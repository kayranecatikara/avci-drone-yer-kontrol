"""
Avci Drone - Gudum ve Kestirim Cekirdegi (saf Python + Numpy)
=============================================================
Iki sinif:
  1) APN_Guidance   : Augmented Proportional Navigation -> Roll/Pitch/Yaw/Throttle komutu
  2) IMMEKF_Filter  : 3-modelli (CV/CA/CT) IMM-EKF hedef takip + GNSS jam / FOV kaybi dayanikligi

VARSAYILAN KOORDINAT CERCEVESI (degistirilebilir):
  - Dunya cercevesi, sag-el, z YUKARI.
  - yaw, +x ekseninden +y eksenine dogru (CCW) olcuulur: yaw = atan2(y, x)
  - SDK'nin ekseni farkliysa (Unreal sol-el olabilir) CONFIG'deki isaret
    carpanlarini (sign_*) saha kalibrasyonunda ayarla.
"""

import numpy as np


# ===========================================================================
# 1) APN GUDUM SINIFI
# ===========================================================================
class APN_Guidance:
    """
    Augmented Proportional Navigation tabanli onleme gudumu.

    compute(...) -> dict:
        roll, pitch, yaw, throttle : SDK'ya basilacak normalize komutlar
                                     roll/pitch/yaw in [-1, 1], throttle in [0, 1]
        *_deg                      : fiziksel aci/oran (debug)
        a_cmd, closing_speed, ...  : telemetri (debug / sunum videosu icin)

    Kamera kisiti:
      Kamera govde burnundan 35 derece YUKARI sabit. Hedefi dikeyde kadrajda
      tutmak icin pitch = (LOS_yukselis_acisi - 35 derece) olarak hesaplanir.
      Ayni irtifadaki hedefte LOS_yukselis ~ 0 -> pitch ~ -35 (burun asagi):
      bu hem ileri itki saglar hem kamerayi yataya cevirir (35 derecelik tilt'in
      tasarim amaci budur).
    """

    def __init__(self,
                 N=4.0,                 # APN navigasyon kazanci (3-5; dusuk hiz orani icin 4)
                 cam_tilt_deg=35.0,     # kamera yukari sabit aci
                 dt=0.02,               # 50 Hz
                 max_tilt_deg=50.0,     # Angle Mode roll/pitch limiti (Drone yere çakılmasın diye limitlendi)
                 max_yaw_rate_deg=120.0,
                 hover_throttle=0.5,    # asili kalma throttle referansi (baz; kalibre et)
                 k_yaw=2.0,             # yaw hata -> yaw rate kazanci
                 kp_alt=1.0,            # irtifa hatasi -> dikey ivme (1/s^2) - "roket tirmanis"
                 kd_alt=2.0,            # dikey hiz sonumleme (1/s) - asma onleme
                 g=9.81,
                 sign_roll=1.0,         # saha kalibrasyonunda isaret duzeltme
                 sign_yaw=1.0,
                 sign_pitch=1.0,        # Unreal pitch ters ise -1 yap (nose-up/backflip duzeltme)
                 warmup_s=2.0,          # soft-start: ilk 2 s komut otoritesi 0->1 (devrilme onleme)
                 max_closing=45.0,      # closing_speed tavani (m/s) - EKF spike'i t_go'yu sifirlamasin
                 # --- YATAY HIZ-TAKIPLI KONTROLCU (sonumleme = salinim onleyici) ---
                 kp_vel=1.0,            # hiz hatasi -> ivme kazanci (1/s)
                 v_approach=12.0,       # istenen yatay kapanis hizi (m/s) - Talon'dan (15-18) HIZLI olmali
                 k_apn=0.5,             # APN lateral feed-forward agirligi (ATR; bounded)
                 a_apn_max=10.0):       # APN ivme tavani (m/s^2)
        self.N = float(N)
        self.cam_tilt = np.radians(cam_tilt_deg)
        self.dt = float(dt)
        self.max_tilt = np.radians(max_tilt_deg)
        self.max_yaw_rate = np.radians(max_yaw_rate_deg)
        self.hover = float(hover_throttle)
        self.k_yaw = float(k_yaw)
        self.kp_alt = float(kp_alt)
        self.kd_alt = float(kd_alt)
        self.g = float(g)
        self.sign_roll = float(sign_roll)
        self.sign_yaw = float(sign_yaw)
        self.sign_pitch = float(sign_pitch)
        self.warmup_s = float(warmup_s)
        self.max_closing = float(max_closing)
        self.kp_vel = float(kp_vel)
        self.v_approach = float(v_approach)
        self.k_apn = float(k_apn)
        self.a_apn_max = float(a_apn_max)
        self._t = 0.0                  # ic zaman sayaci (soft-start rampasi icin)
        self.lock_timer = 0.0          # Talon'un arkasında bekleme sayacı

        # PID Controller Durum Değişkenleri
        self.pitch_i = 0.0
        self.pitch_last_err = 0.0
        self.roll_i = 0.0
        self.roll_last_err = 0.0
        self.yaw_i = 0.0
        self.yaw_last_err = 0.0
    @staticmethod
    def _wrap(a):
        """Aciyi [-pi, pi] araligina sar."""
        return (a + np.pi) % (2 * np.pi) - np.pi

    def _pid(self, err, last_err, integral, kp, ki, kd, limit=1.0):
        """Standart PID Kontrolcüsü."""
        integral = self._clamp(integral + err * self.dt, -limit, limit)
        derivative = (err - last_err) / self.dt if self.dt > 1e-6 else 0.0
        out = self._clamp((kp * err) + (ki * integral) + (kd * derivative), -limit, limit)
        return out, integral, err

    @staticmethod
    def _clamp(v, lo, hi):
        return max(lo, min(hi, v))

    @staticmethod
    def _clamp_mag(v, vmax):
        n = float(np.linalg.norm(v))
        return v * (vmax / n) if n > vmax else v

    def compute(self, own_pos, own_vel, own_euler,
                tgt_pos, tgt_vel, tgt_accel=None):
        """
        own_pos   : (3,) kendi konum [x,y,z]
        own_vel   : (3,) kendi hiz
        own_euler : (3,) kendi tutum [roll, pitch, yaw] (radyan)
        tgt_pos   : (3,) hedef konum   (jam/FOV kaybinda IMM-EKF kestirimini ver)
        tgt_vel   : (3,) hedef hiz     (IMM-EKF'ten)
        tgt_accel : (3,) hedef ivme    (opsiyonel; IMM-EKF'ten - APN terimi)
        """
        own_pos = np.asarray(own_pos, float)
        own_vel = np.asarray(own_vel, float)
        own_euler = np.asarray(own_euler, float)
        tgt_pos = np.asarray(tgt_pos, float)
        tgt_vel = np.asarray(tgt_vel, float)
        self._t += self.dt                         # soft-start zaman sayaci

        # === LOS geometrisi (dunya cercevesi) ===
        R = tgt_pos - own_pos                      # LOS vektoru
        rng = np.linalg.norm(R)
        if rng < 1e-6:
            rng = 1e-6
        u_los = R / rng
        V_rel = tgt_vel - own_vel                  # bagil hiz
        Vc = -np.dot(R, V_rel) / rng               # kapanis hizi (+ kapaniyor)
        Vc = self._clamp(Vc, -self.max_closing, self.max_closing)
        Omega = np.cross(R, V_rel) / np.dot(R, R)  # LOS donus hizi
        los_rate = np.linalg.norm(Omega)

        # APN lateral ivme (cift-capraz carpim -> LOS'a DIK; isaret-elliginden BAGIMSIZ geometrik vektor)
        a_apn = self.N * Vc * np.cross(Omega, u_los)
        if tgt_accel is not None:
            tgt_accel = np.asarray(tgt_accel, float)
            a_perp = tgt_accel - np.dot(tgt_accel, u_los) * u_los
            a_apn = a_apn + 0.5 * self.N * a_perp

       # === YATAY: HIZ-TAKIPLI SONUMLU KONTROLCU + APN (SON ÇARE: SCALAR MATEMATİK) ===
        los_h = np.array([float(R[0]), float(R[1])])
        dist_h = np.linalg.norm(los_h)
        u_h = los_h / dist_h if dist_h > 1e-6 else np.array([0.0, 0.0])
        
        # Talon hızı
        tgt_speed_h = max(np.linalg.norm(tgt_vel[0:2]), 18.0)
        
        # --- KAMİKAZE FAZLARI ---
        tgt_dir = tgt_vel[0:2] / tgt_speed_h if tgt_speed_h > 1.0 else (los_h / dist_h if dist_h > 1e-6 else np.array([0.0, 0.0]))
        
        if not hasattr(self, 'is_death_plunge'):
            self.is_death_plunge = False
            self.has_committed_to_dive = False
            self.death_timer = 0.0
            self.dive_start_timer = 0.0
            self.lock_timer = 0.0

        if not self.is_death_plunge:
            # Kilit sayacı: Drone Talon'a 15 metreden daha yakınsa süre başlar.
            # (İrtifa dalgalanmaları kilidi bozmasın diye sadece mesafeye bakıyoruz)
            if rng > 15.0:
                self.lock_timer = 0.0
            else:
                self.lock_timer += self.dt

        # KULLANICI İSTEĞİ: "kilitlenme 5.2 saniye olsun"
        if self.lock_timer >= 5.2:
            self.is_death_plunge = True
            
        # KULLANICI İSTEĞİ: "talona tam gelmedi alçalandı... biraz daha ilerlesi"
        # Dalışa çok erken (2.0 metreden) geçiyordu. Bunu 0.5 metreye çektim!
        # Artık uçağın tam gövdesinin üstüne kadar (+0.5m yükseklikte) dümdüz ilerleyecek, tam üstüne geldiğinde dalacak!
        if self.is_death_plunge and dist_h <= 0.5:
            self.has_committed_to_dive = True

        if not self.is_death_plunge:
            # UZAKTAN YAKLAŞMA VE KUYRUK TAKİBİ (STALKING) FAZI
            # Mesafe kapandıkça hızını uçağın hızına eşitler ve 5.2 saniye boyunca arkasında usulca stalk'lar!
            err_d = rng - 0.5
            hiz_farki = self._clamp(err_d * 1.5, -2.0, 30.0) 
            dyn_v_app = tgt_speed_h + hiz_farki
            
            thr_boost = 0.05
            p_gain = 0.035
            u_h = los_h / max(dist_h, 0.1) 
            target_z = tgt_pos[2] - 0.5
        else:
            if not self.has_committed_to_dive:
                # KİLİT OLDU: YÜKSELEREK İLERLEME FAZI
                # "hafif hafif yükselcek talonun tam yukarısında olacak şekilde ama baya yukarısında"
                self.death_timer += self.dt
                progress = min(self.death_timer / 3.0, 1.0)
                
                # -0.5'ten başla, 1.0 metre tırmanarak +0.5'e çık! (Talonun üstü)
                target_z = (tgt_pos[2] - 0.5) + (progress * 1.0)
                
                # Hızı yüksek ve YUMUŞAK tut (arkaya kayma sarsıntısını engeller)
                # Mesafe azaldıkça hız farkı +30'dan +15'e pürüzsüzce düşer
                dyn_v_app = tgt_speed_h + 15.0 + self._clamp((dist_h)*1.5, 0.0, 15.0)
                thr_boost = 0.15
                p_gain = 0.035
                
                # Uçağa doğru dümdüz ilerle
                u_h = los_h / max(dist_h, 0.1)
            else:
                # DALIŞ FAZI: TAM ÜSTÜNDEYİZ
                # "azcık ortasına gelcek sonra inecek"
                self.dive_start_timer += self.dt
                
                # Artık tam üstünde olduğumuz için inişi daha hızlı (0.5 saniyede) yapsın
                dive_progress = min(self.dive_start_timer / 0.5, 1.0)
                
                # KULLANICI İSTEĞİ: "azalt yüksekli" -> Yükseklik +1.0'dan +0.5'e düşürüldü!
                # +0.5 yüksekliğinden, uçağın gövdesine (-0.7) dalış!
                target_z = (tgt_pos[2] + 0.5) - (dive_progress * 1.2)
                
                # Dalış sırasında hız formülü AYNI tutuldu ki sarsıntı/fren yapmasın
                dyn_v_app = tgt_speed_h + 15.0 + self._clamp((dist_h)*1.5, 0.0, 15.0)
                thr_boost = 0.20
                p_gain = 0.035
                
                # SAĞ KANADA SAPMAYI ENGELLEME: Sadece Talon'un uçtuğu yöne (dümdüz) dal!
                u_h = tgt_dir

        v_des_h = np.array([dyn_v_app * u_h[0], dyn_v_app * u_h[1], 0.0])
        own_vel_h = np.array([own_vel[0], own_vel[1], 0.0])
        
        # Yumuşatılmış Hız Takibi
        a_pursuit = (self.kp_vel * 0.85) * (v_des_h - own_vel_h)
        a_apn_h = np.array([a_apn[0], a_apn[1], 0.0])
        a_apn_h = self._clamp_mag(a_apn_h, self.a_apn_max)
        
        # HATA DÜZELTİLDİ: APN'nin aniden 0.0'a düşmesi (Singularity) drone'un arkaya kaymasına (teredüt) yol açıyordu!
        # Artık 5 metreden itibaren APN yavaşça ve pürüzsüzce sıfırlanıyor. Sarsıntı tamamen bitti!
        k_apn_current = self.k_apn * 0.85
        if dist_h < 5.0:
            fade = max((dist_h - 1.0) / 4.0, 0.0) # 5m'de 1.0, 1m'de 0.0
            k_apn_current *= fade
            
        a_des_h = a_pursuit + k_apn_current * a_apn_h

        # === DUNYA -> GOVDE DONUSUMU ===
        yaw = own_euler[2]
        cy, sy = np.cos(yaw), np.sin(yaw)
        a_fwd = a_des_h[0] * cy + a_des_h[1] * sy
        a_right = -a_des_h[0] * sy + a_des_h[1] * cy

        # === ACI -> STICK KOMUTU ===
        # Dronun geriye sert fren yapmasını (arkaya yatmasını) önlemek için geriye yatış (pozitif açı) 10.0 derece ile sınırlandı
        # İleri uçuş (negatif açı) ise max_tilt ile serbest bırakıldı!
        pitch_des = self._clamp(self.sign_pitch * np.arctan2(a_fwd, self.g), -self.max_tilt, np.radians(10.0))
        roll_des = self._clamp(self.sign_roll * np.arctan2(a_right, self.g), -self.max_tilt, self.max_tilt)
        
        pitch_err_deg = np.degrees(pitch_des - own_euler[1])
        roll_err_deg = np.degrees(roll_des - own_euler[0])
        
        pitch_cmd = self._clamp(pitch_err_deg * p_gain, -1.0, 1.0)
        roll_cmd = self._clamp(roll_err_deg * p_gain, -1.0, 1.0)
        
        yaw_des = np.arctan2(R[1], R[0])
        yaw_err = self._wrap(yaw_des - yaw)
        yaw_rate = self._clamp(self.sign_yaw * self.k_yaw * yaw_err, -self.max_yaw_rate, self.max_yaw_rate)
        yaw_cmd = self._clamp(yaw_rate / self.max_yaw_rate, -1.0, 1.0)

        # === DİKEY: İRTİFA KİLİTLEME (Z-LOCKING) ===
        tavan = tgt_pos[2] + 5.0
        target_z = min(target_z, tavan) 
        
        alt_err = target_z - own_pos[2]
        # P-kontrolcüsü 0.8'den 1.5'e çıkarıldı. Milimetrik havada asılı kalma (steady-state error) yok edildi.
        kp_z = 1.5  
        a_climb = (kp_z * alt_err) - (self.kd_alt * own_vel[2])
        
        cos_tilt = np.cos(own_euler[1]) * np.cos(own_euler[0])
        # İleri atılırken drone havalanmasın diye 0.4 yerine 0.7 yapıldı (Gazı az artıracak)
        cos_tilt = max(cos_tilt, 0.7)
        tilt_compensated_hover = self.hover / cos_tilt
        
        base_power = tilt_compensated_hover + thr_boost
        # İrtifayı milimi milimine basması için düzeltme gücü 0.35'ten 0.60'a çıkarıldı!
        alt_correction = (alt_err * 0.60) - (own_vel[2] * 0.10)
        
        # HATA DÜZELTİLDİ: Eskiden "rng <= 15 ise gazı 1.0 (fulle)" kodu vardı!
        # Bu yüzden 15 metreye girince dron ful gaz yapıp Talon'un üstünden aşıyordu! İptal edildi.
        if own_pos[2] > tavan:
            throttle = 0.1 
        else:
            throttle = self._clamp(base_power + alt_correction, 0.0, 1.0)

        # === Normalize SDK komutlari + SOFT-START rampasi ===
        ramp = min(1.0, self._t / self.warmup_s) if self.warmup_s > 1e-6 else 1.0
        roll_cmd *= ramp
        pitch_cmd *= ramp
        yaw_cmd *= ramp
        throttle = self.hover + ramp * (throttle - self.hover)

        return {
            "roll": roll_cmd, "pitch": pitch_cmd,
            "yaw": yaw_cmd, "throttle": throttle,
            "roll_deg": np.degrees(roll_des),
            "pitch_deg": np.degrees(pitch_des),
            "yaw_rate_deg": np.degrees(yaw_rate),
            "a_cmd": a_des_h,
            "a_apn": a_apn,
            "closing_speed": Vc,
            "los_rate": los_rate,
            "range": rng,
            "alt_err": alt_err,
            "ramp": ramp,
        }

# ===========================================================================
# 2) IMM-EKF FILTRE SINIFI (3 model: CV / CA / CT)
# ===========================================================================
class IMMEKF_Filter:
    """
    Durum (9D, dunya): [x, y, z, vx, vy, vz, ax, ay, az]
    Olcum (3D)       : [x, y, z]   (POS-ONLY - hiz EKF tarafindan kestirilir, gecikme yok)

    GNSS jammer dayanikligi:
      step(z=None)            -> yalniz tahmin (predict-only). Veri kesilince (jam) cagir;
                                 filtre son kestirimle rotayi surdurur (coasting).
      Mahalanobis gating      -> sahte/spoof olcumu (buyuk konum kaymasi) reddeder -> coast.
      Tutarli-red re-acquire  -> ardisik RED'ler birbirine YAKIN ise gercek veri donuyordur
                                 -> hiz koruyarak yeniden kilitlen; ZIPLIYORSA spoof -> coast'ta kal.
      predict_trajectory(T)   -> gelecek T saniye rota.
    """

    def __init__(self, dt=0.02, gate_chi2=12.0, max_reject=10, coherence_m=3.0, pos_std=0.5,
                 max_speed=40.0, max_accel=30.0, warmup_frames=25):
        self.dt = float(dt)
        self.n = 9
        self.m = 3                          # POS-ONLY olcum [x,y,z]
        # Anti-spike: pos-only filtrede ilk karelerde hiz/ivme matematiksel siciramasi olur.
        # Cikis fiziksel tavanla sinirlanir; ayrica ilk warmup_frames boyunca hiz rampa ile acilir.
        self.max_speed = float(max_speed)    # m/s  (Talon ~15-18; tavan genis)
        self.max_accel = float(max_accel)    # m/s^2
        self.warmup_frames = int(warmup_frames)  # ~0.5 s @50Hz: hiz/ivme cikisi 0->1 rampa
        self._frames = 0
        # Gate: jammer spoof'unu (buyuk konum kaymasi) yakalar, gercek gurultuyu elemez.
        # chi2(3,0.99)=11.34 -> 12 esik kaba spoof'a yeterli, gercek veriye toleransli.
        self.gate_chi2 = float(gate_chi2)
        self.max_reject = int(max_reject)
        self.coherence = float(coherence_m) # ardisik RED'ler bu mesafe icinde TUTARLI ise
                                            # gercek veri donuyordur (re-acquire); degilse spoof (coast)
        self.pos_std = float(pos_std)
        self.reject_count = 0
        self._last_reject = None
        self.initialized = False
        self.last_rejected = False

        # Mod olasiliklari (CV en yuksek apriori - Talon mod kalicilig)
        self.mu = np.array([0.60, 0.20, 0.20])           # [CV, CA, CT]
        # Markov gecis matrisi (kosegen yuksek = mod kaliciligi)
        self.P_trans = np.array([
            [0.92, 0.04, 0.04],
            [0.05, 0.90, 0.05],
            [0.05, 0.05, 0.90],
        ])

        # Olcum matrisi: yalniz konum sec (3x9)
        self.H = np.zeros((self.m, self.n))
        self.H[0, 0] = self.H[1, 1] = self.H[2, 2] = 1.0
        # Konum olcum gurultusu (std^2)
        self.R = np.diag(np.array([pos_std, pos_std, pos_std]) ** 2)

        # Model bazli surec gurultusu spektral yogunlugu
        # (manevraya cabuk yanit + kovaryans cokmesini onleme -> gate dengeli kalir)
        self.q = [2.0, 5.0, 5.0]    # [CV, CA, CT]
        self.Q = [self._build_Q(qi) for qi in self.q]

        # Her model icin durum & kovaryans
        self.x = [np.zeros(self.n) for _ in range(3)]
        self.P = [np.eye(self.n) * 100.0 for _ in range(3)]

    # ---- Q insasi (eksen-bazli surekli beyaz jerk modeli) ----
    def _build_Q(self, q):
        dt = self.dt
        q1 = q * np.array([
            [dt**5 / 20, dt**4 / 8, dt**3 / 6],
            [dt**4 / 8,  dt**3 / 3, dt**2 / 2],
            [dt**3 / 6,  dt**2 / 2, dt],
        ])
        Q = np.zeros((9, 9))
        for k in range(3):                     # x, y, z eksenleri
            idx = [k, 3 + k, 6 + k]            # [p, v, a]
            for r in range(3):
                for c in range(3):
                    Q[idx[r], idx[c]] += q1[r, c]
        return Q

    # ---- Model gecis fonksiyonlari ----
    def _f_cv(self, x):
        dt = self.dt
        y = x.copy()
        y[0:3] = x[0:3] + x[3:6] * dt
        y[3:6] = x[3:6]
        y[6:9] = 0.0                            # CV: ivme ~ 0
        return y

    def _f_ca(self, x):
        dt = self.dt
        y = x.copy()
        y[0:3] = x[0:3] + x[3:6] * dt + 0.5 * x[6:9] * dt**2
        y[3:6] = x[3:6] + x[6:9] * dt
        y[6:9] = x[6:9]
        return y

    def _f_ct(self, x):
        dt = self.dt
        y = x.copy()
        vx, vy = x[3], x[4]
        ax, ay = x[6], x[7]
        # donus hizi: omega = (v x a)_z / |v|^2
        sp2 = vx * vx + vy * vy + 1e-6
        w = (vx * ay - vy * ax) / sp2
        th = w * dt
        if abs(w) < 1e-4:                       # neredeyse duz -> CV gibi (yatay)
            y[0] = x[0] + vx * dt
            y[1] = x[1] + vy * dt
            y[3] = vx
            y[4] = vy
        else:
            s, c = np.sin(th), np.cos(th)
            y[0] = x[0] + (s / w) * vx - ((1 - c) / w) * vy
            y[1] = x[1] + ((1 - c) / w) * vx + (s / w) * vy
            y[3] = c * vx - s * vy
            y[4] = s * vx + c * vy
            y[6] = c * ax - s * ay             # ivmeyi de dondur (tutarlilik)
            y[7] = s * ax + c * ay
        # dikey eksen: CA gibi
        y[2] = x[2] + x[5] * dt + 0.5 * x[8] * dt**2
        y[5] = x[5] + x[8] * dt
        y[8] = x[8]
        return y

    def _models(self):
        return [self._f_cv, self._f_ca, self._f_ct]

    @staticmethod
    def _num_jac(f, x, eps=1e-5):
        n = len(x)
        F = np.zeros((n, n))
        for i in range(n):
            dx = np.zeros(n); dx[i] = eps
            F[:, i] = (f(x + dx) - f(x - dx)) / (2 * eps)
        return F

    # ---- Baslatma ----
    def initialize(self, z, keep_vel=False):
        z = np.asarray(z, float)
        # hiz/ivme kestirimini koru (re-acquire) ya da sifirla (ilk kilit)
        vel = self.get_state()[3:6] if (keep_vel and self.initialized) else np.zeros(3)
        x0 = np.zeros(self.n)
        x0[0:3] = z[0:3]
        x0[3:6] = vel
        for i in range(3):
            self.x[i] = x0.copy()
            P0 = np.eye(self.n) * 10.0
            P0[3:6, 3:6] *= 9.0                # hiz belirsizligi: yumusatildi (eski 25 -> spike yapardi)
            P0[6:9, 6:9] *= 9.0                # ivme belirsizligi de nazik baslat
            self.P[i] = P0
        self.initialized = True
        if not keep_vel:
            self._frames = 0                   # ilk kilit -> warmup rampasini sifirla

    # ---- Ana adim ----
    def step(self, z=None):
        """
        z : (3,) konum olcumu [x,y,z] veya None (jam -> predict-only/coast)
        Donus: (9,) IMM-birlesik durum kestirimi (pos, vel, acc)
        """
        if not self.initialized:
            if z is not None:
                self.initialize(z)
            return self.get_state()

        self._frames += 1                              # warmup rampa sayaci

        models = self._models()

        # 1) Karistirma (mixing)
        c_pred = self.P_trans.T @ self.mu              # tahmini mod olasilik (normalizer)
        c_pred = np.maximum(c_pred, 1e-12)
        x0, P0 = [], []
        for j in range(3):
            mu_ij = self.P_trans[:, j] * self.mu / c_pred[j]
            xj = sum(mu_ij[i] * self.x[i] for i in range(3))
            Pj = np.zeros((self.n, self.n))
            for i in range(3):
                d = (self.x[i] - xj).reshape(-1, 1)
                Pj += mu_ij[i] * (self.P[i] + d @ d.T)
            x0.append(xj); P0.append(Pj)

        # 2) Model-kosullu tahmin
        xp, Pp = [], []
        for j in range(3):
            F = self._num_jac(models[j], x0[j])
            xpred = models[j](x0[j])
            Ppred = F @ P0[j] @ F.T + self.Q[j]
            xp.append(xpred); Pp.append(Ppred)

        # --- Gating: birlesik tahminden Mahalanobis mesafesi ---
        do_update = z is not None
        if do_update:
            x_comb_pred = sum(c_pred[j] * xp[j] for j in range(3))
            P_comb_pred = np.zeros((self.n, self.n))
            for j in range(3):
                d = (xp[j] - x_comb_pred).reshape(-1, 1)
                P_comb_pred += c_pred[j] * (Pp[j] + d @ d.T)
            y = np.asarray(z, float) - self.H @ x_comb_pred
            S = self.H @ P_comb_pred @ self.H.T + self.R
            d2 = float(y @ np.linalg.solve(S, y))
            if d2 > self.gate_chi2:                # suphe: bo bozuk/spoof/jam olcumu -> guncelleme
                self.last_rejected = True
                zc = np.asarray(z, float)[0:3]
                # COHERENCE: ardisik RED'ler birbirine YAKIN (kararli) ise gercek veri
                # donuyordur (filtre kaymis) -> tutarli sayaci buyut. ZIPLIYORSA gurultulu
                # sahte (jammer) -> sayaci sifirla, coast'ta kal (asla spoof'a kilitlenme).
                if self._last_reject is not None and \
                        np.linalg.norm(zc - self._last_reject) < self.coherence:
                    self.reject_count += 1
                else:
                    self.reject_count = 1
                self._last_reject = zc
                if self.reject_count >= self.max_reject:
                    # tutarli RED zinciri -> jam bitti/gercek veri: HIZI KORUYARAK yeniden kilitlen
                    self.initialize(z, keep_vel=True)
                    self.reject_count = 0
                    self._last_reject = None
                    self.last_rejected = False
                    return self.get_state()
                do_update = False
            else:
                self.reject_count = 0
                self._last_reject = None
                self.last_rejected = False

        # 3) Olcum guncellemesi + olabilirlik
        if do_update:
            z = np.asarray(z, float)
            likelihood = np.zeros(3)
            for j in range(3):
                y = z - self.H @ xp[j]
                S = self.H @ Pp[j] @ self.H.T + self.R
                K = Pp[j] @ self.H.T @ np.linalg.inv(S)
                self.x[j] = xp[j] + K @ y
                self.P[j] = (np.eye(self.n) - K @ self.H) @ Pp[j]
                # Gauss olabilirlik
                det = max(np.linalg.det(2 * np.pi * S), 1e-30)
                likelihood[j] = np.exp(-0.5 * (y @ np.linalg.solve(S, y))) / np.sqrt(det)
            likelihood = np.maximum(likelihood, 1e-30)
            mu_new = c_pred * likelihood
            self.mu = mu_new / np.sum(mu_new)
        else:
            # predict-only: rotayi surdur, mod olasilik tahmini devreye gir
            for j in range(3):
                self.x[j] = xp[j]
                self.P[j] = Pp[j]
            self.mu = c_pred / np.sum(c_pred)

        return self.get_state()

    # ---- Cikti yardimcilari ----
    def get_state(self):
        return sum(self.mu[j] * self.x[j] for j in range(3))

    def get_position(self):
        return self.get_state()[0:3]

    def _clamp_mag(self, v, vmax):
        n = float(np.linalg.norm(v))
        return v * (vmax / n) if n > vmax else v

    def get_velocity(self):
        # warmup rampasi: ilk warmup_frames boyunca 0->1 (baslangic spike'ini sondurur)
        # + fiziksel tavanla sinirla (her an spike korumasi)
        r = min(1.0, self._frames / max(1, self.warmup_frames))
        return self._clamp_mag(self.get_state()[3:6] * r, self.max_speed)

    def get_acceleration(self):
        r = min(1.0, self._frames / max(1, self.warmup_frames))
        return self._clamp_mag(self.get_state()[6:9] * r, self.max_accel)

    def get_mode_probabilities(self):
        return self.mu.copy()

    def predict_trajectory(self, horizon_s, step_s=None):
        """Gelecek rotayi ciz: birlesik durumu mod-agirlikli gecisle ileri tasi."""
        step_s = step_s or self.dt
        steps = int(horizon_s / step_s)
        models = self._models()
        x = self.get_state().copy()
        traj = []
        for _ in range(steps):
            x = sum(self.mu[j] * models[j](x) for j in range(3))
            traj.append(x[0:3].copy())
        return np.array(traj)


# ===========================================================================
# ANA DONGU ENTEGRASYON ORNEGI (50 Hz)
# ===========================================================================
if __name__ == "__main__":
    # --- Senaryo: hedef once CV ucar, sonra koordineli donus yapar; ---
    # --- arada GNSS jam (olcum=None) ve bir bozuk olcum enjekte edilir ---
    np.random.seed(0)
    dt = 0.02
    ekf = IMMEKF_Filter(dt=dt)
    apn = APN_Guidance(dt=dt, cam_tilt_deg=35.0)

    # gercek hedef baslangici
    tp = np.array([100.0, 0.0, 20.0])
    tv = np.array([0.0, 16.0, 0.0])
    own_pos = np.array([0.0, 0.0, 20.0])
    own_vel = np.array([0.0, 0.0, 0.0])
    own_euler = np.array([0.0, 0.0, 0.0])

    rmse_acc = []
    for k in range(300):
        t = k * dt
        # gercek hedef dinamigi
        if t > 2.0:                       # 2 s sonra koordineli donus
            w = np.radians(20.0)          # 20 deg/s
            R2 = np.array([[np.cos(w*dt), -np.sin(w*dt)],
                           [np.sin(w*dt),  np.cos(w*dt)]])
            tv[0:2] = R2 @ tv[0:2]
        tp = tp + tv * dt

        # olcum uretimi - POS-ONLY (3B) + GNSS jammer senaryosu
        if 100 <= k < 120:                # veri KESIK (jam) -> coast/predict-only
            z = None
        elif 150 <= k < 165:              # GURULTULU SAHTE (jammer): buyuk RASTGELE sicrama
            z = tp + np.random.randn(3) * 30.0          # incoherent -> reddet, coast
        else:
            z = tp + np.random.randn(3) * 0.5           # normal konum olcumu

        est = ekf.step(z)
        rmse_acc.append(np.linalg.norm(est[0:3] - tp))

        # gudum komutu (kestirilen hedef durumu ile - hiz EKF tarafindan kestirildi)
        cmd = apn.compute(own_pos, own_vel, own_euler,
                          ekf.get_position(), ekf.get_velocity(),
                          ekf.get_acceleration())

        if k in (50, 110, 157, 200, 250):
            mp = ekf.get_mode_probabilities()
            tag = {110: " [JAM/coast]", 157: " [SAHTE/coast]"}.get(k, "")
            print(f"k={k:3d} t={t:4.2f}s | poz hata={rmse_acc[-1]:5.2f}m "
                  f"| mod[CV,CA,CT]=[{mp[0]:.2f},{mp[1]:.2f},{mp[2]:.2f}] "
                  f"| reddedildi={ekf.last_rejected}{tag}")

    traj = ekf.predict_trajectory(1.0)
    print(f"\nOrtalama poz hatasi: {np.mean(rmse_acc):.2f} m")
    print(f"1 s ileri rota tahmini ilk/son nokta: {traj[0].round(1)} -> {traj[-1].round(1)}")
    print("Smoke test tamam.")

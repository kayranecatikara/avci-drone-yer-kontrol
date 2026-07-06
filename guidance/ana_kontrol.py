import csv
import math
import os
import time
import numpy as np
from fusion.inovasyonlu_j_v2 import GNSSDuzeltici as V2Filtre
from guidance.ibvs_guidance import AvciGorselGudum

# --- UCUS LOGU ---
_HERE = os.path.dirname(os.path.abspath(__file__))          # .../guidance
_PROJ_ROOT = os.path.dirname(_HERE)                         # Depo root'u
_VERI_DIR = os.path.join(_PROJ_ROOT, "veri")                # Calisma ciktilari
_LOG_COLS = [
    # meta
    "t_perf", "t_wall", "phase", "kaynak", "durum", "handoff", "fresh", "none_count",
    # drone durumu (cm / derece / rad)
    "drone_x", "drone_y", "drone_z", "drone_roll", "drone_pitch", "drone_yaw_deg",
    "drone_yaw_rad", "drone_speed", "vown_x", "vown_y",
    # hedef (FILTRE): est=2sn lead, anlik=lead'siz, ham=bozuk
    "est_x", "est_y", "est_z", "z_ref", "xy_anlik_x", "xy_anlik_y", "son_z_anlik",
    "son_hiz_x", "son_hiz_y", "son_hiz_z", "son_ham_x", "son_ham_y", "son_ham_z",
    # hedef (GERCEK / truth) + drone truth + gercek mesafe + hedef rotasyon (guvenilmez)
    "true_tx", "true_ty", "true_tz", "true_dx", "true_dy", "true_dz", "gercek_mesafe",
    "tgt_roll", "tgt_pitch", "tgt_yaw",
    # hata / guduum ici
    "ex", "ey", "ez", "d_h", "e_fwd", "e_right", "vcap", "mag_scale", "alc_oncelik", "ez_int",
    # terminal vurus (strike)
    "d_s", "v_close", "vdx", "vdy", "ax", "ay", "a_fwd", "a_right",
    # yaw & FOV (nose_off_true = burun ile GERCEK hedef arasi aci, DERECE)
    "bearing", "yaw_err", "nose_off_true",
    # ham komut (rate-limit ONCESI) vs uygulanan komut (rate-limit SONRASI = self.prev)
    "thr_raw", "pitch_raw", "roll_raw", "yaw_raw", "thr_cmd", "pitch_cmd", "roll_cmd", "yaw_cmd",
    # GORSEL GUDUM (VISUAL fazi): normalize bbox-merkez hatasi + gordu/conf/alan
    "vis_ex", "vis_ey", "vis_gordu", "vis_conf", "vis_area",
]

class Cfg:
    # ==============================================================
    # ORTAK PARAMETRELER (3 gorevin birden kullandigi parametreler)
    # ==============================================================
    ROT_IN_DEGREES = True       # get_drone_rotation derece donduruse True
    PITCH_SIGN = +1.0           # ileri hareket +pitch degilse -1
    ROLL_SIGN  = +1.0           # saga hareket +roll degilse -1
    YAW_SIGN   = +1.0           # hedefe donus icin +yaw degilse -1
    Z_SIGN     = +1.0

    # --- DONGU (server.py / calistirma 50 Hz surer) ---
    LOOP_HZ = 50.0
    DT = 1.0 / LOOP_HZ

    # --- KOMUT TAVANLARI ---
    PITCH_MAX = 0.75
    ROLL_MAX  = 0.75
    THR_UP    = 0.70
    THR_DN    = -1.00
    YAW_MAX   = 0.45           # burnu (kamerayi) hedefe donuk tutar

    # --- HIZ LIMITI (salinimi onleme) ---
    MAX_DELTA = 0.05           # komut/tick max degisim

    # --- BURUN -> HEDEF YAW (GPS yaklasma + strike ORTAK) ---
    KP_YAW = 1.3
    YAW_DEADBAND = math.radians(3)

    # --- DEBUG ---
    DEBUG_Z = True

    # --- UCUS LOGU ---
    LOG_ENABLE = True

    # ==========================================================================
    # GOREV 1: GPS VERILERI ILE TAKIP  (bozuk GNSS -> J temizleme -> yaklasma)
    # ==========================================================================
    # --- KALKIS / ARAMA IRTIFASI ---
    SEARCH_ALT = 5000.0         # cm; arama irtifasi (TUNE). Kalkis ayri katmanda ise TAKEOFF=False.
    TAKEOFF = True
    ALT_TOL = 200.0             # cm; irtifa ulasma toleransi
    TAKEOFF_THR = 0.6           # tirmanma throttle

    # --- YAKLASMA HIZI PROFILI (overshoot guard) ---
    V_CAP_FAR  = 2500.0         # cm/s; hedef uzakta iken hiz degeri (120km/h = 3333 cm/s'in altinda)
    V_CAP_NEAR = 500.0          # cm/s; hedef handoff yakininda iken hiz degeri
    BRAKE_DIST = 7000.0         # cm; bu mesafe altinda hizi kademeli olarak dusur

    # --- ANTI-OVERSHOOT STANDOFF ---
    APPROACH_STANDOFF   = 500.0 # cm; hedefin LOS(Line of Sight) uzerinde nisan alma mesafesi
    APPROACH_LEAD_S     = 0.5   # s; nisani hedefin gidecegi yere ongoru suresi
    APPROACH_ALT_OFFSET = 500.0 # cm; droneun hedefin altindan ucacagi mesafe

    # --- PID (Proportional-Integral-Deriative) GAINS ---
    KP_H = 0.00025              # cm; yatay konum hatasi -> pitch/roll komutu
    KD_H = 0.00060              # yatay konum hatasi turevi -> sonumleme/fren
    KP_Z = 0.00040              # irtifa hatasi -> throttle
    KD_Z = 0.00100              # dikey hiz -> sonumleme
    KI_Z = 0.00020              # kalici irtifa hatasini topla_kapat
    INT_Z_BAND = 2500.0         # cm; integrali sadece |ez|<band iken biriktir (uzakta iken sismeyi(windup) onle)
    INT_Z_MAX  = 5000.0         # cm; biriken integrali kisma (KI_Z*INT_Z_MAX = 1.0 -> tek basina tavani asamaz)

    # --- FILTRELEME / DEADBAND (Turev EMA(Exponential Moving Average) + yatay jitter) ---
    DERIV_EMA = 0.20            # a degeri (yeni ortalama = (1 - a) x eski_ortalama + a x ham_deger)
    POS_DEADBAND = 150.0        # cm; yakinda jitter'i onle

    # --- EKSIK GPS VERISI YONETIMI (tick @50Hz) ---
    HOLD_TICKS = 300           # ~6s: bu sureye kadar son kestirimi tut

    # =================================================================
    # GOREV 2: GORSEL TAKIP
    # =================================================================
    # --- GORSEL TEMAS SONRASI YONELIM ---
    VIS_MODEL_PATH   = os.path.join(_PROJ_ROOT, "models", "best.pt")    # YOLO tespit modeli
    VIS_CONF_MIN     = 0.45     # tespiti gecerli sayma esigi
    VIS_N_LOCK       = 5        # gorsel gudum icin ardisik gecerli tespit sayisi
    VIS_STALE_S      = 0.5      # tespit bu sureden eskiyse yok say
    VIS_DEADRECKON_S = 0.5      # kayipta son EMA yonuyle KISA kor-devam, sonra hover
    VIS_LOST_TO_GPS_S = 1.0     # kayip kac sn asinca GPS gudumune donulsun
    VIS_EMA          = 0.4      # bbox merkez hatasi (ex/ey) EMA yumusatma orani (tek-kare tespit hatasini bastir)
    VIS_EY_REF       = 0.43     # dikey nisan referansi: kameranin 25 derecelik yukari tilt telafisi

    # --- ISARETLER (+/-) ---
    VIS_SIGN_YAW     = +1.0     # yaw yonu (ex>0 hedef sagda -> burnu saga cevir)
    VIS_SIGN_VZ      = -1.0     # throttle yonu (hedef referansin altinda -> alcal)
    VIS_SIGN_PITCH   = +1.0     # Ileri yon (yaklasma icin +pitch)

    # --- KAZANCLAR / KAPILAR ---
    VIS_K_YAW        = 0.5      # yatay ortalama kazanci (yaw komutu = SIGN*K*ex)
    VIS_K_VZ         = 0.5      # dikey ortalama kazanci (throttle komutu = SIGN*K*ey)
    VIS_K_FWD        = 0.4      # ileri yaklasma kazanci (yalnizca merkez-kapisi acikken)
    VIS_FWD_MAX      = 0.5      # ileri (pitch) komut tavani
    VIS_CENTER_GATE  = 0.35     # once ortala: |ex|,|ey| bu esigin altinda ise ileriye izin ver
    VIS_AREA_STOP    = 0.20     # bbox alan orani buna yaklasinca ileri hizi 0'a indir (yakin -> dur)

    # ==============================================================
    # GOREV 3: GUDUM / STRIKE  (handoff karari + terminal vurus)
    # ==============================================================
    # --- HANDOFF (histerezisli) ---
    HANDOFF_RANGE = 4000.0      # cm; bu mesafenin altina girince kilitle
    HANDOFF_EXIT  = 5000.0      # cm; bu mesafenin disina cikinca handoff iptal
    AUTO_VISUAL_HANDOFF = False # yakin mesafede cisim tanimlandiginda gorsel takibe gec

    # --- TERMINAL VURUS (GPS ile CARPMA) - VARSAYILAN KAPALI ---
    GPS_TERMINAL_STRIKE = False # False: sadece hedefe yaklas | TRUE: hedefi vur
    STRIKE_RANGE = 6000.0       # cm; bu menzil altinda vurus moduna gec
    V_CLOSE      = 1200.0       # cm/s; kapanis hizi tavani (uzakta hizli)
    KP_CLOSE     = 0.6          # 1/s; kapanis hizi = KP_CLOSE*mesafe (yakinda kademeli yavaslar)
    V_CLOSE_MIN  = 700.0        # cm/s; kapanis hizi tabani (temasta 0'a inmesin -> geri atilma yok, delip gecer).
    KV_STRIKE    = 2.5          # 1/s; hiz izleme kazanci (ivme = KV*(v_des-v_own); dusuk -> yumusak). satir 852-853 + UI slider kullanir
    A_MAX_STRIKE = 9.81 * math.tan(math.radians(35.0)) * 100.0   # ~687 cm/s^2 yatay ivme tavani (35 derece tilt)
    STRIKE_TILT  = 0.8          # vurus tilt yetkisi
    COMMIT_RANGE = 500.0        # cm; bu menzil altinda yanal ivmeyi kis -> hedefe duz dal (kovalamayi birak)
    VZ_MAX       = 3333.0       # cm/s; max hiz
    

# ==========================================================
# HELPERS
# ==========================================================
def wrap_pi(a): # Aciyi -pi...+pi araligina alir
    return (a + math.pi) % (2.0 * math.pi) - math.pi

def clamp(x, lo, hi): # Degerleri [lo, hi] araligina alir
    return lo if x < lo else hi if x > hi else x

def deadband(x, db): # Kucuk degerleri (|x|<db sifirlar) ->jitter/titreme onler
    return 0.0 if abs(x) < db else x

def rate_limit(target, prev, max_delta): # Komutun tick basi degisimini +-max delta ile sinirlar -> ani sicramayi onler
    return prev + clamp(target - prev, -max_delta, max_delta)

def world_to_body(ex, ey, yaw_rad): # Dunya cveresindeki yatay hatayi govde (ileri/sag) cercevesine cevirir
    c, s = math.cos(yaw_rad), math.sin(yaw_rad)
    e_fwd   = ex * c + ey * s
    e_right = ex * s - ey * c
    return e_fwd, e_right

def speed_cap(d_horiz): # Mesafeye gore hiz tavanini dondurur (yakinda dusuk ->overshoot guard)
    if d_horiz >= Cfg.BRAKE_DIST:
        return Cfg.V_CAP_FAR
    t = d_horiz / Cfg.BRAKE_DIST
    return Cfg.V_CAP_NEAR + (Cfg.V_CAP_FAR - Cfg.V_CAP_NEAR) * t


def _filtre_uret(kaynak): # Gudum kaynagina gore filtre uretir
    if kaynak == "gercek":
        return None
    return V2Filtre()


class AvciKontrol:
    # ================================================================
    # ORTAK / ALTYAPI  (kurulum, komut gonderme, loglama, teshis)
    # ================================================================
    def __init__(self, drone, debug_olc=True, kaynak="v2"):
        self.drone = drone
        self.kaynak = kaynak           # "v2" | "gercek"
        self.filtre = _filtre_uret(kaynak)
        self.durum = "ARAMA"            # ARAMA(yaklasma) -> KILIT(handoff/gorus)
        self.son_ham = None
        self.son_temiz = None           # J'nin son gecerli ciktisi (cm, 2sn lead) - YATAY icin
        self.son_z_anlik = None         # J'nin ANLIK (lead'siz) irtifa kestirimi (cm) - DIKEY icin
        self.son_xy_anlik = None        # J'nin ANLIK (lead'siz) yatay konumu (cm) - terminal vurus LOS'u
        self.son_hiz = None             # J'nin kestirdigi hedef hizi (cm/s, 3B) - olcum/ileri kullanim
        self._fresh = False             # bu tik J'den YENI gecerli kestirim geldi mi?

        # --- FAZ-1 guduum durumu (faz1_gnss_yaklasma.Faz1Guidance'tan) ---
        self.prev = {'thr': 0.0, 'pitch': 0.0, 'roll': 0.0, 'yaw': 0.0}
        self.e_prev = None
        self.t_prev = None
        self.de = [0.0, 0.0, 0.0]       # EMA-filtreli hata turevi (cm/s)
        self._ez_int = 0.0              # dikey INTEGRAL birikimi (cm*s) - kalici irtifa hatasini kapatir
        # kendi YATAY hiz vektoru (temiz konum sonlu-fark, EMA) - terminal vurus icin
        self._own_pxy = None            # onceki kendi yatay konum (cm)
        self._own_tv = None             # onceki olcum zamani
        self._own_v = np.zeros(2)       # kendi yatay hiz (cm/s, dunya)
        # GERCEK modda hedef hizi (truth konum sonlu-fark) - carpisma-rotasi icin
        self._gt_prev_p = None          # onceki truth hedef konum (cm)
        self._gt_prev_t = None
        self._gt_vel = np.zeros(3)      # hedef hizi (cm/s, 3B)
        self.none_count = 0
        self.last_est = None
        self.handoff = False
        self.handoff_announced = False
        self._kalkis_done = (not Cfg.TAKEOFF)

        # debug olcum birikimi
        self.debug_olc = debug_olc
        self.ham_hatalar = []
        self.j_hatalar = []
        self.bozukluk_sayac = {}

        # ucus logu (Cfg.LOG_ENABLE) - lazy-open, uzunca zaman-damgali dosya
        self._log_f = None
        self._log_w = None

        # --- GORSEL GUDUM (IBVS) durumu ---
        # son_tespit: server.dedektor_dongusu'nin beyin_lock icinde yazdigi son bbox dict.
        self.son_tespit = None          # {cx,cy,w,h,conf,W,H,t} | None
        self.son_tespit_t = None        # o tespitin perf_counter zamani (bayatlik kontrolu)
        self._vis_pos_count = 0         # ardisik gecerli-tespit (kilit histerezisi)
        self._vis_lost_count = 0        # ardisik kayip (kor-devam -> hover karari)
        self._vis_ilan = False          # "GPS kesildi" anonsu bir kez basilsin
        self.ibvs = AvciGorselGudum()  # bbox -> angle-mode komut (bagimsiz modul, canli-tune)
        self.vis_mode = "OTO"           # guduum pipeline switch (test): OTO | GPS | GORSEL

    # ----------------------------------------------------------------
    #  Guduum kaynagini CANLI degistir (v2/Gercek butonlari)
    #  Yeni filtre taze baslar; FAZ-1 durumu da sifirlanir (temiz soft-start).
    # ----------------------------------------------------------------
    def set_kaynak(self, kaynak):
        if kaynak == self.kaynak and (self.filtre is not None or kaynak == "gercek"):
            return                          # zaten o kaynak -> dokunma
        self.kaynak = kaynak
        self.filtre = _filtre_uret(kaynak)
        self.son_ham = None                 # yeni filtre taze beslensin
        self.son_z_anlik = None
        self.son_xy_anlik = None
        self.son_hiz = None
        self._fresh = False
        # FAZ-1 durumunu sifirla: komutlar 0'dan rate-limit'lensin, turev/handoff temiz.
        self.prev = {'thr': 0.0, 'pitch': 0.0, 'roll': 0.0, 'yaw': 0.0}
        self.e_prev = None
        self.t_prev = None
        self.de = [0.0, 0.0, 0.0]
        self._ez_int = 0.0              # dikey integrali taze baslat
        self._own_pxy = None            # kendi yatay hiz kestirimini taze baslat
        self._own_tv = None
        self._own_v = np.zeros(2)
        self.none_count = 0
        self.last_est = None
        self.handoff = False
        self.handoff_announced = False
        self.durum = "ARAMA"
        self._kalkis_done = (not Cfg.TAKEOFF)
        # GORSEL GUDUM: yeni gorev -> gorsel kilit/kor-devam durumunu da taze basla
        self.son_tespit = None
        self.son_tespit_t = None
        self._vis_pos_count = 0
        self._vis_lost_count = 0
        self._vis_ilan = False
        self.ibvs.sifirla()
        # ucus logu: yeni gorev -> yeni dosya (sonraki tik taze zaman-damgali acar).
        # NOT: ayni kaynak ust uste secilirse bu metod erken doner (yukarida) -> dosya
        # donmez; temiz dosya icin server'i yeniden baslat ya da kaynak degistir.
        if self._log_f is not None:
            try: self._log_f.close()
            except Exception: pass
            self._log_f = self._log_w = None

    # ----------------------------------------------------------------
    #  Komut gonder (rate-limit + atomik set_control_surfaces)
    # ----------------------------------------------------------------
    def _send(self, thr, pitch, roll, yaw):
        thr   = rate_limit(thr,   self.prev['thr'],   Cfg.MAX_DELTA)
        pitch = rate_limit(pitch, self.prev['pitch'], Cfg.MAX_DELTA)
        roll  = rate_limit(roll,  self.prev['roll'],  Cfg.MAX_DELTA)
        yaw   = rate_limit(yaw,   self.prev['yaw'],   Cfg.MAX_DELTA)
        self.prev = {'thr': thr, 'pitch': pitch, 'roll': roll, 'yaw': yaw}
        self.drone.set_control_surfaces(thr, pitch, roll, yaw, True)

    def _loiter(self):
        # dropout / veri yok: agresifligi kes, hover (thr=0 -> irtifa korunur), seviyelen
        self._send(0.0, 0.0, 0.0, 0.0)

    # ----------------------------------------------------------------
    #  UCUS LOGU: her tik zengin teshis satiri (Cfg.LOG_ENABLE). Lazy-open,
    #  zaman-damgali dosya. Truth + drone/hedef rotasyon + nose_off_true burada
    #  hesaplanir (loglama modu; her tik birkac SDK cagrisi kabul edilir).
    #  d: cagri yerinden gelen alanlar (+ 'drone_pos','drone_yaw' -> nose_off_true icin).
    # ----------------------------------------------------------------
    def _log(self, phase, d):
        if not Cfg.LOG_ENABLE:
            return
        if self._log_f is None:                                  # ilk yazim -> dosya ac
            os.makedirs(_VERI_DIR, exist_ok=True)                # ciktilar veri/ altina
            fn = time.strftime("ucus_log_%Y%m%d_%H%M%S.csv")
            self._log_f = open(os.path.join(_VERI_DIR, fn), "w", newline="", encoding="utf-8")
            self._log_w = csv.writer(self._log_f)
            self._log_w.writerow(_LOG_COLS)
            self._log_f.flush()
        # --- truth + rotasyonlar (guvenli; hata olursa alan bos kalir) ---
        try:
            rot = self.drone.get_drone_rotation()
            d["drone_roll"], d["drone_pitch"] = float(rot[0]), float(rot[1])
        except Exception:
            pass
        try:
            trot = self.drone.get_target_rotation()             # ANA (bozuk) akis - guvenilmez
            d["tgt_roll"], d["tgt_pitch"], d["tgt_yaw"] = float(trot[0]), float(trot[1]), float(trot[2])
        except Exception:
            pass
        try:
            dbg = self.drone.get_debug_truth()
            if dbg.get("available"):
                tp = dbg["target"]["position"]; dp = dbg["drone"]["position"]
                d["true_tx"], d["true_ty"], d["true_tz"] = float(tp[0]), float(tp[1]), float(tp[2])
                d["true_dx"], d["true_dy"], d["true_dz"] = float(dp[0]), float(dp[1]), float(dp[2])
                d["gercek_mesafe"] = math.sqrt((tp[0]-dp[0])**2 + (tp[1]-dp[1])**2 + (tp[2]-dp[2])**2)
                dpos = d.get("drone_pos"); dyaw = d.get("drone_yaw")
                if dpos is not None and dyaw is not None:        # burun ile GERCEK hedef acisi (deg)
                    d["nose_off_true"] = math.degrees(
                        wrap_pi(math.atan2(tp[1] - dpos[1], tp[0] - dpos[0]) - dyaw))
        except Exception:
            pass
        d["phase"] = phase
        d["t_wall"] = time.time()

        def _c(x):
            if x is None:
                return ""
            if isinstance(x, (float, np.floating)):
                return round(float(x), 4)
            return x
        self._log_w.writerow([_c(d.get(k)) for k in _LOG_COLS])
        self._log_f.flush()

    def _log_early(self, phase, t, drone_pos, yaw_m, drone_yaw, v_own):
        # Erken-donus tikleri (TAKEOFF/DROPOUT/WARMUP): sadece meta+drone+uygulanan komut.
        if not Cfg.LOG_ENABLE:
            return
        self._log(phase, {
            "t_perf": t, "kaynak": self.kaynak, "none_count": self.none_count,
            "drone_x": drone_pos[0], "drone_y": drone_pos[1], "drone_z": drone_pos[2],
            "drone_yaw_deg": yaw_m, "drone_yaw_rad": drone_yaw,
            "vown_x": v_own[0], "vown_y": v_own[1],
            "thr_cmd": self.prev['thr'], "pitch_cmd": self.prev['pitch'],
            "roll_cmd": self.prev['roll'], "yaw_cmd": self.prev['yaw'],
            "drone_pos": drone_pos, "drone_yaw": drone_yaw,
        })

    # ----------------------------------------------------------------
    #  Debug olcum: J gercekten ham'dan iyi mi?
    # ----------------------------------------------------------------
    def _debug_olc(self):
        dbg = self.drone.get_debug_truth()
        if not dbg.get("available") or self.son_temiz is None: return
        gercek = np.array(dbg["target"]["position"])
        ham = np.array(self.son_ham)
        self.ham_hatalar.append(np.linalg.norm(ham - gercek))
        self.j_hatalar.append(np.linalg.norm(self.son_temiz - gercek))
        for ad in self.drone.get_active_corruption():
            self.bozukluk_sayac[ad] = self.bozukluk_sayac.get(ad, 0) + 1

    # ================================================================
    # GOREV 1: GPS VERILERIYLE TAKIP  (J temizleme + hedef hiz + turev)
    # ================================================================
    # ----------------------------------------------------------------
    #  J: bozuk hedef konumu temizle (sadece YENI telemetri gelince).
    #  self._fresh: bu cagride J'den YENI gecerli kestirim geldi mi? FAZ-1
    #  None yonetimi (hold vs dropout) bunu kullanir.
    # ----------------------------------------------------------------
    def _hedef_temizle(self):
        # GERCEK GPS modu: filtreyi atla, oyunun GERCEK hedef konumunu hedef al.
        if self.kaynak == "gercek":
            self.son_ham = self.drone.get_target_location()   # debug olcumu icin tut
            dbg = self.drone.get_debug_truth()
            if dbg.get("available"):
                p = np.array(dbg["target"]["position"], float)
                self.son_temiz = p
                self.son_z_anlik = float(p[2])                # gercekte lead yok -> ayni z
                self.son_xy_anlik = np.array([p[0], p[1]], float)  # carpisma-rotasi LOS'u icin
                self.son_hiz = self._gercek_hedef_hiz(p)      # hedef hizi (truth sonlu-fark)
                self._fresh = True                            # -> terminal vurus GERCEK modda da acilir
            else:
                self._fresh = False
            return self.son_temiz

        ham = self.drone.get_target_location()
        if ham != self.son_ham:               # yeni telemetri paketi
            self.son_ham = ham
            sonuc = self.filtre.guncelle(ham[0], ham[1], ham[2])
            if sonuc is not None:
                self.son_temiz = np.array(sonuc)   # 2sn lead'li (YATAY intercept icin)
                self._fresh = True            # YENI gecerli kestirim
                # J hedef hizini + ANLIK irtifayi da al. DIKEY icin lead'siz z kullanilir:
                # 2sn dikey lead, hedef dikey manevra yapinca irtifayi cok abartiyor (sim:
                # manevrada +55m sapma). Anlik z gercegi cok daha iyi takip eder.
                durum = self.filtre.durum_guduum()
                if durum is None:
                    self.son_hiz = None
                    self.son_z_anlik = float(self.son_temiz[2])   # fallback
                    self.son_xy_anlik = None
                else:
                    self.son_hiz = np.array(durum["vel"], float)
                    self.son_z_anlik = float(durum["pos"][2])     # lead'siz anlik irtifa
                    # lead'siz ANLIK yatay konum -> terminal vurus (carpisma-rotasi) LOS'u
                    # bunu kullanir; lead son_temiz'de degil, hedef hizini eslemede otomatik.
                    self.son_xy_anlik = np.array([durum["pos"][0], durum["pos"][1]], float)
            else:
                self._fresh = False           # isinma/donma -> kestirim yok
        else:
            self._fresh = False               # ratelimit ile donmus kare (yeni bilgi yok)
        return self.son_temiz                  # None olabilir (isinma)

    # ----------------------------------------------------------------
    #  GERCEK modda hedef hizi (cm/s, 3B): truth konum sonlu-fark + EMA.
    #  Carpisma-rotasi (v_des = v_hedef + V_CLOSE*LOS) icin gerekli; truth temiz
    #  oldugundan sonlu-fark guvenli.
    # ----------------------------------------------------------------
    def _gercek_hedef_hiz(self, p):
        now = time.perf_counter()
        if self._gt_prev_p is None or self._gt_prev_t is None:
            self._gt_prev_p = p.copy(); self._gt_prev_t = now
            return self._gt_vel
        dt = now - self._gt_prev_t
        if 1e-3 < dt < 0.5:
            raw = (p - self._gt_prev_p) / dt
            self._gt_vel = 0.7 * self._gt_vel + 0.3 * raw
            self._gt_prev_p = p.copy(); self._gt_prev_t = now
        elif dt >= 0.5:
            self._gt_prev_p = p.copy(); self._gt_prev_t = now
        return self._gt_vel

    # ----------------------------------------------------------------
    #  EMA-filtreli hata turevi (degisken update-rate'e dayanikli)
    # ----------------------------------------------------------------
    def _derivative(self, e, t):
        if self.e_prev is None:
            self.e_prev, self.t_prev = e, t
            return self.de
        dt = t - self.t_prev
        if dt > 1e-3:
            a = Cfg.DERIV_EMA
            for i in range(3):
                raw = (e[i] - self.e_prev[i]) / dt
                self.de[i] = (1.0 - a) * self.de[i] + a * raw
            self.e_prev, self.t_prev = e, t
        return self.de

    # ================================================================
    # GOREV 2: GORSEL TAKIP  (tespit koprusu + IBVS gorsel guduum)
    # ================================================================
    # ----------------------------------------------------------------
    #  GORSEL TESPIT KOPRUSU (thread-guvenli): server.dedektor_dongusu AGIR YOLO
    #  inference'i beyin_lock DISINDA kosar, sonucu beyin_lock ICINDE buraya yazar;
    #  adim() ayni kilit altinda _gorsel_tespit_oku ile okur -> inference tik'ten
    #  DECOUPLE (kontrol dongusu 50Hz akici kalir).
    #  det: {cx,cy,w,h,conf,W,H,t} | None  (gorsel_tespit.HedefDedektor.tespit_et)
    # ----------------------------------------------------------------
    # ----------------------------------------------------------------
    #  GUDUM PIPELINE SWITCH (test icin): hangi yol aktif?
    #    "OTO"    -> otomatik: N_LOCK tespitte gorsel kilitlenir, kayipta GPS'e doner
    #    "GPS"    -> ZORLA GPS: gorsel yol kapali (gorseldeysen GPS'e doner)
    #    "GORSEL" -> ZORLA GORSEL: kilidi atla, hemen gorsel; kayipta GPS'e DONMEZ
    # ----------------------------------------------------------------
    def set_vis_mode(self, mode):
        m = str(mode).upper()
        if m not in ("OTO", "GPS", "GORSEL"):
            return False
        self.vis_mode = m
        self._vis_pos_count = 0          # switch -> gorsel kilit/EMA temiz baslasin
        self._vis_lost_count = 0
        self._vis_ilan = False
        self.ibvs.sifirla()
        return True

    def set_gorsel_tespit(self, det):
        if det is not None:
            self.son_tespit = det
            self.son_tespit_t = det.get("t", time.perf_counter())
        # det None ise ESKI tespiti SILME: tek bos kare kilidi dusurmesin. Bayatlik
        # (VIS_STALE_S) _oku'da elenir; kayip histerezisini _vis_lost_count yonetir.

    def _gorsel_tespit_oku(self):
        """Bayat-olmayan son tespiti dondur; yoksa/bayatsa None (kayip mantigi devreye girer)."""
        det = self.son_tespit
        if det is None or self.son_tespit_t is None:
            return None
        if (time.perf_counter() - self.son_tespit_t) > Cfg.VIS_STALE_S:
            return None
        return det

    # ----------------------------------------------------------------
    #  GORSEL GUDUM (DUZ IBVS) - YONELIM YALNIZCA KAMERADAN.
    #  Gorsel temas VARKEN GPS/filtre YONELIMI KULLANILMAZ (yarisma kurali).
    #  tespit VAR -> ibvs.hesapla(bbox merkezi -> angle-mode komut).
    #  tespit YOK -> KADEMELI: (1) VIS_DEADRECKON_S kor-devam, (2) VIS_LOST_TO_GPS_S'e
    #  kadar hover (ararken bekle), (3) o da asilirsa GPS guduumune GERI DON (re-acquire)
    #  -> durumu ARAMA yap, gorsel kilidi sifirla, None dondur (adim() GPS yoluna duser).
    #  return: (throttle,pitch,roll,yaw) | None (=GPS'e don). _send rate-limit'ler.
    # ----------------------------------------------------------------
    def _gorsel_guduum(self, tespit, t, revert_izin=True):
        # revert_izin=False (manuel GORSEL switch): kayipta GPS'e DONME, hover'da kal.
        if tespit is not None:
            self._vis_lost_count = 0
            bbox_merkez = (tespit["cx"], tespit["cy"])
            bbox_boyut  = (tespit["w"], tespit["h"])
            return self.ibvs.hesapla(bbox_merkez, tespit["W"], tespit["H"],
                                     bbox_boyut, Cfg, dt=Cfg.DT)
        # --- KAYIP: kademeli tepki ---
        self._vis_lost_count += 1
        lost_s = self._vis_lost_count * Cfg.DT
        if lost_s <= Cfg.VIS_DEADRECKON_S:
            return self.ibvs.kor_devam(Cfg)      # 1) son EMA yonuyle KISA kor-devam
        if (not revert_izin) or Cfg.VIS_LOST_TO_GPS_S <= 0 or lost_s <= Cfg.VIS_LOST_TO_GPS_S:
            return 0.0, 0.0, 0.0, 0.0            # 2) hover: ararken bekle (manuel GORSEL'de KAL)
        # 3) UZUN kayip (yalnizca OTO) -> GPS guduumune GERI DON (yeniden yaklas, yeniden kilitle)
        print("[GORSEL] Hedef %.1fs kayip -> GPS guduumune GERI DONULDU (yeniden yaklas)." % lost_s)
        self.durum = "ARAMA"
        self._vis_pos_count = 0
        self._vis_lost_count = 0
        self._vis_ilan = False
        self.ibvs.sifirla()
        return None                              # -> adim() GPS yoluna DUSER (bu tik)

    # ----------------------------------------------------------------
    #  GORSEL_GUDUM logu (phase="VISUAL"): meta+drone+uygulanan komut + normalize
    #  gorsel hata (vis_ex/ey), gordu/conf/area. _LOG_COLS'daki vis_* kolonlarini
    #  doldurur; digerleri bos kalir (sema-guvenli; analiz_ucus.py etkilenmez).
    # ----------------------------------------------------------------
    def _log_gorsel(self, t, drone_pos, yaw_m, drone_yaw, v_own, tespit):
        if not Cfg.LOG_ENABLE:
            return
        d = {
            "t_perf": t, "kaynak": self.kaynak, "durum": self.durum,
            "none_count": self.none_count,
            "drone_x": drone_pos[0], "drone_y": drone_pos[1], "drone_z": drone_pos[2],
            "drone_yaw_deg": yaw_m, "drone_yaw_rad": drone_yaw,
            "vown_x": v_own[0], "vown_y": v_own[1],
            "thr_cmd": self.prev['thr'], "pitch_cmd": self.prev['pitch'],
            "roll_cmd": self.prev['roll'], "yaw_cmd": self.prev['yaw'],
            "drone_pos": drone_pos, "drone_yaw": drone_yaw,
            "vis_ex": self.ibvs.ex_f, "vis_ey": self.ibvs.ey_f,
            "vis_gordu": 1 if tespit is not None else 0,
        }
        if tespit is not None:
            d["vis_conf"] = float(tespit.get("conf", 0.0))
            W = float(tespit.get("W", 0) or 0); H = float(tespit.get("H", 0) or 0)
            if W > 1 and H > 1:
                d["vis_area"] = (float(tespit["w"]) * float(tespit["h"])) / (W * H)
        self._log("VISUAL", d)

    # ================================================================
    # GOREV 3: GUDUM / STRIKE  (kendi hiz + kamera FOV/handoff hook stub)
    # ================================================================
    # ----------------------------------------------------------------
    #  Kendi YATAY hiz vektoru (cm/s, dunya): temiz konum sonlu-fark + EMA.
    #  Terminal vurus (carpisma-rotasi) hiz-izleme icin kullanir.
    # ----------------------------------------------------------------
    def _own_hiz(self, pxy, t):
        if self._own_pxy is None or self._own_tv is None:
            self._own_pxy = pxy.copy(); self._own_tv = t
            return self._own_v
        dt = t - self._own_tv
        if 1e-3 < dt < 0.5:
            raw = (pxy - self._own_pxy) / dt
            self._own_v = 0.7 * self._own_v + 0.3 * raw
            self._own_pxy = pxy.copy(); self._own_tv = t
        elif dt >= 0.5:                                # bayat -> resetle
            self._own_pxy = pxy.copy(); self._own_tv = t
        return self._own_v

    # ================================================================
    # ORTAK: ORKESTRASYON / DONGU  (adim tum gorevleri sirayla kosar)
    #   adim() akisi: KALKIS -> [G2 gorsel kesme] -> None yonetimi ->
    #   [G1 GPS yaklasma + HANDOFF] -> [G3 strike: GPS_TERMINAL_STRIKE=True] -> _send
    # ================================================================
    # ----------------------------------------------------------------
    #  TEK kontrol adimi (donguude bir kez cagrilir) - FAZ-1 guduum
    # ----------------------------------------------------------------
    def adim(self):
        drone_pos = np.array(self.drone.get_drone_location())   # TEMIZ (cm)
        # Oyun yaw'i DERECE verir; guduum RADYAN bekler -> cevir.
        yaw_m = self.drone.get_drone_rotation()[2]
        drone_yaw = math.radians(yaw_m) if Cfg.ROT_IN_DEGREES else yaw_m
        t = time.perf_counter()
        v_own = self._own_hiz(drone_pos[:2], t)                 # kendi yatay hiz (cm/s, dunya)

        # 1) J ile bozuk hedefi temizle (self._fresh: yeni kestirim geldi mi?)
        self._hedef_temizle()
        if self.debug_olc: self._debug_olc()

        # 2) KALKIS (non-blocking): arama irtifasina tirman, sonra yaklasmaya gec.
        if not self._kalkis_done:
            if drone_pos[2] >= Cfg.SEARCH_ALT - Cfg.ALT_TOL:
                self._kalkis_done = True
            else:
                self._send(Cfg.TAKEOFF_THR, 0.0, 0.0, 0.0)      # tirman, seviye
                self._log_early("TAKEOFF", t, drone_pos, yaw_m, drone_yaw, v_own)
                return

        # 2.5) GUDUM PIPELINE SECIMI (switch: self.vis_mode) + GORSEL kesme.
        #      OTO   : conf>=VIS_CONF_MIN kareler ard arda VIS_N_LOCK olunca GORSEL'e kilitlenir;
        #              kayip VIS_LOST_TO_GPS_S'i asarsa GPS'e geri doner (re-acquire).
        #      GPS   : gorsel yol KAPALI (gorseldeysen GPS'e doner) -> hep GPS.
        #      GORSEL: kilidi ATLA, hemen GORSEL; kayipta GPS'e DONME (zorlanmis).
        #      GORSEL kilitliyken asagidaki TUM GPS yonelimi ATLANIR (return) -> gorsel
        #      temas VARKEN GPS yonelimi kullanilmaz. _send prev surekliligi -> sarsintisiz.
        tespit = self._gorsel_tespit_oku()
        mod = getattr(self, "vis_mode", "OTO")
        if mod == "GPS":
            if self.durum == "GORSEL_GUDUM":              # manuel: gorselden GPS'e don
                self.durum = "ARAMA"; self._vis_ilan = False
            self._vis_pos_count = 0
        elif mod == "GORSEL":
            if self.durum != "GORSEL_GUDUM":              # manuel: hemen gorsel (kilit sayaci yok)
                self.durum = "GORSEL_GUDUM"; self._vis_lost_count = 0
                if not self._vis_ilan:
                    print("[GORSEL] Manuel switch -> GORSEL GUDUM (GPS yonelimi kapali).")
                    self._vis_ilan = True
        else:  # OTO - otomatik kilit: YAKINLIK + YOLO kilidi (ikisi birden)
            if self.durum != "GORSEL_GUDUM":
                if tespit is not None and float(tespit.get("conf", 0.0)) >= Cfg.VIS_CONF_MIN:
                    self._vis_pos_count += 1
                else:
                    self._vis_pos_count = 0
                # HANDOFF: GPS hedefe YETERINCE YAKLASMIS OLMALI (self.handoff = d_h<HANDOFF_RANGE,
                # onceki tikte hesaplanir) VE YOLO kilidi (ard arda VIS_N_LOCK gecerli tespit).
                # Ikisi birden saglaninca saldiri KAMERAYA devredilir; oncesinde GPS yaklasmaya
                # devam eder (uzaktan yanlis-kilit yok).
                # SIMDILIK KAPALI (Cfg.AUTO_VISUAL_HANDOFF=False): kilit+yakinlik saglansa
                # bile GPS takibe DEVAM eder, gorsele gecmez. Manuel GORSEL switch etkilenmez.
                if (Cfg.AUTO_VISUAL_HANDOFF
                        and self._vis_pos_count >= Cfg.VIS_N_LOCK and self.handoff):
                    self.durum = "GORSEL_GUDUM"
                    if not self._vis_ilan:
                        print("[GORSEL] Yakinlik + gorsel kilit saglandi -> GPS YAKLASMAYI BIRAKTI, "
                              "yonelim/saldiri yalnizca KAMERA verisiyle.")
                        self._vis_ilan = True

        if self.durum == "GORSEL_GUDUM":
            sonuc = self._gorsel_guduum(tespit, t, revert_izin=(mod == "OTO"))
            if sonuc is not None:
                thr, pitch, roll, yaw = sonuc
                self._send(thr, pitch, roll, yaw)
                self._log_gorsel(t, drone_pos, yaw_m, drone_yaw, v_own, tespit)
                return
            # sonuc None (yalnizca OTO) -> gorsel UZUN kayip -> GPS yolu BU tik calisir

        # 3) None yonetimi: normal donmus kare (hold) vs dropout (loiter)
        if not self._fresh:
            self.none_count += 1
            if self.none_count <= Cfg.HOLD_TICKS and self.son_temiz is not None:
                est = self.son_temiz                            # son 2sn-lead kestirimi tut
            else:
                self._loiter()                                  # uzun None -> dropout -> bekle
                self._log_early("DROPOUT", t, drone_pos, yaw_m, drone_yaw, v_own)
                return
        else:
            self.none_count = 0
            est = self.son_temiz

        if est is None:                                          # isinma: henuz kestirim yok
            self._loiter()
            self._log_early("WARMUP", t, drone_pos, yaw_m, drone_yaw, v_own)
            return
        self.last_est = est

        # YATAY nisan noktasi:
        #   - GPS_TERMINAL_STRIKE=True (ram): 2sn lead'li kestirim (est) = intercept (eski davranis).
        #   - approach-only (ram KAPALI): B) ANTI-OVERSHOOT STANDOFF -> hedefi GECMEDEN onunde
        #     dur. KISA lead (APPROACH_LEAD_S) ile nisan (savrulmayi onler); pozisyon KOMUTU
        #     hedefe DEGIL, APPROACH_STANDOFF kadar GERIYE surulur -> drone standoff'ta paceler.
        # DIKEY: lead'siz anlik irtifa (lead dikeyde irtifa asimina/yukari kacmaya yol aciyor).
        z_ref = self.son_z_anlik if self.son_z_anlik is not None else float(est[2])
        # KAMERA CERCEVELEME: hedefi kadrajda merkezin BIRAZ USTUNDE tut. z_ref'i (hedef
        # irtifasi) APPROACH_ALT_OFFSET kadar ASAGI cek -> drone hedefin altinda dengelenir
        # -> 25 derece yukari-tilt kamerada hedef LOS'u yukselir -> kadrajda yukari kayar.
        # Yalnizca yaklasma-only'de (ram KAPALI); carpma geometrisini bozmasin.
        if not Cfg.GPS_TERMINAL_STRIKE:
            z_ref -= Cfg.APPROACH_ALT_OFFSET
        ez = float(z_ref - drone_pos[2])
        if (not Cfg.GPS_TERMINAL_STRIKE) and self.son_xy_anlik is not None and self.son_hiz is not None:
            tx = float(self.son_xy_anlik[0]) + Cfg.APPROACH_LEAD_S * float(self.son_hiz[0])  # kisa lead
            ty = float(self.son_xy_anlik[1]) + Cfg.APPROACH_LEAD_S * float(self.son_hiz[1])
        else:
            tx, ty = float(est[0]), float(est[1])                 # ram / fallback: 2sn lead
        ex = tx - float(drone_pos[0])                             # HEDEFE hata (yaw/handoff/FOV/log)
        ey = ty - float(drone_pos[1])
        d_h = math.hypot(ex, ey)
        # POZISYON KOMUT hatasi (PD bunu surer): ram'de hedefe git; approach-only'de standoff'a.
        if not Cfg.GPS_TERMINAL_STRIKE:
            if d_h > 1e-6:
                _ux, _uy = ex / d_h, ey / d_h
                _dcmd = d_h - Cfg.APPROACH_STANDOFF              # +: yaklas, 0: dur, -: cok yakin -> geri cekil
                ex_cmd, ey_cmd = _ux * _dcmd, _uy * _dcmd
            else:
                ex_cmd = ey_cmd = 0.0
        else:
            ex_cmd, ey_cmd = ex, ey

        # ZORUNLU None-init (ucus logu icin): strike/alc bloklari calismazsa bile bu
        # degiskenler 559'daki log dict'inde referanslanir -> NameError'i onle (yoksa
        # beyin_lock'taki try/except o log satirini sessizce yutar).
        ex_s = ey_s = d_s = ux = uy = v_close = vdx = vdy = ax = ay = a_fwd = a_right = None
        alc_oncelik = None

        # 4) HANDOFF (histerezisli) -> durum: ARAMA / KILIT
        if not self.handoff and d_h < Cfg.HANDOFF_RANGE:
            self.handoff = True
        elif self.handoff and d_h > Cfg.HANDOFF_EXIT:
            self.handoff = False
            self.handoff_announced = False
        self.durum = "KILIT" if self.handoff else "ARAMA"

        # 5) turev (EMA) - YATAY komut hatasi (standoff'lu) uzerinden; dikey ez uzerinden
        de = self._derivative((ex_cmd, ey_cmd, ez), t)

        # 6) yatay: KOMUT hatasini (standoff) ve turevini govde cercevesine cevir
        e_fwd, e_right = world_to_body(ex_cmd, ey_cmd, drone_yaw)
        de_fwd, de_right = world_to_body(de[0], de[1], drone_yaw)

        pitch_raw = Cfg.PITCH_SIGN * (Cfg.KP_H * e_fwd   + Cfg.KD_H * de_fwd)
        roll_raw  = Cfg.ROLL_SIGN  * (Cfg.KP_H * e_right + Cfg.KD_H * de_right)

        # 7) mesafe-tabanli hiz tavani -> komut buyuklugunu kisitla (overshoot guard)
        vcap = speed_cap(d_h)
        spd = self.drone.get_drone_speed()                      # skaler cm/s (yaklasik)
        if spd > vcap:                                          # tavandan hizliysa ileri itiyi fren et
            brake = clamp((spd - vcap) / max(vcap, 1.0), 0.0, 1.0)
            pitch_raw *= (1.0 - 0.8 * brake)
        mag_scale = clamp(vcap / Cfg.V_CAP_FAR, 0.15, 1.0)      # yakinda kucuk tavan

        pitch_raw = clamp(pitch_raw, -Cfg.PITCH_MAX, Cfg.PITCH_MAX) * mag_scale
        roll_raw  = clamp(roll_raw,  -Cfg.ROLL_MAX,  Cfg.ROLL_MAX)  * mag_scale

        # 7b) DIKEY-YATAY AYRISTIRMA DUZELTMESI (tani verisiyle kanitlandi):
        #     Drone hedefin irtifasini ASTIGINDA (ez<0) hizli ileri-ucus YUKARI TASIMA
        #     uretip alcalmayi engelliyordu (THR=-0.40'a ragmen +3 m/s tirmanis). Cozum:
        #     ne kadar ustteyse kovalamayi (pitch/roll) o kadar KIS -> tasima dussun ->
        #     drone alcalabilsin. Hedef irtifasina donunce tam kovalama geri gelir.
        if ez < 0.0:
            alc_oncelik = clamp(1.0 + ez / 800.0, 0.15, 1.0)   # ez=-8 m'de %15'e iner
            pitch_raw *= alc_oncelik
            roll_raw  *= alc_oncelik

        # 8) irtifa (PID) - Z_SIGN ile dikey yon. P: KP_Z*ez, I: kalici acigi kapatir
        #    (ileri-ucus tasimasina karsi ~14 m ustte dengelenmeyi onler), D: KD_Z*de[2].
        #    KP_Z/KD_Z DEGISMEZ; THR_DN=-1.0 tam inme yetkisi.
        #    Anti-windup: integrali sadece hedefe MAKUL yakinken (|ez|<band) biriktir ve
        #    clamp'le; uzaktayken (tirmanis) sifirla ki windup olmasin.
        if abs(ez) < Cfg.INT_Z_BAND:
            self._ez_int = clamp(self._ez_int + ez * Cfg.DT, -Cfg.INT_Z_MAX, Cfg.INT_Z_MAX)
        else:
            self._ez_int = 0.0
        thr_raw = clamp(Cfg.Z_SIGN * (Cfg.KP_Z * ez + Cfg.KI_Z * self._ez_int + Cfg.KD_Z * de[2]),
                        Cfg.THR_DN, Cfg.THR_UP)

        # 9) yaw: nazikce burnu hedefe cevir (handoff'ta kamera ortalansin)
        bearing = math.atan2(ey, ex)
        yaw_err = deadband(wrap_pi(bearing - drone_yaw), Cfg.YAW_DEADBAND)
        yaw_raw = Cfg.YAW_SIGN * clamp(Cfg.KP_YAW * yaw_err, -Cfg.YAW_MAX, Cfg.YAW_MAX)

        # 10) deadband (cok yakinda yatay jitter onle)
        if d_h < Cfg.POS_DEADBAND:
            pitch_raw = 0.0
            roll_raw = 0.0

        # 10b) TERMINAL VURUS (COMMIT / RAM) - hedefin ICINE dal, delip GEC (hit).
        #      >>> VARSAYILAN KAPALI (Cfg.GPS_TERMINAL_STRIKE=False): GPS VURMAZ, sadece yaklasir;
        #          saldiri KAMERA verisiyle (gorsel faz) yapilir. Blok korunur, bayrakla acilir. <<<
        #      v_des = v_hedef + v_close*LOS.  v_close = clamp(KP_CLOSE*d, V_CLOSE_MIN, V_CLOSE):
        #      uzakta hizli, YAKINDA TABAN'da (V_CLOSE_MIN) kalir -> temasta 0'a inmez, drone
        #      hedefin icine itmeye devam eder (GERI ATILMA yok). Hedef hizini esledigimiz
        #      icin lead OTOMATIK. ivme = KV*(v_des - v_own). Cok yakinda (d_s<COMMIT_RANGE)
        #      YANAL (LOS'a dik) ivme kisilir -> LOS singula rite salinimi kovalanmaz, DUZ dalinir.
        if (Cfg.GPS_TERMINAL_STRIKE and d_h < Cfg.STRIKE_RANGE
                and self.son_hiz is not None and self.son_xy_anlik is not None):
            # LOS = lead'siz ANLIK hedefe (carpisma icin gercek yon; lead son_temiz'de DEGIL).
            ex_s = float(self.son_xy_anlik[0] - drone_pos[0])
            ey_s = float(self.son_xy_anlik[1] - drone_pos[1])
            d_s = math.hypot(ex_s, ey_s)
            ux, uy = ex_s / max(d_s, 1e-6), ey_s / max(d_s, 1e-6)      # LOS birim (dunya)
            # BURUN/KAMERA DUZELTMESI: terminalde burun ANLIK hedefe doner (2sn-lead
            # noktasina DEGIL). Carpisma lead'i hiz-eslemede ZATEN var (v_des =
            # v_hedef + v_close*LOS); burnu lead'e cevirmek kamerayi gercek hedeften
            # kaciriyordu (yakin mesafede manevrali hedefte ~50 dereceye varan sapma
            # -> gorsel temas kaybi). Kamera gorsel fazin sensorudur; hep hedefte kalsin.
            bearing = math.atan2(ey_s, ex_s)
            yaw_err = deadband(wrap_pi(bearing - drone_yaw), Cfg.YAW_DEADBAND)
            yaw_raw = Cfg.YAW_SIGN * clamp(Cfg.KP_YAW * yaw_err, -Cfg.YAW_MAX, Cfg.YAW_MAX)
            v_close = clamp(Cfg.KP_CLOSE * d_s, Cfg.V_CLOSE_MIN, Cfg.V_CLOSE)  # TABAN'li -> ram
            vdx = float(self.son_hiz[0]) + v_close * ux               # istenen hiz (cm/s, dunya)
            vdy = float(self.son_hiz[1]) + v_close * uy
            # 3D CARPMA (DIKEY): hedefin uzerinden/altindan GECMESIN -> mevcut irtifa-PID'ine
            # dikey KAPANIS feedforward'u EKLE (PID'i ezme -> pozisyon+lift telafisi korunur).
            # ez=dikey hata, d3d=3B mesafe, losz=LOS dikey bileseni. hedefin dikey hizini esle
            # (son_hiz_z) + v_close*losz ile dikeyi yatayla SENKRON kapat. throttle olcegi: /VZ_MAX.
            d3d = math.hypot(d_s, ez)
            losz = ez / max(d3d, 1e-6)
            thr_ff = (float(self.son_hiz[2]) + v_close * losz) / Cfg.VZ_MAX
            thr_raw = clamp(thr_raw + Cfg.Z_SIGN * thr_ff, Cfg.THR_DN, Cfg.THR_UP)
            ax = Cfg.KV_STRIKE * (vdx - float(v_own[0]))               # ivme = KV*(v_des - v_own)
            ay = Cfg.KV_STRIKE * (vdy - float(v_own[1]))
            if d_s < Cfg.COMMIT_RANGE:                                 # COMMIT: yanal ivmeyi kis
                along = ax * ux + ay * uy                              # LOS boyunca (ram) bilesen
                kperp = clamp(d_s / Cfg.COMMIT_RANGE, 0.25, 1.0)       # temasta %25'e iner
                ax = along * ux + (ax - along * ux) * kperp
                ay = along * uy + (ay - along * uy) * kperp
            am = math.hypot(ax, ay)
            if am > Cfg.A_MAX_STRIKE:                                  # TOPLAM ivme tavani
                ax *= Cfg.A_MAX_STRIKE / am; ay *= Cfg.A_MAX_STRIKE / am
            a_fwd, a_right = world_to_body(ax, ay, drone_yaw)          # dunya -> govde
            pitch_raw = Cfg.PITCH_SIGN * clamp(a_fwd  / Cfg.A_MAX_STRIKE, -1.0, 1.0) * Cfg.STRIKE_TILT
            roll_raw  = Cfg.ROLL_SIGN  * clamp(a_right / Cfg.A_MAX_STRIKE, -1.0, 1.0) * Cfg.STRIKE_TILT

        # --- TESHIS: irtifa kacma sorununu olcmek icin (Cfg.DEBUG_Z=False ile kapat) ---
        if Cfg.DEBUG_Z:
            self._dbgz = getattr(self, "_dbgz", 0) + 1
            if self._dbgz % 25 == 0:                         # ~2 Hz
                dbg = self.drone.get_debug_truth()
                ztrue = (dbg["target"]["position"][2] if dbg.get("available") else None)
                raw_z = (self.son_ham[2] if self.son_ham is not None else None)
                ztrue_s = f"{ztrue:8.0f}" if ztrue is not None else "    NA  "
                raw_s   = f"{raw_z:8.0f}" if raw_z is not None else "    NA  "
                corr = ",".join(self.drone.get_active_corruption()) or "-"
                print(f"[Z] dz={drone_pos[2]:8.0f} zref={z_ref:8.0f} ztrue={ztrue_s} "
                      f"zlead={float(est[2]):8.0f} rawz={raw_s} ez={ez:+7.0f} dez={de[2]:+7.0f} "
                      f"thr={thr_raw:+.2f} spd={spd:6.0f} pit={pitch_raw:+.2f} dh={d_h:7.0f} "
                      f"{self.durum} corr=[{corr}]")

        if self.handoff and not self.handoff_announced:
            print(f"[HANDOFF] tespit menzilinde (mesafe<{Cfg.HANDOFF_RANGE:.0f}cm). Gorus devralabilir.")
            self.handoff_announced = True

        self._send(thr_raw, pitch_raw, roll_raw, yaw_raw)

        # --- UCUS LOGU: ana yol (APPROACH/STRIKE) tam teshis satiri ---
        if Cfg.LOG_ENABLE:
            mod = "STRIKE" if (Cfg.GPS_TERMINAL_STRIKE and d_h < Cfg.STRIKE_RANGE
                               and self.son_hiz is not None
                               and self.son_xy_anlik is not None) else "APPROACH"
            sh = self.son_hiz; sx = self.son_xy_anlik; sm = self.son_ham
            self._log(mod, {
                "t_perf": t, "kaynak": self.kaynak, "durum": self.durum,
                "handoff": int(self.handoff), "fresh": int(self._fresh), "none_count": self.none_count,
                "drone_x": drone_pos[0], "drone_y": drone_pos[1], "drone_z": drone_pos[2],
                "drone_yaw_deg": yaw_m, "drone_yaw_rad": drone_yaw, "drone_speed": spd,
                "vown_x": v_own[0], "vown_y": v_own[1],
                "est_x": est[0], "est_y": est[1], "est_z": est[2], "z_ref": z_ref,
                "xy_anlik_x": (sx[0] if sx is not None else None),
                "xy_anlik_y": (sx[1] if sx is not None else None),
                "son_z_anlik": self.son_z_anlik,
                "son_hiz_x": (sh[0] if sh is not None else None),
                "son_hiz_y": (sh[1] if sh is not None else None),
                "son_hiz_z": (sh[2] if sh is not None else None),
                "son_ham_x": (sm[0] if sm is not None else None),
                "son_ham_y": (sm[1] if sm is not None else None),
                "son_ham_z": (sm[2] if sm is not None else None),
                "ex": ex, "ey": ey, "ez": ez, "d_h": d_h, "e_fwd": e_fwd, "e_right": e_right,
                "vcap": vcap, "mag_scale": mag_scale, "alc_oncelik": alc_oncelik, "ez_int": self._ez_int,
                "d_s": d_s, "v_close": v_close, "vdx": vdx, "vdy": vdy, "ax": ax, "ay": ay,
                "a_fwd": a_fwd, "a_right": a_right,
                "bearing": bearing, "yaw_err": yaw_err,
                "thr_raw": thr_raw, "pitch_raw": pitch_raw, "roll_raw": roll_raw, "yaw_raw": yaw_raw,
                "thr_cmd": self.prev['thr'], "pitch_cmd": self.prev['pitch'],
                "roll_cmd": self.prev['roll'], "yaw_cmd": self.prev['yaw'],
                "drone_pos": drone_pos, "drone_yaw": drone_yaw,   # _log: truth + nose_off_true icin
            })

    # ----------------------------------------------------------------
    #  Gercek oyun ana donguusu
    # ----------------------------------------------------------------
    def calistir(self):
        if not self.drone.connect():
            print("Baglanti kurulamadi (oyun acik ve Play modunda mi?)")
            return
        self.drone.set_arm(True)
        print("FAZ 1: GNSS ile yaklasma basladi. (Filtre warm-up'inda hover eder.)")
        try:
            while True:
                self.adim()
                time.sleep(Cfg.DT)   # 50 Hz
        except KeyboardInterrupt:
            self.drone.set_control_surfaces(0.0, 0.0, 0.0, 0.0, True)   # hover ile birak
            self.drone.disconnect()

    # ----------------------------------------------------------------
    #  Debug ozet (test sonrasi)
    # ----------------------------------------------------------------
    def ozet(self):
        if not self.ham_hatalar:
            return "Debug olcum yok."
        h = np.array(self.ham_hatalar)/100; j = np.array(self.j_hatalar)/100
        s = []
        s.append(f"Ham hedef hatasi : {h.mean():.1f} m")
        s.append(f"J hedef hatasi   : {j.mean():.1f} m")
        s.append(f"J kazanci        : %{100*(h.mean()-j.mean())/h.mean():.0f}  "
                 f"({'J IYI' if j.mean()<h.mean() else 'J KOTU!'})")
        s.append(f"Aktif bozukluklar: {self.bozukluk_sayac}")
        return "\n".join(s)

# -*- coding: utf-8 -*-
"""
HAMIDIYE - GORSEL PNG GUDUMU  (bbox -> LOS -> oransal seyrusefer carpisma rotasi)
================================================================================
Gorsel temas SONRASI terminal guduum. IBVS (bbox-merkezleme servo) yalnizca hedefi
kadrajda tutar; bu modul ise hedefin GIDECEGI noktayi kesen bir CARPISMA ROTASI ucar
(PN: "gorus hatti donusunu sifira sur"). Kanit/matematik png_sim/ paketinde tam-durum
formunda dogrulandi; burada YZ modelinin bbox ciktisindan (yalniz aci + pinhole menzil)
ayni yasa uretilir. png_sim IMPORT EDILMEZ (o paketin kendi bagimliliklari var); PN
matematigi bu dosyada bagimsiz ve takimca aciklanabilir sekilde yeniden yazildi.

YARISMA KURALI (KATI): gorsel temas SAGLANDIKTAN SONRA hareket komutu YALNIZCA GORSEL
VERIDEN turetilir. Yon (LOS), menzil (pinhole/bbox), kapanma hizi, dikey ayrim — HEPSI
kameradan. GPS/J-filtre verisi (yon YA DA buyukluk) bu fazda KULLANILMAZ; kullanmak
DISKALIFIYE sebebidir. (Eski _j_fallback menzil/Vc yedegi 2026-07-07 KALDIRILDI.)
Menzil gecersizken (bbox cok kucuk/kenar) eski gorsel R_f korunur; GPS'e BASVURULMAZ.

MATEMATIK
---------
1) Piksel -> DUNYA LOS birim vektoru (u_hat):
     fx = (W/2)/tan(HFOV/2)  [pose.geometri.fx_from_hfov]
     d_cam = [1, (cx-W/2)/fx, -(cy-H/2)/fx]   (projekte()'nin tersi; UE kamera lokali
                                               x=ileri, y=saga, z=yukari)
     _, R_cam = geometri.kamera_pozu(drone_pos, (roll,pitch,yaw), tilt=VIS_TILT_DEG)
     u_hat = normalize(R_cam @ d_cam)
   Tam tan haritasi + tam tutum (roll/pitch/yaw) kullanildigi icin govde YATARKEN
   (PN roll manevrasinda) LOS bozulmaz -> IBVS'e gore kritik ustunluk.

2) Menzil (pinhole): R = fx * KANAT_ACIKLIGI / max(w_px, h_px).
   Aspect yanliligi: hedef tam yandan gorununce yatay izdusum kanat(171.8) yerine
   govde(110) olur -> R en fazla ~x1.56 fazla tahmin edilir. PN buna dayaniklidir:
   Omega menzilsizdir (yalniz aci), menzil yanliligi yalniz Vc'ye ORANSAL girer ->
   a = N*Vc*(Omega x u) sadece sabit bir carpanla olceklenir (etkin N degisimi gibi).
   Ayrica PN carpisma rotasinda hedef cogunlukla ON/ARKA aspect'te gorunur.

3) Kapanma hizi:  Vc = -(R - R_onceki)/dt      (+ = yaklasiyoruz), EMA.
4) LOS donme vektoru:  Omega = (u_onceki x u)/dt , bilesen clamp +-OMEGA_MAX, EMA.
   (Kalman yerine EMA+clamp: tek parametre, jüriye aciklanabilir; clamp tek-kare
    YOLO sicramasini oldurur.)
5) PN komutu (dunya, cm/s^2):
     a_pn  = N * Vc * (Omega x u_hat)                       (yanal; u'ya dik)
     a_los = KV * (clamp(KP*R, VC_MIN, VC_CAP) - Vc) * u    (LOS-boyu kapanma)
     Vc<=0 (aciliyoruz) ise once burnu cevir: a += A_MAX * u
     |a| <= A_MAX  (yon koruyarak kirp)
6) Commit (terminal): R < COMMIT_R -> yanal bilesen kperp=clamp(R/COMMIT_R,LAT,1) ile
   kisilir (temasta LOS acisal hizi patlar; kovalamayi birak, DUZ dal). R<300cm veya
   bbox alan orani>0.5 -> son komutu DONDUR (saf ram). Vurus latch'i (<3m) server'da.
7) TAKIP modu (vurus_izin=False; sartname 6.1.2/6.1.4 kilit isteri dolmadan):
   ana_kontrol alt-FSM'i (YAKLASMA->TAKIP->TERMINAL) gecirir. Bu modda commit-freeze
   ve Vc<=0 itisi KAPALI; kapanma kanali MENZIL TUTMA olur:
     v_close_des = clamp(KP*(R - R_hold), -VC_CAP, +VC_CAP)   (VC_MIN tabani yok)
     R_hold = fx(1.0) * SPAN / HOLD_PCT   (bbox'i HOLD_PCT'te tutan pinhole menzili)
   PN yanal + yaw AYNEN calisir -> hedef kadrajda merkezde tutulur (kilit penceresi
   dolarken kontrolsuz yakinlasma olmaz). vurus_izin=True yolu eski davranisin aynisi.

KRITIK KENAR DURUMU: server ayni det'i VIS_STALE_S boyunca sunar; 50 Hz hesapla()
ayni kareyi defalarca gorur. R/Vc/Omega YALNIZ det["t"] DEGISINCE guncellenir;
diger tiklerde filtreli durum aynen kullanilir (yoksa dt->0, Omega patlar).

BILINEN KISITLAR (koda gomulu):
  - KAMERA_TILT_DEG=25 pose/geometri.py'de DOGRULANMAMIS placeholder -> LOS dikeyinde
    sabit yanlilik; pose/kalibre.py netlestirene dek EMA'lar tolere eder.
  - Tespit gecikmesi (~50-100ms) ile anlik tutum tam eslesmez -> sinirli yanlilik.
Parametreler disaridan `p` (Cfg) ile gelir; ana_kontrol IMPORT EDILMEZ (donusel yok).
"""
import math
import numpy as np

from pose import geometri


def clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x


def _clip_norm(vec, max_norm):
    """Vektoru YONUNU KORUYARAK |vec| <= max_norm olacak sekilde kirp."""
    n = float(np.linalg.norm(vec))
    if n > max_norm and n > 0.0:
        return vec * (max_norm / n)
    return vec


def _world_to_body(ex, ey, yaw_rad):
    """Dunya yatay vektoru govde cercevesine (ileri, sag). ana_kontrol.world_to_body
    ile AYNI (donusel import olmasin diye lokal kopya; ibvs_guidance deseni)."""
    c, s = math.cos(yaw_rad), math.sin(yaw_rad)
    e_fwd = ex * c + ey * s
    e_right = ex * s - ey * c
    return e_fwd, e_right


# ---------------------------------------------------------------------------
#  SAF FONKSIYONLAR (test edilebilir; sinif durumundan bagimsiz)
# ---------------------------------------------------------------------------
def piksel_to_los(cx, cy, W, H, drone_pos, drone_rot_rpy, tilt_deg=None):
    """bbox merkez pikseli -> DUNYA cercevesi LOS birim vektoru (np.array(3)).
    projekte()'nin tersi; kamera pozu tam tutumdan (roll,pitch,yaw) kurulur."""
    W = float(W); H = float(H)
    fx = float(geometri.fx_from_hfov(W))
    d_cam = np.array([1.0, (cx - W / 2.0) / fx, -(cy - H / 2.0) / fx])
    _, R_cam = geometri.kamera_pozu(drone_pos, drone_rot_rpy, tilt_deg=tilt_deg)
    d_world = R_cam @ d_cam
    n = float(np.linalg.norm(d_world))
    return d_world / n if n > 1e-9 else d_world


def menzil_pinhole(w_px, h_px, W, span_cm):
    """R = fx * kanat_acikligi / max(w_px, h_px)  [cm]. bbox ne kadar buyukse o kadar yakin."""
    s_px = max(float(w_px), float(h_px))
    if s_px < 1e-6:
        return None
    fx = float(geometri.fx_from_hfov(float(W)))
    return fx * float(span_cm) / s_px


# ---------------------------------------------------------------------------
#  PNG GORSEL GUDUM SINIFI
# ---------------------------------------------------------------------------
class AvciPNGGuduum:

    def __init__(self):
        self.sifirla()

    def sifirla(self):
        """Re-acquire / gorev basi: tum filtre ve kor-devam durumunu temizle."""
        self.u_hat = None            # son DUNYA LOS birim vektoru
        self.R_f = None              # EMA menzil (cm)
        self.Vc_f = 0.0              # EMA kapanma hizi (cm/s)
        self.omega_f = np.zeros(3)   # EMA LOS donme vektoru (rad/s)
        self.ex_f = 0.0              # EMA yatay piksel hatasi (yaw kanali icin)
        self.ey_f = 0.0              # EMA dikey piksel hatasi (dikey cerceveleme icin)
        self._son_det_t = None       # islenen son det["t"] (ayni kare tekrar gelirse guncelleme)
        self._u_prev = None          # bir onceki DUNYA LOS (Omega icin)
        self._son_komut = None       # commit-freeze icin son uygulanan komut
        self._had = False            # hic gecerli tespit islendi mi
        self._kaynak = "-"           # "pinhole" | "J" | "-"
        self._commit = False
        self._vurus_izin = True      # son cagridaki mod (False=TAKIP menzil-tutma; telemetri)
        self._tilt = 0.0             # son manevra yetki carpani (VIS_TRACK_TILT vs VIS_PN_TILT)
        self._elev_deg = 0.0         # son LOS yukselis acisi (deg; asin(u_hat[2])) — telemetri
        self._dh = 0.0               # arac hedefin ne kadar ALTINDA (cm, +=altta) — telemetri
        self._lookup_ok = True       # arac hedef altinda ~VIS_DH_TARGET mesafede mi
        self._yaw_lead = 0.0         # son ongorulu yaw katkisi (teshis)

    # ------------------------------------------------------------------
    #  Yeni bbox ile komut uret (gorsel temas VAR).
    #  det: {cx,cy,w,h,conf,W,H,t}  |  drone_pos: (x,y,z) cm  |  drone_rot_rpy: (roll,pitch,yaw) deg
    #  v_own_xy: kendi yatay hiz (cm/s, dunya)  |  p: Cfg
    #  YALNIZ GORSEL VERI: hareket komutu bbox/LOS'tan turer; GPS/J YOK (yarisma kurali).
    #  vurus_izin: False = TAKIP modu (sartname 6.1.2/6.1.4 kilit isteri dolmadan):
    #    commit-freeze KAPALI, kapanma kanali MENZIL TUTMA (R -> R_hold). True =
    #    TERMINAL: mevcut tam kapanma + commit (davranis bit-bit eski haliyle ayni).
    #  return: (throttle, pitch, roll, yaw) hepsi [-1,1]
    # ------------------------------------------------------------------
    def hesapla(self, det, drone_pos, drone_rot_rpy, v_own_xy, p, vurus_izin=True):
        cx, cy = float(det["cx"]), float(det["cy"])
        W, H = float(det["W"]), float(det["H"])
        w_px, h_px = float(det["w"]), float(det["h"])
        det_t = det.get("t", None)
        yaw_rad = math.radians(float(drone_rot_rpy[2])) if p.ROT_IN_DEGREES else float(drone_rot_rpy[2])

        # yaw kanali icin YATAY, dikey cerceveleme icin DIKEY piksel hatasi (EMA).
        # ex>0 hedef SAGDA; ey>0 hedef ALTTA (alt kenara dogru). Piksel-uzayi -> kamera
        # tilt kalibrasyonundan BAGIMSIZ (dikey cerceveleme icin dogrudan gozlem).
        ex = (cx - W / 2.0) / (W / 2.0) if W > 1 else 0.0
        ey = (cy - H / 2.0) / (H / 2.0) if H > 1 else 0.0
        a_ema = float(p.VIS_EMA)
        self.ex_f = ex if not self._had else (1.0 - a_ema) * self.ex_f + a_ema * ex
        self.ey_f = ey if not self._had else (1.0 - a_ema) * self.ey_f + a_ema * ey

        # DUNYA LOS birim vektoru (yon HER ZAMAN kameradan)
        u = piksel_to_los(cx, cy, W, H, drone_pos, drone_rot_rpy, tilt_deg=p.VIS_TILT_DEG)

        # --- R/Vc/Omega SADECE yeni kare gelince guncellenir (bayat-tekrar korumasi) ---
        yeni_kare = (det_t is not None and det_t != self._son_det_t)

        # bbox kenara tasti mi (kirpik -> w_px sahte kuculur -> menzil sicrar) -> menzili GUNCELLEME
        kenarda = (cx - w_px / 2.0 <= 1.0 or cx + w_px / 2.0 >= W - 1.0 or
                   cy - h_px / 2.0 <= 1.0 or cy + h_px / 2.0 >= H - 1.0)
        menzil_gecerli = (max(w_px, h_px) >= float(p.VIS_W_PX_MIN)) and (not kenarda)

        if yeni_kare:
            dt = clamp(det_t - self._son_det_t, 0.01, 0.5) if self._son_det_t is not None else None

            # (a) menzil (pinhole) EMA
            R_new = menzil_pinhole(w_px, h_px, W, p.VIS_SPAN_CM) if menzil_gecerli else None
            if R_new is not None:
                R_new = clamp(R_new, p.VIS_R_MIN, p.VIS_R_MAX)
                self._kaynak = "pinhole"
                if self.R_f is None:
                    self.R_f = R_new
                else:
                    R_prev = self.R_f
                    self.R_f = (1.0 - p.VIS_R_EMA) * self.R_f + p.VIS_R_EMA * R_new
                    # (c) kapanma hizi Vc = -dR/dt
                    if dt is not None:
                        Vc_raw = -(self.R_f - R_prev) / dt
                        Vc_raw = clamp(Vc_raw, -p.VZ_MAX, p.VZ_MAX)
                        self.Vc_f = (1.0 - p.VIS_VC_EMA) * self.Vc_f + p.VIS_VC_EMA * Vc_raw
            # NOT: menzil gecersizken (bbox cok kucuk/kenar) ESKI R_f korunur; GPS/J YEDEGI
            # YOK. Yarisma kurali: gorsel temastan SONRA hareket komutu YALNIZ gorsel veriden
            # (GPS kullanimi diskalifiye). (Eski _j_fallback 2026-07-07 kaldirildi.)

            # (d) LOS donme vektoru Omega = (u_prev x u)/dt
            if self._u_prev is not None and dt is not None:
                Omega_raw = np.cross(self._u_prev, u) / dt
                Omega_raw = np.clip(Omega_raw, -p.VIS_OMEGA_MAX, p.VIS_OMEGA_MAX)
                self.omega_f = (1.0 - p.VIS_OMEGA_EMA) * self.omega_f + p.VIS_OMEGA_EMA * Omega_raw

            self._u_prev = u
            self._son_det_t = det_t

        self.u_hat = u
        self._had = True

        # menzil hic kurulamadiysa (ilk kareler) yaklasik degerle basla -> komut patlamasin
        R = self.R_f if self.R_f is not None else float(p.VIS_R_MAX)
        return self._komut(u, R, self.Vc_f, self.omega_f, self.ex_f, w_px, h_px, W, H,
                           v_own_xy, yaw_rad, p, vurus_izin=vurus_izin,
                           drone_z=float(drone_pos[2]), ey=self.ey_f)

    # ------------------------------------------------------------------
    #  Kayip (dead-reckon): yeni bbox yok -> son Omega/Vc ile LOS'u ilerlet.
    #  AvciKontrol suru asilinca hover'a gecirir.
    # ------------------------------------------------------------------
    def kor_devam(self, p, dt, vurus_izin=True):
        if not self._had or self.u_hat is None:
            return 0.0, 0.0, 0.0, 0.0                       # hic tespit yok -> hover
        # LOS'u son donme hiziyla ilerlet, menzili son kapanmayla azalt
        u = self.u_hat + np.cross(self.omega_f, self.u_hat) * dt
        n = float(np.linalg.norm(u))
        u = u / n if n > 1e-9 else self.u_hat
        self.u_hat = u
        if self.R_f is not None:
            self.R_f = max(self.R_f - self.Vc_f * dt, p.VIS_R_MIN)
        R = self.R_f if self.R_f is not None else float(p.VIS_R_MAX)
        # kor-devamda gorsel piksel yok; yaw kanali son ex_f'i tutar. w/h bilinmiyor -> commit
        # freeze'i tetiklemesin diye buyuk bbox varsayma; alan=0 gecir.
        return self._komut(u, R, self.Vc_f, self.omega_f, self.ex_f, 0.0, 0.0, 1.0, 1.0,
                           np.zeros(2), 0.0, p, vurus_izin=vurus_izin, drone_z=None, ey=None)

    # ------------------------------------------------------------------
    #  Ortak komut hesabi:  PN ivme (dunya) -> (thr, pitch, roll, yaw).
    # ------------------------------------------------------------------
    def _komut(self, u_hat, R, Vc, omega, ex_f, w_px, h_px, W, H, v_own_xy, yaw_rad, p,
               vurus_izin=True, drone_z=None, ey=None):
        area = (w_px * h_px) / (W * H) if (W > 1 and H > 1) else 0.0
        a_max = float(p.VIS_PN_A_MAX)
        self._vurus_izin = bool(vurus_izin)

        if vurus_izin:
            # ================== TERMINAL (kilit isteri SAGLANDI) ==================
            # --- COMMIT FREEZE: cok yakin -> son komutu dondur, saf dal ---
            if self._son_komut is not None and (
                    (self.R_f is not None and self.R_f < 300.0) or area > 0.5):
                self._commit = True
                return self._son_komut

        # (e) PN yanal ivme + LOS-boyu kapanma
        a_pn = float(p.VIS_PN_N) * Vc * np.cross(omega, u_hat)
        self._commit = False
        if vurus_izin:
            # TERMINAL kapanma: v_close_des = clamp(KP*R, VC_MIN, VC_CAP) (mevcut yasa)
            v_close_des = clamp(float(p.VIS_KP_CLOSE) * R, float(p.VIS_VC_MIN), float(p.VIS_VC_CAP))
            a_los = float(p.VIS_KV_CLOSE) * (v_close_des - Vc)

            # (f) COMMIT: yakinda yanal PN'i kis (LOS singularite salinimini kovalama)
            if self.R_f is not None and self.R_f < float(p.VIS_COMMIT_R):
                kperp = clamp(self.R_f / float(p.VIS_COMMIT_R), float(p.VIS_COMMIT_LAT), 1.0)
                a_pn = a_pn * kperp
                self._commit = True

            a_cmd = a_pn + a_los * u_hat
            if Vc <= 0.0:                                    # aciliyoruz -> once burnu cevir
                a_cmd = a_cmd + a_max * u_hat
        else:
            # ================== TAKIP (kilit isteri HENUZ dolmadi) ==================
            # Sartname 6.1.2: hedefi cerceve icinde tut, KONTROLSUZ YAKINLASMA;
            # kapanma kanali MENZIL TUTMA: R'yi, bbox'i VIS_HOLD_PCT'te tutan
            # R_hold'a sur (pinhole tersinden turetilir; fx/W orani W'den bagimsiz).
            # v_close_des NEGATIF olabilir (fazla yaklastiysak geri acil);
            # VC_MIN tabani UYGULANMAZ (minimum kapanma dayatmak tutmayi bozar).
            # Commit-freeze ve Vc<=0 "burnu cevir" itisi de KAPALI (dalma yok).
            r_hold = float(geometri.fx_from_hfov(1.0)) * float(p.VIS_SPAN_CM) / float(p.VIS_HOLD_PCT)
            # NAZIK yaklasma: TAKIP hiz tavani VC_CAP (12 m/s) degil VIS_TAKIP_VC (~3 m/s)
            # -> kilit menzilinde dalip hedefi kacirmaz; kadrajda park eder, kilit dolar (#1).
            vc_takip = float(getattr(p, "VIS_TAKIP_VC", p.VIS_VC_CAP))
            v_close_des = clamp(float(p.VIS_KP_CLOSE) * (R - r_hold), -vc_takip, vc_takip)
            a_los = float(p.VIS_KV_CLOSE) * (v_close_des - Vc)
            a_cmd = a_pn + a_los * u_hat
        a_cmd = _clip_norm(a_cmd, a_max)

        # (g) ivme -> komut esleme (GPS strike blogu :963 aynasi). PITCH ve ROLL yetkisi
        # AYRI: takipte savrulma/clutter ROLL'dan (bank) geliyordu -> ROLL kisilir
        # (VIS_TRACK_TILT), ama PITCH (ileri/KAPANMA) TAM yetki (VIS_PN_TILT) -> arac
        # yaklasabilir. (Tek-tilt kisisi hem bank'i hem ileri-egimi kisip yaklasmayi
        # olduruyordu: VIS_TAKIP_VC hiz tavani etkisizdi cunku pitch tilt'te doyuyordu.)
        # Yaklasma HIZINI artik VIS_TAKIP_VC belirler; bank yine sinirli (gokyuzu arka plan).
        tilt_pitch = float(p.VIS_PN_TILT)
        tilt_roll = float(p.VIS_PN_TILT) if vurus_izin else float(getattr(p, "VIS_TRACK_TILT", p.VIS_PN_TILT))
        a_fwd, a_right = _world_to_body(float(a_cmd[0]), float(a_cmd[1]), yaw_rad)
        pitch = p.PITCH_SIGN * clamp(a_fwd / a_max, -1.0, 1.0) * tilt_pitch
        roll = p.ROLL_SIGN * clamp(a_right / a_max, -1.0, 1.0) * tilt_roll

        # dikey taban: PN dikey ivmesi*tau. Kapanma feedforward (v_close*u_z) YALNIZ
        # TERMINAL'de: takipte hedefe tirmanip hedefi kadrajda ASAGI itiyordu (alttan kacis).
        # Takipte dikeyi CERCEVELEME kontrol eder (asagida). VIS_PN_SIGN_VZ: SIM'de dikey
        # komut LOS-z ile TERS bulundu; isaret bu kanala ozel (yatay PN/yaw dokunulmaz).
        vz_des = float(a_cmd[2]) * float(p.VIS_TAU_Z)
        if vurus_izin:
            vz_des += v_close_des * float(u_hat[2])          # terminal intercept dikeyi

        # --- DIKEY = HEDEF ALTINDA SABIT MESAFE (alttan yaklas/vur) ---
        # Kadraj-pozisyonu (sabit ACI) yerine dunya dikey AYRIMINI tut: arac hedefin
        # irtifasindan VIS_DH_TARGET kadar ALTTA kalsin. Sabit aci -> kapandikca ayrim
        # kuculur -> arac hedefin USTUNE cikip arka plan ZEMIN oluyordu (tespit kopuyordu).
        # Sabit MESAFE -> hep altta -> gokyuzu arka plan -> hedef kapandikca kadrajda YUKARI
        # kayar (alttan yaklasma). dh_actual: arac hedefin ne kadar ALTINDA (cm, +=altta).
        # dh_actual TAMAMEN GORSEL: R (pinhole, bbox boyutundan) * u_hat[2] (LOS-z, kameradan).
        # GPS/J YOK — yarisma kurali: gorsel temastan SONRA hareket komutu YALNIZ gorsel
        # veriden turetilir (GPS kullanimi DISKALIFIYE). u_hat[2]>0 hedef USTTE (altta kaliyoruz),
        # <0 hedef ALTTA (ustune ciktik -> guclu alcal). R*u_hat[2] = dunya dikey ayrimi.
        self._elev_deg = math.degrees(math.asin(clamp(float(u_hat[2]), -1.0, 1.0)))  # telemetri
        self._dh = R * float(u_hat[2])                       # cm; +=hedefin altinda (gorsel)
        if not vurus_izin:
            dh_t = float(getattr(p, "VIS_DH_TARGET", 0.0))
            band = max(float(getattr(p, "VIS_DH_BAND", 1.0)), 1.0)
            self._lookup_ok = abs(self._dh - dh_t) < band    # hedef altinda ~hedef mesafede mi
            # dh<target (yeterince altta degil / USTTE) -> ALCAL; dh>target (cok altta) -> TIRMAN
            vz_sep = clamp((self._dh - dh_t) / band, -1.0, 1.0) * float(getattr(p, "VIS_LOOKUP_VZ", 0.0))
            # yere cakilma korumasi: taban altinda ALCALMA (vz<0) dayatma; TIRMANISA izin
            if drone_z is not None and float(drone_z) <= float(getattr(p, "LOOKUP_MIN_ALT_CM", 0.0)):
                vz_sep = max(vz_sep, 0.0)
            vz_des += vz_sep
        else:
            self._lookup_ok = True

        thr = clamp(p.Z_SIGN * float(getattr(p, "VIS_PN_SIGN_VZ", 1.0)) * vz_des
                    / float(p.VZ_MAX), p.THR_DN, p.THR_UP)

        # yaw: PN'in parcasi DEGIL; govdeye sabit kamerayi (HFOV 125) hedefte tutar.
        #  P terimi (ex_f): anlik yatay hatayi kapatir. LEAD terimi (omega_z): LOS azimut
        #  hizini ILERI-BESLE -> hareketli hedefi GERIDEN kovalamayi onler (canli log:
        #  ex_ort +0.49, kayiplarin %100'u kenar). omega dunya-Z bileseni = azimut hizi;
        #  burun bu hizda donerse hedef kadrajda MERKEZDE kalir. omega EMA'li+clamp'li.
        yaw_p = float(p.VIS_SIGN_YAW) * float(p.VIS_K_YAW) * ex_f
        yaw_lead = float(p.VIS_SIGN_YAW) * float(getattr(p, "VIS_K_YAW_LEAD", 0.0)) * float(omega[2])
        yaw = clamp(yaw_p + yaw_lead, -1.0, 1.0)
        self._yaw_lead = float(yaw_lead)        # telemetri/teshis (lead katkisi)

        self._tilt = float(tilt_roll)          # bank (roll) yetki carpani (teshis; pitch tam)
        komut = (float(thr), float(pitch), float(roll), float(yaw))
        self._son_komut = komut
        return komut

    # ------------------------------------------------------------------
    #  Telemetri (server build_telemetry okur; guduum girdisi DEGIL).
    # ------------------------------------------------------------------
    def durum(self):
        return {
            "law": "PNG",
            "R_m": (self.R_f / 100.0) if self.R_f is not None else None,
            "Vc_ms": self.Vc_f / 100.0,
            "omega_rads": float(np.linalg.norm(self.omega_f)),
            "commit": bool(self._commit),
            "kaynak": self._kaynak,
            "vurus_izin": bool(self._vurus_izin),
            "tilt": float(self._tilt),                # manevra yetki carpani (takip<terminal; teshis)
            "elev_deg": float(self._elev_deg),        # LOS yukselis acisi (bilgi/teshis)
            "dh_below_m": float(self._dh) / 100.0,    # arac hedefin ne kadar ALTINDA (m; +=altta)
            "lookup_ok": bool(self._lookup_ok),       # hedef altinda ~VIS_DH_TARGET mesafede mi
            "ex": float(self.ex_f),                   # EMA yatay kadraj hatasi (0=merkez, 1=kenar)
            "ey": float(self.ey_f),                   # EMA dikey kadraj hatasi (0=merkez, +=alt)
            "yaw_lead": float(self._yaw_lead),        # ongorulu yaw katkisi (teshis)
        }

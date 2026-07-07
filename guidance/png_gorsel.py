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

YARISMA KURALI: gorsel temas VARKEN YONELIM YALNIZCA KAMERADAN gelir. LOS birim
vektoru (yon) her zaman bbox pikselinden turetilir; GPS/J-filtre yalnizca menzil/
kapanma hizinin BUYUKLUGU gecersizken (bbox cok kucuk/kenarda) yedek olarak ve
Cfg.VIS_PN_FALLBACK_J acikken devreye girer -> yon ASLA GPS'ten alinmaz.

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
        self._son_det_t = None       # islenen son det["t"] (ayni kare tekrar gelirse guncelleme)
        self._u_prev = None          # bir onceki DUNYA LOS (Omega icin)
        self._son_komut = None       # commit-freeze icin son uygulanan komut
        self._had = False            # hic gecerli tespit islendi mi
        self._kaynak = "-"           # "pinhole" | "J" | "-"
        self._commit = False

    # ------------------------------------------------------------------
    #  Yeni bbox ile komut uret (gorsel temas VAR).
    #  det: {cx,cy,w,h,conf,W,H,t}  |  drone_pos: (x,y,z) cm  |  drone_rot_rpy: (roll,pitch,yaw) deg
    #  v_own_xy: kendi yatay hiz (cm/s, dunya)  |  p: Cfg
    #  j_fallback: (R_cm, Vc_cms) | None  -> menzil gecersizken YALNIZ buyukluk yedegi
    #  return: (throttle, pitch, roll, yaw) hepsi [-1,1]
    # ------------------------------------------------------------------
    def hesapla(self, det, drone_pos, drone_rot_rpy, v_own_xy, p, j_fallback=None):
        cx, cy = float(det["cx"]), float(det["cy"])
        W, H = float(det["W"]), float(det["H"])
        w_px, h_px = float(det["w"]), float(det["h"])
        det_t = det.get("t", None)
        yaw_rad = math.radians(float(drone_rot_rpy[2])) if p.ROT_IN_DEGREES else float(drone_rot_rpy[2])

        # yaw kanali icin yatay piksel hatasi (IBVS ile ayni tanim), EMA
        ex = (cx - W / 2.0) / (W / 2.0) if W > 1 else 0.0
        a_ema = float(p.VIS_EMA)
        self.ex_f = ex if not self._had else (1.0 - a_ema) * self.ex_f + a_ema * ex

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
            elif p.VIS_PN_FALLBACK_J and j_fallback is not None:
                # menzil gecersiz -> YALNIZ buyukluk J'den (yon degil)
                R_j, Vc_j = j_fallback
                if R_j is not None:
                    self.R_f = float(R_j); self._kaynak = "J"
                if Vc_j is not None:
                    self.Vc_f = float(Vc_j)

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
                           v_own_xy, yaw_rad, p)

    # ------------------------------------------------------------------
    #  Kayip (dead-reckon): yeni bbox yok -> son Omega/Vc ile LOS'u ilerlet.
    #  AvciKontrol suru asilinca hover'a gecirir.
    # ------------------------------------------------------------------
    def kor_devam(self, p, dt):
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
                           np.zeros(2), 0.0, p)

    # ------------------------------------------------------------------
    #  Ortak komut hesabi:  PN ivme (dunya) -> (thr, pitch, roll, yaw).
    # ------------------------------------------------------------------
    def _komut(self, u_hat, R, Vc, omega, ex_f, w_px, h_px, W, H, v_own_xy, yaw_rad, p):
        area = (w_px * h_px) / (W * H) if (W > 1 and H > 1) else 0.0
        a_max = float(p.VIS_PN_A_MAX)

        # --- COMMIT FREEZE: cok yakin -> son komutu dondur, saf dal ---
        if self._son_komut is not None and (
                (self.R_f is not None and self.R_f < 300.0) or area > 0.5):
            self._commit = True
            return self._son_komut

        # (e) PN yanal ivme + LOS-boyu kapanma
        a_pn = float(p.VIS_PN_N) * Vc * np.cross(omega, u_hat)
        v_close_des = clamp(float(p.VIS_KP_CLOSE) * R, float(p.VIS_VC_MIN), float(p.VIS_VC_CAP))
        a_los = float(p.VIS_KV_CLOSE) * (v_close_des - Vc)

        # (f) COMMIT: yakinda yanal PN'i kis (LOS singularite salinimini kovalama)
        self._commit = False
        if self.R_f is not None and self.R_f < float(p.VIS_COMMIT_R):
            kperp = clamp(self.R_f / float(p.VIS_COMMIT_R), float(p.VIS_COMMIT_LAT), 1.0)
            a_pn = a_pn * kperp
            self._commit = True

        a_cmd = a_pn + a_los * u_hat
        if Vc <= 0.0:                                        # aciliyoruz -> once burnu cevir
            a_cmd = a_cmd + a_max * u_hat
        a_cmd = _clip_norm(a_cmd, a_max)

        # (g) ivme -> komut esleme (GPS strike blogu :963 aynasi)
        a_fwd, a_right = _world_to_body(float(a_cmd[0]), float(a_cmd[1]), yaw_rad)
        pitch = p.PITCH_SIGN * clamp(a_fwd / a_max, -1.0, 1.0) * float(p.VIS_PN_TILT)
        roll = p.ROLL_SIGN * clamp(a_right / a_max, -1.0, 1.0) * float(p.VIS_PN_TILT)

        # dikey: kapanma feedforward (v_close*u_z) + PN dikey ivmesi*tau -> dikey hiz komutu.
        # VIS_PN_SIGN_VZ: SIM'de gozlemlendi -> dikey komut LOS-z ile TERS calisiyordu
        # (hedef yukarida iken alcaliyor, asagida iken yukseliyordu). Isaret bu kanala
        # OZEL (yatay PN/yaw dokunulmaz); gerekirse tek sabitten geri alinir.
        vz_des = v_close_des * float(u_hat[2]) + float(a_cmd[2]) * float(p.VIS_TAU_Z)
        thr = clamp(p.Z_SIGN * float(getattr(p, "VIS_PN_SIGN_VZ", 1.0)) * vz_des
                    / float(p.VZ_MAX), p.THR_DN, p.THR_UP)

        # yaw: PN'in parcasi DEGIL; govdeye sabit kamerayi (HFOV 125) hedefte tutar (IBVS ile ayni)
        yaw = clamp(p.VIS_SIGN_YAW * float(p.VIS_K_YAW) * ex_f, -1.0, 1.0)

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
        }

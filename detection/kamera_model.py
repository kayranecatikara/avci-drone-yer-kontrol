# -*- coding: utf-8 -*-
"""
================================================================================
KAMERA MODELI — TEK KAYNAK (FAZ 0, yarisma pipeline)
================================================================================
Kameranin ic parametre matrisi (K), distorsiyon varsayimi ve kamera-govde
montaj donusumu (25 derece pitch-up tilt) icin TEK KAYNAK. PnP oryantasyon
zinciri, gyro-CMC homografisi, IBVS dikey referansi (VIS_EY_REF) ve LOS/bearing
hesaplari tilt'i ve K'yi BURADAN okur — koda ikinci bir 25/125 sabiti YAZILMAZ.

SDK v0.0.5 platform sabitleri (oyuna gomulu, degistirilemez):
  * FOV = 125 derece YATAY (HFOV; convention netlesti)
  * Kamera tilt = 25 derece YUKARI (FPV kamera burnun 25 derece ustune bakar)

COZUNURLUK-K BAGI: K piksel cinsindendir; f_x dogrudan yakalanan goruntunun
piksel GENISLIGINE baglidir: f_x = W / (2*tan(HFOV/2)) ~= 0.2603*W
(orn. 1920 px'te ~499.8 px; 960 px'te ~249.9 px). Cozunurluk degisirse K ayni
HFOV=125'ten yeni cozunurlukle yeniden turetilir (fonksiyonlar W,H parametreli).
Aspect (W/H) yalnizca turetilen VFOV'u degistirir, f_x'i DEGIL.
Turetilen, bilgi amacli (16:9): VFOV ~ 94.4 derece, DFOV ~ 131.2 derece.

EKSEN TAKIMLARI (tum tuketiciler icin ortak dil):
  DUNYA  : sim telemetrisiyle ayni; x,y yatay, z YUKARI, sag-el.
           yaw = atan2(y, x) yonu, CCW (mevcut GPS gudumuyle sim'de KANITLI).
  GOVDE  : +x burun, +y SOL, +z yukari (sag-el; dunya ile ayni el).
           "sag" = -y_govde. (ana_kontrol.world_to_body'nin fwd/right
           skalerleriyle tutarli: e_right = -y_govde.)
  KAMERA : OpenCV standardi; +Z optik eksen (ileri), +X goruntude SAGA,
           +Y goruntude ASAGI. solvePnP / homografi dogrudan bu cerceve.

ATTITUDE KONVANSIYON VARSAYIMI (>>> SIM'DE DOGRULA <<<):
  SDK get_drone_rotation() -> (roll, pitch, yaw) DERECE.
    yaw   : +z etrafinda CCW, 0 = +x dunya (sim'de kanitli — gudum ucuyor)
    pitch : burun YUKARI pozitif (VARSAYIM)
    roll  : SAGA yatis pozitif (VARSAYIM)
  Dogrulama araclari: arac/k_sanity_olcum.py (merkez-reprojeksiyon tanisi) ve
  FAZ 1 CMC isaret testi. Yanlis cikan isaret/sira BURADA duzeltilir (tek nokta);
  tuketiciler (PnP, CMC, IBVS) degismez.
================================================================================
"""
import math

import numpy as np

# --- Platform sabitleri (SDK v0.0.5; oyuna gomulu, degistirilemez) ---
HFOV_DEG = 125.0     # YATAY gorus alani (derece)
TILT_DEG = 25.0      # kamera montaj tilti: burun ekseninin ustu (pitch-up, derece)


# ----------------------------------------------------------------------------
#  K matrisi ve FOV turetmeleri (hepsi cozunurluk parametreli)
# ----------------------------------------------------------------------------
def fx_px(W):
    """Yatay odak uzakligi [px]: f_x = W / (2*tan(HFOV/2)) ~= 0.2603*W."""
    return float(W) / (2.0 * math.tan(math.radians(HFOV_DEG) / 2.0))


def K_matrisi(W, H):
    """Kamera ic parametre matrisi K (3x3, float64, piksel cinsinden).
    f_y = f_x (kare piksel varsayimi: pikseller fiziksel olarak kare;
    oyun/render motorlarinda standart), c = goruntu merkezi, distorsiyon = 0."""
    f = fx_px(W)
    return np.array([[f,   0.0, float(W) / 2.0],
                     [0.0, f,   float(H) / 2.0],
                     [0.0, 0.0, 1.0]], dtype=float)


def dist_katsayilari():
    """Distorsiyon katsayilari: render kamerasi -> 0 varsayimi (5'li OpenCV vektoru)."""
    return np.zeros(5, dtype=float)


def vfov_rad(W, H):
    """Turetilen DIKEY FOV [rad]: tan(v/2) = (H/W)*tan(HFOV/2). 16:9'da ~94.4 der."""
    return 2.0 * math.atan((float(H) / float(W)) * math.tan(math.radians(HFOV_DEG) / 2.0))


def dfov_rad(W, H):
    """Turetilen DIYAGONAL FOV [rad]: tan(d/2)=sqrt(tan^2(h/2)+tan^2(v/2)). 16:9'da ~131.2 der."""
    th = math.tan(math.radians(HFOV_DEG) / 2.0)
    tv = math.tan(vfov_rad(W, H) / 2.0)
    return 2.0 * math.atan(math.hypot(th, tv))


def ey_ref(W=16.0, H=9.0):
    """IBVS dikey referansi: ayni irtifadaki (ufuktaki) hedefin normalize dikey
    konumu ey = (v - H/2)/(H/2). Kamera TILT_DEG yukari baktigindan ufuk goruntu
    merkezinin ALTINDA durur: ey_ref = tan(tilt)/tan(VFOV/2).
    Yalnizca W/H ORANINA baglidir (16,9 gecmek 1920,1080 ile ozdes). 16:9'da ~0.4315."""
    return math.tan(math.radians(TILT_DEG)) / math.tan(vfov_rad(W, H) / 2.0)


# ----------------------------------------------------------------------------
#  Kamera-govde montaj donusumu (R_mount): 25 derece pitch-up
#  Kamera eksenlerinin GOVDE koordinatlari (tau = TILT_DEG):
#    x_kam (goruntude sag)  = (0, -1, 0)            (govde sagi = -y)
#    y_kam (goruntude asagi)= (sin t, 0, -cos t)
#    z_kam (optik eksen)    = (cos t, 0,  sin t)    (burnun t ustu)
# ----------------------------------------------------------------------------
def R_mount_kam2gov():
    """Kamera -> govde donusum matrisi (sutunlar: kamera eksenleri govdede)."""
    t = math.radians(TILT_DEG)
    ct, st = math.cos(t), math.sin(t)
    return np.array([[0.0, st, ct],
                     [-1.0, 0.0, 0.0],
                     [0.0, -ct, st]], dtype=float)


def R_mount_gov2kam():
    """Govde -> kamera donusum matrisi (R_mount_kam2gov'un transpozu)."""
    return R_mount_kam2gov().T


# ----------------------------------------------------------------------------
#  Attitude: govde <-> dunya  (SDK telemetrisi DERECE; konvansiyon dosya
#  basligindaki VARSAYIM — sim dogrulamasinda tek nokta burasi)
# ----------------------------------------------------------------------------
def R_govde_to_dunya(roll_deg, pitch_deg, yaw_deg):
    """Govde -> dunya donusumu. Kompozisyon (intrinsic): Rz(yaw)@Rpitch@Rroll.
    pitch: burun-yukari (+); roll: saga-yatis (+); yaw: CCW (+z etrafinda)."""
    fi = math.radians(roll_deg)
    th = math.radians(pitch_deg)
    ps = math.radians(yaw_deg)
    cf, sf = math.cos(fi), math.sin(fi)
    ct, st = math.cos(th), math.sin(th)
    cp, sp = math.cos(ps), math.sin(ps)
    Rroll = np.array([[1.0, 0.0, 0.0],       # +x (burun) etrafinda; +fi = saga yatis
                      [0.0, cf, -sf],
                      [0.0, sf, cf]])
    Rpitch = np.array([[ct, 0.0, -st],       # +fi degil: burun-yukari +theta
                       [0.0, 1.0, 0.0],      # (standart Ry(-theta); x -> (c,0,+s))
                       [st, 0.0, ct]])
    Ryaw = np.array([[cp, -sp, 0.0],         # +z etrafinda CCW
                     [sp, cp, 0.0],
                     [0.0, 0.0, 1.0]])
    return Ryaw @ Rpitch @ Rroll


def R_dunya_to_kamera(roll_deg, pitch_deg, yaw_deg):
    """Dunya -> kamera donusumu (attitude + montaj zinciri tek cagrida)."""
    return R_mount_gov2kam() @ R_govde_to_dunya(roll_deg, pitch_deg, yaw_deg).T


def dunya_to_kamera(p_dunya, drone_pos, roll_deg, pitch_deg, yaw_deg):
    """Dunya noktasi -> kamera cercevesi koordinati (birim: girdiyle ayni, orn. cm)."""
    d = np.asarray(p_dunya, dtype=float) - np.asarray(drone_pos, dtype=float)
    return R_dunya_to_kamera(roll_deg, pitch_deg, yaw_deg) @ d


def kamera_to_dunya_yon(v_kam, roll_deg, pitch_deg, yaw_deg):
    """Kamera cercevesi VEKTORU -> dunya cercevesi (yon/konum farki; oteleme yok)."""
    return R_govde_to_dunya(roll_deg, pitch_deg, yaw_deg) @ (
        R_mount_kam2gov() @ np.asarray(v_kam, dtype=float))


# ----------------------------------------------------------------------------
#  GYRO-CMC (kamera hareket telafisi) — saf rotasyon homografisi
#  Avci frame1->frame2 dondugunde, UZAK (dunya-sabit) bir noktanin goruntu
#  konumu nasil kayar? Saf rotasyonda derinlikten BAGIMSIZ exact:
#     x2 = H · x1,   H = K · R_Δ,kam · K⁻¹
#  R_Δ,kam: frame1 kamera-yonunu frame2 kamera-yonune tasiyan donus. Tilt≠0
#  oldugundan govde attitude farki kamera cercevesine MONTAJ donusumuyle tasinir:
#     R_Δ,kam = R_mount^T · R_Δ,govde · R_mount   (eslenik/benzerlik donusumu)
#  Bu, R_dunya_to_kamera(t2) · R_dunya_to_kamera(t1)^T ile MATEMATIKSEL OLARAK
#  OZDESTIR (R_d2k = R_mount^T · R_govde_to_dunya^T oldugundan R_mount otomatik
#  girer); asagida ikinci bicimle hesaplanir (tek kaynak: R_dunya_to_kamera).
# ----------------------------------------------------------------------------
def R_delta_kamera(att1, att2):
    """att = (roll, pitch, yaw) DERECE. Frame1->frame2 kamera cercevesi donusu."""
    R1 = R_dunya_to_kamera(*att1)
    R2 = R_dunya_to_kamera(*att2)
    return R2 @ R1.T


def cmc_homografi(W, H, att1, att2):
    """gyro-CMC homografisi (3x3): frame1 goruntu noktasi -> frame2 (uzak hedef).
    att1/att2 = (roll,pitch,yaw) derece. K ayni cozunurlukten (W,H)."""
    K = K_matrisi(W, H)
    Rd = R_delta_kamera(att1, att2)
    return K @ Rd @ np.linalg.inv(K)


# ----------------------------------------------------------------------------
#  Izdusum yardimcilari
# ----------------------------------------------------------------------------
def izdusur(p_kam, K):
    """Kamera-cercevesi noktayi piksele izdusur -> (u, v). Kamera ARKASINDA
    (Z<=0) ise None (izdusum tanimsiz)."""
    p = np.asarray(p_kam, dtype=float)
    if p[2] <= 1e-9:
        return None
    u = K[0, 0] * p[0] / p[2] + K[0, 2]
    v = K[1, 1] * p[1] / p[2] + K[1, 2]
    return float(u), float(v)


def piksel_yon(u, v, K):
    """Piksel -> kamera cercevesi BIRIM bakis yonu (K^-1 uygulanmis, normalize)."""
    d = np.array([(float(u) - K[0, 2]) / K[0, 0],
                  (float(v) - K[1, 2]) / K[1, 1],
                  1.0])
    return d / np.linalg.norm(d)


def dikey_ekran_tahmini(hedef_z, drone_z, d_h_yatay, W=16.0, H=9.0):
    """KABA dikey-ekran kestirimi: hedefin ham-GPS irtifasi + drone irtifasi +
    yatay mesafe + KAMERA TILT'inden, hedefin OLABILECEGI normalize dikey ekran
    konumu (v_pred, 0=ust .. 1=alt) + elevasyon acisi (derece).

    ATTITUDE-BAGIMSIZ (drone pitch/roll KATILMAZ): optik eksen ~TILT_DEG dikey
    acisinda varsayilir. Amac gross imkansizlari elemek (bkz. kilit geometrik
    kapisi); band GENIS tutuldugundan pitch degiskenligi + ham-GPS gurultusu
    yutulur. Kucuk-aci lineer yaklasim (VFOV'a orani). >>> Blokor B (attitude
    konvansiyon dogrulamasi) kapaninca reprojeksiyon-tabanli SIKI kapiya cevrilir. """
    dz = float(hedef_z) - float(drone_z)
    elev_t = math.degrees(math.atan2(dz, max(float(d_h_yatay), 1.0)))
    cam_elev = TILT_DEG                                   # optik eksen ~tilt (pitch YOK)
    vfov = math.degrees(vfov_rad(W or 16.0, H or 9.0))
    v_pred = 0.5 - (elev_t - cam_elev) / max(vfov, 1e-6)   # 0=ust,1=alt
    return v_pred, elev_t

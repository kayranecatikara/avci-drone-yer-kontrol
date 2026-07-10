# -*- coding: utf-8 -*-
"""KAMERA MODELI — tek kaynak. K matrisi, FOV turetmeleri, kamera-govde montaj
tilt'i (25 derece), attitude donusumleri, gyro-CMC homografisi ve izdusum yardimcilari."""
import math

import numpy as np

# Platform sabitleri (SDK v0.0.5; oyuna gomulu).
HFOV_DEG = 125.0     # yatay gorus alani (derece)
TILT_DEG = 25.0      # kamera montaj tilti (pitch-up, derece)


# K matrisi ve FOV turetmeleri (hepsi cozunurluk parametreli)
def fx_px(W):
    """Yatay odak uzakligi [px]: f_x = W / (2*tan(HFOV/2))."""
    return float(W) / (2.0 * math.tan(math.radians(HFOV_DEG) / 2.0))


def K_matrisi(W, H):
    """Kamera ic parametre matrisi K (3x3, piksel). f_y=f_x, c=merkez, distorsiyon=0."""
    f = fx_px(W)
    return np.array([[f,   0.0, float(W) / 2.0],
                     [0.0, f,   float(H) / 2.0],
                     [0.0, 0.0, 1.0]], dtype=float)


def dist_katsayilari():
    """Distorsiyon katsayilari: 0 varsayimi (5'li OpenCV vektoru)."""
    return np.zeros(5, dtype=float)


def vfov_rad(W, H):
    """Turetilen dikey FOV [rad]: tan(v/2) = (H/W)*tan(HFOV/2)."""
    return 2.0 * math.atan((float(H) / float(W)) * math.tan(math.radians(HFOV_DEG) / 2.0))


def dfov_rad(W, H):
    """Turetilen diyagonal FOV [rad]: tan(d/2)=sqrt(tan^2(h/2)+tan^2(v/2))."""
    th = math.tan(math.radians(HFOV_DEG) / 2.0)
    tv = math.tan(vfov_rad(W, H) / 2.0)
    return 2.0 * math.atan(math.hypot(th, tv))


def ey_ref(W=16.0, H=9.0):
    """IBVS dikey referansi: ufuktaki hedefin normalize dikey konumu.
    ey_ref = tan(tilt)/tan(VFOV/2); yalniz W/H oranina baglidir."""
    return math.tan(math.radians(TILT_DEG)) / math.tan(vfov_rad(W, H) / 2.0)


# Kamera-govde montaj donusumu (R_mount): 25 derece pitch-up
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


# Attitude: govde <-> dunya (SDK telemetrisi derece)
def R_govde_to_dunya(roll_deg, pitch_deg, yaw_deg):
    """Govde -> dunya donusumu. Rz(yaw)@Rpitch@Rroll.
    pitch: burun-yukari (+); roll: saga-yatis (+); yaw: CCW (+z etrafinda)."""
    fi = math.radians(roll_deg)
    th = math.radians(pitch_deg)
    ps = math.radians(yaw_deg)
    cf, sf = math.cos(fi), math.sin(fi)
    ct, st = math.cos(th), math.sin(th)
    cp, sp = math.cos(ps), math.sin(ps)
    Rroll = np.array([[1.0, 0.0, 0.0],
                      [0.0, cf, -sf],
                      [0.0, sf, cf]])
    Rpitch = np.array([[ct, 0.0, -st],
                       [0.0, 1.0, 0.0],
                       [st, 0.0, ct]])
    Ryaw = np.array([[cp, -sp, 0.0],
                     [sp, cp, 0.0],
                     [0.0, 0.0, 1.0]])
    return Ryaw @ Rpitch @ Rroll


def R_dunya_to_kamera(roll_deg, pitch_deg, yaw_deg):
    """Dunya -> kamera donusumu (attitude + montaj zinciri tek cagrida)."""
    return R_mount_gov2kam() @ R_govde_to_dunya(roll_deg, pitch_deg, yaw_deg).T


def dunya_to_kamera(p_dunya, drone_pos, roll_deg, pitch_deg, yaw_deg):
    """Dunya noktasi -> kamera cercevesi koordinati (birim: girdiyle ayni)."""
    d = np.asarray(p_dunya, dtype=float) - np.asarray(drone_pos, dtype=float)
    return R_dunya_to_kamera(roll_deg, pitch_deg, yaw_deg) @ d


def kamera_to_dunya_yon(v_kam, roll_deg, pitch_deg, yaw_deg):
    """Kamera cercevesi vektoru -> dunya cercevesi (yon; oteleme yok)."""
    return R_govde_to_dunya(roll_deg, pitch_deg, yaw_deg) @ (
        R_mount_kam2gov() @ np.asarray(v_kam, dtype=float))


# GYRO-CMC: saf rotasyon homografisi. H = K · R_delta,kam · K^-1;
# R_delta,kam = R_dunya_to_kamera(t2) · R_dunya_to_kamera(t1)^T.
def R_delta_kamera(att1, att2):
    """att = (roll, pitch, yaw) derece. Frame1->frame2 kamera cercevesi donusu."""
    R1 = R_dunya_to_kamera(*att1)
    R2 = R_dunya_to_kamera(*att2)
    return R2 @ R1.T


def cmc_homografi(W, H, att1, att2):
    """gyro-CMC homografisi (3x3): frame1 goruntu noktasi -> frame2 (uzak hedef)."""
    K = K_matrisi(W, H)
    Rd = R_delta_kamera(att1, att2)
    return K @ Rd @ np.linalg.inv(K)


# Izdusum yardimcilari
def izdusur(p_kam, K):
    """Kamera-cercevesi noktayi piksele izdusur -> (u, v). Z<=0 ise None."""
    p = np.asarray(p_kam, dtype=float)
    if p[2] <= 1e-9:
        return None
    u = K[0, 0] * p[0] / p[2] + K[0, 2]
    v = K[1, 1] * p[1] / p[2] + K[1, 2]
    return float(u), float(v)


def piksel_yon(u, v, K):
    """Piksel -> kamera cercevesi birim bakis yonu (K^-1 uygulanmis, normalize)."""
    d = np.array([(float(u) - K[0, 2]) / K[0, 0],
                  (float(v) - K[1, 2]) / K[1, 1],
                  1.0])
    return d / np.linalg.norm(d)


def dikey_ekran_tahmini(hedef_z, drone_z, d_h_yatay, W=16.0, H=9.0):
    """Kaba dikey-ekran kestirimi: hedefin normalize dikey ekran konumu (v_pred, 0=ust..1=alt)
    + elevasyon acisi (derece). Attitude-bagimsiz (optik eksen ~TILT_DEG varsayilir)."""
    dz = float(hedef_z) - float(drone_z)
    elev_t = math.degrees(math.atan2(dz, max(float(d_h_yatay), 1.0)))
    cam_elev = TILT_DEG                                   # optik eksen ~tilt (pitch yok)
    vfov = math.degrees(vfov_rad(W or 16.0, H or 9.0))
    v_pred = 0.5 - (elev_t - cam_elev) / max(vfov, 1e-6)   # 0=ust,1=alt
    return v_pred, elev_t

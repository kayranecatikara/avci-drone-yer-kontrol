# -*- coding: utf-8 -*-
"""
================================================================================
 POSE GEOMETRI — ortak matematik (UE rotasyon, projeksiyon, keypoint yukleme)
================================================================================
Faz 4 (etiketle.py) ve Faz 6 (poz_cozucu.py / degerlendir.py) buradan import eder.
Tek dogruluk kaynagi: eksen konvansiyonu ve projeksiyon SADECE burada tanimlidir.

UE dunyasi: SOL-elli, X=ileri, Y=saga, Z=yukari, birim cm, acilar derece.
SDK rotasyon tuple sirasi: (roll, pitch, yaw)  <-- get_drone/target_rotation.

Keypoint frame (talon_keypoints.json): UE GOVDE — X=ileri(burun), Y=saga, Z=yukari.
Kullanicinin AM tablosu (sag-elli: +X=kuyruk +Y=yukari +Z=sol kanat) su donusumle
UE'ye cevrildi ve JSON'a oyle yazildi:  X_UE = -X_tablo,  Y_UE = -Z_tablo,  Z_UE = +Y_tablo.
"""
import os
import json
import numpy as np

_BURADA = os.path.dirname(os.path.abspath(__file__))
_KP_JSON = os.path.join(_BURADA, "talon_keypoints.json")

# Platform sabitleri
# TILT (kamera yukari egim): DEGERI HENUZ KESIN DEGIL.
#   - SDK_README: 25 derece yukari.  - Kullanici: "tilt yok" dedi.
#   - SAHA VERISI (3 Tem, best.pt kalibrasyonu): ~15-25 derece YUKARI tilt VAR
#     (tilt=0 veriyle celisiyor). Kesin deger latency'den bulanik; pose/kalibre.py
#     TEMIZ (yavas) kayittan olcecek. Simdilik SDK degeri 25 placeholder.
KAMERA_TILT_DEG = 25.0     # YUKARI tilt/pitch (deg) — detection/kamera_model.TILT_DEG ile ESIT tutulmali; kalibre.py netleştirir
KAMERA_TILT_YAW_DEG = 0.0  # kamera montaj YAW ofseti (deg) — kalibre.py olcerse doldurulur
KAMERA_TILT_ROLL_DEG = 0.0 # kamera montaj ROLL ofseti (deg)
KAMERA_HFOV_DEG = 125.0    # YATAY FOV (kullanici teyidi) -> fx = (W/2)/tan(HFOV/2)


def ue_rot_matrix(pitch, yaw, roll):
    """UE FRotator (derece) -> R (3x3): P_world = R @ P_local.
    Sutunlar = lokal X(ileri), Y(sag), Z(yukari) eksenlerinin dunyadaki yonu."""
    p, y, r = np.radians([pitch, yaw, roll])
    cp, sp = np.cos(p), np.sin(p)
    cy, sy = np.cos(y), np.sin(y)
    cr, sr = np.cos(r), np.sin(r)
    fwd   = np.array([cp * cy,                 cp * sy,               sp])
    right = np.array([sr * sp * cy - cr * sy,  sr * sp * sy + cr * cy, -sr * cp])
    up    = np.array([-(cr * sp * cy + sr * sy), cy * sr - cr * sp * sy, cr * cp])
    return np.column_stack([fwd, right, up])


def fx_from_hfov(W, hfov_deg=KAMERA_HFOV_DEG):
    """YATAY FOV -> odak uzakligi (px). UE kare piksel: fy = fx (distorsiyon yok)."""
    return (W / 2.0) / np.tan(np.radians(hfov_deg) / 2.0)


def kamera_pozu(drone_pos, drone_rot_rpy, tilt_deg=None, tilt_yaw_deg=None, tilt_roll_deg=None):
    """SDK drone konum+rotasyonundan kamera (pos, R_cam) doner.
    drone_rot_rpy: SDK tuple (roll, pitch, yaw). Kamera = govde @ sabit montaj rotasyonu.
    tilt_* None ise MODUL GLOBAL'leri kullanilir (cagri aninda okunur -> kalibre.py
    KAMERA_TILT_DEG'i degistirince aninda etkili olur)."""
    roll, pitch, yaw = drone_rot_rpy
    R_drone = ue_rot_matrix(pitch, yaw, roll)
    tp = KAMERA_TILT_DEG if tilt_deg is None else tilt_deg
    ty = KAMERA_TILT_YAW_DEG if tilt_yaw_deg is None else tilt_yaw_deg
    tr = KAMERA_TILT_ROLL_DEG if tilt_roll_deg is None else tilt_roll_deg
    R_cam = R_drone @ ue_rot_matrix(tp, ty, tr)          # lokal montaj -> sagdan carp
    return np.asarray(drone_pos, float), R_cam


def projekte(p_world, cam_pos, R_cam, fx, W, H):
    """Dunya noktasi -> (u, v) piksel. Kamera arkasi ise None.
    UE kamera lokali: x=ileri, y=saga, z=yukari (pinhole, distorsiyon yok)."""
    v = R_cam.T @ (np.asarray(p_world, float) - cam_pos)
    x, y, z = v
    if x < 1e-6:
        return None
    return (W * 0.5 + fx * y / x, H * 0.5 - fx * z / x)


def keypoints_dunyada(target_pos, target_rot_rpy, kp_local_cm):
    """Hedef poz+rotasyonundan 6 keypoint'in DUNYA konumlarini (cm) verir.
    target_rot_rpy: SDK tuple (roll, pitch, yaw). kp_local_cm: (N,3) UE govde cm."""
    roll, pitch, yaw = target_rot_rpy
    R_t = ue_rot_matrix(pitch, yaw, roll)
    return np.asarray(target_pos, float) + (R_t @ np.asarray(kp_local_cm).T).T


def keypointleri_yukle(path=_KP_JSON):
    """talon_keypoints.json -> (isimler, kp_cm (N,3), flip_idx)."""
    with open(path, "r", encoding="utf-8") as f:
        d = json.load(f)
    return d["keypoint_isimleri"], np.asarray(d["keypoints_cm"], float), d["flip_idx"]


# --- Kendi kendine dogrulama ------------------------------------------------
def _selftest():
    isimler, kp, flip = keypointleri_yukle()
    print("Keypoint (UE govde, cm)  [X=ileri Y=saga Z=yukari]:")
    for ad, (x, y, z) in zip(isimler, kp):
        print(f"  {ad:12s}  X={x:+7.2f}  Y={y:+7.2f}  Z={z:+7.2f}")

    i = {ad: k for k, ad in enumerate(isimler)}
    kanat = np.linalg.norm(kp[i["sol_kanat"]] - kp[i["sag_kanat"]])
    govde = np.linalg.norm(kp[i["burun"]] - kp[i["kuyruk_arka"]])
    print(f"\nKanat acikligi : {kanat:7.2f} cm  (beklenen 171.80)  "
          f"{'OK' if abs(kanat - 171.8) < 0.5 else 'HATA'}")
    print(f"Govde uzunlugu : {govde:7.2f} cm  (~108.7; SDK 110)")

    # Isaret/yon saglamalari (UE govde): burun +X, sag kanat +Y, V-kuyruk +Z(yukari)
    tests = [
        ("burun ileride (+X)",      kp[i["burun"]][0] > 0),
        ("kuyruk geride (-X)",      kp[i["kuyruk_arka"]][0] < 0),
        ("sag kanat sagda (+Y)",    kp[i["sag_kanat"]][1] > 0),
        ("sol kanat solda (-Y)",    kp[i["sol_kanat"]][1] < 0),
        ("V-kuyruklar yukarida(+Z)", kp[i["sol_kuyruk"]][2] > kp[i["kuyruk_arka"]][2]),
        ("L/R kanat simetrik",      abs(kp[i["sol_kanat"]][1] + kp[i["sag_kanat"]][1]) < 0.5),
    ]
    print("\nIsaret/yon saglamalari:")
    for ad, ok in tests:
        print(f"  [{'OK ' if ok else 'HATA'}] {ad}")
    print("\nflip_idx:", flip, "(yatay flip'te sol<->sag takasi — data.yaml'a birebir gider)")


if __name__ == "__main__":
    _selftest()

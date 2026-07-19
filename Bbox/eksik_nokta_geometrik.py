# -*- coding: utf-8 -*-
r"""
Silinen keypoint'leri GEOMETRIYLE geri hesaplama (kesin yontem)
================================================================
JSON'da kamera (konum + acilar + fov) ve drone (konum + acilar) kayitli;
talon modelinin yerel nokta koordinatlari sabittir (oyundaki Lua ile ayni).
Silinen noktanin dunya konumu = drone konumu + (yerel nokta x drone rotasyonu)
Ekran konumu = pinhole projeksiyon (fov 125, 1920x1080) - Lua'nin yaptiginin
birebir Python'u.

GUVENLIK: her karede once KALAN noktalar ayni matematikle yeniden hesaplanir
ve JSON'daki degerlerle karsilastirilir. Hata <= 3 px ise geometriye guvenilir
ve silinen nokta(lar) eklenerek kutu 6 noktadan kurulur; degilse kareye
DOKUNULMAZ (silut yontemiyle bulunan mevcut kutu kalir).

Kullanim:  python eksik_nokta_geometrik.py
"""

import json
import math
import sys
from pathlib import Path

import cv2

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from draw_bbox import compute_bbox, draw_bbox

KOK = Path(__file__).parent
# Rakam isimli TUM alt klasorler otomatik bulunur (1..4 de olur 1..8 de)
KLASORLER = sorted((p.name for p in KOK.iterdir() if p.is_dir() and p.name.isdigit()), key=int)
KONTROL = KOK / "kontrol"
JPEG_KALITE = 90
MAKS_HATA_PX = 3.0   # kalan noktalarin yeniden-projeksiyon hatasi bunu asarsa dokunma

# Oyundaki Lua ile birebir ayni yerel koordinatlar (X-UAV Talon, cm)
KEYPOINTS_LOCAL = {
    "Nose":           (61.11,  -0.07, -2.32),
    "Left_Wingtip":   ( 3.50, -89.00,  4.66),
    "Right_Wingtip":  ( 1.50,  88.91,  5.09),
    "Tail":           (-48.81,  0.03,  0.56),
    "Left_Tail_Fin":  (-38.86, 24.80, 15.16),
    "Right_Tail_Fin": (-37.80,-25.02, 15.61),
}


def rot_matris(pitch, yaw, roll):
    """UE FRotationMatrix eksenleri (Lua'daki RotateVectorScaled ile birebir)."""
    sp, cp = math.sin(math.radians(pitch)), math.cos(math.radians(pitch))
    sy, cy = math.sin(math.radians(yaw)),   math.cos(math.radians(yaw))
    sr, cr = math.sin(math.radians(roll)),  math.cos(math.radians(roll))
    x = (cp*cy, cp*sy, sp)                                   # ileri
    y = (sr*sp*cy - cr*sy, sr*sp*sy + cr*cy, -sr*cp)         # sag
    z = (-(cr*sp*cy + sr*sy), cy*sr - cr*sp*sy, cr*cp)       # yukari
    return x, y, z


def yerel_to_dunya(yerel, drone_loc, drone_rot):
    ax, ay, az = rot_matris(drone_rot["pitch"], drone_rot["yaw"], drone_rot["roll"])
    lx, ly, lz = yerel
    return (drone_loc["x"] + lx*ax[0] + ly*ay[0] + lz*az[0],
            drone_loc["y"] + lx*ax[1] + ly*ay[1] + lz*az[1],
            drone_loc["z"] + lx*ax[2] + ly*ay[2] + lz*az[2])


def projeksiyon(dunya, cam_loc, cam_rot, fov, W=1920, H=1080):
    """Dunya noktasini ekrana izdusurur (UE: X ileri, Y sag, Z yukari)."""
    ax, ay, az = rot_matris(cam_rot["pitch"], cam_rot["yaw"], cam_rot["roll"])
    vx = dunya[0] - cam_loc["x"]
    vy = dunya[1] - cam_loc["y"]
    vz = dunya[2] - cam_loc["z"]
    ileri = vx*ax[0] + vy*ax[1] + vz*ax[2]
    sag   = vx*ay[0] + vy*ay[1] + vz*ay[2]
    yukari= vx*az[0] + vy*az[1] + vz*az[2]
    if ileri <= 1.0:
        return None  # kamera arkasinda
    odak = (W / 2.0) / math.tan(math.radians(fov) / 2.0)
    return (W / 2.0 + odak * sag / ileri,
            H / 2.0 - odak * yukari / ileri)


def main():
    duzeltilen, dokunulmayan, zaten_tam = 0, 0, 0
    hatalar = []

    for k in KLASORLER:
        for jp in sorted((KOK / k).glob("*.json")):  # on-ek fark etmez
            d = json.loads(jp.read_text(encoding="utf-8"))
            kp2 = d.get("keypoints_2d") or {}
            if len(kp2) >= 6:
                zaten_tam += 1
                continue

            cam_loc, cam_rot = d["camera_location"], d["camera_rotation"]
            dr_loc, dr_rot = d["drone_location"], d["drone_rotation"]
            kp3 = d.get("keypoints_3d") or {}

            # --- 1) Yerel model dogru mu? (sakli 3D ile kiyas; olcek=1 kesin) ---
            model_ok = True
            for ad, p3 in kp3.items():
                yerel = KEYPOINTS_LOCAL.get(ad)
                if yerel is None:
                    model_ok = False
                    break
                r = yerel_to_dunya(yerel, dr_loc, dr_rot)
                if math.dist(r, (p3["x"], p3["y"], p3["z"])) > 1.0:  # 1 cm
                    model_ok = False
                    break
            if not model_ok or len(kp3) < 3:
                dokunulmayan += 1
                continue

            # --- 2) Kamerayi KALAN noktalarla kalibre et ---
            # px = cx + odak*Xn ; py = cy - odak*Yn  (Xn=sag/ileri, Yn=yukari/ileri)
            ax, ay, az = rot_matris(cam_rot["pitch"], cam_rot["yaw"], cam_rot["roll"])
            def yon(dunya):
                vx = dunya[0]-cam_loc["x"]; vy = dunya[1]-cam_loc["y"]; vz = dunya[2]-cam_loc["z"]
                ileri = vx*ax[0]+vy*ax[1]+vz*ax[2]
                if ileri <= 1.0: return None
                return ((vx*ay[0]+vy*ay[1]+vz*ay[2])/ileri,
                        (vx*az[0]+vy*az[1]+vz*az[2])/ileri)

            A, b = [], []
            gecerli = True
            for ad, p in kp2.items():
                p3 = kp3.get(ad)
                if p3 is None: gecerli = False; break
                n2 = yon((p3["x"], p3["y"], p3["z"]))
                if n2 is None: gecerli = False; break
                A.append([n2[0], 1.0, 0.0]); b.append(p["x"])
                A.append([-n2[1], 0.0, 1.0]); b.append(p["y"])
            if not gecerli:
                dokunulmayan += 1
                continue
            import numpy as _np
            cozum, *_ = _np.linalg.lstsq(_np.array(A), _np.array(b), rcond=None)
            odak, cx, cy = cozum
            artik = _np.abs(_np.array(A) @ cozum - _np.array(b)).max()
            if artik > MAKS_HATA_PX:
                dokunulmayan += 1
                continue
            hatalar.append(float(artik))

            # --- 3) SILINEN noktalari kalibre projeksiyon ile geri hesapla ---
            noktalar = [(p["x"], p["y"]) for p in kp2.values()]
            for ad, yerel in KEYPOINTS_LOCAL.items():
                if ad in kp2:
                    continue
                n2 = yon(yerel_to_dunya(yerel, dr_loc, dr_rot))
                if n2 is not None:
                    noktalar.append((cx + odak * n2[0], cy - odak * n2[1]))

            # Kutu: 6 noktadan (draw_bbox'in AYNI hesabi, pay=0, sinira kirpma)
            ip = jp.with_suffix(".png")
            img = cv2.imread(str(ip))
            if img is None:
                dokunulmayan += 1
                continue
            h, w = img.shape[:2]
            box = compute_bbox(noktalar, w, h)
            if box is None:
                dokunulmayan += 1
                continue

            x1, y1, x2, y2 = box
            (KOK / k / f"{jp.stem}.txt").write_text(
                f"0 {(x1+x2)/2.0/w:.6f} {(y1+y2)/2.0/h:.6f} "
                f"{(x2-x1)/w:.6f} {(y2-y1)/h:.6f}\n", encoding="utf-8")
            draw_bbox(img, box)
            cv2.imwrite(str(KONTROL / f"{jp.stem}.jpg"), img,
                        [cv2.IMWRITE_JPEG_QUALITY, JPEG_KALITE])
            duzeltilen += 1

    print(f"GEOMETRIK DUZELTILEN: {duzeltilen} kare (silinen nokta geri hesaplandi)")
    print(f"DOKUNULMAYAN: {dokunulmayan} kare (dogrulama tutmadi - silut kutusu kaldi)")
    print(f"ZATEN 6 NOKTA: {zaten_tam} kare")
    if hatalar:
        hatalar.sort()
        print(f"dogrulama hatasi: medyan {hatalar[len(hatalar)//2]:.2f} px, "
              f"maks {hatalar[-1]:.2f} px (esik {MAKS_HATA_PX})")


if __name__ == "__main__":
    main()

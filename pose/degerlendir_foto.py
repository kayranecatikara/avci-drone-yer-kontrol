# -*- coding: utf-8 -*-
"""
================================================================================
 DEGERLENDIR_FOTO — model+PnP'yi FOTO DATASETINDE gercege karsi olc  [Faz 6]
================================================================================
C:\\talon_pose_data\\dataset karelerinde (JSON'da KESIN kamera+talon pozu var):
  1) pose modelini kostur -> 6 keypoint
  2) PozCozucu (PnP) -> mesafe + hedef dunya yaw
  3) Gercekle kiyasla: mesafe MAE/%, yaw MAE (mesafe binlerine gore tablo)
  4) Ornek kareleri isaretle (tahmin=RENKLI nokta+iskelet, gercek=BEYAZ arti)
     -> C:\\talon_pose_data\\pnp_degerlendirme\\   + rapor.csv

!!! DIKKAT: bu kareler modelin EGITIM VERISI (talon_v10 bunlardan uretildi) —
sonuclar IYIMSER ust sinirdir. Gercek kalite canli ucusta gorulur; burasi
"boru hatti dogru mu + model hic degilse egitim dagiliminda ise yariyor mu"
sorusunu cevaplar.

Kullanim (repo kokunden):
    python pose\\degerlendir_foto.py                 # tum kareler, 36 ornek gorsel
    python pose\\degerlendir_foto.py --sayi 100 --gorsel 20
"""
import os
import sys
import csv
import json
import glob
import argparse

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _KOK not in sys.path:
    sys.path.insert(0, _KOK)

import numpy as np
import cv2

from pose import geometri
from pose.poz_cozucu import PozCozucu, EGITIM_SIRASI
from pose.sira_bul import gt_noktalar, REF_SIRA

MODEL_YOL = os.path.join(_KOK, "models", "talon_pose.pt")   # aktif poz modeli (v3, imgsz=1280)
IMGSZ = 1280                                                 # egitim imgsz'i (v3; eski model 960 idi)
DATASET = r"C:\talon_pose_data\dataset"
CIKTI = r"C:\talon_pose_data\pnp_degerlendirme"

# Renkler REF indeksine gore (onizle.py ile ayni): burun,solK,sagK,solKuy,sagKuy,kuyArk
RENK_REF = [(0, 0, 255), (0, 255, 0), (0, 200, 255), (255, 128, 0),
            (255, 0, 255), (255, 255, 0)]
ISKELET_REF = [(0, 5), (1, 2), (0, 1), (0, 2), (3, 5), (4, 5), (3, 4)]
BIN_SINIR_M = [0, 5, 10, 15, 20, 30, 1e9]
BIN_AD = ["0-5", "5-10", "10-15", "15-20", "20-30", "30+"]


def _aci_fark(a, b):
    return abs((a - b + 180.0) % 360.0 - 180.0)


def _ciz(img, kxy, kcf, gt_uv, satirlar):
    """Tahmin (renkli, model->ref renk esleme) + gercek (beyaz arti) + bilgi bloku."""
    for a, b in ISKELET_REF:                       # iskelet: ref cifti -> model indeksleri
        ma, mb = EGITIM_SIRASI.index(a), EGITIM_SIRASI.index(b)
        if kcf[ma] > 0.25 and kcf[mb] > 0.25:
            pa = tuple(np.round(kxy[ma]).astype(int))
            pb = tuple(np.round(kxy[mb]).astype(int))
            cv2.line(img, pa, pb, (255, 255, 255), 1, cv2.LINE_AA)
    for mi in range(6):
        ref = EGITIM_SIRASI[mi]
        if kcf[mi] > 0.25:
            c = tuple(np.round(kxy[mi]).astype(int))
            cv2.circle(img, c, 5, RENK_REF[ref], -1, cv2.LINE_AA)
            cv2.circle(img, c, 5, (0, 0, 0), 1, cv2.LINE_AA)
    for ref, p in enumerate(gt_uv):
        if p is not None:
            cv2.drawMarker(img, (int(round(p[0])), int(round(p[1]))), (255, 255, 255),
                           cv2.MARKER_CROSS, 10, 1, cv2.LINE_AA)
    y = 26
    for s in satirlar:
        cv2.putText(img, s, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(img, s, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 1, cv2.LINE_AA)
        y += 24
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sayi", type=int, default=0, help="islenecek kare (0=hepsi)")
    ap.add_argument("--gorsel", type=int, default=36, help="isaretlenecek ornek kare sayisi")
    ap.add_argument("--conf", type=float, default=0.20, help="tespit conf esigi")
    args = ap.parse_args()

    from ultralytics import YOLO
    model = YOLO(MODEL_YOL)
    pc = PozCozucu(conf_esik=0.5, ema_alpha=0.0)    # kare-bagimsiz olcum: EMA/tasima yok

    jler = sorted(glob.glob(os.path.join(DATASET, "*.json")))
    if args.sayi:
        idx = np.linspace(0, len(jler) - 1, min(args.sayi, len(jler))).round().astype(int)
        jler = [jler[i] for i in sorted(set(idx))]
    os.makedirs(CIKTI, exist_ok=True)
    gorsel_idx = set(np.linspace(0, len(jler) - 1, min(args.gorsel, len(jler)))
                     .round().astype(int).tolist()) if args.gorsel else set()

    print("[EVAL] %d kare | model=%s" % (len(jler), os.path.basename(MODEL_YOL)))
    print("[EVAL] UYARI: kareler egitim dagilimindan -> sonuc IYIMSER ust sinir.\n")

    kayitlar = []            # (gt_m, pred_m, yaw_err, rms, n_kp)
    n_tespit_yok, n_pnp_yok = 0, 0

    for k, jf in enumerate(jler):
        png = jf[:-5] + ".png"
        if not os.path.exists(png):
            continue
        with open(jf, encoding="utf-8") as f:
            data = json.load(f)
        cam = data["camera_location"]; tal = data.get("drone_location") or data["talon_location"]
        crot = data["camera_rotation"]
        trot = data.get("drone_rotation") or data.get("talon_rotation")
        gt_cm = float(np.linalg.norm([tal["x"] - cam["x"], tal["y"] - cam["y"],
                                      tal["z"] - cam["z"]]))

        res = model.predict(png, imgsz=IMGSZ, conf=args.conf, verbose=False)[0]
        H, W = res.orig_shape
        secilen = None
        if res.keypoints is not None and len(res.boxes) > 0:
            i = int(res.boxes.conf.argmax())
            kxy = res.keypoints.xy[i].cpu().numpy()
            kcf = (res.keypoints.conf[i].cpu().numpy()
                   if res.keypoints.conf is not None else np.ones(6))
            secilen = (kxy, kcf)
        if secilen is None:
            n_tespit_yok += 1
            continue

        kxy, kcf = secilen
        pc.sifirla()                                  # her kare bagimsiz cozulsun
        poz = pc.coz(kxy, kcf, W, H)
        if poz is None:
            n_pnp_yok += 1
            continue

        R_cam = geometri.ue_rot_matrix(crot["pitch"], crot["yaw"], crot["roll"])
        yw, _pt = PozCozucu.dunya_yonelim_kamera_pozuyla(poz, R_cam, ema=False)
        yaw_err = _aci_fark(yw, float(trot["yaw"]))
        kayitlar.append((gt_cm / 100.0, poz["mesafe_cm"] / 100.0, yaw_err,
                         poz["rms_px"], poz["n_kp"]))

        if k in gorsel_idx:
            img = cv2.imread(png)
            gt_uv = gt_noktalar(data, W, H)
            sat = ["KAM d=%.1f m   GERCEK d=%.1f m   (hata %+.1f m)"
                   % (poz["mesafe_cm"] / 100, gt_cm / 100,
                      (poz["mesafe_cm"] - gt_cm) / 100),
                   "KAM yaw=%.0f   GERCEK yaw=%.0f   (hata %.1f der)"
                   % (yw % 360, float(trot["yaw"]) % 360, yaw_err),
                   "rms=%.1f px  n_kp=%d  aspect=%.0f der"
                   % (poz["rms_px"], poz["n_kp"], poz["aspect_deg"])]
            _ciz(img, kxy, kcf, gt_uv, sat)
            cv2.imwrite(os.path.join(
                CIKTI, os.path.basename(png).replace(".png", "_pnp.png")), img)

    n = len(kayitlar)
    toplam = n + n_tespit_yok + n_pnp_yok
    print("[EVAL] kare: %d | PnP cozuldu: %d (%%%.0f) | tespit yok: %d | PnP red: %d"
          % (toplam, n, 100.0 * n / max(toplam, 1), n_tespit_yok, n_pnp_yok))
    if n == 0:
        print("[EVAL] hic cozum yok — model/boru hatti kontrol."); return 1

    a = np.array(kayitlar)                            # gt_m, pred_m, yaw_err, rms, n_kp
    hata = a[:, 1] - a[:, 0]
    pct = 100.0 * np.abs(hata) / a[:, 0]
    print("\nGENEL:  mesafe MAE=%.2f m (medyan %.2f)  |hata| %%%.1f (medyan %%%.1f)"
          % (np.abs(hata).mean(), np.median(np.abs(hata)), pct.mean(), np.median(pct)))
    print("        mesafe BIAS=%+.2f m (sistematik)  yaw MAE=%.1f der (medyan %.1f)"
          % (hata.mean(), a[:, 2].mean(), np.median(a[:, 2])))

    print("\nMESAFE BINLERINE GORE  (hedef: <20 m'de mesafe <%5, yaw <10 der):")
    print("%8s %6s %10s %9s %9s %8s" % ("bin(m)", "n", "d MAE(m)", "|d| %", "yaw MAE", "rms px"))
    for bi in range(len(BIN_AD)):
        m = (a[:, 0] >= BIN_SINIR_M[bi]) & (a[:, 0] < BIN_SINIR_M[bi + 1])
        if not m.any():
            print("%8s %6d %10s" % (BIN_AD[bi], 0, "-")); continue
        print("%8s %6d %10.2f %9.1f %9.1f %8.1f"
              % (BIN_AD[bi], m.sum(), np.abs(hata[m]).mean(), pct[m].mean(),
                 a[m, 2].mean(), a[m, 3].mean()))

    yol = os.path.join(CIKTI, "rapor.csv")
    with open(yol, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["gt_m", "pred_m", "yaw_err_deg", "rms_px", "n_kp"])
        w.writerows(kayitlar)
    print("\n[EVAL] rapor.csv + %d ornek gorsel -> %s" % (len(gorsel_idx), CIKTI))
    return 0


if __name__ == "__main__":
    sys.exit(main())

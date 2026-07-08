# -*- coding: utf-8 -*-
"""
POSE MODELI KEYPOINT SIRASI DOGRULAMA (kural 8: takimca dogrulanabilir).
================================================================================
Yeni bir pose modeli entegre edilince, kanat uclarinin BEKLENEN index'te
(sol=1, sag=2) oldugunu ampirik dogrular. Roll -> ongorulu yaw lead bu index'lere
bagli (guidance/ibvs_gorsel.kanat_roll_img); yanlis index = yanlis bank.

YONTEM: kanat acikligi (wingspan) planformun EN BUYUK boyutudur -> tespit
karelerinde EN-UZAK keypoint cifti tutarli sekilde (1,2) cikmali. Ayrica seviye/
arkadan karelerde index 1 (sol) index 2'den (sag) daha kucuk x'te olmali.

KULLANIM:
    python araclar/kp_sira_dogrula.py [model_yolu] [kare_klasoru]
    # varsayilan: models/talon_pose.pt + son ham oturum
Beklenen cikti: "EN-UZAK-CIFT (wingspan)" dagiliminin C%100'u (1, 2).
Degilse pose/poz_cozucu.EGITIM_SIRASI ve ibvs_gorsel kanat index'leri gozden gecir.
"""
import glob
import os
import sys
from collections import Counter

import numpy as np
from ultralytics import YOLO

_HERE = os.path.dirname(os.path.abspath(__file__))
_KOK = os.path.dirname(_HERE)


def _son_oturum(kok=r"C:\talon_pose_data\ham"):
    ler = sorted(glob.glob(os.path.join(kok, "oturum_*")))
    for d in reversed(ler):
        if glob.glob(os.path.join(d, "kare_*.png")):
            return d
    return None


def main():
    model_yolu = sys.argv[1] if len(sys.argv) > 1 else os.path.join(_KOK, "models", "talon_pose.pt")
    klasor = sys.argv[2] if len(sys.argv) > 2 else _son_oturum()
    if not klasor or not os.path.isdir(klasor):
        print("Kare klasoru bulunamadi; ikinci argumanla ver: python araclar/kp_sira_dogrula.py <model> <klasor>")
        return 1
    m = YOLO(model_yolu)
    kareler = sorted(glob.glob(os.path.join(klasor, "kare_*.png")))[::10]
    print("model:", model_yolu, "| task:", m.task, "| ornek kare:", len(kareler))

    max_cift = Counter()
    kp_conf = np.zeros(6)
    n_det = sol1 = 0
    for f in kareler:
        r = m.predict(f, imgsz=1280, conf=0.35, verbose=False)[0]
        if r.keypoints is None or r.boxes is None or len(r.boxes) == 0:
            continue
        i = int(r.boxes.conf.argmax())
        kxy = r.keypoints.xy[i].cpu().numpy()
        kcf = (r.keypoints.conf[i].cpu().numpy() if r.keypoints.conf is not None else np.ones(6))
        if kxy.shape[0] != 6:
            continue
        n_det += 1
        kp_conf += kcf
        best, bd = None, -1.0
        for a in range(6):
            for b in range(a + 1, 6):
                d = float(np.hypot(*(kxy[a] - kxy[b])))
                if d > bd:
                    bd, best = d, (a, b)
        max_cift[best] += 1
        if kxy[1][0] < kxy[2][0]:
            sol1 += 1

    print("\ntespit: %d / %d" % (n_det, len(kareler)))
    if n_det:
        print("ortalama keypoint conf (model sirasi 0..5):",
              [round(x / n_det, 2) for x in kp_conf])
        print("EN-UZAK-CIFT (wingspan adayi) dagilimi:")
        for cift, s in max_cift.most_common():
            isaret = "  <-- BEKLENEN (kanat uclari)" if cift == (1, 2) else ""
            print("   %s -> %d%s" % (cift, s, isaret))
        print("index1 (sol) x < index2 (sag) x: %d / %d kare (seviye/arkadan beklenen)" % (sol1, n_det))
        ok = max_cift.most_common(1)[0][0] == (1, 2)
        print("\nSONUC:", "OK — kanat uclari (1,2), EGITIM_SIRASI degismesin"
              if ok else "DIKKAT — en-uzak-cift (1,2) DEGIL; keypoint sirasini gozden gecir")
        return 0 if ok else 2
    print("Hic tespit yok — hedefli kare iceren bir oturum ver.")
    return 1


if __name__ == "__main__":
    sys.exit(main())

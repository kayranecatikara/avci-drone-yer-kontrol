# -*- coding: utf-8 -*-
"""
================================================================================
 SIRA_BUL — pose modelinin KEYPOINT SIRASINI deneysel kesfet + hizli kalite bakisi
================================================================================
Problem: talon_yolo11m_pose_2_best.pt Colab'da egitildi (talon_v10); etiketleri
ureten donusumun KEYPOINT SIRASI elimizde yok. PnP icin "model cikti indeksi ->
hangi anatomik nokta (burun/kanat/kuyruk...)" eslesmesi SART.

Cozum: dataset karelerinde (C:\\talon_pose_data\\dataset, JSON'da KESIN kamera pozu
var) modeli kostur; tahmin edilen 6 noktayi, bilinen 3D noktalarin (KEYPOINTS_LOCAL
+ MESH_PIVOT_OFFSET — etiket uretimiyle AYNI) projeksiyonuyla eslestir (kare basina
min-toplam-mesafe permutasyonu = n=6 icin kesin Hungarian). Kareler uzerinden oy
toplayip kararli eslesmeyi bul.

AYNI ANDA bedava cikan teshisler:
  * flip_idx sagligi: sol/sag kanat oylari ~yari yariya bolunuyorsa egitimde
    fliplr sol<->sag takasini OGRENEMEMIS demektir (sinsi hata).
  * keypoint piksel hatasi (egitim verisinde -> iyimser ust sinir).

Kullanim (repo kokunden):  python pose\\sira_bul.py [--sayi 120] [--conf 0.25]
"""
import os
import sys
import json
import glob
import argparse
import itertools

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _KOK not in sys.path:
    sys.path.insert(0, _KOK)

import numpy as np

from pose.draw_keypoint import (KEYPOINTS_LOCAL, MESH_PIVOT_OFFSET, TALON_SCALE,
                                local_to_world, project_world_to_screen)

# Anatomik nokta adlari (talon_keypoints.json sirasi = PnP/pipeline REFERANS sirasi)
REF_SIRA = ["burun", "sol_kanat", "sag_kanat", "sol_kuyruk", "sag_kuyruk", "kuyruk_arka"]
# draw_keypoint KEYPOINTS_LOCAL adlari -> referans adlar
AD_ESLE = {"nose": "burun", "left_wingtip": "sol_kanat", "right_wingtip": "sag_kanat",
           "left_tail_fin": "sol_kuyruk", "right_tail_fin": "sag_kuyruk", "tail": "kuyruk_arka"}

MODEL_YOL_VARSAYILAN = os.path.join(_KOK, "talon_yolo11m_pose_2_best.pt")
DATASET_VARSAYILAN = r"C:\talon_pose_data\dataset"


def gt_noktalar(data, W, H):
    """JSON kare verisinden 6 gercek 2D nokta (REF_SIRA sirasinda). None'li liste."""
    fov = float(data.get("camera_fov", 125.0))
    cam_loc, cam_rot = data["camera_location"], data["camera_rotation"]
    tal_loc = data.get("drone_location") or data.get("talon_location")
    tal_rot = data.get("drone_rotation") or data.get("talon_rotation")
    uv = {}
    for ad, lokal in KEYPOINTS_LOCAL.items():
        w = local_to_world(lokal, tal_loc, tal_rot, MESH_PIVOT_OFFSET, TALON_SCALE)
        uv[AD_ESLE[ad]] = project_world_to_screen(w, cam_loc, cam_rot, fov, W, H)
    return [uv[ad] for ad in REF_SIRA]


def kare_esle(pred_uv, pred_conf, gt_uv, conf_esik):
    """Tek karede pred index -> GT index atamasi (min toplam mesafe permutasyonu).
    Dusuk conf'lu pred'ler ve None GT'ler es disi birakilir. (atama, maliyet) doner."""
    gecerli_p = [i for i in range(6) if pred_conf[i] >= conf_esik]
    gecerli_g = [j for j in range(6) if gt_uv[j] is not None]
    if len(gecerli_p) < 4 or len(gecerli_g) < 4:
        return None, None
    n = min(len(gecerli_p), len(gecerli_g))
    en_iyi, en_maliyet = None, None
    # kucuk n icin butun permutasyonlar (<=720) — kesin cozum, scipy gerekmez
    for perm in itertools.permutations(gecerli_g, n):
        m = 0.0
        for k in range(n):
            p, g = gecerli_p[k], perm[k]
            m += float(np.hypot(pred_uv[p][0] - gt_uv[g][0], pred_uv[p][1] - gt_uv[g][1]))
        if en_maliyet is None or m < en_maliyet:
            en_maliyet, en_iyi = m, {gecerli_p[k]: perm[k] for k in range(n)}
    return en_iyi, en_maliyet / n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sayi", type=int, default=120, help="islenecek kare sayisi")
    ap.add_argument("--conf", type=float, default=0.25, help="keypoint conf esigi")
    ap.add_argument("--model", default=MODEL_YOL_VARSAYILAN)
    ap.add_argument("--dataset", default=DATASET_VARSAYILAN)
    args = ap.parse_args()

    from ultralytics import YOLO
    model = YOLO(args.model)
    print("[SIRA] model: %s  (kpt_shape=%s)" % (os.path.basename(args.model),
                                                model.model.kpt_shape))

    jler = sorted(glob.glob(os.path.join(args.dataset, "*.json")))
    if not jler:
        print("[HATA] dataset bos:", args.dataset); return 1
    idx = np.linspace(0, len(jler) - 1, min(args.sayi, len(jler))).round().astype(int)
    secili = [jler[i] for i in sorted(set(idx))]
    print("[SIRA] %d/%d kare islenecek" % (len(secili), len(jler)))

    oylar = np.zeros((6, 6), int)     # oylar[pred_i, gt_j]
    px_hatalar = []                   # eslesen ciftlerin px mesafesi
    tespit_yok = 0
    kullanilan = 0

    for jf in secili:
        png = jf[:-5] + ".png"
        if not os.path.exists(png):
            continue
        with open(jf, encoding="utf-8") as f:
            data = json.load(f)
        res = model.predict(png, imgsz=960, conf=0.20, verbose=False)[0]
        if res.keypoints is None or len(res.boxes) == 0:
            tespit_yok += 1
            continue
        i = int(res.boxes.conf.argmax())
        kxy = res.keypoints.xy[i].cpu().numpy()          # (6,2) px
        kcf = (res.keypoints.conf[i].cpu().numpy()
               if res.keypoints.conf is not None else np.ones(6))
        H, W = res.orig_shape
        gt = gt_noktalar(data, W, H)
        atama, ort = kare_esle(kxy, kcf, gt, args.conf)
        if atama is None:
            continue
        kullanilan += 1
        for p, g in atama.items():
            oylar[p, g] += 1
            px_hatalar.append(float(np.hypot(kxy[p][0] - gt[g][0], kxy[p][1] - gt[g][1])))

    print("\n[SIRA] kullanilan kare: %d  (tespitsiz: %d)" % (kullanilan, tespit_yok))
    if kullanilan == 0:
        print("[HATA] hic kare eslesmedi — model/veri uyumsuz mu?"); return 1

    print("\nOY MATRISI  (satir=model cikti indeksi, sutun=anatomik nokta):")
    print("%8s" % "", "  ".join("%11s" % a for a in REF_SIRA))
    for p in range(6):
        print("%8s" % ("pred[%d]" % p), "  ".join("%11d" % oylar[p, g] for g in range(6)))

    # kararli eslesme: her pred icin en cok oy alan GT + guven yuzdesi
    print("\nKARARLI ESLESME (pred index -> anatomik nokta):")
    esleme = []
    for p in range(6):
        top = oylar[p].sum()
        g = int(oylar[p].argmax())
        yuzde = 100.0 * oylar[p, g] / top if top else 0.0
        esleme.append(g)
        uyari = ""
        if yuzde < 85.0:
            uyari = "  <-- KARARSIZ! (flip_idx / sol-sag karisikligi olabilir)"
        print("  pred[%d] -> %-11s  (%%%.1f oy)%s" % (p, REF_SIRA[g], yuzde, uyari))
    if sorted(esleme) != list(range(6)):
        print("  !!! Eslesme PERMUTASYON DEGIL (iki pred ayni noktaya gitti) — dikkat.")

    a = np.array(px_hatalar)
    print("\nKEYPOINT PIKSEL HATASI (egitim karelerinde -> IYIMSER ust sinir):")
    print("  ortalama=%.1f px  medyan=%.1f px  p90=%.1f px  (n=%d)"
          % (a.mean(), np.median(a), np.percentile(a, 90), a.size))
    print("\nPython listesi (poz_cozucu icin):  EGITIM_SIRASI = %r" % (esleme,))
    print("(anlami: model cikti indeksi k, talon_keypoints.json'daki %r indeksli noktadir)"
          % ([REF_SIRA[g] for g in esleme],))
    return 0


if __name__ == "__main__":
    sys.exit(main())

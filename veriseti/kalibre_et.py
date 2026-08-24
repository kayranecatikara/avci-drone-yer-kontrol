# -*- coding: utf-8 -*-
"""
================================================================================
 KALIBRE ET — elle duzeltilmis karelerden DUZELTME MODELI ogren
================================================================================
GELISTIRME ARACI — teslim paketine girmez.

DERT: truth projeksiyonu kutuyu dogru yere koyuyor ama tam oturmuyor. Ilk
denemede tek bir SABIT ofset (+4 px) takildi -- zayifti, cunku hata sabit degil:
hedef bankadayken, uzaktayken, belli bir bakis acisindayken FARKLI davraniyor.

COZUM: artigi (insan kutusu - projeksiyon kutusu) olculebilir buyuklukIerin
fonksiyonu olarak ogren. Model, kutunun KENDI boyutuna gore normalize calisir
-> 100 px'lik kutuda ogrendigi duzeltme 30 px'lik kutuda oranli uygulanir.

  hedefler (4 ayri regresyon):
      ex = (cx_insan - cx_proj) / w_proj      yatay kayma, kutu genisligi biriminde
      ey = (cy_insan - cy_proj) / h_proj      dikey kayma
      lw = log(w_insan / w_proj)              genislik olcegi (log -> simetrik)
      lh = log(h_insan / h_proj)              yukseklik olcegi

  ozellikler (hepsi kareden BAGIMSIZ olcum, uydurma yok):
      1                       sabit terim (eski tek-ofsetin karsiligi)
      sin(roll), cos(roll)    hedefin banka acisi -- kanat silueti bununla doner
      |sin(roll)|             yon bagimsiz banka siddeti
      sin(aspect), cos(aspect)  bakis acisi (arkadan/yandan) -- siluet uzunlugu
      log(menzil)             mesafe (uzakta kutu kucuk, kirpma/gurultu artar)
      log(kutu kisa kenari)   piksel olcegi

YONTEM: ridge regresyon (kucuk lambda, ozellikler standartlastirilmis).
DOGRULAMA: K-katli capraz dogrulama. Model AYNI veriye uydurulup ayni veride
olculurse her zaman "iyi" gorunur; burada her kat DISARIDA BIRAKILIR ve iyilesme
GORULMEMIS karelerde olculur. Rapor edilen sayi odur.

GUVENLIK: hicbir etiket bu araçla YAZILMAZ. Cikti sadece model dosyasidir
(kalibrasyon.json); uygulamayi veriseti/oto_etiket.py --kalibrasyon yapar.

KULLANIM
    python veriseti/kalibre_et.py --klasor C:\\...\\talon_pozitif --gozden-gecirilen 770
    python veriseti/kalibre_et.py --klasor ... --gozden-gecirilen 770 --kat 5
================================================================================
"""
import os
import sys
import json
import math
import argparse

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _KOK not in sys.path:
    sys.path.insert(0, _KOK)

import numpy as np

from pose import geometri
from veriseti.negatif_topla import KP_CM, kutu_zarfi
from veriseti.bbox_etiketle import (telemetri_oku, yolo_oku, Akis, kare_listesi)


# =============================================================================
#  Saf cekirdek (birim testli: tests/test_kalibre.py)
# =============================================================================

def ozellikler(roll_deg, aspect_deg, menzil_m, kisa_kenar_px):
    """Bir karenin ozellik vektoru. Sirasi MODEL DOSYASINA yazilir; degistirmek
    eski modelleri gecersiz kilar (uygula() sirayi dosyadan okur)."""
    r = math.radians(roll_deg)
    a = math.radians(aspect_deg)
    return [1.0,
            math.sin(r), math.cos(r), abs(math.sin(r)),
            math.sin(a), math.cos(a),
            math.log(max(menzil_m, 1.0)),
            math.log(max(kisa_kenar_px, 1.0))]


OZELLIK_AD = ["sabit", "sin_roll", "cos_roll", "abs_sin_roll",
              "sin_aspect", "cos_aspect", "log_menzil", "log_kenar"]


def ridge_cozum(X, y, lam=1.0):
    """Standartlastirilmis ridge. -> katsayi vektoru (X'in sutun sayisi kadar).

    Sabit terim CEZALANDIRILMAZ (aksi halde model ortalamayi kaciriyor)."""
    X = np.asarray(X, float); y = np.asarray(y, float)
    n, p = X.shape
    C = np.eye(p) * lam
    C[0, 0] = 0.0                      # sabit terime ceza yok
    return np.linalg.solve(X.T @ X + C, X.T @ y)


def kutu_duzelt(kutu, kats, ozl):
    """Projeksiyon kutusuna ogrenilen duzeltmeyi uygula. -> yeni kutu

    ex/ey kutunun KENDI boyutuyla olceklenir, w/h log-oranla carpilir; boylece
    ayni model her mesafede tutarli calisir."""
    x0, y0, x1, y1 = kutu
    w, h = x1 - x0, y1 - y0
    if w <= 0 or h <= 0:
        return list(kutu)
    v = np.asarray(ozl, float)
    ex = float(np.dot(kats["ex"], v))
    ey = float(np.dot(kats["ey"], v))
    lw = float(np.dot(kats["lw"], v))
    lh = float(np.dot(kats["lh"], v))
    cx = (x0 + x1) / 2.0 + ex * w
    cy = (y0 + y1) / 2.0 + ey * h
    # log-oran +-0.7 ile sinirli (2x buyume/kucule) -- asiri duzeltme guvenligi
    nw = w * math.exp(max(-0.7, min(lw, 0.7)))
    nh = h * math.exp(max(-0.7, min(lh, 0.7)))
    return [cx - nw / 2, cy - nh / 2, cx + nw / 2, cy + nh / 2]


def iou(a, b):
    x0 = max(a[0], b[0]); y0 = max(a[1], b[1])
    x1 = min(a[2], b[2]); y1 = min(a[3], b[3])
    if x1 <= x0 or y1 <= y0:
        return 0.0
    k = (x1 - x0) * (y1 - y0)
    return k / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - k)


def katlara_bol(n, kat, tohum=0):
    """Deterministik K-kat bolme. -> her ornek icin kat indeksi (0..kat-1)."""
    rng = np.random.RandomState(tohum)
    idx = rng.permutation(n)
    bolum = np.zeros(n, dtype=int)
    for k in range(kat):
        bolum[idx[k::kat]] = k
    return bolum


# =============================================================================
#  Veri toplama
# =============================================================================

def aspect_acisi(dpos, tpos, tyaw_deg):
    """Kamera-hedef gorus dogrultusu ile hedefin BURUN yonu arasindaki aci (0-180).
    0 = tam arkadan bakiyoruz, 90 = yandan, 180 = karsidan."""
    los = np.asarray(tpos, float)[:2] - np.asarray(dpos, float)[:2]
    n = np.linalg.norm(los)
    if n < 1e-6:
        return 0.0
    los = los / n
    y = math.radians(tyaw_deg)
    ileri = np.array([math.cos(y), math.sin(y)])
    return math.degrees(math.acos(max(-1.0, min(1.0, float(np.dot(los, ileri))))))


def veri_topla(klasor, ad, gozden_gecirilen, marj_x, marj_y, dt):
    """Insan tarafindan GOZDEN GECIRILMIS karelerden ornek toplar.

    ONEMLI: "duzeltilmis" degil "GOZDEN GECIRILMIS" alinir. Yalnizca degistirilen
    kareleri almak SECIM YANLILIGI yaratir -- model, duzeltme gerektiren zor
    karelerin dagilimini ogrenip iyi kareleri de bozar. Insanin Enter'layip
    onayladigi kare de bir cevaptir ve sete girer."""
    tel = telemetri_oku(klasor)
    akis = Akis(os.path.join(klasor, "telemetri_akis.jsonl"))
    ornek = []
    for png in kare_listesi(klasor, ad):
        base = os.path.basename(png)
        try:
            no = int(os.path.splitext(base)[0][len(ad) + 1:])
        except ValueError:
            continue
        if no > gozden_gecirilen:
            continue
        sat = tel.get(base)
        if not sat or sat.get("truth_target_pos") is None:
            continue
        if len(akis) < 2 or not akis.kapsar(sat["t"] - dt):
            continue                     # gecikme telafisi yapilamayan kare
        W, H = int(sat["W"]), int(sat["H"])
        txt = os.path.splitext(png)[0] + ".txt"
        try:
            with open(txt, encoding="utf-8") as f:
                insan = yolo_oku(f.readline(), W, H)
        except OSError:
            insan = None
        if insan is None:
            continue
        d = akis.durum(sat["t"] - dt)
        dpos, drot, tpos, trot = (np.asarray(v, float) for v in d)
        cam, R = geometri.kamera_pozu(dpos, drot)
        fx = geometri.fx_from_hfov(W)
        uvs = [geometri.projekte(q, cam, R, fx, W, H)
               for q in geometri.keypoints_dunyada(tpos, trot, KP_CM)]
        if any(u is None for u in uvs):
            continue
        proj = list(kutu_zarfi(uvs, marj_x, marj_y))
        pw, ph = proj[2] - proj[0], proj[3] - proj[1]
        if pw <= 2 or ph <= 2:
            continue
        menzil = float(np.linalg.norm(tpos - dpos)) / 100.0
        asp = aspect_acisi(dpos, tpos, float(trot[2]))
        ozl = ozellikler(float(trot[0]), asp, menzil, min(pw, ph))
        ornek.append({"ad": base, "proj": proj, "insan": insan, "ozl": ozl,
                      "roll": abs(float(trot[0])), "menzil": menzil})
    return ornek


# =============================================================================
#  Ana
# =============================================================================

def main(argv=None):
    ap = argparse.ArgumentParser(description="Elle duzeltmelerden duzeltme modeli ogren")
    ap.add_argument("--klasor", required=True)
    ap.add_argument("--ad", default="talon1")
    ap.add_argument("--gozden-gecirilen", type=int, required=True,
                    help="bu NUMARAYA kadar olan kareler insan tarafindan gozden gecirildi")
    ap.add_argument("--marj-x", type=float, default=0.07)
    ap.add_argument("--marj-y", type=float, default=0.10)
    ap.add_argument("--dt", type=float, default=0.10)
    ap.add_argument("--kat", type=int, default=5, help="capraz dogrulama kat sayisi")
    ap.add_argument("--lam", type=float, default=1.0, help="ridge cezasi")
    ap.add_argument("--cikti", default="")
    args = ap.parse_args(argv)

    print("=" * 66)
    ornek = veri_topla(args.klasor, args.ad, args.gozden_gecirilen,
                       args.marj_x, args.marj_y, args.dt)
    print("  GOZDEN GECIRILMIS ornek: %d kare (talon1_0000..%04d)"
          % (len(ornek), args.gozden_gecirilen))
    if len(ornek) < 50:
        print("  [HATA] cok az ornek, model ogrenilemez.")
        return 2

    X = np.array([o["ozl"] for o in ornek], float)
    # standartlastir (sabit terim haric) -- olcek farki ridge cezasini bozar
    ort = X.mean(axis=0); std = X.std(axis=0)
    ort[0] = 0.0; std[0] = 1.0
    std[std < 1e-9] = 1.0
    Xs = (X - ort) / std

    Y = {}
    for o in ornek:
        px0, py0, px1, py1 = o["proj"]; pw, ph = px1 - px0, py1 - py0
        ix0, iy0, ix1, iy1 = o["insan"]; iw, ih = ix1 - ix0, iy1 - iy0
        Y.setdefault("ex", []).append(((ix0 + ix1) / 2 - (px0 + px1) / 2) / pw)
        Y.setdefault("ey", []).append(((iy0 + iy1) / 2 - (py0 + py1) / 2) / ph)
        Y.setdefault("lw", []).append(math.log(max(iw, 1e-6) / pw))
        Y.setdefault("lh", []).append(math.log(max(ih, 1e-6) / ph))
    Y = {k: np.asarray(v, float) for k, v in Y.items()}

    # ---- CAPRAZ DOGRULAMA: her kat DISARIDA, iyilesme GORULMEMIS karelerde ----
    bolum = katlara_bol(len(ornek), args.kat, tohum=0)
    taban_iou, model_iou, ofset_iou = [], [], []
    for k in range(args.kat):
        eg = bolum != k
        te = bolum == k
        kats = {ad: ridge_cozum(Xs[eg], Y[ad][eg], args.lam) for ad in Y}
        # kiyas icin: SADECE sabit ofset (eski basit yontem), ayni egitim katinda
        ofs_x = float(np.mean([(o["insan"][0] + o["insan"][2]) / 2
                               - (o["proj"][0] + o["proj"][2]) / 2
                               for o, m in zip(ornek, eg) if m]))
        ofs_y = float(np.mean([(o["insan"][1] + o["insan"][3]) / 2
                               - (o["proj"][1] + o["proj"][3]) / 2
                               for o, m in zip(ornek, eg) if m]))
        for i, o in enumerate(ornek):
            if not te[i]:
                continue
            taban_iou.append(iou(o["proj"], o["insan"]))
            model_iou.append(iou(kutu_duzelt(o["proj"], kats, Xs[i]), o["insan"]))
            p = o["proj"]
            ofset_iou.append(iou([p[0] + ofs_x, p[1] + ofs_y,
                                  p[2] + ofs_x, p[3] + ofs_y], o["insan"]))
    taban_iou = np.array(taban_iou); model_iou = np.array(model_iou)
    ofset_iou = np.array(ofset_iou)

    print("-" * 66)
    print("  %d-KAT CAPRAZ DOGRULAMA (hepsi GORULMEMIS karelerde)" % args.kat)
    print("  %-26s %8s %8s %8s %8s" % ("", "ort", "medyan", ">=0.7", "<0.5"))
    for ad, v in (("ham projeksiyon", taban_iou),
                  ("+ sabit ofset (eski)", ofset_iou),
                  ("+ OGRENILEN MODEL", model_iou)):
        print("  %-26s %8.4f %8.4f %7.0f%% %7.0f%%"
              % (ad, v.mean(), np.median(v), 100 * (v >= 0.7).mean(),
                 100 * (v < 0.5).mean()))
    kazanc = model_iou.mean() - taban_iou.mean()
    print("  KAZANC (model - ham): %+.4f IoU   (sabit ofsete gore %+.4f)"
          % (kazanc, model_iou.mean() - ofset_iou.mean()))

    # zor kesitte de bakalim -- ortalama iyilesip zor kareler bozulmasin
    roll = np.array([o["roll"] for o in ornek])
    sira = np.concatenate([np.where(bolum == k)[0] for k in range(args.kat)])
    rl = roll[sira]
    for etiket, m in (("|roll| < 20", rl < 20), ("|roll| >= 20", rl >= 20)):
        if m.sum():
            print("    %-14s ham %.4f -> model %.4f  (n=%d)"
                  % (etiket, taban_iou[m].mean(), model_iou[m].mean(), m.sum()))

    if kazanc <= 0.002:
        print("-" * 66)
        print("  [KARAR] kazanc ihmal edilebilir -> MODEL YAZILMADI.")
        print("  Ham projeksiyon zaten yeterli; duzeltme eklemek gurultu katardi.")
        return 1

    # ---- TUM veriyle nihai model ----
    kats = {ad: ridge_cozum(Xs, Y[ad], args.lam) for ad in Y}
    cikti = args.cikti or os.path.join(args.klasor, "kalibrasyon.json")
    with open(cikti, "w", encoding="utf-8") as f:
        json.dump({
            "surum": 1,
            "ozellik_ad": OZELLIK_AD,
            "ort": ort.tolist(), "std": std.tolist(),
            "kats": {k: v.tolist() for k, v in kats.items()},
            "marj": [args.marj_x, args.marj_y], "dt": args.dt,
            "ornek": len(ornek), "gozden_gecirilen": args.gozden_gecirilen,
            "cv": {"kat": args.kat, "ham": float(taban_iou.mean()),
                   "sabit_ofset": float(ofset_iou.mean()),
                   "model": float(model_iou.mean())},
        }, f, indent=2)
    print("-" * 66)
    print("  MODEL YAZILDI -> %s" % cikti)
    print("  Uygula: veriseti/oto_etiket.py --kalibrasyon %s --koru-kadar %d"
          % (cikti, args.gozden_gecirilen))
    print("=" * 66)
    return 0


if __name__ == "__main__":
    sys.exit(main())

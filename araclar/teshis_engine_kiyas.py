# -*- coding: utf-8 -*-
"""
================================================================================
 TENSORRT ENGINE DOGRULAMA  (best.engine vs best.pt — ayni karelerde)
================================================================================
Engine'i devreye almadan once IKI SORUYU birlikte cevaplar:
  1) HIZ  : engine gercekten .pt'den hizli mi? (kare basina predict suresi)
  2) DOGRULUK: FP16 engine, FP32 .pt ile AYNI seyi mi goruyor? (tespit orani +
     conf + kutu merkezi kaymasi). Hiz kazanci dogrulugu bozuyorsa engine kullanilmaz.

AYNI kare kumesinde (canli dump klasoru) iki modeli SIRAYLA kosar; her kareyi
ayni girdiyle besler -> adil kiyas. Cikti: konsol tablosu + veri/teshis_engine_kiyas.csv

  python araclar/teshis_engine_kiyas.py                      # varsayilan: en yeni dump klasoru
  python araclar/teshis_engine_kiyas.py --kareler veri/teshis_kareler/OTURUM --n 100
"""
import argparse
import glob
import os
import time

import numpy as np

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GORSEL_UZANTI = (".png", ".jpg", ".jpeg", ".bmp")


def en_yeni_dump():
    ad = sorted(glob.glob(os.path.join(_KOK, "veri", "teshis_kareler", "*")),
                key=os.path.getmtime, reverse=True)
    for d in ad:
        if os.path.isdir(d) and glob.glob(os.path.join(d, "*.png")):
            return d
    return None


def kare_yukle(klasor, n):
    import cv2
    yollar = sorted(p for p in glob.glob(os.path.join(klasor, "*"))
                    if p.lower().endswith(GORSEL_UZANTI))
    if n:
        yollar = yollar[:n]
    kareler = []
    for p in yollar:
        im = cv2.imread(p, cv2.IMREAD_COLOR)
        if im is not None:
            kareler.append((os.path.basename(p), im))
    return kareler


def en_iyi_kutu(res):
    """(conf, cx, cy) en yuksek-conf kutu | (0, None, None)."""
    b = getattr(res, "boxes", None)
    if b is None or len(b) == 0:
        return 0.0, None, None
    i = int(b.conf.argmax())
    x1, y1, x2, y2 = [float(v) for v in b.xyxy[i]]
    return float(b.conf[i]), (x1 + x2) / 2.0, (y1 + y2) / 2.0


def olc(model, kareler, imgsz, device):
    """Her karede (conf, cx, cy, ms). Ilk 5 kare isinma sayilir (sureden dislanir)."""
    # isinma
    for _ in range(5):
        model.predict(kareler[0][1], imgsz=imgsz, conf=0.10, device=device, verbose=False)
    kayit = []
    for ad, im in kareler:
        t0 = time.perf_counter()
        res = model.predict(im, imgsz=imgsz, conf=0.10, device=device, verbose=False)[0]
        ms = (time.perf_counter() - t0) * 1000.0
        c, cx, cy = en_iyi_kutu(res)
        kayit.append((ad, c, cx, cy, ms))
    return kayit


def ozet(kayit):
    conf = np.array([k[1] for k in kayit])
    ms = np.array([k[4] for k in kayit])
    return {
        "n": len(kayit),
        "det_025": float((conf >= 0.25).mean() * 100),
        "det_045": float((conf >= 0.45).mean() * 100),
        "conf_ort": float(conf[conf >= 0.25].mean()) if (conf >= 0.25).any() else 0.0,
        "ms_ort": float(ms.mean()), "ms_p50": float(np.percentile(ms, 50)),
        "ms_p95": float(np.percentile(ms, 95)),
    }


def main():
    ap = argparse.ArgumentParser(description="best.engine vs best.pt (ayni karelerde)")
    ap.add_argument("--kareler", default=None, help="dump klasoru (yoksa en yenisi)")
    ap.add_argument("--engine", default=os.path.join(_KOK, "models", "best.engine"))
    ap.add_argument("--pt", default=os.path.join(_KOK, "models", "best.pt"))
    ap.add_argument("--imgsz", type=int, default=1280)
    ap.add_argument("--n", type=int, default=100)
    args = ap.parse_args()

    import torch
    from ultralytics import YOLO
    device = 0 if torch.cuda.is_available() else "cpu"
    assert torch.cuda.is_available(), "CUDA yok — anlamli kiyas icin GPU sart"
    print("[ENV] torch %s | cuda %s | gpu %s" % (
        torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0)))

    klasor = args.kareler or en_yeni_dump()
    if not klasor:
        raise SystemExit("[HATA] dump klasoru yok. Once: POST /api/teshis {\"dump_kare\":100}")
    kareler = kare_yukle(klasor, args.n)
    if not kareler:
        raise SystemExit("[HATA] klasorde kare yok: %s" % klasor)
    print("[KARE] %d kare <- %s\n" % (len(kareler), klasor))

    if not os.path.exists(args.engine):
        raise SystemExit("[HATA] engine yok: %s (once araclar\\teshis_trt_export.py)" % args.engine)

    print("... best.pt kosuyor")
    k_pt = olc(YOLO(args.pt), kareler, args.imgsz, device)
    print("... best.engine kosuyor")
    k_en = olc(YOLO(args.engine), kareler, args.imgsz, device)

    o_pt, o_en = ozet(k_pt), ozet(k_en)

    # kutu merkezi kaymasi: IKI modelin de tespit ettigi karelerde px mesafe
    ptmap = {k[0]: k for k in k_pt}
    kaymalar = []
    for ad, c, cx, cy, _ in k_en:
        if c >= 0.25 and ad in ptmap and ptmap[ad][1] >= 0.25 and cx is not None:
            _, _, px, py, _ = ptmap[ad]
            if px is not None:
                kaymalar.append(((cx - px) ** 2 + (cy - py) ** 2) ** 0.5)
    kayma_med = float(np.median(kaymalar)) if kaymalar else None

    print("\n%-14s %8s %8s %8s %10s %10s" % ("model", "det@.25", "det@.45", "conf", "ms p50", "ms p95"))
    for ad, o in (("best.pt (FP32)", o_pt), ("best.engine", o_en)):
        print("%-14s %7.1f%% %7.1f%% %8.3f %9.1f %9.1f" % (
            ad, o["det_025"], o["det_045"], o["conf_ort"], o["ms_p50"], o["ms_p95"]))

    print("\n=== YORUM ===")
    hiz = o_pt["ms_p50"] / o_en["ms_p50"] if o_en["ms_p50"] else 0
    print("  HIZ      : engine %.2fx (%.1f -> %.1f ms p50)" % (hiz, o_pt["ms_p50"], o_en["ms_p50"]))
    print("  DOGRULUK : det@.45 fark %+.1f puan | conf fark %+.3f | kutu kaymasi medyan %s px" % (
        o_en["det_045"] - o_pt["det_045"], o_en["conf_ort"] - o_pt["conf_ort"],
        ("%.1f" % kayma_med) if kayma_med is not None else "-"))
    dogru_ok = abs(o_en["det_045"] - o_pt["det_045"]) <= 5.0 and abs(o_en["conf_ort"] - o_pt["conf_ort"]) <= 0.05
    if dogru_ok and hiz >= 1.15:
        print("  KARAR    : ENGINE KULLAN — dogruluk esit (+-%5 band), belirgin hizli.")
    elif not dogru_ok:
        print("  KARAR    : DIKKAT — FP16 dogrulugu kaydirdi; engine kullanmadan once incele.")
    else:
        print("  KARAR    : hiz kazanci marjinal; contention altinda (sim acik) tekrar olc.")

    csv_yol = os.path.join(_KOK, "veri", "teshis_engine_kiyas.csv")
    with open(csv_yol, "w", encoding="utf-8") as f:
        f.write("kare,pt_conf,pt_ms,en_conf,en_ms\n")
        for (ad, cp, _, _, mp), (_, ce, _, _, me) in zip(k_pt, k_en):
            f.write("%s,%.3f,%.1f,%.3f,%.1f\n" % (ad, cp, mp, ce, me))
    print("\n  kare detayi: %s" % csv_yol)


if __name__ == "__main__":
    main()

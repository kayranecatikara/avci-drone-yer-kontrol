# -*- coding: utf-8 -*-
"""
================================================================================
 TESHIS A/B KARE TESTI  (MASTER Asama 3 — belirleyici test)
================================================================================
best.pt'yi IKI kare kaynaginda AYNI metriklerle olcer:
  A = canli hattan dump edilen kareler (POST /api/teshis {"dump_kare":100} ciktisi:
      veri/teshis_kareler/<ts>/  — modele giren array'in birebir aynisi)
  B = referans kareler (kayitli video dosyasi, PNG klasoru veya tek gorsel)

Metrikler: tespit orani (@0.25 UI esigi / @0.45 kilit esigi), ortalama/medyan
conf, inference suresi ort/p95. Yorum kilavuzu (master prompt):
  A ~= B  -> kareler + model temiz; sorun TAMAMEN ZAMANLAMADA (contention/backlog)
  A << B  -> sorun CAPTURE ICERIGINDE (renk/olcek/overlay/yanlis bolge)

Kullanim (repo kokunden):
  python araclar\\teshis_ab_test.py --a veri\\teshis_kareler\\20260708_120000 --b "C:\\kayitlar\\test.mp4"
  python araclar\\teshis_ab_test.py --a <klasor>                      # tek kaynak da olur
Secenekler: --n 100 (kaynak basina en cok kare), --adim 5 (videodan her 5. kare),
            --imgsz 1280, --half, --model models\\best.pt
"""
import argparse
import glob
import os
import sys
import time

import numpy as np

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # depo koku

VIDEO_UZANTI = (".mp4", ".avi", ".mkv", ".mov", ".webm")
GORSEL_UZANTI = (".png", ".jpg", ".jpeg", ".bmp")


def kareler(kaynak, n_max, adim):
    """Kaynaktan BGR kareler uret: klasor (PNG/JPG), video dosyasi veya tek gorsel.
    (ad, ndarray) ikilileri uretir; cv2 hem imread hem VideoCapture icin BGR doner
    -> canli hatla (grab_frame_bgr BGR) ayni renk duzeni, adil kiyas."""
    import cv2
    kaynak = os.path.abspath(kaynak)
    if os.path.isdir(kaynak):
        yollar = sorted(p for p in glob.glob(os.path.join(kaynak, "*"))
                        if p.lower().endswith(GORSEL_UZANTI))
        yollar = yollar[::max(1, adim)]
        if n_max:
            yollar = yollar[:n_max]
        for p in yollar:
            im = cv2.imread(p, cv2.IMREAD_COLOR)
            if im is not None:
                yield os.path.basename(p), im
    elif kaynak.lower().endswith(VIDEO_UZANTI):
        cap = cv2.VideoCapture(kaynak)
        if not cap.isOpened():
            raise SystemExit("[HATA] video acilamadi: %s" % kaynak)
        i = say = 0
        while True:
            ok, im = cap.read()
            if not ok:
                break
            if i % max(1, adim) == 0:
                yield "kare_%06d" % i, im
                say += 1
                if n_max and say >= n_max:
                    break
            i += 1
        cap.release()
    elif kaynak.lower().endswith(GORSEL_UZANTI):
        im = cv2.imread(kaynak, cv2.IMREAD_COLOR)
        if im is None:
            raise SystemExit("[HATA] gorsel okunamadi: %s" % kaynak)
        yield os.path.basename(kaynak), im
    else:
        raise SystemExit("[HATA] kaynak taninamadi (klasor/video/gorsel degil): %s" % kaynak)


def olc(model, kaynak, etiket, args):
    """Kaynagi kosturup metrik sozlugu don. Kare basina satirlari CSV'ye yazar."""
    csv_yol = os.path.join(_KOK, "veri", "teshis_ab_%s.csv" % etiket)
    os.makedirs(os.path.dirname(csv_yol), exist_ok=True)
    confs, sureler, cozunurluk = [], [], None
    n = 0
    with open(csv_yol, "w", encoding="utf-8") as f:
        f.write("ad,W,H,conf,infer_ms\n")
        pkw = dict(imgsz=args.imgsz, conf=0.10, device=args.device, verbose=False)
        if args.half:                       # 'half' yalniz istenince (deprecation uyarisi)
            pkw["half"] = True
        for ad, im in kareler(kaynak, args.n, args.adim):
            t0 = time.perf_counter()
            res = model.predict(im, **pkw)[0]
            dt = (time.perf_counter() - t0) * 1000.0
            boxes = getattr(res, "boxes", None)
            c = float(boxes.conf.max()) if boxes is not None and len(boxes) else 0.0
            confs.append(c)
            sureler.append(dt)
            cozunurluk = (im.shape[1], im.shape[0])
            f.write("%s,%d,%d,%.3f,%.1f\n" % (ad, im.shape[1], im.shape[0], c, dt))
            n += 1
            if n % 25 == 0:
                print("  [%s] %d kare islendi..." % (etiket, n))
    if not confs:
        raise SystemExit("[HATA] %s kaynaginda kare yok: %s" % (etiket, kaynak))
    confs = np.array(confs)
    sure = np.array(sureler[3:] if len(sureler) > 6 else sureler)   # ilk kareler isinma
    ust = confs[confs >= 0.25]
    return {
        "etiket": etiket, "kaynak": kaynak, "n": int(confs.size),
        "cozunurluk": "%dx%d" % cozunurluk,
        "det_025": float((confs >= 0.25).mean() * 100.0),
        "det_045": float((confs >= 0.45).mean() * 100.0),
        "conf_ort": float(ust.mean()) if ust.size else 0.0,
        "conf_med": float(np.median(ust)) if ust.size else 0.0,
        "ms_ort": float(sure.mean()), "ms_p95": float(np.percentile(sure, 95)),
        "csv": csv_yol,
    }


def yazdir(m):
    print("  kaynak      : %s  (%d kare, %s)" % (m["kaynak"], m["n"], m["cozunurluk"]))
    print("  tespit orani: %%%.1f @0.25 (UI)   |   %%%.1f @0.45 (kilit esigi)"
          % (m["det_025"], m["det_045"]))
    print("  conf (>=.25): ort %.3f / medyan %.3f" % (m["conf_ort"], m["conf_med"]))
    print("  inference   : ort %.1f ms / p95 %.1f ms  (offline, sim yuku haric)"
          % (m["ms_ort"], m["ms_p95"]))
    print("  kare detayi : %s" % m["csv"])


def main():
    ap = argparse.ArgumentParser(description="best.pt A/B kare testi (canli dump vs referans)")
    ap.add_argument("--a", required=True, help="A kaynagi (canli dump klasoru)")
    ap.add_argument("--b", default=None, help="B kaynagi (video/klasor; kiyas icin)")
    ap.add_argument("--model", default=os.path.join(_KOK, "models", "best.pt"))
    ap.add_argument("--imgsz", type=int, default=1280)
    ap.add_argument("--n", type=int, default=100, help="kaynak basina en cok kare (0=hepsi)")
    ap.add_argument("--adim", type=int, default=1, help="her N. kareyi al (video icin onerilir)")
    ap.add_argument("--half", action="store_true", help="FP16 inference (kiyas denemesi)")
    ap.add_argument("--device", default=None)
    args = ap.parse_args()

    from ultralytics import YOLO
    import torch
    if args.device is None:
        args.device = "cuda" if torch.cuda.is_available() else "cpu"
    print("[ENV] torch %s | cuda %s | device=%s" % (
        torch.__version__, torch.cuda.is_available(), args.device))
    model = YOLO(args.model)
    wkw = dict(imgsz=args.imgsz, device=args.device, verbose=False)
    if args.half:
        wkw["half"] = True
    model.predict(np.zeros((args.imgsz, args.imgsz, 3), np.uint8), **wkw)  # isinma

    print("\n=== A: CANLI DUMP ===")
    ma = olc(model, args.a, "canli", args)
    yazdir(ma)
    if not args.b:
        return
    print("\n=== B: REFERANS (video/klasor) ===")
    mb = olc(model, args.b, "referans", args)
    yazdir(mb)

    print("\n=== KIYAS (A canli - B referans) ===")
    d25 = ma["det_025"] - mb["det_025"]
    d45 = ma["det_045"] - mb["det_045"]
    dc = ma["conf_ort"] - mb["conf_ort"]
    print("  tespit farki : %+.1f puan @0.25 | %+.1f puan @0.45" % (d25, d45))
    print("  conf farki   : %+.3f" % dc)
    if abs(d45) <= 5.0 and abs(dc) <= 0.05:
        print("  YORUM: A ~= B -> kareler ve model TEMIZ; sorun ZAMANLAMADA")
        print("         (GPU contention / kare yasi). Asama 5-6'ya agirlik ver.")
    elif d45 < -5.0:
        print("  YORUM: canli kareler belirgin KOTU -> sorun CAPTURE ICERIGINDE")
        print("         (renk/olcek/overlay/bolge). Asama 4: dump PNG'lerini GOZLE incele.")
    else:
        print("  YORUM: canli kareler referanstan IYI/esit -> capture temiz;")
        print("         zamanlama olcumlerine (teshis_zaman CSV) bak.")


if __name__ == "__main__":
    sys.exit(main())

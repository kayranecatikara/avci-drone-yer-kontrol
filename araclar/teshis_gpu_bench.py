# -*- coding: utf-8 -*-
"""
================================================================================
 TESHIS GPU BENCH  (MASTER Asama 6 — contention kaniti)
================================================================================
AYNI kare uzerinde N iterasyon best.pt inference'i kronometreler. IKI kez
calistirilir: bir kez SIM KAPALI, bir kez SIM ACIK (oyun PLAY modunda) iken.
Iki kosu arasindaki fark = oyunla GPU paylasiminin (contention) kaniti.

  python araclar\\teshis_gpu_bench.py --etiket sim_kapali
  python araclar\\teshis_gpu_bench.py --etiket sim_acik
  python araclar\\teshis_gpu_bench.py --etiket sim_acik_poz --poz     # canli yuku birebir:
                                                                      # her 3. iterasyonda poz modeli de kosar
  python araclar\\teshis_gpu_bench.py --etiket sim_acik_half --half   # FP16 denemesi

Kare: --kare <png> verilmezse en yeni veri/teshis_kareler/*/kare_*.png aranir;
o da yoksa sentetik 1920x1080 gurultu (deterministik) kullanilir.
--dmon: olcum boyunca `nvidia-smi dmon -s u` ciktisini veri/ altina loglar.
Sonuc satiri veri/teshis_bench.csv'ye EKLENIR (before/after tablosu buradan).
"""
import argparse
import glob
import os
import subprocess
import sys
import time

import numpy as np

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # depo koku
VERI = os.path.join(_KOK, "veri")


def varsayilan_kare():
    """En yeni dump karesini bul; yoksa None (sentetik kullanilir)."""
    adaylar = sorted(glob.glob(os.path.join(VERI, "teshis_kareler", "*", "kare_*.png")),
                     key=os.path.getmtime, reverse=True)
    return adaylar[0] if adaylar else None


def main():
    ap = argparse.ArgumentParser(description="best.pt sabit-kare inference benchmark'i")
    ap.add_argument("--etiket", required=True,
                    help="kosu adi: sim_kapali | sim_acik | sim_acik_poz | ... (CSV'ye yazilir)")
    ap.add_argument("--kare", default=None, help="test karesi PNG (yoksa en yeni dump / sentetik)")
    ap.add_argument("--model", default=os.path.join(_KOK, "models", "best.pt"))
    ap.add_argument("--imgsz", type=int, default=1280)
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--half", action="store_true", help="FP16 inference")
    ap.add_argument("--poz", action="store_true",
                    help="canli yuku taklit et: her --poz-her-n iterasyonda talon_pose.pt de kos")
    ap.add_argument("--poz-her-n", type=int, default=3)
    ap.add_argument("--poz-model", default=os.path.join(_KOK, "models", "talon_pose.pt"))
    ap.add_argument("--dmon", action="store_true", help="nvidia-smi dmon -s u logu al")
    ap.add_argument("--device", default=None)
    args = ap.parse_args()

    import torch
    from ultralytics import YOLO
    if args.device is None:
        args.device = "cuda" if torch.cuda.is_available() else "cpu"
    print("[ENV] python %s" % sys.version.split()[0])
    print("[ENV] torch %s | cuda %s | available %s" % (
        torch.__version__, torch.version.cuda, torch.cuda.is_available()))
    if torch.cuda.is_available():
        print("[ENV] gpu %s" % torch.cuda.get_device_name(0))

    # Test karesi
    kare_yol = args.kare or varsayilan_kare()
    if kare_yol:
        import cv2
        im = cv2.imread(kare_yol, cv2.IMREAD_COLOR)
        if im is None:
            raise SystemExit("[HATA] kare okunamadi: %s" % kare_yol)
        print("[KARE] %s (%dx%d)" % (kare_yol, im.shape[1], im.shape[0]))
    else:
        rng = np.random.default_rng(42)
        im = rng.integers(0, 255, (1080, 1920, 3), dtype=np.uint8)
        print("[KARE] sentetik 1920x1080 gurultu (dump karesi bulunamadi)")

    model = YOLO(args.model)
    poz_model = None
    if args.poz:
        if os.path.exists(args.poz_model):
            poz_model = YOLO(args.poz_model)
        else:
            print("[UYARI] poz modeli yok (%s) -> poz yuku ATLANDI. Not: canli sistem de"
                  " ayni dosyayi bulamayinca poz kestirimini sessizce kapatir." % args.poz_model)
            args.poz = False

    # predict kwargs: 'half' yalniz istenince gecilir (8.4.x'te deprecation uyarisi basiyor)
    pkw = dict(imgsz=args.imgsz, conf=0.25, device=args.device, verbose=False)
    pkw_poz = dict(imgsz=args.imgsz, conf=0.35, device=args.device, verbose=False)
    if args.half:
        pkw["half"] = True
        pkw_poz["half"] = True

    # Isinma (ilk predict CUDA cekirdek/algoritma hazirligi yuzunden yavas)
    for _ in range(10):
        model.predict(im, **pkw)
    if poz_model is not None:
        for _ in range(3):
            poz_model.predict(im, **pkw_poz)

    # dmon logu (opsiyonel)
    dmon_p, dmon_yol = None, None
    if args.dmon:
        os.makedirs(VERI, exist_ok=True)
        dmon_yol = os.path.join(VERI, "teshis_dmon_%s.log" % args.etiket)
        try:
            dmon_f = open(dmon_yol, "w")
            dmon_p = subprocess.Popen(["nvidia-smi", "dmon", "-s", "u", "-d", "1"],
                                      stdout=dmon_f, stderr=subprocess.STDOUT)
            print("[DMON] GPU kullanim logu -> %s" % dmon_yol)
        except Exception as e:
            print("[DMON] baslatilamadi (%r) -> logsuz devam" % e)

    # Olcum
    sureler, poz_sureler = [], []
    t_bas = time.perf_counter()
    for i in range(args.n):
        t0 = time.perf_counter()
        model.predict(im, **pkw)
        sureler.append((time.perf_counter() - t0) * 1000.0)
        if poz_model is not None and (i + 1) % max(1, args.poz_her_n) == 0:
            t0 = time.perf_counter()
            poz_model.predict(im, **pkw_poz)
            poz_sureler.append((time.perf_counter() - t0) * 1000.0)
    toplam_s = time.perf_counter() - t_bas

    if dmon_p is not None:
        dmon_p.terminate()

    a = np.array(sureler)
    efektif_fps = args.n / toplam_s     # poz dahil gercek dongu hizi
    print("\n=== SONUC [%s]  (n=%d, imgsz=%d, half=%s, poz=%s) ===" % (
        args.etiket, args.n, args.imgsz, args.half,
        ("her %d. iter" % args.poz_her_n) if args.poz else "yok"))
    print("  best.pt : ort %.1f | p50 %.1f | p95 %.1f | max %.1f ms" % (
        a.mean(), np.percentile(a, 50), np.percentile(a, 95), a.max()))
    if poz_sureler:
        p = np.array(poz_sureler)
        print("  poz     : ort %.1f | p95 %.1f ms  (n=%d)" % (
            p.mean(), np.percentile(p, 95), p.size))
    print("  dongu   : %.1f FPS efektif (%.1f sn toplam)" % (efektif_fps, toplam_s))
    if dmon_yol:
        print("  dmon    : %s" % dmon_yol)

    # before/after tablosu icin CSV'ye ekle
    os.makedirs(VERI, exist_ok=True)
    bcsv = os.path.join(VERI, "teshis_bench.csv")
    yeni = not os.path.exists(bcsv)
    with open(bcsv, "a", encoding="utf-8") as f:
        if yeni:
            f.write("t,etiket,model,imgsz,half,poz,n,ort_ms,p50_ms,p95_ms,max_ms,efektif_fps\n")
        f.write("%s,%s,%s,%d,%d,%d,%d,%.1f,%.1f,%.1f,%.1f,%.1f\n" % (
            time.strftime("%Y-%m-%d %H:%M:%S"), args.etiket,
            os.path.basename(args.model), args.imgsz, int(args.half), int(args.poz),
            args.n, a.mean(), np.percentile(a, 50), np.percentile(a, 95),
            a.max(), efektif_fps))
    print("  kayit   : %s (etiket=%s)" % (bcsv, args.etiket))


if __name__ == "__main__":
    main()

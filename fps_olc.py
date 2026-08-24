# -*- coding: utf-8 -*-
"""
================================================================================
  FPS OLC  --  gercek boru hattini oyun acikken asama asama olcer
================================================================================
Sorun "model yavas" mi, "yakalama yavas" mi, "oyun GPU'yu yiyor" mu?
Tahmin etmek yerine her asamayi ayri olcuyoruz:

    yakalama (ekran)  ->  ?? ms   (hangi yontem: WGC / PrintWindow / mss)
    tespit (YOLO)     ->  ?? ms   (hangi motor: engine / pt)
    -------------------------------
    toplam            ->  ?? ms   ->  ?? FPS

Ayrica tespit edilen kareleri kutulu halde kaydeder -> fps_olc_kareler/
Boylece hem HIZI hem DOGRULUGU ayni anda gorursun.

KULLANIM
    python fps_olc.py            200 kare olc
    python fps_olc.py 500        500 kare olc

Oyun ACIK ve PLAY modunda olmali (drone ucuyor olmali ki tespit gorelim).
Hicbir sey degistirmez, sadece olcer.
================================================================================
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import config as Cfg

KARE = int(sys.argv[1]) if len(sys.argv) > 1 else 200
CIKTI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fps_olc_kareler")
IPUCU = ["dronesofwar", "drones of war", "drone of war"]


def yuzde(liste, p):
    if not liste:
        return 0.0
    s = sorted(liste)
    return s[min(len(s) - 1, int(len(s) * p / 100.0))]


def main():
    os.makedirs(CIKTI, exist_ok=True)
    for f in os.listdir(CIKTI):
        try:
            os.remove(os.path.join(CIKTI, f))
        except Exception:
            pass

    print("=" * 70)
    print("BORU HATTI OLCUMU")
    print("=" * 70)

    # ---------------------------------------------------------- 1) YAKALAMA
    from detection.pencere_yakala import PencereYakala, pencere_bul
    baslik, hwnd = pencere_bul(IPUCU)
    print(f"  oyun penceresi : {baslik!r}  (hwnd={hwnd})")
    if baslik is None:
        print("  !! Oyun penceresi bulunamadi. Oyun acik mi?")
        return

    yak = PencereYakala(title_hints=IPUCU)
    ok = yak.baslat()
    yontem = "windows-capture (WGC)" if ok else "mss / PrintWindow (yedek)"
    print(f"  yakalama yontemi: {yontem}")
    time.sleep(1.5)                       # ilk kareler gelsin

    kare = yak.get_latest_bgr() if ok else None
    if kare is None:
        print("  WGC kare vermedi -> mss'e dusuluyor")
        import mss
        sct = mss.mss()
        import pygetwindow as gw
        b = None
        for w in gw.getAllWindows():
            if getattr(w, "_hWnd", None) == hwnd:
                b = {"left": w.left, "top": w.top, "width": w.width, "height": w.height}
        if b is None:
            print("  !! pencere bolgesi alinamadi")
            return

        def al():
            g = sct.grab(b)
            return np.asarray(g)[:, :, :3].copy()
        yontem = "mss"
    else:
        def al():
            return yak.get_latest_bgr()

    k = al()
    print(f"  kare boyutu    : {k.shape[1]}x{k.shape[0]}")

    # ------------------------------------------------------------ 2) MODEL
    from detection.gorsel_tespit import HedefDedektor
    yol = os.path.join("models", Cfg.VIS_MODEL_ADI + ".pt")
    ded = HedefDedektor(yol, conf=getattr(Cfg, "VIS_CONF_MIN", 0.35),
                        imgsz=960, half=True, sahi=False)
    print(f"  model          : {Cfg.VIS_MODEL_ADI}  motor={ded.motor}  "
          f"cihaz={ded.device}  half={ded.half}  SAHI=KAPALI")
    for _ in range(5):
        ded.tespit_hepsi(k)               # isinma

    # ------------------------------------------------------------ 3) OLCUM
    print(f"\n  {KARE} kare olculuyor...\n")
    t_yak, t_ted, t_top = [], [], []
    tespitli = 0
    kaydedilen = 0
    import cv2

    for i in range(KARE):
        a = time.perf_counter()
        frame = al()
        b = time.perf_counter()
        if frame is None:
            continue
        dets = ded.tespit_hepsi(frame)
        c = time.perf_counter()

        t_yak.append((b - a) * 1000)
        t_ted.append((c - b) * 1000)
        t_top.append((c - a) * 1000)
        if dets:
            tespitli += 1
            if kaydedilen < 12 and i % 7 == 0:
                g = frame.copy()
                for d in dets:
                    # tespit_hepsi semasi: {cx,cy,w,h,conf,...} (merkez + en/boy)
                    x1 = int(d["cx"] - d["w"] / 2.0); y1 = int(d["cy"] - d["h"] / 2.0)
                    x2 = int(d["cx"] + d["w"] / 2.0); y2 = int(d["cy"] + d["h"] / 2.0)
                    cv2.rectangle(g, (x1, y1), (x2, y2), (0, 255, 0), 3)
                    cv2.putText(g, "%.2f" % d["conf"], (x1, max(20, y1 - 8)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                cv2.imwrite(os.path.join(CIKTI, "kare_%03d.jpg" % i), g,
                            [cv2.IMWRITE_JPEG_QUALITY, 85])
                kaydedilen += 1

    if not t_top:
        print("  !! hic kare alinamadi")
        return

    # ------------------------------------------------------------ 4) RAPOR
    n = len(t_top)
    print("=" * 70)
    print(f"SONUC  ({n} kare)")
    print("=" * 70)
    print(f"  {'asama':<22}{'ortalama':>11}{'p50':>9}{'p95':>9}")
    for ad, v in (("yakalama (ekran)", t_yak), ("tespit (YOLO)", t_ted),
                  ("TOPLAM", t_top)):
        print(f"  {ad:<22}{sum(v)/len(v):>9.1f}ms{yuzde(v,50):>7.1f}ms{yuzde(v,95):>7.1f}ms")
    ort = sum(t_top) / n
    print()
    print(f"  FPS (ortalama)  : {1000.0/ort:.1f}")
    print(f"  FPS (p95 en kotu): {1000.0/max(1e-6, yuzde(t_top,95)):.1f}")
    print()
    print(f"  yakalama yontemi: {yontem}")
    print(f"  tespit motoru   : {ded.motor}")
    print(f"  DRONE BULUNAN KARE: {tespitli}/{n}  (%{100.0*tespitli/n:.1f})")
    print(f"  ornek kareler   : {CIKTI}  ({kaydedilen} adet)")

    # darbogaz kim?
    oy, ot = sum(t_yak)/n, sum(t_ted)/n
    print()
    if oy > ot:
        print(f"  >> DARBOGAZ: YAKALAMA  ({oy:.1f} ms vs model {ot:.1f} ms)")
    else:
        print(f"  >> DARBOGAZ: MODEL  ({ot:.1f} ms vs yakalama {oy:.1f} ms)")
    print("=" * 70)

    try:
        yak.durdur()
    except Exception:
        pass


if __name__ == "__main__":
    main()

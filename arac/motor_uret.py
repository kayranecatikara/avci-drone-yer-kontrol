# -*- coding: utf-8 -*-
"""
================================================================================
  MOTOR URET  --  TensorRT .engine dosyalarini BU MAKINEDE uret
================================================================================
⚠⚠ NEDEN BU BETIK VAR — 14 FPS SORUNUNUN CEVABI

TensorRT motoru GPU modeline, surucu ve TensorRT surumune GORE derlenir.
`.engine` dosyalari BIR MAKINEDEN DIGERINE KOPYALANAMAZ. Kopyalanirsa (ya da
hic yoksa) dedektor sessizce `.pt`'ye duser.

DEPODA OLCULEN FARK (RTX 4060, oyun+sunucu kosarken, ayni 40 kare):

    motor      tam-kare    SAHI batch8    kare/sn    IoU ort    IoU>0.9
    .pt         113.5 ms      205.1 ms       3.1      1.0000       —
    .onnx       752.4 ms      877.0 ms       0.6      0.9840      ...
    .engine      13.1 ms       33.9 ms      21.3      0.9861     %100

**7 KAT.** Tespit sayisi birebir ayni (20/20), kutu kaymasi yok.
Yani ".pt ile calisiyor" demek "FPS'in yedide biri" demektir.

BU YUZDEN: yeni bir makinede sistemi ilk kez kurarken ONCE BU BETIGI CALISTIR.

KULLANIM
--------------------------------------------------------------------------------
    python arac/motor_uret.py              # eksik olanlari uret + olc
    python arac/motor_uret.py --olc        # URETME, yalniz mevcut durumu olc
    python arac/motor_uret.py --zorla      # var olanlari da yeniden uret
    python arac/motor_uret.py --model talon_v3.pt

CIKTI: models/<ad>.engine  (yaninda .pt durur; .pt SILINMEZ)

⚠ Uretim GPU'yu doldurur ve model basina 1-5 dakika surebilir. Oyun ve sunucu
  KAPALIYKEN calistir, yoksa hem yavaslar hem olcum kirlenir.
⚠ FP16 kullanilir (half=True): olculdu, dogruluk kaybi ihmal edilebilir
  (IoU>0.9 orani %100), hiz ~2 kat.
================================================================================
"""
import argparse
import os
import sys
import time

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(KOK, "models")

# (dosya adi, imgsz, gorev)  --  imgsz EGITIM olcegine esit olmali
#   talon_v3   : yolo11s @960 (detect)          -> ucus dedektoru
#   talon_pose_v2 : @960 (pose, tam kare)       -> gozlemci poz
# ⚠ Krop poz modeli (256x96) burada DEGIL: o dosya talon_dataset altinda ve
#   imgsz'i (96,256) dikdortgen -- ayri uretilir (asagida NOT).
MOTORLAR = [
    ("talon_v3.pt", 960, "detect"),          # ← UCUSTA KULLANILAN, en kritik
    ("talon_v2.pt", 960, "detect"),          # yedek/karsilastirma
    ("best.pt", 640, "detect"),              # eski model (640 egitimli)
    ("talon_pose_v2.pt", 960, "pose"),       # poz (varsayilan KAPALI ama hazir dursun)
]


def _yaz(s=""):
    print(s, flush=True)


def gpu_bilgi():
    try:
        import torch
        if not torch.cuda.is_available():
            return None, "CUDA YOK -> TensorRT uretilemez, sistem .pt ile kosar"
        return torch.cuda.get_device_name(0), None
    except Exception as e:
        return None, "torch yuklenemedi: %r" % (e,)


def olc(yol, imgsz, tekrar=25):
    """Bir modeli yukleyip ortanca cikarim suresini olc (ms)."""
    try:
        from ultralytics import YOLO
        import numpy as np
    except Exception as e:
        return None, "ultralytics/numpy yok: %r" % (e,)
    try:
        gorev = "pose" if "pose" in os.path.basename(yol).lower() else "detect"
        m = YOLO(yol, task=gorev) if yol.endswith(".engine") else YOLO(yol)
        bos = np.zeros((imgsz, imgsz, 3), dtype="uint8")
        for _ in range(8):                                   # isinma
            m.predict(bos, imgsz=imgsz, device=0, verbose=False)
        v = []
        for _ in range(tekrar):
            t = time.perf_counter()
            m.predict(bos, imgsz=imgsz, device=0, verbose=False)
            v.append((time.perf_counter() - t) * 1000.0)
        v.sort()
        return v[len(v) // 2], None
    except Exception as e:
        return None, "%r" % (e,)


def uret(pt_yol, imgsz, gorev):
    from ultralytics import YOLO
    m = YOLO(pt_yol)
    return m.export(format="engine", imgsz=imgsz, half=True, device=0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--olc", action="store_true", help="uretme, yalniz olc")
    ap.add_argument("--zorla", action="store_true", help="var olani da yeniden uret")
    ap.add_argument("--model", default=None, help="yalniz bu dosya (orn. talon_v3.pt)")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ad, hata = gpu_bilgi()
    _yaz("=" * 72)
    _yaz("  MOTOR URET  --  TensorRT .engine")
    _yaz("=" * 72)
    if hata:
        _yaz("  ⛔ %s" % hata)
        _yaz("  Sistem yine calisir ama dedektor ~7 KAT yavas olur (bkz. basliktaki tablo).")
        return 1
    _yaz("  GPU: %s" % ad)
    _yaz("  models/: %s" % MODEL_DIR)
    _yaz()

    isler = MOTORLAR
    if a.model:
        isler = [x for x in MOTORLAR if x[0] == a.model]
        if not isler:
            isler = [(a.model, 960, "detect")]

    sonuc = []
    for dosya, imgsz, gorev in isler:
        pt = os.path.join(MODEL_DIR, dosya)
        eng = pt[:-3] + ".engine"
        if not os.path.exists(pt):
            _yaz("  ATLANDI  %-22s (.pt yok)" % dosya)
            continue

        var = os.path.exists(eng)
        if a.olc:
            durum = "mevcut" if var else "YOK"
        elif var and not a.zorla:
            durum = "zaten var (yeniden uretmek icin --zorla)"
        else:
            _yaz("  URETILIYOR  %-22s imgsz=%d  (1-5 dk surebilir...)" % (dosya, imgsz))
            t0 = time.time()
            try:
                yeni = uret(pt, imgsz, gorev)
                durum = "URETILDI (%.0f s)" % (time.time() - t0)
                _yaz("     -> %s" % yeni)
            except Exception as e:
                durum = "BASARISIZ: %r" % (e,)
                _yaz("     ⛔ %s" % durum)

        ms_pt, e1 = olc(pt, imgsz)
        ms_en, e2 = (olc(eng, imgsz) if os.path.exists(eng) else (None, "engine yok"))
        sonuc.append((dosya, imgsz, durum, ms_pt, ms_en))
        _yaz("  %-22s %s" % (dosya, durum))

    _yaz()
    _yaz("=" * 72)
    _yaz("  OLCUM (ortanca cikarim, bos kare, GPU bosken)")
    _yaz("=" * 72)
    _yaz("  %-22s %8s %10s %10s %8s" % ("model", "imgsz", ".pt ms", ".engine ms", "kazanc"))
    for dosya, imgsz, _d, ms_pt, ms_en in sonuc:
        kaz = ("%.1fx" % (ms_pt / ms_en)) if (ms_pt and ms_en and ms_en > 0) else "-"
        _yaz("  %-22s %8d %10s %10s %8s"
             % (dosya, imgsz,
                ("%.1f" % ms_pt) if ms_pt else "-",
                ("%.1f" % ms_en) if ms_en else "YOK",
                kaz))
    _yaz()
    kritik = [s for s in sonuc if s[0] == "talon_v3.pt"]
    if kritik and kritik[0][4]:
        _yaz("  ✓ UCUS DEDEKTORU (talon_v3) engine HAZIR -> tam hizda kosacak.")
    else:
        _yaz("  ⛔ UCUS DEDEKTORU (talon_v3) engine YOK -> sistem ~7 KAT yavas kosar.")
    _yaz()
    _yaz("  NOT: krop poz modeli (256x96) bu listede degil. Onu uretmek icin:")
    _yaz("     python -c \"from ultralytics import YOLO; \"")
    _yaz("       \"YOLO('<yol>/talon_pose_krop_v2/weights/best.pt')\"")
    _yaz("       \".export(format='engine', imgsz=(96,256), half=True, device=0)\"")
    _yaz("  ⚠ imgsz DIKDORTGEN verilmeli; kare verilirse model cop uretir.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

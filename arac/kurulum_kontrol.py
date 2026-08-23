# -*- coding: utf-8 -*-
r"""
================================================================================
  KURULUM KONTROL  --  "bende neden yavas / neden calismiyor" sorusunun ilk adimi
================================================================================
Hicbir sey calistirmadan, sadece BAKARAK sistemin hazir olup olmadigini soyler.
Her satir ya ✔ ya ⛔ ile biter; ⛔ olan satirin yaninda NE YAPILACAGI yazar.

KULLANIM
    python arac/kurulum_kontrol.py

Cikti sonunda tek cumlelik HUKUM verir.
================================================================================
"""
import importlib
import os
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if KOK not in sys.path:
    sys.path.insert(0, KOK)

sorun = []


def satir(ad, deger, ok, cozum=""):
    isaret = "✔" if ok else "⛔"
    print("  %-26s %-34s %s" % (ad, str(deger)[:34], isaret))
    if not ok and cozum:
        print("      -> %s" % cozum)
        sorun.append((ad, cozum))


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("=" * 78)
    print("  KURULUM KONTROL")
    print("=" * 78)

    # ---- python / paketler ----
    print()
    print("  --- PAKETLER ---")
    satir("python", sys.version.split()[0], sys.version_info >= (3, 9),
          "Python 3.9+ gerekli")
    for ad, ipucu in (("torch", "pip install torch --index-url https://download.pytorch.org/whl/cu121"),
                      ("ultralytics", "pip install ultralytics"),
                      ("numpy", "pip install numpy"),
                      ("PIL", "pip install pillow"),
                      ("mss", "pip install mss")):
        try:
            m = importlib.import_module(ad)
            satir(ad, getattr(m, "__version__", "kurulu"), True)
        except Exception:
            satir(ad, "YOK", False, ipucu)
    try:
        import tensorrt
        satir("tensorrt", tensorrt.__version__, True)
    except Exception:
        satir("tensorrt", "YOK", False,
              "pip install tensorrt   (FPS'in 7 katini bu saglar)")

    # ---- GPU ----
    print()
    print("  --- GPU ---")
    try:
        import torch
        var = torch.cuda.is_available()
        satir("CUDA kullanilabilir", var, var,
              "NVIDIA surucusu + CUDA'li torch kur; GPU yoksa sistem 7 kat yavas kosar")
        if var:
            satir("GPU", torch.cuda.get_device_name(0), True)
            satir("CUDA (torch)", torch.version.cuda, True)
            tb = torch.cuda.get_device_properties(0).total_memory / 1e9
            satir("VRAM", "%.1f GB" % tb, tb >= 4.0,
                  "4 GB alti VRAM'de imgsz dusurmek gerekebilir")
    except Exception as e:
        satir("torch/CUDA", repr(e)[:30], False, "torch kurulumunu duzelt")

    # ---- model ----
    print()
    print("  --- MODEL ---")
    try:
        from guidance.ana_kontrol import Cfg
        pt = Cfg.VIS_MODEL_PATH
        satir("aktif model", os.path.basename(pt), os.path.exists(pt),
              "models/ altinda yok -- branch'i tam cektin mi?")
        if os.path.exists(pt):
            satir("  boyut", "%.1f MB" % (os.path.getsize(pt)/1048576), True)
        eng = pt[:-3] + ".engine"
        v = os.path.exists(eng)
        satir("TensorRT motoru", os.path.basename(eng) if v else "YOK", v,
              "python arac/motor_kur.py     <-- FPS SORUNUNUN COZUMU BU")
        if v:
            satir("  boyut", "%.1f MB" % (os.path.getsize(eng)/1048576), True)
        satir("conf esigi", Cfg.VIS_CONF_MIN, True)
        try:
            from web.server import MODEL_IMGSZ
            satir("imgsz", MODEL_IMGSZ, True)
        except Exception:
            pass
    except Exception as e:
        satir("ana_kontrol.Cfg", repr(e)[:30], False, "depo kokunden calistir")

    # ---- oyun ----
    print()
    print("  --- OYUN ---")
    try:
        import ctypes
        u = ctypes.windll.user32
        bulundu = []
        CB = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

        def cb(h, l):
            if u.IsWindowVisible(h):
                c = ctypes.create_unicode_buffer(256)
                u.GetClassNameW(h, c, 256)
                if c.value == "UnrealWindow":
                    bulundu.append(h)
            return True
        u.EnumWindows(CB(cb), 0)
        satir("oyun penceresi", "acik" if bulundu else "kapali", bool(bulundu),
              "Oyunu ac ve GOREVE gir; ekran yakalama pencereden okuyor")
    except Exception:
        satir("oyun penceresi", "kontrol edilemedi", True)

    # ---- hukum ----
    print()
    print("=" * 78)
    if not sorun:
        print("  ✔ HER SEY HAZIR.  python main.py  ile baslat, http://127.0.0.1:8000")
    else:
        print("  %d EKSIK VAR -- sirayla:" % len(sorun))
        for i, (ad, c) in enumerate(sorun, 1):
            print("    %d) %-24s %s" % (i, ad, c))
    print("=" * 78)
    return 0 if not sorun else 1


if __name__ == "__main__":
    raise SystemExit(main())

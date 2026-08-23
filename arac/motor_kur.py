# -*- coding: utf-8 -*-
r"""
================================================================================
  MOTOR KUR  --  TensorRT .engine uret  (FPS'in %90'i bu adimda kazaniliyor)
================================================================================
NEDEN GEREKLI
--------------------------------------------------------------------------------
Ayni model dosyasi (.pt) iki makinede AYNI hizda kosmaz. Olculdu (RTX 4060,
oyun + sunucu birlikte kosarken, ayni 40 kare):

    motor      tam-kare      kare/sn    tespit
    .pt         113.5 ms        3.1     20/20
    .onnx       752.4 ms        0.6     CPU'ya dusuyor -> ELENDI
    .engine      13.1 ms       21.3     20/20   <-- 7 KAT hizli

Yani ".pt ile 14 FPS aliyorum" sikayetinin sebebi neredeyse her zaman
.engine dosyasinin O MAKINEDE olmamasidir.

⚠ .engine TASINMAZ. GPU modeline, surucu surumune ve TensorRT surumune
  BAGLIDIR. Baska bilgisayardan kopyalanan .engine ya yuklenmez ya da
  sessizce yanlis calisir. Bu yuzden repoya KONMAZ, her makinede URETILIR.

NE YAPAR
--------------------------------------------------------------------------------
models/ altindaki .pt modelleri icin ayni klasore .engine uretir.
Model hangi imgsz ile egitildiyse onu kullanir (yanlis imgsz = yanlis sonuc).

KULLANIM
--------------------------------------------------------------------------------
    python arac/motor_kur.py                 # aktif modeli (Cfg.VIS_MODEL_PATH) kur
    python arac/motor_kur.py --hepsi         # models/ altindaki TUM .pt'ler
    python arac/motor_kur.py --model models/talon_v4.pt
    python arac/motor_kur.py --imgsz 960     # imgsz'i elle ver
    python arac/motor_kur.py --zorla         # .engine varsa bile yeniden uret

SURE: model basina ~2-3 dakika (RTX 4060). Bir kez yapilir.
================================================================================
"""
import argparse
import os
import sys
import time

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if KOK not in sys.path:
    sys.path.insert(0, KOK)


def egitim_imgsz(pt_yol, varsayilan=640):
    """Modelin egitildigi imgsz'i agirliktan oku. Bulamazsa varsayilani dondur."""
    try:
        import torch
        ck = torch.load(pt_yol, map_location="cpu", weights_only=False)
        for anahtar in ("train_args", "args"):
            a = ck.get(anahtar) if isinstance(ck, dict) else None
            if isinstance(a, dict) and a.get("imgsz"):
                v = a["imgsz"]
                return int(v[0] if isinstance(v, (list, tuple)) else v)
    except Exception:
        pass
    return varsayilan


def ortam_kontrol():
    print("  --- ORTAM ---")
    ok = True
    try:
        import torch
        print("    torch          : %s" % torch.__version__)
        if torch.cuda.is_available():
            print("    GPU            : %s" % torch.cuda.get_device_name(0))
            print("    CUDA (torch)   : %s" % torch.version.cuda)
        else:
            print("    GPU            : ⛔ CUDA YOK -- TensorRT motoru URETILEMEZ")
            ok = False
    except Exception as e:
        print("    torch          : ⛔ yok (%r)" % (e,)); ok = False
    try:
        import tensorrt
        print("    tensorrt       : %s" % tensorrt.__version__)
    except Exception:
        print("    tensorrt       : ⛔ YOK ->  pip install tensorrt")
        ok = False
    try:
        import ultralytics
        print("    ultralytics    : %s" % ultralytics.__version__)
    except Exception as e:
        print("    ultralytics    : ⛔ yok (%r)" % (e,)); ok = False
    return ok


def kur(pt_yol, imgsz=None, zorla=False, half=True):
    if not os.path.exists(pt_yol):
        print("  ⛔ model yok: %s" % pt_yol); return False
    eng = pt_yol[:-3] + ".engine"
    if os.path.exists(eng) and not zorla:
        print("  ATLANDI (zaten var): %s   [--zorla ile yenile]" % os.path.basename(eng))
        return True
    if imgsz is None:
        imgsz = egitim_imgsz(pt_yol)
    print()
    print("  %s  ->  %s" % (os.path.basename(pt_yol), os.path.basename(eng)))
    print("     imgsz %d   FP16 %s" % (imgsz, "acik" if half else "kapali"))
    print("     ...2-3 dakika surer, bekle")
    t0 = time.time()
    try:
        from ultralytics import YOLO
        YOLO(pt_yol).export(format="engine", imgsz=imgsz, half=half,
                            device=0, simplify=True)
    except Exception as e:
        print("     ⛔ URETILEMEDI: %r" % (e,))
        print("        TensorRT kurulu mu?  pip install tensorrt")
        return False
    if not os.path.exists(eng):
        print("     ⛔ dosya olusmadi"); return False
    print("     ✔ HAZIR  %.1f MB   %.0f sn" % (os.path.getsize(eng)/1048576, time.time()-t0))
    return True


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="TensorRT .engine uret")
    ap.add_argument("--model", help="tek bir .pt yolu")
    ap.add_argument("--hepsi", action="store_true", help="models/ altindaki tum .pt'ler")
    ap.add_argument("--imgsz", type=int, help="elle imgsz (varsayilan: egitim imgsz'i)")
    ap.add_argument("--zorla", action="store_true", help=".engine varsa bile yeniden uret")
    ap.add_argument("--fp32", action="store_true", help="FP16 yerine FP32 (daha yavas)")
    a = ap.parse_args()

    print("=" * 76)
    print("  MOTOR KUR  --  TensorRT .engine uretimi")
    print("=" * 76)
    if not ortam_kontrol():
        print()
        print("  ⛔ Ortam eksik. Yukaridaki ⛔ satirlarini duzeltmeden devam edilemez.")
        return 1

    hedefler = []
    if a.model:
        hedefler = [a.model if os.path.isabs(a.model) else os.path.join(KOK, a.model)]
    elif a.hepsi:
        md = os.path.join(KOK, "models")
        hedefler = sorted(os.path.join(md, f) for f in os.listdir(md) if f.endswith(".pt"))
    else:
        try:
            from guidance.ana_kontrol import Cfg
            hedefler = [Cfg.VIS_MODEL_PATH]
            print()
            print("  aktif model (Cfg.VIS_MODEL_PATH): %s" % os.path.basename(Cfg.VIS_MODEL_PATH))
        except Exception as e:
            print("  ⛔ aktif model okunamadi (%r). --model ile ver." % (e,))
            return 1

    print()
    print("  --- URETIM ---")
    basarili = sum(1 for h in hedefler if kur(h, a.imgsz, a.zorla, half=not a.fp32))
    print()
    print("=" * 76)
    print("  %d / %d hazir" % (basarili, len(hedefler)))
    print()
    print("  SIRADAKI ADIM -- kazanci OLC:")
    print("      python arac/fps_teshis.py")
    print("  Sonra sunucuyu baslat:  python main.py")
    print("  Baslarken su satiri GOR: '[GORSEL] MODEL: ... engine ...'")
    return 0 if basarili == len(hedefler) else 1


if __name__ == "__main__":
    raise SystemExit(main())

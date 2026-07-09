# -*- coding: utf-8 -*-
"""
================================================================================
 TENSORRT EXPORT  (teshis kapanisi — inference hizlandirma, MASTER Asama 6 #3)
================================================================================
models/best.pt -> models/best.engine : ayni model, bu makinenin GPU'suna derlenmis
(FP16). server.py dedektoru engine dosyasini gorunce OTOMATIK onu yukler; silersen
best.pt ile eski davranisa doner. Engine MAKINEYE OZELDIR (gitignore'lu) — baska
bilgisayarda bu script yeniden kosulur (~3-10 dk, tek seferlik).

  python araclar\teshis_trt_export.py            # kare 1280x1280 (KULLAN — sunucu uyumlu)
  python araclar\teshis_trt_export.py --rect     # 736x1280 (DENEME — asagidaki uyariya bak)

UYARI (--rect): rect engine SABIT sekil (736x1280) bekler; server.py ve tum
dedektor cagrilari imgsz=1280 SCALAR (=1280x1280 kare) besler -> rect engine
CANLIDA "input size mismatch" ile coker (9 Tem denendi). Kare 1280x1280 engine
hem sunucuyla uyumlu hem .pt ile dogrulukta birebir (teshis_engine_kiyas.py) —
VARSAYILAN KARE'yi kullan. rect'i istersen once dedektoru imgsz=[736,1280]'e
gecirmek gerekir (kod degisikligi); marjinal hiz icin onerilmez.
Not: imgsz=1280 sabit kalir — 640 uzak/kucuk hedefi olduruyor (CLAUDE.md, 7 Tem kiyas).

GEREKENLER (once elle kur; asagida oto-kurulum BILEREK kapali — 8 Tem gecesi
ultralytics AutoUpdate torch'u PyPI'nin CPU surumuyle ezdi, CUDA gitti):
    pip install tensorrt onnx onnxslim
Eksik paket varsa bu script ACIK HATA verir; kendi kendine pip calistirmaz.
Export sonrasi kontrol: python -c "import torch; print(torch.cuda.is_available())"
"""
import argparse
import os
import time

os.environ.setdefault("YOLO_AUTOINSTALL", "false")   # oto-pip KAPALI (torch'u korur)

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser(description="best.pt -> best.engine (TensorRT FP16)")
    ap.add_argument("--model", default=os.path.join(_KOK, "models", "best.pt"))
    ap.add_argument("--rect", action="store_true",
                    help="736x1280 dikdortgen engine (16:9; varsayilan kare 1280)")
    args = ap.parse_args()

    import torch
    from ultralytics import YOLO
    assert torch.cuda.is_available(), "CUDA yok — engine GPU'da derlenir"
    print("[ENV] torch %s | gpu %s" % (torch.__version__, torch.cuda.get_device_name(0)))

    imgsz = [736, 1280] if args.rect else 1280
    print("[EXPORT] %s -> engine (half=True, imgsz=%s) ... birkac dakika surer"
          % (args.model, imgsz))
    t0 = time.time()
    yol = YOLO(args.model).export(format="engine", half=True, imgsz=imgsz, device=0)
    print("[TAMAM] %.0f sn -> %s" % (time.time() - t0, yol))
    print("server.py bir sonraki gorev baslangicinda engine'i otomatik yukler.")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
TENSORRT MOTOR EXPORT — models/best.pt + models/talon_pose.pt -> models/*.engine
================================================================================
Egitilmis KENDI modellerimizi (agirliklar aynen) RTX Tensor cekirdegine ozel
TensorRT motoruna cevirir; mantik/agirlik DEGISMEZ, yalniz inference backend
optimize olur (kernel fusion + FP16). Motor DONANIMA + TensorRT surumune OZELdir,
tasinabilir DEGIL -> teslim .zip'ine KONMAZ (kaynak = .pt), HER makinede bir kez
uretilir. (.gitignore: models/*.engine repoya da girmez.)

Server bir sonraki baslatmada models/best.engine varsa OTOMATIK onu kullanir
(detection/gorsel_tespit._motor_adaylari); yoksa/bozuksa .pt'ye zarif duser.
Motoru kapatmak / A-B kiyasi:  set AVCI_TRT=0   (o zaman .pt ile calisir).

BEKLENTI (kullanicinin CLAUDE.md notu, 2026-07-08): canli darbogaz OYUNUN GPU'yu
paylasmasi; TensorRT bunu TAMAMEN cozmez ama inference'i kisaltip GPU isgal
penceresini daraltarak cekismeyi bir miktar azaltabilir. Gercek cozum yine oyunun
grafik yukunu/FPS'ini dusurmek. Bu araç zararsiz, opsiyonel bir optimizasyondur.

Kullanim (BU makinede, oyun KAPALIyken; export dakikalar surebilir):
    python araclar/tensorrt_export.py            # ikisi de
    python araclar/tensorrt_export.py best       # sadece detect (best.pt)
    python araclar/tensorrt_export.py pose       # sadece pose (talon_pose.pt)

KRITIK: imgsz export'ta SABITLENIR ve server'daki predict imgsz'iyle AYNI olmali:
    best.pt       -> imgsz=1280  (server: dedektor_dongusu, detect; 640'ta hedef kacar)
    talon_pose.pt -> imgsz=960   (server: POZ; egitim imgsz'i)
Yanlis imgsz -> ultralytics her predict'te yavaslar/uyarir.

!!! KRITIK — TORCH'U KORU: ultralytics export sirasinda "AutoUpdate" ile export
bagimliliklarini kurar; bunlardan `nvidia-modelopt` (INT8 quantize icin, BIZE gereksiz)
`torch>=2.8` ister ve pip torch'u PyPI'dan CPU wheel'ine (`+cpu`) YUKSELTIR -> CUDA GIDER
(tum tespit hatti CPU'ya duser). Onlem: bu script YOLO_AUTOINSTALL=false yapar (asagida)
-> AutoUpdate KAPALI, torch dokunulmaz. O yuzden export bagimliliklari BIR KEZ elle
kurulmalidir (oyun kapaliyken, BU makinede):
    pip install onnx onnxruntime-gpu onnxslim tensorrt-cu12
    # torch CUDA sabit kalmali: pip install torch==2.5.1 torchvision==0.20.1 \
    #        --index-url https://download.pytorch.org/whl/cu121
Motor uretildikten sonra torch'un hala CUDA'li oldugunu dogrula:
    python -c "import torch; print(torch.cuda.is_available())"   # True olmali
"""
import os
import sys

# AutoUpdate KAPALI (torch'u CPU'ya yukseltmesin — yukaridaki KRITIK not). Ultralytics
# import edilmeden ONCE ayarlanir. Eksik export bagimliligi olursa export net hata verir
# (torch'u sessizce bozmaktansa acik hata iyidir); yukaridaki elle-kurulum komutunu uygula.
os.environ.setdefault("YOLO_AUTOINSTALL", "false")

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MODELS = os.path.join(_KOK, "models")

# (ad, .pt dosyasi, export imgsz) — imgsz server predict'iyle BIREBIR.
_HEDEFLER = {
    "best": ("best.pt", 1280),
    "pose": ("talon_pose.pt", 960),
}


def _export_bir(pt_ad, imgsz):
    from ultralytics import YOLO
    pt_yol = os.path.join(_MODELS, pt_ad)
    if not os.path.exists(pt_yol):
        print("  [ATLA] %s yok." % pt_yol)
        return False
    print("  [EXPORT] %s  (imgsz=%d, FP16)  -> motor uretiliyor, bekleyin..." % (pt_ad, imgsz))
    model = YOLO(pt_yol)
    # half=True -> FP16 gomulu; device=0 -> ilk NVIDIA GPU. imgsz SABIT (yukaridaki not).
    yol = model.export(format="engine", imgsz=imgsz, half=True, device=0)
    print("  [OK] motor yazildi: %s" % yol)
    return True


def main(argv):
    secim = [a.lower() for a in argv[1:]] or list(_HEDEFLER.keys())
    # torch/CUDA on-kontrol (net hata mesaji)
    try:
        import torch
        if not torch.cuda.is_available():
            print("HATA: CUDA GPU gorunmuyor. TensorRT export icin NVIDIA GPU + CUDA torch sart.")
            return 2
        print("GPU:", torch.cuda.get_device_name(0))
    except Exception as e:
        print("HATA: torch yuklu degil (%r). Once requirements.txt kur." % e)
        return 2
    ok = 0
    for ad in secim:
        if ad not in _HEDEFLER:
            print("[?] bilinmeyen hedef: %s  (gecerli: %s)" % (ad, ", ".join(_HEDEFLER)))
            continue
        pt_ad, imgsz = _HEDEFLER[ad]
        try:
            if _export_bir(pt_ad, imgsz):
                ok += 1
        except Exception as e:
            print("  [HATA] %s export edilemedi: %r" % (pt_ad, e))
            print("         TensorRT paketi kurulu mu?  ->  pip install tensorrt")
    print("\nBitti: %d motor uretildi. Server bir sonraki baslatmada .engine'i OTOMATIK "
          "kullanir (kapatmak icin: set AVCI_TRT=0)." % ok)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))

# -*- coding: utf-8 -*-
"""
================================================================================
GELISTIRME ARACI — teslim paketine girmez.
================================================================================
POSE FINE-TUNE — hazir agirliktan devam egitimi (tek komut)
================================================================================
Mevcut pose .pt'den (veya yolov8/11-pose'dan) YENI dataset'le devam egitir;
sonuc .pt'yi models/'a ANLAMLI ADLA (task_arch_dataset_imgsz + tarih) kopyalar.
Ultralytics train sarmalayicisi; egitim mantigi ultralytics'te (biz sadece
tutarli konfig + dataset dogrulama + anlamli isimlendirme sagliyoruz).

>>> EGITIMI BU SCRIPT BASLATMAZ (iskele) — --calistir bayragi ACIKCA verilmedikce
    yalnizca PLANI (komut + config) yazar. Dataset hazir olunca --calistir. <<<

ONCE dataset_dogrula.py cagirilir; KRITIK HATA varsa egitim baslamaz.

KULLANIM:
    # plan (varsayilan; egitmez):
    python arac/egitim/pose_egit.py --data <data.yaml> --agirlik models/yolo26m_pose_best.pt
    # gercekten egit:
    python arac/egitim/pose_egit.py --data <data.yaml> --agirlik <w.pt> --calistir \
        --epochs 100 --imgsz 640 --isim yolo_pose_talonv11
================================================================================
"""
import argparse
import os
import shutil
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJ_ROOT = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _PROJ_ROOT)
sys.path.insert(0, _HERE)

import dataset_dogrula


def _tarih_ekle(isim):
    # Date.now yok; dosya-sistemi zaman damgasi yerine kullaniciya isim sorumlulugu.
    # Anlamli ad zaten --isim ile; burada yalniz uzanti garanti.
    return isim if isim.endswith(".pt") else isim + ".pt"


def main():
    ap = argparse.ArgumentParser(description="Pose fine-tune (hazir agirliktan)")
    ap.add_argument("--data", required=True, help="data.yaml yolu")
    ap.add_argument("--agirlik", required=True, help="baslangic .pt (devam egitimi)")
    ap.add_argument("--epochs", type=int, default=100)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--isim", default="yolo_pose_talon_finetune",
                    help="cikti model adi (models/'a bu adla kopyalanir)")
    ap.add_argument("--calistir", action="store_true",
                    help="GERCEKTEN egit (varsayilan: yalniz plan yaz)")
    arg = ap.parse_args()

    # 1) dataset dogrula (kritik hata -> dur)
    print("[EGITIM] Dataset dogrulaniyor...")
    if not dataset_dogrula.dogrula(arg.data):
        print("[EGITIM] KRITIK dataset hatasi -> egitim IPTAL. Once duzelt.")
        return 1

    hedef = os.path.join(_PROJ_ROOT, "models", _tarih_ekle(arg.isim))
    print("\n[EGITIM] PLAN:")
    print("  baslangic agirlik : %s" % arg.agirlik)
    print("  data.yaml         : %s" % arg.data)
    print("  epochs/imgsz/batch: %d / %d / %d" % (arg.epochs, arg.imgsz, arg.batch))
    print("  cikti model       : %s" % hedef)
    print("  ultralytics komut : yolo pose train model=%s data=%s epochs=%d imgsz=%d batch=%d"
          % (arg.agirlik, arg.data, arg.epochs, arg.imgsz, arg.batch))

    if not arg.calistir:
        print("\n[EGITIM] (PLAN modu — egitim BASLATILMADI). Gercek egitim icin --calistir ekle.")
        return 0

    # 2) gercek egitim (ultralytics)
    try:
        from ultralytics import YOLO
    except Exception as e:
        print("[EGITIM][HATA] ultralytics yok: %s" % e)
        return 1
    print("\n[EGITIM] Baslatiliyor (ultralytics)...")
    model = YOLO(arg.agirlik)
    sonuc = model.train(data=arg.data, epochs=arg.epochs, imgsz=arg.imgsz,
                        batch=arg.batch, task="pose")
    # en iyi agirligi models/'a anlamli adla kopyala
    best = None
    try:
        save_dir = getattr(sonuc, "save_dir", None) or model.trainer.save_dir
        best = os.path.join(str(save_dir), "weights", "best.pt")
        if os.path.isfile(best):
            shutil.copy2(best, hedef)
            print("[EGITIM] En iyi agirlik kopyalandi -> %s" % hedef)
            # yaninda yaml (registry per-model config): sema + aciklama
            try:
                yml = os.path.splitext(hedef)[0] + ".yaml"
                with open(yml, "w", encoding="utf-8") as f:
                    f.write("imgsz: %d\nsema: kuyruk_ucu\n"
                            "aciklama: pose fine-tune %s (epochs=%d)\n"
                            % (arg.imgsz, os.path.basename(arg.data), arg.epochs))
                print("[EGITIM] Per-model yaml yazildi -> %s" % yml)
            except Exception:
                pass
        else:
            print("[EGITIM][UYARI] best.pt bulunamadi: %s" % best)
    except Exception as e:
        print("[EGITIM][UYARI] cikti kopyalanamadi: %s" % e)

    # VAL: mAP raporu (yeni modelin PnP'yi besleyebilme kalitesinin ilk sayisi)
    try:
        print("\n[EGITIM] VAL (mAP) hesaplaniyor...")
        m2 = YOLO(hedef if os.path.isfile(hedef) else (best or arg.agirlik))
        metr = m2.val(data=arg.data, imgsz=arg.imgsz, task="pose")
        box = getattr(metr, "box", None)
        pose = getattr(metr, "pose", None)
        print("[EGITIM] === VAL RAPORU ===")
        if box is not None:
            print("[EGITIM] box  mAP50=%.3f mAP50-95=%.3f"
                  % (getattr(box, "map50", 0.0), getattr(box, "map", 0.0)))
        if pose is not None:
            print("[EGITIM] pose mAP50=%.3f mAP50-95=%.3f (keypoint kalitesi)"
                  % (getattr(pose, "map50", 0.0), getattr(pose, "map", 0.0)))
        print("[EGITIM] Not: asil kabul PnP-uygun oran (kosu_yonetici pnp-test);")
        print("           mAP egitim-ici metrik, sim'de gercek kalite olculur.")
    except Exception as e:
        print("[EGITIM][UYARI] val hesaplanamadi: %s" % e)
    print("\n[EGITIM] BITTI. Registry'de gorunmesi icin arayuzde '↻ Tara' -> Yukle.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

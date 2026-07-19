# -*- coding: utf-8 -*-
"""
======================================================================
 TRAIN BOX  —  YOLO Detection egitimi + editore OTOMATIK kurulum
======================================================================
Girdi : talon_box_yolo/data.yaml  (prepare_box_dataset.py ciktisi)
Cikti : runs/talon_detect/weights/best.pt  +  model/best.pt (editore kopyalanir)

Active-learning dongusu:
  etiketle -> prepare_box_dataset -> train_box -> (yeni model OTOMATIK editore kurulur)
  -> editor artik SENIN etiketlerinle cizer -> daha az duzeltme -> tekrar egit ...
======================================================================
"""

import os
import shutil
from ultralytics import YOLO

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_YAML = r"C:\Users\Zeylo\Desktop\talon_box_yolo\data.yaml"   # (pakette: goreli)
MODEL_DST = os.path.join(BASE, "model", "best.pt")              # editorun kullandigi model

BASE_MODEL = "yolo26n.pt"        # saf DETECTION (pose DEGIL)
FALLBACK_MODEL = "yolov8n.pt"
EPOCHS = 100


def deploy_to_editor(best_path):
    """Egitilen best.pt'yi editorun model/ klasorune kopyalar (otomatik hot-swap)."""
    if best_path and os.path.exists(best_path):
        os.makedirs(os.path.dirname(MODEL_DST), exist_ok=True)
        shutil.copy2(best_path, MODEL_DST)
        return True
    return False


def main():
    if not os.path.exists(DATA_YAML):
        print(f"[HATA] data.yaml yok: {DATA_YAML}")
        print("Once prepare_box_dataset.py calistir (etiketleri bol).")
        return

    # GPU varsa otomatik kullan, yoksa CPU
    try:
        import torch
        device = 0 if torch.cuda.is_available() else "cpu"
    except Exception:
        device = "cpu"

    try:
        model = YOLO(BASE_MODEL)
    except Exception:
        print(f"[BILGI] {BASE_MODEL} yok, {FALLBACK_MODEL} kullaniliyor.")
        model = YOLO(FALLBACK_MODEL)

    print(f"=== TALON DETECTION EGITIMI (device={device}) ===")
    model.train(
        data=DATA_YAML,
        epochs=EPOCHS,
        imgsz=640,
        device=device,
        workers=2,
        batch=8,
        project=os.path.join(BASE, "runs"),
        name="talon_detect",
        exist_ok=True,
    )

    # Egitilen modeli editore OTOMATIK kur (hot-swap)
    best = None
    try:
        best = str(model.trainer.best)
    except Exception:
        best = None
    if not best or not os.path.exists(best):
        best = os.path.join(BASE, "runs", "talon_detect", "weights", "best.pt")

    if deploy_to_editor(best):
        print(f"[OK] Yeni model editore kuruldu: {MODEL_DST}")
        print("Editoru tekrar acinca artik SENIN etiketlerinle egitilen model cizecek.")
    else:
        print("[UYARI] best.pt bulunamadi; otomatik kurulum atlandi.")


if __name__ == "__main__":
    main()

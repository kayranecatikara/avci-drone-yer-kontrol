# -*- coding: utf-8 -*-
"""
======================================================================
 PREPARE BOX DATASET  —  YOLO Detection train/val hazirlayici
======================================================================
Girdi : Talon_Box_Dataset/  (bbox_editor.py'nin urettigi png + .txt ciftleri)
Cikti : talon_box_yolo/      (images/train|val + labels/train|val + data.yaml)

Notlar:
  - Etiketler ZATEN dogru YOLO formatinda (.txt). Burada SADECE train/val'a
    bolunur ve kopyalanir. Keypoint turetme / padding YOK (saf detection).
  - Bos .txt'li kareler ATLANMIS demektir; arka plan (negatif) ornegi olarak
    aynen dahil edilir (YOLO bunu destekler ve yanlis pozitifleri azaltir).
======================================================================
"""

import os
import shutil
import random

SOURCE_DIR = r"C:\Users\Zeylo\Desktop\Talon_Box_Dataset"   # bbox_editor ciktisi
OUTPUT_DIR = r"C:\Users\Zeylo\Desktop\talon_box_yolo"       # YOLO veri seti koku
TRAIN_RATIO = 0.8
SEED = 42


def main():
    if not os.path.isdir(SOURCE_DIR):
        print(f"[HATA] Kaynak yok: {SOURCE_DIR}")
        return

    img_train = os.path.join(OUTPUT_DIR, "images", "train")
    img_val = os.path.join(OUTPUT_DIR, "images", "val")
    lbl_train = os.path.join(OUTPUT_DIR, "labels", "train")
    lbl_val = os.path.join(OUTPUT_DIR, "labels", "val")
    for d in (img_train, img_val, lbl_train, lbl_val):
        os.makedirs(d, exist_ok=True)

    # png + txt ciftlerini bul
    pngs = [f for f in os.listdir(SOURCE_DIR) if f.lower().endswith(".png")]
    pairs = []
    for png in sorted(pngs):
        base = os.path.splitext(png)[0]
        txt = base + ".txt"
        if os.path.exists(os.path.join(SOURCE_DIR, txt)):
            pairs.append((png, txt))
        else:
            print(f"[ATLA] Etiket yok: {png}")

    if not pairs:
        print("[HATA] Hic png+txt cifti bulunamadi. Once bbox_editor ile etiketle.")
        return

    n_box = sum(1 for _, t in pairs if os.path.getsize(os.path.join(SOURCE_DIR, t)) > 0)
    n_bg = len(pairs) - n_box
    print(f"Toplam {len(pairs)} cift  ->  kutulu: {n_box}, arka plan(bos): {n_bg}")

    random.seed(SEED)
    random.shuffle(pairs)
    split = int(len(pairs) * TRAIN_RATIO)
    train_pairs, val_pairs = pairs[:split], pairs[split:]
    print(f"Bolme: %{int(TRAIN_RATIO*100)} train ({len(train_pairs)}), "
          f"%{int((1-TRAIN_RATIO)*100)} val ({len(val_pairs)})")

    def copy_set(pairs_set, img_dir, lbl_dir):
        for png, txt in pairs_set:
            shutil.copy2(os.path.join(SOURCE_DIR, png), os.path.join(img_dir, png))
            shutil.copy2(os.path.join(SOURCE_DIR, txt), os.path.join(lbl_dir, txt))

    copy_set(train_pairs, img_train, lbl_train)
    copy_set(val_pairs, img_val, lbl_val)

    # data.yaml (DETECTION — kpt_shape YOK)
    yaml_path = os.path.join(OUTPUT_DIR, "data.yaml")
    yaml = (f"path: {OUTPUT_DIR.replace(chr(92), '/')}\n"
            f"train: images/train\n"
            f"val: images/val\n\n"
            f"names:\n"
            f"  0: talon\n")
    with open(yaml_path, "w", encoding="utf-8") as f:
        f.write(yaml)

    print(f"\n[BITTI] Veri seti hazir: {OUTPUT_DIR}")
    print(f"data.yaml: {yaml_path}")


if __name__ == "__main__":
    main()

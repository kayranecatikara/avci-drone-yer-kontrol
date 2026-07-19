# -*- coding: utf-8 -*-
# ============================================================================
#  parazit_tum_pngler.py
#  ------------------------------------------------------------------------
#  test_parazit.py'deki PARAZIT efektini (analog Gaussian karincalanma)
#  klasordeki TUM .png'lere uygular.
#
#  NOT: test_parazit.py resmin uzerine kirmizi keypoint noktalari da ciziyordu
#  ama o SADECE onizleme icindi. Bu toplu surum egitim resimlerini bozmamak
#  icin SADECE paraziti uygular; keypoint CIZMEZ.
#
#  GUVENLIK: Uzerine yazmadan once orijinal PNG'leri bir kez yedekler.
#  KULLANIM: dataset klasorunde ->  python parazit_tum_pngler.py
# ============================================================================
import cv2
import os
import glob
import shutil
import numpy as np

# ------------------------------- AYARLAR ------------------------------------
KLASOR     = "."                        # islenecek klasor (varsayilan: script'in calistigi klasor)
SIGMA_MIN  = 10                         # parazit siddeti ALT sinir
SIGMA_MAX  = 15                         # parazit siddeti UST sinir
# KULLANICI ISTEGI (2026-07-08): her foto 10-15 arasi RASTGELE bir sigma alir

IN_PLACE   = True                       # True: PNG'lerin UZERINE yaz  |  False: kopyalari OUT_DIR'e yaz
OUT_DIR    = "dataset_parazit"          # IN_PLACE=False ise ciktilar buraya

BACKUP     = True                       # True: uzerine yazmadan ONCE orijinalleri yedekle (sadece 1 kez)
BACKUP_DIR = "dataset_png_temiz_yedek"  # temiz (parazitsiz) orijinallerin yedegi
# ----------------------------------------------------------------------------


def add_noise(image):
    """Analog Gaussian karincalanma (test_parazit.py ile ayni matematik).
    Sigma her cagrida (yani her fotoda) 10-15 arasi rastgele secilir."""
    row, col, ch = image.shape
    sigma = np.random.uniform(SIGMA_MIN, SIGMA_MAX)
    gauss = np.random.normal(0, sigma, (row, col, ch))
    noisy = image.astype(np.float32) + gauss
    return np.clip(noisy, 0, 255).astype(np.uint8)


def main():
    pngs = sorted(glob.glob(os.path.join(KLASOR, "*.png")))   # sadece bu klasor (alt klasorlere girmez)
    if not pngs:
        print("Bu klasorde .png bulunamadi. Script'i 'dataset' klasorunde calistir.")
        return

    print(f"{len(pngs)} PNG bulundu.  SIGMA=her foto rastgele {SIGMA_MIN}-{SIGMA_MAX}  IN_PLACE={IN_PLACE}")

    # --- yedek (yalnizca uzerine yaziyorsak ve ilk kez) ---
    if IN_PLACE and BACKUP:
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
            for p in pngs:
                shutil.copy2(p, os.path.join(BACKUP_DIR, os.path.basename(p)))
            print(f"Temiz orijinaller yedeklendi: {BACKUP_DIR}\\  ({len(pngs)} PNG)")
        else:
            print(f"UYARI: '{BACKUP_DIR}' zaten var -> yedek ATLANDI.")
            print("       (Tekrar calistirirsan parazit UST USTE binebilir. Temiz baslamak")
            print(f"        istiyorsan once {BACKUP_DIR}\\ icindekileri geri kopyala.)")

    if not IN_PLACE and not os.path.exists(OUT_DIR):
        os.makedirs(OUT_DIR)

    done = 0
    for i, p in enumerate(pngs):
        img = cv2.imread(p)
        if img is None:
            print(f"  atlandi (okunamadi): {p}")
            continue
        noisy = add_noise(img)
        out_path = p if IN_PLACE else os.path.join(OUT_DIR, os.path.basename(p))
        cv2.imwrite(out_path, noisy)
        done += 1
        if (i + 1) % 200 == 0:
            print(f"  [{i+1}/{len(pngs)}] islendi...")

    hedef = "yerinde (uzerine yazildi)" if IN_PLACE else f"{OUT_DIR}\\"
    print(f"\nTAMAM! {done} PNG parazitlendi -> {hedef}")
    if IN_PLACE and BACKUP:
        print(f"Geri almak icin: {BACKUP_DIR}\\ icindeki PNG'leri bu klasore geri kopyala.")


if __name__ == "__main__":
    main()

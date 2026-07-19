# -*- coding: utf-8 -*-
r"""
Toplu BBOX uretimi: 1, 2, 3, 4 klasorlerindeki tum ciftleri isler
==================================================================
Her far_XXXX.png + .json cifti icin:
  1) draw_bbox'in AYNEN AYNI hesabıyla (min/max, pay=0, sinira kirpma)
     kutu hesaplanir - hesaplamalara DOKUNULMADI, import edildi.
  2) Kare, temizleyicinin kurallarindan gecirilir (kutuda talon var mi,
     yazi arkasinda mi, asiri kucuk mu, oyun karesi mi...).
  3) SAGLAM ise:
     - Ayni klasore YOLO formatinda far_XXXX.txt yazilir (class 0,
       normalize cx cy w h)
     - Kutu cizilmis onizleme kontrol\ klasorune JPEG olarak konur
  4) HATALI ise (noktalar yanlis / talon kutuda degil vb.):
     - Cift (png+json) dogrudan elenen\ klasorune tasinir
     - Sebep ve kaynak klasor rapora yazilir
Sonunda ozet + elenen listesi ekrana ve elenen_raporu.txt'ye yazilir.

Kullanim:  python toplu_bbox.py
"""

import json
import shutil
import sys
from pathlib import Path

import cv2

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# draw_bbox'in hesabi ve cizimi AYNEN kullanilir (kopya degil, import)
from draw_bbox import compute_bbox, load_keypoints, draw_bbox
# Dogrulama: temizleyicinin kanitlanmis kurallari (K2..K8)
import desync_kontrol as dk

KOK = Path(__file__).parent
# Rakam isimli TUM alt klasorler otomatik bulunur (1..4 de olur 1..8 de)
KLASORLER = sorted((p.name for p in KOK.iterdir() if p.is_dir() and p.name.isdigit()), key=int)
KONTROL = KOK / "kontrol"
ELENEN = KOK / "elenen"
RAPOR = KOK / "elenen_raporu.txt"
JPEG_KALITE = 90  # kontrol onizlemeleri JPEG olur (disk dostu; egitim verisi PNG'ler el degmeden kalir)


def yolo_satiri(box, img_w, img_h):
    """Kutuyu YOLO formatina cevirir: class cx cy w h (normalize)."""
    x1, y1, x2, y2 = box
    cx = (x1 + x2) / 2.0 / img_w
    cy = (y1 + y2) / 2.0 / img_h
    bw = (x2 - x1) / img_w
    bh = (y2 - y1) / img_h
    return f"0 {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\n"


def main():
    KONTROL.mkdir(exist_ok=True)
    ELENEN.mkdir(exist_ok=True)

    saglam, elenen_liste, hata = 0, [], 0
    islenen = 0

    for klasor_adi in KLASORLER:
        klasor = KOK / klasor_adi
        if not klasor.is_dir():
            print(f"[UYARI] {klasor_adi} klasoru yok, atlandi")
            continue

        for jp in sorted(klasor.glob("*.json")):  # on-ek fark etmez (talon_/far_...)
            ip = jp.with_suffix(".png")
            if not ip.exists():
                continue
            islenen += 1
            if islenen % 200 == 0:
                print(f"  ... {islenen} cift islendi")

            # Temizleyici kurallariyla dogrula (kutuda talon var mi vb.)
            durum, aciklama = dk.kareyi_analiz_et(ip, jp)

            if durum == "SAGLAM":
                img = cv2.imread(str(ip))
                if img is None:
                    hata += 1
                    continue
                h, w = img.shape[:2]
                box = compute_bbox(load_keypoints(jp), w, h)  # draw_bbox'in ayni hesabi
                if box is None:
                    # teoride buraya dusmez (dogrulama gecti) ama guvenlik
                    elenen_liste.append((klasor_adi, jp.stem, "kutu hesaplanamadi"))
                    continue

                # 1) YOLO txt AYNI klasore (cift + etiket bir arada)
                (klasor / f"{jp.stem}.txt").write_text(yolo_satiri(box, w, h), encoding="utf-8")

                # 2) Kutu cizili onizleme -> kontrol\ (JPEG)
                draw_bbox(img, box)
                cv2.imwrite(str(KONTROL / f"{jp.stem}.jpg"), img,
                            [cv2.IMWRITE_JPEG_QUALITY, JPEG_KALITE])
                saglam += 1

            elif durum == "HATALI":
                # Cift dogrudan elenen'e (png + json birlikte)
                for f in (ip, jp):
                    shutil.move(str(f), str(ELENEN / f.name))
                elenen_liste.append((klasor_adi, jp.stem, aciklama))

            else:  # HATA (okunamadi)
                hata += 1
                print(f"[HATA] {jp.stem}: {aciklama}")

    # ---- Ozet + rapor ----
    print("\n" + "=" * 60)
    print(f"SAGLAM: {saglam} cift -> txt uretildi, kontrol\\ icine cizildi")
    print(f"ELENEN: {len(elenen_liste)} cift -> elenen\\ klasorune tasindi")
    if hata:
        print(f"OKUNAMAYAN: {hata}")

    satirlar = ["Elenen ciftler (kaynak klasor | dosya | sebep)", "=" * 60]
    for klasor_adi, stem, sebep in elenen_liste:
        satirlar.append(f"{klasor_adi} | {stem} | {sebep}")
    RAPOR.write_text("\n".join(satirlar) + "\n", encoding="utf-8")
    print(f"\nRapor: {RAPOR}")

    if elenen_liste:
        print("\nELENEN LISTESI:")
        for klasor_adi, stem, sebep in elenen_liste:
            print(f"  [{klasor_adi}] {stem}: {sebep}")


if __name__ == "__main__":
    main()

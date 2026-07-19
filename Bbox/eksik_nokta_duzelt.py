# -*- coding: utf-8 -*-
r"""
Noktasi silinmis karelerde kutuyu gorunur siluetle tamamlama
=============================================================
Kullanici bazi keypoint'leri (cogunlukla Nose) editorde sildi; kutu kalan
noktalardan hesaplaninca talonun govdesini kesebiliyor (orn. far_3400).

Cozum: SADECE noktasi eksik (keypoints_2d < 6) karelerde:
  1) Nokta-kutusu hesaplanir (draw_bbox'in AYNI hesabi - dokunulmadi)
  2) Kutu cevresindeki pencerede talonun gorunur silueti tespit edilir:
     zemine gore YEREL KONTRAST (halka medyanindan fark > esik) - bu yontem
     zeminden bagimsizdir (kum, gokyuzu, deniz...)
  3) Nokta-kutusuna DEGEN siluet parcalariyla BIRLESIM kutusu alinir
     (kutu yalnizca BUYUYEBILIR; asiri buyume sinirlanir)
  4) txt yeniden yazilir, kontrol\ onizlemesi yeniden cizilir
6 noktasi tam olan karelere DOKUNULMAZ.

Kullanim:  python eksik_nokta_duzelt.py
"""

import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from draw_bbox import compute_bbox, load_keypoints, draw_bbox

KOK = Path(__file__).parent
# Rakam isimli TUM alt klasorler otomatik bulunur
KLASORLER = sorted((p.name for p in KOK.iterdir() if p.is_dir() and p.name.isdigit()), key=int)
KONTROL = KOK / "kontrol"
JPEG_KALITE = 90

KONTRAST_FARK = 28   # zeminden fark ALT esigi (grenli karede otomatik yukselir)
MIN_PARCA = 12       # bu kadar pikselden kucuk siluet parcalari gurultudur
PENCERE_ORAN = 0.6   # arama penceresi: kutu her yana maxdim*0.6 genisler
BUYUME_ORAN = 0.5    # kutu her yana en fazla maxdim*0.5 buyuyebilir (emniyet;
                     # silinen burun/pervane uzantisi bundan fazla olamaz)


def siluet_birlesim_kutusu(img, box):
    """Nokta-kutusunu, ona degen gorunur siluet parcalariyla genisletir."""
    h, w = img.shape[:2]
    x1, y1, x2, y2 = box
    maxdim = max(x2 - x1, y2 - y1)
    pencere = max(24, int(maxdim * PENCERE_ORAN))
    buyume = max(10, int(maxdim * BUYUME_ORAN))

    wx1, wy1 = max(0, x1 - pencere), max(0, y1 - pencere)
    wx2, wy2 = min(w, x2 + pencere + 1), min(h, y2 + pencere + 1)
    bolge = img[wy1:wy2, wx1:wx2].astype(np.int16)

    # Zemin rengi: pencerenin medyani (talon kucuk bir kesir, medyani bozmaz)
    zemin = np.median(bolge.reshape(-1, 3), axis=0)
    fark = np.abs(bolge - zemin).max(axis=2)
    # Sabit esik: gercek siluet parcalarini kacirmamak icin 28'de tutulur;
    # gren/gurultu zincirlerini asagidaki morfoloji + yogunluk filtreleri eler
    maske = (fark > KONTRAST_FARK).astype(np.uint8) * 255
    # tuz-biber gurultusunu at, govde parcalarini birlestir
    maske = cv2.morphologyEx(maske, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    maske = cv2.morphologyEx(maske, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))

    n, etiketler, stats, _ = cv2.connectedComponentsWithStats(maske)

    # Parca basina ortalama kontrast: buyuk ama SOLUK parcalar (gokyuzu
    # degradesi, bulut bandi) siluet degildir; talon govdesi guclu kontrastlidir
    duz = etiketler.ravel()
    toplam = np.bincount(duz, weights=fark.ravel().astype(np.float64), minlength=n)
    adet = np.bincount(duz, minlength=n)
    ort_fark = toplam / np.maximum(adet, 1)
    pencere_alani = float(maske.size)

    # pencere koordinatinda nokta-kutusu (2 px tolerans ile)
    bx1, by1 = x1 - wx1 - 2, y1 - wy1 - 2
    bx2, by2 = x2 - wx1 + 2, y2 - wy1 + 2

    # Her parcanin KUTU ICINDEKI piksel sayisi: gercek siluet kutuyu ciddi
    # oranda doldurur (noktalar orada cunku); bulut/cali kenardan ancak
    # kirinti sokar. Bu sayim, "koseden degdi diye birlesime girme"yi bitirir.
    ky1, ky2 = max(0, int(by1)), min(maske.shape[0], int(by2))
    kx1, kx2 = max(0, int(bx1)), min(maske.shape[1], int(bx2))
    kutu_dilimi = etiketler[ky1:ky2, kx1:kx2]
    icte = np.bincount(kutu_dilimi.ravel(), minlength=n)
    kutu_alani_px = max(1, kutu_dilimi.size)

    ux1, uy1, ux2, uy2 = x1, y1, x2, y2
    for i in range(1, n):
        px, py, pw, ph, alan = stats[i]
        if alan < MIN_PARCA:
            continue
        # seyrek/zincir gurultu parcalari (dusuk doluluk) siluet degildir
        if alan / float(pw * ph) < 0.15:
            continue
        # pencerenin %5'inden buyuk parcalar guclu kontrast gostermeli
        # (gokyuzu/bulut bandi ~30'larda kalir, talon govdesi 60+ olur)
        if alan > 0.05 * pencere_alani and ort_fark[i] < 40:
            continue
        # parca kutunun icini yeterince dolduruyor mu? (degmek yetmez)
        if icte[i] < max(20, 0.05 * kutu_alani_px):
            continue
        # birlesime kat (dunya koordinatina cevir)
        ux1 = min(ux1, wx1 + px)
        uy1 = min(uy1, wy1 + py)
        ux2 = max(ux2, wx1 + px + pw - 1)
        uy2 = max(uy2, wy1 + py + ph - 1)

    # emniyet: asiri buyumeyi sinirla (calilik vb. birlesirse)
    ux1 = max(ux1, x1 - buyume); uy1 = max(uy1, y1 - buyume)
    ux2 = min(ux2, x2 + buyume); uy2 = min(uy2, y2 + buyume)
    # goruntu sinirlari
    ux1 = max(0, ux1); uy1 = max(0, uy1)
    ux2 = min(w - 1, ux2); uy2 = min(h - 1, uy2)
    return int(ux1), int(uy1), int(ux2), int(uy2)


def yolo_satiri(box, img_w, img_h):
    x1, y1, x2, y2 = box
    return (f"0 {(x1+x2)/2.0/img_w:.6f} {(y1+y2)/2.0/img_h:.6f} "
            f"{(x2-x1)/img_w:.6f} {(y2-y1)/img_h:.6f}\n")


def main():
    duzeltilen, ayni_kalan, atlanan = 0, 0, 0
    buyumeler = []

    for k in KLASORLER:
        for jp in sorted((KOK / k).glob("*.json")):
            d = json.loads(jp.read_text(encoding="utf-8"))
            if len(d.get("keypoints_2d") or {}) >= 6:
                continue  # 6 noktasi tam: DOKUNMA

            ip = jp.with_suffix(".png")
            img = cv2.imread(str(ip))
            if img is None:
                atlanan += 1
                continue
            h, w = img.shape[:2]

            box = compute_bbox(load_keypoints(jp), w, h)
            if box is None:
                atlanan += 1
                continue

            yeni = siluet_birlesim_kutusu(img, box)
            if yeni == box:
                ayni_kalan += 1
                continue

            # txt guncelle + kontrol onizlemesini yeniden ciz
            (KOK / k / f"{jp.stem}.txt").write_text(yolo_satiri(yeni, w, h), encoding="utf-8")
            draw_bbox(img, yeni)
            cv2.imwrite(str(KONTROL / f"{jp.stem}.jpg"), img,
                        [cv2.IMWRITE_JPEG_QUALITY, JPEG_KALITE])
            duzeltilen += 1
            buyumeler.append((yeni[0]-box[0], yeni[1]-box[1], yeni[2]-box[2], yeni[3]-box[3], jp.stem))

    print(f"DUZELTILEN: {duzeltilen} kare (kutu genisletildi, txt+onizleme yenilendi)")
    print(f"AYNI KALAN: {ayni_kalan} kare (siluet zaten kutunun icindeydi)")
    if atlanan:
        print(f"ATLANAN: {atlanan}")
    if buyumeler:
        px = [max(abs(a), abs(b), abs(c), abs(d)) for a, b, c, d, _ in buyumeler]
        print(f"en buyuk kenar genislemesi: medyan {int(np.median(px))} px, max {max(px)} px")
        enb = max(buyumeler, key=lambda t: max(abs(t[0]), abs(t[1]), abs(t[2]), abs(t[3])))
        print(f"ornek (en cok buyuyen): {enb[4]}")


if __name__ == "__main__":
    main()

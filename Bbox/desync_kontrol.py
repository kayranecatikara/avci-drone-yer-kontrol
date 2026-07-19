# -*- coding: utf-8 -*-
"""
Dataset temizleyici — hatalı kareleri otomatik tespit edip ayıklar
===================================================================
Bir kare şu KURALLARDAN birine takılırsa HATALI sayılır ve ayıklanır:

  K1) Fotoğrafın JSON'u yok (hiç noktalanmamış) ya da JSON'da keypoint yok.
  K2) Hiçbir nokta kare içinde görünmüyor (hepsi on:false ya da koordinatı
      görüntü dışında — JSON'da on:true yazsa bile koordinat kontrol edilir).
  K3) Sadece birkaç nokta görünüyor: kare içindeki nokta sayısı < MIN_NOKTA.
  K4) Talon, OSD yazılarının arkasında: kutu içinde saf beyaz OSD yazı
      pikselleri var (DISARMED, ALT, SPD, batarya vb. bindirme yazıları).
  K5/K6) Kutuda talon bulunamadı: noktalar görüntüyle eşleşmiyor (desync,
      talon_1252 durumu) ya da talon hiç görünmüyor. Üç bağımsız sinyalin
      üçü de boş çıkarsa kare elenir:
        a) mavi-gri HSV maskesi, b) gevşetilmiş HSV maskesi,
        c) yerel kontrast: kutu içindeki piksellerin, kutu çevresindeki
           halkanın medyan renginden farkı (kutu alanının en az %2'si).
      (c) sayesinde parlak/beyaz görünen talonlar da tanınır; deniz/koyu
      arazi gibi mavi zeminlerin yol açtığı yanlış alarmlar da biter.
  K7) Görüntü oyun karesi bile değil (EN ÖNCE kontrol edilir): siyah/karanlık
      ekran, tekdüze boş ekran, ya da OSD yazıları (sinyal / ALT-SPD / batarya)
      bulunmayan görüntü — izleme ekranı, MISSION COMPLETE, menü, masaüstü,
      tarayıcı vb. (örn. talon_0168 masaüstü, talon_0975 izleme, talon_1120
      Chrome bu kurala takılır).

Talon tespiti renk tabanlıdır: mavi-gri gövde, kum (turuncu) ve bulut
(renksiz) zeminden HSV uzayında ayrışır. K6'dan önce gevşetilmiş eşiklerle
ikinci bir geçiş yapılır ki tam yandan görünen soluk/ince talonlar (örn.
talon_1247) yanlışlıkla "görünmüyor" sayılmasın.

Kullanım:
    python desync_kontrol.py                # sadece RAPOR, hiçbir dosyaya dokunmaz
    python desync_kontrol.py --uygula       # HATALI çiftleri ./elenen klasörüne taşır
    python desync_kontrol.py --uygula --kalici-sil   # taşımak yerine kalıcı siler
    python desync_kontrol.py --dir "D:\\klasor" --uygula   # başka klasörde çalıştır
    python desync_kontrol.py --min-nokta 6  # 6'dan az nokta görünen her kareyi ele
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np

# Kutu hesabı draw_bbox.py'den alınır (çizimle birebir aynı formül)
from draw_bbox import compute_bbox

# Windows konsolu varsayılan olarak cp1252 olabilir; Türkçe karakterler için UTF-8
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ------------------------------- Eşikler -------------------------------
MIN_NOKTA = 4       # kare içinde görünmesi gereken en az nokta sayısı (K3)
MIN_KUTU_KENAR = 6  # kutunun kısa kenarı bundan küçükse talon aşırı küçük (K8)
TOLERANS = 5        # kutuya eklenen pay (px): kenardaki yumuşak pikseller için
MIN_IC = 10         # "kutuda talon var" için gereken min. mavi piksel
MIN_IC_GEVSEK = 8   # gevşek eşikli ikinci geçiş için min. piksel (yandan görünüm)
HALKA = 30          # kontrast için kutu çevresinden alınan zemin örneği (px)
KONTRAST_FARK = 28  # bir pikselin "zeminden farklı" sayılması için renk farkı
KONTRAST_ORAN = 0.02  # kutu alanının en az bu oranı zeminden farklıysa talon var
KONTRAST_MIN = 6    # çok küçük kutular için mutlak alt sınır (px)
BEYAZ_ESIK = 245    # OSD yazısı saf beyazdır; 3 kanal da bu değerin üstündeyse yazı
YAZI_ESIK = 40      # kutu içinde bu kadar yazı pikseli varsa "yazının arkasında"
# Talon gövdesinin HSV aralığı (mavi-gri) — normal ve gevşetilmiş eşikler
HSV_NORMAL = (np.array([90, 25, 50]), np.array([140, 255, 255]))
HSV_GEVSEK = (np.array([85, 12, 25]), np.array([145, 255, 255]))
# K7 eşikleri: siyah/tekdüze ekran ve OSD (HUD yazısı) yokluğu
SIYAH_ORT = 12        # gri ortalaması bunun altındaysa siyah ekran
TEKDUZE_STD = 6       # gri std bunun altındaysa tekdüze/boş ekran
# OSD bölgeleri (1920x1080 referans; farklı çözünürlükte oranlanır):
# sol-üst sinyal, sağ-üst ALT/SPD, sol-alt batarya blokları
OSD_BOLGELERI = [(90, 45, 280, 175), (1660, 40, 1880, 170), (95, 835, 320, 1035)]
MIN_OSD_PIKSEL = 50   # bölge başına en az saf beyaz piksel
MIN_OSD_BOLGE = 2     # en az bu kadar bölgede OSD bulunmalı


def talon_maskesi(img_bgr, esik):
    """Talon rengindeki pikselleri 0/255 maskesi olarak döndürür."""
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    return cv2.inRange(hsv, esik[0], esik[1])


def oyun_karesi_mi(img):
    """Görüntü gerçek bir oyun karesi mi? OSD yazı bölgelerini kontrol eder.

    Geçerli oyun karesinde OSD blokları saf beyaz piksellerle doludur; izleme
    ekranı, MISSION COMPLETE, menü, masaüstü ve tarayıcı görüntülerinde bu
    bölgeler boştur. Bölgeler 1920x1080 referansından orana göre ölçeklenir.
    """
    h, w = img.shape[:2]
    sx, sy = w / 1920.0, h / 1080.0
    bulunan = 0
    for x1, y1, x2, y2 in OSD_BOLGELERI:
        b = img[int(y1*sy):int(y2*sy), int(x1*sx):int(x2*sx)]
        if int(np.count_nonzero(np.all(b >= 245, axis=2))) >= MIN_OSD_PIKSEL:
            bulunan += 1
    return bulunan >= MIN_OSD_BOLGE


def kareyi_analiz_et(img_path: Path, json_path):
    """Bir kareyi tüm kurallardan geçirir; (durum, açıklama) döndürür."""
    img = cv2.imread(str(img_path))
    if img is None:
        return "HATA", "görüntü okunamadı"
    h, w = img.shape[:2]

    # K7 (en önce): görüntü oyun karesi mi? Siyah / tekdüze / OSD'siz ekranlar
    # JSON'a bakmaya bile gerek kalmadan elenir.
    gri = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if float(gri.mean()) < SIYAH_ORT:
        return "HATALI", f"K7: siyah/karanlık ekran (ort. parlaklık {gri.mean():.1f})"
    if float(gri.std()) < TEKDUZE_STD:
        return "HATALI", f"K7: tekdüze/boş ekran (std {gri.std():.1f})"
    if not oyun_karesi_mi(img):
        return "HATALI", "K7: oyun karesi değil — OSD yok (izleme/menü/masaüstü/tarayıcı)"

    # K1: JSON hiç yok ya da içinde keypoint yok
    if json_path is None or not json_path.exists():
        return "HATALI", "K1: JSON'u yok — fotoğraf hiç noktalanmamış"
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
        kps = data.get("keypoints_2d") or {}
    except (json.JSONDecodeError, OSError):
        return "HATALI", "K1: JSON okunamadı/bozuk"
    if not kps:
        return "HATALI", "K1: JSON'da hiç keypoint yok"

    # K2-K3: kare içinde gerçekten görünen noktaları say
    # (memory'deki bilinen tuzak: on:true yazsa bile koordinat kare dışı olabilir)
    tum_noktalar = [(kp["x"], kp["y"]) for kp in kps.values()]
    gorunur = [
        (kp["x"], kp["y"]) for kp in kps.values()
        if kp.get("on", True) and 0 <= kp["x"] < w and 0 <= kp["y"] < h
    ]
    if len(gorunur) == 0:
        return "HATALI", "K2: hiçbir nokta kare içinde değil (talon kare dışında)"
    if len(gorunur) < MIN_NOKTA:
        return "HATALI", f"K3: sadece {len(gorunur)}/{len(tum_noktalar)} nokta kare içinde"

    # Çizimle aynı kutu (tüm noktalardan, kare sınırına kırpılmış)
    box = compute_bbox(tum_noktalar, w, h, padding=0)
    if box is None:
        return "HATALI", "K2: keypoint'lerden geçerli kutu çıkmadı"
    x1, y1, x2, y2 = box

    # K8: talon aşırı küçük — 640'a küçültülmüş eğitimde ~2-3 piksele düşen
    # kareler modele katkı vermez (kullanıcı seçimi 2026-07-08: eşik 6 px)
    if min(x2 - x1, y2 - y1) < MIN_KUTU_KENAR:
        return "HATALI", f"K8: talon aşırı küçük (kutu {x2-x1}x{y2-y1} px)"

    ix1, iy1 = max(0, x1 - TOLERANS), max(0, y1 - TOLERANS)
    ix2, iy2 = min(w, x2 + TOLERANS + 1), min(h, y2 + TOLERANS + 1)
    kutu_bolgesi = img[iy1:iy2, ix1:ix2]

    # K4: kutu içinde OSD yazısı var mı? (yazı saf beyaz; talon gövdesi değil)
    beyaz = int(np.count_nonzero(np.all(kutu_bolgesi >= BEYAZ_ESIK, axis=2)))
    if beyaz >= YAZI_ESIK:
        return "HATALI", f"K4: talon yazıların arkasında (kutuda {beyaz} px OSD yazısı)"

    # K5-K6: kutuda talon var mı? Üç bağımsız sinyal denenir:
    #  1) mavi-gri HSV maskesi (normal eşik)
    ic = int(np.count_nonzero(talon_maskesi(kutu_bolgesi, HSV_NORMAL)))
    if ic >= MIN_IC:
        return "SAGLAM", f"kutuda {ic} px talon (mavi)"
    #  2) gevşetilmiş HSV maskesi (yandan/soluk görünümler)
    ic_gevsek = int(np.count_nonzero(talon_maskesi(kutu_bolgesi, HSV_GEVSEK)))
    if ic_gevsek >= MIN_IC_GEVSEK:
        return "SAGLAM", f"kutuda {ic_gevsek} px talon (soluk/yandan görünüm)"
    #  3) yerel kontrast: talon hangi renkte olursa olsun (beyaz dahil) çevre
    #     zeminden farklıdır. Kutu çevresindeki halkanın medyan rengi zemin
    #     kabul edilir; kutuda bu renkten belirgin farklı piksel oranına bakılır.
    rx1, ry1 = max(0, x1 - HALKA), max(0, y1 - HALKA)
    rx2, ry2 = min(w, x2 + HALKA + 1), min(h, y2 + HALKA + 1)
    zemin = np.median(img[ry1:ry2, rx1:rx2].reshape(-1, 3).astype(np.int16), axis=0)
    fark = np.abs(kutu_bolgesi.astype(np.int16) - zemin).max(axis=2)
    kontrast = int(np.count_nonzero(fark > KONTRAST_FARK))
    kontrast_esigi = max(KONTRAST_MIN, KONTRAST_ORAN * kutu_bolgesi.shape[0] * kutu_bolgesi.shape[1])
    if kontrast >= kontrast_esigi:
        return "SAGLAM", f"kutuda talona benzer kütle (kontrast {kontrast} px)"

    return "HATALI", (f"K5/K6: kutuda talon bulunamadı — desync ya da görünmüyor "
                      f"(mavi {ic}, gevşek {ic_gevsek}, kontrast {kontrast} px)")


def kareyi_ayikla(stem: str, kok: Path, kalici: bool):
    """HATALI karenin dosyalarını ./elenen'e taşır (veya kalıcı siler)."""
    hedef = kok / "elenen"
    for f in [kok / f"{stem}.json", kok / f"{stem}.png"]:
        if not f.exists():
            continue
        if kalici:
            f.unlink()
        else:
            hedef.mkdir(exist_ok=True)
            shutil.move(str(f), str(hedef / f.name))
    # Bu kareden üretilmiş eski bbox çıktısı da artık geçersiz -> kaldır
    eski_cikti = kok / "bbox_output" / f"{stem}.png"
    if eski_cikti.exists():
        eski_cikti.unlink()
    print(f"       -> {stem} {'kalıcı silindi' if kalici else 'elenen\\ klasörüne taşındı'}")


def main():
    global MIN_NOKTA
    parser = argparse.ArgumentParser(description="Dataset temizleyici: hatalı kareleri tespit eder ve ayıklar")
    parser.add_argument("--dir", type=Path, default=Path(__file__).parent,
                        help="görüntü + JSON çiftlerinin klasörü")
    parser.add_argument("--uygula", action="store_true",
                        help="HATALI kareleri ayıkla (bunsuz sadece rapor yazar)")
    parser.add_argument("--kalici-sil", action="store_true",
                        help="--uygula ile: taşımak yerine kalıcı sil")
    parser.add_argument("--min-nokta", type=int, default=MIN_NOKTA,
                        help=f"kare içinde görünmesi gereken en az nokta (varsayılan: {MIN_NOKTA})")
    args = parser.parse_args()
    MIN_NOKTA = args.min_nokta

    # Hem JSON'lu çiftleri hem JSON'suz yetim PNG'leri tara
    stemler = sorted({p.stem for p in args.dir.glob("*.png")} |
                     {p.stem for p in args.dir.glob("*.json")})

    sayac = {"SAGLAM": 0, "HATALI": 0, "HATA": 0}
    hatalilar = []
    for stem in stemler:
        img_path = args.dir / f"{stem}.png"
        json_path = args.dir / f"{stem}.json"
        if not img_path.exists():
            print(f"[ATLA    ] {stem}: PNG yok (tek başına JSON)")
            continue
        durum, aciklama = kareyi_analiz_et(img_path, json_path if json_path.exists() else None)
        sayac[durum] += 1
        print(f"[{durum:8s}] {stem}: {aciklama}")
        if durum == "HATALI":
            hatalilar.append(stem)
            if args.uygula:
                kareyi_ayikla(stem, args.dir, args.kalici_sil)

    print(f"\nÖzet: {sayac['SAGLAM']} sağlam, {sayac['HATALI']} hatalı, {sayac['HATA']} okunamadı.")
    if hatalilar and not args.uygula:
        print(f"Ayıklamak için: python {Path(__file__).name} --uygula")


if __name__ == "__main__":
    main()

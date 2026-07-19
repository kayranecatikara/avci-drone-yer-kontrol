# -*- coding: utf-8 -*-
# ============================================================================
# DATASET TEMIZLEYICI
# dataset\ icindeki png+json ciftlerini tek tek kontrol eder, KUSURLU olan
# ciftleri KALICI olarak siler (dataset_annotated'daki kopyasiyla birlikte).
#
# SILME KURALLARI (kullanici istegi 2026-07-07):
#   1) JSON bozuk / keypoints_2d yok veya bos          -> SIL ("hic noktalamiyor")
#   2) 6 keypoint tam degil (eksik/fazla/yanlis isim)  -> SIL
#   3) Herhangi bir keypoint on=false                  -> SIL (nokta yok)
#   4) EN AZ 1 keypoint foto sinirlari DISINDA         -> SIL
#   5) Talon, ekran yazilarinin (OSD) ARKASINDA        -> SIL
#      (yazi bolgeleri 3 ornekten piksel olcumuyle sabitlendi; silme karari
#       SADECE o karede yazi pikseli gercekten talonun ustundeyse verilir)
#
#   NOT: "kirmizi nokta cizilmis mi" ve "yesil overlay" kontrolleri KALDIRILDI:
#   goruntulerdeki kromatik sapma sacaklari bu iki tespiti kandiriyor (kesin
#   degil). Nokta dogrulugu zaten JSON kurallariyla garanti ediliyor.
#
# RAPOR (silinmez, sadece listelenir):
#   - Talon'un gorunmuyor OLABILECEGI kareler (arka planla ayirt edilemiyor)
#
# Kullanim:
#   python dataset_temizleyici.py            -> KALICI SILER
#   python dataset_temizleyici.py --dry-run  -> sadece raporlar, SILMEZ
# ============================================================================
import os
import sys
import json
import time

WORKSPACE = r"c:\Users\Zeylo\Desktop\talon_dataset"
DATASET_DIR = os.path.join(WORKSPACE, "dataset")
ANNOTATED_DIR = os.path.join(WORKSPACE, "dataset_annotated")
REPORT_FILE = os.path.join(WORKSPACE, "temizlik_raporu.txt")

EXPECTED_KEYPOINTS = {"Nose", "Left_Wingtip", "Right_Wingtip",
                      "Tail", "Left_Tail_Fin", "Right_Tail_Fin"}

# Sabit OSD yazi bolgeleri (1920x1080; talon_0001/0110/0218 uzerinde piksel
# olcumu - uc karede de birebir ayni cikti). +6 px guvenlik payi eklenir.
OSD_ZONES = [
    (104, 66, 260, 158),     # sol ust: RSSI / LQ
    (1677, 51, 1864, 152),   # sag ust: sure / ALT / SPD
    (609, 704, 1309, 769),   # merkez: DISARMED / TRIGGER: NOT READY
    (1513, 771, 1881, 788),  # sag alt: Mode: ANGL AIR
    (105, 847, 293, 934),    # sol alt: amper / volt
    (105, 990, 293, 1028),   # sol alt: ikinci volt satiri
]
ZONE_MARGIN = 6      # OSD bolgesi guvenlik payi (px)
BBOX_MARGIN = 12     # talon kutusu guvenlik payi (px)
TEXT_PIXEL_MIN = 8   # bu kadar yazi pikseli talonun ustundeyse "arkasinda" say

IN_FLIGHT_SECONDS = 15  # bu kadar yeni dosyalara dokunma (oyun su an yaziyor olabilir)

try:
    from PIL import Image
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
    from PIL import Image


def is_text_pixel(px, W, H, x, y):
    """OSD pixel-font tespiti: cok parlak beyaz piksel + 2px icinde cok koyu komsu."""
    r, g, b = px[x, y][:3]
    if r < 245 or g < 245 or b < 245:
        return False
    for dx in (-2, -1, 0, 1, 2):
        for dy in (-2, -1, 0, 1, 2):
            nx, ny = x + dx, y + dy
            if 0 <= nx < W and 0 <= ny < H:
                r2, g2, b2 = px[nx, ny][:3]
                if r2 <= 60 and g2 <= 60 and b2 <= 60:
                    return True
    return False


def count_text_pixels_on_talon(px, W, H, bbox):
    """Talon kutusu ile OSD bolgelerinin kesisiminde gercek yazi pikseli say."""
    bx0, by0, bx1, by1 = bbox
    total = 0
    for (zx0, zy0, zx1, zy1) in OSD_ZONES:
        ix0 = max(bx0, zx0 - ZONE_MARGIN)
        iy0 = max(by0, zy0 - ZONE_MARGIN)
        ix1 = min(bx1, zx1 + ZONE_MARGIN)
        iy1 = min(by1, zy1 + ZONE_MARGIN)
        if ix0 > ix1 or iy0 > iy1:
            continue
        for x in range(int(ix0), int(ix1) + 1):
            for y in range(int(iy0), int(iy1) + 1):
                if 0 <= x < W and 0 <= y < H and is_text_pixel(px, W, H, x, y):
                    total += 1
                    if total >= TEXT_PIXEL_MIN:
                        return total
    return total


def talon_maybe_invisible(px, W, H, bbox):
    """RAPOR AMACLI sezgisel kontrol: talon kutusu icinde arka plandan ayrisan
    piksel var mi? Yoksa talon o karede gorunmuyor olabilir (engel arkasinda).
    KESIN degildir -> silmez, sadece rapora yazar."""
    bx0, by0, bx1, by1 = [int(v) for v in bbox]
    rx0, ry0 = max(0, bx0 - 30), max(0, by0 - 30)
    rx1, ry1 = min(W - 1, bx1 + 30), min(H - 1, by1 + 30)

    def lum(x, y):
        r, g, b = px[x, y][:3]
        return 0.299 * r + 0.587 * g + 0.114 * b

    ring = []
    for x in range(rx0, rx1 + 1, 2):
        for y in range(ry0, ry1 + 1, 2):
            if x < bx0 or x > bx1 or y < by0 or y > by1:
                ring.append(lum(x, y))
    if not ring:
        return False
    ring.sort()
    med = ring[len(ring) // 2]

    outliers = 0
    for x in range(max(0, bx0), min(W, bx1 + 1)):
        for y in range(max(0, by0), min(H, by1 + 1)):
            if abs(lum(x, y) - med) > 40:
                outliers += 1
                if outliers >= 12:
                    return False  # belirgin bir nesne var -> gorunuyor
    return True  # kutu ici arka plandan ayirt edilemiyor -> supheli


def check_pair(png_path, json_path):
    """Donus: (verdict, reason). verdict: 'OK' | 'DELETE' | 'SKIP', ek olarak
    supheli gorunmezlik icin ayrica bayrak dondurulur."""
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
    except Exception as e:
        return "DELETE", "JSON okunamiyor/bozuk (%s)" % e, False

    kp = meta.get("keypoints_2d")
    if not isinstance(kp, dict) or len(kp) == 0:
        return "DELETE", "hic noktalanmamis (keypoints_2d yok/bos)", False

    if set(kp.keys()) != EXPECTED_KEYPOINTS:
        return "DELETE", "6 keypoint tam degil: %s" % sorted(kp.keys()), False

    try:
        img = Image.open(png_path).convert("RGB")
    except Exception as e:
        return "DELETE", "PNG acilamiyor/bozuk (%s)" % e, False
    W, H = img.size

    for name, pt in kp.items():
        if not pt.get("on", False):
            return "DELETE", "nokta yok / projeksiyon disi: %s" % name, False
        x, y = pt.get("x"), pt.get("y")
        if x is None or y is None:
            return "DELETE", "koordinat eksik: %s" % name, False
        if x < 0 or x >= W or y < 0 or y >= H:
            return "DELETE", "nokta foto DISINDA: %s (x=%.0f, y=%.0f)" % (name, x, y), False

    px = img.load()

    xs = [pt["x"] for pt in kp.values()]
    ys = [pt["y"] for pt in kp.values()]
    bbox = (min(xs) - BBOX_MARGIN, min(ys) - BBOX_MARGIN,
            max(xs) + BBOX_MARGIN, max(ys) + BBOX_MARGIN)

    n_text = count_text_pixels_on_talon(px, W, H, bbox)
    if n_text >= TEXT_PIXEL_MIN:
        return "DELETE", "talon YAZININ ARKASINDA (%d yazi pikseli ustunde)" % n_text, False

    suspicious = talon_maybe_invisible(px, W, H, bbox)
    return "OK", "", suspicious


def main():
    dry_run = "--dry-run" in sys.argv
    if not os.path.isdir(DATASET_DIR):
        print("[HATA] dataset klasoru yok:", DATASET_DIR)
        return

    pngs = sorted(f for f in os.listdir(DATASET_DIR) if f.lower().endswith(".png"))
    now = time.time()

    deleted, kept, skipped = [], [], []
    suspicious_list = []

    for fname in pngs:
        stem = fname[:-4]
        png_path = os.path.join(DATASET_DIR, fname)
        json_path = os.path.join(DATASET_DIR, stem + ".json")

        # Oyun su an bu cifti yaziyor olabilir -> dokunma
        try:
            age = now - max(os.path.getmtime(png_path),
                            os.path.getmtime(json_path) if os.path.exists(json_path) else 0)
        except OSError:
            age = 0
        if age < IN_FLIGHT_SECONDS:
            skipped.append((stem, "cok yeni (su an yaziliyor olabilir)"))
            continue

        if not os.path.exists(json_path):
            skipped.append((stem, "JSON esi yok (cift degil)"))
            continue

        verdict, reason, suspicious = check_pair(png_path, json_path)

        if verdict == "DELETE":
            deleted.append((stem, reason))
            print(("[SILINECEK]" if dry_run else "[SILINDI]"), stem, "->", reason)
            if not dry_run:
                for p in (png_path, json_path,
                          os.path.join(ANNOTATED_DIR, fname)):
                    try:
                        if os.path.exists(p):
                            os.remove(p)
                    except OSError as e:
                        print("   [UYARI] silinemedi:", p, e)
        else:
            kept.append(stem)
            if suspicious:
                suspicious_list.append(stem)

    print()
    print("=" * 60)
    print("OZET %s" % ("(DRY-RUN: hicbir sey silinmedi)" if dry_run else "(KALICI silme yapildi)"))
    print("  Kontrol edilen cift : %d" % (len(deleted) + len(kept)))
    print("  Silinen             : %d" % len(deleted))
    print("  Kalan (temiz)       : %d" % len(kept))
    print("  Atlanan             : %d" % len(skipped))
    print("  SUPHELI (gorunmuyor olabilir, SILINMEDI): %d" % len(suspicious_list))
    if suspicious_list:
        print("    ->", ", ".join(suspicious_list[:20]) + (" ..." if len(suspicious_list) > 20 else ""))

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("Temizlik raporu - %s %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"),
                                               "(DRY-RUN)" if dry_run else "(KALICI)"))
        f.write("\n[SILINEN] (%d)\n" % len(deleted))
        for stem, reason in deleted:
            f.write("  %s -> %s\n" % (stem, reason))
        f.write("\n[ATLANAN] (%d)\n" % len(skipped))
        for stem, reason in skipped:
            f.write("  %s -> %s\n" % (stem, reason))
        f.write("\n[SUPHELI - talon gorunmuyor olabilir, SILINMEDI] (%d)\n" % len(suspicious_list))
        for stem in suspicious_list:
            f.write("  %s\n" % stem)
        f.write("\n[KALAN] (%d)\n" % len(kept))
    print("Rapor yazildi:", REPORT_FILE)


if __name__ == "__main__":
    main()

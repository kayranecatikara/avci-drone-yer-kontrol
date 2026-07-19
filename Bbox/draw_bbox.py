# -*- coding: utf-8 -*-
"""
Pose keypoint'lerinden Bounding Box üretme ve çizme
====================================================
- Modelden gelen 6 keypoint görüntüye ÇİZİLMEZ (nokta çizimi tamamen iptal edildi).
- Kutu, 6 noktanın (x, y) koordinatlarından min-x, min-y, max-x, max-y
  bulunarak dinamik olarak hesaplanır; yani her zaman noktaların TAMAMINI kapsar.
- Varsayılan olarak kutu, en uç noktalara TAM oturur (pay = 0). İstenirse
  --padding ile kenarlara pay eklenebilir; kutu her durumda görüntü sınırına
  kırpılır (resmin dışına asla taşmaz).
- Görüntü üzerine SADECE nihai bounding box çizilir.

Kullanım:
    python draw_bbox.py                    # klasördeki tüm talon_*.json çiftlerini işler
    python draw_bbox.py --stem talon_1242  # sadece tek bir kareyi işler
    python draw_bbox.py --padding 10       # kenarlara 10 px pay ekler (varsayılan: 0)

Çıktılar ./bbox_output klasörüne aynı dosya adıyla kaydedilir.
"""

import argparse
import json
import math
import sys
from pathlib import Path

import cv2

# Windows konsolu varsayılan olarak cp1252 olabilir; Türkçe karakterler için UTF-8
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ------------------------------- Ayarlar -------------------------------
DEFAULT_PADDING = 0         # kutu kenar payı (piksel); 0 = kutu uç noktalara tam oturur
BOX_COLOR = (0, 255, 0)     # kutu rengi (BGR formatında: yeşil)
BOX_THICKNESS = 2           # kutu çizgi kalınlığı (piksel)


def load_keypoints(json_path: Path) -> list[tuple[float, float]]:
    """JSON'daki 'keypoints_2d' alanından 6 noktanın (x, y) listesini döndürür.

    Not: 'on' alanı false olan (kare dışına taşmış) noktalar da bilinçli olarak
    dahil edilir; compute_bbox içindeki kırpma (clamp) adımı sayesinde kutu yine
    görüntü içinde kalır. Bu, kısmen kare dışına taşan hedefler için doğru
    davranıştır: kutu, hedefin görünen kısmını kare kenarına kadar kapsar.
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [(kp["x"], kp["y"]) for kp in data["keypoints_2d"].values()]


def compute_bbox(points, img_w, img_h, padding=DEFAULT_PADDING):
    """Noktaların tamamını kapsayan, padding'li ve görüntüye kırpılmış kutuyu
    (x_min, y_min, x_max, y_max) olarak döndürür; geçerli kutu yoksa None.

    Adımlar:
      1) Tüm x ve y değerlerinin min/max'ı alınır  -> en dar kapsayan kutu
      2) Varsa 'padding' her kenara eklenir        -> varsayılan 0: kutu uç
                                                      noktalara tam değer
      3) floor/ceil ile tam sayıya GENİŞLETİLİR    -> yuvarlama hiçbir noktayı
                                                      kutunun dışında bırakamaz
      4) Görüntü sınırlarına kırpılır (clamp)      -> kutu resimden taşmaz
    """
    if not points:
        return None

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]

    # 1-2-3) min/max + padding; floor/ceil ile kapsama garantisi
    x_min = math.floor(min(xs) - padding)
    y_min = math.floor(min(ys) - padding)
    x_max = math.ceil(max(xs) + padding)
    y_max = math.ceil(max(ys) + padding)

    # 4) Geçerli piksel aralığına kırp: x için [0, w-1], y için [0, h-1]
    x_min = max(0, x_min)
    y_min = max(0, y_min)
    x_max = min(img_w - 1, x_max)
    y_max = min(img_h - 1, y_max)

    # Noktaların tamamı görüntünün dışındaysa kutu dejenere olur -> çizilmez
    if x_min >= x_max or y_min >= y_max:
        return None

    return x_min, y_min, x_max, y_max


def draw_bbox(image, bbox):
    """Görüntü üzerine SADECE bounding box'ı çizer (nokta çizimi yoktur)."""
    x_min, y_min, x_max, y_max = bbox
    cv2.rectangle(image, (x_min, y_min), (x_max, y_max), BOX_COLOR, BOX_THICKNESS)
    return image


def process_pair(img_path: Path, json_path: Path, out_dir: Path, padding: int):
    """Tek bir görüntü + JSON çiftini işler: kutuyu hesaplar, çizer, kaydeder."""
    image = cv2.imread(str(img_path))
    if image is None:
        print(f"[HATA] Görüntü okunamadı: {img_path.name}")
        return

    img_h, img_w = image.shape[:2]
    points = load_keypoints(json_path)
    bbox = compute_bbox(points, img_w, img_h, padding)

    if bbox is None:
        print(f"[ATLA] {img_path.name}: noktalar kare dışında, geçerli kutu üretilemedi.")
        return

    draw_bbox(image, bbox)

    out_path = out_dir / img_path.name
    cv2.imwrite(str(out_path), image)

    x1, y1, x2, y2 = bbox
    print(f"[OK] {img_path.name}: bbox=({x1}, {y1}) -> ({x2}, {y2})  "
          f"boyut={x2 - x1}x{y2 - y1}px")


def main():
    parser = argparse.ArgumentParser(
        description="6 keypoint'ten bounding box hesaplar ve SADECE kutuyu çizer.")
    parser.add_argument("--dir", type=Path, default=Path(__file__).parent,
                        help="görüntü + JSON çiftlerinin bulunduğu klasör")
    parser.add_argument("--stem", type=str, default=None,
                        help="sadece tek bir kareyi işle (örn. talon_1242)")
    parser.add_argument("--padding", type=int, default=DEFAULT_PADDING,
                        help=f"kutu kenar payı, piksel (varsayılan: {DEFAULT_PADDING})")
    args = parser.parse_args()

    out_dir = args.dir / "bbox_output"
    out_dir.mkdir(exist_ok=True)

    # Tek dosya istenmişse onu, istenmemişse klasördeki tüm JSON'ları işle
    if args.stem:
        json_files = [args.dir / f"{args.stem}.json"]
    else:
        json_files = sorted(args.dir.glob("*.json"))

    for json_path in json_files:
        if not json_path.exists():
            print(f"[ATLA] {json_path.name}: JSON dosyası bulunamadı.")
            continue
        img_path = json_path.with_suffix(".png")
        if not img_path.exists():
            print(f"[ATLA] {json_path.name}: eşleşen .png bulunamadı.")
            continue
        process_pair(img_path, json_path, out_dir, args.padding)


if __name__ == "__main__":
    main()

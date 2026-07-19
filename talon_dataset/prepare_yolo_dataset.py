import os
import json
import shutil
import random
from PIL import Image

def calculate_bbox(keypoints, img_w, img_h):
    # Görünür olan noktaları seç (x != -1 ve y != -1)
    visible_pts = [(kp['x'], kp['y']) for kp in keypoints.values() if kp['x'] != -1 and kp['y'] != -1]
    
    if not visible_pts:
        # Görünür nokta yoksa varsayılan olarak merkezde küçük bir kutu oluştur
        return 0.5, 0.5, 0.1, 0.1

    xs = [pt[0] for pt in visible_pts]
    ys = [pt[1] for pt in visible_pts]

    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)

    if len(visible_pts) == 1 or (xmax - xmin) < 20.0 or (ymax - ymin) < 20.0:
        cx_temp = (xmin + xmax) / 2.0
        cy_temp = (ymin + ymax) / 2.0
        xmin = min(xmin, cx_temp - 10.0)
        xmax = max(xmax, cx_temp + 10.0)
        ymin = min(ymin, cy_temp - 10.0)
        ymax = max(ymax, cy_temp + 10.0)

    # Kutunun orijinal genişlik ve yüksekliği
    w_raw = xmax - xmin
    h_raw = ymax - ymin

    # %10 boşluk (padding)
    pad_x = w_raw * 0.10
    pad_y = h_raw * 0.10

    # Padding eklenmiş koordinatlar (resim sınırları dışına çıkmaması için clip işlemi)
    bbox_xmin = max(0.0, xmin - pad_x)
    bbox_xmax = min(float(img_w), xmax + pad_x)
    bbox_ymin = max(0.0, ymin - pad_y)
    bbox_ymax = min(float(img_h), ymax + pad_y)

    # Kutu genişliği, yüksekliği ve merkez koordinatları
    bbox_w = bbox_xmax - bbox_xmin
    bbox_h = bbox_ymax - bbox_ymin
    bbox_cx = bbox_xmin + (bbox_w / 2.0)
    bbox_cy = bbox_ymin + (bbox_h / 2.0)

    # Değerleri resim boyutuna göre normalize et (0 ile 1 arasına oranla)
    norm_cx = bbox_cx / img_w
    norm_cy = bbox_cy / img_h
    norm_w = bbox_w / img_w
    norm_h = bbox_h / img_h

    return norm_cx, norm_cy, norm_w, norm_h

def convert_dataset(dataset_dir, output_dir, train_ratio=0.8, seed=42):
    random.seed(seed)
    
    # Hedef klasör yollarını oluştur
    images_train_dir = os.path.join(output_dir, "images", "train")
    images_val_dir = os.path.join(output_dir, "images", "val")
    labels_train_dir = os.path.join(output_dir, "labels", "train")
    labels_val_dir = os.path.join(output_dir, "labels", "val")
    
    for folder in [images_train_dir, images_val_dir, labels_train_dir, labels_val_dir]:
        os.makedirs(folder, exist_ok=True)
        
    # JSON ve PNG eşleşmelerini bul
    all_files = os.listdir(dataset_dir)
    json_files = [f for f in all_files if f.endswith('.json')]
    
    pairs = []
    for j_file in json_files:
        base_name = os.path.splitext(j_file)[0]
        png_file = base_name + ".png"
        
        png_path = os.path.join(dataset_dir, png_file)
        json_path = os.path.join(dataset_dir, j_file)
        
        if os.path.exists(png_path):
            pairs.append((png_path, json_path, base_name))
        else:
            print(f"[WARN] No matching image found for: {j_file}")
            
    if not pairs:
        print("[ERROR] No JSON-PNG pairs found for conversion!")
        return

    print(f"Found {len(pairs)} valid data pairs.")
    
    # Veriyi karıştır ve Train/Val olarak ayır
    random.shuffle(pairs)
    split_idx = int(len(pairs) * train_ratio)
    train_pairs = pairs[:split_idx]
    val_pairs = pairs[split_idx:]
    
    print(f"Split ratio: {int(train_ratio*100)}% Train ({len(train_pairs)} pairs), {int((1-train_ratio)*100)}% Val ({len(val_pairs)} pairs)")
    
    # Keypoint sıralaması (YOLO formatı için)
    # KRITIK DUZELTME (2026-07-07): JSON'lardaki anahtarlar buyuk harfli
    # ("Nose"), eski kucuk harfli liste .get()'te hep None donduruyordu ->
    # TUM keypointler etikete "0.0 0.0 0" (gorunmez) yaziliyordu ve model
    # keypoint OGRENEMIYORDU (PnP mesafe testinde kanitlandi). Siralama ayni.
    keypoints_order = ["Nose", "Left_Wingtip", "Right_Wingtip", "Tail", "Left_Tail_Fin", "Right_Tail_Fin"]
    
    def process_pair(pair, dest_img_dir, dest_lbl_dir):
        png_path, json_path, base_name = pair
        
        # Resmi açıp boyutlarını öğren
        with Image.open(png_path) as img:
            img_w, img_h = img.size
            
        # JSON dosyasını Türkçe karakter hatası almamak için utf-8 ile oku
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        keypoints_2d = data.get("keypoints_2d", {})
        
        # Bounding Box hesapla
        cx_norm, cy_norm, w_norm, h_norm = calculate_bbox(keypoints_2d, img_w, img_h)
        
        # Keypoint'leri oranlayıp YOLO formatına getir
        kpt_parts = []
        for kp_name in keypoints_order:
            kp = keypoints_2d.get(kp_name)
            if kp is None or (kp['x'] == -1 and kp['y'] == -1):
                # Görünmeyen nokta
                kpt_parts.extend(["0.0", "0.0", "0"])
            else:
                # Görünür nokta: oranlanmış koordinatlar ve visibility=2
                norm_x = kp['x'] / img_w
                norm_y = kp['y'] / img_h
                kpt_parts.extend([f"{norm_x:.6f}", f"{norm_y:.6f}", "2"])
                
        # YOLO pose satır formatı: class_id cx cy w h kp1_x kp1_y kp1_v ...
        label_line = f"0 {cx_norm:.6f} {cy_norm:.6f} {w_norm:.6f} {h_norm:.6f} " + " ".join(kpt_parts)
        
        # Resmi kopyala
        shutil.copy2(png_path, os.path.join(dest_img_dir, base_name + ".png"))
        
        # Label dosyasını yaz (.txt)
        txt_path = os.path.join(dest_lbl_dir, base_name + ".txt")
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(label_line + "\n")
            
    # Train kümesini işle
    print("Copying and converting Train data...")
    for pair in train_pairs:
        process_pair(pair, images_train_dir, labels_train_dir)
        
    # Val kümesini işle
    print("Copying and converting Val data...")
    for pair in val_pairs:
        process_pair(pair, images_val_dir, labels_val_dir)
        
    # data.yaml dosyasını oluştur
    yaml_path = os.path.join(output_dir, "data.yaml")
    # Windows yollarında ters eğik çizgi sorununu engellemek için '/' kullanıyoruz
    formatted_output_dir = output_dir.replace('\\', '/')
    
    yaml_content = f"""path: {formatted_output_dir}
train: images/train
val: images/val

names:
  0: talon

kpt_shape: [6, 3]
"""
    with open(yaml_path, 'w', encoding='utf-8') as f:
        f.write(yaml_content)
        
    print(f"\n[SUCCESS] All operations completed!")
    print(f"Dataset root: {output_dir}")
    print(f"data.yaml file created at: {yaml_path}")

if __name__ == "__main__":
    # Girdi ve Çıktı klasörleri tanımları
    source_dataset = r"C:\Users\Zeylo\Desktop\talon_dataset\dataset"
    destination_dataset = r"C:\Users\Zeylo\Desktop\dataset1_yolo"
    
    convert_dataset(source_dataset, destination_dataset)

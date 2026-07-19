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

def get_non_conflicting_name(base_name, images_train_dir, images_val_dir):
    candidate = base_name
    # Eğer bu isimde görsel train veya val klasöründe varsa sonuna _new ekle
    while True:
        train_img = os.path.join(images_train_dir, candidate + ".png")
        val_img = os.path.join(images_val_dir, candidate + ".png")
        if os.path.exists(train_img) or os.path.exists(val_img):
            candidate += "_new"
        else:
            return candidate

def get_directory_file_count(folder_path):
    if not os.path.exists(folder_path):
        return 0
    return len([f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))])

def merge_datasets(new_dataset_dir, target_dir, train_ratio=0.8, seed=42):
    random.seed(seed)
    
    # Hedef klasörlerin yolları (Mevcut klasörler)
    images_train_dir = os.path.join(target_dir, "images", "train")
    images_val_dir = os.path.join(target_dir, "images", "val")
    labels_train_dir = os.path.join(target_dir, "labels", "train")
    labels_val_dir = os.path.join(target_dir, "labels", "val")
    
    # Klasörlerin var olduğundan emin ol (yoksa oluştur, silme işlemi yapma)
    for folder in [images_train_dir, images_val_dir, labels_train_dir, labels_val_dir]:
        os.makedirs(folder, exist_ok=True)
        
    # İşlem öncesi hedefteki dosya sayılarını al
    prev_train_imgs = get_directory_file_count(images_train_dir)
    prev_val_imgs = get_directory_file_count(images_val_dir)
    prev_train_lbls = get_directory_file_count(labels_train_dir)
    prev_val_lbls = get_directory_file_count(labels_val_dir)
    
    print("--- MERGE OPERATION STARTED ---")
    print(f"Existing files in {target_dir}:")
    print(f"  Train: {prev_train_imgs} images, {prev_train_lbls} labels")
    print(f"  Val  : {prev_val_imgs} images, {prev_val_lbls} labels")
    
    # Yeni veri klasöründeki dosyaları tara
    all_files = os.listdir(new_dataset_dir)
    json_files = [f for f in all_files if f.endswith('.json')]
    
    new_pairs = []
    for j_file in json_files:
        base_name = os.path.splitext(j_file)[0]
        png_file = base_name + ".png"
        
        png_path = os.path.join(new_dataset_dir, png_file)
        json_path = os.path.join(new_dataset_dir, j_file)
        
        if os.path.exists(png_path):
            new_pairs.append((png_path, json_path, base_name))
            
    if not new_pairs:
        print("[ERROR] No JSON-PNG pairs found in the new dataset directory!")
        return

    print(f"\nFound {len(new_pairs)} new valid data pairs in: {new_dataset_dir}")
    
    # Yeni verileri karıştır ve kendi içinde Train/Val olarak böl
    random.shuffle(new_pairs)
    split_idx = int(len(new_pairs) * train_ratio)
    train_pairs = new_pairs[:split_idx]
    val_pairs = new_pairs[split_idx:]
    
    print(f"Split ratio for new data: {int(train_ratio*100)}% Train ({len(train_pairs)} pairs), {int((1-train_ratio)*100)}% Val ({len(val_pairs)} pairs)")
    
    # Keypoint sırası
    keypoints_order = ["nose", "left_wingtip", "right_wingtip", "tail", "left_tail_fin", "right_tail_fin"]
    
    def process_and_copy_pair(pair, dest_img_dir, dest_lbl_dir):
        png_path, json_path, base_name = pair
        
        # Çakışma kontrolü yapıp güvenli bir isim al
        safe_base_name = get_non_conflicting_name(base_name, images_train_dir, images_val_dir)
        
        # Görsel boyutunu al
        with Image.open(png_path) as img:
            img_w, img_h = img.size
            
        # JSON dosyasını utf-8 ile oku
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        keypoints_2d = data.get("keypoints_2d", {})
        
        # Bounding Box hesapla
        cx_norm, cy_norm, w_norm, h_norm = calculate_bbox(keypoints_2d, img_w, img_h)
        
        # Keypoint'leri YOLO Pose biçimine getir
        kpt_parts = []
        for kp_name in keypoints_order:
            kp = keypoints_2d.get(kp_name)
            if kp is None or (kp['x'] == -1 and kp['y'] == -1):
                kpt_parts.extend(["0.0", "0.0", "0"])
            else:
                norm_x = kp['x'] / img_w
                norm_y = kp['y'] / img_h
                kpt_parts.extend([f"{norm_x:.6f}", f"{norm_y:.6f}", "2"])
                
        label_line = f"0 {cx_norm:.6f} {cy_norm:.6f} {w_norm:.6f} {h_norm:.6f} " + " ".join(kpt_parts)
        
        # Resim dosyasını kopyala
        shutil.copy2(png_path, os.path.join(dest_img_dir, safe_base_name + ".png"))
        
        # Label etiket dosyasını yaz
        txt_path = os.path.join(dest_lbl_dir, safe_base_name + ".txt")
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(label_line + "\n")
            
    # Train kümesini ekle
    print("Processing and adding Train data...")
    for pair in train_pairs:
        process_and_copy_pair(pair, images_train_dir, labels_train_dir)
        
    # Val kümesini ekle
    print("Processing and adding Val data...")
    for pair in val_pairs:
        process_and_copy_pair(pair, images_val_dir, labels_val_dir)
        
    # data.yaml dosyasını güncelle
    yaml_path = os.path.join(target_dir, "data.yaml")
    formatted_target_dir = target_dir.replace('\\', '/')
    yaml_content = f"""path: {formatted_target_dir}
train: images/train
val: images/val

names:
  0: talon

kpt_shape: [6, 3]
"""
    with open(yaml_path, 'w', encoding='utf-8') as f:
        f.write(yaml_content)
        
    # İşlem sonrası hedefteki dosya sayılarını al
    after_train_imgs = get_directory_file_count(images_train_dir)
    after_val_imgs = get_directory_file_count(images_val_dir)
    after_train_lbls = get_directory_file_count(labels_train_dir)
    after_val_lbls = get_directory_file_count(labels_val_dir)
    
    print("\n--- MERGE OPERATION COMPLETED ---")
    print(f"Initial files count: {prev_train_imgs + prev_val_imgs} images, {prev_train_lbls + prev_val_lbls} labels")
    print(f"Added new files count: {len(new_pairs)} pairs")
    print(f"Final total files in {target_dir}:")
    print(f"  Train: {after_train_imgs} images, {after_train_lbls} labels (Added: {after_train_imgs - prev_train_imgs})")
    print(f"  Val  : {after_val_imgs} images, {after_val_lbls} labels (Added: {after_val_imgs - prev_val_imgs})")
    print(f"data.yaml updated at: {yaml_path}")

if __name__ == "__main__":
    new_dataset = r"C:\Users\Zeylo\Desktop\talon_dataset\dataset"
    target_dataset = r"C:\Users\Zeylo\Desktop\dataset1_yolo"
    
    merge_datasets(new_dataset, target_dataset)

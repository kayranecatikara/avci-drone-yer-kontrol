import os
import glob
import json
import random
from PIL import Image, ImageDraw

def generate_yolo_labels(input_dir, output_dir=None, padding=10, preview_count=40):
    print(f"[INFO] Scanning directory for JSON and PNG pairs: {input_dir}")
    
    if output_dir is None:
        output_dir = os.path.join(input_dir, "yolo_labels")
        
    preview_dir = os.path.join(output_dir, "bbox_preview")
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(preview_dir, exist_ok=True)
    
    print(f"[INFO] Text files will be saved to: {output_dir}")
    print(f"[INFO] Bbox preview images will be saved to: {preview_dir}")
    
    json_files = glob.glob(os.path.join(input_dir, "*.json"))
    
    success_count = 0
    processed_data = [] # To store valid pairs for random preview
    
    for json_path in json_files:
        basename = os.path.basename(json_path)
        png_path = json_path.replace(".json", ".png")
        txt_path = os.path.join(output_dir, basename.replace(".json", ".txt"))
        
        if not os.path.exists(png_path):
            continue
            
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Get keypoints
            keypoints = data.get("keypoints_2d", {})
            xs = []
            ys = []
            
            for kp_name, kp_data in keypoints.items():
                if kp_data.get("on", False):
                    xs.append(kp_data["x"])
                    ys.append(kp_data["y"])
                    
            if not xs or not ys:
                continue # No visible points
                
            # Calculate Bounding Box
            xmin = min(xs) - padding
            ymin = min(ys) - padding
            xmax = max(xs) + padding
            ymax = max(ys) + padding
            
            # Open image to get dimensions
            with Image.open(png_path) as img:
                img_width, img_height = img.size
                
            # Clamp to image boundaries
            xmin = max(0, xmin)
            ymin = max(0, ymin)
            xmax = min(img_width, xmax)
            ymax = min(img_height, ymax)
            
            # YOLO Format: class x_center y_center width height (normalized)
            box_width = xmax - xmin
            box_height = ymax - ymin
            x_center = xmin + (box_width / 2.0)
            y_center = ymin + (box_height / 2.0)
            
            norm_x_center = x_center / img_width
            norm_y_center = y_center / img_height
            norm_width = box_width / img_width
            norm_height = box_height / img_height
            
            # Write to TXT file (Class ID is 0 for Talon)
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(f"0 {norm_x_center:.6f} {norm_y_center:.6f} {norm_width:.6f} {norm_height:.6f}\n")
                
            processed_data.append({
                "png_path": png_path,
                "bbox": [xmin, ymin, xmax, ymax],
                "basename": basename.replace(".json", ".png")
            })
            
            success_count += 1
            
        except Exception as e:
            print(f"[ERROR] Failed processing {basename}: {e}")
            
    print(f"[SUCCESS] Generated {success_count} YOLO format .txt labels!")
    
    # RASTGELE 40 FOTO CIZIMI
    print(f"[INFO] Rastgele {preview_count} fotograf secilip uzerine BBOX ciziliyor...")
    preview_samples = random.sample(processed_data, min(preview_count, len(processed_data)))
    
    for item in preview_samples:
        try:
            with Image.open(item["png_path"]) as img:
                draw = ImageDraw.Draw(img)
                xmin, ymin, xmax, ymax = item["bbox"]
                
                # Bbox cizimi (Kalin yesil kutu)
                draw.rectangle([xmin, ymin, xmax, ymax], outline="green", width=3)
                
                save_path = os.path.join(preview_dir, item["basename"])
                img.save(save_path)
        except Exception as e:
            print(f"[ERROR] Cizim hatasi {item['basename']}: {e}")
            
    print(f"[SUCCESS] {len(preview_samples)} adet kontrol gorseli '{preview_dir}' klasorune kaydedildi. Gidip inceleyebilirsin!")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    default_input = os.path.join(current_dir, "dataset")
    
    in_dir = input(f"Input Klasoru (JSON ve PNG'lerin oldugu yer) [{default_input}]: ").strip()
    if not in_dir:
        in_dir = default_input
        
    out_dir = input(f"Output Klasoru (TXT'lerin kaydedilecegi yer) [Bos birakirsan '{in_dir}/yolo_labels' olur]: ").strip()
    if not out_dir:
        out_dir = None
        
    if os.path.exists(in_dir):
        generate_yolo_labels(in_dir, out_dir, preview_count=40)
    else:
        print(f"[ERROR] Klasor bulunamadi: {in_dir}")

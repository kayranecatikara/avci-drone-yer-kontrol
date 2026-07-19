import os
import random
from PIL import Image, ImageDraw

def draw_previews():
    dataset_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dataset_auto_bbox")
    images_dir = os.path.join(dataset_dir, "images")
    labels_dir = os.path.join(dataset_dir, "labels")
    preview_dir = os.path.join(dataset_dir, "previews")
    
    if not os.path.exists(images_dir):
        print("Images folder not found!")
        return

    os.makedirs(preview_dir, exist_ok=True)
    
    # Pick 10 random images to preview
    all_images = [f for f in os.listdir(images_dir) if f.endswith(".png")]
    if len(all_images) > 10:
        sample_images = random.sample(all_images, 10)
    else:
        sample_images = all_images
        
    for img_name in sample_images:
        base_name = os.path.splitext(img_name)[0]
        img_path = os.path.join(images_dir, img_name)
        txt_path = os.path.join(labels_dir, base_name + ".txt")
        
        if not os.path.exists(txt_path):
            continue
            
        img = Image.open(img_path).convert("RGB")
        draw = ImageDraw.Draw(img)
        w, h = img.size
        
        with open(txt_path, "r") as f:
            lines = f.readlines()
            
        for line in lines:
            parts = line.strip().split()
            if len(parts) >= 5:
                # YOLO format: class cx cy bw bh
                cx, cy, bw, bh = map(float, parts[1:5])
                
                # De-normalize
                cx_px = cx * w
                cy_px = cy * h
                bw_px = bw * w
                bh_px = bh * h
                
                # Get corners
                x1 = cx_px - (bw_px / 2)
                y1 = cy_px - (bh_px / 2)
                x2 = cx_px + (bw_px / 2)
                y2 = cy_px + (bh_px / 2)
                
                # Draw box
                draw.rectangle([x1, y1, x2, y2], outline="red", width=3)
                
        preview_path = os.path.join(preview_dir, img_name)
        img.save(preview_path)
        print(f"Saved preview: {preview_path}")

    # Open the folder for the user (Windows specific)
    os.startfile(preview_dir)

if __name__ == "__main__":
    draw_previews()

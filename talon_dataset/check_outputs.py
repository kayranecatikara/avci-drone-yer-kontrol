import os
import json
from PIL import Image

workspace_dir = r"c:\Users\Zeylo\Desktop\talon_dataset"
annotated_dir = os.path.join(workspace_dir, "dataset_annotated")

for frame_idx in [5, 10, 15]:
    filename = f"talon_{frame_idx:04d}.png"
    json_filename = f"talon_{frame_idx:04d}.json"
    
    img_path = os.path.join(annotated_dir, filename)
    json_path = os.path.join(workspace_dir, "dataset", json_filename)
    
    if os.path.exists(img_path) and os.path.exists(json_path):
        with open(json_path, "r") as jf:
            data = json.load(jf)
            
        kps = data.get("keypoints_2d")
        if kps and "tail" in kps:
            tx = int(round(kps["tail"]["x"]))
            ty = int(round(kps["tail"]["y"]))
            
            img = Image.open(img_path)
            crop_box = (tx - 75, ty - 75, tx + 75, ty + 75)
            crop_img = img.crop(crop_box)
            
            out_path = os.path.join(workspace_dir, f"check_tail_f{frame_idx}.png")
            crop_img.save(out_path)
            print(f"Saved tail crop for frame {frame_idx} to {out_path}")

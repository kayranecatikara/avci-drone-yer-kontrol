import os
import cv2
import numpy as np
import json

conv_dir = r"C:\Users\Zeylo\.gemini\antigravity\brain\36eff956-7e9e-4245-954f-3ac1eb798a93"
dataset_dir = r"c:\Users\Zeylo\Desktop\talon_dataset\dataset"

user_images = [
    ("media__1780694886793.png", "Image 1 (Sky View)"),
    ("media__1780694886811.png", "Image 2 (Landscape View)")
]

for filename, desc in user_images:
    path = os.path.join(conv_dir, filename)
    if not os.path.exists(path):
        print(f"File not found: {filename}")
        continue
    user_img = cv2.imread(path)
    h_u, w_u, c_u = user_img.shape
    user_gray = cv2.cvtColor(user_img, cv2.COLOR_BGR2GRAY)
    
    print(f"\nMatching {desc} (shape={user_img.shape}):")
    matches = []
    
    for df in sorted(os.listdir(dataset_dir)):
        if not df.endswith(".png"):
            continue
        json_path = os.path.join(dataset_dir, df.replace(".png", ".json"))
        if not os.path.exists(json_path):
            continue
            
        with open(json_path, "r") as f:
            data = json.load(f)
            
        kps = data.get("keypoints_2d")
        if not kps:
            continue
            
        # Get bounding box of keypoints in the original 1920x1080 image
        xs = [kp["x"] for kp in kps.values()]
        ys = [kp["y"] for kp in kps.values()]
        
        min_x, max_x = int(min(xs)), int(max(xs))
        min_y, max_y = int(min(ys)), int(max(ys))
        
        # Expand box by 100 pixels
        min_x = max(0, min_x - 100)
        max_x = min(1920, max_x + 100)
        min_y = max(0, min_y - 100)
        max_y = min(1080, max_y + 100)
        
        img_path = os.path.join(dataset_dir, df)
        img = cv2.imread(img_path)
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Crop the region around the drone
        drone_crop = img_gray[min_y:max_y, min_x:max_x]
        
        # Template match the user crop inside the drone crop region
        if drone_crop.shape[0] >= user_gray.shape[0] and drone_crop.shape[1] >= user_gray.shape[1]:
            res = cv2.matchTemplate(drone_crop, user_gray, cv2.TM_SQDIFF_NORMED)
            min_v, max_v, min_loc, max_loc = cv2.minMaxLoc(res)
            # Map location back to original image
            orig_x = min_x + min_loc[0]
            orig_y = min_y + min_loc[1]
            matches.append((df, min_v, (orig_x, orig_y)))
            
    # Sort matches
    matches.sort(key=lambda x: x[1])
    for df, val, loc in matches[:3]:
        print(f" - {df}: SQDIFF={val:.6f} at original location {loc}")

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
        continue
    user_img = cv2.imread(path)
    user_gray = cv2.cvtColor(user_img, cv2.COLOR_BGR2GRAY)
    
    print(f"\nMatch scores for {desc}:")
    for i in range(1, 6):
        df = f"talon_{i:04d}.png"
        df_path = os.path.join(dataset_dir, df)
        if not os.path.exists(df_path):
            continue
        df_img = cv2.imread(df_path)
        df_gray = cv2.cvtColor(df_img, cv2.COLOR_BGR2GRAY)
        
        # Crop the middle 600x600 region where the drone usually is
        h, w = df_gray.shape
        drone_crop = df_gray[h//2-300:h//2+300, w//2-300:w//2+300]
        
        res = cv2.matchTemplate(drone_crop, user_gray, cv2.TM_SQDIFF_NORMED)
        min_v, max_v, min_loc, max_loc = cv2.minMaxLoc(res)
        
        print(f" - {df}: SQDIFF = {min_v:.6f} at location {min_loc}")

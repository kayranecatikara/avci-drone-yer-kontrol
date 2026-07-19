import os
import cv2
import numpy as np

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
    
    print(f"\n--- Matching {desc} with scaling ---")
    best_df = None
    best_scale = None
    best_loc = None
    min_val = float('inf')
    
    # We test scales from 0.4 to 1.5
    for scale in np.linspace(0.4, 1.5, 23):
        w_scaled = int(user_gray.shape[1] * scale)
        h_scaled = int(user_gray.shape[0] * scale)
        if w_scaled < 50 or h_scaled < 50 or w_scaled > 1200 or h_scaled > 1000:
            continue
            
        scaled_user = cv2.resize(user_gray, (w_scaled, h_scaled))
        
        for df in sorted(os.listdir(dataset_dir)):
            if not df.endswith(".png"):
                continue
            df_path = os.path.join(dataset_dir, df)
            df_img = cv2.imread(df_path)
            df_gray = cv2.cvtColor(df_img, cv2.COLOR_BGR2GRAY)
            
            if df_gray.shape[0] >= scaled_user.shape[0] and df_gray.shape[1] >= scaled_user.shape[1]:
                res = cv2.matchTemplate(df_gray, scaled_user, cv2.TM_SQDIFF_NORMED)
                min_v, max_v, min_loc, max_loc = cv2.minMaxLoc(res)
                
                # We want to match the drone, so we filter out matches on pure sky/terrain
                # A good match on the drone will be very distinct.
                if min_v < min_val:
                    min_val = min_v
                    best_df = df
                    best_scale = scale
                    best_loc = min_loc
                    
    # Map back the top-left coordinate of the scaled user image
    # user_x_in_original = best_loc[0]
    # user_y_in_original = best_loc[1]
    # Since scaled_user = user * scale, a pixel at (x, y) in user corresponds to (x * scale, y * scale) in scaled_user.
    # So in the original image, it is at: best_loc[0] + x * scale, best_loc[1] + y * scale.
    print(f"Best Match: {best_df} | Scale={best_scale:.3f} | Location={best_loc} | SQDIFF={min_val:.6f}")

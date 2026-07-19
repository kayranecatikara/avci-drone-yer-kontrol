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
    img = cv2.imread(path)
    # Convert to grayscale
    gray_crop = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h_c, w_c = gray_crop.shape
    
    # We will search for a matching template. To avoid annotations matching issues, we can match on key parts.
    # Actually, we can run template matching on all 20 frames.
    best_df = None
    best_loc = None
    min_val = float('inf')
    
    for df in sorted(os.listdir(dataset_dir)):
        if not df.endswith(".png"):
            continue
        df_path = os.path.join(dataset_dir, df)
        df_img = cv2.imread(df_path)
        df_gray = cv2.cvtColor(df_img, cv2.COLOR_BGR2GRAY)
        
        # Template matching
        res = cv2.matchTemplate(df_gray, gray_crop, cv2.TM_SQDIFF_NORMED)
        min_v, max_v, min_loc, max_loc = cv2.minMaxLoc(res)
        
        if min_v < min_val:
            min_val = min_v
            best_df = df
            best_loc = min_loc
            
    print(f"\n{desc}: Best match is {best_df} at {best_loc} with normalized SQDIFF={min_val:.6f}")

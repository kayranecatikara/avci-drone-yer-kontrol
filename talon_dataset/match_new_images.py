import os
import cv2
import numpy as np

workspace_dir = r"c:\Users\Zeylo\Desktop\talon_dataset"
dataset_dir = os.path.join(workspace_dir, "dataset")
media_dir = r"C:\Users\Zeylo\.gemini\antigravity\brain\36eff956-7e9e-4245-954f-3ac1eb798a93\.tempmediaStorage"

user_images = [
    "media_36eff956-7e9e-4245-954f-3ac1eb798a93_1780695142379.png",
    "media_36eff956-7e9e-4245-954f-3ac1eb798a93_1780694994065.png"
]

for filename in user_images:
    user_img_path = os.path.join(media_dir, filename)
    if not os.path.exists(user_img_path):
        print(f"File not found: {filename}")
        continue
        
    user_img = cv2.imread(user_img_path)
    h_u, w_u, c_u = user_img.shape
    print(f"\nMatching {filename} (shape={user_img.shape})...")
    
    # We will search all PNG files in dataset
    best_match = None
    min_val = float('inf')
    
    user_gray = cv2.cvtColor(user_img, cv2.COLOR_BGR2GRAY)
    
    for df in sorted(os.listdir(dataset_dir)):
        if not df.endswith(".png"):
            continue
        img_path = os.path.join(dataset_dir, df)
        img = cv2.imread(img_path)
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # If user image is exactly 1920x1080 (full size)
        if (h_u, w_u) == (1080, 1920):
            # Direct comparison (SSD) ignoring annotations or with downscaling
            # Resize both to 480x270 for quick structural check
            img_small = cv2.resize(img_gray, (480, 270))
            user_small = cv2.resize(user_gray, (480, 270))
            diff = np.mean((img_small - user_small) ** 2)
            if diff < min_val:
                min_val = diff
                best_match = (df, diff, (0, 0))
        else:
            # Template match
            if img_gray.shape[0] >= user_gray.shape[0] and img_gray.shape[1] >= user_gray.shape[1]:
                res = cv2.matchTemplate(img_gray, user_gray, cv2.TM_SQDIFF_NORMED)
                min_v, max_v, min_loc, max_loc = cv2.minMaxLoc(res)
                if min_v < min_val:
                    min_val = min_v
                    best_match = (df, min_v, min_loc)
                    
    if best_match:
        print(f"Best Match for {filename} is: {best_match[0]} at location {best_match[2]} with value {best_match[1]:.6f}")
    else:
        print(f"No match found for {filename}")

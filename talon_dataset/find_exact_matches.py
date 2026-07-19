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
    print(f"\nFinding exact match for {filename} (shape={user_img.shape}):")
    
    # We will search all PNG files in dataset
    matches = []
    
    for df in sorted(os.listdir(dataset_dir)):
        if not df.endswith(".png"):
            continue
        img_path = os.path.join(dataset_dir, df)
        img = cv2.imread(img_path)
        
        if (h_u, w_u) == (1080, 1920):
            # Full size comparison
            diff = np.mean((user_img.astype(float) - img.astype(float)) ** 2)
            matches.append((df, diff))
        else:
            # We need to find where the cropped user image fits in the original image
            # We use template matching with TM_SQDIFF to find the best match and the minimum SSD
            res = cv2.matchTemplate(img, user_img, cv2.TM_SQDIFF)
            min_v, max_v, min_loc, max_loc = cv2.minMaxLoc(res)
            # Normalize the SSD by size to get average pixel difference squared
            avg_diff = min_v / (h_u * w_u * c_u)
            matches.append((df, avg_diff, min_loc))
            
    # Sort matches by difference
    if (h_u, w_u) == (1080, 1920):
        matches.sort(key=lambda x: x[1])
        for df, diff in matches[:3]:
            print(f" - {df}: MSE = {diff:.4f}")
    else:
        matches.sort(key=lambda x: x[1])
        for df, diff, loc in matches[:3]:
            print(f" - {df}: Mean SQDIFF = {diff:.4f} at location {loc}")

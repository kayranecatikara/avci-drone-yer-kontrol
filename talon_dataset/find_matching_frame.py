import os
import cv2
import numpy as np

workspace_dir = r"c:\Users\Zeylo\Desktop\talon_dataset"
dataset_dir = os.path.join(workspace_dir, "dataset")
user_img_path = r"C:\Users\Zeylo\.gemini\antigravity\brain\36eff956-7e9e-4245-954f-3ac1eb798a93\media__1780606020349.png"

user_img = cv2.imread(user_img_path)
h_u, w_u, c_u = user_img.shape

# Let's search all PNG files in dataset
best_match = None
min_val = float('inf')

for filename in sorted(os.listdir(dataset_dir)):
    if not filename.endswith(".png"):
        continue
    img_path = os.path.join(dataset_dir, filename)
    img = cv2.imread(img_path)
    
    # Template match user_img inside the original image
    # Note: user_img contains colored dots, so we should convert both to grayscale or match on channels
    # To ignore the colored dots, we can use a structural similarity or match on the sky/unannotated parts, 
    # or just match the grayscale of the drone.
    # Actually, we can just search for the frame that has similar camera and drone telemetry
    # or we can check which frame's projected points with current coordinates match the drawn dots.
    # The drawn dots on user_img are:
    # Blue: (approx 55, 190) in user_img
    # Pink: (approx 205, 30)
    # Red: (approx 135, 328)
    # Orange: (approx 260, 205)
    # Yellow: (approx 270, 220)
    # Green: (approx 290, 150)
    
    # Let's do a template match using normalized cross-correlation on grayscale
    res = cv2.matchTemplate(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), cv2.cvtColor(user_img, cv2.COLOR_BGR2GRAY), cv2.TM_SQDIFF_NORMED)
    min_v, max_v, min_loc, max_loc = cv2.minMaxLoc(res)
    
    print(f"{filename}: min_val={min_v:.4f} at {min_loc}")
    if min_v < min_val:
        min_val = min_v
        best_match = (filename, min_loc)

print(f"\nBest match: {best_match[0]} at location {best_match[1]} with SQDIFF={min_val:.6f}")
# Let's save a crop of the best matching original image at the same location to verify
best_img = cv2.imread(os.path.join(dataset_dir, best_match[0]))
crop = best_img[best_match[1][1]:best_match[1][1]+h_u, best_match[1][0]:best_match[1][0]+w_u]
cv2.imwrite(os.path.join(workspace_dir, "matched_crop.png"), crop)
print("Saved matched_crop.png")

import cv2
import numpy as np
import os

workspace_dir = r"c:\Users\Zeylo\Desktop\talon_dataset"
dataset_dir = os.path.join(workspace_dir, "dataset")

# Let's crop around the tail for talon_0003.png (around x=900-1100, y=400-600)
img_path = os.path.join(dataset_dir, "talon_0003.png")
img = cv2.imread(img_path)
h, w, c = img.shape
print(f"Loaded image size: {w}x{h}")

crop = img[400:600, 900:1100].copy()
hc, wc, cc = crop.shape

# Draw a grid of 10 pixels
for x in range(0, wc, 10):
    cv2.line(crop, (x, 0), (x, hc), (180, 180, 180), 1)
    if x % 50 == 0:
        cv2.putText(crop, str(900 + x), (x, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 255), 1)

for y in range(0, hc, 10):
    cv2.line(crop, (0, y), (wc, y), (180, 180, 180), 1)
    if y % 50 == 0:
        cv2.putText(crop, str(400 + y), (5, y + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 255), 1)

out_path = r"c:\Users\Zeylo\Desktop\talon_dataset\crop_f3_grid.png"
cv2.imwrite(out_path, crop)
print(f"Saved grid crop to {out_path}")

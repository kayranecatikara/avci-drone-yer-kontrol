import cv2
import numpy as np

user_img_path = r"C:\Users\Zeylo\.gemini\antigravity\brain\36eff956-7e9e-4245-954f-3ac1eb798a93\media__1780606020349.png"
img = cv2.imread(user_img_path)
h, w, c = img.shape
print(f"Loaded image size: {w}x{h}")

# We care about the tail region: x around 450 to 650, y around 200 to 500
crop = img[200:500, 450:650].copy()
hc, wc, cc = crop.shape

# Draw a grid of 10 pixels
for x in range(0, wc, 10):
    cv2.line(crop, (x, 0), (x, hc), (180, 180, 180), 1)
    if x % 50 == 0:
        cv2.putText(crop, str(450 + x), (x, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 255), 1)

for y in range(0, hc, 10):
    cv2.line(crop, (0, y), (wc, y), (180, 180, 180), 1)
    if y % 50 == 0:
        cv2.putText(crop, str(200 + y), (5, y + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 255), 1)

out_path = r"c:\Users\Zeylo\Desktop\talon_dataset\crop_tail_grid.png"
cv2.imwrite(out_path, crop)
print(f"Saved grid crop to {out_path}")

import os
import cv2
import numpy as np

media_dir = r"C:\Users\Zeylo\.gemini\antigravity\brain\36eff956-7e9e-4245-954f-3ac1eb798a93\.tempmediaStorage"
img_name = "media_36eff956-7e9e-4245-954f-3ac1eb798a93_1780695142379.png"
path = os.path.join(media_dir, img_name)

if os.path.exists(path):
    img = cv2.imread(path)
    # Check pixels where Red channel is high (e.g. > 150) and see G/B channels
    b, g, r = img[:, :, 0], img[:, :, 1], img[:, :, 2]
    
    # Let's print some pixels that are reddish
    mask = (r > 150) & (r > b.astype(float) + 50) & (r > g.astype(float) + 50)
    y, x = np.where(mask)
    print(f"Detected {len(x)} reddish pixels.")
    if len(x) > 0:
        print("Sample RGB values of reddish pixels (OpenCV BGR):")
        for i in range(min(10, len(x))):
            px = img[y[i], x[i]]
            print(f"Pixel at x={x[i]}, y={y[i]}: BGR = {px}")
else:
    print("Image not found.")

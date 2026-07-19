import os
import cv2
import numpy as np

media_dir = r"C:\Users\Zeylo\.gemini\antigravity\brain\36eff956-7e9e-4245-954f-3ac1eb798a93\.tempmediaStorage"
img_name = "media_36eff956-7e9e-4245-954f-3ac1eb798a93_1780695142379.png"
path = os.path.join(media_dir, img_name)

if os.path.exists(path):
    img = cv2.imread(path)
    b, g, r = img[:, :, 0], img[:, :, 1], img[:, :, 2]
    
    # We want red to be dominant: R > G + 50 and R > B + 50 and R > 150
    mask = (r > 150) & (r.astype(float) - g.astype(float) > 50) & (r.astype(float) - b.astype(float) > 50)
    y, x = np.where(mask)
    print(f"Detected {len(x)} dominant red pixels.")
    
    # Let's count how many pixels fall in various BGR ranges to find the scribble color
    from collections import Counter
    colors = []
    for i in range(len(x)):
        px = img[y[i], x[i]]
        colors.append(tuple(px))
        
    most_common = Counter(colors).most_common(10)
    print("Most common BGR values among dominant red pixels:")
    for col, count in most_common:
        print(f" - BGR = {col} : count={count}")
else:
    print("Image not found.")

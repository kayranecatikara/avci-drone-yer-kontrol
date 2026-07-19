import os
import cv2
import numpy as np

media_dir = r"C:\Users\Zeylo\.gemini\antigravity\brain\36eff956-7e9e-4245-954f-3ac1eb798a93\.tempmediaStorage"

if not os.path.exists(media_dir):
    print("Directory does not exist.")
    exit()

# The standard keypoint BGR colors in OpenCV (BGR order)
std_colors = [
    (250, 100, 30),  # blue
    (30, 30, 255),   # red (std keypoint red)
    (200, 100, 255), # pink
    (0, 120, 255),  # orange
    (0, 215, 255),  # yellow
    (80, 200, 0)     # green
]

# We will scan all files
matching_files = []

for f in os.listdir(media_dir):
    if not f.endswith(".png"):
        continue
    path = os.path.join(media_dir, f)
    img = cv2.imread(path)
    if img is None:
        continue
        
    b, g, r = img[:, :, 0], img[:, :, 1], img[:, :, 2]
    
    # Scribble red: R > 150, G < 100, B < 100 (or generally Red-dominant)
    # Let's filter out standard keypoint colors to avoid false positives
    mask = (r > 180) & (g < 120) & (b < 120)
    
    # Exclude standard colors by removing pixels that match std_colors exactly or very closely
    for sc in std_colors:
        color_match = (abs(b.astype(float) - sc[0]) < 10) & (abs(g.astype(float) - sc[1]) < 10) & (abs(r.astype(float) - sc[2]) < 10)
        mask = mask & ~color_match
        
    y, x = np.where(mask)
    if len(x) > 30: # at least 30 pixels of custom red scribbles
        mtime = os.path.getmtime(path)
        matching_files.append((f, len(x), mtime))

matching_files.sort(key=lambda x: x[2], reverse=True)
print(f"Found {len(matching_files)} files with custom red scribbles:")
for f, count, mtime in matching_files:
    import time
    time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mtime))
    print(f" - {f}: red_pixels={count}, time={time_str}")

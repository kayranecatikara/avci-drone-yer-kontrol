import json
import cv2
import sys
import numpy as np

img_path = r'C:\Users\Zeylo\Desktop\talon_dataset\dataset\talon_1585.png'
json_path = r'C:\Users\Zeylo\Desktop\talon_dataset\dataset\talon_1585.json'
out_path = r'C:\Users\Zeylo\.gemini\antigravity\brain\36eff956-7e9e-4245-954f-3ac1eb798a93\.tempmediaStorage\media_36eff956-7e9e-4245-954f-3ac1eb798a93_test1585.png'

with open(json_path, 'r') as f:
    data = json.load(f)

img = cv2.imread(img_path)
if img is None:
    print(f"Failed to load image: {img_path}")
    sys.exit(1)

kps = data.get('keypoints_2d', {})
print(f"Found {len(kps)} keypoints")

for name, coords in kps.items():
    if coords is None:
        continue
    if not isinstance(coords, dict):
        continue
    x, y = int(coords['x']), int(coords['y'])
    cv2.circle(img, (x, y), 5, (0, 0, 255), -1)
    cv2.putText(img, name, (x + 10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

cv2.imwrite(out_path, img)
print(f"Saved to {out_path}")

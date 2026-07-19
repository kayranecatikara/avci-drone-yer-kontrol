import json
import cv2
import sys
import glob
import os

dataset_dir = r'C:\Users\Zeylo\Desktop\talon_dataset\dataset'
out_dir = r'C:\Users\Zeylo\.gemini\antigravity\brain\36eff956-7e9e-4245-954f-3ac1eb798a93\.tempmediaStorage'

json_files = glob.glob(os.path.join(dataset_dir, '*.json'))
json_files.sort(key=os.path.getmtime, reverse=True)
last_3_jsons = json_files[:3]

for json_path in last_3_jsons:
    img_path = json_path.replace('.json', '.png')
    base_name = os.path.basename(img_path)
    out_path = os.path.join(out_dir, f'media_36eff956-7e9e-4245-954f-3ac1eb798a93_test_{base_name}')

    with open(json_path, 'r') as f:
        data = json.load(f)

    img = cv2.imread(img_path)
    if img is None:
        print(f"Failed to load image: {img_path}")
        continue

    kps = data.get('keypoints_2d', {})
    
    for name, coords in kps.items():
        if coords is None or not isinstance(coords, dict):
            continue
        x, y = int(coords['x']), int(coords['y'])
        # Smaller circle (radius 2) and smaller text (scale 0.3)
        cv2.circle(img, (x, y), 2, (0, 0, 255), -1)
        cv2.putText(img, name, (x + 5, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

    cv2.imwrite(out_path, img)
    print(f"Saved: {out_path}")

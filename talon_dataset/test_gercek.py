import json
from PIL import Image, ImageDraw
import sys
import os

sys.path.append(r'C:\Users\Zeylo\Desktop\talon_dataset')
import projection_math as pm

with open(r'C:\Users\Zeylo\Desktop\talon_dataset\dataset\talon_0004.json', 'r') as f:
    data = json.load(f)

img = Image.open(r'C:\Users\Zeylo\Desktop\talon_dataset\dataset\talon_0004.png')
draw = ImageDraw.Draw(img)

# Unscaled keypoints override for testing
pm.KEYPOINTS_LOCAL = {
    "nose":             {"x": 49.476, "y": 0.0, "z": 0.0},
    "left_wingtip":     {"x": -0.074, "y": 74.737, "z": 3.716},
    "right_wingtip":    {"x": -0.074, "y": -74.737, "z": 3.716},
    "tail":             {"x": -42.801, "y": 0.0, "z": 0.0},
    "left_tail_fin":    {"x": -28.011, "y": -19.411, "z": 8.164},
    "right_tail_fin":   {"x": -28.011, "y": 19.411, "z": 8.164}
}

pts = pm.calculate_keypoints_2d(data['drone_location'], data['drone_rotation'], data['camera_location'], data['camera_rotation'], data['camera_fov'])

# draw box
xs = [p['x'] for p in pts.values()]
ys = [p['y'] for p in pts.values()]
draw.rectangle([min(xs), min(ys), max(xs), max(ys)], outline=(0,255,0), width=4)

# draw points
for name, p in pts.items():
    draw.ellipse([p['x']-1, p['y']-1, p['x']+1, p['y']+1], fill=(255,0,0))

out_path = r'C:\Users\Zeylo\Desktop\GERCEK_KUTU_TESTI.png'
img.save(out_path)
print("Saved GERCEK_KUTU_TESTI.png")


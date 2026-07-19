import os
import json
import glob
from PIL import Image, ImageDraw

dataset_dir = r'C:\Users\Zeylo\Desktop\talon_dataset\dataset'
files = glob.glob(os.path.join(dataset_dir, '*.png'))
if not files:
    print('No png found')
    exit()

latest_png = max(files, key=os.path.getmtime)
latest_json = latest_png.replace('.png', '.json')

if not os.path.exists(latest_json):
    print('No json found')
    exit()

with open(latest_json, 'r') as f:
    data = json.load(f)

img = Image.open(latest_png)
draw = ImageDraw.Draw(img)

kps = data.get('keypoints_2d', {})
if not kps:
    print('No keypoints in json')
    exit()

def draw_line(p1, p2, color=(255,0,0)):
    if p1 in kps and p2 in kps:
        draw.line([kps[p1]['x'], kps[p1]['y'], kps[p2]['x'], kps[p2]['y']], fill=color, width=3)

draw_line('nose', 'left_wingtip')
draw_line('nose', 'right_wingtip')
draw_line('left_wingtip', 'tail')
draw_line('right_wingtip', 'tail')

# draw bbox
xs = [p['x'] for p in kps.values()]
ys = [p['y'] for p in kps.values()]
if xs and ys:
    draw.rectangle([min(xs), min(ys), max(xs), max(ys)], outline=(0,255,0), width=3)

out_path = r'C:\Users\Zeylo\Desktop\talon_dataset\SON_CEKILEN_ONIZLEME.png'
img.save(out_path)
print('Saved preview to', out_path)

import os
import json
import glob
from PIL import Image, ImageDraw

dataset_dir = r'C:\Users\Zeylo\Desktop\talon_dataset\dataset'
out_dir = r'C:\Users\Zeylo\.gemini\antigravity\brain\36eff956-7e9e-4245-954f-3ac1eb798a93\scratch'
os.makedirs(out_dir, exist_ok=True)

files = glob.glob(os.path.join(dataset_dir, '*.png'))
files.sort(key=os.path.getmtime, reverse=True)

if len(files) == 0:
    print('No png found')
    exit()

def draw_line(draw, kps, p1, p2, color=(0,255,0)):
    if p1 in kps and p2 in kps:
        if kps[p1]['on'] and kps[p2]['on']:
            draw.line([kps[p1]['x'], kps[p1]['y'], kps[p2]['x'], kps[p2]['y']], fill=color, width=4)

colors = {
    'nose': (255, 0, 0),        # Red
    'tail': (0, 0, 255),        # Blue
    'left_wingtip': (0, 255, 0),    # Green
    'right_wingtip': (255, 255, 0), # Yellow
    'left_tail_fin': (0, 255, 255), # Cyan
    'right_tail_fin': (255, 0, 255) # Magenta
}

for i in range(min(4, len(files))):
    png_path = files[i]
    json_path = png_path.replace('.png', '.json')
    if not os.path.exists(json_path):
        continue
    
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    img = Image.open(png_path)
    draw = ImageDraw.Draw(img)
    
    kps = data.get('keypoints_2d', {})
    
    # Draw connections
    draw_line(draw, kps, 'nose', 'left_wingtip')
    draw_line(draw, kps, 'nose', 'right_wingtip')
    draw_line(draw, kps, 'left_wingtip', 'tail')
    draw_line(draw, kps, 'right_wingtip', 'tail')
    draw_line(draw, kps, 'tail', 'left_tail_fin')
    draw_line(draw, kps, 'tail', 'right_tail_fin')

    for k, v in kps.items():
        if v.get('on', False):
            x, y = v['x'], v['y']
            color = colors.get(k, (255, 255, 255))
            draw.point((x, y), fill=color)

    out_path = os.path.join(out_dir, f'preview_{i}.png')
    img.save(out_path)
    print(f'Saved {out_path}')

import os
from PIL import Image

media_dir = r"C:\Users\Zeylo\.gemini\antigravity\brain\36eff956-7e9e-4245-954f-3ac1eb798a93\.tempmediaStorage"

if os.path.exists(media_dir):
    files = [f for f in os.listdir(media_dir) if f.endswith(".png")]
    print(f"Found {len(files)} files in temp media storage:")
    for f in sorted(files):
        path = os.path.join(media_dir, f)
        img = Image.open(path)
        print(f" - {f}: size={img.size}, mode={img.mode}")
else:
    print("Media storage directory does not exist.")

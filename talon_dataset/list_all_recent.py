import os
import time

media_dir = r"C:\Users\Zeylo\.gemini\antigravity\brain\36eff956-7e9e-4245-954f-3ac1eb798a93\.tempmediaStorage"

if os.path.exists(media_dir):
    files = [(f, os.path.getmtime(os.path.join(media_dir, f))) for f in os.listdir(media_dir) if f.endswith(".png")]
    files.sort(key=lambda x: x[1], reverse=True)
    print(f"Total media files: {len(files)}")
    print("Most recent 15 files:")
    for f, mtime in files[:15]:
        time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mtime))
        size = os.path.getsize(os.path.join(media_dir, f))
        print(f" - {f}: time={time_str}, size_bytes={size}")
else:
    print("Directory does not exist.")

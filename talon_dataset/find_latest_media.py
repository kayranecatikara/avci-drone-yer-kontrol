import os

media_dir = r"C:\Users\Zeylo\.gemini\antigravity\brain\36eff956-7e9e-4245-954f-3ac1eb798a93\.tempmediaStorage"

if os.path.exists(media_dir):
    files = [(f, os.path.getmtime(os.path.join(media_dir, f))) for f in os.listdir(media_dir) if f.endswith(".png")]
    files.sort(key=lambda x: x[1], reverse=True)
    print("Latest 5 media files:")
    for f, mtime in files[:5]:
        print(f" - {f}: mtime={mtime}")
else:
    print("Media storage directory does not exist.")

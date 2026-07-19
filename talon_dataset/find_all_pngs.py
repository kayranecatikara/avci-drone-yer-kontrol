import os
import time

conv_dir = r"C:\Users\Zeylo\.gemini\antigravity\brain\36eff956-7e9e-4245-954f-3ac1eb798a93"

print("Scanning for all PNG files recursively:")
png_files = []
for root, dirs, files in os.walk(conv_dir):
    for f in files:
        if f.lower().endswith(".png"):
            path = os.path.join(root, f)
            mtime = os.path.getmtime(path)
            size = os.path.getsize(path)
            png_files.append((path, size, mtime))

png_files.sort(key=lambda x: x[2], reverse=True)
print(f"Found {len(png_files)} PNG files in total.")
print("Top 10 most recent PNG files:")
for path, size, mtime in png_files[:15]:
    time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mtime))
    # Relative path
    rel_path = os.path.relpath(path, conv_dir)
    print(f" - {rel_path}: size={size}, time={time_str}")

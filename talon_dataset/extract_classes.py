import re
import sys

files_to_scan = [
    r"C:\Users\Zeylo\Desktop\drones_of_war\Drones of War Teknofest\DronesOfWar\Content\Paks\DronesOfWar-Windows.pak",
    r"C:\Users\Zeylo\Desktop\drones_of_war\Drones of War Teknofest\DronesOfWar\Content\Paks\DronesOfWar-Windows.ucas"
]
out_path = r"C:\Users\Zeylo\Desktop\talon_dataset\drone_classes.txt"

classes = set()
pattern = re.compile(b'BPP_[A-Za-z0-9]+_C\x00')

try:
    for pak_path in files_to_scan:
        with open(pak_path, "rb") as f:
            while chunk := f.read(1024 * 1024 * 50): # 50 MB chunks
                matches = pattern.findall(chunk)
                for m in matches:
                    classes.add(m.decode('ascii', errors='ignore'))
                
    with open(out_path, "w") as f:
        for c in sorted(classes):
            f.write(c + "\n")
    print(f"Found {len(classes)} classes. Saved to {out_path}")
except Exception as e:
    print("Error:", e)

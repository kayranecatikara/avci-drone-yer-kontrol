import struct
import os

ubulk_path = r"C:\Users\Zeylo\Desktop\FModel\Output\Exports\DronesOfWar\Content\Art\Meshes\Talon\BreakTalon\SM_Talon_Body.ubulk"

if not os.path.exists(ubulk_path):
    print("UBULK not found!")
    exit()

with open(ubulk_path, "rb") as f:
    data = f.read()

min_val = 999999.0
max_val = -999999.0
extremes = []

for i in range(0, len(data) - 4, 4):
    chunk = data[i:i+4]
    try:
        val = struct.unpack("<f", chunk)[0]
        # Ignore NaNs, Infinities, and absurd values
        if -5000.0 < val < 5000.0:
            # Ignore values between -2 and 2 (mostly UVs and Normals)
            if val > 2.0 or val < -2.0:
                if val < min_val: min_val = val
                if val > max_val: max_val = val
                extremes.append(val)
    except:
        pass

extremes.sort()
if len(extremes) > 10:
    print(f"Lowest 10 values: {extremes[:10]}")
    print(f"Highest 10 values: {extremes[-10:]}")
print(f"\nOverall Min: {min_val}")
print(f"Overall Max: {max_val}")

import struct
import sys
import numpy as np

def find_extremes():
    filepath = r"C:\Users\Zeylo\Desktop\FModel\Output\Exports\DronesOfWar\Content\Art\Meshes\Talon\BreakTalon\SM_Talon_Body.ubulk"
    
    with open(filepath, 'rb') as f:
        data = f.read()
        
    print(f"File size: {len(data)} bytes")
    
    # Trying different strides. Unreal usually uses 12 bytes for position (3x float32)
    # But vertex buffer has stride usually 32, 40, or 48.
    # Let's just read ALL float32s and group them by 3 to see if we can find the bounding box.
    
    floats = []
    for i in range(0, len(data) - 4, 4):
        val = struct.unpack('<f', data[i:i+4])[0]
        floats.append(val)
        
    # Filter reasonable floats (between -10000 and 10000, not exactly 0 if many, etc)
    valid_points = []
    for i in range(0, len(floats) - 2):
        x, y, z = floats[i], floats[i+1], floats[i+2]
        if -10000 < x < 10000 and -10000 < y < 10000 and -10000 < z < 10000:
            if not (abs(x) < 0.001 and abs(y) < 0.001 and abs(z) < 0.001):
                valid_points.append((x, y, z))
                
    valid_points = np.array(valid_points)
    print(f"Found {len(valid_points)} possible 3D points.")
    
    if len(valid_points) > 0:
        min_pt = np.min(valid_points, axis=0)
        max_pt = np.max(valid_points, axis=0)
        print(f"Min: {min_pt}")
        print(f"Max: {max_pt}")

if __name__ == "__main__":
    find_extremes()

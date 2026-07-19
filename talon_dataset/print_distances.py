import os
import json
import math

workspace_dir = r"c:\Users\Zeylo\Desktop\talon_dataset"
dataset_dir = os.path.join(workspace_dir, "dataset")

for df in sorted(os.listdir(dataset_dir)):
    if not df.endswith(".json"):
        continue
    json_path = os.path.join(dataset_dir, df)
    with open(json_path, "r") as f:
        data = json.load(f)
        
    dl = data["drone_location"]
    cl = data["camera_location"]
    dist = math.sqrt((dl["x"] - cl["x"])**2 + (dl["y"] - cl["y"])**2 + (dl["z"] - cl["z"])**2)
    
    # Check if bottom side (white) is visible by looking at the pitch/roll or yaw
    # Or we can just print the distance
    print(f"{df}: distance = {dist:.1f} cm | drone_rot={data['drone_rotation']}")

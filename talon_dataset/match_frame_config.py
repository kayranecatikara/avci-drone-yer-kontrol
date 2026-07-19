import os
import json
import math

workspace_dir = r"c:\Users\Zeylo\Desktop\talon_dataset"
dataset_dir = os.path.join(workspace_dir, "dataset")

# Let's inspect the keypoints layout in all frames
# For each frame, we check:
# 1. Nose position relative to Tail (Nose is at left/front, Tail is at right/back)
# 2. Wingtips layout (vertical vs horizontal)
# In Image 1:
# - Nose is at the far left, tail is at the far right.
# - Wingtips are vertical: one at the very top, one at the very bottom.
# - The wing is almost vertical.
# So x_nose < x_tail, y_left_wingtip is very different from y_right_wingtip, and x_left_wingtip is close to x_right_wingtip.

for df in sorted(os.listdir(dataset_dir)):
    if not df.endswith(".json"):
        continue
    json_path = os.path.join(dataset_dir, df)
    with open(json_path, "r") as f:
        data = json.load(f)
        
    kps = data.get("keypoints_2d")
    if not kps:
        continue
        
    nx, ny = kps["nose"]["x"], kps["nose"]["y"]
    tx, ty = kps["tail"]["x"], kps["tail"]["y"]
    lwx, lwy = kps["left_wingtip"]["x"], kps["left_wingtip"]["y"]
    rwx, rwy = kps["right_wingtip"]["x"], kps["right_wingtip"]["y"]
    
    # Calculate some metrics:
    dx_nose_tail = tx - nx  # positive if nose is to the left of tail
    dy_wings = abs(lwy - rwy) # vertical span of wings
    dx_wings = abs(lwx - rwx) # horizontal span of wings
    
    # We want: nose to the left of tail (dx_nose_tail > 0), and wings vertical (dy_wings > dx_wings)
    is_match_1 = dx_nose_tail > 100 and dy_wings > 200 and dx_wings < 150
    
    print(f"{df}: dx_nt={dx_nose_tail:.1f}, dy_wings={dy_wings:.1f}, dx_wings={dx_wings:.1f} | is_match_1={is_match_1}")

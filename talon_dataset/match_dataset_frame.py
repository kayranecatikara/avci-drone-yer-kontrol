import os
import json
import math

workspace_dir = r"c:\Users\Zeylo\Desktop\talon_dataset"
dataset_dir = os.path.join(workspace_dir, "dataset")

# Telemetry points from user image
user_pts = {
    "nose": (111, 376),
    "left_wingtip": (275, 668),
    "right_wingtip": (421, 60),
    "tail": (532, 403)
}

for i in range(1, 21):
    json_path = os.path.join(dataset_dir, f"talon_{i:04d}.json")
    if not os.path.exists(json_path):
        continue
    with open(json_path, "r") as f:
        data = json.load(f)
        
    kps = data.get("keypoints_2d")
    if not kps:
        continue
        
    u_nose = user_pts["nose"]
    u_tail = user_pts["tail"]
    u_dist_nt = math.sqrt((u_nose[0] - u_tail[0])**2 + (u_nose[1] - u_tail[1])**2)
    
    j_nose = (kps["nose"]["x"], kps["nose"]["y"])
    j_tail = (kps["tail"]["x"], kps["tail"]["y"])
    j_dist_nt = math.sqrt((j_nose[0] - j_tail[0])**2 + (j_nose[1] - j_tail[1])**2)
    
    scale = u_dist_nt / j_dist_nt
    
    err = 0
    for kp in ["nose", "left_wingtip", "right_wingtip", "tail"]:
        jp = (kps[kp]["x"], kps[kp]["y"])
        exp_x = u_nose[0] + scale * (jp[0] - j_nose[0])
        exp_y = u_nose[1] + scale * (jp[1] - j_nose[1])
        up = user_pts[kp]
        err += (exp_x - up[0])**2 + (exp_y - up[1])**2
        
    rmse = math.sqrt(err / 4)
    print(f"talon_{i:04d}: scale={scale:.4f}, RMSE={rmse:.4f} pixels")

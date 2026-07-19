import os
import json
import math
import numpy as np

# Load keypoints from JSON telemetry files
workspace_dir = r"c:\Users\Zeylo\Desktop\talon_dataset"
dataset_dir = os.path.join(workspace_dir, "dataset")

# Load telemetry for frames
frames = []
for i in range(1, 21):
    json_path = os.path.join(dataset_dir, f"talon_{i:04d}.json")
    if os.path.exists(json_path):
        with open(json_path, "r") as f:
            frames.append(json.load(f))

print(f"Loaded {len(frames)} frames from dataset.")

# Let's write the projection math in numpy/python
def rotate_vector_ue(x, y, z, pitch, yaw, roll):
    rad_pitch = math.radians(pitch)
    rad_yaw = math.radians(yaw)
    rad_roll = math.radians(roll)
    
    SP = math.sin(rad_pitch)
    CP = math.cos(rad_pitch)
    SY = math.sin(rad_yaw)
    CY = math.cos(rad_yaw)
    SR = math.sin(rad_roll)
    CR = math.cos(rad_roll)
    
    # AxisX (Forward)
    r00 = CP * CY
    r10 = CP * SY
    r20 = SP
    
    # AxisY (Right)
    r01 = SR * SP * CY - CR * SY
    r11 = SR * SP * SY + CR * CY
    r21 = -SR * CP
    
    # AxisZ (Up)
    r02 = CR * SP * CY + SR * SY
    r12 = CR * SP * SY - SR * CY
    r22 = CR * CP
    
    rx = x * r00 + y * r01 + z * r02
    ry = x * r10 + y * r11 + z * r12
    rz = x * r20 + y * r21 + z * r22
    
    return rx, ry, rz

def project_world_to_screen(world_pt, cam_loc, cam_rot, fov=90.0, width=1920, height=1080):
    vx = world_pt[0] - cam_loc['x']
    vy = world_pt[1] - cam_loc['y']
    vz = world_pt[2] - cam_loc['z']
    
    rad_pitch = math.radians(cam_rot['pitch'])
    rad_yaw = math.radians(-cam_rot['yaw'])
    rad_roll = math.radians(cam_rot['roll'])
    
    SP = math.sin(rad_pitch)
    CP = math.cos(rad_pitch)
    SY = math.sin(rad_yaw)
    CY = math.cos(rad_yaw)
    SR = math.sin(rad_roll)
    CR = math.cos(rad_roll)
    
    r00 = CP * CY
    r01 = -CP * SY
    r02 = SP
    
    r10 = SR * SP * CY + CR * SY
    r11 = -SR * SP * SY + CR * CY
    r12 = -SR * CP
    
    r20 = -CR * SP * CY + SR * SY
    r21 = CR * SP * SY + SR * CY
    r22 = CR * CP
    
    x_local = vx * r00 + vy * r01 + vz * r02
    y_local = vx * r10 + vy * r11 + vz * r12
    z_local = vx * r20 + vy * r21 + vz * r22
    
    if x_local <= 0:
        return -1.0, -1.0
        
    focal_length = (width / 2.0) / math.tan(math.radians(fov / 2.0))
    
    u = (width / 2.0) + (y_local / x_local) * focal_length
    v = (height / 2.0) - (z_local / x_local) * focal_length
    
    return u, v

# Let's project current coordinates for frame 1
current_coords = {
    "nose":             {"x": 53.583, "y": 0.0, "z": 0.0},
    "left_wingtip":     {"x": 7.206, "y": 71.690, "z": 8.668},
    "right_wingtip":    {"x": 7.206, "y": -71.690, "z": 8.668},
    "tail":             {"x": -40.412, "y": 0.0, "z": 0.0},
    "left_tail_fin":    {"x": -18.543, "y": 13.841, "z": 17.403},
    "right_tail_fin":   {"x": -18.543, "y": -13.841, "z": 17.403}
}

print("Frame 1 Projections with current coords:")
frame = frames[0]
for name, offset in current_coords.items():
    rx, ry, rz = rotate_vector_ue(offset['x'], offset['y'], offset['z'], 
                                  frame['drone_rotation']['pitch'], frame['drone_rotation']['yaw'], frame['drone_rotation']['roll'])
    world_pt = (frame['drone_location']['x'] + rx, frame['drone_location']['y'] + ry, frame['drone_location']['z'] + rz)
    u, v = project_world_to_screen(world_pt, frame['camera_location'], frame['camera_rotation'], frame['camera_fov'])
    print(f"  {name:15s}: projected=({u:7.2f}, {v:7.2f}) | json=({frame['keypoints_2d'][name]['x']}, {frame['keypoints_2d'][name]['y']})")

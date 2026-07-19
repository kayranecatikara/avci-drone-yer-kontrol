import os
import json
import math

workspace_dir = r"c:\Users\Zeylo\Desktop\talon_dataset"
dataset_dir = os.path.join(workspace_dir, "dataset")

with open(os.path.join(dataset_dir, "talon_0001.json"), "r") as f:
    f1 = json.load(f)

# Unreal Engine FRotator::RotateVector
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
    
    r00 = CP * CY
    r10 = CP * SY
    r20 = SP
    
    r01 = SR * SP * CY - CR * SY
    r11 = SR * SP * SY + CR * CY
    r21 = -SR * CP
    
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

# Coordinates suggested by user
user_coords = {
    "nose":             {"x": 45.58, "y": 0.0, "z": 0.0},
    "left_wingtip":     {"x": -3.44, "y": 73.874, "z": 0.0},
    "right_wingtip":    {"x": -3.44, "y": -73.874, "z": 0.0},
    "tail":             {"x": -47.30, "y": 0.0, "z": 0.0},
    "left_tail_fin":    {"x": -38.70, "y": 17.20, "z": 18.92},
    "right_tail_fin":   {"x": -38.70, "y": -17.20, "z": 18.92}
}

# Ground truth visual targets in Frame 1:
# nose: (804, 530) -> wait, let's look at the actual coordinates
# wingtips: left=(890, 659), right=(960, 351)
# tail: (1024, 544)
# fin_up (left fin tip): (995, 475)
# fin_down (right fin tip): (975, 550)

# Let's project and calculate error
drone_loc = f1["drone_location"]
drone_rot = f1["drone_rotation"]
cam_loc = f1["camera_location"]
cam_rot = f1["camera_rotation"]

print("Frame 1 Projections with user suggested coords:")
for name, offset in user_coords.items():
    rx, ry, rz = rotate_vector_ue(offset["x"], offset["y"], offset["z"], drone_rot["pitch"], drone_rot["yaw"], drone_rot["roll"])
    world_pt = (drone_loc["x"] + rx, drone_loc["y"] + ry, drone_loc["z"] + rz)
    u, v = project_world_to_screen(world_pt, cam_loc, cam_rot)
    print(f"  {name:15s}: projected=({u:.2f}, {v:.2f})")

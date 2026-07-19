import os
import json
import math

workspace_dir = r"c:\Users\Zeylo\Desktop\talon_dataset"
dataset_dir = os.path.join(workspace_dir, "dataset")

with open(os.path.join(dataset_dir, "talon_0001.json"), "r") as f:
    f1 = json.load(f)
with open(os.path.join(dataset_dir, "talon_0003.json"), "r") as f:
    f3 = json.load(f)

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

# Let's project Trial 2 coordinates: Left fin = (-23.26, 19.20, 15.078), Right fin = (-23.26, -19.20, 15.078)
x, y, z = -23.2600, 19.2000, 15.0780

print("=== Frame 1 ===")
# Left
rx1, ry1, rz1 = rotate_vector_ue(x, y, z, f1['drone_rotation']['pitch'], f1['drone_rotation']['yaw'], f1['drone_rotation']['roll'])
u1_l, v1_l = project_world_to_screen((f1['drone_location']['x'] + rx1, f1['drone_location']['y'] + ry1, f1['drone_location']['z'] + rz1), f1['camera_location'], f1['camera_rotation'])
# Right
rx1_r, ry1_r, rz1_r = rotate_vector_ue(x, -y, z, f1['drone_rotation']['pitch'], f1['drone_rotation']['yaw'], f1['drone_rotation']['roll'])
u1_r, v1_r = project_world_to_screen((f1['drone_location']['x'] + rx1_r, f1['drone_location']['y'] + ry1_r, f1['drone_location']['z'] + rz1_r), f1['camera_location'], f1['camera_rotation'])

print(f"Left fin: projected=({u1_l:.2f}, {v1_l:.2f}), target=(997.29, 461.10)")
print(f"Right fin: projected=({u1_r:.2f}, {v1_r:.2f}), target=(1004.01, 551.40)")

print("\n=== Frame 3 ===")
# Left
rx3, ry3, rz3 = rotate_vector_ue(x, y, z, f3['drone_rotation']['pitch'], f3['drone_rotation']['yaw'], f3['drone_rotation']['roll'])
u3_l, v3_l = project_world_to_screen((f3['drone_location']['x'] + rx3, f3['drone_location']['y'] + ry3, f3['drone_location']['z'] + rz3), f3['camera_location'], f3['camera_rotation'])
# Right
rx3_r, ry3_r, rz3_r = rotate_vector_ue(x, -y, z, f3['drone_rotation']['pitch'], f3['drone_rotation']['yaw'], f3['drone_rotation']['roll'])
u3_r, v3_r = project_world_to_screen((f3['drone_location']['x'] + rx3_r, f3['drone_location']['y'] + ry3_r, f3['drone_location']['z'] + rz3_r), f3['camera_location'], f3['camera_rotation'])

print(f"Left fin: projected=({u3_l:.2f}, {v3_l:.2f}), target=(970.00, 495.00)")
print(f"Right fin: projected=({u3_r:.2f}, {v3_r:.2f}), target=(975.00, 550.00)")

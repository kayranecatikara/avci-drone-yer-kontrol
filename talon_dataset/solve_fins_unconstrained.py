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
        return -10000.0, -10000.0
        
    focal_length = (width / 2.0) / math.tan(math.radians(fov / 2.0))
    
    u = (width / 2.0) + (y_local / x_local) * focal_length
    v = (height / 2.0) - (z_local / x_local) * focal_length
    
    return u, v

def loss_single_point(p, target1, target3):
    x, y, z = p
    # Frame 1
    rx1, ry1, rz1 = rotate_vector_ue(x, y, z, f1['drone_rotation']['pitch'], f1['drone_rotation']['yaw'], f1['drone_rotation']['roll'])
    w1 = (f1['drone_location']['x'] + rx1, f1['drone_location']['y'] + ry1, f1['drone_location']['z'] + rz1)
    u1, v1 = project_world_to_screen(w1, f1['camera_location'], f1['camera_rotation'], f1['camera_fov'])
    
    # Frame 3
    rx3, ry3, rz3 = rotate_vector_ue(x, y, z, f3['drone_rotation']['pitch'], f3['drone_rotation']['yaw'], f3['drone_rotation']['roll'])
    w3 = (f3['drone_location']['x'] + rx3, f3['drone_location']['y'] + ry3, f3['drone_location']['z'] + rz3)
    u3, v3 = project_world_to_screen(w3, f3['camera_location'], f3['camera_rotation'], f3['camera_fov'])
    
    err1 = (u1 - target1[0])**2 + (v1 - target1[1])**2
    err3 = (u3 - target3[0])**2 + (v3 - target3[1])**2
    return err1 + err3

def optimize(func, start_val, args=(), steps=[20.0, 10.0, 5.0, 1.0, 0.1, 0.01, 0.001]):
    best_params = list(start_val)
    best_loss = func(best_params, *args)
    for step in steps:
        improved = True
        while improved:
            improved = False
            for i in range(len(best_params)):
                for delta in [-step, step]:
                    test_params = list(best_params)
                    test_params[i] += delta
                    loss = func(test_params, *args)
                    if loss < best_loss:
                        best_loss = loss
                        best_params = test_params
                        improved = True
    return best_params, best_loss

def linspace(start, end, num):
    if num == 1:
        return [start]
    step = (end - start) / (num - 1)
    return [start + i * step for i in range(num)]

best_p_up = None
best_loss_up = float('inf')
best_p_down = None
best_loss_down = float('inf')

print("Searching grid for fin_up...")
for x in linspace(-60, 10, 8):
    for y in linspace(-60, 60, 8):
        for z in linspace(-10, 40, 6):
            p, loss = optimize(loss_single_point, [x, y, z], args=((997.29, 461.10), (970.0, 495.0)))
            if loss < best_loss_up:
                best_loss_up = loss
                best_p_up = p

print(f"Best fin_up: x={best_p_up[0]:.4f}, y={best_p_up[1]:.4f}, z={best_p_up[2]:.4f}, loss={best_loss_up:.4f} (RMSE={math.sqrt(best_loss_up/2):.4f} px)")

print("Searching grid for fin_down...")
for x in linspace(-60, 10, 8):
    for y in linspace(-60, 60, 8):
        for z in linspace(-10, 40, 6):
            p, loss = optimize(loss_single_point, [x, y, z], args=((1004.01, 551.40), (975.0, 550.0)))
            if loss < best_loss_down:
                best_loss_down = loss
                best_p_down = p

print(f"Best fin_down: x={best_p_down[0]:.4f}, y={best_p_down[1]:.4f}, z={best_p_down[2]:.4f}, loss={best_loss_down:.4f} (RMSE={math.sqrt(best_loss_down/2):.4f} px)")

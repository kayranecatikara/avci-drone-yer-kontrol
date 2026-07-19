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

def loss_symmetric_pair(params, target1_left, target1_right, target3_left, target3_right):
    x, y, z = params
    
    # Left fin: x, y, z
    rx1_l, ry1_l, rz1_l = rotate_vector_ue(x, y, z, f1['drone_rotation']['pitch'], f1['drone_rotation']['yaw'], f1['drone_rotation']['roll'])
    w1_l = (f1['drone_location']['x'] + rx1_l, f1['drone_location']['y'] + ry1_l, f1['drone_location']['z'] + rz1_l)
    u1_l, v1_l = project_world_to_screen(w1_l, f1['camera_location'], f1['camera_rotation'], f1['camera_fov'])
    
    rx3_l, ry3_l, rz3_l = rotate_vector_ue(x, y, z, f3['drone_rotation']['pitch'], f3['drone_rotation']['yaw'], f3['drone_rotation']['roll'])
    w3_l = (f3['drone_location']['x'] + rx3_l, f3['drone_location']['y'] + ry3_l, f3['drone_location']['z'] + rz3_l)
    u3_l, v3_l = project_world_to_screen(w3_l, f3['camera_location'], f3['camera_rotation'], f3['camera_fov'])
    
    # Right fin: x, -y, z
    rx1_r, ry1_r, rz1_r = rotate_vector_ue(x, -y, z, f1['drone_rotation']['pitch'], f1['drone_rotation']['yaw'], f1['drone_rotation']['roll'])
    w1_r = (f1['drone_location']['x'] + rx1_r, f1['drone_location']['y'] + ry1_r, f1['drone_location']['z'] + rz1_r)
    u1_r, v1_r = project_world_to_screen(w1_r, f1['camera_location'], f1['camera_rotation'], f1['camera_fov'])
    
    rx3_r, ry3_r, rz3_r = rotate_vector_ue(x, -y, z, f3['drone_rotation']['pitch'], f3['drone_rotation']['yaw'], f3['drone_rotation']['roll'])
    w3_r = (f3['drone_location']['x'] + rx3_r, f3['drone_location']['y'] + ry3_r, f3['drone_location']['z'] + rz3_r)
    u3_r, v3_r = project_world_to_screen(w3_r, f3['camera_location'], f3['camera_rotation'], f3['camera_fov'])
    
    err1_l = (u1_l - target1_left[0])**2 + (v1_l - target1_left[1])**2
    err1_r = (u1_r - target1_right[0])**2 + (v1_r - target1_right[1])**2
    err3_l = (u3_l - target3_left[0])**2 + (v3_l - target3_left[1])**2
    err3_r = (u3_r - target3_right[0])**2 + (v3_r - target3_right[1])**2
    
    return err1_l + err1_r + err3_l + err3_r

def optimize(func, start_val, args=(), steps=[10.0, 5.0, 1.0, 0.1, 0.01, 0.001]):
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

# Try both assignments to see which matches the physical left/right symmetry:
# Since Left wing has positive y (71.690), Left tail fin must have positive y.
# If Trial 1 (Left = UP) yields positive y, then Left is UP.
# If Trial 2 (Left = DOWN) yields positive y, then Left is DOWN.

# Trial 1: Left = UP, Right = DOWN
res1, loss1 = optimize(loss_symmetric_pair, [-35.0, 15.0, 15.0], 
                       args=((997.29, 461.10), (1004.01, 551.40), (970.0, 495.0), (975.0, 550.0)))
print("TRIAL 1 (Left = UP, Right = DOWN):")
print(f"Optimal coords: x={res1[0]:.4f}, y={res1[1]:.4f}, z={res1[2]:.4f}")
print(f"Total loss: {loss1:.4f} (RMSE = {math.sqrt(loss1/4):.4f} pixels)")

# Trial 2: Left = DOWN, Right = UP
res2, loss2 = optimize(loss_symmetric_pair, [-35.0, 15.0, 15.0], 
                       args=((1004.01, 551.40), (997.29, 461.10), (975.0, 550.0), (970.0, 495.0)))
print("\nTRIAL 2 (Left = DOWN, Right = UP):")
print(f"Optimal coords: x={res2[0]:.4f}, y={res2[1]:.4f}, z={res2[2]:.4f}")
print(f"Total loss: {loss2:.4f} (RMSE = {math.sqrt(loss2/4):.4f} pixels)")

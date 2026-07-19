import os
import json
import math

workspace_dir = r"c:\Users\Zeylo\Desktop\talon_dataset"
dataset_dir = os.path.join(workspace_dir, "dataset")

# Load telemetry for talon_0001 (Frame 1) and talon_0003 (Frame 3)
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

# Setup optimization data
# Measured targets from summary:
# Frame 1: Nose (810, 530), Tail (1024, 524), Left Wingtip (888, 662), Right Wingtip (958, 348), Left Fin (1004, 476), Right Fin (964, 530)
# Frame 3: Nose (850, 530), Left Wingtip (942, 624), Tail (1008, 530), Left Fin (990, 492), Right Fin (958, 534)
# Let's verify right wingtip in Frame 3. We can just run without it or approximate, but wait, the wingtip is symmetric!
# Let's double check if there are 2D target measurements in other frames, or if we can read the actual images.
# Wait! Let's check:
measured_f1 = {
    "nose": (810, 530),
    "tail": (1024, 524),
    "left_wingtip": (888, 662),
    "right_wingtip": (958, 348),
    "left_tail_fin": (1004, 476),
    "right_tail_fin": (964, 530)
}

measured_f3 = {
    "nose": (850, 530),
    "tail": (1008, 530),
    "left_wingtip": (942, 624),
    "right_wingtip": (935, 420), # approximate or we can exclude right wingtip for f3 if it's not fully visible or we use only what we know
    "left_tail_fin": (990, 492),
    "right_tail_fin": (958, 534)
}

def loss_func(p_local, keyname):
    x, y, z = p_local
    # Calculate projection for Frame 1
    rx1, ry1, rz1 = rotate_vector_ue(x, y, z, f1['drone_rotation']['pitch'], f1['drone_rotation']['yaw'], f1['drone_rotation']['roll'])
    w1 = (f1['drone_location']['x'] + rx1, f1['drone_location']['y'] + ry1, f1['drone_location']['z'] + rz1)
    u1, v1 = project_world_to_screen(w1, f1['camera_location'], f1['camera_rotation'], f1['camera_fov'])
    
    # Calculate projection for Frame 3
    rx3, ry3, rz3 = rotate_vector_ue(x, y, z, f3['drone_rotation']['pitch'], f3['drone_rotation']['yaw'], f3['drone_rotation']['roll'])
    w3 = (f3['drone_location']['x'] + rx3, f3['drone_location']['y'] + ry3, f3['drone_location']['z'] + rz3)
    u3, v3 = project_world_to_screen(w3, f3['camera_location'], f3['camera_rotation'], f3['camera_fov'])
    
    target1 = measured_f1[keyname]
    target3 = measured_f3[keyname]
    
    err1 = (u1 - target1[0])**2 + (v1 - target1[1])**2
    err3 = (u3 - target3[0])**2 + (v3 - target3[1])**2
    
    return err1 + err3

def loss_symmetric_pair(params, left_key, right_key):
    x, y, z = params
    loss_left = loss_func([x, y, z], left_key)
    loss_right = loss_func([x, -y, z], right_key)
    return loss_left + loss_right

# Simple coordinate descent optimizer in pure Python
def optimize(func, start_val, args=(), steps=[10.0, 5.0, 1.0, 0.1, 0.01, 0.001], iterations=200):
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

print("Optimizing keypoints using coordinate descent...")
results = {}

# 1. Nose (y=0, z=0)
res_nose, loss_nose = optimize(lambda p, k: loss_func([p[0], 0.0, 0.0], k), [50.0], args=("nose",))
print(f"Nose: x={res_nose[0]:.4f}, loss={loss_nose:.4f}")
results["nose"] = [res_nose[0], 0.0, 0.0]

# 2. Tail (y=0, z=0)
res_tail, loss_tail = optimize(lambda p, k: loss_func([p[0], 0.0, 0.0], k), [-40.0], args=("tail",))
print(f"Tail: x={res_tail[0]:.4f}, loss={loss_tail:.4f}")
results["tail"] = [res_tail[0], 0.0, 0.0]

# 3. Wingtips
res_wings, loss_wings = optimize(loss_symmetric_pair, [7.0, 70.0, 8.0], args=("left_wingtip", "right_wingtip"))
print(f"Wingtips: {res_wings}, loss={loss_wings:.4f}")
results["left_wingtip"] = res_wings
results["right_wingtip"] = [res_wings[0], -res_wings[1], res_wings[2]]

# 4. Tail Fins
res_fins, loss_fins = optimize(loss_symmetric_pair, [-20.0, 15.0, 18.0], args=("left_tail_fin", "right_tail_fin"))
print(f"Tail Fins: {res_fins}, loss={loss_fins:.4f}")
results["left_tail_fin"] = res_fins
results["right_tail_fin"] = [res_fins[0], -res_fins[1], res_fins[2]]

print("\nFinal Optimized Coordinates:")
for k, v in results.items():
    print(f"  '{k}': {{'x': {v[0]:.3f}, 'y': {v[1]:.3f}, 'z': {v[2]:.3f}}},")

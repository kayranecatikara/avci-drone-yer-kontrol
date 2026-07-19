import os
import json
import math

workspace_dir = r"c:\Users\Zeylo\Desktop\talon_dataset"
dataset_dir = os.path.join(workspace_dir, "dataset")

with open(os.path.join(dataset_dir, "talon_0001.json"), "r") as f:
    f1 = json.load(f)
with open(os.path.join(dataset_dir, "talon_0002.json"), "r") as f:
    f2 = json.load(f)

# Exact 2D coordinates from user scribbles:
# Frame 1 (talon_0001):
#   Nose: (751.44, 529.36)
#   Left Wingtip: (881.26, 730.45)
#   Right Wingtip: (986.72, 277.40)
#   Tail: (1065.66, 546.99)
#   Left Tail Fin: (1002.82, 575.41)
#   Right Tail Fin: (1044.16, 465.87)
# Frame 2 (talon_0002):
#   Nose: (1107.31, 603.56)
#   Left Wingtip: (1016.74, 800.37)
#   Right Wingtip: (914.55, 404.85)
#   Tail: (834.15, 573.63)
#   Left Tail Fin: (883.87, 608.05)
#   Right Tail Fin: (862.85, 498.20)

user_f1 = {
    "nose": (811.71, 531.85),
    "left_wingtip": (901.18, 672.62),
    "right_wingtip": (976.40, 355.48),
    "tail": (1031.66, 544.19),
    "left_tail_fin": (987.67, 564.09),
    "right_tail_fin": (1016.61, 487.41)
}

user_f2 = {
    "nose": (1056.77, 550.61),
    "left_wingtip": (1006.96, 658.85),
    "right_wingtip": (950.75, 441.32),
    "tail": (906.53, 534.15),
    "left_tail_fin": (933.88, 553.08),
    "right_tail_fin": (922.32, 492.66)
}

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

def loss_func(p_local, keyname):
    x, y, z = p_local
    # Calculate projection for Frame 1
    rx1, ry1, rz1 = rotate_vector_ue(x, y, z, f1['drone_rotation']['pitch'], f1['drone_rotation']['yaw'], f1['drone_rotation']['roll'])
    w1 = (f1['drone_location']['x'] + rx1, f1['drone_location']['y'] + ry1, f1['drone_location']['z'] + rz1)
    u1, v1 = project_world_to_screen(w1, f1['camera_location'], f1['camera_rotation'], f1['camera_fov'])
    
    # Calculate projection for Frame 2
    rx2, ry2, rz2 = rotate_vector_ue(x, y, z, f2['drone_rotation']['pitch'], f2['drone_rotation']['yaw'], f2['drone_rotation']['roll'])
    w2 = (f2['drone_location']['x'] + rx2, f2['drone_location']['y'] + ry2, f2['drone_location']['z'] + rz2)
    u2, v2 = project_world_to_screen(w2, f2['camera_location'], f2['camera_rotation'], f2['camera_fov'])
    
    target1 = user_f1[keyname]
    target2 = user_f2[keyname]
    
    err1 = (u1 - target1[0])**2 + (v1 - target1[1])**2
    err2 = (u2 - target2[0])**2 + (v2 - target2[1])**2
    
    return err1 + err2

def loss_symmetric_pair(params, left_key, right_key):
    x, y, z = params
    loss_left = loss_func([x, y, z], left_key)
    loss_right = loss_func([x, -y, z], right_key)
    return loss_left + loss_right

# Coordinate descent optimizer
def optimize(func, start_val, args=(), steps=[20.0, 10.0, 5.0, 1.0, 0.1, 0.01, 0.001, 0.0001]):
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

print("Optimizing keypoints using coordinate descent on user scribbles...")
results = {}

# 1. Nose (y=0, z=0)
res_nose, loss_nose = optimize(lambda p, k: loss_func([p[0], 0.0, 0.0], k), [40.0], args=("nose",))
print(f"Nose: x={res_nose[0]:.4f}, loss={loss_nose:.4f}")
results["nose"] = [res_nose[0], 0.0, 0.0]

# 2. Tail (y=0, z=0)
res_tail, loss_tail = optimize(lambda p, k: loss_func([p[0], 0.0, 0.0], k), [-45.0], args=("tail",))
print(f"Tail: x={res_tail[0]:.4f}, loss={loss_tail:.4f}")
results["tail"] = [res_tail[0], 0.0, 0.0]

# 3. Wingtips
res_wings, loss_wings = optimize(loss_symmetric_pair, [-3.0, 73.0, 0.0], args=("left_wingtip", "right_wingtip"))
print(f"Wingtips: {res_wings}, loss={loss_wings:.4f}")
results["left_wingtip"] = res_wings
results["right_wingtip"] = [res_wings[0], -res_wings[1], res_wings[2]]

# 4. Tail Fins
# Since the left fin points left (negative Y in UE) and right fin points right (positive Y in UE),
# we start with Y=17.0. If left key is left_tail_fin, it should have negative Y.
# Let's check: in loss_symmetric_pair, left_key gets [x, y, z] and right_key gets [x, -y, z].
# So if we want left_tail_fin to have negative Y, we should optimize with negative Y!
# Let's see: if we pass start y = -17.0:
res_fins, loss_fins = optimize(loss_symmetric_pair, [-38.0, -17.0, 18.0], args=("left_tail_fin", "right_tail_fin"))
print(f"Tail Fins: {res_fins}, loss={loss_fins:.4f}")
results["left_tail_fin"] = res_fins
results["right_tail_fin"] = [res_fins[0], -res_fins[1], res_fins[2]]

print("\nFinal Optimized Coordinates:")
for k, v in results.items():
    print(f"  \"{k}\": {{\"x\": {v[0]:.3f}, \"y\": {v[1]:.3f}, \"z\": {v[2]:.3f}}},")

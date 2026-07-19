import os
import json
import math

dataset_dir = r"C:\Users\Zeylo\Desktop\FINISH\jsonlar"

RAW_CAD_DATA = {
    "nose": {"x": 69.13, "y": 0.19, "z": -2.77},
    "left_wingtip": {"x": 1.65, "y": -99.93, "z": 5.81},
    "right_wingtip": {"x": 1.65, "y": 99.93, "z": 5.81},
    "tail": {"x": -55.38, "y": 0.10, "z": 0.10},
    "left_tail_fin": {"x": -43.17, "y": -28.25, "z": 16.98},
    "right_tail_fin": {"x": -43.17, "y": 28.25, "z": 16.98}
}

def get_unreal_matrix(pitch, yaw, roll):
    SP, CP = math.sin(math.radians(pitch)), math.cos(math.radians(pitch))
    SY, CY = math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
    SR, CR = math.sin(math.radians(roll)), math.cos(math.radians(roll))
    
    r00 = CP * CY; r10 = CP * SY; r20 = SP
    r01 = SR * SP * CY - CR * SY; r11 = SR * SP * SY + CR * CY; r21 = -SR * CP
    r02 = -(CR * SP * CY + SR * SY); r12 = CY * SR - CR * SP * SY; r22 = CR * CP
    return [[r00, r01, r02], [r10, r11, r12], [r20, r21, r22]]

def calculate_keypoints_2d(drone_loc, drone_rot, cam_loc, cam_rot, cam_fov=90.0):
    kps_2d = {}
    for name, cad in RAW_CAD_DATA.items():
        ue_x = cad["x"] * 1.422
        ue_y = cad["y"] * 1.422
        ue_z = cad["z"] * 1.422
        
        R = get_unreal_matrix(drone_rot['pitch'], drone_rot['yaw'], drone_rot['roll'])
        rx = ue_x * R[0][0] + ue_y * R[0][1] + ue_z * R[0][2]
        ry = ue_x * R[1][0] + ue_y * R[1][1] + ue_z * R[1][2]
        rz = ue_x * R[2][0] + ue_y * R[2][1] + ue_z * R[2][2]
        
        world_pt = (drone_loc["x"] + rx, drone_loc["y"] + ry, drone_loc["z"] + rz)
        
        vx = world_pt[0] - cam_loc["x"]
        vy = world_pt[1] - cam_loc["y"]
        vz = world_pt[2] - cam_loc["z"]
        
        R_cam = get_unreal_matrix(cam_rot['pitch'], cam_rot['yaw'], cam_rot['roll'])
        x_local = vx * R_cam[0][0] + vy * R_cam[1][0] + vz * R_cam[2][0]
        y_local = vx * R_cam[0][1] + vy * R_cam[1][1] + vz * R_cam[2][1]
        z_local = vx * R_cam[0][2] + vy * R_cam[1][2] + vz * R_cam[2][2]
        
        if x_local <= 0:
            kps_2d[name] = {"x": -1, "y": -1}
            continue
            
        focal_length = (1920 / 2.0) / math.tan(math.radians(cam_fov / 2.0))
        u = (1920 / 2.0) + (y_local / x_local) * focal_length
        v = (1080 / 2.0) - (z_local / x_local) * focal_length
        kps_2d[name] = {"x": u, "y": v}
    return kps_2d

def test_repair():
    print("TESTING 10 IMAGES (JSON FIX) WITH CLAUDE'S TRUE MATH")
    # You can pick 10 random JSONs here to test
    test_files = ["talon_00000.json", "talon_08000.json", "talon_12780.json", "talon_08550.json"] 
    for filename in test_files:
        filepath = os.path.join(dataset_dir, filename)
        if not os.path.exists(filepath): continue
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        drone_loc, drone_rot = data.get('drone_location'), data.get('drone_rotation')
        cam_loc, cam_rot = data.get('camera_location'), data.get('camera_rotation')
        cam_fov = data.get('camera_fov', 125.0)
        
        # FOV-90 FIX FOR THE BATCHES:
        if cam_fov == 90.0:
            cam_fov = 125.0 # Enforcing actual rendered FOV as proposed by Claude
            
        kps_2d = calculate_keypoints_2d(drone_loc, drone_rot, cam_loc, cam_rot, cam_fov)
        data['keypoints_2d'] = kps_2d
        
        test_out = os.path.join(dataset_dir, filename.replace(".json", "_TEST_FIXED.json"))
        with open(test_out, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        print(f"Fixed: {test_out}")

test_repair()

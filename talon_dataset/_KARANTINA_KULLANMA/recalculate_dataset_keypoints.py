import os
import json
import glob
import math

# Calibrated 3D coordinate offsets in Python projection space
# Note: positive Y projects to Left side of screen, negative Y to Right side of screen
KEYPOINTS_LOCAL = {
    "nose":             {"x": 45.580, "y": 0.000, "z": 0.000},       # Nose-tip FPV Camera
    "left_wingtip":     {"x": -3.440, "y": 73.874, "z": 0.000},     # Left Wingtip
    "right_wingtip":    {"x": -3.440, "y": -73.874, "z": 0.000},    # Right Wingtip
    "tail":             {"x": -47.300, "y": 0.000, "z": 0.000},      # Rear Motor Shaft / Propeller Hub
    "left_tail_fin":    {"x": -38.700, "y": 17.200, "z": 18.920},   # Left V-Tail Tip
    "right_tail_fin":   {"x": -38.700, "y": -17.200, "z": 18.920}   # Right V-Tail Tip
}

def rotate_vector_ue(x, y, z, pitch, yaw, roll):
    # Native Unreal Engine FRotator::RotateVector implementation
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

def recalculate_dataset(target_dir, overwrite_manual=False):
    print(f"[INFO] Scanning directory for JSON files: {target_dir}")
    json_pattern = os.path.join(target_dir, "*.json")
    json_files = glob.glob(json_pattern)
    
    total_files = len(json_files)
    print(f"[INFO] Found {total_files} JSON metadata files to process.")
    
    if total_files == 0:
        print("[WARNING] No JSON files found. Please make sure you pointed to the correct dataset folder.")
        return
        
    fixed_count = 0
    for idx, filepath in enumerate(json_files):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check if this file was manually edited by the user
            is_manual = data.get("manually_edited", False)
            if is_manual and not overwrite_manual:
                continue # Skip manually annotated frames
                
            dl = data.get("drone_location")
            dr = data.get("drone_rotation")
            cl = data.get("camera_location")
            cr = data.get("camera_rotation")
            cf = data.get("camera_fov", 90.0)
            
            if dl and dr and cl and cr:
                new_keypoints = {}
                for name, offset in KEYPOINTS_LOCAL.items():
                    rx, ry, rz = rotate_vector_ue(offset["x"], offset["y"], offset["z"], dr['pitch'], dr['yaw'], dr['roll'])
                    world_pt = (dl['x'] + rx, dl['y'] + ry, dl['z'] + rz)
                    u, v = project_world_to_screen(world_pt, cl, cr, cf)
                    new_keypoints[name] = {"x": round(u), "y": round(v)}
                
                data["keypoints_2d"] = new_keypoints
                
                # Save back the updated JSON
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4)
                
                fixed_count += 1
            
            # Print progress every 1000 files
            if (idx + 1) % 1000 == 0 or (idx + 1) == total_files:
                print(f"[PROGRESS] Processed {idx + 1}/{total_files} files...")
                
        except Exception as e:
            print(f"[ERROR] Failed to process {os.path.basename(filepath)}: {e}")
            
    print(f"[SUCCESS] Recalculated 2D keypoints using calibrated 3D coordinates in {fixed_count} files successfully!")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    local_dataset = os.path.join(current_dir, "dataset")
    
    print("==================================================================")
    print("      TALON UAV DATASET KEYPOINT RECALCULATION SCRIPT")
    print("==================================================================")
    print(f"Default dataset path: {local_dataset}")
    print("If you want to run it on another folder (e.g. the extracted zip folder),")
    print("enter the folder path below. Or just press Enter to run it on the default folder.")
    print("==================================================================")
    
    user_path = input("Enter path (or press Enter for default): ").strip()
    target_path = user_path if user_path else local_dataset
    
    if os.path.exists(target_path):
        recalculate_dataset(target_path)
    else:
        print(f"[ERROR] Path does not exist: {target_path}")

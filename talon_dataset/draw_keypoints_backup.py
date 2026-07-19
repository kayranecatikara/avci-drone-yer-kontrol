import os
import json
import sys
import math

# Ensure PIL (Pillow) is installed for image editing
try:
    from PIL import Image, ImageDraw
except ImportError:
    print("[INFO] Pillow is required for drawing. Installing it now...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
    from PIL import Image, ImageDraw

# Color mapping for beautiful visualization
KEYPOINT_COLORS = {
    "nose":             (30, 100, 250),   # Blue
    "left_wingtip":     (255, 30, 30),    # Red
    "right_wingtip":    (255, 100, 200),  # Pink
    "tail":             (255, 120, 0),    # Orange
    "left_tail_fin":    (255, 215, 0),    # Yellow
    "right_tail_fin":   (0, 200, 80)      # Green
}

# ============================================================================
# TALON PHYSICAL SPECS & 3D PROJECTION MATHEMATICS (X-UAV Talon EPO 1718mm)
# ============================================================================
# DRONE SCALE CALIBRATION: Fix double scaling (çift ölçekleme) bug!
# The 3D model in the Drones of War simulation environment is exactly 14% smaller than
# the physical X-UAV Talon. We divide the previous double-scaled coordinates by 0.86
# to reverse the second scale factor, resulting in a single mathematically perfect 0.86 scale!
KEYPOINTS_LOCAL = {
    "nose":             {"x": 45.6663, "y": -0.6599, "z": -0.2907},
    "left_wingtip":     {"x": -3.8221, "y": 73.9262, "z": -0.2907},
    "right_wingtip":    {"x": -3.8221, "y": -75.2459, "z": -0.2907},
    "tail":             {"x": -48.0081, "y": -0.6599, "z": -0.2907},
    "left_tail_fin":    {"x": -65.6826, "y": 17.0145, "z": 19.1512},
    "right_tail_fin":   {"x": -65.6826, "y": -18.3343, "z": 19.1512}
}

def rotate_vector_ue(x, y, z, pitch, yaw, roll):
    # Convert degrees to radians and invert pitch & roll for Unreal Engine's coordinate system
    rad_pitch = math.radians(-pitch)
    rad_yaw = math.radians(yaw)
    rad_roll = math.radians(-roll)
    
    SP = math.sin(rad_pitch)
    CP = math.cos(rad_pitch)
    SY = math.sin(rad_yaw)
    CY = math.cos(rad_yaw)
    SR = math.sin(rad_roll)
    CR = math.cos(rad_roll)
    
    # Rotation matrix: R = Rz(yaw) @ Ry(-pitch) @ Rx(-roll)
    r00 = CY * CP
    r01 = -SY * CR + CY * SP * SR
    r02 = SY * SR + CY * SP * CR
    
    r10 = SY * CP
    r11 = CY * CR + SY * SP * SR
    r12 = -CY * SR + SY * SP * CR
    
    r20 = -SP
    r21 = CP * SR
    r22 = CP * CR
    
    rx = x * r00 + y * r01 + z * r02
    ry = x * r10 + y * r11 + z * r12
    rz = x * r20 + y * r21 + z * r22
    
    return rx, ry, rz

def project_world_to_screen(world_pt, cam_loc, cam_rot, fov=90.0, width=1920, height=1080):
    vx = world_pt[0] - cam_loc['x']
    vy = world_pt[1] - cam_loc['y']
    vz = world_pt[2] - cam_loc['z']
    
    # Inverted Yaw in Unreal camera rotation!
    rad_pitch = math.radians(cam_rot['pitch'])
    rad_yaw = math.radians(-cam_rot['yaw'])
    rad_roll = math.radians(cam_rot['roll'])
    
    SP = math.sin(rad_pitch)
    CP = math.cos(rad_pitch)
    SY = math.sin(rad_yaw)
    CY = math.cos(rad_yaw)
    SR = math.sin(rad_roll)
    CR = math.cos(rad_roll)
    
    # Camera rotation matrix in XYZ order: R = Rx(roll) @ Ry(pitch) @ Rz(-yaw)
    r00 = CP * CY
    r01 = -CP * SY
    r02 = SP
    
    r10 = SR * SP * CY + CR * SY
    r11 = -SR * SP * SY + CR * CY
    r12 = -SR * CP
    
    r20 = -CR * SP * CY + SR * SY
    r21 = CR * SP * SY + SR * CY
    r22 = CR * CP
    
    # Project camera relative vector onto camera unit axes (rows of R_cam)
    x_local = vx * r00 + vy * r01 + vz * r02
    y_local = vx * r10 + vy * r11 + vz * r12
    z_local = vx * r20 + vy * r21 + vz * r22
    
    if x_local <= 0:
        return -1.0, -1.0
        
    focal_length = (width / 2.0) / math.tan(math.radians(fov / 2.0))
    
    u = (width / 2.0) + (y_local / x_local) * focal_length
    v = (height / 2.0) - (z_local / x_local) * focal_length
    
    return u, v

def calculate_keypoints_2d(drone_loc, drone_rot, cam_loc, cam_rot, cam_fov=90.0):
    kps_2d = {}
    for name, offset in KEYPOINTS_LOCAL.items():
        rx, ry, rz = rotate_vector_ue(
            offset["x"], offset["y"], offset["z"],
            drone_rot["pitch"], drone_rot["yaw"], drone_rot["roll"]
        )
        world_pt = (
            drone_loc["x"] + rx,
            drone_loc["y"] + ry,
            drone_loc["z"] + rz
        )
        u, v = project_world_to_screen(world_pt, cam_loc, cam_rot, fov=cam_fov)
        kps_2d[name] = {"x": u, "y": v}
    return kps_2d

def main():
    workspace_dir = r"c:\Users\Zeylo\Desktop\talon_dataset"
    dataset_dir = os.path.join(workspace_dir, "dataset")
    output_dir = os.path.join(workspace_dir, "dataset_annotated")
    pivot_dir = os.path.join(workspace_dir, "dataset_pivot")
    
    if not os.path.exists(dataset_dir):
        print(f"[ERROR] Dataset directory not found at: {dataset_dir}")
        return
        
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"[INFO] Created output directory: {output_dir}")
        
    if not os.path.exists(pivot_dir):
        os.makedirs(pivot_dir)
        print(f"[INFO] Created pivot directory: {pivot_dir}")
        
    # Find all PNG/JSON pairs
    files = [f for f in os.listdir(dataset_dir) if f.endswith(".png")]
    if not files:
        print(f"[WARNING] No PNG images found in {dataset_dir}. Run your generator first!")
        return
        
    print(f"[INFO] Found {len(files)} screenshots to process. Beginning dual-path rendering...")
    
    processed_count = 0
    skipped_count = 0
    
    for filename in sorted(files):
        base_name = os.path.splitext(filename)[0]
        json_filename = base_name + ".json"
        
        img_path = os.path.join(dataset_dir, filename)
        json_path = os.path.join(dataset_dir, json_filename)
        
        if not os.path.exists(json_path):
            skipped_count += 1
            continue
            
        # 1. Load JSON Telemetry
        try:
            with open(json_path, "r") as jf:
                data = json.load(jf)
        except Exception as e:
            print(f"[ERROR] Failed to load JSON {json_filename}: {e}")
            continue
            
        # FORCE RECALCULATION: Always calculate keypoints on the fly using latest 3D specs if telemetry is present!
        drone_loc = data.get("drone_location")
        drone_rot = data.get("drone_rotation")
        cam_loc = data.get("camera_location")
        cam_rot = data.get("camera_rotation")
        cam_fov = data.get("camera_fov", 90.0)
        
        keypoints_2d = None
        if drone_loc and drone_rot and cam_loc and cam_rot:
            try:
                keypoints_2d = calculate_keypoints_2d(drone_loc, drone_rot, cam_loc, cam_rot, cam_fov)
            except Exception as e:
                print(f"[ERROR] Failed to calculate keypoints on the fly: {e}")
                
        if not keypoints_2d:
            keypoints_2d = data.get("keypoints_2d")
            
        if not keypoints_2d:
            skipped_count += 1
            continue
            
        # 2. Render Path A: 6-Keypoint Skeleton (dataset_annotated)
        try:
            img_ann = Image.open(img_path)
            draw_ann = ImageDraw.Draw(img_ann)
            
            projected_points = {}
            for kp_name, coords in keypoints_2d.items():
                px = coords.get("x", -1)
                py = coords.get("y", -1)
                if px >= 0 and py >= 0 and px <= 1920 and py <= 1080:
                    projected_points[kp_name] = (int(round(px)), int(round(py)))
                    
            def draw_line_safe(pt1_name, pt2_name, color=(128, 128, 128), width=3):
                if pt1_name in projected_points and pt2_name in projected_points:
                    draw_ann.line([projected_points[pt1_name], projected_points[pt2_name]], fill=color, width=width)
                    
            draw_line_safe("nose", "left_wingtip")
            draw_line_safe("nose", "right_wingtip")
            draw_line_safe("left_wingtip", "tail")
            draw_line_safe("right_wingtip", "tail")
            draw_line_safe("tail", "left_tail_fin")
            draw_line_safe("tail", "right_tail_fin")
            
            for kp_name, coord in projected_points.items():
                px, py = coord
                color = KEYPOINT_COLORS[kp_name]
                draw_ann.ellipse([px - 6, py - 6, px + 6, py + 6], fill=color, outline=(255, 255, 255), width=2)
                
            out_ann_path = os.path.join(output_dir, filename)
            img_ann.save(out_ann_path)
        except Exception as e:
            print(f"[ERROR] Failed to render skeleton for {filename}: {e}")
            continue
            
        # 3. Render Path B: Raw Pivot Center (dataset_pivot) - 4x4 Pixel Square
        try:
            if drone_loc and cam_loc and cam_rot:
                img_piv = Image.open(img_path)
                draw_piv = ImageDraw.Draw(img_piv)
                
                # Project raw actor center (0, 0, 0 local offset)
                world_pt = (drone_loc["x"], drone_loc["y"], drone_loc["z"])
                u, v = project_world_to_screen(world_pt, cam_loc, cam_rot, fov=cam_fov)
                
                if u >= 0 and v >= 0 and u <= 1920 and v <= 1080:
                    px, py = int(round(u)), int(round(v))
                    # Draw a solid 4x4 pixel magenta square
                    draw_piv.rectangle([px - 2, py - 2, px + 1, py + 1], fill=(255, 0, 255))
                    
                out_piv_path = os.path.join(pivot_dir, filename)
                img_piv.save(out_piv_path)
        except Exception as e:
            print(f"[ERROR] Failed to render pivot for {filename}: {e}")
            continue
            
        processed_count += 1
        
    print(f"\n[SUCCESS] Render complete! Processed {processed_count} images.")
    print(f"[INFO] 6-Keypoint annotated images saved in: {output_dir}")
    print(f"[INFO] Raw 4x4 pivot-only verification images saved in: {pivot_dir}")

if __name__ == "__main__":
    main()

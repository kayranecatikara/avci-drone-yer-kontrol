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
# KULLANICININ VERDIGI EXACT CAD TABLOSU (Milimetre cinsinden)
# Adam akilli, senin verdigin tablonun BİREBİR AYNISI!
RAW_CAD_DATA = {
    "nose":             {"x": -554.32, "y": -12.66, "z": -0.03},
    "left_wingtip":     {"x": 97.71,   "y": 45.45,  "z": 858.97},
    "right_wingtip":    {"x": 97.71,   "y": 45.45,  "z": -859.03},
    "tail":             {"x": 560.16,  "y": -43.79, "z": 0.01},
    "left_tail_fin":    {"x": 527.61,  "y": 179.87, "z": 225.64},
    "right_tail_fin":   {"x": 527.61,  "y": 179.87, "z": -225.70}
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
    for name, cad in RAW_CAD_DATA.items():
        # TABLODAKI VERILERI OYUN MOTORUNA CEVIR:
        # 1. Oyun motoru santimetre (cm) kullanir, tablo milimetre (mm). Bu yuzden 10'a boluyoruz.
        # 2. Oyun motorunda X ileridir (Burun +X'dir), tabloda Burun eksi X. (Yani X'i ters ceviriyoruz)
        # 3. Oyun motorunda Z yukaridir, tabloda Y yukaridir.
        # 4. Oyun motorunda Y sag/soldur, tabloda Z sag/soldur.
        ue_x = -cad["x"] / 10.0
        ue_y = cad["z"] / 10.0
        ue_z = cad["y"] / 10.0
        
        rx, ry, rz = rotate_vector_ue(
            ue_x, ue_y, ue_z,
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
            
        # FORCE RECALCULATION: Always calculate keypoints on the fly using latest 3D specs
        # UNLESS the frame has been manually edited/verified by the user.
        drone_loc = data.get("drone_location")
        drone_rot = data.get("drone_rotation")
        cam_loc = data.get("camera_location")
        cam_rot = data.get("camera_rotation")
        cam_fov = data.get("camera_fov", 90.0)
        # JSON'dan eski (hatali) noktalari almak yerine,
        # guncellenmis milimetrik CAD verileriyle taze taze hesapliyoruz!
        keypoints_2d = None
        if drone_loc and drone_rot and cam_loc and cam_rot:
            try:
                keypoints_2d = calculate_keypoints_2d(drone_loc, drone_rot, cam_loc, cam_rot, cam_fov)
            except Exception as e:
                print(f"[ERROR] Failed to recalculate keypoints for {filename}: {e}")
                
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
            
            dot_radius = data.get("dot_radius", 6)
            for kp_name, coord in projected_points.items():
                px, py = coord
                color = KEYPOINT_COLORS[kp_name]
                out_w = 2 if dot_radius >= 4 else 1
                draw_ann.ellipse([px - dot_radius, py - dot_radius, px + dot_radius, py + dot_radius], fill=color, outline=(255, 255, 255), width=out_w)
                
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


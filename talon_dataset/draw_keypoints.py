import os
import json
import math
from PIL import Image, ImageDraw

KEYPOINT_COLORS = {
    "nose":             (30, 100, 250),   # Blue
    "left_wingtip":     (255, 30, 30),    # Red
    "right_wingtip":    (255, 100, 200),  # Pink
    "tail":             (255, 120, 0),    # Orange
    "left_tail_fin":    (255, 215, 0),    # Yellow
    "right_tail_fin":   (0, 200, 80)      # Green
}

# EXACT UNREAL ENGINE COORDINATES FROM 3D MESHES (in UE Centimeters)
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

def rotate_vector_ue(x, y, z, pitch, yaw, roll):
    R = get_unreal_matrix(pitch, yaw, roll)
    rx = x * R[0][0] + y * R[0][1] + z * R[0][2]
    ry = x * R[1][0] + y * R[1][1] + z * R[1][2]
    rz = x * R[2][0] + y * R[2][1] + z * R[2][2]
    return rx, ry, rz

def project_world_to_screen(world_pt, cam_loc, cam_rot, cam_fov=90.0, width=1920, height=1080):
    vx = world_pt[0] - cam_loc["x"]
    vy = world_pt[1] - cam_loc["y"]
    vz = world_pt[2] - cam_loc["z"]
    
    R = get_unreal_matrix(cam_rot['pitch'], cam_rot['yaw'], cam_rot['roll'])
    
    x_local = vx * R[0][0] + vy * R[1][0] + vz * R[2][0]
    y_local = vx * R[0][1] + vy * R[1][1] + vz * R[2][1]
    z_local = vx * R[0][2] + vy * R[1][2] + vz * R[2][2]
    
    if x_local <= 0:
        return -1, -1
        
    focal_length = (width / 2.0) / math.tan(math.radians(cam_fov / 2.0))
    u = (width / 2.0) + (y_local / x_local) * focal_length
    v = (height / 2.0) - (z_local / x_local) * focal_length
    
    return u, v

def calculate_keypoints_2d(drone_loc, drone_rot, cam_loc, cam_rot, cam_fov=90.0):
    kps_2d = {}
    for name, cad in RAW_CAD_DATA.items():
        # APPLYING THE 1.422 IN-GAME DRONE SCALE FACTOR
        ue_x = cad["x"] * 1.422
        ue_y = cad["y"] * 1.422
        ue_z = cad["z"] * 1.422
        
        rx, ry, rz = rotate_vector_ue(
            ue_x, ue_y, ue_z,
            drone_rot["pitch"], drone_rot["yaw"], drone_rot["roll"]
        )
        world_pt = (
            drone_loc["x"] + rx,
            drone_loc["y"] + ry,
            drone_loc["z"] + rz
        )
        u, v = project_world_to_screen(world_pt, cam_loc, cam_rot, cam_fov=cam_fov, width=1920, height=1080)
        kps_2d[name] = {"x": u, "y": v}
    return kps_2d

def main():
    workspace_dir = r"c:\Users\Zeylo\Desktop\talon_dataset"
    dataset_dir = os.path.join(workspace_dir, "dataset")
    output_dir = os.path.join(workspace_dir, "dataset_annotated")
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    files = [f for f in os.listdir(dataset_dir) if f.endswith(".png")]
    if not files:
        print(f"[WARNING] No PNG images found in {dataset_dir}.")
        return
        
    print(f"[INFO] Processing {len(files)} images...")
    
    processed_count = 0
    
    for filename in sorted(files):
        base_name = os.path.splitext(filename)[0]
        json_filename = base_name + ".json"
        
        img_path = os.path.join(dataset_dir, filename)
        json_path = os.path.join(dataset_dir, json_filename)
        
        if not os.path.exists(json_path):
            continue
            
        try:
            with open(json_path, "r") as jf:
                data = json.load(jf)
        except Exception as e:
            continue
            
        drone_loc = data.get("drone_location")
        drone_rot = data.get("drone_rotation")
        cam_loc = data.get("camera_location")
        cam_rot = data.get("camera_rotation")
        cam_fov = data.get("camera_fov", 125.0) # Used to be 125.0? Or whatever is in JSON
        
        if not (drone_loc and drone_rot and cam_loc and cam_rot):
            continue
            
        try:
            keypoints_2d = calculate_keypoints_2d(drone_loc, drone_rot, cam_loc, cam_rot, cam_fov)
        except Exception as e:
            continue
            
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
            
            dot_radius = 2
            for kp_name, coord in projected_points.items():
                px, py = coord
                color = KEYPOINT_COLORS.get(kp_name, (255,255,255))
                draw_ann.ellipse([px - dot_radius, py - dot_radius, px + dot_radius, py + dot_radius], fill=color, outline=(255, 255, 255), width=2)
                
            out_ann_path = os.path.join(output_dir, filename)
            print('Saving to:', out_ann_path)
            img_ann.save(out_ann_path)
        except Exception as e:
            print("Error:", e)
            continue
            
        processed_count += 1
        
    print(f"\n[SUCCESS] Render complete! Processed {processed_count} images.")

if __name__ == "__main__":
    main()



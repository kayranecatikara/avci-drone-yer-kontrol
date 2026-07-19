import os
import json
import math
from PIL import Image, ImageDraw

workspace_dir = r"c:\Users\Zeylo\Desktop\talon_dataset"
dataset_dir = os.path.join(workspace_dir, "dataset")

# Newly optimized coordinates
KEYPOINTS_LOCAL = {
    "nose":             {"x": 45.58, "y": 0.0, "z": 0.0},
    "left_wingtip":     {"x": -3.44, "y": 73.874, "z": 0.0},
    "right_wingtip":    {"x": -3.44, "y": -73.874, "z": 0.0},
    "tail":             {"x": -47.30, "y": 0.0, "z": 0.0},
    "left_tail_fin":    {"x": -38.70, "y": 17.20, "z": 18.92},
    "right_tail_fin":   {"x": -38.70, "y": -17.20, "z": 18.92}
}

KEYPOINT_COLORS = {
    "nose":             (30, 100, 250),   # Blue
    "left_wingtip":     (255, 30, 30),    # Red
    "right_wingtip":    (255, 100, 200),  # Pink
    "tail":             (255, 120, 0),    # Orange
    "left_tail_fin":    (255, 215, 0),    # Yellow (fin_up target in f1)
    "right_tail_fin":   (0, 200, 80)      # Green (fin_down target in f1)
}

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

def main():
    img_path = os.path.join(dataset_dir, "talon_0001.png")
    json_path = os.path.join(dataset_dir, "talon_0001.json")
    
    with open(json_path, "r") as f:
        data = json.load(f)
        
    drone_loc = data["drone_location"]
    drone_rot = data["drone_rotation"]
    cam_loc = data["camera_location"]
    cam_rot = data["camera_rotation"]
    cam_fov = data.get("camera_fov", 90.0)
    
    img = Image.open(img_path)
    draw = ImageDraw.Draw(img)
    
    projected_points = {}
    for kp_name, offset in KEYPOINTS_LOCAL.items():
        rx, ry, rz = rotate_vector_ue(offset["x"], offset["y"], offset["z"], drone_rot["pitch"], drone_rot["yaw"], drone_rot["roll"])
        world_pt = (drone_loc["x"] + rx, drone_loc["y"] + ry, drone_loc["z"] + rz)
        u, v = project_world_to_screen(world_pt, cam_loc, cam_rot, fov=cam_fov)
        if u >= 0 and v >= 0:
            projected_points[kp_name] = (int(round(u)), int(round(v)))
            
    def draw_line_safe(pt1_name, pt2_name, color=(128, 128, 128), width=3):
        if pt1_name in projected_points and pt2_name in projected_points:
            draw.line([projected_points[pt1_name], projected_points[pt2_name]], fill=color, width=width)
            
    draw_line_safe("nose", "left_wingtip")
    draw_line_safe("nose", "right_wingtip")
    draw_line_safe("left_wingtip", "tail")
    draw_line_safe("right_wingtip", "tail")
    draw_line_safe("tail", "left_tail_fin")
    draw_line_safe("tail", "right_tail_fin")
    
    for kp_name, coord in projected_points.items():
        px, py = coord
        color = KEYPOINT_COLORS[kp_name]
        draw.ellipse([px - 6, py - 6, px + 6, py + 6], fill=color, outline=(255, 255, 255), width=2)
        
    out_path = os.path.join(workspace_dir, "test_talon_0001_annotated.png")
    img.save(out_path)
    print("Saved test annotated image:", out_path)
    
    # Save a cropped version around the tail
    crop_img = img.crop((900, 400, 1100, 600))
    crop_path = os.path.join(workspace_dir, "test_talon_0001_tail_crop.png")
    crop_img.save(crop_path)
    print("Saved test annotated tail crop:", crop_path)

if __name__ == "__main__":
    main()

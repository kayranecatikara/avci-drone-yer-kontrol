import os
import json
import math
from PIL import Image, ImageDraw, ImageFont

workspace_dir = r"c:\Users\Zeylo\Desktop\talon_dataset"
dataset_dir = os.path.join(workspace_dir, "dataset")

# Load talon_0001
img_path = os.path.join(dataset_dir, "talon_0001.png")
json_path = os.path.join(dataset_dir, "talon_0001.json")

with open(json_path, "r") as f:
    data = json.load(f)

# Coordinates
user_coords = {
    "nose":             {"x": 45.58, "y": 0.0, "z": 0.0},
    "left_wingtip":     {"x": -3.44, "y": 73.874, "z": 0.0},
    "right_wingtip":    {"x": -3.44, "y": -73.874, "z": 0.0},
    "tail":             {"x": -47.30, "y": 0.0, "z": 0.0},
    "left_tail_fin":    {"x": -38.70, "y": 17.20, "z": 18.92},
    "right_tail_fin":   {"x": -38.70, "y": -17.20, "z": 18.92}
}

optimized_coords = {
    "nose":             {"x": 53.583, "y": 0.0, "z": 0.0},
    "left_wingtip":     {"x": 6.086, "y": 71.632, "z": 8.516},
    "right_wingtip":    {"x": 6.086, "y": -71.632, "z": 8.516},
    "tail":             {"x": -40.411, "y": 0.0, "z": 0.0},
    "left_tail_fin":    {"x": -19.465, "y": -18.028, "z": 12.468},
    "right_tail_fin":   {"x": -19.465, "y": 18.028, "z": 12.468}
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

# Draw function
def draw_coords(coords, title):
    img = Image.open(img_path)
    draw = ImageDraw.Draw(img)
    
    drone_loc = data["drone_location"]
    drone_rot = data["drone_rotation"]
    cam_loc = data["camera_location"]
    cam_rot = data["camera_rotation"]
    
    projected = {}
    for name, offset in coords.items():
        rx, ry, rz = rotate_vector_ue(offset["x"], offset["y"], offset["z"], drone_rot["pitch"], drone_rot["yaw"], drone_rot["roll"])
        world_pt = (drone_loc["x"] + rx, drone_loc["y"] + ry, drone_loc["z"] + rz)
        u, v = project_world_to_screen(world_pt, cam_loc, cam_rot)
        if u >= 0 and v >= 0:
            projected[name] = (int(round(u)), int(round(v)))
            
    # Draw skeleton
    def draw_line(p1, p2):
        if p1 in projected and p2 in projected:
            draw.line([projected[p1], projected[p2]], fill=(128, 128, 128), width=3)
            
    draw_line("nose", "left_wingtip")
    draw_line("nose", "right_wingtip")
    draw_line("left_wingtip", "tail")
    draw_line("right_wingtip", "tail")
    draw_line("tail", "left_tail_fin")
    draw_line("tail", "right_tail_fin")
    
    colors = {
        "nose": (30, 100, 250),
        "left_wingtip": (255, 30, 30),
        "right_wingtip": (255, 100, 200),
        "tail": (255, 120, 0),
        "left_tail_fin": (255, 215, 0),
        "right_tail_fin": (0, 200, 80)
    }
    
    for name, pt in projected.items():
        draw.ellipse([pt[0]-6, pt[1]-6, pt[0]+6, pt[1]+6], fill=colors[name], outline=(255, 255, 255), width=2)
        
    # Draw title
    draw.text((50, 50), title, fill=(255, 255, 255))
    
    # Crop around the drone
    # Find bounding box of all projected points
    xs = [pt[0] for pt in projected.values()]
    ys = [pt[1] for pt in projected.values()]
    min_x, max_x = min(xs) - 80, max(xs) + 80
    min_y, max_y = min(ys) - 80, max(ys) + 80
    
    return img.crop((min_x, min_y, max_x, max_y))

# Generate crops
crop_user = draw_coords(user_coords, "User Suggested Coords (Mesh)")
crop_opt = draw_coords(optimized_coords, "Optimized Coords (Perfect Fit)")

# Combine side-by-side
w1, h1 = crop_user.size
w2, h2 = crop_opt.size
combined = Image.new("RGB", (w1 + w2 + 20, max(h1, h2)), (40, 40, 40))
combined.paste(crop_user, (0, 0))
combined.paste(crop_opt, (w1 + 20, 0))

out_path = os.path.join(workspace_dir, "comparison_coordinates.png")
combined.save(out_path)
print("Saved comparison_coordinates.png")

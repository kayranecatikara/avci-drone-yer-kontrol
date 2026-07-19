import os
import json
import glob
import math

try:
    from PIL import Image, ImageDraw
except ImportError:
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
    from PIL import Image, ImageDraw

def ue_rotate_vector(local_pt, pitch_deg, yaw_deg, roll_deg):
    pitch = math.radians(pitch_deg)
    yaw = math.radians(yaw_deg)
    roll = math.radians(roll_deg)
    
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    cr, sr = math.cos(roll), math.sin(roll)
    
    axis_x = (cp*cy, cp*sy, sp)
    axis_y = (sr*sp*cy - cr*sy, sr*sp*sy + cr*cy, -sr*cp)
    axis_z = (-(cr*sp*cy + sr*sy), cy*sr - cr*sp*sy, cr*cp)
    
    rx = local_pt[0]*axis_x[0] + local_pt[1]*axis_y[0] + local_pt[2]*axis_z[0]
    ry = local_pt[0]*axis_x[1] + local_pt[1]*axis_y[1] + local_pt[2]*axis_z[1]
    rz = local_pt[0]*axis_x[2] + local_pt[1]*axis_y[2] + local_pt[2]*axis_z[2]
    
    return rx, ry, rz

def ue_project_to_screen(world_pt, cam_loc, cam_rot, fov, width=1920, height=1080):
    dx = world_pt[0] - cam_loc['x']
    dy = world_pt[1] - cam_loc['y']
    dz = world_pt[2] - cam_loc['z']
    
    pitch = math.radians(cam_rot['pitch'])
    yaw = math.radians(cam_rot['yaw'])
    roll = math.radians(cam_rot['roll'])
    
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    cr, sr = math.cos(roll), math.sin(roll)
    
    axis_x = (cp*cy, cp*sy, sp)
    axis_y = (sr*sp*cy - cr*sy, sr*sp*sy + cr*cy, -sr*cp)
    axis_z = (-(cr*sp*cy + sr*sy), cy*sr - cr*sp*sy, cr*cp)
    
    # Dot product for projection
    cam_x = dx * axis_x[0] + dy * axis_x[1] + dz * axis_x[2]
    cam_y = dx * axis_y[0] + dy * axis_y[1] + dz * axis_y[2]
    cam_z = dx * axis_z[0] + dy * axis_z[1] + dz * axis_z[2]
    
    if cam_x <= 0.01:
        return None # Behind camera
        
    focal_length = (width / 2.0) / math.tan(math.radians(fov / 2.0))
    u = (width / 2.0) + (cam_y / cam_x) * focal_length
    v = (height / 2.0) - (cam_z / cam_x) * focal_length
    
    return (int(u), int(v))

def draw_keypoints(dataset_dir):
    json_files = glob.glob(os.path.join(dataset_dir, "*.json"))
    
    # Exact physical dimensions of the Talon based on new simulation
    # Length: 110cm -> 55cm nose to tail center
    # Wingspan: 171.8cm -> 85.9cm per wing
    KEYPOINTS_LOCAL = {
        "nose": (55.0, 0.0, -15.0),
        "tail": (-55.0, 0.0, -15.0),
        "left_wingtip": (-5.0, 85.9, -12.0),
        "right_wingtip": (-5.0, -85.9, -12.0),
        "left_tail_fin": (-45.0, -22.0, -7.0),
        "right_tail_fin": (-45.0, 22.0, -7.0)
    }
    
    output_dir = os.path.join(os.path.dirname(dataset_dir), "dataset_anotted")
    os.makedirs(output_dir, exist_ok=True)
    
    for json_file in json_files:
        png_file = json_file.replace(".json", ".png")
        if not os.path.exists(png_file):
            continue
            
        with open(json_file, 'r') as f:
            data = json.load(f)
            
        # Prioritize 'drone_location', fallback to 'talon_location'
        talon_loc = data.get("drone_location") or data.get("talon_location")
        talon_rot = data.get("drone_rotation") or data.get("talon_rotation")
        cam_loc = data.get("camera_location") or data.get("avci_camera_location")
        cam_rot = data.get("camera_rotation") or data.get("avci_camera_rotation")
        fov = data.get("camera_fov", 125.0)
        
        if not talon_loc or not cam_loc:
            continue
            
        img = Image.open(png_file)
        draw = ImageDraw.Draw(img)
        
        # Calculate exactly in python
        for name, local_pt in KEYPOINTS_LOCAL.items():
            rx, ry, rz = ue_rotate_vector(local_pt, talon_rot['pitch'], talon_rot['yaw'], talon_rot['roll'])
            world_pt = (talon_loc['x'] + rx, talon_loc['y'] + ry, talon_loc['z'] + rz)
            
            screen_pt = ue_project_to_screen(world_pt, cam_loc, cam_rot, fov, img.width, img.height)
            
            if screen_pt:
                px, py = screen_pt
                draw.ellipse((px-3, py-3, px+3, py+3), fill="red", outline="white")
                draw.text((px+5, py-10), name, fill="yellow")
                
        output_file = os.path.join(output_dir, os.path.basename(png_file).replace(".png", "_marked.png"))
        img.save(output_file, "PNG")
        print(f"Calculated & Marked: {output_file}")

if __name__ == "__main__":
    dataset_directory = r"C:\Users\Zeylo\Desktop\talon_dataset\dataset"
    draw_keypoints(dataset_directory)

import os
import json
import math
import glob
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk, ImageDraw

dataset_dir = r'C:\Users\Zeylo\Desktop\talon_dataset\dataset'
files = glob.glob(os.path.join(dataset_dir, '*.png'))
if not files:
    print('No images found!')
    exit()

latest_png = max(files, key=os.path.getmtime)
latest_json = latest_png.replace('.png', '.json')

with open(latest_json, 'r') as f:
    data = json.load(f)

drone_loc = data['drone_location']
drone_rot = data['drone_rotation']
cam_loc = data['camera_location']
cam_rot = data['camera_rotation']
fov = data.get('camera_fov', 125.0)

original_img = Image.open(latest_png).copy()

# Default CAD points (starting points)
cad_data = {
    "nose": {"x": 55.0, "y": 0.0, "z": 0.0},
    "left_wingtip": {"x": 0.0, "y": 85.9, "z": 0.0},
    "right_wingtip": {"x": 0.0, "y": -85.9, "z": 0.0},
    "tail": {"x": -55.0, "y": 0.0, "z": 0.0},
    "left_tail_fin": {"x": -35.0, "y": 20.0, "z": 5.0},
    "right_tail_fin": {"x": -35.0, "y": -20.0, "z": 5.0}
}

# Try to load if already saved
save_file = r'C:\Users\Zeylo\Desktop\talon_dataset\perfect_keypoints.json'
if os.path.exists(save_file):
    with open(save_file, 'r') as f:
        cad_data = json.load(f)

def rotate_vector_ue(x, y, z, pitch_deg, yaw_deg, roll_deg):
    p = math.radians(pitch_deg)
    y_ = math.radians(yaw_deg)
    r = math.radians(roll_deg)
    SP, CP = math.sin(p), math.cos(p)
    SY, CY = math.sin(y_), math.cos(y_)
    SR, CR = math.sin(r), math.cos(r)
    ax_x = CP * CY; ax_y = CP * SY; ax_z = SP
    ay_x = SR * SP * CY - CR * SY; ay_y = SR * SP * SY + CR * CY; ay_z = -SR * CP
    az_x = -(CR * SP * CY + SR * SY); az_y = SR * CY - CR * SP * SY; az_z = CR * CP
    rx = x * ax_x + y * ay_x + z * ax_z
    ry = x * ax_y + y * ay_y + z * az_y
    rz = x * ax_z + y * ay_z + z * az_z
    return rx, ry, rz

def project_world_to_screen(world_pt, c_loc, c_rot, cam_fov, width=1920, height=1080):
    dx = world_pt[0] - c_loc['x']
    dy = world_pt[1] - c_loc['y']
    dz = world_pt[2] - c_loc['z']
    p = math.radians(c_rot['pitch'])
    yaw = math.radians(c_rot['yaw'])
    r = math.radians(c_rot['roll'])
    SP, CP = math.sin(p), math.cos(p)
    SY, CY = math.sin(yaw), math.cos(yaw)
    SR, CR = math.sin(r), math.cos(r)
    fwd_x = CP * CY; fwd_y = CP * SY; fwd_z = SP
    right_x = SR * SP * CY - CR * SY; right_y = SR * SP * SY + CR * CY; right_z = -SR * CP
    up_x = -(CR * SP * CY + SR * SY); up_y = SR * CY - CR * SP * SY; up_z = CR * CP
    cam_fwd   = dx * fwd_x   + dy * fwd_y   + dz * fwd_z
    cam_right = dx * right_x + dy * right_y + dz * right_z
    cam_up    = dx * up_x    + dy * up_y    + dz * up_z
    if cam_fwd <= 0: return -1, -1
    focal = (width / 2.0) / math.tan(math.radians(cam_fov / 2.0))
    u = (width / 2.0) + (cam_right / cam_fwd) * focal
    v = (height / 2.0) - (cam_up    / cam_fwd) * focal
    return u, v

root = tk.Tk()
root.title("Talon Keypoint Tuner (GUI Hilesi)")

canvas = tk.Canvas(root, width=1280, height=720)
canvas.pack(side=tk.LEFT)

# Resize for preview
preview_img = original_img.resize((1280, 720), Image.Resampling.LANCZOS)
tk_img = ImageTk.PhotoImage(preview_img)
img_id = canvas.create_image(0, 0, anchor=tk.NW, image=tk_img)

control_frame = tk.Frame(root)
control_frame.pack(side=tk.RIGHT, fill=tk.Y)

sliders = {}

def update_image(*args):
    # Get values
    for name in cad_data:
        cad_data[name]['x'] = sliders[name]['x'].get()
        cad_data[name]['y'] = sliders[name]['y'].get()
        cad_data[name]['z'] = sliders[name]['z'].get()
        
    img_copy = preview_img.copy()
    draw = ImageDraw.Draw(img_copy)
    
    kps_2d = {}
    for name, cad in cad_data.items():
        rx, ry, rz = rotate_vector_ue(cad['x'], cad['y'], cad['z'], drone_rot['pitch'], drone_rot['yaw'], drone_rot['roll'])
        wpt = (drone_loc['x'] + rx, drone_loc['y'] + ry, drone_loc['z'] + rz)
        u, v = project_world_to_screen(wpt, cam_loc, cam_rot, fov)
        # scale to 1280x720
        u = u * (1280/1920)
        v = v * (720/1080)
        kps_2d[name] = (u, v)
        if u > 0 and v > 0:
            draw.ellipse([u-4, v-4, u+4, v+4], fill='red', outline='white')
            
    def dl(p1, p2):
        if p1 in kps_2d and p2 in kps_2d:
            u1,v1 = kps_2d[p1]; u2,v2 = kps_2d[p2]
            if u1>0 and v1>0 and u2>0 and v2>0:
                draw.line([u1,v1,u2,v2], fill='green', width=2)
                
    dl('nose', 'left_wingtip'); dl('nose', 'right_wingtip')
    dl('left_wingtip', 'tail'); dl('right_wingtip', 'tail')
    
    global tk_img
    tk_img = ImageTk.PhotoImage(img_copy)
    canvas.itemconfig(img_id, image=tk_img)

for name in cad_data:
    lbl = tk.Label(control_frame, text=name.upper(), font=('Arial', 10, 'bold'))
    lbl.pack(pady=(10,0))
    sliders[name] = {}
    for axis in ['x', 'y', 'z']:
        frame = tk.Frame(control_frame)
        frame.pack(fill=tk.X)
        tk.Label(frame, text=axis.upper()).pack(side=tk.LEFT)
        var = tk.DoubleVar(value=cad_data[name][axis])
        # Allow wide range of offsets
        s = ttk.Scale(frame, from_=-200.0, to=200.0, orient=tk.HORIZONTAL, variable=var, command=update_image)
        s.pack(side=tk.RIGHT, expand=True, fill=tk.X)
        sliders[name][axis] = var

def save_points():
    with open(save_file, 'w') as f:
        json.dump(cad_data, f, indent=4)
    print("SAVED TO:", save_file)
    print("You can close the GUI now.")

tk.Button(control_frame, text="SAVE PERFECT KEYPOINTS", command=save_points, bg='green', fg='white', font=('Arial', 12, 'bold')).pack(pady=20)

update_image()
root.mainloop()

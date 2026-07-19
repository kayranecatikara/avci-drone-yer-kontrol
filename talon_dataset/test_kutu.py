import json
from PIL import Image, ImageDraw
import sys
import math

def rotate_vector_ue(x, y, z, pitch, yaw, roll):
    rad_pitch = math.radians(pitch)
    rad_yaw = math.radians(yaw)
    rad_roll = math.radians(roll)
    SP = math.sin(rad_pitch); CP = math.cos(rad_pitch)
    SY = math.sin(rad_yaw); CY = math.cos(rad_yaw)
    SR = math.sin(rad_roll); CR = math.cos(rad_roll)
    r00 = CP * CY; r10 = CP * SY; r20 = SP
    r01 = SR * SP * CY - CR * SY; r11 = SR * SP * SY + CR * CY; r21 = -SR * CP
    r02 = -(CR * SP * CY + SR * SY); r12 = SR * CY - CR * SP * SY; r22 = CR * CP
    rx = x * r00 + y * r01 + z * r02
    ry = x * r10 + y * r11 + z * r12
    rz = x * r20 + y * r21 + z * r22
    return rx, ry, rz

def project_world_to_screen(world_pt, cam_loc, cam_rot, fov=125.0, width=1920, height=1080):
    dx = world_pt[0] - cam_loc["x"]
    dy = world_pt[1] - cam_loc["y"]
    dz = world_pt[2] - cam_loc["z"]
    rx, ry, rz = rotate_vector_ue(dx, dy, dz, -cam_rot["pitch"], -cam_rot["yaw"], -cam_rot["roll"])
    if rx <= 0.01:
        rx = 0.01
    fov_rad = math.radians(fov)
    half_fov = fov_rad / 2.0
    plane_dist = (width / 2.0) / math.tan(half_fov)
    u = (ry / rx) * plane_dist + (width / 2.0)
    v = -(rz / rx) * plane_dist + (height / 2.0)
    return u, v

with open(r'C:\Users\Zeylo\Desktop\talon_dataset\dataset\talon_0004.json', 'r') as f:
    data = json.load(f)

img = Image.open(r'C:\Users\Zeylo\Desktop\talon_dataset\dataset\talon_0004.png')
draw = ImageDraw.Draw(img)

# Unscaled keypoints
KEYPOINTS = {
    "nose":             {"x": 49.476, "y": 0.0, "z": 0.0},
    "left_wingtip":     {"x": -0.074, "y": 74.737, "z": 3.716},
    "right_wingtip":    {"x": -0.074, "y": -74.737, "z": 3.716},
    "tail":             {"x": -42.801, "y": 0.0, "z": 0.0},
    "left_tail_fin":    {"x": -28.011, "y": -19.411, "z": 8.164},
    "right_tail_fin":   {"x": -28.011, "y": 19.411, "z": 8.164}
}

pts = {}
drone_rot = data['drone_rotation']
drone_loc = data['drone_location']
cam_loc = data['camera_location']
cam_rot = data['camera_rotation']
cam_fov = data['camera_fov']

for name, kp in KEYPOINTS.items():
    rx, ry, rz = rotate_vector_ue(kp['x'], kp['y'], kp['z'], drone_rot['pitch'], drone_rot['yaw'], drone_rot['roll'])
    world_pt = (drone_loc['x'] + rx, drone_loc['y'] + ry, drone_loc['z'] + rz)
    u, v = project_world_to_screen(world_pt, cam_loc, cam_rot, fov=cam_fov)
    pts[name] = (u, v)

# draw box
xs = [p[0] for p in pts.values()]
ys = [p[1] for p in pts.values()]
draw.rectangle([min(xs), min(ys), max(xs), max(ys)], outline=(0,255,0), width=4)

# draw points
for name, p in pts.items():
    draw.ellipse([p[0]-5, p[1]-5, p[0]+5, p[1]+5], fill=(255,0,0))

out_path = r'C:\Users\Zeylo\Desktop\KUTU_TESTI.png'
img.save(out_path)

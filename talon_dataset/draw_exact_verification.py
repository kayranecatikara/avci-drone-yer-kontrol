import os
import json
import math
from PIL import Image, ImageDraw

def project_world_to_screen(world_pt, cam_loc, cam_rot, fov=90.0, width=1920, height=1080):
    """UE FRotator ile birebir ayni projeksiyon."""
    vx = world_pt[0] - cam_loc['x']
    vy = world_pt[1] - cam_loc['y']
    vz = world_pt[2] - cam_loc['z']
    
    rad_pitch = math.radians(cam_rot['pitch'])
    rad_yaw   = math.radians(-cam_rot['yaw'])
    rad_roll  = math.radians(cam_rot['roll'])
    
    SP = math.sin(rad_pitch); CP = math.cos(rad_pitch)
    SY = math.sin(rad_yaw);   CY = math.cos(rad_yaw)
    SR = math.sin(rad_roll);  CR = math.cos(rad_roll)
    
    r00 = CP*CY;  r01 = -CP*SY; r02 = SP
    r10 = SR*SP*CY+CR*SY; r11 = -SR*SP*SY+CR*CY; r12 = -SR*CP
    r20 = -CR*SP*CY+SR*SY; r21 = CR*SP*SY+SR*CY;  r22 = CR*CP
    
    x_local = vx*r00 + vy*r01 + vz*r02
    y_local = vx*r10 + vy*r11 + vz*r12
    z_local = vx*r20 + vy*r21 + vz*r22
    
    if x_local <= 0:
        return -1.0, -1.0
        
    focal = (width / 2.0) / math.tan(math.radians(fov / 2.0))
    u = (width  / 2.0) + (y_local / x_local) * focal
    v = (height / 2.0) - (z_local / x_local) * focal
    return u, v

KEYPOINT_COLORS = {
    "nose":           (30,  100, 250),
    "left_wingtip":   (255,  30,  30),
    "right_wingtip":  (255, 100, 200),
    "tail":           (255, 120,   0),
    "belly":          (0,   255, 255),
    "left_tail_fin":  (255, 215,   0),
    "right_tail_fin": (0,   200,  80),
}

def main():
    base_dir  = r"c:\Users\Zeylo\Desktop\talon_dataset\dataset"
    img_path  = os.path.join(base_dir, "talon_0182.png")
    json_path = os.path.join(base_dir, "talon_0182.json")
    
    with open(json_path, 'r') as f:
        data = json.load(f)
        
    cam_loc = data["camera_location"]
    cam_rot = data["camera_rotation"]
    fov     = data.get("camera_fov", 125.0)
    kps3d   = data.get("keypoints_3d", {})

    img  = Image.open(img_path)
    draw = ImageDraw.Draw(img)
    W, H = img.size

    print(f"JSON'daki keypoints_3d dogrudan kullaniliyor ({len(kps3d)} nokta)\n")

    points_drawn = []
    for name, kp in kps3d.items():
        world_pt = (kp["x"], kp["y"], kp["z"])
        u, v = project_world_to_screen(world_pt, cam_loc, cam_rot, fov, W, H)
        
        print(f"  {name:20s}: world=({kp['x']:.1f},{kp['y']:.1f},{kp['z']:.1f})  -> screen=({u:.1f},{v:.1f})")
        
        if 0 < u < W and 0 < v < H:
            c = KEYPOINT_COLORS.get(name, (255, 255, 255))
            r = 8
            draw.ellipse([u-r, v-r, u+r, v+r], fill=c, outline=(255,255,255), width=2)
            draw.text((u+r+3, v-r), name, fill=c)
            points_drawn.append((u, v))
        else:
            print(f"    ^ EKRAN DISINDA!")
            
    out_path = r"c:\Users\Zeylo\Desktop\talon_dataset\SON_CEKILEN_ONIZLEME.png"
    img.save(out_path)
    print(f"\nKaydedildi: {out_path}")
    
    if points_drawn:
        min_x = min(p[0] for p in points_drawn)
        max_x = max(p[0] for p in points_drawn)
        min_y = min(p[1] for p in points_drawn)
        max_y = max(p[1] for p in points_drawn)
        margin = 150
        crop_box = (max(0,int(min_x)-margin), max(0,int(min_y)-margin),
                    min(W,int(max_x)+margin), min(H,int(max_y)+margin))
        img.crop(crop_box).save(r"c:\Users\Zeylo\Desktop\talon_dataset\_zoom_kp.png")
        print(f"Zoom kaydedildi.")

if __name__ == '__main__':
    main()

import os
import json
import math
import shutil

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(WORKSPACE_DIR, "dataset")
OUTPUT_DIR = os.path.join(WORKSPACE_DIR, "dataset_auto_bbox")

IMG_WIDTH = 1920
IMG_HEIGHT = 1080

DRONE_SCALE = 1.422

RAW_CAD_DATA = {
    "nose":           {"x":  69.13, "y":   0.19, "z":  -2.77},
    "left_wingtip":   {"x":   1.65, "y": -99.93, "z":   5.81},
    "right_wingtip":  {"x":   1.65, "y":  99.93, "z":   5.81},
    "tail":           {"x": -55.38, "y":   0.10, "z":   0.10},
    "left_tail_fin":  {"x": -43.17, "y": -28.25, "z":  16.98},
    "right_tail_fin": {"x": -43.17, "y":  28.25, "z":  16.98},
}

def get_unreal_matrix(pitch, yaw, roll):
    SP, CP = math.sin(math.radians(pitch)), math.cos(math.radians(pitch))
    SY, CY = math.sin(math.radians(yaw)),   math.cos(math.radians(yaw))
    SR, CR = math.sin(math.radians(roll)),  math.cos(math.radians(roll))
    r00 = CP * CY;  r10 = CP * SY;  r20 = SP
    r01 = SR*SP*CY - CR*SY;  r11 = SR*SP*SY + CR*CY;  r21 = -SR*CP
    r02 = -(CR*SP*CY + SR*SY); r12 = CY*SR - CR*SP*SY; r22 = CR*CP
    return [[r00, r01, r02], [r10, r11, r12], [r20, r21, r22]]

def rotate_vector_ue(x, y, z, pitch, yaw, roll):
    R  = get_unreal_matrix(pitch, yaw, roll)
    rx = x*R[0][0] + y*R[0][1] + z*R[0][2]
    ry = x*R[1][0] + y*R[1][1] + z*R[1][2]
    rz = x*R[2][0] + y*R[2][1] + z*R[2][2]
    return rx, ry, rz

def project_world_to_screen(world_pt, cam_loc, cam_rot, cam_fov=125.0, width=IMG_WIDTH, height=IMG_HEIGHT):
    vx = world_pt[0] - cam_loc["x"]
    vy = world_pt[1] - cam_loc["y"]
    vz = world_pt[2] - cam_loc["z"]
    R = get_unreal_matrix(cam_rot["pitch"], cam_rot["yaw"], cam_rot["roll"])
    x_local = vx*R[0][0] + vy*R[1][0] + vz*R[2][0]
    y_local = vx*R[0][1] + vy*R[1][1] + vz*R[2][1]
    z_local = vx*R[0][2] + vy*R[1][2] + vz*R[2][2]
    if x_local <= 0:
        return -1.0, -1.0
    focal_length = (width / 2.0) / math.tan(math.radians(cam_fov / 2.0))
    u = (width  / 2.0) + (y_local / x_local) * focal_length
    v = (height / 2.0) - (z_local / x_local) * focal_length
    return u, v

def compute_keypoints(data):
    cam_loc = data.get("camera_location")
    cam_rot = data.get("camera_rotation")
    cam_fov = float(data.get("camera_fov", 125.0))
    if not (cam_loc and cam_rot):
        return []
    
    kps_3d = data.get("keypoints_3d", {})
    points = []
    for name in RAW_CAD_DATA.keys():
        if name in kps_3d:
            wp = kps_3d[name]
            u, v = project_world_to_screen((wp["x"], wp["y"], wp["z"]), cam_loc, cam_rot, cam_fov)
        else:
            drone_loc = data.get("drone_location")
            drone_rot = data.get("drone_rotation")
            if not (drone_loc and drone_rot): continue
            cad = RAW_CAD_DATA[name]
            lx, ly, lz = cad["x"]*DRONE_SCALE, cad["y"]*DRONE_SCALE, cad["z"]*DRONE_SCALE
            rx, ry, rz = rotate_vector_ue(lx, ly, lz, drone_rot["pitch"], drone_rot["yaw"], drone_rot["roll"])
            u, v = project_world_to_screen((drone_loc["x"]+rx, drone_loc["y"]+ry, drone_loc["z"]+rz), cam_loc, cam_rot, cam_fov)
        
        if u >= 0 and v >= 0:
            points.append((u, v))
    return points

def calculate_bbox(pts, img_w, img_h):
    if not pts: return None
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)

    w_raw = xmax - xmin
    h_raw = ymax - ymin

    # 10% padding
    pad_x = w_raw * 0.10
    pad_y = h_raw * 0.10

    bbox_xmin = max(0.0, xmin - pad_x)
    bbox_xmax = min(float(img_w), xmax + pad_x)
    bbox_ymin = max(0.0, ymin - pad_y)
    bbox_ymax = min(float(img_h), ymax + pad_y)

    bbox_w = bbox_xmax - bbox_xmin
    bbox_h = bbox_ymax - bbox_ymin
    bbox_cx = bbox_xmin + (bbox_w / 2.0)
    bbox_cy = bbox_ymin + (bbox_h / 2.0)

    norm_cx = bbox_cx / img_w
    norm_cy = bbox_cy / img_h
    norm_w = bbox_w / img_w
    norm_h = bbox_h / img_h

    # Return cx, cy, w, h
    return norm_cx, norm_cy, norm_w, norm_h

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    images_dir = os.path.join(OUTPUT_DIR, "images")
    labels_dir = os.path.join(OUTPUT_DIR, "labels")
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(labels_dir, exist_ok=True)

    files = [f for f in os.listdir(DATASET_DIR) if f.endswith(".png")]
    count = 0
    for filename in sorted(files):
        base_name = os.path.splitext(filename)[0]
        json_path = os.path.join(DATASET_DIR, base_name + ".json")
        png_path = os.path.join(DATASET_DIR, filename)

        if not os.path.exists(json_path): continue

        try:
            with open(json_path, "r", encoding="utf-8") as jf:
                data = json.load(jf)
        except Exception:
            continue

        pts = compute_keypoints(data)
        if len(pts) < 3: # Need at least a few points to form a box
            continue

        bbox = calculate_bbox(pts, IMG_WIDTH, IMG_HEIGHT)
        if bbox is None: continue

        cx, cy, w, h = bbox
        
        # YOLO detection format: 0 cx cy w h
        label_line = f"0 {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}\n"

        # Copy image
        shutil.copy2(png_path, os.path.join(images_dir, filename))
        
        # Write label
        with open(os.path.join(labels_dir, base_name + ".txt"), "w", encoding="utf-8") as lf:
            lf.write(label_line)

        count += 1
        
    yaml_content = f"""path: {OUTPUT_DIR.replace('\\\\', '/')}
train: images
val: images

names:
  0: talon
"""
    with open(os.path.join(OUTPUT_DIR, "data.yaml"), 'w', encoding='utf-8') as f:
        f.write(yaml_content)

    print(f"BBox calculation complete! {count} files exported to {OUTPUT_DIR}")

if __name__ == "__main__":
    main()

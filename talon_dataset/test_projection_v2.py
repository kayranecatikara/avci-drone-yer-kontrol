"""
Talon Keypoint Projeksiyon Testi v2
------------------------------------
Bu script son çekilen PNG + JSON'u alır, 
UE5'in gerçek dünya koordinat sistemine göre noktaları hesaplar
ve üzerine çizer.

UE5 Koordinat sistemi:
  X = İleri (Forward)
  Y = Sağ (Right)  
  Z = Yukarı (Up)

SDK'dan alınan Talon boyutları:
  Gövde uzunluğu: 1100 mm = 110 cm = 110 UE unit (1 UE unit = 1 cm)
  Kanat açıklığı: 1718 mm = 171.8 cm = 171.8 UE unit
"""

import os, json, math, glob
from PIL import Image, ImageDraw, ImageFont

# ============================================================
# TALON LOCAL KEYPOINTS — UE5 Actor Local Space
# X = İleri (burun yönü), Y = Sol (negatif = sağ), Z = Yukarı
# Pivot noktası: Actor'un merkezi (ağırlık merkezi civarı)
# SDK: 1100mm gövde, 1718mm kanat açıklığı
# ============================================================
KEYPOINTS_LOCAL = {
    "nose":           {"x":  55.0,  "y":  0.0,    "z":  0.0},
    "left_wingtip":   {"x":  0.0,   "y":  85.9,   "z":  0.0},
    "right_wingtip":  {"x":  0.0,   "y": -85.9,   "z":  0.0},
    "tail":           {"x": -55.0,  "y":  0.0,    "z":  0.0},
    "left_tail_fin":  {"x": -35.0,  "y":  20.0,   "z":  5.0},
    "right_tail_fin": {"x": -35.0,  "y": -20.0,   "z":  5.0},
}

def ue_rotate(x, y, z, pitch_deg, yaw_deg, roll_deg):
    """UE5 FRotator::RotateVector — tam UE implementasyonu"""
    p = math.radians(pitch_deg)
    y_ = math.radians(yaw_deg)
    r = math.radians(roll_deg)
    SP, CP = math.sin(p), math.cos(p)
    SY, CY = math.sin(y_), math.cos(y_)
    SR, CR = math.sin(r), math.cos(r)

    # UE5 rotation matrix columns
    ax_x = CP * CY
    ax_y = CP * SY
    ax_z = SP

    ay_x = SR * SP * CY - CR * SY
    ay_y = SR * SP * SY + CR * CY
    ay_z = -SR * CP

    az_x = -(CR * SP * CY + SR * SY)
    az_y = SR * CY - CR * SP * SY
    az_z = CR * CP

    rx = x * ax_x + y * ay_x + z * az_x
    ry = x * ax_y + y * ay_y + z * az_y
    rz = x * ax_z + y * ay_z + z * az_z
    return rx, ry, rz


def project_to_screen(world_x, world_y, world_z,
                       cam_x, cam_y, cam_z,
                       cam_pitch, cam_yaw, cam_roll,
                       fov_deg, img_w=1920, img_h=1080):
    """
    UE5 dünya koordinatını ekran pikseline çevirir.
    UE5 kamera view matrix (sağ el, Z yukarı).
    """
    # Kameraya göre fark vektörü
    dx = world_x - cam_x
    dy = world_y - cam_y
    dz = world_z - cam_z

    p = math.radians(cam_pitch)
    yaw = math.radians(cam_yaw)
    r = math.radians(cam_roll)

    SP, CP = math.sin(p), math.cos(p)
    SY, CY = math.sin(yaw), math.cos(yaw)
    SR, CR = math.sin(r), math.cos(r)

    # UE5 inverse rotation (transpose of rotation matrix)
    # Forward (X camera) = kameranın baktığı yön
    fwd_x = CP * CY
    fwd_y = CP * SY
    fwd_z = SP

    # Right (Y camera) = kameranın sağı
    right_x = SR * SP * CY - CR * SY
    right_y = SR * SP * SY + CR * CY
    right_z = -SR * CP

    # Up (Z camera) = kameranın yukarısı
    up_x = -(CR * SP * CY + SR * SY)
    up_y = SR * CY - CR * SP * SY
    up_z = CR * CP

    # Kamera uzayına çevir
    cam_fwd   = dx * fwd_x   + dy * fwd_y   + dz * fwd_z
    cam_right = dx * right_x + dy * right_y + dz * right_z
    cam_up    = dx * up_x    + dy * up_y    + dz * up_z

    # Arkada ise geçersiz
    if cam_fwd <= 0:
        return None, None

    # Perspektif projeksiyon
    focal = (img_w / 2.0) / math.tan(math.radians(fov_deg / 2.0))
    u = (img_w  / 2.0) + (cam_right / cam_fwd) * focal
    v = (img_h / 2.0) - (cam_up    / cam_fwd) * focal
    return u, v


# ============================================================
# En son PNG'yi ve JSON'u bul
# ============================================================
dataset_dir = r'C:\Users\Zeylo\Desktop\talon_dataset\dataset'
pngs = glob.glob(os.path.join(dataset_dir, '*.png'))
if not pngs:
    print("Dataset klasöründe PNG yok!")
    exit()

latest_png = max(pngs, key=os.path.getmtime)
latest_json = latest_png.replace('.png', '.json')
if not os.path.exists(latest_json):
    print(f"JSON bulunamadı: {latest_json}")
    exit()

with open(latest_json) as f:
    data = json.load(f)

dl = data['drone_location']
dr = data['drone_rotation']
cl = data['camera_location']
cr = data['camera_rotation']
fov = data.get('camera_fov', 125.0)

print(f"Drone Loc:  X={dl['x']:.1f}  Y={dl['y']:.1f}  Z={dl['z']:.1f}")
print(f"Drone Rot:  P={dr['pitch']:.2f}  Yaw={dr['yaw']:.2f}  Roll={dr['roll']:.2f}")
print(f"Cam Loc:    X={cl['x']:.1f}  Y={cl['y']:.1f}  Z={cl['z']:.1f}")
print(f"Cam Rot:    P={cr['pitch']:.2f}  Yaw={cr['yaw']:.2f}  Roll={cr['roll']:.2f}")
print(f"FOV: {fov}")
print()

# ============================================================
# Her keypoint için dünya koordinatını ve piksel pozisyonunu hesapla
# ============================================================
img = Image.open(latest_png)
draw = ImageDraw.Draw(img)

COLORS = {
    "nose":           (255, 80,  80),   # kırmızı
    "left_wingtip":   (80,  255, 80),   # yeşil
    "right_wingtip":  (80,  200, 255),  # mavi
    "tail":           (255, 255, 80),   # sarı
    "left_tail_fin":  (255, 140, 0),    # turuncu
    "right_tail_fin": (200, 80,  255),  # mor
}

projected = {}
for name, local in KEYPOINTS_LOCAL.items():
    wx, wy, wz = ue_rotate(
        local['x'], local['y'], local['z'],
        dr['pitch'], dr['yaw'], dr['roll']
    )
    world_x = dl['x'] + wx
    world_y = dl['y'] + wy
    world_z = dl['z'] + wz

    u, v = project_to_screen(
        world_x, world_y, world_z,
        cl['x'], cl['y'], cl['z'],
        cr['pitch'], cr['yaw'], cr['roll'],
        fov
    )
    projected[name] = (u, v)
    print(f"  {name:20s}: world=({world_x:.1f}, {world_y:.1f}, {world_z:.1f})  pixel=({u:.0f}, {v:.0f})")

    if u is not None:
        r = 8
        draw.ellipse([u-r, v-r, u+r, v+r], fill=COLORS[name], outline=(0,0,0), width=2)
        draw.text((u+10, v-10), name[:4], fill=COLORS[name])

# Hatlar
def line(p1, p2, c=(255,255,255)):
    u1,v1 = projected.get(p1, (None,None))
    u2,v2 = projected.get(p2, (None,None))
    if None not in [u1,v1,u2,v2]:
        draw.line([u1,v1,u2,v2], fill=c, width=3)

line("nose", "left_wingtip",  (255,80,80))
line("nose", "right_wingtip", (255,80,80))
line("left_wingtip",  "tail", (80,255,80))
line("right_wingtip", "tail", (80,200,255))
line("tail", "left_tail_fin")
line("tail", "right_tail_fin")

# Bounding box
valid_pts = [(u,v) for u,v in projected.values() if u is not None]
if valid_pts:
    xs = [p[0] for p in valid_pts]
    ys = [p[1] for p in valid_pts]
    draw.rectangle([min(xs), min(ys), max(xs), max(ys)], outline=(0,255,0), width=3)

out = r'C:\Users\Zeylo\Desktop\talon_dataset\TEST_PROJ_V2.png'
img.save(out)
print(f"\nKaydedildi: {out}")

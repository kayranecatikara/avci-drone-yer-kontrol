"""
WIREFRAME DIAGNOSTIC TOOL
--------------------------
Talon GLB mesh'lerini mevcut telemetri + projeksiyon matematigi ile
talon_0182.png uzerine cizer. Sonuca bakarak hata sinifini tespit ederiz:

- Tum sekil kaymis ama oran dogru  --> Pivot offset hatasi
- Sekil gerilmis / sikismis         --> Olcek hatasi
- Sekil yamuk / donmus             --> Rotasyon konvansiyon hatasi
- Merkez iyi, kenarlara gidince kotu --> FOV hatasi
"""

import os, json, math, struct
import numpy as np
from PIL import Image, ImageDraw

# ============================================================
# DOSYA YOLLARI
# ============================================================
DATASET_DIR  = r"c:\Users\Zeylo\Desktop\talon_dataset\dataset"
OUTPUT_PATH  = r"c:\Users\Zeylo\Desktop\talon_dataset\wireframe_diag.png"
ZOOM_PATH    = r"c:\Users\Zeylo\Desktop\talon_dataset\wireframe_diag_zoom.png"
GLB_DIR      = r"C:\Users\Zeylo\Desktop\FModel\Output\Exports\DronesOfWar\Content\Art\Meshes\Talon\V2"

TARGET_IMAGE = "talon_0182"

GLB_FILES = [
    "SM_Talon_Body.glb",
    "SM_Talon_Wing_L.glb",
    "SM_Talon_Wing_R.glb",
    "SM_Talon_Small_Wing_L.glb",
    "SM_Talon_Small_Wing_R.glb",
]

# Her mesh icin farkli renk (ayirt etmek icin)
GLB_COLORS = [
    (0, 200, 255),    # Body   - Cyan
    (255, 80, 80),    # Wing L - Red
    (80, 255, 80),    # Wing R - Green
    (255, 200, 0),    # Small Wing L - Yellow
    (200, 0, 255),    # Small Wing R - Purple
]

# ============================================================
# GLB PARSER - vertex'leri okur
# ============================================================
def read_glb_vertices(path):
    """GLB dosyasindan ham vertex pozisyonlarini okur (cm cinsinden degil, UE native birimde)."""
    with open(path, 'rb') as f:
        magic = f.read(4)
        if magic != b'glTF':
            raise ValueError(f"Gecersiz GLB dosyasi: {path}")
        version = struct.unpack('<I', f.read(4))[0]
        length  = struct.unpack('<I', f.read(4))[0]

        # JSON chunk
        json_len  = struct.unpack('<I', f.read(4))[0]
        json_type = f.read(4)
        json_data = json.loads(f.read(json_len).decode('utf-8'))

        # BIN chunk
        bin_len  = struct.unpack('<I', f.read(4))[0]
        bin_type = f.read(4)
        bin_data = f.read(bin_len)

    gltf = json_data
    vertices = []

    for mesh in gltf.get('meshes', []):
        for prim in mesh.get('primitives', []):
            pos_idx = prim.get('attributes', {}).get('POSITION')
            if pos_idx is None:
                continue
            acc   = gltf['accessors'][pos_idx]
            bv    = gltf['bufferViews'][acc['bufferView']]
            offset = bv.get('byteOffset', 0) + acc.get('byteOffset', 0)
            count  = acc['count']
            stride = bv.get('byteStride', 12)

            for i in range(count):
                start = offset + i * stride
                x, y, z = struct.unpack_from('<fff', bin_data, start)
                vertices.append([x, y, z])

    return np.array(vertices, dtype=np.float32)

# ============================================================
# ROTASYON MATRISI (UE FRotator - Pitch, Yaw, Roll)
# ============================================================
def ue_rotmat(pitch, yaw, roll):
    """Unreal Engine FRotator::ToMatrix() ile birebir ayni."""
    P, Y, R = math.radians(pitch), math.radians(yaw), math.radians(roll)
    CP, SP = math.cos(P), math.sin(P)
    CY, SY = math.cos(Y), math.sin(Y)
    CR, SR = math.cos(R), math.sin(R)
    return np.array([
        [ CP*CY,             CP*SY,            SP     ],
        [ SR*SP*CY - CR*SY,  SR*SP*SY + CR*CY, -SR*CP ],
        [-(CR*SP*CY+SR*SY),  CY*SR - CR*SP*SY,  CR*CP  ]
    ], dtype=np.float64)

# ============================================================
# WORLD -> SCREEN PROJEKSIYON
# ============================================================
def project_points(world_pts, cam_loc, cam_rot, W=1920, H=1080, fov_h=125.0):
    """
    Cok sayida world-space noktayi tek seferde ekrana izdusurur.
    Donus: (N,2) piksel koordinatlari. Kamera arkasindaki noktalar NaN olur.
    """
    M   = ue_rotmat(cam_rot['pitch'], cam_rot['yaw'], cam_rot['roll'])
    d   = world_pts - np.array([cam_loc['x'], cam_loc['y'], cam_loc['z']])
    # Kamera eksenlerine izdusur
    fwd = d @ M[0]   # derinlik (ileri)
    rgt = d @ M[1]   # saga
    up  = d @ M[2]   # yukari

    fx = (W / 2.0) / math.tan(math.radians(fov_h / 2.0))
    px = np.where(fwd > 0, W/2 + fx * (rgt / fwd), np.nan)
    py = np.where(fwd > 0, H/2 - fx * (up  / fwd), np.nan)
    return np.stack([px, py], axis=1)

# ============================================================
# VERTEX SUBSAMPLE (render performansi icin)
# ============================================================
def subsample(verts, max_pts=3000):
    if len(verts) <= max_pts:
        return verts
    idx = np.random.choice(len(verts), max_pts, replace=False)
    return verts[idx]

# ============================================================
# KEYPOINT NOKTALARI (onceki hesapli UE offset'ler - cm)
# ============================================================
KP_OFFSETS = {
    "nose":           np.array([ 56.73,   0.78,  -6.77]),
    "tail":           np.array([-43.45,   0.44,  -4.30]),
    "left_wingtip":   np.array([ 44.64,  51.90,   0.65]),
    "right_wingtip":  np.array([ 44.64, -51.90,   0.65]),
    "left_tail_fin":  np.array([-39.44,  23.80,   8.88]),
    "right_tail_fin": np.array([-39.44, -23.80,   8.88]),
}
KP_COLORS = {
    "nose":           (30,  100, 250),
    "tail":           (255, 120,   0),
    "left_wingtip":   (255,  30,  30),
    "right_wingtip":  (255, 100, 200),
    "left_tail_fin":  (255, 215,   0),
    "right_tail_fin": ( 0,  200,  80),
}

# ============================================================
# MAIN
# ============================================================
def main():
    # --- JSON oku ---
    json_path = os.path.join(DATASET_DIR, TARGET_IMAGE + ".json")
    img_path  = os.path.join(DATASET_DIR, TARGET_IMAGE + ".png")

    with open(json_path, 'r') as f:
        data = json.load(f)

    drone_loc = data["drone_location"]
    drone_rot = data["drone_rotation"]
    cam_loc   = data["camera_location"]
    cam_rot   = data["camera_rotation"]
    fov       = data.get("camera_fov", 125.0)

    print(f"[INFO] Drone: {drone_loc}")
    print(f"[INFO] Drone Rot: {drone_rot}")
    print(f"[INFO] Cam: {cam_loc}")
    print(f"[INFO] Cam Rot: {cam_rot}")
    print(f"[INFO] FOV: {fov}")

    drone_R = ue_rotmat(drone_rot['pitch'], drone_rot['yaw'], drone_rot['roll'])
    drone_origin = np.array([drone_loc['x'], drone_loc['y'], drone_loc['z']])

    # --- Resmi yukle ---
    img  = Image.open(img_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    W, H = img.size

    all_screen_pts = []  # zoom icin bbox hesabi

    # --- Her GLB dosyasini isle ---
    for glb_name, color in zip(GLB_FILES, GLB_COLORS):
        glb_path = os.path.join(GLB_DIR, glb_name)
        if not os.path.exists(glb_path):
            print(f"[WARN] Bulunamadi: {glb_name}, atlaniyor.")
            continue

        print(f"[INFO] Okuyor: {glb_name} ...", end="", flush=True)
        try:
            verts_local = read_glb_vertices(glb_path)
        except Exception as e:
            print(f" HATA: {e}")
            continue
        print(f" {len(verts_local)} vertex")

        # GLB birim varsayimi: UE FModel export'u cm cinsinden
        # Vertex'leri drone world-space'e tasiyoruz:
        # world = drone_origin + (local_vertex @ drone_R)
        verts_sub   = subsample(verts_local, max_pts=4000)
        verts_world = verts_sub @ drone_R.T + drone_origin  # (N,3)

        # Ekrana izdusur
        screen = project_points(verts_world, cam_loc, cam_rot, W, H, fov)

        # Goruntu icindeki noktalar
        valid = (
            ~np.isnan(screen[:, 0]) &
            (screen[:, 0] >= 0) & (screen[:, 0] < W) &
            (screen[:, 1] >= 0) & (screen[:, 1] < H)
        )
        screen_valid = screen[valid]

        print(f"       {len(screen_valid)} nokta ekranda gorunuyor")

        # Ciz (kucuk noktalar)
        for pt in screen_valid:
            x, y = int(pt[0]), int(pt[1])
            draw.ellipse([x-1, y-1, x+1, y+1], fill=color)

        all_screen_pts.extend(screen_valid.tolist())

    # --- Keypoint noktalari ---
    print("\n[INFO] Keypoint'ler hesaplaniyor...")
    for kp_name, offset_local in KP_OFFSETS.items():
        world_pt = drone_origin + drone_R @ offset_local
        pts2d = project_points(world_pt.reshape(1, 3), cam_loc, cam_rot, W, H, fov)
        u, v = pts2d[0]
        if not np.isnan(u) and 0 <= u < W and 0 <= v < H:
            c = KP_COLORS[kp_name]
            r = 7
            draw.ellipse([u-r, v-r, u+r, v+r], fill=c, outline=(255,255,255), width=2)
            draw.text((u+r+2, v-r), kp_name, fill=c)
            all_screen_pts.append([u, v])
            print(f"  {kp_name}: ({u:.1f}, {v:.1f})")
        else:
            print(f"  {kp_name}: EKRAN DISINDA")

    # --- Kaydet ---
    img.save(OUTPUT_PATH)
    print(f"\n[OK] Wireframe kaydedildi: {OUTPUT_PATH}")

    # --- Zoom ---
    if all_screen_pts:
        pts_arr = np.array(all_screen_pts)
        mn_x, mn_y = pts_arr[:, 0].min(), pts_arr[:, 1].min()
        mx_x, mx_y = pts_arr[:, 0].max(), pts_arr[:, 1].max()
        margin = 120
        box = (
            max(0,  int(mn_x) - margin),
            max(0,  int(mn_y) - margin),
            min(W,  int(mx_x) + margin),
            min(H,  int(mx_y) + margin),
        )
        zoomed = img.crop(box)
        zoomed.save(ZOOM_PATH)
        print(f"[OK] Zoom kayit: {ZOOM_PATH}")

if __name__ == "__main__":
    np.random.seed(42)
    main()

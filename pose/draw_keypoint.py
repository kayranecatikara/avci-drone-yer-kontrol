# -*- coding: utf-8 -*-
# ==============================================================================
#  draw_keypoint.py  --  TALON IHA 6-NOKTA KEYPOINT CIZICI  (ZEYLO SISTEMI,
#                        kayra uyarlamasi)
# ------------------------------------------------------------------------------
#  Amac:
#    Dataset klasorundeki her *.json (Talon + kamera pozu) ve eslesen *.png icin
#    Talon'un 6 kilit noktasini goruntu uzerine matematiksel olarak projekte edip
#    cizer -> dataset_anotted\. GORSEL DOGRULAMA ARACIDIR (egitim goruntusune
#    dokunmaz; YOLO etiket uretimi ayri adimda yapilacak).
#
#  ORIJINALDEN FARKLAR (kayra):
#   1. DATASET_DIR -> C:\talon_pose_data\dataset (Zeylo yolu kaldirildi)
#   2. Goruntu boyutu 1920x1080 VARSAYILMAZ; her karede img.size kullanilir.
#   3. FOV_OVERRIDE varsayilani None (JSON'lardaki 125 kullanilir). Zeylo'nun
#      131.5445 olcumu (PlayerCameraManager:GetFOVAngle) ESKI FPV kamerasiydi;
#      DONDUR-CEK kamerasi 125 (bkz. asagida KAYRA OLCUMU).
#
#  ONEMLI MATEMATIK GERCEKLERI (Zeylo dogrulamasi — DEGISTIRME):
#    * UE5: SOL-el, Z-yukari. +X ileri (burun), +Y sag, +Z yukari.
#    * FRotationMatrix satirlari = eksen vektorleri (Forward/Right/Up).
#    * world = drone_loc + R . (local*scale + offset)
#    * Pinhole: f = (W/2)/tan(FOV_yatay/2). u saga +, v yukari -.
#    * Mesh GERCEK olculeri (FModel GLB): kanat 200 cm, govde 124.5 cm, ASIMETRIK
#      (burun +69.1, kuyruk -55.4). SDK'nin 171.8/110 degerleri NOMINAL'dir!
# ==============================================================================

import os
import json
import glob
import math

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
    from PIL import Image, ImageDraw, ImageFont

# ==============================================================================
#  1) AYARLAR
# ==============================================================================

DATASET_DIR = r"C:\talon_pose_data\dataset"
OUTPUT_DIR  = None          # None -> DATASET_DIR yanina 'dataset_anotted'

# --- 6 keypoint'in LOKAL (actor-space, cm) koordinatlari ------------------------
#  KAYNAK: KULLANICININ AM (agirlik merkezi) tablosu (preview.jpg/webp), kanat
#  1718 mm. Tablo AM-goreli, sag-elli (+X=kuyruk, +Y=yukari, +Z=sol kanat);
#  UE govde frame'ine cevrildi: X_UE=-X_tablo, Y_UE=-Z_tablo, Z_UE=+Y_tablo (mm->cm).
#  YAN GORUNUS DOGRULAMASI (talon_0058, 3.8m, 3 Tem): bu model burnu tam burun
#  ucuna oturtur; Zeylo'nun 200cm mesh modeli ise burnu ~40px ASIYORDU -> bu dogru.
#  (Zeylo'nun "171.8 oturmuyor" notu eski FARKLI simetrik keypoints_3d icindi.)
KEYPOINTS_LOCAL = {
    "nose":           (  55.03,   0.00,  -1.32),
    "tail":           ( -53.68,   0.00,  -0.65),
    "left_wingtip":   ( -10.17, -85.90,   4.49),
    "right_wingtip":  ( -10.17,  85.90,   4.49),
    "left_tail_fin":  ( -53.16, -22.56,  17.93),
    "right_tail_fin": ( -53.16,  22.57,  17.93),
}

TALON_SCALE = 1.0            # 1.0 = tablo olcegi (kanat 171.8 cm; talon_0058 yan-gorunus dogrulamasi)
# --- MESH PIVOT DUZELTMESI (3 Tem, "noktalar aracin ARKASINDA kaliyor" bulgusu) --
#  KOK NEDEN: Lua drone_location'i K2_GetActorLocation() = ACTOR ORIGIN veriyor,
#  ama gorsel mesh (SM_Talon_Body) actor origin'den +11.76 cm ILERIDE (burna dogru).
#  KANIT: components_dump.txt -> Body dunya konumu - Actor dunya konumu, actor
#  rotasyonuyla govde-frame'ine cevrilince (+11.76 ileri, 0 yan, 0 dikey). Motorun
#  KENDI olcumu, fit degil. Bu yuzden actor-origin etrafinda kurulan tum keypoint'ler
#  mesh'e gore ~11.76cm GERIDE (kuyruga dogru) oturuyordu -> "hepsi arkada" gorunumu,
#  mesafeyle ters olcekli (3m'de ~19px, 18m'de ~3px). talon_0334 (3.3m) dogrulamasi:
#  bu offset'le kanat/kuyruk/fin 18px sapmadan ~0-2px'e indi.
MESH_PIVOT_OFFSET = (11.76, 0.0, 0.0)

#  None -> JSON'daki camera_fov'u kullan. Sayi -> tum kareler icin zorla.
#  KAYRA OLCUMU (best.pt kalibrasyonu, 0004): DONDUR-CEK kamerasi 125 deg'dir
#  (Zeylo'nun 131.54'u ESKI FPV kamerasiydi, bu sistemde YANLIS). JSON zaten 125
#  yaziyor -> None dogru. FOV=125'te dikey sapma +6px, yayilim=bbox genisligi.
FOV_OVERRIDE = None

USE_KEYPOINTS_3D_IF_PRESENT = False   # Lua'daki eski/simetrik 3D noktalar HATALI -> kapali kalsin

DRAW_SKELETON = True
DRAW_LABELS   = False       # KAYRA: nokta uzeri yazilar (nose/wingtip...) KAPALI
DOT_RADIUS    = 2           # KAYRA: 4px nokta -> tam nereyi isaret ettigi belli olsun
KEYPOINT_COLORS = {
    "nose":           (30, 120, 255),
    "tail":           (255, 140, 0),
    "left_wingtip":   (255, 30, 30),
    "right_wingtip":  (255, 60, 200),
    "left_tail_fin":  (255, 230, 0),
    "right_tail_fin": (0, 230, 90),
}
SKELETON_EDGES = [
    ("nose", "left_wingtip"), ("nose", "right_wingtip"),
    ("left_wingtip", "tail"), ("right_wingtip", "tail"),
    ("tail", "left_tail_fin"), ("tail", "right_tail_fin"),
]

# ==============================================================================
#  2) UNREAL ENGINE MATEMATIGI (dogrulandi — degistirme)
# ==============================================================================

def ue_rotation_matrix(pitch_deg, yaw_deg, roll_deg):
    sp, cp = math.sin(math.radians(pitch_deg)), math.cos(math.radians(pitch_deg))
    sy, cy = math.sin(math.radians(yaw_deg)),   math.cos(math.radians(yaw_deg))
    sr, cr = math.sin(math.radians(roll_deg)),  math.cos(math.radians(roll_deg))
    return [
        [cp * cy,                cp * sy,                sp     ],   # Forward
        [sr * sp * cy - cr * sy, sr * sp * sy + cr * cy, -sr * cp],  # Right
        [-(cr * sp * cy + sr * sy), cy * sr - cr * sp * sy, cr * cp],# Up
    ]


def local_to_world(local_xyz, drone_loc, drone_rot, pivot_offset=(0.0, 0.0, 0.0), scale=1.0):
    lx = local_xyz[0] * scale + pivot_offset[0]
    ly = local_xyz[1] * scale + pivot_offset[1]
    lz = local_xyz[2] * scale + pivot_offset[2]
    R = ue_rotation_matrix(drone_rot["pitch"], drone_rot["yaw"], drone_rot["roll"])
    wx = lx * R[0][0] + ly * R[1][0] + lz * R[2][0]
    wy = lx * R[0][1] + ly * R[1][1] + lz * R[2][1]
    wz = lx * R[0][2] + ly * R[1][2] + lz * R[2][2]
    return (drone_loc["x"] + wx, drone_loc["y"] + wy, drone_loc["z"] + wz)


def project_world_to_screen(world_pt, cam_loc, cam_rot, fov, width, height):
    vx = world_pt[0] - cam_loc["x"]
    vy = world_pt[1] - cam_loc["y"]
    vz = world_pt[2] - cam_loc["z"]
    R = ue_rotation_matrix(cam_rot["pitch"], cam_rot["yaw"], cam_rot["roll"])
    fwd   = vx * R[0][0] + vy * R[0][1] + vz * R[0][2]
    right = vx * R[1][0] + vy * R[1][1] + vz * R[1][2]
    up    = vx * R[2][0] + vy * R[2][1] + vz * R[2][2]
    if fwd <= 1e-6:
        return None
    f = (width / 2.0) / math.tan(math.radians(fov / 2.0))
    u = (width / 2.0) + (right / fwd) * f
    v = (height / 2.0) - (up / fwd) * f
    return (u, v)


# ==============================================================================
#  3) KEYPOINT HESABI + CIZIM
# ==============================================================================

def compute_keypoints_2d(data, fov, width, height):
    drone_loc = data.get("drone_location") or data.get("talon_location")
    drone_rot = data.get("drone_rotation") or data.get("talon_rotation")
    cam_loc   = data.get("camera_location") or data.get("avci_camera_location")
    cam_rot   = data.get("camera_rotation") or data.get("avci_camera_rotation")

    kp3d = data.get("keypoints_3d") or {}
    use_gt = USE_KEYPOINTS_3D_IF_PRESENT and isinstance(kp3d, dict) and len(kp3d) >= 6

    pts = {}
    if use_gt:
        for name in KEYPOINTS_LOCAL:
            w = kp3d.get(name)
            pts[name] = project_world_to_screen((w["x"], w["y"], w["z"]),
                                                cam_loc, cam_rot, fov, width, height) if w else None
        return pts, "keypoints_3d (hazir 3B)"
    for name, local_xyz in KEYPOINTS_LOCAL.items():
        world = local_to_world(local_xyz, drone_loc, drone_rot, MESH_PIVOT_OFFSET, TALON_SCALE)
        pts[name] = project_world_to_screen(world, cam_loc, cam_rot, fov, width, height)
    return pts, "mesh model (RAW_CAD)"


def _load_font():
    try:
        return ImageFont.truetype("arial.ttf", 16)
    except Exception:
        return ImageFont.load_default()


def draw_on_image(img, pts):
    draw = ImageDraw.Draw(img)
    font = _load_font()
    if DRAW_SKELETON:
        for a, b in SKELETON_EDGES:
            if pts.get(a) and pts.get(b):
                draw.line([pts[a], pts[b]], fill=(255, 255, 255), width=2)
    for name, p in pts.items():
        if not p:
            continue
        x, y = p
        c = KEYPOINT_COLORS.get(name, (255, 0, 0))
        draw.ellipse((x - DOT_RADIUS, y - DOT_RADIUS, x + DOT_RADIUS, y + DOT_RADIUS),
                     fill=c, outline=(0, 0, 0))
        if DRAW_LABELS:
            draw.text((x + DOT_RADIUS + 2, y - 8), name, fill=c, font=font)
    return img


# ==============================================================================
#  4) ANA DONGU
# ==============================================================================

def run(dataset_dir=DATASET_DIR, output_dir=OUTPUT_DIR, limit=None):
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(dataset_dir.rstrip("\\/")), "dataset_anotted")
    os.makedirs(output_dir, exist_ok=True)

    json_files = sorted(glob.glob(os.path.join(dataset_dir, "*.json")))
    if limit is not None:
        json_files = json_files[:limit]
    print(f"[draw_keypoint] {len(json_files)} JSON islenecek.  Cikti -> {output_dir}")
    print(f"[draw_keypoint] FOV_OVERRIDE={FOV_OVERRIDE}  SCALE={TALON_SCALE}  "
          f"OFFSET={MESH_PIVOT_OFFSET}")

    done = 0
    for jf in json_files:
        png = jf[:-5] + ".png"
        if not os.path.exists(png):
            continue
        try:
            with open(jf, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"  ! {os.path.basename(jf)} okunamadi: {e}")
            continue
        if not ((data.get("drone_location") or data.get("talon_location")) and
                (data.get("camera_location") or data.get("avci_camera_location"))):
            print(f"  ! {os.path.basename(jf)} poz eksik, atlandi.")
            continue

        fov = FOV_OVERRIDE if FOV_OVERRIDE is not None else float(data.get("camera_fov", 125.0))
        img = Image.open(png).convert("RGB")
        W, H = img.size                                   # 1920x1080 VARSAYMA
        pts, _src = compute_keypoints_2d(data, fov, W, H)
        draw_on_image(img, pts)
        out = os.path.join(output_dir, os.path.basename(png).replace(".png", "_marked.png"))
        img.save(out, "PNG")
        done += 1

    print(f"[draw_keypoint] Bitti. {done} goruntu isaretlendi -> {output_dir}")
    try:
        os.startfile(output_dir)      # klasoru otomatik ac (gozle kontrol)
    except Exception:
        pass


if __name__ == "__main__":
    import sys as _sys
    _limit = int(_sys.argv[1]) if len(_sys.argv) > 1 else None   # ör: python pose\draw_keypoint.py 30
    run(limit=_limit)

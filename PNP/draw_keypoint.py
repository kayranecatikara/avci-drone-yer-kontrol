# -*- coding: utf-8 -*-
# ==============================================================================
#  draw_keypoint.py  --  TALON IHA 6-NOKTA KEYPOINT CIZICI  (bagimsiz / standalone)
# ------------------------------------------------------------------------------
#  Amac:
#    Bir dataset klasorundeki her *.json (drone + kamera pozu) ve eslesen *.png
#    icin, Talon'un 6 kilit noktasini (burun, kuyruk, sag/sol kanat ucu,
#    sag/sol kuyruk kanatcigi) 1920x1080 goruntu uzerine matematiksel olarak
#    projekte edip cizer.
#
#  ONEMLI MATEMATIK GERCEKLERI (bu kod bunlara gore kuruldu, dogrulandi):
#    * Unreal Engine 5: SOL-EL, Z-YUKARI. +X ileri (burun), +Y sag, +Z yukari.
#    * FRotationMatrix satirlari = eksen vektorleri: satir0=Forward(X),
#      satir1=Right(Y), satir2=Up(Z). (RotationMatrix.h ile birebir.)
#    * Rotasyon kompozisyon sirasi Roll -> Pitch -> Yaw'dir; tek FRotator
#      matrisi bunu zaten icerir.
#    * local->world :  world = drone_loc + (lx*Forward + ly*Right + lz*Up)
#    * world->kamera:  ortonormal matris => ters = nokta carpim (satirlarla)
#    * Pinhole izdusum: f = (W/2)/tan(FOV_yatay/2).  u saga +, v yukari -.
#
#  DRIFT (kayma) COZUMU -- MESH_PIVOT_OFFSET:
#    Talon Actor'unun pivotu (drone_location) gorsel mesh'in tam merkezinde
#    DEGILDIR. Bu yuzden lokal keypoint'ler once pivot ofsetiyle kaydirilir,
#    SONRA dondurulur. Boylece drone yaw/roll yapinca noktalar kaymaz.
#      world = drone_loc + R(drone_rot) . (KEYPOINTS_LOCAL[k] + MESH_PIVOT_OFFSET)
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
#  1) AYARLAR  (buradan tune edersin)
# ==============================================================================

DATASET_DIR = r"C:\Users\Zeylo\Desktop\talon_dataset\dataset"
OUTPUT_DIR  = None          # None -> DATASET_DIR'in yanindaki 'dataset_anotted'
IMAGE_W, IMAGE_H = 1920, 1080

# --- 6 keypoint'in LOKAL (actor-space, cm) koordinatlari -----------------------
#  KAYNAK: Talon'un GUNCEL (V2) oyun mesh'i, FModel GLB export:
#    C:\Users\Zeylo\Desktop\FModel\Output\Exports\DronesOfWar\Content\Art\Meshes\Talon\V2
#    SM_Talon_Body / Wing_L/R / Small_Wing_L/R.glb  -> her parcanin uc (ekstrem) vertex'i.
#  GLB->UE donusumu: UE(X,Y,Z) = (glb.x, glb.z, glb.y) * 100.  +X burun, +Y sag, +Z yukari.
#  Mesh vertex'leri zaten pivota (component RelativeLocation=0,0,0) gore oldugu icin
#  bunlar DOGRUDAN actor-local keypoint'lerdir -> ekstra offset gerekmez.
#
#  DOGRULAMA: Body X span = TAM 110.0 cm (nose +61.1, tail -48.9), kanat aciklik 178 cm.
#  (Eski BreakTalon mesh'i 200 cm'di ve YANLISTI; keypoints_3d ise simetrik 171.8 sanip
#   ucaga oturmuyordu. V2 = gercek render edilen mesh; mesh silueti ucakla ortusuyor.)
KEYPOINTS_LOCAL = {
    "nose":           (  61.1,     0.0,    -2.4),    # govde en ileri vertex
    "tail":           ( -48.9,     0.0,     0.1),    # govde en geri vertex (pervane bolgesi)
    "left_wingtip":   (   1.5,   -89.0,     4.9),    # Wing_L en dis vertex (sol = -Y)
    "right_wingtip":  (   1.5,    89.0,     4.9),    # Wing_R en dis vertex (sag = +Y)
    "left_tail_fin":  ( -38.0,   -25.3,    15.2),    # Small_Wing_L uc vertex (yukari egik)
    "right_tail_fin": ( -38.0,    25.3,    15.2),    # Small_Wing_R uc vertex
}

# --- TALON OLCEGI -------------------------------------------------------------
#  Oyunun mesh'e uyguladigi RelativeScale3D. V2 mesh dogal boyu: govde 110 cm, kanat 178 cm.
#  1.0 = mesh dogal boyu (goruntude ucak uzerine oturuyor -> dogrulandi).
#  Ucak kadrajda beklenenden kucuk/buyuk gorunuyorsa buradan ince ayar yap.
TALON_SCALE = 1.0

# --- PIVOT OFFSET (ince ayar) -------------------------------------------------
#  Mesh keypoint'leri zaten pivota gore dogru oldugu icin varsayilan (0,0,0).
#  world = drone_loc + R(drone_rot) . (KEYPOINTS_LOCAL[k]*TALON_SCALE + MESH_PIVOT_OFFSET)
#  Kalan mikro kaymayi (or. birkac cm) gormek istersen buradan tune et.
MESH_PIVOT_OFFSET = (0.0, 0.0, 0.0)

# --- FOV ----------------------------------------------------------------------
#  None  -> her karenin kendi JSON'undaki camera_fov'u kullanilir.
#  Sayi  -> tum kareler icin bu FOV'u zorlar.
FOV_OVERRIDE = None

# --- keypoints_3d PASSTHROUGH -------------------------------------------------
#  DIKKAT: Mevcut dataset JSON'larindaki 'keypoints_3d' ESKI/YANLIS simetrik modelden
#  (171.8 cm, nose +-55) uretilmisti ve ucaga OTURMUYOR. Bu yuzden varsayilan False;
#  yukaridaki mesh modeli (RAW_CAD) her karede dogru sonucu uretir.
#  True yaparsan eski (hatali) keypoints_3d'yi aynen cizersin -> ONERILMEZ.
USE_KEYPOINTS_3D_IF_PRESENT = False

# --- Cizim stili --------------------------------------------------------------
DRAW_SKELETON = True
DRAW_LABELS   = True
DOT_RADIUS    = 5
KEYPOINT_COLORS = {
    "nose":           (30, 120, 255),   # mavi
    "tail":           (255, 140, 0),    # turuncu
    "left_wingtip":   (255, 30, 30),    # kirmizi
    "right_wingtip":  (255, 60, 200),   # pembe
    "left_tail_fin":  (255, 230, 0),    # sari
    "right_tail_fin": (0, 230, 90),     # yesil
}
SKELETON_EDGES = [
    ("nose", "left_wingtip"), ("nose", "right_wingtip"),
    ("left_wingtip", "tail"), ("right_wingtip", "tail"),
    ("tail", "left_tail_fin"), ("tail", "right_tail_fin"),
]

# ==============================================================================
#  2) UNREAL ENGINE MATEMATIGI  (dogrulandi -- degistirme)
# ==============================================================================

def ue_rotation_matrix(pitch_deg, yaw_deg, roll_deg):
    """Unreal FRotationMatrix (sol-el, Z-yukari).
    Donen matrisin SATIRLARI dunya-uzayindaki eksen vektorleridir:
        R[0] = Forward (+X),  R[1] = Right (+Y),  R[2] = Up (+Z)
    Roll->Pitch->Yaw kompozisyonu bu tek matriste gomulidur."""
    sp, cp = math.sin(math.radians(pitch_deg)), math.cos(math.radians(pitch_deg))
    sy, cy = math.sin(math.radians(yaw_deg)),   math.cos(math.radians(yaw_deg))
    sr, cr = math.sin(math.radians(roll_deg)),  math.cos(math.radians(roll_deg))
    return [
        [cp * cy,               cp * sy,               sp     ],  # Forward
        [sr * sp * cy - cr * sy, sr * sp * sy + cr * cy, -sr * cp],  # Right
        [-(cr * sp * cy + sr * sy), cy * sr - cr * sp * sy, cr * cp],  # Up
    ]


def local_to_world(local_xyz, drone_loc, drone_rot, pivot_offset=(0.0, 0.0, 0.0), scale=1.0):
    """Lokal (actor-space) keypoint -> dunya koordinati.
    Once olcek + pivot offset lokalde uygulanir, sonra drone rotasyonuyla dondurulur:
        world = drone_loc + R . (local*scale + offset)
    """
    lx = local_xyz[0] * scale + pivot_offset[0]
    ly = local_xyz[1] * scale + pivot_offset[1]
    lz = local_xyz[2] * scale + pivot_offset[2]
    R = ue_rotation_matrix(drone_rot["pitch"], drone_rot["yaw"], drone_rot["roll"])
    wx = lx * R[0][0] + ly * R[1][0] + lz * R[2][0]
    wy = lx * R[0][1] + ly * R[1][1] + lz * R[2][1]
    wz = lx * R[0][2] + ly * R[1][2] + lz * R[2][2]
    return (drone_loc["x"] + wx, drone_loc["y"] + wy, drone_loc["z"] + wz)


def project_world_to_screen(world_pt, cam_loc, cam_rot, fov, width=IMAGE_W, height=IMAGE_H):
    """Dunya noktasi -> ekran pikseli (pinhole). Kamera arkasi/yani -> None.
    fov = YATAY FOV (derece). f = (W/2)/tan(fov/2)."""
    vx = world_pt[0] - cam_loc["x"]
    vy = world_pt[1] - cam_loc["y"]
    vz = world_pt[2] - cam_loc["z"]
    R = ue_rotation_matrix(cam_rot["pitch"], cam_rot["yaw"], cam_rot["roll"])
    # Dunya vektorunu kamera eksenlerine izdusur (satir . v):
    fwd   = vx * R[0][0] + vy * R[0][1] + vz * R[0][2]   # derinlik (Forward)
    right = vx * R[1][0] + vy * R[1][1] + vz * R[1][2]   # saga     (Right)
    up    = vx * R[2][0] + vy * R[2][1] + vz * R[2][2]   # yukari   (Up)
    if fwd <= 1e-6:
        return None  # kamera arkasinda / duzleminde
    f = (width / 2.0) / math.tan(math.radians(fov / 2.0))
    u = (width / 2.0) + (right / fwd) * f
    v = (height / 2.0) - (up / fwd) * f
    return (u, v)


# ==============================================================================
#  3) KEYPOINT HESABI (bir kare icin) + CIZIM
# ==============================================================================

def compute_keypoints_2d(data, fov):
    """Bir JSON'dan 6 keypoint'in 2D piksellerini dondurur. keypoints_3d passthrough
    aktifse ve kare doluysa onu, degilse lokal model + offset + rotasyonu kullanir.
    Donus: {name: (u, v) or None}, kaynak_str"""
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
            pts[name] = project_world_to_screen((w["x"], w["y"], w["z"]), cam_loc, cam_rot, fov) if w else None
        return pts, "keypoints_3d (hazir 3B)"
    else:
        for name, local_xyz in KEYPOINTS_LOCAL.items():
            world = local_to_world(local_xyz, drone_loc, drone_rot, MESH_PIVOT_OFFSET, TALON_SCALE)
            pts[name] = project_world_to_screen(world, cam_loc, cam_rot, fov)
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

def run(dataset_dir=DATASET_DIR, output_dir=OUTPUT_DIR, verbose_calibration=True, limit=None):
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(dataset_dir.rstrip("\\/")), "dataset_anotted")
    os.makedirs(output_dir, exist_ok=True)

    json_files = sorted(glob.glob(os.path.join(dataset_dir, "*.json")))
    if limit is not None:                      # sadece ilk N kare (hizli test icin)
        json_files = json_files[:limit]
    print(f"[draw_keypoint] {len(json_files)} JSON islenecek.  Cikti -> {output_dir}")
    print(f"[draw_keypoint] MESH_PIVOT_OFFSET={MESH_PIVOT_OFFSET}  FOV_OVERRIDE={FOV_OVERRIDE}  "
          f"USE_KP3D={USE_KEYPOINTS_3D_IF_PRESENT}")

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
        if not (data.get("drone_location") and data.get("camera_location")):
            print(f"  ! {os.path.basename(jf)} poz eksik, atlandi.")
            continue

        fov = FOV_OVERRIDE if FOV_OVERRIDE is not None else float(data.get("camera_fov", 125.0))
        pts, _source = compute_keypoints_2d(data, fov)

        img = Image.open(png).convert("RGB")
        draw_on_image(img, pts)
        out = os.path.join(output_dir, os.path.basename(png).replace(".png", "_marked.png"))
        img.save(out, "PNG")
        done += 1

    print(f"[draw_keypoint] Bitti. {done} goruntu isaretlendi.  "
          f"(model=mesh RAW_CAD, scale={TALON_SCALE}, offset={MESH_PIVOT_OFFSET})")


if __name__ == "__main__":
    run()

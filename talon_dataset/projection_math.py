# -*- coding: utf-8 -*-
# ============================================================================
#  projection_math.py  -  TALON DATASET icin TEK DOGRU PROJEKSIYON MODULU
# ----------------------------------------------------------------------------
#  Bu dosya, butun Python scriptlerinin (capture_controller_yeni.py,
#  draw_keypoints.py, recalculate_jsons.py ...) ortak kullandigi TEK matematik
#  kaynagidir. Artik her dosyada ayri ayri (ve farkli/yanlis) rotasyon matrisi
#  YOKTUR. Hepsi buradan import eder.
#
#  KESINLESMIS GERCEKLER (oyun motorundan dogrulandi):
#    * SCALE = 1.0  -> Drone'un RelativeScale3D=(1,1,1), parcalarin
#      RelativeLocation=(0,0,0). GetActorBounds (rotation=0) Y-yaricapi 101 cm
#      = CAD'deki 2001 mm kanat acikligi ile birebir. Yani CAD'deki 1 cm = oyunda
#      1 cm. HICBIR carpan (1.01, 1.422, /0.86 ...) UYGULANMAZ.
#    * Koordinatlar Unreal sol-el, Z-yukari. +X ileri, +Y sag, +Z yukari.
#    * FOV: artik Lua modu her karede gercek render FOV'unu
#      (PlayerCameraManager:GetFOVAngle) JSON'a yazar. Buradaki matematik o
#      gercek FOV'u kullanir; hicbir yere sabit FOV gomulmez.
#
#  RAW_CAD_DATA = kullanicinin kalibre ettigi kutsal santimetre olculeri.
#  ASLA degistirilmez, ASLA carpanla carpilmaz. Sol kanat -Y, sag kanat +Y.
# ============================================================================

import math

# ---- Sabit render cozunurlugu (Lua "r.SetRes 1920x1080w" + Python resize) ----
WIDTH = 1920
HEIGHT = 1080

# ---- KUTSAL HAM CAD KOORDINATLARI (UE cm, actor-relative, SCALE=1.0) ----
RAW_CAD_DATA = {
    "nose":           {"x": 69.13,  "y": 0.19,   "z": -2.77},
    "left_wingtip":   {"x": 1.65,   "y": -99.93, "z": 5.81},
    "right_wingtip":  {"x": 1.65,   "y": 99.93,  "z": 5.81},
    "tail":           {"x": -55.38, "y": 0.10,   "z": 0.10},
    "left_tail_fin":  {"x": -43.17, "y": -28.25, "z": 16.98},
    "right_tail_fin": {"x": -43.17, "y": 28.25,  "z": 16.98},
}

# Ciizim renkleri ve iskelet kenarlari (tek yerde dursun)
KEYPOINT_COLORS = {
    "nose":           (30, 100, 250),   # Mavi
    "left_wingtip":   (255, 30, 30),    # Kirmizi
    "right_wingtip":  (255, 100, 200),  # Pembe
    "tail":           (255, 120, 0),    # Turuncu
    "left_tail_fin":  (255, 215, 0),    # Sari
    "right_tail_fin": (0, 200, 80),     # Yesil
}

SKELETON_EDGES = [
    ("nose", "left_wingtip"),
    ("nose", "right_wingtip"),
    ("left_wingtip", "tail"),
    ("right_wingtip", "tail"),
    ("tail", "left_tail_fin"),
    ("tail", "right_tail_fin"),
]


def get_unreal_matrix(pitch, yaw, roll):
    """Unreal Engine FRotationMatrix (sol-el, Z-yukari). Satirlar = eksen
    vektorleri: R[0]=Forward(X), R[1]=Right(Y), R[2]=Up(Z) bilesenleri sutun
    sirasinda [X, Y, Z]. UE kaynagi (RotationMatrix.h) ile birebir ayni."""
    SP, CP = math.sin(math.radians(pitch)), math.cos(math.radians(pitch))
    SY, CY = math.sin(math.radians(yaw)),   math.cos(math.radians(yaw))
    SR, CR = math.sin(math.radians(roll)),  math.cos(math.radians(roll))

    # Forward (AxisX)
    r00 = CP * CY
    r10 = CP * SY
    r20 = SP
    # Right (AxisY)
    r01 = SR * SP * CY - CR * SY
    r11 = SR * SP * SY + CR * CY
    r21 = -SR * CP
    # Up (AxisZ)  <-- DOGRU isaretler (eski capture/recalc'teki hata burada idi)
    r02 = -(CR * SP * CY + SR * SY)
    r12 = CY * SR - CR * SP * SY
    r22 = CR * CP

    return [[r00, r01, r02],
            [r10, r11, r12],
            [r20, r21, r22]]


def rotate_vector_ue(x, y, z, pitch, yaw, roll):
    """Local (actor-space) vektoru, actor rotasyonuyla dunya offset'ine cevirir.
    Unreal'in TransformVector'u ile ayni: world = x*Forward + y*Right + z*Up."""
    R = get_unreal_matrix(pitch, yaw, roll)
    rx = x * R[0][0] + y * R[0][1] + z * R[0][2]
    ry = x * R[1][0] + y * R[1][1] + z * R[1][2]
    rz = x * R[2][0] + y * R[2][1] + z * R[2][2]
    return rx, ry, rz


def project_world_to_screen(world_pt, cam_loc, cam_rot, fov, width=WIDTH, height=HEIGHT):
    """Pinhole projeksiyon. fov = o karenin GERCEK yatay FOV'u (Lua'dan gelen).
    Donus: (u, v) piksel. Kamera arkasi/yan icin (-1, -1)."""
    vx = world_pt[0] - cam_loc["x"]
    vy = world_pt[1] - cam_loc["y"]
    vz = world_pt[2] - cam_loc["z"]

    R = get_unreal_matrix(cam_rot["pitch"], cam_rot["yaw"], cam_rot["roll"])
    # Dunya vektorunu kamera eksenlerine izdusur (ortonormal matris -> ters = nokta carpim)
    x_local = vx * R[0][0] + vy * R[1][0] + vz * R[2][0]   # v . Forward (derinlik)
    y_local = vx * R[0][1] + vy * R[1][1] + vz * R[2][1]   # v . Right   (saga)
    z_local = vx * R[0][2] + vy * R[1][2] + vz * R[2][2]   # v . Up      (yukari)

    if x_local <= 0:
        return -1.0, -1.0

    focal_length = (width / 2.0) / math.tan(math.radians(fov / 2.0))
    u = (width / 2.0) + (y_local / x_local) * focal_length
    v = (height / 2.0) - (z_local / x_local) * focal_length
    return u, v


def calculate_keypoints_2d(drone_loc, drone_rot, cam_loc, cam_rot, fov,
                           width=WIDTH, height=HEIGHT):
    """6 keypoint'in 2D piksel konumlarini hesaplar. SCALE=1.0, carpan YOK.
    fov = JSON'daki gercek camera_fov (Lua'dan)."""
    kps_2d = {}
    for name, cad in RAW_CAD_DATA.items():
        # SCALE = 1.0 -> ham CAD degeri dogrudan kullanilir, hicbir carpan yok.
        rx, ry, rz = rotate_vector_ue(
            cad["x"], cad["y"], cad["z"],
            drone_rot["pitch"], drone_rot["yaw"], drone_rot["roll"]
        )
        world_pt = (drone_loc["x"] + rx,
                    drone_loc["y"] + ry,
                    drone_loc["z"] + rz)
        u, v = project_world_to_screen(world_pt, cam_loc, cam_rot, fov, width, height)
        kps_2d[name] = {"x": u, "y": v}
    return kps_2d

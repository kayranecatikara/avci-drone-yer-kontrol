"""
Test: Kamera talonun tam 300 birim tepesinde ve tam asagi bakiyorsa,
drone_location merkezi ekranin tam ortasina (960, 540) dusmeli.
"""
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
    r02 = CR * SP * CY + SR * SY; r12 = CR * SP * SY - SR * CY; r22 = CR * CP
    rx = x * r00 + y * r01 + z * r02
    ry = x * r10 + y * r11 + z * r12
    rz = x * r20 + y * r21 + z * r22
    return rx, ry, rz

def project_world_to_screen(world_pt, cam_loc, cam_rot, fov=90.0, width=1920, height=1080):
    vx = world_pt[0] - cam_loc['x']
    vy = world_pt[1] - cam_loc['y']
    vz = world_pt[2] - cam_loc['z']
    rad_pitch = math.radians(cam_rot['pitch'])
    rad_yaw = math.radians(-cam_rot['yaw'])
    rad_roll = math.radians(cam_rot['roll'])
    SP = math.sin(rad_pitch); CP = math.cos(rad_pitch)
    SY = math.sin(rad_yaw); CY = math.cos(rad_yaw)
    SR = math.sin(rad_roll); CR = math.cos(rad_roll)
    r00 = CP * CY; r01 = -CP * SY; r02 = SP
    r10 = SR * SP * CY + CR * SY; r11 = -SR * SP * SY + CR * CY; r12 = -SR * CP
    r20 = -CR * SP * CY + SR * SY; r21 = CR * SP * SY + SR * CY; r22 = CR * CP
    x_local = vx * r00 + vy * r01 + vz * r02
    y_local = vx * r10 + vy * r11 + vz * r12
    z_local = vx * r20 + vy * r21 + vz * r22
    if x_local <= 0: return -1.0, -1.0
    focal_length = (width / 2.0) / math.tan(math.radians(fov / 2.0))
    u = (width / 2.0) + (y_local / x_local) * focal_length
    v = (height / 2.0) - (z_local / x_local) * focal_length
    return u, v

# =========================================
# TEST 1: Top-Down - Kamera tam tepede, asagi bakiyor
# =========================================
print("=" * 60)
print("TEST 1: TOP-DOWN (Kamera 300 birim yukarda, tam asagi bakiyor)")
print("=" * 60)
drone_loc = {"x": 1000.0, "y": 2000.0, "z": 500.0}
drone_rot = {"pitch": 0.0, "yaw": 45.0, "roll": 0.0}
cam_loc = {"x": 1000.0, "y": 2000.0, "z": 800.0}  # 300 birim yukarda
cam_rot = {"pitch": -89.9, "yaw": 45.0 + 90.0, "roll": 0.0}  # Tam asagi

# Drone merkezi ekranin ortasina dusmeli (960, 540)
u, v = project_world_to_screen(
    (drone_loc["x"], drone_loc["y"], drone_loc["z"]),
    cam_loc, cam_rot, fov=90.0
)
print(f"  Drone merkezi => u={u:.2f}, v={v:.2f}")
print(f"  Beklenen:      => u=960.00, v=540.00")
print(f"  SONUC: {'BASARILI OK' if abs(u - 960) < 5 and abs(v - 540) < 5 else 'HATALI FAIL (BUYUK SORUN!)'}")

# Keypoint'leri de test edelim
KEYPOINTS_LOCAL = {
    "nose":             {"x": 49.605, "y": 0.000, "z": 0.000},
    "left_wingtip":     {"x": 38.578, "y": -45.003, "z": 0.548},
    "right_wingtip":    {"x": 38.578, "y": 45.003, "z": 0.548},
    "tail":             {"x": -40.882, "y": 0.000, "z": 0.000},
    "left_tail_fin":    {"x": -34.008, "y": -20.534, "z": 7.655},
    "right_tail_fin":   {"x": -34.008, "y": 20.534, "z": 7.655}
}

print("\n  Keypoints:")
for name, offset in KEYPOINTS_LOCAL.items():
    rx, ry, rz = rotate_vector_ue(offset["x"], offset["y"], offset["z"], drone_rot["pitch"], drone_rot["yaw"], drone_rot["roll"])
    world_pt = (drone_loc["x"] + rx, drone_loc["y"] + ry, drone_loc["z"] + rz)
    u2, v2 = project_world_to_screen(world_pt, cam_loc, cam_rot, fov=90.0)
    print(f"    {name:20s} => u={u2:.2f}, v={v2:.2f}")

# =========================================
# TEST 2: Head-On - Kamera onunde, drone'a bakiyor
# =========================================
print("\n" + "=" * 60)
print("TEST 2: HEAD-ON (Kamera 300 birim onde, drone'a bakiyor)")
print("=" * 60)
drone_loc2 = {"x": 1000.0, "y": 2000.0, "z": 500.0}
drone_rot2 = {"pitch": 0.0, "yaw": 0.0, "roll": 0.0}
# Forward vector: (1, 0, 0) when yaw=0
cam_loc2 = {"x": 1300.0, "y": 2000.0, "z": 500.0}  # 300 birim onde
# LookAt math:
dx = drone_loc2["x"] - cam_loc2["x"]  # -300
dy = drone_loc2["y"] - cam_loc2["y"]  # 0
dz = drone_loc2["z"] - cam_loc2["z"]  # 0
distXY = math.sqrt(dx*dx + dy*dy)
lookYaw = math.degrees(math.atan2(dy, dx))
lookPitch = math.degrees(math.atan2(dz, distXY))
cam_rot2 = {"pitch": lookPitch, "yaw": lookYaw, "roll": 0.0}
print(f"  Computed cam_rot: pitch={lookPitch:.2f}, yaw={lookYaw:.2f}")

u3, v3 = project_world_to_screen(
    (drone_loc2["x"], drone_loc2["y"], drone_loc2["z"]),
    cam_loc2, cam_rot2, fov=90.0
)
print(f"  Drone merkezi => u={u3:.2f}, v={v3:.2f}")
print(f"  Beklenen:      => u=960.00, v=540.00")
print(f"  SONUC: {'BASARILI OK' if abs(u3 - 960) < 5 and abs(v3 - 540) < 5 else 'HATALI FAIL (BUYUK SORUN!)'}")

# =========================================
# TEST 3: Cok farkli yon - Drone yaw=90 head-on
# =========================================
print("\n" + "=" * 60)
print("TEST 3: HEAD-ON (Drone yaw=90, kamera Y ekseninde 300 birim onde)")
print("=" * 60)
drone_loc3 = {"x": 5000.0, "y": 3000.0, "z": 1200.0}
drone_rot3 = {"pitch": 5.0, "yaw": 90.0, "roll": 2.0}
# Forward vector when yaw=90: yaklaşık (0, 1, 0.087)
fw_x = math.cos(math.radians(5.0)) * math.cos(math.radians(90.0))
fw_y = math.cos(math.radians(5.0)) * math.sin(math.radians(90.0))
fw_z = math.sin(math.radians(5.0))
cam_loc3 = {"x": drone_loc3["x"] + fw_x * 300, "y": drone_loc3["y"] + fw_y * 300, "z": drone_loc3["z"] + fw_z * 300}
dx3 = drone_loc3["x"] - cam_loc3["x"]
dy3 = drone_loc3["y"] - cam_loc3["y"]
dz3 = drone_loc3["z"] - cam_loc3["z"]
distXY3 = math.sqrt(dx3*dx3 + dy3*dy3)
lookYaw3 = math.degrees(math.atan2(dy3, dx3))
lookPitch3 = math.degrees(math.atan2(dz3, distXY3))
cam_rot3 = {"pitch": lookPitch3, "yaw": lookYaw3, "roll": 0.0}
print(f"  Computed cam_rot: pitch={lookPitch3:.2f}, yaw={lookYaw3:.2f}")

u4, v4 = project_world_to_screen(
    (drone_loc3["x"], drone_loc3["y"], drone_loc3["z"]),
    cam_loc3, cam_rot3, fov=90.0
)
print(f"  Drone merkezi => u={u4:.2f}, v={v4:.2f}")
print(f"  Beklenen:      => u=960.00, v=540.00")
print(f"  SONUC: {'BASARILI OK' if abs(u4 - 960) < 5 and abs(v4 - 540) < 5 else 'HATALI FAIL (BUYUK SORUN!)'}")

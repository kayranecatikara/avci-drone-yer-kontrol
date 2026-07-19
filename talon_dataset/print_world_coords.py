import json
import math

# Frame 1 telemetry
f1 = {
    "drone_location": {"x": -14828.2, "y": -249122.23, "z": 8391.84},
    "drone_rotation": {"pitch": -1.58, "yaw": -42.97, "roll": 43.73},
    "camera_location": {"x": -14992.95, "y": -249465.63, "z": 8281.9},
    "camera_rotation": {"pitch": 16.0, "yaw": 66.0, "roll": 0.0}
}

def rotate_vector_ue(x, y, z, pitch, yaw, roll):
    rad_pitch = math.radians(pitch)
    rad_yaw = math.radians(yaw)
    rad_roll = math.radians(roll)
    
    SP = math.sin(rad_pitch)
    CP = math.cos(rad_pitch)
    SY = math.sin(rad_yaw)
    CY = math.cos(rad_yaw)
    SR = math.sin(rad_roll)
    CR = math.cos(rad_roll)
    
    r00 = CP * CY
    r10 = CP * SY
    r20 = SP
    
    r01 = SR * SP * CY - CR * SY
    r11 = SR * SP * SY + CR * CY
    r21 = -SR * CP
    
    r02 = CR * SP * CY + SR * SY
    r12 = CR * SP * SY - SR * CY
    r22 = CR * CP
    
    rx = x * r00 + y * r01 + z * r02
    ry = x * r10 + y * r11 + z * r12
    rz = x * r20 + y * r21 + z * r22
    
    return rx, ry, rz

x, y, z = -23.2600, 19.2000, 15.0780

# Left fin (y = 19.2)
rx_l, ry_l, rz_l = rotate_vector_ue(x, y, z, f1['drone_rotation']['pitch'], f1['drone_rotation']['yaw'], f1['drone_rotation']['roll'])
world_l = (f1['drone_location']['x'] + rx_l, f1['drone_location']['y'] + ry_l, f1['drone_location']['z'] + rz_l)

# Right fin (y = -19.2)
rx_r, ry_r, rz_r = rotate_vector_ue(x, -y, z, f1['drone_rotation']['pitch'], f1['drone_rotation']['yaw'], f1['drone_rotation']['roll'])
world_r = (f1['drone_location']['x'] + rx_r, f1['drone_location']['y'] + ry_r, f1['drone_location']['z'] + rz_r)

print(f"Left fin (y={y}):  world Z={world_l[2]:.2f}, rotated Z={rz_l:.2f}")
print(f"Right fin (y={-y}): world Z={world_r[2]:.2f}, rotated Z={rz_r:.2f}")

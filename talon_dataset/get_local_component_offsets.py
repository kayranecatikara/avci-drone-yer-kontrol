import math

# From components_dump.txt:
# Actor World Loc: X=-15107.4520, Y=-248772.0402, Z=8402.9275
# Actor World Rot: P=-1.2804, Y=-57.6861, R=39.7827
# SM_Talon_Body World Loc: X=-15089.7669, Y=-248799.6290, Z=8402.1904

act_loc = {"x": -15107.4520, "y": -248772.0402, "z": 8402.9275}
act_rot = {"pitch": -1.2804, "yaw": -57.6861, "roll": 39.7827}
comp_loc = {"x": -15089.7669, "y": -248799.6290, "z": 8402.1904}

# World offset:
dx = comp_loc["x"] - act_loc["x"]
dy = comp_loc["y"] - act_loc["y"]
dz = comp_loc["z"] - act_loc["z"]

print(f"World Offset: dx={dx:.4f}, dy={dy:.4f}, dz={dz:.4f}")

# Rotate world offset back to local space (using inverse of actor rotation)
# In Unreal Engine: V_world = R_actor * V_local -> V_local = R_actor^T * V_world
def rotate_vector_inverse_ue(vx, vy, vz, pitch, yaw, roll):
    # R = Rz(yaw) @ Ry(pitch) @ Rx(roll)
    # The transpose is R^T = Rx(-roll) @ Ry(-pitch) @ Rz(-yaw)
    # Wait, let's write out the transpose of the FRotator::RotateVector matrix:
    rad_pitch = math.radians(pitch)
    rad_yaw = math.radians(yaw)
    rad_roll = math.radians(roll)
    
    SP = math.sin(rad_pitch)
    CP = math.cos(rad_pitch)
    SY = math.sin(rad_yaw)
    CY = math.cos(rad_yaw)
    SR = math.sin(rad_roll)
    CR = math.cos(rad_roll)
    
    # Rows of R are columns of R^T:
    # AxisX (Forward)
    r00 = CP * CY
    r01 = CP * SY
    r02 = SP
    
    # AxisY (Right)
    r10 = SR * SP * CY - CR * SY
    r11 = SR * SP * SY + CR * CY
    r12 = -SR * CP
    
    # AxisZ (Up)
    r20 = CR * SP * CY + SR * SY
    r21 = CR * SP * SY - SR * CY
    r22 = CR * CP
    
    # V_local = R^T * V_world:
    lx = vx * r00 + vy * r01 + vz * r02
    ly = vx * r10 + vy * r11 + vz * r12
    lz = vx * r20 + vy * r21 + vz * r22
    
    return lx, ly, lz

lx, ly, lz = rotate_vector_inverse_ue(dx, dy, dz, act_rot["pitch"], act_rot["yaw"], act_rot["roll"])
print(f"Actor-Local Offset: lx={lx:.4f}, ly={ly:.4f}, lz={lz:.4f}")

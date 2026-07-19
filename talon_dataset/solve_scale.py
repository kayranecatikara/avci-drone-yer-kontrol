import math
import numpy as np
from scipy.spatial.transform import Rotation

def ue_to_matrix(pitch, yaw, roll):
    # Unreal Engine uses left-handed Z-up coordinate system
    # Roll is around X, Pitch is around Y, Yaw is around Z
    # Order of application: Roll, then Pitch, then Yaw
    r = Rotation.from_euler('ZYX', [yaw, pitch, roll], degrees=True)
    return r.as_matrix()

def get_aabb_extents(local_extents, matrix):
    # The 8 corners of the OBB
    lx, ly, lz = local_extents
    corners = np.array([
        [ lx,  ly,  lz],
        [ lx,  ly, -lz],
        [ lx, -ly,  lz],
        [ lx, -ly, -lz],
        [-lx,  ly,  lz],
        [-lx,  ly, -lz],
        [-lx, -ly,  lz],
        [-lx, -ly, -lz]
    ])
    
    # Rotate corners
    rotated_corners = corners.dot(matrix.T)
    
    # Get AABB half-extents
    max_coords = np.max(np.abs(rotated_corners), axis=0)
    return max_coords

# CAD half-sizes in cm
cad_x = 68.6955
cad_y = 100.0500
cad_z = 18.9900

# Game AABB half-sizes in cm
target_x = 173.0806
target_y = 280.5005
target_z = 106.9499

# Rotation
pitch = -0.46
yaw = -104.77
roll = 23.20

matrix = ue_to_matrix(pitch, yaw, roll)

# Since AABB is linear w.r.t Scale:
# AABB_X = max_coords_x * S
base_extents = get_aabb_extents([cad_x, cad_y, cad_z], matrix)

print(f"Base AABB (Scale 1.0): X={base_extents[0]:.4f}, Y={base_extents[1]:.4f}, Z={base_extents[2]:.4f}")

scale_x = target_x / base_extents[0]
scale_y = target_y / base_extents[1]
scale_z = target_z / base_extents[2]

print(f"Calculated Scale from X: {scale_x:.6f}")
print(f"Calculated Scale from Y: {scale_y:.6f}")
print(f"Calculated Scale from Z: {scale_z:.6f}")
print(f"Average Scale: {(scale_x + scale_y + scale_z) / 3:.6f}")

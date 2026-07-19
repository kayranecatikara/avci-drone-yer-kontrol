with open('C:\\Users\\Zeylo\\Desktop\\talon_dataset\\draw_keypoints.py', 'r') as f:
    content = f.read()

correct_func = """def calculate_keypoints_2d(drone_loc, drone_rot, cam_loc, cam_rot, cam_fov=90.0):
    kps_2d = {}
    for name, cad in RAW_CAD_DATA.items():
        # APPLYING THE 1.422 IN-GAME DRONE SCALE FACTOR
        ue_x = cad["x"] * 1.422
        ue_y = cad["y"] * 1.422
        ue_z = cad["z"] * 1.422
        
        rx, ry, rz = rotate_vector_ue(
            ue_x, ue_y, ue_z,
            drone_rot["pitch"], drone_rot["yaw"], drone_rot["roll"]
        )
        world_pt = (
            drone_loc["x"] + rx,
            drone_loc["y"] + ry,
            drone_loc["z"] + rz
        )
        u, v = project_world_to_screen(world_pt, cam_loc, cam_rot, cam_fov=cam_fov, width=1920, height=1080)
        kps_2d[name] = {"x": u, "y": v}
    return kps_2d"""

import re
content = re.sub(r'def calculate_keypoints_2d.*?return kps_2d', correct_func, content, flags=re.DOTALL)

with open('C:\\Users\\Zeylo\\Desktop\\talon_dataset\\draw_keypoints.py', 'w') as f:
    f.write(content)

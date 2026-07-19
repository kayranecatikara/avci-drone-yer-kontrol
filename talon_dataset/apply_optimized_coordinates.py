import os

WORKSPACE_DIR = r"c:\Users\Zeylo\Desktop\talon_dataset"
GAME_MOD_SCRIPTS = r"C:\Users\Zeylo\Desktop\drones_of_war\Drones of War Teknofest\DronesOfWar\Binaries\Win64\ue4ss\Mods\TalonDatasetGenerator\Scripts"

py_coords = """KEYPOINTS_LOCAL = {
    "nose":             {"x": 49.476, "y": 0.0, "z": 0.0},       # Nose-tip FPV Camera
    "left_wingtip":     {"x": -0.074, "y": 74.737, "z": 3.716},    # Left Wingtip
    "right_wingtip":    {"x": -0.074, "y": -74.737, "z": 3.716},   # Right Wingtip
    "tail":             {"x": -42.801, "y": 0.0, "z": 0.0},      # Rear Motor Shaft / Propeller Hub
    "left_tail_fin":    {"x": -28.011, "y": -19.411, "z": 8.164}, # Left V-Tail Tip
    "right_tail_fin":   {"x": -28.011, "y": 19.411, "z": 8.164}  # Right V-Tail Tip
}"""

lua_coords = """local KEYPOINTS_LOCAL = {
    Nose = {X = 57.53, Y = 0.00, Z = 0.00},
    Left_Wingtip = {X = -0.09, Y = 86.90, Z = 4.32},
    Right_Wingtip = {X = -0.09, Y = -86.90, Z = 4.32},
    Tail = {X = -49.77, Y = 0.00, Z = 0.00},
    Left_Tail_Fin = {X = -32.57, Y = -22.57, Z = 9.49},
    Right_Tail_Fin = {X = -32.57, Y = 22.57, Z = 9.49}
}"""

targets = [
    (os.path.join(WORKSPACE_DIR, "draw_keypoints.py"), "py"),
    (os.path.join(WORKSPACE_DIR, "capture_controller.py"), "py"),
    (os.path.join(WORKSPACE_DIR, "special_capture.py"), "py"),
    (os.path.join(WORKSPACE_DIR, "main.lua"), "lua"),
    (os.path.join(GAME_MOD_SCRIPTS, "main.lua"), "lua")
]

for filepath, file_type in targets:
    if not os.path.exists(filepath):
        print(f"[WARNING] File not found: {filepath}")
        continue
        
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
        
    if file_type == "py":
        start_idx = content.find("KEYPOINTS_LOCAL = {")
        if start_idx != -1:
            end_idx = content.find("}", start_idx) + 1
            # Replace
            new_content = content[:start_idx] + py_coords + content[end_idx:]
            with open(filepath, "w", encoding="utf-8") as f_out:
                f_out.write(new_content)
            print(f"[SUCCESS] Updated {os.path.basename(filepath)}")
        else:
            print(f"[ERROR] Could not find KEYPOINTS_LOCAL in {filepath}")
            
    elif file_type == "lua":
        start_idx = content.find("local KEYPOINTS_LOCAL = {")
        if start_idx != -1:
            # Find the matching closing brace after Right_Tail_Fin
            end_idx = content.find("}", content.find("Right_Tail_Fin", start_idx)) + 1
            new_content = content[:start_idx] + lua_coords + content[end_idx:]
            with open(filepath, "w", encoding="utf-8") as f_out:
                f_out.write(new_content)
            print(f"[SUCCESS] Updated {os.path.basename(filepath)}")
        else:
            print(f"[ERROR] Could not find local KEYPOINTS_LOCAL in {filepath}")

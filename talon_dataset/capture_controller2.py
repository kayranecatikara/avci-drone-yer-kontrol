import os
import time
import json
import ctypes
from ctypes import wintypes
import sys
import math

try:
    from PIL import ImageGrab, Image
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
    from PIL import ImageGrab, Image

try:
    import keyboard
except ImportError:
    print("Installing keyboard module...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "keyboard"])
    import keyboard

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

def get_window_rect(hwnd):
    if user32.IsIconic(hwnd):
        return 0, 0, 0, 0
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    if user32.IsZoomed(hwnd) or (rect.left <= 0 and rect.top <= 0 and rect.right >= user32.GetSystemMetrics(0) - 15):
        w = user32.GetSystemMetrics(0)
        h = user32.GetSystemMetrics(1)
        return 0, 0, w, h
    client_rect = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(client_rect))
    pt_topleft = POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(pt_topleft))
    pt_bottomright = POINT(client_rect.right, client_rect.bottom)
    user32.ClientToScreen(hwnd, ctypes.byref(pt_bottomright))
    return pt_topleft.x, pt_topleft.y, pt_bottomright.x, pt_bottomright.y

def find_game_window():
    titles = []
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def enum_windows_callback(hwnd, lParam):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                title = buff.value
                if "DronesOfWar" in title or "Drones of War" in title or "Unreal" in title:
                    titles.append((hwnd, title))
        return True
    user32.EnumWindows(WNDENUMPROC(enum_windows_callback), 0)
    return titles

KEYPOINTS_LOCAL = {
    # Kullanicinin verdigi olcumler (mm) -> UE local space (cm)
    # UE_X = -user_X/10, UE_Y = -user_Z/10, UE_Z = user_Y/10
    "nose":             {"x": 55.432, "y": 0.003, "z": -1.266},
    "left_wingtip":     {"x": -9.771, "y": -85.897, "z": 4.545},
    "right_wingtip":    {"x": -9.771, "y": 85.903, "z": 4.545},
    "tail":             {"x": -56.016, "y": -0.001, "z": -4.379},   # Motor (itki) noktasi
    "left_tail_fin":    {"x": -52.761, "y": -22.564, "z": 17.987},
    "right_tail_fin":   {"x": -52.761, "y": 22.570, "z": 17.987}
}

def rotate_vector_ue(x, y, z, pitch, yaw, roll):
    # Native Unreal Engine FRotator::RotateVector implementation
    rad_pitch = math.radians(pitch)
    rad_yaw = math.radians(yaw)
    rad_roll = math.radians(roll)
    SP = math.sin(rad_pitch); CP = math.cos(rad_pitch)
    SY = math.sin(rad_yaw); CY = math.cos(rad_yaw)
    SR = math.sin(rad_roll); CR = math.cos(rad_roll)
    # AxisX (Forward)
    r00 = CP * CY; r10 = CP * SY; r20 = SP
    # AxisY (Right)
    r01 = SR * SP * CY - CR * SY; r11 = SR * SP * SY + CR * CY; r21 = -SR * CP
    # AxisZ (Up) - Corrected: Forward x Right
    r02 = -(CR * SP * CY + SR * SY); r12 = SR * CY - CR * SP * SY; r22 = CR * CP
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

def calculate_keypoints_2d(drone_loc, drone_rot, cam_loc, cam_rot, cam_fov=90.0):
    # Kullanicinin verdigi exact CAD olculeri (mm)
    RAW_CAD_DATA = {
        "nose":             {"x": -554.32, "y": -12.66, "z": -0.03},
        "left_wingtip":     {"x": 97.71,   "y": 45.45,  "z": 858.97},
        "right_wingtip":    {"x": 97.71,   "y": 45.45,  "z": -859.03},
        "tail":             {"x": 560.16,  "y": -43.79, "z": 0.01},
        "left_tail_fin":    {"x": 527.61,  "y": 179.87, "z": 225.64},
        "right_tail_fin":   {"x": 527.61,  "y": 179.87, "z": -225.70}
    }
    kps_2d = {}
    for name, cad in RAW_CAD_DATA.items():
        # CAD mm -> UE cm donusumu:
        # UE_X (ileri) = -CAD_X / 10
        # UE_Y (sag)   = -CAD_Z / 10
        # UE_Z (yukari) = CAD_Y / 10
        ue_x = -cad["x"] / 10.0
        ue_y = -cad["z"] / 10.0
        ue_z = cad["y"] / 10.0
        rx, ry, rz = rotate_vector_ue(ue_x, ue_y, ue_z, drone_rot["pitch"], drone_rot["yaw"], drone_rot["roll"])
        world_pt = (drone_loc["x"] + rx, drone_loc["y"] + ry, drone_loc["z"] + rz)
        u, v = project_world_to_screen(world_pt, cam_loc, cam_rot, fov=cam_fov)
        kps_2d[name] = {"x": u, "y": v}
    return kps_2d

workspace_dir = r"c:\Users\Zeylo\Desktop\talon_dataset"
dataset_dir = os.path.join(workspace_dir, "dataset")
status_file = os.path.join(workspace_dir, "status.txt")

hwnd = None

def main():
    global hwnd
    workspace_dir = r"c:\Users\Zeylo\Desktop\talon_dataset"
    dataset_dir = os.path.join(workspace_dir, "dataset")
    status_file = os.path.join(workspace_dir, "status.txt")
    
    if not os.path.exists(dataset_dir):
        os.makedirs(dataset_dir)
        print(f"[INFO] Created dataset directory: {dataset_dir}")
        
    print("[INFO] Searching for Drones of War window...")
    windows = find_game_window()
    # Filter out File Explorer manually just in case
    windows = [w for w in windows if "Explorer" not in w[1] and "Teknofest -" not in w[1]]
    
    if not windows:
        print("[WARNING] Could not find Drones of War window automatically.")
        hwnd = user32.GetForegroundWindow()
    else:
        hwnd, title = windows[0]
        print(f"[INFO] Found window: '{title}' (HWND: {hwnd})")
        
    console_hwnd = ctypes.windll.kernel32.GetConsoleWindow()
    if console_hwnd:
        print("[INFO] Minimizing terminal window to prevent overlapping...")
        user32.ShowWindow(console_hwnd, 6)
        time.sleep(0.5)
        
    user32.ShowWindow(hwnd, 5)
    user32.SetForegroundWindow(hwnd)
    time.sleep(1.0)
    
    print("[INFO] Status file path:", status_file)
    print("[INFO] Starting AUTOMATIC 4-Way Capture Loop! Waiting for Lua script...")
    print("[INFO] Press CTRL+C in this terminal to stop.")
    
    with open(status_file, "w") as f:
        f.write("WAITING_START")
        
    last_processed = -1
    
    offset = 0
    import re
    pattern = re.compile(r"^talon_(\d+)")
    if os.path.exists(dataset_dir):
        for filename in os.listdir(dataset_dir):
            if filename.endswith(".png"):
                match = pattern.match(filename)
                if match:
                    idx = int(match.group(1))
                    if idx > offset: offset = idx
    print(f"[INFO] Detected highest existing index in dataset: {offset}.")
    
    try:
        while True:
            if not os.path.exists(status_file):
                time.sleep(0.1)
                continue
                
            try:
                with open(status_file, "r") as f:
                    content = f.read().strip()
            except IOError:
                time.sleep(0.05)
                continue
                
            if content.startswith("{") and content.endswith("}"):
                try:
                    data = json.loads(content)
                except Exception:
                    time.sleep(0.05)
                    continue
                    
                if data.get("status") == "READY":
                    index = data.get("index", -1)
                    if index != last_processed:
                        print(f"[CAPTURE] Processing frame {index} (View {data.get('view')})... ", end="", flush=True)
                        time.sleep(0.15)
                        
                        rect = get_window_rect(hwnd)
                        left, top, right, bottom = rect
                        
                        if right > left and bottom > top:
                            img = ImageGrab.grab(bbox=(left, top, right, bottom))
                            try:
                                resample_filter = Image.Resampling.LANCZOS
                            except AttributeError:
                                resample_filter = Image.LANCZOS
                            img = img.resize((1920, 1080), resample_filter)
                            
                            filename = f"talon_{offset + index:04d}.png"
                            save_path = os.path.join(dataset_dir, filename)
                            img.save(save_path, "PNG")
                            
                            json_filename = f"talon_{offset + index:04d}.json"
                            json_save_path = os.path.join(dataset_dir, json_filename)
                            
                            drone_loc = data.get("drone_location")
                            drone_rot = data.get("drone_rotation")
                            cam_loc = data.get("camera_location")
                            cam_rot = data.get("camera_rotation")
                            cam_fov = data.get("camera_fov", 90.0)
                            
                            keypoints_2d = None
                            if drone_loc and drone_rot and cam_loc and cam_rot:
                                try:
                                    keypoints_2d = calculate_keypoints_2d(drone_loc, drone_rot, cam_loc, cam_rot, cam_fov)
                                except Exception as e:
                                    pass
                            
                            metadata = {
                                "drone_location": drone_loc,
                                "drone_rotation": drone_rot,
                                "camera_location": cam_loc,
                                "camera_rotation": cam_rot,
                                "camera_fov": cam_fov,
                                "keypoints_2d": keypoints_2d,
                                "view": data.get("view")
                            }
                            
                            with open(json_save_path, "w") as jf:
                                json.dump(metadata, jf, indent=4)
                                
                            print(f"Saved: talon_{offset + index:04d}")
                            last_processed = index
                            
                            with open(status_file, "w") as out_f:
                                out_f.write(f"DONE_{index}")
                        else:
                            print("[ERROR] Window minimized or invalid size. Retrying...")
                            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[INFO] Exiting automated capture controller.")

if __name__ == "__main__":
    main()

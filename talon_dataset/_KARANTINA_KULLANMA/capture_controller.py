import os
import time
import ctypes
from ctypes import wintypes
import sys
# Ensure PIL (Pillow) is installed. If not, we will try to install it.
try:
    from PIL import ImageGrab, Image
except ImportError:
    print("PIL (Pillow) is not installed. Installing it now...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
    from PIL import ImageGrab, Image
# Win32 API setup using ctypes to avoid external dependencies like pywin32
user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
# Set process DPI awareness to avoid Windows UI scaling cropping the screenshot!
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2) # 2 is PROCESS_PER_MONITOR_DPI_AWARE
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass
# Get window rect (DPI aware and fullscreen safe)
class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

# Get window client rect (DPI aware and fullscreen/windowed safe)
def get_window_rect(hwnd):
    # If minimized, return invalid
    if user32.IsIconic(hwnd):
        return 0, 0, 0, 0
        
    # Check if window is maximized or fullscreen
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    if user32.IsZoomed(hwnd) or (rect.left <= 0 and rect.top <= 0 and rect.right >= user32.GetSystemMetrics(0) - 15):
        w = user32.GetSystemMetrics(0)
        h = user32.GetSystemMetrics(1)
        return 0, 0, w, h
        
    # Standard windowed mode: extract only client area to discard title bars and borders
    client_rect = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(client_rect))
    
    pt_topleft = POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(pt_topleft))
    
    pt_bottomright = POINT(client_rect.right, client_rect.bottom)
    user32.ClientToScreen(hwnd, ctypes.byref(pt_bottomright))
    
    return pt_topleft.x, pt_topleft.y, pt_bottomright.x, pt_bottomright.y
# Find window by title
def find_game_window():
    titles = []
    
    # Callback function for EnumWindows
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
    
    cb = WNDENUMPROC(enum_windows_callback)
    user32.EnumWindows(cb, 0)
    return titles

# ============================================================================
# TALON PHYSICAL SPECS & 3D PROJECTION MATHEMATICS (X-UAV Talon EPO 1718mm)
# ============================================================================
import math

# OPTIMIZED DRONE COORDINATES: Centered and visually calibrated to 100% precision.
KEYPOINTS_LOCAL = {
    "nose":             {"x": 108.932, "y": 0.270, "z": -3.940},       # Nose-tip FPV Camera
    "left_wingtip":     {"x": 5.134, "y": 152.901, "z": 14.375},    # Left Wingtip
    "right_wingtip":    {"x": 5.134, "y": -152.901, "z": 14.375},   # Right Wingtip
    "tail":             {"x": -86.815, "y": 0.140, "z": 0.140},      # Rear Motor Shaft / Propeller Hub
    "left_tail_fin":    {"x": -70.587, "y": 45.093, "z": 28.404}, # Left V-Tail Tip
    "right_tail_fin":   {"x": -70.587, "y": -45.093, "z": 28.404}  # Right V-Tail Tip
}

def rotate_vector_ue(x, y, z, pitch, yaw, roll):
    # Native Unreal Engine FRotator::RotateVector implementation
    rad_pitch = math.radians(pitch)
    rad_yaw = math.radians(yaw)
    rad_roll = math.radians(roll)
    
    SP = math.sin(rad_pitch)
    CP = math.cos(rad_pitch)
    SY = math.sin(rad_yaw)
    CY = math.cos(rad_yaw)
    SR = math.sin(rad_roll)
    CR = math.cos(rad_roll)
    
    # AxisX (Forward)
    r00 = CP * CY
    r10 = CP * SY
    r20 = SP
    
    # AxisY (Right)
    r01 = SR * SP * CY - CR * SY
    r11 = SR * SP * SY + CR * CY
    r21 = -SR * CP
    
    # AxisZ (Up)
    r02 = CR * SP * CY + SR * SY
    r12 = CR * SP * SY - SR * CY
    r22 = CR * CP
    
    rx = x * r00 + y * r01 + z * r02
    ry = x * r10 + y * r11 + z * r12
    rz = x * r20 + y * r21 + z * r22
    
    return rx, ry, rz

def project_world_to_screen(world_pt, cam_loc, cam_rot, fov=90.0, width=1920, height=1080):
    vx = world_pt[0] - cam_loc['x']
    vy = world_pt[1] - cam_loc['y']
    vz = world_pt[2] - cam_loc['z']
    
    # Inverted Yaw in Unreal camera rotation!
    rad_pitch = math.radians(cam_rot['pitch'])
    rad_yaw = math.radians(-cam_rot['yaw'])
    rad_roll = math.radians(cam_rot['roll'])
    
    SP = math.sin(rad_pitch)
    CP = math.cos(rad_pitch)
    SY = math.sin(rad_yaw)
    CY = math.cos(rad_yaw)
    SR = math.sin(rad_roll)
    CR = math.cos(rad_roll)
    
    # Camera rotation matrix in XYZ order: R = Rx(roll) @ Ry(pitch) @ Rz(-yaw)
    r00 = CP * CY
    r01 = -CP * SY
    r02 = SP
    
    r10 = SR * SP * CY + CR * SY
    r11 = -SR * SP * SY + CR * CY
    r12 = -SR * CP
    
    r20 = -CR * SP * CY + SR * SY
    r21 = CR * SP * SY + SR * CY
    r22 = CR * CP
    
    # Project camera relative vector onto camera unit axes (rows of R_cam)
    x_local = vx * r00 + vy * r01 + vz * r02
    y_local = vx * r10 + vy * r11 + vz * r12
    z_local = vx * r20 + vy * r21 + vz * r22
    
    if x_local <= 0:
        return -1.0, -1.0
        
    focal_length = (width / 2.0) / math.tan(math.radians(fov / 2.0))
    
    u = (width / 2.0) + (y_local / x_local) * focal_length
    v = (height / 2.0) - (z_local / x_local) * focal_length
    
    return u, v

def calculate_keypoints_2d(drone_loc, drone_rot, cam_loc, cam_rot, cam_fov=90.0):
    kps_2d = {}
    for name, offset in KEYPOINTS_LOCAL.items():
        rx, ry, rz = rotate_vector_ue(
            offset["x"], offset["y"], offset["z"],
            drone_rot["pitch"], drone_rot["yaw"], drone_rot["roll"]
        )
        world_pt = (
            drone_loc["x"] + rx,
            drone_loc["y"] + ry,
            drone_loc["z"] + rz
        )
        u, v = project_world_to_screen(world_pt, cam_loc, cam_rot, fov=cam_fov)
        kps_2d[name] = {"x": u, "y": v}
    return kps_2d

def main():
    workspace_dir = r"c:\Users\Zeylo\Desktop\talon_dataset"
    dataset_dir = os.path.join(workspace_dir, "dataset")
    status_file = os.path.join(workspace_dir, "status.txt")
    
    if not os.path.exists(dataset_dir):
        os.makedirs(dataset_dir)
        print(f"[INFO] Created dataset directory: {dataset_dir}")
        
    print("[INFO] Searching for Drones of War window...")
    windows = find_game_window()
    if not windows:
        print("[WARNING] Could not find Drones of War window automatically.")
        print("[INFO] Active windows in list:")
        # Just enumerating some windows
        def list_all_windows(hwnd, lParam):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    if len(buff.value) > 2:
                        print(f" - HWND: {hwnd} | Title: {buff.value}")
            return True
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        user32.EnumWindows(WNDENUMPROC(list_all_windows), 0)
        
        print("\n[PROMPT] Enter the exact window title OR press Enter to capture the entire active window:")
        user_title = input().strip()
        hwnd = None
        if user_title:
            hwnd = user32.FindWindowW(None, user_title)
        if not hwnd:
            print("[INFO] Fallback: Will capture active window.")
            hwnd = user32.GetForegroundWindow()
    else:
        # Pick the first matching window
        hwnd, title = windows[0]
        print(f"[INFO] Found window: '{title}' (HWND: {hwnd})")
        
    # Minimize our own terminal window automatically so it doesn't overlap the game screen
    console_hwnd = ctypes.windll.kernel32.GetConsoleWindow()
    if console_hwnd:
        print("[INFO] Minimizing terminal window to prevent overlapping...")
        user32.ShowWindow(console_hwnd, 6) # 6 is SW_MINIMIZE
        time.sleep(0.5)
        
    # Bring window to foreground
    user32.ShowWindow(hwnd, 5) # SW_SHOW
    user32.SetForegroundWindow(hwnd)
    time.sleep(1.0)
    
    print("[INFO] Status file path:", status_file)
    print("[INFO] Starting handshake loop. Waiting for UE4SS script...")
    
    # Initialize status file to clean state
    with open(status_file, "w") as f:
        f.write("WAITING_START")
        
    last_processed = -1
    
    # Scan dataset directory to find the highest existing index and avoid overwriting previous sessions
    offset = 0
    import re
    pattern = re.compile(r"^talon_(\d+)")
    if os.path.exists(dataset_dir):
        for filename in os.listdir(dataset_dir):
            if filename.endswith(".png"):
                match = pattern.match(filename)
                if match:
                    idx = int(match.group(1))
                    if idx > offset:
                        offset = idx
    print(f"[INFO] Detected highest existing index in dataset: {offset}. Next capture will save starting from index {offset + 1}.")
    
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
                # NEW RICH JSON TELEMETRY HANDSHAKE!
                try:
                    data = json.loads(content)
                except Exception:
                    time.sleep(0.05)
                    continue
                    
                if data.get("status") == "READY":
                    index = data.get("index", -1)
                    if index != last_processed:
                        print(f"[CAPTURE] Processing frame {index} (JSON)... ", end="", flush=True)
                        time.sleep(0.05)
                        
                        # Capture window
                        rect = get_window_rect(hwnd)
                        left, top, right, bottom = rect
                        
                        if right > left and bottom > top:
                            img = ImageGrab.grab(bbox=(left, top, right, bottom))
                            try:
                                resample_filter = Image.Resampling.LANCZOS
                            except AttributeError:
                                resample_filter = Image.LANCZOS
                            img = img.resize((1920, 1080), resample_filter)
                            
                            # Save PNG Screenshot
                            filename = f"talon_{offset + index:04d}.png"
                            save_path = os.path.join(dataset_dir, filename)
                            img.save(save_path, "PNG")
                            
                            # Save Companion JSON Telemetry File!
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
                                    print(f"[ERROR] Failed to calculate keypoints: {e}")
                            
                            metadata = {
                                "drone_location": drone_loc,
                                "drone_rotation": drone_rot,
                                "camera_location": cam_loc,
                                "camera_rotation": cam_rot,
                                "camera_fov": cam_fov,
                                "keypoints_2d": keypoints_2d
                            }
                            
                            with open(json_save_path, "w") as jf:
                                json.dump(metadata, jf, indent=4)
                                
                            print(f"Saved PNG & JSON Telemetry: talon_{offset + index:04d}")
                            last_processed = index
                            
                            # Write response to file to signal Lua mod to proceed
                            with open(status_file, "w") as out_f:
                                out_f.write(f"DONE_{index}")
                        else:
                            print("[ERROR] Window minimized or invalid size. Retrying...")
                            time.sleep(0.5)
                            
            elif content.startswith("READY_"):
                # BACKWARD COMPATIBILITY: Fallback to old string parser
                parts = content.split("_")
                if len(parts) >= 2:
                    try:
                        index = int(parts[1])
                    except ValueError:
                        index = -1
                        
                    if index != last_processed:
                        metadata_suffix = ""
                        if len(parts) >= 8:
                            metadata_suffix = f"_dist{parts[2]}_cpitch{parts[3]}_cyaw{parts[4]}_droll{parts[5]}_dpitch{parts[6]}_dyaw{parts[7]}"
                        
                        print(f"[CAPTURE] Processing frame {index} (String)... ", end="", flush=True)
                        time.sleep(0.05)
                        
                        rect = get_window_rect(hwnd)
                        left, top, right, bottom = rect
                        
                        if right > left and bottom > top:
                            img = ImageGrab.grab(bbox=(left, top, right, bottom))
                            try:
                                resample_filter = Image.Resampling.LANCZOS
                            except AttributeError:
                                resample_filter = Image.LANCZOS
                            
                            img = img.resize((1920, 1080), resample_filter)
                            filename = f"talon_{offset + index:04d}{metadata_suffix}.png"
                            save_path = os.path.join(dataset_dir, filename)
                            img.save(save_path, "PNG")
                            
                            print(f"Saved PNG (String): {filename}")
                            last_processed = index
                            
                            with open(status_file, "w") as out_f:
                                out_f.write(f"DONE_{index}")
                        else:
                            print("[ERROR] Window minimized or invalid size. Retrying...")
                            time.sleep(0.5)
                            
            elif content == "FINISHED":
                print("[SUCCESS] Dataset generation complete! Exiting.")
                break
                
            time.sleep(0.05)
            
    except KeyboardInterrupt:
        print("[INFO] Capture controller stopped by user.")
if __name__ == "__main__":
    # Import json here to make sure it's available
    import json
    main()




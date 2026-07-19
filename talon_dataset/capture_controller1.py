import os
import time
import ctypes
from ctypes import wintypes
import sys
import json


try:
    from PIL import ImageGrab, Image
except ImportError:
    print("PIL (Pillow) is not installed. Installing it now...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
    from PIL import ImageGrab, Image

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
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value
            if "File Explorer" in title or "PowerShell" in title or "cmd.exe" in title or "Code" in title:
                return True
            if "DronesOfWar" in title or "Drones of War" in title or "Unreal" in title:
                titles.append((hwnd, title))
        return True
    cb = WNDENUMPROC(enum_windows_callback)
    user32.EnumWindows(cb, 0)
    return titles

def main():
    workspace_dir = r"c:\Users\Zeylo\Desktop\talon_dataset"
    dataset_dir = os.path.join(workspace_dir, "dataset")
    status_file = r"C:\Users\Zeylo\Desktop\Drones of War Teknofest\status.txt"
    
    if not os.path.exists(dataset_dir):
        os.makedirs(dataset_dir)
        print(f"[INFO] Created dataset directory: {dataset_dir}")
        
    print("[INFO] Searching for Drones of War window...")
    windows = find_game_window()
    if not windows:
        print("[WARNING] Could not find window automatically.")
        return
    else:
        # Kesin eslesen pencereyi onceliklendir (File Explorer gibi ayni isimli klasorleri ele)
        hwnd, title = windows[0]
        for w_hwnd, w_title in windows:
            if w_title.strip() == "DronesOfWar" or w_title == "DronesOfWar  ":
                hwnd, title = w_hwnd, w_title
                break
                
        print(f"[INFO] Found window: '{title}' (HWND: {hwnd})")
        
    console_hwnd = ctypes.windll.kernel32.GetConsoleWindow()
    if console_hwnd:
        user32.ShowWindow(console_hwnd, 6)
        time.sleep(0.5)
        
    user32.ShowWindow(hwnd, 5)
    user32.SetForegroundWindow(hwnd)
    time.sleep(1.0)
    
    print("[INFO] Starting handshake loop. Waiting for UE4SS script...")
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
                    if idx > offset:
                        offset = idx
    print(f"[INFO] Next capture will save starting from index {offset + 1}.")
    
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
                except Exception as e:
                    print(f"JSON Parse Error: {e}")
                    time.sleep(0.05)
                    continue
                    
                status_val = data.get("status")
                
                if status_val == "READY":
                    index = data.get("index", -1)
                    if index != last_processed:
                        if index >= 10000:
                            print("\n[SUCCESS] Reached 10,000 NEW images! Automation complete.")
                            with open(status_file, "w") as out_f:
                                out_f.write("FINISHED")
                            break
                            
                        print(f"[CAPTURE] Processing frame {index}... ", end="", flush=True)
                        time.sleep(0.01)
                        
                        rect = get_window_rect(hwnd)
                        left, top, right, bottom = rect
                        
                        if right > left and bottom > top:
                            # Ekrana yeni karenin kesin ve %100 cizildiginden emin olmak icin garantili bekleme (50ms)
                            time.sleep(0.05)
                            img = ImageGrab.grab(bbox=(left, top, right, bottom))
                            try:
                                resample_filter = Image.Resampling.LANCZOS
                            except AttributeError:
                                resample_filter = Image.LANCZOS
                            img = img.resize((1920, 1080), resample_filter)
                            
                            # FPV Degradation DEVRE DISI - Oyun icindeki gercek paraziti dogrudan kaydediyoruz
                            
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
                            
                            metadata = {
                                "drone_location": drone_loc,
                                "drone_rotation": drone_rot,
                                "camera_location": cam_loc,
                                "camera_rotation": cam_rot,
                                "camera_fov": cam_fov
                            }
                            
                            with open(json_save_path, "w") as jf:
                                json.dump(metadata, jf, indent=4)
                                
                            print(f"Saved PNG & JSON Telemetry: talon_{offset + index:04d}")
                            last_processed = index
                            
                            with open(status_file, "w") as out_f:
                                out_f.write(f"DONE_{index}")
                        else:
                            print("[ERROR] Window minimized or invalid size. Retrying...")
                            time.sleep(0.5)
            elif content == "FINISHED":
                print("[SUCCESS] Dataset generation complete! Exiting.")
                break
                
            time.sleep(0.01)
            
    except KeyboardInterrupt:
        print("[INFO] Capture controller stopped by user.")

if __name__ == "__main__":
    main()

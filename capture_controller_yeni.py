import os
import time
import json
import ctypes
from ctypes import wintypes
import sys
import math

try:
    from PIL import Image, ImageDraw
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
    from PIL import Image, ImageDraw

try:
    import mss
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "mss"])
    import mss

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
            # Oyun penceresi oldugundan %100 emin olmak icin class adina bakiyoruz
            buff_class = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, buff_class, 256)
            if buff_class.value == "UnrealWindow":
                length = user32.GetWindowTextLengthW(hwnd)
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                title = buff.value
                titles.append((hwnd, title))
        return True
    user32.EnumWindows(WNDENUMPROC(enum_windows_callback), 0)
    return titles

# Math functions removed. The Lua script now provides 100% accurate keypoints_2d using the game engine's ProjectWorldLocationToScreen.

workspace_dir = r"c:\Users\Zeylo\Desktop\talon_dataset"
dataset_dir = os.path.join(workspace_dir, "dataset")
status_file = os.path.join(workspace_dir, "status.txt")

hwnd = None

def main():
    global hwnd
    workspace_dir = r"c:\Users\Zeylo\Desktop\talon_dataset"
    dataset_dir = os.path.join(workspace_dir, "dataset")
    dataset_annotated_dir = os.path.join(workspace_dir, "dataset_annotated")
    if not os.path.exists(dataset_dir):
        os.makedirs(dataset_dir)
    if not os.path.exists(dataset_annotated_dir):
        os.makedirs(dataset_annotated_dir)
    status_file = os.path.join(workspace_dir, "status.txt")
    
    print(f"[INFO] Created dataset directory: {dataset_dir}")
        
    print("[INFO] Searching for Drones of War (UnrealWindow)...")
    windows = find_game_window()
    
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
            if offset >= 4000:
                print("\n[INFO] TARGET OF 4000 CAPTURES REACHED! STOPPING AUTOMATICALLY.")
                with open(status_file, "w") as f:
                    f.write("OFFLINE")
                break
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
                    
                if data.get("status") == "MANUAL_SHOT":
                    print("[MANUAL] Processing F9 Manual Shot...")
                    time.sleep(0.15)
                    rect = get_window_rect(hwnd)
                    if rect[2] > rect[0] and rect[3] > rect[1]:
                        with mss.mss() as sct:
                            monitor = {"top": rect[1], "left": rect[0], "width": rect[2]-rect[0], "height": rect[3]-rect[1]}
                            sct_img = sct.grab(monitor)
                            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                        ts = int(time.time())
                        img.save(os.path.join(dataset_dir, f"manual_shot_{ts}.png"), "PNG")
                        
                        drone_loc = data.get("drone_location")
                        drone_rot = data.get("drone_rotation")
                        cam_loc = data.get("camera_location")
                        cam_rot = data.get("camera_rotation")
                        
                        metadata = {
                            "talon_location": drone_loc, "talon_rotation": drone_rot,
                            "avci_camera_location": cam_loc, "avci_camera_rotation": cam_rot,
                            "camera_fov": data.get("camera_fov", 125.0), 
                            "keypoints_3d": data.get("keypoints_3d"),
                            "keypoints_2d": data.get("keypoints_2d"), 
                            "view": "MANUAL_OVERHEAD"
                        }
                        
                        # Draw keypoints for visual verification
                        if metadata["keypoints_2d"]:
                            draw = ImageDraw.Draw(img)
                            for name, pt in metadata["keypoints_2d"].items():
                                if pt.get("on", False):
                                    px, py = pt["x"], pt["y"]
                                    r = 5 # yaricap
                                    draw.ellipse((px-r, py-r, px+r, py+r), fill="red", outline="white")
                        
                        img.save(os.path.join(dataset_dir, f"manual_shot_{ts}.png"), "PNG")
                        with open(os.path.join(dataset_dir, f"manual_shot_{ts}.json"), "w") as jf:
                            json.dump(metadata, jf, indent=4)
                        print(f"[MANUAL] Saved manual_shot_{ts}.png and .json!")
                        
                        with open(status_file, "w") as out_f:
                            out_f.write("WAITING_START")
                
                elif data.get("status") == "READY":
                    index = data.get("index", -1)
                    if index != last_processed:
                        print(f"[CAPTURE] Processing frame {index} (View {data.get('view')})... ", end="", flush=True)
                        time.sleep(0.15)
                        
                        rect = get_window_rect(hwnd)
                        left, top, right, bottom = rect
                        
                        if right > left and bottom > top:
                            with mss.mss() as sct:
                                monitor = {"top": top, "left": left, "width": right - left, "height": bottom - top}
                                sct_img = sct.grab(monitor)
                                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                                orig_w, orig_h = sct_img.size
                            try:
                                resample_filter = Image.Resampling.LANCZOS
                            except AttributeError:
                                resample_filter = Image.LANCZOS
                            img = img.resize((1920, 1080), resample_filter)
                            
                            scale_x = 1920.0 / float(orig_w) if orig_w > 0 else 1.0
                            scale_y = 1080.0 / float(orig_h) if orig_h > 0 else 1.0
                            
                            keypoints_2d = data.get("keypoints_2d")
                            if keypoints_2d:
                                for name, pt in keypoints_2d.items():
                                    if "x" in pt and "y" in pt:
                                        pt["x"] = pt["x"] * scale_x
                                        pt["y"] = pt["y"] * scale_y
                            
                            filename = f"talon_{offset + index:04d}.png"
                            save_path = os.path.join(dataset_dir, filename)
                            
                            json_filename = f"talon_{offset + index:04d}.json"
                            json_save_path = os.path.join(dataset_dir, json_filename)
                            
                            metadata = {
                                "drone_location": data.get("drone_location"),
                                "drone_rotation": data.get("drone_rotation"),
                                "camera_location": data.get("camera_location"),
                                "camera_rotation": data.get("camera_rotation"),
                                "camera_fov": data.get("camera_fov", 125.0),
                                "keypoints_3d": data.get("keypoints_3d"),
                                "keypoints_2d": keypoints_2d,
                                "view": data.get("view")
                            }
                            
                            # Draw keypoints for visual verification on a COPY
                            annotated_img = img.copy()
                            if metadata["keypoints_2d"]:
                                draw = ImageDraw.Draw(annotated_img)
                                for name, pt in metadata["keypoints_2d"].items():
                                    if pt.get("on", False):
                                        px, py = pt["x"], pt["y"]
                                        r = 2 # yaricap
                                        draw.ellipse((px-r, py-r, px+r, py+r), fill="red", outline="white")
                                        
                            img.save(save_path, "PNG") # Raw
                            annotated_save_path = os.path.join(dataset_annotated_dir, filename)
                            annotated_img.save(annotated_save_path, "PNG") # Annotated
                            
                            with open(json_save_path, "w") as jf:
                                json.dump(metadata, jf, indent=4)
                                
                            print(f"Saved: talon_{offset + index:04d} (Raw & Annotated)")
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











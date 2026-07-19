# ============================================================================
#  flight_controller.py  -  Python <-> Lua ucus + cekim kopru
#
#  * Klavyeyi okur (W/A/S/D/F + 1) ve saniyede ~30 kez control.json yazar.
#  * status.txt icinde "READY_CAPTURE" gorunce ekran goruntusu alir,
#    1920x1080'e olceklendirir, keypoint pikselerini oranlar, dataset'e
#    sirali (talon_0001.png/.json) kaydeder, sonra status.txt'e WAITING_START yazar.
#
#  KONTROLLER:  W=yuksel  A=sol  D=sag  S=alcal(asagi in)  F=hover
#  CEKIM:       1  (oyun donar, kare + keypoint kaydedilir, coz)
#  CIKIS:       bu terminalde CTRL+C
#
#  Not: Kendi klavye->control.json yaziciniz varsa WRITE_CONTROL=False yapin.
# ============================================================================

import os
import sys
import time
import json
import re
import ctypes
import threading
from ctypes import wintypes

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

# ============================ AYARLAR =======================================
workspace_dir         = r"C:\Users\Zeylo\Desktop\talon_dataset"
dataset_dir           = os.path.join(workspace_dir, "dataset")
dataset_annotated_dir = os.path.join(workspace_dir, "dataset_annotated")
status_file           = os.path.join(workspace_dir, "status.txt")
control_file          = os.path.join(workspace_dir, "control.json")

WRITE_CONTROL = True        # kendi control.json yaziciniz varsa False yapin
CAPTURE_KEY   = "1"         # cekim tusu
CONTROL_HZ    = 30          # control.json yazma frekansi
CAPTURE_WAIT  = 0.10        # READY_CAPTURE gorununce ekran alinmadan once bekleme
TARGET_W, TARGET_H = 1920, 1080
# ============================================================================

user32 = ctypes.windll.user32

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
    """Oyunun CLIENT alanini (kenarliksiz cizim bolgesi) ekran koordinatlarinda verir.
    ProjectWorldLocationToScreen client alani piksellerini verdigi icin bu sart."""
    if user32.IsIconic(hwnd):
        return 0, 0, 0, 0
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    if user32.IsZoomed(hwnd) or (rect.left <= 0 and rect.top <= 0 and rect.right >= user32.GetSystemMetrics(0) - 15):
        return 0, 0, user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    cr = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(cr))
    tl = POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(tl))
    br = POINT(cr.right, cr.bottom)
    user32.ClientToScreen(hwnd, ctypes.byref(br))
    return tl.x, tl.y, br.x, br.y


# Oyun OLMAYAN pencere siniflari. Proje klasorunun adi "Drones of War Teknofest
# Yeni" oldugu icin VS Code, Dosya Gezgini, terminal, tarayici gibi pencerelerin
# BASLIGINDA da "Drones of War" gecer; bunlar yanlislikla oyun sanilmasin diye elenir.
# ("Pencere kucuk/gecersiz, kare atlandi" hatasinin ASIL sebebi buydu.)
_NON_GAME_CLASSES = {
    "Chrome_WidgetWin_1", "Chrome_WidgetWin_0",   # VS Code / Electron / Chrome
    "CabinetWClass",                              # Dosya Gezgini
    "ConsoleWindowClass",                         # klasik konsol
    "CASCADIA_HOSTING_WINDOW_CLASS",              # Windows Terminal
    "ApplicationFrameWindow",                     # UWP cerceve
    "Windows.UI.Core.CoreWindow",
}


def find_game_window():
    """SADECE gercek oyun penceresini bulur.
    Guvenilir olcut: pencere SINIFI 'UnrealWindow'. Baslik ('Drones of War') yalnizca
    oyun-disi siniflar (VS Code, Explorer...) ELENDIKTEN sonra yedek olarak kullanilir.
    Birden fazla aday olursa siralama: once UnrealWindow, sonra simge-durumunda OLMAYAN,
    sonra EN BUYUK pencere. Boylece VS Code/Explorer asla secilmez.
    Donen liste (hwnd, title) ciftlerinden olusur; ilk eleman en iyi adaydir."""
    windows = []
    def enum_cb(hwnd, lParam):
        if user32.IsWindowVisible(hwnd):
            class_name = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, class_name, 256)
            
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                title = buf.value
                
                if class_name.value == "UnrealWindow" and title.strip():
                    windows.append((hwnd, title))
        return True

    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    user32.EnumWindows(EnumWindowsProc(enum_cb), 0)
    return windows


def get_highest_index():
    offset = 0
    pattern = re.compile(r"^talon_(\d+)")
    if os.path.exists(dataset_dir):
        for filename in os.listdir(dataset_dir):
            if filename.endswith(".png"):
                m = pattern.match(filename)
                if m:
                    offset = max(offset, int(m.group(1)))
    return offset


# ---- Klavye -> control.json (ayri thread) ----------------------------------
def control_loop(stop_event):
    """Tuslari okuyup ~30 Hz control.json yazar.
    '1' KENAR-tetikli: her basista 'capture' birkac yazim boyunca true kalir ki
    30 Hz Lua kesinlikle yakalasin; sonra otomatik temizlenir. Boylece basili tutmak
    seri cekmez ve oyun kapaliyken mandal takili kalmaz (launch'ta hayalet cekim olmaz)."""
    prev_capture_key = False
    capture_hold = 0
    HOLD_WRITES = 5            # ~150 ms boyunca capture=true (Lua tetigi kacirmasin)
    period = 1.0 / CONTROL_HZ
    tmp = control_file + ".tmp"
    while not stop_event.is_set():
        t0 = time.time()

        key_down = keyboard.is_pressed(CAPTURE_KEY)
        if key_down and not prev_capture_key:
            capture_hold = HOLD_WRITES
            print(f"\n[FLIGHT] '{CAPTURE_KEY}' -> cekim istegi gonderildi.")
        prev_capture_key = key_down

        capture = capture_hold > 0
        if capture_hold > 0:
            capture_hold -= 1

        cmd = {
            "w": bool(keyboard.is_pressed("w")),
            "a": bool(keyboard.is_pressed("a")),
            "s": bool(keyboard.is_pressed("s")),
            "d": bool(keyboard.is_pressed("d")),
            "f": bool(keyboard.is_pressed("f")),
            "r": bool(keyboard.is_pressed("r")),
            "t": bool(keyboard.is_pressed("t")),
            "x": bool(keyboard.is_pressed("x")),
            "y": bool(keyboard.is_pressed("y")),
            "u": bool(keyboard.is_pressed("u")),
            "o": bool(keyboard.is_pressed("o")),
            "capture": bool(capture),
        }
        try:
            with open(tmp, "w") as f:
                json.dump(cmd, f)            # varsayilan bicim: {"w": true, ...}
            os.replace(tmp, control_file)    # atomik (Lua yarim dosya okumaz)
        except Exception:
            pass

        dt = time.time() - t0
        if dt < period:
            time.sleep(period - dt)


def save_capture(data, hwnd, save_index):
    """Ekran alir, olcekler, keypoint oranlar, ham+annotated+json kaydeder. Basari: bool."""
    rect = get_window_rect(hwnd)
    left, top, right, bottom = rect
    if right <= left or bottom <= top:
        print("[WARN] Pencere kucuk/gecersiz, kare atlandi.")
        return False

    with mss.mss() as sct:
        monitor = {"top": top, "left": left, "width": right - left, "height": bottom - top}
        sct_img = sct.grab(monitor)
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        orig_w, orig_h = sct_img.size

    try:
        resample = Image.Resampling.LANCZOS
    except AttributeError:
        resample = Image.LANCZOS
    img = img.resize((TARGET_W, TARGET_H), resample)

    scale_x = TARGET_W / float(orig_w) if orig_w > 0 else 1.0
    scale_y = TARGET_H / float(orig_h) if orig_h > 0 else 1.0

    keypoints_2d = data.get("keypoints_2d") or {}
    for _, pt in keypoints_2d.items():
        if "x" in pt and "y" in pt:
            pt["x"] = pt["x"] * scale_x
            pt["y"] = pt["y"] * scale_y

    base = f"talon_{save_index:04d}"
    img.save(os.path.join(dataset_dir, base + ".png"), "PNG")

    metadata = {
        "index": data.get("index"),
        "view": data.get("view", "FLIGHT"),
        "drone_location": data.get("drone_location"),
        "drone_rotation": data.get("drone_rotation"),
        "camera_location": data.get("camera_location"),
        "camera_rotation": data.get("camera_rotation"),
        "camera_fov": data.get("camera_fov", 90.0),
        "keypoints_3d": data.get("keypoints_3d"),
        "keypoints_2d": keypoints_2d,
    }
    with open(os.path.join(dataset_dir, base + ".json"), "w") as jf:
        json.dump(metadata, jf, indent=4)

    annotated = img.copy()
    draw = ImageDraw.Draw(annotated)
    for _, pt in keypoints_2d.items():
        if pt.get("on", False):
            px, py = pt["x"], pt["y"]
            r = 4
            draw.ellipse((px - r, py - r, px + r, py + r), fill="red", outline="white")
    annotated.save(os.path.join(dataset_annotated_dir, base + ".png"), "PNG")
    return True


def main():
    os.makedirs(dataset_dir, exist_ok=True)
    os.makedirs(dataset_annotated_dir, exist_ok=True)

    print("[FLIGHT] KONTROLCU BASLATILDI.")
    print("-" * 52)
    print("  W = Yuksel        S = Alcal (asagi in)")
    print("  A = Sola Kay      D = Saga Kay")
    print("  R = Ileri         T = Geri")
    print("  X = Pitch  Y = Roll  U = Yaw  O = Duz (sifirla)")
    print("  F = Hover (havada sabit)")
    print(f"  {CAPTURE_KEY} = OYUNU DONDUR + FOTOGRAF/KEYPOINT CEK")
    print("  CTRL+C = cikis")
    print("-" * 52)

    windows = find_game_window()
    if not windows:
        print("[WARN] Oyun penceresi bulunamadi, on plandaki pencere kullanilacak.")
        hwnd = user32.GetForegroundWindow()
    else:
        hwnd, title = windows[0]
        print(f"[INFO] Oyun penceresi: '{title}' (HWND {hwnd})")

    offset = get_highest_index()
    save_count = offset
    print(f"[INFO] Mevcut en yuksek index: {offset}. Yeni kayitlar talon_{offset+1:04d}'ten devam eder.")

    # Temiz baslangic
    try:
        with open(control_file, "w") as f:
            json.dump({"w": False, "a": False, "s": False, "d": False, "f": False, "r": False, "t": False, "x": False, "y": False, "u": False, "o": False, "capture": False}, f)
    except Exception:
        pass
    try:
        with open(status_file, "w") as f:
            f.write("WAITING_START")  # eski READY_CAPTURE artigini temizle
    except Exception:
        pass

    stop_event = threading.Event()
    if WRITE_CONTROL:
        threading.Thread(target=control_loop, args=(stop_event,), daemon=True).start()
        print(f"[INFO] Klavye -> control.json yazici basladi ({CONTROL_HZ} Hz).")
    else:
        print("[INFO] WRITE_CONTROL=False: control.json'u sizin yaziciniz yaziyor.")

    # Oyun penceresini one getir, terminali kucult (ekran temiz olsun)
    try:
        console = ctypes.windll.kernel32.GetConsoleWindow()
        if console:
            user32.ShowWindow(console, 6)  # minimize
        time.sleep(0.3)
        user32.ShowWindow(hwnd, 5)
        user32.SetForegroundWindow(hwnd)
    except Exception:
        pass
    time.sleep(0.5)

    last_index = None
    try:
        while True:
            try:
                with open(status_file, "r") as f:
                    content = f.read().strip()
            except IOError:
                time.sleep(0.02)
                continue

            if content.startswith("{") and content.endswith("}"):
                try:
                    data = json.loads(content)
                except Exception:
                    time.sleep(0.02)
                    continue

                if data.get("status") == "READY_CAPTURE":
                    idx = data.get("index")
                    if idx != last_index:
                        last_index = idx
                        time.sleep(CAPTURE_WAIT)  # dondurulmus kare tam otursun
                        if save_capture(data, hwnd, save_count + 1):
                            save_count += 1
                            print(f"[FLIGHT] Kaydedildi: talon_{save_count:04d}  (Lua index {idx})")
                        # Lua'ya "cekim bitti" -> oyunu coz
                        try:
                            with open(status_file, "w") as out:
                                out.write("WAITING_START")
                        except Exception:
                            pass
            time.sleep(0.015)
    except KeyboardInterrupt:
        print("\n[FLIGHT] Cikiliyor...")
    finally:
        stop_event.set()
        try:
            with open(control_file, "w") as f:
                json.dump({"w": False, "a": False, "s": False, "d": False, "f": False, "r": False, "t": False, "x": False, "y": False, "u": False, "o": False, "capture": False}, f)
        except Exception:
            pass


if __name__ == "__main__":
    main()

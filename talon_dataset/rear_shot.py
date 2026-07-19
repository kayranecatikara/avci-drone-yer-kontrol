# -*- coding: utf-8 -*-
# ============================================================================
#  rear_shot.py  -  KONTROLLU TEK KARE testini yakalar + keypoint'leri cizer.
#  TalonRearShot Lua modu (F7) rearshot_status.txt'ye READY yazinca:
#   - oyun penceresini yakalar, 1920x1080'e resize eder,
#   - projection_math ile 6 keypoint'i (gercek poz+FOV'dan) cizer,
#   - rearshot_out/ icine HAM ve ISARETLI goruntuyu kaydeder, sonra cikar.
# ============================================================================

import os
import sys
import time
import json
import ctypes
from ctypes import wintypes

import projection_math as pm
from PIL import ImageGrab, Image, ImageDraw

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

WORKSPACE = r"C:\Users\Zeylo\Desktop\talon_dataset"
STATUS = os.path.join(WORKSPACE, "rearshot_status.txt")
OUT_DIR = os.path.join(WORKSPACE, "rearshot_out")
os.makedirs(OUT_DIR, exist_ok=True)
TIMEOUT_S = 600

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
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    if user32.IsZoomed(hwnd) or (rect.left <= 0 and rect.top <= 0 and rect.right >= user32.GetSystemMetrics(0) - 15):
        return 0, 0, user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    cr = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(cr))
    tl = POINT(0, 0); user32.ClientToScreen(hwnd, ctypes.byref(tl))
    br = POINT(cr.right, cr.bottom); user32.ClientToScreen(hwnd, ctypes.byref(br))
    return tl.x, tl.y, br.x, br.y


def find_game_window():
    titles = []
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def cb(hwnd, lp):
        if user32.IsWindowVisible(hwnd):
            n = user32.GetWindowTextLengthW(hwnd)
            if n > 0:
                buf = ctypes.create_unicode_buffer(n + 1)
                user32.GetWindowTextW(hwnd, buf, n + 1)
                t = buf.value
                if ("DronesOfWar" in t or "Drones of War" in t or "Unreal" in t) and "Explorer" not in t:
                    titles.append((hwnd, t))
        return True

    user32.EnumWindows(WNDENUMPROC(cb), 0)
    return titles


def main():
    print("[RearShot] Pencere araniyor...")
    wins = find_game_window()
    hwnd = wins[0][0] if wins else user32.GetForegroundWindow()
    if wins:
        print(f"[RearShot] Pencere: '{wins[0][1]}'")

    print(f"[RearShot] F7 bekleniyor (status: {STATUS}) ... (timeout {TIMEOUT_S}s)")
    t0 = time.time()
    data = None
    while time.time() - t0 < TIMEOUT_S:
        if os.path.exists(STATUS):
            try:
                with open(STATUS, "r") as f:
                    c = f.read().strip()
                if c.startswith("{") and c.endswith("}"):
                    d = json.loads(c)
                    if d.get("status") == "READY":
                        data = d
                        break
            except Exception:
                pass
        time.sleep(0.1)

    if not data:
        print("[RearShot] Zaman asimi: F7'ye basilmadi / READY gelmedi.")
        return

    print("[RearShot] READY alindi, kare donduruldu. Yakalaniyor...")
    time.sleep(0.35)  # paused karenin render edilmesini bekle

    user32.SetForegroundWindow(hwnd)
    time.sleep(0.2)
    left, top, right, bottom = get_window_rect(hwnd)
    gw, gh = right - left, bottom - top
    if gw <= 0 or gh <= 0:
        print("[RearShot] Pencere gecersiz/simge durumunda.")
        return
    if gh > 0 and abs((gw / gh) - (16.0 / 9.0)) > 0.02:
        print(f"[UYARI] Pencere 16:9 degil ({gw}x{gh}); resize keypoint hizasini bozabilir!")

    img = ImageGrab.grab(bbox=(left, top, right, bottom))
    try:
        rf = Image.Resampling.LANCZOS
    except AttributeError:
        rf = Image.LANCZOS
    img = img.resize((1920, 1080), rf)
    img.save(os.path.join(OUT_DIR, "rear_shot_raw.png"), "PNG")

    dl, dr = data["drone_location"], data["drone_rotation"]
    cl, cr = data["camera_location"], data["camera_rotation"]
    fov = data.get("camera_fov")

    print("--- KAYITLI POZ ---")
    print(f"  drone_loc = {dl}")
    print(f"  drone_rot = {dr}")
    print(f"  cam_loc   = {cl}")
    print(f"  cam_rot   = {cr}")
    print(f"  cam_fov   = {fov}")
    _dx, _dy, _dz = dl['x']-cl['x'], dl['y']-cl['y'], dl['z']-cl['z']
    _yatay = (_dx*_dx + _dy*_dy) ** 0.5
    print(f"  cam->drone delta = ({_dx:.1f}, {_dy:.1f}, {_dz:.1f})  |yatay|={_yatay:.1f} (beklenen ~500), dikey={_dz:.1f} (beklenen ~0)")

    ann = img.copy()
    drw = ImageDraw.Draw(ann)
    if fov and fov > 0:
        kps = pm.calculate_keypoints_2d(dl, dr, cl, cr, fov)
        pts = {k: (v["x"], v["y"]) for k, v in kps.items() if v["x"] is not None and v["x"] >= 0}
        for a, b in pm.SKELETON_EDGES:
            if a in pts and b in pts:
                drw.line([pts[a], pts[b]], fill=(180, 180, 180), width=2)
        for k, p in pts.items():
            drw.ellipse([p[0]-9, p[1]-9, p[0]+9, p[1]+9], fill=pm.KEYPOINT_COLORS[k], outline=(255, 255, 255), width=2)
        print("--- PROJEKSIYON (piksel) ---")
        for k, v in kps.items():
            print(f"  {k:14s} = ({v['x']:.1f}, {v['y']:.1f})")
    else:
        print("[UYARI] Gecerli FOV yok, keypoint cizilmedi.")

    # ekran merkezi referansi
    drw.line([(960, 0), (960, 1080)], fill=(0, 255, 255), width=1)
    drw.line([(0, 540), (1920, 540)], fill=(0, 255, 255), width=1)
    ann.save(os.path.join(OUT_DIR, "rear_shot_annotated.png"), "PNG")

    print(f"[RearShot] Bitti. Cikti: {OUT_DIR}\\rear_shot_raw.png  &  rear_shot_annotated.png")


if __name__ == "__main__":
    main()

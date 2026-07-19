# -*- coding: utf-8 -*-
# ============================================================================
#  test_tek_kare.py  -  HIZLI GORSEL TEST
# ----------------------------------------------------------------------------
#  Amac: Dataset dongusune / capture_controller'a HIC dokunmadan, tek bir
#  karede keypoint'lerin ucaga oturup oturmadigini gormek.
#
#  NASIL:
#    1) Oyunu ac, Talon'u gorebilecegin bir aciya gel. (Hareketliyse DURAKLAT.)
#    2) Bu scripti calistir:  python test_tek_kare.py
#    3) Script "F7'ye bas" diyene kadar bekle. Oyuna gec, F7'ye bas.
#    4) Script oyun penceresini yakalar, keypoint'leri cizer, TEST_SONUC.png
#       olarak kaydeder ve acar.
#
#  Not: Pencereyi HWND ile yakalar (on planda olmasi sart degil), o yuzden
#  alt-tab yapman sorun degil.
# ============================================================================

import os
import time
import json
import ctypes
from ctypes import wintypes
from PIL import ImageGrab

from draw_keypoints_engine import resolve_points, draw_on_image

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

user32 = ctypes.windll.user32
STATUS = r"c:\Users\Zeylo\Desktop\talon_dataset\status.txt"
OUT = r"c:\Users\Zeylo\Desktop\talon_dataset\TEST_SONUC.png"


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def get_window_rect(hwnd):
    if user32.IsIconic(hwnd):
        return 0, 0, 0, 0
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    if user32.IsZoomed(hwnd) or (rect.left <= 0 and rect.top <= 0 and rect.right >= user32.GetSystemMetrics(0) - 15):
        return 0, 0, user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    client = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(client))
    tl = POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(tl))
    br = POINT(client.right, client.bottom)
    user32.ClientToScreen(hwnd, ctypes.byref(br))
    return tl.x, tl.y, br.x, br.y


def find_game_window():
    found = []
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def cb(hwnd, lp):
        if user32.IsWindowVisible(hwnd):
            ln = user32.GetWindowTextLengthW(hwnd)
            if ln > 0:
                buff = ctypes.create_unicode_buffer(ln + 1)
                user32.GetWindowTextW(hwnd, buff, ln + 1)
                t = buff.value
                if ("DronesOfWar" in t or "Drones of War" in t or "Unreal" in t) and "Explorer" not in t:
                    found.append((hwnd, t))
        return True

    user32.EnumWindows(WNDENUMPROC(cb), 0)
    return found


def main():
    wins = find_game_window()
    if wins:
        hwnd, title = wins[0]
        print(f"[OK] Oyun penceresi: '{title}'")
    else:
        hwnd = user32.GetForegroundWindow()
        print("[UYARI] Pencere otomatik bulunamadi, on plandaki pencere kullanilacak.")

    base_mtime = os.path.getmtime(STATUS) if os.path.exists(STATUS) else 0
    print("\n>>> Simdi OYUNA gec, Talon'u gor, (hareketliyse DURAKLAT) ve F7'ye bas...")
    print("    (Iptal: Ctrl+C)\n")

    while True:
        time.sleep(0.1)
        if not os.path.exists(STATUS):
            continue
        m = os.path.getmtime(STATUS)
        if m <= base_mtime:
            continue
        # taze yazim yakalandi
        try:
            with open(STATUS, "r", encoding="utf-8") as f:
                content = f.read().strip()
        except IOError:
            continue
        if not (content.startswith("{") and '"keypoints_2d"' in content):
            base_mtime = m
            print("[...] status.txt degisti ama keypoint verisi yok, bekleniyor...")
            continue
        try:
            data = json.loads(content)
        except Exception:
            continue

        time.sleep(0.05)
        rect = get_window_rect(hwnd)
        if rect[2] <= rect[0] or rect[3] <= rect[1]:
            print("[HATA] Pencere kucuk/gecersiz. Oyun ekranda mi?")
            base_mtime = m
            continue

        img = ImageGrab.grab(bbox=rect).convert("RGB")
        pts, mode = resolve_points(data, img.width, img.height)
        drawn = draw_on_image(img, pts, dot_radius=6, line_width=2)
        img.save(OUT)

        print(f"\n[BITTI] Kaydedildi: {OUT}")
        print(f"        Yakalanan resim: {img.width}x{img.height}  | viewport: {data.get('viewport')}")
        print(f"        FOV: {data.get('camera_fov')}  | mod: {mode}")
        print(f"        Cizilen keypoint'ler: {list(drawn.keys())}")
        eksik = [k for k in ("nose", "tail", "left_wingtip", "right_wingtip",
                             "left_tail_fin", "right_tail_fin") if k not in drawn]
        if eksik:
            print(f"        (Ekranda olmayan/arkada kalan: {eksik})")
        try:
            os.startfile(OUT)
        except Exception:
            pass
        break


if __name__ == "__main__":
    main()

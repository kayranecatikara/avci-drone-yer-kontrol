# -*- coding: utf-8 -*-
# ============================================================================
# FLIGHT LOGGER - PnP mesafe dogrulama gorevi icin ucus kaydedici
#
# Calisma sekli:
#   - Oyundaki TalonFlightLogger modu saniyede 1 kez flight_status.txt'ye
#     gercek konum/kamera/keypoint verisini yazar.
#   - Bu betik o dosyayi izler; her yeni ornekte oyunun ekran goruntusunu alir
#     ve veriyi kalici kayda gecirir.
#
# Kullanim:
#   1) Oyunu ac (TalonFlightLogger modu yuklu olmali)
#   2) python flight_logger.py   -> kayit baslar
#   3) Talon'u gorerek 3-5 dakika uc (10-40 m arasinda yaklas/uzaklas)
#   4) CTRL+C ile durdur -> ozet yazilir
#
# Cikti: flight_log\ucus_<tarih>\frames\t_XXXX.png + truth_log.jsonl
# ============================================================================
import os
import sys
import json
import time
import math
import ctypes
from ctypes import wintypes

try:
    from PIL import Image
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
    from PIL import Image

try:
    import mss
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "mss"])
    import mss

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

    def cb(hwnd, lParam):
        if user32.IsWindowVisible(hwnd):
            buff_class = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, buff_class, 256)
            if buff_class.value == "UnrealWindow":
                length = user32.GetWindowTextLengthW(hwnd)
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                titles.append((hwnd, buff.value))
        return True

    user32.EnumWindows(WNDENUMPROC(cb), 0)
    return titles


WORKSPACE = r"c:\Users\Zeylo\Desktop\talon_dataset"
SNAP_FILE = os.path.join(WORKSPACE, "flight_status.txt")
POLL_S = 0.01


def main():
    windows = find_game_window()
    if not windows:
        print("[HATA] Oyun penceresi (UnrealWindow) bulunamadi. Once oyunu ac.")
        return
    hwnd = windows[0][0]
    print("[INFO] Oyun penceresi bulundu:", windows[0][1] or "(isimsiz)")

    flight_dir = os.path.join(WORKSPACE, "flight_log", "ucus_" + time.strftime("%Y%m%d_%H%M%S"))
    frames_dir = os.path.join(flight_dir, "frames")
    os.makedirs(frames_dir, exist_ok=True)
    log_path = os.path.join(flight_dir, "truth_log.jsonl")
    print("[INFO] Kayit klasoru:", flight_dir)
    print("[INFO] Ucusa baslayabilirsin. Durdurmak icin CTRL+C.")
    print("-" * 60)

    last_t = None
    n = 0
    t_start = time.time()

    try:
        with mss.mss() as sct, open(log_path, "a", encoding="utf-8") as logf:
            while True:
                time.sleep(POLL_S)
                try:
                    with open(SNAP_FILE, "r", encoding="utf-8") as f:
                        snap = json.load(f)
                except Exception:
                    continue  # dosya yok / yazim ani / bozuk okuma -> sonraki tur

                t = snap.get("t")
                if t is None or t == last_t:
                    continue
                last_t = t

                rect = get_window_rect(hwnd)
                if rect[2] <= rect[0] or rect[3] <= rect[1]:
                    print("[UYARI] Pencere kucultulmus, kare atlandi (t=%s)" % t)
                    continue

                grab_time = time.time()
                monitor = {"top": rect[1], "left": rect[0],
                           "width": rect[2] - rect[0], "height": rect[3] - rect[1]}
                sct_img = sct.grab(monitor)
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                if img.size != (1920, 1080):
                    try:
                        rf = Image.Resampling.LANCZOS
                    except AttributeError:
                        rf = Image.LANCZOS
                    img = img.resize((1920, 1080), rf)

                fname = "t_%04d.png" % t
                img.save(os.path.join(frames_dir, fname), "PNG")

                record = dict(snap)
                record["png"] = "frames/" + fname
                record["py_grab_time"] = round(grab_time, 3)
                record["window"] = list(rect)
                logf.write(json.dumps(record) + "\n")
                logf.flush()
                n += 1

                # Canli geri bildirim: kamera -> talon gercek mesafesi
                try:
                    c = snap["cam_loc"]; tl = snap["talon_loc"]
                    dist_m = math.sqrt((c["x"] - tl["x"]) ** 2 +
                                       (c["y"] - tl["y"]) ** 2 +
                                       (c["z"] - tl["z"]) ** 2) / 100.0
                    # DIKKAT: 'on' bayragi sadece "kamera onunde" demek; kadraj ici
                    # sayilmasi icin koordinat sinir kontrolu de sart.
                    onscr = sum(1 for p in snap.get("kp2d", {}).values()
                                if p.get("on") and 0 <= p["x"] <= 1920 and 0 <= p["y"] <= 1080)
                    uyari = "" if onscr == 6 else "  <- TALON KADRAJDA DEGIL!"
                    print("[KAYIT] t=%-4d mesafe=%6.1f m  kadrajda_kp=%d/6%s" % (t, dist_m, onscr, uyari))
                except Exception:
                    print("[KAYIT] t=%d" % t)
    except KeyboardInterrupt:
        pass

    dur = time.time() - t_start
    print()
    print("=" * 60)
    print("KAYIT BITTI")
    print("  Ornek sayisi : %d" % n)
    print("  Sure         : %.0f saniye" % dur)
    print("  Klasor       : %s" % flight_dir)
    if n < 60:
        print("  [NOT] 60'tan az ornek var - saglikli grafik icin 180+ onerilir.")
    print("Simdi Claude'a bu klasor yolunu soyle; PnP analizini o calistiracak.")


if __name__ == "__main__":
    main()

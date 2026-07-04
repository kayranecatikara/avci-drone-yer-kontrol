# -*- coding: utf-8 -*-
# ==============================================================================
#  ZEYLO SISTEMI - CAPTURE CONTROLLER (kayra uyarlamasi)
# ------------------------------------------------------------------------------
#  Oyun icindeki UE4SS Lua modu (TalonDatasetGenerator) ile status.txt uzerinden
#  el sikisir: Lua sahneyi dondurup kamerayi yerlestirir ve READY+poz JSON'u yazar;
#  bu script ekran goruntusunu alir, TEMIZ PNG + poz JSON'u kaydeder, DONE yazar.
#
#  ORIJINALDEN FARKLAR (kayra duzeltmeleri):
#   1. YOLLAR: c:\Users\Zeylo\... -> C:\talon_pose_data  (Lua'daki yol da boyle)
#   2. TEMIZ EGITIM GORUNTUSU: keypoint noktalari artik dataset PNG'sine CIZILMEZ
#      (egitim verisi kirlenmesin); cizimli kopya ayri 'onizleme\' klasorune gider
#      (ilk 60 kare + her 25. kare).
#   3. 'keyboard' modulu kaldirildi (kullanilmiyordu).
#   4. Cikista status.txt'ye OFFLINE yazilir -> Lua zamani geri acar (oyun donuk kalmaz).
#   5. Pencere client alani 1920x1080 degilse UYARI basilir (resize etiket uyumunu bozabilir).
#
#  Calistirma (repo kokunden):  python pose\capture_controller.py
#  Durdurma: CTRL-C  (oyun donuk kalirsa: script'i tekrar baslatip kapat ya da bekle)
# ==============================================================================
import os
import re
import time
import json
import ctypes
from ctypes import wintypes
import sys

import numpy as np

try:
    from PIL import ImageGrab, Image, ImageDraw
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
    from PIL import ImageGrab, Image, ImageDraw

user32 = ctypes.windll.user32

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# --- AYARLAR ------------------------------------------------------------------
WORKSPACE_DIR = r"C:\talon_pose_data"          # Lua STATUS_FILE_PATH ile AYNI kok!
DATASET_DIR = os.path.join(WORKSPACE_DIR, "dataset")
ONIZLEME_DIR = os.path.join(WORKSPACE_DIR, "onizleme")
STATUS_FILE = os.path.join(WORKSPACE_DIR, "status.txt")
HEDEF_KARE = 4000                               # bu sayiya ulasinca otomatik durur
ONIZLEME_ILK = 60                               # ilk N karenin cizimli kopyasi
ONIZLEME_HER = 25                               # sonrasinda her N karede bir


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def get_window_rect(hwnd):
    if user32.IsIconic(hwnd):
        return 0, 0, 0, 0
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    if user32.IsZoomed(hwnd) or (rect.left <= 0 and rect.top <= 0 and
                                 rect.right >= user32.GetSystemMetrics(0) - 15):
        return 0, 0, user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    client_rect = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(client_rect))
    pt_tl = POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(pt_tl))
    pt_br = POINT(client_rect.right, client_rect.bottom)
    user32.ClientToScreen(hwnd, ctypes.byref(pt_br))
    return pt_tl.x, pt_tl.y, pt_br.x, pt_br.y


def find_game_window():
    titles = []
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def cb(hwnd, lParam):
        if user32.IsWindowVisible(hwnd):
            n = user32.GetWindowTextLengthW(hwnd)
            if n > 0:
                buff = ctypes.create_unicode_buffer(n + 1)
                user32.GetWindowTextW(hwnd, buff, n + 1)
                t = buff.value
                if "DronesOfWar" in t or "Drones of War" in t or "Unreal" in t:
                    titles.append((hwnd, t))
        return True

    user32.EnumWindows(WNDENUMPROC(cb), 0)
    return titles


def _oyun_karesi_mi(img):
    """Kaba kontrol: yakalanan kare OYUN mu (parlak gokyuzu/zemin) yoksa
    EDITOR/masaustu mu (koyu tema)? VS Code/terminal koyu -> ust yari parlakligi
    dusuk. Oyun karesi daima parlak (esik 70; VS Code ~35, oyun >100). Bu, oyun
    ON PLANDA DEGILKEN editorun kaydedilmesini (dataset kirlenmesini) onler."""
    a = np.asarray(img)
    if a.ndim != 3:
        return True
    ust = a[: a.shape[0] // 2]
    return float(ust.mean()) > 70.0


def ciz_onizleme(img, kp2d):
    """Cizimli KOPYA uretir (orijinali degistirmez)."""
    kopya = img.copy()
    d = ImageDraw.Draw(kopya)
    for name, pt in (kp2d or {}).items():
        if pt.get("on", False):
            px, py = pt["x"], pt["y"]
            d.ellipse((px - 2, py - 2, px + 2, py + 2), fill="red", outline="white")  # KAYRA: 4px nokta
    return kopya


# --- KALITE KAPISI ------------------------------------------------------------
#  Kaydetmeden ONCE: 6 keypoint'i poz'dan projekte et, sunlari REDDET:
#   * kadraj disi (hedef ekrandan cikmis)           -> "kadraj-disi"
#   * gokyuzu arka planinda noktalar KOYU SILUETE oturmuyor (hedef yok /
#     poz-goruntu kaymasi)                            -> "gokyuzu-bos"
#  Boylece dataset'e SADECE dogrulanmis kareler girer (yarisi zaten kusursuz;
#  gerisi -ekran disi/hedef yok/zamanlama- otomatik elenir). Zemin arka planinda
#  silueti guvenilir ayirt edemedigimizden orada sadece kadraj kontrolu yapilir.
_KP_FN = None


def _kalite_gecer(img, meta):
    """(gecer_bool, sebep_str) doner. img: PIL (1920x1080), meta: poz sozlugu."""
    global _KP_FN
    if _KP_FN is None:
        try:                                    # paket olarak (python main.py vb.)
            from pose.draw_keypoint import (local_to_world, project_world_to_screen,
                                            KEYPOINTS_LOCAL)
        except ModuleNotFoundError:             # script olarak (python pose\capture_controller.py)
            from draw_keypoint import (local_to_world, project_world_to_screen,
                                       KEYPOINTS_LOCAL)
        _KP_FN = (local_to_world, project_world_to_screen, KEYPOINTS_LOCAL)
    l2w, proj, KPL = _KP_FN
    dl = meta.get("drone_location"); dr = meta.get("drone_rotation")
    cl = meta.get("camera_location"); cr = meta.get("camera_rotation")
    if not (dl and dr and cl and cr):
        return False, "poz-eksik"
    # KAYRA v3: kamera SETTLE etti mi? cam_dpos = POV'un pause'dan onceki son tick'te
    # oynadigi mesafe (cm). >8 ise hala oynuyordu (POV render'la ayrisabilir) -> ELE.
    cdp = meta.get("cam_dpos")
    if cdp is not None and float(cdp) > 8.0:
        return False, "kamera-oynak(dpos=%.0f)" % float(cdp)
    fov = float(meta.get("camera_fov", 125.0))
    W, H = img.size
    pts = []
    for lp in KPL.values():
        p = proj(l2w(lp, dl, dr, (0.0, 0.0, 0.0), 1.0), cl, cr, fov, W, H)
        if p is None:
            return False, "kamera-arkasi"
        pts.append(p)
    m = 0.02
    if not all(W * m <= x <= W * (1 - m) and H * m <= y <= H * (1 - m) for x, y in pts):
        return False, "kadraj-disi"
    a = np.asarray(img)
    cx = sum(x for x, _ in pts) / 6.0
    cy = sum(y for _, y in pts) / 6.0
    R = 200
    x0, y0 = max(0, int(cx - R)), max(0, int(cy - R))
    x1, y1 = min(W, int(cx + R)), min(H, int(cy + R))
    pen = a[y0:y1, x0:x1]
    if pen.size and pen[:, :, :3].mean() > 120:      # parlak = GOKYUZU -> dogrulanabilir
        g = pen[:, :, :3].mean(axis=2)
        koyu = g < (g.mean() - 45)
        ky, kx = int(cy - y0), int(cx - x0)
        rr = 45
        yy0, yy1 = max(0, ky - rr), min(pen.shape[0], ky + rr)
        xx0, xx1 = max(0, kx - rr), min(pen.shape[1], kx + rr)
        if int(koyu[yy0:yy1, xx0:xx1].sum()) < 20:   # centroid cevresinde koyu piksel yok
            return False, "gokyuzu-bos(hedef-yok/kayma)"
    return True, "ok"


def main():
    os.makedirs(DATASET_DIR, exist_ok=True)
    os.makedirs(ONIZLEME_DIR, exist_ok=True)

    print("[INFO] Oyun penceresi araniyor...")
    windows = [w for w in find_game_window()
               if "Explorer" not in w[1] and "Teknofest -" not in w[1]]
    if not windows:
        print("[UYARI] Oyun penceresi otomatik bulunamadi; ONDEKI pencere kullanilacak.")
        hwnd = user32.GetForegroundWindow()
    else:
        hwnd, title = windows[0]
        print(f"[INFO] Pencere bulundu: '{title}' (HWND: {hwnd})")

    console_hwnd = ctypes.windll.kernel32.GetConsoleWindow()
    if console_hwnd:
        print("[INFO] Terminal kucultuluyor (goruntuye girmesin)...")
        user32.ShowWindow(console_hwnd, 6)
        time.sleep(0.5)

    user32.ShowWindow(hwnd, 5)
    user32.SetForegroundWindow(hwnd)
    time.sleep(1.0)

    print("[INFO] Status dosyasi:", STATUS_FILE)
    print("[INFO] Otomatik cekim donugusu basliyor; Lua modu bekleniyor...")
    print("[INFO] Durdurmak icin CTRL-C.")

    with open(STATUS_FILE, "w") as f:
        f.write("WAITING_START")

    # kaldigi yerden devam: dataset'teki en yuksek indeks
    offset = 0
    pattern = re.compile(r"^talon_(\d+)")
    for fn in os.listdir(DATASET_DIR):
        if fn.endswith(".png"):
            m = pattern.match(fn)
            if m:
                offset = max(offset, int(m.group(1)))
    print(f"[INFO] Mevcut en yuksek indeks: {offset} (devam edilecek).")

    last_processed = -1
    boyut_uyarildi = False
    n_kayit = 0                 # KAYDEDILEN (kaliteden gecen) kare
    n_red = 0                   # REDDEDILEN kare
    red_sebep = {}              # red sebebi -> sayi

    try:
        while True:
            if offset >= HEDEF_KARE:
                print(f"\n[INFO] HEDEF {HEDEF_KARE} KAREYE ULASILDI! Otomatik durduruldu.")
                break
            if not os.path.exists(STATUS_FILE):
                time.sleep(0.1)
                continue
            try:
                with open(STATUS_FILE, "r") as f:
                    content = f.read().strip()
            except IOError:
                time.sleep(0.05)
                continue

            if not (content.startswith("{") and content.endswith("}")):
                time.sleep(0.05)
                continue
            try:
                data = json.loads(content)
            except Exception:
                time.sleep(0.05)
                continue

            if data.get("status") == "MANUAL_SHOT":
                print("[MANUAL] F9 manuel cekim isleniyor...")
                time.sleep(0.15)
                rect = get_window_rect(hwnd)
                if rect[2] > rect[0] and rect[3] > rect[1]:
                    img = ImageGrab.grab(bbox=rect)
                    ts = int(time.time())
                    img.save(os.path.join(DATASET_DIR, f"manual_shot_{ts}.png"), "PNG")
                    meta = {
                        "talon_location": data.get("drone_location"),
                        "talon_rotation": data.get("drone_rotation"),
                        "avci_camera_location": data.get("camera_location"),
                        "avci_camera_rotation": data.get("camera_rotation"),
                        "camera_fov": data.get("camera_fov", 125.0),
                        "keypoints_3d": data.get("keypoints_3d"),
                        "keypoints_2d": data.get("keypoints_2d"),
                        "view": "MANUAL_OVERHEAD",
                    }
                    with open(os.path.join(DATASET_DIR, f"manual_shot_{ts}.json"), "w") as jf:
                        json.dump(meta, jf, indent=4)
                    onz = ciz_onizleme(img, meta["keypoints_2d"])
                    onz.save(os.path.join(ONIZLEME_DIR, f"manual_shot_{ts}_marked.png"), "PNG")
                    print(f"[MANUAL] Kaydedildi: manual_shot_{ts} (+onizleme)")
                    with open(STATUS_FILE, "w") as out_f:
                        out_f.write("WAITING_START")

            elif data.get("status") == "READY":
                index = data.get("index", -1)
                if index != last_processed:
                    print(f"[CAPTURE] Kare {index} isleniyor... ", end="", flush=True)
                    time.sleep(0.30)                     # render pause frame'ini cizsin (v3: 0.15->0.30)
                    rect = get_window_rect(hwnd)
                    left, top, right, bottom = rect
                    if right > left and bottom > top:
                        img = ImageGrab.grab(bbox=rect)
                        # OYUN ON PLANDA MI? Degilse (editor/masaustu koyu kare)
                        # KAYDETME + DONE GONDERME -> Lua donuk bekler; oyunu one
                        # getirip ayni kareyi tekrar dene (dataset kirlenmez).
                        if not _oyun_karesi_mi(img):
                            user32.SetForegroundWindow(hwnd)
                            print("\n[BEKLE] oyun on planda degil (koyu kare) -> "
                                  "atlandi. Oyun penceresini one getir; devam edecek.")
                            time.sleep(0.4)
                            continue
                        if img.size != (1920, 1080):
                            if not boyut_uyarildi:
                                boyut_uyarildi = True
                                print(f"\n[UYARI] Pencere {img.size}, 1920x1080 DEGIL! "
                                      f"1920x1080'e olceklenecek; en iyi sonuc icin oyunu "
                                      f"1920x1080 (tam ekran/borderless) calistir.")
                            try:
                                rf = Image.Resampling.LANCZOS
                            except AttributeError:
                                rf = Image.LANCZOS
                            img = img.resize((1920, 1080), rf)

                        kare_no = offset + index
                        png_yol = os.path.join(DATASET_DIR, f"talon_{kare_no:04d}.png")
                        json_yol = os.path.join(DATASET_DIR, f"talon_{kare_no:04d}.json")

                        meta = {
                            "drone_location": data.get("drone_location"),
                            "drone_rotation": data.get("drone_rotation"),
                            "camera_location": data.get("camera_location"),
                            "camera_rotation": data.get("camera_rotation"),
                            "camera_fov": data.get("camera_fov", 125.0),
                            "cam_src": data.get("cam_src"),      # pov/comp/cmd (teshis)
                            "cam_dpos": data.get("cam_dpos"),    # POV vs komut mesafesi (cm) — kamera vardi mi
                            "keypoints_3d": data.get("keypoints_3d"),
                            "keypoints_2d": data.get("keypoints_2d"),
                            "view": data.get("view"),
                        }

                        # KALITE KAPISI: oturmayan/ekran-disi/hedef-yok kareyi KAYDETME.
                        # (DONE gonderilir ki Lua yeni cesitli poz uretsin; dataset temiz kalir.)
                        gecer, sebep = _kalite_gecer(img, meta)
                        if not gecer:
                            n_red += 1
                            red_sebep[sebep] = red_sebep.get(sebep, 0) + 1
                            print(f"RED ({sebep})")
                            last_processed = index
                            with open(STATUS_FILE, "w") as out_f:
                                out_f.write(f"DONE_{index}")
                            continue

                        img.save(png_yol, "PNG")          # TEMIZ egitim goruntusu!
                        with open(json_yol, "w") as jf:
                            json.dump(meta, jf, indent=4)

                        if kare_no <= ONIZLEME_ILK or kare_no % ONIZLEME_HER == 0:
                            onz = ciz_onizleme(img, meta["keypoints_2d"])
                            onz.save(os.path.join(ONIZLEME_DIR,
                                                  f"talon_{kare_no:04d}_marked.png"), "PNG")

                        n_kayit += 1
                        print(f"kaydedildi: talon_{kare_no:04d}  "
                              f"(gecen={n_kayit} red={n_red})")
                        last_processed = index
                        with open(STATUS_FILE, "w") as out_f:
                            out_f.write(f"DONE_{index}")
                    else:
                        print("[HATA] Pencere kucultulmus/gecersiz. Tekrar denenecek...")
                        time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[INFO] CTRL-C — durduruluyor.")
    finally:
        print(f"\n[OZET] kaydedilen(kaliteden gecen)={n_kayit}  reddedilen={n_red}")
        if red_sebep:
            print("[OZET] red sebepleri:", red_sebep)
        # Lua'ya haber ver: zamani geri acsin, oyun donuk kalmasin (KAYRA FIX ile eslesir)
        try:
            with open(STATUS_FILE, "w") as f:
                f.write("OFFLINE")
            print("[INFO] status=OFFLINE yazildi; oyun zamani Lua tarafindan geri acilacak.")
        except Exception:
            pass


if __name__ == "__main__":
    main()

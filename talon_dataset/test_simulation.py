import cv2
import mss
import numpy as np
import ctypes
from ctypes import wintypes
import time
import os

try:
    from ultralytics import YOLO
except ImportError:
    import sys
    import subprocess
    print("Ultralytics yukleniyor...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "ultralytics", "opencv-python"])
    from ultralytics import YOLO

# ==========================================
# AYARLAR
# ==========================================
MODEL_PATH = "best.pt"

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

def find_game_window():
    windows = []
    def enum_cb(hwnd, lParam):
        if user32.IsWindowVisible(hwnd):
            # Class name kontrolu (Unreal Engine oyun pencereleri "UnrealWindow" class'ini kullanir)
            class_name = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, class_name, 256)
            
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                title = buf.value
                
                # Hem UnrealWindow classi olacak hem de title ici bos olmayacak
                if class_name.value == "UnrealWindow" and title.strip():
                    windows.append((hwnd, title))
        return True
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    user32.EnumWindows(EnumWindowsProc(enum_cb), 0)
    return windows

def capture_window_bgra(hwnd):
    # PrintWindow ile arkaplanda kalan (ustu ortulmus) pencereyi cek
    rect = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(rect))
    width = rect.right - rect.left
    height = rect.bottom - rect.top
    
    if width <= 0 or height <= 0:
        return None
        
    hwndDC = user32.GetWindowDC(hwnd)
    mfcDC  = gdi32.CreateCompatibleDC(hwndDC)
    saveBitMap = gdi32.CreateCompatibleBitmap(hwndDC, width, height)
    gdi32.SelectObject(mfcDC, saveBitMap)
    
    # PW_RENDERFULLCONTENT = 2 (Windows 8.1+ donanim hizlandirmali pencereler icin)
    result = user32.PrintWindow(hwnd, mfcDC, 3)
    
    bmpinfo = dict(
        bmiHeader=dict(
            biSize=40,
            biWidth=width,
            biHeight=-height, # top-down
            biPlanes=1,
            biBitCount=32,
            biCompression=0,
            biSizeImage=0,
            biXPelsPerMeter=0,
            biYPelsPerMeter=0,
            biClrUsed=0,
            biClrImportant=0
        )
    )
    
    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [("biSize", ctypes.c_uint32),
                    ("biWidth", ctypes.c_int32),
                    ("biHeight", ctypes.c_int32),
                    ("biPlanes", ctypes.c_uint16),
                    ("biBitCount", ctypes.c_uint16),
                    ("biCompression", ctypes.c_uint32),
                    ("biSizeImage", ctypes.c_uint32),
                    ("biXPelsPerMeter", ctypes.c_int32),
                    ("biYPelsPerMeter", ctypes.c_int32),
                    ("biClrUsed", ctypes.c_uint32),
                    ("biClrImportant", ctypes.c_uint32)]
                    
    bmi = BITMAPINFOHEADER(**bmpinfo["bmiHeader"])
    buffer = ctypes.create_string_buffer(width * height * 4)
    gdi32.GetDIBits(mfcDC, saveBitMap, 0, height, buffer, ctypes.byref(bmi), 0)
    
    img = np.frombuffer(buffer, dtype=np.uint8).reshape((height, width, 4))
    
    gdi32.DeleteObject(saveBitMap)
    gdi32.DeleteDC(mfcDC)
    user32.ReleaseDC(hwnd, hwndDC)
    
    if result == 1:
        return img
    return None

def main():
    if not os.path.exists(MODEL_PATH):
        print(f"[HATA] {MODEL_PATH} bulunamadi! Lutfen best.pt dosyasini bu klasore kopyala.")
        return

    print("[INFO] Model yukleniyor...")
    model = YOLO(MODEL_PATH)
    print("[INFO] Model basariyla yuklendi!")

    windows = find_game_window()
    if not windows:
        print("[HATA] Oyun penceresi bulunamadi! Oyunu acik tuttugundan emin ol.")
        return
    
    hwnd, title = windows[0]
    print(f"[INFO] Oyun penceresi bulundu: {title}")
    print("[INFO] Similasyon testi basliyor. Cikmak icin OpenCV penceresindeyken 'Q' tusuna bas.")

    # 1920x1080 icin ayarla (Senin istedigin gibi buyuk acilacak)
    cv2.namedWindow("Talon Pose Model Test", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Talon Pose Model Test", 1920, 1080)
    
    # FPS hesaplama icin
    prev_time = time.time()

    while True:
        # Arka plandan (veya ustu ortulmusken) oyun penceresini cek
        bgra_img = capture_window_bgra(hwnd)
        
        if bgra_img is None:
            time.sleep(0.1)
            continue
            
        # Resmi BGR formatina cevir
        frame = cv2.cvtColor(bgra_img, cv2.COLOR_BGRA2BGR)

        # Modeli calistir (Ekranda cok ufak gozukmesini engellemek icin imgsz=1080 kullanilabilir)
        # conf=0.5 demek, %50'den emin olmadigi objeleri cizmez
        results = model.predict(source=frame, conf=0.5, show=False, verbose=False)
        
        # Sonuclari ciz
        for result in results:
            # Ultralytics'in kendi cizim fonksiyonu her seyi otomatik cizer
            frame = result.plot()
            
        # FPS Hesabi
        curr_time = time.time()
        fps = 1 / (curr_time - prev_time)
        prev_time = curr_time
        
        cv2.putText(frame, f"FPS: {int(fps)}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame, "Cikis: Q", (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        # Ciktiyi goster
        cv2.imshow("Talon Pose Model Test", frame)

        # Q tusuna basilirsa VEYA pencere X'den kapatilirsa cik
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
            
        try:
            if cv2.getWindowProperty("Talon Pose Model Test", cv2.WND_PROP_VISIBLE) < 1:
                break
        except Exception:
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

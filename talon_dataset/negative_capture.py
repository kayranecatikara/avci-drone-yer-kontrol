import os
import time
import ctypes
from ctypes import wintypes
import mss
from PIL import Image
import keyboard

user32 = ctypes.windll.user32
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

def get_unreal_window():
    hwnd = user32.FindWindowW(None, "DronesOfWar  ")
    if not hwnd:
        hwnd = user32.FindWindowW("UnrealWindow", None)
    return hwnd

def get_window_rect(hwnd):
    if user32.IsIconic(hwnd):
        return 0, 0, 0, 0
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return rect.left, rect.top, rect.right, rect.bottom

def capture_negative_samples():
    out_dir = "negative_samples"
    os.makedirs(out_dir, exist_ok=True)
    
    print("==================================================")
    print("[NEGATIF VERI] Arka plan (hedefsiz) foto cekici basladi!")
    print(f"[BILGI] Cekilen fotolar ve bos TXT'ler '{out_dir}' klasorune kaydedilecek.")
    print("[TUSLAR]: Foto cekmek icin '1' tusuna bas.")
    print("[TUSLAR]: Cikmak icin 'ESC' tusuna bas.")
    print("==================================================")
    
    count = 1
    
    # Eger klasorde onceden neg_XXXX.png varsa, kaldigi numaradan devam etsin
    existing = [f for f in os.listdir(out_dir) if f.startswith("neg_") and f.endswith(".png")]
    if existing:
        nums = [int(f.replace("neg_", "").replace(".png", "")) for f in existing]
        count = max(nums) + 1
        
    hwnd = get_unreal_window()
    if not hwnd:
        print("[UYARI] Oyun penceresi bulunamadi! Tam ekran cekim yapilacak.")
    
    with mss.mss() as sct:
        while True:
            if keyboard.is_pressed('1'):
                if hwnd:
                    left, top, right, bottom = get_window_rect(hwnd)
                    if right > left and bottom > top:
                        monitor = {"top": top, "left": left, "width": right - left, "height": bottom - top}
                    else:
                        monitor = sct.monitors[1] # Pencere kucukse ana ekrani cek
                else:
                    monitor = sct.monitors[1]
                    
                sct_img = sct.grab(monitor)
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                
                # Dosya isimleri
                base_name = f"neg_{count:04d}"
                png_path = os.path.join(out_dir, f"{base_name}.png")
                txt_path = os.path.join(out_dir, f"{base_name}.txt")
                
                # 1. PNG'yi kaydet
                img.save(png_path, "PNG")
                
                # 2. BOS TXT'yi kaydet (Hedefsiz oldugunu ogretmek icin bos birakilir)
                open(txt_path, 'w').close()
                
                print(f"[BASARILI] {base_name}.png ve bos {base_name}.txt kaydedildi!")
                count += 1
                
                # Yanlislikla basili tutarsa ust uste yuzlerce cekmesin diye bekle
                time.sleep(0.3)
                
            elif keyboard.is_pressed('esc'):
                print("\n[CIKIS] Negatif veri cekme islemi sonlandirildi.")
                break
                
            time.sleep(0.01)

if __name__ == "__main__":
    capture_negative_samples()

import sys
import os
import time
import keyboard
import ctypes
from ctypes import wintypes
import mss
from PIL import Image

# Oyun motoru baglantisi icin SDK'nin yolunu tanitiyoruz
sys.path.append(r"C:\Users\Zeylo\Desktop\avci-drone-yer-kontrol\sdk")
try:
    import drone_sdk as sdk
except ImportError:
    print("[HATA] SDK bulunamadi. Yol guncellemelerini kontrol et.")

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

def main():
    print("==================================================")
    print("🚀 MANUEL UCUS + NEGATIF (BOS) FOTOGRAF CEKIMI 🚀")
    print("==================================================")
    
    out_dir = "negative_samples"
    os.makedirs(out_dir, exist_ok=True)
    
    count = 1
    existing = [f for f in os.listdir(out_dir) if f.startswith("neg_") and f.endswith(".png")]
    if existing:
        nums = [int(f.replace("neg_", "").replace(".png", "")) for f in existing]
        count = max(nums) + 1

    print("[BAGLANTI] Oyun motoruna (Unreal) baglaniliyor...")
    try:
        sdk.connect('127.0.0.1', 12345)
        time.sleep(0.5)
    except Exception as e:
        print("[UYARI] SDK baglantisi hatali, oyun acik degil mi?", e)
    
    if sdk.is_connected():
        print("[BASARILI] Baglanti saglandi, motorlar aktif!")
        sdk.set_arm(True)
    else:
        print("[HATA] Baglanilamadi! Sadece foto cekimi aktif.")

    print("\n--- KONTROL TUSLARI ---")
    print("W : YUKARI (Tirmanma)")
    print("S : ASAGI / PERVANE KES")
    print("A : SOLA DON")
    print("D : SAGA DON")
    print("R : ILERI GİT")
    print("U : GERI GİT")
    print("F : KESIN SABITLENME (Havada civi gibi durur)")
    print("1 : FOTOGRAF CEK (Oyun donmaz, PNG + BOS TXT atar)")
    print("ESC : Cikis yap")
    print("-------------------------\n")

    hwnd = get_unreal_window()
    if not hwnd: print("[UYARI] Oyun penceresi bulunamadi! Tam ekran cekim yapilacak.")

    last_capture_time = 0

    with mss.mss() as sct:
        try:
            while True:
                if keyboard.is_pressed('esc'):
                    print("[SISTEM] Kapatiliyor...")
                    break

                # 1. DRONE KONTROLU (LAGSIZ / DONMASIZ)
                throttle, pitch, roll, yaw = 0.0, 0.0, 0.0, 0.0

                if keyboard.is_pressed('f'):
                    # F tusuna basinca her seyi sifirla ve drona durmasini soyle
                    throttle = 0.0
                    pitch = 0.0
                    roll = 0.0
                    yaw = 0.0
                else:
                    if keyboard.is_pressed('w'): throttle = 1.0  # Yukari
                    if keyboard.is_pressed('s'): throttle = -1.0 # Asagi
                    if keyboard.is_pressed('a'): yaw = -1.0      # Sola Don
                    if keyboard.is_pressed('d'): yaw = 1.0       # Saga Don
                    if keyboard.is_pressed('r'): pitch = 1.0     # Ileri
                    if keyboard.is_pressed('u'): pitch = -1.0    # Geri

                if sdk.is_connected():
                    sdk.set_control_surfaces(throttle, pitch, roll, yaw, True)

                # ----------------------------------------------------
                # 2. ANINDA FOTOGRAF CEKIMI (OYUNU ASLA DONDURMAZ)
                # ----------------------------------------------------
                if keyboard.is_pressed('1'):
                    current_time = time.time()
                    # Ayni tusa yanlislikla cok basarsan diye 0.3 saniye bekleme suresi (debounce)
                    if current_time - last_capture_time > 0.3:
                        last_capture_time = current_time
                        
                        if hwnd:
                            left, top, right, bottom = get_window_rect(hwnd)
                            if right > left and bottom > top:
                                monitor = {"top": top, "left": left, "width": right - left, "height": bottom - top}
                            else:
                                monitor = sct.monitors[1]
                        else:
                            monitor = sct.monitors[1]

                        sct_img = sct.grab(monitor)
                        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                        
                        # Resize istersen: img = img.resize((1920, 1080), Image.Resampling.LANCZOS)
                        
                        base_name = f"neg_{count:04d}"
                        png_path = os.path.join(out_dir, f"{base_name}.png")
                        txt_path = os.path.join(out_dir, f"{base_name}.txt")
                        
                        img.save(png_path, "PNG")
                        open(txt_path, 'w').close()
                        
                        print(f"📸 [CEKILDI] {base_name}.png ve bos {base_name}.txt")
                        count += 1

                time.sleep(0.01)

        except KeyboardInterrupt:
            pass
        finally:
            if sdk.is_connected():
                sdk.set_control_surfaces(0.0, 0.0, 0.0, 0.0, True)
                sdk.disconnect()

if __name__ == "__main__":
    main()

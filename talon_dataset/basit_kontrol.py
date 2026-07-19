import sys
import os
import time
import keyboard

# Oyun motoru baglantisi icin SDK'nin yolunu tanitiyoruz
sys.path.append(r"C:\Users\Zeylo\Desktop\avci-drone-yer-kontrol\sdk")
import drone_sdk as sdk

def main():
    print("==================================================")
    print("🚁 BASIT VE NET DRONE KONTROLU 🚁")
    print("==================================================")
    print("[BAGLANTI] Oyun motoruna baglaniliyor...")
    
    sdk.connect('127.0.0.1', 12345)
    time.sleep(0.5)
    
    if not sdk.is_connected():
        print("[HATA] Baglanti kurulamadi! Oyunun acik olduguna emin ol.")
        return
        
    print("[BASARILI] Baglanti saglandi, motorlar aktif!")
    print("\n--- KONTROL TUSLARI ---")
    print("W : YUKARI (Tirmanma / Tam Gaz)")
    print("S : ASAGI / PERVANE KES (Motorlari kesip alcalma)")
    print("A : SOLA DOGRU (Sola yat)")
    print("D : SAGA DOGRU (Saga yat)")
    print("F : KESIN SABITLENME (Havada oldugu yerde ZINK diye durur)")
    print("ESC : Cikis yap")
    print("-------------------------\n")

    sdk.set_arm(True)

    try:
        while True:
            if keyboard.is_pressed('esc'):
                print("[SISTEM] Kapatiliyor...")
                break

            # Gecerli anlik komutlar (varsayilan olarak hicbir seye basmiyorsan süzülür)
            throttle = 0.0
            pitch = 0.0
            roll = 0.0
            yaw = 0.0

            # --- F TUSU (KESIN SABITLENME) ---
            if keyboard.is_pressed('f'):
                # F'ye basinca her sey 0 olur, drone havada mevcut irtifada miknatis gibi sabitlenir (Hover)
                throttle = 0.0
                pitch = 0.0
                roll = 0.0
                yaw = 0.0
            else:
                # --- W, A, S, D KONTROLLERI ---
                if keyboard.is_pressed('w'):
                    throttle = 1.0  # Yukari (Tam Gaz Tirmanma)
                    
                if keyboard.is_pressed('s'):
                    throttle = -1.0 # Asagi (Pervaneleri komple kes ve aninda alcal)
                    
                if keyboard.is_pressed('a'):
                    roll = -1.0     # Sola Dogru
                    
                if keyboard.is_pressed('d'):
                    roll = 1.0      # Saga Dogru

            # Oyun motoruna 0 gecikme ile tek paket yolluyoruz
            sdk.set_control_surfaces(throttle, pitch, roll, yaw, True)
            time.sleep(0.01) # FPS uyumu icin minik bekleme

    except KeyboardInterrupt:
        pass
    finally:
        sdk.set_control_surfaces(0.0, 0.0, 0.0, 0.0, True)
        sdk.disconnect()

if __name__ == "__main__":
    main()

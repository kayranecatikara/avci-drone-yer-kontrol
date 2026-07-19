import keyboard
import json
import time
import os

cmd_file = "C:/Users/Zeylo/Desktop/talon_dataset/manual_cmd.json"

print("--- GERCEKCI KLAVYE DRONE KONTROLCUSU ---")
print("SOL STICK (Motor ve Donus):")
print("  W: Gaz Ver (YUKARI cikar)")
print("  S: Motoru Kes (Hizi sifirla / Asagi duser)")
print("  A: Kendi ekseninde Sola don (Yaw Left)")
print("  D: Kendi ekseninde Saga don (Yaw Right)")
print("\nSAG STICK (Yonlendirme):")
print("  YUKARI OK: Ileri Git (Pitch Down)")
print("  ASAGI OK: Geri Git (Pitch Up)")
print("  SOL OK: Sola Yatarak Git (Roll Left)")
print("  SAG OK: Saga Yatarak Git (Roll Right)")
print("\nSISTEM:")
print("  F: Hover (Irtifayi korur)")
print("  E: Kumandayi Eline Al (Sistemi Baslat)")
print("  1: FOTOGRAF CEK! (JSON + PNG)")
print("Cikis icin ESC'ye basin.\n")

capture_triggered = False

while True:
    if keyboard.is_pressed('esc'):
        print("Cikiliyor...")
        break
        
    cmd = {
        "E": keyboard.is_pressed('e'),  # Sistemi Baslat
        "W": keyboard.is_pressed('w'),
        "S": keyboard.is_pressed('s'),
        "A": keyboard.is_pressed('a'),
        "D": keyboard.is_pressed('d'),
        "UP": keyboard.is_pressed('up'),
        "DOWN": keyboard.is_pressed('down'),
        "LEFT": keyboard.is_pressed('left'),
        "RIGHT": keyboard.is_pressed('right'),
        "F": keyboard.is_pressed('f'),
        "capture": False
    }
    
    if keyboard.is_pressed('1'):
        if not capture_triggered:
            cmd["capture"] = True
            capture_triggered = True
            print("📸 DEKLANSOR PATLADI! [Oyun icinde fotoğraf çekiliyor]")
    else:
        capture_triggered = False
        
    try:
        with open(cmd_file, "w") as f:
            json.dump(cmd, f)
    except:
        pass
        
    time.sleep(0.016) # ~60 FPS guncelleme hizi

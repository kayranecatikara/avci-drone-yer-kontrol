import pygame
import time
import sys

pygame.init()
pygame.joystick.init()

if pygame.joystick.get_count() == 0:
    print("[ERROR] PS4 Kolu bulunamadi! Lutfen kolu PC'ye baglayin ve bu ekrani yeniden baslatin.")
    sys.exit(1)

joystick = pygame.joystick.Joystick(0)
joystick.init()
print(f"[INFO] Baglandi: {joystick.get_name()}")
print("[INFO] Gercek zamanli ucus verileri gonderiliyor...")

def get_axis(idx):
    try:
        val = joystick.get_axis(idx)
        # Olu bolge (Deadzone) ayari (Kollardaki hafif kaymalari onler)
        if abs(val) < 0.15:
            return 0.0
        return val
    except:
        return 0.0

# MODE 2 DRONE KONTROLLERI
# Sol Stick Y (Eksen 1) -> Throttle (Gaz)
# Sol Stick X (Eksen 0) -> Yaw (Kendi etrafinda donme)
# Sag Stick Y (Eksen 3) -> Pitch (Ileri-Geri)
# Sag Stick X (Eksen 2) -> Roll (Saga-Sola yatma)

flight_file = r"c:\Users\Zeylo\Desktop\talon_dataset\flight.txt"

while True:
    pygame.event.pump()
    
    throttle = -get_axis(1) # Ileri itince pozitif gaz versin
    yaw = get_axis(0)       # Saga itince pozitif dondursun
    pitch = -get_axis(3)    # Ileri itince burnunu egsin (Pozitif)
    roll = get_axis(2)      # Saga itince saga yatsin (Pozitif)
    
    # PS4 Ucgen (Triangle) veya Options tusuna basilirsa "Bana Devret" komutunu yolla!
    # Pygame'de tus indeksleri degisebilir, bu yuzden 3 (Ucgen) veya 6 (Options) deniyoruz
    try:
        if joystick.get_button(3) or joystick.get_button(6):
            with open(r"c:\Users\Zeylo\Desktop\talon_dataset\cmd.txt", "w") as cf:
                cf.write("START_JAILBREAK")
            print("[INFO] KONTROL ALINDI! SEN UCURUYORSUN!")
            time.sleep(1) # Cift basilmasini engelle
    except:
        pass
        
    try:
        with open(flight_file, "w") as f:
            f.write(f"T:{throttle} Y:{yaw} P:{pitch} R:{roll}")
    except:
        pass
        
    time.sleep(0.01) # Saniyede 100 kere guncelle (Daha akici)

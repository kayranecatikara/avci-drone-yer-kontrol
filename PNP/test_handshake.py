"""
Hile 1 El Sıkışma Testi — status.txt'i gerçek zamanlı izler.
Terminal minimize OLMAZ. Ne olduğunu görmek için kullan.
"""
import time
import os

STATUS_FILE = r"c:\Users\Zeylo\Desktop\talon_dataset\status.txt"

# status.txt'e WAITING_START yaz
with open(STATUS_FILE, "w") as f:
    f.write("WAITING_START")

print("=" * 50)
print("EL SIKISMAN TESTI BASLADI")
print("=" * 50)
print(f"status.txt -> WAITING_START yazildi")
print(f"Simdi oyun icinde Talon gorunuyor olmali.")
print(f"Lua modu READY sinyali gonderince burada gorunur.")
print(f"Cikmak icin CTRL+C bas.")
print("=" * 50)

prev = None
start = time.time()
while True:
    try:
        if os.path.exists(STATUS_FILE):
            with open(STATUS_FILE, "r") as f:
                content = f.read().strip()
            if content != prev:
                elapsed = time.time() - start
                print(f"[{elapsed:6.1f}s] status.txt = {content[:120]}")
                prev = content
        else:
            print("[HATA] status.txt bulunamadi!")
        time.sleep(0.2)
    except KeyboardInterrupt:
        print("\nTest durduruldu.")
        break

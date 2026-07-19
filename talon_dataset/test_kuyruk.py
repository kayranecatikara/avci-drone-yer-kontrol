import cv2
import json
import glob
import os

print("--- Kuyruk Testi ---")
# Dataset klasorleri icindeki tum jsonlari bul
json_files = glob.glob("dataset*/**/*.json", recursive=True)
if not json_files:
    print("Test edilecek JSON bulunamadi.")
    exit()

# En son cekilen (veya duzeltilen) ilk fotografi al
j_file = json_files[-1]
img_file = j_file.replace(".json", ".png")

if os.path.exists(img_file):
    with open(j_file, "r") as f:
        data = json.load(f)
        
    img = cv2.imread(img_file)
    for name, kp in data.get("keypoints_2d", {}).items():
        # Ekranda gorunuyorsa (veya 'on' parametresi yoksa) ciz
        if kp.get("on", True):
            x, y = int(kp["x"]), int(kp["y"])
            # Kirmizi Nokta
            cv2.circle(img, (x, y), 8, (0, 0, 255), -1) 
            # Sari Isim Yazisi
            cv2.putText(img, name, (x + 10, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            
    out_name = "TEST_KUYRUK_SONUC.png"
    cv2.imwrite(out_name, img)
    print(f"\n[{j_file}] dosyasi okundu ve cizildi.")
    print(f"Test resmi basariyla kaydedildi: {out_name}")
    print("Klasore gidip resme tiklayarak sag ve sol kuyrugun isimlerine bakabilirsin!")
else:
    print(f"{img_file} bulunamadi.")

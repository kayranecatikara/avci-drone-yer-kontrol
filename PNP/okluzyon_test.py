import cv2
import json
import glob
import os

def test_okluzyon():
    # Klasordeki tum JSON'lari bul
    json_files = glob.glob("*.json")
    
    if not json_files:
        print("HATA: Klasorde hic JSON dosyasi bulunamadi!")
        return
        
    for json_file in json_files:
        img_file = json_file.replace(".json", ".png")
        
        if not os.path.exists(img_file):
            continue
            
        # Resmi ve (temizlenmis) JSON'u oku
        img = cv2.imread(img_file)
        with open(json_file, 'r') as f:
            data = json.load(f)
            
        keypoints = data.get("keypoints_2d", {})
        
        # Resmin uzerine guncel noktalari ciz
        for kp_name, kp_data in keypoints.items():
            if kp_data.get("on", False):
                x, y = int(kp_data["x"]), int(kp_data["y"])
                
                # Noktayi ciz (Kirmizi)
                cv2.circle(img, (x, y), 6, (0, 0, 255), -1)
                
                # Hangi nokta oldugunu ustune yaz (Ufak, sari renkle)
                cv2.putText(img, kp_name, (x + 10, y - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
                            
        # Resmi goster
        print(f"Gosteriliyor: {img_file}. Ilerlemek icin bir tusa bas. Kapatmak icin 'q' ya bas.")
        cv2.imshow("Okluzyon (Gorunmezlik) Testi", img)
        
        key = cv2.waitKey(0)
        # Eger 'q' tusuna basarsa testten cik
        if key == ord('q'):
            break
            
    cv2.destroyAllWindows()

if __name__ == "__main__":
    test_okluzyon()
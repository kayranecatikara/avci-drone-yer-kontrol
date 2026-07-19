import glob
import json
import os

print("--- Kuyruk Yuzgecleri (V-Tail) Duzeltici ---")
# Dataset klasorleri icindeki tum json ve txt dosyalarini bul
json_files = glob.glob("dataset*/**/*.json", recursive=True)
txt_files = glob.glob("dataset*/**/*.txt", recursive=True)

fixed_jsons = 0
fixed_txts = 0

for jf in json_files:
    try:
        with open(jf, "r") as f:
            data = json.load(f)
        
        changed = False
        
        # Swap 2D
        if "keypoints_2d" in data:
            left_2d = data["keypoints_2d"].get("Left_Tail_Fin")
            right_2d = data["keypoints_2d"].get("Right_Tail_Fin")
            if left_2d and right_2d:
                data["keypoints_2d"]["Left_Tail_Fin"] = right_2d
                data["keypoints_2d"]["Right_Tail_Fin"] = left_2d
                changed = True
            elif left_2d:
                # Eger sadece biri varsa adini degistir
                data["keypoints_2d"]["Right_Tail_Fin"] = left_2d
                del data["keypoints_2d"]["Left_Tail_Fin"]
                changed = True
            elif right_2d:
                data["keypoints_2d"]["Left_Tail_Fin"] = right_2d
                del data["keypoints_2d"]["Right_Tail_Fin"]
                changed = True

        # Swap 3D
        if "keypoints_3d" in data:
            left_3d = data["keypoints_3d"].get("Left_Tail_Fin")
            right_3d = data["keypoints_3d"].get("Right_Tail_Fin")
            if left_3d and right_3d:
                data["keypoints_3d"]["Left_Tail_Fin"] = right_3d
                data["keypoints_3d"]["Right_Tail_Fin"] = left_3d
                changed = True
            elif left_3d:
                data["keypoints_3d"]["Right_Tail_Fin"] = left_3d
                del data["keypoints_3d"]["Left_Tail_Fin"]
                changed = True
            elif right_3d:
                data["keypoints_3d"]["Left_Tail_Fin"] = right_3d
                del data["keypoints_3d"]["Right_Tail_Fin"]
                changed = True
                
        if changed:
            with open(jf, "w") as f:
                json.dump(data, f, indent=4)
            fixed_jsons += 1
            
    except Exception as e:
        print(f"Hata JSON {jf}: {e}")

# Fix YOLO TXT files
for tf in txt_files:
    try:
        with open(tf, "r") as f:
            lines = f.readlines()
            
        new_lines = []
        changed = False
        for line in lines:
            parts = line.strip().split()
            # YOLO formati: 0:class, 1-4:box, 5-7:nose, 8-10:left_wing, 11-13:right_wing, 14-16:tail, 17-19:left_tail_fin, 20-22:right_tail_fin
            if len(parts) >= 23:
                # Swap 17,18,19 with 20,21,22
                left_x, left_y, left_v = parts[17], parts[18], parts[19]
                right_x, right_y, right_v = parts[20], parts[21], parts[22]
                
                parts[17], parts[18], parts[19] = right_x, right_y, right_v
                parts[20], parts[21], parts[22] = left_x, left_y, left_v
                
                new_lines.append(" ".join(parts) + "\n")
                changed = True
            else:
                new_lines.append(line)
                
        if changed:
            with open(tf, "w") as f:
                f.writelines(new_lines)
            fixed_txts += 1
            
    except Exception as e:
        print(f"Hata TXT {tf}: {e}")

print(f"Islem tamamlandi! {fixed_jsons} JSON dosyasi ve {fixed_txts} TXT dosyasi basariyla duzeltildi.")

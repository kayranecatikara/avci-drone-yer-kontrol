import os
import glob
import re

def rename_dataset(directory, start_index=3700):
    print(f"[INFO] Scanning directory: {directory}")
    
    # 1. Tum PNG ve JSON'lari bul
    png_files = glob.glob(os.path.join(directory, "talon_*.png"))
    
    # Rakamlari cikarip siralayacagiz
    def extract_num(filepath):
        basename = os.path.basename(filepath)
        match = re.search(r'talon_(\d+)\.', basename)
        return int(match.group(1)) if match else -1

    # Rakamlara gore sirala
    png_files.sort(key=extract_num)
    
    valid_pairs = []
    
    # Eslenen ciftleri kontrol et
    for png_path in png_files:
        num = extract_num(png_path)
        if num == -1:
            continue
            
        json_path = png_path.replace(".png", ".json")
        if os.path.exists(json_path):
            valid_pairs.append((png_path, json_path, num))
        else:
            print(f"[WARNING] Esi yok, JSON eksik atliyorum: {os.path.basename(png_path)}")
            
    total_pairs = len(valid_pairs)
    print(f"[INFO] {total_pairs} adet kusursuz cift bulundu. Yeniden isimlendirme basliyor...")
    
    if total_pairs == 0:
        print("[INFO] Islem yapilacak dosya bulunamadi.")
        return

    # Cakismalari (overwrite) onlemek icin once gecici bir isme tasiyoruz
    temp_pairs = []
    for idx, (png_path, json_path, orig_num) in enumerate(valid_pairs):
        temp_png = png_path.replace(".png", "_TEMP.png")
        temp_json = json_path.replace(".json", "_TEMP.json")
        
        os.rename(png_path, temp_png)
        os.rename(json_path, temp_json)
        
        temp_pairs.append((temp_png, temp_json))
        
    # Simdi gercek isimlerine (3700'den baslayarak) kavusturuyoruz
    current_index = start_index
    for temp_png, temp_json in temp_pairs:
        new_basename = f"talon_{current_index:04d}"
        
        new_png = os.path.join(directory, f"{new_basename}.png")
        new_json = os.path.join(directory, f"{new_basename}.json")
        
        os.rename(temp_png, new_png)
        os.rename(temp_json, new_json)
        
        current_index += 1
        
    print(f"[SUCCESS] {total_pairs} cift basariyla 3700 - {current_index-1} arasinda yeniden isimlendirildi!")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    dataset_dir = os.path.join(current_dir, "dataset") # Veya baska klasorse degistir
    
    # Kullanicidan yol iste, bos gecilirse varsayilani kullan
    user_input = input(f"Dataset klasoru ({dataset_dir}) [Kabul etmek icin Enter'a bas]: ").strip()
    if user_input:
        dataset_dir = user_input
        
    if os.path.exists(dataset_dir):
        rename_dataset(dataset_dir, start_index=3700)
    else:
        print(f"[ERROR] Klasor bulunamadi: {dataset_dir}")

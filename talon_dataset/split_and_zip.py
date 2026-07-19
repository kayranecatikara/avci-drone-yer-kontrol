import os
import glob
import re
import shutil
import zipfile

def split_and_zip(directory, chunk_size=200, start_folder_idx=8):
    print(f"[INFO] Scanning directory: {directory}")
    
    png_files = glob.glob(os.path.join(directory, "talon_*.png"))
    
    def extract_num(filepath):
        basename = os.path.basename(filepath)
        match = re.search(r'talon_(\d+)\.', basename)
        return int(match.group(1)) if match else -1

    png_files.sort(key=extract_num)
    
    valid_pairs = []
    for png_path in png_files:
        json_path = png_path.replace(".png", ".json")
        if os.path.exists(json_path):
            valid_pairs.append((png_path, json_path))
            
    total_pairs = len(valid_pairs)
    print(f"[INFO] Found {total_pairs} valid PNG+JSON pairs.")
    
    if total_pairs == 0:
        print("[WARNING] Islem yapilacak cift bulunamadi.")
        return

    folder_idx = start_folder_idx
    for i in range(0, total_pairs, chunk_size):
        chunk = valid_pairs[i:i+chunk_size]
        folder_name = str(folder_idx)
        folder_path = os.path.join(directory, folder_name)
        
        # Klasoru olustur
        os.makedirs(folder_path, exist_ok=True)
        
        print(f"[INFO] {len(chunk)} cift '{folder_name}' klasorune tasiniyor...")
        for png_path, json_path in chunk:
            shutil.move(png_path, os.path.join(folder_path, os.path.basename(png_path)))
            shutil.move(json_path, os.path.join(folder_path, os.path.basename(json_path)))
            
        # Klasoru Zip yap
        zip_path = os.path.join(directory, f"{folder_name}.zip")
        print(f"[INFO] Zipleniyor: {zip_path}")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    # Zip icerisinde klasor yapisini korumak icin arcname kullaniyoruz
                    zipf.write(file_path, arcname=os.path.join(folder_name, file))
                    
        folder_idx += 1
        
    print(f"[SUCCESS] Islem tamamlandi! {start_folder_idx} - {folder_idx-1} arasindaki klasorler ve zıpler olusturuldu.")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    dataset_dir = os.path.join(current_dir, "dataset") # Veya baska klasorse degistir
    
    user_input = input(f"Dataset klasoru ({dataset_dir}) [Kabul etmek icin Enter'a bas]: ").strip()
    if user_input:
        dataset_dir = user_input
        
    if os.path.exists(dataset_dir):
        split_and_zip(dataset_dir, chunk_size=200, start_folder_idx=8)
    else:
        print(f"[ERROR] Klasor bulunamadi: {dataset_dir}")

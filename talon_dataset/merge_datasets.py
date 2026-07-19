import os
import shutil
import glob

def merge_datasets():
    folders = [
        r"C:\Users\Zeylo\Desktop\MORO",
        r"C:\Users\Zeylo\Desktop\MESSİ",
        r"C:\Users\Zeylo\Desktop\sero",
        r"C:\Users\Zeylo\Desktop\Ekstra foto",
        r"C:\Users\Zeylo\Desktop\oro",
        r"C:\Users\Zeylo\Desktop\temz 22",
        r"C:\Users\Zeylo\Desktop\temiz"
    ]
    
    finish_dir = r"C:\Users\Zeylo\Desktop\FİNİSH"
    resimler_dir = os.path.join(finish_dir, "resimler")
    jsonlar_dir = os.path.join(finish_dir, "jsonlar")
    
    os.makedirs(resimler_dir, exist_ok=True)
    os.makedirs(jsonlar_dir, exist_ok=True)
    
    global_index = 0
    total_copied = 0
    
    for folder in folders:
        if not os.path.isdir(folder):
            print(f"[UYARI] Klasör bulunamadı, atlanıyor: {folder}")
            continue
            
        print(f"\n[BİLGİ] Taranıyor: {folder}")
        png_files = glob.glob(os.path.join(folder, "*.png"))
        
        folder_copied = 0
        for png_path in png_files:
            base_name = os.path.splitext(os.path.basename(png_path))[0]
            json_path = os.path.join(folder, base_name + ".json")
            
            if os.path.exists(json_path):
                new_base_name = f"talon_{global_index:05d}"
                
                new_png_path = os.path.join(resimler_dir, new_base_name + ".png")
                new_json_path = os.path.join(jsonlar_dir, new_base_name + ".json")
                
                shutil.copy2(png_path, new_png_path)
                shutil.copy2(json_path, new_json_path)
                
                global_index += 1
                folder_copied += 1
                total_copied += 1
            else:
                print(f"  [ATLANDI] JSON bulunamadı: {png_path}")
                
        print(f"  -> {folder_copied} çift (resim+json) kopyalandı.")
        
    print(f"\n[BAŞARILI] İşlem tamamlandı!")
    print(f"Toplam kopyalanan çift (resim+json) sayısı: {total_copied}")
    print(f"Hedef Klasör: {finish_dir}")

if __name__ == '__main__':
    merge_datasets()

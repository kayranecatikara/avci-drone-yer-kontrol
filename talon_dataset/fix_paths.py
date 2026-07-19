import os
import glob

# Hedef klasorler: eger Masaüstünde kaldiysa orasi, C'ye tasindiysa orasi
dirs_to_check = [
    r"C:\Users\kayra\OneDrive\Masaüstü\talon_dataset",
    r"C:\talon_dataset"
]

for base_dir in dirs_to_check:
    if not os.path.exists(base_dir):
        continue
    
    # Butun python dosyalarini bul (.py)
    py_files = glob.glob(os.path.join(base_dir, "**", "*.py"), recursive=True)
    
    count = 0
    for file_path in py_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Eski yollari yeni yolla degistir
            new_content = content.replace(r"c:\Users\Zeylo\Desktop\talon_dataset", r"C:\talon_dataset")
            new_content = new_content.replace(r"C:\Users\Zeylo\Desktop\talon_dataset", r"C:\talon_dataset")
            new_content = new_content.replace(r"C:\Users\kayra\OneDrive\Masaüstü\talon_dataset", r"C:\talon_dataset")
            new_content = new_content.replace(r"c:\Users\kayra\OneDrive\Masaüstü\talon_dataset", r"C:\talon_dataset")
            
            if new_content != content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                count += 1
                print(f"Fixed paths in: {file_path}")
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    print(f"Updated {count} files in {base_dir}")

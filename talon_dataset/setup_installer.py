import os
import shutil
import sys

def find_ue4ss_directory():
    # Common locations to check
    search_paths = [
        r"C:\Program Files (x86)\Steam\steamapps\common\DronesOfWar",
        r"D:\SteamLibrary\steamapps\common\DronesOfWar",
        r"E:\SteamLibrary\steamapps\common\DronesOfWar",
    ]
    
    for path in search_paths:
        bin_win64 = os.path.join(path, "DronesOfWar", "Binaries", "Win64")
        if os.path.exists(os.path.join(bin_win64, "UE4SS.dll")):
            return bin_win64
            
    # If not found automatically, ask the user or look in the current drive
    print("[INFO] UE4SS installation directory not found automatically in Steam libraries.")
    print("Please paste the absolute path to your game's 'Win64' directory where UE4SS is installed:")
    print("Example: C:\\Games\\DronesOfWar\\DronesOfWar\\Binaries\\Win64")
    
    user_path = input("Path: ").strip().strip('"')
    if os.path.exists(user_path):
        # If they pointed to the root game directory, resolve the Win64 folder
        test_win64 = os.path.join(user_path, "DronesOfWar", "Binaries", "Win64")
        if os.path.exists(test_win64):
            return test_win64
        return user_path
        
    return None

def main():
    workspace_dir = r"c:\Users\Zeylo\Desktop\talon_dataset"
    src_lua = os.path.join(workspace_dir, "main.lua")
    
    if not os.path.exists(src_lua):
        print(f"[ERROR] Source main.lua not found in workspace: {src_lua}")
        return
        
    print("=== Talon UAV Dataset Mod Installer ===")
    win64_dir = find_ue4ss_directory()
    
    if not win64_dir:
        print("[ERROR] Could not locate valid UE4SS directory. Aborting installation.")
        print("[INFO] You can still manually install the mod by following the readme instructions.")
        return
        
    print(f"[SUCCESS] Located UE4SS directory: {win64_dir}")
    
    # Define destination paths
    mods_dir = os.path.join(win64_dir, "Mods")
    target_mod_dir = os.path.join(mods_dir, "TalonDatasetGenerator")
    target_scripts_dir = os.path.join(target_mod_dir, "Scripts")
    dest_lua = os.path.join(target_scripts_dir, "main.lua")
    
    # Create mod folder structure
    os.makedirs(target_scripts_dir, exist_ok=True)
    
    # Copy main.lua
    shutil.copy(src_lua, dest_lua)
    print(f"[INFO] Copied main.lua to: {dest_lua}")
    
    # Enable the mod in mods.txt
    mods_txt_path = os.path.join(mods_dir, "mods.txt")
    if os.path.exists(mods_txt_path):
        with open(mods_txt_path, "r") as f:
            lines = f.readlines()
            
        # Check if already listed
        already_exists = False
        for line in lines:
            if "TalonDatasetGenerator" in line:
                already_exists = True
                break
                
        if not already_exists:
            # Append enabled line
            with open(mods_txt_path, "a") as f:
                f.write("\nTalonDatasetGenerator : 1\n")
            print("[INFO] Added TalonDatasetGenerator to mods.txt")
        else:
            print("[INFO] TalonDatasetGenerator is already configured in mods.txt")
    else:
        # Create mods.txt if it doesn't exist (unlikely, but safe)
        with open(mods_txt_path, "w") as f:
            f.write("TalonDatasetGenerator : 1\n")
        print("[INFO] Created mods.txt and enabled TalonDatasetGenerator")
        
    print("[SUCCESS] UE4SS Mod successfully installed and enabled! Ready to capture.")

if __name__ == "__main__":
    main()

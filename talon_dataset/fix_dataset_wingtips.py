import os
import json
import glob

def fix_dataset(target_dir):
    print(f"[INFO] Scanning directory for JSON files: {target_dir}")
    json_pattern = os.path.join(target_dir, "*.json")
    json_files = glob.glob(json_pattern)
    
    total_files = len(json_files)
    print(f"[INFO] Found {total_files} JSON metadata files to fix.")
    
    if total_files == 0:
        print("[WARNING] No JSON files found. Please make sure you pointed to the correct dataset folder.")
        return
        
    fixed_count = 0
    for idx, filepath in enumerate(json_files):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check if keypoints_2d exists and has the wingtips
            if "keypoints_2d" in data:
                kps = data["keypoints_2d"]
                if "left_wingtip" in kps and "right_wingtip" in kps:
                    # Swap left_wingtip and right_wingtip values
                    temp = kps["left_wingtip"]
                    kps["left_wingtip"] = kps["right_wingtip"]
                    kps["right_wingtip"] = temp
                    
                    # Save back the updated JSON
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=4)
                    
                    fixed_count += 1
            
            # Print progress every 1000 files
            if (idx + 1) % 1000 == 0 or (idx + 1) == total_files:
                print(f"[PROGRESS] Processed {idx + 1}/{total_files} files...")
                
        except Exception as e:
            print(f"[ERROR] Failed to process {os.path.basename(filepath)}: {e}")
            
    print(f"[SUCCESS] Swapped left_wingtip and right_wingtip in {fixed_count} files successfully!")

if __name__ == "__main__":
    # By default, point to the local dataset directory in the workspace
    current_dir = os.path.dirname(os.path.abspath(__file__))
    local_dataset = os.path.join(current_dir, "dataset")
    
    print("==================================================================")
    # Allow user to specify custom path or use default
    print(f"Default dataset path: {local_dataset}")
    print("If you want to run it on another folder, you can enter the path below.")
    print("Or just press Enter to run it on the default folder.")
    print("==================================================================")
    
    user_path = input("Enter path (or press Enter): ").strip()
    target_path = user_path if user_path else local_dataset
    
    if os.path.exists(target_path):
        fix_dataset(target_path)
    else:
        print(f"[ERROR] Path does not exist: {target_path}")

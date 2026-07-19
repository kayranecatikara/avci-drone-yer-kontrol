import os
import zipfile
import glob
import shutil

def main():
    workspace_dir = r"c:\Users\Zeylo\Desktop\talon_dataset"
    dataset_dest = os.path.join(workspace_dir, "yolo_dataset")
    
    # 1. Search for zip files in common folders
    search_paths = [
        workspace_dir,
        r"C:\Users\Zeylo\Desktop",
        r"C:\Users\Zeylo\Downloads"
    ]
    
    zip_path = None
    all_zips = []
    for path in search_paths:
        if os.path.exists(path):
            zips = glob.glob(os.path.join(path, "*.zip"))
            all_zips.extend(zips)
            
    # Find the zip file (containing 'talon' or 'pose' or being the most recently created zip)
    talon_zips = [z for z in all_zips if "talon" in os.path.basename(z).lower() or "pose" in os.path.basename(z).lower()]
    if talon_zips:
        zip_path = sorted(talon_zips, key=os.path.getmtime, reverse=True)[0]
    elif all_zips:
        # Fallback to the latest zip file created on Desktop or Downloads
        zip_path = sorted(all_zips, key=os.path.getmtime, reverse=True)[0]
        
    if not zip_path:
        print("[ERROR] Could not find any .zip file in workspace, Desktop, or Downloads!")
        print("Please place your downloaded Roboflow .zip file inside the workspace folder:")
        print(f"Path: {workspace_dir}")
        return
        
    print(f"[INFO] Found ZIP dataset at: {zip_path}")
    print(f"[INFO] Extracting to: {dataset_dest}")
    
    # Clean output folder if exists
    if os.path.exists(dataset_dest):
        shutil.rmtree(dataset_dest)
    os.makedirs(dataset_dest, exist_ok=True)
    
    # Extract ZIP
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(dataset_dest)
    print("[SUCCESS] Dataset extracted successfully!")
    
    # 2. Fix data.yaml paths for YOLO to work perfectly with absolute paths
    yaml_path = os.path.join(dataset_dest, "data.yaml")
    if os.path.exists(yaml_path):
        print("[INFO] Updating data.yaml with perfect absolute paths...")
        with open(yaml_path, "r") as f:
            lines = f.readlines()
            
        new_lines = []
        for line in lines:
            if line.strip().startswith("path:"):
                # Force absolute path
                new_lines.append(f"path: {dataset_dest}\n")
            elif line.strip().startswith("train:") and not line.strip().startswith("train: /"):
                new_lines.append(f"train: train/images\n")
            elif line.strip().startswith("val:") and not line.strip().startswith("val: /"):
                new_lines.append(f"val: val/images\n")
            elif line.strip().startswith("test:") and not line.strip().startswith("test: /"):
                new_lines.append(f"test: test/images\n")
            else:
                new_lines.append(line)
                
        with open(yaml_path, "w") as f:
            f.writelines(new_lines)
        print("[SUCCESS] data.yaml fixed!")
        
    # 3. Create the train_yolo26.py script
    train_script_content = """import os
from ultralytics import YOLO

def main():
    # Load YOLO26-Pose model
    model = YOLO("yolo26n-pose.pt")
    
    print("=== STARTING YOLO26-POSE TRAINING ON TALON DRONE ===")
    model.train(
        data=r"{yaml_path}",
        epochs=100,
        imgsz=640,
        device=0,  # Uses NVIDIA GPU automatically
        workers=2,
        batch=8
    )
    print("[SUCCESS] Training completed! Weights saved in runs/pose/train/weights/best.pt")

if __name__ == "__main__":
    main()
""".format(yaml_path=yaml_path)
    
    train_script_path = os.path.join(workspace_dir, "train_yolo26.py")
    with open(train_script_path, "w") as f:
        f.write(train_script_content)
        
    # 4. Create a test_yolo26.py script
    test_script_content = """import os
from ultralytics import YOLO
from PIL import Image

def main():
    # Use best trained weights if exists, fallback to pretrained
    best_weights = r"runs/pose/train/weights/best.pt"
    if os.path.exists(best_weights):
        print(f"[INFO] Loading your custom trained Talon weights: {best_weights}")
        model = YOLO(best_weights)
    else:
        print("[WARNING] Trained weights not found. Running with pretrained YOLO26-Pose model.")
        model = YOLO("yolo26n-pose.pt")
        
    print("\\n=== Enter the absolute path to the photo you want to test: ===")
    test_img = input("Photo path: ").strip().strip('"')
    
    if os.path.exists(test_img):
        print(f"[INFO] Analyzing image: {test_img}")
        results = model.predict(test_img, save=True, imgsz=640)
        
        # Open and display predicted image
        predict_dir = results[0].save_dir
        out_name = os.path.basename(test_img)
        # Note: YOLO increments predict directories like predict, predict2, etc.
        out_img_path = os.path.join(predict_dir, out_name)
        
        if os.path.exists(out_img_path):
            print(f"[SUCCESS] Result saved to: {out_img_path}")
            img = Image.open(out_img_path)
            img.show()
        else:
            print("[ERROR] Could not find the output image.")
    else:
        print("[ERROR] Image file does not exist!")

if __name__ == "__main__":
    main()
"""
    
    test_script_path = os.path.join(workspace_dir, "test_yolo26.py")
    with open(test_script_path, "w") as f:
        f.write(test_script_content)
        
    print(f"\n=== SETUP COMPLETE ===")
    print(f"1. Extracted dataset to: {dataset_dest}")
    print(f"2. Created training script: {train_script_path}")
    print(f"3. Created testing/predict script: {test_script_path}")
    print("\nTo start training on your local PC, run:")
    print("   pip install ultralytics")
    print("   python train_yolo26.py")

if __name__ == "__main__":
    main()

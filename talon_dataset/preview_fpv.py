import cv2
import numpy as np
import os
import glob
from fpv_degradation import degrade_image, load_config

def main():
    # Find a sample image
    dataset_dir = r"C:\Users\Zeylo\Desktop\talon_dataset\dataset"
    images = glob.glob(os.path.join(dataset_dir, "*.png"))
    
    if not images:
        print("No images found in dataset directory to preview.")
        return
        
    img_path = images[-1] # take the most recent image
    print(f"Loading {img_path} for preview...")
    
    original = cv2.imread(img_path)
    if original is None:
        print("Failed to load image.")
        return
        
    config = load_config()
    degraded = degrade_image(original, config)
    
    # Combine side-by-side
    h, w, _ = original.shape
    
    # Add labels
    cv2.putText(original, "Original (Clean)", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 0), 4)
    cv2.putText(degraded, "Degraded (FPV Analog)", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 4)
    
    combined = np.hstack((original, degraded))
    
    # Resize for display so it fits on screen
    screen_w = 1920
    scale = screen_w / combined.shape[1]
    display_img = cv2.resize(combined, (int(combined.shape[1] * scale), int(combined.shape[0] * scale)))
    
    print("Press any key to close the preview...")
    cv2.imshow("FPV Degradation Preview", display_img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

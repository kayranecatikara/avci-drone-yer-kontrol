import os
import cv2
import numpy as np

workspace_dir = r"c:\Users\Zeylo\Desktop\talon_dataset"
dataset_dir = os.path.join(workspace_dir, "dataset")

for df in sorted(os.listdir(dataset_dir)):
    if not df.endswith(".png"):
        continue
    img_path = os.path.join(dataset_dir, df)
    img = cv2.imread(img_path)
    
    # Sample the corners of the image (top-left, top-right)
    h, w, c = img.shape
    tl = img[:100, :100]
    tr = img[:100, -100:]
    
    avg_b = np.mean([tl[:, :, 0], tr[:, :, 0]])
    avg_g = np.mean([tl[:, :, 1], tr[:, :, 1]])
    avg_r = np.mean([tl[:, :, 2], tr[:, :, 2]])
    
    # Sky is blue, so B channel should be significantly higher than R channel
    is_sky = avg_b > avg_r + 20 and avg_b > 120
    
    print(f"{df}: Avg BGR = ({avg_b:.1f}, {avg_g:.1f}, {avg_r:.1f}) | is_sky={is_sky}")

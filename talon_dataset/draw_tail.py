import os
import cv2

workspace_dir = r"c:\Users\Zeylo\Desktop\talon_dataset"
dataset_dir = os.path.join(workspace_dir, "dataset")

measured_f1 = {
    "left_tail_fin": (1004, 476),
    "right_tail_fin": (964, 530),
    "tail": (1024, 524)
}

measured_f3 = {
    "left_tail_fin": (990, 492),
    "right_tail_fin": (958, 534),
    "tail": (1008, 530)
}

for name, filename, targets in [("f1", "talon_0001.png", measured_f1), ("f3", "talon_0003.png", measured_f3)]:
    img_path = os.path.join(dataset_dir, filename)
    img = cv2.imread(img_path)
    
    # Draw circles at measured points
    for kp, pt in targets.items():
        color = (0, 0, 255) if "left" in kp else (0, 255, 0)
        if kp == "tail":
            color = (255, 0, 0)
        cv2.circle(img, pt, 5, color, -1)
        cv2.putText(img, kp, (pt[0]+10, pt[1]), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
    # Crop around the tail (around x=950-1050, y=450-550)
    crop = img[400:600, 900:1100]
    out_path = os.path.join(workspace_dir, f"crop_{name}_tail.png")
    cv2.imwrite(out_path, crop)
    print(f"Saved {out_path}")

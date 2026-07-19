import os
import cv2
import numpy as np

workspace_dir = r"c:\Users\Zeylo\Desktop\talon_dataset"
dataset_dir = os.path.join(workspace_dir, "dataset")

img_path = os.path.join(dataset_dir, "talon_0002.png")
img = cv2.imread(img_path)

# Mapped centroids for talon_0002:
centroids = {
    "right_wingtip": (914.55, 404.85),
    "right_tail_fin": (862.85, 498.20),
    "left_tail_fin": (867.18, 596.50),
    "nose": (1107.31, 603.56),
    "left_wingtip": (1016.74, 800.37),
    "tail": (834.15, 573.63) # Cluster 3: (19.15, 196.63) -> 815+19.15=834.15, 377+196.63=573.63
}

colors = {
    "nose": (255, 0, 0),       # Blue in BGR
    "left_wingtip": (0, 0, 255), # Red
    "right_wingtip": (255, 0, 255), # Pink
    "tail": (0, 165, 255),    # Orange
    "left_tail_fin": (0, 255, 255), # Yellow
    "right_tail_fin": (0, 255, 0)   # Green
}

for name, pt in centroids.items():
    cv2.circle(img, (int(round(pt[0])), int(round(pt[1]))), 10, colors[name], -1)
    cv2.putText(img, name, (int(round(pt[0]))+15, int(round(pt[1]))), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

cv2.imwrite(os.path.join(workspace_dir, "check_annotations_f2.png"), img)
print("Saved check_annotations_f2.png")

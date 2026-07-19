import os
import cv2
import numpy as np

conv_dir = r"C:\Users\Zeylo\.gemini\antigravity\brain\36eff956-7e9e-4245-954f-3ac1eb798a93"

# Centroids from inspect_user_uploads.py:
# Image 1 (Sky View, talon_0001.png match at top-left = (729, 251) in 1920x1080):
#   - Cluster 1: centroid=(257.72, 26.40) -> Left Wingtip (Top)
#   - Cluster 2: centroid=(315.16, 214.87) -> Left Tail Fin tip (Top fin)
#   - Cluster 3: centroid=(22.44, 278.36) -> Nose (Left)
#   - Cluster 4: centroid=(336.66, 295.99) -> Tail (Middle/Right)
#   - Cluster 5: centroid=(273.82, 324.41) -> Right Tail Fin tip (Bottom fin)
#   - Cluster 6: centroid=(150.26, 479.45) -> Right Wingtip (Bottom)
# Note: Left Wingtip Y is smaller (top of screen).
# Note: Y increases downwards.

# Bounding box / Offset for Image 1: x_offset = 729, y_offset = 251
# Let's map Image 1 centroids to talon_0001 coordinates (1920x1080):
offsets_f1 = (729, 251)
img1_centroids = {
    "left_wingtip": (257.72, 26.40),
    "left_tail_fin": (315.16, 214.87),
    "nose": (22.44, 278.36),
    "tail": (336.66, 295.99),
    "right_tail_fin": (273.82, 324.41),
    "right_wingtip": (150.26, 479.45)
}

print("Frame 1 (talon_0001) Exact 2D Coordinates (from User Scribbles):")
for name, (cx, cy) in img1_centroids.items():
    orig_x = cx + offsets_f1[0]
    orig_y = cy + offsets_f1[1]
    print(f"  \"{name}\": {{\"x\": {orig_x:.2f}, \"y\": {orig_y:.2f}}},")

# Image 2 (Landscape View, talon_0002.png match at top-left = (815, 377) in 1920x1080):
# Centroids:
#   * Cluster 1: centroid=(99.55, 27.85) -> Right Wingtip (Top, since it's inverted view: Y of right wingtip is smaller in talon_0002.json: 434 vs 644)
#   * Cluster 2: centroid=(47.85, 121.20) -> Right tail fin tip (Top fin, y=492 vs 532)
#   * Cluster 3: centroid=(52.18, 219.50) -> Left tail fin tip (Bottom fin, y=532)
#   * Cluster 4: centroid=(292.31, 226.56) -> Nose (Right)
#   * Cluster 5: centroid=(201.74, 423.37) -> Left Wingtip (Bottom)
# Let's check clusters vs talon_0002.json:
#   - Tail is at x=908, y=534 in talon_0002.json.
#   - In User Image 2, the tail has a scribble at the propeller hub/shaft (far left of body).
#   - Wait, User Image 2 has 5 clusters detected:
#     1. (99.55, 27.85) -> Wingtip (Top)
#     2. (47.85, 121.20) -> Tail Fin (Top)
#     3. (52.18, 219.50) -> Tail Fin (Bottom)
#     4. (292.31, 226.56) -> Nose (Right)
#     5. (201.74, 423.37) -> Wingtip (Bottom)
#     Wait, what about the Tail? The tail point is at the propeller hub, which is very close to the tail fins. Let's see:
#     In User Image 2, did they draw a circle for the tail?
#     Let's check the scribbles on Image 2:
#     - Nose (far right): Red scribble
#     - Wingtip 1 (top): Red scribble
#     - Wingtip 2 (bottom): Red scribble
#     - Tail fin 1 (top fin tip): Red scribble
#     - Tail fin 2 (bottom fin tip): Red scribble
#     - Tail/Propeller hub (far left): Red scribble (wait, that was Cluster 2 or 3 or is it tail?)
#     Let's check if the tail (propeller hub) is at (47.85, 121.20) or similar.
#     Let's map Image 2 centroids directly to talon_0002 coordinates (1920x1080):
offsets_f2 = (815, 377)
img2_centroids = {
    "right_wingtip": (99.55, 27.85),
    "right_tail_fin": (47.85, 121.20),
    "left_tail_fin": (52.18, 219.50),
    "nose": (292.31, 226.56),
    "left_wingtip": (201.74, 423.37)
}

print("\nFrame 2 (talon_0002) Exact 2D Coordinates (from User Scribbles):")
for name, (cx, cy) in img2_centroids.items():
    orig_x = cx + offsets_f2[0]
    orig_y = cy + offsets_f2[1]
    print(f"  \"{name}\": {{\"x\": {orig_x:.2f}, \"y\": {orig_y:.2f}}},")

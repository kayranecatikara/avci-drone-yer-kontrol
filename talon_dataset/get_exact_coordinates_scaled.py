# Let's map coordinates with the exact scale factors and translation offsets
# Image 1 (talon_0001): Scale = 0.700, Offset = (796, 337)
# Image 2 (talon_0002): Scale = 0.550, Offset = (896, 426)

img1_centroids = {
    "left_wingtip": (257.72, 26.40),
    "left_tail_fin": (315.16, 214.87),
    "nose": (22.44, 278.36),
    "tail": (336.66, 295.99),
    "right_tail_fin": (273.82, 324.41),
    "right_wingtip": (150.26, 479.45)
}

# Fine-clustered centroids for Image 2 (talon_0002):
# - Cluster 1: centroid=(99.55, 27.85), points=158 (Right wingtip)
# - Cluster 2: centroid=(47.85, 121.20), points=234 (Right tail fin tip)
# - Cluster 3: centroid=(19.15, 196.63), points=144 (Tail propeller)
# - Cluster 4: centroid=(292.31, 226.56), points=302 (Nose)
# - Cluster 5: centroid=(68.87, 231.05), points=285 (Left tail fin tip)
# - Cluster 6: centroid=(201.74, 423.37), points=199 (Left wingtip)
img2_centroids = {
    "right_wingtip": (99.55, 27.85),
    "right_tail_fin": (47.85, 121.20),
    "tail": (19.15, 196.63),
    "nose": (292.31, 226.56),
    "left_tail_fin": (68.87, 231.05),
    "left_wingtip": (201.74, 423.37)
}

# Map Image 1
print("Frame 1 (talon_0001) Mapped Coordinates:")
mapped_f1 = {}
scale1 = 0.700
offset1 = (796, 337)
for name, (cx, cy) in img1_centroids.items():
    orig_x = offset1[0] + cx * scale1
    orig_y = offset1[1] + cy * scale1
    # Check if Y axis needs swapping for wingtips/tail_fins
    mapped_f1[name] = (orig_x, orig_y)

# Let's adjust labels based on physical meaning:
# Left wingtip has larger Y in Image 1 (Cluster 6 at bottom: y=479.45)
# Right wingtip has smaller Y (Cluster 1 at top: y=26.40)
# Left tail fin has larger Y (Cluster 5 at bottom: y=324.41)
# Right tail fin has smaller Y (Cluster 2 at top: y=214.87)
corrected_f1 = {
    "nose": mapped_f1["nose"],
    "left_wingtip": mapped_f1["right_wingtip"],
    "right_wingtip": mapped_f1["left_wingtip"],
    "tail": mapped_f1["tail"],
    "left_tail_fin": mapped_f1["right_tail_fin"],
    "right_tail_fin": mapped_f1["left_tail_fin"]
}

for name, (x, y) in corrected_f1.items():
    print(f"  \"{name}\": {{\"x\": {x:.2f}, \"y\": {y:.2f}}},")

# Map Image 2
print("\nFrame 2 (talon_0002) Mapped Coordinates:")
mapped_f2 = {}
scale2 = 0.550
offset2 = (896, 426)
for name, (cx, cy) in img2_centroids.items():
    orig_x = offset2[0] + cx * scale2
    orig_y = offset2[1] + cy * scale2
    mapped_f2[name] = (orig_x, orig_y)

# Correct physical labels for Frame 2:
# Left wingtip is at the bottom (Cluster 6: y=423.37) -> mapped_f2["left_wingtip"]
# Right wingtip is at the top (Cluster 1: y=27.85) -> mapped_f2["right_wingtip"]
# Left tail fin is at the bottom (Cluster 5: y=231.05) -> mapped_f2["left_tail_fin"]
# Right tail fin is at the top (Cluster 2: y=121.20) -> mapped_f2["right_tail_fin"]
# Nose is at the right (Cluster 4: y=226.56) -> mapped_f2["nose"]
# Tail is at the left (Cluster 3: y=196.63) -> mapped_f2["tail"]
corrected_f2 = {
    "nose": mapped_f2["nose"],
    "left_wingtip": mapped_f2["left_wingtip"],
    "right_wingtip": mapped_f2["right_wingtip"],
    "tail": mapped_f2["tail"],
    "left_tail_fin": mapped_f2["left_tail_fin"],
    "right_tail_fin": mapped_f2["right_tail_fin"]
}

for name, (x, y) in corrected_f2.items():
    print(f"  \"{name}\": {{\"x\": {x:.2f}, \"y\": {y:.2f}}},")

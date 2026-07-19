import os
import cv2
import numpy as np

conv_dir = r"C:\Users\Zeylo\.gemini\antigravity\brain\36eff956-7e9e-4245-954f-3ac1eb798a93"
path = os.path.join(conv_dir, "media__1780694886811.png")

if os.path.exists(path):
    img = cv2.imread(path)
    b, g, r = img[:, :, 0], img[:, :, 1], img[:, :, 2]
    
    red_mask = (r > 200) & (g < 100) & (b < 100)
    y, x = np.where(red_mask)
    pts = np.column_stack((x, y))
    
    # We use a smaller distance threshold (e.g. 15 pixels) to separate tail and fins
    clusters = []
    for pt in pts:
        added = False
        for cluster in clusters:
            dists = np.sqrt(np.sum((cluster - pt) ** 2, axis=1))
            if np.any(dists < 15):
                cluster.append(pt)
                added = True
                break
        if not added:
            clusters.append([pt])
            
    print(f"Found {len(clusters)} initial small clusters.")
    
    # Merge clusters only if they are extremely close (e.g. < 25 pixels)
    merged_clusters = []
    while len(clusters) > 0:
        c1 = clusters.pop(0)
        c1_arr = np.array(c1)
        merged = False
        for idx, c2 in enumerate(merged_clusters):
            c2_arr = np.array(c2)
            dists = np.sqrt(np.sum((c2_arr[:, None, :] - c1_arr[None, :, :]) ** 2, axis=-1))
            if np.min(dists) < 25:
                merged_clusters[idx].extend(c1)
                merged = True
                break
        if not merged:
            merged_clusters.append(c1)
            
    print(f"Found {len(merged_clusters)} merged clusters:")
    for idx, cluster in enumerate(merged_clusters):
        c_arr = np.array(cluster)
        centroid = np.mean(c_arr, axis=0)
        print(f" - Cluster {idx+1}: centroid=({centroid[0]:.2f}, {centroid[1]:.2f}), points={len(cluster)}")

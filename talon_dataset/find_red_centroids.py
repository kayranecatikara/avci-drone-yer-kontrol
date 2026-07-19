import os
import cv2
import numpy as np

workspace_dir = r"c:\Users\Zeylo\Desktop\talon_dataset"
media_dir = r"C:\Users\Zeylo\.gemini\antigravity\brain\36eff956-7e9e-4245-954f-3ac1eb798a93\.tempmediaStorage"

user_images = [
    ("media_36eff956-7e9e-4245-954f-3ac1eb798a93_1780695142379.png", "Image 1 (Cropped Sky View)"),
    ("media_36eff956-7e9e-4245-954f-3ac1eb798a93_1780694994065.png", "Image 2 (Full-size Landscape View)")
]

for filename, desc in user_images:
    path = os.path.join(media_dir, filename)
    if not os.path.exists(path):
        print(f"File not found: {filename}")
        continue
    img = cv2.imread(path)
    h, w, c = img.shape
    
    # Red detection mask: R is high, G and B are low.
    # In OpenCV, channels are B, G, R.
    b, g, r = img[:, :, 0], img[:, :, 1], img[:, :, 2]
    
    # Let's adjust thresholds for red scribbles
    # Typically, pure red scribble will have R > 180, G < 80, B < 80
    red_mask = (r > 180) & (g < 100) & (b < 100)
    
    # Get coordinates of red pixels
    y_coords, x_coords = np.where(red_mask)
    pts = np.column_stack((x_coords, y_coords))
    
    print(f"\n--- {desc} ---")
    print(f"Detected {len(pts)} red pixels.")
    
    if len(pts) == 0:
        continue
        
    # Cluster using Simple distance thresholding (or DBSCAN if sklearn is installed)
    # We can implement a simple clustering: if a point is within 50 pixels of another, they are in the same cluster.
    clusters = []
    for pt in pts:
        added = False
        for cluster in clusters:
            # Check distance to cluster center or any point in cluster
            dists = np.sqrt(np.sum((cluster - pt) ** 2, axis=1))
            if np.any(dists < 40): # 40 pixels distance threshold
                cluster.append(pt)
                added = True
                break
        if not added:
            clusters.append([pt])
            
    # Combine clusters that might have been split
    merged_clusters = []
    while len(clusters) > 0:
        c1 = clusters.pop(0)
        c1_arr = np.array(c1)
        merged = False
        for idx, c2 in enumerate(merged_clusters):
            c2_arr = np.array(c2)
            # Find min distance between any point in c1 and any point in c2
            dists = np.sqrt(np.sum((c2_arr[:, None, :] - c1_arr[None, :, :]) ** 2, axis=-1))
            if np.min(dists) < 60:
                merged_clusters[idx].extend(c1)
                merged = True
                break
        if not merged:
            merged_clusters.append(c1)
            
    print(f"Found {len(merged_clusters)} clusters:")
    centroids = []
    for idx, cluster in enumerate(merged_clusters):
        c_arr = np.array(cluster)
        centroid = np.mean(c_arr, axis=0)
        centroids.append(centroid)
        print(f" - Cluster {idx+1}: centroid=({centroid[0]:.2f}, {centroid[1]:.2f}), points={len(cluster)}")
        
    # Let's label them based on the drone geometry
    # Image 1 is talon_0001.png cropped to (744, 291)
    # Image 2 is talon_0001.png full size (1920x1080)

import os
import cv2
import numpy as np

workspace_dir = r"c:\Users\Zeylo\Desktop\talon_dataset"
dataset_dir = os.path.join(workspace_dir, "dataset")

# Let's analyze talon_0001.png
img_path = os.path.join(dataset_dir, "talon_0001.png")
if not os.path.exists(img_path):
    print("Image not found:", img_path)
    exit()

img = cv2.imread(img_path)
h, w, c = img.shape
print(f"Image loaded: {img_path}, size={w}x{h}")

# Convert to HSV or grayscale to segment the drone
# The sky is blue, so we can detect it. Or we can threshold based on intensity and saturation.
# Let's print some color samples at the center (where the drone is) vs the corners (where the sky is)
corner_colors = [img[10, 10], img[10, w-10], img[h-10, 10], img[h-10, w-10]]
print("Corner colors (sky):", [list(col) for col in corner_colors])

# Let's threshold the image. The sky has high blue channel, whereas the drone is grey and has lower intensity/saturation.
# Let's save a mask image where the drone is white and sky is black.
# Usually, sky is blue/white, drone is grey.
# Sky has B > 150, drone has B < 150. Let's try thresholding B channel or L channel of LAB.
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
# Save a thumbnail or downscaled version to see
cv2.imwrite(os.path.join(workspace_dir, "gray.png"), gray)
print("Saved gray.png")

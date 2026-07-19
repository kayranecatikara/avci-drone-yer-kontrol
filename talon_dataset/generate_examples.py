import cv2
import numpy as np
import os

img_path = r"C:\Users\Zeylo\Desktop\talon_dataset\dataset\talon_30000.png"
out_dir = r"C:\Users\Zeylo\.gemini\antigravity\brain\28f3a958-002d-45ff-b96c-7bdb5a3591e3"

img = cv2.imread(img_path)
if img is None:
    print("Image not found!")
    exit(1)

# 1. Puruzsuz (Smoothed / Anti-Aliased) 
# Bilateral filter keeps edges sharp while smoothing pixels
smooth = cv2.bilateralFilter(img, 9, 75, 75)
cv2.imwrite(os.path.join(out_dir, "smooth_example.png"), smooth)

# 2. Kotu (Bad / Noisy / Blurry) for AI robustness
# Add Gaussian noise
noise = np.random.normal(0, 25, img.shape).astype(np.float32)
noisy_img = cv2.add(img.astype(np.float32), noise)
noisy_img = np.clip(noisy_img, 0, 255).astype(np.uint8)

# Add Motion Blur
kernel_size = 15
kernel = np.zeros((kernel_size, kernel_size))
kernel[int((kernel_size-1)/2), :] = np.ones(kernel_size)
kernel /= kernel_size
bad_img = cv2.filter2D(noisy_img, -1, kernel)

# Lower resolution (pixelated)
h, w = bad_img.shape[:2]
bad_img = cv2.resize(bad_img, (w//4, h//4), interpolation=cv2.INTER_LINEAR)
bad_img = cv2.resize(bad_img, (w, h), interpolation=cv2.INTER_NEAREST)

cv2.imwrite(os.path.join(out_dir, "bad_example.png"), bad_img)

print("Images generated in artifacts directory.")

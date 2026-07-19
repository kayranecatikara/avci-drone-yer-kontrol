import cv2
import numpy as np
import os

img_path = r"C:\Users\Zeylo\Desktop\talon_dataset\dataset\talon_30000.png"
out_dir = r"C:\Users\Zeylo\.gemini\antigravity\brain\28f3a958-002d-45ff-b96c-7bdb5a3591e3"

img = cv2.imread(img_path)
if img is None:
    print("Image not found!")
    exit(1)

h, w = img.shape[:2]

# 6. Sert Karıncalanma (Heavy Sensor Noise)
noise_heavy = np.random.randn(h, w, 3) * 70
img_noise_heavy = img.astype(np.float32) + noise_heavy
img_noise_heavy = np.clip(img_noise_heavy, 0, 255).astype(np.uint8)
cv2.imwrite(os.path.join(out_dir, "noise_very_heavy.png"), img_noise_heavy)

# 7. Yatay Tarama Cizgileri (TV Scanlines / Interference)
scanlines = np.copy(img)
for i in range(0, h, 4): # Every 4th line
    scanlines[i:i+2, :] = scanlines[i:i+2, :] * 0.5 # Darken line
cv2.imwrite(os.path.join(out_dir, "aug_scanlines.png"), scanlines)

# 8. Sinyal Kaymasi / Yırtılması (Analog Glitch)
glitch = np.copy(img)
for _ in range(15): # 15 random horizontal tears
    y_start = np.random.randint(0, h-20)
    y_end = y_start + np.random.randint(5, 20)
    shift = np.random.randint(-40, 40)
    
    if shift > 0:
        glitch[y_start:y_end, shift:] = glitch[y_start:y_end, :-shift]
        glitch[y_start:y_end, :shift] = 0
    elif shift < 0:
        glitch[y_start:y_end, :shift] = glitch[y_start:y_end, -shift:]
        glitch[y_start:y_end, shift:] = 0
cv2.imwrite(os.path.join(out_dir, "aug_glitch.png"), glitch)

# 9. Bulaniklik ve Sert Karincalanma Bir Arada (Blur + Heavy Noise)
kernel_size_med = 17
kernel_med = np.zeros((kernel_size_med, kernel_size_med))
for i in range(kernel_size_med):
    kernel_med[i, i] = 1
kernel_med /= kernel_size_med
blur_med = cv2.filter2D(img, -1, kernel_med)

combo_noise = np.random.randn(h, w, 3) * 60
combo = blur_med.astype(np.float32) + combo_noise
combo = np.clip(combo, 0, 255).astype(np.uint8)
cv2.imwrite(os.path.join(out_dir, "aug_combo_blur_noise.png"), combo)

print("Extra augmentations generated.")

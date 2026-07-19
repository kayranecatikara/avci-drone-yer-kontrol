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

# 1. Light Motion Blur (Hafif Hareket Bulanikligi)
kernel_size_light = 9  # Previous was 35 (too heavy), now 9 for slight blur
kernel_light = np.zeros((kernel_size_light, kernel_size_light))
for i in range(kernel_size_light):
    kernel_light[i, i] = 1
kernel_light /= kernel_size_light
blur_light = cv2.filter2D(img, -1, kernel_light)
cv2.imwrite(os.path.join(out_dir, "blur_light.png"), blur_light)

# 2. Medium Motion Blur (Orta Hareket Bulanikligi)
kernel_size_med = 17
kernel_med = np.zeros((kernel_size_med, kernel_size_med))
for i in range(kernel_size_med):
    kernel_med[i, i] = 1
kernel_med /= kernel_size_med
blur_med = cv2.filter2D(img, -1, kernel_med)
cv2.imwrite(os.path.join(out_dir, "blur_medium.png"), blur_med)


# 3. Light Sensor Noise (Hafif Karıncalanma)
noise_light = np.random.randn(h, w, 3) * 20
img_noise_light = img.astype(np.float32) + noise_light
img_noise_light = np.clip(img_noise_light, 0, 255).astype(np.uint8)
cv2.imwrite(os.path.join(out_dir, "noise_light.png"), img_noise_light)

# 4. Colorful Chroma Noise (Renkli Karıncalanma)
noise_chroma = np.random.randn(h, w, 3) * 50
# Convert image to HSV, add noise only to Saturation and Hue to create colorful artifacts
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
hsv[:, :, 0] = hsv[:, :, 0] + np.random.randn(h, w) * 20 # Hue noise
hsv[:, :, 1] = hsv[:, :, 1] + np.random.randn(h, w) * 40 # Saturation noise
hsv[:, :, 0] = np.clip(hsv[:, :, 0], 0, 179)
hsv[:, :, 1] = np.clip(hsv[:, :, 1], 0, 255)
img_chroma = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
cv2.imwrite(os.path.join(out_dir, "noise_colorful.png"), img_chroma)

# 5. Heavy Grain / Salt & Pepper Noise (Bozuk Sinyal Karıncalanması)
row, col, ch = img.shape
s_vs_p = 0.5
amount = 0.04
noisy_sp = np.copy(img)
# Salt mode
num_salt = np.ceil(amount * img.size * s_vs_p)
coords = [np.random.randint(0, i - 1, int(num_salt)) for i in img.shape]
noisy_sp[tuple(coords)] = 255
# Pepper mode
num_pepper = np.ceil(amount * img.size * (1. - s_vs_p))
coords = [np.random.randint(0, i - 1, int(num_pepper)) for i in img.shape]
noisy_sp[tuple(coords)] = 0
cv2.imwrite(os.path.join(out_dir, "noise_heavy.png"), noisy_sp)

print("Focused augmentations generated.")

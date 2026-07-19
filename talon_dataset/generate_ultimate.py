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

# --- ADIM 1: Hareket Bulanikligi Kombinasyonu (Hafif + Orta + Agir) ---
# Combine motion blurs by applying a medium/heavy diagonal blur first
kernel_size = 25
kernel_motion = np.zeros((kernel_size, kernel_size))
for i in range(kernel_size):
    kernel_motion[i, i] = 1
kernel_motion /= kernel_size
ultimate_img = cv2.filter2D(img, -1, kernel_motion)

# --- ADIM 2: Hafif + Sert Kamera Karincalanmasi (Light & Heavy Noise) ---
noise_gaussian = np.random.randn(h, w, 3) * 60
ultimate_img = ultimate_img.astype(np.float32) + noise_gaussian

# --- ADIM 3: Renkli Karincalanma (Chroma Noise) ---
# Add random color shifts
noise_color = np.random.randn(h, w, 3) * 30
ultimate_img += noise_color

# Clamp to prevent overflow before next steps
ultimate_img = np.clip(ultimate_img, 0, 255).astype(np.uint8)

# --- ADIM 4: Sinyal Karincalanmasi / Tuz Biber (Salt & Pepper / Static) ---
amount = 0.03
noisy_sp = np.copy(ultimate_img)
# Salt
num_salt = np.ceil(amount * img.size * 0.5)
coords = [np.random.randint(0, i - 1, int(num_salt)) for i in img.shape]
noisy_sp[tuple(coords)] = 255
# Pepper
num_pepper = np.ceil(amount * img.size * 0.5)
coords = [np.random.randint(0, i - 1, int(num_pepper)) for i in img.shape]
noisy_sp[tuple(coords)] = 0
ultimate_img = noisy_sp

# --- ADIM 5: JPEG Sıkıştırma (İletim Bozulması) ---
encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 10]
result, encimg = cv2.imencode('.jpg', ultimate_img, encode_param)
ultimate_img = cv2.imdecode(encimg, 1)

cv2.imwrite(os.path.join(out_dir, "ultimate_chaos.png"), ultimate_img)
print("Ultimate chaos image generated.")

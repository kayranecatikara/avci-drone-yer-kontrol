import cv2
import numpy as np
import os
import random
import glob

def apply_effect(img, effect_idx):
    h, w = img.shape[:2]
    
    if effect_idx == 1:
        # Sert Karıncalanma
        noise_heavy = np.random.randn(h, w, 3) * 70
        res = img.astype(np.float32) + noise_heavy
        return np.clip(res, 0, 255).astype(np.uint8)
        
    elif effect_idx == 2:
        # Bulanık ve Karlı Kombo
        kernel_size = 17
        kernel = np.zeros((kernel_size, kernel_size))
        for i in range(kernel_size): kernel[i, i] = 1
        kernel /= kernel_size
        blur = cv2.filter2D(img, -1, kernel)
        combo_noise = np.random.randn(h, w, 3) * 60
        res = blur.astype(np.float32) + combo_noise
        return np.clip(res, 0, 255).astype(np.uint8)
        
    elif effect_idx == 3:
        # Hafif Hareket Bulanıklığı
        kernel_size = 9
        kernel = np.zeros((kernel_size, kernel_size))
        for i in range(kernel_size): kernel[i, i] = 1
        kernel /= kernel_size
        return cv2.filter2D(img, -1, kernel)
        
    elif effect_idx == 4:
        # Orta Bulanıklık
        kernel_size = 17
        kernel = np.zeros((kernel_size, kernel_size))
        for i in range(kernel_size): kernel[i, i] = 1
        kernel /= kernel_size
        return cv2.filter2D(img, -1, kernel)
        
    elif effect_idx == 5:
        # Hafif Karıncalanma
        noise_light = np.random.randn(h, w, 3) * 20
        res = img.astype(np.float32) + noise_light
        return np.clip(res, 0, 255).astype(np.uint8)
        
    elif effect_idx == 6:
        # Renkli Karıncalanma
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[:, :, 0] += np.random.randn(h, w) * 20
        hsv[:, :, 1] += np.random.randn(h, w) * 40
        hsv[:, :, 0] = np.clip(hsv[:, :, 0], 0, 179)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1], 0, 255)
        return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
        
    elif effect_idx == 7:
        # Sinyal Karıncalanması
        amount = 0.04
        noisy_sp = np.copy(img)
        num_salt = np.ceil(amount * img.size * 0.5)
        coords = [np.random.randint(0, i - 1, int(num_salt)) for i in img.shape]
        noisy_sp[tuple(coords)] = 255
        num_pepper = np.ceil(amount * img.size * 0.5)
        coords = [np.random.randint(0, i - 1, int(num_pepper)) for i in img.shape]
        noisy_sp[tuple(coords)] = 0
        return noisy_sp
        
    elif effect_idx == 8:
        # Hepsi Bir Arada (Ultimate Chaos)
        kernel_size = 25
        kernel_motion = np.zeros((kernel_size, kernel_size))
        for i in range(kernel_size): kernel_motion[i, i] = 1
        kernel_motion /= kernel_size
        res = cv2.filter2D(img, -1, kernel_motion)
        
        noise_gaussian = np.random.randn(h, w, 3) * 60
        res = res.astype(np.float32) + noise_gaussian
        
        noise_color = np.random.randn(h, w, 3) * 30
        res += noise_color
        res = np.clip(res, 0, 255).astype(np.uint8)
        
        amount = 0.03
        noisy_sp = np.copy(res)
        num_salt = np.ceil(amount * img.size * 0.5)
        coords = [np.random.randint(0, i - 1, int(num_salt)) for i in img.shape]
        noisy_sp[tuple(coords)] = 255
        num_pepper = np.ceil(amount * img.size * 0.5)
        coords = [np.random.randint(0, i - 1, int(num_pepper)) for i in img.shape]
        noisy_sp[tuple(coords)] = 0
        res = noisy_sp
        
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 10]
        _, encimg = cv2.imencode('.jpg', res, encode_param)
        return cv2.imdecode(encimg, 1)

def process_folder_inplace(input_dir):
    # YOLO datasets usually use PNG or JPG
    files = glob.glob(os.path.join(input_dir, "*.png"))
    files.extend(glob.glob(os.path.join(input_dir, "*.jpg")))
    
    print(f"[INFO] Found {len(files)} files in {input_dir}")
    
    effect_counts = {i: 0 for i in range(1, 9)}
    
    for file_path in files:
        img = cv2.imread(file_path)
        if img is None:
            continue
            
        effect = random.randint(1, 8)
        effect_counts[effect] += 1
        aug_img = apply_effect(img, effect)
        
        # Overwrite the original file
        cv2.imwrite(file_path, aug_img)
        
    print("\n--- AUGMENTATION SUMMARY ---")
    for eff_id, count in effect_counts.items():
        print(f"Effect {eff_id}: {count} images")
    print(f"Total processed and OVERWRITTEN: {len(files)}")
    print(f"Directory: {input_dir}")

if __name__ == "__main__":
    target_dir = r"C:\Users\Zeylo\Desktop\ham_veri\resimler"
    if os.path.exists(target_dir):
        process_folder_inplace(target_dir)
    else:
        print(f"Error: Directory does not exist -> {target_dir}")

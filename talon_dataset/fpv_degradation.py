import cv2
import numpy as np
import random
import json
import os

# ---------------------------------------------------------
# FPV DEGRADATION PIPELINE
# Applies realistic analog/sensor noise and artifacts 
# to a clean synthetic image without shifting geometric centers.
# ---------------------------------------------------------

def load_config(config_path="fpv_config.json"):
    if not os.path.exists(config_path):
        return {}
    with open(config_path, "r") as f:
        return json.load(f)

def apply_bloom(img, config):
    cfg = config.get("bloom", {})
    if not cfg.get("enabled", True): return img
    
    threshold = cfg.get("threshold", 200)
    sigma = random.uniform(cfg.get("blur_sigma_min", 10.0), cfg.get("blur_sigma_max", 25.0))
    intensity = random.uniform(cfg.get("intensity_min", 0.3), cfg.get("intensity_max", 0.8))
    
    # Extract bright regions
    _, bright = cv2.threshold(img, threshold, 255, cv2.THRESH_TOZERO)
    
    # Blur the bright regions
    ksize = int(sigma * 3)
    if ksize % 2 == 0: ksize += 1
    blurred = cv2.GaussianBlur(bright, (ksize, ksize), sigma)
    
    # Blend
    img_float = img.astype(np.float32)
    blurred_float = blurred.astype(np.float32) * intensity
    
    # Screen blend mode approximation
    blended = img_float + blurred_float - (img_float * blurred_float / 255.0)
    return np.clip(blended, 0, 255).astype(np.uint8)

def apply_chromatic_aberration(img, config):
    cfg = config.get("chromatic_aberration", {})
    if not cfg.get("enabled", True): return img
    
    max_shift = cfg.get("max_shift_px", 3.0)
    if max_shift <= 0: return img
    
    h, w, _ = img.shape
    # Radial distortion base
    x, y = np.meshgrid(np.arange(w), np.arange(h))
    cx, cy = w / 2.0, h / 2.0
    
    # Distance from center normalized to [0, 1]
    dist = np.sqrt((x - cx)**2 + (y - cy)**2)
    max_dist = np.sqrt(cx**2 + cy**2)
    dist_norm = dist / max_dist
    
    # Calculate shifts for R and B channels (G stays in place)
    # R shifts outwards, B shifts inwards
    shift_amt = max_shift * (dist_norm ** 2) # quadratic scaling
    
    # Calculate angle for displacement
    angle = np.arctan2(y - cy, x - cx)
    
    # Randomize the shift slightly per frame
    current_shift = random.uniform(max_shift * 0.5, max_shift)
    dx_r = np.cos(angle) * shift_amt * (current_shift / max_shift)
    dy_r = np.sin(angle) * shift_amt * (current_shift / max_shift)
    
    dx_b = -np.cos(angle) * shift_amt * (current_shift / max_shift)
    dy_b = -np.sin(angle) * shift_amt * (current_shift / max_shift)
    
    # Create remap maps
    map_x_r = (x - dx_r).astype(np.float32)
    map_y_r = (y - dy_r).astype(np.float32)
    
    map_x_b = (x - dx_b).astype(np.float32)
    map_y_b = (y - dy_b).astype(np.float32)
    
    b, g, r = cv2.split(img)
    
    r_warped = cv2.remap(r, map_x_r, map_y_r, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    b_warped = cv2.remap(b, map_x_b, map_y_b, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    
    return cv2.merge((b_warped, g, r_warped))

def apply_softening(img, config):
    cfg = config.get("softening", {})
    if not cfg.get("enabled", True): return img
    
    sigma = random.uniform(cfg.get("blur_sigma_min", 0.3), cfg.get("blur_sigma_max", 1.2))
    if sigma <= 0.1: return img
    
    ksize = int(sigma * 3)
    if ksize % 2 == 0: ksize += 1
    if ksize < 3: ksize = 3
    
    return cv2.GaussianBlur(img, (ksize, ksize), sigma)

def apply_vignette(img, config):
    cfg = config.get("vignette", {})
    if not cfg.get("enabled", True): return img
    
    intensity = random.uniform(cfg.get("intensity_min", 0.4), cfg.get("intensity_max", 0.8))
    h, w, _ = img.shape
    
    x, y = np.meshgrid(np.linspace(-1, 1, w), np.linspace(-1, 1, h))
    radius = np.sqrt(x**2 + y**2)
    
    # Vignette mask (more aggressive falloff)
    mask = 1.0 - np.clip((radius ** 1.5) * intensity, 0, 1)
    # Smooth the mask
    mask = cv2.GaussianBlur(mask, (0, 0), sigmaX=min(w, h)/10.0)
    
    # Expand dims for broadcasting
    mask = np.expand_dims(mask, axis=2)
    
    return np.clip(img.astype(np.float32) * mask, 0, 255).astype(np.uint8)

def apply_color_grade(img, config):
    cfg = config.get("color_grade", {})
    if not cfg.get("enabled", True): return img
    
    # Desaturation
    sat = random.uniform(cfg.get("saturation_min", 0.5), cfg.get("saturation_max", 0.9))
    # Contrast
    contrast = random.uniform(cfg.get("contrast_min", 0.9), cfg.get("contrast_max", 1.3))
    # WB Shift
    wb_shift = random.uniform(cfg.get("wb_shift_min", -15), cfg.get("wb_shift_max", 15))
    # Brightness (make it darker)
    brightness = random.uniform(-40.0, -10.0)
    
    # Apply contrast and brightness
    img_float = img.astype(np.float32)
    img_float = (img_float - 128.0) * contrast + 128.0 + brightness
    
    # Apply WB shift (add to R, subtract from B)
    # b, g, r
    img_float[:, :, 0] -= wb_shift # Blue
    img_float[:, :, 2] += wb_shift # Red
    img_float = np.clip(img_float, 0, 255).astype(np.uint8)
    
    # Apply saturation
    hsv = cv2.cvtColor(img_float, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[:, :, 1] *= sat
    hsv[:, :, 1] = np.clip(hsv[:, :, 1], 0, 255)
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

def apply_scanline(img, config):
    cfg = config.get("scanline", {})
    if not cfg.get("enabled", True): return img
    
    amp = random.uniform(cfg.get("amplitude_min", 0.10), cfg.get("amplitude_max", 0.25))
    freq = cfg.get("frequency", 2.0)
    
    h, w, _ = img.shape
    y = np.arange(h)
    
    # Phase randomize
    phase = random.uniform(0, 2 * np.pi)
    
    # Sinusoidal multiplier
    mult = 1.0 - amp * (np.sin(y * freq + phase) * 0.5 + 0.5)
    mult = np.expand_dims(mult, axis=1)
    mult = np.expand_dims(mult, axis=2)
    
    return np.clip(img.astype(np.float32) * mult, 0, 255).astype(np.uint8)

def apply_noise(img, config):
    cfg = config.get("noise", {})
    if not cfg.get("enabled", True): return img
    
    # Increase static/noise dramatically
    sigma = random.uniform(cfg.get("sigma_min", 10.0), cfg.get("sigma_max", 15.0))
    
    # Gaussian noise
    noise = np.random.normal(0, sigma, img.shape)
    
    # Poisson (Shot) noise approximation
    # Only applying lightweight Poisson to avoid heavy compute
    img_float = img.astype(np.float32)
    noisy = img_float + noise
    
    return np.clip(noisy, 0, 255).astype(np.uint8)

def apply_jpeg_compression(img, config):
    cfg = config.get("jpeg_compression", {})
    if not cfg.get("enabled", True): return img
    
    q = random.randint(cfg.get("quality_min", 60), cfg.get("quality_max", 90))
    
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), q]
    _, encimg = cv2.imencode('.jpg', img, encode_param)
    decimg = cv2.imdecode(encimg, 1)
    
    return decimg

def degrade_image(img_bgr, config=None):
    """
    Applies the full degradation pipeline to a BGR image.
    Order: Bloom -> Chromatic Aberration -> Softening -> Vignette -> Color Grade -> Scanline -> Noise -> JPEG
    """
    if config is None:
        config = load_config()
        
    prob = config.get("global_degradation_probability", 1.0)
    if random.random() > prob:
        return img_bgr.copy()
        
    img = img_bgr.copy()
    img = apply_bloom(img, config)
    img = apply_chromatic_aberration(img, config)
    img = apply_softening(img, config)
    img = apply_vignette(img, config)
    img = apply_color_grade(img, config)
    img = apply_scanline(img, config)
    img = apply_noise(img, config)
    img = apply_jpeg_compression(img, config)
    
    return img

if __name__ == "__main__":
    print("FPV Degradation module loaded. Use preview_fpv.py to test.")

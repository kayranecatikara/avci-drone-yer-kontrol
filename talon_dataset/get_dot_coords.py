import cv2
import numpy as np

user_img_path = r"C:\Users\Zeylo\.gemini\antigravity\brain\36eff956-7e9e-4245-954f-3ac1eb798a93\media__1780606020349.png"
img = cv2.imread(user_img_path)
h, w, c = img.shape

# The colors of the keypoints in BGR:
# nose: Blue -> R=30, G=100, B=250 -> BGR = (250, 100, 30)
# left_wingtip: Red -> R=255, G=30, B=30 -> BGR = (30, 30, 255)
# right_wingtip: Pink -> R=255, G=100, B=200 -> BGR = (200, 100, 255)
# tail: Orange -> R=255, G=120, B=0 -> BGR = (0, 120, 255)
# left_tail_fin: Yellow -> R=255, G=215, B=0 -> BGR = (0, 215, 255)
# right_tail_fin: Green -> R=0, G=200, B=80 -> BGR = (80, 200, 0)

target_colors = {
    "nose": (250, 100, 30),
    "left_wingtip": (30, 30, 255),
    "right_wingtip": (200, 100, 255),
    "tail": (0, 120, 255),
    "left_tail_fin": (0, 215, 255),
    "right_tail_fin": (80, 200, 0)
}

for name, color in target_colors.items():
    # Find pixels matching this color (with some tolerance, since compression/drawing might shift colors slightly)
    # The drawing script uses fill=color and outline=(255,255,255)
    # Let's search for pixels that are very close to the target color
    diff = np.linalg.norm(img.astype(float) - np.array(color), axis=2)
    ys, xs = np.where(diff < 30) # tolerance 30
    if len(xs) > 0:
        cx, cy = int(np.mean(xs)), int(np.mean(ys))
        print(f"Found '{name}' at ({cx}, {cy})")
    else:
        print(f"Could not find '{name}'")

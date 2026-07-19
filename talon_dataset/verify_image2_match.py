import os
import cv2
import numpy as np

conv_dir = r"C:\Users\Zeylo\.gemini\antigravity\brain\36eff956-7e9e-4245-954f-3ac1eb798a93"
dataset_dir = r"c:\Users\Zeylo\Desktop\talon_dataset\dataset"

user_img = cv2.imread(os.path.join(conv_dir, "media__1780694886811.png"))
h_u, w_u, c_u = user_img.shape

# Crop talon_0002 at (815, 377)
df_img = cv2.imread(os.path.join(dataset_dir, "talon_0002.png"))
df_crop = df_img[377:377+h_u, 815:815+w_u]

# Save side-by-side
combined = np.hstack((user_img, df_crop))
cv2.imwrite(os.path.join(conv_dir, "verify_image2.png"), combined)
print("Saved verify_image2.png")

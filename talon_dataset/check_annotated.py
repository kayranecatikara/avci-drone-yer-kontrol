import os
from PIL import Image

workspace_dir = r"c:\Users\Zeylo\Desktop\talon_dataset"
img_path = os.path.join(workspace_dir, "dataset_annotated", "talon_0001.png")

if os.path.exists(img_path):
    img = Image.open(img_path)
    # Crop around tail (900, 400, 1100, 600)
    crop = img.crop((900, 400, 1100, 600))
    out_path = os.path.join(workspace_dir, "check_annotated_f1.png")
    crop.save(out_path)
    print("Saved check_annotated_f1.png from dataset_annotated")
else:
    print("dataset_annotated/talon_0001.png does not exist!")

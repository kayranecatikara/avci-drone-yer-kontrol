import os
import json

json_path = r"c:\Users\Zeylo\Desktop\talon_dataset\dataset\talon_0002.json"
if os.path.exists(json_path):
    with open(json_path, "r") as f:
        data = json.load(f)
    print(json.dumps(data, indent=4))
else:
    print("File not found.")

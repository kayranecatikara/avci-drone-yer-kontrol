import os
import sys
import json
import math

try:
    import matplotlib.pyplot as plt
    import matplotlib.image as mpimg
    import numpy as np
except ImportError:
    print("[INFO] Matplotlib veya Numpy yüklü değil. Kuruluyor...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "matplotlib", "numpy"])
    import matplotlib.pyplot as plt
    import matplotlib.image as mpimg
    import numpy as np

def get_unreal_matrix(pitch, yaw, roll):
    SP, CP = math.sin(math.radians(pitch)), math.cos(math.radians(pitch))
    SY, CY = math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
    SR, CR = math.sin(math.radians(roll)), math.cos(math.radians(roll))
    r00 = CP * CY; r10 = CP * SY; r20 = SP
    r01 = SR * SP * CY - CR * SY; r11 = SR * SP * SY + CR * CY; r21 = -SR * CP
    r02 = -(CR * SP * CY + SR * SY); r12 = CY * SR - CR * SP * SY; r22 = CR * CP
    return np.array([[r00, r01, r02], [r10, r11, r12], [r20, r21, r22]])

def get_world_ray(u, v, cam_rot, fov=125.0, width=1920, height=1080):
    focal_length = (width / 2.0) / math.tan(math.radians(fov / 2.0))
    y_local = (u - width/2.0) / focal_length
    z_local = (height/2.0 - v) / focal_length
    x_local = 1.0
    R = get_unreal_matrix(cam_rot['pitch'], cam_rot['yaw'], cam_rot['roll'])
    v_local = np.array([x_local, y_local, z_local])
    dir_world = R @ v_local
    dir_world = dir_world / np.linalg.norm(dir_world)
    return dir_world

def closest_distance_between_lines(p1, d1, p2, d2):
    w0 = p1 - p2
    a = np.dot(d1, d1)
    b = np.dot(d1, d2)
    c = np.dot(d2, d2)
    d = np.dot(d1, w0)
    e = np.dot(d2, w0)
    
    D = a*c - b*b
    if D < 1e-7:
        return p1, p2
    
    t1 = (b*e - c*d) / D
    t2 = (a*e - b*d) / D
    
    P1 = p1 + t1 * d1
    P2 = p2 + t2 * d2
    return P1, P2

def main():
    workspace_dir = r"c:\Users\Zeylo\Desktop\talon_dataset"
    dataset_dir = os.path.join(workspace_dir, "dataset")
    
    files = [f for f in os.listdir(dataset_dir) if f.endswith(".png")]
    if len(files) < 2:
        print("En az 2 fotoğraf gerekiyor!")
        return
        
    print("Stereo 3D Kalibrasyon Aracına Hoş Geldiniz!")
    print("Lütfen ilk fotoğrafı seçin (örneğin 0, 1, 2...):")
    for i, f in enumerate(files[:10]):
        print(f"[{i}] {f}")
    
    try:
        idx1 = int(input("1. Fotoğraf Numarası: "))
        idx2 = int(input("2. Fotoğraf Numarası (farklı bir açıdan olsun!): "))
    except ValueError:
        print("Lütfen geçerli bir sayı girin.")
        return
        
    file1 = files[idx1]
    file2 = files[idx2]
    
    def load_data(filename):
        base_name = os.path.splitext(filename)[0]
        json_path = os.path.join(dataset_dir, base_name + ".json")
        img_path = os.path.join(dataset_dir, filename)
        with open(json_path, "r") as jf:
            data = json.load(jf)
        return data, img_path
        
    data1, img_path1 = load_data(file1)
    data2, img_path2 = load_data(file2)
    
    keypoints = ["nose", "left_wingtip", "right_wingtip", "tail", "left_tail_fin", "right_tail_fin"]
    new_cad_data = {}
    
    for key in keypoints:
        print(f"\n[{key}] için 1. fotoğrafa tıklayın...")
        img1 = mpimg.imread(img_path1)
        fig, ax = plt.subplots(figsize=(16, 9))
        ax.imshow(img1)
        ax.set_title(f"1. FOTO: Lütfen {key.upper()} noktasına TIKLA")
        clicks1 = plt.ginput(1, timeout=0)
        plt.close()
        
        print(f"[{key}] için 2. fotoğrafa tıklayın...")
        img2 = mpimg.imread(img_path2)
        fig, ax = plt.subplots(figsize=(16, 9))
        ax.imshow(img2)
        ax.set_title(f"2. FOTO: Lütfen {key.upper()} noktasına TIKLA")
        clicks2 = plt.ginput(1, timeout=0)
        plt.close()
        
        u1, v1 = clicks1[0]
        u2, v2 = clicks2[0]
        
        # Ray 1'i Drone 1 Local Space'ine taşı
        drone_loc1 = np.array([data1["drone_location"]["x"], data1["drone_location"]["y"], data1["drone_location"]["z"]])
        R_drone1 = get_unreal_matrix(data1["drone_rotation"]["pitch"], data1["drone_rotation"]["yaw"], data1["drone_rotation"]["roll"])
        cam_loc1 = np.array([data1["camera_location"]["x"], data1["camera_location"]["y"], data1["camera_location"]["z"]])
        dir1_world = get_world_ray(u1, v1, data1["camera_rotation"], data1.get("camera_fov", 125.0))
        cam_local1 = R_drone1.T @ (cam_loc1 - drone_loc1)
        dir_local1 = R_drone1.T @ dir1_world
        
        # Ray 2'yi Drone 2 Local Space'ine taşı
        drone_loc2 = np.array([data2["drone_location"]["x"], data2["drone_location"]["y"], data2["drone_location"]["z"]])
        R_drone2 = get_unreal_matrix(data2["drone_rotation"]["pitch"], data2["drone_rotation"]["yaw"], data2["drone_rotation"]["roll"])
        cam_loc2 = np.array([data2["camera_location"]["x"], data2["camera_location"]["y"], data2["camera_location"]["z"]])
        dir2_world = get_world_ray(u2, v2, data2["camera_rotation"], data2.get("camera_fov", 125.0))
        cam_local2 = R_drone2.T @ (cam_loc2 - drone_loc2)
        dir_local2 = R_drone2.T @ dir2_world
        
        # Kesişim noktasını LOCAL SPACE'de bul
        P1, P2 = closest_distance_between_lines(cam_local1, dir_local1, cam_local2, dir_local2)
        P_local = (P1 + P2) / 2.0
        
        error = np.linalg.norm(P1 - P2)
        print(f"-> 3D Kesişim Hatası: {error:.2f} cm")
        
        ue_x, ue_y, ue_z = P_local[0], P_local[1], P_local[2]
        
        # UE'den CAD formatına çevir
        cad_x = -ue_x * 10.0
        cad_z = -ue_y * 10.0
        cad_y = ue_z * 10.0
        
        new_cad_data[key] = {"x": round(cad_x, 2), "y": round(cad_y, 2), "z": round(cad_z, 2)}

    print("\n=======================================================")
    print("MÜKEMMEL STEREO 3D KALİBRASYON TAMAMLANDI!")
    print("Aşağıdaki RAW_CAD_DATA tablosunu kopyalayıp kullanabilirsin:")
    print("RAW_CAD_DATA = {")
    for key, val in new_cad_data.items():
        print(f'    "{key}": {{"x": {val["x"]}, "y": {val["y"]}, "z": {val["z"]}}},')
    print("}")
    print("=======================================================\n")

if __name__ == "__main__":
    main()

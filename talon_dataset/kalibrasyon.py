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

# Eski/Mevcut CAD Datası (Sadece Z yüksekliklerini referans almak için kullanıyoruz)
RAW_CAD_DATA = {
    "nose":             {"x": -554.32, "y": -12.66, "z": -0.03},
    "left_wingtip":     {"x": 97.71,   "y": 45.45,  "z": 858.97},
    "right_wingtip":    {"x": 97.71,   "y": 45.45,  "z": -859.03},
    "tail":             {"x": 560.16,  "y": -43.79, "z": 0.01},
    "left_tail_fin":    {"x": 527.61,  "y": 179.87, "z": 225.64},
    "right_tail_fin":   {"x": 527.61,  "y": 179.87, "z": -225.70}
}

def get_unreal_matrix(pitch, yaw, roll):
    SP, CP = math.sin(math.radians(pitch)), math.cos(math.radians(pitch))
    SY, CY = math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
    SR, CR = math.sin(math.radians(roll)), math.cos(math.radians(roll))
    
    r00 = CP * CY; r10 = CP * SY; r20 = SP
    r01 = SR * SP * CY - CR * SY; r11 = SR * SP * SY + CR * CY; r21 = -SR * CP
    r02 = -(CR * SP * CY + SR * SY); r12 = CY * SR - CR * SP * SY; r22 = CR * CP
    return [[r00, r01, r02], [r10, r11, r12], [r20, r21, r22]]

def get_world_ray(u, v, cam_rot, fov=125.0, width=1920, height=1080):
    focal_length = (width / 2.0) / math.tan(math.radians(fov / 2.0))
    y_local = (u - width/2.0) / focal_length
    z_local = (height/2.0 - v) / focal_length
    x_local = 1.0
    
    R = get_unreal_matrix(cam_rot['pitch'], cam_rot['yaw'], cam_rot['roll'])
    
    dir_world_x = x_local * R[0][0] + y_local * R[0][1] + z_local * R[0][2]
    dir_world_y = x_local * R[1][0] + y_local * R[1][1] + z_local * R[1][2]
    dir_world_z = x_local * R[2][0] + y_local * R[2][1] + z_local * R[2][2]
    
    return dir_world_x, dir_world_y, dir_world_z

def main():
    workspace_dir = r"c:\Users\Zeylo\Desktop\talon_dataset"
    dataset_dir = os.path.join(workspace_dir, "dataset")
    if not os.path.exists(dataset_dir):
        print("[HATA] dataset klasörü bulunamadı!")
        return

    files = [f for f in os.listdir(dataset_dir) if f.endswith(".png")]
    if not files:
        print("[HATA] Klasörde fotoğraf yok!")
        return

    # İlk fotoğrafı seç
    filename = files[0]
    base_name = os.path.splitext(filename)[0]
    img_path = os.path.join(dataset_dir, filename)
    json_path = os.path.join(dataset_dir, base_name + ".json")

    with open(json_path, "r") as jf:
        data = json.load(jf)

    drone_loc = data["drone_location"]
    drone_rot = data["drone_rotation"]
    cam_loc = data["camera_location"]
    cam_rot = data["camera_rotation"]
    cam_fov = data.get("camera_fov", 125.0)

    print(f"\n[SİSTEM AÇILIYOR] {filename} fotoğrafı ekrana getiriliyor...")
    print("DİKKAT: Ekrana açılacak fotoğrafta sırasıyla şu noktalara TIKLAMALISIN (Sırayı bozma!):")
    print("  1. Burun Ucu")
    print("  2. Sol Kanat Ucu (Uçağın kendi solu)")
    print("  3. Sağ Kanat Ucu")
    print("  4. Motor (Ortadaki arka kısım)")
    print("  5. Sol Kuyruk Ucu")
    print("  6. Sağ Kuyruk Ucu")
    
    img = mpimg.imread(img_path)
    fig, ax = plt.subplots(figsize=(16, 9))
    ax.imshow(img)
    ax.set_title("Sırayla tıkla: Burun -> SolKanat -> SağKanat -> Motor -> SolKuyruk -> SağKuyruk")
    plt.axis('off')
    
    # Kullanıcıdan 6 tıklama al
    clicks = plt.ginput(6, timeout=0, show_clicks=True)
    plt.close()

    if len(clicks) < 6:
        print("\n[HATA] 6 noktayı tam tıklamadın! Lütfen baştan çalıştır.")
        return

    print("\n[HESAPLANIYOR] Lazer projeksiyon işlemi başlatıldı...")
    
    keys = ["nose", "left_wingtip", "right_wingtip", "tail", "left_tail_fin", "right_tail_fin"]
    new_cad_data = {}

    for i, key in enumerate(keys):
        u, v = clicks[i]
        
        # Lazer ışınının dünya uzayındaki yönü
        dir_w_x, dir_w_y, dir_w_z = get_world_ray(u, v, cam_rot, fov=cam_fov)
        
        # Lazer orijini (kamera) ve yönünü Uçağın Lokal Uzayına taşı
        dx = cam_loc["x"] - drone_loc["x"]
        dy = cam_loc["y"] - drone_loc["y"]
        dz = cam_loc["z"] - drone_loc["z"]
        
        R_drone = get_unreal_matrix(drone_rot["pitch"], drone_rot["yaw"], drone_rot["roll"])
        
        # v_local = R^T * v_world
        cam_local_x = dx * R_drone[0][0] + dy * R_drone[1][0] + dz * R_drone[2][0]
        cam_local_y = dx * R_drone[0][1] + dy * R_drone[1][1] + dz * R_drone[2][1]
        cam_local_z = dx * R_drone[0][2] + dy * R_drone[1][2] + dz * R_drone[2][2]
        
        dir_local_x = dir_w_x * R_drone[0][0] + dir_w_y * R_drone[1][0] + dir_w_z * R_drone[2][0]
        dir_local_y = dir_w_x * R_drone[0][1] + dir_w_y * R_drone[1][1] + dir_w_z * R_drone[2][1]
        dir_local_z = dir_w_x * R_drone[0][2] + dir_w_y * R_drone[1][2] + dir_w_z * R_drone[2][2]
        
        # Bilinen Z yüksekliği (CAD tablosundaki Y eksenine denk gelir, cm cinsinden)
        known_ue_z = RAW_CAD_DATA[key]["y"] / 10.0
        
        # Z = known_ue_z düzlemi ile lazeri kesiştir
        t = (known_ue_z - cam_local_z) / dir_local_z
        
        ue_x = cam_local_x + t * dir_local_x
        ue_y = cam_local_y + t * dir_local_y
        ue_z = known_ue_z
        
        # UE (cm) koordinatından geri CAD (mm) koordinatına çevir
        # draw_keypoints'te kullandığımız formülün tam tersi:
        # ue_x = -cad["x"] / 10.0  => cad["x"] = -ue_x * 10.0
        # ue_y = -cad["z"] / 10.0  => cad["z"] = -ue_y * 10.0
        # ue_z = cad["y"] / 10.0   => cad["y"] = ue_z * 10.0
        new_cad_x = -ue_x * 10.0
        new_cad_z = -ue_y * 10.0
        new_cad_y = ue_z * 10.0
        
        new_cad_data[key] = {"x": round(new_cad_x, 2), "y": round(new_cad_y, 2), "z": round(new_cad_z, 2)}
        
    print("\n=============================================")
    print("YEPYENİ VE KUSURSUZ CAD TABLOSU HAZIRLANDI!")
    print("Lütfen bu tabloyu draw_keypoints.py içine kopyala:")
    print("=============================================\n")
    
    print("RAW_CAD_DATA = {")
    for k, v in new_cad_data.items():
        print(f'    "{k}": {{"x": {v["x"]}, "y": {v["y"]}, "z": {v["z"]}}},')
    print("}")
    
    print("\n[BİLGİ] Kalibrasyon tamamlandı! Yukarıdaki RAW_CAD_DATA verisini al ve kullan.")

if __name__ == "__main__":
    main()

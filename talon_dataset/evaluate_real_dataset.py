import cv2
import numpy as np
import json
import matplotlib.pyplot as plt
import math
import os
import glob

# ==========================================
# GERCEK 3D CAD KOORDINATLARI (METRE CINSINDEN)
# ==========================================
# Talon'un gercek fiziksel boyutlaridir. (X: Ileri, Y: Sag/Sol, Z: Yukari)
CAD_3D_POINTS = {
    "Nose":           [ 0.6913,  0.0019, -0.0277],
    "Left_Wingtip":   [ 0.0165, -0.9993,  0.0581],
    "Right_Wingtip":  [ 0.0165,  0.9993,  0.0581],
    "Tail":           [-0.5538,  0.0010,  0.0010],
    "Left_Tail_Fin":  [-0.4317, -0.2825,  0.1698],
    "Right_Tail_Fin": [-0.4317,  0.2825,  0.1698]
}

# ==========================================
# KAMERA IÇ PARAMETRELERI
# ==========================================
def get_camera_intrinsics(width, height, hfov_deg):
    hfov_rad = math.radians(hfov_deg)
    f_x = (width / 2.0) / math.tan(hfov_rad / 2.0)
    f_y = f_x
    c_x = width / 2.0
    c_y = height / 2.0
    
    camera_matrix = np.array([
        [f_x, 0,   c_x],
        [0,   f_y, c_y],
        [0,   0,   1]
    ], dtype=np.float64)
    
    dist_coeffs = np.zeros((4,1))
    return camera_matrix, dist_coeffs

# ==========================================
# GPS MESAFESI HESAPLAMA
# ==========================================
def calculate_gps_distance(loc1, loc2):
    # Unreal Engine lokasyonlari cm cinsindendir, sonucta metreye donusturuyoruz (/100)
    dx = loc1["x"] - loc2["x"]
    dy = loc1["y"] - loc2["y"]
    dz = loc1["z"] - loc2["z"]
    return math.sqrt(dx**2 + dy**2 + dz**2) / 100.0

# ==========================================
# ASIL FONKSIYON: GERCEK VERI SETINI OKU VE ANALIZ ET
# ==========================================
def evaluate_real_dataset(dataset_dir="dataset"):
    print(f"[ANALIZ] Gercek veri seti taraniyor: {dataset_dir} ...")
    json_files = glob.glob(os.path.join(dataset_dir, "*.json"))
    json_files.sort() # Zaman (kare) siralamasi
    
    if not json_files:
        print("[HATA] JSON dosyasi bulunamadi!")
        return

    # Ilk dosyadan kamera ayarlarini alalim
    with open(json_files[0], 'r') as f:
        first_data = json.load(f)
        hfov = first_data.get("camera_fov", 125.0)
    
    cam_mat, dist_coef = get_camera_intrinsics(1920, 1080, hfov)
    
    gps_logs = []
    pnp_logs = []
    times = []
    
    for idx, j_path in enumerate(json_files):
        try:
            with open(j_path, 'r') as f:
                data = json.load(f)
                
            cam_loc = data.get("camera_location")
            drone_loc = data.get("drone_location")
            kp_2d = data.get("keypoints_2d")
            
            if not cam_loc or not drone_loc or not kp_2d:
                continue
                
            # 1. Gercek GPS Mesafesi
            real_dist = calculate_gps_distance(cam_loc, drone_loc)
            
            # 2. PnP Mesafesi (Pose Tahmini)
            obj_points = []
            img_points = []
            
            for kp_name, coords_3d in CAD_3D_POINTS.items():
                kp_data = kp_2d.get(kp_name)
                if kp_data and kp_data.get("on", False):
                    obj_points.append(coords_3d)
                    img_points.append([kp_data["x"], kp_data["y"]])
                    
            if len(img_points) >= 4: # PnP icin en az 4 nokta sarti
                obj_pts_arr = np.array(obj_points, dtype=np.float32)
                img_pts_arr = np.array(img_points, dtype=np.float32)
                
                success, rvec, tvec = cv2.solvePnP(
                    obj_pts_arr, img_pts_arr, cam_mat, dist_coef, flags=cv2.SOLVEPNP_ITERATIVE
                )
                
                if success:
                    pnp_dist = tvec[2][0] # Z-depth
                    
                    times.append(idx)
                    gps_logs.append(real_dist)
                    pnp_logs.append(pnp_dist)
                    
        except Exception as e:
            print(f"[HATA] Dosya okunurken hata {j_path}: {e}")
            
    # Sonuclari Gorsellestir
    if not times:
        print("[HATA] Gecerli nokta veya PnP verisi bulunamadi.")
        return
        
    errors = np.array(pnp_logs) - np.array(gps_logs)
    rmse_overall = np.sqrt(np.mean(errors**2))
    
    terminal_indices = [i for i, d in enumerate(gps_logs) if d < 10.0]
    if terminal_indices:
        terminal_errors = errors[terminal_indices]
        rmse_terminal = np.sqrt(np.mean(terminal_errors**2))
    else:
        rmse_terminal = 0.0
        
    plt.figure(figsize=(12, 6))
    plt.plot(times, gps_logs, label="GERCEK GPS/GNSS Mesafesi", color="blue", linewidth=2.5)
    plt.plot(times, pnp_logs, label="PnP Tahmini (Oyun 2D Pikselleri)", color="red", linestyle="--", linewidth=1.5)
    
    if terminal_indices:
        start_t = times[terminal_indices[0]]
        end_t = times[terminal_indices[-1]]
        plt.axvspan(start_t, end_t, color='red', alpha=0.15, label="Terminal Asama (<10m)")
        
    plt.title("GERCEK VERI: Pose Modeli PnP vs GPS Angajman Analizi", fontsize=14, fontweight="bold")
    plt.xlabel("Kare (Frame / Zaman)")
    plt.ylabel("Mesafe (Metre)")
    plt.grid(True, linestyle=":", alpha=0.7)
    
    info_text = f"GENEL HATA (RMSE): {rmse_overall:.2f} m\nTERMINAL (<10m) HATA: {rmse_terminal:.2f} m"
    plt.gca().text(0.02, 0.05, info_text, transform=plt.gca().transAxes, 
                   fontsize=12, bbox=dict(facecolor='white', alpha=0.9, edgecolor='black'))
    
    plt.legend()
    plt.tight_layout()
    plt.savefig("gercek_veri_analizi.png")
    print(f"[BASARILI] Gercek verilerle analiz tamamlandi! Hata (RMSE): {rmse_overall:.2f}m")
    print("[SONUC] Grafik 'gercek_veri_analizi.png' olarak kaydedildi.")

if __name__ == "__main__":
    evaluate_real_dataset()

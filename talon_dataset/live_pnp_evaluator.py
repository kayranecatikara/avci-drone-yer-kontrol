import os
import time
import json
import cv2
import numpy as np
import math
import matplotlib.pyplot as plt

# ==========================================
# GERCEK 3D CAD KOORDINATLARI (METRE CINSINDEN)
# ==========================================
CAD_3D_POINTS = {
    "Nose":           [ 0.6913,  0.0019, -0.0277],
    "Left_Wingtip":   [ 0.0165, -0.9993,  0.0581],
    "Right_Wingtip":  [ 0.0165,  0.9993,  0.0581],
    "Tail":           [-0.5538,  0.0010,  0.0010],
    "Left_Tail_Fin":  [-0.4317, -0.2825,  0.1698],
    "Right_Tail_Fin": [-0.4317,  0.2825,  0.1698]
}

def get_camera_intrinsics(width, height, hfov_deg):
    hfov_rad = math.radians(hfov_deg)
    f_x = (width / 2.0) / math.tan(hfov_rad / 2.0)
    c_x = width / 2.0
    c_y = height / 2.0
    camera_matrix = np.array([[f_x, 0, c_x], [0, f_x, c_y], [0, 0, 1]], dtype=np.float64)
    return camera_matrix, np.zeros((4,1))

def run_live_evaluator():
    status_file = "status.txt"
    print("==================================================")
    print("[LIVE] CANLI UCUS TESTI BASLADI!")
    print("[LIVE] Oyuna girin ve ucmaya baslayin...")
    print("[LIVE] Sistemi durdurmak ve grafikleri gormek icin CTRL+C'ye basin.")
    print("==================================================")
    
    last_content = ""
    gps_history = []
    pnp_history = []
    times = []
    
    start_time = time.time()
    
    try:
        while True:
            # Oyundan gelen CANLI veriyi status.txt uzerinden dinliyoruz
            try:
                with open(status_file, "r") as f:
                    content = f.read().strip()
            except IOError:
                time.sleep(0.1)
                continue
                
            if content and content != last_content and content.startswith("{") and content.endswith("}"):
                last_content = content
                try:
                    data = json.loads(content)
                except Exception:
                    continue
                    
                cam_loc = data.get("camera_location")
                drone_loc = data.get("drone_location")
                kp_2d = data.get("keypoints_2d")
                
                # Sadece ucak ekrandaysa ve koordinatlar geliyorsa hesapla
                if cam_loc and drone_loc and kp_2d:
                    # 1. GERCEK GPS MESAFESI
                    dx = cam_loc["x"] - drone_loc["x"]
                    dy = cam_loc["y"] - drone_loc["y"]
                    dz = cam_loc["z"] - drone_loc["z"]
                    real_dist = math.sqrt(dx**2 + dy**2 + dz**2) / 100.0
                    
                    # 2. CANLI PnP MESAFESI
                    cam_mat, dist_coef = get_camera_intrinsics(1920, 1080, data.get("camera_fov", 125.0))
                    obj_points, img_points = [], []
                    
                    for kp_name, coords_3d in CAD_3D_POINTS.items():
                        kp_data = kp_2d.get(kp_name)
                        if kp_data and kp_data.get("on", False):
                            obj_points.append(coords_3d)
                            img_points.append([kp_data["x"], kp_data["y"]])
                            
                    if len(img_points) >= 4:
                        succ, rvec, tvec = cv2.solvePnP(
                            np.array(obj_points, dtype=np.float32), 
                            np.array(img_points, dtype=np.float32), 
                            cam_mat, dist_coef, flags=cv2.SOLVEPNP_ITERATIVE
                        )
                        
                        if succ:
                            pnp_dist = tvec[2][0]
                            t = time.time() - start_time
                            
                            times.append(t)
                            gps_history.append(real_dist)
                            pnp_history.append(pnp_dist)
                            
                            err = abs(pnp_dist - real_dist)
                            # Ekrana canli terminal ciktisi ver!
                            print(f"[Zaman: {t:4.1f}s]  GPS Gercek: {real_dist:5.1f}m  |  PnP Tahmin: {pnp_dist:5.1f}m  |  Anlik Sapma: {err:4.1f}m")
                            
            # Her 0.5 saniyede bir ornek al (Saniyede 2 kez)
            time.sleep(0.5) 
            
    except KeyboardInterrupt:
        print("\n==================================================")
        print("[LIVE] UCUS BITIRILDI! Rapor Grafigi Hazirlaniyor...")
        if times:
            errors = np.array(pnp_history) - np.array(gps_history)
            rmse_overall = np.sqrt(np.mean(errors**2))
            
            plt.figure(figsize=(10,6))
            plt.plot(times, gps_history, label="Gercek GPS (Ground Truth)", color="blue", linewidth=2)
            plt.plot(times, pnp_history, label="PnP Tahmini", color="red", linestyle="--", linewidth=2)
            
            plt.title(f"CANLI UCUS: Otonom Hedef Angajmani\nGenel Hata (RMSE): {rmse_overall:.2f} m", fontweight="bold")
            plt.xlabel("Saniye (Ucus Suresi)")
            plt.ylabel("Mesafe (Metre)")
            plt.grid(True, linestyle=":", alpha=0.7)
            plt.legend()
            
            plt.tight_layout()
            plt.savefig("canli_ucus_raporu.png")
            print(f"[BASARILI] Sonuclar 'canli_ucus_raporu.png' olarak kaydedildi. Gidip bakabilirsin!")
        else:
            print("[HATA] Yeterli veri toplanamadi, ucus cok kisa surmus olabilir.")
        print("==================================================")

if __name__ == "__main__":
    run_live_evaluator()

import cv2
import numpy as np
import json
import matplotlib.pyplot as plt
import math
import os

# ==========================================
# GIRDILER VE SABITLER
# ==========================================
IMG_WIDTH = 1920
IMG_HEIGHT = 1080
H_FOV_DEG = 125.0

# Talon IHA kaba 3D kilit noktalari (metre cinsinden - ornek olarak)
# Gercek projede bu noktalar sabit CAD modeli olculerinden gelir.
TARGET_3D_POINTS = np.array([
    [ 0.69,  0.00, -0.02], # Burun (Nose)
    [ 0.01, -0.99,  0.05], # Sol Kanat Ucu (Left Wingtip)
    [ 0.01,  0.99,  0.05], # Sag Kanat Ucu (Right Wingtip)
    [-0.55,  0.00,  0.00], # Kuyruk (Tail)
    [-0.43, -0.28,  0.16], # Sol Kuyruk Kanatcigi
    [-0.43,  0.28,  0.16]  # Sag Kuyruk Kanatcigi
], dtype=np.float32)

# ==========================================
# ASAMA 1: PnP ILE ANGAJMAN MESAFESI KESTIRIMI
# ==========================================
def get_camera_intrinsics(width, height, hfov_deg):
    """
    Kamera ic parametre matrisini (Intrinsic Matrix) hesaplar.
    f_x = (width / 2) / tan(hFOV / 2)
    Piksellerin kare (aspect ratio = 1) oldugu varsayilarak f_y = f_x alinir.
    """
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
    
    dist_coeffs = np.zeros((4,1)) # Distorsiyon varsayilan olarak 0
    return camera_matrix, dist_coeffs

def estimate_distance_pnp(points_2d, camera_matrix, dist_coeffs):
    """
    2D piksel kordinatlari ve 3D dunya koordinatlarini kullanarak
    hedefin kameraya olan Z (derinlik) mesafesini hesaplar.
    """
    points_2d = np.array(points_2d, dtype=np.float32)
    success, rotation_vector, translation_vector = cv2.solvePnP(
        TARGET_3D_POINTS, points_2d, camera_matrix, dist_coeffs, flags=cv2.SOLVEPNP_ITERATIVE
    )
    
    if not success:
        return None
        
    # translation_vector[2] = Z ekseni = Kameradan dogrudan derinlik
    return translation_vector[2][0]

def calculate_gps_distance(pos_hunter, pos_target):
    """ Iki GPS/3D koordinat arasindaki Oklid mesafesini (metre) hesaplar. """
    return math.sqrt(sum((a - b)**2 for a, b in zip(pos_hunter, pos_target)))

# ==========================================
# ASAMA 2: SANIYE BAZLI LOGLAMA (MOCK FLIGHT)
# ==========================================
def run_dummy_simulation():
    print("[SIMULASYON] Kamikaze dalis senaryosu baslatiliyor...")
    cam_mat, dist_coef = get_camera_intrinsics(IMG_WIDTH, IMG_HEIGHT, H_FOV_DEG)
    
    pnp_logs = []
    gps_logs = []
    
    # 20 saniyelik bir dalis senaryosu
    hunter_start = np.array([0, 0, 100]) # Hunter 100m yukseklikte
    target_pos = np.array([0, 50, 20])   # Hedef 50m ileride, 20m yukseklikte
    
    for t in range(21):
        # Hunter saniyede hedefe dogru yaklasiyor
        progress = t / 20.0
        current_hunter_pos = hunter_start + (target_pos - hunter_start) * progress
        
        # Gercek GPS Mesafesi
        real_distance = calculate_gps_distance(current_hunter_pos, target_pos)
        
        # Yapay Poz Uretimi (Kamera acisina gore 2D pikselleri simule edelim)
        # Gercek mesafeye sahte 'model hatasi' ekleyelim: %5 rastgele yanilgi
        noise = np.random.normal(0, real_distance * 0.05)
        simulated_pnp_distance = real_distance + noise
        
        pnp_logs.append({"time": t, "distance_pnp_m": max(0, simulated_pnp_distance)})
        gps_logs.append({
            "time": t, 
            "hunter_pos": current_hunter_pos.tolist(),
            "target_pos": target_pos.tolist(),
            "distance_gps_m": real_distance
        })
        
    with open("pnp_distances.json", "w") as f:
        json.dump(pnp_logs, f, indent=4)
        
    with open("gps_distances.json", "w") as f:
        json.dump(gps_logs, f, indent=4)
        
    print("[SIMULASYON] Ucus bitti. Veriler JSON olarak loglandi.")

# ==========================================
# ASAMA 3: TERMINAL ASAMA ANALIZI & GORSELLESTIRME
# ==========================================
def analyze_and_plot():
    print("[ANALIZ] Loglar okunuyor...")
    with open("pnp_distances.json", "r") as f:
        pnp_data = json.load(f)
    with open("gps_distances.json", "r") as f:
        gps_data = json.load(f)
        
    times = [d["time"] for d in gps_data]
    gps_dist = [d["distance_gps_m"] for d in gps_data]
    pnp_dist = [d["distance_pnp_m"] for d in pnp_data]
    
    # Hata (RMSE) Hesaplama
    errors = np.array(pnp_dist) - np.array(gps_dist)
    rmse_overall = np.sqrt(np.mean(errors**2))
    
    # Terminal Asama (<10 metre) Analizi
    terminal_indices = [i for i, d in enumerate(gps_dist) if d < 10.0]
    if terminal_indices:
        terminal_errors = errors[terminal_indices]
        rmse_terminal = np.sqrt(np.mean(terminal_errors**2))
    else:
        rmse_terminal = 0.0
        
    # Cizim
    plt.figure(figsize=(10, 6))
    plt.plot(times, gps_dist, label="Gercek GPS Mesafesi", color="blue", linewidth=2)
    plt.plot(times, pnp_dist, label="PnP Kestirim Mesafesi (Pose)", color="red", linestyle="--", marker="o")
    
    # Terminal asamayi vurgulama (10 metrenin alti)
    if terminal_indices:
        start_t = times[terminal_indices[0]]
        end_t = times[terminal_indices[-1]]
        plt.axvspan(start_t, end_t, color='red', alpha=0.1, label="Terminal Asama (<10m)")
        
    plt.title("Otonom Interceptor: PnP vs GPS Angajman Mesafesi Analizi", fontsize=14, fontweight="bold")
    plt.xlabel("Zaman (saniye)")
    plt.ylabel("Mesafe (metre)")
    plt.grid(True, linestyle=":", alpha=0.7)
    
    # Koseye RMSE yazdirma
    info_text = f"Genel RMSE: {rmse_overall:.2f} m\nTerminal (<10m) RMSE: {rmse_terminal:.2f} m"
    plt.gca().text(0.02, 0.05, info_text, transform=plt.gca().transAxes, 
                   fontsize=12, bbox=dict(facecolor='white', alpha=0.8, edgecolor='black'))
    
    plt.legend()
    plt.tight_layout()
    plt.savefig("angajman_analiz_raporu.png")
    print("[ANALIZ] Grafik 'angajman_analiz_raporu.png' olarak kaydedildi.")

if __name__ == "__main__":
    # Test Senaryosu
    run_dummy_simulation()
    analyze_and_plot()

import os
import json
import math
import glob
import cv2

# Dronun gövde ayarları (Gerçek Talon dronuna uygun ölçüler)
FUSELAGE_RADIUS = 18.0   # Gövdenin yarıçapı (Çok büyük yaparsak her şeyi siler)
FUSELAGE_X_MIN = -65.0   # Gövdenin arkaya (motora) doğru uzunluğu
FUSELAGE_X_MAX = 70.0    # Gövdenin öne (buruna) doğru uzunluğu

def euler_to_matrix(pitch, yaw, roll):
    p = math.radians(pitch)
    y = math.radians(yaw)
    r = math.radians(roll)
    
    cp, sp = math.cos(p), math.sin(p)
    cy, sy = math.cos(y), math.sin(y)
    cr, sr = math.cos(r), math.sin(r)
    
    m00 = cp * cy
    m01 = cp * sy
    m02 = sp
    
    m10 = sr * sp * cy - cr * sy
    m11 = sr * sp * sy + cr * cy
    m12 = -sr * cp
    
    m20 = -(cr * sp * cy + sr * sy)
    m21 = cy * sr - cr * sp * sy
    m22 = cr * cp
    
    return [[m00, m01, m02], [m10, m11, m12], [m20, m21, m22]]

def world_to_local(point, actor_loc, actor_rot_matrix):
    dx = point['x'] - actor_loc['x']
    dy = point['y'] - actor_loc['y']
    dz = point['z'] - actor_loc['z']
    
    m = actor_rot_matrix
    lx = dx * m[0][0] + dy * m[0][1] + dz * m[0][2]
    ly = dx * m[1][0] + dy * m[1][1] + dz * m[1][2]
    lz = dx * m[2][0] + dy * m[2][1] + dz * m[2][2]
    
    return {'x': lx, 'y': ly, 'z': lz}

def is_occluded(cam_local, target_local, radius, x_min, x_max):
    Cx, Cy, Cz = cam_local['x'], cam_local['y'], cam_local['z']
    Tx, Ty, Tz = target_local['x'], target_local['y'], target_local['z']
    
    dx = Tx - Cx
    dy = Ty - Cy
    dz = Tz - Cz
    
    denominator = (dy**2 + dz**2)
    if denominator == 0:
        return False
        
    t = -(Cy * dy + Cz * dz) / denominator
    
    # Sadece hedefin "ÖNÜNDE" (kamera ile hedef arasinda) olan carpmalari kontrol et
    # 0.90 siniri: Lazer zaten hedefe varmissa, hedefin kendisini "engel" saymasini onler
    if 0.05 < t < 0.90:
        min_dist_sq = (Cy + t * dy)**2 + (Cz + t * dz)**2
        if min_dist_sq < (radius ** 2):
            # Lazer X eksenini gecti ama GÖVDENIN USTUNDEN MI GECTI? (Yoksa önünden/arkasından mi?)
            Px = Cx + t * dx
            if x_min < Px < x_max:
                return True
    return False

def main():
    json_files = glob.glob("*.json")
    if not json_files:
        print("HATA: JSON bulunamadi.")
        return
        
    out_dir = "dataset_test"
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
        
    total_cleaned = 0
    total_files = len(json_files)
    
    for i, j_file in enumerate(json_files):
        img_file = j_file.replace(".json", ".png")
        if not os.path.exists(img_file):
            continue
            
        with open(j_file, 'r') as f:
            data = json.load(f)
            
        if "camera_location" not in data or "drone_location" not in data or "keypoints_3d" not in data:
            continue
            
        c_loc = data["camera_location"]
        d_loc = data["drone_location"]
        d_rot = data["drone_rotation"]
        
        rot_matrix = euler_to_matrix(d_rot['pitch'], d_rot['yaw'], d_rot['roll'])
        cam_local = world_to_local(c_loc, d_loc, rot_matrix)
        
        silinecekler = []
        
        for kp_name, kp3d in data["keypoints_3d"].items():
            kp_local = world_to_local(kp3d, d_loc, rot_matrix)
            
            # Okluzyon kontrolu
            if is_occluded(cam_local, kp_local, FUSELAGE_RADIUS, FUSELAGE_X_MIN, FUSELAGE_X_MAX):
                silinecekler.append(kp_name)
                
        # Okluzyona dusenleri JSON verisinden SİL
        for name in silinecekler:
            if name in data.get("keypoints_2d", {}):
                del data["keypoints_2d"][name]
                total_cleaned += 1
            if name in data.get("keypoints_3d", {}):
                del data["keypoints_3d"][name]
                
        # JSON'u guncelle
        with open(j_file, 'w') as f:
            json.dump(data, f, indent=4)
            
        # Cizilmis PNG'yi uret ve dataset_test icine kaydet
        img = cv2.imread(img_file)
        if img is not None:
            for kp_name, kp_data in data.get("keypoints_2d", {}).items():
                if kp_data.get("on", False):
                    x, y = int(kp_data["x"]), int(kp_data["y"])
                    cv2.circle(img, (x, y), 6, (0, 0, 255), -1)
                    cv2.putText(img, kp_name, (x+10, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,255), 2)
            
            out_img_path = os.path.join(out_dir, img_file)
            cv2.imwrite(out_img_path, img)
            
        print(f"[{i+1}/{total_files}] islendi: {j_file} ({len(silinecekler)} nokta silindi)")
        
    print(f"\nISLEM TAMAM! Toplam {total_cleaned} okluzyon hatasi temizlendi.")
    print(f"Silinmis JSON'lar ana klasore kaydedildi.")
    print(f"Test fotograflari '{out_dir}' klasorune cikarildi.")

if __name__ == "__main__":
    main()

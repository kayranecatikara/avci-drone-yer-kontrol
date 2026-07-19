import os
import json
import math
import glob
import cv2
import numpy as np

# DRONE KAPSÜLLERİ (3 BOYUTLU TAM HACİM MODELLEMESİ)
# A ve B kapsülün başlangıç ve bitiş noktaları, r ise kalınlığı (yarıçapı).
CAPSULES = [
    # 1. ANA GÖVDE (Burundan kuyruk motoruna kadar eksiksiz)
    {
        "A": np.array([90.0, 0.0, -2.0]), 
        "B": np.array([-75.0, 0.0, 2.0]), 
        "r": 16.0,
        "name": "Gövde"
    },
    # 2. SOL KANAT
    {
        "A": np.array([5.0, 15.0, 8.0]),
        "B": np.array([5.0, 145.0, 14.0]),
        "r": 12.0,
        "name": "Sol Kanat"
    },
    # 3. SAĞ KANAT
    {
        "A": np.array([5.0, -15.0, 8.0]),
        "B": np.array([5.0, -145.0, 14.0]),
        "r": 12.0,
        "name": "Sağ Kanat"
    },
    # 4. SOL KUYRUK (V-Tail)
    {
        "A": np.array([-70.0, 5.0, 5.0]),
        "B": np.array([-70.0, 40.0, 25.0]),
        "r": 8.0,
        "name": "Sol Kuyruk"
    },
    # 5. SAĞ KUYRUK (V-Tail)
    {
        "A": np.array([-70.0, -5.0, 5.0]),
        "B": np.array([-70.0, -40.0, 25.0]),
        "r": 8.0,
        "name": "Sağ Kuyruk"
    }
]

def ue_rotmat(pitch, yaw, roll):
    """Unreal Engine FRotator to Rotation Matrix"""
    P, Y, R = math.radians(pitch), math.radians(yaw), math.radians(roll)
    CP, SP = math.cos(P), math.sin(P)
    CY, SY = math.cos(Y), math.sin(Y)
    CR, SR = math.cos(R), math.sin(R)
    return np.array([
        [ CP*CY,             CP*SY,            SP     ],
        [ SR*SP*CY - CR*SY,  SR*SP*SY + CR*CY, -SR*CP ],
        [-(CR*SP*CY+SR*SY),  CY*SR - CR*SP*SY,  CR*CP  ]
    ], dtype=np.float64)

def world_to_local(point_world, actor_loc_world, rot_mat):
    """Dünya koordinatını dronun yerel koordinatlarına çevir"""
    pw = np.array([point_world['x'], point_world['y'], point_world['z']])
    al = np.array([actor_loc_world['x'], actor_loc_world['y'], actor_loc_world['z']])
    # Unreal'de rot_mat local'i world'e cevirir. Tersini bulmak icin transpozesini (M.T) aliriz.
    pl = rot_mat.T @ (pw - al)
    return pl

def segment_segment_dist(p1, p2, p3, p4):
    """
    İki doğru parçası (segment) arasındaki EN KISA mesafeyi bulur.
    p1-p2: Kamera ışını
    p3-p4: Kapsül gövdesi
    """
    u = p2 - p1
    v = p4 - p3
    w = p1 - p3
    a = np.dot(u, u)
    b = np.dot(u, v)
    c = np.dot(v, v)
    d = np.dot(u, w)
    e = np.dot(v, w)
    D = a*c - b*b
    sD = D
    tD = D
    
    if D < 1e-8:
        sN = 0.0
        sD = 1.0
        tN = e
        tD = c
    else:
        sN = (b*e - c*d)
        tN = (a*e - b*d)
        if sN < 0.0:
            sN = 0.0
            tN = e
            tD = c
        elif sN > sD:
            sN = sD
            tN = e + b
            tD = c
            
    if tN < 0.0:
        tN = 0.0
        if -d < 0.0:
            sN = 0.0
        elif -d > a:
            sN = sD
        else:
            sN = -d
            sD = a
    elif tN > tD:
        tN = tD
        if (-d + b) < 0.0:
            sN = 0.0
        elif (-d + b) > a:
            sN = sD
        else:
            sN = (-d + b)
            sD = a
            
    sc = 0.0 if abs(sN) < 1e-8 else sN / sD
    tc = 0.0 if abs(tN) < 1e-8 else tN / tD
    
    dP = w + (sc * u) - (tc * v)
    return np.linalg.norm(dP), sc, tc

def is_occluded_by_any_capsule(cam_local, target_local):
    """Işın, kameradan (cam_local) çıkıp hedefe (target_local) giderken herhangi bir kapsüle çarpıyor mu?"""
    # Işının yönünde hedef noktası 1.0, kamera 0.0 kabul edilir.
    for cap in CAPSULES:
        dist, sc, tc = segment_segment_dist(cam_local, target_local, cap["A"], cap["B"])
        # Eger isin kapsule yariçapindan daha fazla yaklasirsa VE
        # Bu yaklaşma noktanın "kendisi" degilse (yani hedefin %95'inden daha oncesiyse)
        if dist <= cap["r"] and (0.02 < sc < 0.92):
            return True
    return False

def main():
    print("--- Milimetrik Işın İzleme (Ray-Tracing) Oklüzyon Sistemi Başlatıldı ---")
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
        
        rot_matrix = ue_rotmat(d_rot['pitch'], d_rot['yaw'], d_rot['roll'])
        cam_local = world_to_local(c_loc, d_loc, rot_matrix)
        
        silinecekler = []
        
        for kp_name, kp3d in data["keypoints_3d"].items():
            kp_local = world_to_local(kp3d, d_loc, rot_matrix)
            
            if is_occluded_by_any_capsule(cam_local, kp_local):
                silinecekler.append(kp_name)
                
        for name in silinecekler:
            if name in data.get("keypoints_2d", {}):
                del data["keypoints_2d"][name]
                total_cleaned += 1
            if name in data.get("keypoints_3d", {}):
                del data["keypoints_3d"][name]
                
        # JSON'u guncelle
        with open(j_file, 'w') as f:
            json.dump(data, f, indent=4)
            
        # EGER AYNI ISIMDE TXT (YOLO) DOSYASI VARSA ONU DA GUNCELLE!
        txt_file = j_file.replace(".json", ".txt")
        if os.path.exists(txt_file) and len(silinecekler) > 0:
            with open(txt_file, 'r') as tf:
                lines = tf.readlines()
            
            if lines:
                parts = lines[0].strip().split()
                # YOLO format: class cx cy w h kp1x kp1y kp1v ...
                keypoints_order = ["nose", "left_wingtip", "right_wingtip", "tail", "left_tail_fin", "right_tail_fin"]
                
                for name in silinecekler:
                    name_lower = name.lower()
                    if name_lower in keypoints_order:
                        idx = keypoints_order.index(name_lower)
                        base_idx = 5 + (idx * 3)
                        # Parcalar (parts) icinde o noktanin indeksleri varsa sifirla
                        if base_idx + 2 < len(parts):
                            parts[base_idx] = "0.000000"
                            parts[base_idx+1] = "0.000000"
                            parts[base_idx+2] = "0"
                            
                # Guncellenmis metni tekrar TXT dosyasina yaz
                with open(txt_file, 'w') as tf:
                    tf.write(" ".join(parts) + "\n")
            
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
            
        # Konsol Ciktisini Kullaniciya Net Goster
        if os.path.exists(txt_file):
            print(f"[{i+1}/{total_files}] ISLENDI: {j_file} VE {os.path.basename(txt_file)} ({len(silinecekler)} kör nokta silindi)")
        else:
            print(f"[{i+1}/{total_files}] ISLENDI: {j_file} ({len(silinecekler)} kör nokta silindi)")
        
    print(f"\nISLEM TAMAM! Toplam {total_cleaned} okluzyon hatasi temizlendi.")
    print(f"Test fotograflari '{out_dir}' klasorune cikarildi.")

if __name__ == "__main__":
    main()

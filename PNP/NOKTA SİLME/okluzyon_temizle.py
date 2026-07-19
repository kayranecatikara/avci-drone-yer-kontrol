import os
import json
import math
import glob

# Dronun gövde yariçapi (Santimetre cinsinden). 
# Eger dron daha kalinsa bunu arttirabilirsin.
FUSELAGE_RADIUS = 25.0 

def euler_to_matrix(pitch, yaw, roll):
    # Unreal Engine acilarini (Derece) radyana cevirip rotasyon matrisi uretir
    p = math.radians(pitch)
    y = math.radians(yaw)
    r = math.radians(roll)
    
    cp, sp = math.cos(p), math.sin(p)
    cy, sy = math.cos(y), math.sin(y)
    cr, sr = math.cos(r), math.sin(r)
    
    # Unreal Engine'in XYZ (Roll, Pitch, Yaw) donusum matrisi
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
    # Dunya koordinatindaki bir noktayi dronun yerel (local) koordinatina cevirir
    dx = point['x'] - actor_loc['x']
    dy = point['y'] - actor_loc['y']
    dz = point['z'] - actor_loc['z']
    
    # Matrisin tersi ile carpim (Transpoze)
    m = actor_rot_matrix
    lx = dx * m[0][0] + dy * m[0][1] + dz * m[0][2]
    ly = dx * m[1][0] + dy * m[1][1] + dz * m[1][2]
    lz = dx * m[2][0] + dy * m[2][1] + dz * m[2][2]
    
    return {'x': lx, 'y': ly, 'z': lz}

def is_occluded(cam_local, target_local, radius):
    # Işın (Ray) - Silindir (Cylinder) Kesişimi
    # Dronun gövdesini X ekseni boyunca uzanan bir silindir olarak varsayiyoruz.
    # Kameradan (cam) hedefe (target) cizilen isin bu silindiri delip geciyor mu?
    
    Cy, Cz = cam_local['y'], cam_local['z']
    Ty, Tz = target_local['y'], target_local['z']
    
    dy = Ty - Cy
    dz = Tz - Cz
    
    # Işının gövdeye en yaklastigi ani (t) buluyoruz
    denominator = (dy**2 + dz**2)
    if denominator == 0:
        return False
        
    t = -(Cy * dy + Cz * dz) / denominator
    
    # Eger t 0 ile 1 arasindaysa, engelleme dron ile kamera arasindadir
    if 0 < t < 1:
        # O andaki isin noktasinin gövde merkezine (X eksenine) olan uzakligi
        min_dist_sq = (Cy + t * dy)**2 + (Cz + t * dz)**2
        if min_dist_sq < (radius ** 2):
            return True # VURDU! Gövdenin arkasinda kalmis!
            
    return False

def process_jsons():
    json_files = glob.glob("*.json")
    print(f"Toplam {len(json_files)} JSON dosyasi islenecek...")
    
    temizlenen_nokta_sayisi = 0
    
    for file in json_files:
        with open(file, 'r') as f:
            data = json.load(f)
            
        if "camera_location" not in data or "drone_location" not in data or "keypoints_3d" not in data:
            continue
            
        c_loc = data["camera_location"]
        d_loc = data["drone_location"]
        d_rot = data["drone_rotation"]
        
        rot_matrix = euler_to_matrix(d_rot['pitch'], d_rot['yaw'], d_rot['roll'])
        cam_local = world_to_local(c_loc, d_loc, rot_matrix)
        
        silinecekler = []
        
        # Sadece 3D koordinati bilinen kanat/kuyruk uc noktalarini kontrol et
        for kp_name, kp3d in data["keypoints_3d"].items():
            # Burun ve motor genelde govdeden engellenmez, onlari haric tutalim
            if "Burun" in kp_name or "Nose" in kp_name or "Motor" in kp_name:
                continue
                
            kp_local = world_to_local(kp3d, d_loc, rot_matrix)
            
            # Eger nokta engelleniyorsa silinecekler listesine ekle
            if is_occluded(cam_local, kp_local, FUSELAGE_RADIUS):
                silinecekler.append(kp_name)
                
        # Tespit edilen noktalari hem 2D hem 3D listesinden sil!
        for name in silinecekler:
            if name in data.get("keypoints_2d", {}):
                del data["keypoints_2d"][name]
                temizlenen_nokta_sayisi += 1
            if name in data.get("keypoints_3d", {}):
                del data["keypoints_3d"][name]
                
        # JSON'u ustune yazarak kaydet
        with open(file, 'w') as f:
            json.dump(data, f, indent=4)
            
    print(f"ISLEM TAMAM! Toplam {temizlenen_nokta_sayisi} adet gorunmeyen/arkada kalan nokta (okluzyon) silindi.")

if __name__ == "__main__":
    process_jsons()
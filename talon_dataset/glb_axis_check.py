"""
GLB eksen duzeni analizi.
Talon'un kanat uclari Y'de mi Z'de mi?
Buna gore GLB->UE eksen mapping'ini cikartiyoruz.

Bildigimiz gercekler (UE world space, Lua dump'tan):
- Sol kanat ucu world loc: talon_0182.json'dan okuyacagiz
- Drone loc: talon_0182.json'dan okuyacagiz
- Drone rot: talon_0182.json'dan okuyacagiz

GLB local space'te max Z = sol kanat ucu mu? Yoksa max Y mi?
"""

import struct, json, math
import numpy as np

GLB_DIR = r"C:\Users\Zeylo\Desktop\FModel\Output\Exports\DronesOfWar\Content\Art\Meshes\Talon\V2"
DATASET_DIR = r"c:\Users\Zeylo\Desktop\talon_dataset\dataset"

def read_glb_vertices(path):
    with open(path, 'rb') as f:
        f.read(4); f.read(4); f.read(4)
        json_len = struct.unpack('<I', f.read(4))[0]
        f.read(4)
        json_data = json.loads(f.read(json_len).decode('utf-8'))
        bin_len = struct.unpack('<I', f.read(4))[0]
        f.read(4)
        bin_data = f.read(bin_len)
    vertices = []
    for mesh in json_data.get('meshes', []):
        for prim in mesh.get('primitives', []):
            pos_idx = prim.get('attributes', {}).get('POSITION')
            if pos_idx is None: continue
            acc = json_data['accessors'][pos_idx]
            bv = json_data['bufferViews'][acc['bufferView']]
            offset = bv.get('byteOffset', 0) + acc.get('byteOffset', 0)
            count = acc['count']
            stride = bv.get('byteStride', 12)
            for i in range(count):
                start = offset + i * stride
                x, y, z = struct.unpack_from('<fff', bin_data, start)
                vertices.append([x, y, z])
    return np.array(vertices, dtype=np.float32)

import os

# Tum mesh'leri birlestir
all_verts = []
files = ["SM_Talon_Body.glb","SM_Talon_Wing_L.glb","SM_Talon_Wing_R.glb",
         "SM_Talon_Small_Wing_L.glb","SM_Talon_Small_Wing_R.glb"]
for f in files:
    v = read_glb_vertices(os.path.join(GLB_DIR, f))
    all_verts.append(v)
mesh = np.concatenate(all_verts, axis=0)

print("="*60)
print("GLB MESH EKSEN ANALIZI")
print("="*60)
print(f"\nTum GLB boyutlari (metre cinsinden):")
print(f"  X: {mesh[:,0].min():.3f} -> {mesh[:,0].max():.3f}  ARALIK: {mesh[:,0].max()-mesh[:,0].min():.3f} m")
print(f"  Y: {mesh[:,1].min():.3f} -> {mesh[:,1].max():.3f}  ARALIK: {mesh[:,1].max()-mesh[:,1].min():.3f} m")
print(f"  Z: {mesh[:,2].min():.3f} -> {mesh[:,2].max():.3f}  ARALIK: {mesh[:,2].max()-mesh[:,2].min():.3f} m")

print(f"\nTalon gercek olculeri (bilinen):")
print(f"  Uzunluk (burun-kuyruk): ~1.10 m")
print(f"  Kanat acikligi: ~1.78 m")

print(f"\nGLB eksen tahminleri:")
ax_x = mesh[:,0].max()-mesh[:,0].min()
ax_y = mesh[:,1].max()-mesh[:,1].min()
ax_z = mesh[:,2].max()-mesh[:,2].min()
print(f"  X ekseni: {ax_x:.3f} m  -> {'UZUNLUK (Ileri)' if abs(ax_x-1.1)<0.15 else 'KANAT ACIKLIGI' if abs(ax_x-1.78)<0.2 else '?'}")
print(f"  Y ekseni: {ax_y:.3f} m  -> {'UZUNLUK (Ileri)' if abs(ax_y-1.1)<0.15 else 'KANAT ACIKLIGI' if abs(ax_y-1.78)<0.2 else '?'}")
print(f"  Z ekseni: {ax_z:.3f} m  -> {'UZUNLUK (Ileri)' if abs(ax_z-1.1)<0.15 else 'KANAT ACIKLIGI' if abs(ax_z-1.78)<0.2 else '?'}")

# JSON'dan gercek dunyayi kontrol edelim
with open(os.path.join(DATASET_DIR, "talon_0182.json"), 'r') as f:
    data = json.load(f)

drone_loc = data["drone_location"]
drone_rot = data["drone_rotation"]
kps3d = data["keypoints_3d"]

print(f"\n\nJSON keypoints_3d - Drone'a gore OFFSET (UE world cm):")
for name, kp in kps3d.items():
    dx = kp["x"] - drone_loc["x"]
    dy = kp["y"] - drone_loc["y"]
    dz = kp["z"] - drone_loc["z"]
    dist = math.sqrt(dx*dx+dy*dy+dz*dz)
    print(f"  {name:20s}: dx={dx:7.2f}, dy={dy:7.2f}, dz={dz:7.2f}  |dist={dist:.2f} cm")

print(f"\nTalon kanat acikligi 178 cm. Sol kanat offset mesafesi ~89 cm olmali.")
print(f"\nGLB -> UE eksen mapping tahmini:")
print(f"  GLB X (ileri ekseni, {ax_x:.2f}m) = UE X (ileri)")
print(f"  GLB Y (kisa eksen, {ax_y:.2f}m) = UE yukseklik (Z)")
print(f"  GLB Z (kanat acikligi, {ax_z:.2f}m) = UE Y (sag/sol)")

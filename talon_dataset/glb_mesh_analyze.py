"""
GLB Mesh Analiz Scripti
-----------------------
SM_Talon_Body.glb dosyasini okuyup:
1. Bounding box hesaplar (min/max x, y, z)
2. Burun = en on ucundaki vertex (max X)
3. Kuyruk = en arka ucundaki vertex (min X)
4. Sol kanat ucu = en soldaki vertex (max Y)
5. Sag kanat ucu = en sagdaki vertex (min Y)
6. Sol kuyruk kanat = Small Wing L'in merkezi
7. Sag kuyruk kanat = Small Wing R'in merkezi

Hepsi mesh'in LOCAL SPACE'inde (actor local, cm cinsi)
Rotation'dan tamamen bagimsiz, kesin degerler.
"""

import struct, json
import numpy as np

GLB_DIR = r"C:\Users\Zeylo\Desktop\FModel\Output\Exports\DronesOfWar\Content\Art\Meshes\Talon\V2"

def read_glb_vertices(path):
    with open(path, 'rb') as f:
        f.read(4)   # magic
        f.read(4)   # version
        f.read(4)   # length

        json_len  = struct.unpack('<I', f.read(4))[0]
        f.read(4)   # chunk type
        json_data = json.loads(f.read(json_len).decode('utf-8'))

        bin_len  = struct.unpack('<I', f.read(4))[0]
        f.read(4)   # chunk type
        bin_data = f.read(bin_len)

    vertices = []
    for mesh in json_data.get('meshes', []):
        for prim in mesh.get('primitives', []):
            pos_idx = prim.get('attributes', {}).get('POSITION')
            if pos_idx is None:
                continue
            acc    = json_data['accessors'][pos_idx]
            bv     = json_data['bufferViews'][acc['bufferView']]
            offset = bv.get('byteOffset', 0) + acc.get('byteOffset', 0)
            count  = acc['count']
            stride = bv.get('byteStride', 12)
            for i in range(count):
                start = offset + i * stride
                x, y, z = struct.unpack_from('<fff', bin_data, start)
                vertices.append([x, y, z])
    return np.array(vertices, dtype=np.float32)

def analyze(name, path):
    v = read_glb_vertices(path)
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"  Toplam vertex: {len(v)}")
    print(f"{'='*60}")
    print(f"  Bounding Box:")
    print(f"    X: {v[:,0].min():.2f}  -->  {v[:,0].max():.2f}   (aralik: {v[:,0].max()-v[:,0].min():.2f})")
    print(f"    Y: {v[:,1].min():.2f}  -->  {v[:,1].max():.2f}   (aralik: {v[:,1].max()-v[:,1].min():.2f})")
    print(f"    Z: {v[:,2].min():.2f}  -->  {v[:,2].max():.2f}   (aralik: {v[:,2].max()-v[:,2].min():.2f})")
    
    cx = (v[:,0].min() + v[:,0].max()) / 2
    cy = (v[:,1].min() + v[:,1].max()) / 2
    cz = (v[:,2].min() + v[:,2].max()) / 2
    print(f"\n  Geometrik Merkez: X={cx:.2f}, Y={cy:.2f}, Z={cz:.2f}")
    
    # Ekstremum noktalari
    nose_v    = v[v[:,0].argmax()]   # En on (max X = burun)
    tail_v    = v[v[:,0].argmin()]   # En arka (min X = kuyruk)
    lwing_v   = v[v[:,1].argmax()]   # En sol (max Y = sol kanat)
    rwing_v   = v[v[:,1].argmin()]   # En sag (min Y = sag kanat)
    top_v     = v[v[:,2].argmax()]   # En ust (max Z)
    bot_v     = v[v[:,2].argmin()]   # En alt (min Z)

    print(f"\n  Ekstremum Vertexler (LOCAL SPACE, mesh koordinati):")
    print(f"    BURUN  (max X): X={nose_v[0]:8.2f}, Y={nose_v[1]:8.2f}, Z={nose_v[2]:8.2f}")
    print(f"    KUYRUK (min X): X={tail_v[0]:8.2f}, Y={tail_v[1]:8.2f}, Z={tail_v[2]:8.2f}")
    print(f"    SOL    (max Y): X={lwing_v[0]:8.2f}, Y={lwing_v[1]:8.2f}, Z={lwing_v[2]:8.2f}")
    print(f"    SAG    (min Y): X={rwing_v[0]:8.2f}, Y={rwing_v[1]:8.2f}, Z={rwing_v[2]:8.2f}")
    print(f"    UST    (max Z): X={top_v[0]:8.2f}, Y={top_v[1]:8.2f}, Z={top_v[2]:8.2f}")
    print(f"    ALT    (min Z): X={bot_v[0]:8.2f}, Y={bot_v[1]:8.2f}, Z={bot_v[2]:8.2f}")
    
    return v, cx, cy, cz

import os

files = {
    "SM_Talon_Body":         "SM_Talon_Body.glb",
    "SM_Talon_Wing_L":       "SM_Talon_Wing_L.glb",
    "SM_Talon_Wing_R":       "SM_Talon_Wing_R.glb",
    "SM_Talon_Small_Wing_L": "SM_Talon_Small_Wing_L.glb",
    "SM_Talon_Small_Wing_R": "SM_Talon_Small_Wing_R.glb",
}

all_verts = []
for name, fname in files.items():
    path = os.path.join(GLB_DIR, fname)
    v, cx, cy, cz = analyze(name, path)
    all_verts.append(v)

# Tum mesh'leri birlestir (pivot ofseti yok, hepsi local space)
all_v = np.concatenate(all_verts, axis=0)
print(f"\n{'='*60}")
print("  TUM MESH BIRLESMIS - GENEL ANALIZ")
print(f"{'='*60}")
print(f"  Toplam vertex: {len(all_v)}")
print(f"  GLOBAL Bounding Box:")
print(f"    X: {all_v[:,0].min():.2f}  -->  {all_v[:,0].max():.2f}   (aralik: {all_v[:,0].max()-all_v[:,0].min():.2f})")
print(f"    Y: {all_v[:,1].min():.2f}  -->  {all_v[:,1].max():.2f}   (aralik: {all_v[:,1].max()-all_v[:,1].min():.2f})")
print(f"    Z: {all_v[:,2].min():.2f}  -->  {all_v[:,2].max():.2f}   (aralik: {all_v[:,2].max()-all_v[:,2].min():.2f})")

gcx = (all_v[:,0].min() + all_v[:,0].max()) / 2
gcy = (all_v[:,1].min() + all_v[:,1].max()) / 2
gcz = (all_v[:,2].min() + all_v[:,2].max()) / 2
print(f"\n  GLOBAL Geometrik Merkez: X={gcx:.2f}, Y={gcy:.2f}, Z={gcz:.2f}")

nose_v    = all_v[all_v[:,0].argmax()]
tail_v    = all_v[all_v[:,0].argmin()]
lwing_v   = all_v[all_v[:,1].argmax()]
rwing_v   = all_v[all_v[:,1].argmin()]

print(f"\n  6 KEYPOINT ADAYLARI (TUM MESH, LOCAL SPACE):")
print(f"    BURUN  (max X): X={nose_v[0]:8.2f}, Y={nose_v[1]:8.2f}, Z={nose_v[2]:8.2f}")
print(f"    KUYRUK (min X): X={tail_v[0]:8.2f}, Y={tail_v[1]:8.2f}, Z={tail_v[2]:8.2f}")
print(f"    SOL KANAT (max Y): X={lwing_v[0]:8.2f}, Y={lwing_v[1]:8.2f}, Z={lwing_v[2]:8.2f}")
print(f"    SAG KANAT (min Y): X={rwing_v[0]:8.2f}, Y={rwing_v[1]:8.2f}, Z={rwing_v[2]:8.2f}")

# Kucuk kanat merkez hesabi
sw_l = np.concatenate([read_glb_vertices(os.path.join(GLB_DIR, "SM_Talon_Small_Wing_L.glb"))], axis=0)
sw_r = np.concatenate([read_glb_vertices(os.path.join(GLB_DIR, "SM_Talon_Small_Wing_R.glb"))], axis=0)
swl_center = sw_l.mean(axis=0)
swr_center = sw_r.mean(axis=0)
print(f"    SOL KUYRUK KANAT merkez: X={swl_center[0]:8.2f}, Y={swl_center[1]:8.2f}, Z={swl_center[2]:8.2f}")
print(f"    SAG KUYRUK KANAT merkez: X={swr_center[0]:8.2f}, Y={swr_center[1]:8.2f}, Z={swr_center[2]:8.2f}")

print(f"\n[BITTI] Bu degerler mesh'in local space koordinatlari.")
print(f"Bunlari dogrudan Lua/Python keypoint offsetleri olarak kullanabiliriz.")
print(f"Pivot ofsetinden tamamen bagimsizdir.")

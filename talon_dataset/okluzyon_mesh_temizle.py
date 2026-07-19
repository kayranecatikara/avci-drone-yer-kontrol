# -*- coding: utf-8 -*-
# ============================================================================
#  okluzyon_mesh_temizle.py
#  ------------------------------------------------------------------------
#  Her kare (JSON) icin, Talon'un GERCEK 3D mesh'ini (Body + kanatlar + kuyruk
#  fin'leri) kullanarak, kameradan gorunmeyen (okluzyona dusen) keypoint'leri
#  tespit eder ve o kareden (keypoints_2d + keypoints_3d) SILER.
#
#  Occlusion tamamen 3B geometridir: kameranin KONUMU + drone pozu + mesh yeter;
#  FOV ve kamera-rotasyonu GEREKMEZ. (JSON'daki camera_fov=125 zaten sahtedir;
#  gercek render FOV'u ~90.79 olculdu ama occlusion icin onemsizdir.)
#
#  Keypoint'lerin actor-local konumlari projection_math.RAW_CAD'den alinir
#  (keypoints_2d bu degerlerden uretilir). JSON'daki keypoints_3d BAYAT oldugu
#  icin (ozellikle fin'lerde ~50cm sapma) occlusion'da KULLANILMAZ.
#
#  KULLANIM:
#     python okluzyon_mesh_temizle.py            -> DRY-RUN (sadece rapor, silmez)
#     python okluzyon_mesh_temizle.py --apply    -> YEDEK alir sonra SILER
# ============================================================================
import os, sys, json, glob, math, shutil
import numpy as np
import trimesh

# ---- yollar ----
DATASET = r"C:\Users\Zeylo\Desktop\talon_dataset\dataset"
MESHDIR = r"C:\Users\Zeylo\Desktop\FModel\Output\Exports\DronesOfWar\Content\Art\Meshes\Talon\V2"
BACKUP  = r"C:\Users\Zeylo\Desktop\talon_dataset\okluzyon_yedek_json"

# ---- occluder parcalari (UE V2) ----
MESH_PARTS = ["SM_Talon_Body.glb",
              "SM_Talon_Wing_L.glb", "SM_Talon_Wing_R.glb",
              "SM_Talon_Small_Wing_L.glb", "SM_Talon_Small_Wing_R.glb"]  # small = kuyruk fin'leri

# ---- keypoint actor-local koordinatlari (UE cm) = projection_math.RAW_CAD ----
RAW_CAD = {
    "Nose":           (69.13, 0.19, -2.77),
    "Left_Wingtip":   (1.65, -99.93, 5.81),
    "Right_Wingtip":  (1.65,  99.93, 5.81),
    "Tail":           (-55.38, 0.10, 0.10),
    "Left_Tail_Fin":  (-43.17, -28.25, 16.98),
    "Right_Tail_Fin": (-43.17,  28.25, 16.98),
}
KP_ORDER = list(RAW_CAD.keys())

# ---- occlusion ray parametreleri ----
EPS = 0.6      # cm: isini keypoint yuzeyinden kameraya dogru bu kadar iteleriz (self-hit onleme)
MARGIN = 2.5   # cm: engel, kameraya olan mesafeden en az bu kadar yakinsa okluzyon sayilir

def get_unreal_matrix(pitch, yaw, roll):
    """Unreal FRotationMatrix (projection_math ile birebir). local->world."""
    SP, CP = math.sin(math.radians(pitch)), math.cos(math.radians(pitch))
    SY, CY = math.sin(math.radians(yaw)),   math.cos(math.radians(yaw))
    SR, CR = math.sin(math.radians(roll)),  math.cos(math.radians(roll))
    return np.array([
        [CP*CY, SR*SP*CY-CR*SY, -(CR*SP*CY+SR*SY)],
        [CP*SY, SR*SP*SY+CR*CY,  CY*SR-CR*SP*SY],
        [SP,   -SR*CP,           CR*CP]])

def load_concat(path):
    m = trimesh.load(path, force='scene')
    parts = []
    for node in m.graph.nodes_geometry:
        T, gname = m.graph[node]
        g = m.geometry[gname].copy(); g.apply_transform(T); parts.append(g)
    return trimesh.util.concatenate(parts)

def to_ue(mesh):
    """glb (metre, glTF ekseni) -> UE actor-local cm.  UE_X=glbX, UE_Y=glbZ, UE_Z=glbY."""
    v = np.asarray(mesh.vertices) * 100.0
    v = v[:, [0, 2, 1]]
    return trimesh.Trimesh(vertices=v, faces=np.asarray(mesh.faces), process=False)

def build_occluder():
    ms = [to_ue(load_concat(os.path.join(MESHDIR, p))) for p in MESH_PARTS]
    return trimesh.util.concatenate(ms)

def compute_occlusions(files, occ):
    """Her kare icin okluzyona dusen keypoint isimlerini dondurur: {file: [names]}."""
    origins, dirs, Ls, meta = [], [], [], []
    for fi, fp in enumerate(files):
        d = DATA[fp]
        if d is None: continue
        if not all(x in d for x in ("drone_location", "drone_rotation", "camera_location")):
            continue
        R = get_unreal_matrix(d["drone_rotation"]["pitch"], d["drone_rotation"]["yaw"], d["drone_rotation"]["roll"])
        dl = np.array([d["drone_location"][a] for a in "xyz"])
        cw = np.array([d["camera_location"][a] for a in "xyz"])
        cam_local = R.T @ (cw - dl)
        present = set((d.get("keypoints_2d") or {}).keys()) | set((d.get("keypoints_3d") or {}).keys())
        for k in KP_ORDER:
            if k not in present:
                continue
            P = np.array(RAW_CAD[k])
            dvec = cam_local - P
            L = np.linalg.norm(dvec)
            if L < 1e-6: continue
            dirn = dvec / L
            origins.append(P + dirn * EPS); dirs.append(dirn); Ls.append(L); meta.append((fp, k))
    origins = np.array(origins); dirs = np.array(dirs); Ls = np.array(Ls)
    print(f"  {len(origins)} isin (ray) atiliyor...")
    locs, idx_ray, idx_tri = occ.ray.intersects_location(origins, dirs, multiple_hits=False)
    hit_dist = np.full(len(origins), np.inf)
    if len(idx_ray):
        dh = np.linalg.norm(locs - origins[idx_ray], axis=1)
        for r, dd in zip(idx_ray, dh):
            if dd < hit_dist[r]: hit_dist[r] = dd
    occ_flags = hit_dist < (Ls - EPS - MARGIN)
    result = {}
    for (fp, k), f in zip(meta, occ_flags):
        if f: result.setdefault(fp, []).append(k)
    return result

# ---------------------------------------------------------------------------
if __name__ == "__main__":
    APPLY = ("--apply" in sys.argv)
    print("=== TALON OKLUZYON TEMIZLEME (gercek mesh) ===")
    print("MOD:", "APPLY (silecek)" if APPLY else "DRY-RUN (sadece rapor)")

    files = sorted(glob.glob(os.path.join(DATASET, "*.json")))
    print(f"JSON dosyasi: {len(files)}")

    DATA = {}
    for fp in files:
        try:
            DATA[fp] = json.load(open(fp, encoding="utf-8"))
        except Exception:
            DATA[fp] = None
    bad = sum(1 for v in DATA.values() if v is None)
    if bad: print(f"UYARI: {bad} dosya okunamadi/bozuk (atlandi).")

    print("Mesh yukleniyor...")
    occ = build_occluder()
    print(f"Occluder: {len(occ.vertices)} vertex, {len(occ.faces)} yuz.  Ray motoru: {type(occ.ray).__module__}")

    occ_map = compute_occlusions(files, occ)

    from collections import Counter
    per_kp = Counter()
    for fp, ks in occ_map.items():
        for k in ks: per_kp[k] += 1
    total = sum(len(v) for v in occ_map.values())
    print("\n--------- OKLUZYON RAPORU ---------")
    print(f"En az 1 okluzyonlu kare : {len(occ_map)} / {len(files)}")
    print(f"Toplam okluzyon noktasi : {total}")
    for k in KP_ORDER:
        print(f"   {k:16s} {per_kp.get(k,0)}")

    if not APPLY:
        print("\n[DRY-RUN] Hicbir sey silinmedi. Silmek icin:  python okluzyon_mesh_temizle.py --apply")
        sys.exit(0)

    # ---- YEDEK (yalnizca yoksa) ----
    if not os.path.exists(BACKUP):
        os.makedirs(BACKUP)
        for fp in files:
            shutil.copy2(fp, os.path.join(BACKUP, os.path.basename(fp)))
        print(f"\nYEDEK olusturuldu: {BACKUP}  ({len(files)} JSON)")
    else:
        print(f"\nYEDEK zaten var (atlandi): {BACKUP}")

    # ---- SILME ----
    silinen = 0
    degisen_kare = 0
    for fp, names in occ_map.items():
        d = DATA[fp]
        changed = False
        for name in names:
            if name in (d.get("keypoints_2d") or {}):
                del d["keypoints_2d"][name]; silinen += 1; changed = True
            if name in (d.get("keypoints_3d") or {}):
                del d["keypoints_3d"][name]
        if changed:
            with open(fp, "w", encoding="utf-8") as f:
                json.dump(d, f, indent=4)
            degisen_kare += 1

    print(f"\nTAMAM. {degisen_kare} karede toplam {silinen} okluzyon noktasi silindi.")
    print(f"Geri almak icin: {BACKUP} icindeki JSON'lari dataset klasorune geri kopyala.")

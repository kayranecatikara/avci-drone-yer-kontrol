# -*- coding: utf-8 -*-
# ============================================================================
#  fix_dataset_and_test.py   (GUNCEL SURUM - GERCEK 3D MESH ile okluzyon)
#  ------------------------------------------------------------------------
#  ESKI SURUMDEKI SORUNLAR (bu yuzden yanlis nokta siliniyordu):
#    1) world_to_local donusumu TERSTI: rot_mat = ue_rotmat aslinda dogru
#       matrisin transpozesiydi, uzerine bir daha .T alininca net sonuc
#       "G @ v" oluyordu; oysa dunya->yerel icin "G^T @ v" gerekir. Yani
#       kamera ve keypoint'lerin yerel koordinatlari hatali hesaplaniyordu.
#    2) Drone elle tahmini KAPSULLERLE modellenmisti (govde/kanat/kuyruk
#       olculeri gercek mesh'le uyusmuyordu; kanatlar ince tup sayiliyordu).
#
#  BU SURUM:
#    * Talon'un GERCEK 3D mesh'ini (Body + kanatlar + kuyruk fin'leri)
#      occluder olarak kullanir. Kameradan her keypoint'e ISIN atar (embree)
#      ve govdeye/kanada/fin'e carpiyorsa o nokta GORUNMUYOR demektir. Kapsul
#      yaklasimi degil, birebir geometri.
#    * Dogru Unreal donusum matrisi (projection_math.get_unreal_matrix ile ayni).
#    * Keypoint yerel konumlari RAW_CAD'den alinir (keypoints_2d'yi ureten
#      "kutsal" CAD olculeri). JSON icindeki keypoints_3d BAYAT oldugu icin
#      (ozellikle fin'lerde ~50cm sapma) occlusion'da KULLANILMAZ.
#
#  Occlusion tamamen 3B gorunurluktur: kameranin KONUMU + drone POZU + mesh
#  yeter. FOV / kamera-yonelimi GEREKMEZ; camera_fov=125 degerine dokunulmaz.
#
#  YAPTIGI:  okluzyona dusen keypoint'i  keypoints_2d + keypoints_3d + (varsa)
#            YOLO .txt  icinden siler; kontrol icin dataset_test/ altina cizilmis
#            PNG uretir.
#
#  GEREKSINIM:  pip install trimesh embreex rtree     (+ Talon GLB mesh'leri)
#  KULLANIM  :  dataset klasorunde ->  python fix_dataset_and_test.py
# ============================================================================
import os
import sys
import json
import math
import glob
import cv2
import numpy as np

try:
    import trimesh
except ImportError:
    print("HATA: 'trimesh' yok.  Kur:  pip install trimesh embreex rtree")
    sys.exit(1)

# ------------------------------- AYARLAR ------------------------------------
# Talon mesh parcalarinin bulundugu klasor (FModel export'u):
MESHDIR = r"C:\Users\Zeylo\Desktop\FModel\Output\Exports\DronesOfWar\Content\Art\Meshes\Talon\V2"
MESH_PARTS = [
    "SM_Talon_Body.glb",
    "SM_Talon_Wing_L.glb", "SM_Talon_Wing_R.glb",
    "SM_Talon_Small_Wing_L.glb", "SM_Talon_Small_Wing_R.glb",   # small_wing = kuyruk fin'leri
]

OUT_DIR   = "dataset_test"   # cizilmis kontrol goruntuleri buraya
DRAW_TEST = True             # False yaparsan PNG uretmez -> COK daha hizli

EPS    = 0.6    # cm: isini keypoint yuzeyinden kameraya dogru itele (self-hit onleme)
MARGIN = 2.5    # cm: engel, kameraya olan mesafeden en az bu kadar yakinsa okluzyon say

# Keypoint'lerin actor-local (UE cm) konumlari = projection_math.RAW_CAD
RAW_CAD = {
    "Nose":           (69.13, 0.19, -2.77),
    "Left_Wingtip":   (1.65, -99.93, 5.81),
    "Right_Wingtip":  (1.65,  99.93, 5.81),
    "Tail":           (-55.38, 0.10, 0.10),
    "Left_Tail_Fin":  (-43.17, -28.25, 16.98),
    "Right_Tail_Fin": (-43.17,  28.25, 16.98),
}
# YOLO .txt icindeki keypoint sirasi (class cx cy w h  kp1x kp1y kp1v  kp2x ...)
YOLO_ORDER = ["nose", "left_wingtip", "right_wingtip", "tail", "left_tail_fin", "right_tail_fin"]

# ------------------------------ GEOMETRI ------------------------------------
def get_unreal_matrix(pitch, yaw, roll):
    """Unreal FRotationMatrix (local -> world). projection_math ile BIREBIR.
    Sutunlar = eksen vektorleri: [Forward(X) | Right(Y) | Up(Z)]."""
    SP, CP = math.sin(math.radians(pitch)), math.cos(math.radians(pitch))
    SY, CY = math.sin(math.radians(yaw)),   math.cos(math.radians(yaw))
    SR, CR = math.sin(math.radians(roll)),  math.cos(math.radians(roll))
    return np.array([
        [CP*CY, SR*SP*CY - CR*SY, -(CR*SP*CY + SR*SY)],
        [CP*SY, SR*SP*SY + CR*CY,  CY*SR - CR*SP*SY],
        [SP,   -SR*CP,             CR*CP],
    ], dtype=np.float64)

def load_concat(path):
    """GLB'yi (sahne olabilir) tek Trimesh olarak yukle, dugum donusumleriyle."""
    scn = trimesh.load(path, force='scene')
    parts = []
    for node in scn.graph.nodes_geometry:
        T, gname = scn.graph[node]
        g = scn.geometry[gname].copy()
        g.apply_transform(T)
        parts.append(g)
    return trimesh.util.concatenate(parts)

def to_ue(mesh):
    """glTF (metre, sag-el) -> UE actor-local (cm, sol-el).
    Eksen esleme: UE_X = glbX,  UE_Y = glbZ,  UE_Z = glbY."""
    v = np.asarray(mesh.vertices) * 100.0
    v = v[:, [0, 2, 1]]
    return trimesh.Trimesh(vertices=v, faces=np.asarray(mesh.faces), process=False)

def build_occluder():
    if not os.path.isdir(MESHDIR):
        print(f"HATA: Mesh klasoru yok:\n  {MESHDIR}\n(MESHDIR sabitini duzelt.)")
        sys.exit(1)
    ms = []
    for p in MESH_PARTS:
        fp = os.path.join(MESHDIR, p)
        if not os.path.exists(fp):
            print(f"HATA: Mesh parcasi yok: {fp}")
            sys.exit(1)
        ms.append(to_ue(load_concat(fp)))
    return trimesh.util.concatenate(ms)

def occluded_names(data, occ):
    """Bu karede okluzyona dusen (kameradan gorunmeyen) keypoint isimleri."""
    d_loc, d_rot, c_loc = data["drone_location"], data["drone_rotation"], data["camera_location"]
    R = get_unreal_matrix(d_rot["pitch"], d_rot["yaw"], d_rot["roll"])   # local->world
    dl = np.array([d_loc["x"], d_loc["y"], d_loc["z"]])
    cw = np.array([c_loc["x"], c_loc["y"], c_loc["z"]])
    cam_local = R.T @ (cw - dl)          # DOGRU dunya->yerel (G^T @ v)

    present = set((data.get("keypoints_2d") or {}).keys()) | set((data.get("keypoints_3d") or {}).keys())

    origins, dirs, Ls, names = [], [], [], []
    for name, cad in RAW_CAD.items():
        if name not in present:          # sadece bu karede VAR OLAN noktalari test et
            continue
        P = np.array(cad)                # keypoint zaten yerel (RAW_CAD)
        dvec = cam_local - P
        L = np.linalg.norm(dvec)
        if L < 1e-6:
            continue
        dirn = dvec / L
        origins.append(P + dirn * EPS)   # isini yuzeyden biraz iteleyerek baslat
        dirs.append(dirn); Ls.append(L); names.append(name)

    if not origins:
        return []
    O = np.array(origins); D = np.array(dirs)
    locs, idx_ray, idx_tri = occ.ray.intersects_location(O, D, multiple_hits=False)
    nearest = {}
    if len(idx_ray):
        dh = np.linalg.norm(locs - O[idx_ray], axis=1)
        for r, dd in zip(idx_ray, dh):
            if r not in nearest or dd < nearest[r]:
                nearest[r] = dd
    out = []
    for i, name in enumerate(names):
        if i in nearest and nearest[i] < (Ls[i] - EPS - MARGIN):
            out.append(name)             # engel, keypoint'ten once geliyor -> gorunmuyor
    return out

# ------------------------------- ANA AKIS -----------------------------------
def main():
    print("--- GERCEK MESH ISIN-IZLEME (RAY-TRACING) OKLUZYON SISTEMI ---")
    json_files = sorted(glob.glob("*.json"))
    if not json_files:
        print("HATA: Bu klasorde JSON yok. Scripti 'dataset' klasorunde calistir.")
        return

    print("Mesh yukleniyor...")
    occ = build_occluder()
    print(f"Occluder: {len(occ.vertices)} vertex, {len(occ.faces)} yuz.  Ray motoru: {type(occ.ray).__module__}")

    if DRAW_TEST and not os.path.exists(OUT_DIR):
        os.makedirs(OUT_DIR)

    total_cleaned = 0
    affected = 0
    total = len(json_files)
    for i, j_file in enumerate(json_files):
        try:
            with open(j_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        if not all(k in data for k in ("camera_location", "drone_location", "drone_rotation")):
            continue

        silinecekler = occluded_names(data, occ)

        for name in silinecekler:
            if name in data.get("keypoints_2d", {}):
                del data["keypoints_2d"][name]; total_cleaned += 1
            if name in data.get("keypoints_3d", {}):
                del data["keypoints_3d"][name]
        if silinecekler:
            affected += 1

        with open(j_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

        # Ayni isimde YOLO .txt varsa: silinen keypoint slotunu sifirla
        txt_file = j_file.replace(".json", ".txt")
        if silinecekler and os.path.exists(txt_file):
            with open(txt_file, "r") as tf:
                lines = tf.readlines()
            if lines:
                parts = lines[0].strip().split()
                for name in silinecekler:
                    nl = name.lower()
                    if nl in YOLO_ORDER:
                        b = 5 + YOLO_ORDER.index(nl) * 3   # class(1)+bbox(4) sonrasi
                        if b + 2 < len(parts):
                            parts[b], parts[b+1], parts[b+2] = "0.000000", "0.000000", "0"
                with open(txt_file, "w") as tf:
                    tf.write(" ".join(parts) + "\n")

        # Kontrol goruntusu: kalan (gorunur) noktalari ciz
        if DRAW_TEST:
            img_file = j_file.replace(".json", ".png")
            img = cv2.imread(img_file) if os.path.exists(img_file) else None
            if img is not None:
                for kp_name, kp in data.get("keypoints_2d", {}).items():
                    if "x" in kp:
                        x, y = int(kp["x"]), int(kp["y"])
                        cv2.circle(img, (x, y), 6, (0, 0, 255), -1)
                        cv2.putText(img, kp_name, (x+10, y-10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
                cv2.imwrite(os.path.join(OUT_DIR, os.path.basename(img_file)), img)

        if (i + 1) % 200 == 0 or len(silinecekler) > 0:
            print(f"[{i+1}/{total}] {j_file}  ({len(silinecekler)} kor nokta silindi)")

    print(f"\nISLEM TAMAM! {affected} karede toplam {total_cleaned} okluzyon noktasi temizlendi.")
    if DRAW_TEST:
        print(f"Kontrol goruntuleri: {OUT_DIR}/")

if __name__ == "__main__":
    main()

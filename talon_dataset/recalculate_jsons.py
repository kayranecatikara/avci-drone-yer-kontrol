# -*- coding: utf-8 -*-
# ============================================================================
#  recalculate_jsons.py  -  Mevcut dataset JSON'larindaki keypoints_2d'yi
#  TEK DOGRU matematik (projection_math.py) ile yeniden hesaplar.
# ----------------------------------------------------------------------------
#  ONEMLI / DURUSTLUK UYARISI:
#    Bu script her karenin JSON'undaki KAYITLI camera_fov degerini kullanir.
#    Eski kareler (Lua'daki GetFOVAngle duzeltmesinden ONCE cekilenler) sabit
#    125 / 90 / 131.54 gibi YANLIS FOV ile kaydedilmistir. O kareler icin bu
#    script dogru keypoint URETEMEZ -- cunku gercek render FOV'u kayitli degil.
#    Dogru sonuc icin o kareleri YENIDEN CEKMEK ya da keypoint_editor.py ile
#    elle duzeltmek gerekir. Bu script sadece, camera_fov'u GERCEK olan
#    (yeni boru hattiyla cekilmis) kareleri dogru sekilde yeniden uretir.
#
#    * manually_edited = True olan kareler GROUND-TRUTH'tur; ASLA ezilmez.
#    * SCALE=1.0, RAW_CAD, dogru UE matrisi -> hepsi projection_math.py'den.
# ============================================================================

import os
import sys
import json
import shutil
import projection_math as pm

dataset_dir = r"C:\Users\Zeylo\Desktop\FİNİSH\jsonlar"
backup_dir = r"C:\Users\Zeylo\Desktop\FİNİSH\jsonlar_backup"

# Eski boru hattinin URETTIGI SAHTE/sabit FOV degerleri. Bir karenin camera_fov'u
# bunlardan biriyse, o kare GetFOVAngle duzeltmesinden ONCE cekilmistir; gercek
# render FOV'u kayitli DEGILDIR ve yeniden hesap o kareyi BOZAR. Bu yuzden
# varsayilan olarak ATLANIR. Yine de zorlamak istersen:  python recalculate_jsons.py --force
LEGACY_FAKE_FOVS = {125.0, 90.0, 131.54}
FORCE = ("--force" in sys.argv)

if not os.path.exists(dataset_dir):
    print(f"Dataset folder not found at: {dataset_dir}")
    raise SystemExit(0)

# Yedek (yalnizca yoksa olusturulur)
if not os.path.exists(backup_dir):
    shutil.copytree(dataset_dir, backup_dir)
    print(f"Backup created at: {backup_dir}")
else:
    print(f"Backup already exists (skipped): {backup_dir}")

count = 0
skipped_manual = 0
skipped_nofov = 0
skipped_legacy = 0

for filename in os.listdir(dataset_dir):
    if not filename.endswith(".json"):
        continue
    filepath = os.path.join(dataset_dir, filename)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        continue

    # 1) Elle duzeltilmis kareler -> dokunma (ground-truth).
    if data.get("manually_edited"):
        skipped_manual += 1
        continue

    drone_loc = data.get("drone_location")
    drone_rot = data.get("drone_rotation")
    cam_loc = data.get("camera_location")
    cam_rot = data.get("camera_rotation")
    cam_fov = data.get("camera_fov")

    if not (drone_loc and drone_rot and cam_loc and cam_rot and cam_fov and cam_fov > 0):
        skipped_nofov += 1
        continue

    # 2) SAHTE/sabit FOV korumasi: gercek render FOV'u olmayan eski kareleri bozma.
    if (round(float(cam_fov), 2) in LEGACY_FAKE_FOVS) and not FORCE:
        skipped_legacy += 1
        continue

    data["keypoints_2d"] = pm.calculate_keypoints_2d(drone_loc, drone_rot, cam_loc, cam_rot, cam_fov)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    count += 1

print(f"\nYeniden hesaplanan      : {count}")
print(f"Atlanan (manuel)        : {skipped_manual}   (ground-truth korundu)")
print(f"Atlanan (FOV yok)       : {skipped_nofov}")
print(f"Atlanan (sahte/sabit FOV): {skipped_legacy}   (125/90/131.54 -> --force ile zorlanir)")
if skipped_legacy and not FORCE:
    print("\n[KORUMA] Bu karelerin FOV'u sahte/sabit. Yeniden hesap onlari BOZARDI, atlandi.")
    print("         Dogru cozum: bu kareleri YENI boru hattiyla yeniden cek (gercek FOV ile).")

# -*- coding: utf-8 -*-
# ============================================================================
#  draw_keypoints_engine.py  -  MOTOR SENKRON keypoint cizimi
# ----------------------------------------------------------------------------
#  RAW_CAD_DATA / carpan / elle offset YOK. Iki yol:
#
#   1) BIRINCIL (onerilen): Lua modu her keypoint'i motorun kendi
#      ProjectWorldLocationToScreen'i ile 2D'ye cevirip JSON'a "keypoints_2d"
#      olarak yaziyor. Burada sadece onlari (viewport -> resim olcegiyle)
#      cizeriz. HICBIR projeksiyon matematigi yok -> render ile birebir.
#
#   2) YEDEK / DOGRULAMA: keypoints_3d (motordan gelen GERCEK dunya
#      koordinatlari) + o karenin GERCEK FOV'u ile pinhole projeksiyon.
#      Ayni sonucu vermeli; sapma varsa cozunurluk/FOV ayarini yakalar.
# ============================================================================

import os
import json
import math
from PIL import Image, ImageDraw

KEYPOINT_COLORS = {
    "nose":           (30, 100, 250),   # Mavi
    "left_wingtip":   (255, 30, 30),    # Kirmizi
    "right_wingtip":  (255, 100, 200),  # Pembe
    "tail":           (255, 120, 0),    # Turuncu
    "left_tail_fin":  (255, 215, 0),    # Sari
    "right_tail_fin": (0, 200, 80),     # Yesil
}

SKELETON_EDGES = [
    ("nose", "left_wingtip"), ("nose", "right_wingtip"),
    ("left_wingtip", "tail"), ("right_wingtip", "tail"),
    ("tail", "left_tail_fin"), ("tail", "right_tail_fin"),
]


# ---------------------------------------------------------------------------
#  YEDEK PROJEKSIYON (senin istedigin project_world_to_screen, DUZELTILMIS)
#  Farklar (eski koddaki hatalarin cozumu):
#    * cam_fov ARTIK sabit 125 degil -> her karenin GERCEK FOV'u disaridan gelir
#    * width/height sabit 1920x1080 degil -> resmin GERCEK boyutu gelir
#    * kamera-arkasi (cam_fwd <= 0) elenir -> nokta kosede patlamaz
#    * UE FRotationMatrix birebir (roll dahil)
# ---------------------------------------------------------------------------
def _unreal_basis(pitch, yaw, roll):
    """UE FRotationMatrix eksen vektorleri: forward(X), right(Y), up(Z)."""
    SP, CP = math.sin(math.radians(pitch)), math.cos(math.radians(pitch))
    SY, CY = math.sin(math.radians(yaw)),   math.cos(math.radians(yaw))
    SR, CR = math.sin(math.radians(roll)),  math.cos(math.radians(roll))
    fwd   = (CP * CY,                 CP * SY,                 SP)
    right = (SR * SP * CY - CR * SY,  SR * SP * SY + CR * CY,  -SR * CP)
    up    = (-(CR * SP * CY + SR * SY), CY * SR - CR * SP * SY,  CR * CP)
    return fwd, right, up


def project_world_to_screen(world_pt, cam_loc, cam_rot, fov_deg, width, height):
    """UE5 pinhole. world_pt=(x,y,z) UE cm. Donus: (u, v) piksel ya da None (arka)."""
    dx = world_pt[0] - cam_loc["x"]
    dy = world_pt[1] - cam_loc["y"]
    dz = world_pt[2] - cam_loc["z"]

    fwd, right, up = _unreal_basis(cam_rot["pitch"], cam_rot["yaw"], cam_rot["roll"])
    cam_fwd   = dx * fwd[0]   + dy * fwd[1]   + dz * fwd[2]     # derinlik
    cam_right = dx * right[0] + dy * right[1] + dz * right[2]   # saga
    cam_up    = dx * up[0]    + dy * up[1]    + dz * up[2]      # yukari

    if cam_fwd <= 1e-4:
        return None  # kameranin arkasinda/tam yaninda

    # UE varsayilani: yatay FOV korunur, kare piksel (fx = fy).
    focal = (width / 2.0) / math.tan(math.radians(fov_deg) / 2.0)
    u = (width / 2.0) + (cam_right / cam_fwd) * focal
    v = (height / 2.0) - (cam_up / cam_fwd) * focal
    return u, v


# ---------------------------------------------------------------------------
#  Bir JSON + resim ciftinden 2D noktalari cikar.
#  Once motorun keypoints_2d'sini dene; yoksa keypoints_3d'yi projelendir.
# ---------------------------------------------------------------------------
def resolve_points(data, img_w, img_h):
    pts = {}
    # image_size varsa keypoint'ler ZATEN resim uzayinda (capture_controller olcekledi)
    # -> tekrar olcekleme (sx=1). Yoksa (Lua status.txt) viewport ile olcekle.
    vp = data.get("image_size") or data.get("viewport") or {}
    vp_w = float(vp.get("w") or 0) or img_w
    vp_h = float(vp.get("h") or 0) or img_h
    sx = img_w / vp_w
    sy = img_h / vp_h

    kp2d = data.get("keypoints_2d")
    if kp2d:
        for name, p in kp2d.items():
            if p and p.get("on") and p.get("x", -1) >= 0:
                pts[name] = (p["x"] * sx, p["y"] * sy)
        if pts:
            return pts, "engine2d"

    # --- yedek: 3D'den projelendir ---
    kp3d = data.get("keypoints_3d")
    cam_loc = data.get("camera_location")
    cam_rot = data.get("camera_rotation")
    fov = data.get("camera_fov")
    if kp3d and cam_loc and cam_rot and fov:
        for name, w in kp3d.items():
            if abs(w["x"]) + abs(w["y"]) + abs(w["z"]) < 1e-6:
                continue  # doldurulmamis (0,0,0)
            uv = project_world_to_screen((w["x"], w["y"], w["z"]), cam_loc, cam_rot, fov, img_w, img_h)
            if uv:
                pts[name] = uv
        return pts, "world3d"

    return pts, "none"


def draw_on_image(img, pts, bbox=None, dot_radius=5, line_width=2):
    d = ImageDraw.Draw(img)
    W, H = img.size
    # Bounding box (object detection kutusu)
    if bbox and all(k in bbox for k in ("x0", "y0", "x1", "y1")):
        d.rectangle([bbox["x0"], bbox["y0"], bbox["x1"], bbox["y1"]],
                    outline=(0, 255, 255), width=2)
    on = {k: (int(round(x)), int(round(y))) for k, (x, y) in pts.items()
          if -50 <= x <= W + 50 and -50 <= y <= H + 50}
    for a, b in SKELETON_EDGES:
        if a in on and b in on:
            d.line([on[a], on[b]], fill=(200, 200, 200), width=line_width)
    for name, (px, py) in on.items():
        c = KEYPOINT_COLORS.get(name, (255, 255, 255))
        d.ellipse([px - dot_radius, py - dot_radius, px + dot_radius, py + dot_radius],
                  fill=c, outline=(255, 255, 255), width=2)
    return on


def main():
    ws = r"c:\Users\Zeylo\Desktop\talon_dataset"
    src = os.path.join(ws, "dataset")
    out = os.path.join(ws, "dataset_annotated")
    os.makedirs(out, exist_ok=True)

    files = sorted(f for f in os.listdir(src) if f.lower().endswith(".png"))
    if not files:
        print("[UYARI] dataset/ icinde PNG yok.")
        return

    ok, modes = 0, {"engine2d": 0, "world3d": 0, "none": 0}
    for fn in files:
        base = os.path.splitext(fn)[0]
        jp = os.path.join(src, base + ".json")
        if not os.path.exists(jp):
            continue
        try:
            with open(jp, "r", encoding="utf-8") as f:
                data = json.load(f)
            img = Image.open(os.path.join(src, fn)).convert("RGB")
        except Exception as e:
            print(f"[ATLA] {fn}: {e}")
            continue

        pts, mode = resolve_points(data, img.width, img.height)
        modes[mode] = modes.get(mode, 0) + 1
        draw_on_image(img, pts, data.get("bbox"))
        img.save(os.path.join(out, fn))
        ok += 1

    print(f"[BITTI] {ok} resim islendi. Mod dagilimi: {modes}")
    print(f"        Cikti: {out}")


if __name__ == "__main__":
    main()

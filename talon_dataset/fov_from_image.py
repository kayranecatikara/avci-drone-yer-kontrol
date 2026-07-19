import math, argparse

# ============================================================================
# GORUNTUDEN FOV KALIBRASYONU
# Bilinen genislikteki bir nesneyi (Talon kanat acikligi = 1.718 m) bilinen
# mesafede, kameranin TAM KARSISINDA (optik eksene dik, ortada) cek.
# Goruntudeki piksel acikligini olc, FOV'u geri hesapla.
#
# Pinhole: p = (w * W) / (2 * D * tan(HFOV/2))  ->  HFOV = 2*atan( w*W / (2*D*p) )
#   w = nesne gercek genisligi (m)   D = mesafe (m)
#   p = nesnenin ekrandaki piksel genisligi   W = goruntu genisligi (px)
# ============================================================================

def hfov_deg(object_width_m, distance_m, pixel_span, image_width_px=1920):
    return math.degrees(2*math.atan((object_width_m*image_width_px)/(2*distance_m*pixel_span)))

def vfov_deg(hfov, width=1920, height=1080):
    return math.degrees(2*math.atan(math.tan(math.radians(hfov)/2)*height/width))

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--width_m", type=float, default=1.718, help="nesne gercek genisligi (m), Talon kanat=1.718")
    ap.add_argument("--dist_m",  type=float, required=True, help="kamera-nesne mesafesi (m)")
    ap.add_argument("--span_px", type=float, required=True, help="nesnenin ekrandaki piksel genisligi")
    ap.add_argument("--img_w",   type=float, default=1920)
    ap.add_argument("--img_h",   type=float, default=1080)
    a = ap.parse_args()
    h = hfov_deg(a.width_m, a.dist_m, a.span_px, a.img_w)
    v = vfov_deg(h, a.img_w, a.img_h)
    print(f"Yatay FOV (HFOV) = {h:.3f} derece")
    print(f"Dikey FOV (VFOV) = {v:.3f} derece  (16:9 varsayimiyla)")

# --- self-test: debug kamera verisiyle dogrulama (123.262 cikmali) ---
def _selftest():
    # talon_0000: ~5m head-on, kanat ekranda 173.9 px
    h = hfov_deg(1.718, 5.0, 173.9, 1920)
    print(f"[self-test] beklenen ~123.3 -> hesap = {h:.3f} derece")
_selftest()

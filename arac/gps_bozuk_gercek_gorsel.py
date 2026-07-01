# -*- coding: utf-8 -*-
"""
gps_bozuk_gercek.json'i 3B gorsellestirir: hedef IHA'nin sadece BOZUK (ham GNSS) ve
GERCEK konum yorungesi (filtreli YOK).
Kullanim:
  python gps_bozuk_gercek_gorsel.py           -> gps_bozuk_gercek_3d.png kaydeder
  python gps_bozuk_gercek_gorsel.py --show    -> donebilen interaktif pencere de acar
"""
import json
import os
import sys
import math

import matplotlib
if "--show" not in sys.argv:
    matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERI = os.path.join(ROOT, "veri")               # calisma ciktilari (json/png)
with open(os.path.join(VERI, "gps_bozuk_gercek.json"), "r", encoding="utf-8") as f:
    kay = json.load(f)["kayitlar"]
if not kay:
    print("kayit BOS"); raise SystemExit


def xyz(key):
    xs, ys, zs = [], [], []
    for k in kay:
        v = k.get(key)
        if v is not None:
            xs.append(v[0]); ys.append(v[1]); zs.append(v[2])
    return xs, ys, zs


bx, by, bz = xyz("bozuk")
gx, gy, gz = xyz("gercek")

# Ham GNSS'in gercege ortalama 3B hatasi
def d3(a, b):
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))
he = [d3(k["bozuk"], k["gercek"]) for k in kay if k.get("bozuk") and k.get("gercek")]
ham_ort = sum(he) / len(he) if he else 0.0
print("ornek: %d | ham (bozuk) ort. hata: %.1f m" % (len(kay), ham_ort))

fig = plt.figure(figsize=(12, 9))
ax = fig.add_subplot(111, projection="3d")
ax.plot(bx, by, bz, color="#ff4d4d", lw=1.1, alpha=0.6, label="Bozuk GNSS (ham)  ~%.0f m hata" % ham_ort)
ax.scatter(bx, by, bz, color="#ff4d4d", s=9, alpha=0.35)
ax.plot(gx, gy, gz, color="#2ecc71", lw=2.8, label="Gercek konum")
if gx:
    ax.scatter([gx[0]], [gy[0]], [gz[0]], color="white", edgecolor="black", s=95, label="Baslangic")
    ax.scatter([gx[-1]], [gy[-1]], [gz[-1]], color="black", marker="X", s=95, label="Bitis")

ax.set_xlabel("X (m)")
ax.set_ylabel("Y (m)")
ax.set_zlabel("Z / irtifa (m)")
ax.set_title("Hedef IHA GPS  -  Bozuk (ham GNSS) vs Gercek konum\n"
             "%d ornek, %.0f sn   |   ham GNSS ortalama %.0f m sapma"
             % (len(kay), kay[-1]["t"], ham_ort))
ax.legend(loc="upper left")
ax.view_init(elev=22, azim=-60)
plt.tight_layout()
out = os.path.join(VERI, "gps_bozuk_gercek_3d.png")
plt.savefig(out, dpi=130)
print("kaydedildi:", out)

if "--show" in sys.argv:
    plt.show()

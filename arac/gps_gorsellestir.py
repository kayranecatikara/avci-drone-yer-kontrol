# -*- coding: utf-8 -*-
"""
gps_kayit.json'i 3B gorsellestirir: hedef IHA'nin BOZUK / GERCEK / TEMIZLENMIS yorungesi.

'temizlenmis' = Inovasyonlu J'nin LEAD'SIZ (guncel) kestirimi. JSON'daki bozuk seri
uzerinde OFFLINE yeniden hesaplanir (filtre sabit dt -> deterministik). Boylece saf
"gurultu temizleme" gorunur; JSON'daki 'filtreli' alani ise 2sn-lead'li guduum
ciktisidir (donen hedefte tasar, gorsellestirme icin lead'siz daha temiz).

Kullanim:
  python gps_gorsellestir.py           -> gps_3d.png kaydeder
  python gps_gorsellestir.py --show    -> ayrica donebilen interaktif pencere acar
"""
import json
import os
import sys
import math

import matplotlib
if "--show" not in sys.argv:
    matplotlib.use("Agg")                       # penceresiz: sadece PNG
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

# arac/ alt klasorunden depo kokunu path'e ekle -> fusion paketi bulunur
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from fusion.inovasyonlu_j_v2 import GNSSDuzeltici

VERI = os.path.join(ROOT, "veri")               # calisma ciktilari (json/png)
with open(os.path.join(VERI, "gps_kayit.json"), "r", encoding="utf-8") as f:
    kay = json.load(f)["kayitlar"]
if not kay:
    print("kayit BOS - once ucus yap."); raise SystemExit

# --- J'yi bozuk seri uzerinde LEAD'SIZ yeniden calistir (metre -> cm -> metre) ---
filt = GNSSDuzeltici()
B, G, F = [], [], []                            # hizali: bozuk, gercek, temizlenmis(lead'siz)
for k in kay:
    b, g = k.get("bozuk"), k.get("gercek")
    if b is None:
        continue
    lead = filt.guncelle(b[0] * 100.0, b[1] * 100.0, b[2] * 100.0)   # 2sn-lead (cm) veya None
    du = filt.durum_guduum()                                         # lead'siz kestirim (cm) veya None
    B.append(b)
    G.append(g)
    # GUDUMDE KULLANILAN kestirim: yatay 2sn-lead (3sn gecikmeyi telafi) + dikey lead'siz (stabil irtifa)
    if lead is not None and du is not None:
        F.append([lead[0] / 100.0, lead[1] / 100.0, du["pos"][2] / 100.0])
    else:
        F.append(None)


def xyz(seq):
    return ([p[0] for p in seq if p], [p[1] for p in seq if p], [p[2] for p in seq if p])


bx, by, bz = xyz(B)
gx, gy, gz = xyz(G)
fx, fy, fz = xyz(F)


def d3(a, b):
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


he = [d3(B[i], G[i]) for i in range(len(B)) if G[i]]
fe = [d3(F[i], G[i]) for i in range(len(F)) if F[i] and G[i]]
ham_ort = sum(he) / len(he) if he else 0.0
j_ort = sum(fe) / len(fe) if fe else 0.0
kazanc = 100.0 * (ham_ort - j_ort) / ham_ort if ham_ort else 0.0
print("ornek: %d | ham hata: %.1f m | J(lead'siz) hata: %.1f m | kazanc: %%%.0f"
      % (len(kay), ham_ort, j_ort, kazanc))

fig = plt.figure(figsize=(12, 9))
ax = fig.add_subplot(111, projection="3d")
ax.plot(bx, by, bz, color="#ff4d4d", lw=1.0, alpha=0.5, label="Bozuk GNSS (ham)  ~%.0f m" % ham_ort)
ax.scatter(bx, by, bz, color="#ff4d4d", s=7, alpha=0.25)
ax.plot(gx, gy, gz, color="#2ecc71", lw=2.6, label="Gercek konum")
ax.plot(fx, fy, fz, color="#3aa0ff", lw=1.9, label="Inovasyonlu J (guduumde kullanilan)  ~%.0f m" % j_ort)
if gx:
    ax.scatter([gx[0]], [gy[0]], [gz[0]], color="white", edgecolor="black", s=90, label="Baslangic")
    ax.scatter([gx[-1]], [gy[-1]], [gz[-1]], color="black", marker="X", s=90, label="Bitis")
ax.set_xlabel("X (m)")
ax.set_ylabel("Y (m)")
ax.set_zlabel("Z / irtifa (m)")
ax.set_title("Hedef IHA GPS  -  Bozuk vs Gercek vs Inovasyonlu J (guduumde kullanilan)\n"
             "%d ornek, %.0f sn   |   hata %.0f m -> %.0f m  (%%%.0f azalma; 3sn gecikme lead ile telafi)"
             % (len(kay), kay[-1]["t"], ham_ort, j_ort, kazanc))
ax.legend(loc="upper left")
ax.view_init(elev=22, azim=-60)
plt.tight_layout()
out = os.path.join(VERI, "gps_3d.png")
plt.savefig(out, dpi=130)
print("kaydedildi:", out)

if "--show" in sys.argv:
    plt.show()

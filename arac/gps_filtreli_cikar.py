# -*- coding: utf-8 -*-
"""
gps_kayit.json'dan 'filtreli' alanini cikarir; sadece zaman + bozuk + gercek yazar.
Cikti: gps_bozuk_gercek.json  (orijinal gps_kayit.json'a DOKUNMAZ).
Kullanim: python gps_filtreli_cikar.py
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERI = os.path.join(ROOT, "veri")               # calisma ciktilari (json)
src = os.path.join(VERI, "gps_kayit.json")
dst = os.path.join(VERI, "gps_bozuk_gercek.json")

with open(src, "r", encoding="utf-8") as f:
    d = json.load(f)

temiz = []
for k in d.get("kayitlar", []):
    temiz.append({
        "t": k.get("t"),
        "bozuk": k.get("bozuk"),      # ham GNSS
        "gercek": k.get("gercek"),    # gercek konum
    })

out = {
    "birim": d.get("birim", "metre"),
    "eksenler": d.get("eksenler", ["x", "y", "z"]),
    "aciklama": "hedef IHA GPS - bozuk: ham GNSS, gercek: gercek konum (filtreli alani cikarildi)",
    "ornek_sayisi": len(temiz),
    "kayitlar": temiz,
}

with open(dst, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

print("yazildi:", dst)
print("kayit sayisi:", len(temiz))
if temiz:
    print("ilk kayit:", temiz[0])
    print("son kayit:", temiz[-1])
# kontrol: filtreli gercekten yok mu
print("filtreli iceren kayit:", sum(1 for k in temiz if "filtreli" in k))

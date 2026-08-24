# -*- coding: utf-8 -*-
"""
KARAR URET  --  sablon + ucus_3b.json  ->  tek dosyalik HTML

    python arac/ucus_3b_disaktar.py      # once veriyi tazele
    python arac/karar_uret.py            # sonra sayfayi uret

Cikti: veri/ucus_karar.html   (disariya hicbir istek yapmaz, tek dosya)
"""
import os
import json

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SABLON = os.path.join(KOK, "arac", "karar_sablon.html")
VERI = os.path.join(KOK, "veri", "ucus_3b.json")
CIKTI = os.path.join(KOK, "veri", "ucus_karar.html")

with open(SABLON, encoding="utf-8") as f:
    s = f.read()
with open(VERI, encoding="utf-8") as f:
    d = json.load(f)

# </script> gomulu JSON icinde gecerse sayfa boluner -- kacir
gomulu = json.dumps(d, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
if "__VERI__" not in s:
    raise SystemExit("sablonda __VERI__ yer tutucusu yok")
s = s.replace("__VERI__", gomulu)

with open(CIKTI, "w", encoding="utf-8") as f:
    f.write(s)

n = sum(len(x["kare"]) for x in d["segmentler"])
print("  %s" % d["kaynak"])
print("  %d segment, %d kare, %d alan" % (len(d["segmentler"]), n, len(d["alanlar"])))
print("  -> %s  (%.0f KB)" % (CIKTI, os.path.getsize(CIKTI) / 1024.0))

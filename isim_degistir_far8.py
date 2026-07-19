# -*- coding: utf-8 -*-
r"""
talon_XXXX.png / talon_XXXX.text  ->  far9_XXXX.png / far9_XXXX.text
===================================================================
Sadece dosya adinin BASINDAKI "talon" kismi "far9" olur; numara ve
uzanti (_0000.png / _0000.text) birebir AYNEN kalir. Ciftler bozulmaz.
"talon_" ile baslamayan dosyalara dokunulmaz.

Kullanim:
    python isim_degistir_far8.py  "C:\Users\Zeylo\Desktop\DATA YÜKLEME\BBOX\48\48"   -> scriptin durdugu klasorde
    python isim_degistir_far8.py "C:\Users\Zeylo\Desktop\DATA YÜKLEME\BBOX\48\48"  -> istenen klasorde

NOT: Bu aciklama ham metin (r ile baslayan docstring) oldugu icin icine
ters-bolulu yol yapistirmak script'i bozmaz.
"""

import sys
from pathlib import Path

# Klasor: arguman verildiyse o, verilmediyse scriptin kendi klasoru
klasor = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent

degisen = 0
atlanan = 0
for dosya in sorted(klasor.iterdir()):
    # Sadece dosyalar ve sadece "talon_" ile baslayanlar
    if not dosya.is_file() or not dosya.name.startswith("talon_"):
        continue

    # Bastaki "talon" -> "far10"; adin geri kalani (numara + uzanti) aynen korunur
    yeni_ad = "far10_" + dosya.name[len("talon_"):]
    hedef = dosya.with_name(yeni_ad)

    # Guvenlik: ayni isimde dosya varsa ustune yazma, atla ve haber ver
    if hedef.exists():
        print(f"[ATLA] {yeni_ad} zaten var, dokunulmadi: {dosya.name}")
        atlanan += 1
        continue

    dosya.rename(hedef)
    degisen += 1

print(f"Bitti: {degisen} dosya yeniden adlandirildi (talon_ -> far10_)"
      + (f", {atlanan} dosya atlandi" if atlanan else ""))


# -*- coding: utf-8 -*-
"""MISSION COMPLETE ekranindan cikisi GOREREK bul -- kor tahmin YOK.

NEDEN: 2026-08-17'de otomatik acilis 3 tur denedi ve basaramadi. Ekran
goruntusu alinca sebep gorundu: oyun "MISSION COMPLETE" ekranindaydi,
kayitli dizi ise BASLIK ekranindan basliyor.

Bu betik her girdiden SONRA ekran goruntusu alir ve piksel farkiyla
"ekran degisti mi" diye bakar. Degisirse durur. Boylece hangi tusun
ise yaradigi TAHMIN degil OLCUM olur.

⚠ ALT / F4 / Win / Ctrl ASLA gonderilmez (oyunu kapatabilir).
⚠ Pencere one gelmezse HICBIR tus gonderilmez (yanlis pencereye
   tus gitmesi daha once yasandi).
"""
import os
import sys
import time

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)

from arac import oyun_kurtar as OK      # noqa: E402

TMP = os.environ.get("EKRAN_TMP",
                     r"C:\Users\Zeylo\.claude\jobs\9d604bde\tmp")

# Guvenli adaylar: menu onaylama/kapatma icin makul, hicbiri yikici degil.
ADAYLAR = ["SPACE", "RETURN", "ESCAPE", "E"]


def _imza(yol):
    """Kaba gorsel imza: PNG boyutu + orta seritten ornekler."""
    try:
        with open(yol, "rb") as f:
            b = f.read()
    except OSError:
        return None
    return (len(b), b[len(b) // 3:len(b) // 3 + 64])


def main():
    h = OK.oyun_penceresi()
    if not h:
        print("oyun penceresi YOK -> once oyunu baslat")
        return 2
    if not OK.one_al(h):
        print("pencere ONE GELMEDI -> tus gonderilmiyor (guvenlik)")
        return 3

    onc_yol = os.path.join(TMP, "kesfet_00.png")
    OK.ekran_goruntusu(onc_yol)
    onc = _imza(onc_yol)
    print("baslangic imzasi: %s" % (onc[0] if onc else "?"))

    for i, tus in enumerate(ADAYLAR, 1):
        if not OK.one_al(h):
            print("  pencere odagi kayboldu -> DUR")
            return 3
        print("  -> %s gonderiliyor" % tus)
        OK.tus_bas(tus)
        time.sleep(2.5)
        yol = os.path.join(TMP, "kesfet_%02d.png" % i)
        OK.ekran_goruntusu(yol)
        yeni = _imza(yol)
        if OK.port_acik():
            print("  ★ PORT ACILDI -- '%s' ise yaradi (gorevdeyiz)" % tus)
            return 0
        if yeni and onc and abs(yeni[0] - onc[0]) > max(4000, onc[0] * 0.02):
            print("  ekran DEGISTI ('%s') -> %s" % (tus, yol))
            onc = yeni
        else:
            print("  degisiklik yok ('%s')" % tus)
    print("hicbir aday portu acmadi -- ekran goruntuleri: %s" % TMP)
    return 1


if __name__ == "__main__":
    sys.exit(main())

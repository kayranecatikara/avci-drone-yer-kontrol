# -*- coding: utf-8 -*-
"""
KILIT ESIGI TOLERANS KURALI (sartname paket-gonderme siniri) — regresyon testi.
=============================================================================
Sartname metni (birebir):
  "Takimlar goruntu isleme algoritmalarini gelistirirken paket gonderme icin
   kabul ettikleri sinirin tam %5 olmasi TAVSIYE EDILMEZ. Algoritmalar belli bir
   toleransta calismaktadir; ornegin video goruntusunun aslinda %4,5'ini kaplayan
   bir objeyi, gelistirilen algoritma kilitlenme olarak degerlendirip sunucuya
   paket gonderebilir. Bu durum hakem incelemesinde HATALI KILITLENME PAKETI
   olarak degerlendirilir. Buna karsi daha toleransli bir algoritma gelistirilmesi,
   paket gonderme limitinin %6 VEYA DAHA USTU olmasi TAVSIYE EDILIR."

Bu testler algoritmamizin bu tavsiyeye UYDUGUNU kalici olarak dogrular:
  - Esik >= %6 (tam %5'te calismiyoruz -> hatali paket riski yok).
  - Kuralin ornegi %4,5'lik obje KILIT SAYILMAZ.
  - Tam %5 (sartname ham siniri) da KILIT SAYILMAZ (marj birakilir).
  - %6 ve ustu KILIT SAYILIR (float sinir dahil).
  - Boyut = max(w/W, h/H): tek eksen esigi asarsa yeter (sartname yorumu).

Not: kilit AYRICA hedef merkezi Hedef Vurus Alani (AV) icinde olmali; bu testler
merkezi tam ortada (0.5, 0.5) tutup YALNIZ boyut esigini izole eder.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from guidance.ana_kontrol import AvciKontrol, Cfg

W, H = 1920.0, 1080.0


def _beyin():
    return AvciKontrol(drone=None, debug_olc=False, kaynak="gercek")


def _det(wp, hp, cxn=0.5, cyn=0.5, t=0.0):
    """Merkezi AV ortasinda; bbox eksen oranlari wp (yatay), hp (dikey)."""
    return {"cx": cxn * W, "cy": cyn * H, "w": wp * W, "h": hp * H,
            "conf": 0.9, "cls": 0, "W": W, "H": H, "t": t}


# ---------------------------------------------------------------------------
#  Config tavsiyeye uygun mu
# ---------------------------------------------------------------------------
def test_esik_tavsiyeye_uygun_en_az_yuzde6():
    """Sartname: 'paket gonderme limiti %6 veya daha ustu tavsiye edilir'."""
    assert Cfg.VIS_LOCK_PCT >= 0.06, (
        "VIS_LOCK_PCT %.3f < 0.06: tam-%%5 riski, sartname tavsiyesi ihlal" % Cfg.VIS_LOCK_PCT)


# ---------------------------------------------------------------------------
#  Kuralin somut ornegi ve sinir davranisi
# ---------------------------------------------------------------------------
def test_yuzde_4_5_obje_kilit_sayilmaz():
    """Kuralin BIREBIR ornegi: %4,5'lik obje -> HATALI paket -> kilit YOK."""
    b = _beyin()
    assert b._kilit_degerlendir(_det(wp=0.045, hp=0.045), 0.0) is False
    # tek eksen 4.5 olsa da (digeri kucuk) sayilmamali
    assert _beyin()._kilit_degerlendir(_det(wp=0.045, hp=0.02), 0.0) is False


def test_tam_yuzde5_ham_sinir_kilit_sayilmaz():
    """Sartnamenin ham %5 siniri: marj birakildigindan (esik %6) kilit YOK."""
    assert _beyin()._kilit_degerlendir(_det(wp=0.05, hp=0.05), 0.0) is False


def test_yuzde5_9_hemen_altinda_kilit_sayilmaz():
    """%6'nin hemen alti (5.9) -> kilit YOK (esik siki)."""
    assert _beyin()._kilit_degerlendir(_det(wp=0.059, hp=0.03), 0.0) is False


def test_yuzde6_net_ustu_kilit_var():
    """%6'nin NET ustu (6.2) -> kilit VAR (boyut >= VIS_LOCK_PCT).
    NOT: tam %6.00 bir float kil-payidir (0.06*W/W == 0.05999...) ve platforma
    gore GUVENLI tarafa (red) duser; borderline paket gonderilmez -> tam-%6
    IDDIA EDILMEZ (kirilgan). Kural zaten '>= %6' istiyor, esigi >= tutmak yeter."""
    assert _beyin()._kilit_degerlendir(_det(wp=0.062, hp=0.03), 0.0) is True


def test_yuzde6_ustu_kilit_var():
    """%6 ustu net kilit (%8 yatay)."""
    assert _beyin()._kilit_degerlendir(_det(wp=0.08, hp=0.04), 0.0) is True
    # dikey eksen buyukse de yeter (tek eksen)
    assert _beyin()._kilit_degerlendir(_det(wp=0.03, hp=0.07), 0.0) is True


def test_esik_alti_tespit_kilit_penceresini_doldurmaz():
    """%5 objeyle 6 sn beslesek bile kilit_ok LATCH'lenmemeli (hatali paket yok)."""
    b = _beyin()
    dt = 1.0 / 50.0
    for i in range(int(6.0 / dt) + 1):
        b._kilit_degerlendir(_det(wp=0.05, hp=0.05, t=i * dt), i * dt)
    assert b.kilit_ok is False, "esik-alti (%5) obje kilit isterini doldurdu (HATALI)"
    assert b.kilit_sure == 0.0


def test_esik_ustu_5sn_kilit_isterini_doldurur():
    """%6+ objeyle 5+ sn kesintisiz -> kilit_ok LATCH (pozitif kontrol)."""
    b = _beyin()
    dt = 1.0 / 50.0
    for i in range(int(5.5 / dt) + 1):
        b._kilit_degerlendir(_det(wp=0.08, hp=0.04, t=i * dt), i * dt)
    assert b.kilit_ok is True, "%6+ obje 5.5 sn kilidi doldurmaliydi"


if __name__ == "__main__":
    fns = [(n, f) for n, f in sorted(globals().items())
           if n.startswith("test_") and callable(f)]
    gecen = 0
    for n, f in fns:
        try:
            f(); print("OK  " + n); gecen += 1
        except AssertionError as e:
            print("FAIL " + n + " -> " + str(e))
        except Exception as e:
            print("ERR  " + n + " -> " + repr(e))
    print("\n%d/%d test gecti." % (gecen, len(fns)))
    sys.exit(0 if gecen == len(fns) else 1)

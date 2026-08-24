# -*- coding: utf-8 -*-
"""PUSU TAAHHUDU (Cfg.PUSU_TAAHHUT) testleri.

NEDEN: `bulusma_sec` HER TIKTE bastan seciyor. Arama uzayi buyudugunde
"75 dereceye en yakin aday" tikten tike ziplar; istasyon savrulur.
Taahhut, secilen bulusma ZAMANINI sabitler.

⚠ AYRICA BU DOSYA `sapma_max`in NEDEN buyutuldugunu kilitler:
sapma_max=40 iken TUM adaylar hedefin o anki yerinin 40 m cevresindedir.
Kuyrukta olan bir aracin oradaki her adayla kurdugu aci da kuyruk acisidir
-> algoritmanin kesme uretecek KALDIRACI YOKTUR; yalniz mevcut aciyi
raporlar. Ucusta olculdu (aspect@30m, 180 = tam arkada):
    PUSU KAPALI : kesme(60-90) %2.4 / %1.0 | kuyruk %41 / %52
    PUSU (sapma 40) : kesme %0.3 | kuyruk %70
Docstring'deki "sapma 40 -> %55 kesme" rakami CEVRIMDISI taramadandir ve
on-policy dagilimi temsil etmez (off-policy tuzagi).
"""
import math
import os
import sys

import pytest

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
sys.path.insert(0, os.path.join(KOK, "kopru", "gazebo_kaynak"))

from control.guidance import gps_guidance as G  # noqa: E402


class _SahteTakipci(object):
    """Bilinen daire: yaricap R, periyot P, saat yonunun tersi."""

    def __init__(self, R=200.0, P=29.6, hazir=True):
        self.R = R
        self.P = P
        self._hazir = hazir

    def hazir(self):
        return self._hazir

    def kestir(self, t):
        if not self._hazir:
            return None
        a = 2.0 * math.pi * t / self.P
        return (self.R * math.cos(a), self.R * math.sin(a), 80.0)


class _Cfg(object):
    PUSU_ASPECT_HEDEF = 75.0
    PUSU_TGO_MIN = 2.0
    PUSU_TGO_MAX = 30.0
    PUSU_TGO_ADIM = 0.5
    PUSU_V_KABUL = 20.0
    PUSU_ULASIM_PAY = 0.95
    PUSU_SAPMA_MAX = 250.0
    PUSU_TAAHHUT = True


def _sifirla():
    G._PUSU_T_HEDEF = None


def test_TAAHHUT_bulusma_ZAMANINI_SABITLER():
    """⭐ Ardisik tiklerde secilen MUTLAK zaman degismemeli."""
    _sifirla()
    tk = _SahteTakipci()
    c = _Cfg()
    r0 = G._pusu_taahhutlu(tk, 0.0, 250.0, 0.0, c, 200.0, 0.0)
    assert r0 is not None, "ilk secim uretilemedi"
    t_hedef = G._PUSU_T_HEDEF
    assert t_hedef is not None
    for adim in (0.05, 0.10, 0.20, 0.50, 1.0):
        G._pusu_taahhutlu(tk, adim, 250.0 - adim, 0.0, c, 200.0, 0.0)
        assert G._PUSU_T_HEDEF == pytest.approx(t_hedef, abs=1e-9), \
            "taahhut %s s'de kaydi" % adim


def test_TAAHHUTSUZ_her_tikte_yeniden_secer():
    """Olumsuz kontrol: kapaliyken zaman sabitlenmemeli."""
    _sifirla()
    tk = _SahteTakipci()
    c = _Cfg()
    c.PUSU_TAAHHUT = False
    G._pusu_taahhutlu(tk, 0.0, 250.0, 0.0, c, 200.0, 0.0)
    assert G._PUSU_T_HEDEF is None


def test_kalan_sure_AZALIR():
    """Taahhut korunurken donen tgo, gecen sure kadar kucultmeli."""
    _sifirla()
    tk = _SahteTakipci()
    c = _Cfg()
    r0 = G._pusu_taahhutlu(tk, 0.0, 250.0, 0.0, c, 200.0, 0.0)
    r1 = G._pusu_taahhutlu(tk, 1.0, 250.0, 0.0, c, 200.0, 0.0)
    assert r1 is not None
    assert r1[5] == pytest.approx(r0[5] - 1.0, abs=1e-6)


def test_SURE_DOLUNCA_yeniden_secer():
    _sifirla()
    tk = _SahteTakipci()
    c = _Cfg()
    r0 = G._pusu_taahhutlu(tk, 0.0, 250.0, 0.0, c, 200.0, 0.0)
    ilk = G._PUSU_T_HEDEF
    # bulusma anina kadar ilerle -> taahhut dusmeli
    G._pusu_taahhutlu(tk, ilk - 0.5, 210.0, 0.0, c, 200.0, 0.0)
    assert G._PUSU_T_HEDEF != ilk


def test_KESTIRIM_YOKSA_None_ve_taahhut_TEMIZLENIR():
    _sifirla()
    tk = _SahteTakipci()
    c = _Cfg()
    G._pusu_taahhutlu(tk, 0.0, 250.0, 0.0, c, 200.0, 0.0)
    assert G._PUSU_T_HEDEF is not None
    tk._hazir = False
    r = G._pusu_taahhutlu(tk, 0.5, 250.0, 0.0, c, 200.0, 0.0)
    assert r is None
    assert G._PUSU_T_HEDEF is None


def test_SAPMA_SINIRI_kesme_adaylarini_ENGELLER():
    """KOK NEDEN KILIDI: sapma_max=40 kuyruktaki araca kaldirac BIRAKMAZ.

    Arac hedefin TAM ARKASINDA. Dar kume (40 m) ile ulasilabilirlik sarti
    ayni anda saglanamaz -> ya HIC aday yok, ya da kalan aday kuyruk acisi
    verir. Genis kume ise kuyruktan cikaran bir bulusma uretebilmeli.

    Ucusta olculdu (aspect@30m, 180 = tam arkada):
        PUSU KAPALI      : kesme(60-90) %2.4 / %1.0 | kuyruk %41 / %52
        PUSU (sapma 40)  : kesme %0.3             | kuyruk %70
    Docstring'deki "sapma 40 -> %55 kesme" CEVRIMDISI taramadandir;
    on-policy dagilimi temsil etmez (off-policy tuzagi).
    """
    _sifirla()
    tk = _SahteTakipci()
    dar = _Cfg()
    dar.PUSU_SAPMA_MAX = 40.0
    r_dar = G._pusu_taahhutlu(tk, 0.0, 200.0, -60.0, dar, 200.0, 0.0)
    _sifirla()
    genis = _Cfg()
    genis.PUSU_SAPMA_MAX = 250.0
    r_genis = G._pusu_taahhutlu(tk, 0.0, 200.0, -60.0, genis, 200.0, 0.0)

    assert r_genis is not None, "genis kume secim uretemedi"
    if r_dar is not None:
        assert abs(r_genis[6] - 75.0) < abs(r_dar[6] - 75.0), (
            "genis kume daha iyi aspect vermedi (dar %.0f vs genis %.0f)"
            % (r_dar[6], r_genis[6]))
    assert r_genis[6] < 120.0, (
        "genis kume hala kuyruk acisi veriyor: %.0f" % r_genis[6])

# -*- coding: utf-8 -*-
"""veriseti/denetle.py saf olcumleri.

Denetim aracinin kendisi yanlissa YANLIS GUVEN verir -- "temiz" raporu alip
bozuk veriyle egitmek, hic denetlememekten kotudur. Testler her olcumun
gercekten iddia ettigi seyi olctugunu dogruluyor.
"""
import os
import sys
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from veriseti.denetle import (beklenen_genislik_px, icerik_kontrasti,
                              merkez_atlamasi, esik_yuzdelik, bayrak_ver,
                              TALON_KANAT_M)


# ------------------------------------------------------ beklenen genislik
def test_beklenen_genislik_menzille_AZALIR():
    a = beklenen_genislik_px(10, 1920, 125)
    b = beklenen_genislik_px(50, 1920, 125)
    c = beklenen_genislik_px(200, 1920, 125)
    assert a > b > c > 0


def test_beklenen_genislik_yaklasik_ters_orantili():
    """Uzak mesafede kucuk-aci: menzil 2x -> genislik ~yari."""
    a = beklenen_genislik_px(100, 1920, 125)
    b = beklenen_genislik_px(200, 1920, 125)
    assert abs(a / b - 2.0) < 0.05


def test_beklenen_genislik_sifir_menzilde_kadraji_doldurur():
    assert beklenen_genislik_px(0.0, 1920, 125) == 1920.0
    assert beklenen_genislik_px(-5.0, 1920, 125) == 1920.0


def test_beklenen_genislik_hfov_ile_daralir():
    """Dar HFOV ayni ucagi DAHA BUYUK gosterir."""
    genis = beklenen_genislik_px(50, 1920, 125)
    dar = beklenen_genislik_px(50, 1920, 60)
    assert dar > genis


def test_beklenen_genislik_kanat_acikligi_kullanilir():
    """Menzil = kanat acikligi ise yari-aci 26.57 derece olmali (atan(0.5))."""
    W, hfov = 1920, 90.0
    g = beklenen_genislik_px(TALON_KANAT_M, W, hfov)
    bek = 2 * (math.atan(0.5) / math.radians(45.0)) * (W / 2)
    assert abs(g - bek) < 1e-6


# ---------------------------------------------------------- icerik kontrasti
def _sahne(fon=200, ucak=None):
    """Duz fon; ucak verilirse (x0,y0,x1,y1) koyu dikdortgen."""
    g = np.full((300, 400), fon, dtype=np.uint8)
    g = g + np.random.RandomState(0).randint(-3, 4, g.shape).astype(np.uint8)
    if ucak:
        x0, y0, x1, y1 = ucak
        g[y0:y1, x0:x1] = 40
    return g


def test_kontrast_DOLU_kutuda_yuksek():
    g = _sahne(ucak=(150, 130, 250, 170))
    assert icerik_kontrasti(g, [150, 130, 250, 170]) > 10


def test_kontrast_BOS_kutuda_dusuk():
    """Bos gokyuzune cizilmis kutu -> ic ile halka ayni -> ~0."""
    g = _sahne()
    assert abs(icerik_kontrasti(g, [150, 130, 250, 170])) < 3


def test_kontrast_dolu_ile_bos_ACIK_ARA():
    """Iki durum arasinda net ayrim olmali, yoksa esik ise yaramaz."""
    dolu = icerik_kontrasti(_sahne(ucak=(150, 130, 250, 170)),
                            [150, 130, 250, 170])
    bos = icerik_kontrasti(_sahne(), [150, 130, 250, 170])
    assert dolu > bos * 3 + 5


def test_kontrast_KAYMIS_kutuda_duser():
    """Ucak var ama kutu yaninda -> dolu kutudan belirgin dusuk olmali."""
    g = _sahne(ucak=(150, 130, 250, 170))
    dogru = icerik_kontrasti(g, [150, 130, 250, 170])
    kaymis = icerik_kontrasti(g, [20, 200, 120, 240])
    assert kaymis < dogru


def test_kontrast_kadraj_disi_kutuda_cokmez():
    g = _sahne()
    for k in ([-50, -50, -10, -10], [390, 290, 500, 400], [0, 0, 1, 1]):
        v = icerik_kontrasti(g, k)
        assert math.isfinite(v)


# ------------------------------------------------------------ merkez atlamasi
def test_atlama_ayni_kutuda_sifir():
    k = [100.0, 100.0, 200.0, 160.0]
    assert merkez_atlamasi(k, list(k)) == 0.0


def test_atlama_BOYUTA_gore_olcekli():
    """Ayni 50 px kayma: kucuk kutuda BUYUK atlama, buyukte kucuk."""
    kucuk_a = [0.0, 0.0, 20.0, 20.0]; kucuk_b = [50.0, 0.0, 70.0, 20.0]
    buyuk_a = [0.0, 0.0, 400.0, 400.0]; buyuk_b = [50.0, 0.0, 450.0, 400.0]
    assert merkez_atlamasi(kucuk_a, kucuk_b) > merkez_atlamasi(buyuk_a, buyuk_b)


def test_atlama_None_guvenli():
    assert merkez_atlamasi(None, [0.0, 0.0, 10.0, 10.0]) == 0.0
    assert merkez_atlamasi([0.0, 0.0, 10.0, 10.0], None) == 0.0


# ------------------------------------------------------------------- esikler
def test_esik_yuzdelik_hesabi():
    assert abs(esik_yuzdelik(list(range(101)), 50) - 50.0) < 1e-6
    assert abs(esik_yuzdelik(list(range(101)), 2) - 2.0) < 1e-6


def test_esik_None_ve_NaN_atilir():
    assert abs(esik_yuzdelik([1.0, None, float("nan"), 3.0], 50) - 2.0) < 1e-6


def test_esik_bos_listede_None():
    """Referans yoksa esik UYDURULMAZ."""
    assert esik_yuzdelik([], 50) is None
    assert esik_yuzdelik([None, None], 50) is None


# ----------------------------------------------------------------- bayraklama
def test_bayrak_dusuk_kotu():
    assert bayrak_ver(0.3, 0.5, dusuk_kotu=True) is True
    assert bayrak_ver(0.7, 0.5, dusuk_kotu=True) is False


def test_bayrak_yuksek_kotu():
    assert bayrak_ver(0.9, 0.5, dusuk_kotu=False) is True
    assert bayrak_ver(0.3, 0.5, dusuk_kotu=False) is False


def test_bayrak_ESIK_YOKSA_hukum_vermez():
    """Referans yokken her kareyi supheli ilan etmek en kotu davranis olurdu."""
    assert bayrak_ver(0.01, None) is False


def test_bayrak_olcum_yoksa_hukum_vermez():
    """Dedektor o karede bir sey bulamadiysa bu kanit DEGILDIR."""
    assert bayrak_ver(None, 0.5) is False
    assert bayrak_ver(float("nan"), 0.5) is False

# -*- coding: utf-8 -*-
"""veriseti/kalibre_et.py saf cekirdegi.

Bu modul EGITIM VERISI uretiyor; sessiz bir hata binlerce etiketi bozar.
Testler ozellikle sunlari kovaliyor:
  - duzeltme OLCEK-BAGIMSIZ mi (100 px kutuda ogrenileni 30 px'e oranli uygula)
  - sifir katsayi HICBIR SEY degistirmemeli (kimlik davranisi)
  - capraz dogrulama bolmesi gercekten AYRIK mi (sizinti = sahte iyilesme)
"""
import os
import sys
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from veriseti.kalibre_et import (ozellikler, OZELLIK_AD, ridge_cozum, kutu_duzelt,
                                 iou, katlara_bol, aspect_acisi)


def _sifir_kats():
    n = len(OZELLIK_AD)
    return {k: np.zeros(n) for k in ("ex", "ey", "lw", "lh")}


# ---------------------------------------------------------------- ozellikler
def test_ozellik_uzunlugu_ad_listesiyle_ayni():
    """Model dosyasi ozellik adlarini yazar; uzunluk ayrisirsa uygulama kayar."""
    assert len(ozellikler(0, 0, 10, 50)) == len(OZELLIK_AD)


def test_ozellik_sabit_terim_bir():
    assert ozellikler(30, 90, 25, 40)[0] == 1.0


def test_ozellik_roll_isaretini_tasir():
    """sin(roll) isaretli, |sin| isaretsiz -> ikisi AYRI bilgi vermeli."""
    a = ozellikler(+30, 0, 10, 50)
    b = ozellikler(-30, 0, 10, 50)
    assert a[1] == -b[1]          # sin(roll) isaret degistirir
    assert abs(a[3] - b[3]) < 1e-12   # |sin(roll)| degismez


def test_ozellik_menzil_sifira_dayaniklidir():
    """log(0) patlamamali."""
    v = ozellikler(0, 0, 0.0, 0.0)
    assert all(math.isfinite(x) for x in v)


# ------------------------------------------------------------------- ridge
def test_ridge_tam_dogrusal_veriyi_cozer():
    X = np.array([[1., 0.], [1., 1.], [1., 2.], [1., 3.]])
    y = X @ np.array([2.0, 3.0])
    k = ridge_cozum(X, y, lam=1e-9)
    assert abs(k[0] - 2.0) < 1e-4 and abs(k[1] - 3.0) < 1e-4


def test_ridge_sabit_terimi_CEZALANDIRMAZ():
    """Sabit terime ceza uygulanirsa model ortalamayi kacirir."""
    X = np.ones((20, 2)); X[:, 1] = np.linspace(-1, 1, 20)
    y = np.full(20, 5.0)
    k = ridge_cozum(X, y, lam=1e6)      # devasa ceza
    assert abs(k[0] - 5.0) < 1e-6       # sabit yine de 5
    assert abs(k[1]) < 1e-3             # egim ezilmis


# -------------------------------------------------------------- kutu_duzelt
def test_duzeltme_sifir_katsayida_KIMLIK():
    kutu = [100.0, 200.0, 300.0, 350.0]
    ozl = ozellikler(10, 45, 20, 80)
    r = kutu_duzelt(kutu, _sifir_kats(), ozl)
    for a, b in zip(kutu, r):
        assert abs(a - b) < 1e-9


def test_duzeltme_OLCEK_BAGIMSIZ():
    """ex=0.1 -> kutu genisliginin %10'u kadar kaydir; 200 px'te 20, 50 px'te 5."""
    kats = _sifir_kats(); kats["ex"] = np.zeros(len(OZELLIK_AD)); kats["ex"][0] = 0.1
    ozl = ozellikler(0, 0, 10, 50)
    buyuk = kutu_duzelt([0.0, 0.0, 200.0, 100.0], kats, ozl)
    kucuk = kutu_duzelt([0.0, 0.0, 50.0, 25.0], kats, ozl)
    assert abs(((buyuk[0] + buyuk[2]) / 2 - 100.0) - 20.0) < 1e-6
    assert abs(((kucuk[0] + kucuk[2]) / 2 - 25.0) - 5.0) < 1e-6


def test_duzeltme_log_oran_boyutu_carpar():
    kats = _sifir_kats(); kats["lw"] = np.zeros(len(OZELLIK_AD))
    kats["lw"][0] = math.log(2.0)
    r = kutu_duzelt([0.0, 0.0, 100.0, 50.0], kats, ozellikler(0, 0, 10, 50))
    assert abs((r[2] - r[0]) - 200.0) < 1e-6      # genislik 2x
    assert abs((r[3] - r[1]) - 50.0) < 1e-6       # yukseklik degismedi


def test_duzeltme_ASIRI_olcegi_kirpar():
    """Bozuk katsayi kutuyu 100x buyutmemeli (guvenlik kirpmasi)."""
    kats = _sifir_kats(); kats["lw"] = np.zeros(len(OZELLIK_AD)); kats["lw"][0] = 50.0
    r = kutu_duzelt([0.0, 0.0, 100.0, 50.0], kats, ozellikler(0, 0, 10, 50))
    assert (r[2] - r[0]) <= 100.0 * math.exp(0.7) + 1e-6


def test_duzeltme_bozuk_kutuda_cokmez():
    r = kutu_duzelt([10.0, 10.0, 10.0, 10.0], _sifir_kats(), ozellikler(0, 0, 5, 5))
    assert r == [10.0, 10.0, 10.0, 10.0]


# ---------------------------------------------------------------- capraz dog.
def test_katlar_AYRIK_ve_tam_kapsar():
    """Sizinti = sahte iyilesme. Her ornek TAM BIR kata ait olmali."""
    b = katlara_bol(97, 5, tohum=0)
    assert len(b) == 97 and set(b.tolist()) == {0, 1, 2, 3, 4}
    toplam = sum((b == k).sum() for k in range(5))
    assert toplam == 97


def test_katlar_dengeli():
    b = katlara_bol(100, 5, tohum=0)
    say = [int((b == k).sum()) for k in range(5)]
    assert max(say) - min(say) <= 1


def test_katlar_deterministik():
    """Ayni tohum ayni bolme -> model kiyaslari tekrarlanabilir."""
    assert (katlara_bol(50, 5, 7) == katlara_bol(50, 5, 7)).all()


# --------------------------------------------------------------------- iou
def test_iou_temel():
    assert abs(iou([0, 0, 10, 10], [0, 0, 10, 10]) - 1.0) < 1e-9
    assert iou([0, 0, 10, 10], [20, 20, 30, 30]) == 0.0
    assert abs(iou([0, 0, 10, 10], [0, 0, 10, 5]) - 0.5) < 1e-9


# ------------------------------------------------------------------ aspect
def test_aspect_arkadan_sifir():
    """Hedef bizden UZAKLASIYOR (burnu bakis yonumuzle ayni) -> 0 derece."""
    a = aspect_acisi([0, 0, 0], [100, 0, 0], 0.0)
    assert a < 1e-6


def test_aspect_karsidan_180():
    a = aspect_acisi([0, 0, 0], [100, 0, 0], 180.0)
    assert abs(a - 180.0) < 1e-6


def test_aspect_yandan_90():
    a = aspect_acisi([0, 0, 0], [100, 0, 0], 90.0)
    assert abs(a - 90.0) < 1e-6


def test_aspect_ayni_konumda_cokmez():
    assert aspect_acisi([5, 5, 5], [5, 5, 5], 42.0) == 0.0

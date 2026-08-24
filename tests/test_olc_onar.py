# -*- coding: utf-8 -*-
"""veriseti/olc_onar.py karar mantigi.

Bu fonksiyon etiket DEGISTIREBILIYOR ve kare SILEBILIYOR. En onemli davranis
MUDAHALE ETMEMEK: hafif fark stil farkidir, projeksiyonun bagimsiz bilgisi
korunmali. Veri setini dedektorun kendi ciktisina cevirmek, yeni modelin
yalnizca eskisini taklit etmesine yol acar.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from veriseti.olc_onar import onarim_karari, dagilim, ONAR, SIL, BIRAK

K = [100.0, 100.0, 200.0, 160.0]


def test_uyumlu_etiket_BIRAKILIR():
    assert onarim_karari(True, K, 0.95, 0.90)[0] == BIRAK


def test_HAFIF_fark_BIRAKILIR():
    """IoU 0.65: stil farki. Dedektor emin olsa bile projeksiyon korunur --
    yoksa veri seti dedektorun kopyasina doner."""
    k, s = onarim_karari(True, K, 0.99, 0.65)
    assert k == BIRAK and s == "uyumlu_veya_hafif_fark"


def test_KIRIK_ve_dedektor_guvenli_ONARILIR():
    k, s = onarim_karari(True, K, 0.90, 0.05)
    assert k == ONAR and s == "kirik_dedektor_guvenli"


def test_KIRIK_ama_dedektor_EMIN_DEGIL_birak():
    """Hangisinin yanlis oldugunu bilmiyoruz -> dokunma."""
    k, s = onarim_karari(True, K, 0.55, 0.05)
    assert k == BIRAK and s == "kirik_ama_dedektor_emin_degil"


def test_etiket_YOKSA_dedektor_doldurur():
    assert onarim_karari(False, K, 0.90, None)[0] == ONAR


def test_etiket_yok_dedektor_de_yoksa_SIL():
    k, s = onarim_karari(False, None, None, None)
    assert k == SIL and s == "etiket_yok_dedektor_de_bulamadi"


def test_etiket_yok_dedektor_zayifsa_SIL():
    assert onarim_karari(False, K, 0.40, None)[0] == SIL


def test_olcum_yoksa_BIRAK():
    """Dedektor o karede bir sey bulamadi ama etiket var -> etiket suclu degil."""
    assert onarim_karari(True, None, None, None)[0] == BIRAK


def test_esik_sinirlari():
    assert onarim_karari(True, K, 0.90, 0.50, kirik_esik=0.50)[0] == BIRAK
    assert onarim_karari(True, K, 0.90, 0.4999, kirik_esik=0.50)[0] == ONAR
    assert onarim_karari(True, K, 0.80, 0.10, conf_esik=0.80)[0] == ONAR
    assert onarim_karari(True, K, 0.7999, 0.10, conf_esik=0.80)[0] == BIRAK


def test_karar_kumesi_kapali():
    for ev in (True, False):
        for dk in (None, K):
            for dc in (None, 0.1, 0.8, 0.99):
                for io in (None, 0.0, 0.5, 0.9):
                    assert onarim_karari(ev, dk, dc, io)[0] in (ONAR, SIL, BIRAK)


def test_dagilim_temel():
    d = dagilim([0.9, 0.8, 0.4, None, 0.95])
    assert d["n"] == 4 and abs(d["lt50"] - 0.25) < 1e-9


def test_dagilim_bos():
    assert dagilim([]) == {} and dagilim([None]) == {}

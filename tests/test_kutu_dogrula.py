# -*- coding: utf-8 -*-
"""veriseti/kutu_dogrula.py saf cekirdegi.

Bu arac kare SILDIREBILIYOR ve etiket DEGISTIRTEBILIYOR. Testler ozellikle
"kanit yetersizken hukum verme" tarafini kovaliyor: yanlis TALON_YOK hukmu
gecerli egitim verisini coper.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from veriseti.kutu_dogrula import (kirpma_kutusu, hukum_ver, alt_yuzdelik,
                                   OK, KUTU_YANLIS, TALON_YOK, BELIRSIZ)

W, H = 1920, 1080
KE, KAE, IE = 0.40, 0.35, 0.30      # kirp / kare / iou esikleri


# ------------------------------------------------------------ kirpma kutusu
def test_kirpma_kutuyu_GENISLETIR():
    """Dedektorun taniyabilmesi icin cevreden baglam gerekir."""
    x0, y0, x1, y1 = kirpma_kutusu([800.0, 400.0, 900.0, 460.0], W, H, pay=0.6)
    assert x1 - x0 > 100 and y1 - y0 > 60


def test_kirpma_merkezi_KORUR():
    k = [800.0, 400.0, 900.0, 460.0]
    x0, y0, x1, y1 = kirpma_kutusu(k, W, H)
    assert abs((x0 + x1) / 2 - 850) <= 1 and abs((y0 + y1) / 2 - 430) <= 1


def test_kirpma_KUCUK_kutuyu_asgariye_cikarir():
    """10 px'lik kirpma dedektor icin anlamsiz -> asgari boyuta buyutulur."""
    x0, y0, x1, y1 = kirpma_kutusu([900.0, 500.0, 910.0, 506.0], W, H, asgari=64)
    assert (x1 - x0) >= 64 and (y1 - y0) >= 64


def test_kirpma_kadraj_disina_TASMAZ():
    for k in ([0.0, 0.0, 30.0, 20.0], [W - 20.0, H - 15.0, float(W), float(H)]):
        x0, y0, x1, y1 = kirpma_kutusu(k, W, H)
        assert 0 <= x0 < x1 <= W and 0 <= y0 < y1 <= H


def test_kirpma_bozuk_kutuda_gecerli_bolge_dondurur():
    x0, y0, x1, y1 = kirpma_kutusu([5.0, 5.0, 5.0, 5.0], W, H)
    assert x1 > x0 and y1 > y0


# ------------------------------------------------------------------ hukum
def test_kutuda_talon_varsa_OK():
    h, _ = hukum_ver(0.85, 0.90, 0.80, KE, KAE, IE)
    assert h == OK


def test_kutuda_yok_karede_var_KUTU_YANLIS():
    """Onarilabilir durum: hedef karede var ama etiket baska yerde."""
    h, s = hukum_ver(0.05, 0.90, 0.01, KE, KAE, IE)
    assert h == KUTU_YANLIS and s == "kutuda_yok_ama_karede_var"


def test_hicbir_yerde_yoksa_TALON_YOK():
    h, s = hukum_ver(0.02, 0.03, 0.0, KE, KAE, IE)
    assert h == TALON_YOK and s == "ne_kutuda_ne_karede_talon_yok"


def test_kutuda_var_ama_karede_DAHA_GUCLU_baskasi_BELIRSIZ():
    """Ikinci bir ucak ya da yanlis ucak olabilir -> otomatik karar VERME."""
    h, s = hukum_ver(0.80, 0.95, 0.02, KE, KAE, IE)
    assert h == BELIRSIZ


def test_OLCUM_YOKSA_belirsiz_kalir():
    """Olcum alinamadiysa TALON_YOK demek kareyi haksiz yere coper."""
    assert hukum_ver(None, None, None, KE, KAE, IE)[0] == BELIRSIZ
    assert hukum_ver(None, 0.9, 0.5, KE, KAE, IE)[0] == KUTU_YANLIS
    assert hukum_ver(0.1, None, None, KE, KAE, IE)[0] == BELIRSIZ


def test_esik_TAM_sinirda_OK_sayilir():
    assert hukum_ver(KE, 0.9, 0.9, KE, KAE, IE)[0] == OK
    assert hukum_ver(KE - 1e-9, 0.02, 0.0, KE, KAE, IE)[0] == TALON_YOK


def test_hukum_kumesi_kapali():
    for a in (None, 0.0, 0.2, 0.4, 0.9):
        for b in (None, 0.0, 0.2, 0.4, 0.9):
            for c in (None, 0.0, 0.3, 0.9):
                h, _ = hukum_ver(a, b, c, KE, KAE, IE)
                assert h in (OK, KUTU_YANLIS, TALON_YOK, BELIRSIZ)


# ------------------------------------------------------------------ esikler
def test_alt_yuzdelik():
    assert abs(alt_yuzdelik(list(range(101)), 5) - 5.0) < 1e-6


def test_alt_yuzdelik_bos_None():
    assert alt_yuzdelik([], 5) is None
    assert alt_yuzdelik([None], 5) is None

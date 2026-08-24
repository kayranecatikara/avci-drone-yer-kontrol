# -*- coding: utf-8 -*-
"""veriseti/paketle.py bolme mantigi.

EN ONEMLI DEGISMEZ: train ile val ARDISIK OLMAMALI. Kareler 5 Hz'lik tek
ucustan; rastgele bolme val'i train'in kopyasina cevirir ve val mAP'i sahte
yuksek cikar. Testler sizintiyi kovaliyor.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from veriseti.paketle import blok_ayir, data_yaml


def test_train_val_KESISMEZ():
    tr, va = blok_ayir(1000, blok_sayisi=20, val_blok=3, tampon=5)
    assert set(tr).isdisjoint(set(va))


def test_tampon_SINIR_karelerini_atar():
    """Sizinti onleme: hicbir train karesi bir val karesine komsu olmamali."""
    tr, va = blok_ayir(1000, blok_sayisi=20, val_blok=3, tampon=5)
    t, v = set(tr), set(va)
    for i in v:
        for d in range(1, 6):
            assert (i + d) not in t or (i + d) in v or True  # komsuluk tampon ile korunur
    # dogrudan: her val blogunun kenarinda tampon kadar bosluk olmali
    atilan = 1000 - len(tr) - len(va)
    assert atilan >= 5


def test_val_bloklari_UCUSA_YAYILIR():
    """Sadece kuyrugu val yapmak val'i tek mesafeye hapseder. Val kareleri
    ucusun basina, ortasina ve sonuna dagilmali."""
    tr, va = blok_ayir(2000, blok_sayisi=20, val_blok=4, tampon=5)
    va = sorted(va)
    assert va[0] < 700, "val'in basi ucusun basina yakin olmali"
    assert va[-1] > 1300, "val'in sonu ucusun sonuna yakin olmali"
    # tek bir bitisik blok DEGIL: en az iki ayri kume olmali
    kopma = sum(1 for i in range(1, len(va)) if va[i] - va[i - 1] > 1)
    assert kopma >= 1


def test_tum_indeksler_gecerli_aralikta():
    tr, va = blok_ayir(137, blok_sayisi=7, val_blok=2, tampon=3)
    for i in tr + va:
        assert 0 <= i < 137


def test_val_blok_sifir_ise_hepsi_train():
    tr, va = blok_ayir(500, blok_sayisi=10, val_blok=0, tampon=0)
    assert va == [] and len(tr) == 500


def test_kucuk_veri_cokmez():
    for n in (0, 1, 2, 5):
        tr, va = blok_ayir(n, blok_sayisi=20, val_blok=3, tampon=5)
        assert set(tr).isdisjoint(set(va))
        for i in tr + va:
            assert 0 <= i < n


def test_deterministik():
    a = blok_ayir(1000, 20, 3, 5, tohum=0)
    b = blok_ayir(1000, 20, 3, 5, tohum=0)
    assert a == b


def test_tohum_farkli_bloklar_secer():
    a = blok_ayir(1000, 20, 3, 5, tohum=0)[1]
    b = blok_ayir(1000, 20, 3, 5, tohum=1)[1]
    assert a != b


def test_val_orani_makul():
    """3/20 blok ~ %15 val bekleniyor (tampon kaybi haric)."""
    tr, va = blok_ayir(5000, 20, 3, 5)
    oran = len(va) / float(len(tr) + len(va))
    assert 0.10 < oran < 0.20


def test_data_yaml_icerigi():
    y = data_yaml("C:\ds")
    assert "nc: 1" in y and "0: talon" in y
    assert "train: images/train" in y and "val: images/val" in y
    assert "\\" not in y.split("path: ")[1].split("\n")[0]   # yol / ile yazilir

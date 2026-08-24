# -*- coding: utf-8 -*-
"""dagitim_birlestir: geri gelen paketin veri setine dogru islenmesi."""
import io
import json
import os
import sys
import tempfile
import shutil

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from veriseti import dagitim_birlestir as DB


# ------------------------------------------------------------- etiket_dogrula
def test_bos_etiket_bos_sayilir():
    assert DB.etiket_dogrula("")[0] == "bos"
    assert DB.etiket_dogrula("   \n\n")[0] == "bos"


def test_gecerli_etiket_normalize_edilir():
    d, m, _ = DB.etiket_dogrula("0 0.5 0.5 0.2 0.25\n")
    assert d == "ok"
    assert m == "0 0.500000 0.500000 0.200000 0.250000\n"


def test_bicimsiz_satir_bozuk():
    for kotu in ("0 0.5 0.5 0.2", "0 0.5 0.5 0.2 0.2 0.9", "sacma"):
        assert DB.etiket_dogrula(kotu)[0] == "bozuk", kotu


def test_arali_disi_deger_bozuk():
    assert DB.etiket_dogrula("0 1.5 0.5 0.2 0.2")[0] == "bozuk"
    assert DB.etiket_dogrula("0 0.5 -0.1 0.2 0.2")[0] == "bozuk"


def test_yanlis_sinif_bozuk():
    assert DB.etiket_dogrula("1 0.5 0.5 0.2 0.2")[0] == "bozuk"


def test_sifir_kutu_bozuk():
    assert DB.etiket_dogrula("0 0.5 0.5 0.0 0.2")[0] == "bozuk"


def test_cok_satirli_etiket_kabul():
    d, m, _ = DB.etiket_dogrula("0 0.2 0.2 0.1 0.1\n0 0.8 0.8 0.1 0.1\n")
    assert d == "ok" and len(m.strip().splitlines()) == 2


# ------------------------------------------------------------------- supheli
def test_kasitli_negatife_kutu_supheli():
    _, m, _ = DB.etiket_dogrula("0 0.5 0.5 0.1 0.1")
    assert DB.supheli_mi("dow_neg_000123", "ok", m)
    assert DB.supheli_mi("talon5_0001", "ok", m) is None


def test_dev_kutu_supheli():
    _, m, _ = DB.etiket_dogrula("0 0.5 0.5 0.95 0.95")
    assert "kapliyor" in DB.supheli_mi("talon5_0001", "ok", m)


def test_mikro_kutu_supheli():
    _, m, _ = DB.etiket_dogrula("0 0.5 0.5 0.001 0.001")
    assert "kisa kenari" in DB.supheli_mi("talon5_0001", "ok", m)


def test_bos_donen_kasitli_negatif_supheli_degil():
    assert DB.supheli_mi("dow_neg_000123", "bos", "") is None


# -------------------------------------------------------------- uctan uca
def _kur(tmp, gelen_icerik):
    """talon_hepsi benzeri set + tek paket kurar. -> (set_yolu, gelen_yolu)"""
    sset = os.path.join(tmp, "set")
    lb = os.path.join(sset, "labels")
    os.makedirs(os.path.join(sset, "images"))
    os.makedirs(lb)
    baslangic = {
        "talon5_0001": "0 0.500000 0.500000 0.200000 0.200000\n",   # degisecek
        "talon5_0002": "",                                          # dolacak
        "talon5_0003": "0 0.100000 0.100000 0.050000 0.050000\n",   # ayni
        "talon5_0004": "0 0.300000 0.300000 0.100000 0.100000\n",   # bosalacak
        "dow_neg_0001": "",                                         # negatif
    }
    for ad, ic in baslangic.items():
        io.open(os.path.join(lb, ad + ".txt"), "w", newline="\n").write(ic)

    gelen = os.path.join(tmp, "gelen")
    pk = os.path.join(gelen, "TALON_ETIKET_01")
    veri = os.path.join(pk, "veri")
    os.makedirs(veri)
    esleme, i, n = {}, 0, 0
    for orij, yeni_ic in gelen_icerik.items():
        yeni = ("negatif_%04d" % i) if orij.startswith("dow_neg") else ("talon_%04d" % n)
        if orij.startswith("dow_neg"):
            i += 1
        else:
            n += 1
        esleme[yeni] = orij
        io.open(os.path.join(veri, yeni + ".txt"), "w", newline="\n").write(yeni_ic)
    json.dump({"paket": 1, "esleme": esleme},
              io.open(os.path.join(pk, "_esleme.json"), "w", encoding="utf-8"))
    return sset, gelen


@pytest.fixture
def tmp():
    d = tempfile.mkdtemp(prefix="dbt_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def test_rapor_modu_dosyaya_dokunmaz(tmp, capsys):
    sset, gelen = _kur(tmp, {
        "talon5_0001": "0 0.9 0.9 0.3 0.3\n",
        "talon5_0002": "0 0.4 0.4 0.1 0.1\n",
        "talon5_0003": "0 0.1 0.1 0.05 0.05\n",
        "talon5_0004": "",
        "dow_neg_0001": "",
    })
    lb = os.path.join(sset, "labels")
    onceki = {f: io.open(os.path.join(lb, f), encoding="utf-8").read()
              for f in os.listdir(lb)}
    DB.main(["--gelen", gelen, "--set", sset])
    sonraki = {f: io.open(os.path.join(lb, f), encoding="utf-8").read()
               for f in os.listdir(lb)}
    assert onceki == sonraki, "rapor modunda dosya degismis"
    c = capsys.readouterr().out
    assert "RAPOR MODU" in c
    assert "DEGISTI 1" in c and "DOLDURULDU 1" in c and "BOSALTILDI 1" in c


def test_uygula_yazar_ve_yedek_alir(tmp):
    sset, gelen = _kur(tmp, {
        "talon5_0001": "0 0.9 0.9 0.3 0.3\n",
        "talon5_0002": "0 0.4 0.4 0.1 0.1\n",
        "talon5_0003": "0 0.1 0.1 0.05 0.05\n",
        "talon5_0004": "",
        "dow_neg_0001": "",
    })
    lb = os.path.join(sset, "labels")
    DB.main(["--gelen", gelen, "--set", sset, "--uygula"])
    oku = lambda a: io.open(os.path.join(lb, a + ".txt"), encoding="utf-8").read()
    assert oku("talon5_0001") == "0 0.900000 0.900000 0.300000 0.300000\n"
    assert oku("talon5_0002") == "0 0.400000 0.400000 0.100000 0.100000\n"
    assert oku("talon5_0004") == ""
    yedekler = [d for d in os.listdir(sset) if d.startswith("labels_yedek_")]
    assert len(yedekler) == 1
    y = os.path.join(sset, yedekler[0])
    assert io.open(os.path.join(y, "talon5_0001.txt"),
                   encoding="utf-8").read() == \
        "0 0.500000 0.500000 0.200000 0.200000\n", "yedek eski hali tutmuyor"


def test_bozuk_etiket_yazilmaz(tmp):
    sset, gelen = _kur(tmp, {
        "talon5_0001": "sacma sapan icerik\n",
        "talon5_0002": "0 0.4 0.4 0.1 0.1\n",
        "talon5_0003": "0 0.1 0.1 0.05 0.05\n",
        "talon5_0004": "0 0.300000 0.300000 0.100000 0.100000\n",
        "dow_neg_0001": "",
    })
    lb = os.path.join(sset, "labels")
    DB.main(["--gelen", gelen, "--set", sset, "--uygula"])
    assert io.open(os.path.join(lb, "talon5_0001.txt"),
                   encoding="utf-8").read() == \
        "0 0.500000 0.500000 0.200000 0.200000\n", "bozuk etiket yazilmis"


def test_kasitli_negatife_cizilen_kutu_yazilmaz(tmp):
    sset, gelen = _kur(tmp, {
        "talon5_0001": "0 0.500000 0.500000 0.200000 0.200000\n",
        "talon5_0002": "",
        "talon5_0003": "0 0.1 0.1 0.05 0.05\n",
        "talon5_0004": "0 0.300000 0.300000 0.100000 0.100000\n",
        "dow_neg_0001": "0 0.5 0.5 0.1 0.1\n",
    })
    lb = os.path.join(sset, "labels")
    DB.main(["--gelen", gelen, "--set", sset, "--uygula"])
    assert io.open(os.path.join(lb, "dow_neg_0001.txt"),
                   encoding="utf-8").read() == "", "negatife kutu yazilmis"


def test_eksik_txt_raporlanir(tmp, capsys):
    sset, gelen = _kur(tmp, {
        "talon5_0001": "0 0.500000 0.500000 0.200000 0.200000\n",
        "talon5_0002": "",
        "talon5_0003": "0 0.1 0.1 0.05 0.05\n",
        "talon5_0004": "0 0.300000 0.300000 0.100000 0.100000\n",
        "dow_neg_0001": "",
    })
    os.remove(os.path.join(gelen, "TALON_ETIKET_01", "veri", "talon_0001.txt"))
    DB.main(["--gelen", gelen, "--set", sset])
    assert "GONDERIDE EKSIK" in capsys.readouterr().out


def test_silinen_kareler_raporlanir_ama_silinmez(tmp, capsys):
    sset, gelen = _kur(tmp, {
        "talon5_0001": "0 0.500000 0.500000 0.200000 0.200000\n",
        "talon5_0002": "",
        "talon5_0003": "0 0.1 0.1 0.05 0.05\n",
        "talon5_0004": "0 0.300000 0.300000 0.100000 0.100000\n",
        "dow_neg_0001": "",
    })
    sil = os.path.join(gelen, "TALON_ETIKET_01", "veri", "_silinen")
    os.makedirs(sil)
    io.open(os.path.join(sil, "talon_0002.jpg"), "w").write(u"x")
    DB.main(["--gelen", gelen, "--set", sset, "--uygula"])
    c = capsys.readouterr().out
    assert "KARE ATILMIS" in c and "talon5_0003" in c
    assert os.path.exists(os.path.join(sset, "labels", "talon5_0003.txt"))


def test_esleme_yoksa_paket_atlanir(tmp, capsys):
    sset, gelen = _kur(tmp, {
        "talon5_0001": "0 0.500000 0.500000 0.200000 0.200000\n",
        "talon5_0002": "",
        "talon5_0003": "0 0.1 0.1 0.05 0.05\n",
        "talon5_0004": "0 0.300000 0.300000 0.100000 0.100000\n",
        "dow_neg_0001": "",
    })
    os.remove(os.path.join(gelen, "TALON_ETIKET_01", "_esleme.json"))
    assert DB.main(["--gelen", gelen, "--set", sset]) == 1
    assert "_esleme.json iceren paket yok" in capsys.readouterr().out

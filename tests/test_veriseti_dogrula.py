# -*- coding: utf-8 -*-
"""veriseti/dogrula.py bicim katmani.

Bu katman, ultralytics'i CAGIRMADAN "etiket bozuk mu?" sorusunu yanitlar.
Sessizce gecen bozuk etiket, egitimde saatler sonra fark edilir -> testler
ozellikle SESSIZ bozulmalari kovaliyor (aralik disi deger, tasan kutu,
sifir alan, bos dosya).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from veriseti.dogrula import satir_dogrula, dosya_dogrula, kutu_alani, disari_aktar


# ------------------------------------------------------------- satir_dogrula
def test_gecerli_satir():
    ok, sebep = satir_dogrula("0 0.500000 0.400000 0.200000 0.250000")
    assert ok and sebep == ""


def test_alan_sayisi_yanlis():
    assert satir_dogrula("0 0.5 0.4 0.2")[0] is False
    assert satir_dogrula("0 0.5 0.4 0.2 0.25 0.9")[0] is False


def test_sinif_tamsayi_olmali():
    """'0.0 ...' YOLO'da sinif alani; float yazilirsa sessiz bozulma olur."""
    assert satir_dogrula("0.0 0.5 0.4 0.2 0.25")[0] is False
    assert satir_dogrula("talon 0.5 0.4 0.2 0.25")[0] is False


def test_aralik_disi_deger():
    assert satir_dogrula("0 1.5 0.4 0.2 0.25")[0] is False
    assert satir_dogrula("0 0.5 -0.1 0.2 0.25")[0] is False


def test_sifir_alanli_kutu():
    assert satir_dogrula("0 0.5 0.4 0.0 0.25")[0] is False
    assert satir_dogrula("0 0.5 0.4 0.2 0.0")[0] is False


def test_kadraj_disina_tasan_kutu_REDDEDILIR():
    """cx=0.05, w=0.30 -> sol kenar -0.10: normalize degerler tek basina
    'araliktaymis' gibi gorunur, kutu yine de tasar."""
    ok, sebep = satir_dogrula("0 0.05 0.5 0.30 0.20")
    assert ok is False and "tasiyor" in sebep


def test_tam_kadraj_kutusu_gecerli():
    assert satir_dogrula("0 0.5 0.5 1.0 1.0")[0] is True


# ------------------------------------------------------------- dosya_dogrula
def test_bos_dosya_BOS_sayilir(tmp_path):
    p = tmp_path / "a.txt"; p.write_text("")
    assert dosya_dogrula(str(p))[0] == "bos"


def test_sadece_bosluk_da_BOS(tmp_path):
    p = tmp_path / "a.txt"; p.write_text("\n  \n")
    assert dosya_dogrula(str(p))[0] == "bos"


def test_gecerli_dosya_ok(tmp_path):
    p = tmp_path / "a.txt"; p.write_text("0 0.5 0.5 0.2 0.2\n")
    durum, satirlar, hatalar = dosya_dogrula(str(p))
    assert durum == "ok" and len(satirlar) == 1 and hatalar == []


def test_cok_nesneli_dosya_ok(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("0 0.3 0.3 0.1 0.1\n0 0.7 0.7 0.1 0.1\n")
    durum, satirlar, _ = dosya_dogrula(str(p))
    assert durum == "ok" and len(satirlar) == 2


def test_tek_bozuk_satir_dosyayi_HATALI_yapar(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("0 0.5 0.5 0.2 0.2\n0 9.9 0.5 0.2 0.2\n")
    durum, _, hatalar = dosya_dogrula(str(p))
    assert durum == "hatali" and len(hatalar) == 1


def test_okunamayan_dosya(tmp_path):
    assert dosya_dogrula(str(tmp_path / "yok.txt"))[0] == "hatali"


def test_kutu_alani():
    assert abs(kutu_alani("0 0.5 0.5 0.2 0.25") - 0.05) < 1e-9


# --------------------------------------------------------------- disari_aktar
def test_disari_aktar_duzeni_ve_bolunmesi(tmp_path):
    kaynak = tmp_path / "ham"; kaynak.mkdir()
    ciftler = []
    for i in range(10):
        png = kaynak / ("talon1_%04d.png" % i); png.write_text("x")
        txt = kaynak / ("talon1_%04d.txt" % i); txt.write_text("0 0.5 0.5 0.2 0.2\n")
        ciftler.append((str(png), str(txt)))
    hedef = tmp_path / "ds"
    bol = disari_aktar(ciftler, str(hedef), val_orani=0.2, tohum=1)
    assert bol["train"] + bol["val"] == 10 and bol["val"] == 2
    for b in ("train", "val"):
        im = hedef / "images" / b
        lb = hedef / "labels" / b
        assert len(list(im.glob("*.png"))) == bol[b]
        assert len(list(lb.glob("*.txt"))) == bol[b]
    yaml = (hedef / "data.yaml").read_text(encoding="utf-8")
    assert "nc: 1" in yaml and "talon" in yaml


def test_disari_aktar_ayni_tohum_ayni_bolme(tmp_path):
    """Bolme TEKRARLANABILIR olmali; yoksa val seti her koşuda degisir ve
    model kiyaslari anlamsizlasir."""
    kaynak = tmp_path / "ham"; kaynak.mkdir()
    ciftler = []
    for i in range(20):
        png = kaynak / ("t_%04d.png" % i); png.write_text("x")
        txt = kaynak / ("t_%04d.txt" % i); txt.write_text("0 0.5 0.5 0.2 0.2\n")
        ciftler.append((str(png), str(txt)))
    a = tmp_path / "a"; b = tmp_path / "b"
    disari_aktar(ciftler, str(a), 0.1, tohum=7)
    disari_aktar(ciftler, str(b), 0.1, tohum=7)
    ad_a = sorted(p.name for p in (a / "images" / "val").glob("*.png"))
    ad_b = sorted(p.name for p in (b / "images" / "val").glob("*.png"))
    assert ad_a == ad_b

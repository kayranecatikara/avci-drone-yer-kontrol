# -*- coding: utf-8 -*-
"""kopru/gorsel_ozellikler.py — panel anahtarlari (bbox_ibvs.Cfg / SupCfg).

NEDEN: kaynak CLAUDE.md §5 kurali — sisteme eklenen HER davranis anahtarinin
panelde ac/kapa dugmesi olacak. Bu testler mekanizmanin CANLI yazdigini ve
yasa dosyalarina DOKUNMADIGINI kilitler. Oyun GEREKMEZ.
"""
import pytest

from kopru import gorsel_ozellikler as goz


def _yasa():
    bi, sup = goz._moduller()
    if bi is None:
        pytest.skip("yasa modulu yok (kopru/gazebo_kaynak)")
    return bi, sup


def test_liste_dolu_ve_alanlari_tam():
    L = goz.hepsi()
    assert len(L) >= 10
    for o in L:
        assert set(o) >= {"anahtar", "modul", "tur", "alt", "ust",
                          "etiket", "aciklama", "deger"}
        assert o["tur"] in ("bool", "float", "int")
        assert o["etiket"] and o["aciklama"]


def test_bool_anahtar_canli_yazar():
    bi, _ = _yasa()
    eski = bi.Cfg.DIKEY_ROLL
    try:
        assert goz.ayarla("DIKEY_ROLL", 1) == (True, None)
        assert bi.Cfg.DIKEY_ROLL is True
        assert goz.ayarla("DIKEY_ROLL", 0) == (False, None)
        assert bi.Cfg.DIKEY_ROLL is False
    finally:
        bi.Cfg.DIKEY_ROLL = eski


def test_float_anahtar_canli_yazar():
    bi, _ = _yasa()
    eski = bi.Cfg.KACIS_KD
    try:
        v, hata = goz.ayarla("KACIS_KD", 1.25)
        assert hata is None and v == pytest.approx(1.25)
        assert bi.Cfg.KACIS_KD == pytest.approx(1.25)
    finally:
        bi.Cfg.KACIS_KD = eski


def test_supervisor_anahtari_canli_yazar():
    _, sup = _yasa()
    eski = sup.SupCfg.KAYIP_M
    try:
        assert goz.ayarla("KAYIP_M", 60) == (60, None)
        assert sup.SupCfg.KAYIP_M == 60
    finally:
        sup.SupCfg.KAYIP_M = eski


def test_supervisor_ve_ibvs_AYNI_cfg_nesnesi():
    """Kaynagin dogruladigi varsayim: IbvsCfg is bbox_ibvs.Cfg. Bu bozulursa
    panel gorsel yasayi degistirir ama supervisor eski degeri gorur."""
    bi, sup = _yasa()
    assert sup.IbvsCfg is bi.Cfg


def test_aralik_disi_deger_KIRPILIR():
    bi, _ = _yasa()
    eski = bi.Cfg.YANAL_K
    try:
        v, hata = goz.ayarla("YANAL_K", 999.0)
        assert hata is None and v == pytest.approx(6.0)      # ust sinira kirpildi
        v, hata = goz.ayarla("YANAL_K", -5.0)
        assert hata is None and v == pytest.approx(0.0)      # alt sinira kirpildi
    finally:
        bi.Cfg.YANAL_K = eski


def test_bilinmeyen_anahtar_REDDEDILIR():
    v, hata = goz.ayarla("BOYLE_BIR_SEY_YOK", 1)
    assert v is None and "bilinmeyen" in hata


def test_gecersiz_deger_REDDEDILIR():
    v, hata = goz.ayarla("KACIS_KD", "abc")
    assert v is None and "gecersiz" in hata


def test_varsayilanlar_KAYNAKLA_AYNI():
    """Senkron sonrasi varsayilanlar dalin HEAD'iyle ayni olmali (UYGULANACAK.md):
    T1a ACIK (M1 ucusta dogrulandi), gerisi KAPALI."""
    bi, _ = _yasa()
    import importlib
    importlib.reload(bi)                      # env'siz taze varsayilanlar
    assert bi.Cfg.ROLL_TELAFI is True         # M1 — ucusta dogrulandi
    assert bi.Cfg.LEAD_ERKEN is False         # M3 — notr
    assert bi.Cfg.DIKEY_ROLL is False         # T1b — UCULMADI
    assert bi.Cfg.KACIS_KD == 0.0             # O1
    assert bi.Cfg.YANAL_K == 0.0              # O8
    assert bi.Cfg.SONUM_T == 0.0              # O9
    assert bi.Cfg.DONUS_A == 0.0              # O5

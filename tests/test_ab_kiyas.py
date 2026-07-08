# -*- coding: utf-8 -*-
"""
arac/ab_kiyas.py analiz testleri (sim/oyun/server GEREKMEZ — sentetik JSONL).
Calistirma:  python test/test_ab_kiyas.py
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "arac"))

import ab_kiyas


def _yaz(dosya, satirlar):
    with open(dosya, "w", encoding="utf-8") as f:
        for s in satirlar:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")


def _tik(t, **ek):
    """Taban telemetri tiki (bizim/main ortak sozlesme); ek ile alan ezilir."""
    s = {"t": t, "connected": True,
         "gorev": {"faz": "YAKLASMA", "vurus": False, "basari": False, "en_yakin_m": None},
         "gorsel": {"gps_kesildi": False},
         "takip": {"aktif": False, "id": None},
         "gnss": {"kesinti": False}}
    for k, v in ek.items():
        if isinstance(v, dict) and isinstance(s.get(k), dict):
            s[k].update(v)
        else:
            s[k] = v
    return s


def test_basarili_kosu():
    tmp = tempfile.mkdtemp()
    dosya = os.path.join(tmp, "kosu_a.jsonl")
    satirlar = [
        _tik(0.0),
        _tik(10.0, gnss={"kesinti": True}),                      # kesinti epizodu basi
        _tik(12.0, gnss={"kesinti": True}),
        _tik(14.0),                                              # kesinti bitti
        _tik(30.0, gorsel={"gps_kesildi": True},                 # gorsel faza gecis
             takip={"aktif": True, "id": 3}),
        _tik(35.0, gorsel={"gps_kesildi": True, "kilit": {"kumulatif_sn": 2.0}},
             takip={"aktif": True, "id": 3}),
        _tik(36.0, gorsel={"gps_kesildi": True, "kilit": {"kumulatif_sn": 2.4}},
             takip={"aktif": False, "id": 3}),                   # takip kaybi (1)
        _tik(38.0, gorsel={"gps_kesildi": True, "kilit": {"kumulatif_sn": 5.2}},
             takip={"aktif": True, "id": 7}),                    # yeni ID (toplam 2)
        _tik(50.0, gorev={"vurus": True, "en_yakin_m": 0.8},
             takip={"aktif": True, "id": 7},
             olay_yeni=[{"id": 9, "m": "VURUS! mesafe=0.8 m (gercek kaynak)"}]),
        _tik(53.5, gorev={"vurus": True, "basari": True, "en_yakin_m": 0.8},
             takip={"aktif": True, "id": 7}),
    ]
    _yaz(dosya, satirlar)
    m = ab_kiyas.analiz_kosu(dosya)
    assert m["basari"] is True and m["vurus"] is True
    assert abs(m["vurus_t_s"] - 50.0) < 1e-9
    assert abs(m["en_yakin_m"] - 0.8) < 1e-9
    assert m["mesafe_kaynak"] == "gercek"
    assert abs(m["gorsel_gecis_t_s"] - 30.0) < 1e-9
    assert abs(m["kilit_kum_max_s"] - 5.2) < 1e-9
    assert m["takip_kayip"] == 1
    assert m["takip_id_sayisi"] == 2
    assert m["gnss_kesinti_epizot"] == 1
    assert 0.0 < m["gnss_kesinti_oran"] < 1.0
    assert abs(m["sure_s"] - 53.5) < 1e-9
    print("  OK basarili kosu (vurus/kaynak/kilit/takip/kesinti)")


def test_main_tarzi_kilitsiz_iska():
    """main telemetrisinde 'kilit' yok; vurus da yok (timeout/iska) -> None'lar."""
    tmp = tempfile.mkdtemp()
    dosya = os.path.join(tmp, "kosu_b.jsonl")
    satirlar = [
        _tik(0.0),
        _tik(20.0, gorsel={"gps_kesildi": True}, takip={"aktif": True, "id": 1},
             gorev={"en_yakin_m": 6.4}),
        _tik(40.0, gorsel={"gps_kesildi": True}, takip={"aktif": True, "id": 1},
             gorev={"en_yakin_m": 3.1}),
    ]
    _yaz(dosya, satirlar)
    m = ab_kiyas.analiz_kosu(dosya)
    assert m["basari"] is False and m["vurus"] is False and m["vurus_t_s"] is None
    assert m["kilit_kum_max_s"] is None            # gosterge yok -> None (0 degil)
    assert m["mesafe_kaynak"] is None
    assert abs(m["en_yakin_m"] - 3.1) < 1e-9
    assert m["takip_kayip"] == 0 and m["takip_id_sayisi"] == 1
    print("  OK main-tarzi kosu (kilit gostergesiz, iska)")


def test_bos_ve_bozuk_satir():
    tmp = tempfile.mkdtemp()
    bos = os.path.join(tmp, "kosu_bos.jsonl")
    open(bos, "w").close()
    assert ab_kiyas.analiz_kosu(bos) is None
    yarim = os.path.join(tmp, "kosu_yarim.jsonl")
    with open(yarim, "w", encoding="utf-8") as f:
        f.write(json.dumps(_tik(1.0)) + "\n")
        f.write('{"t": 2.0, "gorev": {"vur')          # kopma aninda yarim satir
    m = ab_kiyas.analiz_kosu(yarim)
    assert m is not None and abs(m["sure_s"] - 1.0) < 1e-9
    print("  OK bos dosya None; yarim satir atlanir")


def test_ozet_medyan_ve_none():
    ms = [
        {"basari": True, "vurus": True, "vurus_t_s": 50.0, "en_yakin_m": 0.8,
         "mesafe_kaynak": "gercek", "gorsel_gecis_t_s": 30.0, "kilit_kum_max_s": 5.2,
         "takip_kayip": 1, "takip_id_sayisi": 2, "gnss_kesinti_oran": 0.2},
        {"basari": False, "vurus": False, "vurus_t_s": None, "en_yakin_m": 3.1,
         "mesafe_kaynak": None, "gorsel_gecis_t_s": 20.0, "kilit_kum_max_s": None,
         "takip_kayip": 0, "takip_id_sayisi": 1, "gnss_kesinti_oran": 0.0},
    ]
    o = ab_kiyas._ozet(ms)
    assert o["n"] == 2 and o["basari"] == 1 and o["vurus"] == 1
    assert abs(o["vurus_t_med_s"] - 50.0) < 1e-9      # None'lar medyana girmez
    assert abs(o["en_yakin_med_m"] - 1.95) < 1e-9
    assert abs(o["kilit_kum_med_s"] - 5.2) < 1e-9
    assert o["kaynaklar"] == ["gercek"]
    print("  OK ozet (None-dayanikli medyanlar)")


if __name__ == "__main__":
    print("test_ab_kiyas:")
    test_basarili_kosu()
    test_main_tarzi_kilitsiz_iska()
    test_bos_ve_bozuk_satir()
    test_ozet_medyan_ve_none()
    print("SONUC: TUM TESTLER GECTI")

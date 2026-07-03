# -*- coding: utf-8 -*-
"""
Madde 6-7: harici hedef-kaynagi disi (ana_kontrol.set_hedef_kaynagi) +
web/dev_truth.DevTruthKaynagi sentetik dogrulamasi (sim GEREKMEZ).
Calistirma:  python test/test_dev_kaynak.py
"""
import os
import sys

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from guidance.ana_kontrol import AvciKontrol, Cfg, lead_kelepce   # noqa: E402
from web.dev_truth import DevTruthKaynagi              # noqa: E402


class SahteDrone:
    """AvciKontrol/DevTruthKaynagi'nin dokundugu SDK yuzeyinin sahtesi."""

    def __init__(self):
        self.ham = (100.0, 200.0, 300.0)
        self.dbg = {"available": False,
                    "target": {"position": (0.0, 0.0, 0.0)}}

    def get_target_location(self):
        return self.ham

    def get_debug_truth(self):
        return dict(self.dbg)


def test_dikis_takilir_ve_cikarilir():
    d = SahteDrone()
    b = AvciKontrol(d)
    assert b.hedef_kaynak_ad == "filtre" and b._hedef_kaynak_fn is None

    # 1) fn takili: hedef durumu dogrudan fn'den, filtre atlanir
    fn_deger = {"pos": (1000.0, 2000.0, 5000.0), "vel": (-500.0, 0.0, 10.0)}
    b.set_hedef_kaynagi(lambda: fn_deger, "sahte")
    out = b._hedef_temizle()
    assert b._fresh is True
    assert np.allclose(out, [1000.0, 2000.0, 5000.0])
    assert float(b.son_z_anlik) == 5000.0
    assert np.allclose(b.son_xy_anlik, [1000.0, 2000.0])
    assert np.allclose(b.son_hiz, [-500.0, 0.0, 10.0])
    assert b.hedef_kaynak_ad == "sahte"

    # 2) fn None dondururse: fresh dusmez ama son kestirim korunur (hold yolu)
    fn_deger = None
    b._hedef_kaynak_fn = lambda: fn_deger
    b._hedef_temizle()
    assert b._fresh is False and b.son_temiz is not None

    # 3) cikarilinca: uretim yolu, taze filtre, etiket "filtre"
    eski_filtre = b.filtre
    b.set_hedef_kaynagi(None, "filtre")
    assert b._hedef_kaynak_fn is None
    assert b.hedef_kaynak_ad == "filtre"
    assert b.filtre is not eski_filtre                 # taze soft-start
    assert b.son_temiz is None and b._fresh is False


def test_dev_truth_kaynagi():
    d = SahteDrone()
    saat = [0.0]
    dev = DevTruthKaynagi(d, saat=lambda: saat[0])
    b = AvciKontrol(d)

    # truth AKMIYOR: gercek moda gecis reddedilir
    ok, msg = dev.uygula(b, "gercek")
    assert ok is False and "AKMIYOR" in msg
    assert dev._fn() is None
    assert b.hedef_kaynak_ad == "filtre"

    # truth AKIYOR ve ham'la TUTARLI (bozuk GPS ~30 m sapmis): gecis olur
    d.dbg = {"available": True, "target": {"position": (10000.0, 0.0, 7000.0)}}
    d.ham = (10020.0, 2800.0, 7150.0)               # truth'a yakin (fark ~28 m)
    ok, msg = dev.uygula(b, "gercek")
    assert ok is True
    assert b.hedef_kaynak_ad == "gercek" and b._hedef_kaynak_fn is not None
    b._hedef_temizle()
    assert np.allclose(b.son_temiz, [10000.0, 0.0, 7000.0]) and b._fresh

    # hiz: 0.1 sn sonra hedef +100 cm x -> EMA = 0.3 * (100/0.1) = 300 cm/s
    saat[0] = 0.1
    d.dbg = {"available": True, "target": {"position": (10100.0, 0.0, 7000.0)}}
    b._hedef_temizle()
    assert abs(float(b.son_hiz[0]) - 300.0) < 1e-6, b.son_hiz
    assert abs(float(b.son_hiz[1])) < 1e-9

    # durum() arayuz ozeti + filtreye donus
    st = dev.durum(b)
    assert st == {"var": True, "aktif": True, "akiyor": True}
    ok, msg = dev.uygula(b, "filtre")
    assert ok is True and b.hedef_kaynak_ad == "filtre" and b._hedef_kaynak_fn is None
    assert dev.durum(b)["aktif"] is False

    # truth kesilirse fn None -> beyin hold/dropout yoluna duser (kor kalinmaz)
    dev.uygula(b, "gercek")
    d.dbg = {"available": False, "target": {"position": (0.0, 0.0, 0.0)}}
    b._hedef_temizle()
    assert b._fresh is False


def test_gecis_tutarlilik_kapisi():
    """Birim/indeks/eksen hatasi: truth ham'la bagdasmiyorsa gecis REDDEDILIR."""
    d = SahteDrone()
    dev = DevTruthKaynagi(d, saat=lambda: 0.0)
    b = AvciKontrol(d)
    # 'metre truth' senaryosu: truth = ham/100 -> oran ~0.01, fark ~%99|ham|
    d.ham = (10000.0, 5000.0, 7000.0)
    d.dbg = {"available": True, "target": {"position": (100.0, 50.0, 70.0)}}
    ok, msg = dev.uygula(b, "gercek")
    assert ok is False and "REDDEDILDI" in msg, msg
    assert b.hedef_kaynak_ad == "filtre" and b._hedef_kaynak_fn is None
    # indeks kaymasi / baska nesne: dogru olcek ama 5 km otede -> fark kapisi
    d.dbg = {"available": True, "target": {"position": (510000.0, 5000.0, 7000.0)}}
    ok, msg = dev.uygula(b, "gercek")
    assert ok is False and "REDDEDILDI" in msg, msg
    # hiz kelepcesi: tek karelik 100 m sicrama EMA'da 40 m/s'yi ASAMAZ
    saat = [0.0]
    dev2 = DevTruthKaynagi(d, saat=lambda: saat[0])
    d.dbg = {"available": True, "target": {"position": (10000.0, 5000.0, 7000.0)}}
    dev2._fn()
    saat[0] = 0.02
    d.dbg = {"available": True, "target": {"position": (20000.0, 5000.0, 7000.0)}}
    hd = dev2._fn()
    assert abs(hd["vel"][0]) <= dev2.V_KELEPCE + 1e-9, hd["vel"]


def test_lead_kelepce():
    """Saf kelepce: sinir icinde dokunmaz, disinda kureye kirpar."""
    anlik = np.array([0.0, 0.0, 5000.0])
    yakin = np.array([3000.0, 0.0, 5000.0])
    kirp, asildi = lead_kelepce(anlik, yakin, Cfg.LEAD_MAX_CM)
    assert not asildi and np.allclose(kirp, yakin)
    uzak = np.array([100000.0, 0.0, 5000.0])          # 1 km otede lead
    kirp, asildi = lead_kelepce(anlik, uzak, Cfg.LEAD_MAX_CM)
    assert asildi
    assert abs(np.linalg.norm(kirp - anlik) - Cfg.LEAD_MAX_CM) < 1e-6
    assert np.allclose((kirp - anlik) / np.linalg.norm(kirp - anlik),
                       (uzak - anlik) / np.linalg.norm(uzak - anlik))  # yon korunur


if __name__ == "__main__":
    test_dikis_takilir_ve_cikarilir()
    print("OK  test_dikis_takilir_ve_cikarilir")
    test_dev_truth_kaynagi()
    print("OK  test_dev_truth_kaynagi")
    test_gecis_tutarlilik_kapisi()
    print("OK  test_gecis_tutarlilik_kapisi")
    test_lead_kelepce()
    print("OK  test_lead_kelepce")
    print("TUM TESTLER GECTI (4)")

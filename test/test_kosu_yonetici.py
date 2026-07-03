# -*- coding: utf-8 -*-
"""
arac/kosu_yonetici.py sim'siz birim testleri (oyun/TCP GEREKMEZ).
Calistirma:  python test/test_kosu_yonetici.py
Kapsam: tur kaydi butunlugu, surec bulma (sahte psutil), kapanis bildirimi,
zombilesme protokolu KARARI (fn cagrisi sahte, oyun cagrilari sayilir)."""
import os
import sys
import types

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "arac"))

import kosu_yonetici as ky


def test_tur_kaydi_butunluk():
    for ad, (fn, ucuslu, acik) in ky.TUR_KAYDI.items():
        assert callable(fn), ad
        assert isinstance(ucuslu, bool), ad
        assert isinstance(acik, str) and acik, ad
    # bugunku turlerin hepsi arm'siz (ucuslu FAZ 1'de eklenecek)
    assert all(not v[1] for v in ky.TUR_KAYDI.values())
    assert set(ky.TUR_KAYDI) >= {"hakem", "k-sanity", "filtre"}


def test_surec_bulma(monkeypatch_yok=True):
    # psutil'i sahtele: iki DronesOfWar + bir baska surec
    sahte = types.ModuleType("psutil")

    class _P:
        def __init__(self, ad):
            self.info = {"name": ad}
            self.killed = False
            self.terminated = False

        def terminate(self):
            self.terminated = True

        def kill(self):
            self.killed = True

    procs = [_P("DronesOfWar.exe"), _P("chrome.exe"), _P("DronesOfWar-Win64-Shipping.exe")]
    sahte.process_iter = lambda attrs=None: procs
    sahte.wait_procs = lambda ps, timeout=0: (ps, [])       # hepsi terminate ile gitti
    sys.modules["psutil"] = sahte
    try:
        bulunan = ky._oyun_surecleri()
        assert len(bulunan) == 2, [p.info for p in bulunan]
        assert ky.oyun_calisiyor_mu() is True
        ky.oyunu_kapat()
        assert all(p.terminated for p in bulunan)           # ikisi de terminate edildi
    finally:
        del sys.modules["psutil"]


def test_exe_adaylari_mutlak():
    assert len(ky.EXE_ADAYLARI) >= 2
    for e in ky.EXE_ADAYLARI:
        assert os.path.isabs(e) and e.endswith("DronesOfWar.exe"), e


def test_kapanis_bildirim_cokmez():
    # bip/başlık cagrilari platform API'siz de cokmemeli (fallback)
    ky.kosu_bitti_bildir("test -> OK")     # istisna atmamali


def test_zombilesme_karari():
    # tur_yurut'un oyun-yasam-dongusu dallari: fn ve oyun cagrilarini sahtele,
    # ucuslu tur SONRASI restart (kapat+baslat) cagriliyor mu?
    izler = []
    orij = (ky.oyunu_baslat, ky.oyunu_kapat, ky.baglan_ve_bekle, ky.kosu_bitti_bildir)
    ky.oyunu_baslat = lambda: (izler.append("baslat"), (True, None))[1]
    ky.oyunu_kapat = lambda: izler.append("kapat")
    ky.baglan_ve_bekle = lambda play_bekle_s=120.0: types.SimpleNamespace(
        disconnect=lambda: None)
    ky.kosu_bitti_bildir = lambda s: izler.append("bildir")
    ky.TUR_KAYDI["_ucuslu_test"] = (lambda d, a: (True, "ok"), True, "test ucuslu")
    ky.TUR_KAYDI["_armsiz_test"] = (lambda d, a: (True, "ok"), False, "test armsiz")
    try:
        arg = types.SimpleNamespace(sure=0.0, oyunu_acik_birak=False, oyun_hazir=False)
        izler.clear()
        ky.tur_yurut("_ucuslu_test", arg)
        # ucuslu: baslat(ilk) -> ... -> kapat+baslat(restart). En az iki baslat + bir kapat.
        assert izler.count("baslat") == 2 and izler.count("kapat") == 1, izler
        izler.clear()
        ky.tur_yurut("_armsiz_test", arg)
        # arm'siz + biz actik: baslat(ilk) -> kapat(temiz). Restart YOK.
        assert izler.count("baslat") == 1 and izler.count("kapat") == 1, izler
        # arm'siz + oyunu-acik-birak: kapat YOK
        arg2 = types.SimpleNamespace(sure=0.0, oyunu_acik_birak=True, oyun_hazir=False)
        izler.clear()
        ky.tur_yurut("_armsiz_test", arg2)
        assert izler.count("kapat") == 0, izler
    finally:
        ky.oyunu_baslat, ky.oyunu_kapat, ky.baglan_ve_bekle, ky.kosu_bitti_bildir = orij
        del ky.TUR_KAYDI["_ucuslu_test"], ky.TUR_KAYDI["_armsiz_test"]


if __name__ == "__main__":
    for ad, fn in sorted(globals().items()):
        if ad.startswith("test_"):
            fn()
            print("OK  %s" % ad)
    print("TUM TESTLER GECTI")

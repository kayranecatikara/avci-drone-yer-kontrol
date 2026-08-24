# -*- coding: utf-8 -*-
"""KilitSayaci — sartname 6.1.2/6.1.4 kilit isteri sayaci (SALT GOZLEM).

Eski `ana_kontrol._kilit_degerlendir`'in yerini alir; testler o davranisi
kilitler: AV bandi, boyut esigi, 10 sn pencere / 5 sn kumulatif, latch,
GPS fazinda saymama, bosluk atlanmasi.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from guidance.kilit_sayaci import KilitSayaci, KilitCfg  # noqa: E402

W, H = 1920.0, 1080.0


def det(cxn, cyn, boyut):
    """Normalize konum/boyuttan tam-kare piksel tespiti."""
    return {"cx": cxn * W, "cy": cyn * H, "w": boyut * W, "h": boyut * H,
            "W": W, "H": H}


def test_merkezde_buyuk_kutu_kilit():
    s = KilitSayaci()
    assert s.guncelle(det(0.5, 0.5, 0.10), 0.0) is True
    assert s.anlik is True
    assert abs(s.boyut - 0.10) < 1e-9


def test_av_disinda_kilit_yok():
    s = KilitSayaci()
    assert s.guncelle(det(0.10, 0.5, 0.10), 0.0) is False   # yatay AV disi
    assert s.guncelle(det(0.5, 0.03, 0.10), 0.1) is False   # dikey AV disi


def test_kucuk_kutu_kilit_yok():
    s = KilitSayaci()
    assert s.guncelle(det(0.5, 0.5, 0.03), 0.0) is False    # %3 < esik %6


def test_esik_tam_sinirda_kilit():
    s = KilitSayaci()
    assert s.guncelle(det(0.5, 0.5, KilitCfg.LOCK_PCT), 0.0) is True


def test_tespit_yok_kilit_yok():
    s = KilitSayaci()
    assert s.guncelle(None, 0.0) is False
    assert s.boyut is None


def test_gps_fazinda_saymaz():
    s = KilitSayaci()
    assert s.guncelle(det(0.5, 0.5, 0.10), 0.0, gorsel_faz=False) is False


def test_bes_saniye_kumulatif_latch():
    s = KilitSayaci()
    t = 0.0
    while t < 6.0:                      # 0.1 s adimlarla surekli kilit
        s.guncelle(det(0.5, 0.5, 0.10), t)
        t += 0.1
    assert s.ok is True
    assert s.sure >= KilitCfg.WIN_NEED_S


def test_latch_kalici():
    s = KilitSayaci()
    t = 0.0
    while t < 6.0:
        s.guncelle(det(0.5, 0.5, 0.10), t); t += 0.1
    assert s.ok is True
    for _ in range(50):                 # sonra hic tespit yok
        s.guncelle(None, t); t += 0.1
    assert s.ok is True                 # latch DUSMEZ
    assert s.anlik is False


def test_yetersiz_sure_latch_yok():
    s = KilitSayaci()
    t = 0.0
    while t < 3.0:                      # 3 s < gereken 5 s
        s.guncelle(det(0.5, 0.5, 0.10), t); t += 0.1
    assert s.ok is False


def test_buyuk_bosluk_kumulatife_sayilmaz():
    s = KilitSayaci()
    s.guncelle(det(0.5, 0.5, 0.10), 0.0)
    s.guncelle(det(0.5, 0.5, 0.10), 2.0)     # 2 s bosluk > BOSLUK_MAX_S
    assert s.sure == 0.0


def test_pencere_kayiyor():
    s = KilitSayaci()
    t = 0.0
    while t < 6.0:
        s.guncelle(det(0.5, 0.5, 0.10), t); t += 0.1
    ilk = s.sure
    while t < 20.0:                     # 10 s pencere disina cikar
        s.guncelle(None, t); t += 0.1
    assert s.sure < ilk                 # kumulatif dustu
    assert s.ok is True                 # ama latch korunur


def test_sifirla_latch_dahil_temizler():
    s = KilitSayaci()
    t = 0.0
    while t < 6.0:
        s.guncelle(det(0.5, 0.5, 0.10), t); t += 0.1
    assert s.ok is True
    s.sifirla()
    assert s.ok is False and s.sure == 0.0 and s.anlik is False and not s.win


def test_durum_sozlugu():
    s = KilitSayaci()
    s.guncelle(det(0.5, 0.5, 0.10), 0.0)
    d = s.durum()
    assert set(d) == {"anlik", "sure", "ok", "boyut_pct", "esik_pct",
                      "pencere_s", "gereken_s"}
    assert d["anlik"] is True
    assert abs(d["boyut_pct"] - 10.0) < 0.2
    assert d["gereken_s"] == KilitCfg.WIN_NEED_S


def test_bozuk_tespit_cokmez():
    s = KilitSayaci()
    assert s.guncelle({"cx": "x", "cy": 1, "w": 1, "h": 1, "W": W, "H": H}, 0.0) is False
    assert s.guncelle({"cx": 1, "cy": 1}, 0.1) is False      # W/H yok
    assert s.guncelle({"cx": 1, "cy": 1, "w": 1, "h": 1, "W": 0, "H": 0}, 0.2) is False

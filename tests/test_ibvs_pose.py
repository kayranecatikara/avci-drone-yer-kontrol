# -*- coding: utf-8 -*-
"""
POZ-MESAFELI ILERI HIZ PROFILI — saf matematik testleri (silinen tasarimin
geri eklenmesi; senaryolar bayat .pyc'den kurtarilan 8 test adinin yeniden yazimi).

Kural: poz mesafesi VARKEN ve bayrak ACIKKEN ileri hiz GERCEK metreden hesaplanir
(dogrusal profil: >=SLOW_M tam K_FWD, <=STOP_M 0); poz YOKKEN / bayrak KAPALIYKEN
genislik yasasi BIREBIR gecerli. Poz YALNIZ ileriyi etkiler (yaw/throttle bagimsiz).

Kosum (repo kokunden):  python -m pytest tests/test_ibvs_pose.py -q
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from guidance.ibvs_guidance import AvciGorselGuduum  # noqa: E402


class P:
    VIS_EMA         = 0.4
    VIS_EY_REF      = 0.43
    VIS_ATT_COMP    = 1.0
    VIS_CAM_TILT_DEG = 25.0
    VIS_HFOV_DEG    = 125.0
    VIS_SIGN_YAW    = +1.0
    VIS_SIGN_VZ     = -1.0
    VIS_SIGN_PITCH  = +1.0
    VIS_SIGN_ROLL   = +1.0
    VIS_K_YAW       = 0.5
    VIS_K_ROLL      = 0.0
    VIS_K_VZ        = 2.0
    VIS_VZ_MAX      = 1100.0
    VIS_KV_Z        = 0.0020
    VIS_ALC_MIN     = 0.5
    VIS_K_FWD       = 0.4
    VIS_FWD_MAX     = 0.5
    VIS_CENTER_GATE = 0.35
    VIS_W_STOP      = 0.30
    VIS_USE_POSE_DIST = 0.0     # taban sinif: bayrak KAPALI
    VIS_DIST_SLOW_M = 12.0
    VIS_DIST_STOP_M = 4.0
    THR_DN          = -1.00
    THR_UP          = 0.70
    VZ_MAX          = 3333.0


class PPoz(P):
    VIS_USE_POSE_DIST = 1.0     # bayrak ACIK


W, H = 1280.0, 720.0
BBW, BBH = 0.10 * W, 0.08 * H
FWD_GENISLIK = P.VIS_K_FWD * (1.0 - 0.10 / P.VIS_W_STOP)   # genislik yasasi = 0.26667
NY_REF = (1.0 + P.VIS_EY_REF) / 2.0                        # REF hizasi (eyd~0, kisma yok)


def cmd(p=P, poz_cm=None, ny=NY_REF, nx=0.5, vz=0.0):
    g = AvciGorselGuduum()
    return g.hesapla((nx * W, ny * H), W, H, (BBW, BBH), p,
                     vz=vz, pitch_deg=0.0, det_t=1.0, poz_cm=poz_cm)


def test_poz_uzakta_tam_hiz():
    _, pitch, _, _ = cmd(p=PPoz, poz_cm=2000.0)             # 20 m >= SLOW_M
    assert pitch == pytest.approx(P.VIS_K_FWD)              # tam K_FWD (genislikten bagimsiz)


def test_poz_stop_mesafesinde_durur():
    _, pitch, _, _ = cmd(p=PPoz, poz_cm=400.0)              # 4 m = STOP_M
    assert pitch == pytest.approx(0.0)


def test_poz_arada_dogrusal():
    _, pitch, _, _ = cmd(p=PPoz, poz_cm=800.0)              # 8 m: (8-4)/(12-4) = 0.5
    assert pitch == pytest.approx(0.5 * P.VIS_K_FWD)


def test_poz_yoksa_genislik_yasasi():
    _, pitch, _, _ = cmd(p=PPoz, poz_cm=None)               # bayrak acik ama poz yok -> fallback
    assert pitch == pytest.approx(FWD_GENISLIK)


def test_bayrak_kapaliyken_poz_yok_sayilir():
    _, pitch, _, _ = cmd(p=P, poz_cm=400.0)                 # bayrak KAPALI -> genislik yasasi
    assert pitch == pytest.approx(FWD_GENISLIK)


def test_merkez_kapisi_poz_profilinde_de_gecerli():
    _, pitch, _, _ = cmd(p=PPoz, poz_cm=2000.0, nx=0.9)     # |ex|=0.8 > kapi
    assert pitch == 0.0


def test_kor_devam_son_pozu_tasir():
    g = AvciGorselGuduum()
    g.hesapla((0.5 * W, NY_REF * H), W, H, (BBW, BBH), PPoz,
              pitch_deg=0.0, det_t=1.0, poz_cm=800.0)
    _, pitch, _, _ = g.kor_devam(PPoz)
    assert pitch == pytest.approx(0.5 * P.VIS_K_FWD)        # donmus poz snapshot'i tasindi


def test_yaw_throttle_pozdan_etkilenmez():
    sonuc = {}
    for ad, poz in (("yok", None), ("yakin", 400.0), ("uzak", 2000.0)):
        thr, _, _, yaw = cmd(p=PPoz, poz_cm=poz, ny=0.815, nx=0.9)
        sonuc[ad] = (thr, yaw)
    assert sonuc["yok"] == pytest.approx(sonuc["yakin"])
    assert sonuc["yok"] == pytest.approx(sonuc["uzak"])
    assert sonuc["yok"][1] == pytest.approx(0.5 * 0.8)      # yaw = K_YAW * ex

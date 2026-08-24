# -*- coding: utf-8 -*-
"""TERMINAL KAPANMA PAYI (bbox_ibvs.Cfg.TERM_PAY) testleri.

NEDEN: V_TERMINAL=18 m/s'in gerekcesi "hedef 14.5 m/s" varsayiyordu.
BAGIMSIZ OLCUM (2026-08-19, debug.target_real turevi, n=353):
    gercek hedef hizi medyan 17.93 m/s  (p10 15.52 / p90 20.44)
    avci hizi p90 24.67, maks 26.68     -> pay MEVCUT ama kullanilmiyor
Yani terminalde kapanma payi ~0; canli izlemede menzil 3-4 m'de dip yapip
dr/dt pozitife donuyor (son metreler kapanmiyor).

TERM_PAY hucum hizini yasanin KENDI gorsel kestirimi `hiz_I` uzerine sabit
pay olarak tanimlar -> senaryo bagimsiz.
"""
import os
import sys

import pytest

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
sys.path.insert(0, os.path.join(KOK, "kopru", "gazebo_kaynak"))

from control.guidance.bbox_ibvs import Cfg  # noqa: E402


def _clamp(v, a, b):
    return max(a, min(b, v))


def _vlos(hiz_I, pay, v_term=18.0, v_min=10.0, v_max=24.0):
    """Terminal dalin BIREBIR kopyasi."""
    v = v_term
    if pay > 0.0:
        v = _clamp(max(v, hiz_I + pay), v_min, v_max)
    return v


def test_KAPALIYKEN_eski_davranis():
    assert _vlos(17.9, 0.0) == 18.0
    assert _vlos(5.0, 0.0) == 18.0


def test_OLCULEN_DURUMU_DUZELTIR():
    """⭐ Hedef 17.93 m/s -> hucum 18 ise kapanma ~0. Pay 3.5 ile 21.4 olmali."""
    v = _vlos(17.93, 3.5)
    assert v == pytest.approx(21.43, abs=0.01)
    assert v - 17.93 == pytest.approx(3.5, abs=0.01), "kapanma payi yok"


def test_ASLA_V_TERMINALIN_ALTINA_INMEZ():
    """Yavas hedefte bile mevcut davranistan kotu olamaz."""
    for h in (0.0, 5.0, 12.0, 14.4):
        assert _vlos(h, 3.5) >= 18.0


def test_HIZLI_HEDEFTE_de_pay_birakir():
    """Senaryo genellemesi: hedef 25 m/s olsa sabit 18 yetmezdi."""
    v = _vlos(25.0, 3.5, v_max=32.0)
    assert v == pytest.approx(28.5, abs=0.01)


def test_V_TOPLAM_MAX_asilmaz():
    assert _vlos(40.0, 3.5, v_max=24.0) == 24.0


def test_varsayilan_KAPALI():
    assert float(getattr(Cfg, "TERM_PAY", 0.0)) == 0.0 or \
        os.environ.get("AVCI_IBVS_TERM_PAY"), "varsayilan ACIK gelmis"


def test_kaynak_ifadesi_AYNI():
    yol = os.path.join(KOK, "kopru", "gazebo_kaynak", "control",
                       "guidance", "bbox_ibvs.py")
    s = open(yol, encoding="utf-8").read()
    assert "TERM_PAY" in s
    assert "max(v_los, hiz_I + _tp)" in s


def test_V_TERMINAL_gerekcesi_KODA_ISLENDI():
    """Gerekcenin gecersizligi kodda yaziyor olmali (yoksa tekrar tuzaga duseriz)."""
    yol = os.path.join(KOK, "kopru", "gazebo_kaynak", "control",
                       "guidance", "bbox_ibvs.py")
    s = open(yol, encoding="utf-8").read()
    assert "17.9" in s or "17.93" in s, "olculen gercek hedef hizi kodda yok"

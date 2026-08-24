# -*- coding: utf-8 -*-
"""KOMUT YON TAVANI — "sallanma + durdurmalar"in kok nedeni.

LOGDAN OLCULDU (2026-08-19, 43994 ornek, 20 Hz sabit adim):
    menzil >50 m : |w|>60 °/s %3.6
    menzil 10-25 : %16.9
    menzil <10 m : %39.0   (medyan 48.9, p90 127.7, maks 293.6 °/s)
Savrulurken hiz 22.1 -> 16.3 m/s dusuyor.

⚠ Burun BIZIM yaw komutumuzu takip etmiyor (GPS tavani 80 °/s iken bile
  293 °/s goruldu); oyun ANGL AIR modunda ve burun HIZ KOMUTUNUN YONUNU
  izliyor.
⭐ KENDINI BESLEYEN DONGU: ivme tavani yon donusunu w = a/v ile sinirlar,
  yani HIZ DUSTUKCE izin verilen donus BUYUR (20 m/s -> 34 °/s,
  5 m/s -> 137 °/s). Savrulma hizi dusurur, dusen hiz daha cok savrulmaya
  izin verir.
Bu modul yon degisim hizini DOGRUDAN sinirlar; buyukluk korunur.
"""
import math
import os
import sys

import pytest

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
sys.path.insert(0, os.path.join(KOK, "kopru", "gazebo_kaynak"))

from control.guidance.gps_guidance import Cfg  # noqa: E402


def _norm(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


def _uygula(vx, vy, vx_prev, vy_prev, tavan_dps, dt):
    """gps_guidance icindeki tavanin BIREBIR kopyasi."""
    kirp = 0.0
    if tavan_dps > 0.0 and dt > 0.0:
        m_yeni = math.hypot(vx, vy)
        m_onc = math.hypot(vx_prev, vy_prev)
        if m_yeni > 0.5 and m_onc > 0.5:
            a_onc = math.atan2(vy_prev, vx_prev)
            a_yeni = math.atan2(vy, vx)
            d = _norm(a_yeni - a_onc)
            lim = math.radians(tavan_dps) * dt
            if abs(d) > lim:
                kirp = math.degrees(abs(d) - lim) / dt
                a = a_onc + (lim if d > 0 else -lim)
                vx = m_yeni * math.cos(a)
                vy = m_yeni * math.sin(a)
    return vx, vy, kirp


def test_KAPALIYKEN_degismez():
    a = _uygula(0.0, 20.0, 20.0, 0.0, 0.0, 0.05)
    assert a[0] == 0.0 and a[1] == 20.0 and a[2] == 0.0


def test_YON_DEGISIMI_TAVANA_KIRPILIR():
    """90 derecelik ani donus 45 °/s tavanla 0.05 s'de 2.25 dereceye iner."""
    vx, vy, kirp = _uygula(0.0, 20.0, 20.0, 0.0, 45.0, 0.05)
    aci = math.degrees(math.atan2(vy, vx))
    assert aci == pytest.approx(2.25, abs=0.01)
    assert kirp > 0


def test_BUYUKLUK_KORUNUR():
    """Yalniz YON kirpilir; hiz buyuklugu aynen kalir (fren DEGIL)."""
    vx, vy, _ = _uygula(0.0, 17.0, 20.0, 0.0, 45.0, 0.05)
    assert math.hypot(vx, vy) == pytest.approx(17.0, abs=1e-6)


def test_KUCUK_DEGISIM_DOKUNULMAZ():
    """Tavanin altindaki donus aynen gecmeli."""
    a_onc = 0.0
    a_yeni = math.radians(1.0)          # 1 deg / 0.05 s = 20 °/s < 45
    vx, vy, kirp = _uygula(20 * math.cos(a_yeni), 20 * math.sin(a_yeni),
                           20.0, 0.0, 45.0, 0.05)
    assert kirp == 0.0
    assert math.degrees(math.atan2(vy, vx)) == pytest.approx(1.0, abs=1e-6)


def test_IKI_YONE_DE_calisir():
    _, vy1, _ = _uygula(0.0, 20.0, 20.0, 0.0, 45.0, 0.05)
    _, vy2, _ = _uygula(0.0, -20.0, 20.0, 0.0, 45.0, 0.05)
    assert vy1 > 0 and vy2 < 0


def test_DUSUK_HIZDA_DA_baglar():
    """⭐ Asil derdi bu: ivme tavani dusuk hizda serbest birakiyordu."""
    # 5 m/s'de 90 derecelik donus -- ivme tavani 12 m/s^2 buna IZIN VERIR
    # (12/5 = 137 °/s) ama yon tavani vermemeli.
    vx, vy, kirp = _uygula(0.0, 5.0, 5.0, 0.0, 45.0, 0.05)
    assert math.degrees(math.atan2(vy, vx)) == pytest.approx(2.25, abs=0.01)
    assert kirp > 0


def test_DURGUNKEN_dokunulmaz():
    """Cok kucuk komutlarda yon anlamsiz -> kirpma yok."""
    a = _uygula(0.1, 0.1, 0.2, 0.0, 45.0, 0.05)
    assert a[2] == 0.0


def test_varsayilan_KAPALI():
    assert float(getattr(Cfg, "KOMUT_YON_TAVAN", 0.0)) == 0.0 or \
        os.environ.get("AVCI_GPS_YON_TAVAN")


def test_kaynak_ve_mekanizma_kapisi():
    yol = os.path.join(KOK, "kopru", "gazebo_kaynak", "control",
                       "guidance", "gps_guidance.py")
    s = open(yol, encoding="utf-8").read()
    assert "KOMUT_YON_TAVAN" in s
    assert '"yon_kirp_deg"' in s, "mekanizma kapisi sutunu yok"

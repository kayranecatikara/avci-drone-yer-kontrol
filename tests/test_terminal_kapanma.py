# -*- coding: utf-8 -*-
"""TERMINAL KAPANMA TABANI testleri.

NEDEN (2026-08-19, olculdu: 3943 ornek, yarisma modu):
    menzil 22-30 m -> dr/dt -4.80 m/s
    menzil  6-10 m -> dr/dt -0.57 m/s   <- kapanma COKUYOR
    menzil  3- 6 m -> v_yanal 11.8 vs v_LOS 1.2  <- komut neredeyse tamamen yanal
Sonuc: angajman ~10 m'de platoluyor (CPA medyani 10.29 m, %8 <3 m).

Bu modul komuta LOS boyunca eksik kapanmayi ekler. Testler MATEMATIGI
kilitler; ucus etkisi AYRICA canli olculur (kapali/acik kol).
"""
import math
import os
import sys

import pytest

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)


def _uygula(menzil, vx, vy, vz, tv, u, tkm=12.0, hedef_kap=4.0, vmut=24.0, vzmax=6.0):
    """gps_guidance icindeki kapanma tabaninin BIREBIR kopyasi.

    Kod tek bir dongunun icinde yasadigi icin dogrudan cagrilamiyor; burada
    ayni ifadeler tekrarlanir. Ifade degisirse test DUSMEZ -- bu yuzden
    `test_kaynak_ifadesi_AYNI` ayrica kaynagi tarar.
    """
    term_kap = 0.0
    if tkm > 0.0 and menzil < tkm and menzil > 0.3:
        ux, uy, uz = u
        rdot = ((tv[0] - vx) * ux + (tv[1] - vy) * uy + (tv[2] - vz) * uz)
        ist = -hedef_kap
        if rdot > ist:
            term_kap = rdot - ist
            vx += term_kap * ux
            vy += term_kap * uy
            vz = max(-vzmax, min(vzmax, vz + term_kap * uz))
            vm = math.hypot(vx, vy)
            if vm > vmut and vm > 1e-6:
                s = vmut / vm
                vx *= s
                vy *= s
    return vx, vy, vz, term_kap


def _rdot(vx, vy, vz, tv, u):
    return (tv[0] - vx) * u[0] + (tv[1] - vy) * u[1] + (tv[2] - vz) * u[2]


def test_KAPALIYKEN_komut_DEGISMEZ():
    """Varsayilan 0 -> eski davranis bit-ayni olmali."""
    u = (1.0, 0.0, 0.0)
    tv = (18.0, 0.0, 0.0)
    a = _uygula(8.0, 15.0, 3.0, 0.5, tv, u, tkm=0.0)
    assert a[:3] == (15.0, 3.0, 0.5)
    assert a[3] == 0.0


def test_MENZIL_DISINDA_dokunmaz():
    u = (1.0, 0.0, 0.0)
    tv = (18.0, 0.0, 0.0)
    a = _uygula(25.0, 15.0, 3.0, 0.5, tv, u, tkm=12.0)
    assert a[:3] == (15.0, 3.0, 0.5)
    assert a[3] == 0.0


def test_OLCULEN_COKUSU_DUZELTIR():
    """⭐ MODULUN VAR OLMA SEBEBI.

    Sahada olculen 6-10 m durumu: drone hedefle ayni yonde 15 m/s giderken
    hedef 18 m/s -> dr/dt = +3 m/s (UZAKLASIYOR). Taban -4 m/s'e cekmeli.
    """
    u = (1.0, 0.0, 0.0)
    tv = (18.0, 0.0, 0.0)
    onc = _rdot(15.0, 0.0, 0.0, tv, u)
    assert onc == pytest.approx(3.0), "kurgu yanlis"
    vx, vy, vz, k = _uygula(8.0, 15.0, 0.0, 0.0, tv, u)
    son = _rdot(vx, vy, vz, tv, u)
    assert k > 0
    assert son == pytest.approx(-4.0, abs=0.05), "kapanma tabani tutmadi: %.2f" % son


def test_ZATEN_KAPANIYORSA_ARTIRMAZ():
    """dr/dt zaten -6 m/s ise dokunma (asiri hizlandirma yok)."""
    u = (1.0, 0.0, 0.0)
    tv = (18.0, 0.0, 0.0)
    vx, vy, vz, k = _uygula(8.0, 24.0, 0.0, 0.0, tv, u)
    assert k == 0.0
    assert (vx, vy, vz) == (24.0, 0.0, 0.0)


def test_YANAL_bileseni_KIRPMAZ():
    """Yalniz LOS yonunde ekleme yapilir; LOS'a dik bilesen korunur."""
    u = (1.0, 0.0, 0.0)
    tv = (18.0, 0.0, 0.0)
    vx, vy, vz, k = _uygula(5.0, 14.0, 6.0, 0.0, tv, u, vmut=100.0)
    assert k > 0
    assert vy == pytest.approx(6.0), "yanal bilesen degisti"


def test_YANDAN_gecISTE_dogru_yone_eklenir():
    """Hedef yanda: ekleme LOS boyunca olmali, hedefin hizina degil."""
    u = (0.0, 1.0, 0.0)                 # hedef dogu tarafimizda
    tv = (18.0, 0.0, 0.0)               # hedef kuzeye ucuyor
    vx, vy, vz, k = _uygula(6.0, 10.0, 0.0, 0.0, tv, u, vmut=100.0)
    assert k == pytest.approx(4.0, abs=0.05)
    assert vy == pytest.approx(4.0, abs=0.05)
    assert vx == pytest.approx(10.0)


def test_DIKEY_bileseni_VZ_MAX_ile_sinirli():
    """Hedef tam ustumuzde: dikey ekleme VZ_MAX'i asmamali."""
    u = (0.0, 0.0, -1.0)                # NED: hedef YUKARIDA
    tv = (0.0, 0.0, 0.0)
    vx, vy, vz, k = _uygula(5.0, 0.0, 0.0, 0.0, tv, u, hedef_kap=20.0, vzmax=6.0)
    assert vz >= -6.0 and vz <= 6.0


def test_COK_YAKINDA_kapali():
    """menzil<=0.3 m: bolme guvenligi, dokunma."""
    u = (1.0, 0.0, 0.0)
    tv = (18.0, 0.0, 0.0)
    a = _uygula(0.2, 15.0, 0.0, 0.0, tv, u)
    assert a[3] == 0.0


def test_kaynak_ifadesi_AYNI():
    """⚠ Bu test kopyanin kaynaktan SAPMASINI yakalar."""
    yol = os.path.join(KOK, "kopru", "gazebo_kaynak", "control",
                       "guidance", "gps_guidance.py")
    s = open(yol, encoding="utf-8").read()
    for parca in ("term_kap = _rdot - _ist",
                  "TERM_KAPANMA_M",
                  "TERM_KAPANMA_MPS",
                  '"term_kap_mps"'):
        assert parca in s, "kaynakta yok: %s" % parca


def test_varsayilan_ACIK_ve_ucusta_dogrulandi():
    """⭐ 2026-08-19: terminal kapanma UCUSTA ACILDI.

    Kapatilmasinin sebebi vurus orani ayirt edilememesiydi; sonra DUZ ucan
    hedefi bile tutamamanin kok nedeni bulundu: istasyon hedefin
    0.966*menzil gerisinde durdugu icin kovalanan hata menzilin %3.4'u
    kaliyor ve kapanma ~0.2 m/s'e dusuyordu.

    UCUSTA OLCULDU (yatay12 + dikey12 + taban25/4 birlikte):
        CPA medyani    10.58 -> 6.49 m
        <5 m orani       %12 -> %27
        3-6 m kapanma  -1.01 -> -4.50 m/s
    Geri alma: AVCI_GPS_TERM_KAP_M=0 AVCI_GPS_TERM_YATAY=0 AVCI_GPS_TERM_DIKEY=0
    """
    sys.path.insert(0, os.path.join(KOK, "kopru", "gazebo_kaynak"))
    from control.guidance.gps_guidance import Cfg
    if os.environ.get("AVCI_GPS_TERM_KAP_M"):
        return
    assert float(Cfg.TERM_KAPANMA_M) == 25.0
    assert float(Cfg.TERM_YATAY_M) == 12.0
    assert float(Cfg.TERM_DIKEY_M) == 12.0

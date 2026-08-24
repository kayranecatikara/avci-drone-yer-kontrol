# -*- coding: utf-8 -*-
"""GORSEL FAZ MANEVRA KANALI — M1 donus butcesi + M2 arac gecikme telafisi.

NEDEN (2026-08-17, ayna duzeltmesi SONRASI olcum; kampanya izi + bbox_ibvs
kare logu 1:1 eslenerek, 41 angajman / 3467 tespitli kare):
    grup           n  CPA_med   hedef cercevesinde ARKADA / YANAL / DIKEY
    DUZ  (w<15)   26   2.69 m        0.87 / 0.36 / 1.31
    DONUS(w>=15)  15   6.43 m        4.42 / 1.29 / 0.95
  Manevra iskasi YANAL DEGIL BOYUNA: donuste mesafe kapanmiyor
  (kapanma hizi DUZ +1.04 m/s, DONUS -0.84 m/s).
  delta (gercek hiz yonu <-> truth LOS) isaretli ayrisimi, donus karelerinde:
    kerteriz hatasi -0.8 deg | SIGMA -18.2 deg | ARAC GECIKMESI -16.4 deg
  ve donus komutu doyuyor: istenen |w| med 39.4 deg/s, tavan a/V med 30.1,
  DOYGUNLUK %54.1.

Bu testler su davranislari KILITLER:
  * iki kapi da VARSAYILAN KAPALI (sessiz davranis degisikligi YOK)
  * kapaliyken yeni v_kapi parametresi ciktiyi HIC degistirmez (bit-ayni)
  * M1 yalniz KISAR, tabana uyar, DUZ segmentte baglamaz, TERMINALE dokunmaz
  * M2 yalniz CIKISI onceler; psi_v DURUMU ongorusuz kalir (pozitif geri
    besleme yapisal olarak imkansiz)
  * mekanizma kapisi sutunlari log semasinda VAR
"""
import math
import os
import random
import sys

import pytest

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "kopru", "gazebo_kaynak"))

from control.guidance import bbox_ibvs as B          # noqa: E402
from control.guidance.common import normalize_angle  # noqa: E402


class CDpp(B.Cfg):
    """DPP acik referans (kampanyadaki B_ayna_DPP ayari)."""
    DPP_K_SIGMA = 1.4
    DPP_K_R = 0.7
    DPP_R_SET = 6.0
    PN_N = 0.0


class CM1(CDpp):
    DONUS_BUTCE = 0.9
    DONUS_BUTCE_VTABAN = 15.0


class CM2(CDpp):
    ARAC_TAU = 0.35


class CPn(B.Cfg):
    DPP_K_SIGMA = 0.0
    PN_N = 1.6


def _cagri(**ek):
    """Donen hedef + 20 derece sigma hatasi olan tipik bir donus karesi."""
    a = dict(cx=380.0, cy=300.0, w=18.0, h=14.0, iris_yaw=0.3, hiz_I=19.0,
             dt=0.05, terminal=False, los_hiz=(0.5, 0.0), iris_pitch=-0.28,
             iris_vz=0.0, kapanma=1.0, iris_roll=0.05, yaw_hizi=0.4,
             psi_v=0.3 - 0.35)
    a.update(ek)
    return a


# ══════════════════════════════════════════════════════════════════
#  1) VARSAYILAN KAPALI
# ══════════════════════════════════════════════════════════════════
def test_manevra_kapilari_varsayilan_KAPALI():
    import importlib
    importlib.reload(B)                       # env'siz taze varsayilanlar
    assert B.Cfg.DONUS_BUTCE == 0.0           # M1
    assert B.Cfg.ARAC_TAU == 0.0              # M2
    # λ̇ tabanli terminal kapisi olcumle curutuldu (bkz. Cfg.TERM_LAM_MAX_DEG)
    assert B.Cfg.TERM_LAM_MAX_DEG == 0.0


def test_kapaliyken_v_kapi_ciktiyi_DEGISTIRMEZ():
    """Yeni parametre eklendi; kapali yolda cikti BIT-AYNI kalmali."""
    random.seed(1234)
    for _ in range(200):
        a = dict(cx=random.uniform(60, 580), cy=random.uniform(120, 440),
                 w=random.uniform(8, 60), h=random.uniform(6, 45),
                 iris_yaw=random.uniform(-3, 3), hiz_I=random.uniform(0, 24),
                 dt=0.05, terminal=random.random() < 0.3,
                 los_hiz=(random.uniform(-2, 2), random.uniform(-1, 1)),
                 iris_pitch=random.uniform(-0.6, 0.2),
                 iris_vz=random.uniform(-3, 3),
                 kapanma=random.uniform(-5, 8),
                 iris_roll=random.uniform(-0.7, 0.7),
                 yaw_hizi=random.uniform(-2, 2),
                 psi_v=random.uniform(-3, 3))
        for cfg in (B.Cfg, CDpp, CPn):
            ref = B.komut(cfg=cfg, **a)[:5]
            for vk in (None, 12.0, 17.0, 30.0):
                assert B.komut(cfg=cfg, v_kapi=vk, **a)[:5] == ref


# ══════════════════════════════════════════════════════════════════
#  2) M1 · DONUS BUTCESI HIZ KAPISI
# ══════════════════════════════════════════════════════════════════
def test_M1_talep_tavani_asinca_hizi_KISAR():
    t0 = B.komut(cfg=CDpp, v_kapi=None, **_cagri())[5]
    t1 = B.komut(cfg=CM1, v_kapi=None, **_cagri())[5]
    # talep gercekten tavanin ustunde olmali (deneyin on sarti)
    assert abs(t0["w_ham"]) > t0["w_tavan"]
    assert t1["v_los"] < t0["v_los"]
    assert t1["donus_kapi"] is not None


def test_M1_asla_hizi_ARTIRMAZ():
    """Yalniz kisar: hicbir girdide taban ayarindan HIZLI olamaz."""
    random.seed(99)
    for _ in range(300):
        a = _cagri(cx=random.uniform(60, 580), hiz_I=random.uniform(0, 24),
                   los_hiz=(random.uniform(-2, 2), 0.0),
                   psi_v=random.uniform(-3, 3), w=random.uniform(8, 60),
                   h=random.uniform(6, 45))
        v0 = B.komut(cfg=CDpp, v_kapi=None, **a)[5]["v_los"]
        v1 = B.komut(cfg=CM1, v_kapi=None, **a)[5]["v_los"]
        assert v1 <= v0 + 1e-9


def test_M1_tabanin_altina_INMEZ():
    """λ̇ sicramasinda bile hiz tabani korunur (hedef 18 m/s, kopmayalim)."""
    a = _cagri(los_hiz=(4.0, 0.0))            # 229 deg/s -- absurt talep
    t = B.komut(cfg=CM1, v_kapi=None, **a)[5]
    assert t["v_los"] >= CM1.DONUS_BUTCE_VTABAN - 1e-9


def test_M1_DUZ_segmentte_BAGLAMAZ():
    """Duz takipte talep tavanin cok altinda -> kapi hic dokunmaz."""
    from vision import geometry as geo
    # ⚠ iris_roll=0 SART: roll telafisi acikken yatik ucusta cx=CX bile
    #   sifir olmayan seviye azimutu verir (yani sigma!=0 olur).
    # eps=0 ve psi_v = LOS  ->  sigma=0, λ̇~0  ->  talep ~ 0
    a = _cagri(cx=geo.CX, los_hiz=(0.01, 0.0), psi_v=0.3, yaw_hizi=0.0,
               iris_roll=0.0)
    t0 = B.komut(cfg=CDpp, v_kapi=None, **a)[5]
    t1 = B.komut(cfg=CM1, v_kapi=None, **a)[5]
    assert t1["v_los"] == pytest.approx(t0["v_los"], abs=1e-9)


def test_M1_TERMINALE_dokunmaz():
    """Terminal hucum hizi (V_TERMINAL, kullanici karari) korunur."""
    a = _cagri(terminal=True, los_hiz=(2.0, 0.0))
    r0 = B.komut(cfg=CDpp, v_kapi=None, **a)[:5]
    r1 = B.komut(cfg=CM1, v_kapi=None, **a)[:5]
    assert r0 == r1


def test_M1_kapisi_RAMPALI():
    """Kapi kare kare ziplamamali: |kapi - onceki| <= MAX_ACCEL*dt."""
    a = _cagri(los_hiz=(4.0, 0.0))            # kapi tabana kosmak ister
    onceki = 24.0
    t = B.komut(cfg=CM1, v_kapi=onceki, **a)[5]
    assert abs(t["donus_kapi"] - onceki) <= CM1.MAX_ACCEL * a["dt"] + 1e-9


def test_M1_tavani_KISILMIS_hizla_hesaplar():
    """M1'in actigi donus yetkisi GERCEKTEN kullanilmali (yoksa yama bosa gider).

    v_kapi tasindiginda w_tavan = MAX_ACCEL / v_kapi olmali.
    """
    a = _cagri(los_hiz=(1.5, 0.0))
    t_ref = B.komut(cfg=CDpp, v_kapi=None, **a)[5]
    t_kap = B.komut(cfg=CM1, v_kapi=15.0, **a)[5]
    assert t_kap["w_tavan"] > t_ref["w_tavan"]
    assert t_kap["w_tavan"] == pytest.approx(CM1.MAX_ACCEL / 15.0, rel=1e-9)


# ══════════════════════════════════════════════════════════════════
#  3) M2 · ARAC GECIKME TELAFISI
# ══════════════════════════════════════════════════════════════════
def test_M2_cikisi_uygulanan_donus_hiziyla_ONCELER():
    a = _cagri()
    vx0, vy0, _, _, _, t0 = B.komut(cfg=CDpp, v_kapi=None, **a)
    vx1, vy1, _, _, _, t1 = B.komut(cfg=CM2, v_kapi=None, **a)
    bek = CM2.ARAC_TAU * t0["w_uyg"]
    assert t1["arac_lead"] == pytest.approx(bek, rel=1e-9)
    d = normalize_angle(math.atan2(vy1, vx1) - math.atan2(vy0, vx0))
    assert d == pytest.approx(bek, abs=1e-9)


def test_M2_psi_v_DURUMU_ongorusuz_kalir():
    """Kritik: ongoru duruma girerse dongu kendi lead'ini geri okur."""
    a = _cagri()
    t0 = B.komut(cfg=CDpp, v_kapi=None, **a)[5]
    t1 = B.komut(cfg=CM2, v_kapi=None, **a)[5]
    assert t1["psi_v"] == pytest.approx(t0["psi_v"], abs=1e-12)
    assert abs(t1["arac_lead"]) > 1e-3        # lead gercekten uygulandi


def test_M2_lead_TAVANLI():
    a = _cagri(los_hiz=(4.0, 0.0))
    t = B.komut(cfg=CM2, v_kapi=None, **a)[5]
    assert abs(t["arac_lead"]) <= math.radians(CM2.ARAC_TAU_MAX_DEG) + 1e-12


def test_M2_donus_yokken_ETKISIZ():
    """Duz uctugumuzda uygulanan w ~ 0 -> lead ~ 0 -> cikti degismez."""
    from vision import geometry as geo
    # ⚠ iris_roll=0 SART (bkz. M1 duz segment testi)
    a = _cagri(cx=geo.CX, los_hiz=(0.0, 0.0), psi_v=0.3, yaw_hizi=0.0,
               iris_roll=0.0)
    t = B.komut(cfg=CDpp, v_kapi=None, **a)[5]
    assert abs(t["w_uyg"]) < 1e-9             # deneyin on sarti: donus yok
    r0 = B.komut(cfg=CDpp, v_kapi=None, **a)[:5]
    r1 = B.komut(cfg=CM2, v_kapi=None, **a)[:5]
    assert r0 == pytest.approx(r1, abs=1e-9)


def test_M2_saf_takipte_SESSIZCE_devre_disi():
    """PN=0 ve DPP=0 iken donus hizi ACIK bir buyukluk degil -> lead 0."""
    class CSaf(B.Cfg):
        DPP_K_SIGMA = 0.0
        PN_N = 0.0
        ARAC_TAU = 0.35
    a = _cagri()
    t = B.komut(cfg=CSaf, v_kapi=None, **a)[5]
    assert t["w_uyg"] is None and t["arac_lead"] == 0.0


# ══════════════════════════════════════════════════════════════════
#  4) MEKANIZMA KAPISI SUTUNLARI
# ══════════════════════════════════════════════════════════════════
def test_mekanizma_kapisi_sutunlari_log_semasinda_VAR():
    for ad in ("w_talep_deg", "w_tavan_deg", "w_uyg_deg",
               "donus_kapi_v", "arac_lead_deg"):
        assert ad in B._CSV_ALANLAR


def test_doygunluk_olculebilir():
    """w_talep/w_tavan ayni kirpmaya ait olmali -- yoksa doygunluk yanlis olculur."""
    a = _cagri()
    t = B.komut(cfg=CDpp, v_kapi=None, **a)[5]
    assert abs(t["w_uyg"]) == pytest.approx(min(abs(t["w_ham"]), t["w_tavan"]),
                                            rel=1e-9)

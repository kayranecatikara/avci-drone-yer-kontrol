# -*- coding: utf-8 -*-
"""
================================================================================
  test_bbox_geometri  --  bbox_geometri.py'nin matematigini KILITLER
================================================================================
Bu modul SAF matematiktir; her iddiasi burada baglanir. Uc sinif test var:

  1) TUR-DONUSU        ileri donusum ile tersi birbirini goturmeli
  2) CAPRAZ DOGRULAMA  BAGIMSIZ ileri model (vision/geometry.py'nin motor
                       projeksiyonu) ile ayni cevabi vermeli
  3) IKIZ KILIDI       depoda ayni matematigin baska kopyalari var
                       (bbox_ibvs.los_seviye, tespit_akisi.dow_pikseli_yasaya);
                       sapmalari BIREBIR yakalanmali

⚠ EN GUCLU TEST (2): motorun kendi 3B->2B projeksiyonundan piksel uretilir,
  sonra bbox_geometri o pikselden yonu GERI cozer. Iki kod yolu birbirinden
  bagimsizdir; ayni cevabi vermeleri tesaduf olamaz.

⚠ CERCEVE TUZAGI: vision/geometry.py GAZEBO cercevesindedir (x ileri, y SOL,
  z YUKARI); bbox_geometri FRD/NED'dir (y SAG, z ASAGI). Donusum:
        roll_FRD = roll_gz ,  pitch_FRD = -pitch_gz ,  yaw_FRD = -yaw_gz
  Bu, geometry.py:27'nin kendi notuyla tutarlidir ("negatif = yukari").
  Testler bunu ACIKCA uygular; unutulursa isaret hatasi ANINDA patlar.
================================================================================
"""

import math
import os
import sys

import pytest

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "kopru", "gazebo_kaynak"))
sys.path.insert(0, os.path.join(KOK, "kopru"))

from control.guidance import bbox_geometri as BG          # noqa: E402


# ══════════════════════════════════════════════════════════════════════════
#  0. SABITLER — tek kaynakla ayni mi
# ══════════════════════════════════════════════════════════════════════════

def test_icsellikler_vision_geometry_ile_ayni():
    """bbox_geometri kendi sabitlerini tasiyor (bagimliligi yok); ama
    vision/geometry.py TEK KAYNAK -- ikisi ayrilirsa sessiz yanlis olur."""
    from vision import geometry as geo
    assert abs(BG.CX - geo.CX) < 1e-9
    assert abs(BG.CY - geo.CY) < 1e-9
    assert abs(BG.FX - geo.FX) < 1e-6
    assert abs(BG.FY - geo.FY) < 1e-6


def test_dow_icsellik_motorun_degeri():
    """fx_dow motorun kendi projeksiyonundan cozuldu: 531.36 (artik 0.001 px)."""
    assert abs(BG.FX_DOW - 531.36) < 0.01
    assert abs(BG.OLCEK_DOW_YASA - 0.31350) < 1e-4
    # yasa cercevesi HFOV 125 (Gazebo mirasi) -> FX 166.58
    assert abs(BG.FX - 166.58) < 0.01


def test_kamera_tilt_guidance_core_ile_ayni():
    from control.guidance.guidance_core import Cfg as GeoCfg
    assert abs(BG.KAMERA_TILT_DEG - GeoCfg.KAMERA_TILT_DEG) < 1e-9


# ══════════════════════════════════════════════════════════════════════════
#  1. TUR-DONUSU
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("cy", [120.0, 180.0, 240.0, 301.0, 318.0, 400.0, 460.0])
def test_turdonus_piksel_elev(cy):
    """elev_piksel(piksel_elev(cy)) == cy, MAKINE HASSASIYETINDE."""
    assert abs(BG.elev_piksel(BG.piksel_elev(cy)) - cy) < 1e-9


def test_seviye_hedef_pikseli():
    """Yukselis 0 (seviye hedef) -> cy = CY + FY*tan(25 deg) = 317.7 px.
    Bu, CY_NISAN=301 ile arasindaki 16.7 px'in NEREDEN geldigini sabitler:
    301 px = +4.888 deg govde yukselisi = TASARIM ofseti."""
    assert abs(BG.elev_piksel(0.0) - (BG.CY + BG.FY * math.tan(
        math.radians(25.0)))) < 1e-9
    assert abs(BG.elev_piksel(0.0) - 317.68) < 0.05
    assert abs(math.degrees(BG.piksel_elev(301.0)) - 4.888) < 0.01


def test_turdonus_menzil_acisal():
    """Bilinen L ve R -> piksel boyutu -> menzil_acisal geri R vermeli."""
    from vision import geometry as geo
    for R in (5.0, 12.0, 30.0):
        for L in (0.8, 1.4, 1.78):
            # merkezde, LOS'a dik parca: yari-aci atan(L/2R)
            yari = math.atan((L / 2.0) / R)
            w = 2.0 * geo.FX * math.tan(yari)
            R2 = BG.menzil_acisal(BG.CX, BG.CY, w, w, L)
            assert abs(R2 - R) < 1e-6 * max(R, 1.0), (R, L, R2)


def test_acisal_menzil_merkez_disinda_da_dogru():
    """★ ACISAL modelin ASIL iddiasi: kadraj KENARINDA da dogru menzil.
    Ayni fiziksel parcayi merkezden 45 derece uzaga koy; piksel boyutu
    sec^2 ile SISER ama acisal olcut bunu goturur."""
    R, L = 15.0, 1.4
    tx = math.tan(math.radians(45.0))
    cx = BG.CX + BG.FX * tx
    # kenarlarin aci konumlari: merkez aci +- yari
    yari = math.atan((L / 2.0) / R)
    a0, a1 = math.radians(45.0) - yari, math.radians(45.0) + yari
    w = BG.FX * (math.tan(a1) - math.tan(a0))
    assert w > 2.0 * BG.FX * math.tan(yari) * 1.5, "sec^2 sismesi yok?"
    R2 = BG.menzil_acisal(cx, BG.CY, w, w, L)
    assert abs(R2 - R) / R < 0.02, (R2, R)
    # PIKSEL tabanli sabit ayni yerde %90+ hata yapar
    R_px = BG.menzil_px_sabit(w, w, BG.FX * L)
    assert abs(R_px - R) / R > 0.4, R_px


# ══════════════════════════════════════════════════════════════════════════
#  2. CAPRAZ DOGRULAMA — motorun ileri projeksiyonuna karsi
# ══════════════════════════════════════════════════════════════════════════

def _gz_piksel(hedef_gz, roll, pitch, yaw):
    """vision/geometry ile 3B nokta -> piksel. Girdi FRD/NED acilariyla;
    Gazebo'ya cevrilir (pitch ve yaw isaret degistirir).
    cam_pos da dondurulur: kamera govde merkezinde DEGIL (CAM_OFFSET_POS)."""
    import numpy as np
    from vision import geometry as geo
    cam_pos, R_cam = geo.camera_world_pose((0.0, 0.0, 0.0),
                                           (roll, -pitch, -yaw))
    u, v, ok = geo.project_points(np.array([hedef_gz], float), cam_pos, R_cam)
    return (float(u[0]), float(v[0]), bool(ok[0]), cam_pos)


@pytest.mark.parametrize("roll_d,pitch_d,yaw_d", [
    (0.0, 0.0, 0.0), (0.0, -14.5, 0.0), (25.0, 0.0, 0.0), (-30.0, -20.0, 0.0),
    (40.0, 10.0, 0.0), (50.7, -17.6, 0.0), (15.0, 5.0, 60.0), (-45.0, -25.0, -120.0),
])
def test_los_seviye_motor_projeksiyonuyla_ayni(roll_d, pitch_d, yaw_d):
    """★ EN GUCLU TEST. Motorun projeksiyonundan piksel uret, los_seviye ile
    yonu GERI coz, GERCEK seviye azimut/yukselisiyle kiyasla.

    Beklenen (GAZEBO dunya cercevesi: x ileri/kuzey, y SOL, z YUKARI):
        azimut_seviye   = atan2(-Yr, Xr) - yaw_FRD
        yukselis_seviye = atan2(Zr, hypot(Xr, Yr))
    ⚠ (Xr,Yr,Zr) hedefin KAMERA'ya gore konumudur, govde merkezine gore
      DEGIL: kamera CAM_OFFSET_POS=(0.10,0,0.05) m kaydirilmistir. Bu test
      ilk yazildiginda o ofset unutulmustu ve 0.1 deg'lik "gizemli" sapma
      verdi -- paralaks TERIMI budur (bkz. BG.parallaks_duzelt).
    """
    pytest.importorskip("numpy")
    from vision import geometry as geo
    # ⚠ geometry.py TILT'i 0.4363 rad HARDCODED (= 24.99815 deg, 25.0 DEGIL).
    #   Fark 3.2e-5 rad = 0.0019 deg -- ihmal edilebilir ama bu test 1e-9
    #   hassasiyette oldugu icin ACIKCA ayni sabit kullanilir. (Depoda kalan
    #   bir tutarsizlik; bu testin yan urunu olarak belgelendi.)
    tilt = math.degrees(-geo.CAM_TILT_RAD)
    roll, pitch, yaw = (math.radians(roll_d), math.radians(pitch_d),
                        math.radians(yaw_d))
    n = 0
    for X, Y, Z in ((20.0, 0.0, 3.0), (15.0, 6.0, -2.0), (30.0, -8.0, 10.0),
                    (8.0, 2.0, 0.5), (25.0, -3.0, -6.0), (12.0, 9.0, 4.0),
                    (18.0, -5.0, 8.0), (10.0, 0.0, -1.0), (-6.0, 12.0, 5.0),
                    (-14.0, -9.0, -3.0), (0.0, 18.0, 6.0), (2.0, -20.0, -4.0)):
        cx, cy, ok, cam = _gz_piksel((X, Y, Z), roll, pitch, yaw)
        if not ok or not (0 <= cx <= 640 and 0 <= cy <= 480):
            continue
        Xr, Yr, Zr = X - cam[0], Y - cam[1], Z - cam[2]
        az_b, el_b = BG.los_seviye(cx, cy, roll, pitch, tilt)
        az_g = BG.sarmala_pi(math.atan2(-Yr, Xr) - yaw)
        el_g = math.atan2(Zr, math.hypot(Xr, Yr))
        assert abs(BG.sarmala_pi(az_b - az_g)) < 1e-9, (X, Y, Z, az_b, az_g)
        assert abs(el_b - el_g) < 1e-9, (X, Y, Z, el_b, el_g)
        n += 1
    assert n >= 2, "hicbir nokta kadraja girmedi -- test bos kosuyor"


def test_geometry_py_tilt_sabiti_25_dereceden_SAPIYOR():
    """Depoda kalan kucuk tutarsizligi ACIKCA kaydeder: vision/geometry.py
    CAM_TILT_RAD = -0.4363 (24.99815 deg), guidance_core ise 25.0 deg.
    Fark 0.0019 deg -- zararsiz, ama 'ayni sabit' sanilmamali."""
    from vision import geometry as geo
    d = abs(math.degrees(-geo.CAM_TILT_RAD) - BG.KAMERA_TILT_DEG)
    assert 0.0 < d < 0.01, d


@pytest.mark.parametrize("R", [3.0, 5.0, 8.0, 20.0])
def test_paralaks_terimi_olculu_ve_menzille_soner(R):
    """Kamera ofseti yakin menzilde OLCULUR bir yukselis kaymasi yapar.

    Kamera govdenin 0.05 m USTUNDE. Seviye hedef icin (az=el=0) duzeltme
        d_el = -p_asagi/R = +0.05/R      (govde merkezinden hedef DAHA YUKARIDA)
    3 m'de +0.95 deg, 20 m'de +0.14 deg. ILERI ofset (p_f) bu ozel durumda
    dusuyor cunku sin(el)=0."""
    az, el = BG.parallaks_duzelt(0.0, 0.0, R)
    assert az == 0.0                       # p_r = 0 -> yatay kayma yok
    assert abs(math.degrees(el) - math.degrees(0.05 / R)) < 1e-12
    assert el > 0
    assert abs(math.degrees(el)) < 1.0
    # menzille 1/R sonmeli
    _, el2 = BG.parallaks_duzelt(0.0, 0.0, 2.0 * R)
    assert abs(el2 - el / 2.0) < 1e-12


def test_paralaks_motor_projeksiyonuyla_dogrulanir():
    """★ paralaks duzeltmesi, motorun ileri modelindeki ofseti GERI ALMALI."""
    pytest.importorskip("numpy")
    from vision import geometry as geo
    tilt = math.degrees(-geo.CAM_TILT_RAD)
    n = 0
    for X, Y, Z in ((20.0, 0.0, 3.0), (10.0, 2.0, -1.0), (8.0, -3.0, 2.0),
                    (30.0, 5.0, -4.0), (6.0, 1.0, 1.5)):
        cx, cy, ok, cam = _gz_piksel((X, Y, Z), 0.0, 0.0, 0.0)
        if not ok:
            continue
        az_b, el_b = BG.los_seviye(cx, cy, 0.0, 0.0, tilt)
        R_kam = math.sqrt((X - cam[0]) ** 2 + (Y - cam[1]) ** 2 + (Z - cam[2]) ** 2)
        az_d, el_d = BG.parallaks_duzelt(az_b, el_b, R_kam)
        # govde MERKEZINE gore gercek yon (birinci mertebe -> 1e-4 bandi)
        assert abs(BG.sarmala_pi(az_d - math.atan2(-Y, X))) < 1e-4, (X, Y, Z)
        assert abs(el_d - math.atan2(Z, math.hypot(X, Y))) < 1e-4, (X, Y, Z)
        # duzeltme GERCEKTEN bir sey yapmali (bos test olmasin)
        assert abs(el_d - el_b) > 1e-4
        n += 1
    assert n >= 3


def test_piksel_elev_kamera_ekseninde_motorla_ayni():
    """piksel_elev DUZLEMSEL: yalniz cx=CX'te kuresel yukselise esittir."""
    for cy in (200.0, 240.0, 301.0, 350.0):
        az, el = BG.los_seviye(BG.CX, cy, 0.0, 0.0)
        assert abs(az) < 1e-12
        assert abs(el - BG.piksel_elev(cy)) < 1e-12


def test_duzlem_kuresel_merkez_disinda_AYRISIR():
    """cx != CX'te duzlemsel piksel_elev kuresel yukselisi ASAR. Yasanin
    terminal dali (bbox_ibvs:1410) tam da bunu kullaniyor -> sapma OLCULU."""
    _, el_k = BG.los_seviye(BG.CX + 250.0, 301.0, 0.0, 0.0)
    fark = math.degrees(BG.piksel_elev(301.0) - el_k)
    assert fark > 1.5, fark            # olculen 2.06 deg
    assert BG.piksel_elev(301.0) > el_k


# ══════════════════════════════════════════════════════════════════════════
#  3. IKIZ KILIDI — depodaki diger kopyalarla BIREBIR ayni
# ══════════════════════════════════════════════════════════════════════════

def test_los_seviye_bbox_ibvs_ikiziyle_BIREBIR():
    """bbox_ibvs.los_seviye ile ayni sayiyi vermeli (yasaya baglarken bit-ayni
    davranis sarti). Ayrilirsa entegrasyon SESSIZ bir davranis degisikligi olur."""
    from control.guidance import bbox_ibvs as BI
    for cx in (60.0, 320.0, 500.0, 610.0):
        for cy in (100.0, 240.0, 301.0, 400.0):
            for roll in (-0.7, 0.0, 0.35, 0.9):
                for pitch in (-0.4, -0.25, 0.0, 0.2):
                    a1, e1 = BG.los_seviye(cx, cy, roll, pitch)
                    a2, e2 = BI.los_seviye(cx, cy, roll, pitch)
                    assert abs(a1 - a2) < 1e-12
                    assert abs(e1 - e2) < 1e-12


def test_piksel_elev_ve_elev_piksel_ikizleriyle_BIREBIR():
    from control.guidance import bbox_ibvs as BI
    for cy in (120.0, 240.0, 301.0, 318.0, 430.0):
        assert abs(BG.piksel_elev(cy) - BI.piksel_elev(cy)) < 1e-12
    for e in (-0.6, -0.2, 0.0, 0.085, 0.4):
        assert abs(BG.elev_piksel(e) - BI.elev_piksel(e)) < 1e-12


def test_dow_ceviri_tespit_akisi_ikiziyle_BIREBIR():
    """dow_yasa_piksel == tespit_akisi.dow_pikseli_yasaya (AYNA dahil)."""
    import tespit_akisi as TA
    for cx, cy, w, h in ((960.0, 540.0, 100.0, 60.0), (10.0, 20.0, 30.0, 30.0),
                         (1900.0, 1050.0, 200.0, 120.0), (500.0, 800.0, 44.0, 33.0)):
        a = BG.dow_yasa_piksel(cx, cy, w, h, 1920.0, 1080.0)
        b = TA.dow_pikseli_yasaya(cx, cy, w, h, 1920.0, 1080.0)
        for x, y in zip(a, b):
            assert abs(x - y) < 1e-9, (cx, cy, a, b)


def test_ayna_isareti():
    """DoW karesinin SAGINDAKI hedef, yasa cercevesinde NEGATIF azimut olmali.
    (Ayna: NED_y = -DoW_y. Bu depodaki en pahali hata; testle cakiliyor.)"""
    cxy, _, _, _ = BG.dow_yasa_piksel(1900.0, 540.0, 20.0, 20.0, 1920.0, 1080.0)
    assert cxy < BG.CX
    assert BG.azimut_ham(cxy) < 0
    # dikey DEGISMEZ: DoW'da asagida olan yasada da asagida
    _, cyy, _, _ = BG.dow_yasa_piksel(960.0, 1000.0, 20.0, 20.0, 1920.0, 1080.0)
    assert cyy > BG.CY


# ══════════════════════════════════════════════════════════════════════════
#  4. ACISAL BOYUT / OFF-AXIS
# ══════════════════════════════════════════════════════════════════════════

def test_acisal_boyut_merkezde_kucuk_aci():
    """Merkezde acisal boyut ~ w/FX (kucuk aci)."""
    dy, dd = BG.acisal_boyut(BG.CX, BG.CY, 20.0, 12.0)
    assert abs(dy - 20.0 / BG.FX) < 1e-3
    assert abs(dd - 12.0 / BG.FY) < 1e-3


def test_offaxis_sec2_kazanci():
    """Ayni PIKSEL boyutu kenarda DAHA KUCUK acidir; oran ~ sec^2(alfa)."""
    for a_deg in (30.0, 45.0, 56.0):
        cx = BG.CX + BG.FX * math.tan(math.radians(a_deg))
        d0, _ = BG.acisal_boyut(BG.CX, BG.CY, 20.0, 20.0)
        d1, _ = BG.acisal_boyut(cx, BG.CY, 20.0, 20.0)
        oran = d0 / d1
        sec2 = 1.0 / math.cos(math.radians(a_deg)) ** 2
        assert abs(oran / sec2 - 1.0) < 0.05, (a_deg, oran, sec2)


def test_kutu_kirpik_sinirlari():
    """Kadraj sinirlari DoW 1920x1080'in yasa cercevesindeki karsiligi."""
    assert abs(BG.KADRAJ_U0 - 18.9) < 0.2 and abs(BG.KADRAJ_U1 - 621.1) < 0.2
    assert abs(BG.KADRAJ_V0 - 70.7) < 0.2 and abs(BG.KADRAJ_V1 - 409.3) < 0.2
    assert not BG.kutu_kirpik(320.0, 240.0, 40.0, 30.0)
    assert BG.kutu_kirpik(30.0, 240.0, 40.0, 30.0)          # sol kenar
    assert BG.kutu_kirpik(320.0, 400.0, 40.0, 30.0)         # alt kenar


# ══════════════════════════════════════════════════════════════════════════
#  5. HEDEF BOYUTU / ASPECT
# ══════════════════════════════════════════════════════════════════════════

def test_gorunur_genislik_sinir_degerleri():
    """ARTI (cross) modeli: kuyrukta kanat acikligi, bordada govde uzunlugu."""
    assert abs(BG.gorunur_genislik_m(math.radians(180.0)) - 1.78) < 1e-9
    assert abs(BG.gorunur_genislik_m(0.0) - 1.78) < 1e-9
    assert abs(BG.gorunur_genislik_m(math.radians(90.0)) - 1.10) < 1e-9
    # MAKSIMUM modeli TOPLAM modelinden kucuk olmali (eski hata)
    a = math.radians(45.0)
    assert BG.gorunur_genislik_m(a) < 1.78 * math.cos(a) + 1.10 * math.sin(a)
    # en kucuk deger dallarin kesistigi yerde
    en_kucuk = min(BG.gorunur_genislik_m(math.radians(x)) for x in range(0, 181))
    assert 0.90 < en_kucuk < 0.96


def test_menzil_belirsizlik_tabani_aspect():
    """Aspect bilinmiyorsa menzil belirsizliginin TABANI %19; piksel
    gurultusu 30 px'lik kutuda bunun yaninda kucuk kalir."""
    s30 = BG.menzil_belirsizlik(10.0, 30.0, 30.0, 1.0) / 10.0
    s10 = BG.menzil_belirsizlik(10.0, 10.0, 10.0, 1.0) / 10.0
    assert 0.185 < s30 < 0.20
    assert s10 > s30
    assert BG.menzil_belirsizlik(20.0, 30.0, 30.0) == pytest.approx(
        2.0 * BG.menzil_belirsizlik(10.0, 30.0, 30.0))     # R ile dogrusal


# ══════════════════════════════════════════════════════════════════════════
#  6. IRTIFA
# ══════════════════════════════════════════════════════════════════════════

def test_irtifa_farki_roll_telafisinin_katkisi():
    """Terminalde olculen yatis 50.7 deg. Telafisiz kestirim buyuk SAHTE
    irtifa farki uretir; telafili olan gercek deger etrafinda kalir."""
    cx, cy, R = BG.CX + 180.0, 330.0, 8.0
    roll, pitch = math.radians(45.0), math.radians(-17.6)
    dz_dogru = BG.irtifa_farki(cx, cy, roll, pitch, R)
    dz_telafisiz = BG.irtifa_farki_telafisiz(cy, pitch, R)
    assert abs(dz_telafisiz - dz_dogru) > 1.0, (dz_dogru, dz_telafisiz)
    # roll=0'da bile fark KALIR: piksel_elev DUZLEMSEL, kuresel degil.
    # cx merkezden 180 px uzakta, R=8 m -> 0.79 m. Yani terminaldeki dikey
    # hatanin BIR KISMI roll degil, DUZLEM/KURESEL karisikligidir.
    d0 = BG.irtifa_farki(cx, cy, 0.0, pitch, R)
    d1 = BG.irtifa_farki_telafisiz(cy, pitch, R)
    assert 0.5 < abs(d1 - d0) < 1.2, (d0, d1)
    # merkezde (cx=CX) ikisi TAM ayni olmali
    assert abs(BG.irtifa_farki(BG.CX, cy, 0.0, pitch, R)
               - BG.irtifa_farki_telafisiz(cy, pitch, R)) < 1e-12


def test_irtifa_farki_isareti():
    """Hedef ufkun uzerindeyse dz POZITIF."""
    assert BG.irtifa_farki(BG.CX, 200.0, 0.0, 0.0, 10.0) > 0    # yukarida
    assert BG.irtifa_farki(BG.CX, 400.0, 0.0, 0.0, 10.0) < 0    # asagida


# ══════════════════════════════════════════════════════════════════════════
#  7. KARARLILIK
# ══════════════════════════════════════════════════════════════════════════

def test_faz_payi_kazancta_azalan():
    onceki = 1e9
    for k in (0.4, 0.8, 1.2, 1.6, 2.0, 3.0, 4.0):
        _, pm, _ = BG.yaw_kazanc_kararlilik(k)
        assert pm < onceki
        onceki = pm


def test_yaw_kazanc_oner_tersi_tutarli():
    for pm in (70.0, 60.0, 50.0, 45.0, 35.0):
        k = BG.yaw_kazanc_oner(pm)
        assert abs(BG.yaw_kazanc_kararlilik(k)[1] - pm) < 0.05, pm


def test_olculen_kanalda_dpp_k_makul():
    """AVCI_DPP_K=1.4 varsayilani BAGIMSIZ turetmeyle 45-60 deg PM bandinda
    olmali. (Olculen kanal: dedektor 0.20 s + ornekleme, tau 0.28 s.)"""
    _, pm, gm = BG.yaw_kazanc_kararlilik(1.4)
    assert 45.0 < pm < 60.0, pm
    assert gm > 2.0, gm


def test_gecikme_arttikca_kazanc_dusmeli():
    k1 = BG.yaw_kazanc_oner(50.0, 0.10)
    k2 = BG.yaw_kazanc_oner(50.0, 0.30)
    assert k2 < k1


def test_ileri_besleme_kalici_hatayi_sifirlar():
    assert BG.yaw_kalici_hata(1.4, 0.5, ff=1.0) == pytest.approx(0.0)
    assert BG.yaw_kalici_hata(1.4, 0.5, ff=0.0) == pytest.approx(0.5 / 1.4)
    # kazanc iki katina cikarsa kalici hata yariya iner
    assert BG.yaw_kalici_hata(2.8, 0.5) == pytest.approx(
        0.5 * BG.yaw_kalici_hata(1.4, 0.5))


def test_yaw_komut_tavani_ve_isareti():
    assert BG.yaw_komut(0.0) == 0.0
    assert BG.yaw_komut(0.2, k=1.4) > 0            # sag hata -> saga don
    assert BG.yaw_komut(-0.2, k=1.4) < 0
    buyuk = BG.yaw_komut(3.0, k=5.0)
    assert abs(buyuk - math.radians(BG.YAW_TAVAN_DPS)) < 1e-12


def test_donus_hizi_tavani_olculen_deger():
    """a=12, V=18 -> 38.2 deg/s. Olculen %99 donus hizi 37.9 -- clamp bagliyor."""
    assert abs(math.degrees(BG.donus_hizi_tavani(18.0, 12.0)) - 38.2) < 0.2
    # hiz vektoru tavani BURUN tavanindan cok daha kucuk
    assert math.degrees(BG.donus_hizi_tavani(18.0, 12.0)) < BG.YAW_TAVAN_DPS / 2.0


# ══════════════════════════════════════════════════════════════════════════
#  8. IVME DAGITIMI
# ══════════════════════════════════════════════════════════════════════════

def test_ivme_tutum_hover():
    roll, pitch, T, yat = BG.ivme_tutum(0.0, 0.0, 0.0, 0.0)
    assert abs(roll) < 1e-12 and abs(pitch) < 1e-12
    assert abs(T - BG.G) < 1e-9
    assert abs(yat) < 1e-9


def test_ivme_tutum_ileri_ivme_burun_asagi():
    """FRD: pozitif pitch burun YUKARI. Ileri ivmelenmek NEGATIF pitch ister."""
    _, pitch, _, _ = BG.ivme_tutum(5.0, 0.0, 0.0, 0.0)
    assert pitch < 0
    assert abs(math.degrees(pitch) + math.degrees(math.atan(5.0 / BG.G))) < 1e-9


def test_ivme_tutum_yaw_donusumu():
    """yaw=90 deg iken DOGU'ya ivme, govdede ILERI ivmedir."""
    _, p0, _, _ = BG.ivme_tutum(5.0, 0.0, 0.0, 0.0)
    _, p90, _, _ = BG.ivme_tutum(0.0, 5.0, 0.0, math.radians(90.0))
    assert abs(p0 - p90) < 1e-9
    r90, _, _, _ = BG.ivme_tutum(0.0, 5.0, 0.0, 0.0)      # yaw=0 -> SAGA ivme
    assert r90 > 0


def test_kamera_kisiti_common_py_ile_ayni_sayiyi_verir():
    """common.py:60 'yaklasik 5 m/s^2 ustunde gokyuzu kaybolur' notunun
    BAGIMSIZ turetmesi: a <= g*tan(25 deg) = 4.57."""
    a = BG.yatay_ivme_tavani_kamera(0.0, 0.0)
    assert abs(a - BG.G * math.tan(math.radians(25.0))) < 1e-9
    assert 4.5 < a < 4.7


def test_tirmanma_yatay_butceyi_buyutur():
    """NED'de a_d < 0 = YUKARI. (g - a_d) buyudugu icin yatay tavan ARTAR --
    tek 3B tavanin kurdugu bag TERS yondedir."""
    assert (BG.yatay_ivme_tavani_kamera(-5.0, 0.0)
            > BG.yatay_ivme_tavani_kamera(0.0, 0.0))


def test_ivme_butce_dikeyi_KORUR():
    """Yatay doygunken dikey talep AYNEN gecmeli (tek 3B tavanin yapamadigi)."""
    an, ae, ad = BG.ivme_butce(30.0, 0.0, -4.0, 12.0, 10.0)
    assert abs(math.hypot(an, ae) - 12.0) < 1e-9
    assert ad == -4.0
    # dikey de kendi tavaniyla kirpilir
    assert BG.ivme_butce(0.0, 0.0, -30.0, 12.0, 10.0)[2] == -10.0


def test_ivme_butce_yon_korur():
    an, ae, _ = BG.ivme_butce(9.0, 12.0, 0.0, 12.0, 10.0)
    assert abs(math.atan2(ae, an) - math.atan2(12.0, 9.0)) < 1e-12


def test_ivme_butce_kamerali_sirasi():
    """Once dikey (kamerayi bozmaz), sonra kalan kamera butcesiyle yatay."""
    an, ae, ad, tav = BG.ivme_butce_kamerali(12.0, 0.0, -5.0, 10.0, 0.0)
    assert ad == -5.0
    assert abs(tav - BG.yatay_ivme_tavani_kamera(-5.0, 0.0)) < 1e-12
    assert abs(math.hypot(an, ae) - tav) < 1e-9
    # tirmanirken yatay butce, duz ucustakinden BUYUK
    _, _, _, tav0 = BG.ivme_butce_kamerali(12.0, 0.0, 0.0, 10.0, 0.0)
    assert tav > tav0


# ══════════════════════════════════════════════════════════════════════════
#  8b. TAM DURUM KESTIRIMI — irtifa + hiz + yon + aci
# ══════════════════════════════════════════════════════════════════════════
# ⚠ EN GUCLU TEST BURADA DA TUR-DONUSUDUR: bilinen bir 3B bagil konumdan
#   `seviye_piksel` ile PIKSEL uretilir, sonra `hedef_ofset_ned` o pikselden
#   3B konumu GERI cozer. Iki yon birbirinden bagimsiz yazildi.

def _ofset_pikselden(N, E, D, roll, pitch, yaw):
    """(N,E,D) bagil ofset -> (cx, cy, R): ileri model (test yardimcisi)."""
    R = math.sqrt(N * N + E * E + D * D)
    psi = math.atan2(E, N)
    el = math.atan2(-D, math.hypot(N, E))
    az = BG.sarmala_pi(psi - yaw)
    m = BG.seviye_piksel(az, el, roll, pitch)
    return m, R


@pytest.mark.parametrize("N,E,D", [
    (10.0, 0.0, 0.0), (8.0, 3.0, -2.0), (15.0, -4.0, 1.5),
    (5.0, 1.0, -0.5), (25.0, 6.0, 3.0),
])
@pytest.mark.parametrize("roll,pitch,yaw", [
    (0.0, 0.0, 0.0), (0.35, -0.25, 1.1),
    # ⚠ TERMINAL YATISI: olculen en buyuk yatis 50.7 deg = 0.885 rad. Roll
    #   telafisinin en cok bagladigi yer burasi -- test onu ACIKCA gezmeli.
    (-0.885, -0.30, -0.70),
])
def test_ofset_ned_TUR_DONUSU(N, E, D, roll, pitch, yaw):
    """3B -> piksel -> 3B kapaniyor mu (mm mertebesinde)."""
    m, R = _ofset_pikselden(N, E, D, roll, pitch, yaw)
    if m is None:
        pytest.skip("kamera arkasi")
    cx, cy = m
    o = BG.hedef_ofset_ned(cx, cy, roll, pitch, yaw, R)
    for a, b in zip(o, (N, E, D)):
        assert abs(a - b) < 1e-6


def test_ofset_ned_dz_irtifa_farki_ILE_AYNI():
    """dz = -D, ve bu `irtifa_farki`nin verdigi sayinin TA KENDISI olmali.
    (Iki fonksiyon ayri yazildi; ayrilirlarsa sessiz yanlis olur.)"""
    for cx in (200.0, 320.0, 480.0):
        for cy in (260.0, 301.0, 360.0):
            for roll in (0.0, 0.4, -0.6):
                o = BG.hedef_ofset_ned(cx, cy, roll, -0.25, 0.9, 12.0)
                assert abs(-o[2] - BG.irtifa_farki(cx, cy, roll, -0.25, 12.0)) < 1e-12


def test_ofset_ned_DPSI_yaw_bayatligini_CIKARIR():
    """dpsi verilince kestirim TAM dpsi kadar geri doner (yatayda)."""
    dpsi = math.radians(13.05)                 # olculen p90
    a = BG.hedef_ofset_ned(400.0, 300.0, 0.2, -0.2, 1.0, 10.0)
    b = BG.hedef_ofset_ned(400.0, 300.0, 0.2, -0.2, 1.0, 10.0, dpsi=dpsi)
    psi_a = math.atan2(a[1], a[0])
    psi_b = math.atan2(b[1], b[0])
    assert abs(BG.sarmala_pi(psi_a - psi_b) - dpsi) < 1e-9
    # DIKEY eksen yaw'dan ETKILENMEZ — bayatlik yalniz yatayi bozar
    assert abs(a[2] - b[2]) < 1e-12


def test_egim_pencere_TAM_dogru_ve_az_ornekte_None():
    ts = [0.0, 0.1, 0.2, 0.35, 0.5]
    xs = [3.0 + 7.5 * t for t in ts]
    assert abs(BG.egim_pencere(ts, xs) - 7.5) < 1e-9
    assert BG.egim_pencere([0.0, 0.1], [1.0, 2.0]) is None      # <3 ornek
    assert BG.egim_pencere([0.2] * 4, [1.0] * 4) is None        # sxx = 0


def test_hedef_hiz_ned_SENTETIK_GERI_COZULUYOR():
    """Bilinen hedef hizi, kutudan uretilen ofsetlerden BIREBIR geri cikmali.

    Kurgu: arac sabit hizla ucuyor, hedef baska bir sabit hizla. Ofset
    zamanda DOGRUSAL oldugu icin en kucuk kareler egimi TAM cozer.
    """
    v_kendi = (18.0, 2.0, -0.5)
    v_hedef = (14.0, -6.0, 0.8)
    p_kendi = [0.0, 0.0, -40.0]
    p_hedef = [30.0, 5.0, -42.0]
    ts, ofs = [], []
    for k in range(8):
        t = 0.04 * k
        ofs.append(tuple(p_hedef[i] + v_hedef[i] * t
                         - (p_kendi[i] + v_kendi[i] * t) for i in range(3)))
        ts.append(t)
    v = BG.hedef_hiz_ned(ts, ofs, v_kendi)
    for a, b in zip(v, v_hedef):
        assert abs(a - b) < 1e-9
    assert BG.hedef_hiz_ned(ts[:2], ofs[:2], v_kendi) is None


def test_hedef_hiz_MENZIL_YANLILIGI_RADYALE_AYNEN_BINER():
    """★ TURETMENIN KILIDI: R_kest = (1+b)R ise BAGIL hiz da (1+b) katidir.

    Bu, MENZIL_PX_M=202.6'nin olculen +%33 yanliliginin kapanma hizini da
    %33 sisirdiginin kaniti -- ve recetedeki menzil kolunun IKINCI
    mekanizma kapisi.
    """
    b = 0.33
    v_kendi = (20.0, 0.0, 0.0)
    v_hedef = (14.0, 0.0, 0.0)          # tam onumuzde, saf kapanma
    ts, o1, o2 = [], [], []
    for k in range(8):
        t = 0.04 * k
        d = 20.0 + (v_hedef[0] - v_kendi[0]) * t
        ts.append(t)
        o1.append((d, 0.0, 0.0))
        o2.append((d * (1.0 + b), 0.0, 0.0))
    v1 = BG.hedef_hiz_ned(ts, o1, v_kendi)
    v2 = BG.hedef_hiz_ned(ts, o2, v_kendi)
    bagil1 = v1[0] - v_kendi[0]
    bagil2 = v2[0] - v_kendi[0]
    assert abs(bagil1 - (v_hedef[0] - v_kendi[0])) < 1e-9
    assert abs(bagil2 / bagil1 - (1.0 + b)) < 1e-9


def test_rota_ve_yer_hizi():
    r, s = BG.rota_ve_yer_hizi(0.0, 18.0)
    assert abs(math.degrees(r) - 90.0) < 1e-9          # tam DOGU
    assert abs(s - 18.0) < 1e-12
    r, s = BG.rota_ve_yer_hizi(-3.0, -4.0)
    assert abs(s - 5.0) < 1e-12
    assert abs(math.degrees(r) + 126.8698976) < 1e-6


def test_aspect_hizdan_KUYRUK_ve_BORDA():
    """Hedef bizden UZAKLASIYORSA kuyrugundayiz (aspect 180)."""
    ofs = (10.0, 0.0, 0.0)                       # hedef tam kuzeyimizde
    # hedef kuzeye gidiyor -> bizden uzaklasiyor -> KUYRUK
    a = BG.aspect_hizdan(ofs, (18.0, 0.0, 0.0))
    assert abs(math.degrees(a) - 180.0) < 1e-9
    # hedef doguya gidiyor -> BORDA
    a = BG.aspect_hizdan(ofs, (0.0, 18.0, 0.0))
    assert abs(math.degrees(a) - 90.0) < 1e-9
    # hedef bize dogru geliyor -> KARSIDAN
    a = BG.aspect_hizdan(ofs, (-18.0, 0.0, 0.0))
    assert abs(math.degrees(a)) < 1e-9
    assert BG.aspect_hizdan(ofs, (0.0, 0.0, 3.0)) is None      # yatay hiz yok


def test_durum_kestir_PAKETI_TUTARLI():
    d = BG.durum_kestir(420.0, 288.0, 34.0, 21.0, 0.45, -0.28, 1.2, 9.0)
    az, el = BG.los_seviye(420.0, 288.0, 0.45, -0.28)
    assert abs(d["az"] - az) < 1e-12 and abs(d["el"] - el) < 1e-12
    assert abs(d["psi"] - BG.sarmala_pi(1.2 + az)) < 1e-12
    assert abs(d["dz_m"] - 9.0 * math.sin(el)) < 1e-12
    assert abs(d["yatay_m"] - 9.0 * math.cos(el)) < 1e-12
    # yatay^2 + dz^2 = R^2  (kuresel ayrisim kapanmali)
    assert abs(math.hypot(d["yatay_m"], d["dz_m"]) - 9.0) < 1e-9
    assert d["sigma_R_m"] > 0.0
    assert d["kirpik"] in (True, False)


def test_durum_kestir_SIGMA_taban_ASPECTTEN():
    """Belirsizligin TABANI %18.7 (aspect bilinmiyor) -- piksel degil.
    Kutu buyudukce sigma/R bu tabana yaklasmali, ALTINA INMEMELI."""
    for wh in ((20.0, 14.0), (60.0, 42.0), (200.0, 140.0)):
        d = BG.durum_kestir(320.0, 301.0, wh[0], wh[1], 0.0, 0.0, 0.0, 10.0)
        assert d["sigma_R_m"] / 10.0 >= 0.187 - 1e-9
    d_kucuk = BG.durum_kestir(320.0, 301.0, 8.0, 6.0, 0.0, 0.0, 0.0, 10.0)
    d_buyuk = BG.durum_kestir(320.0, 301.0, 80.0, 60.0, 0.0, 0.0, 0.0, 10.0)
    assert d_kucuk["sigma_R_m"] > d_buyuk["sigma_R_m"]


# ══════════════════════════════════════════════════════════════════════════
#  9. SAFLIK ve IC TUTARLILIK
# ══════════════════════════════════════════════════════════════════════════

def test_fonksiyonlar_SAF():
    """Yan etki yok: ayni girdi iki kez -> ayni cikti; global durum degismez."""
    a1 = BG.los_seviye(400.0, 300.0, 0.3, -0.2)
    a2 = BG.los_seviye(400.0, 300.0, 0.3, -0.2)
    assert a1 == a2
    b1 = BG.acisal_boyut(400.0, 300.0, 30.0, 20.0)
    assert b1 == BG.acisal_boyut(400.0, 300.0, 30.0, 20.0)
    assert BG.tutarlilik_raporu() == BG.tutarlilik_raporu()


def _import_adlari():
    """Modulun GERCEK import ifadelerini AST ile cikarir (yorum/docstring degil)."""
    import ast
    agac = ast.parse(open(BG.__file__, "r", encoding="utf-8").read())
    adlar = set()
    for d in ast.walk(agac):
        if isinstance(d, ast.Import):
            adlar.update(a.name.split(".")[0] for a in d.names)
        elif isinstance(d, ast.ImportFrom):
            if d.module:
                adlar.add(d.module.split(".")[0])
    return adlar


def test_modul_YALNIZ_math_IMPORT_EDER():
    """⛔ SAF KUTUPHANE KILIDI: env, zaman, IO, yasa -- hicbiri girmemeli.
    Girerse tezgah ile canli yasa ayni sayiyi vermeyebilir ve modul
    test edilemez hale gelir."""
    assert _import_adlari() <= {"math", "__future__"}, _import_adlari()


def test_modul_YAN_ETKI_URETMEZ():
    """Modul govdesinde print/open/environ cagrisi olmamali (AST ile)."""
    import ast
    agac = ast.parse(open(BG.__file__, "r", encoding="utf-8").read())
    yasak = {"print", "open", "input", "exec", "eval"}
    for d in ast.walk(agac):
        if isinstance(d, ast.Call) and isinstance(d.func, ast.Name):
            assert d.func.id not in yasak, d.func.id
        if isinstance(d, ast.Attribute):
            assert d.attr not in ("environ", "getenv"), d.attr


def test_tutarlilik_raporu_kapilari():
    r = BG.tutarlilik_raporu()
    assert r["turdonus_px"] < 1e-6
    assert r["seviye_vs_duzlem_merkez_deg"] < 1e-9
    assert r["duzlem_kuresel_fark_deg"] > 1.5
    assert abs(r["cy_seviye"] - 317.68) < 0.05
    assert 3.0 < r["offaxis_sisme"] < 3.5        # sec^2(56.3 deg) = 3.25


def test_sarmala_pi():
    assert abs(BG.sarmala_pi(math.radians(359.0)) + math.radians(1.0)) < 1e-12
    assert abs(BG.sarmala_pi(math.radians(-181.0)) - math.radians(179.0)) < 1e-12


def test_kirp():
    assert BG.kirp(5.0, 0.0, 1.0) == 1.0
    assert BG.kirp(-5.0, 0.0, 1.0) == 0.0
    assert BG.kirp(0.5, 0.0, 1.0) == 0.5

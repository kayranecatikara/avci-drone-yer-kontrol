# -*- coding: utf-8 -*-
"""GORSEL FAZ DIKEY KANALI — terminal dikey rampasi + ayrik ivme tavani.

NEDEN (2026-08-17 olcumu, ayna duzeltmesi sonrasi 147 CPA):
  Gorsel TUTUS yasasi hedefi CY_NISAN=301 px'te tutar. Bu GOVDE cercevesinde
  +4.89 derece; DUNYA cercevesinde ise +4.89 + iris_pitch, ve olculen pitch
  medyani -16.1 derece oldugu icin -11.2 derece cikiyor. NEGATIF = hedef
  ufkun ALTINDA tutuluyor = ARAC HEDEFIN USTUNDEN geciyor.
  Olcum: VISUAL CPA (r<=3 m, n=35) dz medyan +0.96 m, %86'si USTTE.
  Yani dikey iska bir kontrol hatasi degil TASARIM ofsetidir ve GPS
  tarafindaki 1.553 m'lik ALT ofsetinin AYNASIDIR.

Bu testler su davranislari KILITLER:
  * elev_piksel, piksel_elev'in TAM tersi (tur-donus)
  * rampa VARSAYILAN KAPALI -> nisan bit-ayni CY_NISAN
  * rampa acikken uzakta hic dokunmaz, yakinda ES-IRTIFAYA surer
  * rampa ISARETTEN BAGIMSIZ calisir (pitch<0 ve pitch>0 iki yone de)
  * es irtifadaki hedefte rampa acikken dikey komut ~0 (kapaliyken DEGIL)
  * ayrik ivme tavani VARSAYILAN KAPALI, ve acikken tek 3B tavanin
    ustune cikabiliyor (mekanizma kapisi)
"""
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "kopru", "gazebo_kaynak"))

from control.guidance import bbox_ibvs as B          # noqa: E402
from control.guidance.common import (                # noqa: E402
    limit_acceleration, limit_acceleration_split)


class CfgKapali(B.Cfg):
    """DEVIR KAPILARI (D1 ufuk + Y1 hiz sicak) ACIKCA KAPALI.

    ⚠⚠ 2026-08-17: iki kapi da ucus A/B'sini kazandi ve VARSAYILAN ACIK
    yapildi (bkz. Cfg.DIKEY_UFUK / Cfg.HIZ_SICAK_PAY).
    Bundan sonra "kapaliyken su davranis" diyen HICBIR test modul
    varsayilanina GUVENEMEZ -- kapiyi ACIKCA kapatmak zorundadir. Aksi
    halde o testler sessizce ACIK halini olcer, yesil kalir ve
    BEKCILIK GOREVLERINI KAYBEDERLER (asil yakalamalari gereken sey,
    birinin kapiyi farkinda olmadan degistirmesidir).
    Varsayilanin kendisi ayrica asagida ACIKCA kilitlenir:
    bkz. test_varsayilanlar_UCUS_ABSI_ILE_KILITLI.
    """
    DIKEY_UFUK = False
    UFUK_ELEV_DEG = 0.0
    HIZ_SICAK_PAY = -1.0


class CfgRampa(CfgKapali):
    """Rampa ACIK, devir kapilari KAPALI — rampayi IZOLE test etmek icin."""
    TERM_DIKEY_M = 17.0      # vekil metre (~12 gercek m; bkz. Cfg.TERM_DIKEY_M)


def _nisan_dunya(cy_nisan, pitch):
    """Nisanin DUNYA cercevesindeki yukselisi (rad)."""
    return B.piksel_elev(cy_nisan) + pitch


# ══════════════════════════════════════════════════════════════════
#  1) GEOMETRI: elev_piksel <-> piksel_elev
# ══════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("cy", [120.0, 240.0, 301.0, 318.0, 400.0, 460.0])
def test_elev_piksel_tam_ters(cy):
    assert B.elev_piksel(B.piksel_elev(cy)) == pytest.approx(cy, abs=1e-6)


def test_es_irtifa_pikseli_bilinen_deger():
    """Duz ucusta (pitch=0) es irtifa CY + FY*tan(25 deg) ~ 318 px."""
    from vision import geometry as geo
    assert B.elev_piksel(0.0) == pytest.approx(geo.CY + geo.FY * math.tan(
        math.radians(25.0)), abs=1e-6)


# ══════════════════════════════════════════════════════════════════
#  2) RAMPA VARSAYILAN KAPALI -> BIT-AYNI
# ══════════════════════════════════════════════════════════════════
def test_rampa_varsayilan_kapali():
    assert B.Cfg.TERM_DIKEY_M == 0.0


@pytest.mark.parametrize("pitch_deg", [-25.0, -16.0, 0.0, 10.0])
@pytest.mark.parametrize("boyut", [5.0, 25.0, 90.0])
def test_kapaliyken_nisan_degismez(pitch_deg, boyut):
    """HER IKI KAPI da kapaliyken nisan TAM OLARAK CY_NISAN (eski davranis).
    ⚠ CfgKapali sart: modul varsayilani artik ACIK (bkz. CfgKapali)."""
    assert B.nisan_cy(math.radians(pitch_deg), boyut, CfgKapali) == B.Cfg.CY_NISAN


def test_boyut_sifirken_cokmez():
    """Kutu boyutu 0 (menzil vekili tanimsiz) -> nisan CY_NISAN'da kalir."""
    assert B.nisan_cy(math.radians(-16.0), 0.0, CfgRampa) == B.Cfg.CY_NISAN


def test_boyut_sifirken_ufuk_acikken_de_cokmez():
    """Ayni sinir, ufuk kapisi ACIKKEN: boyut=0 menzil vekilini tanimsiz
    yapar ama ufuk nisani boyuta HIC bakmaz -> yine gecerli piksel doner.
    ⚠ Kapi ACIKCA verilir; varsayilani bu test DEGIL,
    test_varsayilanlar_UCUS_ABSI_ILE_KILITLI kilitler (tek is, tek test)."""
    cy = B.nisan_cy(math.radians(-16.0), 0.0, CfgUfuk)
    assert 0.0 < cy < 480.0
    assert math.degrees(_nisan_dunya(cy, math.radians(-16.0))) == pytest.approx(
        0.0, abs=0.01)


# ══════════════════════════════════════════════════════════════════
#  3) RAMPA ACIK: uzakta dokunmaz, yakinda es irtifaya surer
# ══════════════════════════════════════════════════════════════════
def test_uzakta_rampa_dokunmaz():
    """Vekil menzil esigin USTUNDE -> nisan aynen CY_NISAN."""
    boyut_uzak = B.Cfg.MENZIL_PX_M / (CfgRampa.TERM_DIKEY_M + 5.0)
    assert B.nisan_cy(math.radians(-16.0), boyut_uzak, CfgRampa) == B.Cfg.CY_NISAN


def test_esikte_tam_surekli():
    """Esigin TAM USTUNDE ve TAM ALTINDA nisan ayni — kesiklik yok."""
    b_esik = B.Cfg.MENZIL_PX_M / CfgRampa.TERM_DIKEY_M
    ust = B.nisan_cy(math.radians(-16.0), b_esik * 0.999, CfgRampa)
    alt = B.nisan_cy(math.radians(-16.0), b_esik * 1.001, CfgRampa)
    assert ust == pytest.approx(alt, abs=0.05)


@pytest.mark.parametrize("pitch_deg", [-21.0, -16.0, -5.0, 0.0, 8.0])
def test_yakinda_es_irtifaya_yaklasir(pitch_deg):
    """Menzil kuculdukce nisanin DUNYA yukselisi 0'a gider — pitch ISARETINDEN
    BAGIMSIZ. Bu, hem 'hedefin ustunden geciyoruz' hem 'altindan geciyoruz'
    halini AYNI kod yoluyla duzeltir."""
    pitch = math.radians(pitch_deg)
    w_uzak = _nisan_dunya(B.nisan_cy(pitch, 3.0, CfgRampa), pitch)     # ~68 m
    w_orta = _nisan_dunya(B.nisan_cy(pitch, 25.0, CfgRampa), pitch)    # ~8 m
    w_yakin = _nisan_dunya(B.nisan_cy(pitch, 120.0, CfgRampa), pitch)  # ~1.7 m
    assert abs(w_uzak) >= abs(w_orta) >= abs(w_yakin)
    assert abs(w_yakin) < 0.35 * max(abs(w_uzak), 1e-9)
    assert abs(math.degrees(w_yakin)) < 2.0


def test_rampa_dunya_yukselisi_menzille_oransal():
    """W_etkin = W0 * menzil/esik — dogrudan tanimin kendisi."""
    pitch = math.radians(-16.0)
    w0 = _nisan_dunya(B.Cfg.CY_NISAN, pitch)
    for k in (0.25, 0.5, 0.75):
        boyut = B.Cfg.MENZIL_PX_M / (CfgRampa.TERM_DIKEY_M * k)
        w = _nisan_dunya(B.nisan_cy(pitch, boyut, CfgRampa), pitch)
        assert w == pytest.approx(w0 * k, abs=1e-9)


# ══════════════════════════════════════════════════════════════════
#  4) YASA CIKTISI: es irtifadaki hedefte dikey komut
# ══════════════════════════════════════════════════════════════════
def _vz(cfg, cy, boyut, pitch):
    """komut()'un dikey ciktisi (TUTUS dali)."""
    kenar = boyut          # w = h = boyut -> sqrt(w*h) = boyut
    _, _, vz, _, _, _ = B.komut(
        cx=B.Cfg.CX_NISAN, cy=cy, w=kenar, h=kenar, iris_yaw=0.0,
        hiz_I=15.0, dt=0.05, cfg=cfg, terminal=False,
        los_hiz=(0.0, 0.0), iris_pitch=pitch)
    return vz


def test_es_irtifadaki_hedefte_rampa_dikeyi_susturur():
    """Hedef TAM es irtifada (dunya yukselisi 0) ve menzil kisa:
       rampa KAPALI -> yasa hala 'alcal/tirman' diyor (tasarim ofseti)
       rampa ACIK   -> komut ~0 (nisan es irtifada)."""
    pitch = math.radians(-16.0)
    boyut = 90.0                                   # vekil ~2.3 m
    cy_es = B.elev_piksel(-pitch)                  # dunya yukselisi 0 olan piksel
    vz_kapali = _vz(CfgKapali, cy_es, boyut, pitch)
    vz_acik = _vz(CfgRampa, cy_es, boyut, pitch)
    assert abs(vz_kapali) > 1.0                    # olculen arizanin ta kendisi
    # ⚠ OLCUT ORANSAL: mutlak esik (0.25) K_VZ ile birlikte olcekleniyordu ve
    #   K_VZ oynatildiginda bu test ALAKASIZ bir sebeple kiriliyordu. Rampanin
    #   sustur(ma) orani K_VZ'den bagimsizdir (olculdu: 0.129 / 0.129).
    assert abs(vz_acik) < 0.20 * abs(vz_kapali)
    assert abs(vz_acik) < abs(vz_kapali)


def test_rampa_kapaliyken_yasa_ciktisi_degismez():
    """Kapilar kapaliyken komut() dikeyi ESKI formulun birebir aynisi.
    ⚠ CfgKapali sart: modul varsayilani artik ACIK (bkz. CfgKapali)."""
    from vision import geometry as geo
    pitch = math.radians(-16.0)
    for cy in (250.0, 301.0, 360.0):
        beklenen = max(-B.Cfg.VZ_MAX, min(B.Cfg.VZ_MAX,
                       B.Cfg.K_VZ * B.Cfg.V_NOM
                       * math.atan((cy - B.Cfg.CY_NISAN) / geo.FY)))
        assert _vz(CfgKapali, cy, 40.0, pitch) == pytest.approx(beklenen, abs=1e-9)


# ══════════════════════════════════════════════════════════════════
#  5) AYRIK IVME TAVANI (mekanizma kapisi)
# ══════════════════════════════════════════════════════════════════
def test_split_varsayilan_kapali():
    assert B.Cfg.ACCEL_SPLIT is False
    assert B.Cfg.MAX_ACCEL_V == pytest.approx(10.0)


def test_split_tek_tavanin_ustune_cikabilir():
    """MEKANIZMA KAPISI: tek 3B tavanda |dv| <= a*dt HER ZAMAN; ayrik tavanda
    bileske sqrt(12^2+10^2)=15.6'ya kadar cikabilir. Ucus logunda bu fark
    dogrudan olculebilir (>12.5 m/s^2 tik orani 0'dan buyuk olmali)."""
    dt, a_h, a_v = 0.05, 12.0, 10.0
    vp = (0.0, 0.0, 0.0)
    # her iki eksende de tavani zorlayan bir istek
    istek = (100.0, 0.0, 100.0)
    tek = limit_acceleration(*istek, *vp, a_h, dt)
    ayr = limit_acceleration_split(*istek, *vp, a_h, a_v, dt)
    n_tek = math.sqrt(sum(x * x for x in tek)) / dt
    n_ayr = math.sqrt(sum(x * x for x in ayr)) / dt
    assert n_tek == pytest.approx(a_h, abs=1e-6)
    assert n_ayr == pytest.approx(math.hypot(a_h, a_v), abs=1e-6)
    assert n_ayr > 12.5                       # kapinin esigi
    # ve DIKEY pay tam tavanda
    assert abs(ayr[2]) / dt == pytest.approx(a_v, abs=1e-6)


def test_split_yatay_doyarken_dikeyi_yemez():
    """Asil ariza buydu: yatay bileske tavani doldurunca tek 3B tavan dikey
    istegi de olceklendiriyordu. Ayrik tavanda dikey istek AYNEN gecer."""
    dt = 0.05
    vp = (0.0, 0.0, 0.0)
    istek = (100.0, 0.0, 0.3)          # yatay doygun, dikey KUCUK
    tek = limit_acceleration(*istek, *vp, 12.0, dt)
    ayr = limit_acceleration_split(*istek, *vp, 12.0, 10.0, dt)
    assert tek[2] < 0.3 * 0.1                     # dikey neredeyse tamamen yendi
    assert ayr[2] == pytest.approx(0.3, abs=1e-9)  # ayrik tavanda tam gecti


# ══════════════════════════════════════════════════════════════════
#  6) D1 · DIKEY NISAN UFKA BAGLI  (devir sicramasi, 2026-08-17)
# ══════════════════════════════════════════════════════════════════
# Bkz. Cfg.DIKEY_UFUK: nisanin GOVDE pikseli degil DUNYA yukselisi
# sabitlenir. Olcum (n=295 devir): devirden sonra dikey ayrim
# -1.45 m -> +1.55 m'ye SURUKLENIYOR ve orada kaliyor; yasanin analitik
# dengesi D* = -R*tan(piksel_elev(301)+pitch) tam bunu ongoruyor.
class CfgUfuk(B.Cfg):
    """D1 ACIK — varsayilani degistirmeden test etmek icin."""
    DIKEY_UFUK = True
    UFUK_ELEV_DEG = 0.0


class CfgUfuk2(B.Cfg):
    DIKEY_UFUK = True
    UFUK_ELEV_DEG = 2.0          # hedefin 2 derece ALTINDA kal


def test_varsayilanlar_UCUS_ABSI_ILE_KILITLI():
    """VARSAYILANI KILITLE — ucus A/B'si (2026-08-17) ne secti ise o.

    Bu test bir BEKCIDIR: birisi varsayilani sessizce oynatirsa yakalar.
    Degistirmek icin once yeni bir ucus A/B'si kosulmali; kanit
    arac/recete_gecis.json + Cfg.DIKEY_UFUK yorumundaki tablodadir.

        G0 taban -> G3 (ufuk+hiz): |dz| 1.39 -> 0.84 m, <2 m %25 -> %41,
        temas 2 -> 5.  Olumsuz kontrol G5 5/5 olcude kotulesti.
    KAZANMAYAN ve bu yuzden varsayilanda OLMAYAN iki aday:
        G4 (K_VZ=0.9)     : dikey daha iyi ama CPA 2.84 -> 3.64 m  -> ALINMADI
        G6 (UFUK_ELEV=2)  : her olcude kotu (CPA 5.53)             -> ALINMADI

    ⭐ 2026-08-18 GUNCELLEME — K_VZ 0.5 -> 0.8 ALINDI (yeni ucus A/B'si)
    Kanit: `arac/recete_kazanc.json`, SERPISTIRILMIS 4 kol, ~14 dk/kol:

        kol        yaklasma  CPA   <1.5m  <1m  |dz|@CPA  vurus
        taban_a         46   2.73   %22    %4    1.03      3
        taban_b         46   2.86   %15    %7    0.89      2
        kvz08_a         36   2.35   %25    %6    0.46      4
        kvz08_b         30   2.80   %30   %17    0.78      5

    Hedef buyukluk |dz|@CPA: taban ort. 0.96 -> 0.62 (**-0.34**).
    Gurultu tabani (10 taban cifti): medyan 0.144, **p90 0.339**
    -> fark p90'IN OTESINDE, ve iki tekrar da iki tabandan iyi.
    Bagimsiz ikinci kanit: 2026-08-18 gecesi K_VZ=0.9 tek olumlu kol
    (kapatma %69 vs %60.5). Iki ayri kampanya ayni yon.

    ⚠⚠ ESKI G4 SONUCUYLA GERILIM — SILINMEDI, OKUNSUN:
    G4 (K_VZ=0.9) CPA'yi 2.84 -> 3.64 m KOTULESTIRMISTI. Bizim olcumde
    CPA kotulesmedi (2.80 -> 2.58, gurultu icinde). Farkin muhtemel
    sebebi DENGE NOKTASI: G4, `DIKEY_UFUK` kazanmadan onceki dengeyle
    kosuldu; olculdu ki ayni kazanc yanlis dengede |dz|'yi %155
    KOTULESTIRIYOR, dogru dengede %66 IYILESTIRIYOR.
    ⚠ Yine de: bu kolun kazanci DIKEY eksende; toplam CPA anlamli
      oynamadi. K_VZ'yi daha da buyutmeden ONCE yeni A/B kosulmali
      (0.8 -> 1.1 doz kolu bu kampanyada KOSULMADI).
    """
    assert B.Cfg.DIKEY_UFUK is True,  "D1 ufuk kapisi ucus A/B'sini kazandi"
    assert B.Cfg.HIZ_SICAK_PAY == pytest.approx(1.5), "Y1 pay 1.5 m/s"
    assert B.Cfg.UFUK_ELEV_DEG == pytest.approx(0.0), "G6 kaybetti, 0 kalir"
    assert B.Cfg.K_VZ == pytest.approx(0.8), \
        "2026-08-18 A/B: |dz|@CPA 0.96 -> 0.62 (gurultu p90 0.339'un otesinde)"
    assert B.Cfg.KVZD_SEYIR == pytest.approx(0.0), \
        ("seyir sonumlemesi KAPALI kalir: asim CPA'dan +0.6..1.3 s SONRA "
         "oluyor (5 kolun 5'inde) -> vurusu etkilemiyor; ustelik |dz|@CPA'yi "
         "1.03'e KOTULESTIRDI (taban 0.96)")


def test_kapilar_env_ile_KAPATILABILIR():
    """GERI DONUS YOLU: varsayilan acik olsa da env ile eski davranisa
    donulebilmeli. Kapali yol BIT-AYNI eski davranistir."""
    assert B.nisan_cy(math.radians(-13.3), 20.0, CfgKapali) == B.Cfg.CY_NISAN
    assert float(CfgKapali.HIZ_SICAK_PAY) < 0.0


@pytest.mark.parametrize("pitch_deg", [-25.0, -13.3, 0.0, 10.0])
@pytest.mark.parametrize("boyut", [5.0, 25.0, 90.0])
def test_ufuk_kapaliyken_bit_ayni(pitch_deg, boyut):
    """⚠ CfgKapali sart: modul varsayilani artik ACIK (bkz. CfgKapali)."""
    assert B.nisan_cy(math.radians(pitch_deg), boyut, CfgKapali) == B.Cfg.CY_NISAN


@pytest.mark.parametrize("pitch_deg", [-30.0, -20.0, -13.3, -10.75, 0.0, 12.0])
def test_ufuk_acikken_nisanin_dunya_yukselisi_sifir(pitch_deg):
    """ASIL SART: nisanin DUNYA yukselisi pitch'ten BAGIMSIZ 0.
    Bu, dikey denge noktasini D* = -R*tan(0) = 0 (ES IRTIFA) yapar."""
    pitch = math.radians(pitch_deg)
    cy = B.nisan_cy(pitch, 20.0, CfgUfuk)
    assert math.degrees(_nisan_dunya(cy, pitch)) == pytest.approx(0.0, abs=0.01)


@pytest.mark.parametrize("pitch_deg", [-20.0, -13.3, 0.0])
def test_ufuk_elev_ofseti_bire_bir(pitch_deg):
    """ISARET SOZLESMESI: UFUK_ELEV_DEG=+2 -> nisanin dunya yukselisi +2
    derece, yani hedefi 2 derece YUKARIMIZDA tutariz -> BIZ hedefin
    ALTINDA kaliriz (denge D* = -R*tan(+2) < 0). Gokyuzu arka plani payi
    isteniyorsa POZITIF verilir."""
    pitch = math.radians(pitch_deg)
    cy = B.nisan_cy(pitch, 20.0, CfgUfuk2)
    assert math.degrees(_nisan_dunya(cy, pitch)) == pytest.approx(+2.0, abs=0.01)
    # ve denge noktasi gercekten ALTTA olmali
    R = 14.0
    assert -R * math.tan(_nisan_dunya(cy, pitch)) < -0.3


def test_ufuk_mekanizma_kapisi_cy_pitchle_oynar():
    """MEKANIZMA KAPISI: kapi acikken `cy_nisan` 301'de SABIT KALAMAZ ve
    pitch ile TERS yonde oynar (burun asagi -> nisan yukari/kucuk cy).
    Ucus logunda cy_nisan sutunu 301'de kaliyorsa yama devrede DEGILDIR."""
    a = B.nisan_cy(math.radians(0.0), 20.0, CfgUfuk)
    b = B.nisan_cy(math.radians(-13.3), 20.0, CfgUfuk)
    assert abs(a - B.Cfg.CY_NISAN) > 5.0
    assert abs(b - B.Cfg.CY_NISAN) > 5.0
    assert b < a                                   # burun asagi -> cy kucuk


def test_ufuk_pitch_kuplajini_kirar():
    """KOK NEDEN SINAMASI: taban yasada pitch degisimi, hedef HIC
    KIMILDAMADAN dikey komutu degistiriyor (yatay kanal dikeye sahte
    'tirman' enjekte ediyor). D1 acikken bu kuplaj SIFIRLANIR.
    Olculen tetik: devirde pitch -10.8 -> +0.75 s'de -16.1 derece."""
    boyut, cy = 12.0, 260.0            # hedefin GOVDE pikseli sabit degil;
    # ayni DUNYA konumundaki hedefin pikseli pitch ile kayar:
    #   cy(pitch) = elev_piksel(W_hedef - pitch)
    W_hedef = math.radians(4.0)         # hedef ufkun 4 derece USTUNDE, SABIT
    v_taban, v_ufuk = [], []
    for pd in (-10.8, -16.1):
        p = math.radians(pd)
        cy = B.elev_piksel(W_hedef - p)
        v_taban.append(_vz(CfgKapali, cy, boyut, p))
        v_ufuk.append(_vz(CfgUfuk, cy, boyut, p))
    # taban: hedef kimildamadigi halde komut belirgin degisiyor
    d_taban = abs(v_taban[1] - v_taban[0])
    d_ufuk = abs(v_ufuk[1] - v_ufuk[0])
    assert d_taban > 0.4
    # ufuk: komut hedefin GERCEK yerine bagli -> kuplaj pratikte YOK.
    # ⚠ OLCUT ORANSAL: mutlak esik (0.02) K_VZ ile olcekleniyordu ve
    #   K_VZ degistirildiginde bu test ALAKASIZ bir sebeple kiriliyordu.
    assert d_ufuk < 0.05 * d_taban
    # ve komut hedefin gercek yukselisini takip eder (yukarida -> TIRMAN)
    assert v_ufuk[0] < 0.0


def test_ufuk_denge_noktasi_es_irtifa():
    """Hedef TAM es irtifada -> D1 acikken dikey komut ~0; KAPALIYKEN
    (tasarim ofseti) komut belirgin sekilde sifirdan farkli."""
    for pd in (-16.0, -10.0, 0.0):
        p = math.radians(pd)
        cy_es = B.elev_piksel(-p)          # dunya yukselisi 0 olan piksel
        assert abs(_vz(CfgUfuk, cy_es, 12.0, p)) < 0.02
    assert abs(_vz(CfgKapali, B.elev_piksel(math.radians(16.0)), 12.0,
                   math.radians(-16.0))) > 1.0


def test_ufuk_asiri_pitchte_patlamaz():
    """Kurtarma gibi asiri duruslarda nisan kadrajdan kacamaz (+-120 px)."""
    for pd in (-60.0, -45.0, 40.0):
        cy = B.nisan_cy(math.radians(pd), 20.0, CfgUfuk)
        assert B.Cfg.CY_NISAN - B.NISAN_KAYMA_MAX - 1e-6 <= cy
        assert cy <= B.Cfg.CY_NISAN + B.NISAN_KAYMA_MAX + 1e-6


def test_ufuk_ve_rampa_birlikte_cakismaz():
    """Iki kapi birlikte acikken rampa TABANDAN (ufuk nisanindan) baslar;
    ufuk tabani zaten W0~0 oldugu icin rampa fiilen etkisizdir."""
    class CfgIkisi(CfgUfuk):
        TERM_DIKEY_M = 17.0
    p = math.radians(-13.3)
    for boyut in (8.0, 25.0, 90.0):
        a = B.nisan_cy(p, boyut, CfgUfuk)
        b = B.nisan_cy(p, boyut, CfgIkisi)
        assert b == pytest.approx(a, abs=0.6)


# ══════════════════════════════════════════════════════════════════
#  7) Y1 · HIZ INTEGRALININ SICAK BASLANGICI  (yatay devir sicramasi)
# ══════════════════════════════════════════════════════════════════
# Bkz. Cfg.HIZ_SICAK_PAY. Olcum (n=299 devir): ff_hiz kestirimi hedefin
# gercek hizindan %62 oraninda DUSUK, %33'unde |hata|>3 m/s; bu fazlarda
# saha EN YAKIN MENZILI 11.85 m (iyi olanlarda 3.95 m).
class _SahteKilit:
    def is_set(self):
        return True             # dongu hic donmez, yalniz kurulum kosar


def _sicak_baslangic(monkeypatch, tmp_path, ff, oz_hiz, pay=None):
    """run_bbox_ibvs'in kurulum ciktisindan hiz_I sicak baslangicini oku.

    ⚠ pay=None -> kapi ACIKCA KAPATILIR (-1.0). Once `class Cfg2(B.Cfg): pass`
    yazip pay verilmediginde dokunmuyordu; varsayilan 1.5 olunca o yol
    "kapali" testini sessizce ACIK halde kosturuyordu.
    """
    import io
    import contextlib

    class Cfg2(B.Cfg):
        pass
    Cfg2.HIZ_SICAK_PAY = -1.0 if pay is None else pay
    monkeypatch.setattr(B, "_LOG_DIR", str(tmp_path))
    # MAVLink baglantisi YOK: cikista basilan durdurma komutu yutulur.
    monkeypatch.setattr(B, "send_velocity", lambda *a, **k: None)
    yaz = io.StringIO()
    with contextlib.redirect_stdout(yaz):
        sonuc = B.run_bbox_ibvs(
            conn=None,
            get_iris=lambda: {"vx": oz_hiz, "vy": 0.0, "vz": 0.0,
                              "yaw": 0.0, "roll": 0.0, "pitch": 0.0},
            wait_pose=lambda seq, timeout=0.5: None,
            stop_event=_SahteKilit(), cfg=Cfg2, ff_hiz=ff)
    s = yaz.getvalue()
    assert sonuc in (None, "kayip", "durduruldu")
    sat = [x for x in s.splitlines() if "sıcak başlangıç" in x]
    assert sat, s
    return sat[0]


def test_hiz_sicak_KAPATILINCA_ff_aynen_gecer(monkeypatch, tmp_path):
    """Kapi ACIKCA KAPALIYKEN kotu ff (10 m/s) aynen kullanilir — bit-ayni
    eski davranis. (Varsayilan artik ACIK; bkz.
    test_varsayilanlar_UCUS_ABSI_ILE_KILITLI.)"""
    sat = _sicak_baslangic(monkeypatch, tmp_path, ff=(10.0, 0.0, 0.0),
                           oz_hiz=19.6, pay=-1.0)
    assert "kaynak=ff" in sat
    assert "10.0 m/s" in sat


def test_hiz_sicak_VARSAYILAN_kotu_ffi_kurtarir(monkeypatch, tmp_path):
    """VARSAYILAN AYARDA (pay=1.5) kotu ff artik KURTARILIR.
    Bu, kalici hale getirilen davranisin ta kendisidir: ff 10 m/s ile
    kapanma imkansizdi, taban 19.6-1.5=18.1 m/s ile mumkun."""
    class Cfg2(B.Cfg):
        pass
    sat = _sicak_baslangic(monkeypatch, tmp_path, ff=(10.0, 0.0, 0.0),
                           oz_hiz=19.6, pay=Cfg2.HIZ_SICAK_PAY)
    assert "kaynak=kendi" in sat
    assert "18.1 m/s" in sat


def test_hiz_sicak_acikken_kendi_hizimiz_taban_olur(monkeypatch, tmp_path):
    """MEKANIZMA KAPISI: kapi acikken kaynak 'kendi' yazmali ve deger
    (kendi hiz - pay) olmali. 19.6 - 1.5 = 18.1 ~ hedefin gercek hizi."""
    sat = _sicak_baslangic(monkeypatch, tmp_path, ff=(10.0, 0.0, 0.0),
                           oz_hiz=19.6, pay=1.5)
    assert "kaynak=kendi" in sat
    assert "18.1 m/s" in sat


def test_hiz_sicak_yalniz_yukari_ceker(monkeypatch, tmp_path):
    """ff zaten iyiyse (kendi hizimizdan buyukse) DOKUNULMAZ — kapi
    yalniz kotu kestirimi kurtarir, iyisini bozmaz."""
    sat = _sicak_baslangic(monkeypatch, tmp_path, ff=(21.0, 0.0, 0.0),
                           oz_hiz=19.6, pay=1.5)
    assert "kaynak=ff" in sat
    assert "21.0 m/s" in sat


def test_hiz_sicak_pay_negatifse_kapali(monkeypatch, tmp_path):
    sat = _sicak_baslangic(monkeypatch, tmp_path, ff=(5.0, 0.0, 0.0),
                           oz_hiz=19.6, pay=-1.0)
    assert "kaynak=ff" in sat


def test_tezgah_vekili_ile_gercek_kapi_ayni():
    """sim/devir.py yamayi once cfg VEKILI ile modellemisti (CY_NISAN'i kare
    kare yazarak). Gercek kapi (nisan_cy icindeki DIKEY_UFUK) AYNI pikseli
    vermeli — yoksa tezgah sonucu koda tasinmamis olur."""
    for pd in (-25.0, -13.3, 0.0, 10.0):
        p = math.radians(pd)
        vekil = B.elev_piksel(math.radians(0.0) - p)
        gercek = B.nisan_cy(p, 20.0, CfgUfuk)
        assert gercek == pytest.approx(
            max(B.Cfg.CY_NISAN - B.NISAN_KAYMA_MAX,
                min(B.Cfg.CY_NISAN + B.NISAN_KAYMA_MAX, vekil)), abs=1e-6)

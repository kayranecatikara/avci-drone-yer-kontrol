# -*- coding: utf-8 -*-
"""
IBVS DIKEY EKSEN (ASIMETRIK YASA v2) — saf matematik testleri.
Oyunsuz/SDK'siz calisir: AvciGorselGuduum sentetik bbox + vz ile beslenir,
(throttle, pitch, roll, yaw) ciktisi dogrulanir.

Kosum (repo kokunden):  python -m pytest tests/test_ibvs_dikey.py -q

v2 gerekce (2026-07-05): canli loglar ESKI ham-P kodunda isaret alttayken bile NET
TIRMANIS gosterdi; simetrik hiz-hatasi P'si (v1, hic ucmadi) de asimetrik SDK plantinda
(thr>0 = HIZ komutu, thr<0 = IVME alani) analizce limit cevrimine mahkum. Yeni yasa:
tirmanis = feedforward (vz_des/VZ_MAX), inis = vz-hatasi P'si UST KLEMP 0.0
(iniste asla tirmanis komutu yok).
Sabitler ana_kontrol.Cfg ile AYNI degerlerde yerel P sinifina klonlanir.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from guidance.ibvs_guidance import AvciGorselGuduum  # noqa: E402


class P:
    # ana_kontrol.Cfg'nin IBVS'e giren alanlari (degerler birebir ayni tutulur)
    VIS_EMA         = 0.4
    VIS_EY_REF      = 0.43
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
    VIS_W_STOP      = 0.30      # genislik-tabanli fren (eski alan yasasinin yerine; F3)
    THR_DN          = -1.00
    THR_UP          = 0.70
    VZ_MAX          = 3333.0    # oyun fizik tavani (tirmanis feedforward olcegi)


W, H = 1280.0, 720.0
BBW, BBH = 0.10 * W, 0.08 * H          # sahte-isaret bbox'u (server.py ile ayni) -> w_norm = 0.10
FWD_TAM = P.VIS_K_FWD * (1.0 - 0.10 / P.VIS_W_STOP)   # kisilmamis ileri komut = 0.26667


def cmd(ny, nx=0.5, vz=0.0, p=P):
    """Taze IBVS ile tek adim: normalize (nx,ny) isaret + kendi dikey hiz vz (cm/s)."""
    g = AvciGorselGuduum()
    return g.hesapla((nx * W, ny * H), W, H, (BBW, BBH), p, vz=vz)


def eyd(ny):
    return (2.0 * ny - 1.0) - P.VIS_EY_REF


def vz_des(ny):
    e = max(-1.0, min(1.0, P.VIS_K_VZ * eyd(ny)))
    return P.VIS_SIGN_VZ * P.VIS_VZ_MAX * e


NY_EYD02 = (1.0 + P.VIS_EY_REF + 0.2) / 2.0   # eyd=+0.2 (REF alti, kapi ici) -> ny=0.815


def test_alt_kenar_tam_inis_ve_dalis():
    # Ekranin en dibi (eyd=0.57): tam iniş istegi (-1100 cm/s) -> thr THR_DN'e doyar;
    # KOORDINELI DALIS: alt-taraf kapisi kalkti -> ileri pitch tabanda SURER (v1'de 0'di).
    g = AvciGorselGuduum()
    thr, pitch, roll, yaw = g.hesapla((0.5 * W, 1.0 * H), W, H, (BBW, BBH), P, vz=0.0)
    assert thr == pytest.approx(P.THR_DN)              # 0.002*(-1100-0)=-2.2 -> klemp -1.0
    assert pitch == pytest.approx(FWD_TAM * P.VIS_ALC_MIN)   # 0.384*0.5 = 0.192 (dalis vektoru)
    assert yaw == pytest.approx(0.0)
    assert roll == 0.0
    # gozlemlenebilirlik sozlesmesi (UI karti + ucus logu bu alanlari okur)
    assert g.son_vz_des == pytest.approx(-P.VIS_VZ_MAX)
    assert g.son_vz == pytest.approx(0.0)
    assert g.son_alc == pytest.approx(P.VIS_ALC_MIN)


def test_ref_alti_kapi_ici_inis_ve_hafif_kisma():
    # REF'in altinda, kapi icinde (eyd=0.2): inis + taban BAGLAR (1-0.2/0.35=0.43 < 0.5).
    thr, pitch, _, _ = cmd(ny=NY_EYD02)
    assert thr == pytest.approx(-0.88)                 # 0.002*(-440-0)
    assert pitch == pytest.approx(FWD_TAM * P.VIS_ALC_MIN)


def test_ref_uzerinde_hover():
    # Isaret tam REF cizgisinde, vz=0: dikey denge (thr~0), ileri tam (kisma ~yok).
    # NOT: eyd = +/-5e-17 float tozu -> hangi dala girdigini ASSERT ETME.
    ny = (1.0 + P.VIS_EY_REF) / 2.0                    # eyd=0 -> ny=0.715
    thr, pitch, _, _ = cmd(ny=ny)
    assert thr == pytest.approx(0.0)
    assert pitch == pytest.approx(FWD_TAM)


def test_ref_ustu_tirmanis_feedforward():
    # REF'in ustunde (eyd=-0.3): TIRMANIS = FEEDFORWARD hiz komutu vz_des/VZ_MAX
    # (v1 burada +0.70'e doyuyordu = 23 m/s tirmanis; artik 660/3333 = 6.6 m/s).
    ny = (1.0 + P.VIS_EY_REF - 0.3) / 2.0              # eyd=-0.3 -> ny=0.565
    thr, pitch, _, _ = cmd(ny=ny)
    assert thr == pytest.approx(660.0 / 3333.0)        # IFADE: 0.198... literali yazma
    assert pitch == pytest.approx(FWD_TAM)             # tirmanista kisma yok


def test_cok_yukarida_ust_kapi_pitch_kapali():
    # Hedef COK yukarida (eyd=-0.6 < -kapi): once tirman -> ileri pitch KAPALI;
    # thr = tam tirmanis FF'i ve THR_UP'a hic dayanmaz (1100/3333=0.33 < 0.70).
    ny = (1.0 + P.VIS_EY_REF - 0.6) / 2.0              # eyd=-0.6 -> ny=0.415
    thr, pitch, _, _ = cmd(ny=ny)
    assert thr == pytest.approx(1100.0 / 3333.0)
    assert thr < P.THR_UP
    assert pitch == 0.0


def test_yakinsamis_iniste_throttle_sifir():
    # vz istenen inis hizina ulasinca komut kendini sifirlar (thr -> 0'a yaslanir).
    thr, _, _, _ = cmd(ny=NY_EYD02, vz=vz_des(NY_EYD02))     # vz = vz_des = -440 cm/s
    assert thr == pytest.approx(0.0)


def test_asiri_dusus_freni_asla_pozitif_degil():
    # REGRESYON (v1 hatasi): asiri hizli duste "fren" POZITIF thr'ye kacamaz —
    # ust klemp 0.0 (fren = yercekimi telafisini geri ac = irtifa-tut).
    # v1 testi burada thr == THR_UP bekliyordu; o beklenti limit cevrimini KODLUYORDU.
    thr, _, _, _ = cmd(ny=NY_EYD02, vz=-1500.0)        # raw +2.12 olurdu -> klemp 0.0
    assert thr == 0.0
    for vzz in (-3000.0, -1500.0, -440.0, -100.0, 0.0, 300.0, 1100.0, 3000.0):
        t_, _, _, _ = cmd(ny=NY_EYD02, vz=vzz)         # eyd>0 -> vz_des<0: inis dali
        assert t_ <= 0.0                               # iniste ASLA tirmanis komutu yok


def test_tasima_karsiti_tam_yetki():
    # Ileri-ucus tasimasi drone'u YUKARI iterken (vz>0) inis istegi varsa tam yetki.
    thr, _, _, _ = cmd(ny=NY_EYD02, vz=+300.0)         # 0.002*(-440-300)=-1.48 -> klemp
    assert thr == pytest.approx(P.THR_DN)


def test_zarf_taramasi():
    # Her (ny, vz) kombinasyonunda cikti GPS zarfinin icinde kalir.
    for nyy in (0.0, 0.25, 0.5, 0.715, 0.815, 1.0):
        for vzz in (-3000.0, -1100.0, 0.0, 1100.0, 3000.0):
            t_, _, _, _ = cmd(ny=nyy, vz=vzz)
            assert P.THR_DN <= t_ <= P.THR_UP


def test_roll_default_kapali_ve_acilinca_oranli():
    # Kullanici spec'i: roll = SIGN_ROLL*K_ROLL*ex, "istenirse 0". Default KAPALI.
    _, _, roll, _ = cmd(ny=0.715, nx=0.9)
    assert roll == 0.0
    class P2(P):
        VIS_K_ROLL = 0.5
    _, _, roll2, _ = cmd(ny=0.715, nx=0.9, p=P2)       # ex=0.8
    assert roll2 == pytest.approx(0.5 * 0.8)
    class P3(P2):
        VIS_SIGN_ROLL = -1.0
    _, _, roll3, _ = cmd(ny=0.715, nx=0.9, p=P3)
    assert roll3 == pytest.approx(-0.5 * 0.8)


def test_yaw_dikeyden_bagimsiz():
    # Regresyon korkulugu: dikey yasa calisan yaw yolunu ETKILEMEZ.
    for vzz in (0.0, -800.0):
        _, pitch, _, yaw = cmd(ny=1.0, nx=0.9, vz=vzz)
        assert yaw == pytest.approx(P.VIS_SIGN_YAW * P.VIS_K_YAW * 0.8)
        assert pitch == 0.0                            # |ex|=0.8 > kapi -> ileri yok


def test_kor_devam_sonumleme():
    # Kor-devamda son goruntu hatasi tasinir ama inis dali CANLI vz ile calisir.
    g = AvciGorselGuduum()
    g.hesapla((0.5 * W, NY_EYD02 * H), W, H, (BBW, BBH), P, vz=0.0)
    thr_dengede, _, _, _ = g.kor_devam(P, vz=vz_des(NY_EYD02))   # vz hedefte -> ~0
    assert thr_dengede == pytest.approx(0.0)
    thr_hover, _, _, _ = g.kor_devam(P, vz=0.0)                  # duruyor -> inis komutu
    assert thr_hover == pytest.approx(-0.88)
    taze = AvciGorselGuduum()
    assert taze.kor_devam(P) == (0.0, 0.0, 0.0, 0.0)             # hic tespit yok -> hover

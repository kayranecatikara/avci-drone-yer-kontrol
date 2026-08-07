# -*- coding: utf-8 -*-
"""FAZ 1 kopru birim testleri: cerceve donusumu tersinirligi + kontrolcu
isaret/kirpma/slew/bayat davranislari. Oyun GEREKMEZ (FakeSDK)."""
import math

import pytest

from kopru.dow_kopru import (
    Cfg, DowKopru, dow_to_ned_vek, ned_to_dow_vek, dow_yaw_to_ned,
    ned_yaw_to_dow, sarmala_pi, send_velocity, yatay_trim_stick,
)


class FakeSDK:
    """DoW SDK'nin kopru tarafindan kullanilan yuzeyi (cm / cm-s / derece)."""

    def get_debug_truth(self):
        return self.truth

    def __init__(self):
        self.truth = {"available": False,
                      "drone": {"position": (0.0, 0.0, 0.0)},
                      "target": {"position": (0.0, 0.0, 0.0)}}
        self.telemetry = {
            "drone": {
                "position": (0.0, 0.0, 3000.0),      # cm (30 m irtifa)
                "rotation": (0.0, 0.0, 0.0),         # derece
                "velocity": (0.0, 0.0, 0.0),         # cm/s
                "speed": 0.0, "altitude": 3000.0,
            },
            "target": {
                "position": (10000.0, 0.0, 3000.0),
                "rotation": (0.0, 0.0, 0.0),
                "speed": 0.0,
            },
        }
        self.gonderilen = []          # (thr, pitch, roll, yaw, arm) kayitlari
        self.armed = None

    def get_telemetry(self):
        return self.telemetry

    def get_drone_altitude(self):
        return self.telemetry["drone"]["position"][2]

    def set_control_surfaces(self, thr, pitch, roll, yaw, arm):
        self.gonderilen.append((thr, pitch, roll, yaw, arm))

    def set_arm(self, s):
        self.armed = s


def _cfg_kopya(**degisiklik):
    """Cfg'nin test-yerel alt sinifi (global Cfg kirlenmez)."""
    return type("CfgTest", (Cfg,), degisiklik)


def _kopru(sdk=None, **cfg_degisiklik):
    return DowKopru(sdk or FakeSDK(), cfg=_cfg_kopya(**cfg_degisiklik))


def _tikla(k, n, dt=0.02, sp=(0.0, 0.0, 0.0), yaw=0.0):
    """Her tik taze setpoint yaz + bir kontrol adimi kos (bayat tetiklenmez)."""
    for _ in range(n):
        k.set_hiz_ned(sp[0], sp[1], sp[2], yaw)
        k.adim(dt=dt)
    return k.sdk.gonderilen[-1]


# ── Cerceve donusumu ─────────────────────────────────────────────────────────

def test_vektor_tersinir():
    for v in [(1.0, 2.0, 3.0), (-4.5, 0.0, 9.9), (0.001, -0.002, 0.0),
              (123.4, -567.8, 91.2)]:
        assert ned_to_dow_vek(dow_to_ned_vek(v)) == v
        assert dow_to_ned_vek(ned_to_dow_vek(v)) == v


def test_vektor_bilinen_deger():
    # DoW (x, y, z-yukari) -> NED (kuzey, dogu, asagi): y ve z isaret degistirir
    assert dow_to_ned_vek((1.0, 2.0, 3.0)) == (1.0, -2.0, -3.0)
    assert ned_to_dow_vek((1.0, -2.0, -3.0)) == (1.0, 2.0, 3.0)


def test_yaw_tersinir():
    for i in range(-40, 41):
        a = i * 0.1 * math.pi
        geri = dow_yaw_to_ned(ned_yaw_to_dow(a))
        assert abs(sarmala_pi(a - geri)) < 1e-12


def test_yaw_bilinen_deger():
    assert dow_yaw_to_ned(0.0) == 0.0
    assert abs(dow_yaw_to_ned(math.pi / 2) - (-math.pi / 2)) < 1e-12
    assert abs(ned_yaw_to_dow(-math.pi / 4) - (math.pi / 4)) < 1e-12


# ── Giris adaptorleri ───────────────────────────────────────────────────────

def test_get_iris_birim_ve_cerceve():
    sdk = FakeSDK()
    sdk.telemetry["drone"]["position"] = (1000.0, 2000.0, 3000.0)   # cm
    sdk.telemetry["drone"]["velocity"] = (100.0, -200.0, 300.0)     # cm/s
    sdk.telemetry["drone"]["rotation"] = (10.0, 20.0, 30.0)         # derece
    iris = _kopru(sdk).get_iris()
    assert iris["x"] == pytest.approx(10.0)     # cm -> m
    assert iris["y"] == pytest.approx(-20.0)    # y cevrilir
    assert iris["z"] == pytest.approx(-30.0)    # z-yukari -> z-asagi
    assert iris["vx"] == pytest.approx(1.0)
    assert iris["vy"] == pytest.approx(2.0)     # -(-2)
    assert iris["vz"] == pytest.approx(-3.0)
    assert iris["roll"] == pytest.approx(math.radians(10.0))
    # pitch AYNEN gecer (iki konvansiyonda da burun-yukari pozitif; taslaktaki
    # -pitch hatasi duzeltildi)
    assert iris["pitch"] == pytest.approx(math.radians(20.0))
    assert iris["yaw"] == pytest.approx(-math.radians(30.0))


def test_get_plane_cerceve_ve_frozen():
    sdk = FakeSDK()
    sdk.telemetry["target"]["position"] = (1000.0, 2000.0, 3000.0)
    sdk.telemetry["target"]["rotation"] = (0.0, 0.0, 45.0)
    k = _kopru(sdk)
    p1 = k.get_plane()
    assert (p1["x"], p1["y"], p1["z"]) == pytest.approx((10.0, -20.0, -30.0))
    assert p1["yaw"] == pytest.approx(-math.radians(45.0))
    assert p1["frozen"] is False                 # ilk okuma taze sayilir
    assert k.get_plane()["frozen"] is True       # deger degismedi -> donuk
    sdk.telemetry["target"]["position"] = (1100.0, 2000.0, 3000.0)
    assert k.get_plane()["frozen"] is False      # yeni deger -> taze


# ── Dikey kanal ─────────────────────────────────────────────────────────────

def test_dikey_isaret_tirmanma():
    # NED vz = -2 (yukari 2 m/s) + olculen 0 -> throttle TRIM'in USTUNE cikmali
    # (mutlak isaret degil TRIM'e gore: DoW'da hover gazi ~-0.60 OLCULDU)
    k = _kopru()
    son = _tikla(k, 20, sp=(0.0, 0.0, -2.0))
    assert son[0] - Cfg.THR_TRIM > 0.35          # FF 0.06 + P 0.44 civari
    assert k.son_tani["vz_up_sp"] == pytest.approx(2.0)


def test_dikey_isaret_alcalma():
    # NED vz = +2 (asagi) -> throttle TRIM'in ALTINA inmeli (isaret tuzagi kaniti)
    k = _kopru()
    son = _tikla(k, 20, sp=(0.0, 0.0, 2.0))
    assert son[0] - Cfg.THR_TRIM < -0.35


def test_dikey_slew_tik_basina_sinirli():
    # rate-limit: ardisik gonderimler arasi fark hicbir kanalda MAX_DELTA'yi asamaz
    k = _kopru()
    _tikla(k, 25, sp=(0.0, 0.0, -3.0))
    g = k.sdk.gonderilen
    for i in range(1, len(g)):
        for kanal in range(4):
            assert abs(g[i][kanal] - g[i - 1][kanal]) <= Cfg.MAX_DELTA + 1e-9


def test_dikey_integral_yetki_tavani():
    # KP/FF sifirlanmis cfg: integral tek basina I_VZ_MAX'i ASAMAZ
    k = _kopru(KP_VZ=0.0, FF_VZ=0.0)
    _tikla(k, 400, sp=(0.0, 0.0, -2.0))          # e_vz = +2 kalici
    assert k._i_vz == pytest.approx(k.cfg.I_VZ_MAX)


def test_dikey_antiwindup_doygunlukta_birikmez():
    # Buyuk hata -> thr_ham doygun -> integral BIRIKMEMELI
    k = _kopru()
    _tikla(k, 100, sp=(0.0, 0.0, -10.0))         # thr_ham ~2.5 >> THR_UP
    assert k._i_vz == pytest.approx(0.0)
    assert k.son_tani["thr_doydu"] == 1
    assert k.sdk.gonderilen[-1][0] <= k.cfg.THR_UP + 1e-9


def test_dikey_hiz_kaynak_sonlu_fark():
    # kaynak=sonlu_fark: komut SDK velocity'yi degil fd kestirimini kullanmali
    k = _kopru(HIZ_KAYNAK="sonlu_fark")
    k.sdk.telemetry["drone"]["velocity"] = (0.0, 0.0, 500.0)   # SDK 5 m/s der
    k._fd_vz = 0.0                                             # fd 0 der
    k.set_hiz_ned(0.0, 0.0, 0.0, 0.0)
    k.adim(dt=0.02)
    assert k.son_tani["e_vz"] == pytest.approx(0.0)            # fd kullanildi
    assert k.son_tani["vz_up_sdk"] == pytest.approx(5.0)       # log ikisini gorur
    k2 = _kopru(HIZ_KAYNAK="sdk")
    k2.sdk.telemetry["drone"]["velocity"] = (0.0, 0.0, 500.0)
    k2.set_hiz_ned(0.0, 0.0, 0.0, 0.0)
    k2.adim(dt=0.02)
    assert k2.son_tani["e_vz"] == pytest.approx(-5.0)          # sdk kullanildi


def test_vz_sonlu_fark_kestirimi():
    k = _kopru()
    k._vz_sonlu_fark(30.0, 100.0)
    for i in range(1, 60):                        # 2 m/s tirmanis, 50 Hz
        v = k._vz_sonlu_fark(30.0 + 2.0 * i * 0.02, 100.0 + i * 0.02)
    assert v == pytest.approx(2.0, abs=0.05)      # EMA yakinsadi
    v2 = k._vz_sonlu_fark(35.0, 102.0)            # 0.82 s bosluk -> reset
    assert v2 == v                                 # bayat aralikta guncelleme yok


# ── Yaw kanali ──────────────────────────────────────────────────────────────

def test_yaw_sarma_kisa_yol():
    # olculen +170 deg (DoW), hedef -170 deg (DoW) -> hata +20 deg (sarma), -340 DEGIL
    sdk = FakeSDK()
    sdk.telemetry["drone"]["rotation"] = (0.0, 0.0, 170.0)
    k = _kopru(sdk)
    _tikla(k, 1, yaw=dow_yaw_to_ned(math.radians(-170.0)))
    assert k.son_tani["yaw_hata_deg"] == pytest.approx(20.0, abs=1e-6)
    assert k.sdk.gonderilen[-1][3] > 0            # pozitif yonde don


def test_yaw_hata_kirpma_kacak_korumasi():
    # 170 deg hata -> +-90'a kirpilir (kacak korumasi)
    sdk = FakeSDK()
    k = _kopru(sdk)
    _tikla(k, 1, yaw=dow_yaw_to_ned(math.radians(170.0)))
    assert k.son_tani["yaw_hata_deg"] == pytest.approx(90.0)


def test_yaw_deadband():
    sdk = FakeSDK()
    k = _kopru(sdk)
    _tikla(k, 5, yaw=dow_yaw_to_ned(math.radians(2.0)))    # 2 deg < 3 deg bant
    assert k.sdk.gonderilen[-1][3] == pytest.approx(0.0)


def test_yaw_komut_tavani():
    sdk = FakeSDK()
    k = _kopru(sdk)
    son = _tikla(k, 30, yaw=dow_yaw_to_ned(math.radians(90.0)))
    # 90 deg hata: 1.3 * 1.571 = 2.04 -> YAW_MAX 0.60'a kirpilir
    assert son[3] == pytest.approx(k.cfg.YAW_MAX)


# ── Bayat setpoint / guvenli birakma ────────────────────────────────────────

def test_bayat_setpoint_hover():
    k = _kopru()
    k._i_vz = 0.30
    for _ in range(20):
        k.adim(dt=0.02)                           # hic setpoint yazilmadi -> bayat
    assert k.son_tani["bayat"] == 1
    son = k.sdk.gonderilen[-1]
    # guvenli birakma: thr TRIM'e oturur (olculen denge gazi), sticks sifir
    assert son[0] == pytest.approx(Cfg.THR_TRIM)
    assert son[1:4] == (0.0, 0.0, 0.0)
    assert k._i_vz == pytest.approx(0.30)         # bayatta integral DONUK


def test_bayat_suresi_asiminda_devreye_girer():
    k = _kopru()
    k.set_hiz_ned(0.0, 0.0, -2.0, 0.0)
    k.adim(dt=0.02)
    assert k.son_tani["bayat"] == 0
    k._t_sp -= (k.cfg.BAYAT_S + 0.05)             # setpoint'i yapay eskit
    k.adim(dt=0.02)
    assert k.son_tani["bayat"] == 1


# ── Faz bayraklari / olcum kancalari ────────────────────────────────────────

def test_yatay_kapali_pitch_roll_sifir():
    # FAZ 1: buyuk yatay hiz istegi bile pitch/roll uretmemeli
    k = _kopru()
    son = _tikla(k, 30, sp=(10.0, -10.0, 0.0))
    assert son[1] == pytest.approx(0.0)           # pitch
    assert son[2] == pytest.approx(0.0)           # roll
    assert k._i_fwd == 0.0 and k._i_right == 0.0


def test_pitch_sabit_kancasi():
    k = _kopru(PITCH_SABIT=0.30)
    son = _tikla(k, 10, sp=(0.0, 0.0, 0.0))
    assert son[1] == pytest.approx(0.30)          # slew ile 0.30'a oturdu


def test_roll_sabit_kancasi():
    k = _kopru(ROLL_SABIT=-0.20)
    son = _tikla(k, 10, sp=(0.0, 0.0, 0.0))
    assert son[2] == pytest.approx(-0.20)


# ── Yatay trim + PI (Faz 2) ─────────────────────────────────────────────────

def test_yatay_trim_interpolasyon():
    # OLCULMUS tablo (2026-08-06 f2trim): dugum noktalari + ara + isaret + ekstrap
    n = Cfg.YATAY_TRIM_NOKTA
    assert yatay_trim_stick(0.0, n) == 0.0
    assert yatay_trim_stick(8.7, n) == pytest.approx(0.10)
    assert yatay_trim_stick(17.6, n) == pytest.approx(0.20)
    # ara nokta: (8.7,0.10)-(13.2,0.15) arasi 10.95 -> 0.125
    assert yatay_trim_stick(10.95, n) == pytest.approx(0.125)
    assert yatay_trim_stick(-17.6, n) == pytest.approx(-0.20)    # isaretli/simetrik
    # son parcanin egimiyle ekstrapolasyon: (0.45-0.30)/(32.9-26.2)=0.02239 per m/s
    assert yatay_trim_stick(36.0, n) == pytest.approx(
        0.45 + 0.02239 * (36.0 - 32.9), abs=1e-3)


def test_yatay_kapali_cevrim_ileri_isaret():
    # yaw=0'da NED kuzey (+x) hiz istegi -> POZITIF pitch (ileri), roll ~0
    k = _kopru(YATAY_AKTIF=True)
    son = _tikla(k, 20, sp=(10.0, 0.0, 0.0))
    assert son[1] > 0.30                          # trim(10)=0.05 + P 0.4
    assert abs(son[2]) < 1e-6
    assert k.son_tani["e_fwd"] == pytest.approx(10.0)


def test_yatay_kapali_cevrim_yanal_isaret():
    # yaw=0'da NED dogu (+y) istegi -> POZITIF roll (saga strafe; e_right tuzagi)
    k = _kopru(YATAY_AKTIF=True)
    son = _tikla(k, 20, sp=(0.0, 5.0, 0.0))
    assert son[2] > 0.15
    assert abs(son[1]) < 1e-6
    assert k.son_tani["e_right"] == pytest.approx(5.0)


def test_yatay_cerceve_yaw90():
    # arac DoW-yaw 90'a donukken NED kuzey istegi GOVDE SAGINA duser -> roll
    sdk = FakeSDK()
    sdk.telemetry["drone"]["rotation"] = (0.0, 0.0, 90.0)
    k = _kopru(sdk, YATAY_AKTIF=True)
    son = _tikla(k, 20, sp=(5.0, 0.0, 0.0))
    assert son[2] > 0.15                          # roll (+, sag)
    assert abs(son[1]) < 1e-6                     # pitch ~0


def test_yatay_integral_yetki_ve_doyum():
    # bant-ici kucuk hata: integral I_VH_MAX'ta kirpilir
    k = _kopru(YATAY_AKTIF=True, KP_VH=0.0,
               YATAY_TRIM_NOKTA=((0.0, 0.0), (50.0, 0.0)))
    _tikla(k, 700, sp=(2.0, 0.0, 0.0))            # hata 2.0 <= bant 2.5
    assert k._i_fwd == pytest.approx(k.cfg.I_VH_MAX)
    # doygun eksen: integral DONUK (bant devre disi birakilarak izole test)
    k2 = _kopru(YATAY_AKTIF=True, E_VH_INT_BAND=1e9)
    _tikla(k2, 50, sp=(30.0, 0.0, 0.0))           # ham ~1.1 >> PITCH_MAX
    assert k2._i_fwd == pytest.approx(0.0)


def test_yatay_integral_buyuk_hatada_birikmez():
    # WINDUP KAPISI (f2adim olcumu): buyuk hata rampasinda integral DOLMAZ —
    # doymamis stick'te bile |e| > E_VH_INT_BAND ise i sabit kalir.
    k = _kopru(YATAY_AKTIF=True)
    _tikla(k, 100, sp=(10.0, 0.0, 0.0))           # e=10 >> bant 2.5; ham ~0.35 doymamis
    assert k._i_fwd == pytest.approx(0.0)


def test_yaw_sabit_kancasi():
    sdk = FakeSDK()
    sdk.telemetry["drone"]["rotation"] = (0.0, 0.0, 100.0)   # kontrolcu 0.6 isterdi
    k = _kopru(sdk, YAW_SABIT=0.30)
    son = _tikla(k, 10, yaw=0.0)
    assert son[3] == pytest.approx(0.30)


def test_gnss_duzeltici_varsayilan_acik():
    # Onaylanan varsayilan (2026-08-06): CT-EKF ACIK. Tek satirla geri alinabilir.
    assert Cfg.GNSS_DUZELTICI_AKTIF is True
    assert Cfg.GNSS_TELAFI_SN == pytest.approx(1.0)
    assert Cfg.GNSS_DT == pytest.approx(0.23)


def test_gnss_duzeltici_kapali_ham_gecer():
    # Bayrak KAPALI: get_plane HAM konumu verir — filtre oncesi davranis bit-ayni
    sdk = FakeSDK()
    sdk.telemetry["target"]["position"] = (12345.0, -6789.0, 5000.0)
    k = _kopru(sdk, GNSS_DUZELTICI_AKTIF=False)
    p = k.get_plane()
    assert p["x"] == pytest.approx(123.45)
    assert p["y"] == pytest.approx(67.89)
    assert k._gnss is None                        # filtre hic kurulmadi


def test_gnss_duzeltici_acikken_filtre_zinciri():
    # Bayrak ACIK: CT-EKF kurulur, YALNIZ taze pakette guncellenir, donukta
    # son cikti korunur (yasanin tazelik kapisi bozulmaz).
    sdk = FakeSDK()
    k = _kopru(sdk, GNSS_DUZELTICI_AKTIF=True, GNSS_DT=0.23, GNSS_TELAFI_SN=1.0)
    # duz ucan hedef: her cagride 4 m ilerlesin (cm)
    for i in range(40):
        sdk.telemetry["target"]["position"] = (10000.0 + i * 400.0, 0.0, 6000.0)
        p = k.get_plane()
        assert p["frozen"] is False
    assert k._gnss is not None
    # filtre isindi ve konum kestirimi uretiyor (telafi_sn ile ONE tasinmis)
    assert k._gnss_cikti is not None
    x_ham = 10000.0 + 39 * 400.0
    # lead: 1 s telafi, hiz ~ 4 m / 0.23 s -> kestirim ham'in ILERISINDE olmali
    assert k._gnss_cikti[0] > x_ham / 100.0
    # DONUK kare: ayni ham -> cikti DEGISMEZ, filtre zaman ilerletmez
    onceki = k._gnss_cikti
    p2 = k.get_plane()
    assert p2["frozen"] is True
    assert k._gnss_cikti == onceki


def test_gnss_duzeltici_hata_zarif_duser():
    # Filtre patlarsa guduum durmaz: HAM konuma duser, bir kez uyarir
    sdk = FakeSDK()
    k = _kopru(sdk, GNSS_DUZELTICI_AKTIF=True)

    class Patlak:
        def guncelle(self, *a):
            raise RuntimeError("test")
    k._gnss = Patlak()
    sdk.telemetry["target"]["position"] = (5000.0, 0.0, 3000.0)
    p = k.get_plane()
    assert p["x"] == pytest.approx(50.0)          # HAM konum kullanildi
    assert k._gnss_uyari is True


def test_hedef_truth_modu():
    # TESHIS bayragi: get_plane bozuk kanali HIC okumaz, truth'tan besler,
    # CT-EKF baypas edilir. Cerceve/birim cevrimi AYNEN korunur.
    sdk = FakeSDK()
    sdk.telemetry["target"]["position"] = (99999.0, 99999.0, 99999.0)   # bozuk
    sdk.truth = {"available": True,
                 "drone": {"position": (0.0, 0.0, 4840.0)},
                 "target": {"position": (1000.0, 2000.0, 6000.0)}}      # cm
    k = _kopru(sdk, HEDEF_TRUTH_AKTIF=True, GNSS_DUZELTICI_AKTIF=True,
               NED_ZEMIN_M=48.4)
    p = k.get_plane()
    assert p["x"] == pytest.approx(10.0)          # truth, cm->m
    assert p["y"] == pytest.approx(-20.0)         # y cevrildi
    assert p["z"] == pytest.approx(-(60.0 - 48.4))
    assert k._gnss is None                        # CT-EKF BAYPAS (kurulmadi bile)
    # bayrak kapaninca eski hal: bozuk kanal geri gelir
    k2 = _kopru(sdk, HEDEF_TRUTH_AKTIF=False, GNSS_DUZELTICI_AKTIF=False)
    assert k2.get_plane()["x"] == pytest.approx(999.99)


def test_hedef_truth_yoksa_gurultulu_patlar():
    # truth kapaliyken teshis modu SESSIZCE bozuk veriye dusmemeli
    sdk = FakeSDK()
    k = _kopru(sdk, HEDEF_TRUTH_AKTIF=True)
    with pytest.raises(RuntimeError):
        k.get_plane()


def test_ned_zemin_kaydirmasi():
    # Faz 3.1: NED z = -(dow_z - zemin) -> yasanin gordugu irtifa AGL olur
    # (gps_guidance LOOKUP_MIN_ALT=8 korumasi ancak boyle calisir).
    sdk = FakeSDK()
    sdk.telemetry["drone"]["position"] = (0.0, 0.0, 5000.0)     # dunya-z 50 m
    sdk.telemetry["drone"]["velocity"] = (0.0, 0.0, 300.0)      # +3 m/s tirmanis
    sdk.telemetry["target"]["position"] = (1000.0, 0.0, 6000.0)  # dunya-z 60 m
    k = _kopru(sdk, NED_ZEMIN_M=48.4)
    iris = k.get_iris()
    assert iris["z"] == pytest.approx(-(50.0 - 48.4))           # -1.6 (1.6 m AGL)
    assert iris["vz"] == pytest.approx(-3.0)                    # hiza kaydirma YOK
    assert k.get_plane()["z"] == pytest.approx(-(60.0 - 48.4))  # -11.6
    # varsayilan 0 = eski davranis
    k0 = _kopru(FakeSDK())
    k0.sdk.telemetry["drone"]["position"] = (0.0, 0.0, 5000.0)
    assert k0.get_iris()["z"] == pytest.approx(-50.0)


def test_kalkis_zemin_referansi():
    # 2026-08-06 kazasi dersi: get_drone_altitude DUNYA-Z'dir. Spawn zemini
    # z=48.4 m'deyken eski mutlak esik yerde "kalkis tamam" diyordu.
    sdk = FakeSDK()
    sdk.telemetry["drone"]["position"] = (0.0, 0.0, 4840.0)   # yerde, zemin 48.4 m
    k = _kopru(sdk)
    # zemin referansiyla: 48.4 m dunya-z arac YERDE demek -> hedefe ulasamaz
    assert k.kalkis(30.0, zaman_asimi_s=0.15, zemin_m=48.4) is False
    assert any(g[0] == pytest.approx(Cfg.KALKIS_THR, abs=0.3)
               for g in sdk.gonderilen)           # tirmanma komutu gonderildi
    # gercekten zemin+30'un ustundeyse aninda tamam
    sdk.telemetry["drone"]["position"] = (0.0, 0.0, 7900.0)   # 79 m > 48.4+30-1.5
    assert k.kalkis(30.0, zaman_asimi_s=0.15, zemin_m=48.4) is True


def test_send_velocity_yalniz_setpoint_yazar():
    k = _kopru()
    n_once = len(k.sdk.gonderilen)
    send_velocity(k, 1.0, 2.0, 3.0, 0.5)
    assert k._sp_ned == (1.0, 2.0, 3.0)
    assert k._sp_yaw_ned == 0.5
    assert k._t_sp is not None
    assert len(k.sdk.gonderilen) == n_once        # komut GONDERMEDI (adim isi)

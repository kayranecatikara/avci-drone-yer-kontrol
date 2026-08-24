# -*- coding: utf-8 -*-
"""KesintisizKilit — GERCEK "5 s kesintisiz kilit" kapisi (2026-08-17).

Testler su davranislari KILITLER:
  * KESINTISIZ sayim (KilitSayaci'nin KUMULATIF sayimindan farkli)
  * kapi VARSAYILAN KAPALI -> gecti() hep True (davranis bit-ayni)
  * hayalet kare kilide SAYILMAZ
  * conf esigi / kadraj disi kare kilide SAYILMAZ
  * bosluk toleransi: kucuk bosluk sureyi sifirlamaz, buyuk bosluk KIRAR
  * denetim ozeti bagimsiz dogrulanabilir (fark_s == kesintisiz_kilit_s)
"""
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "kopru", "gazebo_kaynak"))

from control.guidance.kesintisiz_kilit import (  # noqa: E402
    KesintisizKilit, KilitKapiCfg)


def det(conf=0.8, cx=320.0, cy=240.0, w=40.0, h=14.0):
    """Yasa cercevesi (640x480) tespiti."""
    return {"cx": cx, "cy": cy, "w": w, "h": h, "conf": conf}


class Cfg5(KilitKapiCfg):
    """Kapi ACIK: 5 s esik, AMA eski tolerans/doluluk tanimlariyla.

    ⚠ 2026-08-17: varsayilanlar ucus A/B'siyle DEGISTI (ESIK_S 5.0,
    CONF_MIN 0.25, BOSLUK_MOD "sure", DOLULUK_MIN 0.80). Bu sinif eski
    TANIMLARI acikca sabitler ki asagidaki davranis testleri varsayilan
    degisiminden ETKILENMESIN ve bekcilik gorevleri korunsun."""
    ESIK_S = 5.0
    CONF_MIN = 0.35
    BOSLUK_MOD = "kare"
    DOLULUK_MIN = 0.0


class CfgEski(KilitKapiCfg):
    """Kapi KAPALI + eski tanimlar = 2026-08-17 oncesi davranis (bit-ayni)."""
    ESIK_S = 0.0
    CONF_MIN = 0.35
    BOSLUK_MOD = "kare"
    DOLULUK_MIN = 0.0


# ───────────────────────────────────────────────────── temel kesintisiz sayim
def test_kesintisiz_sure_birikir():
    kk = KesintisizKilit()
    for i in range(101):                 # 101 kare @20 Hz = 5.00 s
        kk.guncelle(det(), i * 0.05)
    assert abs(kk.sure - 5.0) < 1e-6
    assert kk.kare == 101


def test_kilit_kapisi_KAPALI_kullanici_talimati():
    """⛔ 2026-08-18 KULLANICI TALIMATI: "kiliti komple bos ver, sisteme dahil
    etme, calistirma". Kapi KAPALI olmali.

    Olculen sonuc kaybolmadi -- `arac/KILIT_BULGUSU.md`'de duruyor:
      kapi ACIK 5 s -> GPS_VISUAL %100 / TERMINAL %100 >=5 s, min 5.00 s,
      50 gecis SIFIR ihlal, vurus 2->2, en yakin 0.81 -> 0.46 m.
    Yani kapi CALISIYOR; kapatilma sebebi olcum degil, oncelik.
    """
    assert KilitKapiCfg.ESIK_S == 0.0, (
        "kullanici kilidi sistemden CIKARMAMIZI istedi; acmak icin "
        "AVCI_KILIT_S=5 (bkz. arac/KILIT_BULGUSU.md)")
    assert KilitKapiCfg.DOLULUK_MIN == 0.0
    assert not KilitKapiCfg.acik()
    # ⚠ Denetim KAYDI yine de tutulur -- olcum enstrumaniz, davranis degil.
    assert KilitKapiCfg.SART_S == 5.0



def test_kapi_KAPATILINCA_eski_davranis_bit_ayni():
    """AVCI_KILIT_S=0 -> hicbir kilit olmasa bile gecti() True.
    Kapi kapatilabilir olmali (geri donus yolu)."""
    kk = KesintisizKilit(cfg=CfgEski)
    assert not CfgEski.acik()
    assert kk.gecti() is True             # hic kare beslenmeden bile
    kk.guncelle(None, 0.0)
    assert kk.sure == 0.0
    assert kk.gecti() is True


def test_kapi_ACIK_esik_dolmadan_gecirmez():
    kk = KesintisizKilit(cfg=Cfg5)
    for i in range(60):                   # 60 kare @20 Hz = 2.95 s
        kk.guncelle(det(), i * 0.05)
    assert kk.sure < 5.0
    assert kk.gecti() is False
    for i in range(60, 101):
        kk.guncelle(det(), i * 0.05)
    assert kk.sure >= 5.0
    assert kk.gecti() is True


# ───────────────────────────────────────────────────────── kilit TANIMI
def test_hayalet_kare_kilide_sayilmaz():
    kk = KesintisizKilit(cfg=Cfg5)
    for i in range(20):
        kk.guncelle(det(), i * 0.05)
    once = kk.sure
    # ust uste hayalet kare -> tolerans asilir -> kilit KIRILIR
    for i in range(20, 30):
        kk.guncelle(None, i * 0.05, hayalet=True)
    assert kk.sure == 0.0, "hayalet kare kilidi surdurmemeli (once %.2f)" % once
    assert kk.hayalet_top == 10


def test_dusuk_conf_sayilmaz():
    kk = KesintisizKilit(cfg=Cfg5)
    for i in range(30):
        kk.guncelle(det(conf=0.10), i * 0.05)      # esik 0.35
    assert kk.sure == 0.0
    assert kk.kare == 0


def test_kadraj_disi_sayilmaz():
    kk = KesintisizKilit(cfg=Cfg5)
    for i in range(30):
        kk.guncelle(det(cx=5.0), i * 0.05)         # 640 px cercevede kenarda
    assert kk.sure == 0.0


def test_bos_kutu_sayilmaz():
    kk = KesintisizKilit(cfg=Cfg5)
    for i in range(30):
        kk.guncelle(det(w=0.0, h=0.0), i * 0.05)
    assert kk.sure == 0.0


# ─────────────────────────────────────────────────────── bosluk toleransi
def test_kucuk_bosluk_kilidi_kirmaz():
    """1 kare bosluk (tolerans 3) sureyi SIFIRLAMAZ — dedektor titremesi."""
    kk = KesintisizKilit(cfg=Cfg5)
    t = 0.0
    for i in range(40):
        kk.guncelle(det(), t); t += 0.05
    kk.guncelle(None, t); t += 0.05           # tek bosluk kare
    kk.guncelle(det(), t)
    assert kk.sure > 1.9, "tek bosluk kilidi kirmamali (sure %.2f)" % kk.sure
    assert kk.bosluk_top == 1


def test_uzun_bosluk_kilidi_KIRAR():
    kk = KesintisizKilit(cfg=Cfg5)
    t = 0.0
    for i in range(40):
        kk.guncelle(det(), t); t += 0.05
    for i in range(5):                        # 5 > BOSLUK_KARE(3)
        kk.guncelle(None, t); t += 0.05
    assert kk.sure == 0.0
    kk.guncelle(det(), t)
    assert kk.sure == 0.0, "kirilmadan sonra SIFIRDAN baslamali"
    assert kk.kirilma == 1


def test_uzun_zaman_boslugu_kirar():
    """Kare sayisi az olsa da SURE toleransi (0.35 s) asilirsa kirilir."""
    kk = KesintisizKilit(cfg=Cfg5)
    for i in range(40):
        kk.guncelle(det(), i * 0.05)
    kk.guncelle(None, 40 * 0.05 + 2.0)        # tek kare ama 2 s sonra
    assert kk.sure == 0.0


# ──────────────────────────────────────────────── devir + denetim ozeti
def test_devret_t0_kilidi_tasir():
    """Faz gecerken kilit SIFIRLANMAMALI (yoksa toplam sart 10 s olurdu)."""
    kk = KesintisizKilit(cfg=Cfg5)
    for i in range(101):
        kk.guncelle(det(), i * 0.05)
    t0 = kk.devret_t0()
    assert t0 is not None
    kk2 = KesintisizKilit(cfg=Cfg5, t0=t0)
    kk2.guncelle(det(), 101 * 0.05)
    assert kk2.sure >= 5.0, "devralinan kilit sifirdan baslamamali"
    assert kk2.gecti() is True


def test_ozet_bagimsiz_dogrulanabilir():
    """fark_s (duvar saati farki) ile kesintisiz_kilit_s ORTUSMELI."""
    kk = KesintisizKilit(cfg=Cfg5)
    for i in range(101):
        kk.guncelle(det(), i * 0.05)
    o = kk.ozet()
    assert abs(o["kesintisiz_kilit_s"] - 5.0) < 0.01
    assert abs(o["fark_s"] - o["kesintisiz_kilit_s"]) < 0.05
    assert o["gecis_wall"] > o["kilit_t0_wall"]
    assert o["kare_gercek"] == 101
    assert o["hayalet_kare"] == 0
    assert abs(o["conf_medyan"] - 0.8) < 1e-6


def test_denetim_kaydi_yazilir_ve_ihlal_isaretlenir(tmp_path):
    """kilit_denetim_*.csv: kapi KAPALI olsa da yazilir ve ihlal bayragi
    5 s referansina gore konur (kullanici istegi 2026-08-17)."""
    import csv as _csv
    import control.guidance.kesintisiz_kilit as km
    eski = km._LOG_DIR
    try:
        km._LOG_DIR = str(tmp_path)
        log = km.DenetimLog()
        log.ac()
        # ⚠ Kapi ACIKKEN de KAPALIYKEN de denetim tutulmali. Burada ACIKCA
        #   KAPALI (CfgEski) kullaniliyor: kayit kapiya BAGLI OLMAMALI.
        kk = KesintisizKilit(cfg=CfgEski)         # kapi acikca KAPALI
        for i in range(10):                       # 0.45 s -> IHLAL
            kk.guncelle(det(), i * 0.05)
        log.yaz("GPS_VISUAL", kk, "OTO: ardisik_kare>=10", {"menzil_m": 15.0})
        kk2 = KesintisizKilit(cfg=CfgEski)
        for i in range(101):                      # 5.00 s -> ihlal YOK
            kk2.guncelle(det(), 100.0 + i * 0.05)
        log.yaz("TERMINAL", kk2, "kutu>=25px", {"boyut_px": 26.0})
        yol = log.yol
        log.kapat()

        with open(yol, encoding="utf-8") as f:
            sat = list(_csv.DictReader(f))
        assert len(sat) == 2
        assert sat[0]["olay"] == "GPS_VISUAL"
        assert abs(float(sat[0]["kesintisiz_kilit_s"]) - 0.45) < 0.01
        assert sat[0]["ihlal"] == "1", "0.45 s IHLAL olmali"
        # ⚠ `kapi_acik` sutunu KURESEL ayardan yazilir (ornekten degil).
        #   Testin asil iddiasi: kapi ACIK da olsa KAPALI da olsa KAYIT
        #   TUTULUR -- bunu len(sat)==2 zaten kanitliyor.
        assert sat[0]["kapi_acik"] == ("1" if KilitKapiCfg.acik() else "0")
        assert sat[1]["olay"] == "TERMINAL"
        assert sat[1]["ihlal"] == "0", "5.00 s ihlal OLMAMALI"
        # zaman damgalari BAGIMSIZ dogrulanabilir olmali
        for s in sat:
            assert abs(float(s["fark_s"]) - float(s["kesintisiz_kilit_s"])) < 0.05
            assert float(s["gecis_wall"]) > float(s["kilit_t0_wall"])
            assert s["hayalet_kare"] == "0"
    finally:
        km._LOG_DIR = eski


def test_10_ardisik_kare_5_saniye_DEGILDIR():
    """Olculen gercek: 20 fps'te 10 ardisik kare = 0.45 s, 5 s DEGIL.
    Mevcut kapinin (supervisor KILIT_N=10) neden yetersiz oldugunu kilitler."""
    kk = KesintisizKilit(cfg=Cfg5)
    for i in range(10):
        kk.guncelle(det(), i * 0.05)          # olculen medyan periyot
    assert kk.kare == 10
    assert abs(kk.sure - 0.45) < 1e-6
    assert kk.gecti() is False, "10 kare 5 s kilit SAYILMAMALI"


# ══════════════════════════════════════════════════════════════════════════
#  ALGI SUREKLILIGI YAMALARI (2026-08-17) — VARSAYILAN DAVRANIS KILIDI
# ══════════════════════════════════════════════════════════════════════════
def test_kadraj_kapisi_varsayilan_YASA_modu():
    """Varsayilan KADRAJ_MOD 'yasa' olmali (bugunku davranis, bit-ayni).
    'dow' modu ancak AVCI_KILIT_KADRAJ_MOD ile acilir."""
    assert getattr(KilitKapiCfg, "KADRAJ_MOD", "yasa") == "yasa"


def test_kadraj_yasa_modu_OLU_KOD_oldugunu_kilitler():
    """OLCULDU (20976 gorsel faz karesi): kadraj kapisi HIC atesLENMEDI.
    Sebep geometrik: DoW karesi yasa cercevesinde u[19,621] v[71,409]'a
    duser, PAY=0.02 kapisi ise [12.8,627.2]x[9.6,470.4] istiyor -> erisilebilir
    bolgeyi TAMAMEN kapsiyor. Bu test o olu-kod halini KANITLAR (yamanin
    gerekcesi budur); 'dow' modu acilinca kapi gercekten ateslenir."""
    kk = KesintisizKilit()
    # DoW karesinin EN UST kenari (v=0 -> yasa v=70.7) ve EN SAG kenari
    for cx, cy in ((KilitKapiCfg.DOW_U0, 240.0), (KilitKapiCfg.DOW_U1, 240.0),
                   (320.0, KilitKapiCfg.DOW_V0), (320.0, KilitKapiCfg.DOW_V1)):
        ok, _sebep = kk._kare_gecerli(det(cx=cx, cy=cy))
        assert ok, "yasa modunda DoW kenari kabul edilmeli (kapi olu)"


def test_kadraj_dow_modu_kenari_REDDEDER():
    class CfgDow(KilitKapiCfg):
        KADRAJ_MOD = "dow"
    kk = KesintisizKilit(cfg=CfgDow)
    ok, _ = kk._kare_gecerli(det(cx=320.0, cy=240.0))
    assert ok, "merkez her modda gecerli"
    for cx, cy in ((KilitKapiCfg.DOW_U0, 240.0), (KilitKapiCfg.DOW_U1, 240.0),
                   (320.0, KilitKapiCfg.DOW_V0), (320.0, KilitKapiCfg.DOW_V1)):
        ok, sebep = kk._kare_gecerli(det(cx=cx, cy=cy))
        assert not ok and "dow" in sebep, (cx, cy, sebep)


def test_dow_sinirlari_geometriyle_tutuyor():
    """Sinirlar AYAR DEGIL geometri: FX_yasa/fx_dow orani ile DoW yari
    kadraji. Sayi kayarsa ceviri bozulmus demektir."""
    assert abs(KilitKapiCfg.DOW_U0 - 19.0) < 1.0
    assert abs(KilitKapiCfg.DOW_U1 - 621.0) < 1.0
    assert abs(KilitKapiCfg.DOW_V0 - 70.7) < 1.0
    assert abs(KilitKapiCfg.DOW_V1 - 409.3) < 1.0


def test_supervisor_algi_kapilari_varsayilan_ESKI_davranis():
    """AVCI_DEVIR_BOYUT_MOD / AVCI_HAYALET_MOD varsayilanlari eski
    davranis olmali. Biri sessizce degisirse canli davranis degisir."""
    from control.guidance.supervisor import SupCfg
    assert SupCfg.DEVIR_BOYUT_MOD == "kare"     # kapi kare-gecerliliginde
    assert SupCfg.HAYALET_MOD == "oran"         # en-boy testi her boyutta
    assert SupCfg.DEVIR_BOYUT_PX == 14.0
    assert SupCfg.HAYALET_WH_MIN == 1.3


def test_karar_logu_yeni_kolonlar_SONDA():
    """w/h/cx_yasa/cy_yasa/eleme SALT GOZLEM kolonlaridir ve SONA eklendi;
    basliktaki eski sira DEGISMEMELI (eski cozumleyici kirilmasin)."""
    from control.guidance.supervisor import _KararLog
    b = _KararLog.BASLIK.strip().split(",")
    assert b[:13] == ["t", "mod", "faz", "gorulen", "conf", "kilit_s", "esik_s",
                      "boyut_pct", "esik_pct", "merkez_av", "d_h_m", "karar",
                      "sebep"]
    assert b[13:] == ["w", "h", "cx_yasa", "cy_yasa", "eleme", "kilit_kes_s",
                      "u_truth", "v_truth"]


# ═════════════════════════════════════════════════════════════════════════
#  DOLULUK — "5 s kesintisiz kilit"in yuzde kaci GERCEKTEN gozlemlendi
# ═════════════════════════════════════════════════════════════════════════
# NEDEN: bugunku tanim tek bir boslugun UZUNLUGUNU sinirlar ama SAYISINI
# sinirlamaz. "2 kare gor / 0.3 s kor kal" dizisi sonsuz tekrarlanabilir ve
# 5 saniyelik "KESINTISIZ" kilit uretir. Tezgahta olculdu (12 adet >=5 s
# epizod): doluluk medyan %62.1, EN KOTU %51.1. Bu testler o acigi KILITLER.

def test_kesintisiz_kilit_YARI_KOR_olabilir():
    """★ TANIM ACIGI: sure sarti dolar ama arac zamanin yarisinda KORDUR.

    Dizi: 2 gecerli kare, sonra 0.30 s bosluk (tolerans 0.35 s icinde),
    tekrar tekrar. Sure birikmeye devam eder -- ama doluluk %50 civaridir.
    """
    kk = KesintisizKilit()
    t = 0.0
    for _ in range(40):
        kk.guncelle(det(), t); t += 0.05
        kk.guncelle(det(), t)
        t += 0.30                        # 0.35 s toleransin ALTINDA -> kirmaz
        kk.guncelle(None, t - 0.15)      # bosluk karesi (tolere edilir)
    assert kk.sure > 5.0, "sure sarti DOLUYOR"
    assert kk.doluluk < 0.75, (
        "doluluk %.2f -- kilit KESINTISIZ gorunuyor ama arac kor" % kk.doluluk)
    assert kk.kor_s > 1.0                # kilit icinde gercek kor sure var


def test_doluluk_kesintisiz_akista_1e_yakin():
    """Hicbir kare kacmazsa doluluk ~1.0 olmali."""
    kk = KesintisizKilit()
    for i in range(101):
        kk.guncelle(det(), i * 0.05)
    assert kk.doluluk > 0.99
    assert kk.kor_s < 0.01


def test_doluluk_tabani_KAPATILABILIR():
    """AVCI_KILIT_DOLULUK=0 -> doluluk kapiyi ETKILEMEZ (geri donus yolu)."""
    assert KilitKapiCfg.DOLULUK_MIN == 0.0     # kapi KAPALI (2026-08-18)

    class C(KilitKapiCfg):
        ESIK_S = 5.0
        DOLULUK_MIN = 0.0
    kk = KesintisizKilit(cfg=C)
    t = 0.0
    for _ in range(40):
        kk.guncelle(det(), t); t += 0.05
        kk.guncelle(det(), t); t += 0.30
        kk.guncelle(None, t - 0.15)
    assert kk.sure >= 5.0
    assert kk.doluluk < 0.75
    assert kk.gecti() is True, "taban KAPALIYKEN doluluk kapiyi kapatmamali"


def test_doluluk_tabani_ACIK_yari_kor_kilidi_REDDEDER():
    """Taban acilinca ayni yari-kor kilit GECMEMELI."""
    class C(KilitKapiCfg):
        ESIK_S = 5.0
        DOLULUK_MIN = 0.80
    kk = KesintisizKilit(cfg=C)
    t = 0.0
    for _ in range(40):
        kk.guncelle(det(), t); t += 0.05
        kk.guncelle(det(), t); t += 0.30
        kk.guncelle(None, t - 0.15)
    assert kk.sure >= 5.0                # sure sarti SAGLANDI
    assert kk.gecti() is False           # ama DOLULUK saglanmadi


def test_doluluk_ozette_ve_baslikta_var():
    """Denetim kaydi doluluk'u tasimazsa ihlal 'sure' ile gizlenebilir."""
    from control.guidance.kesintisiz_kilit import BASLIKLAR
    for k in ("doluluk", "kor_s", "kare_periyot_s"):
        assert k in BASLIKLAR
    kk = KesintisizKilit()
    for i in range(20):
        kk.guncelle(det(), i * 0.05)
    o = kk.ozet()
    for k in ("doluluk", "kor_s", "kare_periyot_s"):
        assert k in o


# ═════════════════════════════════════════════════════════════════════════
#  BOSLUK TOLERANSI KARE HIZINDAN BAGIMSIZ OLMALI
# ═════════════════════════════════════════════════════════════════════════
def test_kare_toleransi_KARE_HIZINA_bagimli_OLDUGUNU_kilitler():
    """★ OLCULEN KUSUR: BOSLUK_KARE=3, kare periyoduna gore farkli SURE eder.
    20 fps'te 0.15 s, 14.3 fps'te 0.21 s. Ayni tanim, dedektor yavaslayinca
    KENDILIGINDEN gevsiyor. Bu test o bagimliligi belgeler."""
    assert Cfg5.BOSLUK_MOD == "kare"   # ESKI tanim (varsayilan artik "sure")

    def kir_mi(dt):
        kk = KesintisizKilit(cfg=Cfg5)
        t = 0.0
        for _ in range(5):
            kk.guncelle(det(), t); t += dt
        onceki = kk.kirilma
        for _ in range(4):                        # 4 bosluk karesi > 3
            kk.guncelle(None, t); t += dt
        return kk.kirilma > onceki

    # Her iki hizda da KARE sayisi asilinca kirilir -- yani esik SURE degil
    assert kir_mi(0.05) is True
    assert kir_mi(0.07) is True
    # ...ama kirilana kadar gecen SURE farklidir: 4*0.05=0.20 vs 4*0.07=0.28


def test_sure_modu_kare_sayisini_YOKSAYAR():
    """BOSLUK_MOD=sure -> yalniz BOSLUK_S gecerli; tanim kare hizindan
    BAGIMSIZ olur."""
    class C(KilitKapiCfg):
        BOSLUK_MOD = "sure"
        BOSLUK_S = 0.35
        BOSLUK_KARE = 3
    kk = KesintisizKilit(cfg=C)
    t = 0.0
    for _ in range(5):
        kk.guncelle(det(), t); t += 0.05
    onceki = kk.kirilma
    for _ in range(6):                    # 6 kare > BOSLUK_KARE(3)
        kk.guncelle(None, t); t += 0.05   # ama toplam 0.30 s < BOSLUK_S
    assert kk.kirilma == onceki, "kare sayisi 'sure' modunda olcut OLMAMALI"
    kk.guncelle(None, t + 0.30)           # simdi SURE asildi
    assert kk.kirilma > onceki


def test_sure_modu_VARSAYILAN_DEGIL():
    """Kapi kapatilinca eski tanim geri geldi (kullanici talimati 2026-08-18)."""
    assert KilitKapiCfg.BOSLUK_MOD == "kare"


# ═════════════════════════════════════════════════════════════════════════
#  TEZGAH SHIM'I EKSIK ALAN DUSURMEMELI
# ═════════════════════════════════════════════════════════════════════════
def test_tezgah_ayar_shimi_TUM_kapi_alanlarini_tasir():
    """★ SESSIZ OLCUM HATASI KORUMASI.

    arac/kilit_tezgah.Ayar, KilitKapiCfg'nin klonudur. Bir alan `_ALAN`
    listesine eklenmezse tarama o ekseni HIC denemez ama tabloyu yine de
    basar -> "yamanin etkisi yok" diye YANLIS sonuc cikar. 2026-08-17'de
    DOLULUK_MIN ve BOSLUK_MOD tam olarak bu yuzden etkisiz gorundu.
    """
    import importlib.util
    kok = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    yol = os.path.join(kok, "arac", "kilit_tezgah.py")
    spec = importlib.util.spec_from_file_location("kilit_tezgah", yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # Kilit DAVRANISINI belirleyen tum ayar alanlari shim'de olmali.
    zorunlu = {"ESIK_S", "CONF_MIN", "BOSLUK_KARE", "BOSLUK_S", "BOSLUK_MOD",
               "KADRAJ_PAY", "KADRAJ_MOD", "SART_S", "DOLULUK_MIN"}
    eksik = zorunlu - set(mod.Ayar._ALAN)
    assert not eksik, "tezgah shim'i su alanlari DUSURUYOR: %s" % sorted(eksik)

    # ...ve klon gercekten tasiyor olmali (isim listede ama kopyalanmiyorsa da bozuk)
    a = mod.Ayar()
    for alan in zorunlu:
        assert getattr(a, alan, None) is not None or alan == "ESIK_S", alan

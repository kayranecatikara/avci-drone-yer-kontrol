# -*- coding: utf-8 -*-
"""KOPRU YASA KONFIGURASYONU — IMPORT SIRASINDAN BAGIMSIZ OLMALI.

⛔ 2026-08-13 CANLI YAKALANAN HATA (bu testlerin varlik sebebi):
gg.Cfg env'i SINIF TANIMINDA okur. entegre._kur() env yaziyordu, ama panel
(kopru/gorsel_ozellikler -> supervisor -> gps_guidance) yasayi GOREV BASLAMADAN
import edince Cfg HAM VARSAYILANLARLA kuruluyordu ve env ETKISIZ kaliyordu.
Konsol kaniti: "RANGE_SET=8.0 ELEV=15 IC_KAYMA=14 ELEV_DIN=True"
(olmasi gereken 6.9 / 25 / 0 / False). Arac yanlis konfigle uctu.
"""
import sys

import pytest

from guidance.ana_kontrol import Cfg as AK
from kopru.entegre import KopruGudum


class _SahteDrone:
    def get_drone_altitude(self):
        return 4840.0


def _kur(**kw):
    a = dict(range_set=AK.KOPRU_RANGE_SET, v_max=AK.KOPRU_V_MAX,
             ic_kayma=AK.KOPRU_IC_KAYMA, gnss_duzeltici=AK.KOPRU_GNSS_FILTRE,
             kalkis_agl=AK.KOPRU_KALKIS_AGL, istasyon_elev=AK.KOPRU_ISTASYON_ELEV,
             birebir=AK.KOPRU_BIREBIR, vmax_istisna=AK.KOPRU_VMAX_ISTISNA)
    a.update(kw)
    g = KopruGudum(_SahteDrone(), **a)
    g._kur()
    import control.guidance.gps_guidance as gg
    return gg


def test_konfig_oturur_temiz_baslangicta():
    gg = _kur()
    assert gg.Cfg.RANGE_SET == pytest.approx(AK.KOPRU_RANGE_SET)
    assert gg.Cfg.ISTASYON_ELEV_DEG == pytest.approx(AK.KOPRU_ISTASYON_ELEV)
    assert gg.Cfg.IC_KAYMA == pytest.approx(AK.KOPRU_IC_KAYMA)
    assert gg.Cfg.V_MAX == pytest.approx(AK.KOPRU_V_MAX)
    assert gg.Cfg.ELEV_DINAMIK is False


def test_YASA_ONCE_IMPORT_EDILSE_BILE_konfig_oturur():
    """ASIL REGRESYON TESTI: panel yasayi onceden cekmis olsun."""
    from kopru import gorsel_ozellikler as goz
    goz.hepsi()                       # panel sorgusu -> supervisor -> gps_guidance
    import control.guidance.gps_guidance as gg_once
    assert "control.guidance.gps_guidance" in sys.modules
    gg_once.Cfg.RANGE_SET = 8.0       # ham varsayilani ZORLA (hatanin hali)
    gg_once.Cfg.ISTASYON_ELEV_DEG = 15.0
    gg_once.Cfg.IC_KAYMA = 14.0
    gg_once.Cfg.ELEV_DINAMIK = True

    gg = _kur()                       # kopru simdi kurulsun
    assert gg.Cfg.RANGE_SET == pytest.approx(AK.KOPRU_RANGE_SET)   # 6.9
    assert gg.Cfg.ISTASYON_ELEV_DEG == pytest.approx(AK.KOPRU_ISTASYON_ELEV)  # 25
    assert gg.Cfg.IC_KAYMA == pytest.approx(AK.KOPRU_IC_KAYMA)     # 0
    assert gg.Cfg.ELEV_DINAMIK is False


def test_hibrit_yolunda_da_oturur():
    gg = _kur(hibrit=True, kayip_m=AK.KOPRU_KAYIP_M)
    assert gg.Cfg.RANGE_SET == pytest.approx(AK.KOPRU_RANGE_SET)
    assert gg.Cfg.ELEV_DINAMIK is False
    import control.guidance.supervisor as sup
    assert sup.SupCfg.KAYIP_M == AK.KOPRU_KAYIP_M


def test_istasyon_geometrisi_tasarima_esit():
    """RANGE 6.0 x ELEV 15 -> 5.80 m arka + 1.55 m ALT.

    ⚠ 2026-08-17 GUNCELLENDI (eski kilit: RANGE 6.9 x ELEV 25 -> 6.25 + 2.92).
    Sessiz kayma DEGIL, olculmus karar:
      RANGE_SET 7.0 -> 6.0  ->  en yakin gecis 4.8 -> 1.87 m,
      vurus 0/0 -> 1/1 (iki bagimsiz cift, 2026-08-17 kampanyasi).

    ⚠⚠ ACIK KONU -- BU KILIT BIR SORUNU DA BELGELIYOR:
    1.55 m'lik "hedefin ALTINDA dur" ofseti TASARIM geregi (gokyuzu arka plani
    korunsun, hedef kadrajin ust yarisinda kalsin diye). Ama CPA'da olculen
    dikey iska 1.19-1.63 m -- yani AYNI BUYUKLUK. Demek ki terminal fazda bu
    ofsetin GERI ALINMASI gerekirken alinmiyor (TERM_DIKEY_M rampasi yetmiyor;
    yakin gecislerin %90'i VISUAL fazda ve orada rampa hic YOK).
    Dikey iska cozulunce bu kilit yine guncellenecek.
    """
    import math
    gg = _kur()
    R, E = gg.Cfg.RANGE_SET, math.radians(gg.Cfg.ISTASYON_ELEV_DEG)
    assert R * math.cos(E) == pytest.approx(5.80, abs=0.02)
    assert R * math.sin(E) == pytest.approx(1.55, abs=0.02)


def test_konfig_oturmazsa_SESSIZ_KALMAZ(monkeypatch):
    """Zorlama basarisiz olursa ucus IPTAL edilmeli (sessiz yanlis konfig YOK)."""
    import control.guidance.gps_guidance as gg
    gercek = gg.Cfg

    class _Yutan(type):               # SINIF duzeyi setattr'i yutar (metaclass sart:
        def __setattr__(cls, *a):     # sinif govdesindeki __setattr__ yalniz ORNEKLERE isler)
            pass

    class _Kilitli(metaclass=_Yutan):     # zorlamayi yutan sahte Cfg
        RANGE_SET, IC_KAYMA, ISTASYON_ELEV_DEG = 8.0, 14.0, 15.0
        V_MAX, ELEV_DINAMIK = 18.0, True

    try:
        gg.Cfg = _Kilitli
        with pytest.raises(RuntimeError, match="OTURMADI"):
            _kur()
    finally:
        gg.Cfg = gercek

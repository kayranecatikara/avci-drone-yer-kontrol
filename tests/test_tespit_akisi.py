# -*- coding: utf-8 -*-
"""kopru/tespit_akisi.py — dedektor ile Gazebo yasasi arasindaki koprü.

KRITIK DEGISMEZLER:
  - `bekle` sozlesmesi: yeni kare gelene kadar BLOKLAR, timeout'ta None
  - kutusuz kare `pose=None` ile GECER (yasa onu kayip sayar) — YUTULMAZ
  - ⛔ kayitta YALNIZ kamera olcumu olur; GPS/menzil/truth alani SIZMAZ
"""
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kopru.tespit_akisi import TespitAkisi

DET = {"cx": 960.0, "cy": 540.0, "w": 100.0, "h": 40.0, "conf": 0.87}


# ------------------------------------------------------------------ sozlesme
def test_yeni_kare_seq_artirir():
    a = TespitAkisi()
    a.yaz(DET); a.yaz(DET)
    r = a.bekle(0, timeout=0.1)
    assert r["seq"] == 2


def test_bekle_ESKI_seq_ile_hemen_doner():
    a = TespitAkisi()
    a.yaz(DET)
    r = a.bekle(0, timeout=0.05)
    assert r is not None and r["seq"] == 1


def test_bekle_AYNI_seq_ile_timeout():
    """Yeni kare yoksa None — yasa bunu 'akis durdu' sayar."""
    a = TespitAkisi()
    a.yaz(DET)
    t0 = time.perf_counter()
    assert a.bekle(1, timeout=0.15) is None
    assert time.perf_counter() - t0 >= 0.14


def test_bekle_yeni_kare_gelince_UYANIR():
    """Bloklama gercek olmali: yazma anında okuyucu uyanmali."""
    a = TespitAkisi()
    sonuc = {}
    def oku():
        sonuc["r"] = a.bekle(0, timeout=2.0)
    t = threading.Thread(target=oku); t.start()
    time.sleep(0.05)
    a.yaz(DET)
    t.join(timeout=2.0)
    assert sonuc["r"] is not None and sonuc["r"]["seq"] == 1


def test_kutusuz_kare_pose_None_ile_GECER():
    """Tespit basarisiz kare YUTULMAZ — yasa KAYIP_M'e dogru saymali."""
    a = TespitAkisi()
    a.yaz(None)
    r = a.bekle(0, timeout=0.1)
    assert r is not None and r["seq"] == 1 and r["pose"] is None


def test_bozuk_kayit_kutusuz_sayilir():
    """Eksik alanli det sessizce gecmemeli, kutusuz kare olmali."""
    a = TespitAkisi()
    a.yaz({"conf": 0.9})                       # cx/cy yok
    assert a.bekle(0, timeout=0.1)["pose"] is None


# ------------------------------------------------------------------ ⛔ KURAL
def test_kural_yalniz_kamera_alanlari():
    """GPS/menzil/truth alani yasaya SIZMAMALI (gorsel fazda GPS yasak)."""
    a = TespitAkisi()
    a.yaz({**DET, "menzil": 12.3, "tgt_x": 5.0, "truth": [1, 2, 3],
           "track_id": 7, "t": 99.0, "W": 1920, "H": 1080})
    p = a.bekle(0, timeout=0.1)["pose"]
    assert set(p) == {"conf", "cx", "cy", "w", "h"}


def test_kural_kayit_kopyalanir_disaridan_degismez():
    """Yasaya verilen sozluk, dedektorun sozlugune BAGLI olmamali."""
    a = TespitAkisi()
    d = dict(DET)
    a.yaz(d)
    d["cx"] = -999.0
    assert a.bekle(0, timeout=0.1)["pose"]["cx"] == 960.0


# ------------------------------------------------------------------- olcum
def test_olcum_tespit_orani():
    a = TespitAkisi()
    for x in (DET, None, DET, DET):
        a.yaz(x)
    o = a.olcum()
    assert o["kare"] == 4 and o["kutulu"] == 3
    assert abs(o["tespit_orani"] - 0.75) < 1e-9


def test_olcum_hz_ve_esik_sureleri():
    """Yasanin kare-sayisi esikleri, olculen hizda SURE karsiligi kazanmali."""
    a = TespitAkisi()
    for i in range(11):
        a.yaz(DET, simdi=i * 0.1)          # 10 Hz
    o = a.olcum()
    assert abs(o["hz"] - 10.0) < 1e-6
    assert abs(o["kilit_penceresi_s"] - 1.5) < 1e-6   # 15 kare @10 Hz
    assert abs(o["kayip_esigi_s"] - 2.0) < 1e-6       # 20 kare @10 Hz


def test_olcum_bos_akista_cokmez():
    o = TespitAkisi().olcum()
    assert o["kare"] == 0 and o["hz"] == 0.0 and o["kilit_penceresi_s"] is None


# ------------------------------------------------------------------ sifirla
def test_sifirla_bayat_kareyi_devretmez():
    a = TespitAkisi()
    a.yaz(DET)
    a.sifirla()
    assert a.bekle(0, timeout=0.05) is None
    assert a.olcum()["kare"] == 0


# ══════════════════════════════════════════════════════════════════════════
#  KAMERA CERCEVESI CEVIRISI (2026-08-10 hata duzeltmesi)
#  Yasa (bbox_ibvs) pikselleri GAZEBO icsellikleriyle (640x480, CX=320,
#  FX=166.6) okur; dedektor DoW karesini 1920x1080 tam piksel verir. Ceviri
#  olmadan kadrajin MERKEZINDEKI hedef yasaya +75.4 deg yaw hatasi gibi
#  gorunuyordu. Bu testler cevirinin dogrulugunu KILITLER.
# ══════════════════════════════════════════════════════════════════════════
import math as _math

from kopru.tespit_akisi import dow_pikseli_yasaya, HFOV_DOW_DEG, _yasa_icsellik


def _icsellik():
    """Modulun KENDI cozumu — vision.geometry yolu ancak kopru kurulunca acilir;
    acik degilse modul Gazebo SDF varsayilanlarina duser (ayni degerler)."""
    return _yasa_icsellik()


def test_ceviri_merkez_yasanin_merkezine_gider():
    """En kritik durum: kadraj merkezindeki hedef -> yasanin ana noktasi."""
    CX, CY, _, _ = _icsellik()
    cx, cy, _, _ = dow_pikseli_yasaya(960.0, 540.0, 100.0, 60.0, 1920.0, 1080.0)
    assert abs(cx - CX) < 1e-6
    assert abs(cy - CY) < 1e-6


def test_ceviri_kenar_acisi_hfov_yarisi():
    """Kare kenari -> yaklasik HFOV/2 acisi (ince kamera modeli)."""
    CX, _, FX, _ = _icsellik()
    cx, _, _, _ = dow_pikseli_yasaya(1920.0, 540.0, 10.0, 10.0, 1920.0, 1080.0)
    aci = _math.degrees(_math.atan((cx - CX) / FX))
    # ⚠ 2026-08-17 AYNA DUZELTMESI: yasanin cercevesi dow_kopru.py:49-53
    #   uyarinca AYNALI (NED_y = -DoW_y). Kamera da artik aynalaniyor
    #   (tespit_akisi.dow_pikseli_yasaya), yani karenin SAG kenari yasa
    #   cercevesinde NEGATIF azimuta dusuyor. Buyukluk aynen HFOV/2.
    assert abs(aci + HFOV_DOW_DEG / 2.0) < 0.5


def test_ceviri_cozunurlukten_bagimsiz():
    """Ayni NORMALIZE konum, farkli cozunurlukte AYNI yasa pikselini vermeli."""
    a = dow_pikseli_yasaya(1440.0, 270.0, 96.0, 54.0, 1920.0, 1080.0)
    b = dow_pikseli_yasaya(960.0, 180.0, 64.0, 36.0, 1280.0, 720.0)
    for x, y in zip(a, b):
        assert abs(x - y) < 1e-6


def test_ceviri_boyut_acisal_olcek():
    """w/h de ayni olcekle kuculur (acisal boyut korunur; menzil kestirimi)."""
    _, _, FX, _ = _icsellik()
    W = 1920.0
    fx_dow = (W / 2.0) / _math.tan(_math.radians(HFOV_DOW_DEG) / 2.0)
    _, _, w, _ = dow_pikseli_yasaya(960.0, 540.0, 300.0, 100.0, W, 1080.0)
    assert abs(w - 300.0 * FX / fx_dow) < 1e-6


def test_ceviri_WH_yoksa_dokunmaz():
    """W/H bilinmiyorsa yanlis olceklemektense girdiyi aynen birak."""
    assert dow_pikseli_yasaya(960.0, 540.0, 100.0, 60.0, 0.0, 0.0) == (960.0, 540.0, 100.0, 60.0)
    assert dow_pikseli_yasaya(960.0, 540.0, 100.0, 60.0, None, None) == (960.0, 540.0, 100.0, 60.0)


def test_akis_ceviriyi_uygular_ve_WH_sizdirmaz():
    """Uctan uca: yaz() cevirir, kayitta W/H/track_id BULUNMAZ (D0 sozlesmesi)."""
    CX, CY, _, _ = _icsellik()
    a = TespitAkisi()
    a.yaz({"cx": 960.0, "cy": 540.0, "w": 120.0, "h": 70.0, "conf": 0.9,
           "W": 1920, "H": 1080, "track_id": 7, "t": 1.0})
    p = a.bekle(0, timeout=0.2)["pose"]
    assert abs(p["cx"] - CX) < 1e-6 and abs(p["cy"] - CY) < 1e-6
    assert set(p.keys()) == {"conf", "cx", "cy", "w", "h"}

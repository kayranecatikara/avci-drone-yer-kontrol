# -*- coding: utf-8 -*-
"""supervisor izci dongusu — ALGI SUREKLILIGI yamalarinin CALISMA testi (2026-08-17).

NEDEN VAR: yamalar `izci()` closure'inin ICINDE. Sozdizimi testi ve config
testi oradaki bir NameError/TypeError'i YAKALAMAZ; hata ancak canli gorevde
patlardi ve kampanya kosuyor. Bu test dongunun kendisini gercekten kosturur.

KILITLENEN DAVRANISLAR
  * VARSAYILAN ("kare" modu): kucuk kutu tespiti SAYILMAZ -> devir OLMAZ
  * "devir" modu: kucuk kutu tespit SAYILIR (sureklilik korunur) ama
    devir yine OLMAZ (menzil kisiti duruyor)
  * "devir" modu + buyuk kutu: devir OLUR
  * karar logu yeni kolonlariyla birlikte HATASIZ yazilir (bicimlendirme)
"""
import io
import os
import sys
import threading
import time

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "kopru", "gazebo_kaynak"))


def _kos(boyut_mod, w, h, n_kare=40, hayalet_mod="oran"):
    """izci dongusunu gercekten kostur; (devretti_mi, karar_csv) dondur."""
    os.environ["AVCI_DEVIR_BOYUT_MOD"] = boyut_mod
    os.environ["AVCI_HAYALET_MOD"] = hayalet_mod
    os.environ["AVCI_KILIT_DENETIM"] = "0"          # canli logs/ dizinine yazma
    # ⚠ 2026-08-17: 5 s kesintisiz kilit kapisi VARSAYILAN ACIK oldu. Bu
    #   dosya BOYUT/HAYALET modlarini sinar, kilit kapisini DEGIL; dongu
    #   yalniz 40 kare (2.0 s) kosuyor, yani kapi acikken hicbir zaman
    #   devretmezdi. Kapiyi ACIKCA kapatiyoruz ki testin konusu korunsun.
    os.environ["AVCI_KILIT_S"] = "0"
    import importlib
    import control.guidance.kesintisiz_kilit as K
    import control.guidance.supervisor as S
    importlib.reload(K)
    importlib.reload(S)

    tampon = io.StringIO()
    S.karar_log.ac = lambda: None                   # canli logs/ dizinine yazma
    S.karar_log.f = tampon
    S._ga.status["d_h"] = 10.0                      # devir menzil kapisi ACIK
    S._ga.status["durum"] = "OK"

    stop = threading.Event()
    sayac = {"n": 0}

    def wait_pose(son_seq, timeout=0.5):
        if sayac["n"] >= n_kare:
            stop.set()
            return None
        sayac["n"] += 1
        return {"seq": sayac["n"], "t": sayac["n"] * 0.05,
                "pose": {"cx": 320.0, "cy": 240.0, "w": w, "h": h, "conf": 0.9}}

    def sahte_gps(conn, get_plane, get_iris, faz_stop):
        faz_stop.wait(3.0)                          # izci karar verene kadar bekle

    S.run_gps_guidance = sahte_gps
    S.run_bbox_ibvs = lambda *a, **k: stop.set()
    S.run_visual_lead = lambda *a, **k: stop.set()

    t = threading.Thread(
        target=S.run_hybrid,
        args=(None, lambda: None, lambda: None, wait_pose, lambda: None, stop),
        daemon=True)
    t.start()
    t.join(6.0)
    stop.set()
    t.join(2.0)
    return S.status.get("gecis_sayisi", 0) > 0 or S.status.get("faz") == "GORSEL", \
        tampon.getvalue()


def _temizle():
    for k in ("AVCI_DEVIR_BOYUT_MOD", "AVCI_HAYALET_MOD", "AVCI_KILIT_DENETIM"):
        os.environ.pop(k, None)


# ───────────────────────────────────────────────────────────── kucuk kutu
def test_kare_modu_kucuk_kutu_tespiti_SAYMAZ():
    """VARSAYILAN: 10 px kutu (< 14 px kapisi) -> gorulen=0, ardisik hic dolmaz."""
    try:
        _devretti, csv = _kos("kare", w=10.0, h=4.0)
    finally:
        _temizle()
    satir = [s for s in csv.strip().split("\n") if s]
    assert satir, "karar logu HIC satir yazmadi -> dongu kosmadi"
    assert all(s.split(",")[3] == "0" for s in satir), "kucuk kutu SAYILMAMALI"
    assert all(s.split(",")[17] == "BOYUT" for s in satir), \
        "eleme kolonu BOYUT yazmali (kolon 17)"


def test_devir_modu_kucuk_kutu_tespiti_SAYAR_ama_devretmez():
    """'devir' modu: sureklilik sayaci calisir (gorulen=1) ama devir OLMAZ."""
    try:
        devretti, csv = _kos("devir", w=10.0, h=4.0)
    finally:
        _temizle()
    satir = [s for s in csv.strip().split("\n") if s]
    assert satir, "karar logu HIC satir yazmadi -> dongu kosmadi"
    assert all(s.split(",")[3] == "1" for s in satir), \
        "'devir' modunda kucuk kutu tespit SAYILMALI (sureklilik korunur)"
    assert all(s.split(",")[17] == "BOYUT" for s in satir), \
        "eleme kolonu yine BOYUT demeli (kapi hala biliniyor)"
    assert not devretti, "menzil kisiti KALKMAMALI -- kucuk kutuda devir YOK"


# ───────────────────────────────────────────────────────────── buyuk kutu
def test_devir_modu_buyuk_kutu_DEVREDER():
    try:
        devretti, csv = _kos("devir", w=40.0, h=14.0)
    finally:
        _temizle()
    assert csv.strip(), "karar logu HIC satir yazmadi -> dongu kosmadi"
    assert devretti, "buyuk kutuda devir OLMALI"


def test_kare_modu_buyuk_kutu_DEVREDER():
    """Referans: varsayilan modda da buyuk kutu devrediyor (bit-ayni yol)."""
    try:
        devretti, _csv = _kos("kare", w=40.0, h=14.0)
    finally:
        _temizle()
    assert devretti


# ───────────────────────────────────────────────── karar logu bicimlendirme
def test_karar_logu_kolon_sayisi_BASLIKLA_ayni():
    """Yeni kolonlar eklendi; her satir baslikla AYNI sayida alan icermeli
    (bicimlendirme hatasi sessizce yutuluyordu -- try/except pass)."""
    try:
        _d, csv = _kos("kare", w=40.0, h=14.0, n_kare=15)
    finally:
        _temizle()
    import control.guidance.supervisor as S
    n = len(S._KararLog.BASLIK.strip().split(","))
    for s in csv.strip().split("\n"):
        if s:
            assert len(s.split(",")) == n, (n, s)


# ─────────────────────────────────────────────── HAYALET "boyut" modu
def test_hayalet_oran_modu_kucuk_KARE_kutuyu_eler():
    """VARSAYILAN 'oran': 18x17 px (w/h=1.06 < 1.3) -> HAYALET sayilir.
    Kutu BOYUT kapisini (14 px) GECIYOR, yani eleme yalniz en-boy testinden.
    OLCULDU: bu davranis 16-24 px bandinda GERCEK tespitlerin %12.3'unu,
    8-16 px bandinda %27.0'sini eliyor."""
    try:
        _d, csv = _kos("devir", w=18.0, h=17.0, hayalet_mod="oran", n_kare=20)
    finally:
        _temizle()
    satir = [s for s in csv.strip().split("\n") if s]
    assert satir
    assert all(s.split(",")[17] == "HAYALET" for s in satir), \
        "oran modunda kucuk kare kutu HAYALET elenmeli"


def test_hayalet_boyut_modu_kucuk_kutuda_orani_ATLAR_ama_DONUGU_yakalar():
    """'boyut' modu: 18 px < 24 px (HAYALET_MIN_PX) -> en-boy testi ATLANIR,
    kutu BOYUT kapisini de geciyor -> ilk kareler GECERLI. Ama kutu 20 kare
    boyunca HIC degismedigi icin DONUK testi devreye girer ve yakalar.
    Iki dal da BURADA kosuyor: ilk 7 kare gecerli, 8.'den sonra DONUK."""
    try:
        _d, csv = _kos("devir", w=18.0, h=17.0, hayalet_mod="boyut", n_kare=20)
    finally:
        _temizle()
    el = [s.split(",")[17] for s in csv.strip().split("\n") if s]
    assert el, "karar logu bos"
    assert el[0] == "", "kucuk kutuda en-boy testi ATLANMALI (ilk kare gecerli)"
    assert "HAYALET" in el, "DONUK KUTU testi devreye girmeli (kutu hic degismiyor)"
    assert el.index("HAYALET") >= 7, \
        "DONUK testi en az DONUK_N kare beklemeli (erken atesleme)"

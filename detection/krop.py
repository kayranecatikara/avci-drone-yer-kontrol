# -*- coding: utf-8 -*-
"""
================================================================================
  KROP  --  dedektore TAM CERCEVE yerine hedefin etrafindan 1:1 pencere ver
================================================================================
NEDEN
--------------------------------------------------------------------------------
Dedektor motoru STATIK 960x960. 1920x1080 kare ona verilince iki kayip olur:
    1) 1920 -> 960  yani hedef ag girdisinde YARI boyutta gorunur
    2) 1080 -> 540 olur ama girdi 960 yuksekliginde -> ustune %44 GRI BANT
       (hesabin neredeyse yarisi bos piksele gider)
Krop ikisini de kaldirir: hedefin etrafindan 960x960 kesip 1:1 veririz.
    hedef 15 m'de ~15 px (yasa cercevesi) -> ag girdisinde 24 px yerine 48 px
    gri bant sifir -> det_ms ARTMAZ, duser

⚠ POZ MODELI DE 960x960. Yani ayni krop poz motoruna da BIREBIR oturur;
   tek kirpma, iki model, ikisi de tam cozunurlukte.

GUVENLIK
--------------------------------------------------------------------------------
Hedef pencereden cikarsa TAMAMEN kaybederiz. Marj olculdu:
    en hizli kadraj supurmesi 575 px/s, 30 FPS'te kare basi 19 px
    hedef ortadayken 480 px marj  ->  0.8 s
Geri cekilme: son tespit BAYAT ise (BAYAT_S) tam kareye donulur. Yani kotu
durumda davranis bugunku davranisin AYNISI olur, daha kotusu degil.

⚠ KOORDINAT SOZLESMESI: bu modul YALNIZ goruntuyu kirpar. Tespit sonuclari
   cagiran tarafindan (x0, y0) ile TAM KARE pikseline geri cevrilir. Yasa ve
   tespit_akisi hicbir sey fark etmez -- onlar hep tam-kare pikseli gorur.
================================================================================
"""
import os
import time

BOYUT = int(os.environ.get("AVCI_KROP_BOYUT", "960"))      # pencere kenari (px)
BAYAT_S = float(os.environ.get("AVCI_KROP_BAYAT", "0.5"))  # bu kadar eskiyse tam kare
# ⚠ 2026-08-16 20:50 varsayilan KAPALI. Krop+poz birlikte FPS'i 53 -> 14.5
# dusurdu; hangisinin ne kadar payi oldugu AYRI olculmedi (gorev dustu).
# Krop'un kendisi det_ms'i DUSURMELI (gri bant kalkiyor) ama TensorRT motoru
# statik 960x960 ve kropla tam kare arasinda gidip gelmek motoru her seferinde
# yeniden yapilandiriyor olabilir -- bu OLCULMEDI.
# Denemek icin: AVCI_KROP=1  (once TEK BASINA, poz KAPALI olcun)
AKTIF = os.environ.get("AVCI_KROP", "0").strip() not in ("", "0")

_son = {"t": 0.0, "cx": None, "cy": None}
_sayac = {"krop": 0, "tam": 0}


def tespit_bildir(cx, cy, t=None):
    """Dedektor TAM KARE pikselinde bir hedef bulduysa cagrilir."""
    _son["t"] = time.perf_counter() if t is None else t
    _son["cx"] = float(cx)
    _son["cy"] = float(cy)


def sifirla():
    _son["t"] = 0.0
    _son["cx"] = _son["cy"] = None


def hazirla(bgr):
    """(krop_goruntu, x0, y0) dondurur. Krop yoksa (bgr, 0, 0).

    Krop kosullari: AKTIF, son tespit taze, ve kare kroptan buyuk.
    """
    if bgr is None or not AKTIF:
        return bgr, 0, 0
    try:
        h, w = bgr.shape[:2]
    except Exception:
        return bgr, 0, 0
    if w <= BOYUT and h <= BOYUT:
        return bgr, 0, 0                      # zaten kucuk, kirpmanin anlami yok
    cx, cy = _son["cx"], _son["cy"]
    if cx is None or (time.perf_counter() - _son["t"]) > BAYAT_S:
        _sayac["tam"] += 1
        return bgr, 0, 0                      # GERI CEKILME: tam kare
    yari = BOYUT // 2
    x0 = int(round(cx)) - yari
    y0 = int(round(cy)) - yari
    # kareden tasmayi ICERI cek (pencere boyutu SABIT kalsin)
    x0 = max(0, min(x0, w - BOYUT))
    y0 = max(0, min(y0, h - BOYUT))
    if BOYUT > h:                             # kare kroptan alcaksa dikeyde tam al
        y0 = 0
        alt = bgr[0:h, x0:x0 + BOYUT]
        _sayac["krop"] += 1
        return alt, x0, 0
    _sayac["krop"] += 1
    return bgr[y0:y0 + BOYUT, x0:x0 + BOYUT], x0, y0


def durum():
    n = _sayac["krop"] + _sayac["tam"]
    return {"aktif": AKTIF, "boyut": BOYUT,
            "krop": _sayac["krop"], "tam": _sayac["tam"],
            "krop_oran": (_sayac["krop"] / n) if n else 0.0}

# -*- coding: utf-8 -*-
"""PERIYODIK KESTIRICI testleri.

Bu modul hedef konum hatasini 14.9 m -> 5.8 m indiriyor ve o hata
bugune kadar olculen EN BUYUK tek hata kaynagi (angajman 10-30 m'de
geciyor). Testler ucus kararlarini ve tuzaklari kilitler.

Olculen dayanaklar (2026-08-19, 1055 esli ornek, yarisma modu):
  HAM bozuk GPS      : medyan 21.6 m | p90 39.5
  mevcut "j" filtresi: medyan 14.9 m | p90 39.0
  bu modul (nedensel): medyan  5.8 m | p90 10.1
  olumsuz kontrol (ileri=0): 21.3 m  <- kazanc GECIKME TELAFISINDEN
"""
import os
import sys
import math

import pytest

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)

from fusion.periyodik_kestirici import PeriyodikKestirici, SICRAMA_M  # noqa: E402


def _pist(pk, sure_s, P=29.6, R=200.0, hz=4.4, t0=0.0,
          gecikme=0.0, gurultu=0.0, tohum=1):
    """Kapali oval pist besle.

    gecikme: raporlanan konum bu kadar GEC (oyunun delay_s'i gibi)
    gurultu: deterministik salinim genligi (m)
    """
    n = int(sure_s * hz)
    t = t0
    for i in range(n):
        t = t0 + i / hz
        tg = t - gecikme                       # raporlanan = gecmisteki konum
        a = 2.0 * math.pi * tg / P
        x = R * math.cos(a) + 0.4 * R * math.cos(3 * a)   # oval-benzeri
        y = R * math.sin(a)
        if gurultu:
            x += gurultu * math.sin(7.3 * i + tohum)
            y += gurultu * math.cos(5.1 * i + tohum)
        pk.ekle(t, x, y, 80.0)
        pk.guncelle(t)
    return t


def _gercek(t, P=29.6, R=200.0):
    a = 2.0 * math.pi * t / P
    return (R * math.cos(a) + 0.4 * R * math.cos(3 * a), R * math.sin(a))


def test_veri_yokken_hazir_degil():
    pk = PeriyodikKestirici()
    assert pk.hazir() is False
    assert pk.kestir(5.0) is None


def test_kisa_gozlemde_kapi_KAPALI():
    """Bir tur + ortusme (>=75 s) gormeden ASLA kestirim uretme."""
    pk = PeriyodikKestirici()
    _pist(pk, 40.0)
    assert pk.hazir() is False
    assert pk.kestir(50.0) is None


def test_periyodu_bulur_ve_acilir():
    pk = PeriyodikKestirici()
    _pist(pk, 130.0)
    assert pk.hazir() is True
    assert pk.periyot == pytest.approx(29.6, abs=0.3)
    assert pk.kalite < 2.0


def test_GECIKMEYI_TELAFI_EDER():
    """⭐ MODULUN VAR OLMA SEBEBI.

    Rapor edilen konum 1.2 s GECIKMELI. `ileri_s=1.2` ile model GERCEK
    konumu geri kazanmali; `ileri_s=0` ile gecikme kadar SAPMALI.
    """
    GEC = 1.2
    iyi = PeriyodikKestirici(ileri_s=GEC)
    son = _pist(iyi, 130.0, gecikme=GEC)
    kotu = PeriyodikKestirici(ileri_s=0.0)
    _pist(kotu, 130.0, gecikme=GEC)
    assert iyi.hazir() and kotu.hazir()

    gx, gy = _gercek(son)
    pi = iyi.kestir(son)
    pk_ = kotu.kestir(son)
    assert pi is not None and pk_ is not None
    h_iyi = math.hypot(pi[0] - gx, pi[1] - gy)
    h_kotu = math.hypot(pk_[0] - gx, pk_[1] - gy)
    assert h_iyi < 5.0, "telafi calismadi (%.1f m)" % h_iyi
    assert h_kotu > 3 * h_iyi, \
        "OLUMSUZ KONTROL BOZUK: ileri=0 de iyi cikti (%.1f vs %.1f)" % (h_kotu, h_iyi)


def test_gurultuyu_duzlestirir():
    """Uydurma gurultuyu bastirmali: kestirim ham gurultuden KUCUK sapmali.

    ⚠ Genlik GERCEKCI secilmeli: sahadaki uydurma artigi 5.5 m olculdu ve
    kapi esigi 12 m. 15 m genlikli sentetik gurultu artigi esigin USTUNE
    cikarir ve kapi -- DOGRU sekilde -- kapanir; o zaman test modulu degil
    kendi kurgusunu olcer.
    """
    G = 8.0
    pk = PeriyodikKestirici(ileri_s=0.0)
    son = _pist(pk, 130.0, gurultu=G)
    assert pk.hazir()
    gx, gy = _gercek(son)
    p = pk.kestir(son)
    assert p is not None
    assert math.hypot(p[0] - gx, p[1] - gy) < G, "duzlestirme yok"


def test_tekrarsiz_pistte_kapi_KAPANIR():
    """Hedef kapali pist ucmuyorsa (8 varyanttan biri degisirse) kapi kapali."""
    pk = PeriyodikKestirici()
    t = 0.0
    for i in range(700):
        t = i / 4.4
        pk.ekle(t, 3.0 * t + 40 * math.sin(0.017 * t),
                1.5 * t * math.cos(0.009 * t), 80.0)
        pk.guncelle(t)
    assert pk.hazir() is False


def test_saat_geriye_giderse_sifirlanir():
    pk = PeriyodikKestirici()
    _pist(pk, 130.0)
    assert pk.hazir() is True
    pk.ekle(1.0, 0.0, 0.0, 80.0)          # sunucu yeniden basladi
    assert pk.hazir() is False


def test_BOZULMA_SICRAMASI_tamponu_SIFIRLAMAZ():
    """⚠ BU TUZAK MODULU BIR KEZ TAMAMEN CALISMAZ YAPTI.

    Bozuk sinyal ornekler arasi 40+ m ziplar (olculen p99 40.1, maks 43.3).
    Ilk surumde esik HIZ (55 m/s = 12.4 m/ornek) idi -> orneklerin %5.5'i
    "isinlanma" sayilip tampon SUREKLI sifirlandi ve kapi HIC acilmadi
    (0/1055). Esik MUTLAK MESAFE (150 m) olmali.
    """
    pk = PeriyodikKestirici()
    t = 0.0
    hz = 4.4
    for i in range(int(130 * hz)):
        t = i / hz
        a = 2.0 * math.pi * t / 29.6
        x = 200 * math.cos(a) + 0.4 * 200 * math.cos(3 * a)
        y = 200 * math.sin(a)
        if i % 20 == 0:                    # her 20 ornekte 40 m'lik sicrama
            x += 40.0
        pk.ekle(t, x, y, 80.0)
        pk.guncelle(t)
    assert pk.hazir() is True, "bozulma sicramasi tamponu sifirladi (REGRESYON)"


def test_ISINLANMA_tamponu_SIFIRLAR():
    """Gorev yeniden baslangicinda hedef YUZLERCE metre isinlanir -> sifirla."""
    pk = PeriyodikKestirici()
    son = _pist(pk, 130.0)
    assert pk.hazir() is True
    pk.ekle(son + 0.25, 5000.0, 5000.0, 80.0)   # >> SICRAMA_M
    assert pk.hazir() is False


def test_arkaplan_iscisi_kontrol_dongusunu_BLOKLAMAZ():
    """⚠ `guncelle()` olculdu: p99 18.7 ms, MAKS 121.8 ms. 20 Hz dongude
    (50 ms tik) bu IKI TIK dusurur. Uydurma AYRI IS PARCACIGINDA olmali;
    kontrol dongusunde yalniz `ekle` + `kestir` cagrilir."""
    import time
    pk = PeriyodikKestirici()
    pk.isci_baslat(arali_s=0.05)
    try:
        t = 0.0
        en_uzun = 0.0
        for i in range(400):
            t = i / 4.4
            a = 2.0 * math.pi * t / 29.6
            b = time.perf_counter()
            pk.ekle(t, 200 * math.cos(a), 200 * math.sin(a), 80.0)
            pk.kestir(t)
            en_uzun = max(en_uzun, (time.perf_counter() - b) * 1000.0)
        assert en_uzun < 5.0, "kontrol dongusu %.1f ms bloke oldu" % en_uzun
    finally:
        pk.isci_durdur()


def test_tani_alanlari():
    pk = PeriyodikKestirici()
    _pist(pk, 130.0)
    d = pk.tani()
    for k in ("pk_periyot_s", "pk_kalite_m", "pk_hazir", "pk_ornek",
              "pk_sure_s", "pk_ileri_s"):
        assert k in d
    assert d["pk_hazir"] is True


def test_sicrama_esigi_bozulmadan_BUYUK():
    """Esik, olculen en buyuk bozulma sicramasindan (43.3 m) belirgin buyuk
    ama isinlanmadan (yuzlerce m) kucuk olmali."""
    assert 100.0 <= SICRAMA_M <= 300.0

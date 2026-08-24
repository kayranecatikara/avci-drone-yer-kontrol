# -*- coding: utf-8 -*-
"""hedef_tekrar SICRAMA ESIGI regresyonu.

⚠ BU TUZAK MODULU IKI KEZ TAMAMEN CALISMAZ YAPTI.
Once `fusion/periyodik_kestirici.py`'de (esik HIZ idi -> orneklerin %5.5'i
"isinlanma" sayildi, kapi 0/1055 acildi), sonra AYNI hata burada bulundu:

  UCUSTA OLCULDU (2026-08-19, yarisma modu, tani satirlari):
      bayrak=True, menzil>=15 saglaniyor
      tampon uzunlugu 2, 4, 7, 11, 33, 2 ...   -> MIN_ORNEK=120'ye ULASAMIYOR
      tk_periyot=None  ->  PUSU 5166 satirda 0 kez atesledi

Sebep: 20 Hz'de dt=0.05 s iken HIZ esigi 55 m/s = ornek basina 2.75 m,
bozuk GPS ise 40+ m ziplar (olculen p99 40.1, maks 43.3).
Esik MUTLAK MESAFE olmali.
"""
import math
import os
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
sys.path.insert(0, os.path.join(KOK, "kopru", "gazebo_kaynak"))

from control.guidance.hedef_tekrar import HedefTekrar, SICRAMA_M  # noqa: E402


def _besle(tk, sure_s, hz=20.0, P=29.6, R=200.0, bozulma=0.0, tohum=1):
    """Kapali oval; `bozulma` metre genlikli ornekler-arasi ZIPLAMA ekler."""
    n = int(sure_s * hz)
    t = 0.0
    for i in range(n):
        t = i / hz
        a = 2.0 * math.pi * t / P
        x = R * math.cos(a) + 0.4 * R * math.cos(3 * a)
        y = R * math.sin(a)
        if bozulma:
            # her ornekte isaret degistiren ziplama: gercek bozulma deseni
            x += bozulma * (1 if i % 2 else -1)
            y += bozulma * (1 if i % 3 else -1) * 0.5
        tk.ekle(t, x, y, 80.0)
        tk.guncelle(t)
    return t


def test_esik_MUTLAK_MESAFE_ve_makul():
    """43 m'lik bozulma sicramasindan BUYUK, isinlanmadan (yuzlerce m) KUCUK."""
    assert 100.0 <= SICRAMA_M <= 300.0


def test_BOZULMA_SICRAMASI_tamponu_SIFIRLAMAZ():
    """⭐ REGRESYON KILIDI: 40 m'lik ornekler-arasi ziplama tamponu oldurmemeli."""
    tk = HedefTekrar(kalite_max=12.0)
    _besle(tk, 120.0, bozulma=20.0)      # ornekler arasi ~40 m fark
    assert len(tk._buf) > 100, \
        "tampon sifirlandi (REGRESYON): n=%d" % len(tk._buf)


def test_TEMIZ_veride_periyot_kilitlenir():
    tk = HedefTekrar(kalite_max=12.0)
    _besle(tk, 120.0)
    assert tk.periyot is not None
    assert abs(tk.periyot - 29.6) < 1.0


def test_GERCEK_ISINLANMA_hala_SIFIRLAR():
    """Gorev yeniden dogusu (yuzlerce metre) tamponu SIFIRLAMALI."""
    tk = HedefTekrar(kalite_max=12.0)
    son = _besle(tk, 120.0)
    assert len(tk._buf) > 100
    tk.ekle(son + 0.05, 9000.0, 9000.0, 80.0)
    assert len(tk._buf) <= 1, "isinlanma yakalanmadi"


def test_kalite_esigi_AYARLANABILIR():
    """Yarisma modunda artik ~5 m; 3.0 sabit esik kapiyi HIC acmaz."""
    tk = HedefTekrar(kalite_max=10.0)
    assert tk.kalite_max == 10.0

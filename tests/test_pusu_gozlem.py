# -*- coding: utf-8 -*-
"""
================================================================================
  PUSU GOZLEM AYRIMI  --  model beslenirse hazir oluyor mu?
================================================================================
2026-08-21'de olculdu: `_tk.ekle/guncelle` cagrilari `cfg.PUSU` kapisinin
ardindaydi; yani model yalnizca PUSU ACIKKEN beslenirdi. Ama PUSU'nun ise
yaramasi icin modelin ZATEN bir tur (~30 s) gozlem birikmis olmasi gerekir
-> tavuk-yumurta, pusu hicbir zaman ateslenemez.

Yama: GOZLEM kapisiz, EYLEM hala `cfg.PUSU`'ya bagli.

Bu testler yamanin dayandigi PREMISI dogrular:
  1) model yeterince beslenince hazir() True olur ve periyodu bulur
  2) yetersiz gozlemde hazir() False'tur (uydurma kestirim YOK)
  3) sicrama (yeniden dogus isinlanmasi) tamponu sifirlar
  4) periyodu bilerek bozunca kalite kotulesir (olumsuz kontrol)
================================================================================
"""
import math
import os
import sys

import pytest

_KAYNAK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "kopru", "gazebo_kaynak")
if _KAYNAK not in sys.path:
    sys.path.insert(0, _KAYNAK)

from control.guidance.hedef_tekrar import (          # noqa: E402
    HedefTekrar, PERIYOT_BEKLENEN, SICRAMA_M,
)

# ⚠ MIN_GOZLEM_S = 45.0 s (docstring 30 s ima ediyor, GERCEK 45).
#   Ayrica guncelle() pahali taramayi YENIDEN_HESAP_S=2.0 s'den sik yapmaz,
#   yani TAM 45.0 s beslemek YETMEZ: son hesap 44. saniyede olur ve
#   "sure < min_gozlem_s" kapisina takilir. Testler 60 s besler.
GOZLEM_S = 60.0
HZ = 20.0
PERIYOT = 29.6
YARICAP = 90.0          # m; oval yaricapi (olculen pist mertebesi)


def _oval(t, periyot=PERIYOT, r=YARICAP, ovallik=0.65):
    """Kapali, tekrarlayan pist. Hedefin gercek ovaline benzer."""
    a = 2.0 * math.pi * (t / periyot)
    return r * math.cos(a), r * ovallik * math.sin(a)


def _besle(tk, sure_s, t0=1000.0, periyot=PERIYOT, gurultu=0.0):
    n = int(sure_s * HZ)
    for i in range(n):
        t = t0 + i / HZ
        x, y = _oval(t, periyot=periyot)
        if gurultu:
            # deterministik, tohumsuz kucuk salinim (rastgelelik testte istenmez)
            x += gurultu * math.sin(t * 7.3)
            y += gurultu * math.cos(t * 5.1)
        tk.ekle(t, x, y, 40.0)
        tk.guncelle(t)
    return t0 + (n - 1) / HZ


def test_bir_tur_gozlemle_hazir_olur():
    """PREMIS: yeterince beslenirse model periyodu bulur ve hazir() True olur."""
    tk = HedefTekrar()
    _besle(tk, GOZLEM_S)
    assert tk.hazir(), (
        "%g s oval gozleminden sonra model HAZIR olmali " % GOZLEM_S +
        "(periyot=%s kalite=%s)" % (tk.periyot, tk.kalite))
    assert tk.periyot is not None
    assert abs(tk.periyot - PERIYOT) < 1.5, (
        "kestirilen periyot %.2f, beklenen %.1f" % (tk.periyot, PERIYOT))


def test_yetersiz_gozlemde_hazir_degil():
    """Uydurma kestirim YOK: bir turdan kisa gozlemde kapi KAPALI kalir."""
    tk = HedefTekrar()
    _besle(tk, 8.0)
    assert not tk.hazir(), "8 s gozlemle hazir() True donmemeli"


def test_tam_esik_yetmez_throttle_yuzunden():
    """MIN_GOZLEM_S kadar beslemek YETMEZ (2 s throttle son hesabi kacirir).
    Bu bir KOD hatasi degil, olculmus davranis -- cagiran pay birakmali."""
    tk = HedefTekrar()
    _besle(tk, 45.0)
    assert not tk.hazir(), "tam esikte hazir olmamali (throttle payi)"


def test_bos_model_hazir_degil():
    """Hic beslenmemis model -- yamadan ONCEKI canli durum (tk_n=0)."""
    tk = HedefTekrar()
    assert not tk.hazir()
    assert tk.periyot is None


def test_sicrama_tamponu_sifirlar():
    """Yeniden dogusta hedef isinlanir; tampon GECERSIZ sayilmali."""
    tk = HedefTekrar()
    son_t = _besle(tk, GOZLEM_S)
    assert tk.hazir()
    # SICRAMA_M'den buyuk ani yer degistirme
    tk.ekle(son_t + 0.05, 5000.0, 5000.0, 40.0)
    assert not tk.hazir(), (
        "%.0f m'lik sicramadan sonra model kendini gecersiz saymali" % SICRAMA_M)


def test_saat_geriye_giderse_sifirlar():
    """Sunucu yeniden baslarsa monotonik saat sifirlanir -> tampon atilmali."""
    tk = HedefTekrar()
    _besle(tk, GOZLEM_S)
    assert tk.hazir()
    tk.ekle(10.0, 0.0, 0.0, 40.0)          # saat geriye gitti
    assert not tk.hazir()


def test_olumsuz_kontrol_bozuk_pist_kaliteyi_kotulestirir():
    """Kapali pist DEGILSE (surekli suruklenen hedef) kalite kapisi kapanmali."""
    tk = HedefTekrar()
    t0 = 1000.0
    n = int(GOZLEM_S * HZ)
    for i in range(n):
        t = t0 + i / HZ
        x, y = _oval(t)
        x += 3.0 * (t - t0)                # 3 m/s surekli suruklenme: pist KAPALI degil
        tk.ekle(t, x, y, 40.0)
        tk.guncelle(t)
    assert not tk.hazir(), (
        "surukleneni tekrar sanmamali (periyot=%s kalite=%s)"
        % (tk.periyot, tk.kalite))


def test_beklenen_periyot_sabiti_yazili_degil():
    """Periyot her kosuda YENIDEN kestirilir; sabit yazilmis olmamali."""
    tk = HedefTekrar()
    assert tk.periyot is None, "taze model periyodu ONCEDEN bilmemeli"
    assert PERIYOT_BEKLENEN > 0


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))

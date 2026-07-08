# -*- coding: utf-8 -*-
"""
KESISIM (INTERCEPT) LEAD dogrulama — guidance.ana_kontrol.intercept_tgo (saf fonksiyon).

Test edilenler:
  1) Tanim ozelligi: gecerli kesisim varsa |r + Vt*t_go| == vo*t_go (avci vo ile o
     noktaya tam o surede varir).
  2) Durgun hedef (Vt=0): t_go = menzil / vo; nisan = hedef (lead yok).
  3) Capraz hedef: nisan noktasi hedefin ONUNDE (hiz yonunde) -> onunu keser.
  4) Karsidan gelen (head-on): saf takibe gore t_go kucuk, nisan ~ hedef.
  5) Kaciyor + hedef vo'dan HIZLI (kesisim yok): menzil/vo pursuit-lead'e duser (sonlu, >0).
  6) Tavan: t_go <= tgo_max.
  7) Sifir menzil: t_go = 0.

Calistirma:  python tests/test_intercept.py
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from guidance.ana_kontrol import intercept_tgo   # noqa: E402

_gecti = 0
_kaldi = 0


def onay(ad, kosul):
    global _gecti, _kaldi
    if kosul:
        _gecti += 1
        print("OK   " + ad)
    else:
        _kaldi += 1
        print("HATA " + ad)


def test_tanim_ozelligi_capraz():
    # drone orijinde, hedef (10000,0) cm, saga-capraz hiz (0, 1500) cm/s, vo=2500
    rx, ry, vtx, vty, vo = 10000.0, 0.0, 0.0, 1500.0, 2500.0
    t = intercept_tgo(rx, ry, vtx, vty, vo, 10.0)
    # bulusma noktasina uzaklik = vo*t olmali (kesisim tanimi)
    ix, iy = rx + vtx * t, ry + vty * t
    onay("test_tanim_ozelligi_capraz (|r+Vt*t|==vo*t)",
         abs(math.hypot(ix, iy) - vo * t) < 1.0 and t > 0.0)


def test_durgun_hedef():
    rx, ry, vo = 8000.0, 0.0, 2000.0
    t = intercept_tgo(rx, ry, 0.0, 0.0, vo, 10.0)
    onay("test_durgun_hedef (t_go = menzil/vo)", abs(t - 8000.0 / 2000.0) < 1e-3)


def test_capraz_nisan_onde():
    # capraz hedefte nisan noktasi hedefin ONUNDE (hiz yonunde ty>0) olmali
    rx, ry, vtx, vty, vo = 12000.0, 0.0, 0.0, 1800.0, 2500.0
    t = intercept_tgo(rx, ry, vtx, vty, vo, 10.0)
    nisan_y = ry + vty * t                          # hedef + Vt*t (lead noktasi, drone-goreli)
    onay("test_capraz_nisan_onde (lead hiz yonunde, hedefi kesecek)", nisan_y > 500.0)


def test_head_on_kucuk_tgo():
    # hedef karsidan geliyor (rx>0, vtx<0): kapanma hizli -> t_go < menzil/vo (durgun hal)
    rx, vo = 10000.0, 2500.0
    t_head = intercept_tgo(rx, 0.0, -1500.0, 0.0, vo, 10.0)
    t_durgun = intercept_tgo(rx, 0.0, 0.0, 0.0, vo, 10.0)
    onay("test_head_on_kucuk_tgo (karsidan gelende t_go daha kucuk)",
         0.0 < t_head < t_durgun)


def test_kaciyor_hizli_fallback():
    # hedef vo'dan HIZLI ve kaciyor (rx>0, vtx>vo): gercek kesisim yok -> fallback sonlu>0
    rx, vo = 10000.0, 2000.0
    t = intercept_tgo(rx, 0.0, 3000.0, 0.0, vo, 10.0)   # hedef 3000>vo=2000, uzaklasiyor
    onay("test_kaciyor_hizli_fallback (kesisim yok -> menzil/vo)",
         math.isfinite(t) and t > 0.0)


def test_tavan():
    # cok uzak + yavas kapanma -> buyuk t_go ama tavana clamp
    t = intercept_tgo(500000.0, 0.0, 0.0, 0.0, 100.0, 4.0)
    onay("test_tavan (t_go <= tgo_max)", t <= 4.0 + 1e-9)


def test_sifir_menzil():
    onay("test_sifir_menzil (t_go = 0)", intercept_tgo(0.0, 0.0, 1000.0, 500.0, 2500.0, 4.0) == 0.0)


if __name__ == "__main__":
    test_tanim_ozelligi_capraz()
    test_durgun_hedef()
    test_capraz_nisan_onde()
    test_head_on_kucuk_tgo()
    test_kaciyor_hizli_fallback()
    test_tavan()
    test_sifir_menzil()
    print("\n%d/%d test gecti." % (_gecti, _gecti + _kaldi))
    sys.exit(1 if _kaldi else 0)

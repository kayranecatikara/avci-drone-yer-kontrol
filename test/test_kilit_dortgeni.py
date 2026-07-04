# -*- coding: utf-8 -*-
"""
Madde 3: kilit dortgeni dogrulamalari (kilit_kurali kadraj proxy + arac truth).
Calistirma:  python test/test_kilit_dortgeni.py   (sim GEREKMEZ)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "arac"))
from guidance.kilit_kurali import KilitDurumu, KilitCfg
import kilit_dortgeni as kd_arac

W, H = 1920, 1080


def _hedef(cx, cy, w, h):
    return {"cx": cx, "cy": cy, "w": w, "h": h}


# ---- pipeline PROXY: dortgen_kadraj_orani (truth-bagimsiz) ----
def test_kadraj_tam_ici():
    o = KilitDurumu.dortgen_kadraj_orani(_hedef(960, 540, 200, 150), W, H)
    assert abs(o - 1.0) < 1e-9


def test_kadraj_yari_tasma():
    # bbox merkezi sol kenarda: yarisi ekran disi -> ~0.5
    o = KilitDurumu.dortgen_kadraj_orani(_hedef(0, 540, 200, 150), W, H)
    assert abs(o - 0.5) < 0.02


def test_kadraj_proxy_engel():
    # bbox %20 tasarsa (kadraj orani <0.90) sayac ENGEL: dortgen_tasma
    dur = KilitDurumu()
    # cx=W-20, w=200 -> sag 120px disarda / 200 = %60 disarda -> orani 0.4
    h = {"cx": W - 20, "cy": 540, "w": 200, "h": 150, "conf": 0.9,
         "tespit_mi": True, "track_durumu": "CONFIRMED"}
    out = dur.adim(h, W, H, 0.1, 0.45)
    assert out["sayan"] is False and out["engel"] == "dortgen_tasma"


# ---- arac TRUTH dogrulama (>=%90 icerme + merkez + cizgi) ----
def test_truth_ideal_gecer():
    r = kd_arac.dortgen_dogrula((960, 540, 200, 150), (960, 540, 200, 150), cizgi_px=2)
    assert r["gecerli"] and r["icerme_orani"] >= 0.99
    assert r["merkez_dx_orani"] < 0.01 and r["cizgi_ok"]


def test_truth_icerme_dusuk():
    # dortgen hedeften kaymis -> hedefin <%90'i icinde
    r = kd_arac.dortgen_dogrula((960 + 120, 540, 200, 150), (960, 540, 200, 150))
    assert not r["gecerli"] and r["icerme_orani"] < 0.90


def test_truth_merkez_yatay_asim():
    # merkez farki yatayda w/2'yi asar (dw kaymasi > tw/2)
    r = kd_arac.dortgen_dogrula((960 + 110, 540, 200, 150), (960, 540, 200, 150))
    assert r["merkez_dx_orani"] > 1.0 and not r["gecerli"]


def test_truth_cizgi_kalin():
    r = kd_arac.dortgen_dogrula((960, 540, 200, 150), (960, 540, 200, 150), cizgi_px=5)
    assert not r["cizgi_ok"] and not r["gecerli"]      # 5 > 3 px


def test_cizgi_sabiti_3px():
    assert KilitCfg.CIZGI_PX == 3


if __name__ == "__main__":
    testler = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in testler:
        t()
        print("OK  %s" % t.__name__)
    print("TUM TESTLER GECTI (%d)" % len(testler))

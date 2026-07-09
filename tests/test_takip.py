# -*- coding: utf-8 -*-
"""
TAKIP smoke testi — HybridSort (boxmot) adaptoru (detection/takip.py).
Eski EL-YAZIMI ByteTrack kaldirildi (2026-07-09); bu testler artik ADAPTOR
sozlesmesini dogrular (arayuz + tek-hedef ciktisi + bos-tespit). boxmot gerekir.

Calistirma:  python tests/test_takip.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from detection import takip as tk


def _img():
    return np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)


def _det(cx, cy, w=60, h=40, conf=0.85, **ek):
    d = {"cx": float(cx), "cy": float(cy), "w": float(w), "h": float(h),
         "conf": float(conf), "cls": 0, "W": 1920, "H": 1080}
    d.update(ek)
    return d


def test_cfg_conf_dusuk():
    # server predict esigini takipci.cfg.CONF_DUSUK'ten okur -> var ve makul olmali
    assert hasattr(tk.TakipCfg, "CONF_DUSUK")
    assert 0.0 <= tk.TakipCfg.CONF_DUSUK <= tk.TakipCfg.CONF_YUKSEK


def test_arayuz_ve_id_surekliligi():
    # Hareketli hedef: adaptor track dondurur, ID sabit kalir, dict sozlesmesi tam.
    tp = tk.Takipci()
    img = _img()
    out = None
    ilk_id = None
    for i in range(6):
        out = tp.guncelle([_det(960 + i * 8, 540, t=100.0 + i * 0.1)], 0.05, None, None, frame=img)
        assert out is not None, "hareketli hedefte track beklenir (kare %d)" % i
        for k in ("track_id", "cx", "cy", "w", "h", "conf", "tespit_mi", "W", "H"):
            assert k in out, "cikti sozlesmesinde %s yok" % k
        assert out["tespit_mi"] is True
        if ilk_id is None:
            ilk_id = out["track_id"]
        assert out["track_id"] == ilk_id, "ID surekliligi kopmamali"
    assert out["t"] == 100.5, "eslesen tespitin t'si tasinmali"


def test_bos_tespit_none():
    # Tespit yok -> HybridSort track dondurmez (coast ciktisi yok) -> None.
    tp = tk.Takipci()
    img = _img()
    for i in range(4):
        tp.guncelle([_det(960, 540)], 0.05, None, None, frame=img)
    assert tp.guncelle([], 0.05, None, None, frame=img) is None


def test_frame_yoksa_none():
    # HybridSort kareyi ISTER; frame=None -> guvenli None (cokme yok).
    tp = tk.Takipci()
    assert tp.guncelle([_det(960, 540)], 0.05, None, None, frame=None) is None


def test_sifirla():
    tp = tk.Takipci()
    img = _img()
    tp.guncelle([_det(960, 540)], 0.05, None, None, frame=img)
    tp.sifirla()
    assert tp.trackler == []


if __name__ == "__main__":
    testler = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in testler:
        t()
        print("OK  %s" % t.__name__)
    print("TUM TESTLER GECTI (%d)" % len(testler))

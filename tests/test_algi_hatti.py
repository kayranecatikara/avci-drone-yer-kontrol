# -*- coding: utf-8 -*-
"""
FAZ 1: detection/algi_hatti.py testleri (sim/YOLO GEREKMEZ — sahte dedektor).
Calistirma:  python test/test_algi_hatti.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from detection.algi_hatti import AlgiHatti, AlgiCiktisi


class SahteDedektor:
    """tespit_hepsi(frame) -> onceden kurulmus kutu listesi (frame yok sayilir)."""

    def __init__(self):
        self.hazir = True
        self.kutular = []

    def tespit_hepsi(self, frame):
        return list(self.kutular)


def _det(cx, cy, w=40, h=30, conf=0.9, **ek):
    d = {"cx": float(cx), "cy": float(cy), "w": float(w), "h": float(h),
         "conf": float(conf), "W": 1920, "H": 1080}
    d.update(ek)
    return d


def test_model_yoklugu_graceful():
    # dedektor None -> hedef None, sistem cokmez (GPS ile ucar)
    ah = AlgiHatti(dedektor=None)
    c = ah.adim(frame=None, attitude=(0, 0, 0), t=0.0)
    assert isinstance(c, AlgiCiktisi) and c.hedef is None
    assert ah.son_cikti().hedef is None


def test_kilit_ve_snapshot():
    ded = SahteDedektor()
    ah = AlgiHatti(dedektor=ded)
    t = 0.0
    for i in range(5):
        ded.kutular = [_det(500 + i, 400)]
        c = ah.adim(frame="x", attitude=(0, 0, 0), t=t)
        t += 0.02
    assert c.hedef is not None and c.hedef["track_durumu"] == "CONFIRMED"
    # son_cikti AYNI snapshot'i vermeli (thread-guvenli okuma)
    assert ah.son_cikti().hedef["track_id"] == c.hedef["track_id"]


def test_turev_algi_timestampi():
    # LOS bearing turevi: hedef sabit hizla (Kalman ogrenir, IoU korunur) yatayda
    # kayarken lam_dot sifir olmamali; buyuklugu algi dt'siyle olceklenir.
    ded = SahteDedektor()
    ah = AlgiHatti(dedektor=ded)
    t = 0.0
    cx = 700.0
    for i in range(9):
        cx += 10.0                            # her frame +10px (Kalman hiz ogrenir)
        ded.kutular = [_det(cx, 300)]
        c = ah.adim("x", (0, 0, 0), t); t += 0.02
        if i >= 6:                            # kilit + hiz oturduktan sonra
            assert abs(c.lam_dot) > 1e-6, "hareket -> sifir olmayan lam_dot"
            assert c.hedef["tespit_mi"] is True
    # Vc: hedef buyurken (yaklasirken) pozitif — konum sabit, bbox buyusun
    for i in range(4):
        ded.kutular = [_det(cx, 300, w=60 + i * 12, h=45 + i * 9)]
        c = ah.adim("x", (0, 0, 0), t); t += 0.02
    assert c.Vc > 0, "bbox buyurken Vc pozitif (yaklasma vekili)"


def test_coast_turev_resetlenir():
    # coast'ta (tespit_mi False) turev uretilmez -> lam_dot/Vc = 0
    ded = SahteDedektor()
    ah = AlgiHatti(dedektor=ded)
    t = 0.0
    for i in range(6):
        ded.kutular = [_det(500 + i * 20, 400)]
        ah.adim("x", (0, 0, 0), t); t += 0.02
    ded.kutular = []                              # tespit yok -> coast
    c = ah.adim("x", (0, 0, 0), t)
    assert c.hedef is not None and c.hedef["tespit_mi"] is False
    assert c.lam_dot == 0.0 and c.Vc == 0.0       # coast turev URETMEZ


def test_cmc_beslemesi_cokmez():
    # attitude degisirken H_cmc kurulur ve takip'e verilir; hedef izi kopmamali
    ded = SahteDedektor()
    ah = AlgiHatti(dedektor=ded)
    t = 0.0
    yaw = 0.0
    tid = None
    for i in range(10):
        ded.kutular = [_det(960, 400)]
        c = ah.adim("x", (0.0, 0.0, yaw), t)
        yaw += 1.0; t += 0.02
        if c.hedef and c.hedef["track_durumu"] == "CONFIRMED":
            tid = tid or c.hedef["track_id"]
    assert tid is not None and c.hedef["track_id"] == tid   # ID CMC altinda sabit


if __name__ == "__main__":
    testler = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in testler:
        t()
        print("OK  %s" % t.__name__)
    print("TUM TESTLER GECTI (%d)" % len(testler))

# -*- coding: utf-8 -*-
"""
FAZ 0: arac/k_sanity_olcum.py ANALIZ yolunun sentetik dogrulamasi (sim GEREKMEZ).
Calistirma:  python test/test_k_sanity_arac.py

Mantik: bilinen bir "gercek" HFOV ile sentetik ucus CSV'si uret (bbox genislik +
merkez, truth konumlar, temiz attitude) ve araca analiz ettir.
  A) gercek HFOV = 125 (varsayimla AYNI)  -> GECTI, sapma ~%0, merkez offset kucuk
  B) gercek HFOV = 100 (varsayim YANLIS)  -> KALDI, sapma buyuk (arac yakalar)
Boylece sim kosusundan ONCE aracin matematigi/kapilari kanitlanir (arac hatasi
sim olcumune "GECTI/KALDI" olarak yansimaz).
"""
import csv
import math
import os
import sys
import tempfile

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "arac"))

from detection import kamera_model as km            # noqa: E402
import k_sanity_olcum as ks                         # noqa: E402


def sentetik_csv(hfov_gercek_deg, yol, sure_s=8.0, fps=20.0):
    """Duz ucusla yaklasan hedef; bbox'lar 'gercek' HFOV'la render edilmis gibi."""
    rng = np.random.default_rng(42)
    fx_g = 960.0 / (2.0 * math.tan(math.radians(hfov_gercek_deg) / 2.0))
    W, H = 960, 540
    dpos = np.array([0.0, 0.0, 5000.0])
    v = np.array([-1200.0, 0.0, 0.0])               # cm/s; drona dogru duz ucus
    # z: yakin pencerede (~x=50m) optik eksene yakin dursun (tilt 25 -> +x*tan25)
    p0 = np.array([12000.0, 400.0, 7332.0])
    n = int(sure_s * fps)
    with open(yol, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(ks.CSV_KOLON)
        for i in range(n):
            t = i / fps
            tp = p0 + v * t
            att = (3.0 * math.sin(0.7 * t), 2.0 * math.sin(t), 1.0 * math.sin(0.5 * t))
            ham = tp + rng.normal(0.0, 300.0, 3)     # bozuk GPS (truth varken kullanilmaz)
            satir_kuyruk = [dpos[0], dpos[1], dpos[2], att[0], att[1], att[2],
                            tp[0], tp[1], tp[2], ham[0], ham[1], ham[2], 1, ""]
            if i % 7 == 3:                           # arada tespitsiz kare
                w.writerow([t, W, H, "", "", "", "", ""] + satir_kuyruk)
                continue
            pk = km.dunya_to_kamera(tp, dpos, *att)  # zincir ortak; test FOKAL'i izole eder
            if pk[2] <= 0:
                continue
            u = W / 2.0 + fx_g * pk[0] / pk[2] + rng.normal(0, 0.7)
            vv = H / 2.0 + fx_g * pk[1] / pk[2] + rng.normal(0, 0.7)
            vh = np.array([v[0], v[1], 0.0])
            s = np.array([-vh[1], vh[0], 0.0]) / np.linalg.norm(vh)
            los = (tp - dpos) / np.linalg.norm(tp - dpos)
            proj = math.sqrt(max(0.0, 1.0 - float(np.dot(s, los)) ** 2))
            wpx = fx_g * (ks.TALON_KANAT_CM * proj) / pk[2] * rng.normal(1.0, 0.02)
            conf = 0.85 if i % 11 else 0.20          # arada dusuk-conf kare (kapi testi)
            w.writerow([t, W, H, u, vv, wpx, wpx * 0.45, conf] + satir_kuyruk)
    return yol


def test_dogru_hfov_gecer():
    yol = os.path.join(tempfile.gettempdir(), "k_sanity_sentetik_ok.csv")
    sentetik_csv(km.HFOV_DEG, yol)
    r = ks.analiz(yol)
    os.remove(yol)
    assert r and not r["yetersiz"], r
    assert r["n"] >= 50, r["n"]                      # kapilar asiri agresif degil
    assert r["gecti"] is True, r
    assert abs(r["sapma"]) < 0.03, r["sapma"]        # ~%0 sapma
    assert r["off_med_px"] is not None and r["off_med_px"] < 3.0, r["off_med_px"]


def test_yanlis_hfov_yakalanir():
    yol = os.path.join(tempfile.gettempdir(), "k_sanity_sentetik_bozuk.csv")
    sentetik_csv(100.0, yol)                         # "gercek" FOV 100 olsaydi
    r = ks.analiz(yol)
    os.remove(yol)
    assert r and not r["yetersiz"], r
    assert r["gecti"] is False, r                    # arac yanlis HFOV'u YAKALAR
    assert r["sapma"] > 0.30, r["sapma"]             # fx_gercek >> fx_varsayim


if __name__ == "__main__":
    test_dogru_hfov_gecer()
    print("OK  test_dogru_hfov_gecer")
    test_yanlis_hfov_yakalanir()
    print("OK  test_yanlis_hfov_yakalanir")
    print("TUM TESTLER GECTI (2)")

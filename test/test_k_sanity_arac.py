# -*- coding: utf-8 -*-
"""
FAZ 0: arac/k_sanity_olcum.py TRUTH'SUZ analiz yolunun sentetik dogrulamasi
(sim GEREKMEZ).  Calistirma:  python test/test_k_sanity_arac.py

Sentetik uretici GERCEK v0.0.5 kosullarini taklit eder:
  hedef GPS 5 Hz + GECIKME (0.7 s) + SABIT OFFSET + gurultu (80 cm) +
  %2 spike (+25 m) + 2 sn dropout; kareler arasi paket tekrarli (rate-limit).
Rota: yaklasan bacak + uzaklasan bacak (iki grup da dolsun).

  A) gercek HFOV = 125 (varsayimla AYNI):
     - gecikme grup sapmalarini ZIT yonde sisirir (r_yak > r_uzk, fark buyuk)
     - grup ORTALAMASI gecikmeyi iptal eder -> GECTI (kalan kucuk sapma = offset)
     - regresyon A (olcek) offset'ten ARINDIRILMIS ~1.00 cikar; B/A offseti bulur
     - dropout'a tasan pencereler medyan_yok ile elenir
  B) gercek HFOV = 100 (varsayim YANLIS): KALDI, sapma >> %10 (arac yakalar)
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

DRONE = np.array([0.0, 0.0, 5000.0])
GECIKME_S = 0.7
OFSET = np.array([250.0, -150.0, 80.0])             # cm; sabit GPS kaymasi
GPS_STD = 80.0                                      # cm; paket basi gurultu
V_CM = 1000.0                                       # hedef hizi (10 m/s)
DONUS_T = 11.0                                      # yaklasan->uzaklasan donus ani


def _hedef_gercek(t):
    """Duz yaklasan (x:14000->3000) + duz uzaklasan bacak; y,z sabit."""
    if t <= DONUS_T:
        x = 14000.0 - V_CM * t
    else:
        x = 3000.0 + V_CM * (t - DONUS_T)
    return np.array([x, 300.0, 7565.0])


def _hedef_hiz(t):
    return np.array([-V_CM if t <= DONUS_T else +V_CM, 0.0, 0.0])


def sentetik_csv(hfov_gercek_deg, yol, sure_s=26.0, fps=20.0):
    rng = np.random.default_rng(42)
    fx_g = 960.0 / (2.0 * math.tan(math.radians(hfov_gercek_deg) / 2.0))
    W, H = 960, 540

    # --- 5 Hz GPS paketleri: gecikmeli + offset + gurultu + spike; 22-24 sn dropout
    paket_t, paket_p = [], []
    for k in range(int(sure_s / 0.2) + 1):
        tk = k * 0.2
        if 22.0 <= tk < 24.0:
            continue                                 # dropout: yeni paket YOK
        p = _hedef_gercek(tk - GECIKME_S) + OFSET + rng.normal(0.0, GPS_STD, 3)
        if rng.random() < 0.02:
            p = p + np.array([2500.0, 0.0, 0.0])     # ani sicrama (spike)
        paket_t.append(tk)
        paket_p.append(p)
    paket_t = np.array(paket_t)

    n = int(sure_s * fps)
    with open(yol, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(ks.CSV_KOLON)
        for i in range(n):
            t = i / fps
            j = int(np.searchsorted(paket_t, t, side="right")) - 1
            ham = paket_p[max(j, 0)]                 # rate-limit: son paketi tekrarla
            att = (3.0 * math.sin(0.7 * t), 2.0 * math.sin(t), 1.0 * math.sin(0.5 * t))
            kuyruk = [DRONE[0], DRONE[1], DRONE[2], att[0], att[1], att[2],
                      ham[0], ham[1], ham[2]]
            if i % 7 == 3:                           # arada tespitsiz kare
                w.writerow([t, W, H, "", "", "", "", ""] + kuyruk)
                continue
            tp = _hedef_gercek(t)                    # render GERCEK konumdan (anlik)
            pk = km.dunya_to_kamera(tp, DRONE, *att)
            if pk[2] <= 0:
                w.writerow([t, W, H, "", "", "", "", ""] + kuyruk)
                continue
            u = W / 2.0 + fx_g * pk[0] / pk[2] + rng.normal(0, 0.7)
            vv = H / 2.0 + fx_g * pk[1] / pk[2] + rng.normal(0, 0.7)
            vh = _hedef_hiz(t)
            s = np.array([-vh[1], vh[0], 0.0]) / np.linalg.norm(vh[:2])
            los = (tp - DRONE) / np.linalg.norm(tp - DRONE)
            proj = math.sqrt(max(0.0, 1.0 - float(np.dot(s, los)) ** 2))
            wpx = fx_g * (ks.TALON_KANAT_CM * proj) / pk[2] * rng.normal(1.0, 0.02)
            conf = 0.85 if i % 11 else 0.20          # arada dusuk-conf kare (kapi testi)
            w.writerow([t, W, H, u, vv, wpx, wpx * 0.45, conf] + kuyruk)
    return yol


def test_dogru_hfov_gecer():
    yol = os.path.join(tempfile.gettempdir(), "k_sanity_sentetik_ok.csv")
    sentetik_csv(km.HFOV_DEG, yol)
    r = ks.analiz(yol)
    os.remove(yol)
    assert r and not r["yetersiz"], r
    assert r["n_yak"] >= 15 and r["n_uzk"] >= 15, (r["n_yak"], r["n_uzk"])
    # gecikme: gruplar ZIT yonde sapar (yaklasan Z buyuk gorur -> oran > uzaklasan)
    assert r["r_yak"] - r["r_uzk"] > 0.10, (r["r_yak"], r["r_uzk"])
    # grup ortalamasi gecikmeyi iptal eder; kalan kucuk pozitif sapma = radyal offset
    assert r["gecti"] is True, r
    assert 0.0 < r["sapma"] < 0.08, r["sapma"]
    # regresyon: A olcegi offset'ten AYIRIR (K dogru: A ~ 1.00); B/A offseti bulur
    assert r["reg_kosullu"], r
    assert abs(r["A_sapma"]) < 0.035, r["A_sapma"]
    assert 0.5 < r["ofset_m"] < 5.0, r["ofset_m"]
    # dropout'a tasan medyan pencereleri elendi (2 sn boslugun izi)
    assert r["ele"]["medyan_yok"] > 0, r["ele"]


def test_yanlis_hfov_yakalanir():
    yol = os.path.join(tempfile.gettempdir(), "k_sanity_sentetik_bozuk.csv")
    sentetik_csv(100.0, yol)                         # "gercek" FOV 100 olsaydi
    r = ks.analiz(yol)
    os.remove(yol)
    assert r and not r["yetersiz"], r
    assert r["gecti"] is False, r                    # arac yanlis HFOV'u YAKALAR
    assert r["sapma"] > 0.30, r["sapma"]             # fx_gercek >> fx_varsayim
    # regresyon da ayni teshisi verir: olcek (A) sapmasi buyuk, yani K sorunu
    if r["reg_kosullu"]:
        assert r["A_sapma"] > 0.30, r["A_sapma"]


if __name__ == "__main__":
    test_dogru_hfov_gecer()
    print("OK  test_dogru_hfov_gecer")
    test_yanlis_hfov_yakalanir()
    print("OK  test_yanlis_hfov_yakalanir")
    print("TUM TESTLER GECTI (2)")

# -*- coding: utf-8 -*-
"""
arac/filtre_dogrulama.py METRIK matematiginin sentetik dogrulamasi (sim GEREKMEZ).
Calistirma:  python test/test_filtre_dogrulama.py

Sentetik: donen hedef truth'u; 'ham' = truth(t-0.7)+gurultu(100cm)+%2 spike;
'filtre' = truth(t-0.3)+kucuk gurultu(30cm). Beklenen:
  - RMSE_filtre < RMSE_ham (arac kazanci dogru olcer)
  - gecikme kestirimi: ham ~0.7 s, filtre ~0.3 s (+-0.15)
  - gecikme-arindirilmis RMSE dogrudan RMSE'den kucuk
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

import filtre_dogrulama as fd                       # noqa: E402


def _truth(t):
    """Donen hedef: 300 m yaricapli cember, 20 m/s (CT-EKF'nin sevdigi durum)."""
    w = 20.0 / 300.0                                # rad/s (v/r)
    return np.array([30000.0 * math.cos(w * t), 30000.0 * math.sin(w * t),
                     8000.0 + 500.0 * math.sin(0.1 * t)])


def sentetik_csv(yol, sure_s=60.0, hz=50.0):
    rng = np.random.default_rng(7)
    n = int(sure_s * hz)
    with open(yol, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(fd.CSV_KOLON)
        for i in range(n):
            t = i / hz
            tru = _truth(t)
            ham = _truth(t - 0.7) + rng.normal(0, 100.0, 3)
            if rng.random() < 0.02:
                ham = ham + np.array([3000.0, -2000.0, 0.0])      # spike
            fil = _truth(t - 0.3) + rng.normal(0, 30.0, 3)
            w.writerow(["%.4f" % t] + ["%.1f" % x for x in ham]
                       + ["%.1f" % x for x in fil] + ["%.1f" % x for x in tru])
    return yol


def test_metrikler():
    yol = os.path.join(tempfile.gettempdir(), "filtre_dogrulama_sentetik.csv")
    sentetik_csv(yol)
    r = fd.analiz(yol)
    os.remove(yol)
    assert r is not None
    ham, fil = r["ham"], r["filtre"]
    assert fil["rmse_m"] < ham["rmse_m"], (fil["rmse_m"], ham["rmse_m"])
    assert r["kazanc_pct"] > 30, r["kazanc_pct"]
    assert abs(ham["tau_s"] - 0.7) <= 0.15, ham["tau_s"]      # gecikme kestirimi
    assert abs(fil["tau_s"] - 0.3) <= 0.15, fil["tau_s"]
    assert ham["rmse_tau_m"] < ham["rmse_m"], ham             # arindirilmis < dogrudan
    assert fil["rmse_tau_m"] < fil["rmse_m"], fil


if __name__ == "__main__":
    test_metrikler()
    print("OK  test_metrikler")
    print("TUM TESTLER GECTI (1)")

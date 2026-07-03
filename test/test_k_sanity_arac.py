# -*- coding: utf-8 -*-
"""
FAZ 0: arac/k_sanity_olcum.py TRUTH-TABANLI analiz yolunun sentetik dogrulamasi
(sim GEREKMEZ).  Calistirma:  python test/test_k_sanity_arac.py

Uretici: truth kolonlari GERCEK konum; ham GPS kolonlari (analizde kullanilmaz,
referans icin) gecikme+offset+gurultulu. Truth'a seyrek yapay glitch eklenir
(spike korumasi kapisi calissin).
  A) gercek HFOV = 125 (varsayimla AYNI)  -> GECTI, |sapma| < %2, offset kucuk
  B) gercek HFOV = 100 (varsayim YANLIS)  -> KALDI, sapma >> %5 (arac yakalar)
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


def sentetik_csv(hfov_gercek_deg, yol, sure_s=22.0, fps=20.0):
    rng = np.random.default_rng(42)
    fx_g = 960.0 / (2.0 * math.tan(math.radians(hfov_gercek_deg) / 2.0))
    W, H = 960, 540
    n = int(sure_s * fps)
    with open(yol, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(ks.CSV_KOLON)
        for i in range(n):
            t = i / fps
            tp = _hedef_gercek(t)
            tt = tp.copy()
            if i % 97 == 50:
                tt = tt + np.array([30000.0, 0.0, 0.0])   # yapay glitch (spike kapisi)
            ham = _hedef_gercek(t - 0.7) + np.array([250.0, -150.0, 80.0]) \
                + rng.normal(0.0, 80.0, 3)                # referans (analizde kullanilmaz)
            att = (3.0 * math.sin(0.7 * t), 2.0 * math.sin(t), 1.0 * math.sin(0.5 * t))
            kuyruk = [DRONE[0], DRONE[1], DRONE[2], att[0], att[1], att[2],
                      tt[0], tt[1], tt[2], ham[0], ham[1], ham[2], 1, 0.0]
            if i % 7 == 3:                                # arada tespitsiz kare
                w.writerow([t, W, H, "", "", "", "", ""] + kuyruk)
                continue
            pk = km.dunya_to_kamera(tp, DRONE, *att)      # render GERCEK konumdan
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
            conf = 0.85 if i % 11 else 0.20               # arada dusuk-conf (kapi testi)
            w.writerow([t, W, H, u, vv, wpx, wpx * 0.45, conf] + kuyruk)
    return yol


def test_siluet_tespit():
    """Sentetik gok + koyu siluet: genislik ~dogru; gunes/zemin ROI'leri reddedilir."""
    import cv2
    rng = np.random.default_rng(3)
    fr = np.clip(170.0 + rng.normal(0, 3.0, (1080, 1920)), 0, 255).astype(np.uint8)
    cv2.ellipse(fr, (900, 500), (30, 8), 0, 0, 360, 60, -1)      # 60 px kanat
    fr = cv2.GaussianBlur(fr, (3, 3), 0)
    fr3 = cv2.cvtColor(fr, cv2.COLOR_GRAY2BGR)
    det, neden = ks._siluet_tespit(fr3, (905.0, 505.0), cv2)
    assert det is not None and neden == "ok"
    assert abs(det["w"] - 60.0) <= 6.0, det["w"]                 # <=%10 kenar hatasi
    assert abs(det["cx"] - 900) < 8 and abs(det["cy"] - 500) < 8
    # PARLAK hedef (acik boyali govde) de yakalanmali (kutupsuz sapma maskesi)
    par = np.clip(170.0 + rng.normal(0, 3.0, (1080, 1920)), 0, 255).astype(np.uint8)
    cv2.ellipse(par, (900, 500), (30, 8), 0, 0, 360, 235, -1)
    par3 = cv2.cvtColor(cv2.GaussianBlur(par, (3, 3), 0), cv2.COLOR_GRAY2BGR)
    det2, neden2 = ks._siluet_tespit(par3, (905.0, 505.0), cv2)
    assert det2 is not None and abs(det2["w"] - 60.0) <= 6.0, (det2, neden2)
    # gunes parlamasi: ROI'de doygun blob -> red
    gun = fr3.copy()
    cv2.circle(gun, (900, 500), 45, (255, 255, 255), -1)
    assert ks._siluet_tespit(gun, (905.0, 505.0), cv2)[0] is None
    # zemin (koyu/dokulu) ROI -> red
    zemin = np.clip(80.0 + rng.normal(0, 20.0, (1080, 1920)), 0, 255).astype(np.uint8)
    zemin3 = cv2.cvtColor(zemin, cv2.COLOR_GRAY2BGR)
    assert ks._siluet_tespit(zemin3, (905.0, 505.0), cv2)[0] is None
    # kadraj kenari -> red (ROI tasar)
    assert ks._siluet_tespit(fr3, (30.0, 500.0), cv2)[0] is None


def test_dogru_hfov_gecer():
    yol = os.path.join(tempfile.gettempdir(), "k_sanity_sentetik_ok.csv")
    sentetik_csv(km.HFOV_DEG, yol)
    r = ks.analiz(yol)
    os.remove(yol)
    assert r and not r["yetersiz"], r
    assert r["n"] >= ks.N_MIN, r["n"]
    assert r["gecti"] is True, r
    assert abs(r["sapma"]) < 0.02, r["sapma"]        # truth'la ~%0 sapma beklenir
    assert r.get("off_med_px") is not None and r["off_med_px"] < 3.0, r
    assert r["ele"]["spike"] > 0, r["ele"]           # glitch kareleri elendi


def test_yanlis_hfov_yakalanir():
    yol = os.path.join(tempfile.gettempdir(), "k_sanity_sentetik_bozuk.csv")
    sentetik_csv(100.0, yol)                         # "gercek" FOV 100 olsaydi
    r = ks.analiz(yol)
    os.remove(yol)
    assert r and not r["yetersiz"], r
    assert r["gecti"] is False, r                    # arac yanlis HFOV'u YAKALAR
    assert r["sapma"] > 0.30, r["sapma"]             # fx_gercek >> fx_varsayim


if __name__ == "__main__":
    test_siluet_tespit()
    print("OK  test_siluet_tespit")
    test_dogru_hfov_gecer()
    print("OK  test_dogru_hfov_gecer")
    test_yanlis_hfov_yakalanir()
    print("OK  test_yanlis_hfov_yakalanir")
    print("TUM TESTLER GECTI (3)")

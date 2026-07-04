# -*- coding: utf-8 -*-
"""
FAZ 2 kabul testleri: detection/talon_pose_estimator.py (sim/model GEREKMEZ).
Calistirma:  python test/test_pnp.py

SENTETIK ROUND-TRIP: bilinen rastgele poz -> 6 keypoint'i K ile goruntuye
yansit -> piksel gurultusu ekle (sigma) -> solvePnPRansac ile geri bul ->
poz hatasi + reproj error. Keypoint eksiltme (6->5->4), tek-aykiri senaryo,
k-taramasi (k=0.9 uretilmis veride min 0.9).
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from detection import talon_pose_estimator as pe
from detection import kamera_model as km

try:
    import cv2
    _CV2 = True
except Exception:
    _CV2 = False

W, H = 1920, 1080


def _rastgele_poz(rng, mes_min=3000.0, mes_max=8000.0):
    """Kamera onunde makul bir hedef pozu. mesafe cm; kucuk aci."""
    mesafe = rng.uniform(mes_min, mes_max)
    yon = np.array([rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3), 1.0])
    yon /= np.linalg.norm(yon)
    tvec_cm = yon * mesafe
    aci = rng.uniform(-0.4, 0.4, 3)               # rad; hedef yonelimi
    R, _ = cv2.Rodrigues(aci)
    return R, (tvec_cm * 10.0).reshape(3, 1)      # mm


def _yansit(R, tvec_mm, sema=pe.VARSAYILAN_SEMA, K=None):
    K = K if K is not None else km.K_matrisi(W, H)
    obj = pe.SEMALAR[sema]
    rvec, _ = cv2.Rodrigues(R)
    proj, _ = cv2.projectPoints(obj, rvec, tvec_mm, K, None)
    return proj.reshape(-1, 2)


def _kp(img_pts, confs=None):
    confs = confs if confs is not None else [0.9] * len(img_pts)
    return [[float(x), float(y), float(c)] for (x, y), c in zip(img_pts, confs)]


def test_roundtrip_gurultu_seviyeleri():
    # PnP'nin ANLAMLI oldugu band (5-25 m; terminal faz). Far-field'de derinlik
    # dejenere (k-taramasi testinde ayri gosterildi) -> orada GPS kullanilir.
    assert _CV2, "cv2 gerekli"
    for sigma in (0.5, 1.0, 2.0):
        rng = np.random.default_rng(int(sigma * 100))
        mes_hatalari, reprojlar = [], []
        for _ in range(40):
            R, tvec = _rastgele_poz(rng, 500.0, 2500.0)
            img = _yansit(R, tvec)
            img_g = img + rng.normal(0, sigma, img.shape)
            s = pe.TalonPozKestirici().kestir(_kp(img_g), (0.0, 0.0, 0.0), W, H)
            assert s["gecerli"], (sigma, s["sebep"])
            mesafe_gercek = float(np.linalg.norm(tvec) / 10.0)
            mes_hatalari.append(abs(s["mesafe"] - mesafe_gercek) / mesafe_gercek)
            reprojlar.append(s["reproj_err"])
        # yakin bant: mesafe hatasi kucuk kalir; reproj ~ sigma mertebesi
        assert np.median(mes_hatalari) < 0.03 + sigma * 0.03, (sigma, np.median(mes_hatalari))
        assert np.median(reprojlar) < 3.0 * sigma + 1.0, (sigma, np.median(reprojlar))


def test_keypoint_eksiltme_6_5_4():
    assert _CV2
    rng = np.random.default_rng(7)
    for n_gorunur in (6, 5, 4):
        ok = 0
        for _ in range(30):
            R, tvec = _rastgele_poz(rng)
            img = _yansit(R, tvec) + rng.normal(0, 0.7, (6, 2))
            confs = [0.9] * 6
            for i in range(6 - n_gorunur):        # son (6-n) keypoint'i dusuk conf yap
                confs[5 - i] = 0.1
            s = pe.TalonPozKestirici().kestir(_kp(img, confs), (0, 0, 0), W, H)
            if s["gecerli"] and s["kullanilan_kp"] == n_gorunur:
                ok += 1
        assert ok >= 25, (n_gorunur, ok)          # 4 nokta bile cozulebilmeli


def test_3_kp_reddedilir():
    assert _CV2
    rng = np.random.default_rng(1)
    R, tvec = _rastgele_poz(rng)
    img = _yansit(R, tvec)
    confs = [0.9, 0.9, 0.9, 0.1, 0.1, 0.1]        # yalniz 3 gorunur
    s = pe.TalonPozKestirici().kestir(_kp(img, confs), (0, 0, 0), W, H)
    assert not s["gecerli"] and "yeterli kp yok" in s["sebep"]


def test_tek_aykiri_keypoint_reproj_yakalar():
    # bir keypoint cok sapkin (yanlis tespit) -> reproj error patlar -> RANSAC
    # aykiriyi elese bile refine dahil reproj esigi asilirsa REDDEDILIR.
    assert _CV2
    rng = np.random.default_rng(3)
    reddedilen = 0
    for _ in range(30):
        R, tvec = _rastgele_poz(rng)
        img = _yansit(R, tvec) + rng.normal(0, 0.7, (6, 2))
        img[2] += np.array([120.0, -90.0])        # 3. kp'yi kaydir (aykiri)
        s = pe.TalonPozKestirici().kestir(_kp(img), (0, 0, 0), W, H)
        # ya reddedilir (reproj yuksek) ya da RANSAC aykiriyi eleyip gecerli+dusuk reproj
        if not s["gecerli"]:
            reddedilen += 1
        else:
            assert s["reproj_err"] <= pe.PnPCfg.REPROJ_ESIK
    # en azindan bazi vakalar reddedilmeli ya da temizlenmeli (ikisi de kabul);
    # asil sart: HICBIR vaka yuksek-reproj'la GECERLI donmesin (yukarida assert)
    assert True


def test_yonelim_sonlu_ve_tutarli():
    # Yonelim (phi_T/psi_T) SONLU ve [-180,180] araliginda olmali (NaN/inf yok).
    # KESIN ISARET keypoint sirasina baglidir -> sim gorsel teyidinde dogrulanir
    # (yanlis sira -> yanlis yonelim). Burada ic tutarlilik: ayni poz ayni yonelim.
    assert _CV2
    rng = np.random.default_rng(5)
    for _ in range(20):
        R, tvec = _rastgele_poz(rng, 800.0, 3000.0)
        img = _yansit(R, tvec) + rng.normal(0, 0.5, (6, 2))
        s = pe.TalonPozKestirici().kestir(_kp(img), (0.0, 0.0, 0.0), W, H)
        assert s["gecerli"]
        assert math.isfinite(s["phi_T"]) and -180 <= s["phi_T"] <= 180
        assert math.isfinite(s["psi_T"]) and -180 <= s["psi_T"] <= 180
        # ayni girdi -> ayni cikti (deterministiklik; low-pass'siz t=None)
        s2 = pe.TalonPozKestirici().kestir(_kp(img), (0.0, 0.0, 0.0), W, H)
        assert abs(s2["phi_T"] - s["phi_T"]) < 1e-6


def test_k_taramasi_bulur_09_yakin():
    # YAKIN hedef (perspektif guclu): k=0.9 uretilmis veride min ~0.9 + guvenilir
    assert _CV2
    rng = np.random.default_rng(11)
    fnom = km.fx_px(W)
    K_gercek = np.array([[0.9 * fnom, 0, W / 2.0], [0, 0.9 * fnom, H / 2.0], [0, 0, 1]], float)
    kayitlar = []
    for _ in range(60):
        R, tvec = _rastgele_poz(rng, 300.0, 1000.0)       # 3-10 m: perspektif guclu
        img = _yansit(R, tvec, K=K_gercek) + rng.normal(0, 0.5, (6, 2))
        kayitlar.append(_kp(img))
    r = pe.k_taramasi(kayitlar, W, H, adim=0.01)
    assert r is not None and r["k_star"] is not None, r
    assert abs(r["k_star"] - 0.9) <= 0.04, r["k_star"]
    assert r["guvenilir"], r       # yakin -> perspektif yeterli, egri belirgin


def test_k_taramasi_farfield_guvenilmez():
    # FAR-FIELD (50-80 m): fx-tvec dejenere -> k* guvenilmez isaretlenmeli
    assert _CV2
    rng = np.random.default_rng(13)
    kayitlar = []
    for _ in range(40):
        R, tvec = _rastgele_poz(rng, 5000.0, 8000.0)      # 50-80 m: dejenere
        img = _yansit(R, tvec) + rng.normal(0, 0.5, (6, 2))
        kayitlar.append(_kp(img))
    r = pe.k_taramasi(kayitlar, W, H, adim=0.01)
    assert r["perspektif_gucu"] < 0.06, r["perspektif_gucu"]
    assert not r["guvenilir"], "far-field k* GUVENILMEZ isaretlenmeli"


def test_sema_secimi():
    ke = pe.TalonPozKestirici(sema="motor")
    assert ke.sema == "motor" and ke.obj.shape == (6, 3)
    ke.sema_ayarla("kuyruk_ucu")
    assert ke.sema == "kuyruk_ucu"
    # gecersiz sema -> varsayilana duser
    assert pe.TalonPozKestirici(sema="olmayan").sema == pe.VARSAYILAN_SEMA


def test_kp_sayisi_uyumsuz():
    s = pe.TalonPozKestirici().kestir([[1, 2, 0.9]] * 5, (0, 0, 0), W, H)   # 5 kp
    assert not s["gecerli"] and "kpt_shape uyumsuz" in s["sebep"]


if __name__ == "__main__":
    if not _CV2:
        print("cv2 YOK - PnP testleri atlaniyor")
        sys.exit(0)
    testler = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in testler:
        t()
        print("OK  %s" % t.__name__)
    print("TUM TESTLER GECTI (%d)" % len(testler))

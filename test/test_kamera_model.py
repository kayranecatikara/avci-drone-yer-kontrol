# -*- coding: utf-8 -*-
"""
FAZ 0 kabul testleri: detection/kamera_model.py
Calistirma (pytest GEREKMEZ):  python test/test_kamera_model.py
Her test duz assert; hepsi gecince "TUM TESTLER GECTI" basar, aksi halde
ilk kirilan assert traceback ile durur (exit code != 0).
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from detection import kamera_model as km


def yakin(a, b, tol=1e-9):
    return abs(a - b) <= tol


def test_fx_orani():
    # f_x = W/(2*tan(62.5)) ~= 0.2603*W; 1920'de ~499.8 px (prompt: ~500 px)
    assert yakin(km.fx_px(1920) / 1920.0, 0.26032, 1e-4), km.fx_px(1920)
    assert 499.0 < km.fx_px(1920) < 500.5, km.fx_px(1920)
    assert yakin(km.fx_px(960), km.fx_px(1920) / 2.0, 1e-9)   # cozunurlukle dogrusal


def test_K_parametrik():
    K = km.K_matrisi(960, 540)
    assert yakin(K[0, 0], km.fx_px(960), 1e-9)
    assert yakin(K[1, 1], K[0, 0], 1e-12)          # kare piksel: f_y = f_x
    assert yakin(K[0, 2], 480.0) and yakin(K[1, 2], 270.0)
    assert K.shape == (3, 3) and yakin(K[2, 2], 1.0)
    assert np.all(km.dist_katsayilari() == 0.0)    # distorsiyon = 0 varsayimi


def test_turetilen_fovlar():
    # 16:9'da VFOV ~ 94.4, DFOV ~ 131.2 (prompt'taki bilgi degerleri)
    v = math.degrees(km.vfov_rad(1920, 1080))
    d = math.degrees(km.dfov_rad(1920, 1080))
    assert abs(v - 94.4) < 0.1, v
    assert abs(d - 131.2) < 0.1, d


def test_ey_ref():
    # tan(25)/tan(VFOV/2); 16:9'da ~0.4315 (mevcut Cfg.VIS_EY_REF=0.43 ile tutarli)
    r = km.ey_ref(16.0, 9.0)
    assert abs(r - 0.4315) < 0.002, r
    assert yakin(km.ey_ref(1920, 1080), r, 1e-12)  # yalnizca ORANA bagli


def test_mount_ortogonal():
    R = km.R_mount_kam2gov()
    assert np.allclose(R @ R.T, np.eye(3), atol=1e-12)
    assert abs(np.linalg.det(R) - 1.0) < 1e-12                   # sag-el (yansima yok)
    assert np.allclose(km.R_mount_gov2kam(), R.T, atol=1e-15)
    # optik eksen govdede burnun 25 ustu; goruntu-sagi govde sagi (-y)
    t = math.radians(km.TILT_DEG)
    assert np.allclose(R[:, 2], [math.cos(t), 0.0, math.sin(t)], atol=1e-12)
    assert np.allclose(R[:, 0], [0.0, -1.0, 0.0], atol=1e-12)


def test_attitude_ortogonal_ve_yaw():
    R = km.R_govde_to_dunya(17.0, -8.0, 133.0)
    assert np.allclose(R @ R.T, np.eye(3), atol=1e-12)
    assert abs(np.linalg.det(R) - 1.0) < 1e-12
    # yaw CCW: level dronda burun (1,0,0) -> dunyada (cos psi, sin psi, 0)
    ps = math.radians(40.0)
    R = km.R_govde_to_dunya(0.0, 0.0, 40.0)
    assert np.allclose(R @ [1, 0, 0], [math.cos(ps), math.sin(ps), 0.0], atol=1e-12)
    # pitch burun-yukari: +10 pitch'te burun z>0
    R = km.R_govde_to_dunya(0.0, 10.0, 0.0)
    assert (R @ [1, 0, 0])[2] > 0.1
    # roll saga: +20 roll'de govde SOL kanadi (+y) yukari kalkar (z>0)
    R = km.R_govde_to_dunya(0.0, 0.0, 0.0)
    R20 = km.R_govde_to_dunya(20.0, 0.0, 0.0)
    assert (R20 @ [0, 1, 0])[2] > 0.1 and np.allclose(R, np.eye(3), atol=1e-12)


def test_zincir_tilt_merkez():
    # Level drone (0,0,0 att), yaw=0: dunya noktasi 25 derece ELEVASYONDA ileri
    # -> tam goruntu MERKEZINE dusmeli (optik eksen = burnun 25 ustu).
    W, H = 960, 540
    K = km.K_matrisi(W, H)
    t = math.radians(km.TILT_DEG)
    D = 5000.0
    p = np.array([D * math.cos(t), 0.0, D * math.sin(t)])
    pk = km.dunya_to_kamera(p, [0, 0, 0], 0.0, 0.0, 0.0)
    assert pk[2] > 0 and abs(pk[0]) < 1e-6 and abs(pk[1]) < 1e-6, pk
    u, v = km.izdusur(pk, K)
    assert yakin(u, W / 2.0, 1e-6) and yakin(v, H / 2.0, 1e-6), (u, v)


def test_zincir_yaw_ve_pitch_merkez():
    W, H = 960, 540
    K = km.K_matrisi(W, H)
    t = math.radians(km.TILT_DEG)
    D = 3000.0
    # yaw=90 (burun +y): 25 elevasyonda +y yonundeki nokta merkezde
    p = np.array([0.0, D * math.cos(t), D * math.sin(t)])
    u, v = km.izdusur(km.dunya_to_kamera(p, [0, 0, 0], 0.0, 0.0, 90.0), K)
    assert yakin(u, W / 2.0, 1e-6) and yakin(v, H / 2.0, 1e-6), (u, v)
    # pitch=-25 (burun 25 asagi -> kamera ufka bakar): ufuktaki ileri nokta merkezde
    p = np.array([D, 0.0, 0.0])
    u, v = km.izdusur(km.dunya_to_kamera(p, [0, 0, 0], 0.0, -km.TILT_DEG, 0.0), K)
    assert yakin(u, W / 2.0, 1e-6) and yakin(v, H / 2.0, 1e-6), (u, v)


def test_goruntu_yonleri():
    # Level drone, yaw=0. Optik eksene gore SAGDAKI nokta (dunya -y) -> u > W/2;
    # daha YUKARIDAKI nokta -> v < H/2 (goruntu y'si asagi dogru).
    W, H = 960, 540
    K = km.K_matrisi(W, H)
    t = math.radians(km.TILT_DEG)
    D = 5000.0
    merkez = np.array([D * math.cos(t), 0.0, D * math.sin(t)])
    u_sag, _ = km.izdusur(km.dunya_to_kamera(merkez + [0, -300.0, 0], [0, 0, 0], 0, 0, 0), K)
    _, v_ust = km.izdusur(km.dunya_to_kamera(merkez + [0, 0, 300.0], [0, 0, 0], 0, 0, 0), K)
    assert u_sag > W / 2.0 + 5, u_sag
    assert v_ust < H / 2.0 - 5, v_ust


def test_ey_ref_zincirle_tutarli():
    # ey_ref TANIMI: ayni irtifada (ufukta) ileri nokta, level dronda
    # ey = (v - H/2)/(H/2) = ey_ref olmali. (IBVS tilt telafisinin kaynagi.)
    W, H = 1280, 720
    K = km.K_matrisi(W, H)
    p = np.array([8000.0, 0.0, 0.0])
    u, v = km.izdusur(km.dunya_to_kamera(p, [0, 0, 0], 0.0, 0.0, 0.0), K)
    ey = (v - H / 2.0) / (H / 2.0)
    assert abs(ey - km.ey_ref(W, H)) < 1e-9, (ey, km.ey_ref(W, H))
    assert yakin(u, W / 2.0, 1e-6)


def test_piksel_yon_gidis_donus():
    W, H = 960, 540
    K = km.K_matrisi(W, H)
    p = np.array([123.0, -45.0, 678.0])
    uv = km.izdusur(p, K)
    yon = km.piksel_yon(uv[0], uv[1], K)
    assert np.allclose(yon, p / np.linalg.norm(p), atol=1e-12)
    # kamera->dunya->kamera tutarliligi (rastgele attitude)
    v_dunya = km.kamera_to_dunya_yon(yon, 12.0, -7.0, 63.0)
    geri = km.R_dunya_to_kamera(12.0, -7.0, 63.0) @ v_dunya
    assert np.allclose(geri, yon, atol=1e-12)
    # arkadaki nokta izdusurulemez
    assert km.izdusur([0.0, 0.0, -10.0], K) is None


if __name__ == "__main__":
    testler = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in testler:
        t()
        print("OK  %s" % t.__name__)
    print("TUM TESTLER GECTI (%d)" % len(testler))

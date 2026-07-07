# -*- coding: utf-8 -*-
"""
DIKEY = HEDEF ALTINDA SABIT MESAFE — YALNIZ GORSEL VERI (2026-07-07 v5).

YARISMA KURALI: gorsel temastan sonra hareket komutu YALNIZ gorsel veriden. Dikey ayrim
GPS/J DEGIL, tamamen GORSEL: dh = R (pinhole, bbox boyutundan) * u_hat[2] (LOS-z, kameradan).
Arac hedefin irtifasindan VIS_DH_TARGET kadar ALTTA kalir; kapandikca ayrim SABIT (kadraj-
pozisyonu kontrolunun tersine kuculmez) -> hedef kadrajda YUKARI kayar (alttan yaklasma).

_det_dunya'da bbox pinhole R'yi TAM verir (w_px=FX*SPAN/R) -> dh = R*u_hat[2] = gercek dikey
ayrim (zt - drone_z). Yani dh'yi geometriden (drone_z, zt) kurariz; target_alt (J) YOK.

thr = -vz_des/VZ_MAX -> ALCAL (vz<0) = thr BUYUK, TIRMAN (vz>0) = thr KUCUK.

Calistirma:  python tests/test_lookup_geometri.py     (pytest de calisir)
"""
import os
import sys
import math
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pose import geometri
from guidance.png_gorsel import AvciPNGGuduum
from guidance.ana_kontrol import Cfg

TILT = 25.0
W, H = 1920.0, 1080.0
FX = geometri.fx_from_hfov(W)


def _det_dunya(p_target, drone_pos, t=0.0):
    cam, Rc = geometri.kamera_pozu(drone_pos, (0.0, 0.0, 0.0), tilt_deg=TILT)
    uv = geometri.projekte(np.asarray(p_target, float), cam, Rc, FX, W, H)
    assert uv is not None, "hedef kadraj disinda (test kurulumu)"
    R = float(np.linalg.norm(np.asarray(p_target, float) - cam))
    return {"cx": uv[0], "cy": uv[1], "w": FX * Cfg.VIS_SPAN_CM / R, "h": FX * 110.0 / R,
            "conf": 0.9, "cls": 0, "W": W, "H": H, "t": t}


def _thr(vurus_izin, drone_z, zt=1500.0, D=2000.0):
    """Tek kare; throttle + durum. GORSEL dh = R*u_hat[2] ~ (zt - drone_z).
    drone D onde, zt hedef irtifasi, drone_z arac irtifasi -> dikey ayrim zt-drone_z."""
    png = AvciPNGGuduum()
    drone = np.array([0.0, 0.0, float(drone_z)])
    komut = png.hesapla(_det_dunya([D, 0.0, float(zt)], drone), drone, (0.0, 0.0, 0.0),
                        np.zeros(2), Cfg, vurus_izin=vurus_izin)
    return komut[0], png.durum()


# ---------------------------------------------------------------------------
#  A) dh GORSEL'den turer (target_alt/J YOK) + isaret
# ---------------------------------------------------------------------------
def test_dh_gorsel_dogru():
    # drone 1000, hedef 1500 -> dikey ayrim +500 cm = +5 m (yalnizca goruntuden)
    _, d = _thr(True, drone_z=1000.0, zt=1500.0)
    assert abs(d["dh_below_m"] - 5.0) < 0.15, "gorsel dh yanlis: %.2f" % d["dh_below_m"]


def test_ustte_dh_negatif():
    # arac hedefin USTUNDE (1600 > 1500) -> dh negatif
    _, d = _thr(True, drone_z=1600.0, zt=1500.0)
    assert d["dh_below_m"] < 0, "ustteyken dh negatif olmali: %.2f" % d["dh_below_m"]


# ---------------------------------------------------------------------------
#  B) az-altta -> ALCAL, cok-altta -> TIRMAN (thr karsilastirma)
# ---------------------------------------------------------------------------
def test_alcal_vs_tirman():
    # dh=+200 (<hedef 400) -> ALCAL ; dh=+700 (>400) -> TIRMAN -> thr(az) > thr(cok)
    thr_az, d_az = _thr(False, drone_z=1300.0, zt=1500.0)   # dh=+200
    thr_cok, _ = _thr(False, drone_z=1000.0, zt=1700.0)     # dh=+700
    assert thr_az > thr_cok + 0.05, "az-altta ALCAL > cok-altta TIRMAN: az=%.3f cok=%.3f" % (thr_az, thr_cok)
    assert d_az["lookup_ok"] is False, "dh=+200 hedeften uzak -> lookup_ok False"


def test_ustte_guclu_alcal():
    # arac USTTE (dh=-100) -> guclu ALCAL ; cok-altta (dh=+700) -> TIRMAN
    thr_ust, _ = _thr(False, drone_z=1600.0, zt=1500.0)     # dh=-100
    thr_cok, _ = _thr(False, drone_z=1000.0, zt=1700.0)     # dh=+700
    assert thr_ust > thr_cok + 0.1, "ustteyken guclu ALCAL olmali: ust=%.3f cok=%.3f" % (thr_ust, thr_cok)


# ---------------------------------------------------------------------------
#  C) TERMINAL kapali + yere cakilma
# ---------------------------------------------------------------------------
def test_terminal_ayrim_kapali():
    # TERMINAL'de ayrim kontrolu YOK -> az/cok altta thr ~ ayni (target'a bagimsiz)
    thr_az, _ = _thr(True, drone_z=1300.0, zt=1500.0)
    thr_cok, _ = _thr(True, drone_z=1000.0, zt=1700.0)
    assert abs(thr_az - thr_cok) < 0.15, "TERMINAL'de ayrim kontrolu KAPALI: %.3f vs %.3f" % (thr_az, thr_cok)


def test_yere_cakilma_korumasi():
    # tabanda az-altta (alcalirdi) BLOKLU -> descend farki tabanda KUCUK, yuksekte BUYUK
    taban = float(Cfg.LOOKUP_MIN_ALT_CM) - 50.0
    az_t, _ = _thr(False, drone_z=taban, zt=taban + 200.0)      # dh=+200 (tabanda, alcalma bloklu)
    notr_t, _ = _thr(False, drone_z=taban, zt=taban + 400.0)    # dh=+400 (notr)
    fark_taban = az_t - notr_t
    az_y, _ = _thr(False, drone_z=3000.0, zt=3200.0)            # dh=+200 (yuksekte, alcalma serbest)
    notr_y, _ = _thr(False, drone_z=3000.0, zt=3400.0)          # dh=+400
    fark_yuksek = az_y - notr_y
    assert fark_yuksek > fark_taban + 0.03, (
        "tabanda ALCALMA bloklanmali (fark kucuk): taban=%.3f yuksek=%.3f" % (fark_taban, fark_yuksek))


# ---------------------------------------------------------------------------
#  D) Kapali-dongu: kapanirken dh SABIT + hedef kadrajda YUKARI (alttan yaklasma)
# ---------------------------------------------------------------------------
def test_kapali_dongu_alttan_yaklasma():
    png = AvciPNGGuduum()
    VZMAX = float(Cfg.VZ_MAX)
    dh_t = float(Cfg.VIS_DH_TARGET)
    zt = 1500.0
    drone = np.array([0.0, 0.0, zt - dh_t])           # tam VIS_DH_TARGET altta basla
    D = 4000.0
    dt = 0.02
    dh_izi = []; ey_izi = []
    son_det = None; son_det_t = -1.0
    for k in range(500):                              # 10 s
        t = k * dt
        D = max(D - 400.0 * dt, 300.0)                # yatay kapan
        p_t = [D, 0.0, zt]
        if t - son_det_t >= 0.05 - 1e-9:
            son_det = _det_dunya(p_t, drone, t=t); son_det_t = t
        d_now = _det_dunya(p_t, drone, t=t)
        komut = png.hesapla(d_now, drone, (0.0, 0.0, 0.0), np.zeros(2), Cfg, vurus_izin=False)
        drone = drone + np.array([0.0, 0.0, (-komut[0] * VZMAX) * dt])
        dh_izi.append(zt - drone[2])
        ey_izi.append((d_now["cy"] - H / 2.0) / (H / 2.0))
    dh_son = sum(dh_izi[-50:]) / 50.0
    print("kapali-dongu (GORSEL): dh_son=%.0f cm (hedef %.0f) | ey %.2f->%.2f" % (
        dh_son, dh_t, ey_izi[0], ey_izi[-1]))
    assert abs(dh_son - dh_t) < 120.0, "dikey ayrim hedefte kalmadi (dh_son=%.0f)" % dh_son
    assert ey_izi[-1] < ey_izi[0] - 0.05, "kapanirken hedef kadrajda YUKARI kaymali (alttan yaklasma)"


if __name__ == "__main__":
    fns = [(n, f) for n, f in sorted(globals().items())
           if n.startswith("test_") and callable(f)]
    gecen = 0
    for n, f in fns:
        try:
            f(); print("OK  " + n); gecen += 1
        except AssertionError as e:
            print("FAIL " + n + " -> " + str(e))
        except Exception as e:
            print("ERR  " + n + " -> " + repr(e))
    print("\n%d/%d test gecti." % (gecen, len(fns)))
    sys.exit(0 if gecen == len(fns) else 1)

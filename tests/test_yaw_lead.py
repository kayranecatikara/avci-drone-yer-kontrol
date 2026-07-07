# -*- coding: utf-8 -*-
"""
ONGORULU (LEAD) YAW dogrulama — kameranin hareketli hedefi kadrajda tutmasi.

PROBLEM (canli log 7 Tem): gorsel fazda ex ortalamasi +0.49 (hedef hep kadrajin
sag yarisinda, kamera GERIDEN takip); kayiplarin %100'u hedef KENARDA (ex~0.9).
Salt-P yaw hareketli hedefte kalici gecikme birakir.

Bu test GERCEKCI yaw dinamigi ile (rate-limitli komut + sinirli donus hizi) SABIT
MENZILDE capraz gecen hedefi simule eder; PNG'nin yaw komutunu uygular ve kadraj
hatasi |ex| ortalamasini LEAD KAPALI vs ACIK olcer. Beklenti: lead |ex|'i belirgin
dusurur (kamera hedefi merkezde tutar) -> KENAR-KAYBI biter.

Calistirma:  python tests/test_yaw_lead.py     (pytest de calisir)
"""
import os
import sys
import math
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pose import geometri
from guidance.png_gorsel import AvciPNGGuduum
from guidance.ana_kontrol import Cfg, rate_limit, clamp

TILT = 25.0
W, H = 1920.0, 1080.0
FX = geometri.fx_from_hfov(W)


def _det_yap(p_target, drone_pos, psi_deg, t):
    cam_pos, R_cam = geometri.kamera_pozu(drone_pos, (0.0, 0.0, psi_deg), tilt_deg=TILT)
    uv = geometri.projekte(np.asarray(p_target, float), cam_pos, R_cam, FX, W, H)
    if uv is None:
        return None
    cx, cy = uv
    R = float(np.linalg.norm(np.asarray(p_target, float) - cam_pos))
    w_px = FX * Cfg.VIS_SPAN_CM / R
    h_px = FX * 110.0 / R
    return {"cx": cx, "cy": cy, "w": w_px, "h": h_px, "conf": 0.9,
            "cls": 0, "W": W, "H": H, "t": t}


def _kosu(k_lead):
    """Sabit menzilde capraz gecen hedef; PNG yaw komutunu uygula. Yerlesme sonrasi
    ortalama |ex| dondur. k_lead: VIS_K_YAW_LEAD (gecici)."""
    eski = Cfg.VIS_K_YAW_LEAD
    Cfg.VIS_K_YAW_LEAD = k_lead
    try:
        g = AvciPNGGuduum()
        drone = np.array([0.0, 0.0, 1000.0])
        R0 = 800.0                                # 8 m sabit menzil
        theta = -0.15                             # hedef baslangic azimut (rad)
        theta_dot = 0.8                           # rad/s capraz gecis (~46 deg/s, gucyu stres)
        psi = theta                               # burun basta hedefe kilitli (deg->rad ayni)
        K_RATE = 2.0                              # yaw komutu -> donus hizi (rad/s @ cmd=1)
        dt = 0.02                                 # 50 Hz kontrol
        det_periyot = 0.05                        # 20 Hz dedektor
        yaw_prev = 0.0
        son_det = None; son_det_t = -1.0; son_psi = psi
        ex_kayit = []
        for k in range(400):                      # 8 s
            t = k * dt
            theta += theta_dot * dt
            # hedef sabit menzilde azimut supurur (dikey ~ ayni irtifa)
            p_t = drone + np.array([R0 * math.cos(theta), R0 * math.sin(theta), 0.0])

            if t - son_det_t >= det_periyot - 1e-9:
                d = _det_yap(p_t, drone, math.degrees(psi), t)
                if d is not None:
                    son_det, son_det_t, son_psi = d, t, psi
            if son_det is None:
                continue
            # PNG komutu (bu tik guncel psi ile det uret; omega det frame'inde kuruldu)
            d_now = _det_yap(p_t, drone, math.degrees(psi), t)
            if d_now is not None:
                ex_now = (d_now["cx"] - W / 2.0) / (W / 2.0)
                if t > 2.0:                        # yerlesme sonrasi olc
                    ex_kayit.append(abs(ex_now))
            _, _, _, yaw = g.hesapla(son_det, drone, (0.0, 0.0, math.degrees(psi)),
                                     np.zeros(2), Cfg)
            yaw = rate_limit(yaw, yaw_prev, Cfg.MAX_DELTA)   # _send ile ayni rate-limit
            yaw = clamp(yaw, -Cfg.YAW_MAX, Cfg.YAW_MAX)
            yaw_prev = yaw
            psi += K_RATE * yaw * dt                # burun donus dinamigi (yaw_cmd>0 -> saga)
        return (sum(ex_kayit) / len(ex_kayit)) if ex_kayit else 1.0
    finally:
        Cfg.VIS_K_YAW_LEAD = eski


def test_lead_kadraj_hatasini_dusurur():
    ex_p = _kosu(0.0)                              # salt-P (eski davranis)
    ex_lead = _kosu(0.30)                          # P + lead
    print("ortalama |ex|:  salt-P=%.3f  P+lead=%.3f" % (ex_p, ex_lead))
    # salt-P'de belirgin gecikme olmali (hedef kenara dogru), lead bunu dusurmeli
    assert ex_p > 0.30, "test kurulumu gecikme uretmedi (salt-P |ex|=%.3f)" % ex_p
    assert ex_lead < ex_p * 0.7, (
        "lead kadraj hatasini yeterince dusurmedi: salt-P=%.3f lead=%.3f "
        "(isaret ters olabilir)" % (ex_p, ex_lead))


def test_lead_isareti_dogru():
    """Lead, P ile AYNI yonde katki vermeli (gecikmeyi kapatmali, artirmamamli)."""
    ex_p = _kosu(0.0)
    ex_lead = _kosu(0.30)
    assert ex_lead <= ex_p, "lead |ex|'i ARTIRDI -> isaret ters (salt-P=%.3f lead=%.3f)" % (ex_p, ex_lead)


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

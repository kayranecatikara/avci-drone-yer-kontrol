# -*- coding: utf-8 -*-
"""
DINAMIK DIKEY REFERANS (durus kompanzasyonu, F1) — saf matematik testleri.
Govdeye sabit kamera (25 derece yukari, hFOV 125) one yatinca hedefin goruntu
konumu kayar; referans artik durustan hesaplanir:
    ey_ref = tan(TILT + pitch_own) / tan(vFOV/2),  tan(vFOV/2)=tan(hFOV/2)*H/W
(UE: one yatis = NEGATIF pitch). Eski sabit-REF davranisi comp kapaliyken korunur.

Kosum (repo kokunden):  python -m pytest tests/test_ibvs_att_comp.py -q
"""
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from guidance.ibvs_guidance import AvciGorselGuduum, dinamik_ey_ref  # noqa: E402


class P:
    VIS_EMA         = 0.4
    VIS_EY_REF      = 0.43
    VIS_ATT_COMP    = 1.0
    VIS_CAM_TILT_DEG = 25.0
    VIS_HFOV_DEG    = 125.0
    VIS_SIGN_YAW    = +1.0
    VIS_SIGN_VZ     = -1.0
    VIS_SIGN_PITCH  = +1.0
    VIS_SIGN_ROLL   = +1.0
    VIS_K_YAW       = 0.5
    VIS_K_ROLL      = 0.0
    VIS_K_VZ        = 2.0
    VIS_VZ_MAX      = 1100.0
    VIS_KV_Z        = 0.0020
    VIS_ALC_MIN     = 0.5
    VIS_K_FWD       = 0.4
    VIS_FWD_MAX     = 0.5
    VIS_CENTER_GATE = 0.35
    VIS_W_STOP      = 0.30
    THR_DN          = -1.00
    THR_UP          = 0.70
    VZ_MAX          = 3333.0


class P_KAPALI(P):
    VIS_ATT_COMP = 0.0


W, H = 1280.0, 720.0                      # 16:9 -> tan(vFOV/2) = tan(62.5)*0.5625
BBW, BBH = 0.10 * W, 0.08 * H
FWD_TAM = P.VIS_K_FWD * (1.0 - 0.10 / P.VIS_W_STOP)   # 0.26667


def test_referans_degerleri_tan_dogru():
    # Denetimdeki tan-dogru degerler: yatis 0 / 11.5 / 23 derege karsilik.
    assert dinamik_ey_ref(P, 0.0, W, H) == pytest.approx(0.43155, abs=1e-4)
    assert dinamik_ey_ref(P, -11.5, W, H) == pytest.approx(0.22218, abs=1e-4)
    assert dinamik_ey_ref(P, -23.0, W, H) == pytest.approx(0.03232, abs=1e-4)


def test_comp_kapali_veya_pitch_yoksa_statik_fallback():
    assert dinamik_ey_ref(P, None, W, H) == 0.43            # pitch bilinmiyor -> eski davranis
    assert dinamik_ey_ref(P_KAPALI, -23.0, W, H) == 0.43    # toggle kapali -> eski davranis


def test_en_boy_etkisi():
    # 4:3 pencerede vFOV buyur -> ayni tilt daha kucuk normalize referans verir.
    r_169 = dinamik_ey_ref(P, 0.0, 1280.0, 720.0)
    r_43 = dinamik_ey_ref(P, 0.0, 1280.0, 960.0)
    beklenen_43 = math.tan(math.radians(25.0)) / (math.tan(math.radians(62.5)) * 0.75)
    assert r_43 == pytest.approx(beklenen_43, abs=1e-6)
    assert r_43 < r_169


def test_uc_yatis_klempi():
    # elev +-75'e klemplenir; tan patlamasi yerine [-1,1] sinirina oturur.
    assert dinamik_ey_ref(P, -120.0, W, H) == -1.0
    assert dinamik_ey_ref(P, +80.0, W, H) == 1.0


def test_limit_cevrim_birim_regresyonu():
    # 23 derece one yatista, ESKI sabit-REF hizasinda (ny=0.715) duran ayni-irtifa
    # hedef: comp ACIKKEN dogru yorum = hedef REFERANSIN ALTINDA -> INIS + kapi ACIK
    # (ileri surer). ESKI kod eyd=0 sanip hover'da kaliyordu; yatis dinamiginde bu
    # sahte tirmanis + kapi cirpinmasi (limit cevrim) uretiyordu.
    g = AvciGorselGuduum()
    thr, pitch, _, _ = g.hesapla((0.5 * W, 0.715 * H), W, H, (BBW, BBH), P,
                                 vz=0.0, pitch_deg=-23.0, det_t=1.0)
    assert thr < -0.5                                       # guclu inis istegi (eyd ~ +0.40)
    assert pitch == pytest.approx(FWD_TAM * P.VIS_ALC_MIN)  # kapi ACIK + hafif kisma
    # comp KAPALI ayni girdi: eski davranis — eyd ~ 0, hover + tam ileri.
    g2 = AvciGorselGuduum()
    thr2, pitch2, _, _ = g2.hesapla((0.5 * W, 0.715 * H), W, H, (BBW, BBH), P_KAPALI,
                                    vz=0.0, pitch_deg=-23.0, det_t=1.0)
    assert thr2 == pytest.approx(0.0, abs=0.01)
    assert pitch2 == pytest.approx(FWD_TAM)


def test_dondurma_ayni_karede_ref_degismez():
    # Referans yalniz YENI tespitte guncellenir (goruntu+durus tutarli SNAPSHOT).
    g = AvciGorselGuduum()
    g.hesapla((0.5 * W, 0.715 * H), W, H, (BBW, BBH), P, pitch_deg=-23.0, det_t=1.0)
    ref1 = g.son_ey_ref
    g.hesapla((0.5 * W, 0.715 * H), W, H, (BBW, BBH), P, pitch_deg=0.0, det_t=1.0)
    assert g.son_ey_ref == pytest.approx(ref1)              # ayni kare: DONMUS
    g.hesapla((0.5 * W, 0.715 * H), W, H, (BBW, BBH), P, pitch_deg=0.0, det_t=2.0)
    assert g.son_ey_ref == pytest.approx(0.43155, abs=1e-4)  # yeni kare: guncellendi


def test_kor_devam_donmus_referansi_tasir():
    g = AvciGorselGuduum()
    g.hesapla((0.5 * W, 0.715 * H), W, H, (BBW, BBH), P, vz=0.0,
              pitch_deg=-23.0, det_t=1.0)
    thr, _, _, _ = g.kor_devam(P, vz=0.0)
    assert thr < -0.5                                       # donmus eyd ~ +0.40 -> inis surer


def test_kare_basina_ema_ayni_karede_islemez():
    g = AvciGorselGuduum()
    g.hesapla((0.5 * W, 0.815 * H), W, H, (BBW, BBH), P, det_t=1.0)
    ey1 = g.ey_f                                            # ilk kare: ham (0.63)
    g.hesapla((0.5 * W, 1.0 * H), W, H, (BBW, BBH), P, det_t=1.0)   # AYNI det_t
    assert g.ey_f == pytest.approx(ey1)                     # EMA islemedi
    g.hesapla((0.5 * W, 1.0 * H), W, H, (BBW, BBH), P, det_t=2.0)   # YENI kare
    assert g.ey_f == pytest.approx(0.6 * ey1 + 0.4 * 1.0)   # tek EMA adimi


def test_defaultlar_eski_davranisi_korur():
    # Yeni kwarg'lar verilmeden cagri: statik REF + her-cagri EMA (v2 sayilari).
    g = AvciGorselGuduum()
    thr, _, _, _ = g.hesapla((0.5 * W, 0.815 * H), W, H, (BBW, BBH), P)
    assert thr == pytest.approx(-0.88)                      # 0.002*(-440-0)
    assert g.son_ey_ref == pytest.approx(0.43)

# -*- coding: utf-8 -*-
"""
FAZ 3: guidance/gudum_yasasi.py (APN+OIPN) + iletisim/hakem_istemci.py testleri.
Calistirma:  python test/test_gudum_hakem.py   (sim GEREKMEZ)
"""
import math
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from guidance.gudum_yasasi import apn_oipn, GudumCfg
from iletisim.hakem_istemci import HakemIstemci


def test_apn_temel():
    # lam_dot=0 -> PN ivmesi 0 (LOS donmuyor, carpisma rotasinda)
    r = apn_oipn(0.0, 1000.0, (1.0, 0.0))
    assert abs(r["a_pn"]) < 1e-9 and r["a_cmd"] == (0.0, 0.0)
    # lam_dot>0 -> PN ivmesi N·Vc·λ̇, LOS'a dik yonde
    r = apn_oipn(0.01, 1000.0, (1.0, 0.0))       # LOS +x; dik yon (0,-1)
    assert abs(r["a_pn"] - 4.0 * 1000.0 * 0.01) < 1e-6
    ax, ay = r["a_cmd"]
    assert abs(ax) < 1e-6 and ay < 0            # dik yonde (uy,-ux)=(0,-1)


def test_apn_hedef_ivme():
    # a_T verilince (N/2)·a_T dik bileseni eklenir
    r0 = apn_oipn(0.005, 800.0, (1.0, 0.0))
    r1 = apn_oipn(0.005, 800.0, (1.0, 0.0), a_T=(0.0, -100.0))  # dik yonde a_T
    assert abs(r1["a_apn"]) > 0
    assert abs(r1["a_cmd"][1]) > abs(r0["a_cmd"][1])            # daha buyuk dik ivme


def test_oipn_deadzone():
    # |phi_T| < 5 deg -> OIPN 0 (gurultu bastir)
    r = apn_oipn(0.005, 800.0, (1.0, 0.0), phi_T=3.0, V_T=2000.0)
    assert r["a_oipn"] == 0.0 and r["kullanildi"] == "APN"


def test_oipn_devrede():
    # phi_T=20 deg, V_T var -> OIPN terimi devrede, a_ff=g·tan(20)
    r = apn_oipn(0.005, 800.0, (1.0, 0.0), phi_T=20.0, V_T=2000.0)
    beklenen = GudumCfg.BETA * GudumCfg.G * math.tan(math.radians(20.0))
    assert abs(r["a_oipn"] - beklenen) < 1e-6
    assert r["kullanildi"] == "APN+OIPN"


def test_oipn_pnp_gecersiz_sifir():
    # phi_T None (PnP gecersiz) -> OIPN otomatik 0
    r = apn_oipn(0.005, 800.0, (1.0, 0.0), phi_T=None, V_T=2000.0)
    assert r["a_oipn"] == 0.0 and r["kullanildi"] == "APN"


def test_oipn_anahtar_kapali():
    # oipn_acik=False -> OIPN 0 (arayuz anahtari)
    r = apn_oipn(0.005, 800.0, (1.0, 0.0), phi_T=20.0, V_T=2000.0, oipn_acik=False)
    assert r["a_oipn"] == 0.0


def test_ivme_tavani():
    # cok buyuk lam_dot -> A_MAX ile kirpilir
    r = apn_oipn(1.0, 5000.0, (1.0, 0.0))
    assert math.hypot(*r["a_cmd"]) <= GudumCfg.A_MAX + 1e-6


def test_hakem_kilit_bir_kez():
    yol = os.path.join(tempfile.gettempdir(), "hakem_test.jsonl")
    if os.path.exists(yol):
        os.remove(yol)
    h = HakemIstemci(log_yolu=yol)
    kd = {"kumulatif_kilit_sn": 5.2, "surekli_kilit_sn": 3.1}
    assert h.kilit_paketi_gonder(1.0, (100, 200, 300), kd) is True    # ilk: True
    assert h.kilit_gonderildi is True
    assert h.kilit_paketi_gonder(2.0, (100, 200, 300), kd) is False   # tekrar: False
    # log: 2 satir, ikincisi tekrar=True
    with open(yol, encoding="utf-8") as f:
        satirlar = f.readlines()
    assert len(satirlar) == 2
    import json
    assert json.loads(satirlar[1])["tekrar"] is True
    h.kapat()
    os.remove(yol)


def test_hakem_telemetri_hiz_siniri():
    yol = os.path.join(tempfile.gettempdir(), "hakem_tel.jsonl")
    if os.path.exists(yol):
        os.remove(yol)
    h = HakemIstemci(log_yolu=yol)
    # ayni anda iki cagri: ikincisi hiz-limitiyle atlanir
    ok1 = h.telemetri_gonder(1.0, (1, 2, 3), "GORSEL_GUDUM", hz=5.0)
    ok2 = h.telemetri_gonder(1.0, (1, 2, 3), "GORSEL_GUDUM", hz=5.0)
    assert ok1 is True and ok2 is False
    h.kapat()
    os.remove(yol)


def test_hakem_sifirla():
    yol = os.path.join(tempfile.gettempdir(), "hakem_sfr.jsonl")
    h = HakemIstemci(log_yolu=yol)
    h.kilit_paketi_gonder(1.0, (1, 2, 3), {})
    h.sifirla()
    assert h.kilit_gonderildi is False        # yeni gorev -> tekrar gonderilebilir
    h.kapat()
    if os.path.exists(yol):
        os.remove(yol)


if __name__ == "__main__":
    testler = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in testler:
        t()
        print("OK  %s" % t.__name__)
    print("TUM TESTLER GECTI (%d)" % len(testler))

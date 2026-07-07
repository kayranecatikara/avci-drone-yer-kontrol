# -*- coding: utf-8 -*-
"""
BASIT IBVS dogrulama (oyunsuz): goruntu merkezi -> bbox merkezi cizgisi.

Test edilenler:
  1) Yon eslemesi: hedef SAGDA -> yaw>0; SOLDA -> yaw<0; YUKARIDA -> thr>0
     (tirman); ASAGIDA -> thr<0; MERKEZDE -> yaw~0, thr~0, ileri TAM.
  2) Merkez freni: cizgi buyudukce ileri itki kisilir.
  3) Aci/buyukluk aritmetigi: sag=0, yukari=+90, asagi=-90.
  4) Clamp'ler: |yaw| <= YAW_MAX, thr THR_DN..THR_UP; roll HEP 0.
  5) EMA: tek-kare sicrama yumusatilir (ilk kare aynen alinir).
  6) GPS'siz imza: hesapla yalniz (det, p) alir — konum/hiz/rotasyon parametresi
     YOK -> "gorsel fazda GPS yasak" yarisma kurali YAPISAL olarak saglanir.

Calistirma:  python tests/test_ibvs_gorsel.py     (pytest de calisir)
"""
import inspect
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from guidance.ibvs_gorsel import AvciIBVS
from guidance.ana_kontrol import Cfg

W, H = 1920.0, 1080.0


def _det(cxn=0.5, cyn=0.5, wp=0.08, hp=0.04, t=0.0):
    return {"cx": cxn * W, "cy": cyn * H, "w": wp * W, "h": hp * H,
            "conf": 0.9, "cls": 0, "W": W, "H": H, "t": t}


def _tek(cxn, cyn):
    """Tek kare besle (ilk kare EMA'siz aynen alinir) -> (thr,pitch,roll,yaw)."""
    return AvciIBVS().hesapla(_det(cxn=cxn, cyn=cyn), Cfg)


def test_yon_eslemesi():
    thr, _, _, yaw = _tek(0.75, 0.5)             # hedef SAGDA
    assert yaw > 0 and abs(thr) < 1e-9, "sagda: yaw>0 thr=0 bekleniyordu"
    _, _, _, yaw = _tek(0.25, 0.5)               # SOLDA
    assert yaw < 0
    thr, _, _, yaw = _tek(0.5, 0.25)             # YUKARIDA
    assert thr > 0 and abs(yaw) < 1e-9, "yukarida: thr>0 (tirman) bekleniyordu"
    thr, _, _, _ = _tek(0.5, 0.75)               # ASAGIDA
    assert thr < 0, "asagida: thr<0 (alcal) bekleniyordu"


def test_merkezde_tam_ileri():
    thr, pitch, roll, yaw = _tek(0.5, 0.5)
    assert abs(yaw) < 1e-9 and abs(thr) < 1e-9
    assert abs(pitch - Cfg.PITCH_SIGN * Cfg.IBVS_ILERI) < 1e-9, \
        "merkezde ileri itki tam IBVS_ILERI olmali (kisma=1)"


def test_merkez_freni_ileriyi_kisar():
    p_merkez = abs(_tek(0.5, 0.5)[1])
    p_kenar = abs(_tek(0.98, 0.5)[1])            # cizgi ~0.96 -> fren
    assert p_kenar < p_merkez, "sapma buyuyunce ileri itki kisilmali"


def test_aci_ve_buyukluk():
    g = AvciIBVS(); g.hesapla(_det(cxn=0.75, cyn=0.5), Cfg)
    d = g.durum()
    assert abs(d["aci_deg"] - 0.0) < 1e-6, "sag = 0 derece"
    assert abs(d["buyukluk"] - 0.5) < 1e-6
    g = AvciIBVS(); g.hesapla(_det(cxn=0.5, cyn=0.25), Cfg)
    assert abs(g.durum()["aci_deg"] - 90.0) < 1e-6, "yukari = +90 derece"
    g = AvciIBVS(); g.hesapla(_det(cxn=0.5, cyn=0.75), Cfg)
    assert abs(g.durum()["aci_deg"] + 90.0) < 1e-6, "asagi = -90 derece"


def test_clamp_ve_roll_sifir():
    thr, _, roll, yaw = _tek(1.0, 0.0)           # sag-ust kose (asiri sapma)
    assert abs(yaw) <= Cfg.YAW_MAX + 1e-9, "yaw YAW_MAX'i asmamali"
    assert Cfg.THR_DN - 1e-9 <= thr <= Cfg.THR_UP + 1e-9
    assert roll == 0.0, "roll HEP 0 (bank yok)"
    thr2 = _tek(0.5, 1.0)[0]                     # tam alt kenar
    assert thr2 >= Cfg.THR_DN - 1e-9


def test_ema_yumusatma():
    g = AvciIBVS()
    g.hesapla(_det(cxn=0.5, cyn=0.5, t=0.0), Cfg)    # merkez (ilk kare)
    g.hesapla(_det(cxn=0.9, cyn=0.5, t=0.1), Cfg)    # ani sicrama (ex=0.8)
    assert 0.0 < g.ex_f < 0.8, "EMA sicramayi yumusatmali (tam 0.8'e atlamamali)"


def test_gps_siz_imza():
    """hesapla yalniz (det, p) alir — 'gorsel fazda GPS yasak' yapisal garanti."""
    params = list(inspect.signature(AvciIBVS.hesapla).parameters)
    assert params == ["self", "det", "p"], "imzaya konum/hiz parametresi SIZMAMALI: %s" % params


if __name__ == "__main__":
    fns = [(n, f) for n, f in sorted(globals().items())
           if n.startswith("test_") and callable(f)]
    gecen = 0
    for n, f in fns:
        try:
            f()
            print("OK  " + n)
            gecen += 1
        except AssertionError as e:
            print("FAIL " + n + " -> " + str(e))
        except Exception as e:
            print("ERR  " + n + " -> " + repr(e))
    print("\n%d/%d test gecti." % (gecen, len(fns)))
    sys.exit(0 if gecen == len(fns) else 1)

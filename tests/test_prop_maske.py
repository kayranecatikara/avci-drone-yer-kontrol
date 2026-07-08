# -*- coding: utf-8 -*-
"""
PERVANE MASKESI dogrulama — HedefDedektor._maskede + tespit_et argmax-oncesi eleme.

Kendi pervanemiz arada bir "ucak" olarak algilaniyor (dedektor sinif-agnostik en-yuksek
conf'u secer). Pervane KADRAJDA SABIT bolgede -> o bolgede MERKEZI olan kutular elenir.
Bu test _maskede geometrisini ve tespit_et'in sahte 'boxes' ile secim mantigini dogrular
(YOLO/model YUKLENMEDEN — res nesnesi taklit edilir).

Calistirma:  python tests/test_prop_maske.py     (pytest de calisir)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from detection.gorsel_tespit import HedefDedektor

MASKE = [(0.80, 0.55, 1.0, 0.95)]     # sag-alt (Cfg.PROP_MASKE varsayilani)


# ---------------------------------------------------------------------------
#  _maskede geometri
# ---------------------------------------------------------------------------
def test_maskede_geometri():
    m = HedefDedektor._maskede
    assert m(0.90, 0.75, MASKE) is True         # sag-alt kose -> icinde
    assert m(0.50, 0.50, MASKE) is False        # merkez -> disinda
    assert m(0.90, 0.30, MASKE) is False        # sag ama UST -> disinda
    assert m(0.10, 0.75, MASKE) is False        # alt ama SOL -> disinda
    assert m(0.50, 0.50, None) is False         # maske yok -> hep False
    assert m(0.50, 0.50, []) is False


# ---------------------------------------------------------------------------
#  tespit_et: sahte res ile argmax-oncesi eleme
# ---------------------------------------------------------------------------
class _FakeTensor(list):
    def __init__(s, v): super().__init__(v)
    def argmax(s): return max(range(len(s)), key=lambda i: s[i])

class _FakeBoxes:
    def __init__(s, boxes):
        s.xyxy = [b["xyxy"] for b in boxes]
        s.conf = _FakeTensor([b["conf"] for b in boxes])
        s.cls = _FakeTensor([b.get("cls", 0) for b in boxes])
    def __len__(s): return len(s.xyxy)

class _FakeRes:
    def __init__(s, boxes, W=1000, H=1000):
        s.boxes = _FakeBoxes(boxes)
        s.orig_shape = (H, W)

class _FakeModel:
    def __init__(s, res): s._res = res
    def predict(s, *a, **k): return [s._res]

def _dedektor(boxes, W=1000, H=1000):
    d = HedefDedektor.__new__(HedefDedektor)   # __init__'i atla (YOLO yukleme yok)
    d.hazir = True
    d.imgsz = 1280; d.conf = 0.25; d.device = "cpu"; d._q = {}   # FP16 kwarg (gercek __init__ set eder)
    d.model = _FakeModel(_FakeRes(boxes, W, H))
    return d


def test_pervane_elenir_hedef_secilir():
    # pervane sag-altta YUKSEK conf (0.9), gercek hedef merkezde DUSUK conf (0.5).
    # Maske YOKKEN pervane secilir; maske VARKEN hedef secilir.
    boxes = [
        {"xyxy": (880, 720, 980, 820), "conf": 0.90, "cls": 0},   # pervane (merkez ~0.93,0.77)
        {"xyxy": (480, 480, 520, 520), "conf": 0.50, "cls": 0},   # gercek hedef (merkez 0.5,0.5)
    ]
    # maske yok -> yuksek conf pervane secilir
    d0 = _dedektor(boxes)
    r0 = d0.tespit_et(None, maske=None)
    assert abs(r0["cx"]/1000 - 0.93) < 0.02, "maske yokken pervane secilmeliydi"
    # maske var -> pervane elenir, hedef secilir
    d1 = _dedektor(boxes)
    r1 = d1.tespit_et(None, maske=MASKE)
    assert abs(r1["cx"]/1000 - 0.5) < 0.02, "maske varken gercek hedef secilmeliydi (conf=%.2f)"%r1["conf"]
    assert abs(r1["conf"] - 0.5) < 1e-6


def test_tek_kutu_pervane_ise_none():
    # tek kutu ve o da maskede -> tespit yok (None)
    boxes = [{"xyxy": (880, 720, 980, 820), "conf": 0.90, "cls": 0}]
    d = _dedektor(boxes)
    assert d.tespit_et(None, maske=MASKE) is None, "tek kutu pervaneyse None donmeli"


def test_maske_disi_hedef_etkilenmez():
    # merkezdeki tek hedef maske ile de aynen secilir (yan etki yok)
    boxes = [{"xyxy": (480, 480, 520, 520), "conf": 0.7, "cls": 0}]
    d = _dedektor(boxes)
    r = d.tespit_et(None, maske=MASKE)
    assert r is not None and abs(r["cx"]/1000 - 0.5) < 0.02


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

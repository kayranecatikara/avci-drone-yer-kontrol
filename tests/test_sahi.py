# -*- coding: utf-8 -*-
"""
SAHI (Slicing Aided Hyper Inference) dogrulama — HedefDedektor dilimleme yolu.

SAHI: kareyi ortusen dilimlere bol, HER dilimde predict, kutulari tam-kare koordina
tasi (offset) + NMS ile birlestir -> uzak/kucuk hedef recall. Bu test SAF geometri +
merge mantigini dogrular (YOLO/model YUKLENMEDEN; model + res taklit edilir):
  _dilimler  : izgara kapsama / kenar kirpma / kucuk-kare bos
  _iou_xyxy  : IoU
  _nms       : cift kutu collapse, en-yuksek-conf tut, ayrik kutu korunur
  _sahi_ham  : kosullu-atlama (yakin hedef), dilim offset dogrulugu, ndarray-disi fallback
  tespit_hepsi: sahi yolu tam-kare piksel semasi (cx,cy,W,H) + pervane maskesi

Calistirma:  python tests/test_sahi.py     (pytest de calisir)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from detection.gorsel_tespit import HedefDedektor


# ---------------------------------------------------------------------------
#  Sahte model/res (YOLO yuklemeden dilimleme yolunu surmek icin)
# ---------------------------------------------------------------------------
class _FakeBoxes:
    def __init__(s, boxes):
        s.xyxy = [b["xyxy"] for b in boxes]
        s.conf = [b["conf"] for b in boxes]
        s.cls = [b.get("cls", 0) for b in boxes]
    def __len__(s): return len(s.xyxy)

class _FakeRes:
    def __init__(s, boxes, W, H):
        s.boxes = _FakeBoxes(boxes)
        s.orig_shape = (H, W)
        s.keypoints = None

class _FakeModel:
    """predict(arr) -> fn(arr) ile kutu uretir. arr.shape (H,W,3); orig_shape ondan.
    Cagri sayaci sayar (kosullu-atlama testi predict adedini denetler)."""
    def __init__(s, fn):
        s.fn = fn
        s.cagri = 0
    def predict(s, frame, *a, **k):
        s.cagri += 1
        arr = np.asarray(frame)
        H, W = int(arr.shape[0]), int(arr.shape[1])
        return [_FakeRes(s.fn(arr, W, H), W, H)]


def _dedektor(fn, **sahi):
    d = HedefDedektor.__new__(HedefDedektor)      # __init__'i atla (YOLO yok)
    d.hazir = True
    d.imgsz = 1280; d.conf = 0.15; d.device = "cpu"; d._fp16_kwargs = {}
    d.model = _FakeModel(fn)
    # SAHI varsayilanlari (test bazinda override)
    d.sahi = True
    d.sahi_dilim = sahi.get("dilim", 640)
    d.sahi_ortusme = sahi.get("ortusme", 0.2)
    d.sahi_tam_kare = sahi.get("tam_kare", True)
    d.sahi_nms_iou = sahi.get("nms_iou", 0.5)
    d.sahi_kosul_conf = sahi.get("kosul_conf", 0.5)
    return d


# ---------------------------------------------------------------------------
#  _dilimler geometri
# ---------------------------------------------------------------------------
def test_dilimler_kapsama():
    # 1280x720, dilim 640, ortusme 0.2 -> adim 512. Kare TAMAMEN kaplanmali.
    d = HedefDedektor._dilimler(1280, 720, 640, 0.2)
    assert len(d) >= 4, "yeterli dilim uretilmedi: %d" % len(d)
    assert max(x1 for _, _, x1, _ in d) == 1280, "sag kenar kaplanmadi"
    assert max(y1 for _, _, _, y1 in d) == 720, "alt kenar kaplanmadi"
    assert min(x0 for x0, _, _, _ in d) == 0 and min(y0 for _, y0, _, _ in d) == 0
    for x0, y0, x1, y1 in d:                       # her dilim kare icinde ve pozitif alan
        assert 0 <= x0 < x1 <= 1280 and 0 <= y0 < y1 <= 720

def test_dilimler_kucuk_kare_bos():
    # kare zaten dilimden kucuk -> dilim yok (tek tam-kare yeter)
    assert HedefDedektor._dilimler(500, 400, 640, 0.2) == []
    assert HedefDedektor._dilimler(640, 640, 640, 0.2) == []

def test_dilimler_tek_eksen():
    # genis ama alcak: yatayda dilim, dikeyde kirpma
    d = HedefDedektor._dilimler(1000, 400, 640, 0.2)
    assert len(d) == 2, d
    assert max(x1 for _, _, x1, _ in d) == 1000
    assert all(y1 == 400 for _, _, _, y1 in d)     # dikey kirpilir


# ---------------------------------------------------------------------------
#  _iou_xyxy / _nms
# ---------------------------------------------------------------------------
def test_iou():
    a = {"x1": 0, "y1": 0, "x2": 10, "y2": 10}
    assert abs(HedefDedektor._iou_xyxy(a, a) - 1.0) < 1e-9
    b = {"x1": 20, "y1": 20, "x2": 30, "y2": 30}
    assert HedefDedektor._iou_xyxy(a, b) == 0.0
    c = {"x1": 5, "y1": 0, "x2": 15, "y2": 10}     # yari ortusme -> IoU 1/3
    assert abs(HedefDedektor._iou_xyxy(a, c) - (50.0 / 150.0)) < 1e-6

def test_nms_collapse_en_yuksek_tutar():
    # ayni nesne iki kez (dilim+tam-kare), farkli conf -> tek kutu, YUKSEK conf
    k = [
        {"x1": 100, "y1": 100, "x2": 140, "y2": 140, "conf": 0.4, "cls": 0},
        {"x1": 102, "y1": 98,  "x2": 141, "y2": 139, "conf": 0.7, "cls": 0},
    ]
    out = HedefDedektor._nms(k, 0.5)
    assert len(out) == 1 and abs(out[0]["conf"] - 0.7) < 1e-9

def test_nms_ayrik_korunur():
    k = [
        {"x1": 0, "y1": 0, "x2": 40, "y2": 40, "conf": 0.6, "cls": 0},
        {"x1": 500, "y1": 500, "x2": 540, "y2": 540, "conf": 0.5, "cls": 0},
    ]
    assert len(HedefDedektor._nms(k, 0.5)) == 2


# ---------------------------------------------------------------------------
#  _sahi_ham: kosullu-atlama / offset / fallback
# ---------------------------------------------------------------------------
def test_sahi_kosullu_atlama():
    # tam-karede conf>=kosul_conf kutu VAR -> dilimleme ATLANIR (predict 1 kez)
    def fn(arr, W, H):
        return [{"xyxy": (600, 300, 660, 360), "conf": 0.8, "cls": 0}]  # yakin/guclu hedef
    d = _dedektor(fn, kosul_conf=0.5)
    frame = np.zeros((720, 1280, 3), dtype="uint8")
    ham, W, H = d._sahi_ham(frame)
    assert d.model.cagri == 1, "yakin hedefte dilimleme atlanmaliydi (predict=%d)" % d.model.cagri
    assert (W, H) == (1280, 720) and len(ham) == 1

def test_sahi_offset_dogru():
    # tam-kare BOS (kosullu tetiklenmez); yalnizca belli bir DILIMDE tespit ver.
    # Dedektor kutuyu tile-local uretir; _sahi_ham tam-kare koordina offsetlemeli.
    def fn(arr, W, H):
        if (W, H) == (1280, 720):
            return []                              # tam kare: tespit yok -> dilimleme sart
        # bir dilim (640x...) icinde tile-local (10,10)-(50,50) -> merkez ~(30,30)
        return [{"xyxy": (10, 10, 50, 50), "conf": 0.3, "cls": 0}]
    d = _dedektor(fn, kosul_conf=0.0, tam_kare=True, nms_iou=0.5)
    frame = np.zeros((720, 1280, 3), dtype="uint8")
    ham, W, H = d._sahi_ham(frame)
    assert d.model.cagri >= 2, "dilimleme kosmadi"
    # her dilimde ayni tile-local kutu -> farkli offsetlerle FARKLI tam-kare konumlar.
    # En az bir kutu (0,0) dilimindeki -> tam-kare (10,10,50,50); offset dogruysa mevcut.
    var = any(abs(k["x1"] - 10) < 1e-6 and abs(k["y1"] - 10) < 1e-6 for k in ham)
    assert var, "ilk dilim offset'i (0,0) bekleniyordu: %s" % ham
    # ve offsetli bir kutu (dilim x0=512 ya da 640) -> x1 >= 512+10
    assert any(k["x1"] >= 512 for k in ham), "offsetli dilim kutusu yok: %s" % ham

def test_sahi_ndarray_disi_fallback():
    # 3B ndarray degil (orn None/2B) -> _tek_ham'e duser, cokme yok
    def fn(arr, W, H):
        return [{"xyxy": (100, 100, 140, 140), "conf": 0.9, "cls": 0}]
    d = _dedektor(fn)
    ham, W, H = d._sahi_ham(np.zeros((10, 10), dtype="uint8"))   # 2B
    assert len(ham) == 1 and d.model.cagri == 1


# ---------------------------------------------------------------------------
#  tespit_hepsi: sahi yolu sema + pervane maskesi
# ---------------------------------------------------------------------------
def test_tespit_hepsi_sahi_sema():
    def fn(arr, W, H):
        return [{"xyxy": (600, 300, 680, 380), "conf": 0.7, "cls": 0}]   # tam-karede yakalanir
    d = _dedektor(fn, kosul_conf=0.5)
    frame = np.zeros((720, 1280, 3), dtype="uint8")
    r = d.tespit_hepsi(frame)
    assert len(r) == 1
    e = r[0]
    assert abs(e["cx"] - 640) < 1e-6 and abs(e["cy"] - 340) < 1e-6
    assert e["w"] == 80 and e["h"] == 80 and e["W"] == 1280 and e["H"] == 720
    assert e["conf"] == 0.7 and "t" in e

def test_tespit_hepsi_sahi_maske_eler():
    # sag-altta (maske icinde) tek kutu -> sahi yolunda da elenir
    def fn(arr, W, H):
        return [{"xyxy": (1100, 600, 1180, 680), "conf": 0.8, "cls": 0}]  # merkez ~(0.89,0.89)
    d = _dedektor(fn, kosul_conf=0.5)
    frame = np.zeros((720, 1280, 3), dtype="uint8")
    r = d.tespit_hepsi(frame, maske=[(0.80, 0.55, 1.0, 0.95)])
    assert r == [], "maske icindeki kutu sahi yolunda elenmodi: %s" % r


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

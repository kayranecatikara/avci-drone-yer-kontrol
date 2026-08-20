# -*- coding: utf-8 -*-
"""
perception/camera.py — kare yakalama -> tespit -> takip -> detection_state.

Simulasyon bir Unreal Engine OYUNU oldugundan "kamera" = oyunun EKRAN GORUNTUSU.
mss ile birincil monitor (ya da AVCI_BOLGE ile verilen dikdortgen) yakalanir,
YOLO tespiti kosulur, HybridSort kimlik surekliligini saglar ve sonuc
detection_state'e yayinlanir. Guduum dongusu (control/main.py) oradan okur.

    OYUN PENCERESI GORUNUR OLMALIDIR. mss EKRANI yakalar; oyun baska bir
    pencerenin arkasinda kalirsa dedektore masaustu pikseli gider ve hedef
    "kaybolur". Oyunu KENARLIKSIZ PENCERE modunda ONDE tut.

Ayarlar (ortam degiskeni):
    AVCI_BOLGE="left,top,w,h"   yalniz bu dikdortgeni yakala (varsayilan: tum ekran)
    AVCI_DEBUG_PENCERE=1        dedektorun GORDUGU kareyi kutularla ayri pencerede goster
    AVCI_FP16=0                 FP16 inference'i kapat

Cozunurluk: kare DOGAL cozunurlukte dedektore verilir (kucultme YOK). Kareyi
once kucultup modele geri buyutturmek uzaktaki kucuk hedefin detayini oldurur.
"""
import os
import threading
import time

import numpy as np

from perception import detection_state
from perception.detector import HedefDedektor
from perception.tracking import Takipci

FP16 = os.environ.get("AVCI_FP16", "1").lower() not in ("0", "off", "false")
DEBUG_PENCERE = os.environ.get("AVCI_DEBUG_PENCERE", "0").lower() in ("1", "on", "true")

_thread_local = threading.local()
_durum = {"kare": 0, "fps": 0.0, "det_ms": 0.0, "kaynak": None, "hata": None}


def _sct():
    """mss her is parcaciginda AYRI ornek ister -> thread-local."""
    import mss
    if not hasattr(_thread_local, "sct"):
        _thread_local.sct = mss.mss()
    return _thread_local.sct


def _bolge():
    """AVCI_BOLGE="left,top,w,h" verilmisse o dikdortgen, yoksa None (tum ekran)."""
    ham = os.environ.get("AVCI_BOLGE", "").strip()
    if not ham:
        return None
    try:
        l, t, w, h = [int(v) for v in ham.replace(" ", "").split(",")]
        return {"left": l, "top": t, "width": w, "height": h}
    except Exception:
        print("[KAMERA] AVCI_BOLGE cozulemedi (%r) -> tum ekran." % ham)
        return None


def yakala_bgr():
    """(BGR ndarray, kaynak_adi) doner; yakalanamazsa (None, sebep)."""
    try:
        sct = _sct()
        bbox = _bolge()
        if bbox is None:
            bbox = sct.monitors[1]                     # birincil monitor
            kaynak = "mss (tum ekran)"
        else:
            kaynak = "mss (AVCI_BOLGE)"
        raw = sct.grab(bbox)
        frame = np.frombuffer(raw.bgra, dtype=np.uint8).reshape(raw.height, raw.width, 4)
        return np.ascontiguousarray(frame[:, :, :3]), kaynak   # BGRA -> BGR
    except Exception as e:
        return None, "KARE YOK (%s)" % e


def _debug_ciz(bgr, det):
    """Dedektorun ISLEDIGI karenin uzerine AYNI karenin ciktisini ciz (kare<->cikti
    %100 senkron). Yalnizca AVCI_DEBUG_PENCERE=1 iken; kapaliyken sifir maliyet."""
    try:
        import cv2
        kare = bgr.copy()
        if det is not None:
            x1 = int(det["cx"] - det["w"] / 2); y1 = int(det["cy"] - det["h"] / 2)
            x2 = int(det["cx"] + det["w"] / 2); y2 = int(det["cy"] + det["h"] / 2)
            cv2.rectangle(kare, (x1, y1), (x2, y2), (0, 255, 0), 2)
            etiket = "ID:%s %.2f" % (det.get("track_id", "-"), det.get("conf", 0.0))
            cv2.putText(kare, etiket, (x1, max(20, y1 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        if kare.shape[1] > 1280:
            kare = cv2.resize(kare, (1280, int(kare.shape[0] * 1280 / kare.shape[1])))
        cv2.imshow("dedektor gozu", kare)
        cv2.waitKey(1)
    except Exception:
        pass


def dongu(aktif):
    """Kamera thread'i. `aktif`: her turda cagrilan, gorev calisiyor mu diyen fonksiyon."""
    dedektor = None
    takipci = Takipci()
    _t_onceki = None
    while True:
        if not aktif():
            if takipci.trackler:
                takipci.sifirla()                      # yeni gorev bayat ID ile baslamasin
            time.sleep(0.05)
            continue

        if dedektor is None:                           # LAZY: ilk gorev tikinde yukle
            dedektor = HedefDedektor(half=(True if FP16 else False))
            if dedektor.hazir:
                print("[KAMERA] best.pt yuklendi (device=%s, half=%s, imgsz=%d). Siniflar: %s"
                      % (dedektor.device, dedektor.half, dedektor.imgsz, dedektor.names))
                if not takipci.hazir:
                    print("[KAMERA] takipci YUKLENEMEDI (%s) -> ham tespit kullanilir."
                          % takipci.hata)
            else:
                print("[KAMERA] Dedektor YUKLENEMEDI (%s) -> sistem GPS fazinda devam eder."
                      % dedektor.hata)
        if not dedektor.hazir:
            time.sleep(1.0)                            # kurulum yok -> CPU yakma
            continue

        bgr, kaynak = yakala_bgr()
        if _durum["kaynak"] != kaynak:                 # kaynak degisince BIR KEZ yaz
            _durum["kaynak"] = kaynak
            print("[KAMERA] goruntu kaynagi -> %s" % kaynak)
        if bgr is None:
            time.sleep(0.05)
            continue

        t0 = time.perf_counter()
        dets = dedektor.tespit_hepsi(bgr)
        det = takipci.guncelle(dets, bgr)
        t1 = time.perf_counter()

        detection_state.yayinla(det, kare_t=t1)
        _durum["kare"] += 1
        _durum["det_ms"] = (t1 - t0) * 1000.0
        if _t_onceki is not None:
            dt = t1 - _t_onceki
            if dt > 1e-6:
                _durum["fps"] = 0.8 * _durum["fps"] + 0.2 * (1.0 / dt)
        _t_onceki = t1

        if DEBUG_PENCERE:
            _debug_ciz(bgr, det)


def baslat(aktif):
    """Kamera thread'ini arka planda baslat."""
    th = threading.Thread(target=dongu, args=(aktif,), daemon=True, name="kamera")
    th.start()
    return th


def durum():
    """(kare sayisi / FPS / inference suresi / kaynak) — konsol ozeti icin."""
    return dict(_durum)

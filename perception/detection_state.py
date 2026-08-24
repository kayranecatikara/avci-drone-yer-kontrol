# -*- coding: utf-8 -*-
"""
perception/detection_state.py — kamera thread'i ile guduum dongusu arasindaki
thread-safe kopru. perception/camera.py YAZAR;
control/main.py (PhaseSupervisor.read_detection) ve gorsel faz OKUR.

Tespit kaydi (dict) alanlari:
    cx, cy, w, h  — piksel; kutu merkezi ve boyutu
    conf          — tespit guveni (0..1)
    W, H          — kare olculeri (piksel)
    t             — perf_counter damgasi (bayatlik hesabi bunun uzerinden)
    id            — takip kimligi (HybridSort track_id) | None

Hedef bulunmayan karelerde de publish(None) cagrilir: "kare geldi ama hedef
yok" ile "kare hic gelmedi" ayri durumlardir — ilki takibin normal deligi,
ikincisi kamera arizasidir.
"""
import threading

_lock = threading.Lock()
_det = None
_seq = 0
_frame_t = None  # son kare zamani (kamera canli mi)


def publish(det, frame_t=None):
    """Yeni kareyi yayinla (hedef yoksa det=None)."""
    global _det, _seq, _frame_t
    with _lock:
        _det = det
        _seq += 1
        _frame_t = frame_t


def status():
    """(det, seq, frame_t) — okuyucunun tek atislik tutarli goruntusu."""
    with _lock:
        return _det, _seq, _frame_t


def reset():
    """Sayaci ve son kaydi sifirlar (yeni gorev)."""
    global _det, _seq, _frame_t
    with _lock:
        _det = None
        _seq = 0
        _frame_t = None

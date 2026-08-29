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
    """[KAMERA THREAD'I] Bu karenin sonucunu yayinlar.

    det     : tespit kaydi | None (kare geldi ama hedef yok)
    frame_t : s (perf_counter); karenin ISLENDIGI an

    Sayac (`seq`) her cagrida artar — hedef bulunmasa bile. Okuyucu bunu
    "yeni kare geldi mi?" olcusu olarak kullanir; kutu kimligi degil.
    """
    global _det, _seq, _frame_t
    with _lock:
        _det = det
        _seq += 1
        _frame_t = frame_t


def status():
    """[GUDUM DONGUSU] Son yayinin TEK ATISLIK tutarli goruntusu.

    -> (det, seq, frame_t)
       det     : son tespit | None
       seq     : kare sayaci — ayni kareyi iki kez saymamak icin
       frame_t : s; son karenin islenme ani

    Ucu birlikte, tek kilit altinda dondurulur: ayri ayri okunsalardi kamera
    thread'i aradan gecip bir karenin kutusuyla baska bir karenin sayacini
    eslestirebilirdi.
    """
    with _lock:
        return _det, _seq, _frame_t


def reset():
    """Yeni gorev: sayaci ve son kaydi sifirlar.

    Yeni gorevin ONCEKI gorevin kutusuyla acilmasini engeller. Tek basina
    YETMEZ; `camera.reset()` de cagrilmalidir, cunku bu yalnizca YAYINLANMIS
    kaydi temizler, uretici ile tuketici arasinda bekleyen KAREYI degil.
    """
    global _det, _seq, _frame_t
    with _lock:
        _det = None
        _seq = 0
        _frame_t = None

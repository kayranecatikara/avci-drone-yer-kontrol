# -*- coding: utf-8 -*-
"""
================================================================================
 PENCERE-ICERIGI YAKALAMA  (Windows.Graphics.Capture / windows-capture)
================================================================================
mss EKRAN-BOLGESI yakalar -> tek monitorde oyun tarayicinin ARKASINDA kalinca
yanlis pencereyi (masaustu/tarayici) alir ve ozyineleme (ayna) olur. Bu modul
hedef PENCERENIN ICERIGINI yakalar: pencere arkada / kucultulmus olsa BILE dogru
oyun goruntusu gelir. Tek monitor + tarayici onde senaryosu icin sart.

start_free_threaded ile kutuphane kendi thread'inde kare uretir; en son kareyi
lock altinda saklariz. get_latest_bgr() son BGR (H,W,3) kareyi doner (yoksa None).

ZARIF BOZULMA: windows-capture yoksa / pencere bulunamazsa hazir=False, get_latest_bgr=None
-> server.py mss'e geri duser (mevcut davranis korunur, sistem cokmez).
"""
import threading


def pencere_bul(title_hints):
    """title_hints (kucuk harf) ile eslesen ilk gorunur pencerenin (baslik, hwnd)
    ciftini doner. Bulamazsa (None, None)."""
    try:
        import pygetwindow as gw
    except Exception:
        return None, None
    try:
        for w in gw.getAllWindows():
            t = (w.title or "").strip()
            if not t:
                continue
            if any(h in t.lower() for h in title_hints):
                if w.width > 100 and w.height > 100:
                    return t, getattr(w, "_hWnd", None)
    except Exception:
        pass
    return None, None


class PencereYakala:
    def __init__(self, title_hints=None, window_name=None, window_hwnd=None):
        """
          title_hints : pencere basligi ipuclari (window_name/hwnd verilmezse aranir)
          window_name : tam pencere basligi (verilirse dogrudan kullanilir)
          window_hwnd : pencere handle'i (en saglam eslesme)
        """
        self.title_hints = [h.lower() for h in (title_hints or [])]
        self.window_name = window_name
        self.window_hwnd = window_hwnd
        self.hazir = False
        self.aktif_pencere = None
        self._latest = None
        self._lock = threading.Lock()
        self._baslat_lock = threading.Lock()   # baslat() cift-cagri yarisini onler
        self._control = None
        try:
            from windows_capture import WindowsCapture
            self._WindowsCapture = WindowsCapture
            self.hazir = True
        except Exception as e:
            print("[PENCERE_YAKALA] windows-capture yok (%s); mss fallback kullanilacak." % e)

    def calisiyor(self):
        return self._control is not None

    def baslat(self):
        """Yakalamayi baslatir (non-blocking). Zaten calisyorsa True; pencere
        bulunamazsa / hata olursa False (server mss'e duser). Iki thread ayni anda
        cagirsa bile kilit + cift-kontrol ile tek capture acilir."""
        if not self.hazir:
            return False
        with self._baslat_lock:
            if self._control is not None:
                return True
            return self._baslat_kilitli()

    def _baslat_kilitli(self):
        import numpy as np

        ad, hwnd = self.window_name, self.window_hwnd
        if ad is None and hwnd is None:
            ad, hwnd = pencere_bul(self.title_hints)
        if ad is None and hwnd is None:
            return False

        try:
            if hwnd:
                cap = self._WindowsCapture(cursor_capture=False, draw_border=False,
                                           window_hwnd=int(hwnd))
            else:
                cap = self._WindowsCapture(cursor_capture=False, draw_border=False,
                                           window_name=ad)
        except Exception as e:
            print("[PENCERE_YAKALA] capture olusturulamadi (%r): %s" % (ad or hwnd, e))
            return False

        @cap.event
        def on_frame_arrived(frame, capture_control):
            try:
                bgr = np.ascontiguousarray(frame.convert_to_bgr().frame_buffer)
                with self._lock:
                    self._latest = bgr
            except Exception:
                pass

        @cap.event
        def on_closed():
            # Pencere kapandi: kareyi temizle ve restart edilebilmesi icin control'u birak.
            with self._lock:
                self._latest = None
            self._control = None

        try:
            self._control = cap.start_free_threaded()
        except Exception as e:
            print("[PENCERE_YAKALA] start_free_threaded hatasi: %s" % e)
            self._control = None
            return False
        self.aktif_pencere = ad if ad else ("hwnd:%s" % hwnd)
        print("[PENCERE_YAKALA] yakalama basladi: %s" % self.aktif_pencere)
        return True

    def durdur(self):
        c = self._control
        self._control = None
        with self._lock:
            self._latest = None
        if c is not None:
            try:
                c.stop()
            except Exception:
                pass

    def get_latest_bgr(self):
        with self._lock:
            return self._latest

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


GAME_PROC_HINTS = ("dronesofwar",)      # oyun exe/surec adi bunu icermeli (kucuk harf)
# Baslik-ipucu fallback'inde ELENECEK surecler: tarayici sekmesi/editor basligi
# "Drones of War" icerebilir (orn. GitHub/Drive sayfasi) -> YANLIS pencere yakalanir.
_TARAYICI_EXE = ("brave", "chrome", "msedge", "firefox", "opera", "vivaldi", "code")
_TARAYICI_BASLIK = (" - brave", " - google chrome", " - microsoft edge",
                    " - mozilla firefox", " - opera", "visual studio code")


def _pencere_pid(hwnd):
    """hwnd -> sahibi surecin PID'i (ctypes; hata olursa None)."""
    try:
        import ctypes
        pid = ctypes.c_ulong(0)
        ctypes.windll.user32.GetWindowThreadProcessId(int(hwnd), ctypes.byref(pid))
        return int(pid.value) or None
    except Exception:
        return None


def _surec_adi(pid):
    """PID -> surec exe adi (kucuk harf; psutil yoksa/bilinmiyorsa bos string)."""
    if not pid:
        return ""
    try:
        import psutil
        return (psutil.Process(pid).name() or "").lower()
    except Exception:
        return ""


def pencere_bul(title_hints):
    """Oyun penceresini bul; (baslik, hwnd) doner, bulamazsa (None, None).
    ONCE pencerenin SAHIBI SUREC ADIYLA esler (DronesOfWar*.exe) — en saglami:
    tarayici sekmesinin basligi 'Drones of War' icerse bile yanilmaz.
    Surec eslesmezse baslik ipucuna duser; orada da tarayici/editor pencereleri elenir."""
    try:
        import pygetwindow as gw
    except Exception:
        return None, None
    adaylar = []
    try:
        for w in gw.getAllWindows():
            t = (w.title or "").strip()
            if t and w.width > 100 and w.height > 100:
                adaylar.append((t, getattr(w, "_hWnd", None)))
    except Exception:
        return None, None
    # 1) SUREC ADI eslesmesi (dogru pencere garantisi)
    for t, hwnd in adaylar:
        ad = _surec_adi(_pencere_pid(hwnd)) if hwnd else ""
        if ad and any(h in ad for h in GAME_PROC_HINTS):
            return t, hwnd
    # 2) BASLIK ipucu (fallback) — tarayici/editor pencerelerini ELE
    for t, hwnd in adaylar:
        tl = t.lower()
        if not any(h in tl for h in title_hints):
            continue
        ad = _surec_adi(_pencere_pid(hwnd)) if hwnd else ""
        if any(b in ad for b in _TARAYICI_EXE):
            continue                          # tarayici sekmesi basligi -> yanlis pencere
        if not ad and any(b in tl for b in _TARAYICI_BASLIK):
            continue                          # psutil yoksa baslik sonekiyle ele
        return t, hwnd
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
            # Oyun penceresi henuz bulunamadi: ~her 10 sn bir kez bilgilendir (spam yok).
            import time as _t
            simdi = _t.monotonic()
            if simdi - getattr(self, "_son_uyari_t", 0.0) > 10.0:
                self._son_uyari_t = simdi
                print("[PENCERE_YAKALA] Oyun penceresi bulunamadi (DronesOfWar surecine ait "
                      "gorunur pencere yok). Oyun acik ve PLAY modunda mi? -> server mss'e duser.")
            return False

        # Hedef (hwnd en saglam, sonra pencere adi) x yakalama ayarlari kombinasyonlari.
        # Bazi Windows surumlerinde (orn. Win10 LTSC 19044) 'capture border' / 'cursor'
        # API'leri YOK -> bunlara False gecirmek OTURUMU patlatir. Once istedigimiz
        # ayarlar, olmazsa ayarlara HIC dokunmayan (None=varsayilan) kombinasyon.
        hedefler = []
        if hwnd:
            hedefler.append(("hwnd", dict(window_hwnd=int(hwnd))))
        if ad:
            hedefler.append(("ad", dict(window_name=ad)))
        ayar_setleri = [dict(cursor_capture=False, draw_border=False),
                        dict(cursor_capture=None, draw_border=None)]
        son_hata = None
        for yontem, hkw in hedefler:
            for akw in ayar_setleri:
                try:
                    cap = self._WindowsCapture(**dict(akw, **hkw))
                except Exception as e:
                    son_hata = "olusturma(%s): %s" % (yontem, e)
                    continue

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
                    # Pencere kapandi: kareyi temizle; control birakilir -> restart edilebilir.
                    with self._lock:
                        self._latest = None
                    self._control = None

                try:
                    self._control = cap.start_free_threaded()
                    self.aktif_pencere = ad if ad else ("hwnd:%s" % hwnd)
                    print("[PENCERE_YAKALA] yakalama basladi: %s" % self.aktif_pencere)
                    return True
                except Exception as e:
                    son_hata = "baslatma(%s): %s" % (yontem, e)
                    self._control = None

        # Tum kombinasyonlar basarisiz: ~10 sn'de bir raporla (2 sn'lik retry SPAM'i yok).
        import time as _t
        simdi = _t.monotonic()
        if simdi - getattr(self, "_son_uyari_t", 0.0) > 10.0:
            self._son_uyari_t = simdi
            print("[PENCERE_YAKALA] baslatilamadi (%s) -> mss fallback." % son_hata)
        return False

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

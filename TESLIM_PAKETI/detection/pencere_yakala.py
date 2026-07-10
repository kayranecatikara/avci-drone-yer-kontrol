# -*- coding: utf-8 -*-
"""PENCERE-ICERIGI YAKALAMA. Hedef pencerenin icerigini yakalar (pencere arkada/kucultulmus
olsa bile dogru oyun goruntusu). windows-capture yoksa hazir=False -> server mss'e duser."""
import ctypes
import threading
import time


GAME_PROC_HINTS = ("dronesofwar",)      # oyun surec adi bunu icermeli (kucuk harf)
# Baslik-ipucu fallback'inde elenecek surecler (tarayici sekmesi basligi "Drones of War"
# icerebilir -> yanlis pencere yakalanir).
_TARAYICI_EXE = ("brave", "chrome", "msedge", "firefox", "opera", "vivaldi", "code")
_TARAYICI_BASLIK = (" - brave", " - google chrome", " - microsoft edge",
                    " - mozilla firefox", " - opera", "visual studio code")


def _pencere_pid(hwnd):
    """hwnd -> sahibi surecin PID'i (hata olursa None)."""
    try:
        import ctypes
        pid = ctypes.c_ulong(0)
        ctypes.windll.user32.GetWindowThreadProcessId(int(hwnd), ctypes.byref(pid))
        return int(pid.value) or None
    except Exception:
        return None


def _surec_adi(pid):
    """PID -> surec exe adi (kucuk harf; bilinmiyorsa bos string)."""
    if not pid:
        return ""
    try:
        import psutil
        return (psutil.Process(pid).name() or "").lower()
    except Exception:
        return ""


def pencere_bul(title_hints):
    """Oyun penceresini bul; (baslik, hwnd) doner, bulamazsa (None, None).
    Once surec adiyla esler (DronesOfWar*.exe), olmazsa baslik ipucuna duser
    (tarayici/editor pencereleri elenir)."""
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
    # 1) surec adi eslesmesi
    for t, hwnd in adaylar:
        ad = _surec_adi(_pencere_pid(hwnd)) if hwnd else ""
        if ad and any(h in ad for h in GAME_PROC_HINTS):
            return t, hwnd
    # 2) baslik ipucu (fallback) — tarayici/editor pencerelerini ele
    for t, hwnd in adaylar:
        tl = t.lower()
        if not any(h in tl for h in title_hints):
            continue
        ad = _surec_adi(_pencere_pid(hwnd)) if hwnd else ""
        if any(b in ad for b in _TARAYICI_EXE):
            continue
        if not ad and any(b in tl for b in _TARAYICI_BASLIK):
            continue
        return t, hwnd
    return None, None


# PrintWindow pencere-icerigi yakalama (saf Win32 GDI; ek native kutuphane yok).
# Oyun baska pencerelerin arkasindayken bile dogru kareyi verir.
class _BMIH(ctypes.Structure):
    _fields_ = [("biSize", ctypes.c_uint32), ("biWidth", ctypes.c_long),
                ("biHeight", ctypes.c_long), ("biPlanes", ctypes.c_uint16),
                ("biBitCount", ctypes.c_uint16), ("biCompression", ctypes.c_uint32),
                ("biSizeImage", ctypes.c_uint32), ("biXPelsPerMeter", ctypes.c_long),
                ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", ctypes.c_uint32),
                ("biClrImportant", ctypes.c_uint32)]


def pencere_icerik_bgr(hwnd):
    """PrintWindow ile pencere icerigini BGR ndarray (H,W,3) doner.
    Basarisiz veya tumu-siyah icerik -> None (cagiran mss'e duser)."""
    import ctypes
    import numpy as np
    try:
        u32, g32 = ctypes.windll.user32, ctypes.windll.gdi32
        r = (ctypes.c_long * 4)()
        if not u32.GetClientRect(int(hwnd), ctypes.byref(r)):
            return None
        w, h = int(r[2] - r[0]), int(r[3] - r[1])
        if w < 64 or h < 64:
            return None
        wdc = u32.GetDC(int(hwnd))
        if not wdc:
            return None
        mdc = g32.CreateCompatibleDC(wdc)
        bmp = g32.CreateCompatibleBitmap(wdc, w, h)
        eski = g32.SelectObject(mdc, bmp)
        try:
            if not u32.PrintWindow(int(hwnd), mdc, 3):   # 1|2: CLIENTONLY|RENDERFULLCONTENT
                return None
            bi = _BMIH()
            bi.biSize = ctypes.sizeof(_BMIH)
            bi.biWidth = w
            bi.biHeight = -h                             # negatif: satirlar yukaridan asagi
            bi.biPlanes = 1
            bi.biBitCount = 32
            bi.biCompression = 0                         # BI_RGB
            buf = ctypes.create_string_buffer(w * h * 4)
            if g32.GetDIBits(mdc, bmp, 0, h, buf, ctypes.byref(bi), 0) != h:
                return None
            fr = np.frombuffer(buf, dtype=np.uint8).reshape(h, w, 4)[:, :, :3]
            if float(fr.std()) < 1.0:                    # tumu siyah/tek renk -> icerik yok
                return None
            return fr.copy()
        finally:
            g32.SelectObject(mdc, eski)
            g32.DeleteObject(bmp)
            g32.DeleteDC(mdc)
            u32.ReleaseDC(int(hwnd), wdc)
    except Exception:
        return None


class PencereYakala:
    def __init__(self, title_hints=None, window_name=None, window_hwnd=None):
        """title_hints: baslik ipuclari; window_name: tam baslik; window_hwnd: pencere handle."""
        self.title_hints = [h.lower() for h in (title_hints or [])]
        self.window_name = window_name
        self.window_hwnd = window_hwnd
        self.hazir = False
        self.aktif_pencere = None
        self._latest = None
        self._lock = threading.Lock()
        self._baslat_lock = threading.Lock()   # baslat() cift-cagri yarisini onler
        self._control = None
        # WATCHDOG durumu (bayat-kare / yanlis-pencere yeniden baglama)
        self._latest_t = 0.0      # son kare geldigi an; 0 = hic kare gelmedi
        self._baglama_t = 0.0     # yakalama basladigi an
        self._bagli_hwnd = None   # su an bagli oldugumuz pencere handle'i
        try:
            from windows_capture import WindowsCapture
            self._WindowsCapture = WindowsCapture
            self.hazir = True
        except Exception as e:
            print("[PENCERE_YAKALA] windows-capture yok (%s); mss fallback kullanilacak." % e)

    def calisiyor(self):
        return self._control is not None

    def baslat(self):
        """Yakalamayi baslatir (non-blocking). Zaten calisyorsa True; hata olursa False.
        Kilit + cift-kontrol ile tek capture acilir."""
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
            # Oyun penceresi bulunamadi: ~10 sn'de bir bilgilendir (spam yok).
            import time as _t
            simdi = _t.monotonic()
            if simdi - getattr(self, "_son_uyari_t", 0.0) > 10.0:
                self._son_uyari_t = simdi
                print("[PENCERE_YAKALA] Oyun penceresi bulunamadi (DronesOfWar surecine ait "
                      "gorunur pencere yok). Oyun acik ve PLAY modunda mi? -> server mss'e duser.")
            return False

        # Hedef (hwnd/ad) x yakalama ayarlari kombinasyonlari. Iki WGC ayarinin build
        # gereksinimi farkli (cursor_capture 19041+, draw_border 22000+); LTSC 19044'te
        # ideal set duserse cursor-only ara sete, en son varsayilana inilir.
        hedefler = []
        if hwnd:
            hedefler.append(("hwnd", dict(window_hwnd=int(hwnd))))
        if ad:
            hedefler.append(("ad", dict(window_name=ad)))
        ayar_setleri = [dict(cursor_capture=False, draw_border=False),  # Win11/Server2022+: imlec+kenar kapali
                        dict(cursor_capture=False),                     # LTSC 19044: yalniz imlec kapali
                        dict(cursor_capture=None, draw_border=None)]     # son care: varsayilan (imlec acik)
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
                        self._latest_t = time.monotonic()   # WATCHDOG: taze kare damgasi
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
                    self._bagli_hwnd = hwnd
                    self._baglama_t = time.monotonic()
                    self._latest_t = 0.0                    # ilk kareyi bekle
                    print("[PENCERE_YAKALA] yakalama basladi: %s" % self.aktif_pencere)
                    return True
                except Exception as e:
                    son_hata = "baslatma(%s): %s" % (yontem, e)
                    self._control = None

        # Tum kombinasyonlar basarisiz: ~10 sn'de bir raporla.
        import time as _t
        simdi = _t.monotonic()
        if simdi - getattr(self, "_son_uyari_t", 0.0) > 10.0:
            self._son_uyari_t = simdi
            print("[PENCERE_YAKALA] baslatilamadi (%s) -> mss fallback." % son_hata)
        return False

    def durdur(self):
        c = self._control
        self._control = None
        self._latest_t = 0.0
        self._bagli_hwnd = None
        with self._lock:
            self._latest = None
        if c is not None:
            try:
                c.stop()
            except Exception:
                pass

    def yeniden_baglanmali(self, stale_s=2.0):
        """WATCHDOG: yakalama 'calisyor' gorunuyor ama gercekte bozuk mu?
        True = yeniden baglan (durdur+baslat ile taze pencereye)."""
        if self._control is None:
            return False
        simdi = time.monotonic()
        # (a) kare geldi ama bayatladi
        if self._latest_t > 0.0 and (simdi - self._latest_t) > stale_s:
            return True
        # (b) baglandi ama hic kare gelmedi (yanlis/gorunmez pencere)
        if self._latest_t == 0.0 and self._baglama_t > 0.0 and (simdi - self._baglama_t) > stale_s:
            return True
        # (c) bagli oldugumuz pencere artik gecerli oyun penceresi degil (handle degisti)
        if self.window_name is None and self.window_hwnd is None and self._bagli_hwnd is not None:
            try:
                _, hwnd = pencere_bul(self.title_hints)
                if hwnd is not None and int(hwnd) != int(self._bagli_hwnd):
                    return True
            except Exception:
                pass
        return False

    def get_latest_bgr(self):
        with self._lock:
            return self._latest

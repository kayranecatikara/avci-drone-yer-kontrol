# -*- coding: utf-8 -*-
"""
================================================================================
  GIRIS KAYDET / OYNAT  --  kullanicinin yaptigi tus+fare dizisini ogren ve tekrarla
================================================================================
NEDEN
--------------------------------------------------------------------------------
Oyunun BASLIK ekrani ("PRESS FOR START") sentetik klavye/fare girdisini kabul
etmiyor. 2026-08-17 gecesi 30'dan fazla tus, uzun basma, tek/cift tik denendi --
hicbiri gecmedi. Ama GOREV ICINDE klavye calisiyor (E ile drone doguyor).
Kor tahmin yerine: kullanici bir kez yapar, biz kaydeder ve birebir tekrarlariz.

KULLANIM
    1) python arac/giris_kaydet.py --kaydet baslangic
       -> kullanici oyunu acar ve gorevin basladigi ana kadar ne yapiyorsa yapar
       -> ESC'e UC KEZ ust uste basinca kayit biter (ya da --sure dolunca)
    2) python arac/giris_kaydet.py --oynat baslangic
       -> ayni diziyi birebir tekrarlar

⚠ KOORDINAT: fare konumu hem MUTLAK hem de OYUN PENCERESINE GORE ORANLI
   kaydedilir. Oynatirken pencere farkli yerde/boyutta olsa bile oranli konum
   kullanilir -> pencere tasinsa da calisir.

⚠ SIFRE/KISISEL VERI: bu arac TUM tuslari kaydeder. Kayit sirasinda sifre
   yazma. Kayit dosyasi veri/gece/giris/<ad>.json icinde duz metindir.
================================================================================
"""
import os
import sys
import json
import time
import ctypes
import argparse
from ctypes import wintypes

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CIK = os.path.join(KOK, "veri", "gece", "giris")

u32 = ctypes.WinDLL("user32", use_last_error=True)

# İzlenen tuşlar: harf/rakam + yaygın kontrol tuşları
VK_ADLARI = {}
for c in range(0x30, 0x5B):                     # 0-9, A-Z
    VK_ADLARI[c] = chr(c)
VK_ADLARI.update({
    0x01: "MOUSE_L", 0x02: "MOUSE_R", 0x04: "MOUSE_M",
    0x08: "BACKSPACE", 0x09: "TAB", 0x0D: "ENTER", 0x10: "SHIFT",
    0x11: "CTRL", 0x12: "ALT", 0x13: "PAUSE", 0x14: "CAPS", 0x1B: "ESC",
    0x20: "SPACE", 0x21: "PGUP", 0x22: "PGDN", 0x23: "END", 0x24: "HOME",
    0x25: "LEFT", 0x26: "UP", 0x27: "RIGHT", 0x28: "DOWN",
    0x2D: "INSERT", 0x2E: "DELETE",
    0x60: "NUM0", 0x61: "NUM1", 0x62: "NUM2", 0x63: "NUM3", 0x64: "NUM4",
    0x65: "NUM5", 0x66: "NUM6", 0x67: "NUM7", 0x68: "NUM8", 0x69: "NUM9",
    0x6D: "NUM_MINUS", 0x6B: "NUM_PLUS",
    0x70: "F1", 0x71: "F2", 0x72: "F3", 0x73: "F4", 0x74: "F5", 0x75: "F6",
    0x76: "F7", 0x77: "F8", 0x78: "F9", 0x79: "F10", 0x7A: "F11", 0x7B: "F12",
    0xA0: "LSHIFT", 0xA1: "RSHIFT", 0xA2: "LCTRL", 0xA3: "RCTRL",
    0xA4: "LALT", 0xA5: "RALT",
})
FARE_VK = {0x01, 0x02, 0x04}
# Oynatirken ASLA gonderilmeyecek tuslar: ALT (F4 ile pencere kapatir),
# F4, Windows tuslari, Ctrl (Ctrl+W/Ctrl+C gibi kazalar).
_TEHLIKELI = {0x12, 0xA4, 0xA5, 0x73, 0x5B, 0x5C, 0x11, 0xA2, 0xA3}


class RECT(ctypes.Structure):
    _fields_ = [("l", ctypes.c_long), ("t", ctypes.c_long),
                ("r", ctypes.c_long), ("b", ctypes.c_long)]


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def oyun_penceresi():
    bulunan = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def gez(h, _):
        n = u32.GetWindowTextLengthW(h)
        if n:
            b = ctypes.create_unicode_buffer(n + 1)
            u32.GetWindowTextW(h, b, n + 1)
            if "DronesOfWar" in b.value and u32.IsWindowVisible(h):
                bulunan.append(h)
        return True

    u32.EnumWindows(gez, 0)
    return bulunan[0] if bulunan else None


def pencere_kutu(h):
    r = RECT()
    if h and u32.GetWindowRect(h, ctypes.byref(r)):
        return r.l, r.t, r.r, r.b
    return None


def fare_konum():
    p = POINT()
    u32.GetCursorPos(ctypes.byref(p))
    return p.x, p.y


def basili(vk):
    return bool(u32.GetAsyncKeyState(vk) & 0x8000)


# ─────────────────────────────────────────────────────────────────────────
#  KAYIT
# ─────────────────────────────────────────────────────────────────────────
def _port_acik(port=12345):
    import socket
    try:
        s = socket.create_connection(("127.0.0.1", port), timeout=0.4)
        s.close()
        return True
    except Exception:
        return False


def kaydet(ad, sure_s, hz=100.0):
    os.makedirs(CIK, exist_ok=True)
    yol = os.path.join(CIK, ad + ".json")
    izle = list(VK_ADLARI.keys())
    onceki = {vk: False for vk in izle}
    olaylar = []
    t0 = time.perf_counter()
    periyot = 1.0 / hz
    esc_dizi = []
    son_fare = None

    print("=" * 66)
    print("  KAYIT BASLADI  ->  %s" % yol)
    print("  Simdi OYUNDA ne yapiyorsan yap (tiklama + tus).")
    print("  BITIRMEK ICIN: ESC'e ard arda UC KEZ bas  (ya da %.0f s bekle)" % sure_s)
    print("  ⚠ Kayit sirasinda SIFRE yazma -- her tus duz metin kaydedilir.")
    print("=" * 66, flush=True)

    while time.perf_counter() - t0 < sure_s:
        dongu = time.perf_counter()
        t = dongu - t0
        h = oyun_penceresi()
        kutu = pencere_kutu(h)

        for vk in izle:
            s = basili(vk)
            if s == onceki[vk]:
                continue
            onceki[vk] = s
            ad_t = VK_ADLARI.get(vk, "VK_%02X" % vk)
            o = {"t": round(t, 3), "tur": "fare" if vk in FARE_VK else "tus",
                 "vk": vk, "ad": ad_t, "bas": bool(s)}
            if vk in FARE_VK:
                x, y = fare_konum()
                o["x"], o["y"] = x, y
                if kutu:
                    L, T, R, B = kutu
                    o["ox"] = round((x - L) / max(R - L, 1), 4)
                    o["oy"] = round((y - T) / max(B - T, 1), 4)
            olaylar.append(o)
            print("  %6.2f s  %-9s %-10s %s" % (t, o["tur"], ad_t,
                                                "BASILDI" if s else "birakildi"),
                  flush=True)
            if ad_t == "ESC" and s:
                esc_dizi.append(t)
                esc_dizi = [x for x in esc_dizi if t - x < 2.0]
                if len(esc_dizi) >= 3:
                    print("\n  ESC x3 -> kayit bitiriliyor.")
                    t0 -= sure_s                      # dongudan cik
                    break

        # fare hareketi: yalniz belirgin degisimde ve seyrek
        x, y = fare_konum()
        if son_fare is None or abs(x - son_fare[0]) + abs(y - son_fare[1]) > 25:
            o = {"t": round(t, 3), "tur": "hareket", "x": x, "y": y}
            if kutu:
                L, T, R, B = kutu
                o["ox"] = round((x - L) / max(R - L, 1), 4)
                o["oy"] = round((y - T) / max(B - T, 1), 4)
            olaylar.append(o)
            son_fare = (x, y)

        # ⚠ EN IYI BITIS SINYALI: SDK portu acildi = gorev basladi.
        #   Kayit tam o anda biter -> dizi kendiliginden "gereken kadar" olur.
        #   (ESC x3 elle bitisi de calisir, yedek olarak duruyor.)
        if int(t * 4) != int((t - periyot) * 4):        # ~4 Hz kontrol
            if _port_acik():
                print("\n  ✓ SDK portu ACILDI (%.1f s) -> gorev basladi, "
                      "kayit bitiyor." % t)
                break

        kal = periyot - (time.perf_counter() - dongu)
        if kal > 0:
            time.sleep(kal)

    kutu = pencere_kutu(oyun_penceresi())
    with open(yol, "w", encoding="utf-8") as f:
        json.dump({"ad": ad, "sure_s": round(time.perf_counter() - t0, 2),
                   "pencere": kutu, "olaylar": olaylar}, f,
                  ensure_ascii=False, indent=1)
    tus = sum(1 for o in olaylar if o["tur"] == "tus")
    fare = sum(1 for o in olaylar if o["tur"] == "fare")
    hrk = sum(1 for o in olaylar if o["tur"] == "hareket")
    print("\n  KAYDEDILDI: %d tus olayi, %d fare tiklamasi, %d hareket -> %s"
          % (tus, fare, hrk, yol))
    return yol


# ─────────────────────────────────────────────────────────────────────────
#  OYNAT
# ─────────────────────────────────────────────────────────────────────────
def _one_al(h):
    """Pencereyi one al ve DOGRULA (AttachThreadInput; duz cagri sessizce basarisiz olur)."""
    if not h:
        return False
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    if u32.IsIconic(h):
        u32.ShowWindow(h, 9)
        time.sleep(0.3)
    u32.SetForegroundWindow(h)
    time.sleep(0.2)
    if u32.GetForegroundWindow() == h:
        return True
    hedef = u32.GetWindowThreadProcessId(h, None)
    benim = k32.GetCurrentThreadId()
    onp = u32.GetForegroundWindow()
    onp_th = u32.GetWindowThreadProcessId(onp, None) if onp else 0
    for th in {hedef, onp_th} - {0, benim}:
        u32.AttachThreadInput(benim, th, True)
    try:
        u32.ShowWindow(h, 5)
        u32.BringWindowToTop(h)
        u32.SetForegroundWindow(h)
        time.sleep(0.3)
    finally:
        for th in {hedef, onp_th} - {0, benim}:
            u32.AttachThreadInput(benim, th, False)
    return u32.GetForegroundWindow() == h


def oynat(ad, hiz=1.0, bekle_port=True):
    yol = os.path.join(CIK, ad + ".json")
    with open(yol, encoding="utf-8") as f:
        K = json.load(f)
    olaylar = K["olaylar"]
    print("  OYNATILIYOR: %s  (%d olay, %.1f s)" % (yol, len(olaylar), K["sure_s"]))

    h = oyun_penceresi()
    if not _one_al(h):
        print("  ⚠ oyun penceresi one alinamadi -> IPTAL (tuslar baska yere gitmesin)")
        return False
    kutu = pencere_kutu(h)
    L, T, R, B = kutu if kutu else (0, 0, 1920, 1080)

    KEYUP = 0x0002
    FARE = {0x01: (0x0002, 0x0004), 0x02: (0x0008, 0x0010), 0x04: (0x0020, 0x0040)}
    t0 = time.perf_counter()
    for o in olaylar:
        hedef_t = o["t"] / max(hiz, 1e-3)
        kal = hedef_t - (time.perf_counter() - t0)
        if kal > 0:
            time.sleep(kal)
        if o["tur"] == "hareket":
            x = int(L + o.get("ox", 0.5) * (R - L)) if "ox" in o else o["x"]
            y = int(T + o.get("oy", 0.5) * (B - T)) if "oy" in o else o["y"]
            u32.SetCursorPos(x, y)
        elif o["tur"] == "fare":
            x = int(L + o.get("ox", 0.5) * (R - L)) if "ox" in o else o["x"]
            y = int(T + o.get("oy", 0.5) * (B - T)) if "oy" in o else o["y"]
            u32.SetCursorPos(x, y)
            time.sleep(0.02)
            asagi, yukari = FARE.get(o["vk"], (0x0002, 0x0004))
            u32.mouse_event(asagi if o["bas"] else yukari, 0, 0, 0, 0)
        else:
            # ⚠ TEHLIKELI TUS ELEME: ilk kayitta ALT+F4 vardi (kullanici bir
            #   pencere kapatmis). Korukorune tekrar oynatmak oyunu ya da baska
            #   bir uygulamayi KAPATIRDI. ALT/F4 ve Windows tuslari atlanir.
            if o["vk"] in _TEHLIKELI:
                continue
            # ⚠ keybd_event: SendInput bu oyunda YUTULUYOR, eski API calisiyor
            #   (2026-08-17 olculdu: dort yontemden yalniz bu port acti)
            u32.keybd_event(o["vk"], 0, 0 if o["bas"] else KEYUP, 0)
    print("  oynatma bitti (%.1f s)" % (time.perf_counter() - t0))

    if bekle_port:
        import socket
        for _ in range(20):
            try:
                s = socket.create_connection(("127.0.0.1", 12345), timeout=1.0)
                s.close()
                print("  ✓ SDK portu ACILDI -> oyun gorevde")
                return True
            except Exception:
                time.sleep(1.5)
        print("  ⚠ SDK portu acilmadi")
        return False
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kaydet", metavar="AD")
    ap.add_argument("--oynat", metavar="AD")
    ap.add_argument("--sure", type=float, default=180.0)
    ap.add_argument("--hiz", type=float, default=1.0)
    ap.add_argument("--liste", action="store_true")
    a = ap.parse_args()
    if a.liste:
        os.makedirs(CIK, exist_ok=True)
        for f in sorted(os.listdir(CIK)):
            if f.endswith(".json"):
                d = json.load(open(os.path.join(CIK, f), encoding="utf-8"))
                print("  %-20s %5.1f s  %d olay" % (f[:-5], d["sure_s"], len(d["olaylar"])))
        return
    if a.kaydet:
        kaydet(a.kaydet, a.sure)
    elif a.oynat:
        oynat(a.oynat, a.hiz)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()

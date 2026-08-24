# -*- coding: utf-8 -*-
"""
================================================================================
  GECE TEZGAHI  --  gozetimsiz kosu, otomatik respawn, kosu basina puanlama
================================================================================
NEDEN
--------------------------------------------------------------------------------
"Bazen sans eseri vuruyor" iddiasini ELEMEK icin tek yol: AYNI ayarla COK kosu
yapip vurus oranini olcmek. Tek vurus kanit degildir. Bu tezgah geceyi
gozetimsiz cevirir ve her kosuyu ayni sekilde puanlar.

RESPAWN IMZASI  (2026-08-16, 202186 satirlik gercek kayittan OLCULDU)
--------------------------------------------------------------------------------
Aracimiz olunce/vurunca oyun bizi DOGUM NOKTASINA isinliyor:
    tek tikta >40 m sicrama  VE  yeni irtifa ~49.1 m
Olculen 4 olay: t+66.8 (gorev basi), t+5522.9, t+6224.4, t+6303.5.
Son ikisinde sicrama anindaki menzil 1.4 m idi -> VURUS.
Digerlerinde menzil 81-219 m idi -> gorev basi / dusme.

    SINIFLANDIRMA:  sicrama anindaki menzil < VURUS_MENZIL_M  ->  VURUS
                    degilse                                   ->  OLUM/RESET

⚠ 3 m'nin altina inmek VURUS DEGILDIR. Olculdu: 10016 s'de 57 ayri "3 m alti"
   olayi oldu ama YALNIZ 2'si respawn uretti. Yani oyunun carpisma hacmi cok
   dar (~1.5 m). Puanlamada TEK gecerli vurus olcutu respawn'dir.

KLAVYE
--------------------------------------------------------------------------------
Bazi olumlerde oyun 'E' bekliyor. Tezgah oyun penceresini one alip SendInput ile
'E' basar. --tus-yok ile kapatilir (once gozlemle, sonra ac).

CALISTIR
    python arac/gece_tezgahi.py --izle                 # yalniz gozlemle, mudahale YOK
    python arac/gece_tezgahi.py --kampanya recete.json # ayar suepuerup kosu yapar
    python arac/gece_tezgahi.py --kosu 40              # tek ayar, 40 kosu

CIKTI
    veri/gece/kosular.csv        her kosu bir satir (puanlama)
    veri/gece/iz_<damga>.csv     her kosunun tik tik izi (10 Hz)
    veri/gece/olaylar.log        insan okur gunluk
================================================================================
"""
import os
import sys
import csv
import json
import time
import math
import argparse
import urllib.request

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CIK = os.path.join(KOK, "veri", "gece")
SUNUCU = "http://127.0.0.1:8000"

DOGUM_IRTIFA_M = 49.1      # olculdu; respawn bu irtifaya isinliyor
DOGUM_TOLERANS = 3.0
SICRAMA_M = 40.0           # tek tikta bundan buyuk yer degistirme = isinlanma
VURUS_MENZIL_M = 6.0       # sicrama aninda hedefe bu kadar yakinsak VURUS sayilir
TIK_HZ = 10.0


# ─────────────────────────────────────────────────────────────────────────
#  SUNUCU
# ─────────────────────────────────────────────────────────────────────────
def _get(yol, zaman=4.0):
    with urllib.request.urlopen(SUNUCU + yol, timeout=zaman) as r:
        return json.loads(r.read().decode("utf-8"))


def _post(yol, govde, zaman=6.0):
    d = json.dumps(govde).encode("utf-8")
    q = urllib.request.Request(SUNUCU + yol, data=d,
                               headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(q, timeout=zaman) as r:
        return json.loads(r.read().decode("utf-8"))


def telemetri():
    return _get("/api/telemetry")


def gorev_baslat():
    return _post("/api/command", {"cmd": "start_gercek"})


def gorev_durdur():
    return _post("/api/command", {"cmd": "stop"})


def mod_ayarla(m):
    return _post("/api/command", {"cmd": "vismode", "mode": m})


def ayar_yaz(anahtar, deger):
    """Canli ayar. /api/gudum_ozellikleri POST sozlesmesi sunucudan okunur."""
    return _post("/api/gudum_ozellikleri", {"anahtar": anahtar, "deger": deger})


def ayar_oku():
    d = _get("/api/gudum_ozellikleri")
    return {x["anahtar"]: x["deger"] for x in d.get("liste", [])}


# ─────────────────────────────────────────────────────────────────────────
#  KLAVYE  (oyun penceresine 'E')
# ─────────────────────────────────────────────────────────────────────────
def _tus_gonder(harf="e"):
    """Oyun penceresini one al ve SendInput ile bas. Hata durumunda False."""
    try:
        import ctypes
        from ctypes import wintypes
        u32 = ctypes.WinDLL("user32", use_last_error=True)

        hedef = []

        @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        def gez(h, _):
            n = u32.GetWindowTextLengthW(h)
            if n:
                b = ctypes.create_unicode_buffer(n + 1)
                u32.GetWindowTextW(h, b, n + 1)
                if "DronesOfWar" in b.value and u32.IsWindowVisible(h):
                    hedef.append(h)
            return True

        u32.EnumWindows(gez, 0)
        if not hedef:
            return False
        h = hedef[0]
        if u32.IsIconic(h):
            u32.ShowWindow(h, 9)              # SW_RESTORE
        u32.SetForegroundWindow(h)
        time.sleep(0.25)

        # SendInput: scancode ile (oyunlar RawInput okur, PostMessage yutulur)
        KEYEVENTF_SCANCODE = 0x0008
        KEYEVENTF_KEYUP = 0x0002
        SC = {"e": 0x12, "r": 0x13}.get(harf, 0x12)

        class KEYBDINPUT(ctypes.Structure):
            _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                        ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]

        class INPUT(ctypes.Structure):
            class _U(ctypes.Union):
                _fields_ = [("ki", KEYBDINPUT)]
            _anonymous_ = ("u",)
            _fields_ = [("type", wintypes.DWORD), ("u", _U)]

        def bas(yukari):
            i = INPUT()
            i.type = 1                        # INPUT_KEYBOARD
            i.ki = KEYBDINPUT(0, SC, KEYEVENTF_SCANCODE | (KEYEVENTF_KEYUP if yukari else 0),
                              0, None)
            u32.SendInput(1, ctypes.byref(i), ctypes.sizeof(INPUT))

        bas(False)
        time.sleep(0.06)
        bas(True)
        return True
    except Exception as e:
        gunluk("[TUS] gonderilemedi: %r" % (e,))
        return False


# ─────────────────────────────────────────────────────────────────────────
#  GUNLUK
# ─────────────────────────────────────────────────────────────────────────
_gl = None


def gunluk(s):
    global _gl
    os.makedirs(CIK, exist_ok=True)
    if _gl is None:
        _gl = open(os.path.join(CIK, "olaylar.log"), "a", encoding="utf-8")
    z = time.strftime("%H:%M:%S")
    print("%s %s" % (z, s), flush=True)
    _gl.write("%s %s\n" % (z, s))
    _gl.flush()


# ─────────────────────────────────────────────────────────────────────────
#  TIK  --  telemetriden tek satirlik durum
# ─────────────────────────────────────────────────────────────────────────
def durum_al():
    t = telemetri()
    d, h = t["drone"], t["target"]
    g, gd, gv = t["gorsel"], t["gudum"], t["gorev"]
    hb = gd.get("hibrit", {}) or {}
    ak = hb.get("akis", {}) or {}
    ts = g.get("tespit") or {}
    dbg = (t.get("debug") or {})
    hr = dbg.get("target_real") or {}
    # hedefin GERCEK konumu (bozulmamis) varsa onu kullan
    hx = hr.get("x", h.get("x"))
    hy = hr.get("y", h.get("y"))
    hz = hr.get("z", h.get("z"))
    dx, dy, dz = d["x"], d["y"], d["z"]
    men = math.dist((hx, hy, hz), (dx, dy, dz)) if None not in (hx, hy, hz) else float("nan")
    return {
        "t": time.perf_counter(), "t_duvar": time.time(),
        "dx": dx, "dy": dy, "dz": dz,
        "d_irtifa": d.get("altitude_m"), "d_hiz": d.get("speed_ms"),
        "d_roll": d.get("roll"), "d_pitch": d.get("pitch"), "d_yaw": d.get("yaw"),
        "hx": hx, "hy": hy, "hz": hz, "h_hiz": h.get("speed_ms"),
        "menzil": men,
        "irtifa_farki": (dz - hz) if None not in (dz, hz) else float("nan"),
        "faz": hb.get("faz"), "gecis": hb.get("gecis_sayisi"),
        "kilit": hb.get("kilit_sayac"), "durum": gd.get("durum"),
        "mod": gd.get("mod"), "kaynak": gd.get("kaynak"),
        "tespit": bool(ts.get("tespit_mi")), "conf": ts.get("conf"),
        "kutu_w": (ts.get("w") or 0) * 1920, "kutu_h": (ts.get("h") or 0) * 1080,
        "kopru": bool(g.get("kopru")),
        "tespit_orani": ak.get("tespit_orani"), "akis_hz": ak.get("hz"),
        "det_ms": (g.get("perf") or {}).get("det_ms"),
        "fps": (g.get("perf") or {}).get("fps"),
        "vurus": bool(gv.get("vurus")), "en_yakin": gv.get("en_yakin_m"),
        "gorev_aktif": bool(t.get("gorev_aktif")),
    }


IZ_ALAN = ["t", "t_duvar", "dx", "dy", "dz", "d_irtifa", "d_hiz", "d_roll", "d_pitch",
           "d_yaw", "hx", "hy", "hz", "h_hiz", "menzil", "irtifa_farki", "faz", "gecis",
           "kilit", "durum", "mod", "tespit", "conf", "kutu_w", "kutu_h", "kopru",
           "tespit_orani", "akis_hz", "det_ms", "fps", "vurus", "en_yakin"]


# ─────────────────────────────────────────────────────────────────────────
#  KOSU  --  bir respawn'dan digerine
# ─────────────────────────────────────────────────────────────────────────
class Kosu:
    """Bir respawn'dan sonrakine kadar gecen sureyi biriktirir ve puanlar."""

    def __init__(self, no, ayar_adi, iz_yaz):
        self.no = no
        self.ayar = ayar_adi
        self.iz = iz_yaz
        self.t0 = time.perf_counter()
        self.n = 0
        self.en_yakin = float("inf")
        self.en_yakin_t = None
        self.en_uzun_kilit = 0.0
        self.kilit_max = 0.0
        self.tespitli = 0
        self.koprulu = 0
        self.gorsel_tik = 0
        self.irtifa_min = float("inf")
        self.irtifa_farki_top = 0.0
        self.men_top = 0.0
        self.alt3 = 0
        self.alt5 = 0
        self.alt10 = 0
        self.det_ms = []
        self.fps = []
        self.son = None

    def ekle(self, s):
        self.n += 1
        self.son = s
        if self.iz:
            self.iz.writerow([s.get(k) for k in IZ_ALAN])
        m = s["menzil"]
        if m == m:                                  # NaN degil
            if m < self.en_yakin:
                self.en_yakin = m
                self.en_yakin_t = s["t"] - self.t0
            self.men_top += m
            self.alt3 += (m < 3.0)
            self.alt5 += (m < 5.0)
            self.alt10 += (m < 10.0)
        if s["tespit"]:
            self.tespitli += 1
        if s["kopru"]:
            self.koprulu += 1
        if str(s["faz"]).startswith("VIS"):
            self.gorsel_tik += 1
        k = s.get("kilit")
        if k is not None:
            self.kilit_max = max(self.kilit_max, float(k))
        if s.get("d_irtifa") is not None:
            self.irtifa_min = min(self.irtifa_min, float(s["d_irtifa"]))
        if s.get("irtifa_farki") == s.get("irtifa_farki"):
            self.irtifa_farki_top += s["irtifa_farki"]
        if s.get("det_ms"):
            self.det_ms.append(float(s["det_ms"]))
        if s.get("fps"):
            self.fps.append(float(s["fps"]))

    def puanla(self, sonuc, sicrama_menzil):
        o = lambda a, b: (a / b) if b else 0.0
        med = lambda v: (sorted(v)[len(v) // 2] if v else None)
        return {
            "kosu": self.no, "ayar": self.ayar, "sonuc": sonuc,
            "sure_s": round(time.perf_counter() - self.t0, 2),
            "tik": self.n,
            "sicrama_menzil_m": (round(sicrama_menzil, 2)
                                 if sicrama_menzil == sicrama_menzil else ""),
            "en_yakin_m": round(self.en_yakin, 2) if self.en_yakin < 1e8 else "",
            "en_yakin_t_s": round(self.en_yakin_t, 2) if self.en_yakin_t else "",
            "kilit_max_s": round(self.kilit_max, 2),
            "ort_menzil_m": round(o(self.men_top, self.n), 1),
            "alt3_%": round(100 * o(self.alt3, self.n), 1),
            "alt5_%": round(100 * o(self.alt5, self.n), 1),
            "alt10_%": round(100 * o(self.alt10, self.n), 1),
            "tespit_%": round(100 * o(self.tespitli, self.n), 1),
            "kopru_%": round(100 * o(self.koprulu, self.n), 1),
            "gorsel_%": round(100 * o(self.gorsel_tik, self.n), 1),
            "irtifa_min_m": round(self.irtifa_min, 1) if self.irtifa_min < 1e8 else "",
            "irtifa_farki_ort_m": round(o(self.irtifa_farki_top, self.n), 2),
            "det_ms_med": med(self.det_ms), "fps_med": med(self.fps),
            "damga": time.strftime("%Y-%m-%d %H:%M:%S"),
        }


PUAN_ALAN = ["kosu", "ayar", "sonuc", "sure_s", "tik", "sicrama_menzil_m", "en_yakin_m",
             "en_yakin_t_s", "kilit_max_s", "ort_menzil_m", "alt3_%", "alt5_%", "alt10_%",
             "tespit_%", "kopru_%", "gorsel_%", "irtifa_min_m", "irtifa_farki_ort_m",
             "det_ms_med", "fps_med", "damga"]


# ─────────────────────────────────────────────────────────────────────────
#  ANA DONGU
# ─────────────────────────────────────────────────────────────────────────
def dongu(a):
    os.makedirs(CIK, exist_ok=True)
    puan_yol = os.path.join(CIK, "kosular.csv")
    yeni = not os.path.exists(puan_yol)
    pf = open(puan_yol, "a", newline="", encoding="utf-8")
    pw = csv.writer(pf)
    if yeni:
        pw.writerow(PUAN_ALAN)
        pf.flush()

    damga = time.strftime("%Y%m%d_%H%M%S")
    izf = open(os.path.join(CIK, "iz_%s.csv" % damga), "w", newline="", encoding="utf-8")
    izw = csv.writer(izf)
    izw.writerow(["kosu", "ayar"] + IZ_ALAN)

    class IzYaz:
        def __init__(self):
            self.kosu = 0
            self.ayar = ""

        def writerow(self, r):
            izw.writerow([self.kosu, self.ayar] + r)
    izy = IzYaz()

    gunluk("=" * 70)
    gunluk("GECE TEZGAHI basladi | izle=%s tus=%s hedef kosu=%s"
           % (a.izle, not a.tus_yok, a.kosu))
    try:
        gunluk("mevcut ayarlar: %s" % json.dumps(ayar_oku(), ensure_ascii=False))
    except Exception as e:
        gunluk("ayar okunamadi: %r" % (e,))

    onceki = None
    kosu_no = 0
    kosu = None
    periyot = 1.0 / TIK_HZ
    son_yaz = 0.0
    bitti = 0

    while True:
        t_dongu = time.perf_counter()
        try:
            s = durum_al()
        except Exception as e:
            gunluk("telemetri hatasi: %r" % (e,))
            time.sleep(1.0)
            continue

        # ── ISINLANMA TESPITI ────────────────────────────────────────────
        sicradi = False
        sic_men = float("nan")
        if onceki is not None:
            adim = math.dist((s["dx"], s["dy"], s["dz"]),
                             (onceki["dx"], onceki["dy"], onceki["dz"]))
            dogum = (s["dz"] is not None and
                     abs(s["dz"] - DOGUM_IRTIFA_M) < DOGUM_TOLERANS)
            if adim > SICRAMA_M and dogum:
                sicradi = True
                sic_men = onceki["menzil"]

        if sicradi:
            sonuc = "VURUS" if (sic_men == sic_men and sic_men < VURUS_MENZIL_M) else "OLUM"
            if kosu is not None and kosu.n > 20:
                p = kosu.puanla(sonuc, sic_men)
                pw.writerow([p.get(k, "") for k in PUAN_ALAN])
                pf.flush()
                izf.flush()
                bitti += 1
                gunluk("KOSU %-4d %-6s | sicrama menzili %6s m | en yakin %5s m | "
                       "kilit_max %4.1f s | tespit %%%.0f | kopru %%%.0f | "
                       "irtifa farki %+.1f m | fps %s | sure %.0f s"
                       % (p["kosu"], sonuc, p["sicrama_menzil_m"], p["en_yakin_m"],
                          p["kilit_max_s"], p["tespit_%"], p["kopru_%"],
                          p["irtifa_farki_ort_m"], p["fps_med"], p["sure_s"]))
            else:
                gunluk("isinlanma (kosu cok kisa, puanlanmadi) menzil=%s" % sic_men)

            if a.kosu and bitti >= a.kosu:
                gunluk("hedef kosu sayisina ulasildi (%d). Bitiriliyor." % bitti)
                break

            # ── MUDAHALE ────────────────────────────────────────────────
            if not a.izle:
                if not a.tus_yok:
                    ok = _tus_gonder("e")
                    gunluk("  respawn icin 'E' gonderildi: %s" % ok)
                time.sleep(1.2)
                try:
                    gorev_baslat()
                    gunluk("  gorev yeniden baslatildi")
                except Exception as e:
                    gunluk("  gorev baslatilamadi: %r" % (e,))
                time.sleep(1.5)

            kosu_no += 1
            izy.kosu = kosu_no
            kosu = Kosu(kosu_no, izy.ayar, izy)
            onceki = None
            continue

        if kosu is None:
            kosu_no += 1
            izy.kosu = kosu_no
            kosu = Kosu(kosu_no, izy.ayar, izy)
            gunluk("KOSU %d basladi (menzil %.1f m, irtifa %.1f m)"
                   % (kosu_no, s["menzil"], s["dz"] or 0))

        kosu.ekle(s)
        onceki = s

        # 30 saniyede bir kisa nabiz
        if time.perf_counter() - son_yaz > 30.0:
            son_yaz = time.perf_counter()
            gunluk("  ... kosu %d | %5.1f m | faz %-4s | kilit %4.1f | tespit %s | "
                   "irt %5.1f (fark %+5.1f) | fps %s | det %s ms"
                   % (kosu_no, s["menzil"], s["faz"], s["kilit"] or 0,
                      "VAR" if s["tespit"] else "yok", s["dz"] or 0,
                      s["irtifa_farki"], s["fps"], s["det_ms"]))

        kal = periyot - (time.perf_counter() - t_dongu)
        if kal > 0:
            time.sleep(kal)

    pf.close()
    izf.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--izle", action="store_true",
                    help="yalniz gozlemle, hicbir mudahale yapma")
    ap.add_argument("--tus-yok", action="store_true",
                    help="'E' gonderme (oyun kendi respawn ediyorsa)")
    ap.add_argument("--kosu", type=int, default=0, help="bu kadar kosudan sonra dur")
    a = ap.parse_args()
    try:
        dongu(a)
    except KeyboardInterrupt:
        gunluk("kullanici durdurdu.")


if __name__ == "__main__":
    main()

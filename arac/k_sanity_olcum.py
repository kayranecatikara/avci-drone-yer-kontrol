# -*- coding: utf-8 -*-
"""
================================================================================
GELISTIRME/DOGRULAMA ARACI — gorev ucusunda ve degerlendirme kosusunda
kullanilmaz. (Truth erisimi YALNIZCA arac/ altinda yasayabilir; ucus
pipeline'ina — detection/ guidance/ fusion/ web/ main.py — truth izi giremez.)
================================================================================
K SANITY OLCUMU (FAZ 0 — zorunlu, tek sefer)
================================================================================
AMAC: kamera_model.K'nin (HFOV=125 YATAY varsayimi + cozunurluk bagi) gercek
sim goruntusuyle tutarliligini OLCMEK. Beklenen kanat-genisligi:

    w_px_beklenen = f_x * (171.8 cm * proj) / Z_c

  f_x  : kamera_model.fx_px(W)  (W = yakalanan karenin px genisligi)
  171.8: Talon kanat acikligi (1718 mm, SDK'da teyitli)
  proj : bakis-acisi izdusum faktoru = sqrt(1-(s.u)^2)  (s: kanat yonu birim
         vektoru = hiza dik yatay; u: LOS birim). Onden/arkadan bakista ~1.
  Z_c  : hedefin KAMERA-ILERI derinligi (tam zincirle: dunya->govde->kamera)

YONTEM (truth-tabanli): Z referansi dogrudan sim'in DEBUG TRUTH kanalindan
(bozulmamis hedef konumu; sdk.get_debug_truth). Hedef hizi (kanat yonu icin)
truth konumlarindan KISA pencere merkezi farkiyla (+-0.3 s) alinir; ardisik
truth sicramasi fiziksel siniri asarsa kare atilir (spike korumasi). Grup/
medyan/band makinesi YOK (truth'suz eski yontem git gecmisinde: 7f50f5f).

KARAR: |medyan(w_olculen / w_beklenen) - 1| <= %5 -> GECTI (N >= 30 kare).
Sapma > %5 -> DUR ve ISARETLE (HFOV bilgisi, cozunurluk varsayimi veya olcum
proseduru hatali demektir; korlemesine devam edilmez).

TANI (ekstra): ayni zincirle hedef merkezinin reprojeksiyonu vs YOLO bbox
merkezi (px offset; truth'la artik gecikmesiz/temiz). Buyukse (>%3 W)
kamera_model'deki attitude KONVANSIYON varsayimi suphelidir.

KULLANIM (drone YERDE/PASIF calisir — yaklasma ucusu GEREKMEZ; arac arm etmez.
Dogrudan SDK baglanir; WEB ARAYUZU KAPALI olmali — oyun tek TCP kabul eder):
    python arac/k_sanity_olcum.py                 # 60 sn olc + analiz + rapor
    python arac/k_sanity_olcum.py --sure 90       # daha uzun olcum (onerilen)
    python arac/k_sanity_olcum.py --tirman 6      # yerden gorus yetmezse: hover'da olc
    python arac/k_sanity_olcum.py --analiz veri/k_sanity_XXXX.csv   # offline analiz

SAHNE GEREKSINIMI: hedef UCUYOR olmali (kanat yonu hizdan turetilir; duran
hedef olculemez) ve rotasi <50-60 m'den gecmeli; uzak/yan/merkez-disi kareleri
kapilar zaten eler. COK-NESNELI SAHNE (orn. yerde PARK ikinci Talon): kutu
SECIMI truth konumunun goruntuye reprojeksiyonuna EN YAKIN merkezle yapilir
(esik 0.25*W; eslesen kutu yoksa kare tespitsiz sayilir) — GENISLIK olcumu
secimden bagimsizdir, yanlilik girmez. Oyunda debug truth AKMIYORSA arac
basta acik hatayla durur.

NOT: yakalama DOGAL cozunurlukte (--genislik 0; 1920'de 36 m'deki Talon ~24 px,
960'a kucultulmus karede ~12 px'ti) ve --imgsz varsayilani 1280 (uretimdeki
640 DEGIL; olcumde FPS onemsiz, kucuk hedef kaybolmasin). CUDA bellek yetmezse
--imgsz 960'a in; K cozunurluk-parametreli oldugundan analiz etkilenmez.

YAKALAMA: oncelik PrintWindow pencere-ICERIGI — oyun BASKA PENCERELERIN
ARKASINDAYKEN de dogru kare gelir (olcum sirasinda terminal/VS Code'a
bakilabilir). PrintWindow calismazsa mss ekran-bolgesine dusulur; YALNIZCA o
durumda oyun onde/gorunur ve sabit boyutta kalmali (arac kaynagi konsola yazar).
================================================================================
"""
import argparse
import csv
import math
import os
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJ_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _PROJ_ROOT)

from detection import kamera_model as km                       # noqa: E402

TALON_KANAT_CM = 171.8        # 1718 mm (SDK'da teyitli; FAZ 2 model tablosu +-859 mm)
CAM_MAX_WIDTH = 960           # server.py ile AYNI olcek (domain tutarliligi)
GAME_TITLE_HINTS = ["dronesofwar", "drones of war", "drone of war"]
VERI_DIR = os.path.join(_PROJ_ROOT, "veri")

# --- Analiz kapilari (olcume girecek kareler) ---
CONF_MIN = 0.45               # uretim esigiyle ayni (Cfg.VIS_CONF_MIN); --conf ile ezilebilir
                              # (geometri olcumu kilit karari degildir; dusuk-conf kutunun
                              # genisligi de genelde dogrudur, gerekirse 0.35'e inilebilir)
PROJ_MIN = 0.90               # kanat cizgisi ~goruntu duzlemine paralel (onden/arkadan)
W_PX_MIN = 6.0                # cok kucuk bbox -> kuantizasyon gurultusu
W_BEK_MIN = 5.0               # beklenen genislik de cok kucukse (hedef cok uzak) alma
EX_EY_MAX = 0.50              # goruntu kenarindaki tespitleri alma (merkez en guvenli)
VHIZ_MIN = 200.0              # cm/s; hedef yatay hizi altindaysa kanat yonu guvenilmez
TREND_S = 0.3                 # hedef hizi icin +-bakis suresi (kisa pencere)
SICRAMA_CMS = 15000.0         # truth ardisik-fark hiz siniri (150 m/s ustu = spike/glitch)
N_MIN = 30                    # karar icin asgari gecerli kare
SAPMA_ESIK = 0.05             # KARAR esigi: medyan oran sapmasi <= %5


# ----------------------------------------------------------------------------
#  Yakalama (server.py'nin mss yolunun sadelestirilmis kopyasi; server import
#  EDILMEZ — modul yan etkileri var)
# ----------------------------------------------------------------------------
def _oyun_bul():
    """Oyun penceresini bul -> ((left,top,w,h)|None, hwnd|None)."""
    try:
        import pygetwindow as gw
        from detection.pencere_yakala import pencere_bul
        baslik, hwnd = pencere_bul(GAME_TITLE_HINTS)
        if baslik is None:
            return None, None
        for w in gw.getAllWindows():
            if (hwnd is not None and getattr(w, "_hWnd", None) == hwnd) or \
               (hwnd is None and (w.title or "").strip() == baslik):
                if w.width > 0 and w.height > 0 and w.visible:
                    return (w.left, w.top, w.width, w.height), getattr(w, "_hWnd", hwnd)
    except Exception:
        pass
    return None, None


class _BMIH(  # BITMAPINFOHEADER (GetDIBits icin)
        __import__("ctypes").Structure):
    import ctypes as _ct
    _fields_ = [("biSize", _ct.c_uint32), ("biWidth", _ct.c_long),
                ("biHeight", _ct.c_long), ("biPlanes", _ct.c_uint16),
                ("biBitCount", _ct.c_uint16), ("biCompression", _ct.c_uint32),
                ("biSizeImage", _ct.c_uint32), ("biXPelsPerMeter", _ct.c_long),
                ("biYPelsPerMeter", _ct.c_long), ("biClrUsed", _ct.c_uint32),
                ("biClrImportant", _ct.c_uint32)]


def _pencere_icerik_bgr(hwnd):
    """PrintWindow (PW_CLIENTONLY|PW_RENDERFULLCONTENT) ile pencere ICERIGINI yakala:
    oyun BASKA PENCERELERIN ARKASINDAYKEN de dogru goruntu verir (mss ekran-bolgesi
    yakalamanin 'oyun onde kalmali' sartini kaldirir). Basarisiz/bos icerik -> None
    (cagiran mss'e duser). Yalnizca bu OLCUM ARACINDA kullanilir; uretim serverin
    yakalama yolu degismez."""
    import ctypes
    u32, g32 = ctypes.windll.user32, ctypes.windll.gdi32
    r = (ctypes.c_long * 4)()
    if not u32.GetClientRect(hwnd, ctypes.byref(r)):
        return None
    w, h = int(r[2] - r[0]), int(r[3] - r[1])
    if w < 64 or h < 64:
        return None
    wdc = u32.GetDC(hwnd)
    if not wdc:
        return None
    mdc = g32.CreateCompatibleDC(wdc)
    bmp = g32.CreateCompatibleBitmap(wdc, w, h)
    eski = g32.SelectObject(mdc, bmp)
    try:
        if not u32.PrintWindow(hwnd, mdc, 3):        # 1|2: CLIENTONLY|RENDERFULLCONTENT
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
        u32.ReleaseDC(hwnd, wdc)


def _oyun_one_getir():
    """Oyun penceresini ONE getir (mss ekran-bolgesi yakalar; oyun baska pencerenin
    ARKASINDAYSA yanlis goruntu gelir). Basarisizsa False; kullanici elle tiklar."""
    try:
        import ctypes
        import pygetwindow as gw
        from detection.pencere_yakala import pencere_bul
        baslik, hwnd = pencere_bul(GAME_TITLE_HINTS)
        if hwnd is None and baslik:
            for w in gw.getAllWindows():
                if (w.title or "").strip() == baslik:
                    hwnd = getattr(w, "_hWnd", None)
                    break
        if not hwnd:
            return False
        u32 = ctypes.windll.user32
        if u32.IsIconic(hwnd):
            u32.ShowWindow(hwnd, 9)          # SW_RESTORE: kucultulmusse geri getir
        u32.SetForegroundWindow(hwnd)
        return True
    except Exception as e:
        print("[UYARI] Oyun penceresi one getirilemedi (%s)." % e)
        return False


def kare_al(sct, cv2, genislik=0):
    """(BGR kare, kaynak_adi). Oncelik: PrintWindow pencere-ICERIGI (oyun arkada
    olsa bile dogru kare; olcum sirasinda baska pencereyle calisilabilir).
    Olmazsa mss bolge (oyun ONDE olmali), o da olmazsa tum ekran.
    genislik=0 -> DOGAL cozunurluk (kucuk/uzak hedef icin en iyi tespit sansi;
    K zaten cozunurluk-parametreli). >0 -> o genislige olcekle."""
    bolge, hwnd = _oyun_bul()
    fr = None
    kaynak = ""
    if hwnd:
        fr = _pencere_icerik_bgr(hwnd)
        if fr is not None:
            kaynak = "pencere-icerik"
    if fr is None:
        if bolge:
            left, top, wd, hg = bolge
            bbox = {"left": left, "top": top, "width": wd, "height": hg}
            kaynak = "mss-bolge(oyun ONDE olmali)"
        else:
            bbox = sct.monitors[1]
            kaynak = "TUM-EKRAN"
        raw = sct.grab(bbox)
        fr = np.frombuffer(raw.bgra, dtype=np.uint8).reshape(
            raw.height, raw.width, 4)[:, :, :3]
    if genislik and fr.shape[1] > genislik:
        oran = genislik / fr.shape[1]
        fr = cv2.resize(fr, (genislik, int(fr.shape[0] * oran)))
    return np.ascontiguousarray(fr), kaynak


CSV_KOLON = ["t", "W", "H", "cx", "cy", "w", "h", "conf",
             "dx", "dy", "dz", "droll", "dpitch", "dyaw",
             "ttx", "tty", "ttz", "hamx", "hamy", "hamz",
             "n_kutu", "sec_off_px"]     # tani: karedeki kutu sayisi + secim offseti


def olc(sure_s, tirman_s, csv_yolu, imgsz=1280, genislik=0):
    import cv2
    import mss
    from sdk import drone_sdk as drone
    from detection.gorsel_tespit import HedefDedektor

    if not drone.connect():
        print("[HATA] Oyuna baglanilamadi. Oyun acik ve PLAY modunda mi?")
        print("       WEB ARAYUZU KAPALI olmali (oyun tek TCP baglantisi kabul eder).")
        return None
    time.sleep(1.5)                                    # ilk telemetri gelsin
    if not drone.get_debug_truth().get("available"):
        print("[HATA] DEBUG TRUTH AKMIYOR (get_debug_truth available=False).")
        print("       Bu arac truth-tabanlidir; sim'de debug/truth kanalini ac.")
        drone.disconnect()
        return None
    print("[OK] Oyuna baglanildi; debug truth AKIYOR.")

    ded = HedefDedektor(os.path.join(_PROJ_ROOT, "models", "best.pt"),
                        conf=0.15, imgsz=imgsz)     # dusuk taban: analiz kapisi ayri (--conf)
    if not ded.hazir:
        print("[HATA] best.pt yuklenemedi: %s" % ded.hata)
        drone.disconnect()
        return None
    print("[OK] best.pt yuklendi (device=%s, imgsz=%d)." % (ded.device, imgsz))

    if tirman_s > 0:
        print("[UCUS] %d sn tirmaniliyor (thr=0.5), sonra hover'da olcum..." % tirman_s)
        drone.set_control_surfaces(0.5, 0.0, 0.0, 0.0, True)
        t0 = time.perf_counter()
        while time.perf_counter() - t0 < tirman_s:
            time.sleep(0.05)
        drone.set_control_surfaces(0.0, 0.0, 0.0, 0.0, True)   # hover

    if _oyun_one_getir():
        print("[OK] Oyun penceresi ONE getirildi; 3 sn icinde olcum basliyor...")
    else:
        print("[UYARI] OYUN PENCERESINE TIKLA (one getir) - olcum 3 sn icinde basliyor!")
    time.sleep(3.0)

    os.makedirs(VERI_DIR, exist_ok=True)
    f = open(csv_yolu, "w", newline="", encoding="utf-8")
    wcsv = csv.writer(f)
    wcsv.writerow(CSV_KOLON)

    sct = mss.mss()
    t0 = time.perf_counter()
    n_kare = n_tespit = 0
    son_hover = t0
    kaynak_uyari = False
    print("[OLCUM] %d sn kare toplaniyor (hedef gecislerini bekle)..." % sure_s)
    while True:
        t = time.perf_counter() - t0
        if t >= sure_s:
            break
        if tirman_s > 0 and time.perf_counter() - son_hover > 0.5:
            drone.set_control_surfaces(0.0, 0.0, 0.0, 0.0, True)  # hover tazele
            son_hover = time.perf_counter()
        # Telemetri kareye MUMKUN OLDUGUNCA yakin okunur (attitude tam hizli/temiz)
        dpos = drone.get_drone_location()
        drot = drone.get_drone_rotation()
        ham = drone.get_target_location()
        truth = drone.get_debug_truth()
        tvar = bool(truth.get("available"))
        tpos = truth["target"]["position"] if tvar else ("", "", "")
        try:
            fr, kaynak = kare_al(sct, cv2, genislik=genislik)
        except Exception as e:
            print("[UYARI] kare alinamadi: %s" % e)
            time.sleep(0.2)
            continue
        if n_kare == 0:
            print("[YAKALAMA] kaynak: %s" % kaynak)
        if kaynak != "pencere-icerik" and not kaynak_uyari:
            kaynak_uyari = True
            print("[UYARI] Pencere-ICERIGI yakalanamiyor -> %s. Bu yolda OYUN ONDE/"
                  "gorunur kalmali; olcum boyunca baska pencereye TIKLAMA." % kaynak)
        kutular = ded.tespit_hepsi(fr)
        n_kare += 1
        # KUTU SECIMI: cok-nesneli sahnede (park Talon vb.) truth'un goruntuye
        # reprojeksiyonuna EN YAKIN merkezli kutu alinir (esik 0.25*W; eslesen
        # yoksa kare tespitsiz sayilir). Reprojeksiyon yoksa en yuksek conf.
        det = None
        sec_off = ""
        if kutular:
            Wf, Hf = kutular[0]["W"], kutular[0]["H"]
            uv = None
            if tvar:
                pk = km.dunya_to_kamera(np.array(tpos, float), np.array(dpos, float),
                                        drot[0], drot[1], drot[2])
                if pk[2] > 0:
                    uv = km.izdusur(pk, km.K_matrisi(Wf, Hf))
            if uv is not None:
                aday = min(kutular, key=lambda d: (d["cx"] - uv[0]) ** 2
                           + (d["cy"] - uv[1]) ** 2)
                off = ((aday["cx"] - uv[0]) ** 2 + (aday["cy"] - uv[1]) ** 2) ** 0.5
                if off <= 0.25 * Wf:
                    det = aday
                    sec_off = "%.1f" % off
            else:
                det = kutular[0]
        if det is not None:
            n_tespit += 1
            satir = [t, det["W"], det["H"], det["cx"], det["cy"], det["w"], det["h"],
                     det["conf"]]
        else:
            satir = [t, fr.shape[1], fr.shape[0], "", "", "", "", ""]
        satir += [dpos[0], dpos[1], dpos[2], drot[0], drot[1], drot[2],
                  tpos[0], tpos[1], tpos[2], ham[0], ham[1], ham[2],
                  len(kutular), sec_off]
        wcsv.writerow(["%.4f" % x if isinstance(x, float) else x for x in satir])
        if n_kare % 50 == 0:
            f.flush()
            print("  ... t=%.0fs kare=%d tespit=%d" % (t, n_kare, n_tespit))
    f.close()
    if tirman_s > 0:
        drone.set_control_surfaces(0.0, 0.0, 0.0, 0.0, True)
        print("[UCUS] Olcum bitti; drone HOVER'da birakildi (arm acik).")
    drone.disconnect()
    print("[OLCUM] Bitti: %d kare, %d tespit -> %s" % (n_kare, n_tespit, csv_yolu))
    return csv_yolu


# ----------------------------------------------------------------------------
#  Analiz — truth-tabanli (Z dogrudan truth; kisa pencere hizi + spike korumasi)
# ----------------------------------------------------------------------------
def _yukle(csv_yolu):
    with open(csv_yolu, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _zaman_indeksi(t_kare, i, dt_hedef):
    """t_kare[i]+dt_hedef anina en yakin kare indeksi; tolerans disinda None."""
    j = int(np.searchsorted(t_kare, t_kare[i] + dt_hedef))
    j = min(max(j, 0), len(t_kare) - 1)
    if abs(t_kare[j] - (t_kare[i] + dt_hedef)) > 0.25:
        return None
    return j


def analiz(csv_yolu, conf_min=CONF_MIN):
    rows = _yukle(csv_yolu)
    if not rows:
        print("[HATA] CSV bos: %s" % csv_yolu)
        return {"gecti": False, "yetersiz": True, "n": 0}

    t_kare = np.array([_f(r["t"]) for r in rows], dtype=float)
    tp = np.array([[(_f(r["ttx"]) if r["ttx"] else np.nan),
                    (_f(r["tty"]) if r["tty"] else np.nan),
                    (_f(r["ttz"]) if r["ttz"] else np.nan)] for r in rows], dtype=float)
    dpos_a = np.array([[_f(r["dx"]), _f(r["dy"]), _f(r["dz"])] for r in rows],
                      dtype=float)

    # SPIKE KORUMASI: ardisik truth farki fiziksel hiz sinirini asarsa o kareyi atla
    # (truth temiz olmali; yine de glitch/paket karismasina karsi ucuz supap).
    bozuk = np.zeros(len(rows), dtype=bool)
    for i in range(1, len(rows)):
        dt = t_kare[i] - t_kare[i - 1]
        if dt <= 0 or np.any(np.isnan(tp[i])) or np.any(np.isnan(tp[i - 1])):
            continue
        if np.linalg.norm(tp[i] - tp[i - 1]) / dt > SICRAMA_CMS:
            bozuk[i] = True

    # Modal cozunurluk (pencere boyutu degistiyse o kareler elenir)
    Ws = [int(float(r["W"])) for r in rows if r["W"]]
    Hs = [int(float(r["H"])) for r in rows if r["H"]]
    W = max(set(Ws), key=Ws.count)
    H = max(set(Hs), key=Hs.count)
    Km = km.K_matrisi(W, H)
    fx = km.fx_px(W)

    kayit = []   # (oran, Zc, w_olc, w_bek, proj, off_px)
    ele = {"tespit_yok": 0, "conf": 0, "cozunurluk": 0, "truth_yok": 0, "spike": 0,
           "hiz_yok": 0, "yavas": 0, "proj": 0, "kenar": 0, "kucuk": 0, "arkada": 0}
    for i, r in enumerate(rows):
        if not r["cx"]:
            ele["tespit_yok"] += 1
            continue
        conf = _f(r["conf"]) or 0.0
        if conf < conf_min:
            ele["conf"] += 1
            continue
        if int(float(r["W"])) != W or int(float(r["H"])) != H:
            ele["cozunurluk"] += 1
            continue
        if np.any(np.isnan(tp[i])):
            ele["truth_yok"] += 1
            continue
        if bozuk[i]:
            ele["spike"] += 1
            continue
        # Hedef hizi: truth konumlarindan KISA pencere merkezi farki (+-TREND_S)
        j1 = _zaman_indeksi(t_kare, i, -TREND_S)
        j2 = _zaman_indeksi(t_kare, i, +TREND_S)
        if (j1 is None or j2 is None or j1 == j2 or
                np.any(np.isnan(tp[j1])) or np.any(np.isnan(tp[j2])) or
                bozuk[j1] or bozuk[j2]):
            ele["hiz_yok"] += 1
            continue
        v_t = (tp[j2] - tp[j1]) / (t_kare[j2] - t_kare[j1])
        vh = np.array([v_t[0], v_t[1], 0.0])
        nvh = np.linalg.norm(vh)
        if nvh < VHIZ_MIN:
            ele["yavas"] += 1                               # kanat yonu guvenilmez
            continue
        dpos = dpos_a[i]
        att = (_f(r["droll"]), _f(r["dpitch"]), _f(r["dyaw"]))
        los = tp[i] - dpos
        u = los / max(np.linalg.norm(los), 1e-9)
        s = np.array([-vh[1], vh[0], 0.0]) / nvh            # kanat yonu: hiza dik yatay
        proj = math.sqrt(max(0.0, 1.0 - float(np.dot(s, u)) ** 2))
        if proj < PROJ_MIN:
            ele["proj"] += 1
            continue
        cx, cy, wpx = _f(r["cx"]), _f(r["cy"]), _f(r["w"])
        ex = (cx - W / 2.0) / (W / 2.0)
        ey = (cy - H / 2.0) / (H / 2.0)
        if abs(ex) > EX_EY_MAX or abs(ey) > EX_EY_MAX:
            ele["kenar"] += 1
            continue
        pk = km.dunya_to_kamera(tp[i], dpos, att[0], att[1], att[2])
        if pk[2] <= 0:
            ele["arkada"] += 1          # zincir hedefi arkada saniyor (KONVANSIYON tanisi!)
            continue
        Zc = float(pk[2])
        w_bek = fx * (TALON_KANAT_CM * proj) / Zc
        if wpx < W_PX_MIN or w_bek < W_BEK_MIN:
            ele["kucuk"] += 1
            continue
        off_px = None
        uv = km.izdusur(pk, Km)
        if uv is not None:
            off_px = math.hypot(uv[0] - cx, uv[1] - cy)
        kayit.append((wpx / w_bek, Zc, wpx, w_bek, proj, off_px))

    # ---------------- RAPOR ----------------
    print("\n" + "=" * 68)
    print(" K SANITY RAPORU (truth-tabanli)  (%s)" % os.path.basename(csv_yolu))
    print("=" * 68)
    print(" cozunurluk       : %dx%d  (f_x = %.1f px; f_x/W = %.4f)" % (W, H, fx, fx / W))
    print(" kare / tespit    : %d / %d" % (len(rows), sum(1 for r in rows if r["cx"])))
    print(" elenen           : %s" % ", ".join("%s=%d" % kv for kv in ele.items() if kv[1]))
    print(" olcume giren     : %d kare (gerek: >=%d)" % (len(kayit), N_MIN))

    sonuc = {"gecti": False, "yetersiz": False, "n": len(kayit), "ele": ele,
             "W": W, "H": H, "fx": fx}
    if len(kayit) < N_MIN:
        print("\n[SONUC] YETERSIZ VERI. Hedefin onden/arkadan, merkeze yakin ve")
        print("        <50-60 m'den gectigi daha uzun/yakin bir kosu gerekli")
        print("        (--sure artir veya once manuel modla rotaya yaklas).")
        sonuc["yetersiz"] = True
        return sonuc

    a = np.array([[k[0], k[1], k[2], k[3], k[4]] for k in kayit], dtype=float)
    oran, Zc_a, wolc, wbek, proj_a = a[:, 0], a[:, 1], a[:, 2], a[:, 3], a[:, 4]
    m_oran = float(np.median(oran))
    mad = float(np.median(np.abs(oran - m_oran)))
    sapma = m_oran - 1.0
    offs = np.array([k[5] for k in kayit if k[5] is not None], dtype=float)

    print("\n --- PROMPT TABLOSU (Z, w_px olculen, w_px beklenen, sapma %%) ---")
    print(" Z (kamera-ileri) : medyan %.1f m   (aralik %.1f-%.1f m)"
          % (np.median(Zc_a) / 100, Zc_a.min() / 100, Zc_a.max() / 100))
    print(" w_px olculen     : medyan %.1f px" % np.median(wolc))
    print(" w_px beklenen    : medyan %.1f px  (f_x*171.8cm*proj/Zc; medyan proj=%.3f)"
          % (np.median(wbek), np.median(proj_a)))
    print(" oran (olc/bek)   : medyan %.4f  (MAD %.4f)  ->  SAPMA = %+.1f%%"
          % (m_oran, mad, 100 * sapma))
    if offs.size:
        off_med = float(np.median(offs))
        print("\n TANI: merkez reproj offset medyan %.1f px (goruntu genisliginin %%%.1f'i)"
              % (off_med, 100 * off_med / W))
        print("       (kutu secimi reprojeksiyonla yapildigindan bu istatistik 0.25W ile"
              " sinirlidir; asil karar genislik oranindadir)")
        if off_med > 0.03 * W:
            print("       [!] >%%3 W: kamera_model attitude KONVANSIYON varsayimi supheli"
                  " (isaret/sira) — genislik gecse bile isaretle.")
        sonuc["off_med_px"] = off_med

    gecti = abs(sapma) <= SAPMA_ESIK
    print("\n" + "=" * 68)
    if gecti:
        print(" SONUC: GECTI  (|%+.1f%%| <= %%5) - K/HFOV varsayimi DOGRULANDI."
              % (100 * sapma))
    else:
        print(" SONUC: KALDI  (|%+.1f%%| > %%5) - DUR VE ISARETLE:" % (100 * sapma))
        print("   HFOV bilgisi, cozunurluk varsayimi veya olcum proseduru hatali.")
        print("   Korlemesine devam ETME (master prompt FAZ 0 kurali).")
    print("=" * 68)
    sonuc.update({"gecti": gecti, "sapma": sapma, "m_oran": m_oran, "mad": mad,
                  "z_med_m": float(np.median(Zc_a)) / 100.0})
    return sonuc


def main():
    ap = argparse.ArgumentParser(description="FAZ 0 K sanity olcumu (truth-tabanli)")
    ap.add_argument("--sure", type=float, default=60.0, help="olcum suresi (sn)")
    ap.add_argument("--tirman", type=float, default=0.0,
                    help="olcumden once N sn tirman (arm eder; sonra hover)")
    ap.add_argument("--imgsz", type=int, default=1280,
                    help="YOLO inference cozunurlugu (olcumde FPS onemsiz; CUDA bellek "
                         "yetmezse 960'a in)")
    ap.add_argument("--genislik", type=int, default=0,
                    help="kare genisligi (0 = DOGAL cozunurluk, onerilen; 960 = eski "
                         "davranis)")
    ap.add_argument("--analiz", type=str, default=None,
                    help="yakalama YAPMADAN var olan CSV'yi analiz et")
    ap.add_argument("--csv", type=str, default=None, help="cikti CSV yolu")
    ap.add_argument("--conf", type=float, default=CONF_MIN,
                    help="analiz conf kapisi (varsayilan uretim esigi %.2f; geometri "
                         "olcumu icin gerekirse 0.35'e inilebilir)" % CONF_MIN)
    arg = ap.parse_args()
    if arg.analiz:
        sonuc = analiz(arg.analiz, conf_min=arg.conf)
    else:
        yol = arg.csv or os.path.join(
            VERI_DIR, time.strftime("k_sanity_%Y%m%d_%H%M%S.csv"))
        yol = olc(arg.sure, arg.tirman, yol, imgsz=arg.imgsz, genislik=arg.genislik)
        sonuc = analiz(yol, conf_min=arg.conf) if yol else None
    sys.exit(0 if (sonuc and sonuc.get("gecti")) else 1)


if __name__ == "__main__":
    main()

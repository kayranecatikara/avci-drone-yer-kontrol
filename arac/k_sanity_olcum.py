# -*- coding: utf-8 -*-
"""
================================================================================
K SANITY OLCUMU (FAZ 0 — zorunlu, tek sefer)                    [OLCUM ARACI]
================================================================================
AMAC: kamera_model.K'nin (HFOV=125 YATAY varsayimi + cozunurluk bagi) gercek
sim goruntusuyle tutarliligini OLCMEK. Beklenen kanat-genisligi:

    w_px_beklenen = f_x * (171.8 cm * proj) / Z_c

  f_x  : kamera_model.fx_px(W)  (W = yakalanan karenin px genisligi)
  171.8: Talon kanat acikligi (1718 mm, SDK'da teyitli)
  proj : bakis-acisi izdusum faktoru = sqrt(1-(s.u)^2)  (s: kanat yonu birim
         vektoru = hiza dik yatay; u: LOS birim). Onden/arkadan bakista ~1.
  Z_c  : hedefin KAMERA-ILERI derinligi (tam zincirle: dunya->govde->kamera)

TRUTH'SUZ YONTEM (sim v0.0.5 gercegi: debug truth kanali YOK; arayuzdeki
anahtar guduum modu secicidir, telemetri bozulmalari KAPATILAMAZ — SDK_README):

 1) Z REFERANSI = hedef GPS'inin KAYAN MEDYANI (merkezli pencere ~1.2 s,
    tekillestirilmis TAZE paketler). Medyan spike'lari tamamen eler,
    sifir-ortalamali gurultuyu bastirir; SABIT OFFSET/DRIFT medyanda KALIR
    (bu yuzden 3. madde sart). Dropout 30. sn'den sonra baslar: taze-paket
    boslugu (>0.6 s) pencereye tasarsa o kareler ELENIR; olcumun ilk 30 sn'si
    onceliklidir (olcumu Play'e gecer gecmez baslat).
 2) GECIKME AYRIMI: GPS gecikmesi hareketli hedefte Z'ye sistematik hata katar
    (15-18 m/s hedefte 0.5-1 s gecikme ~ 8-18 m). Kareler Z-trendine gore
    YAKLASAN / UZAKLASAN diye ikiye ayrilir; sapma grup basina ayri raporlanir
    ve KARAR iki grubun ORTALAMASINA uygulanir — gecikme hatasi iki yonde zit
    isaretlidir (yaklasirken Z buyuk, uzaklasirken kucuk gorunur), simetrik
    orneklemde birinci mertebede iptal olur.
 3) K / OFFSET AYRIMI: 2-3 MESAFE BANDI; her bandin degeri GECIKME-IPTALLI
    (bant ici yaklasan/uzaklasan medyan ortalamasi). Sapma Z ile orantiliysa
    (bantlarda sabit YUZDE) OLCEK/K sorunudur; mesafeden bagimsiz sabit METRE
    ise GPS OFFSET'idir. Nicel ayrim: bant noktalarina oran = A + B*(1/Zc) fit'i
      oran = (fx_gercek/fx_varsayim) * (Z_ref/Z_gercek) ~ k * (1 + o_r/Z)
    => A = k (OLCEK; offset VE gecikmeden arindirilmis), B/A = o_r (sabit
    radyal GPS offset, cm). Kare/grup-bazli fit BILEREK kullanilmaz: gecikme
    terimi tau*|dR/dt|/Z grup icinde de Z ile degisir, egrilik intercept'e
    sizar (sentetik testte kanitli). En az 2 cift-yonlu bant ve bant medyanlari
    arasi Zmax/Zmin >= 1.25 gerekir; degilse yalniz grup ortalamasi kullanilir.
 4) KARAR: %10 esigi TEK KAREYE degil GRUP ORTALAMALARINA uygulanir:
    |ort(medyan_yaklasan, medyan_uzaklasan) - 1| <= 0.10 -> GECTI.
    Grup basina en az 15 gecerli kare gerekir; yetersizse sureyi uzat veya
    --tirman ile hedef rotasina yaklas.

KULLANIM A (onerilen — arayuzle birlikte, MANUEL yaklastirma):
    1. Oyun acik + Play; arayuz acik (2_Arayuzu_Baslat.bat).
    2. MANUEL modla hedef rotasinin ~20-40 m yakinina, hedefle ayni irtifa
       bandina uc; tuslari birak (failsafe HOVER pozisyonu tutar).
    3. python arac/k_sanity_olcum.py --api --sure 75
       (telemetri server'dan okunur; oyunun tek TCP'sine dokunulmaz)
KULLANIM B (arayuzsuz, dogrudan SDK; WEB ARAYUZU KAPALI olmali):
    python arac/k_sanity_olcum.py                 # 45 sn olc + analiz + rapor
    python arac/k_sanity_olcum.py --tirman 6      # once 6 sn tirman, hover'da olc
OFFLINE: python arac/k_sanity_olcum.py --analiz veri/k_sanity_XXXX.csv

NOT: --imgsz varsayilani 960 (uretimdeki 640 DEGIL): olcumde FPS onemsiz;
kucuk/uzak hedefin 640'a kucultulurken kaybolmasini onler. ~8 px'lik hedef
(55-70 m) 640'ta ~5 px'e dusup kacar; 960'ta oldugu gibi kalir.

Hedef DUZ UCUSTA olmali ve rotasi hem YAKLASAN hem UZAKLASAN bacak icermeli
(gidis-donus / yanindan gecis). Kullanilabilir pencere kabaca <70-80 m
(bbox >= 6 px @960). Oyun penceresi olcum boyunca ONDE/GORUNUR ve SABIT
boyutta kalmali — mss EKRAN BOLGESI yakalar: oyunun onune baska pencere
(tarayici/VS Code) gecerse olcum o pencereyi gorur (arac basta oyunu one
getirir; olcum bitene kadar baska pencereye TIKLAMA).
================================================================================
"""
import argparse
import csv
import json
import math
import os
import sys
import time
import urllib.request

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
CONF_MIN = 0.45               # uretim esigiyle ayni (Cfg.VIS_CONF_MIN)
PROJ_MIN = 0.90               # kanat cizgisi ~goruntu duzlemine paralel (onden/arkadan)
W_PX_MIN = 6.0                # cok kucuk bbox -> kuantizasyon gurultusu
W_BEK_MIN = 5.0               # beklenen genislik de cok kucukse (hedef cok uzak) alma
EX_EY_MAX = 0.50              # goruntu kenarindaki tespitleri alma (merkez en guvenli)
VHIZ_MIN = 200.0              # cm/s; hedef yatay hizi altindaysa kanat yonu guvenilmez

# --- Truth'suz yontem parametreleri ---
MED_PENCERE_S = 0.6           # kayan medyan YARIM penceresi (toplam 1.2 s ~ 6 taze paket @5Hz)
TAZE_MIN = 4                  # pencerede en az taze paket (medyan anlamli olsun)
GAP_S = 0.6                   # taze paketler arasi bosluk esigi (dropout/donma tespiti)
TREND_S = 0.5                 # Z-trend / hedef hizi icin +-bakis suresi
TREND_ESIK = 150.0            # cm/s; |dZ/dt| altinda "duragan" (gruba girmez, bilgi)
GRUP_N_MIN = 15               # karar icin grup basina asgari kare
SAPMA_ESIK = 0.10             # KARAR esigi: birlesik grup-ortalamasi sapmasi <= %10
REG_N_MIN = 20                # regresyon icin GRUP basina asgari kare
REG_Z_ORAN = 1.4              # regresyon kosullanmasi: grup ici Zmax/Zmin alt siniri


# ----------------------------------------------------------------------------
#  Yakalama (server.py'nin mss yolunun sadelestirilmis kopyasi; server import
#  EDILMEZ — modul yan etkileri var: kiyas_log.csv sifirlama, thread'ler)
# ----------------------------------------------------------------------------
def _oyun_bolgesi():
    try:
        import pygetwindow as gw
        from detection.pencere_yakala import pencere_bul
        baslik, hwnd = pencere_bul(GAME_TITLE_HINTS)
        if baslik is None:
            return None
        for w in gw.getAllWindows():
            if (hwnd is not None and getattr(w, "_hWnd", None) == hwnd) or \
               (hwnd is None and (w.title or "").strip() == baslik):
                if w.width > 0 and w.height > 0 and w.visible:
                    return (w.left, w.top, w.width, w.height)
    except Exception:
        pass
    return None


def _oyun_one_getir():
    """Oyun penceresini ONE getir (mss ekran-bolgesi yakalar; oyun baska pencerenin
    ARKASINDAYSA yanlis goruntu gelir — orn. tam ekran VS Code/tarayici). Basarisizsa
    False doner; kullanicinin elle tiklamasi gerekir."""
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


def kare_al(sct, cv2):
    """(BGR kare, kaynak_adi) — oyun penceresi bolgesi; bulunamazsa tum ekran."""
    bolge = _oyun_bolgesi()
    if bolge:
        left, top, wd, hg = bolge
        bbox = {"left": left, "top": top, "width": wd, "height": hg}
        kaynak = "pencere"
    else:
        bbox = sct.monitors[1]
        kaynak = "TUM-EKRAN"
    raw = sct.grab(bbox)
    fr = np.frombuffer(raw.bgra, dtype=np.uint8).reshape(raw.height, raw.width, 4)[:, :, :3]
    if fr.shape[1] > CAM_MAX_WIDTH:
        oran = CAM_MAX_WIDTH / fr.shape[1]
        fr = cv2.resize(fr, (CAM_MAX_WIDTH, int(fr.shape[0] * oran)))
    return np.ascontiguousarray(fr), kaynak


CSV_KOLON = ["t", "W", "H", "cx", "cy", "w", "h", "conf",
             "dx", "dy", "dz", "droll", "dpitch", "dyaw",
             "hamx", "hamy", "hamz"]


API_URL = "http://127.0.0.1:8000/api/telemetry"


def _api_oku():
    """Calisan server'in /api/telemetry ciktisi -> (dpos_cm, drot_deg, ham_cm, dbg).
    Server METRE verir -> cm'ye cevrilir (tum arac cm calisir)."""
    with urllib.request.urlopen(API_URL, timeout=1.0) as r:
        t = json.loads(r.read())
    d, g = t["drone"], t["target"]
    dpos = (d["x"] * 100.0, d["y"] * 100.0, d["z"] * 100.0)
    drot = (d["roll"], d["pitch"], d["yaw"])
    ham = (g["x"] * 100.0, g["y"] * 100.0, g["z"] * 100.0)
    return dpos, drot, ham, t


def olc(sure_s, tirman_s, csv_yolu, api=False, imgsz=960):
    import cv2
    import mss
    from detection.gorsel_tespit import HedefDedektor

    drone = None
    if api:
        # API MODU: telemetri CALISAN server'dan okunur (ikinci TCP acilmaz).
        # Kullanim amaci: drone'u MANUEL modla hedef rotasinin yakinina ucurup
        # hover'da birakmak; olcum normal sistem calisirken paralel yapilir.
        try:
            _, _, _, t0 = _api_oku()
        except Exception as e:
            print("[HATA] Server'a ulasilamadi (%s): %s" % (API_URL, e))
            print("       once arayuzu baslat (2_Arayuzu_Baslat.bat).")
            return None
        if not t0.get("connected"):
            print("[HATA] Server calisiyor ama OYUNA bagli degil (oyun acik/Play mi?).")
            return None
        print("[OK] API modu: telemetri server'dan (oyun baglantisina dokunulmaz).")
        print("     debug truth available = %s" % t0.get("debug", {}).get("available"))
        if tirman_s > 0:
            print("[UYARI] --tirman API modunda YOK (kontrol server'da); yoksayildi.")
            tirman_s = 0
    else:
        from sdk import drone_sdk as drone_mod
        drone = drone_mod
        if not drone.connect():
            print("[HATA] Oyuna baglanilamadi. Oyun acik ve PLAY modunda mi?")
            print("       WEB ARAYUZU KAPALI olmali (oyun tek TCP kabul eder) ya da")
            print("       arayuz aciksa --api ile server uzerinden olc.")
            return None
        time.sleep(1.0)                      # ilk telemetri gelsin
        print("[OK] Oyuna baglanildi. debug truth available = %s"
              % drone.get_debug_truth().get("available"))

    ded = HedefDedektor(os.path.join(_PROJ_ROOT, "models", "best.pt"),
                        conf=0.25, imgsz=imgsz)
    if not ded.hazir:
        print("[HATA] best.pt yuklenemedi: %s" % ded.hata)
        if drone is not None:
            drone.disconnect()
        return None
    print("[OK] best.pt yuklendi (device=%s, imgsz=%d)." % (ded.device, imgsz))
    print("[NOT] Dropout 30. sn'den sonra baslar -> ILK 30 SN EN DEGERLI VERI.")

    if tirman_s > 0 and drone is not None:
        print("[UCUS] %d sn tirmaniliyor (thr=0.5), sonra hover'da olcum..." % tirman_s)
        drone.set_control_surfaces(0.5, 0.0, 0.0, 0.0, True)
        t0 = time.perf_counter()
        while time.perf_counter() - t0 < tirman_s:
            time.sleep(0.05)
        drone.set_control_surfaces(0.0, 0.0, 0.0, 0.0, True)   # hover

    # mss EKRAN BOLGESI yakalar -> oyun penceresi ONDE olmali. Otomatik one getir;
    # olmazsa kullaniciya soyle (ilk karelerde yanlis pencere = tespit yok, zarar yok).
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
        if tirman_s > 0 and drone is not None and time.perf_counter() - son_hover > 0.5:
            drone.set_control_surfaces(0.0, 0.0, 0.0, 0.0, True)  # hover tazele
            son_hover = time.perf_counter()
        # Telemetri kareye MUMKUN OLDUGUNCA yakin okunur (attitude tam hizli/temiz)
        try:
            if drone is not None:
                dpos = drone.get_drone_location()
                drot = drone.get_drone_rotation()
                ham = drone.get_target_location()
            else:
                dpos, drot, ham, _t = _api_oku()
        except Exception as e:
            print("[UYARI] telemetri okunamadi: %s" % e)
            time.sleep(0.2)
            continue
        try:
            fr, kaynak = kare_al(sct, cv2)
        except Exception as e:
            print("[UYARI] kare alinamadi: %s" % e)
            time.sleep(0.2)
            continue
        if kaynak != "pencere" and not kaynak_uyari:
            kaynak_uyari = True
            print("[UYARI] Oyun penceresi bulunamadi -> TUM EKRAN yakalaniyor "
                  "(oyun tam ekran degilse olcum kirlenir).")
        det = ded.tespit_et(fr)
        n_kare += 1
        if det is not None:
            n_tespit += 1
            satir = [t, det["W"], det["H"], det["cx"], det["cy"], det["w"], det["h"],
                     det["conf"]]
        else:
            satir = [t, fr.shape[1], fr.shape[0], "", "", "", "", ""]
        satir += [dpos[0], dpos[1], dpos[2], drot[0], drot[1], drot[2],
                  ham[0], ham[1], ham[2]]
        wcsv.writerow(["%.4f" % x if isinstance(x, float) else x for x in satir])
        if n_kare % 50 == 0:
            f.flush()
            print("  ... t=%.0fs kare=%d tespit=%d" % (t, n_kare, n_tespit))
    f.close()
    if drone is not None:
        if tirman_s > 0:
            drone.set_control_surfaces(0.0, 0.0, 0.0, 0.0, True)
            print("[UCUS] Olcum bitti; drone HOVER'da birakildi (arm acik).")
        drone.disconnect()
    print("[OLCUM] Bitti: %d kare, %d tespit -> %s" % (n_kare, n_tespit, csv_yolu))
    return csv_yolu


# ----------------------------------------------------------------------------
#  Analiz — truth'suz yontem (kayan medyan + yon ayrimi + K/offset regresyonu)
# ----------------------------------------------------------------------------
def _yukle(csv_yolu):
    with open(csv_yolu, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _taze_paketler(t, ham):
    """Tekillestirilmis TAZE hedef-GPS paketleri: (zamanlar, konumlar).
    SDK rate-limit ayni paketi kareler boyu tekrarlar; degisim aninda taze sayilir.
    Zaman damgasi = degisimin ILK gorulduguu kare (hata <= kare araligi)."""
    tz, pz = [], []
    onceki = None
    for i in range(len(t)):
        p = ham[i]
        if onceki is None or not np.allclose(p, onceki):
            tz.append(t[i])
            pz.append(p)
            onceki = p
    return np.array(tz), np.array(pz)


def _kayan_medyan(t_kare, tz, pz):
    """Her kare icin merkezli pencerede taze-paket MEDYANI. Pencerede TAZE_MIN'den
    az paket varsa veya GAP_S'ten buyuk bosluk (dropout) pencereye tasiyorsa NaN."""
    n = len(t_kare)
    med = np.full((n, 3), np.nan)
    for i in range(n):
        t = t_kare[i]
        lo = np.searchsorted(tz, t - MED_PENCERE_S)
        hi = np.searchsorted(tz, t + MED_PENCERE_S, side="right")
        if hi - lo < TAZE_MIN:
            continue
        tt = tz[lo:hi]
        # pencere ici + kenar bosluklari: dropout pencereye tasmis mi?
        sinir = np.concatenate(([t - MED_PENCERE_S], tt, [t + MED_PENCERE_S]))
        if np.max(np.diff(sinir)) > GAP_S:
            continue
        med[i] = np.median(pz[lo:hi], axis=0)
    return med


def _zaman_indeksi(t_kare, i, dt_hedef):
    """t_kare[i]+dt_hedef anina en yakin kare indeksi; tolerans disinda None."""
    j = int(np.searchsorted(t_kare, t_kare[i] + dt_hedef))
    j = min(max(j, 0), len(t_kare) - 1)
    if abs(t_kare[j] - (t_kare[i] + dt_hedef)) > 0.3:
        return None
    return j


def analiz(csv_yolu):
    rows = _yukle(csv_yolu)
    if not rows:
        print("[HATA] CSV bos: %s" % csv_yolu)
        return {"gecti": False, "yetersiz": True, "n": 0}

    t_kare = np.array([_f(r["t"]) for r in rows], dtype=float)
    ham = np.array([[_f(r["hamx"]), _f(r["hamy"]), _f(r["hamz"])] for r in rows],
                   dtype=float)
    tz, pz = _taze_paketler(t_kare, ham)
    med = _kayan_medyan(t_kare, tz, pz)

    # Modal cozunurluk (pencere boyutu degistiyse o kareler elenir)
    Ws = [int(float(r["W"])) for r in rows if r["W"]]
    Hs = [int(float(r["H"])) for r in rows if r["H"]]
    W = max(set(Ws), key=Ws.count)
    H = max(set(Hs), key=Hs.count)
    Km = km.K_matrisi(W, H)
    fx = km.fx_px(W)

    # Menzil serisi (trend icin): |medyan_hedef - drone|
    dpos_a = np.array([[_f(r["dx"]), _f(r["dy"]), _f(r["dz"])] for r in rows],
                      dtype=float)
    R_seri = np.linalg.norm(med - dpos_a, axis=1)          # NaN'li kareler NaN kalir

    kayit = []   # (oran, Zc, grup, w_olc, w_bek, proj, off_px, err_cm, t)
    ele = {"tespit_yok": 0, "conf": 0, "cozunurluk": 0, "medyan_yok": 0,
           "trend_yok": 0, "yavas": 0, "proj": 0, "kenar": 0, "kucuk": 0,
           "arkada": 0}
    n_duragan = 0
    duragan_oran = []
    for i, r in enumerate(rows):
        if not r["cx"]:
            ele["tespit_yok"] += 1
            continue
        conf = _f(r["conf"]) or 0.0
        if conf < CONF_MIN:
            ele["conf"] += 1
            continue
        if int(float(r["W"])) != W or int(float(r["H"])) != H:
            ele["cozunurluk"] += 1
            continue
        if np.any(np.isnan(med[i])):
            ele["medyan_yok"] += 1                          # dropout/pencere yetersiz
            continue
        # Z-trend + hedef hizi: +-TREND_S bakisiyla medyan serisinden
        j1 = _zaman_indeksi(t_kare, i, -TREND_S)
        j2 = _zaman_indeksi(t_kare, i, +TREND_S)
        if (j1 is None or j2 is None or j1 == j2 or
                np.any(np.isnan(med[j1])) or np.any(np.isnan(med[j2])) or
                np.isnan(R_seri[j1]) or np.isnan(R_seri[j2])):
            ele["trend_yok"] += 1
            continue
        dt = t_kare[j2] - t_kare[j1]
        v_t = (med[j2] - med[j1]) / dt                      # hedef hizi (medyan serisi)
        dRdt = (R_seri[j2] - R_seri[j1]) / dt               # menzil trendi
        vh = np.array([v_t[0], v_t[1], 0.0])
        nvh = np.linalg.norm(vh)
        if nvh < VHIZ_MIN:
            ele["yavas"] += 1                               # kanat yonu guvenilmez
            continue
        dpos = dpos_a[i]
        att = (_f(r["droll"]), _f(r["dpitch"]), _f(r["dyaw"]))
        los = med[i] - dpos
        Rm = np.linalg.norm(los)
        u = los / max(Rm, 1e-9)
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
        pk = km.dunya_to_kamera(med[i], dpos, att[0], att[1], att[2])
        if pk[2] <= 0:
            ele["arkada"] += 1          # zincir hedefi arkada saniyor (KONVANSIYON tanisi!)
            continue
        Zc = float(pk[2])
        w_bek = fx * (TALON_KANAT_CM * proj) / Zc
        if wpx < W_PX_MIN or w_bek < W_BEK_MIN:
            ele["kucuk"] += 1
            continue
        oran = wpx / w_bek
        # bbox'in ima ettigi mesafe vs GPS-medyan mesafe (bant tanisi: metre hatasi)
        Zc_ima = fx * (TALON_KANAT_CM * proj) / wpx
        err_cm = Zc - Zc_ima
        off_px = None
        uv = km.izdusur(pk, Km)
        if uv is not None:
            off_px = math.hypot(uv[0] - cx, uv[1] - cy)
        if dRdt <= -TREND_ESIK:
            grup = "yaklasan"
        elif dRdt >= TREND_ESIK:
            grup = "uzaklasan"
        else:
            n_duragan += 1
            duragan_oran.append(oran)
            continue                                        # karara girmez (bilgi)
        kayit.append((oran, Zc, grup, wpx, w_bek, proj, off_px, err_cm, t_kare[i]))

    # ---------------- RAPOR ----------------
    print("\n" + "=" * 68)
    print(" K SANITY RAPORU (truth'suz yontem)  (%s)" % os.path.basename(csv_yolu))
    print("=" * 68)
    print(" cozunurluk       : %dx%d  (f_x = %.1f px; f_x/W = %.4f)" % (W, H, fx, fx / W))
    print(" kare / tespit    : %d / %d   taze GPS paketi: %d"
          % (len(rows), sum(1 for r in rows if r["cx"]), len(tz)))
    print(" elenen           : %s" % ", ".join("%s=%d" % kv for kv in ele.items() if kv[1]))
    n30 = sum(1 for k in kayit if k[8] < 30.0)
    print(" olcume giren     : %d kare (%d tanesi ilk 30 sn'de) + %d duragan (bilgi)"
          % (len(kayit), n30, n_duragan))

    yak = np.array([k[0] for k in kayit if k[2] == "yaklasan"])
    uzk = np.array([k[0] for k in kayit if k[2] == "uzaklasan"])
    sonuc = {"gecti": False, "yetersiz": False, "n": len(kayit),
             "n_yak": int(yak.size), "n_uzk": int(uzk.size), "ele": ele,
             "W": W, "H": H, "fx": fx, "A": None, "A_sapma": None,
             "ofset_m": None, "reg_kosullu": False}
    if yak.size < GRUP_N_MIN or uzk.size < GRUP_N_MIN:
        print("\n[SONUC] YETERSIZ VERI: yaklasan=%d, uzaklasan=%d (gerek: >=%d/grup)."
              % (yak.size, uzk.size, GRUP_N_MIN))
        print("        Sureyi uzat (--sure), hedef rotasina yaklas (--tirman) veya")
        print("        hedefe gidis-donus bacakli rota ver (her iki grup da dolmali).")
        sonuc["yetersiz"] = True
        return sonuc

    r_yak = float(np.median(yak))
    r_uzk = float(np.median(uzk))
    mad_yak = float(np.median(np.abs(yak - r_yak)))
    mad_uzk = float(np.median(np.abs(uzk - r_uzk)))
    birlesik = 0.5 * (r_yak + r_uzk)
    sapma = birlesik - 1.0
    a = np.array([[k[0], k[1], k[7]] for k in kayit], dtype=float)
    oran_a, Zc_a, err_a = a[:, 0], a[:, 1], a[:, 2]

    print("\n --- GRUP AYRIMI (gecikme iki yonde zit isaretli -> ortalama iptal) ---")
    print(" GRUP        N    medyan oran   MAD      sapma")
    print(" yaklasan  %4d     %.4f     %.4f    %+.1f%%" % (yak.size, r_yak, mad_yak,
                                                           100 * (r_yak - 1)))
    print(" uzaklasan %4d     %.4f     %.4f    %+.1f%%" % (uzk.size, r_uzk, mad_uzk,
                                                           100 * (r_uzk - 1)))
    if duragan_oran:
        print(" duragan   %4d     %.4f     (bilgi; karara girmez)"
              % (n_duragan, float(np.median(duragan_oran))))
    print(" BIRLESIK (grup ort.)  %.4f    ->  SAPMA = %+.1f%%   <- KARAR (esik %%10)"
          % (birlesik, 100 * sapma))
    print("\n Z (kamera-ileri) : medyan %.1f m  (aralik %.1f-%.1f m)"
          % (np.median(Zc_a) / 100, Zc_a.min() / 100, Zc_a.max() / 100))
    print(" w_px olculen/beklenen (medyan): %.1f / %.1f px"
          % (float(np.median([k[3] for k in kayit])),
             float(np.median([k[4] for k in kayit]))))

    # --- Mesafe bantlari: sabit yuzde (K) mi, sabit metre (offset) mi?
    #     Bant ici deger GECIKME-IPTALLI hesaplanir (yaklasan/uzaklasan medyan
    #     ortalamasi); tek-yonlu bantlar isaretlenir (gecikme iptal edilemez).
    print("\n --- MESAFE BANTLARI (sabit %% -> olcek/K; sabit metre -> GPS offset) ---")
    grup_a = np.array([k[2] for k in kayit])
    sirali = np.argsort(Zc_a)
    n_bant = 3 if len(kayit) >= 45 else (2 if len(kayit) >= 30 else 1)
    bant_nokta = []                     # (Zc_med_cm, birlesik_oran, birlesik_err_cm)
    print(" bant   Zc medyan   N(yak/uzk)   birlesik oran   birlesik err")
    for b in range(n_bant):
        idx = sirali[b * len(sirali) // n_bant:(b + 1) * len(sirali) // n_bant]
        if idx.size == 0:
            continue
        iy = idx[grup_a[idx] == "yaklasan"]
        iu = idx[grup_a[idx] == "uzaklasan"]
        if iy.size >= 5 and iu.size >= 5:
            o_b = 0.5 * (float(np.median(oran_a[iy])) + float(np.median(oran_a[iu])))
            e_b = 0.5 * (float(np.median(err_a[iy])) + float(np.median(err_a[iu])))
            zb = float(np.median(Zc_a[idx]))
            bant_nokta.append((zb, o_b, e_b))
            print("  %d      %5.1f m   %4d/%-4d       %.4f        %+.1f m"
                  % (b + 1, zb / 100, iy.size, iu.size, o_b, e_b / 100))
        else:
            print("  %d      %5.1f m   %4d/%-4d         -  (tek yonlu; gecikme iptal edilemez)"
                  % (b + 1, np.median(Zc_a[idx]) / 100, iy.size, iu.size))

    # --- K vs OFFSET ayrimi: bant noktalarina oran = A + B*(1/Zc) fit'i.
    #     Kare-bazli/grup-bazli fit YANILIR: gecikme terimi tau*|dR/dt|/Z grup
    #     ICINDE de Z'yle degisir (egrilik intercept'e sizar). Bant noktalari ise
    #     zaten gecikme-iptalli oldugundan geriye k*(1 + o_r/Z) kalir:
    #       A = k (OLCEK: K/HFOV sapmasi), B/A = o_r (sabit radyal GPS offset).
    print("\n --- K / OFFSET AYRIMI (gecikme-iptalli bant noktalarina A + B/Zc) ---")
    reg_kosullu = False
    if len(bant_nokta) >= 2:
        zb = np.array([p[0] for p in bant_nokta])
        ob = np.array([p[1] for p in bant_nokta])
        z_yayilim = float(zb.max() / max(zb.min(), 1e-9))
        if z_yayilim >= 1.25:
            X = np.column_stack([np.ones(len(bant_nokta)), 1.0 / zb])
            katsayi, *_ = np.linalg.lstsq(X, ob, rcond=None)
            A, B = float(katsayi[0]), float(katsayi[1])
            ofset_m = (B / A) / 100.0 if abs(A) > 1e-9 else None
            reg_kosullu = True
            sonuc.update({"A": A, "A_sapma": A - 1.0, "ofset_m": ofset_m,
                          "reg_kosullu": True})
            print(" A (olcek; offset+gecikmeden arindirilmis) : %.4f -> K sapmasi %+.1f%%"
                  % (A, 100 * (A - 1)))
            print(" B/A (sabit radyal GPS offset kestirimi)   : %+.1f m" % ofset_m)
            print(" kosullanma: %d bant, Zmax/Zmin = %.2f" % (len(bant_nokta), z_yayilim))
        else:
            print(" [dar mesafe yayilimi] bant Zmax/Zmin = %.2f < 1.25 -> fit guvenilmez;"
                  % z_yayilim)
            print(" 2-3 FARKLI mesafe bandinda tekrar olc (yakin + uzak gecisler).")
    else:
        print(" Cift-yonlu bant sayisi < 2 -> K/offset ayrimi yapilamadi;")
        print(" 2-3 farkli mesafe bandinda TEKRARLA (yakin + uzak gecisler).")

    offs = np.array([k[6] for k in kayit if k[6] is not None], dtype=float)
    if offs.size:
        print("\n TANI: merkez reproj offset medyan %.1f px (GECIKMEYE ACIK - hedef"
              % float(np.median(offs)))
        print("       hareketliyken buyur; yalniz cok buyukse (>%%10 W) konvansiyon supheli)")

    gecti = abs(sapma) <= SAPMA_ESIK
    print("\n" + "=" * 68)
    if gecti:
        print(" SONUC: GECTI  (birlesik |%+.1f%%| <= %%10) - K/HFOV varsayimi TUTARLI."
              % (100 * sapma))
    else:
        print(" SONUC: KALDI  (birlesik |%+.1f%%| > %%10) - DUR VE ISARETLE:" % (100 * sapma))
        print("   once K/OFFSET ayrimina bak: A sapmasi kucuk + offset buyukse sorun")
        print("   GPS offset'idir (K dogru olabilir); A sapmasi da buyukse HFOV/")
        print("   cozunurluk varsayimi veya olcum proseduru hatali. Korlemesine devam ETME.")
    print("=" * 68)
    sonuc.update({"gecti": gecti, "sapma": sapma, "r_yak": r_yak, "r_uzk": r_uzk,
                  "birlesik": birlesik,
                  "z_med_m": float(np.median(Zc_a)) / 100.0,
                  "off_med_px": (float(np.median(offs)) if offs.size else None)})
    return sonuc


def main():
    ap = argparse.ArgumentParser(description="FAZ 0 K sanity olcumu (truth'suz)")
    ap.add_argument("--sure", type=float, default=45.0, help="olcum suresi (sn)")
    ap.add_argument("--tirman", type=float, default=0.0,
                    help="olcumden once N sn tirman (arm eder; sonra hover; API modunda yok)")
    ap.add_argument("--api", action="store_true",
                    help="telemetriyi CALISAN server'dan oku (/api/telemetry); oyunun "
                         "TCP'sine dokunmaz. Kullanim: arayuzle MANUEL modda hedef "
                         "rotasi yakinina uc, hover'da birak, sonra bu araci calistir")
    ap.add_argument("--imgsz", type=int, default=960,
                    help="YOLO inference cozunurlugu (olcumde FPS onemsiz; kucuk/uzak "
                         "hedef icin 960 onerilir, uretimdeki 640 degil)")
    ap.add_argument("--analiz", type=str, default=None,
                    help="yakalama YAPMADAN var olan CSV'yi analiz et")
    ap.add_argument("--csv", type=str, default=None, help="cikti CSV yolu")
    arg = ap.parse_args()
    if arg.analiz:
        sonuc = analiz(arg.analiz)
    else:
        yol = arg.csv or os.path.join(
            VERI_DIR, time.strftime("k_sanity_%Y%m%d_%H%M%S.csv"))
        yol = olc(arg.sure, arg.tirman, yol, api=arg.api, imgsz=arg.imgsz)
        sonuc = analiz(yol) if yol else None
    sys.exit(0 if (sonuc and sonuc.get("gecti")) else 1)


if __name__ == "__main__":
    main()

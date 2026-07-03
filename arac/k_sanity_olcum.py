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
  Z_c  : hedefin KAMERA-ILERI derinligi (tam zincirle: dunya->govde->kamera;
         merkez disi bakis acisinin cos duzeltmesini otomatik icerir)

KARAR: |medyan(w_olculen / w_beklenen) - 1| <= %10 -> GECTI.
       Sapma > %10 -> DUR ve ISARETLE (HFOV bilgisi, cozunurluk varsayimi veya
       olcum proseduru hatali demektir; korlemesine devam edilmez).

TANI (ekstra): ayni zincirle hedef merkezinin reprojeksiyonu vs YOLO bbox merkezi
(px offset). Buyuk offset attitude KONVANSIYON hatasina isaret eder (kamera_model
basligindaki VARSAYIM'lar) — genislik oranindan bagimsiz rapor edilir.

KULLANIM (once oyunu ac, Play moduna al; WEB ARAYUZUNU KAPAT — oyun TEK TCP
baglantisi kabul eder, bu arac dogrudan baglanir):

    python arac/k_sanity_olcum.py                 # 45 sn olc + analiz + rapor
    python arac/k_sanity_olcum.py --sure 60       # 60 sn olc
    python arac/k_sanity_olcum.py --tirman 6      # once 6 sn tirman, hover'da olc
    python arac/k_sanity_olcum.py --analiz veri/k_sanity_XXXX.csv   # offline analiz

GEREKSINIM: oyunda DEBUG TRUTH ACIK olmali (kiyas panelinin kullandigi kanal)
— Z her karede temiz konum farkindan gelir. Truth kapaliysa arac uyarir ve
ham-GPS-medyan fallback'ine duser (yalnizca SABIT DURAN hedefte anlamli).
Hedef DUZ UCUSTA olmali; sana dogru / senden uzaga ucan bacaklar olcume girer
(proj kapisi digerlerini otomatik eler). Oyun penceresi olcum boyunca GORUNUR
ve SABIT boyutta kalmali (mss bolge yakalar; kenarliksiz pencere onerilir).
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
CONF_MIN = 0.45               # uretim esigiyle ayni (Cfg.VIS_CONF_MIN)
PROJ_MIN = 0.90               # kanat cizgisi ~goruntu duzlemine paralel (onden/arkadan +-25 der)
W_PX_MIN = 6.0                # cok kucuk bbox -> kuantizasyon gurultusu
W_BEK_MIN = 5.0               # beklenen genislik de cok kucukse (hedef cok uzak) alma
EX_EY_MAX = 0.50              # goruntu kenarindaki tespitleri alma (merkez en guvenli)
VHIZ_MIN = 200.0              # cm/s; hedef yatay hizi bunun altindaysa yon guvenilmez
SAPMA_ESIK = 0.10             # KARAR esigi: medyan oran sapmasi <= %10


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
             "ttx", "tty", "ttz", "hamx", "hamy", "hamz", "truth", "corr"]


def olc(sure_s, tirman_s, csv_yolu):
    import cv2
    import mss
    from sdk import drone_sdk as drone
    from detection.gorsel_tespit import HedefDedektor

    if not drone.connect():
        print("[HATA] Oyuna baglanilamadi. Oyun acik ve PLAY modunda mi?")
        print("       WEB ARAYUZU KAPALI olmali (oyun tek TCP baglantisi kabul eder).")
        return None

    ded = HedefDedektor(os.path.join(_PROJ_ROOT, "models", "best.pt"), conf=0.25)
    if not ded.hazir:
        print("[HATA] best.pt yuklenemedi: %s" % ded.hata)
        drone.disconnect()
        return None
    print("[OK] Oyuna baglanildi; best.pt yuklendi (device=%s)." % ded.device)

    if tirman_s > 0:
        print("[UCUS] %d sn tirmaniliyor (thr=0.5), sonra hover'da olcum..." % tirman_s)
        drone.set_control_surfaces(0.5, 0.0, 0.0, 0.0, True)
        t0 = time.perf_counter()
        while time.perf_counter() - t0 < tirman_s:
            time.sleep(0.05)
        drone.set_control_surfaces(0.0, 0.0, 0.0, 0.0, True)   # hover

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
        tpos = truth["target"]["position"] if tvar else (None, None, None)
        corr = ";".join(drone.get_active_corruption())
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
                  tpos[0] if tvar else "", tpos[1] if tvar else "", tpos[2] if tvar else "",
                  ham[0], ham[1], ham[2], int(tvar), corr]
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
#  Analiz
# ----------------------------------------------------------------------------
def _yukle(csv_yolu):
    satirlar = []
    with open(csv_yolu, "r", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        for r in rd:
            satirlar.append(r)
    return satirlar


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def analiz(csv_yolu):
    rows = _yukle(csv_yolu)
    if not rows:
        print("[HATA] CSV bos: %s" % csv_yolu)
        return False

    n_truth = sum(1 for r in rows if r["truth"] == "1")
    truth_var = n_truth > len(rows) * 0.5
    if not truth_var:
        print("[UYARI] Debug truth YOK (%d/%d satir). Ham-GPS-medyan fallback'i "
              "kullanilacak - yalnizca SABIT hedefte anlamli; sonucu ihtiyatla oku."
              % (n_truth, len(rows)))

    # Hedef konum dizisi (truth varsa truth; yoksa ham) + zaman
    t = np.array([_f(r["t"]) for r in rows], dtype=float)
    if truth_var:
        tp = np.array([[_f(r["ttx"]) or np.nan, _f(r["tty"]) or np.nan,
                        _f(r["ttz"]) or np.nan] for r in rows], dtype=float)
    else:
        tp = np.array([[_f(r["hamx"]), _f(r["hamy"]), _f(r["hamz"])] for r in rows],
                      dtype=float)
        med = np.nanmedian(tp, axis=0)                 # sabit hedef varsayimi
        tp = np.tile(med, (len(rows), 1))

    # Hedef hizi: +-3 kare merkezi fark (truth temiz ve surekli)
    K3 = 3
    hiz = np.full_like(tp, np.nan)
    for i in range(K3, len(rows) - K3):
        dt = t[i + K3] - t[i - K3]
        if dt > 1e-3:
            hiz[i] = (tp[i + K3] - tp[i - K3]) / dt

    # Modal cozunurluk (pencere boyutu degistiyse o kareler elenir)
    Ws = [int(float(r["W"])) for r in rows if r["W"]]
    Hs = [int(float(r["H"])) for r in rows if r["H"]]
    W = max(set(Ws), key=Ws.count)
    H = max(set(Hs), key=Hs.count)
    Km = km.K_matrisi(W, H)
    fx = km.fx_px(W)

    kayit = []           # (oran, w_olc, w_bek, Zc, proj, ex, ey, off_px, w_zincir)
    ele = {"tespit_yok": 0, "conf": 0, "cozunurluk": 0, "hiz_yok": 0, "yavas": 0,
           "proj": 0, "kenar": 0, "kucuk": 0, "arkada": 0}
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
        if np.any(np.isnan(hiz[i])) or np.any(np.isnan(tp[i])):
            ele["hiz_yok"] += 1
            continue
        vh = np.array([hiz[i][0], hiz[i][1], 0.0])
        nvh = np.linalg.norm(vh)
        if truth_var and nvh < VHIZ_MIN:
            ele["yavas"] += 1                      # yon guvenilmez (sabit hedefte proj=1 varsay)
            continue
        dpos = np.array([_f(r["dx"]), _f(r["dy"]), _f(r["dz"])])
        att = (_f(r["droll"]), _f(r["dpitch"]), _f(r["dyaw"]))
        los = tp[i] - dpos
        R = np.linalg.norm(los)
        u = los / max(R, 1e-9)
        if truth_var:
            s = np.array([-vh[1], vh[0], 0.0]) / nvh   # kanat yonu: hiza dik yatay
            proj = math.sqrt(max(0.0, 1.0 - float(np.dot(s, u)) ** 2))
        else:
            s = None
            proj = 1.0                                  # sabit hedef: onden bakis varsayimi
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
            ele["arkada"] += 1                          # zincir hedefi arkada saniyor (KONVANSIYON tanisi!)
            continue
        Zc = float(pk[2])
        w_bek = fx * (TALON_KANAT_CM * proj) / Zc
        if wpx < W_PX_MIN or w_bek < W_BEK_MIN:
            ele["kucuk"] += 1
            continue
        # --- tani: tam zincir merkez reprojeksiyonu + uc-nokta genisligi ---
        off_px = w_zincir = None
        uv = km.izdusur(pk, Km)
        if uv is not None:
            off_px = math.hypot(uv[0] - cx, uv[1] - cy)
        if s is not None:
            p1 = km.izdusur(km.dunya_to_kamera(tp[i] + s * (TALON_KANAT_CM / 2.0),
                                               dpos, *att), Km)
            p2 = km.izdusur(km.dunya_to_kamera(tp[i] - s * (TALON_KANAT_CM / 2.0),
                                               dpos, *att), Km)
            if p1 and p2:
                w_zincir = math.hypot(p1[0] - p2[0], p1[1] - p2[1])
        kayit.append((wpx / w_bek, wpx, w_bek, Zc, proj, ex, ey, off_px, w_zincir))

    # ---------------- RAPOR ----------------
    print("\n" + "=" * 64)
    print(" K SANITY RAPORU  (%s)" % os.path.basename(csv_yolu))
    print("=" * 64)
    print(" cozunurluk       : %dx%d  (f_x = %.1f px; f_x/W = %.4f)" % (W, H, fx, fx / W))
    print(" kare / tespit    : %d / %d" % (len(rows), sum(1 for r in rows if r["cx"])))
    print(" elenen           : %s" % ", ".join("%s=%d" % kv for kv in ele.items() if kv[1]))
    print(" olcume giren     : %d kare" % len(kayit))
    if len(kayit) < 10:
        print("\n[SONUC] YETERSIZ VERI (<10 gecerli kare). Hedefin onden/arkadan,")
        print("        merkeze yakin gectigi daha uzun bir kosu gerekli.")
        return {"gecti": False, "yetersiz": True, "n": len(kayit)}
    a = np.array([[k[0], k[1], k[2], k[3], k[4]] for k in kayit], dtype=float)
    oran, wolc, wbek, Zc, proj = a[:, 0], a[:, 1], a[:, 2], a[:, 3], a[:, 4]
    m_oran = float(np.median(oran))
    mad = float(np.median(np.abs(oran - m_oran)))
    sapma = m_oran - 1.0
    offs = np.array([k[7] for k in kayit if k[7] is not None], dtype=float)
    wz = np.array([(k[8], k[1]) for k in kayit if k[8]], dtype=float)
    print("\n --- PROMPT TABLOSU (Z, w_px olculen, w_px beklenen, sapma %%) ---")
    print(" Z (kamera-ileri) : medyan %.1f m   (aralik %.1f-%.1f m)"
          % (np.median(Zc) / 100, Zc.min() / 100, Zc.max() / 100))
    print(" w_px olculen     : medyan %.1f px" % np.median(wolc))
    print(" w_px beklenen    : medyan %.1f px  (f_x*171.8cm*proj/Zc; medyan proj=%.3f)"
          % (np.median(wbek), np.median(proj)))
    print(" oran (olc/bek)   : medyan %.4f  (MAD %.4f)  ->  SAPMA = %+.1f%%"
          % (m_oran, mad, 100 * sapma))
    print("\n --- TANI (attitude/montaj zinciri; genislikten bagimsiz) ---")
    if offs.size:
        print(" merkez reproj    : medyan offset %.1f px (goruntu genisliginin %%%.1f'i)"
              % (np.median(offs), 100 * np.median(offs) / W))
        print("                    buyukse (>%%5): kamera_model attitude VARSAYIMI supheli")
    if wz.size:
        print(" zincir genislik  : medyan (olc/zincir-bek) = %.4f"
              % float(np.median(wz[:, 1] / wz[:, 0])))
    gecti = abs(sapma) <= SAPMA_ESIK
    print("\n" + "=" * 64)
    if gecti:
        print(" SONUC: GECTI  (|%.1f%%| <= %%10) - K/HFOV varsayimi DOGRULANDI."
              % (100 * sapma))
    else:
        print(" SONUC: KALDI  (|%.1f%%| > %%10) - DUR VE ISARETLE:" % (100 * sapma))
        print("   HFOV bilgisi, cozunurluk varsayimi veya olcum proseduru hatali.")
        print("   Korlemesine devam ETME (master prompt FAZ 0 kurali).")
    print("=" * 64)
    return {"gecti": gecti, "yetersiz": False, "n": len(kayit), "sapma": sapma,
            "m_oran": m_oran, "mad": mad,
            "z_med_m": float(np.median(Zc)) / 100.0,
            "w_olc_med": float(np.median(wolc)), "w_bek_med": float(np.median(wbek)),
            "off_med_px": (float(np.median(offs)) if offs.size else None),
            "W": W, "H": H, "fx": fx}


def main():
    ap = argparse.ArgumentParser(description="FAZ 0 K sanity olcumu")
    ap.add_argument("--sure", type=float, default=45.0, help="olcum suresi (sn)")
    ap.add_argument("--tirman", type=float, default=0.0,
                    help="olcumden once N sn tirman (arm eder; sonra hover)")
    ap.add_argument("--analiz", type=str, default=None,
                    help="yakalama YAPMADAN var olan CSV'yi analiz et")
    ap.add_argument("--csv", type=str, default=None, help="cikti CSV yolu")
    arg = ap.parse_args()
    if arg.analiz:
        sonuc = analiz(arg.analiz)
    else:
        yol = arg.csv or os.path.join(
            VERI_DIR, time.strftime("k_sanity_%Y%m%d_%H%M%S.csv"))
        yol = olc(arg.sure, arg.tirman, yol)
        sonuc = analiz(yol) if yol else None
    sys.exit(0 if (sonuc and sonuc.get("gecti")) else 1)


if __name__ == "__main__":
    main()

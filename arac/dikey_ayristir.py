# -*- coding: utf-8 -*-
"""
================================================================================
  DIKEY AYRISTIR -- CPA'daki dikey ayrimi BILESENLERINE ayirir
================================================================================
NEDEN
--------------------------------------------------------------------------------
"Hala dikeyde sorun var": ayna duzeltmesinden sonra CPA'da YATAY ayrim 4.44 ->
2.17 m indi ama DIKEY 1.36 -> 1.19 m'de takildi. Tek sayi ("1.19 m") hangi
kaldiraci cevirmek gerektigini SOYLEMEZ. Bu betik onu dorde boler:

    dz_CPA  =  tasarim_ofseti + izleme_hatasi + ivme_kirpmasi + kanal_gecikmesi

VERI KAYNAKLARI (ve neden bunlar)
--------------------------------------------------------------------------------
  veri/hedef_iz/hedef_iz_*.csv   24 Hz TRUTH konum (hem hedef hem arac).
      -> CPA ve dz_CPA YALNIZ buradan. KONUM kullanilir, HIZ DEGIL.
      ⚠ d_vz bagimsiz truth DEGIL: SDK velocity'nin kendisi ve +0.240 m/s
        sabit yanliligi olculdu. Hakem yapilirsa sahte bulgu cikar.
        Bu betik dikey hizi HEP dz_m'nin sonlu farkindan turetir.
  kopru/gazebo_kaynak/logs/bbox_ibvs_*.csv   gorsel yasa tik logu (~20 Hz).
      -> eps_elev (izleme hatasi), vz_cmd (kirpma SONRASI), cy, pitch.
      Zaman ekseni ORTAK: hedef_iz t_mutlak = perf_counter,
      bbox_ibvs t = monotonic; bu platformda ayni epoch (dogrulandi).

TANIMLAR
--------------------------------------------------------------------------------
  dz        = dz_m - hz_m  (oyun dunyasi z YUKARI+).  dz<0 = arac hedefin ALTINDA.
  T_TAAHHUT = 0.72 s  (dikey kanalin olu 0.08 s + tau 0.64 s). Bundan sonra
              verilen hicbir komut CPA'ya yetismez -> "son karar ani".
  vz_ist    = yasanin kirpma ONCESI istedigi dikey hiz (loglanmiyor, yasadan
              BIREBIR yeniden hesaplanir; tutus dali icin tam, terminal dali
              icin K_VZ_D terimi olcusuz -> o kareler AYRI raporlanir).

CALISTIR
    python arac/dikey_ayristir.py                 # 2026-08-17 11:03 sonrasi
    python arac/dikey_ayristir.py --sonra 20260817_095545
================================================================================
"""
import argparse
import csv
import glob
import math
import os
import re

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IZ_DIZIN = os.path.join(KOK, "veri", "hedef_iz")
BBOX_DIZIN = os.path.join(KOK, "kopru", "gazebo_kaynak", "logs")

# --- yasa sabitleri (bbox_ibvs.Cfg + vision.geometry ile AYNI olmali) ---
CY, FY = 240.0, 166.6
KAMERA_TILT_DEG = 25.0
CY_NISAN = round(CY + FY * math.tan(math.radians(20.0)), 0)   # 301
K_VZ, V_NOM, VZ_MAX = 0.5, 12.0, 3.0
MAX_ACCEL = 12.0
T_TAAHHUT = 0.72      # s; olu 0.08 + tau 0.64
CPA_ESIK = 12.0       # m; bunun altindaki yerel minimumlar "yakin gecis"
CPA_AYIR = 3.0        # s; iki CPA arasi en az bu kadar olsun


def yuzde(v, q):
    if not v:
        return float("nan")
    s = sorted(v)
    return s[min(len(s) - 1, max(0, int(round(q * (len(s) - 1)))))]


def med(v):
    return yuzde(v, 0.5)


def piksel_elev(cy):
    """Kutu pikselinden GOVDE cercevesinde LOS yukselisi (rad, yukari+)."""
    t = math.radians(KAMERA_TILT_DEG)
    b = (cy - CY) / FY
    return math.atan2(math.sin(t) - math.cos(t) * b,
                      math.cos(t) + math.sin(t) * b)


def _f(s, d=float("nan")):
    try:
        return float(s)
    except (TypeError, ValueError):
        return d


# ══════════════════════════════════════════════════════════════════════
#  1) IZ KAYITLARINDAN CPA OLAYLARI
# ══════════════════════════════════════════════════════════════════════
def iz_oku(yol):
    R = []
    with open(yol, encoding="utf-8", errors="replace") as f:
        for r in csv.DictReader(f):
            t = _f(r.get("t_mutlak"))
            hx, hy, hz = _f(r.get("hx_m")), _f(r.get("hy_m")), _f(r.get("hz_m"))
            dx, dy, dz = _f(r.get("dx_m")), _f(r.get("dy_m")), _f(r.get("dz_m"))
            if any(map(lambda v: v != v, (t, hx, hy, hz, dx, dy, dz))):
                continue
            R.append({"t": t, "hx": hx, "hy": hy, "hz": hz,
                      "dx": dx, "dy": dy, "dz": dz,
                      "faz": (r.get("faz") or "?"),
                      "pitch": _f(r.get("d_pitch"))})
    for a in R:
        a["ex"], a["ey"], a["ez"] = a["dx"] - a["hx"], a["dy"] - a["hy"], a["dz"] - a["hz"]
        a["r"] = math.sqrt(a["ex"] ** 2 + a["ey"] ** 2 + a["ez"] ** 2)
        a["rh"] = math.hypot(a["ex"], a["ey"])
    return R


def dz_at(R, t):
    """t anindaki dz (dogrusal ara deger). Disarida ise uctaki deger."""
    if not R:
        return float("nan")
    if t <= R[0]["t"]:
        return R[0]["ez"]
    if t >= R[-1]["t"]:
        return R[-1]["ez"]
    lo, hi = 0, len(R) - 1
    while hi - lo > 1:
        m = (lo + hi) // 2
        if R[m]["t"] <= t:
            lo = m
        else:
            hi = m
    a, b = R[lo], R[hi]
    if b["t"] - a["t"] < 1e-9:
        return a["ez"]
    u = (t - a["t"]) / (b["t"] - a["t"])
    return a["ez"] + u * (b["ez"] - a["ez"])


def r_at(R, t):
    """t anindaki gercek 3B menzil (dogrusal ara deger)."""
    if not R:
        return float("nan")
    if t <= R[0]["t"]:
        return R[0]["r"]
    if t >= R[-1]["t"]:
        return R[-1]["r"]
    lo, hi = 0, len(R) - 1
    while hi - lo > 1:
        m = (lo + hi) // 2
        if R[m]["t"] <= t:
            lo = m
        else:
            hi = m
    a, b = R[lo], R[hi]
    if b["t"] - a["t"] < 1e-9:
        return a["r"]
    u = (t - a["t"]) / (b["t"] - a["t"])
    return a["r"] + u * (b["r"] - a["r"])


def cpa_bul(R):
    """Yerel minimumlari bul, iki ornek arasi DOGRUSAL bagil hareketle
    inceltir. dt~0.04 s ve kapanma ~10 m/s -> ham izgara 0.4 m; bu inceltme
    olmadan 1.19 m'lik bir olcum gurultuye bogulur."""
    olay = []
    n = len(R)
    for i in range(1, n - 1):
        if R[i]["r"] > CPA_ESIK:
            continue
        if not (R[i]["r"] <= R[i - 1]["r"] and R[i]["r"] <= R[i + 1]["r"]):
            continue
        # bagil konum/hiz (KONUM turevi -- SDK velocity DEGIL)
        a, b = R[i - 1], R[i + 1]
        dt = b["t"] - a["t"]
        if dt <= 1e-6:
            continue
        vx = (b["ex"] - a["ex"]) / dt
        vy = (b["ey"] - a["ey"]) / dt
        vz = (b["ez"] - a["ez"]) / dt
        vv = vx * vx + vy * vy + vz * vz
        tau = 0.0
        if vv > 1e-9:
            tau = -(R[i]["ex"] * vx + R[i]["ey"] * vy + R[i]["ez"] * vz) / vv
            tau = max(-dt / 2, min(dt / 2, tau))
        ex = R[i]["ex"] + vx * tau
        ey = R[i]["ey"] + vy * tau
        ez = R[i]["ez"] + vz * tau
        tc = R[i]["t"] + tau
        olay.append({
            "t": tc, "i": i, "r": math.sqrt(ex * ex + ey * ey + ez * ez),
            "rh": math.hypot(ex, ey), "dz": ez,
            "kapanma": math.sqrt(vv), "vz_bagil": vz,
            "faz": R[i]["faz"], "pitch": R[i]["pitch"],
            "dz_taahhut": dz_at(R, tc - T_TAAHHUT),
            "dz_1s": dz_at(R, tc - 1.0),
            "dz_2s": dz_at(R, tc - 2.0),
            "r_taahhut": r_at(R, tc - T_TAAHHUT),
        })
    # cok yakin olaylari tekille (en kucuk r kalsin)
    olay.sort(key=lambda o: o["t"])
    ayik = []
    for o in olay:
        if ayik and o["t"] - ayik[-1]["t"] < CPA_AYIR:
            if o["r"] < ayik[-1]["r"]:
                ayik[-1] = o
            continue
        ayik.append(o)
    return ayik


# ══════════════════════════════════════════════════════════════════════
#  2) BBOX LOGLARINDAN YASA TESHISI
# ══════════════════════════════════════════════════════════════════════
def bbox_oku(dizinden_sonra):
    """Zaman damgasi filtreli TUM bbox tiklerini tek listeye topla."""
    T = []
    for y in sorted(glob.glob(os.path.join(BBOX_DIZIN, "bbox_ibvs_*.csv"))):
        m = re.search(r"(\d{8}_\d{6})", os.path.basename(y))
        if not m or m.group(1) < dizinden_sonra:
            continue
        try:
            with open(y, encoding="utf-8", errors="replace") as f:
                for r in csv.DictReader(f):
                    t = _f(r.get("t"))
                    if t != t:
                        continue
                    # ⚠ KURTARMA satirlari TUM alanlari BOS yazar. Bosu 0.0
                    #   saymak hem ivme istatistigini hem eps istatistigini
                    #   bozar -> satir tamamen atlanir, zincir de kirilir.
                    if any(_f(r.get(k)) != _f(r.get(k))
                           for k in ("vx_cmd", "vy_cmd", "vz_cmd",
                                     "eps_elev_deg", "iris_pitch_deg")):
                        T.append({"t": t, "dt": _f(r.get("dt"), 0.05),
                                  "durum": r.get("durum", ""), "gecersiz": True,
                                  "cy": float("nan"), "eps_elev": float("nan"),
                                  "pitch": float("nan"), "v_los": 0.0,
                                  "vx": float("nan"), "vy": float("nan"),
                                  "vz": float("nan"), "kopru": 0.0,
                                  "boyut": 0.0})
                        continue
                    T.append({
                        "t": t, "dt": _f(r.get("dt"), 0.05),
                        "durum": r.get("durum", ""),
                        "cy": _f(r.get("cy")),
                        "eps_elev": math.radians(_f(r.get("eps_elev_deg"), 0.0)),
                        "pitch": math.radians(_f(r.get("iris_pitch_deg"), 0.0)),
                        "v_los": _f(r.get("v_los"), 0.0),
                        "vx": _f(r.get("vx_cmd"), 0.0),
                        "vy": _f(r.get("vy_cmd"), 0.0),
                        "vz": _f(r.get("vz_cmd"), 0.0),
                        "kopru": _f(r.get("kopru"), 0.0),
                        "boyut": _f(r.get("boyut"), 0.0),
                    })
        except OSError:
            continue
    T.sort(key=lambda a: a["t"])
    # ivme kirpmasi teshisi: onceki komuta gore 3B degisim
    for i in range(1, len(T)):
        a, b = T[i - 1], T[i]
        if (b["t"] - a["t"] > 1.0            # ayri faz -> zincir kopar
                or a.get("gecersiz") or b.get("gecersiz")):
            b["dv"] = b["dvz"] = float("nan")
            continue
        dt = max(b["dt"], 1e-3)
        b["dv"] = math.sqrt((b["vx"] - a["vx"]) ** 2 + (b["vy"] - a["vy"]) ** 2
                            + (b["vz"] - a["vz"]) ** 2) / dt
        b["dvz"] = abs(b["vz"] - a["vz"]) / dt
    if T:
        T[0]["dv"] = T[0]["dvz"] = float("nan")
    return T


def gps_ayristir(sonra):
    """GPS yasasinin dikey butcesi -- yasanin KENDI logundan, dogrudan.

    gps_guidance CSV'si istasyonu (st_z), araci (iris_z) ve hedefi (tgt_z)
    NED'de (asagi+) yazar. Bu ucu AYNI SATIRDA oldugu icin TASARIM ile
    IZLEME birbirinden temiz ayrilir -- vekil, model, varsayim yok.
    Ucu de IRTIFA farkina cevrilir (irtifa = -z), isaret: + = YUKARIDA:
        tasarim = tgt_z - st_z     istasyonun HEDEFE gore irtifasi
        izleme  = st_z  - iris_z   aracin ISTASYONA gore irtifasi
        gercek  = tgt_z - iris_z   aracin HEDEFE gore irtifasi
    ve OZDESLIK gecerlidir:  gercek = tasarim + izleme.
    """
    R = []
    for y in sorted(glob.glob(os.path.join(BBOX_DIZIN, "gps_guidance_*.csv"))):
        m = re.search(r"(\d{8}_\d{6})", os.path.basename(y))
        if not m or m.group(1) < sonra:
            continue
        try:
            with open(y, encoding="utf-8", errors="replace") as f:
                prev = None
                for r in csv.DictReader(f):
                    d = {k: _f(r.get(k)) for k in
                         ("menzil", "t", "dt", "iris_z", "tgt_z", "st_z",
                          "vx_cmd", "vy_cmd", "vz_cmd", "ist_elev_deg")}
                    if any(d[k] != d[k] for k in ("menzil", "iris_z", "tgt_z", "st_z")):
                        prev = None
                        continue
                    if prev is not None and 0 < d["t"] - prev["t"] < 1.0:
                        dt = max(d["dt"], 1e-3)
                        d["dv"] = math.sqrt(sum((d[k] - prev[k]) ** 2 for k in
                                                ("vx_cmd", "vy_cmd", "vz_cmd"))) / dt
                        d["dvz"] = abs(d["vz_cmd"] - prev["vz_cmd"]) / dt
                        d["dvh"] = math.hypot(d["vx_cmd"] - prev["vx_cmd"],
                                              d["vy_cmd"] - prev["vy_cmd"]) / dt
                    prev = d
                    R.append(d)
        except OSError:
            continue
    if not R:
        print("\n--- GPS YASASI: log yok ---")
        return
    print("\n--- GPS YASASI: TASARIM / IZLEME AYRIMI (kendi logundan) ---")
    print("%8s %6s %9s %9s %9s %8s | %8s %8s" %
          ("menzil", "n", "tasarim", "izleme", "gercek", "elev", "tavanda", "dikeye"))
    for lo, hi in ((0, 4), (4, 8), (8, 15), (15, 30)):
        G = [x for x in R if lo <= x["menzil"] < hi]
        if not G:
            continue
        S = [x for x in G if x.get("dv", 0.0) >= MAX_ACCEL * 0.98]
        print("%3d-%-4d %6d %9.2f %9.2f %9.2f %8.1f | %7.1f%% %8.2f" % (
            lo, hi, len(G),
            med([x["tgt_z"] - x["st_z"] for x in G]),
            med([x["st_z"] - x["iris_z"] for x in G]),
            med([x["tgt_z"] - x["iris_z"] for x in G]),
            med([x["ist_elev_deg"] for x in G]),
            100.0 * len(S) / max(1, len([x for x in G if "dv" in x])),
            med([x["dvz"] for x in S]) if S else float("nan")))
    print("  hepsi IRTIFA farki, + = YUKARIDA.  gercek = tasarim + izleme")
    print("  tasarim = istasyonun hedefe gore irtifasi (yasanin ISTEDIGI)")
    print("  izleme  = aracin istasyona gore irtifasi (yasanin KACIRDIGI)")
    print("  dikeye  = ivme TAVANINDAKI tiklerde dikeye kalan |d(vz_cmd)/dt| medyani")


def vz_istenen(tik):
    """Kirpma ONCESI dikey komut. Tutus dali BIREBIR; terminal dali
    K_VZ_D*iris_vz terimi loglanmadigi icin YAKLASIK (o yuzden ayri sayilir)."""
    if tik["durum"] == "TERMINAL":
        return None                       # olculmedi (bkz. docstring)
    return max(-VZ_MAX, min(VZ_MAX, K_VZ * V_NOM * tik["eps_elev"]))


def pencere(T, t0, t1):
    """Zaman penceresindeki GECERLI tikler (KURTARMA satirlari haric)."""
    return [x for x in T if t0 <= x["t"] <= t1 and not x.get("gecersiz")]


# ══════════════════════════════════════════════════════════════════════
#  MEKANIZMA KAPILARI -- "yama gercekten devreye girdi mi?"
# ══════════════════════════════════════════════════════════════════════
#  Gazebo ekibinin O6 dersi: bir ozelligi KIYASLAMADAN once devreye
#  girdigini KANITLA. Iki yamanin da logda birakmasi gereken iz belli:
#
#  A) AVCI_ACCEL_SPLIT=1  -> tek 3B tavan yerine 12 yatay / 10 dikey.
#     Tek tavanda |d(v_cmd)/dt| <= 12.0 YAPISAL olarak asilamaz; split ile
#     bileske sqrt(12^2+10^2)=15.6'ya cikabilir.
#     TABAN OLCUMU (split kapali, 2026-08-17, n=10823 tik): >12.25 orani %0.00,
#     p99 = 12.17 (fazlasi CSV yuvarlamasi: vz 2 ondalik / dt bolumu).
#     KAPI: >12.5 m/s^2 tik orani belirgin sekilde 0'dan buyuk olmali.
#
#  B) AVCI_IBVS_TERM_DIKEY>0 -> nisan pikseli menzille kayar.
#     KAPI: cy_nisan sutunu CY_NISAN'dan (301) sapmali. Sapma yoksa ya env
#     surece gecmemistir (bayat sunucu) ya da menzil vekili hic esigin
#     altina inmemistir.
def kapilar(sonra):
    print("=" * 78)
    print("MEKANIZMA KAPILARI (>= %s)" % sonra)
    print("=" * 78)
    n = ust = 0
    cyn, sapan = [], 0
    for y in sorted(glob.glob(os.path.join(BBOX_DIZIN, "bbox_ibvs_*.csv"))):
        m = re.search(r"(\d{8}_\d{6})", os.path.basename(y))
        if not m or m.group(1) < sonra:
            continue
        try:
            with open(y, encoding="utf-8", errors="replace") as f:
                rows = list(csv.DictReader(f))
        except OSError:
            continue
        for i, r in enumerate(rows):
            if "cy_nisan" in r and r["cy_nisan"] not in (None, ""):
                v = _f(r["cy_nisan"])
                if v == v:
                    cyn.append(v)
                    if abs(v - CY_NISAN) > 1.0:
                        sapan += 1
            if i == 0:
                continue
            a = rows[i - 1]
            # ⚠ KURTARMA satirlarinda komut alanlari BOS yazilir. Bosu 0.0
            #   saymak sahte 100+ m/s^2 sicramalari uretir (bir kez dustum:
            #   kapi %2.47 gosterdi, gercegi %0.00).
            v = [_f(r.get(k)) for k in ("vx_cmd", "vy_cmd", "vz_cmd")]
            u = [_f(a.get(k)) for k in ("vx_cmd", "vy_cmd", "vz_cmd")]
            if any(x != x for x in v + u):
                continue
            dt = _f(r.get("dt"), 0.05)
            d = math.sqrt(sum((x - y) ** 2 for x, y in zip(v, u)))
            if dt > 1e-3:
                n += 1
                if d / dt > 12.5:
                    ust += 1
    if n:
        print("A) IVME: |d(v_cmd)/dt| > 12.5 m/s^2 olan tik orani = %%%.3f  (n=%d)"
              % (100.0 * ust / n, n))
        print("   split KAPALI beklentisi ~%0.00 | split ACIK beklentisi belirgin >0")
    if cyn:
        print("B) NISAN: cy_nisan medyan %.1f (CY_NISAN=%.0f) | sapan tik %%%.1f (n=%d)"
              % (med(cyn), CY_NISAN, 100.0 * sapan / len(cyn), len(cyn)))
        print("   rampa KAPALI beklentisi %0.0 sapma | rampa ACIK beklentisi >0")
    else:
        print("B) NISAN: cy_nisan sutunu YOK -> ya eski log ya da yama devrede degil")


# ══════════════════════════════════════════════════════════════════════
#  3) RAMPA BOYUTLANDIRMA -- dikey kanalin OLCULEN cevabiyla benzetim
# ══════════════════════════════════════════════════════════════════════
#  Kanal: olu zaman 0.08 s + birinci mertebe tau 0.64 s (olculmus).
#  Kapanma: 9.87 m/s (bu betigin CPA olcumu).
#  Yasa   : gorsel TUTUS -> vz = K_VZ*V_NOM*eps  (eps = nisan_yuk - hedef_yuk)
#  Rampa  : nisanin DUNYA yukselisi W0, k=clamp(menzil/R0,0,1) ile 0'a surulur.
V_KAPANMA = 9.87
OLU_S, TAU_S = 0.08, 0.64


def benzet(R0, W0_deg=-11.21, a_v=1.45, R_bas=20.0, z0=-1.25, hz=50.0,
           vzmax=VZ_MAX):
    """R_bas menzilinden CPA'ya kadar dikey ekseni cozer.
    R0=0 -> rampa KAPALI (bugunku davranis). Doner: CPA'daki dz (m, + = ustte).

    BASLANGIC KOSULU OLCUMDEN: gorsel faz ~20 m'de devralir ve o an arac
    hedefin 1.25 m ALTINDADIR (VISUAL CPA'larin dz(-2 s) medyani). Dengede
    baslatmak (z=-R*tan(W0)) yanlis olur -- yasa dengesine hic ulasmiyor."""
    dt = 1.0 / hz
    W0 = math.radians(W0_deg)
    R = R_bas
    z = z0
    vz_act, vz_cmd = 0.0, 0.0
    kuyruk = [0.0] * max(1, int(round(OLU_S / dt)))
    while R > 0.05:
        k = 1.0 if R0 <= 0.0 else min(1.0, R / R0)
        W = W0 * k
        E_t = math.atan2(-z, max(R, 0.05))          # hedefin DUNYA yukselisi
        eps = W - E_t
        hedef_cmd = max(-vzmax, min(vzmax, K_VZ * V_NOM * eps))
        d = max(-a_v * dt, min(a_v * dt, hedef_cmd - vz_cmd))
        vz_cmd += d
        kuyruk.append(vz_cmd)
        gecikmeli = kuyruk.pop(0)
        vz_act += (gecikmeli - vz_act) * (dt / TAU_S)
        z -= vz_act * dt                             # NED asagi+ -> z yukari
        R -= V_KAPANMA * dt
    return z


def boyutlandir():
    print("\n" + "=" * 78)
    print("RAMPA BOYUTLANDIRMA (dikey kanal: olu %.2f s + tau %.2f s, "
          "kapanma %.2f m/s)" % (OLU_S, TAU_S, V_KAPANMA))
    print("=" * 78)
    print("Yasa dengesi W0 = %+.2f deg (olculen pitch medyanindan)." % -11.21)
    print("Baslangic: 20 m'de dz = -1.25 m (olculen devir durumu).")
    print("Dikey ivme butcesi: TEK 3B tavanin gorsel fazda BIRAKTIGI 1.45 m/s^2 "
          "(olculdu, doymus tikler)\nve SPLIT ile 10.0 m/s^2.\n")
    print("%8s | %14s | %14s | %s" %
          ("R0 (m)", "a_v=1.45", "a_v=10.0", "rampa omru (s)"))
    print("%8s-+-%14s-+-%14s-+-%s" % ("-" * 8, "-" * 14, "-" * 14, "-" * 14))
    for R0 in (0.0, 4.0, 6.0, 8.0, 10.0, 12.0, 15.0, 20.0):
        a = benzet(R0, a_v=1.45)
        b = benzet(R0, a_v=10.0)
        ad = "KAPALI" if R0 <= 0 else "%.0f" % R0
        omr = "-" if R0 <= 0 else "%.2f" % (min(R0, 20.0) / V_KAPANMA)
        print("%8s | %+8.2f m     | %+8.2f m     | %s" % (ad, a, b, omr))
    print("\nOKUMA: R0=KAPALI satiri BUGUNKU davranistir; olculen VISUAL CPA "
          "medyani (+0.84 m) ile\nkarsilastirilarak modelin gecerliligi sinanir.")
    print("Kanal cevabi olu+tau = %.2f s -> %.2f m; rampa bunun altinda kalirsa "
          "komut yolda yenir." % (OLU_S + TAU_S, (OLU_S + TAU_S) * V_KAPANMA))

    # ── DEVIR DURUMU DAGILIMI: tek yorunge yaniltir ──
    # Olculen dz(-2 s) dagilimi p10 .. p90 araligini tarar. Rampanin asil
    # kazanci MEDYANI degil, YUKARI KUYRUGU kesmesidir: rampa yokken yasanin
    # cekim noktasi +R*tan(11.2 deg), yani menzil buyudukce YUKARI kaciyor.
    print("\n%10s | %s" % ("z0 (m)", "CPA'da dz  (a_v=10.0)"))
    z0lar = (-2.5, -1.25, 0.0, 1.0, 2.0)
    bas = "%10s |" % ""
    for R0 in (0.0, 8.0, 12.0, 20.0):
        bas += " %8s" % ("KAPALI" if R0 <= 0 else "R0=%.0f" % R0)
    print(bas)
    ort = {R0: [] for R0 in (0.0, 8.0, 12.0, 20.0)}
    for z0 in z0lar:
        sat = "%10.2f |" % z0
        for R0 in (0.0, 8.0, 12.0, 20.0):
            v = benzet(R0, a_v=10.0, z0=z0)
            ort[R0].append(abs(v))
            sat += " %+8.2f" % v
        print(sat)
    sat = "%10s |" % "|dz| ort"
    for R0 in (0.0, 8.0, 12.0, 20.0):
        sat += " %8.2f" % (sum(ort[R0]) / len(ort[R0]))
    print(sat)


# ══════════════════════════════════════════════════════════════════════
def main():
    global CPA_ESIK
    ap = argparse.ArgumentParser()
    ap.add_argument("--sonra", default="20260817_110320",
                    help="bu zaman damgasindan sonraki kayitlar (YYYYMMDD_HHMMSS)")
    ap.add_argument("--esik", type=float, default=CPA_ESIK)
    ap.add_argument("--sim", action="store_true", help="yalniz rampa boyutlandirma")
    ap.add_argument("--kapi", action="store_true",
                    help="yalniz mekanizma kapilari (yama devreye girdi mi?)")
    a = ap.parse_args()
    CPA_ESIK = a.esik
    if a.sim:
        boyutlandir()
        return
    if a.kapi:
        kapilar(a.sonra)
        return

    izler = [y for y in sorted(glob.glob(os.path.join(IZ_DIZIN, "hedef_iz_*.csv")))
             if re.search(r"(\d{8}_\d{6})", os.path.basename(y))
             and re.search(r"(\d{8}_\d{6})", os.path.basename(y)).group(1) >= a.sonra]
    print("=" * 78)
    print("DIKEY AYRISTIRMA  |  %d iz kaydi (>= %s)" % (len(izler), a.sonra))
    print("=" * 78)

    T = bbox_oku(a.sonra)
    print("bbox tik sayisi: %d" % len(T))

    hepsi = []
    for y in izler:
        R = iz_oku(y)
        if len(R) < 50:
            continue
        for o in cpa_bul(R):
            o["dosya"] = os.path.basename(y)
            hepsi.append(o)
    if not hepsi:
        print("CPA olayi yok.")
        return

    vis = [o for o in hepsi if str(o["faz"]).startswith("VIS")]
    gps = [o for o in hepsi if not str(o["faz"]).startswith("VIS")]

    print("\n--- CPA OZETI (r < %.0f m yerel minimumlar) ---" % CPA_ESIK)
    print("%-8s %5s %8s %8s %8s %8s %8s" %
          ("grup", "n", "r_med", "yatay", "dz_med", "dz_p10", "dz_p90"))
    for ad, G in (("HEPSI", hepsi), ("VISUAL", vis), ("GPS", gps)):
        if not G:
            continue
        print("%-8s %5d %8.2f %8.2f %8.2f %8.2f %8.2f" % (
            ad, len(G), med([o["r"] for o in G]), med([o["rh"] for o in G]),
            med([o["dz"] for o in G]), yuzde([o["dz"] for o in G], 0.10),
            yuzde([o["dz"] for o in G], 0.90)))
    alt = sum(1 for o in hepsi if o["dz"] < 0)
    print("arac hedefin ALTINDA: %d/%d = %%%.1f" %
          (alt, len(hepsi), 100.0 * alt / len(hepsi)))
    print("kapanma hizi medyan: %.2f m/s" % med([o["kapanma"] for o in hepsi]))

    print("\n--- DIKEY KAPANMA BUTCESI (isaret: + = arac yukarida) ---")
    print("%-8s %10s %10s %10s %10s" %
          ("grup", "dz(-2s)", "dz(-1s)", "dz(-0.72s)", "dz(CPA)"))
    for ad, G in (("HEPSI", hepsi), ("VISUAL", vis), ("GPS", gps)):
        if not G:
            continue
        print("%-8s %10.2f %10.2f %10.2f %10.2f" % (
            ad, med([o["dz_2s"] for o in G]), med([o["dz_1s"] for o in G]),
            med([o["dz_taahhut"] for o in G]), med([o["dz"] for o in G])))
    kap = [o["dz"] - o["dz_taahhut"] for o in hepsi]
    print("son %.2f s'de KAPATILAN dikey: medyan %+.2f m (p10 %+.2f, p90 %+.2f)"
          % (T_TAAHHUT, med(kap), yuzde(kap, .10), yuzde(kap, .90)))

    # ── yasa teshisi: CPA'lardan geriye bakan pencereler ──
    print("\n--- YASA TESHISI (CPA oncesi %.2f s penceresi, bbox logu) ---" % T_TAAHHUT)
    sat = []          # ivme tavaninda gecen tik orani
    dvz_hepsi, eps_hepsi, kirp_hepsi, vzc_hepsi, vzi_hepsi = [], [], [], [], []
    term_n = tik_n = 0
    for o in hepsi:
        W = pencere(T, o["t"] - T_TAAHHUT, o["t"])
        if len(W) < 3:
            continue
        for x in W:
            tik_n += 1
            if x["durum"] == "TERMINAL":
                term_n += 1
            if x["dv"] == x["dv"]:
                sat.append(1.0 if x["dv"] >= MAX_ACCEL * 0.98 else 0.0)
                dvz_hepsi.append(x["dvz"])
            eps_hepsi.append(math.degrees(x["eps_elev"]))
            vzc_hepsi.append(x["vz"])
            vi = vz_istenen(x)
            if vi is not None:
                vzi_hepsi.append(vi)
                kirp_hepsi.append(vi - x["vz"])
    if tik_n:
        print("pencere tik sayisi %d | TERMINAL %%%.1f | ivme tavaninda %%%.1f"
              % (tik_n, 100.0 * term_n / tik_n,
                 100.0 * sum(sat) / max(len(sat), 1)))
        # MEKANIZMA KAPISI TABANI: split acilinca bu sayilar YUKSELMELI
        doy = [x["dvz"] for o in hepsi
               for x in pencere(T, o["t"] - T_TAAHHUT, o["t"])
               if x.get("dv", float("nan")) >= MAX_ACCEL * 0.98]
        if doy:
            print("DOYMUS tiklerde dikeye kalan |d(vz)/dt|: medyan %.2f  "
                  "p90 %.2f  p99 %.2f  m/s^2  (n=%d)"
                  % (med(doy), yuzde(doy, .90), yuzde(doy, .99), len(doy)))
        print("|d(vz_cmd)/dt| : medyan %.2f  p90 %.2f  p99 %.2f  max %.2f  m/s^2"
              % (med(dvz_hepsi), yuzde(dvz_hepsi, .90),
                 yuzde(dvz_hepsi, .99), max(dvz_hepsi) if dvz_hepsi else float("nan")))
        print("eps_elev (deg) : medyan %+.2f  p10 %+.2f  p90 %+.2f"
              % (med(eps_hepsi), yuzde(eps_hepsi, .10), yuzde(eps_hepsi, .90)))
        print("vz_cmd (m/s)   : medyan %+.2f  p10 %+.2f  p90 %+.2f"
              % (med(vzc_hepsi), yuzde(vzc_hepsi, .10), yuzde(vzc_hepsi, .90)))
        if kirp_hepsi:
            print("vz_ist - vz_cmd: medyan %+.2f  p90 %+.2f  (TUTUS dali, n=%d)"
                  % (med(kirp_hepsi), yuzde(kirp_hepsi, .90), len(kirp_hepsi)))
            print("   -> kirpma kaybi ~ %+.2f m  (%.2f s boyunca)"
                  % (med(kirp_hepsi) * T_TAAHHUT, T_TAAHHUT))

    # ── tasarim ofseti: yasanin DENGE noktasi ──
    print("\n--- TASARIM OFSETI (gorsel TUTUS yasasinin denge nisani) ---")
    b_el = math.degrees(piksel_elev(CY_NISAN))
    print("CY_NISAN=%.0f px -> GOVDE cercevesinde LOS yukselisi %+.3f deg"
          % (CY_NISAN, b_el))
    W = [x for x in T if x["durum"] != "TERMINAL" and not x.get("gecersiz")]
    if W:
        pit = [math.degrees(x["pitch"]) for x in W]
        dunya = [b_el + p for p in pit]
        print("iris_pitch (tum IBVS tikleri, n=%d): medyan %+.2f  p10 %+.2f  p90 %+.2f"
              % (len(pit), med(pit), yuzde(pit, .10), yuzde(pit, .90)))
        print("denge DUNYA yukselisi = %+.3f + pitch : medyan %+.2f deg"
              % (b_el, med(dunya)))
        print("   NEGATIF => hedef ufkun ALTINDA tutuluyor => arac hedefin USTUNDEN gecer")
        for R in (4.0, 6.0, 8.0, 10.0):
            print("   menzil %4.1f m'de tasarim ofseti = %+.2f m (arac hedefin USTUNDE)"
                  % (R, -R * math.tan(math.radians(med(dunya)))))

    # ── CPA basina: taahhut aninda tasarim vs gercek ──
    # ⚠ MENZIL: hedef_iz TRUTH'undan alinir, kutu boyutu vekilinden DEGIL.
    #   Vekil (MENZIL_PX_M/boyut) ayrica kalibre edilir (asagida).
    print("\n--- TAAHHUT ANINDA (CPA-%.2f s) TASARIM vs GERCEK ---" % T_TAAHHUT)
    vd, vg, ve, vr = [], [], [], []
    for o in vis:
        Wp = pencere(T, o["t"] - T_TAAHHUT - 0.3, o["t"] - T_TAAHHUT + 0.3)
        Wp = [x for x in Wp if x["durum"] != "TERMINAL"]
        if len(Wp) < 2 or o["r_taahhut"] != o["r_taahhut"]:
            continue
        pit = med([x["pitch"] for x in Wp])
        Rp = o["r_taahhut"]
        tas = -Rp * math.tan(piksel_elev(CY_NISAN) + pit)
        vd.append(tas)
        vg.append(o["dz_taahhut"])
        ve.append(o["dz_taahhut"] - tas)
        vr.append(Rp)
    if vd:
        print("VISUAL n=%d | menzil(truth) %.1f m" % (len(vd), med(vr)))
        print("  tasarim ofseti  %+.2f m   (yasanin denge nisani, o menzilde)" % med(vd))
        print("  gercek dz       %+.2f m" % med(vg))
        print("  izleme hatasi   %+.2f m   (gercek - tasarim)" % med(ve))

    gps_ayristir(a.sonra)

    # ── MENZIL VEKILI KALIBRASYONU (yeni rampanin menzil kaynagi) ──
    print("\n--- MENZIL VEKILI: MENZIL_PX_M/boyut vs TRUTH ---")
    par = []
    for y in izler:
        R = iz_oku(y)
        if len(R) < 50:
            continue
        for x in T:
            if x.get("gecersiz") or x["boyut"] <= 1e-6 or x["kopru"] >= 0.5:
                continue
            if not (R[0]["t"] <= x["t"] <= R[-1]["t"]):
                continue
            rt = r_at(R, x["t"])
            if 3.0 <= rt <= 30.0:
                par.append((rt, 202.6 / x["boyut"], x["boyut"]))
    if par:
        oran = [v / t for t, v, _ in par]
        pxm = [t * b for t, _, b in par]
        print("n=%d | vekil/truth: medyan %.2f  p10 %.2f  p90 %.2f"
              % (len(par), med(oran), yuzde(oran, .10), yuzde(oran, .90)))
        print("olculen px*m carpani (boyut*menzil_truth): medyan %.0f  "
              "(kodda MENZIL_PX_M=202.6)" % med(pxm))
        for lo, hi in ((3, 6), (6, 10), (10, 15), (15, 30)):
            g = [t * b for t, _, b in par if lo <= t < hi]
            if g:
                print("   truth %2d-%2d m -> px*m medyan %5.0f  (n=%d)"
                      % (lo, hi, med(g), len(g)))

    # ── |dz| ve esik taramasi: "1.19 m" hangi tanimla cikiyor? ──
    print("\n--- |dz| MEDYANI, CPA ESIGINE GORE ---")
    print("%6s %6s %8s %8s %8s %8s" %
          ("esik", "n", "|dz|med", "dz_med", "alt%", "yatay"))
    for e in (2.0, 3.0, 4.0, 6.0, 8.0, 12.0):
        G = [o for o in hepsi if o["r"] <= e]
        if not G:
            continue
        print("%6.0f %6d %8.2f %+8.2f %7.0f%% %8.2f" % (
            e, len(G), med([abs(o["dz"]) for o in G]), med([o["dz"] for o in G]),
            100.0 * sum(1 for o in G if o["dz"] < 0) / len(G),
            med([o["rh"] for o in G])))
    for ad, G in (("VISUAL", vis), ("GPS", gps)):
        G3 = [o for o in G if o["r"] <= 3.0]
        if G3:
            print("  r<=3 %-6s n=%-3d |dz|med %.2f  dz_med %+.2f  alt %%%.0f" % (
                ad, len(G3), med([abs(o["dz"]) for o in G3]),
                med([o["dz"] for o in G3]),
                100.0 * sum(1 for o in G3 if o["dz"] < 0) / len(G3)))

    print("\n--- CPA LISTESI ---")
    print("%-8s %9s %7s %7s %7s %7s %6s" %
          ("dosya", "t", "r", "yatay", "dz", "dz-0.72", "faz"))
    for o in sorted(hepsi, key=lambda z: z["t"]):
        print("%-8s %9.1f %7.2f %7.2f %+7.2f %+7.2f %6s" %
              (o["dosya"][-10:-4], o["t"], o["r"], o["rh"], o["dz"],
               o["dz_taahhut"], str(o["faz"])[:6]))


if __name__ == "__main__":
    main()

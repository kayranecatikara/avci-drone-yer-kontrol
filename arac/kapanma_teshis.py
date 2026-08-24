# -*- coding: utf-8 -*-
"""
================================================================================
  KAPANMA TESHISI  --  hedefe yaklasiyor muyuz, uzaklasiyor muyuz?
================================================================================
Onceki iki olcum:
  * arac zamanin %26'sinda KENDI BURNUNA GORE GERI gidiyor
  * ama burun hedeften SAPMIYOR (ortanca 11.8 der, kadraj disi yalniz %4.2)
Ikisi birlikte sunu ima eder: HEDEFE BAKARKEN ONDAN UZAKLASIYORUZ.
Bu betik onu dogrudan olcer -- yorum degil, dr/dt.

    r  = |biz - hedef|
    dr/dt < 0  -> kapaniyoruz (iyi)
    dr/dt > 0  -> aciliyoruz  (kotu)

Ayrica "asim" (overshoot) aranir: hedef ekseninde konumumuz s, negatiften
pozitife gecerse hedefi GECMISIZ demektir. Gecis sayisi ve gecis anindaki
menzil, "onune gecip sonra arkaya dusuyor" sikayetinin olculmus halidir.

⚠ SICRAMA SUZGECI: yeniden dogus konumu isinlar -> |dr/dt| tavani.
⚠ DONMUS TELEMETRI suzgeci: ardisik ayni imza atilir.
⚠ Bu log turunde vis_* kolonlari BOS cikabilir; tespit istatistigi burada
  ARANMAZ (bkz. arac/burun_tespit_bagi.py notu).
================================================================================
"""
import csv
import glob
import math
import os
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CM = 100.0
DT_MIN, DT_MAX = 0.02, 0.60
DR_TAVAN = 60.0              # m/s, ustu = sicrama
HIZ_TAVAN = 45.0


def f(s):
    try:
        v = float(s)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def y(v, q):
    if not v:
        return float("nan")
    s = sorted(v)
    return s[min(len(s) - 1, max(0, int(round(q * (len(s) - 1)))))]


def main():
    yol = sys.argv[1] if len(sys.argv) > 1 else None
    if not yol:
        lst = sorted(glob.glob(os.path.join(KOK, "veri", "ucus_log_*.csv")),
                     key=os.path.getmtime)
        if not lst:
            print("ucus_log_*.csv yok"); return
        yol = lst[-1]
    print("[KAPANMA] %s" % os.path.basename(yol))

    ham, onceki = [], None
    with open(yol, newline="", encoding="utf-8", errors="replace") as fh:
        for r in csv.DictReader(fh):
            d = f(r.get("gercek_mesafe"))
            dx, dy, dz = f(r.get("drone_x")), f(r.get("drone_y")), f(r.get("drone_z"))
            tx, ty, tz = f(r.get("true_tx")), f(r.get("true_ty")), f(r.get("true_tz"))
            t = f(r.get("t_perf")) or f(r.get("t_wall"))
            if None in (d, dx, dy, tx, ty, t) or d <= 50.0:
                continue
            imza = (round(dx, 2), round(dy, 2), round(tx, 2), round(ty, 2))
            if imza == onceki:
                continue
            onceki = imza
            ham.append({"t": t, "dx": dx / CM, "dy": dy / CM,
                        "dz": (dz or 0) / CM, "tx": tx / CM, "ty": ty / CM,
                        "tz": (tz or 0) / CM, "r": d / CM,
                        "yaw": f(r.get("drone_yaw_deg"))})

    R, sicrama = [], 0
    for i in range(1, len(ham)):
        a, b = ham[i - 1], ham[i]
        dt = b["t"] - a["t"]
        if not (DT_MIN <= dt <= DT_MAX):
            continue
        dr = (b["r"] - a["r"]) / dt
        vx, vy = (b["dx"] - a["dx"]) / dt, (b["dy"] - a["dy"]) / dt
        tvx, tvy = (b["tx"] - a["tx"]) / dt, (b["ty"] - a["ty"]) / dt
        if abs(dr) > DR_TAVAN or math.hypot(vx, vy) > HIZ_TAVAN:
            sicrama += 1
            continue
        b["dr"] = dr
        b["vx"], b["vy"] = vx, vy
        b["tvx"], b["tvy"] = tvx, tvy
        R.append(b)

    print("[KAPANMA] ornek %d | sicrama atilan %d" % (len(R), sicrama))
    if len(R) < 100:
        print("[KAPANMA] yeterli veri yok"); return

    dr = [r["dr"] for r in R]
    acilan = sum(1 for x in dr if x > 0)
    print()
    print("  ── KAPANMA HIZI dr/dt ──")
    print("    ortanca %+.2f m/s | p10 %+.2f | p90 %+.2f" % (y(dr, .5), y(dr, .1), y(dr, .9)))
    print("    ACILIYOR (dr/dt>0) : %5.1f%%  (n=%d)" % (100.0 * acilan / len(dr), acilan))
    print("    kapaniyor          : %5.1f%%" % (100.0 * (len(dr) - acilan) / len(dr)))

    print()
    print("  ── MENZIL BANDINA GORE ──")
    print("    %-10s %12s %12s %10s" % ("menzil", "dr/dt ortanca", "aciliyor %", "n"))
    for lo, hi in ((0, 6), (6, 10), (10, 25), (25, 60), (60, 1e9)):
        alt = [r for r in R if lo <= r["r"] < hi]
        if not alt:
            continue
        v = [r["dr"] for r in alt]
        et = ("%d+ m" % lo) if hi > 1e8 else ("%d-%d m" % (lo, hi))
        print("    %-10s %+11.2f %11.1f%% %10d"
              % (et, y(v, .5), 100.0 * sum(1 for x in v if x > 0) / len(v), len(alt)))

    # ── ASIM: hedef ekseninde isaret degisimi ───────────────────────────────
    gecis, gecis_menzil = 0, []
    onceki_s = None
    for r in R:
        tsp = math.hypot(r["tvx"], r["tvy"])
        if tsp < 0.5:
            continue
        thx, thy = r["tvx"] / tsp, r["tvy"] / tsp
        s = (r["dx"] - r["tx"]) * thx + (r["dy"] - r["ty"]) * thy
        if onceki_s is not None and onceki_s < 0 <= s:
            gecis += 1
            gecis_menzil.append(r["r"])
        onceki_s = s
    print()
    print("  ── ASIM: hedefi kac kez GECTIK ──")
    print("    arkadan one gecis : %d kez" % gecis)
    if gecis_menzil:
        print("    gecis anindaki menzil: ortanca %.1f m | en yakin %.1f m"
              % (y(gecis_menzil, .5), min(gecis_menzil)))
        yakin = sum(1 for m in gecis_menzil if m < 25)
        print("    bunlarin %d tanesi 25 m icinde (%.0f%%)"
              % (yakin, 100.0 * yakin / len(gecis_menzil)))

    # ── en yakin gecisler (CPA) ─────────────────────────────────────────────
    cpa, i = [], 1
    while i < len(R) - 1:
        if R[i]["r"] < R[i - 1]["r"] and R[i]["r"] <= R[i + 1]["r"] and R[i]["r"] < 40:
            cpa.append(R[i]["r"])
            i += 30
        i += 1
    if cpa:
        print()
        print("  ── YAKIN GECISLER (yerel minimumlar, <40 m) ──")
        print("    gecis %d | CPA ortanca %.2f m | en iyi %.2f m | <3 m %.0f%%"
              % (len(cpa), y(cpa, .5), min(cpa),
                 100.0 * sum(1 for c in cpa if c < 3.0) / len(cpa)))


if __name__ == "__main__":
    main()

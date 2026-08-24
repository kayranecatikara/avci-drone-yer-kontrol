# -*- coding: utf-8 -*-
"""
================================================================================
  PN KIYAS  --  ab_pn.py'nin damgaladigi pencereleri OLCUMLE kiyaslar
================================================================================
Her ayar penceresi icin dort sayi cikarir:

  en_yakin    truth izden gercek en yakin gecis  (ASIL OLCUT)
  faz_omru    gorsel fazin ne kadar yasadigi
  lam_sisme   yasanin hesapladigi LOS hizi / GERCEK LOS hizi
              -> 1.0 saglikli. 5-10 arasi ise kestirim kendini besliyor
                 (burun kestirimi kovaliyor, kestirim burunla buyuyor).
  eps_max     hedefin kadraj kenarina ne kadar yaklastigi (61 = kenar)

⚠ EN YAKIN GECIS TEK BASINA YETMEZ: faz cok kisaysa yasa denenmemis demektir.
Bu yuzden faz_omru ile birlikte okunur.

CALISTIR  python arac/pn_kiyas.py
================================================================================
"""
import os
import csv
import glob
import json
import math
import bisect
import statistics as st

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IBVS = os.path.join(KOK, "kopru", "gazebo_kaynak", "logs")
PENCERE = os.path.join(KOK, "veri", "ab_pn_pencereler.json")


def truth_yukle():
    yl = sorted(glob.glob(os.path.join(KOK, "veri", "hedef_iz", "hedef_iz_*.csv")),
                key=os.path.getmtime)
    if not yl:
        return None
    R = []
    with open(yl[-1], newline="", encoding="utf-8", errors="replace") as f:
        for r in csv.DictReader(f):
            try:
                R.append((float(r["t_mutlak"]),
                          float(r["hx_m"]), float(r["hy_m"]), float(r["hz_m"]),
                          float(r["dx_m"]), float(r["dy_m"]), float(r["dz_m"])))
            except (KeyError, ValueError, TypeError):
                pass
    R.sort()
    return R


def coz(yol, R, T):
    rows = [x for x in csv.DictReader(open(yol, encoding="utf-8", errors="replace"))
            if x.get("t")]
    if len(rows) < 6:
        return None
    ts = [float(x["t"]) for x in rows]
    a, b = min(ts), max(ts)

    # en yakin gecis: faz + 1.5 s (en yakin nokta tespit kesildikten SONRA olabilir)
    men = []
    for t, hx, hy, hz, dx, dy, dz in R:
        if a <= t <= b + 1.5:
            men.append(math.dist((hx, hy, hz), (dx, dy, dz)))
    if not men:
        return None

    # LOS hizi: yasanin kendi kestirimi vs TRUTH
    def tlos(t):
        i = min(max(bisect.bisect_left(T, t), 1), len(R) - 1)
        _, hx, hy, _, dx, dy, _ = R[i]
        return math.degrees(math.atan2(hy - dy, hx - dx))

    kutulu = [x for x in rows if x.get("eps_yaw_deg") not in ("", None)]
    lam_yasa = lam_truth = None
    if len(kutulu) >= 8:
        tt = [float(x["t"]) for x in kutulu]
        yl_ = [(float(x["iris_yaw_deg"]) + float(x["eps_yaw_deg"]) + 540) % 360 - 180
               for x in kutulu]
        tl_ = [tlos(t) for t in tt]

        def hizlar(v):
            o = []
            for i in range(3, len(v)):
                dt = tt[i] - tt[i - 3]
                if dt > 1e-3:
                    o.append(abs(((v[i] - v[i - 3] + 540) % 360 - 180) / dt))
            return o
        hy_, ht_ = hizlar(yl_), hizlar(tl_)
        if hy_ and ht_:
            lam_yasa = sorted(hy_)[int(.95 * (len(hy_) - 1))]
            lam_truth = sorted(ht_)[int(.95 * (len(ht_) - 1))]

    eps = [abs(float(x["eps_yaw_deg"])) for x in kutulu]
    return {"t0": a, "sure": b - a, "kare": len(rows),
            "en_yakin": min(men),
            "eps_max": max(eps) if eps else 0.0,
            "sureklilik": len(kutulu) / len(rows),
            "lam_yasa": lam_yasa, "lam_truth": lam_truth}


def main():
    R = truth_yukle()
    if not R:
        print("  truth iz yok."); return
    T = [x[0] for x in R]
    if not os.path.exists(PENCERE):
        print("  %s yok — once arac/ab_pn.py kos." % PENCERE); return
    pencereler = json.load(open(PENCERE, encoding="utf-8"))

    hepsi = []
    for y in sorted(glob.glob(os.path.join(IBVS, "bbox_ibvs_*.csv")),
                    key=os.path.getmtime):
        d = coz(y, R, T)
        if d:
            hepsi.append(d)

    print("=" * 78)
    print("  PN A/B KIYASI — %d gorsel faz, %d ayar penceresi"
          % (len(hepsi), len(pencereler)))
    print("=" * 78)
    print("  %-13s %4s %7s %8s %8s %8s %9s"
          % ("ayar", "faz", "omur", "en_yakin", "en_iyi", "eps_max", "lam_sisme"))
    print("  " + "-" * 74)
    for p in pencereler:
        ic = [d for d in hepsi if p["t0"] <= d["t0"] <= p["t1"]]
        if not ic:
            print("  %-13s %4d   (bu pencerede gorsel faz olmadi)" % (p["ad"], 0))
            continue
        ey = [d["en_yakin"] for d in ic]
        sis = [d["lam_yasa"] / d["lam_truth"] for d in ic
               if d["lam_yasa"] and d["lam_truth"] and d["lam_truth"] > 1e-6]
        print("  %-13s %4d %6.2fs %7.2fm %7.2fm %7.0f° %8s"
              % (p["ad"], len(ic), st.median([d["sure"] for d in ic]),
                 st.median(ey), min(ey),
                 st.median([d["eps_max"] for d in ic]),
                 ("%.1fx" % st.median(sis)) if sis else "-"))
    print("  " + "-" * 74)
    print("  ayarlar:")
    for p in pencereler:
        print("    %-13s %s" % (p["ad"], p["ayar"]))
    print()
    print("  OKUMA: en_yakin ASIL olcut; omur cok kisaysa yasa denenmemistir.")
    print("         lam_sisme 1.0 saglikli, buyukse LOS kestirimi kendini besliyor.")


if __name__ == "__main__":
    main()

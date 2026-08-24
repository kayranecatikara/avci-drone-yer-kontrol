# -*- coding: utf-8 -*-
"""
================================================================================
  BURUN <-> TESPIT BAGI  --  "geri gidiyor" gorsel gudumu mu kiriyor?
================================================================================
Onceki olcum (arac/onde_arkada_teshis.py): arac zamanin %26'sinda KENDI BURNUNA
GORE GERI gidiyor, 25 m icinde %22.

HIPOTEZ: kamera BURNUN baktigi yere bakar. Govde hedefe dogru suzulurken burun
baska yone bakiyorsa hedef kadrajdan cikar -> tespit kopar -> gorsel faz duser.
Yani "geri gidiyor" ile "gorsel gudum kesiliyor" AYNI olayin iki yuzu olabilir.

BU BETIK SUNU OLCER:
  1) burun hedeften kac derece sapmis (nose_off_true) ve bu FOV yariciapini
     asiyor mu (FOV 122.08 -> yaricap 61.04 der)
  2) ileri giderken vs geri giderken TESPIT ORANI (vis_gordu)
  3) sapmanin menzile gore dagilimi
  4) tespit kaybi ile burun sapmasi arasindaki bag

⚠ TESPIT ORANI SADE OKUNMAZ: hedef kadraj DISINDAYKEN tespit dogal olarak 0
  cikar ve bu dedektorun sucu degildir (bkz. talon-olcum-tuzaklari #9).
  Bu yuzden tespit orani DAIMA |sapma| < FOV/2 kosuluyla da ayrica verilir.

⚠ SICRAMA SUZGECI: konum turevi yeniden dogusta 3000+ m/s uretiyor.
  HIZ_TAVAN ustu ornekler atilir.
================================================================================
"""
import csv
import glob
import math
import os
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CM = 100.0
FOV_YARICAP = 61.04          # 122.08 / 2  (olculmus FOV)
HIZ_TAVAN = 45.0             # m/s ustu = yeniden dogus sicramasi
HIZ_MIN = 0.5
DT_MIN, DT_MAX = 0.02, 0.60


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
    print("[BAG] %s" % os.path.basename(yol))

    ham, onceki = [], None
    with open(yol, newline="", encoding="utf-8", errors="replace") as fh:
        for r in csv.DictReader(fh):
            d = f(r.get("gercek_mesafe"))
            dx, dy = f(r.get("drone_x")), f(r.get("drone_y"))
            tx, ty = f(r.get("true_tx")), f(r.get("true_ty"))
            t = f(r.get("t_perf")) or f(r.get("t_wall"))
            if None in (d, dx, dy, tx, ty, t) or d <= 50.0:
                continue
            imza = (round(dx, 2), round(dy, 2), round(tx, 2), round(ty, 2))
            if imza == onceki:
                continue
            onceki = imza
            ham.append({"t": t, "dx": dx / CM, "dy": dy / CM,
                        "tx": tx / CM, "ty": ty / CM, "d": d / CM,
                        "yaw": f(r.get("drone_yaw_deg")),
                        "gordu": f(r.get("vis_gordu")),
                        "conf": f(r.get("vis_conf")),
                        "nose_off": f(r.get("nose_off_true")),
                        "yaw_err": f(r.get("yaw_err"))})

    R = []
    sicrama = 0
    for i in range(1, len(ham)):
        a, b = ham[i - 1], ham[i]
        dt = b["t"] - a["t"]
        if not (DT_MIN <= dt <= DT_MAX):
            continue
        vx, vy = (b["dx"] - a["dx"]) / dt, (b["dy"] - a["dy"]) / dt
        sp = math.hypot(vx, vy)
        if sp > HIZ_TAVAN:
            sicrama += 1
            continue
        if sp < HIZ_MIN or b["yaw"] is None:
            continue
        al = math.radians(b["yaw"])
        b["vf"] = vx * math.cos(al) + vy * math.sin(al)
        b["sp"] = sp
        # burun ile hedef kerterizi arasindaki aci (logdaki nose_off_true varsa o)
        ker = math.degrees(math.atan2(b["ty"] - b["dy"], b["tx"] - b["dx"]))
        sap = (ker - b["yaw"] + 180.0) % 360.0 - 180.0
        b["sapma"] = abs(sap)
        R.append(b)

    print("[BAG] kullanilan ornek %d | sicrama atilan %d" % (len(R), sicrama))
    if len(R) < 100:
        print("[BAG] yeterli veri yok"); return

    ileri = [r for r in R if r["vf"] >= 0]
    geri = [r for r in R if r["vf"] < 0]
    print()
    print("  ── 1) BURUN HEDEFTEN NE KADAR SAPIYOR ──")
    print("    tum ornekler : ortanca %5.1f der | p90 %5.1f der" % (y([r["sapma"] for r in R], .5),
                                                                   y([r["sapma"] for r in R], .9)))
    print("    ileri giderken: ortanca %5.1f der  (n=%d)" % (y([r["sapma"] for r in ileri], .5), len(ileri)))
    print("    GERI giderken : ortanca %5.1f der  (n=%d)" % (y([r["sapma"] for r in geri], .5), len(geri)))
    kd = sum(1 for r in R if r["sapma"] > FOV_YARICAP)
    kdi = sum(1 for r in ileri if r["sapma"] > FOV_YARICAP)
    kdg = sum(1 for r in geri if r["sapma"] > FOV_YARICAP)
    print()
    print("    KADRAJ DISI (sapma > %.1f der = FOV/2):" % FOV_YARICAP)
    print("      tum          : %5.1f%%" % (100.0 * kd / len(R)))
    print("      ileri giderken: %5.1f%%" % (100.0 * kdi / max(1, len(ileri))))
    print("      GERI giderken : %5.1f%%   <-- fark buysa bag KURULUR"
          % (100.0 * kdg / max(1, len(geri))))

    # 2) tespit orani
    def tespit(lst, sadece_ic=False):
        v = [r for r in lst if r["gordu"] is not None
             and (not sadece_ic or r["sapma"] < FOV_YARICAP)]
        if not v:
            return None, 0
        return 100.0 * sum(1 for r in v if r["gordu"] > 0.5) / len(v), len(v)

    print()
    print("  ── 2) TESPIT ORANI ──")
    for et, lst in (("tum", R), ("ileri giderken", ileri), ("GERI giderken", geri)):
        a, na = tespit(lst)
        b, nb = tespit(lst, sadece_ic=True)
        if a is None:
            continue
        print("    %-15s ham %5.1f%% (n=%d)  |  kadraj ICINDE %5.1f%% (n=%d)"
              % (et, a, na, b if b is not None else float("nan"), nb))

    # 3) menzile gore
    print()
    print("  ── 3) MENZILE GORE ──")
    print("    %-10s %10s %12s %12s" % ("menzil", "geri %", "sapma ortanca", "tespit(ic) %"))
    for lo, hi in ((0, 10), (10, 25), (25, 60), (60, 1e9)):
        alt = [r for r in R if lo <= r["d"] < hi]
        if not alt:
            continue
        g = 100.0 * sum(1 for r in alt if r["vf"] < 0) / len(alt)
        t, _ = tespit(alt, sadece_ic=True)
        et = ("%d+ m" % lo) if hi > 1e8 else ("%d-%d m" % (lo, hi))
        print("    %-10s %9.1f%% %12.1f %11s"
              % (et, g, y([r["sapma"] for r in alt], .5),
                 ("%.1f%%" % t) if t is not None else "-"))

    # 4) tespit kaybi ile sapma bagi
    gor = [r for r in R if r["gordu"] is not None and r["gordu"] > 0.5]
    yok = [r for r in R if r["gordu"] is not None and r["gordu"] <= 0.5]
    if gor and yok:
        print()
        print("  ── 4) TESPIT VAR/YOK ANLARINDA BURUN SAPMASI ──")
        print("    tespit VAR : sapma ortanca %5.1f der | geri orani %5.1f%%  (n=%d)"
              % (y([r["sapma"] for r in gor], .5),
                 100.0 * sum(1 for r in gor if r["vf"] < 0) / len(gor), len(gor)))
        print("    tespit YOK : sapma ortanca %5.1f der | geri orani %5.1f%%  (n=%d)"
              % (y([r["sapma"] for r in yok], .5),
                 100.0 * sum(1 for r in yok if r["vf"] < 0) / len(yok), len(yok)))


if __name__ == "__main__":
    main()

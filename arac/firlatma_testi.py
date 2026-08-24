# -*- coding: utf-8 -*-
"""FIRLATMA TESTI — "gorsel faz bizi hedeften atiyor mu?"

Kullanicinin tarifi: "kilit esnasinda araci duzgun takip etmiyor, alakasiz
baska yere gidiyor, sonra tekrar pesine takiliyor."

OLCULEN (16 Agu, 75 gecis, duzeltme ONCESI):
    t=-2.0s sapma  11°  menzil 12.9 m   <- hedefin uzerinde
    t=-0.5s sapma  95°  menzil 17.7 m
    t=+0.5s sapma 130°  menzil 39.8 m   <- neredeyse TERS yon
    t=+3.0s sapma   1°  menzil 59.4 m   <- toparladi ama 59 m'de
ve: gorsel faz basi 11.7 m -> sonu 32.1 m, 10/10 fazda UZAKLASMA.

BASARI OLCUTU: +0.5 s'teki sapma DUSMELI ve menzil artisi kaybolmali.
CALISTIR  python arac/firlatma_testi.py
"""
import csv, glob, os, math, bisect
import statistics as st

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def yukle():
    yl = sorted(glob.glob(os.path.join(KOK, "veri", "hedef_iz", "hedef_iz_*.csv")),
                key=os.path.getmtime)
    if not yl:
        return None, None
    R = []
    with open(yl[-1], newline="", encoding="utf-8", errors="replace") as f:
        for r in csv.DictReader(f):
            try:
                R.append((float(r["t_mutlak"]),
                          float(r["hx_m"]), float(r["hy_m"]), float(r["hz_m"]),
                          float(r["dx_m"]), float(r["dy_m"]), float(r["dz_m"]),
                          float(r["d_vx"]), float(r["d_vy"]),
                          (r.get("faz") or "").startswith("VIS")))
            except (KeyError, ValueError, TypeError):
                pass
    R.sort()
    return R, os.path.basename(yl[-1])


def main():
    R, ad = yukle()
    if not R or len(R) < 200:
        print("  truth iz yok/kisa."); return
    T = [x[0] for x in R]
    n = len(R)
    print("  %s  (%d ornek, %.0f s)" % (ad, n, R[-1][0] - R[0][0]))

    gecis = [i for i in range(1, n) if R[i - 1][9] and not R[i][9]]
    faz_bas = [i for i in range(1, n) if not R[i - 1][9] and R[i][9]]
    print("  gorsel faz: %d basladi, %d bitti" % (len(faz_bas), len(gecis)))
    if len(gecis) < 3:
        print("  yeterli gecis yok."); return

    def sap(i):
        a = R[i]
        if math.hypot(a[7], a[8]) < 3:
            return None
        los = math.degrees(math.atan2(a[2] - a[5], a[1] - a[4]))
        biz = math.degrees(math.atan2(a[8], a[7]))
        return abs((biz - los + 540) % 360 - 180)

    def menz(i):
        a = R[i]
        return math.dist((a[1], a[2], a[3]), (a[4], a[5], a[6]))

    print()
    print("  %8s %10s %11s   %s" % ("t (s)", "|sapma|", "menzil", "ONCEKI (duzeltme oncesi)"))
    print("  " + "-" * 62)
    eski = {-2.0: (11, 12.9), -0.5: (95, 17.7), 0.0: (120, 27.2),
            0.5: (130, 39.8), 1.0: (46, 50.6), 3.0: (1, 59.4)}
    for dt in (-2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0, 3.0, 5.0):
        S, M = [], []
        for gi in gecis:
            j = min(max(bisect.bisect_left(T, R[gi][0] + dt), 1), n - 1)
            s = sap(j)
            if s is not None:
                S.append(s); M.append(menz(j))
        if len(S) < 3:
            continue
        e = eski.get(dt)
        print("  %+7.1f %9.0f° %10.1f m   %s" % (
            dt, st.median(S), st.median(M),
            ("(onceki %3d° / %.1f m)" % e) if e else ""))
    print("  " + "-" * 62)

    # faz basi/sonu menzil farki
    fark = []
    for bi in faz_bas:
        son = next((g for g in gecis if g > bi), None)
        if son is None:
            continue
        fark.append(menz(son) - menz(bi))
    if fark:
        print("  FAZ BASI -> SONU menzil farki: medyan %+.1f m  (uzaklasan %d/%d)"
              % (st.median(fark), sum(1 for x in fark if x > 0), len(fark)))
        print("  ONCEKI: +21.1 m, uzaklasan 10/10")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
================================================================================
  TAKIP KALITESI  --  "hedefin uzerine mi gidiyoruz?" sorusunu olcer
================================================================================
NEDEN AYRI BIR ARAC
--------------------------------------------------------------------------------
pn_kiyas.py iska / omur / lam_sismesi veriyor. Ama 2026-08-16'da olculen kok
neden bunlarin hicbiri degil:

    tespit VARKEN  hiz yonu <-> hedefe olan yon : medyan  8.3°   (IYI)
    faz GENELINDE                               : medyan 56.4°, %24'u >90°

Yani yasa gordugu surece dogru gidiyor; gorsel fazin ~%60'inda kutu YOK ve o
karelerde son komut (YAW DAHIL) aynen tekrarlaniyor -> burun DONUYOR, hedef
kadrajda kaymaya devam ediyor, kutu kenara gidiyor, kor kaliyoruz.

Bu arac tam o farki olcer:
    * faz GENELINDE  |hiz yonu - hedefe yon|   <- ASIL OLCUT
    * tespitli karelerde ayni sayi              <- kiyas (bu zaten iyi)
    * KOR surede burun DONUYOR mu               <- kisir dongunun kaniti
    * tespitli gecen sure orani

⚠ CERCEVE: veri/hedef_iz HAM OYUN DUNYASI. Bu dosya HER SEYI orada tutar
   (konum, hiz vektoru, LOS) -> NED aynasina hic girmez. Guduum logundan
   sadece ZAMAN ve tespit VARLIGI okunur, aci OKUNMAZ.

CALISTIR
    python arac/takip_kalitesi.py                 son ucus, faz bazinda
    python arac/takip_kalitesi.py --pencere       ab_pn_pencereler.json ile ayar bazinda
================================================================================
"""
import os
import csv
import glob
import json
import math
import bisect
import argparse
import statistics as st

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IZ_DIR = os.path.join(KOK, "veri", "hedef_iz")
IBVS_DIR = os.path.join(KOK, "kopru", "gazebo_kaynak", "logs")
PENCERE = os.path.join(KOK, "veri", "ab_pn_pencereler.json")


def _f(r, k):
    v = r.get(k, "")
    try:
        return float(v) if v not in ("", None) else None
    except (TypeError, ValueError):
        return None


def truth():
    yl = sorted(glob.glob(os.path.join(IZ_DIR, "hedef_iz_*.csv")),
                key=os.path.getmtime)
    if not yl:
        return None, None
    R = []
    with open(yl[-1], newline="", encoding="utf-8", errors="replace") as f:
        for r in csv.DictReader(f):
            t = _f(r, "t_mutlak")
            hx, hy = _f(r, "hx_m"), _f(r, "hy_m")
            dx, dy = _f(r, "dx_m"), _f(r, "dy_m")
            vx, vy = _f(r, "d_vx"), _f(r, "d_vy")
            if None in (t, hx, hy, dx, dy):
                continue
            R.append((t, hx, hy, dx, dy, vx, vy,
                      (r.get("faz") or "").startswith("VIS")))
    R.sort()
    return R, os.path.basename(yl[-1])


def tespit_zamanlari(t0, t1):
    """[t0,t1] araliginda KUTU TASIYAN kare zamanlari + kopru bayragi."""
    Z = []
    for y in glob.glob(os.path.join(IBVS_DIR, "bbox_ibvs_*.csv")):
        try:
            rows = list(csv.DictReader(open(y, encoding="utf-8", errors="replace")))
        except OSError:
            continue
        for r in rows:
            t = _f(r, "t")
            if t is None or not (t0 <= t <= t1):
                continue
            if _f(r, "boyut") is None:
                continue                       # kutu yok -> tespit yok
            Z.append((t, int(_f(r, "kopru") or 0)))
    Z.sort()
    return Z


def coz(R, t0, t1, ad=""):
    S = [x for x in R if t0 <= x[0] <= t1 and x[7]]      # yalniz GORSEL faz
    if len(S) < 40:
        return None
    Z = tespit_zamanlari(t0, t1)
    Zt = [z[0] for z in Z]
    kopru_n = sum(1 for z in Z if z[1])

    tum, gorurken, korken = [], [], []
    yaw_don, los_don = [], []
    for i, (t, hx, hy, dx, dy, vx, vy, _) in enumerate(S):
        if vx is None or math.hypot(vx, vy) < 4:
            continue
        los = math.degrees(math.atan2(hy - dy, hx - dx))
        biz = math.degrees(math.atan2(vy, vx))
        h = abs((biz - los + 540) % 360 - 180)
        tum.append(h)
        # bu ana en yakin tespit 0.10 s icinde mi?
        taze = False
        if Zt:
            j = min(max(bisect.bisect_left(Zt, t), 0), len(Zt) - 1)
            for c in (j - 1, j, j + 1):
                if 0 <= c < len(Zt) and abs(Zt[c] - t) < 0.10:
                    taze = True
                    break
        (gorurken if taze else korken).append(h)
        # burun/LOS donus hizi (0.3 s pencere) — kisir dongu kaniti
        k = i
        while k > 0 and t - S[k][0] < 0.3:
            k -= 1
        if k < i and S[k][5] is not None and math.hypot(S[k][5], S[k][6]) > 4:
            dt = t - S[k][0]
            if dt > 0.05:
                b0 = math.degrees(math.atan2(S[k][6], S[k][5]))
                l0 = math.degrees(math.atan2(S[k][2] - S[k][4], S[k][1] - S[k][3]))
                yaw_don.append(abs((biz - b0 + 540) % 360 - 180) / dt)
                los_don.append(abs((los - l0 + 540) % 360 - 180) / dt)
    if len(tum) < 30:
        return None
    p = lambda v, q: sorted(v)[int(q * (len(v) - 1))] if v else 0.0
    return {
        "ad": ad, "n": len(tum),
        "hepsi_p50": st.median(tum), "hepsi_p90": p(tum, .9),
        "kotu90": 100.0 * sum(1 for x in tum if x > 90) / len(tum),
        "gorur_p50": st.median(gorurken) if len(gorurken) > 10 else None,
        "kor_p50": st.median(korken) if len(korken) > 10 else None,
        "taze_oran": 100.0 * len(gorurken) / len(tum),
        "kopru_kare": kopru_n,
        "yaw_don": st.median(yaw_don) if yaw_don else 0.0,
        "los_don": st.median(los_don) if los_don else 0.0,
    }


def yaz(d):
    print("  %-14s n=%5d | TUM %5.1f° (p90 %5.1f°, >90° %%%2.0f) | gorur %s | kor %s"
          % (d["ad"], d["n"], d["hepsi_p50"], d["hepsi_p90"], d["kotu90"],
             ("%5.1f°" % d["gorur_p50"]) if d["gorur_p50"] is not None else "  —  ",
             ("%5.1f°" % d["kor_p50"]) if d["kor_p50"] is not None else "  —  "))
    print("  %-14s taze kare %%%.0f | kopru karesi %d | burun donusu %.0f °/s vs LOS %.0f °/s"
          % ("", d["taze_oran"], d["kopru_kare"], d["yaw_don"], d["los_don"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pencere", action="store_true")
    a = ap.parse_args()
    R, ad = truth()
    if not R:
        print("  truth iz yok."); return
    print("  truth: %s (%d satir)" % (ad, len(R)))
    print("  ASIL OLCUT = faz genelinde |hiz yonu - hedefe olan yon|")
    print("  saha referansi: TUM 56.4° | >90° %24 | gorurken 8.3°")
    print("  " + "-" * 74)

    if a.pencere and os.path.exists(PENCERE):
        for p in json.load(open(PENCERE, encoding="utf-8")):
            d = coz(R, p["t0"], p["t1"], p["ad"])
            if d:
                yaz(d)
            else:
                print("  %-14s (yeterli gorsel faz verisi yok)" % p["ad"])
    else:
        d = coz(R, R[0][0], R[-1][0], "TUM UCUS")
        if d:
            yaz(d)


if __name__ == "__main__":
    main()

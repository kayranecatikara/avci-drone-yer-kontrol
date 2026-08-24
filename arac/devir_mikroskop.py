# -*- coding: utf-8 -*-
"""
================================================================================
  DEVIR MIKROSKOBU  --  GPS -> GORSEL gecisinin ILK SANIYELERI
================================================================================
NEDEN
--------------------------------------------------------------------------------
Kullanicinin tarifi: "faza gectiginde tutamiyor". Devir aninda ne oldugunu
saniyenin dortte biri cozunurlukte gormek gerekiyor. Bu arac her devri
yakalar, t=0'i devir ani kabul eder ve etrafindaki pencereyi cikarir.

⚠ OLCUM TUZAKLARI (arac/kol_hukum.py basligindaki listeyle ayni):
  - `menzil==0` / `d_hiz==0` satirlari GECERSIZ (bos telemetri)
  - `t` = time.monotonic ve SUNUCU YENIDEN BASLAYINCA SIFIRLANIR
    -> her (DOSYA, AYAR) ayri ele alinir, asla birlestirilmez

EKSEN AYRISTIRMASI (asil deger burada)
--------------------------------------------------------------------------------
3B menzil tek basina yaniltici. Bagil konumu HEDEFIN CERCEVESINDE ayiriyoruz:
    BOYUNA  : hedefin hiz yonundeki bilesen (- = arkasindayiz)
    YANAL   : hedefin hiz yonune dik yatay bilesen
    DIKEY   : irtifa farki (+ = BIZ USTTEYIZ)
Boylece "hangi eksen kapaniyor, hangisi kapanmiyor" ayri ayri gorulur.

KULLANIM
    python arac/devir_mikroskop.py                 # son 4 iz dosyasi
    python arac/devir_mikroskop.py --on C --dosya 2
================================================================================
"""
import os
import csv
import sys
import glob
import math
import argparse

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _f(r, k):
    v = (r.get(k) or "").strip()
    if v in ("", "None", "nan"):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def med(x):
    if not x:
        return float("nan")
    s = sorted(x)
    n = len(s)
    return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])


def gecerli(r):
    m = _f(r, "menzil")
    h = _f(r, "d_hiz")
    return m is not None and m >= 0.5 and h is not None and h > 0.5


def hedef_kursu(R, i, geri=5):
    """Hedefin hiz yonu (birim vektor), gecmis `geri` ornekten."""
    j = max(0, i - geri)
    ax, ay = _f(R[j], "hx"), _f(R[j], "hy")
    bx, by = _f(R[i], "hx"), _f(R[i], "hy")
    if None in (ax, ay, bx, by):
        return None
    dx, dy = bx - ax, by - ay
    n = math.hypot(dx, dy)
    if n < 0.3:                      # hedef neredeyse durmus -> yon guvenilmez
        return None
    return dx / n, dy / n


def eksenler(R, i):
    """(boyuna, yanal, dikey, menzil) -- hedefin cercevesinde."""
    u = hedef_kursu(R, i)
    if u is None:
        return None
    hx, hy, hz = _f(R[i], "hx"), _f(R[i], "hy"), _f(R[i], "hz")
    dx, dy, dz = _f(R[i], "dx"), _f(R[i], "dy"), _f(R[i], "dz")
    if None in (hx, hy, hz, dx, dy, dz):
        return None
    rx, ry, rz = dx - hx, dy - hy, dz - hz          # hedeften BIZE
    boyuna = rx * u[0] + ry * u[1]                  # - = arkasindayiz
    yanal = -rx * u[1] + ry * u[0]
    return boyuna, yanal, rz, math.sqrt(rx * rx + ry * ry + rz * rz)


def devirleri_bul(R):
    """faz GPS -> VISUAL gecis indeksleri."""
    out = []
    for i in range(1, len(R)):
        a = (R[i - 1].get("faz") or "").strip()
        b = (R[i].get("faz") or "").strip()
        if a == "GPS" and b == "VISUAL":
            out.append(i)
    return out


def pencere(R, i0, once=1.0, sonra=4.0):
    """t=0 devir ani; (dt, eksenler) listesi."""
    t0 = _f(R[i0], "t")
    if t0 is None:
        return []
    out = []
    for i in range(len(R)):
        t = _f(R[i], "t")
        if t is None:
            continue
        dt = t - t0
        if not (-once <= dt <= sonra):
            continue
        if not gecerli(R[i]):
            continue
        e = eksenler(R, i)
        if e is None:
            continue
        out.append((dt, e, R[i]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--on", default="", help="yalniz bu onekle baslayan ayarlar")
    ap.add_argument("--dosya", type=int, default=4)
    a = ap.parse_args()

    G = {}
    for y in sorted(glob.glob(os.path.join(KOK, "veri", "gece",
                                           "kampanya_iz_*.csv")),
                    key=os.path.getmtime)[-a.dosya:]:
        try:
            with open(y, encoding="utf-8", errors="replace") as fh:
                for r in csv.DictReader(fh):
                    ad = r.get("ayar", "?")
                    if a.on and not ad.startswith(a.on):
                        continue
                    G.setdefault((os.path.basename(y), ad), []).append(r)
        except OSError:
            continue
    if not G:
        print("veri yok")
        return

    # tum devirleri topla
    hepsi = []
    for anahtar in sorted(G):
        R = G[anahtar]
        R.sort(key=lambda r: (_f(r, "t") or 0.0))
        for i0 in devirleri_bul(R):
            p = pencere(R, i0)
            if len(p) >= 8:
                hepsi.append(p)
    print("=" * 86)
    print("  DEVIR MIKROSKOBU  --  %d devir yakalandi" % len(hepsi))
    print("  eksenler HEDEFIN cercevesinde: BOYUNA(- = arkasindayiz), YANAL, DIKEY(+ = ustteyiz)")
    print("=" * 86)
    if not hepsi:
        return

    dilimler = [(-1.0, -0.5), (-0.5, 0.0), (0.0, 0.25), (0.25, 0.5),
                (0.5, 0.75), (0.75, 1.0), (1.0, 1.5), (1.5, 2.0),
                (2.0, 3.0), (3.0, 4.0)]
    print("%-12s %5s %8s %8s %8s %8s %9s %8s"
          % ("pencere", "n", "menzil", "BOYUNA", "YANAL", "DIKEY", "kapanma", "hiz"))
    print("-" * 76)
    onceki_m = None
    for lo, hi in dilimler:
        M, B, Y, D, H = [], [], [], [], []
        for p in hepsi:
            v = [x for x in p if lo <= x[0] < hi]
            if not v:
                continue
            # dilim ortasi: dilimdeki medyan
            M.append(med([x[1][3] for x in v]))
            B.append(med([x[1][0] for x in v]))
            Y.append(med([x[1][1] for x in v]))
            D.append(med([x[1][2] for x in v]))
            h = [_f(x[2], "d_hiz") for x in v]
            H.append(med([z for z in h if z is not None]))
        if len(M) < 3:
            continue
        m = med(M)
        kap = ""
        if onceki_m is not None:
            kap = "%+8.2f" % ((onceki_m - m) / max(hi - lo, 1e-6))
        onceki_m = m
        print("%-12s %5d %8.2f %8.2f %8.2f %+8.2f %9s %8.1f"
              % ("[%+.2f,%+.2f)" % (lo, hi), len(M), m, med(B), med(Y),
                 med(D), kap or "  —", med(H)))

    # ── devir ANI ozeti ──────────────────────────────────────────────
    t0 = []
    for p in hepsi:
        v = [x for x in p if -0.15 <= x[0] <= 0.15]
        if v:
            t0.append(min(v, key=lambda x: abs(x[0])))
    if t0:
        print("\n★ DEVIR ANI (t=0)  n=%d" % len(t0))
        for ad, f in (("menzil (m)", lambda x: x[1][3]),
                      ("BOYUNA (m)", lambda x: x[1][0]),
                      ("YANAL (m)", lambda x: x[1][1]),
                      ("DIKEY (m)", lambda x: x[1][2]),
                      ("hiz (m/s)", lambda x: _f(x[2], "d_hiz")),
                      ("tespit orani", lambda x: 1.0 if str(x[2].get("tespit")) == "True" else 0.0)):
            vals = [f(x) for x in t0]
            vals = [v for v in vals if v is not None]
            if vals:
                s = sorted(vals)
                print("   %-14s medyan %+8.2f   p10 %+8.2f   p90 %+8.2f"
                      % (ad, med(vals), s[int(0.1 * len(s))], s[int(0.9 * len(s))]))

    # ── en yakin ana kadar ne oluyor ─────────────────────────────────
    enyakin_t, enyakin_m, son_m = [], [], []
    for p in hepsi:
        ileri = [x for x in p if x[0] >= 0]
        if len(ileri) < 5:
            continue
        j = min(ileri, key=lambda x: x[1][3])
        enyakin_t.append(j[0])
        enyakin_m.append(j[1][3])
        son_m.append(ileri[-1][1][3])
    if enyakin_t:
        print("\n★ DEVIRDEN SONRA")
        print("   en yakin ana kadar gecen sure : medyan %.2f s" % med(enyakin_t))
        print("   o andaki menzil               : medyan %.2f m" % med(enyakin_m))
        print("   pencere sonundaki menzil      : medyan %.2f m" % med(son_m))
        geri = sum(1 for a_, b_ in zip(enyakin_m, son_m) if b_ > a_ + 1.0)
        print("   ⚠ en yakindan sonra UZAKLASAN : %d / %d  (%%%.0f)"
              % (geri, len(son_m), 100.0 * geri / len(son_m)))


if __name__ == "__main__":
    main()

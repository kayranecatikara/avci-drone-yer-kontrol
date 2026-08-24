# -*- coding: utf-8 -*-
"""
================================================================================
  KOL HUKMU  --  kampanya kollarini GECERLI veriyle kiyaslar
================================================================================
⚠⚠ NEDEN AYRI BIR BETIK: 2026-08-17'de iki kez ayni tuzaga dusuldu.

`kampanya_iz_*.csv` ve `kareler.csv`'de telemetri BOS geldiginde (arac olu,
yeniden doguyor, ya da baglanti kopuk) `menzil`, `d_hiz`, `d_roll`, `d_pitch`
alanlari **0.0** yazilir. Bu satirlar:
   - menzil<12 filtresine takilip SAHTE "yakin gecis" epizodu uretir,
   - 0 -> buyuk sicramasi SAHTE "temas" sayilir.
Olculdu: bir kolda 14 dk'da 474 gecis / 194 temas cikti (fiziken imkansiz;
gercegi ~48 gecis / 1 temas).

GECERLILIK KURALI (bu betikte tek yerde):
   menzil >= 0.5  VE  d_hiz > 0.5
Filtrelemezsen HER menzil/CPA analizi COP uretir.

Ayrica: ayni ayar adi birden fazla kez kosulmus olabilir (yeniden kosu).
`t`'deki buyuk bosluklara gore AYRI BLOKLARA boler.

KULLANIM
    python arac/kol_hukum.py                 # son 4 iz dosyasi
    python arac/kol_hukum.py --on M          # yalniz M* kollari
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
    """⚠ Telemetrisi bos satiri ELE (bkz. modul basligi)."""
    m = _f(r, "menzil")
    h = _f(r, "d_hiz")
    return m is not None and m >= 0.5 and h is not None and h > 0.5


def bloklara_ayir(R, bosluk_s=120.0):
    R = [r for r in R if _f(r, "t") is not None]
    R.sort(key=lambda r: _f(r, "t"))
    if not R:
        return []
    out, cur = [], [R[0]]
    for i in range(1, len(R)):
        if _f(R[i], "t") - _f(R[i - 1], "t") > bosluk_s:
            out.append(cur)
            cur = []
        cur.append(R[i])
    if cur:
        out.append(cur)
    return out


def olc(R):
    """CPA geometrisi + temas -- YALNIZ gecerli satirlarla."""
    V = [r for r in R if gecerli(r)]
    atilan = len(R) - len(V)
    mz = [_f(r, "menzil") for r in V]
    ep, cur = [], []
    for i, m in enumerate(mz):
        if m < 12:
            cur.append(i)
        elif cur:
            ep.append(cur)
            cur = []
    if cur:
        ep.append(cur)
    cpa, dz, dh = [], [], []
    for e in ep:
        j = min(e, key=lambda i: mz[i])
        m = mz[j]
        if m > 8:
            continue
        v = _f(V[j], "irt_fark")
        if v is None:
            continue
        cpa.append(m)
        dz.append(v)
        dh.append(math.sqrt(max(m * m - v * v, 0.0)))
    # temas: gecerli satirlar arasinda menzil<8 -> >25 sicramasi
    tem = 0
    for i in range(1, len(V)):
        a, b = mz[i - 1], mz[i]
        if a < 8 and b - a > 25:
            tem += 1
    t = [x for x in (_f(r, "t") for r in R) if x is not None]
    dk = (max(t) - min(t)) / 60.0 if len(t) > 1 else 0.0
    return dk, cpa, dz, dh, tem, atilan, len(R)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--on", default="", help="yalniz bu harfle baslayan kollar")
    ap.add_argument("--dosya", type=int, default=4, help="son kac iz dosyasi")
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
                    # ⚠⚠ ANAHTAR (DOSYA, AYAR) OLMALI. `t` = time.monotonic
                    #   ve SUNUCU YENIDEN BASLAYINCA SIFIRLANIR. Ayni adli iki
                    #   kosu tek listede birlesip t'ye gore siralanirsa iki
                    #   BAGIMSIZ ucus ic ice geciyor -> menzil zikzak yapiyor,
                    #   sahte "yakin gecis" ve sahte "temas" uretiyor.
                    #   OLCULDU: M0_taban 14 dk'da 474 gecis / 194 temas
                    #   gosterdi (gercegi ~48 / 1).
                    G.setdefault((os.path.basename(y), ad), []).append(r)
        except OSError:
            continue
    if not G:
        print("kol bulunamadi")
        return
    print("=" * 88)
    print("  KOL HUKMU   (⚠ menzil>=0.5 VE d_hiz>0.5 -- bos telemetri ELENDI)")
    print("=" * 88)
    print("%-24s %-6s %5s %5s %7s %8s %7s %6s %6s %6s" % (
        "AYAR", "blok", "dk", "CPA", "|dz|", "dz", "CPAmed", "<2m%", "<3m%", "temas"))
    print("-" * 88)
    top_at = top_ham = 0
    for anahtar in sorted(G):
        dosya, ad = anahtar
        bl = bloklara_ayir(G[anahtar])
        for i, B in enumerate(bl):
            dk, cpa, dz, dh, tem, at, ham = olc(B)
            top_at += at
            top_ham += ham
            if len(dz) < 5 or dk < 4:
                continue
            etiket = ("#%d" % (i + 1)) if len(bl) > 1 else "tek"
            a2 = 100.0 * sum(1 for c in cpa if c < 2) / len(cpa)
            a3 = 100.0 * sum(1 for c in cpa if c < 3) / len(cpa)
            print("%-24s %-6s %5.1f %5d %7.2f %+8.2f %7.2f %5.0f%% %5.0f%% %6d" % (
                ad[:24], etiket, dk, len(dz), med([abs(x) for x in dz]),
                med(dz), med(cpa), a2, a3, tem))
    if top_ham:
        print("\n  elenen bos telemetri satiri: %d / %d (%%%.1f)"
              % (top_at, top_ham, 100.0 * top_at / top_ham))
    print("  ⚠ vurus/temas ZAYIF sinyal (12-14 dk'da 0-5). CPA dagilimina bak.")


if __name__ == "__main__":
    main()

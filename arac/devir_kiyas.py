# -*- coding: utf-8 -*-
"""
================================================================================
  DEVIR KIYASI  --  devir kapisi deneylerini kol bazinda okur
================================================================================
NEDEN AYRI
--------------------------------------------------------------------------------
Devir kapisi iki sey yapar ve ikisi BIRLIKTE olculmeli:
  1. DEVIR SAYISINI dusurur (bekleme maliyeti)
  2. Kalan devirlerin KALITESINI artirir (kazanc)
Yalniz CPA'ya bakmak birinciyi gizler; yalniz devir sayisina bakmak ikinciyi.
Bu betik ikisini yan yana basar ve "devir basina kazanc" ile "saat basina
firsat" arasindaki odunlesmeyi gorunur kilar.

OLCUT: KAPATMA ORANI = (devir menzili - sonraki 4 s'deki en yakin) / devir menzili
  ⚠ Ham "en yakin menzil" KULLANILMAZ: devir menziliyle korelasyonu +0.99,
    yani neredeyse mekanik. Normalize olcut gruplar arasi kiyasi mumkun kilar.

⚠ OLCUM TUZAKLARI (arac/kol_hukum.py basligi): menzil==0/d_hiz==0 satirlari
  gecersiz; `t` monotonic ve sunucu yeniden basladiginda SIFIRLANIR ->
  anahtar (DOSYA, AYAR).

KULLANIM
    python arac/devir_kiyas.py --on H      # devir kapisi deneyi
    python arac/devir_kiyas.py --on I      # ic-daire kesme deneyi
================================================================================
"""
import os
import csv
import sys
import glob
import math
import argparse

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "arac"))
import devir_mikroskop as DM                      # noqa: E402

_f = DM._f
med = DM.med


def _w(x):
    return (x + 540) % 360 - 180


def omega(R, i, geri=8):
    j = max(0, i - geri)
    a = DM.hedef_kursu(R, j)
    b = DM.hedef_kursu(R, i)
    ta, tb = _f(R[j], "t"), _f(R[i], "t")
    if a is None or b is None or ta is None or tb is None or tb - ta < 0.1:
        return None
    return _w(math.degrees(math.atan2(b[1], b[0]))
              - math.degrees(math.atan2(a[1], a[0]))) / (tb - ta)


def kol_olc(R):
    """Bir kolun tum devirlerini olc."""
    R.sort(key=lambda r: (_f(r, "t") or 0.0))
    t = [x for x in (_f(r, "t") for r in R) if x is not None]
    dk = (max(t) - min(t)) / 60.0 if len(t) > 1 else 0.0
    out = []
    for i0 in DM.devirleri_bul(R):
        p = DM.pencere(R, i0)
        if len(p) < 8:
            continue
        t0 = [x for x in p if abs(x[0]) <= 0.2]
        ileri = [x for x in p if 0 <= x[0] <= 4.0]
        if not t0 or len(ileri) < 5:
            continue
        z = min(t0, key=lambda x: abs(x[0]))
        men = z[1][3]
        if men < 3:
            continue
        ey = min(x[1][3] for x in ileri)
        om = omega(R, i0)
        out.append(dict(men=men, ey=ey, kap=(men - ey) / men,
                        om=abs(om) if om is not None else None))
    return dk, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--on", default="", help="ayar oneki (H, I, ...)")
    ap.add_argument("--dosya", type=int, default=3)
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
        print("kol bulunamadi (henuz veri yok olabilir)")
        return
    print("=" * 92)
    print("  DEVIR KIYASI   olcut: KAPATMA = (devir menzili - en yakin)/devir menzili")
    print("=" * 92)
    print("%-22s %5s %6s %8s %9s %8s %8s %9s"
          % ("AYAR", "dk", "devir", "devir/sa", "kapatma", "≥%70", "≥%85", "donus med"))
    print("-" * 92)
    S = {}
    for anahtar in sorted(G):
        dosya, ad = anahtar
        dk, D = kol_olc(G[anahtar])
        if dk < 4 or len(D) < 4:
            continue
        kp = [d["kap"] for d in D]
        om = [d["om"] for d in D if d["om"] is not None]
        S[ad] = (dk, len(D), med(kp), om)
        print("%-22s %5.1f %6d %8.1f %8.0f%% %7.0f%% %7.0f%% %9s"
              % (ad[:22], dk, len(D), len(D) / (dk / 60.0),
                 100 * med(kp),
                 100 * sum(1 for x in kp if x >= 0.70) / len(kp),
                 100 * sum(1 for x in kp if x >= 0.85) / len(kp),
                 ("%.1f" % med(om)) if om else "—"))
    print()
    print("  ⚠ KAPI ODUNLESMESI: 'devir/sa' duserken 'kapatma' artmali.")
    print("     Ikisi de duserse kapi ZARARLI; ikisi de artarsa serbest kazanc.")
    print("  ⚠ Bir kolun devir sayisi digerlerinin YARISINDAN azsa kapi COK SIKI.")
    # taban kollarini birlestir
    tb = [k for k in S if "taban" in k]
    if tb:
        n = sum(S[k][1] for k in tb)
        d = sum(S[k][0] for k in tb)
        print("\n  TABAN birlesik: %d devir / %.0f dk = %.1f devir/sa"
              % (n, d, n / (d / 60.0)))


if __name__ == "__main__":
    main()

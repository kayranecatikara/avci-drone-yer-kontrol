# -*- coding: utf-8 -*-
"""
INOVASYONLU J — GATING ESIK ANALIZI + SWEEP (ampirik esik secimi).
==================================================================
Ayni v2 ucus_log'unu FARKLI gate degerleriyle replay eder; her gate icin
kabul orani + J-ANLIK/LEAD truth hatasini olcer. Once maha^2 dagilimini
(temiz<5m vs sicrama>35m) dokup teorik ki-kare (2DOF) esigiyle kiyaslar.
Amac: dogru esigi VERIDEN sec (tahmin degil) ve gating'in bu profilde
gercekten anlik hatayi dusurup dusurmedigini gor. Filtre MANTIGI degismez
(sadece gate parametresi taranir; guncelle icindeki gozlemsel _diag okunur).

Kullanim:  python arac/j_gate_sweep.py [--dosya veri/ucus_log_...csv]
"""
import csv
import glob
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from fusion.inovasyonlu_j_v2 import GNSSDuzeltici


def fl(x):
    try:
        v = float(x)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def _v2_log(dosya):
    if dosya:
        return dosya
    for f in sorted(glob.glob(os.path.join(ROOT, "veri", "ucus_log_*.csv")), reverse=True):
        with open(f, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if r.get("kaynak") == "v2":
                    return f
    return None


def _paketler(dosya):
    """v2 satirlarindan yeni-paket (ham degisen) dizisini + truth'u cikar (ana_kontrol gibi)."""
    out = []
    prev = None
    for r in csv.DictReader(open(dosya, encoding="utf-8")):
        if r.get("kaynak") != "v2":
            continue
        hx, hy, hz = fl(r.get("son_ham_x")), fl(r.get("son_ham_y")), fl(r.get("son_ham_z"))
        tx, ty = fl(r.get("true_tx")), fl(r.get("true_ty"))
        tw = fl(r.get("t_wall"))
        if None in (hx, hy, hz):
            continue
        ham = (hx, hy, hz)
        if ham == prev:
            continue
        prev = ham
        out.append((hx, hy, hz, tx, ty, tw))
    return out


def replay(paketler, gate):
    """Verilen gate ile TAZE filtre replay; per-adim kayit dondur (state trajesi gate'e gore degisir)."""
    filt = GNSSDuzeltici(gate=gate)
    rec = []
    for hx, hy, hz, tx, ty, tw in paketler:
        sonuc = filt.guncelle(hx, hy, hz, tw)
        if sonuc is None:
            continue
        d = filt._diag or {}
        dg = filt.durum_guduum() or {"pos": (0.0, 0.0, 0.0)}
        ax, ay = dg["pos"][0], dg["pos"][1]
        lx, ly = sonuc[0], sonuc[1]
        raw = math.hypot(hx - tx, hy - ty) / 100.0 if tx is not None else None
        an = math.hypot(ax - tx, ay - ty) / 100.0 if tx is not None else None
        le = math.hypot(lx - tx, ly - ty) / 100.0 if tx is not None else None
        rec.append({"maha2": d.get("maha2", 0.0), "yk": d.get("yk_cm", 0.0),
                    "gecti": d.get("gecti", False), "raw": raw, "an": an, "le": le})
    return rec


def pct(x, p):
    if not x:
        return 0.0
    s = sorted(x)
    i = min(len(s) - 1, max(0, int(p / 100.0 * len(s))))
    return s[i]


def med(x):
    return pct(x, 50)


def main():
    dosya = None
    a = sys.argv[1:]
    for i, x in enumerate(a):
        if x == "--dosya" and i + 1 < len(a):
            dosya = a[i + 1]
    dosya = _v2_log(dosya)
    if not dosya:
        print("kaynak=v2 ucus_log bulunamadi.")
        return 1

    pk = _paketler(dosya)
    base = replay(pk, 200.0)                              # baseline: mevcut gate=200 (hepsi kabul)

    temiz = [r["maha2"] for r in base if r["raw"] is not None and r["raw"] < 5.0]
    orta = [r["maha2"] for r in base if r["raw"] is not None and 5.0 <= r["raw"] <= 35.0]
    sic = [r["maha2"] for r in base if r["raw"] is not None and r["raw"] > 35.0]
    allm = [r["maha2"] for r in base]

    print("=" * 82)
    print("MAHA^2 DAGILIMI (baseline gate=200, hepsi kabul)  |  %s" % os.path.basename(dosya))
    print("  N=%d adim.  Teorik ki-kare 2DOF esik: %%95=5.99  %%99=9.21  %%99.9=13.8" % len(base))
    print("  TUMU      : med=%.1f  p90=%.1f  p99=%.1f  max=%.1f" % (med(allm), pct(allm, 90), pct(allm, 99), max(allm) if allm else 0))
    print("  TEMIZ <5m : n=%d  med=%.1f  p90=%.1f  max=%.1f" % (len(temiz), med(temiz), pct(temiz, 90), max(temiz) if temiz else 0))
    print("  ORTA 5-35m: n=%d  med=%.1f  p90=%.1f  max=%.1f" % (len(orta), med(orta), pct(orta, 90), max(orta) if orta else 0))
    print("  SICRA >35m: n=%d  med=%.1f  min=%.1f  max=%.1f" % (len(sic), med(sic), min(sic) if sic else 0, max(sic) if sic else 0))
    print("  NOT: gating INNOVATION'i olcer (olcum vs kestirim), truth'u DEGIL. Duzgun-gecikmeli")
    print("       bias (kucuk maha^2) reddEDILEMEZ; yalniz SUREKSIZLIK/jump (buyuk maha^2) reddedilir.")
    print("-" * 82)

    print("GATE SWEEP (her gate TAZE replay; state trajesi degisir):")
    print("  %-7s %-9s %-14s %-11s %-11s" % ("gate", "gate^2", "kabul", "J-ANLIK m", "J-LEAD m"))
    for g in [3.0, 3.6, 6.0, 9.2, 13.0, 20.0, 35.0, 50.0, 100.0, 200.0]:
        rec = replay(pk, g)
        kab = sum(1 for r in rec if r["gecti"])
        tot = len(rec)
        ans = [r["an"] for r in rec if r["an"] is not None]
        les = [r["le"] for r in rec if r["le"] is not None]
        print("  %-7.1f %-9.0f %-14s %-11.1f %-11.1f" % (
            g, g * g, "%d/%d=%.0f%%" % (kab, tot, 100.0 * kab / tot if tot else 0), med(ans), med(les)))
    print("  (J-ANLIK dususu = gating bu profilde ISE YARIYOR; sabit kalmasi = hata jump degil bias)")
    print("=" * 82)
    return 0


if __name__ == "__main__":
    sys.exit(main())

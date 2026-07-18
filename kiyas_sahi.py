"""kiyas_sahi.py — SAHI acik vs kapali UCUS kiyasi: MENZIL-BINLI recall + taze-tespit orani.

Amac: bench_sahi.py hiz tarafini kanitladi (SAHI-OFF ~33 FPS, ON ~2-3 FPS). Bu script
RECALL tarafini olcer: gorsel faz boyunca, HER MENZIL bandinda dedektor hedefi ne kadar
gorabiliyor (tespit-var %) ve ne kadar TAZE kutu uretiyor (Hz). Hipotez: SAHI-kapali surekli
yuksek taze-oran, bir uzak hedefi SAHI-acik'in tek-kare recall'indan daha iyi TAKIP eder.

Kullanim:
    python kiyas_sahi.py --on veri/ucus_log_SAHI_ACIK.csv --off veri/ucus_log_SAHI_KAPALI.csv
    python kiyas_sahi.py --on ... --off ... --fov 60      # yatay FOV kapisi (deg); 0=kapali

Metrikler (yalniz phase=VISUAL satirlari):
  - tespit%   : vis_gordu==1 (gercek kutu VAR, kopru haric) orani -> "o menzilde kutu var mi"
  - taze_Hz   : ayri kutu (vis_cx/vis_conf degisimi) / o bantta gecen sure -> uretim/sureklilik
  - conf      : kutu varken ortalama guven
FOV kapisi (--fov): |nose_off_true| < fov -> hedef yatayda kadraj icindeyken say (adil recall;
  arkada/yanda olan tik'ler dedektore firsat degil). nose_off_true yoksa kapi atlanir.

NOT (durustluk): iki ucus farkli yorunge -> her bantta gecen sure/aspect farkli olabilir.
Kesin degil, YON gosterir. gercek_mesafe truth-kaynagi ister (get_debug_truth available).
"""
import argparse
import csv
import math
import os
import statistics as st
import sys

GAP_S = 0.20                 # ardisik VISUAL tik arasi < bu -> sureye/gecise say (segment ici)
BINLER = [0, 10, 20, 30, 40, 60, 100, float("inf")]   # menzil bantlari (m)


def _bin_ad(lo, hi):
    return f"{lo:.0f}-{'inf' if hi == float('inf') else f'{hi:.0f}'} m"


def _bin_no(r_m):
    for i in range(len(BINLER) - 1):
        if BINLER[i] <= r_m < BINLER[i + 1]:
            return i
    return None


def _oku(path, fov_deg):
    """VISUAL satirlari -> [{r_m, gordu, conf, cx, tw}]; FOV kapisi opsiyonel."""
    rows = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            if row.get("phase") != "VISUAL":
                continue
            gm = (row.get("gercek_mesafe") or "").strip()
            if not gm:
                continue                       # truth menzil yok -> binlenemez
            try:
                r_m = float(gm) / 100.0        # cm -> m
            except ValueError:
                continue
            if fov_deg > 0:
                no = (row.get("nose_off_true") or "").strip()
                if no:
                    try:
                        if abs(float(no)) > fov_deg:
                            continue           # hedef yatay FOV disi -> dedektore firsat degil
                    except ValueError:
                        pass
            try:
                gordu = 1 if float(row.get("vis_gordu") or 0) >= 0.5 else 0
            except ValueError:
                gordu = 0
            conf = (row.get("vis_conf") or "").strip()
            cx = (row.get("vis_cx") or "").strip()
            tw = (row.get("t_wall") or "").strip()
            rows.append({
                "r_m": r_m, "gordu": gordu,
                "conf": float(conf) if conf else None,
                "cx": cx, "tw": float(tw) if tw else None,
            })
    return rows


def _metrik(rows):
    """Bant basina: n, tespit%, taze_Hz, conf_ort. Dondurur: {bin_no: {...}}."""
    n_bin = len(BINLER) - 1
    tot = [0] * n_bin
    det = [0] * n_bin
    conf_top = [0.0] * n_bin
    conf_n = [0] * n_bin
    taze = [0] * n_bin
    sure = [0.0] * n_bin

    son_kutu = None                            # en son gorulen (cx,conf) — taze gecis tespiti
    for i, r in enumerate(rows):
        b = _bin_no(r["r_m"])
        if b is None:
            continue
        tot[b] += 1
        if r["gordu"]:
            det[b] += 1
            if r["conf"] is not None:
                conf_top[b] += r["conf"]; conf_n[b] += 1
            kutu = (r["cx"], r["conf"])
            if kutu != son_kutu:               # yeni (farkli) kutu -> taze inference
                taze[b] += 1
                son_kutu = kutu
        # sure: ardisik VISUAL tik contiguous ise onceki satirin bant'ina ekle
        if i > 0 and rows[i - 1]["tw"] is not None and r["tw"] is not None:
            dt = r["tw"] - rows[i - 1]["tw"]
            if 0 < dt < GAP_S:
                pb = _bin_no(rows[i - 1]["r_m"])
                if pb is not None:
                    sure[pb] += dt

    out = {}
    for b in range(n_bin):
        if tot[b] == 0:
            continue
        out[b] = {
            "n": tot[b],
            "recall": 100.0 * det[b] / tot[b],
            "taze_hz": (taze[b] / sure[b]) if sure[b] > 1e-6 else 0.0,
            "conf": (conf_top[b] / conf_n[b]) if conf_n[b] else float("nan"),
            "sure": sure[b],
        }
    return out


def _genel(rows):
    n = len(rows)
    det = sum(r["gordu"] for r in rows)
    return n, (100.0 * det / n if n else 0.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--on", required=True, help="SAHI ACIK ucus logu (baz)")
    ap.add_argument("--off", required=True, help="SAHI KAPALI ucus logu (yeni)")
    ap.add_argument("--fov", type=float, default=60.0,
                    help="yatay FOV kapisi (deg, |nose_off_true|<fov); 0=kapali")
    args = ap.parse_args()

    for p in (args.on, args.off):
        if not os.path.exists(p):
            print("HATA: log yok:", p); sys.exit(1)

    on = _oku(args.on, args.fov)
    off = _oku(args.off, args.fov)
    on_m = _metrik(on)
    off_m = _metrik(off)
    on_n, on_r = _genel(on)
    off_n, off_r = _genel(off)

    print("\n" + "=" * 88)
    print("SAHI KIYAS  (FOV kapisi=%s deg; yalniz VISUAL + truth-menzil satirlari)"
          % (args.fov if args.fov > 0 else "KAPALI"))
    print("  ON  (SAHI acik) : %s   VISUAL n=%d  genel tespit%%=%.1f" % (os.path.basename(args.on), on_n, on_r))
    print("  OFF (SAHI kapali): %s   VISUAL n=%d  genel tespit%%=%.1f" % (os.path.basename(args.off), off_n, off_r))
    print("-" * 88)
    print(f"{'menzil':>10} | {'ON n':>5} {'tespit%':>7} {'taze_Hz':>7} {'conf':>5} "
          f"| {'OFF n':>5} {'tespit%':>7} {'taze_Hz':>7} {'conf':>5}")
    print("-" * 88)
    for b in range(len(BINLER) - 1):
        if b not in on_m and b not in off_m:
            continue
        ad = _bin_ad(BINLER[b], BINLER[b + 1])
        o = on_m.get(b); f = off_m.get(b)
        def _fmt(m):
            if not m:
                return f"{'-':>5} {'-':>7} {'-':>7} {'-':>5}"
            return (f"{m['n']:>5d} {m['recall']:>7.1f} {m['taze_hz']:>7.2f} "
                    f"{(m['conf'] if not math.isnan(m['conf']) else 0):>5.2f}")
        print(f"{ad:>10} | {_fmt(o)} | {_fmt(f)}")
    print("=" * 88)
    print("Okuma: taze_Hz OFF'ta ON'dan yuksekse -> sureklilik kazanci (beklenen, ozellikle uzak).")
    print("       tespit%% OFF'ta uzak bantta ON'dan DUSUKse -> SAHI'nin uzak-recall bedeli (tradeoff).")
    print("       Karar: OFF'un yuksek taze_Hz'i, ON'un uzak tespit%% avantajini kapatiyor mu?")


if __name__ == "__main__":
    main()

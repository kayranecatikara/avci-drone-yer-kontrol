# -*- coding: utf-8 -*-
"""
================================================================================
 TALON ROTA ANALIZI — hedefin (Talon) GERCEK yorungesi (truth) uzerinden
================================================================================
Amac: Talon'un ucus rotasini (guzergah) uctan-ucta cikarmak, KARAKTERIZE etmek
(oval/daire, merkez, boyut, periyot, hiz, irtifa deseni) ve BIRDEN FAZLA ucusu
UST USTE bindirip "rota her seferinde ayni mi?" sorusunu yanitlamak. Girdi:
veri/ucus_log_*.csv icindeki true_tx/ty/tz (Talon truth konumu, GNSS gurultusuz).

Kullanim:
    python araclar/talon_rota_analiz.py                 # en yeni 3 ucus logu
    python araclar/talon_rota_analiz.py A.csv B.csv ...  # belirli loglar
    python araclar/talon_rota_analiz.py --son 5          # en yeni 5 log

Cikti: her log icin metrikler (konsol) + UST USTE rota grafigi
(veri/talon_rota_kiyas_<zaman>.png; matplotlib varsa).

NOT (kural): bu SADECE gozlem/analiz. Rotayi guduume GOMMEK overfit/diskalifiye;
bu arac Talon'un ne yaptigini ANLAMAK icin (genel ongorulu-intercept tasarimina veri).
"""
import csv, glob, math, os, sys

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERI = os.path.join(PROJ, "veri")


def f(x):
    try:
        return float(x)
    except (ValueError, TypeError):
        return None


def rota_oku(log_yolu):
    """Talon truth yorungesini (t, x, y, z) METRE olarak dondur (bos ise [])."""
    try:
        rows = list(csv.DictReader(open(log_yolu, encoding="utf-8", errors="replace")))
    except OSError:
        return []
    pts = []
    for r in rows:
        tx, ty, tz, tw = f(r.get("true_tx")), f(r.get("true_ty")), f(r.get("true_tz")), f(r.get("t_wall"))
        if None not in (tx, ty, tz, tw):
            pts.append((tw, tx / 100.0, ty / 100.0, tz / 100.0))   # cm -> m
    return pts


def karakterize(pts):
    """Talon yorungesini karakterize et -> metrik dict."""
    if len(pts) < 10:
        return None
    t0 = pts[0][0]
    ts = [p[0] - t0 for p in pts]
    xs = [p[1] for p in pts]; ys = [p[2] for p in pts]; zs = [p[3] for p in pts]
    cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)              # merkez (centroid)
    # XY yayilim (bbox + merkeze uzaklik = ~yaricap)
    rr = [math.hypot(x - cx, y - cy) for x, y in zip(xs, ys)]
    r_ort = sum(rr) / len(rr)
    r_std = (sum((r - r_ort) ** 2 for r in rr) / len(rr)) ** 0.5
    # hiz
    sps = []
    for i in range(1, len(pts)):
        dt = pts[i][0] - pts[i - 1][0]
        if dt > 1e-3:
            sps.append(math.dist(pts[i][1:], pts[i - 1][1:]) / dt)
    # tur/periyot (merkez etrafinda kumulatif aci)
    angs = [math.atan2(y - cy, x - cx) for x, y in zip(xs, ys)]
    tot = 0.0
    for i in range(1, len(angs)):
        da = angs[i] - angs[i - 1]
        while da > math.pi:  da -= 2 * math.pi
        while da < -math.pi: da += 2 * math.pi
        tot += da
    turns = abs(tot) / (2 * math.pi)
    dur = ts[-1]
    periyot = (dur / turns) if turns > 0.05 else None
    return {
        "sure": dur, "n": len(pts), "cx": cx, "cy": cy,
        "r_ort": r_ort, "r_std": r_std,
        "x_min": min(xs), "x_max": max(xs), "y_min": min(ys), "y_max": max(ys),
        "z_min": min(zs), "z_max": max(zs), "z_ort": sum(zs) / len(zs),
        "hiz_ort": (sum(sps) / len(sps)) if sps else 0.0, "hiz_max": max(sps) if sps else 0.0,
        "turlar": turns, "periyot": periyot,
        "xs": xs, "ys": ys, "zs": zs, "ts": ts,
    }


def yazdir(ad, m):
    print("=" * 70)
    print("ROTA: %s" % ad)
    print("  sure %.0f sn | %d nokta | %.2f tur -> periyot %s"
          % (m["sure"], m["n"], m["turlar"], ("%.0f sn/tur" % m["periyot"]) if m["periyot"] else "-"))
    print("  merkez (%.0f, %.0f) m | ~yaricap %.0f m (std %.0f -> %s)"
          % (m["cx"], m["cy"], m["r_ort"], m["r_std"],
             "DAIRE" if m["r_std"] < 0.15 * m["r_ort"] else "OVAL/duzensiz"))
    print("  XY kutu: %.0f x %.0f m | irtifa %.0f..%.0f m (salinim %.0f m, ort %.0f)"
          % (m["x_max"] - m["x_min"], m["y_max"] - m["y_min"],
             m["z_min"], m["z_max"], m["z_max"] - m["z_min"], m["z_ort"]))
    print("  hiz: ort %.1f m/s, max %.1f m/s" % (m["hiz_ort"], m["hiz_max"]))


def kiyas(metrikler):
    """Birden fazla rota -> tutarlilik ozeti (merkez/yaricap/periyot ayni mi?)."""
    if len(metrikler) < 2:
        return
    print("=" * 70)
    print("TUTARLILIK (rota her ucusta ayni mi?)")
    cxs = [m["cx"] for _, m in metrikler]; cys = [m["cy"] for _, m in metrikler]
    rs = [m["r_ort"] for _, m in metrikler]
    ps = [m["periyot"] for _, m in metrikler if m["periyot"]]
    def yay(v): return max(v) - min(v)
    print("  merkez sacilimi: X %.0f m, Y %.0f m" % (yay(cxs), yay(cys)))
    print("  yaricap sacilimi: %.0f m (%.0f..%.0f)" % (yay(rs), min(rs), max(rs)))
    if ps:
        print("  periyot sacilimi: %.0f sn (%.0f..%.0f)" % (yay(ps), min(ps), max(ps)))
    ayni = yay(cxs) < 40 and yay(cys) < 40 and yay(rs) < 25
    print("  -> %s" % ("ROTA TUTARLI (ayni yorunge) -> ongoru guvenilir"
                       if ayni else "ROTA DEGISKEN -> tek uctan strateji kurma, daha cok gozlem"))


def ciz(metrikler, out):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("(matplotlib yok -> grafik atlandi; metrikler yukarida)")
        return
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    renkler = plt.cm.tab10.colors
    for i, (ad, m) in enumerate(metrikler):
        c = renkler[i % 10]
        ax1.plot(m["xs"], m["ys"], '-', lw=1.0, color=c, alpha=0.8, label=ad[:22])
        ax1.scatter([m["xs"][0]], [m["ys"][0]], color=c, s=60, marker='o', edgecolors='k', zorder=5)
        ax2.plot(m["ts"], m["zs"], '-', lw=1.0, color=c, alpha=0.8, label=ad[:22])
    ax1.set_xlabel("X (m)"); ax1.set_ylabel("Y (m)"); ax1.set_title("TALON ROTASI (ustten; o=baslangic)")
    ax1.axis('equal'); ax1.grid(alpha=0.3); ax1.legend(fontsize=7)
    ax2.set_xlabel("zaman (sn)"); ax2.set_ylabel("irtifa Z (m)"); ax2.set_title("TALON IRTIFA")
    ax2.grid(alpha=0.3); ax2.legend(fontsize=7)
    plt.tight_layout(); plt.savefig(out, dpi=90)
    print("\nGRAFIK: %s" % out)


def main(argv):
    son_n = 3
    args = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--son":
            try:
                son_n = int(argv[i + 1]); i += 2; continue
            except (ValueError, IndexError):
                i += 1; continue
        if a.startswith("--"):
            i += 1; continue
        args.append(a); i += 1
    if args:
        loglar = args
    else:
        aday = sorted(glob.glob(os.path.join(VERI, "ucus_log_*.csv")), key=os.path.getmtime, reverse=True)
        loglar = []
        for p in aday:
            if rota_oku(p):                 # Talon truth verisi olan loglar
                loglar.append(p)
            if len(loglar) >= son_n:
                break
        loglar = loglar[::-1]
    if not loglar:
        print("Talon truth verisi olan ucus_log bulunamadi."); return
    metrikler = []
    for p in loglar:
        pts = rota_oku(p)
        m = karakterize(pts)
        if m is None:
            print("(%s: yetersiz Talon verisi)" % os.path.basename(p)); continue
        yazdir(os.path.basename(p), m)
        metrikler.append((os.path.basename(p), m))
    kiyas(metrikler)
    if metrikler:
        try:
            damga = os.path.getmtime(loglar[-1])
            out = os.path.join(VERI, "talon_rota_kiyas_%d.png" % int(damga))
        except OSError:
            out = os.path.join(VERI, "talon_rota_kiyas.png")
        ciz(metrikler, out)


if __name__ == "__main__":
    main(sys.argv[1:])

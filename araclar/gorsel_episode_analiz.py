# -*- coding: utf-8 -*-
"""
================================================================================
 GORSEL GUDUM TUNE ARACI — ucus logundan episode analizi
================================================================================
Kullanim:
    python araclar/gorsel_episode_analiz.py                  # en yeni veri/ucus_log_*.csv
    python araclar/gorsel_episode_analiz.py veri/ucus_log_20260706_200819.csv

Her GORSEL_GUDUM bolumu (episode) icin yazar:
  - sure, tespit kapsama orani (PN'in girdi kalitesi)
  - EN YAKIN gecis: minR + YATAY/DIKEY bilesenler (truth'tan) -> iskalama hangi eksende?
  - handoff ani gercek mesafe + dikey acik (GPS fazi hedefin kac m altinda birakti?)
  - komut aralik/saturasyon (|cmd|>=0.75 tik orani) + isaret-degisim (osilasyon)
  - png R/Vc/omega seyri, bolum sonu (KILIT'e mi ARAMA'ya mi dustu)
Ozet tablo: minR medyani, dikey-acik medyani, saturasyon -> parametre tune kiyasi
icin TEK SAYILIK metrikler. (Tune dongusu: 1 parametre degistir -> 1 gorev kos ->
bu araci calistir -> minR medyani dustu mu?)
"""
import csv, glob, os, sys

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def f(x):
    try:
        return float(x)
    except (ValueError, TypeError):
        return None

def isaret_degisim(v):
    v = [x for x in v if x is not None and abs(x) > 1e-6]
    if len(v) < 3:
        return 0.0
    return sum(1 for i in range(len(v)-1) if (v[i] > 0) != (v[i+1] > 0)) / (len(v)-1)

def sature(v, esik=0.75):
    v = [x for x in v if x is not None]
    if not v:
        return 0.0
    return sum(1 for x in v if abs(x) >= esik) / len(v)

def analiz(log_yolu):
    rows = list(csv.DictReader(open(log_yolu, encoding="utf-8", errors="replace")))
    if not rows:
        print("bos log"); return
    t0 = f(rows[0]["t_wall"])
    eps, s = [], None
    for i, r in enumerate(rows):
        if r["durum"] == "GORSEL_GUDUM":
            if s is None:
                s = i
        else:
            if s is not None:
                eps.append((s, i-1)); s = None
    if s is not None:
        eps.append((s, len(rows)-1))
    print("%s : %d gorsel episode, gorev %.1fs" %
          (os.path.basename(log_yolu), len(eps), f(rows[-1]["t_wall"]) - t0))
    if not eps:
        print("  (gorsel faz hic devreye girmemis)"); return

    min_rler, dikeyler, handoff_dz, handoff_R = [], [], [], []
    for k, (a, b) in enumerate(eps):
        seg = rows[a:b+1]
        t_a = f(seg[0]["t_wall"]) - t0
        sure = f(seg[-1]["t_wall"]) - t0 - t_a
        gordu = sum(1 for r in seg if f(r["vis_gordu"]) == 1)
        # en yakin gecis (truth)
        best = None
        for r in seg:
            dx, dy, dz = f(r["true_dx"]), f(r["true_dy"]), f(r["true_dz"])
            tx, ty, tz = f(r["true_tx"]), f(r["true_ty"]), f(r["true_tz"])
            if None in (dx, dy, dz, tx, ty, tz):
                continue
            yat = ((dx-tx)**2 + (dy-ty)**2) ** 0.5 / 100.0
            dik = (dz - tz) / 100.0                        # + = drone hedefin USTUNDE
            R = (yat**2 + dik**2) ** 0.5
            if best is None or R < best[0]:
                best = (R, yat, dik)
        # handoff ani (bolum basi)
        r0 = seg[0]
        hz = (f(r0["true_dz"]) - f(r0["true_tz"])) / 100.0 \
            if None not in (f(r0["true_dz"]), f(r0["true_tz"])) else None
        hr = f(r0["gercek_mesafe"]); hr = hr / 100.0 if hr is not None else None
        yaw = [f(r["yaw_cmd"]) for r in seg]; rol = [f(r["roll_cmd"]) for r in seg]
        pit = [f(r["pitch_cmd"]) for r in seg]
        pngR = [f(r["png_R_m"]) for r in seg if f(r["png_R_m"]) is not None]
        sonraki = rows[b+1]["durum"] if b+1 < len(rows) else "LOG SONU"
        satir = "[%2d] sn %6.1f  %4.1fs  kapsama %3.0f%%" % (k, t_a, sure, 100.0*gordu/len(seg))
        if hr is not None:
            satir += "  handoff R=%.0fm dz=%+.1fm" % (hr, hz if hz is not None else 0)
            handoff_R.append(hr)
            if hz is not None:
                handoff_dz.append(hz)
        if best:
            satir += "  minR=%.1fm (yatay %.1f / dikey %+.1f)" % best
            min_rler.append(best[0]); dikeyler.append(best[2])
        satir += "  sat: r%.0f%% p%.0f%%  osi: y%.0f%%" % (
            100*sature(rol), 100*sature(pit), 100*isaret_degisim(yaw))
        if pngR:
            satir += "  pngR %.0f->%.0fm" % (pngR[0], pngR[-1])
        satir += "  -> " + sonraki
        print(satir)

    def medyan(v):
        return sorted(v)[len(v)//2] if v else None
    print("-" * 78)
    print("OZET: minR medyan = %s m | dikey acik (min anda) medyan = %s m | "
          "handoff dz medyan = %s m | handoff R medyan = %s m" % (
        "%.1f" % medyan(min_rler) if min_rler else "-",
        "%+.1f" % medyan(dikeyler) if dikeyler else "-",
        "%+.1f" % medyan(handoff_dz) if handoff_dz else "-",
        "%.0f" % medyan(handoff_R) if handoff_R else "-"))

if __name__ == "__main__":
    if len(sys.argv) > 1:
        yol = sys.argv[1]
    else:
        adaylar = sorted(glob.glob(os.path.join(PROJ, "veri", "ucus_log_*.csv")),
                         key=os.path.getmtime)
        if not adaylar:
            sys.exit("veri/ucus_log_*.csv bulunamadi")
        yol = adaylar[-1]
    analiz(yol)

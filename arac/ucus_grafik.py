# -*- coding: utf-8 -*-
"""
================================================================================
  UCUS GRAFIK  --  tek ucusun 1 Hz GPS izi, kus bakisi, hiza gore renkli cizgi
================================================================================
NE YAPAR
--------------------------------------------------------------------------------
  1) hedef_iz_kaydi.py'nin surekli yazdigi ham kayittan BIR UCUSU keser
     (--baslangic ile isaretlenen andan itibaren),
  2) tam 1 Hz'lik (her saniye bir satir) temiz bir CSV uretir,
  3) kus bakisi X-Y grafigini cizer -- Z KULLANILMAZ,
  4) cizginin RENGI hiza gore degisir: YAVAS = SARI, HIZLI = KIRMIZI.

RENK NEDEN "YUMUSATILMIS" HIZDAN
--------------------------------------------------------------------------------
Ham komsu-fark hizi ornekleme titremesi yuzunden +-%25 zipliyor (olculdu:
dt-hiz korelasyonu -0.861). O hiz renge verilseydi sabit hizla ucan bir arac
bile alacali gorunurdu -- yani renk hizi degil GURULTUYU gosterirdi.
Bu yuzden renk, yay uzunlugundan pencereli olarak hesaplanan hizdan geliyor.

RENK OLCEGI DURUSTLUGU
--------------------------------------------------------------------------------
Olcek her zaman alt basliga YAZILIR. Hiz gercekte sabitse (yayilim gurultu
tabaninin altinda) bu ACIKCA soylenir; renk skalasi yapay olarak gerdirilip
"sanki hiz degisiyormus" gibi gosterilmez.

CALISTIR
    python arac/ucus_grafik.py                          (tum kayit)
    python arac/ucus_grafik.py --baslangic 1234.5       (o andan sonrasi)
    python arac/ucus_grafik.py --csv <yol> --baslangic 0 --bitis 900
================================================================================
"""
import os
import sys
import glob
import argparse

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.colors import LinearSegmentedColormap, Normalize

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CIKTI = os.path.join(KOK, "veri", "hedef_iz")

# Kullanici istegi: SARI -> KIRMIZI. Araya turuncu konuyor ki gecis
# algisal olarak duzgun olsun (sari->kirmizi dogrudan karistirilinca orta
# ton camurlasiyor).
CMAP = LinearSegmentedColormap.from_list(
    "sari_kirmizi", ["#FFE81A", "#FFB400", "#FF7A00", "#F03800", "#B00000"])

# Hiz penceresi: 3 s. 1 Hz veride +-33 ms paket yasi -> %1'in altinda hata.
W = 3.0


def en_yeni_csv():
    a = sorted(glob.glob(os.path.join(CIKTI, "hedef_iz_*.csv")),
               key=os.path.getmtime)
    return a[-1] if a else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=None)
    ap.add_argument("--baslangic", type=float, default=None,
                    help="ham kayittaki t_s degeri; ucus buradan baslar")
    ap.add_argument("--bitis", type=float, default=None)
    ap.add_argument("--ad", default=None, help="cikti dosya adi eki")
    ap.add_argument("--arac", choices=("hedef", "bizim"), default="hedef",
                    help="hangi aracin izi cizilsin (vars: hedef)")
    a = ap.parse_args()

    yol = a.csv or en_yeni_csv()
    if not yol or not os.path.exists(yol):
        print("Ham kayit bulunamadi: veri/hedef_iz/hedef_iz_*.csv")
        return 1

    d = np.genfromtxt(yol, delimiter=",", names=True)
    t = np.asarray(d["t_s"], float)
    on = "h" if a.arac == "hedef" else "d"      # hx/hy = hedef, dx/dy = bizim
    x = np.asarray(d[on + "x_m"], float)
    y = np.asarray(d[on + "y_m"], float)
    ARAC = "Hedef hava araci" if a.arac == "hedef" else "Avci drone (bizim)"

    art = np.concatenate([[True], np.diff(t) > 1e-9])
    t, x, y = t[art], x[art], y[art]

    t0 = a.baslangic if a.baslangic is not None else t[0]
    t1 = a.bitis if a.bitis is not None else t[-1]
    m = (t >= t0) & (t <= t1)
    if m.sum() < 30:
        print("Secilen aralikta yeterli veri yok (%d ornek). "
              "Baslangic/bitis degerlerini kontrol et." % m.sum())
        return 1
    t, x, y = t[m] - t0, x[m], y[m]

    # ---- HIZ: tam hizli veriden pencereli yay uzunlugu (dogru olan) --------
    s = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(x), np.diff(y)))])
    ta = np.clip(t - W / 2.0, t[0], t[-1])
    tb = np.clip(t + W / 2.0, t[0], t[-1])
    v_tam = (np.interp(tb, t, s) - np.interp(ta, t, s)) / np.maximum(tb - ta, 1e-9)

    # ---- 1 Hz IZGARAYA OTURT  (kullanici istegi: "her saniye bazinda") -----
    tg = np.arange(0.0, np.floor(t[-1]) + 1e-9, 1.0)
    xg = np.interp(tg, t, x)
    yg = np.interp(tg, t, y)
    vg = np.interp(tg, t, v_tam)

    ek = ("_" + a.ad) if a.ad else ""
    if a.arac != "hedef":
        ek += "_bizim"
    ucus_csv = os.path.join(CIKTI, "ucus_1hz%s.csv" % ek)
    with open(ucus_csv, "w", encoding="utf-8", newline="\n") as f:
        f.write("t_s,x_m,y_m,hiz_ms\n")
        for i in range(len(tg)):
            f.write("%.0f,%.3f,%.3f,%.3f\n" % (tg[i], xg[i], yg[i], vg[i]))

    # ---- OLCUM OZETI -------------------------------------------------------
    ic = (tg >= W / 2.0) & (tg <= tg[-1] - W / 2.0)
    if ic.sum() < 5:
        ic = np.ones_like(tg, bool)
    vi = vg[ic]
    yol_m = s[-1]
    print("=" * 74)
    print("UCUS  %s" % os.path.basename(yol))
    print("=" * 74)
    print("  sure            : %.0f sn   (%d satir, 1 Hz)" % (tg[-1], len(tg)))
    print("  kat edilen yol  : %.1f m" % yol_m)
    print("  ortalama hiz    : %.2f m/s  (%.1f km/h)"
          % (vi.mean(), vi.mean() * 3.6))
    print("  max / min       : %.2f / %.2f m/s" % (vi.max(), vi.min()))
    print("  std sapma       : %.3f m/s" % vi.std())
    print("  bagimsiz kontrol: %.2f m/s  (toplam yol / toplam sure)"
          % (yol_m / max(t[-1] - t[0], 1e-9)))

    # Renk olcegi: gercek degisim var mi?  Yoksa skalayi GERME.
    yayilim = float(vi.max() - vi.min())
    sabit = yayilim < max(0.5, 0.05 * vi.mean())
    if sabit:
        # Sabit hiz: skalayi 0..max yap. Boylece "her yer ayni renk" gorunur
        # ve bu DOGRU olur -- dar araligi gerip sahte alacalilik uretmeyiz.
        vmin, vmax = 0.0, float(np.ceil(vi.max()))
        not_ = ("hiz SABIT (%.2f m/s, yayilim yalnizca %.2f m/s) -> "
                "renk tek ton, olcek 0-%.0f m/s" % (vi.mean(), yayilim, vmax))
    else:
        vmin, vmax = float(vi.min()), float(vi.max())
        not_ = ("renk olcegi %.1f - %.1f m/s   (sari = yavas, kirmizi = hizli)"
                % (vmin, vmax))
    print("  %s" % not_)

    # ---- CIZIM: kus bakisi, hiza gore renkli CIZGI -------------------------
    fig, ax = plt.subplots(figsize=(11, 10))
    nok = np.column_stack([xg, yg]).reshape(-1, 1, 2)
    seg = np.concatenate([nok[:-1], nok[1:]], axis=1)
    lc = LineCollection(seg, cmap=CMAP, norm=Normalize(vmin, vmax),
                        linewidth=3.2, capstyle="round")
    lc.set_array((vg[:-1] + vg[1:]) / 2.0)       # segmentin ORTA hizi
    ax.add_collection(lc)

    cb = fig.colorbar(lc, ax=ax, pad=0.02, fraction=0.046)
    cb.set_label("hiz (m/s)   —   sari = yavas,  kirmizi = hizli", fontsize=11)

    ax.plot(xg[0], yg[0], "o", ms=13, mfc="white", mec="black", mew=2,
            label="baslangic", zorder=5)
    ax.plot(xg[-1], yg[-1], "X", ms=15, mfc="white", mec="black", mew=2,
            label="bitis", zorder=5)

    # np.ptp(...) fonksiyon halinde: ndarray.ptp() metodu NumPy 2.0'da KALDIRILDI
    p = 0.06 * max(np.ptp(xg), np.ptp(yg), 1.0)
    ax.set_xlim(xg.min() - p, xg.max() + p)
    ax.set_ylim(yg.min() - p, yg.max() + p)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("X  (m)   dogu-bati", fontsize=11)
    ax.set_ylabel("Y  (m)   kuzey-guney", fontsize=11)
    ax.grid(alpha=.3, ls=":")
    ax.legend(loc="best", fontsize=10)
    ax.set_title(ARAC + " — kus bakisi GPS izi  (Z = 0, 1 Hz)\n"
                 "%.0f sn, %.0f m, ort %.1f m/s\n%s"
                 % (tg[-1], yol_m, vi.mean(), not_), fontsize=12)

    fig.tight_layout()
    png = os.path.join(CIKTI, "ucus_1hz%s.png" % ek)
    fig.savefig(png, dpi=140)
    print()
    print("  1 Hz veri -> %s" % ucus_csv)
    print("  grafik    -> %s" % png)
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
"""
================================================================================
  FAZ GECIS ANALIZ  --  "gorsel faza gecince baska yere gidiyor" iddiasinin
                        SAYISAL testi
================================================================================
SORU
--------------------------------------------------------------------------------
GPS -> GORSEL devrinde arac hedefe mi gidiyor, yoksa alakasiz bir yone mi?

NASIL OLCULUYOR
--------------------------------------------------------------------------------
hedef_iz_kaydi.py iki aracin da TRUTH konumunu ~30 Hz yaziyor ve her satira
supervisor'in FAZ damgasini basiyor. Konumdan hiz turetilir (pencereli, ham
komsu farki ornekleme titremesinden dolayi guvenilmez -- olculdu, dt-hiz
korelasyonu -0.861).

Kritik olcu SAPMA ACISI:
    sapma = bizim HIZ VEKTORUMUZ ile "bize gore hedefin yonu" arasindaki aci
      0°  = tam hedefe gidiyoruz
     90°  = hedefin yanindan geciyoruz
    180°  = hedeften KACIYORUZ

Devir aninda bu aci SICRIYORSA ("baska yere gidiyor" sikayeti) sebep faz
girisindeki komut sureksizligidir. Sicramiyorsa sorun devirde degil,
takip yasasindadir.

CALISTIR
    python arac/faz_gecis_analiz.py            (en yeni kayit)
    python arac/faz_gecis_analiz.py <csv>
================================================================================
"""
import os
import sys
import glob
import math

import numpy as np

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CIKTI = os.path.join(KOK, "veri", "hedef_iz")
W = 0.5          # s; hiz penceresi


def en_yeni():
    a = sorted(glob.glob(os.path.join(CIKTI, "hedef_iz_*.csv")),
               key=os.path.getmtime)
    return a[-1] if a else None


def hiz_vek(t, x, y, w=W):
    """Pencereli hiz vektoru (m/s). Ham komsu farki DEGIL -- bkz. dosya basi."""
    ta = np.clip(t - w / 2, t[0], t[-1])
    tb = np.clip(t + w / 2, t[0], t[-1])
    dt = np.maximum(tb - ta, 1e-6)
    return ((np.interp(tb, t, x) - np.interp(ta, t, x)) / dt,
            (np.interp(tb, t, y) - np.interp(ta, t, y)) / dt)


def main():
    yol = sys.argv[1] if len(sys.argv) > 1 else en_yeni()
    if not yol or not os.path.exists(yol):
        print("Kayit yok: veri/hedef_iz/hedef_iz_*.csv")
        return 1

    d = np.genfromtxt(yol, delimiter=",", names=True, dtype=None, encoding="utf-8")
    if "faz" not in (d.dtype.names or ()):
        print("Bu kayitta FAZ sutunu yok (eski surum). Arayuzu yeniden baslat.")
        return 1
    t = np.asarray(d["t_s"], float)
    faz = np.asarray([str(v) for v in d["faz"]])
    hx, hy = np.asarray(d["hx_m"], float), np.asarray(d["hy_m"], float)
    dx, dy = np.asarray(d["dx_m"], float), np.asarray(d["dy_m"], float)

    art = np.concatenate([[True], np.diff(t) > 1e-9])
    t, faz, hx, hy, dx, dy = t[art], faz[art], hx[art], hy[art], dx[art], dy[art]
    if len(t) < 50:
        print("Kayit cok kisa (%d ornek)." % len(t))
        return 1

    bvx, bvy = hiz_vek(t, dx, dy)        # bizim hiz
    hvx, hvy = hiz_vek(t, hx, hy)        # hedef hizi
    lx, ly = hx - dx, hy - dy            # bize gore hedef yonu
    menzil = np.hypot(lx, ly)
    bhiz = np.hypot(bvx, bvy)

    # SAPMA ACISI: hiz vektorumuz ile hedefe olan yon arasindaki aci
    nz = (bhiz > 0.5) & (menzil > 0.3)
    sapma = np.full(len(t), np.nan)
    sapma[nz] = np.degrees(np.arccos(np.clip(
        (bvx[nz] * lx[nz] + bvy[nz] * ly[nz]) / (bhiz[nz] * menzil[nz]), -1, 1)))

    # GECISLER: faz GPS -> VISUAL
    gec = [i for i in range(1, len(faz))
           if faz[i] == "VISUAL" and faz[i - 1] != "VISUAL"]
    print("=" * 76)
    print("FAZ GECIS ANALIZI   %s" % os.path.basename(yol))
    print("=" * 76)
    print("  kayit %.0f sn, %d ornek | GPS->GORSEL gecisi: %d"
          % (t[-1] - t[0], len(t), len(gec)))
    if not gec:
        print("\n  Hic gorsel faza gecilmemis. (Gorsel Gudum'e basildi mi?)")
        return 0

    ozet = []
    for k, i in enumerate(gec, 1):
        t0 = t[i]
        onc = (t >= t0 - 2.0) & (t < t0)
        son = (t >= t0) & (t <= t0 + 3.0)
        if onc.sum() < 5 or son.sum() < 5:
            continue
        print()
        print("-" * 76)
        print("  GECIS #%d   t=%.1f s   menzil %.1f m" % (k, t0, menzil[i]))
        print("-" * 76)
        print("  %-26s%12s%12s" % ("olcu", "ONCE (2s)", "SONRA (3s)"))
        for ad, v in (("bizim hiz (m/s)", bhiz),
                      ("hedef hizi (m/s)", np.hypot(hvx, hvy)),
                      ("menzil (m)", menzil),
                      ("SAPMA ACISI (derece)", sapma)):
            a = np.nanmean(v[onc]); b = np.nanmean(v[son])
            print("  %-26s%12.1f%12.1f" % (ad, a, b))
        # sureklilik: gecisin HEMEN oncesi/sonrasi (0.3 s)
        p = (t >= t0 - 0.3) & (t < t0)
        q = (t >= t0) & (t <= t0 + 0.3)
        d_yon = np.nan
        if p.sum() > 2 and q.sum() > 2:
            a1 = math.atan2(np.nanmean(bvy[p]), np.nanmean(bvx[p]))
            a2 = math.atan2(np.nanmean(bvy[q]), np.nanmean(bvx[q]))
            d_yon = abs(math.degrees((a2 - a1 + math.pi) % (2 * math.pi) - math.pi))
        print()
        print("  gecis aninda YON SICRAMASI (+-0.3 s): %.0f derece" % d_yon)
        print("  menzil egilimi: %.1f m -> %.1f m  (%s)"
              % (menzil[i], np.nanmean(menzil[son]),
                 "YAKLASIYOR" if np.nanmean(menzil[son]) < menzil[i] else "UZAKLASIYOR"))
        s_son = np.nanmean(sapma[son])
        print("  sapma acisi sonrasi: %.0f derece  -> %s"
              % (s_son,
                 "HEDEFE GIDIYOR" if s_son < 30 else
                 ("YANINDAN GECIYOR" if s_son < 120 else "HEDEFTEN KACIYOR")))
        ozet.append((np.nanmean(sapma[onc]), s_son, d_yon,
                     menzil[i], np.nanmean(menzil[son])))

    if ozet:
        A = np.array(ozet)
        print()
        print("=" * 76)
        print("TOPLU SONUC  (%d gecis)" % len(ozet))
        print("=" * 76)
        print("  sapma acisi  ONCE %.0f°  ->  SONRA %.0f°"
              % (np.nanmean(A[:, 0]), np.nanmean(A[:, 1])))
        print("  gecis aninda yon sicramasi: ort %.0f°, max %.0f°"
              % (np.nanmean(A[:, 2]), np.nanmax(A[:, 2])))
        print("  menzil: %.1f m -> %.1f m" % (np.nanmean(A[:, 3]), np.nanmean(A[:, 4])))
        print()
        if np.nanmean(A[:, 1]) > 90:
            print("  KARAR: gorsel fazda arac hedeften UZAKLASAN bir yone gidiyor.")
            print("         Sikayet DOGRULANDI -- faz girisi bozuk.")
        elif np.nanmean(A[:, 1]) - np.nanmean(A[:, 0]) > 25:
            print("  KARAR: devirden SONRA sapma belirgin artiyor (+%.0f°)."
                  % (np.nanmean(A[:, 1]) - np.nanmean(A[:, 0])))
            print("         Faz girisinde sureksizlik VAR.")
        else:
            print("  KARAR: devir sonrasi sapma artmiyor -- arac hedefe gitmeye")
            print("         devam ediyor. Sorun devirde DEGIL, takip yasasinda.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

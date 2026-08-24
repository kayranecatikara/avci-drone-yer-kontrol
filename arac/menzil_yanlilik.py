# -*- coding: utf-8 -*-
"""
================================================================================
  MENZIL YANLILIK  --  "R = 160/kutu" kestirimi ne kadar yaniliyor?
================================================================================
NEDEN
--------------------------------------------------------------------------------
Gorsel faz boyunca menzili YALNIZCA kutu boyutundan kestiriyoruz:
    R ≈ MENZIL_PX_M / boyut,   boyut = sqrt(w·h),   MENZIL_PX_M = 160
Gazebo ekibi ayni formulu ayni sabitle kullaniyor ve kendi olcumlerinde
kestirimin hedefi UZAKTA 12-21 m YAKIN sandigini buldu (RAPOR §3.3, §10.4-e).
Bizde de ayniysa zincirleme etkisi buyuk:
    * hiz PI'si  -> boyut hatasindan uretiliyor
    * terminal mandali -> kutu >= 25 px
    * terminal dikey yasa -> kapanma hizi (r_dot) uzerinden

NASIL OLCULUYOR
--------------------------------------------------------------------------------
Iki bagimsiz kaynak AYNI saat ekseninde:
    bbox_ibvs_*.csv      t (perf_counter), boyut  -> KESTIRIM
    hedef_iz_*.csv       t_mutlak (perf_counter), iki aracin TRUTH konumu
                         -> GERCEK menzil
Truth konumlar guduume GIRMIYOR, yalniz olcum icin. Kestirim gercege
interpolasyonla eslestirilir.

CALISTIR  python arac/menzil_yanlilik.py
================================================================================
"""
import os
import sys
import glob

import numpy as np

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IZ = os.path.join(KOK, "veri", "hedef_iz")
LOG = os.path.join(KOK, "kopru", "gazebo_kaynak", "logs")
MENZIL_PX_M = 160.0


def main():
    izler = sorted(glob.glob(os.path.join(IZ, "hedef_iz_*.csv")),
                   key=os.path.getmtime)
    # t_mutlak sutunu olan EN YENI iz kaydini bul
    T = None
    for p in reversed(izler):
        try:
            d = np.genfromtxt(p, delimiter=",", names=True, dtype=None,
                              encoding="utf-8")
        except Exception:
            continue
        if d.dtype.names and "t_mutlak" in d.dtype.names and d.size > 100:
            T, yol = d, p
            break
    if T is None:
        print("t_mutlak sutunlu iz kaydi yok. Arayuzu yeniden baslatip ucus yap.")
        return 1

    tm = np.asarray(T["t_mutlak"], float)
    hx, hy, hz = (np.asarray(T["hx_m"], float), np.asarray(T["hy_m"], float),
                  np.asarray(T["hz_m"], float))
    dx, dy, dz = (np.asarray(T["dx_m"], float), np.asarray(T["dy_m"], float),
                  np.asarray(T["dz_m"], float))
    gercek = np.sqrt((hx - dx) ** 2 + (hy - dy) ** 2 + (hz - dz) ** 2)
    a = np.argsort(tm)
    tm, gercek = tm[a], gercek[a]
    print("=" * 74)
    print("MENZIL YANLILIK OLCUMU")
    print("=" * 74)
    print("  iz kaydi   : %s  (%d ornek, %.0f-%.0f s)"
          % (os.path.basename(yol), len(tm), tm[0], tm[-1]))

    # IBVS kayitlarindan kestirimleri topla, zaman araligina DUSENLER
    est, ger = [], []
    n_dosya = 0
    for p in sorted(glob.glob(os.path.join(LOG, "bbox_ibvs_*.csv")),
                    key=os.path.getmtime):
        try:
            d = np.genfromtxt(p, delimiter=",", names=True, encoding="utf-8")
        except Exception:
            continue
        if d.size < 5 or "boyut" not in (d.dtype.names or ()):
            continue
        t = np.atleast_1d(np.asarray(d["t"], float))
        b = np.atleast_1d(np.asarray(d["boyut"], float))
        m = np.isfinite(b) & (b > 1e-6) & (t >= tm[0]) & (t <= tm[-1])
        if m.sum() < 3:
            continue
        n_dosya += 1
        est.append(MENZIL_PX_M / b[m])
        ger.append(np.interp(t[m], tm, gercek))
    if not est:
        print("  Zaman araligina dusen IBVS kaydi YOK.")
        print("  (iz kaydi ile ayni oturumda gorsel faz yasanmis olmali)")
        return 1
    E = np.concatenate(est)
    G = np.concatenate(ger)
    print("  IBVS dosyasi: %d   eslesen ornek: %d" % (n_dosya, len(E)))

    hata = E - G                      # + : oldugundan UZAK saniyor
    print()
    print("  %-14s%7s%10s%10s%10s%9s" % ("gercek menzil", "kare", "gercek",
                                         "kestirim", "hata", "oran"))
    for lo, hi in ((0, 5), (5, 10), (10, 20), (20, 35), (35, 60), (60, 200)):
        m = (G >= lo) & (G < hi)
        if m.sum() < 5:
            continue
        print("  %-14s%7d%9.1f%10.1f%+10.1f%8.2fx"
              % ("%d-%d m" % (lo, hi), m.sum(), np.median(G[m]),
                 np.median(E[m]), np.median(hata[m]),
                 np.median(E[m]) / max(np.median(G[m]), 1e-6)))
    print()
    print("  TOPLU: medyan hata %+.1f m   (kestirim/gercek = %.2fx)"
          % (np.median(hata), np.median(E) / max(np.median(G), 1e-6)))
    yon = "YAKIN saniyor" if np.median(hata) < 0 else "UZAK saniyor"
    print("  -> kestirim hedefi %s" % yon)

    # En iyi olcek sabitini coz: R = K/boyut  ->  K = R·boyut
    K = np.median(G * (MENZIL_PX_M / E))
    print()
    print("  MENZIL_PX_M su an : %.0f" % MENZIL_PX_M)
    print("  olculen en iyi    : %.0f   (medyan R·boyut)" % K)
    if abs(K - MENZIL_PX_M) / MENZIL_PX_M > 0.15:
        print("  ⚠ %.0f%% sapma var -> sabit YENIDEN KALIBRE EDILMELI"
              % (100 * abs(K - MENZIL_PX_M) / MENZIL_PX_M))
    else:
        print("  sabit makul (sapma %%%.0f)" % (100 * abs(K - MENZIL_PX_M) / MENZIL_PX_M))
    return 0


if __name__ == "__main__":
    sys.exit(main())

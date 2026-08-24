# -*- coding: utf-8 -*-
"""
================================================================================
  UCUS GOZCU  --  ucusun BITTIGINI kendiliginden anlar
================================================================================
Kullanici "bittiginde sen anlarsin" dedi. Bu betik ham kaydi izler ve su
uc durumdan biri olunca CIKAR (cikinca ana oturum haberdar olur):

  1) GOREV BITTI : bizim drone bir sure UCTU (>2 m/s), sonra 20 sn boyunca
                   durdu (<0.5 m/s). Yani inis/gorev sonu.
  2) BAGLANTI    : kayit 30 sn boyunca hic buyumedi -> oyun kapandi/koptu.
  3) SURE        : en fazla --azami dakika bekler, sonra yine de cikar.

Cikis kodu degil, EKRANA yazdigi "SEBEP:" satiri okunur.

CALISTIR
    python arac/ucus_gozcu.py --baslangic 2286.2 [--azami 45]
================================================================================
"""
import os
import sys
import time
import glob
import argparse

import numpy as np

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CIKTI = os.path.join(KOK, "veri", "hedef_iz")


def son_csv():
    a = sorted(glob.glob(os.path.join(CIKTI, "hedef_iz_*.csv")),
               key=os.path.getmtime)
    return a[-1] if a else None


def oku(yol, t0):
    try:
        d = np.genfromtxt(yol, delimiter=",", names=True)
    except Exception:
        return None
    if d.size < 5:
        return None
    t = np.asarray(d["t_s"], float)
    m = t >= t0
    if m.sum() < 5:
        return None
    return (t[m], np.asarray(d["dx_m"], float)[m], np.asarray(d["dy_m"], float)[m],
            np.asarray(d["hx_m"], float)[m], np.asarray(d["hy_m"], float)[m])


def hiz(t, x, y, W=2.0):
    s = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(x), np.diff(y)))])
    ta = np.clip(t - W / 2, t[0], t[-1])
    tb = np.clip(t + W / 2, t[0], t[-1])
    return (np.interp(tb, t, s) - np.interp(ta, t, s)) / np.maximum(tb - ta, 1e-9)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baslangic", type=float, required=True)
    ap.add_argument("--azami", type=float, default=45.0, help="dakika")
    a = ap.parse_args()

    yol = son_csv()
    if not yol:
        print("SEBEP: ham kayit yok")
        return

    t_bas = time.time()
    ucmustu = False
    son_boy = -1
    son_buyume = time.time()
    print("[GOZCU] izliyorum  (baslangic t_s=%.1f, azami %.0f dk)"
          % (a.baslangic, a.azami))

    while True:
        time.sleep(10.0)
        gecen = (time.time() - t_bas) / 60.0

        boy = os.path.getsize(yol) if os.path.exists(yol) else -1
        if boy != son_boy:
            son_boy, son_buyume = boy, time.time()
        elif time.time() - son_buyume > 30.0:
            print("SEBEP: kayit 30 sn buyumedi -> oyun baglantisi kapandi")
            return

        r = oku(yol, a.baslangic)
        if r is None:
            continue
        t, dx, dy, hx, hy = r
        if t[-1] - t[0] < 5.0:
            continue

        vd = hiz(t, dx, dy)
        if not ucmustu and (vd > 2.0).sum() > 60:      # ~2 sn'lik gercek ucus
            ucmustu = True
            print("[GOZCU] bizim arac ucuyor (max %.1f m/s) -- inis bekleniyor"
                  % vd.max())

        if ucmustu:
            # son 20 sn duruyor mu?
            sonrasi = t >= t[-1] - 20.0
            if sonrasi.sum() > 30 and vd[sonrasi].max() < 0.5:
                print("SEBEP: bizim arac 20 sn hareketsiz -> GOREV BITTI")
                return

        if gecen >= a.azami:
            print("SEBEP: azami sure (%.0f dk) doldu" % a.azami)
            return


if __name__ == "__main__":
    main()

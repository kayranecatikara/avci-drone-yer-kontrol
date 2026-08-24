# -*- coding: utf-8 -*-
"""
================================================================================
  KOS  --  GERCEK gorsel guduum yasasini simulatorde kosturur
================================================================================
⚠ EN ONEMLI KURAL: yasa kodu DEGISTIRILMEZ.
bbox_ibvs.komut() dogrudan import edilip cagriliyor. Boylece burada bulunan
her sey oyunda da gecerlidir; simulator yalnizca TESISI (arac + hedef +
kamera) taklit eder.

komut() SAF bir fonksiyon (thread yok, zaman yok, I/O yok) — bu yuzden
gercek zamandan bagimsiz, deterministik ve cok hizli kosabiliyoruz.

CALISTIR
    python sim/kos.py                 tek angajman, ayrinti dokumu
    python sim/kos.py --n 200         200 angajman, ozet
================================================================================
"""
import os
import sys
import math
import argparse

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "kopru", "gazebo_kaynak"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tesis import Avci, Hedef, Olcum, kadraj, tespit_olasilik, CX, CY, FX, FY
from control.guidance import bbox_ibvs as IB


def tek_kosu(faz0=0.0, avci_faz=0.15, sure=25.0, dt=1.0 / 62.0,
             tespit_gurultusu=True, tohum=0, cfg=IB.Cfg, kayit=False):
    """Bir gorsel angajman kosar.

    Baslangic: avci hedefin GERISINDE, devir mesafesinde (~13 m) — yani
    GPS fazinin devrettigi anda basliyoruz. Amac gorsel yasayi IZOLE
    sinamak; GPS fazi bu testin disinda.
    """
    import random
    rnd = random.Random(tohum)

    hed = Hedef(faz0=faz0)
    hx, hy, hz, hvx, hvy, _ = hed.durum()
    # avciyi hedefin GERISINE, hiz yonunun tersine yerlestir
    hdg = math.atan2(hvy, hvx)
    D = 13.0                                   # devir mesafesi (olculen medyan)
    av = Avci(x=hx - D * math.cos(hdg), y=hy - D * math.sin(hdg),
              z=hz - 3.0, yaw=hdg,
              max_accel=cfg.MAX_ACCEL, v_max=cfg.V_TOPLAM_MAX,
              vz_max=cfg.VZ_MAX, yaw_rate_max=cfg.YAW_RATE_MAX_DEG)
    av.vx, av.vy = Olcum.HEDEF_HIZ * math.cos(hdg), Olcum.HEDEF_HIZ * math.sin(hdg)

    hiz_I = Olcum.HEDEF_HIZ                    # sicak baslangic (yasadaki ff_hiz)
    t = 0.0
    kayip = 0
    terminal = False
    los_onceki = None
    los_hiz = (0.0, 0.0)
    en_yakin = 1e9
    izler = []
    gorulen_kare = 0
    toplam_kare = 0

    while t < sure:
        hed.adim(dt)
        hx, hy, hz, hvx, hvy, _ = hed.durum()
        av._hedef_yon = math.atan2(hvy, hvx)       # kutu boyutu bakis acisina bagli
        k = kadraj(av, hx, hy, hz)
        toplam_kare += 1

        pose = None
        if k is not None:
            cx, cy, w, h, menzil = k
            en_yakin = min(en_yakin, menzil)
            p = tespit_olasilik(w, h) if tespit_gurultusu else 1.0
            if rnd.random() < p:
                pose = (cx, cy, w, h)
                gorulen_kare += 1
        else:
            menzil = math.dist((av.x, av.y, av.z), (hx, hy, hz))
            en_yakin = min(en_yakin, menzil)

        if pose is not None:
            kayip = 0
            cx, cy, w, h = pose
            # atalet LOS azimut hizi (yasanin bekledigi girdi)
            los_az = av.yaw + math.atan((cx - cfg.CX_NISAN) / FX)
            if los_onceki is not None:
                d = (los_az - los_onceki + math.pi) % (2 * math.pi) - math.pi
                los_hiz = (d / dt, 0.0)
            los_onceki = los_az

            boyut = math.sqrt(w * h)
            if not terminal and boyut >= cfg.TERMINAL_BOYUT:
                terminal = True

            vx, vy, vz, yaw_cmd, hiz_I, tani = IB.komut(
                cx, cy, w, h, av.yaw, hiz_I, dt, cfg, terminal,
                tuple(los_hiz), av.pitch, av.vz, None, av.roll, av.yaw_hizi)
            av.setpoint(vx, vy, vz, yaw_cmd, t)
            if kayit:
                izler.append((t, menzil, cx, cy, boyut,
                              math.degrees(tani["eps_yaw"]),
                              math.degrees(math.atan2(vy, vx)),
                              math.degrees(av.yaw)))
        else:
            kayip += 1
            if kayip >= 20:                    # KAYIP_M — sartname
                break

        av.adim(dt, t)
        t += dt

    return {"en_yakin": en_yakin, "sure": t,
            "gorulen": gorulen_kare, "toplam": toplam_kare,
            "gorus_oran": gorulen_kare / max(toplam_kare, 1),
            "terminal": terminal, "iz": izler}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1)
    ap.add_argument("--sure", type=float, default=25.0)
    ap.add_argument("--gurultusuz", action="store_true",
                    help="tespit gurultusunu KAPAT (yasayi izole sina)")
    a = ap.parse_args()

    if a.n == 1:
        r = tek_kosu(sure=a.sure, tespit_gurultusu=not a.gurultusuz, kayit=True)
        print("=" * 70)
        print("TEK ANGAJMAN")
        print("=" * 70)
        print("  sure %.2f s | en yakin %.2f m | gorus %%%.0f | terminal %s"
              % (r["sure"], r["en_yakin"], 100 * r["gorus_oran"],
                 "EVET" if r["terminal"] else "hayir"))
        print()
        print("  %6s%9s%8s%8s%9s%10s%11s" %
              ("t", "menzil", "cx", "boyut", "eps_yaw", "komut_yon", "arac_yaw"))
        iz = r["iz"]
        for i in range(0, len(iz), max(1, len(iz) // 18)):
            t, m, cx, cy, b, e, ky, ay = iz[i]
            print("  %6.2f%8.1fm%8.0f%8.0f%8.0f°%9.0f°%10.0f°"
                  % (t, m, cx, b, e, ky, ay))
        return

    import statistics as st
    sonuc = []
    for i in range(a.n):
        r = tek_kosu(faz0=i / a.n, sure=a.sure,
                     tespit_gurultusu=not a.gurultusuz, tohum=i)
        sonuc.append(r)
    ey = [r["en_yakin"] for r in sonuc]
    su = [r["sure"] for r in sonuc]
    go = [r["gorus_oran"] for r in sonuc]
    isabet = sum(1 for x in ey if x < 1.0)
    print("=" * 70)
    print("%d ANGAJMAN%s" % (a.n, "  (tespit gurultusu KAPALI)" if a.gurultusuz else ""))
    print("=" * 70)
    print("  en yakin menzil : medyan %.2f m  min %.2f  max %.2f"
          % (st.median(ey), min(ey), max(ey)))
    print("  faz suresi      : medyan %.2f s" % st.median(su))
    print("  gorus orani     : medyan %%%.0f" % (100 * st.median(go)))
    print("  terminal        : %d/%d" % (sum(1 for r in sonuc if r["terminal"]), a.n))
    print("  ISABET (<1 m)   : %d/%d  (%%%.1f)" % (isabet, a.n, 100 * isabet / a.n))


if __name__ == "__main__":
    main()

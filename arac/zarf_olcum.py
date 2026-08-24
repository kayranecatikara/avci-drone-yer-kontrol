# -*- coding: utf-8 -*-
"""
================================================================================
  ZARF OLCUM  --  aracin GERCEK fiziksel zarfini olcer (yazilim clamp'i DEGIL)
================================================================================
NEDEN
--------------------------------------------------------------------------------
Gazebo eslestirmesi icin "(b) sinir kaldirilinca aracin yapabildigi" lazim.
Gudum uzerinden olculen her sey bizim kendi clamp'imize dayaniyordu:
    MAX_ACCEL=12 iken olculen yanal ivme max 11.96 m/s²  <- BIZIM sinirimiz
    MAX_ACCEL=20 iken olculen yanal ivme max 31.67 m/s²  <- hala doymadi
Yani gudum yolu zarfi olcmeye UYGUN DEGIL.

BU BETIK NE YAPAR
--------------------------------------------------------------------------------
/api/manuel uzerinden DOGRUDAN KUMANDA CUBUGU komutu gonderir
(set_control_surfaces -> throttle/pitch/roll/yaw). Bu yol gudumun hiz
clamp'lerini TAMAMEN atlar, yani aracin kendi limitine dayanir.

Test dizisi (her adim arasi 2 s notr toparlanma):
    1. TAM SAG ROLL      3 s  -> max yanal ivme, hiz vektoru donus hizi
    2. TAM SOL ROLL      3 s  -> ayni, simetri kontrolu
    3. TAM ILERI PITCH   4 s  -> max yatay ivme ve max hiz
    4. TAM THROTTLE      3 s  -> max tirmanma
    5. TAM ASAGI         3 s  -> max alcalma
    6. TAM YAW           3 s  -> max yaw hizi
    7. BASAMAK (step)    roll 0 -> 1 ani  -> KOMUT-TEPKI GECIKMESI

OLCUM NEREDEN GELIYOR
--------------------------------------------------------------------------------
Bu betik OLCMEZ, yalniz KOMUT gonderir ve her adimin zamanini damgalar.
Olcumu sunucunun icinde zaten calisan 30 Hz'lik truth iz kaydi yapar
(arac/hedef_iz_kaydi.py -> veri/hedef_iz/hedef_iz_*.csv).
    ⚠ NEDEN BOYLE: /api/telemetry yalniz ~2 Hz guncelleniyor (olculdu:
      medyan 235 ms) -> ivme/donus icin cok yavas. Ayri surecten
      drone_sdk.get_debug_truth() ise BOS doner, cunku oyun TEK TCP
      baglantisi kabul ediyor ve onu sunucu tutuyor.
    Windows'ta time.perf_counter() QPC tabanli ve SURECLER ARASI ORTAK
    (dogrulandi) -> zaman damgalari iz kaydiyla birebir hizalanir.

⚠ UYARI: arac bu test boyunca SERT manevra yapar. Yeterli irtifa ve
bos alan olsun. CTRL+C her an notr komut gonderip cikar.

CALISTIR  python arac/zarf_olcum.py
================================================================================
"""
import os
import sys
import glob
import json
import time
import math
import urllib.request

import numpy as np

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = "http://127.0.0.1:8000"

zaman_cizelgesi = []          # (asama, t_bas, t_bit)


def post(yol, veri):
    r = urllib.request.Request(URL + yol, data=json.dumps(veri).encode(),
                               headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=3) as f:
        return f.read()


def cubuk(thr=0.0, pit=0.0, rol=0.0, yaw=0.0):
    post("/api/manuel", {"throttle": thr, "pitch": pit, "roll": rol, "yaw": yaw})


def adim(ad, sure, **k):
    print("  %-18s %.1f s  %s" % (ad, sure, k), flush=True)
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < sure:
        cubuk(**k)
        time.sleep(0.05)
    zaman_cizelgesi.append((ad, t0, time.perf_counter()))
    t0 = time.perf_counter()          # notr toparlanma
    while time.perf_counter() - t0 < 2.0:
        cubuk()
        time.sleep(0.05)


def iz_oku():
    """Sunucunun 30 Hz truth iz kaydini okur -> (ad, t, x, y, z)."""
    fs = sorted(glob.glob(os.path.join(KOK, "veri", "hedef_iz", "hedef_iz_*.csv")),
                key=os.path.getmtime)
    for yol in reversed(fs):
        try:
            d = np.genfromtxt(yol, delimiter=",", names=True, dtype=None,
                              encoding="utf-8")
        except Exception:
            continue
        if d.dtype.names and "t_mutlak" in d.dtype.names and d.size > 50:
            t = np.asarray(d["t_mutlak"], float)
            a = np.argsort(t)
            return (os.path.basename(yol), t[a],
                    np.asarray(d["dx_m"], float)[a],
                    np.asarray(d["dy_m"], float)[a],
                    np.asarray(d["dz_m"], float)[a])
    return None


def coz(t, x, y, z, t0, t1, kirp=0.4):
    """Zaman penceresindeki hiz / ivme / donus hizi."""
    m = (t >= t0 + kirp) & (t <= t1)
    if m.sum() < 8:
        return None
    tt, xx, yy, zz = t[m], x[m], y[m], z[m]
    W = 0.25
    ta = np.clip(tt - W / 2, tt[0], tt[-1])
    tb = np.clip(tt + W / 2, tt[0], tt[-1])
    dt = np.maximum(tb - ta, 1e-9)

    def d(v):
        return (np.interp(tb, tt, v) - np.interp(ta, tt, v)) / dt

    vx, vy, vz = d(xx), d(yy), d(zz)
    V = np.hypot(vx, vy)
    ah = np.hypot(d(vx), d(vy))
    psi = np.unwrap(np.arctan2(vy, vx))
    om = np.abs(np.degrees((np.interp(tb, tt, psi) - np.interp(ta, tt, psi)) / dt))
    return {"n": int(m.sum()), "V": float(V.max()), "a": float(ah.max()),
            "om": float(om.max()), "vzmax": float(vz.max()),
            "vzmin": float(vz.min())}


def main():
    print("=" * 72)
    print("ZARF OLCUMU - aracin GERCEK limitleri (gudum clamp'leri devre disi)")
    print("=" * 72)
    try:
        post("/api/command", {"cmd": "manuel_on"})
    except Exception as e:
        print("  !! arayuze baglanilamadi: %r" % e)
        return 1
    print("  manuel mod ACIK - komut dizisi basliyor")
    print("")

    try:
        adim("notr_baslangic", 2.0)
        adim("roll_sag", 3.0, rol=1.0)
        adim("roll_sol", 3.0, rol=-1.0)
        adim("pitch_ileri", 4.0, pit=1.0)
        adim("throttle_yukari", 3.0, thr=1.0)
        adim("throttle_asagi", 3.0, thr=-1.0)
        adim("yaw_sag", 3.0, yaw=1.0)
        adim("step", 2.5, rol=1.0)
    except KeyboardInterrupt:
        print("  kesildi")
    finally:
        for _ in range(25):
            try:
                cubuk()
            except Exception:
                pass
            time.sleep(0.05)

    print("")
    print("  komutlar bitti, notr gonderildi. Iz kaydi bekleniyor...")
    time.sleep(8.0)          # logger 500 satirda bir flush ediyor

    r = iz_oku()
    if r is None:
        print("  !! iz kaydi okunamadi (t_mutlak sutunlu dosya yok)")
        return 1
    ad, t, x, y, z = r
    print("  iz: %s  (%d ornek, t %.0f..%.0f)" % (ad, len(t), t[0], t[-1]))

    print("")
    print("=" * 72)
    print("SONUC - aracin OLCULEN zarfi")
    print("=" * 72)
    print("  %-18s%6s%8s%9s%9s%9s%9s"
          % ("asama", "n", "V max", "a_yatay", "om max", "vz max", "vz min"))
    ozet = {}
    for asama, t0, t1 in zaman_cizelgesi:
        c = coz(t, x, y, z, t0, t1)
        if not c:
            print("  %-18s  (iz kaydinda yok / yetersiz ornek)" % asama)
            continue
        ozet[asama] = c
        print("  %-18s%6d%8.1f%9.2f%9.1f%9.1f%9.1f"
              % (asama, c["n"], c["V"], c["a"], c["om"], c["vzmax"], c["vzmin"]))

    if ozet:
        A = max(c["a"] for c in ozet.values())
        O = max(c["om"] for c in ozet.values())
        V = max(c["V"] for c in ozet.values())
        print("")
        print("  == ZARF ==")
        print("    max yatay ivme      : %.2f m/s²   (esdeger yatis %.0f derece)"
              % (A, math.degrees(math.atan(A / 9.81))))
        print("    max hiz vek. donusu : %.1f derece/s" % O)
        print("    max yatay hiz       : %.1f m/s" % V)
        print("    max tirmanma        : %.1f m/s"
              % max(c["vzmax"] for c in ozet.values()))
        print("    max alcalma         : %.1f m/s"
              % min(c["vzmin"] for c in ozet.values()))
        print("")
        print("    KIYAS: gudum yoluyla olculen max ivme 11.96 (clamp 12) /")
        print("           31.67 (clamp 20). Bu test clamp'siz.")

    st = [zz for zz in zaman_cizelgesi if zz[0] == "step"]
    if st:
        _, t0, t1 = st[0]
        m = (t >= t0 - 0.5) & (t <= t1)
        if m.sum() > 12:
            tt, xx, yy = t[m] - t0, x[m], y[m]
            W = 0.15
            ta = np.clip(tt - W / 2, tt[0], tt[-1])
            tb = np.clip(tt + W / 2, tt[0], tt[-1])
            dt = np.maximum(tb - ta, 1e-9)

            def d(v):
                return (np.interp(tb, tt, v) - np.interp(ta, tt, v)) / dt

            a = np.hypot(d(d(xx)), d(d(yy)))
            p = tt > 0
            if p.sum() > 5 and a[p].max() > 0.5:
                ap, tp = a[p], tt[p]
                i = int(np.argmax(ap > 0.10 * ap.max()))
                j = int(np.argmax(ap > 0.632 * ap.max()))
                print("")
                print("  == BASAMAK TEPKISI (komut -> arac) ==")
                print("    olu zaman (ivme %%10) : %4.0f ms" % (tp[i] * 1000))
                print("    zaman sabiti (%%63)   : %4.0f ms" % (tp[j] * 1000))

    yol = os.path.join(KOK, "veri", "zarf_olcum_asamalar.csv")
    with open(yol, "w", encoding="utf-8", newline="\n") as f:
        f.write("asama,t_bas,t_bit\n")
        for a_, b_, c_ in zaman_cizelgesi:
            f.write("%s,%.4f,%.4f\n" % (a_, b_, c_))
    print("")
    print("  asama zamanlari -> %s" % yol)
    print("  ! MANUEL MOD ACIK KALDI - arayuzden kapat")
    return 0


if __name__ == "__main__":
    sys.exit(main())

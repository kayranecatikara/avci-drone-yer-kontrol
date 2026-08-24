# -*- coding: utf-8 -*-
"""
================================================================================
  ZARF OLCUM 2  --  ilk testin ATLADIGI iki buyuklugu olcer
================================================================================
ILK TESTIN KUSURU (zarf_olcum.py)
--------------------------------------------------------------------------------
Test HAVADA ASILIYKEN basladi. Oradan tam roll vermek araci yana DUZ
ivmelendiriyor -- hiz vektorunun YONU degismiyor, yani donus hizi olculmuyor
(olculen om ~0.1-0.3 °/s, anlamsiz). Dogrusu: once ileri hiz kazan, SONRA
roll ver; o zaman mevcut hiz vektoru DONER.

Ayrica burun (yaw) hizi iz kaydindan cikmiyor -- o dosyada attitude yok.
Burada /api/telemetry'den yaw okunuyor (2 Hz, ama 3 saniyelik SUREKLI bir
donuste ortalama hiz icin yeterli).

TEST DIZISI
    1. ILERI HIZLAN        4 s  pitch=1        -> hiz kazan
    2. HIZLIYKEN TAM ROLL  4 s  pitch=1 rol=1  -> HIZ VEKTORU DONUSU
    3. notr                2 s
    4. YAW (yerinde)       4 s  yaw=1          -> BURUN donus hizi (API'den)

CALISTIR  python arac/zarf_olcum2.py
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
cizelge = []
yaw_ornek = []          # (t, yaw_deg)


def post(yol, veri):
    r = urllib.request.Request(URL + yol, data=json.dumps(veri).encode(),
                               headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=3) as f:
        return f.read()


def cubuk(thr=0.0, pit=0.0, rol=0.0, yaw=0.0):
    post("/api/manuel", {"throttle": thr, "pitch": pit, "roll": rol, "yaw": yaw})


def yaw_oku():
    """Aracin burun acisini API'den okur. Bulamazsa None."""
    try:
        with urllib.request.urlopen(URL + "/api/telemetry", timeout=1.0) as f:
            d = json.loads(f.read())
    except Exception:
        return None
    for kap in (d.get("drone"), (d.get("debug") or {}).get("drone_real"), d):
        if isinstance(kap, dict):
            for k in ("yaw", "yaw_deg", "heading", "hdg"):
                if k in kap:
                    try:
                        return float(kap[k])
                    except Exception:
                        pass
    return None


def adim(ad, sure, yaw_topla=False, **k):
    print("  %-20s %.1f s  %s" % (ad, sure, k), flush=True)
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < sure:
        cubuk(**k)
        if yaw_topla:
            y = yaw_oku()
            if y is not None:
                yaw_ornek.append((time.perf_counter(), y))
        time.sleep(0.05)
    cizelge.append((ad, t0, time.perf_counter()))
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < 2.0:
        cubuk()
        time.sleep(0.05)


def iz_oku():
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
            return (t[a], np.asarray(d["dx_m"], float)[a],
                    np.asarray(d["dy_m"], float)[a],
                    np.asarray(d["dz_m"], float)[a])
    return None


def main():
    print("=" * 72)
    print("ZARF OLCUM 2 - hiz vektoru donusu + burun yaw hizi")
    print("=" * 72)
    try:
        post("/api/command", {"cmd": "manuel_on"})
    except Exception as e:
        print("  !! arayuze baglanilamadi: %r" % e)
        return 1
    y0 = yaw_oku()
    print("  manuel mod ACIK   (API'den yaw okunabiliyor mu: %s)"
          % ("EVET" if y0 is not None else "HAYIR"))
    print("")
    try:
        adim("ileri_hizlan", 4.0, pit=1.0)
        adim("hizli_roll", 4.0, pit=1.0, rol=1.0)
        adim("yaw_yerinde", 4.0, yaw_topla=True, yaw=1.0)
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
    print("  komutlar bitti. Iz kaydi bekleniyor...")
    time.sleep(8.0)

    r = iz_oku()
    if r is None:
        print("  !! iz kaydi yok")
        return 1
    t, x, y, z = r

    print("")
    print("=" * 72)
    print("SONUC")
    print("=" * 72)
    for ad, t0, t1 in cizelge:
        m = (t >= t0 + 0.5) & (t <= t1)
        if m.sum() < 8:
            print("  %-20s (yetersiz ornek: %d)" % (ad, int(m.sum())))
            continue
        tt, xx, yy = t[m], x[m], y[m]
        W = 0.25
        ta = np.clip(tt - W / 2, tt[0], tt[-1])
        tb = np.clip(tt + W / 2, tt[0], tt[-1])
        dt = np.maximum(tb - ta, 1e-9)

        def d(v):
            return (np.interp(tb, tt, v) - np.interp(ta, tt, v)) / dt

        vx, vy = d(xx), d(yy)
        V = np.hypot(vx, vy)
        psi = np.unwrap(np.arctan2(vy, vx))
        om = np.abs(np.degrees((np.interp(tb, tt, psi)
                                - np.interp(ta, tt, psi)) / dt))
        # hiz yeterince buyukse donus anlamli
        g = V > 5.0
        print("  %-20s n=%-4d V %.1f-%.1f m/s" % (ad, int(m.sum()), V.min(), V.max()))
        if g.sum() > 5:
            print("      hiz vektoru donusu: medyan %.1f  %%95 %.1f  max %.1f derece/s"
                  % (np.median(om[g]), np.percentile(om[g], 95), om[g].max()))
            print("      yanal ivme        : max %.2f m/s²"
                  % np.hypot(d(vx), d(vy)).max())
        else:
            print("      (hiz < 5 m/s, donus olcumu anlamsiz)")

    if len(yaw_ornek) > 4:
        ty = np.array([a for a, _ in yaw_ornek])
        yy_ = np.unwrap(np.radians([b for _, b in yaw_ornek]))
        w = np.degrees(np.abs(np.diff(yy_) / np.maximum(np.diff(ty), 1e-6)))
        w = w[np.isfinite(w) & (w < 2000)]
        if w.size:
            print("")
            print("  BURUN (yaw) HIZI: %d ornek, medyan %.0f  max %.0f derece/s"
                  % (w.size, np.median(w), w.max()))
    else:
        print("")
        print("  BURUN (yaw) HIZI: API yaw vermedi -> OLCULEMEDI")

    print("")
    print("  ! MANUEL MOD ACIK KALDI - arayuzden kapat")
    return 0


if __name__ == "__main__":
    sys.exit(main())

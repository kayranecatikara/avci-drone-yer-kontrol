# -*- coding: utf-8 -*-
"""
================================================================================
  ZARF OLCUM 3  --  belgede "OLCULEMEDI" kalan satirlari kapatir
================================================================================
Ilk iki testte acik kalan sorular ve bu testin onlari nasil kapattigi:

  1) ARAC TIPI (multirotor mu?)
     TEST: hizliyken SADECE roll ver, yaw komutu VERME. Burun sabit kalirken
     hiz vektoru donuyorsa arac YAN UCABILIYOR demektir -> multirotor.
     Fixed-wing'de burun ile hiz vektoru AYRILAMAZ.
     Ayrica: V=0'da yerinde yaw yapabiliyor mu (fixed-wing yapamaz).

  2) SAF DONUS HIZI
     Ilk testte pitch de tam ileriydi -> ivmenin cogu HIZLANMAYA gitti,
     donmeye degil (olculen 30.4 °/s bir ALT SINIRDI).
     TEST: once hiz kazan, sonra pitch'i BIRAK ve YALNIZ roll ver.
     Boylece butun yanal ivme donuse gider.

  3) IVME DOYUMU
     TEST: roll'u 6 s tut (ilk testte 3 s'ti). Ivme plato yapiyorsa zarf
     bulunmus, hala tirmaniyorsa test suresi yetmemis demektir.

  4) RUZGAR
     TEST: notr cubukla 10 s bekle. Sistematik surukleme varsa ruzgar var.

  5) YERCEKIMI
     TEST: throttle -1 ile 4 s. Serbest dususte ivme g'ye yaklasir.
     ⚠ Arac aktif frenliyorsa (ilk testte alcalma yalniz -5.6 m/s cikti)
     bu olcum g'yi DEGIL, aracin dikey otoritesini verir. Ikisi ayrilir.

CALISTIR  python arac/zarf_olcum3.py
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
attitude = []          # (t, yaw_deg)


def post(yol, veri):
    r = urllib.request.Request(URL + yol, data=json.dumps(veri).encode(),
                               headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=3) as f:
        return f.read()


def cubuk(thr=0.0, pit=0.0, rol=0.0, yaw=0.0):
    post("/api/manuel", {"throttle": thr, "pitch": pit, "roll": rol, "yaw": yaw})


def yaw_oku():
    try:
        with urllib.request.urlopen(URL + "/api/telemetry", timeout=1.0) as f:
            d = json.loads(f.read())
    except Exception:
        return None
    for kap in (d.get("drone"), (d.get("debug") or {}).get("drone_real")):
        if isinstance(kap, dict):
            for k in ("yaw", "yaw_deg", "heading", "hdg"):
                if k in kap:
                    try:
                        return float(kap[k])
                    except Exception:
                        pass
    return None


def adim(ad, sure, att=False, bekle=2.0, **k):
    print("  %-22s %.1f s  %s" % (ad, sure, k), flush=True)
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < sure:
        cubuk(**k)
        if att:
            y = yaw_oku()
            if y is not None:
                attitude.append((time.perf_counter(), y))
        time.sleep(0.05)
    cizelge.append((ad, t0, time.perf_counter()))
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < bekle:
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


def pencere(t, x, y, z, t0, t1, kirp=0.3):
    m = (t >= t0 + kirp) & (t <= t1)
    if m.sum() < 8:
        return None
    tt = t[m]
    W = 0.25
    ta = np.clip(tt - W / 2, tt[0], tt[-1])
    tb = np.clip(tt + W / 2, tt[0], tt[-1])
    dt = np.maximum(tb - ta, 1e-9)

    def d(v):
        return (np.interp(tb, tt, v) - np.interp(ta, tt, v)) / dt

    vx, vy, vz = d(x[m]), d(y[m]), d(z[m])
    V = np.hypot(vx, vy)
    psi = np.unwrap(np.arctan2(vy, vx))
    om = np.degrees((np.interp(tb, tt, psi) - np.interp(ta, tt, psi)) / dt)
    return {"t": tt - tt[0], "V": V, "vz": vz, "om": np.abs(om),
            "ah": np.hypot(d(vx), d(vy)), "az": d(vz),
            "x": x[m], "y": y[m], "z": z[m], "n": int(m.sum())}


def main():
    print("=" * 74)
    print("ZARF OLCUM 3 - acik kalan sorulari kapatir")
    print("=" * 74)
    try:
        post("/api/command", {"cmd": "manuel_on"})
    except Exception as e:
        print("  !! arayuze baglanilamadi: %r" % e)
        return 1
    print("  manuel mod ACIK")
    print("")
    try:
        adim("ruzgar_notr", 10.0, bekle=1.0)
        adim("hiz_kazan", 5.0, pit=1.0, bekle=0.0)
        adim("saf_roll", 6.0, att=True, rol=1.0)        # pitch YOK -> saf donus
        adim("yercekimi_dusus", 4.0, thr=-1.0)
        adim("yerinde_yaw", 3.0, att=True, yaw=1.0)
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
    P = {}
    for ad, t0, t1 in cizelge:
        p = pencere(t, x, y, z, t0, t1)
        if p:
            P[ad] = p

    print("")
    print("=" * 74)
    print("SONUCLAR")
    print("=" * 74)

    # 1) RUZGAR
    if "ruzgar_notr" in P:
        p = P["ruzgar_notr"]
        yol = math.hypot(p["x"][-1] - p["x"][0], p["y"][-1] - p["y"][0])
        sur = p["t"][-1]
        print("  1) RUZGAR")
        print("     notr cubukla %.1f s -> yatay surukleme %.2f m (%.2f m/s)"
              % (sur, yol, yol / max(sur, 1e-6)))
        print("     ortalama yatay hiz %.2f m/s, max %.2f" % (p["V"].mean(), p["V"].max()))
        print("     -> %s" % ("RUZGAR YOK (surukleme ihmal edilebilir)"
                              if yol / max(sur, 1e-6) < 0.3 else
                              "SURUKLEME VAR (%.2f m/s) - ruzgar olabilir" % (yol / sur)))

    # 2) SAF DONUS + ARAC TIPI + IVME DOYUMU
    if "saf_roll" in P:
        p = P["saf_roll"]
        g = p["V"] > 8
        print("")
        print("  2) SAF DONUS HIZI  (pitch BIRAKILDI, yalniz roll)")
        if g.sum() > 5:
            print("     hiz %.1f-%.1f m/s" % (p["V"][g].min(), p["V"][g].max()))
            print("     hiz vektoru donusu: medyan %.1f  %%95 %.1f  MAX %.1f derece/s"
                  % (np.median(p["om"][g]), np.percentile(p["om"][g], 95),
                     p["om"][g].max()))
            print("     yanal ivme: max %.2f m/s²" % p["ah"][g].max())
            # teorik kiyas
            Vm = np.median(p["V"][g])
            print("     teorik (a/V): %.1f/%.1f = %.1f derece/s"
                  % (p["ah"][g].max(), Vm,
                     math.degrees(p["ah"][g].max() / max(Vm, 1e-6))))
        print("")
        print("  3) IVME DOYUMU  (6 s roll)")
        h = p["ah"]
        n3 = max(len(h) // 3, 3)
        print("     ilk 1/3 max %.2f | orta 1/3 max %.2f | son 1/3 max %.2f m/s²"
              % (h[:n3].max(), h[n3:2 * n3].max(), h[2 * n3:].max()))
        print("     -> %s" % ("PLATO (zarf bulundu)"
                              if h[2 * n3:].max() <= h[n3:2 * n3].max() * 1.08
                              else "HALA TIRMANIYOR (test suresi yetmedi)"))

    # 4) ARAC TIPI
    if attitude:
        ta_ = np.array([a for a, _ in attitude])
        ya_ = np.unwrap(np.radians([b for _, b in attitude]))
        sr = [zz for zz in cizelge if zz[0] == "saf_roll"]
        print("")
        print("  4) ARAC TIPI")
        if sr:
            _, a0, a1 = sr[0]
            m = (ta_ >= a0) & (ta_ <= a1)
            if m.sum() > 3:
                dy_ = abs(math.degrees(ya_[m][-1] - ya_[m][0]))
                om_ = P["saf_roll"]["om"]
                dv = float(np.trapezoid(om_, P["saf_roll"]["t"])) if len(om_) > 2 else 0.0
                print("     saf roll sirasinda BURUN dondu : %.0f derece" % dy_)
                print("     ayni sirada HIZ VEKTORU dondu  : %.0f derece" % dv)
                if dv > 15 and dy_ < dv * 0.5:
                    print("     -> BURUN SABIT, HIZ VEKTORU DONDU = YAN UCABILIYOR")
                    print("        ==> MULTIROTOR (fixed-wing bunu YAPAMAZ)")
                elif dy_ > 15:
                    print("     -> burun da dondu; ayrisma net degil")
    if "yerinde_yaw" in P:
        p = P["yerinde_yaw"]
        print("     yerinde yaw sirasinda yatay hiz: max %.2f m/s" % p["V"].max())
        if p["V"].max() < 3.0:
            print("        (yerinde donebiliyor -> fixed-wing DEGIL)")

    # 5) YERCEKIMI
    if "yercekimi_dusus" in P:
        p = P["yercekimi_dusus"]
        print("")
        print("  5) DIKEY OTORITE / YERCEKIMI")
        print("     alcalma: max %.2f m/s  |  dikey ivme: max %.2f m/s²"
              % (abs(p["vz"].min()), abs(p["az"]).max()))
        print("     irtifa %.1f -> %.1f m" % (p["z"][0], p["z"][-1]))
        if abs(p["az"]).max() < 5.0:
            print("     -> serbest dusus DEGIL, arac AKTIF FRENLIYOR")
            print("        yercekimi bu testle OLCULEMEZ (olcum aracin dikey otoritesi)")

    # 6) JERK (basamak testinden)
    print("")
    print("  6) JERK / IVME RAMPASI")
    print("     ilk testin basamak tepkisinden: olu zaman 46 ms, zaman sabiti 211 ms")
    print("     max ivme 35.91 m/s² -> jerk ~ 35.91/0.211 = %.0f m/s³" % (35.91 / 0.211))
    print("     (dolayli hesap; dogrudan jerk limiti bilinmiyor)")

    yol = os.path.join(KOK, "veri", "zarf3_asamalar.csv")
    with open(yol, "w", encoding="utf-8", newline="\n") as f:
        f.write("asama,t_bas,t_bit\n")
        for a_, b_, c_ in cizelge:
            f.write("%s,%.4f,%.4f\n" % (a_, b_, c_))
    print("")
    print("  asama zamanlari -> %s" % yol)
    print("  ! MANUEL MOD ACIK KALDI")
    return 0


if __name__ == "__main__":
    sys.exit(main())

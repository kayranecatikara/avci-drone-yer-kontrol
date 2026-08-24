# -*- coding: utf-8 -*-
"""
================================================================================
  SICAK BASLANGIC -> ISKA?  Gorsel faza girerken cok mu hizli gidiyoruz?
================================================================================
KULLANICI TARIFI: "faza gectigimizde cok hizli gidip kaciriyor, her turlu
kaciriyor, tutmasi imkansiz."

MEKANIZMA: gorsel yasa hiz integralini devirde SICAK baslatiyor
    hiz_I = clamp( max(|ff|, |v_kendi| - 1.5), I_MIN, I_MAX )
`ff` GPS fazinin hedef hiz kestirimi. Kural YALNIZ YUKARI ceker -> `ff` sacma
derecede BUYUKSE ust akil kontrolu YOKTUR. Canli ornek:
    kaynak=ff, ff=37.4, kendi=21.0  -> sicak baslangic 24.0 (TAVAN)
oysa hedefin OLCULEN hizi 17.90 m/s. Yani faz 6+ m/s fazla hizla basliyor.

BU BETIK ONU OLCER: her gorsel faz epizodu icin
    * ilk karedeki hiz_I (sicak baslangic)
    * o epizotta ULASILAN EN YAKIN menzil
iliskisi. Sicak baslangic yuksekken CPA kotulesiyorsa hipotez DOGRULANIR.

⚠ MENZIL KAYNAGI: `menzil_m` yasanin KUTU BOYUTUNDAN kestirimidir ve
  +%32 yanli oldugu olculmustu. MUTLAK CPA icin kullanilamaz; burada yalniz
  epizotlar ARASI KIYAS icin kullaniliyor (yanlilik ortak). Mutlak sayi
  isteniyorsa truth ile birlestirilmeli (bkz. kamera_tilt_olc.py'deki duvar
  saati kapisi -- t_perf surec basina sifirlanir).

⚠ Epizot = bir bbox_ibvs_*.csv dosyasi (yasa her gorsel fazda yeni dosya acar).

KULLANIM
--------------------------------------------------------------------------------
    python arac/sicak_baslangic_etkisi.py
================================================================================
"""
import csv
import math
import os
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGD = os.path.join(KOK, "kopru", "gazebo_kaynak", "logs")
MIN_SATIR = 15


def f(s):
    try:
        v = float(s)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def y(v, q):
    if not v:
        return float("nan")
    s = sorted(v)
    return s[min(len(s) - 1, max(0, int(round(q * (len(s) - 1)))))]


def korelasyon(a, b):
    n = len(a)
    if n < 8:
        return float("nan")
    ma, mb = sum(a) / n, sum(b) / n
    pay = sum((x - ma) * (z - mb) for x, z in zip(a, b))
    va = math.sqrt(sum((x - ma) ** 2 for x in a))
    vb = math.sqrt(sum((z - mb) ** 2 for z in b))
    return pay / (va * vb) if va > 0 and vb > 0 else float("nan")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    epizot = []
    for e in os.scandir(LOGD):
        if not (e.name.startswith("bbox_ibvs_") and e.name.endswith(".csv")):
            continue
        try:
            R = list(csv.DictReader(open(e.path, newline="", encoding="utf-8",
                                         errors="replace")))
        except Exception:
            continue
        if len(R) < MIN_SATIR:
            continue
        ilk = None
        for r in R:                      # ilk GECERLI hiz_I
            v = f(r.get("hiz_I"))
            if v is not None:
                ilk = v
                break
        men = [f(r.get("menzil_m")) for r in R]
        men = [x for x in men if x is not None and 0.3 < x < 200.0]
        if ilk is None or len(men) < 5:
            continue
        # epizot suresi
        tv = [f(r.get("t")) for r in R]
        tv = [x for x in tv if x is not None]
        sure = (max(tv) - min(tv)) if len(tv) > 1 else 0.0
        epizot.append({"ad": e.name, "hiz_I": ilk, "cpa": min(men),
                       "bas_menzil": men[0], "n": len(R), "sure": sure})

    print("[SICAK] epizot: %d" % len(epizot))
    if len(epizot) < 20:
        print("[SICAK] yeterli epizot yok"); return 1

    h = [x["hiz_I"] for x in epizot]
    c = [x["cpa"] for x in epizot]
    print()
    print("  sicak baslangic hiz_I : ortanca %.2f | p10 %.2f | p90 %.2f m/s"
          % (y(h, .5), y(h, .1), y(h, .9)))
    print("  epizot CPA (kutudan)  : ortanca %.2f | p10 %.2f | p90 %.2f m"
          % (y(c, .5), y(c, .1), y(c, .9)))
    print("  epizot suresi         : ortanca %.1f s" % y([x["sure"] for x in epizot], .5))
    print()
    print("  korelasyon(hiz_I, CPA) = %+.3f   (+ = hizli baslamak ISKALATIYOR)"
          % korelasyon(h, c))

    print()
    print("  ── SICAK BASLANGIC BANDINA GORE ──")
    print("    %-16s %10s %10s %10s %7s" % ("hiz_I", "CPA ortanca", "CPA p10", "<3 m %", "n"))
    for lo, hi in ((0, 16), (16, 19), (19, 22), (22, 100)):
        alt = [x for x in epizot if lo <= x["hiz_I"] < hi]
        if len(alt) < 5:
            continue
        v = [x["cpa"] for x in alt]
        et = ("%g+ m/s" % lo) if hi > 90 else ("%g-%g m/s" % (lo, hi))
        print("    %-16s %10.2f %10.2f %9.0f%% %7d"
              % (et, y(v, .5), y(v, .1),
                 100.0 * sum(1 for z in v if z < 3.0) / len(v), len(alt)))

    # hedefin olculen hizi 17.90 m/s -> "fazla hizli" esigi
    HEDEF = 17.90
    hizli = [x for x in epizot if x["hiz_I"] > HEDEF + 3.0]
    normal = [x for x in epizot if x["hiz_I"] <= HEDEF + 3.0]
    print()
    print("  ── HEDEFIN HIZINA GORE (V_hedef = %.2f m/s) ──" % HEDEF)
    for ad, g in (("hiz_I > V+3 (fazla hizli)", hizli), ("hiz_I <= V+3", normal)):
        if len(g) < 5:
            print("    %-28s n=%d (yetersiz)" % (ad, len(g)))
            continue
        v = [x["cpa"] for x in g]
        print("    %-28s CPA ortanca %.2f m | <3 m %.0f%% | n=%d"
              % (ad, y(v, .5), 100.0 * sum(1 for z in v if z < 3.0) / len(v), len(g)))

    # baslangic menzili karistiriyor mu (uzaktan baslayan epizot dogal olarak
    # kotu CPA verir) -> ayni baslangic menzili bandinda tekrar bak
    print()
    print("  ── KARISTIRICI KONTROLU: ayni baslangic menzili bandinda ──")
    for lo, hi in ((0, 15), (15, 25), (25, 40)):
        alt = [x for x in epizot if lo <= x["bas_menzil"] < hi]
        if len(alt) < 10:
            continue
        hz = [x for x in alt if x["hiz_I"] > HEDEF + 3.0]
        nm = [x for x in alt if x["hiz_I"] <= HEDEF + 3.0]
        if len(hz) < 4 or len(nm) < 4:
            continue
        print("    baslangic %2d-%2d m: fazla hizli CPA %.2f (n=%d)  vs  normal %.2f (n=%d)"
              % (lo, hi, y([x["cpa"] for x in hz], .5), len(hz),
                 y([x["cpa"] for x in nm], .5), len(nm)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

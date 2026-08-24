# -*- coding: utf-8 -*-
"""
================================================================================
  DEVIR SICRAMASI A/B HUKMU  --  recete_gecis.json sonuclarini yorumsuz okur
================================================================================
NEDEN AYRI BETIK
--------------------------------------------------------------------------------
Bu deneyin iki tuzagi var ve ikisi de gozden kacabilir:

 1) MEKANIZMA KAPISI — bir kolun env'i verilmis olmasi, yamanin GERCEKTEN
    devreye girdigi anlamina GELMEZ (bayat sunucu / import anindaki env /
    yanlis anahtar adi). Once "yama calisti mi" dogrulanir, sonra sonuca
    bakilir. Kapi saglanmiyorsa o kol GECERSIZ sayilir.

 2) OLUMSUZ KONTROL — G5 dikey kazanci TEK BASINA artirir. Teshis dogruysa
    bu kol KOTULESMELI (tezgah: |dz| +155%). Kotulesmiyorsa teshis
    (yanlis denge noktasi) CURUR ve G4'un iyilesmesi baska bir sebeptendir.
    Bu betik onu ACIKCA yazar.

⚠ HANGI SINYAL SAYILIR (tekrar): "vurus" alani YAPISKAN MANDAL, "kilit_s"
   DOYMUS KARE sayaci. Gecerli sinyal: yeniden dogus (menzil sicramasi) ve
   CPA geometrisi.

KULLANIM
    python arac/gecis_hukum.py
================================================================================
"""
import os
import csv
import sys
import glob
import math
import argparse
from collections import defaultdict

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _f(r, k):
    v = (r.get(k) or "").strip()
    if v in ("", "None", "nan"):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def med(x):
    if not x:
        return float("nan")
    s = sorted(x)
    n = len(s)
    return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])


def cpa_olc(satirlar):
    """Yakin gecislerin CPA'si: menzil, ISARETLI dikey, yatay, temas."""
    mz = [_f(r, "menzil") for r in satirlar]
    ep, cur = [], []
    for i, m in enumerate(mz):
        if m is not None and m < 12:
            cur.append(i)
        elif cur:
            ep.append(cur)
            cur = []
    if cur:
        ep.append(cur)
    cpa, dz, dh, vis = [], [], [], 0
    for e in ep:
        j = min(e, key=lambda i: mz[i] if mz[i] is not None else 9e9)
        m = mz[j]
        if m is None or m > 8:
            continue
        v = _f(satirlar[j], "irt_fark")
        if v is None:
            continue
        cpa.append(m)
        dz.append(v)                                  # + = BIZ USTTE
        dh.append(math.sqrt(max(m * m - v * v, 0.0)))
        vis += 1 if (satirlar[j].get("faz") or "") == "VISUAL" else 0
    temas = sum(1 for i in range(1, len(satirlar))
                if mz[i - 1] is not None and mz[i] is not None
                and mz[i - 1] < 8 and mz[i] - mz[i - 1] > 25)
    return cpa, dz, dh, vis, temas


def _ayar_pencereleri():
    """kampanya.log'dan ayar -> (baslangic, bitis) duvar saati araliklari.

    ⚠ Mekanizma kapisi AYAR BAZINDA olculmeli. Topluca bakilirsa taban
    kolunun kareleri kapali kolun kanitiymis gibi gorunur ve "kapi
    calismadi" diye YANLIS hukum verilir.
    """
    import re
    import time
    kl = os.path.join(KOK, "veri", "gece", "kampanya.log")
    if not os.path.exists(kl):
        return {}
    bugun = time.strftime("%Y-%m-%d")
    pen = {}
    ad = None
    t0 = None
    for satir in open(kl, encoding="utf-8", errors="replace"):
        m = re.match(r"^(\d\d):(\d\d):(\d\d)\s+AYAR\s+(\S+)", satir)
        if not m:
            continue
        try:
            ts = time.mktime(time.strptime(
                "%s %s:%s:%s" % (bugun, m.group(1), m.group(2), m.group(3)),
                "%Y-%m-%d %H:%M:%S"))
        except ValueError:
            continue
        if ad is not None and t0 is not None:
            pen[ad] = (t0, ts)
        ad = m.group(4)
        t0 = ts
    if ad is not None and t0 is not None:
        pen[ad] = (t0, t0 + 10 ** 9)
    return pen


def mekanizma_kapisi(ayar, pencere):
    """Kolun yamasi GERCEKTEN devreye girdi mi? -- YALNIZ o ayarin
    zaman penceresinde yazilmis bbox_ibvs loglarina bakar."""
    yol = os.path.join(KOK, "kopru", "gazebo_kaynak", "logs")
    if not pencere:
        return 0, 0
    t0, t1 = pencere
    sapan = 0
    top = 0
    for y in glob.glob(os.path.join(yol, "bbox_ibvs_*.csv")):
        try:
            m = os.path.getmtime(y)
        except OSError:
            continue
        if not (t0 - 5 <= m <= t1 + 60):
            continue
        try:
            with open(y, encoding="utf-8", errors="replace") as f:
                for r in csv.DictReader(f):
                    c = _f(r, "cy_nisan")
                    if c is None:
                        continue
                    top += 1
                    if abs(c - 301.0) > 0.5:
                        sapan += 1
        except OSError:
            continue
    return sapan, top


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iz", default="")
    a = ap.parse_args()
    yollar = ([a.iz] if a.iz else
              sorted(glob.glob(os.path.join(KOK, "veri", "gece",
                                            "kampanya_iz_*.csv")),
                     key=os.path.getmtime)[-2:])
    grup = defaultdict(list)
    for y in yollar:
        try:
            with open(y, encoding="utf-8", errors="replace") as f:
                for r in csv.DictReader(f):
                    ad = r.get("ayar", "?")
                    if ad.startswith("G"):
                        grup[ad].append(r)
        except OSError:
            continue
    if not grup:
        print("G* ayari bulunamadi -- kampanya henuz baslamamis olabilir")
        return

    print("=" * 84)
    print("  DEVIR SICRAMASI A/B HUKMU")
    print("  ⚠ ISARETLI dikey:  + = BIZ USTTE,  - = BIZ ALTTA")
    print("=" * 84)
    print("%-20s %6s %6s %7s %8s %7s %7s %6s %6s %5s" % (
        "AYAR", "dk", "CPA n", "|dz|", "dz", "yatay", "CPA med",
        "<2m%", "<3m%", "temas"))
    print("-" * 92)

    S = {}
    for ad in sorted(grup):
        R = grup[ad]
        if len(R) < 100:
            continue
        t = [x for x in (_f(r, "t") for r in R) if x is not None]
        dk = (max(t) - min(t)) / 60.0 if len(t) > 1 else 0.0
        cpa, dz, dh, vis, tem = cpa_olc(R)
        if not dz:
            print("%-22s %6.1f   (yakin gecis yok)  temas %d" % (ad[:22], dk, tem))
            continue
        # ⚠ VURUS SAYISI ZAYIF SINYAL (12 dk'da 0-2). CPA DAGILIMI cok daha
        #   guclu: 44-51 gecisten hesaplanir. Nihai hukum buna dayanmali.
        alt2 = 100.0 * sum(1 for c in cpa if c < 2.0) / len(cpa)
        alt3 = 100.0 * sum(1 for c in cpa if c < 3.0) / len(cpa)
        S[ad] = (dk, len(dz), med([abs(x) for x in dz]), med(dz), med(dh),
                 min(cpa), tem, med(cpa), alt2, alt3)
        print("%-20s %6.1f %6d %7.2f %+8.2f %7.2f %7.2f %5.0f%% %5.0f%% %5d" % (
            ad[:20], dk, len(dz), med([abs(x) for x in dz]), med(dz),
            med(dh), med(cpa), alt2, alt3, tem))

    print()
    pen = _ayar_pencereleri()
    print("★ MEKANIZMA KAPISI -- AYAR BAZINDA (cy_nisan 301'den sapiyor mu)")
    print("   %-24s %9s %9s   hukum" % ("ayar", "sapan", "toplam"))
    UFUK = ("G1_ufuk", "G3_ufuk_hiz", "G4_ufuk_hiz_kvz", "G6_ufuk2_gokyuzu")
    for ad in sorted(S):
        kok = ad.split("#")[0]
        sapan, top = mekanizma_kapisi(kok, pen.get(ad) or pen.get(kok))
        bekle = any(kok.startswith(u) for u in UFUK)
        if not top:
            h = "log yok"
        elif bekle and sapan == 0:
            h = "✗ GECERSIZ -- kapi ACILMAMIS"
        elif bekle:
            h = "✓ kapi calisti (%%%.0f)" % (100.0 * sapan / top)
        elif sapan:
            h = "⚠ kapali olmali ama SAPMA VAR"
        else:
            h = "✓ beklendigi gibi kapali"
        print("   %-24s %9d %9d   %s" % (kok[:24], sapan, top, h))

    # ── OLUMSUZ KONTROL ────────────────────────────────────────────────
    t0 = S.get("G0_taban#t1")
    g5 = S.get("G5_kvz_tek_KONTROL#t1")
    g4 = S.get("G4_ufuk_hiz_kvz#t1")
    print()
    print("★ OLUMSUZ KONTROL (G5: dikey kazanc TEK BASINA)")
    if not (t0 and g5):
        print("   veri yok (kollar henuz tamamlanmadi)")
    else:
        # ⚠ 2026-08-17: HUKUM TEK OLCUYE BAKMAMALI. Ilk surum yalniz |dz|'ye
        #   bakiyordu; G5'te fark +0.15 m ile esikte kalinca "dogrulanmadi"
        #   yazdi -- oysa ISARETLI sapma ve TUM yakinlik olculeri kararli
        #   bicimde kotulesmisti. Dar olcut yanlis hukum verir.
        oy = 0
        print("   %-22s %8s %8s %8s" % ("olcu", "taban", "G5", "yon"))
        for ad, i, buyuk_kotu in (("|dz| (m)", 2, True), ("dz isaretli (m)", 3, True),
                                  ("CPA medyan (m)", 7, True), ("<2 m orani (%)", 8, False),
                                  ("<3 m orani (%)", 9, False)):
            kotu = (g5[i] > t0[i]) if buyuk_kotu else (g5[i] < t0[i])
            iyi = (g5[i] < t0[i]) if buyuk_kotu else (g5[i] > t0[i])
            oy += 1 if kotu else (-1 if iyi else 0)
            print("   %-22s %8.2f %8.2f %8s" % (
                ad, t0[i], g5[i], "KOTU" if kotu else ("iyi" if iyi else "esit")))
        print("   temas %d -> %d" % (t0[6], g5[6]))
        print()
        if oy >= 3:
            print("   ✓ BEKLENDIGI GIBI KOTULESTI (%d/5 olcu) -> teshis"
                  " (yanlis denge noktasi) AYAKTA" % oy)
        elif oy <= -3:
            print("   ✗✗ IYILESTI -> TESHIS CURUDU. 'yanlis denge noktasi'")
            print("      aciklamasi YENIDEN DUSUNULMELI.")
        else:
            print("   ~ karisik (%+d) -> teshis DOGRULANMADI" % oy)
    if t0 and g4:
        print()
        print("★ ANA ADAY (G4: ufuk + hiz sicak + K_VZ)")
        print("   |dz|   %.2f -> %.2f m  (%+.0f%%)"
              % (t0[2], g4[2], 100 * (g4[2] - t0[2]) / max(t0[2], 1e-6)))
        print("   CPA med %.2f -> %.2f m | <2 m %%%.0f -> %%%.0f | <3 m %%%.0f -> %%%.0f"
              % (t0[7], g4[7], t0[8], g4[8], t0[9], g4[9]))
        print("   temas %d -> %d   (⚠ zayif sinyal, CPA dagilimina bak)"
              % (t0[6], g4[6]))
    print()
    print("⚠ Kollarin hicbiri 10 dk'dan kisaysa hukum verme -- kampanya suruyor.")


if __name__ == "__main__":
    main()

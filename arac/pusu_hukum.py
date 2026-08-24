# -*- coding: utf-8 -*-
"""
================================================================================
  PUSU HUKMU  --  hedefin kapali pistinde bulusma noktasi denemesi
================================================================================
NE SINANIYOR
--------------------------------------------------------------------------------
Vurusu KESME GEOMETRISI uretir (olculdu, 2026-08-17/18):
    aspect 60-90 deg  -> CPA<1.5 m orani %55   (83 vurusun %81'i aspect<90)
    aspect 150-180    -> %9
Bugun yaklasmalarin **%54'u kuyrukta** bitiyor, yalniz %4'u en iyi bantta --
cunku GPS istasyonu tasarim geregi hedefin ARKASINA konuyor.

Hedef KAPALI oval uculuyor (periyot 29.60 s, p10=p90=29.60) ve tekrar
kestiricisi ufuktan BAGIMSIZ 0.62-0.66 m hata veriyor. O yuzden bulusma
noktasi SECILEBILIR. Uretim fonksiyonu kayitli veride: en iyi bantta %99
(sinirsiz) / %55 (40 m sapma siniriyla).

⚠⚠ SAPMA SINIRI NEDEN VAR: sinirsiz secim istasyonu hedefin simdiki
yerinden medyan 130.6 m uzaga koyuyordu; hedefi medyan 29 m'den goruyoruz
ve tespit 40 m otesinde dusuyor -> hedef kaybi -> devir olcutu (10 ardisik
kare) hic dolmaz -> SISTEM COKER. Ucmadan once olculdu ve 40 m'ye baglandi.

⚠⚠ MEKANIZMA KAPISI -- GECMEYEN KOLUN SONUCU OKUNMAZ
--------------------------------------------------------------------------------
  1. `pusu_aspect_deg` sutunu DOLU olmali (kapi calisti mi?)
  2. degeri 60-90 bandinda olmali (dogru noktayi mi seciyor?)
  3. `pusu_sapma_m` sinirin altinda olmali (istasyon gorus menzilinde mi?)
  4. `pusu_periyot_s` ~29.6 olmali (pisti dogru mu cozdu?)
Taban kollarinda bu sutunlar BOS olmali; doluysa kapi sizmis demektir.

⚠ ASIL OLCUT: CPA'daki ASPECT. Mudahale dogrudan onu hedefliyor. CPA
mesafesi ikincil -- geometri duzelse bile mesafe gec duzelebilir.

⚠ OLUMSUZ KONTROL (P2): periyot %20 kasten bozulur. O kol KOTULESMELI;
kotulesmiyorsa kazanc kestirimden GELMIYOR ve pusu fikri COKER.

⚠ OLCUM TUZAKLARI (arac/kol_hukum.py basligiyla ayni): menzil<0.5 /
d_hiz<=0.5 satirlari gecersiz; `t` monotonic ve sunucu yeniden baslayinca
SIFIRLANIR -> anahtar (DOSYA, AYAR).

KULLANIM
    python arac/pusu_hukum.py
================================================================================
"""
import os
import csv
import sys
import glob
import math
import argparse

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gecerlilik import temizle as _donmus_temizle  # noqa: E402

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _f(r, k):
    v = (r.get(k) or "").strip()
    if v in ("", "None", "nan"):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def gecerli(r):
    m, h = _f(r, "menzil"), _f(r, "d_hiz")
    return m is not None and m >= 0.5 and h is not None and h > 0.5


def kurs(R, i, geri=5):
    j = max(0, i - geri)
    ax, ay = _f(R[j], "hx"), _f(R[j], "hy")
    bx, by = _f(R[i], "hx"), _f(R[i], "hy")
    if None in (ax, ay, bx, by):
        return None
    dx, dy = bx - ax, by - ay
    n = math.hypot(dx, dy)
    return (dx / n, dy / n) if n >= 0.3 else None


def aspect(R, i):
    u = kurs(R, i)
    if u is None:
        return None
    hx, hy = _f(R[i], "hx"), _f(R[i], "hy")
    dx, dy = _f(R[i], "dx"), _f(R[i], "dy")
    if None in (hx, hy, dx, dy):
        return None
    rx, ry = dx - hx, dy - hy
    n = math.hypot(rx, ry)
    if n < 0.5:
        return None
    return math.degrees(math.acos(max(-1.0, min(1.0, (rx * u[0] + ry * u[1]) / n))))


def topla(on="P", dosya=2):
    """(ayar) -> {'cpa': [(menzil, aspect, |dz|)], 'mek': [(tgo, asp, sapma, per)]}"""
    G = {}
    for y in sorted(glob.glob(os.path.join(KOK, "veri", "gece",
                                           "kampanya_iz_*.csv")),
                    key=os.path.getmtime)[-dosya:]:
        with open(y, encoding="utf-8", errors="replace") as fh:
            for r in csv.DictReader(fh):
                ad = r.get("ayar", "?")
                if on and not ad.startswith(on):
                    continue
                G.setdefault((os.path.basename(y), ad), []).append(r)
    OUT = {}
    for (dos, ad), R in G.items():
        R = _donmus_temizle(R)          # ⚠ DONMUS telemetri (bkz. arac/gecerlilik.py)
        R.sort(key=lambda r: (_f(r, "t") or 0.0))
        d = OUT.setdefault(ad, {"cpa": [], "mek": []})
        ep = None
        sont = None
        for i, r in enumerate(R):
            t = _f(r, "t")
            if t is None:
                continue
            if sont is not None and (t < sont or t - sont > 3.0):
                ep = None
            sont = t
            if not gecerli(r):
                continue
            m = _f(r, "menzil")
            if m < 18.0:
                if ep is None:
                    ep = []
                ep.append(i)
            elif ep is not None and m > 24.0:
                if len(ep) >= 8:
                    j = min(ep, key=lambda k: _f(R[k], "menzil") or 9e9)
                    d["cpa"].append((_f(R[j], "menzil"), aspect(R, j),
                                     abs(_f(R[j], "irt_fark") or 0.0)))
                ep = None
        if ep and len(ep) >= 8:
            j = min(ep, key=lambda k: _f(R[k], "menzil") or 9e9)
            d["cpa"].append((_f(R[j], "menzil"), aspect(R, j),
                             abs(_f(R[j], "irt_fark") or 0.0)))
    return OUT


def mekanizma_oku(on="P"):
    """⚠ PUSU sutunlari `kampanya_iz`de DEGIL, GPS yasasinin KENDI logunda
    (`kopru/gazebo_kaynak/logs/gps_guidance_*.csv`). Ilk surum yanlis dosyayi
    okuyup "KAPI HIC CALISMADI" diyordu -- oysa kapi calisiyordu.
    Kollar dosya mtime'i ile kampanya.log penceresinden eslenir."""
    import re
    import time as _t
    L = os.path.join(KOK, "veri", "gece", "kampanya.log")
    if not os.path.exists(L):
        return {}
    sat = open(L, encoding="utf-8", errors="replace").readlines()
    bas = max((i for i, s in enumerate(sat) if "KAMPANYA basladi" in s),
              default=0)
    bugun = _t.strftime("%Y-%m-%d")
    olay = []
    for s in sat[bas:]:
        m = re.match(r"^(\d{2}):(\d{2}):(\d{2})\s+AYAR\s+(\S+)", s)
        if m:
            tt = _t.mktime(_t.strptime("%s %s:%s:%s" % (bugun, m.group(1),
                                       m.group(2), m.group(3)),
                                       "%Y-%m-%d %H:%M:%S"))
            olay.append((tt, m.group(4).split("#")[0]))
    pen = [(a, t, (olay[i + 1][0] if i + 1 < len(olay) else t + 86400))
           for i, (t, a) in enumerate(olay)]
    OUT = {}
    for y in sorted(glob.glob(os.path.join(KOK, "kopru", "gazebo_kaynak",
                                           "logs", "gps_guidance_*.csv")),
                    key=os.path.getmtime)[-400:]:
        mt = os.path.getmtime(y)
        ad = None
        for a, t0, t1 in pen:
            if t0 <= mt < t1 + 60:
                ad = a
                break
        if ad is None or (on and not ad.startswith(on)):
            continue
        try:
            R = list(csv.DictReader(open(y, encoding="utf-8", errors="replace")))
        except OSError:
            continue
        d = OUT.setdefault(ad, [])
        for r in R:
            asp = _f(r, "pusu_aspect_deg")
            if asp is not None:
                d.append((_f(r, "pusu_tgo_s"), asp, _f(r, "pusu_sapma_m"),
                          _f(r, "pusu_periyot_s")))
    return OUT


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--on", default="P")
    ap.add_argument("--dosya", type=int, default=2)
    a = ap.parse_args()
    D = topla(a.on, a.dosya)
    MEK = mekanizma_oku(a.on)
    for ad, v in MEK.items():
        D.setdefault(ad + "#t1", {"cpa": [], "mek": []})
        for k in list(D):
            if k.split("#")[0] == ad:
                D[k]["mek"] = v
    if not D:
        print("veri yok")
        return

    print("=" * 94)
    print("  PUSU HUKMU")
    print("=" * 94)
    print("\n[1] MEKANIZMA KAPISI  --  kapi gercekten calisti mi?")
    print("-" * 94)
    print("%-26s %8s %11s %12s %11s %11s"
          % ("AYAR", "n", "aspect med", "60-90 bandi", "sapma med", "periyot"))
    kapi = {}
    for ad in sorted(D):
        v = D[ad]["mek"]
        taban = "taban" in ad.lower()
        if not v:
            kapi[ad] = taban          # tabanda BOS olmasi DOGRU
            print("%-26s %8d %11s %12s %11s %11s  %s"
                  % (ad[:26], 0, "-", "-", "-", "-",
                     "GECTI (taban, bos)" if taban else "!! KAPI HIC CALISMADI"))
            continue
        asp = np.array([x[1] for x in v])
        sap = [x[2] for x in v if x[2] is not None]
        per = [x[3] for x in v if x[3] is not None]
        bant = 100 * np.mean((asp >= 60) & (asp < 90))
        ok = (not taban) and bant >= 40.0
        kapi[ad] = ok
        print("%-26s %8d %11.0f %11.0f%% %11s %11s  %s"
              % (ad[:26], len(v), np.median(asp), bant,
                 ("%.0f" % np.median(sap)) if sap else "-",
                 ("%.1f" % np.median(per)) if per else "-",
                 "GECTI" if ok else ("!! TABANDA DOLU -- SIZINTI" if taban
                                     else "!! BANT DISI")))

    print("\n[2] ASIL OLCUT: CPA'DAKI ASPECT  (mudahalenin hedefi)")
    print("-" * 94)
    print("%-26s %8s %11s %12s %12s %11s"
          % ("AYAR", "yaklasma", "aspect med", "60-90 (iyi)", "150+ (kuyruk)", "<90"))
    S = {}
    for ad in sorted(D):
        v = [x for x in D[ad]["cpa"] if x[1] is not None]
        if len(v) < 12:
            continue
        asp = np.array([x[1] for x in v])
        S[ad] = asp
        print("%-26s %8d %11.0f %11.0f%% %12.0f%% %10.0f%%"
              % (ad[:26], len(v), np.median(asp),
                 100 * np.mean((asp >= 60) & (asp < 90)),
                 100 * np.mean(asp >= 150), 100 * np.mean(asp < 90)))

    print("\n[3] SONUC: EN YAKIN GECIS")
    print("-" * 94)
    print("%-26s %8s %11s %10s %10s %11s"
          % ("AYAR", "yaklasma", "CPA medyan", "<1.5 m", "<1 m", "|dz|@CPA"))
    for ad in sorted(D):
        v = D[ad]["cpa"]
        if len(v) < 12:
            continue
        m = np.array([x[0] for x in v])
        z = np.array([x[2] for x in v])
        g = "" if kapi.get(ad, True) else "   !! KAPI GECMEDI -- OKUMA"
        print("%-26s %8d %11.2f %9.0f%% %9.0f%% %11.2f%s"
              % (ad[:26], len(v), np.median(m), 100 * np.mean(m < 1.5),
                 100 * np.mean(m < 1.0), np.median(z), g))

    print("\n  ⚠ GURULTU TABANI (10 taban cifti): CPA medyani 0.91 m /"
          " p90 1.46 m; <1.5m orani 10 / 17 puan; |dz|@CPA 0.144 / 0.339.")
    print("  ⚠ KARAR: P2 (bozuk periyot) KOTULESMEZSE kazanc kestirimden")
    print("     GELMIYOR demektir ve pusu fikri COKER -- P1 iyi cikmis olsa bile.")
    print()


if __name__ == "__main__":
    main()

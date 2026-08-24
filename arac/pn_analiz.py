# -*- coding: utf-8 -*-
"""
================================================================================
  PN ANALIZ  --  PN'li gorsel fazi uctuktan hemen sonra "oldu mu?" sorusuna
                 OLCUMLE cevap verir
================================================================================
NEDEN: simulator 357/480 vurus soyluyor. Oyunda olmazsa sebebi bilmemiz lazim,
"olmadi" demek yetmez. Bu betik uc soruyu ayirir:

  1) PN CALISTI MI?      pn_sapma_deg ~ 0 ise PN hic devreye girmemis demektir
                         (lam kestirimi bos, ya da faz hic acilmamis).
  2) lam SAGLIKLI MI?    |los_hiz_az| cok buyukse kestirim gurultuden besleniyor;
                         pn_ornek < 3 ise pencere hic dolmuyor (tespit seyrek).
  3) YAKINSADI MI?       menzil truth izden; en yakin gecis ve kapanma hizi.

CALISTIR
    python arac/pn_analiz.py                 en son kosuyu coz
    python arac/pn_analiz.py --sonra 13:14   bu saatten sonraki loglar
    python arac/pn_analiz.py --hepsi         PN'li tum kosulari ozetle
================================================================================
"""
import os
import sys
import csv
import glob
import math
import time
import argparse
import statistics as st

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IBVS_DIR = os.path.join(KOK, "kopru", "gazebo_kaynak", "logs")
IZ_DIR = os.path.join(KOK, "veri", "hedef_iz")


def _f(satir, ad, vars=None):
    try:
        d = satir.get(ad, "")
        return float(d) if d not in ("", None) else vars
    except (TypeError, ValueError):
        return vars


def oku(yol):
    with open(yol, newline="", encoding="utf-8", errors="replace") as f:
        return list(csv.DictReader(f))


def ibvs_loglari(sonra_ts=None):
    yl = sorted(glob.glob(os.path.join(IBVS_DIR, "bbox_ibvs_*.csv")),
                key=os.path.getmtime)
    if sonra_ts:
        yl = [y for y in yl if os.path.getmtime(y) >= sonra_ts]
    return yl


def son_iz():
    yl = sorted(glob.glob(os.path.join(IZ_DIR, "hedef_iz_*.csv")),
                key=os.path.getmtime)
    return yl[-1] if yl else None


# ══════════════════════════════════════════════════════════════════════════
def faz_coz(yol):
    """Bir bbox_ibvs CSV'sini ozetler. PN alanlari yoksa 'eski kosu' der."""
    s = oku(yol)
    if not s:
        return None
    pn_var = "pn_sapma_deg" in s[0]
    t = [_f(r, "t") for r in s if _f(r, "t") is not None]
    sure = (max(t) - min(t)) if len(t) > 1 else 0.0

    kutulu = [r for r in s if _f(r, "boyut") not in (None, 0.0)]
    sureklilik = len(kutulu) / max(len(s), 1)

    d = {"yol": os.path.basename(yol), "kare": len(s), "sure": sure,
         "sureklilik": sureklilik, "pn_var": pn_var}

    def dagilim(ad, kaynak=None):
        v = [_f(r, ad) for r in (kaynak or s)]
        v = [x for x in v if x is not None]
        return v

    boy = dagilim("boyut", kutulu)
    d["boyut_med"] = st.median(boy) if boy else 0.0
    d["boyut_max"] = max(boy) if boy else 0.0
    eps = [abs(x) for x in dagilim("eps_yaw_deg", kutulu)]
    d["eps_med"] = st.median(eps) if eps else 0.0
    d["eps_max"] = max(eps) if eps else 0.0

    if pn_var:
        sap = [_f(r, "pn_sapma_deg") for r in kutulu]
        sap = [x for x in sap if x is not None]
        d["sapma_med"] = st.median([abs(x) for x in sap]) if sap else 0.0
        d["sapma_p95"] = (sorted(abs(x) for x in sap)[int(.95 * len(sap))]
                          if sap else 0.0)
        orn = [_f(r, "pn_ornek") for r in kutulu]
        orn = [x for x in orn if x is not None]
        d["ornek_med"] = st.median(orn) if orn else 0.0
        d["ornek_yeter"] = (sum(1 for x in orn if x >= 3) / len(orn)) if orn else 0.0
        lam = [abs(_f(r, "los_hiz_az", 0.0) or 0.0) for r in kutulu]
        d["lam_med"] = st.median(lam) if lam else 0.0
        d["lam_p95"] = sorted(lam)[int(.95 * len(lam))] if lam else 0.0
        d["pn_n"] = _f(s[0], "pn_n", 0.0)
    return d


def menzil_coz(iz_yol, t0, t1):
    """Truth izden [t0,t1] araligindaki EN YAKIN mesafeyi ve kapanmayi cikarir."""
    if not iz_yol or not os.path.exists(iz_yol):
        return None
    en = None
    n = 0
    with open(iz_yol, newline="", encoding="utf-8", errors="replace") as f:
        for r in csv.DictReader(f):
            tm = _f(r, "t_mutlak")
            if tm is None or not (t0 <= tm <= t1):
                continue
            try:
                m = math.dist((float(r["hx_m"]), float(r["hy_m"]), float(r["hz_m"])),
                              (float(r["dx_m"]), float(r["dy_m"]), float(r["dz_m"])))
            except (KeyError, ValueError, TypeError):
                continue
            n += 1
            if en is None or m < en:
                en = m
    return None if not n else {"en_yakin": en, "ornek": n}


def yaz(d, iz_yol=None):
    print("  %s" % d["yol"])
    if not d["pn_var"]:
        print("     ESKI KOSU (PN alanlari yok) — kiyas icin tutuluyor")
    print("     sure %.2f s | %d kare | tespit surekliligi %%%.0f"
          % (d["sure"], d["kare"], 100 * d["sureklilik"]))
    print("     kutu medyan %.1f px (max %.1f) | |eps_yaw| medyan %.1f° (max %.0f°)"
          % (d["boyut_med"], d["boyut_max"], d["eps_med"], d["eps_max"]))
    if d["pn_var"]:
        print("     PN N=%.2f | sapma medyan %.1f° p95 %.1f° | lam medyan %.2f p95 %.2f rad/s"
              % (d["pn_n"], d["sapma_med"], d["sapma_p95"], d["lam_med"], d["lam_p95"]))
        print("     pencere ornek medyan %.0f | >=3 olan kare orani %%%.0f"
              % (d["ornek_med"], 100 * d["ornek_yeter"]))
        # ── TESHIS ──
        if d["sapma_med"] < 1.0:
            print("     !! PN DEVREDE DEGIL: sapma ~0. lam bos ya da faz cok kisa.")
        elif d["sapma_p95"] > 70.0:
            print("     !! SAPMA COK BUYUK: lam kestirimi gurultuden besleniyor olabilir.")
        else:
            print("     -> PN calisiyor (beklenen sapma bandi 5-45°).")
        if d["ornek_yeter"] < 0.5:
            print("     !! PENCERE DOLMUYOR: tespit cok seyrek, lam cogu karede 0.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sonra", default=None, help="SS:DD — bu saatten sonrakiler")
    ap.add_argument("--hepsi", action="store_true")
    ap.add_argument("--asgari-kare", type=int, default=8)
    a = ap.parse_args()

    ts = None
    if a.sonra:
        h, m = a.sonra.split(":")
        bg = time.localtime()
        ts = time.mktime((bg.tm_year, bg.tm_mon, bg.tm_mday, int(h), int(m), 0,
                          0, 0, -1))

    yl = ibvs_loglari(ts)
    if not yl:
        print("  bbox_ibvs logu yok — gorsel faz hic acilmamis.")
        print("  (arayuzde hedefi yakalayip 10 ust uste tespit gerekiyor)")
        return

    if not a.hepsi:
        yl = yl[-12:]

    print("=" * 74)
    print("  PN ANALIZ — %d gorsel faz" % len(yl))
    print("=" * 74)
    coz = []
    for y in yl:
        d = faz_coz(y)
        if d and d["kare"] >= a.asgari_kare:
            coz.append(d)
            yaz(d)
            print()
    if not coz:
        print("  Tum fazlar %d kareden kisa — faz SAVRULUYOR, guduum yasasina"
              % a.asgari_kare)
        print("  sira bile gelmiyor. Once devir mesafesi/boyut kapisi.")
        return

    pn = [d for d in coz if d["pn_var"]]
    print("-" * 74)
    print("  OZET")
    print("    faz sayisi           %d  (PN'li %d)" % (len(coz), len(pn)))
    print("    faz omru medyan      %.2f s" % st.median([d["sure"] for d in coz]))
    print("    tespit surekliligi   %%%.0f" % (100 * st.median([d["sureklilik"] for d in coz])))
    if pn:
        print("    PN sapma medyan      %.1f°" % st.median([d["sapma_med"] for d in pn]))
        print("    pencere yeterli      %%%.0f" % (100 * st.median([d["ornek_yeter"] for d in pn])))

    iz = son_iz()
    if iz:
        print("    truth iz             %s" % os.path.basename(iz))
        print("    (en yakin gecis icin: python arac/faz_gecis_analiz.py)")


if __name__ == "__main__":
    main()

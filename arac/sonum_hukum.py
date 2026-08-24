# -*- coding: utf-8 -*-
"""
================================================================================
  SEYIR DIKEY SONUMLEMESI  --  hukum betigi
================================================================================
NE SINANIYOR
--------------------------------------------------------------------------------
bbox_ibvs seyir/tutus dalinda dikey yasa SAF ORANSAL idi (sonumleme yok).
Terminal dalinda ayni sonumleme (K_VZ_D) VARDI. Devir menzili medyan 12.7 m,
terminal mandali cok daha yakinda kalkiyor -> devir sonrasi butun gecici
davranis sonumlemesiz dalda yasaniyordu.

OLCULEN ARIZA (2306 devir, G3 sonrasi): dz devirde -1.46 m -> +2.5..3 s'de
+0.41 m ASIM; gecislerin %69'u dogru irtifadan GECIP gidiyor; hata 1 m altina
ancak ~1.5 s'de iniyor (gorsel faz omru ~5 s). Asim %28 -> ikinci mertebe
tersinden sonumleme orani z ~= 0.375 (az sonumlu; ideal ~0.7).

⚠⚠ MEKANIZMA KAPISI -- BUNU GECMEYEN KOLUN SONUCU OKUNMAZ
--------------------------------------------------------------------------------
Sonumleme terimi:  sp_vz = (1+Kd)*K_VZ*V_NOM*eps  -  Kd*olc_vz
Yani `olc_vz` KATSAYISI tam olarak  -Kd  olmalidir; kapali kolda 0 cikmali.
Bu, "kapi gercekten devreye girdi mi" sorusunun DOGRUDAN cevabidir: ayar
adina ya da env'e GUVENMEZ, komutun kendisini olcer.

⚠ AYIRT EDICI OLUMSUZ KONTROL (S2): sonumleme terimi kazanci da (1+Kd) kati
buyutur. S2 kolu ayni DURGUN kazanci (K_VZ=0.8) sonumlemesiz uygular.
   S1 > S2  -> etki HIZ GERI BESLEMESINDEN (sonumleme gercekten calisiyor)
   S1 ~ S2  -> etki yalnizca kazanctan; sonumleme GEREKSIZ, geri al.

⚠ OLCUM TUZAKLARI (arac/kol_hukum.py basligindaki liste ile ayni):
  - menzil<0.5 / d_hiz<=0.5 satirlari GECERSIZ (bos telemetri)
  - kampanya_iz `t` = monotonic ve SUNUCU YENIDEN BASLAYINCA SIFIRLANIR
    -> anahtar (DOSYA, AYAR)
  - kareler.csv'de `ayar` sutunu YOK -> kollar kampanya.log'daki duvar
    saatinden pencerelenir

KULLANIM
    python arac/sonum_hukum.py
    python arac/sonum_hukum.py --on S --dosya 2
================================================================================
"""
import os
import re
import csv
import sys
import glob
import time
import math
import argparse

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gecerlilik import temizle as _donmus_temizle  # noqa: E402

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "kopru", "gazebo_kaynak"))


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


def med(x):
    return float(np.median(x)) if len(x) else float("nan")


# ── 1) KOL PENCERELERI (kampanya.log'dan, duvar saati) ──────────────────
def kol_pencereleri():
    """[(ayar, t_baslangic, t_bitis)] -- kareler.csv'yi kollara boler.

    ⚠⚠ HATA VE DUZELTMESI (2026-08-18) -- BU TUZAGA IKINCI KEZ DUSME:
    kampanya.log satirlari yalniz HH:MM:SS tasir, TARIH YOKTUR. Ilk surum
    her satira BUGUNUN tarihini veriyordu -> gunler onceki kampanyalarin
    kollari (R0_taban, B1_ff_koru, ...) bugune dusuyor, pencereler
    birbirine giriyor ve gercek kollar GOLGELENIYORDU.
    BELIRTI: mekanizma tablosu BOS cikar, ama veri yerinde durur --
    yani "kapi acilmamis" gibi gorunur, oysa OLCUM BOZUKTUR.
    DUZELTME: yalniz son "KAMPANYA basladi" satirindan sonrasi okunur;
    saat geriye giderse gun eklenir (gece yarisi gecisi).
    """
    yol = os.path.join(KOK, "veri", "gece", "kampanya.log")
    if not os.path.exists(yol):
        return []
    with open(yol, encoding="utf-8", errors="replace") as fh:
        satirlar = fh.readlines()
    bas = 0
    for i, s in enumerate(satirlar):
        if "KAMPANYA basladi" in s:
            bas = i
    bugun = time.strftime("%Y-%m-%d")
    olay = []
    onceki = None
    gun = 0
    for satir in satirlar[bas:]:
        m = re.match(r"^(\d{2}):(\d{2}):(\d{2})\s+AYAR\s+(\S+)", satir)
        if not m:
            continue
        hh, mm, ss, ad = m.groups()
        t = time.mktime(time.strptime("%s %s:%s:%s" % (bugun, hh, mm, ss),
                                      "%Y-%m-%d %H:%M:%S")) + gun * 86400
        if onceki is not None and t < onceki:          # gece yarisini gecti
            gun += 1
            t += 86400
        onceki = t
        olay.append((t, ad.split("#")[0]))
    out = []
    for i, (t, ad) in enumerate(olay):
        son = olay[i + 1][0] if i + 1 < len(olay) else t + 86400
        out.append((ad, t, son))
    return out


# ── 2) MEKANIZMA KAPISI ─────────────────────────────────────────────────
# ⚠ ILK SURUM BOZUKTU (2026-08-18): sp_vz'yi [cy, pitch, olc_vz] uzerine
#   regresyona sokup olc_vz katsayisini -Kd bekliyordum. TABAN kolunda bile
#   -0.427 cikti (0 olmaliydi): ham `cy` yasanin kullandigi eps DEGIL, ve
#   eksik vekil yuzunden olc_vz sahte negatif katsayi topluyor.
# DOGRU KAPI (asagidaki `mekanizma`): eps'i yasanin KENDI nisan_cy'siyle
#   birebir kurup, eps ~ 0 VE arac TIRMANIRKEN artigi olcuyoruz:
#       sp_vz = (1+Kd)*K_VZ*V_NOM*eps - Kd*vz_ned
#       eps~0'da  artik = sp_vz - K_VZ*V_NOM*eps  ~=  -Kd*vz_ned = +Kd*|vz|
#   Yani sonumleme aciksa artik POZITIF yone kayar (fren). Kapali kolda ~0.
#   ⚠ Kol basina K_VZ FARKLI olabilir (S2 = 0.8) -> her kol KENDI K_VZ'siyle
#     karsilastirilir, yoksa "kazanc" etkisi sonumleme sanilir.
# ⚠ Olculen buyukluk teorinin ~%40'i cikar: log 1.3 Hz, kontrol 20 Hz;
#   loglanan olc_vz o tikteki iris_vz'nin AYNISI degildir. YON guvenilir,
#   MUTLAK BUYUKLUK degil.
KOL_KVZ = {"S0_taban_a": 0.5, "S0_taban_b": 0.5, "S1_sonum06": 0.5,
           "S2_kazanc_TEK": 0.8, "S3_sonum10": 0.5}
KOL_KD = {"S0_taban_a": 0.0, "S0_taban_b": 0.0, "S1_sonum06": 0.6,
          "S2_kazanc_TEK": 0.0, "S3_sonum10": 1.0}


def mekanizma(on=""):
    """eps~0 & tirmanirken artik: sonumleme aciksa +Kd*|vz| yonunde kayar."""
    import control.guidance.bbox_ibvs as B          # noqa: E402
    C = B.Cfg

    def nis(p):
        return max(C.CY_NISAN - B.NISAN_KAYMA_MAX,
                   min(C.CY_NISAN + B.NISAN_KAYMA_MAX, B.elev_piksel(-p, C)))

    pen = kol_pencereleri()
    if not pen:
        return {}
    kova = {}
    for y in sorted(glob.glob(os.path.join(KOK, "veri", "ucus_kamera",
                                           "*", "kareler.csv")),
                    key=os.path.getmtime)[-3:]:
        with open(y, encoding="utf-8", errors="replace") as fh:
            for r in csv.DictReader(fh):
                tw = _f(r, "t_wall")
                if tw is None or not gecerli(r):
                    continue
                if (r.get("faz") or "").strip() != "VISUAL":
                    continue
                sp, ol = _f(r, "sp_vz"), _f(r, "olc_vz")
                cy, pit = _f(r, "kutu_cy"), _f(r, "d_pitch")
                if None in (sp, ol, cy, pit):
                    continue
                eps = math.atan((cy * 480.0 - nis(math.radians(pit))) / B.geo.FY)
                if abs(eps) >= 0.08 or -ol >= -0.4:      # eps~0 ve TIRMANIYOR
                    continue
                for ad, t0, t1 in pen:
                    if t0 <= tw < t1:
                        if not on or ad.startswith(on):
                            kova.setdefault(ad, []).append((eps, -ol, sp))
                        break
    out = {}
    for ad, v in kova.items():
        if len(v) < 12:
            out[ad] = (len(v), None, None)
            continue
        eps = np.array([x[0] for x in v])
        vz = np.array([x[1] for x in v])
        sp = np.array([x[2] for x in v])
        kvz = KOL_KVZ.get(ad.split("#")[0], C.K_VZ)
        artik = float(np.median(sp) - kvz * C.V_NOM * float(np.median(eps)))
        bek = float(-KOL_KD.get(ad.split("#")[0], 0.0) * np.median(vz))
        out[ad] = (len(v), artik, bek)
    return out


def _mekanizma_eski(on=""):
    """ESKI/BOZUK surum -- yalniz kayit icin tutuluyor, cagrilmiyor."""
    pen = kol_pencereleri()
    if not pen:
        return {}
    kova = {}
    for y in sorted(glob.glob(os.path.join(KOK, "veri", "ucus_kamera",
                                           "*", "kareler.csv")),
                    key=os.path.getmtime)[-4:]:
        with open(y, encoding="utf-8", errors="replace") as fh:
            for r in csv.DictReader(fh):
                tw = _f(r, "t_wall")
                if tw is None or not gecerli(r):
                    continue
                if (r.get("faz") or "").strip() != "VISUAL":
                    continue
                sp, ol = _f(r, "sp_vz"), _f(r, "olc_vz")
                cy, pit = _f(r, "kutu_cy"), _f(r, "d_pitch")
                men = _f(r, "menzil")
                if None in (sp, ol, cy, pit, men):
                    continue
                if abs(sp) >= 2.99 or men < 6.0:     # doymus / terminal disla
                    continue
                for ad, t0, t1 in pen:
                    if t0 <= tw < t1:
                        if not on or ad.startswith(on):
                            kova.setdefault(ad, []).append(
                                (cy, math.radians(pit), ol, sp))
                        break
    out = {}
    for ad, v in kova.items():
        if len(v) < 120:
            out[ad] = (len(v), None)
            continue
        A = np.array([[x[0], x[1], x[2], 1.0] for x in v])
        b = np.array([x[3] for x in v])
        try:
            kats = np.linalg.lstsq(A, b, rcond=None)[0]
            out[ad] = (len(v), float(kats[2]))
        except np.linalg.LinAlgError:
            out[ad] = (len(v), None)
    return out


# ── 3) DEVIR GECICI DAVRANISI (asil olcut) ──────────────────────────────
def devir_izleri(on="", dosya=2):
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
    IZ = {}
    for (dos, ad), R in G.items():
        R = _donmus_temizle(R)          # ⚠ DONMUS telemetri (bkz. arac/gecerlilik.py)
        R.sort(key=lambda r: (_f(r, "t") or 0.0))
        for i in range(1, len(R)):
            if (R[i - 1].get("faz") or "").strip() != "GPS":
                continue
            if (R[i].get("faz") or "").strip() != "VISUAL":
                continue
            t0 = _f(R[i], "t")
            if t0 is None:
                continue
            iz = []
            for j in range(max(0, i - 40), min(len(R), i + 220)):
                t = _f(R[j], "t")
                if t is None:
                    continue
                dt = t - t0
                if not (-0.5 <= dt <= 5.0):
                    continue
                if not gecerli(R[j]):
                    continue
                v = _f(R[j], "irt_fark")
                if v is None:
                    continue
                iz.append((dt, v, _f(R[j], "menzil")))
            if len(iz) >= 20:
                IZ.setdefault(ad, []).append(iz)
    return IZ


def gecici_olc(H):
    """asim orani, 1 m altina inis suresi, +3..5 s'de |dz|, gecip gitme."""
    asim, sure, son = [], [], []
    gec = 0
    n = 0
    for iz in H:
        a = [x for x in iz if -0.3 <= x[0] <= 0.1]
        il = [x for x in iz if x[0] >= 0]
        if not a or len(il) < 10:
            continue
        z0 = med([x[1] for x in a])
        if abs(z0) < 0.3:
            continue
        n += 1
        ters = [x[1] for x in il if (x[1] > 0) != (z0 > 0)]
        if ters:
            gec += 1
            asim.append(abs(max(ters, key=abs)) / abs(z0))
        else:
            asim.append(0.0)
        alt = [x[0] for x in il if abs(x[1]) < 1.0]
        sure.append(alt[0] if alt else float("nan"))
        s = [abs(x[1]) for x in il if x[0] >= 3.0]
        if s:
            son.append(med(s))
    if not n:
        return None
    su = [x for x in sure if not math.isnan(x)]
    return dict(n=n, asim=med(asim), sure=med(su) if su else float("nan"),
                sure_orani=len(su) / float(n), son=med(son) if son else float("nan"),
                gec=100.0 * gec / n)


BEK = {"S0_taban_a": 0.0, "S0_taban_b": 0.0, "S2_kazanc_TEK": 0.0,
       "S1_sonum06": -0.6, "S3_sonum10": -1.0}


# ── 4) SONUC OLCUTU: CPA (vurus sayisindan COK daha iyi guclendirilmis) ──
# ⚠ NEDEN VURUS SAYISI DEGIL: 14 dk'da 1-8 vurus cikiyor; Poisson gurultusu
#   +-2.8 civari. Iki kolu 4 vs 2 vurusla ayirmak istatistiksel olarak
#   MUMKUN DEGIL. CPA ise kol basina 40-60 yaklasma verir.
def cpa_olc(on="", dosya=2):
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
        ep = None
        sont = None
        for r in R:
            t = _f(r, "t")
            if t is None:
                continue
            if sont is not None and (t < sont or t - sont > 3.0):
                ep = None                       # saat sicramasi -> epizodu kes
            sont = t
            m, h = _f(r, "menzil"), _f(r, "d_hiz")
            dz = _f(r, "irt_fark")
            if None in (m, h, dz) or m < 0.5 or h <= 0.5:
                continue
            fp = _f(r, "fps")
            if m < 18.0:
                if ep is None:
                    ep = []
                ep.append((m, dz, fp))
            elif ep is not None and m > 24.0:
                if len(ep) >= 8:
                    OUT.setdefault(ad, []).append(min(ep, key=lambda x: x[0]))
                ep = None
        if ep and len(ep) >= 8:
            OUT.setdefault(ad, []).append(min(ep, key=lambda x: x[0]))
    return OUT


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--on", default="S")
    ap.add_argument("--dosya", type=int, default=2)
    a = ap.parse_args()

    MEK = mekanizma(a.on)
    IZ = devir_izleri(a.on, a.dosya)

    print("=" * 94)
    print("  SEYIR DIKEY SONUMLEMESI -- HUKUM")
    print("=" * 94)
    print("\n[1] MEKANIZMA KAPISI  --  eps~0 & TIRMANIRKEN artik (= +Kd*|vz| olmali)")
    print("-" * 94)
    print("   taban kollarina gore KAYMA olculur; yon guvenilir, mutlak buyukluk degil")
    print("%-18s %8s %12s %12s %12s %s"
          % ("AYAR", "n", "artik", "taban farki", "beklenen", "hukum"))
    kapi = {}
    tb_art = [MEK[a][1] for a in MEK
              if "taban" in a and MEK[a][1] is not None]
    taban_art = float(np.mean(tb_art)) if tb_art else None
    for ad in sorted(MEK):
        n, artik, bek = MEK[ad]
        if artik is None:
            print("%-18s %8d %12s %12s %12s  az veri" % (ad, n, "-", "-", "-"))
            kapi[ad] = False
            continue
        fark = (artik - taban_art) if taban_art is not None else float("nan")
        if abs(bek) < 1e-9:                       # kapi KAPALI olmali
            ok = abs(fark) < 0.10
            hk = "GECTI (kapali)" if ok else "!! BEKLENMEDIK KAYMA"
        else:                                     # kapi ACIK olmali
            ok = fark > 0.30 * bek                # teorinin en az %30'u
            hk = ("GECTI (%%%.0f)" % (100 * fark / bek)) if ok else "!! ACILMAMIS"
        kapi[ad] = ok
        print("%-18s %8d %12.3f %12.3f %12.3f  %s"
              % (ad, n, artik, fark, bek, hk))
    print("\n[2] DEVIR SONRASI GECICI DAVRANIS  (asil olcut)")
    print("-" * 94)
    print("%-18s %6s %9s %12s %11s %12s %s"
          % ("AYAR", "devir", "asim", "1m alti(s)", "1m'e giren",
             "+3..5s |dz|", "gecip giden"))
    S = {}
    for ad in sorted(IZ):
        o = gecici_olc(IZ[ad])
        if not o or o["n"] < 15:
            continue
        S[ad] = o
        print("%-18s %6d %8.0f%% %12.2f %10.0f%% %12.2f %10.0f%%"
              % (ad, o["n"], 100 * o["asim"], o["sure"],
                 100 * o["sure_orani"], o["son"], o["gec"]))
    tb = [k for k in S if "taban" in k]
    if tb and len(S) > len(tb):
        print("\n[3] KIYAS  (taban kollarinin ortalamasina gore)")
        print("-" * 94)
        ta = {m: float(np.mean([S[k][m] for k in tb]))
              for m in ("asim", "sure", "son", "gec")}
        print("   TABAN      : asim %%%.0f | 1m alti %.2f s | +3..5s |dz| %.2f | gecip giden %%%.0f"
              % (100 * ta["asim"], ta["sure"], ta["son"], ta["gec"]))
        for ad in sorted(S):
            if ad in tb:
                continue
            o = S[ad]
            g = "" if kapi.get(ad, True) else "   !! MEKANIZMA KAPISI ACILMAMIS -- OKUMA"
            print("   %-11s: asim %%%.0f (%+.0f) | 1m %.2f s (%+.2f) | |dz| %.2f (%+.2f) | gecip %%%.0f (%+.0f)%s"
                  % (ad, 100 * o["asim"], 100 * (o["asim"] - ta["asim"]),
                     o["sure"], o["sure"] - ta["sure"],
                     o["son"], o["son"] - ta["son"],
                     o["gec"], o["gec"] - ta["gec"], g))
    CPA = cpa_olc(a.on, a.dosya)
    if CPA:
        print("\n[4] SONUC OLCUTU: EN YAKIN GECIS (vurus sayisindan cok daha guclu)")
        print("-" * 94)
        print("%-18s %8s %11s %9s %9s %10s %7s"
              % ("AYAR", "yaklasma", "CPA medyan", "<1.5 m", "<1 m",
                 "|dz|@CPA", "fps"))
        for ad in sorted(CPA):
            v = CPA[ad]
            if len(v) < 12:
                continue
            m = np.array([x[0] for x in v])
            z = np.array([abs(x[1]) for x in v])
            fp = [x[2] for x in v if x[2] is not None]
            print("%-18s %8d %11.2f %8.0f%% %8.0f%% %10.2f %7s"
                  % (ad, len(v), np.median(m), 100 * np.mean(m < 1.5),
                     100 * np.mean(m < 1.0), np.median(z),
                     ("%.0f" % np.median(fp)) if fp else "-"))
        print("\n   ⚠ Vurus sayisi 14 dk'da 1-8 arasi = Poisson gurultusu +-2.8;")
        print("     iki kolu vurusla ayirmak MUMKUN DEGIL. CPA'ya bak.")
    print("\n   !! KARAR KURALI: S1 (sonumleme) ile S2 (ayni durgun kazanc,")
    print("      sonumleme YOK) karsilastirilmadan sonumlemenin ise yaradigi")
    print("      SOYLENEMEZ. S1 ~ S2 ise etki kazanctandir, terimi geri al.")
    print()


if __name__ == "__main__":
    main()

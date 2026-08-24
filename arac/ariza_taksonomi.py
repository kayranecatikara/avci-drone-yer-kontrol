# -*- coding: utf-8 -*-
"""
================================================================================
  ARIZA TAKSONOMISI  --  gorsel faz KAC FARKLI SEKILDE oluyor?
================================================================================
SORU
--------------------------------------------------------------------------------
Tek bir angajmana bakip genelleme yapmak defalarca yaniltti. Bu betik BUGUNKU
BUTUN gorsel fazlari (her bbox_ibvs_*.csv = BIR faz) tek tek siniflandirir:

  A) YANDAN CIKTI  hedef kadrajin YAN sinirini asti      (|tan az| > 1.807)
  B) DIKEYDEN CIKTI hedef kadrajin UST/ALT sinirini asti (|tan el| > 1.016)
  C) TESPIT OLDU   hedef kadrajin ICINDEYDI, dedektor goremedi
  D) YANLIS NESNE  loglanan cx truth izdusumunden > 120 px sapiyor
  E) BASKA         siniflanamayan

Son 0.5 saniyeye bakilir ve HANGISI ONCE OLDU sorusu ile karar verilir.

--------------------------------------------------------------------------------
 CERCEVE -- TAHMIN DEGIL, OLCUM (bu betigin en kritik parcasi)
--------------------------------------------------------------------------------
hedef_iz HAM OYUN DUNYASI (z yukari), gudum loglari NED. Sozlesme
kopru/dow_kopru.py:49-52:  NED_x=DoW_x, NED_y=-DoW_y, NED_z=-DoW_z.

Bu sozlesme TAHMIN EDILMEDI, ayni saatteki gps_guidance_*.csv'nin iris_x/y/z
(NED) sutunlari ile hedef_iz'in dx/dy/dz (DoW) sutunlari kiyaslanarak
DOGRULANDI (60 dosya, korelasyon +1.0000 / -1.0000 / -1.0000, egimler
+0.9999 / -0.9999 / -0.9999, z'de sabit +48.4 m kalkis datumu). Yani konum
zinciri kesin.

 ! OLCULEN AYKIRILIK -- KAMERA YATAY EKSENI AYNALI
   Truth'tan hesaplanan kamera azimutu ile dedektorun cx'i TERS isaretli.
   6 oturum / 1373 faz / 13105 karede olculdu:
       duz model   |az hatasi| medyan 18-37 deg   p90 70-90 deg
       AYNALI      |az hatasi| medyan  3.3-6.3 deg p90  8-16 deg
       dikey (el)  |el hatasi| medyan  0.8-1.6 deg  -- her iki modelde de ayni
   Dikey mukemmel, yatay tam ters: bu bir MODEL hatasi degil, ISARET hatasi.
   Ayni imza gps_guidance'in KENDI izdusumunde de var: devir aninda yasanin
   u_px'i ~310 (az = -5.9 deg) derken dedektor cx ~329 (az = +5.6 deg) diyor.
   Bu yuzden izdusum AYNALI modelle kurulur (asagida AYNALI_X).
   Kok neden adayi: DoW/Unreal sol-el (Y=sag); NED_y=-DoW_y cevirisi butun
   dunyayi aynaliyor. GPS gudumu ayna-simetrik oldugu icin bundan etkilenmez,
   KAMERA etkilenir.

--------------------------------------------------------------------------------
 KADRAJIN GERCEK SINIRI
--------------------------------------------------------------------------------
bbox_ibvs'teki cx,cy,w,h YASA cercevesindedir: 640x480, F=166.6. Ama gercek
kadraj DoW'un 1920x1080 / HFOV 122.0709 kamerasidir:
    |tan(az)| <= (1920/2)/531.36 = 1.8067  (+-61.04 deg)
    |tan(el)| <= (1080/2)/531.36 = 1.0163  (+-45.47 deg)
Yani 640x480'in tamami DEGIL. (bkz. sim/tesis.py:88-90)

CALISTIR
    python arac/ariza_taksonomi.py                # bugunku butun oturumlar
    python arac/ariza_taksonomi.py --oturum <hedef_iz.csv>
    python arac/ariza_taksonomi.py --gun 20260816
================================================================================
"""
import csv
import glob
import json
import math
import os
import sys
import time

import numpy as np

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IZ_DIZIN = os.path.join(KOK, "veri", "hedef_iz")
LOG_DIZIN = os.path.join(KOK, "kopru", "gazebo_kaynak", "logs")
AB_JSON = os.path.join(KOK, "veri", "ab_pn_pencereler.json")

# ── yasa cercevesi (vision/geometry.py) ──
CX, CY, F = 320.0, 240.0, 166.6
CY_NISAN = 300.0                       # bbox_ibvs.Cfg.CY_NISAN (~240+F*tan20)
TILT_DEG = 25.0                        # kamera gövdeye 25 deg YUKARI
AYNALI_X = True                        # bkz. dosya basi: olculen isaret hatasi

# ── gercek kadraj siniri (tanjant) ──
TAN_AZ_MAX = 1.8067
TAN_EL_MAX = 1.0163
AZ_MAX_DEG = math.degrees(math.atan(TAN_AZ_MAX))    # 61.04
EL_MAX_DEG = math.degrees(math.atan(TAN_EL_MAX))    # 45.47

PENCERE = 0.5          # s; "son 0.5 saniye"
D_ESIK_PX = 120.0      # gorevde verilen esik
D_ESIK_DEG = 25.0      # ek koruma: model kalintisinin (p90 ~11 deg) 2 kati
HIZ_W = 0.5            # s; pencereli hiz turevi


# ══════════════════════════════════════════════════════════════════════════
#  OKUMA
# ══════════════════════════════════════════════════════════════════════════
def _f(s, d=float("nan")):
    try:
        return float(s)
    except (TypeError, ValueError):
        return d


def iz_oku(yol):
    d = np.genfromtxt(yol, delimiter=",", names=True, dtype=None, encoding="utf-8")
    t = np.asarray(d["t_mutlak"], float)
    art = np.concatenate([[True], np.diff(t) > 1e-9])
    d, t = d[art], t[art]
    return {
        "yol": yol, "t": t,
        "hx": np.asarray(d["hx_m"], float), "hy": np.asarray(d["hy_m"], float),
        "hz": np.asarray(d["hz_m"], float),
        "dx": np.asarray(d["dx_m"], float), "dy": np.asarray(d["dy_m"], float),
        "dz": np.asarray(d["dz_m"], float),
    }


def bbox_oku(yol):
    """Bir gorsel faz. Kutusuz (KUTU_YOK) satirlarda yalniz iris_yaw var;
    pitch/roll son gecerli degerden TASINIR (dikey siniflandirma bunun icin
    biraz daha zayif -- raporda soylenir)."""
    with open(yol, newline="", encoding="utf-8") as fh:
        rr = list(csv.DictReader(fh))
    if len(rr) < 5:
        return None
    t, cx, cy, bo, cf, kutu = [], [], [], [], [], []
    yaw, pit, rol = [], [], []
    sp, sr = 0.0, 0.0
    for r in rr:
        t.append(_f(r["t"]))
        var = r["durum"] in ("IBVS", "TERMINAL")
        kutu.append(var)
        cx.append(_f(r["cx"])); cy.append(_f(r["cy"]))
        bo.append(_f(r["boyut"])); cf.append(_f(r["conf"]))
        yaw.append(_f(r["iris_yaw_deg"]))
        if r["iris_pitch_deg"]:
            sp, sr = _f(r["iris_pitch_deg"]), _f(r["iris_roll_deg"])
        pit.append(sp); rol.append(sr)
    a = {k: np.asarray(v, float) for k, v in
         (("t", t), ("cx", cx), ("cy", cy), ("boyut", bo), ("conf", cf),
          ("yaw", yaw), ("pit", pit), ("rol", rol))}
    a["kutu"] = np.asarray(kutu, bool)
    a["ad"] = os.path.basename(yol)
    # AYNI ZAMAN DAMGALI satirlar var (loop iki kere yazabiliyor) -> turev
    # alirken 0'a bolme yapar; tekillestir.
    tek = np.concatenate([[True], np.diff(a["t"]) > 1e-6])
    for k in list(a):
        if k != "ad":
            a[k] = a[k][tek]
    # yaw bosluklarini doldur (nadiren bos gelebiliyor)
    m = np.isfinite(a["yaw"])
    if m.sum() < 3:
        return None
    a["yaw"] = np.interp(a["t"], a["t"][m], np.unwrap(np.radians(a["yaw"][m])))
    a["pit"] = np.radians(a["pit"]); a["rol"] = np.radians(a["rol"])
    return a


# ══════════════════════════════════════════════════════════════════════════
#  GEOMETRI
# ══════════════════════════════════════════════════════════════════════════
def pencereli(t, x, w=HIZ_W):
    ta = np.clip(t - w / 2, t[0], t[-1])
    tb = np.clip(t + w / 2, t[0], t[-1])
    return (np.interp(tb, t, x) - np.interp(ta, t, x)) / np.maximum(tb - ta, 1e-6)


def kamera(iz, ti, yaw, pit, rol):
    """Truth'tan KAMERA cercevesi. Donus: az_deg, el_deg, menzil, cx_izd, cy_izd.
    az/el kamera ekseni etrafinda (sag+ / asagi+); cx_izd AYNALI_X uygulanmis."""
    n = np.interp(ti, iz["t"], iz["hx"]) - np.interp(ti, iz["t"], iz["dx"])
    e = -(np.interp(ti, iz["t"], iz["hy"]) - np.interp(ti, iz["t"], iz["dy"]))
    dn = -(np.interp(ti, iz["t"], iz["hz"]) - np.interp(ti, iz["t"], iz["dz"]))
    xb = n * np.cos(yaw) + e * np.sin(yaw)
    yb = -n * np.sin(yaw) + e * np.cos(yaw)
    zb = dn
    yb, zb = (yb * np.cos(rol) + zb * np.sin(rol),
              -yb * np.sin(rol) + zb * np.cos(rol))
    th = math.radians(TILT_DEG) + pit
    xc = xb * np.cos(th) - zb * np.sin(th)
    zc = xb * np.sin(th) + zb * np.cos(th)
    az = np.degrees(np.arctan2(yb, xc))
    el = np.degrees(np.arctan2(zc, xc))
    s = -1.0 if AYNALI_X else 1.0
    with np.errstate(divide="ignore", invalid="ignore"):
        cxp = CX + s * F * yb / xc
        cyp = CY + F * zc / xc
    cxp = np.where(xc > 0.3, cxp, np.nan)
    cyp = np.where(xc > 0.3, cyp, np.nan)
    return az, el, np.sqrt(n * n + e * e + dn * dn), cxp, cyp


def aspect_deg(iz, ti):
    """ASPECT ACISI (havacilik tanimi): hedefin KUYRUGU ile hedeften bize
    bakan LOS arasindaki aci.
        0   = tam kuyrukta  (hedefin arkasindayiz, o bizden kaciyor)
        180 = tam karsidan  (bas basa)
    Hesap: hedefin hiz vektoru ile BIZDEN HEDEFE bakan vektorun acisi --
    arkasindaysak ikisi ayni yone bakar -> 0."""
    vhx = np.interp(ti, iz["t"], pencereli(iz["t"], iz["hx"]))
    vhy = np.interp(ti, iz["t"], pencereli(iz["t"], iz["hy"]))
    vhz = np.interp(ti, iz["t"], pencereli(iz["t"], iz["hz"]))
    lx = np.interp(ti, iz["t"], iz["hx"]) - np.interp(ti, iz["t"], iz["dx"])
    ly = np.interp(ti, iz["t"], iz["hy"]) - np.interp(ti, iz["t"], iz["dy"])
    lz = np.interp(ti, iz["t"], iz["hz"]) - np.interp(ti, iz["t"], iz["dz"])
    nv = np.sqrt(vhx**2 + vhy**2 + vhz**2)
    nl = np.sqrt(lx**2 + ly**2 + lz**2)
    c = (vhx * lx + vhy * ly + vhz * lz) / np.maximum(nv * nl, 1e-9)
    return np.degrees(np.arccos(np.clip(c, -1, 1)))


# ══════════════════════════════════════════════════════════════════════════
#  SINIFLANDIRMA
# ══════════════════════════════════════════════════════════════════════════
def faz_incele(iz, b):
    t = b["t"]
    az, el, rng, cxp, cyp = kamera(iz, t, b["yaw"], b["pit"], b["rol"])
    asp = aspect_deg(iz, t)
    vd = np.hypot(np.interp(t, iz["t"], pencereli(iz["t"], iz["dx"])),
                  np.interp(t, iz["t"], pencereli(iz["t"], iz["dy"])))
    # kapanma hizi: +' = yaklasiyoruz
    rr = np.sqrt((iz["hx"] - iz["dx"])**2 + (iz["hy"] - iz["dy"])**2
                 + (iz["hz"] - iz["dz"])**2)
    kap = -np.interp(t, iz["t"], pencereli(iz["t"], rr))

    kutu = b["kutu"] & np.isfinite(b["cx"])
    if kutu.sum() < 3:
        return None
    i0, iN = int(np.argmax(kutu)), int(len(t) - 1 - np.argmax(kutu[::-1]))
    t_son_kutu = t[iN]
    t_bit = t[-1]
    omur = t_bit - t[0]
    temas = t_son_kutu - t[i0]

    disari_az = np.abs(az) > AZ_MAX_DEG
    disari_el = np.abs(el) > EL_MAX_DEG
    sapma_px = np.where(kutu, np.abs(b["cx"] - cxp), np.nan)
    # aci uzayinda sapma: olculen az (ayna cozulmus) ile truth az farki
    az_olc = (-1.0 if AYNALI_X else 1.0) * np.degrees(
        np.arctan((b["cx"] - CX) / F))
    sapma_deg = np.where(kutu, np.abs(az_olc - az), np.nan)
    yanlis = kutu & (sapma_px > D_ESIK_PX) & (sapma_deg > D_ESIK_DEG)

    # ⚠ PENCERE SECIMI: faz, kutu kesildikten sonra KAYIP_M=20 kare daha
    # kor devam eder (~0.6 s). O kor kuyrukta arac donmeye devam ettigi icin
    # hedef HER fazda eninde sonunda kadrajdan cikar -- kuyrugu pencereye
    # katmak her seyi "A" yapar. Bu yuzden karar penceresi GORSEL TEMASIN
    # son 0.5 saniyesidir: [son_kutu-0.5, son_kutu].
    pen = (t >= t_son_kutu - PENCERE) & (t <= t_son_kutu + 1e-9)
    def ilk(mask):
        j = np.where(mask & pen)[0]
        return t[j[0]] if len(j) else np.inf
    tA, tB, tD = ilk(disari_az), ilk(disari_el), ilk(yanlis)
    en = min(tA, tB, tD)
    if not np.isfinite(en):
        sinif = "C"
        t_olum = t_son_kutu
    else:
        sinif = "A" if en == tA else ("B" if en == tB else "D")
        t_olum = en
    # C ALT AYRIMI: kor kuyrukta hedef kadrajdan cikiyor mu?
    #   C-kenar : tespit tam kenarda oldu, hedef hemen ardindan cikti
    #   C-ici   : hedef kor kuyruk boyunca kadrajin ICINDE kaldi -- saf
    #             dedektor arizasi
    kuyruk = t > t_son_kutu
    alt = ""
    if sinif == "C":
        cikti = bool(np.any((disari_az | disari_el) & kuyruk))
        alt = "kenar" if cikti else "ici"
    # E: truth kamera onunde degil / veri yok
    if not np.isfinite(rng[iN]):
        sinif, alt = "E", "truth yok"

    j = int(np.argmin(np.abs(t - t_olum)))          # olum ani indeksi
    kj = np.where(kutu & (t <= t_olum + 1e-9))[0]
    kj = kj[-1] if len(kj) else iN                  # olum anindaki son kutu
    return {
        "ad": b["ad"], "t0": t[0], "t_son_kutu": t_son_kutu, "t_bit": t_bit,
        "t_olum": t_olum, "sinif": sinif, "omur": omur, "temas": temas,
        "n_kare": len(t), "n_kutu": int(kutu.sum()),
        "kutu_orani": float(kutu.mean()),
        # olum anindaki kosullar
        "o_menzil": rng[j], "o_aspect": asp[j], "o_boyut": b["boyut"][kj],
        "o_conf": b["conf"][kj], "o_hiz": vd[j], "o_kapanma": kap[j],
        "o_az": az[j], "o_el": el[j], "o_sapma_px": sapma_px[kj],
        "o_sapma_deg": sapma_deg[kj],
        # devir anindaki kosullar
        "d_menzil": rng[i0], "d_aspect": asp[i0], "d_boyut": b["boyut"][i0],
        "d_conf": b["conf"][i0], "d_az": az[i0], "d_el": el[i0],
        "d_cy": b["cy"][i0], "d_dikey_ofset": b["cy"][i0] - CY_NISAN,
        "d_hiz": vd[i0], "d_kapanma": kap[i0],
        # faz boyu
        "min_menzil": float(np.nanmin(rng)), "az_hizi": float(
            np.nanmedian(np.abs(np.gradient(az, t)))),
        "sapma_p50": float(np.nanmedian(sapma_deg)),
    }


# ══════════════════════════════════════════════════════════════════════════
#  A/B PENCERELERI
# ══════════════════════════════════════════════════════════════════════════
def ab_yukle():
    try:
        with open(AB_JSON, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return []


def ab_ad(pencereler, t):
    for p in pencereler:
        if p["t0"] <= t <= p["t1"]:
            return p["ad"]
    return "-"


# ══════════════════════════════════════════════════════════════════════════
#  RAPOR
# ══════════════════════════════════════════════════════════════════════════
def p(a, q):
    a = np.asarray([x for x in a if np.isfinite(x)], float)
    return float(np.percentile(a, q)) if a.size else float("nan")


def med(a):
    return p(a, 50)


def spearman(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() < 5:
        return float("nan")
    rx = np.argsort(np.argsort(x[m])); ry = np.argsort(np.argsort(y[m]))
    return float(np.corrcoef(rx, ry)[0, 1])


SINIF_AD = {"A": "A YANDAN CIKTI", "B": "B DIKEYDEN CIKTI",
            "C": "C TESPIT OLDU", "D": "D YANLIS NESNE", "E": "E BASKA"}


def main():
    gun = time.strftime("%Y%m%d")
    tek = None
    av = sys.argv[1:]
    if "--gun" in av:
        gun = av[av.index("--gun") + 1]
    if "--oturum" in av:
        tek = av[av.index("--oturum") + 1]

    bb = []
    for f in sorted(glob.glob(os.path.join(LOG_DIZIN, "bbox_ibvs_*.csv"))):
        try:
            with open(f, encoding="utf-8") as fh:
                ls = fh.readlines()
            if len(ls) < 6:
                continue
            bb.append((float(ls[1].split(",")[0]), float(ls[-1].split(",")[0]), f))
        except Exception:
            continue

    oturumlar = [tek] if tek else sorted(
        glob.glob(os.path.join(IZ_DIZIN, "hedef_iz_%s_*.csv" % gun)))
    pencereler = ab_yukle()

    kayit, otu_ozet = [], []
    for yol in oturumlar:
        try:
            iz = iz_oku(yol)
        except Exception:
            continue
        if iz["t"].size < 500:
            continue
        sec = [f for a, b_, f in bb if a >= iz["t"][0] and b_ <= iz["t"][-1]]
        n0 = len(kayit)
        for f in sec:
            b = bbox_oku(f)
            if b is None:
                continue
            r = faz_incele(iz, b)
            if r is None:
                continue
            r["oturum"] = os.path.basename(yol)
            r["ab"] = ab_ad(pencereler, r["t0"])
            kayit.append(r)
        if len(kayit) > n0:
            otu_ozet.append((os.path.basename(yol), len(kayit) - n0))

    if not kayit:
        print("Faz bulunamadi. --gun / --oturum ile deneyin.")
        return 1

    N = len(kayit)
    print("=" * 78)
    print("ARIZA TAKSONOMISI -- %s | %d gorsel faz | %d oturum"
          % (gun if not tek else os.path.basename(tek), N, len(otu_ozet)))
    for ad, n in otu_ozet:
        print("   %-34s %3d faz" % (ad, n))
    print("=" * 78)

    # ── 0. cerceve dogrulamasi (kalinti) ──
    sp = [r["sapma_p50"] for r in kayit]
    print("\n[0] IZDUSUM KALINTISI (aynali model)  faz-ici medyan |az hatasi|:"
          " p50=%.1f p90=%.1f deg  -> D esigi %g px / %g deg guvenli"
          % (med(sp), p(sp, 90), D_ESIK_PX, D_ESIK_DEG))

    # ── 1. sinif dagilimi ──
    print("\n[1] OLUM SEKLI DAGILIMI")
    print("%-16s %5s %7s | %7s %7s %7s %7s %7s %7s"
          % ("sinif", "faz", "yuzde", "menzil", "aspect", "kutu", "conf",
             "hizimiz", "kapanma"))
    for s in "ABCDE":
        g = [r for r in kayit if r["sinif"] == s]
        if not g:
            print("%-16s %5d %6.1f%%" % (SINIF_AD[s], 0, 0.0))
            continue
        print("%-16s %5d %6.1f%% | %7.1f %7.0f %7.1f %7.2f %7.1f %+7.1f"
              % (SINIF_AD[s], len(g), 100.0 * len(g) / N,
                 med([r["o_menzil"] for r in g]), med([r["o_aspect"] for r in g]),
                 med([r["o_boyut"] for r in g]), med([r["o_conf"] for r in g]),
                 med([r["o_hiz"] for r in g]), med([r["o_kapanma"] for r in g])))
    print("   (medyanlar; menzil m, aspect deg 0=kuyrukta, kutu px sqrt(w*h),"
          " hiz m/s, kapanma m/s +'=yaklasiyor)")
    print("   olum aninda kadraj acisi:  |az| p50=%.0f p90=%.0f deg (sinir %.0f) |"
          "  |el| p50=%.0f p90=%.0f deg (sinir %.0f)"
          % (med([abs(r["o_az"]) for r in kayit]),
             p([abs(r["o_az"]) for r in kayit], 90), AZ_MAX_DEG,
             med([abs(r["o_el"]) for r in kayit]),
             p([abs(r["o_el"]) for r in kayit], 90), EL_MAX_DEG))
    print("   faz boyunca kutulu kare orani: p50=%.2f  (kalan kareler KUTU_YOK)"
          % med([r["kutu_orani"] for r in kayit]))

    # ── 2. A/B capraz ──
    if pencereler:
        print("\n[2] GUDUM AYARI CAPRAZI (veri/ab_pn_pencereler.json)")
        adlar = [q["ad"] for q in pencereler] + ["-"]
        print("%-14s %5s | %s | %8s %8s"
              % ("ayar", "faz", " ".join("%5s" % s for s in "ABCDE"),
                 "omur_p50", "omur_p90"))
        for a in adlar:
            g = [r for r in kayit if r["ab"] == a]
            if not g:
                continue
            ayar = next((q["ayar"] for q in pencereler if q["ad"] == a), {})
            print("%-14s %5d | %s | %8.2f %8.2f   %s"
                  % (a, len(g),
                     " ".join("%5d" % sum(1 for r in g if r["sinif"] == s)
                              for s in "ABCDE"),
                     med([r["omur"] for r in g]), p([r["omur"] for r in g], 90),
                     ("PN=%.1f BURUN_LOS=%s" % (ayar.get("PN_N", 0),
                                                ayar.get("BURUN_LOS"))
                      if ayar else "(pencere disi)")))

    # ── 3. omur dagilimi ──
    om = [r["omur"] for r in kayit]
    te = [r["temas"] for r in kayit]
    print("\n[3] FAZ OMRU (s)")
    print("   toplam faz omru : p10=%.2f  p50=%.2f  p90=%.2f  min=%.2f max=%.2f"
          % (p(om, 10), med(om), p(om, 90), min(om), max(om)))
    print("   gorsel temas    : p10=%.2f  p50=%.2f  p90=%.2f"
          % (p(te, 10), med(te), p(te, 90)))
    print("   omur ~ devir kosulu (Spearman rho):")
    for ad, k in (("devir menzili", "d_menzil"), ("devir aspect", "d_aspect"),
                  ("devir kutu boyutu", "d_boyut"), ("devir conf", "d_conf"),
                  ("devir |az|", "d_az"), ("devir dikey ofset", "d_dikey_ofset"),
                  ("devir kapanma", "d_kapanma"),
                  ("faz-ici LOS az hizi", "az_hizi")):
        v = [abs(r[k]) if k == "d_az" else r[k] for r in kayit]
        print("      %-22s rho=%+.3f" % (ad, spearman(v, om)))

    # ── 4. devir kosullari + hangi kosul daha uzun faz veriyor ──
    print("\n[4] DEVIR ANI KOSULLARI (n=%d)" % N)
    print("%-20s %8s %8s %8s" % ("", "p10", "p50", "p90"))
    for ad, k in (("menzil (m)", "d_menzil"), ("aspect (deg)", "d_aspect"),
                  ("kutu boyut (px)", "d_boyut"), ("conf", "d_conf"),
                  ("kadraj az (deg)", "d_az"), ("kadraj el (deg)", "d_el"),
                  ("dikey ofset (px)", "d_dikey_ofset"),
                  ("kapanma (m/s)", "d_kapanma")):
        v = [r[k] for r in kayit]
        print("%-20s %8.1f %8.1f %8.1f" % (ad, p(v, 10), med(v), p(v, 90)))
    print("\n   DEVIR KAPISI: kosul ucte bolunup omur medyani")
    for ad, k in (("devir menzili (m)", "d_menzil"),
                  ("devir aspect (deg)", "d_aspect"),
                  ("devir kutu (px)", "d_boyut"),
                  ("devir |kadraj az| (deg)", "d_az"),
                  ("devir dikey ofset (px)", "d_dikey_ofset"),
                  ("devir conf", "d_conf")):
        v = np.array([abs(r[k]) if k == "d_az" else r[k] for r in kayit], float)
        q1, q2 = np.nanpercentile(v, [33.3, 66.7])
        sat = []
        for lo, hi, et in ((-np.inf, q1, "dusuk"), (q1, q2, "orta"),
                           (q2, np.inf, "yuksek")):
            m = (v > lo) & (v <= hi)
            g = [r for r, mm in zip(kayit, m) if mm]
            sat.append("%s(<=%.1f) n=%2d omur=%.2f A=%d C=%d"
                       % (et, hi if np.isfinite(hi) else v.max(), len(g),
                          med([r["omur"] for r in g]),
                          sum(1 for r in g if r["sinif"] == "A"),
                          sum(1 for r in g if r["sinif"] == "C")))
        print("   %-24s %s" % (ad, " | ".join(sat)))

    # ── 5. yaklasan fazlar ──
    print("\n[5] EN YAKIN GECIS")
    mm = [r["min_menzil"] for r in kayit]
    print("   faz-ici min menzil: p10=%.1f p50=%.1f p90=%.1f m" %
          (p(mm, 10), med(mm), p(mm, 90)))
    yak = sum(1 for r in kayit if r["min_menzil"] < r["d_menzil"] - 1.0)
    print("   devir menzilinden >1 m YAKLASAN faz: %d/%d (%%%.0f)"
          % (yak, N, 100.0 * yak / N))
    en = sorted(kayit, key=lambda r: r["min_menzil"])[:5]
    print("%-32s %6s %6s %6s %6s %6s %6s %5s %5s"
          % ("en yakin 5 faz", "min_m", "dev_m", "omur", "asp0", "kutu0",
             "azHiz", "sinif", "ab"))
    for r in en:
        print("%-32s %6.1f %6.1f %6.2f %6.0f %6.1f %6.0f %5s %5s"
              % (r["ad"], r["min_menzil"], r["d_menzil"], r["omur"],
                 r["d_aspect"], r["d_boyut"], r["az_hizi"], r["sinif"], r["ab"]))
    dg = [r for r in kayit if r not in en]
    print("   kiyas (kalan %d faz medyani): min_m=%.1f dev_m=%.1f omur=%.2f "
          "asp0=%.0f kutu0=%.1f azHiz=%.0f"
          % (len(dg), med([r["min_menzil"] for r in dg]),
             med([r["d_menzil"] for r in dg]), med([r["omur"] for r in dg]),
             med([r["d_aspect"] for r in dg]), med([r["d_boyut"] for r in dg]),
             med([r["az_hizi"] for r in dg])))

    # ── 6. faz listesi ──
    if "--liste" in av:
        print("\n[6] FAZ FAZ")
        print("%-32s %5s %6s %6s %7s %6s %6s %6s %5s"
              % ("faz", "sinif", "omur", "dev_m", "dev_asp", "olm_m", "az",
                 "el", "ab"))
        for r in kayit:
            print("%-32s %5s %6.2f %6.1f %7.0f %6.1f %6.0f %6.0f %5s"
                  % (r["ad"], r["sinif"], r["omur"], r["d_menzil"],
                     r["d_aspect"], r["o_menzil"], r["o_az"], r["o_el"],
                     r["ab"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
"""
================================================================================
  YAW BAYATLIGI + MENZIL KALIBRASYONU TEZGAHI
================================================================================
NE YAPAR
--------------------------------------------------------------------------------
  --yaw      KOMUT YOLUNUN yaw bayatligini GERCEK ucus loglarinda olcer ve
             `Cfg.KOMUT_HIZALA_S` taramasini yapar (yasanin KENDI EMA'li
             yaw_hizi'siyla, canli kodun birebir tekrari).
  --menzil   MENZIL_PX_M / K_w / additif-pay modellerini truth'a karsi kiyaslar,
             menzil dilimlerine ve TERMINAL bandina ayirir; terminal nisan
             kapisindaki 160.0 IKIZININ tutarsizligini sayiyla gosterir.
  --kapi     MEKANIZMA KAPILARI: bbox_ibvs.komut()'u dogrudan cagirip
             yamalarin (a) varsayilanda BIT-AYNI oldugunu, (b) acildiginda
             beklenen imzayi urettigini kanitlar.
  --hepsi    ucu birden.

⛔ OYUNA DOKUNMAZ. Yalnizca diskteki CSV'leri OKUR. Port 12345'e baglanmaz,
   hicbir sureci baslatmaz/oldurmez. Kampanya kosarken guvenle calisir.
   ⛔ Hicbir env degiskenini KALICI olarak degistirmez; --kapi testi env'i
      kendi icinde kurar ve ESKI HALINE geri koyar (modul reload'lariyla).

================================================================================
 NEDEN AYRI BIR TEZGAH (sim/bbox_kontrol.py zaten var)
================================================================================
bbox_kontrol.py GEOMETRIYI sinar: "piksel -> aci" dogru mu? Cevabi biliniyor
(A1 4.30 deg, A3 1.32 deg). Ama o tezgah *yasanin ne yaptigini* degil,
*formulun ne verdigini* olcuyor. Buradaki soru farkli:

    yasa KOMUTU kurarken `iris_yaw(SIMDI) + eps(t-D)` yaziyor.
    Bunu duzeltmek icin elimizde IDEAL dpsi = yaw(t) - yaw(t-D) YOK;
    elimizde yalnizca yasanin kendi EMA'li `yaw_hizi` kestirimi var.
    KOMUT_HIZALA_S * yaw_hizi, IDEAL dpsi'nin ne kadarini yakalar?

Bu soru ancak canli kodun EMA'sini BIREBIR tekrarlayarak cevaplanir:
    yaw_hizi <- 0.3 * (dyaw/dt) + 0.7 * yaw_hizi        (bbox_ibvs.py:1803-1805)
ve bu EMA HER dongu adiminda isler -- KUTUSUZ karelerde de. Bu yuzden ham
CSV'nin BUTUN satirlari okunur (bbox_kontrol.yasa_yukle yalniz tespitli
satirlari tutar; onunla EMA yeniden uretilemez).

================================================================================
 TRUTH  (bbox_kontrol.py ile AYNI kaynak, ayni kapilar)
================================================================================
 KULLANILAN: veri/hedef_iz/hedef_iz_*.csv  (drone.get_debug_truth)
 KULLANILMAYAN: karar_*.csv'nin u_truth/v_truth'u (kestirim projeksiyonu)
 AYNA ERASI KAPISI: yatay (yaw) istatistikleri YALNIZ `ayna_sonrasi` loglardan.
 Menzil de ayni kumeden okunur -- tek veri kumesi, tek hukum.
================================================================================
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "kopru", "gazebo_kaynak"))
sys.path.insert(0, os.path.join(KOK, "sim"))

from control.guidance import bbox_geometri as BG          # noqa: E402
import bbox_kontrol as BK                                 # noqa: E402

LOG_DIR = BK.LOG_DIR

# yasanin kendi EMA katsayisi (bbox_ibvs.py:1805)
EMA_A = 0.3


# ══════════════════════════════════════════════════════════════════════════
#  0. YARDIMCILAR
# ══════════════════════════════════════════════════════════════════════════

def med(a):
    if not a:
        return float("nan")
    s = sorted(a)
    n = len(s)
    return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])


def p(a, q):
    return BK.yuzdelik(a, q)


def _f(s, vars=float("nan")):
    return BK._f(s, vars)


# ══════════════════════════════════════════════════════════════════════════
#  1. CANLI `yaw_hizi` EMA'SININ BIREBIR TEKRARI
# ══════════════════════════════════════════════════════════════════════════

def sonum_serisi(yol):
    """BAGIMSIZ DOGRULAMA: logun kendi `sonum_deg` sutunu.

    Canli kod: sonum = clamp(SONUM_T*yaw_hizi, ±SONUM_MAX_DEG) ve varsayilan
    SONUM_T = 0.30. Yani `sonum_deg/0.30`, YASANIN KENDI yaw_hizi'sidir --
    benim EMA yeniden uretimimden BAGIMSIZ bir tanik. Ikisi ortusmezse
    yeniden uretim YANLIStir ve butun --yaw sonucu COPTUR.
    ⚠ |yaw_hizi| > 100 °/s'de sonum doyar (SONUM_MAX_DEG=30) -> o kareler
      karsilastirmadan CIKARILIR.
    """
    out = {}
    try:
        with open(yol, "r", encoding="utf-8", errors="replace") as f:
            rd = csv.DictReader(f)
            if "sonum_deg" not in (rd.fieldnames or []):
                return {}
            for row in rd:
                tt = _f(row.get("t"))
                sd = _f(row.get("sonum_deg"))
                if math.isfinite(tt) and math.isfinite(sd):
                    out[round(tt, 3)] = math.radians(sd) / 0.30
    except Exception:
        return {}
    return out


def yaw_hizi_serisi(yol):
    """Ham bbox_ibvs CSV -> {t: yaw_hizi(rad/s)}.

    CANLI KODUN BIREBIR TEKRARI (bbox_ibvs.py:1795-1806):
        dt   = clamp(now - prev, 0.001, 0.5)
        _yr  = sarmala_pi(iyaw - iyaw_onceki) / dt
        yaw_hizi = 0.3*_yr + 0.7*yaw_hizi        (yalniz 1e-3 < dt < 0.5 iken)
    ve BU DONGU HER KAREDE isler -- KUTU_YOK / kopru satirlari DAHIL.
    Bu yuzden burada CSV'nin butun satirlari okunur; tespit filtresi YOK.

    TEK SAPMA: canli kodda `now = time.monotonic()`, logda `t` 3 haneye
    YUVARLANMIS. 1 ms kuantalama 30 Hz'de dt'de <%4 hata demek.
    """
    out = {}
    t_on = None
    y_on = None
    yh = 0.0
    try:
        with open(yol, "r", encoding="utf-8", errors="replace") as f:
            for row in csv.DictReader(f):
                tt = _f(row.get("t"))
                yd = _f(row.get("iris_yaw_deg"))
                if not (math.isfinite(tt) and math.isfinite(yd)):
                    continue
                iyaw = math.radians(yd)
                if t_on is not None and y_on is not None:
                    dt = BG.kirp(tt - t_on, 0.001, 0.5)
                    if 1e-3 < dt < 0.5:
                        _yr = BG.sarmala_pi(iyaw - y_on) / dt
                        yh = EMA_A * _yr + (1.0 - EMA_A) * yh
                t_on, y_on = tt, iyaw
                out[round(tt, 3)] = yh
    except Exception:
        return {}
    return out


_YH_ONBELLEK = {}


def yaw_hizi_al(log_adi):
    if log_adi not in _YH_ONBELLEK:
        _YH_ONBELLEK[log_adi] = yaw_hizi_serisi(os.path.join(LOG_DIR, log_adi))
    return _YH_ONBELLEK[log_adi]


_SN_ONBELLEK = {}


def sonum_al(log_adi):
    if log_adi not in _SN_ONBELLEK:
        _SN_ONBELLEK[log_adi] = sonum_serisi(os.path.join(LOG_DIR, log_adi))
    return _SN_ONBELLEK[log_adi]


def yaw_hizi_ekle(kayit):
    """Her kayda canli EMA'li `yaw_hizi`yi ve IDEAL `dpsi`yi ekler."""
    n_ok = 0
    for r in kayit:
        seri = yaw_hizi_al(r["log"])
        v = seri.get(round(r["t"], 3))
        r["yaw_hizi"] = v
        r["yaw_hizi_log"] = sonum_al(r["log"]).get(round(r["t"], 3))
        # IDEAL bayatlik: dpsi = yaw(t) - yaw(t-D).
        #   eps_truth   = az_dunya - yaw(t)
        #   eps_truth_h = az_dunya - yaw(t-D)
        # => dpsi = eps_truth_h - eps_truth      (ekstra veri gerekmez)
        r["dpsi"] = BG.sarmala_pi(r["eps_truth_h"] - r["eps_truth"])
        if v is not None:
            n_ok += 1
    return n_ok


# ══════════════════════════════════════════════════════════════════════════
#  2. YAW BAYATLIGI: KOMUT_HIZALA_S TARAMASI
# ══════════════════════════════════════════════════════════════════════════

K_TARAMA = [0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40]


def kiyas_yaw(kayit, ayrinti=False):
    """Yasanin komut yolundaki YATAY hatasini ve telafisini olcer.

    HATA TANIMI (yasanin gercekten yaptigi is):
        yasa mutlak kerterizi  psi_L = yaw(t) + eps_kutu(t-D)
        gercek mutlak kerteriz psi_T = yaw(t) + eps_truth
        hata = eps_kutu - eps_truth              (yaw sadelesir)
    Telafi acikken yasa `- KOMUT_HIZALA_S*yaw_hizi` ekler:
        hata(K) = eps_kutu - K*yaw_hizi - eps_truth
    Ust sinir (ideal, olculemez): eps_kutu - eps_truth_h
    """
    g = [r for r in kayit
         if r.get("ayna_sonrasi") and r.get("yaw_hizi") is not None]
    print("\n" + "=" * 78)
    print(" YAW BAYATLIGI -- KOMUT YOLU  (n=%d kare, %d log)" %
          (len(g), len({r["log"] for r in g})))
    print("=" * 78)
    if len(g) < 200:
        print("  YETERSIZ VERI")
        return None

    # ── ONCE KENDI OLCUM ARACIMI CURUTMEYI DENE ──
    ck = [(r["yaw_hizi"], r["yaw_hizi_log"]) for r in g
          if r.get("yaw_hizi_log") is not None
          and abs(r["yaw_hizi_log"]) < 1.70]        # sonum doymamis kareler
    print("\n  [DOGRULAMA] yeniden uretilen EMA vs logun KENDI sonum_deg'i")
    if len(ck) < 100:
        print("      n=%d -- YETERSIZ, BAGIMSIZ TANIK YOK (sonuc supheli)" % len(ck))
    else:
        d = [abs(math.degrees(a - b)) for a, b in ck]
        print("      n=%d  |fark| medyan %.3f °/s | p95 %.3f | maks %.2f"
              % (len(ck), med(d), p(d, 95), max(d)))
        print("      -> %s" % ("GECTI: yeniden uretim guvenilir"
                               if med(d) < 0.5 else
                               "⛔ KALDI: EMA yeniden uretimi TUTMUYOR"))

    dpsi_d = [abs(math.degrees(r["dpsi"])) for r in g]
    print("\n  OLCULEN BAYATLIK |dpsi| = |yaw(t) - yaw(t-D)|,  D = %.2f s" %
          BG.DEDEKTOR_GECIKME_S)
    print("      medyan %.2f deg | p90 %.2f | p95 %.2f | maks %.1f" %
          (med(dpsi_d), p(dpsi_d, 90), p(dpsi_d, 95), max(dpsi_d)))

    # yasanin kestirimi (K*yaw_hizi) ideal dpsi'yi ne kadar yakaliyor?
    x = [r["yaw_hizi"] for r in g]
    y = [r["dpsi"] for r in g]
    sxx = sum(a * a for a in x)
    sxy = sum(a * b for a, b in zip(x, y))
    egim = sxy / sxx if sxx > 1e-12 else float("nan")
    ym = sum(y) / len(y)
    sst = sum((b - ym) ** 2 for b in y)
    ssr = sum((b - egim * a) ** 2 for a, b in zip(x, y))
    r2 = 1.0 - ssr / sst if sst > 1e-12 else float("nan")
    print("\n  dpsi ~ egim * yaw_hizi  ->  egim = %.4f s   R^2 = %.3f" % (egim, r2))
    print("      (egim = EMA'li yaw_hizi'nin OPTIMAL carpani; ideal D=%.2f'den"
          % BG.DEDEKTOR_GECIKME_S)
    print("       sapmasi EMA'nin kendi gecikmesidir)")

    def _ist(err_rad):
        a = [abs(math.degrees(e)) for e in err_rad]
        return med(a), p(a, 90), p(a, 95)

    ham = [BG.sarmala_pi(BG.azimut_ham(r["cx"]) - r["eps_truth"]) for r in g]
    sev = []
    for r in g:
        az, _ = BG.los_seviye(r["cx"], r["cy"], r["roll"], r["pitch"])
        sev.append(BG.sarmala_pi(az - r["eps_truth"]))
    ideal = [BG.sarmala_pi(BG.azimut_ham(r["cx"]) - r["eps_truth_h"]) for r in g]
    ideal_sev = []
    for r in g:
        az, _ = BG.los_seviye(r["cx"], r["cy"], r["roll_h"], r["pitch_h"])
        ideal_sev.append(BG.sarmala_pi(az - r["eps_truth_h"]))

    print("\n  %-46s %8s %8s %8s" % ("formulasyon", "|med|", "p90", "p95"))
    print("  " + "-" * 72)
    for ad, e in (("ham atan((cx-CX)/FX), yasanin zamanlamasi", ham),
                  ("los_seviye (roll telafili), yasanin zamanlamasi", sev)):
        m, a, b = _ist(e)
        print("  %-46s %8.2f %8.2f %8.2f" % (ad, m, a, b))

    print("  " + "-" * 72)
    en_iyi = None
    for K in K_TARAMA:
        e = [BG.sarmala_pi(BG.azimut_ham(r["cx"]) - K * r["yaw_hizi"]
                           - r["eps_truth"]) for r in g]
        m, a, b = _ist(e)
        if en_iyi is None or m < en_iyi[1]:
            en_iyi = (K, m, a, b)
        print("  %-46s %8.2f %8.2f %8.2f" %
              ("  KOMUT_HIZALA=%.2f s (HAM eps)" % K, m, a, b))
    print("  " + "-" * 72)
    # SIRA: once hizalama, SONRA roll telafisi.
    Kb = en_iyi[0]
    e = []
    for r in g:
        az, _ = BG.los_seviye(r["cx"], r["cy"], r["roll"], r["pitch"])
        e.append(BG.sarmala_pi(az - Kb * r["yaw_hizi"] - r["eps_truth"]))
    m, a, b = _ist(e)
    print("  %-46s %8.2f %8.2f %8.2f" %
          ("  KOMUT_HIZALA=%.2f + roll telafisi (BAYAT tutum)" % Kb, m, a, b))
    m, a, b = _ist(ideal)
    print("  %-46s %8.2f %8.2f %8.2f" %
          ("UST SINIR: ideal dpsi cikarilmis", m, a, b))
    m, a, b = _ist(ideal_sev)
    print("  %-46s %8.2f %8.2f %8.2f" %
          ("UST SINIR: tutum da t-D'ye hizali", m, a, b))

    print("\n  ⇒ EN IYI OLCULEN K = %.2f s  (|med| %.2f deg, p90 %.2f)" %
          (en_iyi[0], en_iyi[1], en_iyi[2]))

    # ── AYRISTIRMA: gecikmenin NE KADARI ARACIN kendi donusu (duzeltilebilir),
    #    ne kadari HEDEFIN hareketi (duzeltilemez, lead/DPP'nin isi)?
    lam = []
    for i in range(1, len(g)):
        a, b = g[i - 1], g[i]
        if a["log"] != b["log"]:
            continue
        dt = b["t"] - a["t"]
        if not (1e-3 < dt < 0.3):
            continue
        az0 = BG.sarmala_pi(a["eps_truth"] + a["yaw"])
        az1 = BG.sarmala_pi(b["eps_truth"] + b["yaw"])
        lam.append(abs(math.degrees(BG.sarmala_pi(az1 - az0) / dt)))
    if len(lam) > 200:
        print("\n  AYRISTIRMA -- D=%.2f s icinde kerteriz ne kadar kayiyor?"
              % BG.DEDEKTOR_GECIKME_S)
        print("      ARACIN yaw'i (dusuk = duzeltilebilir) |dpsi| medyan %.2f°"
              % med(dpsi_d))
        print("      HEDEFIN hareketi |lam|*D medyan %.2f° (|lam| med %.1f °/s)"
              % (med(lam) * BG.DEDEKTOR_GECIKME_S, med(lam)))
        print("      ⇒ bayatligin %.0f%%'i ARACIN KENDI DONUSU -> KOMUT_HIZALA"
              % (100.0 * med(dpsi_d) / max(med(dpsi_d)
                                           + med(lam) * BG.DEDEKTOR_GECIKME_S,
                                           1e-9)))
        print("        kalani hedefin hareketi -- onu LEAD/DPP kapatir, bu yama DEGIL.")

    print("\n  DONUS HIZINA GORE (K=%.2f):" % Kb)
    print("  %-16s %6s %10s %10s %10s" %
          ("|yaw_hizi| dps", "n", "K=0 |med|", "K=%.2f" % Kb, "kazanc"))
    for lo, hi in ((0, 5), (5, 15), (15, 30), (30, 200)):
        s = [r for r in g if lo <= abs(math.degrees(r["yaw_hizi"])) < hi]
        if len(s) < 30:
            continue
        e0 = [abs(math.degrees(BG.sarmala_pi(
            BG.azimut_ham(r["cx"]) - r["eps_truth"]))) for r in s]
        e1 = [abs(math.degrees(BG.sarmala_pi(
            BG.azimut_ham(r["cx"]) - Kb * r["yaw_hizi"] - r["eps_truth"])))
            for r in s]
        print("  %-16s %6d %10.2f %10.2f %9.0f%%" %
              ("%d-%d" % (lo, hi), len(s), med(e0), med(e1),
               100.0 * (med(e1) / max(med(e0), 1e-9) - 1.0)))

    s = [r for r in g if r["boyut"] >= 25.0]
    if len(s) >= 30:
        e0 = [abs(math.degrees(BG.sarmala_pi(
            BG.azimut_ham(r["cx"]) - r["eps_truth"]))) for r in s]
        e1 = [abs(math.degrees(BG.sarmala_pi(
            BG.azimut_ham(r["cx"]) - Kb * r["yaw_hizi"] - r["eps_truth"])))
            for r in s]
        print("\n  TERMINAL bandi (boyut >= 25 px), n=%d: %.2f -> %.2f deg"
              % (len(s), med(e0), med(e1)))
    return en_iyi


# ══════════════════════════════════════════════════════════════════════════
#  3. MENZIL KALIBRASYONU
# ══════════════════════════════════════════════════════════════════════════

def _ape(est, R):
    return 100.0 * abs(est - R) / R


def kiyas_menzil2(kayit, ayrinti=False):
    """MENZIL_PX_M ikizleri + K_w/w + additif pay -> medAPE / YANLILIK."""
    g = [r for r in kayit if r.get("ayna_sonrasi") and not r["kirpik"]
         and r["w"] > 1.0 and r["h"] > 1.0 and 0.5 < r["R"] < 200.0]
    print("\n" + "=" * 78)
    print(" MENZIL KALIBRASYONU  (n=%d kare, %d log)" %
          (len(g), len({r["log"] for r in g})))
    print("=" * 78)
    if len(g) < 200:
        print("  YETERSIZ VERI")
        return None

    k_b = med([r["R"] * r["boyut"] for r in g])
    k_w = med([r["R"] * r["w"] for r in g])
    k_h = med([r["R"] * r["h"] for r in g])
    print("\n  OLCULEN CARPANLAR (medyan, px*m)")
    print("      R*sqrt(w*h) = %.1f      R*w = %.1f      R*h = %.1f"
          % (k_b, k_w, k_h))
    print("      => kodun MENZIL_PX_M=202.6'si olculenden %+.0f%% BUYUK"
          % (100.0 * (202.6 / k_b - 1.0)))

    # additif-pay modelinin sabiti VERIDEN cikarilir (yanliligi 0'a getirir)
    k_of = med([r["R"] * (r["boyut"] + 4.11) for r in g])

    # ── ADDITIF PAYIN ISARETI: TURETMEDEN cikar, VERIDEN dogrula ──
    # Dedektor kutusu gercek siluetten SABIT c px BUYUKSE
    #     s_olculen = s_gercek + c = FX*L/R + c   =>   R*s_olculen = k + c*R
    # yani "R*boyut" R'de DOGRUSALDIR ve EGIMI c'dir. Tersi:
    #     R = k / (s - c)          <-- payda EKSI. `+c` yazmak TERS DUZELTIR.
    # c ve k'yi burada dogrudan REGRESYONLA cikariyoruz.
    _x = [r["R"] for r in g]
    _y = [r["R"] * r["boyut"] for r in g]
    _n = len(g)
    _xm, _ym = sum(_x) / _n, sum(_y) / _n
    _sxx = sum((a - _xm) ** 2 for a in _x)
    c_fit = (sum((a - _xm) * (b - _ym) for a, b in zip(_x, _y)) / _sxx
             if _sxx > 1e-9 else 0.0)
    k_fit = _ym - c_fit * _xm
    print("\n  ADDITIF PAY REGRESYONU:  R*boyut = k + c*R")
    print("      k = %.1f px*m   c = %+.2f px      =>  R = k / (boyut - c)"
          % (k_fit, c_fit))
    print("      ⚠ c > 0 -> paydada EKSI. '232.2/(boyut+4.11)' ISARETI TERSTIR;")
    print("        turetme de veri de `boyut - c` diyor.")

    modeller = [
        ("M0  kod  202.6 / sqrt(w*h)", lambda r: 202.6 / r["boyut"]),
        ("M0b kodun hardcoded IKIZI 160.0 / sqrt(w*h)",
         lambda r: 160.0 / r["boyut"]),
        ("M0c olculen %.1f / sqrt(w*h)" % k_b, lambda r: k_b / r["boyut"]),
        ("M5  K_w / w  (yalniz GENISLIK) K_w=%.1f" % k_w, lambda r: k_w / r["w"]),
        ("M6  232.2 / (sqrt(w*h) + 4.11)", lambda r: 232.2 / (r["boyut"] + 4.11)),
        ("M6b %.1f / (sqrt(w*h) + 4.11)  [yanlilik=0]" % k_of,
         lambda r: k_of / (r["boyut"] + 4.11)),
        ("M7  ★ %.1f / (sqrt(w*h) - %.2f)  [DOGRU ISARET]" % (k_fit, c_fit),
         lambda r: (k_fit / (r["boyut"] - c_fit)
                    if r["boyut"] - c_fit > 1e-6 else float("nan"))),
    ]

    print("\n  %-46s %8s %10s %8s %9s"
          % ("model", "medAPE", "yanlilik", "medAE(m)", "TERM AE"))
    print("  " + "-" * 86)
    for ad, fn in modeller:
        ape, yan, ae, tae = [], [], [], []
        for r in g:
            e = fn(r)
            if not math.isfinite(e) or e <= 0:
                continue
            ape.append(_ape(e, r["R"]))
            yan.append(100.0 * (e / r["R"] - 1.0))
            ae.append(abs(e - r["R"]))
            if r["R"] < 15.0:
                tae.append(abs(e - r["R"]))
        print("  %-46s %7.1f%% %+9.1f%% %8.2f %9.2f"
              % (ad, med(ape), med(yan), med(ae), med(tae)))
    print("      (TERM AE = truth menzil < 15 m olan karelerde medyan mutlak")
    print("       hata (m) -- terminal kararlarini BU band belirliyor)")

    print("\n  MENZIL DILIMLERINE GORE -- YANLILIK (%); 0'a yakin = KAYMA YOK")
    print("  %-12s %7s %9s %9s %9s %9s %9s %9s"
          % ("R bandi", "n", "R*boyut", "202.6", "%.0f/sq" % k_b,
             "K_w/w", "%.0f/(b+4)" % k_of, "%.0f/(b-%.1f)" % (k_fit, c_fit)))
    bant = []
    for lo, hi in ((3, 6), (6, 10), (10, 15), (15, 30), (30, 60), (60, 200)):
        s = [r for r in g if lo <= r["R"] < hi]
        if len(s) < 30:
            continue
        kb = med([r["R"] * r["boyut"] for r in s])
        y1 = med([100.0 * (202.6 / r["boyut"] / r["R"] - 1.0) for r in s])
        y0 = med([100.0 * (k_b / r["boyut"] / r["R"] - 1.0) for r in s])
        y2 = med([100.0 * (k_w / r["w"] / r["R"] - 1.0) for r in s])
        y3 = med([100.0 * (k_of / (r["boyut"] + 4.11) / r["R"] - 1.0) for r in s])
        y4 = med([100.0 * (k_fit / max(r["boyut"] - c_fit, 1e-6) / r["R"] - 1.0)
                  for r in s])
        bant.append((y0, y2, y3, y4))
        print("  %-12s %7d %9.1f %+8.1f%% %+8.1f%% %+8.1f%% %+8.1f%% %+8.1f%%"
              % ("%d-%d m" % (lo, hi), len(s), kb, y1, y0, y2, y3, y4))
    if len(bant) >= 3:
        def _yay(i):
            v = [b[i] for b in bant]
            return max(v) - min(v)
        print("      BANTLAR ARASI YAYILIM (kucuk = model menzille KAYMIYOR):")
        print("        %.0f/sqrt %.1f | K_w/w %.1f | %.0f/(b+4.11) %.1f "
              "| %.0f/(b-%.2f) %.1f  puan"
              % (k_b, _yay(0), _yay(1), k_of, _yay(2), k_fit, c_fit, _yay(3)))

    print("\n  TERMINAL NISAN KAPISI TUTARSIZLIGI (bbox_ibvs.py:2104)")
    t = [r for r in g if r["boyut"] >= 25.0]
    print("      terminal esigini (boyut>=25 px) gecen kare: n=%d" % len(t))
    if t:
        # ⚠ YANLILIK KARE BASINA olculur: med(est/R − 1). med(est)/med(R)
        #   YANLIS cevap verir (medyan bolmeyle degismez).
        mtr = med([r["R"] for r in t])
        print("      GERCEK menzil medyani            : %6.2f m" % mtr)
        for ad, fn in (("kapinin kullandigi 160.0/boyut", lambda r: 160.0 / r["boyut"]),
                       ("yasanin kullandigi 202.6/boyut", lambda r: 202.6 / r["boyut"]),
                       ("olculen %.1f/boyut" % k_b, lambda r: k_b / r["boyut"]),
                       ("K_w/w  (%.1f)" % k_w, lambda r: k_w / r["w"])):
            yy = med([100.0 * (fn(r) / r["R"] - 1.0) for r in t])
            print("      %-32s : %6.2f m  (yanlilik %+.0f%%)"
                  % (ad, med([fn(r) for r in t]), yy))
        yy = med([100.0 * (160.0 / r["boyut"] / r["R"] - 1.0) for r in t])
        print("      => bu bandin KARE BASINA en iyi sabiti ~%.0f px*m"
              % (160.0 / (1.0 + yy / 100.0)))

        print("\n  ⚠⚠ KOSULLANDIRMA TUZAGI -- IKI ISTATISTIK TERS SOYLUYOR")
        print("     R'ye gore kosullandirinca (ust tablo)  : 202.6, 3-6 m'de +53% SISIK")
        print("     boyut>=25'e gore kosullandirinca       : 202.6 yalniz %+.0f%% sapiyor"
              % med([100.0 * (202.6 / r["boyut"] / r["R"] - 1.0) for r in t]))
        print("     SEBEP: kapi `boyut`a bakarak aciliyor. boyut>=25 secimi, kutunun")
        print("     RASGELE BUYUK ciktigi kareleri toplar (Berkson secilimi); o")
        print("     karelerde k/boyut zaten dusuk cikar. Yani AYNI sabit, R'ye")
        print("     gore SISIK, boyut'a gore DENGELI olabilir. IKISI DE dogru --")
        print("     ama KAPININ hukmu boyut kosullusudur.")

        # OPERASYONEL SORU: kapi ne siklikta aciliyor?
        _mx = 2.0          # Cfg.TERM_NISAN_MAX_M varsayilani
        print("\n  NISAN KAPISI GECIS ORANI  (yanal = menzil*|tan eps| <= %.1f m)"
              % _mx)
        for ad, fn in (("truth R (hakem)", lambda r: r["R"]),
                       ("160.0/boyut (bugunku kapi)", lambda r: 160.0 / r["boyut"]),
                       ("202.6/boyut (yasa ile esit)", lambda r: 202.6 / r["boyut"]),
                       ("153.1/boyut (olculen)", lambda r: k_b / r["boyut"]),
                       ("K_w/w  (%.1f)" % k_w, lambda r: k_w / r["w"])):
            gec = sum(1 for r in t
                      if fn(r) * abs(math.tan(BG.azimut_ham(r["cx"]))) <= _mx)
            print("      %-30s : %5.1f%% (%d/%d)"
                  % (ad, 100.0 * gec / len(t), gec, len(t)))
        print("      ⇒ hakemle (truth) arasindaki fark, kapinin YANLIS ACMA /")
        print("        YANLIS KAPAMA oranidir. 160.0 menzili KUCUK sayar ->")
        print("        yanal sapmayi KUCUK sayar -> kapiyi GEVSETIR.")

        # KARE BAZINDA UYUSMAZLIK: marjinal oran degil, KARAR ESLESMESI
        hak = [abs(math.tan(BG.azimut_ham(r["cx"]))) * r["R"] <= _mx for r in t]
        print("\n  KARE BAZINDA UYUSMAZLIK (hakemle AYNI karari vermeme orani)")
        print("      %-10s %10s %12s %12s %12s"
              % ("sabit", "gecis %", "uyusmazlik", "YANLIS AC", "YANLIS KAPA"))
        en = None
        for K in (140, 153, 160, 170, 180, 190, 196, 202.6, 210, 220):
            ya = yk = 0
            for r, ht in zip(t, hak):
                gg = (K / r["boyut"]) * abs(math.tan(BG.azimut_ham(r["cx"]))) <= _mx
                if gg and not ht:
                    ya += 1
                elif ht and not gg:
                    yk += 1
            u = 100.0 * (ya + yk) / len(t)
            if en is None or u < en[1]:
                en = (K, u)
            print("      %-10.1f %9.1f%% %11.1f%% %11.1f%% %11.1f%%"
                  % (K, 100.0 * sum(1 for r in t
                                    if (K / r["boyut"])
                                    * abs(math.tan(BG.azimut_ham(r["cx"]))) <= _mx)
                     / len(t), u, 100.0 * ya / len(t), 100.0 * yk / len(t)))
        print("      ⇒ EN AZ UYUSMAZLIK: %.1f px*m (%.1f%%)" % en)
        print("        ⚠ Bu sayi TERMINAL kapisi icindir; yasanin geri kalani")
        print("          (kapanma, YANAL_K, DPP_K_R) R'ye kosullu calisiyor ve")
        print("          orada olculen sabit %.1f. IKISI AYNI OLMAK ZORUNDA DEGIL"
              % k_b)
        print("          -- MENZIL_TERM_PX_M'in ayri kalmasinin gerekcesi budur.")

    print("\n  KAPANMA KESTIRIMI:  rdot = R*(dboyut/dt)/boyut  ->  R ile DOGRUSAL")
    print("      202.6 -> %.1f  olcek = %.3f kat (kestirim bu kadar KUCULMELI)"
          % (k_b, k_b / 202.6))
    return {"k_b": k_b, "k_w": k_w, "k_h": k_h}


# ══════════════════════════════════════════════════════════════════════════
#  4. MEKANIZMA KAPILARI -- YAMALARIN KENDISI
# ══════════════════════════════════════════════════════════════════════════

def _env_oku(env):
    """ENV PLUMBING SINAVI: verilen env ile TAZE yukleyip Cfg degerlerini alir.

    ⚠ TUZAK (bu tezgahta bir kez dusuldu): `importlib.reload` AYNI modul
      nesnesini yeniden doldurur. Iki farkli env icin iki degisken tutarsan
      IKISI DE SON reload'a bakar ve "fark yok" diye YANLIS gecer.
      Bu yuzden burada YALNIZ SAYILAR okunur, modul TASINMAZ; davranis
      kiyaslari `_cfg()` ile (Cfg alt sinifi) yapilir.
    """
    import importlib
    eski = {}
    for k, v in (env or {}).items():
        eski[k] = os.environ.get(k)
        os.environ[k] = str(v)
    try:
        import control.guidance.bbox_ibvs as bi
        importlib.reload(bi)
        return {k: getattr(bi.Cfg, k, None) for k in
                ("KOMUT_HIZALA_S", "KOMUT_HIZALA_MAX_DEG", "MENZIL_PX_M",
                 "MENZIL_TERM_PX_M", "MENZIL_KW", "MENZIL_OFS_PX")}
    finally:
        for k, v in eski.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        import control.guidance.bbox_ibvs as bi
        importlib.reload(bi)          # varsayilanlara GERI DON


def _yasa(env=None):
    """Modulu env'siz taze yukler (varsayilan davranis)."""
    import importlib
    import control.guidance.bbox_ibvs as bi
    importlib.reload(bi)
    return bi


def _cfg(bi, **kw):
    """Cfg'nin TEK ALANI degistirilmis alt sinifi -- reload aliasing YOK."""
    return type("CfgDeney", (bi.Cfg,), dict(kw))


def _cagir(bi, cfg=None, yaw_hizi=0.0, cx=380.0, cy=301.0, w=30.0, h=22.0,
           terminal=False):
    return bi.komut(cx, cy, w, h, 0.0, 18.0, 0.05, cfg or bi.Cfg, terminal,
                    (0.0, 0.0), 0.0, 0.0, None, 0.0, yaw_hizi, None, 0.0, None)


def kapilar():
    print("\n" + "=" * 78)
    print(" MEKANIZMA KAPILARI")
    print("=" * 78)
    ok = True

    bi = _yasa()
    w_, h_ = 30.0, 22.0
    b_ = math.sqrt(w_ * h_)

    # ── K1: VARSAYILANLAR + BIT-AYNILIK ──
    print("\n  K1  VARSAYILAN BIT-AYNILIK  (env'siz taze yukleme)")
    d = _env_oku({})
    for ad, bek in (("KOMUT_HIZALA_S", 0.0), ("MENZIL_PX_M", 202.6),
                    ("MENZIL_TERM_PX_M", 160.0), ("MENZIL_KW", 0.0),
                    ("MENZIL_OFS_PX", 0.0)):
        v = d[ad] is not None and abs(d[ad] - bek) < 1e-12
        print("      Cfg.%-18s = %-8s (beklenen %-6s)  %s"
              % (ad, d[ad], bek, "GECTI" if v else "KALDI"))
        ok = ok and v
    y = [_cagir(bi, yaw_hizi=w)[3] for w in (-0.6, 0.0, 0.6)]
    v = abs(y[0] - y[1]) < 1e-15 and abs(y[2] - y[1]) < 1e-15
    print("      yaw_cmd, yaw_hizi -0.6/0/+0.6 rad/s icin AYNI: %s"
          % ("GECTI" if v else "KALDI"))
    ok = ok and v
    r_tab = bi.menzil_kutudan(b_, bi.Cfg, w_)
    r_trm = bi.menzil_kutudan(b_, bi.Cfg, w_, terminal_kapi=True)
    v = abs(r_tab - 202.6 / b_) < 1e-12 and abs(r_trm - 160.0 / b_) < 1e-12
    print("      menzil_kutudan ana=%.4f (202.6/b=%.4f) term=%.4f (160/b=%.4f) %s"
          % (r_tab, 202.6 / b_, r_trm, 160.0 / b_, "GECTI" if v else "KALDI"))
    ok = ok and v
    v = abs(bi.menzil_olcek(b_, bi.Cfg, w_) - b_) < 1e-15
    print("      menzil_olcek == sqrt(w*h) (turev tabani degismedi): %s"
          % ("GECTI" if v else "KALDI"))
    ok = ok and v

    # ── K2: ENV PLUMBING ──
    print("\n  K2  ENV KAPILARI GERCEKTEN OKUNUYOR MU")
    for env, ad, bek in (
            ({"AVCI_IBVS_KOMUT_HIZALA": "0.20"}, "KOMUT_HIZALA_S", 0.20),
            ({"AVCI_IBVS_MENZIL_PX": "153.0"}, "MENZIL_PX_M", 153.0),
            ({"AVCI_IBVS_MENZIL_TERM_PX": "153.0"}, "MENZIL_TERM_PX_M", 153.0),
            ({"AVCI_IBVS_MENZIL_KW": "241.8"}, "MENZIL_KW", 241.8),
            ({"AVCI_IBVS_MENZIL_OFS": "-4.11"}, "MENZIL_OFS_PX", -4.11)):
        g = _env_oku(env)[ad]
        v = g is not None and abs(g - bek) < 1e-12
        print("      %-32s -> Cfg.%-18s = %-8s %s"
              % (list(env)[0], ad, g, "GECTI" if v else "KALDI"))
        ok = ok and v
    d = _env_oku({})
    v = abs(d["KOMUT_HIZALA_S"]) < 1e-12 and abs(d["MENZIL_PX_M"] - 202.6) < 1e-12
    print("      env geri alindiktan sonra varsayilanlar SAGLAM: %s"
          % ("GECTI" if v else "KALDI"))
    ok = ok and v

    # ── K3: KOMUT_HIZALA IMZASI ──
    print("\n  K3  KOMUT_HIZALA=0.20 imzasi (isaret TERS, buyukluk K*yaw_hizi)")
    C = _cfg(bi, KOMUT_HIZALA_S=0.20)
    print("      %-10s %14s %14s %12s %12s"
          % ("yaw_hizi", "yaw_cmd(0)", "yaw_cmd(0.20)", "fark deg", "hizala_deg"))
    farklar = []
    for w in (-0.6, -0.2, 0.0, 0.2, 0.6):
        a = _cagir(bi, yaw_hizi=w)
        b = _cagir(bi, cfg=C, yaw_hizi=w)
        dd = math.degrees(BG.sarmala_pi(b[3] - a[3]))
        hz = math.degrees(b[5]["hizala"])
        farklar.append((w, dd, hz))
        print("      %-10.2f %14.4f %14.4f %+12.4f %+12.4f"
              % (w, math.degrees(a[3]), math.degrees(b[3]), dd, hz))
    v = all(abs(dd - math.degrees(-0.20 * w)) < 1e-9 for w, dd, _ in farklar)
    print("      fark == -0.20*yaw_hizi           : %s" % ("GECTI" if v else "KALDI"))
    ok = ok and v
    v = all(dd * w < -1e-9 for w, dd, _ in farklar if abs(w) > 1e-9)
    print("      isaret donus hiziyla TERS        : %s" % ("GECTI" if v else "KALDI"))
    ok = ok and v
    # tani["hizala"] logdaki kapiyla tutarli mi
    v = all(abs(hz - math.degrees(0.20 * w)) < 1e-9 for w, _, hz in farklar)
    print("      tani['hizala'] == +0.20*yaw_hizi : %s" % ("GECTI" if v else "KALDI"))
    ok = ok and v
    # tavan bagliyor mu (patlama kalkani)
    C2 = _cfg(bi, KOMUT_HIZALA_S=0.20, KOMUT_HIZALA_MAX_DEG=5.0)
    hz = math.degrees(_cagir(bi, cfg=C2, yaw_hizi=3.0)[5]["hizala"])
    v = abs(hz - 5.0) < 1e-9
    print("      tavan 5 deg, yaw_hizi 3 rad/s -> hizala %.3f deg  %s"
          % (hz, "GECTI" if v else "KALDI"))
    ok = ok and v

    # ── K4: MENZIL MODELLERI ──
    print("\n  K4  MENZIL MODELLERI ve IKIZIN KAPANMASI")
    Ck = _cfg(bi, MENZIL_KW=241.8)
    a1 = bi.menzil_kutudan(b_, Ck, w_)
    a2 = bi.menzil_kutudan(b_, Ck, w_, terminal_kapi=True)
    v = abs(a1 - 241.8 / w_) < 1e-12 and abs(a2 - a1) < 1e-12
    print("      KW=241.8 -> ana=%.4f term=%.4f (ikisi de 241.8/w=%.4f)  %s"
          % (a1, a2, 241.8 / w_, "GECTI" if v else "KALDI"))
    ok = ok and v
    v = abs(bi.menzil_olcek(b_, Ck, w_) - w_) < 1e-12
    print("      KW acikken turev tabani da w (tutarli rdot): %s"
          % ("GECTI" if v else "KALDI"))
    ok = ok and v
    Co = _cfg(bi, MENZIL_PX_M=232.2, MENZIL_OFS_PX=-4.11)
    a3 = bi.menzil_kutudan(b_, Co, w_)
    v = abs(a3 - 232.2 / (b_ + 4.11)) < 1e-9
    print("      PX=232.2 OFS=-4.11 -> %.4f m (232.2/(b+4.11)=%.4f)  %s"
          % (a3, 232.2 / (b_ + 4.11), "GECTI" if v else "KALDI"))
    ok = ok and v
    Ce = _cfg(bi, MENZIL_PX_M=153.0, MENZIL_TERM_PX_M=153.0)
    v = abs(bi.menzil_kutudan(b_, Ce, w_)
            - bi.menzil_kutudan(b_, Ce, w_, terminal_kapi=True)) < 1e-15
    print("      PX=TERM=153.0 -> yasa ile kapi AYNI menzil: %s"
          % ("GECTI" if v else "KALDI"))
    ok = ok and v

    # ── K5: KAPANMA KESTIRIMI OLCEGI ──
    print("\n  K5  KAPANMA KESTIRIMI OLCEGI (202.6 -> 153.0 = %.4f kat)"
          % (153.0 / 202.6))
    Cm = _cfg(bi, MENZIL_PX_M=153.0)
    r1 = bi.menzil_kutudan(b_, bi.Cfg, w_)
    r2 = bi.menzil_kutudan(b_, Cm, w_)
    v = abs(r2 / r1 - 153.0 / 202.6) < 1e-12
    print("      %.4f -> %.4f m  olcek %.4f  %s"
          % (r1, r2, r2 / r1, "GECTI" if v else "KALDI"))
    ok = ok and v
    # tani['menzil'] sutunu da ayni olcegi tasimali (log kapisi)
    m1 = _cagir(bi, yaw_hizi=0.0)[5]["menzil"]
    m2 = _cagir(bi, cfg=Cm, yaw_hizi=0.0)[5]["menzil"]
    v = abs(m2 / m1 - 153.0 / 202.6) < 1e-12
    print("      log sutunu menzil_m: %.4f -> %.4f (olcek %.4f)  %s"
          % (m1, m2, m2 / m1, "GECTI" if v else "KALDI"))
    ok = ok and v
    mt = _cagir(bi, yaw_hizi=0.0)[5]["menzil_term"]
    v = abs(m1 / mt - 202.6 / 160.0) < 1e-12
    print("      TABAN kosuda menzil_m/menzil_term = %.4f (202.6/160=%.4f) %s"
          % (m1 / mt, 202.6 / 160.0, "GECTI" if v else "KALDI"))
    ok = ok and v

    print("\n  SONUC: %s"
          % ("TUM KAPILAR GECTI" if ok else "EN AZ BIR KAPI KALDI"))
    return ok


# ══════════════════════════════════════════════════════════════════════════
#  4b. BIT-AYNILIK: YAMALI KOD vs YEDEK  (en guclu kapi)
# ══════════════════════════════════════════════════════════════════════════

def bitayni(yedek_yolu=None, n=4000):
    """`komut()` ciktisini YAMA ONCESI dosyayla RASGELE girdilerde kiyaslar.

    ⚠ "Varsayilan degismedi" iddiasi ancak boyle KANITLANIR. Cfg'ye bakmak
      yetmez: kod yolu degistiyse ayni Cfg farkli sayi uretebilir.
    Kiyas TAM ESITLIK (==) ile yapilir, tolerans YOK.
    """
    import importlib.util
    import random

    if yedek_yolu is None:
        kok = os.path.join(KOK, "yedek")
        aday = []
        for d in os.listdir(kok):
            p = os.path.join(kok, d, "kod", "bbox_ibvs.py")
            if os.path.exists(p):
                aday.append(p)
            p2 = os.path.join(kok, d, "kod",
                              "kopru__gazebo_kaynak__control__guidance",
                              "bbox_ibvs.py")
            if os.path.exists(p2):
                aday.append(p2)
        if not aday:
            print("  YEDEK BULUNAMADI -> BIT-AYNILIK SINANAMADI")
            return None
        aday.sort(key=os.path.getmtime)
        yedek_yolu = aday[-1]

    print("\n" + "=" * 78)
    print(" BIT-AYNILIK  (yama oncesi yedek ile)")
    print("=" * 78)
    print("  yedek: %s" % yedek_yolu)

    spec = importlib.util.spec_from_file_location("_bbox_ibvs_yedek", yedek_yolu)
    eski = importlib.util.module_from_spec(spec)
    sys.modules["_bbox_ibvs_yedek"] = eski
    spec.loader.exec_module(eski)
    yeni = _yasa()

    rnd = random.Random(20260817)
    kotu = 0
    ornek = None
    for _ in range(n):
        a = dict(
            cx=rnd.uniform(20, 620), cy=rnd.uniform(20, 460),
            w=rnd.uniform(7, 120), h=rnd.uniform(5, 90),
            iris_yaw=rnd.uniform(-math.pi, math.pi),
            hiz_I=rnd.uniform(0, 30), dt=rnd.uniform(0.02, 0.2),
            terminal=rnd.random() < 0.3,
            los_hiz=(rnd.uniform(-2, 2), rnd.uniform(-1, 1)),
            iris_pitch=rnd.uniform(-0.6, 0.4), iris_vz=rnd.uniform(-5, 5),
            kapanma=(None if rnd.random() < 0.2 else rnd.uniform(-10, 15)),
            iris_roll=rnd.uniform(-0.7, 0.7),
            yaw_hizi=rnd.uniform(-1.2, 1.2),
            psi_v=(None if rnd.random() < 0.2 else rnd.uniform(-math.pi, math.pi)),
            eps_hizi=rnd.uniform(-3, 3),
            v_kapi=(None if rnd.random() < 0.5 else rnd.uniform(10, 25)),
        )
        arg = (a["cx"], a["cy"], a["w"], a["h"], a["iris_yaw"], a["hiz_I"],
               a["dt"])
        kw = (a["terminal"], a["los_hiz"], a["iris_pitch"], a["iris_vz"],
              a["kapanma"], a["iris_roll"], a["yaw_hizi"], a["psi_v"],
              a["eps_hizi"], a["v_kapi"])
        e = eski.komut(*arg, eski.Cfg, *kw)
        y = yeni.komut(*arg, yeni.Cfg, *kw)
        if e[:5] != y[:5]:
            kotu += 1
            if ornek is None:
                ornek = (a, e[:5], y[:5])
    print("  n=%d rasgele cagri  ->  FARKLI: %d" % (n, kotu))
    if ornek:
        print("  ORNEK FARK: %s\n     eski=%s\n     yeni=%s" % ornek)
    print("  -> %s" % ("GECTI (BIT-AYNI)" if kotu == 0 else "KALDI"))
    return kotu == 0


# ══════════════════════════════════════════════════════════════════════════
#  5. CLI
# ══════════════════════════════════════════════════════════════════════════

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yaw", action="store_true")
    ap.add_argument("--menzil", action="store_true")
    ap.add_argument("--kapi", action="store_true")
    ap.add_argument("--bitayni", action="store_true")
    ap.add_argument("--yedek", default=None)
    ap.add_argument("--hepsi", action="store_true")
    ap.add_argument("--log-sayisi", type=int, default=400)
    ap.add_argument("--conf", type=float, default=0.35)
    ap.add_argument("--gecikme-s", type=float, default=BG.DEDEKTOR_GECIKME_S)
    ap.add_argument("--ayrinti", action="store_true")
    a = ap.parse_args()
    if not any((a.yaw, a.menzil, a.kapi, a.bitayni, a.hepsi)):
        a.hepsi = True

    if a.kapi or a.hepsi:
        kapilar()
    if a.bitayni or a.hepsi:
        bitayni(a.yedek)

    if a.yaw or a.menzil or a.hepsi:
        print("\n[veri] hedef_iz + bbox_ibvs birlestiriliyor "
              "(D=%.2f s, conf>=%.2f)..." % (a.gecikme_s, a.conf))
        kayit, damga = BK.veri_topla(a.gecikme_s, a.log_sayisi, a.conf,
                                     a.ayrinti)
        print("[veri] n=%d kare / %d log" % (len(kayit), len(damga)))
        n = yaw_hizi_ekle(kayit)
        print("[veri] canli EMA yaw_hizi eslesen kare: %d (%.1f%%)"
              % (n, 100.0 * n / max(len(kayit), 1)))
        if a.yaw or a.hepsi:
            kiyas_yaw(kayit, a.ayrinti)
        if a.menzil or a.hepsi:
            kiyas_menzil2(kayit, a.ayrinti)


if __name__ == "__main__":
    main()

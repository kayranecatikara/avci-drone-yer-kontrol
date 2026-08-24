# -*- coding: utf-8 -*-
"""
================================================================================
  BBOX KONTROL TEZGAHI  --  bbox_geometri.py'nin KOR sinavi
================================================================================
NE YAPAR
--------------------------------------------------------------------------------
  --veri        GERCEK ucus loglarindan geometri uretip her formulasyonu
                TRUTH'a karsi kiyaslar (acik dongu, kor).
  --kararlilik  Yaw kanalinin OLCULEN gecikmesiyle kazanc/faz payi taramasi.
  --cevrim      Kapali cevrim benzetimi (olculen kanal + ivme tavanlari) ->
                iska dagilimi.
  --hepsi       ucu birden.

⛔ OYUNA DOKUNMAZ. Yalnizca diskteki CSV'leri OKUR. Port 12345'e baglanmaz,
   hicbir sureci baslatmaz/oldurmez. Kampanya kosarken guvenle calisir.

================================================================================
 TRUTH NEREDEN GELIYOR -- ve NEREDEN GELMIYOR
================================================================================
✔ KULLANILAN:  veri/hedef_iz/hedef_iz_*.csv
   `drone.get_debug_truth()` ciktisi: oyunun KENDI temiz konumu (~30 Hz),
   200 Hz yoklanip konum DEGISTIGINDE yaziliyor. Birim cm -> m. Cerceve:
   OYUN DUNYASI (DoW), aynalanmamis.

⛔ KULLANILMAYAN: karar_*.csv'nin `u_truth`/`v_truth` sutunlari.
   Adi yaniltici: bunlar gps_guidance'in `est_x/y/z` EMA KESTIRIMININ
   Gazebo kamera modeliyle (HFOV 125!) projeksiyonudur -- GPS gurultusu,
   EMA gecikmesi ve YANLIS ic parametre tasirlar. Kalibrasyon hakemi
   olamazlar. (algi_sureklilik.py:250-253 bunu kendi de yaziyor.)

⛔ KULLANILMAYAN: hedef_iz'in `d_vz` sutunu -- +0.240 m/s yanli, bagimsiz
   truth degil (konum turevi kullanilir).

================================================================================
 ⚠ AYNA ERASI KAPISI  (bu tezgahin en onemli kapisi)
================================================================================
kopru/tespit_akisi.py'deki YATAY AYNA duzeltmesi 2026-08-17 sabahi girdi.
ONCESINDEKI loglarda `cx` TERS isaretlidir. Ikisini karistirmak yatay
kalibrasyonu tamamen bozar.
Tezgah bunu TARIHE GORE DEGIL, VERIDEN kendi bulur: her log icin
`corr(eps_kutu, eps_truth)` isaretine bakar; negatifse "AYNA ONCESI" damgasi
vurur ve yatay istatistiklerden CIKARIR (dikey/menzil icin tutar --
ayna dikeyi degistirmez).
================================================================================
"""

from __future__ import annotations

import argparse
import csv
import glob
import math
import os
import sys

# Windows konsolu cp1252; UTF-8'e cevir yoksa ⚠/° karakterleri patlatir.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "kopru", "gazebo_kaynak"))

from control.guidance import bbox_geometri as BG          # noqa: E402

try:
    import numpy as np
except ImportError:                                        # pragma: no cover
    np = None

IZ_DIR = os.path.join(KOK, "veri", "hedef_iz")
LOG_DIR = os.path.join(KOK, "kopru", "gazebo_kaynak", "logs")

# menzil_model.py (arac/) opsiyonel -- varsa rakip olarak yarisir
try:
    sys.path.insert(0, os.path.join(KOK, "arac"))
    import menzil_model as MM                              # noqa: E402
except Exception:
    MM = None


# ══════════════════════════════════════════════════════════════════════════
#  YARDIMCILAR
# ══════════════════════════════════════════════════════════════════════════

def _f(s, vars=float("nan")):
    try:
        v = float(s)
        return v if math.isfinite(v) else vars
    except (TypeError, ValueError):
        return vars


def yuzdelik(a, p):
    """Saf yuzdelik (numpy yoksa da calissin diye ayri)."""
    if np is not None:
        return float(np.percentile(a, p)) if len(a) else float("nan")
    b = sorted(a)
    if not b:
        return float("nan")
    k = (len(b) - 1) * p / 100.0
    lo, hi = int(math.floor(k)), int(math.ceil(k))
    return b[lo] if lo == hi else b[lo] * (hi - k) + b[hi] * (k - lo)


def ozet(ad, hata, birim="deg", ek=""):
    """Hata dagiliminin tek satirlik ozeti."""
    if not len(hata):
        return "%-26s  ORNEK YOK" % ad
    a = [abs(x) for x in hata]
    med = yuzdelik(hata, 50)
    return ("%-26s n=%-6d yanlilik %+7.2f  |med| %6.2f  p90 %7.2f  p95 %7.2f %s %s"
            % (ad, len(hata), med, yuzdelik(a, 50), yuzdelik(a, 90),
               yuzdelik(a, 95), birim, ek))


# ══════════════════════════════════════════════════════════════════════════
#  1. VERI: hedef_iz (truth) + bbox_ibvs (piksel) ZAMANDA BIRLESTIRME
# ══════════════════════════════════════════════════════════════════════════

def iz_yukle(yol):
    """hedef_iz CSV -> zaman sirali truth dizileri (DoW oyun cercevesi, m)."""
    t, hx, hy, hz, dx, dy, dz = [], [], [], [], [], [], []
    dr, dp, dyaw = [], [], []
    with open(yol, "r", encoding="utf-8", errors="replace") as f:
        for row in csv.DictReader(f):
            tm = _f(row.get("t_mutlak"))
            if not math.isfinite(tm):
                continue
            a = _f(row.get("hx_m")); b = _f(row.get("hy_m")); c = _f(row.get("hz_m"))
            d = _f(row.get("dx_m")); e = _f(row.get("dy_m")); g = _f(row.get("dz_m"))
            if not all(math.isfinite(v) for v in (a, b, c, d, e, g)):
                continue
            t.append(tm); hx.append(a); hy.append(b); hz.append(c)
            dx.append(d); dy.append(e); dz.append(g)
            dr.append(_f(row.get("d_roll"))); dp.append(_f(row.get("d_pitch")))
            dyaw.append(_f(row.get("d_yaw")))
    if len(t) < 20:
        return None
    return {"t": t, "hx": hx, "hy": hy, "hz": hz, "dx": dx, "dy": dy, "dz": dz,
            "d_roll": dr, "d_pitch": dp, "d_yaw": dyaw,
            "t0": t[0], "t1": t[-1]}


def _interp(tq, t, v):
    """Dogrusal interpolasyon (numpy varsa vektorel)."""
    if np is not None:
        return np.interp(tq, t, v)
    out = []
    for q in tq:
        if q <= t[0]:
            out.append(v[0]); continue
        if q >= t[-1]:
            out.append(v[-1]); continue
        lo, hi = 0, len(t) - 1
        while hi - lo > 1:
            m = (lo + hi) // 2
            if t[m] <= q:
                lo = m
            else:
                hi = m
        w = (q - t[lo]) / max(t[hi] - t[lo], 1e-12)
        out.append(v[lo] * (1 - w) + v[hi] * w)
    return out


def yasa_yukle(yol, conf_min=0.35):
    """bbox_ibvs CSV -> GERCEK TESPITLI kareler (yasa cercevesi pikseli)."""
    t, cx, cy, w, h = [], [], [], [], []
    roll, pitch, yaw, durum, boyut = [], [], [], [], []
    with open(yol, "r", encoding="utf-8", errors="replace") as f:
        for row in csv.DictReader(f):
            if (row.get("kopru") or "0").strip() not in ("0", "False", ""):
                continue                                   # HAYALET kare -> at
            tt = _f(row.get("t"))
            a = _f(row.get("cx")); b = _f(row.get("cy"))
            ww = _f(row.get("w")); hh = _f(row.get("h"))
            cf = _f(row.get("conf"), 0.0)
            if not all(math.isfinite(v) for v in (tt, a, b, ww, hh)):
                continue
            if ww <= 1.0 or hh <= 1.0 or cf < conf_min:
                continue
            t.append(tt); cx.append(a); cy.append(b); w.append(ww); h.append(hh)
            roll.append(math.radians(_f(row.get("iris_roll_deg"), 0.0)))
            pitch.append(math.radians(_f(row.get("iris_pitch_deg"), 0.0)))
            yaw.append(math.radians(_f(row.get("iris_yaw_deg"), 0.0)))
            durum.append((row.get("durum") or "").strip())
            boyut.append(math.sqrt(max(ww, 0.0) * max(hh, 0.0)))
    if not t:
        return None
    return {"t": t, "cx": cx, "cy": cy, "w": w, "h": h, "roll": roll,
            "pitch": pitch, "yaw": yaw, "durum": durum, "boyut": boyut,
            "t0": t[0], "t1": t[-1]}


def birlestir(yasa, iz, gecikme_s):
    """Yasa karelerini truth'la esler. Piksel t'de, truth (t - gecikme)'de.

    NEDEN GECIKME: dedektor gecikmesi olculdu ~0.20-0.25 s (gecikme taramasi
    tepesi D=0.20'de egim 1.041). Yani karedeki piksel, dunyanin GECMISTEKI
    halidir. Gecikmeyi yok sayarsan yatay hatayi hedefin donus hiziyla
    orantili bir terimle SISIRIRSIN ve "geometri yanlis" diye yanlis
    teshis koyarsin.
    """
    tq = [x - gecikme_s for x in yasa["t"]]
    hx = _interp(tq, iz["t"], iz["hx"]); hy = _interp(tq, iz["t"], iz["hy"])
    hz = _interp(tq, iz["t"], iz["hz"]); dx = _interp(tq, iz["t"], iz["dx"])
    dy = _interp(tq, iz["t"], iz["dy"]); dz = _interp(tq, iz["t"], iz["dz"])
    # ⚠ ZAMAN HIZALAMASI: piksel t-D anina aittir, ama yasa t anindaki tutumu
    # kullanir. Yaw'daki bu kayma DOGRUDAN azimut hatasina biner (38 deg/s
    # donuste 0.2 s = 7.6 deg). GEOMETRIYI zamandan ayirmak icin yasanin kendi
    # tutum serisi de t-D'ye interpole edilir -> "hizali" kestirim.
    _yh = [BG.sarmala_pi(a) for a in yasa["yaw"]]
    _un = []                                   # yaw'i sarmadan ac (unwrap)
    for a in _yh:
        _un.append(a if not _un else _un[-1] + BG.sarmala_pi(a - _un[-1]))
    yaw_h = _interp(tq, yasa["t"], _un)
    roll_h = _interp(tq, yasa["t"], yasa["roll"])
    pitch_h = _interp(tq, yasa["t"], yasa["pitch"])
    # hedefin rotasi (aspect icin) — konum turevinden, +-0.25 s pencere
    hx_i = _interp([x + 0.25 for x in tq], iz["t"], iz["hx"])
    hy_i = _interp([x + 0.25 for x in tq], iz["t"], iz["hy"])
    hx_g = _interp([x - 0.25 for x in tq], iz["t"], iz["hx"])
    hy_g = _interp([x - 0.25 for x in tq], iz["t"], iz["hy"])

    out = []
    n = len(yasa["t"])
    for i in range(n):
        # ── kadraj disi / bayat interpolasyon kapisi ──
        if not (iz["t0"] <= tq[i] <= iz["t1"]):
            continue
        # DoW -> NED (yasa cercevesi): N=+x, E=-y, D=-z
        N = hx[i] - dx[i]
        E = -(hy[i] - dy[i])
        U = hz[i] - dz[i]
        R = math.sqrt(N * N + E * E + U * U)
        if not (0.5 < R < 200.0):
            continue
        az_dunya = math.atan2(E, N)
        eps_truth = BG.sarmala_pi(az_dunya - yasa["yaw"][i])
        el_truth = math.atan2(U, math.hypot(N, E))
        # hedefin rotasi ve ASPECT (LOS ile hedef ekseni arasindaki aci)
        vhx = hx_i[i] - hx_g[i]
        vhy = hy_i[i] - hy_g[i]
        aspect = float("nan")
        if math.hypot(vhx, vhy) > 0.5:                     # >1 m/s
            rot = math.atan2(-vhy, vhx)                    # NED kursu
            # hedeften BIZE bakan yon
            los_geri = math.atan2(-E, -N)
            aspect = abs(BG.sarmala_pi(los_geri - rot))
        _x, _y, _ = BG.piksel_isin(yasa["cx"][i], yasa["cy"][i])
        out.append({
            "t": yasa["t"][i], "cx": yasa["cx"][i], "cy": yasa["cy"][i],
            "w": yasa["w"][i], "h": yasa["h"][i], "boyut": yasa["boyut"][i],
            "roll": yasa["roll"][i], "pitch": yasa["pitch"][i],
            "yaw": yasa["yaw"][i], "durum": yasa["durum"][i],
            "roll_h": roll_h[i], "pitch_h": pitch_h[i],
            "eps_truth_h": BG.sarmala_pi(az_dunya - yaw_h[i]),
            "R": R, "eps_truth": eps_truth, "el_truth": el_truth,
            "dz_truth": U, "aspect": aspect,
            "alfa": math.degrees(math.atan(math.hypot(_x, _y))),
            "kirpik": BG.kutu_kirpik(yasa["cx"][i], yasa["cy"][i],
                                     yasa["w"][i], yasa["h"][i]),
        })
    return out


# ── ONBELLEK: gecikme taramasi ayni dosyalari 6-8 kez okuyor. hedef_iz
#    klasoru 250 MB; onbelleksiz tarama dakikalar yerine SAATLER surer ve
#    kampanyanin CPU'sunu bosuna yer. Anahtar: (yol, conf).
_IZ_ONBELLEK = {}
_YASA_ONBELLEK = {}


def _izleri_al():
    if "_" not in _IZ_ONBELLEK:
        izler = []
        for p in sorted(glob.glob(os.path.join(IZ_DIR, "hedef_iz_*.csv"))):
            try:
                z = iz_yukle(p)
            except Exception:
                z = None
            if z:
                izler.append(z)
        izler.sort(key=lambda z: z["t0"])
        _IZ_ONBELLEK["_"] = izler
    return _IZ_ONBELLEK["_"]


def veri_topla(gecikme_s=BG.DEDEKTOR_GECIKME_S, en_fazla_log=400,
               conf_min=0.35, ayrinti=False):
    """Butun ortusen (yasa, iz) ciftlerini birlestirip tek liste dondurur."""
    izler = _izleri_al()
    if not izler:
        return [], {}

    loglar = sorted(glob.glob(os.path.join(LOG_DIR, "bbox_ibvs_*.csv")),
                    key=os.path.getsize, reverse=True)[:en_fazla_log]
    kayit, damga = [], {}
    for p in loglar:
        anahtar = (p, conf_min)
        if anahtar in _YASA_ONBELLEK:
            y = _YASA_ONBELLEK[anahtar]
        else:
            try:
                y = yasa_yukle(p, conf_min)
            except Exception:
                y = None
            _YASA_ONBELLEK[anahtar] = y
        if not y:
            continue
        iz = None
        for z in izler:
            if y["t0"] < z["t1"] and y["t1"] > z["t0"]:
                iz = z
                break
        if iz is None:
            continue
        try:
            par = birlestir(y, iz, gecikme_s)
        except Exception:
            continue
        if len(par) < 15:
            continue
        # ── AYNA ERASI KAPISI: kutu kerterizi ile truth kerterizi ayni isarette mi
        e_k = [BG.azimut_ham(r["cx"]) for r in par]
        e_t = [r["eps_truth"] for r in par]
        sxy = sum(a * b for a, b in zip(e_k, e_t))
        sxx = sum(a * a for a in e_k)
        egim = sxy / sxx if sxx > 1e-12 else 0.0
        ayna_sonrasi = egim > 0.0
        for r in par:
            r["ayna_sonrasi"] = ayna_sonrasi
            r["log"] = os.path.basename(p)
        damga[os.path.basename(p)] = (egim, len(par))
        kayit.extend(par)
        if ayrinti:
            print("   %-40s n=%-5d egim %+6.3f  %s" % (
                os.path.basename(p), len(par), egim,
                "AYNA SONRASI" if ayna_sonrasi else "ayna oncesi"))
    return kayit, damga


# ══════════════════════════════════════════════════════════════════════════
#  2. KOR KIYAS: YON
# ══════════════════════════════════════════════════════════════════════════

def kiyas_yon(kayit):
    print("\n" + "=" * 78)
    print(" A) KUTUDAN YON  --  bagil kerteriz (azimut) ve yukselis")
    print("=" * 78)
    K = [r for r in kayit if r["ayna_sonrasi"]]
    print(" AYNA SONRASI kare: %d / %d  (oncesi yatayda KULLANILMAZ)"
          % (len(K), len(kayit)))
    if not K:
        print(" ⚠ AYNA SONRASI kare YOK -- yatay kiyas ATLANDI.")
    else:
        h_ham, h_sev, h_hz, h_hamz = [], [], [], []
        for r in K:
            e_ham = BG.azimut_ham(r["cx"])
            e_sev, _ = BG.los_seviye(r["cx"], r["cy"], r["roll"], r["pitch"])
            e_svh, _ = BG.los_seviye(r["cx"], r["cy"], r["roll_h"], r["pitch_h"])
            h_ham.append(math.degrees(BG.sarmala_pi(e_ham - r["eps_truth"])))
            h_sev.append(math.degrees(BG.sarmala_pi(e_sev - r["eps_truth"])))
            h_hamz.append(math.degrees(BG.sarmala_pi(e_ham - r["eps_truth_h"])))
            h_hz.append(math.degrees(BG.sarmala_pi(e_svh - r["eps_truth_h"])))
        print("\n AZIMUT (bagil kerteriz) -- yasanin KULLANDIGI tutum (t anı):")
        print("   " + ozet("A1 ham atan((cx-CX)/FX)", h_ham))
        print("   " + ozet("A2 los_seviye (roll+pitch)", h_sev))
        print("\n AZIMUT -- tutum da t-D'ye HIZALI (saf GEOMETRI hatasi):")
        print("   " + ozet("A3 ham, hizali", h_hamz))
        print("   " + ozet("A4 los_seviye, hizali", h_hz))
        print("   -> A2'den A4'e dusen kisim ZAMAN HIZALAMASI, geometri degil.")
        # ── HANGI TERIM? yaw bayatligi mi, roll/pitch bayatligi mi ──
        # Yasa MUTLAK yonu `iris_yaw(t) + eps` ile kuruyor; ama eps t-D
        # anindaki GOVDEYE goredir. Aradaki fark tam olarak
        #     d_psi = yaw(t) - yaw(t-D)   ~   yaw_hizi * D
        # Bu terim TEK BASINA cikarilirsa ne kadar duzeliyor?
        h_yaw, dpsi = [], []
        for r in K:
            e_sev, _ = BG.los_seviye(r["cx"], r["cy"], r["roll"], r["pitch"])
            d = BG.sarmala_pi(r["eps_truth_h"] - r["eps_truth"])   # = yaw(t)-yaw(t-D)
            dpsi.append(abs(math.degrees(d)))
            h_yaw.append(math.degrees(BG.sarmala_pi(e_sev - d - r["eps_truth"])))
        print("   " + ozet("A2b los_seviye - d_psi", h_yaw))
        print("   |d_psi| = |yaw(t)-yaw(t-D)|: med %.2f  p90 %.2f  p95 %.2f deg"
              % (yuzdelik(dpsi, 50), yuzdelik(dpsi, 90), yuzdelik(dpsi, 95)))
        print("   ⇒ A2 (%.2f) -> A2b (%.2f): YAW BAYATLIGI tek basina "
              "hatanin %%%.0f'ini aciklıyor."
              % (yuzdelik([abs(x) for x in h_sev], 50),
                 yuzdelik([abs(x) for x in h_yaw], 50),
                 100.0 * (1.0 - yuzdelik([abs(x) for x in h_yaw], 50)
                          / max(yuzdelik([abs(x) for x in h_sev], 50), 1e-9))))
        # yatis dilimlerinde
        print("\n   -- YATIS (|roll|) dilimlerinde |hata| medyani --")
        print("   %-14s %6s %9s %9s %9s %9s"
              % ("|roll| bandi", "n", "A1 ham", "A2 sev", "A3 hamH", "A4 sevH"))
        for lo, hi in ((0, 10), (10, 20), (20, 30), (30, 45), (45, 90)):
            idx = [i for i, r in enumerate(K)
                   if lo <= abs(math.degrees(r["roll"])) < hi]
            if len(idx) < 20:
                continue
            print("   %-14s %6d %9.2f %9.2f %9.2f %9.2f" % (
                "%d-%d deg" % (lo, hi), len(idx),
                yuzdelik([abs(h_ham[i]) for i in idx], 50),
                yuzdelik([abs(h_sev[i]) for i in idx], 50),
                yuzdelik([abs(h_hamz[i]) for i in idx], 50),
                yuzdelik([abs(h_hz[i]) for i in idx], 50)))
        # kadraj kenarina gore (off-axis) — ince kamera modeli kenarda tutuyor mu
        print("\n   -- KADRAJ ACISINA (alfa) gore |hata| medyani, HIZALI --")
        print("   %-14s %6s %9s %9s" % ("alfa bandi", "n", "A3 ham", "A4 seviye"))
        for lo, hi in ((0, 10), (10, 20), (20, 30), (30, 40), (40, 65)):
            idx = [i for i, r in enumerate(K) if lo <= r["alfa"] < hi]
            if len(idx) < 20:
                continue
            print("   %-14s %6d %9.2f %9.2f" % (
                "%d-%d deg" % (lo, hi), len(idx),
                yuzdelik([abs(h_hamz[i]) for i in idx], 50),
                yuzdelik([abs(h_hz[i]) for i in idx], 50)))

        # ── RADYAL BOZUNUM SINAVI ────────────────────────────────────────
        # Model:  tan(az_truth) = a*tan(az_kutu) + b*tan^3(az_kutu)
        #   a != 1  -> ODAK UZAKLIGI (yani HFOV) hatasi
        #   b != 0  -> RADYAL BOZUNUM (ince kamera modeli yetmiyor)
        # En kucuk karelerle 2 bilinmeyen; yalniz HIZALI tutumla anlamli.
        X1 = X3 = Y1 = Y3 = S11 = S13 = S33 = 0.0
        n_b = 0
        for r in K:
            e_k, _ = BG.los_seviye(r["cx"], r["cy"], r["roll_h"], r["pitch_h"])
            if abs(e_k) > 1.2 or abs(r["eps_truth_h"]) > 1.2:
                continue
            u, v = math.tan(e_k), math.tan(r["eps_truth_h"])
            u3 = u ** 3
            S11 += u * u; S13 += u * u3; S33 += u3 * u3
            Y1 += u * v; Y3 += u3 * v
            X1 += u; X3 += u3; n_b += 1
        det = S11 * S33 - S13 * S13
        if n_b > 200 and abs(det) > 1e-12:
            a_ = (Y1 * S33 - Y3 * S13) / det
            b_ = (Y3 * S11 - Y1 * S13) / det
            print("\n   -- RADYAL BOZUNUM SINAVI (n=%d) --" % n_b)
            print("      tan(az_truth) = a*tan(az) + b*tan^3(az)")
            print("      a = %.4f  (1.000 = odak dogru)   b = %+.4f  "
                  "(0 = bozunum yok)" % (a_, b_))
            print("      a'nin ima ettigi HFOV = %.2f deg (kullanilan %.2f)"
                  % (2.0 * math.degrees(math.atan(
                      math.tan(math.radians(BG.DOW_HFOV_DEG) / 2.0) * a_)),
                     BG.DOW_HFOV_DEG))
            # duzeltilmis modelin artik hatasi
            hh = []
            for r in K:
                e_k, _ = BG.los_seviye(r["cx"], r["cy"], r["roll_h"], r["pitch_h"])
                if abs(e_k) > 1.2:
                    continue
                u = math.tan(e_k)
                hh.append(math.degrees(BG.sarmala_pi(
                    math.atan(a_ * u + b_ * u ** 3) - r["eps_truth_h"])))
            print("      " + ozet("A5 bozunum duzeltmeli", hh))

    # ── YUKSELIS: ayna dikeyi ETKILEMEZ, hepsi kullanilir ──
    b_duz, b_sev = [], []
    for r in kayit:
        el_duz = BG.piksel_elev(r["cy"]) + r["pitch"]
        _, el_sev = BG.los_seviye(r["cx"], r["cy"], r["roll"], r["pitch"])
        b_duz.append(math.degrees(el_duz - r["el_truth"]))
        b_sev.append(math.degrees(el_sev - r["el_truth"]))
    print("\n YUKSELIS (dunya cercevesi):")
    print("   " + ozet("B1 piksel_elev+pitch", b_duz))
    print("   " + ozet("B2 los_seviye (roll dahil)", b_sev))
    print("\n   -- YATIS dilimlerinde |hata| medyani (ROLL TELAFISININ KATKISI) --")
    print("   %-14s %6s %11s %11s %9s" % ("|roll| bandi", "n", "B1 roll YOK",
                                          "B2 roll VAR", "kazanc"))
    for lo, hi in ((0, 10), (10, 20), (20, 30), (30, 45), (45, 90)):
        idx = [i for i, r in enumerate(kayit)
               if lo <= abs(math.degrees(r["roll"])) < hi]
        if len(idx) < 20:
            continue
        m1 = yuzdelik([abs(b_duz[i]) for i in idx], 50)
        m2 = yuzdelik([abs(b_sev[i]) for i in idx], 50)
        print("   %-14s %6d %11.2f %11.2f %8.2f deg" % (
            "%d-%d deg" % (lo, hi), len(idx), m1, m2, m1 - m2))
    # terminal alt kumesi
    T = [i for i, r in enumerate(kayit) if r["durum"] == "TERMINAL"]
    if len(T) > 30:
        print("\n   TERMINAL karelerde: B1 |med| %.2f  ->  B2 |med| %.2f deg (n=%d)"
              % (yuzdelik([abs(b_duz[i]) for i in T], 50),
                 yuzdelik([abs(b_sev[i]) for i in T], 50), len(T)))
    return {"n": len(kayit)}


# ══════════════════════════════════════════════════════════════════════════
#  3. KOR KIYAS: MENZIL
# ══════════════════════════════════════════════════════════════════════════

def kiyas_menzil(kayit):
    print("\n" + "=" * 78)
    print(" B) KUTUDAN MENZIL")
    print("=" * 78)
    if not kayit:
        print(" ORNEK YOK"); return {}
    temiz = [r for r in kayit if not r["kirpik"]]

    # --- once DEGISMEZ arayisi: R*olcut ne kadar sabit? ---
    print("\n SAÇILIM SINAVI -- 'R x olcut' ne kadar SABIT? (std(log) kucuk = iyi)")
    print(" %-34s %8s %9s %9s %8s" % ("olcut", "medyan", "p10", "p90", "std(log)"))

    def _sac(ad, fn, birim=""):
        v = []
        for r in kayit:
            try:
                x = fn(r)
            except Exception:
                continue
            if math.isfinite(x) and x > 1e-9:
                v.append(r["R"] * x)
        if len(v) < 50:
            print(" %-34s ORNEK YOK" % ad); return None
        lg = [math.log(x) for x in v]
        m = sum(lg) / len(lg)
        sd = math.sqrt(sum((x - m) ** 2 for x in lg) / max(len(lg) - 1, 1))
        print(" %-34s %8.1f %9.1f %9.1f %8.4f %s"
              % (ad, yuzdelik(v, 50), yuzdelik(v, 10), yuzdelik(v, 90), sd, birim))
        return {"med": yuzdelik(v, 50), "sd": sd}

    s0 = _sac("PIKSEL sqrt(w*h)      [px*m]", lambda r: r["boyut"])
    _sac("PIKSEL max(w,h)      [px*m]", lambda r: max(r["w"], r["h"]))
    _sac("PIKSEL w             [px*m]", lambda r: r["w"])
    _sac("PIKSEL h             [px*m]", lambda r: r["h"])
    _sac("PIKSEL w^.15 h^.85   [px*m]",
         lambda r: (r["w"] ** 0.15) * (r["h"] ** 0.85))

    def _ang_geo(r):
        dy, dd = BG.acisal_boyut(r["cx"], r["cy"], r["w"], r["h"])
        return math.sqrt(max(dy, 1e-9) * max(dd, 1e-9))

    def _ang_w(r):
        dy, _ = BG.acisal_boyut(r["cx"], r["cy"], r["w"], r["h"])
        return 2.0 * math.tan(dy / 2.0)

    s_ang = _sac("ACISAL sqrt(dy*dd)   [m]", _ang_geo)
    _sac("ACISAL 2tan(dy/2)    [m]", _ang_w)

    if s0 and s_ang:
        print("\n  -> ACISAL olcutun sacilimi PIKSEL'e gore %+.1f%%"
              % (100.0 * (s_ang["sd"] / s0["sd"] - 1.0)))

    # --- USTEL TARAMASI: w^a * h^(1-a) ailesinde en az sacilim nerede? ---
    # menzil_model.py A_W = 0.15 iddiasinda; bu veride sinaniyor.
    print("\n USTEL TARAMASI  w^a * h^(1-a)  (std(log(R*olcut)) en kucuk = iyi)")
    print(" %-8s %10s   %-8s %10s" % ("a", "std(log)", "a", "std(log)"))
    sonuc = []
    for a in (0.0, 0.15, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.2):
        v = []
        for r in temiz:
            x = (r["w"] ** a) * (r["h"] ** (1.0 - a))
            if x > 1e-9:
                v.append(math.log(r["R"] * x))
        if len(v) < 100:
            continue
        m = sum(v) / len(v)
        sd = math.sqrt(sum((z - m) ** 2 for z in v) / (len(v) - 1))
        sonuc.append((a, sd))
    for i in range(0, len(sonuc), 2):
        satir = " %-8.2f %10.4f" % sonuc[i]
        if i + 1 < len(sonuc):
            satir += "   %-8.2f %10.4f" % sonuc[i + 1]
        print(satir)
    if sonuc:
        en = min(sonuc, key=lambda s: s[1])
        a015 = [s for s in sonuc if abs(s[0] - 0.15) < 1e-9]
        print(" -> EN IYI a = %.2f (std %.4f).  menzil_model'in A_W=0.15'i: %s"
              % (en[0], en[1],
                 ("std %.4f, %%%.0f DAHA KOTU"
                  % (a015[0][1], 100.0 * (a015[0][1] / en[1] - 1.0)))
                 if a015 else "olculemedi"))

    # --- MENZILE gore yanlilik: sabit carpan neden kayiyor ---
    print("\n MENZIL DILIMLERINDE 'R x sqrt(w*h)' (kodun kullandigi olcut):")
    print(" %-12s %7s %9s %9s %9s" % ("menzil", "n", "med px*m", "kod 202.6", "yanlilik"))
    for lo, hi in ((0, 3), (3, 6), (6, 10), (10, 15), (15, 30), (30, 60), (60, 200)):
        v = [r["R"] * r["boyut"] for r in kayit if lo <= r["R"] < hi]
        if len(v) < 30:
            continue
        m = yuzdelik(v, 50)
        print(" %-12s %7d %9.1f %9.1f %8.0f%%" % (
            "%d-%d m" % (lo, hi), len(v), m, 202.6, 100.0 * (202.6 / m - 1.0)))

    # --- KIRPILMA: kutu kadraj kenarina degiyorsa boyut GERCEK DEGIL ---
    kirp_n = sum(1 for r in kayit if r["kirpik"])
    print("\n KIRPILMA: %d / %d kare (%.1f%%) kadraj kenarina DEGIYOR"
          % (kirp_n, len(kayit), 100.0 * kirp_n / max(len(kayit), 1)))
    print(" %-16s %7s %10s %10s" % ("kume", "n", "med px*m", "std(log)"))
    for ad, kume in (("hepsi", kayit), ("TEMIZ (kirpiksiz)", temiz),
                     ("KIRPIK", [r for r in kayit if r["kirpik"]])):
        v = [r["R"] * r["boyut"] for r in kume]
        if len(v) < 30:
            continue
        lg = [math.log(x) for x in v if x > 0]
        m = sum(lg) / len(lg)
        sd = math.sqrt(sum((x - m) ** 2 for x in lg) / max(len(lg) - 1, 1))
        print(" %-16s %7d %10.1f %10.4f" % (ad, len(v), yuzdelik(v, 50), sd))

    # --- KADRAJ KENARI (off-axis): MENZIL BANDI SABIT tutularak ---
    print("\n OFF-AXIS (menzil bandi SABIT, KIRPIKSIZ): 'R x sqrt(wh)' vs alfa")
    print("  -> sec^2 modeli dogruysa px*m alfa ile ARTMALI")
    for rlo, rhi in ((6, 12), (12, 25)):
        band = [r for r in temiz if rlo <= r["R"] < rhi]
        if len(band) < 100:
            continue
        print("  menzil %d-%d m (n=%d):" % (rlo, rhi, len(band)))
        print("   %-12s %7s %10s %10s %10s"
              % ("alfa", "n", "med px*m", "olcu/merkez", "sec^2"))
        taban = None
        for lo, hi in ((0, 10), (10, 20), (20, 30), (30, 45), (45, 65)):
            sel = [r for r in band if lo <= r["alfa"] < hi]
            if len(sel) < 25:
                continue
            m = yuzdelik([r["R"] * r["boyut"] for r in sel], 50)
            am = yuzdelik([r["alfa"] for r in sel], 50)
            if taban is None:
                taban = m
            print("   %-12s %7d %10.1f %10.3f %10.3f"
                  % ("%d-%d" % (lo, hi), len(sel), m, m / taban,
                     1.0 / math.cos(math.radians(am)) ** 2))

    # --- ASPECT etkisi (hedefin bize gore duruşu) ---
    print("\n ASPECT (0=burun/kuyruk, 90=borda) dilimlerinde 'R x acisal' [m]")
    print(" %-14s %7s %9s %11s" % ("aspect", "n", "med L_etkin", "model L(a)"))
    for lo, hi in ((0, 30), (30, 60), (60, 90), (90, 120), (120, 150), (150, 180)):
        sel = [r for r in kayit
               if math.isfinite(r["aspect"])
               and lo <= math.degrees(r["aspect"]) < hi]
        if len(sel) < 30:
            continue
        v = []
        for r in sel:
            dy, _ = BG.acisal_boyut(r["cx"], r["cy"], r["w"], r["h"])
            if dy > 1e-9:
                v.append(r["R"] * 2.0 * math.tan(dy / 2.0))
        if len(v) < 30:
            continue
        am = math.radians(yuzdelik([math.degrees(r["aspect"]) for r in sel], 50))
        print(" %-14s %7d %9.3f %11.3f" % (
            "%d-%d deg" % (lo, hi), len(v), yuzdelik(v, 50),
            BG.gorunur_genislik_m(am)))

    # --- SABITIN YENIDEN TURETILMESI (KIRPIKSIZ kume) ---
    def _sabit(kume, fn):
        v = [r["R"] * fn(r) for r in kume if fn(r) > 1e-9]
        if len(v) < 50:
            return None
        return yuzdelik(v, 50), yuzdelik(v, 16), yuzdelik(v, 84)

    # --- ★ ADDITIF DEDEKTOR PAYI: boyut = k/R + c  (dogrusal regresyon) ---
    print("\n ★ ADDITIF PAY MODELI:  boyut = k/R + c   (=> R = k/(boyut - c))")
    print("   'R x boyut'un menzille kaymasi, dedektor kutusundaki SABIT PAYIN")
    print("   imzasidir. Dogruysa boyut ~ 1/R dogrusal, kesisimi c > 0 olur.")

    def _fit(kume):
        n = len(kume)
        if n < 100:
            return None
        sx = sy = sxx = sxy = 0.0
        for r in kume:
            x, y = 1.0 / r["R"], r["boyut"]
            sx += x; sy += y; sxx += x * x; sxy += x * y
        d = n * sxx - sx * sx
        if abs(d) < 1e-12:
            return None
        k = (n * sxy - sx * sy) / d
        c = (sy - k * sx) / n
        # R^2
        ym = sy / n
        ss = sum((r["boyut"] - ym) ** 2 for r in kume)
        rs = sum((r["boyut"] - (k / r["R"] + c)) ** 2 for r in kume)
        return k, c, (1.0 - rs / ss if ss > 0 else float("nan"))

    # ⚠ EN KUCUK KARELER BURADA YANILTIR: sacilim aspect'ten geliyor ve
    #   dagilim log-normal. Dogru hakem, DILIM MEDYANLARINI duzlestiren c'dir.
    def _bant_medyan(kume, c):
        out = []
        for lo, hi in ((3, 6), (6, 10), (10, 15), (15, 30)):
            v = [r["R"] * (r["boyut"] - c) for r in kume if lo <= r["R"] < hi]
            if len(v) > 30:
                m = yuzdelik(v, 50)
                if m > 1e-6:
                    out.append(m)
        return out

    print("\n   ROBUST c TARAMASI (dilim medyanlarini duzlestiren c):")
    print("   %-8s %10s %10s" % ("c (px)", "yayilim", "k' medyan"))
    en_iyi_c = (0.0, 1e9)
    c = 0.0
    while c <= 6.01:
        ms = _bant_medyan(temiz, c)
        if len(ms) >= 3:
            yay = max(ms) / min(ms)
            if abs(c * 4 - round(c * 4)) < 1e-9 and abs(c - round(c * 2) / 2) < 1e-9:
                print("   %-8.2f %10.3fx %10.1f" % (c, yay, yuzdelik(ms, 50)))
            if yay < en_iyi_c[1]:
                en_iyi_c = (c, yay)
        c += 0.25
    C_OFS = en_iyi_c[0]
    K_OFS = yuzdelik(_bant_medyan(temiz, C_OFS), 50)
    y0 = _bant_medyan(temiz, 0.0)
    print("   -> ★ ROBUST en iyi c = %.2f px, k = %.1f px*m  "
          "(L_etkin = %.3f m)" % (C_OFS, K_OFS, K_OFS / BG.FX))
    print("      YAYILIM: c=0 -> %.3fx   c=%.2f -> %.3fx"
          % (max(y0) / min(y0), C_OFS, en_iyi_c[1]))
    fit = _fit(temiz)
    if fit:
        print("      (⚠ EN KUCUK KARELER ayni veride c=%.2f diyor, R^2=%.3f --"
              " ASIRI duzeltiyor; log-normal sacilimda LS YANILIR.)"
              % (fit[1], fit[2]))
    print("   %-12s %8s %10s %10s %10s"
          % ("menzil", "n", "sabit k'", "ofsetli k'", "hedef"))
    for lo, hi in ((3, 6), (6, 10), (10, 15), (15, 30)):
        v = [r for r in temiz if lo <= r["R"] < hi]
        if len(v) < 30:
            continue
        print("   %-12s %8d %10.1f %10.1f %10.1f"
              % ("%d-%d m" % (lo, hi), len(v),
                 yuzdelik([r["R"] * r["boyut"] for r in v], 50),
                 yuzdelik([r["R"] * (r["boyut"] - C_OFS) for r in v], 50),
                 K_OFS))

    print("\n SABITIN YENIDEN TURETILMESI (KIRPIKSIZ, n=%d):" % len(temiz))
    for ad, fn in (("K_sqrt  (sqrt(w*h))", lambda r: r["boyut"]),
                   ("K_w     (w)", lambda r: r["w"]),
                   ("K_max   (max(w,h))", lambda r: max(r["w"], r["h"]))):
        s = _sabit(temiz, fn)
        if s:
            print("   %-22s = %6.1f px*m   [1sigma bandi %.1f .. %.1f, +-%.0f%%]"
                  % (ad, s[0], s[1], s[2], 50.0 * (s[2] - s[1]) / s[0]))
    Lw = [r["R"] * 2.0 * math.tan(BG.acisal_boyut(
        r["cx"], r["cy"], r["w"], r["h"])[0] / 2.0) for r in temiz]
    L_ETK = yuzdelik(Lw, 50) if Lw else 1.0
    print("   %-22s = %6.3f m       [1sigma %.3f .. %.3f]"
          % ("L_etkin (ACISAL, w)", L_ETK, yuzdelik(Lw, 16), yuzdelik(Lw, 84)))

    # --- MODEL YARISI: mutlak yuzde hata ---
    def _yaris_kume(kume, baslik):
        print("\n MODEL YARISI -- %s (n=%d)" % (baslik, len(kume)))
        print(" %-42s %6s %8s %8s %9s"
              % ("model", "n", "medAPE", "p90APE", "yanlilik"))

        def _y(ad, fn):
            e = []
            for r in kume:
                try:
                    R = fn(r)
                except Exception:
                    continue
                if math.isfinite(R) and R > 0:
                    e.append(100.0 * (R - r["R"]) / r["R"])
            if len(e) < 50:
                print(" %-42s ORNEK YOK" % ad); return
            print(" %-42s %6d %8.1f %8.1f %+9.1f"
                  % (ad, len(e), yuzdelik([abs(x) for x in e], 50),
                     yuzdelik([abs(x) for x in e], 90), yuzdelik(e, 50)))

        _y("M0  kod: 202.6/sqrt(wh)", lambda r: 202.6 / r["boyut"])
        _y("M0b hardcoded ikiz: 160.0/sqrt(wh)", lambda r: 160.0 / r["boyut"])
        _y("M1  232.9/max(w,h)", lambda r: 232.9 / max(r["w"], r["h"]))
        if MM is not None:
            _y("M2  menzil_model (w^.15 h^.85)",
               lambda r: MM.menzil_kestir(r["w"], r["h"])[0])
        _y("M3  ACISAL(w), sabit L=%.3f m" % L_ETK,
           lambda r: BG.menzil_acisal(r["cx"], r["cy"], r["w"], r["h"], L_ETK))
        _y("M4  ACISAL(w) + truth aspect L(a)",
           lambda r: (BG.menzil_acisal(
               r["cx"], r["cy"], r["w"], r["h"],
               BG.gorunur_genislik_m(r["aspect"], dedektor_k=0.90))
               if math.isfinite(r["aspect"]) else float("nan")))
        _y("M5  PIKSEL(w), yeniden kalibre K_w",
           lambda r: (yuzdelik([x["R"] * x["w"] for x in temiz], 50)
                      / max(r["w"], 1e-9)))
        if K_OFS:
            _y("M6  ★ ADDITIF PAY k=%.0f c=%.2f" % (K_OFS, C_OFS),
               lambda r: BG.menzil_ofsetli(r["w"], r["h"], K_OFS, C_OFS))
            _y("M6b M6 + kucuk kutu kapisi (s>c+3)",
               lambda r: (BG.menzil_ofsetli(r["w"], r["h"], K_OFS, C_OFS)
                          if r["boyut"] > C_OFS + 3.0 else float("nan")))

    _yaris_kume(kayit, "HEPSI")
    _yaris_kume(temiz, "KIRPIKSIZ")
    print("\n  NOT: M4 hedefin GERCEK aspect'ini kullanir -- ucusta bu bilgi YOK.")
    print("        Menzil hatasinin ASPECT'ten gelen TABANINI olcer (ALT sinir).")
    return {"L_ETK": L_ETK,
            "K_w": yuzdelik([r["R"] * r["w"] for r in temiz], 50) if temiz else None,
            "K_sqrt": yuzdelik([r["R"] * r["boyut"] for r in temiz], 50) if temiz else None}


# ══════════════════════════════════════════════════════════════════════════
#  4. KOR KIYAS: IRTIFA FARKI
# ══════════════════════════════════════════════════════════════════════════

def kiyas_irtifa(kayit, L_ETK=None):
    print("\n" + "=" * 78)
    print(" C) KUTUDAN IRTIFA FARKI (Delta-z, + = hedef YUKARIDA)")
    print("=" * 78)
    if not kayit:
        print(" ORNEK YOK"); return

    def _dz(fn_el, fn_R):
        e = []
        for r in kayit:
            try:
                R = fn_R(r)
                if not (math.isfinite(R) and R > 0):
                    continue
                e.append(R * math.sin(fn_el(r)) - r["dz_truth"])
            except Exception:
                continue
        return e

    R_truth = lambda r: r["R"]                                       # noqa: E731
    R_kod = lambda r: 202.6 / r["boyut"]                             # noqa: E731
    R_ang = (lambda r: BG.menzil_acisal(r["cx"], r["cy"], r["w"], r["h"],
                                        L_ETK, L_ETK)) if L_ETK else R_kod
    el_duz = lambda r: BG.piksel_elev(r["cy"]) + r["pitch"]          # noqa: E731
    el_sev = lambda r: BG.los_seviye(r["cx"], r["cy"], r["roll"],    # noqa: E731
                                     r["pitch"])[1]

    print("\n MENZIL TRUTH verilirse (yalniz ACI hatasi gorunur):")
    print("   " + ozet("C1 duzlem elev (roll YOK)", _dz(el_duz, R_truth), "m"))
    print("   " + ozet("C2 seviye elev (roll VAR)", _dz(el_sev, R_truth), "m"))
    print("\n MENZIL de kutudan (GERCEK islevsel hata):")
    print("   " + ozet("C3 duzlem + kod menzili", _dz(el_duz, R_kod), "m"))
    print("   " + ozet("C4 seviye + kod menzili", _dz(el_sev, R_kod), "m"))
    print("   " + ozet("C5 seviye + acisal menzil", _dz(el_sev, R_ang), "m"))

    print("\n TERMINAL (son metreler) alt kumesi:")
    T = [r for r in kayit if r["durum"] == "TERMINAL"]
    if len(T) > 30:
        eski = kayit[:]
        kayit[:] = T
        print("   " + ozet("C1 duzlem + truth menzil", _dz(el_duz, R_truth), "m"))
        print("   " + ozet("C2 seviye + truth menzil", _dz(el_sev, R_truth), "m"))
        print("   " + ozet("C4 seviye + kod menzili", _dz(el_sev, R_kod), "m"))
        kayit[:] = eski
    else:
        print("   yeterli TERMINAL karesi yok (n=%d)" % len(T))


# ══════════════════════════════════════════════════════════════════════════
#  5. GECIKME TARAMASI
# ══════════════════════════════════════════════════════════════════════════

def gecikme_tara(en_fazla_log=120, conf_min=0.35):
    print("\n" + "=" * 78)
    print(" D) DEDEKTOR GECIKMESI -- uc BAGIMSIZ kanaldan kestirim")
    print("=" * 78)
    print(" 'yatay-t'  : piksel(t) vs truth(t-D), tutum t'de     (yasanin hali)")
    print(" 'yatay-h'  : piksel(t) vs truth(t-D), tutum da t-D'de (TAM tutarli)")
    print(" 'yukselis' : yaw'dan BAGIMSIZ -> en temiz olcu")
    print("\n %-7s %8s %10s %10s %10s"
          % ("D (s)", "n", "yatay-t", "yatay-h", "yukselis"))
    en_iyi = (None, 1e9)
    for D in (0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40):
        kayit, _ = veri_topla(D, en_fazla_log, conf_min)
        K = [r for r in kayit if r["ayna_sonrasi"]]
        if len(K) < 100:
            print(" %-7.2f  ORNEK YOK" % D); continue
        ha = [abs(math.degrees(BG.sarmala_pi(
            BG.los_seviye(r["cx"], r["cy"], r["roll"], r["pitch"])[0]
            - r["eps_truth"]))) for r in K]
        hh = [abs(math.degrees(BG.sarmala_pi(
            BG.los_seviye(r["cx"], r["cy"], r["roll_h"], r["pitch_h"])[0]
            - r["eps_truth_h"]))) for r in K]
        hb = [abs(math.degrees(
            BG.los_seviye(r["cx"], r["cy"], r["roll_h"], r["pitch_h"])[1]
            - r["el_truth"])) for r in kayit]
        m = yuzdelik(hh, 50)
        print(" %-7.2f %8d %10.2f %10.2f %10.2f"
              % (D, len(K), yuzdelik(ha, 50), m, yuzdelik(hb, 50)))
        if m < en_iyi[1]:
            en_iyi = (D, m)
    print("\n -> TAM TUTARLI kiyasta en kucuk yatay hata D = %.2f s (%.2f deg)"
          % en_iyi)
    return en_iyi[0]


def gecikme_menzil_tara(en_fazla_log=80, conf_min=0.35):
    """MENZIL sabitinin menzille kaymasi GECIKMEDEN mi geliyor?

    Mantik: gercek gecikme D_g iken D kullanirsan truth menzili
    (D - D_g)*kapanma kadar YANLIS okursun. Bu hata YAKIN menzilde ORANSAL
    olarak cok daha buyuktur -> 'R x boyut' menzille kayar. Dogru D'de
    kayma EN KUCUK olmalidir. Yani bu tarama gecikmenin BAGIMSIZ bir
    kestirimidir (yatay kerteriz taramasindan farkli bir fizige dayanir).
    """
    print("\n" + "=" * 78)
    print(" D2) MENZIL SABITININ MENZILE BAGIMLILIGI vs DEDEKTOR GECIKMESI")
    print("=" * 78)
    print(" %-7s %7s %9s %9s %9s %9s %10s"
          % ("D (s)", "n", "3-6 m", "6-10 m", "10-15 m", "15-30 m", "yayilim"))
    for D in (0.0, 0.10, 0.20, 0.30, 0.45, 0.60):
        kayit, _ = veri_topla(D, en_fazla_log, conf_min)
        kayit = [r for r in kayit if not r["kirpik"]]
        if len(kayit) < 500:
            print(" %-7.2f  ORNEK YOK" % D); continue
        satir, ms = [], []
        for lo, hi in ((3, 6), (6, 10), (10, 15), (15, 30)):
            v = [r["R"] * r["boyut"] for r in kayit if lo <= r["R"] < hi]
            m = yuzdelik(v, 50) if len(v) > 30 else float("nan")
            satir.append(m)
            if math.isfinite(m):
                ms.append(m)
        yay = (max(ms) / min(ms)) if len(ms) > 1 else float("nan")
        print(" %-7.2f %7d %9.1f %9.1f %9.1f %9.1f %9.2fx"
              % (D, len(kayit), satir[0], satir[1], satir[2], satir[3], yay))
    print("\n -> yayilim (en buyuk/en kucuk dilim) EN KUCUK olan D, gecikmenin")
    print("    menzil kanalindan BAGIMSIZ kestirimidir.")


def _olcek_fit(K, roll_key="roll_h", pitch_key="pitch_h", truth_key="eps_truth_h"):
    """tan(az_truth) = a*tan(az_kutu) + b*tan^3(az_kutu) -> (a, b, n)."""
    S11 = S13 = S33 = Y1 = Y3 = 0.0
    n = 0
    for r in K:
        e_k, _ = BG.los_seviye(r["cx"], r["cy"], r[roll_key], r[pitch_key])
        if abs(e_k) > 1.2 or abs(r[truth_key]) > 1.2:
            continue
        u, v = math.tan(e_k), math.tan(r[truth_key])
        u3 = u ** 3
        S11 += u * u; S13 += u * u3; S33 += u3 * u3
        Y1 += u * v; Y3 += u3 * v
        n += 1
    det = S11 * S33 - S13 * S13
    if n < 200 or abs(det) < 1e-12:
        return None
    return ((Y1 * S33 - Y3 * S13) / det, (Y3 * S11 - Y1 * S13) / det, n)


def olcek_gecikme_tara(en_fazla_log=80, conf_min=0.35):
    """★ 'Odak olcegi a=0.86' GERCEK bir optik etki mi, GECIKME artigi mi?

    Ayrim su: gecikme artigi hedefin KADRAJDAKI HIZIYLA orantilidir, yani
    a'yi D ile birlikte kaydirir ve DURGUN karelerde kaybolur. Gercek bir
    odak/olcek hatasi ise D'den ve donus hizindan BAGIMSIZDIR.
    """
    print("\n" + "=" * 78)
    print(" D3) OLCEK KATSAYISI a  --  gercek optik mi, gecikme artigi mi?")
    print("=" * 78)
    print(" %-7s %8s %9s %11s %12s" % ("D (s)", "n", "a", "b", "ima HFOV"))
    for D in (0.0, 0.10, 0.20, 0.30, 0.45):
        kayit, _ = veri_topla(D, en_fazla_log, conf_min)
        K = [r for r in kayit if r["ayna_sonrasi"]]
        f = _olcek_fit(K)
        if not f:
            print(" %-7.2f  ORNEK YOK" % D); continue
        a_, b_, n = f
        print(" %-7.2f %8d %9.4f %11.5f %11.2f deg"
              % (D, n, a_, b_, 2.0 * math.degrees(math.atan(
                  math.tan(math.radians(BG.DOW_HFOV_DEG) / 2.0) * a_))))
    print("\n DURGUN kareler (aracin yaw hizi kucuk) -- gecikme artigi SONER:")
    kayit, _ = veri_topla(0.20, en_fazla_log, conf_min)
    K = [r for r in kayit if r["ayna_sonrasi"]]
    K.sort(key=lambda r: r["t"])
    # yaw hizini komsu karelerden kestir
    for i in range(1, len(K)):
        dt = K[i]["t"] - K[i - 1]["t"]
        K[i]["w_yaw"] = (abs(math.degrees(BG.sarmala_pi(
            K[i]["yaw"] - K[i - 1]["yaw"])) / dt) if 1e-3 < dt < 0.5 else 999.0)
    K[0]["w_yaw"] = 999.0
    print(" %-18s %8s %9s %11s" % ("|yaw hizi|", "n", "a", "b"))
    for lo, hi in ((0, 5), (5, 15), (15, 40), (40, 200)):
        alt = [r for r in K if lo <= r.get("w_yaw", 999.0) < hi]
        f = _olcek_fit(alt)
        if not f:
            continue
        print(" %-18s %8d %9.4f %11.5f" % ("%d-%d deg/s" % (lo, hi),
                                           f[2], f[0], f[1]))
    print("\n -> a DURGUN karelerde de 1'den uzaksa etki GERCEK; 1'e yaklasiyorsa")
    print("    gecikme artigidir ve odak/HFOV'a DOKUNULMAMALIDIR.")

    # ── EKSEN AYRIMI: olcek hatasi YATAYA MI OZGU? ────────────────────────
    # fx = fy (kare piksel) oldugu icin GERCEK bir odak/HFOV hatasi HER IKI
    # ekseni AYNI oranda bozmali. Yalniz yatayda gorunuyorsa sebep optik
    # DEGIL, yatay eksene ozgu bir seydir (ayna ekseni, yakalama kirpmasi,
    # dedektorun yatay kutu yanliligi).
    print("\n EKSEN AYRIMI: piksel olcegi s ile bolunerek hata taranir")
    print(" (s = 1.00 -> HFOV 122.07 ; s < 1 -> daha DAR gercek FOV)")
    print(" %-7s %11s %12s %12s" % ("s", "ima HFOV", "|az| med", "|el| med"))
    en_az = en_el = (None, 1e9)
    for s in (0.80, 0.85, 0.90, 0.95, 1.00, 1.05, 1.10):
        ha, he = [], []
        for r in kayit:
            x, y, _ = BG.piksel_isin(r["cx"], r["cy"])
            cx2 = BG.CX + BG.FX * x / s
            cy2 = BG.CY + BG.FY * y / s
            az, el = BG.los_seviye(cx2, cy2, r["roll_h"], r["pitch_h"])
            if r["ayna_sonrasi"]:
                ha.append(abs(math.degrees(BG.sarmala_pi(az - r["eps_truth_h"]))))
            he.append(abs(math.degrees(el - r["el_truth"])))
        ma, me = yuzdelik(ha, 50), yuzdelik(he, 50)
        print(" %-7.2f %10.2f deg %11.2f %12.2f"
              % (s, 2.0 * math.degrees(math.atan(
                  math.tan(math.radians(BG.DOW_HFOV_DEG) / 2.0) / s)), ma, me))
        if ma < en_az[1]:
            en_az = (s, ma)
        if me < en_el[1]:
            en_el = (s, me)
    print("\n -> YATAY en iyi s = %.2f (%.2f deg) | DIKEY en iyi s = %.2f (%.2f deg)"
          % (en_az[0], en_az[1], en_el[0], en_el[1]))
    if en_az[0] != en_el[0]:
        print(" ⇒ IKI EKSEN AYNI s'te BULUSMUYOR: bu bir ODAK/HFOV hatasi DEGIL.")
        print("   Kare piksel varsayimi (fy=fx) altinda optik hata her iki")
        print("   ekseni ayni oranda bozardi. Sebep YATAYA OZGU olmali.")
    else:
        print(" ⇒ Iki eksen ayni s'te bulusuyor -> gercek bir HFOV hatasi.")


# ══════════════════════════════════════════════════════════════════════════
#  6. KARARLILIK
# ══════════════════════════════════════════════════════════════════════════

def kararlilik():
    print("\n" + "=" * 78)
    print(" E) YAW KANALI KARARLILIGI  (olculen gecikme ile)")
    print("=" * 78)
    Td = BG.DEDEKTOR_GECIKME_S + 0.5 / BG.DONGU_HZ
    print(" model  L(s) = k e^{-Td s} / ( s (1 + tau s) )")
    print(" Td = %.4f s (dedektor %.2f + ornekleme %.4f)   tau = %.2f s"
          % (Td, BG.DEDEKTOR_GECIKME_S, 0.5 / BG.DONGU_HZ, BG.YAW_GECIKME_S))
    print("\n %-8s %10s %10s %10s %12s %12s"
          % ("k", "w_c rad/s", "PM deg", "GM (x)", "eps_ss p50", "eps_ss p90"))
    for k in (0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 2.0, 2.5, 3.0, 4.0):
        wc, pm, gm = BG.yaw_kazanc_kararlilik(k, Td)
        e50 = math.degrees(BG.yaw_kalici_hata(k, math.radians(6.55)))
        e90 = math.degrees(BG.yaw_kalici_hata(k, math.radians(32.0)))
        print(" %-8.2f %10.3f %10.1f %10.2f %11.1f° %11.1f°"
              % (k, wc, pm, gm, e50, e90))
    print("\n ISTENEN FAZ PAYINI VEREN EN BUYUK KAZANC:")
    for pm in (70.0, 60.0, 50.0, 45.0, 40.0, 30.0):
        print("   PM %4.0f deg -> k = %.3f rad/s (= %.1f deg/s per rad hata)"
              % (pm, BG.yaw_kazanc_oner(pm, Td),
                 math.degrees(BG.yaw_kazanc_oner(pm, Td))))
    print("\n GECIKME DUYARLILIGI (PM=50 deg icin gereken k):")
    for D in (0.10, 0.15, 0.20, 0.25, 0.30):
        print("   dedektor D = %.2f s -> k = %.3f rad/s"
              % (D, BG.yaw_kazanc_oner(50.0, D + 0.5 / BG.DONGU_HZ)))
    print("\n ILERI BESLEME (ff) ile kalici hata (k = 1.4):")
    print(" %-10s %12s %12s %12s" % ("ff", "p50 6.55°/s", "p90 32°/s", "p95 112°/s"))
    for ff in (0.0, 0.5, 0.8, 1.0):
        print(" %-10.1f %11.1f° %11.1f° %11.1f°" % (
            ff,
            math.degrees(BG.yaw_kalici_hata(1.4, math.radians(6.55), ff)),
            math.degrees(BG.yaw_kalici_hata(1.4, math.radians(32.0), ff)),
            math.degrees(BG.yaw_kalici_hata(1.4, math.radians(111.9), ff))))
    print("\n ⚠ HIZ VEKTORU tavani (burun DEGIL):")
    for v in (12.0, 18.0, 24.0):
        print("   V=%4.1f m/s, a=12 m/s^2 -> %.1f deg/s   (yaw tavani %.0f deg/s)"
              % (v, math.degrees(BG.donus_hizi_tavani(v, 12.0)), BG.YAW_TAVAN_DPS))


# ══════════════════════════════════════════════════════════════════════════
#  7. IVME DAGITIMI
# ══════════════════════════════════════════════════════════════════════════

def dagitim():
    print("\n" + "=" * 78)
    print(" F) IVME DAGITIMI  --  kamera kisiti ve itki butcesi birlikte")
    print("=" * 78)
    print("\n Yatay ivme -> govde pitch'i -> KAMERA bakisi (trim -14.5 deg dahil):")
    print(" %-12s %12s %14s %16s" % ("a_yatay", "pitch (deg)", "kamera (deg)",
                                     "trim'li (deg)"))
    for a in (0.0, 2.0, 4.0, 6.0, 8.0, 10.0, 12.0):
        roll, pitch, T, yat = BG.ivme_tutum(a, 0.0, 0.0, 0.0)
        bak = math.degrees(BG.kamera_bakis_acisi(pitch))
        bak_t = math.degrees(BG.kamera_bakis_acisi(
            pitch + math.radians(BG.GOVDE_PITCH_TRIM_DEG)))
        print(" %-12.1f %12.1f %14.1f %16.1f"
              % (a, math.degrees(pitch), bak, bak_t))
    print("\n KAMERAYI ufkun uzerinde tutan yatay ivme tavani:")
    for bmin in (0.0, 5.0, 10.0, 15.0):
        print("   bakis >= %4.0f deg -> a_yatay <= %5.2f m/s^2"
              % (bmin, BG.yatay_ivme_tavani_kamera(0.0, bmin)))
    print("\n TIRMANMA yatay butceyi BUYUTUR (g - a_d terimi):")
    for ad in (0.0, -2.0, -5.0, -8.0):
        print("   a_d = %+5.1f (NED, - = yukari) -> a_yatay <= %5.2f m/s^2"
              % (ad, BG.yatay_ivme_tavani_kamera(ad, 0.0)))
    print("\n TEK 3B TAVAN vs AYRIK: 'yukari cik' talebinden dikeye kalan")
    print(" %-26s %10s %10s" % ("talep (a_n, a_d)", "tek 12", "ayrik"))
    for an, ad in ((12.0, -3.0), (11.0, -5.0), (8.0, -8.0)):
        m = math.sqrt(an * an + ad * ad)
        tek_d = ad * (12.0 / m) if m > 12.0 else ad
        _, _, ay_d = BG.ivme_butce(an, 0.0, ad, 12.0, 10.0)
        print(" %-26s %10.2f %10.2f"
              % ("(%.0f, %+.0f)" % (an, ad), tek_d, ay_d))


# ══════════════════════════════════════════════════════════════════════════
#  8. KAPALI CEVRIM BENZETIMI
# ══════════════════════════════════════════════════════════════════════════

def cevrim_tara(n=40, sure=25.0):
    """★ KAPALI CEVRIM A/B — DEGISTIRILMEMIS `bbox_ibvs.komut()` ile.

    ⛔ NEDEN KENDI CEVRIMIMI KULLANMIYORUM: bu dosyanin ilk surumunde 3B bir
    cevrim yazdim ve medyan 21 m iska verdi (sahada olculen 2-4 m). Sebep
    benim modelimin eksikligiydi (menzil kestirimi hicbir kanala baglanmamisti).
    `sim/tesis.py` ise SAHAYA KARSI DOGRULANMIS bir tesistir (bagimsiz olarak
    3.7 m verirken saha 4.22 m olcmustu) ve `sim/deney.py::kosu(cfg=...)`
    YASA KODUNU DEGISTIRMEDEN cfg uzerinden A/B yapmaya izin verir.
    ⇒ Kendi kirilgan cevrimimi atip DOGRULANMIS tezgahi kullaniyorum.
       (Bu, repo'nun kendi dersi: "tesis iki kez kendi hatasini yasada bug
        gibi gosterdi" -- sim/tesis.py:16-33.)

    Degistirilen TEK sey `cfg` alanlaridir; bunlar zaten env kapilarina birebir
    karsilik gelir, yani tezgahtaki kol ile sahadaki kol AYNI seydir.
    """
    print("\n" + "=" * 78)
    print(" G) KAPALI CEVRIM A/B  --  DOGRULANMIS tesis + DEGISTIRILMEMIS yasa")
    print("=" * 78)
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import deney as D
        from control.guidance import bbox_ibvs as IB
    except Exception as e:
        print(" ⛔ tezgah yuklenemedi: %r" % (e,))
        return

    def _kol(ad, devir, **alanlar):
        cfg = type("CfgAB", (IB.Cfg,), alanlar) if alanlar else IB.Cfg
        r = D.parti(n=n, cfg=cfg, sure=sure, devir_m=devir)
        e = sorted(x["en_yakin"] for x in r)
        g = sum(x["gorus"] for x in r) / len(r)
        print(" %-38s med %6.2f m  p10 %5.2f  <3m %%%3.0f  gorus %%%2.0f"
              % (ad, yuzdelik(e, 50), yuzdelik(e, 10),
                 100.0 * sum(1 for x in e if x < 3.0) / len(e), 100.0 * g))
        return yuzdelik(e, 50)

    # ⚠ DEVIR MENZILI KRITIK: 13 m'de angajman o kadar kisa ki iska
    #   BASLANGIC GEOMETRISIYLE belirlenir ve HICBIR kol ayrismaz (hepsi
    #   4.66 m). Sahada olculen devir medyani 32.9 m; ayirt etme orada olur.
    for devir in (13.0, 32.9):
        print("\n" + "-" * 78)
        print(" DEVIR MENZILI %.1f m   (n=%d/kol, %.0f s)" % (devir, n, sure))
        print("-" * 78)
        taban = _kol("TABAN (bugunku varsayilanlar)", devir)
        print(" -- tek degisken --")
        for mk in (202.6, 160.0, 147.9):
            _kol("MENZIL_PX_M = %.1f" % mk, devir, MENZIL_PX_M=mk)
        for dr in (False, True):
            _kol("DIKEY_ROLL = %s" % dr, devir, DIKEY_ROLL=dr)
        for sp in (False, True):
            _kol("ACCEL_SPLIT = %s" % sp, devir, ACCEL_SPLIT=sp)
        for ky in (0.6, 1.0, 1.4, 2.0):
            _kol("K_YAW = %.1f" % ky, devir, K_YAW=ky)
        b = _kol("★ BIRLESIK ONERILEN", devir,
                 MENZIL_PX_M=147.9, DIKEY_ROLL=True, ACCEL_SPLIT=True)
        print(" -> TABAN %.2f m  ->  ONERILEN %.2f m  (%+.1f%%)"
              % (taban, b, 100.0 * (b / taban - 1.0) if taban else float("nan")))

    # ── KESME GEOMETRISI: vuruslarin %81'i aspect<90'da olusuyor (olculdu,
    #    869 angajman). Kuyrukta P(<3m)=0.005, kesmede 0.421. Tezgah TABAN
    #    kolunda hic vurus uretmiyorsa, ayirt etme gucunu ORADA aramak gerek.
    print("\n" + "-" * 78)
    print(" DEVIR ACISI TARAMASI (devir 32.9 m) -- kesme geometrisi")
    print("-" * 78)
    print(" %-10s %26s %26s" % ("devir_aci", "TABAN", "ONERILEN"))
    for da in (0.0, 30.0, 60.0, 90.0, 120.0):
        cikti = []
        for ad, alanlar in (("t", {}),
                            ("o", dict(MENZIL_PX_M=147.9, DIKEY_ROLL=True,
                                       ACCEL_SPLIT=True))):
            cfg = type("CfgAB", (IB.Cfg,), alanlar) if alanlar else IB.Cfg
            r = D.parti(n=n, cfg=cfg, sure=sure, devir_m=32.9, devir_aci=da)
            e = sorted(x["en_yakin"] for x in r)
            cikti.append("med %5.2f m  <3m %%%3.0f"
                         % (yuzdelik(e, 50),
                            100.0 * sum(1 for x in e if x < 3.0) / len(e)))
        print(" %-10.0f %26s %26s" % (da, cikti[0], cikti[1]))
    print("\n ⚠ Tezgah GEREK sarttir, YETER degil. sim/tesis.py ruzgar ve aero")
    print("   modellemez; SIRALAMAYI gosterir, mutlak iskayi DEGIL.")


# ══════════════════════════════════════════════════════════════════════════
#  ANA
# ══════════════════════════════════════════════════════════════════════════

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--veri", action="store_true")
    ap.add_argument("--kararlilik", action="store_true")
    ap.add_argument("--cevrim", action="store_true")
    ap.add_argument("--gecikme", action="store_true")
    ap.add_argument("--dagitim", action="store_true")
    ap.add_argument("--hepsi", action="store_true")
    ap.add_argument("--log-sayisi", type=int, default=400)
    ap.add_argument("--gecikme-s", type=float, default=BG.DEDEKTOR_GECIKME_S)
    ap.add_argument("--conf", type=float, default=0.35)
    ap.add_argument("--ayrinti", action="store_true")
    a = ap.parse_args()
    if not any((a.veri, a.kararlilik, a.cevrim, a.gecikme, a.dagitim, a.hepsi)):
        a.hepsi = True

    print("=" * 78)
    print(" BBOX KONTROL TEZGAHI   (bbox_geometri.py kor sinavi)")
    print("=" * 78)
    t = BG.tutarlilik_raporu()
    print(" ic tutarlilik: tur-donusu %.2e px | seviye==duzlem(merkez) %.2e deg"
          % (t["turdonus_px"], t["seviye_vs_duzlem_merkez_deg"]))
    print(" duzlem-kuresel fark (cx+250, cy=301): %.2f deg"
          % t["duzlem_kuresel_fark_deg"])
    print(" OFF-AXIS: cx+250 (alfa=56.3 deg) piksel/aci kazanci %.2fx  "
          "[sec^2 = %.2f]" % (t["offaxis_sisme"],
                              1.0 / math.cos(math.atan(250.0 / BG.FX)) ** 2))
    if t["turdonus_px"] > 1e-6 or t["seviye_vs_duzlem_merkez_deg"] > 1e-9:
        print(" ⛔ IC TUTARLILIK BOZUK -- sonuclara guvenme.")

    if a.gecikme or a.hepsi:
        gecikme_tara(min(a.log_sayisi, 120), a.conf)
        gecikme_menzil_tara(min(a.log_sayisi, 80), a.conf)
        olcek_gecikme_tara(min(a.log_sayisi, 80), a.conf)

    L = None
    if a.veri or a.hepsi:
        print("\n veri toplaniyor (D = %.2f s, en fazla %d log)..."
              % (a.gecikme_s, a.log_sayisi))
        kayit, damga = veri_topla(a.gecikme_s, a.log_sayisi, a.conf, a.ayrinti)
        ayna = sum(1 for v in damga.values() if v[0] > 0)
        print(" %d log eslesti (%d ayna sonrasi), %d kare"
              % (len(damga), ayna, len(kayit)))
        if kayit:
            kiyas_yon(kayit)
            m = kiyas_menzil(kayit)
            L = m.get("L_ETK")
            kiyas_irtifa(kayit, L)
        else:
            print(" ⛔ ESLESEN KARE YOK.")

    if a.kararlilik or a.hepsi:
        kararlilik()
    if a.dagitim or a.hepsi:
        dagitim()
    if a.cevrim or a.hepsi:
        cevrim_tara()


if __name__ == "__main__":
    main()

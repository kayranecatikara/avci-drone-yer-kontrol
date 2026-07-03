# -*- coding: utf-8 -*-
"""
================================================================================
GELISTIRME/DOGRULAMA ARACI — gorev ucusunda ve degerlendirme kosusunda
kullanilmaz. (Truth erisimi YALNIZCA arac/ altinda yasayabilir.)
================================================================================
FILTRE DOGRULAMA: fusion cikti kalitesini SAYIYLA gormek
================================================================================
Fusion filtresinin (GNSSDuzeltici) ciktisi ile sim'in DEBUG TRUTH kanali
arasinda uc metrik raporlar (ham GPS taban cizgisiyle birlikte):

  * RMSE   : hata karelerinin ortalamasinin karekoku — tek sayilik dogruluk
             ozeti (3B konum hatasi uzerinden, metre)
  * MAX    : en kotu anlik sapma (metre)
  * GECIKME: seri, truth'un KAC SANIYE oncesine en iyi oturuyor? (kayan tau
             taramasi: truth(t-tau)'ya karsi RMSE'yi en kucukleyen tau)
             + gecikme-arindirilmis RMSE (o tau'daki kalan hata)

BESLEME DESENI pipeline ile AYNIDIR (guidance._hedef_temizle): filtre yalnizca
YENI ham pakette guncellenir; metrik filtre.durum_guduum()['pos'] (lead'siz
ANLIK kestirim) uzerinden alinir — "temize yakin mi?" sorusunun dogru karsiligi
budur (2 sn'lik lead ongorusu ayri is; burada degerlendirilmez).

fusion/'a DOKUNULMAZ: filtre modulu degisse de arayuz (guncelle/durum_guduum)
ayni kaldikca bu arac otomatik uyumludur.

KULLANIM (dogrudan SDK; WEB ARAYUZU KAPALI olmali — oyun tek TCP kabul eder):
    python arac/filtre_dogrulama.py               # 60 sn olc + analiz + rapor
    python arac/filtre_dogrulama.py --sure 120
    python arac/filtre_dogrulama.py --analiz veri/filtre_dogrulama_XXXX.csv
================================================================================
"""
import argparse
import csv
import os
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJ_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _PROJ_ROOT)

VERI_DIR = os.path.join(_PROJ_ROOT, "veri")
CSV_KOLON = ["t", "hamx", "hamy", "hamz", "fx", "fy", "fz", "ttx", "tty", "ttz"]

TAU_MAX = 2.0        # gecikme taramasi ust siniri (s)
TAU_ADIM = 0.05      # tarama adimi (s)


def olc(sure_s, csv_yolu):
    from sdk import drone_sdk as drone
    from fusion.inovasyonlu_j_v2 import GNSSDuzeltici

    if not drone.connect():
        print("[HATA] Oyuna baglanilamadi. Oyun acik ve PLAY modunda mi?")
        print("       WEB ARAYUZU KAPALI olmali (oyun tek TCP baglantisi kabul eder).")
        return None
    time.sleep(1.5)
    if not drone.get_debug_truth().get("available"):
        print("[HATA] DEBUG TRUTH AKMIYOR (available=False). Bu arac truth-tabanlidir.")
        drone.disconnect()
        return None
    print("[OK] Oyuna baglanildi; debug truth AKIYOR. Filtre pipeline varsayilanlariyla.")

    filtre = GNSSDuzeltici()                 # pipeline ile AYNI varsayilanlar
    os.makedirs(VERI_DIR, exist_ok=True)
    f = open(csv_yolu, "w", newline="", encoding="utf-8")
    w = csv.writer(f)
    w.writerow(CSV_KOLON)

    t0 = time.perf_counter()
    son_ham = None
    filt = None
    n = 0
    print("[OLCUM] %d sn, ~50 Hz ornekleme (filtre yalnizca YENI ham pakette beslenir)..." % sure_s)
    while True:
        t = time.perf_counter() - t0
        if t >= sure_s:
            break
        ham = drone.get_target_location()
        if ham != son_ham:                   # yeni paket -> filtreyi besle (pipeline deseni)
            son_ham = ham
            filtre.guncelle(ham[0], ham[1], ham[2])
            d = filtre.durum_guduum()
            filt = (None if d is None else d["pos"])   # lead'siz ANLIK kestirim
        truth = drone.get_debug_truth()
        tt = truth["target"]["position"] if truth.get("available") else ("", "", "")
        fi = filt if filt is not None else ("", "", "")
        w.writerow(["%.4f" % t,
                    "%.1f" % ham[0], "%.1f" % ham[1], "%.1f" % ham[2],
                    ("%.1f" % fi[0]) if filt else "", ("%.1f" % fi[1]) if filt else "",
                    ("%.1f" % fi[2]) if filt else "",
                    ("%.1f" % tt[0]) if truth.get("available") else "",
                    ("%.1f" % tt[1]) if truth.get("available") else "",
                    ("%.1f" % tt[2]) if truth.get("available") else ""])
        n += 1
        if n % 250 == 0:
            f.flush()
            print("  ... t=%.0fs ornek=%d" % (t, n))
        time.sleep(0.02)                     # ~50 Hz
    f.close()
    drone.disconnect()
    print("[OLCUM] Bitti: %d ornek -> %s" % (n, csv_yolu))
    return csv_yolu


# ----------------------------------------------------------------------------
#  Analiz
# ----------------------------------------------------------------------------
def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return np.nan


def _seri_oku(csv_yolu):
    with open(csv_yolu, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    t = np.array([_f(r["t"]) for r in rows])
    ham = np.array([[_f(r["hamx"]), _f(r["hamy"]), _f(r["hamz"])] for r in rows])
    fil = np.array([[_f(r["fx"]), _f(r["fy"]), _f(r["fz"])] for r in rows])
    tru = np.array([[_f(r["ttx"]), _f(r["tty"]), _f(r["ttz"])] for r in rows])
    return t, ham, fil, tru


def _truth_interp(t, tru, t_sor):
    """Truth konumunu t_sor anlarina eksen eksen dogrusal enterpole et."""
    ok = ~np.any(np.isnan(tru), axis=1)
    out = np.full((len(t_sor), 3), np.nan)
    if ok.sum() < 2:
        return out
    for e in range(3):
        out[:, e] = np.interp(t_sor, t[ok], tru[ok, e], left=np.nan, right=np.nan)
    return out


def _metrikler(t, seri, tru):
    """(rmse_m, max_m, tau_s, rmse_tau_m): dogrudan hata + en iyi gecikme oturmasi."""
    ok = ~(np.any(np.isnan(seri), axis=1) | np.any(np.isnan(tru), axis=1))
    if ok.sum() < 20:
        return None
    e = np.linalg.norm(seri[ok] - tru[ok], axis=1) / 100.0        # cm -> m
    rmse = float(np.sqrt(np.mean(e ** 2)))
    emax = float(np.max(e))
    # gecikme taramasi: seri(t) ~ truth(t - tau) icin en iyi tau
    en_iyi = (0.0, rmse)
    for tau in np.arange(0.0, TAU_MAX + 1e-9, TAU_ADIM):
        tru_gecik = _truth_interp(t, tru, t[ok] - tau)
        m = ~np.any(np.isnan(tru_gecik), axis=1)
        if m.sum() < 20:
            continue
        e2 = np.linalg.norm(seri[ok][m] - tru_gecik[m], axis=1) / 100.0
        r2 = float(np.sqrt(np.mean(e2 ** 2)))
        if r2 < en_iyi[1]:
            en_iyi = (float(tau), r2)
    return {"rmse_m": rmse, "max_m": emax, "tau_s": en_iyi[0], "rmse_tau_m": en_iyi[1]}


def analiz(csv_yolu):
    t, ham, fil, tru = _seri_oku(csv_yolu)
    m_ham = _metrikler(t, ham, tru)
    m_fil = _metrikler(t, fil, tru)
    print("\n" + "=" * 68)
    print(" FILTRE DOGRULAMA RAPORU  (%s)" % os.path.basename(csv_yolu))
    print("=" * 68)
    if m_ham is None or m_fil is None:
        print(" [HATA] Yeterli ortusen ornek yok (truth/filtre bos?).")
        return None
    print(" %-14s %10s %10s %12s %16s" % ("SERI", "RMSE (m)", "MAX (m)",
                                          "GECIKME (s)", "RMSE@gecikme (m)"))
    print(" %-14s %10.2f %10.2f %12.2f %16.2f"
          % ("ham GPS", m_ham["rmse_m"], m_ham["max_m"], m_ham["tau_s"], m_ham["rmse_tau_m"]))
    print(" %-14s %10.2f %10.2f %12.2f %16.2f"
          % ("filtre (J)", m_fil["rmse_m"], m_fil["max_m"], m_fil["tau_s"], m_fil["rmse_tau_m"]))
    kazanc = 100.0 * (m_ham["rmse_m"] - m_fil["rmse_m"]) / max(m_ham["rmse_m"], 1e-9)
    print("\n RMSE kazanci     : %%%.0f  (%s)"
          % (kazanc, "filtre HAM'dan iyi" if kazanc > 0 else "filtre HAM'dan KOTU!"))
    print(" Gecikme yorumu   : ham tau=%.2fs sim'in verdigi gecikme+ratelimit etkisi;"
          % m_ham["tau_s"])
    print("                    filtre tau=%.2fs kestirimin kalan gecikmesi (kucuk olmali;"
          % m_fil["tau_s"])
    print("                    lead/ongoru guduumde ayrica telafi eder).")
    print("=" * 68)
    return {"ham": m_ham, "filtre": m_fil, "kazanc_pct": kazanc}


def main():
    ap = argparse.ArgumentParser(description="Fusion filtre dogrulama (truth-tabanli)")
    ap.add_argument("--sure", type=float, default=60.0, help="olcum suresi (sn)")
    ap.add_argument("--analiz", type=str, default=None,
                    help="yakalama YAPMADAN var olan CSV'yi analiz et")
    arg = ap.parse_args()
    if arg.analiz:
        r = analiz(arg.analiz)
    else:
        yol = os.path.join(VERI_DIR, time.strftime("filtre_dogrulama_%Y%m%d_%H%M%S.csv"))
        yol = olc(arg.sure, yol)
        r = analiz(yol) if yol else None
    sys.exit(0 if r else 1)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
================================================================================
GELISTIRME/DOGRULAMA ARACI — gorev ucusunda kullanilmaz. (Osilasyon teshisi;
mevcut ucus CSV'lerinden, SIM GEREKMEZ; teslim paketine girmez.)
================================================================================
TESHIS-2 — ROLL OSILASYON IMZASI (saha gozlemi: surekli saga-sola roll)
================================================================================
YAKLASMA/ARAMA (GPS yaklasma) fazi roll_cmd zaman serisinden osilasyonun
KAYNAGINI ayirt eder. Uc hipotez (kanitla):
  (i)   ORNEK-TUTMA ZIPLAMASI: roll periyodu ~ DEV-truth/hedef ornek yenilenme
        araligi -> hedef konumu her ornekte zipliyor, yanal hata jerk yapiyor.
  (ii)  EKSEN KARISMASI / YAW-SERVO YOK: roll_cmd, yaw_hata (hedef bearing -
        drone yaw) ile YUKSEK korelasyonlu -> burun hedefe DONMEDEN roll ile
        yana suzuluyor (kamera hedefe bakmiyor; Talon FOV'a girmiyor).
  (iii) PD KAZANC: yukaridakiler degilse -> yanal kontrolcu oz-osilasyonu (kazanc).

CIKTI: roll periyodu/genligi, yaw_cmd kullanimi, korelasyonlar, ornek-yenilenme
periyodu ve HANGI HIPOTEZ + kaniti. (Duzeltme sirasi DUZELTME-2'de; konvansiyon
dogrulanmadan kazanc ayari YAPILMAZ.)

Kullanim: python arac/osilasyon_teshis.py [ucus_log_*.csv]  (yoksa en yeni buyuk)
================================================================================
"""
import csv
import glob
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJ = os.path.dirname(_HERE)


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _seri(rows, kol):
    return [(_num(r.get("t_perf")), _num(r.get(kol))) for r in rows
            if _num(r.get("t_perf")) is not None and _num(r.get(kol)) is not None]


def _periyot_isaret_degisim(seri):
    """Ortalama-cikarilmis serinin ISARET DEGISIMI (sifir gecis) sayisindan
    baskin periyot (2*T/gecis) + genlik (RMS). -> (periyot_s, genlik, gecis)."""
    if len(seri) < 8:
        return None, 0.0, 0
    ts = [t for t, _ in seri]
    ys = [y for _, y in seri]
    ort = sum(ys) / len(ys)
    yc = [y - ort for y in ys]
    gecis = sum(1 for i in range(1, len(yc)) if yc[i - 1] * yc[i] < 0)
    T = ts[-1] - ts[0]
    periyot = (2.0 * T / gecis) if gecis > 0 else None
    rms = math.sqrt(sum(v * v for v in yc) / len(yc))
    return periyot, rms, gecis


def _korelasyon(a, b):
    n = min(len(a), len(b))
    if n < 8:
        return 0.0
    a = a[:n]; b = b[:n]
    ma = sum(a) / n; mb = sum(b) / n
    va = sum((x - ma) ** 2 for x in a); vb = sum((x - mb) ** 2 for x in b)
    if va < 1e-12 or vb < 1e-12:
        return 0.0
    cov = sum((a[i] - ma) * (b[i] - mb) for i in range(n))
    return cov / math.sqrt(va * vb)


def _ornek_yenilenme_periyodu(rows):
    """est_x DEGISTIGI anlar arasi ortalama sure (DEV/hedef ornek yenilenme)."""
    t_deg, son = [], None
    for r in rows:
        ex, t = _num(r.get("est_x")), _num(r.get("t_perf"))
        if ex is None or t is None:
            continue
        if son is None or abs(ex - son) > 1e-6:
            t_deg.append(t); son = ex
    if len(t_deg) < 3:
        return None
    farklar = [t_deg[i] - t_deg[i - 1] for i in range(1, len(t_deg))]
    farklar = [d for d in farklar if d > 1e-6]
    return (sum(farklar) / len(farklar)) if farklar else None


def teshis(rows):
    # YAKLASMA/ARAMA fazi: est dolu (GPS yaklasma; roll orada oscile ediyor)
    appr = [r for r in rows if _num(r.get("est_x")) is not None]
    if len(appr) < 20:
        return {"sonuc": "YAKLASMA/ARAMA satiri yetersiz (%d)" % len(appr)}
    roll = _seri(appr, "roll_cmd")
    periyot, genlik, gecis = _periyot_isaret_degisim(roll)
    yaw_cmd = [y for _, y in _seri(appr, "yaw_cmd")]
    yaw_cmd_std = (sum((v) ** 2 for v in yaw_cmd) / len(yaw_cmd)) ** 0.5 if yaw_cmd else 0.0
    yaw_cmd_aktif = sum(1 for v in yaw_cmd if abs(v) > 0.02) / max(len(yaw_cmd), 1)
    # korelasyon roll_cmd vs yaw_err
    rc = [y for _, y in roll]
    ye = [y for _, y in _seri(appr, "yaw_err")]
    kor_roll_yawerr = _korelasyon(rc, ye)
    yaw_err_mutlak_ort = sum(abs(v) for v in ye) / len(ye) if ye else 0.0
    orn_periyot = _ornek_yenilenme_periyodu(appr)

    # HIPOTEZ karari
    hip = []
    kanit = []
    if orn_periyot and periyot and abs(periyot - orn_periyot) / max(orn_periyot, 1e-6) < 0.4:
        hip.append("i (ornek-tutma ziplama)")
        kanit.append("roll periyodu %.2fs ~ ornek yenilenme %.2fs" % (periyot, orn_periyot))
    if abs(kor_roll_yawerr) > 0.3 or (yaw_cmd_aktif < 0.1 and yaw_err_mutlak_ort > 0.3):
        hip.append("ii (eksen karismasi / yaw-servo YOK)")
        kanit.append("corr(roll,yaw_err)=%.2f, yaw_cmd aktif %%%.0f, |yaw_err| ort %.2f rad"
                     % (kor_roll_yawerr, 100 * yaw_cmd_aktif, yaw_err_mutlak_ort))
    if not hip:
        hip.append("iii (PD kazanc / oz-osilasyon)")
        kanit.append("ornek-tutma ve eksen-karismasi imzasi zayif -> kazanc suphesi")
    return {
        "appr_satir": len(appr), "roll_periyot_s": periyot, "roll_genlik_rms": genlik,
        "roll_isaret_degisim": gecis, "yaw_cmd_std": yaw_cmd_std, "yaw_cmd_aktif_oran": yaw_cmd_aktif,
        "corr_roll_yawerr": kor_roll_yawerr, "yaw_err_mutlak_ort_rad": yaw_err_mutlak_ort,
        "ornek_yenilenme_s": orn_periyot, "hipotez": hip, "kanit": kanit,
    }


def metrikler(rows):
    """C ONCE/SONRA + TEPE YAW-RATE ozet: roll RMS, |yaw_err| ort (deg), yaw-rate
    p95/maks (deg/s, wrap-aware). YAKLASMA/ARAMA (est dolu) satirlar uzerinden."""
    appr = [r for r in rows if _num(r.get("est_x")) is not None]
    rc = [_num(r.get("roll_cmd")) for r in appr if _num(r.get("roll_cmd")) is not None]
    ye = [_num(r.get("yaw_err")) for r in appr if _num(r.get("yaw_err")) is not None]
    roll_rms = (sum(v * v for v in rc) / len(rc)) ** 0.5 if rc else 0.0
    ye_ort = math.degrees(sum(abs(v) for v in ye) / len(ye)) if ye else 0.0
    yr, prev = [], None
    for r in appr:
        y, t = _num(r.get("drone_yaw_deg")), _num(r.get("t_perf"))
        if y is None or t is None:
            continue
        if prev is not None:
            dt = t - prev[1]
            if 1e-3 < dt < 0.5:
                dyaw = (y - prev[0] + 180.0) % 360.0 - 180.0     # wrap
                yr.append(abs(dyaw / dt))
        prev = (y, t)
    yr.sort()
    return {"n": len(appr), "roll_rms": roll_rms, "yaw_err_ort_deg": ye_ort,
            "yaw_rate_p95": (yr[min(len(yr) - 1, int(len(yr) * 0.95))] if yr else 0.0),
            "yaw_rate_maks": (max(yr) if yr else 0.0)}


def kiyasla(yol_once, yol_sonra):
    """C: ONCE/SONRA tek tablo (roll RMS + |yaw_err| + tepe yaw-rate)."""
    def _yukle(y):
        with open(y, encoding="utf-8", errors="replace", newline="") as f:
            return metrikler(list(csv.DictReader(f)))
    o, s = _yukle(yol_once), _yukle(yol_sonra)
    print("=" * 70)
    print(" C — DUZELTME-1 ONCE/SONRA (yaw-servo/turn-then-advance)")
    print("=" * 70)
    print(" %-22s %12s %12s   %s" % ("metrik", "ONCE", "SONRA", "yorum"))
    print(" %-22s %12.3f %12.3f   %s" % ("roll_cmd RMS", o["roll_rms"], s["roll_rms"],
          "dusmeli (osilasyon soner)" if s["roll_rms"] < o["roll_rms"] else "DUSMEDI!"))
    print(" %-22s %12.1f %12.1f   %s" % ("|yaw_err| ort (deg)", o["yaw_err_ort_deg"],
          s["yaw_err_ort_deg"], "dusmeli (<10 kabul)" if s["yaw_err_ort_deg"] < o["yaw_err_ort_deg"] else "DUSMEDI!"))
    yr = s["yaw_rate_p95"]
    yorum = ("<15 -> SIM yaw otoritesi kisitli; donus fazi suresi/esigi Cfg'de ayarla"
             if yr < 15.0 else ">=15 -> yaw calisiyor; onceki zayif olcum kisa step'tendi")
    print(" %-22s %12s %12.1f   %s" % ("TEPE yaw-rate p95 (deg/s)", "-", yr, yorum))
    print(" %-22s %12s %12.1f" % ("  yaw-rate maks (deg/s)", "-", s["yaw_rate_maks"]))
    return 0


def main():
    if len(sys.argv) >= 4 and sys.argv[1] == "--kiyasla":
        return kiyasla(sys.argv[2], sys.argv[3])
    yol = sys.argv[1] if len(sys.argv) > 1 else None
    if not yol:
        lst = [f for f in glob.glob(os.path.join(_PROJ, "veri", "ucus_log_*.csv"))
               if os.path.getsize(f) > 500000]           # buyuk (gercek ucus) kosular
        yol = sorted(lst)[-1] if lst else None
    if not yol or not os.path.isfile(yol):
        print("CSV yok."); return 1
    with open(yol, encoding="utf-8", errors="replace", newline="") as f:
        rows = list(csv.DictReader(f))
    d = teshis(rows)
    print("=" * 70)
    print(" OSILASYON TESHISI (TESHIS-2) — %s" % os.path.basename(yol))
    print("=" * 70)
    if "sonuc" in d:
        print(" ", d["sonuc"]); return 0
    print(" YAKLASMA/ARAMA satir: %d" % d["appr_satir"])
    print(" roll_cmd: periyot=%s s ; genlik(RMS)=%.3f ; isaret-degisim=%d"
          % (round(d["roll_periyot_s"], 3) if d["roll_periyot_s"] else "-",
             d["roll_genlik_rms"], d["roll_isaret_degisim"]))
    print(" yaw_cmd : std=%.3f ; aktif(|.|>0.02) oran=%%%.0f  <- ~0 ise BURUN-HEDEFE YOK"
          % (d["yaw_cmd_std"], 100 * d["yaw_cmd_aktif_oran"]))
    print(" corr(roll_cmd, yaw_err)=%.2f ; |yaw_err| ort=%.2f rad (%.0f deg)"
          % (d["corr_roll_yawerr"], d["yaw_err_mutlak_ort_rad"],
             math.degrees(d["yaw_err_mutlak_ort_rad"])))
    print(" ornek yenilenme periyodu=%s s"
          % (round(d["ornek_yenilenme_s"], 3) if d["ornek_yenilenme_s"] else "-"))
    print("-" * 70)
    print(" HIPOTEZ: %s" % " + ".join(d["hipotez"]))
    for k in d["kanit"]:
        print("   kanit: %s" % k)
    return 0


if __name__ == "__main__":
    sys.exit(main())

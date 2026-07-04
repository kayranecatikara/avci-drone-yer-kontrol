# -*- coding: utf-8 -*-
"""
================================================================================
GELISTIRME/DOGRULAMA ARACI — gorev ucusunda ve degerlendirme kosusunda
kullanilmaz. (Truth-tabanli TP/FP analizi; teslim paketine girmez.)
================================================================================
TP/FP AYRISTIRMA + KILIT ENGELI ANATOMISI (referans kosu analizi)
================================================================================
Soru: "cizilen bbox'lar gercekten Talon'da miydi, yoksa dag/tas uzerinde mi?"
CSV bbox SAYISI tek basina Talon kanidi DEGILDIR.

YONTEM (TP/FP): her tespit karesinde, AYNI an truth hedef konumunu kamera
modeliyle (detection/kamera_model) goruntuye reprojekte et; bbox merkezi ile
reprojeksiyon arasindaki mesafe ESIK altindaysa TP, degilse FP. Esik OLCEK-
DUYARLI: k * bbox_kosegeni (varsayilan k=0.75 -> bbox'in ~0.75 kosegeni kadar
sapma hedefi hala sarar; secim gerekce: kucuk/uzak hedefte bbox kosegeni ~tespit
belirsizligi mertebesinde). Normalize goruntu koordinatinda calisir (W,H mutlak
GEREKMEZ; f_x/W sabit=0.2603, aspect 16:9).

VERI GEREKSINIMI: tespit satirinda (vis_gordu=1) AYNI an truth hedef konumu
(est_x/y/z, DEV kaynakta = truth) + drone pozu. NOT: mevcut _log_gorsel truth'u
YAZMIYOR (est_* yalniz ARAMA/TAKIP'te) -> GORSEL_GUDUM tespitlerinde truth YOK.
Bu arac truth-yaknligi tol icinde bulunamazsa TP/FP'yi ATLAR ve raporlar; CSV
anatomisi (conf/engel/coast/tespit-orani) HER durumda cikar. Gelecek kosu icin
cozum: _log_gorsel'e est_* eklemek (ayni source feed; DEV'de = truth).

Kullanim: python arac/tp_fp_analiz.py [ucus_log_*.csv]  (yoksa en yeni)
================================================================================
"""
import bisect
import csv
import glob
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJ = os.path.dirname(_HERE)
sys.path.insert(0, _PROJ)

import numpy as np
from detection import kamera_model as km
from guidance.ana_kontrol import Cfg

TP_K = 0.75            # esik = TP_K * bbox_kosegeni (normalize)
TRUTH_TOL_SN = 0.15    # tespit->truth zaman farki bu ustundeyse truth "yok" say
KILIT_HEDEF_CONF = 0.72   # kullanicinin sordugu hipotetik siki esik (kiyas icin)


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _oku(yol):
    with open(yol, "r", encoding="utf-8", errors="replace", newline="") as f:
        return list(csv.DictReader(f))


def _bbox_merkez_norm(r):
    """vis_ex/ey (IBVS hata, EMA-yumusatilmis) -> bbox merkezi normalize [0,1].
    ex=(cx-W/2)/(W/2) -> cx_norm=(ex+1)/2. EMA lag CAVEAT (ham merkez loglanmiyor)."""
    ex, ey = _num(r.get("vis_ex")), _num(r.get("vis_ey"))
    if ex is None or ey is None:
        return None
    return (ex + 1.0) / 2.0, (ey + 1.0) / 2.0


def _bbox_kosegen_norm(r):
    ky, kd = _num(r.get("kaplama_yatay")), _num(r.get("kaplama_dikey"))
    if ky is None or kd is None:
        return None
    return math.hypot(ky, kd)


def _reproj_truth_norm(truth_world, drone_pos, roll, pitch, yaw_deg):
    """truth dunya noktasi -> normalize goruntu (u_norm,v_norm) veya None (arka)."""
    p_kam = km.dunya_to_kamera(truth_world, drone_pos, roll, pitch, yaw_deg)
    K = km.K_matrisi(16.0, 9.0)                 # aspect 16:9; normalize icin yeterli
    uv = km.izdusur(p_kam, K)
    if uv is None:
        return None
    return uv[0] / 16.0, uv[1] / 9.0


def _truth_zaman_serisi(rows):
    """est_* dolu satirlardan (t_perf -> truth_world) sirali seri."""
    ts, pts = [], []
    for r in rows:
        ex, t = _num(r.get("est_x")), _num(r.get("t_perf"))
        if ex is None or t is None:
            continue
        ts.append(t)
        pts.append((ex, _num(r.get("est_y")), _num(r.get("est_z"))))
    return ts, pts


def _en_yakin_truth(ts, pts, t):
    if not ts:
        return None, None
    i = bisect.bisect_left(ts, t)
    aday = [j for j in (i - 1, i) if 0 <= j < len(ts)]
    if not aday:
        return None, None
    j = min(aday, key=lambda k: abs(ts[k] - t))
    return pts[j], abs(ts[j] - t)


# ---------------------------------------------------------------------------
#  TP/FP (truth varsa)
# ---------------------------------------------------------------------------
def tp_fp(rows):
    ts, pts = _truth_zaman_serisi(rows)
    vis = [r for r in rows if r.get("vis_gordu") in ("1", "1.0")]
    olcules = [r for r in vis if r.get("tespit_mi") in ("1", "1.0")]   # OLCULEN (coast degil)
    sonuc = {"tp": 0, "fp": 0, "truth_yok": 0, "arka": 0, "toplam_olculen": len(olcules)}
    gaps = []
    for r in olcules:
        t = _num(r.get("t_perf"))
        tw, gap = _en_yakin_truth(ts, pts, t) if t is not None else (None, None)
        if gap is not None:
            gaps.append(gap)
        if tw is None or gap is None or gap > TRUTH_TOL_SN or None in tw:
            sonuc["truth_yok"] += 1
            continue
        drone = (_num(r.get("drone_x")), _num(r.get("drone_y")), _num(r.get("drone_z")))
        roll, pitch, yaw = _num(r.get("drone_roll")), _num(r.get("drone_pitch")), _num(r.get("drone_yaw_deg"))
        if None in drone or None in (roll, pitch, yaw):
            sonuc["truth_yok"] += 1
            continue
        uv = _reproj_truth_norm(tw, drone, roll, pitch, yaw)
        if uv is None:
            sonuc["arka"] += 1                     # truth kamera arkasinda (hedef gorunmuyor)
            continue
        mc = _bbox_merkez_norm(r)
        kos = _bbox_kosegen_norm(r)
        if mc is None or kos is None:
            sonuc["truth_yok"] += 1
            continue
        d = math.hypot(mc[0] - uv[0], mc[1] - uv[1])
        if d <= TP_K * max(kos, 1e-6):
            sonuc["tp"] += 1
        else:
            sonuc["fp"] += 1
    sonuc["gap_medyan"] = sorted(gaps)[len(gaps) // 2] if gaps else None
    return sonuc


# ---------------------------------------------------------------------------
#  CSV anatomisi (truth GEREKMEZ) — HER durumda
# ---------------------------------------------------------------------------
def _blok_sureleri(vis, alan, deger):
    """Ardisik (alan==deger) bloklarinin sureleri (t_perf farki)."""
    sureler, blok_bas = [], None
    for r in vis:
        t = _num(r.get("t_perf"))
        if t is None:
            continue
        eslesme = (r.get(alan) == deger) if not callable(deger) else deger(r.get(alan))
        if eslesme and blok_bas is None:
            blok_bas = t
        elif not eslesme and blok_bas is not None:
            sureler.append(t - blok_bas)
            blok_bas = None
    return sureler


def _p(lst, q):
    if not lst:
        return None
    s = sorted(lst)
    return s[min(len(s) - 1, int(len(s) * q))]


def anatomi(rows):
    vis = [r for r in rows if r.get("vis_gordu") in ("1", "1.0")]
    olculen = [r for r in vis if r.get("tespit_mi") in ("1", "1.0")]
    confs = [_num(r.get("vis_conf")) for r in olculen if _num(r.get("vis_conf")) is not None]
    from collections import Counter
    engel = Counter(r.get("kilit_engel") or "(sayan)" for r in vis)
    # conf dagilimi esiklere gore
    conf_dag = {
        "<0.45": sum(1 for c in confs if c < 0.45),
        "0.45-0.72": sum(1 for c in confs if 0.45 <= c < KILIT_HEDEF_CONF),
        ">=0.72": sum(1 for c in confs if c >= KILIT_HEDEF_CONF),
    }
    coast = _blok_sureleri(vis, "tespit_mi", lambda v: v in ("0", "0.0", "", None))
    confirmed = _blok_sureleri(vis, "track_durumu", "CONFIRMED")
    tespit_orani = len(olculen) / max(len(vis), 1)
    return {
        "vis": len(vis), "olculen": len(olculen), "tespit_orani": tespit_orani,
        "conf_medyan": (sorted(confs)[len(confs) // 2] if confs else None),
        "conf_dag": conf_dag, "engel": dict(engel),
        "coast_medyan_ms": (_p(coast, 0.5) or 0) * 1000, "coast_p90_ms": (_p(coast, 0.9) or 0) * 1000,
        "coast_maks_ms": (max(coast) if coast else 0) * 1000, "coast_blok": len(coast),
        "confirmed_medyan_sn": _p(confirmed, 0.5), "confirmed_maks_sn": (max(confirmed) if confirmed else 0),
    }


def main():
    yol = sys.argv[1] if len(sys.argv) > 1 else None
    if not yol:
        lst = sorted(glob.glob(os.path.join(_PROJ, "veri", "ucus_log_*.csv")))
        yol = lst[-1] if lst else None
    if not yol or not os.path.isfile(yol):
        print("CSV yok."); return 1
    rows = _oku(yol)
    print("=" * 70)
    print(" TP/FP + KILIT ENGELI ANATOMISI — %s" % os.path.basename(yol))
    print("=" * 70)
    print(" handoff/kilit conf esigi (kod): VIS_CONF_MIN = %.2f, VIS_N_LOCK = %d"
          % (Cfg.VIS_CONF_MIN, Cfg.VIS_N_LOCK))
    print(" -> faz gecisi VE kilit AYNI esikle (0.72 kodda YOK). FP-track %.2f-0.72"
          % Cfg.VIS_CONF_MIN)
    print("    arasi hem GORSEL_GUDUM'u tetikler hem kilit sayar (daga-gudum riski).")

    a = anatomi(rows)
    print("\n --- CSV ANATOMISI (truth gerekmez) ---")
    print(" GORSEL_GUDUM tespit karesi (vis): %d ; OLCULEN (coast degil): %d ; tespit orani: %.1f%%"
          % (a["vis"], a["olculen"], 100 * a["tespit_orani"]))
    print(" conf medyan (olculen): %s" % (round(a["conf_medyan"], 3) if a["conf_medyan"] else "-"))
    print(" conf dagilimi: <0.45=%d  0.45-0.72=%d  >=0.72=%d"
          % (a["conf_dag"]["<0.45"], a["conf_dag"]["0.45-0.72"], a["conf_dag"][">=0.72"]))
    print(" engel dagilimi (kare):")
    for k, v in sorted(a["engel"].items(), key=lambda kv: -kv[1]):
        print("    %-16s %d" % (k, v))
    print(" coast blok: %d ; sure medyan=%.0f ms p90=%.0f ms maks=%.0f ms (200 ms kopru esigi)"
          % (a["coast_blok"], a["coast_medyan_ms"], a["coast_p90_ms"], a["coast_maks_ms"]))
    print(" CONFIRMED kesintisiz: medyan=%s sn maks=%.1f sn"
          % (round(a["confirmed_medyan_sn"], 2) if a["confirmed_medyan_sn"] else "-", a["confirmed_maks_sn"]))

    print("\n --- TP/FP (truth-reprojeksiyon) ---")
    s = tp_fp(rows)
    if s["tp"] + s["fp"] == 0:
        print(" [ATLANDI] Olculen tespit anlarinda truth BULUNAMADI (en yakin truth")
        print("           zaman farki > %.0f ms). Sebep: _log_gorsel est_* yazmiyor;" % (TRUTH_TOL_SN * 1000))
        print("           truth yalniz ARAMA/TAKIP'te loglaniyor (tespit_yok: %d)." % s["truth_yok"])
        print("           -> RIGOROUS TP/FP bu referans CSV'den CIKARILAMAZ.")
        print("           Cozum: _log_gorsel'e est_* ekle (gelecek kosu analiz edilebilir).")
    else:
        tp, fp = s["tp"], s["fp"]
        prec = tp / max(tp + fp, 1)
        print(" olculen tespit: %d ; TP=%d FP=%d (truth_yok=%d, arka=%d)"
              % (s["toplam_olculen"], tp, fp, s["truth_yok"], s["arka"]))
        print(" PRECISION (cizilen kutunun hedefte olma orani): %.1f%%" % (100 * prec))
    return 0


if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
"""
================================================================================
  ONDE Mi / GERI Mi  --  "aracimiz karsi aracin onunde ve arkaya gidiyor"
================================================================================
Kullanici sikayeti iki AYRI iddia iceriyor; ikisi de olculebilir:

  (A) KONUM: bizim arac hedefin ONUNDE mi?
      s = (biz - hedef) . t_hat        t_hat = hedefin gidis yonu
      s > 0  -> hedefin ONUNDEYIZ (hedef bizi arkadan yakaliyor)
      s < 0  -> hedefin ARKASINDAYIZ (klasik kuyruk takibi)

  (B) HAREKET: kendi burnumuza gore GERI mi gidiyoruz?
      vf = v_own . burun_hat ;  vf < 0 -> burun bir yone, govde ters yone

⚠⚠ LOG KOLONLARI YANILTICI (2026-08-21 olculdu, ucus_log_*.csv):
    drone_speed    : TAMAMEN BOS (0/58015)
    vown_x/vown_y  : HEP 0.0
    true_dx/dy/dz  : hedef hizi DEGIL -- degerleri drone_x/drone_y ile BIREBIR AYNI
    v_close/vdx/vdy: BOS
  Bu yuzden hiz ASLA log kolonundan alinmaz, KONUM TUREVINDEN hesaplanir.
  (Ayrica bkz. talon-olcum-tuzaklari: SDK hizi +0.240 m/s yanli.)

⚠ BIRIM: konumlar SANTIMETRE (UE dunyasi). gercek_mesafe de cm.
  4169.9 -> 41.7 m. Betik hepsini metreye cevirir.

⚠ ISARET GELENEGI VARSAYILMAZ, OLCULUR: bu depoda ayna/isaret hatasi UC KEZ
  tekrarladi. Burun vektoru ile turevden gelen hiz vektorunun ortusmesi once
  dogrulanir; ortusmuyorsa "geri gidiyor" cikarimi yapilmaz.

⚠ GECERSIZ SATIR SUZGECI: mesafe<=0.5 m, ve DONMUS telemetri (ardisik satirda
  (drone_x,drone_y,true_tx,true_ty) imzasi ayni -> oyun cokmus).

KULLANIM
--------------------------------------------------------------------------------
    python arac/onde_arkada_teshis.py                    # en yeni ucus logu
    python arac/onde_arkada_teshis.py veri/ucus_log_X.csv
================================================================================
"""
import csv
import glob
import math
import os
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CM = 100.0
TUREV_MIN_DT = 0.02          # bundan kisa araliklarda turev gurultulu
TUREV_MAX_DT = 0.60          # bundan uzun aralik = kopukluk, turev gecersiz
HIZ_MIN = 0.5                # m/s, altinda yon tanimsiz


def f(s):
    try:
        v = float(s)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def oku(yol):
    ham, gecersiz, donmus = [], 0, 0
    onceki = None
    with open(yol, newline="", encoding="utf-8", errors="replace") as fh:
        for r in csv.DictReader(fh):
            d = f(r.get("gercek_mesafe"))
            dx, dy = f(r.get("drone_x")), f(r.get("drone_y"))
            tx, ty = f(r.get("true_tx")), f(r.get("true_ty"))
            t = f(r.get("t_perf")) or f(r.get("t_wall"))
            if None in (d, dx, dy, tx, ty, t) or d <= 50.0:      # 50 cm
                gecersiz += 1
                continue
            imza = (round(dx, 2), round(dy, 2), round(tx, 2), round(ty, 2))
            if imza == onceki:
                donmus += 1
                continue
            onceki = imza
            ham.append({"t": t, "dx": dx / CM, "dy": dy / CM,
                        "tx": tx / CM, "ty": ty / CM, "d": d / CM,
                        "yaw": f(r.get("drone_yaw_deg")),
                        "faz": (r.get("phase") or "?").strip(),
                        "vis": (r.get("vis_faz") or "").strip()})
    return ham, gecersiz, donmus


def turevle(ham):
    """konum turevinden hiz (m/s). Kopuk araliklar atlanir."""
    for i in range(1, len(ham)):
        a, b = ham[i - 1], ham[i]
        dt = b["t"] - a["t"]
        if not (TUREV_MIN_DT <= dt <= TUREV_MAX_DT):
            continue
        b["vx"] = (b["dx"] - a["dx"]) / dt
        b["vy"] = (b["dy"] - a["dy"]) / dt
        b["tvx"] = (b["tx"] - a["tx"]) / dt
        b["tvy"] = (b["ty"] - a["ty"]) / dt
    return [r for r in ham if "vx" in r]


def y(v, q):
    if not v:
        return float("nan")
    s = sorted(v)
    return s[min(len(s) - 1, max(0, int(round(q * (len(s) - 1)))))]


def main():
    yol = sys.argv[1] if len(sys.argv) > 1 else None
    if not yol:
        lst = sorted(glob.glob(os.path.join(KOK, "veri", "ucus_log_*.csv")),
                     key=os.path.getmtime)
        if not lst:
            print("ucus_log_*.csv yok"); return
        yol = lst[-1]
    print("[TESHIS] %s" % os.path.basename(yol))
    ham, gecersiz, donmus = oku(yol)
    print("[TESHIS] gecerli %d | gecersiz %d | donmus %d" % (len(ham), gecersiz, donmus))
    R = turevle(ham)
    print("[TESHIS] turev alinabilen %d" % len(R))
    if len(R) < 50:
        print("[TESHIS] yeterli veri yok"); return

    # ── 0) isaret geleneği: burun ile hareket ortusuyor mu ──────────────────
    oran = []
    for r in R:
        sp = math.hypot(r["vx"], r["vy"])
        if sp < HIZ_MIN or r["yaw"] is None:
            continue
        a = math.radians(r["yaw"])
        oran.append((r["vx"] * math.cos(a) + r["vy"] * math.sin(a)) / sp)
    print()
    print("  ── isaret geleneği kontrolü (burun vs hareket) ──")
    if not oran:
        print("    veri yok"); return
    ort = sum(oran) / len(oran)
    print("    cos(burun, hareket) ortalama %+.3f | ortanca %+.3f  (n=%d)"
          % (ort, y(oran, .5), len(oran)))
    if ort < 0.3:
        print("    ⛔ TUTMUYOR -> yaw gelenegi ters/kaymis olabilir.")
        print("       'geri gidiyor' cikarimi bu haliyle YAPILAMAZ.")
        gelenek = False
    else:
        print("    ✓ tutuyor -> cikarim gecerli")
        gelenek = True

    # ── A) hedefin onunde mi ────────────────────────────────────────────────
    kayit = []
    for r in R:
        tsp = math.hypot(r["tvx"], r["tvy"])
        if tsp < HIZ_MIN:
            continue
        thx, thy = r["tvx"] / tsp, r["tvy"] / tsp
        s = (r["dx"] - r["tx"]) * thx + (r["dy"] - r["ty"]) * thy
        q = (r["dx"] - r["tx"]) * (-thy) + (r["dy"] - r["ty"]) * thx
        kayit.append((s, q, r["d"], r))
    print()
    print("  ── (A) HEDEFE GORE KONUMUMUZ ──")
    if not kayit:
        print("    hedef hizi olculemedi"); return
    s_hep = [k[0] for k in kayit]
    onde = sum(1 for s, _, _, _ in kayit if s > 0)
    print("    hedefin ONUNDE   : %5.1f%%   (n=%d)" % (100.0 * onde / len(kayit), onde))
    print("    hedefin ARKASINDA: %5.1f%%   (n=%d)"
          % (100.0 * (len(kayit) - onde) / len(kayit), len(kayit) - onde))
    print("    eksen boyu s     : ortanca %+.1f m | p10 %+.1f | p90 %+.1f"
          % (y(s_hep, .5), y(s_hep, .1), y(s_hep, .9)))
    print("    yanal ayrilma    : ortanca %.1f m" % y([abs(k[1]) for k in kayit], .5))
    print()
    print("    menzile gore 'hedefin onundeyiz' orani:")
    for lo, hi in ((0, 10), (10, 25), (25, 60), (60, 1e9)):
        alt = [k for k in kayit if lo <= k[2] < hi]
        if alt:
            et = ("%d+ m" % lo) if hi > 1e8 else ("%d-%d m" % (lo, hi))
            print("      %-9s %5.1f%%   (n=%d)"
                  % (et, 100.0 * sum(1 for k in alt if k[0] > 0) / len(alt), len(alt)))

    # ── B) geri gidiyor muyuz ───────────────────────────────────────────────
    if gelenek:
        vf_all, geri = [], []
        yakin_t = yakin_geri = 0
        for r in R:
            sp = math.hypot(r["vx"], r["vy"])
            if sp < HIZ_MIN or r["yaw"] is None:
                continue
            a = math.radians(r["yaw"])
            vf = r["vx"] * math.cos(a) + r["vy"] * math.sin(a)
            vf_all.append(vf)
            if vf < 0:
                geri.append(vf)
            if r["d"] < 25:
                yakin_t += 1
                if vf < 0:
                    yakin_geri += 1
        print()
        print("  ── (B) KENDI BURNUMUZA GORE GERI GIDIYOR MUYUZ ──")
        print("    geri (vf<0)      : %5.2f%%   (n=%d / %d)"
              % (100.0 * len(geri) / max(1, len(vf_all)), len(geri), len(vf_all)))
        if geri:
            print("    geri hizi        : ortanca %.2f m/s | en kotu %.2f m/s"
                  % (abs(y(geri, .5)), abs(min(geri))))
        if yakin_t:
            print("    25 m icinde geri : %5.2f%%   (n=%d)"
                  % (100.0 * yakin_geri / yakin_t, yakin_t))
        print("    ileri hiz        : ortanca %.2f m/s" % y(vf_all, .5))

    # ── C) faz dagilimi ─────────────────────────────────────────────────────
    faz = {}
    for r in R:
        faz[r["faz"]] = faz.get(r["faz"], 0) + 1
    print()
    print("  ── (C) FAZ DAGILIMI ──")
    for k, v in sorted(faz.items(), key=lambda x: -x[1]):
        print("    %-14s %5.1f%%   (n=%d)" % (k, 100.0 * v / len(R), v))


if __name__ == "__main__":
    main()

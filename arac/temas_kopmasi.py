# -*- coding: utf-8 -*-
"""
================================================================================
  GORSEL TEMAS NEDEN KOPUYOR?  ("takip -> fren -> donme -> tekrar takip")
================================================================================
KULLANICI TARIFI: "karsi araci takip ediyor sonra bi anda frenleme ve kendi
etrafinda donme sonra tekrar takip ve boyle devam ediyor."

OLCULDU: 5818 gorsel faz epizodu, ortanca suresi YALNIZ 4.4 s. Yani sistem
surekli gorsel<->GPS arasinda gidip geliyor. Bu bir LIMIT DONGUSU ve her
donguste GPS yasasi da sifirdan kuruluyor (16 dk'da 145 kez olculdu).

SORU: epizot bitmeden hemen ONCE ne oluyor? Suclu aday dort tane:
    1) hedef KADRAJDAN CIKIYOR      -> cx/cy kenara dayanmis olmali
    2) hedef COK KUCULUYOR           -> boyut, kapinin (14 px) altina dusmus
    3) GUVEN dusuyor                 -> conf esigin altina inmis
    4) hicbiri                       -> dedektor bosluğu / hayalet

Bu betik her epizodun SON karelerine bakip hangisinin gerceklestigini sayar.

⚠ Kadraj: yasa cercevesi 640x480 (CX=320, CY=240). Kenar payi PAY_PX.
⚠ Epizot = bir bbox_ibvs_*.csv (yasa her gorsel fazda yeni dosya acar).
⚠ Son satirlar KUTUSUZ olabilir (kayip sayaci dolarken); bu yuzden SON
  GECERLI kutu aranir, ham son satir degil.
================================================================================
"""
import csv
import os
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGD = os.path.join(KOK, "kopru", "gazebo_kaynak", "logs")
IMG_W, IMG_H = 640.0, 480.0
PAY_PX = 60.0          # bu kadar kenara yaklastiysa "kadraj kenarinda"
BOYUT_KAPI = 14.0      # SupCfg boyut kapisi (px)
MIN_SATIR = 15


def f(s):
    try:
        v = float(s)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def y(v, q):
    if not v:
        return float("nan")
    s = sorted(v)
    return s[min(len(s) - 1, max(0, int(round(q * (len(s) - 1)))))]


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    n_ep = 0
    sebep = {"kadraj_kenari": 0, "kucuk": 0, "dusuk_conf": 0, "belirsiz": 0}
    son_cx, son_cy, son_boyut, son_conf, son_menzil = [], [], [], [], []
    kenar_yon = {"sag": 0, "sol": 0, "ust": 0, "alt": 0}
    sure_l = []

    for e in os.scandir(LOGD):
        if not (e.name.startswith("bbox_ibvs_") and e.name.endswith(".csv")):
            continue
        try:
            R = list(csv.DictReader(open(e.path, newline="", encoding="utf-8",
                                         errors="replace")))
        except Exception:
            continue
        if len(R) < MIN_SATIR:
            continue
        # SON GECERLI kutu
        sk = None
        for r in reversed(R):
            cx, cy = f(r.get("cx")), f(r.get("cy"))
            if cx is not None and cy is not None and (cx != 0.0 or cy != 0.0):
                sk = r
                break
        if sk is None:
            continue
        n_ep += 1
        cx, cy = f(sk.get("cx")), f(sk.get("cy"))
        bo = f(sk.get("boyut"))
        cf = f(sk.get("conf"))
        mz = f(sk.get("menzil_m"))
        tv = [f(r.get("t")) for r in R]
        tv = [x for x in tv if x is not None]
        if len(tv) > 1:
            sure_l.append(max(tv) - min(tv))
        son_cx.append(cx); son_cy.append(cy)
        if bo is not None:
            son_boyut.append(bo)
        if cf is not None:
            son_conf.append(cf)
        if mz is not None and 0.3 < mz < 200:
            son_menzil.append(mz)

        kenarda = (cx < PAY_PX or cx > IMG_W - PAY_PX
                   or cy < PAY_PX or cy > IMG_H - PAY_PX)
        if kenarda:
            sebep["kadraj_kenari"] += 1
            if cx < PAY_PX:
                kenar_yon["sol"] += 1
            elif cx > IMG_W - PAY_PX:
                kenar_yon["sag"] += 1
            if cy < PAY_PX:
                kenar_yon["ust"] += 1
            elif cy > IMG_H - PAY_PX:
                kenar_yon["alt"] += 1
        elif bo is not None and bo < BOYUT_KAPI:
            sebep["kucuk"] += 1
        elif cf is not None and cf < 0.30:
            sebep["dusuk_conf"] += 1
        else:
            sebep["belirsiz"] += 1

    print("[TEMAS] epizot: %d" % n_ep)
    if n_ep < 20:
        print("[TEMAS] yeterli epizot yok"); return 1
    print("[TEMAS] epizot suresi: ortanca %.1f s | p90 %.1f s"
          % (y(sure_l, .5), y(sure_l, .9)))
    print()
    print("  ── TEMAS KOPMADAN ONCEKI SON KUTU ──")
    print("    cx     : ortanca %6.1f | p10 %6.1f | p90 %6.1f   (merkez 320)"
          % (y(son_cx, .5), y(son_cx, .1), y(son_cx, .9)))
    print("    cy     : ortanca %6.1f | p10 %6.1f | p90 %6.1f   (merkez 240)"
          % (y(son_cy, .5), y(son_cy, .1), y(son_cy, .9)))
    if son_boyut:
        print("    boyut  : ortanca %6.1f | p10 %6.1f px          (kapi %.0f)"
              % (y(son_boyut, .5), y(son_boyut, .1), BOYUT_KAPI))
    if son_conf:
        print("    conf   : ortanca %6.2f | p10 %6.2f" % (y(son_conf, .5), y(son_conf, .1)))
    if son_menzil:
        print("    menzil : ortanca %6.1f m | p10 %6.1f" % (y(son_menzil, .5), y(son_menzil, .1)))
    print()
    print("  ── SEBEP DAGILIMI ──")
    for k, v in sorted(sebep.items(), key=lambda x: -x[1]):
        print("    %-16s %5.1f%%  (n=%d)" % (k, 100.0 * v / n_ep, v))
    if sebep["kadraj_kenari"]:
        print()
        print("  ── KADRAJDAN HANGI YONDEN CIKIYOR ──")
        t = sebep["kadraj_kenari"]
        for k, v in sorted(kenar_yon.items(), key=lambda x: -x[1]):
            print("    %-6s %5.1f%%  (n=%d)" % (k, 100.0 * v / t, v))
        print("    (sag/sol = yaw yetismiyor · ust/alt = dikey yetismiyor)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

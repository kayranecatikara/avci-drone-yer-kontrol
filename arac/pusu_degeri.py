# -*- coding: utf-8 -*-
"""
================================================================================
  PUSU DEGERI  --  periyodik model anlik kestirimden IYI mi?
================================================================================
2026-08-21 olcumu: gozlem yamasindan sonra model periyodu buluyor
(29.2-29.9 s, belgelenen 29.60 ile ortusuyor) ama KALITE 8-15 m cikiyor ve
`PUSU_KALITE_MAX=3.0` kapisi kapali kaliyor -> pusu hic ateslemiyor.

Kalite kotu cunku model YARISMA kestirimiyle besleniyor (~10 m hatali).
Ama asil soru kalite degil: MODELIN TAHMINI, ELIMIZDEKI ANLIK KESTIRIMDEN
DAHA MI IYI? Iyiyse kapiyi olculmus degere acmak dogru; degilse ACMAYIZ.

YONTEM
--------------------------------------------------------------------------------
Iki log JOIN edilir (ikisi de ayni surecte perf_counter tabanli):
  * kopru/gazebo_kaynak/logs/gps_guidance_*.csv -> tgt_x/tgt_y  (KESTIRIM)
  * veri/ucus_log_*.csv                          -> true_tx/ty  (TRUTH, cm)
Sonra ayni anlarda uc hata karsilastirilir:
  A) anlik kestirim hatasi        |kestirim(t) - truth(t)|
  B) periyodik model hatasi       |model(t) - truth(t)|   model = kestirimle beslenmis
  C) olumsuz kontrol              periyot %20 yanlis verilirse B kotulesmeli

⚠ B'nin A'dan belirgin kucuk olmasi SART. Degilse pusu kapisini acmak
  gerekcesiz olur -- "yaklasik dogru kestirimle ucmak YOK" (hedef_tekrar.py).
⚠ Model YALNIZ kestirimle beslenir; truth'a ASLA bakmaz (yarisma kurali).
================================================================================
"""
import csv
import glob
import math
import os
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_KAYNAK = os.path.join(KOK, "kopru", "gazebo_kaynak")
if _KAYNAK not in sys.path:
    sys.path.insert(0, _KAYNAK)

from control.guidance.hedef_tekrar import HedefTekrar          # noqa: E402

CM = 100.0
JOIN_TOL = 0.10          # s; iki log arasi eslesme toleransi
UFUK = 3.0               # s; ileri kestirim ufku (pusu tgo mertebesi)


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


def gps_oku(p):
    R = []
    for r in csv.DictReader(open(p, newline="", encoding="utf-8", errors="replace")):
        t, x, yy = f(r.get("t")), f(r.get("tgt_x")), f(r.get("tgt_y"))
        z = f(r.get("tgt_z"))
        if None not in (t, x, yy):
            R.append((t, x, yy, z or 0.0))
    return R


def ucus_oku(p):
    R = []
    for r in csv.DictReader(open(p, newline="", encoding="utf-8", errors="replace")):
        t = f(r.get("t_perf"))
        x, yy = f(r.get("true_tx")), f(r.get("true_ty"))
        if None not in (t, x, yy):
            R.append((t, x / CM, yy / CM))
    return R


def main():
    gl = sorted(glob.glob(os.path.join(_KAYNAK, "logs", "gps_guidance_*.csv")),
                key=os.path.getmtime)[-8:]
    ul = sorted(glob.glob(os.path.join(KOK, "veri", "ucus_log_*.csv")),
                key=os.path.getmtime)[-3:]
    if not gl or not ul:
        print("log bulunamadi"); return

    truth = []
    for p in ul:
        truth += ucus_oku(p)
    truth.sort()
    print("[DEGER] truth ornegi %d (%d dosya)" % (len(truth), len(ul)))
    if len(truth) < 500:
        print("[DEGER] truth yetersiz"); return

    tt = [r[0] for r in truth]

    def truth_at(t):
        lo, hi = 0, len(tt) - 1
        while lo < hi:
            m = (lo + hi) // 2
            if tt[m] < t:
                lo = m + 1
            else:
                hi = m
        en = None
        for j in (lo - 1, lo, lo + 1):
            if 0 <= j < len(tt):
                d = abs(tt[j] - t)
                if en is None or d < en[0]:
                    en = (d, truth[j])
        return en[1] if en and en[0] <= JOIN_TOL else None

    for carpan, etiket in ((1.0, "GERCEK periyot"), (1.2, "OLUMSUZ KONTROL (%20 yanlis)")):
        tk = HedefTekrar(periyot_carpan=carpan, kalite_max=1e9)
        A, B = [], []
        eslesme = 0
        for p in gl:
            for (t, ex, ey, ez) in gps_oku(p):
                tk.ekle(t, ex, ey, ez)
                tk.guncelle(t)
                gt = truth_at(t)
                if gt is None:
                    continue
                eslesme += 1
                A.append(math.hypot(ex - gt[1], ey - gt[2]))
                if tk.periyot is None:
                    continue
                # model: bir tur oncesine bakip SIMDIYI kestir
                try:
                    mk = tk.kestir(t) if hasattr(tk, "kestir") else None
                except Exception:
                    mk = None
                if mk is None:
                    try:
                        mk = tk._konum(t - tk.periyot)
                    except Exception:
                        mk = None
                if mk:
                    B.append(math.hypot(mk[0] - gt[1], mk[1] - gt[2]))
        print()
        print("  ── %s ──" % etiket)
        print("    eslesen ornek : %d" % eslesme)
        if A:
            print("    A) anlik kestirim hatasi : ortanca %.2f m | p90 %.2f m (n=%d)"
                  % (y(A, .5), y(A, .9), len(A)))
        if B:
            print("    B) periyodik model hatasi: ortanca %.2f m | p90 %.2f m (n=%d)"
                  % (y(B, .5), y(B, .9), len(B)))
            if A:
                kaz = 100.0 * (y(A, .5) - y(B, .5)) / y(A, .5)
                print("    -> model %s (%+.1f%%)"
                      % ("DAHA IYI" if y(B, .5) < y(A, .5) else "DAHA KOTU", -kaz))
        else:
            print("    B) model hic kestirim uretemedi (periyot bulunamadi)")
        print("    periyot=%s kalite=%s" % (tk.periyot, tk.kalite))


if __name__ == "__main__":
    main()

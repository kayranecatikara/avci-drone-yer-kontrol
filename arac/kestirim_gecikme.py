# -*- coding: utf-8 -*-
"""
================================================================================
  KESTIRIM GECIKMESI  --  "gercek GPS ile vuruyor, kendi kestirimimizle vurmuyor"
================================================================================
Kullanici gozlemi: kaynak=gercek (dogru GPS) secildiginde arac hedefi VURUYOR;
kaynak=v2 (Inovasyonlu J, bozulmus GPS + filtre) ile vurmuyor.
Bu, gudum yasasinin degil HEDEF KESTIRIMININ suclu oldugunu soyler.

Bu betik kestirimi gercek konumla karsilastirir ve HATANIN CINSINI ayirir:

  1) BUYUKLUK : |est - true| dagilimi (m)
  2) GECIKME  : est(t) ile true(t - tau) arasindaki hata tau'ya gore taranir.
                En iyi tau > 0 ise kestirim GECIKMELI -- yani hedefin
                ESKI yerini gosteriyoruz. Gecikmede hata giderilebilir
                (ileri kestirim), saf gurultude giderilemez.
  3) YONU     : hata hedefin gidis yonunde mi (boylamsal = gecikme imzasi)
                yoksa yanal mi (gurultu imzasi)?

⚠ Gecikme imzasi: hata AGIRLIKLI OLARAK -t_hat yonunde (hedefin GERISINDE)
  ve buyuklugu hedef hiziyla orantili olmalidir:  |hata| ~ v_hedef * tau.
  Kontrol: olculen |hata| / v_hedef ~ bulunan tau cikmali. Cikmiyorsa
  "gecikme" aciklamasi eksiktir.

⚠ BIRIM: log konumlari SANTIMETRE. Betik metreye cevirir.
⚠ DONMUS telemetri ve yeniden dogus sicramalari atilir.
================================================================================
"""
import csv
import glob
import math
import os
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CM = 100.0
TAU_MAX = 2.0
TAU_ADIM = 0.05


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
    yol = sys.argv[1] if len(sys.argv) > 1 else None
    if not yol:
        lst = sorted(glob.glob(os.path.join(KOK, "veri", "ucus_log_*.csv")),
                     key=os.path.getmtime)
        if not lst:
            print("ucus_log_*.csv yok"); return
        yol = lst[-1]
    print("[KESTIRIM] %s" % os.path.basename(yol))

    R, onc = [], None
    kaynaklar = {}
    for r in csv.DictReader(open(yol, newline="", encoding="utf-8", errors="replace")):
        tx, ty = f(r.get("true_tx")), f(r.get("true_ty"))
        ex, ey = f(r.get("est_x")), f(r.get("est_y"))
        t = f(r.get("t_perf"))
        d = f(r.get("gercek_mesafe"))
        if None in (tx, ty, ex, ey, t, d) or d <= 50.0:
            continue
        imza = (round(tx, 2), round(ty, 2), round(ex, 2), round(ey, 2))
        if imza == onc:
            continue
        onc = imza
        k = (r.get("kaynak") or "?").strip()
        kaynaklar[k] = kaynaklar.get(k, 0) + 1
        R.append({"t": t, "tx": tx / CM, "ty": ty / CM,
                  "ex": ex / CM, "ey": ey / CM, "d": d / CM, "kaynak": k})

    print("[KESTIRIM] ornek %d" % len(R))
    print("[KESTIRIM] kaynak dagilimi: %s"
          % ", ".join("%s=%d" % kv for kv in sorted(kaynaklar.items(), key=lambda x: -x[1])))
    if len(R) < 200:
        print("[KESTIRIM] yeterli veri yok"); return

    # ── 1) buyukluk ─────────────────────────────────────────────────────────
    hata = [math.hypot(r["ex"] - r["tx"], r["ey"] - r["ty"]) for r in R]
    print()
    print("  ── 1) KESTIRIM HATASI (est vs true) ──")
    print("    ortanca %.2f m | p90 %.2f m | p99 %.2f m"
          % (y(hata, .5), y(hata, .9), y(hata, .99)))
    print()
    print("    menzile gore:")
    for lo, hi in ((0, 10), (10, 25), (25, 60), (60, 1e9)):
        v = [math.hypot(r["ex"] - r["tx"], r["ey"] - r["ty"])
             for r in R if lo <= r["d"] < hi]
        if v:
            et = ("%d+ m" % lo) if hi > 1e8 else ("%d-%d m" % (lo, hi))
            print("      %-9s ortanca %.2f m  (n=%d)" % (et, y(v, .5), len(v)))

    # ── 2) gecikme taramasi ─────────────────────────────────────────────────
    # est(t) ile true(t - tau): true'yu tau kadar GERI kaydirip karsilastir
    ts = [r["t"] for r in R]
    print()
    print("  ── 2) GECIKME TARAMASI ──")
    print("    tau (s)   ortanca hata (m)")
    en_iyi, en_iyi_tau = None, None
    j0 = 0
    tau = 0.0
    sonuc = []
    while tau <= TAU_MAX + 1e-9:
        v, j = [], 0
        for i, r in enumerate(R):
            hedef_t = r["t"] - tau
            while j + 1 < len(R) and ts[j + 1] <= hedef_t:
                j += 1
            if abs(ts[j] - hedef_t) > 0.25:
                continue
            v.append(math.hypot(r["ex"] - R[j]["tx"], r["ey"] - R[j]["ty"]))
        if len(v) > 100:
            m = y(v, .5)
            sonuc.append((tau, m))
            if en_iyi is None or m < en_iyi:
                en_iyi, en_iyi_tau = m, tau
        tau += TAU_ADIM
    for t_, m in sonuc[::4]:
        im = " <-- EN IYI" if abs(t_ - (en_iyi_tau or -9)) < 1e-9 else ""
        print("    %6.2f    %8.2f%s" % (t_, m, im))
    print()
    if en_iyi_tau is not None:
        print("    EN IYI TAU = %.2f s  ->  ortanca hata %.2f m (tau=0'da %.2f m)"
              % (en_iyi_tau, en_iyi, sonuc[0][1] if sonuc else float("nan")))
        if en_iyi_tau > 0.1:
            kaz = 100.0 * (sonuc[0][1] - en_iyi) / sonuc[0][1] if sonuc else 0.0
            print("    -> KESTIRIM GECIKMELI. %.2f s ileri kestirimle hata %%%.0f duser."
                  % (en_iyi_tau, kaz))
        else:
            print("    -> gecikme YOK (tau~0). Hata gurultu/yanlilik cinsinden.")

    # ── 3) hatanin yonu ─────────────────────────────────────────────────────
    boy, yan = [], []
    for i in range(1, len(R)):
        a, b = R[i - 1], R[i]
        dt = b["t"] - a["t"]
        if not (0.02 <= dt <= 0.60):
            continue
        tvx, tvy = (b["tx"] - a["tx"]) / dt, (b["ty"] - a["ty"]) / dt
        sp = math.hypot(tvx, tvy)
        if sp < 1.0 or sp > 45.0:
            continue
        thx, thy = tvx / sp, tvy / sp
        hx, hy = b["ex"] - b["tx"], b["ey"] - b["ty"]
        boy.append(hx * thx + hy * thy)          # + = hedefin ONUNU gosteriyoruz
        yan.append(hx * (-thy) + hy * thx)
    if boy:
        print()
        print("  ── 3) HATANIN YONU (hedefin gidis eksenine gore) ──")
        print("    boylamsal (gidis ekseni): ortanca %+.2f m  (- = hedefin GERISINI gosteriyoruz)"
              % y(boy, .5))
        print("    yanal                   : ortanca %+.2f m | |yanal| ortanca %.2f m"
              % (y(yan, .5), y([abs(x) for x in yan], .5)))
        gb = sum(1 for x in boy if x < 0)
        print("    boylamsal hata NEGATIF olan oran: %.1f%%  (gecikme imzasi)"
              % (100.0 * gb / len(boy)))
        # tutarlilik: |boylamsal| / v_hedef ~ tau olmali
        if en_iyi_tau:
            bek = 17.9 * en_iyi_tau
            print("    tutarlilik: v_hedef(17.9) * tau(%.2f) = %.1f m  vs olculen |boylamsal| %.1f m"
                  % (en_iyi_tau, bek, abs(y(boy, .5))))


if __name__ == "__main__":
    main()

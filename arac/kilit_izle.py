# -*- coding: utf-8 -*-
"""KILIT IZLEYICI — sartname olcutunu CANLI gosterir.

Bugun "en yakin gecis"i optimize ettim; gorevin olcutu O DEGIL.
Sartname (kilit_sayaci.py 6.1.2/6.1.4):
    * merkez Angajman Volumu icinde (yatay %25-75, dikey %10-90)
    * bbox EN AZ BIR eksende ekranin >= %5'i (kodda %6 marj)
    * 10 s kayan pencerede KUMULATIF >= 5 s
⚠ Sayac YALNIZ GORSEL fazda birikiyor (ana_kontrol.py:997).
"""
import json, time, sys, urllib.request, statistics as st

KOK = 'http://127.0.0.1:8000'


def tel():
    with urllib.request.urlopen(KOK + '/api/telemetry', timeout=4) as r:
        return json.loads(r.read().decode('utf-8', 'replace'))


def main():
    sure = float(sys.argv[1]) if len(sys.argv) > 1 else 180.0
    t0 = time.perf_counter()
    boy = []
    men = []
    en_uzun = 0.0
    kum_max = 0.0
    print("  %6s %7s %7s %7s %8s %9s %8s %s" % (
        "t", "menzil", "kutu%", "esik%", "merkez", "kumulatif", "en_uzun", "faz"), flush=True)
    son = 0.0
    while time.perf_counter() - t0 < sure:
        try:
            t = tel()
        except Exception:
            time.sleep(0.5)
            continue
        g = t.get('gorsel', {}) or {}
        k = g.get('kilit', {}) or {}
        h = (t.get('gudum', {}) or {}).get('hibrit', {}) or {}
        R = t.get('gercek_mesafe_m') or 0.0
        bp = k.get('boyut_pct')
        if bp is not None:
            boy.append(bp)
        if R:
            men.append(R)
        kum_max = max(kum_max, float(k.get('sure') or 0.0))
        en_uzun = max(en_uzun, float(k.get('en_uzun_s') or k.get('kesintisiz') or 0.0))
        if time.perf_counter() - son >= 5.0:
            son = time.perf_counter()
            print("  %5.0fs %6.1fm %6s %6s %8s %8s %8.1f %s" % (
                son - t0, R,
                ("%.1f" % bp) if bp is not None else "—",
                k.get('esik_pct', '—'),
                "ICINDE" if k.get('anlik') else "-",
                ("%.1f" % (k.get('sure') or 0.0)), en_uzun, h.get('faz')), flush=True)
        time.sleep(0.4)
    print("\n  === OZET ===", flush=True)
    if boy:
        print("  kutu orani : medyan %%%.1f  p90 %%%.1f  max %%%.1f   (esik %%6)" % (
            st.median(boy), sorted(boy)[int(.9 * (len(boy) - 1))], max(boy)), flush=True)
        print("  esigi gecen ornek: %%%.0f" % (100.0 * sum(1 for x in boy if x >= 6.0) / len(boy)), flush=True)
    if men:
        print("  menzil     : medyan %.1f m  p10 %.1f m  min %.1f m" % (
            st.median(men), sorted(men)[len(men) // 10], min(men)), flush=True)
    print("  kumulatif kilit MAX: %.1f s  (gereken 5.0)" % kum_max, flush=True)


if __name__ == "__main__":
    main()

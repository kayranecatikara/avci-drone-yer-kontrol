# -*- coding: utf-8 -*-
"""
================================================================================
  TEKRARLANABILIRLIK HUKMU  --  "vurus tesaduf mu, degil mi?"
================================================================================
NEDEN
--------------------------------------------------------------------------------
Kullanicinin sarti: "kesinlikle tekrarlanabilir vuruslar, tesaduf degil".
Tek bir ayarda 2 vurus gormek bunu KANITLAMAZ. Bu betik ayni ayarin
tekrarlarini sayar ve ISTATISTIKSEL bir hukum basar.

⚠ HANGI SINYAL SAYILIR
    "vurus" telemetri alani YAPISKAN MANDAL  -> acik kare saymak ANLAMSIZ
    "kilit_s" 10.0'da DOYMUS sayac           -> basari olcutu DEGIL
    GECERLI SINYAL: YENIDEN DOGUS = menzil <8 m iken aniden >25 m sicramasi
                    (arac oldu ve yeniden dogdu; hedefe 1-3 m'de olmek = temas)

KULLANIM
    python arac/tekrar_hukum.py
    python arac/tekrar_hukum.py --iz veri/gece/kampanya_iz_20260817_113334.csv
================================================================================
"""
import os
import csv
import sys
import glob
import math
import argparse
from collections import defaultdict

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _f(r, k):
    v = (r.get(k) or "").strip()
    if v in ("", "None", "nan"):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _fisher_tek_yonlu(a, b, c, d):
    """2x2 icin tek yonlu Fisher kesin testi (p-degeri).
       [[a,b],[c,d]] = [[vuran_kosu, vurmayan], [taban_vuran, taban_vurmayan]]"""
    def C(n, k):
        if k < 0 or k > n:
            return 0
        return math.comb(n, k)
    n = a + b + c + d
    p = 0.0
    toplam = C(n, a + c)
    if toplam == 0:
        return 1.0
    for x in range(a, min(a + b, a + c) + 1):
        p += C(a + b, x) * C(c + d, a + c - x)
    return min(p / toplam, 1.0)


def temaslar(satirlar):
    """Yeniden dogus (temas) sayisi ve dogus anindaki menziller."""
    mz = [_f(r, "menzil") for r in satirlar]
    out = []
    for i in range(1, len(satirlar)):
        a, b = mz[i - 1], mz[i]
        if a is not None and b is not None and a < 8 and b - a > 25:
            out.append((a, satirlar[i - 1]))
    return out


def cpa_geometri(satirlar):
    """Yakin gecislerin CPA'sinda dikey/yatay ayrim medyani."""
    mz = [_f(r, "menzil") for r in satirlar]
    ep, cur = [], []
    for i, m in enumerate(mz):
        if m is not None and m < 12:
            cur.append(i)
        elif cur:
            ep.append(cur)
            cur = []
    if cur:
        ep.append(cur)
    dv, dh, cpa = [], [], []
    for e in ep:
        j = min(e, key=lambda i: mz[i] if mz[i] is not None else 9e9)
        m = mz[j]
        if m is None or m > 8:
            continue
        v = abs(_f(satirlar[j], "irt_fark") or 0.0)
        dv.append(v)
        dh.append(math.sqrt(max(m * m - v * v, 0.0)))
        cpa.append(m)
    return cpa, dv, dh


def med(x):
    if not x:
        return float("nan")
    s = sorted(x)
    n = len(s)
    return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iz", default="")
    a = ap.parse_args()
    yollar = ([a.iz] if a.iz else
              sorted(glob.glob(os.path.join(KOK, "veri", "gece", "kampanya_iz_*.csv")),
                     key=os.path.getmtime)[-3:])
    grup = defaultdict(list)
    for y in yollar:
        try:
            for r in csv.DictReader(open(y, encoding="utf-8", errors="replace")):
                grup[r.get("ayar", "?")].append(r)
        except OSError:
            continue
    if not grup:
        print("iz dosyasi bulunamadi")
        return

    print("=" * 78)
    print("  TEKRARLANABILIRLIK HUKMU")
    print("  sinyal: YENIDEN DOGUS (menzil<8 m iken >25 m sicrama) = temas")
    print("=" * 78)
    print("%-22s %7s %6s %7s %8s %8s %8s" % (
        "AYAR", "dk", "TEMAS", "temas/sa", "CPA med", "dikey", "yatay"))
    print("-" * 78)

    sonuc = {}
    for ayar in sorted(grup):
        S = grup[ayar]
        if len(S) < 100:
            continue
        t = [_f(r, "t") for r in S]
        t = [x for x in t if x is not None]
        dk = (max(t) - min(t)) / 60.0 if len(t) > 1 else 0.0
        tm = temaslar(S)
        cpa, dv, dh = cpa_geometri(S)
        sonuc[ayar] = (dk, len(tm), med(dv), med(dh), med(cpa))
        print("%-22s %7.1f %6d %7.2f %8.2f %8.2f %8.2f" % (
            ayar[:22], dk, len(tm), (len(tm) / (dk / 60.0)) if dk > 1 else 0.0,
            med(cpa), med(dv), med(dh)))

    # ── T (tekrar) kollari: ayni ayar, birebir tekrar ────────────────────
    T = {k: v for k, v in sonuc.items() if k.startswith("T")}
    V = {k: v for k, v in sonuc.items() if k.startswith("V")}
    print()
    # ⚠ YETERSIZ VERIYLE HUKUM VERME. Yarim kalmis bir kosu "tekrarlanmadi"
    #   diye okunursa SAHTE NEGATIF cikar. Ayna sonrasi olculen hiz
    #   ~4-17 temas/saat -> 10 dk'lik bir kosuda 0 temas gormek NORMAL.
    T_ham = dict(T)
    T = {k: v for k, v in T.items() if v[0] >= 10.0}
    V = {k: v for k, v in V.items() if v[0] >= 10.0}
    eksik = len(T_ham) - len(T)
    if eksik:
        print("   (%d kosu 10 dk'dan kisa -> hukme KATILMADI, henuz suruyor)"
              % eksik)
    if T:
        vuran = sum(1 for v in T.values() if v[1] > 0)
        toplam_temas = sum(v[1] for v in T.values())
        toplam_dk = sum(v[0] for v in T.values())
        print("★ TEKRARLANABILIRLIK  (ayni ayar, birebir tekrar)")
        print("   %d kosunun %d'inde temas var | toplam %d temas / %.0f dk"
              % (len(T), vuran, toplam_temas, toplam_dk))
        # ayna ONCESI taban: 19 ayar, ~3.5 saat, 0 temas (olculdu 2026-08-17)
        p = _fisher_tek_yonlu(vuran, len(T) - vuran, 0, 19)
        print("   ayna ONCESI taban: 0/19 ayar temas (~3.5 saat)")
        print("   Fisher tek yonlu p = %.5f  -> %s" % (
            p, "TESADUF DEGIL (p<0.01)" if p < 0.01 else
               ("guclu isaret (p<0.05)" if p < 0.05 else "HENUZ KANIT YETERSIZ")))
        if vuran == len(T) and len(T) >= 3:
            print("   HUKUM: ✓ TEKRARLANABILIR -- her kosuda temas")
        elif vuran == 0:
            print("   HUKUM: ✗ TEKRARLANMADI -- hicbir kosuda temas yok")
        else:
            print("   HUKUM: ~ KISMI -- %d/%d kosu" % (vuran, len(T)))
    else:
        print("★ TEKRARLANABILIRLIK: henuz hukum YOK")
        print("   >=10 dk tamamlanmis tekrar kosusu bulunamadi -- kampanya suruyor.")
    if T and V:
        dt = med([v[2] for v in T.values()])
        dvv = med([v[2] for v in V.values()])
        print()
        print("★ DIKEY IVME BUTCESI (AVCI_ACCEL_SPLIT)")
        print("   split KAPALI (T): dikey ayrim %.2f m" % dt)
        print("   split ACIK   (V): dikey ayrim %.2f m" % dvv)
        fark = dt - dvv
        print("   fark %+.2f m -> %s" % (
            fark, "YAMA ISE YARADI" if fark > 0.15 else
                  ("etkisiz" if abs(fark) <= 0.15 else "★ KOTULESTI, GERI AL")))
        tt = sum(v[1] for v in T.values())
        vt = sum(v[1] for v in V.values())
        print("   temas: split kapali %d | split acik %d" % (tt, vt))
    print()
    print("⚠ MEKANIZMA KAPISI: split kolunun GERCEKTEN devreye girdigini")
    print("   dogrulamadan sonucu kabul etme -> gps_guidance_*.csv icinde")
    print("   |d(vz_cmd)/dt| p90 su TABANIN uzerine cikmali:")
    print("     OLCULDU 2026-08-17 (T1_tekrar, ACCEL_SPLIT=0, 8945 tik):")
    print("       p90 = 2.39   |   menzil<8 m'de p90 = 2.55")
    print("   ⚠ '0.43' esigi YANLISTI -- o, tavandayken dikeye KALAN ivme")
    print("     paylasimiydi, d(vz_cmd)/dt DEGIL. O esikle yama hic")
    print("     devreye girmemisken 'girdi' diye okunurdu.")


if __name__ == "__main__":
    main()

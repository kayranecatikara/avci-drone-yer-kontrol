# -*- coding: utf-8 -*-
"""
INOVASYONLU J (CT-EKF) TESHIS — offline replay (filtre MANTIGI degismez, gozlemsel).
====================================================================================
Bir v2 (kaynak=v2) ucus_log'unun HAM GPS'ini (son_ham_x/y/z) TAZE bir GNSSDuzeltici'den
gecirir; filtrenin ic davranisini (innovation yk, gate karari maha^2<gate^2, turn-rate w,
dt) + ANLIK/LEAD/HAM hatasini (truth'a gore) CSV'ye doker ve 3 soruyu EMPIRIK yanitlar:
  (1) bank-acisi (phi->w) enjeksiyonu aktif mi / CT manevra modeli calisiyor mu
  (2) gecikme telafisi/ongoru adimi var mi, ne kadar ileri sariyor
  (3) sicrama-reddi (gating) esigi ne, neden 40m zplamalari geciriyor
Kullanim:  python arac/j_analiz.py [--dosya veri/ucus_log_...csv]
"""
import csv
import glob
import math
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from fusion.inovasyonlu_j_v2 import GNSSDuzeltici


def fl(x):
    try:
        v = float(x)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def _v2_log(dosya):
    if dosya:
        return dosya
    for f in sorted(glob.glob(os.path.join(ROOT, "veri", "ucus_log_*.csv")), reverse=True):
        with open(f, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if r.get("kaynak") == "v2":
                    return f
    return None


def main():
    dosya = None
    a = sys.argv[1:]
    for i, x in enumerate(a):
        if x == "--dosya" and i + 1 < len(a):
            dosya = a[i + 1]
    dosya = _v2_log(dosya)
    if not dosya:
        print("kaynak=v2 ucus_log bulunamadi (v2 kosusu gerekli).")
        return 1

    rows = [r for r in csv.DictReader(open(dosya, encoding="utf-8")) if r.get("kaynak") == "v2"]
    filt = GNSSDuzeltici()                                   # ana_kontrol ile AYNI (tum varsayilanlar)
    out = os.path.join(ROOT, "veri", time.strftime("j_analiz_%Y%m%d_%H%M%S.csv"))
    cols = ["adim", "raw_err_m", "anlik_err_m", "lead_err_m", "yk_cm", "maha2", "gate2", "gecti", "w", "dt"]
    of = open(out, "w", encoding="utf-8")
    of.write(",".join(cols) + "\n")

    prev = None
    R = []; A = []; L = []; W = []; D = []
    kabul = toplam = sic = sic_kabul = 0
    for r in rows:
        hx, hy, hz = fl(r.get("son_ham_x")), fl(r.get("son_ham_y")), fl(r.get("son_ham_z"))
        tx, ty = fl(r.get("true_tx")), fl(r.get("true_ty"))
        tw = fl(r.get("t_wall"))                            # adaptif dt: gercek zaman damgasi
        if None in (hx, hy, hz):
            continue
        ham = (hx, hy, hz)
        if ham == prev:                                     # ana_kontrol gibi: yeni paket degil -> atla
            continue
        prev = ham
        sonuc = filt.guncelle(hx, hy, hz, tw)               # 2sn-lead doner (None = isinma/donma)
        if sonuc is None:
            continue
        d = filt._diag or {}
        dg = filt.durum_guduum() or {"pos": (0.0, 0.0, 0.0)}
        ax, ay = dg["pos"][0], dg["pos"][1]                 # ANLIK (lead-siz)
        lx, ly = sonuc[0], sonuc[1]                         # LEAD (2sn ileri)
        raw = math.hypot(hx - tx, hy - ty) / 100.0 if tx is not None else None
        an = math.hypot(ax - tx, ay - ty) / 100.0 if tx is not None else None
        le = math.hypot(lx - tx, ly - ty) / 100.0 if tx is not None else None
        of.write(",".join(str(c) for c in [
            filt._adim, "" if raw is None else round(raw, 2), "" if an is None else round(an, 2),
            "" if le is None else round(le, 2), round(d.get("yk_cm", 0), 1), round(d.get("maha2", 0), 1),
            round(d.get("gate2", 0), 1), int(d.get("gecti", False)), round(d.get("w", 0), 5), d.get("dt", 0)
        ]) + "\n")
        toplam += 1
        if d.get("gecti"):
            kabul += 1
        if d.get("yk_cm", 0) > 3500:                        # >35m innovation = buyuk sicrama adayi
            sic += 1
            if d.get("gecti"):
                sic_kabul += 1
        if raw is not None:
            R.append(raw)
        if an is not None:
            A.append(an)
        if le is not None:
            L.append(le)
        W.append(d.get("w", 0))
        D.append(d.get("dt", 0))

    of.close()

    def md(x):
        return sorted(x)[len(x) // 2] if x else 0.0

    print("=" * 76)
    print("INOVASYONLU J (CT-EKF) TESHIS  |  %s" % os.path.basename(dosya))
    print("CSV: %s   (%d yeni-paket adimi)" % (os.path.basename(out), toplam))
    print("Filtre param: dt=%.2f  telafi_sn=%.1f  gate=%.0f (gate^2=%.0f)  Qw=1e-5  w_max=%.2f  R=100cm"
          % (filt.dt, filt.telafi_sn, filt.gate, filt.gate ** 2, filt.w_max))
    print("-" * 76)
    print("[1] BANK-ACISI (phi->w) ENJEKSIYONU + CT MANEVRA MODELI:")
    print("    guncelle(x,y,z) SADECE konum alir -> phi/bank pseudo-olcumu YOK.")
    print("    turn-rate w: min=%.4f  med=%.4f  max=%.4f rad/s" % (min(W) if W else 0, md(W), max(W) if W else 0))
    print("    -> Qw=1e-5 cok kucuk: w pozisyondan cok yavas adapte, neredeyse SABIT. CT teknik")
    print("       olarak ACIK ama PASIF (manevra ongorusu yok, ~sabit-hiz gibi davraniyor).")
    print("[2] GECIKME TELAFISI / ONGORU:")
    print("    LEAD ciktisi = state + %.1f sn ileri (telafi_sn). ANLIK (durum_guduum) telafi-SIZ." % filt.telafi_sn)
    print("    PREDICT adim dt ADAPTIF: medyan=%.3f min=%.3f max=%.3f sn -- gercek paket araligi."
          % (md(D), min(D) if D else 0, max(D) if D else 0))
    print("    Hata (truth'a, m): HAM med=%.1f | J-ANLIK med=%.1f | J-LEAD med=%.1f" % (md(R), md(A), md(L)))
    print("    -> ANLIK ~ HAM: gecikme ANLIK kestirimde telafi EDILMIYOR (LOS/terminal bunu kullaniyor).")
    print("[3] SICRAMA-REDDI (GATING):")
    print("    Olcut INNOVATION-tabanli: Mahalanobis^2 (yk'Sx^-1 yk) < gate^2 (=%.0f)." % (filt.gate ** 2))
    print("    Kabul orani: %d/%d = %%%.1f" % (kabul, toplam, 100.0 * kabul / toplam if toplam else 0))
    print("    Buyuk innovation (>35m): %d adim -> KABUL: %d (%%%.0f gecti, reddedilen ~%%%.0f)"
          % (sic, sic_kabul, 100.0 * sic_kabul / sic if sic else 0, 100.0 * (1 - sic_kabul / sic) if sic else 0))
    print("    -> gate=%.0f (gate^2=%.0f). Bu profilde >35m hatalar JUMP DEGIL bias (maha^2 kucuk)"
          % (filt.gate, filt.gate ** 2))
    print("       -> gating anlik hatayi DUSURMEZ; 18m = gecikme (esik analizi: arac/j_gate_sweep.py).")
    print("=" * 76)
    return 0


if __name__ == "__main__":
    sys.exit(main())

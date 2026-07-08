# -*- coding: utf-8 -*-
"""
KILIT DENEMESI — 5 saniyelik ozet (Aşama 0).
============================================
En yeni veri/kilit_deneme_*.csv'yi okur, SON N saniyeyi (varsayilan 5) ozetler:
tespit orani, GPS/PnP menzil, det skor, bbox yatay/dikey %, %AV-ici (full-box),
guidance_source dagilimi ve YOLO/PnP/TOPLAM cikarim suresi (ms). Pandas YOK
(repo stili: csv + statistics). CSV'yi server.py dedektor_dongusu uretir (gozlemsel).

Kullanim:
  python arac/kilit_ozet.py                 # en yeni CSV, son 5 sn
  python arac/kilit_ozet.py --saniye 10     # son 10 sn
  python arac/kilit_ozet.py --dosya veri/kilit_deneme_...csv
"""
import csv
import glob
import os
import sys
from collections import Counter

VERI = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "veri")

# SAHTE-POZITIF kapisi (ana_kontrol Cfg.VIS_LOCK_* ile ESIT tutulmali): gecerli kilit karesi
# >=%6 + full-box AV'ye EK olarak conf + en/boy (w/h) kapisi -> uzak clutter/pervane elenir.
LOCK_PCT = 6.0
CONF_MIN = 0.50
ASP_MIN, ASP_MAX = 1.5, 6.0


def _flt(x):
    try:
        v = float(x)
        return v if v == v else None      # nan -> None (bozuk kutu satirlari istatistigi kirletmesin)
    except (TypeError, ValueError):
        return None


def _ozet_say(ad, dizi, birim=""):
    v = [x for x in dizi if x is not None]
    if not v:
        print("  %-22s : veri yok" % ad)
        return
    sv = sorted(v)
    med = sv[len(sv) // 2]
    ort = sum(v) / len(v)
    p95 = sv[min(len(sv) - 1, int(round(0.95 * (len(sv) - 1))))]
    print("  %-22s : medyan %.2f%s  ort %.2f  min %.2f  maks %.2f  p95 %.2f  (n=%d)"
          % (ad, med, birim, ort, sv[0], sv[-1], p95, len(v)))


def _valid(r):
    """CSV satiri GECERLI kilit karesi mi (backend _kilit_degerlendir ile AYNI): tespit var +
    full-box AV-ici + en az bir eksen >= %6 + SAHTE-POZITIF kapisi (conf + en/boy w/h)."""
    if str(r.get("det_var")) not in ("1", "1.0"):
        return False
    if str(r.get("av_ici")) not in ("1", "1.0"):
        return False
    y = _flt(r.get("bbox_yatay_pct")) or 0.0
    d = _flt(r.get("bbox_dikey_pct")) or 0.0
    if max(y, d) < LOCK_PCT:
        return False
    if (_flt(r.get("det_skor")) or 0.0) < CONF_MIN:          # sahte-pozitif kapisi: conf
        return False
    asp = _flt(r.get("bbox_en_boy"))                         # yeni CSV: dogrudan; eski: yatay/dikey (16:9)
    if asp is None:
        asp = (y / d) * (16.0 / 9.0) if d > 0 else 0.0
    return ASP_MIN <= asp <= ASP_MAX                         # en/boy (talon GENIS; dar/dikey=sahte)


def _pencere_max_kumulatif(segs, pencere):
    """segs: (bas,son) araliklari; `pencere` sn'lik KAYAN pencerede azami toplam kaplama (s)."""
    if not segs:
        return 0.0
    adaylar = set()
    for (s, e) in segs:
        adaylar.add(s); adaylar.add(e - pencere)
    en = 0.0
    for w0 in adaylar:
        w1 = w0 + pencere
        top = 0.0
        for (s, e) in segs:
            a = max(s, w0); b = min(e, w1)
            if b > a:
                top += (b - a)
        en = max(en, top)
    return en


def blok_analizi(rows, kopru_ms=400.0):
    """Ardisik GECERLI kilit karesi (>=%6 + AV) bloklarini bul; her blok icin sure/menzil/
    kare; en uzun blok = tek-geciste potansiyel; 10 sn pencerede azami kumulatif. Iki gecerli
    kare arasi <= kopru_ms ise ayni blok (tek dusen kareyi koprular). fly-by (kisa blok, menzil
    hizla degisir) mu PARK (uzun blok, menzil ~sabit) mu tek bakista gorunur."""
    kopru = kopru_ms / 1000.0
    bloklar = []
    cur = None
    for r in rows:
        if not _valid(r):
            continue
        t = _flt(r.get("t_yerel"))
        if t is None:
            continue
        g = _flt(r.get("gps_menzil_m"))
        if cur is None or (t - cur["son"]) > kopru:
            cur = {"bas": t, "son": t, "n": 1, "mz": ([g] if g is not None else [])}
            bloklar.append(cur)
        else:
            cur["son"] = t; cur["n"] += 1
            if g is not None:
                cur["mz"].append(g)
    print("")
    print("=" * 76)
    print("BLOK ANALIZI  |  gecerli kare = bbox>=%%6 VE full-box AV  |  kopru <= %d ms" % int(kopru_ms))
    print("-" * 76)
    if not bloklar:
        print("  Hic gecerli kilit karesi (>=%6 + AV) yok -> tek-geciste potansiyel 0.")
        print("=" * 76)
        return
    for i, b in enumerate(bloklar, 1):
        sure = b["son"] - b["bas"]
        mz = b["mz"]
        if mz:
            delta = max(mz) - min(mz)
            mstr = "%5.1f-%5.1f m (D%4.1f)" % (min(mz), max(mz), delta)
        else:
            delta, mstr = 0.0, "menzil yok"
        tur = ("PARK (uzun+menzil sabit)" if (sure >= 1.0 and delta <= 3.0)
               else "fly-by (kisa gecis)" if sure < 1.0 else "gecis")
        print("  blok %2d: %5.2f s | %3d kare | %-22s | %s" % (i, sure, b["n"], mstr, tur))
    en = max(bloklar, key=lambda b: b["son"] - b["bas"])
    print("-" * 76)
    print("  >>> TEK GECISTE kilit potansiyeli (en uzun blok): %.2f s" % (en["son"] - en["bas"]))
    ku = _pencere_max_kumulatif([(b["bas"], b["son"]) for b in bloklar], 10.0)
    print("  >>> 10 sn kayan pencerede AZAMI kumulatif (>=%%6+AV): %.2f s  ->  5 sn sarti: %s"
          % (ku, "SAGLANIR" if ku >= 5.0 else "saglanmaz"))
    print("=" * 76)


def _gate_gecti(r):
    """Bu CSV satirinda kapiyi (conf+en-boy) gecen tespit var mi (gudume 'gercek' hedef gitti mi).
    Yeni CSV'de gudum_hedef kolonu; eski CSV'de conf+en-boy'dan hesaplanir."""
    gh = r.get("gudum_hedef")
    if gh is not None and gh != "":
        return gh == "gercek"
    if str(r.get("det_var")) not in ("1", "1.0"):
        return False
    conf = _flt(r.get("det_skor")) or 0.0
    asp = _flt(r.get("bbox_en_boy"))
    if asp is None:
        y = _flt(r.get("bbox_yatay_pct")) or 0.0
        d = _flt(r.get("bbox_dikey_pct")) or 0.0
        asp = (y / d) * (16.0 / 9.0) if d > 0 else 0.0
    return conf >= CONF_MIN and ASP_MIN <= asp <= ASP_MAX


def sahte_oran_raporu(rows, far_m=40.0):
    """SAHTE-POZITIF ORANI: OTO/gorsel modda gercek hedef UZAK iken (GPS menzil > far_m -> yakinda
    kilitlenecek gercek talon YOK, sahne 'bos') dedektor ne kadar sik KAPI-GECEN (talon_gate)
    tespit uretti = gudume beslenen sahte hedef orani. Amac: arac OLMAYAN talonu takip etmesin."""
    bos = gecen = gecen6 = 0
    for r in rows:
        vm = (r.get("vis_mode") or "").strip()
        gd = (r.get("guidance_source") or "").strip()
        if vm not in ("OTO", "GORSEL") and gd != "GORSEL_GUDUM":
            continue                                          # dedektor gudume beslemiyor -> atla
        mz = _flt(r.get("gps_menzil_m"))
        if mz is None or mz <= far_m:
            continue                                          # yakin/gecerli hedef olabilir -> atla
        bos += 1
        if _gate_gecti(r):
            gecen += 1
            y = _flt(r.get("bbox_yatay_pct")) or 0.0
            d = _flt(r.get("bbox_dikey_pct")) or 0.0
            if max(y, d) >= LOCK_PCT:
                gecen6 += 1
    print("")
    print("=" * 76)
    print("SAHTE-POZITIF ORANI  |  OTO/gorsel modda hedef > %d m (yakinda gercek talon YOK)" % int(far_m))
    print("-" * 76)
    if bos == 0:
        print("  Bu kosuda 'uzak hedef + gudum aktif' kare yok -> oran hesaplanamaz.")
        print("=" * 76)
        return
    print("  Bos-sahne kare (uzak hedef + gudum aktif)   : %d" % bos)
    print("  Kapi-gecen tespit (gudume SAHTE hedef gitti): %d   ->   SAHTE-POZITIF ORANI: %%%.1f"
          % (gecen, 100.0 * gecen / bos))
    print("  bunlardan >=%%6 (uzakta fiziksel imkansiz, KESIN sahte): %d" % gecen6)
    print("=" * 76)


def main():
    saniye, dosya, kopru_ms, far_m = 5.0, None, 400.0, 40.0
    a = sys.argv[1:]
    for i, x in enumerate(a):
        if x == "--saniye" and i + 1 < len(a):
            saniye = float(a[i + 1])
        if x == "--dosya" and i + 1 < len(a):
            dosya = a[i + 1]
        if x == "--kopru-ms" and i + 1 < len(a):
            kopru_ms = float(a[i + 1])
        if x == "--far-m" and i + 1 < len(a):
            far_m = float(a[i + 1])

    if dosya is None:
        cand = sorted(glob.glob(os.path.join(VERI, "kilit_deneme_*.csv")))
        if not cand:
            print("veri/ altinda kilit_deneme_*.csv yok. Once bir kilit denemesi kosun "
                  "(oyun PLAY + gorev baslat).")
            return 1
        dosya = cand[-1]

    with open(dosya, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        print("Bos CSV: %s" % dosya)
        return 1

    ty = [_flt(r.get("t_yerel")) for r in rows]
    tvar = [t for t in ty if t is not None]
    if not tvar:
        print("t_yerel kolonu bos: %s" % dosya)
        return 1
    tson = max(tvar)
    pencere = [r for r, t in zip(rows, ty) if t is not None and (tson - t) <= saniye]

    print("=" * 76)
    print("KILIT DENEMESI OZETI  |  %s" % os.path.basename(dosya))
    print("Toplam kare: %d (~%.1f s)  |  Ozet penceresi: SON %.1f s -> %d kare"
          % (len(rows), tson - min(tvar), saniye, len(pencere)))
    print("-" * 76)
    if not pencere:
        print("Pencerede kare yok (--saniye buyut).")
        return 1

    pt = [t for t in (_flt(r.get("t_yerel")) for r in pencere) if t is not None]
    psure = (max(pt) - min(pt)) if len(pt) > 1 else 0.0
    fps = (len(pencere) / psure) if psure > 0 else 0.0
    detvar = sum(1 for r in pencere if str(r.get("det_var")) in ("1", "1.0"))
    print("  %-22s : %.1f Hz (efektif detektor kadansi)" % ("Kare hizi", fps))
    print("  %-22s : %%%.0f  (%d/%d kare)"
          % ("Tespit orani", 100.0 * detvar / len(pencere), detvar, len(pencere)))

    avrows = [r for r in pencere if str(r.get("det_var")) in ("1", "1.0")]
    avin = sum(1 for r in avrows if str(r.get("av_ici")) in ("1", "1.0"))
    if avrows:
        print("  %-22s : %%%.0f  (tespitli karelerde; full-box)"
              % ("Hedef AV-ici", 100.0 * avin / len(avrows)))

    _ozet_say("GPS menzili (m)", [_flt(r.get("gps_menzil_m")) for r in pencere])
    _ozet_say("PnP menzili (m)", [_flt(r.get("pnp_menzil_m")) for r in pencere])
    _ozet_say("Detektor skoru", [_flt(r.get("det_skor")) for r in pencere])
    _ozet_say("bbox yatay (%)", [_flt(r.get("bbox_yatay_pct")) for r in pencere])
    _ozet_say("bbox dikey (%)", [_flt(r.get("bbox_dikey_pct")) for r in pencere])
    _ozet_say("YOLO suresi (ms)", [_flt(r.get("yolo_ms")) for r in pencere])
    _ozet_say("PnP suresi (ms)", [_flt(r.get("pnp_ms")) for r in pencere])
    _ozet_say("TOPLAM gecikme (ms)", [_flt(r.get("toplam_ms")) for r in pencere])

    dag = Counter((r.get("guidance_source") or "?") for r in pencere)
    print("  %-22s : %s" % ("guidance_source",
          "  ".join("%s %%%.0f" % (k, 100.0 * v / len(pencere)) for k, v in dag.most_common())))
    print("=" * 76)

    blok_analizi(rows, kopru_ms)     # #1: fly-by vs park + tek-geciste potansiyel + 10 sn kumulatif
    sahte_oran_raporu(rows, far_m)   # #2: OTO/gorsel'de uzak-hedefte kapi-gecen sahte tespit orani
    devirler = [r for r in rows if str(r.get("devir")) in ("1", "1.0")]
    if devirler:
        print("")
        print("=== DEVIR ANLARI (GPS/OTO -> gorsel; o andaki bbox + menzil) ===")
        for r in devirler:
            print("  bbox y=%s%% d=%s%% (en/boy=%s)  menzil=%sm  guidance=%s"
                  % (r.get("bbox_yatay_pct"), r.get("bbox_dikey_pct"), r.get("bbox_en_boy"),
                     r.get("gps_menzil_m"), r.get("guidance_source")))
    return 0


if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
"""
================================================================================
  KILIT DENETIM  --  "5 saniye KESINTISIZ kilit olmadan faza gecildi mi?"
                     sorusunun TEK DOSYADAN cevabi
================================================================================
SORU
--------------------------------------------------------------------------------
Kullanici sarti: arac hedefi 5 saniye KESINTISIZ kilitte tutmadan gorsel /
terminal (vurus) fazina gecmemeli. Bu betik o sartin UCUSTA saglanip
saglanmadigini olcer ve NET hukum basar.

VERI KAYNAGI
--------------------------------------------------------------------------------
kopru/gazebo_kaynak/logs/kilit_denetim_*.csv
Bu dosyayi supervisor.py (GPS_VISUAL) ve bbox_ibvs.py (TERMINAL) yazar; her
faz gecisi = bir satir. Kayit KAPI KAPALIYKEN DE tutulur (varsayilan durum),
cunku amac mevcut davranisin ne kadar ihlal urettigini olcmektir.

Satirdaki bagimsiz dogrulanabilir alanlar:
    kesintisiz_kilit_s   gecis anindaki gercek KESINTISIZ kilit suresi
    kilit_t0_wall        kilidin BASLADIGI duvar saati (epoch s)
    gecis_wall           GECIS ani (epoch s)
    fark_s               gecis_wall - kilit_t0_wall  (sureyi bagimsiz dogrular)
    kare_gercek          kilit boyunca sayilan GERCEK tespit karesi
    kare_bosluk          tolere edilen bosluk karesi
    hayalet_kare         kilit icinde tolere edilen HAYALET kare (0 OLMALI)
    conf_medyan          kilit boyunca guven medyani
    kapi / kapi_esik_s   gecise izin veren kapinin adi ve esigi
    sart_s               denetim referansi (AVCI_KILIT_SART_S, varsayilan 5.0)

CALISTIR
    python arac/kilit_denetim.py                 (tum kayitlar)
    python arac/kilit_denetim.py <csv> [<csv>..] (belirli dosyalar)
    python arac/kilit_denetim.py --son 5         (en yeni 5 kayit)
    python arac/kilit_denetim.py --sart 5.0      (referans esigi degistir)

CIKIS KODU
    0 = IHLAL YOK      1 = IHLAL VAR      2 = veri yok
================================================================================
"""
import csv
import glob
import os
import statistics
import sys

# Windows konsolu varsayilan cp1252'dir; bu rapordaki kutu/isaret karakterleri
# (─ ★ ✓ ⚠) orada UnicodeEncodeError firlatir ve DENETIM HIC CALISMAZ.
# (2026-08-17: betik bu yuzden bir kez bile sonuna kadar kosmamisti.)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LOG_DIR = os.path.join(_KOK, "kopru", "gazebo_kaynak", "logs")

OLAY_AD = {"GPS_VISUAL": "GPS -> GORSEL devri",
           "TERMINAL": "TERMINAL (vurus) mandali"}


def _f(v, vars=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return vars


def _i(v, vars=None):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return vars


def q(v, p):
    """p'inci yuzdelik (lineer interpolasyon)."""
    if not v:
        return float("nan")
    v = sorted(v)
    i = (len(v) - 1) * p
    lo = int(i)
    hi = min(lo + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (i - lo)


def oku(yollar):
    satirlar = []
    for y in yollar:
        try:
            with open(y, encoding="utf-8", errors="replace") as f:
                for r in csv.DictReader(f):
                    r["_dosya"] = os.path.basename(y)
                    satirlar.append(r)
        except Exception as e:
            print("  ! okunamadi %s: %r" % (y, e))
    return satirlar


def rapor(satirlar, sart_s):
    if not satirlar:
        print("\nVERI YOK — hic kilit_denetim_*.csv satiri bulunamadi.")
        print("Sebep olabilir: (a) gorev hic faz degistirmedi, (b) denetim")
        print("kaydi kapali (AVCI_KILIT_DENETIM=0), (c) yama sonrasi hic")
        print("ucus yapilmadi. Kayit VARSAYILAN OLARAK ACIKTIR.")
        return 2

    ihlal_top = 0
    toplam = 0
    print("=" * 78)
    print(" KILIT DENETIMI — referans sart: %.1f s KESINTISIZ kilit" % sart_s)
    print("=" * 78)

    for olay in ("GPS_VISUAL", "TERMINAL"):
        grup = [r for r in satirlar if (r.get("olay") or "") == olay]
        if not grup:
            continue
        sureler = [_f(r.get("kesintisiz_kilit_s"), 0.0) for r in grup]
        ihlaller = [(i, r, s) for i, (r, s) in enumerate(zip(grup, sureler), 1)
                    if s < sart_s]
        ihlal_top += len(ihlaller)
        toplam += len(grup)
        kapi_acik = any(_i(r.get("kapi_acik"), 0) == 1 for r in grup)

        print("\n── %s ── (%s)" % (OLAY_AD.get(olay, olay), olay))
        print("  gecis sayisi          : %d" % len(grup))
        print("  kapi durumu           : %s"
              % ("ACIK (AVCI_KILIT_S>0)" if kapi_acik
                 else "KAPALI (AVCI_KILIT_S=0) — salt olcum"))
        print("  kesintisiz kilit (s)  : medyan %.2f | min %.2f | p10 %.2f "
              "| p90 %.2f | max %.2f"
              % (statistics.median(sureler), min(sureler), q(sureler, 0.10),
                 q(sureler, 0.90), max(sureler)))
        n_ok = len(grup) - len(ihlaller)
        print("  >=%.1f s saglayan      : %d / %d  (%%%.1f)"
              % (sart_s, n_ok, len(grup), 100.0 * n_ok / len(grup)))

        # bagimsiz dogrulama: fark_s ile kesintisiz_kilit_s tutuyor mu
        tutmaz = 0
        for r in grup:
            a = _f(r.get("kesintisiz_kilit_s"))
            b = _f(r.get("fark_s"))
            if a is not None and b is not None and abs(a - b) > 0.05:
                tutmaz += 1
        print("  zaman damgasi tutarli : %d / %d satir (fark_s == kilit_s)"
              % (len(grup) - tutmaz, len(grup)))

        hay = [_i(r.get("hayalet_kare"), 0) for r in grup]
        hay_var = sum(1 for x in hay if x > 0)
        print("  hayalet kare (0 olmali): %d gecis > 0  (toplam %d kare)"
              % (hay_var, sum(hay)))

        # ── DOLULUK: kilit suresi TEK BASINA yaniltir ──────────────────────
        # Kilit tanimi tek bir boslugun UZUNLUGUNU sinirlar ama SAYISINI
        # sinirlamaz; "2 kare gor / 0.3 s kor kal" dizisi 5 s "kesintisiz"
        # kilit uretebilir. DOLULUK, o surenin yuzde kacinin GERCEKTEN
        # gozlemlendigini soyler. Eski kayitlarda bu kolon YOKTUR.
        dol = [_f(r.get("doluluk")) for r in grup]
        dol = [d for d in dol if d is not None]
        if dol:
            kor = [_f(r.get("kor_s"), 0.0) or 0.0 for r in grup]
            print("  DOLULUK (gozlemlenen): medyan %%%.1f | en dusuk %%%.1f "
                  "| kilit icindeki kor sure medyan %.2f s"
                  % (100 * statistics.median(dol), 100 * min(dol),
                     statistics.median(kor)))
            zayif = sum(1 for d in dol if d < 0.5)
            if zayif:
                print("    ! %d gecis %%50'den AZ gozlemle 'kilitli' sayildi "
                      "(sure sarti saglansa bile bu KESINTISIZ DEGILDIR)"
                      % zayif)
        else:
            print("  DOLULUK               : OLCULMEDI (kayit bu kolondan once)")
        confs = [_f(r.get("conf_medyan")) for r in grup]
        confs = [c for c in confs if c is not None]
        if confs:
            print("  conf medyani          : %.2f (gecisler arasi medyan)"
                  % statistics.median(confs))
        kg = [_i(r.get("kare_gercek"), 0) for r in grup]
        kb = [_i(r.get("kare_bosluk"), 0) for r in grup]
        if kg:
            print("  kare: gercek medyan %d | tolere edilen bosluk medyan %d"
                  % (statistics.median(kg), statistics.median(kb)))

        if ihlaller:
            print("\n  ★ IHLALLER (%d):" % len(ihlaller))
            print("    %-4s %-19s %8s %8s %7s  %s"
                  % ("#", "zaman", "kilit_s", "eksik_s", "kare", "izin veren kapi"))
            for i, r, s in ihlaller[:25]:
                print("    %-4d %-19s %8.2f %8.2f %7s  %s"
                      % (i, r.get("t_wall_iso", "?"), s, sart_s - s,
                         r.get("kare_gercek", "?"), r.get("kapi", "?")))
            if len(ihlaller) > 25:
                print("    ... ve %d ihlal daha" % (len(ihlaller) - 25))
            # en sik izin veren kapi
            kapilar = {}
            for _, r, _s2 in ihlaller:
                k = r.get("kapi", "?")
                kapilar[k] = kapilar.get(k, 0) + 1
            print("\n    Erken acan kapilar:")
            for k, n in sorted(kapilar.items(), key=lambda x: -x[1]):
                print("      %4d kez  %s" % (n, k))

    print("\n" + "=" * 78)
    if toplam == 0:
        print(" VERI YOK — kayitta faz gecisi satiri yok.")
        return 2
    if ihlal_top == 0:
        print(" ✓ IHLAL YOK — %d gecisin hepsi >=%.1f s KESINTISIZ kilitten sonra."
              % (toplam, sart_s))
        # MEKANIZMA KAPISI: kapi gercekten ACIK miydi? Kapi KAPALIYKEN de
        # "ihlal yok" cikabilir (hic gecis olmamissa ya da tesadufen). O
        # durumda bu sonuc SARTIN UYGULANDIGINI KANITLAMAZ.
        acik = sum(1 for r in satirlar if _i(r.get("kapi_acik"), 0) == 1)
        if acik == 0:
            print(" ⚠ ANCAK: kapi KAPALIYDI (kapi_acik=0). Sart UYGULANMADI,")
            print("   yalnizca bu kosuda tesadufen ihlal olmadi. Kapiyi")
            print("   AVCI_KILIT_S=%.1f ile acmadan bu sonuc KANIT DEGILDIR."
                  % sart_s)
        print("=" * 78)
        return 0
    print(" ★ IHLAL: %d gecisten %d tanesi ERKEN (>=%.1f s kesintisiz kilit YOK)."
          % (toplam, ihlal_top, sart_s))
    print("   Oran: %%%.1f  |  Uygulanacak: AVCI_KILIT_S=%.1f ile kapiyi ac."
          % (100.0 * ihlal_top / toplam, sart_s))
    print("=" * 78)
    return 1


def main(argv):
    sart_s = 5.0
    son_n = None
    yollar = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--sart" and i + 1 < len(argv):
            sart_s = float(argv[i + 1]); i += 2; continue
        if a == "--son" and i + 1 < len(argv):
            son_n = int(argv[i + 1]); i += 2; continue
        yollar.append(a); i += 1
    if not yollar:
        yollar = sorted(glob.glob(os.path.join(_LOG_DIR, "kilit_denetim_*.csv")))
        if son_n:
            yollar = yollar[-son_n:]
    if not yollar:
        print("kilit_denetim_*.csv bulunamadi: %s" % _LOG_DIR)
        return 2
    print("okunan kayit: %d dosya" % len(yollar))
    return rapor(oku(yollar), sart_s)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

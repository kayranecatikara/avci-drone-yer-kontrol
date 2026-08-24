# -*- coding: utf-8 -*-
"""
================================================================================
 kilit_tezgah.py — KESINTISIZ KILIT TEZGAHI (cevrimdisi, oyunsuz)
================================================================================
NE YAPAR
--------------------------------------------------------------------------
Gercek ucus loglarindaki (karar_*.csv, TAM sema) KARE AKISINI, depoda FIILEN
CALISAN `KesintisizKilit` sinifina yeniden besler ve supervisor'in devir
kararini birebir yeniden oynatir. Boylece OYUN ACMADAN:

  * farkli kilit TANIMLARINI (bosluk toleransi, conf, hayalet, kadraj, koast)
    tarayabiliriz,
  * her tanim icin  [>=5 s epizod sayisi]  vs  [DEVIR sayisi]  odunlesimini
    cikarabiliriz,
  * bir tanimin angajmani ÖLDÜRÜP oldurmedigini ONCEDEN gorebiliriz.

⚠ TEZGAH KENDI KILIT MANTIGINI YAZMAZ. `control.guidance.kesintisiz_kilit`
  modulunu IMPORT eder. Amac tam olarak budur: 2026-08-16'da tesis kendi
  yeniden-yazimindan iki SAHTE bulgu uretmisti. Burada olculen sey, ucusta
  calisacak KODUN TA KENDISIDIR.

VERI SOZLESMESI (karar_*.csv, supervisor.py:795-806 / 850-867)
--------------------------------------------------------------------------
  t          supervisor monoton saati (s)
  gorulen    supervisor'in "gecerli tespit" bayragi (BOYUT kapisi UYGULANMIS)
  conf       dedektor guveni
  w,h        kutu boyutu (yasa cercevesi px)   -- pose varsa dolu
  cx_yasa,cy_yasa  kutu merkezi (yasa cercevesi px)
  eleme      KUTU_YOK | CONF_DUSUK | HAYALET | BOYUT | DIGER | "" (gecerli)
  kilit_kes_s  UCUSTA olculen kesintisiz kilit (dogrulama referansi)
  u_truth,v_truth  hedefin GERCEK goruntu-duzlemi izdusumu (motor truth)
  d_h_m      menzil (m)

KARE -> kk.guncelle() ESLEMESI supervisor.py:687-689 ile BIREBIR:
    tespit  = {cx,cy,w,h,conf} if w varsa else None      (HAM pose, BOYUT dahil)
    hayalet = (eleme == "HAYALET")

CALISTIR
    python arac/kilit_tezgah.py                    # ozet + taban dogrulama
    python arac/kilit_tezgah.py --tara             # ODUNLESIM taramasi
    python arac/kilit_tezgah.py --kaynak "logs/karar_2026*.csv"
    python arac/kilit_tezgah.py --dogrula          # tezgah == ucus mu?
================================================================================
"""
import argparse
import csv
import glob
import math
import os
import statistics as st
import sys

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LOG = os.path.join(_KOK, "kopru", "gazebo_kaynak", "logs")
sys.path.insert(0, os.path.join(_KOK, "kopru", "gazebo_kaynak"))

from control.guidance.kesintisiz_kilit import (  # noqa: E402
    KesintisizKilit, KilitKapiCfg)

# supervisor'in ETKIN (OTO) kolundaki devir olcutu — supervisor.py:76,868
KILIT_N = 10
# GPS fazina yeniden girisi isaretleyen zaman bosluğu: supervisor her GPS
# fazinda YENI bir KesintisizKilit yaratir (supervisor.py:507), bu yuzden
# akista boyle bir kopus gorulunce sayaclar sifirlanmalidir.
FAZ_BOSLUK_S = 1.0


def _f(v, vars=None):
    try:
        x = float(v)
        return x if x == x else vars          # NaN ele
    except (TypeError, ValueError):
        return vars


# ══════════════════════════════════════════════════════════════════════════
#  VERI YUKLEME
# ══════════════════════════════════════════════════════════════════════════
GEREKLI = ("w", "eleme", "kilit_kes_s")


def sema_tam(yol):
    try:
        with open(yol, encoding="utf-8", errors="replace") as f:
            h = f.readline()
        return all(k in h for k in GEREKLI)
    except Exception:
        return False


def yukle(yollar, faz="GPS"):
    """karar_*.csv -> kare listesi (dosya basina bir AKIS)."""
    akislar = []
    for y in yollar:
        if not sema_tam(y):
            continue
        kareler = []
        try:
            with open(y, encoding="utf-8", errors="replace") as f:
                for r in csv.DictReader(f):
                    if faz and (r.get("faz") or "") != faz:
                        continue
                    t = _f(r.get("t"))
                    if t is None:
                        continue
                    w, h = _f(r.get("w")), _f(r.get("h"))
                    kareler.append({
                        "t": t,
                        "gorulen": (r.get("gorulen") or "0").strip() in ("1", "True", "true"),
                        "conf": _f(r.get("conf"), 0.0),
                        "w": w, "h": h,
                        "cx": _f(r.get("cx_yasa")), "cy": _f(r.get("cy_yasa")),
                        "eleme": (r.get("eleme") or "").strip(),
                        "kilit_kes_s": _f(r.get("kilit_kes_s")),
                        "u_truth": _f(r.get("u_truth")),
                        "v_truth": _f(r.get("v_truth")),
                        "d_h": _f(r.get("d_h_m")),
                        "karar": (r.get("karar") or "").strip(),
                        "mod": (r.get("mod") or "").strip(),
                    })
        except Exception as e:
            print("  ! okunamadi %s: %r" % (os.path.basename(y), e))
            continue
        if len(kareler) >= 50:
            akislar.append({"ad": os.path.basename(y), "kare": kareler})
    return akislar


def kaynaklar(desen=None, en_az=50):
    yollar = (sorted(glob.glob(desen)) if desen
              else sorted(glob.glob(os.path.join(_LOG, "karar_*.csv")),
                          key=os.path.getmtime))
    return [y for y in yollar if sema_tam(y)]


# ══════════════════════════════════════════════════════════════════════════
#  KARE -> kk GIRDISI  (supervisor.py:687-689 ile birebir)
# ══════════════════════════════════════════════════════════════════════════
def kk_girdisi(k):
    hayalet = (k["eleme"] == "HAYALET")
    if hayalet or k["w"] is None:
        return None, hayalet
    return {"cx": k["cx"], "cy": k["cy"], "w": k["w"], "h": k["h"],
            "conf": k["conf"]}, hayalet


# ══════════════════════════════════════════════════════════════════════════
#  AYAR SHIM — gercek sinifi farkli TANIMLARLA kosturmak icin
# ══════════════════════════════════════════════════════════════════════════
class Ayar(object):
    """KilitKapiCfg klonu; tarama icin alan alan degistirilebilir."""

    # ⚠ BURAYA EKLENMEYEN ALAN SESSIZCE DUSER: Ayar, KilitKapiCfg'nin
    # KLONUDUR ve eksik alan varsayilana geri doner -> tarama o ekseni HIC
    # denemez ama tabloyu yine de basar (2026-08-17'de DOLULUK_MIN ve
    # BOSLUK_MOD bu yuzden etkisiz gorunuyordu). Yeni env alani eklerken
    # BURAYI da guncelle; asagidaki test bunu KILITLER.
    _ALAN = ("ESIK_S", "CONF_MIN", "BOSLUK_KARE", "BOSLUK_S", "BOSLUK_MOD",
             "KADRAJ_PAY", "W", "H", "KADRAJ_MOD",
             "DOW_U0", "DOW_U1", "DOW_V0", "DOW_V1",
             "SART_S", "DOLULUK_MIN")

    def __init__(self, **kw):
        for a in self._ALAN:
            setattr(self, a, getattr(KilitKapiCfg, a, None))
        for a, v in kw.items():
            setattr(self, a, v)

    def acik(self):
        return float(self.ESIK_S or 0.0) > 0.0

    def etiket(self):
        p = ["bosluk=%dk/%.2fs(%s)" % (self.BOSLUK_KARE, self.BOSLUK_S,
                                       self.BOSLUK_MOD),
             "conf=%.2f" % self.CONF_MIN,
             "kadraj=%s" % self.KADRAJ_MOD]
        if float(self.DOLULUK_MIN or 0.0) > 0.0:
            p.append("doluluk>=%.2f" % self.DOLULUK_MIN)
        return " ".join(p)


# ══════════════════════════════════════════════════════════════════════════
#  YENIDEN OYNATMA
# ══════════════════════════════════════════════════════════════════════════
def oynat(akis, ayar, kilit_esik_s=0.0):
    """Bir akisi bastan sona kostur.

    kilit_esik_s : DEVIR kapisinin esigi (0 = kapi KAPALI = bugunku davranis)

    Doner: {
      "epizod":   [her kesintisiz kilit epizodunun suresi],
      "devir":    kac kez GPS->GORSEL devri tetiklenirdi,
      "devir_kilit": [devir anindaki kesintisiz kilit suresi],
      "ihlal":    devirlerin kacinda kilit < SART_S,
      "kare":     islenen kare sayisi,
      "sure_s":   akis suresi,
    }
    """
    ayar = ayar or Ayar()
    ayar.ESIK_S = float(kilit_esik_s)
    kk = KesintisizKilit(cfg=ayar)
    ardisik = 0
    epizod, devir_kilit = [], []
    zirve = 0.0
    onceki_t = None
    kare = akis["kare"]
    sart = float(getattr(ayar, "SART_S", 5.0) or 5.0)

    def epizodu_kapat():
        nonlocal zirve
        if zirve > 0.0:
            epizod.append(zirve)
        zirve = 0.0

    for k in kare:
        t = k["t"]
        # GPS fazina yeniden giris -> supervisor yeni kk yaratir
        if onceki_t is not None and (t - onceki_t) > FAZ_BOSLUK_S:
            epizodu_kapat()
            kk = KesintisizKilit(cfg=ayar)
            ardisik = 0
        onceki_t = t

        tespit, hayalet = kk_girdisi(k)
        onceki_kirilma = kk.kirilma
        sure = kk.guncelle(tespit, t, hayalet=hayalet)
        if kk.kirilma > onceki_kirilma:      # kilit KIRILDI -> epizod bitti
            epizodu_kapat()
        zirve = max(zirve, sure)

        # ── supervisor OTO kolu (supervisor.py:839-902) ──────────────────
        ardisik = (ardisik + 1) if k["gorulen"] else 0
        if ardisik >= KILIT_N and kk.gecti():
            devir_kilit.append(sure)
            epizodu_kapat()
            kk = KesintisizKilit(cfg=ayar)   # yeni GPS fazi -> yeni sayac
            ardisik = 0

    epizodu_kapat()
    t0, t1 = kare[0]["t"], kare[-1]["t"]
    return {
        "epizod": epizod,
        "devir": len(devir_kilit),
        "devir_kilit": devir_kilit,
        "ihlal": sum(1 for s in devir_kilit if s < sart),
        "kare": len(kare),
        "sure_s": t1 - t0,
    }


def topla(akislar, ayar, kilit_esik_s=0.0):
    """Tum akislari kostur ve BIRLESTIR."""
    top = {"epizod": [], "devir": 0, "devir_kilit": [], "ihlal": 0,
           "kare": 0, "sure_s": 0.0}
    for a in akislar:
        r = oynat(a, ayar, kilit_esik_s)
        top["epizod"] += r["epizod"]
        top["devir"] += r["devir"]
        top["devir_kilit"] += r["devir_kilit"]
        top["ihlal"] += r["ihlal"]
        top["kare"] += r["kare"]
        top["sure_s"] += r["sure_s"]
    return top


def ozet(r, sart=5.0):
    e = r["epizod"]
    n5 = sum(1 for x in e if x >= sart)
    return {
        "epizod_n": len(e),
        "epizod_med": st.median(e) if e else 0.0,
        "epizod_p90": (sorted(e)[int(0.9 * (len(e) - 1))] if e else 0.0),
        "epizod_max": max(e) if e else 0.0,
        "n5": n5,
        "devir": r["devir"],
        "ihlal": r["ihlal"],
        "devir_med": (st.median(r["devir_kilit"]) if r["devir_kilit"] else 0.0),
    }


# ══════════════════════════════════════════════════════════════════════════
#  RAPORLAR
# ══════════════════════════════════════════════════════════════════════════
def r_taban(akislar, sart):
    print("=" * 78)
    print(" TABAN — bugunku tanim (bosluk %d kare / %.2f s, conf %.2f, kadraj %s)"
          % (KilitKapiCfg.BOSLUK_KARE, KilitKapiCfg.BOSLUK_S,
             KilitKapiCfg.CONF_MIN, KilitKapiCfg.KADRAJ_MOD))
    print("=" * 78)
    a = Ayar(SART_S=sart)
    r = topla(akislar, a, 0.0)
    o = ozet(r, sart)
    print("  akis %d | kare %d | sure %.0f s" % (len(akislar), r["kare"], r["sure_s"]))
    print("  KESINTISIZ epizod : n=%d  medyan %.2f s  p90 %.2f s  max %.2f s"
          % (o["epizod_n"], o["epizod_med"], o["epizod_p90"], o["epizod_max"]))
    print("  >=%.1f s epizod    : %d  (%%%.2f)"
          % (sart, o["n5"], 100.0 * o["n5"] / max(1, o["epizod_n"])))
    print("  DEVIR (kapi KAPALI): %d   devir anindaki kilit medyani %.2f s"
          % (o["devir"], o["devir_med"]))
    print("  IHLAL (<%.1f s)    : %d / %d  (%%%.1f)"
          % (sart, o["ihlal"], o["devir"], 100.0 * o["ihlal"] / max(1, o["devir"])))
    return r


def r_dogrula(akislar):
    """TEZGAH KAPISI: tezgahin urettigi kilit suresi, UCUSTA loglanan
    kilit_kes_s ile ayni mi? Ayni degilse tezgah GECERSIZDIR."""
    print("\n" + "=" * 78)
    print(" TEZGAH KAPISI — tezgah kilidi == ucusta loglanan kilit_kes_s ?")
    print("=" * 78)
    a = Ayar()
    a.ESIK_S = 0.0
    top_n = top_ok = 0
    hata = []
    sapma = []
    for akis in akislar:
        kk = KesintisizKilit(cfg=a)
        onceki_t = None
        for k in akis["kare"]:
            t = k["t"]
            if onceki_t is not None and (t - onceki_t) > FAZ_BOSLUK_S:
                kk = KesintisizKilit(cfg=a)
            onceki_t = t
            tespit, hayalet = kk_girdisi(k)
            s = kk.guncelle(tespit, t, hayalet=hayalet)
            ref = k["kilit_kes_s"]
            if ref is None:
                continue
            top_n += 1
            d = abs(s - ref)
            sapma.append(d)
            if d <= 0.06:      # bir kare toleransi
                top_ok += 1
            elif len(hata) < 5:
                hata.append((akis["ad"], t, s, ref, k["eleme"]))
    if top_n == 0:
        print("  kilit_kes_s kolonu bos - DOGRULANAMADI")
        return False
    o = 100.0 * top_ok / top_n
    print("  eslesen kare: %d / %d  (%%%.2f)" % (top_ok, top_n, o))
    ss = sorted(sapma)
    print("  sapma |tezgah-ucus| (s): medyan %.4f  p99 %.3f  max %.3f"
          % (st.median(ss), ss[int(0.99 * (len(ss) - 1))], ss[-1]))
    # Sapma bir KARE PERIYODUNDAN buyuk mu? Buyukse mantik farkidir, degilse
    # yalniz saat ofsetidir (karar_log kendi t0'ini kullanir, kk ise
    # kayit["t"] -- supervisor.py:687).
    buyuk = sum(1 for d in sapma if d > 0.12)
    print("  > 2 kare (0.12 s) sapan : %d  (%%%.3f)  <- mantik farki BURADA olur"
          % (buyuk, 100.0 * buyuk / top_n))
    for h in hata:
        print("    ! %s t=%.2f tezgah=%.2f ucus=%.2f eleme=%s" % h)
    print("  HUKUM: %s" % ("[OK] TEZGAH GECERLI (ucusla ayni)" if o >= 97.0
                           else "[!!] TEZGAH SAPIYOR - bulgular GECERSIZ"))
    return o >= 97.0


def _sebep_sinifi(son_sebep):
    """kk.son_sebep -> kopma sinifi. ⚠ `eleme` DEGIL: BOYUT kapisina takilan
    kare kilit acisindan GECERLIDIR (ham pose beslenir), onu kopma sebebi
    saymak yanlis taksonomi uretir (ilk surumde bu hataya dusuldu)."""
    s = (son_sebep or "").lower()
    if s.startswith("gecerli"):
        return None
    if "tespit yok" in s:
        return "KUTU_YOK"
    if "hayalet" in s:
        return "HAYALET"
    if s.startswith("conf"):
        return "CONF"
    if "kadraj" in s:
        return "KADRAJ"
    if "kutu bos" in s:
        return "KUTU_BOS"
    return "DIGER"


def r_kopma(akislar):
    """Kilit neden kiriliyor? Kirilmaya sebep olan karenin sinifi."""
    print("\n" + "=" * 78)
    print(" KOPMA TAKSONOMISI - kilidi KIRAN karenin sinifi")
    print("=" * 78)
    a = Ayar()
    a.ESIK_S = 0.0
    sayim = {}
    top = 0
    for akis in akislar:
        kk = KesintisizKilit(cfg=a)
        onceki_t = None
        bekleyen = []            # tolere edilen bosluklarin sinifi
        for k in akis["kare"]:
            t = k["t"]
            if onceki_t is not None and (t - onceki_t) > FAZ_BOSLUK_S:
                kk = KesintisizKilit(cfg=a)
                bekleyen = []
            onceki_t = t
            tespit, hayalet = kk_girdisi(k)
            once = kk.kirilma
            kk.guncelle(tespit, t, hayalet=hayalet)
            e = _sebep_sinifi(kk.son_sebep)
            if e is None:
                bekleyen = []
            else:
                bekleyen.append(e)
            if kk.kirilma > once:
                # kiran zincirin ILK sinifi -> asil sebep
                sinif = bekleyen[0] if bekleyen else e
                sayim[sinif] = sayim.get(sinif, 0) + 1
                top += 1
                bekleyen = []
    for s, n in sorted(sayim.items(), key=lambda x: -x[1]):
        print("  %-12s %5d  (%%%.1f)" % (s, n, 100.0 * n / max(1, top)))
    print("  TOPLAM kirilma: %d" % top)
    return sayim


def r_gercek(akislar, sart, gate_k=3.0, gercek_min=0.90):
    """★ TANIMIN NAMUSLULUK TESTI — bir ">=5 s kilit" GERCEKTEN o hedefi mi
    izliyordu?

    Kilit epizodunun her SAYILAN karesinde, dedektor kutusunun merkezi ile
    motorun TRUTH izdusumu (u_truth,v_truth) karsilastirilir. Kutu, hedefin
    gate_k * max(w,h) yaricapindaki halkasinin icindeyse o kare "hedefte"
    sayilir. Epizodun truth-kapsamli karelerinin >= gercek_min'i hedefteyse
    epizod GERCEK'tir.

    NEDEN GEREKLI: bosluk toleransini buyutmek ">=5 s epizod" SAYISINI
    artirir, ama tolere edilen bosluktan sonra dedektor BASKA bir seyi
    yakalamis olabilir. O zaman "5 s kesintisiz kilit" bir YALANDIR. Bu
    olcum, tanimi gevsetmenin kazanci SAHTE mi diye dogrudan bakar.
    """
    print("\n" + "=" * 78)
    print(" TANIM NAMUSLULUK TESTI - '>=%.1f s kilit' GERCEK hedefte miydi?"
          % sart)
    print(" (kare hedefte := |kutu - truth| <= %.1f*max(w,h);"
          " epizod GERCEK := >=%.0f%% kare hedefte)" % (gate_k, 100 * gercek_min))
    print("=" * 78)
    print("  %-34s %6s %6s %8s %9s | %6s"
          % ("TANIM", ">=%.0fs" % sart, "GERCEK", "sahte_%", "truth_kap", "devir"))
    print("  " + "-" * 76)
    cikti = []
    for et, kw in tanim_izgarasi():
        a = Ayar(SART_S=sart, **kw)
        a.ESIK_S = 0.0
        n5 = n5g = 0
        kap_top = kap_n = 0
        devir5 = topla(akislar, a, sart)["devir"]
        for akis in akislar:
            for ep in _epizodlar(akis, a):
                if ep["sure"] < sart:
                    continue
                n5 += 1
                iyi = tum = 0
                for (cx, cy, w, h, u, v) in ep["kare"]:
                    if u is None or v is None or cx is None:
                        continue
                    tum += 1
                    if math.hypot(cx - u, cy - v) <= gate_k * max(4.0, w, h):
                        iyi += 1
                if tum == 0:
                    continue                      # truth yok -> hukum verilemez
                kap_top += tum
                kap_n += len(ep["kare"])
                if iyi / tum >= gercek_min:
                    n5g += 1
        sahte = (100.0 * (n5 - n5g) / n5) if n5 else 0.0
        kap = (100.0 * kap_top / kap_n) if kap_n else 0.0
        print("  %-34s %6d %6d %7.1f%% %8.1f%% | %6d"
              % (et, n5, n5g, sahte, kap, devir5))
        cikti.append((et, n5, n5g, devir5))
    print("\n  OKUMA: 'sahte_%' epizod KIMLIGINI olcer (baska hedefe atlama).")
    print("  Bu sutun dusuk cikiyorsa tanim gevsetilebilir DEMEK DEGILDIR:")
    print("  kimlik korunsa bile arac o sure boyunca KOR olabilir. Asil olcut")
    print("  DOLULUK'tur (--doluluk), yani '5 s kilit'in kaci GERCEKTEN")
    print("  gozlemlendi.")
    return cikti


def r_doluluk(akislar, sart):
    """★ ASIL OLCUT — bir '>=5 s kesintisiz kilit'in ne kadari GERCEKTEN
    gozlemlendi?

    DOLULUK = (epizod suresi - tolere edilen KOR sure) / epizod suresi

    Bosluk toleransini buyutmek ">=5 s epizod" sayisini artirir, ama bunu
    epizodun icine KOR ZAMAN doldurarak yapar. "5 saniye KESINTISIZ kilit"
    sarti, arastirma sonucu ne olursa olsun, icinde 2 saniye korluk olan bir
    pencereyle KARSILANMIS SAYILAMAZ. Bu tablo o bedeli gorunur kilar.
    """
    print("\n" + "=" * 78)
    print(" DOLULUK - '>=%.1f s kilit'in yuzde kaci GERCEKTEN gozlemlendi?" % sart)
    print("=" * 78)
    print("  %-34s %6s %8s %8s %9s %9s"
          % ("TANIM", ">=%.0fs" % sart, "doluluk", "en_kotu", "kor_med_s",
             "max_bosluk"))
    print("  " + "-" * 76)
    for et, kw in tanim_izgarasi():
        a = Ayar(SART_S=sart, **kw)
        a.ESIK_S = 0.0
        dol, kor, mxb = [], [], []
        n5 = 0
        for akis in akislar:
            for ep in _epizodlar(akis, a, iz=True):
                if ep["sure"] < sart:
                    continue
                n5 += 1
                kor_s = sum(ep["bosluk"])
                top = ep["sure"]
                dol.append(max(0.0, (top - kor_s) / top) if top > 0 else 0.0)
                kor.append(kor_s)
                mxb.append(max(ep["bosluk"]) if ep["bosluk"] else 0.0)
        if not dol:
            print("  %-34s %6d  (epizod yok)" % (et, n5))
            continue
        print("  %-34s %6d %7.1f%% %7.1f%% %9.2f %9.2f"
              % (et, n5, 100 * st.median(dol), 100 * min(dol),
                 st.median(kor), max(mxb)))
    print("\n  OKUMA: doluluk %100'den ne kadar duserse, '5 s kesintisiz kilit'")
    print("  o kadar SAHTE bir iddiadir. Kullanici sarti KESINTISIZLIK oldugu")
    print("  icin dogru tanim, doluluk'u yuksek tutan EN KUCUK bosluk")
    print("  toleransidir - epizod sayisini en cok buyuten degil.")


def kare_periyodu(akis):
    """Akisin GERCEK kare periyodu (medyan dt).

    ⚠ SABIT 0.05 s VARSAYMA. Olculen periyot loga gore 0.04-0.07 s arasinda
    degisiyor (13:19 kosusu 0.07 s = 14.3 fps). Ilk surumde 0.05 s sabiti
    kullanildi ve NORMAL kare adimlari "kor zaman" sayildi -> doluluk %22.6
    gibi SAHTE bir sonuc cikti. Periyot akistan olculur."""
    ts = [k["t"] for k in akis["kare"]]
    d = [b - a for a, b in zip(ts, ts[1:]) if 0 < b - a < 1.0]
    return st.median(d) if d else 0.05


def _epizodlar(akis, ayar, iz=False):
    """Bir akistaki kesintisiz kilit epizodlarini, SAYILAN kareleriyle
    birlikte cikar. iz=True ise tolere edilen KOR araliklar da olculur.

    Epizod, kilidin FIILEN basladigi anda baslar (kk._t0 None -> deger);
    kilit oncesi kareler epizoda KATILMAZ."""
    kk = KesintisizKilit(cfg=ayar)
    dt0 = kare_periyodu(akis)
    out = []

    def yeni():
        return {"sure": 0.0, "kare": [], "bosluk": [], "dt": dt0}

    cur = yeni()
    onceki_t = None
    son_ok_t = None          # son GECERLI karenin ani (kor araligi olcmek icin)
    for k in akis["kare"]:
        t = k["t"]
        if onceki_t is not None and (t - onceki_t) > FAZ_BOSLUK_S:
            if cur["sure"] > 0:
                out.append(cur)
            cur = yeni()
            son_ok_t = None
            kk = KesintisizKilit(cfg=ayar)
        onceki_t = t
        tespit, hayalet = kk_girdisi(k)
        once = kk.kirilma
        onceki_t0 = kk._t0
        s = kk.guncelle(tespit, t, hayalet=hayalet)
        if kk.kirilma > once:
            if cur["sure"] > 0:
                out.append(cur)
            cur = yeni()
            son_ok_t = None
        if onceki_t0 is None and kk._t0 is not None:
            cur = yeni()          # kilit YENI basladi -> epizod burada baslar
            son_ok_t = None
        if kk.son_sebep == "gecerli":
            cur["kare"].append((k["cx"], k["cy"], k["w"] or 0.0, k["h"] or 0.0,
                                k["u_truth"], k["v_truth"]))
            if iz and son_ok_t is not None:
                # KOR sure = araligin bir kare periyodunu ASAN kismi
                bos = (t - son_ok_t) - dt0
                if bos > 0.5 * dt0:
                    cur["bosluk"].append(bos)
            son_ok_t = t
        cur["sure"] = max(cur["sure"], s)
    if cur["sure"] > 0:
        out.append(cur)
    return out


def r_tara(akislar, sart):
    """ODUNLESIM TARAMASI — kilit tanimini oynat, [>=5 s epizod] ve
    [kapi ACIKKEN devir] nasil degisiyor gor."""
    print("\n" + "=" * 78)
    print(" ODUNLESIM TARAMASI  (sart %.1f s)" % sart)
    print("=" * 78)
    print("  %-38s %6s %7s %7s %6s | %6s %6s"
          % ("TANIM", "epiz", "medyan", "max", ">=%.0fs" % sart,
             "devir0", "devir5"))
    print("  " + "-" * 76)
    satirlar = []
    for et, kw in tanim_izgarasi():
        a = Ayar(SART_S=sart, **kw)
        r0 = topla(akislar, a, 0.0)          # kapi KAPALI -> taban devir
        r5 = topla(akislar, a, sart)         # kapi ACIK   -> gercek devir
        o0 = ozet(r0, sart)
        o5 = ozet(r5, sart)
        print("  %-38s %6d %7.2f %7.2f %6d | %6d %6d"
              % (et, o0["epizod_n"], o0["epizod_med"], o0["epizod_max"],
                 o0["n5"], o0["devir"], o5["devir"]))
        satirlar.append((et, o0, o5))
    return satirlar


def r_esik(akislar, esikler=(0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0)):
    """★ KARAR TABLOSU — AVCI_KILIT_S esigi ile DEVIR sayisi arasindaki
    odunlesim. Kullanicinin esigi BILEREK secebilmesi icin."""
    print("\n" + "=" * 78)
    print(" KARAR TABLOSU - AVCI_KILIT_S esigi vs ANGAJMAN")
    print("=" * 78)
    a = Ayar()
    taban = topla(akislar, a, 0.0)["devir"]
    print("  %-10s %8s %9s %11s %12s"
          % ("esik (s)", "devir", "taban_%", "kayip_devir", "ihlal"))
    print("  " + "-" * 60)
    out = []
    for e in esikler:
        r = topla(akislar, Ayar(SART_S=max(e, 0.001)), e)
        d = r["devir"]
        # kapi ACIKKEN ihlal: tanim geregi 0 olmali (mekanizma kapisi)
        ihl = sum(1 for s in r["devir_kilit"] if s < e - 1e-6)
        print("  %-10.1f %8d %8.1f%% %11d %12d"
              % (e, d, 100.0 * d / max(1, taban), taban - d, ihl))
        out.append((e, d, ihl))
    print("\n  'ihlal' sutunu MEKANIZMA KAPISIDIR: kapi acikken 0 OLMALIDIR.")
    print("  0 degilse kapi fiilen uygulanmiyor demektir ve deney GECERSIZDIR.")
    return out


def tanim_izgarasi():
    """Taranacak kilit TANIMLARI. Her biri TEK bir eksende oynar."""
    g = []
    g.append(("TABAN (bosluk 3k/0.35s, conf .35)", {}))
    for bk in (0, 1, 2, 3, 5, 8, 12, 20, 30):
        g.append(("bosluk %2d kare (sure serbest)" % bk,
                  {"BOSLUK_KARE": bk, "BOSLUK_S": 99.0}))
    for bs in (0.10, 0.20, 0.35, 0.50, 0.75, 1.00, 1.50, 2.00):
        g.append(("bosluk %.2f s (kare serbest)" % bs,
                  {"BOSLUK_KARE": 10 ** 6, "BOSLUK_S": bs}))
    for c in (0.10, 0.25, 0.35, 0.50):
        g.append(("conf %.2f (bosluk taban)" % c, {"CONF_MIN": c}))
    g.append(("kadraj=dow (gercek sinir)", {"KADRAJ_MOD": "dow"}))
    g.append(("conf .25 + bosluk 1.0 s",
              {"CONF_MIN": 0.25, "BOSLUK_KARE": 10 ** 6, "BOSLUK_S": 1.00}))
    return g


# ══════════════════════════════════════════════════════════════════════════
def main(argv=None):
    p = argparse.ArgumentParser(description="Kesintisiz kilit tezgahi")
    p.add_argument("--kaynak", default=None, help="karar_*.csv glob deseni")
    p.add_argument("--tara", action="store_true", help="odunlesim taramasi")
    p.add_argument("--dogrula", action="store_true", help="tezgah kapisi")
    p.add_argument("--kopma", action="store_true", help="kopma taksonomisi")
    p.add_argument("--gercek", action="store_true",
                   help="tanim namusluluk testi (truth ile)")
    p.add_argument("--doluluk", action="store_true",
                   help="ASIL OLCUT: kilidin ne kadari gozlemlendi")
    p.add_argument("--esik", action="store_true",
                   help="KARAR TABLOSU: esik vs angajman")
    p.add_argument("--sart", type=float, default=5.0)
    p.add_argument("--hepsi", action="store_true", help="tum raporlar")
    a = p.parse_args(argv)

    yollar = kaynaklar(a.kaynak)
    if not yollar:
        print("TAM SEMALI karar_*.csv bulunamadi (%s)" % (a.kaynak or _LOG))
        print("Gerekli kolonlar: %s" % ", ".join(GEREKLI))
        return 2
    akislar = yukle(yollar)
    if not akislar:
        print("Yeterli kareye sahip akis yok (>=50 kare).")
        return 2
    print("kaynak: %d dosya, %d akis, %d kare"
          % (len(yollar), len(akislar), sum(len(x["kare"]) for x in akislar)))
    for x in akislar:
        print("   %-36s %6d kare  %6.0f s" % (x["ad"], len(x["kare"]),
                                              x["kare"][-1]["t"] - x["kare"][0]["t"]))

    gecerli = True
    if a.dogrula or a.hepsi or not (a.tara or a.kopma):
        gecerli = r_dogrula(akislar)
    r_taban(akislar, a.sart)
    if a.kopma or a.hepsi:
        r_kopma(akislar)
    if a.tara or a.hepsi:
        r_tara(akislar, a.sart)
    if a.gercek or a.hepsi:
        r_gercek(akislar, a.sart)
    if a.doluluk or a.hepsi:
        r_doluluk(akislar, a.sart)
    if a.esik or a.hepsi:
        r_esik(akislar)
    if not gecerli:
        print("\n[!!] UYARI: tezgah kapisi GECMEDI - yukaridaki sayilar guvenilmez.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

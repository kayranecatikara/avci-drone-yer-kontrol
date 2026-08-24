# -*- coding: utf-8 -*-
"""
================================================================================
  ALGI SUREKLILIGI  --  "tespit neden surekli kopuyor?" sorusunun sayili cevabi
================================================================================
Kullanici sarti: 5 saniye KESINTISIZ kilit, sonra vurus. Kapi kodu var
(kesintisiz_kilit.py, AVCI_KILIT_S) ama algi surekliligi tasimiyor. Bu betik
HER KOPMA ANINI siniflandirir ve her kapinin sureklilige BEDELINI olcer.

IKI AYRI SAYAC VAR -- KARISTIRMA (depoda en sik yapilan hata)
--------------------------------------------------------------------------------
  [KILIT]  kesintisiz_kilit.KesintisizKilit  -> AVCI_KILIT_S 5 s kapisi
           Kare gecerli: pose VAR + conf >= AVCI_KILIT_CONF + kutu gecerli
                         + kadrajda + HAYALET DEGIL
           !! BOYUT KAPISI BU SAYACA GIRMEZ. supervisor.py:503 sayaca HAM
              `pose` besler, `gorulen` DEGIL. Yani 14 px kapisi kilidi
              KIRMAZ -- devri engeller.

  [DEVIR]  supervisor `ardisik_gor` -> sartname "10 ardisik kare" olcutu
           Kare gecerli: pose VAR + conf >= POSE_CONF_MIN + BOYUT KAPISI gecti
                         + HAYALET KAPISI gecti
           Devir icin IKISI DE gerekir: ardisik_gor>=10 VE kilit>=AVCI_KILIT_S.

KOPMA SEBEPLERI
--------------------------------------------------------------------------------
    (a) KUTU_YOK     dedektor kutu vermedi (ya da conf < predict esigi 0.25)
    (b) CONF_DUSUK   kutu var, conf < AVCI_KILIT_CONF (0.35)
    (c) BOYUT        BOYUT KAPISI eledi (max(w,h) < DEVIR_BOYUT_PX)  [yalniz DEVIR]
    (d) KADRAJ       hedef merkezi kadraj payinin disina cikti
    (e) HAYALET      w/h < HAYALET_WH_MIN, ya da bbox_ibvs kor-koprusu (kopru=1)
    (f) AKIS         kare akisi durdu / dedektor gecikti (kare araligi > AKIS_ESIK)

VERI KAYNAKLARI (hepsi MEVCUT log; canli oyuna DOKUNMAZ)
--------------------------------------------------------------------------------
  karar_*.csv       GPS FAZI, dedektorun HER karesi icin bir satir.
                    t, gorulen, conf, d_h_m (GERCEK menzil) -> MENZIL EKSENI.
                    `gorulen` kapilardan SONRAKI karardir -> (c)+(e) toplami
                    OLCUMLU; ikisinin AYRIMI menzil modeliyle kestirilir ("~").
                    !! w/h/cx_yasa/cy_yasa kolonlari 2026-08-17'de eklendi
                       (supervisor _KararLog). Varsa ayrim OLCUMLU yapilir.

  bbox_ibvs_*.csv   GORSEL FAZ: cx, cy, w, h, conf, kopru -> KUTU/KADRAJ/HAYALET
                    TAM OLCUMLU. Menzil YOK.
                    !! ORNEKLEM YANLI (survivorship): gorsel faz zaten tespit
                       calisirken var -> uzak menzil az temsil edilir.

  gps_guidance_*.csv  u_px, v_px = hedefin TRUTH'tan projekte edilmis piksel
                    konumu (guidance_core.hedef_kadraj_hatasi). "Hedef gercekten
                    kadrajda miydi?" sorusunun BAGIMSIZ cevabi.

OLCEK SABITI (geometri, tahmin DEGIL)
--------------------------------------------------------------------------------
Yasaya giden kutu, DoW pikselinin FX/fx_dow = 166.58/531.36 = 0.31350 kati
(tespit_akisi.dow_pikseli_yasaya). Canli olculen DoW sabiti
    menzil x max(w,h)_dow = 743 px*m   (n=966)
->  menzil x max(w,h)_yasa = 232.9 px*m
->  DEVIR_BOYUT_PX = 14 px (yasa) = 44.7 px (DoW) = 16.6 m MENZIL TAVANI
   (depodaki "14 px -> 22.2 m" notu ESKI 310 px*m sabitinden; duzeltildi)

CALISTIR
    python arac/algi_sureklilik.py --gun 20260817 --sonra 110000
    python arac/algi_sureklilik.py --bosluk 3 --bosluk-s 0.35
================================================================================
"""
import collections
import csv
import glob
import math
import os
import statistics as st
import sys

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LOG = os.path.join(_KOK, "kopru", "gazebo_kaynak", "logs")

# -- yasa cercevesi ve olcek (vision/geometry.py: 640x480, HFOV 125, FX=166.58)
YASA_W, YASA_H = 640.0, 480.0
YASA_FX = (YASA_W / 2.0) / math.tan(2.18166 / 2.0)               # 166.582
FX_DOW = 960.0 / math.tan(math.radians(122.0709) / 2.0)          # 531.360
OLCEK = YASA_FX / FX_DOW                                         # 0.31350
K_DOW = 743.0                  # menzil * max(w,h) DoW px*m (n=966, canli)
K_YASA = K_DOW * OLCEK         # 232.9 px*m

# DoW kadrajinin YASA cercevesindeki gercek siniri (yasa 640x480 saniyor ama
# DoW karesi daha dar bir koniye karsilik gelir -> gercek sinir BU).
DOW_U0 = 320.0 - YASA_FX * (960.0 / FX_DOW)
DOW_U1 = 320.0 + YASA_FX * (960.0 / FX_DOW)
DOW_V0 = 240.0 - YASA_FX * (540.0 / FX_DOW)
DOW_V1 = 240.0 + YASA_FX * (540.0 / FX_DOW)

# -- uretim kapilari ----------------------------------------------------------
BOYUT_PX = float(os.environ.get("AVCI_DEVIR_BOYUT", 14.0))
HAYALET_WH = float(os.environ.get("AVCI_HAYALET_WH", 1.3))
KILIT_CONF = float(os.environ.get("AVCI_KILIT_CONF", 0.35))
KADRAJ_PAY = float(os.environ.get("AVCI_KILIT_KADRAJ", 0.02))
BOSLUK_KARE = int(os.environ.get("AVCI_KILIT_BOSLUK", 3))
BOSLUK_S = float(os.environ.get("AVCI_KILIT_BOSLUK_S", 0.35))
AKIS_ESIK = 0.30               # s; bunun ustu kare araligi = akis durmasi

SEBEPLER = ["KUTU_YOK", "CONF_DUSUK", "BOYUT", "HAYALET", "KAPI~", "KADRAJ", "AKIS"]


def F(v, d=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def q(v, p):
    if not v:
        return float("nan")
    v = sorted(v)
    i = (len(v) - 1) * p
    lo = int(i)
    hi = min(lo + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (i - lo)


def yuzde(n, t):
    return (100.0 * n / t) if t else 0.0


# ==========================================================================
#  EPIZOD  (kesintisiz_kilit.py bosluk toleransinin BIREBIR uygulamasi)
# ==========================================================================
def epizotlar(kareler, bk=None, bs=None):
    """kareler: [(t, gecerli, sebep, menzil)] zaman sirali.
    Donus: (sureler[], kirilmalar[(t, sebep, menzil, sure)])"""
    bk = BOSLUK_KARE if bk is None else int(bk)
    bs = BOSLUK_S if bs is None else float(bs)
    sureler, kirilma = [], []
    t0 = son_ok = None
    bos_n = 0
    bos_sebep = None
    for t, ok, sebep, men in kareler:
        if ok:
            if t0 is None:
                t0 = t
            son_ok = t
            bos_n = 0
            bos_sebep = None
            continue
        if t0 is None:
            continue
        bos_n += 1
        if bos_sebep is None:
            bos_sebep = sebep
        if bos_n > bk or (t - son_ok) > bs:
            sureler.append(son_ok - t0)
            kirilma.append((t, bos_sebep, men, son_ok - t0))
            t0 = son_ok = None
            bos_n = 0
            bos_sebep = None
    if t0 is not None and son_ok is not None:
        sureler.append(son_ok - t0)
    return sureler, kirilma


def epizot_ozet(sureler):
    """Basari olcutu. Medyan TEK BASINA yaniltir: bir kapi kalkinca tek-kare
    (0 s) epizot sayisi patlar ve medyani asagi ceker. Bu yuzden ZAMAN
    AGIRLIKLI olcutler de verilir."""
    if not sureler:
        return {"n": 0, "med": 0.0, "p90": 0.0, "max": 0.0, "n5": 0,
                "o5": 0.0, "top": 0.0, "top5": 0.0, "zaman5": 0.0}
    top = sum(sureler)
    top5 = sum(x for x in sureler if x >= 5.0)
    n5 = sum(1 for x in sureler if x >= 5.0)
    return {"n": len(sureler), "med": st.median(sureler), "p90": q(sureler, 0.90),
            "max": max(sureler), "n5": n5, "o5": yuzde(n5, len(sureler)),
            "top": top, "top5": top5, "zaman5": yuzde(top5, top)}


def epizot_bas(ad, o, dk=None):
    ek = ("  | %.2f epizod/dk" % (o["n5"] / dk)) if (dk and dk > 0) else ""
    print("    %-30s n=%-5d med %5.2f s  p90 %5.2f s  max %6.2f s  "
          ">=5s: %d ep (%%%.2f) %%%.1f zaman%s"
          % (ad, o["n"], o["med"], o["p90"], o["max"], o["n5"], o["o5"],
             o["zaman5"], ek))


# ==========================================================================
#  KAYNAK 1: karar_*.csv   (GPS fazi -- MENZIL burada)
# ==========================================================================
def karar_oku(yollar):
    cik = []
    for y in yollar:
        try:
            with open(y, encoding="utf-8", errors="replace") as f:
                cik.append((os.path.basename(y), list(csv.DictReader(f))))
        except Exception as e:
            print("  ! okunamadi %s: %r" % (y, e))
    return cik


def _karar_kareler(satirlar, akim, bagisik=frozenset()):
    """Bir gorevin karelerini (t, ok, sebep, menzil) listesine cevir.

    akim: "KILIT"  -> kesintisiz_kilit tanimi (BOYUT kapisi YOK)
          "DEVIR"  -> supervisor `gorulen` (BOYUT + HAYALET kapisi VAR)
    bagisik: karsi-olgu; bu sebepler "gecerli" sayilir (kapi kaldirilmis gibi)
    """
    olcumlu = bool(satirlar) and "w" in satirlar[0]
    kareler = []
    onceki_t = None
    for r in satirlar:
        t = F(r.get("t"))
        if t is None:
            continue
        conf = F(r.get("conf"))
        men = F(r.get("d_h_m"))
        gorulen = (r.get("gorulen") or "").strip() == "1"
        ok, sebep = True, ""
        if conf is None:
            ok, sebep = False, "KUTU_YOK"
        elif conf < KILIT_CONF:
            ok, sebep = False, "CONF_DUSUK"
        elif akim == "DEVIR" and not gorulen:
            # kapi eledi. Hangisi? Olcumlu dosyada dogrudan; degilse menzil modeli.
            if olcumlu:
                w, h = F(r.get("w"), 0.0), F(r.get("h"), 0.0)
                if max(w, h) < BOYUT_PX:
                    ok, sebep = False, "BOYUT"
                elif h > 0 and (w / h) < HAYALET_WH:
                    ok, sebep = False, "HAYALET"
                else:
                    ok, sebep = False, "KAPI~"
            elif men and (K_YASA / men) < BOYUT_PX:
                ok, sebep = False, "BOYUT"
            else:
                ok, sebep = False, "KAPI~"     # HAYALET olmasi kuvvetle muhtemel
        if not ok and sebep in bagisik:
            ok, sebep = True, ""
        if onceki_t is not None and (t - onceki_t) > AKIS_ESIK and ok:
            if "AKIS" not in bagisik:
                ok, sebep = False, "AKIS"
        onceki_t = t
        kareler.append((t, ok, sebep, men))
    return kareler, olcumlu


def yanlis_pozitif(dosyalar, esik_px=60.0):
    """conf esigini dusurmek YANLIS POZITIF getirir mi? -- DOGRUDAN olcum.

    Yeni karar logu ayni satirda hem dedektorun kutusunu (cx_yasa/cy_yasa) hem
    hedefin TRUTH'tan projekte edilmis pikselini (u_truth/v_truth) tasir.
    |cx_yasa - u_truth| esikten kucukse tespit GERCEK, buyukse YANLIS POZITIF.

    ⚠ esik_px varsayilani 60 px (yasa cercevesinde ~20 deg): truth projeksiyonu
    Gazebo kamera modelini (HFOV 125, tilt 25) kullanir, DoW'unkini degil ->
    sistematik birkac derece sapma beklenir. Esik onu yutacak kadar genis.
    Bu yuzden sonuc "ayni yerde mi" sorusunun cevabidir, piksel dogrulugu DEGIL.
    """
    kova = collections.defaultdict(lambda: [0, 0])       # conf bandi -> [n, ok]
    sapma = []
    n_olcumlu = 0
    for _, satirlar in dosyalar:
        for r in satirlar:
            cx, ut = F(r.get("cx_yasa")), F(r.get("u_truth"))
            conf = F(r.get("conf"))
            if cx is None or ut is None or conf is None:
                continue
            n_olcumlu += 1
            d = abs(cx - ut)
            sapma.append(d)
            b = round(min(0.9, max(0.2, conf)) * 20) / 20.0   # 0.05'lik bant
            kova[b][0] += 1
            if d <= esik_px:
                kova[b][1] += 1
    return {"kova": kova, "sapma": sapma, "n": n_olcumlu, "esik": esik_px}


def karar_analiz(dosyalar, akim, bk=None, bs=None):
    sayac = collections.Counter()
    menzil_sebep = collections.defaultdict(collections.Counter)
    sureler, kirilma, dt_hepsi = [], [], []
    olcumlu_n = 0
    sure_top = 0.0
    for _, satirlar in dosyalar:
        if not satirlar:
            continue
        kareler, olcumlu = _karar_kareler(satirlar, akim)
        olcumlu_n += 1 if olcumlu else 0
        onceki = None
        for t, ok, sebep, men in kareler:
            sayac["GECERLI" if ok else sebep] += 1
            if men:
                menzil_sebep[int(men // 10) * 10]["GECERLI" if ok else sebep] += 1
            if onceki is not None:
                d = t - onceki
                if 0 < d < 5.0:
                    dt_hepsi.append(d)
            onceki = t
        if kareler:
            sure_top += kareler[-1][0] - kareler[0][0]
        s, k = epizotlar(kareler, bk, bs)
        sureler += s
        kirilma += k
    return {"sayac": sayac, "menzil_sebep": menzil_sebep, "sureler": sureler,
            "kirilma": kirilma, "dt": dt_hepsi, "olcumlu": olcumlu_n,
            "dosya": len(dosyalar), "sure_top": sure_top}


def karsi_olgu(dosyalar, akim, kurulum, bk=None, bs=None):
    cik = []
    for ad, bagisik in kurulum:
        sureler = []
        for _, satirlar in dosyalar:
            if not satirlar:
                continue
            kareler, _ = _karar_kareler(satirlar, akim, bagisik)
            s, _k = epizotlar(kareler, bk, bs)
            sureler += s
        cik.append((ad, epizot_ozet(sureler)))
    return cik


# ==========================================================================
#  KAYNAK 2: bbox_ibvs_*.csv   (gorsel faz -- KUTU/KADRAJ/HAYALET tam olcumlu)
# ==========================================================================
def ibvs_analiz(yollar, bk=None, bs=None):
    sayac = collections.Counter()
    boyut_sebep = collections.defaultdict(collections.Counter)
    sureler, kirilma = [], []
    kadraj_yon = collections.Counter()
    conf_hepsi, boyut_hepsi = [], []
    for y in yollar:
        try:
            with open(y, encoding="utf-8", errors="replace") as f:
                satirlar = list(csv.DictReader(f))
        except Exception:
            continue
        kareler = []
        for r in satirlar:
            t = F(r.get("t"))
            if t is None:
                continue
            kopru = (r.get("kopru") or "").strip() == "1"
            conf = F(r.get("conf"))
            w, h = F(r.get("w")), F(r.get("h"))
            cx, cy = F(r.get("cx")), F(r.get("cy"))
            ok, sebep = True, ""
            if kopru:
                ok, sebep = False, "KOPRU"
            elif conf is None or conf <= 0 or not w or w <= 0 or not h or h <= 0:
                ok, sebep = False, "KUTU_YOK"
            elif conf < KILIT_CONF:
                ok, sebep = False, "CONF_DUSUK"
            elif (w / h) < HAYALET_WH:
                ok, sebep = False, "HAYALET"
            elif not (KADRAJ_PAY * YASA_W <= (cx or 0) <= (1 - KADRAJ_PAY) * YASA_W
                      and KADRAJ_PAY * YASA_H <= (cy or 0) <= (1 - KADRAJ_PAY) * YASA_H):
                ok, sebep = False, "KADRAJ"
            elif max(w, h) < BOYUT_PX:
                ok, sebep = False, "BOYUT"
            if conf and conf > 0 and not kopru:
                conf_hepsi.append(conf)
            if not kopru and w and h and w > 0 and h > 0:
                boyut_hepsi.append(max(w, h))
                boyut_sebep[int(max(w, h) // 8) * 8]["GECERLI" if ok else sebep] += 1
            if sebep == "KADRAJ":
                if (cx or 0) < KADRAJ_PAY * YASA_W:
                    kadraj_yon["SOL"] += 1
                elif (cx or 0) > (1 - KADRAJ_PAY) * YASA_W:
                    kadraj_yon["SAG"] += 1
                if (cy or 0) < KADRAJ_PAY * YASA_H:
                    kadraj_yon["UST"] += 1
                elif (cy or 0) > (1 - KADRAJ_PAY) * YASA_H:
                    kadraj_yon["ALT"] += 1
            sayac["GECERLI" if ok else sebep] += 1
            kareler.append((t, ok, sebep, None))
        s, k = epizotlar(kareler, bk, bs)
        sureler += s
        kirilma += k
    return {"sayac": sayac, "boyut_sebep": boyut_sebep, "sureler": sureler,
            "kirilma": kirilma, "kadraj_yon": kadraj_yon,
            "conf": conf_hepsi, "boyut": boyut_hepsi}


# ==========================================================================
#  KAYNAK 3: gps_guidance_*.csv  -- TRUTH kadraj ("hedef gercekten kadrajda mi")
# ==========================================================================
def truth_kadraj(yollar):
    n = ici = 0
    yon = collections.Counter()
    band = collections.defaultdict(lambda: [0, 0])
    for y in yollar:
        try:
            with open(y, encoding="utf-8", errors="replace") as f:
                for r in csv.DictReader(f):
                    u, v = F(r.get("u_px")), F(r.get("v_px"))
                    m = F(r.get("menzil"))
                    n += 1
                    if m:
                        band[int(m // 10) * 10][0] += 1
                    if u is None or v is None:
                        yon["ARKA"] += 1
                        continue
                    if DOW_U0 <= u <= DOW_U1 and DOW_V0 <= v <= DOW_V1:
                        ici += 1
                        if m:
                            band[int(m // 10) * 10][1] += 1
                        continue
                    if u < DOW_U0:
                        yon["SOL"] += 1
                    elif u > DOW_U1:
                        yon["SAG"] += 1
                    if v < DOW_V0:
                        yon["UST"] += 1
                    elif v > DOW_V1:
                        yon["ALT"] += 1
        except Exception:
            continue
    return {"n": n, "ici": ici, "yon": yon, "band": band}


# ==========================================================================
def bas_sayac(baslik, sayac):
    t = sum(sayac.values())
    print("\n  %s  (n=%d kare)" % (baslik, t))
    print("    %-12s %9s %8s" % ("sebep", "kare", "oran%"))
    for k in ["GECERLI"] + SEBEPLER + ["KOPRU"]:
        if sayac.get(k):
            print("    %-12s %9d %7.1f%%" % (k, sayac[k], yuzde(sayac[k], t)))


def main(argv):
    gun, sonra, bk, bs = "20260817", None, None, None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--gun" and i + 1 < len(argv):
            gun = argv[i + 1]; i += 2; continue
        if a == "--sonra" and i + 1 < len(argv):
            sonra = argv[i + 1]; i += 2; continue
        if a == "--bosluk" and i + 1 < len(argv):
            bk = int(argv[i + 1]); i += 2; continue
        if a == "--bosluk-s" and i + 1 < len(argv):
            bs = float(argv[i + 1]); i += 2; continue
        i += 1

    def sec(onek):
        y = sorted(glob.glob(os.path.join(_LOG, "%s_%s_*.csv" % (onek, gun))))
        if sonra:
            y = [p for p in y
                 if os.path.basename(p).split("_")[-1].split(".")[0] >= sonra]
        return y

    kararlar, ibvsler, gpsler = sec("karar"), sec("bbox_ibvs"), sec("gps_guidance")

    print("=" * 78)
    print(" ALGI SUREKLILIGI -- kopma sebep taksonomisi")
    print("=" * 78)
    print(" gun=%s sonra=%s | karar %d | bbox_ibvs %d | gps_guidance %d dosya"
          % (gun, sonra or "-", len(kararlar), len(ibvsler), len(gpsler)))
    print(" kapilar: BOYUT>=%.0f px | HAYALET w/h>=%.2f | KILIT conf>=%.2f "
          "| kadraj pay %.2f | bosluk %d kare / %.2f s"
          % (BOYUT_PX, HAYALET_WH, KILIT_CONF, KADRAJ_PAY,
             BOSLUK_KARE if bk is None else bk, BOSLUK_S if bs is None else bs))
    print(" olcek: yasa_px = DoW_px x %.5f | menzil x max(w,h)_yasa = %.1f px*m"
          % (OLCEK, K_YASA))
    print(" -> BOYUT kapisi %.0f px = %.1f m MENZIL TAVANI  (devir bu menzilin"
          " otesinde YAPISAL OLARAK IMKANSIZ)" % (BOYUT_PX, K_YASA / BOYUT_PX))
    print(" -> DoW kadrajinin yasa cercevesindeki gercek siniri: "
          "u[%.0f,%.0f] v[%.0f,%.0f]" % (DOW_U0, DOW_U1, DOW_V0, DOW_V1))

    if kararlar:
        d = karar_oku(kararlar)
        for akim, baslik in (("KILIT", "kesintisiz_kilit (5 s kapisi)"),
                             ("DEVIR", "supervisor ardisik_gor (10 kare olcutu)")):
            a = karar_analiz(d, akim, bk, bs)
            print("\n" + "-" * 78)
            print(" [%s] GPS FAZI -- %s" % (akim, baslik))
            print("-" * 78)
            if akim == "DEVIR" and a["olcumlu"] < a["dosya"]:
                print("  !! w/h kolonsuz %d dosyada BOYUT/HAYALET ayrimi MENZIL"
                      % (a["dosya"] - a["olcumlu"]))
                print("     MODELIYLE yapildi; ayrilamayan kalinti 'KAPI~'.")
            bas_sayac("kare taksonomisi", a["sayac"])
            if a["dt"]:
                dt = a["dt"]
                print("\n  akis: kare araligi medyan %.3f s (%.1f fps) | p95 %.3f s"
                      " | >%.2f s %d kare (%%%.2f)"
                      % (st.median(dt), 1.0 / st.median(dt), q(dt, 0.95), AKIS_ESIK,
                         sum(1 for x in dt if x > AKIS_ESIK),
                         yuzde(sum(1 for x in dt if x > AKIS_ESIK), len(dt))))
            print("\n  EPIZOD (basari olcutu):")
            epizot_bas("MEVCUT", epizot_ozet(a["sureler"]), a["sure_top"] / 60.0)
            k = a["kirilma"]
            if k:
                c = collections.Counter(x[1] for x in k)
                print("\n  KIRAN SEBEP (epizodu bitiren ILK gecersiz kare), n=%d:" % len(k))
                for kk, vv in c.most_common():
                    print("    %-12s %7d  %6.1f%%" % (kk, vv, yuzde(vv, len(k))))
                mm = [x[2] for x in k if x[2]]
                if mm:
                    print("\n  KIRILMA MENZILI: medyan %.1f m | p10 %.1f | p90 %.1f"
                          % (st.median(mm), q(mm, 0.10), q(mm, 0.90)))
                    b = collections.Counter(int(x // 10) * 10 for x in mm)
                    for bb in sorted(b):
                        print("    %3d-%3d m  %6d  %5.1f%%"
                              % (bb, bb + 10, b[bb], yuzde(b[bb], len(mm))))
            ms = a["menzil_sebep"]
            if ms:
                print("\n  MENZILE GORE KARE TAKSONOMISI:")
                bas = ["GECERLI", "KUTU_YOK", "CONF_DUSUK", "BOYUT", "KAPI~"]
                print("    %-10s %7s %s" % ("menzil", "kare",
                                            " ".join("%9s" % x for x in bas)))
                for bb in sorted(ms):
                    c = ms[bb]
                    n = sum(c.values())
                    if n < 50:
                        continue
                    print("    %3d-%3d m  %7d %s"
                          % (bb, bb + 10, n,
                             " ".join("%8.1f%%" % yuzde(c[x], n) for x in bas)))

        # -- conf esigi vs YANLIS POZITIF (truth ile DOGRUDAN) -------------
        yp = yanlis_pozitif(d)
        print("\n" + "-" * 78)
        print(" [CONF x YANLIS POZITIF] dedektor kutusu TRUTH ile ayni yerde mi")
        print("-" * 78)
        if yp["n"] == 0:
            print("  OLCULMEDI — karar logunda cx_yasa/u_truth kolonlari YOK.")
            print("  Bu kolonlar 2026-08-17'de eklendi; sonraki kosuda dolar.")
            print("  O zamana kadar dolayli kanit: dusuk-conf kareler uzak")
            print("  menzilde yogun ve TRUTH o menzillerde hedefin karelerin")
            print("  %90-93'unde kadrajda oldugunu soyluyor -> cogunlugu GERCEK.")
        else:
            print("  n=%d kare | sapma |cx-u_truth|: medyan %.1f px | p90 %.1f px"
                  " | esik %.0f px"
                  % (yp["n"], st.median(yp["sapma"]), q(yp["sapma"], 0.90),
                     yp["esik"]))
            print("    %-10s %8s %10s %10s" % ("conf", "kare", "TRUTH ile", "eslesme%"))
            for b in sorted(yp["kova"]):
                n2, ok2 = yp["kova"][b]
                if n2 < 20:
                    continue
                print("    %.2f-%.2f %8d %10d %9.1f%%"
                      % (b, b + 0.05, n2, ok2, yuzde(ok2, n2)))
            print("  -> Esigi 0.35'ten 0.25'e cekmenin bedeli: 0.25-0.35 bandinin")
            print("     eslesme orani ile 0.35+ bandinin eslesme orani FARKI.")

        # -- karsi-olgu: her kapinin sureklilige BEDELI --------------------
        print("\n" + "-" * 78)
        print(" [KARSI-OLGU] kapilari TEK TEK kaldirinca epizod ne olur")
        print("-" * 78)
        print("  !! SIMULASYON: kutu zaten kayitta, kapiyi kaldirmak dedektoru")
        print("     degistirmez -> gercekci kestirim. Ama guduumun o kutuyla ne")
        print("     yapacagini SOYLEMEZ (yanlis pozitif riski ayri olculmeli).")
        print("\n  -- KILIT akimi (5 s kapisini besleyen sayac) --")
        for ad, o in karsi_olgu(d, "KILIT", [
                ("MEVCUT (conf>=0.35)", frozenset()),
                ("conf esigi 0.35 -> 0.25", frozenset({"CONF_DUSUK"})),
                ("+ akis boslugu bagisik", frozenset({"CONF_DUSUK", "AKIS"}))],
                bk, bs):
            epizot_bas(ad, o)
        print("\n  -- DEVIR akimi (10 ardisik kare olcutu) --")
        for ad, o in karsi_olgu(d, "DEVIR", [
                ("MEVCUT (tum kapilar)", frozenset()),
                ("-BOYUT kapisi", frozenset({"BOYUT"})),
                ("-HAYALET/kalinti kapisi", frozenset({"KAPI~", "HAYALET"})),
                ("-BOYUT -HAYALET", frozenset({"BOYUT", "KAPI~", "HAYALET"})),
                ("-BOYUT -HAYALET -CONF", frozenset({"BOYUT", "KAPI~", "HAYALET",
                                                     "CONF_DUSUK"}))], bk, bs):
            epizot_bas(ad, o)

        # -- bosluk toleransi taramasi ------------------------------------
        print("\n  -- BOSLUK TOLERANSI taramasi (KILIT akimi, conf>=0.35) --")
        print("     !! SURE TAVANI kare sayisiyla birlikte buyur "
              "(n+1 kare @ olculen 20 fps). Tavan kaldirilirsa epizod GORSEL")
        print("     FAZIN uzerinden atlar (karar logu o sirada satir yazmaz) ve")
        print("     max 190+ s gibi FIZIKSEL OLMAYAN degerler cikar.")
        for n_bos in (0, 1, 3, 5, 8, 12, 20):
            tavan = max(0.10, (n_bos + 1) * 0.06)
            sureler = []
            for _, satirlar in d:
                kareler, _ = _karar_kareler(satirlar, "KILIT")
                s, _k = epizotlar(kareler, n_bos, tavan)
                sureler += s
            epizot_bas("bosluk <= %2d kare / %.2f s" % (n_bos, tavan),
                       epizot_ozet(sureler))

    if ibvsler:
        b = ibvs_analiz(ibvsler, bk, bs)
        print("\n" + "-" * 78)
        print(" [GORSEL FAZ] bbox_ibvs -- kutu/kadraj/hayalet TAM olcumlu")
        print("-" * 78)
        print("  !! ORNEKLEM YANLI (survivorship): uzak menzil az temsil edilir")
        print("     -> BOYUT/HAYALET oranlari ALT SINIR.")
        bas_sayac("kare taksonomisi", b["sayac"])
        print("\n  EPIZOD:")
        epizot_bas("MEVCUT", epizot_ozet(b["sureler"]))
        k = b["kirilma"]
        if k:
            c = collections.Counter(x[1] for x in k)
            print("\n  KIRAN SEBEP, n=%d:" % len(k))
            for kk, vv in c.most_common():
                print("    %-12s %7d  %6.1f%%" % (kk, vv, yuzde(vv, len(k))))
        bo = b["boyut"]
        if bo:
            print("\n  KUTU max(w,h) yasa px: medyan %.1f (=%.1f m) | p10 %.1f "
                  "| p90 %.1f" % (st.median(bo), K_YASA / st.median(bo),
                                  q(bo, 0.10), q(bo, 0.90)))
            for th in (10, 14, 18, 25, 32):
                print("    max(w,h) < %2d px : %%%.1f  (menzil > %.1f m)"
                      % (th, yuzde(sum(1 for x in bo if x < th), len(bo)),
                         K_YASA / th))
        bs2 = b["boyut_sebep"]
        if bs2:
            print("\n  HAYALET KAPISININ (w/h<%.2f) BOYUTA GORE ELEME ORANI" % HAYALET_WH)
            print("  Kapi 'kare leke = sahte' varsayimiyla kondu ve buyuk kutuda")
            print("  olculdu (%%4.3). Kucuk kutuda en-boy orani kuantalanma")
            print("  yuzunden 1'e yaklasir -> GERCEK hedef eleniyor mu? BAK:")
            print("    %-12s %8s %9s %8s %10s"
                  % ("max(w,h)", "kare", "HAYALET", "oran%", "~menzil m"))
            for bb in sorted(bs2):
                c = bs2[bb]
                n = sum(c.values())
                if n < 30:
                    continue
                print("    %3d-%3d px  %8d %9d %7.1f%%  %5.1f-%5.1f"
                      % (bb, bb + 8, n, c["HAYALET"], yuzde(c["HAYALET"], n),
                         K_YASA / (bb + 8), K_YASA / max(bb, 1)))
        ky = b["kadraj_yon"]
        print("\n  KADRAJ KAYBI (yasa 640x480 payina gore): %s"
              % (", ".join("%s %d" % (k2, v2) for k2, v2 in ky.most_common())
                 if ky else "0 kare -- kapi HIC atesLENMIYOR"))
        if not ky:
            print("     SEBEP: kadraj kapisi 640x480'i tam saniyor, ama DoW karesi")
            print("     yasa cercevesinde yalniz u[%.0f,%.0f] v[%.0f,%.0f] kaplar"
                  % (DOW_U0, DOW_U1, DOW_V0, DOW_V1))
            print("     -> gercek tespit MATEMATIKSEL OLARAK bu payin disina cikamaz.")
        cf = b["conf"]
        if cf:
            print("\n  CONF (gercek kutulu kare, n=%d): medyan %.3f | p05 %.3f "
                  "| min %.3f" % (len(cf), st.median(cf), q(cf, 0.05), min(cf)))
            for th in (0.30, 0.35, 0.40, 0.50):
                print("    conf < %.2f : %%%.2f"
                      % (th, yuzde(sum(1 for x in cf if x < th), len(cf))))

    if gpsler:
        t = truth_kadraj(gpsler)
        print("\n" + "-" * 78)
        print(" [TRUTH KADRAJ] gps_guidance u_px/v_px -- hedef GERCEKTEN kadrajda miydi")
        print("-" * 78)
        print("  kare %d | DoW kadrajinda %%%.1f" % (t["n"], yuzde(t["ici"], t["n"])))
        ty = sum(t["yon"].values())
        print("  kadraj DISI %d olay:" % ty)
        for k, v in t["yon"].most_common():
            print("    %-6s %6d  %5.1f%%" % (k, v, yuzde(v, ty)))
        print("\n  %-10s %8s %10s" % ("menzil", "kare", "kadrajda%"))
        for bb in sorted(t["band"]):
            a2, c2 = t["band"][bb]
            if a2 < 50:
                continue
            print("  %3d-%3d m %8d %9.1f%%" % (bb, bb + 10, a2, yuzde(c2, a2)))

    print("\n" + "=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

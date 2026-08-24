# -*- coding: utf-8 -*-
"""
================================================================================
  SIM_DEVIR  --  DEVIR (handoff) POLITIKASI TEZGAHI
================================================================================
SORU: GPS fazindan gorsel faza NE ZAMAN devretmeli?

Mevcut olcut: 10 ARDISIK tespit + kutu >= 14 px (supervisor.DEVIR_BOYUT_PX).
Kutu boyutu supheli bir olcut: 15 px'te gurultu baskin ve SAHADA olculdu ki
devir kutusu ile faz omru arasindaki korelasyon rho = +0.098, yani YOK.

⚠ BU BETIK HICBIR CANLI DOSYAYI DEGISTIRMEZ.
   sim/tesis.py, sim/deney.py ve kopru/ altindaki yasa/supervisor SALT OKUNUR.
   Tesis (Avci/Hedef/kadraj/Algi) ve gercek yasa (bbox_ibvs.komut) import
   edilir; devir politikasi BURADA modellenir.

⚠⚠ OLCUM HATASI ACIK KOSULUR (T.HataAyari varsayilani).
   Kapali simulator 16 Agustos sabahi YANLIS KAZANAN sectI (PN'i). Sebep
   sim/tesis.py:349-372'de yaziyor. Burada hata varsayilan olarak ACIK ve
   `--hatasiz` bilerek ayri bir kontrol kosusu olarak birakildi.

--------------------------------------------------------------------------------
 TESISE EKLENEN TEK SEY: SAHA-KALIBRE TESPIT KAYBI  (SahaAlgi)
--------------------------------------------------------------------------------
tesis.tespit_olasilik() kutu boyutuna bagli BAGIMSIZ yazi-tura atar. Sahada
kayip BOYLE DAVRANMIYOR: kayiplar KUMELI ve |eps| (kadraj ici aci) ile
patliyor. Kanit -- 283 gorsel faz, bbox_ibvs_20260816_1[6-7]*.csv, ardisik
kare gecisleri sayilarak (kare basina kayip olasiligi):

    |eps|  0-10   0.044 (n=2163)     30-40  0.663 (n=166)
          10-20   0.113 (n=1002)     40-50  0.631 (n= 84)
          20-30   0.383 (n= 545)     50-60  0.750 (n= 80)
                                     60-70  0.840 (n= 25)

Kutu boyutu ETKISI CIKARILDI (iki boyutlu tablo, |eps|<15 satiri):
    kutu  8-16 px -> 0.09 (n=1090)      kutu 16-24 px -> 0.03 (n=1613)
yani boyut 3 kat oynatiyor, |eps| 19 kat. ⚠ Boyutun marjinal tablosundaki
U seklindeki egri (5-10 px 0.39, 15-20 px 0.08, 30-35 px 0.57) SAHTE bir
etki: buyuk kutu = yakin menzil = |eps| hizli suruklendigi rejim.

Kayiptan DONUS olculdu: p(bulus|kayip) = 0.050 / yasa tiki (duz ortalama).
Yasa dongusu 33.3 Hz (bugunun logunda dt p50 0.030 s; DURUM'daki 21.3 Hz
15 Agustos'un FPS cokusune ait, bugun 53 FPS'e donuldu).

--------------------------------------------------------------------------------
 KALIBRASYON HEDEFLERI (hepsi bugun sahada olculdu, 283 faz)
--------------------------------------------------------------------------------
    faz omru       p10 0.78  p50 1.22  p90 1.86 s   (ort 1.29)
    devir kutusu   p50 15.8 px  -> R*max(w,h)=310 ile  R p50 19.6 m
    devir |eps|    p50  3 deg          olum |eps| p50 33 deg
    kutulu kare orani (faz ici) 0.33
    devirler arasi BOSLUK p50 6.6 s    (⚠ gorevdeki 27 s ESKI konfigurasyon;
                                        bugun 14 px kapisi + istasyon 9 m ile
                                        6.6 s olculdu -> gorsel faz nobeti
                                        %6 degil ~%16)
    en yakin gecis (S9_eski, 18 faz)  medyan 12.73 m

--------------------------------------------------------------------------------
 ⚠⚠ TEZGAHIN NEREYE GUVENILIR, NEREYE GUVENILMEZ  (kalibrasyon hukmu)
--------------------------------------------------------------------------------
GUVENILIR -- devir durumundan gorsel fazin SONUCU (gorsel_angajman):
    SAHA devir durumundan (15.7 m, aspect 17, 1.5 m alt, 21.6 m/s) kosulunca
        omur p10/p50/p90  0.94 / 1.45 / 2.19 s   SAHA 0.78 / 1.22 / 1.86
        faz ici kutulu kare orani  0.35          SAHA 0.33
        en yakin gecis             10.8 m        SAHA 12.73 m
        vurus                      0/40          SAHA yok
    Dort bagimsiz olcut, tek kalibre sayiyla (asagi). Politika kiyaslari
    BU parca uzerine kuruludur.

GUVENILMEZ -- gorev() dongusunun GPS FAZI:
    Tesisteki arac istasyona VARIYOR (9 m), sahadaki VARAMIYOR: komut hizi
    22.0'de doymus, GERCEKLESEN 16.1 m/s, hedef 18.2 -> kapanma +0.32 m/s.
    Bu yuzden devir SIKLIGI ve devir DURUMU dagilimi tesisten DEGIL, gercek
    gps_guidance loglarindan alinir (saha_akisi / saha_kiyas).
    ⚠ Mutlak devir sikligi da modelden gelmez: MEVCUT politika sahanin
    olculen 8.4 devir/dk'sina SABITLENIR, digerleri ayni carpanla olceklenir.

KALIBRE EDILEN SAYILAR (ikisi de OLCULEN bir acigi kapatir, mekanizma DEGIL):
    SURUKLEME_EK = 18 deg/s -- kadraj ici suruklenme acigi (saha 22, tezgah 4)
    V_GPS_ETKIN  = 19 m/s   -- yalniz gorev() dongusunde; ana sonuclar kullanmaz
Her politika kiyasi SURUKLEME_EK ACIK ve KAPALI kosulur; siralamanin ayni
kalmasi, sonucun kalibrasyona dayanmadiginin kanitidir (2026-08-16 sabahi
tezgah tam bu sinamayi yapmadigi icin yanlis kazanan secmisti).

CALISTIR
    python arac/sim_devir.py --kalibre      tezgah sahayi yeniden uretiyor mu
    python arac/sim_devir.py --politika     politika kiyas tablosu (2 kalibrasyon)
    python arac/sim_devir.py --supurme      esik taramalari (1,2,3,4)
    python arac/sim_devir.py --pencere      devir kosulu -> sonuc iliskisi
    python arac/sim_devir.py --tekrar       devir arasi bosluk / KAYIP_M analizi
    python arac/sim_devir.py --yuzey        (menzil x aspect) sonuc yuzeyi
================================================================================
"""
import os
import sys
import math
import random
import argparse
import statistics as st

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "kopru", "gazebo_kaynak"))
sys.path.insert(0, os.path.join(KOK, "sim"))

# ── SAHANIN KALICI AYARI (DURUM_2026-08-16.md §17) ────────────────────────
# Cfg env'i SINIF KURULURKEN okur -> import'tan ONCE yazilmali.
os.environ.setdefault("AVCI_IBVS_KAPANMA", "0")      # kutudan kapanma KAPALI
os.environ.setdefault("AVCI_IBVS_YAW_HIZALA", "0.12")
os.environ.setdefault("AVCI_IBVS_VMAX", "24.0")
os.environ.setdefault("AVCI_MAX_ACCEL", "12.0")
os.environ.setdefault("AVCI_VZ_MAX_GORSEL", "3.0")
os.environ.setdefault("AVCI_IBVS_PN", "1.6")

import tesis as T                                              # noqa: E402
from tesis import Avci, Hedef, Olcum, kadraj, F_YASA, HataAyari, Algi  # noqa: E402
from control.guidance import bbox_ibvs as IB                   # noqa: E402


# ══════════════════════════════════════════════════════════════════════════
#  SAHA SABITLERI  (hepsi olculdu -- provenance yukaridaki bas yorumda)
# ══════════════════════════════════════════════════════════════════════════
class Saha:
    # kayip tehlikesi: (|eps| bandi ortasi derece, kare basina kayip olasiligi)
    TEHLIKE = [(5.0, 0.044), (15.0, 0.113), (25.0, 0.383), (35.0, 0.663),
               (45.0, 0.631), (55.0, 0.750), (65.0, 0.840)]
    BULUS_P = 0.050          # p(bulus|kayip) / tik  (GORSEL faz icinde olculdu)
    TEHLIKE_ORT = 0.163      # ayni populasyonun ORTALAMA kayip tehlikesi
    OLCUM_HZ = 33.3          # tehlike tablosunun olculdugu tik hizi
    # ⚠ Tehlike tablosunun kutu-tabani SAHANIN devir kutusu (15.8 px @ 15.7 m,
    # yani R*max(w,h) = 248 px·m). Tesisin kadraj()'i AYNI menzilde 18.9 px
    # veriyor (kanat 1.78 m, F 166.6 -> 296 px·m). Boyut carpanini saha
    # px'ine gore anchor'lamak %19'luk SAHTE bir "daha iyi tespit" uretirdi;
    # bu yuzden referans TESISIN ayni menzildeki kutusudur.
    BOYUT_REF_PX = 18.9      # px; tesis kadraji @ saha devir menzili (15.7 m)
    BOYUT_OLCEK = 7.28       # px; f(b)=exp((REF-b)/OLCEK), 8 px'te 3 kat
    BOYUT_F_MIN, BOYUT_F_MAX = 0.5, 5.0
    YASA_HZ = 33.3           # bugunku olculen yasa dongusu (dt p50 0.030 s)

    # kalibrasyon hedefleri
    OMUR_P50 = 1.22
    OMUR_P90 = 1.86
    DEVIR_KUTU_P50 = 15.8
    DEVIR_MENZIL_P50 = 19.6
    KUTULU_ORAN = 0.33
    BOSLUK_P50 = 6.6
    DEVIR_DK = 8.4          # devir/dk (329 segment / 7.2 s cevrim)
    ISKA_P50 = 12.73         # S9_eski, 18 faz
    # ── GPS FAZI (gps_guidance_20260816_1[6-7]*.csv, 329 segment) ─────────
    # ⚠ EN ONEMLI SAHA GERCEGI: ISTASYONA HIC VARILMIYOR. Komut 9 m,
    # olculen segment MIN menzili 14.3 m. Sebep de olculdu:
    #     komut hizi   p50 22.0  p90 22.0 m/s   (DOYMUS -- hep tam gaz)
    #     GERCEKLESEN  p50 16.1 m/s             (konum turevinden)
    #     hedef hizi   p50 18.2 m/s
    #     kapanma      p50 +0.32 m/s            (fiilen SIFIR)
    # Yani arac GPS fazinda hedeften YAVAS. Tesis bunu kendiliginden
    # uretemez (komutu birebir gerceklestirir) -> V_GPS_ETKIN ile kalibre
    # edilir. ⚠ BU TEK AYARLANAN SAYIDIR; asagidaki 5 bagimsiz ciktinin
    # hepsi onunla dogrulanir.
    SEG_BAS_P50 = 16.2       # m; gorsel faz oldugunde kalinan menzil
    SEG_MIN_P50 = 14.3       # m; GPS segmentinde ulasilan EN YAKIN menzil
    SEG_SON_P50 = 15.8       # m; DEVIR anindaki menzil (dogrudan olcum)
    SEG_SURE_P50 = 7.0       # s; GPS segment suresi (= devirler arasi bosluk)
    AVCI_HIZ_GPS = 16.1      # m/s; GPS fazinda GERCEKLESEN hiz p50
    # ── KADRAJ ICI SURUKLENME (faz omrunun ASIL belirleyicisi) ───────────
    # SAHA (1881..186 kare, devir anindan itibaren 0.25 s kovalari):
    #   |eps_ham| p50  0.12s->5.9  0.37->8.9  0.62->13.8  0.87->20.6  1.12->26.0
    #   => ~22 deg/s DUZGUN surukleme; hedef kadrajdan YURUYEREK cikiyor.
    # TEZGAH ayni durumda 2-5 deg/s veriyor: tesisin yasa+arac cevrimi hedefi
    # merkezde TUTABILIYOR. Yaw slew'i 120 -> 12 deg/s'ye kismak bile bunu
    # uretmedi (surukleme 2.5 -> 4.6), yani sebep tesisin MODELLEDIGI hicbir
    # kanalda degil.
    # ⚠⚠ SURUKLEME_EK BU YUZDEN MEKANIZMA DEGIL, OLCULEN ACIGIN KAPATILMASIDIR.
    # Yalnizca TEHLIKE hesabina girer (yasanin gordugu kutuya DOKUNMAZ), yani
    # "faz ne kadar yasar" sorusunu sahaya oturtur, guduumu bozmaz.
    # Politika siralamasi bu sayiya DAYANMAMALI: --politika hem 0 hem kalibre
    # degerle kosulur ve iki siralama raporda KARSILASTIRILIR.
    SURUKLEME_SAHA = 22.0    # deg/s (olculdu)
    # istasyon mesafesi -> iska medyani (DURUM §17)
    ISTASYON_EGRISI = {22.7: 19.54, 18.0: 18.73, 13.0: 15.62,
                       9.0: 12.73, 7.0: 13.60, 5.0: 13.75}


def _tehlike_p(eps_deg, boyut_px):
    """Kare basina kayip olasiligi: h(|eps|) * f(kutu). Tablodan interpolasyon."""
    e = abs(eps_deg)
    tab = Saha.TEHLIKE
    if e <= tab[0][0]:
        h = tab[0][1]
    elif e >= tab[-1][0]:
        h = tab[-1][1]
    else:
        h = tab[-1][1]
        for i in range(len(tab) - 1):
            x0, y0 = tab[i]
            x1, y1 = tab[i + 1]
            if x0 <= e <= x1:
                h = y0 + (y1 - y0) * (e - x0) / (x1 - x0)
                break
    f = math.exp((Saha.BOYUT_REF_PX - max(boyut_px, 1.0)) / Saha.BOYUT_OLCEK)
    f = max(Saha.BOYUT_F_MIN, min(Saha.BOYUT_F_MAX, f))
    return max(0.0, min(0.98, h * f))


def _bulus_p(eps_deg, boyut_px):
    """Kayiptan DONUS olasiligi / tik.

    ⚠ OLCULEN 0.050 degeri bbox_ibvs satirlarindan, yani YALNIZ GORSEL FAZ
    icinden geliyor -- hedefin zaten kadraj kenarina suruklendigi rejim.
    Ayni sabiti GPS fazinda (hedef nisanda, 15 m) kullanmak dedektoru
    haksiz yere kotu gosterir ve devir sikligini 15 KAT dusuruyordu.
    Bu yuzden donus, KAYBIN AYNASI olarak modellenir:
        p_bulus = 0.050 * h_ort / h(eps, kutu)
    h_ort = 0.163 -- 0.050'nin olculdugu populasyonun ORTALAMA tehlikesi
    (|eps| dagilimiyla agirliklandirilmis; bkz. bas yorumdaki tablo).
    Boylece nisandaki hedef hizli, kenardaki hedef yavas bulunur ve
    olculen nokta AYNEN korunur.
    """
    h = _tehlike_p(eps_deg, boyut_px)
    return max(0.005, min(0.60, Saha.BULUS_P * Saha.TEHLIKE_ORT / max(h, 1e-6)))


def _oran_cevir(p, dt):
    """Tik olasiligini surekli tehlike hizina cevirip dt'ye tasir."""
    if p <= 0.0:
        return 0.0
    if p >= 1.0:
        return 1.0
    lam = -math.log(1.0 - p) * Saha.OLCUM_HZ
    return 1.0 - math.exp(-lam * dt)


class SahaAlgi(Algi):
    """tesis.Algi + SAHA-KALIBRE, |eps| suruclu KUMELI tespit kaybi.

    ⚠ Tesisin kendi tespit_kaybi'ni KAPATIR (cift sayim olmasin) ve yerine
    iki durumlu Markov zinciri koyar. Diger butun hata kaynaklari (donuk yaw,
    kutu gecikmesi, kenar yanliligi, yanlis nesne, jitter, dongu hizi) TESISTEN
    aynen gelir -- onlara DOKUNULMAZ.
    """

    def __init__(self, ayar=None, tohum=0, saha_kayip=True, gorunur=False,
                 surukleme_ek=0.0):
        ayar = HataAyari() if ayar is None else ayar
        self.saha_kayip = saha_kayip
        if saha_kayip:
            ayar.tespit_kaybi = False       # kayip bu sinifta uretilecek
        Algi.__init__(self, ayar, tohum=tohum)
        # ⚠ DEVIR ANINDA HEDEF GORULUYOR (kapi 10 ardisik tespit istiyor).
        # gorunur=False ile baslatmak fazi daha dogmadan olduruyordu.
        self.gorunur = gorunur
        self._kare_t = None
        self.eps_gercek = 0.0               # tani: gercek |eps| (derece)
        # ⚠ FENOMENOLOJIK: olculen kadraj-ici suruklenme acigi (bkz.
        # Saha.SURUKLEME_SAHA). Yalniz TEHLIKE hesabina girer.
        self.surukleme_ek = surukleme_ek
        self.faz_t0 = None

    def kare_ver(self, t, avci, k):
        if not self.saha_kayip:
            return Algi.kare_ver(self, t, avci, k)
        a = self.a
        # tesisin kamera ornekleme kapisi ile AYNI kosul (yeni kare mi?)
        yeni = (a.kamera_hz <= 0.0
                or t - self._son_kare >= (1.0 / a.kamera_hz) - 1e-9)
        if yeni:
            dtk = (1.0 / max(a.kamera_hz, 1e-6) if self._kare_t is None
                   else max(t - self._kare_t, 1e-6))
            self._kare_t = t
            if k is None:
                self.gorunur = False        # kadraj DISINDA -> kesin kayip
                self.eps_gercek = 90.0
            else:
                eps = math.degrees(math.atan((k[0] - T.CX) / F_YASA))
                self.eps_gercek = abs(eps)
                if self.surukleme_ek > 0.0 and self.faz_t0 is not None:
                    eps = abs(eps) + self.surukleme_ek * max(t - self.faz_t0, 0.0)
                b = max(k[2], k[3])
                if self.gorunur:
                    if self.rnd.random() < _oran_cevir(_tehlike_p(eps, b), dtk):
                        self.gorunur = False
                else:
                    if self.rnd.random() < _oran_cevir(_bulus_p(eps, b), dtk):
                        self.gorunur = True
        return Algi.kare_ver(self, t, avci, (k if self.gorunur else None))


# ══════════════════════════════════════════════════════════════════════════
#  DEVIR POLITIKALARI
# ══════════════════════════════════════════════════════════════════════════
# ⚠ YARISMA KURALI: devir OLCUTU GPS fazinda degerlendirilir; hedef GPS'i
# orada SERBEST (gps_guidance.py:722 ayni gerekceyi yaziyor). Yasak olan,
# GORSEL FAZ boyunca hedef GPS'inden guduum uretmek. Asagidaki politikalarin
# hicbiri gorsel faza GPS tasimaz -- yalnizca ANI secerler.
class Politika:
    """Devir kapisi. Hepsi ARDISIK TESPIT sartini korur (sartname).

    kare_n     : ardisik tespitli kare (sartname 10)
    boyut_px   : max(w,h) esigi -- 0 = KAPALI  (mevcut 14)
    aspect_max : hedef kuyruk konisi acisi tavani (derece) -- None = KAPALI
    tgo_max    : tahmini kapanma suresi tavani (s) = R/Vc -- None = KAPALI
    lam_max    : |LOS azimut hizi| tavani (deg/s) -- None = KAPALI
    lam_kaynak : "truth" (GPS fazi telemetrisi) | "yasa" (kirli piksel+yaw)
    donus_max  : hedefin kendi donus hizi tavani (deg/s) -- None = KAPALI
    """

    def __init__(self, ad, kare_n=10, boyut_px=14.0, aspect_max=None,
                 tgo_max=None, lam_max=None, lam_kaynak="truth",
                 donus_max=None, menzil_max=None):
        self.ad = ad
        self.kare_n = kare_n
        self.boyut_px = boyut_px
        self.aspect_max = aspect_max
        self.tgo_max = tgo_max
        self.lam_max = lam_max
        self.lam_kaynak = lam_kaynak
        self.donus_max = donus_max
        self.menzil_max = menzil_max
        self.ardisik = 0

    def sifirla(self):
        self.ardisik = 0

    def degerlendir(self, g):
        """g: gozlem sozlugu. Doner: True = DEVRET."""
        # 1) SARTNAME: ardisik tespitli kare (+ varsa boyut kapisi)
        sayilir = g["gorulen"]
        if sayilir and self.boyut_px > 0.0 and g["kutu"] < self.boyut_px:
            sayilir = False                 # supervisor.py:405-415 ile ayni
        self.ardisik = (self.ardisik + 1) if sayilir else 0
        if self.ardisik < self.kare_n:
            return False
        # 2) EK KAPILAR (hepsi GPS fazi bilgisi)
        if self.aspect_max is not None and g["aspect"] > self.aspect_max:
            return False
        if self.tgo_max is not None:
            vc = g["kapanma"]
            tgo = g["menzil"] / vc if vc > 0.2 else 1e9
            if tgo > self.tgo_max:
                return False
        if self.lam_max is not None:
            lam = g["lam_truth"] if self.lam_kaynak == "truth" else g["lam_yasa"]
            if abs(lam) > self.lam_max:
                return False
        if self.donus_max is not None and abs(g["hedef_donus"]) > self.donus_max:
            return False
        if self.menzil_max is not None and g["menzil"] > self.menzil_max:
            return False
        return True


# ══════════════════════════════════════════════════════════════════════════
#  GOREV DONGUSU  --  GPS istasyon -> devir -> gorsel faz -> olum -> GPS ...
# ══════════════════════════════════════════════════════════════════════════
V_GPS_MAX = 22.0        # ana_kontrol.KOPRU_V_MAX (onaylanmis tek istisna)
# ⚠ TEK KALIBRE EDILEN SAYI. Sahada komut 22.0 m/s'de DOYMUS ama gerceklesen
# hiz p50 16.1 m/s (hedef 18.2). Tesis komutu birebir gerceklestirdigi icin
# bu kaybi kendiliginden uretemez; GPS fazinin ETKIN hiz tavani buraya konur.
# Deger --kalibre taramasi ile secildi: segment MIN/SON menzilini ve segment
# suresini AYNI ANDA tutturan tek deger. Ham olcum 16.1'in ustunde cikmasi
# beklenir cunku tesis daha temiz bir yorunge uçuyor (donuste kayip yok).
V_GPS_ETKIN = float(os.environ.get("SIMDEVIR_VGPS", 19.0))
# ⚠⚠ IKINCI (VE ASIL) KALIBRE EDILEN SAYI: ARACIN ETKIN YAW SLEW HIZI.
# tesis.Avci yaw'i cfg.YAW_RATE_MAX_DEG=120 deg/s ile ANINDA cevirir; sahada
# burun komutu KOVALAYAMIYOR ve hedef kadrajdan disari YURUYOR:
#     |eps_ham| p50: t=0.12 s -> 5.9 | t=0.50 -> 13.8 | t=1.0 -> 26.0 deg
#         => kadraj ici surukleme ~22 deg/s        (n=1881..186 kare)
#     |yaw_cmd - iris_yaw| p50: 3.8 -> 8.6 -> 14.6 -> 19.4 deg (t=0..0.75 s)
#         => yasa DONMESINI SOYLUYOR, arac DONMUYOR (komut hatasi 21 deg/s buyuyor)
#     yaw hizi (sifir olmayan adimlar) p50 21.3 p90 57.7 deg/s
# Sebep depoda kesin degil (DoW cubuk esleme / kopru onceligi). ETKISI olculdu;
# tezgaha ETKI olarak konur. Bu, faz omrunu belirleyen TEK BUYUK degiskendir.
YAW_RATE_ETKIN = float(os.environ.get("SIMDEVIR_YAWRATE", 120.0))
# ⚠ FENOMENOLOJIK KAPATMA (bkz. Saha.SURUKLEME_SAHA): tezgahin kendi
# suruklenmesi 2-5 deg/s, saha 22 deg/s. Fark buradan eklenir ve YALNIZ
# tehlike hesabina girer. 0.0 = kapali (yalniz mekanizma).
SURUKLEME_EK = float(os.environ.get("SIMDEVIR_SURUKLEME", 18.0))
K_IST = 0.8             # istasyon P kazanci (1/s)
K_IST_Z = 0.8
KAYIP_M = 20            # supervisor.SupCfg.KAYIP_M


def _aspect_deg(ax, ay, hx, hy, hvx, hvy):
    """gps_guidance.py:740-746 ile AYNI tanim. 0 = tam kuyruk takibi."""
    ex, ey = hx - ax, hy - ay
    lr = math.hypot(ex, ey)
    vh = math.hypot(hvx, hvy)
    if lr < 0.1 or vh < 0.1:
        return 0.0
    lx, ly = ex / lr, ey / lr
    vpar = hvx * lx + hvy * ly
    vdik = abs(hvx * ly - hvy * lx)
    return math.degrees(math.atan2(vdik, vpar))


def gorev(pol, sure=240.0, tohum=0, faz0=0.0, istasyon=9.0, elev=10.0,
          dt=1.0 / 62.0, cfg=IB.Cfg, hata=None, saha_kayip=True,
          kayip_m=KAYIP_M, hedef_yon=+1, v_gps=None):
    """Tek gorev: politika ile GPS<->GORSEL dongusu, `sure` saniye.

    Doner: {"faz": [faz kayitlari], "gps_s": ..., "gorsel_s": ...}
    """
    if hata is None:
        hata = HataAyari()                       # ⚠ GERCEKCI (hata ACIK)
    hata.yasa_hz = Saha.YASA_HZ
    hata.kamera_hz = Saha.YASA_HZ
    v_gps = V_GPS_ETKIN if v_gps is None else v_gps
    algi = SahaAlgi(hata, tohum=tohum, saha_kayip=saha_kayip,
                    surukleme_ek=SURUKLEME_EK)
    rnd = random.Random(tohum + 9901)

    hed = Hedef(faz0=faz0, yon=hedef_yon)
    hx, hy, hz, hvx, hvy, _ = hed.durum()
    hdg = math.atan2(hvy, hvx)
    d_arka = istasyon * math.cos(math.radians(elev))
    d_alt = istasyon * math.sin(math.radians(elev))
    # baslangic: istasyonda oturmus (gorev basi tirmanis modellenmiyor)
    av = Avci(x=hx - d_arka * math.cos(hdg), y=hy - d_arka * math.sin(hdg),
              z=hz - d_alt, yaw=hdg,
              max_accel=cfg.MAX_ACCEL, v_max=cfg.V_TOPLAM_MAX,
              vz_max=cfg.VZ_MAX, yaw_rate_max=cfg.YAW_RATE_MAX_DEG)
    av.vx, av.vy = Olcum.HEDEF_HIZ * math.cos(hdg), Olcum.HEDEF_HIZ * math.sin(hdg)

    pol.sifirla()
    faz = "GPS"
    t = 0.0
    son_yasa_t = -1e9
    gps_s = gorsel_s = 0.0
    fazlar = []
    segmentler = []          # GPS segmenti: (bas_menzil, min_menzil, sure)
    seg_bas = None
    seg_min = 1e9
    seg_t0 = 0.0
    son_olum_t = 0.0

    # GPS fazi tanilari (truth turevleri -- GPS fazinda serbest)
    los_o = men_o = t_o = None
    lam_truth = 0.0
    kapanma = 0.0
    hdg_o = None
    hedef_donus = 0.0
    # yasa kanalindaki (kirli) lam kestirimi -- devir kapisi icin
    los_yasa_gecmis = []
    lam_yasa = 0.0

    # gorsel faz durumu
    g_hiz_I = Olcum.HEDEF_HIZ
    g_psi_v = None
    g_terminal = False
    g_kayip = 0
    g_los_gecmis = []
    g_lam = 0.0
    g_en_yakin = 1e9
    g_t0 = 0.0
    g_kutulu = 0
    g_tik = 0
    g_devir = None

    while t < sure:
        hed.adim(dt)
        hx, hy, hz, hvx, hvy, _ = hed.durum()
        av._hedef_yon = math.atan2(hvy, hvx)
        k = kadraj(av, hx, hy, hz)
        algi.kare_ver(t, av, k)
        menzil = math.dist((av.x, av.y, av.z), (hx, hy, hz))

        # ── yasa/supervisor dongusu (33.3 Hz) ─────────────────────────────
        if t - son_yasa_t < 1.0 / hata.yasa_hz - 1e-9:
            av.adim(dt, t)
            t += dt
            if faz == "GPS":
                gps_s += dt
            else:
                gorsel_s += dt
                g_en_yakin = min(g_en_yakin, menzil)
            continue
        dt_yasa = dt if son_yasa_t < 0.0 else max(t - son_yasa_t, dt)
        son_yasa_t = t
        poz = algi.oku(t)
        yaw_olc = algi.yaw_oku(t)
        roll_olc, pitch_olc = algi.tutum_oku(t)

        # ── TRUTH TUREVLERI (yalniz GPS fazinda kullanilir) ───────────────
        los = math.atan2(hy - av.y, hx - av.x)
        if los_o is not None and t_o is not None and t - t_o > 1e-6:
            d = (los - los_o + math.pi) % (2 * math.pi) - math.pi
            ham = math.degrees(d / (t - t_o))
            lam_truth = 0.35 * ham + 0.65 * lam_truth     # EMA (olcum gurultusu)
            kapanma = 0.35 * ((men_o - menzil) / (t - t_o)) + 0.65 * kapanma
        los_o, men_o, t_o = los, menzil, t
        hdg_s = math.atan2(hvy, hvx)
        if hdg_o is not None:
            d = (hdg_s - hdg_o + math.pi) % (2 * math.pi) - math.pi
            hedef_donus = 0.3 * math.degrees(d / dt_yasa) + 0.7 * hedef_donus
        hdg_o = hdg_s

        if faz == "GPS":
            gps_s += dt
            if seg_bas is None:
                seg_bas, seg_t0 = menzil, t
            seg_min = min(seg_min, menzil)
            # yasanin gorecegi (kirli) LOS ve lam -- politika 3'un "yasa" kolu
            if poz is not None:
                lo = yaw_olc + math.atan((poz[0] - cfg.CX_NISAN) / F_YASA)
                if los_yasa_gecmis:
                    onc = los_yasa_gecmis[-1][1]
                    lo = onc + ((lo - onc + math.pi) % (2 * math.pi) - math.pi)
                los_yasa_gecmis.append((t, lo))
                while los_yasa_gecmis and t - los_yasa_gecmis[0][0] > cfg.PN_PENCERE_S:
                    los_yasa_gecmis.pop(0)
                if len(los_yasa_gecmis) >= 3:
                    n_ = len(los_yasa_gecmis)
                    tm = sum(g[0] for g in los_yasa_gecmis) / n_
                    lm = sum(g[1] for g in los_yasa_gecmis) / n_
                    sxx = sum((g[0] - tm) ** 2 for g in los_yasa_gecmis)
                    if sxx > 1e-12:
                        lam_yasa = math.degrees(
                            sum((g[0] - tm) * (g[1] - lm) for g in los_yasa_gecmis) / sxx)
            else:
                los_yasa_gecmis = []

            gozlem = {
                "gorulen": poz is not None,
                "kutu": (max(poz[2], poz[3]) if poz is not None else 0.0),
                "menzil": menzil,
                "aspect": _aspect_deg(av.x, av.y, hx, hy, hvx, hvy),
                "lam_truth": lam_truth,
                "lam_yasa": lam_yasa,
                "kapanma": kapanma,
                "hedef_donus": hedef_donus,
            }
            if pol.degerlendir(gozlem):
                if seg_bas is not None:
                    segmentler.append((seg_bas, seg_min, t - seg_t0))
                    seg_bas, seg_min = None, 1e9
                faz = "GORSEL"
                g_devir = dict(gozlem)
                g_devir["az"] = abs(math.degrees(
                    math.atan((poz[0] - cfg.CX_NISAN) / F_YASA))) if poz else 0.0
                g_devir["t"] = t
                g_devir["bosluk"] = t - son_olum_t
                g_hiz_I = math.hypot(av.vx, av.vy)
                g_psi_v = None
                g_terminal = False
                g_kayip = 0
                g_los_gecmis = []
                g_lam = 0.0
                g_en_yakin = menzil
                g_t0 = t
                g_kutulu = 0
                g_tik = 0
                algi.faz_t0 = t          # suruklenme SAYACI gorsel fazla baslar
                pol.sifirla()
            else:
                # ── GPS ISTASYON TUTMA ────────────────────────────────────
                sx = hx - d_arka * math.cos(hdg_s)
                sy = hy - d_arka * math.sin(hdg_s)
                sz = hz - d_alt
                vx = hvx + K_IST * (sx - av.x)
                vy = hvy + K_IST * (sy - av.y)
                vm = math.hypot(vx, vy)
                if vm > v_gps:
                    vx, vy = vx * v_gps / vm, vy * v_gps / vm
                vz = -K_IST_Z * (sz - av.z)          # NED: asagi pozitif
                vz = max(-cfg.VZ_MAX, min(cfg.VZ_MAX, vz))
                av.setpoint(vx, vy, vz, math.atan2(hy - av.y, hx - av.x), t)
        else:
            # ══ GORSEL FAZ -- GERCEK YASA, GPS YOK ══════════════════════
            gorsel_s += dt
            g_tik += 1
            g_en_yakin = min(g_en_yakin, menzil)
            if poz is None:
                g_kayip += 1
                if g_kayip >= kayip_m:
                    fazlar.append({
                        "t0": g_t0, "omur": t - g_t0, "en_yakin": g_en_yakin,
                        "kutulu": g_kutulu / max(g_tik, 1),
                        "devir": g_devir, "bitis": "KAYIP"})
                    son_olum_t = t
                    faz = "GPS"
                    algi.faz_t0 = None       # GPS fazinda surukleme YOK
                    pol.sifirla()
                    los_yasa_gecmis = []
            else:
                g_kayip = 0
                g_kutulu += 1
                cx, cy, w, h = poz
                # ⚠ LOS'un IKI PARCASI DA OLCUM (deney.py:110-113 ile ayni)
                lo = yaw_olc + math.atan((cx - cfg.CX_NISAN) / F_YASA)
                if g_los_gecmis:
                    onc = g_los_gecmis[-1][1]
                    lo_a = onc + ((lo - onc + math.pi) % (2 * math.pi) - math.pi)
                else:
                    lo_a = lo
                g_los_gecmis.append((t, lo_a))
                while g_los_gecmis and t - g_los_gecmis[0][0] > cfg.PN_PENCERE_S:
                    g_los_gecmis.pop(0)
                if len(g_los_gecmis) >= 3:
                    n_ = len(g_los_gecmis)
                    tm = sum(g[0] for g in g_los_gecmis) / n_
                    lm = sum(g[1] for g in g_los_gecmis) / n_
                    sxx = sum((g[0] - tm) ** 2 for g in g_los_gecmis)
                    g_lam = (max(-6.0, min(6.0, sum((g[0] - tm) * (g[1] - lm)
                                                    for g in g_los_gecmis) / sxx))
                             if sxx > 1e-12 else 0.0)
                boyut = math.sqrt(w * h)
                if not g_terminal and boyut >= cfg.TERMINAL_BOYUT:
                    g_terminal = True
                vx, vy, vz, yaw_cmd, g_hiz_I, tani = IB.komut(
                    cx, cy, w, h, yaw_olc, g_hiz_I, dt_yasa, cfg, g_terminal,
                    (g_lam, 0.0), pitch_olc, av.vz, None, roll_olc,
                    av.yaw_hizi, g_psi_v)
                g_psi_v = tani.get("psi_v")
                av.setpoint(vx, vy, vz, yaw_cmd, t)

        av.adim(dt, t)
        t += dt

    if faz == "GORSEL" and g_devir is not None:
        fazlar.append({"t0": g_t0, "omur": t - g_t0, "en_yakin": g_en_yakin,
                       "kutulu": g_kutulu / max(g_tik, 1),
                       "devir": g_devir, "bitis": "SURE"})
    return {"faz": fazlar, "gps_s": gps_s, "gorsel_s": gorsel_s, "sure": t,
            "segment": segmentler}


# ══════════════════════════════════════════════════════════════════════════
#  TEK GORSEL ANGAJMAN -- VERILEN DEVIR DURUMUNDAN
# ══════════════════════════════════════════════════════════════════════════
# ⚠⚠ BU, CALISMANIN ANA DELILI. Sebep: yukaridaki gorev() dongusunun GPS
# FAZI SAHAYA SADIK DEGIL (bkz. --kalibre: tesisteki arac istasyona VARIYOR,
# sahadaki VARAMIYOR). Devir POLITIKASI sorusu ise "hangi devir DURUMU iyi"
# sorusudur; onu GPS modelinden BAGIMSIZ olcebiliriz:
#   * devir durumunu SAHADA OLCULEN dagilimdan orneklersin,
#   * o durumdan GERCEK yasayi + saha-kalibre tespit modelini kosarsin,
#   * politika = durum uzerinde bir SUZGEC.
# Devir SIKLIGI de sahadan gelir (329 segment, p50 7.0 s), tesisten degil.
#
# SAHA DEVIR DURUMU (gps_guidance_20260816_1[6-7]*.csv, 359 devir ani):
#     menzil   p10 12.7  p50 15.7  p90 20.1 m
#     aspect   p10  4    p50 17    p90 30   deg
#     omega_LOS p10 3.5  p50 19.0  p90 37.8 deg/s
#     dikey (hedef-avci)  p50 -1.5 m  (istasyon 9 m x sin10 = 1.56 -- TUTUYOR)
#     avci hizi p10 17.6 p50 21.6 p90 24.2 m/s
# ⚠ TURETILEN KIMLIK: omega = V_hedef * sin(aspect) / R.
#    18*sin(17)/15.7 = 19.2 deg/s -- olculen 19.0. Yani ASPECT KAPISI ile
#    LOS HIZI KAPISI AYNI degiskenin iki yuzu; fark, lam'in menzili de
#    icermesi. Politika 2 ve 3 bagimsiz secenek DEGIL.
def gorsel_angajman(menzil=15.7, aspect=17.0, dikey=1.5, v0=21.6, faz0=0.0,
                    tohum=0, cfg=IB.Cfg, hata=None, saha_kayip=True,
                    kayip_m=KAYIP_M, dt=1.0 / 62.0, sure=12.0, hedef_yon=+1,
                    yon_isaret=+1, yaw_rate=None, surukleme_ek=None):
    """Devir anindan baslayan TEK gorsel angajman. GPS YOK (yarisma kurali).

    menzil : devir aninda egik menzil (m)
    aspect : hedefin hiz vektoru ile LOS arasi aci (deg); 0 = tam kuyruk
    dikey  : avcinin hedefin KAC METRE ALTINDA oldugu (m)
    v0     : avcinin devir anindaki yatay hizi (m/s)
    """
    if hata is None:
        hata = HataAyari()
    hata.yasa_hz = Saha.YASA_HZ
    hata.kamera_hz = Saha.YASA_HZ
    algi = SahaAlgi(hata, tohum=tohum, saha_kayip=saha_kayip, gorunur=True,
                    surukleme_ek=(SURUKLEME_EK if surukleme_ek is None
                                  else surukleme_ek))
    algi.faz_t0 = 0.0

    hed = Hedef(faz0=faz0, yon=hedef_yon)
    hx, hy, hz, hvx, hvy, _ = hed.durum()
    hdg = math.atan2(hvy, hvx)
    # avci: hedefin gerisinde, kuyruk konisinden `aspect` kadar yana
    chi = math.radians(aspect) * yon_isaret
    yatay = math.sqrt(max(menzil ** 2 - dikey ** 2, 1.0))
    av = Avci(x=hx + yatay * math.cos(hdg + math.pi + chi),
              y=hy + yatay * math.sin(hdg + math.pi + chi),
              z=hz - dikey, yaw=hdg,
              max_accel=cfg.MAX_ACCEL, v_max=cfg.V_TOPLAM_MAX,
              vz_max=cfg.VZ_MAX,
              yaw_rate_max=(YAW_RATE_ETKIN if yaw_rate is None else yaw_rate))
    los0 = math.atan2(hy - av.y, hx - av.x)
    av.yaw = los0
    av.vx, av.vy = v0 * math.cos(los0), v0 * math.sin(los0)

    donus0 = hed.donus_hizi_deg()      # devir aninda hedef donuyor mu (deg/s)
    hiz_I = v0
    psi_v = None
    terminal = False
    kayip = 0
    los_gecmis = []
    lam = 0.0
    en_yakin = menzil
    t = 0.0
    son_yasa_t = -1e9
    kutulu = tik = 0
    eps_izi = []
    while t < sure:
        hed.adim(dt)
        hx, hy, hz, hvx, hvy, _ = hed.durum()
        av._hedef_yon = math.atan2(hvy, hvx)
        k = kadraj(av, hx, hy, hz)
        algi.kare_ver(t, av, k)
        en_yakin = min(en_yakin, math.dist((av.x, av.y, av.z), (hx, hy, hz)))
        if t - son_yasa_t < 1.0 / hata.yasa_hz - 1e-9:
            av.adim(dt, t)
            t += dt
            continue
        dt_yasa = dt if son_yasa_t < 0.0 else max(t - son_yasa_t, dt)
        son_yasa_t = t
        poz = algi.oku(t)
        yaw_olc = algi.yaw_oku(t)
        roll_olc, pitch_olc = algi.tutum_oku(t)
        tik += 1
        if k is not None:
            eps_izi.append((t, abs(math.degrees(
                math.atan((k[0] - T.CX) / F_YASA)))))
        if poz is None:
            kayip += 1
            if kayip >= kayip_m:
                break
        else:
            kayip = 0
            kutulu += 1
            cx, cy, w, h = poz
            lo = yaw_olc + math.atan((cx - cfg.CX_NISAN) / F_YASA)
            if los_gecmis:
                onc = los_gecmis[-1][1]
                lo = onc + ((lo - onc + math.pi) % (2 * math.pi) - math.pi)
            los_gecmis.append((t, lo))
            while los_gecmis and t - los_gecmis[0][0] > cfg.PN_PENCERE_S:
                los_gecmis.pop(0)
            if len(los_gecmis) >= 3:
                n_ = len(los_gecmis)
                tm = sum(g[0] for g in los_gecmis) / n_
                lm = sum(g[1] for g in los_gecmis) / n_
                sxx = sum((g[0] - tm) ** 2 for g in los_gecmis)
                lam = (max(-6.0, min(6.0, sum((g[0] - tm) * (g[1] - lm)
                                              for g in los_gecmis) / sxx))
                       if sxx > 1e-12 else 0.0)
            boyut = math.sqrt(w * h)
            if not terminal and boyut >= cfg.TERMINAL_BOYUT:
                terminal = True
            vx, vy, vz, yaw_cmd, hiz_I, tani = IB.komut(
                cx, cy, w, h, yaw_olc, hiz_I, dt_yasa, cfg, terminal,
                (lam, 0.0), pitch_olc, av.vz, None, roll_olc,
                av.yaw_hizi, psi_v)
            psi_v = tani.get("psi_v")
            av.setpoint(vx, vy, vz, yaw_cmd, t)
        av.adim(dt, t)
        t += dt
    # ⚠ SURUKLEME: hedefin KADRAJ ICINDE kayma hizi (deg/s). SAHADA OLCULDU:
    # |eps_ham| p50  t=0.12 s -> 5.9 deg ... t=1.0 s -> 26.0 deg  => ~22 deg/s.
    # Faz omrunu belirleyen ASIL degisken bu; tehlike tablosu |eps|'in
    # fonksiyonu oldugu icin surukleme ne kadar hizliysa faz o kadar kisa.
    sur = 0.0
    if len(eps_izi) >= 4:
        bas = [q for q in eps_izi if q[0] <= 0.20]
        son = [q for q in eps_izi if 0.55 <= q[0] <= 0.95]
        if bas and son:
            t_b = sum(q[0] for q in bas) / len(bas)
            t_s = sum(q[0] for q in son) / len(son)
            if t_s - t_b > 0.1:
                sur = ((sum(q[1] for q in son) / len(son)
                        - sum(q[1] for q in bas) / len(bas)) / (t_s - t_b))
    return {"omur": t, "en_yakin": en_yakin,
            "kutulu": kutulu / max(tik, 1), "surukleme": sur,
            "eps_p50": (sorted(q[1] for q in eps_izi)[len(eps_izi) // 2]
                        if eps_izi else 0.0),
            "menzil": menzil, "aspect": aspect, "v0": v0,
            "lam0": math.degrees(Olcum.HEDEF_HIZ * math.sin(math.radians(aspect))
                                 / max(menzil, 1e-6)),
            "donus": donus0}


# ══════════════════════════════════════════════════════════════════════════
#  ISTATISTIK YARDIMCILARI
# ══════════════════════════════════════════════════════════════════════════
def p(a, q):
    if not a:
        return float("nan")
    b = sorted(a)
    return b[min(len(b) - 1, int(q * (len(b) - 1)))]


def spearman(x, y):
    n = len(x)
    if n < 8:
        return float("nan")

    def rank(v):
        o = sorted(range(n), key=lambda i: v[i])
        r = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and v[o[j + 1]] == v[o[i]]:
                j += 1
            ort = (i + j) / 2.0
            for q_ in range(i, j + 1):
                r[o[q_]] = ort
            i = j + 1
        return r

    a, b = rank(x), rank(y)
    ma, mb = sum(a) / n, sum(b) / n
    sa = math.sqrt(sum((v - ma) ** 2 for v in a))
    sb = math.sqrt(sum((v - mb) ** 2 for v in b))
    if sa < 1e-9 or sb < 1e-9:
        return float("nan")
    return sum((a[i] - ma) * (b[i] - mb) for i in range(n)) / (sa * sb)


def kosu_seti(pol, n=16, sure=240.0, **kw):
    """n gorev kosar, faz kayitlarini birlestirir."""
    fz, sg, gps, gor, top = [], [], 0.0, 0.0, 0.0
    for i in range(n):
        r = gorev(pol, sure=sure, tohum=i, faz0=(i * 0.618) % 1.0,
                  hedef_yon=(+1 if i % 2 == 0 else -1), **kw)
        fz += r["faz"]
        sg += r["segment"]
        gps += r["gps_s"]
        gor += r["gorsel_s"]
        top += r["sure"]
    return {"faz": fz, "segment": sg, "gorsel_s": gor, "sure": top, "gorev": n}


def ozet(ad, s, gen=30):
    fz = s["faz"]
    e = [x["en_yakin"] for x in fz]
    o = [x["omur"] for x in fz]
    v3 = sum(1 for x in e if x < 3.0)
    v1 = sum(1 for x in e if x < 1.0)
    dk = 60.0 * len(fz) / max(s["sure"], 1e-9)
    return ("  %-*s%8.2f%8.2f%8.2f%7.1f%7d%6d%7.0f%%" %
            (gen, ad[:gen], (p(e, .5) if e else float("nan")),
             (min(e) if e else float("nan")),
             (p(o, .5) if o else float("nan")), dk, v3, v1,
             100.0 * s["gorsel_s"] / max(s["sure"], 1e-9)))


def baslik(gen=30):
    return ("  %-*s%8s%8s%8s%7s%7s%6s%8s" %
            (gen, "politika", "iska50", "en iyi", "omur50", "devir/dk",
             "<3m", "<1m", "nobet") + "\n  " + "-" * (gen + 52))


# ══════════════════════════════════════════════════════════════════════════
#  1) KALIBRASYON -- tezgah sahayi yeniden uretiyor mu?
# ══════════════════════════════════════════════════════════════════════════
def _kalibre_tablo(s):
    fz = s["faz"]
    e = [x["en_yakin"] for x in fz]
    o = [x["omur"] for x in fz]
    ku = [x["devir"]["kutu"] for x in fz]
    me = [x["devir"]["menzil"] for x in fz]
    az = [x["devir"]["az"] for x in fz]
    bo = [x["devir"]["bosluk"] for x in fz if x["devir"]["bosluk"] > 0.1]
    kt = [x["kutulu"] for x in fz]
    sg = s.get("segment", [])
    return [
        ("GPS segment BASI menzil (m)", p([q[0] for q in sg], .5), Saha.SEG_BAS_P50),
        ("GPS segment MIN menzil (m)", p([q[1] for q in sg], .5), Saha.SEG_MIN_P50),
        ("GPS segment SURESI (s)", p([q[2] for q in sg], .5), Saha.SEG_SURE_P50),
        ("DEVIR menzili p50 (m)", p(me, .5), Saha.SEG_SON_P50),
        ("devir kutusu p50 (px)", p(ku, .5), Saha.DEVIR_KUTU_P50),
        ("devir |eps| p50 (deg)", p(az, .5), 3.0),
        ("faz omru p50 (s)", p(o, .5), Saha.OMUR_P50),
        ("faz omru p90 (s)", p(o, .9), Saha.OMUR_P90),
        ("faz ici kutulu kare orani", p(kt, .5), Saha.KUTULU_ORAN),
        ("devirler arasi bosluk p50 (s)", p(bo, .5), Saha.BOSLUK_P50),
        ("EN YAKIN GECIS p50 (m)", p(e, .5), Saha.ISKA_P50),
    ]


def kalibre(n=16, sure=240.0, supur=True):
    print("=" * 78)
    print("KALIBRASYON -- tezgah SAHAYI yeniden uretiyor mu?")
    print("  (mevcut politika: 10 ardisik tespit + kutu >= 14 px, istasyon 9 m)")
    print("=" * 78)
    assert not T.dogrula(sessiz=True), "TESIS OZ-SINAMASI KALDI"
    if supur:
        print("\n  TEK AYARLANAN SAYI: V_GPS_ETKIN (GPS fazinda ULASILAN hiz)")
        print("  %6s%9s%9s%9s%9s%9s%9s" %
              ("v_gps", "seg_bas", "seg_min", "seg_sure", "devir_m", "omur", "iska"))
        print("  " + "-" * 62)
        for v in (17.0, 18.0, 19.0, 20.0, 22.0):
            s = kosu_seti(Politika("M", 10, 14.0), n=max(4, n // 3), sure=sure,
                          istasyon=9.0, v_gps=v)
            tab = dict((a, b) for a, b, _ in _kalibre_tablo(s))
            print("  %6.1f%9.1f%9.1f%9.1f%9.1f%9.2f%9.2f" %
                  (v, tab["GPS segment BASI menzil (m)"],
                   tab["GPS segment MIN menzil (m)"], tab["GPS segment SURESI (s)"],
                   tab["DEVIR menzili p50 (m)"], tab["faz omru p50 (s)"],
                   tab["EN YAKIN GECIS p50 (m)"]))
        print("  SAHA  %9.1f%9.1f%9.1f%9.1f%9.2f%9.2f" %
              (Saha.SEG_BAS_P50, Saha.SEG_MIN_P50, Saha.SEG_SURE_P50,
               Saha.SEG_SON_P50, Saha.OMUR_P50, Saha.ISKA_P50))

    pol = Politika("MEVCUT", kare_n=10, boyut_px=14.0)
    s = kosu_seti(pol, n=n, sure=sure, istasyon=9.0)
    fz = s["faz"]
    e = [x["en_yakin"] for x in fz]
    print("\n  SECILEN AYARLA (V_GPS_ETKIN = %.1f m/s):" % V_GPS_ETKIN)
    print("  %-32s%10s%10s%9s" % ("olcut", "TEZGAH", "SAHA", "fark"))
    print("  " + "-" * 60)
    for ad, sim, saha in _kalibre_tablo(s):
        print("  %-32s%10.2f%10.2f%8.0f%%" %
              (ad, sim, saha, 100.0 * (sim - saha) / max(abs(saha), 1e-9)))
    print("  (n=%d faz / %d gorev / %.0f s)" % (len(fz), n, s["sure"]))

    print("\n  ISTASYON MESAFESI EGRISI (sahada olculen tek EGRI -- SEKIL testi)")
    print("  %8s%10s%10s%9s%9s" % ("istasyon", "TEZGAH", "SAHA", "omur", "devir/dk"))
    sim_e, saha_e = [], []
    for D in (22.7, 18.0, 13.0, 9.0, 7.0, 5.0):
        s2 = kosu_seti(Politika("M", 10, 14.0), n=max(6, n // 2),
                       sure=sure, istasyon=D)
        ee = [x["en_yakin"] for x in s2["faz"]]
        oo = [x["omur"] for x in s2["faz"]]
        sim_e.append(p(ee, .5))
        saha_e.append(Saha.ISTASYON_EGRISI[D])
        print("  %8.1f%10.2f%10.2f%9.2f%9.1f" %
              (D, p(ee, .5), Saha.ISTASYON_EGRISI[D], p(oo, .5),
               60.0 * len(s2["faz"]) / max(s2["sure"], 1e-9)))
    print("  egri SIRALAMA korelasyonu (Spearman) = %+.3f" % spearman(sim_e, saha_e))


# ══════════════════════════════════════════════════════════════════════════
#  2) POLITIKA KIYASI
# ══════════════════════════════════════════════════════════════════════════
def politikalar():
    return [
        Politika("1  MEVCUT 10 kare + 14 px", 10, 14.0),
        Politika("1b kutu kapisi KAPALI", 10, 0.0),
        Politika("1c kutu >= 20 px", 10, 20.0),
        Politika("1d kutu >= 10 px", 10, 10.0),
        # ── EK kapilar: MEVCUT kapinin USTUNE (menzil kisiti korunur) ──
        Politika("2  +aspect<20 (14 px ustune)", 10, 14.0, aspect_max=20.0),
        Politika("2b +aspect<20 +tgo<4 s", 10, 14.0, aspect_max=20.0, tgo_max=4.0),
        Politika("3  +|lam|<15 d/s (truth)", 10, 14.0, lam_max=15.0),
        Politika("3b +|lam|<15 (YASA kestirimi)", 10, 14.0, lam_max=15.0,
                 lam_kaynak="yasa"),
        Politika("4  +hedef DUZ (<8 d/s)", 10, 14.0, donus_max=8.0),
        Politika("5  +aspect<20 +lam<15", 10, 14.0, aspect_max=20.0, lam_max=15.0),
        # ── kapi YERINE: geometri tek basina (menzil kisiti YOK) ──
        Politika("6  aspect<20 TEK BASINA", 10, 0.0, aspect_max=20.0),
        Politika("7  |lam|<15 TEK BASINA", 10, 0.0, lam_max=15.0),
    ]


def kiyas(surukleme_ek=None, kayip_m=KAYIP_M):
    print("=" * 92)
    print("POLITIKA KIYASI -- SAHA firsat akisi (%d GPS tiki) x TEZGAH sonucu"
          % len(saha_akisi()))
    print("  olcum hatasi ACIK | suruklenme kalibrasyonu %s | KAYIP_M %d"
          % (("%.0f d/s" % (SURUKLEME_EK if surukleme_ek is None else surukleme_ek)),
             kayip_m))
    print("=" * 92)
    saha_kiyas(politikalar(), kayip_m=kayip_m, surukleme_ek=surukleme_ek)


# ══════════════════════════════════════════════════════════════════════════
#  3) ESIK TARAMALARI
# ══════════════════════════════════════════════════════════════════════════
def supurme():
    print("=" * 92)
    print("ESIK TARAMALARI -- SAHA firsat akisi x TEZGAH sonucu")
    print("=" * 92)
    setler = [
        ("2 GEOMETRIK -- aspect tavani (tgo KAPALI)",
         [Politika("aspect<%s" % x, 10, 14.0, aspect_max=x)
          for x in (10, 15, 20, 25, 30, 40, 999)]),
        ("2b GEOMETRIK -- kapanma suresi tavani (aspect KAPALI)",
         [Politika("tgo<%s s" % x, 10, 14.0, tgo_max=x)
          for x in (1.5, 2.5, 4.0, 6.0, 999)]),
        ("3 LOS HIZI KAPISI -- |lam| tavani (TRUTH, GPS fazi telemetrisi)",
         [Politika("|lam|<%s d/s" % x, 10, 14.0, lam_max=x)
          for x in (5, 10, 15, 20, 30, 999)]),
        ("3b AYNI KAPI, YASANIN KENDI lam KESTIRIMIYLE (5.9x sisme, 3.8-8.2 gezinen)",
         [Politika("|lam_yasa|<%s d/s" % x, 10, 14.0, lam_max=x, lam_kaynak="yasa")
          for x in (30, 60, 90, 150, 999)]),
        ("4 FIRSAT PENCERESI -- hedefin kendi donus hizi tavani",
         [Politika("donus<%s d/s" % x, 10, 14.0, donus_max=x)
          for x in (2, 5, 8, 15, 999)]),
        ("1 KUTU KAPISI -- boyut esigi (referans; 14 px = 17.7 m)",
         [Politika("kutu>=%s px" % x, 10, x) for x in (0, 8, 10, 14, 18, 22)]),
        ("1e MENZIL KAPISI (kutu yerine DOGRUDAN menzil)",
         [Politika("menzil<%s m" % x, 10, 0.0, menzil_max=x)
          for x in (10, 13, 16, 20, 25, 999)]),
    ]
    for ad, pl in setler:
        print("\n  " + ad)
        saha_kiyas(pl)


# ══════════════════════════════════════════════════════════════════════════
#  4) DEVIR PENCERESI -- devir kosulu ile SONUC arasindaki iliski
# ══════════════════════════════════════════════════════════════════════════
def pencere(n=6):
    """Devir anindaki kosullar ile fazin SONUCU arasindaki iliski.

    Devir durumlari SAHADAN orneklenir (kadraj icindeki her GPS tiki bir
    aday), sonuc TEZGAHTAN. Boylece iliski, mevcut kapinin daralttigi dar
    banda degil, GERCEKTEN karsilasilan tum durum uzayina bakar.
    """
    print("=" * 92)
    print("DEVIR ANI KOSULLARI -> FAZIN SONUCU")
    print("=" * 92)
    tik = [g for g in saha_akisi() if g["eps"] is not None and g["eps"] <= EPS_KAPI]
    # dagilimi temsil eden bir alt orneklem (her 60. tik)
    ornek = tik[::60]
    kayit = []
    for j, g in enumerate(ornek):
        R = [gorsel_angajman(menzil=g["menzil"], aspect=g["aspect"],
                             faz0=((j * 7 + i) * 0.618) % 1.0, tohum=j * 31 + i,
                             hedef_yon=(+1 if i % 2 == 0 else -1),
                             yon_isaret=(+1 if (i // 2) % 2 == 0 else -1))
             for i in range(n)]
        kayit.append((g, p([x["omur"] for x in R], .5),
                      p([x["en_yakin"] for x in R], .5),
                      sum(1 for x in R if x["en_yakin"] < 3.0) / len(R)))
    print("  n = %d devir adayi x %d tohum" % (len(kayit), n))
    o = [k[1] for k in kayit]
    e = [k[2] for k in kayit]
    print("\n  %-26s%12s%12s" % ("devir anindaki kosul", "rho(ISKA)", "rho(OMUR)"))
    print("  " + "-" * 50)
    for ad, an in (("devir menzili (m)", "menzil"),
                   ("devir aspect (deg)", "aspect"),
                   ("devir |lam| (d/s)", "lam"),
                   ("devir kutusu (px)", "kutu"),
                   ("devir |eps| (deg)", "eps"),
                   ("hedef donus hizi (d/s)", "donus")):
        v = [k[0][an] for k in kayit]
        print("  %-26s%+12.3f%+12.3f" % (ad, spearman(v, e), spearman(v, o)))
    print("\n  BANTLARA GORE (iska / omur / <3m):")
    for ad, an, kenar in (("devir menzili (m)", "menzil", (10, 13, 16, 20, 25)),
                          ("devir aspect (deg)", "aspect", (10, 20, 30, 45)),
                          ("devir |lam| (d/s)", "lam", (10, 20, 30, 45)),
                          ("devir kutusu (px)", "kutu", (10, 14, 18, 24)),
                          ("hedef donus (d/s)", "donus", (2, 8, 15, 25))):
        print("\n   %s" % ad)
        kov = {}
        for k in kayit:
            v = k[0][an]
            i = 0
            while i < len(kenar) and v > kenar[i]:
                i += 1
            kov.setdefault(i, []).append(k)
        for i in sorted(kov):
            alt = ("<%g" % kenar[0]) if i == 0 else (
                ">=%g" % kenar[-1] if i == len(kenar) else
                "%g-%g" % (kenar[i - 1], kenar[i]))
            g = kov[i]
            print("     %-10s n=%3d  iska %6.2f m  omur %5.2f s  <3m %%%.1f"
                  % (alt, len(g), p([z[2] for z in g], .5),
                     p([z[1] for z in g], .5),
                     100.0 * sum(z[3] for z in g) / len(g)))


# ══════════════════════════════════════════════════════════════════════════
#  6) DEVIR DURUM YUZEYI -- (menzil x aspect) -> omur / iska / vurus
# ══════════════════════════════════════════════════════════════════════════
def _parti(menzil, aspect, n, **kw):
    return [gorsel_angajman(menzil=menzil, aspect=aspect,
                            faz0=(i * 0.618) % 1.0, tohum=i * 7 + 3,
                            hedef_yon=(+1 if i % 2 == 0 else -1),
                            yon_isaret=(+1 if (i // 2) % 2 == 0 else -1), **kw)
            for i in range(n)]


def yuzey(n=24, menziller=(10, 13, 16, 19, 22, 26, 30),
          aspectler=(0, 10, 20, 30, 45), **kw):
    print("=" * 92)
    print("DEVIR DURUM YUZEYI -- gorsel faz, saha devir durumundan kosuldu")
    print("  (her hucre %d angajman; deger = medyan)" % n)
    print("=" * 92)
    veri = {}
    for ad, dizin in (("FAZ OMRU (s)", "omur"), ("ISKA (m)", "en_yakin"),
                      ("<3 m ORANI (%)", "vurus")):
        print("\n  %s" % ad)
        print("  %8s" % "menzil" + "".join("%9s" % ("asp%d" % a) for a in aspectler))
        for m in menziller:
            sat = "  %8.0f" % m
            for a in aspectler:
                key = (m, a)
                if key not in veri:
                    veri[key] = _parti(m, a, n, **kw)
                R = veri[key]
                if dizin == "vurus":
                    v = 100.0 * sum(1 for x in R if x["en_yakin"] < 3.0) / len(R)
                else:
                    v = p([x[dizin] for x in R], .5)
                sat += "%9.2f" % v
            print(sat)
    return veri


# ══════════════════════════════════════════════════════════════════════════
#  7) ⭐ ASIL DENEY -- SAHA FIRSAT AKISI x TEZGAH SONUCU
# ══════════════════════════════════════════════════════════════════════════
# ⚠ NEDEN BOYLE: gorev() dongusunun GPS fazi sahaya SADIK DEGIL (--kalibre
# bunu acikca gosteriyor: tesisteki arac istasyona variyor, sahadaki
# varamiyor). Ama devir politikasi sorusu IKI parcaya ayrilir:
#     (a) hangi devir DURUMLARI ne siklikta ONUMUZE geliyor?  -> SAHADAN
#     (b) verilen bir devir durumundan faz nasil bitiyor?      -> TEZGAHTAN
# (a) icin gercek gps_guidance loglari tik tik okunur (GPS segmentleri);
# (b) icin kalibre edilmis gorsel_angajman() kosulur. Boylece tezgahin
# SADIK OLMAYAN parcasi denklemden CIKAR.
SAHA_LOG = os.path.join(KOK, "kopru", "gazebo_kaynak", "logs")


def saha_segmentleri(desen="gps_guidance_20260816_1[6-7]*.csv", en_az=5):
    """Gercek GPS segmentleri: her tikte (t, menzil, aspect, donus, lam, kutu).

    kutu_px : R*max(w,h) = 248 px·m (bugun DOGRUDAN olculdu: devir menzili
              p50 15.7 m, devir kutusu p50 15.8 px).
    lam     : V_hedef*sin(aspect)/R  -- kimlik SAHADA DOGRULANDI
              (18*sin17/15.7 = 19.2 vs olculen omega_los p50 19.0).
    """
    import csv
    import glob as _g

    def _f(x):
        try:
            return float(x)
        except Exception:
            return None

    seg = []
    for y in sorted(_g.glob(os.path.join(SAHA_LOG, desen))):
        try:
            R = list(csv.DictReader(open(y, encoding="utf-8", errors="replace")))
        except Exception:
            continue
        tik = []
        hdg_o = t_o = None
        donus = 0.0
        for r in R:
            m = _f(r.get("menzil"))
            ax, ay = _f(r.get("iris_x")), _f(r.get("iris_y"))
            tx, ty = _f(r.get("tgt_x")), _f(r.get("tgt_y"))
            vx, vy = _f(r.get("tgt_vx")), _f(r.get("tgt_vy"))
            t = _f(r.get("t"))
            if None in (m, ax, ay, tx, ty, vx, vy, t) or m < 1.0:
                continue
            ex, ey = tx - ax, ty - ay
            lr = math.hypot(ex, ey)
            vh = math.hypot(vx, vy)
            if lr < 0.5 or vh < 1.0:
                continue
            lx, ly = ex / lr, ey / lr
            asp = math.degrees(math.atan2(abs(vx * ly - vy * lx), vx * lx + vy * ly))
            hd = math.atan2(vy, vx)
            if hdg_o is not None and t_o is not None and 0.01 < t - t_o < 0.5:
                d = (hd - hdg_o + math.pi) % (2 * math.pi) - math.pi
                donus = 0.3 * math.degrees(d / (t - t_o)) + 0.7 * donus
            hdg_o, t_o = hd, t
            # kadraj ici konum: hedefin kerterizi ile BURUN arasindaki aci.
            # Devir icin hedefin kadrajda VE tespit edilebilir olmasi sart;
            # faz oldugunde burun 30-60 derece kacik kaliyor, GPS fazinin
            # ilk isi geri cevirmek -- olculen 7.2 s'lik boslugun sebebi bu.
            iy = _f(r.get("iris_yaw_deg"))
            eps = None
            if iy is not None:
                eps = abs((math.degrees(math.atan2(ey, ex)) - iy + 540.0)
                          % 360.0 - 180.0)
            tik.append({"t": t, "menzil": m, "aspect": asp, "eps": eps,
                        "donus": abs(donus), "kutu": 248.0 / m,
                        "sisme": 3.8 + 4.4 * (((int(t * 1000) * 2654435761)
                                               % 1000) / 1000.0),
                        "lam": math.degrees(vh * math.sin(math.radians(asp)) / m)})
        if len(tik) >= en_az:
            seg.append(tik)
    return seg


# hedefin kadrajda VE tespit edilebilir sayilmasi icin gereken azami |eps|.
# Yari-HFOV 61 derece; 40-50 bandinda kare basina kayip 0.585 oldugu icin
# 10 ARDISIK kare pratikte toplanamaz -> 45 derece kesme.
EPS_KAPI = 45.0
DEVIR_DWELL_S = 10.0 / Saha.YASA_HZ      # 10 ardisik kare = 0.30 s @33.3 Hz


def _kabul(g, pol):
    """Politikanin GPS fazi kapilari (ardisik kare sarti ayri ele alinir)."""
    if g.get("eps") is None or g["eps"] > EPS_KAPI:
        return False
    if pol.boyut_px > 0.0 and g["kutu"] < pol.boyut_px:
        return False
    if pol.aspect_max is not None and g["aspect"] > pol.aspect_max:
        return False
    if pol.lam_max is not None:
        # ⚠ "yasa" kolu: yasanin lam kestirimi SAHADA truth'un 5.9 KATI ve
        # sisme 3.8-8.2 arasinda GEZINIYOR (arac/pn_kiyas.py, 7 faz). Yani
        # esik sabit olsa bile kapi RASTGELE aciliyor. Tik basi sisme.
        lam = abs(g["lam"]) * (g["sisme"] if pol.lam_kaynak == "yasa" else 1.0)
        if lam > pol.lam_max:
            return False
    if pol.donus_max is not None and g["donus"] > pol.donus_max:
        return False
    if pol.menzil_max is not None and g["menzil"] > pol.menzil_max:
        return False
    if pol.tgo_max is not None:
        # kapanma sahada ~4 m/s olculdu (DURUM §1)
        if g["menzil"] / 4.0 > pol.tgo_max:
            return False
    return True


_AKIS = None


def saha_akisi(seg=None):
    """Butun GPS tiklerini ZAMAN SIRASINDA tek akisa dizer.

    ⚠ VARSAYIM: bir politika devretmeyi ERTELERSE, arac benzer durum
    cevrimini gormeye devam eder -- yani ardisik segmentleri birlestirmek
    "devretmeseydik ne gorurduk" sorusuna makul bir vekildir. Gercek yorunge
    farkli olurdu; bu, calismanin BILINEN yaklasimidir.
    """
    global _AKIS
    if _AKIS is None or seg is not None:
        s = saha_segmentleri() if seg is None else seg
        tik = [g for x in s for g in x if g.get("eps") is not None]
        tik.sort(key=lambda g: g["t"])
        _AKIS = tik
    return _AKIS


_ONBELLEK = {}
_REF_ORAN = {}


def saha_kiyas(politikalar_, tohum_n=8, ayrinti=True, akis=None,
               kayip_m=KAYIP_M, surukleme_ek=None, _ham=False):
    """SAHA firsat akisi + TEZGAH sonucu -> politika kiyas tablosu."""
    tik = saha_akisi() if akis is None else akis

    def sonuc(m, a, n=tohum_n):
        k = (round(m / 1.5) * 1.5, round(a / 5.0) * 5.0, kayip_m, surukleme_ek)
        if k not in _ONBELLEK:
            _ONBELLEK[k] = [gorsel_angajman(
                menzil=max(k[0], 5.0), aspect=k[1], faz0=(i * 0.618) % 1.0,
                tohum=i * 13 + 5, kayip_m=kayip_m, surukleme_ek=surukleme_ek,
                hedef_yon=(+1 if i % 2 == 0 else -1),
                yon_isaret=(+1 if (i // 2) % 2 == 0 else -1)) for i in range(n)]
        return _ONBELLEK[k]

    # gorev suresi: 30 s'den buyuk sicramalar "ayri kosu" sayilir
    top_sure = 0.0
    for i in range(1, len(tik)):
        d = tik[i]["t"] - tik[i - 1]["t"]
        if 0 < d < 30.0:
            top_sure += d

    satirlar = []
    for pol in politikalar_:
        i = 1
        n = len(tik)
        cikti, devirler, bekle = [], [], []
        son_devir_t = tik[0]["t"]
        # ⚠ TESPIT SURECI DE MODELLENIR: "10 ARDISIK KARE" sarti, olculen
        # tehlike tablosuyla (|eps|, kutu) yurutulen iki durumlu zincirle
        # saglanir. Boylece uzak menzilde kapi KENDILIGINDEN zorlasir --
        # 33 m'de kutu 7.5 px, 10 ardisik kare pratikte toplanamaz.
        rnd = random.Random(4242)
        gor = False
        ardisik = 0
        while i < n:
            g = tik[i]
            dt_t = g["t"] - tik[i - 1]["t"]
            if not (0 < dt_t < 1.0):
                dt_t = 1.0 / Saha.YASA_HZ
            e = g["eps"] if g["eps"] is not None else 90.0
            b = g["kutu"]
            if e > 61.0 or b < 4.0:
                gor = False
            elif gor:
                if rnd.random() < _oran_cevir(_tehlike_p(e, b), dt_t):
                    gor = False
            else:
                if rnd.random() < _oran_cevir(_bulus_p(e, b), dt_t):
                    gor = True
            sayilir = gor and (pol.boyut_px <= 0.0 or b >= pol.boyut_px)
            ardisik = (ardisik + 1) if sayilir else 0
            if ardisik >= pol.kare_n and _kabul(g, pol):
                R = sonuc(g["menzil"], g["aspect"])
                cikti += R
                devirler.append(g)
                if 0 < g["t"] - son_devir_t < 120.0:
                    bekle.append(g["t"] - son_devir_t)
                omur = p([x["omur"] for x in R], .5)
                t_son = g["t"] + omur
                son_devir_t = t_son
                while i < n and tik[i]["t"] < t_son:
                    i += 1
                gor = False          # faz KAYIP_M ile bitti -> kutu yok
                ardisik = 0
                continue
            i += 1
        if not cikti:
            satirlar.append([pol.ad, float("nan"), float("nan"), 0.0,
                             0.0, 0.0, 0.0, float("nan")])
            continue
        e = [x["en_yakin"] for x in cikti]
        o = [x["omur"] for x in cikti]
        dev_dk = 60.0 * len(devirler) / max(top_sure, 1e-9)
        vur = sum(1 for x in e if x < 3.0) / len(e)
        satirlar.append([pol.ad, p(e, .5), p(o, .5),
                         p([g["menzil"] for g in devirler], .5),
                         dev_dk, 100.0 * vur, dev_dk * vur,
                         p(bekle, .5) if bekle else float("nan")])
    # ── DEVIR SIKLIGI SAHAYA OLCEKLENIR ──────────────────────────────────
    # Modelin MUTLAK sikligi sahanin 8.4/dk'sini tutturmuyor (bkz. rapor):
    # tespit zinciri, kisa yaklasma penceresinde 10 ardisik kareyi sahanin
    # basardigi kadar sik toplayamiyor. Bu, TUM politikalar icin ORTAK bir
    # carpan; siralamayi degistirmez. Bu yuzden MEVCUT politika sahanin
    # olculen degerine sabitlenir ve digerleri ayni carpanla olceklenir.
    ref = _REF_ORAN.get((kayip_m, surukleme_ek))
    if ref is None and not _ham:
        r0 = saha_kiyas([Politika("_ref", 10, 14.0)], tohum_n=tohum_n,
                        ayrinti=False, akis=tik, kayip_m=kayip_m,
                        surukleme_ek=surukleme_ek, _ham=True)
        ref = r0[0][4] if r0 and r0[0][4] > 0 else 1.0
        _REF_ORAN[(kayip_m, surukleme_ek)] = ref
    if not _ham:
        k = Saha.DEVIR_DK / max(ref, 1e-9)
        for s in satirlar:
            s[4] *= k
            s[6] = s[4] * (s[5] / 100.0)
            s[7] = (60.0 / s[4]) - s[2] if s[4] > 1e-9 else float("nan")
    if ayrinti:
        print("  %-30s%8s%8s%8s%9s%7s%9s%8s" %
              ("politika", "iska50", "omur50", "devir_m", "devir/dk", "<3m%",
               "vurus/dk", "bosluk"))
        print("  " + "-" * 88)
        for s in satirlar:
            print("  %-30s%8.2f%8.2f%8.1f%9.2f%7.1f%9.3f%8.1f" % tuple(s))
    return satirlar


# ══════════════════════════════════════════════════════════════════════════
#  5) TEKRAR DEVIR -- bosluk / nobet / toplam vurus sansi
# ══════════════════════════════════════════════════════════════════════════
def tekrar():
    """5) TEKRAR DEVIR: bosluk kisalirsa toplam vurus sansi artar mi?"""
    print("=" * 92)
    print("TEKRAR DEVIR -- faz oldukten sonra ne kadar hizli geri donuyoruz?")
    print("=" * 92)
    print("  SAHA OLCUMU (bugun, 16 Agu 16:00-17:03, 329 GPS segmenti):")
    print("    devirler arasi bosluk p50 %.1f s (p10 4.2 / p90 9.6-14)"
          % Saha.BOSLUK_P50)
    print("    !! Gorevde verilen 27 s ESKI konfigurasyona ait; bugun 6.6 s.")
    print("    faz omru 1.22 s -> gorsel faz NOBETI = 1.22/(1.22+6.6) = %%%.0f"
          % (100.0 * Saha.OMUR_P50 / (Saha.OMUR_P50 + Saha.BOSLUK_P50)))
    print("    BOSLUGUN SEBEBI OLCULDU: faz oldugunde hedef burundan"
          " p50 95 derece KACIK\n    (segment basi |eps| p50 95, p90 136;"
          " yari-HFOV 61) -- yani hedef KADRAJ DISINDA.\n    Once geri donmek"
          " gerekiyor; kapiyi gevsetmek bu sureyi KISALTMAZ.")
    print()
    for ad, pl, km in (
            ("A) KAPIYI GEVSETMEK (KAYIP_M=20 sabit)",
             [Politika("mevcut 14 px", 10, 14.0),
              Politika("kutu >= 10 px", 10, 10.0),
              Politika("kutu kapisi KAPALI", 10, 0.0)], 20),
            ("B) FAZI DAHA GEC OLDURMEK: KAYIP_M=30 (0.90 s kor tolerans)",
             [Politika("mevcut 14 px", 10, 14.0)], 30),
            ("C) KAYIP_M=40 (1.20 s kor tolerans)",
             [Politika("mevcut 14 px", 10, 14.0)], 40),
            ("D) KAYIP_M=60 (1.80 s -- sartname disi, ust sinir)",
             [Politika("mevcut 14 px", 10, 14.0)], 60)):
        print("  " + ad)
        saha_kiyas(pl, kayip_m=km)
        print()


# ══════════════════════════════════════════════════════════════════════════
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kalibre", action="store_true")
    ap.add_argument("--politika", action="store_true")
    ap.add_argument("--supurme", action="store_true")
    ap.add_argument("--pencere", action="store_true")
    ap.add_argument("--tekrar", action="store_true")
    ap.add_argument("--yuzey", action="store_true")
    ap.add_argument("--hatasiz", action="store_true",
                    help="KONTROL: olcum hatasi KAPALI (kiyas icin, guvenme)")
    ap.add_argument("--n", type=int, default=16)
    ap.add_argument("--sure", type=float, default=240.0)
    ap.add_argument("--istasyon", type=float, default=9.0)
    a = ap.parse_args()
    assert not T.dogrula(sessiz=True), "TESIS OZ-SINAMASI KALDI"

    hic = not (a.kalibre or a.politika or a.supurme or a.pencere or a.tekrar
               or a.yuzey)
    if a.kalibre or hic:
        kalibre(n=a.n, sure=a.sure)
    if a.yuzey:
        print()
        yuzey(n=a.n)
    if a.politika or hic:
        print()
        kiyas()
        print("\n  !! SAGLAMLIK: AYNI KIYAS, SURUKLENME KALIBRASYONU KAPALI")
        print("     (siralama degisiyorsa sonuc kalibrasyona baglidir -- guvenme)")
        kiyas(surukleme_ek=0.0)
    if a.supurme:
        print()
        supurme()
    if a.pencere:
        print()
        pencere()
    if a.tekrar:
        print()
        tekrar()


if __name__ == "__main__":
    main()

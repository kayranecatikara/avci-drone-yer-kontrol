# -*- coding: utf-8 -*-
"""
================================================================================
  SIM_YASA  --  gurultu ve gecikme altinda DAYANAN yatay guduum yasasi arayisi
================================================================================
⚠ SALT OKUNUR KOMSULAR: kopru/ altindaki yasa kodu, sim/tesis.py ve sim/deney.py
DEGISTIRILMEZ. Bu dosya kendi angajman dongusunu kurar, IB.komut()'u AYNEN
cagirir ve yalniz komutun YATAY bilesenini degistirir (deney.py'deki N>0 PN
yamasinin desenini izler). Dikey/hiz kanallari her zaman yasadan gelir.

⚠⚠ HATA MODELI DAIMA ACIK. HataAyari.kapali()/eski() ile kosulan tarama
BILDIRILMEZ; tesis kusursuz sensorle 2026-08-16 sabahi PN'i sampiyon ilan etti
(37/480 -> 357/480) ve oyunda dort varyant da ~19.5 m verdi.

--------------------------------------------------------------------------------
 SAHA OLCUMU (arac/ariza_taksonomi.py, 2026-08-16, 831 gorsel faz)
--------------------------------------------------------------------------------
 OLUM SEKLI          A yandan cikti %27.6 | C dedektor goremedi %69.0
                     B dikeyden %0.7 | D yanlis nesne %2.8
 FAZ OMRU            p10 0.89 | p50 1.44 | p90 2.83 s
 EN YAKIN GECIS      p10 10.7 | p50 14.2 | p90 19.8 m
 DEVIR ANI           menzil 17.7 m | aspect 17.9 deg | kutu 9.0 px
                     kadraj az -6.4 deg | kapanma 3.5 m/s
 KUTULU KARE ORANI   p50 0.40
 OMRU EN COK BELIRLEYEN (Spearman): faz-ici LOS az hizi rho = -0.679
     (devir kapanma -0.392, devir |az| -0.367, devir menzili -0.006)

 -> Yani omru belirleyen sey MENZIL DEGIL, LOS HIZI. lam'i kucuk tutan yasa
    hem A olumunu (kadraj kenarina supurulme) hem C olumunu azaltir.

--------------------------------------------------------------------------------
 ⚠ TESIS SAHAYI OLDUGU GIBI URETMIYOR — bu dosyanin en onemli uyarisi
--------------------------------------------------------------------------------
 sim/deney.py + tesis.HataAyari() varsayilani (devir 17.7 m, 60 angajman):
        iska medyani ~4.4 m      faz omru ~11 s
 SAHA:  iska medyani 14.2 m      faz omru 1.44 s
 Fark tek bir eksik modelde: tesiste tespit kaybi BAGIMSIZ (i.i.d.), sahada
 KUMELI. p=0.26 ile 20 ardisik kare kaybetme olasiligi 0.74^20 = 0.0024;
 21.3 Hz'de olum bekleme suresi ~20 s. Sahada 1.44 s. Ustelik saha per-kare
 gorunurlugu DAHA IYI (0.40 > 0.26) ama olum DAHA HIZLI: bu tam olarak
 kumelenmenin imzasi (93/93 faz 19 karelik olum serisiyle bitiyor).
 Kapanma hizi ise ZATEN dogru: saha 3.5 m/s, tesis 3.6 m/s. Yani tesisin
 iskasi "omur x kapanma"dan ibaret; omur duzelince iska da duzeliyor.

 Bu yuzden IKI REJIMDE de kosulur ve IKISI DE raporlanir:
   --rejim tesis  : tesis.HataAyari() aynen (i.i.d. tespit kaybi)
   --rejim saha   : + Patlama (iki durumlu kumeli tespit kaybi), asagida
                    SAHA'nin omur/gorunurluk cifti tutturularak kalibre edildi.
 Bir yasa YALNIZ iki rejimde de kazanirsa "dayaniyor" denir.

 ⚠ Patlama modeli LAM'DAN BAGIMSIZDIR (bilerek). lam'a bagli bir dusme modeli
 kurmak "lam'i kucuk tutan yasa kazanir" sonucunu TANIMI GEREGI uretirdi —
 tesisin dorduncu sahte bulgusu olurdu. Patlama saf Poisson; yasanin omre
 etkisi yalniz GEOMETRI uzerinden (kadrajda kalmak, kutuyu buyutmek) olur.

--------------------------------------------------------------------------------
 ⚠ deney.py'de bulunan ve BURADA DUZELTILEN iki sadakat kusuru
--------------------------------------------------------------------------------
 1) deney.py yasaya `av.yaw_hizi`yi (GERCEK, anlik) veriyor. Gercekte
    bbox_ibvs.py:1054-1056 yaw hizini AYNI BAYAT `iris.yaw`i turevleyerek
    uretiyor ("kendi IMU'su, D0 temiz" yorumu yaw donmasi olculmeden once
    yazilmis ve ARTIK YANLIS). Burada yaw_hizi olculen yaw'dan, canli koddaki
    ayni 0.3/0.7 EMA ile turetilir. (--temiz_r ile karsilastirilabilir.)
 2) deney.py angajmani hedefle AYNI hizda (kapanma 0) baslatiyor; saha devir
    aninda kapanma medyani 3.5 m/s. Burada kapanma0 ile verilir.
--------------------------------------------------------------------------------
 BULGULAR (2026-08-16 aksami, n=400/varyant, saha-kalibre rejim)
--------------------------------------------------------------------------------
 1. OLCULEN KOR PENCEREDE (0.47 s) HICBIR YATAY YASA FARK ETMIYOR.
    23 varyantin hepsi 13.6-16.7 m; ilk altisinin %90 araliklari TAMAMEN
    ust uste. Sahada olculen "dort ayar da ~19.5 m" bulgusu YENIDEN URETILDI.
    Sebep aritmetik: 1.3 s omur x 3.5 m/s kapanma = 4.5 m. Devir 17.7 m'den
    baslayip 4.5 m kapatirsan 13.2 m'de kalirsin — yasa ne olursa olsun.

 2. ASIL KALDIRAC YASA DEGIL, KOR PENCERE (kayip toleransi):
        kor 0.47 s -> 14.1 m    kor 0.94 s -> 6.4-8.9 m    kor 1.50 s -> 4.6 m
    Tek parametre 8 m getiriyor; en iyi yasa farki 1.7 m. KAYIP_M 20 -> 40.

 3. PENCERE ACILINCA YASA ONEMLI OLUYOR ve SIRALAMA TERSINE DONUYOR:
    kor 0.94 s'de PN EN KOTU (8.90 m), saf takip 7.21, CB10 6.57,
    CB10+sessiz burun 6.37 m. PN'i acik tutmak 2.5 m KAYBETTIRIYOR.
    Bugun zararsiz gorunmesinin tek sebebi fazin PN'in etki edemeyecegi
    kadar kisa olmasi.

 4. GORUNTU DUZLEMI ACISAL HIZI (sahada omurle en guclu bagintili nicelik,
    rho -0.679) yasayla GERCEKTEN kontrol edilebiliyor:
        saf takip 33.7 d/s -> CB10 21.4 -> CB10+sessiz burun 19.2  (-%43)
    ⚠ Bu kanalin OMRE etkisi tesiste MODELLENMIYOR (bkz. asagi). Yani -%43
    bir GIRDI olcumu; ciktisi ancak sahada olculur.

 5. lam KESTIRIMCISI: PN altinda 10 kestirimci 13.60-14.74 m'ye yayiliyor
    (en iyi: yaw gozlemcisi `model`; en kotu: yaw'siz `piksel`). CB altinda
    yayilim 14.43-14.83 — yani sabit kerteriz kestirimciye 3 KAT DUYARSIZ,
    cunku lam'in yalniz ISARETINI kullaniyor. Asil bulgu bu.

--------------------------------------------------------------------------------
 SAHADA DENENECEK SIRA (ucuz -> pahali; her adim TEK degisken)
--------------------------------------------------------------------------------
 A) KAYIP_M 20 -> 40    (/api/gudum_ozellikleri, KOD DEGISIKLIGI YOK)
    Olculdu: 20 karelik olum serisi 0.47 s suruyor (kor pencere). 40 kare
    ~0.94 s eder. Tesis: iska 14.1 -> 6.4-8.9 m. Beklenen etki 4-8 m.
    ⚠ Bedeli: kor ucus suresi iki katina cikar; iz gercekten koptuysa GPS'e
    donus gecikir. Once 30 ile ara adim mantikli (ab_omur.py zaten 30 denedi:
    omur 1.24 -> 1.49 s, ISKA HENUZ OLCULMEDI — o sayiyi cikar).
 B) PN_N 1.6 -> 0.0     (/api/gudum_ozellikleri, KOD DEGISIKLIGI YOK)
    A adimindan SONRA. Pencere aciliyken PN 2.5 m KAYBETTIRIYOR (8.90 vs 6.37).
    A'dan once olcmenin anlami yok: 0.47 s'de fark 0.13 m (gurultu).
 C) SESSIZ BURUN: bbox_ibvs.Cfg.K_YAW 1.0 -> 0.3 (+ gorsel_ozellikler'e anahtar).
    Yalniz BURUN'u yavaslatir, hiz vektorune dokunmaz. Tesis: goruntu duzlemi
    hizi 33.7 -> 27.0 d/s, kor 0.94'te iska 7.21 -> 6.87 m, eps_max 27.7 deg
    (kadraj siniri 61 deg — pay bol, A olumu artmadi).
 D) SABIT KERTERIZ (CB lead 10 deg): yeni kod yolu, y_cb() burada.
    hiz_yonu = LOS + 10 deg * isaret(lam_yavas). Tesis: kor 0.94'te 6.57 m,
    C ile birlikte 6.37 m — MEVCUT'a gore 1.70 m (araliklar ayrik).

 ⚠ GUVEN DUZEYI: tesis saha omrunu/iskasini/sureklilgini uretiyor ama
 GORUNTU DUZLEMI HIZINI URETMIYOR (sim 27 d/s, saha 59 d/s) ve sahanin
 rho = -0.679 bagintisini isaret olarak bile tutturamiyor (sim +0.26...+0.11,
 K_GORUNTU ne yapilirsa yapilsin). Yani 1-3 ve 5 numarali bulgular saglam;
 4 numaralinin OMRE cevrilmesi TESISTE KANITLANAMAZ.
================================================================================
CALISTIR
    python arac/sim_yasa.py                 # uc rejim, butun taramalar
    python arac/sim_yasa.py --onay --n 400  # KARAR TABLOSU (guven araligiyla)
    python arac/sim_yasa.py --kalibre       # patlama modelinin saha uydurmasi
    python arac/sim_yasa.py --rho           # goruntu-hizi kanalini rho'ya uydur
    python arac/sim_yasa.py --grup omur     # kor pencere duyarliligi
    python arac/sim_yasa.py --grup lam      # lam kestirimci taramasi
================================================================================
"""
import argparse
import math
import os
import random
import statistics as st
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "kopru", "gazebo_kaynak"))
sys.path.insert(0, os.path.join(KOK, "sim"))

import tesis as T                                            # noqa: E402
from tesis import Avci, Hedef, Olcum, kadraj, F_YASA, CX, CY  # noqa: E402
from tesis import HataAyari, Algi, tespit_olasilik           # noqa: E402
from control.guidance import bbox_ibvs as IB                 # noqa: E402


# ══════════════════════════════════════════════════════════════════════════
#  SAHA SABITLERI (ariza_taksonomi.py ciktisi, 2026-08-16, 831 faz)
# ══════════════════════════════════════════════════════════════════════════
class Saha:
    DEVIR_M = 17.7          # m   devir ani menzil p50
    ASPECT_DEG = 17.9       # deg devir ani aspect p50 (0 = tam kuyruk)
    KAPANMA0 = 3.5          # m/s devir ani kapanma p50
    OMUR_P50 = 1.44         # s
    OMUR_P90 = 2.83         # s
    ISKA_P50 = 14.2         # m   faz-ici en yakin gecis p50
    GORUNUR = 0.40          # kutulu kare orani p50
    KAYIP_M = 20            # kare — kod sabiti (bbox_ibvs kayip_kare_esik)

    # ── ⚠ BU IKISI BU CALISMADA YENI OLCULDU (923 bbox_ibvs_20260816_*.csv) ──
    # tesis.HataAyari.yasa_hz = 21.3 Hz YANLIS TUREVLENMIS: o sayi yalnizca
    # KUTU TASIYAN satirlarin dt medyani (47 ms). Dongu wait_pose ile KARE
    # basina doner, kutu olsun olmasin. BUTUN satirlarda dt medyani 32.0 ms:
    YASA_HZ = 31.2          # Hz  (n=35.641 satir; dt p10 15 ms, p90 63 ms)
    # ve KAYIP_M=20 karenin GERCEK SURESI (fazi bitiren son kutusuz serinin
    # olculen suresi) 0.94 s DEGIL:
    KOR_S = 0.47            # s   (n=918 faz; p50 0.47, p90 1.33)
    # ⚠ Bu iki duzeltme onemli: 0.94 s'lik kor pencere ile hicbir makul dusme
    # modeli 1.44 s'lik omru URETEMIYOR (kalibrasyon izgarasi bunu gosterdi).
    # 0.47 s ile uretiyor. Yani "faz neden bu kadar cabuk oluyor" sorusunun
    # bir parcasi olcum hatasiydi, yasada degil.
    OMUR_OLC = 1.45         # s   (923 fazin dogrudan olcumu; taksonomi 1.44)
    GORUNUR_OLC = 0.37      # kutulu kare orani p50 (923 faz)


# ══════════════════════════════════════════════════════════════════════════
#  KUMELI TESPIT KAYBI (yalniz --rejim saha)
# ══════════════════════════════════════════════════════════════════════════
class Patlama:
    """IKI BILESENLI kumeli tespit kaybi (Gilbert-Elliott, iki kotu sinifi).

    IYI durum : olasilik = lojistik(kutu boyutu), yari-nokta IYI_YARI
    KISA kotu : sik, kisa dedektor hiccup'i. Sureklilgi (%40) belirler,
                20 kareyi (0.94 s) nadiren asar -> OLDURMEZ.
    UZUN kotu : seyrek, uzun iz kaybi. FAZI BU OLDURUR.

    NEDEN IKI BILESEN: tek ussel bilesenle saha ciftini (omur p50 1.44 s VE
    kutulu kare orani 0.40) AYNI ANDA tutturmak MATEMATIKSEL OLARAK imkansiz.
    Tek bilesende olum hizi 0.48/s icin kotu-durum gorev cevrimi ~%80 gerekir,
    bu da gorunurlugu 0.20'ye cakar (olculdu: --kalibre ciktisi). Sahada iki
    ayri nufus var: cok sayida 1-3 karelik bosluk + nadir uzun kopus
    (93/93 faz 19 karelik olum serisiyle bitiyor).

    ⚠ Hicbir parametre lam'a, eps'e ya da yasaya bagli DEGIL (bilerek).
    """
    # ── KALIBRE EDILMIS (python arac/sim_yasa.py --kalibre, 72 nokta x 60 anga.)
    #    olculen saha        tesis+patlama
    #    omur p50   1.45 s      1.39 s
    #    omur p90   2.83 s      3.06 s
    #    kutulu kare 0.37       0.39
    #    iska p50   14.2 m     13.4 m
    #    A olumu    27.6%      10%    <- ⚠ TEK BUYUK SAPMA, asagiya bak
    # ⚠ A (kadrajdan cikma) olumu eksik uretiliyor. A, yasanin KONTROL EDEBILDIGI
    # olum kanali; eksik uretmek karsilastirmayi TUTUCU yapar (yasalar arasi
    # farki KUCUK gosterir), abartmaz. Yani burada cikan "fark yok" sonucu
    # guvenli, cikan "fark var" sonucu ise alt sinirdir.
    KISA_HIZ = 1.00         # 1/s
    KISA_SURE = 0.14        # s   (ussel ortalama) — sureklilik bilesenli
    UZUN_HIZ = 2.40         # 1/s
    UZUN_SURE = 0.50        # s   (ussel; KOR_S=0.47'yi %39 olasilikla asar)
    IYI_YARI = 2.0          # px  iyi durumda lojistigin yari-noktasi

    # ── ⚠ GORUNTU-HIZI KANALI — VARSAYILAN KAPALI (K=0) ───────────────────
    # Sahada olculen en guclu bagintisi: faz-ici GORUNTU DUZLEMI acisal hizi
    # ile faz omru, Spearman rho = -0.679 (ariza_taksonomi.py `az_hizi` =
    # medyan |d(kamera azimutu)/dt|, TRUTH izdusumunden). Yani hedef kadrajda
    # hizli kayarken iz kopuyor (bulaniklik + izleyici eslestirme kapisi).
    # Yukaridaki lam-KOR model bu kanali ICERMIYOR ve sahanin TERSI isareti
    # veriyor (sim: rho = +0.41, cunku uzun yasayan faz yakinlasir ve acisal
    # hiz artar). Isaret farki, kanalin sahada GERCEK oldugunun kaniti.
    # K_GORUNTU > 0 iken uzun-patlama hizi (|w_goruntu|/REF)^K ile olceklenir.
    # ⚠ BU BIR VARSAYIMDIR, OLCUM DEGIL. Bu yuzden ayri rejim ve raporda ayri
    # satir. Amaci: "saha bagintisi nedenselse hangi yasa kazanir?" sorusu.
    K_GORUNTU = 0.0
    REF_DEG = 59.0          # deg/s — saha medyani (taksonomi azHiz p50)


class AlgiSaha(Algi):
    """tesis.Algi + kumeli tespit kaybi. Diger her sey (yaw donmasi, kutu
    gecikmesi, kenar yanliligi, yanlis nesne) tesisten AYNEN gelir."""

    def __init__(self, ayar=None, tohum=0, patlama=None):
        super().__init__(ayar, tohum)
        self.p = patlama
        self._kotu_bitis = -1e9
        self.kotuda = False
        self.w_goruntu = 0.0      # rad/s — hedefin KADRAJDAKI acisal hizi
                                  # (tesis GERCEK geometriden verir; plant'in
                                  #  bunu bilmesi dogru, yasa gormez)

    def _gorunur_mu(self, t, w, h, per):
        if self.p is None:
            return (not self.a.tespit_kaybi) or self.rnd.random() < tespit_olasilik(w, h)
        if t < self._kotu_bitis:
            return False
        uzun = self.p.UZUN_HIZ
        k_g = getattr(self.p, "K_GORUNTU", 0.0)
        if k_g > 0.0:
            o = math.degrees(abs(self.w_goruntu)) / self.p.REF_DEG
            uzun *= max(0.05, min(6.0, o)) ** k_g
        if self.rnd.random() < uzun * per:
            self._kotu_bitis = t + self.rnd.expovariate(1.0 / self.p.UZUN_SURE)
            return False
        if self.rnd.random() < self.p.KISA_HIZ * per:
            self._kotu_bitis = t + self.rnd.expovariate(1.0 / self.p.KISA_SURE)
            return False
        b = max(w, h)
        return self.rnd.random() < 1.0 / (1.0 + math.exp(-Olcum.TESPIT_EGIM *
                                                         (b - self.p.IYI_YARI)))

    def kare_ver(self, t, avci, k):
        dt = (1.0 / 62.0) if self._son_t is None else max(t - self._son_t, 0.0)
        self._son_t = t
        self._yaw_yaz(t, avci, dt)
        a = self.a
        if a.kamera_hz > 0.0 and t - self._son_kare < (1.0 / a.kamera_hz) - 1e-9:
            self._hazirla(t)
            return
        self._son_kare = t
        per = (1.0 / a.kamera_hz) if a.kamera_hz > 0.0 else (1.0 / 62.0)
        olcum = None
        if k is not None and self._gorunur_mu(t, k[2], k[3], per):
            olcum = self._bozup_ver(t, k)
        self._bekleyen.append((t + a.kare_gecikme_s + self._det_suresi(), t, olcum))
        self._hazirla(t)


# ══════════════════════════════════════════════════════════════════════════
#  LOS HIZI (lam) KESTIRIMCILERI
# ══════════════════════════════════════════════════════════════════════════
# Hepsinin arayuzu ayni:  guncelle(t, dt, eps, yaw, taze, yaw_cmd) -> lam (rad/s)
#   eps      : kutudan gelen, GOVDEYE gore azimut (rad)  — D kadar GECIKMELI
#   yaw      : telemetriden gelen yaw (rad)              — DONMUS olabilir
#   taze     : yaw degeri bir onceki tikten FARKLI mi (sahada da olculebilir:
#              dow_kopru._tazelik() ayni testi yapiyor)
#   yaw_cmd  : bizim GECEN TIKTE gonderdigimiz yaw setpoint'i (bizim bilgimiz)
LAM_TAVAN = 6.0            # rad/s — deney.py ile ayni clamp


def _sar(d):
    return (d + math.pi) % (2 * math.pi) - math.pi


class KTemel:
    ad = "temel"

    def __init__(self, **kw):
        self.__dict__.update(kw)
        self.sifirla()

    def sifirla(self):
        self.lam = 0.0
        self._onc = None

    def guncelle(self, t, dt, eps, yaw, taze, yaw_cmd):
        return 0.0


class KFark(KTemel):
    """Ardisik fark + EMA. Yasanin PN_PENCERE_S=0 yolunun aynisi."""
    ad = "fark"
    tau = 0.10

    def guncelle(self, t, dt, eps, yaw, taze, yaw_cmd):
        los = yaw + eps
        if self._onc is not None and t - self._onc[0] > 1e-6:
            ham = _sar(los - self._onc[1]) / (t - self._onc[0])
            ham = max(-LAM_TAVAN, min(LAM_TAVAN, ham))
            a = 1.0 if self.tau <= 0 else min(1.0, dt / max(self.tau, dt))
            self.lam += a * (ham - self.lam)
        self._onc = (t, los)
        return self.lam


class KEks(KTemel):
    """En kucuk kareler egimi (pencere W). Yasanin PN_PENCERE_S yolu."""
    ad = "eks"
    W = 0.25

    def sifirla(self):
        self.lam = 0.0
        self.g = []
        self._son = None

    def _it(self, t, los):
        if self.g:
            los = self.g[-1][1] + _sar(los - self.g[-1][1])
        self.g.append((t, los))
        while self.g and t - self.g[0][0] > self.W:
            self.g.pop(0)

    def _egim(self):
        n = len(self.g)
        if n < 3:
            return self.lam
        tm = sum(g[0] for g in self.g) / n
        lm = sum(g[1] for g in self.g) / n
        sxx = sum((g[0] - tm) ** 2 for g in self.g)
        if sxx < 1e-12:
            return self.lam
        s = sum((g[0] - tm) * (g[1] - lm) for g in self.g) / sxx
        return max(-LAM_TAVAN, min(LAM_TAVAN, s))

    def guncelle(self, t, dt, eps, yaw, taze, yaw_cmd):
        self._it(t, yaw + eps)
        self.lam = self._egim()
        return self.lam


class KAtla(KEks):
    """En kucuk kareler AMA yalniz yaw'in TAZE oldugu ornekler.

    Gerekce: yaw donukken los = yaw_donuk + eps(t); arac donerken eps
    kuculuyor, yani olculen LOS TERS yone kayiyor. O ornekler bilgi degil
    ZEHIR. Sahada uygulanabilir: dow_kopru._tazelik() zaten yas hesapliyor.
    """
    ad = "atla"

    def guncelle(self, t, dt, eps, yaw, taze, yaw_cmd):
        if taze:
            self._it(t, yaw + eps)
        self.lam = self._egim()
        return self.lam


class KModel(KEks):
    """YAW GOZLEMCISI: telemetri donukken yaw'i KENDI KOMUTUMUZDAN yurutur.

    Sahada uygulanabilir cunku yaw setpoint'ini biz uretiyoruz ve aracin yaw
    hiz tavani olculdu (214 deg/s zarf, yazilim clamp'i 120 deg/s).
        taze ornek geldi -> yaw_hat = telemetri  (duzeltme)
        donuk            -> yaw_hat += clamp(yaw_cmd - yaw_hat, +-r_max*dt)
    Boylece donma boyunca LOS'un ters yone kaymasi biter.
    """
    ad = "model"
    r_max = math.radians(120.0)

    def sifirla(self):
        KEks.sifirla(self)
        self.yaw_hat = None

    def guncelle(self, t, dt, eps, yaw, taze, yaw_cmd):
        if self.yaw_hat is None or taze:
            self.yaw_hat = yaw
        elif yaw_cmd is not None:
            d = _sar(yaw_cmd - self.yaw_hat)
            lim = self.r_max * dt
            self.yaw_hat = _sar(self.yaw_hat + max(-lim, min(lim, d)))
        self._it(t, self.yaw_hat + eps)
        self.lam = self._egim()
        return self.lam


class KAlfaBeta(KTemel):
    """Alfa-beta izleyici: los ve lam birlikte, sabit kazanc."""
    ad = "ab"
    alfa = 0.35
    beta = 0.10

    def sifirla(self):
        self.lam = 0.0
        self.x = None

    def guncelle(self, t, dt, eps, yaw, taze, yaw_cmd):
        z = yaw + eps
        if self.x is None:
            self.x = z
            return 0.0
        self.x = self.x + self.lam * dt
        r = _sar(z - self.x)
        self.x = _sar(self.x + self.alfa * r)
        if dt > 1e-6:
            self.lam += self.beta * r / dt
        self.lam = max(-LAM_TAVAN, min(LAM_TAVAN, self.lam))
        return self.lam


class KPiksel(KEks):
    """YAW'A HIC BAGLI OLMAYAN: lam yalniz piksel akisindan (eps).

    Bu GOVDE cercevesindeki LOS hizidir; atalet lam'i degildir (aradaki fark
    aracin kendi donus hizi). Burun LOS'u kovaladiginda eps~0'a oturur ve bu
    kestirim SIFIRA gider — yani bilgi kaybi. Yine de olculmeli: donuk yaw'in
    urettigi TERS ISARETLI zehirden daha mi iyi?
    """
    ad = "piksel"

    def guncelle(self, t, dt, eps, yaw, taze, yaw_cmd):
        self._it(t, eps)
        self.lam = self._egim()
        return self.lam


# ══════════════════════════════════════════════════════════════════════════
#  YATAY YASALAR — her biri hiz vektorunun YONUNU (rad, NED) dondurur
# ══════════════════════════════════════════════════════════════════════════
# Girdi sozlugu `d`:
#   los   : yaw_olc + eps            (olculen atalet LOS)
#   taban : yasanin kendi urettigi yon (IB.komut ciktisindan atan2(vy,vx))
#   lam   : kestirilen LOS hizi
#   lam_y : YAVAS kestirim (isaret icin; uzun pencere)
#   psi_v : bir onceki tikte komut edilen yon (PN durumu)
#   dt, boyut, w, h, v
MU = Olcum.HEDEF_HIZ / 21.6        # 0.833 — olculen hiz orani (saha)
YARI_HFOV = math.radians(61.04)    # tesis.TX_MAX -> atan(1.8067)


def y_yasa(d):
    """Yasanin kendi yatay kanali (PN dahil, Cfg neyse o). Referans."""
    return d["taban"]


def y_saf(d):
    """SAF TAKIP: hiz LOS'a. PN kapatilmis yasanin esdegeri."""
    return d["los"]


def y_pn(d, N=1.6):
    """PN: psi_v += N*lam*dt. deney.py'deki yamanin aynisi."""
    p = d["psi_v"]
    return d["los"] if p is None else _sar(p + N * d["lam"] * d["dt"])


def y_pn_fov(d, N=1.6, pay_deg=8.0):
    """FOV PAYINA GORE SINIRLI PN.

    Sert sinir: sin(lead) = mu*sin(aspect); mu=0.833'te en kotu lead 56.4 deg,
    yari-HFOV 61.04 deg -> 4.6 deg pay. PN'in LOS'tan sapmasi lead acisinin ta
    kendisi; onu kismak yasayi oldurur (bbox_ibvs.py:836-839 olctu: 45 deg
    tavanda 0/40). Bu yuzden tavan SABIT degil, KADRAJ PAYINA gore:
        tavan = yari_HFOV - |eps| - pay
    Yani hedef kadraj merkezindeyken PN serbest, kenara kaydikca kisiliyor.
    """
    p = d["psi_v"]
    if p is None:
        return d["los"]
    yeni = _sar(p + N * d["lam"] * d["dt"])
    tav = max(math.radians(3.0),
              YARI_HFOV - abs(d["eps"]) - math.radians(pay_deg))
    s = _sar(yeni - d["los"])
    return _sar(d["los"] + max(-tav, min(tav, s)))


def y_cb(d, lead_deg=15.0, dead=0.03):
    """SABIT KERTERIZ (sapmali saf takip): hiz LOS'tan SABIT bir aci kadar,
    hedefin gectigi YONE dogru sapar.

    NEDEN BU: kirli lam'in BUYUKLUGU 4-7 kat sisiyor ama ISARETI cogunlukla
    dogru. PN buyuklugu kullanir -> zehirlenir. Sabit kerteriz yalniz ISARET
    kullanir. Ofset kapanma geometrisinden gelir:
        sin(lead) = mu * sin(aspect),  mu = V_hedef/V_avci = 0.833
        saha aspect p50 17.9 deg -> lead = asin(0.833*sin17.9) = 14.8 deg
    Kadrajda karsiligi: cx = 320 + 166.6*tan(14.8) = 364 px, yani hedefi
    merkeze degil 44 px yana surersin.
    dead: |lam_y| bunun altindaysa ofset uygulanmaz (isaret guvenilmez).
    """
    L = math.radians(lead_deg)
    ly = d["lam_y"]
    if abs(ly) < dead:
        return d["los"]
    return _sar(d["los"] + math.copysign(L, ly))


def y_cb_asp(d, dead=0.03, tavan_deg=30.0):
    """SABIT KERTERIZ, ofset KUTU EN-BOY oraniyla kestirilen aspect'ten.

    Talon'un gorunur genisligi w = F*hypot(K*cos b, G*sin b)/R, yuksekligi
    h = F*0.30*G/R. Yani w/h yalniz |b|'ye baglidir -> aspect kestirilebilir:
        c = (w/h)*0.30*G ;  |cos b| = sqrt((c^2 - G^2)/(K^2 - G^2))
    ⚠ SADIKLIK UYARISI: bu bagintiyi tesis.kadraj() URETIYOR; gercek dedektor
    9-11 px'lik bir kutuda en-boy oranini bu hassasiyette vermez. Bu varyantin
    simulatordeki basarisi SAHAYA TASINMAZ diye okunmalidir.
    """
    K, G = Olcum.KANAT_ACIKLIGI, Olcum.GOVDE_UZUNLUK
    ly = d["lam_y"]
    if abs(ly) < dead or d["h"] <= 1e-6:
        return d["los"]
    c = (d["w"] / d["h"]) * 0.30 * G
    u = (c * c - G * G) / max(K * K - G * G, 1e-9)
    u = max(0.0, min(1.0, u))
    b = math.acos(math.sqrt(u))                 # |aspect| (0 = tam yandan)
    asp = math.pi / 2.0 - b                     # 0 = tam kuyrukta
    L = math.asin(max(-1.0, min(1.0, MU * math.sin(asp))))
    L = min(L, math.radians(tavan_deg))
    return _sar(d["los"] + math.copysign(L, ly))


def y_cb_pn(d, lead_deg=15.0, N=1.6, dead=0.03):
    """Sabit kerteriz TABAN + uzerine kucuk PN duzeltmesi."""
    taban = y_cb(d, lead_deg, dead)
    p = d["psi_v"]
    if p is None:
        return taban
    yeni = _sar(p + N * d["lam"] * d["dt"])
    s = _sar(yeni - taban)
    tav = math.radians(15.0)
    return _sar(taban + max(-tav, min(tav, s)))


# ── 5) KENDI FIKRIM: SESSIZ BURUN (nose quieting) ─────────────────────────
# GEREKCE, uc olcume dayanir:
#  (a) Sahada omurle EN GUCLU baginti GORUNTU DUZLEMI acisal hizi (rho -0.679),
#      yani hedefin KADRAJDA ne kadar hizli kaydigi. Bunu belirleyen sey hiz
#      vektoru degil BURUN'dur: kamera govdeye vidali.
#  (b) lam sismesinin iki kaynagi da (kutu gecikmesi 6.3x, donuk yaw 5.0x)
#      YAW HIZIYLA carpim halinde girer: LOS_yasa(t) ~ LOS(t-D) + yaw_hizi*D.
#      Burun ne kadar az donerse parazitik terim o kadar kucuk. BURUN_LOS bunu
#      KAPALI DONGUYE ceviriyor (tesis.py:365-371) — kendi kendini besliyor.
#  (c) Yaw komutu tek yeri: yaw_cmd = iris_yaw + K_YAW*eps, K_YAW = 1.0.
#      K_YAW < 1 dogrudan dongu kazancini dusurur. Sahada TEK SATIR.
# ⚠ Bedeli: burun yavas donerse hedef kadrajda kenara kayar -> A olumu artar.
# Kadraj yari-genisligi 61 deg oldugu icin epeyce pay var; OLCULMESI gerek.
def y_saf_sessiz(d, K=0.5):
    """Hiz LOS'ta (saf takip), BURUN yavas: yaw_cmd = yaw + K*eps."""
    return d["los"], _sar(d["yaw"] + K * d["eps"])


def y_cb_sessiz(d, lead_deg=15.0, K=0.5, dead=0.03):
    """Sabit kerteriz + sessiz burun."""
    return y_cb(d, lead_deg, dead), _sar(d["yaw"] + K * d["eps"])


def y_saf_burun_v(d):
    """BURUN HIZ VEKTORUNE. Kamera nereye ucuyorsak oraya bakar; hedef
    kadrajda sabit bir ofsete oturur ve kadraj icinde SESSIZ kalir."""
    return d["los"], d["los"]


YASALAR = {
    "yasa":       y_yasa,
    "saf":        y_saf,
    "pn":         y_pn,
    "pn_fov":     y_pn_fov,
    "cb":         y_cb,
    "cb_asp":     y_cb_asp,
    "cb_pn":      y_cb_pn,
    "saf_sessiz": y_saf_sessiz,
    "cb_sessiz":  y_cb_sessiz,
}


# ══════════════════════════════════════════════════════════════════════════
#  ANGAJMAN
# ══════════════════════════════════════════════════════════════════════════
def angajman(yatay=y_yasa, yasa_kw=None, kest=None, kest_yavas=None,
             cfg=IB.Cfg, faz0=0.0, tohum=0, hedef_yon=+1,
             devir_m=Saha.DEVIR_M, aspect_deg=Saha.ASPECT_DEG,
             kapanma0=Saha.KAPANMA0, sure=12.0, dt=1 / 62.0, kor_s=None,
             hata=None, patlama=None, temiz_r=False, kayit=False):
    """Tek gorsel angajman. deney.kosu()'nun deseni; farklari dosya basinda.

    Doner: iska (en yakin gecis, m), omur (s), olum sinifi, tani.
    """
    yasa_kw = yasa_kw or {}
    hata = HataAyari() if hata is None else hata
    # kor pencere: verilmediyse kod sabitinden turet (KAYIP_M kare / dongu hizi)
    if kor_s is None:
        kor_s = Saha.KAYIP_M / (hata.yasa_hz if hata.yasa_hz > 0 else 62.0)
    algi = AlgiSaha(hata, tohum=tohum, patlama=patlama)
    kest = kest or KEks(W=cfg.PN_PENCERE_S)
    kest.sifirla()
    if kest_yavas is not None:
        kest_yavas.sifirla()

    hed = Hedef(faz0=faz0, yon=hedef_yon)
    hx, hy, hz, hvx, hvy, _ = hed.durum()
    hdg = math.atan2(hvy, hvx)
    yon = hdg + math.pi + math.radians(aspect_deg)     # hedeften BIZE
    av = Avci(x=hx + devir_m * math.cos(yon), y=hy + devir_m * math.sin(yon),
              z=hz - 3.0, yaw=hdg, max_accel=cfg.MAX_ACCEL, v_max=cfg.V_TOPLAM_MAX,
              vz_max=cfg.VZ_MAX, yaw_rate_max=cfg.YAW_RATE_MAX_DEG)
    los0 = math.atan2(hy - av.y, hx - av.x)
    av.yaw = los0
    # ⚠ devir aninda kapanma 3.5 m/s (saha p50): hiz LOS yonunde, hedef hizi
    # LOS'a izdusumu + kapanma kadar.
    v0 = Olcum.HEDEF_HIZ * math.cos(_sar(hdg - los0)) + kapanma0
    av.vx, av.vy = v0 * math.cos(los0), v0 * math.sin(los0)

    t = 0.0
    kayip_t0 = None            # kesintisiz kutusuzlugun basladigi an
    terminal = False
    hiz_I = Olcum.HEDEF_HIZ
    psi_v = None
    yaw_cmd_onc = av.yaw
    yaw_onc_olc = None
    yaw_hizi = 0.0
    son_yasa_t = -1e9
    iska = 1e9
    gor = tick = 0
    olum = "SURE"
    son_eps = 0.0
    disarda = []          # kor pencere boyunca hedef KADRAJ DISINDA miydi
    eps_max = 0.0
    eps_g_onc = None
    w_iz = []
    lam_yasa_iz = []
    lam_truth_iz = []
    t_iz = []
    iz = []

    while t < sure:
        hed.adim(dt)
        hx, hy, hz, hvx, hvy, _ = hed.durum()
        av._hedef_yon = math.atan2(hvy, hvx)
        k = kadraj(av, hx, hy, hz)
        iska = min(iska, math.dist((av.x, av.y, av.z), (hx, hy, hz)))
        # ── GERCEK goruntu-duzlemi acisal hizi (plant bilir, yasa GORMEZ) ──
        # ariza_taksonomi.py `az_hizi` ile ayni tanim: |d(kamera azimutu)/dt|.
        if k is not None:
            e_g = math.atan((k[0] - CX) / F_YASA)
            if eps_g_onc is not None:
                algi.w_goruntu = (e_g - eps_g_onc) / dt
                w_iz.append(abs(algi.w_goruntu))
            eps_g_onc = e_g
        else:
            eps_g_onc = None
        algi.kare_ver(t, av, k)

        if hata.yasa_hz > 0.0 and t - son_yasa_t < 1.0 / hata.yasa_hz - 1e-9:
            av.adim(dt, t)
            t += dt
            continue
        dt_y = dt if son_yasa_t < 0.0 else max(t - son_yasa_t, dt)
        son_yasa_t = t
        tick += 1

        disarda.append((t, k is None))
        while disarda and t - disarda[0][0] > kor_s:
            disarda.pop(0)
        poz = algi.oku(t)
        yaw_olc = algi.yaw_oku(t)
        roll_olc, pitch_olc = algi.tutum_oku(t)
        # ⚠ SADAKAT: yaw hizi da OLCULEN yaw'dan (canli kod bunu boyle yapiyor)
        taze = (yaw_onc_olc is None) or (abs(yaw_olc - yaw_onc_olc) > 1e-12)
        if yaw_onc_olc is not None and 1e-3 < dt_y < 0.5:
            yaw_hizi = 0.3 * (_sar(yaw_olc - yaw_onc_olc) / dt_y) + 0.7 * yaw_hizi
        yaw_onc_olc = yaw_olc
        r_yasa = av.yaw_hizi if temiz_r else yaw_hizi

        if poz is None:
            if kayip_t0 is None:
                kayip_t0 = t
            if t - kayip_t0 >= kor_s:
                # OLUM SINIFI (taksonomi kurali): olum penceresi boyunca hedef
                # cogunlukla KADRAJ DISINDA idiyse A, kadrajin ICINDE olup da
                # dedektor goremediyse C.
                dis = sum(1 for _, b in disarda if b)
                olum = "A_KADRAJ" if dis * 2 >= len(disarda) else "C_TESPIT"
                break
        else:
            kayip_t0 = None
            cx, cy, w, h = poz
            gor += 1
            eps, _ = IB.los_seviye(cx, cy, roll_olc, pitch_olc, cfg)
            son_eps = eps
            eps_max = max(eps_max, abs(eps))
            los = _sar(yaw_olc + eps)
            lam = kest.guncelle(t, dt_y, eps, yaw_olc, taze, yaw_cmd_onc)
            lam_y = (kest_yavas.guncelle(t, dt_y, eps, yaw_olc, taze, yaw_cmd_onc)
                     if kest_yavas is not None else lam)
            t_iz.append(t)
            lam_yasa_iz.append(math.degrees(los))
            lam_truth_iz.append(math.degrees(math.atan2(hy - av.y, hx - av.x)))

            boyut = math.sqrt(w * h)
            if not terminal and boyut >= cfg.TERMINAL_BOYUT:
                terminal = True

            vx, vy, vz, yaw_cmd, hiz_I, tani = IB.komut(
                cx, cy, w, h, yaw_olc, hiz_I, dt_y, cfg, terminal,
                (lam, 0.0), pitch_olc, av.vz, None, roll_olc, r_yasa, psi_v)

            v = math.hypot(vx, vy)
            d = {"los": los, "eps": eps, "taban": math.atan2(vy, vx),
                 "lam": lam, "lam_y": lam_y, "psi_v": psi_v, "dt": dt_y,
                 "boyut": boyut, "w": w, "h": h, "v": v, "terminal": terminal,
                 "yaw": yaw_olc, "yaw_cmd": yaw_cmd}
            cikti = yatay(d, **yasa_kw)
            # varyant ya yalniz HIZ YONUNU ya da (hiz yonu, yaw_cmd) doner
            if isinstance(cikti, tuple):
                yon_cmd, yaw_cmd = cikti
            else:
                yon_cmd = cikti
            psi_v = yon_cmd
            vx, vy = v * math.cos(yon_cmd), v * math.sin(yon_cmd)
            yaw_cmd_onc = yaw_cmd
            av.setpoint(vx, vy, vz, yaw_cmd, t)
            if kayit:
                iz.append((round(t, 2), round(math.dist((av.x, av.y, av.z), (hx, hy, hz)), 2),
                           round(cx, 1), round(boyut, 1),
                           round(math.degrees(eps), 1), round(math.degrees(lam), 1)))
        av.adim(dt, t)
        t += dt

    def _p95h(v):
        o = []
        for i in range(3, len(v)):
            dd = t_iz[i] - t_iz[i - 3]
            if dd > 1e-3:
                o.append(abs(((v[i] - v[i - 3] + 540) % 360 - 180) / dd))
        return sorted(o)[int(0.95 * (len(o) - 1))] if o else None

    ly, lt = _p95h(lam_yasa_iz), _p95h(lam_truth_iz)
    return {"iska": iska, "omur": t, "olum": olum, "gorus": gor / max(tick, 1),
            "sisme": (ly / lt) if (ly and lt and lt > 1e-6) else None,
            "eps_max": math.degrees(eps_max), "son_eps": math.degrees(abs(son_eps)),
            "az_hizi": (math.degrees(st.median(w_iz)) if w_iz else None),
            "lam_yasa": ly, "lam_truth": lt, "iz": iz}


def parti(n=60, **kw):
    return [angajman(faz0=i / n, tohum=i, hedef_yon=(+1 if i % 2 == 0 else -1), **kw)
            for i in range(n)]


def _med(v):
    v = [x for x in v if x is not None]
    return st.median(v) if v else float("nan")


def ozet(r):
    return {
        "iska": _med([x["iska"] for x in r]),
        "omur": _med([x["omur"] for x in r]),
        "omur90": (sorted(x["omur"] for x in r)[int(0.9 * (len(r) - 1))] if r else 0),
        "gorus": _med([x["gorus"] for x in r]),
        "sisme": _med([x["sisme"] for x in r]),
        "A": sum(1 for x in r if x["olum"] == "A_KADRAJ") / len(r),
        "C": sum(1 for x in r if x["olum"] == "C_TESPIT") / len(r),
        "eps": _med([x["eps_max"] for x in r]),
        "az": _med([x["az_hizi"] for x in r]),
        "vur3": sum(1 for x in r if x["iska"] < 3.0) / len(r),
    }


def spearman(a, b):
    n = len(a)
    if n < 3:
        return 0.0
    A = [0] * n
    B = [0] * n
    for k, i in enumerate(sorted(range(n), key=lambda i: a[i])):
        A[i] = k
    for k, i in enumerate(sorted(range(n), key=lambda i: b[i])):
        B[i] = k
    ma, mb = sum(A) / n, sum(B) / n
    num = sum((A[i] - ma) * (B[i] - mb) for i in range(n))
    den = math.sqrt(sum((A[i] - ma) ** 2 for i in range(n)) *
                    sum((B[i] - mb) ** 2 for i in range(n)))
    return num / den if den else 0.0


BAS = ("  %-26s %7s %7s %7s %7s %7s %6s %5s  %s" %
       ("varyant", "iska_m", "omur_s", "omur90", "az_d/s", "sisme", "gorus",
        "A%", "kazanc (iska / omur)"))


def satir(ad, o, taban=None):
    ek = ""
    if taban is not None:
        ek = "   %+6.2f m %+6.2f s" % (taban["iska"] - o["iska"],
                                       o["omur"] - taban["omur"])
    return ("  %-26s %7.2f %7.2f %7.2f %7.1f %7.2f %6.2f %4.0f%%%s" %
            (ad, o["iska"], o["omur"], o["omur90"], o["az"], o["sisme"],
             o["gorus"], 100 * o["A"], ek))


# ══════════════════════════════════════════════════════════════════════════
#  REJIMLER
# ══════════════════════════════════════════════════════════════════════════
def rejim_kw(ad):
    """tesis : sim/deney.py'nin gordugu tesis, AYNEN (kiyas tabani).
    saha  : + olculen dongu hizi (31.2 Hz), olculen kor pencere (0.47 s) ve
            kumeli tespit kaybi. SAHA sayilarini uretmesi icin kalibre edildi.
    """
    if ad == "tesis":
        return {"hata": HataAyari(), "patlama": None, "kor_s": None, "sure": 14.0}
    if ad == "saha":
        return {"hata": HataAyari(yasa_hz=Saha.YASA_HZ, kamera_hz=Saha.YASA_HZ),
                "patlama": Patlama, "kor_s": Saha.KOR_S, "sure": 10.0}
    if ad == "goruntu":
        # ⚠ VARSAYIMLI rejim: saha + goruntu-hizi kanali acik. Bkz.
        # Patlama.K_GORUNTU. Sonuclari "eger o baginti nedenselse" diye oku.
        class PG(Patlama):
            K_GORUNTU = 1.4
            UZUN_HIZ = 2.10          # rho uydurmasindan sonra omur p50'yi
                                     # 1.45 s'e geri getiren yeniden olcek
        return {"hata": HataAyari(yasa_hz=Saha.YASA_HZ, kamera_hz=Saha.YASA_HZ),
                "patlama": PG, "kor_s": Saha.KOR_S, "sure": 10.0}
    raise SystemExit("bilinmeyen rejim: %s" % ad)


# ══════════════════════════════════════════════════════════════════════════
#  KALIBRASYON — patlama modelinin saha uydurmasi
# ══════════════════════════════════════════════════════════════════════════
def kalibre(n=80):
    """UZUN bilesen omru, KISA bilesen surekliligi belirler; ikisi neredeyse dik."""
    print("KALIBRASYON: Patlama -> saha (omur p50, omur p90, kutulu kare orani, iska)")
    print("  hedef: omur %.2f | omur90 %.2f | gorunur %.2f | iska %.1f m | A %.0f%%"
          % (Saha.OMUR_P50, Saha.OMUR_P90, Saha.GORUNUR, Saha.ISKA_P50, 27.6))
    print("  %5s %5s %5s %5s | %7s %7s %7s %7s %5s" %
          ("u_hiz", "u_sur", "k_hiz", "k_sur", "omur", "omur90", "gorus", "iska", "A%"))
    en, eniyi = 1e9, None
    for uh in (0.8, 1.2, 1.7, 2.4):
        for us in (0.35, 0.50, 0.70):
            for kh in (1.0, 2.0, 3.5):
                for ks in (0.08, 0.14):
                    class P:
                        UZUN_HIZ, UZUN_SURE = uh, us
                        KISA_HIZ, KISA_SURE = kh, ks
                        IYI_YARI = Patlama.IYI_YARI
                    r = parti(n=n, patlama=P,
                              hata=HataAyari(yasa_hz=Saha.YASA_HZ,
                                             kamera_hz=Saha.YASA_HZ),
                              kor_s=Saha.KOR_S, sure=10.0)
                    o = ozet(r)
                    c = (abs(o["omur"] - Saha.OMUR_P50) / Saha.OMUR_P50 +
                         abs(o["omur90"] - Saha.OMUR_P90) / Saha.OMUR_P90 +
                         abs(o["gorus"] - Saha.GORUNUR) / Saha.GORUNUR)
                    if c < en:
                        en, eniyi = c, (uh, us, kh, ks, o)
                    print("  %5.2f %5.2f %5.2f %5.2f | %7.2f %7.2f %7.2f %7.2f %4.0f%%" %
                          (uh, us, kh, ks, o["omur"], o["omur90"], o["gorus"],
                           o["iska"], 100 * o["A"]))
    print("\n  EN IYI: UZUN_HIZ=%.2f UZUN_SURE=%.2f KISA_HIZ=%.2f KISA_SURE=%.2f"
          % eniyi[:4])
    print("          omur %.2f omur90 %.2f gorus %.2f iska %.2f A %.0f%%"
          % (eniyi[4]["omur"], eniyi[4]["omur90"], eniyi[4]["gorus"],
             eniyi[4]["iska"], 100 * eniyi[4]["A"]))


# ══════════════════════════════════════════════════════════════════════════
#  TARAMALAR
# ══════════════════════════════════════════════════════════════════════════
KEST = {
    "fark":   (KFark, {"tau": 0.10}),
    "fark30": (KFark, {"tau": 0.30}),
    "eks25":  (KEks, {"W": 0.25}),
    "eks50":  (KEks, {"W": 0.50}),
    "eks100": (KEks, {"W": 1.00}),
    "ab":     (KAlfaBeta, {"alfa": 0.35, "beta": 0.10}),
    "ab_yum": (KAlfaBeta, {"alfa": 0.15, "beta": 0.02}),
    "atla":   (KAtla, {"W": 0.50}),
    "model":  (KModel, {"W": 0.50}),
    "piksel": (KPiksel, {"W": 0.50}),
}


def _kest(ad, yavas=False):
    """Kestirimci fabrikasi.

    yavas=True: AYNI ailenin uzun pencereli (W=1.0 / tau=0.6) surumu. Sabit
    kerteriz yalniz ISARET kullandigi icin isareti bu yavas kestirim verir —
    boylece 'hangi kestirimci' sorusu CB varyantlarinda da anlamli olur.
    """
    sinif, kw = KEST[ad]
    kw = dict(kw)
    if yavas:
        if "W" in kw:
            kw["W"] = 1.0
        if "tau" in kw:
            kw["tau"] = 0.6
        if "alfa" in kw:
            kw["alfa"], kw["beta"] = 0.10, 0.01
    return sinif(**kw)


def _kos(n, rejim, cfg, yatay, fkw, kad):
    kw = rejim_kw(rejim)
    return ozet(parti(n=n, yatay=yatay, yasa_kw=fkw, kest=_kest(kad),
                      kest_yavas=_kest(kad, yavas=True), cfg=cfg, **kw))


def tarama_lam(n, rejim, cfg):
    """[2] lam kestirimci taramasi — YASA SABIT, yalniz kestirim degisir.

    Iki yasada birden kosulur: PN (lam'in BUYUKLUGUNU kullanir) ve
    CB15 (lam'in yalniz ISARETINI kullanir). Hangi yasanin hangi kestirime
    duyarli oldugu boyle ayrisir.
    """
    for ad_y, f, fkw in (("PN1.6", y_pn, {"N": 1.6}),
                         ("CB15", y_cb, {"lead_deg": 15.0})):
        print("\n[2] LAM KESTIRIMCI TARAMASI - yasa = %s" % ad_y)
        print(BAS)
        taban = None
        for ad in ("fark", "fark30", "eks25", "eks50", "eks100", "ab", "ab_yum",
                   "atla", "model", "piksel"):
            o = _kos(n, rejim, cfg, f, fkw, ad)
            if taban is None:
                taban = o
                print(satir(ad_y + "/" + ad, o))
            else:
                print(satir(ad_y + "/" + ad, o, taban))


DENEYLER = [
    ("MEVCUT (yasa, PN N=1.6)", y_yasa, {}, "eks25"),
    ("saf takip",              y_saf,  {}, "eks25"),
    ("PN N=1.6",               y_pn,   {"N": 1.6}, "eks50"),
    ("PN N=3.0",               y_pn,   {"N": 3.0}, "eks50"),
    ("PN N=1.6 FOV-sinirli",   y_pn_fov, {"N": 1.6, "pay_deg": 8.0}, "eks50"),
    ("PN N=3.0 FOV-sinirli",   y_pn_fov, {"N": 3.0, "pay_deg": 8.0}, "eks50"),
    ("PN N=1.6 + model-yaw",   y_pn,   {"N": 1.6}, "model"),
    ("CB lead  5 deg",         y_cb,   {"lead_deg": 5.0}, "eks100"),
    ("CB lead 10 deg",         y_cb,   {"lead_deg": 10.0}, "eks100"),
    ("CB lead 15 deg",         y_cb,   {"lead_deg": 15.0}, "eks100"),
    ("CB lead 20 deg",         y_cb,   {"lead_deg": 20.0}, "eks100"),
    ("CB lead 25 deg",         y_cb,   {"lead_deg": 25.0}, "eks100"),
    ("CB lead 35 deg",         y_cb,   {"lead_deg": 35.0}, "eks100"),
    ("CB aspect(w/h) turetme", y_cb_asp, {}, "eks100"),
    ("CB15 + PN1.6 duzeltme",  y_cb_pn, {"lead_deg": 15.0, "N": 1.6}, "eks50"),
    ("CB15 + model-yaw",       y_cb,   {"lead_deg": 15.0}, "model"),
    ("CB15 + piksel isaret",   y_cb,   {"lead_deg": 15.0}, "piksel"),
    ("SESSIZ BURUN K=0.7",     y_saf_sessiz, {"K": 0.7}, "eks50"),
    ("SESSIZ BURUN K=0.5",     y_saf_sessiz, {"K": 0.5}, "eks50"),
    ("SESSIZ BURUN K=0.3",     y_saf_sessiz, {"K": 0.3}, "eks50"),
    ("SESSIZ BURUN K=0.15",    y_saf_sessiz, {"K": 0.15}, "eks50"),
    ("burun = hiz vektoru",    y_saf_burun_v, {}, "eks50"),
    ("CB10 + sessiz K=0.3",    y_cb_sessiz, {"lead_deg": 10.0, "K": 0.3}, "eks100"),
]


def tarama_omur(n, rejim, cfg):
    """[3] KOR PENCERE DUYARLILIGI — faz omru uzarsa yasa fark etmeye baslar mi?

    NEDEN: mevcut kor pencere OLCULEN 0.47 s. Yasanin yapabilecegi her sey bu
    sureye sigmali. ab_omur.py sahada KAYIP_M 20->30 denedi (omur 1.24->1.49).
    Burada pencerenin yasalar arasi farki NE ZAMAN acmaya basladigi olculur.
    """
    kw = dict(rejim_kw(rejim))
    kw["sure"] = 16.0
    print("\n[3] KOR PENCERE (kor_s) DUYARLILIGI - iska_m / omur_s")
    ad_y = [("saf takip", y_saf, {}, "eks25"),
            ("PN N=1.6", y_pn, {"N": 1.6}, "eks50"),
            ("CB 10 deg", y_cb, {"lead_deg": 10.0}, "eks100"),
            ("sessiz burun K=0.3", y_saf_sessiz, {"K": 0.3}, "eks50")]
    print("  %7s | %s" % ("kor_s", " ".join("%20s" % x[0] for x in ad_y)))
    for kor in (0.47, 0.70, 0.94, 1.50, 2.50):
        kw["kor_s"] = kor
        hu = []
        for _, f, fkw, kad in ad_y:
            o = ozet(parti(n=n, yatay=f, yasa_kw=fkw, kest=_kest(kad),
                           kest_yavas=_kest(kad, True), cfg=cfg, **kw))
            hu.append("%9.2f m %7.2f s" % (o["iska"], o["omur"]))
        print("  %7.2f | %s" % (kor, " ".join(hu)))


ONAY = [
    ("MEVCUT (yasa, PN1.6)", y_yasa, {}, "eks25"),
    ("saf takip (PN kapali)", y_saf, {}, "eks25"),
    ("PN N=1.6", y_pn, {"N": 1.6}, "eks50"),
    ("CB lead 10 deg", y_cb, {"lead_deg": 10.0}, "eks100"),
    ("sessiz burun K=0.3", y_saf_sessiz, {"K": 0.3}, "eks50"),
    ("CB10 + sessiz K=0.3", y_cb_sessiz, {"lead_deg": 10.0, "K": 0.3}, "eks100"),
]


def _onyukleme(v, B=400, tohum=7):
    r = random.Random(tohum)
    n = len(v)
    s = sorted(st.median([v[r.randrange(n)] for _ in range(n)]) for _ in range(B))
    return s[int(0.05 * B)], s[int(0.95 * B)]


def onay(n=400):
    """[4] KARAR TABLOSU: az sayida aday, cok angajman, ONYUKLEME araligiyla.

    Iki kor pencerede kosulur: OLCULEN 0.47 s ve KAYIP_M'i iki katina cikaran
    0.94 s. Ilkinde hicbir yasa farki anlamli degil; ikincisinde yasa ANLAMLI
    olmaya basliyor. Karar bu tablodan verilir.
    """
    for kor in (0.47, 0.94):
        kw = dict(rejim_kw("saha"))
        kw["kor_s"] = kor
        kw["sure"] = 16.0
        print("\n[4] KARAR TABLOSU - kor pencere %.2f s, n=%d  "
              "(medyan [%%90 onyukleme araligi])" % (kor, n))
        print("  %-24s %-22s %-22s %8s" %
              ("varyant", "iska_m", "omur_s", "az d/s"))
        for ad, f, fkw, kad in ONAY:
            r = parti(n=n, yatay=f, yasa_kw=fkw, kest=_kest(kad),
                      kest_yavas=_kest(kad, True), **kw)
            e = [x["iska"] for x in r]
            o = [x["omur"] for x in r]
            az = [x["az_hizi"] for x in r if x["az_hizi"]]
            ce, co = _onyukleme(e), _onyukleme(o)
            print("  %-24s %6.2f [%5.2f %5.2f]  %6.2f [%5.2f %5.2f] %8.1f" %
                  (ad, st.median(e), ce[0], ce[1],
                   st.median(o), co[0], co[1], st.median(az)))


def rho_uydur(n=200):
    """Goruntu-hizi kanalinin K'sini sahanin rho = -0.679'una uydurur."""
    kw = rejim_kw("saha")
    print("GORUNTU-HIZI KANALI: K'yi saha bagintisina uydur (hedef rho -0.679)")
    print("  %5s %6s | %7s %7s %7s %7s" %
          ("K", "u_hiz", "rho", "omur", "omur90", "iska"))
    for K, uh in ((0.0, 2.40), (0.7, 2.30), (1.0, 2.20), (1.4, 2.10),
                  (2.0, 1.90), (2.8, 1.70)):
        class PG(Patlama):
            K_GORUNTU = K
            UZUN_HIZ = uh
        kw2 = dict(kw)
        kw2["patlama"] = PG
        r = parti(n=n, yatay=y_pn, yasa_kw={"N": 1.6}, kest=_kest("eks50"),
                  kest_yavas=_kest("eks50", True), **kw2)
        r = [x for x in r if x["az_hizi"]]
        o = ozet(r)
        print("  %5.1f %6.2f | %+7.3f %7.2f %7.2f %7.2f" %
              (K, uh, spearman([x["az_hizi"] for x in r], [x["omur"] for x in r]),
               o["omur"], o["omur90"], o["iska"]))


def tarama_ana(n, rejim, cfg):
    print("\n[1] ANA YASA KARSILASTIRMASI")
    print(BAS)
    ref = None
    for ad, f, fkw, kad in DENEYLER:
        o = _kos(n, rejim, cfg, f, fkw, kad)
        if ref is None:
            ref = o
            print(satir(ad, o))
        else:
            print(satir(ad, o, ref))
    return ref


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=80)
    ap.add_argument("--rejim", default="hepsi",
                    choices=("tesis", "saha", "goruntu", "hepsi"))
    ap.add_argument("--grup", default="hepsi",
                    choices=("hepsi", "ana", "lam", "omur"))
    ap.add_argument("--kalibre", action="store_true")
    ap.add_argument("--rho", action="store_true",
                    help="goruntu-hizi kanalinin K'sini saha rho'suna uydur")
    ap.add_argument("--onay", action="store_true",
                    help="karar tablosu: 6 aday, cok angajman, guven araligi")
    a = ap.parse_args()

    kirli = T.dogrula(sessiz=True)
    assert not kirli, "TESIS OZ-SINAMASI BASARISIZ: %s" % kirli
    print("tesis.dogrula(): temiz")

    cfg = IB.Cfg
    print("Cfg: PN_N=%.2f PENCERE=%.2f BURUN_LOS=%s V_MAX=%.1f MAX_ACCEL=%.1f "
          "YAW_HIZALA=%.3f" % (cfg.PN_N, cfg.PN_PENCERE_S, cfg.BURUN_LOS,
                               cfg.V_TOPLAM_MAX, cfg.MAX_ACCEL, cfg.YAW_HIZALA_S))

    if a.kalibre:
        kalibre(n=max(a.n, 60))
        return
    if a.rho:
        rho_uydur(n=max(a.n, 150))
        return
    if a.onay:
        onay(n=max(a.n, 200))
        return

    rejimler = ("tesis", "saha", "goruntu") if a.rejim == "hepsi" else (a.rejim,)
    for rj in rejimler:
        print("\n" + "=" * 108)
        print("REJIM: %s   (n=%d angajman)" % (rj.upper(), a.n))
        if rj == "goruntu":
            print("  !! VARSAYIMLI REJIM - saha + goruntu-hizi kanali (K=%.1f)."
                  " Bkz. Patlama.K_GORUNTU." % 1.4)
        if rj in ("saha", "goruntu"):
            print("  dongu %.1f Hz (OLCULDU) | kor pencere %.2f s (OLCULDU) | "
                  "patlama uzun %.2f/s x %.2fs, kisa %.2f/s x %.2fs"
                  % (Saha.YASA_HZ, Saha.KOR_S, Patlama.UZUN_HIZ,
                     Patlama.UZUN_SURE, Patlama.KISA_HIZ, Patlama.KISA_SURE))
            print("  SAHA hedefi: iska %.1f m | omur %.2f s (p90 %.2f) | "
                  "gorunur %.2f | A %.0f%%"
                  % (Saha.ISKA_P50, Saha.OMUR_OLC, Saha.OMUR_P90,
                     Saha.GORUNUR_OLC, 27.6))
        print("=" * 108)
        if a.grup in ("hepsi", "ana"):
            tarama_ana(a.n, rj, cfg)
        if a.grup in ("hepsi", "lam"):
            tarama_lam(a.n, rj, cfg)
        if a.grup in ("hepsi", "omur"):
            tarama_omur(a.n, rj, cfg)


if __name__ == "__main__":
    main()

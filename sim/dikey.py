# -*- coding: utf-8 -*-
"""
================================================================================
  DIKEY NISAN  --  temas icin dikey ekseni cevrimdisi olc  (sim/ altinda)
================================================================================
SORU
--------------------------------------------------------------------------------
Hedefe 1.3-1.9 m'ye kadar yaklasip DEGMIYORUZ. Iskanin baskin bileseni DIKEY.
Bu dosya dikey nisan YAPILARINI (a/b/c/d) TUM senaryolara karsi kiyaslar ve
ANA OLCUT olarak CPA anindaki DIKEY AYRIMI ve CARPISMA ORANINI olcer.

⚠ Oyun/sunucu/yasa dosyalarina DOKUNULMADI. Yalniz bu dosya yenidir.
⚠ (c) secenegi GERCEK kodu cagirir: bbox_ibvs.komut(..., terminal=True).

================================================================================
 SAHA OLCUMU — bu dosyanin hedefi (bagimsiz yeniden olculdu, 2026-08-17)
================================================================================
veri/hedef_iz/*.csv son 6 kayit, 3B mesafe yerel minimumlari (100 yakin gecis):

    3B<2.0 m  n=17 | yatay medyan 0.60 | DIKEY medyan -1.29 m
    3B<2.5 m  n=26 | yatay medyan 1.20 | DIKEY medyan -1.30 m
    3B<3.0 m  n=34 | yatay medyan 1.44 | DIKEY medyan -1.32 m
    3B<4.0 m  n=49 | yatay medyan 1.89 | DIKEY medyan -1.34 m
    3B<6.0 m  n=100| yatay medyan 3.86 | DIKEY medyan -1.36 m
    100 gecisin 97'sinde hedefin ALTINDAYIZ.

⭐ ASIL KANIT BURADA: yatay ayrim 3.86 -> 0.60 m'ye inerken (6.4 KAT) dikey
   ayrim 1.36 -> 1.29 m'de KIMILDAMIYOR (%5). Yani dikey bilesen bir DENETIM
   HATASI DEGIL, GEOMETRIK TABAN. Nisan iyilestikce yatay kapaniyor, dikey
   kapanmiyor. Bu, "bilerek konmus sabit ofset" imzasidir.
   Ongorulen taban: RANGE_SET 6 m x sin(ISTASYON_ELEV 15°) = 1.553 m.
   Olculen 1.30 m = ongorunun %84'u (tirmanma yasasi ofseti kismen kapatiyor
   ama TAMAMLAYAMIYOR -- bu dosyanin olctugu sey tam olarak bu).

================================================================================
 ⚠ TEZGAH KUSURLARI — bu dosya DIKEY EKSENDE UC YENI TANE BULDU
================================================================================
Tesis gecmiste UC (isaretli roll / yanlis odak / ters dikey isaret), trail.py
UC daha (kutu yuksekligi 2.23x, kutu gurultusu yok, kilit hic olculmemis)
kusur uretti. Dikey ekseni sormadan once zinciri yeniden denetledim:

(7) GOVDE PITCH TRIMI MODELLENMIYOR — DIKEY EKSENIN EN BUYUK KUSURU.
    tesis.Avci.pitch YALNIZ ileri ivmeden turetilir (`-atan2(a_ileri,g)*0.5`)
    ve SABIT HIZDA SIFIRDIR. OLCULEN gercek:
        gps_guidance_*.csv, iris_pitch_deg, hiz kusaklarina bolunmus (n=7569):
            4-6 m/s  -12.6°   |  12-14 m/s -14.8°  |  22-24 m/s -14.6°
            6-8      -14.1    |  14-16     -14.5   |  30-34     -15.0
        yani pitch HIZDAN NEREDEYSE BAGIMSIZ, SABIT ~-14.5° (burun ASAGI).
        BAGIMSIZ DOGRULAMA: kopru/entegre.py:153 "ucus logu 113105, 31164
        seyir tiki: govde pitch seyirde ort -13.3°".
    NEDEN OLDURUCU: kamera GOVDEYE vidali (25° yukari). Etkin bakis yukselisi
    = TILT + pitch = 25 - 13.3 = +11.7°, tezgahin sandigi +25° DEGIL.
    Butun dikey kadraj/kilit sinirlari 13.3° kayiyor:
        tezgah (pitch=0)   : hedefin USTUNDE en cok 20.5° (kadraj), 14.1° (kilit)
        OLCULEN (pitch=-13.3): USTUNDE 33.8° (kadraj), 27.4° (kilit)
    ⭐ SONUC: "kamera yukari bakiyor, o yuzden ALTTAN gitmek ZORUNDAYIZ"
    gerekcesi OLCULEN pitch ile COK ZAYIFLIYOR. Dikey ofseti sifirlamak
    kadraji da sartname kilidini de BOZMUYOR (bu dosyada olculdu).

(8) DIKEY IVME SINIRI YOK — dikey kanal 5 KAT FAZLA CEVIK.
    tesis.Avci dikeyde yalniz birinci mertebe gecikme (tau 0.211) ve vz
    clamp'i uygular; ivme clamp'i SADECE YATAYA konmus. Sonuc: 3 m/s'lik
    dikey basamak 3/0.211 = 14.2 m/s^2 ile uygulaniyor.
    OLCULEN (kopru_tani_*.csv, vz_up_sdk, 0.5 s pencere, n=191438):
        |a_z| p50 0.41 | p90 2.10 | p95 2.95 | p99 4.22 m/s^2
    Yani gercek surdurulebilir dikey ivme ~3 m/s^2. Tezgah 4.8 KAT abartiyordu.
    NEDEN OLDURUCU: "son N metrede ofseti sifirla" sorusunun CEVABI dogrudan
    bu sayidir. 1.55 m'yi kapatmak a=3 ile 2*sqrt(d/a) = 1.44 s ister;
    a=14.2 ile 0.66 s. Kusurlu tezgah "6 m esik yeter" derdi, gercek "yetmez".

(9) CPA ORNEKLEME ILE OLCULEMEZ.  Onceki tezgahlar en yakin menzili
    `min(R_i)` ile buluyordu. 62 Hz'de ve 6 m/s bagil hizda adim 0.10 m,
    24 m/s'lik yandan gecisde 0.39 m. Olculecek sey 0.9 m esigi olunca bu
    %43'e varan yanlilik demektir. Burada CPA her adimda BAGIL KONUM
    DOGRU PARCASI uzerinde ANALITIK cozulur (dogrula #4 bunu sinar).

⚠ BULUNAN DORDUNCU KUSUR BASKA BIR TEZGAHTA (arac/dpp_senaryo.py):
    O dosya senaryolarini "GERCEKCI bant" diye 0-4 °/s uzerine kurmus ve
    gerekce olarak "OLCULDU: medyan 0.4 °/s, p95 3.1" yaziyor (satir 74-84).
    AMA AYNI DOSYANIN gercek_yorunge() docstring'i (satir 118-120) "tekrar
    eden satirlar atilmazsa turev yikanir; ilk olcumumde 6.1 yerine 0.4
    bulmamin sebebi tam olarak buydu" diyor. Yani senaryo listesi, dosyanin
    KENDI belgeledigi OLCUM ARTIFAKTINA gore kurulmus.
    YENIDEN OLCTUM (veri/hedef_iz son 6 kayit, tekrar satirlar atilmis,
    n=118156): p50 6.55 | p75 20.0 | p90 32.0 | p95 38.7 | p99 53.3 °/s;
    zamanin %25.0'i >20 °/s, %42.6'si <5 °/s. Gorevde verilen 6.1/34.4/
    %29/%46 ile birebir. dpp_senaryo'nun "gercekci" bandi gercegin 1/8'i.

================================================================================
 KIYASLANAN DIKEY NISAN YAPILARI
================================================================================
Yatay kanal ve kestirim TUM yapilarda AYNI (tek degisken kurali). Fark yalniz
vz komutunu ureten yasadadir.

 (a) SABIT      : bugunku hal. dz_hedef = -min(R,R_SET)*sin(ISTASYON_ELEV)
                  (gps_guidance.py:587-609 birebir; r_eff = min(menzil,R_SET))
 (b) TERM_DIKEY : (a) + menzil esigin altinda yukselis dogrusal olarak sifire
                  surulur (gps_guidance.py:603-606'daki YENI knob).
 (c) KESISIM    : GERCEK bbox_ibvs.komut(..., terminal=True) cagrilir; vz'si
                  alinir (vz = -v*tan(nisan_elev) + K_VZ_D sonumlemesi).
                  Tetikleme menzili taranir (kodda kapi kutu boyutunda).
 (d) TGO        : ONERI. Nisan kaydirmasi MENZILE degil KALAN SUREYE baglanir
                  ve dikey kapanma sifir-caba-iskasi (ZEM) / t_go ile surulur.
 (e) MERKEZ     : ofset HIC yok (dogrudan hedefin merkezine). Ust sinir olcumu.

================================================================================
 ⭐ SONUC — TEZGAHTA OLCULDU (10 senaryo x 5 aspect x 4 tohum = 200/yapi)
================================================================================
                        CARP%  |dz|50  |dz|90  dz50(isaretli)
  (a) sabit 15 [BUGUN]   16%    1.18    2.32     -1.12   <- SAHA 1.29 ile ORTUSUR
  (b) TERM_DIKEY  6 m    25%    1.00    2.20     -0.84
  (b) TERM_DIKEY  8 m    30%    0.79    1.98     -0.60
  (b) TERM_DIKEY 12 m    34%    0.69    1.98     -0.45
  (b) TERM_DIKEY 20 m    34%    0.60    1.65     -0.40
  (c) kesisim R<8  m     36%    0.52    1.71     -0.24
  (c) kesisim R<16 m     37%    0.47    1.49     -0.25
  (c) kesisim R<30 m     36%    0.38    1.56     -0.18
  (d)  t_go TEK tetik    36%    0.68    1.67     -0.38
  (D)  t_go 3.0 + R 14m  38%    0.54    1.51     -0.14   <- ONERI
  (e) merkez (ofsetsiz)  38%    0.32    1.36     -0.08

 ⚠ BU TABLO TEK BASINA YANILTIR. Tezgah tespiti YALNIZ kutu boyutuna
 baglar; hedefin ARKA PLANINI (alttan gokyuzu / ustten yer karmasasi)
 modellemez, yani "ofseti tamamen kaldir" secenegini YAPISAL OLARAK
 KAYIRIR. Ceza parametre yapilip tarandi (arka_plan=alttan/ustten tespit
 orani); KIRILMA NOKTASI acik:

   arka plan cezasi:      1.0    0.5      kadraj ici (ceza 0.5)   |dz|90
   (a) sabit 15           16%    17%          80%                  1.71
   (b) TERM_DIKEY 12      34%    30%          77%                  1.66
   (c) kesisim R<16       37%    38%          78%                  1.45
   (d) t_go TEK tetik     36%    44%          79%                  1.46
   (D) t_go 3.0 + R 14 m  38%    43%          79%                  1.33  <- ONERI
   (e) merkez             38%    41%          66%  <- COKUYOR      1.54

 ⭐ KAZANAN YAPI (D): ofseti hem KALAN SUREYE hem MENZILE bagla (OR),
 ve dikey kapanmayi ZEM/t_go ile sur. Sebep tek satirda: TEK YAPI O ki
 hem ofsetin gorsel faydasini uzakta korur, hem de tezgahin OLCEMEDIGI
 arka plan etkisine karsi DUYARSIZDIR (%38-43, ceza ne olursa olsun),
 hem de |dz| kuyrugunu (p90) en cok kisan yapidir.

 ⚠ IKI TETIK NEDEN SART (tezgahta gorulen ariza): tek basina t_go,
 KUYRUK TAKIBINDE kor kalir — arkasina oturunca kapanma hizi 0'a yakinsar,
 t_go 20-40 s'e cikar ve cizelge HIC erimez (tek angajman dokumunde
 dz_ist temasa kadar -1.55 m'de kaldi). Tek basina MENZIL ise KARSIDAN
 gecise kor kalir. OR'lanmis hali ikisini birden kapatir.

 ⭐ ASPECT KIRILIMI — (D)'nin ASIL GEREKCESI (arka plan cezasi 0.5):
   yapi              asp0   asp45  asp90  asp135  asp180
   (a) sabit 15      30%    32%    20%     2%      0%
   (b) TERM_DIKEY 12 50%    50%    20%    30%      0%
   (c) kesisim R<16  58%    68%    30%    38%      0%
   (d) t_go tek      52%    58%    35%    40%     32%
   (D) t_go + menzil 62%    50%    28%    42%     32%   <- her yerde calisir
   (e) merkez        60%    42%    40%    30%     32%
 KARSIDAN (aspect 180) kapanma 36-42 m/s. MENZIL esikli her yapi (a/b/c)
 orada SIFIR verir: 30 m'lik esik bile yalniz 0.8 s birakir ve dikey kanal
 (a_z 3 m/s^2) 1.55 m'yi 1.44 s'den once kapatamaz. t_go esigi 3.0 s ise
 o geometride ~110 m'ye denk gelir ve zamaninda baslar. Bu, MENZIL ESIGININ
 YAPISAL KUSURUDUR, ayar kusuru degil.

 ⭐ BAGLAYAN LIMIT DIKEY IVME, DIKEY HIZ DEGIL (tarandi):
   a_z tavani   1.5    3.0(OLCULEN)   5.0    10.0   ->  (d) |dz|50
                0.99      0.74        0.49   0.37
   vz tavani    2.0      3.0          5.0           ->  (d) |dz|50
                0.72     0.74         0.74
 VZ_MAX'i buyutmek ISE YARAMAZ; dikey IVME yetkisi (Copter WPNAV_ACCEL_Z)
 buyutmek |dz|'yi neredeyse YARIYA indirir.

 ⭐ SARTNAME KILIDININ BEDELI YOK (tutus rejimi, yatay taahhut kapali,
   acisal kapi DUZELTILDIKTEN sonra — bkz. kusur 10):
     (a) sabit 15   5s kilit %59  kadraj %93   dz -1.11
     (b) esik 12    %66           %93          dz -0.61
     (d*) t_go      %57           %93          dz -1.18
     (e) merkez     %64           %93          dz +0.01   <- ofsetsiz DAHA IYI
     hedefin 2 m USTUNDE  %53     %87          dz +1.52   <- USTE cikmak KOTU
   Yani asimetri GERCEK (uste cikmak kotu) ama dz=0 ceza uretmiyor.

 ⭐ NEREDE BOZULUYOR
   * HIZ ORANI: v_max 19 (mu=0.95) -> hepsi cokuyor
     (a) %11, (b8) %13, (d) %6; angajman tamamlama %82 -> %66.
     (d) burada EN COK zarar goren: kapanma hizi kucukse t_go patlar.
   * DEVIR MENZILI (gorsel faza teslim menzili) — ⭐ EN GUCLU DEGISKEN:
     R0=13 m: (a) %9  |dz| 1.42 | (b8) %22 1.25 | (d) %18 1.35
     R0=20 m: (a) %16 1.15       | (b8) %28 0.76 | (d) %27 1.06
     R0=33 m: (a) %11 1.08       | (b8) %26 0.73 | (d) %29 0.34
     13 m'de teslim alinca hicbir yapi dikeyi kapatamiyor: Vc~4 m/s'de
     13 m = 3.2 s, dikey kapanma ihtiyaci 1.44 s + gecikme ~0.5 s ve
     yatay hucum da ayni sureyi istiyor. Zarchan'in (1998) "cozunurluk
     sonrasi kalan sure / zaman sabiti >= 10" kurali ile ayni yon.
   * HEDEF MANEVRASI: 35 °/s ve zikzak. Ama bu DIKEY degil EDINIM arizasi:
     angajman tamamlama don35 %55, zikzak %30 (digerleri %90-100).
     35 °/s icin gereken yanal ivme V*om = 11.0 m/s^2, MAX_ACCEL 12'ye
     dayaniyor -> hedef kadrajdan cikiyor, kestirim hayalete kayiyor.
   * ASPECT: 135° ve 180°. 180'de MENZIL esikli her yapi SIFIR.

 ⭐ TEZGAH KUSURLARININ SONUCA ETKISI (ablasyon — bu dosyanin en onemli
   dogruluk beyani):
     yapi                      CARP%   |dz|50
     (d) OLCULEN tezgah         27%     0.64
     (d) dikey ivme siniri YOK  33%     0.33   <- ESKI tezgah (d)'yi 1.9 KAT
     (d) pitch trimi YOK        29%     0.69      IYI gosteriyordu
     (d) ikisi de YOK           32%     0.32
   Yani DUZELTMESEYDIM "t_go yasasi 0.33 m dikey ayrim veriyor" diye
   rapor edecektim; olculen dikey ivme ile gercek 0.64 m.
   ⚠ Ayrica: OLCUM HATASI KAPALI iken (a) %47 / (b8) %57 / (d) %65 ve
   (d)'nin dikey ayrimi 0.15 m. YAPI YETERLI; sinirlayan ALGI.

 ⚠ GOREV METNINDEKI BIR SAYI DUZELTILDI: "TERMINAL neredeyse hic
   atesleniyor (%0.2)". Son 200 bbox_ibvs kaydinda (n=18854 satir)
   durum dagilimi: IBVS %65.5, TERMINAL %23.4, TERM_KOR %6.3,
   KUTU_YOK %4.7. Yani terminal kapisi GORSEL FAZDA duzenli aciliyor;
   %0.2 rakami TUM guduum tikleri icinde gorsel fazin kucuk olmasindan
   geliyor. Dolayisiyla (c)'nin degeri "kapi hic acilmiyor" degil,
   "kapi 8.1 m'de aciliyor" (TERMINAL_BOYUT 25 px / MENZIL_PX_M 202.6);
   16-30 m'ye cekmek olculen kazanci veriyor.

================================================================================
 LITERATUR — TEZGAHTAN BAGIMSIZ DOGRULAMA / CELISKI
================================================================================
 CELISEN (sabit ofseti terminale tasimaya KARSI):
 * Palumbo/Blauwkamp/Lloyd, JHU APL Tech Digest 29(1):25-41 ve 42-59 (2010).
   "Modern Homing Missile Guidance": ZEM tanimi ve "Intercept is achieved at
   tgo = 0 in each case, since the ZEM goes nearly to zero."
   "Basic Principles": handover hatasi ayristirmasi — "the miss distance that
   must be removed by the interceptor after transition to terminal homing is
   contained in e_perp" (LOS'a DIK bilesen). 15° ofset tam olarak e_perp'tir.
 * Zarchan, Science & Global Security 8:99-124 (1998). Hit-to-kill'de nisan
   noktasi kaymasi: "the ratio of the time left after warhead resolution to
   the guidance system time constant must be at least ten". Ve geç kayma
   felaket: 0.2 s kala duzeltmek "not only to miss the warhead but also the
   missile itself" ile sonuclanabiliyor.
   -> Bizim karsiligimiz: ofset sifirlama suresi >= 10 x kapali-cevrim zaman
      sabiti. tau ~ 0.26 s -> ~2.6 s. TERM_DIKEY_M=6 m, Vc=4 m/s'de 1.5 s:
      KURALIN ALTINDA. t_go esigi 3.0 s ise kurali SAGLIYOR.
 * Kim/Lee/Tahk (KAIST), CEAS EuroGNC 2022, paper CEAS-GNC-2022-040.
   Midcourse'un terminale teslim kosulu acikca sigma(tf)=0 (bakis acisi
   hatasi SIFIR teslim edilir), PIP + FOV kisitlariyla birlikte.
 * Kane & Zamani, J Exp Biol 217:225-234 (2014), PMC3898623. GERCEK bir
   strapdown arayici (sahin, sabit fovea): uzak takipte yatay -8.8°,
   DIKEY +2.4°; 8 m'nin ICINDE yatay -2.8°, DIKEY 0.0 +- 0.3°.
   -> Ofset midcourse'ta TASINIR, terminalde COKER. Bizim (d) yapimizin
      tam profili; bugunku (a) bunun TERSI.
 * MDPI Drones 10(6):420 (2026), drone-on-drone kinetik yakalama: fiziksel
   temas icin "sub-meter terminal guidance precision"; olculen hata "below
   0.4 m in all axes". Pliska ve ark., IEEE RA-L 9(10) 2024 (arXiv:2405.13542):
   yakalama dogrulugu 0.16 m (statik) / 0.99 m (5 m/s hedef).
   Yan ve ark. arXiv:2409.17497: IBVS+PNG, strapdown, CEP 0.089 m.
   -> Bizim 1.30 m'lik dikey ayrimimiz bu literaturun 3-8 KATI disinda.
 * Yang/Bai/She/Quan, arXiv:2404.08296 (2024) — strapdown kamerali cok
   pervaneli onleyici: "Due to the strapdown camera configuration, the
   rotation matrix R_c^b is constant" ve tasarlanan LOS "is crafted to
   approximate the force vector n_f as closely as possible within the FOV".
   -> Sabit 25° tilt aim hesabindan SABIT DONUSUMLE cikarilir; nisan
      goruntu merkezine degil HIZ/KUVVET vektorune yapilir. Bizim
      CY_NISAN semamiz bunun tersi.
 * Ghose, "Guidance of Missiles", NPTEL/IISc (2012), Modul 6: carpisma
   ucgeni saglanmiyorsa "capture is possible if and only if V_T < V_M".
   Brighton ve ark., J Exp Biol 224 (2021), PMC7938797: dusuk N (~1.2)
   "will tend to keep the attacker flying behind its target" ve kuyruk
   takibi "to tire their prey" ile kazanilir — anlik kinetik temasla degil.
   -> Olculen aspect>150° -> P(<3m)=0.005 bulgusuyla birebir tutarli.

 DESTEKLEYEN (ofsetin bir degeri VAR — ama kosullu):
 * Munir/Siddiqui/Anwar, IEEE-CVF WACV 2024 Workshop, arXiv:2305.16450:
   gokyuzu arka planli kumede mAP50-95 72.0/71.7, karmasik arka planli
   kumede 57.5/59.0. ⚠ Kontrollu A/B degil (ayri veri kumeleri).
   -> Tezgahin modellemedigi tek gercek etki; bu yuzden arka_plan
      parametresi ile TARANDI (yukaridaki kirilma tablosu).
 * Lin & Leonardo, Current Biology 27(8):1124-1137 (2017): yusufcuk avi
   TEPEDE tutar, "the loss of prey fixation or overhead positioning during
   flight is strongly correlated with terminated flights". ⚠ AMA bu
   YAKLASMA GEOMETRISIDIR; nisan avin ALTINA degil AVA yapilir.
 * US SIR H400 (US Army, 1987/88), "Aimpoint bias for terminal homing
   guidance": kasitli nisan kaydirmasi carpismaya kadar korunabilir —
   ⚠ ama ofset hedefin USTUNDEKI baska bir noktaya, BOSLUGA degil.
 * Pliska ve ark. (RA-L 2024): govde hedefin USTUNDEN gecer, dikey ofset
   korunur — ⚠ ofset tam olarak ASILI AGIN sarkma mesafesidir.
   -> KURAL: korunabilir ofset = referans noktasindan EFEKTORE olan vektor.
      Bizim efektorumuz govdenin kendisi (kanat vurusu) -> mesru ofset SIFIR.

 KAYNAK YOK: PAC-3/THAAD/EKV'nin nisan noktasi secim algoritmasi acik
 literaturde bulunamadi. Aspect acisi <-> vurus olasiligi icin yayimlanmis
 nicel egri bulunamadi (bizim 869 angajmanlik olcumumuz daha spesifik).

================================================================================
 CALISTIR
    python sim/dikey.py --dogrula     # oz-sinama (once bu)
    python sim/dikey.py --sadakat     # tezgah sahayi yeniden uretiyor mu
    python sim/dikey.py --kiyas       # a/b/c/d/e x tum senaryolar
    python sim/dikey.py --tara        # esik/kazanc taramasi
    python sim/dikey.py --limit       # NEREDE BOZULUYOR
    python sim/dikey.py               # hepsi
================================================================================
"""
import os
import sys
import math
import random
import argparse

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)

import tesis as T                                                  # noqa: E402
from tesis import Avci, Olcum, kadraj, F_YASA, CX, CY, HataAyari, Algi  # noqa
from tesis import TX_MAX, TY_MAX                                   # noqa: E402
import trail as TR                                                 # noqa: E402
from trail import Kal, Kutu, Kestirim, los_dunya, _sar             # noqa: E402
from guidance.kilit_sayaci import KilitSayaci, KilitCfg            # noqa: E402


# ══════════════════════════════════════════════════════════════════════════
#  OLCULMUS SABITLER (bu dosyada YENI olculenler — kaynak yorumda)
# ══════════════════════════════════════════════════════════════════════════
class Dik:
    # ── govde pitch trimi (kusur 7) ──
    # gps_guidance_*.csv iris_pitch_deg, hiz kusagi p50'leri: -12.6..-15.0
    # kopru/entegre.py:153 bagimsiz: -13.3 (31164 seyir tiki)
    PITCH_TRIM = -13.3        # derece; burun ASAGI (OLCULDU)
    PITCH_HIZ = 4.0           # m/s; bu hizin altinda trim dogrusal olarak erir
    # ── dikey ivme (kusur 8) ──
    # kopru_tani_*.csv vz_up_sdk, 0.5 s pencere: p90 2.10 p95 2.95 p99 4.22
    AZ_MAX = 3.0              # m/s^2 (OLCULDU p95)
    VZ_MAX = 3.0              # m/s   (Cfg.VZ_MAX gorsel faz; olculen p01/p99
    #                                  -3.39/+2.35 ile tutarli)
    VZ_MAX_TERM = 5.0         # m/s   (Cfg.VZ_MAX_TERM)
    # ── yasadan gelen ayar (guidance/ana_kontrol.py:279, :237) ──
    ISTASYON_ELEV = 15.0      # derece
    RANGE_SET = 6.0           # m
    # ── carpisma olcutu (gorev tanimi) ──
    KANAT = 1.72              # m ; Talon kanat acikligi
    TEMAS = 0.9               # m ; dikey VE yatay bu esigin altinda = carpisma


# ══════════════════════════════════════════════════════════════════════════
#  AVCI — tesis.Avci + OLCULEN pitch trimi + OLCULEN dikey ivme siniri
# ══════════════════════════════════════════════════════════════════════════
class AvciD(Avci):
    """tesis.Avci'nin dikey-dogru surumu.

    ⚠ tesis.py DEGISTIRILMEDI; duzeltme burada, tureyen sinifta.
    pitch_trim=0.0 ve az_max=None verilirse davranis tesis.Avci ile BIT-AYNI
    (gerileme kiyasi/ablasyon icin --limit'te kullaniliyor).
    """

    def __init__(self, *a, pitch_trim=Dik.PITCH_TRIM, az_max=Dik.AZ_MAX, **kw):
        super().__init__(*a, **kw)
        self.pitch_trim = pitch_trim
        self.az_max = az_max

    def adim(self, dt, t):
        vz0 = self.vz
        super().adim(dt, t)
        # ── (8) DIKEY IVME SINIRI ────────────────────────────────────────
        # tesis yalnizca YATAY ivmeyi kisiyor; dikey kanalda 3 m/s'lik
        # basamak 14.2 m/s^2 ile uygulaniyordu. OLCULEN surdurulebilir
        # dikey ivme p95 = 2.95 m/s^2.
        if self.az_max is not None and dt > 1e-9:
            dvz = self.vz - vz0
            sin_ = self.az_max * dt
            if abs(dvz) > sin_:
                # z entegrasyonu super().adim icinde yapildi; farki geri al
                duz = (sin_ if dvz > 0 else -sin_) - dvz
                self.vz += duz
                self.z -= duz * dt          # ⚠ z irtifa, vz NED asagi-pozitif
        # ── (7) GOVDE PITCH TRIMI ────────────────────────────────────────
        # Cok-pervaneli arac ileri gitmek icin burnunu ASAGI egmek zorunda;
        # OLCULEN deger hizdan neredeyse bagimsiz sabit ~-13.3°. tesis'in
        # ivmeden turettigi pitch (sabit hizda 0) UZERINE eklenir.
        s = math.hypot(self.vx, self.vy)
        self.pitch += math.radians(self.pitch_trim) * min(1.0, s / Dik.PITCH_HIZ)


# ══════════════════════════════════════════════════════════════════════════
#  HEDEF — gorevin istedigi TUM senaryolar
# ══════════════════════════════════════════════════════════════════════════
_IZ = None


def gercek_iz():
    """veri/hedef_iz/*.csv -> (T, X, Y, Z). Hedefin KENDI kaydi, model yok.

    ⚠ TEKRAR EDEN SATIRLAR ATILIR. Logger konum degismedikce de yaziyor;
    atilmazsa turev yikanir (donus hizi 6.5 yerine 0.4 °/s cikar — bkz.
    dosya basi, dpp_senaryo kusuru).
    ⚠ OYUN DUNYASI -> tezgah cercevesi: y ISARETI CEVRILIR (dow_kopru.py:49
    NED_y = -DoW_y). z zaten YUKARI. Konum+tutum HAM kalir, yalniz eksen
    isareti duzeltilir.
    ⚠⚠ SUREKLI PARCAYA BOLUNUR — TEZGAH KUSURU OLURDU. Ham kayitta
    zaman BOSLUKLARI ve KONUM SICRAMALARI var (oyun yeniden baslama /
    hedef yeniden dogma / logger duraksamasi). Bolmeden oynatinca dogrusal
    interpolasyon o bosluklari 100+ m/s'lik HAYALET bir hedefe cevirir:
    ilk surumde bu, angajmanlarin menzilini 25 m'den 500 m'ye tasidi ve
    "gercek yorungede yasa cokuyor" diye SAHTE bir bulgu uretti.
    Olcut: ardisik iki ornek arasinda dt<0.5 s VE adim hizi <40 m/s.
    En uzun surekli parca kullanilir.
    """
    global _IZ
    if _IZ is not None:
        return _IZ
    import csv
    import glob
    ys = sorted(glob.glob(os.path.join(KOK, "veri", "hedef_iz",
                                       "hedef_iz_*.csv")), key=os.path.getmtime)
    en_iyi = None
    for y in reversed(ys[-8:]):
        try:
            ham = []
            for r in csv.DictReader(open(y, encoding="utf-8", errors="replace")):
                try:
                    a = float(r["t_mutlak"]); b = float(r["hx_m"])
                    c = -float(r["hy_m"]); d = float(r["hz_m"])
                except Exception:
                    continue
                if ham and b == ham[-1][1] and c == ham[-1][2]:
                    continue
                ham.append((a, b, c, d))
        except OSError:
            continue
        parca = []
        s = []
        for i, p in enumerate(ham):
            if s:
                dt = p[0] - s[-1][0]
                d3 = math.dist(p[1:], s[-1][1:])
                if not (1e-6 < dt < 0.5) or d3 / max(dt, 1e-6) > 40.0:
                    parca.append(s)
                    s = []
            s.append(p)
        parca.append(s)
        for s in parca:
            if len(s) > 2000 and (en_iyi is None or len(s) > len(en_iyi[0])):
                t0 = s[0][0]
                en_iyi = ([p[0] - t0 for p in s], [p[1] for p in s],
                          [p[2] for p in s], [p[3] for p in s],
                          os.path.basename(y))
    _IZ = en_iyi if en_iyi is not None else False
    return _IZ


class HedefD:
    """Hedef yorungesi. Sabit 17.98 m/s; manevra yalniz YON degistirir."""

    SENARYOLAR = ("duz", "don4", "don8", "don15", "don20", "don35",
                  "zikzak", "dikey", "oval", "gercek")

    def __init__(self, senaryo="duz", z=None, hdg=0.0, t0=0.0):
        if senaryo not in self.SENARYOLAR:
            raise KeyError("bilinmeyen senaryo: %r" % senaryo)
        self.senaryo = senaryo
        self.x = self.y = 0.0
        self.z = Olcum.HEDEF_IRTIFA if z is None else z
        self.hdg = hdg
        self.t = 0.0
        self.v = Olcum.HEDEF_HIZ
        self.vz = 0.0
        self._oval = T.Hedef(faz0=0.0) if senaryo == "oval" else None
        if self._oval is not None:
            self._oval.z = self.z
        self._iz = gercek_iz() if senaryo == "gercek" else None
        if self._iz is False:
            raise RuntimeError("gercek iz kaydi bulunamadi (veri/hedef_iz)")
        if self._iz:
            self._tg = float(t0) % self._iz[0][-1]
            self.x, self.y, self.z = self._ara(self._tg)
            nx, ny, _ = self._ara(self._tg + 0.30)
            self.hdg = math.atan2(ny - self.y, nx - self.x)

    def _ara(self, tt):
        Tl, X, Y, Z = self._iz[0], self._iz[1], self._iz[2], self._iz[3]
        tt = tt % Tl[-1]
        lo, hi = 0, len(Tl) - 1
        while lo < hi:
            m = (lo + hi) // 2
            if Tl[m] < tt:
                lo = m + 1
            else:
                hi = m
        i = max(1, lo)
        d = Tl[i] - Tl[i - 1]
        a = 0.0 if d <= 0 else (tt - Tl[i - 1]) / d
        return (X[i - 1] + a * (X[i] - X[i - 1]),
                Y[i - 1] + a * (Y[i] - Y[i - 1]),
                Z[i - 1] + a * (Z[i] - Z[i - 1]))

    def _om_vz(self):
        s, t = self.senaryo, self.t
        if s == "duz":
            return 0.0, 0.0
        if s.startswith("don"):
            return math.radians(float(s[3:])), 0.0
        if s == "zikzak":                       # 4 s'de bir isaret degistirir
            return (math.radians(20.0)
                    * (1.0 if int(t / 4.0) % 2 == 0 else -1.0)), 0.0
        if s == "dikey":                        # +-2 m/s, 8 s periyot
            return 0.0, 2.0 * math.sin(2.0 * math.pi * t / 8.0)
        return 0.0, 0.0

    def adim(self, dt):
        self.t += dt
        if self._iz:
            self._tg += dt
            px, py, pz = self.x, self.y, self.z
            self.x, self.y, self.z = self._ara(self._tg)
            if abs(self.x - px) > 1e-9 or abs(self.y - py) > 1e-9:
                self.hdg = math.atan2(self.y - py, self.x - px)
            self.vz = (self.z - pz) / max(dt, 1e-9)
            n = math.hypot(self.x - px, self.y - py) / max(dt, 1e-9)
            self.v = n if n > 1.0 else self.v
            return
        if self._oval is not None:
            self._oval.adim(dt)
            x, y, z, vx, vy, _ = self._oval.durum()
            self.x, self.y, self.z = x, y, self.z
            self.hdg = math.atan2(vy, vx)
            self.vz = 0.0
            return
        om, vz = self._om_vz()
        self.hdg += om * dt
        self.x += self.v * math.cos(self.hdg) * dt
        self.y += self.v * math.sin(self.hdg) * dt
        self.z += vz * dt
        self.vz = vz

    def durum(self):
        return (self.x, self.y, self.z,
                self.v * math.cos(self.hdg), self.v * math.sin(self.hdg),
                self.vz)


# ══════════════════════════════════════════════════════════════════════════
#  CPA — ORNEKLEME DEGIL, ANALITIK  (kusur 9)
# ══════════════════════════════════════════════════════════════════════════
def t_go_kes(kes, vc_min=1.0, tgo_min=0.30, tgo_max=None):
    """Kalan sure kestirimi. R ve kapanma hizi KESTIRIMDEN gelir.

    ⚠ TGO_MAX SART. Kuyruk takibinde kapanma 0-2 m/s'e iner ve t_go 20-30 s
    olur; ZEM/t_go duzeltmesi o zaman SIFIRA gider (kazanc = N/t_go) ve
    yasa "hedefin dikey hizini esle, konum hatasini yok say" haline duser.
    OLCULDU (ilk surum, kuyruk takibi duz/asp0): dikey ayrim -1.55 m'den
    -4.07 m'ye SURUKLENDI. Tavan konunca uzak rejimde davranis
    kazanci N/TGO_MAX olan bir P denetimine dogal olarak indirgeniyor.
    """
    R = kes.R if kes.R else 6.0
    tg = R / max(-kes.Rdot, vc_min)
    if tgo_max is not None:
        tg = min(tg, tgo_max)
    return max(tgo_min, tg)


def ongoru_yay(kes, t_go):
    """Hedefin t_go sonraki YATAY konumu — ESGUDUMLU DONUS (yay) modeli.

    ⚠ DUZ CIZGI EKSTRAPOLASYONU DONUSTE YETMEZ: hedef 20 °/s doner ve
    t_go 1.5 s ise duz ongoru 30° yanlis yon verir; yay ile 0. OLCULDU
    (ilk surum, duz ongoru): don20/aspect90'da CPA 5.10 m'de takiliyordu,
    yay ongorusuyle kapaniyor. trail.py ayni dersi yatay istasyon icin
    ogrenmisti ("YEREL TEGET"); burada HUCUM fazi icin gerekiyor.
    """
    vx, vy = kes.vT[0], kes.vT[1]
    om = max(-1.2, min(1.2, kes.omega))
    if abs(om) < 1e-4:
        return kes.pT[0] + vx * t_go, kes.pT[1] + vy * t_go
    a = om * t_go
    s, c = math.sin(a), math.cos(a)
    # yay boyunca yer degistirme: (V/om)*[sin a, 1-cos a] hiz cercevesinde
    return (kes.pT[0] + (vx * s - vy * (1.0 - c)) / om,
            kes.pT[1] + (vy * s + vx * (1.0 - c)) / om)


class CPA:
    """Bagil konumun her adim icin DOGRU PARCASI uzerinde en yakin noktasi.

    62 Hz'de ve 24 m/s bagil hizda ornek araligi 0.39 m; olculecek esik 0.9 m.
    Ornekleyerek olcmek %43'e varan yanlilik uretir.
    """

    def __init__(self):
        self.r_onc = None
        self.en_iyi = 1e9
        self.dz = self.yatay = None
        self.t = None
        self.asp = None

    def besle(self, t, r, asp):
        """r = (avci - hedef) bagil konumu, z YUKARI."""
        if self.r_onc is not None:
            r0 = self.r_onc
            d = [r[i] - r0[i] for i in range(3)]
            nn = sum(x * x for x in d)
            s = 0.0 if nn < 1e-18 else -sum(r0[i] * d[i] for i in range(3)) / nn
            s = max(0.0, min(1.0, s))
            rs = [r0[i] + s * d[i] for i in range(3)]
            m = math.sqrt(sum(x * x for x in rs))
            if m < self.en_iyi:
                self.en_iyi = m
                self.dz = rs[2]
                self.yatay = math.hypot(rs[0], rs[1])
                self.t = t
                self.asp = asp
        self.r_onc = tuple(r)

    def carpti(self):
        return (self.dz is not None and abs(self.dz) < Dik.TEMAS
                and self.yatay < Dik.TEMAS)


# ══════════════════════════════════════════════════════════════════════════
#  DIKEY NISAN YASALARI  —  TEK DEGISKEN
# ══════════════════════════════════════════════════════════════════════════
class Dikey:
    """Taban: hedef irtifa ofsetini bir PD ile kovala.

    Cikti: vz_up (yukari-pozitif) komutu. Cagiran NED'e cevirir ve clamp'ler.
    ⚠ Butun yasalar YALNIZ kestirimi (kes) gorur; truth YOK.
    """
    ad = "taban"
    K_Z = 1.0              # 1/s ; irtifa hatasi -> dikey hiz
    ELEV = Dik.ISTASYON_ELEV
    R_SET = Dik.RANGE_SET
    # ── HEDEF DIKEY HIZI ILERI-BESLEMESI: SUZ VE KIS ─────────────────────
    # ⚠ TUM YAPILARDA AYNI (tek degisken kurali).
    # OLCULDU (gercek iz, n=3378): hedefin dikey hizi |vz| p50 0.71,
    # p90 1.45, p99 1.82 m/s; irtifa bandi 10.5 m. Yani Talon PRATIKTE
    # SEVIYELI uciyor. Ama tek-kameradan kestirilen vT_z COK gurultulu:
    # Kestirim._zarf() onu yalnizca ±4 m/s'e kisiyor ve (d) gibi ZEM tabanli
    # yapilar bu terimi N_Z ile CARPARAK kullaniyor.
    # OLCULDU (bu tezgah, ilk surum, duz/asp0): vT_z kestirimi -2.3 m/s
    # gosterirken truth 0 idi -> (d) yasasi vz'yi -3 m/s tavanina yapistirdi
    # ve dikey ayrim -1.55 m'den -3.28 m'ye SURUKLENDI. Yasa degil, ILERI
    # BESLEME GURULTUSU. Suzgec + OLCULEN p99'a kisma bunu kaldirir.
    VT_Z_MAX = 2.0         # m/s ; OLCULEN p99 1.82, max 2.26
    VT_Z_TAU = 0.8         # s   ; ileri-besleme suzgeci

    def __init__(self, **kw):
        self._vtz = 0.0
        for k, v in kw.items():
            setattr(self, k, v)

    def vt_z(self, kes, dt=1.0 / 21.3):
        x = max(-self.VT_Z_MAX, min(self.VT_Z_MAX, kes.vT[2]))
        self._vtz += min(1.0, dt / max(self.VT_Z_TAU, 1e-6)) * (x - self._vtz)
        return self._vtz

    def dz_hedef(self, kes):
        """Hedefe GORE istenen irtifa farki (negatif = ALTINDA)."""
        raise NotImplementedError

    def __call__(self, kes, p, v, ek=None):
        dzh = self.dz_hedef(kes)
        z_ist = kes.pT[2] + dzh
        vz = self.K_Z * (z_ist - p[2]) + self.vt_z(kes, (ek or {}).get("dt", 0.047))
        return max(-Dik.VZ_MAX, min(Dik.VZ_MAX, vz)), dzh


class D_SABIT(Dikey):
    """(a) BUGUNKU HAL — sabit yukselis acisi.

    gps_guidance.py:587-609 birebir:
        r_eff       = min(menzil, RANGE_SET)
        d_below_eff = r_eff * sin(ISTASYON_ELEV)
    ⚠ Menzil RANGE_SET'in ALTINA inince ofset menzille birlikte kuculur —
    yani komut zaten sifire dogru gider. Buna ragmen saha CPA'da 1.30 m
    olcuyor: kapanmayan sey KOMUT degil, dikey kanalin YETISEMEMESI.
    """
    ad = "a-sabit-15"

    def dz_hedef(self, kes):
        R = kes.R if kes.R else self.R_SET
        return -min(R, self.R_SET) * math.sin(math.radians(self.ELEV))


class D_TERM(Dikey):
    """(b) TERM_DIKEY_M — menzil esigin altina inince yukselis 0'a surulur.

    gps_guidance.py:603-606 birebir:
        elev_eff = ist_elev * clamp(menzil/TERM_DIKEY_M, 0, 1)
    """
    ad = "b-term"
    ESIK = 8.0

    def dz_hedef(self, kes):
        R = kes.R if kes.R else self.R_SET
        e = math.radians(self.ELEV)
        if self.ESIK > 0.0 and R < self.ESIK:
            e *= max(0.0, min(1.0, R / self.ESIK))
        return -min(R, self.R_SET) * math.sin(e)


class D_MERKEZ(Dikey):
    """(e) MERKEZ — ofset HIC yok. Ust sinir olcumu (ve kadraj sinamasi)."""
    ad = "e-merkez"

    def dz_hedef(self, kes):
        return 0.0


class D_TGO(Dikey):
    """(d) ONERI — nisan MENZILE degil KALAN SUREYE baglanir, kapanma ZEM/t_go.

    NEDEN MENZIL ESIGI YANLIS: dikey kanalin OLCULEN kabiliyeti a=3 m/s^2,
    vz<=3 m/s. 1.55 m'yi kapatmak bang-bang ile 2*sqrt(d/a) = 1.44 s ister.
    O sure MENZIL cinsinden kapanma hizina baglidir:
        kuyruk takibi Vc ~ 3.7 m/s  -> 5.3 m
        kesme        Vc ~ 20  m/s   -> 28.8 m
    Sabit bir TERM_DIKEY_M esigi bu ikisinden yalnizca birinde dogru olabilir.
    ⭐ Dogrusu esigi ZAMANA koymak: t_go = R/Vc.

    IKINCI DEGISIKLIK: hata kapatmasi P degil ZEM/t_go (sifir-caba-iskasi).
        ZEM_z  = (z_T + dz_hedef + vT_z*t_go) - (z + vz_up*t_go)
        vz_cmd = vz_up + N_Z * ZEM_z / t_go
    Bu, dikey duzlemde oransal seyrusefer (PN) ile ozdestir ve KALAN SUREYI
    acikca kullanir; sabit K_Z'li P denetimi kullanmaz. Gecikme (46 ms olu
    zaman + 211 ms tau + ~130 ms algi) N_Z>1 ile telafi edilir.
    """
    ad = "d-tgo"
    # ⭐ VARSAYILANLAR TARANARAK SECILDI (bkz. dosya basi SONUC bolumu):
    #    T_BASLA 1.0/1.5/2.0/3.0/4.0 -> CARP %25/%27/%27/%32/%31
    #    N_Z     1.0/1.3/1.6/2.2/3.0 -> CARP %26/%28/%27/%31/%33
    #    R_BASLA 0 (yok)/14/20       -> CARP %36/%38/%38, |dz|50 0.68/0.54/0.58
    T_BASLA = 3.0          # s ; bu t_go'dan itibaren ofset erimeye baslar
    T_BITIS = 0.35         # s ; bu t_go'da ofset TAM sifir
    N_Z = 2.4              # ZEM kazanci (1.0 = "kalan surede tam kapat")
    VC_MIN = 1.0           # m/s ; t_go patlamasin
    TGO_MIN = 0.30         # s
    TGO_MAX = 2.0          # s ; ZEM kazanci icin tavan (bkz. t_go_kes)

    def t_go(self, kes, tavan=True):
        return t_go_kes(kes, self.VC_MIN, self.TGO_MIN,
                        self.TGO_MAX if tavan else None)

    # ── MENZIL YEDEGI (2. tetik) ─────────────────────────────────────────
    # ⚠ TEK BASINA t_go YETMIYOR — TEZGAHTA GORULDU. Kuyruk takibinde
    # kapanma hizi 0'a yakinsar (arkasina oturmus haldeyiz), t_go 20-40 s'e
    # cikar ve nisan cizelgesi HIC ERIMEZ: tek angajman dokumunde dz_ist
    # temasa kadar -1.55 m'de kaldi. Bu yuzden iki tetik OR'lanir:
    #     u = min( u(t_go), u(menzil) )
    # t_go tetigi HIZLI kapanmalari (karsidan gecis, kesme) yakalar,
    # menzil tetigi YAVAS kapanmalari (kuyruk takibi) yakalar. Ikisi de
    # tek basina bir geometri ailesinde kor.
    R_BASLA = 14.0         # m ; menzil tetigi burada baslar
    R_BITIS = 2.0          # m ; burada ofset TAM sifir

    def dz_hedef(self, kes):
        # ⚠ NISAN CIZELGESI TAVANSIZ t_go ILE: uzakta (t_go buyuk) ofset TAM
        # kalsin isteriz; tavanli t_go kullanmak ofseti daima erimis
        # gosterirdi.
        R = kes.R if kes.R else self.R_SET
        tg = self.t_go(kes, tavan=False)
        u = (tg - self.T_BITIS) / max(self.T_BASLA - self.T_BITIS, 1e-6)
        u = max(0.0, min(1.0, u))
        if self.R_BASLA > 0.0:
            ur = (R - self.R_BITIS) / max(self.R_BASLA - self.R_BITIS, 1e-6)
            u = min(u, max(0.0, min(1.0, ur)))
        return -min(R, self.R_SET) * math.sin(math.radians(self.ELEV) * u)

    def __call__(self, kes, p, v, ek=None):
        dzh = self.dz_hedef(kes)
        tg = self.t_go(kes)                          # ZEM icin TAVANLI
        vzu = v[2]                                   # kendi dikey hizimiz (up)
        vtz = self.vt_z(kes, (ek or {}).get("dt", 0.047))
        zem = (kes.pT[2] + dzh + vtz * tg) - (p[2] + vzu * tg)
        vz = vzu + self.N_Z * zem / tg
        return max(-Dik.VZ_MAX, min(Dik.VZ_MAX, vz)), dzh


class D_KESISIM(Dikey):
    """(c) GERCEK TERMINAL KESISIM YASASI — bbox_ibvs.komut(terminal=True).

    ⚠ KOPYA MATEMATIK YOK: gercek modul import edilip cagrilir; yalniz vz
    ciktisi alinir (yatay kanal butun yapilarda AYNI kalsin diye).
    Kodda terminal mandali KUTU BOYUTUNA bakar (TERMINAL_BOYUT=25 px ~ 6.4 m)
    ve NISAN KAPISI ile korunur; sahada karelerin ancak %0.2-3.8'inde
    atesleniyor. Burada tetikleme MENZILE baglanip taranir: R_TETIK.
    Esigin USTUNDE (a) yasasi kosar (gercek sistemde de oyle).
    """
    ad = "c-kesisim"
    R_TETIK = 8.0
    _B = None

    @classmethod
    def yasa(cls):
        if cls._B is None:
            sys.path.insert(0, os.path.join(KOK, "kopru", "gazebo_kaynak"))
            from control.guidance import bbox_ibvs as B      # noqa: E402
            cls._B = B
        return cls._B

    def dz_hedef(self, kes):
        R = kes.R if kes.R else self.R_SET
        return -min(R, self.R_SET) * math.sin(math.radians(self.ELEV))

    def __call__(self, kes, p, v, ek=None):
        R = kes.R if kes.R else self.R_SET
        if ek is None or ek.get("kutu") is None or R > self.R_TETIK:
            return Dikey.__call__(self, kes, p, v, ek)
        B = self.yasa()
        cx, cy, w, h = ek["kutu"]
        try:
            _vx, _vy, vz_ned, _yaw, _I, _t = B.komut(
                cx, cy, max(w, 1.0), max(h, 1.0), ek["yaw"], ek["hiz_I"],
                ek["dt"], cfg=B.Cfg, terminal=True,
                los_hiz=(kes.om_los, ek.get("om_el", 0.0)),
                iris_pitch=ek["pitch"], iris_vz=-v[2],
                kapanma=max(-kes.Rdot, 0.0), iris_roll=ek["roll"],
                yaw_hizi=ek.get("yaw_hizi", 0.0), psi_v=None)
        except Exception:
            return Dikey.__call__(self, kes, p, v, ek)
        vz_up = -vz_ned                     # yasa NED asagi-pozitif verir
        return (max(-Dik.VZ_MAX_TERM, min(Dik.VZ_MAX_TERM, vz_up)),
                self.dz_hedef(kes))


YASALAR = {"a": D_SABIT, "b": D_TERM, "c": D_KESISIM, "d": D_TGO, "e": D_MERKEZ}


# ══════════════════════════════════════════════════════════════════════════
#  YATAY KANAL — TUM YAPILARDA AYNI (tek degisken kurali)
# ══════════════════════════════════════════════════════════════════════════
class Yatay(TR.DenetimC):
    """trail.DenetimC'nin YEREL TEGET istasyonu + TEMAS MANDALI.

    ⚠ trail.DenetimC dogrulanmis (10/10) ve donen hedefte olculmus tek yatay
    yapi; yeniden yazmiyorum. Menzil TERM_YATAY'in altina inince MANDAL
    kapanir (bbox_ibvs.terminal_mandal gibi: bir kez girilince geri donmez)
    ve yatay kanal ONGORULEN KESISIM NOKTASINA saf hucuma gecer.

    ⚠⚠ ILK SURUM YANLISTI VE NEDENI OGRETICI: "arka mesafeyi menzille
    orantili kis" yazmistim (d = R_SET*R/TERM_YATAY). TERM_YATAY = R_SET
    oldugu icin bu d = R demek, yani ISTENEN ARKA MESAFE = MEVCUT MENZIL:
    radyal hata TANIMI GEREGI SIFIR, kapanma komutu HIC uretilmiyor.
    Donuste CPA 4.9 m'de takiliyordu ve bu "dikey yasa kotu" gibi
    gorunuyordu. ⚠ AYNI TUZAK GERCEK KODDA DA VAR: gps_guidance.py:587
    `r_eff = min(menzil, RANGE_SET)` — menzil RANGE_SET'in altina inince
    istasyon TAM aracin bulundugu menzile oturur, yani GPS fazinin 6 m'nin
    icinde KAPANMA TAHRIKI YOKTUR. Sahada 1.3-1.9 m'ye inmemizin sebebi
    tasarlanmis bir hucum degil, atalet ve kor kareler olabilir.

    ⚠ TEZGAH SECIMI (ve gerekcesi): yatay kanal BILEREK iyi tutuluyor —
    saha zaten yatayda 0.60 m olcuyor, yani yatay nisan COZULMUS durumda.
    Boylece kalan tek kisit DIKEY olur ve tek degisken kurali korunur.
    Mutlak carpisma oranlari bu yuzden UST SINIRDIR.
    """
    TERM_YATAY = 6.0
    V_TERM = 22.0          # m/s ; mandal sonrasi hucum hizi
    VC_MIN = 1.0
    TGO_MAX = 2.0          # s ; bkz. t_go_kes()

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.mandal = False

    def yatay(self, k, p, v):
        R = k.R if k.R else self.R_set
        if self.TERM_YATAY > 0.0 and R < self.TERM_YATAY:
            self.mandal = True
        if not self.mandal:
            return TR.DenetimC.yatay(self, k, p, v)
        # ── HUCUM: ONGORULEN KESISIM NOKTASINA (yay ongorusu) ────────────
        t_go = t_go_kes(k, self.VC_MIN, 0.15, self.TGO_MAX)
        ix, iy = ongoru_yay(k, t_go)
        hx, hy = ix - p[0], iy - p[1]
        n = math.hypot(hx, hy) or 1e-6
        s = min(self.v_max, self.V_TERM)
        return s * hx / n, s * hy / n


# ══════════════════════════════════════════════════════════════════════════
#  KOSU — tek angajman
# ══════════════════════════════════════════════════════════════════════════
def kosu(dikey="a", senaryo="duz", aspect0=45.0, R0=25.0, sure=30.0,
         dt=1.0 / 62.0, tohum=0, hata=None, v_max=24.0, max_accel=12.0,
         pitch_trim=Dik.PITCH_TRIM, az_max=Dik.AZ_MAX, dz0=None,
         R_set=Dik.RANGE_SET, term_yatay=6.0, kutu_gurultu=True,
         tutum_modeli=True, kayit=False, dikey_kw=None, kes_kw=None,
         t0_gercek=0.0, sicak=True, kayip_kopru_s=0.7,
         arka_plan=1.0, **kw):
    """Tek angajman -> CPA olcutleri.

    aspect0 : baslangicta kuyruktan sapma (derece). 0 = tam arkada.
    dz0     : baslangic irtifa farki (m, negatif = altinda). None ->
              YASANIN KENDI DENGESI: -min(R0,R_SET)*sin(ISTASYON_ELEV).
              ⚠ ILK SURUMDE -R0*sin(15°) idi (R0=25'te -6.47 m). O, yasanin
              istedigi yer DEGIL: gps_guidance r_eff = min(menzil,RANGE_SET)
              kullaniyor, yani 25 m'de de istenen ofset 1.55 m. 6.47 ile
              baslamak her kosuya 4.9 m'lik SAHTE bir dikey gecici ekliyordu
              ve dikey kanali sorunun kendisiyle degil, baslangic hatasiyla
              sinaniyordu — TEZGAH KUSURU.
    sicak   : kestirime GPS fazindan devralinan hedef durumu verilir
              (gurultulu). GERCEKCI: run_bbox_ibvs zaten `ff_hiz` ile sicak
              baslatiliyor ve GPS fazi hedefi saniyelerdir izliyor. False =
              soguk baslangic (1.2 s en-kucuk-kareler; ablasyon).
    """
    if hata is None:
        hata = HataAyari()
    algi = Algi(hata, tohum=tohum)
    kutu = Kutu(tohum=tohum, olcek=True, gurultu=kutu_gurultu)
    sayac = KilitSayaci()
    sayac._ilan = True

    hed = HedefD(senaryo, t0=t0_gercek)
    hx, hy, hz, hvx, hvy, hvz = hed.durum()
    hdg = math.atan2(hvy, hvx)

    Dk = YASALAR[dikey](**(dikey_kw or {})) if isinstance(dikey, str) else dikey
    Yt = Yatay(R_set=R_set, v_max=v_max, TERM_YATAY=term_yatay, **kw)

    if dz0 is None:
        dz0 = -min(R0, R_set) * math.sin(math.radians(Dik.ISTASYON_ELEV))
    yatay0 = math.sqrt(max(R0 ** 2 - dz0 ** 2, 1.0))
    yon = hdg + math.pi + math.radians(aspect0)
    av = AvciD(x=hx + yatay0 * math.cos(yon), y=hy + yatay0 * math.sin(yon),
               z=hz + dz0, yaw=0.0, max_accel=max_accel, v_max=v_max,
               vz_max=Dik.VZ_MAX, yaw_rate_max=120.0,
               pitch_trim=pitch_trim, az_max=az_max)
    av.yaw = math.atan2(hy - av.y, hx - av.x)
    av.vx = Olcum.HEDEF_HIZ * math.cos(av.yaw)
    av.vy = Olcum.HEDEF_HIZ * math.sin(av.yaw)

    yas_nom = (hata.kare_gecikme_s + hata.det_gecikme_s
               + (0.5 / hata.kamera_hz if hata.kamera_hz > 0.0 else 0.0))
    kes = Kestirim(tohum=tohum, tutum_modeli=tutum_modeli,
                   vt_sabit=Olcum.HEDEF_HIZ, yas_nom=yas_nom, **(kes_kw or {}))
    if sicak:
        # ── SICAK DEVIR: GPS fazindan devralinan hedef durumu ────────────
        # ⚠ BU BIR KOLAYLIK DEGIL, SADAKATTIR: run_bbox_ibvs(ff_hiz=...)
        # devir aninda GPS fazinin son hiz kestirimini aliyor ve GPS fazi
        # hedefi saniyelerdir izliyor. Soguk baslatmak, aspect0=180'de
        # (kapanma 36-42 m/s) angajmani kestirim daha hazir olmadan
        # bitiriyordu -> CPA olcumu yasayi degil, 1.2 s'lik soguk basi
        # olcuyordu. Gurultu OLCULEN devir hatasi buyuklugunde birakildi.
        r0 = random.Random(tohum * 7717 + 3)
        kes.pT = (hx + r0.gauss(0.0, 0.8), hy + r0.gauss(0.0, 0.8),
                  hz + r0.gauss(0.0, 0.5))
        kes.vT = (hvx + r0.gauss(0.0, 1.2), hvy + r0.gauss(0.0, 1.2),
                  hvz + r0.gauss(0.0, 0.4))
        kes.R1 = math.dist((av.x, av.y, av.z), kes.pT)
        kes._zarf()
        kes.hazir = True
        kes._turet((av.x, av.y, av.z), (av.vx, av.vy, -av.vz), dt)

    t = 0.0
    son_yasa_t = -1e9
    son_poz = None
    cpa = CPA()
    kilit_iz = []
    kadraj_ic = [0, 0]
    dz_iz = []
    iz = []
    hiz_I = Olcum.HEDEF_HIZ
    kayip_s = 0.0
    om_el = 0.0
    el_onc = None
    R_min_gorulen = 1e9
    ayrildi = False

    while t < sure:
        hed.adim(dt)
        hx, hy, hz, hvx, hvy, hvz = hed.durum()
        hdg = math.atan2(hvy, hvx)
        av._hedef_yon = hdg
        k = kutu(av, hx, hy, hz, dt)
        # ── ARKA PLAN CEZASI (varsayilan KAPALI = 1.0) ───────────────────
        # ⚠ TEZGAHIN BILINEN ACIGI: tespit_olasilik() YALNIZ kutu boyutuna
        # bakiyor. Gercekte hedefin ARKA PLANI onemli: altindan bakinca
        # GOKYUZU, ustunden bakinca YER karmasasi. Bu tezgah o farki
        # modellemedigi icin "ofseti tamamen kaldir" secenegini YAPISAL
        # OLARAK KAYIRIR — sonuclari oyle okumak yaniltici olurdu.
        # LITERATUR (Munir/Siddiqui/Anwar, IEEE-CVF WACV-W 2024,
        # arXiv:2305.16450, Tablo 2-3): gokyuzu arka planli kumede
        # mAP50-95 = 72.0 (YOLOv8m) / 71.7 (YOLOv5m); karmasik arka planli
        # kumede 57.5 / 59.0. ⚠ Kontrollu bir A/B degil, AYRI VERI KUMELERI
        # — buyukluk gostergesi, kanit degil.
        # Bu yuzden ceza bir PARAMETRE: 1.0 = ceza yok. Tarama, ofsetin
        # kendini hangi ceza degerinde AMORTI ETTIGINI bulur.
        if arka_plan < 1.0 and k is not None:
            elev = math.atan2(hz - av.z, math.hypot(hx - av.x, hy - av.y))
            u = max(0.0, min(1.0, 0.5 - elev / math.radians(10.0)))  # yer payi
            if algi.rnd.random() > (1.0 - u * (1.0 - arka_plan)):
                k = None
        algi.kare_ver(t, av, k)

        # ---- TRUTH olcutleri ----
        dxa, dya = av.x - hx, av.y - hy
        na = math.hypot(dxa, dya) or 1e-6
        asp = math.degrees(math.acos(max(-1.0, min(1.0,
                           -(dxa * math.cos(hdg) + dya * math.sin(hdg)) / na))))
        cpa.besle(t, (dxa, dya, av.z - hz), asp)
        Rt = math.dist((av.x, av.y, av.z), (hx, hy, hz))
        R_min_gorulen = min(R_min_gorulen, Rt)
        kadraj_ic[0 if k is None else 1] += 1
        dz_iz.append(av.z - hz)
        # CPA gecildi mi? (yakinsayip uzaklasmaya basladiysa bitir)
        if R_min_gorulen < 8.0 and Rt > R_min_gorulen + 4.0:
            ayrildi = True
            break

        if hata.yasa_hz > 0.0 and t - son_yasa_t < 1.0 / hata.yasa_hz - 1e-9:
            av.adim(dt, t)
            t += dt
            continue
        dt_yasa = dt if son_yasa_t < 0.0 else max(t - son_yasa_t, dt)
        son_yasa_t = t

        poz = algi.oku(t)
        yaw_olc = algi.yaw_oku(t)
        roll_olc, pitch_olc = algi.tutum_oku(t)
        kayip_s = 0.0 if poz is not None else kayip_s + dt_yasa

        # SARTNAME KILIT SAYACI (gercek modul, degistirilmeden)
        tespit = None
        if poz is not None:
            cxp, cyp, wp, hp = poz
            # ⚠⚠ TEZGAH KUSURU (10) — trail.py'den DEVRALINDI, BURADA DUZELTILDI.
            # Kal.KX/KY "YASA PIKSEL OFSETI -> normalize kesir" carpanidir
            # (icinde 1/F_YASA vardir). trail.py:1005-1006 onlari BOYUTSUZ
            # TEGETE (tx = (cx-CX)/F_YASA) uyguluyor, yani F_YASA=166.6 KAT
            # KUCUK bir kesir uretiyor:
            #     seviye hedef (ty=tan25°=0.466) -> DOGRU cyn 0.7293
            #                                       trail.py cyn 0.5014
            # Sonuc: sartname kilidinin ACISAL kapisi (0.25<=cxn<=0.75,
            # 0.10<=cyn<=0.90) trail.py'de FIILEN DEVRE DISI; hedef her zaman
            # kadrajin tam ortasinda gorunuyor ve YALNIZ kutu-boyut olcutu
            # baglıyor. trail.py'nin "%80 5 s kesintisiz kilit" sonucu bu
            # yuzden ACISAL KAPI KAPALIYKEN olculmustur.
            # ⚠ TAM DA BU KUSUR bu gorevin sorusunu bozardi: dikey ofseti
            # kaldirmanin kadraj/kilit BEDELI olup olmadigini olcen tek kapi
            # cyn kapisidir.
            tespit = {"cx": (0.5 + (cxp - CX) * Kal.KX) * 1920.0,
                      "cy": (0.5 + (cyp - CY) * Kal.KY) * 1080.0,
                      "w": wp * (Kal.DOW_F / F_YASA),
                      "h": hp * (Kal.DOW_F / F_YASA),
                      "W": 1920.0, "H": 1080.0}
        kilit_iz.append((t, sayac.guncelle(tespit, t, gorsel_faz=True)))

        yeni_kutu = poz is not None and poz is not son_poz
        son_poz = poz
        kes.guncelle(t, dt_yasa, poz, yaw_olc, roll_olc, pitch_olc,
                     av.yaw_hizi, (av.x, av.y, av.z), (av.vx, av.vy, -av.vz),
                     0.0, yeni_kutu)

        if kes.hazir:
            # dikey LOS acisal hizi (yalniz (c) yasasinin lead'i icin)
            uh = math.hypot(kes.u[0], kes.u[1]) or 1e-6
            el = math.atan2(kes.u[2], uh)
            if el_onc is not None and dt_yasa > 1e-6:
                om_el += min(1.0, dt_yasa / 0.25) * (
                    (el - el_onc) / dt_yasa - om_el)
            el_onc = el
            p = (av.x, av.y, av.z)
            vv = (av.vx, av.vy, -av.vz)
            vx, vy = Yt.yatay(kes, p, vv)
            n = math.hypot(vx, vy)
            if n > v_max:
                vx, vy = vx * v_max / n, vy * v_max / n
            sp = math.hypot(vv[0], vv[1])
            if sp > 1.0:                       # yanal/ileri ivme sekillendirme
                ux, uy = vv[0] / sp, vv[1] / sp
                dvx, dvy = vx - vv[0], vy - vv[1]
                d_par = dvx * ux + dvy * uy
                d_dik = dvx * (-uy) + dvy * ux
                lp = Yt.A_ILERI_MAX * Olcum.ZAMAN_SABITI
                ld = Yt.A_YAN_MAX * Olcum.ZAMAN_SABITI
                d_par = max(-lp, min(lp, d_par))
                d_dik = max(-ld, min(ld, d_dik))
                vx = vv[0] + d_par * ux - d_dik * uy
                vy = vv[1] + d_par * uy + d_dik * ux
            ek = {"kutu": poz, "yaw": kes.yaw_hat or av.yaw, "hiz_I": hiz_I,
                  "dt": dt_yasa, "pitch": kes.pitch_hat, "roll": kes.roll_hat,
                  "om_el": om_el, "yaw_hizi": av.yaw_hizi}
            vz_up, dzh = Dk(kes, p, vv, ek)
            yaw_cmd = math.atan2(kes.u[1], kes.u[0]) + Yt.T_lead * kes.om_los
            # ── KAYIP POLITIKASI (trail.py'den, degistirilmeden) ─────────
            # ⚠ HAYALETI KOVALAMA. trail.py bunu OLCTU ve belgeledi: kutu
            # kaybolunca kestirim ongoruyle ilerliyor, denetleyici o hayalete
            # gidiyor ve menzil 326 m'ye kaciyordu. Bu tezgahin ILK surumunde
            # politikayi unuttum ve AYNI ariza geri geldi: gercek yorunge /
            # aspect90 kosusunda R 25 -> 539 m, dz -8 m. TEZGAH KUSURU, yasa
            # kusuru degil. Dogrusu SEYIR: hedefin son kestirilen hizini
            # surdur, DIKEYI DONDUR, burnu ongorulen LOS'ta tut.
            if kayip_s > kayip_kopru_s:
                vx, vy = kes.vT[0], kes.vT[1]
                vz_up = 0.0
                yaw_cmd = math.atan2(kes.pT[1] - av.y, kes.pT[0] - av.x)
            av.setpoint(vx, vy, -vz_up, yaw_cmd, t)
            if kayit:
                iz.append([round(t, 2), round(Rt, 2), round(kes.R or 0, 2),
                           round(av.z - hz, 2), round(dzh, 2),
                           round(vz_up, 2), round(-av.vz, 2),
                           round(asp, 1), round(math.hypot(av.vx, av.vy), 1),
                           1 if poz is not None else 0])
        elif kes.R1 is not None:
            u = kes.u_ham
            R = kes.R1
            hz_ = max(0.0, min(v_max, Olcum.HEDEF_HIZ + 0.6 * (R - R_set)))
            n = math.hypot(u[0], u[1]) or 1e-6
            av.setpoint(hz_ * u[0] / n, hz_ * u[1] / n, 0.0,
                        math.atan2(u[1], u[0]), t)
        else:
            yc = kes.yaw_hat if kes.yaw_hat is not None else av.yaw
            if poz is not None:
                yc = yc + math.atan((poz[0] - CX) / F_YASA)
            av.setpoint(av.vx, av.vy, 0.0, yc, t)
        av.adim(dt, t)
        t += dt

    # ---- olcutler ----
    en_uzun = 0.0
    bas = None
    for tt, a in kilit_iz:
        if a and bas is None:
            bas = tt
        elif not a and bas is not None:
            en_uzun = max(en_uzun, tt - bas)
            bas = None
    if bas is not None and kilit_iz:
        en_uzun = max(en_uzun, kilit_iz[-1][0] - bas)
    top = kadraj_ic[0] + kadraj_ic[1]
    # ── ANGAJMAN TAMAMLANDI MI? ──────────────────────────────────────────
    # ⚠ AYRIM SART. Kosularin bir kismi hedefi EDINEMEDEN dagiliyor (yuksek
    # aspect, 35 °/s donus): hedef kadrajdan cikiyor, kestirim hayalete
    # kayiyor, menzil 100-200 m'ye aciliyor. O kosularda olculen "dikey
    # ayrim" DIKEY NISANI degil, EDINIM ARIZASINI olcer ve yapilarin
    # kiyasini kirletir. Bu yuzden:
    #     CARP%%  -> BUTUN kosular uzerinden (gorev olcutu)
    #     TAM%%   -> hucum mandalinin kapandigi kosu orani (edinim olcutu)
    #     |dz|,yat -> YALNIZ tamamlananlar uzerinden (dikey nisan olcutu)
    tamam = bool(Yt.mandal) or (cpa.en_iyi is not None and cpa.en_iyi < 5.0)
    return {
        "tamam": tamam, "senaryo": senaryo, "aspect": aspect0,
        "cpa": cpa.en_iyi, "cpa_dz": cpa.dz, "cpa_yatay": cpa.yatay,
        "cpa_t": cpa.t, "cpa_asp": cpa.asp, "carpti": cpa.carpti(),
        "kesintisiz_s": en_uzun, "kesintisiz_ok": en_uzun >= KilitCfg.WIN_NEED_S,
        "sartname_ok": bool(sayac.ok),
        "kadraj_ic": (kadraj_ic[1] / top) if top else 0.0,
        "dz_son": dz_iz[-1] if dz_iz else None,
        "ayrildi": ayrildi, "sure": t, "iz": iz,
    }


# ══════════════════════════════════════════════════════════════════════════
#  KUME / OZET
# ══════════════════════════════════════════════════════════════════════════
SENARYO = ("duz", "don4", "don8", "don15", "don20", "don35", "zikzak",
           "dikey", "oval", "gercek")
ASPECT = (0.0, 45.0, 90.0, 135.0, 180.0)


def kume(n=3, senaryolar=SENARYO, aspectler=ASPECT, dikey="a", **kw):
    r = []
    for sen in senaryolar:
        for asp in aspectler:
            for i in range(n):
                r.append(kosu(dikey=dikey, senaryo=sen, aspect0=asp,
                              tohum=i, t0_gercek=17.0 * i + 3.0 * asp, **kw))
    return r


def dilim(r, senaryo=None, aspect=None):
    return [x for x in r
            if (senaryo is None or x["senaryo"] == senaryo)
            and (aspect is None or x["aspect"] == aspect)]


def _med(v):
    v = [x for x in v if x is not None]
    if not v:
        return None
    s = sorted(v)
    m = len(s)
    return s[m // 2] if m % 2 else 0.5 * (s[m // 2 - 1] + s[m // 2])


def _p90(v):
    v = sorted(x for x in v if x is not None)
    return v[int(0.90 * (len(v) - 1))] if v else None


def ozet(ad, r, gen=26):
    def f(x, s="%6.2f"):
        return (s % x) if x is not None else "     -"
    t = [x for x in r if x["tamam"]] or r
    return ("  %-*s %5.0f%% %4.0f%% %s %s %s %s %s %5.0f%% %5.0f%%" % (
        gen, ad, 100.0 * sum(1 for x in r if x["carpti"]) / len(r),
        100.0 * sum(1 for x in r if x["tamam"]) / len(r),
        f(_med([abs(x["cpa_dz"]) for x in t])),
        f(_p90([abs(x["cpa_dz"]) for x in t])),
        f(_med([x["cpa_yatay"] for x in t])),
        f(_med([x["cpa"] for x in t])),
        f(_med([x["cpa_dz"] for x in t]), "%+6.2f"),
        100.0 * sum(1 for x in r if x["kesintisiz_ok"]) / len(r),
        100.0 * sum(x["kadraj_ic"] for x in r) / len(r)))


def baslik(gen=26):
    return ("  %-*s %5s %4s %6s %6s %6s %6s %6s %5s %5s" % (
        gen, "dikey nisan yapisi", "CARP", "TAM", "|dz|50", "|dz|90", "yat50",
        "cpa50", "dz50", "5s", "kadr")
        + "\n  (|dz| yat cpa: YALNIZ tamamlanan angajmanlar uzerinden)"
        + "\n  " + "-" * (gen + 62))


# ══════════════════════════════════════════════════════════════════════════
#  OZ-SINAMA
# ══════════════════════════════════════════════════════════════════════════
def dogrula_dikey(sessiz=False):
    """Dikey katmanin ISARET/OLCEK dogrulugu. HER TARAMADAN ONCE."""
    h = []
    if T.dogrula(sessiz=True):
        h.append("tesis.dogrula() KALDI")
    if TR.dogrula_trail(sessiz=True):
        h.append("trail.dogrula_trail() KALDI")

    class _A:
        x = y = z = 0.0
        yaw = pitch = roll = 0.0
        _hedef_yon = 0.0

    # 1) PITCH TRIMI KADRAJI KAYDIRMALI. Seviye hedef, pitch=0 -> cy =
    #    CY+F*tan(25°); pitch=-13.3° -> cy = CY+F*tan(25-13.3=11.7°).
    a = _A()
    for pt, bkl in ((0.0, 25.0), (-13.3, 11.7), (10.0, 35.0)):
        a.pitch = math.radians(pt)
        k = kadraj(a, 100.0, 0.0, 0.0)
        cy_b = CY + F_YASA * math.tan(math.radians(bkl))
        if k is None or abs(k[1] - cy_b) > 1.0:
            h.append("pitch %.1f°: cy=%s, beklenen %.1f" %
                     (pt, k and round(k[1], 1), cy_b))
    a.pitch = 0.0

    # 2) AvciD PITCH TRIMI: seyirde OLCULEN degeri vermeli, dururken ~0.
    av = AvciD(x=0, y=0, z=0, yaw=0.0)
    for i in range(600):
        av.setpoint(20.0, 0.0, 0.0, 0.0, i / 62.0)
        av.adim(1 / 62.0, i / 62.0)
    if abs(math.degrees(av.pitch) - Dik.PITCH_TRIM) > 2.0:
        h.append("seyirde pitch %.1f°, beklenen %.1f°"
                 % (math.degrees(av.pitch), Dik.PITCH_TRIM))
    av2 = AvciD(x=0, y=0, z=0, yaw=0.0, pitch_trim=0.0, az_max=None)
    for i in range(600):
        av2.setpoint(20.0, 0.0, 0.0, 0.0, i / 62.0)
        av2.adim(1 / 62.0, i / 62.0)
    if abs(math.degrees(av2.pitch)) > 0.5:
        h.append("pitch_trim=0'da seyir pitch'i %.2f° (0 olmali)"
                 % math.degrees(av2.pitch))

    # 3) DIKEY IVME SINIRI: 0 -> 3 m/s tirmanma en az 3/AZ_MAX saniye surmeli.
    for azm, en_az in ((Dik.AZ_MAX, 3.0 / Dik.AZ_MAX), (None, 0.0)):
        av3 = AvciD(x=0, y=0, z=0, yaw=0.0, az_max=azm)
        av3.vx = 18.0
        t9 = None
        for i in range(400):
            tt = i / 62.0
            av3.setpoint(18.0, 0.0, -3.0, 0.0, tt)
            av3.adim(1 / 62.0, tt)
            if t9 is None and -av3.vz > 2.9:
                t9 = tt
        if azm is not None:
            if t9 is None or t9 < en_az * 0.9:
                h.append("dikey ivme siniri tutmadi: 3 m/s'ye %s s'de cikti, "
                         "en az %.2f s olmali" % (t9, en_az))
        elif t9 is None or t9 > 0.75:
            h.append("az_max=None'da (eski tesis) 3 m/s'ye %s s (hizli olmali)"
                     % t9)
    # ivme sinirinin IRTIFAYI bozmadigi: sabit vz komutunda z dogrusal artmali
    av4 = AvciD(x=0, y=0, z=0, yaw=0.0)
    av4.vx = 18.0
    for i in range(600):
        av4.setpoint(18.0, 0.0, -2.0, 0.0, i / 62.0)
        av4.adim(1 / 62.0, i / 62.0)
    bkl4 = 2.0 * (600 / 62.0) - 2.0 * (2.0 / Dik.AZ_MAX) / 2.0
    if abs(av4.z - bkl4) > 0.4:
        h.append("dikey entegrasyon: z=%.2f m, beklenen ~%.2f m" % (av4.z, bkl4))

    # 4) CPA ANALITIGI: iki dogru cizgi, bilinen en yakin gecis.
    #    Avci (0,-100,0)'dan +y'ye 20 m/s; hedef (0,0,1.0) sabit -> CPA 1.0 m
    #    ve TAM ORNEKLER ARASINDA (dt = 1/62 -> adim 0.32 m).
    c = CPA()
    dt4 = 1.0 / 62.0
    for i in range(700):
        yy = -100.0 + 20.0 * (i * dt4) + 0.1234      # ornek izgarasini kaydir
        c.besle(i * dt4, (0.0, yy, -1.0), 0.0)
    if abs(c.en_iyi - 1.0) > 0.01 or abs(abs(c.dz) - 1.0) > 0.01:
        h.append("CPA analitigi: %.3f m (dz %.3f), beklenen 1.000"
                 % (c.en_iyi, c.dz or -9))
    if c.yatay > 0.02:
        h.append("CPA yatay bileseni %.3f m, beklenen ~0" % c.yatay)

    # 5) ⭐ PLANT<->YASA DIKEY ZINCIRI — VE YASADA BULUNAN KUSUR.
    #
    #    (5a) los_seviye(cx,cy,roll,pitch) TAM olmali: tesisin kadraj()
    #         zincirinin birebir tersidir. Tutarsa hem tezgahin hem yasanin
    #         dikey geometrisi DOGRULANMIS olur (iki bagimsiz uygulama).
    #         OLCULDU: her azimut/roll kusaginda hata 0.00° — TAM.
    #
    #    (5b) ⚠ AMA TERMINAL KESISIM YASASI ONU KULLANMIYOR.
    #         bbox_ibvs.py:1094:  elev_atalet = piksel_elev(cy) + iris_pitch
    #         piksel_elev = atan2(-bz, bx) — yani gövde ileri eksenine gore;
    #         DOGRUSU atan2(-bz, hypot(bx,by)). Yanal bilesen (azimut)
    #         DUSURULMUS, ve roll HIC cikarilmamis, pitch de doner donusum
    #         yerine TOPLANMIS.
    #         OLCULEN HATA (40000 rastgele geometri, isaretli, derece):
    #           roll=0            |eps|15-30: p50 +0.2  p05/p95  -1.7/ +3.0
    #                             |eps|30-45: p50 +0.7  p05/p95  -4.4/ +7.4
    #                             |eps|45-60: p50 +0.7  p05/p95  -9.2/+15.9
    #           roll ±40°         |eps| 0-15: p50 +0.8  p05/p95  -4.3/+11.8
    #                             |eps|15-30: p50 +3.0  p05/p95 -11.8/+23.0
    #                             |eps|30-45: p50 +4.9  p05/p95 -19.6/+31.4
    #         BASKIN SEBEP ROLL. Terminalde yatis 50.7°'ye kadar cikiyor
    #         (MAX_ACCEL=12 -> atan(12/9.81)); yani yasanin nisan yukselisi
    #         tam da hucum aninda 10-30° hatali.
    #         BEDELI: vz = -v*tan(nisan_elev). v=18 m/s'de 5° hata 1.6 m/s,
    #         30° hata 10.4 m/s -> VZ_MAX_TERM=5 doyar, ve "dikey butce"
    #         kisiti YATAY hizi da V_TERM_MIN=10'a indirir.
    #         ⚠ DUZELTMESI DOSYADA ZATEN VAR (los_seviye) ama (i) yalniz
    #         TUTUS dalinda, (ii) Cfg.DIKEY_ROLL varsayilani KAPALI (0.0),
    #         (iii) terminal dalinda hic cagrilmiyor.
    #    Bu sinama artik BEKCI: (5a) bozulursa hata, (5b) OLCULEN zarfin
    #    disina cikarsa hata (yani yasa duzeltilirse burasi haber verir).
    try:
        sys.path.insert(0, os.path.join(KOK, "kopru", "gazebo_kaynak"))
        from control.guidance import bbox_ibvs as B          # noqa: E402
        rnd = random.Random(5)
        enb_s = 0.0
        yasa_h = []
        for _ in range(4000):
            a.yaw = rnd.uniform(-math.pi, math.pi)
            a.pitch = math.radians(rnd.uniform(-30, 15))
            a.roll = math.radians(rnd.uniform(-40, 40))
            hx = rnd.uniform(-40, 40); hy = rnd.uniform(-40, 40)
            hz = rnd.uniform(-15, 15)
            kk = kadraj(a, hx, hy, hz)
            if kk is None:
                continue
            el_t = math.atan2(hz, math.hypot(hx, hy))
            _az, el_s = B.los_seviye(kk[0], kk[1], a.roll, a.pitch, B.Cfg)
            enb_s = max(enb_s, abs(math.degrees(_sar(el_s - el_t))))
            yasa_h.append(abs(math.degrees(
                _sar(B.piksel_elev(kk[1], B.Cfg) + a.pitch - el_t))))
        if enb_s > 0.05:
            h.append("los_seviye() tersi tutmadi (enb %.3f°) — tezgah ya da "
                     "yasa geometrisi bozuk" % enb_s)
        yasa_h.sort()
        p95 = yasa_h[int(0.95 * (len(yasa_h) - 1))] if yasa_h else 0.0
        if not (12.0 <= p95 <= 45.0):
            h.append("terminal nisan yukselisi hatasi p95 %.1f°, OLCULEN "
                     "zarf 12-45° (yasa degisti mi?)" % p95)
        a.yaw = a.pitch = a.roll = 0.0
    except Exception as e:                                   # pragma: no cover
        h.append("gercek yasa import edilemedi: %r" % (e,))

    # 6) YASA (a) DENGESI: kusursuz sensor + duz hedef -> dz = -R_SET*sin(15°)
    r6 = kosu(dikey="a", senaryo="duz", aspect0=0.0, R0=15.0, sure=25.0,
              hata=HataAyari.kapali(), kutu_gurultu=False, tutum_modeli=False,
              term_yatay=0.0)
    bkl6 = -Dik.RANGE_SET * math.sin(math.radians(Dik.ISTASYON_ELEV))
    if r6["dz_son"] is None or abs(r6["dz_son"] - bkl6) > 0.35:
        h.append("(a) dengesi dz=%s m, beklenen %.2f m"
                 % (r6["dz_son"] and round(r6["dz_son"], 2), bkl6))

    # 7) YASA (e) DENGESI: ofset yok -> dz ~ 0 ve hedef HALA kadrajda.
    r7 = kosu(dikey="e", senaryo="duz", aspect0=0.0, R0=15.0, sure=25.0,
              hata=HataAyari.kapali(), kutu_gurultu=False, tutum_modeli=False,
              term_yatay=0.0)
    if r7["dz_son"] is None or abs(r7["dz_son"]) > 0.35:
        h.append("(e) merkez dengesi dz=%s m, beklenen ~0"
                 % (r7["dz_son"] and round(r7["dz_son"], 2)))
    if r7["kadraj_ic"] < 0.9:
        h.append("(e) merkezde hedef kadrajda kalmadi (%.0f%%)"
                 % (100 * r7["kadraj_ic"]))

    # 8) ISARET: hedefin USTUNE nisan alinirsa USTUNE cikmali.
    r8 = kosu(dikey=D_SABIT(ELEV=-15.0), senaryo="duz", aspect0=0.0, R0=15.0,
              sure=25.0, hata=HataAyari.kapali(), kutu_gurultu=False,
              tutum_modeli=False, term_yatay=0.0)
    if r8["dz_son"] is None or r8["dz_son"] < 0.8:
        h.append("ELEV=-15° (ustune nisan) dz=%s m, POZITIF olmaliydi"
                 % (r8["dz_son"] and round(r8["dz_son"], 2)))

    # 9) GERCEK IZ oynatilabiliyor ve OLCULEN donus hizini veriyor mu
    iz = gercek_iz()
    if not iz:
        h.append("gercek hedef izi yuklenemedi (veri/hedef_iz)")
    else:
        hd = HedefD("gercek", t0=0.0)
        om = []
        p = (hd.x, hd.y)
        ph = hd.hdg
        for _ in range(4000):
            hd.adim(1 / 20.0)
            if abs(hd.x - p[0]) > 1e-9 or abs(hd.y - p[1]) > 1e-9:
                om.append(abs(math.degrees(_sar(hd.hdg - ph))) * 20.0)
                ph = hd.hdg
            p = (hd.x, hd.y)
        om.sort()
        if not om or not (2.0 <= om[len(om) // 2] <= 15.0):
            h.append("gercek izin donus hizi medyani %s °/s, OLCULEN ~6.5"
                     % (om and round(om[len(om) // 2], 1)))

    # 10b) ⭐ SARTNAME KILIDININ ACISAL KAPISI GERCEKTEN BAGLIYOR MU?
    #      (bkz. kusur 10). Seviye hedef, pitch=0, R=6 m -> ty=tan(25°)=0.466
    #      -> cyn = 0.5 + 0.466*531.36/1080 = 0.7293. Kapi 0.90'da.
    #      ⭐ DIKEY KILIT PENCERESI (buradan turetildi, R=6 m):
    #         cyn<=0.90 -> ty<=0.813 -> (25°+pitch-elev)<=39.1°
    #         pitch = 0      : hedefin en cok 1.46 m USTUNDE olabiliriz
    #         pitch = -13.3° : en cok 2.76 m USTUNDE   (OLCULEN duruma gore
    #                          pencere neredeyse IKI KATI)
    #         alt taraf      : 5.40 m (pitch 0) / 4.65 m (pitch -13.3°) ALTTA
    #      ⭐ YANI dz=0'a nisan almak (carpisma icin gereken) kilit
    #         penceresinin TAM ORTASINDADIR — ofseti kaldirmanin sartname
    #         bedeli YOKTUR. Bu sinama o iddiayi kilitler.
    s10 = KilitSayaci()
    s10._ilan = True
    a.pitch = 0.0
    ku10 = Kutu(tohum=2, olcek=True, gurultu=False)
    bekle = [(0.0, True), (1.2, True), (2.0, False)]   # (ustunde m, kilit?)
    for ust, bkl in bekle:
        a.x, a.y, a.z = -math.sqrt(max(36.0 - ust * ust, 0.01)), 0.0, ust
        kk = ku10(a, 0.0, 0.0, 0.0, 1 / 62.0)
        if kk is None:
            an = False
        else:
            an = bool(s10.guncelle(
                {"cx": (0.5 + (kk[0] - CX) * Kal.KX) * 1920.0,
                 "cy": (0.5 + (kk[1] - CY) * Kal.KY) * 1080.0,
                 "w": kk[2] * Kal.DOW_F / F_YASA,
                 "h": kk[3] * Kal.DOW_F / F_YASA,
                 "W": 1920.0, "H": 1080.0}, 0.0))
        s10 = KilitSayaci()
        s10._ilan = True
        if an != bkl:
            h.append("kilit acisal kapisi: hedefin %.1f m ustunde kilit=%s, "
                     "beklenen %s (KX/KY olcegi bozuk olabilir)"
                     % (ust, an, bkl))
    a.x = a.y = a.z = 0.0

    # 10) TAAHHUT: yatay taahhut acikken (a) yasasi gercekten YAKLASMALI
    #     (yoksa CPA olcumu anlamsiz olur).
    r10 = [kosu(dikey="a", senaryo="duz", aspect0=0.0, R0=20.0, sure=25.0,
                tohum=i) for i in range(3)]
    if _med([x["cpa"] for x in r10]) > 3.0:
        h.append("taahhut calismiyor: (a) ile CPA medyani %.1f m (<3 bekleniyor)"
                 % _med([x["cpa"] for x in r10]))

    if not sessiz:
        print("  DIKEY OZ-SINAMASI: %s" % ("TAMAM (11/11)" if not h else "KALDI"))
        for x in h:
            print("    ! " + x)
    return h


# ══════════════════════════════════════════════════════════════════════════
#  CLI
# ══════════════════════════════════════════════════════════════════════════
def main():
    ap = argparse.ArgumentParser(description="dikey nisan tezgahi")
    ap.add_argument("--dogrula", action="store_true",
                    help="oz-sinama (11/11) — HER TARAMADAN ONCE")
    ap.add_argument("--sadakat", action="store_true")
    ap.add_argument("--kiyas", action="store_true")
    ap.add_argument("--tara", action="store_true")
    ap.add_argument("--limit", action="store_true")
    ap.add_argument("--tek", action="store_true")
    ap.add_argument("--hepsi", action="store_true")
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--sure", type=float, default=30.0)
    ap.add_argument("--vmax", type=float, default=24.0)
    ap.add_argument("--arkaplan", type=float, default=1.0,
                    help="alttan/ustten tespit orani (1.0 = ceza yok)")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    hepsi = a.hepsi or not any((a.dogrula, a.sadakat, a.kiyas, a.tara,
                                a.limit, a.tek))
    ORT = dict(sure=a.sure, v_max=a.vmax, arka_plan=a.arkaplan)

    print("=" * 100)
    print("DIKEY NISAN TEZGAHI   ISTASYON_ELEV=%.0f°  RANGE_SET=%.1f m  ->  "
          "tasarim ofseti %.2f m ALT" % (
              Dik.ISTASYON_ELEV, Dik.RANGE_SET,
              Dik.RANGE_SET * math.sin(math.radians(Dik.ISTASYON_ELEV))))
    print("  pitch trimi %.1f° (OLCULDU) | dikey ivme tavani %.1f m/s² "
          "(OLCULDU p95) | vz tavani %.1f m/s" % (
              Dik.PITCH_TRIM, Dik.AZ_MAX, Dik.VZ_MAX))
    print("  CARP = |dz|<%.1f m VE yatay<%.1f m | dz50 ISARETLI "
          "(negatif = hedefin ALTINDA)" % (Dik.TEMAS, Dik.TEMAS))
    print("  SAHA HEDEFI (bagimsiz olculdu, 17 en yakin gecis): "
          "yatay 0.60 m | dikey -1.29 m")
    print("=" * 100)

    if a.dogrula or hepsi:
        assert not dogrula_dikey(), "OZ-SINAMA KALDI — tarama gecersiz"

    if a.sadakat or hepsi:
        print("\n" + "=" * 100)
        print("SADAKAT — tezgah SAHAYI yeniden uretiyor mu? (yasa (a), bugunku hal)")
        print("=" * 100)
        print(baslik())
        r = kume(a.n, dikey="a", **ORT)
        print(ozet("(a) OLCULEN tezgah", r))
        print(ozet("(a) ESKI tezgah (pitch=0, dikey ivme sinirsiz)",
                   kume(a.n, dikey="a", pitch_trim=0.0, az_max=None, **ORT)))
        print("\n  SAHA: |dz| 1.29 m, yatay 0.60 m (3B<2 m olan 17 gecis)")

    if a.kiyas or hepsi:
        print("\n" + "=" * 100)
        print("ANA KIYAS — DIKEY NISAN YAPILARI, TUM SENARYOLAR x TUM ASPECT'LER")
        print("  senaryo x aspect x tohum = %d x %d x %d = %d angajman/yapi"
              % (len(SENARYO), len(ASPECT), a.n,
                 len(SENARYO) * len(ASPECT) * a.n))
        print("=" * 100)
        yap = [("(a) sabit 15° [BUGUN]", "a", {}),
               ("(b) TERM_DIKEY 6 m", "b", dict(ESIK=6.0)),
               ("(b) TERM_DIKEY 8 m", "b", dict(ESIK=8.0)),
               ("(b) TERM_DIKEY 12 m", "b", dict(ESIK=12.0)),
               ("(b) TERM_DIKEY 20 m", "b", dict(ESIK=20.0)),
               ("(c) kesisim R<8 m", "c", dict(R_TETIK=8.0)),
               ("(c) kesisim R<16 m", "c", dict(R_TETIK=16.0)),
               ("(c) kesisim R<30 m", "c", dict(R_TETIK=30.0)),
               ("(d) t_go TEK tetik", "d", dict(R_BASLA=0.0)),
               ("(D) t_go 3.0 + R 14 m [ONERI]", "d", {}),
               ("(e) merkez (ofset yok)", "e", {})]
        tum = []
        for ad, d, kw in yap:
            tum.append((ad, kume(a.n, dikey=d, dikey_kw=kw, **ORT)))
        print(baslik())
        for ad, r in tum:
            print(ozet(ad, r))

        def hucre(r):
            if not r:
                return "     -"
            t = [x for x in r if x["tamam"]] or r
            return "%3.0f%%/%.2f" % (
                100.0 * sum(1 for x in r if x["carpti"]) / len(r),
                _med([abs(x["cpa_dz"]) for x in t]))
        print("\n  == SENARYO KIRILIMI (CARP%% / |dz|50) ==")
        print("  %-23s%s" % ("yapi", "".join("%10s" % s for s in SENARYO)))
        for ad, r in tum:
            print("  %-23s%s" % (ad, "".join(
                "%10s" % hucre(dilim(r, senaryo=s)) for s in SENARYO)))
        print("\n  == ASPECT KIRILIMI (CARP%% / |dz|50) ==")
        print("  %-23s%s" % ("yapi", "".join(
            "%12s" % ("aspect %.0f" % x) for x in ASPECT)))
        for ad, r in tum:
            print("  %-23s%s" % (ad, "".join(
                "%12s" % hucre(dilim(r, aspect=x)) for x in ASPECT)))
        print("\n  == ANGAJMAN TAMAMLAMA (TAM%%) — EDINIM, dikey nisandan BAGIMSIZ ==")
        ad0, r0 = tum[0]
        print("  %-23s%s" % ("senaryo", "".join("%10s" % s for s in SENARYO)))
        print("  %-23s%s" % ("TAM%", "".join(
            "%9.0f%%" % (100.0 * sum(1 for x in dilim(r0, senaryo=s)
                                     if x["tamam"]) / max(len(dilim(r0, senaryo=s)), 1))
            for s in SENARYO)))
        print("  %-23s%s" % ("aspect", "".join(
            "%10.0f" % x for x in ASPECT)))
        print("  %-23s%s" % ("TAM%", "".join(
            "%9.0f%%" % (100.0 * sum(1 for x in dilim(r0, aspect=x)
                                     if x["tamam"]) / max(len(dilim(r0, aspect=x)), 1))
            for x in ASPECT)))

    if a.tara or hepsi:
        print("\n" + "=" * 100)
        print("TARAMA — (d) parametreleri ve dikey yetki")
        print("=" * 100)
        print(baslik())
        for tb in (1.0, 1.5, 2.0, 3.0, 4.0):
            print(ozet("(d) T_BASLA=%.1f s" % tb,
                       kume(a.n, dikey="d", dikey_kw=dict(T_BASLA=tb), **ORT)))
        for nz in (1.0, 1.3, 1.6, 2.2, 3.0):
            print(ozet("(d) N_Z=%.1f" % nz,
                       kume(a.n, dikey="d", dikey_kw=dict(N_Z=nz), **ORT)))
        for kz in (0.6, 1.0, 1.6, 2.4):
            print(ozet("(b8) K_Z=%.1f" % kz,
                       kume(a.n, dikey="b",
                            dikey_kw=dict(ESIK=8.0, K_Z=kz), **ORT)))
        print("\n  == DIKEY YETKI (hem (b) hem (d)) ==")
        for azm in (1.5, 3.0, 5.0, 10.0):
            Dik.AZ_MAX = azm
            print(ozet("a_z tavan %.1f m/s²  (b8)" % azm,
                       kume(a.n, dikey="b", dikey_kw=dict(ESIK=8.0),
                            az_max=azm, **ORT)))
            print(ozet("a_z tavan %.1f m/s²  (d)" % azm,
                       kume(a.n, dikey="d", az_max=azm, **ORT)))
        Dik.AZ_MAX = 3.0
        for vzm in (2.0, 3.0, 5.0):
            _s = Dik.VZ_MAX
            Dik.VZ_MAX = vzm
            print(ozet("vz tavan %.1f m/s  (d)" % vzm,
                       kume(a.n, dikey="d", **ORT)))
            Dik.VZ_MAX = _s

    if a.limit or hepsi:
        print("\n" + "=" * 100)
        print("NEREDE BOZULUYOR")
        print("=" * 100)
        print(baslik())
        for ad, d, kw in (("(a) sabit", "a", {}),
                          ("(b) esik 8 m", "b", dict(ESIK=8.0)),
                          ("(d) t_go", "d", {})):
            print("  -- %s --" % ad)
            for vm in (19.0, 22.0, 24.0, 28.0):
                print(ozet("  v_max=%.0f (mu=%.2f)" % (vm, 17.98 / vm),
                           kume(a.n, dikey=d, dikey_kw=kw,
                                **dict(ORT, v_max=vm))))
            for R0 in (13.0, 20.0, 33.0):
                print(ozet("  devir R0=%.0f m" % R0,
                           kume(a.n, dikey=d, dikey_kw=kw,
                                **dict(ORT, R0=R0))))
        print("\n  == TEZGAH KUSURLARININ ETKISI (ablasyon) ==")
        print(baslik())
        for ad, kw in (("OLCULEN tezgah", {}),
                       ("pitch trimi YOK (eski)", dict(pitch_trim=0.0)),
                       ("dikey ivme siniri YOK (eski)", dict(az_max=None)),
                       ("ikisi de YOK (eski tezgah)",
                        dict(pitch_trim=0.0, az_max=None)),
                       ("olcum hatasi KAPALI",
                        dict(hata=HataAyari.kapali(), kutu_gurultu=False))):
            for d, dk, e in (("a", {}, "(a)"), ("b", dict(ESIK=8.0), "(b8)"),
                             ("d", {}, "(d)")):
                print(ozet("%s %s" % (e, ad),
                           kume(a.n, dikey=d, dikey_kw=dk, **dict(ORT, **kw))))

    if a.tek or hepsi:
        print("\n" + "=" * 100)
        print("TEK ANGAJMAN DOKUMU (gercek iz, aspect0=45°) — (a) ve (d)")
        print("=" * 100)
        for d, ad in (("a", "(a) sabit 15°"), ("d", "(d) t_go")):
            r = kosu(dikey=d, senaryo="gercek", aspect0=45.0, R0=25.0,
                     kayit=True, tohum=1, **ORT)
            print("\n  %s  CPA %.2f m (dz %+.2f, yatay %.2f) carpti=%s"
                  % (ad, r["cpa"], r["cpa_dz"], r["cpa_yatay"], r["carpti"]))
            print("    %6s%8s%8s%8s%8s%8s%8s%7s%7s%4s" % (
                "t", "R", "R_kes", "dz", "dz_ist", "vz_cmd", "vz", "asp",
                "|v|", "det"))
            iz = r["iz"]
            for i in range(0, len(iz), max(1, len(iz) // 20)):
                print("    %6.1f%8.2f%8.2f%8.2f%8.2f%8.2f%8.2f%7.1f%7.1f%4d"
                      % tuple(iz[i]))
            if iz:
                print("    %6.1f%8.2f%8.2f%8.2f%8.2f%8.2f%8.2f%7.1f%7.1f%4d"
                      % tuple(iz[-1]))


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
control/visual_tracking.py — GORSEL FAZ: IBVS (goruntu-tabanli gorsel servolama).

TEK FIKIR: kontrol hatasi dogrudan GORUNTU UZAYINDA tanimlanir (piksel);
hedefin 3B konumunu kestirmeye gerek yoktur.

    menzil (R)   = RANGE_C_REF / kutu_boyutu          (benzer ucgenler, p = C/R)
    kerteriz     = piksel + KENDI IMU'muz          (ego-motion telafili)
    yaw          = burnu kerterize cevir
    ileri hiz    = KAPANMA HIZI denetimi: v_yer = v_hedef_LOS + K*(R - TRAIL)
                   -> profil TRAIL_RANGE_M'de sifirlanir, arac kuyruga OTURUR
    dikey hiz    = hedefi KADRAJDA sabit yukseklikte tut (cy -> cy_ref)

⛔⛔ YARISMA KURALI — YAPISAL GARANTI
  Bu modulun girdileri: bbox pikselleri + KENDI IMU/hizimiz. Hedefin GPS'i,
  konumu, menzil telemetrisi FONKSIYON IMZALARINDA YOKTUR -> gorsel fazda
  kural ihlali yapisal olarak IMKANSIZDIR. `own_*` degerleri kendi
  sensorlerimizdir (ego-motion telafisi), hedef verisi DEGILDIR.

NEDEN ESKI YASA BIRAKILDI (olculdu, kardes depo drones_of_war_entegrasyon):
  Eski yasa cubugu dogrudan suruyordu (thr = K*ey, pitch = ILERI*fren...) ve
  arac zarfini bilmiyordu. Yeni yasa HIZ SETPOINT'i uretir; control.common
  icindeki OLCULMUS cevirici cubuga cevirir. Ayrica:
   * Dikeyde saf takip (hiz vektorunu 3B'de hedefe nisanlamak) COKTU: 24
     derece yukseliste 28*sin(24) = 11.4 m/s tirmanma komutu veriyor, arac
     hedefin HIZASINA cikiyor ve kamera 26.5 derece YUKARI baktigi icin hedef
     GORUNMUYORDU (tespit %90 -> %12-15, isabet 0/3). Yerine KADRAJ
     REGULASYONU kondu.
   * Kadraj kanalinda KAZANC ve TAVAN birlikte ayarlandi (E1+E1b, n=8/kol):
        olcut              0.06/1.5   0.014/4.0
        TEMAS                6/8        8/8
        en_yakin medyan     0.86 m     0.51 m   (-%41)
        tespit%             59.00      70.80
        gorsel kesinti     10.20 s     2.05 s   (5 kat az)
        DOYUM orani         %97.0      %17.7    <- mekanizma kaniti
     Eski cift (0.06/1.5) dikey kanali orantili kontrolcu degil AC-KAPA
     anahtari yapiyordu: |e_cy|>25 px olan HER kare doyumdaydi.
   * DIKEY TAVAN (VZ_CAP_VISUAL) tespiti en cok bozan buyuklugu kisar
     (B7, n=4/kol): isabet 3/4 -> 4/4, en_yakin 3.00 -> 0.72 m,
     tespit %20.7 -> %50.9, roll p90 12.6 -> 5.55 derece. Mekanizma: kamera
     GOVDEYE SABIT; dikey komut throttle'i sicratiyor, arac savruluyor ve
     70 px'lik hedef bulaniyor.
   * KUTU KOPRUSU (olu-hesap, B2/B5 n=4/kol): isabet 1/4 -> 4/4, en yakin
     menzil medyani 5.44 -> 1.94 m, roll p90 48.65 -> 27.05 derece. Sure
     tarandi: 0.3 -> 3.35 m, 0.5 -> 1.90 m, 1.0 -> 1.34 m (kazanan).
"""
import math
import time

from control.common import ConverterCfg, VelocityToStick, clamp, wrap_deg


# ==========================================================
#  KAMERA MODELI — OLCULDU (kalibrasyon referansi 1920x1080)
# ==========================================================
# Kamera GOVDEYE SABIT (gimbal yok) ve burnun TILT derece YUKARISINA bakar.
# Arac one yatinca kamera da onunla asagi doner; telafi edilmezse hedef
# kadrajin altindan kacar.
#
# KALIBRASYON: gercek geometriden ongorulen kadraj konumu ile olculen bbox
# merkezi arasinda en kucuk kareler, fx=fy kisitli. Artik 2.6 px (n=614).
#   TILT 25.00 -> artik 5.10 px   (SDK basliginin yazdigi deger)
#   TILT 26.50 -> artik 2.56 px   <- EN IYI
#   TILT 28.00 -> artik 5.14 px
# Bootstrap (60 yeniden ornekleme): 26.57 +- 0.11 derece. 25 KESIN ELENIR.
#
# ⚠ SDK basligi "25 derece tilt, 125 derece FOV" diyor; olcum 26.5 / HFOV
#   121.2 buldu. Belge bu maddede guvenilmez, kendi olcumumuz esastir.
REF_W, REF_H = 1920.0, 1080.0
TILT_DEG = 26.50     # kamera ekseninin burna gore YUKARI acisi
F_PX_REF = 540.4     # odak uzunlugu (px) @1920 genislik; fx = fy
RANGE_C_REF = 997.0  # px*m @1920;  R = RANGE_C_REF / kutu boyutu
# ⚠ RANGE_C_REF ampiriktir (n=59 gercek tespit; %25-75: 855-1060). Geometrik
#   beklenen f * kanat_acikligi = 540.4 * 1.718 (Talon, belge) = 928;
#   olculen/beklenen = 1.07 (bbox kanat uclarindan biraz tasiyor).


def _scale(W):
    """Yakalanan kare genisliginin kalibrasyon referansina orani.

    Ekran yakalama cozunurlugu 1920 olmak zorunda degil. Sabit FOV'da odak
    uzunlugu ve piksel cinsinden her buyukluk genislikle DOGRUSAL olcekler;
    tek carpan yeter. (16:9 disi bir kadrajda oyunun FOV'u da degisir —
    o durumda kalibrasyon yenilenmelidir.)
    """
    return float(W) / REF_W


def f_px(W):
    return F_PX_REF * _scale(W)


def range_m(box_px, W):
    """Kutu boyutundan menzil (m). Delik-igne benzer ucgenler: p = C/R."""
    if box_px <= 0:
        return None
    return (RANGE_C_REF * _scale(W)) / float(box_px)


def pixel_angle(cx_px, cy_px, W, H):
    """Kadraj konumundan KAMERA EKSENINE gore (yatay, dikey) aci (derece).
    dikey > 0 = kamera ekseninin USTUNDE."""
    f = f_px(W)
    return (math.degrees(math.atan((cx_px - W / 2.0) / f)),
            math.degrees(math.atan((H / 2.0 - cy_px) / f)))


def pixel_bearing(cx_px, cy_px, own_pitch_deg, own_roll_deg, W, H):
    """Kadraj konumundan GOVDE-BAGIMSIZ kerteriz (azimut, yukselis) derece.
    Kendi pitch/roll'umuz telafi edilir.

    ⭐ GIRDI YALNIZ: bbox pikselleri + KENDI IMU'muz -> gorsel fazda mesru.
    """
    horiz, vert = pixel_angle(cx_px, cy_px, W, H)
    # kamera ekseni = burun + TILT yukari; govde pitch'i (negatif = burun
    # asagi) kamera eksenini o kadar asagi cevirir.
    elevation = vert + TILT_DEG + own_pitch_deg
    if own_roll_deg:  # roll bilesenleri karistirir
        r = math.radians(own_roll_deg)
        c, s = math.cos(r), math.sin(r)
        horiz, elevation = horiz * c - elevation * s, horiz * s + elevation * c
    return horiz, elevation


def bearing_pixel(azimuth_deg, elevation_deg, own_pitch_deg, own_roll_deg, W, H):
    """`pixel_bearing`in TAM TERSI: kerterizden kadraj konumu (cx, cy).

    ⚠ SIRA ONEMLI. Ileri donusum ONCE kaydirir (dik + TILT + pitch), SONRA
      roll ile dondurur; tersi bu yuzden ONCE -roll dondurup SONRA kaydirmayi
      geri almalidir. (Ters sirada yazildiginda 30 derece yatista 3.9 derece
      hata veriyordu — yani koprunun EN COK gerektigi anda bozuluyordu.)
    """
    horiz, elev = azimuth_deg, elevation_deg
    if own_roll_deg:
        r = math.radians(own_roll_deg)
        c, s = math.cos(r), math.sin(r)
        horiz, elev = horiz * c + elev * s, -horiz * s + elev * c
    vert = elev - TILT_DEG - own_pitch_deg
    f = f_px(W)
    return (W / 2.0 + f * math.tan(math.radians(horiz)),
            H / 2.0 - f * math.tan(math.radians(vert)))


# ==========================================================
#  AYARLAR
# ==========================================================
class Cfg:
    # ============ GECERLILIK KAPISI (TEK KAPI) ============
    # Devir kapisi da (control/main.py :: PhaseSupervisor) `aim_box`yu kullanir.
    # Iki katmana AYRI esik yazmak, gorsel fazin ayni karede reddettigi bir
    # kutuyla devir yapilmasina ve fazin surekli sekmesine yol acar.
    CONF_MIN = 0.40     # OLCULDU: esik 0.10'da tespit %49 / argmax dogru %43,
                        # 0.40'ta %40 / %40 -> ~9 puan tespit karsiliginda
                        # yanlis-pozitifin argmax'i calmasi TAMAMEN biter.
    SIZE_MIN_PX = 8.0   # px @1920; bundan kucuk kutu guvenilmez
    RANGE_MAX_M = 50.0  # m; otesinde gorsel devir YOK (tespit %9-10)
    RANGE_MIN_M = 3.0   # m; ALTINDAKI kutu = dev yanlis-pozitif.
    # ⚠ ESKI `BOYUT_MAX=0.85` (kadraj orani tavani) YERINE MENZIL ARALIGI.
    #   Eski notumuz "sinir gevsek kalsin, yoksa gercek vurusu keser" diyordu
    #   ve o zaman DOGRUYDU: elde kopru yoktu, kutu reddedilince guduum KOR
    #   kaliyordu. Artik BRIDGE_S boyunca son gecerli kutu KENDI donusumuzle
    #   ileri tasiniyor -> son metrelerde nisan kaybolmuyor. Buna karsilik
    #   140 m'de uretilen dev yanlis-pozitif (menzilden 1.3 m cikan kutu)
    #   kapiyi ACIYOR ve guduum "temas" sanip tam hucum veriyordu; iki kosuda
    #   arac yere cakildi. Menzil araligi tam bu hatayi keser.
    STALE_S = 0.5       # s; tespit bundan eskiyse "yeni kare yok" say

    # ============ DEVIR KILIDI: SURE **VE** KARE (ikisi birden) ============
    HANDOFF_LOCK_S = 1.0  # s; kesintisiz gorsel kanit SURESI
    HANDOFF_FRAMES = 10   # ard arda GECERLI KARE (taban)
    # ⭐ KAPI SUREYE BAGLANDI (2026-08-24). Eskiden yalniz kare sayilirdi ve
    #   "10 kare" DEDEKTOR HIZINA gore bambaska bir kanit demekti:
    #       ~10 Hz (tasarim varsayimi) -> 1.00 s   <- hedeflenen
    #       29.9 FPS (olculdu, eski senkron hat) -> 0.33 s
    #       53.2 FPS (olculdu, ayri yakalama thread'i) -> 0.19 s
    #   Yani hattin hizlanmasi kapiyi SESSIZCE zayiflatiyordu. Kardes depoda
    #   olculen faz cirpinmasinin (190 s'de 6-12 faz degisimi, gorsel faz omru
    #   medyan 3.6-5.2 s) kok nedeni zayif kanitla acilan devir kapisiydi.
    #
    # ⛔ SURE TEK BASINA YETMEZ, kare tabani da SART. Kamera thread'i DONARSA
    #   kare sayaci ilerlemez ama duvar saati ilerler: saf sure kapisi donmus
    #   bir goruntudeki kutuyla acilirdi. Iki kosul birlikte:
    #       gecen sure >= HANDOFF_LOCK_S  VE  ayri kare >= HANDOFF_FRAMES
    #   Fiili kapi = max(ikisi). 10 Hz'de ikisi de ~1.0 s -> tasarim davranisi
    #   aynen korunur; 53 FPS'te sure baglar; 2 Hz'de kare tabani baglar.
    #
    # ⚠ KAPI GEC ACILIYORSA once HANDOFF_LOCK_S'i dusurun (1.0 -> 0.7 -> 0.5).
    #   Yalniz HANDOFF_FRAMES'i dusurmek hizli dedektorde HICBIR SEY DEGISTIRMEZ,
    #   cunku orada baglayan kosul suredir.
    #
    # Kayip esigi de SURE cinsindendir (main.Cfg.LOST_S) — ayni gerekce.

    # ============ ILERI HIZ: yatay hiz tavani ============
    V_MAX = 28.0          # m/s; YATAY HIZ TAVANI (hucum hizi DEGIL — yalnizca
                          # kirpma siniri). Talon 17.98 m/s uctugu icin 18 ile
                          # kapanma 0.02 m/s = asla yakalayamayiz. Arac 34.6
                          # yapabiliyor; 28 -> kapanma ~10 m/s. (Tavanin tamami
                          # kullanilmadi: hiz butcesi dikeyle paylasiliyor.)
    V_MIN = 0.0           # m/s; asla geri gitme

    # ⛔⛔ HUCUM (KAMIKAZE) YASASI DEVRE DISI — 2026-08-25, kullanici karari.
    #   Su anki amac TEMAS degil, KAMERA TAKIBINI iyilestirmek. Asagidaki dort
    #   sabit yalnizca eski "temas kutusuna kadar tam gaz" PI'sine aitti ve o
    #   dal `compute()`ten KALDIRILDI. Olculmus degerler geri donus icin
    #   duruyor; geri acmak isterseniz `compute()` icindeki ileri hiz dalini da
    #   geri yazmaniz gerekir (git: bu commit'ten onceki surum).
    #
    #   ⚠ AKTIF YASA ZATEN HUCUM DEGIL: kapanma profili `TRAIL_RANGE_M`(3 m)
    #     de sifirlanir, `ATTACK_RANGE_M`(1 m) de degil -> arac hedefin
    #     kuyruguna oturur ve orada KALIR. Bu satirlarin kaldirilmasi guduum
    #     davranisini DEGISTIRMEZ; yalnizca olu dali ve yaniltici adi siler.
    #
    # ATTACK_RANGE_M = 1.0  # m; PI'nin sifir noktasi = TEMAS menzili. "Su
    #                       # menzilde dur" noktasi YOK -> hata hep pozitif
    #                       # kalir, hiz tavanda oturur, kapanma sabit olur.
    # K_FWD = 0.35          # (m/s)/px @1920; P kazanci
    # K_I = 0.04            # (m/s)/(px*s) @1920; I kazanci
    # I_MAX = 8.0           # m/s; integral doyumu

    # ============ KAPANMA HIZI DENETIMI ============
    # ⛔ ESKI YASANIN KUSURU (olculdu, kodun kendisinden turetildi): yukaridaki
    #   PI, guduum zarfinin TAMAMINDA doygundur -> kontrolcu degil, SABITTIR:
    #       R (m)   50     30     10      5      3     2     1.1    1.0
    #       v       28.0   28.0   28.0   28.0   28.0  28.0   28.0   8.0
    #   Talon 17.98 m/s uctugu icin bu, 3-50 m boyunca SABIT 10 m/s goreli
    #   kapanma demektir ve yasa hicbir yerde yavaslamaz. 28 m/s'den durma
    #   mesafesi 11.5 m (a=34 m/s^2); son 1 m icinde yavaslamak FIZIKSEL OLARAK
    #   imkansiz. Ustune RANGE_MIN_M=3 altinda kutu REDDEDILIR, kopruye dusulur
    #   ve kopruda kutu boyutu DONDUGU icin komut 28'de cakili kalir: 1 s kor
    #   ucusta 10 m goreli yol. Sonuc: arac hedefi vurmak yerine ONUNE GECIYOR.
    #
    # ⭐ COZUM: yer hizi degil KAPANMA hizi denetlenir.
    #       v_yer = v_hedef_LOS + v_kapanma(R)
    #   Hedefin LOS hizi PIKSELDEN turetilir (GPS YOK):
    #       R = C / kutu_boyutu           -> menzil
    #       Rdot = d(R)/dt  (suzulmus)    -> goreli kapanma hizi
    #       v_hedef_LOS = kendi_LOS_hizimiz + Rdot
    #   Girdi yalnizca kutu pikselleri + KENDI hiz vektorumuz -> §KATI KURAL temiz,
    #   `compute` imzasi DEGISMEDI.
    #
    # Bu, GPS istasyon yasasindaki ILERI BESLEME ile ayni fikirdir: saf P
    # hareketli hedefi yakalayamaz (bkz. gps_approach basligi). Gorsel fazda
    # hedef hizini GNSS'ten alamayiz, o yuzden KUTU BUYUMESINDEN kestiriyoruz.
    # CLOSE_CONTROL = True  # eski A/B anahtari; TEK YASA kaldi (bkz. yukarisi)

    # ⛔ PROFIL `TRAIL_RANGE_M`'DE SIFIRLANIR, `ATTACK_RANGE_M`'DE DEGIL.
    #   Neden: `RANGE_MIN_M`(3 m) altinda `aim_box` kutuyu REDDEDER (dev
    #   yanlis-pozitif korumasi, iki cakilmayla olculdu). Yani 3 m'nin ALTINI
    #   HIC GORMUYORUZ. Ardindan BRIDGE_S(1 s) olu-hesap + LOST_S(2 s) "son
    #   komutu tut" gelir -> 3 SANIYE KOR UCUS. 1 m'ye regule etmek, kapali
    #   cevrimde ulasilamayan bir noktaya nisan almaktir: yasa 3 m'de ne hizla
    #   birakirsa arac onu 3 s tasir. Eski yasa orada 28 m/s biraktigi icin
    #   hedefin ~30 m onune geciyordu.
    #   Profil goru sinirinda sifirlaninca arac hedefin KUYRUGUNA oturur ve
    #   orada KALIR — "one gecme" yapisal olarak biter.
    #   ⚠ TRAIL_RANGE_M = ATTACK_RANGE_M yaparsaniz eski kamikaze niyeti geri
    #     gelir AMA kor bolge durdugu icin one gecme de geri gelir. Once kor
    #     bolgeyi kucultun (RANGE_MIN_M / RANGE_C_REF kalibrasyonu), sonra bunu.
    TRAIL_RANGE_M = 3.0   # m; kapanma hizinin sifirlandigi menzil (= RANGE_MIN_M)

    # ⛔ PROFIL ORANTISALDIR, sabit-yavaslama (sqrt) DEGIL.
    #   sqrt(2*a*mesafe) profili zaman-optimaldir ama SIFIR sonumleme payi
    #   birakir: tam olarak "son metrede durabilecek" hizi komut eder. Bizim
    #   ic hiz dongumuzun zaman sabiti 1/K_V = 0.67 s (common.ConverterCfg) ve
    #   ustune 46 ms olu zaman + ~100 ms tespit gecikmesi biner. 6 m/s ile
    #   yaklasirken 0.67 s'de 4 m yol gider — elde 3 m varken. Yani sqrt profili
    #   KAGIT USTUNDE durur, gercekte hep asar (simulasyonda 5 kez one gecti).
    #   Orantisal profil ussel yaklasir: menzil dongusu 1/K_CLOSE = 1.67 s ile
    #   ic dongudén 2.5 KAT YAVAS -> kaskad kurali korunur (bkz. K_V yorumu).
    #   Kiyas: GPS istasyon yasasi ayni aileden bir kazanc kullaniyor
    #   (GPSCfg.STATION_KP = 0.9); gorsel menzil kestirimi daha gurultulu
    #   oldugu icin burada bilincli olarak daha yumusak.
    K_CLOSE = 0.6         # 1/s; v_kapanma = K_CLOSE * (R - TRAIL_RANGE_M)
                          #  Aracin olculmus ivmesi 34; 6 BILINCLI olarak
                          #  muhafazakar (olu zaman 46 ms + yatis 0.211 s +
                          #  ~1 kare tespit gecikmesi profilin icinde kalsin).
    V_CLOSE_MAX = 12.0    # m/s; azami kapanma hizi. 12 -> uzak menzilde
                          #  v_yer = 18 + 12 = 30 -> zaten V_MAX'e kirpilir,
                          #  yani UZAK MENZILDE DAVRANIS AYNEN KORUNUR.
    R_TAU = 0.20          # s; profilde kullanilan menzilin suzgeci (hafif)
    V_TGT_TAU = 0.5       # s; HEDEF HIZI kestiriminin suzgeci. TARANDI
                          #  (5 tohum/kol, 'hedefin one gecmesi' m / gecis):
                          #    tau  temiz      gurultu+kayip   manevra
                          #    0.5  0.0 m / 0   0.0 m / 0      7.7 m / 2  <- SECILDI
                          #    1.0  0.0 m / 0   0.0 m / 0      9.3 m / 3
                          #    1.5  0.0 m / 0   0.0 m / 0      9.7 m / 3
                          #    2.5  0.0 m / 0   0.0 m / 0      9.5 m / 3
                          #  Kisa tau manevrayi daha iyi izliyor ve gurultulu
                          #  kolda BEDEL uretmiyor -> tek yonlu iyilesme.
    # ⛔ SUZGEC EN SONA KONUR, terimlere DEGIL. `v_hedef = own_los + Rdot`
    #   toplaminda iki terimi FARKLI gecikmeyle suzmek (own_los ani, Rdot
    #   suzulmus) gecikme farki kadar sistematik hata uretir ve bu hata
    #   komuta geri beslenir. Olculdu: R 3-11 m arasinda LIMIT CEVRIME girdi,
    #   hedef hizi kestirimi 0.5 ile 28 m/s arasinda savruldu. Dogrusu: iki
    #   terim de GECIKMESIZ alinip TOPLAM bir kez suzulur.
    # ⚠ Uzun zaman sabiti fiziksel olarak mesru: hedefin hizi YAVAS degisen
    #   bir buyukluktur (Talon 17.98 m/s sabit ucuyor), menzil olcumu ise
    #   gurultuludur (RANGE_C_REF %25-75 araligi 855-1060 = ~%10).

    # ============ YAW ============
    K_YAW = 1.0           # kerteriz -> burun hedefi (tam duzeltme)
    KP_YAW_RATE = 3.0     # yaw hatasi (derece) -> yaw hizi (derece/s)
    # derece/s. Arac 214 yapabiliyor AMA hizli yaw goruntuyu bulandirip
    # dedektoru kirar -> BILINCLI olarak 120'de tutuluyor (ConverterCfg).
    YAW_RATE_MAX = ConverterCfg.YAW_RATE_MAX_DEG
    YAW_DEADBAND = 1.0    # derece; altinda yaw duzeltmesi uretilmez

    # ============ DIKEY: KADRAJ REGULASYONU ("alttan vurus") ============
    #   cy > cy_ref -> hedef kadrajda ASAGIDA -> biz YUKSEKTEYIZ -> ALCAL
    #   cy < cy_ref -> hedef kadrajda YUKARIDA -> biz ALCAKTAYIZ -> TIRMAN
    # Kamera govdeye sabit ve TILT derece yukari baktigi icin "hedefi kadrajin
    # surasinda tut" demek "hedefin ALTINDA su aciyla kal" demektir; geometri
    # kendiliginden cikar. GIRDI YALNIZ PIKSEL.
    K_CY = 0.014             # (m/s)/px @1080 yukseklik
    CY_REF_FAR = 470.0       # px @1080; UZAKTA hedefi merkezin USTUNDE tut
    CY_REF_NEAR = 540.0      # px @1080; YAKINDA merkeze getir (nisan al, vur)
    CY_BLEND_PX_FAR = 40.0   # px @1920; kutu bundan buyudukce "yakin" sayilir
    CY_BLEND_PX_NEAR = 90.0  # px @1920
    VZ_CAP_VISUAL = 4.0      # m/s; dikey yumusatma tavani (bkz. baslik, B7)
    # ⛔ Zarf TEK KAYNAKTAN (control.common.ConverterCfg) — buraya sayi yazmayin.
    VZ_MAX_CLIMB = ConverterCfg.VZ_MAX_CLIMB
    VZ_MAX_DESCENT = ConverterCfg.VZ_MAX_DESCENT
    # ⭐ YAPISAL UYUM: aracin dikey asimetrisi (guclu tirmanma, zayif alcalma)
    #   guduumun ihtiyaciyla ORTUSUYOR. Kamera yukari baktigi icin hedefi
    #   kadrajda tutmak araci hedefin ALTINDA tutar; oradan hedefe gitmek
    #   TIRMANMAKTIR — bol yetkimiz olan yon.

    # ============ KUTU KOPRUSU (olu-hesap) ============
    BRIDGE_S = 1.0  # s; son gecerli kutunun ATALET yonu bu kadar yasar
    # Cikarim ~10 Hz; aradaki ~100 ms'de ve tespit bosluklarinda guduum BAYAT
    # kutuyla calisir. Kutunun kerteriz (atalet) yonu saklanip KENDI donusumuz
    # telafi edilerek kutu kadrajda ileri tasinir. GIRDI YALNIZ: son kutu +
    # KENDI IMU'muz -> GPS YOK, menzil YOK.


# ==========================================================
#  KAPILAR (gozetmen ve gorsel faz AYNISINI kullanir)
# ==========================================================
def aim_box(det, cfg=Cfg):
    """Bu tespit guduume girebilir mi? Giremezse None (tespit yok sayilir)."""
    if det is None:
        return None
    W = float(det.get("W", 0)); H = float(det.get("H", 0))
    if W <= 1 or H <= 1:
        return None
    if float(det.get("conf", 0.0)) < float(cfg.CONF_MIN):
        return None
    s = _scale(W)
    size = max(float(det.get("w", 0.0)), float(det.get("h", 0.0)))
    if size < float(cfg.SIZE_MIN_PX) * s:
        return None
    R = range_m(size, W)
    if R is None or R > float(cfg.RANGE_MAX_M) or R < float(cfg.RANGE_MIN_M):
        return None
    cx = float(det.get("cx", -1.0)); cy = float(det.get("cy", -1.0))
    if not (0 <= cx < W and 0 <= cy < H):
        return None
    return det


def is_stale(det, cfg=Cfg, now=None):
    """Tespit STALE_S'ten eski mi? (dedektor 8-10 Hz, guduum 50 Hz -> ayni
    kutu birkac tik tekrar gorunur; bu NORMALDIR. Bayatlik esigi gercek
    kaybi ayirir; kaybin kendisini KOPRU tasir.)"""
    if det is None or det.get("t") is None:
        return True
    now = time.perf_counter() if now is None else now
    return (now - float(det["t"])) > float(cfg.STALE_S)


# ==========================================================
#  GORSEL FAZ SURUCUSU
# ==========================================================
class VisualTracker:
    """IBVS gorsel guduum. Durum: hiz integrali + kutu koprusu."""

    def __init__(self, cfg=Cfg):
        self.cfg = cfg
        self.conv = VelocityToStick()  # DURUMSUZ
        self.reset()

    def reset(self):
        """Her yeni gorsel faz basinda cagrilir (devir / GPS'e donus sonrasi)."""
        self._bridge = None     # son gecerli kutunun ATALET yonu
        self._bridge_count = 0  # mekanizma sutunu: kac kare koprude uculdu
        # --- kapanma hizi denetimi durumu ---
        self._R_f = None        # suzulmus menzil (m) — profil bunu kullanir
        self._R_prev = None     # son OLCUM menzili (turev icin)
        self._dt_acc = 0.0      # iki menzil olcumu arasi birikmis sure (s)
        self._Rdot = 0.0        # menzil turevi (m/s; NEGATIF = kapaniyor)
        self._v_tgt_los = None  # hedefin LOS boyunca hizi (m/s) — kutudan turetildi
        self._v_cmd = 0.0       # son ileri hiz komutu (koprude DONDURULUR)
        self._tlm = {}

    # ------------------------------------------------------------------
    def _closing_speed(self, R, yaw_des_deg, own_vel_ms, dt, bridge):
        """Kapanma hizi denetimli ileri hiz (m/s, YER hizi).

        ⛔ GIRDI YALNIZ: kutu boyutundan turetilen menzil + KENDI hiz
          vektorumuz. Hedefin GPS'i/konumu/telemetrisi YOK -> §KATI KURAL temiz.

        ⚠ KOPRUDE GUNCELLEME YOK. Kopru kutusunun boyutu DONDURULMUSTUR (son
          gercek tespitin w/h'si taşinir), yani R sabit gorunur ve Rdot yapay
          olarak 0'a duser. O anda `own_los`u yeniden okursak "hedef bizimle
          ayni hizda" sonucu cikar ve komut her tik kendi hizimizin uzerine
          v_kapanma ekleyerek KACAK HIZLANMA uretir. Bu yuzden koprude son
          komut aynen tutulur.
        """
        p = self.cfg
        if R is None or dt <= 0.0:
            return self._v_cmd
        if bridge and self._v_tgt_los is not None:
            return self._v_cmd  # kor ucus: son komutu tut, kestirimi bozma

        # (a) profil menzili — hafif suzgec (kutu boyutu ~%10 gurultulu)
        self._R_f = R if self._R_f is None else (
            self._R_f + (dt / (float(p.R_TAU) + dt)) * (R - self._R_f))

        # (b) menzil turevi — YENI olcum geldiginde, gectigi SURE ile.
        #     Dedektor ~10 Hz, dongu 50 Hz: R ard arda tiklerde AYNI kalir.
        #     Her tik (R-R_prev)/dt almak 0,0,0,0,sicrama dizisi uretir; onun
        #     yerine olcumler ARASI gercek sureyi biriktirip bir kez bolelim.
        self._dt_acc += dt
        h = math.radians(yaw_des_deg)
        own_los = own_vel_ms[0] * math.cos(h) + own_vel_ms[1] * math.sin(h)
        if self._R_prev is None:
            self._R_prev = R
            self._dt_acc = 0.0
            if self._v_tgt_los is None:
                self._v_tgt_los = clamp(own_los, 0.0, float(p.V_MAX))
        elif R != self._R_prev and self._dt_acc > 1e-6:
            self._Rdot = (R - self._R_prev) / self._dt_acc
            self._R_prev = R
            # (c) hedefin LOS hizi. Isaret: kapaniyorsak Rdot<0 -> hedef bizden
            #     yavas. Biz 28, Rdot -10 -> hedef 18. Iki terim de GECIKMESIZ;
            #     suzgec yalnizca TOPLAMA uygulanir (bkz. Cfg.V_TGT_TAU).
            raw = own_los + self._Rdot
            b = self._dt_acc / (float(p.V_TGT_TAU) + self._dt_acc)
            self._v_tgt_los += b * (raw - self._v_tgt_los)
            self._v_tgt_los = clamp(self._v_tgt_los, 0.0, float(p.V_MAX))
            self._dt_acc = 0.0

        # (c) sabit-yavaslama yaklasma profili: GORU SINIRINA (TRAIL_RANGE_M)
        #     sifir goreli hizla varacak sekilde kapanma tavani. Uzak menzilde
        #     V_CLOSE_MAX baglar ve toplam zaten V_MAX'e kirpilir ->
        #     UZAK MENZIL DAVRANISI AYNEN KORUNUR.
        gap = max(0.0, self._R_f - float(p.TRAIL_RANGE_M))
        v_close = min(float(p.V_CLOSE_MAX), float(p.K_CLOSE) * gap)
        self._v_cmd = clamp(self._v_tgt_los + v_close,
                            float(p.V_MIN), float(p.V_MAX))
        return self._v_cmd

    # ------------------------------------------------------------------
    #  KUTU SECIMI: taze tespit yoksa KOPRU
    # ------------------------------------------------------------------
    def box(self, det, own_att_deg, t):
        """Guduume verilecek kutuyu dondur (yoksa None).

        det : `aim_box` kapisindan GECMIS taze tespit ya da None.
        own_att_deg : (roll, pitch, yaw) KENDI IMU'muz, derece.

        Taze tespit varsa atalet yonu KAYDEDILIR ve kutu aynen dondurulur.
        Taze tespit yoksa saklanan yon BUGUNKU durusumuzla kadraja geri
        yansitilir (olu-hesap koprusu). GIRDI YALNIZ: son kutu + kendi IMU.
        """
        roll, pitch, yaw = own_att_deg
        if det is not None:
            W = float(det["W"]); H = float(det["H"])
            az, el = pixel_bearing(float(det["cx"]), float(det["cy"]),
                                   pitch, roll, W, H)
            self._bridge = {"az": yaw + az, "el": el,
                            "w": float(det["w"]), "h": float(det["h"]),
                            "conf": float(det.get("conf", 0.0)),
                            "W": W, "H": H, "t": t}
            return det

        k = self._bridge
        if not k or float(self.cfg.BRIDGE_S) <= 0.0:
            return None
        if (t - k["t"]) > float(self.cfg.BRIDGE_S):
            return None  # kopru doldu -> hedef GERCEKTEN kayip
        az = wrap_deg(k["az"] - yaw)
        cx, cy = bearing_pixel(az, k["el"], pitch, roll, k["W"], k["H"])
        if not (0 <= cx < k["W"] and 0 <= cy < k["H"]):
            return None  # kadrajdan cikti
        self._bridge_count += 1
        return {"cx": cx, "cy": cy, "w": k["w"], "h": k["h"],
                "conf": k["conf"], "W": k["W"], "H": k["H"], "t": k["t"],
                "bridge": True}

    # ------------------------------------------------------------------
    #  IBVS YASASI
    # ------------------------------------------------------------------
    def compute(self, det, own_att_deg, own_vel_ms, dt):
        """Bir kontrol tiki -> (thr, pitch, roll, yaw) cubuk konumu.

        det         : {cx, cy, w, h, conf, W, H, t} — HEDEFE AIT TEK VERI
        own_att_deg : (roll, pitch, yaw) KENDI IMU'muz (derece)
        own_vel_ms  : (vx, vy, vz) KENDI hiz vektorumuz (m/s, Unreal)
        dt          : adim suresi (s)

        ⛔ Hedefin konumu/hizi/GNSS'i imzada YOKTUR — yapisal garanti.
        """
        p = self.cfg
        own_roll, own_pitch, own_yaw = own_att_deg
        W = float(det["W"]); H = float(det["H"])
        cx = float(det["cx"]); cy = float(det["cy"])
        sw = _scale(W)         # yatay/boyut piksel olcegi
        sh = float(H) / REF_H  # dikey piksel olcegi

        # --- 1) MENZIL: kutu boyutundan ---
        size = max(float(det["w"]), float(det["h"]))
        R = range_m(size, W)

        # --- 2) KERTERIZ: kadraj konumundan, KENDI durusumuz telafi edilerek ---
        azimuth, elevation = pixel_bearing(cx, cy, own_pitch, own_roll, W, H)

        # --- 3) YAW: burnu hedefe cevir ---
        eps_yaw = 0.0 if abs(azimuth) < float(p.YAW_DEADBAND) else azimuth
        yaw_des = own_yaw + float(p.K_YAW) * eps_yaw
        yaw_rate = clamp(float(p.KP_YAW_RATE) * wrap_deg(yaw_des - own_yaw),
                         -float(p.YAW_RATE_MAX), float(p.YAW_RATE_MAX))

        # --- 4) ILERI HIZ: KAPANMA HIZI DENETIMI ---
        # v_yer = v_hedef_LOS + v_kapanma(R); hedef hizi KUTU BUYUMESINDEN
        # turetilir (GPS YOK). Profil TRAIL_RANGE_M'de sifirlanir -> kuyruga
        # oturulur. Eski "temas kutusuna kadar tam gaz" PI dali KALDIRILDI
        # (2026-08-25; bkz. Cfg icindeki HUCUM YASASI DEVRE DISI notu).
        v = self._closing_speed(R, yaw_des, own_vel_ms, dt,
                                bridge=bool(det.get("bridge")))

        # --- 5) YATAY: hiz nisan (LOS) yonunde ---
        heading = math.radians(yaw_des)
        vx = v * math.cos(heading)
        vy = v * math.sin(heading)

        # --- 6) DIKEY: kadraj regulasyonu ---
        blend_lo = float(p.CY_BLEND_PX_FAR) * sw
        blend_hi = float(p.CY_BLEND_PX_NEAR) * sw
        kg = clamp((size - blend_lo) / max(1e-6, blend_hi - blend_lo), 0.0, 1.0)
        cy_ref = (float(p.CY_REF_FAR)
                  + kg * (float(p.CY_REF_NEAR) - float(p.CY_REF_FAR))) * sh
        e_cy = cy - cy_ref  # + = hedef kadrajda ASAGIDA
        vz_raw = -(float(p.K_CY) / sh) * e_cy
        vz_up = clamp(vz_raw, -float(p.VZ_CAP_VISUAL),
                      float(p.VZ_CAP_VISUAL))
        clipped = int(vz_raw != vz_up)
        vz_up = clamp(vz_up, -float(p.VZ_MAX_DESCENT),
                      float(p.VZ_MAX_CLIMB))

        # --- 7) HIZ -> CUBUK (olculmus model) ---
        thr, pitch, roll, yaw = self.conv.convert(
            (vx, vy, -vz_up), own_vel_ms, math.radians(own_yaw), yaw_rate)

        self._tlm = {
            "range_m": round(R, 2) if R else -1.0,
            "size_px": round(size, 1),
            "azimuth": round(azimuth, 2), "elevation": round(elevation, 2),
            "v_fwd": round(v, 2),
            # mekanizma sutunu: bu ucu sifirsa kapanma denetimi calismiyordur
            "r_dot": round(self._Rdot, 2),
            "v_tgt_los": (round(self._v_tgt_los, 2)
                          if self._v_tgt_los is not None else None),
            "v_close": (round(v - self._v_tgt_los, 2)
                        if self._v_tgt_los is not None else None),
            "cy_ref": round(cy_ref, 1), "e_cy": round(e_cy, 1),
            "nearness": round(kg, 3),
            "vz_up": round(vz_up, 2), "vz_clipped": clipped,
            "yaw_rate": round(yaw_rate, 1),
            "bridge": int(bool(det.get("bridge"))), "bridge_frames": self._bridge_count,
            "thr": round(thr, 3), "pitch": round(pitch, 3),
            "roll": round(roll, 3), "yaw": round(yaw, 3),
        }
        self._tlm.update(self.conv.diag)
        return float(thr), float(pitch), float(roll), float(yaw)

    def status(self):
        """Son tikin ic degerleri (konsol/tani icin; guduume GIRMEZ)."""
        return dict(self._tlm)

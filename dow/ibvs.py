# -*- coding: utf-8 -*-
"""
================================================================================
GÖRSEL GÜDÜM (IBVS) — Gazebo yasası, DoW sabitleriyle
================================================================================
YAPI AYNEN TAŞINDI (Seçenek A): saf takip + kutu boyutundan PI hız yasası.
DEĞİŞEN yalnız SABİTLER; hepsi DoW'da ÖLÇÜLDÜ.

TERİMLER (CLAUDE.md §0.2 — hiçbiri tanımsız bırakılmaz)
  * IBVS (görüntü-tabanlı görsel servolama): kontrol hatası doğrudan
    GÖRÜNTÜ UZAYINDA tanımlanır (piksel), 3B konum kestirmeye gerek yok.
  * saf takip (pure pursuit): hız vektörünü her an hedefe DOĞRU çevir.
    Basit ve dayanıklı; kusuru, kaçan hedefte "kuyruktan" takip etmesi.
  * LOS (görüş hattı): araçtan hedefe giden doğru.
  * kapanma hızı: menzilin azalma hızı (−dR/dt).
  * lead (öngörü): nişanı hedefin gideceği yöne ÖNE almak.
  * PI: Oransal + İntegral kontrolcü. P anlık hatayla, I birikmiş hatayla
    orantılı çıktı üretir; I kalıcı hatayı (sabit fark) kapatır.

YARIŞMA KURALI (CLAUDE.md §10) — YAPISAL GARANTİ
  Bu modülün girdileri: bbox pikselleri + KENDİ IMU'muz (roll/pitch/yaw).
  Hedefin GPS'i FONKSİYON İMZASINDA YOK -> görsel fazda kural ihlali
  yapısal olarak İMKÂNSIZ (Gazebo'daki B5 bekçisinin emsali).

DoW'DA ÖLÇÜLEN SABİTLER (Gazebo değeri -> DoW değeri, neden)
  MENZIL_C   296.8 px·m @640  ->  997 px·m @1920
      Gazebo hedefi 1.28 m kanatlıydı, DoW Talon'u 1.718 m. 1920'ye
      ölçeklenmiş Gazebo sabiti 557 olurdu -> 1.79 KAT yanlış.
  V_HUCUM    18.0 m/s -> 28.0 m/s
      DoW Talon'u 17.98 m/s uçuyor. 18 ile kapanma 0.02 m/s = ASLA
      yakalayamayız. Araç 34.6 m/s yapabiliyor; 28 -> kapanma ~10 m/s.
      (Tavanın tamamı kullanılmadı: toplam hız bütçesi dikeyle paylaşılıyor.)
  kamera     FX=166.6/CX=320 @640 -> f=540.4/CX=960 @1920, TILT 26.5°
      Ölçüldü, artık 2.6 px. Ayrıntı: dow/gorus/kamera.py
  VZ tavanı  ±15 simetrik -> +33.5 / -6.95 ASİMETRİK
      Ölçüldü. Simetrik varsaymak alçalma komutunu ~5 kat abartır.

⭐ YAPISAL UYUM: aracın dikey asimetrisi (güçlü tırmanma, zayıf alçalma)
   güdümün ihtiyacıyla ÖRTÜŞÜYOR. Kamera 26.5° YUKARI baktığı için hedefi
   kadrajda tutmak aracı hedefin ALTINDA tutar; oradan hedefe gitmek
   TIRMANMAKTIR — bol yetkimiz olan yön. Gazebo'daki "alttan vuruş"
   tasarımı DoW aracına tesadüfen değil, doğal olarak oturuyor.
================================================================================
⛔⛔ 2026-08-22 — ÜÇ EKLEMEM GERİ ALINDI. DÜRÜST KAYIT:

Görsel fazda hedefi vuramayınca üst üste "iyileştirme" ekledim ve HER BİRİ
işi KÖTÜLEŞTİRDİ. Ölçülen en yakın menzil medyanı:

  GV02  dikey kadraj regülasyonu (yalnız)   12.05 m   ISABET 1/4  <- EN İYİ
  GV03  + lead                              13.75 m   isabet 0/3
  GV04  + merkez freni                      13.00 m   isabet 0/3
  GV06  + sakin kamera                      16.08 m   isabet 0/3
  GV07  + tam yaw bandı + lead 0.5         ~19    m   isabet 0/2

HATAM: her kararı n=3 koşuyla verdim. CLAUDE.md §5.4 tam bunu yasaklıyor
("n<4 iken hüküm cümlesi kurulmaz") ve üç kez yaşandığı yazılı. Sakin
kameranın tespit kazancı (+5.7 puan) gerçek olabilir ama İSABETE
dönüşmedi; kalan ikisi için elimde kazanç gösteren hiçbir veri yok.

GERİ DÖNÜŞ: GV02 yapılandırması (yalnız dikey kadraj regülasyonu) TABAN
kabul edilir; n>=6 ile doğrulanır; sonra her ekleme AYRI ve DÖNÜŞÜMLÜ
A/B ile, n>=4/kol sınanır. Kod duruyor, anahtarlar KAPALI.
================================================================================
"""
import math
import os

from dow.gorus import kamera as KAM


def _fi(ad, v):   # env ile geçersiz kılınabilir (kampanya kill-switch'i)
    return float(os.environ.get(ad, v))


def _b_i(ad, v):
    return os.environ.get(ad, str(int(v))).strip() not in ("0", "", "false", "False")


def _kirp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x


class IbvsCfg:
    # --- hız yasası ---
    V_HUCUM       = 28.0    # m/s; hücum hızı tavanı (hedef 17.98 -> kapanma ~10)
    V_MIN         = 0.0     # m/s; asla geri gitme
    HUCUM_MENZIL_M= 1.0     # m; PI'nın sıfır noktası = TEMAS menzili.
                            # "Şu menzilde dur" noktası YOK -> hata hep pozitif
                            # kalır, hız tavanda oturur, sabit kapanma.
    K_FWD         = 0.35    # (m/s)/px; P kazancı  (Gazebo'dan AYNEN)
    K_I           = 0.04    # (m/s)/(px·s); I kazancı (Gazebo'dan AYNEN)
    I_MAX         = 8.0     # m/s; integral doyumu (windup önleyici)

    # --- yaw ---
    K_YAW         = 1.0     # tam düzeltme (Gazebo'dan AYNEN)
    YAW_RATE_MAX  = 120.0   # °/s. Araç 214 yapabiliyor AMA hızlı yaw
                            # görüntüyü bulandırıp dedektörü kırar -> KORUNDU.
    YAW_OLU_BAND  = 1.0     # °; altında yaw komutu güncellenmez

    #   ⭐ 4.0'a YÜKSELTİLDİ — ama YALNIZ K_CY 0.014'e düşürüldüğü için.
    #     Tek başına 4.0 (K_CY 0.06 ile) B8'de KAYBETMİŞTİ; ikisi birlikte
    #     kanalı oransal yapıyor. Bkz. K_CY notu.
    VZ_TAVAN_GORSEL = _fi("DOW_VZ_TAVAN_GORSEL", 4.0)   # m/s

    # --- DİKEY: KADRAJ REGÜLASYONU ("alttan vuruş") ---
    # ⛔ ÖNCEKİ YASA ÇÖKTÜ (GV01, 3 koşu, ölçüldü):
    #   Hız vektörü doğrudan hedefe nişanlanıyordu (saf takip). Bu, hedefin
    #   İRTİFASINA TIRMANMAK demek: 24° yükselişte 28·sin(24°)=11.4 m/s
    #   tırmanma komutu. 6.8 m'lik farkı 0.6 s'de kapatıp hedefin hizasına
    #   çıkıyor; kamera 26.5° YUKARI baktığı için oradan hedef GÖRÜNMÜYOR.
    #   Sonuç: görsel fazda tespit %90 -> %12-15, isabet 0/3.
    #
    # YENİ YASA: hedefi KADRAJDA sabit bir yükseklikte tut (cy -> cy_ref).
    #   Kamera gövdeye sabit ve TILT° yukarı baktığı için "hedefi kadrajın
    #   şurasında tut" demek, "hedefin ALTINDA şu açıyla kal" demektir —
    #   geometri kendiliğinden çıkar, ayrıca hesaplamaya gerek yok.
    #   GİRDİ YALNIZ PİKSEL: menzil/irtifa/GPS KULLANILMAZ.
    #
    #   cy > cy_ref  -> hedef kadrajda AŞAĞIDA -> biz YÜKSEKTEYİZ -> ALÇAL
    #   cy < cy_ref  -> hedef kadrajda YUKARIDA -> biz ALÇAKTAYIZ -> TIRMAN
    # ⭐⭐ YENİDEN AYARLANDI 2026-08-23 (E1+E1b, havuzlanmış n=8/kol)
    #   ⛔ TEŞHİS: K_CY=0.06 + tavan 1.5 ile |e_cy|>25 px olan HER kare
    #     doyuma giriyordu. ÖLÇÜLDÜ: taze kutuda bile karelerin %98.3'ü
    #     doyumda, |e_cy| medyan 143 px. Yani dikey kanal oransal kontrolcü
    #     DEĞİL, AÇ-KAPA anahtarıydı: hedef 30 px de üstte olsa 300 px de
    #     olsa komut aynı (throttle tam tıpatıp 0.019 ölçüldü).
    #     Geometri de tutmuyordu: 24.8° yükseliş + 3.62 m/s kapanma ->
    #     gereken dikey 1.67 m/s, tavan 1.50 m/s.
    #   ⚠ Önceki tavan taramalarım (2/4/8) YANILTICIYDI: hepsinde K_CY 0.06
    #     sabitti, yani hepsi aç-kapaydı; büyük tavan sadece daha büyük
    #     darbe verip salınım üretti. KAZANÇ ve TAVAN hiç BİRLİKTE
    #     değiştirilmemişti — eksik olan deney buydu.
    #      ölçüt              0.06/1.5   0.014/4.0
    #      TEMAS                6/8        8/8
    #      en_yakin medyan     0.86 m     0.51 m   (-%41)
    #      tespit%             59.00      70.80
    #      cx dönüş/s           0.30       0.10   (3 kat sakin)
    #      roll p90             3.75°      3.25°
    #      görsel kesinti      10.20 s     2.05 s (5 kat az)
    #      DOYUM oranı         %97.0      %17.7   <- mekanizma kanıtı
    #   Doğrusal kaldığı aralık: 4.0/0.014 = ±286 px (eskiden ±25 px).
    K_CY          = _fi("DOW_K_CY", 0.014)  # (m/s)/px
    CY_REF_UZAK   = 470.0   # px; UZAKTA hedefi merkezin ÜSTÜNDE tut (altta kal)
    CY_REF_YAKIN  = 540.0   # px; YAKINDA merkeze getir (nişan al, vur)
    # Geçiş kutu boyutuyla: kutu bu değerden büyükse "yakın" sayılır.
    CY_GECIS_PX_UZAK = 40.0   # px (≈25 m)
    CY_GECIS_PX_YAKIN= 90.0   # px (≈11 m)
    VZ_MAX_TIRMAN = 33.5    # m/s; ÖLÇÜLDÜ
    VZ_MAX_ALCAL  = 6.95    # m/s; ÖLÇÜLDÜ (⚠ 4.8 kat asimetrik; hover'da.
                            #   İleri uçuşta 15.6'ya çıkıyor ama tabanı alıyoruz)

    # T6 · DİKEY YUMUŞATMA — |throttle| tespiti en çok bozan büyüklüktü
    #   (2.2 kat). VZ_TAVAN_GORSEL zaten var ama YALNIZ SAKIN_KAMERA
    #   açıkken uygulanıyordu; bu anahtar onu bağımsız kılar.
    # ⭐⭐ GİRDİ 2026-08-23 gecesi — GECENİN EN BÜYÜK KAZANIMI.
    #   B7, n=4/kol, dönüşümlü A/B:
    #      ölçüt          KAPALI     AÇIK
    #      isabet          3/4        4/4
    #      en_yakin       3.00 m     0.72 m
    #      koşular   2.16·1.55·3.84·5.14   0.69·0.82·0.56·0.76
    #      tespit%        20.70      50.90   (2.5 KAT)
    #      doğru%         89.20      95.05
    #      yanlış%        10.80       4.95
    #      görsel faz     27.15 s    38.40 s
    #      roll p90       12.60°      5.55°
    #   ARALIKLAR HİÇ ÖRTÜŞMÜYOR: kontrol [1.55-5.14], deney [0.56-0.82].
    #   İlan edilen birincil ölçüt (tespit%) +30 PUAN; her geçerlilik eşi
    #   de aynı yönde -> kazanç junk kutudan gelmiyor.
    #   MEKANİZMA: kamera GÖVDEYE SABİT. Dikey komut throttle'ı sıçratıyor,
    #   araç dikeyde savruluyor ve 70 px'lik hedef bulanıklaşıyor. İlk
    #   oturumda ölçülmüştü: |throttle| 0.300 (tespit VAR) / 0.669 (YOK) —
    #   2.2 kat, ölçülen EN BÜYÜK ayırıcı. Tavan tam o büyüklüğü kısıyor.
    VZ_TAVAN_AKTIF = _b_i("DOW_VZ_TAVAN", True)

    # ⛔ D1 TERMİNAL DİKEY SERBESTLİĞİ ELENDİ ve SİLİNDİ (2026-08-23)
    #   Hipotez: dikey tavan (1.5 m/s) son metrelerde düzeltmeyi kısıtlıyor.
    #   ÖLÇÜLDÜ (n=4/kol, dönüşümlü) — HİPOTEZ ÇÜRÜDÜ, aralıklar AYRIK:
    #       ölçüt        kapalı                 açık (menzil<5 m'de serbest)
    #       TEMAS         4/4                    0/4
    #       en_yakin   0.78 m (0.89·0.80·        1.61 m (1.70·1.85·
    #                          0.76·0.70)                1.53·1.17)
    #   Mekanizma kapısı geçmişti (terminal kare 13-20 vs 0), yani özellik
    #   çalıştı ve İŞİ KÖTÜLEŞTİRDİ. Dikey tavan terminali KISITLAMIYOR,
    #   KORUYOR: kalkınca araç son metrelerde savruluyor.
    # T5 · BBOX KÖPRÜSÜ (ölü-hesap) — ⭐ GİRDİ (B2, n=4/kol)
    #   Çıkarım 10 Hz; aradaki ~100 ms'de ve tespit boşluklarında güdüm
    #   BAYAT kutuyla çalışıyor. Kutunun ATALET yönünü saklayıp KENDİ
    #   dönüşümüzü telafi ederek kutuyu kadrajda ileri taşırız.
    #   ⭐ GİRDİ YALNIZ: son kutu + KENDİ IMU'muz. GPS YOK, menzil YOK.
    #      ölçüt            KOPRU=0    KOPRU=0.5
    #      isabet             1/4        4/4
    #      en_yakin medyan   5.44 m     1.94 m   (-64%)
    #      roll p90          48.65°     27.05°   (-44%)
    #   Süre TARANDI (B5, n=4/kol): 0.3 -> 3.35 m, 0.5 -> 1.90 m,
    #   1.0 -> 1.34 m (kazanan). 2.0 ek kazanç vermedi (B6).
    KOPRU_S       = _fi("DOW_KOPRU_S", 1.0)

    # B · BAYAT KUTUYU BIRAK — BERABERE, KAPALI (C1, n=4/kol)
    #   Köprü KOPRU_S dolunca güdüm sessizce ESKİ HAM KUTUYA düşüyordu;
    #   kaybı ancak 20 çıkarım (=2 s) sonra kabul ediyordu. ÖLÇÜLDÜ:
    #   kutu yaşı medyan 80 ms, p90 1546 ms, max 2187 ms — karelerin %30'u
    #   0.5 s'den ESKİ kutuyla uçuyor. Mekanizma kapısı GEÇTİ (bayat_birak
    #   sayacı deney kolunda 46-497, kontrolde 0).
    #      ölçüt            kapalı   açık
    #      TEMAS             3/4      3/4
    #      en_yakin medyan  0.92 m   0.75 m  (-%18; ilan edilen eşik %20)
    #   Aralıklar örtüşüyor -> GİRMEDİ. ⚠ Karşılaştırmanın tamamı hedef DÜZ
    #   uçarken yapıldı; hayalete uçmanın bedeli manevrada çıkabilir.
    #   Anahtar KAPALI, gerekçesi yazılı, manevra açılınca yeniden sınanacak.
    BAYAT_BIRAK   = _b_i("DOW_BAYAT_BIRAK", False)

    # ⛔ D2 TAM KERTERİZ — GÜDÜM ÇEVRİMİNDE ELENDİ, ÖLÇÜMDE GİRDİ (2026-08-23)
    #
    #   `piksel_kerteriz` roll döndürmesini TILT eklendikten SONRA uyguluyor;
    #   yükseliş bileşeni 26.5° olduğu için küçük yatış bile azimuta
    #   26.5·sin(roll) sızdırır. Hata ≈ roll'un kendisi kadar
    #   (3°->3.3°, 10°->11.0°, 35°->39.8°).
    #   Gazebo'nun `los_seviye`si dönüşü 3B ışın üzerinde doğru sırayla
    #   yapıyor; AYNEN taşındı + tersi yazıldı (gidiş-dönüş 700/700 tam).
    #
    #   ⭐ HANGİSİ DOĞRU: 4146 eşleşmiş karede tespit edilen kutuya uyum
    #      yaklaşık 33.1 px / TAM 13.6 px medyan sapma -> TAM zincir DOĞRU.
    #      Bu yüzden ÖLÇÜM YOLU tam zincire geçirildi (kosu.py, tespit_olcu).
    #
    #   ⛔ AMA GÜDÜM ÇEVRİMİNDE ELENDİ (havuzlanmış n=8/kol):
    #        temas 6/8 -> 4/8,  cx dönüş/s 0.34 -> 1.30 (4 kat salınım)
    #      SEBEP: tam zincirde araç 35° yatıkken KADRAJ MERKEZİNDEKİ hedefin
    #      azimutu +21° çıkar (doğrudur). Güdüm bunu `yaw + 3.0·azimut` ile
    #      hız yönüne çeviriyor -> yatış > büyük yaw > daha çok yatış.
    #      Kazançlar YANLIŞ modele göre ayarlanmış.
    #   ⛔ Yalnız köprüde denendi (D2c): temas 3/4 vs 3/4, BERABERE.
    #      D2'deki "+11 puan tespit" büyük ölçüde kısa/yakın karşılaşmanın
    #      yan etkisiymiş (§5.2 tuzağı).
    #
    #   ⚠⚠ BİLİNEN BORÇ: güdüm hâlâ MATEMATİKSEL OLARAK YANLIŞ kerterizi
    #      kullanıyor. Şu an zararsız çünkü roll p90 3-8°'ye indi (gece
    #      başında 42-51°'ydi). Yatış tekrar büyürse hata sessizce geri
    #      gelir. Doğru çözüm: tam zincire geçip K_YAW'ı yeniden ayarlamak.
    #      Bekçi B29 bu borcu görünür tutuyor.
    # D3 · DİKEY YASA — Gazebo'nun 3B saf takibi vs kadraj regülasyonu
    #   Kullanıcı: "gazebodaki görsel güdüm algoritmasının aynısını entegre
    #   etsek olmaz mı." Yatay kanal ZATEN aynı; kalan tek büyük fark bu.
    #
    #   "kadraj"   (mevcut): vz = -K_CY·(cy - cy_ref)
    #        Hedefi kadrajda sabit yükseklikte tut. GV01'de saf takip
    #        dikeyde "hedefin irtifasına tırmanıp kaybetme" yapınca buna
    #        geçmiştim — AMA O KARARI n=3 İLE VERMİŞTİM (§5.4 ihlali).
    #   "saftakip" (Gazebo): nisan_elev = K_ELEV·elev_los;
    #        vz = -v·sin(nisan_elev), yani hız vektörü 3B'de hedefe nişanlanır
    #        (yatayla AYNI matematik). Artı:
    #          - türev sönümlemesi K_VZ_D (kendi dikey hızımız nişanı aşarsa
    #            komut geri çekilir -> hedefin üstünden geçme biter)
    #          - |v| KORUNUMU: dikey ne alırsa yatay kısılır
    #        elev_los TAM zincirden gelir (los_seviye) — D2'de ölçüldü,
    #        4146 karede 2.4 kat daha uyumlu.
    #   ⚠ Gazebo'nun YAVASLA / lead / DIKEY_KAPANMA özellikleri DAHİL DEĞİL
    #     (ayrı deney). Dikey tavan HER İKİ KOLDA da uygulanır.
    DIKEY_YASA    = os.environ.get("DOW_DIKEY_YASA", "kadraj").strip()
    K_ELEV        = _fi("DOW_K_ELEV", 1.0)      # Gazebo değeri
    K_VZ_D        = _fi("DOW_K_VZ_D", 0.6)      # Gazebo değeri

    # T4 · YERELLİK KAPISI — düşük eşik + "hedef nerede olmalı" kısıtı.
    #   Görsel fazda hedefin kadrajda NEREDE olduğunu bir önceki kutumuzdan
    #   (ve T5 köprüsünden) biliyoruz. O yüzden dedektör eşiğini düşürüp
    #   (0.40 -> YEREL_CONF_MIN) adayları YERELLİKLE eleyebiliriz:
    #     - merkez, beklenen yerin YEREL_KAPI_PX + 2*son_kutu içinde
    #     - genişlik, son genişliğin 0.5-2.0 katı
    #   Kazanç: 0.40 eşiğinin ALTINDA kalan soluk tespitler kurtarılır
    #   (ölçüldü: eşik 0.10'da tespit %49 / 0.40'ta %40 — 9 puan orada).
    #   Yanlış-pozitif riski: argmax'ı OSD çalıyordu; yerellik bunu keser.
    #   ⭐ TAMAMEN KAMERA İÇİ — GPS yok (§10).  0 = kapalı.
    # ⭐ GİRDİ 2026-08-23 gecesi — B3b+B3c havuzlanmış, n=5/kol, dönüşümlü:
    #      ölçüt          YEREL=0    YEREL=60
    #      isabet          4/5        5/5
    #      en_yakin       1.84 m     1.87 m   (berabere)
    #      tespit%        28.00      25.00    (aralıklar İÇ İÇE: 20-43 vs
    #                                          23-31 -> AYIRT EDİLEMİYOR)
    #      doğru%         74.50      79.70
    #      yanlış%        25.50      20.30
    #      kadraj%        96.40     100.00
    #      roll p90       31.60°      8.30°   (-74%; 5 koşunun 4'ü ≤9.3)
    #   İlan edilen birincil ölçüt (tespit%) FARK GÖSTERMEDİ; zaten kapı
    #   açıkken "tespit" tanımı değişiyor (dedektör buldu VE yerellikten
    #   geçti), yani kollar arası aynı şeyi ölçmüyor. Ölçüt sonradan
    #   değiştirilmedi (§5.6) — ayırt edemediği söylendi. Kalan HER ölçüt
    #   tek yönde. CLAUDE.md §4: salınan araç, aynı sonucu üretse bile kötüdür.
    #   ⚠ İlk uygulamam ELENMİŞTİ (B3: isabet 1/4, görsel faz 4.85 s):
    #     kapı bir kez kaybedince kilitleniyordu. YEREL_KURTAR ve "en yüksek
    #     güvenli" seçim kuralı bunu çözdü.
    YEREL_KAPI_PX = _fi("DOW_YEREL_KAPI", 60.0)
    YEREL_CONF_MIN = _fi("DOW_YEREL_CONF", 0.20)
    # ⛔ KİLİTLENME ÇARESİ (B3'te ölçüldü): referans bayatlayınca hiçbir aday
    #   kapıdan geçmiyor, kapı asla yeniden yakalayamıyor ve görsel faz
    #   ~5 s'de düşüyordu (tespit %33 -> %15-18, isabet 2/2 -> 0/4).
    #   Bu kadar ardışık başarısızlıktan sonra kapı AÇILIR ve düz argmax'a
    #   dönülür; ilk yeni tespit referansı tazeler.
    YEREL_KURTAR  = 5

    # --- geçerlilik ---
    CONF_MIN      = 0.40    # ÖLÇÜLDÜ (dow/gorus/dedektor.py)
    BOYUT_MIN_PX  = 8.0     # px; bundan küçük kutu güvenilmez
    MENZIL_MAX_M  = 50.0    # m; ötesinde görsel devir YOK (tespit %10)
    MENZIL_MIN_M  = 3.0     # m; ALTINDAKİ kutu = dev yanlış-pozitif.
                            # 997/3 = 332 px'lik kutu demek; hedef bu boyuta
                            # ancak TEMAS anında ulaşır. Dedektör 140 m'de
                            # bu boyutta kutular üretiyordu (ölçüldü).


def komut(cx, cy, w, h, own_yaw_deg, own_pitch_deg, own_roll_deg,
          hiz_I, dt, cfg=IbvsCfg, own_vz=0.0):
    """IBVS kontrol yasası.

    GİRDİ (hedefin GPS'i YOK — yapısal garanti):
      cx, cy, w, h  : tespit kutusu (piksel) — TEK canlı hedef kaynağı
      own_*         : KENDİ yönelimimiz (derece) — kendi IMU'muz
      hiz_I         : hız integralinin o anki değeri (m/s); çağıran taşır
      dt            : adım süresi (s)
      own_vz        : KENDİ dikey hızımız (m/s, yukarı+) — D3 türev
                      sönümlemesi için; kendi sensörümüz (§10 temiz)

    ÇIKTI: (v_ned, vz, yaw_hedef_deg, hiz_I_yeni, tani)
      v_ned = (vx, vy) m/s DÜNYA yatay düzleminde (NED: x kuzey, y doğu)
      vz    = m/s, NED (POZİTİF = AŞAĞI; çevirici ters çevirir)
    """
    tani = {}

    # --- 1) MENZİL: kutu boyutundan (benzer üçgenler, p = C/R) ---
    boyut = max(w, h)                      # köşegen yerine en büyük eksen
    R = KAM.menzil(boyut) if boyut > 0 else None
    tani["ibvs_boyut_px"] = boyut
    tani["ibvs_menzil_m"] = R if R else -1

    # --- 2) KERTERİZ: kadraj konumundan, KENDİ duruşumuz telafi edilerek ---
    azimut, yukselis = KAM.piksel_kerteriz(cx, cy, own_pitch_deg, own_roll_deg)
    tani["ibvs_azimut"] = azimut
    tani["ibvs_yukselis"] = yukselis

    # --- 4) YAW: burnu hedefe çevir (+ lead) ---
    eps_yaw = azimut
    if abs(eps_yaw) < cfg.YAW_OLU_BAND:
        eps_yaw = 0.0
    yaw_hedef = own_yaw_deg + cfg.K_YAW * eps_yaw
    tani["ibvs_eps_yaw"] = eps_yaw

    # --- 4b) İSTENEN KADRAJ YERİ (dikey nişan) — fren de bunu kullanır ---
    kg = _kirp((boyut - cfg.CY_GECIS_PX_UZAK) /
               max(1e-6, cfg.CY_GECIS_PX_YAKIN - cfg.CY_GECIS_PX_UZAK), 0.0, 1.0)
    cy_ref = cfg.CY_REF_UZAK + kg * (cfg.CY_REF_YAKIN - cfg.CY_REF_UZAK)

    # --- 5) HIZ: kutu boyutu hatası üzerinden PI ---
    # Denge kutusu = TEMAS kutusu -> hata hep pozitif, hız tavanda oturur.
    hedef_boyut = KAM.MENZIL_C / cfg.HUCUM_MENZIL_M
    hata_px = hedef_boyut - boyut
    hiz_I = _kirp(hiz_I + cfg.K_I * hata_px * dt, -cfg.I_MAX, cfg.I_MAX)
    v_istek = cfg.K_FWD * hata_px + hiz_I
    v = _kirp(v_istek, cfg.V_MIN, cfg.V_HUCUM)

    tani["ibvs_hata_px"] = hata_px
    tani["ibvs_v"] = v

    # --- 6) YATAY: hız LOS (nişan) yönünde ---
    yon = math.radians(yaw_hedef)
    vx = v * math.cos(yon)
    vy = v * math.sin(yon)

    # --- 7) DİKEY ---
    e_cy = cy - cy_ref                      # + = hedef kadrajda AŞAĞIDA
    if cfg.DIKEY_YASA == "saftakip":
        # D3 · GAZEBO: hız vektörünü 3B'de hedefe nişanla (yatayla aynı
        # matematik). elev_los TAM zincirden; nişan ofseti YOK.
        _, _elev = KAM.los_seviye(cx, cy, own_roll_deg, own_pitch_deg)
        nisan_elev = _kirp(cfg.K_ELEV * _elev, -60.0, 60.0)
        _vz_nisan = v * math.sin(math.radians(nisan_elev))     # yukarı+
        # TÜREV SÖNÜMLEMESİ: kendi dikey hızımız nişanı aştıysa geri çek
        vz_yukari = _vz_nisan + cfg.K_VZ_D * (_vz_nisan - own_vz)
        tani["ibvs_nisan_elev"] = nisan_elev
    else:
        # KADRAJ REGÜLASYONU (mevcut): hedefi kadrajda sabit yükseklikte tut
        vz_yukari = -cfg.K_CY * e_cy        # aşağıdaysa ALÇAL
    _v0 = vz_yukari
    if cfg.VZ_TAVAN_AKTIF:                              # T6
        vz_yukari = _kirp(vz_yukari, -cfg.VZ_TAVAN_GORSEL, cfg.VZ_TAVAN_GORSEL)
    # §5.1 MEKANİZMA SÜTUNU: dikey kanal DOYUMDA mı? Ölçüldü 2026-08-23:
    #   taze kutuda bile karelerin %98.3'ü doyumda -> kontrolcü oransal
    #   DEĞİL, aç-kapa. Bu sütun kazanç/tavan çiftinin işe yarayıp
    #   yaramadığını doğrudan gösterir.
    tani["ibvs_vz_kirpildi"] = int(_v0 != vz_yukari)
    vz_yukari = _kirp(vz_yukari, -cfg.VZ_MAX_ALCAL, cfg.VZ_MAX_TIRMAN)
    if cfg.DIKEY_YASA == "saftakip":
        # |v| KORUNUMU: dikey ne aldıysa gerisi yataya (Gazebo).
        _yat = math.sqrt(max(v * v - vz_yukari * vz_yukari, 0.0))
        vx = _yat * math.cos(yon); vy = _yat * math.sin(yon)
    vz_ned = -vz_yukari            # NED: pozitif = AŞAĞI
    tani["ibvs_vz_yukari"] = vz_yukari
    tani["ibvs_cy_ref"] = cy_ref
    tani["ibvs_e_cy"] = e_cy
    tani["ibvs_yakinlik"] = kg

    return (vx, vy), vz_ned, yaw_hedef, hiz_I, tani


def gecerli(cx, cy, w, h, conf, cfg=IbvsCfg):
    """Bu tespit güdüme girebilir mi? (§5.1 mekanizma kapısı için ayrı tutuldu)"""
    if conf < cfg.CONF_MIN: return False, "conf"
    boyut = max(w, h)
    if boyut < cfg.BOYUT_MIN_PX: return False, "boyut"
    R = KAM.menzil(boyut)
    if R is None or R > cfg.MENZIL_MAX_M: return False, "menzil_uzak"
    if R < cfg.MENZIL_MIN_M: return False, "menzil_yakin"   # dev yanlış-pozitif
    if not (0 <= cx < KAM.IMG_W and 0 <= cy < KAM.IMG_H): return False, "kadraj"
    return True, ""

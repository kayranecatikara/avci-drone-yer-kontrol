"""
supervisor.py — Faz 4: GPS ↔ görsel güdüm geçişi (hibrit müdahale).

run_hybrid tek görev döngüsüdür (start_chase bunu çalıştırır):

  GPS fazı (gps_guidance) hedefe yaklaşır. Görsel temas oturunca
  (KILIT_N ardışık pose karesi, conf ≥ POSE_CONF_MIN, VE handoff menzili
  içindeyiz YA DA GPS düşmüş/DROPOUT) → GÖRSEL faza (visual_lead) geçilir.
  Görsel temas kesilirse (KAYIP_M ardışık pose'suz kare veya kare akışının
  durması) → GPS fazına dönülür. stop_chase gelene (veya araç vurulana)
  kadar bu döngü sürer.

Menzil kapısının (GATE_KILIT) nedeni: görsel fazın kapanma hızı sabit
(V_KAPANMA); uzaktan erken geçilirse hızlı hedefe yetişilemez. GPS handoff
histerezisi (≤40 m) zaten "yetişilmiş" durumu işaretler. GPS jam/DROPOUT'ta
menzil bilinemez → görsel temas tek başına yeter (jamming fallback).
"""

import collections
import os
import threading
import time                      # GORSEL modunda kilit SURESI icin (2026-08-14)

from control.guidance import gps_guidance as _ga
from control.guidance.gps_guidance import run_gps_guidance
from control.guidance.guidance_core import Cfg as LeadCfg
# visual_lead = ESKI alternatif gorsel yasa (arsiv, kural disi FF icerir).
# Yeni yasaya gecince eski_gudum yedegine tasindi; yalniz AVCI_VISUAL=lead
# secilirse gerekir. Yoksa import HATASI verip tum gorevi dusurmesin.
try:
    from control.guidance.visual_lead import run_visual_lead
except ImportError:
    run_visual_lead = None
from control.guidance.bbox_ibvs import run_bbox_ibvs, Cfg as IbvsCfg
# GERCEK "5 s KESINTISIZ kilit" kapisi + denetim kaydi (2026-08-17).
# Varsayilan AVCI_KILIT_S=0 -> kapi KAPALI, bu modul davranisi DEGISTIRMEZ;
# yalnizca kilit_denetim_*.csv yazar. Bkz. kesintisiz_kilit.py basligi.
from control.guidance.kesintisiz_kilit import (
    KesintisizKilit, KilitKapiCfg, denetim as kilit_denetim)

# ══ YENI GUDUM YASALARI (2026-08-24, kullanici istegi) ═══════════════════
#   GPS    : dow/gps.py    - istasyon tutma + ileri besleme
#   GORSEL : dow/ibvs.py   - saf takip + kutu boyutundan PI + kadraj regulasyonu
#   Dongu  : dow/amir.py   - yasalari araca baglayan katman (eski
#            run_gps_guidance / run_bbox_ibvs ile AYNI sozlesme).
# Eski yasalara donmek icin: AVCI_YASA=eski
_YASA = os.environ.get("AVCI_YASA", "dow").strip().lower()
_dow_amir = None
_DowAyar = None
if _YASA == "dow":
    import sys as _sys
    _DEPO = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                         "..", "..", "..", ".."))
    if _DEPO not in _sys.path:
        _sys.path.insert(0, _DEPO)
    from dow import amir as _dow_amir
    from dow.ayarlar import Ayar as _DowAyar
    # TELEMETRI KOPRUSU: arayuz/izci menzili `gps_guidance.status["d_h"]`
    # uzerinden okuyor. Eski yasa artik HIC kosmadigi icin o sozluk bayat
    # kalirdi (menzil alani bos gorunur). Amir'in status'unu AYNI sozluge
    # baglayarak arayuz degismeden calismaya devam eder.
    _dow_amir.status = _ga.status

# GÖRSEL FAZ SEÇİMİ (2026-08-08, D0 yarışma kuralı):
#   bbox : SAF bbox IBVS — GPS'siz, kural uyumlu (VARSAYILAN)
#   lead : eski visual_lead (pose/truth-menzil zamanı; ARŞİV, kural dışı FF içerir)
_GORSEL_YASA = os.environ.get("AVCI_VISUAL", "bbox").strip().lower()


class SupCfg:
    # ── DEVİR KAPISI: ARDIŞIK → KAYAN PENCERE (2026-07-31) ──
    # Eskiden KILIT_N ARDIŞIK güvenli kare aranıyordu. Tespit gürültülü olduğu
    # için (gerçek uçuşlarda karelerin yalnız %12'si temiz `ok`) bu şart çok geç
    # sağlanıyordu: devir kapısı 20 m'ye ayarlı olmasına rağmen görsel faz
    # 6-10 m'de başlıyordu ve elinde 0.6-1.9 s kalıyordu — hedefin 4.65 m altında
    # devralınan dikey farkı kapatmaya yetmiyor.
    # Kayan pencere aynı güveni verir ama tek bir kötü kare sayacı sıfırlamaz.
    # ⚠ 10 → 7 DENENDİ VE GERİ ALINDI (2026-08-02). DÜŞÜRMEYİN.
    #
    # Gerekçe iyiydi: A5 sonrası 17 geçişte vuranlar görsel faza medyan
    # 11.11 m'de, ıskalayanlar 9.05 m'de girmişti. Kapıyı gevşetmek devri
    # uzaklaştırıp terminale daha çok tırmanma süresi bırakacaktı.
    #
    # Ölçüm bunu ÇÜRÜTTÜ — her ölçütte kötüleşti:
    #
    #                        KILIT_N=10 (5 uçuş)   KILIT_N=7 (1 uçuş)
    #   faz / uçuş                  3.4                  8.0
    #   giriş menzili medyan      10.00 m               9.62 m   ← DÜŞTÜ
    #   en yakın menzil medyan     1.73 m               2.08 m
    #   kor_dalis medyan            %19                  %27
    #   <1.5 s'de kopan faz        2/17                  4/8
    #   vuruş                      3/17                 1/8
    #
    # MEKANİZMA: kapı cılız tespitte de açılıyor. Erken devirler gerçekten
    # oluyor (14.73 m, 10.47 m'de girdi) ama hemen ölüyor — o iki faz 0.9 ve
    # 1.3 s sürdü, birinde kareler %69 kör_dalış, diğerinde %100 tespit_yok.
    # Faz KAYIP_M yiyip GPS'e dönüyor, drone bu arada yaklaşmış oluyor, bir
    # sonraki devir DAHA YAKINDA gerçekleşiyor. Net etki ters.
    #
    # Yani devir menzili ile vuruş arasındaki bağıntı nedensel DEĞİL: ikisi de
    # "tespit o an gerçekten sağlam mı"ya bağlı. Kapıyı gevşetmek sağlamlığı
    # üretmiyor, sadece sağlam sanılan anları çoğaltıyor.
    # Asıl kaldıraç terminal algı sürekliliği (vuran 4 geçişin dördünde de
    # kor_dalis ≤ %3) — bkz. UYGULANACAK.md B6.
    # TEK KAYNAK: dow/ayarlar.py::Ayar.DEVIR_KARE (bkz. KAYIP_M notu).
    KILIT_N = int(os.environ.get(
        "AVCI_HYBRID_KILIT_N", _DowAyar.DEVIR_KARE if _DowAyar else 10))
    KILIT_PENCERE = 15    # kayan pencere boyu (~0.5 s @30 Hz)
    # ⚠ 20 -> 60 (2026-08-16, UCUSTA DOGRULANDI). Kor pencere = KAYIP_M/dongu.
    # Koddaki "~0.66 s" 30 Hz varsayiyordu; olculen dongu 31.2 Hz ve gercek
    # kor pencere 20 karede 0.47 s (n=918 faz).
    # UCUS OLCUMU (conf sabit 0.35, tek degisken):
    #     K20  omur 1.91 s  iska 12.47 m  en iyi 9.73 m
    #     K45  omur 1.70 s  iska 12.89 m  en iyi 8.11 m
    #     K60  omur 3.06 s  iska 10.10 m  EN IYI 3.71 m   <- gunun rekoru
    # Iki bagimsiz simulator tezgahi da ayni yonu gosterdi (biri 12.3->5.7 m,
    # digeri kor pencere 0.47 s->14.1 m / 0.94 s->6.4 m). Buyukluk abartiliydi,
    # YON dogruydu. ⚠ K45 iyilesme gostermedi -> tepki monoton DEGIL, orneklem
    # kucuk (ayar basina 10-11 faz, kosu-arasi degiskenlik ~1 m).
    # ⭐ 2026-08-24 KULLANICI SARTI: "üst üste 20 kare algılamaz ise GPS'e geç"
    #   Eski deger 60 idi (~1.9 s @31 Hz); 20 kare ~0.64 s @31 Hz.
    #   TEK KAYNAK: dow/ayarlar.py::Ayar.KAYIP_KARE (yeni yasanin kendi
    #   dosyasinda zaten "10 kare tespit -> gorsel, 20 kare tespitsiz -> GPS"
    #   yaziyor). Iki yerde ayri sayi tutmak bunlarin sessizce ayrismasi
    #   demektir; buradan okunur.
    KAYIP_M = int(os.environ.get(
        "AVCI_KAYIP_M", _DowAyar.KAYIP_KARE if _DowAyar else 20))

    # ══ D0 KURAL UYUMU — DEVİR ÖLÇÜTÜ SADELEŞTİRİLDİ (2026-08-10) ══
    # Kullanıcı tespiti: "görsel temas sağlandıktan sonra GPS'ten güdüm
    # üretmek yasak; ekstra farklı bir şey olmasın — üst üste 10 kare
    # detection modeli algıladıysa görsel güdüme geçelim."
    #
    # ESKİ HÂLİNDE İKİ SAPMA VARDI:
    #   1) KAYAN PENCERE (son 15'in 10'u) — "üst üste 10" değil. Bu şart
    #      GEVŞEKTİ, yani devri erkene alıyordu (kural lehine).
    #   2) conf ≥ 0.5 — dedektörün kendi eşiği 0.35. Bu şart KATIYDI: model
    #      "gördüm" dediği hâlde güdüm GPS'te kalıyordu. İHLAL RİSKİ BUYDU.
    #
    # YENİ HÂLİ: tespit varsa (dedektör ne verdiyse) ve ARDIŞIK KILIT_N kare
    # sürdüyse devir. Ekstra güven eşiği YOK.
    # ⚠ RİSK: "10 ardışık" gürültülü tespitte geç sağlanabiliyordu — kayan
    # pencere tam bu yüzden konmuştu (2026-07-31). Devir menzili ölçülecek.
    # AVCI_HYBRID_ARDISIK=0 → eski kayan pencere davranışı geri gelir.
    # AVCI_HYBRID_CONF=0.5  → eski ekstra güven eşiği geri gelir.
    KILIT_ARDISIK = os.environ.get("AVCI_HYBRID_ARDISIK", "1") == "1"
    POSE_CONF_MIN = float(os.environ.get("AVCI_HYBRID_CONF", 0.0))

    # ── MENZİL KAPISI KAPATILDI (2026-08-08, D0 YARIŞMA KURALI) ──
    #
    # Kural: görsel temas kurulunca (tespit sürekliliği) GPS ile güdüm YASAK.
    # Menzil kapısı tam bunu ihlal ediyordu: 30 m'de hedef kesintisiz
    # görülürken kapı "henüz 20 m değil" deyip GPS güdümünü SÜRDÜRÜYORDU.
    # Kapıyı 20 → 12 m'ye çekmek ihlali BÜYÜTÜR (GPS'te daha uzun kalınır);
    # 2026-08-08'de bunu yaptım, kullanıcı yakaladı — yanlış refleksti.
    #
    # DOĞRU ÇÖZÜM: kapıyı kaldır, görsel fazı uzak menzilde de ÇALIŞIR yap.
    # Uzakta çalışamamasının kök nedeni kapı değil HIZDI: saf kutu-boyutu
    # modeli 8 m/s üretiyordu, hedef 15 m/s. Dondurulmuş taşıyıcı (bkz.
    # bbox_ibvs) bunu kapatıyor → devir artık her menzilde yaşanabilir.
    #
    # Geri açmak (deney amaçlı): AVCI_HYBRID_GATE=1
    GATE_KILIT = os.environ.get("AVCI_HYBRID_GATE", "0") == "1"
    GATE_MENZIL = float(os.environ.get("AVCI_HYBRID_GATE_MENZIL", 20.0))

    # ── ZORLA MOD (2026-08-14, kullanici istegi: "iki buton yap") ──────────
    # Arayuzdeki GPS/GORSEL butonlari BUNU yazar. Eskiden arayuzdeki switch
    # ana_kontrol.set_vis_mode()'a gidiyordu ama o fonksiyonun kendi aciklamasi
    # "HIBRITTE ETKISIZ ... guduume GIRMEZ" diyordu -> buton hicbir sey
    # yapmiyordu, faz kararini hep bu supervisor veriyordu.
    #   None / "OTO" : eski davranis (KILIT_N ardisik kare -> GORSEL). Bit-ayni.
    #   "GPS"        : GORSEL faza HIC gecilmez. Tespit gelse bile GPS yasasi
    #                  (Gazebo'dan tasinan gps_guidance) tek basina kosar.
    #   "GORSEL"     : GPS FAZIYLA BASLAR (repodaki ozgun akis). Kilit
    #                  KILIT_SURE_S saniye KESINTISIZ dolunca gorsel yasaya
    #                  devredilir -> GPS o an kesilir. Kacirirsa (KAYIP_M kare
    #                  tespitsiz) GPS fazina GERI DONER ve dongu tekrarlar.
    ZORLA_MOD = None

    # "GORSEL" modunda devir olcutu: KARE SAYISI degil SURE (kullanici istegi
    # 2026-08-14: "kilit 5 saniye dolduğunda vuracak").
    # Neden sure: kare hizi degisken (15-35 FPS olculdu) -> KILIT_N=10 kare
    # bazen 0.3 s bazen 0.7 s ediyordu. Sure kullanmak yarisma sartnamesindeki
    # 5 s kilit isteriyle de birebir ortusuyor (Cfg.VIS_WIN_NEED_S = 5.0).
    # 2026-08-15: 5.0 -> 0.0 (KAPALI). Sartname devir olcutunu ARDISIK KARE
    # olarak tanimliyor ("ust uste 10 kare tespit"); ustune bir de sure
    # kilidi kosmak "10 kare olunca GECMELIDIR" kuralini ihlal eder.
    # >0 verilirse EK sart olarak geri gelir (AVCI_KILIT_SURE_S=5).
    # ⚠ 0.0 -> 5.0 GERI ACILDI (2026-08-16, kullanici: "kilit 5 saniye
    # dolmadan GPS kesilmesin"). GEREKCE OLCULDU:
    #   10 gorsel fazin 10'unda menzil 11.7 m -> 32.1 m (+21 m UZAKLASMA).
    #   GPS bizi 7.0 m'ye getiriyor, gorsel faz 1.75 s'de firlatiyor,
    #   GPS tekrar topluyor -> kilit HIC birikemiyor, kutu %6'ya hic ulasmiyor.
    # 10-kare olcutu bizi hedefin YANINDAYKEN devrediyor ve orada kaybediyoruz.
    # Sure kilidi ile GPS istasyonda TUTAR, kilit birikir, sonra devredilir.
    # ⚠ Supervisor'in okudugu sayac `kilit_devir` -- FAZ FARK ETMEKSIZIN
    # sayar (ana_kontrol.py:1000), yani GPS fazinda da birikir. Dogru olan bu.
    # ⚠ Sartname yorumu: "ust uste 10 kare tespit -> GECMELIDIR" kurali hala
    # gecerli; bu EK bir sart ve devri GECIKTIRIR. Kullanici istegi bu yonde.
    KILIT_SURE_S = float(os.environ.get("AVCI_KILIT_SURE_S", 5.0))

    # ── GEOMETRI KAPISI (2026-08-15) — "B: kuyruk takibi" ─────────────────
    # NEDEN: kilit 5 s dolduğu için devredildi ama geometri YANDAN GEÇİŞTİ.
    # Ölçüm (bbox_ibvs_20260815_151957.csv, tek angajman):
    #   görsel faz 1.53 s sürdü, hedef YANDAN çıktı (cy sabit, eps_yaw 0→61°)
    #   aracın gerçek dönüş hızı max 94.6 °/s
    #   hatanın büyüme hızı      max 105.4 °/s   -> araç yetişemez
    # Kazanç artırmak çözmez; araç zaten limitte. Çözüm: yandan geçişte
    # DEVRETME, hedefin arkasına düşene kadar GPS'te kal.
    #
    # aspect_deg = hedefin hız vektörü ile LOS arası açı (gps_guidance yayınlar)
    #   0°  = hedef bizden uzaklaşıyor (kuyruk takibi, ω≈0 -> ideal)
    #   90° = yandan geçiş (ω patlar -> ıska)
    #
    # Eşik neden 40°: hedef 18 m/s ölçüldü (sabit, manevrada yavaşlamıyor).
    #   v_dik = 18·sin(40°) = 11.6 m/s -> 5 m'de ω = 133°/s  (hâlâ yüksek)
    #   v_dik = 18·sin(25°) =  7.6 m/s -> 5 m'de ω =  87°/s  (limitin altında)
    # Yani FİZİĞİN istediği ~25°. Ama çok dar eşik hiç devretmeme riski taşır;
    # 40° ile başlanıyor ve her karar loglanıyor -> gerçek dağılıma bakıp
    # AVCI_DEVIR_ASPECT ile daraltılacak. 999 vermek kapıyı KAPATIR (eski
    # davranış, bit-aynı).
    # 2026-08-15: 40 -> 999 (KAPALI). Ayni gerekce: sartname ek sart
    # tanimlamiyor. Geometri kapisinin OLCULEN faydasi duruyor (yandan
    # gecis devirlerini engelliyordu) -> AVCI_DEVIR_ASPECT=40 ile acilir.
    DEVIR_ASPECT_MAX = float(os.environ.get("AVCI_DEVIR_ASPECT", 999.0))

    # ── HAYALET KAPISI (2026-08-15) ────────────────────────────────────────
    # Kare kutu Talon olamaz. Olculdu (2993 tespitli kare): medyan w/h 2.86,
    # ~kare (1.0-1.3) bandi karelerin yalnizca %4.3'u ve orada yakalanan
    # vaka 63 kare boyunca DONUK 20.7x20.7 px'lik sahte bir kutuydu.
    # 1.3 esigi o bandi keser, gercek tespitlerin %95.7'sine dokunmaz.
    HAYALET_KAPISI = os.environ.get("AVCI_HAYALET", "1") == "1"
    HAYALET_WH_MIN = float(os.environ.get("AVCI_HAYALET_WH", 1.3))

    # ── BOYUT KAPISI (2026-08-16) ─────────────────────────────────────────
    # Devir icin kutunun kadrajin en az bu kadarini kaplamasi gerekir.
    # 0.05 = SARTNAMENIN KENDI kilit olcutu (bkz. Cfg.VIS_LOCK_PCT yorumu).
    # Olculdu: bu kapi olmadan devirler medyan 32.9 m'de, kutu %1.6 iken
    # oluyor ve faz 1.08 s'de oluyor -> 40 dakikada 37 gecis.
    # AVCI_DEVIR_BOYUT=0 -> kapali.
    # ⚠ BIRIM PIKSEL. Yasaya giden kayitta w,h piksel (tespit_akisi.py:9),
    # yasa cercevesi 640x480 -> sartnamedeki %5 kilit olcutu = 32 px.
    # Ilk surum oran (0.05) kullaniyordu ve kapi hic atesleyemedi.
    # AVCI_DEVIR_BOYUT=0 -> kapali. 20 px ~ %3 (~17 m), 32 px ~ %5 (~10 m).
    # 32 -> 24 (2026-08-16): 32 px gecmis veride %95'lik dilimin USTUNDE
    # (medyan 12.7, %90 22.9, %95 27.6) -> 10 ARDISIK kare toplanamayabilir
    # ve hic devretmeme riski dogar, ki bu savrulmadan da kotudur.
    # 24 px ~ %3.75 ~ 13 m: GPS fazinin olculen kilit mesafesi (9-15 m) ile
    # ortusuyor, yani ULASILABILIR; buna karsilik eski efektif esik ~12 px'ti.
    # ⚠ 24.0 -> 14.0 (2026-08-16, UCUSTA OLCULDU). 24 px konurken kapinin
    # hangi menzile karsilik geldigi HESAPLANMAMISTI. Canli olcum (52 ornek,
    # gercek menzil ile): R * max(w,h) = 310 px·m. Yani:
    #     24 px -> devir ancak 12.9 m'de   (fiili olarak HIC atesLENMEZ)
    #     14 px -> devir 22.2 m'ye kadar
    # Simulator devir mesafesine gore vurusu olctu (30 angajman/nokta):
    #     8 m 27/30 | 13 m 27/30 | 20 m 24/30 | 30 m 16/30 | 40 m 7/30
    # Yani 22 m'ye kadar guvenli, 30 m'den sonra cokuyor. 14 px tam oraya
    # denk geliyor: iyi bandi ACIK birakir, cokus bandini KAPALI tutar.
    DEVIR_BOYUT_PX = float(os.environ.get("AVCI_DEVIR_BOYUT", 14.0))

    # ── BOYUT KAPISI NEREDE UYGULANIR (2026-08-17, ALGI SUREKLILIGI) ──────
    # ⛔ OLCULEN HATA: kapinin GEREKCESI menzil ("30 m'den sonra vurus cokuyor"),
    # ama UYGULAMASI kare-gecerliligi. `gorulen = False` yazinca yalniz devri
    # geciktirmiyor, SUREKLILIK SAYACINI da sifirliyor (ardisik_gor).
    #
    # OLCUM (arac/algi_sureklilik.py, 2026-08-17 ayna-sonrasi, 30733 kare):
    #   BOYUT kapisi tum karelerin %29.5'ini eliyor
    #   20-30 m bandinda karelerin %66.4'unu eliyor -> o bantta GECERLI %3.4
    #   DEVIR akiminda kesintisiz epizod: medyan 0.39 s, MAX 2.66 s,
    #     >=5 s epizod sayisi = 0  -> 5 s sarti YAPISAL OLARAK IMKANSIZ
    #   Kapi kare-gecerliliginden cikarilinca: max 2.66 -> 9.64 s,
    #     >=5 s epizod 0 -> 22 (%2.72), kilit zamaninin %17.8'i >=5 s icinde
    #
    # ⚠ OLCEK DUZELTMESI: yukaridaki "14 px -> 22.2 m" ESKI 310 px*m
    # sabitinden geliyordu. Yasaya giden kutu DoW pikselinin FX/fx_dow =
    # 166.58/531.36 = 0.3135 katidir (tespit_akisi.dow_pikseli_yasaya) ve
    # canli olculen DoW sabiti menzil*max(w,h)=743 px*m (n=966). Yani
    #     yasa cercevesinde  menzil * max(w,h) = 232.9 px*m
    #     14 px  ->  16.6 m   (22.2 m DEGIL)
    # Kapi, sanildigindan 5.6 m DAHA YAKINA kilitliyordu.
    #
    # "devir" MODU: boyut testi kare-gecerliliginden CIKAR, yalnizca DEVIR
    # KARARINDA uygulanir. Menzil kisiti AYNEN korunur (devir yine ~16.6 m
    # icinde olur) ama sureklilik sayaci her GERCEK tespiti sayar.
    # "kare" (VARSAYILAN) = bugunku davranis, BIT-AYNI.
    DEVIR_BOYUT_MOD = os.environ.get("AVCI_DEVIR_BOYUT_MOD", "kare").strip().lower()
    # "devir" modunda kapi ARTIK tek karenin boyutuna bakar. Kutu olcusu
    # gurultuludur (bbox_ibvs'te ayni menzilde 0-8 px ile 16-24 px kareler
    # yan yana) -> tek buyuk kare 30 m'de sahte devir tetikleyebilirdi.
    # Bu yuzden "devir" modunda boyut sartinin N ARDISIK karede saglanmasi
    # istenir. 1 = filtre yok (ham tek kare).
    DEVIR_BOYUT_N = int(float(os.environ.get("AVCI_DEVIR_BOYUT_N", 3)))

    # ── HAYALET KAPISI: EN-BOY ORANI KUCUK KUTUDA ANLAMSIZ (2026-08-17) ────
    # Kapi "kare kutu Talon olamaz" varsayimiyla kondu ve BUYUK kutuda
    # olculdu (%4.3). Kucuk kutuda w/h kuantalanma gurultusudur.
    # OLCUM (bbox_ibvs, 2026-08-17 ayna-sonrasi, 14340 gercek kutulu kare):
    #     max(w,h)  0- 8 px -> w/h<1.3 orani %78.8   (~29-233 m)
    #               8-16 px -> %27.0                 (~15-29 m)  <- DEVIR BANDI
    #              16-24 px -> %12.3
    #              32-40 px -> %7.2                  <- kapinin kalibre edildigi yer
    #              40-48 px -> %5.4
    # Yani kapi, devir bandinda gercek tespitlerin dortte birini "hayalet"
    # sayiyor ve kilidi KIRIYOR (kk.guncelle(..., hayalet=True)).
    # GPS fazinda 10-20 m bandinda karelerin %24.7'si bu kapiya takiliyor.
    #
    # "boyut" MODU: en-boy testi yalniz max(w,h) >= HAYALET_MIN_PX iken
    # uygulanir; kucuk kutular icin yerine DONUK KUTU testi konur — yakalanan
    # gercek vakanin imzasi zaten oydu (63 kare boyunca 20.7x20.7 px, std 0.07).
    # "oran" (VARSAYILAN) = bugunku davranis, BIT-AYNI.
    HAYALET_MOD = os.environ.get("AVCI_HAYALET_MOD", "oran").strip().lower()
    HAYALET_MIN_PX = float(os.environ.get("AVCI_HAYALET_MIN_PX", 24.0))
    HAYALET_DONUK_N = int(float(os.environ.get("AVCI_HAYALET_DONUK_N", 8)))
    HAYALET_DONUK_EPS = float(os.environ.get("AVCI_HAYALET_DONUK_EPS", 0.5))

    # ── DUZ KISIM KAPISI (2026-08-15) — asil hamle ─────────────────────────
    # GEREKCE ZINCIRI (hepsi olculdu):
    #   1. Hedefin yolunun %52'si DUZ (oval pist, 530 m tur, 51 m yaricap).
    #   2. Saf takip yon kanalinda SAF ORANSAL kontrolcudur; rampa girdiye
    #      kalici hatasi e_ss = rampa_egimi/K'dir ve K sonsuz olmadikca
    #      SIFIRLANMAZ. Donen hedefte kerteriz rampadir -> kalici hata
    #      KACINILMAZ. (Gazebo ekibi bunu bagimsiz dogruladi, RAPOR §12.5.)
    #   3. DUZ kisimda lambda_dot ~ 0 -> rampa girdi YOK -> kalici hata YOK.
    #   4. Gazebo'nun %65 isabet aldigi kosul tam budur: duz ucan hedef.
    #      Ayni yasa dairede 62 angajmanda 0 isabet veriyor.
    #   5. Bizim aracin hiz vektoru en fazla g·tan(45°)/V = 26 °/s donebiliyor,
    #      donuste gereken 33-36 °/s. Fizik yetmiyor -- yasa degil.
    # => Yasayi degistirmek yerine devri hedefin DUZ kismina denk getir;
    #    problem Gazebo'nun COZULMUS rejimine tasinmis olur.
    #
    # ⚠ SARTNAME GERILIMI: sartname "ust uste 10 kare tespit -> GECMELIDIR"
    # diyor. Bu kapi EK sart oldugu icin varsayilan KAPALI (999).
    # Deney icin: AVCI_DEVIR_DONUS=8
    DEVIR_DONUS_MAX = float(os.environ.get("AVCI_DEVIR_DONUS", 999.0))

    # ── SINIRLI BEKLEME (2026-08-18) — SARTNAME GERILIMINI COZER ──────────
    # Yukaridaki kapi ENGELLEYICI: geometri kotuyken devir HIC olmaz ve
    # "10 kare -> GECMELIDIR" kurali ihlal edilir.
    # Bu parametre kapiyi BEKLEMEYE cevirir: 10 kare dolduysa ve geometri
    # kotuyse EN FAZLA bu kadar saniye bekler, sonra YINE DEVREDER.
    # Boylece sartname korunur (devir mutlaka olur) ama firsat varsa daha
    # iyi kosulda olur.
    #
    # OLCUM (713 devir, 2026-08-18): devir aninda hedefin donus hizi
    # sonucu belirliyor. Normalize olcut = kapatma orani:
    #     omega < 5 °/s   -> kapatma %63,  >=%70 olan %41
    #     omega 15-30 °/s -> kapatma %29,  >=%70 olan %10
    # Ve dogru degisken omega degil `omega x t_go` (yaklasma boyunca hedefin
    # donecegi aci): <10° -> kapatma %79 ; >60° -> %15.
    # Hedefin turunun ~%47'si duz, dolayisiyla 1-3 s beklemek genelde yeterli.
    # 0 = bekleme YOK (varsayilan, davranis BIT-AYNI).
    DEVIR_BEKLE_MAX_S = float(os.environ.get("AVCI_DEVIR_BEKLE", 0.0))




# Telemetri/arayüz için son durum (gcs_server okur; salt gözlem)
status = {"faz": "GPS", "gecis_sayisi": 0, "kilit_sayac": 0, "son_sebep": None}

# ── SARTNAME KILIT SAYACI KANCASI (2026-08-14) ─────────────────────────────
# "GORSEL" modunda devir olcutu ARTIK ham tespit sayisi DEGIL, arayuzun ust
# barinda gordugun "X.X / 5.0 s" sayaci.  O sayac guidance/kilit_sayaci.py'de
# tutuluyor ve sartname kurallarini uyguluyor:
#     * hedef MERKEZI "Hedef Vurus Alani" (AV) icinde olacak
#     * bbox en az bir eksende kadranin >= %6'si olacak (VIS_LOCK_PCT)
#     * bunlar 10 s'lik pencerede KUMULATIF 5 s saglanacak
# Ham tespit saymak yanlisti: model hedefi 100 m'de de goruyor ama o "kilit"
# degil. Kullanicinin ekranda gordugu sayac ile guduumun kullandigi sayac
# ayni olmali -- yoksa "kilit doldu ama bir sey olmadi" yasaniyor (14 Agu).
# server.py bu kancayi doldurur: kilit_kaynagi = lambda: beyin.kilit.durum()
kilit_kaynagi = None        # () -> {"sure": float, "ok": bool, ...} | None

# ── DEVIR SAYACINI SIFIRLAMA KANCASI (2026-08-14) ──────────────────────────
# Devir sayaci 10 s'lik pencerede KUMULATIF calisiyor. Gorsel faz olup GPS'e
# donuldugunde sayacta hala eski ~5 s duruyordu -> hedef HIC gorunmezken
# aninda SAHTE bir devir daha tetikliyordu.
# KANIT (15 Agu karar logu) -- devirler ikiserli geliyordu:
#     #1 t=19.0  mesafe 21.4 m  kutu %2.2  conf 0.70  merkez ICINDE  (gercek)
#     #2 t=23.7  mesafe 21.4 m  kutu %1.3  conf  -    merkez DISINDA (sahte)
#     #3 t=63.9  ... ICINDE (gercek)   #4 t=67.6 ... DISINDA (sahte)
# Sahte devirlerde gorsel faz 0/59, 1/74 kare kutu goruyordu -- yasanin
# elinde hicbir sey yoktu. Devir aninda sayac SIFIRLANIR.
kilit_sifirla = None        # () -> None | None


# ── KARAR LOGU (2026-08-14, kullanici istegi: "neden oyle yaptigini full logla")
# Supervisor'in HER degerlendirmesini CSV'ye yazar: ne gordu, sayaclar neydi,
# ne karar verdi ve NEDEN. "Kilit doldu ama bir sey olmadi" tipi sorunlarin
# ekran goruntusuyle degil KAYITLA cozulmesi icin.
_KARAR_LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "..", "..", "logs")


class _KararLog:
    # ⚠ 2026-08-17: w,h,cx_yasa,cy_yasa,eleme,kilit_kes_s,u_truth,v_truth
    # EKLENDI (SALT GOZLEM).
    # Sebep 1: kopma taksonomisi (arac/algi_sureklilik.py) BOYUT ile HAYALET
    # kapisini birbirinden ayiramiyordu — `gorulen` ikisinin de sonucu ve
    # kutu olculeri loga hic yazilmiyordu. Ayrim MENZIL MODELIYLE tahmin
    # edilmek zorunda kalindi. w/h/cx_yasa/cy_yasa/eleme ayrimi OLCULEBILIR yapar.
    # Sebep 2: "conf esigini dusurmek yanlis pozitif getirir mi?" sorusu ancak
    # kutunun GERCEKTEN hedefin oldugu yerde olup olmadigina bakilarak
    # cevaplanabilir. u_truth/v_truth = hedefin TRUTH'tan projekte edilmis
    # piksel konumu (guidance_core.hedef_kadraj_hatasi -> gps_guidance.status).
    # AYNI SATIRDA cx_yasa ile karsilastirilir: |cx_yasa - u_truth| kucukse
    # tespit GERCEK, buyukse YANLIS POZITIF. Ayri log eslestirmesi gerekmez.
    # ⛔ Bu alanlar YALNIZ LOGA yazilir; yasaya/karara GIRMEZ (D0: gorsel faz
    #    GPS gormez). supervisor GPS fazinda calisir, bbox_ibvs bunlari okumaz.
    # Kolonlar SONA eklendi ve csv.DictReader ile okunuyor -> eski cozumleyici
    # kirilmaz (depoda karar_*.csv okuyan baska betik zaten YOK, arandi).
    BASLIK = ("t,mod,faz,gorulen,conf,kilit_s,esik_s,boyut_pct,esik_pct,"
              "merkez_av,d_h_m,karar,sebep,"
              "w,h,cx_yasa,cy_yasa,eleme,kilit_kes_s,u_truth,v_truth\n")

    def __init__(self):
        self.f = None
        self._t0 = time.monotonic()

    def ac(self):
        try:
            os.makedirs(_KARAR_LOG_DIR, exist_ok=True)
            ad = time.strftime("karar_%Y%m%d_%H%M%S.csv")
            self.f = open(os.path.join(_KARAR_LOG_DIR, ad), "w",
                          encoding="utf-8", buffering=1)
            self.f.write(self.BASLIK)
            print("[SUPERVISOR] karar logu: %s" % ad)
        except Exception as e:
            print("[SUPERVISOR] karar logu acilamadi: %r" % (e,))
            self.f = None

    def yaz(self, **k):
        if self.f is None:
            return
        try:
            self.f.write(
                "%.2f,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,"
                "%s,%s,%s,%s,%s,%s,%s,%s\n" % (
                    time.monotonic() - self._t0,
                    k.get("mod", ""), k.get("faz", ""),
                    int(bool(k.get("gorulen"))), _s(k.get("conf")),
                    _s(k.get("kilit_s")), _s(k.get("esik_s")),
                    _s(k.get("boyut_pct")), _s(k.get("esik_pct")),
                    k.get("merkez_av", ""), _s(k.get("d_h")),
                    k.get("karar", ""), k.get("sebep", ""),
                    # SALT GOZLEM (2026-08-17): kopma taksonomisi icin
                    _s(k.get("w"), 1), _s(k.get("h"), 1),
                    _s(k.get("cx"), 1), _s(k.get("cy"), 1),
                    k.get("eleme", ""), _s(k.get("kilit_kes_s")),
                    _s(k.get("u_truth"), 1), _s(k.get("v_truth"), 1)))
        except Exception:
            pass

    def kapat(self):
        try:
            if self.f:
                self.f.close()
        except Exception:
            pass
        self.f = None


def _s(v, n=2):
    """Sayiyi CSV icin bicimle; None -> bos."""
    try:
        return "" if v is None else ("%.*f" % (n, float(v)))
    except Exception:
        return ""


karar_log = _KararLog()


def _kopru(parent_event, child_event):
    """parent set olunca child'ı da set eder (faz thread'i ana stop'u duysun)."""
    def izle():
        while not parent_event.is_set() and not child_event.is_set():
            parent_event.wait(0.5)
        if parent_event.is_set():
            child_event.set()
    threading.Thread(target=izle, daemon=True).start()


def run_hybrid(conn, get_plane, get_iris, wait_pose, get_plane_truth,
               stop_event, sup_cfg=SupCfg, lead_cfg=LeadCfg, get_temas=None,
               get_menzil=None, get_gercek=None):
    status.update(faz="GPS", gecis_sayisi=0, kilit_sayac=0, son_sebep=None)
    karar_log.ac()          # her gorev = ayri karar logu (neden-nicin kaydi)
    # KILIT DENETIM KAYDI: kapi KAPALI olsa da acilir — mevcut davranisin ne
    # kadar ihlal urettigini olcmek icin (kullanici istegi 2026-08-17).
    kilit_denetim.ac()
    if KilitKapiCfg.acik():
        print("[SUPERVISOR] ⏱ KESINTISIZ KILIT KAPISI ACIK: %.1f s "
              "(conf≥%.2f, bosluk tolerans %s) — bu sure "
              "DOLMADAN gorsel/terminal faza GECILMEZ"
              % (KilitKapiCfg.ESIK_S, KilitKapiCfg.CONF_MIN,
                 ("%.2f s [kare hizindan BAGIMSIZ]" % KilitKapiCfg.BOSLUK_S)
                 if KilitKapiCfg.BOSLUK_MOD == "sure"
                 else ("%d kare / %.2f s" % (KilitKapiCfg.BOSLUK_KARE,
                                             KilitKapiCfg.BOSLUK_S))))
        # DOLULUK tabani: "5 s kilit"in yuzde kaci GERCEKTEN gozlemlenmis
        # olmali. Kapali (0) iken sure sarti TEK BASINA yeterlidir ve
        # olculen doluluk medyani yalnizca %59.7'dir (tezgah, 2026-08-17)
        # -- yani kilit "kesintisiz" adini tam hak etmez. Bu satir hangi
        # tanimin yururlukte oldugunu ucus logunda GORUNUR kilar.
        if float(getattr(KilitKapiCfg, "DOLULUK_MIN", 0.0) or 0.0) > 0.0:
            print("[SUPERVISOR] ⏱ DOLULUK TABANI: kilidin >=%%%.0f'i GERCEKTEN "
                  "gozlemlenmis olmali (AVCI_KILIT_DOLULUK)"
                  % (100.0 * KilitKapiCfg.DOLULUK_MIN))
        else:
            print("[SUPERVISOR] ⏱ DOLULUK tabani KAPALI — sure sarti tek "
                  "basina; kilit icinde kor zaman SINIRSIZ (olculen doluluk "
                  "medyani %59.7). Sikilastirmak icin: AVCI_KILIT_DOLULUK=0.80")
    else:
        print("[SUPERVISOR] ⏱ kesintisiz kilit kapisi KAPALI (AVCI_KILIT_S=0) "
              "— davranis degismedi, yalniz denetim kaydi tutuluyor")

    # ── ALGI SUREKLILIGI ANAHTARLARI (2026-08-17) — MEKANIZMA KAPISI ───────
    # Bu satir loga BASILMADIYSA yama DEVREDE DEGILDIR ve o kosunun A/B
    # sonucu GECERSIZDIR. (Deney disiplini: sessiz kurulum hatasi, sahte
    # "fark yok" sonucu uretiyordu.)
    print("[SUPERVISOR] 🔎 ALGI: boyut_mod=%s (%.0f px ~ %.1f m, ardisik %d) | "
          "hayalet_mod=%s (oran>=%.2f, min_px=%.0f, donuk %d kare/%.1f px) | "
          "kilit_conf=%.2f | kadraj_mod=%s"
          % (sup_cfg.DEVIR_BOYUT_MOD, sup_cfg.DEVIR_BOYUT_PX,
             (232.9 / sup_cfg.DEVIR_BOYUT_PX) if sup_cfg.DEVIR_BOYUT_PX > 0 else -1,
             sup_cfg.DEVIR_BOYUT_N,
             sup_cfg.HAYALET_MOD, sup_cfg.HAYALET_WH_MIN, sup_cfg.HAYALET_MIN_PX,
             sup_cfg.HAYALET_DONUK_N, sup_cfg.HAYALET_DONUK_EPS,
             KilitKapiCfg.CONF_MIN,
             getattr(KilitKapiCfg, "KADRAJ_MOD", "yasa")))
    # ⚠ ESIK UYUSMAZLIGI UYARISI: boru hattinin kendi esigi (Cfg.VIS_CONF_MIN,
    # server.py:1621 det_beyin kapisi) kilit esiginden DUSUKSE, arada kalan
    # kutular yasaya GIRER ama kilide SAYILMAZ -> kilit sebepsiz kirilir.
    # Olculdu (2026-08-17, 30733 kare): campaign VIS_CONF=0.25 iken kilit
    # esigi 0.35 -> 1713 kare (%5.6) bu araliktaydi ve kilit kirilmalarinin
    # %17.4'unu tek basina bu yapti.
    try:
        _vis_conf = float(os.environ.get("AVCI_VIS_CONF", "0.35") or 0.35)
        if KilitKapiCfg.CONF_MIN > _vis_conf + 1e-6:
            print("[SUPERVISOR] ⚠ ESIK UYUSMAZLIGI: boru hatti conf>=%.2f "
                  "gecirirken kilit conf>=%.2f istiyor. Aradaki kutular yasaya "
                  "girer ama kilide SAYILMAZ -> kilit sebepsiz kirilir. "
                  "Hizalamak icin: AVCI_KILIT_CONF=%.2f"
                  % (_vis_conf, KilitKapiCfg.CONF_MIN, _vis_conf))
    except (TypeError, ValueError):
        pass

    while not stop_event.is_set():
        # ZORLA MOD: arayuzdeki iki butonun gercek karsiligi (bkz. SupCfg.ZORLA_MOD)
        _zorla = (getattr(sup_cfg, "ZORLA_MOD", None) or "OTO").upper()

        # HER IKI MODDA DA GPS FAZIYLA BASLANIR (kullanici istegi 2026-08-14):
        #   "GPS"    -> gorsel faza HIC gecilmez (asagida kapi kapali)
        #   "GORSEL" -> kilit KILIT_SURE_S saniye dolunca gorsele devredilir,
        #               kacirirsa GPS'e geri donulur (repodaki ozgun akis)
        # ══ GPS FAZI ══ (gps_guidance kendi 20 Hz döngüsünde; izci pose akışını sayar)
        status["faz"] = "GPS"
        faz_stop = threading.Event()
        _kopru(stop_event, faz_stop)
        tetik = {"gorsel": False}

        def izci():
            pencere = collections.deque(maxlen=sup_cfg.KILIT_PENCERE)
            ardisik = 0
            son_seq = 0
            kilit_t0 = None            # kesintisiz kilidin BASLADIGI an (GORSEL modu)
            ardisik_gor = 0            # ardışık TESPİTLİ kare (şartname: 10 -> GÖRSEL)
            hayalet_n = 0              # hayalet kapisinin eledigi kare sayisi
            kucuk_n = 0                # boyut kapisinin eledigi kare sayisi
            boyut_ok = True            # son karede BOYUT kapisi gecti mi ("devir" modu)
            ardisik_boyut = 0          # ust uste BOYUT sartini saglayan kare
            donuk_gec = collections.deque(maxlen=max(2, sup_cfg.HAYALET_DONUK_N))
            donuk_n = 0                # DONUK KUTU testinin eledigi kare
            # ── GERCEK KESINTISIZ KILIT SAYACI (2026-08-17) ────────────────
            # `ardisik`/`ardisik_gor` KARE sayar (10 kare = olculen 0.45-0.51 s).
            # `kilit_devir.sure` 10 s pencerede KUMULATIF sayar.
            # Ikisi de "5 s KESINTISIZ" demek DEGIL. Bu sayac gercekten
            # kesintisiz olcer; kapi AVCI_KILIT_S ile acilir (varsayilan 0=kapali).
            kk = KesintisizKilit()
            tetik["kk"] = kk
            while not faz_stop.is_set():
                kayit = wait_pose(son_seq, timeout=0.5)
                if kayit is None:
                    continue
                son_seq = kayit["seq"]
                pose = kayit["pose"]
                gorulen = (pose is not None
                           and pose.get("conf", 0.0) >= sup_cfg.POSE_CONF_MIN)

                # ── HAYALET KAPISI (2026-08-15) ────────────────────────────
                # YAKALANAN VAKA (bbox_ibvs_20260815_172219.csv):
                #   63 kare boyunca kutu 20.7x20.7 px, TAM KARE, std 0.07 —
                #   yani HİÇ değişmemiş. Aynı sürede hedefin GERÇEK menzili
                #   45.8 -> 50.6 m'ye AÇILIYORDU. Güdüm 3 saniye boyunca
                #   hedefi 7.7 m'de sanıp gerçekte 46 m'deki bir şeyi kovaladı.
                #
                # Talon bir UÇAK: 2993 tespitli karenin ölçülen w/h dağılımı
                #   ~kare (1.0-1.3) %4.3      <- bu bant SAHTE
                #   2.0-3.0          %48.8
                #   3.0-5.0          %39.4    <- uçak gibi
                #   medyan           2.86
                # Kare kutu Talon olamaz.
                #
                # ⚠ ŞARTNAME İHLALİ DEĞİL: şartname "hedefi tespit ederse"
                # diyor. Kare bir leke hedef DEĞİL; onu saymak şartnameyi
                # uygulamak değil, yanlış uygulamaktır. Eski devir ölçütünde
                # bir "kutu küçük -> uzak" kapısı vardı; ek şartları kapatınca
                # o da kalktı ve bu boşluk açıldı.
                # AVCI_HAYALET=0 -> kapalı (eski davranış).
                # ── BOYUT KAPISI (2026-08-16) — FAZ SAVRULMASINI DURDURUR ──
                # ÖLÇÜLDÜ: 40 dakikada 37 görsel faz, medyan ömür 1.08 s
                # (%43'ü 1 s'nin altında), devir mesafesi medyan 32.9 m,
                # orada kutu ~10 px (kadrajın %1.6'sı) ve faz içinde tespit
                # sürekliliği yalnız %13. Yani 10 ardışık kare zar zor
                # toplanıyor, hemen kaybediliyor, GPS'e dönülüyor, tekrar
                # devrediliyor — 37 kez.
                #
                # Gazebo ekibinin uyarısı birebir bu (RAPOR §12.4/ÖNERİ 4):
                #   "Angajman başına 20-30 geçiş varsa asıl sorununuz güdüm
                #    yasası DEĞİL, faz kararsızlığıdır ve yasayı değiştirmek
                #    işe yaramaz."
                #
                # ⚠ ŞARTNAME İHLALİ DEĞİL — TAM TERSİ: şartnamenin kendi kilit
                # ölçütü "bbox en az bir eksende kadrajın >= %5'i"
                # (bkz. Cfg.VIS_LOCK_PCT = 0.06, şartname kuralı >= 0.05).
                # Kadrajın %1.6'sını kaplayan bir lekeyi "tespit edilmiş hedef"
                # saymak şartnameyi uygulamak değil, kendi kilit tanımını
                # çiğnemektir. Bu kapı 10-ardışık-kare kuralını, şartnamenin
                # GEÇERLİ tespit tanımıyla birleştirir.
                # AVCI_DEVIR_BOYUT=0 -> kapalı (eski davranış).
                # ⚠ BIRIM: yasaya giden kayitta w,h PIKSEL cinsinden
                # (tespit_akisi.py:9 "tam-kare piksel"), normalize DEGIL.
                # Ilk surumde 0.05 (oran) ile kiyaslanmisti ve kapi HIC
                # atesleyemedi -- 10-30 px her zaman 0.05'ten buyuk.
                # Yasa cercevesi 640x480 (tespit_akisi._yasa_icsellik:
                # CX=320, CY=240) -> sartnamedeki %5 = 32 piksel.
                # ⚙ 2026-08-17: kapinin NEREDE uyguladigi artik secilebilir.
                #   "kare"  (VARSAYILAN) -> gorulen=False; sureklilik sayaci da kirilir
                #   "devir"              -> yalniz boyut_ok=False; DEVIR KARARINDA
                #                           kullanilir, sureklilik SAYILMAYA devam eder
                #   (bkz. SupCfg.DEVIR_BOYUT_MOD; olcum orada)
                boyut_ok = True
                if gorulen and sup_cfg.DEVIR_BOYUT_PX > 0.0:
                    _w = pose.get("w") or 0.0
                    _h = pose.get("h") or 0.0
                    if max(_w, _h) < sup_cfg.DEVIR_BOYUT_PX:
                        boyut_ok = False
                        if sup_cfg.DEVIR_BOYUT_MOD != "devir":
                            gorulen = False
                        kucuk_n += 1
                        if kucuk_n in (1, 100) or kucuk_n % 1000 == 0:
                            print("[SUPERVISOR] BOYUT KAPISI [%s]: kutu %.0f px < "
                                  "%.0f px (kadrajin %%%.1f'i, ~%.1f m) -> hedef "
                                  "UZAK%s [toplam %d]"
                                  % (sup_cfg.DEVIR_BOYUT_MOD, max(_w, _h),
                                     sup_cfg.DEVIR_BOYUT_PX,
                                     100 * max(_w, _h) / 640.0,
                                     (232.9 / max(_w, _h)) if max(_w, _h) > 0 else -1,
                                     (", tespit sayilmadi"
                                      if sup_cfg.DEVIR_BOYUT_MOD != "devir"
                                      else ", DEVIR bloke (tespit SAYILDI)"),
                                     kucuk_n))
                ardisik_boyut = (ardisik_boyut + 1) if (boyut_ok and gorulen) else 0

                _hayalet_bu = False        # bu kare HAYALET olarak mi elendi
                if gorulen and sup_cfg.HAYALET_KAPISI:
                    _w = pose.get("w") or 0.0
                    _h = pose.get("h") or 0.0
                    if _w > 0 and _h > 0:
                        # DUZELTME 2026-08-24: _w/_h -> max/min (YON BAGIMSIZ)
                        #   ESKI: _oran = _w / _h. Bu YONE BAGLI bir olcut:
                        #   kutu enden uzunsa buyuk, BOYDAN uzunsa 1'in ALTINDA
                        #   cikar. Talon yattikca kanat acikligi dikeye doner,
                        #   kutu boydan uzar, oran duser ve kapi tespiti ATAR.
                        #
                        #   OLCULDU (6000 GERCEK etiketli kare, veri seti):
                        #       w/h < 1.30 olan          : %44.2
                        #       w/h < 1.00 (boydan uzun) : %28.6  -> %100 elenir
                        #     hedefin yatikligina gore elenme orani:
                        #        0-10 der %36.4 | 20-30 %45.3 | 30-40 %50.9
                        #       40-90 der %58.9   <- yatik hedefte YARIDAN FAZLA
                        #   Ucusta bildirilen "talon roll yapinca algilama
                        #   kesiliyor" TAM BUYDU: model goruyor, supervisor atiyor.
                        #
                        #   YENI: max/min -- kutu hangi yone uzun olursa olsun
                        #   ayni sonucu verir. Ayni 6000 karede eleme %26.4'e
                        #   iner ve YATIKLIKTAN BAGIMSIZ olur (%25-29 sabit).
                        #
                        #   KAPININ AMACI KORUNUYOR: yakalanan gercek hayalet
                        #   20.7x20.7 px KARE bir kutuydu; max/min = 1.0, yani
                        #   yeni olcutle de ELENIR. Sadece yatik ucak artik
                        #   cezalandirilmiyor. Ustelik o vakanin asil imzasi
                        #   "63 kare boyunca HIC degismeyen kutu" idi ve onu
                        #   DONUK KUTU testi bagimsizca yakaliyor.
                        #
                        #
                        #   UCUSTA DOGRULANDI (2026-08-24, canli gorev, ayni
                        #   karede iki olcut birden sayildi): 200 kutu ->
                        #   ikisi de eledi 23 | ikisi de gecirdi 164 |
                        #   YENI KURTARDI 13 (%6.5) | YENI KAYBETTI 0.
                        #   Kayip SIFIR tesaduf degil, YAPISAL: max/min >= w/h
                        #   her zaman dogru oldugundan yeni olcut eskinin
                        #   gecirdigi hicbir kutuyu eleyemez.
                        #   (%6.5 < %44 cunku bu kosu kuyruktan duz takipti;
                        #    kazanc hedef yattikca buyur.)
                        #   Eski davranis: AVCI_HAYALET_ORAN=yonlu
                        if os.environ.get("AVCI_HAYALET_ORAN", "mutlak") == "yonlu":
                            _oran = _w / _h                    # ESKI (yone bagli)
                        else:
                            _oran = max(_w, _h) / min(_w, _h)  # YENI (yon bagimsiz)
                        # ⚙ 2026-08-17 "boyut" MODU: en-boy testi ancak kutu
                        # anlamli olcude buyukse uygulanir (kucuk kutuda w/h
                        # kuantalanma gurultusu; olcum SupCfg.HAYALET_MOD'da).
                        _oran_uygula = (
                            sup_cfg.HAYALET_MOD != "boyut"
                            or max(_w, _h) >= sup_cfg.HAYALET_MIN_PX)
                        if _oran_uygula and _oran < sup_cfg.HAYALET_WH_MIN:
                            gorulen = False
                            _hayalet_bu = True
                            hayalet_n += 1
                            if hayalet_n in (1, 25) or hayalet_n % 200 == 0:
                                print("[SUPERVISOR] HAYALET KAPISI (oran): kutu "
                                      "en/boy %.2f < %.2f, max(w,h)=%.0f px -> "
                                      "tespit SAYILMADI [toplam %d]"
                                      % (_oran, sup_cfg.HAYALET_WH_MIN,
                                         max(_w, _h), hayalet_n))
                        # ── DONUK KUTU TESTI (2026-08-17) ─────────────────
                        # En-boy testi kucuk kutuda kapatilinca acilan bosluk
                        # BUYUK degil: yakalanan gercek hayaletin imzasi
                        # "kutu HIC degismiyor" idi (63 kare 20.7x20.7,
                        # std 0.07 px). Bu test tam onu arar ve en-boy
                        # testinin aksine BOYUTTAN BAGIMSIZDIR.
                        # Yalniz "boyut" modunda devrede; varsayilan modda
                        # calismaz -> davranis BIT-AYNI.
                        elif sup_cfg.HAYALET_MOD == "boyut":
                            donuk_gec.append((round(_w, 2), round(_h, 2),
                                              round(pose.get("cx") or 0.0, 2),
                                              round(pose.get("cy") or 0.0, 2)))
                            if len(donuk_gec) >= sup_cfg.HAYALET_DONUK_N:
                                _e = sup_cfg.HAYALET_DONUK_EPS
                                _ilk = donuk_gec[0]
                                if all(abs(a[i] - _ilk[i]) <= _e
                                       for a in donuk_gec for i in range(4)):
                                    gorulen = False
                                    _hayalet_bu = True
                                    donuk_n += 1
                                    if donuk_n in (1, 25) or donuk_n % 200 == 0:
                                        print("[SUPERVISOR] HAYALET KAPISI "
                                              "(DONUK): kutu %d karedir %.1f px "
                                              "icinde HIC degismedi (%.1fx%.1f) "
                                              "-> tespit SAYILMADI [toplam %d]"
                                              % (len(donuk_gec), _e, _w, _h,
                                                 donuk_n))

                # ── KOPMA TAKSONOMISI ICIN SALT GOZLEM (2026-08-17) ────────
                # Karar logu bugune kadar yalniz `gorulen` yaziyordu; BOYUT ile
                # HAYALET kapisi birbirinden AYRILAMIYORDU (arac/algi_sureklilik
                # menzil modeliyle tahmin etmek zorunda kaldi). Bu alanlar
                # ayrimi OLCULEBILIR yapar. Hicbir karari etkilemez.
                _lw = (pose or {}).get("w")
                _lh = (pose or {}).get("h")
                _lcx = (pose or {}).get("cx")
                _lcy = (pose or {}).get("cy")
                if pose is None:
                    _eleme = "KUTU_YOK"
                elif (pose.get("conf") or 0.0) < sup_cfg.POSE_CONF_MIN:
                    _eleme = "CONF_DUSUK"
                elif _hayalet_bu:
                    _eleme = "HAYALET"
                elif not boyut_ok:
                    _eleme = "BOYUT"
                elif not gorulen:
                    _eleme = "DIGER"
                else:
                    _eleme = ""

                # ── ARDIŞIK TESPİT SAYACI (2026-08-15, şartname) ──────────
                # "Tespit modeli hedefi üst üste 10 karede tespit ederse görsel
                # güdüme geçilmeli." wait_pose(son_seq) her turda YENİ bir
                # dedektör karesi bekler (seq artışı), yani burada saymak
                # gerçekten ARDIŞIK KARE saymaktır -- supervisor tik'i değil.
                # Tek kötü kare sayacı SIFIRLAR (şartname "üst üste" diyor).
                if gorulen:
                    ardisik_gor += 1
                else:
                    ardisik_gor = 0

                # ── KESINTISIZ KILIT SAYACI (2026-08-17) ──────────────────
                # Kilit tanimi (kesintisiz_kilit.py sozlesmesi): GERCEK tespit,
                # conf >= AVCI_KILIT_CONF, kutu gecerli, hedef KADRAJDA.
                # Hayalet kapisinin eledigi kare "hayalet" olarak beslenir ->
                # kilide SAYILMAZ (kullanici sarti: "gercek tespit, hayalet DEGIL").
                # SALT OLCUM: kapi kapaliyken (AVCI_KILIT_S=0) hicbir karar
                # bu sayaca bakmaz, davranis bit-ayni kalir.
                # ⚠ HAM `pose` beslenir, `gorulen` DEGIL: BOYUT kapisi (hedef
                # uzak) kilit tanimina girmez — kullanici tanimi yalniz
                # "gercek tespit + conf + kadrajda" diyor. Sayac kendi
                # conf/kadraj kapilarini uygular (kesintisiz_kilit.py).
                _kk_t = kayit.get("t") or time.monotonic()
                kk.guncelle(None if _hayalet_bu else pose, _kk_t,
                            hayalet=_hayalet_bu)
                _kilit_ok = kk.gecti()
                status["kesintisiz_kilit_s"] = round(kk.sure, 2)

                # ⚠ 2026-08-14 CANLI OKUMA (yakalanan hata):
                # Mod eskiden dongu basinda BIR KEZ okunup closure'a kapaniyordu.
                # Arayuz "Görsel Güdüm"e basildiginda gorev ZATEN baslamis
                # oluyordu -> calisan izci hala OTO olcutunu (10 ardisik kare
                # ~0.3 s) kullaniyordu ve ilk tespitte devrediyordu.
                # Kanit (14 Agu logu): "zorla modu -> GORSEL" yazdiktan SONRA
                # supervisor "GPS fazı (görsel kilit: 10 ARDIŞIK kare)" basti.
                # Artik HER KAREDE tazeden okunuyor.
                _z = (getattr(sup_cfg, "ZORLA_MOD", None) or "OTO").upper()

                # ── GORSEL modu: olcut = SARTNAME KILIT SAYACI ──────────────
                # Arayuzdeki "X.X / 5.0 s" ile BIREBIR ayni sayac (bkz.
                # modul basindaki kilit_kaynagi aciklamasi).
                if _z == "GORSEL":
                    kd = None
                    try:
                        if kilit_kaynagi is not None:
                            kd = kilit_kaynagi()
                    except Exception:
                        kd = None
                    if kd is None:
                        # Kanca yoksa devretme -- sessizce yanlis olcutle
                        # devretmektense GPS'te kalmak yeglenir. Bir kez uyar.
                        if not tetik.get("_uyari"):
                            tetik["_uyari"] = True
                            print("[SUPERVISOR] !! kilit kaynagi bagli DEGIL -> "
                                  "GORSEL devri yapilamiyor (GPS'te kalinacak)")
                        continue
                    kilit_s = float(kd.get("sure") or 0.0)
                    status["kilit_sayac"] = round(kilit_s, 2)
                    status["kilit_sure_s"] = round(kilit_s, 2)
                    _boyut = kd.get("boyut_pct")
                    _esik = kd.get("esik_pct")

                    # ── GEOMETRI KAPISI: yandan gecmede DEVRETME ──────────
                    # Kilit dolsa bile hedef YANDAN geciyorsa gorsel faz
                    # kacinilmaz olarak iska ile biter (bkz. DEVIR_ASPECT_MAX
                    # aciklamasi). Arkasina dusene kadar GPS'te kal.
                    _asp = _ga.status.get("aspect_deg")
                    _omt = _ga.status.get("omega_term_deg")
                    status["aspect_deg"] = _asp
                    status["omega_term_deg"] = _omt
                    _geo_ok = (sup_cfg.DEVIR_ASPECT_MAX >= 999.0
                               or _asp is None
                               or _asp <= sup_cfg.DEVIR_ASPECT_MAX)
                    # DUZ KISIM: hedefin KENDI donus hizi kucukse devret
                    _hdon = _ga.status.get("hedef_donus_deg")
                    status["hedef_donus_deg"] = _hdon
                    _duz_ok = (sup_cfg.DEVIR_DONUS_MAX >= 999.0
                               or _hdon is None
                               or abs(_hdon) <= sup_cfg.DEVIR_DONUS_MAX)
                    _geo_ok = _geo_ok and _duz_ok
                    # ── SINIRLI BEKLEME: kapi ENGELLEMEZ, GECIKTIRIR ──────
                    #   10 kare dolduysa ve geometri kotuyse sayaci baslat;
                    #   BEKLE_MAX_S dolunca sartname geregi YINE devret.
                    if sup_cfg.DEVIR_BEKLE_MAX_S > 0.0:
                        if _geo_ok:
                            tetik["_geo_bekle_t0"] = None
                        else:
                            if tetik.get("_geo_bekle_t0") is None:
                                tetik["_geo_bekle_t0"] = time.monotonic()
                            _gec = time.monotonic() - tetik["_geo_bekle_t0"]
                            if _gec >= sup_cfg.DEVIR_BEKLE_MAX_S:
                                _geo_ok = True          # sure doldu -> devret
                                if not tetik.get("_geo_sure_bilgi"):
                                    tetik["_geo_sure_bilgi"] = True
                                    print("[SUPERVISOR] DEVIR BEKLEME %.1f s doldu "
                                          "-> sartname geregi devrediliyor "
                                          "(geometri hala kotu)"
                                          % sup_cfg.DEVIR_BEKLE_MAX_S)
                            status["devir_bekle_s"] = round(_gec, 2)
                    if not _geo_ok and not tetik.get("_geo_bilgi"):
                        tetik["_geo_bilgi"] = True
                        print("[SUPERVISOR] GEOMETRI KAPISI: aspect %.0f° > %.0f° "
                              "(yandan gecis) -> kilit dolsa da devredilmiyor, "
                              "hedefin arkasina dusuluyor"
                              % (_asp, sup_cfg.DEVIR_ASPECT_MAX))
                    if _geo_ok:
                        tetik["_geo_bilgi"] = False

                    # ── ŞARTNAME ÖLÇÜTÜ: ÜST ÜSTE 10 KARE TESPİT ──────────
                    # Birincil kural budur. KILIT_SURE_S (süre kilidi) ve
                    # geometri kapısı EK şartlardır; ikisi de varsayılan
                    # KAPALI, çünkü şartname "10 kare tespit ederse GEÇMELİDİR"
                    # diyor ve ek şart koymak bunu ihlal ederdi.
                    _sure_ok = (sup_cfg.KILIT_SURE_S <= 0.0
                                or kilit_s >= sup_cfg.KILIT_SURE_S)
                    _kare_ok = ardisik_gor >= sup_cfg.KILIT_N
                    # BOYUT "devir" modu: kapi kare-gecerliliginden cikti, menzil
                    # kisitini BURADA uygular (davranis "kare" modunda BIT-AYNI,
                    # cunku orada zaten gorulen=False olmustu).
                    _boyut_ok = ((sup_cfg.DEVIR_BOYUT_MOD != "devir")
                                 or ardisik_boyut >= max(1, sup_cfg.DEVIR_BOYUT_N))
                    # ⚠ `kilit_s` KUMULATIF'tir (10 s pencerede toplam) —
                    # KESINTISIZ degil. Gercek kesintisiz sart AVCI_KILIT_S
                    # ile gelir; kapali (0) iken _kilit_ok her zaman True.
                    _devret = (_kare_ok and _sure_ok and _geo_ok and _kilit_ok
                               and _boyut_ok)

                    # NEDEN devredilmiyor? En kısıtlayıcı şartı yaz.
                    if not _boyut_ok:
                        _sebep = ("boyut kapisi (devir modu): kutu < %.0f px "
                                  "-> hedef UZAK" % sup_cfg.DEVIR_BOYUT_PX)
                    elif not _kilit_ok:
                        _sebep = ("kesintisiz kilit %.2f/%.1f s"
                                  % (kk.sure, KilitKapiCfg.ESIK_S))
                    elif not _kare_ok:
                        _sebep = ("ardisik tespit %d/%d"
                                  % (ardisik_gor, sup_cfg.KILIT_N))
                    elif not _duz_ok:
                        _sebep = ("duz kisim kapisi: hedef %.0f °/s doniyor "
                                  "(> %.0f) -> duz kismi bekle"
                                  % (abs(_hdon), sup_cfg.DEVIR_DONUS_MAX))
                    elif not _geo_ok:
                        _sebep = ("geometri kapisi: aspect %.0f° > %.0f° (yandan gecis)"
                                  % (_asp, sup_cfg.DEVIR_ASPECT_MAX))
                    elif not _sure_ok:
                        _sebep = "sure kilidi %.1f/%.1f s" % (kilit_s, sup_cfg.KILIT_SURE_S)
                    else:
                        _sebep = "ardisik %d kare tespit -> DEVRET" % ardisik_gor
                    status["ardisik_gor"] = ardisik_gor
                    karar_log.yaz(mod="GORSEL", faz="GPS", gorulen=gorulen,
                                  conf=(pose or {}).get("conf"),
                                  kilit_s=kilit_s, esik_s=sup_cfg.KILIT_SURE_S,
                                  boyut_pct=_boyut, esik_pct=_esik,
                                  merkez_av=("icinde" if kd.get("anlik") else "disinda"),
                                  d_h=_ga.status.get("d_h"),
                                  karar=("DEVRET" if _devret else "BEKLE"),
                                  sebep=_sebep,
                                  w=_lw, h=_lh, cx=_lcx, cy=_lcy,
                                  eleme=_eleme, kilit_kes_s=kk.sure,
                                  u_truth=_ga.status.get("u_px_truth"),
                                  v_truth=_ga.status.get("v_px_truth"))
                    if _devret:
                        print("[SUPERVISOR] UST USTE %d KARE TESPIT (sartname) "
                              "-> gorsel faza devrediliyor  [mesafe %s m, "
                              "aspect %s°, terminal w %s°/s, KESINTISIZ KILIT "
                              "%.2f s]"
                              % (ardisik_gor,
                                 _s(_ga.status.get("d_h"), 1) or "?",
                                 ("%.0f" % _asp) if _asp is not None else "?",
                                 ("%.0f" % _omt) if _omt is not None else "?",
                                 kk.sure))
                        kilit_denetim.yaz(
                            "GPS_VISUAL", kk,
                            "GORSEL: ardisik>=%d & kumulatif>=%.1fs%s"
                            % (sup_cfg.KILIT_N, sup_cfg.KILIT_SURE_S,
                               (" & kesintisiz>=%.1fs" % KilitKapiCfg.ESIK_S)
                               if KilitKapiCfg.acik() else ""),
                            {"menzil_m": _ga.status.get("d_h"),
                             "not": "kumulatif_kilit_s=%.2f ardisik=%d"
                                    % (kilit_s, ardisik_gor)})
                        ardisik_gor = 0
                        # Sayaci SIFIRLA: yoksa gorsel faz olup GPS'e donunce
                        # penceredeki eski 5 s aninda SAHTE devir tetikliyor.
                        try:
                            if kilit_sifirla is not None:
                                kilit_sifirla()
                        except Exception:
                            pass
                        tetik["gorsel"] = True
                        faz_stop.set()
                        return
                    continue                 # GORSEL modunda kare sayaci kullanilmaz

                if sup_cfg.KILIT_ARDISIK:
                    # D0: ARDIŞIK sayım — tek bir tespitsiz kare sayacı sıfırlar
                    ardisik = (ardisik + 1) if gorulen else 0
                    sayac = ardisik
                else:
                    pencere.append(gorulen)
                    sayac = sum(pencere)      # eski: kayan pencere
                status["kilit_sayac"] = sayac
                # OTO / ZORLA-GPS modlarinda da HER kareyi logla (kullanici
                # istegi: "neden oyle yaptigini full logla"). Boylece mod ne
                # olursa olsun kayit var; GORSEL kolu yukarida ayrica yaziyor.
                karar_log.yaz(mod=_z, faz="GPS", gorulen=gorulen,
                              conf=(pose or {}).get("conf"),
                              kilit_s=sayac, esik_s=sup_cfg.KILIT_N,
                              d_h=_ga.status.get("d_h"),
                              karar=("DEVRET" if (sayac >= sup_cfg.KILIT_N
                                                  and _kilit_ok
                                                  and _z != "GPS") else "BEKLE"),
                              sebep=("ZORLA GPS: devir kapali" if _z == "GPS"
                                     else (("kesintisiz kilit %.2f/%.1f s"
                                            % (kk.sure, KilitKapiCfg.ESIK_S))
                                           if (sayac >= sup_cfg.KILIT_N
                                               and not _kilit_ok)
                                           else ("%d/%d ardisik kare"
                                                 % (sayac, sup_cfg.KILIT_N)))),
                              w=_lw, h=_lh, cx=_lcx, cy=_lcy,
                              eleme=_eleme, kilit_kes_s=kk.sure,
                              u_truth=_ga.status.get("u_px_truth"),
                              v_truth=_ga.status.get("v_px_truth"))
                if sayac >= sup_cfg.KILIT_N:
                    d_h = _ga.status.get("d_h")
                    yakin = (d_h is not None and d_h < sup_cfg.GATE_MENZIL)
                    dropout = _ga.status.get("durum") == "DROPOUT"  # jamming fallback
                    kapi = (not sup_cfg.GATE_KILIT) or yakin or dropout
                    if _z == "GPS":
                        kapi = False        # ZORLA GPS: gorsel faza asla gecme
                    # BOYUT "devir" modu: kapi kare-gecerliliginden cikarildi ->
                    # menzil kisitini BURADA uygular. "kare" modunda (varsayilan)
                    # boyut_ok zaten gorulen'i sifirlamisti -> BIT-AYNI.
                    if (sup_cfg.DEVIR_BOYUT_MOD == "devir"
                            and ardisik_boyut < max(1, sup_cfg.DEVIR_BOYUT_N)):
                        kapi = False
                    # ── KESINTISIZ KILIT KAPISI (2026-08-17) ──────────────
                    # ⚠ ETKIN KOL BURASI: olculen 62 karar logunda mod %100
                    # "OTO" -> yukaridaki GORSEL kolu HIC calismiyor. `sayac`
                    # 10 ARDISIK KARE'dir ve olculen 20.0 fps'te yalnizca
                    # 0.45-0.51 SANIYE eder. 5 s sartini uygulayan tek yer bu
                    # kapidir. AVCI_KILIT_S=0 -> _kilit_ok her zaman True,
                    # davranis BIT-AYNI.
                    if not _kilit_ok:
                        kapi = False
                    if kapi:
                        kilit_denetim.yaz(
                            "GPS_VISUAL", kk,
                            "OTO: ardisik_kare>=%d%s"
                            % (sup_cfg.KILIT_N,
                               (" & kesintisiz>=%.1fs" % KilitKapiCfg.ESIK_S)
                               if KilitKapiCfg.acik() else ""),
                            {"menzil_m": d_h,
                             "not": "ardisik=%d fps_esdeger_s=%s"
                                    % (sayac, _s(kk.sure, 2))})
                        tetik["gorsel"] = True
                        faz_stop.set()          # gps_guidance döngüsünü kır
                        return

        threading.Thread(target=izci, daemon=True).start()
        if _zorla == "GPS":
            print("[SUPERVISOR] GPS fazı — ZORLA GPS: görsel faza geçilmeyecek")
        elif _zorla == "GORSEL":
            print(f"[SUPERVISOR] GPS fazı — kilit {sup_cfg.KILIT_SURE_S:.1f} s "
                  f"KESİNTİSİZ dolunca görsel faza devredilecek "
                  f"(kaçırırsa GPS'e geri döner)")
        else:
            print(f"[SUPERVISOR] GPS fazı (görsel kilit: {sup_cfg.KILIT_N} {'ARDIŞIK' if sup_cfg.KILIT_ARDISIK else '/15 kayan'} kare, conf≥{sup_cfg.POSE_CONF_MIN:.2f}"
                  f"{' + handoff/DROPOUT kapısı' if sup_cfg.GATE_KILIT else ''}"
                  f"{f' + KESİNTİSİZ KİLİT ≥{KilitKapiCfg.ESIK_S:.1f} s' if KilitKapiCfg.acik() else ''})")
        if _dow_amir is not None:
            _dow_amir.gps_fazi(conn, get_plane, get_iris, faz_stop)
        else:
            run_gps_guidance(conn, get_plane, get_iris, faz_stop)

        if stop_event.is_set() or not tetik["gorsel"]:
            break

        # ══ GÖRSEL FAZ ══ (temas kesilene ya da stop'a kadar)
        status["faz"] = "VISUAL"
        status["gecis_sayisi"] += 1
        print(f"[SUPERVISOR] ✓ GÖRSEL TEMAS — görsel güdüme geçildi "
              f"(geçiş #{status['gecis_sayisi']}, yasa={_GORSEL_YASA.upper()})")
        if _GORSEL_YASA == "bbox":
            # bbox IBVS — CANLI GPS girmez (yarışma kuralı D0).
            # get_plane_truth/get_menzil/get_gercek KASITEN geçilmez.
            #
            # DONDURULMUŞ TAŞIYICI: hedefin son GPS hız kestirimi BURADA, yani
            # görsel faz BAŞLAMADAN önce bir kez okunur ve sayı olarak geçilir.
            # Görsel döngü canlı GPS'e erişemez (callback değil, üçlü sayı).
            ff = (_ga.status.get("tgt_vx") or 0.0,
                  _ga.status.get("tgt_vy") or 0.0,
                  _ga.status.get("tgt_vz") or 0.0)
            print(f"[SUPERVISOR] taşıyıcı donduruldu: "
                  f"({ff[0]:+.1f},{ff[1]:+.1f},{ff[2]:+.1f}) m/s "
                  f"— görsel faz boyunca GPS'e bir daha bakılmayacak")
            # get_temas: Talon çarpma sensörü — SONUÇ sinyali (vuruş kararı),
            # güdüm girdisi değil; hedefin yerini/hızını taşımaz.
            # KESINTISIZ KILIT DEVRI (2026-08-17): kilit GPS fazinda birikti;
            # faz degisince SIFIRLANMAMALI, yoksa terminal kapisi devirden
            # sonra bastan 5 s beklerdi ve toplam sart 10 s'ye cikardi.
            # kilit_t0 = kilidin BASLADIGI monoton an (kilit yoksa None).
            _kk = tetik.get("kk")
            if _dow_amir is not None:
                sebep = _dow_amir.gorsel_fazi(
                    conn, get_iris, wait_pose, stop_event,
                    kayip_kare_esik=sup_cfg.KAYIP_M, get_temas=get_temas)
            else:
                sebep = run_bbox_ibvs(conn, get_iris, wait_pose, stop_event,
                                      cfg=IbvsCfg, kayip_kare_esik=sup_cfg.KAYIP_M,
                                      ff_hiz=ff, get_temas=get_temas,
                                      kilit_t0=(_kk.devret_t0() if _kk else None))
        else:
            sebep = run_visual_lead(conn, wait_pose, get_plane_truth, stop_event,
                                    cfg=lead_cfg, kayip_kare_esik=sup_cfg.KAYIP_M,
                                    get_temas=get_temas, get_menzil=get_menzil,
                                    get_gercek=get_gercek)
        status["son_sebep"] = sebep
        if sebep == "vuruldu":
            status["faz"] = "VURULDU"
            print("[SUPERVISOR] ✓✓ HEDEF VURULDU — görev tamamlandı.")
            return
        if sebep == "kayip":
            # Kacirirsa GPS'e geri don (kullanici istegi 2026-08-14) -- repodaki
            # ozgun davranis. Bir onceki denememde "GORSEL'de GPS'e donme" diye
            # bir kural eklemistim; hedef kadrajdan cikinca droneu geri getirecek
            # hicbir sey kalmadigi icin savruluyordu (20 gecis, mesafe 333 m'ye
            # firladi). O kural KALDIRILDI.
            print("[SUPERVISOR] Görsel temas kesildi → GPS fazına dönülüyor")
            continue
        break                                    # durduruldu

    status["faz"] = "DURDU"
    print("[SUPERVISOR] Hibrit güdüm sonlandı.")

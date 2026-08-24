"""
gps_guidance.py — GPS güdümü (sıfırdan yeniden inşa, görsel-temas odaklı).

AMAÇ (başarı kriteri): Drone'u öyle konumlandır ki hedef sabit-kanatlı İHA
kameranın TAM ORTASINDA, pose modelinin güvenilir çalıştığı menzil bandında
(~10-11 m) ve KARARLI görünsün → supervisor görsel faza devretsin. (Vuruş DEĞİL;
vuruş görsel fazın işi.)

Kadraj merkezi ⇔ gövde-çerçevesinde hedefe bakış: azimut=0, yükseliş=+25°
(kamera tilt'i). Bu hata GPS + drone attitude'undan kapalı formda ölçülür
(guidance_core.hedef_kadraj_hatasi) ve her kare CSV'ye yazılır → merkezleme
başarısı ölçülebilir.

KADEME 1 (bu sürüm): GEOMETRİK kadraj-noktası takibi. Hedefin hız yönünün
D_BEHIND gerisine + D_BELOW altına (slant RANGE_SET'te +25° yükseliş verecek)
bir istasyon kur; oraya PD hız + hedef-hızı feedforward ile git (feedforward →
kilitlenince kararlı hold). Burun daima gerçek hedefe döner (yaw). Drone hedefin
ALTINDA kalır → gökyüzü arka planı, pose kopmaz.

KADEME 2 (2026-08-06): istasyonun LOS yükselişi artık GÖVDE PİTCH'İNDEN
dinamik türetilir (elev = kamera tilt + pitch) — kamera gövdeye vidalı olduğu
için sabit açı hedefi kadrajda sabit tutamıyordu (daire tutuşunda burun +11°
yukarı → hedef merkezin 20-28° altına düşüyordu). Bkz. Cfg.ELEV_DINAMIK.

Arayüz (supervisor / gcs_server ile aynı sözleşme):
  run_gps_guidance(conn, get_plane, get_iris, stop_event, cfg=Cfg)
    get_plane() -> {x,y,z,yaw,frozen}                (m, NED; GPS-gürültülü hedef)
    get_iris()  -> {x,y,z, roll,pitch,yaw, vx,vy,vz} (m/rad; kendi poz + attitude)
  status["d_h"], status["durum"] supervisor.izci tarafından okunur (DROPOUT dahil).
"""

import csv
import math
import os
import time

from control.guidance.common import (
    clamp, normalize_angle, limit_acceleration, limit_acceleration_split,
    send_velocity,
)
from control.guidance.guidance_core import hedef_kadraj_hatasi
from control.guidance.kurtarma import Kurtarma


def _env_f(name, default):
    return float(os.environ.get(name, default))


class Cfg:
    LOOP_HZ = 20.0

    # --- KADRAJ GEOMETRİSİ (merkezleme) ---
    CENTER_ELEV_DEG = 25.0    # kamera tilt'i (FİZİKSEL, iris_cam modelinden).
                              # Hedefin kadrajın TAM MERKEZİNDE görünmesi için
                              # gereken LOS yükselişi. Ölçüm/tanı referansı;
                              # istasyon geometrisini ARTIK BELİRLEMİYOR.
    # RANGE_SET 11 → 8 (2026-08-08, C1 ikinci hamle, UÇUŞTA DOĞRULANDI):
    #     düz uçuş : 13-14 → 11.7 m (oturmuş p10 11.2 / p90 12.1 — kararlı)
    #     dönüşler : 15.1 → 13.3 m (aynı segmentasyonla, kontrol log 121248)
    # Eski "11→5 denendi, hiç etki yok" bulgusu bu değişikliğe engel DEĞİL:
    # o ölçüm menzil >16 m'de komut V_MAX'a doygunken alınmıştı; artık 12-15 m
    # bandında lineer bölgedeyiz ve istasyonun yeri birebir menzile yansıyor.
    # 11'in kökeni pose modelinin tatlı noktasıydı (pose artık devre dışı).
    RANGE_SET = _env_f("AVCI_GPS_RANGE", 8.0)    # m; slant menzil setpoint

    # İSTASYONUN LOS yükselişi — kamera tilt'inden AYRILDI (2026-08-02).
    #
    # NEDEN AYRILDI: ikisi tek sayıya bağlıydı (25°), dolayısıyla istasyon
    # RANGE_SET·sin25° = 4.65 m ALTTA kuruluyordu. Terminal hücum bu 4.65 m'yi
    # kapatmak zorunda ve ÖLÇÜLDÜ (3 uçuş, kara kutu): ArduPilot dikey hız
    # komutunu WP_ACC_Z = 1.0 m/s² ile rampalıyor — güdüm 8-22 m/s tırmanma
    # istese de. Sıfırdan 4.65 m kapatmak 3.05 s sürer; terminalde eldeki süre
    # 2.4-2.8 s. Yani geometri, aracın dikey ivme bütçesine SIĞMIYORDU:
    #     vurdu   → kalan dikey +0.03 m   (rampayı erken başlatabildiği için)
    #     ıskaladı→ kalan dikey +1.52 m, +2.06 m  (drone hedefin ALTINDAN geçti)
    #
    # 15°'de istasyon RANGE_SET·sin15° = 2.85 m altta, 10.63 m geride:
    #     eldeki süre 10.63 / 3.7 m/s ≈ 2.87 s → 1 m/s² ile 4.13 m tırmanılır
    #     gereken 2.85 m → %45 pay. En hızlı ölçülen kapanmada (4.3 m/s) bile
    #     2.47 s → 3.05 m, yine yeter.
    # BEDELİ: hedef kadraj merkezinde değil, ~10° altında görünür
    # (v_px ≈ 269/480 — hâlâ rahat içeride). G11 bütçeyi test olarak koruyor.
    #
    # ⚠ BU AYRIM HENÜZ KESİNLEŞMEDİ — bkz. UYGULANACAK.md B7.
    # 25° tesadüf değildi, kamera tilt'i o; istasyon 25°'de kurulunca hedef
    # kadrajın TAM MERKEZİNDE oluyordu. Ölçüm 15°'yi destekliyor (terminal
    # `ok` oranı %8.7 → %18.2, kadraj içi %59.8 → %67.0, en yakın menzil
    # medyanı 5.25 → 1.73 m) AMA bu kanıt karışık: algının iyileşmesi büyük
    # ölçüde geometrinin SONUCU (drone seviyeye yakın kalınca hedef kadrajdan
    # geç çıkıyor). Merkez dışı kadrajlamanın KENDİ bedeli izole ölçülmedi.
    #
    # İki şey denenmedi:
    #   (1) 15° taranarak seçilmedi, ivme bütçesi hesabından çıktı — bütçeye
    #       sığan en büyük açı (18°? 20°?) merkeze daha yakın olurdu.
    #   (2) Asıl alternatif: istasyonu 25°'de bırakıp WP_ACC_Z'yi 1.0 → 2.5
    #       yükseltmek. Tutarsa bu ayrım gereksiz hale gelir.
    ISTASYON_ELEV_DEG = _env_f("AVCI_GPS_ISTASYON_ELEV", 15.0)

    # ── DİNAMİK İSTASYON YÜKSELİŞİ (2026-08-06, kullanıcı fikri) ──
    #
    # SORUN: sabit yükseliş açısı hedefi kadrajda sabit TUTMUYOR — kamera
    # gövdeye vidalı (25° yukarı) ve gövdenin duruşu uçuş rejimiyle değişiyor.
    # 8 uçuşun logundan ölçüldü (kadraj_pitch_hata_deg; 0 = dikey merkez):
    #     düz kovalama : pitch ≈ 0°               → hedef merkezin ~10° altında
    #     daire tutuşu : pitch +11° BURUN YUKARI  → hedef merkezin 20-28° altında
    #                    (v_px 300-330/480; dikey yarı-FOV 55° — yarı yolda)
    #
    # Burun-yukarının nedeni FPV sezgisindeki "hızlanınca öne eğilme" DEĞİL
    # (simde sürükleme küçük; düz kovalamada 12 m/s'de pitch ~0). Dairede burun
    # hedefte ama hız teğet: drone 26-37° YENGEÇ uçuyor ve merkezcil yatma
    # gövde ekseninde "geriye" bileşen kazanıyor → burun yukarı. Ölçüm
    # (163801 uçuşu): yengeç>20° diliminde pitch +10.9° / roll +18.4°,
    # yengeç<10° diliminde +1.1° / +0.8° — hızlar neredeyse aynı (9.8 vs 12.2).
    # Yani pitch'i HIZ değil GEOMETRİ belirliyor. Teorik kestirim de tutuyor:
    # istasyon geometrisinden yengeç 37°, merkezcil 3.1 m/s² → +10.6° beklenir.
    #
    # ÇÖZÜM: yükseliş gövde pitch'inden türetilir (hedef kadraj merkezi şartı):
    #     elev = CENTER_ELEV_DEG + pitch_EMA,  [ELEV_DIN_MIN, ELEV_DIN_MAX]
    # Roll ihmalinin kalıntısı ~2° (roll 18°'de). Girdi HIZ DEĞİL ölçülü pitch:
    # hız→pitch bağı loglarda yok, pitch ise ATTITUDE'dan hazır geliyor.
    # EMA (τ≈1 s): ivme geçicileri istasyonu sallamasın.
    #
    # Beklenen denge: düzde ~25° (alt 2.85→4.65 m), dairede ~36° (alt ~6.5 m).
    # Eski 15°'nin gerekçesi dikey ivme bütçesiydi (1.0 m/s² ölçümü) — o ölçüm
    # PARAM ADI DÜZELTMESİNDEN ÖNCE: 1.0, Copter'ın WPNAV_ACCEL_Z varsayılanı
    # (100 cm/s²). avci_copter.parm artık 250 yazıyor (2.5 m/s²) → 25°'nin
    # 4.65 m'si bütçeye yeniden sığar (2.32 s'de 6.7 m tırmanılabilir). Yani
    # ISTASYON_ELEV_DEG yorumundaki "(2) asıl alternatif" fiilen gerçekleşti;
    # G11 testi statik taban geometrisini korumaya devam ediyor.
    #
    # Kapatmak için: AVCI_GPS_ELEV_DIN=0 → sabit ISTASYON_ELEV_DEG (eski yol).
    ELEV_DINAMIK = _env_f("AVCI_GPS_ELEV_DIN", 1.0) >= 0.5
    ELEV_DIN_MIN = 5.0        # °; sert ileri ivmede (burun aşağı) taban
    ELEV_DIN_MAX = 40.0       # °; dairede gereken ~36° içeride kalsın
    ELEV_PITCH_EMA = 0.05     # tick başına; 20 Hz'de τ ≈ 1 s
    TRACK_MIN_SPD = 3.0       # m/s; üstünde istasyon HIZ yönünün gerisi (kuyruk), altında LOS gerisi
    LOOKUP_MIN_ALT = 8.0      # m; alçalma tabanı (yere çakılma koruması)

    # --- HIZ KONTROLÜ ---
    KP_H = _env_f("AVCI_GPS_KP", 0.8)   # yatay konum hatası → hız (1/s)

    # KD_H — bu terim SÖNÜMLEME DEĞİL, LEAD'in kendisidir (2026-08-05 bulgusu).
    # de[] istasyon hatasının türevidir, yani ≈ göreli hız Δv. Yasa açılınca:
    #     v_cmd = v_hedef + KP_H·Δp + KD_H·Δv
    # FRPN'in hız formu da aynı üç terimli yapıda; oradaki karşılığı K_ZEM.
    # Yani "hedefin gideceği yere nişan alma" miktarını bu katsayı belirliyor:
    # küçükse hedefin izini birebir tekrarlarsın, büyükse aşıp salınırsın.
    # Denge analizi: Δv_yeni⊥ = −K·Δv_eski⊥ → K=1 söndürmez, salındırır.
    # F3 taraması (tools/frpn_replay.py --tara) 0.60'ı buldu.
    #
    # UÇUŞTA DOĞRULANDI → VARSAYILAN 0.20'DEN 0.60'A ÇEKİLDİ (2026-08-05).
    # Aynı senaryoda (daire, hedef 14.4-14.6 m/s, dönüş 21.4-21.9°/s), görev
    # başından hizalanmış 30 s'lik dilimlerde oturmuş menzil:
    #     KD_H=0.20 → 34.3 m      KD_H=0.60 → 29.4 m      (FRPN → 31.1 m)
    # Üç koşu da 150 s boyunca ±0.3 m içinde kararlı kaldı, yani fark gürültü
    # değil. Eskisine dönmek için: AVCI_GPS_KD=0.2
    KD_H = _env_f("AVCI_GPS_KD", 0.60)

    # ── İÇ DAİRE NİŞANI (2026-08-05) ──
    # SORUN: istasyon "hedefin hız yönünün gerisi"ne konuyor. Hedef daire
    # çizerken o nokta hedefin KENDİ ÇEMBERİNİN ÜZERİNDEDİR. Drone onu
    # kovaladığı sürece aynı yarıçapta uçmak zorunda, dolayısıyla aynı hıza
    # muhtaç. Ölçüldü (2026-08-05, 6 koşu): drone yarıçapı 38 m = hedef
    # yarıçapı 38 m, menzil 29-34 m'de donuyor.
    #
    # Dairesel kovalamacada zorunlu bağ:  yarıçap = hız / açısal_hız
    # Hedefin açısal hızı sabit olduğuna göre drone'u HIZLANDIRMAK çemberini
    # BÜYÜTÜR. Bu deneyle doğrulandı: V_MAX 18→24 yapılınca drone yarıçapı
    # 38→43 m'ye çıktı ve menzil 29→35-41 m'ye AÇILDI. Yani güç eklemek
    # ters teptik.
    #
    # ÇÖZÜM: istasyonu dönüşün İÇİNE kaydır. Drone daha küçük yarıçapta,
    # DAHA AZ hızla aynı açısal hızı tutturur ve hedefe yaklaşır:
    #     34 m yarıçap → 12.8 m/s gerekir → hedefe ~4 m
    #     30 m yarıçap → 11.3 m/s gerekir → hedefe ~8 m
    # Drone zaten 13-15 m/s yapabiliyor; ekstra güce ihtiyaç YOK.
    #
    # Kayma yönü = merkezcil ivme yönü = hız vektörünün dönüş yönünde 90°'si.
    # Hedef DÜZ uçarken açısal hız ~0 olur ve kayma kendiliğinden sıfırlanır —
    # düz kovalama durumunda regresyon riski yok (kritik: en iyi bilinen
    # sonucumuz bu yolda bozulmamalı).
    #
    # UÇUŞTA ÖLÇÜLDÜ (2026-08-05, aynı senaryoda üç koşu):
    #     kayma   menzil(medyan)  en yakın   drone R − hedef R
    #       0 m       34.1 m        31.3 m        +2 m  (aynı çember)
    #       8 m       22.8 m         6.9 m        −7 m  (İÇERİDE)
    #      14 m        9.8 m         3.2 m       −11 m  (İÇERİDE)
    # Mekanizma doğrulandı: drone artık hedefin çemberinin İÇİNDE uçuyor.
    # 34.1 → 9.8 m; GPS fazının hedefi (görsel faza devredilebilir konum)
    # fazlasıyla tutturuldu. Kayma başına kazanç 8→14 aralığında artıyor
    # (1.41 → 2.17 m/m), yani eğri henüz doymamış; 14 yeter görüldüğü için
    # daha ileri gidilmedi — GPS fazının işi çarpmak değil devretmek.
    # ⚠ Bu SABİT METRE bir kaymadır. Çok dar dairede (uçağın yapabileceği en
    # dar ~24 m yarıçap) fazla içeri iter. Yarıçap-oranlı sürüm sıradaki iş.
    #
    # DÜZ UÇUŞ REGRESYON TESTİ YAPILDI: kare deseninde düz kenarlarda davranış
    # bozulmadı — ölçekleme (ω→0 ⇒ kayma→0) uçuşta da doğrulandı.
    # Kapatmak için: AVCI_GPS_IC=0
    IC_KAYMA = _env_f("AVCI_GPS_IC", 14.0)     # m; dönüş merkezine doğru kayma
    IC_OMEGA_REF = 0.15                        # rad/s; bu dönüş hızında tam kayma
    IC_OMEGA_EMA = 0.15                        # açısal hız kestirimi yumuşatması

    # ── YARIÇAP-ORANLI KAYMA (2026-08-05, sabit-metre sürümünün devamı) ──
    # SABİT METRENİN AÇIĞI: 14 m, bu senaryonun dairesi (hedef R ≈ 52 m) için
    # ölçülmüş doğru değer. Ama hedef DAR bir daire çizerse (uçağın yapabileceği
    # en dar ~24 m yarıçap) aynı 14 m nişanı merkeze fazla yaklaştırır: drone
    # gereğinden içeride uçar, hedefe 14 m kalır — oysa oranlı olsa ~6 m olurdu.
    # Tehlikeli değil ama performans kaybı; ve dar daire yarışmada olası.
    #
    # ÇÖZÜM: kaymayı hedefin DÖNÜŞ YARIÇAPININ oranı yap. Yarıçap zaten
    # elimizde: R = |v_hedef| / |ω|  (ikisini de ölçüyoruz).
    #     kayma = IC_ORAN × R,  IC_KAYMA_MAX ile tavanlı
    #
    # KATSAYI ÖLÇÜMDEN: 2026-08-05 uçuşunda 14 m kayma, hedefin 52.2 m'lik
    # yarıçabının 0.268'iydi → IC_ORAN = 0.27. Böylece bu senaryoda oranlı
    # sürüm sabit sürümle AYNI kaymayı üretir (14.1 m); fark yalnız yarıçap
    # değişince ortaya çıkar — istenen davranış bu.
    #
    # ⚠ TEORİK TAHMİN TUTMADI, ölçüme uyuldu. Geometrik beklenti
    # (1 − v_drone/v_hedef ≈ 0.06) gerçeğin dörtte biriydi; çünkü drone hedefin
    # çemberini birebir izlemiyor ve istasyonun 10.6 m'lik "arka" bileşeni de
    # menzile katkı veriyor. Katsayı teoriden değil uçuştan alınmıştır.
    #
    # VARSAYILAN 0.0 = KAPALI (sabit metre kullanılır). Denemek için:
    #     AVCI_GPS_IC_ORAN=0.27
    IC_ORAN = _env_f("AVCI_GPS_IC_ORAN", 0.0)  # 0 = kapalı, sabit IC_KAYMA geçerli
    IC_KAYMA_MAX = _env_f("AVCI_GPS_IC_MAX", 25.0)   # m; oranlı kaymanın tavanı
    IC_R_MIN = 15.0            # m; bundan dar yarıçap kestirimi güvenilmez sayılır

    # ── DÖNÜŞ İLERİ BESLEMESİ (2026-08-08, C1 birinci hamle) ──
    #
    # SORUN: hız ileri beslemesi HEDEFİN hızını basıyor (v_hedef). Ama istasyon
    # dönüşte hedefle BİRLİKTE DÖNEN bir nokta: hedefin 8.7 m gerisi + 14 m içi.
    # Birlikte dönen noktanın gerçek hızı  v_ist = v_hedef + ω × r  (r = hedef→
    # istasyon). ⌀55 dairede: |ω×r| = 0.28 × 16.5 ≈ 4.6 m/s — istasyonun gerçek
    # hızı ~10.9 m/s iken FF 14.5 basıyordu. Ölçüm bunu doğruluyor: drone dönüş
    # tutuşunda 11.9 m/s uçuyor (2026-08-08, log 121248), yani PD her turda
    # FF'in ~3 m/s'lik yalanını hata terimiyle geri ödüyor → kalıcı teğetsel
    # gecikme (~14 m'nin ana bileşeni).
    #
    # ⚠ BU DAHA ÖNCE DENENDİ VE GERİ ALINDI ("istasyon hızı ileri beslemesi
    # (ω×s)", KARARLI_HAL tablosu). GERİ ALMA GEREKÇESİ: "komut doygun olduğu
    # için etkisi yutuldu" — o dönem menzil >16 m'de komut V_MAX'a doygundu.
    # ŞİMDİ GEÇERSİZ: 15 m'de tutuyoruz ve komut lineer bölgede (dün ölçüldü:
    # drone 11.9 m/s, tavan 18). Gerekçesi ölen ret, ret sayılmaz — yeniden
    # deneniyor, bu kez tek değişken olarak ve otonom uçuşla ölçülerek.
    #
    # Formül ω ile ölçeklendiği için düz uçuşta (ω≈0) kendiliğinden sıfır —
    # en iyi bilinen düz davranış bozulmaz (IC kaymasıyla aynı güvence).
    #
    # ❌ UÇUŞTA ELENDİ (2026-08-08, log 131037, otonom koşu):
    #     FF açık : daire menzil med 23.0 m [p10 22.4, p90 23.7], FF med 6.6 m/s
    #     kontrol : daire menzil med 15.1 m [p10 14.6, p90 17.2]  (log 121248)
    # Formül doğru (G14b sayısal türevle birebir) ve uçuşta aktifti — yani
    # sorun uygulama değil, MEKANİZMA: "doğru" istasyon hızı beslemesi komut
    # hızını düşürüyor (10.9 < 14.5) ve dönen çerçevede aracın hız-takip
    # gecikmesini telafisiz bırakıyor. Eski "yanlış" v_hedef beslemesindeki
    # fazlalık, meğer bu gecikmeyi kazara telafi eden faydalı bir lead'miş.
    # Denge kayması ölçümle uyumlu: Δv/KP ≈ 4.6/0.8 ≈ 6 m dışarı.
    # DERS: FF'i "daha doğru" yapmak tek başına kazanç değil; araç gecikmesi
    # dahil kapalı döngü ölçülmeden değiştirilmez. Varsayılan KAPALI kalacak;
    # yeniden açmayı deneyeceksen yanına araç-gecikmesi telafisi (komut açısını
    # ω·τ kadar öne alma) koymadan deneme.
    FF_DONUS = _env_f("AVCI_GPS_FF_DONUS", 0.0) >= 0.5   # ❌ ölçümle kapalı
    FF_DONUS_MAX = 8.0        # m/s; ω kestirimi sıçrarsa düzeltme tavanı

    # ── ARKA KISALTMA (2026-08-08, C1 üçüncü hamle) ──
    #
    # Dönüşte istasyon = arka bileşen (6.3 m @ elev 38°) + iç kayma (14 m);
    # ikisi DİK vektörler, hedefe yatay uzaklık √(6.3²+14²) = 15.35 m.
    # Ölçülen tutuş 13.3 m ve bunun çoğu istasyonun KENDİ ofseti (C1 tespiti).
    # Arka bileşenin dönüşteki işlevi zayıf: kuyruk görüşü zaten yok (istasyon
    # kuyruk hattından 66° içeride) ve burun/kamera hedefe yaw ile dönük.
    # Bileşeni dönüşte eritmek istasyonu 14.0 m'ye getirir (~1.4 m kazanç);
    # iç kaymanın yeniden ayarına da zemin açar (IC 14, ESKİ arka 10.6 m'yle
    # birlikte ölçülmüştü).
    #
    # Ölçek iç kaymayla AYNI ω rampasında (IC_OMEGA_REF): düz uçuşta arka
    # bileşen TAM kalır (en iyi bilinen düz davranış değişmez), tam dönüşte
    # ARKA_KISALT oranında erir (1.0 = tamamen).
    #
    # ❗ YARIŞMA HATTINDA VARSAYILAN 0 = KAPALI (2026-08-08, kullanıcı kararı
    # + D0 kuralı, bkz. UYGULANACAK.md): yakın yandan eskort (1.0 → daire
    # 5.7 m, log 141740) tespit sürekliliği başlatır ve kural bizi görsel
    # faza ZORLAR; 6 m'de yandan giriş saf bbox takibi için ölümcül (LOS
    # dönüşü 139°/s > yaw tavanı 120°/s). 0 ile dönüş davranışı kararlı
    # profildir: daire 13.3 m, kuyruktan 66° (log 131611) — oradan görsel
    # devir yaşanabilir (~50-60°/s, pure pursuit kuyruğa süzülür).
    # Teknik gimball_gudum branch'inde TAM haliyle arşivli; gimbal takılınca
    # 1.0'a döner (docs/YANDAN_ESKORT_VE_GIMBAL.md).
    ARKA_KISALT = _env_f("AVCI_GPS_ARKA_KISALT", 0.0)   # 0..1; tam dönüşte eriyen pay
    KP_Z = 1.0               # dikey konum hatası → hız (1/s)
    # ⚠ 2026-08-15 OLCULDU: arac 33.7 m/s tirmanabiliyor (tam throttle 3 s'de
    # 60.2 -> 150.7 m). Bu clamp aracin dikey yetkisini 5.6 KAT kisiyor.
    # Kamera tilt hatasi hedefi kadrajin 32 derece YUKARISINDA tutuyor
    # (bkz. DOW_ARAC_PARAMETRELERI); dikey hatayi kapatacak yetki VAR ama
    # bu clamp izin vermiyor.
    VZ_MAX = _env_f("AVCI_VZ_MAX", 6.0)   # m/s; dikey hiz tavani
    # V_MAX 20→28 (2026-07-31): telemetri 4→25 Hz düzeltilince hedefin GERÇEK hızı
    # ortaya çıktı — 18-23 m/s (4 Hz'de EMA sönümlemesi 14-15 gösteriyordu). 20 m/s
    # tavanında komut %98 doygundu: hedef 19-23 giderken drone tavanda kalınca
    # yaklaşma hızı ≈ 0, açı hiç kapanmıyordu. Yüksek hızda eski salınımın sebebi
    # 250 ms telemetri faz gecikmesiydi; 25 Hz ile ~40 ms'e indi.
    # 2026-08-01: 28 → 18. 28 m/s'den MAX_ACCEL=12 m/s² ile durma mesafesi
    # v²/2a = 32.7 m, oysa istasyon standoff'u yalnız 10 m yatay — araç
    # geometrik olarak zamanında yavaşlayamıyor, hedefin etrafında savruluyor.
    # ⚠ TODO: main branch 20.0 kullanıyor — merge sonrası 18 vs 20 karşılaştırma testi yapılacak.
    V_MAX = _env_f("AVCI_GPS_V_MAX", 18.0)   # m/s; yatay hız tavanı

    # ── ILERI BESLEME KORUMASI (2026-08-17 gece) ─────────────────────────
    # FF_KORU=True: hedefin hizini tasiyan ileri besleme (ff) ASLA kirpilmaz;
    # yalniz PD duzeltmesi kalan yetkiye kirpilir. Boylece komut her zaman
    # "hedefin hizi + kucuk bir duzeltme" olur -> arkadan takip, asim yok,
    # ve kurs acisi saf takibe DUSMEZ.
    # KAPANMA_MIN: ff tek basina V_MAX'i doldursa bile birakilan kapanma yetkisi.
    #   hedef 18 m/s, V_MAX 22 -> butce normalde 4 m/s; taban 5 -> 40 m'yi ~8 s.
    # V_MUTLAK_MAX: ff+duzeltme toplaminin sert emniyet tavani.
    FF_KORU = _env_f("AVCI_GPS_FF_KORU", 1.0) >= 0.5
    KAPANMA_MIN = _env_f("AVCI_GPS_KAPANMA_MIN", 5.0)   # m/s

    # ── TERMINAL KAPANMA TABANI (2026-08-19, OLCUMDEN) ───────────────────
    # OLCULDU (3943 ornek, yarisma modu, son 90 dk, donmus satirlar atildi):
    #   menzil 22-30 m -> dr/dt -4.80 m/s | v_LOS 21.1 | v_yanal 4.6
    #   menzil 15-22 m -> dr/dt -4.01     | v_LOS 19.5 | v_yanal 4.7
    #   menzil 10-15 m -> dr/dt -1.92     | v_LOS 15.9 | v_yanal 5.1
    #   menzil  6-10 m -> dr/dt -0.57     | v_LOS  8.9 | v_yanal 7.2   <-- COKUS
    #   menzil  3- 6 m -> dr/dt -1.01     | v_LOS  1.2 | v_yanal 11.8  <-- YANAL
    # Yani 10 m'nin ICINDE komutun neredeyse tamami YANAL oluyor ve kapanma
    # 0.57 m/s'e dusuyor: son 6 metre 10+ saniye suruyor. Hedefin oval pisti
    # o surede donuyor, geometri sifirlaniyor ve angajman ~10 m'de PLATOLUYOR
    # (olculen CPA medyani 10.29 m, %8 <3 m; teshis modunda 2.66 m / %58).
    #
    # SEBEP yapisal: istasyon noktasi hedefin GERISINDE+ALTINDA duruyor
    # (d_arka ~ 0.966*menzil). Drone kuyruga tam oturmadiysa o noktaya
    # SAVRULMAK zorunda kaliyor; duzeltme terimi ileri beslemeyi CIKARIYOR
    # (18 - 5 = 13-15 m/s) ve arac hedeften YAVAS kaliyor. Hedef 18.0 m/s.
    #
    # COZUM: terminal menzilde komuta, LOS boyunca kapanmayi en az
    # TERM_KAPANMA_MPS yapacak kadar bilesen EKLENIR. Yanal terim
    # kirpilmaz -- yalniz eksik kapanma tamamlanir; toplam V_MUTLAK_MAX'ta
    # doyar. 0 = KAPALI (eski davranis, bit-ayni).
    # ⚠ MEKANIZMA KAPISI: acikken `term_kap_mps` sutunu terminal menzilde
    #   SIFIRDAN BUYUK olmali; hep 0 ise kapi acilmamistir.
    TERM_KAPANMA_M = _env_f("AVCI_GPS_TERM_KAP_M", 25.0)   # m  <- UCUSTA ACILDI
    TERM_KAPANMA_MPS = _env_f("AVCI_GPS_TERM_KAP_V", 4.0)  # m/s hedef kapanma
    V_MUTLAK_MAX = _env_f("AVCI_GPS_V_MUTLAK", 26.0)    # m/s

    # ── TERMINAL DIKEY KAPANMA ESIGI (m) ─────────────────────────────────
    # Bu menzilin ALTINDA istasyonun dikey ofseti yumusakca sifira suruluyor.
    # Gerekce ve olcum: yukaridaki d_below_eff blogu.
    # 8 m secildi: devir kapisi (14 px ~ 22 m) coktan gecilmis ve kilit
    # sayacinin dolmasi icin sure kalmis olur; ama temas oncesi son 8 metrede
    # es irtifaya geciyoruz. 0 = kapali.
    TERM_DIKEY_M = _env_f("AVCI_GPS_TERM_DIKEY", 12.0)  # m  <- UCUSTA ACILDI

    # ── TERMINAL YATAY KAPANMA (2026-08-19, DUZ HEDEFI TUTAMAMANIN SEBEBI) ─
    # Istasyon hedefin GERISINDE d_arka = r_eff*cos(elev) duruyor ve
    # r_eff = min(menzil, RANGE_SET). Yani menzil RANGE_SET'in ALTINA
    # inince istasyon "hedefin 0.966*menzil gerisi" olur; kovaladigimiz
    # konum hatasi menzilin yalnizca %3.4'udur:
    #     menzil 8 m -> hata 0.27 m -> PD = 0.8*0.27 = 0.22 m/s kapanma
    # OLCULEN dr/dt ile birebir: 6-10 m'de -0.57 m/s (22-30 m'de -4.80).
    # SONUC: hedefe ASIMPTOTIK yaklasip HIC VARAMIYORUZ; arac hedefin
    # yanina yapisip paralel uciyor (3-6 m'de yanal 11.76 vs LOS 1.16 m/s).
    # Bu, hedef DUZ ucarken bile olur -- kesme geometrisiyle ilgisi yok.
    #
    # ⚠ DIKEY icin bu cokus ZATEN yazilmis (TERM_DIKEY_M); YATAY esi
    #   yazilmamis. Bu o eksik.
    # Menzil TERM_YATAY_M altina inince arka ofset YUMUSAKCA sifira surulur:
    #     menzil = esikte carpan 1.0  ·  menzil = 0'da 0.0
    # 12 m ile: menzil 8 -> d_arka 7.73 -> 5.15 m (hata 2.85 m -> 2.3 m/s)
    # 0 = kapali (eski davranis, bit-ayni).
    TERM_YATAY_M = _env_f("AVCI_GPS_TERM_YATAY", 12.0)  # m  <- UCUSTA ACILDI
    # ⭐ UCUSTA OLCULDU (2026-08-19, yatay12 + dikey12 + taban25/4 birlikte):
    #     CPA medyani   10.58 -> 6.49 m
    #     <5 m orani      %12 -> %27
    #     3-6 m kapanma -1.01 -> -4.50 m/s   (6-10 m: -0.57 -> -1.70)
    #     yaklasma sayisi 16 -> 15 (degismedi), gorev en iyi 1.23 m
    #   ⚠ BEDEL: yavas zaman (<5 m/s) %2.7 -> %10.3, savrulma %7.7 -> %12.2
    #     ve 10-15 m bandinda dr/dt pozitife dondu (+2.80) -- orada bir
    #     asim/geri dusme var, henuz cozulmedi.
    # Geri alma: AVCI_GPS_TERM_YATAY=0 AVCI_GPS_TERM_DIKEY=0 AVCI_GPS_TERM_KAP_M=0

    # ══ PUSU: HEDEFIN KAPALI PISTINDE BULUSMA NOKTASI (2026-08-18) ══════
    # Vurusu KESME GEOMETRISI uretir: aspect 60-90 deg -> CPA<1.5 m %55;
    # saf kuyruk 150-180 -> %9. Bugun yaklasmalarin %54'u kuyrukta bitiyor
    # ve yalniz %4'u en iyi bantta -- cunku istasyon hedefin ARKASINDA.
    #
    # Hedef KAPALI oval uculuyor (periyot 29.60 s, p10=p90=29.60). Tekrar
    # kestiricisi (control/guidance/hedef_tekrar.py) ufuktan BAGIMSIZ
    # 0.62-0.66 m hata veriyor -- 30 s ilerisi, 2 s ilerisinden 6 KAT daha
    # dogru. O yuzden bulusma noktasi SECILEBILIR.
    #
    # SAF KINEMATIK TARAMA (n=1557, ulasilabilirlik suzgeciyle):
    #     aspect bandi     mevcut   basit kesisme   SECILI
    #     60-90 (en iyi)     ~4%        12%          %99
    #     <90 (kesme)         6%        28%         %100
    #     150-180 kuyruk     50%        30%           %0
    # Secilen bulusma suresi medyan 16 s.
    # ⚠ UST SINIRDIR: donus dinamigi/algi katilmadi, gercekte %99 CIKMAZ.
    #
    # ⚠ MENZIL_MIN ALTINDA KAPALI: yakinda konumlanma degil VURUS isteriz;
    #   terminal davranis dokunulmadan kalir.
    # ⚠ `menzil`, `ex/ey` ve faz mantigi HEP gercek simdiki konumu kullanir;
    #   yalniz ISTASYON CAPASI degisir.
    # ⚠ MEKANIZMA KAPISI: acikken `pusu_tgo_s` ve `pusu_aspect_deg`
    #   sutunlari DOLU olmali ve `pusu_aspect_deg` 60-90 bandinda cikmali.
    #   Bos/bantsizsa kol GECERSIZ.
    # ⚠ OLUMSUZ KONTROL: PUSU_CARPAN=1.2 -> periyot %20 bozulur; o kol
    #   KOTULESMELI. Kotulesmiyorsa kazanc kestirimden GELMIYOR demektir.
    # 0 = KAPALI (varsayilan) -> bit-ayni eski davranis.
    PUSU = _env_f("AVCI_GPS_PUSU", 0.0) >= 0.5
    PUSU_ASPECT_HEDEF = _env_f("AVCI_GPS_PUSU_ASPECT", 75.0)    # deg; bandin ortasi
    PUSU_TGO_MIN = _env_f("AVCI_GPS_PUSU_TGO_MIN", 2.0)         # s
    PUSU_TGO_MAX = _env_f("AVCI_GPS_PUSU_TGO_MAX", 30.0)        # s
    PUSU_TGO_ADIM = _env_f("AVCI_GPS_PUSU_TGO_ADIM", 0.5)       # s
    PUSU_V_KABUL = _env_f("AVCI_GPS_PUSU_V", 20.0)              # m/s; ulasilabilirlik hizi
    PUSU_ULASIM_PAY = _env_f("AVCI_GPS_PUSU_PAY", 0.95)         # emniyet payi
    PUSU_MENZIL_MIN = _env_f("AVCI_GPS_PUSU_MENZIL_MIN", 15.0)  # m; altinda KAPALI
    PUSU_CARPAN = _env_f("AVCI_GPS_PUSU_CARPAN", 1.0)           # OLUMSUZ KONTROL

    # ── PUSU KALITE ESIGI (2026-08-19, PUSU'nun HIC ATESLEMEME SEBEBI) ───
    # `hedef_tekrar.KALITE_MAX_M` varsayilani 3.0 m. Bu esik TEMIZ veriye
    # gore secilmis; YARISMA MODUNDA (bozuk GPS) tur-uzeri artik dogal
    # olarak ~5 m oldugu icin kapi HIC acilmiyor.
    # UCUSTA OLCULDU: bayrak=True, menzil>=15 saglaniyor, ama 44 tani
    # satirinin HEPSINDE `tk_periyot=None` -> bulusma noktasi hic uretilmedi
    # (5166 satirda `pusu_tgo_s` 0 kez doldu).
    # ⚠ AYNI TUZAK koprudeki `fusion/periyodik_kestirici.py`'de de vardi ve
    #   orada 12.0 m'ye cikarilarak cozulmustu (bkz. o dosyadaki KALITE_MAX_M
    #   notu: "3 m DEGIL: bozuk veride artik dogal olarak ~5 m").
    # ⚠ GEVSETMENIN RISKI: sahte periyot. Buna karsi OLUMSUZ KONTROL zaten
    #   var -- PUSU_CARPAN=1.2 periyodu %20 bozar; o kolda kazanc SIFIRA
    #   inmezse kazanc periyottan gelmiyordur.
    # Varsayilan 3.0 = DEGISMEDI (eski davranis birebir).
    PUSU_KALITE_MAX = _env_f("AVCI_GPS_PUSU_KALITE", 3.0)       # m

    # ── PUSU ARKA CARPANI (2026-08-19, OLCUMDEN) ─────────────────────────
    # PUSU acikken istasyon, bulusma noktasinin GERISINE konuyordu:
    #     st = bulusma + (-kurs) * d_arka
    # Yani bulusma aninda yine KUYRUGA yerlesiyoruz. Olculdu (aspect@30m,
    # hafiza sozlesmesi: 180 = tam arkasindayiz):
    #     PUSU KAPALI : kesme(60-90) %2.4 | kuyruk(150-180) %41.1 | medyan 141
    #     PUSU ACIK   : kesme       %0.3 | kuyruk        %70.4 | medyan 162
    # -> ozellik amacinin TERSINI uretiyor.
    # Standoff, kuyruk takibinde kamerayi kadrajda tutmak icin var; KESME
    # gecisinde gereksiz. Bu carpan onu PUSU modunda kisar.
    # 1.0 = eski davranis (varsayilan, bit-ayni). 0.0 = dogrudan bulusma
    # noktasina nisan.
    PUSU_ARKA = _env_f("AVCI_GPS_PUSU_ARKA", 1.0)

    # ── PUSU TAAHHUDU (2026-08-19) ───────────────────────────────────────
    # `bulusma_sec` HER TIKTE bastan seciyor. Arama uzayi buyudugunde
    # (sapma_max buyuk) "75 dereceye en yakin aday" tikten tike ZIPLAR;
    # istasyon savrulur ve arac hicbir plana baglanmadan suruklenir.
    # Taahhut: bir kez secilen bulusma ZAMANI sabitlenir; her tikte yalniz
    # o anin KONUMU guncellenir. Sure dolunca ya da ulasilamaz hale gelince
    # yeniden secilir. 1 = acik (varsayilan; PUSU zaten kapali gelir).
    PUSU_TAAHHUT = _env_f("AVCI_GPS_PUSU_TAAHHUT", 1.0) >= 0.5
    # ⚠⚠ SAPMA SINIRI -- HAYATI (ucmadan once olculdu):
    #   Sinirsiz secim istasyonu hedefin SIMDIKI yerinden medyan 130.6 m
    #   (p90 217 m) uzaga koyar. Hedefi medyan 29 m'den goruyoruz, tespit
    #   40 m otesinde duser -> hedef KAYBEDILIR, devir olcutu (10 ardisik
    #   kare) hic dolmaz, sistem COKER.
    #   Tarama: 25 m -> bant %33 · 40 m -> %55 · 60 m -> %65 · sinirsiz %99
    #   ama gercek sapma sirasiyla 19.5 / 21.2 / 27.9 / 130.6 m.
    PUSU_SAPMA_MAX = _env_f("AVCI_GPS_PUSU_SAPMA", 40.0)        # m

    # ══ KURSUN MODU (2026-08-18) — KOK NEDENE DOGRUDAN NISAN ═════════════
    # ⭐ OLCULEN KOK NEDEN (n=62887 kare, donmus veri ayiklandi):
    #     hedef donusu      dr/dt        yaklasan kare
    #     duz (<5 d/s)     -3.20 m/s          %72
    #     hafif 5-15       -0.57              %56
    #     donuyor 15-30    +0.82  UZAKLASIYOR %43
    #   Hiz ustunlugumuz +3.3 m/s DURUYOR ama hedef donunce menzil kapanmayi
    #   birakip ACILIYOR. Yani hiz var, LOS ile HIZALI DEGIL.
    #   Bu, saf takibin egri yoldaki YAPISAL siniridir.
    #   ⚠ Dort alternatif aciklama ELENDI: algi bozulmuyor (donuste tespit
    #     %81 vs duzde %74), hizimiz dusmuyor (21.8->21.0), kapanma
    #     cokmuyor (3.7->3.3), donus tavanina dayanmiyoruz (23.9 vs 32.7).
    #   Kacirmanin ayrisimi da bunu soyluyor: donuste BOYUNA -8.62 m,
    #   yanal -1.39, dikey -1.25. Yani "geride kaliyoruz", yana savrulmuyoruz.
    #
    # COZUM: istasyonu hedefin SIMDIKI yerinin arkasina degil, `t_go` SONRAKI
    # yerinin arkasina kur -- kirisi kes, yayi takip etme.
    #     t_go = menzil / kapanma,  [TGO_MIN, KURSUN_TGO_MAX] araliginda
    # ⚠ PUSU_MOD="aspect" (eski): 15 s ileri, 40 m uzak, aci maksimize eden
    #   nokta secilir. UCUSTA DENENDI, KAZANMADI -- cunku istasyonu cok
    #   uzaga tasiyip angajmani bozuyor.
    #   PUSU_MOD="kursun": KISA ufuk, istasyon hedefin hemen arkasinda kalir,
    #   yalnizca DONUSU ONCELER. Kok nedene dogrudan nisan alan mod budur.
    # ⚠ Kestirim dogrulugu bu ufukta olculdu: 1 s'de 0.57 m
    #   (sabit donus 1.73, sabit hiz 2.58) -- yani kisa ufukta guvenli.
    PUSU_MOD = os.environ.get("AVCI_GPS_PUSU_MOD", "aspect").strip().lower()
    KURSUN_TGO_MAX = _env_f("AVCI_GPS_KURSUN_TGO", 3.0)         # s
    KURSUN_KAPANMA = _env_f("AVCI_GPS_KURSUN_KAP", 3.2)         # m/s (olculen)
    # ── MAX_ACCEL: KOMUT HIZI DEGISIM SINIRI ─────────────────────────────
    # ⚠ 2026-08-15'te OLCULDU: ASIL BAGLAYAN LIMIT BU.
    # Bizim aracin GERCEK yanal ivmesi (24682 ornekli iz kaydi, hiz>8 m/s):
    #     %99  11.22   max 11.96 m/s²      -> esdeger yatis 49-51°
    # yani komut tam 12.0'a DAYANMIS. Aracin kendi fizigi degil, BU CLAMP
    # baglıyor. Hiz vektorunun donebilecegi en yuksek hiz dogrudan buradan:
    #     omega_max = MAX_ACCEL / V = 12 / 18.3 = 37.6 °/s
    # ve olculen %99 donus hizi 37.9 °/s -- birebir ayni.
    #
    # NEDEN ONEMLI: donen hedefi takip icin gereken 33-36 °/s. Tavana
    # dayaniyoruz, yani her 30°'lik duzeltme
    #     dv = 2·V·sin(15°) = 9.3 m/s  ->  9.3/12 = 0.78 s
    # suruyor ve o surede hedef 16° daha donuyor. Kalici takip gecikmesinin
    # kaynagi bu.
    #
    # ⚠ MEKANIZMA KAPISI (Gazebo ekibinin O6 dersi): bir ozelligi kiyaslamadan
    # ONCE gercekten devreye girdigini kanitla. Yukseltince OLCULEN yanal
    # ivmenin 12'yi ASTIGINI dogrula; asmiyorsa oyunun kendi ucus modeli
    # bagliyordur ve deney gecersizdir.
    # Hedef kestirimi emniyeti (2026-08-17, OLCULDU)
    #   normal adim medyan 0.605 m, p99 1.89 m  -> 10 m esigi 5 kat pay birakir
    #   hedefin gercek hizi 17.99 m/s (sabit oval) -> 40 m/s tavani 2.2 kat pay
    # ⚠ 2026-08-17 VARSAYILAN KAPALI YAPILDI. Bu koruma bugun eklendi,
    #   dayanagi YANLIS cikti ("isinlanma" sandigim sey VERI BOSLUGUYDU) ve
    #   canli olcumde 346 kez tetiklenip kestirimi BOZDU:
    #       tgt_v medyan 10.9  (gercegi 17.99)
    #   Orijinal kod `1e-3 < fdt < 2.0` kapisiyla bayat farklari zaten
    #   eliyordu. Dogrulanmamis bir degisiklik olcumu bozmamali ->
    #   acmak icin AVCI_HEDEF_SICRAMA_KORU=1.
    SICRAMA_KORU = _env_f("AVCI_HEDEF_SICRAMA_KORU", 0.0) >= 0.5
    HEDEF_SICRAMA_M = _env_f("AVCI_HEDEF_SICRAMA_M", 10.0)
    HEDEF_HIZ_TAVAN = _env_f("AVCI_HEDEF_HIZ_TAVAN", 40.0)
    MAX_ACCEL = _env_f("AVCI_MAX_ACCEL", 12.0)   # m/s²  — YATAY
    # ══ DIKEY IVME BUTCESI (2026-08-17) ══════════════════════════════════
    # OLCULDU (14 ucus logu, 1970 tik): tek 3B tavan dikeyi ac birakiyor.
    #   menzil 4-8 m  -> tiklerin %100'u tavanda, yataya 11.97 m/s²,
    #                    DIKEYE 0.22-0.83 m/s² kaliyor.
    # Terminal kapinin istedigi 1.55 m tirmanis icin 0.82 s'de ~1.85 m/s
    # gerekiyor; 0.43 m/s² ile o surede ancak 0.35 m/s kurulabiliyor -> 5 kat az.
    # common.limit_acceleration_split ZATEN bu ariza icin yazilmis
    # (docstring: "drone hedefin ~2 m altindan geciyordu", 2026-07-31) ama
    # iki canli yasanin ikisi de cagirmiyordu.
    # ⚠ VARSAYILAN KAPALI: split, tek tavanla BIREBIR ayni davranisa
    #   ayarlanamaz (12/12 split = 17 m/s² bileske). Once A/B ile kanitla.
    ACCEL_SPLIT = _env_f("AVCI_ACCEL_SPLIT", 0.0) >= 0.5
    MAX_ACCEL_V = _env_f("AVCI_MAX_ACCEL_V", 10.0)   # m/s² — DIKEY (split acikken)
    DERIV_EMA = 0.2

    # --- YAW ---
    # ── BURUN (YAW) OTORITESI ────────────────────────────────────────────
    # ⚠ OLCULDU (2026-08-19, canli, 1436 ornek): burun ANGAJMAN BANDINDA
    #   savruluyor ve HIZI YIYOR.
    #       menzil >50 m : |w|>60 °/s orani %2.9
    #       menzil 25-50 : %17.0
    #       menzil 10-25 : %26.4   (p90 106 °/s)   <-- angajman bandi
    #       menzil <10   : %17.4
    #       savrulurken hiz medyan 16.3 m/s, normalde 22.1
    #   Faz gecisinin ILK saniyesinde de sicrama: %31.2 (>60 °/s).
    # SEBEP: burun GERCEK hedefe kilitli; yakin menzilde LOS acisal hizi
    #   patlar (15 m'de ~69 °/s, 10 m'de ~103 °/s). Yasa burnu buna
    #   uydurmaya calisir, govde savrulur. Yaw doyunca motorlarin roll/pitch
    #   yetkisi azalir (bkz. asagidaki takla notu) -> oteleme kaybi.
    # ⚠ AMA BURUN TAM HEDEFTE OLMAK ZORUNDA DEGIL: kamera FOV'u 122.08 deg,
    #   yarisi ~61 deg. 20-25 derecelik kerteriz hatasi hedefi kadrajin
    #   ortasindan ~130 px kaydirir (640 px'de 189..451 araligi) -- rahat
    #   icinde. Olu bant genisletilip tavan dusurulunce yaw dinginlesir ve
    #   yetki otelemeye kalir.
    # Varsayilanlar DEGISMEDI (3 deg / 120 deg-s); env ile denenir.
    # ── KERTERIZ DUZLESTIRME (yalniz BURUN) ──────────────────────────────
    # Kerteriz her tikte hedefin DUZLESTIRILMEMIS kestiriminden hesaplaniyor
    # (POS_EMA=1.0 -- gecikmeyi silmek icin bilerek kapatildi). 15 m'de
    # birkac metrelik kestirim titremesi 10-20 derecelik kerteriz titremesi
    # demektir ve burun onu kovalar: olculdu, |w|>60 °/s orani menzil
    # 10-25 m'de %26.4 (p90 106 °/s) ve savrulurken hiz 22.1 -> 16.3 m/s.
    # ⚠ COZUM KONUMU DEGIL BURNU duzlestirmek: oteleme komutu ham (tepkisel)
    #   kestirimi kullanmaya devam eder, yalniz yaw hedefi yumusatilir.
    #   Boylece POS_EMA'nin geri getirdigi 3 m'lik gecikme YENIDEN GIRMEZ.
    # 1.0 = kapali (varsayilan, bit-ayni). 0.25 = belirgin yumusatma.
    KERTERIZ_EMA = _env_f("AVCI_GPS_KERTERIZ_EMA", 1.0)

    # ── KOMUT YON TAVANI (2026-08-19, KOK NEDEN) ─────────────────────────
    # Kullanicinin gordugu "sallanma + sacma sapan durdurmalar".
    # LOGDAN OLCULDU (43994 ornek, 20 Hz sabit adim, iris_yaw_deg turevi):
    #     menzil >50 m : |w|>60 °/s %3.6   (medyan  0.0)
    #     menzil 25-50 : %10.0             (medyan  2.2)
    #     menzil 10-25 : %16.9             (medyan 17.7)
    #     menzil <10 m : %39.0             (medyan 48.9, p90 127.7, maks 293.6)
    #
    # ⚠ BURUN BIZIM YAW KOMUTUMUZU TAKIP ETMIYOR: GPS yaw tavani 80 °/s ve
    #   gorsel yasaya da tavan konuldugu halde maks 175-293 °/s goruldu.
    #   Oyun "ANGL AIR" modunda; burun HIZ KOMUTUNUN YONUNU izliyor.
    #
    # ⭐ KENDINI BESLEYEN DONGU: ivme tavani yon donusunu w = a/v ile
    #   sinirlar -- yani HIZ DUSTUKCE IZIN VERILEN DONUS BUYUR:
    #       20 m/s -> 12/20 = 34 °/s      5 m/s -> 12/5 = 137 °/s
    #   Savrulma hizi dusurur (olculdu: 22.1 -> 16.3 m/s), dusen hiz daha
    #   buyuk savrulmaya izin verir. Dongu boyle kilitleniyor.
    #
    # COZUM: komut edilen hiz vektorunun YON DEGISIM HIZINI dogrudan sinirla
    # (ivme BUYUKLUGUNU degil). Boylece dusuk hizda da yon savrulamaz.
    # 0 = kapali (varsayilan, bit-ayni).
    # ⚠ MEKANIZMA KAPISI: acikken `yon_kirp_deg` sutunu SIFIRDAN BUYUK
    #   satirlar icermeli; hep 0 ise tavan hic baglamamistir.
    # ⚠ DENENDI ve KAPALI BIRAKILDI. Mekanizma kapisi (`yon_kirp_deg`)
    #   tavanin NEREDEYSE HIC BAGLAMADIGINI gosterdi:
    #       menzil 10-25 m : kirp>0 yalniz %0.6
    #       menzil <10 m   : %3.9
    #   Yani komut edilen hiz YONU yakin menzilde zaten hizli degismiyor;
    #   savrulmanin kaynagi burasi DEGIL. (A/B: savrulma %10.3 -> %8.3,
    #   CPA/hiz fark etmedi.)
    # ⭐ UC SUPHELININ UCU DE ELENDI:
    #     1) GPS yaw komutu   -> 80 °/s'de sinirliyken bile 293 °/s goruldu
    #     2) gorsel yasa yaw'i -> sinirlaninca DUZELMEDI (hatta kotulesti)
    #     3) komut edilen yon  -> tavan baglamiyor (bu satir)
    #   Geriye kalan aciklama: burun GERCEK hiz vektorunu izliyor ve gercek
    #   hiz yonu YAKIN MENZILDE ASIM yuzunden savruluyor. Yani "sallanma"
    #   bir yaw sorunu degil, ASIM belirtisi -> cozum terminal geometride.
    KOMUT_YON_TAVAN = _env_f("AVCI_GPS_YON_TAVAN", 0.0)   # °/s (0 = kapali)
    # ── SECILEN DEGERLER (2026-08-19) ────────────────────────────────────
    # Kullanicinin canli gozlemi: "cok sallanmalar, dengesiz takip, sacma
    # sapan durdurmalar". Olcum bunu dogruladi ve tek olay oldugunu gosterdi:
    # burun savruldugunda hiz 22.1 -> 16.3 m/s dusuyor.
    # DENENDI (A/B, olu bant 22 deg + tavan 60 deg/s):
    #     |w|>60 °/s orani  %13.0 -> %6.2   (YARIYA indi)
    #     hiz medyan        20.8  -> 19.3
    #     CPA medyani       9.81  -> 14.47  (ama <2 m %0 -> %8, en iyi 2.50 -> 1.45)
    #   n=12-21 ile CPA medyani KARAR VERDIRMIYOR (kollar arasi 6.8-14.5
    #   arasi saliniyor); savrulma olcutu ise net.
    # ⚠ CURUTULDU: "kerteriz titremesi burnu savuruyor" -> KERTERIZ_EMA=0.25
    #   savrulmayi AZALTMADI (%8.2 -> %9.9). Titreme kestirimden degil,
    #   yakin menzilde GERCEKTEN var olan LOS acisal hizindan geliyor
    #   (15 m'de ~69 °/s, 10 m'de ~103 °/s).
    # Bu yuzden OLCULU degerler secildi: olu bant 12 deg (61 derecelik yari
    # FOV'un besde biri -- hedef kadrajda rahat kalir), tavan 80 deg/s.
    # Geri almak: AVCI_GPS_YAW_OLU=3 AVCI_GPS_YAW_TAVAN=120
    YAW_DEADBAND = math.radians(_env_f("AVCI_GPS_YAW_OLU", 12.0))
    YAW_RATE_MAX = math.radians(_env_f("AVCI_GPS_YAW_TAVAN", 80.0))

    # --- HEDEF TELEMETRİ FİLTRESİ ---
    # ⚠⚠ CIFTE FILTRELEME (olculdu 2026-08-19, ucusta):
    #   Periyodik kestirici (fusion/periyodik_kestirici.py) get_plane
    #   cikisini 21 m -> 3.42 m'ye indiriyor, AMA bu EMA onu tekrar
    #   6.48 m'ye CIKARIYOR. Sebep: EMA ~0.35 s gecikme ekler, 18 m/s'de
    #   ~6 m. Kestiricinin cikisi ZATEN duzgun ve gecikme telafili;
    #   ustune EMA koymak SAF ZARAR.
    #   Olculen: |menzil_ham - gercek| 3.42 m (p90 14.9)
    #            |menzil     - gercek| 6.48 m (p90 26.4)
    #   -> AVCI_PERIYODIK acikken bunu 1.0 (filtre yok) yapin.
    #   Varsayilan 0.4 -> bit-ayni eski davranis.
    POS_EMA = _env_f("AVCI_GPS_POS_EMA", 0.4)
    VEL_EMA = 0.3
    HOLD_S = 3.0             # s; hedef telemetri bu kadar donuk kalırsa → DROPOUT

    # --- DURUM / DEVİR ETİKETİ (supervisor kendi GATE_MENZIL=20'yi kullanır) ---
    HANDOFF_RANGE = 20.0    # m; d_h altında durum=KILIT (görsel devir bandı)


# Telemetri/arayüz için son durum (gcs_server + supervisor.izci okur; salt gözlem)
#
# tgt_vx/vy/vz (2026-08-08): hedefin GPS'ten kestirilen hız vektörü. Supervisor
# bunu DEVİR ANINDA bir kez okuyup görsel faza DONDURULMUŞ taşıyıcı olarak verir
# (bkz. bbox_ibvs.Cfg / D0 yarışma kuralı). Görsel faz boyunca bu değer bir daha
# okunmaz — görsel döngüye canlı GPS erişimi YOKTUR (yapısal garanti).
status = {
    "durum": "WARMUP", "d_h": None, "menzil": None,
    "kadraj_yaw_deg": None, "kadraj_elev_deg": None, "none_count": 0,
    "tgt_vx": None, "tgt_vy": None, "tgt_vz": None,
    # Angajman geometrisi (bkz. adim 9b) -- gorsel devir kapisi bunlari okur.
    "aspect_deg": None, "omega_los_deg": None, "omega_term_deg": None,
    "term_kap_mps": 0.0,
    "yon_kirp_deg": 0.0,
    # Hedefin KENDI donus hizi (°/s). ~0 = duz kisim, ~20 = donus.
    "hedef_donus_deg": None,
}

# Hedefin yon gecmisi (donus hizi turevi icin). [(heading_rad, t)]
_hdg_gecmis = []

# ── FAZ GECISI SURDURME (2026-08-21) ────────────────────────────────────
# run_gps_guidance faz gecislerinde yeniden cagriliyor (olculdu: 16 dk'da
# 145 kez, ~6.5 s'de bir). Kestirim durumu burada YASAR, boylece kisa
# gorsel araliklardan sonra SOGUK baslanmaz. Ayrintili gerekce ve bayatlik
# kurallari run_gps_guidance icindeki "FAZ GECISINDE SURDURME" blogunda.
_GPS_SURDUR = {}
# Kesinti bundan uzunsa durum ATILIR. 8 s: olculen gorsel faz epizotlari
# kisa (temas 20 karede kayboluyor, ~1.3 s @15 FPS); 8 s birkac epizodu
# kapsar ama gorev yeniden baslamasi/olum gibi uzun kopusları KAPSAMAZ.
SURDUR_MAX_S = 8.0
# ⚠ ISINLANMAYA (yeniden dogus) karsi AYRI bir mesafe kapisi YOK: restore
#   edilen est_* bir EMA'dir ve gelen ham olcumle birkac tikte yakinsar,
#   ayrica 8 s'lik bayatlik kapisi gorev yeniden baslamasini zaten eler.
#   Kapi eklenecekse ham konum restore aninda okunabilir olmali -- su an
#   dongu baslamadan once elimizde degil.

_PUSU_TK = None          # modul duzeyinde tek kestirici (fazlar arasi yasar)
_PUSU_T_HEDEF = None     # taahhut edilen MUTLAK bulusma zamani (s)
_PUSU_TK_CARPAN = None   # olumsuz kontrol carpani degisirse yeniden kur


def _pusu_takipci(cfg):
    """Fazlar arasi YASAYAN tek kestirici. Bkz. Cfg.PUSU gerekcesi."""
    global _PUSU_TK, _PUSU_TK_CARPAN
    from .hedef_tekrar import HedefTekrar
    c = float(getattr(cfg, "PUSU_CARPAN", 1.0))
    _k = float(getattr(cfg, "PUSU_KALITE_MAX", 3.0))
    if (_PUSU_TK is None or _PUSU_TK_CARPAN != c
            or getattr(_PUSU_TK, "kalite_max", None) != _k):
        _PUSU_TK = HedefTekrar(periyot_carpan=c,
                               kalite_max=float(getattr(cfg, "PUSU_KALITE_MAX", 3.0)))
        _PUSU_TK_CARPAN = c
    return _PUSU_TK


def _pusu_sec(tk, now, ix, iy, cfg, hx, hy):
    """cfg parametreleriyle tek seferlik bulusma secimi.

    ⚠ `bulusma_sec` BURADA ice aktarilir: modulun ust duzeyinde degil,
      `run_gps_guidance` icinde local olarak ice aktariliyordu; modul
      duzeyindeki bu yardimci onu goremez (NameError). Testte yakalandi.
    """
    from .hedef_tekrar import bulusma_sec as _bs
    return _bs(
        tk, now, ix, iy,
        aspect_hedef=cfg.PUSU_ASPECT_HEDEF,
        tgo_min=cfg.PUSU_TGO_MIN, tgo_max=cfg.PUSU_TGO_MAX,
        tgo_adim=cfg.PUSU_TGO_ADIM, v_kabul=cfg.PUSU_V_KABUL,
        ulasim_pay=cfg.PUSU_ULASIM_PAY,
        sapma_max=cfg.PUSU_SAPMA_MAX, hx=hx, hy=hy)


def _pusu_taahhutlu(tk, now, ix, iy, cfg, hx, hy):
    """TAAHHUTLU secim (bkz. Cfg.PUSU_TAAHHUT).

    Secilen bulusma ZAMANI sabit tutulur; her tikte yalniz o anin konumu
    yeniden kestirilir. Boylece plan tikten tige ziplamaz.
    Taahhut DUSER: sure doldu (kalan < tgo_min) · kestirim uretilemiyor ·
    artik yetisilemiyor (ulasilabilirlik %15 paya ragmen bozuldu).
    """
    global _PUSU_T_HEDEF
    if not getattr(cfg, "PUSU_TAAHHUT", True):
        _PUSU_T_HEDEF = None
        return _pusu_sec(tk, now, ix, iy, cfg, hx, hy)

    if _PUSU_T_HEDEF is not None:
        kalan = _PUSU_T_HEDEF - now
        if kalan >= float(cfg.PUSU_TGO_MIN):
            p = tk.kestir(_PUSU_T_HEDEF)
            q = tk.kestir(_PUSU_T_HEDEF + 0.5)
            if p is not None and q is not None:
                ux = q[0] - p[0]
                uy = q[1] - p[1]
                un = math.hypot(ux, uy)
                if un >= 0.3:
                    ux /= un
                    uy /= un
                    rx = ix - p[0]
                    ry = iy - p[1]
                    rn = math.hypot(rx, ry)
                    ulas = (float(cfg.PUSU_V_KABUL) * kalan
                            * float(cfg.PUSU_ULASIM_PAY) * 1.15)
                    if 0.5 <= rn <= ulas:
                        c = max(-1.0, min(1.0, (rx * ux + ry * uy) / max(rn, 1e-6)))
                        return (p[0], p[1], p[2], ux, uy, kalan,
                                math.degrees(math.acos(c)))
        _PUSU_T_HEDEF = None

    r = _pusu_sec(tk, now, ix, iy, cfg, hx, hy)
    if r is not None:
        _PUSU_T_HEDEF = now + r[5]
    return r


_LOG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "logs")

# ⚠ "menzil" ve "tgt_*" KESTİRİMDEN hesaplanır (EMA'lı est_x/y/z), HAM
# telemetriden değil. Bu ayrım 2026-08-06'da kafa karışıklığı yarattı:
# arayüz ham telemetriyi kullandığı için köşelerde CSV 15 m derken panel 21 m
# gösteriyordu ve hangisinin doğru olduğu ayırt edilemiyordu.
# Artık HAM konum ve ona olan mesafe de yazılıyor:
#     tgt_ham_*  : get_plane()'in verdiği konum (EMA'dan ÖNCE)
#     menzil_ham : drone → ham konum mesafesi  (panelin gördüğü sayı)
#     kestirim_gecikme_m : |ham − kestirim|, yani filtrenin ne kadar geriden
#                          geldiği. Manevrada bu büyür; köşe analizinin anahtarı.
_CSV_ALANLAR = [
    "t", "dt", "durum", "d_h", "menzil",
    "menzil_ham", "kestirim_gecikme_m",
    "tgt_ham_x", "tgt_ham_y", "tgt_ham_z",
    "tgt_x", "tgt_y", "tgt_z", "tgt_vx", "tgt_vy", "tgt_vz",
    "iris_x", "iris_y", "iris_z", "iris_roll_deg", "iris_pitch_deg", "iris_yaw_deg",
    "st_x", "st_y", "st_z", "vx_cmd", "vy_cmd", "vz_cmd", "yaw_cmd_deg",
    "kadraj_yaw_deg", "kadraj_elev_deg", "kadraj_pitch_hata_deg", "u_px", "v_px",
    "ist_elev_deg",   # istasyonun o anki LOS yükselişi (dinamik modda değişken)
    "ff_donus_mps",   # dönüş ileri beslemesi |ω×r| (düzde 0)
    "d_arka_m",       # istasyonun etkin arka bileşeni (dönüşte erir)
    # ── DEVIR KAPISI MEKANIZMA KAPISI (2026-08-18) ────────────────────────
    #   Kapi acildiginda "gercekten calisti mi" bu iki sutundan dogrulanir.
    "hedef_donus_deg",   # hedefin KENDI donus hizi (isaretli, EMA'li)
    "aspect_deg",        # hedefin hiz vektoru ile LOS arasi aci
    "term_kap_mps",      # terminal kapanma tabaninin EKLEDIGI m/s (0=kapi kapali)
    "yon_kirp_deg",      # komut yon tavaninin KIRPTIGI °/s (0=tavan baglamadi)
    # ── PUSU mekanizma kapisi (bkz. Cfg.PUSU) ────────────────────────────
    # ⚠ status ile CSV AYRI sozluklerdir (extrasaction="ignore"): yalniz
    #   status'e yazmak sutunu BOS birakir. 2026-08-17'de `hedef_donus_deg`
    #   tam bu yuzden 228 satirin 0'inda doluydu. Ikisine de yazilir.
    "pusu_tgo_s",        # secilen bulusma suresi (s); BOSSA kapi calismadi
    "pusu_aspect_deg",   # bulusma anindaki aspect; 60-90 bandinda olmali
    "pusu_sapma_m",      # istasyon <-> hedefin SIMDIKI yeri (sinir 40 m)
    "pusu_periyot_s",    # kestirilen periyot (~29.6 bekleniyor)
    "pusu_kalite_m",     # tur-uzeri artik medyani (kucuk = pist tekrarliyor)
]


def run_gps_guidance(conn, get_plane, get_iris, stop_event, cfg=Cfg):
    loop_period = 1.0 / cfg.LOOP_HZ
    ist_elev = math.radians(cfg.ISTASYON_ELEV_DEG)
    d_behind = cfg.RANGE_SET * math.cos(ist_elev)        # yatay standoff (15°'de ~10.63 m)
    d_below = cfg.RANGE_SET * math.sin(ist_elev)         # dikey alt ofset (15°'de ~2.85 m)

    # hedef kestirimi (EMA pozisyon + sonlu-fark hız)
    est_x = est_y = est_z = None
    bearing_f = None                 # KERTERIZ_EMA durumu (yalniz burun)
    # ⚠⚠ PUSU kestiricisi MODUL DUZEYINDE yasar -- OLCULEREK duzeltildi:
    #   `run_gps_guidance` HER FAZ GECISINDE yeniden cagriliyor ve GPS fazi
    #   epizotlari yalniz 2-28 s suruyor (medyan 11-17 s; olculdu, 5 log).
    #   Kestirici fonksiyon icinde yaratilinca her geciste SIFIRLANIYORDU ve
    #   45 s'lik gozlem esigi HIC dolmuyordu -> kapi hic acilmadi (ucusta
    #   dogrulandi: pusu_* sutunlarinin TAMAMI bos).
    #   Hedef ovalini kesintisiz uculuyor; sifirlanan tek sey bizim tamponumuzdu.
    #   Isinlanmaya karsi koruma `HedefTekrar.ekle` icinde (SICRAMA_HIZ).
    from .hedef_tekrar import bulusma_sec as _bulusma_sec      # noqa: E402
    _tk = _pusu_takipci(cfg)
    vel_x = vel_y = vel_z = 0.0
    tgt_hdg_prev = None       # hedefin hız yönü (rad) — dönüş hızı için
    tgt_omega = 0.0           # hedefin açısal hızı (rad/s, işaretli), EMA'lı
    last_raw = None
    t_last_fresh = None
    none_count = 0

    de = [0.0, 0.0, 0.0]           # EMA'lı yatay/dikey hata türevi
    e_prev = None
    t_prev_deriv = None

    vx_prev = vy_prev = vz_prev = 0.0
    cmd_yaw = None

    # ══ FAZ GECISINDE SURDURME (2026-08-21, olculdu) ═════════════════════
    # `run_gps_guidance` her GPS<->GORSEL gecisinde YENIDEN cagriliyor.
    # OLCULDU (tek kosu, 16 dk): 145 ayri gps_guidance_*.csv, yani yasa
    # ortalama HER 6.5 SANIYEDE BIR sifirdan kuruluyor. Dongu su:
    #   GPS kosar -> 10 ardisik karede gorsel KILIT -> faz_stop.set()
    #   -> gorsel faz -> 20 karede temas kaybi -> GPS'e donus -> YENIDEN INSA
    # Her insa sunlari SOGUK baslatiyordu:
    #   est_x/y/z   hedef konum EMA'si      -> kestirim her seferinde yakinsamaya
    #   vel_x/y/z   hedef hiz kestirimi        bastan basliyor ("gec takip ediyor")
    #   tgt_omega   hedefin acisal hizi
    #   pitch_ema   govde pitch EMA
    #   de/e_prev   hata turevi EMA'si
    # PUSU takipcisi icin ayni sorun ONCEDEN tespit edilip modul duzeyine
    # tasinmisti (bkz. _pusu_takipci); ayni ilaci kestiriciye de veriyoruz.
    #
    # ⚠ BAYAT DURUM RESTORE EDILMEZ: kesinti SURDUR_MAX_S'den uzunsa
    #   (gorev yeniden basladi, arac oldu, uzun gorsel faz) durum ATILIR ve
    #   soguk baslanir. "Yaklasik dogru" durumla ucmak YOK.
    # ⚠ Isinlanma korumasi: kaydedilen konumla simdiki ham konum arasi
    #   SURDUR_SICRAMA_M'yi asiyorsa da atilir (yeniden dogus).
    global _GPS_SURDUR
    _sur = _GPS_SURDUR
    if _sur:
        _bosluk = time.monotonic() - _sur.get("t_kayit", 0.0)
        if _bosluk <= SURDUR_MAX_S:
            est_x, est_y, est_z = _sur["est"]
            vel_x, vel_y, vel_z = _sur["vel"]
            tgt_hdg_prev = _sur["hdg"]
            tgt_omega = _sur["omega"]
            pitch_ema = _sur["pitch_ema"]
            bearing_f = _sur["bearing_f"]
            cmd_yaw = _sur["cmd_yaw"]
            print("[GPS] SURDURULDU: kestirim durumu korundu (kesinti %.1f s)"
                  % _bosluk)
        else:
            print("[GPS] SOGUK BASLANGIC: kesinti %.1f s > %.1f s -> durum atildi"
                  % (_bosluk, SURDUR_MAX_S))
            _GPS_SURDUR = {}
    prev_time = None
    loop_count = 0
    pitch_ema = None               # gövde pitch EMA (rad) — dinamik yükseliş girdisi
    kurt = Kurtarma()              # duruş bekçisi (normal uçuşta hiç tetiklenmez)

    os.makedirs(_LOG_DIR, exist_ok=True)
    csv_yol = os.path.join(_LOG_DIR, time.strftime("gps_guidance_%Y%m%d_%H%M%S.csv"))
    f = open(csv_yol, "w", newline="")
    w = csv.DictWriter(f, fieldnames=_CSV_ALANLAR, extrasaction="ignore")
    w.writeheader()

    print("=" * 60)
    print("[GPS] Kadraj güdümü (yeniden inşa) — hedefi kamera merkezine getir")
    print(f"[GPS] setpoint: slant {cfg.RANGE_SET:.1f}m → {d_behind:.1f}m arka + "
          f"{d_below:.1f}m alt; yakınlaşınca ofset menzille ORANTILI küçülür, "
          f"yükseliş her menzilde {cfg.ISTASYON_ELEV_DEG:.0f}° kalır "
          f"(kamera tilt'i {cfg.CENTER_ELEV_DEG:.0f}° → hedef merkezin "
          f"{cfg.CENTER_ELEV_DEG - cfg.ISTASYON_ELEV_DEG:.0f}° altında) — log: {csv_yol}")
    if cfg.ELEV_DINAMIK:
        print(f"[GPS] istasyon yükselişi DİNAMİK: {cfg.CENTER_ELEV_DEG:.0f}° + gövde "
              f"pitch (EMA τ≈1 s), sınır [{cfg.ELEV_DIN_MIN:.0f}°, "
              f"{cfg.ELEV_DIN_MAX:.0f}°] — düzde ~25°, daire tutuşunda ~36° beklenir; "
              f"kapatmak: AVCI_GPS_ELEV_DIN=0")
    _t_terminal = d_behind / 3.7          # ölçülen terminal yatay kapanma hızı
    print(f"[GPS] terminal dikey bütçe: {d_below:.2f} m kapatılacak, "
          f"~{_t_terminal:.2f} s var → 1 m/s² rampayla {0.5*_t_terminal**2:.2f} m "
          f"{'YETER' if 0.5*_t_terminal**2 > d_below else '⚠ YETMEZ'}")
    print("=" * 60)

    def _hover():
        send_velocity(conn, 0.0, 0.0, 0.0, cmd_yaw or 0.0)

    try:
        while not stop_event.is_set():
            now = time.monotonic()
            dt = (now - prev_time) if prev_time is not None else loop_period
            dt = clamp(dt, 0.001, 0.2)
            prev_time = now

            iris = get_iris()
            ix, iy, iz = iris["x"], iris["y"], iris["z"]
            iroll = iris.get("roll", 0.0)
            ipitch = iris.get("pitch", 0.0)
            iyaw = iris.get("yaw", 0.0)

            # ── KURTARMA BEKÇİSİ (güdümden bağımsız emniyet; bkz. kurtarma.py) ──
            # Araç takla atıyor/kaçak dönüyorsa güdüm komutu KESİLİR: hız sıfır,
            # yaw olduğu yerde tutulur → araç toparlanır, uçuş kurtulur.
            # Normal uçuşta tetiklenmez (eşikler ölçülen zarfın çok üstünde).
            if kurt.guncelle(iroll, ipitch, iyaw, now):
                send_velocity(conn, 0.0, 0.0, 0.0, iyaw)
                vx_prev = vy_prev = vz_prev = 0.0
                cmd_yaw = iyaw          # güdüm devralınca sıçrama olmasın
                status.update(durum="KURTARMA")
                loop_count += 1
                _sleep(now, loop_period)
                continue

            # ── DİNAMİK İSTASYON YÜKSELİŞİ: elev = tilt + pitch (bkz. Cfg) ──
            pitch_ema = ipitch if pitch_ema is None else (
                cfg.ELEV_PITCH_EMA * ipitch
                + (1 - cfg.ELEV_PITCH_EMA) * pitch_ema)
            if cfg.ELEV_DINAMIK:
                ist_elev = math.radians(clamp(
                    cfg.CENTER_ELEV_DEG + math.degrees(pitch_ema),
                    cfg.ELEV_DIN_MIN, cfg.ELEV_DIN_MAX))

            plane = get_plane()

            # ── 1) TAZELİK + FİLTRE (EMA pozisyon, sonlu-fark hız) ──
            raw = (plane["x"], plane["y"], plane["z"])
            frozen = bool(plane.get("frozen", False))
            fresh = (not frozen) and (raw != last_raw)
            if fresh:
                last_raw = raw
                none_count = 0
                if est_x is None:
                    est_x, est_y, est_z = raw
                # ══ SICRAMA KORUMASI (2026-08-17) ═══════════════════════════
                # Hedef IMHA EDILIP yeniden dogunca konumu ISINLANIYOR:
                # olculdu 9 sicrama, 28-96 m, TEK ornekte (normal adim 0.605 m,
                # p99 1.89 m). Kestirici bu sicramanin USTUNDEN fark aliyordu:
                #   vel = POS_EMA * 180 m / 0.05 s  ->  ~1000 m/s
                # Sonuc: tgt_v 18 -> 55-159 m/s, gudum sekiz kat hizli hayali
                # bir hedefe onden kesme hesapliyor, arac kontrolden cikiyor
                # (yaw 800-2400 °/s). Kontrol kaybi 3 -> 99'a firladi.
                # ⚠ NEDEN SIMDI ORTAYA CIKTI: sicrama ancak hedefe VURUNCA
                #   olusuyor. Ayna duzeltmesinden once hic vuramadigimiz icin
                #   bu hata hic tetiklenmemisti -- basari gizli hatayi acti.
                elif (getattr(cfg, "SICRAMA_KORU", False)
                      and math.dist(raw, (est_x, est_y, est_z))
                      / max((now - t_last_fresh) if t_last_fresh else 1e-3, 1e-3)
                      > cfg.HEDEF_HIZ_TAVAN):
                    # ⚠ 2026-08-17 DUZELTME: olcut MESAFE DEGIL, IMA EDILEN HIZ.
                    #   Ilk surumde "35 m sicradi -> isinlandi" diyordum; oysa
                    #   o bir VERI BOSLUGUYDU: hedef 18 m/s giderken 1.8 s'lik
                    #   telemetri boslugu 33 m fark yapar ve bu NORMALDIR.
                    #   Mesafeye bakan koruma her orenekte tetiklenip hizi hic
                    #   guncellemiyordu -> tgt_v 18 yerine 2.3'e dusuyordu.
                    #   Gercek isinlanma = gecen sureyle ACIKLANAMAYAN atlama.
                    _atl = math.dist(raw, (est_x, est_y, est_z))
                    est_x, est_y, est_z = raw          # yeni konuma DEMIRLE
                    tgt_hdg_prev = None                # donus hizi da sifirlansin
                    tgt_omega = 0.0
                    t_last_fresh = now                 # fark ALMA
                    # hiz KORUNUR: hedef ayni ovalde 18 m/s ucmaya devam ediyor,
                    # sifirlamak onden kestirmeyi gereksiz yere kaybettirirdi.
                    print("[GPS] ⚠ HEDEF ISINLANDI %.1f m / %.2f s -> kestirici "
                          "demirlendi (hiz korundu %.1f m/s)"
                          % (_atl, (now - t_last_fresh) if t_last_fresh else -1,
                             math.hypot(vel_x, vel_y)))
                else:
                    a = cfg.POS_EMA
                    nx = a * raw[0] + (1 - a) * est_x
                    ny = a * raw[1] + (1 - a) * est_y
                    nz = a * raw[2] + (1 - a) * est_z
                    if t_last_fresh is not None:
                        fdt = now - t_last_fresh
                        if 1e-3 < fdt < 2.0:
                            b = cfg.VEL_EMA
                            vel_x = b * ((nx - est_x) / fdt) + (1 - b) * vel_x
                            vel_y = b * ((ny - est_y) / fdt) + (1 - b) * vel_y
                            vel_z = b * ((nz - est_z) / fdt) + (1 - b) * vel_z
                            # IKINCI SAVUNMA: hedef fiziken bu hizi gecemez
                            # (olculen 17.99 m/s sabit). Herhangi baska bir yol
                            # kestirimi bozarsa burada kirpilir.
                            _sp = math.hypot(vel_x, vel_y)
                            if getattr(cfg, "SICRAMA_KORU", False) and _sp > cfg.HEDEF_HIZ_TAVAN:
                                _k = cfg.HEDEF_HIZ_TAVAN / _sp
                                vel_x *= _k
                                vel_y *= _k
                            vel_z = clamp(vel_z, -cfg.HEDEF_HIZ_TAVAN,
                                          cfg.HEDEF_HIZ_TAVAN)
                    est_x, est_y, est_z = nx, ny, nz
                # Hedefin AÇISAL HIZI (işaretli) — iç daire nişanı için.
                # Yalnız taze telemetride güncellenir; ara karelerde hız
                # değişmediği için burada hesaplamak zorunlu (her döngüde
                # hesaplansaydı taze olmayan karelerde 0'a sönerdi).
                if t_last_fresh is not None:
                    fdt2 = now - t_last_fresh
                    spd2 = math.hypot(vel_x, vel_y)
                    if 1e-3 < fdt2 < 2.0 and spd2 >= cfg.TRACK_MIN_SPD:
                        hdg = math.atan2(vel_y, vel_x)
                        if tgt_hdg_prev is not None:
                            dh = normalize_angle(hdg - tgt_hdg_prev)
                            w_ham = dh / fdt2
                            if abs(w_ham) < 3.0:      # gürültü ayıklama
                                a_w = cfg.IC_OMEGA_EMA
                                tgt_omega = a_w * w_ham + (1 - a_w) * tgt_omega
                        tgt_hdg_prev = hdg
                t_last_fresh = now
            else:
                none_count += 1
            status["none_count"] = none_count

            # ── 2) WARMUP / DROPOUT ──
            if est_x is None:
                _hover()
                status.update(durum="WARMUP", d_h=None, menzil=None)
                loop_count += 1
                _sleep(now, loop_period)
                continue
            if none_count * loop_period > cfg.HOLD_S:
                _hover()
                vx_prev = vy_prev = vz_prev = 0.0
                status.update(durum="DROPOUT")
                loop_count += 1
                _sleep(now, loop_period)
                continue

            # ── 3) HATA / MENZİL (hedef kestirimine göre) ──
            ex = est_x - ix
            ey = est_y - iy
            d_h = math.hypot(ex, ey)
            menzil = math.sqrt(ex * ex + ey * ey + (est_z - iz) ** 2)

            # ══ PUSU: bulusma noktasi secimi (bkz. Cfg.PUSU) ═════════════
            # Kapali (varsayilan) -> asagisi HIC calismaz, bit-ayni.
            _pusu = None            # (x, y, z, ux, uy, tgo, aspect)
            # ══ GOZLEM, EYLEMDEN AYRI (2026-08-21, olculdu) ═══════════════
            # ONCEDEN: besleme de eylem de ayni `cfg.PUSU` kapisinin
            # ardindaydi. Bu TAVUK-YUMURTA uretiyordu:
            #   * HedefTekrar hazir olmak icin MIN_GOZLEM_S kadar KESINTISIZ
            #     ornek ister (bir tam tur, ~30 s).
            #   * Ornekler yalnizca PUSU ACIKKEN toplanirdi.
            #   * PUSU acildigi an model BOS olur, hazir() False doner,
            #     cagiran eski davranisa duser -> pusu hicbir zaman
            #     ateslenemez.
            # CANLI KANIT (13 dk kosu, uzun_kosu.log):
            #     [PUSU-TANI] bayrak=False ... tk_periyot=None tk_kalite=None
            #                 tk_n=0 pusu=yok
            #   ve 1202 satirlik dort terminal logunda pusu_* sutunlarinin
            #   BESI DE tamamen bos.
            # ⚠ Ayrica yasa her GPS<->GORSEL gecisinde YENIDEN INSA ediliyor
            #   (13 dk'da 24 gecis; loglar 8.7-149 s arasi, ortanca 42.5 s).
            #   Tampon modul duzeyinde yasadigi icin (bkz. _pusu_takipci)
            #   yeniden insadan SAG CIKAR -- ama ancak DOLDURULUYORSA.
            # SIMDI: gozlem KAPISIZ. Eylem (asagisi) hala `cfg.PUSU`'ya bagli,
            # yani PUSU kapaliyken komut bit-ayni kalir; tek fark model
            # SICAK bekler ve acildigi anda kullanilabilir olur.
            # MALIYET: ekle() O(1) (deque); guncelle() pahali taramayi
            # YENIDEN_HESAP_S=2.0 s'den sik yapmaz -> 20 Hz yasada ihmal
            # edilebilir.
            # ⚠ MENZIL_MIN kapisi KORUNDU: cok yakinda kestirim gurultusu
            #   periyot taramasini bozar.
            if menzil >= cfg.PUSU_MENZIL_MIN:
                _tk.ekle(now, est_x, est_y, est_z)
                _tk.guncelle(now)
            if getattr(cfg, "PUSU", False) and menzil >= cfg.PUSU_MENZIL_MIN:
                if getattr(cfg, "PUSU_MOD", "aspect") == "kursun":
                    # KURSUN: kisa ufuk, aci taramasi YOK. Istasyon hedefin
                    # t_go sonraki yerinin arkasina kurulur (kirisi kes).
                    # ⚠ Kapanma SABIT alinir (olculen: duz ucusta 3.20 m/s).
                    #   Anlik dr/dt kullanmak DONUSTE +0.82'ye cikiyor ve
                    #   t_go'yu patlatiyordu; tavan zaten sinirliyor.
                    _kap = float(cfg.KURSUN_KAPANMA)
                    _tg = max(0.5, min(float(cfg.KURSUN_TGO_MAX), menzil / _kap))
                    _p = _tk.kestir(now + _tg)
                    _q = _tk.kestir(now + _tg + 0.5)
                    _pusu = None
                    if _p is not None and _q is not None:
                        _ux, _uy = _q[0] - _p[0], _q[1] - _p[1]
                        _un = math.hypot(_ux, _uy)
                        if _un >= 0.3:
                            _sap = math.hypot(_p[0] - est_x, _p[1] - est_y)
                            if _sap <= cfg.PUSU_SAPMA_MAX:
                                _rx, _ry = ix - _p[0], iy - _p[1]
                                _rn = math.hypot(_rx, _ry)
                                _a = (math.degrees(math.acos(clamp(
                                    (_rx * _ux / _un + _ry * _uy / _un) / _rn,
                                    -1.0, 1.0))) if _rn > 0.5 else 0.0)
                                _pusu = (_p[0], _p[1], _p[2],
                                         _ux / _un, _uy / _un, _tg, _a)
                else:
                    _pusu = _pusu_taahhutlu(_tk, now, ix, iy, cfg,
                                            est_x, est_y)
            status["pusu_tgo_s"] = _pusu[5] if _pusu else None
            status["pusu_aspect_deg"] = _pusu[6] if _pusu else None
            status["pusu_periyot_s"] = _tk.periyot
            status["pusu_kalite_m"] = _tk.kalite

            # ── 4) KADRAJ NOKTASI (istasyon): hedefin gerisi + altı ──
            #
            # SABİT METRE DEĞİL, SABİT AÇI (2026-08-01 dikey ıska düzeltmesi).
            # Eskiden ofset RANGE_SET'ten bir kez hesaplanıp sabit metre olarak
            # kullanılıyordu (d_behind 9.97 m, d_below 4.65 m). Ama sabit metre
            # kapanan menzilde sabit açı DEĞİLDİR — drone RANGE_SET'ten daha
            # yakına girdiğinde aynı 4.65 m giderek büyüyen bir LOS yükselişine
            # dönüşüyordu:
            #     menzil 11 m → 25° (kadraj merkezi, kamera tilt'i)
            #     menzil  8 m → 35°
            #     menzil  6 m → 51°
            #     menzil  4 m → >90°  (kadrajın DIŞI; üst sınır +80.2°)
            # Hedef kadrajın tepesinden çıkıyor, tespit kopuyor, drone altından
            # geçiyordu. Yani tasarım, korumak istediği görsel temasını yakın
            # menzilde kendi bozuyordu.
            #
            # Düzeltme: etkin standoff, menzil RANGE_SET'in altına inince onunla
            # birlikte küçülür. Böylece LOS yükselişi HER menzilde
            # ISTASYON_ELEV_DEG kalır. Uzakta (menzil ≥ RANGE_SET) davranış
            # AYNEN eskisi gibidir.
            # NOT: bu açı 2026-08-02'de kamera tilt'inden (CENTER_ELEV_DEG=25°)
            # AYRILDI ve 15°'ye indirildi — terminalin kapatması gereken dikey
            # mesafe aracın 1 m/s²'lik dikey ivme bütçesine sığmıyordu. Ayrıntı
            # ve ölçüm: Cfg.ISTASYON_ELEV_DEG.
            r_eff = min(menzil, cfg.RANGE_SET)
            # ── TERMINAL DIKEY KAPANMA (2026-08-17, OLCUMDEN) ─────────────
            # OLCULDU (27 yakin gecis, son 4 ucus kaydi):
            #     CPA aninda YATAY ayrim medyan 0.85 m   <- nisan ZATEN iyi
            #     CPA aninda DIKEY ayrim medyan 1.63 m   <- iskanin sebebi BU
            #     tek tek: yatay 0.08 / 0.10 / 0.14 m iken dikey 1.8-2.1 m
            # Ve bu bir kontrol hatasi DEGIL, AYAR: ISTASYON_ELEV 15 deg x
            # istasyon 6 m = hedefin 1.55 m ALTI. Olculen 1.63 ile birebir.
            # Yani hedefin altindan gecmeyi BILEREK istiyoruz; carpismayi
            # onlemek icin konmus bir pay, ama biz carpmak istiyoruz.
            #
            # COZUM: uzakta ofset AYNEN kalir (kamera nisani, guvenli yaklasma);
            # menzil TERM_DIKEY_M altina inince ofset YUMUSAKCA sifira suruluyor
            # -> son metrelerde hedefle es irtifaya gecilir.
            # Kesiklik yok: menzil=esikte carpan 1.0, menzil=0'da 0.0.
            # 0 = kapali (eski davranis).
            _td = float(getattr(cfg, "TERM_DIKEY_M", 0.0) or 0.0)
            _elev_eff = ist_elev
            if _td > 0.0 and menzil < _td:
                _elev_eff = ist_elev * clamp(menzil / _td, 0.0, 1.0)
            elev_etkin = _elev_eff          # ⚠ LOGA BU yazilmali, ist_elev DEGIL
            d_behind_eff = r_eff * math.cos(_elev_eff)
            d_below_eff = r_eff * math.sin(_elev_eff)

            tgt_spd_h = math.hypot(vel_x, vel_y)

            # Dönüş ölçeği (0=düz, 1=tam dönüş) — hem arka kısaltma hem iç
            # kayma bunu kullanır; hedef yavaşsa ω kestirimi güvenilmez → 0.
            olcek_don = 0.0
            if tgt_spd_h >= cfg.TRACK_MIN_SPD:
                olcek_don = min(1.0, abs(tgt_omega) / cfg.IC_OMEGA_REF)

            if tgt_spd_h >= cfg.TRACK_MIN_SPD:
                bx, by = -vel_x / tgt_spd_h, -vel_y / tgt_spd_h   # hız yönünün gerisi (kuyruk)
            elif d_h > 1e-6:
                bx, by = -ex / d_h, -ey / d_h                     # LOS gerisi (drone tarafı)
            else:
                bx, by = 0.0, 0.0
            # ── ARKA KISALTMA (bkz. Cfg.ARKA_KISALT): dönüşte arka bileşen
            # ω ölçeğiyle erir → istasyon kuyruktan yana (içeri) kayar.
            d_arka = d_behind_eff * (1.0 - cfg.ARKA_KISALT * olcek_don)
            # TERMINAL YATAY KAPANMA (bkz. Cfg.TERM_YATAY_M): terminal
            # menzilde arka ofseti sifira sur -> istasyon hedefin USTUNE
            # gelir, kovalanan hata buyur, kapanma gercekten olur.
            _ty = float(getattr(cfg, "TERM_YATAY_M", 0.0) or 0.0)
            if _ty > 0.0 and menzil < _ty:
                d_arka *= clamp(menzil / _ty, 0.0, 1.0)
            # ⚠ PUSU acikken capa hedefin GELECEKTEKI yeri, "arka" yonu de
            #   O ANDAKI kursundan alinir (simdiki kurstan DEGIL -- yoksa
            #   istasyon anlamsiz yere duser). Kapali -> bit-ayni.
            if _pusu is not None:
                _cx, _cy, _cz, _cux, _cuy = _pusu[0], _pusu[1], _pusu[2], _pusu[3], _pusu[4]
                _bx, _by = -_cux, -_cuy
                # PUSU_ARKA: kesme gecisinde standoff'u kis (bkz. Cfg.PUSU_ARKA)
                d_arka *= float(getattr(cfg, "PUSU_ARKA", 1.0))
            else:
                _cx, _cy, _cz = est_x, est_y, est_z
                _bx, _by = bx, by
            st_x = _cx + _bx * d_arka
            st_y = _cy + _by * d_arka
            st_z = _cz + d_below_eff                              # NED: altında (+z aşağı)

            # ── İÇ DAİRE KAYMASI (bkz. Cfg.IC_KAYMA; varsayılan 0 = kapalı) ──
            # Merkezcil yön: hız birim vektörünün dönüş yönünde 90°'si.
            # NED'de (x kuzey, y doğu) başlık atan2(vy,vx) ARTARKEN hız vektörü
            # x'ten y'ye döner; o dönüşün merkezi (-v̂y, +v̂x) yönündedir.
            # İşaret tgt_omega'dan gelir → sağa ve sola dönüşte doğru taraf.
            ic_kayma = 0.0
            ic_yaricap = None
            if tgt_spd_h >= cfg.TRACK_MIN_SPD:
                olcek = olcek_don
                if cfg.IC_ORAN > 0.0:
                    # YARIÇAP-ORANLI: R = |v| / |ω|. Dar dairede küçük, geniş
                    # dairede büyük kayma → tek katsayı her yarıçapta doğru.
                    if abs(tgt_omega) > 1e-6:
                        ic_yaricap = tgt_spd_h / abs(tgt_omega)
                        if ic_yaricap >= cfg.IC_R_MIN:
                            ic_kayma = min(cfg.IC_ORAN * ic_yaricap,
                                           cfg.IC_KAYMA_MAX) * olcek
                else:
                    # SABİT METRE (uçuşta doğrulanmış varsayılan)
                    ic_kayma = cfg.IC_KAYMA * olcek
                if ic_kayma > 1e-6:
                    vhx, vhy = vel_x / tgt_spd_h, vel_y / tgt_spd_h
                    isaret = 1.0 if tgt_omega >= 0 else -1.0
                    cx_, cy_ = -vhy * isaret, vhx * isaret     # merkeze doğru
                    st_x += cx_ * ic_kayma
                    st_y += cy_ * ic_kayma
            if -st_z < cfg.LOOKUP_MIN_ALT:                        # yere çakılma koruması
                st_z = -cfg.LOOKUP_MIN_ALT

            # ── 4b) DÖNÜŞ İLERİ BESLEMESİ: v_ist = v_hedef + ω × r ──
            # r = hedef→istasyon; +90° dönüşü ω>0'da (−ry, rx) (IC ile aynı
            # konvansiyon). Düz uçuşta ω≈0 → düzeltme 0. Bkz. Cfg.FF_DONUS.
            ff_x, ff_y = vel_x, vel_y
            ff_donus_mps = 0.0
            if (cfg.FF_DONUS and tgt_spd_h >= cfg.TRACK_MIN_SPD
                    and abs(tgt_omega) > 1e-6):
                rx_, ry_ = st_x - est_x, st_y - est_y
                dvx = tgt_omega * (-ry_)
                dvy = tgt_omega * rx_
                ff_donus_mps = math.hypot(dvx, dvy)
                if ff_donus_mps > cfg.FF_DONUS_MAX:
                    olc_ = cfg.FF_DONUS_MAX / ff_donus_mps
                    dvx *= olc_
                    dvy *= olc_
                    ff_donus_mps = cfg.FF_DONUS_MAX
                ff_x += dvx
                ff_y += dvy

            # ── 5) EMA TÜREV (istasyona hata) ──
            ex_cmd, ey_cmd, ez_cmd = st_x - ix, st_y - iy, st_z - iz
            e_now = (ex_cmd, ey_cmd, ez_cmd)
            if e_prev is not None and t_prev_deriv is not None:
                ddt = now - t_prev_deriv
                if ddt > 1e-3:
                    a = cfg.DERIV_EMA
                    for i in range(3):
                        de[i] = (1 - a) * de[i] + a * (e_now[i] - e_prev[i]) / ddt
            e_prev, t_prev_deriv = e_now, now

            # ── 6) HIZ KOMUTU: istasyon-hızı FF + PD ──
            # ⚠ 2026-08-17 GECE — ILERI BESLEME KORUMASI (FF_KORU)
            # ESKI HALI: vx = ff + PD, sonra TOPLAM V_MAX'a kirpiliyordu.
            # Kirpma TEK BIR olcekle yapildigi icin ileri beslemeyi (hedefin
            # hizini) da ayni oranda kisiyordu. OLCULEN SONUC:
            #   menzil 40 m -> istasyon hatasi ~33 m -> PD = 0.8*33 = 26 m/s
            #   ff = 18 m/s  ->  toplam 44  ->  22'ye kirpilinca olcek 0.50
            #   -> ff FIILEN 9 m/s'e duser, yani hedefin hizinin YARISI.
            # Komut yonu boylece "istasyona dogru" (saf takip) baskin hale
            # geliyordu. Gercek ucusta olculen kurs hatasi medyan 16.8°;
            # carpisma rotasi icin gereken onalma 43°. Aradaki fark kerterizi
            # yaklasma boyunca 103° dondurup hedefi kadrajdan atiyordu.
            # YENI HALI: ff ASLA kisilmaz (hedefin hizini her zaman esleriz),
            # yalniz DUZELTME terimi kalan yetkiye kirpilir. Bu yapisal olarak
            # "arkadan takip + hiz esleme" demektir ve asim uretmez.
            # KAPANMA_MIN, ff tek basina V_MAX'i doldurdugunda bile bir miktar
            # kapanma yetkisi birakir (aksi halde butce 0 olur ve hic yaklasmayiz).
            _pdx = cfg.KP_H * ex_cmd + cfg.KD_H * de[0]
            _pdy = cfg.KP_H * ey_cmd + cfg.KD_H * de[1]
            if getattr(cfg, "FF_KORU", True):
                _ffm = math.hypot(ff_x, ff_y)
                _butce = max(cfg.V_MAX - _ffm, float(getattr(cfg, "KAPANMA_MIN", 5.0)))
                _pm = math.hypot(_pdx, _pdy)
                if _pm > _butce and _pm > 1e-6:
                    _s = _butce / _pm
                    _pdx *= _s
                    _pdy *= _s
                vx = ff_x + _pdx
                vy = ff_y + _pdy
                _vmut = float(getattr(cfg, "V_MUTLAK_MAX", cfg.V_MAX + 6.0))
                vmag = math.hypot(vx, vy)
                if vmag > _vmut and vmag > 1e-6:
                    s = _vmut / vmag
                    vx *= s
                    vy *= s
            else:
                vx = ff_x + _pdx
                vy = ff_y + _pdy
                vmag = math.hypot(vx, vy)
                if vmag > cfg.V_MAX and vmag > 1e-6:
                    s = cfg.V_MAX / vmag
                    vx *= s
                    vy *= s
            vz = clamp(vel_z + cfg.KP_Z * ez_cmd, -cfg.VZ_MAX, cfg.VZ_MAX)

            # ══ TERMINAL KAPANMA TABANI (bkz. Cfg.TERM_KAPANMA_M) ═══════
            # Komut edilen menzil degisim hizi:
            #     dr/dt = (v_hedef - v_komut) · u        (u: drone->hedef)
            # Negatifse yaklasiyoruz. Terminal menzilde bunu en az
            # -TERM_KAPANMA_MPS yapacak kadar LOS yonunde bilesen eklenir.
            # Yanal terime DOKUNULMAZ: yalniz eksik kapanma tamamlanir.
            term_kap = 0.0
            _tkm = float(getattr(cfg, "TERM_KAPANMA_M", 0.0) or 0.0)
            if _tkm > 0.0 and menzil < _tkm and menzil > 0.3:
                _ux = ex / menzil
                _uy = ey / menzil
                _uz = (est_z - iz) / menzil
                _rdot = ((vel_x - vx) * _ux + (vel_y - vy) * _uy
                         + (vel_z - vz) * _uz)
                _ist = -float(getattr(cfg, "TERM_KAPANMA_MPS", 4.0))
                if _rdot > _ist:                 # yeterince kapanmiyoruz
                    term_kap = _rdot - _ist      # >0: eklenecek kapanma
                    vx += term_kap * _ux
                    vy += term_kap * _uy
                    vz = clamp(vz + term_kap * _uz, -cfg.VZ_MAX, cfg.VZ_MAX)
                    _vmut2 = float(getattr(cfg, "V_MUTLAK_MAX", cfg.V_MAX + 6.0))
                    _vm2 = math.hypot(vx, vy)
                    if _vm2 > _vmut2 and _vm2 > 1e-6:
                        _s2 = _vmut2 / _vm2
                        vx *= _s2
                        vy *= _s2
            status["term_kap_mps"] = round(term_kap, 2)

            # ── 7) YAW: burun GERÇEK hedefe ──
            bearing = math.atan2(ey, ex)
            # KERTERIZ EMA (bkz. Cfg.KERTERIZ_EMA) -- aci sarmasina dayanikli
            _ka = float(getattr(cfg, "KERTERIZ_EMA", 1.0) or 1.0)
            if _ka < 0.999:
                if bearing_f is None:
                    bearing_f = bearing
                else:
                    bearing_f = normalize_angle(
                        bearing_f + _ka * normalize_angle(bearing - bearing_f))
                bearing = bearing_f
            if cmd_yaw is None:
                # ⚠ FAZ GİRİŞİNDE ARACIN MEVCUT YÖNÜNDEN BAŞLA (2026-08-08).
                # Eskiden doğrudan `bearing` atanıyordu; görsel fazdan sonra
                # GPS'e dönüldüğünde hedef genelde ARKADA kalıyor ve bu, tek
                # karede 100-160°'lik bir yaw KOMUT SIÇRAMASI demek oluyordu.
                # Ölçüldü: 12 faz girişinin 6'sında sıçrama >60° (en büyük 160°).
                # Araç bu adımı yakalamak için yaw'ı doyuruyor, motorlar yaw
                # torkuna gidince roll/pitch yetkisi kalmıyor ve TAKLA atıyor
                # (8 koşuluk veri: takla YAŞANMAYAN 2 koşunun İKİSİ de ilk
                # denemede vurdu; takla yaşanan 3 koşuda 1 vuruş).
                # Mevcut yaw'dan başlayınca YAW_RATE_MAX (120°/s) devreye
                # girer ve komut hedefe yumuşak yürür. Normal takipte fark
                # YOK: burun zaten hedefteyken mevcut yaw ≈ bearing.
                cmd_yaw = iyaw
            yaw_err = normalize_angle(bearing - cmd_yaw)
            if abs(yaw_err) > cfg.YAW_DEADBAND:
                step = clamp(yaw_err, -cfg.YAW_RATE_MAX * dt, cfg.YAW_RATE_MAX * dt)
                cmd_yaw = normalize_angle(cmd_yaw + step)

            # ── 8) İVME SINIRI + GÖNDER ──
            if getattr(cfg, "ACCEL_SPLIT", False):
                vx, vy, vz = limit_acceleration_split(
                    vx, vy, vz, vx_prev, vy_prev, vz_prev,
                    cfg.MAX_ACCEL, float(getattr(cfg, "MAX_ACCEL_V", 10.0)), dt)
            else:
                vx, vy, vz = limit_acceleration(
                    vx, vy, vz, vx_prev, vy_prev, vz_prev, cfg.MAX_ACCEL, dt)
            # ══ KOMUT YON TAVANI (bkz. Cfg.KOMUT_YON_TAVAN) ═════════════
            # Yatay komut vektorunun YONU, bir onceki komuta gore en fazla
            # tavan*dt kadar donebilir. Buyukluk korunur.
            yon_kirp = 0.0
            _yt = float(getattr(cfg, "KOMUT_YON_TAVAN", 0.0) or 0.0)
            if _yt > 0.0 and dt > 0.0:
                _m_yeni = math.hypot(vx, vy)
                _m_onc = math.hypot(vx_prev, vy_prev)
                if _m_yeni > 0.5 and _m_onc > 0.5:
                    _a_onc = math.atan2(vy_prev, vx_prev)
                    _a_yeni = math.atan2(vy, vx)
                    _d = normalize_angle(_a_yeni - _a_onc)
                    _lim = math.radians(_yt) * dt
                    if abs(_d) > _lim:
                        yon_kirp = math.degrees(abs(_d) - _lim) / dt
                        _a = _a_onc + (_lim if _d > 0 else -_lim)
                        vx = _m_yeni * math.cos(_a)
                        vy = _m_yeni * math.sin(_a)
            status["yon_kirp_deg"] = round(yon_kirp, 1)
            vx_prev, vy_prev, vz_prev = vx, vy, vz
            send_velocity(conn, vx, vy, vz, cmd_yaw)

            # ── 9) KADRAJ HATASI (başarı ölçütü) — gerçek attitude'la ──
            kad = hedef_kadraj_hatasi((est_x, est_y, est_z), (ix, iy, iz),
                                      iroll, ipitch, iyaw)

            # ── 9b) ANGAJMAN GEOMETRISI (görsel devir kapısı için) ──────────
            # ÖLÇÜLDÜ 2026-08-15 (bbox_ibvs_20260815_151957.csv): görsel faz
            # 1.53 s sürdü ve hedef kadrajdan YANDAN çıktı — cy sabit kaldı
            # (184..207) ama eps_yaw 0° → 61°'ye (=HFOV/2) fırladı. Aracın
            # gerçek dönüş hızı max 94.6°/s, hatanın büyüme hızı max 105.4°/s
            # → araç fiziksel olarak yetişemiyor, bu bir kontrol hatası değil.
            #
            # Sebep GEOMETRİ: yandan geçen hedefte LOS açısal hızı
            #     ω = v_dik / menzil
            # ve menzil küçüldükçe ω patlar. Tail-chase'te (hedef bizden UZAKA
            # uçuyorsa) v_dik ≈ 0 olur ve ω her menzilde küçük kalır.
            #
            # aspect_deg : hedefin HIZ VEKTÖRÜ ile LOS arasındaki açı
            #     0°   = hedef tam bizden uzaklaşıyor  (mükemmel kuyruk takibi)
            #     90°  = yandan geçiş                  (en kötü)
            #     180° = kafa kafaya
            # omega_los_deg : ŞU ANKİ LOS açısal hızı (°/s)
            # omega_term_deg: 5 m terminal menzilde BEKLENEN ω (°/s) —
            #     asıl karar bunun üzerinden verilmeli, çünkü ω menzille büyür.
            # HEDEFIN KENDI DONUS HIZI (°/s) — "su an duz mu ucuyor?"
            # NEDEN: hedefin yolunun %52'si DUZ (olculdu: oval pist, 530 m tur).
            # Duz kisimda LOS acisal hizi lambda_dot ~ 0 olur; saf takibin
            # RAMPA girdiye kalici hatasi da orada YOKTUR. Gazebo ekibinin
            # %65 isabet aldigi kosul tam budur (duz ucan hedef); dairede
            # onlar da 62 angajmanda 0 isabet aliyor.
            # => Devri hedefin DUZ kismina denk getirmek, yasayi degistirmeden
            #    problemi Gazebo'nun cozulmus rejimine tasir.
            # ⚠ KURAL: bu hesap GPS FAZINDA yapiliyor ve hedefin konumunu
            #    kullaniyor -- yarisma kurali GPS'i yalnizca GORSEL FAZ
            #    boyunca yasakliyor, GPS fazinda serbest.
            try:
                _hd = math.atan2(vel_y, vel_x)
                _p = _hdg_gecmis[0] if _hdg_gecmis else None
                if _p is not None and now - _p[1] > 0.15:
                    _d = (_hd - _p[0] + math.pi) % (2 * math.pi) - math.pi
                    _w = math.degrees(_d / (now - _p[1]))
                    _prev = status.get("hedef_donus_deg")
                    # EMA: ham turev gurultulu, 0.3 ile yumusatiliyor
                    status["hedef_donus_deg"] = round(
                        _w if _prev is None else 0.3 * _w + 0.7 * _prev, 1)
                    _hdg_gecmis[:] = [(_hd, now)]
                elif _p is None:
                    _hdg_gecmis[:] = [(_hd, now)]
            except Exception:
                pass

            try:
                _lr = math.hypot(ex, ey)
                _vh = math.hypot(vel_x, vel_y)
                if _lr > 0.1 and _vh > 0.1:
                    _lx, _ly = ex / _lr, ey / _lr        # LOS birim (biz->hedef)
                    _vpar = vel_x * _lx + vel_y * _ly    # LOS boyunca bileşen
                    _vdik = abs(vel_x * _ly - vel_y * _lx)   # LOS'a DİK bileşen
                    _asp = math.degrees(math.atan2(_vdik, _vpar))
                    status["aspect_deg"] = round(_asp, 1)
                    # ⚠ DEVIR GEOMETRI KAPISININ girdisi. Olculdu (713 devir):
                    #   hedef <3 °/s donerken devir -> en yakin 3.40 m (%44 <3m)
                    #   hedef >15 °/s donerken devir -> en yakin 7.54 m (%7)
                    #   Menzil kusagi sabitken de duruyor -> kafa karisikligi degil.
                    status["hedef_donus_deg"] = round(math.degrees(tgt_omega), 1)
                    status["omega_los_deg"] = round(math.degrees(_vdik / max(_lr, 0.5)), 1)
                    status["omega_term_deg"] = round(math.degrees(_vdik / 5.0), 1)
                else:
                    status["aspect_deg"] = None
                    status["omega_los_deg"] = None
                    status["omega_term_deg"] = None
                    status["hedef_donus_deg"] = round(math.degrees(tgt_omega), 1)
            except Exception:
                status["aspect_deg"] = None
                status["omega_los_deg"] = None
                status["omega_term_deg"] = None
                status["hedef_donus_deg"] = round(math.degrees(tgt_omega), 1)

            # ── 10) DURUM ──
            durum = "KILIT" if d_h < cfg.HANDOFF_RANGE else "ARAMA"
            status.update(durum=durum, d_h=round(d_h, 1), menzil=round(menzil, 1),
                          kadraj_yaw_deg=round(math.degrees(kad["yaw_hata"]), 1),
                          kadraj_elev_deg=round(math.degrees(kad["elev"]), 1),
                          # SALT GOZLEM (2026-08-17, algi surekliligi): hedefin
                          # TRUTH'tan projekte edilmis piksel konumu. supervisor
                          # bunu karar loguna yazar; boylece "dedektorun verdigi
                          # kutu GERCEKTEN hedef mi, yoksa yanlis pozitif mi"
                          # sorusu AYNI KAREDE, ayri log eslestirmesi olmadan
                          # olculebilir hale gelir (dusuk-conf esigi tartismasi).
                          # ⛔ GORSEL FAZA GECMEZ: bunu yalniz supervisor'in GPS
                          # fazi okur; bbox_ibvs status'e bakmaz (D0 garantisi).
                          u_px_truth=(round(kad["u"], 1)
                                      if kad.get("u") is not None else None),
                          v_px_truth=(round(kad["v"], 1)
                                      if kad.get("v") is not None else None),
                          tgt_vx=round(vel_x, 2), tgt_vy=round(vel_y, 2),
                          tgt_vz=round(vel_z, 2))

            _ps = None
            if _pusu is not None:
                _ps = round(math.hypot(_pusu[0] - est_x, _pusu[1] - est_y), 1)
            w.writerow({
                "pusu_tgo_s": round(_pusu[5], 2) if _pusu else None,
                "pusu_aspect_deg": round(_pusu[6], 1) if _pusu else None,
                "pusu_sapma_m": _ps,
                "pusu_periyot_s": (round(_tk.periyot, 2)
                                   if _tk.periyot is not None else None),
                "pusu_kalite_m": (round(_tk.kalite, 2)
                                  if _tk.kalite is not None else None),
                "t": round(now, 3), "dt": round(dt, 4), "durum": durum,
                "d_h": round(d_h, 2), "menzil": round(menzil, 2),
                # HAM telemetri (EMA'dan önce) + ona olan mesafe + filtre gecikmesi
                "tgt_ham_x": round(raw[0], 2), "tgt_ham_y": round(raw[1], 2),
                "tgt_ham_z": round(raw[2], 2),
                "menzil_ham": round(math.sqrt((raw[0] - ix) ** 2 + (raw[1] - iy) ** 2
                                              + (raw[2] - iz) ** 2), 2),
                "kestirim_gecikme_m": round(math.sqrt((raw[0] - est_x) ** 2
                                                      + (raw[1] - est_y) ** 2
                                                      + (raw[2] - est_z) ** 2), 2),
                "tgt_x": round(est_x, 2), "tgt_y": round(est_y, 2), "tgt_z": round(est_z, 2),
                "tgt_vx": round(vel_x, 2), "tgt_vy": round(vel_y, 2), "tgt_vz": round(vel_z, 2),
                "iris_x": round(ix, 2), "iris_y": round(iy, 2), "iris_z": round(iz, 2),
                "iris_roll_deg": round(math.degrees(iroll), 1),
                "iris_pitch_deg": round(math.degrees(ipitch), 1),
                "iris_yaw_deg": round(math.degrees(iyaw), 1),
                "st_x": round(st_x, 2), "st_y": round(st_y, 2), "st_z": round(st_z, 2),
                "vx_cmd": round(vx, 2), "vy_cmd": round(vy, 2), "vz_cmd": round(vz, 2),
                "yaw_cmd_deg": round(math.degrees(cmd_yaw), 1),
                "kadraj_yaw_deg": round(math.degrees(kad["yaw_hata"]), 2),
                "kadraj_elev_deg": round(math.degrees(kad["elev"]), 2),
                "kadraj_pitch_hata_deg": round(math.degrees(kad["pitch_hata"]), 2),
                "u_px": round(kad["u"], 1) if kad["u"] is not None else "",
                "v_px": round(kad["v"], 1) if kad["v"] is not None else "",
                # ⚠ ETKIN deger yazilir: TERM_DIKEY_M yakinda ofseti sifira
                #   surer ve ist_elev degismeden kalir -> eskisi logda
                #   mekanizmanin CALISTIGINI GIZLIYORDU.
                "ist_elev_deg": round(math.degrees(
                    locals().get("elev_etkin", ist_elev)), 2),
                "ff_donus_mps": round(ff_donus_mps, 2),
                "d_arka_m": round(d_arka, 2),
                # ⚠ DEVIR KAPISININ MEKANIZMA KAPISI. Once yalniz `status`'e
                #   yazmistim ve CSV sutunu BOS kaldi (0/228) -- yani kapiyi
                #   acsam "gercekten calisti mi" diye bakacak sinyal yoktu.
                #   `status` ile CSV AYRI sozluklerdir; ikisine de yazilmali.
                "hedef_donus_deg": round(math.degrees(tgt_omega), 2),
                "aspect_deg": status.get("aspect_deg"),
                "term_kap_mps": locals().get("term_kap", 0.0),
                "yon_kirp_deg": locals().get("yon_kirp", 0.0),
            })
            f.flush()

            loop_count += 1
            # ── PUSU TANI (AVCI_GPS_PUSU_TANI=1 ile acilir; varsayilan KAPALI).
            #    PUSU'nun neden atesmedigini bu satirlar ortaya cikardi:
            #    tampon 2/4/7/11/33 -> surekli sifirlaniyordu (SICRAMA_HIZ).
            if (_env_f("AVCI_GPS_PUSU_TANI", 0.0) >= 0.5
                    and loop_count % int(cfg.LOOP_HZ * 5) == 0):
                try:
                    print("[PUSU-TANI] bayrak=%s mod=%s menzil=%.1f min=%.1f "
                          "tk_periyot=%s tk_kalite=%s tk_n=%s pusu=%s"
                          % (getattr(cfg, "PUSU", None),
                             getattr(cfg, "PUSU_MOD", None), menzil,
                             getattr(cfg, "PUSU_MENZIL_MIN", -1),
                             getattr(_tk, "periyot", "YOK"),
                             getattr(_tk, "kalite", "YOK"),
                             len(getattr(_tk, "_buf", []) or []),
                             "VAR" if _pusu else "yok"), flush=True)
                except Exception as _e:
                    print("[PUSU-TANI] hata: %r" % (_e,), flush=True)
            if loop_count % int(cfg.LOOP_HZ * 3) == 0:
                print(f"[GPS] {durum} d_h={d_h:.1f}m menzil={menzil:.1f}m "
                      f"kadraj(yaw={math.degrees(kad['yaw_hata']):+.0f}°,"
                      f"elev={math.degrees(kad['elev']):+.0f}°/istasyon {math.degrees(ist_elev):.0f}°) "
                      f"v=({vx:+.1f},{vy:+.1f},{vz:+.1f}) tgt_v={tgt_spd_h:.1f}")

            _sleep(now, loop_period)

        send_velocity(conn, 0.0, 0.0, 0.0, cmd_yaw or 0.0)
        status.update(durum="DURDU")
        print("[GPS] Stop sinyali — döngü sonlandı.")
    finally:
        # ── kestirim durumunu SAKLA (bkz. FAZ GECISINDE SURDURME) ──
        # Yalniz gecerli kestirim saklanir; est_x None ise saklanacak bir sey
        # yoktur ve eski (bayat) kayit da TEMIZLENIR.
        try:
            if est_x is not None and est_y is not None:
                _GPS_SURDUR.clear()
                _GPS_SURDUR.update(
                    t_kayit=time.monotonic(),
                    est=(est_x, est_y, est_z),
                    vel=(vel_x, vel_y, vel_z),
                    hdg=tgt_hdg_prev, omega=tgt_omega,
                    pitch_ema=pitch_ema, bearing_f=bearing_f, cmd_yaw=cmd_yaw)
            else:
                _GPS_SURDUR.clear()
        except Exception:
            _GPS_SURDUR.clear()
        f.close()
        print(f"[GPS] log kapatıldı: {csv_yol}")


def _sleep(t_start, period):
    elapsed = time.monotonic() - t_start
    if elapsed < period:
        time.sleep(period - elapsed)

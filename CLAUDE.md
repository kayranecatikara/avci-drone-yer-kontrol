# Avcı Drone — Proje Notları (CLAUDE.md)

## KAPSAM
Proje **yalnızca iki şeyden** ibarettir: **GPS takip** (bozuk GNSS ile hedefin
kuyruğundaki istasyona oturma) ve **görsel takip** (kamera ile IBVS güdüm).
Poz/PnP kestirimi, tune raporu, analiz araçları, kampanya/bekçi/kayıt
altyapısı, testler ve arşiv **yoktur** (kullanıcı kararı; git geçmişinde
`main` branch'inde durur).

**Görev `web/` üzerinden koşturulur** (2026-08-24 kararı; terminal giriş
noktası kaldırıldı):

```
python -m web.server        ->  http://127.0.0.1:8001
```

Arayüzün **iki modu** vardır ve ikisi de aynı `control/` kodunu çağırır:

| mod | ne koşar | kamera |
|---|---|---|
| **GPS** | kalkış → GPS fazı (istasyon tutma) | hiç açılmaz, dedektör yüklenmez |
| **HİBRİT** | kalkış → GPS fazı → devir kapısı → görsel faz | açık; komut görsel fazda yalnız kameradan |

Arayüz **güdüm yasası içermez ve komut üretmez**: yasayı `control/` üretir,
arayüz döngüyü koşturur, gösterir ve tetikler. Ortada kuşbakışı harita,
yanlarda telemetri ve başlat/durdur vardır; **ekran paylaşımı/kamera görüntüsü
YOKTUR** (hibrit modda kamera hattı ekranı yakalar ama görüntü arayüze
akmaz — yalnızca tespit sayıları gösterilir).

⚠ `control/main.py` artık **yalnızca faz geçişidir** (`PhaseSupervisor`): komut
üretmez, döngü tutmaz, giriş noktası değildir. `python -m control.main`
**çalışmaz**. Kapı eşikleri (TAKEOFF_ALT_M, HANDOFF_FRAMES, HANDOFF_STATION_ERR_M,
LOST_S...) orada tek yerde durur; koşturucu değişse de kapı değişmez.

Simülasyon ortamı bir **Unreal Engine oyunudur** (Drones of War). Gazebo,
MAVLink, ArduPilot SITL gibi katmanlar bu projede **YOKTUR** ve eklenmez;
araç I/O'su `sdk/drone_sdk.py` (resmi yarışma SDK'sı, TCP) üzerinden gider.

---

## MİMARİ

Güdüm artık **üç katmandır** ve katmanlar birbirine dokunmadan değiştirilebilir:

```
YASA (m/s hız setpoint'i)     ->  ÇEVİRİCİ (ölçülmüş zarf)  ->  KOMUT KAPISI
control/takeoff.py                common.VelocityToStick        common.CommandSender
control/gps_approach.py
control/visual_tracking.py

hangi yasa koşacak?           ->  control/main.py :: PhaseSupervisor   (KAPI)
döngü / telemetri / tetik     ->  web/server.py                        (KOŞTURUCU)
bozuk GNSS -> temiz hedef+hız ->  filter/gnss_filtre_v2.py (CT-EKF, yalnız GPS fazı)

kare -> kutu                  ->  perception/camera.py  (ÜRETİCİ + TÜKETİCİ, 2 thread)
```

**Kamera hattı iki iş parçacığıdır** (2026-08-24). Üretici kaynaktan sürekli
kare çeker ve `_latest`'te **yalnız en tazesini** tutar; tüketici oradan okur,
YOLO + takipçi koşturur, `detection_state`'e yayınlar. Aradaki kareler bilerek
düşer (`camera.status()["dropped"]` sayar): güdüm için bir kare gecikmek,
kuyruktan **bayat** kare tüketmekten iyidir.

⭐ **NEDEN AYRI THREAD (ölçüldü).** Senkron hatta toplam = yakalama + çıkarım;
ayrı thread'de toplam = `max(yakalama, çıkarım)`. Simülasyonda 29.9 → **53.2
FPS**, kare yaşı çıkarıma girerken 0.0–7.7 ms. Gerçek kamerada fark daha
büyüktür: `cv2.VideoCapture.read()` bir **sonraki** kareyi bekler (ölçüldü:
32.00 ms @30 fps) ve senkron döngüde bu süre tamamen ölü beklemedir.

⛔ **BAYAT KARE — capture kartların klasik tuzağı.** Sürücü kuyruğunda bekleyen
kare `read()`'te **anında** döner (ölçüldü: 0.1 ms; gerçek yeni kare bir kare
periyodu bekletir). Güdüm onu taze sanıp bir periyot eski görüntüyle komut
üretir. İki katmanlı önlem: (1) **yapısal** — üretici sürekli okur, kuyruk hiç
birikemez; (2) açılışta ve her duraklama sonrası `DeviceSource.drain()`
kuyruğu boşaltır. `CAP_PROP_BUFFERSIZE=1` de denenir ama backend'ler sessizce
yok sayabilir (DSHOW'da `-1` okundu) → **tek başına güvenilmez**.

**Neden.** DoW SDK'sı yalnızca kumanda çubuğu (-1..+1) kabul eder; arada
ArduPilot'un `AC_PosControl`'ü gibi bir hız/konum kontrolcüsü **yoktur**.
Eski sürümümüz bu boşluğu görmezden gelip PD çıktısını **doğrudan çubuğa**
yazıyordu (`KP_H`, `KP_Z`, `ILERI*fren`...) — yani aracın ölçülmüş zarfını
(asimetrik dikey, iki kollu throttle haritası, ivme tavanı) hiç bilmiyordu.
Eksik katman `VelocityToStick`'dir ve sabitleri **ölçüldü**.

### Ölçülmüş araç zarfı (`control/common.py :: ConverterCfg`)
| büyüklük | değer |
|---|---|
| yatay hız tavanı | 34.6 m/s |
| tırmanma tavanı | +33.51 m/s |
| **alçalma tavanı** | **−6.95 m/s (4.8 KAT asimetrik)** |
| yatay ivme | 34–39 m/s² (tam çubuk) |
| yatış zaman sabiti | 0.211 s |
| ölü zaman | 46 ms |
| yaw tavanı | 214 °/s (biz 120'de tutuyoruz) |

⭐ **ZARF TEK KAYNAKTA.** `VZ_MAX_CLIMB`, `VZ_MAX_DESCENT` ve `YAW_RATE_MAX`
yalnızca `ConverterCfg`'de tanımlıdır; `GPSCfg` ve `VisualCfg` oradan **okur**.
Üçe kopyalandıkları sürümde tırmanma tavanı 33.51 / 33.5 / 33.5 diye **zaten
kaymıştı**. Bu üç ada elle sayı yazmayın.

⛔ **THROTTLE MAYINI.** `thr = -0.001` → **+9.31 m/s TIRMANMA**, `thr = 0.000`
→ +0.88 m/s. Yani "eksi binde bir" irtifa tutmaz, 9 m/s tırmandırır. Nötr
throttle **`HOVER_THR = -0.586`**'dır (orada ölçülen vz = −0.235 m/s).
Eski koddaki "kaçak tırmanma"nın kök nedeni tam olarak buydu.
`CommandSender.loiter()` bu yüzden 0 değil `HOVER_THR` gönderir.

⛔ **YANAL EKSEN İŞARETİ ÖLÇÜLDÜ** (`Y_SIGN = -1`). Unreal sol-ellidir;
sağ-elli dönüşüm yanal komutu ters yöne gönderir, hata büyür, roll ±1'e
çakılır ve araç hedefe gitmek yerine daire çizer.

⚠ **EĞİM SINIRI TEK YERDE** (`CommandSender.MAX_DELTA = 0.15`). Çevirici de
sınırlarsa iki sönümleme üst üste biner; aracın yatışı zaten 0.211 s ile
yumuşuyor.

⚠ **BİRİM SINIRI TEK YERDE** (`common.Telemetry`). SDK cm/derece verir, yasalar
m/(m/s) ile çalışır. `control/` içinde bu sınıfın dışında `*0.01` görülmemeli
(tek istisna: `gps_approach.clean_target`, çünkü GNSS filtresi cm alanında
çalışır ve sınır orada açıkça geçilir).

---

## DOKUNULMAZ
- `Drones of War Teknofest/` — oyun paketi (gitignore'lu, repoya konmaz).
- `sdk/` — resmi yarışma SDK'sı. **Değiştirilmez.** (`drones_of_war_entegrasyon`
  ile bayt bayt aynıdır, yalnız satır sonları farklı.)

---

## ⛔ KATI KURAL — GÖRSEL FAZDA GPS/GNSS YASAK (diskalifiye sebebi)
Görsel temas **sağlandıktan sonra** hareket komutu **yalnızca görsel veriden**
türetilir. Kural **yapısal** sağlanır: `VisualTracker.compute(det, own_att_deg,
own_vel_ms, dt)` imzasında hedefe ait tek veri **bbox pikselleri**dir;
konum/hız/GNSS kestirimi parametre olarak bile geçmez. `own_*` değerleri
**kendi IMU/hızımızdır** (ego-motion telafisi), hedef verisi değildir.

Koşturucu (`web/server.py`) görsel fazda yalnızca `brain.clean_target()`
çağırır; bu **hiçbir komuta girmez**, sadece faz geri dönerse filter ısınmış
olsun diyedir. `PhaseSupervisor.visual_tick` imzası da temizdir: hedefe ait tek
veri "kutu var mı yok mu"dur.
**Görsel güdüm için ASLA GPS/filtre tabanlı bir çözüm önerme.**

---

## GPS GÜDÜMÜNÜN ROLÜ (net sınır)
GPS fazı öldürücü faz değildir. Görevi: (1) bozuk GNSS'i temizle ve hedef
hızını kestir, (2) hedefin **kuyruğundaki istasyona** otur ve orada **kal**,
(3) hedefle kesintisiz görsel temas kur, (4) görsel faza temiz devret.
**Son yaklaşma (terminal faz) görsel fazın işidir**, GPS'in değil.

### İstasyon geometrisi — ÖLÇÜLDÜ (GK+GK2, 24 uçuş, dönüşümlü A/B)
Hedefin **8 m arkası, R×0.75 = 6 m altı**. Gerçek tespit oranı medyanı:

| istasyon | tespit | kutu | yanlış-pozitif |
|---|---|---|---|
| 15 m / 0.45 | %66.9 | 47.7 px | %11.4 |
| 8 m / 0.45 | %76.0 | 73.5 px | %4.0 |
| **8 m / 0.75** | **%88.8** | 69.3 px | **%3.7** ← seçildi |

Kolların aralıkları hiç örtüşmüyor. İki düğme **bağımsızdır**: MENZİL yalnız
kutu boyutunu, ORAN yalnız gök payını değiştirir (yükseliş açısı `atan(oran)`,
menzilden bağımsız). Gök payı büyüdükçe hedefin arka planı gökyüzü olur.

⭐ **İLERİ BESLEME ŞART** (`STATION_FEEDFWD`). Saf P kontrolcü hareketli hedefi
asla yakalayamaz: denge `e = V/Kp`'de kurulur (Kp=0.9, V=18 m/s → **20 m kalıcı
hata**). Ölçüldü: ileri beslemesiz sürümde menzil 100–255 m arası salındı ve
kapanma hızı medyan **−3.78 m/s** (uzaklaşıyordu).

⛔ **DÖNÜŞ İLERİ BESLEMESİ ELENDİ** (n=8/kol, havuzlanmış). Mekanizma çalıştı
(manevra %21→%34, hedef_w 3.7→8.6 °/s) ama sonuca dönüşmedi: temas 4/8→3/8,
istasyon hatası 6.46→8.19 m, roll p90 7.05→13.50°. Salınan araç, aynı sonucu
üretse bile kötüdür. Geri eklemeyin.

---

## GNSS FİLTRESİ — `filter/gnss_filtre_v2.py`

Klasör **`filter/` → `filter/`** oldu (içinde füzyon değil, filter var).
Aktif kestirici **`GNSSFilterV2`** (CT-EKF: durum `x, y, vx, vy, ω`):
Mahalanobis kapıları jammer sıçramasını istatistiksel reddeder, kapı üst üste
reddederse `P` şişirilip yeni rejime yeniden kilitlenilir (kaçış), kesintide
ölü-hesapla ileri gidilir (`dr_max_s=2.5 s`), çıkış `lead_s` kadar ileri
taşınarak ~1.13 s'lik GNSS gecikmesi kapatılır.

Önceki `GNSSFilter` (pencere tabanlı spike kapıları + lineer hız eğimi)
`filter/gnss_filtre.py`'de **duruyor ama çağrılmıyor**.

**Sentetik jammer testi** (120 s × 5 tohum, 50 cm gürültü, %4 sıçrama, 1.13 s
gecikme, hedef 18 m/s, düz→sağ dönüş→düz→sol dönüş; n=29900 tik/kol):

| ölçüt | ESKİ `GNSSFilter` | **YENİ `GNSSFilterV2`** |
|---|---|---|
| konum hatası medyan | 21.86 m | **3.15 m** (6.9×) |
| konum hatası p90 | 23.12 m | **7.60 m** |
| **hız hatası medyan** | 4.31 m/s | **0.43 m/s** (10×) |
| hız hatası p90 | 8.54 m/s | **1.30 m/s** |

Beş tohumun aralıkları hiç örtüşmüyor. Mekanizma: eskinin lead'i **güven
ağırlıklı** olduğu için gecikmeyi fiilen kapatmıyordu — 21.9 m ≈ 18 m/s ×
1.13 s, yani hata *tam olarak telafi edilmemiş gecikme*. Hız kazancı istasyon
yasası için doğrudan kritiktir: hız **ileri beslenen** terimdir.

⚠ **ISINMA TRANSİENTİ (ölçüldü).** Yeni filtrenin 25 m üstü tüm hataları
**ilk 4 saniyededir** (t=1.3–4.0 s; ısınma penceresi medyan 23.6 m, max 52 m).
Isınma sonrası her fazda max 13–17 m, dönüşlerde bile. Kalkış ~4 s sürdüğü ve
o sırada yatay komut üretilmediği için transient doğal olarak maskeleniyor —
**kalkışı kısaltırsanız bu maske kalkar.** Maskeyi ayakta tutan iki şey
`control/takeoff.py`'de ve `web/server.py :: _takeoff_step`'tedir: kalkışta
yatay komut üretilmez, ama filtre yine de her tik beslenir.

⭐ **`GPSCfg.FILTER_EVERY_TICK = True`** — filter 50 Hz'de beslenir. Filtre paket
tekrarını kendi tanır (`np.allclose`) ve arada ölü-hesapla ilerler. Yalnız
yeni pakette beslenirse bu mekanizma hiç çalışmaz ve hedef konumu 50 Hz'lik
yasaya ~5 Hz'lik **merdiven** olarak girer. Ölçüldü (3 s'lik kesinti):
kesinti içinde medyan 2.23 m, `dr_max_s` dolunca 9.78 m'de sabitleniyor,
sonra 5 s'de yeniden kilitleniyor. `False` = eski davranış.

---

## FAZ AKIŞI VE KAPILAR

```
KALKIŞ ──(irtifa kapısı)──> GPS (istasyon) ──(devir kapısı)──> GÖRSEL
                                 ^                                │
                                 └──────────(kayıp, LOST_S)───────┘
```

Üç fazın da **yasası ayrı bir modülde**, **kapısı `PhaseSupervisor`'da**dır.
Koşturucu (`web/server.py`) yalnızca faza göre dağıtım yapar.

### KALKIŞ KAPISI (2026-08-25) — kalkış `gps_approach`'tan çıkarıldı
Tırmanma yasası **`control/takeoff.py :: TakeoffLaw`** (yalnız dikey hız
setpoint'i; `TakeoffCfg.VZ = 12 m/s`), "bitti mi?" kararı
**`PhaseSupervisor.takeoff_tick`**. İki yoldan **biri** yeter:
1. zemine göreli `TAKEOFF_ALT_M − TAKEOFF_TOL_M` (45 − 3 = 42 m), **ya da**
2. hedefin irtifasına `TAKEOFF_TARGET_GAP_M` (20 m) kadar yaklaşıldı — hedef
   alçaktaysa 45 m'ye tırmanmak boşuna yoldur.

⛔ 2. kol hedefin GPS'ini okur ve **meşrudur**: devir kapısının 2. koşuluyla
aynı gerekçe — faz geçişi kapısıdır, güdüm yasası değildir, görsel temas henüz
yoktur.

⛔ **KALKIŞTA YATAY KOMUT YOKTUR** ve bu bir tercih değil, filtrenin ısınma
transientinin **maskesi**dir (bkz. §GNSS FİLTRESİ). `TakeoffLaw.step()`
pitch/roll/yaw'a sıfır yazar. Buraya yatay komut eklerseniz 23.6 m medyanlı
transient doğrudan güdüme girer.

⭐ **KALKIŞTA DA `clean_target()` ÇAĞRILIR** (`web/server.py :: _takeoff_step`).
Atlanması **sessiz** bir bozulma olurdu: filtre kalkış boyunca ısınmazsa
transient olduğu gibi istasyon fazının ilk saniyelerine — yani yatay komutun
**üretildiği** yere — taşınır. ⚠ Sıra doğrulandı ama **oyunda değil**: sahte
drone ile kuru koşuda filtre kapı açılmadan ısınıyor (0.40 s vs 1.50 s). Gerçek
kalkış süresi ve ısınma canlıda doğrulanmalı (bkz. §CANLI DOĞRULAMA BEKLEYEN).

⚠ `GPSTracker` artık kalkış **durumu tutmaz** (`_takeoff_done`, `_ground_z`
gitti) ve `step()` aracın **zaten havada** olduğunu varsayar. `GPSTracker.phase`
yalnızca `STATION` üretir; arayüzün `TAKEOFF` çipini gözetmen sürer.

### DEVİR KAPISI (GPS → GÖRSEL)
İki koşul **birlikte** (`control/main.py :: PhaseSupervisor`):
1. **Görsel kilit** — kesintisiz olarak **hem** `VisualCfg.HANDOFF_LOCK_S` (1.0 s)
   **hem** `VisualCfg.HANDOFF_FRAMES` (10) ayrı **karede** güdüme girebilecek kutu.
   Fiilî kapı = `max(süre, kare/dedektör_hızı)`.
2. **İstasyona oturma** — istasyon hatası `HANDOFF_STATION_ERR_M` (8 m) altında VE
   hedefe menzil `HANDOFF_RANGE_M` (15 m) altında, ard arda `HANDOFF_STATION_TICKS`
   (25 tik ≈ 0.5 s). GNSS bayatsa bu koşul düşer, kutu kapısı tek başına yeter.

Kutu kapısı **tek yerde**: `control.visual_tracking.aim_box`. Gözetmen ve
görsel faz **aynı kapıyı** kullanır — iki katmana ayrı eşik yazmak, görsel
fazın aynı karede reddettiği kutuyla devir yapılmasına ve fazın sürekli
sekmesine yol açar.

**2. koşul hedefin GPS'ini okur ve bu meşrudur**: bir *faz geçişi* kapısıdır,
*güdüm yasası* değildir — görsel temas henüz yoktur. `Cfg.CAMERA_ONLY_GATE =
True` yapılırsa bu koşul yapısal olarak devre dışı kalır ve sistem kamera-tek
kapıya düşer. Kapı verisi gözetmene **parametre olarak** geçer
(`gps_tick(..., station_err=, range_h=)`); gözetmen `GPSTracker`'e bakmaz.

**Neden 2. koşul var** (ölçüldü): kamera kapısı tek başına yaklaşma sırasında,
araç daha oturmadan ateşliyordu — devir 22.7 m'de, 14.9 s'de, istasyon hatası
hâlâ 34.6 m. "Otur, SONRA devret" hiç gerçekleşmiyordu.

⚠ **KAPI TİK DEĞİL, KARE SAYAR.** Döngü 50 Hz, dedektör çok daha yavaş → aynı
kutu onlarca tik tekrar görünür. Sayaç bunu ayırt etmezse 10 kare şartı fiilen
10 tik = 0.2 s olur, yani kapı **tek tespitle** açılır. Dedup
`detection_state.status()`'un `seq`'i ile yapılır (`main.PhaseSupervisor._process_frame`).
Kardeş depoda (hamidiyesim) ölçülen çırpınmanın kök nedeni tam olarak zayıf
kanıtla açılan devir kapısıydı: 190 s'de 6–12 faz değişimi, görsel faz ömrü
medyan 3.6–5.2 s.

⭐ **KAPI SÜREYE BAĞLANDI (2026-08-24) — çünkü kare saymak dedektör hızına
kaydı.** "10 kare" sabit bir kanıt değildir; hat hızlandıkça kapı **sessizce**
zayıflar. Ölçüldü:

| dedektör | eski kapı (yalnız kare) | yeni kapı (süre VE kare) |
|---|---|---|
| 8–10 Hz (eski tasarım varsayımı) | 1.00 s | 1.00 s |
| 29.9 FPS (senkron hat, ölçüldü) | **0.33 s** | 1.00 s |
| 53.2 FPS (ayrı yakalama thread'i) | **0.19 s** | 1.00 s |
| 2 Hz (patolojik) | 5.00 s | 4.50 s (kare tabanı bağlar) |

⛔ **SÜRE TEK BAŞINA YETMEZ, üç koşul birden gerekir.** Kamera thread'i donarsa
`seq` durur ama duvar saati ilerler — kare tabanı o ana dek dolmuşsa saf süre
kapısı **donmuş bir görüntüyle** açılır (ölçüldü: 53 Hz'de 0.20 s'de donan
kamera kapıyı 1.00 s'de açıyordu). Bu yüzden `_process_frame` "son YENİ kareden
beri geçen süre > `STALE_S`" olduğunda zinciri kırar. Eşik bilinçli olarak
`STALE_S`'tir: görsel fazın "bu kutu artık güdüme giremez" dediği **aynı**
andır — iki katmana iki ayrı eşik yazılmaz.

⚠ **Kapı geç açılıyorsa önce `HANDOFF_LOCK_S`'i düşürün** (1.0 → 0.7 → 0.5).
Yalnız `HANDOFF_FRAMES`'i düşürmek hızlı dedektörde **hiçbir şey değiştirmez**,
çünkü orada bağlayan koşul süredir.

Görsel fazda `Cfg.LOST_S` (2.0 s) boyunca geçerli kutu gelmezse GPS fazına
dönülür. **Süre cinsinden** yazıldı ki kamera thread'i donarsa da tetiklensin
(donmuş kamerada kare sayacı ilerlemez) — devir kapısı da aynı gerekçeyle
süreye bağlandı.

---

## GÖRSEL MODEL — `perception/models/talon_v3.pt`

| | best.pt (eski) | **talon_v3.pt (aktif)** |
|---|---|---|
| eğitim `imgsz` | 640 | **960** |
| epoch / ultralytics | 200 / 8.4.90 | 60 / 8.4.83 |
| taban / görev / sınıf | yolo11s / detect / `talon` | aynı |

⛔ **`IMGSZ` MODELDEN TÜRETİLİR** (`perception/detector.py`). Modeli değiştirip
`IMGSZ`'yi unutmak **sessiz** bir bozulmadır: çıkarım eğitimden farklı ölçekte
koşar, önce uzak/küçük hedef kaybolur, sonra görsel faz hiç açılmaz. Bu yüzden
eşleme kodda tablo olarak duruyor. Geri alma: `AVCI_MODEL=best.pt` (IMGSZ
kendiliğinden 640'a döner), elle ezme: `AVCI_IMGSZ=...`.

⚠ **`RANGE_C_REF = 997` YENİDEN DOĞRULANMALI.** Menzil kutu **boyutundan**
türer, kutu boyutu ise modelin kutulama sıkılığına bağlıdır. Sabit kardeş
depoda `talon_v3.pt` ile ölçülmüştü — yani bu değişim sabiti *muhtemelen
yaklaştırıyor*, ama **bizim kurulumumuzda ölçülmedi**. Yanlışsa
`aim_box`'nun 3–50 m kapısı yanlış yerde açılır/kapanır.

---

## GÖRSEL YASA — KORUNAN ÖLÇÜMLER (silme)

### Kamera modeli (`control/visual_tracking.py` başı) — kalibre edildi
`TILT = 26.50°`, `F_PX = 540.4 @1920`, `RANGE_C_REF = 997 px·m @1920`.
Artık 2.6 px (n=614); bootstrap 26.57° ± 0.11°. **SDK başlığının yazdığı 25°
kesin olarak elenir** (orada artık iki katına çıkıyor). Model çözünürlükten
bağımsızdır: `_scale(W) = W/1920` ile tüm piksel sabitleri ölçeklenir.

### Dikey kanal: KADRAJ REGÜLASYONU (saf takip DEĞİL)
Hız vektörünü 3B'de hedefe nişanlamak (saf takip) **çöktü**: 24° yükselişte
`28·sin(24°) = 11.4 m/s` tırmanma komutu veriyor, araç hedefin hizasına
çıkıyor ve kamera 26.5° yukarı baktığı için hedef **görünmüyor** (tespit
%90 → %12–15, isabet 0/3). Yerine `vz = -K_CY·(cy - cy_ref)`.

⭐ **KAZANÇ ve TAVAN BİRLİKTE ayarlandı** (E1+E1b, n=8/kol):

| ölçüt | 0.06 / 1.5 | **0.014 / 4.0** |
|---|---|---|
| TEMAS | 6/8 | **8/8** |
| en yakın (medyan) | 0.86 m | **0.51 m** |
| tespit % | 59.0 | **70.8** |
| görsel kesinti | 10.20 s | **2.05 s** |
| doyum oranı | %97.0 | **%17.7** ← mekanizma kanıtı |

Eski çift dikey kanalı orantılı kontrolcü değil **aç-kapa anahtarı** yapıyordu:
`|e_cy| > 25 px` olan her kare doyumdaydı. Doğrusal aralık ±25 px → **±286 px**.

### Dikey tavan (`VZ_CAP_VISUAL = 4.0`)
B7, n=4/kol: isabet 3/4 → 4/4, en yakın 3.00 → 0.72 m, tespit %20.7 → %50.9,
roll p90 12.6° → 5.55°. Aralıklar hiç örtüşmüyor. Mekanizma: kamera gövdeye
sabit; dikey komut throttle'ı sıçratıyor, araç savruluyor, 70 px'lik hedef
bulanıyor (|throttle| tespiti en çok bozan büyüklük: 0.300 var / 0.669 yok).

### Kutu köprüsü (`BRIDGE_S = 1.0`) — ölü-hesap
Çıkarım ~10 Hz; aradaki 100 ms'de ve tespit boşluklarında güdüm bayat kutuyla
uçar. Kutunun **kerteriz (atalet) yönü** saklanır, **kendi dönüşümüz** telafi
edilerek kadraja geri yansıtılır. B2, n=4/kol: isabet 1/4 → 4/4, en yakın
medyan 5.44 → 1.94 m, roll p90 48.65° → 27.05°. Süre tarandı (B5): 0.3 → 3.35 m,
0.5 → 1.90 m, **1.0 → 1.34 m (kazanan)**; 2.0 ek kazanç vermedi.
⭐ Girdi yalnız: son kutu + kendi IMU'muz → GPS yok, menzil yok (§kural temiz).

### Geçerlilik kapısı: MENZİL ARALIĞI (eski `BOYUT_MAX` yerine)
`CONF_MIN=0.40`, `SIZE_MIN_PX=8`, `3 m ≤ R ≤ 50 m`.
- `CONF_MIN` ölçüldü: eşik 0.10'da tespit %49 / argmax doğru %43; 0.40'ta
  %40 / %40. ~9 puan tespit karşılığında yanlış-pozitifin argmax'ı çalması
  tamamen biter.
- `RANGE_MAX_M=50`: 60–90 m'de tespit %9 — orada GPS fazı sürer.
- `RANGE_MIN_M=3`: altındaki kutu **dev yanlış-pozitif**tir. Dedektör 140 m'de
  bu boyutta kutu üretiyordu; kapı açılıyor, güdüm "temas" sanıp tam hücum
  veriyor ve araç yere çakılıyordu (iki koşu, "Player ☠").

⚠ **ESKİ NOTUN NEDEN DEĞİŞTİĞİ (2026-08-24).** Eski `BOYUT_MAX=0.85` maddesi
"sınırı DARALTMAYIN, gerçek vuruşu keser" diyordu ve **o zaman doğruydu**:
elde köprü yoktu, kutu reddedilince güdüm KÖR kalıyordu. Artık `BRIDGE_S`
boyunca son geçerli kutu kendi dönüşümüzle ileri taşınıyor, yani son
metrelerde nişan kaybolmuyor. Kısıtı gevşetmek için köprüyü kaldırmayın —
ikisi birlikte anlamlıdır.

### Yaw
`K_YAW=1.0` (tam düzeltme), `YAW_RATE_MAX=120 °/s`. Araç 214 yapabiliyor ama
hızlı yaw görüntüyü bulandırıp dedektörü kırar — **bilinçli olarak korundu**.

### İleri hız — KAPANMA HIZI DENETİMİ (hücum PI'si DEĞİL)

⚠ **Bu madde 2026-08-25'te düzeltildi**: eskiden burada anlatılan "temas
kutusuna kadar tam gaz PI"si aslında `CLOSE_CONTROL=False` dalıydı ve **aktif
değildi**. Aktif yasa baştan beri kapanma denetimiydi; doküman geride kalmıştı.
O ölü dal artık koddan da kaldırıldı.

```
v_yer = v_hedef_LOS + v_kapanma(R),   v_kapanma = K_CLOSE · (R − TRAIL_RANGE_M)
```

Hedefin LOS hızı **kutu büyümesinden** kestirilir (`R = C/kutu`, `Rdot`
süzülür) — GPS yok, §KATI KURAL temiz. `V_MAX = 28 m/s` bir **hız tavanıdır**,
hücum hızı değil: Talon 17.98 m/s uçtuğu için 18 ile kapanma 0.02 m/s = asla
yakalayamayız; 28 → kapanma ~10 m/s.

⭐ **PROFİL `TRAIL_RANGE_M` (3 m) DE SIFIRLANIR, `ATTACK_RANGE_M` (1 m) DE
DEĞİL.** `RANGE_MIN_M`(3 m) altında `aim_box` kutuyu reddeder, ardından
`BRIDGE_S`(1 s) + `LOST_S`(2 s) gelir → **3 saniye kör uçuş**. 1 m'ye regüle
etmek kapalı çevrimde ulaşılamayan bir noktaya nişan almaktır; eski yasa orada
28 m/s bıraktığı için araç hedefin ~30 m **önüne geçiyordu**. Profil görü
sınırında sıfırlanınca araç hedefin **kuyruğuna oturur ve orada kalır**.

⛔ **HÜCUM YASASI DEVRE DIŞI** (2026-08-25, kullanıcı kararı). Şu anki amaç
temas değil, **kamera takibini iyileştirmek**. `ATTACK_RANGE_M`, `K_FWD`,
`K_I`, `I_MAX` ve `CLOSE_CONTROL` anahtarı `visual_tracking.Cfg` içinde
**yorum satırı** olarak duruyor (ölçülmüş değerler korundu); `compute()`
içindeki dal kaldırıldı. Bu **güdüm davranışını değiştirmez** — aktif yasa
zaten kuyruğa oturuyordu.

⛔ **ELENEN EKLEMELER — geri koymayın** (hepsi ölçüldü ve işi kötüleştirdi):
lead (13.75 m), merkez freni (13.00 m), sakin kamera (16.08 m), tam yaw bandı
(~19 m) — taban 12.05 m, isabet 1/4. Terminal dikey serbestliği: temas 4/4 →
0/4. Tam kerteriz zinciri güdüm çevriminde: temas 6/8 → 4/8, cx dönüş/s
0.34 → 1.30. Yerellik kapısı ve bayat-kutu-bırak: berabere, alınmadı.

---

## ÖLÇÜLMÜŞ HAT BÜTÇESİ (2026-08-24, RTX 5050 Laptop, oyun KAPALI)

`talon_v3.pt` @ imgsz 960, FP16, CUDA. Her nokta n ≥ 30.

| aşama | simülasyon (mss) | yer istasyonu (capture kart, 1080p MJPEG) |
|---|---:|---:|
| yakalama | 15.6 ms | *üretici thread'inde, kritik yolda değil* |
| BGRA→BGR / MJPEG decode | 8.6 → **1.1** ms | 3.96 ms |
| YOLO `detect_all` | 10.3 ms | 11.43 ms |
| HybridSort (`sof`) | 5.65 ms | 5.65 ms |
| **işleme toplamı** | **53.2 FPS** | **20.95 ms → 47.7 FPS** |

⭐ **BGRA→BGR: `cv2.cvtColor` kullanın, numpy dilimi DEĞİL.** 1920×1200'de
8.56 → 1.11 ms (ölçüldü). Üreticinin kare başı maliyeti doğrudan yakalama
tavanını belirler.

⛔ **GPU HESAPLA DEĞİL, KERNEL BAŞLATMAYLA SINIRLI.** Saf ileri geçiş
(ultralytics gideri hariç): imgsz 640 → 10.48 ms (21.7 GFLOPs), imgsz 960 →
10.59 ms (49.1 GFLOPs). **2.3 kat iş, aynı süre.** Üç sonuç:
- `IMGSZ` düşürmek beyhude (416 ile 960 arası 1.5 ms) — uzak menzil tespitini
  bedavaya kaybedersiniz, **dokunmayın**.
- `yolo11n` (2.62 M / 15.2 GFLOPs, bizimki 9.43 M / 49.1) bu donanımda hiçbir
  şey kazandırmaz. Jetson gibi **hesap sınırlı** bir kartta kazandırırdı.
- **FP16 farksız** (9.63 vs 9.54 ms); 640'ta FP16 daha *yavaş* (10.48 vs 8.29).
- Kalan tek kaldıraç **TensorRT**'dir: katman füzyonu + CUDA graph tam da
  kernel başlatma giderini hedefler. **Ölçmeden vaat etmeyin**; `.engine`
  sürücüye ve GPU'ya bağlıdır, her kart için ayrı üretilir.

⚠ **DAHA BÜYÜK GPU BU SORUNU ÇÖZMEZ.** Kernel başlatma gideri sürücü/CPU
tarafındadır. A100 büyük yığın (batch) ve büyük modelde parlar; bizimki tek
kare, 49 GFLOPs'luk küçük bir iş yükü ve A100'ün taban saati bir dizüstü
Blackwell'den düşüktür → kare başına süre aynı ya da biraz **kötü** çıkabilir.
Donanım değişikliğinden gecikme kazancı beklemeden önce **o kartta ölçün**.

⚠ **ÖLÇÜM KOŞULU: OYUN KAPALIYDI.** Unreal aynı GPU'yu kullanırken sayılar
kötüleşir; darboğazın *yeri* değişmez, *büyüklüğü* değişir.

---

## CANLI DOĞRULAMA BEKLEYEN (öncelik sırasıyla)

> **Hiçbiri oyunda koşturulmadı.** Aşağıdaki her madde ölçüm ya da kod
> incelemesiyle doğrulandı; canlı uçuşla değil.

### Önce bunlar — koşturmayı engelleyenler

**ALGI PAKETLERİ ARTIK KURULU** (2026-08-24 doğrulandı): `ultralytics 8.4.127`,
`mss`, `opencv-python`, `boxmot 22.0.0`, `torch 2.13.0+cu132` (CUDA çalışıyor),
Python 3.13.15. Kamera hattı uçtan uca koştu. Paketler eksikse dedektör tembel
yüklenir, yüklenemeyince tüketici sessizce bekler ve kare sayacı ilerlemez;
arayüz bunu 15 s sonra olay günlüğünde bildirir, GPS modu etkilenmez.

⛔ **`boxmot` MODÜL YOLU SÜRÜMLER ARASINDA İKİ KEZ DEĞİŞTİ.** 22.0.0'da
`hybridsort` bir **paket değil, düz modüldür** → eski iki import yolu da
`ModuleNotFoundError` verir ve takipçi **sessizce** devre dışı kalır
(`ready=False` → ham argmax, kimlik sürekliliği ve tek-kare parazit filtresi
kaybolur, hiçbir şey çökmez). `perception/tracking.py` artık üç yolu yeniden
eskiye dener ve hepsi başarısızsa hangi yolun ne hata verdiğini yazar.
Doğru yol (v22+): `from boxmot.trackers.bbox.hybridsort import HybridSort`.
Çıktı düzeni değişmedi: 8 sütun `[x1,y1,x2,y2,track_id,conf,cls,ind]`.

**YENİ GNSS FİLTRESİ CANLIDA DENENMEDİ.** `GNSSFilterV2` sentetik jammer
verisinde eskisinden 6.9× (konum) / 10× (hız) daha iyi çıktı, ama gerçek jammer
profili farklı olabilir. **Isınma transienti** ilk ~4 saniyededir (medyan
23.6 m, max 52 m) ve kalkışla örtüştüğü için maskeleniyor — kalkışı
kısaltırsanız bu maske kalkar. Geri dönüş: `GPSCfg` içinde `GNSSFilterV2`
yerine `filter/gnss_filtre.py :: GNSSFilter` (o sürüm `lead_s=` değil
`delay_s=` parametresi alır).

### Sonra bunlar — canlı tune

1. **KAMERA KALİBRASYONU BİZİM KURULUMUMUZDA DOĞRULANMALI.** `F_PX=540.4`,
   `TILT=26.5°`, `RANGE_C_REF=997` kardeş depoda **Proton/Wine altında** ölçüldü;
   Windows'ta DPI zinciri farklıdır. `RANGE_C_REF` ayrıca dedektörün kutulama
   sıkılığına bağlıdır; 2026-08-24'ten beri biz de `talon_v3.pt` kullanıyoruz
   (sabitin ölçüldüğü modelle **aynı ad**), yani risk azaldı ama sıfırlanmadı.
   **Bu üç sabit menzil kapılarını (3–50 m) ve ileri hız PI'sini doğrudan
   sürer** — yanlışsa görsel faz ya hiç açılmaz ya da yanlış hızla kapanır.
   Doğrulama: bilinen menzilde (GPS'ten okunan, faz devri ÖNCESİ) kutu
   genişliğini ölç, `RANGE_C_REF = genişlik × menzil` hesapla.
2. **EKRAN YAKALAMA ALANI.** Kamera modeli **oyun kadrajını** varsayar. Tüm
   ekran yakalanırsa (görev çubuğu, pencere kenarlığı) merkez ve odak kayar.
   `AVCI_REGION="left,top,w,h"` ile tam oyun görüntüsünü verin.
   ⚠ **Gerçek kameraya geçildiğinde `F_PX`/`TILT`/`RANGE_C_REF` üçü de
   geçersizdir** — bunlar oyunun sanal kamerasının sabitleridir, fiziksel bir
   merceğin değil. Yeniden kalibrasyon şarttır.
3. **İŞARET DOĞRULAMASI.** `Y_SIGN`/`Z_SIGN` ölçülmüş değerlerdir ama
   kurulum farkı olursa: yanal komut ters tepki verirse
   `common.ConverterCfg.Y_SIGN = +1`.
4. **DEDEKTÖR ÇÖZÜNÜRLÜĞÜ.** `IMGSZ` artık modelden türetiliyor:
   `talon_v3.pt → 960` (eğitim çözünürlüğü, checkpoint metadata'sından okundu).
   Kardeş depo kendi ölçümünde 1920'nin uzak menzilde şart olduğunu bulmuştu
   (40–60 m'de tespit %6 → %55) — bizde **ölçülmedi**. Uzak menzilde tespit
   zayıfsa `AVCI_IMGSZ=1920` deneyin (VRAM/FPS bedeliyle).
5. **İSTASYON/DEVİR AYARLARI.** `STATION_RANGE_M`, `STATION_ALT_RATIO`,
   `HANDOFF_RANGE_M` canlı tune edilir. Kapı geç açılıyorsa **önce
   `HANDOFF_LOCK_S`'i düşürün** (1.0→0.7→0.5); `HANDOFF_FRAMES` hızlı
   dedektörde bağlayıcı değildir. `CONF_MIN` veya menzil aralığını
   **gevşetmeyin**.
6. **VİDEO LİNKİ GECİKMESİ** (gerçek uçuş). Kodun düzeltebildiği her şeyden
   büyük olabilir ve hakkında **hiç verimiz yok**. Ölçüm: kameranın önünde
   koşan bir milisaniye kronometresini çekin, ekrandaki görüntüyle aynı karede
   fotoğraflayın, farkı okuyun. Neden kritik: kapanma hızı
   `V_ATTACK 28 − Talon 17.98 = 10.02 m/s` → **100 ms gecikme = 1.00 m bayat
   nişan**, yani tam olarak `ATTACK_RANGE_M`'nin kendisi.

### Açık karar: HybridSort takipçisi
`perception/tracking.py` yerinde duruyor (kullanıcı riski bilerek onayladı).
Kardeş depo onu **çıkardı**, gerekçesi kayıtlı: takipçi dedektörün
yanlış-pozitifini de bir iz olarak benimseyip Kalman ile ~20 kare ileri
taşıyordu — yani hatayı silmiyor, **uzatıyordu**. Bizde artık aynı işi
`aim_box` menzil kapısı + `BRIDGE_S` ölü-hesabı yapıyor ve ikisi de
kendi ölçtüğümüz mekanizmalar. Görsel fazda sürüklenen/hayalet kutu
görürseniz ilk şüpheli takipçidir; kapatmak için `Tracker.ready = False`
davranışı (boxmot yokken) zaten ham argmax'a düşer.

⛔ **KAMERA-HAREKET TELAFİSİ `sof`, `ecc` DEĞİL.** Ölçüldü (1920×1200, n=30,
`update()` başına): `ecc` 9.66 ms · `sof` 3.51 ms · kapalı 0.41 ms ·
`ecc` yarım çözünürlükte 1.76 ms. `tracking.py`'deki `_silence()` yorumunun
kendisi ECC'nin dokusu az **gökyüzü** karelerinde "did not converge" bastığını
söylüyor — yani 9.66 ms yakıp güvenilmez bir dönüşüm üretiyordu. Geçerli
değerler (boxmot 22): `ecc`, `orb`, `sift`, `sof`.

---

## ADLANDIRMA

**KOD İNGİLİZCE, AÇIKLAMA TÜRKÇE.** Tek kural bu:

| İngilizce | Türkçe |
|---|---|
| modül/sınıf/fonksiyon/değişken/sabit adları | yorum satırları ve docstring'ler |
| sözlük anahtarları, telemetri JSON alanları | arayüzde **görünen** her metin |
| durum/faz metinleri (`READY`, `TAKEOFF`, `STATION`, `VISUAL`, `HYBRID`) | olay günlüğü mesajları |
| HTML `id`/`class`/`data-*`, JS işlev ve değişkenleri | HTML metin içeriği |
| ortam değişkenleri (`AVCI_REGION`, `AVCI_DEBUG_WINDOW`, `AVCI_MODEL`, `AVCI_IMGSZ`, `AVCI_DEVICE*`, `AVCI_CAP_FPS`, `AVCI_FP16`) | — |

Faz metni ile ekranda yazan etiket **ayrıdır**: kod `VISUAL` üretir, arayüz
`data-phase="VISUAL"` çipinde **GÖRSEL** gösterir. Birini diğerinin yerine
kullanmayın — çeviriyi tek yerde, HTML'de yapın.

⚠ İki bilinçli istisna: `filter/gnss_filtre.py` ve `filter/gnss_filtre_v2.py`
dosya adları (kullanıcı kararı; içerideki her şey İngilizcedir) ve `AVCI_`
öneki (proje adının kendisi).

⚠ `GPSTracker.filter` bir **özniteliktir**, `filter` builtin'ini gölgelemez.
`filter` paketi de yalnızca `from filter.x import y` biçiminde kullanılır.

---

## ÇALIŞMA İLKELERİ (değişmez)
- **Sadece üzerinde çalıştığımız, açıklayabildiğimiz şeyi kullan** (yarışma
  kuralı 8). Bakmadığımız yabancı modüller entegre EDİLMEZ. Bilinen istisna:
  `boxmot` HybridSort (kullanıcı riski bilerek onayladı).
- **Hazır güdüm yazılımı doğrudan kullanılmaz** (kural 6). Filtre, istasyon
  yasası, IBVS yasası ve çevirici bizim implementasyonumuzdur.
- Senaryoya aşırı-uydurulmuş sabitler kullanılmaz.
- **n < 4 iken hüküm cümlesi kurulmaz.** Kardeş depoda üç kez, n=3 ile verilen
  kararların hepsi işi kötüleştirdi ve geri alındı.
- Yeni özellik eklerken **kapsamı büyütme**: proje bilinçli olarak sadeleşti.

---

## PLATFORM (Linux + Windows)
Python kodu **platformdan bağımsızdır**. Fark **yalnızca iki yüzeyde**:
1. **Oyunun başlatılması** — Linux `scripts/start_game.sh` (Wine), Windows
   `scripts/start_game.ps1` (native). İkisi de AYNI shipping exe'yi AYNI
   argümanlarla açar; birini değiştirirken diğerini de güncelle.
2. **Kabuk sözdizimi** — `python3` ↔ `python`, `export VAR=x` ↔ `$env:VAR="x"`,
   `.venv/bin/activate` ↔ `.venv\Scripts\Activate.ps1`.

**Python sürümü: 3.10–3.13, 3.14 DEĞİL.** `boxmot`'un hiçbir sürümü 3.14'ü
desteklemez. 3.14'te sistem çökmez ama takipçi sessizce devre dışı kalır
(`tracking.py: hazir=False` → ham argmax) — kimlik sürekliliği ve tek-kare
parazit filtresi kaybolur. Bu **sessiz** bir bozulmadır.

Güdüm/algı mantığına platform için **dokunulmaz**; yeni bir OS farkı çıkarsa
çözüm script veya dokümanda olur, `control/`–`perception/` içinde değil.

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

⛔ **MASKE GÖREV YENİDEN BAŞLATILDIĞINDA ÇALIŞMAZ** (araç zaten havadadır,
kalkış anında biter). O yol için ikinci bir savunma vardır: filtre görevler
arası **korunur** ve soğuk başlamaz — bkz. §GÖREVİ DURDURUP YENİDEN BAŞLATMA.
Ölçüldü: filtre yeniden kurulunca istasyon fazının ilk 1.5 s'inde hedef konum
hatası medyan **39.2 m** (max 80.8), korununca **2.5 m** (max 6.3).

⭐ **`GPSCfg.FILTER_EVERY_TICK = True`** — filter 50 Hz'de beslenir. Filtre paket
tekrarını kendi tanır (`np.allclose`) ve arada ölü-hesapla ilerler. Yalnız
yeni pakette beslenirse bu mekanizma hiç çalışmaz ve hedef konumu 50 Hz'lik
yasaya ~5 Hz'lik **merdiven** olarak girer. Ölçüldü (3 s'lik kesinti):
kesinti içinde medyan 2.23 m, `dr_max_s` dolunca 9.78 m'de sabitleniyor,
sonra 5 s'de yeniden kilitleniyor. `False` = eski davranış.

---

## FAZ AKIŞI VE KAPILAR

```
KALKIŞ ─(irtifa)─> GPS (istasyon) ─(devir)─> GÖRSEL ─(10 s güdüm)─> ÇARPMA
                        ^                       │                      │
                        └───(kayıp, LOST_S)─────┘                      │
                        └──────────────(kayıp, LOST_S)─────────────────┘
```

Dört fazın da **yasası ayrı bir modülde**, **kapısı `PhaseSupervisor`'da**dır.
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

#### KADRAJ PENCERESİ — devir kapısının 3. koşulu (2026-08-27)

Devir kapısı hedefin kadrajın **neresinde** olduğuna bakmıyordu. Tek konum
kontrolü `aim_box`'taki `0 <= cx < W and 0 <= cy < H` idi; bu bir *geçerlilik*
kontrolüdür, konum kapısı değil — köşeye 2 px kalmış kutu merkezdekiyle
**aynı** geçiyordu.

Kural tek cümle: **devir, görsel yasanın ilk komutunu DOYURACAĞI bir noktada
yapılmaz.** Eşikler `control/visual_tracking.py :: handoff_frame_limits`'te
mevcut sabitlerden **türetilir; yeni tune düğmesi YOKTUR**:

```
dx = f_px(W) · tan( YAW_RATE_MAX / (KP_YAW_RATE · K_YAW) )   -> 453 px @1920
dy = VZ_CAP_VISUAL · sh / K_CY                                -> 286 px @1080
kabul: |cx − W/2| < dx   VE   |cy − CY_REF·sh| < dy
```

Pencere kadrajın ortasına değil **`CY_REF`e (nişan noktası)** göredir.
@1920×1080: `cx ∈ (507, 1413)`, `cy ∈ (184, 756)` — kadrajın **~%25'i**.

⭐ **NEDEN ÖLÇÜLMÜŞ SABİTLERDEN TÜRÜYOR.** Kenardaki kutuyla devir yapılırsa
ilk görsel komut doyar (own_att=0, R=20 m ile hesaplandı):

| kutu yeri | azimut | yaw çubuk | vz | throttle |
|---|---:|---:|---:|---:|
| nişan noktası (960,470) | 0.0° | 0.00 | 0.00 | −0.586 |
| sol kenar (30,540) | −59.8° | **−1.00** | −0.98 | −0.645 |
| üst kenar (960,30) | 0.0° | 0.00 | **+4.00** | +0.096 |
| sol üst köşe | −59.8° | **−1.00** | **+4.00** | +0.096 |

İkisi de dokümanda zaten gerekçeli: hızlı yaw görüntüyü bulandırıp dedektörü
kırar (bu yüzden `YAW_RATE_MAX` aracın 214'ü yerine 120'de tutuluyor) ve
`|throttle|` tespiti **en çok bozan** büyüklüktür (B7: 0.300 var / 0.669 yok).
Köşede throttle `HOVER_THR` −0.586'dan +0.096'ya sıçrıyor. Zincir: savrul →
bulanıklaş → kutuyu kaybet → `LOST_S` → GPS'e dön = **faz çırpınması**.

⚠ **KAPI YALNIZ DEVİR KARARINA UYGULANIR, GÜDÜME DEĞİL.** Görsel faz sürerken
hedef kenara kayarsa yasa **tam da** yaw'ı doyurup onu geri getirmelidir;
orada reddetmek aracı kör bırakırdı. `PhaseSupervisor._process_frame` bu
yüzden `_last_valid_t`'yi kadraj koşulundan **önce** tazeler: kenardaki kutu
devri açmaz ama `LOST_S`'i de tetiklemez. Doğrulandı: görsel fazdayken hedef
cx 960 → 1700'e kaydırıldığında faz **VISUAL kaldı**.

⭐ **TEK KAPI KURALI KORUNDU.** `handoff_framed` = `aim_box` **VE** pencere.
1479 noktalık taramada devirden geçip `aim_box`'tan geçmeyen **tek kutu yok**.
Yani devir, görsel fazın aynı karede reddedeceği kutuyla asla açılamaz —
CLAUDE.md'nin uyardığı çırpınma yönü budur. Ters yön (görsel fazın kabul edip
devrin reddetmesi) kasıtlıdır.

⚠ **BU KAPI DEVRİ GECİKTİRİR** ve canlıda ölçülmedi. Geç açılıyorsa sırayla:
(1) arayüzdeki **"kadraj dışı"** uyarısına bakın — kilit satırında görünür ve
kapının hangi koşulda takıldığını söyler; (2) `HANDOFF_LOCK_S`'i düşürün.
Pencereyi genişletmek için `K_CY`/`VZ_CAP_VISUAL`/`YAW_RATE_MAX` ile
**oynamayın**: onlar ölçülmüş güdüm sabitleridir, pencere onların türevidir.

⛔ **KIRPILMIŞ KUTU ARTIK `aim_box`TAN GEÇMEZ** (ayrı ve daha geniş kapsamlı
düzeltme — devir kararını değil, **her kareyi** etkiler). Dedektör kutuyu kare
sınırına kırpar; hedefin bir kısmı dışarıdaysa `size` küçük ölçülür ve
`R = C/size` büyük çıkar. Ölçüldü:

| gerçek menzil | kadrajda %50'si kalırsa | kapanma komutu |
|---|---|---|
| 8 m | 16.0 m okunur | 7.8 m/s (doğrusu 3.0) |
| 12 m | 24.0 m okunur | 12.0 m/s (doğrusu 5.4) |

Yani araç, sandığının **yarısı kadar yakın** olan hedefe doğru hızlanıyordu.
Artık kutunun **kenarları** kadrajın içinde olmalı, yalnız merkezi değil
(`EDGE_EPS_PX = 1.0` — tolerans değil, kayan nokta payı). Reddedilen kare kör
bırakmaz: `BRIDGE_S` boyunca son geçerli kutu kendi dönüşümüzle ileri taşınır
— kısıt ve köprü **birlikte** anlamlıdır.

### ÇARPMA KAPISI (GÖRSEL → SPIKE) — 2026-08-27

**Kural (kullanıcı kararı): 10 s görsel güdümden sonra çarpma fazı.**
`Cfg.SPIKE_AFTER_VISUAL_S = 10.0`. Süre **görsel faza girişten** sayılır
(`_visual_since`) ve faz GPS'e düşerse sıfırlanır — yani "10 saniye boyunca
hedefi görsel olarak güttük" demektir, "görev başlayalı 10 s oldu" değil.

⛔ **SÜRE TEK BAŞINA YETMEZ — ikinci koşul: O ANDA taze bir kutu.** Kamera
donarsa `seq` durur ama duvar saati ilerler; saf süre kapısı çarpma fazını
**donmuş bir görüntüyle** açardı. Devir kapısında ölçülüp kayda geçen dersin
aynısı (53 Hz'de 0.20 s'de donan kamera saf süre kapısını 1.00 s'de açıyordu)
— ama bedeli burada daha ağırdır: bayat kanıtla **çarpışma rotasına** girilir.

Çarpma fazında kutu `LOST_S` (2.0 s) boyunca gelmezse **doğrudan GPS'e**
dönülür. ⚠ İlk taslakta iki kademeli yazmıştım (önce GÖRSEL'e, o toparlamazsa
GPS'e); kuru koşuda o ara adımın **boş** olduğu görüldü — iki faz da aynı
`_last_valid_t`ye baktığı için görsel faz ilk tikte aynı kaybı görüp düşüyordu
(SPIKE→VISUAL t=27.00, VISUAL→GPS t=27.02: 20 ms'lik sahte kademe). Temas
menzilinde 28 m/s ile kutuyu kaybettiysek zaten hedefin yanından geçmişizdir;
yapılacak şey istasyonu yeniden kurmaktır ve ısınmış GNSS filtresi hazırdır.

### ÖN-HIZLANMA — fren geçişten `SPIKE_LEAD_S` önce kapatılır (2026-08-27)

⛔ **SORUN.** Görsel faz hedefin kuyruğunda **oturur**: `v_close` menzil
`TRAIL_RANGE_M`e yaklaştıkça küçülür, yani araç geçiş anına kadar
FRENLEMEKTEDİR (canlıda ölçüldü: seyir 64–67 km/h ≈ 18 m/s). Çarpma yasası
ise ilk tikte `V_ATTACK`(28 m/s) ister. Ölçüldü — iki yasaya AYNI durum
verilip ilk komutları karşılaştırıldı:

| durum | görsel ister | çarpma ister | pitch adımı | `MAX_DELTA` katı |
|---|---:|---:|---:|---:|
| **fren AÇIK** (v=18, R=4.5) | 18.0 m/s | 28.0 m/s | **0.441** | **2.9×** |
| fren KAPALI (v=25.3) | 28.0 m/s | 28.0 m/s | **0.000** | 0.0× |

Fren açıkken eğim sınırı ~3 tik (59 ms) **doyar**: doymuş pitch = burun aşağı
savrulma = bulanık görüntü = tam da dedektörü kıran şey (B7).

⭐ **SÜRE ÖLÇÜLDÜ, TAHMİN EDİLMEDİ.** Gerçek zincir simüle edildi
(`VelocityToStick` → `MAX_DELTA` eğim sınırı → 46 ms ölü zaman → 0.211 s yatış
sabiti). 18 → 28 m/s tırmanışı: %63'e 0.74 s, %90'a 1.22 s, %95'e 1.40 s.

**ALT SINIR** — geçişte ilk komut eğim sınırını aşmasın (devir kapısındaki
"ilk komutu DOYURACAK noktada devretme" ilkesinin aynısı):

```
dv <= MAX_DELTA * A_MAX / K_V = 0.15 * 34 / 1.5 = 3.40 m/s
-> gecis aninda hiz >= 24.60 m/s
   v0=18 -> 0.78 s | v0=17 -> 0.82 s | v0=16 -> 0.86 s   ==> 0.86 s
```

**ÜST SINIR** — ön-hızlanma sırasında menzil de kapanır (hedef 18 m/s, biz
hızlanıyoruz); görüş tabanının altına inilmemeli:

```
R0=6 m -> 0.90 s | R0=7 m -> 1.04 s | R0=8 m -> 1.16 s   ==> 0.90 s
```

**GÜVENLİ PENCERE 0.86–0.90 s → `Cfg.SPIKE_LEAD_S = 0.90`.**
Doğrulandı: N=0.9 s'de geçiş hızı 25.39 m/s (≥24.60 ✓), geçiş menzili 4.96 m
(görüş tabanının üstünde ✓), pitch adımı 0.000 ✓. Tutarlılık sınaması: alt
sınırda (v=24.6) pitch tam olarak **0.150 = `MAX_DELTA`** çıkıyor — türetimle
birebir.

⚠ **ÜST SINIR YAPISAL OLARAK KALDIRILDI.** Pencere çok dardı ve canlıda
ölçülen EN YAKIN menzil 4.5 m idi — oradan başlarsa üst sınır alt sınırın
altına düşer ve ayar **kendi kendini bozardı**: menzil tabanı aşılır, kutu
reddedilir, kapı TAZE kutu şart koştuğu için HİÇ açılamaz ve araç hedefin
içinden geçer. Bu yüzden `spike_armed` penceresinde **terminal süreklilik
istisnası da açılır**; menzil kapanması artık kutuyu kaybettiremez. İstisna
süreklilik şartıyla (taze + ≤`TERMINAL_GROWTH` kat) korumalıdır — kapsamı
0.9 s genişler, **gevşemez**.

⭐ Pencere YALNIZ GÖRSEL fazda açılır (`spike_armed` önce `phase == VISUAL`
bakar); GPS fazında sayaç zaten sıfırlanmıştır.
Telemetri: `supervisor.status()["spike_armed"]` ve `VisualTracker.status()`
içindeki `no_brake` mekanizma sütunudur.

### ÇARPMA KAPISININ 3. KOŞULU: DİKEY NİŞAN OTURMASI (2026-08-27)

⛔ **CANLI ISKADAN GELDİ.** 2026-08-27 22:11 uçuşu: 214 s, **5 isabet / 2 ıska**
(oyunda çarpma avcıyı da imha ettiği için "yeniden doğma" = isabet; OSD'nin
kaybolduğu pencereler tarandı). Ayırt edici tek değişken, hücuma girerkenki
**dikey nişan hatası**ydı:

| koşu | `\|e_cy\|` girişte (@720) | dikey komut doyumu | sonuç |
|---|---:|---:|---|
| t=138.5 | 9 px | %0.0 | ÇARPTI |
| t=100.2 | 17 px | %0.0 | ÇARPTI |
| t=24.4 | 26 px | %0.0 | ÇARPTI |
| t=170.8 | **91 px** | **%20.9** | **ISKA** |
| t=194.5 | **60 px** | **%9.8** | **ISKA** |

Iskalarda hedef **tırmanan kaçamak dönüş** yaptı (karelerde görülüyor); buruna
göre dikey açı koşu boyunca kapanmak yerine **büyüdü** (47° → 69°) ve araç
hedefin altından geçti. İsabetlerde aynı açı kapanıyordu (36.6° → 29°).

⛔ **TERMİNAL FAZDA DÜZELTİLEMİYOR.** OSD'ye göre ıskada araç 3.4 s'de
32 → 35 m, yani yalnız **0.88 m/s** tırmandı — oysa yasa 4.0 istiyor ve
karelerin %21'inde tavana dayanmıştı. Sebep: 65–79 km/h ileri hızda burun
aşağı yatıkken itkinin çoğu **ileri** gidiyor; `ConverterCfg`'nin dikey
haritası (`POS_SLOPE`/`POS_INTERCEPT`) bu bağlaşımı içermez, düz uçuşta
ölçülmüştür. ⚠ Bu yüzden **`VZ_CAP_VISUAL`'i yükseltmek çözmez** — araç o
hızda o tırmanmayı zaten veremiyor. Çare hücuma **hatasız girmektir**.

⭐ **EŞİK TÜRETİLİR — `visual_tracking.spike_aim_limit`.** Devir penceresinin
ölçütü "komut doyar mı"dır (±190 px @720) ve burada YETMEZ: iki ıskada da
komut girişte doymamıştı, koşu sürerken doydu. Doğru ölçüt **geometriktir** —
menzil kapandıkça açısal hata 1/R ile şişer:

```
dθ/dt = ḋ/R + d·|Ṙ|/R²   ->  acinin BUYUMEMESI icin  ḋ > tan(θ)·|Ṙ|
tan(θ_max) = VZ_CAP_VISUAL / V_MAX          (en kotu kapanma = hucum hizi)
dy_spike   = f_px(W) · tan(θ_max)           = 77 px @1080,  51 px @720
```

⚠ `sh` çarpanı YOKTUR — `f_px(W)` ölçeklemeyi zaten yapar. `handoff_frame_limits`
te `sh` vardır çünkü orada ölçüt `vz = (K_CY/sh)·e_cy` doyumudur ve `K_CY`
@1080 tanımlıdır; burada ölçüt bir AÇIdır.

Doğrulandı (aynı uçuşun kutu dizisi): isabetler %100 / %80.8 / %76.9 açık →
**geçer**; ıskalar %0.0 / %13.8 → **engeller**.

⚠ **ÖN-HIZLANMA DA AYNI KOŞULA BAĞLI, AMA TUTMA SÜRESİYLE.** Nişan penceresi
canlı kayıtta karelerin yalnız **%29.4**'ünde açık; ham koşula bağlansaydı fren
açılıp kapanır, ileri komut 18 ↔ 28 m/s salınır ve her salınım 0.44'lük bir
pitch adımı (MAX_DELTA'nın 2.9 katı) üretirdi — tam da önlemeye çalıştığımız
şey. Tutma = `SPIKE_LEAD_S`, yeni sabit yok.

⛔ **KAPI POST-COMMIT MANEVRAYI ÖNLEMEZ — ölçüldü.** Iska #2'de bağlanma anında
nişan OTURMUŞTU (`e_cy` = +35 px) ve 2.6 s boyunca içeride kaldı; hedef ondan
SONRA tırmandı (`e_cy` −65 → −93 → −195). Yani kapı *kötü nişanla bağlanmayı*
engeller, *bağlandıktan sonraki manevrayı* engellemez. Bunun çaresi çarpma
fazında bir **iptal** koşulu olurdu (nişan pencereden çıkıp kalırsa görsel faza
dön); yazılmadı — thrashing riski var ve ölçülmedi.

⚠ **TEK UÇUŞ (n=7 koşu).** Ayrım temiz ama eşiğin kendisi canlıda doğrulanmadı.

### ÇARPMA YASASI — `control/spike.py`

Görsel fazdan **tek farkı ileri hız ve dikey nişandır**; yaw ve dikey kanal
sabitleri `VisualCfg`ten OKUNUR (zarf tek kaynakta).

| | GÖRSEL (`visual_tracking`) | ÇARPMA (`spike`) |
|---|---|---|
| ileri hız | kapanma denetimi, profil `TRAIL_RANGE_M`(4.5 m)'de sıfırlanır | **PI, sıfır noktası `ATTACK_RANGE_M`(1 m) = TEMAS** |
| davranış | kuyruğa oturur ve **kalır** | hata hep pozitif → hız tavanda **oturur** |
| dikey nişan | tek sabit `CY_REF = 470` | **470 → 540 harmanı** (kutu 40→90 px) |

Sabitler (`K_FWD=0.35`, `K_I=0.04`, `I_MAX=8.0`, `CY_REF_FAR/NEAR=470/540`,
`CY_BLEND_PX_FAR/NEAR=40/90`) **bu deponun kendi git geçmişinden** geri alındı
(`47eeddd~1`), kardeş depodan kopyalanmadı — ikisi zaten aynı ölçüm soyundandır
ve birebir aynıdır.

⚠ **SÜZGEÇ YOK, BİLİNÇLİ.** Görsel fazda `size`e medyan uygulanır; çarpmada
uygulanmaz. İki sebep: (1) terminal fazda kutu devdir (1–3 m'de 330–1000 px
@1920), bağıl gürültü küçüktür; (2) medyan bir rampayı pencere/2 = 0.1 s
geciktirir, `V_ATTACK` 28 m/s'de bu **2.8 m bayat menzil** — `ATTACK_RANGE_M`in
kendisinden büyük. Terminal fazda gecikme gürültüden pahalıdır.

⛔ **FAZ GEÇİŞİNDEKİ DİKEY BASAMAK GİDERİLDİ (2026-08-27).** İlk sürümde
görsel faz hedefi `CY_REF=470`'te tutuyor, çarpma fazı ise nişanı **anında**
540'a kaydırıyordu. Kök neden devralınan harman sabitleriydi: 40→90 px
(~25 m → ~11 m). O eşikler terminal nişanın UZUN bir yaklaşma boyunca kaydığı
bir mimariden geliyor; **bizde çarpma fazı ~5 m'de açılıyor ve kutu orada
zaten ~199 px**, yani harman geçiş anında ÇOKTAN doymuş (k=1.0) oluyordu.

Ölçüldü: `e_cy` basamağı **−70 px** → `vz` +0.98 m/s → throttle
`HOVER_THR`(−0.586) → 0.000 = **0.586 birim = `MAX_DELTA`nın 3.9 katı** →
eğim sınırı **78 ms doyuyor**. Bu, ileri kanaldaki basamaktan (2.9×) daha
kötüydü ve dikey kanaldaydı.

⛔ **ZAMANLA YAYMAK ÇÖZMEZ** — ölçülmüş throttle haritasında "yumuşak
tırmanma" bölgesi YOK: pozitif dal `POS_INTERCEPT`(0.869 m/s)'ten başlar ve
[0,1]'e kırpılır, dolayısıyla `HOLD_BAND`(0.05) aşılan HER an throttle aynı
basamağı atar. Rampanın hızı fark etmez.

⭐ **ÇÖZÜM YAPISAL: harman faza GİRİŞTEKİ kutu boyutuna çapalanır.** Girişte
k=0 → nişan = `VisualCfg.CY_REF` → görsel fazın hedefi tuttuğu yerin ta
kendisi → `e_cy = 0` → **basamak yok**. Harman `ATTACK_RANGE_M`den türeyen
temas kutusunda tamamlanır. `CY_REF_FAR` artık sabit değil,
`VisualCfg.CY_REF`ten OKUNUR — ikisi ayrı yazılırsa fark doğrudan basamağa
dönüşür. Yeni tune düğmesi yoktur; `CY_BLEND_PX_FAR/NEAR` silindi.

Doğrulandı — geçiş anındaki throttle adımı, giriş menzilinden BAĞIMSIZ olarak:

| giriş menzili | 8 m | 6 m | 5 m | 4 m | 3 m |
|---|---|---|---|---|---|
| eski (sabit harman) | 0.586 | 0.586 | 0.586 | 0.586 | 0.586 |
| **yeni (girişe çapalı)** | **0.000** | **0.000** | **0.000** | **0.000** | **0.000** |

(eski kolda basamak her menzilde `MAX_DELTA`nın 3.9 katıdır — harman zaten
doymuş olduğu için giriş menzilinden bağımsızdır.)

Kapalı çevrimde de kötüleşme yok: HOVER↔tırmanma rejim değişimi **2 → 0**,
throttle aralığı daralıyor (−0.595…−0.286 → −0.593…−0.436).

⚠ Throttle haritasının `HOLD_BAND` sıçraması **giderilmedi ve giderilemez** —
ölçülmüş araç davranışıdır, görsel fazda da vardır ve canlı kayıtlarda sistem
onunla %89.6 tespitle çalışıyor. Düzeltilen şey yalnızca FAZ GEÇİŞİNDEKİ
basamaktır.

⛔ **TERMİNAL SÜREKLİLİK İSTİSNASI** (`VisualCfg.TERMINAL_GROWTH = 2.0`).
`RANGE_MIN_M`(3 m) altındaki kutu normalde reddedilir; çarpmanın nişanı 1 m
olduğuna göre bu, vuruşun son yarım saniyesinde güdümü **kendi süzgecimizin**
kör etmesi demektir. Kapı silinmez (140 m'deki dev yanlış-pozitif iki kez
aracı yere çaktı, "Player ☠"); ayırt edici fizik kullanılır: **dev
yanlış-pozitif yoktan var olur, gerçek hedef büyüyerek gelir.** İstisna (a) son
kabul edilen kutunun taze olmasını (yaş ≤ `BRIDGE_S`) ve (b) yeni kutunun ondan
en fazla 2 kat büyük olmasını arar.
⭐ **Yapısal olarak faz kapsamlıdır**: gözetmen `last_size`/`last_age`'i
YALNIZ SPIKE fazında geçirir; verilmezse `aim_box` bit bit eski davranışındadır.
⛔ GPS yok — koşulun iki girdisi de piksel ve zamandır (§KATI KURAL temiz).

⚠ **HİÇBİRİ OYUNDA KOŞTURULMADI.** Kuru koşuda doğrulananlar: kapı tam 10.0 s'de
açılıyor, taze kutu yokken açılmıyor, geriye uyumluluk bozulmadı (girdisiz
`aim_box` aynı), terminal istisna dev yanlış-pozitifi (2.46 kat) reddediyor,
faz akışı KALKIŞ→GPS→GÖRSEL→ÇARPMA→(kayıp)→GPS temiz.

Görsel fazda `Cfg.LOST_S` (2.0 s) boyunca geçerli kutu gelmezse GPS fazına
dönülür. **Süre cinsinden** yazıldı ki kamera thread'i donarsa da tetiklensin
(donmuş kamerada kare sayacı ilerlemez) — devir kapısı da aynı gerekçeyle
süreye bağlandı.

---

## GÖREVİ DURDURUP YENİDEN BAŞLATMA (2026-08-27)

**Belirti:** görev durdurulup yeniden başlatıldığında araç sapıtıyordu ve
düzelmesi için **sunucuyu kapatıp açmak** gerekiyordu. Dört ayrı kusur vardı;
ikisi `web/server.py :: mission_start`'ın erişemediği MODÜL durumundaydı — bu
yüzden yalnızca süreç yeniden başlatınca temizleniyorlardı.

### 1. Sıcak GNSS filtresi görev başında çöpe atılıyordu ⛔ ASIL SEBEP
`control_loop` görev PASİFKEN de her tik `clean_target()` çağırır; tek amacı
filtrenin ısınmış kalmasıdır. Ama `mission_start` → `brain.reset()` filtreyi
**yeniden kuruyordu** — yani o satır fiilen ölü koddu ve her görev SOĞUK
filtreyle başlıyordu.

İlk görevde bunu **kalkış maskeler** (~4 s sürer, o sırada yatay komut
üretilmez). Görev **havadayken** yeniden başlatılırsa kalkış kapısının 2. kolu
(`TAKEOFF_TARGET_GAP_M`) daha ilk tikte açılır, kalkış saniyenin onda birinde
biter ve **maske kalkar**: ısınma transienti doğrudan istasyon fazına, yani
yatay komutun ÜRETİLDİĞİ yere düşer.

⭐ **ÖLÇÜLDÜ** (havadayken yeniden başlat, hedef 18 m/s, 5 Hz paket + 50 cm
gürültü + %4 sıçrama + 1.13 s gecikme, 4 tohum, istasyon fazının ilk 1.5 s'i):

| `brain.reset()` davranışı | hedef konum hatası medyan | p90 | MAX |
|---|---:|---:|---:|
| ESKİ — filtre yeniden kurulur | **39.2 m** | 76.0 m | **80.8 m** |
| **YENİ — filtre korunur** | **2.5 m** | 4.9 m | 6.3 m |

40–80 m yanlış hedef, istasyon yasasına doğrudan büyük bir hız komutu olarak
girer; çevirici bunu tam çubuğa çevirir (`MAX_DELTA = 0.15` ile 7 tikte, yani
0.14 s'de doyar). "Sapıtma" tam olarak budur.

⚠ **SICAK TAŞIMANIN TEK İSTİSNASI: filtre kilidini kaybetmişse.** Oyun yeniden
başlatılıp hedef BAŞKA YERDE doğarsa sıcak filtre eski kilidinde kalır.
`GPSTracker._filter_lost()` bunu filtrenin KENDİ teşhisinden okur (`ret` = üst
üste kapı reddi ≥ `escape_thresh/2`) ve o durumda soğuk kurar. Ölçüldü (hedef
500 m ışınlandı, n=4): kaçış mekanizması ~11 tikte devreye giriyor, yeniden
kilitlenme **medyan 2.60 s / max 2.80 s**; soğuk kurulum ise ~0.40 s'de çıkış
verir. Elle zorlamak: `brain.reset(cold_filter=True)`.

### 2. Takipçi sıfırlaması bir bayrağa bağlıydı, kenara değil ⛔ MODÜL DURUMU
`camera.loop` şöyleydi: `if tracker.tracks: tracker.reset()`. Görev **son
karesinde hedef yoksa** `tracks` boş olur → sıfırlama ATLANIR → HybridSort
örneği (iç Kalman izleri + kare sayacı) bir sonraki göreve taşınır. Takipçi
izleri `max_age` kadar ileri taşıdığı için yeni görev **hayalet kutuyla**
açılırdı. Artık aktif→pasif **kenarında koşulsuz** sıfırlanır (örnek yeniden
kurulur), pasifken bir daha değil.

### 3. Üretici–tüketici arasındaki tek kare görevler arası yaşıyordu ⛔ MODÜL
`_latest` görevler arası duruyordu; tüketici yeni görevde `last_seq = 0` ile
başladığı için oradaki ÖNCEKİ GÖREVDEN kalma kareyi "yeni" sanıp işliyor ve
`detection_state`'e **o anın** zaman damgasıyla yayınlıyordu — yani kare bayat
olduğu hâlde TAZE görünüyor ve `is_stale()` onu yakalayamıyordu.
`camera.reset()` o kareyi düşürür; `mission_start` çağırır.
(`DeviceSource.drain()` ÜRETİCİ tarafını temizler — bu ise aradaki tek kareyi.)

### 4. Görev çıkarımın ortasında durursa sonuç yine yayınlanıyordu
`detect_all` + takipçi ~14 ms sürer. `loop()` en başta `active()` bakıp sonra
koşulsuz `publish()` ediyordu; görev o arada durursa sonuç bir sonraki görevin
ilk karesi olarak görünürdü. `mission_start`'ın `detection_state.reset()`'i
bunu kaçırır, çünkü yayın ondan SONRA gelir. Artık yayından önce `active()`
yeniden bakılır.

⚠ **KALKIŞ ZEMİN REFERANSI HAVADA ALINIR — bilinçli olarak dokunulmadı.**
`takeoff.reset()` → `_ground_z = None` → ilk tikte O ANKİ irtifa "zemin"
sayılır, yani `height` havada 0'dan başlar. Kapının 2. kolu (hedefin
irtifasına `TAKEOFF_TARGET_GAP_M` kadar yaklaşıldı) bu durumu zaten
karşıladığı için araç boşuna tırmanmaz. Sıcak filtreyle birlikte `target_p`
ilk tikte hazır olduğu için kapı **doğru veriyle** karar verir.

---

## GÖRSEL MODEL — `perception/models/talon_v3`

| | best (eski) | **talon_v3 (aktif)** |
|---|---|---|
| eğitim `imgsz` | 640 | **960** |
| epoch / ultralytics | 200 / 8.4.90 | 60 / 8.4.83 |
| taban / görev / sınıf | yolo11s / detect / `talon` | aynı |

⛔ **`IMGSZ` MODELDEN TÜRETİLİR** (`perception/detector.py`). Modeli değiştirip
`IMGSZ`'yi unutmak **sessiz** bir bozulmadır: çıkarım eğitimden farklı ölçekte
koşar, önce uzak/küçük hedef kaybolur, sonra görsel faz hiç açılmaz. Bu yüzden
eşleme kodda tablo olarak duruyor. Geri alma: `AVCI_MODEL=best.pt` (IMGSZ
kendiliğinden 640'a döner), elle ezme: `AVCI_IMGSZ=...`.

⭐ **TABLO UZANTISIZ ANAHTARLANIR** (`talon_v3` → 960, `best` → 640). Aynı
ağırlığın `.pt` ve `.engine` sürümü **aynı** ölçekte koşmak zorundadır;
uzantıyla anahtarlansaydı motor tabloda bulunamaz ve sessizce 640'a düşerdi.

### TensorRT motoru — `talon_v3.engine` (2026-08-27, **FP32**)
Dedektör, `perception/models/` içinde `talon_v3.engine` **varsa onu** yükler;
yoksa `.pt` koşar. `AVCI_ENGINE=0` motoru atlar. Üretim (çevirir, ölçer, `.pt`
ile ham çıktıyı karşılaştırır):

```
python -m scripts.export_engine --fp32     # ⭐ bu depoda kullanılan
python -m scripts.export_engine            # FP16 (betiğin varsayılanı)
```

⭐ **FP32 SEÇİLDİ (kullanıcı kararı).** FP32 motor `.pt` ile **birebir aynı**
sayıyı üretir (skor farkı max 0.00000). Bedeli hızdır: FP16 motor aynı kartta
1.34× daha hızlı (10.36 vs 13.85 ms) ve dosyası yarı boyutta. Ölçümler
§ÖLÇÜLMÜŞ HAT BÜTÇESİ'nde.

⭐ **ÖLÇÜ MOTORUN KENDİ BAŞLIĞINDAN OKUNUR**, yukarıdaki tablodan değil
(`detector.engine_imgsz`, salt stdlib — torch import etmez). Static motorun
girdi şekli derlenirken sabitlenir; ikinci bir yerde tutulan bir sayı yoktur.

⛔ **`AVCI_IMGSZ` MOTORU EZEMEZ.** Farklı ölçek TensorRT arka ucunda assert
atar ve `detect_all` **sessizce boş liste** döndürür. Çakışma görülürse sistem
kendiliğinden `.pt`'ye düşer — böylece uzak menzil taraması (`AVCI_IMGSZ=1920`)
çalışmaya devam eder. Motoru başka ölçekte istiyorsanız **yeniden üretin**.

⛔ **MOTOR TAŞINMAZ.** `.engine` şu karta, şu sürücüye ve şu TensorRT sürümüne
derlenir; başka makinede açılmaz (bu yüzden `.gitignore`'da). Açılmazsa
`TargetDetector` sessizce değil, **gerekçesiyle** `.pt`'ye döner
(`self.fallback` → `camera.py` ekrana basar).

⚠ **`RANGE_C_REF` MOTORDAN ETKİLENMEZ AMA DOĞRULANMALI.** Motor aynı ağırlığın
FP32 derlemesidir ve ham çıktısı `.pt` ile **birebir** örtüşüyor (skor farkı
max 0.00000, n=18900 çapa) — yani kutulama sıkılığı değişmiyor. Aşağıdaki
`RANGE_C_REF` uyarısı motor yüzünden değil, **kalibrasyon** yüzünden geçerlidir.

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

⭐ **PROFİL `TRAIL_RANGE_M`'DE SIFIRLANIR, `ATTACK_RANGE_M` (1 m) DE
DEĞİL.** `RANGE_MIN_M`(3 m) altında `aim_box` kutuyu reddeder, ardından
`BRIDGE_S`(1 s) + `LOST_S`(2 s) gelir → **3 saniye kör uçuş**. 1 m'ye regüle
etmek kapalı çevrimde ulaşılamayan bir noktaya nişan almaktır; eski yasa orada
28 m/s bıraktığı için araç hedefin ~30 m **önüne geçiyordu**. Profil görü
sınırının ÜSTÜNDE sıfırlanınca araç hedefin **kuyruğuna oturur ve orada kalır**.

⛔ **`TRAIL_RANGE_M` 3.0 → 4.5 m (2026-08-27) — SIFIR MARJ DÖNÜŞTE HEDEFİ
KAÇIRIYORDU.** Sabit `RANGE_MIN_M` ile **birebir eşitti**: yasa aracı tam
olarak ret sınırına oturtuyordu. Hedef dönüşte bank yapınca görünüş açısı
değişip kutu büyüyor, `R = C/size` **küçük** okunuyor ve zincir kuruluyor:

```
kutu buyur -> R < RANGE_MIN_M -> aim_box RED -> BRIDGE_S(1 s, ileri hiz donuk)
           -> kopru biter, roll/yaw sifirlanir -> LOST_S(2 s) -> GPS fazi
           -> hedef bu 3 saniyede donusunu tamamlar
```

Ölçüldü (gerçek yasa, kapalı çevrim: `aim_box` → köprü → `LOST_S`; hedef
18 m/s, 6 s dönüş, dedektör 10 Hz; kolonlar dönüş hızı / sahte kutu büyümesi):

| `TRAIL` | 15°/%50 | 15°/%100 | 25°/%50 | 25°/%100 | 40°/%50 | 40°/%100 |
|---|---|---|---|---|---|---|
| **3.0 (eski)** | KAYIP | KAYIP | KAYIP | KAYIP | KAYIP | KAYIP |
| 4.0 | 3.4 m | 3.2 m | 3.4 m | KAYIP | 3.5 m | KAYIP |
| **4.5 (aktif)** | 3.9 m | 3.6 m | 3.9 m | 3.4 m | 4.0 m | KAYIP |
| 5.0 | 4.4 m | 4.1 m | 4.3 m | 3.9 m | 4.4 m | 4.4 m |

Marj **türetilir, yeni tune düğmesi değildir**: `TRAIL_RANGE_M ≥ RANGE_MIN_M ×
(1 + g_max)`. 4.5 = 3.0 × 1.5, yani **g_max = %50 varsayımı**.

⭐ **g_max ÖLÇÜLDÜ** (canlı kayıt, aşağıya bak): 0.5 s penceresinde kutu
tepe/taban oranı p90 = **1.58**, p99 = 3.76 → gereken marj 3.0 × 1.58 = 4.74 m.
4.5 bunun hemen altındadır ve bilinçlidir: p90 geçici bir olaydır (on karede
bir) ve `BRIDGE_S`(1 s) onu yutar. ⛔ **AŞAĞI ÇEKMEYİN** — 3.5/4.0 sırasıyla
g>%17 / %33 olan her kareyi reddeder, ölçülen medyan oran ise 1.10'dur.

⛔ **`RANGE_MIN_M`'i DÜŞÜREREK ÇÖZMEYİN** — o kapı 140 m'deki dev
yanlış-pozitifleri kesen kapıdır (iki koşu, "Player ☠").

⚠ Denenip **işe yaramayan** aday: `R`'nin `V_CLOSE_MAX`'tan hızlı küçülmesini
engelleyen hız sınırı — altı kolun hiçbirini değiştirmedi. Sorun değişim
*hızı* değil, kararlı noktanın sınırın üstünde olmasıdır.

⚠ Bu tablo **simülasyondur** ve çeviriciyi atlar (`MAX_DELTA`, 0.211 s yatış
sabiti, 46 ms ölü zaman) → gerçek araç daha hantaldır. Hedef sabit 18 m/s
koordineli dönüşte modellendi. ⛔ **Canlı kayıtta `R<3` reddi HİÇ OLMADI**
(min R = 4.5 m): marj gerçek bir yapısal koruma ama gözlenen kaçışın sebebi
DEĞİLDİ — sebep aşağıdaki `Rdot` hatasıdır.

### ⛔ `Rdot` FİZİKSEL KAPAMASI (2026-08-27) — GÖZLENEN KAÇIŞIN ASIL SEBEBİ

Canlı kayıt analizinde (135 s / 3567 kare / 1280×720, TensorRT motoru, her
kareye gerçek `aim_box`) kaçışın kök nedeni bulundu ve **koddadır**:

```
kutu boyutu gurultusu   ardisik iki karede 4.26 KAT sicrama (olculdu)
  -> R = C/size          gurultuyu aynen devralir
  -> Rdot ham turev      |Rdot| MAX 1085.77 m/s   <- fiziksel olarak imkansiz
  -> _v_tgt_los          SIFIRA cokuyor (min 0.00 m/s)
  -> v_cmd               MIN 3.49 m/s, hedef 18 m/s ucarken
  -> arac yavasliyor     OSD dogruluyor: t=67.2 s'de SPD 31 km/h (seyir 64-66)
  -> hedef kadrajdan CIKIYOR -> "tespit yok" -> LOST_S
```

⭐ **NEDENSELLİK ÖLÇÜLDÜ, VARSAYILMADI.** Uzun "kutu yok" epizotlarının
**7/8'i**, öncesindeki 3 s içinde `v_cmd` 12 m/s altına düşen epizotlardı
(tek istisna ilk yakalama anı). Yani fren önce, tespit kaybı sonra geliyor.

Düzeltme `_closing_speed` içinde tek satırdır ve sınır `V_CLOSE_MAX`'tan
**türer** (yeni tune düğmesi yok): yasa zaten bundan hızlı kapanma komut
etmez. Gerçek tespit dizisiyle ölçüldü:

| kol | v_cmd min | v_cmd med | `v_cmd < 18 m/s` |
|---|---:|---:|---:|
| kapama yok (eski) | 3.49 | 20.13 | **%11.0** |
| `\|Rdot\| ≤ 28` (`V_MAX`) | 12.89 | 20.30 | %5.4 |
| **`\|Rdot\| ≤ 12` (`V_CLOSE_MAX`) ⭐ AKTİF** | **16.35** | **20.39** | **%3.0** |

Medyan davranış değişmiyor (20.13 → 20.39) — kapama sağlıklı rejime dokunmaz,
yalnız imkânsız değerleri keser.

⭐ **MODEL SUÇLU DEĞİL.** Aynı analizde: YOLO karelerin **%87.6**'sında kutu
üretti, **%84.2**'si `aim_box`'tan geçti, medyan güven **0.88**. Kapı reddi
yalnız %3.5 (conf<0.40 %3.0, R>50 %0.4, kırpık %0.1). "Tespit yok" denen
%12.4'lük kısımda hedef karelerde **fiilen yok** — model görünen hedefi
kaçırmıyor, hedef görüş alanında değil. `talon_v3`'e dokunmayın.

⚠ **DÜZELTME OYUNDA KOŞTURULMADI.** Yukarıdaki sayılar kaydedilmiş tespit
dizisinin yasadan geçirilmesiyle üretildi (açık çevrim): fren epizotları
ortadan kalkıyor, ama düzelmiş komutun hedefi gerçekten yakalayıp
yakalamadığı **canlı uçuşla doğrulanmalı**.

⭐ **DÜZELTME CANLIDA DOĞRULANDI (2. kayıt, 215 s).** OSD hızları: t=25s 74,
55s 65, 66s 64, **72s 83, 78s 95**, 95s 65, 130s 69, 180s 65 km/h. Kayıp
anında araç frenlemek yerine neredeyse tam gazla kovalıyor (95 km/h =
26.4 m/s, `V_MAX` 28). Kanıt özellikle güçlü: 2. kaydın kutu gürültüsü **daha
kötü** (imkânsız `|Rdot|>28` oranı %10.2 → %34.0), yani eski kod koşsaydı fren
daha SIK olurdu.

⚠ **AMA GENEL PERFORMANS İÇİN HÜKÜM YOK — n=1/kol.** Değişiklik öncesi bir,
sonrası bir uçuş var; ikisi farklı angajmanlar (medyan menzil 8.8 m vs
17.4 m). Kural sonucu: kilit %86.3 → %79.5, en uzun kesintisiz 28.2 → 19.8 s,
≥5 s sağlayan 10 s pencere %94.8 → %87.7 — ikisi de kuralı geçiyor.

### ⛔ SÜZGEÇ `size`'A UYGULANIR, `R`'YE DEĞİL (2026-08-27)

`R = C/size` bir **terslemedir**: `size`'daki simetrik piksel gürültüsü,
tersleme sonrası **çarpık ve ağır kuyruklu** olur (küçük kutunun aşağı
titremesi R'de dev sıçrama üretir). Süzgeci R'ye uygulamak, o sıçramaları
süzgecin İÇİNE almak demektir. Bu yüzden medyan artık `compute()` içinde
`size` üzerinde, `R`'den ÖNCE çalışır.

- **Medyan, ortalama/EMA değil** — gürültü darbelidir (ardışık iki karede
  4.26 kat sıçrama ölçüldü); EMA darbeyi silmez, zamana yayar.
- **Pencere süreyle, kare sayısıyla değil** — dedektör hızı değişkendir,
  "son N kare" bir süre değildir ve hat hızlandıkça süzgeç sessizce zayıflar
  (devir kapısındaki dersin aynısı).
- **Pencere = `R_TAU`**, yeni tune düğmesi yok.
- **Köprü kareleri tampona girmez** (aynı kutuyu tekrar beslemek medyanı
  yapay olarak dondururdu).

⚠ **İKİ ÖLÇÜT ÇELİŞİYOR — canlı uçuşla karara bağlanmalı.** Aynı kod yolunda
A/B (tek fark bu medyan):

| ölçüt | video 1 | video 2 | |
|---|---|---|---|
| `\|Rdot\|` medyan | 4.16 → **1.65** | 12.00 → **5.08** | ⭐ |
| kapama doyumu | %21.3 → **%9.1** | %59.2 → **%26.7** | ⭐ |
| `v_fwd` p10 | 19.17 → 18.98 | 20.67 → 19.82 | ⛔ |
| `v_fwd < 18 m/s` | %3.0 → %4.7 | %1.9 → %3.6 | ⛔ |

Kestirim belirgin temizleniyor, komut biraz tembelleşiyor (medyan bir rampayı
pencere/2 = 0.1 s geciktirir). ⛔ **Replay AÇIK ÇEVRİMDİR** ve kayıt eski
yasayla uçulmuş bir yörüngeden gelir; ayrıca "v<18" ölçütü hedefin 18 m/s
uçtuğu VARSAYIMINA dayanır. Geri alma: `compute()` içinde `size` yerine
`size_raw` kullan.

⭐ **EMA ve KAPAMA hâlâ yerini hak ediyor** — ikisi de kaldırılınca kötüleşti
(`v<18`: %4.7 → %6.2 EMA'sız, → %8.9 kapamasız; video 2'de → %5.9 / %13.9).

⛔ **DENENDİ, İŞE YARAMADI — HAMPEL** (medyanı sinyal değil aykırı-değer
reddedici kullanmak; normal karede ham boyutu geçir, gecikme sıfır).
K=1.5/2.0/3.0'te karelerin yalnız %0.2–2.0'si reddedildi ve `|Rdot|` medyanı
video 2'de **12.00'de kaldı**. Sebep: bu gürültü ara sıra gelen darbe değil,
**sürekli geniş bantlı titremedir** — her kare biraz yanlıştır, ayıklanacak
tek bir aykırı yoktur. Gerçek yumuşatmanın alternatifi yok; gecikme bedeli
kaçınılmaz.

⭐ **TELEMETRİ**: `VisualTracker.status()` artık hem `size_px` (süzülmüş) hem
`size_raw` yayınlar — canlı tune ederken ikisinin farkı süzgecin ne kadar iş
yaptığını doğrudan gösterir.

⭐ **HÜCUM (SPIKE) YASASI GERİ GELDİ — ama kendi fazında** (2026-08-27).
2026-08-25'te görsel takip yasasından silinmişti ("şu anki amaç temas değil,
kamera takibini iyileştirmek") ve o gün "spike fazına 10 s'lik görsel güdümden
sonra geçilecek" diye not düşülmüştü. O faz artık yazıldı: **`control/spike.py`**.
Görsel takip yasası DEĞİŞMEDİ — kuyruğa oturmaya devam ediyor; hücum ayrı bir
fazda ve ayrı bir modülde. Aşağıdaki tarihsel not, silinme gerekçesi olarak
geçerliliğini korur.
`ATTACK_RANGE_M`, `K_FWD`, `K_I`, `I_MAX` ve `CLOSE_CONTROL` anahtarı önce
`compute()` dalından, sonra (yorum satırı olarak da) `VisualCfg`'den tamamen
silindi — kodda hiçbir izi kalmadı, ölçülmüş değerleri git geçmişindedir
(`47eeddd`, `a3e77f9`). Bu **güdüm davranışını değiştirmedi**: aktif yasa
zaten kapanma denetimiydi ve kuyruğa oturuyordu.

⛔ **TERMİNAL KADRAJ KAYMASI DA KALDIRILDI** (2026-08-25, aynı gerekçe).
Dikey referans `CY_REF_FAR`(470) → `CY_REF_NEAR`(540) arasında kutu boyutuyla
harmanlanıyordu ("yakında merkeze al, nişan al"); bu **spike'a nişan alma**
davranışıydı. Artık tek sabit referans var: `VisualCfg.CY_REF = 470 px @1080`.
`CY_BLEND_PX_FAR`/`CY_BLEND_PX_NEAR` ve `nearness` telemetrisi silindi.
⚠ Bu **güdüm davranışını DEĞİŞTİRİR**: kutu 40 px'ten büyükken (R < ~25 m)
nişan noktası eskiden merkeze kayıyordu, artık kaymıyor — hedef son metrelerde
kadrajda daha yukarıda tutulur. Spike fazı yazılırken bu kayma **o faza**
konmalıdır, görsel takip yasasına değil.

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
- Kalan tek kaldıraç **TensorRT**'dir: katman füzyonu tam da kernel başlatma
  giderini hedefler. **ÖLÇÜLDÜ, aşağıda** — ama `.engine` sürücüye ve GPU'ya
  bağlıdır, her kart için ayrı üretilir.

⚠ **DAHA BÜYÜK GPU BU SORUNU ÇÖZMEZ.** Kernel başlatma gideri sürücü/CPU
tarafındadır. A100 büyük yığın (batch) ve büyük modelde parlar; bizimki tek
kare, 49 GFLOPs'luk küçük bir iş yükü ve A100'ün taban saati bir dizüstü
Blackwell'den düşüktür → kare başına süre aynı ya da biraz **kötü** çıkabilir.
Donanım değişikliğinden gecikme kazancı beklemeden önce **o kartta ölçün**.

⚠ **ÖLÇÜM KOŞULU: OYUN KAPALIYDI.** Unreal aynı GPU'yu kullanırken sayılar
kötüleşir; darboğazın *yeri* değişmez, *büyüklüğü* değişir.

### TensorRT ÖLÇÜLDÜ (2026-08-27, aynı kart, oyun KAPALI)

`talon_v3` @ imgsz 960, static (batch 1), TensorRT 11.1.0.106.
**Derlenen motor FP32'dir** (kullanıcı kararı); FP16 karşılaştırma için
ölçülmüştür, depoda durmaz.

⚠ **ÖLÇÜM GÜÇ DURUMU: PRİZDE DEĞİL + "Silent" profili, GPU 47 W sınırında**
(`nvidia-smi`: SM 1725–2317 MHz, tavan 3090). Bu bir kusur değil, ölçümün
koşuludur — **oran güç durumuna duyarlıdır**, aşağıya bakın.

Her kol **ayrı süreçte**, 3 tur dönüşümlü, 4 s kesintisiz ısınma sonrası
8 blok × 25 kare (n=200/kol), 1920×1200 kare, `detect_all()`:

| kol | kare başı | FPS | `.pt`'ye göre | motor dosyası |
|---|---:|---:|---:|---:|
| `.pt` (FP16 çıkarım) | 19.50 ms | 51.3 | 1.00× | — |
| **`.engine` FP32 ⭐ AKTİF** | **13.85 ms** | **72.2** | **1.41×** | 40.2 MB |
| `.engine` FP16 | 10.36 ms | 96.5 | 1.88× | 20.5 MB |

Aynı oturumda, `scripts/export_engine` ölçümü (n=60):

| ölçüm | `.pt` | `.engine` FP32 |
|---|---:|---:|
| saf arka uç ileri geçişi | 13.07 ms | **7.59 ms** (1.72×) |
| ultralytics `predict()` (ön işleme + NMS dahil) | 18.67 ms | **13.68 ms** (1.36×) |

⭐ **FP32 MOTOR `.pt` İLE BİREBİR AYNI SAYIYI ÜRETİYOR** — skor farkı max
**0.00000** (n=18900 çapa). FP16 motorda bu fark 0.00001'di; ikisi de güdüm
için fazlasıyla küçük, ama FP32 sıfır. Kutulama sıkılığı değişmediği için
`RANGE_C_REF` motordan **etkilenmez**.

⛔ **FP32'İN BEDELİ HIZ, KAZANCI KESİNLİK.** FP16 motor bu kartta FP32'den
**1.34× daha hızlı** (10.36 vs 13.85 ms) ve dosyası yarı boyutta. FP32
seçildiyse gerekçe sayısal birebirliktir, performans değil. Geri dönüş tek
komut: `python -m scripts.export_engine` (varsayılan FP16).

⛔ **ORAN GÜÇ DURUMUNA BAĞLI — TEK BİR ÇARPAN YAZMAYIN.** Aynı gün, makine
daha yüksek güç durumundayken ölçülen kol: `.pt` 9.24 ms, FP16 motor 7.58 ms
→ kazanç yalnız **1.22×**. Yani GPU tam saatteyken `.pt` hızlanıyor ve motorun
üstünlüğü eriyor; güç sınırlıyken `.pt` daha çok kaybediyor ve motor öne
çıkıyor. Mekanizma: motorla kalan sürenin çoğu **CPU tarafındaki ultralytics
gideridir** (letterbox, tensöre kopya, NMS, `Results`) ve bu GPU saatiyle
ölçeklenmez. ⚠ Görev sırasında Unreal **aynı GPU'yu** kullanacağı için
gerçek durum "güç/kaynak sınırlı" tarafa yakındır — ama bu **ölçülmedi**.

⛔ **UÇTAN UCA KAZANÇ, SAF İLERİ GEÇİŞTEKİNDEN KÜÇÜKTÜR** (1.36× vs 1.72×)
çünkü darboğaz yer değiştirdi: motorla birlikte kalan sürenin çoğu artık
ultralytics'in kendi giderindedir. Bir sonraki kaldıraç TensorRT değil,
**o katmandır**.

⚠ **MOTOR KARE letterbox'a KARE ÖDER.** `.pt` yolu `rect=True` ile 960×608
koşar (1920×1200 için), static motor 960×960'a doldurur — yani **1.58 kat
piksel** işler ve yine de daha hızlıdır. Ölçek ikisinde de aynıdır
(960/1920 = 0.5), dolayısıyla kutu boyutları ve `RANGE_C_REF` değişmez;
fark yalnızca gri dolgudur. Dikdörtgen motor üretmek biraz daha kazandırırdı
ama motoru **tek en-boy oranına** bağlardı: kaynak oranı değişince ölçek
düşer ve uzak menzil tespiti bedavaya kaybedilir. **Kare kalsın.**

⚠ **FP16 GİRDİ/ÇIKIŞ DEĞİL, İÇERİDEDİR.** Ultralytics FP16 motorda bile
`images` bağlantısını FP32 bırakır. Arka uca yanlış tipte tensör verilirse
TensorRT bitleri olduğu gibi yorumlar — **şekil doğru olduğu için assert de
atmaz** — ve çıktı çöp olur (ilk ölçümümüzde tam olarak bu oldu: skor farkı
0.00001 yerine 659 çıkmıştı). `predict()` bunu kendi halleder; elle ölçerken
`AutoBackend.fp16`'ya bakın.

⚠ **ÖLÇÜM YÖNTEMİ — üçü de gerekli, yoksa sayı uydurursunuz.**
1. **GPU boşta 315 MHz'e düşer.** Kısa ısınmayla ölçmek saat rampasını
   ölçmektir; yukarıdaki ölçüm **4 s kesintisiz** çıkarımdan sonra başlar.
2. **Her kolu AYRI SÜREÇTE ölçün.** Birden çok modeli aynı süreçte tutup
   dönüşümlü koşturduğumuzda sayılar tek-model ölçümüyle tutarsız çıktı.
3. **Farklı oturumların sayılarını karşılaştırmayın.** Güç durumu değişince
   tüm kollar birlikte kayar (bkz. güç durumu uyarısı); yalnız **aynı oturumda
   dönüşümlü** ölçülen kollar karşılaştırılabilir.

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

**TENSORRT MOTORU KURULDU AMA OYUNDA KOŞTURULMADI (2026-08-27).** Sayılar
oyun KAPALIYKEN ölçüldü (bkz. §ÖLÇÜLMÜŞ HAT BÜTÇESİ). Unreal aynı GPU'yu
kullanırken hem `.pt` hem `.engine` yavaşlar; oranın korunup korunmadığı
**ölçülmedi**. Kurulum: `pip install onnx onnxslim "tensorrt-cu13==11.1.0.106"`
(paket adı `torch.version.cuda`'nın ana sürümüyle eşleşmeli; sürüm pini için
aşağıdaki SAC maddesine bakın), sonra `python -m scripts.export_engine --fp32`.

⚠ **BAĞLAYICI/KÜTÜPHANE SÜRÜMLERİ BU MAKİNEDE EŞLEŞMİYOR** ve bu bilinçlidir:
bağlayıcı 11.1.0.106 (SAC'ın izin verdiği en yeni), kütüphaneler 11.2.1.2.
Aynı ANA sürüm oldukları için çalışıyor ve çıktı `.pt` ile birebir doğrulandı,
ama NVIDIA'nın desteklediği bir eşleşme değildir. Tam eşleşme için
`pip install "tensorrt-cu13==11.1.0.106"` (≈2 GB indirme) ve ardından motoru
**yeniden üretin** — TensorRT planı sürüme bağlıdır, eski motor açılmaz.

⛔ **MOTORU HER MAKİNEDE YENİDEN ÜRETİN.** `.engine` repoda yoktur ve
kopyalanamaz. Yeni bir kurulumda üretilmezse sistem sessizce değil, açıkça
`.pt` ile koşar — yani hız kaybı fark edilmeden geçmez.

⛔ **WINDOWS SMART APP CONTROL EN YENİ TensorRT'yi ENGELLİYOR** (bu makinede
`VerifiedAndReputablePolicyState = 1`). NVIDIA'nın **kütüphaneleri imzalıdır**
(`nvinfer_11.dll` → "NVIDIA Corporation", geçerli) ama Python **bağlayıcısı**
(`tensorrt.cp313-win_amd64.pyd`) imzasızdır ve SAC yalnızca *itibar kaydı olan*
imzasız dosyalara izin verir. Ölçüldü (`ctypes.WinDLL` ile, aynı oturumda):

| tensorrt-cu13 bağlayıcı | SAC |
|---|---|
| 10.13.3.9 … 11.1.0.106 | **geçiyor** |
| 11.2.1.2 (en yeni) | **WinError 4551 — engellendi** |

Yani çözüm **Smart App Control'ü kapatmak değil** (geri dönüşü yoktur), bir
önceki sürümü kurmaktır: `pip install "tensorrt-cu13==11.1.0.106"`. Yeni bir
sürüm çıktığında aynı duvara çarparsanız önce **bağlayıcı wheel'ini** (≈900 kB)
indirip `ctypes.WinDLL` ile deneyin — 2 GB'lık kütüphaneyi indirmeden önce
cevabı verir. Belirti: `ImportError: DLL load failed ... Uygulama Denetimi
ilkesi bu dosyayı engelledi`.

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
   zayıfsa `AVCI_IMGSZ=1920` deneyin (VRAM/FPS bedeliyle). ⚠ TensorRT motoru
   kuruluysa bu değişken motoru **ezemez**: sistem `.pt`'ye düşüp isteneni
   koşar. Motoru da o ölçekte istiyorsanız `AVCI_IMGSZ=1920 python -m
   scripts.export_engine` ile yeniden üretin.
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
| ortam değişkenleri (`AVCI_REGION`, `AVCI_DEBUG_WINDOW`, `AVCI_MODEL`, `AVCI_IMGSZ`, `AVCI_ENGINE`, `AVCI_DEVICE*`, `AVCI_CAP_FPS`, `AVCI_FP16`) | — |

Faz metni ile ekranda yazan etiket **ayrıdır**: kod `VISUAL` üretir, arayüz
`data-phase="VISUAL"` çipinde **GÖRSEL** gösterir. Birini diğerinin yerine
kullanmayın — çeviriyi tek yerde, HTML'de yapın.

⛔ **FAZ ETİKETİ GÖZETMENDEN GELİR, `brain.phase`E DÜŞÜLMEZ** (2026-08-27,
kullanıcı bildirdi). `web/server.py :: _watch_mission` eskiden şöyleydi:
"VISUAL değilse ve TAKEOFF değilse `brain.phase`". `GPSTracker.phase` **her
zaman** `"STATION"` ürettiği için, gözetmene eklenen **her yeni faz arayüzde
İSTASYON görünüyordu** — ÇARPMA fazı eklenince ortaya çıktı ("çarpma fazına
geçince görev istasyona dönmüş gözüküyor"). Sessiz bir hataydı: sistem doğru
çalışıyor, arayüz yanlış söylüyordu.

⭐ Artık **tersine kurulu**: etiket gözetmenin faz adından gelir, YALNIZ GPS
fazında `brain.phase`e devredilir (istasyon etiketini o üretir). Yeni bir faz
eklendiğinde arayüz onu artık YANLIŞ gösteremez — en fazla hiç çip yanmaz, ki
bu **görünür** bir eksikliktir, sessiz değil. Yeni faz eklerken `server.html`
içine `data-phase` çipini eklemeyi unutmayın.

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

# Avcı Drone — GPS Takip + Görsel Takip

Teknofest **Drones of War** simülasyonunda (Unreal Engine oyunu) hedef Talon
İHA'sını otonom takip eden yer kontrol yazılımı. Sistem **iki fazlıdır**:

1. **GPS fazı** — hedefin **bozuk GNSS** telemetrisi filtrelenip temizlenir,
   hız ve yön kestirilir; araç hedefin **kuyruğundaki istasyona** (8 m arkası,
   6 m altı) oturur ve orada kalır.
2. **Görsel faz** — görsel temas kurulunca komut **yalnızca kameradan** türer
   (YOLO bbox → IBVS). Bu fazda GPS/GNSS güdüme **girmez**.

Başka faz veya yardımcı güdüm katmanı yoktur. Görev `web/` altındaki **yer
kontrol arayüzünden** koşturulur; arayüz güdüm üretmez, yalnızca döngüyü
koşturur, gösterir ve başlatır/durdurur. İki modu vardır: **GPS** (yalnız 1.
faz) ve **HİBRİT** (GPS + kamera, yani her iki faz).

---

## Katmanlar

```
YASA (m/s hız setpoint'i)  ──►  ÇEVİRİCİ (ölçülmüş zarf)  ──►  KOMUT KAPISI  ──►  SDK
gps_approach.py                 common.VelocityToStick        common.CommandSender
visual_tracking.py

hangi yasa koşacak?  ──►  control/main.py :: PhaseSupervisor   (yalnız faz kapısı)
döngüyü kim koşturur? ─►  web/server.py                        (komut üretmez)
```

Ölçülmüş araç zarfı (`VZ_MAX_CLIMB`, `VZ_MAX_DESCENT`, `YAW_RATE_MAX`) **tek
yerde**, `common.ConverterCfg`'de durur; GPS ve görsel yasalar oradan okur.

DoW SDK'sı yalnızca kumanda çubuğu (−1..+1) kabul eder; arada ArduPilot'un
`AC_PosControl`'ü gibi bir hız kontrolcüsü **yoktur**. `VelocityToStick` o
eksik katmandır ve sabitleri oyunda ölçülmüştür (dikey eşleme iki kollu ve
tam sıfırda süreksiz, alçalma 4.8 kat asimetrik, nötr throttle −0.586).
Yasaya dokunmadan çevirici değiştirilebilir; tersi de doğru.

## Klasör yapısı

```
control/            güdüm ve karar
  main.py             PhaseSupervisor — YALNIZ faz devir kapısı (komut üretmez)
  gps_approach.py     GPSTracker — kalkış + bozuk GNSS ile istasyon tutma
  visual_tracking.py  VisualTracker — ölçülmüş kamera modeli + IBVS yasası
  common.py           birim sınırı (Telemetry) + hız→çubuk çevirici + komut kapısı
filter/             bozuk GNSS'i temizleyen kestiriciler
  gnss_filtre_v2.py   GNSSFilterV2 — CT-EKF + Mahalanobis kapıları + ölü-hesap ⭐ AKTİF
  gnss_filtre.py      GNSSFilter — önceki sürüm (spike kapıları); artık çağrılmıyor
perception/         hedef tespit + takip
  camera.py           ekran yakalama → tespit → takip → detection_state
  detector.py         YOLO tespiti (models/talon_v3.pt) + pervane maskesi
  tracking.py         HybridSort (boxmot) kimlik sürekliliği
  detection_state.py  kamera thread'i ↔ güdüm döngüsü köprüsü
  models/talon_v3.pt  eğitilmiş model — imgsz 960 (task=detect, sınıf: talon)
  models/talon_v3.engine  aynı ağırlığın TensorRT motoru ⭐ VARSA AKTİF (repoya konmaz)
  models/best.pt      önceki model — imgsz 640; geri almak için AVCI_MODEL=best.pt
sdk/                simülasyon I/O (resmi yarışma SDK'sı — DEĞİŞTİRİLMEZ)
web/                yer kontrol arayüzü + görevin KOŞTURUCUSU (güdüm üretmez)
  server.py           yerel HTTP sunucusu + 50 Hz kontrol döngüsü (port 8001)
  server.html         tek sayfa arayüz: kuşbakışı harita + telemetri + olay günlüğü
scripts/start_game.sh   oyunu başlatır — Linux (Wine ile)
scripts/start_game.ps1  oyunu başlatır — Windows (native, Wine yok)
scripts/export_engine.py  .pt → TensorRT .engine çevirir, çevirimi ÖLÇER ve doğrular
```

Veri akışı tek yönlüdür:

```
oyun ekranı ──► perception/camera ──► detection_state ──┐
                                                        ├─► control/main ─┐  (KAPI: hangi faz?)
oyun telemetrisi (bozuk GNSS) ──► filter/gnss_filtre_v2 ┘                 │
                                                                          ▼
                          web/server ──► gps_approach | visual_tracking ──► common ──► sdk ──► oyun
                          (döngü)          (YASA)                    (çevirici + komut kapısı)
```

---

## Kurulum

Python kodu platformdan bağımsızdır; fark yalnızca **kabuk komutları** ve
**oyunun başlatılma biçimidir** (Linux'ta Wine, Windows'ta native).

> **Python sürümü: 3.10 – 3.13.** `boxmot` (HybridSort takipçisi) **3.14'ü
> desteklemez**. 3.14'te sistem çalışır ama takipçi sessizce devre dışı kalır
> (`tracking.py: hazir=False` → ham argmax kutusu), yani kareler-arası kimlik
> sürekliliği ve tek-kare parazit filtresi kaybolur.

**Linux:**

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt        # torch'u CUDA'lı kurmak için pytorch.org
```

**Windows (PowerShell):**

```powershell
# Python 3.13 yoksa:  winget install Python.Python.3.13 --source winget
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
# torch'u ÖNCE CUDA index'inden kur — PyPI'daki Windows wheel'i CPU-only'dir.
# RTX 50xx (Blackwell, sm_120) için en az cu128 gerekir.
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
pip install -r requirements.txt
```

Yarışma paketindeki oyunu depo köküne **`Drones of War Teknofest/`** klasörü
olacak şekilde çıkartın (bu klasör repoya konmaz, `.gitignore`'dadır).

### TensorRT motoru (opsiyonel, ölçülmüş hızlanma)

`talon_v3.pt` aynı ağırlığın TensorRT motoruna çevrilebilir. **Dedektör motoru
varsa kendiliğinden onu yükler**, yoksa `.pt` ile aynen çalışır — yani bu adım
atlanabilir, hiçbir şey bozulmaz.

```powershell
python -c "import torch; print(torch.version.cuda)"   # 13.x ise cu13, 12.x ise cu12
pip install onnx onnxslim "tensorrt-cu13==11.1.0.106"
python -m scripts.export_engine --fp32                # çevirir + ÖLÇER + doğrular
```

**Bu depoda motor FP32 derlenir** (`--fp32`). FP32 motor `.pt` ile **birebir
aynı** sayıyı üretir (skor farkı max 0.00000) ama FP16'dan yavaştır. Ölçüldü
(oyun kapalı, prizde değil + "Silent" profil, her kol ayrı süreçte, n=200):

| kol | kare başı | FPS | `.pt`'ye göre |
|---|---:|---:|---:|
| `.pt` | 19.50 ms | 51.3 | 1.00× |
| **`.engine` FP32** | **13.85 ms** | **72.2** | **1.41×** |
| `.engine` FP16 (`--fp32` vermeyin) | 10.36 ms | 96.5 | 1.88× |

> ⚠ **Kazanç oranı GPU'nun güç durumuna bağlıdır**, tek bir çarpan yoktur.
> Aynı gün daha yüksek güç durumunda ölçülen kolda FP16 kazancı 1.88× değil
> **1.22×** çıktı: GPU tam saatteyken `.pt` hızlanıyor ve motorun üstünlüğü
> eriyor. Motorla kalan sürenin çoğu artık CPU tarafındaki ultralytics
> giderindedir (letterbox, NMS) ve o GPU saatiyle ölçeklenmez.

> **TensorRT sürümü:** Windows Smart App Control açıksa **en yeni** sürümün
> Python bağlayıcısı imzasız+itibarsız olduğu için engellenir
> (`ImportError: DLL load failed ... Uygulama Denetimi ilkesi bu dosyayı
> engelledi`). Çözüm SAC'ı kapatmak değil — geri dönüşü yoktur — bir önceki
> sürümü kurmaktır. Bu makinede 10.13.3.9 … 11.1.0.106 geçiyor, 11.2.1.2
> engelleniyor.

Betik çevirimden sonra `.pt` ile `.engine`'i **aynı girdi tensörüyle** besleyip
NMS öncesi ham çıktıları karşılaştırır (doğrulama karenin içeriğinden bağımsız
olsun diye) ve ikisinin kare başı süresini basar.

> ⛔ **Motor taşınmaz.** `.engine` şu karta, şu sürücüye ve şu TensorRT sürümüne
> derlenir; başka makinede açılmaz. Bu yüzden `.gitignore`'dadır ve donanım,
> sürücü, TensorRT ya da model değişince **yeniden üretilir**. Açılmazsa
> dedektör sessizce değil, **gerekçesiyle** `.pt`'ye döner (olay günlüğüne
> `TensorRT motoru ACILMADI (...)` düşer).

> ⚠ **`AVCI_IMGSZ` motoru ezemez.** Motorun girdi şekli derlenirken sabitlenir
> (960×960); başka ölçek TensorRT tarafında assert atar. Çakışırsa sistem
> otomatik olarak `.pt`'ye düşer, böylece uzak menzil taraması
> (`AVCI_IMGSZ=1920`) çalışmaya devam eder. Motoru başka ölçekte istiyorsanız
> o ölçekte **yeniden üretin**.

## Çalıştırma

**Linux:**

```bash
./scripts/start_game.sh                # 1) oyunu başlat, PLAY moduna geç
python3 -m web.server                  # 2) ayrı terminalde yer kontrolü aç
```

**Windows (PowerShell):**

```powershell
.\scripts\start_game.ps1               # 1) oyunu başlat, PLAY moduna geç
python -m web.server                   # 2) ayrı terminalde yer kontrolü aç
```

> Script imzasız diye reddedilirse:
> `powershell -ExecutionPolicy Bypass -File .\scripts\start_game.ps1`

Ardından tarayıcıda `http://127.0.0.1:8001` açılır ve görev **oradan**
başlatılır. Sunucuda `Ctrl+C` motorları keser ve kapatır.

> `python -m control.main` **çalışmaz**: o dosya artık yalnızca faz geçiş
> kapısıdır (`PhaseSupervisor`), giriş noktası değildir.

> **Görevi durdurup yeniden başlatmak için sunucuyu kapatmanız gerekmez.**
> Durdur/başlat, güdüm durumunun tamamını sıfırlar; GNSS filtresi ise
> bilinçli olarak **korunur** (soğuk filtre, araç havadayken yeniden
> başlatıldığında ısınma transientini doğrudan güdüme sokuyordu — ölçüldü:
> hedef konum hatası medyan 39.2 m → 2.5 m). Ayrıntı ve diğer üç düzeltme
> `CLAUDE.md :: GÖREVİ DURDURUP YENİDEN BAŞLATMA` bölümünde.
> Oyunu yeniden başlatıp hedef başka yerde doğduysa filtre bunu kendi teşhisiyle
> anlayıp soğuk kurulur; elle zorlamak için `brain.reset(cold_filter=True)`.

> **Oyun penceresi görünür/önde kalmalıdır.** Kamera hattı `mss` ile **ekranı**
> yakalar; oyun başka bir pencerenin arkasında kalırsa dedektöre masaüstü
> pikseli gider ve hedef "kaybolur". Kenarlıksız pencere modu en sağlıklısıdır.

### Yer kontrol arayüzü

Tarayıcıda `http://127.0.0.1:8001`: ortada **kuşbakışı harita** (avcı izi,
ham/bozuk hedef izi, temiz hedef izi ve **istasyon noktası**), sağda telemetri
+ istasyon tutma ölçütleri + **görsel takip paneli** + uygulanan güdüm
komutları, altta görev olay günlüğü. Ekran paylaşımı/kamera görüntüsü yoktur.

Sol paneldeki **iki başlatma düğmesi** modu seçer:

| düğme | ne koşar | kamera |
|---|---|---|
| **GPS Takibi Başlat** | yalnız GPS fazı: kalkış + istasyon tutma | hiç açılmaz — dedektör (torch) yüklenmez |
| **Hibrit Takip Başlat** | GPS fazı → devir kapısı → görsel faz | açık; görsel fazda komut **yalnız kameradan** |

Hibrit modda görsel takip paneli devir kapısının **koşullarını canlı**
gösterir (kaç ard arda kare kilit, kaç tik istasyona oturmuş), ayrıca kutudan
türeyen menzil, hücum hızı, kadraj hatası, köprü durumu ve kamera FPS'i.

> Arayüz **ayrı bir beyin değildir**: `control/` paketindeki aynı kodu çağırır
> ve komutu tek komut kapısından (`CommandSender`) gönderir. Güdüm yasası
> içermez.

> **Devir kapısının 3. koşulu: kadraj penceresi.** Hedef, görsel yasanın ilk
> komutunu doyuracağı bir noktadaysa (kadrajın kenarına yakın) devir açılmaz —
> kilit satırında **"kadraj dışı"** yazar. Eşikler mevcut güdüm sabitlerinden
> türer (`YAW_RATE_MAX/KP_YAW_RATE` ve `VZ_CAP_VISUAL/K_CY`), ayrı bir tune
> düğmesi yoktur. Kapı yalnız **devre** uygulanır: görsel faz sürerken hedef
> kenara kayarsa faz düşmez, yasa onu geri getirir.

> Dedektör **tembel** yüklenir: yalnızca hibrit görev başlatıldığında. Kamera
> hattından kare gelmezse arayüz 15 s sonra olay günlüğünde uyarır (torch /
> ultralytics kurulu değilse bu **sessiz** bir bozulmadır).

### Ortam değişkenleri

| Değişken | Etki |
|---|---|
| `AVCI_REGION="left,top,w,h"` | Tüm ekran yerine yalnız bu dikdörtgeni yakala |
| `AVCI_DEBUG_WINDOW=1` | Dedektörün **gördüğü** kareyi kutularla ayrı pencerede göster |
| `AVCI_FP16=0` | FP16 inference'i kapat |
| `AVCI_MODEL=best.pt` | Başka bir ağırlık kullan (`perception/models/` içinde). `IMGSZ` bilinen modellerde kendiliğinden ayarlanır |
| `AVCI_IMGSZ=1920` | Çıkarım çözünürlüğünü elle ez (uzak menzilde tespit zayıfsa) |
| `AVCI_ENGINE=0` | TensorRT motorunu yok say, `.pt` ile koş (motor varken karşılaştırma yapmak için) |

Linux'ta `AVCI_REGION="0,0,1280,720" python3 -m web.server`,
Windows'ta `$env:AVCI_REGION="0,0,1280,720"; python -m web.server`.

> **Kamera modeli oyun kadrajını varsayar.** Tüm ekranı yakalarsanız (görev
> çubuğu, pencere kenarlığı) kadraj merkezi ve odak uzaklığı kayar, kerteriz
> hesabı bozulur. `AVCI_REGION` ile tam oyun görüntüsünü verin.

> **Çoklu monitör (Windows):** `mss` varsayılan olarak **birincil** monitörü
> yakalar. Oyun ikinci ekrandaysa ya oyunu birincil ekrana alın ya da o ekranın
> dikdörtgenini `AVCI_REGION` ile verin.

---

## GPS fazı — istasyon tutma

Yasa tek satırdır:

```
v = v_des  +  Kp · (istasyon − konum)
```

İlk terim **ileri beslemedir**: hedefin kendi hızı doğrudan komuta eklenir.
Bu olmadan saf P kontrolcü hareketli hedefi asla yakalayamaz — denge
`e = V/Kp`'de kurulur (Kp=0.9, V=18 m/s → **20 m kalıcı hata**).

İstasyon noktası hedefin **8 m arkasında**, `8 × 0.75 = 6 m altındadır`.
Altta durmak, kamera 26.5° yukarı baktığı için hedefi kadraja sokar ve arka
planı gökyüzü yapar (dedektör için temiz zemin). Burun her zaman **hedefe**
dönüktür, istasyona değil.

Dikey tavanlar asimetriktir (+33.5 / −6.95 m/s); tek tavan kullanmak alçalma
komutunu ~5 kat abartır.

## Faz devir kapısı (GPS → görsel)

İki koşul **birlikte** sağlanmalıdır:

1. **Görsel kilit** — ard arda `HANDOFF_FRAMES` (10) **karede** güdüme girebilecek
   kutu.
2. **İstasyona oturma** — istasyon hatası ≤ 8 m ve hedefe menzil ≤ 15 m,
   ard arda 25 tik (~0.5 s). Hedef GNSS'i bayatsa bu koşul düşer.

Kutu kapısı tek yerde tanımlıdır (`control.visual_tracking.aim_box`) ve hem
gözetmen hem görsel faz **aynısını** kullanır. İki katmana ayrı eşik yazmak,
görsel fazın aynı karede reddettiği bir kutuyla devir yapılmasına ve fazın
sürekli sekmesine yol açar.

2. koşul hedefin GPS'ini okur; bu bir **faz geçişi** kapısıdır, güdüm yasası
değildir (görsel temas henüz yoktur). `control.main.Cfg.CAMERA_ONLY_GATE = True`
ile yapısal olarak kapatılıp kamera-tek kapıya düşülebilir.

Görsel fazda `LOST_S` (2 s) boyunca geçerli kutu gelmezse GPS fazına dönülür.

## Görsel güdüm yasası (IBVS)

Kontrol hatası doğrudan **görüntü uzayında** tanımlanır; hedefin 3B konumu
kestirilmez.

```
menzil R   = RANGE_C_REF / kutu_boyutu          benzer üçgenler (p = C/R)
kerteriz   = piksel + KENDİ IMU'muz          ego-motion telafili
yaw        = burnu kerterize çevir           K_YAW · azimut
ileri hız  = PI(temas_kutusu − kutu)         V_ATTACK = 28 m/s tavan
dikey hız  = −K_CY · (cy − cy_ref)           hedefi kadrajda sabit tut
```

- **Dikey kanal kadraj regülasyonudur**, saf takip değil. Hız vektörünü 3B'de
  hedefe nişanlamak aracı hedefin hizasına çıkarır ve kamera yukarı baktığı
  için hedef görünmez olur (ölçüldü: tespit %90 → %12–15).
- **Kutu köprüsü** (`BRIDGE_S = 1 s`): çıkarım ~10 Hz olduğu için aradaki
  karelerde son kutunun kerteriz yönü saklanır ve **kendi dönüşümüz** telafi
  edilerek kadraja geri yansıtılır. Girdi yalnızca son kutu + kendi IMU'muz.
- **Geçerlilik kapısı** menzil aralığıdır: `conf ≥ 0.40`, kutu ≥ 8 px,
  `3 m ≤ R ≤ 50 m`. 3 m'nin altındaki kutu dev yanlış-pozitiftir (dedektör
  140 m'de üretebiliyor); 50 m'nin ötesinde tespit %9 — orada GPS fazı sürer.

Ayar sabitleri `control/visual_tracking.py :: VisualCfg` içindedir. Ölçülmüş
değerlerin gerekçeleri ve elenen denemeler `CLAUDE.md`'de kayıtlıdır —
**geri eklemeden önce oraya bakın.**

## Bozuk GNSS zinciri

`sdk.drone_sdk.get_target_location()` bozuk (gürültü/offset/sıçrama/kesinti/
gecikme içerebilir) hedef konumunu verir. `filter/gnss_filtre_v2.py` bunu
**CT-EKF** ile temizler (durum: `x, y, vx, vy, ω` — yani hedefin dönüşünü
öngörür): Mahalanobis kapıları jammer sıçramasını istatistiksel olarak
reddeder, kapı üst üste reddederse `P` şişirilip yeni rejime yeniden
kilitlenilir, kesintide ölü-hesapla ileri gidilir ve çıkış `lead_s` kadar
ileri taşınarak ~1.13 s'lik GNSS gecikmesi kapatılır.

Sentetik jammer testinde (120 s × 5 tohum) önceki `GNSSFilter`'ye göre konum
hatası medyanı **21.9 → 3.2 m**, hız hatası medyanı **4.31 → 0.43 m/s**. Hız
kazancı doğrudan kritiktir: istasyon yasası hedefin hızını **ileri besler**.
Ölçümlerin ayrıntısı ve ısınma transienti uyarısı `CLAUDE.md`'dedir.

Önceki sürüm `filter/gnss_filtre.py`'de duruyor (çağrılmıyor): nedensel
temizleme, z-spike ve x/y-spike kapıları, son-N nokta lineer hız
kestirimi ve gecikme telafili lead. `control/gps_approach.py` bu temiz
kestirimden hedefin konumunu, **hızını** ve **gidiş yönünü** alır; istasyon
noktası bu yöne göre kuyruğa kurulur.

> `get_target_speed()` SDK'da **daima 0** döner — hedef hızı konumdan
> kestirilmek zorundadır.

## Kurala uyum (görsel fazda GPS yasağı)

Görsel temas kurulduktan sonra hareket komutunu GPS ile üretmek diskalifiye
sebebidir. Kural **yapısal** olarak sağlanır: `VisualTracker.compute(det,
own_att_deg, own_vel_ms, dt)` imzasında hedefe ait tek veri **bbox**tır —
konum, hız ya da GNSS kestirimi parametre olarak bile geçmez. `own_*`
değerleri kendi IMU/hızımızdır (ego-motion telafisi), hedef verisi değildir.

# TEKNOFEST 2026 Savaşan İHA Avcı Drone — Takip & Tespit Model Analizi

**Belge tarihi:** 2026-07-01 · **Son güncelleme:** 2026-07-02 — (1) komisyonun OSD cevabı işlendi (OSD kalıcı; "OSD yokken" senaryosu kaldırıldı); (2) **pose modeli GERİ ALINDI** — artık birincil detektör değil, kilitli hedefin **yönelimini (yaw/roll)** kestiren ikincil başlık; amaç yönelimden hedefin gelecekteki uçuş yönünü önden tahmin edip **öngörülü güdüm** (yeni Bölüm 5 — özgün katman)
**Aşama:** Simülasyon (SkyDagger) — kaynak kod + Simülasyon Uçuş Kanıt Videosu hazırlığı
**⚠️ Kritik hatırlatma:** Simülasyon Uçuş Kanıt Videosu + kaynak kod `.zip` son teslim **8 Temmuz 2026 17:00**. Bu belge o tarihe kadar yapılacak model/pipeline kararlarını özetler.

---

## 0. Bağlam ve model seçimini belirleyen kısıtlar

> **📌 Komisyon cevabı (OSD sorumuza, resmi):** *"Yarışma ortamında takımların kullanacağı dronelarda da bu yazılar, göstergeler ve HUD ekranı olacaktır. Dolayısıyla algoritmanızı hazırlarken gerçek ortamda da bu durumla karşılaşacağınızı bilerek hazırlamanız gerekmektedir. Simülasyon ekranından ekran yakalama ile aldığınız görüntü ham veri olup gecikme bulunmamaktadır."*
>
> **Çıkarımlar:** (1) OSD/HUD **kalıcı kısıt** — simde de gerçek yarışmada da ekranda olacak; "OSD'siz" senaryo yok, anti-OSD katmanı sistemin kalıcı parçası. (2) Ekran yakalama **meşru giriş yolu**; görüntü **ham veri + gecikmesiz** → capture-gecikme telafisi gerekmez, bozulmalar render'dan gelir (yakalama katmanından değil).

| Kısıt | Değer | Etki |
|---|---|---|
| İşlem yeri | Yer istasyonu (GPU'lu PC) | Ağır model mümkün; onboard kısıt yok |
| Dil / model formatı | Python, `.pt` (organizatör YOLOv8/v11 bekliyor: `best.pt`, `TalonDetect.py`, `input.py`) | Detektör = YOLO ailesi |
| Görüntü | ~60 FPS (~16 ms/kare); kalite düşük — FPV bozulmalı (çözünürlük teyitsiz) | Hafif detektör; kareler arası hareket küçük |
| Kamera (sim) | 25° yukarı tilt, gövdeye sabit (ilk "tilt 0" gözlemi saha kalibrasyonuyla YANLIŞ çıktı; sim v0.0.5 finalle aynı) | Ego-hareket **faz-bağımlı**: seyir/arama fazında düşük, **terminal dalış/angajmanda şiddetli** → CMC/GMC dalışta kazanç sağlayabilir (varsayma, ölç) |
| Kamera (final) | 25° **yukarı**, analog 1500 TVL, 125° FOV | Hedef gökyüzü zemininde (silüet), gerçek gürültü |
| Hedef | X-UAV Talon (1718 mm), sim'de **düşük manevra** | Öngörülebilir/doğrusal hareket → doğrusal Kalman ideal |
| FPV bozulmaları (sim, ekip gözlemi) | Pervane motion blur (kadraj kenarı/köşe), kromatik saçaklanma (kenarlarda R/C ayrışması, kenara doğru artan lateral CA), fıçı/barrel distorsiyon (kavisli ufuk, geniş FOV), güneş bloom + blown highlights, atmosferik pus/haze (uzak ufuk düşük kontrast), kenar hareket smearı, OSD/HUD bindirmesi (pixel-font telemetri: sinyal/süre/ALT/SPD/ARMED/TRIGGER/Mode), belirsiz: gökyüzü benekleri (gürültü/toz/artefakt), köşede hafif vinyet olası | Bozulmalar **appearance**'ı vuruyor (hareketi değil) → hareket-tabanlı ilişkilendirme + düşük-güven kurtarma; ReID'den kaçın |
| **OSD/HUD — komisyon teyitli** | Sim **ve** gerçek yarışma dronunda yazılar/göstergeler/HUD ekranda OLACAK; kaldırılamaz | Anti-OSD katmanı (Bölüm 4) kalıcı + zorunlu; OSD hard-negative eğitim pazarlıksız |
| **Ekran yakalama — komisyon teyitli** | Ham veri, **gecikmesiz**; meşru giriş yolu | Capture-gecikme telafisi gereksiz; kare zaman damgaları güvenilir |
| Kilit kuralı | Hedef merkezde kutu içinde, ekranın ≥%5'i, 10 sn'de kümülatif 5 sn (kesintili olabilir) | Kayıp doldurma + kestirim şart |

**Temel karar:** Bu bir "tek tracker" problemi değil; **Tespit (YOLO) → Anti-OSD filtre → İlişkilendirme (MOT) → Sıkı kilit/boşluk (SOT) → Kestirim (Kalman)** katmanlı hattı. OSD kalıcı olduğundan filtre katmanı hattın standart parçasıdır.

---

## 1. Detektör mimarisi — detect (kilit omurgası) + pose (yönelim başlığı) — POSE GERİ ALINDI

**Karar değişikliği (2026-07-02):** Pose modeli **geri alındı**, ama **rolü değişti.** Artık pose *birincil detektör değil*; kilit omurgası yine düz **detect** (**YOLOv11** / **YOLO26**). Pose, kilitli hedefin **yönelimini (attitude: yaw + roll)** kestiren **ikincil başlık** olarak yalnızca hedef ROI'sinde çalışır. Amaç: yönelimden hedefin **gelecekteki uçuş yönünü önden tahmin edip** öngörülü güdüm yapmak (bkz **Bölüm 5 — özgün katman**).

**Neden iki-başlıklı (detect + pose), pose tek başına değil:**
- Kilit kuralı hâlâ **bbox merkezi + boyut** ister → kilidi **detect + ByteTrack** taşır (kanıtlanmış, OSD'ye karşı sağlam hat). Pose kilit yoluna sokulmaz.
- Pose sadece **yönelim** üretir: nişan/güdüm için gerekli ama *kilit geçerliliği* için değil. Böylece pose kaçırsa/gürültülü olsa bile kilit düşmez → **graceful degradation** (pose yoksa sistem klasik takibe düşer, kilit sürer).

**Eski "pose bırakıldı" itirazları nasıl karşılandı:**
| Eski itiraz | Çözüm |
|---|---|
| Pose'un COCO-insan ön-eğitimi OSD metnine ateşliyordu | Pose artık **full-frame değil, sadece kilitli hedef ROI'sinde** çalışır → OSD köşeleri kadraj dışında kalır; ayrıca Talon-özel keypoint + OSD hard-negative ile eğitilir |
| Keypoint eğitimi veriyi zayıflatır, hata yüzeyini artırır | Detect başlığı ayrı ve **saf** kalır; pose bağımsız başlık/model → ana tespit hattı kirlenmez |
| Kilit keypoint istemiyor | Doğru — keypoint kilit için değil, **yönelim/öngörü** için; bu farklı bir iş (Bölüm 5) |

**İki uygulama seçeneği (ölç, seç):**
| Seçenek | Nasıl | Artı / Eksi |
|---|---|---|
| **A) Tek YOLOv11-pose** (detect+keypoint tek geçiş) | Full-frame pose, Talon keypoint'li | + Tek model/tek geçiş. − OSD hard-negative pazarlıksız; full-frame keypoint gürültüsü daha yüksek |
| **B) İki aşama: detect → ROI-pose** ⭐ **(ÖNERİLEN)** | YOLOv11-detect full-frame kilidi; ayrı hafif pose/keypoint yalnız kilitli kutu kırpıntısında | + OSD'den tam izole (ROI merkezde), ucuz, kilit hattı saf kalır. − İki model bakımı |

**Talon keypoint şeması (yönelim için yeterli minimum):** burun ucu · sol kanat ucu · sağ kanat ucu · kuyruk ucu · (ops.) dikey stabilizatör tepesi → ~4–5 nokta. **Bilinen açıklık 1718 mm**, PnP ölçeği için hazır referans (Bölüm 5.1).

**Sürüm seçimi (detect başlığı):**
| Sürüm | Artı | Dikkat |
|---|---|---|
| **YOLOv11** | Olgun, Ultralytics ekosistemi, **P2 varyantı + augmentasyon hazır**, `-pose` varyantı mevcut | Güvenli varsayılan |
| **YOLO26** | Daha yeni, **NMS-free/end-to-end** → düşük latency | `.pt` export'un sim arayüzüyle uyumunu + P2/küçük-nesne + **pose varyant desteğini** **teyit et**; yarışma "YOLOv8/v11 vb." diyor → v11/26 kabul kapsamında ama emin ol |

**Küçük hedef için kritik ayarlar (Talon arama/yaklaşma fazında küçük görünür → recall burada belirleyici):**
- **P2 tespit başlığı (stride 4):** yüksek çözünürlüklü feature map → **küçük-nesne recall'ı artar** (`yolo11-p2` benzeri konfig). Bedeli: daha yavaş + daha çok bellek → **60 FPS bütçesinde ölç.**
- **Yüksek `imgsz`** (örn. 960/1280): çoğu zaman P2'den daha pratik küçük-nesne kazancı; FPS ile dengele.
- İkisini **ayrı ayrı ve birlikte** test et → en iyi recall/FPS dengesini seç.
- **Tek sınıf "Talon"** + **OSD hard-negative** + **augmentasyon** (motion-blur, haze, bloom, renk kayması, ölçek/mozaik).
- **Not (pose güveni menzile bağlı):** yönelim ancak hedef yeterince büyük göründüğünde güvenilir → uzak fazda detect+CV yeter, pose/CT terminal fazda devreye girer (Bölüm 5.5).

---

## 2. Model karşılaştırması — OSD/HUD KALICI (tek geçerli senaryo)

> **Komisyon cevabı gereği "OSD yokken / OSD varken" ayrımı kaldırıldı:** OSD/HUD hem simülasyonda hem gerçek yarışma dronunda ekranda duracak. Mevcut sorun aynen geçerli: YOLO OSD metnini "Talon" sanıp drone OSD konumuna yönelebiliyor. Tüm model seçimi OSD'yi **kalıcı distraktör** kabul eder; FPV bozulmaları (blur/haze/bloom/CA) da her zaman var. **Anti-OSD katmanı (Bölüm 4) opsiyon değil, zorunlu kalıcı bileşendir.**

### Tespit-tabanlı MOT (takip omurgası)
| Model | Aile | Uygunluk | Gerekçe + OSD/distraktör önlemi |
|---|---|---|---|
| **ByteTrack** | MOT | ⭐⭐⭐⭐⭐ | Düşük güven kutusunu kurtarır → pus/glare için ideal; içinde Kalman var. OSD: Kalman hızı üzerinden **statik(~0 hız) iz reddi** ile elenir. **Birincil.** |
| **OC-SORT** | MOT | ⭐⭐⭐⭐ | Glare/haze sonrası yeniden yakalamada + kayıp toparlamada güçlü. Avcı manevrası hedefin kare-üstü hareketini doğrusal-olmayan yapar → gözlem-merkezli mantık burada işe yarar. OSD: statik iz reddi ile birleştir. |
| **SORT** | MOT | ⭐⭐⭐ | Basit/hızlı baz; düşük-güven kurtarması yok. OSD: statik-iz reddi şart. |
| **BoT-SORT** (CMC, ReID **kapalı**) | MOT | ⭐⭐⭐ (↕ faz-bağımlı) | CMC **ego-hareketi** telafi eder → terminal dalışta kazanç adayı; seyirde düşük. Risk: CMC hareket-kestirimi blur/haze/texturesiz gökte bozulup **backfire** edebilir → ölç (kıyas: Bölüm 3.1). ReID bozulmada zararlı, KAPAT. OSD: yine statik-iz reddi gerekir. |
| **DeepSORT** | MOT | ⭐⭐ | ReID glare/blur/CA'da ve OSD baskısında çöker; önerilmez. |
| **StrongSORT** | MOT | ⭐ | Ağır; 60 FPS'i zorlar; önerilmez. |

### Tek-nesne takipçileri (sıkı kilit / kısa boşluk — biri seçilir)
| Model | Aile | Uygunluk | Gerekçe + OSD notu |
|---|---|---|---|
| **NanoTrack** | Deep-SOT | ⭐⭐⭐⭐ | Blur/CA'ya CF'den dayanıklı; CPU real-time (OpenCV `TrackerNano`). OSD bölgesi dışında başlatıldığında sağlam. |
| **CSRT** | CF-SOT | ⭐⭐⭐⭐ | Yaklaşmada ölçek uyarlama en iyisi (OpenCV hazır). Şablon OSD'ye oturmasın diye init'i doğrula. |
| **DaSiamRPN** | Deep-SOT | ⭐⭐⭐ | **Distraktör-farkında** → OSD/benek baskısında görece avantajlı (tek-nesne SOT). |
| **MedianFlow** | CF-SOT | ⭐⭐⭐ | "Kayboldu" sinyali tetikleyicisi olarak. |
| **KCF** | CF-SOT | ⭐⭐ | Pervane blur'unda sürüklenir. |
| **MOSSE** | CF-SOT | ⭐ | Grayscale, kırılgan. |
| **OSTrack / STARK / MixFormer** | Deep-SOT | ⭐⭐ | 60 FPS'te her karede zor; aşırı güç. |

**Önerilen hat:** `YOLO(detect, OSD hard-negative eğitimli) → anti-OSD filtre (Bölüm 4) → ByteTrack → (ops.) NanoTrack/CSRT → Kalman coasting → güdüm`

**Kritik:** Model seçimi tek başına yetmez — asıl çözüm detektörde (**hard-negative eğitim**, Bölüm 4-A); filtreler (4-B/C/D) kalıcı emniyet katmanıdır.

---

## 3. Tracking modellerinin füzyonu (katmanlı kaskad — rakip değil)

**Yaygın yanılgı:** Birden çok tracker'ı aynı anda çalıştırıp oylamak. **Doğrusu:** her katmanın farklı rolü olan **öncelikli bir kaskad (gating)**. "NanoTrack **veya** CSRT" = ikisinden **birini** seç.

### Katmanların rolü
| Katman | Görevi | Ne zaman |
|---|---|---|
| **YOLO (detektör)** | "Karede Talon nerede?" sıfırdan bulur | Her karede (veya her K karede) |
| **ByteTrack (ilişkilendirme)** | Kutuları sürekli **iz + ID**'ye bağlar (içinde Kalman) | Her karede |
| **SOT (NanoTrack *veya* CSRT — biri)** | Detektör kaçırınca görüntüden yeri bulur | Sadece detektör boşluk bırakınca |
| **Kalman / coasting** | Tam kayıpta konumu tahminle uzatır + GNSS birleştirir | Güneş/glare tam kaybında |

### Füzyon = durum makinesi (ortalama değil, öncelik)
```
Her kare:
  1. YOLO → aday kutular
  2. Adayları FİLTRELE (OSD reddi / statik / şekil)   ← Bölüm 4
  3. ByteTrack ile hedef izine ilişkilendir
  4. DURUM:
     ├─ Detektör iyi kutu verdi        → TRACKING      : izi+SOT şablonu+Kalman güncelle
     ├─ Detektör kaçırdı, hedef görünür → GÖRSEL-COAST  : SOT kutuyu tahmin etsin, Kalman güncelle
     └─ İkisi de yok (güneş/glare)      → KÖR-COAST     : sadece Kalman; "kilit GEÇERSİZ" işaretle
                                                           (sunucuya sahte kilit paketi GÖNDERME)
  5. Detektör Kalman tahmini yakınında tekrar ateşler → yeniden ilişkilendir → TRACKING
```

### Kademeli kurulum (basit başla, ölçüp ekle)
- **Tier 0 (buradan başla):** `YOLO + ByteTrack + OSD filtresi`. ByteTrack'in iç Kalman'ı kısa boşlukları köprüler. **Çoğu ihtiyacı karşılar.**
- **Tier 1 (detektör boşlukları görülürse):** Tek bir SOT ekle (blur için **NanoTrack**). Sadece "detektör kaçırdı, hedef görünür" durumunda devrede.
- **Tier 2 (uzun glare kayıpları):** Kalman coasting süresini uzat + GNSS bearing'i yeniden-yakalama için birleştir.

### 3.1 Yükseltme kıyası — ByteTrack → BoT-SORT / OC-SORT (ölçümlü karar)
ByteTrack **temel (baseline)**; BoT-SORT (CMC) ve OC-SORT doğrudan yükseltme adayları. Ama "BoT-SORT vs OC-SORT" diye kıyaslama **iki farklı etkiyi karıştırır**. Onun yerine **iki bağımsız anahtarı ayrıştır (2×2 tasarım):**

| | Kalman-ByteTrack ilişkilendirme | OC-SORT (gözlem-merkezli) |
|---|---|---|
| **CMC kapalı** | baseline | OC-SORT'un OCM/ORU etkisi izole |
| **CMC açık** | "ByteTrack + CMC" (≈ **ReID'siz** BoT-SORT) | CMC + gözlem-merkezli |

- **Ölçüm ekseni:** parazit/gürültü slider'ı × terminal dalış anları.
- **Metrikler:** ID-switch sayısı, kilit sürekliliği (10 sn'de kümülatif kilit), dalışta iz-kopma oranı, kare-başı süre (60 FPS bütçesi).
- **Kritik uyarılar:**
  - **CMC'yi varsayma, doğrula:** hareket-kestirimi blur/haze/texturesiz gökte bozulup ilişkilendirmeye gürültü enjekte edebilir (backfire). CMC'nin faydayı mı varyansı mı artırdığına bak.
  - **BoT-SORT'ta ReID KAPALI** — bu görüntüde (blur+CA+haze) appearance zararlı; test edilen şey saf "ByteTrack + CMC".
  - **CMC'nin değeri hedefin manevrasından değil, avcının EGO-hareketinden gelir** → Talon uslu uçsa bile terminal dalışta kazanç mümkün.
- **Sıralama:** Bu kıyas bir **Tier-1/2 işidir.** Önce baseline (YOLO+ByteTrack+OSD fix+Kalman) otonom kilit yapmalı; CMC/OC-SORT kıyası ondan sonra. Teslime (8 Tem) baseline yetişmeden bu rabbit hole'a girme.

---

## 4. Anti-OSD katmanı (KOMBİNE kullan — kalıcı sistem bileşeni)

> **"OSD maskesi" = tespit-reddi (o bölgedeki kutuyu yok say), görüntüden piksel silmek DEĞİL.** Ekranı kapatmaya gerek yok; sahne/merkez açık kalır.
>
> **Kalıcılık (komisyon teyitli):** OSD hem simde hem gerçek yarışma dronunda olacak → bu katman geçici workaround değil, kalıcı bileşen. Gerçek dronun OSD yerleşimi/fontu simdekinden farklı olabilir → görünümden bağımsız **C (statik-iz reddi)** her ortamda aynen çalışır; **B (bölge reddi)** ortam başına yeniden ayarlanır (tek konfig); **A (hard-negative)** eğitim setine mümkünse farklı OSD yerleşim/font varyasyonları da eklenmeli.

**A) Kök çözüm — hard-negative eğitim (en etkilisi):**
Eğitim setine OSD'li kareleri koy, **sadece gerçek Talon'u etiketle**; OSD metin kırpıntılarını negatif/arka plan olarak ekle. Model OSD'ye ateşlemeyi bırakır. OSD ekranda dursa bile hedef sanmaz. Drone OSD'ye *güvenle* yöneliyorsa **tek gerçek çözüm budur.**

**B) Köşe/kenar reddi (anında, ucuz, sahneyi kapatmaz):**
OSD sabit ve bilinen piksel bölgelerinde (köşeler/kenarlar: sinyal, süre, ALT/SPD, ARMED/TRIGGER). Sadece o küçük şeritlere merkezi düşen tespitleri at. Merkez ve sahne açık kalır (kilit zaten merkezde olacağı için zarar vermez).

**C) Statik / hareket-tutarlılığı filtresi (OSD'ye özel, zarif):**
OSD ekran koordinatına **çivili** → her karede aynı pikselde, ~sıfır ekran hızıyla. Gerçek Talon kare boyunca hareket eder. ByteTrack/Kalman zaten hız veriyor → **kalıcı ~0 hızlı ve sabit konumlu izi OSD say, düşür.** Alternatif: karelerin temporal median'ı statik OSD'yi verir, çıkarırsın.

**D) Şekil/renk önselleri (ucuz son-filtre):**
OSD = ince, yüksek-frekanslı, belirli renk (beyaz/yeşil), bloklu glyph. Talon = kompakt uçak silüeti. En/boy oranı, alan, kenar-yoğunluğu, renk ile eleme.

**Pratik reçete:** **A + B + C** birlikte (D artçı emniyet). B ve C "drone OSD'ye yöneliyor" hatasını *hemen* keser; A problemi kaynağında bitirir.

---

## 5. Yönelim-tabanlı öngörülü güdüm — projenin ÖZGÜN katmanı

> **Fikrin özü:** Klasik takip algoritmaları hedefin **görüntü-hareketinden** hız vektörünü çıkarır (nereye *gitmiş*). Ama uçak burnunu/kanadını çevirdiğinde uçuş yolu **anında** değişmez — atalet yüzünden bir süre eski yönde **sürüklenir**, sonra burnun yönüne oturur. Yani **attitude (yönelim) önden gelen (leading) gösterge, hız vektörü geriden gelen (lagging) göstergedir.** Klasik tracker sadece geç göstergeyi gördüğü için manevranın **hep gerisinde** kalır ve mevcut yönde ilerleyeceğini varsayar. Biz pose'tan **yaw + roll** okuyup dönüşü **başlamadan** kestirir, hedefi **önden alırız (lead).** Rakiplerin görüntü-hızıyla yaptığı işi biz **uçuş dinamiğiyle** yapıyoruz — ayrıştırıcı fark budur.

### 5.1 Hangi açı neyi söyler
| Açı | Fiziksel anlam | Görüntüden kestirim (2D ipucu) | Güvenilirlik |
|---|---|---|---|
| **Roll (yatış/bank)** | Sabit-kanat uçak **yatarak döner** → bank açısı dönüş hızının doğrudan sürücüsü | Kanat-ucu↔kanat-ucu ekseninin ufka göre eğimi (ego-roll'dan arındırılmış) | **En güçlü/doğrudan** — 2D'de neredeyse ölçülebilir |
| **Yaw (baş açısı / aspect)** | Burnun baktığı yön = niyet edilen gidiş yönü | Burun→kuyruk vektörü + gövde/açıklık ön-kısalması (foreshortening); PnP | Orta — tek karede gürültülü, zamansal filtre şart |
| Pitch (ikincil) | Tırmanma/dalış | Aynı PnP çıktısı | Dikey öngörü için opsiyonel |

### 5.2 Kritik denklem — koordineli dönüş
Koordineli (yan-kaymasız) dönüşte **bank açısı φ, dönüş hızını verir:**
```
ψ̇ (baş açısı değişim hızı) = g · tan(φ) / V
```
- φ = ölçülen roll (bank), V = hedef sürati (izden kestirilir), g = 9.81 m/s².
- **Sonuç:** roll'u ölçtüğün an hedef yörüngesinin **eğriliğini** bilirsin — hız vektörü daha dönmeden. Bu, düz-çizgi ekstrapolasyonunu **eğri yörünge** kestirimine çevirir.

### 5.3 Sürüklenme = yan-kayma açısı
Burun yönü (yaw) ile yer-hız vektörü (izden) arasındaki fark = **yan-kayma (sideslip) β** → kullanıcının tarif ettiği *"burnu döner ama bir süre sürüklenir, sonra burnuna oturur"* olayı tam olarak budur.
- β büyük → hedef manevranın içinde, hız vektörü henüz yaw'a oturmamış.
- β küçülüyor → hedef manevradan çıkıyor, **hız vektörünün nereye oturacağını** (yaw yönüne) önden koyabilirsin.

### 5.4 Hareket modeli — CV yerine dinamik-farkında CT
- **Baseline (rakip yaklaşımı):** Sabit-hız (CV) Kalman → dönüşü göremez, manevranın gerisinde kalır.
- **Bizim:** **Koordineli-dönüş (CT / CTRV) modeli**, dönüş hızı ψ̇ **ölçülen bank açısıyla beslenir** (5.2 denklemi). Roll → ψ̇ → eğri öngörü. Pose gürültülü/yoksa CT, CV'ye **zarifçe düşer.**
- **Güdüm:** düz "şu anki yön" değil, **öngörülen eğri yörüngedeki gelecek konum** → lead pursuit / oransal seyrüsefer (PN) beslemesi.

### 5.5 Dürüst kısıtlar (rabbit hole'a düşmeden)
- **Menzil/piksel bağımlı:** uzak/küçük hedefte keypoint gürültülü → pose güveni düşer. Kural: hedef pikseli eşiğin altındaysa **CV'ye düş**; hedef büyüdükçe (terminal faz — zaten en kritik an) CT'yi aç. Piksel-boyutuna göre kademeli geçiş.
- **Ego-attitude arındırma:** görüntü ufku bizim kendi roll'umuzla eğilir → **kendi IMU/attitude verimizle ufku düzle**, sonra hedef roll'unu ölç. Yoksa kendi yatışımızı hedefin yatışı sanırız.
- **PnP belirsizliği:** küçük ölçekte yaw belirsizleşebilir; **roll (kanat-çizgisi) yaw'dan daha sağlam** → önce roll'a güven, yaw'ı zamansal filtre + iz-hızıyla füzyonla.
- **Tek kare değil, zaman serisi:** pose açı çıktısını küçük bir filtreden geçir (açı gürültüsü yüksek); ani sıçramaları reddet.
- **Sıralama:** bu bir **Tier-2 özgünlük katmanı.** Önce baseline kilit (YOLO+ByteTrack+OSD fix+Kalman) 5s/10s tutmalı; CT/pose-öngörü ondan sonra. **8 Tem teslimini bu katman için riske atma.**

### 5.6 Otonomi & ayrıştırıcılık
Yarışmada drone **tam otonom** → tüm zincir (keypoint → açı → CT öngörü → lead nokta → güdüm komutu) uçuş içinde, insansız koşmalı; hiçbir adım manuel değil. Bu katman iki işi birden yapar: (1) **otonom nişanı** manevra eden hedefte bile isabetli tutar (klasik takibin "gerisinde kalma" hatasını kapatır), (2) **rakiplerden ayrışma** — çoğu takım görüntü-hız tabanlı klasik takip yapar; **uçuş-dinamiği-farkında öngörü** görece nadir ve teknik olarak savunulabilir bir iddiadır (video ilk 3 dk algoritma anlatımında öne çıkarılacak koz).

---

## 6. Önerilen uçtan uca hat (OSD kalıcı — sim + gerçek ortam)

```
[SkyDagger 60fps, ekran yakalama = ham veri & gecikmesiz (komisyon teyitli), FPV-bozulmalı, OSD ekranda — KALICI]
  → ÖN-İŞLEME:  barrel undistort (kalibrasyon)  +  CLAHE (pus/kontrast)  +  ego-attitude ile ufuk düzleme (kendi IMU)
        ▼
1) TESPİT:   YOLOv11 / YOLO26 detect (m) — Talon tek sınıf; küçük hedef için P2 başlığı ve/veya yüksek imgsz
             Eğitim: OSD hard-negative + aug(motion-blur, haze, bloom, renk kayması, ölçek)  → best.pt
        ▼
2) FİLTRE:   OSD köşe-reddi + statik(~0 hız) iz reddi + şekil/renk önseli   ← Bölüm 4 (A+B+C+D)
        ▼
3) İLİŞKİLENDİRME:  ByteTrack (düşük güven eşiği düşük tut)  → kilitli hedef izi + hız vektörü
        ▼
3b) YÖNELİM (pose):  kilitli hedef ROI → keypoint (burun/kanat uçları/kuyruk) → PnP/2D
                     → yaw + roll (ego-roll'dan arındırılmış), zamansal filtre         ← Bölüm 5
                     [yalnız hedef yeterince büyükse; küçükse atla → CV]
        ▼
4) SIKI KİLİT + KISA BOŞLUK:  NanoTrack (blur) VEYA CSRT (ölçek) — re-detection ile gated  [Tier 1]
        ▼
5) KESTİRİM/COASTING:  dinamik-farkında Kalman — bank-beslemeli KOORDİNELİ-DÖNÜŞ (CT/CTRV);
                       pose yoksa sabit-hız (CV)'ye düşer; glare/haze kayıplarında sürdür → 5s/10s kilidi kurtarır
        ▼
6) GÜDÜM:  öngörülen EĞRİ yörüngedeki gelecek konum → lead nokta → ekran merkez sapması
           → yönelim komutu (yaw/roll-farkında öngörü — ÖZGÜN, Bölüm 5)
```

---

## 7. Sıradaki adımlar
1. **Detektör (kilit omurgası):** **YOLOv11/YOLO26 detect** + küçük-nesne ayarı (P2 başlığı ve/veya yüksek imgsz'yi 60 FPS altında kıyasla) + veri düzeltmesi (**OSD hard-negative — komisyon cevabı gereği pazarlıksız** + augmentasyon). *(Baseline önce çalışsın; pose bunun üstüne gelir.)*
2. **OSD filtresini** YOLO çıktı aşamasına ekle (Bölüm 4 B+C), hemen test et.
3. **Tier 0** (YOLO+ByteTrack+filtre) ile kilit performansını (5s/10s) ölç; gerekiyorsa Tier 1 SOT ekle. **Öngörü katmanına geçmeden önce baseline kilit sağlam olmalı.**
4. **Pose/yönelim başlığı (Tier 2 — ÖZGÜN):** Talon keypoint verisi hazırla (burun/kanat uçları/kuyruk); Seçenek B (detect→ROI-pose) ile başla. Kilitli ROI'de yaw/roll kestir, **ego-roll arındır**, zamansal filtrele. Menzil eşiğiyle gate'le (küçük hedefte CV'ye düş).
5. **CT hareket modeli:** CV Kalman'ı **bank-beslemeli koordineli-dönüş (CT/CTRV)** ile değiştir (ψ̇ = g·tanφ/V); güdümü **lead nokta** (öngörülen eğri yörünge) üzerinden ver. Manevralı hedefte CV vs CT kilit sürekliliğini **ölç** (ayrıştırıcı kanıt bu).
6. Tracker'ı interface arkasına al → final (analog, 25° yukarı, **OSD orada da ekranda**) için `ByteTrack→OC-SORT` geçişi tek konfig olsun; OSD bölge-reddi (4-B) koordinatları da aynı konfigden gelsin.
7. **8 Temmuz** teslimine kadar: çalışan pipeline + video (ilk 3 dk algoritma anlatımı — **yönelim-tabanlı öngörülü güdümü koz olarak öne çıkar**, son 3 dk otonom görev kanıtı) + `.zip` (input.py, tespit, pose/yönelim, tracking, füzyon, güdüm, README).

---
*Bu belge yaşayan bir dokümandır; kod incelemesi ve sim testleri sonrası güncellenecektir.*
*Güncelleme 2026-07-02 (a): Komisyonun resmi OSD cevabı işlendi — "OSD yokken" senaryosu (eski Karşılaştırma A) kaldırıldı, model karşılaştırmaları tek OSD-kalıcı tabloda birleştirildi; bölümler yeniden numaralandı (füzyon→3, 4.1→3.1, anti-OSD→4, uçtan uca hat→5, adımlar→6).*
*Güncelleme 2026-07-02 (b): **Pose modeli geri alındı** — birincil detektör olarak değil, kilitli hedef ROI'sinde çalışan **yönelim (yaw/roll) başlığı** olarak. Bölüm 1 iki-başlıklı (detect + pose) mimariye yeniden yazıldı; eski "pose bırakıldı" itirazları karşılandı. **Yeni Bölüm 5 (Yönelim-tabanlı öngörülü güdüm — özgün katman)** eklendi: attitude=leading / hız=lagging fikri, koordineli-dönüş denklemi (ψ̇=g·tanφ/V), sürüklenme=sideslip, CV→bank-beslemeli CT hareket modeli. Pipeline (→6) ve adımlar (→7) yönelim dalı + CT ile güncellendi.*

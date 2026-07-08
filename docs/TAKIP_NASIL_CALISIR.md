# TAKİP (TRACKING) — Nasıl Çalışıyor? Model Bunun Neresinde?

> Bu doküman şu soruya cevaptır: **"Modeli eğitiyoruz; modelin tracking yapması için
> hangi teknikleri kullanacağız, yapay zekaya ne prompt'u vereceğiz?"**
>
> Kısa cevap: **Tracking için prompt'a da yeni koda da gerek yok — o katman bu projede
> yazılı, çalışıyor ve birim testli.** Eğitilen model tracking YAPMAZ; model her karede
> sadece kutu bulur. Tracking, o kutuları kareler arasında birbirine bağlayan **klasik
> bir algoritmadır** (ByteTrack + Kalman + jiroskop telafisi) ve `detection/takip.py`
> içinde kendi kodumuz olarak durur.
>
> İlgili kod: `detection/gorsel_tespit.py` (model çıktısı), `detection/takip.py`
> (takipçi), `detection/algi_hatti.py` (döngü), `detection/kamera_model.py` (CMC
> matematiği). Testler: `test/test_takip.py`, `test/test_algi_hatti.py`.

---

## 0) Arkadaşına verilecek kısa cevap (kopyala-yapıştır)

> Hocam tracking için yapay zekaya ayrıca prompt yazdırmamıza gerek yok — o katman
> bizde hazır ve testli durumda. Eğittiğimiz model zaten tracking yapmaz: model her
> karede sadece "kutu + güven skoru" üretir (tespit). Tracking, bu kutuları kareler
> arasında ilişkilendiren klasik bir algoritmadır; öğrenme/prompt işi değildir. Biz
> bunu ByteTrack yöntemiyle (Kalman filtresi ile konum tahmini + IoU eşleştirme +
> jiroskop verisiyle kamera hareketi telafisi) kendi kodumuz olarak yazdık
> (`detection/takip.py`). Senin dediğin "modelin çıktısı kodda işlenerek tracking
> yapılsın" akışı birebir şu an çalışan sistem. Bizden tek beklenen: iyi bir tespit
> modeli (.pt). Eğitilen dosyayı `models/` klasörüne atınca sistem otomatik tanıyor,
> kod değişikliği gerekmiyor. Nasıl çalıştığının basit + teknik anlatımı
> `TAKIP_NASIL_CALISIR.md` dosyasında.

---

## 1) En kritik ayrım: TESPİT ≠ TAKİP

| | TESPİT (detection) | TAKİP (tracking) |
|---|---|---|
| Soru | "Bu karede Talon **nerede**?" | "Bu karedeki kutu, önceki karedekiyle **aynı nesne mi**?" |
| Kim yapar | Eğitilen YOLO modeli (`best.pt`) | Klasik algoritma (bizim kodumuz, `takip.py`) |
| Girdi | Tek kare görüntü | Kutu listesi + zaman + drone attitude (gyro) |
| Çıktı | Kutular: `{cx, cy, w, h, conf}` | Kimlikli, onaylı **iz** (track): "ID 3, 42 karedir izliyorum" |
| Hafıza | YOK — her kare bağımsız | VAR — izin geçmişi, hızı, durumu tutulur |
| Öğrenme | Var (eğitim verisiyle) | Yok (deterministik matematik: Kalman, IoU) |
| "Prompt" | Yok. YOLO'ya prompt atılmaz; girdisi piksel, çıktısı kutudur | Yok. Düz kod; GPU bile gerekmez |

Buradaki yaygın kafa karışıklığı: "modele prompt verelim, tracking yapsın" cümlesi
LLM'lerden (ChatGPT tarzı) gelen bir alışkanlık. YOLO bir **görüntü** modelidir;
konuşmaz, prompt almaz. Tracking de bir modelin değil, modelin **çıktısını tüketen
kodun** işidir — ve o kod yazıldı.

Not: "Prompt ile takip" yapan modeller gerçekten vardır (ör. SAM-2 tarzı video
segmentasyon: nesneyi bir kez işaretlersin, model videoda sürdürür). Biz bunları
**bilerek** kullanmıyoruz: yarışma kuralı 8 (her bileşeni açıklayabilmeliyiz),
gerçek-zaman bütçesi ve otonomi isteri (manuel işaretleme YASAK — bizde hedef seçimi
de otonom). Sahnemiz gökyüzü + tek küçük hedef; bu problemin endüstri standardı ve
en açıklanabilir çözümü tespit-tabanlı takiptir (ByteTrack ailesi). Alternatiflerin
kıyası ayrıca `Avci_Drone_Takip_Model_Analizi.md`'de mevcut.

---

## 2) Basit anlatım — 60 saniyede süreç

Her görüntü karesinde sırayla şunlar olur:

1. **YOLO kutuları döker.** "Şurada %86 ihtimalle Talon var, şurada %23'lük şüpheli
   bir leke var." Model işini burada bitirir.
2. **Takipçi tahmin eder.** Elindeki her iz için "geçen kareden bu kareye geçen
   sürede hedef nereye gitmiş olmalı?" diye sorar. Bunu Kalman filtresi yapar:
   hedefin görüntüdeki hızını öğrenmiştir, sabit hızla ilerletir.
3. **Kamera dönüşü telafi edilir (CMC).** Avcı drone döndüyse görüntüdeki HER ŞEY
   kayar — hedef kıpırdamasa bile. Kafanı hızla sağa çevirdiğinde odadaki eşyaların
   görüş alanında sola kayması gibi. Jiroskop/attitude verisinden "kamera şu kadar
   döndü, o hâlde beklediğim nokta görüntüde şuraya kaymış olmalı" diye tahminler
   kaydırılır. Böylece kendi manevramız hedef kaçtı sanılmaz.
4. **Eşleştirme.** Kaydırılmış tahmin kutuları ile YOLO'nun yeni kutuları örtüşme
   oranına (IoU) göre eşlenir: en çok örtüşen çiftler birbirinin devamı sayılır.
5. **ByteTrack'in püf noktası.** Güven skoru düşük diye kutu çöpe atılmaz. Hedef
   bulanıklaşınca / parazit girince YOLO'nun güveni bir anlığına düşer; o "zayıf"
   kutu, ZATEN VAR OLAN izi sürdürmek için kullanılır — iz kopmaz. Ama zayıf kutu
   YENİ iz **başlatamaz** — parazitten hayalet hedef doğmaz. (İsim buradan: yüksek
   VE düşük skorlu kutuların ikisi de — her "byte" — değerlendirilir.)
6. **Yaşam döngüsü: aday → onaylı → kayıp.** Yeni görülen kutu önce ADAY'dır
   (TENTATIVE); **5 ardışık karede** üst üste eşleşirse ONAYLI (CONFIRMED) olur ve
   ancak o zaman güdüme/kilide sunulur. Tek karelik yanlış pozitif, onaylanamadan
   ölür. Onaylı iz kaybolursa ~0.5 saniye "tahminle taşıma" (coast) yapılır — kısa
   bir bulanıklıkta iz kopmaz; süre aşılırsa iz silinir.

Sonuç: FSM'e (ARAMA→YAKLASMA→GORSEL_TAKIP→KILIT_BILDIR) her an tek bir "en iyi onaylı iz"
sunulur; kilit kuralı ve güdüm bu izin üstünde çalışır.

---

## 3) Veri akışı — "modelin çıktısı kodda işlenerek" tam olarak bu

```
[oyun karesi (BGR)]
      │
      ▼
gorsel_tespit.py ── YOLO best.pt ──► kutu listesi (conf'a göre sıralı):
      │        [{cx, cy, w, h, conf, cls, W, H, t, keypoints?}, ...]
      ▼
takip.py (Takipci.guncelle)  ◄── H_cmc (jiroskop/attitude'dan homografi,
      │                            kamera_model.cmc_homografi)
      │  1) tüm izler için Kalman TAHMİN + CMC kaydırma
      │  2) BYTE eşleştirme (2 tur, IoU)
      │  3) yaşam döngüsü (aday/onaylı/kayıp/silinmiş)
      ▼
en iyi ONAYLI iz: {track_id, bbox, cx, cy, w, h, conf,
                   tespit_mi, track_durumu, keypoints?}
      │
      ▼
algi_hatti.py ── türevler (lam_dot: LOS açısal hızı, Vc: kapanma vekili)
      │           + [pose modeli varsa PnP mesafe/yönelim — FAZ 2]
      ▼
AlgiCiktisi (atomik snapshot) ──► güdüm thread'i (50 Hz, kilitli okuma)
                                   → FSM / kilit kuralı / güdüm yasası
```

- Model YOKSA veya hazır değilse: kutu listesi boş → `hedef=None` → sistem GPS ile
  uçmaya devam eder (zarif bozulma). Yani takip katmanı modele "kutu sözleşmesi"
  dışında hiçbir şekilde bağımlı değildir.
- Model **detect** ise sadece kutu gelir; model **pose** ise ek olarak 6 keypoint
  gelir ve PnP (mesafe/yönelim kestirimi) otomatik açılır. Gelmezse otomatik pasif.
  Takip kodu iki durumda da AYNIDIR.

---

## 4) Teknik anlatım

### 4.1 Model çıktı sözleşmesi (`gorsel_tespit.tespit_hepsi`)

Karedeki TÜM kutular, conf'a göre azalan sırada döner (seçimi takipçi yapar):

```python
{
  "cx": 963.2, "cy": 402.7,   # kutu merkezi (px)
  "w": 38.0,   "h": 22.5,     # kutu boyutu (px)
  "conf": 0.86,               # tespit güveni [0..1]
  "cls": 0,                   # sınıf indeksi
  "W": 1920, "H": 1080,       # görüntü boyutu
  "t": 12.3456,               # kare zaman damgası (sn)
  "keypoints": [[x,y,conf]*6] # YALNIZ pose modelinde
}
```

Takipçinin modelden beklediği her şey bu. Hangi mimariyle eğitildiği (v8/v11, n/s/m)
takibi hiç ilgilendirmez — sözleşmeyi sağlayan her `.pt` tak-çalıştır.

### 4.2 Kalman filtresi — görüntü düzleminde sabit-hız (SORT konvansiyonu)

Her izin durumu görüntü düzleminde tutulur:

```
x = [cx, cy, s, r, v_cx, v_cy, v_s]
     s = w·h  (kutu alanı)      r = w/h  (en-boy oranı; hızı yok — yavaş değişir)
```

- **Tahmin (predict):** `x ← F·x`, `P ← F·P·Fᵀ + Q`. F sabit-hız modeli:
  `cx += v_cx·dt`, `cy += v_cy·dt`, `s += v_s·dt`. dt, kare zaman damgalarından gelir.
- **Güncelleme (update):** ölçüm `z = [cx, cy, s, r]` (YOLO kutusundan). Standart
  Kalman denklemleri: `y = z − H·x`, `S = H·P·Hᵀ + R`, `K = P·Hᵀ·S⁻¹`,
  `x ← x + K·y`, `P ← (I − K·H)·P`.
- Kutuya geri dönüş: `w = √(s·r)`, `h = s/w`.
- Gürültü değerleri `TakipCfg`'de (ölçüm: konum 1 px, alan 10; süreç: konum 1·dt,
  hız 0.01). Başlangıçta hız belirsizliği kasıtlı dev (P'de 1e4): ilk ölçümlerle
  hız hızla oturur.

Neden görüntü düzleminde? Terminal fazda karar görüntü üzerinden veriliyor (IBVS /
kilit dörtgeni); dünya-koordinatı takibe gerek yok, basit ve test edilebilir olan bu.

### 4.3 Gyro-CMC — kamera hareket telafisi

Avcı iki kare arasında dönerse, uzak (dünya-sabit sayılabilir) bir noktanın görüntü
konumu şu homografiyle kayar — **saf rotasyonda derinlikten bağımsız, exact**:

```
x₂ = H · x₁          H = K · R_Δ,kam · K⁻¹
R_Δ,kam = R_dünya→kam(att₂) · R_dünya→kam(att₁)ᵀ
```

- `K`: kamera iç parametre matrisi (FOV'dan türetilir, `kamera_model.K_matrisi`).
- `att = (roll, pitch, yaw)`: iki kare anındaki drone attitude'u (telemetri/gyro).
- Kameranın gövdeye 25° yukarı montajı (`R_mount`) zincire otomatik girer.
- Uygulama: eşleştirmeden ÖNCE her izin Kalman **merkez** tahmini H ile taşınır
  (`warp_merkez`); ardışık kareler arası dönüşte ölçek değişimi ihmal edilebilir
  olduğundan kutu boyutu warp edilmez.

Neden görüntü-tabanlı CMC (ORB/ECC — BoT-SORT'un yaptığı) değil? Arka planımız
gökyüzü: feature'sız, eşleştirilecek doku yok. Elimizde ise tam hızlı ve temiz
attitude telemetrisi var — jiroskoptan telafi hem bedava hem kesin.

Bu telafi olmasa ne olur? Avcı sert döndüğünde tüm görüntü onlarca piksel kayar,
IoU sıfıra düşer, takipçi "hedef kaçtı" sanıp izi düşürür. CMC ile kendi
manevramız hedef hareketi sanılmaz — kilit sürekliliğinin (şartname 6.1.4) ön şartı.

### 4.4 BYTE eşleştirme — ByteTrack'in özü

Her tikte tespitler güvene göre İKİYE ayrılır:

```
yüksek: conf ≥ 0.5          düşük: 0.1 ≤ conf < 0.5
```

1. **1. tur:** yüksek conf kutular ↔ TÜM aktif izler (IoU ile).
2. **2. tur:** 1. turda eşleşmeyen izler ↔ düşük conf kutular. Amaç: blur/parazit
   anında conf'u düşen GERÇEK hedefin izini koparmamak.
3. Kural: **düşük conf kutu yeni iz açamaz** — sadece mevcut izi sürdürebilir.
   Yeni iz yalnızca eşleşmemiş YÜKSEK conf kutudan doğar.
4. Hâlâ eşleşmeyen izler → coast/kayıp; eşleşme IoU'su 0.2 altındaysa sayılmaz.

Eşleştirme **greedy IoU** ile yapılır: tüm (iz, kutu) çiftleri IoU'ya göre sıralanır,
en yüksekten başlanarak çakışmasız atanır. Klasik ByteTrack Hungarian (Macar
algoritması) kullanır; bizim senaryo tek-hedef ağırlıklı olduğundan greedy aynı
sonucu verir (tek izde matematiksel olarak optimal), kodu ise herkesin
açıklayabileceği 15 satırdır — yarışma kuralı 8'e doğrudan hizmet.

### 4.5 İz yaşam döngüsü (durum makinesi)

```
             5 ardışık eşleşme                 eşleşme yok
TENTATIVE ────────────────────► CONFIRMED ────────────────► LOST (coast)
    │ tek kare bile kaçırırsa        ▲    yeniden eşleşirse   │  25 tik (~0.5 sn)
    ▼                                └────────────────────────┘  aşılırsa
 REMOVED ◄───────────────────────────────────────────────────── REMOVED
```

- `MIN_HITS = 5`: FSM'deki "5 kare YOLO onayı" kuralını takipçi devralmıştır —
  ana kontroldeki ham sayaç kalktı, FSM artık `track_durumu == CONFIRMED` sorgular.
  **Amaç: −30 puanlık yanlış kilit paketine karşı zamansal filtre.** Tek karelik
  yanlış pozitif TENTATIVE'ken ilk kaçırmada REMOVED olur; güdüm onu hiç görmez.
- `MAX_COAST = 25` tik: onaylı iz ölçümsüz kalınca Kalman tahminiyle ~0.5 sn
  taşınır (LOST). Bu, kısa bulanıklık/parazitte kilit sayacının korunmasını sağlar;
  yeniden eşleşirse iz AYNI ID ile CONFIRMED'a döner.
- Çok iz varsa FSM'e sunulan tek iz: CONFIRMED/LOST'lar içinde **en uzun yaşayan**
  (eşitlikte ortalama conf'u yüksek olan). Kararlılık ölçütü uzun geçmiştir, anlık
  parlak conf değil.

### 4.6 Takip çıktısı, türevler ve dürüstlük kuralı

İz çıktısında iki kritik alan var:

- `tespit_mi`: bu tikte GERÇEK ölçüm mü eşleşti (True) yoksa kutu Kalman tahmini mi
  (coast, False)? Kilit kuralı ve türevler bunu ayırt eder.
- `keypoints`: yalnızca ölçüm eşleşen tikte taşınır — coast'ta bayat poz PnP'ye
  gitmez.

Güdümün ihtiyaç duyduğu türevler takip çıktısından **algı döngüsünde** hesaplanır
(`algi_hatti._turevler`):

- `lam_dot` (LOS açısal hızı, rad/s): görüntü merkezine göre bearing
  `atan2(cy−H/2, cx−W/2)`'nin sarmal (wrap) farkı / dt.
- `Vc` (kapanma vekili, 1/s): kutu alanının bağıl büyüme hızı `ΔA/A/dt` —
  yaklaşırken hedef görüntüde büyür.

İki kural:
1. **Türev kuralı:** türevler algı kare zaman damgalarıyla alınır; 50 Hz güdüm
   thread'i HAZIR değeri tüketir. Aksi hâlde güdüm aynı ölçümü birden çok kez görür
   (zero-order hold) ve türev sıfırlanma/çift-sayım hatası üretir.
2. **Dürüstlük:** türevler yalnız ÖLÇÜLEN tespitte güncellenir; coast'taki tahmin
   kutusundan türev üretilmez (tahminin türevi bilgi değil, uydurmadır — şartnamenin
   kilit tanımına dürüstlük).

### 4.7 Parametreler (`TakipCfg` — tek yerden ayar)

| Parametre | Değer | Anlamı |
|---|---|---|
| `CONF_YUKSEK` | 0.5 | 1. tur eşleşme eşiği; yeni iz AÇABİLİR |
| `CONF_DUSUK` | 0.1 | 2. tur alt eşiği; yalnız mevcut izi sürdürür |
| `MIN_HITS` | 5 | ADAY→ONAYLI için ardışık eşleşme (FSM 5-kare kuralı) |
| `MAX_COAST` | 25 tik | ölçümsüz tahminle taşıma tavanı (~0.5 sn) |
| `IOU_ESIK` | 0.2 | eşleşme sayılması için asgari IoU (CMC sonrası) |
| `STD_OLCUM_KONUM` | 1.0 px | ölçüm gürültüsü (cx, cy) |
| `STD_OLCUM_ALAN` | 10.0 | ölçüm gürültüsü (alan; en-boy bunun 0.1'i) |
| `STD_SUREC_KONUM` | 1.0 | süreç gürültüsü (konum, ·dt) |
| `STD_SUREC_HIZ` | 0.01 | süreç gürültüsü (hız) |

---

## 5) Neden böyle tasarlandı? (yarışma bağlamı)

- **Kural 8 (açıklanabilirlik):** Hazır tracker kütüphanesi (supervision, boxmot vb.)
  import etmedik; ByteTrack'in özünü ~300 satır saf numpy olarak kendimiz yazdık.
  Jüri "şu satır ne yapıyor?" derse her satırın cevabı var. Birim testleri sim/YOLO
  olmadan sentetik tespitlerle çalışır (`test/test_takip.py`).
- **Kural 6 (hazır güdüm yasağı):** Takip→güdüm zincirinin tamamı (kilit kuralı,
  APN/OIPN) kendi temiz implementasyonumuz; takip katmanı da aynı ilkeyle uyumlu.
- **−30 puan (yanlış kilit paketi):** MIN_HITS=5 zamansal filtresi + "düşük conf yeni
  iz açamaz" kuralı, tek-kare parazitin kilit zincirine sızmasını yapısal olarak
  engeller.
- **Şartname 6.1.4 (kilit sürekliliği):** coast (~0.5 sn) + gyro-CMC, kısa
  blur/parazitte ve kendi manevramızda izi koparmayarak kilit sayacını korur.
  (Kilit kuralındaki 200 ms kaçak toleransı ve köprüleme, `guidance/kilit_kurali.py`.)
- **Gökyüzü sahnesi:** feature'sız arka plan → görüntü-tabanlı CMC imkânsız →
  jiroskop-tabanlı CMC. Tek hedef → Hungarian yerine greedy. ReID/görünüm embedding'i
  gereksiz (ayırt edilecek ikinci nesne yok) → GPU bütçesi YOLO'ya kalır.
- **Otonomi isteri:** manuel işaretleme/tıklama yok — iz seçimi de (en uzun yaşayan
  onaylı iz) otonom bir kuraldır.

---

## 6) Modeli eğiten kişiyi ne ilgilendirir?

Takip katmanı hazır olduğuna göre, eğitim tarafının takibe tek teması **sözleşme**dir:

1. **Detect modeli yeterli.** Kutu + conf üreten her YOLO `.pt`'si takibi besler.
   Pose modeli (6 keypoint, `kpt_shape=[6,3]`) gelirse PnP/OIPN de açılır — ama
   takip için şart değil.
2. **Tak-çalıştır:** `.pt` dosyasını `models/` klasörüne at → arayüzde "↻ Tara" →
   dropdown'dan seç. Kod değişikliği yok; canlı FPS/latency/conf metrikleri ve CSV
   logu otomatik (`detection/model_yonetici.py`).
3. **Conf kalibrasyonu önemli:** BYTE eşikleri (0.5 / 0.1) conf'a dayanır. Model
   gerçek hedefe tipik olarak ≥0.5 veriyorsa mükemmel; sürekli 0.3-0.4 bandında
   kalıyorsa iz coast'a düşmez ama YENİ iz geç açılır (ilk yakalama gecikir).
   Bu yüzden eğitim raporunda conf dağılımını görmek isteriz.
4. **Eğitim verisinde işe yarayan şeyler:** uzak/küçük hedef örnekleri (ARAMA fazı
   ilk yakalama), motion blur ve parazitli kareler (BYTE'ın 2. turunun işe yaradığı
   yer), boş gökyüzü negatifleri (yanlış pozitif oranını düşürür — TENTATIVE
   filtresine az iş bırakır).
5. **Üretim eşiği ayrıdır:** kilit/angajman zincirini besleyen conf eşiği kodda
   sabittir ve muhafazakârdır; model yaml'ındaki `conf` yalnız görselleştirme/metrik
   içindir. (Kural: yanlış kilit −30.)

---

## 7) İlle "yapay zekaya verilecek prompt" gerekiyorsa

Tracking kodu yazdırmak İÇİN prompt gerekmiyor (kod var). Ama bir yapay zekaya
bağlam verip soru sormak istersen şu özeti yapıştırabilirsin:

> Sabit kanatlı avcı İHA'mız, gökyüzündeki tek bir hedef İHA'yı (Talon) kamerayla
> izliyor. YOLO tabanlı detect modeli her karede {cx, cy, w, h, conf} kutuları
> üretiyor. Takip katmanımız kendi yazdığımız sadeleştirilmiş ByteTrack: görüntü
> düzleminde sabit-hız Kalman filtresi (durum [cx,cy,alan,en-boy,hızlar], SORT
> parametrizasyonu), iki turlu BYTE eşleştirme (yüksek conf ≥0.5 birinci tur,
> 0.1–0.5 ikinci tur yalnız iz sürdürür, yeni iz açamaz), greedy IoU ataması
> (eşik 0.2), iz yaşam döngüsü TENTATIVE→(5 ardışık eşleşme)→CONFIRMED→(kayıpta
> ~0.5 sn Kalman coast)→REMOVED. Kamera hareketi telafisi görüntüden değil
> jiroskoptan: iki kare arası attitude farkından H = K·R_Δ·K⁻¹ homografisi kurulup
> eşleştirme öncesi iz merkezleri warp ediliyor (gökyüzü feature'sız olduğundan
> ORB/ECC yerine). Takip çıktısından LOS açısal hızı ve kutu-büyüme kapanma vekili
> algı zaman damgalarıyla türetilip 50 Hz güdüm döngüsüne snapshot olarak sunuluyor.
> Sorum şu: ...

Bu paragraf aynı zamanda video anlatımının "tracking" bölümünün iskeletidir.

---

## 8) Mini sözlük

- **IoU (Intersection over Union):** iki kutunun kesişim alanı / birleşim alanı.
  1.0 = tam üst üste, 0 = hiç örtüşmüyor. "Aynı nesne mi?" sorusunun metriği.
- **Kalman filtresi:** gürültülü ölçümlerden konum+hız kestirip bir sonraki konumu
  tahmin eden klasik optimal filtre. Öğrenme yok; iki adım: tahmin et, ölçümle düzelt.
- **conf (confidence):** modelin "bu gerçekten hedef" güveni, 0–1.
- **CMC (Camera Motion Compensation):** kameranın KENDİ hareketinin görüntüdeki
  kaymasını geri alma. Bizde jiroskop/attitude'dan, homografiyle.
- **Homografi (H):** görüntü düzlemini görüntü düzlemine götüren 3×3 dönüşüm; saf
  kamera dönüşünde pikselin nereye kaydığını exact verir.
- **Coast:** ölçüm yokken izi Kalman tahminiyle "süzülerek" sürdürme (bizde ~0.5 sn).
- **Track (iz):** kimlikli, geçmişli hedef kaydı: ID, kutu, hız, durum, yaş, conf
  ortalaması.
- **LOS (Line of Sight):** avcıdan hedefe bakış hattı; `lam_dot` bu hattın açısal
  dönme hızı (güdüm yasasının ana girdisi).
- **FSM:** durum makinesi (ARAMA→YAKLASMA→GORSEL_TAKIP→KILIT_BILDIR→ANGAJMAN);
  takipçinin "CONFIRMED" bilgisini tüketen üst katman.

# TALON VERİ SETİ — ne yaptık, neden, hangi ölçümle

> 2026-08-09 · Drones of War'da tespit modeli için sıfırdan veri seti.
> Bu belge **yapılan işin kaydı**: her karar bir ölçüme dayanıyor, ölçüm
> tutmadıysa o da yazılı.

---

## 1. Sorun

Model HUD metinlerini uçak sanıyordu — sinyal göstergesi, `ALT/SPD`,
`ARMED / TRIGGER:NOT READY`, batarya okuması, `Mode: ANGL AIR`.

Kök neden: `avci_yolo.pt` **Gazebo'da** eğitildi, DoW'un HUD'unu hiç görmedi.
Ölçüm (`docs/dedektor_testi.md`, imgsz=1280 ile adil koşu):

| | avci_yolo (Gazebo) | best.pt (DoW) |
|---|---|---|
| Hedefle eşleşen tespit | %4.0 | %12.0 |
| **Yanlış pozitif** | **%96.0** | %28.0 |

İki iş gerekiyordu: **negatif örnek** (HUD'un arka plan olduğunu öğret) ve
**DoW pozitifi** (hedefin nasıl göründüğünü öğret).

---

## 2. Negatif seti — 1000 hard negative

`C:\Users\Zeylo\Desktop\talon_negatif_1000\`

**Hard negative** = modelin *şu an* yanlış-pozitif ürettiği, hedefsiz kare.
Rastgele boş gökyüzü karesi bir şey öğretmez; modelin takıldığı kare öğretir.

### Güvenlik kuralı (bu işin tek gerçek riski)

Bir karede hedef **görünüyorsa** ve etiketsiz verilirse, modele *"bu uçağı
GÖRME"* denmiş olur — gerçek tespiti bozar. O yüzden kare ancak şu koşullarda
negatif sayıldı:

- 6 keypoint'in **tamamı kamera arkasında**, veya
- hepsi önde ve projekte kutu kadrajın **tamamen dışında** +
  `max(8 px, 0.5 × kutu boyutu)` emniyet payı

Pay kutu boyutuyla ölçekleniyor çünkü hedef **rotasyonu** bozulabilen kanaldan
geliyor (truth'ta rotasyon yok); o hatanın büyüklüğü hedefin kendi boyutuyla
sınırlı. Aradaki her şey (kısmen görünür, kenarda, kp'lerin bir kısmı arkada)
**reddedildi**.

QA: kenar payına göre sıralanmış 30 kare gözle denetlendi — en riskli karede
(pay 18 px) uçak yok.

### Sonuç

```
kaydedilen kare   1505
GÜVENLİ negatif   1074      (kamera arkası 307 + kadraj dışı 767)
kadrajda -> RED    424
FP üreten kare    1072/1074  (%99.8)
yazılan            1000
```

Yanlış kutuların dağılımı — hipotez doğrulandı:

| HUD öğesi | Yanlış kutu |
|---|---|
| Sol üst — sinyal | 1798 |
| Sağ üst — ALT/SPD | 1165 |
| Orta — ARMED/TRIGGER | 921 |
| Sol alt — batarya | 639 |
| Sağ — Mode | 166 |
| **toplam** | **4689 / 5228 = %90** |

---

## 3. Pozitif seti — 5045 kare

`C:\Users\Zeylo\Desktop\talon_pozitif\` (ham) →
`C:\Users\Zeylo\Desktop\talon_dataset_v1\` (paketlenmiş)

### 3.1 Yakalama

Gerçek GPS ile otonom görev, 5 Hz, görev başlangıcından 20 sn sonra
(kalkış kadraja girmesin). Her kare için `.png` + boş `.txt` + telemetri.

Kritik ek: **~48 Hz sürekli telemetri akışı** (`telemetri_akis.jsonl`).
Bu olmadan gecikme ölçülemiyordu — ilk denemede 2 Hz'le çözemedim.

### 3.2 Etiket elle çizilmedi, hesaplandı

Simülasyon hedefin **kesin konumunu** veriyor (truth kanalı). Uçağın 3B şeklini
(6 nokta) ve kamerayı (tilt 25°, HFOV) biliyoruz → uçağın ekranda nereye
düştüğü **hesaplanabilir**.

İlk doğrulama, kullanıcının elle çizdiği 10 kareye karşı:

```
marj 0.06/0.20 (pose için ayarlanmış)  ->  IoU 0.825
marj 0.07/0.10 (kullanıcı tarzına kalibre) -> IoU ort 0.868  medyan 0.907
```

Elle çizim ~9 sn/kare sürüyordu → 5000 kare **12,5 saat**. Hesapla ~1 sn/kare.

### 3.3 Gecikme (dt) — ilk başarısızlık ve düzeltmesi

Banka yapan (yatık) karelerde kutu kayıyordu. Ölçüm:

```
IoU >= 0.6 -> ortalama |roll| 14.7°
IoU <  0.6 -> ortalama |roll| 34.6°
```

Denenen ve **çürütülen** açıklamalar:
- roll işareti ters mi? → `+1` en iyi (0.755), `-1` daha kötü (0.709). **Değil.**
- kutu küçük mü? → bankaya bağlı marj taraması, en iyi yine sabit değer. **Değil.**

Gerçek neden: **kare telemetriden eski.** 2 Hz veriyle çözülemedi (ara-değerleme
hatası kazancı yiyordu). 48 Hz akışla net tepe:

```
dt (sn)   ort     roll<20   roll>=20
 0.00   0.693     0.734      0.637
 0.10   0.824     0.865      0.768   <- tepe
 0.20   0.695     0.726      0.653
```

`dt = 0.10 sn` uygulandı.

### 3.4 Düzeltme modeli — ikinci iterasyon

İlk denemede tek bir sabit ofset (+4 px) takıldı. **Zayıftı** — hata sabit değil,
koşula göre değişiyor. Yerine artığı ölçülebilir büyüklüklerin fonksiyonu olarak
öğrenen model kuruldu (`kalibre_et.py`):

- 4 regresyon: yatay kayma, dikey kayma, genişlik oranı, yükseklik oranı
- Hepsi **kutunun kendi boyutuna göre** normalize → mesafeden bağımsız
- 8 özellik: sabit · `sin/cos/|sin|(roll)` · `sin/cos(aspect)` · `log(menzil)` ·
  `log(kutu kenarı)`
- Ridge regresyon, sabit terim cezalandırılmaz

**5-kat çapraz doğrulama** (hepsi *görülmemiş* karelerde):

```
                        ort     medyan   >=0.7   <0.5
ham projeksiyon        0.8448  0.8593    %93     %1
+ sabit ofset (eski)   0.8606  0.8846    %94     %1
+ ÖĞRENİLEN MODEL      0.8781  0.8982    %95     %0

|roll| <  20   0.8745 -> 0.8812
|roll| >= 20   0.8036 -> 0.8737     <- görsel olarak bozuk olanlar
```

**Seçim yanlılığı önlendi:** kalibrasyon setine sadece *düzeltilen* değil,
insanın **gözden geçirdiği tüm** kareler girdi (716). Yalnızca değiştirilenleri
almak, modele "zor kare" dağılımını öğretip iyi kareleri bozardı.

### 3.5 Bağımsız denetim

Etiketi truth projeksiyonundan üretip **yine truth projeksiyonuyla** kontrol
etmek totolojidir. Dört bağımsız sinyal kuruldu (`denetle.py`):

1. **Dedektör uyumu** — `best.pt` kareyi piksellerden bulur, geometriyi bilmez
2. **İçerik kontrastı** — kutunun içi çevre halkasına göre koyu mu
3. **Zaman sürekliliği** — 0.2 sn arayla kutu sıçrayamaz
4. **Boyut-menzil** — fizik: 1.718 m kanat, HFOV biliniyor

**Eşikler uydurulmadı**, insanın onayladığı karelerin dağılımından öğrenildi.
Referans yoksa araç hüküm vermez; ölçüm alınamadıysa kanıt sayılmaz.

Bulgu:

```
İNSAN dedektör-IoU : 0.9266   OTO : 0.8474   fark -0.0792
kutu_BOS_gorunuyor : 157 kare
```

Denetim **gerçek hata yakaladı**: `talon1_1071`'de kutu boş gökyüzünde, Talon
sağdaydı.

### 3.6 Başarısız deneme — kırpma testi (kayda geçsin)

"Kutunun içinde Talon var mı" sorusunu doğrudan sormak için kutu kırpılıp
büyütülerek dedektöre verildi. **Çalışmadı:** `best.pt` 640'ta *küçük* hedefle
eğitildi; büyütülmüş kırpma dağılım dışı. İnsanın onayladığı, içinde apaçık
Talon olan kutularda bile güven medyanı **0.19** — eşik sıfıra çöktü.

Doğru sinyal tam-kare dedektörüydü; ona dönüldü.

### 3.7 Onarım — sadece kırığı tamir et

Etiketi her farkta dedektörün kutusuyla değiştirmek IoU'yu tavana çıkarırdı ama
**sahte kazanç** olurdu: veri seti dedektörün kendi çıktısına döner, yeni model
yalnızca eskisini taklit eder, truth geometrisinden gelen bağımsız bilgi kaybolur.

Kural (`olc_onar.py`):

| Durum | Karar |
|---|---|
| IoU ≥ 0.50 | **BIRAK** — stil farkı, projeksiyon korunur |
| IoU < 0.50 **ve** dedektör conf ≥ 0.80 | **ONAR** — biri açıkça yanlış, hangisi belli |
| IoU < 0.50, dedektör emin değil | **BIRAK** — bilmiyoruz |
| Etiket yok, dedektör güvenli | ONAR |
| Etiket yok, dedektör de yok | **SİL** → `_silinen/` |

Sonuç:

```
onarılan 29 · silinen 0 · bırakılan 4250
KIRIK ETİKET (IoU<0.5):  50 -> 23 kare  (%1.2 -> %0.5)
ortalama IoU: 0.8473 -> 0.8515
```

Ortalama neredeyse değişmedi çünkü sorun 29 kırık karede değildi; kalan fark
**hassasiyet farkı** (otomatik kutular hedefin üstünde ama ~0.08 IoU daha gevşek).

### 3.8 İnsan katkısı

Kullanıcı **766+ kareyi** elle gözden geçirdi/düzeltti. Bu kareler hem veri hem
**ölçüt**: tüm eşikler ve kalibrasyon onların dağılımından öğrenildi.
`--koru-kadar` sınırı koda gömülü — `--ustune-yaz` bile bu sınıra uyar,
insan emeği hiçbir bayrakla ezilemez (her koşuda bayt bayt doğrulandı: 0 ihlal).

---

## 4. Paketleme — train/val ayrımı

`C:\Users\Zeylo\Desktop\talon_dataset_v1\`

**Rastgele bölme yapılmadı.** Kareler tek uçuştan 5 Hz ile alındı; ardışık
kareler 0.2 sn arayla, neredeyse aynı görüntü. Rastgele bölünseydi kare N
train'e, N+1 val'e düşerdi → val, train'in kopyası olur → **val mAP'i sahte
yüksek** çıkar, ezberleme görünmez.

Yerine **blok bazlı**: uçuş 20 ardışık bloğa bölündü, her blok bütün halinde
train veya val. Val blokları uçuşa **yayıldı** (başı uzak, sonu yakın mesafe).
Blok sınırlarında **5'er kare atıldı** (190 kare) — sınırın iki yanı hâlâ benziyor.

```
train  4818 görüntü  (pozitif 4128 + negatif 690 = %14.3)
val     847 görüntü  (pozitif  727 + negatif 120 = %14.2)
```

Ultralytics'in kendi yükleyicisiyle doğrulandı:
`check_det_dataset OK · nc=1 · train 4128 kutu / 690 background · val 727 / 120`

Görüntüler **sert bağlantı** (11 GB anlık, disk yer kaplamadı).

---

## 5. Dürüst sınırlar

**Etiket hassasiyeti.** Otomatik etiketler bağımsız ölçütte 0.85, insan çizimi
0.93. Bu kırıklık değil, gevşeklik. `>=0.85` olan kare oranı: insan %97,
otomatik %62. Kutu regresyonu biraz gevşek öğrenilebilir.

**Mesafe dağılımı dar** — en ciddi sınır:

```
  0-10 m   %66.7
 10-20 m   %33.2
 20-40 m    %0.1
 40 m+      %0.0
```

Model 0-20 m'de çok iyi, **20 m üstünde kör** olacak. Görsel güdüme geçiş
~40 m'de olduğu için o bant boş. Sebebi: gerçek GPS güdümü 7-9 m'de istasyona
oturuyor ve orada kalıyor. **Etiketle düzeltilemez, yeniden uçmak gerekir.**
Çözüm: v2/bozuk GPS koşuları karıştırmak (39-44 m'de oturur) veya manuel uzak
uçuş.

**Val aynı uçuştan.** Blok ayrımı sızıntıyı engelliyor ama aynı sahne, ışık,
arka plan. Yüksek val mAP'i genelleme kanıtı **değildir** — asıl sınav HUD
yanlış-pozitif testi ve canlı uçuş.

---

## 6. Araçlar

Hepsi `veriseti/` altında, geliştirme aracı (teslim paketine girmez).
Toplam **~90 birim testi**.

| Araç | Görevi |
|---|---|
| `negatif_topla.py` | Hard negative madencisi; güvenlik kuralı + FP ısı haritası |
| `bbox_etiketle.py` | Canlı bbox etiketleyici; truth ön-doldurma, tutamaç tuşları, kare silme |
| `oto_etiket.py` | Toplu otomatik etiket; dt telafisi, kalibrasyon, koruma sınırı |
| `kalibre_et.py` | Elle düzeltmelerden düzeltme modeli öğrenir (çapraz doğrulamalı) |
| `denetle.py` | Dört bağımsız sinyalle denetim; eşikler insan dağılımından |
| `kutu_dogrula.py` | Kırpma testi (başarısız oldu — kayıt için duruyor) |
| `olc_onar.py` | Ölç → kırığı onar → yeniden ölç |
| `paketle.py` | Blok bazlı train/val + data.yaml + sert bağlantı |
| `dogrula.py` | Biçim denetimi + **gerçek ultralytics yükleyicisi** |

Yakalama `web/server.py` içinde, env bayrakları arkasında:
`AVCI_NEG_KAYIT` (negatif), `AVCI_KAYIT` (pozitif) — verilmezse thread hiç
başlamaz, davranış değişmez.

---

## 7. Eğitim

Başlangıç ağırlığı **`avci_yolo.pt`** (YOLO11n) — kullanıcı kararı, mimari
değişmesin diye. `imgsz=640` seçildi: mimari değil eğitim parametresi; canlı
sistem 640'ta koşuyor (GPU oyunla paylaşılıyor, 1280 ~4x yavaş).

```bash
cd talon_dataset_v1
chmod +x egit.sh
./egit.sh              # data.yaml yolunu otomatik ayarlar
```

Önemli ayarlar ve gerekçeleri:

| | |
|---|---|
| `lr0=0.005` | fine-tune; 0.01 Gazebo ağırlıklarını fazla sarsar |
| `scale=0.5` | **en önemlisi** — mesafe çeşitliliği zayıf, ölçek artırımı telafi eder |
| `close_mosaic=10` | son 10 epoch gerçek kadraja alışsın |
| `save_period=10` | çökerse baştan başlama |

Duman testi (1 epoch): `mAP50 0.993 · mAP50-95 0.719`. Yüksek olması normal —
tek sınıf, hedef büyük, val aynı uçuştan.

## 8. Eğitim sonrası ölçüm zinciri

**(a) HUD yanlış-pozitif — en kritik**
```bat
python veriseti\negatif_topla.py ^
  --oturum C:\talon_dataset_v2\negatif_ham\oturum_20260809_080936 ^
  --model <yeni_best.pt> --n 1000 --cikti <klasor>
```
Aynı 1074 karelik havuz → `toplam_fp_kutu` ve ısı haritası **doğrudan
karşılaştırılabilir**. Bugünkü model 5228 yanlış kutu üretiyor. Düşmezse
negatifler işe yaramamış demektir.

**(b) Etiket uyumu**
```bat
python veriseti\olc_onar.py --klasor <talon_pozitif> --model <yeni> ^
  --koru-kadar 999999 --kuru
```
Hiçbir şey değiştirmez; yeni modelin insan karelerine uyumunu ölçer (bugün 0.9266).

**(c) Canlı uçuş** — `set AVCI_MODEL=<yeni_best.pt>` ile takıp gerçek görevde.

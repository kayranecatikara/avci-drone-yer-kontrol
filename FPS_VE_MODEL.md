# FPS ve Model — kurulum, hızlandırma, doğrulama

**Branch:** `model-fps` · 2026-08-23

Bu belge tek bir soruyu bitirmek için yazıldı: **"model bende 14 FPS ile çalışıyor, neden?"**

Cevap kısaca: modelin `.pt` hâli yavaş, `.engine` hâli **7 kat** hızlı, ve `.engine`
dosyası **taşınamadığı için** repoda yok — kendi makinende üretmen gerekiyor. Tek komut,
iki buçuk dakika.

---

## 0. Acelen varsa — üç komut

```bash
python arac/kurulum_kontrol.py     # neyin eksik olduğunu söyler
python arac/motor_kur.py           # TensorRT motorunu üretir  (~2-3 dk)
python arac/fps_teshis.py          # kazancı ölçer
```

Sonra `python main.py` → tarayıcıda `http://127.0.0.1:8000`.

Gerisini okumana gerek yok. Ama bir yerde takılırsan bölüm 6'da teşhis ağacı var.

---

## 1. Bu branch'te ne var

| dosya | ne |
|---|---|
| `models/talon_v4.pt` | yeni tespit modeli (18,3 MB) |
| `guidance/ana_kontrol.py` | `VIS_MODEL_PATH` → v4 |
| `detection/gorsel_tespit.py` | motor seçimi + sessiz düşmeyi bitiren uyarı |
| `arac/motor_kur.py` | **yeni** — TensorRT `.engine` üretir |
| `arac/kurulum_kontrol.py` | **yeni** — ortam/model/GPU denetimi |
| `arac/fps_teshis.py` | model başına ayrı süreçte hız ölçümü |
| `FPS_VE_MODEL.md` | bu belge |

`.engine` dosyaları **bilerek yok** — sebebi bölüm 3'te.

---

## 2. Model: talon_v4

`talon_v3` üzerine ince ayar. 40 epoch, imgsz 960, `patience` kapalı.

**Veri** (`19 024` kare): 16 332 eski + **1 629 yeni 15-43 m kare** (uzak ağırlıklı,
%27'si 35-43 m) + **966 negatif** (hedefin sahnede hiç olmadığı kareler).
Negatif oranı %1,21 → **%6,7**. Dedektörün yanlış-pozitif verdiği 51 "zor negatif"
eğitimde 3 kat tekrarlandı.

**Aynı doğrulama setinde v3'e karşı ölçüldü** (2 529 pozitif + 169 negatif):

| ölçüt | v3 | **v4** |
|---|---|---|
| tespit | %93,0 | **%93,6** |
| hiç bulamama | %2,6 | **%2,1** |
| 25-30 m tespit | %85 | **%90** |
| **35-50 m tespit** | %75 | **%81** |
| **yanlış pozitif** | %4,7 | **%0,0** |
| IoU ortanca | 0,94 | 0,94 |

Uzak menzil zayıf taraftı, veriyi oraya ağırlıklandırdık, en büyük kazanç orada geldi.

⚠ **Bilinen açık:** doğrulama setinde %0 olan yanlış pozitif, **canlı uçuşta sıfır
değil**. Örneklenen 12 canlı tespitin 9'u (güven 0,29-0,43) boş araziydi; güveni
≥0,48 olanların hepsi gerçek hedefti. Sebebi muhtemelen şu: 966 negatifin tamamı oyun
**dondurulmuşken** çekildi, canlı uçuş kareleri farklı. Eşiği yükseltmek (0,25 → ~0,45)
bunu büyük ölçüde keser ama önce ölçülmeli — eşik bir zamanlar 0,35'ten 0,25'e
indirildiğinde kilit **ikiye katlanmıştı**.

---

## 3. FPS neden düşük — ölçülmüş sebep

Aynı model, aynı makine, aynı 40 kare (RTX 4060, oyun + sunucu birlikte koşarken):

| motor | tam kare | kare/sn | tespit | not |
|---|---|---|---|---|
| `.pt` | **113,5 ms** | **3,1** | 20/20 | varsayılan hâl |
| `.onnx` | 752,4 ms | 0,6 | — | onnxruntime CPU'ya düşüyor → **elendi** |
| **`.engine`** | **13,1 ms** | **21,3** | 20/20 | **7 kat hızlı**, kutu kayması yok |

Tespit sayısı ve kutu konumu birebir aynı — hız kazancı **bedava**, doğruluk kaybı yok.

### `.engine` neden repoda yok

TensorRT motoru derlenirken **senin GPU'nun mimarisine, sürücü sürümüne ve TensorRT
sürümüne** göre optimize edilir. Başka makinede üretilmiş bir `.engine`:

- ya hiç yüklenmez (sistem `.pt`'ye düşer, yani yine yavaş),
- ya da yüklenir ama beklenmedik davranır.

Bu yüzden `.gitignore`'da ve **her makinede yeniden üretilir**. Üretim tek seferlik,
2-3 dakika.

### Eskiden sessizdi, artık değil

`.engine` yoksa sistem eskiden **hiçbir şey yazmadan** `.pt` ile koşuyordu ve kurulum
yapan kişi bunu ancak FPS'e bakarak anlıyordu — nitekim öyle oldu. Artık başlangıçta
açıkça uyarı basılıyor.

---

## 4. Kurulum — adım adım

### 4.1 Ön koşullar

| gereksinim | neden |
|---|---|
| NVIDIA GPU | TensorRT yalnız NVIDIA'da çalışır. GPU yoksa sistem CPU'da ~7 kat yavaş koşar |
| Güncel NVIDIA sürücüsü | TensorRT sürücüye bağlı |
| Python 3.9+ | |
| Oyun: `Drones of War Teknofest` | repoda **yok** (çok büyük), ayrıca kurulu olmalı |

### 4.2 Depoyu al

```bash
git clone https://github.com/kayranecatikara/avci-drone-yer-kontrol.git
cd avci-drone-yer-kontrol
git checkout model-fps
```

### 4.3 Sanal ortam ve bağımlılıklar

```bash
python -m venv .venv
.venv\Scripts\activate            # Linux/macOS: source .venv/bin/activate

pip install --upgrade pip
pip install torch --index-url https://download.pytorch.org/whl/cu121
pip install ultralytics tensorrt numpy pillow mss
```

⚠ `pip install torch` düz hâliyle **CPU sürümünü** kurar ve her şey yavaşlar.
Yukarıdaki `--index-url` satırını kullan. Kurulumdan sonra doğrula:

```bash
python -c "import torch; print(torch.cuda.is_available(), torch.version.cuda)"
```

`True 12.1` gibi bir çıktı görmelisin. `False` görürsen GPU kullanılmıyor demektir.

### 4.4 Ortamı denetle

```bash
python arac/kurulum_kontrol.py
```

Her satır `✔` ya da `⛔` ile biter; `⛔` olanın altında ne yapılacağı yazar.
Beklenen çıktı:

```
  torch                      2.5.1+cu121                        ✔
  ultralytics                8.4.83                             ✔
  tensorrt                   11.1.0.106                         ✔
  CUDA kullanilabilir        True                               ✔
  GPU                        NVIDIA GeForce RTX 4060 Laptop GPU ✔
  aktif model                talon_v4.pt                        ✔
  TensorRT motoru            YOK                                ⛔
      -> python arac/motor_kur.py     <-- FPS SORUNUNUN COZUMU BU
```

### 4.5 ⭐ Motoru üret — FPS düzeltmesi burada

```bash
python arac/motor_kur.py
```

- Aktif modeli (`Cfg.VIS_MODEL_PATH`) bulur
- Modelin **eğitildiği imgsz**'i ağırlıktan okur (v4 için 960) — yanlış imgsz yanlış sonuç verir
- FP16 ile derler, `models/talon_v4.engine` üretir

Süre ~2-3 dakika. Bittiğinde:

```
     ✔ HAZIR  21.0 MB   140 sn
```

Bütün modeller için: `python arac/motor_kur.py --hepsi`
Yeniden üretmek için: `--zorla`

### 4.6 Kazancı ölç

```bash
python arac/fps_teshis.py
```

Her modeli **ayrı bir alt süreçte** ölçer. Bu önemli: aynı süreçte arka arkaya
ölçmek sonucu bozuyor — daha önce bir modeli 50 ms sanmıştık, ayrı süreçte
ölçünce 10,2 ms çıktı.

### 4.7 Çalıştır

```bash
python main.py
```

Tarayıcı: `http://127.0.0.1:8000`

Başlangıç çıktısında **şu satırı gör**:

```
Loading .../models/talon_v4.engine for TensorRT inference...
[GORSEL] MODEL: talon_v4.pt  (imgsz=960, device=cuda, half=True, sahi=False)
```

`engine` kelimesini görmüyorsan motor kullanılmıyor demektir → bölüm 6.

---

## 5. Beklenen sayılar

Ölçüm: RTX 4060 Laptop, oyun + sunucu birlikte koşarken.

| durum | tespit süresi | FPS |
|---|---|---|
| `.engine` yok (`.pt`) | ~113 ms | **~3** |
| `.engine` var, tek başına | ~13 ms | — |
| `.engine` var, oyunla birlikte | ~34-44 ms | **~21** |

Yani **21 FPS bu donanımda normal**. `.engine` kurulduktan sonra hâlâ 3-5 FPS
görüyorsan motor yüklenmiyordur.

Kendi makinende ölçmek için sunucu çalışırken:

```bash
python -c "import urllib.request,json; d=json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/telemetry')); p=d['gorsel']['perf']; print('FPS', p['fps'], ' tespit_ms', p['det_ms'])"
```

---

## 6. Hâlâ yavaşsa — teşhis ağacı

Sırayla, atlamadan:

**1) Motor gerçekten yüklendi mi?**
Sunucunun başlangıç çıktısında `for TensorRT inference` satırı var mı?
Yoksa: `models/` altında `.engine` var mı bak; yoksa `arac/motor_kur.py` koştur.
Varsa ama yüklenmiyorsa, `[GORSEL] TensorRT engine yuklenemedi` satırı **sebebi yazar**
(genelde TensorRT sürüm uyuşmazlığı) → `--zorla` ile yeniden üret.

**2) GPU gerçekten kullanılıyor mu?**
```bash
python -c "import torch; print(torch.cuda.is_available())"
```
`False` ise CPU'dasın. `pip install torch --index-url .../cu121` ile yeniden kur.

**3) Oyun GPU'yu mu yiyor?**
Başka bir terminalde `nvidia-smi` bak. Oyun + tespit aynı GPU'yu paylaşıyor.
Oyunun grafik ayarlarını düşürmek tespit süresini kısaltır.

**4) imgsz doğru mu?**
`kurulum_kontrol.py` çıktısında `imgsz 960` görmelisin. Model 960'ta eğitildi;
başka değer hem yavaşlatır hem doğruluğu bozar.
Elle: `set AVCI_IMGSZ=960` (Windows) / `export AVCI_IMGSZ=960`.

**5) Ekran yakalama mı yavaş?**
Tespit süresi ekran yakalama + ön işleme + çıkarımı kapsar. Motor kuruluyken çıkarım
~13 ms; kalan ~20-30 ms bu tarafta. Oyunu **kenarlıksız pencere** kipinde çalıştırmak
ve pencereyi ön planda tutmak yardımcı olur.

⚠ Oyun ön planda değilken sistem kare kaydetmez/işlemez — ölçüldü: odak kaybında
hız **333 → 120 kare/saat** düştü.

---

## 7. Tuzaklar

**`.engine` taşınmaz.** Başka bilgisayardan kopyalama. Repoya ekleme.
`.gitignore` zaten engelliyor.

**Sessiz düşme.** `.engine` yoksa sistem `.pt` ile koşar. Artık uyarı basıyor ama
uyarıyı görmezden gelirsen 7 kat yavaş çalışır ve sebebini anlamazsın.

**Motoru kapatmak istersen:** `set AVCI_MOTOR=pt` — sadece hata ayıklama için.

**Modeli değiştirmek:** `guidance/ana_kontrol.py` içinde `VIS_MODEL_PATH`.
`talon_v3.pt` yazarsan eski modele dönersin (dosya duruyor, silinmedi).
Yeni modele geçince **o model için de motor üretmen gerekir**.

**Aynı süreçte arka arkaya ölçüm yapma.** Dört modeli tek süreçte ölçtüğümüzde
sonuç 50 ms çıkmıştı; ayrı süreçlerde ölçünce 10,2 ms. `fps_teshis.py` bunu doğru yapar.

---

## 8. Arkadaşına vereceğin tek cümle

Claude Code'a şunu yapıştırması yeterli:

```
https://github.com/kayranecatikara/avci-drone-yer-kontrol reposunun model-fps
branch'ini çek, FPS_VE_MODEL.md dosyasını oku ve oradaki adımları uygula:
kurulum_kontrol.py ile eksikleri bul, motor_kur.py ile TensorRT motorunu üret,
fps_teshis.py ile kazancı ölç, sonra main.py'yi başlat.
```

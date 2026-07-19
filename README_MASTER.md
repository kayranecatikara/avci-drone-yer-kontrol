# 🎯 TALON İHA Pose Dataset — Sıfırdan Tüm Detaylar

> **Hazırlayan:** Zeylo  
> **Tarih:** Temmuz 2026  
> **Amaç:** Bu doküman, TALON insansız hava aracı (İHA) için bilgisayarlı görü (computer vision) tabanlı bir **6 Keypoint Pose Detection** ve **Bounding Box** veri seti oluşturma sisteminin **sıfırdan nasıl yapıldığını, neden böyle tasarlandığını, nasıl çalıştırıldığını ve nasıl doğrulandığını** aşırı detaylı şekilde anlatır.

---

## 📂 Klasör Yapısı

```
C:\Users\Zeylo\Desktop\Berat\
│
├── talon_dataset\                    ← ANA PROJE KLASÖRü (Herşey burada)
│   ├── main.lua                      ← Oyun motorunun içinde çalışan ANA Lua scripti
│   ├── capture_controller_yeni.py    ← Python tarafındaki ANA yakalama kontrolcüsü
│   ├── status.txt                    ← Lua ↔ Python haberleşme dosyası (köprü)
│   ├── control.json                  ← Genel kontrol/konfigürasyon dosyası
│   ├── fpv_config.json               ← FPV bozulma efektleri ayarları
│   ├── best.pt                       ← Eğitilmiş YOLO model ağırlıkları
│   │
│   ├── dataset\                      ← HAM VERİ SETİ (PNG + JSON çiftleri)
│   │   ├── talon_0001.png            ← Temiz ekran görüntüsü (üzerinde çizim yok)
│   │   ├── talon_0001.json           ← Metadata (konum, rotasyon, keypoint'ler)
│   │   ├── talon_0002.png
│   │   ├── talon_0002.json
│   │   └── ...                       ← Binlerce çift dosya
│   │
│   ├── dataset_annotated\            ← AÇIKLAMALI GÖRSELLER (keypoint'ler çizilmiş)
│   │   ├── talon_0001.png            ← Üzerinde kırmızı noktalar çizilmiş versiyon
│   │   └── ...
│   │
│   ├── dataset_auto_bbox\            ← OTOMATİK BBOX YOLO ETİKETLERİ
│   │   ├── talon_0001.txt            ← YOLO formatında bbox etiketi
│   │   └── ...
│   │
│   ├── draw_keypoint.py              ← Gelişmiş keypoint çizim aracı (iskelet + bbox)
│   ├── draw_keypoints.py             ← Basit keypoint çizici + YOLO etiket üretici
│   ├── auto_export_bbox.py           ← Otomatik Bounding Box YOLO export
│   ├── prepare_yolo_dataset.py       ← YOLO dataset hazırlama + ZIP paketleme
│   ├── bbox_editor.py                ← PyQt5 GUI ile bbox düzenleme aracı
│   ├── keypoint_editor.py            ← PyQt5 GUI ile keypoint düzenleme aracı
│   ├── dataset_temizleyici.py        ← Veri seti temizleme aracı
│   │
│   ├── main_kuyruk_odakli.lua        ← Kuyruk odaklı çekim modu (Lua)
│   ├── main_manual.lua               ← Manuel çekim modu (Lua)
│   ├── main_flight.lua               ← Klavye ile uçuş kontrol (Lua)
│   │
│   ├── AUTO_EXPORT_BBOX.bat          ← Otomatik bbox export çalıştırıcı
│   ├── DRAW_PREVIEWS.bat             ← Keypoint önizleme çizici çalıştırıcı
│   ├── EXPORT_ZIP.bat                ← YOLO dataset + ZIP hazırlayıcı
│   ├── KEYPOINT_EDITOR.bat           ← Keypoint editör çalıştırıcı
│   │
│   └── flight_log\                   ← Uçuş kayıtları (JSON log dosyaları)
│
└── Bbox\                             ← BOUNDING BOX TEST KLASÖRü
    ├── bbox_test.py                  ← Bbox hesaplama ve çizim test scripti
    └── result.png                    ← Test sonucu görseli
```

---

## 🏗️ MİMARİ: Sistem Nasıl Çalışıyor?

Sistem **iki katmanlı (two-layer)** bir mimariye sahiptir:

```
┌─────────────────────────────────────────────────────────┐
│                    KATMAN 1: LUA                         │
│              (Oyun Motorunun İÇİNDE çalışır)             │
│                                                          │
│  Unreal Engine 5 ──► UE4SS Mod Framework ──► main.lua    │
│                                                          │
│  Görevleri:                                              │
│  • Talon drone'u bul ve dondur                           │
│  • Kamerayı çeşitli açılara konumlandır                  │
│  • 3D kemik/bileşen koordinatlarını çıkar                │
│  • ProjectWorldLocationToScreen ile 2D'ye projekte et    │
│  • JSON verisini status.txt'ye yaz                       │
│  • Python'un "DONE" sinyalini bekle                      │
└──────────────────────┬──────────────────────────────────┘
                       │
                  status.txt  (JSON haberleşme köprüsü)
                       │
┌──────────────────────▼──────────────────────────────────┐
│                    KATMAN 2: PYTHON                       │
│            (Windows masaüstünde bağımsız çalışır)         │
│                                                          │
│  capture_controller_yeni.py                               │
│                                                          │
│  Görevleri:                                              │
│  • status.txt'yi sürekli oku                             │
│  • "READY" geldiğinde ekran görüntüsü yakala (mss)      │
│  • Görüntüyü 1920×1080'e ölçekle                        │
│  • Keypoint koordinatlarını yeni çözünürlüğe ölçekle     │
│  • Ham görüntüyü dataset/'e kaydet                       │
│  • Açıklamalı görüntüyü dataset_annotated/'e kaydet      │
│  • JSON metadata'yı dataset/'e kaydet                    │
│  • status.txt'ye "DONE_X" yaz (Lua'ya sinyal)            │
└─────────────────────────────────────────────────────────┘
```

### Neden İki Katman?

1. **Lua (UE4SS)** oyun motorunun içinde çalışır çünkü 3D dünya koordinatlarına, kemik pozisyonlarına ve `ProjectWorldLocationToScreen` gibi motor fonksiyonlarına **sadece oyun motorunun içinden** erişilebilir. Dışarıdan bir program bu bilgileri alamaz.

2. **Python** dışarıda çalışır çünkü ekran görüntüsü yakalama (`mss`), görüntü işleme (`PIL`), dosya yönetimi ve YOLO etiket üretimi gibi işlemler Python'un güçlü kütüphaneleriyle çok daha kolay ve güvenilir yapılır.

3. **status.txt** bu iki dünyayı birbirine bağlayan **köprü dosyasıdır**. Lua yazar → Python okur → Python "DONE" yazar → Lua okur. Bu senkronizasyon sayesinde her fotoğraf doğru zamanda, doğru veriyle eşleştirilir.

---

## 🎮 Oyun ve Araçlar

| Bileşen | Detay |
|---------|-------|
| **Oyun** | Drones of War (Unreal Engine 5 tabanlı) |
| **Modding Framework** | UE4SS (Unreal Engine 4/5 Scripting System) |
| **Hedef Drone** | TALON İHA (oyun içi actor adı: `BP_Talon_C`) |
| **Kamera Drone** | Avcı İHA (oyun içi actor adı: `BP_Avci_C`) |
| **Kamera FOV** | 125.0° (geniş açı) |
| **Çıkış Çözünürlüğü** | 1920 × 1080 piksel |

### Oyun İçi Aktörler

```
BP_Talon_C  → Hedef drone (veri setinde tespit edilecek olan)
BP_Avci_C   → Avcı drone (kamerasını kullanıyoruz)
```

Lua scripti `FindAllOf("BP_Talon_C")` ve `FindAllOf("BP_Avci_C")` komutlarıyla bu aktörleri oyun dünyasında bulur.

---

## 📍 6 KEYPOINT SİSTEMİ

Drone üzerinde **6 adet kilit nokta** (keypoint) tanımlıdır. Bunlar drone'un 3D modelindeki fiziksel konumlara karşılık gelir:

```
                    ╭─── nose (burun) ───╮
                   ╱                      ╲
        left_wing ●━━━━━━━━━━━━━━━━━━━━━━━● right_wing
        (sol kanat)    ╲            ╱       (sağ kanat)
                        ╲          ╱
                    left_fin ●  ● right_fin
                    (sol fin)    (sağ fin)
                         ╲      ╱
                          ╲    ╱
                        ●  tail  ●
                        (kuyruk)
```

| # | Keypoint Adı | Türkçe | Açıklama |
|---|-------------|--------|----------|
| 1 | `nose` | Burun | Gövdenin en ön ucu |
| 2 | `tail` | Kuyruk | Gövdenin en arka ucu |
| 3 | `left_wing` | Sol Kanat | Sol kanat ucu |
| 4 | `right_wing` | Sağ Kanat | Sağ kanat ucu |
| 5 | `left_fin` | Sol Fin | Sol dikey kuyruk stabilizörü |
| 6 | `right_fin` | Sağ Fin | Sağ dikey kuyruk stabilizörü |

### Keypoint'ler Nasıl Hesaplanıyor?

**Adım 1 — 3D Koordinat Çıkarma (Lua tarafında):**

Lua scripti drone'un merkezini (`GetActorLocation()`) ve rotasyonunu (`GetActorRotation()`) alır. Sonra her keypoint için kalibrasyon ofsetleri uygulayarak 3D dünya koordinatlarını hesaplar:

```lua
-- Örnek: Burun (nose) hesabı
local droneCenter = talonActor:K2_GetActorLocation()
local droneRot = talonActor:K2_GetActorRotation()
local forwardVector = GetForwardVector(droneRot)  -- İleri yön vektörü

-- Burun = Merkez + (İleri Yön × Burun Uzunluğu)
nose_3d = droneCenter + forwardVector * NOSE_OFFSET
```

Aynı mantıkla:
- `tail` = merkez + geri yön × kuyruk ofseti
- `left_wing` = merkez + sol yön × kanat ofseti
- `right_wing` = merkez + sağ yön × kanat ofseti
- `left_fin` = merkez + geri yön + sol yön + yukarı yön × fin ofsetleri
- `right_fin` = merkez + geri yön + sağ yön + yukarı yön × fin ofsetleri

**Adım 2 — 2D Ekran Projeksiyonu (Lua tarafında):**

Unreal Engine'in kendi `ProjectWorldLocationToScreen()` fonksiyonu kullanılır. Bu fonksiyon 3D dünya koordinatını alıp kamera perspektifine göre 2D ekran piksel koordinatına dönüştürür:

```lua
local PC = GetPlayerController()
local success, screenX, screenY = PC:ProjectWorldLocationToScreen(nose_3d)
```

Bu fonksiyon aynı zamanda noktanın kameranın **önünde** mi **arkasında** mı olduğunu döndürür. Kameranın arkasındaki noktalar `on = false` olarak işaretlenir.

**Adım 3 — Ölçekleme (Python tarafında):**

Ekran görüntüsü yakalandığında, gerçek pencere çözünürlüğü 1920x1080'den farklı olabilir (örneğin 2560x1440 monitörde). Python bu farkı telafi eder:

```python
scale_x = 1920.0 / float(orig_w)  # Yatay ölçek faktörü
scale_y = 1080.0 / float(orig_h)  # Dikey ölçek faktörü

# Her keypoint'in koordinatları ölçeklenir
pt["x"] = pt["x"] * scale_x
pt["y"] = pt["y"] * scale_y
```

Bu sayede son kaydedilen JSON'daki keypoint koordinatları **her zaman 1920x1080** çözünürlüğe göre doğrudur.

---

## 📋 JSON VERİ FORMATI

Her `talon_XXXX.json` dosyası aşağıdaki yapıdadır:

```json
{
    "drone_location": {
        "X": -54178.24,
        "Y": -87631.58,
        "Z": 11461.18
    },
    "drone_rotation": {
        "Pitch": -2.69,
        "Yaw": -109.45,
        "Roll": -0.78
    },
    "camera_location": {
        "X": -53876.73,
        "Y": -87258.25,
        "Z": 11102.12
    },
    "camera_rotation": {
        "Pitch": 22.79,
        "Yaw": -146.24,
        "Roll": 7.99
    },
    "camera_fov": 125.0,
    "keypoints_3d": {
        "nose":       {"X": -54298.03, "Y": -87637.66, "Z": 11489.77},
        "tail":       {"X": -54085.27, "Y": -87627.34, "Z": 11440.00},
        "left_wing":  {"X": -54188.36, "Y": -87531.85, "Z": 11454.60},
        "right_wing": {"X": -54168.14, "Y": -87731.35, "Z": 11467.76},
        "left_fin":   {"X": -54099.58, "Y": -87590.54, "Z": 11465.35},
        "right_fin":  {"X": -54096.48, "Y": -87665.50, "Z": 11459.54}
    },
    "keypoints_2d": {
        "nose":       {"x": 610.28, "y": 243.57, "on": true},
        "tail":       {"x": 822.58, "y": 411.07, "on": true},
        "left_wing":  {"x": 756.19, "y": 337.61, "on": true},
        "right_wing": {"x": 667.00, "y": 307.48, "on": true},
        "left_fin":   {"x": 806.91, "y": 358.71, "on": true},
        "right_fin":  {"x": 788.65, "y": 368.42, "on": true}
    },
    "view": "FL"
}
```

### Her Alanın Açıklaması:

| Alan | Tip | Açıklama |
|------|-----|----------|
| `drone_location` | {X, Y, Z} | Drone'un Unreal Engine dünya koordinatları (santimetre cinsinden) |
| `drone_rotation` | {Pitch, Yaw, Roll} | Drone'un rotasyonu (derece cinsinden) |
| `camera_location` | {X, Y, Z} | Kameranın dünya koordinatları |
| `camera_rotation` | {Pitch, Yaw, Roll} | Kameranın rotasyonu |
| `camera_fov` | float | Kamera görüş açısı (Field of View) — sabit 125.0° |
| `keypoints_3d` | dict | 6 keypoint'in 3D dünya koordinatları (Unreal cm) |
| `keypoints_2d` | dict | 6 keypoint'in 2D ekran koordinatları (1920x1080 piksele göre) |
| `keypoints_2d.*.on` | bool | `true` = keypoint ekranda görünür, `false` = kamera arkasında veya dışında |
| `view` | string | Çekim açısı: `"FL"` (Ön-Sol), `"FR"` (Ön-Sağ), `"RL"` (Arka-Sol), `"RR"` (Arka-Sağ) |

---

## ⚙️ main.lua — ANA LUA SCRİPTİ (Detaylı Açıklama)

### Sabitler ve Konfigürasyon

```lua
local CAPTURES_PER_SPOT = 4       -- Her noktada 4 fotoğraf çekilir (FL, FR, RL, RR)
local FLY_TICKS = 10              -- Drone 10 tick boyunca uçar (10 x 250ms = 2.5 saniye)
local MIN_DIST = 200              -- Minimum mesafe: 2 metre
local MAX_DIST = 4000             -- Maksimum mesafe: 40 metre
local TICK_INTERVAL_MS = 250      -- State machine her 250ms'de bir çalışır (saniyede 4 kez)
local STATUS_FILE_PATH = "c:\\Users\\Zeylo\\Desktop\\talon_dataset\\status.txt"
```

> **ÖNEMLİ NOT:** `GenerateDiverseCombo()` fonksiyonundaki mesafe şu anda `math.random(500, 1200)` olarak ayarlıdır — yani **5 metre ile 12 metre** arası. Bu değer daha önce 500-4000 (5m-40m) idi ve kullanıcı isteğiyle daraltıldı.

### Benzerlik Kontrolü (Diversity Check)

Sistem her yeni kamera pozisyonunu son **1000 poz**la karşılaştırır. Eğer yeni poz, öncekilerden birine çok benziyorsa reddedilir ve yeni bir poz denenir:

```lua
function IsSimilar(p1, p2)
    -- Mesafe farkı < 100cm (1 metre) ise benzer
    -- Kamera yaw farkı < 15° ise benzer
    -- Kamera pitch farkı < 10° ise benzer
    -- Drone yaw farkı < 30° ise benzer
    -- TÜM koşullar sağlanırsa "Çok benzer, reddet!"
end
```

Bu mekanizma sayesinde veri setinde **binlerce birbirinden farklı açı** elde edilir.

### State Machine (Durum Makinesi)

Scriptin kalbi bir durum makinesidir. Her 250ms'de bir çalışır ve şu akışı takip eder:

```
INIT
  │
  ▼
FIND_ACTORS ──── Talon ve Avci drone'ları bul
  │
  ▼
FREEZE ───────── Oyunu duraklat, drone'u dondur, UI'ı gizle
  │
  ▼
SETUP_COMBO ──── Yeni kamera pozisyonu oluştur (veya alt-görüşe geç)
  │
  ▼
POSITION_CAMERA ─ Kamerayı hesaplanan konuma taşı
  │
  ▼
WAIT_RENDER ──── 2-3 tick bekle (Unreal Engine yeni kareyi çizsin)
  │
  ▼
WRITE_STATUS ─── JSON verisini status.txt'ye yaz
  │
  ▼
WAIT_CAPTURE ─── Python'un "DONE_X" yazmasını bekle
  │
  ▼
CHECK_DONE
  │
  ├── viewIndex < 4 → Bir sonraki alt-görüşe geç → POSITION_CAMERA
  │
  └── viewIndex = 4 → Tüm görüşler tamam → FLY
                                                │
                                                ▼
                                         FLY ── Drone 2.5 sn uçsun
                                                │
                                                ▼
                                           FREEZE (tekrar)
```

### 4 Alt-Görüş Sistemi

Her noktada drone dondurulur ve **4 farklı açıdan** fotoğraf çekilir:

| # | Görüş Kodu | Açıklama | Yaw Ofseti |
|---|-----------|----------|------------|
| 1 | FL | Front-Left (Ön Sol) | Temel açı |
| 2 | FR | Front-Right (Ön Sağ) | +30° |
| 3 | RL | Rear-Left (Arka Sol) | +180° |
| 4 | RR | Rear-Right (Arka Sağ) | +210° |

### Kamera Konumlandırma

Kamera küresel koordinat sistemi ile konumlandırılır:

```lua
-- Arka yarı küre: Yaw 90° ile 270° arası (drone'un arkasından)
-- Pitch: -70° (alttan) ile +10° (hafif üstten) arası
-- Mesafe: 500-1200 cm (5m-12m)
-- Roll: -30° ile +30° arası (kamera yatması)

cam_x = drone_x + dist * cos(pitch) * cos(yaw)
cam_y = drone_y + dist * cos(pitch) * sin(yaw)
cam_z = drone_z + dist * sin(pitch)
```

### Drone Dondurma/Çözme

```lua
-- DONDURMA (FREEZE state):
talonActor.CustomTimeDilation = 0     -- Zaman akışını durdur
SetGamePaused(true)                   -- Oyunu duraklat

-- ÇÖZME (FLY state):
talonActor.CustomTimeDilation = 1.0   -- Zaman akışını normal yap
SetGamePaused(false)                  -- Oyunu devam ettir
```

Bu sayede fotoğraf çekilirken drone **kesinlikle hareket etmez**, bulanıklık olmaz, keypoint'ler yüzde yüz doğru pozisyonda kalır.

---

## 🐍 capture_controller_yeni.py — PYTHON YAKALAMA KONTROLCÜSÜ

### DPI Farkındalığı (Kritik!)

```python
ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-Monitor DPI Aware V2
```

> **NEDEN?** Eğer bu satır olmazsa, yüksek DPI ekranlarda (örn. 4K monitör) Windows, pencere koordinatları hakkında **yalan söyler**. Ekran görüntüleri yanlış yerden kesilir ve keypoint'ler kayar. Bu satır Windows'a "Bana gerçek pikselleri ver, ölçekleme yapma" der.

### Oyun Penceresini Bulma

```python
def find_game_window():
    # Tüm açık pencereleri tara
    # ClassName == "UnrealWindow" olan pencereyi bul
    # Bu, Unreal Engine oyunlarının kullandığı standart pencere sınıfıdır
```

Bu yüzden script **oyunun adını bile bilmek zorunda değildir** — sadece Unreal Engine penceresi olduğunu anlar.

### Ekran Görüntüsü Yakalama

```python
with mss.mss() as sct:
    monitor = {
        "top": top,          # Pencerenin üst kenarı
        "left": left,        # Pencerenin sol kenarı
        "width": right - left,
        "height": bottom - top
    }
    sct_img = sct.grab(monitor)  # Sadece oyun penceresini yakala
    img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
```

**Neden `mss`?** `mss` kütüphanesi, Python'daki en hızlı ekran yakalama yöntemidir. Alternatif olan `PIL.ImageGrab` çok yavaştır. `mss` doğrudan Windows GDI API'sini kullanarak milisaniyeler içinde ekran görüntüsü alır.

### Ölçekleme Sistemi

```python
# Orijinal çözünürlüğü al
orig_w, orig_h = sct_img.size  # Örn: 2560x1440

# 1920x1080'e yeniden boyutlandır
img = img.resize((1920, 1080), Image.Resampling.LANCZOS)

# Keypoint koordinatlarını da ölçekle
scale_x = 1920.0 / float(orig_w)  # Örn: 1920/2560 = 0.75
scale_y = 1080.0 / float(orig_h)  # Örn: 1080/1440 = 0.75

for name, pt in keypoints_2d.items():
    pt["x"] = pt["x"] * scale_x
    pt["y"] = pt["y"] * scale_y
```

### Otomatik İndeks Devam Sistemi

```python
pattern = re.compile(r"^talon_(\d+)")
for filename in os.listdir(dataset_dir):
    match = pattern.match(filename)
    if match:
        idx = int(match.group(1))
        if idx > offset: offset = idx
```

Eğer `dataset/` klasöründe zaten `talon_0001` ile `talon_0500` arası varsa, yeni çekimler otomatik olarak `talon_0501`'den devam eder. **Sistemi durdurur, oyunu kapatır, sonra tekrar açarsan kaldığı yerden devam eder.**

### Ham vs Açıklamalı Kayıt

```python
# HAM GÖRÜNTÜ — Hiçbir çizim yok, temiz
img.save(os.path.join(dataset_dir, filename), "PNG")

# AÇIKLAMALI GÖRÜNTÜ — Keypoint noktaları çizilmiş (kırmızı + beyaz)
annotated_img = img.copy()
draw = ImageDraw.Draw(annotated_img)
for name, pt in keypoints_2d.items():
    if pt.get("on", False):  # Sadece görünür keypoint'leri çiz
        px, py = pt["x"], pt["y"]
        r = 2  # 2 piksel yarıçap
        draw.ellipse((px-r, py-r, px+r, py+r), fill="red", outline="white")
annotated_img.save(os.path.join(dataset_annotated_dir, filename), "PNG")
```

---

## 📦 BOUNDING BOX (BBOX) SİSTEMİ

### Bbox Nasıl Hesaplanıyor?

Bounding box, 6 keypoint'in koordinatları kullanılarak hesaplanır:

```python
def calculate_bbox(keypoints_2d, img_w=1920, img_h=1080, padding_ratio=0.20):
    """
    Görünür (on=true) keypoint'lerin min/max koordinatlarından bbox hesapla.
    """
    visible_points = []
    for name, pt in keypoints_2d.items():
        if pt.get("on", False):
            visible_points.append((pt["x"], pt["y"]))
    
    if not visible_points:
        return None  # Hiçbir nokta görünür değil
    
    # En uç değerleri bul
    x_coords = [p[0] for p in visible_points]
    y_coords = [p[1] for p in visible_points]
    
    x_min = min(x_coords)
    y_min = min(y_coords)
    x_max = max(x_coords)
    y_max = max(y_coords)
    
    # Kutu genişliği ve yüksekliği
    w = x_max - x_min
    h = y_max - y_min
    
    # %20 padding (nefes payı) ekle
    pad_x = w * padding_ratio
    pad_y = h * padding_ratio
    
    x_min = max(0, x_min - pad_x)
    y_min = max(0, y_min - pad_y)
    x_max = min(img_w, x_max + pad_x)
    y_max = min(img_h, y_max + pad_y)
    
    return x_min, y_min, x_max, y_max
```

### YOLO Formatına Dönüştürme

YOLO format: `class_id center_x center_y width height` (tümü 0-1 arası normalize edilmiş)

```python
# Bbox koordinatlarından YOLO formatına çevir
cx = ((x_min + x_max) / 2.0) / img_w   # Merkez X (normalize)
cy = ((y_min + y_max) / 2.0) / img_h   # Merkez Y (normalize)
bw = (x_max - x_min) / img_w            # Genişlik (normalize)
bh = (y_max - y_min) / img_h            # Yükseklik (normalize)

# YOLO etiket satırı:
# 0 0.543210 0.321456 0.187654 0.234567
label_line = f"0 {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}"
```

### Keypoint'li YOLO Formatı (Pose Modeli İçin)

```
0 cx cy w h x1 y1 v1 x2 y2 v2 x3 y3 v3 x4 y4 v4 x5 y5 v5 x6 y6 v6
```

- `0` = sınıf ID'si (talon)
- `cx cy w h` = bounding box (normalize)
- `x1 y1 v1` = nose keypoint (normalize x, normalize y, görünürlük)
- `x2 y2 v2` = tail keypoint
- ... (toplam 6 keypoint x 3 değer = 18 ek değer)
- `v` = `2` (görünür) veya `0` (görünmez)

---

## 🔧 KURULUM — SIFIRDAN ADIM ADIM

### Gereksinimler

| Gereksinim | Açıklama |
|-----------|----------|
| **Windows 10/11** | Zorunlu (Win32 API kullanılıyor) |
| **Python 3.8+** | Python 3.10+ önerilir |
| **Drones of War** | Unreal Engine 5 tabanlı oyun |
| **UE4SS** | Unreal Engine modding framework (Lua scriptlerini çalıştırmak için) |

### Adım 1: Python Kurulumu

```cmd
python --version
:: Python 3.10+ olduğundan emin ol
```

### Adım 2: Python Kütüphaneleri

Script ilk çalıştırıldığında eksik kütüphaneleri otomatik yükler, ama önceden kurmak istersen:

```cmd
pip install Pillow mss keyboard opencv-python numpy PyQt5
```

| Kütüphane | Ne İçin Kullanılıyor |
|-----------|---------------------|
| `Pillow` (PIL) | Görüntü işleme, keypoint çizme, resize |
| `mss` | Hızlı ekran görüntüsü yakalama |
| `keyboard` | Klavye kısayolları (F9 manual shot) |
| `opencv-python` | Bbox çizim ve görüntü işleme araçları |
| `numpy` | Sayısal hesaplamalar |
| `PyQt5` | GUI editörleri (keypoint editor, bbox editor) |

### Adım 3: UE4SS Kurulumu

1. UE4SS'i indir (GitHub'dan): `https://github.com/UE4SS-RE/RE-UE4SS`
2. UE4SS dosyalarını oyunun `.exe` dosyasının yanına kopyala
3. `main.lua` dosyasını UE4SS'in `Mods/` klasörüne koy
4. Oyunu başlat — UE4SS otomatik olarak `main.lua`'yı çalıştıracak

### Adım 4: Klasör Yapısını Oluştur

```cmd
mkdir C:\Users\Zeylo\Desktop\Berat\talon_dataset
mkdir C:\Users\Zeylo\Desktop\Berat\talon_dataset\dataset
mkdir C:\Users\Zeylo\Desktop\Berat\talon_dataset\dataset_annotated
mkdir C:\Users\Zeylo\Desktop\Berat\Bbox
```

### Adım 5: Path'leri Güncelle

Aşağıdaki dosyalarda path'leri kendi bilgisayarına göre güncelle:

**`main.lua` içinde:**
```lua
local STATUS_FILE_PATH = "c:\\Users\\Zeylo\\Desktop\\Berat\\talon_dataset\\status.txt"
```

**`capture_controller_yeni.py` içinde:**
```python
workspace_dir = r"c:\Users\Zeylo\Desktop\Berat\talon_dataset"
```

---

## ▶️ ÇALIŞTIRMA — ADIM ADIM

### 1. Oyunu Başlat
Drones of War'u aç. UE4SS otomatik olarak `main.lua`'yı yükleyecek.

### 2. Python Script'i Başlat
**Yeni bir terminal (CMD veya PowerShell) aç** ve şunu çalıştır:

```cmd
cd C:\Users\Zeylo\Desktop\Berat\talon_dataset
python capture_controller_yeni.py
```

Terminal çıktısı:
```
[INFO] Created dataset directory: ...\dataset
[INFO] Searching for Drones of War (UnrealWindow)...
[INFO] Found window: 'Drones of War' (HWND: 12345678)
[INFO] Minimizing terminal window to prevent overlapping...
[INFO] Starting AUTOMATIC 4-Way Capture Loop! Waiting for Lua script...
[INFO] Press CTRL+C in this terminal to stop.
[INFO] Detected highest existing index in dataset: 0.
[CAPTURE] Processing frame 1 (View FL)... Saved: talon_0001 (Raw & Annotated)
[CAPTURE] Processing frame 2 (View FR)... Saved: talon_0002 (Raw & Annotated)
...
```

### 3. Sistem Otomatik Çalışır
Artık müdahale etmene gerek yok. Sistem:
1. Lua drone'u dondurur, kamerayı konumlandırır, JSON yazar
2. Python JSON'u okur, ekran yakalar, kaydeder, "DONE" yazar
3. Lua "DONE"u okur, bir sonraki açıya/noktaya geçer
4. Bu döngü otomatik olarak **4000 çekim**e kadar devam eder

### 4. Durdurmak İçin
Terminal penceresinde `CTRL+C` bas.

---

## 📊 VERİ SETİNİ DOĞRULAMA (TEYİT ETME)

### Yöntem 1: Açıklamalı Görüntüleri Kontrol Et
`dataset_annotated/` klasörünü aç. Her görselde drone'un üzerinde **kırmızı noktalar** görmelisin. Bu noktalar 6 keypoint'in doğru yerde olduğunu gösterir.

### Yöntem 2: DRAW_PREVIEWS.bat Çalıştır
```cmd
DRAW_PREVIEWS.bat
```
Bu script tüm `dataset/` klasörünü tarar, her PNG+JSON çifti için keypoint'leri görüntü üzerine çizer ve `dataset_annotated/`'e kaydeder.

### Yöntem 3: Keypoint Editör ile Görsel Kontrol
```cmd
KEYPOINT_EDITOR.bat
```
PyQt5 tabanlı GUI açılır. Her görüntüyü teker teker inceleyebilir, keypoint'leri sürükleyerek düzeltebilir, zoom yapabilirsin.

### Yöntem 4: JSON Dosyasını Manuel Kontrol Et
Herhangi bir `talon_XXXX.json` dosyasını Not Defteri ile aç:
- `keypoints_2d` altında her noktanın `"on": true` olduğunu kontrol et
- `x` ve `y` değerlerinin 0-1920 ve 0-1080 arasında olduğunu doğrula
- İlgili PNG'yi aç ve koordinatların drone'un üzerinde düştüğünü gözle kontrol et

### Yöntem 5: Dataset Temizleyici
```cmd
python dataset_temizleyici.py
```
- Yetim dosyaları bulur (JSON'suz PNG veya PNG'siz JSON)
- Bozuk görüntüleri tespit eder
- JSON yapısını doğrular
- İstatistik raporu verir

---

## 📤 YOLO EXPORT İŞLEMİ

### Sadece Bounding Box Export
```cmd
AUTO_EXPORT_BBOX.bat
```
veya
```cmd
python auto_export_bbox.py
```

**Çıktı:** `dataset_auto_bbox/` klasörüne YOLO formatında `.txt` etiket dosyaları oluşturur.

### Tam YOLO Dataset + ZIP Export
```cmd
EXPORT_ZIP.bat
```
veya
```cmd
python prepare_yolo_dataset.py
```

**Ne yapar:**
1. `dataset/` klasöründeki tüm PNG+JSON çiftlerini okur
2. Her biri için YOLO keypoint etiketi oluşturur
3. %80 eğitim / %20 doğrulama olarak böler
4. Aşağıdaki yapıyı oluşturur:

```
yolo_dataset/
├── images/
│   ├── train/    ← Eğitim görselleri (%80)
│   └── val/      ← Doğrulama görselleri (%20)
├── labels/
│   ├── train/    ← Eğitim etiketleri
│   └── val/      ← Doğrulama etiketleri
└── data.yaml     ← YOLO konfigürasyonu
```

**data.yaml içeriği:**
```yaml
train: images/train
val: images/val
nc: 1                    # Sınıf sayısı (sadece 'talon')
names: ['talon']         # Sınıf adı
kpt_shape: [6, 3]        # 6 keypoint, her biri 3 değer (x, y, visibility)
```

5. Her şeyi `yolo_dataset.zip` olarak paketler (Google Colab'a yüklemek için hazır)

---

## 🎮 FARKLI ÇEKİM MODLARI

| Özellik | main.lua | main_kuyruk_odakli.lua | main_manual.lua | main_flight.lua |
|---------|----------|----------------------|-----------------|-----------------|
| **Mod** | Tam Otomatik | Otomatik (Kuyruk Odaklı) | Manuel Çekim | Manuel Uçuş |
| **Tick Hızı** | 250ms (4 Hz) | 250ms (4 Hz) | 100ms (10 Hz) | 33ms (~30 Hz) |
| **Görüş/Nokta** | 4 (FL,FR,RL,RR) | 2 | 1 (manuel) | Yok |
| **Mesafe** | 500-1200 cm | 1500-2200 cm | Kullanıcı kontrollü | Kullanıcı kontrollü |
| **Kamera Açıları** | Otomatik (arka yarı küre) | Otomatik (kuyruk odaklı) | Manuel | Manuel |
| **Benzerlik Kontrolü** | Evet (son 1000) | Temel | Hayır | Hayır |
| **Oyun Duraklatma** | Evet | Evet | Hayır | Hayır |

---

## 🎛️ FPS AYARLAMA

Oyunun FPS'ini (kare hızını) değiştirmek için:

**Dosya:** `C:\Users\<KULLANICI>\AppData\Local\DronesOfWar\Saved\Config\Windows\GameUserSettings.ini`

```ini
[/Script/Engine.GameUserSettings]
bUseVSync=False
FrameRateLimit=30.000000    ← Bu değeri değiştir (0 = sınırsız, 30 = 30 FPS)
```

**Adımlar:**
1. `Win+R` bas, `%LOCALAPPDATA%\DronesOfWar\Saved\Config\Windows` yaz, Enter
2. `GameUserSettings.ini` dosyasını Not Defteri ile aç
3. `FrameRateLimit=` satırını bul ve istediğin değeri yaz
4. Kaydet ve oyunu yeniden başlat
5. `Win+G` (Xbox Game Bar) ile FPS'i doğrula

---

## 🧩 BBOX TEST KLASÖRü

`C:\Users\Zeylo\Desktop\Berat\Bbox\` klasöründe bounding box hesaplama ve çizim mantığını test eden bir script bulunur:

**`bbox_test.py`** — 6 keypoint'ten bbox hesaplayıp çizen bağımsız test scripti:

```cmd
cd C:\Users\Zeylo\Desktop\Berat\Bbox
python bbox_test.py
:: Sonuç: result.png dosyası oluşur
```

---

## 🔑 KRİTİK BİLGİLER VE İPUÇLARI

### Sık Yapılan Hatalar

| Hata | Çözüm |
|------|-------|
| Keypoint'ler kayık görünüyor | DPI ayarını kontrol et, çözünürlük ölçeklemesini doğrula |
| status.txt boş kalıyor | UE4SS'in main.lua'yı yüklediğinden emin ol |
| Siyah ekran görüntüsü | Terminal penceresi oyunun üzerini kapatmış olabilir |
| JSON parse hatası | Lua ve Python aynı anda status.txt'ye yazmaya çalışıyor, bekleme süresini artır |
| 4000'den sonra durdu | `capture_controller_yeni.py`'deki `offset >= 4000` limitini artır |

### Performans Önerileri

- **FPS 30'a sabitle** — GPU'yu rahatlatır, veri toplama kalitesini artırır
- **Oyun ayarlarını düşür** — `GameUserSettings.ini`'de `sg.ShadowQuality=0` vb. zaten en düşükte
- **Terminal penceresini küçült** — Script bunu otomatik yapıyor ama emin ol

### Güvenlik

- `status.txt` üzerinden haberleşme senkron değildir — hem Lua hem Python aynı anda yazabilir. Bu yüzden `try/except` ve `time.sleep()` ile korunma sağlanmıştır.
- Script `keyboard` modülünü kullanır; bu modül yönetici hakları gerektirebilir.

---

## 📝 ÖZET: Veri Toplama Akışı (Baştan Sona)

```
1.  Oyunu başlat → UE4SS main.lua'yı yükler
2.  Python capture_controller_yeni.py'yi başlat
3.  Lua: Talon drone'u bulur → dondurur → kamerayı konumlandırır
4.  Lua: 6 keypoint'in 3D koordinatlarını çıkarır
5.  Lua: ProjectWorldLocationToScreen ile 2D'ye projekte eder
6.  Lua: Tüm veriyi JSON olarak status.txt'ye yazar (status: "READY")
7.  Python: status.txt'yi okur → "READY" görür
8.  Python: mss ile ekran görüntüsü yakalar
9.  Python: 1920x1080'e resize eder, keypoint'leri ölçekler
10. Python: Ham görüntüyü dataset/talon_XXXX.png'ye kaydeder
11. Python: Keypoint'leri çizdiği kopyayı dataset_annotated/'e kaydeder
12. Python: Metadata'yı dataset/talon_XXXX.json'a kaydeder
13. Python: status.txt'ye "DONE_X" yazar
14. Lua: "DONE_X"i okur → bir sonraki açıya/noktaya geçer
15. 4 açı tamamlanınca → drone uçar → yeni nokta → 1'e dön
16. Bu döngü 4000 çekim tamamlanana kadar otomatik devam eder

Sonra:
17. auto_export_bbox.py ile YOLO bbox etiketleri üretilir
18. prepare_yolo_dataset.py ile train/val split yapılır ve ZIP'lenir
19. ZIP Google Colab'a yüklenir ve YOLOv8 ile eğitilir
```

---

> **Son Not:** Bu sistem tamamen otomatiktir. Bir kere kurulumu yapıp başlattıktan sonra bilgisayarın başında oturmana gerek yoktur. Sistem kendi kendine çeşitli açılardan binlerce fotoğraf çeker, keypoint'leri doğru şekilde kaydeder ve model eğitimi için hazır bir veri seti oluşturur. Mesafe, açı, benzerlik kontrolü ve FPS gibi tüm parametreler tamamen özelleştirilebilir.

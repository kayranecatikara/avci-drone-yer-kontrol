# 🛸 Avcı Drone — Yer Kontrol İstasyonu & GPS Filtre Test Sistemi

TEKNOFEST "Drones of War" avcı drone projesi için geliştirilen sistem.
Oyundan telemetri okur, **bozuk hedef GPS'ini filtreler**, drone'u otonom yönetir
ve **farklı GPS filtrelerini adil şekilde yarıştırır**. Tarayıcı tabanlı bir
kontrol arayüzü içerir.

> **Bu repo ne işine yarar?** Kendi GPS filtreleme algoritmanı yazıp, hazır
> sisteme takıp, oyunun **gerçek** hedef konumuna göre kaç metre hata yaptığını
> ölçebilirsin. Mevcut iki filtre (Efe & Ömer) ile **yan yana** karşılaştırırsın.

---

## 📦 Gereksinimler
- **Python 3.10+** (Windows)
- **Drones of War** oyunu (TEKNOFEST yarışma paketi — repoya dahil değildir)
- `drone_sdk.py` (yarışma paketinden gelir; repoda mevcut)
- Birkaç Python paketi (`requirements.txt`)

---

## ⚙️ Kurulum (tek seferlik)
1. Bu repoyu indir veya klonla:
   ```
   git clone <repo-url>
   cd "Yarismaci Dokuman"
   ```
2. Gerekli paketleri kur:
   ```
   pip install -r requirements.txt
   ```
3. **Oyunu** bu klasörün içine koy: `Drones of War Teknofest/DronesOfWar.exe`
   (oyun repoya dahil değildir, yarışma paketinden gelir).

---

## ▶️ Çalıştırma
1. **Oyunu aç** → `1_Oyunu_Baslat.bat` (veya elle `DronesOfWar.exe`) → **PLAY**'e bas.
2. **Arayüzü aç** → `2_Arayuzu_Baslat.bat` (veya elle `python server.py`).
3. Tarayıcıda otomatik açılır: **http://127.0.0.1:8000**
4. Orta paneldeki **"📡 Görüntüyü Bağla"** → açılan listeden **oyun penceresini** seç
   (canlı görüntü için; ekran paylaşımı yöntemi).

> ⚠️ Aynı anda **tek bir** `server.py` çalışsın. İkinci bir tane açma (oyun tek
> bağlantı kabul ediyor, çakışır). Yeniden başlatırken önce eski siyah pencereyi kapat.

---

## 🖥️ Arayüz
| Panel | İçerik |
|-------|--------|
| **Sol** | Görev butonları (Başlat/Durdur). "Başlat" drone'u arm edip hedefe yöneltir. |
| **Orta** | Oyun görüntüsü (ekran paylaşımı) + drone HUD. |
| **Sağ** | Telemetri (avcı + hedef), **Filtre Kıyası** (Ham · Efe · Ömer · Kazanan), mesafe. |

---

## 🧠 Sistem nasıl çalışıyor?
```
Oyun (Unreal, TCP 127.0.0.1:12345)
   │  bozuk hedef GPS (cm)
   ▼
drone_sdk.py  ──►  server.py (Python beyni)
                     ├─ GPS filtresi (bozuk hedefi temizler)
                     ├─ güdüm (ana_kontrol.py: hedefe yönelt/çarp)
                     └─ web sunucusu  ──►  index.html (tarayıcı arayüzü)
```
- **Birim:** Oyun her şeyi **santimetre** verir; arayüzde metreye çevrilir (×0.01).
- **Hedef GPS bilerek bozuktur** (gürültü, sabit kayma, sıçrama, kesinti, 1 Hz
  yavaş güncelleme, ~3 sn gecikme). Avcının kendi GPS'i temizdir.
- **`get_debug_truth()`** ile oyunun **gerçek** hedef konumu okunabilir — filtreleri
  bununla karşılaştırıp ölçeriz (sadece test/geliştirme amaçlı).

---

## 🏁 KENDİ FİLTRENİ EKLE ve TEST ET

Sisteme yeni bir GPS filtresi takmak çok kolay. İki filtre formatı destekleniyor.

### 1) Filtre sözleşmesi (en basit format — "Efe formatı")
Filtren bir **sınıf** olsun; her yeni GPS paketinde çağrılan bir `guncelle` metodu
olsun. **Giriş ve çıkış santimetre (cm)**:
```python
class BenimFiltrem:
    def guncelle(self, bozuk_x, bozuk_y, bozuk_z):
        # ... senin temizleme mantigin ...
        return (temiz_x, temiz_y, temiz_z)   # cm
        # veya isinma/donma sirasinda:  return None
```
Dosyanı projeye koy: `benim_filtrem.py`

### 2) `server.py` içinde kıyasa ekle (3 küçük yer)
`server.py` zaten Efe ve Ömer'i yarıştırıyor; aynı kalıbı izle:

**(a) Filtreyi oluştur** (kıyas bölümünde, `_kiyas_efe` yanında):
```python
from benim_filtrem import BenimFiltrem
_kiyas_benim = BenimFiltrem()
_kiyas_benim_hata = deque(maxlen=80)
```

**(b) `_kiyas_guncelle()` içinde besle** (Efe'nin yaptığı gibi):
```python
benim_out = _kiyas_benim.guncelle(hx, hy, hz)
if benim_out is not None:
    _kiyas_benim_hata.append(
        float(np.linalg.norm(np.array(benim_out, float) - gercek)))
```

**(c) `build_telemetry()` içinde rapora ekle** (`kiyas` sözlüğüne):
```python
if _kiyas_benim_hata:
    kiyas["benim_ort_m"] = sum(_kiyas_benim_hata) / len(_kiyas_benim_hata) / 100.0
```

### 3) Çalıştır ve ölç
- Oyunu aç, `server.py`'yi başlat, **~1-2 dakika** ölçüm modunda bekle
  (drone yerde, görev başlatma).
- Her paketin sonucu **`kiyas_log.csv`** dosyasına yazılır:
  `paket, ham_m, efe_m, omer_m, ...`
- CSV'yi Excel'de aç veya bir scriptle analiz et: **ortalama, medyan, en kötü
  (max), dalgalanma (std)**. Düşük hata + düşük dalgalanma = **iyi filtre**.

> 💡 **Adil karşılaştırma kuralları:** Filtreler aynı ham veriyle beslenir, aynı
> gerçek konumla karşılaştırılır. Filtren **ileri tahmin / gecikme telafisi**
> yapıyorsa, çıktının hangi zamana ait olduğuna dikkat et (gecikmeli filtreler
> kendi referans zamanlarının gerçeğiyle eşlenmeli — `omer_filtre.py` örneğine bak).

---

## 📁 Dosyalar
| Dosya | Açıklama |
|-------|----------|
| `server.py` | Python beyni: bağlantı, filtreler, güdüm, web sunucusu, kıyas. |
| `index.html` | Tarayıcı arayüzü (3 panel). |
| `drone_sdk.py` | Oyunla TCP haberleşen resmi SDK. |
| `blok_j.py` | **Efe'nin filtresi** (Kalman/EKF + gecikme telafisi). |
| `omer_filtre.py` | **Ömer'in filtresi** (switching-KF + fixed-lag smoother + Hermite). |
| `ana_kontrol.py` | Güdüm + durum makinesi (ARAMA→KİLİT) + kamera taslağı. |
| `1_Oyunu_Baslat.bat` / `2_Arayuzu_Baslat.bat` | Tek tıkla başlatıcılar. |
| `SDK_README.md` | Resmi SDK belgesi (birim, throttle modeli, bozulma türleri). |

---

## 📝 SDK kısa notları (detay: `SDK_README.md`)
- **Konum/hız: cm, cm/s.** Metre için ×0.01.
- **`set_control_surfaces(throttle, pitch, roll, yaw, arm)`** — tek satırda kontrol.
- **Throttle = dikey komut:** `+1` tırman, `0` **hover (irtifa korunur)**, `-1` serbest düş.
- **Pitch/Roll = hedef yatış açısı** (±1 ≈ 60°), Angle Mode.
- **Kontrol döngüsü ~50 Hz** (`time.sleep(0.02)`).
- Filtreni **tek okumaya güvenmeyecek** şekilde, gürültü/gecikmeye **dayanıklı** kur.

---
*TEKNOFEST Drones of War — Avcı Drone Takımı*

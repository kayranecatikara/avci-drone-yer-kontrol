# DÖNÜŞTÜRÜCÜ (KÖPRÜ) — Gazebo GPS Güdümünün Drones of War'a Taşınması

> **Tek cümlede:** Gazebo/ArduPilot'ta çalışan GPS güdüm yasamız, **tek satırı
> değiştirilmeden** Drones of War'da uçuyor. Aradaki çeviriyi bu klasördeki
> **dönüştürücü** yapıyor: `dow_kopru.py`.

---

## 1. PROBLEM

Güdüm yasası (`gps_guidance.py`) çıktı olarak **hız komutu** üretir:

```python
send_velocity(conn, vx, vy, vz, yaw)      # m/s, dünya NED + mutlak yaw (rad)
```

Gazebo'da bu komutu **ArduPilot** alıyordu ve şu zinciri kendisi yürütüyordu:

```
hız hatası → ivme → yatış açısı → itki → motorlar
```

Drones of War'da bu katman **YOK**. DoW SDK'sı yalnızca normalize açı kabul eder:

```python
set_control_surfaces(throttle, pitch, roll, yaw, arm)   # hepsi -1.0 … +1.0
```

- `pitch`, `roll` → **yatış AÇISI** (Angle mode, ±1.0 = 60°) — açısal hız değil
- `throttle` → **dikey komut**, üstelik **asimetrik** (+1 tırmanma hızı, 0 hover
  değil!, −1 yerçekimi telafisi kapalı)
- `yaw` → dönüş **hızı** (yasa ise **mutlak açı** gönderiyor)

**Dönüştürücünün görevi: ArduPilot'un yerini almak.** Yasa ne komut ederse
etsin, onu DoW'un anlayacağı stick değerlerine kapalı çevrimde çevirmek.

---

## 2. MİMARİ — ÖNCE / SONRA

**Gazebo (kaynak sistem):**
```
gps_guidance.py ──hız komutu (MAVLink)──> ArduPilot ──açı/itki──> araç
      ▲                                       │
      └──── get_plane() / get_iris() ◄────────┘  (telemetri, NED, metre)
```

**Drones of War (bu repo):**
```
gps_guidance.py ──hız komutu──> ★ dow_kopru.py ──stick──> DoW SDK ──> araç
   (DEĞİŞMEDİ)                   (DÖNÜŞTÜRÜCÜ)                          │
      ▲                                ▲                                │
      └── get_plane() / get_iris() ────┴────── telemetri (cm, z-yukarı)─┘
                  (köprünün adaptörleri çevirir)
```

Dönüştürücü **iki ucu birden** sağlar:
1. **Giriş adaptörü** — DoW telemetrisi (cm, z-yukarı, derece) → yasanın beklediği
   NED/metre/radyan sözleşmesi
2. **Çıkış köprüsü** — yasanın hız komutu → DoW stick'i (kapalı çevrim)

Bu ikisi **aynı dosyada** olmak zorunda: çıkış, girişin tam tersini kullanır.
Ayrı yazılırsa biri kaçınılmaz olarak ters olur ve hata yalnızca uçuşta çıkar.

---

## 3. DOSYA HARİTASI

### ★ DÖNÜŞTÜRÜCÜ — asıl iş

| Dosya | Satır | Görevi |
|---|---|---|
| **`dow_kopru.py`** | 643 | **DÖNÜŞTÜRÜCÜ.** Çerçeve dönüşümü, giriş adaptörleri (`get_iris`/`get_plane`), yatay/dikey/yaw kanalları, rate-limit, GNSS düzeltici bağlantısı, kalkış |
| `entegre.py` | 194 | Yasa + köprüyü tek nesnede paketler; yer kontrol istasyonuna bağlanan yüz |

### SENİN YASAN — dokunulmadı (hash birebir doğrulandı)

| Dosya | Satır | Görevi |
|---|---|---|
| `gazebo_kaynak/control/guidance/gps_guidance.py` | 522 | **Güdüm yasası.** İstasyon geometrisi + PD + hedef-hızı ileri beslemesi |
| `gazebo_kaynak/control/guidance/common.py` | 106 | Ortak yardımcılar + `send_velocity` (MAVLink gönderici) |
| `gazebo_kaynak/control/guidance/guidance_core.py` | 612 | `hedef_kadraj_hatasi` — kadraj ÖLÇÜMÜ (komuta girmez) |
| `gazebo_kaynak/control/guidance/hedef_kestirim.py` | 250 | IMM (CV+CA) — **kullanılmıyor** |
| `gazebo_kaynak/vision/geometry.py` | 325 | Kamera izdüşümü (guidance_core'un bağımlılığı) |

### ÖLÇÜM VE KOŞU ARAÇLARI

| Dosya | Görevi |
|---|---|
| `kosu_faz31.py` | Angajman koşucusu + 6 metriğin analizi (kilit bandı, menzil eğrisi, komut-takip, doyum, yarıçap) |
| `olcum_faz1.py` | Dikey + yaw kanalı ölçümü, hız kaynağı kıyası |
| `olcum_faz2.py` | Yatay kanal: işaret/eksen, trim eğrisi, basamak yanıtı |
| `olcum_faz3on.py` | Hedef hızı + kestirim gürültüsü (pasif gözlem) |
| `olcum_gnss.py` | GNSS düzeltici A/B (truth'a karşı, uçuşsuz) |

---

## 4. AYRINTILI BELGELER

| Belge | İçerik |
|---|---|
| **[01_GAZEBO_KAYNAK.md](01_GAZEBO_KAYNAK.md)** | Gönderilen sistem: her dosya, her Cfg sabiti, yasa nasıl çalışıyor, ArduPilot ne yapıyordu |
| **[02_DONUSTURUCU.md](02_DONUSTURUCU.md)** | Dönüştürücü: çerçeve sözleşmesi, kanal kanal matematik, döngü mimarisi, ArduCopter'da olup bizde olmayanlar |
| **[03_OLCUMLER.md](03_OLCUMLER.md)** | Her sayının nereden geldiği: Faz 1/2/3 ölçümleri, çürütülen varsayımlar, kanıtlanmayanlar |
| **[04_ENTEGRASYON.md](04_ENTEGRASYON.md)** | Yer kontrol istasyonuna bağlanma, silinen eski yasa, GPS kaynağı seçici |
| **[../docs/kopru_denetim.md](../docs/kopru_denetim.md)** | Bağımsız denetim: köprü ArduCopter'ın yerini doğru alıyor mu? (uçtan uca iz, limit önceliği, zamanlama) |

---

## 5. DURUM — ne kanıtlandı, ne kanıtlanmadı

### Kanıtlandı ✅

- **Yasa harfiyen aynı** — 4 kaynak dosyanın hash'i Gazebo orijinalleriyle birebir
- **25 Cfg sabitinin 21'i aynı**; 4'ü ölçümle ve kullanıcı onayıyla değişti
  (`V_MAX 18→22`, `RANGE_SET 11→6.9`, `IC_KAYMA 14→0`,
  `ISTASYON_ELEV_DEG 15→25` — gerekçeler 03'te)
- **Çeviri doğru** — uçtan uca izde çerçeve sapması **0.00 m**, komut sapması
  **0.013 m/s**, stick birebir eşleşme
- **Köprü yasayı kısıtlamıyor** — yatay limitleri karelerin **%0.00**'ında bağlıyor
- **Teslimat %99.5** (komut edilen hız ↔ gerçekleşen hız oranı 0.9945)
- **Kadraj merkezde** — hedef AV kutusunun içinde **%100**
- **Kilit isterisi sağlandı** (gerçek GPS ile): oturmuş menzil **8.9 m**,
  %5 bandında 10 sn pencerede **7.9-8.05 s** (gereken 5 s), **3/3 bölüm**
- **İstasyon geometrisi tasarımına oturuyor** — drone hedefin **2.89 m altında**
  (tasarım 2.92), 7.0-7.3 m arkasında; LOS yükselişi +21.4…+22.1°
- **164 birim testi** geçiyor (38'i köprüye ait)

### Kanıtlanmadı / açık ⚠️

- **Gazebo uçuşuyla birebir karşılaştırma yapılmadı** — elimizde Gazebo uçuş logu
  yok. "Aynı yasa" kanıtlı, "aynı uçuş" değil (araç, hedef ve telemetri farklı)
- **Bozuk GPS'te menzil 39-44 m'de oturuyor** (gerçek GPS'te ~9 m). Fark
  kestirim hatasından; kapatmak ayrı iş
- **%6 kutu bandı sağlanmıyor** (şartname eşiği %5 sağlanıyor). ELEV=25 kararının
  ölçülmüş bedeli — ayrıntı 03'te
- **Jerk şekillendirme yok** (ArduCopter'da WPNAV_JERK=4 vardı) — ölçüm bu turda
  zararsız olduğunu gösterdi, ama yapısal eksik
- **`get_iris` roll işareti ters** (DoW roll = −NED roll) — yalnız kadraj
  ÖLÇÜMÜNE girer, komuta girmez; etkisi \|Δu\|=0.013 (AV kutusu %100 değişmiyor)

---

## 6. NASIL ÇALIŞTIRILIR

### A) Yer kontrol istasyonuyla (normal kullanım)

```bat
1_Oyunu_Baslat.bat          :: oyunu aç, PLAY moduna geç
2_Arayuzu_Baslat.bat        :: arayüz → http://127.0.0.1:8000
```
Arayüzde **"Görev Başlat"**. Konsolda beklenen:
```
[KOPRU-GUDUM] hazir: HEDEF=BOZUK GPS  RANGE_SET=6.9 ELEV=25 V_MAX=22 IC_KAYMA=0 ... CT-EKF=ACIK
[KOPRU-GUDUM] istasyon: 6.25 m ARKA + 2.92 m ALT (hedefin altinda)
[KOPRU-GUDUM] kalkis: AGL 0.0 -> 40 m (zemin 48.4)
[KOPRU-GUDUM] kalkis TAMAM (AGL 39.x m) -> yasa devrede
[GPS] Kadraj güdümü (yeniden inşa) — hedefi kamera merkezine getir
[GPS] ARAMA d_h=... menzil=...
```

**GPS kaynağı** arayüzdeki butonlarla seçilir:
- **v2 (İnovasyonlu J)** → bozuk kanal + CT-EKF · yarışma koşulu · menzil ~39-44 m
- **🎯 Gerçek GPS (test)** → truth kanalı, filtre baypas · teşhis · menzil ~7-8 m

### B) Arayüzsüz, doğrudan ölçüm koşusu

```bash
python -m kopru.kosu_faz31 --n 3 --sure 75 --zemin 48.4 \
       --etiket X --vmax 22 --range 6.9 --ic 0 --hedef truth
```
Sonunda 6 metriğin analizi basılır; CSV'ler `veri/kopru_angajman_X_*.csv`.

> ⚠️ Oyun **tek TCP bağlantısı** kabul eder — arayüz ile koşu scriptini aynı anda
> çalıştırma.

---

## 7. DEĞİŞMEZ KURALLAR

1. **`gazebo_kaynak/` altındaki yasa dosyalarına dokunulmaz.** Değer değiştirmek
   gerekiyorsa env (`AVCI_GPS_*`) veya tek `setattr` ile, gerekçesi yazılarak.
2. **Yasa değerleri donduruldu.** Onaylı istisnalar: `V_MAX=22`, `RANGE_SET=6.9`,
   `IC_KAYMA=0`, `ISTASYON_ELEV_DEG=25` — hepsi ölçümle türetilip onaylandı.
   Yeni istisna eklenmez — ölç, gerekçelendir, sor.
3. **Köprünün kendi kazançları serbesttir** (trim tablosu, KP_VH, THR_TRIM,
   KP_VZ…) — bunlar ArduCopter'ın yerini alan katmandır ve platforma göre
   **ölçülmek zorundadır**.

> Ayrım tek cümlede: **yasa NE isteyeceğini söyler (değişmez), köprü NASIL
> yapılacağını söyler (ölçülür).**

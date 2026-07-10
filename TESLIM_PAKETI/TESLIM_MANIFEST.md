# TESLİM MANİFESTİ — Kaynak Kod Dosya Haritası

> **Takım:** Hamidiye · **Yarışma:** TEKNOFEST 2026 Savaşan İHA Avcı Drone
> Bu belge, teslim dokümanının **7. Kaynak Kod Teslimi** ve **3.7 Kaynak Kod Açıklaması**
> maddelerine göre, pakete konan her dosyanın hangi görevi yaptığını gösterir.

## Doküman gereksinimi → dosya eşlemesi

| Dokümanda istenen | Bu paketteki dosya(lar) | Görevi |
|---|---|---|
| **input.py** (simülasyon I/O) | `sdk/drone_sdk.py` | Oyunla TCP haberleşmesi: `get_*` telemetri, `set_*` kontrol komutu. **Bu, komitenin sağladığı RESMİ SDK'dır** (v2.2), bizim kodumuz değil — biz import edip kullanıyoruz. |
| **Hedef tespit** | `detection/gorsel_tespit.py` | YOLO26s ile Talon tespiti (+ dilimleme). Yardımcı: `kamera_model.py`, `model_yonetici.py` |
| **Tracking/takip** | `detection/takip.py` | Açık kaynak **boxmot HybridSort** sarmalayıcısı: kalıcı ID + kısa delik dayanıklılığı |
| **Sensör füzyonu / filtreleme** | `fusion/gnss_filtre.py` | Bozuk GNSS temizleme (spike reddi + hız + gecikme telafisi). **Özgün kodumuz.** |
| **Güdüm ve karar** | `guidance/ana_kontrol.py`, `guidance/gps_takip.py`, `guidance/ibvs_gorsel.py` | Karar makinesi (FSM), GPS güdüm (PD/PID + ölü-hesap), görsel güdüm (IBVS). **Özgün kodumuz.** |
| **Ana çalıştırma** | `main.py` → `web/server.py` | Yer kontrol istasyonunu başlatır; tüm hattı bağlar |
| **Konfigürasyon** | `config.py` (+ `guidance` içindeki `Cfg`/`GPSCfg` sınıfları) | Ağ/port + güdüm parametreleri |
| **Bağımlılıklar** | `requirements.txt` | Gerekli tüm paketler |
| **README (çalıştırma)** | `README.md`, `SDK_README.md` | Kurulum + çalıştırma talimatı |
| **Eğitilmiş model** | `models/best.pt` | YOLO26s Talon tespit modeli (kendi eğittiğimiz) |

### Ek çalışma-zamanı dosyaları (yukarıdakiler bunlara bağlı)
- `detection/kamera_model.py` — kamera geometrisi / homografi
- `detection/pencere_yakala.py` — oyun penceresini yakalama (görüntü kaynağı)
- `web/index.html` — yer kontrol arayüzü (telemetri + görev göstergeleri)

> **NOT:** Gerçek/truth GPS (`get_debug_truth`), truth-tabanlı test güdüm modu, parametre-ayar
> rapor aracı (tune_rapor) ve tüm debug göstergeleri teslim paketinden **tamamen çıkarıldı** —
> güdüm yalnızca filtreli bozuk GNSS + kamera kullanır.

> **NOT:** Poz/keypoint gözlemcisi (pose) bu sürümde KAPALI ve teslim paketinden **tamamen
> çıkarıldı** (`pose/`, `poz_tespit.py`, `talon_pose_estimator.py`, `talon_pose.pt`); ilgili
> yükleme kodu `web/server.py`'den de kaldırıldı. Görev yalnızca bbox tespiti + takip + füzyon +
> güdüm ile yürür.

## Açık kaynak kütüphaneler (Doküman 8.5 — kaynak beyanı)
- **ultralytics** (+ torch) — YOLO tespit çıkarımı
- **boxmot** — HybridSort çoklu-nesne takibi
- **opencv-python** — görüntü işleme / kare yakalama
- **numpy** — vektör/matris
- **mss, Pillow, pygetwindow, windows-capture** — ekran/pencere yakalama (Windows)
- **openpyxl, psutil** — rapor / sistem yardımcıları

## Özgünlük beyanı (Doküman 8)
- **Bizim özgün kodumuz:** `fusion/gnss_filtre.py`, `guidance/*`, `detection/*` (takip.py HybridSort'u
  **sarar**), `web/*`, `config.py`, `main.py`.
- **Komitenin sağladığı (bizim değil):** `sdk/drone_sdk.py` (resmi SDK v2.2).
- **Hazır kütüphane (yalnız çağrılıyor):** ultralytics/YOLO tespiti, boxmot/HybridSort takibi.
- Karar ve güdüm mantığının tamamı bize aittir ve her ana bileşeni açıklayabiliriz.

## Çalıştırma (özet — ayrıntı README.md)
1. `pip install -r requirements.txt`
2. Oyunu başlat (`1_Oyunu_Baslat.bat`) → Play.
3. Arayüzü başlat (`2_Arayuzu_Baslat.bat` veya `python main.py`) → tarayıcıda yer kontrol arayüzü.

## Doğrulama notu
- **İçe-aktarma (import) bütünlüğü statik olarak DOĞRULANDI:** pakette proje-içi hiçbir modül eksik
  değil (tüm `import`'lar paket içinde çözülüyor).
- **ÖNERİ:** Teslimden önce bu klasörü **temiz bir bilgisayara** kopyalayıp `pip install -r
  requirements.txt` + oyun açık şekilde bir kez çalıştırın — doküman "başka bilgisayarda doğrudan
  çalıştırılabilir olmalı" diyor; canlı bir deneme, eksik sistem bağımlılığı ihtimalini de kapatır.

## Pakete BİLEREK konulmayanlar (gerekli değil / teslim dışı)
- **Poz/keypoint gözlemcisi (KAPALI):** `pose/`, `detection/poz_tespit.py`,
  `detection/talon_pose_estimator.py`, `models/talon_pose.pt` — göreve girmiyordu, çıkarıldı.
- **Ölü/kullanılmayan modüller:** `detection/algi_hatti.py`, `detection/model_yonetici.py`,
  `web/dev_truth.py` (hiçbir yerden import edilmiyordu).
- **Çalışma zamanı çıktıları / geliştirme:** `veri/` (loglar), oyun dosyaları, `arsiv/` (eski kod),
  `arac/`, `araclar/`, `png_sim/`, `docs/`, testler, model yedekleri, iç notlar (`CLAUDE.md` vb.),
  `video/` (video hazırlık belgeleri).

Bu paket **yalnızca görevi çalıştıran kodu** içerir; import bütünlüğü doğrulandı (eksik modül yok).

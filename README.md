# 🛸 Avcı Drone — Simülasyon Test Ortamı (Yer Kontrol İstasyonu)

TEKNOFEST **"Drones of War"** avcı drone projesinin yazılımı. Simülatörden gelen
**bozuk hedef GNSS'ini** İnovasyonlu J (CT-EKF) ile temizler, **GPS güdümüyle** hedefe
yaklaşır, görsel temas kurulunca **YOLO (best.pt) + DÜZ IBVS** ile yönelimi **yalnızca
kameradan** üretir (yarışma kuralı) ve hepsini tarayıcı tabanlı bir arayüzden yönetir:
canlı FPV (tarayıcı ekran/pencere paylaşımı), telemetri, canlı tune panelleri, güdüm
pipeline anahtarı (OTO / GPS / GÖRSEL).

```
Oyun (Unreal, TCP 127.0.0.1:12345)
   │ bozuk hedef GPS (cm, max 1 Hz)          ┌──────────────────────────────┐
   ▼                                          │  models/best.pt (YOLO, talon)│
sdk/drone_sdk.py ──► web/server.py ◄── detection/ (pencere yakalama + tespit)
                        │                                   ▲ oyun penceresi karesi
                        ├─ fusion/inovasyonlu_j_v2.py  (GNSS temizleme + hız kestirimi)
                        ├─ guidance/ana_kontrol.py     (GPS yaklaşma + GORSEL_GUDUM FSM)
                        ├─ guidance/ibvs_guidance.py   (bbox → angle-mode komut)
                        └─ web sunucusu ──► web/index.html (tarayıcı arayüzü, :8000)
```

---

## 📦 Gereksinimler
- **Windows 10/11** (pencere-içeriği yakalama `windows-capture` Windows'a özeldir; oyun da Windows exe'sidir)
- **Python 3.10 – 3.12** (3.12 ile test edildi; 3.13'e CUDA'lı torch wheel'i yoktur, kullanma)
- **Git**
- **NVIDIA GPU önerilir** (YOLO ~60-80 FPS; GPU yoksa CPU ile de çalışır, daha yavaş tespit)
- Yarışma paketi (aşağıdaki Drive bağlantısından): oyun + resmi SDK

---

## ⚙️ Kurulum (adım adım)

### 1) Repoyu klonla
```
git clone https://github.com/kayranecatikara/avci-drone-yer-kontrol.git
cd avci-drone-yer-kontrol
```

### 2) Yarışma dosyalarını indir ve yerleştir
Drive klasörü: **https://drive.google.com/drive/folders/1-7t80jf5uW446tsSB3JQXyxqDZC2dECO**

| Drive'daki dosya | Nereye koyulacak | Not |
|---|---|---|
| `Drones of War Teknofest` (zip) | Zip'i **repo kökünde** `Drones of War Teknofest` klasörü olacak şekilde çıkart → `avci-drone-yer-kontrol\Drones of War Teknofest\DronesOfWar.exe` | Klasör adı birebir böyle kalmalı (`1_Oyunu_Baslat.bat` ve pencere yakalama buna göre). Git'e girmez (gitignore'lu). |
| `drone_sdk.py` | `sdk\drone_sdk.py` **üzerine yaz** | Repo zaten v2.2 içerir; Drive'da daha yeni sürüm yayınlanırsa güncelle. |
| `README.md` (resmi SDK dokümanı) | `SDK_README.md` **üzerine yaz** | ⚠️ Repo kökündeki `README.md`'nin (bu dosyanın) üzerine YAZMA! |

### 3) Python paketlerini kur
**GPU'n varsa (önerilen)** — önce CUDA'lı torch, sonra kalanlar:
```
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt
```
**GPU yoksa (CPU):**
```
pip install torch torchvision
pip install -r requirements.txt
```
`requirements.txt` içeriği: numpy, mss, Pillow, pygetwindow, **ultralytics**,
**opencv-python**, **windows-capture**. Eğitilmiş model **`models/best.pt` repoda
hazır gelir** — ayrıca bir şey indirilmez.

### 4) Kurulumu doğrula (repo kökünden)
```
python -c "import torch; print(torch.__version__, 'CUDA:', torch.cuda.is_available())"
python -c "import sys; sys.path.insert(0,'.'); import web.server; print('IMPORT OK')"
python detection\gorsel_tespit.py
```
Son komut `best.pt siniflari (model.names): {0: 'talon'}` yazmalı.

---

## ▶️ Çalıştırma
1. **Oyunu aç:** `1_Oyunu_Baslat.bat` (veya `Drones of War Teknofest\DronesOfWar.exe`) → **PLAY** moduna geç.
2. **Arayüzü aç:** `2_Arayuzu_Baslat.bat` (veya repo kökünden `python main.py`).
3. Tarayıcı: **http://127.0.0.1:8000** — sol üstte "Oyuna bağlı" yeşil olmalı.
4. Orta paneldeki **"📡 Görüntüyü Bağla"** butonuna bas → açılan listeden **oyun
   penceresini (Drones of War)** seç. FPV görüntüsü bu pencereden akar; üstüne
   tespit overlay'i (bbox / REF çizgisi / rozet) çizilir.

> ⚠️ Aynı anda **tek bir** arayüz örneği çalışsın (oyun tek TCP bağlantısı kabul
> eder). Yeniden başlatmadan önce eski pencereyi kapat.
> ⚠️ Arayüzü hep **repo kökünden** `python main.py` ile başlat; `python web\server.py`
> doğrudan çalıştırılmaz (paket importları kırılır).

---

## 🖥️ Arayüz
| Panel | İçerik |
|-------|--------|
| **Sol** | Görev Başlat (İnovasyonlu J) / Gerçek GPS (test) / Durdur / Manuel mod / **Tune (canlı ayar)** / **Güdüm Pipeline anahtarı: OTO · GPS · GÖRSEL** |
| **Orta** | FPV (Görüntüyü Bağla → oyun penceresi) + overlay: hedef bbox'ı, görüntü merkezi `+`, **turuncu REF çizgisi** (25° kamera tilt telafisi), ex/ey/conf, durum, **"GPS GÜDÜMÜ: KAPALI/AÇIK" rozeti** |
| **Sağ** | Telemetri (avcı + hedef), İnovasyonlu J sapma ölçümü (ham vs filtre, gerçeğe hata), mesafeler |

**Güdüm akışı:** ARAMA (GPS yaklaşma) → best.pt hedefi 5 ardışık karede görünce
**GORSEL_GUDUM** (GPS yönelimi mimari olarak kesilir; yönelim yalnızca kamera) →
hedef ~1.5 sn kaybedilirse GPS'e geri döner ve yeniden yakalar (OTO modda).

---

## 🎯 İlk uçuş kalibrasyonu (tek seferlik, ~2 dk)
Simülatör güncellemesi (SDK v2.2) kamerayı **25° yukarı tilt**'li yaptı; güdüm hedefi
görüntü merkezine değil **turuncu REF çizgisine** oturtur. İlk uçuşta Tune panelinden:
1. **VIS_EY_REF (Dikey referans):** hedef seninle **aynı irtifadayken** bbox merkezi
   turuncu çizgiye oturana kadar slider'ı oynat (üstte kalıyorsa küçült, altta ise büyüt).
2. **İşaretler:** hedef sağdayken burun ters dönüyorsa `VIS_SIGN_YAW`'ı çevir (+1↔−1);
   irtifayı ters düzeltiyorsa `VIS_SIGN_VZ`'yi çevir. Kural: komut hatayı **azaltmalı**.
3. İyi değerleri **📋 Değerleri Yazdır** ile kopyala → `guidance/ana_kontrol.py` içindeki
   `Cfg`'ye yapıştır (kalıcı olsun; slider değerleri sunucu kapanınca sıfırlanır).

---

## 🔧 Sorun giderme
| Belirti | Sebep / Çözüm |
|---|---|
| FPV görüntüsü yok | "📡 Görüntüyü Bağla"ya bastın mı? Açılan listeden **oyun penceresini** seç. Tarayıcı ekran paylaşımına izin vermeli. |
| Overlay (bbox/REF) çizilmiyor | Görüntü var ama tespit yoksa: oyun görünür/önde mi (sunucu tespiti mss ile oyun penceresinden yapar), model yüklendi mi (`{0:'talon'}`)? |
| "Sunucu kapalı" | `python main.py` çalışmıyor ya da 8000 portu başka süreçte. Eski pencereyi kapat, tekrar başlat. |
| Telemetri gelmiyor ama FPV var | Oyun PLAY modunda değil; ya da 12345 portunu başka bir arayüz örneği tutuyor. |
| `[GORSEL] Dedektor YUKLENEMEDI` | ultralytics/torch kurulu değil → sistem **çökmez**, GPS güdümüyle devam eder. Paketleri kur. |
| CUDA False | torch'u CUDA wheel'inden kurmadın: önce `pip install torch --index-url https://download.pytorch.org/whl/cu121`. |
| `ModuleNotFoundError: fusion/guidance/...` | Repo kökünden çalıştırmıyorsun. `cd avci-drone-yer-kontrol` → `python main.py`. |
| Loglar nerede? | Tüm çalışma çıktıları (`ucus_log_*.csv`, `kiyas_log.csv`, metrikler) `veri\` klasöründe. |

---

## 🏁 Kendi GPS filtreni test etmek istersen
Üretim filtresi `fusion/inovasyonlu_j_v2.py` (İnovasyonlu J). `web/server.py` her ham
pakette filtreyi besleyip **gerçeğe hatayı** ölçer (`_kiyas_guncelle`) ve `veri/kiyas_log.csv`'ye
yazar. Kendi filtren için aynı sözleşmeyi uygula — sınıfında cm cinsinden
`guncelle(x, y, z) -> (tx, ty, tz) | None` olsun — ve `_kiyas_guncelle` içindeki J
kalıbını kopyalayıp filtreni ekle; arayüz sağ panelinde ortalama/en kötü hata görünür.

---

## 📁 Dosya haritası
| Yol | Açıklama |
|-----|----------|
| `main.py` | Giriş noktası — **tek başlatma komutu:** `python main.py` |
| `sdk/drone_sdk.py` | Resmi yarışma SDK'sı (v2.2; TCP telemetri/kontrol) |
| `fusion/inovasyonlu_j_v2.py` | GNSS temizleme + hedef hız kestirimi (CT-EKF) |
| `guidance/ana_kontrol.py` | Güdüm beyni: GPS yaklaşma, GORSEL_GUDUM FSM, Cfg (tüm ayarlar) |
| `guidance/ibvs_guidance.py` | DÜZ IBVS: bbox merkezi → throttle/pitch/roll/yaw |
| `detection/gorsel_tespit.py` | YOLO best.pt sarmalayıcı (en yüksek conf bbox) |
| `detection/pencere_yakala.py` | Oyun penceresi içeriği yakalama (occlusion-proof FPV) |
| `web/server.py` + `web/index.html` | Web sunucusu + tarayıcı arayüzü |
| `models/best.pt` | Eğitilmiş YOLO modeli (sınıf: `talon`) — repoda hazır |
| `arac/` | Bağımsız analiz araçları (`analiz_ucus.py`: uçuş logu teşhisi) |
| `veri/` | Çalışma çıktıları (loglar) — otomatik oluşur, git'e girmez |
| `arsiv/` | Eski sürümler (referans) |
| `SDK_README.md` | Resmi SDK dokümanı (birimler, angle-mode, bozulma türleri) |
| `1_Oyunu_Baslat.bat` / `2_Arayuzu_Baslat.bat` | Tek tıkla başlatıcılar |

---

## 🤖 Claude ile otomatik kurulum (takım arkadaşları için)

Aşağıdaki prompt'u kopyalayıp **Claude Code**'a (terminalde `claude` yazıp) ya da
Claude'a ver; kurulumun tamamını senin yerine yapar/yönetir. Tek elle yapacağın şey
Drive'dan dosyaları indirmek (Claude sana ne zaman gerektiğini söyler) ve oyunda
PLAY'e basmak.

```text
GÖREV: Windows makinemde TEKNOFEST "Drones of War" avcı drone test ortamını
(simülatör + Python yer kontrol arayüzü) SIFIRDAN kur, doğrula ve çalıştır.
Adım adım ilerle; her adımın çıktısını kontrol et, hata olursa çözüp devam et.

1) ORTAM DENETİMİ
   - "python --version" çalıştır: 3.10–3.12 olmalı (3.13 OLMAZ: CUDA'lı torch wheel'i
     yok). Python yoksa/3.13 ise beni python.org'dan 3.12 kurmaya yönlendir
     ("Add python.exe to PATH" işaretli olacak) ve kurulumdan sonra devam et.
   - "git --version" kontrol et; yoksa git-scm.com'dan kurdur.
   - "nvidia-smi" dene: çalışıyorsa GPU var (CUDA'lı kurulum yapacağız), çalışmıyorsa
     CPU kurulumu yapacağız. Not: PowerShell 5.1'de "&&" zincirleme çalışmaz;
     komutları ayrı ayrı çalıştır.

2) REPO
   - Uygun bir klasörde: git clone https://github.com/kayranecatikara/avci-drone-yer-kontrol.git
   - Bundan sonraki HER komutu repo kökünden (avci-drone-yer-kontrol içinden) çalıştır.

3) YARIŞMA DOSYALARI (Drive'dan — ben indireceğim, sen yerleştir)
   - Benden şu klasörü tarayıcıyla açıp İNDİRMEMİ iste:
     https://drive.google.com/drive/folders/1-7t80jf5uW446tsSB3JQXyxqDZC2dECO
     İçinde 3 öğe var: "Drones of War Teknofest" (zip), "drone_sdk.py", "README.md".
     (İstersen önce "pip install gdown" + "gdown --folder <link>" ile otomatik indirmeyi
     DENE; olmazsa manuel indirmemi bekle. İndirilenler genelde Downloads klasöründedir.)
   - Zip'i REPO KÖKÜNE çıkart; sonuç TAM OLARAK şu yol olmalı:
     avci-drone-yer-kontrol\Drones of War Teknofest\DronesOfWar.exe
     (Klasör adını değiştirme; zip içinden çift-klasör çıkarsa düzelt. Bu klasör
     .gitignore'dadır, commit edilmez.)
   - drone_sdk.py dosyasını sdk\drone_sdk.py ÜZERİNE kopyala.
   - README.md dosyasını (resmi SDK dokümanı) SDK_README.md ÜZERİNE kopyala.
     ÇOK ÖNEMLİ: repo kökündeki README.md'nin üzerine YAZMA — o proje dokümanıdır.
     Kopyalamadan önce/sonra "git status" ile yalnız sdk/drone_sdk.py ve SDK_README.md'nin
     değiştiğini doğrula; README.md değiştiyse "git checkout -- README.md" ile geri al.

4) PYTHON PAKETLERİ
   - GPU varsa ÖNCE: pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
     GPU yoksa: pip install torch torchvision
   - Sonra: pip install -r requirements.txt
     (ultralytics, opencv-python, windows-capture, mss, Pillow, pygetwindow, numpy kurulur.)
   - Model dosyası models\best.pt REPODA HAZIR gelir; ekstra indirme yok.

5) DOĞRULAMA (hepsi repo kökünden; herhangi biri hata verirse önce onu çöz)
   - python -c "import torch; print(torch.__version__, 'CUDA:', torch.cuda.is_available())"
     (GPU'lu kurulumda CUDA: True görmelisin.)
   - python -m py_compile main.py web/server.py guidance/ana_kontrol.py guidance/ibvs_guidance.py detection/gorsel_tespit.py detection/pencere_yakala.py fusion/inovasyonlu_j_v2.py sdk/drone_sdk.py
   - python -c "import sys; sys.path.insert(0,'.'); import web.server; print('IMPORT OK')"
   - python detection\gorsel_tespit.py
     Beklenen çıktı: best.pt siniflari (model.names): {0: 'talon'}
     (İlk YOLO yüklemesi ~5-10 sn sürebilir; normaldir.)

6) ÇALIŞTIRMA TESTİ
   - Benden oyunu açmamı iste: 1_Oyunu_Baslat.bat (veya Drones of War Teknofest\
     DronesOfWar.exe) ve oyunda PLAY moduna geçmemi bekle.
   - Sonra arayüzü başlat: python main.py   (arka planda çalıştır ve çıktıyı izle;
     alternatif: 2_Arayuzu_Baslat.bat)
   - http://127.0.0.1:8000 aç(tır): sol üst "Oyuna bağlı" YEŞİL olmalı. FPV görüntüsü
     için orta paneldeki "📡 Görüntüyü Bağla" butonuna basıp açılan listeden OYUN
     PENCERESİNİ (Drones of War) seçmem gerektiğini bana hatırlat (tarayıcı ekran
     paylaşımı; otomatik değildir).

7) BİLİNEN TUZAKLAR (bunlara dikkat et)
   - Arayüz HEP repo kökünden "python main.py" ile başlatılır; "python web\server.py"
     doğrudan ÇALIŞTIRILMAZ (paket importları kırılır).
   - Aynı anda TEK arayüz örneği: oyun tek TCP bağlantısı kabul eder (127.0.0.1:12345),
     web portu 8000. Yeniden başlatmadan önce eski süreci kapat.
   - ultralytics/torch kurulamazsa sistem yine açılır: görsel faz pasif kalır, GPS
     güdümü çalışır (konsolda "[GORSEL] Dedektor YUKLENEMEDI" görürsün).
   - windows-capture kurulamazsa FPV mss ekran yakalamaya düşer; o modda oyun penceresi
     görünür/önde olmalı.
   - Çalışma çıktıları (ucus_log_*.csv, kiyas_log.csv) veri\ klasörüne yazılır.
   - Oyun + arayüz AYNI makinede çalışmalı (bağlantı 127.0.0.1).

8) BİTİŞ RAPORU
   Kurulum bitince bana kısaca raporla: Python/torch sürümleri, CUDA durumu,
   doğrulama sonuçları, oyun bağlantısı ve FPV durumu, arayüzü nasıl başlatacağım.
   İlk uçuş kalibrasyonu için beni repo README'sindeki "İlk uçuş kalibrasyonu"
   bölümüne yönlendir (VIS_EY_REF turuncu çizgi + işaret kalibrasyonu).
```

---
*TEKNOFEST Drones of War — Avcı Drone Takımı*

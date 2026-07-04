# Avcı Drone — Proje Notları (CLAUDE.md)

## ASIL HEDEF
Bu projenin asıl amacı **Simülasyon Uçuş Kanıt Videosu** aşamasından geçmektir.
Tüm mimari ve kod kararları, şartnamedeki görev akışını ve video isterlerini
EKSİKSİZ karşılayacak şekilde alınır.

## ÇALIŞMA İLKELERİ (değişmez)
- **Sadece üzerinde çalıştığımız, açıklayabildiğimiz şeyi kullan: İnovasyonlu J**
  (`inovasyonlu_j_v2.py`, CT-EKF GNSS düzeltici). IMM-EKF veya bakmadığımız yabancı
  modüller entegre EDİLMEZ. (Yarışma kuralı 8: her bileşeni açıklayabilmeliyiz.)
- **Düzgün/açıklanabilir parçaları entegre et, saçma/overfit parçaları etme.**
  Senaryoya aşırı-uydurulmuş sabitler (örn. "lock 5.2 sn", death_plunge) kullanılmaz.
- **Hazır güdüm yazılımı doğrudan kullanılmaz** (kural 6). Kullandığımız her yöntem
  (filtre, öngörülü yönelim) bizim temiz implementasyonumuzdur ve takımca açıklanabilir.
- **Mevcut çalışan sistemi bozma:** server.py + index.html (web arayüzü), manuel mod,
  kıyas paneli, kaynak geçişi korunur. Güdüm değişiklikleri `AvciKontrol` içine gömülür.

## GPS GÜDÜMÜNÜN ROLÜ (net sınır)
GPS güdümü **öldürücü faz değildir.** Görevi:
1. Bozuk GNSS'i optimize et (İnovasyonlu J ile temizle + hedef hızını kestir).
2. Araca yönel (öngörülü/lead yönelim — hedefin gideceği yere nişan al).
3. Hedefle **kesintisiz, düzgün görsel temas** kur (kamera FOV'unda merkezde tut).
4. Görsel güdüm fazına (YOLO/CV) temiz devret (ARAMA→KILIT). Terminal vuruş görsel fazın işi.

## SİSTEM MİMARİSİ (modül → şartname teslim eşlemesi)
- `drone_sdk.py`        → simülasyon I/O (input/telemetri); şartname "input.py" muadili.
- `inovasyonlu_j_v2.py` → sensör füzyonu / filtreleme / tahmin (GNSS temizleme + hız kestirimi).
- `ana_kontrol.py`      → güdüm ve karar mekanizması (öngörülü yönelim + ARAMA→KILIT FSM).
- `server.py`+`index.html` → görev arayüzü, telemetri, **10 video isterinin görünürlüğü**
  (aşağıdaki bölüm). Olay günlüğü + görev izleyici `server.py`'de; ID/faz/vuruş overlay'i
  index.html'de. GÜDÜM KODUNA DOKUNULMAZ (bkz. VİDEO ÇIKTILARI ARAYÜZÜ).
- [YAPILACAK] görüntü işleme + hedef tespit + tracking (YOLOv8/v11 .pt) → görsel faz; şu an
  `_kamera_kontrol` stub'ı yerine bağlanacak. Teslim .zip'i bu modülü + model dosyasını içermeli.

## VİDEO ÇIKTILARI ARAYÜZÜ (10 zorunlu çıktı — 2026-07-04'te eklendi)
Şartnamenin **videoda görünür 10 teknik çıktısı** arayüzde karşılanır. TEMEL KURAL:
tüm yeni sinyaller `web/server.py`'deki **`_gorev_izle()` görev izleyicisinde**, `beyin`'in
VAR OLAN alanlarından **kenar-tespitiyle** (önceki tik ↔ bu tik) türetilir →
`guidance/ana_kontrol.py` ve `detection/gorsel_tespit.py` **DEĞİŞMEZ** (kural 8: izleyici
"durum değişti mi?" karşılaştırmasından ibaret, takımca açıklanabilir).
- **Payload** (`build_telemetry`): `olaylar`, `gnss`, `gudum`, `takip`, `gorev` anahtarları +
  `gorsel.tespit`'e `cls/sinif/id`. Eski anahtarlar korundu (`gorsel.gps_kesildi` yanıltıcı
  adı dahil — mevcut rozet ona bağlı).
- **Arayüz eşlemesi:** (1) FPV; (2) mini-harita + koordinat kartları; (3) BOZUK GNSS kartı
  (bozulma adları, KESİNTİ rozeti, ham/J hata); (4) olay günlüğü "İLK TESPİT"; (5) bbox +
  "ID:n sınıf conf" etiketi + TAKİP kartı; (6) TAKİP: AKTİF/PASİF rozeti; (7) olay zinciri
  kayıp→yeniden tespit; (8) GÜDÜM KOMUTLARI kartı (uygulanan 4 komut + d_h/handoff); (9) faz
  çipleri + "VURUŞ!" banner; (10) kalıcı "GÖREV BAŞARILI" banner.
- **Takip-ID:** kara-kutu takipçi YOK; `beyin.son_tespit_t` tazeliğinden basit ID makinesi.
  Eşikler mevcut `Cfg.VIS_STALE_S`/`VIS_LOST_TO_GPS_S`'ten türer (yeni sabit icat edilmez).
- **VURUŞ latch mesafesi:** truth varsa gerçek 3B, yoksa J-temiz; **ham ASLA** (sahte vuruş).
- Detaylı tasarım: `~/.claude/plans/5-videoda-g-r-lmesi-beklenen-peaceful-yao.md`.

## VİDEO İSTERLERİ (karşılanması zorunlu — özet)
İlk 3 dk (hızlandırma YOK, sesli teknik anlatım): sistem mimarisi; bozuk GNSS'in girdi
olarak alınışı ve değerlendirilişi; görüntü işleme/hedef tespit; tracking; sensör füzyonu/
filtreleme (GNSS hata/sıçrama/kayıp/gecikmede tepki); güdüm/karar; kaynak kod dosyalarının
tanıtımı + kullanılan açık kaynak kütüphaneler.
Son 3 dk (gerçek zamanlı görev kanıtı): otonom başlama → bozuk GNSS ile bölgeye yönelme →
görüntüyle tespit → tracking aktif → görsel takip → **GNSS bağımlılığının azaldığının
gösterilmesi** → yaklaşma → otonom angajman → vuruş/başarı → insan müdahalesi olmadığı.
Otonomi: manuel hedef seçimi/işaretleme YOK; tespit ve tracking otonom devreye girmeli.
Teslim .zip: input, hedef tespit, tracking, füzyon/filtre, güdüm, ana çalıştırma, config,
bağımlılıklar (requirements), README, eğitilmiş model (.pt). Video↔kod tutarlı olmalı.

## BEKLEYEN İŞ
- **Görsel güdüm fazı — YZ modelleri / ekstra özellikler:** görsel güdüm algoritmasına yapay
  zeka modelleri ve ek yetenekler eklenecek (ör. daha güçlü tespit/tracking, hedef sınıf/ID
  sürekliliği, poz/mesafe kestirimi, kamera-tabanlı terminal vuruş). **Bunlar eklendikçe
  arayüzde de karşılık gelen değişiklikler yapılacak** — yeni panel/rozet/telemetri alanı.
  Arayüz mimarisi buna HAZIR: yeni sinyalleri `server.py` `_gorev_izle()` içinde `beyin`'den
  okuyup `build_telemetry` payload'ına ekle + `index.html`'de kart/overlay çiz (güdüm koduna
  minimum dokunuş; VİDEO ÇIKTILARI ARAYÜZÜ bölümündeki desen).
- **Otonom angajman/vuruş (İster 9/10) — güdüm bağımlılığı:** UI göstergeleri hazır ama drone
  OTO uçuşta hedefe otonom VURMUYOR. Gerekli 3 iş: `Cfg.AUTO_VISUAL_HANDOFF=True`, kamera-
  tabanlı terminal vuruş mantığı, `Cfg.GPS_TERMINAL_STRIKE` (şu an hepsi kapalı). Bunlar gelince
  UI'da satır DEĞİŞMEZ (VURUŞ/BAŞARI latch'i mesafe eşiğinden otomatik tetiklenir). Şimdilik
  test: manuel GÖRSEL switch veya `GPS_TERMINAL_STRIKE=True` + "Gerçek GPS" ram.
- Video anlatım metinleri (ilk 3 dk + son 3 dk) — kullanıcı EN SONDA isteyecek; tüm metinler
  takır takır verilecek.

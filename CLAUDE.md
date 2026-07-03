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
- **Mevcut çalışan sistemi bozma:** server.py + index.html (web arayüzü), manuel mod
  korunur. Güdüm değişiklikleri `AvciKontrol` içine gömülür.
  *(Not 2026-07-03: truth'a dayalı kıyas paneli ve "Gerçek GPS" kaynak geçişi SERT
  AYRIM gereği arayüzden kaldırıldı; filtre doğrulama artık `arac/` altındadır.)*

## SERT AYRIM — TRUTH POLİTİKASI (kalıcı, ihlal edilmez)
Sim'in bozulmamış "truth" kanalı (`get_debug_truth` / `get_active_corruption`,
resmî SDK'nın debug alanları) yalnızca GELİŞTİRME/DOĞRULAMA içindir:
- **Truth erişimi yalnızca iki yerde yaşayabilir:** (1) `arac/` altındaki
  geliştirme/doğrulama scriptleri (uçuş sonrası analiz/ölçüm; üretim hattına
  `arac/`'tan RUNTIME IMPORT YAPILMAZ), (2) çalışma anındaki TEK dev kod
  noktası olan **`web/dev_truth.py`** (DEV hedef-kaynağı; teslim paketine
  girmez). (`arsiv/` ve `test/` de uçuş dışıdır; paketlenmez.)
- **Uçuş pipeline'ı (`detection/`, `guidance/`, `fusion/`, `web/`, `main.py`)
  truth'a erişemez:** import, çağrı, yorum, log dizesi dahil hiçbir iz
  bulunamaz. TEK istisna biçimi: `web/server.py` ve `web/index.html` içinde
  `>>> DEV-ONLY >>> ... <<< DEV-ONLY <<<` işaretçileriyle ÇİTLENMİŞ bağlantı
  blokları (dev_truth'a bağlanan az sayıda satır). Çit dışında hiçbir dosyada
  truth/dev izi olamaz; görürsen hata say, kaldır. `web/dev_truth.py`
  yoksa/yüklenemezse sunucu normal başlar, DEV butonu arayüzde hiç görünmez.
  (`sdk/drone_sdk.py` resmî verili dosyadır; truth API'sinin orada TANIMLI
  olması bizim kullanmamız değildir.)
- **DEV hedef-kaynağı bir GÜDÜM modu değil KAYNAK seçicisidir:**
  `AvciKontrol.set_hedef_kaynagi` dikişine bağlanır; yalnızca midcourse
  (ARAMA/TAKIP) beslemesini değiştirir, OTO/GPS/GÖRSEL anahtarına ve
  GORSEL_GUDUM sonrasına dokunmaz. GERÇEK (DEV) aktifken arayüzde kırmızı
  bant çıkar; uçuş CSV'sine `hedef_kaynak` (filtre/gercek) yazılır.
- **Truth kullanan her scriptin başına şerh:** "GELİŞTİRME/DOĞRULAMA ARACI —
  görev uçuşunda ve değerlendirme koşusunda kullanılmaz."
- **Görev zinciri değişmez:** bozuk hedef GPS → fusion filtresi → midcourse
  yaklaşma; görsel temas sonrası hedef konumu YALNIZCA görsel (bbox/PnP).

## TESLİM PAKETİ KURALI
Yarışmaya gidecek kod paketi = uçuş pipeline'ı (`main.py`, `detection/`,
`guidance/`, `fusion/`, `web/`, `sdk/`, `models/`, requirements, README).
`arac/` altındaki geliştirme scriptleri ve **`web/dev_truth.py` pakete GİRMEZ**.
`arac/paket_kontrol.py`: (a) dev_truth.py'yi dışlar, (b) DEV-ONLY çitli
blokları server.py ve index.html'den otomatik siler (söküm sonrası server
py_compile ile doğrulanır), (c) kalan TÜM pakette truth/dev_truth/gercek
anahtar kelimelerini tarar — TEK eşleşmede paketlemeyi reddeder.
**Gönderilecek video koşusu da bu paketten çıkan kodla yapılır.**

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
- `server.py`+`index.html` → görev arayüzü, telemetri, bozuk-GNSS görünürlüğü (video çıktıları).
- [SÜRÜYOR] görüntü işleme + hedef tespit + tracking (YOLO .pt) → görsel faz; yarışma
  pipeline refaktörüyle genişliyor (takip/PnP). Teslim .zip'i bu modülü + model dosyasını içermeli.

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
- Video anlatım metinleri (ilk 3 dk + son 3 dk) — kullanıcı EN SONDA isteyecek; tüm metinler
  takır takır verilecek.

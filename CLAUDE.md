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
  noktası olan **`web/dev_truth.py`** (DEV hedef-kaynağı + DEV vuruş-mesafe
  ölçümü; teslim paketine girmez). (`arsiv/` ve `test/` de uçuş dışıdır;
  paketlenmez. **`pose/` (merge 2026-07-06):** yalnız KOŞU-ZAMANI üçlüsü
  `poz_cozucu.py`+`geometri.py`+`talon_keypoints.json` uçuş hattı sayılır ve
  truth-izsiz tutulur/paketlenir; pose/'un kalan scriptleri uçuş dışıdır,
  paketlenmez.)
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
`guidance/`, `fusion/`, `web/`, `sdk/`, `models/`, requirements, README
+ pose koşu-zamanı üçlüsü: `pose/poz_cozucu.py`, `pose/geometri.py`,
`pose/talon_keypoints.json` [PnP 3B tablo tek kaynağı] ve `pose/__init__.py`).
`arac/` altındaki geliştirme scriptleri, pose/'un kalan araçları ve
**`web/dev_truth.py` pakete GİRMEZ**.
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
- `server.py`+`index.html` → görev arayüzü, telemetri, bozuk-GNSS görünürlüğü (video
  çıktıları). MERGE 2026-07-06: bizim arayüz BAZ; main'in kullanışlı ekleri (sahte
  tespit modu, poz gözlemci paneli vb.) bizim hatta taşınarak entegre edilir.
- [FAZ 1-4 KOD TAMAM] görsel pipeline: `detection/` (kamera_model, takip=ByteTrack+gyro-CMC,
  algi_hatti, talon_pose_estimator=PnP, model_yonetici=registry) + `guidance/` (kilit_kurali
  §6.1.4, gudum_yasasi APN+OIPN) + `iletisim/hakem_istemci`. FSM: ARAMA→TAKIP→GORSEL_GUDUM→
  KILIT_BILDIR→ANGAJMAN. **Pose'suz TAM çalışır** (PnP/OIPN otomatik pasif → IBVS fallback;
  regresyon: OIPN kapalı+pose'suz = eski hat birebir). ~91 birim testi. Sim borçları +
  "iyi model geldiğinde" runbook MEVCUT_DURUM'da. Teslim .zip bu modülleri + model .pt içerir.
- MERGE 2026-07-06 (main→yarisma-pipeline): GPS güdümünde İKİ PROFİL bayrakla yaşar
  (`GPS_TERMINAL_STRIKE=False`→serhadcan standoff [varsayılan], `True`→bizim intercept+ram;
  `AUTO_VISUAL_HANDOFF`/`HANDOFF_YAKINLIK_SART` görsel devir kapıları) — HİÇBİR TARAF
  SİLİNMEZ. Pose'da 3B keypoint TEK KAYNAĞI `pose/talon_keypoints.json` (Berat, doğrulanmış);
  bizim `talon_pose_estimator` onu OKUR (gömülü tablo bayrakla yedek).

## VİDEO ÇIKTILARI ARAYÜZÜ (10 zorunlu çıktı — main'den 2026-07-06 merge ile taşındı)
Şartnamenin **videoda görünür 10 teknik çıktısı** arayüzde karşılanır. TEMEL KURAL:
tüm yeni sinyaller `web/server.py`'deki **`_gorev_izle()` görev izleyicisinde**, `beyin`'in
VAR OLAN alanlarından **kenar-tespitiyle** (önceki tik ↔ bu tik) türetilir → güdüm kodu
DEĞİŞMEZ (kural 8: izleyici "durum değişti mi?" karşılaştırmasından ibaret).
- **Payload** (`build_telemetry`): `olaylar`, `gnss`, `gudum` (+aktif GPS profili), `takip`,
  `gorev` anahtarları; `gorsel.gorev_sonu` izleyici latch'inden beslenir.
- **Arayüz eşlemesi (bizim arayüz baz):** FPV altında mini-harita (avcı/ham/J-temiz izleri,
  KESİNTİ işareti) + görev olay günlüğü; sağ sütunda BOZUK GNSS kartı (KESİNTİ rozeti,
  paket yaşı, J düzeltme) + GÖREV kartı (faz, profil, en yakın mesafe, TAKİP rozeti);
  "VURUŞ!" uçucu banner + kalıcı "GÖREV BAŞARILI" ekranı (mevcut basariEkran).
- **Takip-ID:** merge uyarlaması — main'in sentetik ID makinesi yerine GERÇEK ByteTrack
  `track_id`'si kullanılır; kayıp/yeniden eşikleri `Cfg.VIS_STALE_S`/`VIS_LOST_TO_GPS_S`.
- **VURUŞ latch mesafesi:** J-temiz kestirim; DEV koşusunda (DEV-ONLY çit içinde,
  `dev_truth.mesafe_m` üzerinden) gerçek 3B; **ham ASLA** (sahte vuruş). SERT AYRIM korunur:
  paketlenmiş kodda çit söküldüğünden latch daima J-temizdir.

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

## POZ KESTİRİMİ (merge 2026-07-06 sonrası TEK HAT)
`models/talon_pose.pt` (Berat, yolo11m-pose, 6 keypoint) bizim algı hattına bağlandı:
- **3B keypoint TEK KAYNAĞI: `pose/talon_keypoints.json`** (sim'de doğrulanmış, flip_idx'li).
  `detection/talon_pose_estimator.sema_berat_yukle()` bunu okur ve **`berat_json`
  şemasını** kurar: sıra = `pose/poz_cozucu.EGITIM_SIRASI` (model çıktı sırası, 87 karede
  deneysel; **pred[k]→json[EGITIM_SIRASI[k]]**), pivot = `MESH_PIVOT_OFFSET_CM`
  (+11.76 cm ileri → tvec = kamera→actor origin = `get_target_location`, telemetriyle
  doğrudan kıyaslanır). Gömülü şemalar (`kuyruk_ucu`/`motor`) SİLİNMEDİ — yaml `sema`
  bayrağıyla seçilebilir yedek (JSON okunamazsa da düşülür).
- `models/talon_pose.yaml`: `sema: berat_json`, `conf: 0.35` (main canlı testi: 0.20'de boş
  gökyüzüne uyduruyor). Model registry'den (arayüz 🧠 MODEL paneli) hot-swap ile aktifleşir;
  aktif olunca bbox+keypoints AYNI ağdan gelir → ByteTrack + PnP + OIPN zinciri çalışır.
- main'in gözlemci hattı (`detection/poz_tespit.py` + `pose/` araçları) repo'da DURUYOR
  (silinmedi); bizim server bunları çağırmaz — tek aktif model mimarisi bizde registry'dir.
- Kalite (Berat ölçümü, eğitim karelerinde İYİMSER): mesafe medyan %8 / yaw medyan 6°
  (<10 m iyi); 15 m+ şişer → **terminal faz (≈4-12 m) aracı**.

## SAHTE TESPİT MODU (main'den 2026-07-06 merge ile taşındı — güdüm geliştirme aracı)
YZ modeli olgun değilken görsel güdüm algoritması geliştirmek için: arayüzdeki
**"🖱️ Sahte Tespit (Mouse)"** butonu açıkken, görev sırasında FPV'de mouse BASILI
TUTULAN nokta `/api/sahte` üzerinden server'a akar ve `dedektor_dongusu`'nde asıl algı
çıktısının YERİNE geçer (aynı det sözlüğü → `beyin.set_gorsel_tespit`; o döngüde
inference koşulmaz, ByteTrack sahteyle kirlenmez). Failsafe: mesaj 0.6 s kesilirse
otomatik düşer. Overlay'de MACENTA bbox + "[SAHTE/MOUSE]" etiketi (yeşil = model).
Buton kapalıyken sistem tamamen eskisi gibi. **Video isteri gereği (manuel işaretleme
YASAK) yarışma/video koşusunda KULLANILMAZ; teslim öncesi komiteye giden paketten
kaldırılır** (kullanıcı kararı 2026-07-06).

## BEKLEYEN İŞ
- **Merge sonrası sim regresyonu:** iki profil de sim'de uçurulup teyit edilecek —
  (a) varsayılan standoff (GPS_TERMINAL_STRIKE=False): 5 m arkada/altta pace + kamera
  çerçeveleme; (b) GPS_TERMINAL_STRIKE=True: eski intercept+ram birebir; (c) sahte
  tespitle GORSEL_TAKIP zinciri; (d) talon_pose.pt hot-swap ile PnP/berat_json canlı doğrulama
  (reproj_err ~makul, mesafe telemetriyle uyumlu mu).
- **Poz çıktısı güdüme girsin mi?** (kamera-mesafeli angajman / hedef-yaw lead) — talon_pose.pt
  canlıda doğrulanınca kararlaştırılacak (OIPN zaten PnP-geçerliyken devrede).
- **Arayüz deseni:** yeni sinyaller `server.py` `_gorev_izle()`den türetilip `build_telemetry`
  payload'ına eklenir + `index.html`'de kart/overlay (güdüm koduna dokunmadan).
- Video anlatım metinleri (ilk 3 dk + son 3 dk) — kullanıcı EN SONDA isteyecek; tüm metinler
  takır takır verilecek.

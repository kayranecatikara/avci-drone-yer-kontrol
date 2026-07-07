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
- **Uçuş pipeline'ı (`detection/`, `guidance/`, `fusion/`, `iletisim/`, `web/`, `main.py`)
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
  (ARAMA/YAKLASMA) beslemesini değiştirir, OTO/GPS/GÖRSEL anahtarına ve
  GORSEL_TAKIP sonrasına dokunmaz. GERÇEK (DEV) aktifken arayüzde kırmızı
  bant çıkar; uçuş CSV'sine `hedef_kaynak` (filtre/gercek) yazılır.
- **Truth kullanan her scriptin başına şerh:** "GELİŞTİRME/DOĞRULAMA ARACI —
  görev uçuşunda ve değerlendirme koşusunda kullanılmaz."
- **Görev zinciri değişmez:** bozuk hedef GPS → fusion filtresi → midcourse
  yaklaşma; görsel temas sonrası hedef konumu YALNIZCA görsel (bbox/PnP).

## TESLİM PAKETİ KURALI
Yarışmaya gidecek kod paketi = uçuş pipeline'ı (`main.py`, `detection/`,
`guidance/`, `fusion/`, `iletisim/`, `web/`, `sdk/`, `models/`, requirements, README
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
4. Görsel güdüm fazına (YOLO/CV) temiz devret (YAKLASMA→GORSEL_TAKIP devri). Terminal vuruş görsel fazın işi.

## SİSTEM MİMARİSİ (modül → şartname teslim eşlemesi)
- `drone_sdk.py`        → simülasyon I/O (input/telemetri); şartname "input.py" muadili.
- `inovasyonlu_j_v2.py` → sensör füzyonu / filtreleme / tahmin (GNSS temizleme + hız kestirimi).
- `ana_kontrol.py`      → güdüm ve karar mekanizması — **MERGE 2026-07-07: main BAZ**
  (A/B kararı: `docs/AB_KIYAS_KARAR_20260707.md`). Öngörülü yönelim + ARAMA→KILIT FSM;
  görsel yasa TEK: `guidance/png_gorsel.py` (PNG). Bizim IBVS/OIPN + GPS_TERMINAL_STRIKE
  yolu bu merge ile devre dışı (IBVS dosyası silindi; main 2026-07-06 temizliği).
- `server.py`+`index.html` → görev arayüzü, telemetri, **10 video isterinin görünürlüğü**;
  MERGE 2026-07-07: main'in server+arayüzü BAZ (olay günlüğü + görev izleyici server'da;
  ID/faz/vuruş overlay'i index'te). GÜDÜM KODUNA DOKUNULMAZ deseni geçerli.
- `detection/gorsel_tespit.py` (best.pt YOLO @1280) → görsel tespit.
  **GÜDÜM KODU HARİTASI: `guidance/GUDUM_HARITA.md`**.
- **Bizim hat (TAŞINACAK-ADAY; runtime dışı ama repoda + testli):** `detection/`
  (takip=ByteTrack+gyro-CMC, algi_hatti, model_yonetici=registry, talon_pose_estimator=PnP),
  `guidance/kilit_kurali.py` (**§6.1.4 ZORUNLU taşınacak**), `iletisim/hakem_istemci`,
  `guidance/gudum_yasasi.py` (APN+OIPN — emekli aday). Taşıma planı karar dokümanında.
- Pose 3B keypoint TEK KAYNAĞI `pose/talon_keypoints.json` (Berat, doğrulanmış);
  koşu-zamanı üçlüsü paketlenir. `models/talon_pose.pt` merge'de KORUNDU (main silmişti;
  gözlemci/terminal aracı olarak duruyor).

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
- **Overlay gecikmesi (2026-07-07, main 152a7bc bizim hatta PORT):** bbox/keypoint overlay'i
  hızlı **`/api/gorsel`** kanalından (~15 Hz `gorselTick`) beslenir; server tespite
  yakalama-anı yaşı (`yas_s`, `kare_uretici`'nin `tp` damgasından) + normalize hız
  (`vx,vy` 1/s, `_ui_hiz_damgala`: aynı track_id şartı) ekler; istemci kutu+iskeleti yaş
  kadar İLERİ çizer (≤300 ms lead). Kanal düşerse telemetri tespitine geri düşer.
  `algi.adim(t=kare_tp)` ile takip dt + PnP low-pass da yakalama saatine geçti. Güdüm
  kodu DEĞİŞMEDİ (yalnız UI yolu).

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

## POZ KESTİRİMİ — BİZİM PnP HATTI (TAŞINACAK-ADAY; runtime dışı)
Registry tabanlı hat (`talon_pose_estimator` + ByteTrack + OIPN zinciri) merge 2026-07-07
ile runtime dışı kaldı; PNG'ye kamera-mesafe girdisi gerektiğinde taşınacak aday budur:
- **3B keypoint TEK KAYNAĞI: `pose/talon_keypoints.json`** — `berat_json` şeması:
  sıra **pred[k]→json[EGITIM_SIRASI[k]]** (`pose/poz_cozucu.EGITIM_SIRASI`), pivot
  `MESH_PIVOT_OFFSET_CM` (+11.76 cm → tvec = `get_target_location` ile kıyaslanır).
- `models/talon_pose.yaml`: `sema: berat_json`, `conf: 0.35`. Kalite (Berat ölçümü,
  İYİMSER): mesafe medyan %8 / yaw 6° (<10 m iyi) → **terminal faz (≈4-12 m) aracı**.

## SAHTE TESPİT MODU (main'in aracı — güdüm geliştirme)
YZ modeli olgun değilken görsel güdüm testi: arayüzdeki **"🖱️ Sahte Tespit (Mouse)"**
açıkken FPV'de mouse BASILI TUTULAN nokta `/api/sahte` ile asıl algı çıktısının YERİNE
geçer; 0.6 s failsafe; MACENTA bbox + "[SAHTE/MOUSE]". **Video isteri gereği (manuel
işaretleme YASAK) yarışma/video koşusunda KULLANILMAZ; teslim paketinden kaldırılır**
(kullanıcı kararı 2026-07-06).

## CANLI TESPİT HATTI (main 2026-07-06 — kök neden analizi + 4 düzeltme; AKTİF HAT)
Canlı görevde dedektör kördü (87.6 sn'de 1 tespit; aynı görüntüde offline %62.5
kilit-eşiği-üstü). Kök neden: mss EKRAN yakalar; oyun penceresi Chrome'un arkasında
kalınca dedektöre masaüstü/tarayıcı pikseli gitti (FPV paylaşımı pencere-İÇERİĞİ
gösterdiğinden kullanıcı fark etmez). Kanıt/teşhis: `veri/ucus_log_*.csv`'de
`vis_gordu/vis_conf` + gerçek-mesafe binleme; dedektör gözü = `/api/frame`.
Düzeltmeler (server.py):
1. `PENCERE_YAKALA_AKTIF=True` — windows-capture pencere-içeriği (occlusion-proof).
   Sorun çıkarsa False → mss fallback (o zaman oyun penceresi ÖNDE tutulmalı).
2. Dedektör kareyi DOĞAL çözünürlükte alır; `CAM_MAX_WIDTH=960` küçültme yalnızca
   FPV JPEG akışında (`fpv_jpeg`). (960→1280 çift örnekleme uzak hedefi öldürüyordu.)
3. `UI_CONF_MIN=0.25` predict eşiği; **güdüm kapısı**: `det_beyin` yalnız
   conf≥`VIS_CONF_MIN` beyne gider (kilit/takip/güdüm davranışı DEĞİŞMEDİ).
   Zayıf tespit arayüzde TURUNCU kesikli çizilir (`gorsel.conf_esik` telemetride).
4. `POZ_HER_N=3` — poz inference'i seyrek (gözlemci-only özellik GPU'nun yarısını
   yiyip dedektörü ~5-7 Hz'e düşürüyordu → takip delikleri).
Beklenti (mesafeye bağlı, normal): 0-10 m ~%70-80, 15-20 m ~%45+, 60 m+ %0 (hedef
birkaç piksel). "Video gibi kesintisiz" görünüm UI'daki 0.25 eşiğiyle gelir.
Model (7 Tem 2026): `models/best.pt` = best_son (19 MB, detect/talon, imgsz=1280).
Referans kayıtta eski 40 MB modele karşı kilit-eşiği-üstü %62.5→%73.0 ve %33 hızlı
(640'ta çöküyor — imgsz 1280 kalacak; kıyas: scratchpad model_kiyas, 7 Tem).

## POZ KESTİRİMİ (2026-07-04'te eklendi — GÖZLEMCİ modda)
`models/talon_pose.pt` (yolo11m-pose, 6 keypoint) + PnP artık pipeline'da:
- `detection/poz_tespit.py` (PozDedektor) + `pose/poz_cozucu.py` (PnP+EMA; **EGITIM_SIRASI
  ve MESH_PIVOT_OFFSET kritik** — POSE_REHBERI "EĞİTİM SIRASI" bölümü).
- `server.py` dedektör döngüsü best.pt'ye İLAVE koşar; **beyin/güdüm girdisi DEĞİŞMEDİ**
  (best.pt bbox akışı aynen). Telemetri: `gorsel.poz` + `gorsel.poz_hazir`.
- Arayüz: FPV'de iskelet + "MESAFE (KAM) / HEDEF YAW" satırları + 📐 POZ KESTİRİMİ kartı
  (kamera vs gerçek kıyas). Video isteri "GNSS bağımlılığının azalması" kanıtına birebir.
- Model: **v3 (5 Tem 2026)**, models/best.pt ile AYNI dosya (talon_pose.pt kopyası;
  bbox+poz iki ayrı inference — tekleştirme ileriki optimizasyon). imgsz=1280.
  EGITIM_SIRASI=[0,1,2,5,3,4] sira_bul.py ile YENİDEN doğrulandı (5 Tem).
- Kalite v3 (eğitim karelerinde İYİMSER, degerlendir_foto): PnP çözüm %61, tespitsiz
  %10; mesafe MAE 0.84 m / medyan |hata| %6.1 / BIAS −0.37 m; yaw MAE 12° (medyan 3.7°).
  15-20 m bini artık %7 (eski model %89'du). Güdüme besleme SONRAKİ adım (kullanıcı onayı).

## BEKLEYEN İŞ
- **MERGE 2026-07-07 KALANLARI (sırayla):**
  1. **SERT AYRIM temizliği (paket_kontrol şartı):** main'den gelen `ana_kontrol.py`'de
     "gercek" kaynak yolu GÜDÜM İÇİNDE truth okuyor (`get_debug_truth`, `_gercek_hedef_hiz`,
     `true_*` debug alanları) → bizim `set_hedef_kaynagi`/dev_truth dikişine çevrilecek;
     `server.py`+`index.html`'deki çitsiz truth/gercek noktaları DEV-ONLY çite alınacak.
  2. **Kilit §6.1.4 taşıma:** main'in kilit/ATIS kuralı şartnameyle kıyaslanacak; eksikse
     bizim `guidance/kilit_kurali.py` + `iletisim/hakem_istemci` main FSM'ine bağlanacak.
  3. **ByteTrack kararı (ölçerek):** main tek-kutu argmax (A/B'de 72 kayıp kenarı/30 ID);
     bizim `detection/takip.py` (ByteTrack+gyro-CMC) aday.
  4. **Test uyumu:** FSM/faz testleri main güdümüne göre güncellenecek (eski hat testleri
     TAŞINACAK-ADAY modülleriyle yaşamaya devam eder).
  5. **ab_kiyas regresyonu:** merge sonrası ≥ main'in bugünkü seviyesi (1/3) doğrulanacak.
  6. **Kayra onayı → push** (merge yerel; `docs/AB_KIYAS_KARAR_20260707.md` ile birlikte).
- **PNG tune ile ıskalamayı kapatmak** (İster 9/10; main 6 Tem log analizi: handoff dikey
  açığı + kapanma hızı; `araclar/gorsel_episode_analiz.py` + TUNE_REHBERI §9). A/B bulgusu:
  ana başarı kaldıracı MODEL (HUD-FP + uzak menzil conf — `docs/AB_KIYAS_KARAR_20260707.md` §7).
- **Görsel güdüm fazı — YZ modelleri / ekstra özellikler:** güçlü tespit/tracking, poz/mesafe
  kestirimi, kamera-tabanlı terminal vuruş eklendikçe arayüz de genişler. Desen HAZIR:
  yeni sinyal `server.py` `_gorev_izle()` → `build_telemetry` → `index.html` kart/overlay
  (güdüm koduna minimum dokunuş). Sıradaki karar: poz çıktısı güdüme girsin mi
  (kamera-mesafeli angajman / hedef-yaw lead)?
- Video anlatım metinleri (ilk 3 dk + son 3 dk) — kullanıcı EN SONDA isteyecek; tüm metinler
  takır takır verilecek.

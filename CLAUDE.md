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

## ⛔ KATI KURAL — GÖRSEL FAZDA GPS/J YASAK (diskalifiye sebebi)
**Görsel temas SAĞLANDIKTAN SONRA (GORSEL_GUDUM) hareket komutu YALNIZCA GÖRSEL VERİDEN
türetilir.** Yön, menzil, kapanma hızı, dikey ayrım — HEPSİ bbox/LOS/kameradan. GPS/GNSS
ya da J-filtre kestirimi (`son_temiz`, `son_z_anlik`, `son_xy_anlik`, `son_hiz`) bu fazda
komuta GİRMEZ — ne yön ne büyüklük olarak. **Yarışma kuralı: görsel temastan sonra GPS
verisiyle aracı yönlendirmek DİSKALİFİYEDİR.** (2026-07-07: `_j_fallback` menzil/Vc yedeği
ve dikey ayrımın J-irtifa yolu KALDIRILDI; dikey ayrım artık `R·u_hat[2]` = tamamen görsel.)
GPS/J YALNIZCA görsel-öncesi fazda (ARAMA/KILIT yaklaşma) kullanılır. **Görsel güdüm için
ASLA GPS/J tabanlı bir çözüm önerme.**

## SİSTEM MİMARİSİ (modül → şartname teslim eşlemesi)
- `drone_sdk.py`        → simülasyon I/O (input/telemetri); şartname "input.py" muadili.
- `inovasyonlu_j_v2.py` → sensör füzyonu / filtreleme / tahmin (GNSS temizleme + hız kestirimi).
- `ana_kontrol.py`      → güdüm ve karar mekanizması (öngörülü yönelim + ARAMA→KILIT FSM).
- `server.py`+`index.html` → görev arayüzü, telemetri, **10 video isterinin görünürlüğü**
  (aşağıdaki bölüm). Olay günlüğü + görev izleyici `server.py`'de; ID/faz/vuruş overlay'i
  index.html'de. GÜDÜM KODUNA DOKUNULMAZ (bkz. VİDEO ÇIKTILARI ARAYÜZÜ).
- `detection/gorsel_tespit.py` (best.pt YOLO) → görsel tespit; `guidance/png_gorsel.py` →
  görsel PNG güdüm (TEK görsel yasa). Teslim .zip'i bu modülleri + model dosyasını içermeli.
- **GÜDÜM KODU HARİTASI: `guidance/GUDUM_HARITA.md`** (2026-07-06 temizliği: IBVS,
  GPS terminal strike, `_kamera_kontrol`/`calistir`/`ozet` silindi; Cfg faz-bantlı).

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

## CANLI TESPİT HATTI (2026-07-06 — kök neden analizi + 4 düzeltme)
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
**PENCERE-YAKALAMA WATCHDOG (2026-07-07):** "oyunu açınca bazen dedektör farklı yeri görüyor,
restart düzeltiyor" → kök neden: windows-capture bir kez bağlanıp bir daha kontrol edilmiyordu;
oyun penceresini yeniden yaratınca (loading→PLAY) / WGC donunca / başlangıçta yanlış pencereye
bağlanınca `on_closed` tetiklenmiyor → `_control` dolu kalıyor ama kare gelmiyor/bayatlıyor →
mss'e düşüp yanlış yeri görüyor. Çözüm: `PencereYakala.yeniden_baglanmali(stale_s)` — (a) kare
bayat, (b) hiç kare gelmedi (yanlış pencere), (c) bağlı HWND artık oyun penceresi değil →
`connection_manager` `durdur()+baslat()` ile TAZE yeniden bağlanır (restart gerekmez). Kare
damgası `on_frame_arrived`'da. UI: dedektör mss'e düşünce FPV'de turuncu "⚠ KAMERA: mss" uyarısı
(`gorsel.kare_kaynak`). Birim test: watchdog 5/5 koşul.

Model (7 Tem 2026): `models/best.pt` = best_son (19 MB, detect/talon, imgsz=1280).
Referans kayıtta eski 40 MB modele karşı kilit-eşiği-üstü %62.5→%73.0 ve %33 hızlı
(640'ta çöküyor — imgsz 1280 kalacak; kıyas: scratchpad model_kiyas, 7 Tem).

## DİKEY = HEDEF ALTINDA SABİT MESAFE (2026-07-07 v4, alttan-yaklaşma)
Kullanıcı: araç hedefin ÜSTÜNE çıkıyor → arka plan zemin → YOLO hedefi zeminden ayıramıyor →
takip kopuyor; "hep alttan yaklaşıp alttan vurmalıyız". **Kök neden (geometrik):** kadraj-pozisyonu
(v3 piksel-ey) sabit AÇI tutuyordu; kapanınca (R↓) dünya dikey ayrımı `Δh=R·sin(elev)` KÜÇÜLÜR →
araç hedefin irtifasına tırmanır. **Çözüm:** dikeyi dünya AYRIMIYLA kontrol et — araç hedefin
irtifasından `VIS_DH_TARGET` (400 cm) kadar ALTTA kalsın. Kapandıkça hep altta → hedef kadrajda
yukarı kayar (alttan yaklaşma) → gökyüzü arka plan → tespit kararlı → TERMINAL'de alttan vuruş.
Araç üste çıkarsa (Δh<0) güçlü alçalma. **Dikey ayrım TAMAMEN GÖRSEL: `dh = R·u_hat[2]`**
(R pinhole/bbox'tan, u_hat[2] LOS'tan) — GPS/J YOK (yarışma kuralı; 7 Tem J-irtifa yolu kaldırıldı).
`png_gorsel._komut`,
`VIS_DH_TARGET`/`VIS_DH_BAND` (Cfg+slider; `VIS_EY_REF/K` panelden çıktı). YALNIZ TAKIP; TERMINAL
saf PN. UI: turuncu çizgi → "HEDEF ALTINDA: X.X m" göstergesi. Test: `tests/test_lookup_geometri.py`
(kapalı-döngü: kapanırken dh sabit 4m, hedef kadrajda yukarı kayar). GPS `LOOKUP_ELEV_DEG` z_ref'te
kaldı (handoff'ta altta). Kapalı-döngü kanıt: dh 400→410 cm sabit, ey +0.32→−0.52.

## DİKEY ÇERÇEVELEME — PİKSEL (2026-07-07 v3, alttan-kaçış çözümü — v4 ile DEĞİŞTİRİLDİ)
Hedef kadrajın ALTINDAN kaçıyordu. Kök neden: dikey look-up **dünya-elevation açısını** tutuyordu
ama kamera 25° tilt kalibrasyonu DOĞRULANMAMIŞ (placeholder) → hedef sistematik alçak oturuyordu;
ayrıca yaklaşırken kapanma feedforward'ı (`v_close·u_z`) aracı hedefe tırmandırıp hedefi kadrajda
aşağı itiyordu. Çözüm: dikeyi **doğrudan gözlenen piksel `ey`'den** kontrol et (tilt'ten bağımsız).
Hedefi `VIS_EY_REF` (turuncu HEDEF ÇİZGİSİ, artık AKTİF) yüksekliğinde tut: `ey>ref` (alt) → ALÇAL
(→ hedef yukarı kalkar), `ey<ref` → TIRMAN. `VIS_EY_K` = tutma gücü, `VIS_LOOKUP_VZ` = hız tavanı.
Kapanma feedforward'ının dikey bileşeni artık YALNIZ TERMINAL'de (takipte çerçeveleme baskın).
`png_gorsel._komut` (ey param), `VIS_EY_REF` 0.20 default + `VIS_EY_K` 2.5. `LOOKUP_ELEV_DEG` hâlâ
GPS-yaklaşma z_ref'inde (handoff altında kalma) kullanılıyor. Test: `tests/test_lookup_geometri.py`
(piksel yön + kapalı-döngü ey yakınsama). UI çizgisi tam-genişlik "↕ HEDEF ÇİZGİSİ".
**Tune paneli sadeleştirildi (13 slider, ince adımlı):** ANA (VIS_TRACK_TILT, VIS_TAKIP_VC,
VIS_K_YAW_LEAD, VIS_EY_REF, VIS_SOFTSTART_S) + İNCE. Belirti→knob tablosu `TUNE_REHBERI.md` başında.

## GÖRSEL TAKİPTE AŞIRI ROLL → CLUTTER (2026-07-07, Gemini video #2 + log)
Soft-start handoff sıçramasını çözdü ama steady-state takip manevrası hâlâ agresifti: log'da
`drone_roll` bank açısı **max 47°**, `|roll_cmd|` p90 0.53. Bu bank hedefi kadrajdan atıyor +
gövdeye sabit 25°-eğik kamerayı YERE çeviriyor → clutter → YOLO sahte pozitif (yerdeki nesne
"talon 0.27"). Araç 1 m'ye kapanıyor ama kilit dolmuyor (roll hedefi off-center atıyor).
**İçgörü:** takipte amaç ÇERÇEVELEME (bunu **yaw** yapar, bank gerektirmez); roll/pitch intercept
içindir, takipte zararlı. Çözüm: takip fazında (vurus_izin=False) PN pitch/roll yetkisi
`VIS_TRACK_TILT`=0.30 (TERMINAL'de tam `VIS_PN_TILT`=0.8). `clamp*tilt` yapısı max komut=tilt →
bank sınırı. Yaw/dikey/kapanma dokunulmadı. Test: `test_png_gorsel.test_takip_fazi_dusuk_manevra_yetkisi`.
Slider: `VIS_TRACK_TILT`. Bekleyen: hâlâ clutter varsa bank-to-pitch komp. (Gemini D3).

## HANDOFF TRANSİYENTİ — YUMUŞAK BAŞLANGIÇ (soft-start, 2026-07-07, Gemini video analizi)
Gemini uçuş videosu analizi: kilit anında **hedef MERKEZDEYKEN** araç ani sert roll+pitch
yapıp hedefi üst-sol köşeden atıyordu → **handoff transiyenti** (mod değişiminde kontrol
süreksizliği; steady-state gecikme DEĞİL — hata küçükken büyük komut = geçiş sıçraması).
Çözüm: GORSEL_GUDUM'a girişte ilk `VIS_SOFTSTART_S` (1.5 sn) boyunca komut (thr/pitch/roll/yaw)
büyüklüğü `VIS_SOFTSTART_MIN` (0.20) → 1.0 lineer rampalanır (`_softstart_gain`+`_ramp`,
`_gorsel_giris_t` giriş anı). Geçiş sarsıntısız; steady-state yetki (yaw-lead, kenar-merkezleme)
KORUNUR. `_gorsel_giris_t` giriş/çıkışta set/reset (OTO+manuel handoff, GPS revert, kaynak/vismode).
Slider: `VIS_SOFTSTART_S`, `VIS_SOFTSTART_MIN`. Test: `tests/test_kilit_takip.py`. NOT: Gemini
ikincil olarak latency kompanzasyonu (Smith predictor) önerdi — transiyent birincil; gerekirse
sonraki adım. Yaw rate cap (YAW_MAX) global düşürülmedi (kenar-kaybı yüksek yaw ister); ramp
handoff'ta zaten kısıyor.

## KİLİT DOLDURMA — NAZİK YAKLAŞMA + YAKIN-MENZİL YAPIŞKANLIĞI (2026-07-07)
Log analizi (14:15): araç kapanabiliyor (bir epizot 38→5.1 m'ye 3.5 sn'de) ama **kilit
menziline hızla (≈9.4 m/s) dalıp tam orada hedefi kaçırıyor ve GPS'e revert ediyor, kilit
dolamadan** (max 0.58 sn / 5 sn). İki neden: hızlı kapanma (motion blur/ejeksiyon) + look-up
tırmanışı (3 m/s) kapanmaya yetişemiyor (`ey` −0.23). İki düzeltme:
1. **TAKİP nazik yaklaşma (`VIS_TAKIP_VC`=300 cm/s):** TAKİP fazında kapanma tavanı VC_CAP
   (12 m/s) yerine 3 m/s → araç dalmadan ~6 m'ye park eder, hedef kadrajda kalır, look-up
   yetişir, kilit dolar. (`png_gorsel._komut` TAKİP dalı; slider.)
2. **Yakın-menzil yapışkanlığı:** `pngg.R_f < VIS_STICKY_R` (10 m) iken kayıp eşikleri uzar
   (`VIS_DEADRECKON_S_NEAR`=1.5, `VIS_LOST_TO_GPS_S_NEAR`=3.0) → kilit menzilinde kısa tespit
   blip'inde GPS'e dönüp kapanma ilerlemesini çöpe atmaz. (`ana_kontrol._gorsel_guduum`.)
Test: `tests/test_kilit_takip.py` (yakın yapışkan / uzak normal revert). UI: GPS fazında bbox
artık SADE nötr (kırmızı/yeşil YOK); kilit renklendirmesi yalnız GORSEL_GUDUM'da.

## PERVANE YANLIŞ-POZİTİF MASKESİ (2026-07-07 — clutter değil, kendi aracımız)
Avcının KENDİ pervanesi arada bir "uçak" olarak algılanıyor (dedektör sınıf-agnostik
en-yüksek-conf seçer → bir karede pervane hedefi bastırabilir). Pervane kadrajda SABIT
konumda. Çözüm: `Cfg.PROP_MASKE` = normalize [(x0,y0,x1,y1),...] dikdörtgen listesi;
merkezi maskede olan kutular `detection/gorsel_tespit.tespit_et` içinde **argmax ÖNCESİ**
elenir (tüm kutular maskeliyse o kare None). Değer (7 Tem log analizi): 60 kesin yanlış-poz
(gerçek hedef 126 m uzak/kadraj dışı iken conf~0.48 tespit) **sağ-altta** kümelendi
(ex~0.75-1.0, ey~0.25) → varsayılan `[(0.80,0.55,1.0,0.95)]`. Server maskeyi `Cfg`'den
CANLI okur (`dedektor.tespit_et(bgr, maske=Cfg.PROP_MASKE)`); arayüz FPV'de kırmızı tarama
+ "PERVANE" etiketiyle çizer (kullanıcı doğrular/rafine eder). Log'a ham `vis_cx` eklendi
(EMA'sız → köşe kümesi kesin bulunur). Test: `tests/test_prop_maske.py`. RAFİNE: canlı
FPV'de maske pervaneyi tam örtmüyorsa `PROP_MASKE`'yi düzenle (sol-üstte zayıf 2. küme de var).

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
- **Görsel güdüm fazı — YZ modelleri / ekstra özellikler:** görsel güdüm algoritmasına yapay
  zeka modelleri ve ek yetenekler eklenecek (ör. daha güçlü tespit/tracking, hedef sınıf/ID
  sürekliliği, poz/mesafe kestirimi, kamera-tabanlı terminal vuruş). **Bunlar eklendikçe
  arayüzde de karşılık gelen değişiklikler yapılacak** — yeni panel/rozet/telemetri alanı.
  Arayüz mimarisi buna HAZIR: yeni sinyalleri `server.py` `_gorev_izle()` içinde `beyin`'den
  okuyup `build_telemetry` payload'ına ekle + `index.html`'de kart/overlay çiz (güdüm koduna
  minimum dokunuş; VİDEO ÇIKTILARI ARAYÜZÜ bölümündeki desen).
  → İLK ADIM ATILDI: poz kestirimi gözlemci modda entegre (üstteki bölüm). Sıradaki karar:
  poz çıktısı güdüme girsin mi (kamera-mesafeli angajman / hedef-yaw lead)?
- **Otonom angajman/vuruş (İster 9/10):** `Cfg.AUTO_VISUAL_HANDOFF=True` AÇIK — OTO uçuşta
  yakınlık+YOLO kilidiyle görsel faza otonom geçiyor; terminal vuruş kamera verisiyle PNG
  yasasında (`guidance/png_gorsel.py`). GPS_TERMINAL_STRIKE yolu 2026-07-06'da SİLİNDİ
  (vuruş görsel fazın işi). Kalan iş: PNG tune ile ıskalamayı kapatmak (6 Tem log analizi:
  handoff dikey açığı + kapanma hızı; `araclar/gorsel_episode_analiz.py` + TUNE_REHBERI §9).
- **ÖNGÖRÜLÜ (LEAD) YAW EKLENDİ (2026-07-07, kadraj-kaybı çözümü):** canlı log analizi
  (7 Tem) — görsel fazın %71'inde hedef görülmüyor; kayıpların %100'ü hedef KENARDA (ex~0.9),
  ex ortalaması +0.49 (kamera geriden kovalıyor), yaw kayıp anlarının %42'sinde doygunlukta.
  Kök neden: salt-P yaw hareketli hedefi ortalayamıyor. Çözüm: `yaw += SIGN·VIS_K_YAW_LEAD·omega_z`
  (LOS azimut hızı ileri-besleme; PNG zaten omega hesaplıyor) + `YAW_MAX` 0.45→0.60. Kapalı-döngü
  test (`tests/test_yaw_lead.py`): ort |ex| 0.79→0.31. Slider: `VIS_K_YAW_LEAD`. Sıradaki: canlı
  görevde yeni log alıp `ex` ortalamasını doğrula; hâlâ kaçırıyorsa look-up alçalma dikey ejeksiyonu
  (öneri #3) + kayıpta yeniden-merkezleme (#4).
- **LOOK-UP GEOMETRİSİ EKLENDİ (2026-07-07, aşağı-bakma/clutter çözümü):** avcı hedefin
  ÜSTÜNDEN takip edince kamera aşağı bakıp clutter'da tespiti kopartıyordu; ALTTAN bakış
  gökyüzü silueti + maksimum planform → güvenilir. Kısıt: LOS yükseliş açısı ≥ `LOOKUP_ELEV_DEG`
  (ε=8°). Menzil-ölçekli (sabit Δh yetmez): GPS fazı `z_ref = z_hedef − max(APPROACH_ALT_OFFSET,
  tan(ε)·d_h)` + taban `LOOKUP_MIN_ALT_CM`; görsel faz `u_hat[2]=sin(elev)` < sinε iken alçalma
  bias (`VIS_LOOKUP_VZ`, yalnız TAKIP/YAKLAŞMA, TERMINAL saf PN). UI PN kartında "LOS yükseliş"
  satırı + 2 slider. Detay: `guidance/GUDUM_HARITA.md` §6.5; test: `tests/test_lookup_geometri.py`.
  **v2 (7 Tem, log analizi sonrası):** tek-yön alçalma bias'ı hedefi ÜST KENARDAN kaçırıyordu
  (log: ey_ort −0.19, %32 alçalma, dikey artık baskın kayıp ekseni). Çözüm: **çift-yönlü
  dikey setpoint** — `elev<ε` alçal, `elev>ε` TIRMAN (= dikey merkezleme, öneri #2). Tek terim
  hem look-up hem dikey çerçeveleme. ε 8→6°, `VIS_LOOKUP_VZ` 500→300. Kapalı-döngü test: elev
  0→ε yakınsar, kararlı (7/7).
- **KİLİTLENME İSTERİ EKLENDİ (2026-07-07, şartname 6.1.2/6.1.4):** görsel fazda alt-FSM
  `beyin.gorsel_faz`: YAKLASMA → (bbox ekseni ≥ `VIS_LOCK_PCT`=0.06) → TAKIP (PNG menzil
  tutar, `VIS_HOLD_PCT`; commit-freeze kapalı) → (10 sn pencerede kümülatif ≥5 sn kilit:
  merkez AV %25-75/%10-90 içinde + boyut eşiği; `kilit_ok` latch) → TERMINAL (eski tam
  kapanma+vuruş). ANGAJMAN faz çipi artık TERMINAL şartına bağlı. UI: KİLİTLENME kartı
  (5/10 sn sayaç), kilitte bbox düz KIRMIZI #FF0000 ≤3px (şartname video kuralı).
  Harita: `guidance/GUDUM_HARITA.md` §2; testler: `tests/test_kilit_takip.py` (9/9).
- Video anlatım metinleri (ilk 3 dk + son 3 dk) — kullanıcı EN SONDA isteyecek; tüm metinler
  takır takır verilecek.

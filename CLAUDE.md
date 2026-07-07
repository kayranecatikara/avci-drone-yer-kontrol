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
türetilir.** GPS/GNSS ya da J-filtre kestirimi (`son_temiz`, `son_z_anlik`, `son_xy_anlik`,
`son_hiz`) bu fazda komuta GİRMEZ — ne yön ne büyüklük olarak. **Yarışma kuralı: görsel
temastan sonra GPS verisiyle aracı yönlendirmek DİSKALİFİYEDİR.** (2026-07-07 v7: tek
görsel yasa `ibvs_gorsel.hesapla(det, p)` — imzasında konum/hız/rotasyon parametresi bile
YOK; kural YAPISAL sağlanır, kilit testi: `test_ibvs_gorsel.test_gps_siz_imza`.)
GPS/J YALNIZCA görsel-öncesi fazda (ARAMA/KILIT yaklaşma) kullanılır. **Görsel güdüm için
ASLA GPS/J tabanlı bir çözüm önerme.**

## SİSTEM MİMARİSİ (modül → şartname teslim eşlemesi)
- `drone_sdk.py`        → simülasyon I/O (input/telemetri); şartname "input.py" muadili.
- `inovasyonlu_j_v2.py` → sensör füzyonu / filtreleme / tahmin (GNSS temizleme + hız kestirimi).
- `ana_kontrol.py`      → güdüm ve karar mekanizması (öngörülü yönelim + ARAMA→KILIT FSM).
- `server.py`+`index.html` → görev arayüzü, telemetri, **10 video isterinin görünürlüğü**
  (aşağıdaki bölüm). Olay günlüğü + görev izleyici `server.py`'de; ID/faz/vuruş overlay'i
  index.html'de. GÜDÜM KODUNA DOKUNULMAZ (bkz. VİDEO ÇIKTILARI ARAYÜZÜ).
- `detection/gorsel_tespit.py` (best.pt YOLO) → görsel tespit; `guidance/ibvs_gorsel.py` →
  görsel BASİT IBVS güdüm (TEK görsel yasa). Teslim .zip'i bu modülleri + modeli içermeli.
- **GÜDÜM KODU HARİTASI: `guidance/GUDUM_HARITA.md`** (2026-07-07 v7 büyük sıfırlama
  sonrası günceldir: PN yığını silindi, basit IBVS geldi; Cfg faz-bantlı).

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

## ⭐ BÜYÜK SIFIRLAMA — BASİT IBVS (2026-07-07 v7, kullanıcı kararı)
Kullanıcı: "bu IBVS işine çok değişik şeyler eklemişsin (PN'i yönelime entegre etmiştik),
en basit haliyle uygula: görüntünün orta noktasından bbox merkezine bir çizgi çek, bu çizginin
**açısı ve büyüklüğüne** göre komut türet; tüm görsel güdüm kodunu EN BAŞTAN kur, eskiyi KOMPLE SİL."
Yapılan: `guidance/png_gorsel.py` + testleri (test_png_gorsel/test_yaw_lead/test_lookup_geometri)
SİLİNDİ (git geçmişinde). Yeni tek yasa: **`guidance/ibvs_gorsel.py` (AvciIBVS)**.
- **Matematik:** `ex=(cx−W/2)/(W/2)`, `ey=(cy−H/2)/(H/2)`, büyüklük `r=hypot(ex,ey)`,
  açı `atan2(−ey,ex)`. Komut: `yaw=SIGN·K_YAW·ex` (±YAW_MAX), `thr=SIGN·K_DIKEY·(−ey)`
  (THR_DN..THR_UP), `pitch=PITCH_SIGN·IBVS_ILERI·max(0,1−MERKEZ_FREN·r)`, **roll=0**.
  Çizgiyi sıfıra sürüp sürekli ileri uçmak = saf takip (pure pursuit); rota hedefe kapanır.
- **⛔ GPS yasağı YAPISAL:** `hesapla(det, p)` imzasında konum/hız/rotasyon YOK → görsel fazda
  GPS/J kullanmak imkânsız (kilit testi: `test_ibvs_gorsel.test_gps_siz_imza`).
- **Alttan yaklaşma bedava:** kamera +25° yukarı tilt'li; hedefi MERKEZDE tutmak = araç hedefin
  ALTINDA (gökyüzü arka plan). Ekstra look-up/dikey-geometri knob'u YOK.
- **Kaldırılan Cfg (hepsi):** VIS_LAW, VIS_PN_N/A_MAX/TILT/SIGN_VZ, VIS_TRACK_TILT, VIS_TAKIP_VC,
  VIS_KP_CLOSE/KV_CLOSE, VIS_TERM_PCT/COMMIT_PCT/COMMIT_LAT, VIS_HOLD_PCT, VIS_SPAN_CM,
  VIS_R/VC/OMEGA_EMA, VIS_OMEGA_MAX, VIS_W_PX_MIN, VIS_VC_CAP, VIS_TAU_Z, VZ_MAX, VIS_LOOKUP_VZ,
  VIS_EY_REF/K, VIS_K_YAW_LEAD, VIS_SOFTSTART_S/MIN, VIS_STICKY_PCT, VIS_DEADRECKON_S(_NEAR),
  VIS_LOST_TO_GPS_S_NEAR. **Yeni:** IBVS_K_YAW, IBVS_SIGN_YAW, IBVS_K_DIKEY, IBVS_SIGN_DIKEY,
  IBVS_ILERI, IBVS_MERKEZ_FREN. Panel 8 slider'a indi. **KAZANÇLAR CANLI TUNE gerektirir.**
- **Alt-FSM SİLİNDİ:** YAKLASMA/TAKIP/TERMINAL yok — tek davranış, hep ileri. Kilit isteri
  sayacı (5/10 sn pencere, `_kilit_degerlendir`) **SALT GÖZLEM** olarak yaşar: kırmızı dörtgen,
  ANGAJMAN çipi, olay günlüğü kanıtı üretir ama HİÇBİR komuta girmez.
- **Kayıp yönetimi sade:** tespit yok → HOVER; `VIS_LOST_TO_GPS_S`(2 s) aşılırsa (yalnız OTO)
  GPS'e revert. Kör-devam/yakın-yapışkanlık katmanları silindi.
- **Telemetri:** `gudum.png`→`gudum.ibvs` {ex,ey,buyukluk,aci_deg,kisma,dikey,ileri,yaw};
  UI'da PN kartı→IBVS kartı, FPV'de merkez→bbox turuncu HATA ÇİZGİSİ (sapma+açı etiketi).
  Log: png_R_m/Vc/omega + vis_faz artık BOŞ; yeni `ibvs_r`/`ibvs_aci` kolonları.
- **Testler:** `tests/test_ibvs_gorsel.py` (7/7) + `tests/test_kilit_takip.py` (10/10, sayaç+kayıp).
- **İŞARET DOĞRULAMA (canlı, İLK İŞ):** yaw ters dönerse `IBVS_SIGN_YAW=-1`, dikey ters
  tepkiyse `IBVS_SIGN_DIKEY=-1` (Cfg'den; bir kez doğrula). Sim'de +1 varsayıldı, teyit edilecek.

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
  yakınlık+YOLO kilidiyle görsel faza otonom geçiyor; terminal vuruş kamera verisiyle basit
  IBVS yasasında (`guidance/ibvs_gorsel.py` — hedefi merkezde tutup ileri uç). Kalan iş:
  CANLI TUNE (aşağıdaki madde) — IBVS_ILERI + K_YAW/K_DIKEY ile hedefi merkezde tutup vuruşa götür.
- **⭐ CANLI TUNE + İŞARET DOĞRULAMA (basit IBVS — SIRADAKİ İLK İŞ):** yeni yasa sim'de
  33 birim testten geçti ama CANLI davranışı hiç görülmedi. İlk uçuşta: (1) yaw/dikey İŞARET
  doğrula (ters ise `IBVS_SIGN_YAW`/`IBVS_SIGN_DIKEY`=-1, Cfg'den); (2) `IBVS_ILERI` ile yaklaşma
  hızını ayarla; (3) `IBVS_K_YAW`/`IBVS_K_DIKEY` ile hedefi merkezde sabitle; (4) sapmada taşma
  varsa `IBVS_MERKEZ_FREN` artır. Belirti→knob: `TUNE_REHBERI.md` başı. Panel 8 slider (canlı).
- **KİLİTLENME İSTERİ SAYACI (2026-07-07, şartname 6.1.2/6.1.4 — SALT GÖZLEM):** `_kilit_degerlendir`
  her görsel tik: hedef merkezi AV %25-75/%10-90 içinde + bbox en az bir eksende ≥ `VIS_LOCK_PCT`;
  10 sn pencerede kümülatif ≥5 sn → `kilit_ok` latch → ANGAJMAN çipi + kırmızı dörtgen (#FF0000)
  + olay kaydı. **Komuta GİRMEZ** (basit IBVS tek yasa; eski YAKLASMA/TAKIP/TERMINAL alt-FSM'i
  silindi). Testler: `tests/test_kilit_takip.py` (10/10).
- Video anlatım metinleri (ilk 3 dk + son 3 dk) — kullanıcı EN SONDA isteyecek; tüm metinler
  takır takır verilecek.

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
türetilir.** Görsel veri = **kameradan gelen her şey: bbox pikselleri (det) + pose KEYPOINT
pikselleri (poz)**. İkisi de kameradan → kurala UYGUN. GPS/GNSS ya da J-filtre kestirimi
(`son_temiz`, `son_z_anlik`, `son_xy_anlik`, `son_hiz`) bu fazda komuta GİRMEZ — ne yön ne
büyüklük olarak. **Yarışma kuralı: görsel temastan sonra GPS verisiyle aracı yönlendirmek
DİSKALİFİYEDİR.** (2026-07-07 v8: görsel yasa `ibvs_gorsel.hesapla(det, p, poz=None)` — imzada
det+p+poz var, `drone_pos/v_own/rot/yaw_rad` GİRMEZ; kural YAPISAL sağlanır, kilit testi
`test_ibvs_gorsel.test_gps_siz_imza` hem izinli seti hem yasak kinematik isimleri denetler.)
GPS/J YALNIZCA görsel-öncesi fazda (ARAMA/KILIT yaklaşma) kullanılır. **Görsel güdüm için
ASLA GPS/J tabanlı bir çözüm önerme; pose keypoint'i GÖRSEL veridir, serbesttir.**

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
(kıyas: scratchpad model_kiyas, 7 Tem). **DÜZELTME 2026-07-18:** "640'ta çöker — imgsz 1280
kalacak" o eski best_son içindi; aktif model best3/yolo11s NATIVE 640, dedektör **imgsz=640**
çalışıyor — bkz THROUGHPUT DARBOĞAZI bölümü.

## ⭐ YENİ MODELLER ENTEGRE — enson_bbox + ensonpose (2026-07-09)
Kullanıcının en son eğittiği iki model sisteme alındı: `enson_bbox.pt`→`models/best.pt`
(20 MB), `ensonpose.pt`→`models/talon_pose.pt` (21 MB). Eskiler `models/best_eski_20260709.pt`
+ `talon_pose_eski_20260709.pt` olarak yedeklendi. **Keypoint sırası AYNI** (`sira_bul.py` ile
doğrulandı: pred[0..5]=burun/solK/sagK/kuyArka/solKuy/sagKuy → `EGITIM_SIRASI=[0,1,2,5,3,4]`
değişmedi; yeni modelde eskideki "kararsız pred[4]" uyarısı YOK, oylar daha temiz). Drop-in
uyumlu (task/sınıf/kpt_shape aynı); PnP şeması (`talon_pose.yaml` berat_json) geçerli.
**KIYAS (379 kare pose dataset, GT'li; NOT: eski modellerin eğitim dağılımı → eskiye HAFİF
avantajlı, yine de yeni bbox kazandı):**
- **BBOX (yeni daha İYİ, güdüm ana girdisi):** tespit% ~berabere (89.2 vs 90.2), güven ort
  **0.852→0.908**, IoU medyan **0.729→0.773** (IoU>0.5 %80→**%88**) → kutu hedefe daha oturaklı.
- **POSE (karışık, robustluk net artı):** PnP çözüm **%66→%80** (tespit-yok 28→12, red 100→62 —
  zor/uzak kareleri daha çok yakalıyor); çözülen karede ortalama hassasiyet biraz düşük (mesafe
  MAE 2.02→2.81 m, yaw 15.3→22.0° — ama medyanlar yakın: 0.60→0.75 m, 2.7→3.2°; ortalama, yeni
  modelin eskinin hiç çözemediği zor kareleri de denemesinden şişiyor). Pose gözlemci/lead
  girdisi olduğundan +%14 çözüm oranı (kaybetmeme) net değerli.
- Araç: `pose/degerlendir_foto.py --model <yol>` (kıyas için --model eklendi);
  `scratchpad/bbox_kiyas.py` (tespit/güven/IoU). **CANLI DOĞRULAMA BEKLİYOR** (dataset iyimser;
  gerçek kalite uçuşta). Kötüleşirse yedekten geri dönülür.

## ⭐ DİKEY MERKEZLEME ÇÖKÜŞÜ — EGO-PITCH TELAFİSİ AŞIRIYDI (2026-07-09)
Kullanıcı: "model tracking'i kaybetmese bile araç ortalayamıyor, hedef hemen kameradan
çıkıyor." VERİ (ucus_log_000321, YALNIZ gerçek-tespit tikleri): **yatay iyi** (|ex| ort 0.16,
kenar %7) ama **dikey çöküyor** (|ey| p90 0.92 — hedef kadraj üst kenarında). Kök neden
PARAMETRE/model değil, **ego-pitch telafisi ters çalışıyordu**: ileri itki artınca (İLERİ
0.70) gövde kalıcı **−37°** yatık uçuyor; `IBVS_EGO_PITCH_GAIN=1.0` bu KALICI yatıklığı
"sahte yukarı" sanıp +0.70 telafi ekliyordu → ham `vis_ey −0.36` (hedef GERÇEKTE yukarıda,
drone altında = istenen) telafiyle **+0.37'ye DÖNÜYORDU** → yasa "hedef aşağıda, çok
yüksekteyiz" sanıp sürekli sert **alçalış** (thr ort −0.63, %93) → drone hedefin altına inip
hedefi kadraj ÜSTÜNDEN kaçırıyordu. Ego-telafi geçici pitch spike'ları içindi (kaçak-tırmanma);
ileri itki kalıcı olunca kalıcı zararlı ofset oldu. **Düzeltme:** `IBVS_EGO_PITCH_GAIN 1.0→0.4`
— uçuş verisinden tarandı (GAIN süpürme: 1.0 eyy +0.47/%86 alçal → 0.4 eyy +0.04 hedef nişanda,
|ey| dikey p90 0.77→0.59 en merkezi). Kaçak-tırmanma koruması 0.4'te kısmen korunur (geçici
spike hâlâ telafi, kalıcı yatıklık aşırı silinmez). Yatay kanal (yaw) zaten iyiydi, dokunulmadı.

## ⭐ THROUGHPUT DARBOĞAZI = SAHI (2026-07-18 ÖLÇÜLDÜ — eski "GPU paylaşımı / TensorRT gerekir" anlatısı DÜZELTİLDİ)
Gerçek makine **GTX 1650 Ti** (eski "RTX 4060 @1280 39 ms" sayıları TEK SEFERLİK benchmark
kutusuydu; canlı uçuşlar HEP 1650 Ti — `perf_log` gpu kolonu). Aktif dedektör çağrısı
**imgsz=640** (best3/yolo11s 640'ta native eğitildi, server.py:955). Ölçüm araçları:
`bench_sahi.py` (izole det_ms, SAHI on/off), `kiyas_sahi.py` (menzil-binli recall), `perf_log_*.csv` (canlı).
- **Kök neden = SAHI, model DEĞİL.** İzole bench (1650 Ti, FP16 açık): TEK predict @640 **~30 ms**
  (model HIZLI); SAHI açık **347-459 ms** (kare başına 7-9+ predict; **12-15x**). Yani ~800 ms canlı
  det_ms = SAHI'nin kare-başına dilim-predict'leri, ağır model DEĞİL. → **`SAHI_AKTIF=False`**
  (ana_kontrol.py:304). Canlı det_ms 800→**~203 ms / ~5 FPS**.
- **FP16 ZATEN default açık** (`AVCI_FP16=1`, server.py:69) — lever DEĞİLDİ. "Model ağır,
  TensorRT/FP16 gerekir" anlatısı YANLIŞ (tek predict 30 ms; compute-bound değil).
- **Kalan ~203 ms (izole 30 ms değil) = oyun GPU contention** (Drones of War PLAY'de aynı 1650 Ti'yi
  paylaşıyor). Bu kısım geçerli: gerçek çözüm KULLANICI tarafında (grafik kalitesi/çözünürlük düşür
  veya NVIDIA panel FPS cap → inference'e headroom).
- **imgsz=640 KALIR** (aktif model native 640; eski "imgsz 1280 KALIR / 640'ta çöker" GEÇERSİZ).
  Doğruluk (uzak/küçük recall + düşük conf ~0.30) ayrı iş: eğitim/veri (ekip).
- Önceki mitigasyonlar (poz OFF olduğundan çoğu moot): pose imgsz 1280→960, `POZ_HER_N` 3→5, FP16
  (`quantize=fp16`/`half` dinamik — yeni ultralytics uyarısız, eski `half`'e düşer; `AVCI_FP16=0` ile kapatılır).

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
- **Kayıp yönetimi sade:** tespit yok → (OTO) `VIS_LOST_TO_GPS_S` kadar hover, sonra GPS'e
  revert. **Default 0 = kayıpta ANINDA GPS (2026-07-08 kullanıcı isteği: ara hover beklemesi
  kafa karıştırıyordu);** dedektör titremesini `VIS_STALE_S`(0.5 s) köprüsü emer → tek-kare
  atlamalar revert tetiklemez. Manuel GÖRSEL switch'te revert yok (hep hover). Kör-devam/
  yakın-yapışkanlık katmanları silindi → **2026-07-08: GÖRÜNTÜ-DÜZLEMİ KÖPRÜ kullanıcı
  onayıyla GERİ GELDİ (aşağıdaki bölüm)** — v7'dekinden farkı: tek knob, kilit saymaz, log ayrıştırır.
- **Telemetri:** `gudum.png`→`gudum.ibvs` {ex,ey,buyukluk,aci_deg,kisma,dikey,ileri,yaw};
  UI'da PN kartı→IBVS kartı, FPV'de merkez→bbox turuncu HATA ÇİZGİSİ (sapma+açı etiketi).
  Log: png_R_m/Vc/omega + vis_faz artık BOŞ; yeni `ibvs_r`/`ibvs_aci` kolonları.
- **Testler:** `tests/test_ibvs_gorsel.py` (7/7) + `tests/test_kilit_takip.py` (10/10, sayaç+kayıp).
- **İŞARET DOĞRULAMA (canlı, İLK İŞ):** yaw ters dönerse `IBVS_SIGN_YAW=-1`, dikey ters
  tepkiyse `IBVS_SIGN_DIKEY=-1` (Cfg'den; bir kez doğrula). Sim'de +1 varsayıldı, teyit edilecek.

## ⭐ ÖNGÖRÜLÜ YAW LEAD — POSE'DAN HEDEF ROLL (2026-07-07 v8)
Kullanıcı: iki yeni model (`eniyi_bbox.pt` = mevcut `models/best.pt` ile ÖZDEŞ → bbox no-op;
`eniyi_pose.pt` = yeni poz modeli → `models/talon_pose.pt`). Pose çıktısı artık güdüme giriyor:
avcı hedefi **arkadan takip ederken** iki **kanat ucu pikselinden** (kp[1]=sol, kp[2]=sağ)
hedefin **roll/bank** açısı çıkarılıp, banklı uçağın alçak kanadı yönüne döneceği fiziğiyle
**bir an sonra nereye yöneleceği** öngörülür ve yaw'a **ileri-besleme (lead)** olarak eklenir.
- **Matematik (`ibvs_gorsel.kanat_roll_img`):** `roll_img = atan2((v_sağ−v_sol)·H, (u_sağ−u_sol)·W)`
  (normalize kp W/H ile piksel-orana ölçeklenir). Sağ kanat alçak (v büyük) → roll_img>0 → hedef
  sağa döner. `yaw = clamp(K_YAW·ex + IBVS_SIGN_ROLL·IBVS_K_ROLL_LEAD·roll_f, ±YAW_MAX)`. **Sadece
  YAW; thr/pitch/roll DEĞİŞMEZ** (kullanıcı kararı: yaw ileri-besleme). roll_f EMA'lı (IBVS_ROLL_EMA).
- **Kapılar (biri düşerse lead=0 → saf IBVS, zarif düşüş):** iki kanat ucu conf ≥ `IBVS_ROLL_CONF_MIN`;
  `aspect_deg ≥ IBVS_ASPECT_MIN` (yalnız PnP çözülünce; yandan/önden kanat çizgisi bank'i temsil
  etmez); poz bayatlığı ≤ `IBVS_POZ_STALE_S` (`_gorsel_guduum`'da; POZ_HER_N=3 seyrek).
- **Roll PnP'ye BAĞIMLI DEĞİL:** doğrudan 2 kanat-ucu pikselinden → PnP başarısız olsa da (kp varsa)
  çalışır (PnP'nin LOS-ekseni roll'ü kötü-koşullu; bu yöntem sağlam).
- **EGO-MOTION TELAFİSİ (v8+):** kamera gövdeye sabit → biz yatınca (kendi roll) kanat çizgisi de
  döner, "hedef bank"ı kirletir. `roll_comp = roll_img − IBVS_EGO_ROLL_GAIN·own_roll` (own_roll =
  kendi IMU roll'ümüz, `adim()`→`_gorsel_guduum`→`hesapla(..., own_roll_rad=...)`). Kendi IMU'muz =
  ego-motion, HEDEF konumu DEĞİL → kural ihlali değil. **Basit IBVS roll=0 komut verdiğinden gövde
  ~düz kalır → kirlilik zaten küçük** (7 Tem log: own roll std 1.5° vs hedef bank 9.2°); ego-comp
  agresif/banklı uçuşta sigortadır. Log: ham `ibvs_roll_raw` + ego-telafili `ibvs_roll`.
- **⛔ İŞARET VERİYLE BELİRLENDİ:** `IBVS_SIGN_ROLL=−1` (default). `araclar/pose_ongoru_analiz.py`
  (7 Tem, ucus_log_220539): corr **−0.86** @0.2sn, **%86** doğru yön → +1 TERS'ti (sağ derken hedef
  sola gidiyordu). Öngörünün FİZİĞİ geçerli, yön bağı tersti. Ego-comp işareti: aynı araç ego A/B
  → `IBVS_EGO_ROLL_GAIN` (+1 default; banklı koşuda teyit).
- **Veri akışı:** `server.dedektor_dongusu` taze pose koşunca `beyin_lock` altında
  `beyin.set_gorsel_poz(poz_ui)` (normalize kp); `_gorsel_guduum` bayatlık + kendi roll'le
  `ibvs.hesapla(det, Cfg, poz=..., own_roll_rad=...)`'a geçirir. Pose GÖRSEL veri → kurala uygun.
- **Cfg (yeni):** `IBVS_K_ROLL_LEAD=0.5⚙`, `IBVS_SIGN_ROLL=−1(veri)`, `IBVS_ROLL_CONF_MIN=0.5⚙`,
  `IBVS_ROLL_EMA=0.4`, `IBVS_ASPECT_MIN=120`, `IBVS_POZ_STALE_S=0.6`, `IBVS_EGO_ROLL_GAIN=1.0`,
  `VIS_POSE_MODEL_PATH`.
- **Telemetri/UI:** `gudum.ibvs` → `roll_deg(ego-telafili)/roll_raw_deg/lead/roll_ok`; IBVS kartında
  "Hedef bank"+"Öngörü"; FPV'de kanat çizgisi (camgöbeği) + öngörülen dönüş oku (sarı).
  Log: `ibvs_roll/ibvs_lead/ibvs_roll_ok/ibvs_roll_raw`.
- **DOĞRULAMA ARAÇLARI:** `python araclar/kp_sira_dogrula.py` (keypoint sırası; "SONUÇ: OK") +
  `python araclar/pose_ongoru_analiz.py` (öngörü uyum%/işaret/ufuk + ego-comp A/B). Tune prosedürü
  `TUNE_REHBERI.md` "ÖNGÖRÜLÜ YAW LEAD — VERİ-TABANLI TUNE PROSEDÜRÜ".
- **DURUM:** işaret VERİYLE belirlendi (`SIGN_ROLL=−1`); ego-comp eklendi (`GAIN=+1`, banklı koşuda
  teyit). Kalan: `IBVS_K_ROLL_LEAD` canlı tune. Test: `tests/test_ibvs_gorsel.py` (13/13).

## ⭐ YUMUŞAK GEÇİŞ / SOFT-HANDOFF — GPS→GÖRSEL SÜREKLİLİĞİ (2026-07-09)
Kullanıcı: "GPS'ten görsel güdüme geçiş anında iki mimari uyumsuzluğu hedefi kadrajdan
çıkarıyor, görsel temas kesiliyor." Kök neden ÜÇ mekanizma (kod keşfiyle doğrulandı):
(1) **İleri lunge** — handoff mesafesinde (~40m) bbox küçük → `ileri_istek` `IBVS_ILERI`
tavanına doyar + `yak=1` fren baypası → ilk tikten tam ileri pitch (+0.70) → gövde ~−37°
öne yatar, gövdeye sabit kamera düşer, hedef kadraj ÜSTÜNDEN kaçar; (2) **Dikey nişan
sıçraması** — GPS hedefi merkezde tutar (ey≈0), görsel yasa `ey_ref≈−0.108` "alttan vur"a
ANİDEN kayar → ilk tik `thr≈−0.216` ani alçalış; (3) **Soğuk başlangıç** — ilk görsel tik
ham komut, tek koruma `_send` MAX_DELTA=0.05 slew (yalnız hızı sınırlar, büyüklüğü değil).
**Çözüm (kamera-only, GPS'e dokunmadan — kural yapısal korunur):** görsel faz başından
`IBVS_HANDOFF_S`(1.0s ⚙) süren rampa faktörü `s:0→1` (`ibvs_gorsel.hesapla`); YALNIZ iki
kanalı yumuşatır: **ileri-itki** (pozitif pitch terimi `*s`) ve **dikey-nişan** (`ey_ref_eff
= s·ey_ref`, merkezden alttan-vur'a). **Yaw + dikey-ORTALAMA ilk tikten TAM güçte** (hedefi
kadrajda tutan kanallar dokunulmaz). Zamanlayıcı = görsel faza giriş anı (faz durumu, GPS
verisi DEĞİL); `IBVS_HANDOFF_S=0` → `s=1` hep → KAPALI (eski davranış bit-aynı; A/B).
- **Mekanik:** `ibvs_gorsel.sifirla()` `_handoff_t=None`; `hesapla` ilk tikte `det["t"]` ile
  damgalar, `s=clamp((t−_handoff_t)/HANDOFF_S,0,1)`. OTO handoff girişinde (`ana_kontrol.py`
  `durum="GORSEL_GUDUM"`) + manuel switch (`set_vis_mode`) + GPS revert → hepsi `ibvs.sifirla()`
  çağırdığından her yeni görsel faz taze rampa penceresi alır. `_send` slew ile birleşir
  (GPS'in son frenlenmiş komutundan rampalı görsel komuta akış; stall yok).
- **Telemetri:** `gudum.ibvs.handoff_s` (0=giriş,1=tamam), `ey_ref` artık EFEKTİF (FPV nişan
  çizgisi rampa boyunca gerçek konumu gösterir), `ey_ref_hedef` tam hedef. Tune slider
  `IBVS_HANDOFF_S` (0-2s; uzunsa yaklaşma gecikir, kısaysa lunge geri gelir).
- **Sim doğrulama:** rampalı ilk tik thr=0/ileri=0 → 1sn'de tam (−0.216/+0.700); rampasız ilk
  tik −0.216/+0.700 (eski lunge+alçalış). Testler: `test_ibvs_gorsel.py` 31/31 (3 yeni handoff
  testi), `test_kilit_takip` 17/17. NOT: çekirdek-yasa test dosyaları rampayı KAPALI test eder
  (`Cfg.IBVS_HANDOFF_S=0` modül başı); rampa `test_handoff_*` ile ayrı doğrulanır.
- **CANLI DOĞRULAMA BEKLİYOR:** geçişte hedefin kadrajda kaldığı FPV'de gözlemlenmeli;
  `IBVS_HANDOFF_S` 0.6-1.5s canlı tune. Kapsam kararı: hazırlık-kapısı + derin PD sönümleme
  ERTELENDİ (kullanıcı "çekirdek yumuşak geçiş" seçti).

## ⭐ TILT-FARKINDA DİKEY NİŞAN — HIZ VEKTÖRÜ HEDEFE (2026-07-08)
Kullanıcı: kamera +25° yukarı sabit; hedefi kadraj MERKEZİNDE tutmak = hız vektörünü hedefin
~25° ALTINA nişanlamak (kronik dikey undershoot / laggy tail-chase). **Tilt kesin 25° (teyit).**
Çözüm: dikey setpoint'i tilt'ten türet — hedefi hız vektörünün görüntüdeki yerine (FOE) tut:
- **Matematik (`ibvs_gorsel.hesapla`):** `ey_ref = IBVS_DIKEY_NISAN · tan(TILT)/tan(VFOV_yarı)`
  (25°/47.2° → ~0.43). Dikey sapma `eyy = ey_f − ey_ref`; `thr = SIGN_DIKEY·K_DIKEY·(−eyy)`,
  `r = hypot(ex, eyy)`, `açı = atan2(−eyy, ex)`. Yani "çizgi" artık MERKEZDEN değil **NİŞAN
  noktasından** bbox'a; hedefi oraya sürmek = "burun hedefe kilitli" (doğrudan çarpışma rotası).
- **`IBVS_DIKEY_NISAN` (−0.8..1.2, ⚙ slider):** **NEGATİF = ALTTAN VUR: hedefi merkez ÜSTÜNDE
  tut → LOS > TILT → araç orantılı olarak hedefin ALTINDA + gökyüzü arka plan** (2026-07-08
  eklendi, aşağıdaki ALTTAN VURUŞ bölümü); 0 = merkezde tut; 1 = hız vektörünü hedefe nişanla
  (terminal çarpışma). Default **−0.25** (0.1 ve 1.0'dan evrildi).
- **Geriye uyum:** ey_ref=0 (nisan=0) → eski merkez-tabanlı yasa bit-bit aynı. Cfg: `IBVS_TILT_DEG=25`,
  `IBVS_VFOV_HALF_DEG=47.2`. Telemetri `gudum.ibvs.ey_ref`; FPV'de mavi kesikli nişan çizgisi
  (pozitif: "⊕ HIZ VEKTÖRÜ", negatif: "⊕ ALTTAN VUR") + IBVS hata çizgisi nişandan çizilir.
- Test: `tests/test_ibvs_gorsel.py` (`test_dikey_nisan_tilt_farkinda`, `test_nisanda_tam_ileri`; 19/19).

## ⭐ ALTTAN VURUŞ — NEGATİF NİŞAN + ALÇALMA FRENİ (2026-07-08, kullanıcı isteği)
Kullanıcı: görsel güdümde irtifa sürekli artıyor, araç hedefin ÜSTÜNE çıkıyor (istenen: alttan
git, alttan vur; üstten bakınca hedef zemin clutter'ında ve dedektör kör). Kök neden İKİ yapısal
kilit: (1) `nisan` clamp tabanı 0.0 → yasa hedefi asla merkez üstünde tutamıyordu → denge LOS ≤
25° → menzil kapandıkça dikey ayrım co-altitude'a büzülür; (2) sabit ileri itki **lift carry**
üretir, alçal komutu `thr=−K_DIKEY·eyy` (~−0.2) bunu yenemez (GPS dersi `THR_DN` yorumunda:
−0.40 bile yetmiyordu) ve GPS yolundaki `alc_oncelik` pitch-kısma mekanizmasının görsel yasada
karşılığı YOKTU → irtifa mandallanıyordu. Çözüm (ikisi de SALT görüntü verisi → GPS yasağına uygun):
- **Negatif nişan:** `ibvs_gorsel.hesapla` clamp `(0,1.5)→(−1,1.5)`; default `−0.25`
  (ey_ref≈−0.108 → hedef cyn≈0.45'te, kilit AV bandı içinde). Slider min −0.8.
- **Alçalma freni (anti-lift-carry):** `alcal = clamp(1 − IBVS_ALCAL_FREN·max(0,eyy),
  IBVS_ALCAL_TABAN, 1)`; `pitch *= kisma·alcal`. Hedef nişanın ALTINDAysa (eyy>0 = fazla
  yüksekteyiz) ileri kısılır → negatif thr GERÇEKTEN alçaltır. Tırmanış (eyy<0) etkilenmez.
  Cfg: `IBVS_ALCAL_FREN=2.0⚙` (slider 0..4), `IBVS_ALCAL_TABAN=0.2` (slider dışı; GPS
  alc_oncelik 0.15 tabanının aynası — asla tam durma).
- Telemetri `gudum.ibvs.alcal` (IBVS kartında nişan satırında turuncu "alçalma freni" eki);
  log kolonları `ibvs_eyref`/`ibvs_alcal` (_LOG_COLS sonuna, şema-güvenli). NOT: `mean|vis_ey|`
  artık tasarımsal ~|ey_ref| ofseti taşır — merkezleme kalitesi için `ibvs_r`/`merkez_%` kullan
  (ibvs_r nişan-göreli olduğundan rapor KPI'ları doğru kalır).
- Testler: `test_negatif_nisan_altta_kal` (merkezdeki hedef → thr<0), `test_alcalma_freni_*`,
  `test_alcalma_taban`, `test_nisan_clamp_negatif`. Canlı: üste çıkma sürerse
  NISAN −0.4 + ALCAL_FREN 3+.
- **EGO-PITCH TELAFİSİ + KÖPRÜ DİKEY-TUT (aynı gün, 2. iterasyon — kaçak tırmanma):** ilk
  düzeltme yetmedi; log 204331 tık-tık analizi kök nedeni gösterdi: **ileri itki gövdeyi öne
  yatırınca (burun −20°) gövdeye sabit kamera düşüyor, hedef görüntüde sahte YUKARI zıplıyor**
  (corr(drone_pitch, vis_ey)=0.70) → yasa drone hedefin 10 m ALTINDAYKEN +0.70 tırmanış
  veriyordu; tespit ölünce KÖPRÜ ego-kaynaklı vy'yi sürdürüp sanal kutuyu kadraj tepesine
  mıhlıyor, ~1.7 sn kör tam-tırmanış (+30 m fırlama; ey=−1.0 kuyrukları). Düzeltme:
  (1) `ey_dunya = ey_f − IBVS_EGO_PITCH_GAIN·tan(own_pitch)/tan(VFOV_yarı)` — dikey hata kendi
  pitch'ten arındırılır (`hesapla(..., own_pitch_rad=...)`; ego-roll emsali, kendi IMU = ego-motion
  → kural OK; GAIN=1.0, 0=A/B kapalı); (2) köprüde **cy DONar** (vy ekstrapole edilmez) ve
  **thr=0 (irtifa-tut)** — tahminle irtifa entegre edilmez, yatay takip sürer. EP5 geri-oynatma:
  pitch sallanma anında eski thr +0.35'e sapıyor, yeni −0.45..−0.03'te kalıyor; köprü kuyruğu
  +0.70→0.0. İmza testi allowed-set'e `own_pitch_rad` eklendi. Telemetri `gudum.ibvs.ey_ego`;
  log kolonu `ibvs_eyego` (vis_ey ham kalır; fark = silinen kirlilik). Testler:
  `test_ego_pitch_telafi`, `test_ego_pitch_yokken_eski_davranis` (21/21) + köprü testleri (16/16).

## ⭐ KİLİT-TUT — BOYUT-REGÜLELİ İLERİ İTKİ (2026-07-08, Faz 2 / şartname 6.1.2+6.1.4)
Kullanıcı kararı: GPS fazı (Faz 1) tamam; sıradaki iş VURUŞ DEĞİL **kilitlenme**. Eski yasa
sabit ileri itkiyle sürekli kapanıyordu (vuruşa gidiyordu). Yeni ileri kanal, bbox eksen
oranını (boyut = max(w/W, h/H) — **kilit sayacı metriğiyle AYNI ölçü**) hedefe süren P-yasa:
`ileri = clamp(IBVS_K_BOYUT·(IBVS_BOYUT_HEDEF − boyut_f), −IBVS_GERI_MAX, IBVS_ILERI)`.
- **Uzakta** istek doygun → `IBVS_ILERI` **TAVANIYLA** yaklaş (eski davranışla bit-aynı) —
  "%5 olana kadar yaklaş" isteri kendiliğinden.
- **Hedef boyutta** cruise dengesi: `boyut_eq = HEDEF − ileri_eq/K` (0.09 − 0.25/15 ≈ 0.073 ≥
  kilit eşiği 0.06) → hedefin gerisinde **istasyon tut**, 10 sn'de 5 sn pencere dolar.
- **Fazla yakınsa** hafif **GERİ kaçış** (tavan `IBVS_GERI_MAX=0.15`; kullanıcı onayı) —
  hedef frenleyince üstüne binme. **kisma/alcal YALNIZ ileri yönü frenler** (geri = kaçış
  manevrası; kenardayken/yüksekken bile mesafe açılabilmeli).
- **`IBVS_K_BOYUT=0` = regülasyon KAPALI** → eski sabit-ileri yasa (canlı A/B + kaçış kapısı;
  Segment Kıyas'ta tek uçuşta kıyaslanır).
- boyut ex/ey ile aynı `VIS_EMA`'dan geçer (`boyut_f`, sifirla'da temiz). Girdi yalnız bbox
  pikselleri → GPS yasağına uygun; `hesapla` imzası DEĞİŞMEDİ (`test_gps_siz_imza` dokunulmadan).
- **YAKLAŞMA-AĞIRLIKLI FREN (2026-07-08, "görsel fazda hızlanamıyor" düzeltmesi):** merkez freni
  (kisma) + alçalma freni (alcal) ÇARPIMSAL binince ileri itkiyi ~10'da 1'e eziyordu (220830 logu:
  görsel pitch med **0.04** vs GPS 0.17; hedef 18 m/s kaçıyor, yaklaşılamıyor → `IBVS_ILERI`'yi
  sonuna çekmek çarpanların altında yeniliyordu). Çözüm: `yak = clamp(ileri_istek/İLERİ,0,1)` →
  frenler yalnız **kilit-tut bandında** (hedefe yakın, istek düşük → yak→0) devrede; **UZAKTA**
  (istek tavanda → yak=1) `kisma_eff=alcal_eff=1` → tam ileri, mesafe kapat. `kisma_eff =
  yak+(1−yak)·kisma` (alcal aynı). Merkezleme (yaw/thr) yak'tan BAĞIMSIZ hep aktif → dengeleme
  bozulmaz, yalnız ileri açılır. Geri-oynatma: görsel pitch med 0.04→**0.45** (tiklerin %90'ı
  tavan). Telemetri `gudum.ibvs.yak` (UI ileri satırı: YAKLAŞMA frensiz / fren % / TUT); yaklaşma
  hâlâ az gelirse artık `IBVS_ILERI` (tavan) etkili — çekilebilir. Test: `test_yaklasmada_fren_baypas`.
- Cfg: `IBVS_BOYUT_HEDEF=0.09⚙` (slider 0.06-0.20), `IBVS_K_BOYUT=15⚙` (0-40),
  `IBVS_GERI_MAX=0.15⚙` (0-0.40); `IBVS_ILERI` artık **TAVAN** (etiket güncellendi).
- Telemetri `gudum.ibvs.boyut/boyut_hedef/ileri_istek`; UI IBVS kartında "📏 Bbox boyutu /
  hedef" satırı (TUTUYOR/yaklaşıyor/GERİ kaçış); log kolonu `ibvs_boyut`. Köprüde w/h donuk →
  istek donuk (thr zaten 0). Kilit sayacı/AV/pencere aritmetiğine DOKUNULMADI (salt gözlem).
- Testler: `tests/test_ibvs_gorsel.py` 27/27 (6 yeni boyut testi + 3 uyarlama: uzak-det ile
  doygunluk korunur), `tests/test_kilit_takip.py` 17/17 (`test_kopru_boyut_donuk`).
- **Terminal vuruş SONRAKİ faz:** kilit_ok sonrası bilinçli angajman kararıyla ayrı banda
  geçilecek (NISAN→1, boyut regülasyonu kapat/İLERİ tam) — şimdilik YOK.

## ⭐ GÖRÜNTÜ-DÜZLEMİ KÖPRÜ / ÖLÜ-HESAP (2026-07-08, kullanıcı onayı)
İki tune uçuşunun verisi netti: güdüm parametreleri işini yapıyor (en iyi episodlarda
r=0.07-0.2) ama **dedektör 15-40 m'de düzenli 0.5+ sn delik açıyor** → görsel episodlar
1-2.4 sn'de ölüyor → kilit isteri (10 sn'de 5 sn) matematiksel imkânsız. Model ekipçe
iyileştiriliyor (paralel iş); yazılım tarafı çözümü **köprü**: gerçek tespit `VIS_STALE_S`'i
aşınca bbox, son iki GERÇEK tespitten ölçülen görüntü-hızıyla (px/s, `VIS_KOPRU_V_EMA`=0.5
EMA'lı, tavan 0.8·W/s) `VIS_KOPRU_S`(1.2 s ⚙ slider) boyunca İLERİ taşınır; IBVS aynı
yasayla sanal bbox'u izler. Gerçek tespit dönünce devralır; köprü de dolarsa kayıp mantığı
(`VIS_LOST_TO_GPS_S`) çalışır. **Kurallara uyum:** sabit-hız varsayımı = açıklanabilir
(kural 8); girdi = son bbox + bbox hızı (kameradan türetilmiş) → görsel-faz GPS yasağına
uygun. **DÜRÜSTLÜK:** köprü tiki KİLİT SAYACINA SAYILMAZ (`_kilit_degerlendir`'e None gider),
loga `vis_gordu=0, vis_kopru=1` yazılır (rapor tespit%'si gerçek kalır), yalnız GORSEL_GUDUM
fazında kurulur (OTO kilit sayacı `_vis_pos_count` şişmez), uzun delik sonrası ilk tespitte
hız SIFIRLANIR (bayat hızla köprü kurulmaz). UI: FPV'de turuncu "◌ KÖPRÜ" rozeti
(`gorsel.kopru`). Mekanik: `set_gorsel_tespit` hız ölçer, `_gorsel_tespit_oku` sanal det
üretir (`kopru=True`). Testler: `tests/test_kilit_takip.py` (16/16; 5 köprü testi).

## ARAYÜZ GECİKME TELAFİSİ + DEDEKTÖR DEBUG PENCERESİ (2026-07-08)
Kullanıcı gözlemi: bbox/iskelet FPV'de hedefin GERİSİNDE kalıyor (pose daha da geç).
Sebep: FPV = tarayıcı ekran paylaşımı (~0 ms), tespit = yakala+inference (~100-300 ms),
poz ayrıca `POZ_HER_N=3` seyrek → yapısal olarak daha bayat. **GÜDÜM BUNDAN ETKİLENMEZ:**
beyin tespiti inference biter bitmez `set_gorsel_tespit` ile alır (UI polling/çizim hattı
güdüme girmez); poz da `IBVS_POZ_STALE_S` kapısıyla yalnız tazeyken yaw lead'e katkı verir.
Düzeltmeler: (1) bbox'taki YAŞ TELAFİSİ (vx,vy ile ileri çizim) İSKELETE de uygulandı —
`/api/gorsel` poz'a `yas_s` ekler (`t_poz` damgası `_normalize_poz`'da), index.html kp'leri
bbox hızıyla poz yaşı kadar kaydırır (cap 500 ms). (2) `set AVCI_DEBUG_PENCERE=1` →
server'da OpenCV "dedektör gözü" penceresi: işlenen karenin üzerine AYNI karenin
tespit/poz çıktısı (kare↔çıktı %100 senkron; yeşil=güdüme giden, turuncu=zayıf/UI-only,
kırmızı=pervane maskesi). Yalnız görev aktifken güncellenir; kapalıyken sıfır maliyet.

## TUNE RAPORU — "DEĞERLERİ YAZDIR" → EXCEL (2026-07-08)
Tune panelindeki **Değerleri Yazdır** artık Cfg dökümüne EK olarak `/api/tune_rapor`'u
çağırır: `web/tune_rapor.py` aktif (yoksa en yeni) `veri/ucus_log_*.csv`'yi okuyup
GÖRSEL-faz performans metriklerini çıkarır ve `veri/tune_rapor_<zaman>.xlsx` yazar
(3 sayfa: Özet / Tune Değerleri [slider + `TUNE_SABIT_RAPOR` sabitleri] / Performans).
Metrikler: ilk tespit süresi+mesafesi, tespit oranı, kayıp sayısı, en uzun kesintisiz
takip, kilit penceresi max + isteri SAĞLANDI/SAĞLANMADI + kilide ulaşma süresi,
|ex|/|ey|/ibvs_r merkezleme, yaw pürüzlülüğü/std + yatay salınım (tutarlılık),
mesafe ilk/min/son + kapanma hızı, öngörü aktif% + |lead|. Kısa özet arayüzde
dump'ın altında görünür. Güdüm koduna dokunulmadı (salt log okuma). Bağımlılık:
`openpyxl` (requirements'ta; yoksa arayüz sebebi söyler, sistem çökmez).
**UÇUŞ-İÇİ A/B TESTİ (kullanıcı isteği, aynı gün):** slider değerleri 1 Hz
`veri/tune_log_*.csv`'ye yazılır (`server.tune_log_dongusu`); rapor uçuş loguyla
t_wall üzerinden hizalar → **"Segment Kıyas"** sayfası: her parametre değişimi
uçuşu segmente böler, her segment ayrı satır (değişiklik metni + o dilimin tespit%/
kayıp/r_ort/merkez%/yaw pürüzlülük/kapanma + tam parametre seti) → "artırınca
iyileşti mi?" TEK uçuşta görünür. **"Saniye Detay"** sayfası: saniye başına metrik
+ o saniyedeki tune değerleri (Excel'de grafiklenebilir). 3 sn içi ardışık
değişimler (slider sürükleme) tek segment sayılır (`_SEG_BIRLESTIR_S`).
**UÇUŞ KLASÖRÜ (aynı gün):** rapor basıldığında her uçuşun TÜM verileri
`veri/tune_parametreler/ucus_N/` altında toplanır (uçuş logu kopyası + tune logu
kopyası + Excel raporları). Aynı uçuş logu hep aynı klasöre eşlenir
(`kayit.json` registry, `tune_rapor.ucus_klasoru`); yeni uçuş logu → sıradaki
numara. Kopyalar her rapor basımında tazelenir (kaynak hâlâ yazılıyor olabilir).
**Her "Görev Başlat" = yeni uçuş:** server start komutunda `beyin.log_dondur()`
KOŞULSUZ çağrılır (`ana_kontrol.py`'de güdüm-dışı küçük metod; aynı kaynak üst
üste seçilse bile log dosyası döner → her görev ayrı ucus_N klasörü alır).
Test: `tests/test_tune_rapor.py` (20/20, sentetik uçuş+tune logu).

## ⭐ BYTETRACK + GYRO-CMC CANLI HATTA BAĞLANDI (2026-07-09)
`yarisma-pipeline` branch'inin tracking bağlaması main'e taşındı. Kütüphane katmanı
(`detection/takip.py` ByteTrack, `detection/kamera_model.py` cmc_homografi,
`detection/algi_hatti.py`) zaten PR#2 merge'üyle main'deydi ama **server'a bağlı değildi**
(dedektör argmax tek kutu kullanıyordu → A/B kıyasında 120 sn'de 72 tespit-kaybı kenarı /
30 farklı ID; `docs/BYTETRACK_ENTEGRASYON_NOTU.md` + `docs/AB_KIYAS_KARAR_20260707.md`).
Yapılan (branch'teki kanıtlanmış bağlama, main'in FP16/perf ölçümü korunarak):
- `dedektor_dongusu`: `tespit_hepsi` (TÜM kutular, maske sonrası) → `Takipci.guncelle
  (dets, dt, H_cmc)`; H_cmc her turda `drone.get_drone_rotation()` çiftinden
  (`kamera_model.cmc_homografi`) — kendi dönüşümüz kutu kaydırmasını telafi eder.
  Predict eşiği `min(UI_CONF_MIN, VIS_CONF_MIN, takipci.cfg.CONF_DUSUK)` — BYTE'ın
  düşük-conf ikinci turu izi yaşatır (yeni track açamaz). Görev pasifken `takipci.sifirla()`.
- **GÜDÜM KAPISI DEĞİŞMEDİ:** `det_beyin` = yalnız `tespit_mi=True` (coast beyne gitmez;
  görüntü-düzlemi KÖPRÜ ile çift ölü-hesap olmasın) + `conf>=VIS_CONF_MIN`. Coast karesinde
  poz inference de koşmaz.
- `takip.py cikti()`: son ölçümün `cls` + `t`'sini taşır (UI sınıf etiketi + yaş telafisi;
  coast'ta `t` taşınmaz, server `simdi` atar). Test: `test_cikti_t_ve_cls_tasima` (14/14).
- UI: `_normalize_tespit` → `track_id/track_durumu/tespit_mi`; `_takip` makinesi GERÇEK
  ByteTrack ID kullanır (ID değişimi = YENİDEN TESPİT olayı; `ilk` bayrağı); `/api/gorsel`
  `id`=track_id; index.html coast kutusunu KESİKLİ + "(tahmin)" çizer. UI hız kestirimi
  aynı-track_id şartına bağlandı (ID değişiminde sahte hız yok).
- `pencere_yakala.py`: WGC ayar setine cursor-only ara kademe (LTSC 19044'te draw_border
  yok → set komple düşüp imleç AÇIK kalıyordu → imleç 'talon' FP'si; branch'ten alındı).
- **⛔ CANLI REGRESYON + DÜZELTME (aynı gün, 2. iterasyon):** İlk bağlama canlıda sistemi
  ÇÖKERTTİ (kullanıcı testi: kutu hedefe bir kez çizilip rastgele yöne yürüyor, tespit
  kesiliyor). VERİ: <25 m tespit oranı önce %14-30 → sonra %0-1.2; en uzun kesintisiz takip
  2.2 s → 0.4 s (9 Tem 15:xx uçuşları). KÖK NEDEN: tracker eşikleri 50 Hz varsayımıyla tik
  cinsindendi, canlı döngü GPU paylaşımından ~8 FPS: (1) `MIN_HITS=5 ARDIŞIK` + tek kaçırmada
  TENTATIVE ölümü → dedektörün bilinen delikleriyle iz ONAYLANAMIYOR → beyne hiçbir şey
  gitmiyor (%0 uçuşlar); (2) `MAX_COAST=25 tik` = 8 FPS'te ~3 sn hayalet kutu (gürültülü
  Kalman hızıyla "rastgele yürüyen bbox"); (3) `en_iyi_track=max(hits)` coast'taki eski izi
  taze ölçülen izin önüne koyuyordu. Branch'in kendi uçuşları görsel faza HİÇ girmediğinden
  (A/B dok.) bu bağlama gerçek tespitle hiç test edilmemişti. DÜZELTMELER (`takip.py`):
  yaşam döngüsü SÜRE-tabanlı (`ONAY_MIN_HIT=3` toplam ölçüm — ardışık ŞART DEĞİL;
  `TENT_COAST_S=0.30` aday izin kaçırma affı; `COAST_S=0.60` hayalet tavanı, VIS_STALE_S
  ile uyumlu); `en_iyi_track` önce `tespit_mi=True` (ölçülen iz hayaleti bastırır).
  Simülasyon (8 FPS delikli desen): eski cfg ham tespitlerin %0'ını, yeni %99'unu beyne
  ulaştırıyor. Testler yeni semantiğe uyarlandı (test_takip 16/16).
- **ANAHTARLAR (Cfg, ana_kontrol.py):** `TAKIP_AKTIF=False` (2026-07-18 DÜZELTME — eskiden True) —
  tracker KAPALI, ham argmax tespit doğrudan beyne. SEBEP: HybridSort yaşam-döngüsü ~50 Hz
  varsayımlıydı; canlı ~5 FPS'te izi eşleştiremeyip coast'layıp bbox'u DONDURUYORDU (canlı A/B:
  tracker-on 32 s'de 2 kutu / tracker-off detektör hızında ~0.24 s tazeleniyor; bkz hafıza
  `tracker-coast-freeze-5fps`). boxmot 22.0.0 kurulu + `takip.py` import düzeltildi → 5 FPS için
  retune edilirse geri açılabilir; ŞİMDİLİK ham argmax (güdüm track_id kullanmıyor, sorunsuz).
- CANLI DOĞRULAMA BEKLİYOR: bir uçuş + tune raporu "kayıp sayısı / en uzun kesintisiz
  takip" kıyası (baz: 8-9 Tem gece uçuşları %14-30). NOT (9 Tem): kullanıcı canlı gözlemle
  "tracking düzeldi" dedi; DETECTION log kolonlarında hata var (loga güvenme, FPV/gözlem esas).

## ⭐ GYRO-CMC DENENDİ → KAPATILDI (2026-07-09, canlı kötüleştirdi)
**DURUM: `TAKIP_CMC_AKTIF=False` (KAPALI).** Kullanıcı isteğiyle açıldı, canlıda KÖTÜLEŞTİRDİ,
geri kapatıldı. KANIT (durum-geçişi kıyası, bozuk tespit kolonundan BAĞIMSIZ): CMC-açık uçuş
(165030) 258 sn'de GORSEL_GUDUM'a HİÇ giremedi; CMC-kapalı uçuş (163042) girmişti. Muhtemel
kök neden: sim attitude işareti ters (Blokör B açık) → ters CMC kaymayı 2x yapıp her dönüşte
izi kırıyor → görsel faza geçilemiyor. Kod + emniyet knob'ları DURUYOR (silinmedi); DOĞRU
açmak için önce `arac/attitude_dogrula.py` (uçuşlu truth sweep) ile işaret doğrulanmalı,
ters çıkarsa `TAKIP_CMC_SIGN=-1`, sonra `TAKIP_CMC_AKTIF=True`. **NOT (2026-07-18): ByteTrack/HybridSort
artık `TAKIP_AKTIF=False` (KAPALI) — 5 FPS canlıda coast-freeze yaptığı ölçüldü (bkz THROUGHPUT
DARBOĞAZI + tracker düzeltmesi); gyro-CMC katmanı da zaten kapalı.**

Aşağıdaki teknik detay açılırsa geçerli (şimdilik referans):
gyro-CMC (jiroskop hareket telafisi) `dedektor_dongusu`'nda `TAKIP_CMC_AKTIF` ile devreye girer.
- **NE YAPAR:** avcının kendi dönüşü (yaw/pitch/roll) uzak hedefin bbox'unu görüntüde kaydırır;
  CMC bu kaymayı IMU attitude'undan türetilen homografiyle (`kamera_model.cmc_homografi`)
  ÖNCEDEN telafi eder (eşleştirme öncesi Kalman merkezini warp'lar) → hızlı yaw'da iz kopmaz.
  Girdi = KENDİ attitude (ego-motion), HEDEF konumu DEĞİL → görsel-faz GPS yasağına UYGUN
  (ego-roll/pitch telafisinin emsali). Uçtan uca sim: doğru işaretle hızlı yaw'da iz kayması
  **136 px → 0 px**.
- **⛔ İŞARET RİSKİ (Blokör B, hâlâ açık):** sim attitude konvansiyonu (`R_govde_to_dunya`
  pitch/roll işareti + Euler sırası) bu simde truth ile HENÜZ doğrulanmadı (`MEVCUT_DURUM.md`).
  TERS işaretli CMC kaymayı DÜZELTMEK yerine İKİYE KATLAR (sim doğrulama: sign=-1 → 136→248 px).
  Güvenlik katmanları: (1) **`TAKIP_CMC_SIGN=+1`** — FPV'de dönüşte kutu hedeften UZAKLAŞIYORSA
  `-1` yap (att sırası takas → warp yönü ters; kodu değiştirmeden canlı düzeltme, server restart);
  (2) **`TAKIP_CMC_MAX_KAYDIRMA=0.25`** — tek tikte CMC kutuyu en fazla %25·W kaydırır, aşılırsa
  o track o tik CMC'siz predict eder (yanlış-işaret + büyük yaw kutuyu ekrandan fırlatmasın;
  meşru hızlı yaw ~%6·W/tik → 4x marj); `takip.py:_KalmanKutu.warp_merkez(H, max_kaydirma)`.
- **CANLI DOĞRULAMA PROSEDÜRÜ:** `set AVCI_DEBUG_PENCERE=1` ile dedektör penceresini aç, görev
  sırasında bir YAW manevrası yap: CMC doğru işaretteyse coast (kesikli) kutu dönüşte hedefin
  ÜSTÜNDE kalır; hedeften ters yöne kayıyorsa `TAKIP_CMC_SIGN=-1`. Kesin: `arac/cmc_isaret_testi.py`
  veya `arac/attitude_dogrula.py` (uçuşlu, truth-tabanlı sweep — Blokör B'yi kapatır).
- Test: `test_takip.py` `test_cmc_clamp_asiri_warp_atlar` + mevcut CMC testleri (17/17).

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
- `server.py` dedektör döngüsü best.pt'ye İLAVE koşar. Telemetri: `gorsel.poz` + `gorsel.poz_hazir`.
  **GÜNCELLEME (v8, 7 Tem):** poz artık gözlemci-only DEĞİL — kanat uçlarından türetilen hedef
  ROLL, görsel güdüme öngörülü yaw lead olarak giriyor (üstteki "ÖNGÖRÜLÜ YAW LEAD" bölümü).
  Mesafe/yaw kestirimi hâlâ gözlemci (güdüme girmez); yalnız kanat-ucu roll'ü komuta katkı yapar.
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
  yakınlık+YOLO kilidiyle görsel faza otonom geçiyor. **2026-07-08 Faz-2 kararı: görsel yasa
  şimdilik KİLİT-TUT modunda** (boyut-regüleli ileri; yukarıdaki bölüm) — hedefi AV içinde ve
  bbox ≥%6'da tutup kilit penceresini doldurur, VURMAZ. Kalan iş: kilit isteri canlıda
  doğrulanınca TERMİNAL VURUŞ fazı (kilit_ok sonrası bilinçli angajman kararı: NISAN→1,
  boyut regülasyonu kapat/İLERİ tam; şartname 6.1.3 kanıt zinciriyle).
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

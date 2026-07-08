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

## ⭐ TILT-FARKINDA DİKEY NİŞAN — HIZ VEKTÖRÜ HEDEFE (2026-07-08)
Kullanıcı: kamera +25° yukarı sabit; hedefi kadraj MERKEZİNDE tutmak = hız vektörünü hedefin
~25° ALTINA nişanlamak (kronik dikey undershoot / laggy tail-chase). **Tilt kesin 25° (teyit).**
Çözüm: dikey setpoint'i tilt'ten türet — hedefi hız vektörünün görüntüdeki yerine (FOE) tut:
- **Matematik (`ibvs_gorsel.hesapla`):** `ey_ref = IBVS_DIKEY_NISAN · tan(TILT)/tan(VFOV_yarı)`
  (25°/47.2° → ~0.43). Dikey sapma `eyy = ey_f − ey_ref`; `thr = SIGN_DIKEY·K_DIKEY·(−eyy)`,
  `r = hypot(ex, eyy)`, `açı = atan2(−eyy, ex)`. Yani "çizgi" artık MERKEZDEN değil **NİŞAN
  noktasından** bbox'a; hedefi oraya sürmek = "burun hedefe kilitli" (doğrudan çarpışma rotası).
- **`IBVS_DIKEY_NISAN` (0..1, ⚙ slider):** 0 = hedefi merkezde tut (altta kal / gökyüzü arka plan,
  eski davranış); 1 = hız vektörünü hedefe nişanla (terminal çarpışma). Default **1.0**. Her ikisi
  de çarpışmaya yakınsar (açısal bias, menzille küçülür) ama nişan=1 daha DOĞRUDAN/az-laggy rota.
- **Geriye uyum:** ey_ref=0 (nisan=0) → eski merkez-tabanlı yasa bit-bit aynı. Cfg: `IBVS_TILT_DEG=25`,
  `IBVS_VFOV_HALF_DEG=47.2`, `IBVS_DIKEY_NISAN=1.0⚙`. Telemetri `gudum.ibvs.ey_ref`; FPV'de mavi
  kesikli "⊕ HIZ VEKTÖRÜ (nişan)" çizgisi + IBVS hata çizgisi artık nişandan çizilir.
- Test: `tests/test_ibvs_gorsel.py` (`test_dikey_nisan_tilt_farkinda`, `test_nisanda_tam_ileri`; 14/14).
  Sky-bg riski: araç hedefin üstüne çıkarsa zemin arka plan; regülasyon nişanda tutar, aşırı
  tırmanma yok. Yaklaşmada daha çok "altta kal" istenirse slider'ı düşür.

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

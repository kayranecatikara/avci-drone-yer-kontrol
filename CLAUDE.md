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

## POZ KESTİRİMİ (2026-07-04'te eklendi — GÖZLEMCİ modda)
`models/talon_pose.pt` (yolo11m-pose, 6 keypoint) + PnP artık pipeline'da:
- `detection/poz_tespit.py` (PozDedektor) + `pose/poz_cozucu.py` (PnP+EMA; **EGITIM_SIRASI
  ve MESH_PIVOT_OFFSET kritik** — POSE_REHBERI "EĞİTİM SIRASI" bölümü).
- `server.py` dedektör döngüsü best.pt'ye İLAVE koşar; **beyin/güdüm girdisi DEĞİŞMEDİ**
  (best.pt bbox akışı aynen). Telemetri: `gorsel.poz` + `gorsel.poz_hazir`.
- Arayüz: FPV'de iskelet + "MESAFE (KAM) / HEDEF YAW" satırları + 📐 POZ KESTİRİMİ kartı
  (kamera vs gerçek kıyas). Video isteri "GNSS bağımlılığının azalması" kanıtına birebir.
- Kalite (eğitim karelerinde İYİMSER): mesafe medyan %8 / yaw medyan 6° (<10 m iyi);
  15 m+ mesafe şişer; %27 kare tespitsiz → **yalnız terminal faz (≈4-12 m) aracı**.
  Güdüme besleme (dalış zamanlaması / lead) modeli kullanıcı onaylarsa SONRAKİ adım.

## SAHTE TESPİT MODU (2026-07-04 — güdüm geliştirme aracı)
YZ modeli hazır olmadan görsel güdüm algoritması geliştirmek için: arayüzdeki
**"🖱️ Sahte Tespit (Mouse)"** butonu açıkken, görev sırasında FPV'de:
**SOL TIK** = hedefi işaretle — işaret bırakınca da KALIR (kalıcı ~12 Hz akış; basılı
tutup sürüklersen imleci izler, bırakınca son yerde sabitlenir; yeni sol tık taşır) ·
**SAĞ TIK / ESC** = işareti temizle (mod kapatma / odak kaybı da temizler). İşaret
`/api/sahte` üzerinden server'a akar ve `dedektor_dongusu`'nde gerçek model çıktısının
YERİNE geçer (aynı det sözlüğü → `beyin.set_gorsel_tespit`; güdüm için gerçek
tespitten ayırt edilemez). Failsafe: mesaj 0.6 s kesilirse otomatik düşer (kalıcı
akışı tarayıcı sekmesi sürdürür; sekme kapanırsa failsafe devrede).
DİKKAT: dedektör döngüsü SADECE otonom görevde işler → görev başlatılmadan işaret
işlenmez; arayüz bu durumda uyarı yazar (leftStatus).
**OTOMATİK ZORLA GÖRSEL:** OTO modda görsel yol hiç devreye girmez
(`AUTO_VISUAL_HANDOFF=False`, bilinçli) → işaret konunca server güdümü otomatik
**ZORLA GÖRSEL**'e alır (drone işarete tepki verir: yaw+irtifa, ortalanınca ileri);
işaret kalkınca/görev durunca ÖNCEKİ moda geri döner (olay günlüğüne yazılır).
Kullanıcı manuel mod değiştirdiyse geri dönüş ezilmez. NOT: işaret EKRANA sabittir —
kenara konursa drone o yöne DÖNER ama işaret merkeze gelmediği için ileri gitmez;
gerçek "hedefe git" testi = işareti oyundaki hedefin üstünde tut/sürükle.
Overlay'de MACENTA bbox + "[SAHTE/MOUSE]" etiketi (yeşil = gerçek model). Yeni model
gelince hiçbir şey sökülmez — buton kapalıyken sistem tamamen eskisi gibi.
Sahte bbox boyutu %10×%8 (kilit eşiği %6'nın üstü → mouse ile KİLİTLENME test edilir).
Mouse verisi tazeyken ağır YOLO inference ATLANIR (sonuç zaten ezilecekti) → sahte akış
GPU/CPU hızından bağımsız ~20 Hz; kilit tazelik sınırı (0.2 s) yavaş makinede de tutar.
DURUŞ KOMPANZASYONU ETKİSİ (2026-07-05): dikey referans artık dinamik (aşağıda). Hover'da
mouse davranışı birebir aynı; İLERİ UÇUŞTA ekrana PARK edilmiş işaret "o anki dünya-yönü"
olarak yorumlanır (öne yatınca REF çizgisi yukarı çıkar → sabit işaret altında kalır →
iniş komutu; fiziksel doğru). Belgelenen kullanım (işareti oyundaki hedefin ÜSTÜNDE
tutmak) bundan İYİLEŞİR. Eski sabit-referans davranışı gerekirse `VIS_ATT_COMP=0`.

## GÖRSEL GÜDÜM (DÜZ IBVS) + KİLİTLENME ÖLÇÜMÜ (2026-07-04)
Kullanıcının verdiği minimum IBVS speci `guidance/ibvs_guidance.py`'de: bbox merkezinin
görüntü merkezinden sapması TEK hata sinyali → angle-mode komut. Derinlik/PnP/
kalibrasyon/roll YOK. SDK fiziğine tek uyarlama: pitch=YATAY ivme olduğundan
"yukarıdaysa burnu kaldır" işini throttle yapar (kamera 25° tilt → `VIS_EY_REF=0.43`
referans çizgisi); "sağdaysa dön"=yaw, "küçükse ileri"=pitch (merkez kapısı + alan-dur).
**DİKEY EKSEN = ASİMETRİK YASA (2026-07-05 v2; canlı log kanıtıyla düzeltildi):** görüntü
hatası → istenen dikey hız (`VIS_K_VZ=2.0`, tavan `VIS_VZ_MAX=1100` cm/s iki yönde) →
TIRMANIŞTA `thr = vz_des/Cfg.VZ_MAX` feedforward (SDK'da thr>0 zaten HIZ komutu, sim
döngüyü kapatır; GPS terminal eşlemesi), İNİŞTE `thr = clamp(VIS_KV_Z·(vz_des−vz),
THR_DN, 0.0)` — üst klemp 0.0: fren = yerçekimi telafisini geri açmak (thr=0 irtifa-tut);
inişte ASLA tırmanış komutu yok. Canlı loglardaki NET tırmanış (+7.8 m/s, işaret REF
altındayken; veri/ucus_log_20260705_*; thr max +0.715 = ESKİ ham-P klempinin izi — süreç
o gün eski kodla çalışıyordu, v1 hiç uçmadı) ham P'nin yetersizliğini gösterdi. Simetrik
hız-hatası P'si (v1) de bu asimetrik plantta (thr>0 hız modu ANINDA izler — log ölçümü:
thr≥0.5'te vz ort +17 m/s; thr<0 ivme modu yavaş birikir) analizce limit çevrimine
mahkûmdu: "fren" +0.7 = 23 m/s tırmanış komutu. **KOORDİNELİ DALIŞ:** ileri pitch'in alt-taraf kapısı
kaldırıldı (v1'de iniş tiklerinin %84-92'sinde pitch=0 → "kanatlar durur"); hedef
alttayken ileri+iniş birlikte sürer, kısma tabanı `VIS_ALC_MIN=0.5` (canlı ayar); üst
kapı durur (hedef çok yukarıdaysa önce tırman). Spec'in opsiyonel roll'u eklendi
(`VIS_K_ROLL=0` default KAPALI). vz kaynağı: SDK `velocity[2]` (temiz), yalnız GORSEL
dalında. Gözlemlenebilirlik: GÜDÜM kartında "İniş isteği / vz" satırı; uçuş logunda
`vis_vz_des/vis_vz_own/vis_alc` kolonları. Testler: `tests/test_ibvs_dikey.py` (12 test;
"aşırı düşüş freni asla pozitif değil" regresyon testi limit çevrimini kalıcı yasaklar).
**HASSASİYET SERTLEŞTİRMESİ (2026-07-05 denetimi; gerçek/pose model hazırlığı):**
- **DİNAMİK DİKEY REFERANS (F1, en kritik):** gövdeye sabit kamera öne yatınca hedefin
  görüntü konumu kayar (23° yatışta ~0.40) — sabit `VIS_EY_REF` yalnız sıfır-yatış
  kalibrasyonuydu ve dikey/ileri döngüleri kamera üzerinden çapraz bağlıyordu (sahte
  tırmanış + kapı çırpınması; kapalı-döngü simde kanıtlandı: comp KAPALI +12.7 m sahte
  tırmanış zirvesi / comp AÇIK eyd RMS 0.04). Çözüm `ibvs_guidance.dinamik_ey_ref`:
  `ey_ref = tan(TILT + pitch_own)/tan(vFOV/2)` (UE: öne yatış = NEGATİF pitch; vFOV =
  hFOV·H/W). Tilt/hFOV tek kaynak `pose/geometri.py` (kalibre.py rafine ederse güdüm
  izler). `VIS_ATT_COMP=1` default AÇIK (slider'la kapatılabilir); UI'daki turuncu REF
  çizgisi artık duruşla hareket eder + "REF eyd=" okuması. Kalibrasyon: aynı irtifadaki
  hedefte eyd=0 olana dek `VIS_CAM_TILT_DEG` slider'ı.
- **KARE-BAŞINA EMA (F4):** EMA artık yalnız YENİ tespitte işler (`det_t` kapısı) —
  eski kod 50 Hz'de aynı kareyle tekrar besleyip tek kötü kareye %92 ağırlık veriyordu.
  Referans+poz da görüntüyle aynı anda SNAPSHOT'lanır; kor-devam donmuş çifti taşır.
- **GENİŞLİK FRENİ (F3):** ileri fren ölçüsü bbox GENİŞLİĞİ (`VIS_W_STOP=0.30`; eski
  alan yasası w~0.5'te duruyordu = tam Av kenarı, sıfır gezinme payı → kilit imkânsız).
- **POZ→GÜDÜM PROFİLİ (F5; bayrak KAPALI başlar):** `VIS_USE_POSE_DIST=1` iken ileri
  hız poz mesafesinden (12 m'de yavaşla → 4 m'de dur; yalnız İLERİYİ etkiler; poz yokken
  genişlik yasası fallback). Besleme: server → `beyin.set_poz(mesafe_ema_cm)` →
  `_gorsel_guduum` → `hesapla(poz_cm=)`. Kapalı-döngü simde 5 m tutuş+kilitlenme geçti.
- **Boru hattı (F2/F8):** `det["t"]` artık KARE ANI (inference sonu değil); bbox beyne
  poz'dan ÖNCE teslim; poz her `_POZ_HER_N=2` karede; pencere-bölgesi 2 sn cache
  (her karedeki getAllWindows+psutil taraması kalktı). TAKİP kartında "Dedektör
  kadansı" (kilit ≥~5 Hz ister; CPU'da gerçek model yetmez → sahte akış dev yolu).
- **conf/sınıf koruması (F7):** `_gorsel_tespit_oku` conf tabanı; `VIS_CLS_ID` ile
  dedektör sınıf filtresi (çok-sınıflı modelde decoy kilidi önlenir; -1=kapalı).
- **Kapalı-döngü sim:** `tests/test_sim_kapali_dongu.py` — sentetik plant (asimetrik dikey +
  lean + parametrik yaw) + GERÇEK `pose/geometri.py` projeksiyonu; F1 kabul testi,
  iniş değişmezi, kadans matematiği, poz tutuş senaryosu + kesen-hedef/dropout raporu
  (bulgu: 10 Hz + %27 kayıpta 0.2 sn bütçe yetmiyor — kilit için kadans/kayıp iyileşmeli).
  Tüm süitler: `python -m pytest tests/ -q`.
**KİLİTLENME (şartname) — `KilitlenmeTakip`** (ibvs_guidance.py, GÖZLEMCİ; komut üretmez):
- Geçerli kilit tiki: bbox W ve H'nin **≥ %6'sı** (şartname sınırı %5; tam sınır hakem
  riski → tavsiye %6 = `KILIT_ESIK_ORAN`) + bbox **TAMAMEN Hedef Vuruş Alanı içinde**
  (yatay %25 / dikey %10 kenar payları) + tespit ≤ 0.2 sn taze.
- KİLİTLENME = **5.0 sn kesintisiz**; "eksik/hatalı frame toleransı" TOPLAM **0.2 sn**
  ve başlangıç/bitiş kenarlarında GEÇERSİZ (deneme geçerli tikte başlar, başarı geçerli
  tikte ilan). Bütçe aşılırsa deneme sıfırlanır. Testler: `tests/test_kilitlenme.py`
  (8 senaryo + float-sınır, bütçe API'sine karşı) + `tests/test_sim_kapali_dongu.py` kadans
  testi (dedektör ≥~5 Hz şartı: 2/4 Hz'de kilit MATEMATİKSEL imkânsız, 10/20 Hz'de olur).
- Akış: `beyin.kilit` her adim()'de güncellenir (mod'dan bağımsız) → `server.py`
  `_gorev_izle()` kenar-tespitiyle olay üretir (sayaç akıyor / KOPTU / BAŞARILI) →
  telemetri `gorsel.kilit` (durum + geometri sabitleri) → `index.html`: FPV'de SARI
  "HEDEF VURUŞ ALANI" çerçevesi, kilit geçerliyken KIRMIZI bbox (şartname renkleri),
  alan alt kenarında ilerleme çubuğu, TAKİP kartında "Kilitlenme (şartname)" satırları.
- Sabitler ŞARTNAMEDEN gelir (overfit değil); TUNE_ALLOW'a bilerek EKLENMEDİ.

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
- **Otonom angajman/vuruş (İster 9/10) — güdüm bağımlılığı:** UI göstergeleri hazır ama drone
  OTO uçuşta hedefe otonom VURMUYOR. Gerekli 3 iş: `Cfg.AUTO_VISUAL_HANDOFF=True`, kamera-
  tabanlı terminal vuruş mantığı, `Cfg.GPS_TERMINAL_STRIKE` (şu an hepsi kapalı). Bunlar gelince
  UI'da satır DEĞİŞMEZ (VURUŞ/BAŞARI latch'i mesafe eşiğinden otomatik tetiklenir). Şimdilik
  test: manuel GÖRSEL switch veya `GPS_TERMINAL_STRIKE=True` + "Gerçek GPS" ram.
- Video anlatım metinleri (ilk 3 dk + son 3 dk) — kullanıcı EN SONDA isteyecek; tüm metinler
  takır takır verilecek.

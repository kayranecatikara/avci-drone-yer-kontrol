# GÖREV: Yarışma Pipeline Refaktörü
## detection → tracking → pose (PnP) → güdüm (APN+OIPN) → angajman

## Bağlam
Bu repo (avci-drone-yer-kontrol) TEKNOFEST avcı drone yer kontrol yazılımı. Mevcut akış: `pencere_yakala` → `gorsel_tespit` (YOLO, bbox) → `ana_kontrol` FSM (ARAMA→KILIT→GORSEL_GUDUM) → `ibvs_guidance` (bbox merkez hatası → komut). Bu refaktörle görsel hat yarışma pipeline'ına dönüştürülüyor:

**tespit → takip (ByteTrack + gyro-CMC) → PnP poz kestirimi → APN+OIPN güdüm → kilit bildirimi → angajman**

**Sürüm notu (sim/SDK v0.0.5):** kamera tilt **25° yukarı** (v0.0.4'teki 0° geri alındı — FPV kamera burnu 25° yukarı eğik bakar), FOV **125° yatay (HFOV — convention netleşti)**, hedef GPS **5 Hz**, dropout 30. sn'den sonra her 10 sn'de 2 sn, gecikme değişken ve açıklanmıyor. Uçuş modeli Angle Mode: maks yatış 60°, toplam hız 120 km/h (dalışta aşılabilir), throttle dikey komut.

> **SONUÇ NOTU (2026-07-06):** Bu spec büyük ölçüde UYGULANDI (tarihî belge). Sonradan değişenler:
> - FSM durum adları yeniden adlandırıldı: `TAKIP`→`YAKLASMA`, `GORSEL_GUDUM`→`GORSEL_TAKIP`
>   (tek kaynak: `arac/fsm_adlari.py`); aşağıdaki tarihî adlar koda birebir uymaz.
> - Pose modeli ARTIK VAR: `models/talon_pose.pt` (Berat, yolo11m-pose; registry'den hot-swap) —
>   satır ~62'deki "henüz eğitilmedi / dataset işaretleme sürüyor" ifadesi tarihîdir. Eğitim
>   zinciri iskeleti de hazır: `arac/egitim/dataset_dogrula.py` + `pose_egit.py`.
> - Keypoint sırası "dataset yaml'ından doğrulanacak" varsayımı (satır ~125) yerine DENEYSEL
>   bulundu (`pose/poz_cozucu.EGITIM_SIRASI`, 87 kare) ve 3B tablonun TEK KAYNAĞI
>   `pose/talon_keypoints.json` oldu (satır ~119'daki "koda sabit gömülür" gömülü tablo artık yedek).

**Başlamadan önce oku:** `CLAUDE.md`, `MEVCUT_DURUM.md`, `sdk/SDK_README.md` (v0.0.5 uçuş modeli, tilt, telemetri davranışı), `web/server.py`, `detection/gorsel_tespit.py`, `guidance/ana_kontrol.py`, `guidance/ibvs_guidance.py`, `sdk/drone_sdk.py` (attitude telemetrisinin alanları için), `web/index.html`. Mevcut convention'lara (Türkçe isimlendirme, Cfg deseni, thread yapısı) uy.

---

## Çalışma düzeni

- **İlk iş:** `yarisma-pipeline` adlı yeni git branch'i aç; tüm çalışma orada yapılır (main'deki çalışan sistem refaktör bitene dek bozulmaz).
- **Fazlar sırayla, geçişler OTOMATİK:** Her fazın kabul kriterlerini KENDİN doğrula ve sağlanınca kullanıcı onayı beklemeden sonraki faza geç. Kod-içi kriterleri (unit testler, sözleşme/format kontrolleri, import/başlatma testleri) yazdığın test ve scriptlerle kendin koş; kriter sağlanmıyorsa düzelt ve tekrar dene.
- **Sim koşusu gerektiren doğrulamalarda protokol:** (FAZ 0 sanity ölçümü, CMC işaret testi, PnP-vs-GPS koşusu, OIPN açık/kapalı kıyası gibi) önce ölçüm scriptini/aracını yaz, sonra dur ve kullanıcıdan YALNIZCA sim hazırlığını iste — net, adım adım talimatla: "oyunu başlat, Play moduna al, hedefi şöyle konumlandır (ör. sabit uçuş / dönüş manevrası), hazır olunca yaz." Hazır onayı gelince ölçümü/koşuyu KENDİN çalıştır, çıktıyı (CSV/log) KENDİN oku, kriteri KENDİN değerlendir, sonucu kısaca raporla ve geçtiyse otomatik devam et.
- Kullanıcıyı yalnız iki durumda meşgul et: sim hazırlığı gerektiğinde ve kendi başına çözemediğin bir kriter ihlalinde.
- Her faz sonunda branch'e anlamlı mesajla commit at (faz adı + geçen kriterler).

---

## Mimari ilkeler — ne nerede yaşar

**Dosya = sorumluluk. Döngü = zamanlama.** Frame-senkron işler (tespit, takip, PnP) aynı döngüde ardışık çalışır, aralarında thread/kuyruk sınırı yoktur. Güdüm 50 Hz kendi thread'inde çalışır ve algının son çıktısını lock'lu snapshot olarak okur.

```
[oyun penceresi] ──frame──► detection/algi_hatti.py  (YOLO thread'inde, tek döngü)
                              ├─ gorsel_tespit.py   (YOLO inference: bbox+conf, pose ise +keypoints)
                              ├─ takip.py           (ByteTrack + gyro-CMC → onaylı track)
                              └─ talon_pose_estimator.py (PnP → relatif konum + φ_T/ψ_T)
                                        │
                              AlgiCiktisi (tek veri yapısı, timestamp'li; λ̇/Vc türevleri
                              BURADA, algı timestamp'iyle hesaplanır)
                                        │  lock'lu snapshot
                                        ▼
[SDK telemetri] ──► guidance/ana_kontrol.py (50 Hz thread — FSM)
                      ├─ guidance/kilit_kurali.py   (§6.1.4 sayaç, saf mantık)
                      ├─ guidance/gudum_yasasi.py   (APN + OIPN; PnP geçersizse ibvs fallback)
                      └─ iletisim/hakem_istemci.py  (kilit paketi + telemetri, sim'de stub)
                                        │
                                        ▼ komutlar (throttle/pitch/roll/yaw) → SDK → oyun
```

**Türev kuralı:** λ̇ (LOS açısal hızı) ve Vc (kapanma hızı) algı döngüsünde, algı frame timestamp'leriyle hesaplanır. Güdüm thread'i hazır değerleri tüketir. Sebep: algı FPS'i güdüm frekansının (50 Hz) altındaysa güdüm aynı ölçümü birden fazla kez görür (zero-order hold — yeni veri gelene dek son değerin tutulması); türev güdüm frekansıyla alınırsa sıfırlanma/çift sayım hataları oluşur.

**Görüntü kaynağı ve domain tutarlılığı:** Algı hattına giden kare, `server.py`'nin **mss ile oyun penceresi bölgesinden** yakaladığı görüntüdür (`dedektor_dongusu` thread'i). `pencere_yakala.py`'nin pencere-içeriği yakalama yolu `PENCERE_YAKALA_AKTIF=False` ile bilinçli kapalıdır ve bu refaktörde değiştirilmez (oyun penceresi görünür/önde kalmalı). Arayüzdeki "📡 Görüntüyü Bağla" akışı (tarayıcı pencere paylaşımı) yalnızca gösterim/overlay içindir — **algı hattı o görüntüyü ASLA kullanmaz.** Eğitim dataseti de aynı kaynaktan (oyun görüntüsü) toplanmaktadır; bu domain tutarlılığı (train–inference dağılım uyumu: kaynak değişirse sıkıştırma/ölçekleme/overlay artefaktları modelin eğitimde görmediği bir dağılım yaratır) bozulmayacak.
**Çözünürlük–K bağı:** K piksel cinsindendir; f_x doğrudan yakalanan görüntünün piksel genişliğine bağlıdır. Oyun penceresi boyutu koşular arasında sabit tutulur; değişmesi gerekirse `kamera_model.py` çözünürlüğü parametre alır ve K aynı HFOV=125°'den yeni çözünürlükle yeniden türetilir (aspect W/H yalnızca türetilen VFOV'u değiştirir, f_x'i değil).

**Model yokluğunda davranış (graceful degradation — bir bileşen eksikken sistemin alt kademede çalışmayı sürdürmesi):**

| Bileşen | Model gereksinimi | Model yokken davranış |
|---|---|---|
| Tespit | ZORUNLU — `models/best.pt` (talon-eğitimli, repoda mevcut) asgari modeldir | Alternatifi yoktur: COCO-pretrained genel YOLO'da "talon" sınıfı bulunmaz, güvenilir tespit üretemez. Tespit modeli yoksa sistem açık hata ile başlamaz |
| Takip | MODEL DEĞİLDİR — ByteTrack bir algoritmadır (Kalman + eşleştirme mantığı); ağırlık/eğitim/dataset gerektirmez | Her zaman aktif |
| Pose → PnP → OIPN | OPSİYONEL — talon-pose .pt (henüz eğitilmedi; dataset işaretleme sürüyor) | Otomatik pasif: `keypoints` alanı yok → PnP `gecerli=False` → OIPN terimi 0 → güdüm IBVS fallback'te. **Kilit sayacı ve angajman bbox+track tabanlıdır; pose modeli olmadan +400/+500 hattı TAM çalışır** |

Sistem her aşamada "pose'suz mod"da uçtan uca çalışır durumda tutulur; pose modeli hazır olduğunda `models/` klasörüne koyup Cfg'de göstermek yeterlidir, başka kod değişikliği gerekmez.

---

## FAZ 0 — `detection/kamera_model.py` kurulumu + K sanity ölçümü (İLK ADIM)
FOV convention netleşti: **125° YATAY (HFOV).** K matrisi (kamera iç parametre matrisi; f_x, f_y odak uzaklıkları ve c_x, c_y optik merkez, piksel cinsinden) doğrudan kurulur — hem PnP hem gyro-CMC homografisi K kullanır, ikisi AYNI K'dan beslenmek zorunda:
- f_x = W / (2·tan(62.5°)) ≈ 0.2603 · W  (örn. 1920 px genişlikte f_x ≈ 500 px)
- f_y = f_x (kare piksel varsayımı — pikseller fiziksel olarak kare; oyun/render motorlarında standart), c_x = W/2, c_y = H/2, distorsiyon = 0
- Türetilen, bilgi amaçlı (16:9): VFOV ≈ 94.4°, DFOV ≈ 131.2°

`kamera_model.py`: K (çözünürlük parametreli), distorsiyon=0 varsayımı, kamera-gövde montaj dönüşümü **R_mount = 25° pitch-up** (v0.0.5: FPV kamera burnu 25° yukarı bakar). PnP oryantasyon zinciri, gyro-CMC, IBVS dikey referansı (VIS_EY_REF) ve LOS/bearing hesapları tilt'i BURADAN okur — koda ikinci bir 25° sabiti yazılmaz. Her tüketici buradan import eder.

**Sanity ölçümü (zorunlu, tek sefer):** Talon'u bilinen mesafede yakala (Z: temiz konum farkından; hedef GPS'i bozuk olduğundan hedefi sabit tutup birkaç saniyelik medyan al). Kanat açıklığının piksel genişliği w_px'i ölç (kanat çizgisi görüntü düzlemine yaklaşık paralelken — hedefe önden/arkadan bakış; hedef görüntü merkezine yakın tutulur — distorsiyon=0 varsayımı merkezde en güvenlidir ve tilt 25° nedeniyle bu, drone burnunun hedefin ~25° altını göstermesi demektir). Beklenen w_px = f_x · 1718 / Z ile karşılaştır. **Sapma > %10 ise dur ve işaretle** — HFOV bilgisi, çözünürlük varsayımı veya ölçüm prosedüründen biri hatalı demektir; körlemesine devam edilmez. Bulguyu `MEVCUT_DURUM.md`'ye tarih+ölçümle yaz.

**Kabul:** K tek kaynaktan, çözünürlük parametreli; sanity ölçümü tabloda (Z, w_px ölçülen, w_px beklenen, sapma %); tilt zinciri tanımlı.

---

## FAZ 1 — Takip: yeni dosya `detection/takip.py`

### ByteTrack (tek-hedef sadeleştirmesiyle, çoklu track destekli)
- **BYTE association:** tespitler conf'a göre ikiye ayrılır (yüksek eşik ~0.5, düşük eşik ~0.1, Cfg'de). Yüksek conf'lular mevcut track'lerle önce eşleştirilir (IoU); eşleşmeyen track'ler düşük conf'lularla ikinci tur eşleştirilir. **Düşük conf'lu tespit yeni track başlatamaz, yalnızca mevcut track'i sürdürebilir.** Değer: parazit/blur anında conf düşen Talon track'i kopmaz.
- Track durumları: TENTATIVE → (min_hits=5 ardışık eşleşme) → CONFIRMED → (eşleşme yok) → LOST/coast → (max_coast aşımı) → REMOVED. **min_hits=5, mevcut FSM'deki "5 kare YOLO onayı" kuralını devralır** — ana_kontrol'deki ham kare sayacı kaldırılır, FSM tracker durumunu sorgular.
- Tek hedef beklenir ama çoklu track tutulur: yanlış pozitifler (bulut, yer nesnesi) ayrı track açar ve tipik olarak CONFIRMED olamadan ölür — bu, −30 puanlık yanlış kilit paketine karşı zamansal filtredir. FSM'e yalnızca "en iyi CONFIRMED track" (en uzun yaşayan / en yüksek ortalama conf) sunulur.
- Kalman: görüntü düzleminde CV modeli (state: cx, cy, alan, en-boy + hızları). Coast (ölçümsüz tahminle track'i sürdürme) max ~0.5 sn (Cfg'de).

### Gyro-CMC (kamera hareket telafisi)
- Avcının attitude'u (temiz telemetri) frame timestamp'lerine enterpole edilir; frame arası dönüş R_Δ'dan **H = K·R_Δ·K⁻¹** homografisi kurulur, tüm track tahminleri (Kalman ortalamaları) eşleştirme öncesi bu H ile warp edilir.
- Pure rotation homography kamera yalnız dönerken derinlikten bağımsız exact'tir; translasyon bileşeni uzak hedefte ihmal edilebilir (≈0.4 m frame-arası öteleme, 50 m hedefte <1°) — asıl bozucu rotasyondur (100°/sn manevrada frame arası ~2° ≈ onlarca piksel).
- Tilt ≠ 0 olduğundan gövde attitude farkı kamera çerçevesine **montaj dönüşümüyle taşınır**: R_Δ,kam = R_mount^T · R_Δ,gövde · R_mount (eşlenik/benzerlik dönüşümü — aynı fiziksel dönüşün başka eksen takımında ifadesi). R_mount `kamera_model.py`'den; bu adım atlanırsa CMC pitch/yaw karışımını yanlış eksene yazar.
- **Görüntü-tabanlı CMC (ORB/ECC — feature eşleme veya yoğunluk hizalamayla global hareket kestirimi) KULLANILMAZ:** gökyüzü sahnesi feature'sızdır, kestirimler güvenilmez ve hesap maliyeti gereksizdir.
- Eksen/işaret doğrulaması zorunlu: sim attitude konvansiyonu (SDK'dan) → kamera çerçevesi dönüşümünde işaret hatası CMC'yi düzeltme yerine bozucu yapar. Test: hedef sabitken avcıya saf yaw/roll step'i ver; CMC açıkken track tahmini bbox üstünde kalmalı, kapalıyken kaymalı. Bu testin log/ekran kaydı kabul kriteridir.

### Çıktı sözleşmesi
`AlgiCiktisi.hedef = {track_id, bbox, cx, cy, conf, keypoints?, tespit_mi, track_durumu}`
- `tespit_mi`: bu frame'de gerçek tespit eşleşti mi (coast'ta False). **Kilit sayacı yalnızca tespit_mi=True frame'lerde işler** — coast ID sürekliliği sağlar ama görsel teyit sayılmaz (şartnamenin kilitlenme tanımına dürüst yaklaşım; coast'ta bbox tahminidir, ekran kaplama oranı da güvenilmezdir).
- Geriye uyumluluk: `{cx, cy, conf}` çekirdeği korunur.

**Kabul:** parazitli sahnede (conf dalgalanırken) track ID sabit kalıyor; sahte nesne track'i CONFIRMED olamıyor; CMC işaret testi kanıtlı; coast frame'leri loglarda tespit_mi=False görünüyor.

---

## FAZ 2 — PnP: yeni dosya `detection/talon_pose_estimator.py`
Girdi: CONFIRMED track'in keypoints'i (pose modeli yüklüyse; detect modelinde bu faz otomatik pasif).

### 3D model noktaları (mm, origin = AM — tablo referans merkezi; gövde çerçevesi sağ-el: +X kuyruğa/aft, +Y yukarı, +Z sol kanat)
| Keypoint | X — boylam | Y — düşey | Z — açıklık |
|---|---|---|---|
| burun | −550.3 | −13.2 | 0.0 |
| kuyruk_ucu (gövde arka) | +536.8 | −6.5 | 0.0 |
| sol_vtail | +531.6 | +179.3 | +225.6 |
| sag_vtail | +531.6 | +179.3 | −225.7 |
| sol_kanat | +101.7 | +44.9 | +859.0 |
| sag_kanat | +101.7 | +44.9 | −859.0 |

1718 mm gerçek ölçek (Z açıklık ±859.0; SDK'da teyitli). Koda sabit gömülür. **Origin AM olduğundan tvec doğrudan hedef merkezinin kamera-çerçevesi konumudur** — güdüm nişan noktası ve PnP-vs-GPS kıyası için burun-origin'e göre avantajlı (yarım gövde boyu ~550 mm sistematik ofset yok; GPS'in raporladığı referans nokta ile AM arasında kalabilecek küçük ofset kıyas bandında yine görünebilir, görülürse not düşülür). Not: SDK gövde uzunluğunu 1100 mm bildirir; modelde burun→kuyruk_ucu boylam farkı 550.3+536.8 = 1087.1 mm (%1.2 sapma) — ölçek teyidi reprojection error istatistiğiyle yapılır, sistematik uyuşmazlık görülürse işaretlenir, model noktaları elle "düzeltilmez". OpenCV kamera çerçevesi farklıdır (+X sağ, +Y aşağı, +Z ileri); `solvePnP` object çerçevesini olduğu gibi alır — eksenleri elle "düzeltme", dönüşüm rvec/tvec'tedir.

### Çözüm ve kapılar
- Keypoint conf eşiği (başlangıç 0.5, Cfg) üstü **≥4 nokta yoksa** `gecerli=False` (PnP min 4 nokta; 3 noktada P3P dörde kadar çözüm belirsizliği verir)
- `cv2.solvePnPRansac` (RANSAC — rastgele alt-kümelerle uydurup aykırıları dışlayan kestirim) + `SOLVEPNP_ITERATIVE` refine; 6 nokta non-coplanar, iyi koşullanmış
- **Reprojection error** (çözülen pozla 3D noktaları geri yansıtıp ölçülen piksellerle ortalama fark) > eşik (başlangıç 8 px, Cfg) → reddet. Güdüme çöp poz gitmesini engelleyen ana kalite kapısı.
- **Keypoint index sırası dataset yaml'ından doğrulanacak** (varsayım — tablo sırası: burun, kuyruk_ucu, sol_vtail, sag_vtail, sol_kanat, sag_kanat). Yanlış sıra sessizce saçma çözüm üretir — ilk belirti anormal reproj error. Eğitimde flip augmentation için `flip_idx` (yatay aynalamada sol/sağ keypoint çiftlerinin de yer değiştirmesi) tanımlı mı teyit et; değilse arayüzde kalıcı uyarı.

### Oryantasyon
- `cv2.Rodrigues(rvec)` → R (gövde→kamera); avcı attitude'u + kamera_model montaj dönüşümüyle **dünya çerçevesine** çevir → hedef roll φ_T, yaw ψ_T
- Açı-uzayında low-pass (wrap-around'a dikkat: farkı [−180°,180°]'e sar), τ≈0.3 sn (Cfg)
- Oryantasyonun EKF'e fuse edilmesi (Option A) kapsam dışı — ayrı iterasyon

Çıktı: `{gecerli, tvec, mesafe, phi_T, psi_T, reproj_err, kullanilan_kp, rel_konum_dunya}` → AlgiCiktisi'na eklenir. tvec **kamera çerçevesindedir**; dünya-çerçevesi relatif konum, kamera→gövde→dünya zinciriyle (R_mount 25° tilt burada devreye girer) algı hattında hesaplanır ki güdüm hazır dünya-LOS'u tüketsin.

**Kabul:** sabit hedefe PnP mesafesi vs temiz-GPS mesafe farkı ölçülüp raporlanıyor (bant uydurulmaz, ölçülür); reproj eşiği aşan frame'ler reddedilip loglanıyor; <4 kp durumunda sistem sessizce güdüm fallback'ine düşüyor.

---

## FAZ 3 — Güdüm + FSM + Angajman

### 3.1 `guidance/gudum_yasasi.py` — APN + OIPN
GORSEL_GUDUM birincil hattı. PnP geçerliyse LOS vektörü PnP relatif konumdan; λ̇ ve Vc algı hattında hazır (türev kuralı).

**a_cmd = N·Vc·λ̇ + (N/2)·a_T + β·a_ff**
- N=4 başlangıç (Cfg)
- a_T: fusion çıktısında hedef ivme kestirimi varsa oradan; yoksa 0 bırak, yorumla belgele (**fusion/'a dokunma**)
- **OIPN:** a_ff = g·tan(φ_T), hedef hız vektörüne dik yatayda, komuta LOS'a dik izdüşümle. Fizik: koordineli dönüşte (kayışsız dönüş; yatay kaldırma bileşeni merkezcil kuvveti sağlar) ψ̇ = (g/V_T)·tan(φ_T) — roll, heading değişiminden ÖNCE gelir, erken manevra sinyali budur. V_T fusion/EKF'ten (PnP relatif ölçümdür, hedef yer hızını tek başına veremez).
- β=0.3 başlangıç (konservatif), canlı tune'da slider; |φ_T|<5° dead-zone (eşik altı girdinin yok sayıldığı bölge — gürültü roll'ü sızmasın); PnP geçersizse β terimi otomatik 0
- Çift sayım uyarısı (koda yorum olarak): EKF a_T'si manevrayı yakalamaya başlayınca OIPN aynı manevrayı ikinci kez ekleyebilir → β konservatif başlar, loglardan ayarlanır
- **Fallback:** PnP geçersiz frame'lerde `ibvs_guidance` (bbox merkez hatası) devreye girer — frame bazında, komutta süreksizlik sıçraması olmadan (geçiş yumuşatması varsa belgele). IBVS silinmez, güvenlik ağıdır.
- Konumlandırma: pose/OIPN **orta safha kilit-tutma/takip iyileştirmesidir**; terminal vuruş mantığına dokunulmaz.

### 3.2 `guidance/kilit_kurali.py` — §6.1.4 sayacı (saf, unit-test edilebilir mantık)
Girdi (her algı frame'i): bbox merkez (cx,cy), ekran kaplama oranı, tespit_mi, conf, track_durumu, t.
- AV sınırı: yatay %25–75, dikey %10–90 (görüntü boyutuna oranla)
- Kaplama eşiği: Cfg'de 0.06 başlangıç (şartname %5; −30 yanlış-kilit cezasına karşı pay bırakılmış muhafazakâr eşik)
- **Sayaç yalnızca şu koşulların HEPSİ sağlanınca işler:** üretim conf eşiği geçildi + track CONFIRMED + tespit_mi=True + merkez AV içinde + kaplama ≥ eşik
- 10 sn kayan pencerede kümülatif ≥5 sn → `kilit_tamam=True` (bir kez tetiklenir, kenar tetikli)
- Ayrıca `surekli_kilit_sn` üretir (kesintisiz sayaç) — angajman ön şartı için
- Saf fonksiyon/sınıf: sim olmadan sentetik girdiyle unit test yazılacak (pencere kenarları, kesinti, coast durumları)

### 3.3 FSM güncellemesi — `guidance/ana_kontrol.py`
Durumlar: **ARAMA → TAKIP → GORSEL_GUDUM → KILIT_BILDIR → ANGAJMAN**
- ARAMA→TAKIP: tracker'da CONFIRMED track var (eski "5 kare" kuralı buraya taşındı)
- TAKIP→GORSEL_GUDUM: mevcut handoff koşulu (mesafe) korunur; GPS güdümü (PD+lead) ARAMA/TAKIP'te aynen kalır
- GORSEL_GUDUM: gudum_yasasi aktif; kilit_kurali sayacı işler; hedef GNSS verisi bu fazda KULLANILMAZ
- GORSEL_GUDUM→KILIT_BILDIR: `kilit_tamam` → hakem_istemci'ye kilit paketi (+400 garanti altına alınır)
- KILIT_BILDIR→ANGAJMAN: bildirim gönderildi VE `surekli_kilit_sn ≥ 3.0` (angajman için kesintisiz kilit ön şartı — kümülatif 5 sn'den bağımsız ayrı koşul). **Erken angajman yasak: sıralama +400'ü önce garanti eder, +500 sonra denenir.**
- ANGAJMAN: terminal vuruş (mevcut mantık korunur)
- Track kaybı (REMOVED) → duruma göre TAKIP/ARAMA'ya gerileme; geçişler loglanır

### 3.4 `iletisim/hakem_istemci.py` — stub
- Arayüz: `kilit_paketi_gonder(t, konum, kilit_durumu)`, `telemetri_gonder(...)` (1–5 Hz, sistem saati timestamp)
- Sim'de gerçek sunucu yok: dosyaya/loga yazar. Amaç: FSM'deki kilit→bildir→angajman sıralamasını kodda somutlaştırmak; yarışma günü gerçek istemci aynı arayüze takılır.

**Kabul (Faz 3):** OIPN kapalı + pose'suz koşuda davranış mevcut hatla eşdeğer (regresyon yok); kilit_kurali unit testleri geçiyor (pencere kenarı, kesinti, coast senaryoları); FSM sıralaması loglarda görünüyor: kilit_tamam → paket → 3 sn sürekli → ANGAJMAN; dönen hedefe OIPN açık/kapalı iki koşu CSV'den kıyaslanabiliyor.

---

## FAZ 4 — Arayüz + loglama (`web/`)
- Track paneli: ID, durum (TENTATIVE/CONFIRMED/LOST), tespit_mi göstergesi
- **Kilit sayacı göstergesi:** kümülatif sn / 5.0 + 10 sn pencere doluluk çubuğu + AV sınır çerçevesi overlay'de + kaplama oranı
- PnP paneli: relatif X/Y/Z, mesafe, φ_T/ψ_T, reproj_err
- **"HEDEF GNSS: KULLANILMIYOR"** rozeti — GORSEL_GUDUM ve sonrasında yeşil (yarışma videosu zorunluluğunun kanıt paneli)
- OIPN AÇIK/KAPALI anahtarı + β slider (canlı tune)
- Uçuş CSV genişletmesi: `track_id, track_durumu, tespit_mi, kumulatif_kilit_sn, surekli_kilit_sn, pnp_gecerli, reproj_err, phi_T, a_PN, a_APN_terim, a_OIPN_terim, beta, fsm_durum`

---

## ÇIKAR / DEĞİŞTİR / KORU / DOKUNMA — özet tablo

| Öğe | Karar | Not |
|---|---|---|
| `guidance/ibvs_guidance.py` | DEĞİŞİR | Birincil güdümden fallback'e iner. **VIS_EY_REF 25° tilt telafisi KORUNUR** (v0.0.5: kamera 25° yukarı bakıyor) — ancak değer yerel sabit olmaktan çıkar, `kamera_model.py`'deki tek kaynaktan okunur |
| `guidance/ana_kontrol.py` | DEĞİŞİR | FSM yeni durumlar; "5 kare" ham sayacı ÇIKAR → tracker CONFIRMED sorgusu; kilit sayacı kilit_kurali'ya taşınır |
| `detection/gorsel_tespit.py` | KORU+GENİŞLET | Çıktıya opsiyonel keypoints; `{cx,cy,conf}` çekirdeği değişmez |
| `detection/pencere_yakala.py` | KORU | — |
| `fusion/` | DOKUNMA | inovasyonlu_j dt işi ayrı bekleyen iş (v0.0.5: hedef GPS 5 Hz → dt 0.2; bu prompt'un kapsamında DEĞİL) |
| `web/server.py` | DEĞİŞİR | `dedektor_dongusu` thread'i artık algi_hatti'yı çağırır; beyne aktarım `beyin.set_gorsel_tespit(det)` yerine AlgiCiktisi snapshot arayüzüne genişler (mevcut arayüz korunarak sarılabilir); **mss yakalama yolu ve 50 Hz timing korunur** |
| `sdk/`, `arsiv/` | DOKUNMA | — |
| Kök `avci_gudum.py` (CBDR) | DOKUNMA | Entegrasyonu ayrı karar; bu refaktörde ele alınmaz |
| YENİ | — | `detection/kamera_model.py`, `detection/takip.py`, `detection/talon_pose_estimator.py`, `detection/algi_hatti.py`, `guidance/gudum_yasasi.py`, `guidance/kilit_kurali.py`, `iletisim/hakem_istemci.py` |

## Kısıtlar
- Guidance'a giden **üretim conf eşiği yerinde kalır** (muhafazakâr; −30 yanlış kilit cezası). Görselleştirme eşiği ayrıdır ve kilit/angajman kararını ASLA beslemez
- 50 Hz kontrol thread timing'ine müdahale yok; algı kendi hızında, snapshot'la konuşur
- Görüntü yakalama yolu (mss, oyun penceresi bölgesi) değiştirilmez; algı hattı tarayıcı paylaşım görüntüsünü ASLA kullanmaz
- `CLAUDE.md` kuralları geçerli
- Kapsam dışı: MPC/Apollonius, Option A (oryantasyon→EKF fuse), avci_gudum.py entegrasyonu, model registry/hot-swap altyapısı (ayrı prompt), görüntü-tabanlı CMC

## Test planı (fazlarla hizalı)
1. K sanity ölçümü: Z, w_px ölçülen/beklenen, sapma % (eşik %10)
2. CMC işaret testi (saf yaw/roll step, hedef sabit) + parazit altında ID sürekliliği koşusu
3. Sabit hedefe PnP-vs-GPS mesafe hata grafiği
4. kilit_kurali unit testleri (sentetik: pencere kenarı, kesintili kilit, coast)
5. Uçtan uca: dönüş yapan hedefe tam pipeline; loglarda ARAMA→TAKIP→GORSEL_GUDUM→KILIT_BILDIR→ANGAJMAN sıralaması ve OIPN açık/kapalı kıyası

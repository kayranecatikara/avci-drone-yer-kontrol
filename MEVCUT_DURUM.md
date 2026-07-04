# Avcı Drone — Mevcut Durum Brifingi (Claude için tanıtım belgesi)

> **Bu belge ne işe yarar?** Yeni bir Claude oturumuna projeyi sıfırdan tanıtmak için hazırlandı.
> "Şu an neredeyiz, ne çalışıyor, ne bekliyor, hangi kurallar değişmez" sorularının hepsi burada.
> Kod ile birebir tutarlıdır; okuyunca dosyaları tek tek gezmene gerek kalmadan sisteme hâkim olursun.
> (Kalıcı kurallar için ayrıca `CLAUDE.md` var; bu belge onun üstüne **güncel durumu** koyar.)

> **🎬 MÜSABAKA VİDEO KAYDEDİCİ — FİNAL AŞAMASI ZORUNLULUĞU (2026-07-04, ŞİMDİ KODLANMAZ).**
> Müsabaka (gerçek uçuş) teslimi için ayrı bir kayıt zorunluluğu var; **kod finalde yazılır,
> spec burada dursun.** Gereksinimler (Teslim Esasları):
> - **Kaynak:** orijinal FPV karesinin ÜZERİNE canlı çizim — **ekran/masaüstü kaydı KABUL EDİLMEZ**
>   (yani program karesini alıp encode eden bir kaydedici; OBS/ekran-capture değil).
> - **Overlay:** hedef üstünde canlı **#FF0000 (saf kırmızı) kilit dörtgeni** (çizgi ≤3 px —
>   `KilitCfg.CIZGI_PX`) + **sağ üstte ms hassasiyetli SUNUCU saati** (yerel saat değil, hakem/
>   sunucu zamanı; senkron).
> - **Format:** H.264 / MP4; **postprocessing YOK** (canlı, ham); **OpenCV 4.5 + FFPLAY uyumlu**
>   (VideoWriter fourcc `avc1`/`H264`, oynatma ffplay ile sınanır).
> - **Dosya adı:** `[MusabakaNo]_[TakimAdi]_[gg_aa_yyyy].mp4`.
> - **Doğrulama:** her kare dörtgeni `arac/kilit_dortgeni.py` kurallarını geçmeli (≥%90 içerme,
>   merkez farkı, çizgi ≤3 px). Kaydedici bu doğrulamayı canlı çağırır.
> - **MUAF:** **Simülasyon Uçuş Kanıt Videosu bu şartlardan MUAF** (kendi dokümanı: arayüz +
>   kod ekranı + sesli anlatım isteniyor; YouTube liste dışı, ham/postprocessing kısıtı yok).
>   Bu iki video KARIŞTIRILMAZ — müsabaka kaydedici yalnız gerçek uçuş teslimi içindir.
> **Kod yeri (finalde):** `web/musabaka_kaydedici.py` (yeni); `arac/kilit_dortgeni.py` doğrulama
> hazır; dörtgen bbox pipeline'dan (AlgiCiktisi.hedef) gelir.

> **🔔 FAZ 1-4 KOD TAMAM (2026-07-04): pipeline uçtan uca kurulu, pose'suz TAM çalışır.**
> takip (ByteTrack+gyro-CMC) → PnP → APN/OIPN → kilit_kurali (§6.1.4, kaçak toleransı
> dahil) → FSM (ARAMA→TAKIP→GORSEL_GUDUM→KILIT_BILDIR→ANGAJMAN) → hakem stub → FAZ 4
> arayüz (kilit sayacı+AV çerçevesi+HEDEF GNSS rozeti+OIPN slider+CSV). **~91 birim testi.**
> Regresyon kuralı kanıtlı: OIPN kapalı + pose'suz = mevcut IBVS birebir.
>
> ## 🎮 TEK SİM OTURUMU PLANI (pose'suz; taze oyun başlatınca, tek oturum)
> Menü: **PLAY (fare) → FLY (fare) → E (klavye)**. Oyun art arda arm sonrası zombileşir →
> her uçuşlu turdan sonra kosu_yonetici otomatik restart eder (ya da elle yeniden başlat).
> 1. **FSM PROVASI (uçtan uca, canlı panel):** `python main.py` → tarayıcı → **Görev Başlat**.
>    İzle: FSM durumu ARAMA→TAKIP ilerliyor mu; FAZ 4 panelleri (kilit sayacı, AV çerçevesi,
>    HEDEF GNSS rozeti, OIPN slider) canlı mı; regresyon (GPS yaklaşma davranışı eskiyle aynı).
>    **10 kalem tek kadrajda okunuyor mu → `docs/video_prova_kontrol.md` kontrol listesini
>    işaretle** (özellikle kalem 7 kayıp/yeniden-tespit banner'ı, kalem 8 güdüm komutu, kalem
>    10 başarı ekranı). **Zayıf detection hedefi göremezse görsel kilit olmaz → kilit paneli
>    `engel` alanı** hangi koşulda takıldığını gösterir (güncel koşullar: `dortgen_tasma` /
>    `kaplama_dusuk` [EKSEN: max(w/W,h/H)<0.06] / `AV_disi_yatay|dikey` / `dusuk_conf` /
>    `track_onaysiz` / `coast` / `hedef_yok`). Bu bir ÖLÇÜM: modelin FSM'i besleyemediğini
>    kanıtlar. Kaçak toleransı 200 ms (kümülatifi etkilemez; yalnız kesintisiz sayaçta köprü).
>    İyi model gelince kilit tamamlanır.
> 2. **CMC ROLL ±8°:** `python arac/kosu_yonetici.py cmc-test` (yaw zaten GEÇTİ, oran 0.27;
>    roll fazı ±8° küçük genlik, hedef merkezde). **Geçti eşiği:** roll_oran < 0.5.
> 3. **MENÜ FARE-TIK KALİBRASYONU:** PLAY/FLY buton koordinatlarını bir kez ölç
>    (pencere W/H yüzdesi), `kosu_yonetici._play_otomasyonu`'na fare-tık ekle.
>
> ## 🏋️ EĞİTİM ZİNCİRİ (PLAN modundan çıkışa hazır; `arac/egitim/`)
> **Dataset nereye:** ultralytics pose formatı (images/ + labels/ + data.yaml). data.yaml'da
> **kpt_shape [6,3], flip_idx [0,1,3,2,5,4]** (sol/sağ çift!), names: talon, train/val yolları.
> **Komut (sırayla):**
> ```
> python arac/egitim/dataset_dogrula.py <data.yaml>        # kpt/flip/split kapısı; KRİTİK hata->eğitme
> python arac/egitim/pose_egit.py --data <data.yaml> --agirlik models/yolo26m_pose_best.pt \
>     --calistir --epochs 100 --imgsz 640 --isim yolo_pose_talon_v11
> ```
> **Çıktı:** en iyi .pt → `models/<isim>.pt` + yanına .yaml (imgsz/sema/açıklama) otomatik;
> VAL mAP raporu (box + pose mAP50/50-95) basılır. **Kıyas:** yeni modeli arayüzden
> **↻ Tara → Yükle**, canlı panelde FPS/latency/conf/**PnP-uygun oran**ı eskiyle karşılaştır.
> mAP eğitim-içi; ASIL kabul PnP-uygun oran (sim `pnp-test`).
>
> ## 📗 "İYİ MODEL GELDİĞİNDE" RUNBOOK (kod yazmadan, liste takibiyle entegrasyon)
> **(i)** `.pt`'yi `models/`'a koy + yanına `<ad>.yaml` (`imgsz: 640`, `sema: kuyruk_ucu`,
> `aciklama: ...`). **(ii)** Arayüz → **↻ Tara → Yükle**; task/şema rozetini kontrol
> (pose ise kpt_shape=[6,3] yeşil; değilse reddedilir). **(iii) DETECTION modeli:**
> canlı panelden conf/tespit sayısı/FP davranışını oku; **FSM provasını tekrarla — bu kez
> kilit TAMAMLANMALI** (kilit paneli kümülatif 5s'ye ulaşır, `engel` boşalır). Geçti eşiği:
> kilit_tamam=✓, `pnp_uygun` gerekmez (detection). **(iv) POSE modeli — sıralı borç kapatma
> (her adım komut + geçti eşiği):**
> | Adım | Komut | Geçti eşiği |
> |---|---|---|
> | 1. Keypoint görsel teyit (özellikle **sol/sağ**!) | `pnp-test` → `veri/pnp_teyit_*.png` göz kontrolü | 6 nokta 3D tablo sırasıyla eşleşiyor; sol/sağ ters DEĞİL |
> | 2. PnP-uygun oran + reproj | `kosu_yonetici pnp-test` | PnP-uygun >%20; reproj medyan <8 px |
> | 3. Yakın geçişte k* | `pnp-test` (hedef ~5-20 m) | k* `guvenilir`=True; k*≈0.867'ye yakınsa FAZ 0 ile tutarlı |
> | 4. OIPN açık/kapalı CSV kıyası + β | dönen hedefe 2 görev (OIPN AÇIK/KAPALI), `veri/ucus_log_*.csv` a_OIPN_terim | OIPN açıkken kilit-tutma iyileşir (LOS hatası düşer), salınım artmaz; β loglardan ayarla |
> **Pose borçları "iyi model şart" etiketli — hepsinin komutu yukarıda hazır.**

> **🔔 FAZ 2 — sim doğrulaması: ZİNCİR DOĞRULANDI, model kalitesi 0 (2026-07-04, uçuşlu):**
> `pnp-test` turu (model_yonetici pose → algi_hatti → PnP → AlgiCiktisi → panel) gerçek
> veride HATASIZ koştu. **PnP-uygun %0.0, PnP-geçerli %0.0** (407 kare, 0 tespit): pose
> modeli (`yolo26m_pose_best`, task=pose kpt_shape=[6,3] sema=kuyruk_ucu) hedefi hiç
> göremedi (hedef uzaktı + model "detection gibi kalitesiz"). **Bu başarısızlık DEĞİL
> ÖLÇÜMDÜR** — yeni modelin hedefini sayıyla koyar (>%0). **STATÜ: KOD TAMAM + ZİNCİR
> DOĞRULANDI**; hassas k* + keypoint-sırası görsel teyidi iyi modele/yakın hedefe devredildi.
>
> **🔧 MENÜ AKIŞI (saha bilgisi 2026-07-04):** PLAY (FARE tık) → FLY (FARE tık) → E (KLAVYE).
> Salt-klavye otomasyonu bu yüzden tutmaz; koşu yöneticisi menü otomasyonu best-effort +
> insan fallback (çalışıyor). Fare-tık otomasyonu koordinat kalibrasyonu gerektirir (borç).
>
> **📋 BORÇ LİSTESİ (iyi model / uygun sahne gelince; koşu komutları hazır):**
> 1. Keypoint-sırası GÖRSEL TEYİT (şema kuyruk_ucu mu doğru?) → pose modeli hedefi görünce
>    (yeni model VEYA yakın geçiş). `python arac/kosu_yonetici.py pnp-test --oyun-hazir
>    --oyunu-acik-birak` (hedef YAKIN olmalı; veri/pnp_teyit_*.png keypoints çizili).
> 2. HASSAS k* (HFOV=125 kesin teyit; FAZ 0'dan devir) → PnP-uygun frame + perspektif yeterli
>    (terminal faz, hedef ~5-20 m). Aynı pnp-test komutu; talon_pose_estimator.k_taramasi
>    'guvenilir' bayrağı k*'ı gate'ler. k*≈0.867'ye yakınsa FAZ 0 offset-regresyonuyla tutarlı.
> 3. CMC ROLL fazı (FAZ 1'den) → `python arac/kosu_yonetici.py cmc-test` (roll ±8°, hedef
>    merkezde; yaw fazı zaten GEÇTİ oran 0.27).
> 4. Menü fare-tık otomasyonu (koordinat kalibrasyonu).

> **🔔 FAZ 2 — pose modeli şema keşfi (2026-07-04, metadata):**
> `models/yolo26m_pose_best.pt`: task=pose, **kpt_shape=[6,3]** (6 keypoint, PnP için
> ideal), tek sınıf 'talon', dataset `talon_v10` (Colab `/content/datasets/`; repoda
> YOK). **flip_idx TANIMLI DEĞİL** (model.yaml'da None) → yatay-flip augmentation
> sol/sağ keypoint çiftlerini yer değiştirmez; eğitim iskeletinde ve arayüzde kalıcı
> uyarı. **Keypoint SIRASI metadata'da yok** (sadece sınıf adı) → görsel teyit ŞART
> (FAZ 2 sim doğrulamasında: model tahminlerini gerçek karede çizip 3D tablo sırasıyla
> eşle). PnP object-points seti şema-parametreli (`sema: kuyruk_ucu | motor`); kullanılan
> origin (AM = tablo referans merkezi) tvec referansını belirler, çıktıya yazılır.
> Detection modelleri (3 adet: best.pt aktif, bbox_det_30haziran, best_aircraft_yolo11m)
> + bu pose modeli registry'den kıyaslanacak (hepsi "kalitesiz", yeniler eğitilecek).

> **🔔 FAZ 1 — CMC işaret testi GEÇTİ (2026-07-04, uçuşlu tur):**
> gyro-CMC'nin sim attitude konvansiyonuyla tutarlılığı canlı doğrulandı.
> Yöntem (YOLO'suz, truth reproj hedef pikseli; avcıya yaw osilasyonu): ardışık
> kareler arası CMC-warp'lı hata vs warp'sız hata. **YAW fazı: n=169, hata_HAM
> medyan 13.4 px → hata_CMC medyan 3.7 px (oran 0.27 < 0.5 eşiği) → GEÇTİ** —
> CMC doğru işarette kaymayı ~%73 azaltıyor; ters işaret olsa hatayı artırırdı.
> (Roll fazı yeterli eşleşme vermedi — roll drone'u yatırınca hedef FOV'dan
> çıkıyor; yaw doğrulaması FAZ 1 için yeterli, roll bileşeni f_x'ten bağımsız.)
> **Aynı koşu `kosu_yonetici`'nin uçuşlu-tur + zombileşme protokolünü de canlı
> doğruladı:** oyun otomatik açıldı → arm + irtifa tutma → osilasyon → tur sonrası
> oyun otomatik KAPAT+RESTART → [KOŞU BİTTİ] + bip. FAZ 1 (takip+CMC) KAPANDI:
> kod 18 birim testi + CMC sim doğrulaması. FSM entegrasyonu FAZ 3'te.

> **🔔 FAZ 0 — K sanity bulgusu (2026-07-04, truth-tabanlı ölçüm):**
> **Zincir (K + 25° tilt + attitude) AÇISAL olarak doğrulandı; mutlak kanat-genişliği
> ölçümü küçük-hedef limitinde başarısız — kök neden K DEĞİL, ölçüm prosedürü.**
> Ölçüm: 240 sn pasif/yerden, 3013 kare, siluet yöntemi. Sonuç: w_ölçülen medyan
> ~7-9 px, w_beklenen (kanat uçları tam-zincir izdüşümü, yatış dahil) ~16-18 px,
> oran ~0.40 (sapma −%54, eşik %5). **Ama bu bir K/HFOV hatası değil:** (1) hareket-farkı
> hakemi 3 koşuda tutarlı açısal offset verdi (yatay ~0°, dikey ~−1°, MAD ~4-6°) —
> reprojeksiyon hedefin açısal konumunu doğru koyuyor; fx %54 yanlış olsaydı merkez-dışı
> hedefte offset onlarca derece olurdu. (2) w_ölçülen mesafeden **bağımsız** ~7 px sabit
> (fiziksel değil; yakında büyümesi gerekirdi) — siluet Talon'un tam kanadını değil, hep
> aynı yüksek-kontrast gövde çekirdeğini yakalıyor. Sebep: Talon render'da soluk/küçük
> (40-115 m'de 7-24 px), kanat uçları düşük kontrast (eşik kesiyor) + FPV kromatik
> aberasyon + hedef ara ara güneşe yakın geçiyor + truth GPS gecikmeli (reproj ~100-130 px
> kayıyor). **Pozitif K-doğrulama (offset-vs-merkez-dışılık regresyonu):** f_x ölçek
> kestirimi **k=0.867** (ex −0.55..0.95). **Kaba sanity GEÇTİ:** %54 hata k≈0.46, 2× hata
> k≈2.0 verirdi; k=0.867 → HFOV=125 doğru **mertebede** (2-3× hata YOK). Ama tek koşu
> gürültülü (MAD 9°, yatay medyan koşular arası 0°↔−8°; du~ex eğimi GPS gecikmesiyle
> kirleniyor). **Sonuç: mevcut araçlarla (siluet + hareket hakemi) K %5 hassasiyetle NE
> doğrulanabiliyor NE çürütülüyor** — gürültü tabanı çok yüksek. **KARAR:** kaba sanity
> geçti (mertebe-doğru); HASSAS K teyidi **FAZ 2 PnP reprojection-error'a devredildi**
> (master prompt zaten "ölçek teyidi reproj error ile" diyor — 6 keypoint'in kalibre 3D
> modele uydurulması tek-genişlik ölçümünden çok daha sağlam). FAZ 1 (takip) K'ya
> düşük duyarlı: ByteTrack görüntü düzleminde çalışır; gyro-CMC'de yaw/pitch kaynaklı
> kayma f_x ile ORANTILIDIR (≈f_x·Δθ; yalnız roll bileşeni f'den bağımsızdır — "H=K·R·K⁻¹
> sadeleşir" YANLIŞ gerekçedir). Doğru gerekçe: olası %13 f_x hatası CMC düzeltmesinde ~%13
> artık bırakır, bu IoU eşleşmesini bozmayacak kadar küçüktür. `models/best.pt` küçük
> hedefi göremiyor → ayrı model işi (FAZ 1+).

> **🔔 Güncelleme — Sim v0.0.5 saha davranışları (2026-07-04, FAZ 0 ölçüm oturumları):**
> İki kritik sim davranışı tekrarlanabilir şekilde doğrulandı:
> **(1) TCP dinleyici tıkanması:** art arda bağlan/kop döngülerinden sonra oyun yeni
> bağlantı kabul etmeyebiliyor. Önleme: araçlar TEK TCP oturumunu paylaşır
> (`k_sanity_olcum.olc(drone_baglanti=...)`), koşu sonunda tek düzgün kapanış.
> Çözüm: oyunu KOMPLE yeniden başlat (test edildi); "Play'den çık/gir" alternatifi bir
> sonraki takılmada denenecek. **(2) ARM/UÇUŞ SONRASI ZOMBİLEŞME (3 kez doğrulandı):**
> SDK'dan arm edilip uçulan oturumlarda telemetri bir süre sonra bozuluyor — x,y mutlak
> sabit, attitude tam 0/0/sabit-yaw'da donuk (sıfır titreşim), z komutlardan bağımsız
> ~1-3.5 m/s "sayarak" artıyor (thr=−0.4'e rağmen 110→423 m gözlendi). Yerden/pasif
> koşular gün boyu sağlıklı. Ayrıca thr=0 "hover" irtifayı TUTMUYOR (~+1 m/s süzülme) —
> irtifa ancak kapalı-döngü tutulabiliyor (`k_sanity_olcum` P-tutucusu). **Etkisi:**
> FAZ 1+ uçuş gerektiren testler (CMC işaret testi, PnP-vs-GPS, OIPN kıyası) kısa
> koşular halinde planlanmalı ve **her uçuşlu turdan sonra oyun otomatik yeniden
> başlatılmalı** — `arac/kosu_yonetici.py` (kurulacak otomasyon) bu adımı içerecek.
> FAZ 0 K sanity bu yüzden tamamen pasif/yerden, siluet yöntemiyle ölçülüyor.

> **🔔 Güncelleme — SERT AYRIM / truth politikası (2026-07-03, yarisma-pipeline branch):**
> Truth kanalı (`get_debug_truth`) yalnızca **geliştirme/doğrulama** içindir ve iki yerde
> yaşar: `arac/` scriptleri + çalışma anındaki tek dev kod noktası **`web/dev_truth.py`**
> (CLAUDE.md "SERT AYRIM" + "TESLİM PAKETİ" bölümleri). Uçuş pipeline'ından **tüm truth
> izleri söküldü**: eski "Gerçek GPS (test)" kaynağı, kıyas/SAPMA paneli, Z-teşhis truth
> satırları, uçuş logundaki true_*/gercek_mesafe/nose_off_true kolonları ve
> `_kamera_kontrol` stub'ı KALDIRILDI (bu belgedeki eski anlatımları TARİHSELDİR).
> Yerine: arayüzde **KAYNAK: FİLTRE ↔ GERÇEK (DEV)** butonu (dev_truth yüklüyse görünür;
> aktifken kırmızı bant + uçuş CSV'sinde `hedef_kaynak` etiketi; yalnız midcourse
> beslemesini değiştirir, OTO/GPS/GÖRSEL anahtarına dokunmaz). server.py/index.html'deki
> bağlantı satırları `>>> DEV-ONLY >>>` çitleriyle işaretlidir; `arac/paket_kontrol.py`
> paketlerken dev_truth'u dışlar, çitleri söker, kalan pakette truth/gercek/dev izi tarar.
> Filtre doğrulama: `arac/filtre_dogrulama.py` (RMSE/max/gecikme).

> **🔔 Güncelleme — Simülasyon v0.0.5 (2026-07-02, koordinatörlük maili):**
> (1) **Hedef GPS artık 5 Hz** (yarışma koşulu; önceki sürümlerde 1 Hz idi). (2) Simülasyonda **performans iyileştirmeleri** yapıldı.
> **✅ Uyum UYGULANDI (2026-07-03):** İnovasyonlu J'nin PREDICT zaman adımı **`dt` 1.0 → 0.2** yapıldı ve ilk hız tahmini `(Δkonum)/dt` ile cm/s'ye ölçeklendi (`fusion/inovasyonlu_j_v2.py`; tüm kullanım yerleri varsayılanla kurulduğundan tek noktadan düzeldi). Sentetik testte (50 Hz tik + 5 Hz GPS) eski `dt=1.0` **hız kestirimini bozuyordu** (hata ~16 m/s); `dt=0.2` ile ~1.2 m/s'ye indi. **Kalan:** R/Qp/Qw/gate'i v0.0.5 sim'inde yeniden doğrula. Detaylar §5 (fusion) ve §6.

---

## 1) Proje tek cümlede
**Otonom avcı (kamikaze/interceptor) drone** yazılımı: bozuk GPS ile hedefe yaklaşan, sonra **kameradan (YOLO)**
hedefi tespit edip görsel güdümle kilitlenen bir sistem. Yarışma: **Drones of War / Drone Of War (Teknofest)**.
Simülasyon Unreal Engine tabanlı bir oyun; biz Python tarafında beyni yazıyoruz.

- **Hedef platform:** Talon İHA (sabit kanat; kanat açıklığı 1718 mm, gövde 1100 mm).
- **ASIL AMAÇ:** **Simülasyon Uçuş Kanıt Videosu** aşamasını geçmek. Tüm kararlar video isterlerini
  eksiksiz karşılamaya göre alınır (bkz. §11).

---

## 2) Değişmez çalışma ilkeleri (Claude bunlara UYAR)
Bunlar yarışma kurallarından ve `CLAUDE.md`'den gelir; ihlal edilmez:

1. **Sadece açıklayabildiğimiz şeyi kullanırız.** GPS filtresi olarak yalnızca **İnovasyonlu J**
   (`fusion/inovasyonlu_j_v2.py`) var. IMM-EKF veya bakmadığımız yabancı modüller **entegre edilmez** (Kural 8).
2. **Hazır güdüm yazılımı doğrudan kullanılmaz** (Kural 6). Her yöntem (filtre, öngörülü/lead yönelim, IBVS)
   bizim temiz implementasyonumuz ve takımca açıklanabilir.
3. **Senaryoya aşırı-uydurulmuş (overfit) sabit yok.** ("lock 5.2 sn", "death_plunge" gibi şeyler yasak.)
   Sadece açıklanabilir, genel parçalar entegre edilir.
4. **Çalışan sistemi bozma.** `web/server.py` + `web/index.html` (arayüz), manuel mod, kıyas paneli,
   kaynak geçişi korunur. Güdüm değişiklikleri **`AvciKontrol` içine** gömülür.

**GPS güdümünün rolü (net sınır):** GPS güdümü **öldürücü faz DEĞİLDİR.** Görevi:
(1) bozuk GNSS'i temizlemek + hedef hızını kestirmek, (2) araca öngörülü yönelmek (lead),
(3) hedefle **kesintisiz görsel temas** kurmak, (4) görsel faza (YOLO/CV) **temiz devretmek** (ARAMA→KILIT).
Terminal vuruş asıl olarak **görsel fazın** işidir.

---

## 3) Mimari harita (paket → dosya → rol → durum)

| Paket | Dosya | Rolü (şartname eşlemesi) | Durum |
|---|---|---|---|
| `sdk/` | `drone_sdk.py` | Simülasyon I/O: oyunla TCP telemetri/kontrol. **Resmî yarışma SDK'sı (v2.2)** — bizim yazmadığımız, verilen dosya. | ✅ Hazır (verili) |
| `fusion/` | `inovasyonlu_j_v2.py` | Sensör füzyonu: **GNSSDuzeltici** (CT-EKF) — bozuk GPS'i temizler + hedef hızını kestirir (+2 sn lead). **Tek üretim filtremiz.** | ✅ Çalışıyor |
| `guidance/` | `ana_kontrol.py` | **Beyin.** `AvciKontrol`: ARAMA→KILIT→GORSEL_GUDUM FSM, PD yaklaşma, terminal vuruş, handoff, uçuş logu. | ✅ Çalışıyor, ⚙️ sim-tune bekliyor |
| `guidance/` | `ibvs_guidance.py` | **Görsel güdüm (düz IBVS):** bbox merkez hatası → angle-mode komut (yaw/throttle/pitch). | ✅ Yazıldı, ⚙️ canlı kalibrasyon bekliyor |
| `detection/` | `gorsel_tespit.py` | **YOLO tespit:** `best.pt` inference sarmalayıcı; bir kareden en yüksek-conf bbox'ı döner. | ✅ Bağlı |
| `detection/` | `pencere_yakala.py` | **Occlusion-proof FPV:** oyun penceresinin İÇERİĞİNİ yakalar (pencere arkada olsa bile doğru kare). | ✅ Çalışıyor |
| `web/` | `server.py` | Backend: beyni barındırır, telemetri/FPV sunar, canlı-tune, manuel mod, kıyas ölçümü, thread orkestrasyonu. | ✅ Çalışıyor |
| `web/` | `index.html` | Yer Kontrol İstasyonu arayüzü (3 panel: telemetri, FPV+overlay, kıyas/tune). | ✅ Çalışıyor |
| `models/` | `best.pt` | Eğitilmiş YOLO ağırlığı (~44 MB, gerçek model). | ✅ Var |
| `veri/` | `kiyas_log.csv`, `ucus_log_*.csv` | Çalışma çıktıları: uçuş logları, kıyas CSV (üretilir). `.gitignore`'lu. | — |
| `arac/` | `gps_bozuk_gercek_gorsel.py`, `gps_filtreli_cikar.py`, `gps_gorsellestir.py` | **[ODAK DIŞI]** Uçuş sonrası GPS verilerini (ham vs filtreli vs gerçek) görselleştiren bağımsız analiz araçları. | Yardımcı |
| `arac/` | `analiz_ucus.py` | **[ODAK DIŞI]** `ucus_log_*.csv`'yi okuyup üç belirtiyi teşhis eder (geri-çekilme / salınım / görsel temas kaybı) + Cfg ayar önerisi; `ucus_metrikler.csv`'ye tur-kıyası satırı ekler. | Yardımcı |
| `arac/` | `tani_irtifa.py` | **[ODAK DIŞI]** Geçici teşhis scripti: `/api/telemetry`'den irtifa (Z) verisini canlı basar + `tani_log.csv`'ye yazar (oyuna 2. TCP açmaz). Sorun çözülünce silinebilir. | Yardımcı |
| `arsiv/` | `inovasyonlu_j_v1.py`, `inovasyonlu_j_v2_4.py`, `avci_fsm/guidance/main ÜSTEN DALIŞ.py` | **[ODAK DIŞI]** Eskiden yazılmış, yedek olarak tutulan silinmemiş kodlar (eski J sürümleri + eski "üstten dalış" FSM/güdüm/main). Üretimde kullanılmaz. | Yedek |
| kök | `main.py` | Tek giriş noktası: `from web.server import main`. `python main.py` → `http://127.0.0.1:8000`. | ✅ Çalışıyor |
| kök | `README.md` | Proje genel tanıtımı + kurulum/çalıştırma özeti (teslim `.zip` içinde de gider). | ✅ Var |
| kök | `SDK_README.md` | Resmî yarışma SDK'sının (v2.2) API/kullanım dokümanı — SDK ile birlikte verilen referans. | ✅ Var (verili) |
| kök | `CLAUDE.md` | Değişmez çalışma kuralları (Kural 1–8); bu belge onun üstüne güncel durumu koyar. | ✅ Var |
| kök | `requirements.txt` | Python bağımlılıkları (numpy, mss, Pillow, pygetwindow, ultralytics, opencv-python, windows-capture). | ✅ Var |
| kök | `1_Oyunu_Baslat.bat`, `2_Arayuzu_Baslat.bat` | Çalıştırma kısayolları: oyunu aç / arayüzü (`python main.py`) başlat (bkz. §7). | ✅ Var |
| kök | `MEVCUT_DURUM.md` | **Bu belge** — güncel durum brifingi. | ✅ Var |
| kök | `.gitignore`, `.gitattributes`, `.claude/settings.local.json` | Repo/araç konfigürasyonu: yok sayılanlar (oyun dosyaları, büyük modeller, `veri/`), git öznitelikleri, Claude Code yerel izinleri. | Config |
| her paket | `__init__.py` | `sdk/`, `fusion/`, `guidance/`, `detection/`, `web/` paket işaretçileri (genelde boş). | ✅ Var |
| `Drones of War Teknofest/` | `DronesOfWar.exe` + motor içeriği (Paks/Binaries/Engine) | **[HARİCİ]** Unreal tabanlı simülasyon oyunu; bizim yazmadığımız, `.gitignore`'lu (Drive'dan gelir, repoya konmaz). | Verili/harici |

> `main.py` tek giriş noktası: `from web.server import main`. `python main.py` → tarayıcıda `http://127.0.0.1:8000`.
> **Kapsam notu:** Yukarıdaki tablo klasördeki **tüm dosyaları** kapsar; `[ODAK DIŞI]`/`[HARİCİ]` işaretliler geliştirme yardımcıları veya verili bileşenlerdir, üretim güdüm hattının parçası değildir.

---

## 4) Güdüm akışı ve faz sınırları (en önemli kısım)

Kontrol döngüsü **50 Hz** (`server.py:kontrol_dongusu` → `beyin.adim()`). Bir tik şöyle akar:

```
Bozuk hedef GPS ──▶ İnovasyonlu J (temizle + hız kestir, +2sn lead)
                         │
   Kendi TEMİZ konumum ──┤
                         ▼
             FSM durumu:  ARAMA ──(mesafe<HANDOFF)──▶ KILIT ──(N_LOCK conf'lu YOLO tespiti)──▶ GORSEL_GUDUM
                         │                                                                        │
             GPS güdümü (PD + öngörü)                                          IBVS (yalnızca kamera; GPS yönelimi KESİLİR)
```

- **ARAMA (GPS yaklaşma):** J'nin **2 sn lead'li** kestirimi ile yatay intercept; **lead'siz anlık z** ile
  dikey (lead dikeyde irtifa aşımı yapıyor). Hata gövde çerçevesine çevrilir, **PD** ile komut üretilir.
  Koruma katmanları: mesafeye göre **hız tavanı** (overshoot guard), **rate-limit** (salınım önler),
  **dikey PID + integral** (ileri-uçuş taşıması yüzünden ~14 m yukarıda dengelenmeyi kapatır),
  **alçalma önceliği** (hedefin üstündeyken kovalamayı kısıp alçalmayı serbest bırakır).
- **KILIT:** Handoff menziline (histerezisli: `HANDOFF_RANGE`/`HANDOFF_EXIT`) girince. Görüş devralabilir sinyali.
- **GORSEL_GUDUM:** `conf ≥ VIS_CONF_MIN` kareler ard arda `VIS_N_LOCK` (5) olunca kilitlenir. Bu andan sonra
  **GPS yönelimi mimari olarak kesilir** (yarışma kuralı: bir daha GPS'e dönme — OTO modda yalnızca uzun
  görsel kayıpta re-acquire için dönülür). Komut yalnızca bbox merkez hatasından üretilir.
- **Terminal vuruş (COMMIT/RAM):** Çarpışma-rotası `v_des = v_hedef + v_close·LOS`. `v_close` mesafeyle
  orantılı + **tabanlı** (`V_CLOSE_MIN`) → temasta 0'a inmez, hedefin içine iter (geri atılma yok, delip geçer).
  Çok yakında yanal ivme kısılır (LOS singülarite salınımını önler → düz dalış).

> **Not (bilinçli tasarım sınırı):** Kodda terminal vuruş bloğu **GPS yolunda** da var; bu esas olarak
> "gercek" (truth) test modunda ve bir yetenek/emniyet olarak duruyor. Tasarım tezine göre asıl terminal
> vuruş **görsel fazın** işidir (bkz. §2). Video akışında hedef: GPS ile yaklaş → görselle tespit/kilit →
> **GNSS bağımlılığının azaldığını göster** → görsel güdümle angajman.

**Faz geçişi anahtarı (test için):** `vis_mode` = `OTO` (otomatik kilit/geri-dönüş) | `GPS` (görseli kapat) |
`GORSEL` (kilidi atla, zorla görsel). Arayüzden değiştirilebilir.

---

## 5) Modül modül özet

### `sdk/drone_sdk.py` — Resmî Yarışma SDK'sı v2.2 (verili, bizim değil)
- Oyunla TCP: `127.0.0.1:12345`. **Angle mode** uçuş.
- Kontrol: `set_throttle` (**dikey komut**: +1 tırman/0 hover/−1 serbest düşüş), `set_pitch/roll/yaw`,
  `set_control_surfaces(...)` (atomik, önerilen).
- Telemetri: `get_drone_location/rotation/speed/altitude`, `get_target_location/rotation/speed`.
- **Platform sabitleri (gömülü, değişmez):** Kamera **25° yukarı tilt**, **125° FOV**; max hız 120 km/h.
- **Gerçekçi bozuk telemetri (sunucu tarafında, kapatılamaz):** hedef GPS **5 Hz** (sim v0.0.5, yarışma
  koşulu; ≤v0.0.4'te 1 Hz idi); gürültü, sabit offset, ani sıçrama (spike), dropout, rate-limit, gecikme.
  Kendi telemetrimiz temiz ve tam hızlı. *(Kontrol döngüsü hâlâ 50 Hz → GPS artık her ~10 tikte bir taze
  paket veriyor; önceden ~50 tikte bir idi.)*
- **Debug truth kanalı:** `get_debug_truth()` / `get_active_corruption()` — sadece oyunda debug açıkken
  gelir; **gerçek (bozulmamış) değerler + aktif bozma maskesi**. Yalnızca ölçüm/kıyas/test için; yarışmada yok.

### `fusion/inovasyonlu_j_v2.py` — İnovasyonlu J (GNSSDuzeltici) [ODAK DIŞI ama kritik]
- **CT-EKF** (sabit dönüş hızlı — coordinated turn) + fiziksel kısıtlar. Bozuk GPS'i temizler, hedef
  hız vektörünü ve dönüş hızını kestirir.
- v2.1 farkı: rate-limit'li tekrarlanan paketleri **dropout sanmıyor** (tekrar eden paket → `None`,
  zaman ilerletilmez); böylece CT modeli ileri fırlatıp kestirimi bozmuyor. Bu tekilleştirme (allclose)
  mantığı 5 Hz'de de geçerli — GPS (5 Hz) hâlâ kontrol döngüsünden (50 Hz) yavaş, sadece taze paket aralığı
  ~1 s → ~0.2 s'ye indi.
- **✅ v0.0.5 uyumu UYGULANDI (2026-07-03):** `dt` varsayılanı **1.0 → 0.2** (`__init__`; `V2Filtre()`/`JFiltre()`/araçlar
  varsayılanla kurulduğundan tek noktadan geçerli) ve ilk hız tahmini `(Δkonum)/self.dt` ile cm/s'ye ölçeklendi
  (dt=1.0 iken bölme no-op'tu → eski davranış birebir korunur). Sentetik doğrulama (50 Hz tik, 5 Hz GPS,
  100 cm gürültü + %2 spike, 20 m/s dönen hedef): eski `dt=1.0` 5 Hz'de konumu idare eder gösterip **hız
  kestirimini bozuyordu** (hata ~16 m/s; `w` ~%80 sapık) — lead/öngörü tam bu kestirimlere dayanır. `dt=0.2` ile
  hız hatası ~1.2 m/s, `w` hatası ~0.005 rad/s (1 Hz'li eski dünyadan bile iyi). **Kalan:** yatay/dikey KF
  ayarları (R, Qp, Qw, gate) v0.0.5 sim'inde yeniden doğrulanmalı; kıyas panelinde (J vs ham) hata düşüşü ölçülmeli.
  `telafi_sn=2.0` (lead) fiziksel öngörü olduğu için sabit kaldı.
- `guncelle(x,y,z)` → `telafi_sn` (2 sn) ileri taşınmış konum. `durum_guduum()` → telafisiz **anlık** konum + hız
  (çift-lead olmasın diye). Birimler cm / cm-s.

### `guidance/ana_kontrol.py` — Beyin (`AvciKontrol`)
- `adim()` tek kontrol tiki. `Cfg` sınıfı tüm gain/tavan/işaret parametreleri (bir kısmı **canlı-tune**'lu).
- FSM + PD yaklaşma + terminal vuruş + handoff (§4). Kalkış (non-blocking arama irtifasına tırman).
- **Kaynak geçişi:** `set_kaynak("v2"|"gercek")`. "v2" = İnovasyonlu J; "gercek" = filtre yok, truth'a gider (test).
- **Görsel köprü:** `set_gorsel_tespit(det)` (server yazar) / `_gorsel_tespit_oku` (bayatlık kontrolü) —
  thread-güvenli; ağır YOLO inference'i 50 Hz kontrol tikinden **decouple** eder.
- **Zengin uçuş logu:** her tik `veri/ucus_log_*.csv` (teşhis için; yarışmada `Cfg.LOG_ENABLE=False`).
- `_kamera_kontrol` bir **stub** (test'te truth kullanır); gerçek görsel kilit `son_tespit` köprüsünden
  gelen YOLO tespitiyle olur, bu stub'la değil.

### `guidance/ibvs_guidance.py` — Görsel güdüm (düz IBVS)
- Tek hata sinyali: **bbox merkezinin görüntü merkezinden sapması** (PnP/derinlik/poz YOK; roll=0).
- Eksen eşleme (SDK fiziğiyle tutarlı): `yaw ← ex` (yatay ortala), `throttle ← (ey − VIS_EY_REF)`
  (dikey), `pitch ← ileri` (hizalıysa yaklaş).
- **25° kamera tilt telafisi:** kamera burnu 25° yukarı baktığından "tam merkez" = hedef burnun üstünde
  demek; drone hedefin altına oturmasın diye dikey referans `VIS_EY_REF (~0.43)` çizgisine tutulur.
  **SDK v2.2 uyumu için son eklenen kritik parça; sim'de kalibre edilecek.**

### `detection/gorsel_tespit.py` + `pencere_yakala.py`
- `HedefDedektor`: ultralytics YOLO `best.pt` → en yüksek conf bbox `{cx,cy,w,h,conf,W,H,t}`.
  **Zarif bozulma:** ultralytics/torch yoksa `hazir=False`, hep `None` → sistem **GPS ile çalışmaya devam** eder, çökmez.
- `PencereYakala`: `windows-capture` ile pencere içeriğini yakalar (tek monitörde oyun tarayıcının arkasında
  kalsa bile doğru kare). Yoksa mss ekran-bölgesine düşer.

### `web/server.py` + `web/index.html`
- 3 thread: `connection_manager` (oto yeniden bağlan + pencere-yakalamayı ayakta tut),
  `kontrol_dongusu` (50 Hz beyin), `dedektor_dongusu` (ayrı thread YOLO).
- 3 mod, karşılıklı dışlar: **görev** (otonom, `gorev_aktif`), **manuel** (klavye WASD/QE/RF, failsafe hover),
  **pasif** (sadece J ölçümü akar, drone uçmaz).
- **Kıyas ölçümü:** İnovasyonlu J'nin gerçeğe hatası vs ham GPS taban çizgisi (ort/std/max) → `veri/kiyas_log.csv`.
- **Canlı-tune:** arayüz slider'ları `Cfg`'yi çalışırken değiştirir (allowlist'li; server restart gerekmez).
- **API:** `/api/telemetry`, `/api/frame` (ham FPV; overlay istemci canvas'ında), `/api/command`
  (start/stop/manuel/vismode), `/api/manuel`, `/api/tune`.

---

## 6) Çalışan / bekleyen durum

**✅ Çalışıyor / bitti:**
- SDK haberleşme, web arayüzü (GCS), occlusion-proof FPV.
- İnovasyonlu J filtresi + ham'a karşı kıyas paneli.
- GPS yaklaşma güdümü (PD + overshoot guard + dikey PID + alçalma önceliği), terminal vuruş, FSM, handoff.
- Manuel mod + failsafe, kaynak geçişi (v2/gercek), canlı-tune, zengin uçuş logu.
- YOLO tespit bağlı (gerçek `best.pt`), IBVS görsel güdüm yazılı, görsel faz entegre (OTO oto-kilit),
  25° kamera tilt telafisi (`VIS_EY_REF`) eklendi.
- **Sim v0.0.5 filtre uyumu (2026-07-03):** `dt` 1.0 → 0.2 (5 Hz) + ilk-hız `(Δ)/dt` ölçekleme;
  sentetik testle doğrulandı (detay §5 fusion).

**⚙️ Bekleyen / tune gerektiren:**
- **🔔 Sim v0.0.5 uyarlaması (YENİ, öncelikli):**
  - ~~Filtre `dt` 1.0 → 0.2~~ → **YAPILDI (2026-07-03, bkz. §5)**. Kalan: `dt` değiştiği için
    R/Qp/Qw/gate ayarlarını v0.0.5 sim'inde yeniden doğrula.
  - **5 Hz'in avantajını değerlendir:** daha sık GPS → filtre daha az "kör" ekstrapolasyon yapar, kestirim
    ve hız/dönüş çıkarımı iyileşmeli; kıyas panelinde (J vs ham) hata düşüşünü **ölç**.
  - **Performans iyileştirmesi etkisi:** sim FPS/zamanlama değişmiş olabilir → 50 Hz döngü zamanlamasını,
    FPV yakalama gecikmesini ve YOLO tik hızını v0.0.5'te yeniden ölç.
- **Sim'de canlı kalibrasyon:** işaret/frame doğrulama (`PITCH/ROLL/YAW/Z_SIGN`, `VIS_SIGN_*`),
  gain'ler, `VIS_EY_REF` (25° tilt referansı), yaklaşma/vuruş tavanları.
- **Uçtan uca kanıt akışının sim'de doğrulanması:** otonom başla → bozuk GPS ile yönelme → görselle tespit →
  tracking → görsel takip → **GNSS bağımlılığının azaldığını gösterme** → angajman → başarı.
- **Video anlatım metinleri** (ilk 3 dk + son 3 dk) — kullanıcı **en sonda** isteyecek (bkz. §11).

---

## 7) Nasıl çalıştırılır
1. `1_Oyunu_Baslat.bat` → oyunu açar (repo kökündeki veya üst klasördeki `Drones of War Teknofest\DronesOfWar.exe`).
   Oyunda **PLAY** moduna geç, mümkünse pencereli/kenarlıksız.
2. `2_Arayuzu_Baslat.bat` → `python main.py` çalıştırır, tarayıcıyı `http://127.0.0.1:8000`'e açar.
3. Bağımlılıklar: `pip install -r requirements.txt` (numpy, mss, Pillow, pygetwindow, ultralytics,
   opencv-python, windows-capture). **torch'u önce doğru wheel'den kur** (CUDA: `cu121`), sonra requirements.
   ultralytics/torch yoksa görsel faz pasif kalır, saf GPS çalışır.

> Oyun **tek bağlantı** kabul eder: aynı anda tek arayüz çalışsın; yeniden başlatmadan önce eskisini kapat.
> Oyun dosyaları ve büyük modeller `.gitignore`'da (repoya konmaz; Drive'dan gelir).
> **⚠️ Sim sürümü:** v0.0.5 kullan (koordinatörlük bağlantısından). Bu sürümde hedef GPS **5 Hz** ve performans
> iyileştirmeleri var → filtre `dt` uyarlaması gerekli (bkz. §5 fusion, §6). Eski v0.0.4 build'i ile test etme.

---

## 8) Video isterleri (kısa hatırlatma — asıl teslim bu)
- **İlk 3 dk (hızlandırma yok, sesli teknik anlatım):** sistem mimarisi; bozuk GNSS'in girdi olarak alınışı
  ve değerlendirilişi; görüntü işleme/hedef tespit; tracking; sensör füzyonu/filtreleme (GPS hata/sıçrama/
  kayıp/gecikmede tepki); güdüm/karar; kaynak dosya tanıtımı + kullanılan açık kaynak kütüphaneler.
- **Son 3 dk (gerçek zamanlı görev kanıtı):** otonom başlama → bozuk GNSS ile bölgeye yönelme → görüntüyle
  tespit → tracking aktif → görsel takip → **GNSS bağımlılığının azaldığının gösterilmesi** → yaklaşma →
  otonom angajman → vuruş/başarı → **insan müdahalesi olmadığı**. Manuel hedef seçimi/işaretleme YOK.
- **Teslim .zip:** input, hedef tespit, tracking, füzyon/filtre, güdüm, ana çalıştırma, config,
  requirements, README, eğitilmiş model (.pt). **Video ↔ kod tutarlı olmalı.**

---

### Claude'a ipucu
Değişiklik yaparken §2'deki değişmez kurallara sadık kal, güdüm dokunuşlarını `AvciKontrol` içine göm,
çalışan arayüz/manuel/kıyas akışını bozma. Yeni "akıllı" sabitler eklemeden önce sor: *bunu takımca
açıklayabilir miyiz, overfit mi?* — cevabı overfit ise ekleme.

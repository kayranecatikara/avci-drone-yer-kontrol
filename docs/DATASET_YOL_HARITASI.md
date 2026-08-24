# DATASET v2 + YENİ DETECTION MODELİ — YOL HARİTASI (2026-07-17)

## HEDEF
Mevcut dataset kötü (az/kalitesiz foto, dar açı-mesafe dağılımı) ve model canlıda
yetersiz. Amaç: Talon'u **farklı açılardan + farklı mesafelerden**, sistematik
kapsama ile toplanmış, otomatik etiketlenmiş, doğru augmente edilmiş **yeni bir
dataset** kurmak ve onunla **yeni bir YOLO detection modeli** eğitmek.

**Mevcut durum (referans, CLAUDE.md canlı ölçümleri):** 0-10 m ~%70-80,
15-20 m ~%45, 60 m+ %0 tespit; kendi pervanemiz ara sıra yanlış-pozitif.

**Kabul hedefleri (offline test seti, conf ≥ VIS_CONF_MIN):**

| Mesafe bini | Mevcut (yaklaşık) | Hedef recall |
|---|---|---|
| 5-20 m   | %45-80 | ≥ %85 |
| 20-40 m  | düşük  | ≥ %65 |
| 40-60 m  | ~0     | ≥ %45 |
| 60-80 m  | 0      | ≥ %25 |
| Pervane-negatif karelerde FP | var | 0 (conf ≥ 0.25) |

Canlı kabul: tune raporunda "en uzun kesintisiz takip" ve 15-40 m tespit%
mevcut modele karşı aynı uçuş profilinde belirgin artış; kilit penceresi
(10 sn'de 5 sn) dolabilmeli.

---

## ANA FİKİR: ETİKETİ ELLE DEĞİL, TRUTH'TAN ÜRET
SDK tam truth veriyor (`get_target_location/rotation`, `get_drone_location/
rotation`, `get_debug_truth`). Talon'un 3B keypoint modeli elimizde
(`pose/talon_keypoints.json`, kanat açıklığı SDK ile birebir 171.8 cm).
Kamera tilt + telemetri↔kare gecikmesi `pose/kalibre.py` ile VERİDEN ölçülüyor.
→ Her karede hedefin 6 mesh noktasını görüntüye projekte edip **bbox etiketini
otomatik** üretebiliriz. Etiketleme maliyeti ≈ 0; dataset büyüklüğü sorun olmaktan
çıkar. İnsan işi yalnız ÖRNEKLEM KALİTE KONTROLÜ (görsel doğrulama).

Bu hattın tek önkoşulu projeksiyonun doğruluğu → Faz 0 kapısı.

---

## FAZ 0 — PROJEKSİYON HATTINI DOĞRULA (oto-etiketin temeli) — ~1 gün
1. Kısa bir kayıt uçuşu (yakın mesafe ağırlıklı) → `pose/kalibre.py` ile
   kamera tilt + latency dt ölç (best.pt yakın mesafede referans olarak yeterli).
   Çıkan değerler `pose/geometri.py`'ye.
2. **`pose/etiketle.py`'Yİ YAZ** (kayit_ucusu Faz-4 planında var, hiç yazılmamış):
   telemetri.jsonl + kare → 6 keypoint projeksiyonu → bbox (min/max + küçük marj)
   → YOLO detect .txt. Şüpheli kare bayrağı: kadraj kenarı taşması, aşırı
   projeksiyon artığı, hedef FOV dışı.
3. **Uçtan uca doğrulama:** eldeki 379 kare GT'li pose dataset'inde projeksiyon
   keypoint'leri ile GT keypoint pikselleri kıyasla.
   **KAPI: medyan piksel hatası < kare genişliğinin ~%2'si.** Geçemezse önce
   attitude işaret sorunu (Blokör B) `arac/attitude_dogrula.py` ile çözülür.
4. Görsel örneklem: `pose/onizle.py` ile rastgele 30 karede kutu üstüne çizim.

Çıktı: çalışan, doğrulanmış `etiketle.py` + kalibrasyon raporu.

## FAZ 1 — VERİ TOPLAMA (iki hat + negatifler) — 1-2 gün
**Hat A (BİRİNCİL — canlı domain): `pose/kayit_ucusu.py` orbit uçuşları.**
Dağıtım domain'imizle birebir aynı kaynak (pencere yakalama, gerçek motion blur,
gerçek arka planlar). Oturum planı (~2 Hz kayıt, oturum başına ~10 dk):
- Mesafe binleri: 5-15 / 15-30 / 30-50 / 50-80 / 80-120 m (orbit MIN/MAX
  parametreleriyle oturum başına bir bant; uzak bantlara EK oturum — model
  oradan kör).
- Azimut/elevasyon: orbit otopiloti + rastgele yaw ofseti zaten dağıtıyor
  (merkez önyargısı önlenir — araçta hazır).
- Hedef DÜZ uçuş oturumları + MANEVRALI (banklı dönüşlü) oturumlar.
- Farklı ışık/harita seçeneği oyunda varsa en az 2 varyant.
- ⚠ Kayıtta web arayüzü KAPALI (oyun tek TCP bağlantısı kabul ediyor).

**Hat B (TAMAMLAYICI — sistematik grid): `pose/capture_controller.py` + UE4SS
Lua modu (TalonDatasetGenerator).** Sahne dondurulup kamera yerleştirildiği için
uçuşta örneklenemeyen zor açı×mesafe hücrelerini garantiler (ör. tam karşıdan
uzak, tam üstten). Pose dataset'i bununla üretilmişti; aynı akış.

**Hat C (NEGATİFLER — FP ilacı):** etiketsiz kareler: kendi pervanemiz kadrajda
(bilinen FP kaynağı!), boş gökyüzü, yer clutter'ı, ufuk çizgisi, HUD öğeleri.
Ultralytics boş .txt = background örneği olarak eğitime girer.

Ham hedef: A ~10-12k kare, B ~2-3k, C ~1-1.5k. (Depo DIŞI klasörde tutulur,
örn. `C:\talon_dataset_v2\oturum_*`; repoya yalnız manifest/istatistik girer.)

## FAZ 2 — OTO-ETİKET + KALİTE KONTROL — ~yarım gün
- `etiketle.py` tüm oturumlara; şüpheli bayraklılar otomatik ELENİR.
- Örneklem QA: her oturumdan rastgele 30 kare `onizle.py` çizimiyle insan gözü.
  Sistematik kayma görülürse Faz 0'a dön (kalibrasyon), tekil hatalar elenir.
- Kutu sıkılığı kontrolü: projeksiyon-bbox vs best.pt-bbox IoU dağılımı yakın
  mesafede raporlanır (aracı Faz 0'daki doğrulamadan türet).

## FAZ 3 — KÜRASYON + SPLIT — ~yarım gün
- Ardışık near-duplicate ayıklama (kare stride + basit benzerlik eşiği).
- **Stratifikasyon matrisi** (etiket meta'sından: gerçek mesafe × bakış açısı ×
  fon): her hücrede hedef adet; şişkin hücreler kırpılır, boş hücreler Faz 1'e
  ek görev olur. Nihai hedef ~4-6k pozitif + ~%15 negatif.
- **Split OTURUM BAZLI** (kare bazlı ASLA — ardışık kareler sızıntı yapar):
  ~%80 train / %10 val / %10 test; val-test mesafe binlerine dengeli.
  **Test seti DONDURULUR** — bütün model kıyasları hep aynı sette.
- `data.yaml` (detect, tek sınıf `talon`); `arac/egitim/dataset_dogrula.py`'ya
  detect modu ekle (kpt_shape zorunluluğu pose'a özel kalsın).

## FAZ 4 — AUGMENTASYON — kürasyonla birlikte
**Train-time (ultralytics parametreleri, data.yaml/komutta):**
- `scale` GENİŞ (0.3-0.9 bandı etkisi): mesafe çeşitliliğinin ana çarpanı.
- `mosaic 1.0` (küçük-hedef recall), `fliplr 0.5` (Talon simetrik),
  `hsv_h/s/v` ılımlı (ışık), `degrees ±10`, `translate 0.1`, `mixup ~0.1`,
  `flipud 0`.
**Offline (özel, küçük araç):**
- **Küçük-hedef copy-paste:** etiketli karelerden kırpılan Talon'u gök/clutter
  fonlara 8-25 px ölçekte yapıştır → 60 m+ recall'un ana kaldıracı (o mesafede
  gerçek örnek zaten birkaç piksel; sentetik çoğaltma meşru ve açıklanabilir).
- Hafif motion-blur varyantı (hızlı yaw karelerini taklit).
**Val/test'e augment YOK — hep temiz.**

## FAZ 5 — EĞİTİM (Colab) — koşu başına saatler
- `arac/egitim/bbox_egit.py` yaz: `pose_egit.py` iskeletinin detect kardeşi
  (PLAN modu, dataset_dogrula kapısı, `detect_yolo11s_v2_960_202607XX.pt` tarzı
  anlamlı adlandırma, models/'a kopya). İskelet hazır — küçük iş.
- Baz koşu: **yolo11s, imgsz 960**, COCO pretrain'den, epochs 150 / patience 30.
- Kıyas koşuları: aynı dataset ile **imgsz 640** ve **1280**; hız yedeği 11n.
  (Ders: eğitim imgsz'i = çalıştırma imgsz'i olacak — çifte örnekleme uzak
  hedefi öldürüyor. Nihai imgsz kararı Faz 6'nın FPS+recall tablosuyla verilir.)

## FAZ 6 — OFFLINE DEĞERLENDİRME — ~yarım gün
- `arac/model_kiyas.py` yaz (kalıcı, tekrarlanabilir): dondurulmuş test setinde
  **mesafe-bin bazında** recall@VIS_CONF_MIN, precision, conf dağılımı, IoU;
  pervane-negatif setinde FP sayısı; **SAHI açık/kapalı** satırları.
- Karar tablosu: {model} × {imgsz 640/960/1280} × {SAHI on/off} →
  bin-recall + tahmini canlı FPS (izole benchmark). Kabul eşikleri yukarıda.

## FAZ 7 — CANLI ENTEGRASYON + A/B — ~yarım gün
- Eski model `models/best_eski_YYYYMMDD.pt` yedeğiyle değişim (mevcut
  konvansiyon); `server.py` dedektör imgsz'i seçilen değere güncellenir
  (şu an 640 sabit + "best3 640'ta eğitildi" yorumu — birlikte değişmeli).
- Aynı uçuş profiliyle tune raporu **Segment Kıyas** A/B: eski vs yeni model
  (tespit%, kayıp sayısı, en uzun kesintisiz takip, kilit penceresi).
- Kötüleşme görülürse anında yedekten geri dönüş.

---

## RİSKLER / SİGORTALAR
- **Blokör B (sim attitude işareti):** projeksiyon doğruluğunu bozabilir →
  Faz 0 kapısı bunu ölçüyor; gerekirse `attitude_dogrula.py` ile çözülür.
- **Oyun tek TCP bağlantısi:** kayıt uçuşunda arayüz kapalı (araç zaten uyarıyor).
- **GPU paylaşımı:** eğitim Colab'da; canlı testte oyuna FPS cap (bilinen ders).
- **Sim-domain uyumu:** dağıtım domain'i de sim → Hat A birincil olduğu sürece
  domain kayması riski düşük; Lua grid'i yalnız kapsama tamamlar.
- **Aşırı-iyimser offline sonuç:** split oturum-bazlı + test dondurulmuş +
  canlı A/B şartı — üç sigorta birden.

## SIRA (önerilen)
Faz 0 → Faz 1A (ilk 3-4 oturum) → Faz 2 QA → (kapsama boşluğuna göre Faz 1B/1C)
→ Faz 3-4 → Faz 5 baz koşu → Faz 6 → gerekirse Faz 1 ek toplama → Faz 5-6 tekrar
→ Faz 7. İlk uçtan-uca tur küçük tutulur (2-3k kare ile mini-dataset →
pipeline'ı uçtan uca kanıtla), sonra ölçek büyütülür.

## İLK ADIMLAR (bugün başlanabilir)
1. `kayit_ucusu.py`'nin bu branch'te duman testi (oyun açık, 1-2 dk `--pasif`).
2. Kalibrasyon kaydı + `kalibre.py` koşusu (Faz 0.1).
3. `etiketle.py` yazımı (Faz 0.2) — 379 karelik GT setiyle doğrulama dahil.

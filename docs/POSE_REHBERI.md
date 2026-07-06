# 🎯 POSE_REHBERI — Talon Poz Kestirimi (Keypoint + PnP) Yol Haritası

Amaç: FPV kamerasından gelen görüntüden hedef Talon'un **mesafesini ve yönelimini
(açısını)** kestirmek. Yöntem: simülasyondan **otomatik etiketlenmiş** keypoint veri
seti üret → **YOLO-pose** modeli eğit → tespit edilen 2D noktalardan **solvePnP** ile
6DoF poz çöz.

Neden bu mimari (doğrudan "açı+mesafe regresyonu" değil):
- Model yalnızca **2D nokta tespiti** öğrenir (kolay, az veriyle genelleşir);
  mesafe/açıyı **klasik geometri** (PnP) çözer → her bileşeni açıklayabiliriz
  (yarışma kuralı 8 ile uyumlu; PnP standart OpenCV fonksiyonudur, hazır güdüm değildir).
- Çözünürlük/FOV değişse bile sadece K matrisi güncellenir, model yeniden eğitilmez.
- Video isteri **"GNSS bağımlılığının azaldığının gösterilmesi"** için birebir:
  mesafe artık telemetriden değil KAMERADAN gelir.

---

## ⚠️ Çalışma zarfı (önce beklentiyi sabitle)

Kamera FOV 125° (yatay varsayımı Faz 2'de doğrulanacak). 1920 px genişlikte
fx = (W/2)/tan(FOV/2) ≈ **500 px**. Talon kanat açıklığı 171.8 cm → ekrandaki genişliği:

| Mesafe | Kanat açıklığı (px @1920) | Keypoint kalitesi |
|-------:|--------------------------:|-------------------|
|   5 m  | ~172 px | mükemmel |
|  10 m  | ~86 px  | iyi |
|  20 m  | ~43 px  | sınırda |
|  30 m  | ~29 px  | zayıf |
|  50 m  | ~17 px  | çalışmaz (bbox bile zor) |

**Sonuç:** Poz kestirimi **terminal/yakın faz aracı**dır (≈5–35 m). Uzak fazda mevcut
GPS güdümü + best.pt bbox akışı aynen kalır. Ayrıca modele girmeden **hemen elde
edilebilecek kaba mesafe**: takip pozisyonundayken `d ≈ fx · 171.8cm / bbox_w_px`
(önden/arkadan bakışta kanat tam genişlik görünür; yandan bakışta GEÇERSİZ).

---

## Faz 0 — Hazırlık (yarım gün)

1. **Veri seti dizini OneDrive DIŞINA:** `C:\talon_pose_data\` (binlerce PNG
   OneDrive senkronunu ve diski boğar; repo/onedrive'a asla koyma).
2. **Debug truth kontrolü:** oyun debug seçeneği açıkken
   `python -c` ile bağlanıp `get_debug_truth()['available']` True mu bak.
   True ise veri toplama truth alanlarından yapılacak.
3. **Çözünürlüğü sabitle:** oyun penceresini tüm oturumlarda aynı boyutta çalıştır
   (tercihen 1920×1080 veya üstü). Kayıtta yine de her karenin W,H'si `frame.shape`'ten
   alınır (başlık çubuğu / client-area farkları olabilir — asla sabit varsayma).
4. Klasör: repo içine `pose/` modülü (aşağıdaki dosyalar buraya).

```
pose/
  geometri.py         # ortak matematik: UE rotasyon + projeksiyon + kp yukleme — YAZILDI ✓
  talon_keypoints.json# 6 noktanin arac-lokal 3D koordinati (cm) — kullanicidan GELDI ✓
  kayit_ucusu.py      # Faz 1: orbit otopilot + kare/telemetri kaydı — YAZILDI ✓ (sentetik isaret testleri geciyor; oyunda ilk kayit bekliyor)
  etiketle.py         # Faz 4: kayıt → YOLO-pose veri seti + görsel önizleme
  poz_cozucu.py       # Faz 6: PnP + EMA (entegrasyona hazır sınıf)
  degerlendir.py      # Faz 6: truth'a karşı mesafe/açı hata raporu
  fov_kalibre.py      # Faz 3 (OPSIYONEL): gate patlarsa FOV/tilt 2-param fit
```

---

## Faz 1 — Kayıt uçuşu (1 gün)

Oyun **tek TCP bağlantısı** kabul eder → kayıt sırasında web arayüzü KAPALI olacak;
`kayit_ucusu.py` SDK'ya kendisi bağlanır, hem uçurur hem kaydeder.

**Döngü (6–8 Hz):** kare al (PencereYakala; olmazsa mss) → PNG yaz (JPEG DEĞİL —
sıkıştırma artefaktı keypoint hassasiyetini bozar) → JSONL satırı ekle:

```json
{"t": 123.456, "frame": "kare_000123.png", "W": 1920, "H": 1080,
 "drone_pos": [x,y,z], "drone_rot_rpy": [roll,pitch,yaw],
 "target_pos": [x,y,z], "target_rot_rpy": [roll,pitch,yaw], "target_speed": 950.0,
 "truth_available": true, "truth_target_pos": [x,y,z], "corruption_mask": 0}
```

Birimler: **cm ve derece** (UE/telemetri neyse o). `t` = `time.perf_counter()`.
Kare adı ↔ JSONL satırı birebir eşleşir; telemetri kare alındığı anda okunur.

> **⚠️ TRUTH VERİSİ — KONUM VAR, ROTASYON YOK (kritik).** `get_debug_truth()` hedefin
> **bozulmamış konumunu** verir ama **rotasyonunu VERMEZ** (`drone_sdk.py`: truth.target =
> {position, speed}). Etiketleme için ikisi de şart, o yüzden kayıtta HER İKİ kaynağı da yaz:
> - **Konum → `truth_target_pos`** (bozulmamış; etiket origin'i = AM buradan). Kullanıcı isteği: etiketler bozuk GPS'ten DEĞİL, truth'tan üretilecek.
> - **Rotasyon → `target_rot_rpy`** (`get_target_rotation()`; truth'ta yok). Değer olarak bozulmaz ama kanalı paylaştığı için RATELIMIT/DELAY/DROPOUT **zamanlamasını** bozar → Faz 4'te heading çapraz-kontrolüyle temiz kareler seçilir.
> - **Zorunlu:** `truth_available`, `corruption_mask`, hem normal hem truth konumu ve `t` her satırda olsun; kaydı **oyun debug modu AÇIKKEN** al (yoksa `truth_available=False`, veri işe yaramaz).

**Basit orbit otopilotu** (mevcut `ana_kontrol` mantığından esinlen, ama bağımsız tut):
1. Truth GPS ile hedefe yaklaş (P-kontrol).
2. Hedef etrafında yavaş yörünge: mesafe 5–40 m arasında tara (yakına ağırlık ver),
   irtifa hedefin altı–üstü arasında değişsin (elevation ≈ −60°…+60°; avcı çoğunlukla
   üstten dalar → üst yarıya ekstra ağırlık, ama alttan görünüşler de olsun).
3. Yaw'ı hedef bearing'ine döndür **AMA rastgele ofset ekle** — hedef her karede
   görüntünün farklı bölgesinde olsun. Hedef hep merkezdeyse model merkez önyargısı
   öğrenir ve PnP perspektif bilgisi zayıflar.
4. Birden fazla oturum: farklı harita bölgesi/arka plan (gökyüzü, zemin, ufuk),
   mümkünse farklı ışık.

**Hacim hedefi:** 2–3 oturum × ~10 dk × 6 Hz ≈ 10–12k ham kare → filtre sonrası
~6–8k etiketli kare (yeterli). Disk: ~1.5–2.5 MB/PNG → oturum başına ~10 GB civarı.

---

## Faz 2 — Koordinat/işaret doğrulaması (yarım gün)

> **Not:** `ue_rot_matrix` / `projekte` / `kamera_pozu` / `keypoints_dunyada` artık
> `pose/geometri.py`'de yazılı ve self-test'i geçiyor — aşağıdaki kod referans içindir,
> Faz 4/6 doğrudan bu modülü import eder.

Projeksiyon matematiğinin tamamı UE konvansiyonuna dayanır; önce SDK'nın verdiği
değerlerin işaret/sırasını doğrula (5 dakikalık uçuş testleri):

- UE dünyası: **sol-elli, X ileri, Y sağa, Z yukarı, birim cm, açılar derece.**
- SDK tuple sırası `(roll, pitch, yaw)` — UE rotator yazımından FARKLI, unpack'e dikkat.
- Testler: burnu yukarı kaldır → pitch artmalı (+). Sağa yat → roll artmalı (+).
  Sağa dön (saat yönü, üstten) → yaw artmalı (+). Yükselince Z artmalı.
  Ters çıkan olursa etiketleyicide o kanalın işaretini çevir (tek satır).

**UE rotator → rotasyon matrisi** (UE kaynak koduyla birebir; `P_world = R @ P_local`):

```python
import numpy as np

def ue_rot_matrix(pitch, yaw, roll):
    """UE FRotator (derece) -> R (3x3, sutun-vektor): P_world = R @ P_local.
    Sutunlar = lokal X(ileri), Y(sag), Z(yukari) eksenlerinin dunyadaki yonu."""
    p, y, r = np.radians([pitch, yaw, roll])
    cp, sp = np.cos(p), np.sin(p)
    cy, sy = np.cos(y), np.sin(y)
    cr, sr = np.cos(r), np.sin(r)
    fwd   = np.array([cp*cy,               cp*sy,               sp    ])
    right = np.array([sr*sp*cy - cr*sy,    sr*sp*sy + cr*cy,   -sr*cp ])
    up    = np.array([-(cr*sp*cy + sr*sy), cy*sr - cr*sp*sy,    cr*cp ])
    return np.column_stack([fwd, right, up])
```

**Kamera pozu** = drone pozu; kamera **25° YUKARI tilt'lidir** (saha bulgusu 3 Tem, bkz.
Faz 1 notu — ilk "tilt yok" kullanıcı teyidi YANLIŞ çıktı, SDK_README doğrulandı;
`geometri.KAMERA_TILT_DEG=25`):

```python
R_drone = ue_rot_matrix(pitch=p, yaw=y, roll=r)      # SDK: r,p,y = get_drone_rotation()
R_cam   = R_drone @ ue_rot_matrix(TILT, 0.0, 0.0)    # TILT=25 (yukari); kesin deger pose/kalibre.py ile netlesir
cam_pos = np.array(drone_pos)                        # kamera ofseti ~0 varsay (kapida dogrulanir)
```

**Projeksiyon** (UE kamera lokali: x ileri, y sağa, z yukarı):

```python
def projekte(p_world, cam_pos, R_cam, fx, W, H):
    v = R_cam.T @ (np.asarray(p_world) - cam_pos)    # kamera frame'ine
    x, y, z = v
    if x < 1e-6:
        return None                                   # kamera arkasi
    return (W*0.5 + fx * y/x,  H*0.5 - fx * z/x)     # (u, v) piksel

fx = (W/2) / np.tan(np.radians(125.0)/2)             # fy = fx (UE kare piksel, distorsiyon yok)
```

UE render'ı ideal pinhole'dur → `distCoeffs=None` her yerde doğru. 125°'nin yatay FOV
olduğu varsayımı Faz 3'teki taramayla kesinleşir.

---

## Faz 3 — Talon 3D keypoint modeli (HAZIR — kullanıcıdan geldi ✓)

> **DURUM:** Bu faz büyük ölçüde TAMAMLANDI. Keypoint'lerin araç-lokal 3D koordinatları
> kullanıcı tarafından sağlandı (`preview.jpg`), UE gövde frame'ine çevrilip
> `pose/talon_keypoints.json` + `pose/geometri.py` olarak yazıldı. **Triangülasyon GEREKMİYOR.**

**6 nokta şeması** (indeksler sabit — eğitim, etiket ve PnP hepsi buna bağlı):

| # | Ad | UE gövde (cm) X, Y, Z | Not |
|---|----|----------------------:|-----|
| 0 | burun ucu      | +55.03,   0.00, −1.32  | burun +X (ileri) |
| 1 | sol kanat ucu  | −10.17, −85.90, +4.49  | sol → −Y |
| 2 | sağ kanat ucu  | −10.17, +85.90, +4.49  | sağ → +Y |
| 3 | sol kuyruk ucu | −53.16, −22.56, +17.93 | V-kuyruk, yukarı +Z |
| 4 | sağ kuyruk ucu | −53.16, +22.57, +17.93 | |
| 5 | kuyruk arka    | −53.68,   0.00, −0.65  | gövde arkası |

`flip_idx = [0, 2, 1, 4, 3, 5]`. Origin = telemetri hedef pozisyonu (kullanıcı: **AM =
`get_target_location()`**). Sağlama: |kp1.Y − kp2.Y| = **171.8 cm** ✓ (SDK ile birebir),
gövde |kp0 − kp5| = 108.7 cm (~110). `python pose/geometri.py` 6 işaret testini geçiyor.

**Eksen dönüşümü (kritik — bir kez yapıldı):** kullanıcı tablosu **sağ-elli**
(`+X=kuyruk, +Y=yukarı, +Z=sol kanat`), kod UE gövde **sol-elli**
(`+X=ileri, +Y=sağa, +Z=yukarı`) istiyor → `X_UE=−X_tablo, Y_UE=−Z_tablo, Z_UE=+Y_tablo`
(determinant −1 = el değişimi). JSON'daki değerler ZATEN çevrilmiş.

> **HFOV=125° YATAY olduğu kullanıcı tarafından teyit edildi** → `fx=(W/2)·cot(125°/2)`
> kesin; diyagonal/dikey FOV belirsizliği YOK. `pose/geometri.py:fx_from_hfov` bunu kullanır.

**Geriye kalan tek doğrulama (Faz 4 görsel kapısında — ekstra iş değil):**
- **AM = telemetri pivotu mu?** Kullanıcı: `get_target_location()` = ağırlık merkezi (AM) =
  keypoint origin. Doğruysa noktalar tam oturur. Sabit bir kayma görülürse pivot≠AM →
  tüm keypoint'lere **tek gövde-frame ofset vektörü** eklenir (tek satır düzeltme; bu yüzden
  JSON'da ham tablo da saklı). Tilt=25° değeri de burada teyit olur (ilk "tilt=0" kullanıcı
  teyidi saha verisiyle YANLIŞ çıktı — bkz. Faz 1 notu; noktalar sistematik DİKEY kayarsa
  tilt pose/kalibre.py ile yeniden ölçülür).

**Kapı patlarsa (opsiyonel `fov_kalibre.py`):** 3D model artık BİLİNDİĞİ için ~10 karede
noktaları elle tıklayıp reprojeksiyon hatasını minimize eden tilt+pivot ofsetini çöz —
eski tam triangülasyondan çok daha kolay. Yalnızca kapı başarısız olursa gerekir.

---

## Faz 4 — Otomatik etiketleyici (1–2 gün — projenin kalbi)

`etiketle.py`: JSONL+PNG kayıtlarını okur, YOLO-pose veri setine çevirir.

**Zaman senkronu (en kritik kısım) — konum TRUTH'tan, rotasyon NORMAL kanaldan:**
Kareyi etiketlemeden önce:
1. **Konum:** `truth_target_pos` örneklerinin değişim anlarını bul (değer değişti = yeni
   örnek); kare zamanına **truth konum üzerinden lineer interpolasyon** yap. Truth bozulmamış
   olduğundan NOISE/OFFSET/JUMP konumu etkilemez — truth kullanmamızın sebebi tam bu.
2. **Rotasyon** (`target_rot_rpy`; truth'ta yok): kareyi saran iki örnek arası fark < ~3°
   ise interpole et; büyükse (hedef dönüşte / senkron kaymış) **kareyi AT**.
3. Rotasyon kanalının **zamanlaması** bozulabilir → `corruption_mask & (DROPOUT|DELAY|RATELIMIT)`
   aktifken çekilen kareleri AT (rotasyon bayat/donuk olabilir; bayraklar `drone_sdk.py`'de).
4. **Ana emniyet (rotasyon doğrulaması):** hedef hareketliyken truth-konum-farkından çıkan
   heading ile `target_rot_rpy` yaw'ı arasındaki fark > ~8° ise kareyi AT. Bu tek test hem
   senkron hatasını hem rotasyon bozulmasını yakalar (yaw tutuyorsa rotasyon paketi o an güvenilir).

**Etiket üretimi:**
```python
R_t = ue_rot_matrix(pitch=tp, yaw=ty, roll=tr)          # hedef rotasyonu
uv = [projekte(t_pos + R_t @ kp_local, cam_pos, R_cam, fx, W, H)
      for kp_local in KEYPOINTS_CM]                      # 7 nokta -> piksel
```
- 7 noktanın TAMAMI ekran içindeyse kareyi al; değilse at (MVP kuralı — sonra
  visibility bayraklarıyla gevşetilebilir). Görünürlük değeri hepsinde 2 yaz.
- bbox = noktaların zarfı + **%12 pad**, ekrana clamp.
- YOLO satırı (hepsi [0,1] normalize):
  `0 cx cy w h  x0 y0 2  x1 y1 2  ...  x6 y6 2`
- **Çapraz kontrol (bedava sağlama):** mevcut `best.pt`'yi her karede koştur;
  projekte bbox ile IoU < 0.5 ise kareyi karantina klasörüne ayır (senkron hatalarını
  otomatik yakalar).

**Görsel doğrulama — ilerlemeden önce zorunlu kapı:** `etiketle.py --onizle 50` →
rastgele 50 kareye noktaları+iskeleti çizip klasöre yazsın; **gözle incele**.
Koordinat sistemi hataları (işaret, sıra, tilt) burada anında görünür. 50/50 doğru
oturmadan Faz 5'e GEÇME.

Bölme: %90 train / %10 val — **oturum bazında ayır** (aynı uçuşun ardışık kareleri
train ve val'e bölünürse metrik şişer).

---

## Faz 5 — Eğitim (yarım gün + GPU süresi)

`C:\talon_pose_data\data.yaml`:
```yaml
path: C:/talon_pose_data
train: images/train
val: images/val
names:
  0: talon
kpt_shape: [6, 3]
flip_idx: [0, 2, 1, 4, 3, 5]   # sol<->sag takasi — talon_keypoints.json ile AYNI, ZORUNLU
```
`flip_idx` olmadan fliplr augmentasyonu sol/sağ kanadı çapraz öğretir ve model sessizce
bozulur — en sinsi hata bu.

```
yolo pose train data=C:/talon_pose_data/data.yaml model=yolo11s-pose.pt \
     epochs=150 imgsz=1280 batch=-1 device=0 \
     degrees=35 fliplr=0.5 flipud=0.0 mosaic=1.0 close_mosaic=25 name=talon_pose_v1
```
- `imgsz=1280`: hedef küçük göründüğü için 640 yetmez.
- `degrees=35`: drone 60°'ye kadar yatıyor → kamera roll'ü görüntüde dönme üretir.
- GPU yoksa Colab'da eğit (dataset'i zip'le); çıkan `best.pt` → `models/talon_pose.pt`.
- Bak: val `mAP50-95(pose)` + önizleme görüntülerinde nokta oturması.
- Hassasiyet yetmezse (özellikle 20 m+): 2. iterasyon = **two-stage** — best.pt bbox'ı
  ile kırp (1.4× kare crop), pose modelini crop üzerinde eğit/çalıştır. Etiket formatı
  aynı kalır, sadece crop dönüşümü eklenir.

---

## Faz 6 — PnP çözücü + değerlendirme (1 gün)

`poz_cozucu.py` çekirdeği:

```python
import cv2, numpy as np

C = np.array([[0,1,0],[0,0,-1],[1,0,0]], float)   # UE -> OpenCV eksen koprusu
                                                   # cv_x=ue_y, cv_y=-ue_z, cv_z=ue_x

def K_matrisi(W, H, fx):
    return np.array([[fx,0,W/2],[0,fx,H/2],[0,0,1]], float)

def poz_coz(kp_uv, kp_conf, model_cm, K, onceki=None, conf_esik=0.5):
    """kp_uv (6,2) piksel, kp_conf (6,), model_cm (6,3) arac-lokal UE cm (talon_keypoints.json).
    Donus: (mesafe_cm, R_ue_rel, t_ue_cm, rms) | None.
    R_ue_rel: hedef-lokal -> kamera-lokal (UE eksenleri)."""
    m = kp_conf > conf_esik
    if m.sum() < 4:
        return None
    obj = (C @ model_cm[m].T).T                    # lokal noktalar CV konvansiyonuna
    img = np.ascontiguousarray(kp_uv[m], dtype=np.float64)
    if onceki is not None:                          # onceki cozumle basla -> jitter azalir
        rvec, tvec = onceki
        ok, rvec, tvec = cv2.solvePnP(obj, img, K, None, rvec.copy(), tvec.copy(),
                                      useExtrinsicGuess=True, flags=cv2.SOLVEPNP_ITERATIVE)
    else:
        ok, rvec, tvec, _ = cv2.solvePnPRansac(obj, img, K, None,
                                               flags=cv2.SOLVEPNP_SQPNP,
                                               reprojectionError=6.0)
    if not ok:
        return None
    proj, _ = cv2.projectPoints(obj, rvec, tvec, K, None)
    rms = float(np.sqrt(np.mean(np.sum((proj.reshape(-1,2) - img)**2, axis=1))))
    if rms > 8.0:                                   # oturmayan cozumu reddet
        return None
    R_cv, _ = cv2.Rodrigues(rvec)
    R_ue = C.T @ R_cv @ C                           # kamera-UE <- hedef-lokal
    t_ue = (C.T @ tvec).ravel()                     # cm (model_cm cm oldugu icin)
    return float(np.linalg.norm(t_ue)), R_ue, t_ue, rms, (rvec, tvec)
```

**Çıktıların yorumu:**
- `mesafe = ‖t_ue‖` (cm) — doğrudan kameradan menzil.
- Hedefin **dünya yönelimi**: `R_dunya_hedef = R_cam @ R_ue_rel` →
  burun vektörü `f = R_dunya_hedef @ [1,0,0]` → `hedef_yaw = atan2(f[1], f[0])`,
  `hedef_pitch = atan2(f[2], hypot(f[0],f[1]))` (derece'ye çevir).
- **Aspect angle** (angajman için): görüş hattı `-t_ue/‖t_ue‖` ile hedef burnu
  arasındaki açı — arkadan yaklaşmayı/kaçış yönünü söyler.
- Kare-arası **EMA** (α≈0.3–0.5) veya mevcut CT-EKF kültürüne uygun küçük bir filtre
  ile mesafe/açıyı yumuşat; `rvec,tvec`'i sonraki kareye taşı.

`degerlendir.py`: val kayıtlarında **truth'a karşı** ölç (sim'in nimetini kullan):
- mesafe hatası: MAE cm ve % (mesafeye göre grafikle — 20 m'de 1 px keypoint hatası
  ≈ %2–2.5 mesafe hatası beklenir);
- açı hatası: hedef yaw/pitch telemetrisine karşı derece cinsinden.
- Başarı hedefi önerisi: **<20 m'de mesafe hatası <%5, yaw hatası <10°.**

---

## Faz 7 — Sisteme entegrasyon

CLAUDE.md ilkesine uygun: mevcut sistemi bozmadan, ayrı modül + anahtar.
- `detection/gorsel_tespit.py` kalıbında `PozDedektor` sarmalayıcı (hazir=False
  zarif bozulması dahil): kare → (bbox, 7×(u,v,conf)).
- `web/server.py` dedektör döngüsünde pose modeli varsa onu kullan; overlay'e
  noktalar + iskelet + **"MESAFE (KAMERA): 14.2 m / HEDEF YAW: 213°"** rozetini ekle
  (video kanıtı için altın değerinde).
- `guidance/ana_kontrol.py`: GORSEL_TAKIP fazında kamera-mesafesi angajman kararlarına
  (dalış zamanlaması), hedef yaw'ı lead öngörüsüne beslenebilir — GNSS bağımlılığı
  görünür şekilde azalır.
- FPS: yolo11s-pose @1280, RTX sınıfı GPU'da 60+ FPS; sorun olursa `imgsz` düşür
  veya ONNX/TensorRT'ye çevir.

---

## 🪤 Tuzak listesi (kısa ama hayati)

1. **UE = cm, sol-elli, X ileri; SDK tuple sırası (roll,pitch,yaw).** Tüm hatalar
   burada çıkar; Faz 2 testlerini atlama.
2. **flip_idx** yazılmazsa sol/sağ kanat çapraz öğrenilir — sessiz felaket.
3. **PNG kaydet** (JPEG artefaktı keypoint'i bozar); veri seti **OneDrive dışında**.
4. Oyun **tek TCP** kabul eder: kayıt scripti çalışırken arayüzü kapat.
5. W,H'yi her karede `frame.shape`'ten al; pencere client-area ≠ nominal çözünürlük.
6. Hedefi hep görüntü merkezine koyma (yaw ofseti) — merkez önyargısı.
7. Train/val'i **oturum bazında** ayır; ardışık kareler sızarsa metrik yalan söyler.
8. Görsel doğrulama kapısından (Faz 4) geçmeden eğitime başlama — 50 karede noktalar
   gözle doğru oturacak.
9. Uzak mesafe beklentisi: 40 m+ için pose isteme; orada bbox+kanat genişliği kaba
   mesafesi ve GPS füzyonu kullan.

## ✅ Sıralı kontrol listesi

- [x] Faz 0: truth AKIYOR — kullanıcının "Gerçek GPS" güdümü vuruş yapabiliyor ve o mod
      `get_debug_truth()`'tan besleniyor (`web/server.py:321`); script yine de açılışta doğrular
- [~] Faz 1: `kayit_ucusu.py` çalıştı (220 kare) AMA veri kullanılamaz — hedef hızlı+kaçışkan,
      drone 120 km/h kovaladı → **latency (telemetri↔kare hizasız) + motion blur**. `best.pt`
      kalibrasyonu: en iyi tilt'te bile 144px hata. **Çözüm: yavaş/sabit çekim** (hedef
      kontrolü kullanıcıya soruldu). Ayrıca kamerada ~15-25° YUKARI tilt VAR (tilt=0 yanlıştı).
      Altyapı hazır: `telemetri_akis.jsonl` (latency için), `pose/kalibre.py` (tilt+latency ölçer).
- [ ] Faz 2: işaret testleri geçti; projeksiyon çekirdeği `pose/geometri.py`'de (self-test ✓)
- [x] Faz 3: 6 nokta modeli HAZIR (kullanıcıdan geldi → `talon_keypoints.json`); kanat 171.8 cm ✓
- [~] Faz 4: rota DEĞİŞTİ — Photo-Mode "Zeylo" dataseti (`C:\talon_pose_data\dataset`, 379 kare,
      JSON'da KESİN kamera pozu; `pose/draw_keypoint.py` + MESH_PIVOT_OFFSET=+11.76cm ileri).
      Etiketler Colab'da üretildi (talon_v10) — sıra deneysel doğrulandı (aşağıda).
- [x] Faz 5: **talon_yolo11m_pose_2_best.pt eğitildi** (Colab, imgsz=960, 200 epoch/best@101;
      val mAP50(P)=0.756, mAP50-95(P)=0.555). Kopya: `models/talon_pose.pt`. "Orta" kalite.
- [x] Faz 6: `pose/poz_cozucu.py` (PnP+EMA, sentetik self-test ✓) + `pose/degerlendir_foto.py`
      (379 eğitim karesinde, İYİMSER): PnP çözüm %53; mesafe medyan |hata| %8 (0-10 m'de iyi),
      yaw medyan 6.3° — AMA 15 m+ mesafe ~+%90 şişiyor (model noktaları içeri büzüyor),
      %27 karede tespit yok. Hedef (<20 m'de <%5) TUTMADI → **terminal faz aracı (≈4-12 m)**.
      Örnek görseller + rapor.csv: `C:\talon_pose_data\pnp_degerlendirme\`.
- [x] Faz 7 (gözlemci kısmı): `detection/poz_tespit.py` (PozDedektor) + `web/server.py`
      dedektör döngüsünde best.pt'ye İLAVE poz çıkarımı (**güdüme GİRMEZ**; beyin girdisi
      değişmedi) + `gorsel.poz` telemetrisi + index.html iskelet overlay/"MESAFE (KAM)"
      rozeti + 📐 POZ KESTİRİMİ kartı (gerçekle kıyas). Güdüm beslemesi SONRAKI adım
      (model kalitesi onaylanırsa).

## 🔑 EĞİTİM SIRASI (talon_yolo11m_pose_2 — pose/sira_bul.py ile DENEYSEL bulundu)

Model kpt çıktı sırası JSON referans sırasından FARKLI:
`EGITIM_SIRASI = [0, 1, 2, 5, 3, 4]` → pred[k] = json[EGITIM_SIRASI[k]] =
**[burun, sol_kanat, sag_kanat, kuyruk_arka, sol_kuyruk, sag_kuyruk]**.
87 karede oy %76-86 diagonal; sol/sağ kanat 70'e 6 ayrıştı → **flip_idx felaketi YOK**.
PnP obje noktaları = `talon_keypoints.json[EGITIM_SIRASI] + MESH_PIVOT_OFFSET(11.76,0,0) cm`
(etiket üretimiyle birebir; t vektörü = kamera→ACTOR ORIGIN = get_target_location muadili).
Model yeniden eğitilirse `python pose\sira_bul.py` ile sırayı YENİDEN doğrula.

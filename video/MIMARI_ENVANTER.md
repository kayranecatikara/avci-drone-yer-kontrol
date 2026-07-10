# MİMARİ ENVANTER — Simülasyon Uçuş Kanıt Videosu Hazırlığı

> **Kaynak durumu (bu envanterin çekildiği an):** branch `sade-gorsel-guduum-ve-log-temizligi`,
> **çalışma ağacındaki güncel kod** (10 Tem 2026; commit edilmemiş tune değişiklikleri dahil).
> Envanter **koddan** çıkarıldı; CLAUDE.md / README / MEVCUT_DURUM ile çelişen her yerde
> **kod esas alındı** (bayatlık notları en altta). Testler bu ağaçta yeşil:
> `test_ibvs_gorsel` 27/27 · `test_kilit_takip` 17/17 · `test_takip` 5/5 · `test_sahi` 11/11.

> **⚠️ Bu branch'in main'den kritik farkları (video anlatımını doğrudan etkiler):**
> 0. **GPS YIĞINI YENİLENDİ (2026-07-10):** İnovasyonlu J (CT-EKF) SİLİNDİ. GPS filtresi
>    **`fusion/gnss_filtre.py` (GNSSFiltre)**, GPS güdümü **`guidance/gps_takip.py` (GPSTakip)**.
>    `AvciKontrol` GPS fazında bunlara DEVREDER (§2, §3).
> 1. **Pose tamamen KAPALI** (`web/server.py: POSE_AKTIF=False`; roll-lead Cfg parametreleri
>    silindi → `ibvs_gorsel._roll_lead` fiilen no-op). Güdüme giren tek görsel girdi **bbox**.
> 2. **Tracker = boxmot HybridSort** (`detection/takip.py` adaptörü). El yazımı ByteTrack +
>    gyro-CMC 9 Tem'de kullanıcı kararıyla kaldırıldı.
> 3. **SAHI dilimleme** eklendi (kendi temiz implementasyonumuz, `gorsel_tespit._sahi_ham`).
> 4. **PROP_MASKE = []** (pervane/HUD maskesi kapalı; yanlış-pozitifleri tracker onayı emiyor).
> 5. Model: **best.pt = YOLO26s @960** (tek sınıf `talon`, 9 Tem eğitimi). Dedektör `imgsz=960`.

---

## 1. Uçtan uca veri akışı

İki bağımsız girdi, üç kalıcı iş parçacığı, tek çıkış (drone input paketi):

```
GİRDİ 1: TCP telemetri (oyun, 127.0.0.1:12345)          GİRDİ 2: Oyun penceresi GÖRÜNTÜSÜ
  bozuk hedef GNSS (cm, nominal 5 Hz) + kendi              windows-capture (pencere içeriği,
  konum/rotasyon/hız (temiz, tam hız)                      occlusion-proof; watchdog'lu)
        │  sdk/drone_sdk.py (resmi SDK v2.2)                     │  mss ekran-bölgesi fallback
        ▼                                                        ▼
┌─ kontrol_dongusu (50 Hz) ────────────┐   ┌─ dedektor_dongusu (GPU hızında, ~8-25 FPS) ─┐
│ beyin.adim() [beyin_lock altında]    │   │ grab_frame_bgr() → doğal çözünürlük kare    │
│  GPS fazı → self.gps.adim():         │   │ HedefDedektor.tespit_hepsi(bgr):            │
│   guidance/gps_takip.GPSTakip        │   │   YOLO26s predict @imgsz=960 (FP16)         │
│    kalkış(AGL) → fusion/gnss_filtre  │   │   + SAHI: koşullu 640px dilim + NMS merge   │
│    (spike temizle + hız + gecikme    │   │ → TÜM kutular → Takipci.guncelle(dets,      │
│    telafisi) → DR → PD + PID → yaw    │   │   frame): boxmot HybridSort → en iyi        │
│  FSM: ARAMA/KILIT ↔ GORSEL_GUDUM     │   │   onaylı iz (track_id, tespit_mi)           │
│  GÖRSEL faz → AvciIBVS.hesapla       │   │ → GÜDÜM KAPISI: conf ≥ VIS_CONF_MIN ise     │
│    (yalnız bbox; §3.3)               │   │   beyin.set_gorsel_tespit(det) [lock içinde]│
│  _send / gps._send: rate-limit       │   │ → zayıf tespit yalnız arayüze (turuncu)     │
│     → drone.set_control_surfaces(    │   └─────────────────────────────────────────────┘
│        throttle, pitch, roll, yaw,   │   ┌─ HTTP sunucu (:8000, ThreadingHTTPServer) ──┐
│        arm)  ► OYUNA GİDEN INPUT     │   │ /api/telemetry (tam durum ~5 Hz poll)       │
└──────────────────────────────────────┘   │ /api/gorsel (hızlı bbox kanalı ~15 Hz)      │
   + connection_manager (2 sn: TCP         │ /api/frame (FPV JPEG) · /api/tune (canlı)   │
     yeniden bağlanma + pencere-yakalama   │ /api/command (görev başlat/durdur/mod)      │
     watchdog)  + tune_log_dongusu (1 Hz)  │ → web/index.html (FPV+overlay, paneller)    │
                                           └─────────────────────────────────────────────┘
```

- **Kontrol ile algı ayrık:** ağır inference `beyin_lock` DIŞINDA koşar; yalnız sonuç kilit
  içinde beyne yazılır → 50 Hz kontrol döngüsü hiç tıkanmaz.
- **Arayüz FPV'si** tarayıcı ekran/pencere paylaşımıdır (`getDisplayMedia`, "📡 Görüntüyü
  Bağla"); overlay (bbox, kilit dörtgeni, rozetler) istemci canvas'ında telemetriden çizilir.
  Dedektörün gözü ise sunucu tarafındaki windows-capture karesidir (ikisi bağımsız).
- **Bbox yaş telafisi:** arayüz kutuyu tespit yaşı × görüntü-hızı kadar ileri çizer
  (`/api/gorsel: yas_s, vx, vy`) → inference gecikmesi görsel olarak telafi edilir.

## 2. Durum makinesi — kodda GERÇEKTE olan (guidance/ana_kontrol.py)

Güdüm FSM'i `AvciKontrol.durum` (3 durum) + salt-gözlem katmanları:

| Geçiş | Koşul (kod, sayısal) |
|---|---|
| (başlangıç) → kalkış | `GPSCfg.TAKEOFF=True`: kalkış noktasından `TAKEOFF_ALT_AGL=10 m` tırman (`thr=0.6`), sonra yaklaşma |
| **ARAMA → KILIT** | yatay mesafe `d_h < HANDOFF_RANGE=40 m` (histerezis: `>50 m`'de geri ARAMA). KILIT = "görsel devir hazır" bayrağı; güdüm hâlâ GPS. `d_h` = filtre-temiz hedef ↔ drone (AvciKontrol hesaplar) |
| **KILIT → GORSEL_GUDUM** (OTO) | `AUTO_VISUAL_HANDOFF=True` VE ard arda `VIS_N_LOCK=5` kare `conf ≥ VIS_CONF_MIN=0.15` tespit VE handoff yakınlığı → `ibvs.sifirla()` ile taze rampa |
| **GORSEL_GUDUM → ARAMA** (OTO) | gerçek kayıp: tespit `VIS_STALE_S=0.5 s`'ten bayat VE köprü (`VIS_KOPRU_S=1.2 s`) de dolmuş VE `VIS_LOST_TO_GPS_S=0` → ANINDA GPS'e dön (kilit penceresi temizlenir, `kilit_ok` latch'i korunur) |
| Manuel switch | arayüz OTO/GPS/GORSEL: GPS=görsel yol kapalı; GORSEL=kilit sayacı atlanır, kayıpta dönmez (hover) |

**GPS-yaklaşma fazı (ARAMA/KILIT) — `guidance/gps_takip.GPSTakip.adim()` (2026-07-10 devri).**
`AvciKontrol.adim()` bu fazda `self.gps.adim()` çağırır; mekanik ve sabitler (`GPSCfg`) o
dosyadadır: **kalkış** (AGL, `TAKEOFF_ALT_AGL`) → **GNSS temizleme** (`fusion/gnss_filtre`)
→ **kesintide ölü-hesap** (yeni paket gelmiyorsa son hızla ileri tahmin, `DR_MAX_S=30 s` tavan)
→ **standoff nişan** (`APPROACH_STANDOFF=0`, hedefin `APPROACH_ALT_OFFSET=5 m` altı) → dünya→gövde
→ yatay **PD** (`KP_H=0.00025, KD_H=0.0006`, EMA türev) → dikey-yatay ayrıştırma (araç hedefin
üstündeyse ileri itkiyi kıs) → **dikey PID** (`KP_Z/KI_Z/KD_Z`, anti-windup band) → burnu
hedefe çevir (`KP_YAW=1.3`) → **eksen-bazlı rate-limit** (`MAX_DELTA_THR=0.12` dikey daha hızlı,
`_PITCH/_ROLL/_YAW=0.08`) → `set_control_surfaces`. Filtre yalnız yeni ham pakette güncellenir;
kesintide `_son_fresh_t`'den geçen süre DR'yi sürer. Dönüşte `AvciKontrol` handoff mesafesini
hesaplayıp `durum`u ARAMA/KILIT yapar + uçuş logunu yazar.

**GNSS filtresi (`fusion/gnss_filtre.GNSSFiltre`):** pencereli ham örnek tamponu üstünde her
eksende **spike temizleme** — komşu noktalardan lineer-eğim ile beklenen konumu kestirir, ölçüm
hız+konum eşiğini birlikte aşarsa (`x/y/z_spike_temizle`) o örneği tahminle değiştirir (en fazla
`max_hold` ardışık). Temiz seriden son `vel_n=7` noktanın eğimiyle **hız** kestirir (gerçekçi
hedef hızına `MAX_HEDEF_HIZ=40 m/s` kırpılır, EMA yumuşatma). **Güven-ağırlıklı gecikme telafisi:**
kısa-pencere hızı ile yumuşak hız tutarlıysa güven yüksek → konumu `gecikme_sn=1 s` ileri taşır
(`GAP_DT=2.5 s`'lik boşluk sonrası cooldown ile lead kısılır). `guncelle()` lead'li konum döner;
`durum_gudum()` lead'siz `{pos, vel}` (güdümün kendi lead'i ayrı; çift-lead olmaz).

**GÖRSEL faz (GORSEL_GUDUM):** komut YALNIZ `AvciIBVS.hesapla(det, Cfg, ...)` — imzada konum/hız/
rotasyon YOK (GPS yapısal olarak giremez; `test_gps_siz_imza` kilitler). Ayrıntı §3.3.

**Kayıp merdiveni (görsel fazda):** son tespit `VIS_STALE_S=0.5 s` boyunca geçerli sayılır →
sonra **görüntü-düzlemi KÖPRÜ** (`VIS_KOPRU_S=1.2 s`): bbox son ölçülen görüntü-hızıyla ileri
taşınır (cy DONAR, thr=0 irtifa-tut; kilit sayacına SAYILMAZ, loga `vis_kopru=1`) → köprü de
dolarsa kayıp: OTO'da anında GPS'e dönüş, manuel GORSEL'de hover.

**Kilitlenme isteri sayacı (şartname 6.1.2/6.1.4) — SALT GÖZLEM, komuta girmez:**
`_kilit_degerlendir` her görsel tik: hedef merkezi **AV** içinde (yatay %25–75 `VIS_AV_X`,
dikey %10–90 `VIS_AV_Y`) VE bbox en az bir eksende ≥ `VIS_LOCK_PCT=0.06` (şartname %5 + hakem
marjı) → o tik "kilitli". 10 sn kayan pencerede (`VIS_WIN_S`) kümülatif ≥ 5 sn
(`VIS_WIN_NEED_S`) → `kilit_ok` LATCH (kesintili kilit sayılır — şartname örneği 1+2+2).

**Görev izleyici fazları (web/server.py `_gorev_izle` — arayüz/kanıt katmanı, güdüme dokunmaz):**
`YAKLASMA → KILIT → ANGAJMAN → VURUS → BASARI`. ANGAJMAN çipi = görsel faz + takip canlı +
`kilit_ok` latch'i. **VURUŞ latch'i**: mesafe < `VURUS_ESIK_M=3 m` (truth varsa gerçek 3B, yoksa
filtre-temiz; **ham asla**). BASARI = vuruştan 1.5 sn sonra kalıcı banner. Kenar-tespitli olay
günlüğü: İLK TESPİT / YENİDEN TESPİT / TAKİP KAPANDI / GÖRSEL GÜDÜME GEÇİLDİ / KİLİT İSTERİ
SAĞLANDI / ANGAJMAN / VURUŞ! / GÖREV BAŞARILI.

**⛔ TERMİNAL VURUŞ FAZI KODDA YOK (bilinçli).** Görsel yasa şu an **KİLİT-TUT** modunda: bbox
boyutunu `IBVS_BOYUT_HEDEF=0.08`'e süren P-yasa hedefin gerisinde istasyon tutar (kilit
penceresini doldurmak için). Koddaki taslak izler (Cfg yorumları): *"Terminal vuruş AYRI faz
olarak sonra eklenecek — kilit_ok sonrası bilinçli angajman kararıyla ayrı banda geçilecek
(NISAN→1, boyut regülasyonu kapat / İLERİ tam)"*. → Soru turunda netleştirilecek; video metni
bölüm 0.1 istisnasıyla tamamlanmış hali `[VURUŞ-BAĞIMLI]` etiketiyle anlatacak.

## 3. Çekirdek modüller (canlı uçuş hattı — teslim zip'inin özü)

| Dosya | İşlev | Algoritma/Yöntem | Girdi | Çıktı |
|---|---|---|---|---|
| `main.py` | giriş noktası | — (`web.server.main()` çağırır) | — | tüm thread'ler + :8000 |
| `sdk/drone_sdk.py` | resmi SDK v2.2 (şartname "input.py" muadili) | TCP satır-protokolü; 7 bozulma bayrağı çözümü | oyun telemetrisi | `get_*` telemetri; `set_control_surfaces(thr,pitch,roll,yaw,arm)` |
| `fusion/gnss_filtre.py` | GNSS temizleme + hedef hız kestirimi (GNSSFiltre) | **eksen-bazlı spike temizleme** (pencereli lineer-eğim tahmini; hız+konum eşiğini aşan ölçüm tahminle değiştirilir) + eğimden hız (`MAX_HEDEF_HIZ` kırpma, EMA) + **güven-ağırlıklı gecikme telafisi** (tutarlı hızda `gecikme_sn` lead; boşluk sonrası cooldown) | bozuk hedef GNSS (cm) | `guncelle()`: lead'li konum; `durum_gudum()`: lead'siz `{pos, vel}` |
| `guidance/gps_takip.py` | GPS-yaklaşma güdümü (GPSTakip + GPSCfg) | kalkış (AGL); GNSS temizleme çağrısı; kesintide ölü-hesap (DR ≤30 s); yatay PD + dikey-yatay ayrıştırma + dikey PID (anti-windup); yaw; eksen-bazlı rate-limit; kendi `_send`/`set_control_surfaces` | drone telemetri + bozuk hedef GNSS | 4 eksen kontrol komutu (oyuna); `son_temiz/son_xy_anlik/son_hiz` (AvciKontrol proxy okur) |
| `guidance/ana_kontrol.py` | karar beyni: FSM + görsel faz + Cfg (görsel) + uçuş logu | §2 FSM (handoff); GPS fazında `gps.adim()` devri; görsel faz (IBVS); kilit sayacı; köprü/kayıp yönetimi; görsel `_send` `MAX_DELTA=0.05` | GPS proxy'leri, kendi telemetri, `set_gorsel_tespit` bbox'ı | GPS: `gps.adim()`; görsel: `_send()` → drone input; `veri/ucus_log_*.csv` |
| `guidance/ibvs_gorsel.py` | **TEK görsel güdüm yasası (AvciIBVS)** | basit IBVS + katmanlar (§3.3) | `det{cx,cy,w,h,conf,W,H,t}`, Cfg, ego roll/pitch (IMU) | `(thr, pitch, roll=0, yaw)` + telemetri sözlüğü |
| `detection/gorsel_tespit.py` | YOLO tespit sarmalayıcı | ultralytics predict (FP16, imgsz=960) + **SAHI** (kendi impl: koşullu 640px %20 örtüşmeli dilimler + tam kare + sınıf-agnostik NMS 0.5; tam karede conf≥0.5 varsa dilim atlanır) + pervane maske filtresi (şu an boş) | BGR kare | conf-azalan tespit listesi (piksel bbox + cls + t) |
| `detection/takip.py` | çoklu-nesne takip adaptörü | **boxmot HybridSort** (observation-centric SORT + BYTE ikinci turu + uzun-dönem bank; ReID kapalı; ECC kamera-hareket telafisi ~3.5 ms/kare); tek-hedef sözleşmesi: en yüksek conf'lu onaylı iz | tespit listesi + BGR kare | en iyi iz dict (`track_id, tespit_mi=True, cx,cy,w,h,conf,cls`) \| None |
| `detection/pencere_yakala.py` | oyun penceresi İÇERİĞİ yakalama | Windows.Graphics.Capture (windows-capture); süreç-adı öncelikli pencere seçimi (tarayıcı sekmesi elenir); bayat-kare/yanlış-pencere **watchdog** → otomatik yeniden bağlanma | HWND | son BGR kare (`get_latest_bgr`) |
| `web/server.py` | yer istasyonu sunucusu: 4 thread + HTTP API + telemetri payload + görev izleyici + canlı tune | §1'deki akış; `TUNE_ALLOW` allowlist'li canlı parametre; tune/perf/gps logları; olay günlüğü | her şey | `build_telemetry()` JSON; API uçları |
| `web/index.html` | tarayıcı arayüzü (tek dosya) | FPV (getDisplayMedia) + canvas overlay: bbox+merkez+ID, **şartname kilit dörtgeni (kırmızı #FF0000, kilitte 3 px)**, AV çerçevesi (Şekil 2), nişan noktası + IBVS hata çizgisi, KÖPRÜ rozeti, "GPS GÜDÜMÜ: KAPALI/AÇIK" + TAKİP rozetleri, VURUŞ!/GÖREV BAŞARILI banner; mini-harita (kuşbakışı avcı+hedef), olay günlüğü, faz çipleri, BOZUK GNSS / TAKİP / KİLİTLENME (10 sn şerit) / IBVS / GÜDÜM KOMUTLARI kartları; tune slider'ları; klavyeli manuel mod | /api/* | görsel kanıt (videonun 10 isteri) |
| `web/tune_rapor.py` | uçuş sonrası Excel raporu | uçuş+tune loglarını hizalar; segment kıyası (parametre değişimi başına metrik), kilit/merkezleme/kapanma metrikleri | `veri/ucus_log_*.csv`, `tune_log_*.csv` | `veri/tune_rapor_*.xlsx` + `tune_parametreler/ucus_N/` klasörü |
| `config.py` | konuşlandırma ayarları | — | — | WEB_HOST/PORT, başlangıç model adı |

### 3.3 Görsel yasa ayrıntısı (`ibvs_gorsel.AvciIBVS.hesapla` — aktif sürüm)

Temel fikir: **nişan noktasından bbox merkezine çizgi**; çizginin bileşenleri komut olur.
`ex=(cx−W/2)/(W/2)`, `ey=(cy−H/2)/(H/2)`, EMA yumuşatma (`VIS_EMA=0.4`). Katmanlar (hepsi
YALNIZ kamera verisi + kendi IMU'su; sırayla):

1. **Ego-pitch telafisi:** `ey_dünya = ey_f − 0.4·tan(own_pitch)/tan(VFOV/2)` — gövde öne
   yatınca kameranın düşmesinin yarattığı sahte dikey hatayı siler (`IBVS_EGO_PITCH_GAIN=0.4`).
2. **Tilt-farkında dikey nişan:** `ey_ref = NISAN·tan(25°)/tan(47.2°)`; `IBVS_DIKEY_NISAN=−0.25`
   → hedef merkezin ÜSTÜNDE tutulur → araç hedefin ALTINDA, gökyüzü arka plan (**alttan vuruş**
   geometrisi). Dikey sapma `eyy = ey_dünya − s·ey_ref`.
3. **Yumuşak geçiş rampası:** görsel faz başından `IBVS_HANDOFF_S=1.0 s` boyunca `s:0→1`;
   yalnız ileri-itki ve dikey-nişanı rampalar (yaw + dikey-ortalama ilk tikten tam güç).
4. **Yakınlık-ölçekli kazanç (10 Tem):** `k_yakin = 1 + IBVS_YAKIN_KAZANC·clamp(boyut/BOYUT_HEDEF,0,2)`
   — yaklaştıkça açısal hız büyür, kazanç otomatik sıkılaşır (`YAKIN_KAZANC=1.0`).
5. **Komutlar:** `yaw = ±K_YAW·k_yakin·ex` (K_YAW=1.2, tavan `YAW_MAX=0.80`);
   `thr = ±K_DIKEY·k_yakin·(−eyy)` (K_DIKEY=2.15, `THR_DN=−1.0..THR_UP=0.70`); **roll = 0**.
6. **KİLİT-TUT ileri kanalı:** `ileri = clamp(K_BOYUT·(BOYUT_HEDEF−boyut_f), −GERI_MAX, İLERİ)`
   (K_BOYUT=20, hedef 0.08, geri kaçış tavanı 0.30, ileri tavan `IBVS_ILERI=0.75`). Uzakta tavan
   hızla yaklaşır, %8 bbox'ta istasyon tutar, fazla yakınsa geri kaçar.
7. **Kapanma-hızı freni (TTC, 10 Tem):** bbox büyüme hızı `dboyut/dt` (EMA'lı) pozitifse
   `ileri −= IBVS_FREN_HIZ·dboyut/dt` (FREN_HIZ=8) — hedefi AŞMADAN kilit bandına oturt.
8. **Frenler:** merkez freni (`kisma = 1−1.1·r`) + alçalma freni (`alcal`, eyy>0'da, taban 0.2);
   ikisi de `yak` ağırlığıyla YALNIZ kilit-tut bandında devrede (uzakta baypas → tam ileri).

Not: `guidance/ibvs_gorsel_simple.py` daha sade bir alternatif yasa (EMA + tek sabit nişan;
katmansız) — **hiçbir yerden import edilmiyor**, canlı hatta değil.

## 4. Modeller

| Dosya | Mimari | Eğitim | Durum |
|---|---|---|---|
| `models/best.pt` (20.4 MB) | **YOLO26s** (detect), 1 sınıf: `talon` | imgsz=960, 200 epoch, 9 Tem 2026, ultralytics 8.4.90 (Colab) | **AKTİF** — dedektör imgsz=960, FP16 |
| `models/talon_pose.pt` (21.7 MB) | YOLO26s-pose, 6 keypoint | imgsz=640, 200 epoch, 8 Tem 2026 | **KAPALI** (`POSE_AKTIF=False`) — yüklenmiyor |

⚠️ Depo kökünde başıboş model kopyaları var (`best (1).pt`, `best 6.pt`, `best7.pt`,
`best_son.pt`, `eniyi_bbox.pt`, `eniyi_pose.pt`, `models/talon_pose_eski_20260709.pt`) —
teslim zip'ine girmemeli (YAPILACAKLAR'a alındı).

## 5. Açık kaynak kütüphaneler (kurulu sürümler — video "kaynak kod turu" bölümü için)

| Kütüphane | Sürüm | Rol |
|---|---|---|
| Python | 3.11.9 | çalışma zamanı |
| ultralytics | 8.4.83 | YOLO26s inference (tespit; pose kapalı) |
| torch | 2.5.1+cu121 (CUDA) | inference backend (FP16) |
| opencv-python | 4.13.0 | kare ölçekleme/JPEG, debug pencere, boxmot ECC |
| numpy | 2.4.6 | filtre/güdüm vektör aritmetiği |
| **boxmot** | 21.0.0 | **HybridSort** çoklu-nesne takip |
| mss | 10.2.0 | ekran yakalama (fallback) |
| windows-capture | 2.0.0 | pencere-içeriği yakalama (birincil kare kaynağı) |
| Pillow | 12.2.0 | JPEG kodlama (cv2 yoksa) |
| pygetwindow | 0.0.9 | pencere bölgesi bulma (mss yolu) |
| openpyxl | (requirements'ta) | tune Excel raporu (uçuş hattı dışı) |
| stdlib | http.server, socket, threading, csv, json | sunucu + SDK + loglar |

Hazır güdüm yazılımı YOK (kural 6): filtre, güdüm yasaları, FSM, SAHI el yazımı; dış hazır
bileşenler yalnız **tespit (ultralytics)** ve **takip (boxmot)** — ikisi de açık kaynak,
videoda beyan edilecek.

## 6. Şartname → kod eşlemesi (kanıt noktaları)

| Şartname isteri | Koddaki karşılık |
|---|---|
| Bozuk GNSS'in girdi alınması + hatalı ölçüm eleme | `drone_sdk.get_target_location` (7 bozulma tipi) → `gnss_filtre` eksen-bazlı spike temizleme + hız/güven kapıları; arayüz BOZUK GNSS kartı (bozulma adları + KESİNTİ rozeti + ham/filtre hata kıyası) |
| Arama algoritmik yürütülmeli | ARAMA fazı (`gps_takip`): filtre-temiz konuma PD/PID güdüm (manuel hedef girişi yok) |
| Tek karelik tespit yetmez, doğrulama şart | HybridSort iz onayı (min_hits=3) + güdüm kapısı conf≥0.15 + `VIS_N_LOCK=5` ardışık kare şartı |
| Kilit: 10 sn pencerede ≥5 sn kümülatif; bbox ≥%5 (tavsiye %6); AV bandı | `_kilit_degerlendir`: `VIS_LOCK_PCT=0.06`, `VIS_AV_X=0.25/VIS_AV_Y=0.10`, pencere 10/5 sn; UI kırmızı #FF0000 dörtgen (kilitte 3 px) + 10 sn şerit |
| Kilit dörtgeni kırmızı #FF0000, ≤3 px | `index.html` overlay: `kilit ? "#FF0000" : ...`, lineWidth 3 |
| Angajman: son 3 sn aktif takip + mesafenin sistematik azalması + hedef doğrultusunda çarpışma vektörü | uçuş logu (50 Hz komut+mesafe+bbox kolonları) + olay günlüğü + ANGAJMAN çipi; terminal faz eklenince komut zinciri kanıtı `[VURUŞ-BAĞIMLI]` |
| GNSS'siz görsel takip kanıtı | `GORSEL_GUDUM`'da GPS yönelimi MİMARİ kesik (`adim()` erken return; `hesapla` imzasında konum yok) → UI "GPS GÜDÜMÜ: KAPALI" kırmızı rozeti + olay kaydı |
| İnsan müdahalesiz otonomi | OTO mod: handoff→görsel→(kayıpta) GPS revert tam otonom; manuel mod ayrı ve görevle karşılıklı dışlar |
| Yer istasyonu merkezli işleme | tüm algoritma yer istasyonunda; drona yalnız input paketi gider (`set_control_surfaces`) |

## 7. Yardımcı / pasif / geliştirme modülleri (canlı hatta DEĞİL)

| Yol | Ne | Durum |
|---|---|---|
| `guidance/ibvs_gorsel_simple.py` | sade alternatif IBVS yasası | import edilmiyor (aday/yedek) |
| `detection/poz_tespit.py`, `pose/poz_cozucu.py`, `detection/talon_pose_estimator.py`, `pose/*` | pose inference + PnP poz kestirimi zinciri | `POSE_AKTIF=False` → yüklenmiyor |
| `detection/kamera_model.py` | K matrisi + 25° tilt tek kaynağı; gyro-CMC homografisi | CMC kapalı (`TAKIP_CMC_AKTIF=False`); HybridSort kendi ECC'sini kullanır |
| `detection/algi_hatti.py`, `detection/model_yonetici.py`, `web/dev_truth.py`, `iletisim/hakem_istemci.py` | yarisma-pipeline katmanları (algı hattı, model registry, DEV truth kaynağı, hakem sunucu istemcisi stub'ı) | server'a bağlı değil (final aşaması / araç) |
| `arac/` (analiz_ucus, ab_kiyas, paket_kontrol, prova_kaydedici, attitude_dogrula, cmc_isaret_testi, filtre_dogrulama, gps_gorsellestir, kosu_yonetici, egitim/…) | uçuş-sonrası analiz + doğrulama + paketleme araçları | teslim zip'i dışı (paket_kontrol karar verir) |
| `araclar/` (gorsel_episode_analiz, kp_sira_dogrula, pose_ongoru_analiz) | görsel faz / pose analiz araçları | araç |
| `png_sim/` | eski PN güdüm offline simülatörü | miras (canlı yasayla ilgisiz) |
| `arsiv/` | eski sürümler | miras |
| `tests/` (16 dosya) | birim testler (`python tests/test_x.py` ile koşar) | çekirdek 4 dosya yeşil (üstte) |
| `1_Oyunu_Baslat.bat/.sh`, `2_Arayuzu_Baslat.bat/.sh` | tek tık başlatıcılar | çalıştırma talimatı malzemesi |

## 8. Doküman bayatlık notları (video metni KODA dayanacak)

- **CLAUDE.md:** pose/roll-lead AKTİF anlatır → bu branch'te KAPALI. ByteTrack anlatır →
  HybridSort. best.pt@1280 der → YOLO26s@960. PROP_MASKE dolu der → boş.
- **README.md:** "windows-capture bilinçli KAPALI" der → AÇIK (`PENCERE_YAKALA_AKTIF=True`);
  "kayıpta ~1.5 sn sonra GPS" der → anında (0 s; 0.5 s stale + 1.2 s köprü var); VIS_EY_REF /
  VIS_SIGN_VZ slider adları eski.
- **MEVCUT_DURUM.md / docs/anlatim kartları / docs/video_prova_kontrol.md:** yarisma-pipeline
  dönemi (GPS_TERMINAL_STRIKE, OIPN, ByteTrack, TENTATIVE/LOST rozetleri) — akış iskeleti ve
  "müsabaka kaydedicisi finale, sim videosu MUAF" notu hâlâ değerli; teknik adlar bayat.
- Sunucu içi yorumlarda "ByteTrack" adı geçse de gerçek tracker HybridSort'tur (takip.py).

## 9. KARAR KAYDI — soru turu sonuçları (10 Tem 2026, kullanıcı onayı)

1. **Kod tabanı:** video + zip = **bu branch'in güncel hali** (HybridSort + SAHI + pose kapalı).
2. **✅ GPS TARAFI YENİLENDİ (ENTEGRE — 2026-07-10):** İnovasyonlu J söküldü; `fusion/gnss_filtre.py`
   (GNSSFiltre) + `guidance/gps_takip.py` (GPSTakip) entegre edildi. `AvciKontrol` GPS fazında
   `gps.adim()`'e devreder (§2, §3). Arayüzden İnovJ metinleri kaldırıldı; testler + uçtan uca
   sahte-drone doğrulaması yeşil. **CANLI sim uçuşu doğrulaması bekliyor** (§ altta YAPILACAKLAR).
3. **Pose:** videoda ve kod turunda HİÇ anlatılmayacak (sistem bbox-tabanlı anlatılır).
4. **Terminal faz — PAKET A kabul edildi:** taban tetik `kilit_ok` latch'i; EK şart: son ~1 sn
   boyunca (a) IBVS sapması `r < 0.20` (hedef nişanda, kararlı) VE (b) o sürede GERÇEK tespit
   (köprü/tahmin değil). Üçü birden → terminal band: `IBVS_DIKEY_NISAN→1` (hız vektörü hedefe),
   boyut regülasyonu (`K_BOYUT=0`) + TTC freni kapalı, İLERİ tavan tam. ABORT: hedef
   kaybedilirse terminal iptal → kilit-tut'a/köprüye dönüş. (Şartname 6.1.3 "son 3 sn aktif
   takip" kanıtıyla hizalı.)
5. **Vuruş kararı:** ayrı "vur" komutu YOK — terminal band kapanmaya devam eder, temas oyun
   fiziğiyle gerçekleşir. Kanıt: oyun görüntüsündeki çarpışma + arayüz VURUŞ! latch'i
   (≤3 m truth/filtre-temiz) + GÖREV BAŞARILI banner'ı.

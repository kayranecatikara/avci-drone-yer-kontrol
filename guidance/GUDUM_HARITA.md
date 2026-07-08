# GÜDÜM HARİTASI — hangi kod ne işe yarıyor (takım anlatımı / kural 8)

> **2026-07-07 BÜYÜK SIFIRLAMA:** PN/PNG görsel güdüm yığını (LOS vektörü, Omega,
> pinhole menzil, kapanma regülasyonu, look-up geometrisi, soft-start, lead-yaw,
> YAKLASMA/TAKIP/TERMINAL alt-FSM'i) kullanıcı kararıyla KOMPLE SİLİNDİ
> (`guidance/png_gorsel.py` + 3 test dosyası; git geçmişinde durur). Yerine
> **BASİT IBVS** yazıldı: görüntü merkezinden bbox merkezine çizgi çek; çizginin
> açısı + büyüklüğü doğrudan komuta çevrilir. Tek dosya: `guidance/ibvs_gorsel.py`.

## 1) Veri akışı (uçtan uca)

```
OYUN (Drones of War)
  │ drone_sdk (telemetri: konum/rotasyon/hız; BOZUK hedef GNSS)
  ▼
web/server.py  kontrol_dongusu (50 Hz, beyin_lock altında)
  │  beyin.adim()  ← görev aktifken; manuel/pasifte beyin._hedef_temizle()
  ▼
guidance/ana_kontrol.py  AvciKontrol ("beyin")
  │  GPS yaklaşma: fusion/inovasyonlu_j_v2 (J filtre) → PD + standoff + fren
  │  Görsel faz  : _gorsel_guduum → guidance/ibvs_gorsel.py (BASİT IBVS)
  ▼
_send(thr, pitch, roll, yaw) → rate-limit → drone.set_control_surfaces

GÖRSEL TESPİT (ayrı thread, server.py dedektor_dongusu):
  windows-capture pencere karesi → detection/gorsel_tespit.py (best.pt, YOLO)
  → conf≥VIS_CONF_MIN ise beyin.set_gorsel_tespit(det)   [güdüm kapısı]
  → conf≥0.25 zayıf tespitler yalnız ARAYÜZE (turuncu kutu)
  POZ (ilave, seyrek POZ_HER_N): detection/poz_tespit.py (talon_pose.pt, 6 keypoint)
  → beyin.set_gorsel_poz(poz)  [kanat uçlarından hedef ROLL → öngörülü yaw lead; GÖRSEL veri]
```

## 2) FSM (self.durum)

| Durum | Anlamı | Giriş koşulu | Çıkış |
|---|---|---|---|
| `ARAMA` | GPS yaklaşma, hedef uzak | başlangıç / görsel kayıp | d_h < `HANDOFF_RANGE` → KILIT |
| `KILIT` | GPS yaklaşma + görsel devir hazır | handoff histerezisi | görsel kilit → GORSEL_GUDUM; d_h > `HANDOFF_EXIT` → ARAMA |
| `GORSEL_GUDUM` | yönelim YALNIZ kameradan (basit IBVS) | OTO: `AUTO_VISUAL_HANDOFF` + ard arda `VIS_N_LOCK` tespit + handoff; MANUEL: vismode=GORSEL | kayıp > `VIS_LOST_TO_GPS_S` (yalnız OTO) → ARAMA |

vismode anahtarı (arayüz OTO/GPS/GORSEL): GPS = görsel yol kapalı; GORSEL =
kilit sayacı atlanır, kayıpta GPS'e dönmez (tune modu); OTO = otomatik zincir.

**Kayıp yönetimi (sade):** server son tespiti `VIS_STALE_S` (0.5 s) boyunca zaten
sunar (kareler arası boşluk köprülenir). Gerçek kayıpta komut = **HOVER** (yerinde
bekle, yeniden tespit ara); kayıp `VIS_LOST_TO_GPS_S`'i (2 s) aşarsa (yalnız OTO)
GPS'e geri dön → yeniden yaklaş → yeniden kilitle. Kör-devam / yakın-menzil
yapışkanlığı gibi katmanlar SİLİNDİ.

**KİLİTLENME İSTERİ SAYACI (şartname 6.1.2/6.1.4) — SALT GÖZLEM:** her görsel tikte
`_kilit_degerlendir`: hedef merkezi **Hedef Vuruş Alanı** içinde (yatay %25–75,
dikey %10–90 = `VIS_AV_X/Y`) VE bbox **en az bir eksende** ≥ `VIS_LOCK_PCT` → o tik
"kilitli". 10 sn kayan pencerede kümülatif ≥ 5 sn → `kilit_ok` LATCH. Kesintili kilit
sayılır (şartname örneği 1+2+2=5 sn). **Sonuç hiçbir komuta girmez** — kırmızı kilit
dörtgeni, 5/10 sn sayacı, ANGAJMAN çipi ve olay günlüğü kanıtı için yaşar. GPS'e
düşüşte pencere temizlenir, `kilit_ok` latch'i korunur.

## 3) adim() yol haritası (her tik)

1. Poz/hız oku, J güncelle (`_hedef_temizle`), debug ölçümü.
2. KALKIŞ kapısı: `SEARCH_ALT`'a tırmanana kadar başka şey çalışmaz.
3. vismode/kilit seçimi; `durum==GORSEL_GUDUM` ise `_gorsel_guduum` → **return**
   (aşağıdaki GPS mekaniklerinin HİÇBİRİ görsel fazda çalışmaz).
4. **[GPS-YAKLAŞMA yolu]** None yönetimi (`HOLD_TICKS` tut / loiter) →
   standoff nişan noktası (`APPROACH_STANDOFF`, `APPROACH_ALT_OFFSET`,
   `APPROACH_LEAD_S`) → handoff histerezisi → PD (KP_H/KD_H) →
   speed_cap/FREN (`BRAKE_DIST`, `V_CAP_*`) → alçalma önceliği → dikey
   PID (`KP_Z/KI_Z/KD_Z`) → yaw → `_send` → uçuş logu.

## 4) Görsel güdüm çekirdeği — guidance/ibvs_gorsel.py (AvciIBVS)

**TEK FİKİR:** görüntünün orta noktasından bbox merkezine bir ÇİZGİ çek; güdüm bu
çizgiyi sıfıra sürer + sürekli ileri uçar (saf takip / pure pursuit).

```
ex = (cx − W/2) / (W/2)      −1..+1  (+ = hedef sağda)     [EMA: VIS_EMA]
ey = (cy − H/2) / (H/2)      −1..+1  (+ = hedef aşağıda)   [EMA: VIS_EMA]
büyüklük r = hypot(ex, ey)   (0 = merkez; merkeze sapma "mesafesi")
açı        = atan2(−ey, ex)  (0° = sağ, +90° = yukarı; telemetri/UI)

ey_ref= IBVS_DIKEY_NISAN · tan(IBVS_TILT_DEG)/tan(VFOV_yarı)   (tilt-farkında dikey nişan; ~0.43@25°)
eyy   = ey − ey_ref                                   (NİŞAN noktasına göre dikey sapma)
r     = hypot(ex, eyy)                                (nişandan sapma; 0 = hedef nişanda)
lead  = IBVS_SIGN_ROLL · IBVS_K_ROLL_LEAD · roll_f    (pose kanat uçlarından; kapı düşük→0)
yaw   = IBVS_SIGN_YAW  · IBVS_K_YAW  · ex  + lead      (clamp ±YAW_MAX)
thr   = IBVS_SIGN_DIKEY· IBVS_K_DIKEY· (−eyy) (clamp THR_DN..THR_UP; hedefi ey_ref'e sürer)
pitch = PITCH_SIGN · IBVS_ILERI · max(0, 1 − IBVS_MERKEZ_FREN·r)
roll  = 0   (bank YOK — çerçeveleme yaw'ın işi; eski PN'de bank hedefi
             kadrajdan atıp kamerayı yere çeviriyordu)
```

**TILT-FARKINDA DİKEY NİŞAN (v8+):** kamera +25° yukarı sabit → hedefi kadraj MERKEZİNDE tutmak
hız vektörünü hedefin 25° altına nişanlar (undershoot). `ey_ref` (tilt'ten türetilir) hedefi hız
vektörünün görüntüdeki yerine (FOE) çeker → "hedefte" = "burun hedefe kilitli". `IBVS_DIKEY_NISAN`:
0=merkez/altta-kal (gökyüzü), 1=hız-vektörü nişan (terminal çarpışma; default). ey_ref=0 → eski davranış.

**ÖNGÖRÜLÜ YAW LEAD (pose'dan hedef ROLL, v8):** hedefi ARKADAN takip ederken iki kanat
ucu pikselinden (poz["kp"][1]=sol, [2]=sağ) görüntü-uzayı bank açısı `roll_img =
atan2((v_sağ−v_sol)·H, (u_sağ−u_sol)·W)` (normalize kp W/H ile piksel-orana ölçeklenir).
Banklı uçak alçak kanadı yönüne döner → hedefin GİDECEĞİ yön yaw'a ileri-beslenir. Kapılar
(iki kanat conf ≥ `IBVS_ROLL_CONF_MIN`, `aspect_deg ≥ IBVS_ASPECT_MIN` [yalnız PnP çözülünce],
bayatlık ≤ `IBVS_POZ_STALE_S`) düşerse `lead=0` → saf IBVS. Roll PnP'ye BAĞIMLI DEĞİL
(2 keypoint yeter). İşaret VERİYLE (`SIGN_ROLL=−1`, `pose_ongoru_analiz.py` corr=−0.86). **Ego-motion
telafisi:** `roll_comp = roll_img − IBVS_EGO_ROLL_GAIN·own_roll` (kendi IMU roll'ü; kamera gövdeye
sabit → biz yatınca kirlenir). Detay: `guidance/ibvs_gorsel.kanat_roll_img`/`_roll_lead`.

- **⛔ Görsel fazda GPS/J YASAK (diskalifiye):** `hesapla(det, p, poz=None, own_roll_rad=None)` —
  det (bbox px) + poz (kamera keypoint) görsel; `own_roll_rad` = kendi IMU roll'ü (ego-motion
  telafisi, HEDEF konumu DEĞİL). GPS/J HEDEF kestirimi (son_temiz/son_hiz) ve drone_pos/v_own GİRMEZ.
  Kural (`tests/test_ibvs_gorsel.test_gps_siz_imza`: izinli set {det,p,poz,own_roll_rad} + yasak hedef-kinematik).
- **Alttan yaklaşma bedava:** kamera gövdeye +25° yukarı tilt'li; hedefi kadraj
  MERKEZİNDE tutmak = LOS'un ufka göre +25° olması = araç hedefin ALTINDA uçar
  (gökyüzü arka plan). Kapandıkça dikey ayrım R·sin25° ile kendiliğinden küçülür.
- **Menzil/kapanma kestirimi YOK:** vuruş, hedefi merkezde tutup ileri uçmanın
  doğal sonucu. VURUŞ latch'i (<3 m, truth/J-temiz) server `_gorev_izle`'de (güdüm
  değil, görev izleme).
- Durum: yalnız `ex_f/ey_f` EMA'sı. Kaynak/vismode değişiminde `sifirla()`.

## 5) Cfg sözlüğü (faz etiketiyle; ⚙ = arayüz slider'ında)

**[ORTAK]** `ROT_IN_DEGREES, PITCH/ROLL/YAW/Z_SIGN, LOOP_HZ, DT, PITCH/ROLL_MAX,
THR_UP/THR_DN, YAW_MAX⚙, MAX_DELTA, DERIV_EMA, POS/YAW_DEADBAND, DEBUG_Z,
LOG_ENABLE`

**[GPS-YAKLAŞMA]** `SEARCH_ALT, TAKEOFF, ALT_TOL, TAKEOFF_THR, HANDOFF_RANGE,
HANDOFF_EXIT, AUTO_VISUAL_HANDOFF, V_CAP_FAR, V_CAP_NEAR, BRAKE_DIST,
APPROACH_STANDOFF, APPROACH_LEAD_S, APPROACH_ALT_OFFSET, LOOKUP_ELEV_DEG,
LOOKUP_MIN_ALT_CM, KP_H, KD_H, KP_Z, KI_Z, KD_Z, INT_Z_BAND, INT_Z_MAX,
KP_YAW, HOLD_TICKS` (LOOKUP_* yalnız GPS dikey nişanında yaşıyor — görsel fazda
karşılığı yok artık)

**[GÖRSEL — tespit/kayıp]** `VIS_MODEL_PATH, VIS_POSE_MODEL_PATH, PROP_MASKE, VIS_CONF_MIN⚙,
VIS_N_LOCK, VIS_STALE_S, VIS_LOST_TO_GPS_S⚙, VIS_EMA⚙`

**[GÖRSEL — BASİT IBVS]** `IBVS_K_YAW⚙, IBVS_SIGN_YAW, IBVS_K_DIKEY⚙,
IBVS_SIGN_DIKEY, IBVS_ILERI⚙, IBVS_MERKEZ_FREN⚙, IBVS_DIKEY_NISAN⚙ (0=merkez/altta-kal,
1=hız-vektörü nişan), IBVS_TILT_DEG=25, IBVS_VFOV_HALF_DEG=47.2`

**[GÖRSEL — ÖNGÖRÜLÜ YAW LEAD (pose hedef roll)]** `IBVS_K_ROLL_LEAD⚙, IBVS_SIGN_ROLL=−1
(veriyle), IBVS_ROLL_CONF_MIN⚙, IBVS_ROLL_EMA, IBVS_ASPECT_MIN, IBVS_POZ_STALE_S,
IBVS_EGO_ROLL_GAIN (ego-motion telafisi; araclar/pose_ongoru_analiz ego A/B ile doğrula)`

**[GÖRSEL — KİLİTLENME İSTERİ (salt gözlem)]** `VIS_LOCK_PCT (0.06; şartname
≥0.05, tavsiye 0.06), VIS_AV_X/VIS_AV_Y (0.25/0.10 şartname sabiti),
VIS_WIN_S/VIS_WIN_NEED_S (10/5 sn şartname sabiti)`

## 6) GÖRSEL TUNE MODU (prosedür)

Kaynak=GERÇEK + vismode=GORSEL → GPS mekanikleri tamamen devre dışı, saf IBVS.
8 slider (arayüz [GÖRSEL GÜDÜM · BASİT IBVS]): sırayla `IBVS_ILERI` →
`IBVS_K_YAW` → `IBVS_K_DIKEY` → `IBVS_MERKEZ_FREN`; tek koşuda TEK parametre.
Belirti→knob tablosu: `TUNE_REHBERI.md` başı. İşaret şüphesinde: yaw ters
dönüyorsa `IBVS_SIGN_YAW=-1`, dikey ters tepkiyse `IBVS_SIGN_DIKEY=-1`
(Cfg'den; panelde değil — bir kez doğrulanır, bir daha ellenmez).

## 7) Bilinen gerilimler / dikkat noktaları

- **Kilit isteri vs sürekli kapanma:** IBVS hep ileri uçar; 5/10 sn kilit
  penceresi dolmadan hedefe varılabilir. Şartname akışını videoda göstermek
  için `IBVS_ILERI`'yi pencere dolacak kadar yavaş tut (veya handoff'u uzaktan
  başlat). Eski "TAKIP menzil tutma" katmanı bilinçli silindi — gerekirse git'te.
- **`APPROACH_ALT_OFFSET` + `LOOKUP_ELEV_DEG`** yalnız GPS dikey nişanını şekillendirir
  (handoff'ta araç hedefin altında başlar). Görsel fazda dikey tamamen `ey`'den.
- **Fren/speed_cap** görsel faza karışmaz ama handoff HIZINI belirler.
- **İleri itki ↔ dikey bağlaşımı:** pitch öne eğim kamerayı aşağı çevirir →
  hedef kadrajda yukarı kayar → thr tırmanır. Küçük bağlaşım; kazançlar tolere
  eder, sertleşirse `IBVS_ILERI` düşür.
- Uçuş logundaki eski kolonlar (`d_s, v_close, png_R_m, png_Vc, png_omega,
  vis_faz`) şema uyumu için durur, hep boş yazılır. Yeni: `ibvs_r, ibvs_aci`.

## 8) Log ve analiz araçları

- `veri/ucus_log_*.csv` — beyin her tik yazar (`Cfg.LOG_ENABLE`). Görsel satırlar
  `phase=VISUAL`; `vis_ex/vis_ey/vis_conf/vis_area/kilit_win_s/ibvs_r/ibvs_aci` dolu.
- `araclar/gorsel_episode_analiz.py` — eski PN kolonlarını (png_R_m vs.) okuyan
  bölümleri artık boş görür; ex/ey/kapsama analizi hâlâ geçerli.
- `arac/analiz_ucus.py` — GPS yaklaşma/salınım/temas analizi (eski kolonlarla uyumlu).

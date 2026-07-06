# GÜDÜM HARİTASI — hangi kod ne işe yarıyor (takım anlatımı / kural 8)

> 2026-07-06 temizliği sonrası günceldir. Silinenler: IBVS yasası
> (`ibvs_guidance.py`), GPS terminal vuruş (strike/ram) bloğu, `_kamera_kontrol`
> stub'ı, `calistir()`, `ozet()`. Hepsi git geçmişinde durur.

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
  │  Görsel faz  : _gorsel_guduum → guidance/png_gorsel.py (PN çarpışma rotası)
  ▼
_send(thr, pitch, roll, yaw) → rate-limit → drone.set_control_surfaces

GÖRSEL TESPİT (ayrı thread, server.py dedektor_dongusu):
  windows-capture pencere karesi → detection/gorsel_tespit.py (best.pt, YOLO)
  → conf≥VIS_CONF_MIN ise beyin.set_gorsel_tespit(det)   [güdüm kapısı]
  → conf≥0.25 zayıf tespitler yalnız ARAYÜZE (turuncu kutu)
```

## 2) FSM (self.durum)

| Durum | Anlamı | Giriş koşulu | Çıkış |
|---|---|---|---|
| `ARAMA` | GPS yaklaşma, hedef uzak | başlangıç / handoff kaybı | d_h < `HANDOFF_RANGE` → KILIT |
| `KILIT` | GPS yaklaşma + görsel devir hazır | handoff histerezisi | görsel kilit → GORSEL_GUDUM; d_h > `HANDOFF_EXIT` → ARAMA |
| `GORSEL_GUDUM` | yönelim YALNIZ kameradan (PNG) | OTO: `AUTO_VISUAL_HANDOFF` + ard arda `VIS_N_LOCK` tespit + handoff; MANUEL: vismode=GORSEL | kayıp > `VIS_STALE_S`+`VIS_LOST_TO_GPS_S` (yalnız OTO) → ARAMA |

vismode anahtarı (arayüz OTO/GPS/GORSEL): GPS = görsel yol kapalı; GORSEL =
kilit sayacı atlanır, kayıpta GPS'e dönmez (tune modu); OTO = otomatik zincir.

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

## 4) Görsel güdüm çekirdeği — guidance/png_gorsel.py (AvciPNGGuduum)

bbox → LOS birim vektörü (`piksel_to_los`, kamera 25° tilt dahil) → pinhole
menzil (`VIS_SPAN_CM` kanat açıklığından) → EMA'lı R/Vc/Omega → PN ivmesi
`a = N·Vc·(Ω×u)` + LOS-boyu kapanma → gövde komutları. Kayıpta `kor_devam`
(LOS'u son Omega ile ilerlet). Menzil geçersizken J'den yalnız BÜYÜKLÜK
(`_j_fallback`; yön asla GPS'ten gelmez — yarışma kuralı).

**Tune öncelik sırası (arayüz GÖRSEL GÜDÜM — PNG slider'ları):**
1. `VIS_KP_CLOSE` — kapanma hızı talebi (ıskalıyorsa İLK bunu düşür)
2. `VIS_PN_N` — navigasyon sabiti (3-5)
3. `VIS_PN_TILT` — manevra yetkisi
4. `VIS_TAU_Z` — dikey ataklık
Ölçüm: her koşudan sonra `python araclar/gorsel_episode_analiz.py` → minR medyanı.

## 5) Cfg sözlüğü (faz etiketiyle; ⚙ = arayüz slider'ında)

**[ORTAK]** `ROT_IN_DEGREES, PITCH/ROLL/YAW/Z_SIGN, LOOP_HZ, DT, PITCH/ROLL_MAX,
THR_UP⚙/THR_DN⚙, YAW_MAX⚙, MAX_DELTA⚙, DERIV_EMA, POS/YAW_DEADBAND, DEBUG_Z,
LOG_ENABLE`

**[GPS-YAKLAŞMA]** `SEARCH_ALT, TAKEOFF, ALT_TOL, TAKEOFF_THR, HANDOFF_RANGE,
HANDOFF_EXIT, AUTO_VISUAL_HANDOFF, V_CAP_FAR⚙, V_CAP_NEAR⚙, BRAKE_DIST⚙,
APPROACH_STANDOFF, APPROACH_LEAD_S, APPROACH_ALT_OFFSET, KP_H⚙, KD_H⚙,
KP_Z⚙, KI_Z⚙, KD_Z⚙, INT_Z_BAND, INT_Z_MAX, KP_YAW⚙, HOLD_TICKS`

**[GÖRSEL]** `VIS_MODEL_PATH, VIS_CONF_MIN⚙, VIS_N_LOCK, VIS_STALE_S,
VIS_DEADRECKON_S, VIS_LOST_TO_GPS_S, VIS_EMA⚙, VIS_EY_REF⚙(yalnız UI çizgisi),
VIS_TILT_DEG⚙, VIS_SIGN_YAW⚙, VIS_K_YAW⚙, VIS_LAW(="PNG" bilgi), VIS_PN_N⚙,
VIS_PN_A_MAX, VIS_PN_TILT⚙, VZ_MAX, VIS_SPAN_CM, VIS_R/VC/OMEGA_EMA,
VIS_OMEGA_MAX, VIS_R_MIN/MAX, VIS_W_PX_MIN, VIS_VC_CAP, VIS_VC_MIN,
VIS_KP_CLOSE⚙, VIS_KV_CLOSE, VIS_COMMIT_R, VIS_COMMIT_LAT, VIS_TAU_Z⚙,
VIS_PN_SIGN_VZ, VIS_PN_FALLBACK_J`

## 6) GÖRSEL TUNE MODU (prosedür)

Ayrıntı: `TUNE_REHBERI.md` bölüm 9. Özet: kaynak=GERÇEK + vismode=GORSEL →
GPS mekanikleri tamamen devre dışı, saf PNG; her koşu sonrası
`araclar/gorsel_episode_analiz.py`; tek koşuda TEK parametre.

## 7) Bilinen gerilimler / dikkat noktaları

- **`APPROACH_ALT_OFFSET` ↔ handoff geometrisi:** GPS fazı kadraj için hedefin
  5 m altında uçar → görsel faz ~5-8 m dikey açıkla başlar; PNG bunu endgame'de
  kapatmak zorunda (6 Tem log analizi). Küçültme kadrajı bozabilir.
- **`VIS_EY_REF`** güdüme girmez; yalnız FPV'deki turuncu REF çizgisi.
- **Fren/speed_cap** görsel faza karışmaz ama handoff HIZINI belirler.
- **PNG commit-freeze** (`png_gorsel._komut`): R<3 m'de son komut dondurulur
  (saf dalış) — bilinçli; sıfırlama `sifirla()` ile.
- Uçuş logundaki eski strike kolonları (`d_s, v_close, vdx...`) şema uyumu
  için durur, hep boş yazılır.

## 8) Log ve analiz araçları

- `veri/ucus_log_*.csv` — beyin her tik yazar (`Cfg.LOG_ENABLE`). Görsel satırlar
  `phase=VISUAL`; `vis_ex/vis_ey/vis_conf/png_R_m/png_Vc/png_omega` dolu.
- `araclar/gorsel_episode_analiz.py` — görsel bölüm analizi (minR, dikey/yatay
  ıskalama bileşeni, kapsama, satürasyon). Tune döngüsünün ana aracı.
- `arac/analiz_ucus.py` — GPS yaklaşma/salınım/temas analizi (eski kolonlarla uyumlu).

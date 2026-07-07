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

**Kayıp yönetimi + YAKIN-MENZİL YAPIŞKANLIĞI (7 Tem):** tespit kopunca kademeli
kör-devam → hover → GPS revert. `pngg.R_f < VIS_STICKY_R` (10 m) iken **yakın eşikler**
kullanılır (`VIS_DEADRECKON_S_NEAR`=1.5, `VIS_LOST_TO_GPS_S_NEAR`=3.0) → kilit menzilinde
kısa tespit blip'inde GPS'e dönüp kapanma ilerlemesini çöpe atmaz, kilit dolabilir. Uzakta
eski (kısa) eşikler → hızlı re-acquire. (Log kanıtı: araç 5.1 m'ye varıp tam orada tespit
koptu diye revert ediyordu, kilit dolamadan.)

**Görsel alt-FSM (`self.gorsel_faz`, 2026-07-07 — şartname 6.1.2/6.1.4 kilit isteri):**

| Alt-faz | Davranış | Geçiş |
|---|---|---|
| `YAKLASMA` | mevcut PNG kapanma (ama commit-freeze KAPALI) | bbox ekseni ≥ `VIS_LOCK_PCT` → TAKIP |
| `TAKIP` | PN yanal (merkezde tut) + MENZİL TUTMA (R→R_hold, bbox≈`VIS_HOLD_PCT`) **NAZİK yaklaşma `VIS_TAKIP_VC`~3 m/s** (dalıp kaçırmaz); kilit penceresi sayılır | 10 sn pencerede kümülatif ≥ 5 sn kilit (`kilit_ok` latch) → TERMINAL |
| `TERMINAL` | tam PNG kapanma + commit-freeze (vuruş) — eski davranışın aynısı | geri dönüş yok (görev/kaynak/vismode reset hariç) |

Kilit koşulu (`_kilit_degerlendir`, her görsel tik): hedef merkezi **Hedef Vuruş
Alanı** içinde (yatay %25–75, dikey %10–90 = `VIS_AV_X/Y`) VE bbox **en az bir
eksende** ≥ `VIS_LOCK_PCT`. Kesintili kilit sayılır (şartname örneği 1+2+2=5 sn).
GORSEL→ARAMA düşüşünde alt-faz YAKLASMA'ya döner, pencere temizlenir; `kilit_ok`
latch'i KORUNUR (yeniden TAKIP'e girince pencere dolmadan TERMINAL'e geçilir).
`vurus_izin = (gorsel_faz == "TERMINAL")` png_gorsel'e geçirilir.

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
(LOS'u son Omega ile ilerlet). **⛔ Görsel fazda GPS/J YASAK** (diskalifiye): yön, menzil,
kapanma, dikey ayrım hepsi bbox/LOS'tan. Menzil geçersizken eski görsel R_f korunur
(GPS'e başvurulmaz; `_j_fallback` 7 Tem kaldırıldı). Dikey ayrım `dh=R·u_hat[2]` (görsel).

`vurus_izin=False` (YAKLASMA/TAKIP alt-fazları): commit-freeze ve Vc≤0 itişi
KAPALI; kapanma kanalı `v_close_des = clamp(KP·(R−R_hold), ±VC_CAP)` menzil
tutar (`R_hold = fx(1)·SPAN/VIS_HOLD_PCT` ≈ 5.6 m @0.08 — pinhole tersinden,
yeni sihirli sabit yok). `vurus_izin=True` (TERMINAL) = eski davranış bit-bit.

**Yaw (kamera nişanı):** `yaw = SIGN·K_YAW·ex_f + SIGN·K_YAW_LEAD·omega_z`. P terimi
anlık hatayı kapatır; **LEAD terimi** (LOS azimut hızı = omega dünya-Z bileşeni) hareketli
hedefi geriden kovalamayı önler (7 Tem canlı log: ex_ort +0.49, kayıpların %100'ü hedef
kenarda; sim: lead ile ort |ex| 0.79→0.31). Doygunlukta `YAW_MAX` yükselt.

**Roll/pitch (manevra) — AYRI yetki (7 Tem):** takipte **ROLL** (bank) `VIS_TRACK_TILT` (0.30)
ile kısılır (savrulma/clutter: bank max 47° hedefi kadrajdan atıp kamerayı yere çeviriyordu);
**PITCH** (ileri/KAPANMA) ise HER ZAMAN tam `VIS_PN_TILT` (0.8) → araç yaklaşabilir. (Tek-tilt
kısısı hem bank'i hem ileri-eğimi kısıp yaklaşmayı öldürüyordu — `VIS_TAKIP_VC` etkisizdi çünkü
pitch tilt'te doyuyordu.) Yaklaşma HIZINI `VIS_TAKIP_VC` belirler; bank yine sınırlı (gökyüzü
arka plan). TERMINAL'de ikisi de tam. Çerçeveleme roll'da DEĞİL yaw'da. Handoff'ta soft-start kısar.

**Tune öncelik sırası (arayüz GÖRSEL GÜDÜM — PNG slider'ları):**
1. `VIS_KP_CLOSE` — kapanma hızı talebi (ıskalıyorsa İLK bunu düşür)
2. `VIS_PN_N` — navigasyon sabiti (3-5)
3. `VIS_PN_TILT` — manevra yetkisi
4. `VIS_TAU_Z` — dikey ataklık
5. `VIS_K_YAW_LEAD` — öngörülü yaw (hedef geriden kalıyorsa artır; önünü aşıyorsa düşür)
Ölçüm: her koşudan sonra `python araclar/gorsel_episode_analiz.py` → minR medyanı.

> **TUNE PANELİ (2026-07-07 genişletildi):** artık [GÖRSEL] çekirdek katsayıların TAMAMI
> (VIS_KV_CLOSE, VIS_OMEGA_MAX, R/VC/OMEGA_EMA, VIS_COMMIT_R/LAT, VIS_PN_SIGN_VZ,
> VIS_TILT_DEG, LOOKUP_MIN_ALT_CM) + kilit/kayıp FSM zamanlamaları (VIS_N_LOCK,
> VIS_STALE_S, VIS_DEADRECKON_S, VIS_LOST_TO_GPS_S, VIS_STICKY_R + _NEAR) + GPS PD
> kazançları (KP_H/KD_H/KP_Z/KI_Z/KD_Z/THR_UP/THR_DN) canlı slider'da (48 parametre).
> Cfg↔`server.py` TUNE_ALLOW↔`index.html` TUNE_DEFS senkron; POST `float(value)`,
> guduum her tik Cfg'den okur → anında etki. Yeni tunable eklerken ÜÇÜNÜ birden düzenle.

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
VIS_PN_SIGN_VZ` (VIS_PN_FALLBACK_J 7 Tem kaldırıldı — görsel fazda GPS/J yasak)

**[GÖRSEL — KİLİTLENME İSTERİ]** `VIS_LOCK_PCT⚙ (0.06; şartname ≥0.05, tavsiye
0.06), VIS_HOLD_PCT⚙ (0.08 takip mesafe bandı), VIS_AV_X/VIS_AV_Y (0.25/0.10
şartname sabiti), VIS_WIN_S/VIS_WIN_NEED_S (10/5 sn şartname sabiti)`

**[LOOK-UP]** `LOOKUP_ELEV_DEG⚙ (8° ε; GPS+görsel ortak, 0=kapalı),
LOOKUP_MIN_ALT_CM (800 taban), VIS_LOOKUP_VZ⚙ (500 cm/s görsel alçalma tavanı)`

## 6) GÖRSEL TUNE MODU (prosedür)

Ayrıntı: `TUNE_REHBERI.md` bölüm 9. Özet: kaynak=GERÇEK + vismode=GORSEL →
GPS mekanikleri tamamen devre dışı, saf PNG; her koşu sonrası
`araclar/gorsel_episode_analiz.py`; tek koşuda TEK parametre.

## 6.5) LOOK-UP GEOMETRİSİ (aşağı-bakma/clutter çözümü, 2026-07-07)

**Problem:** avcı hedefin ÜSTÜNDEN takip edince kamera aşağı bakar → hedef arazi
dokusu (clutter) önünde düşük kontrast → YOLO tespiti kopar. ALTTAN bakışta arka
plan GÖKYÜZÜ (siluet, yüksek kontrast) + planform izdüşümü maksimum. **Kısıt:**
avcıdan hedefe LOS yükseliş açısı her an ≥ `LOOKUP_ELEV_DEG` (ε≈8°). Sabit Δh
YETMEZ (aynı Δh uzak menzilde küçük açı) → **menzil-ölçekli**:

- **GPS fazı** (`ana_kontrol.adim`): `z_ref = z_hedef − max(APPROACH_ALT_OFFSET,
  tan(ε)·d_h)`, taban `LOOKUP_MIN_ALT_CM`'e clamp (yere çakılma). Açı ≥ ε garanti.
- **Görsel faz** (`png_gorsel._komut`): `u_hat[2] = sin(elev)`. **ÇİFT-YÖNLÜ dikey
  konum tutma** (setpoint = ε): `elev < ε` → alçal (siluet); `elev > ε` → **TIRMAN**
  (aşırı alçalıp hedefi üst kenardan kaçırmayı önler = **dikey merkezleme**). Tek
  terim hem look-up hem dikey çerçeveyi sağlar. ±5° bandında doğrusal, `VIS_LOOKUP_VZ`
  tavanında doyar. YALNIZ TAKIP/YAKLAŞMA; TERMINAL saf PN. Taban altında alçalma
  dayatılmaz (tırmanışa izin). Kapalı-döngü: elev=0'dan ε'ye yakınsar, kararlı kalır
  (7 Tem: v1 tek-yön bias hedefi üst kenara atıyordu, ey_ort −0.19 → v2 çift-yönlü).
- Telemetri: `png_tlm.elev_deg/lookup_ok` + `gorsel.lookup`; UI PN kartında "LOS
  yükseliş" satırı (+ = üstte/gökyüzü ✓, eşik altı = ⬇ alçalıyor). Slider:
  `LOOKUP_ELEV_DEG` (0=kapalı), `VIS_LOOKUP_VZ`. Testler: `tests/test_lookup_geometri.py`.

## 7) Bilinen gerilimler / dikkat noktaları

- **`APPROACH_ALT_OFFSET` artık ASGARI ofset:** GPS dikey nişan `max(APPROACH_ALT_OFFSET,
  tan(ε)·d_h)` ile menzil-ölçeklidir (look-up, §6.5). ε=0 yaparsan eski sabit-5m
  davranışına döner. Taban `LOOKUP_MIN_ALT_CM` hedef çok alçaksa açıyı fiziksel sınırlar.
- **`VIS_EY_REF`** güdüme girmez; yalnız FPV'deki turuncu REF çizgisi.
- **Fren/speed_cap** görsel faza karışmaz ama handoff HIZINI belirler.
- **PNG commit-freeze** (`png_gorsel._komut`): R<3 m'de son komut dondurulur
  (saf dalış) — bilinçli; sıfırlama `sifirla()` ile. YALNIZ TERMINAL alt-fazında
  (`vurus_izin=True`); kilit isteri dolmadan asla dalmaz (şartname 6.1.4).
- Uçuş logundaki eski strike kolonları (`d_s, v_close, vdx...`) şema uyumu
  için durur, hep boş yazılır.

## 8) Log ve analiz araçları

- `veri/ucus_log_*.csv` — beyin her tik yazar (`Cfg.LOG_ENABLE`). Görsel satırlar
  `phase=VISUAL`; `vis_ex/vis_ey/vis_conf/png_R_m/png_Vc/png_omega` dolu.
- `araclar/gorsel_episode_analiz.py` — görsel bölüm analizi (minR, dikey/yatay
  ıskalama bileşeni, kapsama, satürasyon). Tune döngüsünün ana aracı.
- `arac/analiz_ucus.py` — GPS yaklaşma/salınım/temas analizi (eski kolonlarla uyumlu).

# GÖRSEL GÜDÜM — HIZLI AYAR REHBERİ (2026-07-07, sade panel)

> Arayüzdeki tune paneli 12 knob'a indirildi (yapısal sabitler Cfg'de kaldı). Aşağıdaki
> **belirti → çözüm** tablosuna göre ayarla. **ALTIN KURAL: tek seferde TEK slider değiştir,
> bir görev uç, `python araclar/gorsel_episode_analiz.py` ile ölç, karşılaştır.** Panel canlı
> (restart yok). Sıra = önce ANA grup (★ çok etkili), yetmezse İNCE AYAR.

**Etki büyüklüğü:** ★★★ davranışı kökten değiştirir · ★★ belirgin · ★ ince.

| Belirti (videoda/logda gördüğün) | Knob | Yön | Etki |
|---|---|---|---|
| Görsel faza geçince araç **sert yatıyor/savruluyor** (bank), kamera yere bakıp clutter | `VIS_TRACK_TILT` | **DÜŞÜR** (yalnız ROLL; ileri hızı ETKİLEMEZ) | ★★★ |
| **Çok yavaş / hiç yaklaşamıyor** | `VIS_TAKIP_VC` | **ARTIR** (asıl hız knob'u; pitch tam yetkili — tilt'e takılmaz) | ★★★ |
| **Kilit menziline varıp** tam orada hedefi kaçırıyor / kilit dolmuyor | `VIS_TAKIP_VC` | **DÜŞÜR** | ★★★ |
| Hedef **yatayda** (sağ/sol kenar) geride kalıyor, kamera kovalıyor | `VIS_K_YAW_LEAD` | **ARTIR** (0.30→0.45) | ★★ |
| Yatay hâlâ kaçıyor + yaw doygunlukta | `YAW_MAX` sonra `VIS_K_YAW` | **ARTIR** | ★ |
| Araç hedefin **ÜSTÜNE çıkıyor** → arka plan zemin → tespit kopuyor | `VIS_DH_TARGET` | **ARTIR** (400→550) = daha altta uç | ★★ |
| Araç çok altta, hedef üst kenardan kaçıyor | `VIS_DH_TARGET` | **DÜŞÜR** | ★★ |
| Dikeyde sert/salınım/titreme | `VIS_DH_BAND` **ARTIR** veya `VIS_LOOKUP_VZ` **DÜŞÜR** | | ★ |
| Geçiş anında hâlâ sert manevra ("masayı deviriyor") | `VIS_SOFTSTART_S` | **ARTIR** (1.5→2.5) | ★★ |
| Genel **titreşim/salınım** (sarkaç gibi) | `VIS_PN_N` sonra `VIS_K_YAW` | **DÜŞÜR** | ★ |
| Iskalıyor (hedefi geçiyor) | `VIS_KP_CLOSE` | **DÜŞÜR** | ★ |
| Geç kilit / yanlış tespit | `VIS_CONF_MIN` | yanlış çoksa ARTIR / geç ise DÜŞÜR | ★ |
| Takipte fazla uzak/yakın park ediyor | `VIS_HOLD_PCT` | yakın için ARTIR | ★ |

**DİKEY = HEDEF ALTINDA SABİT MESAFE (7 Tem v4):** dikey artık kadraj pozisyonu değil, **dünya
dikey ayrımı** ile kontrol edilir — araç hedefin irtifasından `VIS_DH_TARGET` (cm) kadar ALTTA
tutulur. (Kadraj-çizgisi = sabit AÇI idi; kapanınca dünya-ayrımı küçülüp araç hedefin üstüne
çıkıyordu → zemin arka plan → tespit kopuyordu.) Artık kapandıkça araç HEP altta kalır, hedef
kadrajda yukarı kayar (alttan yaklaşma), gökyüzü arka plan korunur, TERMINAL'de alttan vuruş.
FPV'de **"HEDEF ALTINDA: X.X m"** göstergesi (+ = altta iyi; ≤0 = üste çıkıyor uyarısı). İrtifa
J kestiriminden (magnitude; yön kameradan). `VIS_DH_BAND` = mesafede ne kadar sıkı tutulacağı.

**Tipik ayarlama akışı:** (1) `VIS_TRACK_TILT` ile savrulmayı kes → (2) `VIS_TAKIP_VC` ile
kilit menzilinde nazik park → (3) `VIS_K_YAW_LEAD` (yatay) + `VIS_DH_TARGET` (dikey altta-kal) ile
hedefi çerçevele → (4) `VIS_SOFTSTART_S` ile geçişi yumuşat. Kilit penceresi (5/10 sn) dolup
TERMINAL/vuruş açılana kadar tekrarla. Panelden çıkarılan sabitler (filtre EMA'ları, işaretler,
FSM zamanlamaları, GPS PD, GPS handoff açısı `LOOKUP_ELEV_DEG`) nadiren gerekir —
gerekirse `guidance/ana_kontrol.py` Cfg'den.

---

# GPS GÜDÜM TUNE REHBERİ — "kontrollü yaklaş, hep bak, tekte vur"

> Amaç: hedef araca **kontrollü** yaklaşmak, kamerayı **her an hedefte** tutmak
> (GPS fazının başarı kriteri = kesintisiz görsel temas) ve terminalde **tek
> geçişte** vurmak. Bu rehber koddaki güncel duruma birebir uyumludur
> (terminal-yaw düzeltmesi uygulandı; tüm GPS parametreleri canlı slider'da).

---

## 1) Kamera geometrisi — görsel temasın fiziği (FOV 125° = YATAY, teyitli)

| Büyüklük | Değer | Pratik anlamı |
|---|---|---|
| Yatay FOV | 125° (yarım **62.5°**) | Burun sapması ±62.5° içinde hedef karede; YOLO'nun rahat tespiti için **±30°** içinde tut |
| Dikey FOV | ~94.5° (yarım **47.2°**) | 16:9'dan türetilir |
| Kamera ekseni | **+25° yukarı** | Dikey görüş bandı ufka göre **−22° … +72°** |

**İki altın kural:**
1. **Hedefin ÜSTÜNDE durma.** Kamera aşağıya en fazla ~22° görür: 20 m yatay
   mesafede hedefin 8 m üzerindeysen hedef karenin altından çıkar. Altında olmak
   çok toleranslı (+72°'ye kadar).
2. **İleri eğim kamerayı aşağı çevirir.** Gövde öne θ° yatınca kamera ekseni
   25−θ olur; ~25° eğimde kamera tam ileri bakar. FPV'de "hızlanınca hedef
   yukarı kaçıyor" görüyorsan eğim (hız isteği) görsel teması yiyor demektir →
   `STRIKE_TILT` / hız tavanlarını düşür. (`STRIKE_TILT≈0.45` bandı tilt
   telafisiyle uyumludur.)

---

## 2) Sistem zinciri — belirti hangi katmandan gelir

Her tikte (50 Hz): İnovasyonlu J kestirimi (yatay=2sn lead, dikey=anlık, hedef hızı) →
- `d > STRIKE_RANGE`: **YAKLAŞMA** — PD (`KP_H/KD_H`) + hız tavanı
  (`V_CAP_FAR→V_CAP_NEAR`, `BRAKE_DIST`; tavan aşımında pitch %80'e kadar kesilir).
  Burun lead noktasına bakar (uzakta doğru olan).
- `d ≤ STRIKE_RANGE`: **TERMİNAL** — çarpışma rotası `v_istenen = v_hedef +
  v_close·LOS`; `v_close = clamp(KP_CLOSE·d, V_CLOSE_MIN, V_CLOSE)`; ivme =
  `KV_STRIKE·(hız hatası)`, yetki `STRIKE_TILT`; `d < COMMIT_RANGE`'te yanal ivme
  kısılır (düz dalış); dikeye kapanış feedforward'u eklenir. **Burun ANLIK hedefe
  döner** (kamera kilidi — kod düzeltmesi uygulandı).
- **Dikey**: PID (`KP_Z/KI_Z/KD_Z`, tavanlar `THR_UP/THR_DN`).
- **Yaw**: `KP_YAW` kazanç, `YAW_MAX` tavan, ±3° ölü bant.
- **`MAX_DELTA`**: tik başına maksimum komut değişimi — **dört eksene ortak!**

### Belirti → ilk müdahale
| Belirti | Oynanacak düğme(ler) |
|---|---|
| Kamera hedefte durmuyor (yatay) | `YAW_MAX` ↑, sonra `KP_YAW`; son metrede `COMMIT_RANGE` ↑ |
| Hedef karede YUKARI kaçıyor | `STRIKE_TILT` ↓, hız tavanları ↓ (eğim fazla) |
| Hedef karede AŞAĞI kaçıp kayboluyor | Hedefin üstündesin → irtifa stratejisi (Aşama 2) |
| Yanından geçip savruluyor | `BRAKE_DIST` ↑, `V_CAP_NEAR` ↓ |
| Son metrede sekiyor / geri atılıyor | `V_CLOSE_MIN` ↑ |
| Son metrede çılgınca dönüyor | `COMMIT_RANGE` ↑ |
| Her şey titrek / testere dişi | `MAX_DELTA` ↓, `KV_STRIKE` ↓ |
| Yumuşak ama hantal, hedefe yetişemiyor | `MAX_DELTA` ↑ (küçük adım), `KV_STRIKE` ↑ |

---

## 3) Test protokolü — her koşu böyle yapılır

1. **Tek değişiklik** yap (slider). İki parametre birden asla.
2. Görevi başlat; vuruş/ıskalamayı sonuna kadar izle; durdur.
3. Repo kökünden **`python arac\analiz_ucus.py`** → en yeni logu analiz eder,
   konsola 3 teşhis basar (geri-çekilme / salınım / FOV kaybı) ve
   **`veri\ucus_metrikler.csv`'ye satır ekler** (koşuları Excel'de kıyasla).
4. **Koşu defteri** tut: log zamanı + o koşunun değerleri (📋 Değerleri Yazdır
   çıktısını yapıştır). Bu olmadan metrik tablosu anlamsız.
5. İyi seti **📋 Değerleri Yazdır → Cfg'ye yapıştır** (slider restart'ta sıfırlanır!).

### Metrik hedefleri (kabul çizgisi)
| Metrik | Hedef | Anlamı |
|---|---|---|
| `FOV_kayip_s` | **0.0 sn (0 olay)** | Görsel temas hiç kopmadı — **fazın başarı kriteri** |
| `min_menzil` | < 0.7 m | Vuruş (oyun vuruşta hedefi respawn eder; mesafe aniden fırlar = kanıt) |
| `bounce` | **0** | Tek geçiş; geri atılma yok |
| `roll_salinim` | < ~1 Hz | Testere yok |
| `roll_sat` / `yaw_sat` | < %30-40 | Komut tavana yapışmıyor |
| `max_LOS` | temas anı hariç < birkaç yüz °/s | Son metre kontrollü |

### İki kaynaklı strateji (önemli)
- Önce **"Gerçek GPS (test)"** ile tune: filtresiz, güdümün tavanı; neden-sonuç net.
- Sonra **İnovasyonlu J** ile doğrula: bozulmalar koşudan koşuya değişir
  (v0.0.5: hedef GPS nominal **5 Hz**; 30. sn'den sonra her 10 sn'de ~2 sn kesinti
  + gecikme/gürültü görülebilir) → **3-5 koşu**, ortalamaya bak.
- Gerçek-GPS'te iyi ama J'de kötüyse sorun toleranstır → sertleştirme;
  `COMMIT_RANGE` ↑ / `STRIKE_RANGE` ↑ (erken hız-eşleme) dene.

**Canlı gözlem:** FPV'de hedefin yeri (yatay merkez, dikeyde REF çizgisi civarı);
konsol `[Z]` satırı (ez=dikey hata, thr, spd); telemetri GERÇEK mesafe.

---

## 4) Parametre sözlüğü

Nerede: **S** = slider · **A** = canlı API (slider yok; Cfg'den de olur) · **C** = Cfg + restart.

### Terminal vuruş
| Param | Vars. | Ne yapar / nasıl ayarlanır |
|---|---|---|
| `V_CLOSE_MIN` S | 700 | Kapanış TABANI (ram). Sekme/bounce varsa artır (850→1000). Aşırısı gereksiz sertlik |
| `KV_STRIKE` S | 2.5 | Hız-izleme kazancı. Titrekse azalt (0.25'lik adım), hedef manevrasına geç kalıyorsa artır |
| `STRIKE_TILT` S | 0.8 | Terminal eğim yetkisi. **Görsel temas maliyeti var** (bkz. §1). 0.45 civarı başla |
| `COMMIT_RANGE` S | 500 | Bu mesafede yanal kovalamayı kes, düz dal. Son metre dönüşü/salınımı varsa artır |
| `V_CLOSE` S | 1200 | Kapanış TAVANI (uzakta dalış hızı) |
| `KP_CLOSE` S | 0.6 | Kapanış hızı/mesafe oranı |
| `STRIKE_RANGE` S | 6000 | Terminale giriş (cm). Artır = erken hız-eşleme, stabil kovalama |

### Görsel temas / yaw
| Param | Vars. | Ne yapar |
|---|---|---|
| `YAW_MAX` S | 0.30 | Burun dönüş hızı tavanı. `yaw_sat` yüksek + dönüşlerde FOV kaybı → 0.05'lik adımlarla artır (0.45'e kadar). Salınırsa geri |
| `KP_YAW` S | 1.0 | Yaw kazancı. Burun tembelse artır; sağlı-sollu vuruyorsa 0.7'ye in |
| `YAW_DEADBAND` C | 3° | Dokunma (jitter önler; ±3° gezinme normal) |

### Yaklaşma (kontrollü yaklaşma)
| Param | Vars. | Ne yapar |
|---|---|---|
| `V_CAP_FAR` S | 2500 | Uzak hız tavanı (cm/s; oyun maks 3333) |
| `V_CAP_NEAR` S | 500 | Terminale giriş tavanı. Savruluyorsan düşür |
| `BRAKE_DIST` S | 7000 | Frenleme başlangıcı. Overshoot'ta artır (9000) |
| `KP_H` / `KD_H` A | 2.5e-4 / 6e-4 | Yaklaşma PD'si. Genelde dokunma |

### Dikey
| Param | Vars. | Ne yapar |
|---|---|---|
| `KP_Z/KI_Z/KD_Z` A | 4e-4 / 2e-4 / 1e-3 | İrtifa PID. `[Z]`'de ez sıfıra oturmuyorsa bak; önce Aşama 2'yi dene |
| `THR_UP/THR_DN` A | 0.7 / −1.0 | Dikey tavanlar (THR_DN=−1 kalsın) |
| `SEARCH_ALT` C | 5000 | Arama irtifası (cm). Hedefin tipik irtifasına yakın seç (üstte kalma!) |

### Ortak
| Param | Vars. | Ne yapar |
|---|---|---|
| `MAX_DELTA` S | 0.05 | Tik başına maks komut değişimi (TÜM eksenler!). 0.03 yumuşak/hantal · 0.05 denge · 0.08+ tepkili/titrek |
| `HOLD_TICKS` C | 300 | ~6 sn veri tutma (v0.0.5'in 2 sn'lik kesintilerine bol marj — dokunma) |

**Dokunma:** `A_MAX_STRIKE, VZ_MAX, Z_SIGN, PITCH/ROLL_MAX, DERIV_EMA, POS_DEADBAND`, filtre `telafi_sn`.

---

## 5) AŞAMALI PROSEDÜR — sırayı bozma

Mantık: görsel teması etkileyen katmanlar önce; vuruş sertliği en son.
Aşama 5'e kadar kaynak = **Gerçek GPS**.

**Aşama 0 — Taban çizgisi:** Varsayılanlarla 1 koşu + `analiz_ucus`. Bu satır referansın.

**Aşama 1 — Burun/kamera (yatay):** `FOV_kayip_s` ve `yaw_sat`'a bak; kayıplar
hangi anda (log `nose_off_true` serisi)? Dönüşlerde kayıp + yaw_sat yüksek →
`YAW_MAX` 0.30→0.35→0.40. Burun hedef etrafında salınıyorsa `KP_YAW` 1.0→0.7.
**Karar: FOV_kayip=0 ve salınımsız → geç.**

**Aşama 2 — İrtifa hattı (dikey):** Kural: **hedefle aynı irtifaya erken in,
üstünde süzülme** (25° tilt). Hedef senaryoda yüksekse `SEARCH_ALT`'ı ona yaklaştır.
`[Z]`'de ez yaklaşma boyunca |ez|<2-3 m'ye oturmalı, sarkaç yapmamalı.
**Karar: FPV'de hedef dikeyde kaybolmuyor → geç.**

**Aşama 3 — Kontrollü yaklaşma:** Log'da `gercek_mesafe` monoton azalmalı;
strike sınırına girerken hız ~`V_CAP_NEAR` bandında. Savrulma → `BRAKE_DIST` 7000→9000
ve/veya `V_CAP_NEAR` 500→400. Sürünüyorsa `V_CAP_FAR` 2500→3000.
**Karar: overshoot yok, terminale sakin giriş → geç.**

**Aşama 4 — Terminal ("tekte vur"), üç alt adım SIRAYLA:**
- **4a Stabil izleme:** `KV_STRIKE=2.0, STRIKE_TILT=0.45` ile başla; titrekse KV −0.25.
- **4b Delme:** `V_CLOSE_MIN` 700→850→1000; her adımda `bounce` ve `min_menzil`.
- **4c Son metre:** görüntü dönüyorsa (`max_LOS` binlerce) `COMMIT_RANGE` 500→700→900;
  hedef son anda kaçıp ıskalatıyorsa 400'e in.
**Karar: 3 koşu üst üste vuruş + bounce=0 + FOV_kayip=0.**

**Aşama 5 — İnovasyonlu J ile doğrulama:** Aynı setle 5 koşu. Kabul: ≥4 vuruş,
toplam FOV kaybı <1 sn. Kötüyse toleransı artır (`COMMIT_RANGE` ↑, `STRIKE_RANGE` ↑).

**Aşama 6 — Kalıcılaştırma:** Değerleri Yazdır → `guidance/ana_kontrol.py` Cfg →
commit. `veri/ucus_metrikler.csv`'nin son halini sakla (rapor/video kanıtı).

---

## 6) Log kolonları mini sözlük
`gercek_mesafe` (gerçek 3B mesafe — ana seri) · `nose_off_true` (burun↔gerçek hedef
açısı, derece — görsel temasın ham verisi) · `d_s`,`v_close` (terminal LOS + kapanış hızı)
· `ez`,`ez_int` (dikey hata + integral) · `*_raw` vs `*_cmd` (istenen vs rate-limit
sonrası; sürekli ayrışıyorsa MAX_DELTA kısıtlıyor) · `vcap`,`drone_speed` (hız profili)
· `phase/durum` (hangi anda hangi mod).

## 7) Sık tuzaklar
1. İki parametreyi birden değiştirmek. 2. Tek J koşusuna karar vermek (bozulma her
koşuda farklı). 3. `MAX_DELTA`'nın tüm eksenlere ortak olduğunu unutmak. 4. Slider
değerlerini Cfg'ye yapıştırmamak. 5. Hedefin üstünde süzülmek. 6. `STRIKE_TILT`'i
"agresif=iyi" sanmak (kriter hız değil temas). 7. Aynı anda iki arayüz açmak.

## 8) Başlangıç seti (ilk koşu önerisi)
`YAW_MAX=0.35 · KP_YAW=1.0 · MAX_DELTA=0.05 · STRIKE_RANGE=6000 · V_CLOSE=1200 ·
KP_CLOSE=0.6 · V_CLOSE_MIN=850 · KV_STRIKE=2.0 · STRIKE_TILT=0.45 · COMMIT_RANGE=600`
+ dikey varsayılan.

---

## 9) GÖRSEL TUNE MODU (PNG çarpışma rotası — 2026-07-06)

Görsel güdümü (PNG, `guidance/png_gorsel.py`) **GPS yaklaşma mekaniklerine
takılmadan** izole test etmenin yolu:

1. Oyun + arayüzü başlat; **kaynak = GERÇEK GPS** seç (J filtre sapması denklemden çıkar).
2. Görev başlat; drone hedefe yaklaşsın (veya manuel uçur).
3. Güdüm modunu **GORSEL**'e al (OTO/GPS/GORSEL anahtarı) → FSM anında
   `GORSEL_GUDUM`: kalkış kapısı, standoff, ALT_OFFSET, fren/speed_cap, None
   yönetimi **tamamen atlanır**; komutlar yalnız kameradan üretilir. Kayıpta
   GPS'e geri DÖNMEZ (zorlanmış mod) — hover'da bekler.
4. PNG parametrelerini tune et (öncelik sırası: `VIS_KP_CLOSE` kapanma hızı,
   `VIS_PN_N` navigasyon sabiti, `VIS_PN_TILT` yetki, `VIS_TAU_Z` dikey ataklık).
5. Her koşudan sonra: `python araclar/gorsel_episode_analiz.py` → ÖZET satırındaki
   **minR medyanı** kıyas metriğin (düşüyorsa iyileşiyorsun). Tek koşuda TEK
   parametre değiştir.

OTO uçtan-uca doğrulama (handoff dahil): kaynak V2 + mod OTO ile tam görev;
`ARAMA→KILIT→GORSEL_GUDUM` zinciri konsolda `[GORSEL]` satırıyla izlenir.

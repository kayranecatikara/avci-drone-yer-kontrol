# 03 — ÖLÇÜMLER VE KANITLAR

> **Kural: uydurma yok.** Bu belgede köprüdeki her sayının hangi ölçümden geldiği,
> hangi varsayımın çürütüldüğü ve neyin **kanıtlanmadığı** yazılıdır.

**Ham veri:** 27 yasa uçuş logu (`gazebo_kaynak/logs/gps_guidance_*.csv`),
10 angajman logu + 15 ölçüm logu (`veri/kopru_*.csv`), 164 birim testi.

---

## FAZ 0 — DOĞRULAMA (kod yazmadan)

Platform iddialarının tek tek doğrulanması. Sonuç: **hepsi doğru**.

| İddia | Sonuç | Kanıt |
|---|---|---|
| Dünya z-YUKARI / yaw CCW / burun=+x | ✅ | `ana_kontrol.py:515-521` docstring + `world_to_body` formülü |
| `e_right = ex·s − ey·c` | ✅ | birebir |
| `ROT_IN_DEGREES=True` (rotasyon derece) | ✅ | `:113` + kullanım `:1150-1152` |
| PITCH/ROLL/YAW/Z_SIGN = +1 | ✅ | `:114-120` |
| Komut tavanları | ✅ | PITCH/ROLL_MAX=0.75, THR_UP=0.70, **THR_DN=−1.00**, **YAW_MAX=0.60**, MAX_DELTA=0.05 |
| Throttle negatif = serbest düşüş | ✅ | SDK `:273-276`, README `:87-95` |
| Tırmanma yanlılığı ölçümü kodda | ✅ | `corr(vz,thr)=+0.7`, ort thr=−0.45'te ort vz=+80 cm/s |

**Eksik bulunanlar:** `guidance_core.py` (kullanıcı ekledi),
`vision/geometry.py` (pinli commit `0071fc4`'ten indirildi).

---

## FAZ 1 — DİKEY + YAW

### Kaza dersi (önce bu)

İlk ölçüm koşusu **kazayla** bitti. Kök neden **script hatası**:
`get_drone_altitude()` **dünya-Z** verir, AGL değil. Spawn zemini z=48.4 m
olduğundan script yerdeki aracı "48 m irtifada" sandı; alçalma segmenti araziye
kondu, ileri segment yerde 9.7 s sürttü, araç patladı (CSV: 186 m ışınlanma).

**Eklenen korumalar:** zemin referansı (tüm hedefler AGL), AGL<15 m koruma
tırmanışı, ışınlanma dedektörü, arm kenarı.

### THR_TRIM keşfi — SDK belgesi yanlış

| thr | ölçülen dikey hız |
|---|---|
| −0.38 | **+1.4 m/s** (tırmanış!) |
| −0.617 | −0.18 m/s |
| oturmuş hover | **−0.62 … −0.66** |

⇒ `THR_TRIM = −0.60`. Bulunmadan integratör −0.600 tavanına kilitleniyordu;
eklendikten sonra integratör **0.00** civarında.

### Dikey kabul ölçümleri

| Ölçüm | Hedef | Gerçekleşen |
|---|---|---|
| İrtifa tutma (hover) | ~0 | **+0.34 / −0.29 m** (5 s segment) |
| İrtifa tutma (25 m/s ileri uçuşta) | ~0 | **eğim 0.00 m/s**, AGL 71→71 m |
| Tırmanma +2.0 m/s | 2.0 | **+1.94 m/s** (%97) |
| Alçalma −2.0 m/s | −2.0 | **−1.78 m/s** (%89) |

### Yaw kalibrasyonu

- Açık döngü: stick 0.30 → **41.6°/s**, 0.60 → **88.0°/s** ⇒ **~143°/s per stick**,
  %6 içinde doğrusal
- Kapalı döngü ±90° adım: oturma **1.31 s**, kalan hata **0.0°**, toplam dönüş
  **87.4°** → **kaçak YOK**
- **Çerçeve haritası uçuşta doğrulandı:** NED +90° komutu → DoW −87.4° dönüş

### Hız kaynağı kararı (ölçümle)

Hakem = kat edilen yol/zaman (bağımsız): **26.21 m/s**

| Kriter | SDK velocity | Konum sonlu-farkı |
|---|---|---|
| Kalıcı sapma | **+0.36 m/s** | +2.68 m/s |
| Gürültü std | **0.28–0.34 m/s** | 3.1–5.5 m/s (~15×) |
| Gecikme | **0–20 ms** (korelasyon 0.89-0.93) | referans |

⇒ **Yatay: SDK velocity.** Dikey: sonlu-fark (bu koşuda kanıtlandı,
`ana_kontrol`'ün uçuşta kanıtlı deseni).

---

## FAZ 2 — YATAY KANAL

### Çürütülen varsayım: ArduCopter kazancı

`KP_V=2.0` (PSC_VELXY_P) "45° yatış ≈ 18 m/s" tesisi varsayıyordu.
**Ölçüm: DoW'da 18° yatış = 26.2 m/s** → tesis 3-4 kat daha hızlı. Kazanç iptal,
yerine trim ileri-besleme + PI.

### İşaret/eksen: 8/8 doğru

4 heading (NED 0/90/180/270) × pitch/roll itmeleri; ölçülen dünya-hız azimutu
beklenenle **en fazla 2.7° farklı**.

### Trim eğrisi

| stick | oturmuş hız | %95 süresi |
|---|---|---|
| 0.10 | 8.70 m/s | 5.1 s |
| 0.15 | 13.17 m/s | 5.2 s |
| 0.20 | 17.56 m/s | 5.2 s |
| 0.30 | 26.15 m/s | 5.3 s |
| 0.45 | 32.86 m/s | 3.3 s |

Çalışma bandında **v = 87.8 · stick** (doğrusal R²=0.962). Roll eğrisi pitch'le
birebir (fark <%0.2, R²=0.9999).

### Basamak yanıtı — üç iterasyonluk teşhis

1. `KP_VH=0.024` → aşma **%20.2** (sınır ihlali)
2. `KP_VH=0.018` → aşma **%23.7'ye BÜYÜDÜ** ⇒ suçlu P değil
3. CSV anatomisi: rampa boyunca integral **+0.079 stick** doluyor
   (≈7 m/s trim fazlası) → hedef geçilirken stick trim üstünde → 5 s boşalma
   kuyruğu
4. Çözüm: `E_VH_INT_BAND = 2.5 m/s` (integral yalnız hata banttayken birikir) +
   KP 0.024'e geri

| Basamak | Aşma | Oturma | Kalıcı hata | Kabul (aşma<%20, hata<%5) |
|---|---|---|---|---|
| 0→10 m/s | **%3.2** | 1.41 s | %0.0 | ✅ |
| 10→18 m/s | **%3.5** | 1.42 s | %0.0 | ✅ |

### Yan hareket

Yanal 0→5 m/s: **5.04 m/s** (+%0.8), burun sapması **0.0°**, `i_right` −0.001.

### YAW_MAX 0.60 → 0.85

Yasanın rampası 120°/s; 0.60 yalnız ~86°/s veriyordu. 0.85 → **133.6°/s** ölçüldü;
±90° adım oturma **1.11 s** (0.60'ta 1.31), kaçak yok. **Kalıcı.**

---

## FAZ 3.0 — ÖN ÖLÇÜM (uçuşsuz)

### Hedef hızı

Sıçrama-ayıklamalı çoklu taban çizgisiyle, 2 bağımsız 60 s pencere:

| Taban | Robust medyan | Robust p95 |
|---|---|---|
| 1 s | 18.02 m/s | 27.6 |
| 3 s | 17.87 m/s | 26.7 |
| **5 s** | **17.55 m/s** | **18.32** |

⇒ hedef **≈17.6–18.0 m/s**. Yasanın `V_MAX=18` ile marjı **≈ sıfır**.
Desen: **daire ağırlıklı**, yerel yarıçap ~55 m (çember-fit).

### Bozulma parametreleri (oyunun kendi bildirdiği)

`rate_hz=5.00` · **`delay_s=1.00`** · sabit offset **(2, 2, 1) m** ·
dropout 2 s · konum gürültüsü ±0.1 m · hız gürültüsü ±10 m/s +%10

### Kestirim gürültüsü (gerçeğe karşı)

| Kestirim | Konum hata med | Hız şişkinlik | Hız gürültü std | ω şişkinlik |
|---|---|---|---|---|
| HAM (filtresiz) | 19.3 m | 0.99× | 28.2 m/s | 1.20× |
| **gps_guidance EMA** | **25.7 m** | 1.03× | 4.94 m/s | **1.70×** |
| CT-EKF (telafi 1.0) | **8.6-10.1 m** | 1.05× | 4.20 m/s | 1.43× |

---

## FAZ 3.1 — ANGAJMANLAR

### Konfigürasyon tablosu (her biri 3 angajman × 75 s)

| Etiket | Konfig | Oturmuş menzil | Kilit %5 (10 s kümülatif) |
|---|---|---|---|
| A | V_MAX=18, IC=14, bozuk GPS | 38.7 m* | 0/3 |
| B | + IC_ORAN=0.27 | 38.4 m* | 0/3 |
| C | V_MAX=22 | 38.4 m* | 0/3 |
| D/E | + CT-EKF, RANGE=6.9 | 30.4 m* / **44 m** (truth) | 0/3 |
| T | **gerçek GPS**, IC=14 | **10.1 m** | 4.31/4.03/1.51 s → 0/3 |
| **U** | **gerçek GPS, IC=0** | **8.1 m** | **10.0/10.0/10.0 s → 3/3 ✅** |
| V3 | U'nun tekrarı | 8.4 m | ✅ |

*A-D'nin menzilleri **ham (bozuk) GPS'ten** ölçüldü ve sistematik olarak
**15.2-15.7 m iyimser** — kuyruk takibinde 1 s gecikme hedefi bize doğru kaydırır.
E'den itibaren truth'tan ölçüldü.

### Metodolojik düzeltme (kendi hatam)

Kilit bandını ham hedef konumundan ölçüyordum; onun medyan hatası 19 m. Kilit
kriteri kameranın gördüğü **gerçek** geometriye ait. Koşucuya truth kaydı
eklendi; A-D sayıları bu yüzden yalnız **kendi aralarında** kıyaslanabilir.

### V_MAX=22 kararı

Kaynağın kendi yorumu dairede `V_MAX` artışının **ters teptiğini** söylüyordu
(Gazebo: 18→24 ile çember 38→43 m büyüdü). Ama mekanizma hız değil **yanal ivme
tavanıydı**:

- Gazebo: 24²/38 = **15.2 m/s² > MAX_ACCEL=12** → bağlıyor
- DoW: 22²/146 = **3.3 m/s²** → tavanın 3.6 katı altında ⇒ **bağlamıyor**

Ölçüm doğruladı: doyum %38-48 → %27-39; doyumdaki efektif kapanma
**−0.4…+0.7 → +3.3…+4.1 m/s**; arıza imzası (kendi yarıçapının büyümesi) **yok**.

### RANGE_SET 11 → 6.9 kararı

**Premis düzeltmesi:** Gazebo Talon'unun kanat açıklığı **1.2801 m** (collision
STL AABB'den ölçüldü; SDF'te `scale` etiketi **yok**, görsel .dae aynı ölçekte,
`guidance_core.py:31-32` bağımsız olarak 1.28 diyor). DoW'unki **1.718 m** —
yani DoW hedefi **1.34× BÜYÜK**.

Kutu oranı = `kanat / (2·R·tan(HFOV/2))`; HFOV her ikisinde de **125°**
(`iris_with_standoffs/model.sdf:247` = 2.18166 rad).

- Gazebo'da 11 m'de: `1.2801/(2·11·1.921)` = **%3.03** ⇒ **11 hiçbir zaman bir
  kilit değeri değildi** (pose modelinin tatlı noktasıydı)
- DoW'da şartname kilit eşiği %5 → **R < 8.94 m**; %6 → R < 7.45 m
- Seçilen **6.9 m** → **%6.48** (iki eşiğin de üstünde marj)

Yan etkiler: `d_h = √((6.9·cos15°)² + IC²)` = 15.5 m < HANDOFF_RANGE=20 ✅;
dikey ofset 1.78 m.

### ISTASYON_ELEV_DEG 15 → 25 kararı (2026-08-07)

**Kullanıcı gözlemi:** "Gazebo'da dronum hedefin ~6 m altındaydı, burada öyle değil."

**Ölçüm doğruladı.** Dikey ayrım `RANGE_SET · sin(ELEV)` — yani **menzile bağlı**;
`RANGE_SET`'i 11→6.9 kesmek dikey ayrımı da orantılı olarak küçültmüştü:

| Konfigürasyon | Arka | Alt | Yükseliş |
|---|---|---|---|
| Gazebo **orijinal** (ELEV=25, R=11) | 9.97 m | **4.65 m** | 25° |
| Gazebo şimdiki (ELEV=15, R=11) | 10.63 m | 2.85 m | 15° |
| DoW önce (ELEV=15, R=6.9) | 6.66 m | **1.79 m** (ölçülen 1.71) | 15° |
| **DoW şimdi (ELEV=25, R=6.9)** | 6.25 m | **2.92 m** | 25° |

**Sorun:** 1.71 m dikey pay, Talon'un kanat açıklığı (1.718 m) kadar — çarpışma
payı yok. Nitekim bir koşuda drone hedefe **1.4 m**'ye girip çarptı ve respawn oldu.

**Neden 25° güvenli:** Gazebo'da **orijinali 25'ti**; 15'e iniş sebebi
ArduPilot'un `WP_ACC_Z = 1 m/s²` dikey rampasıydı (terminalde 4.65 m'yi kapatmaya
2.4-2.8 s yetmiyordu). DoW'da dikey kanal **köprünün kendisi** ve ~1.3 m/s²
ölçüldü → o kısıt **yok**. Ayrıca kutu oranı yalnız `R`'ye bağlı olduğundan
**kilit isterisi etkilenmez**.

**W koşusu (3 angajman, gerçek GPS, ELEV=25) — ölçülen:**

| Metrik | U (15°) | **W (25°)** |
|---|---|---|
| **Drone hedefin altında** | 1.71 m | **2.89 m** (tasarım 2.92 — tutturdu) |
| LOS yükselişi | +13.9° | **+21.4…+22.1°** |
| Kamera ekseninden sapma (tilt 25°) | ~11° altta | **~3° altta** |
| **Kilit %5 (10 s kümülatif)** | 10.0/10.0/10.0 → 3/3 | **8.05/7.88/7.92 → 3/3 ✅** |
| Kilit %6 | 4.52/6.08/6.14 → 2/3 | 0.59/1.01/0.00 → **0/3** ⚠️ |
| Oturmuş menzil | 8.1 m | 8.9 m |
| Salınım genliği | 5-6 m | **4 m** |
| Komut-takip açısı | 2.7-4.0° | **2.2-3.7°** |
| En yakın | 4.0 m | 3.0 m |
| Devir bandında geçen | %90-94 | %91-92 |

**Bedeli dürüstçe:** oturmuş menzil 8.1 → 8.9 m'ye çıktığı için **%6 bandı
kayboldu** (0/3). Şartnamenin eşiği **%5** ve o rahat sağlanıyor (7.9-8.05 s ↔
gereken 5 s); %6 reponun kendi tavsiye marjıydı. Karşılığında dikey pay %69
arttı, salınım ve komut takibi iyileşti, hedef kamera merkezine yaklaştı.

**KALICI** (kullanıcı onayı, 2026-08-07). Geri dönüş: `KOPRU_ISTASYON_ELEV = 15.0`.

---

### IC_KAYMA 14 → 0 kararı

**Geometri ölçümü (T koşusu, hedefin kendi çerçevesinde):**

| | arka | yan (içeri) | alt | yükseliş |
|---|---|---|---|---|
| DRONE | +5.0…+5.5 m | **+7.6…+8.1 m** | +1.78 m | +10.9° |
| İSTASYON | +6.66 m | +8.2…+12.2 m | +1.79 m | +7.4° |

Yan bileşen arkanın 1.5 katı, altın 4.5 katı → araç görsel olarak hedefin
**yanında** uçuyor (kullanıcı gözlemi doğrulandı).

Kritik bulgu: `|drone−istasyon| = 3.7-4.3 m` (takip iyi) ama
`|istasyon−hedef| = 13.8-15.6 m` — **istasyonun kendisi hedeften uzakta**, çünkü
14 m'lik yan kayma `RANGE_SET=6.9`'u anlamsız kılıyor.

**IC=0 sonrası:**

| | T (IC=14) | **U (IC=0)** | Tasarım |
|---|---|---|---|
| \|istasyon−hedef\| | 13.8-15.6 m | **6.46-6.66 m** | 6.66 ✅ |
| İstasyon yükselişi | +7.4…+9.6° | **+15.0°** | 15° ✅ |
| \|drone−istasyon\| | 3.7-4.3 m | **0.94-1.32 m** | — |
| Oturmuş menzil | 10.1 m | **8.1 m** | — |
| Kilit %5 | 0/3 | **3/3 ✅** | — |

Yan etki kontrolü: salınım genliği 3-4 → 5-6 m (yan kaymanın geometrik
sönümlemesi bir miktar varmış) ama periyot iki katına uzadı; komut-takip açısı
3.9-5.0° → **2.7-4.0°** (iyileşti), doyum %2-11 → %4-8.

---

## GNSS DÜZELTİCİ (CT-EKF)

`fusion/inovasyonlu_j_v2.GNSSDuzeltici` — bozuk hedef GPS'i `get_plane`
zincirine takıldı.

**Uçtan uca zincir ölçümü** (yasanın GERÇEKTEN gördüğü; CT-EKF → yasanın EMA'sı):

| Zincir | Konum hata med | p99 | Hız gürültü | ω şişkinlik |
|---|---|---|---|---|
| Şu anki: ham + EMA | **25.67 m** | 50.1 | 4.94 | 1.70× |
| CT-EKF tek başına | 8.60-8.88 | 60-65 | 4.20 | 1.43× |
| **CT-EKF → EMA (telafi 1.0)** | **10.56 m** | 56.1 | 8.77 | 2.07× |
| CT-EKF → EMA (telafi 1.25) | 10.55 m | 60.3 | 9.70 | 2.12× |

**Kazanç hayatta: −%59.** EMA'nın eklediği gecikme (0.33 s hesaplandı) zincir
optimumunu 0.75-1.0'dan 1.0-1.25'e **yukarı kaydırdı** — beklenen mekanizma
ölçüldü. Plato içinde **telafi_sn=1.0** seçildi (p99 ve gürültü daha iyi, ayrıca
oyunun bildirdiği `delay_s` ile birebir).

Dürüst kalanlar: hız hata std'si kötüleşiyor (4.94→8.77); ω şişkinliği
düzelmiyor (1.70→2.07×).

---

## KÖPRÜ DENETİMİ (özet)

Tam belge: [`../docs/kopru_denetim.md`](../docs/kopru_denetim.md)

| Madde | Sonuç |
|---|---|
| Uçtan uca iz (3 kare, bağımsız yeniden hesap) | **GEÇTİ** — çerçeve **0.00 m**, istasyon ≤0.01 m, komut **0.013 m/s**, stick **birebir** |
| `get_iris` z çevrimi | GEÇTİ (0.003 m) |
| Hız tutarsızlığı (SDK vs sonlu-fark) | GEÇTİ — **ölü alan** (yasa okumuyor) |
| Attitude **pitch** işareti | GEÇTİ — artık 0.39° ↔ ters hipotez 24.40° |
| Attitude **roll** işareti | **KALDI** — DoW roll = −NED roll; etki \|Δu\|=0.013 |
| Jerk şekillendirme | **KALDI** (yok) — etki ölçüldü, zararsız |
| Limit önceliği (yatay) | GEÇTİ — **%0.00** bağlama |
| Eksik teslimat | GEÇTİ — yatay **0.9945**, dikey 1.01-1.02 |
| Yaw takibi / kadraj / kaçak | GEÇTİ — 2.60° · **AV kutusu %100** · +3.6° |
| Zamanlama / aliasing | GEÇTİ — 21.3 / 48.1 Hz · **%0.0** |

**Hüküm:** köprü ArduCopter'ın yerini doğru alıyor.

---

## KANITLANMAYANLAR (dürüstlük bölümü)

1. **Gazebo uçuşuyla birebir karşılaştırma yapılmadı.** Elimizde Gazebo uçuş logu
   yok. "Aynı yasa" kanıtlı (hash + Cfg diff + bağımsız replay); "aynı uçuş"
   değil — araç, hedef ve telemetri farklı.
2. **Kilit isterisi yalnız gerçek GPS'le sağlandı.** Yarışma koşulunda (bozuk
   GPS + CT-EKF) menzil 39-44 m'de oturuyor. Fark ölçüldü: **7.1 m ↔ 39.0 m**.
3. **Roll işareti ters** ve düzeltilmedi (komuta girmediği için ertelendi).
4. **Jerk şekillendirme yok.**
5. **Dedektör tarafı yarım:** Gazebo modeli (`avci_yolo.pt`) DoW'da kullanılamaz
   (HUD metinlerine %96 hayalet kutu) — bu **kanıtlandı**. Ama "dedektörün kutusu
   kilit eşiğini geçiyor mu" sorusu cevaplanamadı (örneklem yetersiz + hakem
   kayması). Ayrıntı: [`../docs/dedektor_testi.md`](../docs/dedektor_testi.md)

---

## ÖLÇÜM ARAÇLARI — nasıl tekrarlanır

```bash
python -m kopru.olcum_faz1  --mod hepsi   --zemin 48.4   # dikey + yaw + hız kaynağı
python -m kopru.olcum_faz2  --mod acik    --zemin 48.4   # işaret/eksen + trim eğrisi
python -m kopru.olcum_faz2  --mod kapali  --zemin 48.4   # basamak + yanal + yaw tavanı
python -m kopru.olcum_faz3on                             # hedef hızı (pasif)
python -m kopru.olcum_gnss  --sure 90                    # CT-EKF A/B (uçuşsuz)
python -m kopru.kosu_faz31  --n 3 --sure 75 --zemin 48.4 --etiket X \
                            --vmax 22 --range 6.9 --ic 0 --hedef truth
```

Hepsi emniyet katmanlıdır: zemin referansı, AGL<15 m koruması, ışınlanma
dedektörü, Ctrl+C'de TRIM hover.

# 02 — DÖNÜŞTÜRÜCÜ: `dow_kopru.py`

> **Bu klasördeki asıl iş.** 643 satır. Görevi: ArduPilot'un yerini almak —
> yasanın hız komutunu DoW'un stick'ine kapalı çevrimde çevirmek, ve DoW
> telemetrisini yasanın beklediği sözleşmeye getirmek.

---

## 1. TASARIM İLKESİ: İKİ UÇ, TEK DOSYA

```
        DoW telemetri                                    DoW SDK
      (cm, z-yukarı, derece)                      (stick, -1…+1)
              │                                          ▲
              ▼                                          │
    ┌─────────────────────  dow_kopru.py  ─────────────────────┐
    │  get_iris() / get_plane()          adim() → _uygula()     │
    │  cm→m, z-yukarı→NED, deg→rad       trim+PI → stick        │
    └───────────┬──────────────────────────────▲───────────────┘
                ▼                              │
          gps_guidance.py  ──set_hiz_ned()─────┘
             (DEĞİŞMEZ)      (send_velocity'nin karşılığı)
```

Giriş adaptörü ve çıkış köprüsü **aynı dosyada** olmak zorunda: çıkış, girişin
tam tersini kullanır. Ayrı dosyalara bölünürse biri kaçınılmaz olarak ters olur
ve hata **yalnızca uçuşta** ortaya çıkar. Bu yüzden çerçeve dönüşümü tek yerde,
çift yönlü ve **birim testli** tanımlıdır.

---

## 2. ÇERÇEVE SÖZLEŞMESİ (satır 124-141)

```python
NED_x (Kuzey) =  DoW_x
NED_y (Doğu)  = -DoW_y          # yatay eksenlerden BİRİ çevrilir
NED_z (Aşağı) = -DoW_z          # DoW z-yukarı, NED z-aşağı
yaw_NED       = -yaw_DoW
```

Sağdan-el kuralı korunur: `det(diag(1,-1,-1)) = +1`.

```python
def dow_to_ned_vek(v):  return (v[0], -v[1], -v[2])
def ned_to_dow_vek(v):  return (v[0], -v[1], -v[2])   # matris kendi tersi
```

**Neden bu konvansiyon?** Kanıt `guidance/ana_kontrol.py:515-521`'den geldi —
DoW için uçuşta doğrulanmış `world_to_body`:
```python
e_fwd   = ex·cos + ey·sin
e_right = ex·sin - ey·cos      # NED'de -ex·sin + ey·cos olurdu
```
Bu formül DoW'un **z-yukarı / yaw-CCW / burun=+x** dünyasına aittir. Onu
korumak için köprü hesabı DoW çerçevesinde yapar, yasaya NED sunar.

**Tersinirlik testi** (`tests/test_dow_kopru.py`):
```python
ned_to_dow_vek(dow_to_ned_vek(v)) == v          # 4 farklı vektörde
dow_yaw_to_ned(ned_yaw_to_dow(a)) ≈ a           # 81 açıda, hata < 1e-12
```

**Uçuşta doğrulandı:** NED +90° yaw komutu DoW'da −87.4° dönüş üretti → eşleme
fiziken teyit.

### Dikey orijin kaydırması (`NED_ZEMIN_M`, satır 160-168)

Yasanın yere-çakılma koruması (`LOOKUP_MIN_ALT=8`) NED z'sinin **zemin ≈ 0**
olduğu Gazebo'ya göre yazılmış. DoW'da spawn zemini **dünya-z 48.4 m**'de →
kaydırma olmadan koruma çalışmaz (hedef 5 m AGL'ye inerse istasyon 2 m AGL'ye
kurulur). Adaptör bu yüzden:

```python
"z": -(p[2] - NED_ZEMIN_M)      # yasanın gördüğü irtifa = AGL
```

Bu bir **çeviri katmanı kararıdır**, yasa değişikliği değil. Zemin, görev
başında aracın irtifasından alınır.

---

## 3. GİRİŞ ADAPTÖRLERİ

### 3.1 `get_iris()` (satır 368-380)

```python
p, v, (roll, pitch, yaw) = self._drone_dow()      # cm→m, cm/s→m/s, deg→rad
return {"x": pn[0], "y": pn[1], "z": -(p[2] - NED_ZEMIN_M),
        "vx": vn[0], "vy": vn[1], "vz": vn[2],
        "roll": roll, "pitch": pitch, "yaw": dow_yaw_to_ned(yaw)}
```

**İşaret kararları ve kanıtları:**

| Alan | Karar | Kanıt |
|---|---|---|
| `pitch` | **aynen geçer** | İleri itki komutunda (stick +0.208 = +12.5°) DoW **−12.50°** bildiriyor, korelasyon −0.843 → burun aşağı = negatif ⇒ konvansiyon NED ile aynı. Ayrıca attitude'dan bağımsız sınama: `elev_gövde − elev_dünya = −pitch` hipotezinin artığı **0.39°**, ters hipotezinki 24.40° |
| `roll` | **aynen geçer — ama TERS** ⚠️ | Sağa yatışta DoW **negatif** bildiriyor (korelasyon −0.965) ⇒ DoW roll = −NED roll. Düzeltilmedi çünkü yasa roll'ü **yalnız kadraj ölçümünde** kullanır; etkisi \|Δu\|=0.013 (AV kutusu %100 değişmiyor) |
| `yaw` | **çevrilir** | `dow_yaw_to_ned` — uçuşta doğrulandı |
| `vx/vy/vz` | SDK velocity | **Yasa bunları hiç okumuyor** (ölü alan) — bkz. denetim B3 |

### 3.2 `get_plane()` (satır 382-421)

Hedef konumunu döndürür. Üç modu var:

1. **Bozuk kanal + CT-EKF** (yarışma): ham konum
   `fusion/inovasyonlu_j_v2.GNSSDuzeltici`'den geçer
2. **Bozuk kanal, filtresiz**: `GNSS_DUZELTICI_AKTIF=False`
3. **Gerçek GPS** (teşhis): `HEDEF_TRUTH_AKTIF=True` → bozuk kanal **hiç
   okunmaz**, `get_debug_truth()` kullanılır, filtre baypas

**`frozen` semantiği:** ham değer değişmediyse donuk. Yasanın kendi tazelik
kontrolü de (`raw != last_raw`) aynı anlamda. CT-EKF **yalnız taze pakette**
güncellenir (donmuş kare filtreye zaman ilerletmez) → yasanın tazelik kapısı
korunur.

**CT-EKF ayarları ölçümle:**
- `dt = 0.23 s` — ölçülen taze paket aralığı (345 paket / 90 s; oyunun
  bildirdiği `rate_hz=5.0`, dropout'lar etkin hızı düşürüyor)
- `telafi_sn = 1.0 s` — **oyunun kendisi bildiriyor**
  (`get_debug_truth()["corruption_params"]["delay_s"] = 1.00`); offline tarama
  da tam orada tepe yaptı (0.5→12.55, **1.0→10.14**, 1.5→14.40 m hata)

---

## 4. ÇIKIŞ KÖPRÜSÜ — KANAL KANAL

### 4.0 Setpoint girişi (satır 441-447)

```python
def send_velocity(conn, vx, vy, vz, yaw):   # yasanın çağırdığı isim
    conn.set_hiz_ned(vx, vy, vz, yaw)       # YALNIZCA setpoint yazar
```

Kontrol hesabı burada **yapılmaz**. Sebep: yasa 20 Hz koşar, kontrol 50 Hz
olmalı (bkz. §5).

### 4.1 YATAY: `stick = trim(v_sp) + PI(hız hatası)` (satır 478-506)

```python
sp_fwd, sp_right = dunya_to_govde(v_sp_dow[0], v_sp_dow[1], yaw_dow)
olc_fwd, olc_right = dunya_to_govde(v_dow[0], v_dow[1], yaw_dow)
e_fwd   = sp_fwd - olc_fwd
pitch   = yatay_trim_stick(sp_fwd) + KP_VH·e_fwd + i_fwd
roll    = yatay_trim_stick(sp_right) + KP_VH·e_right + i_right
```

#### Neden ArduCopter'ın modeli KULLANILMADI

İlk taslak ArduCopter'ın yaklaşımını taşıyordu:
`ivme = PSC_VELXY_P · hız_hatası`, sonra `açı = atan(ivme/g)`. Bu model
"45° yatış ≈ 18 m/s" tesisi varsayar.

**Ölçüm bunu çürüttü:** DoW'da **18° yatış 26.2 m/s** veriyor — tesis derece
başına 3-4 kat daha hızlı, sürükleme çok düşük. Aynı kazanç aşma yapardı.

#### Yerine: trim ileri-besleme + PI (dikeydeki `THR_TRIM` mantığının aynısı)

Sabit hızda uçmak sabit bir yatış açısı ister (sürükleme dengesi). Bu çalışma
noktasını integratöre **kovalatmak** yerine **ileri beslemek**:

**Ölçülen trim eğrisi** (`olcum_faz2.py --mod trim`):

| stick | oturmuş hız | %95 süresi |
|---|---|---|
| 0.10 | 8.70 m/s | 5.1 s |
| 0.15 | 13.17 m/s | 5.2 s |
| 0.20 | 17.56 m/s | 5.2 s |
| 0.30 | 26.15 m/s | 5.3 s |
| 0.45 | 32.86 m/s | 3.3 s (33.3 m/s zarf tavanına dayandı) |

Çalışma bandında (≤17.6 m/s) neredeyse **tam doğrusal: v = 87.8 · stick**
(doğrusal R²=0.962, kuadratik R²=0.987 — fark yalnız zarf tavanının dayattığı
son-nokta düzleşmesi). Yani "kuadratik sürükleme" baskın değil.

**Roll eğrisi pitch'le birebir** (8.69 / 17.53 / 26.13 m/s; fark <%0.2,
R²=0.9999) → tek tablo iki eksene de geçerli.

```python
YATAY_TRIM_NOKTA = ((0.0,0.0), (8.7,0.10), (13.2,0.15),
                    (17.6,0.20), (26.2,0.30), (32.9,0.45))
```
İşaretli/simetrik, aralar doğrusal, son noktadan sonra son eğimle ekstrapolasyon.

#### Kazançlar ve windup kapısı

```python
KP_VH = 0.024        # dv/dstick = 87.8 ölçümünden: bant 2.1 1/s
KI_VH = 0.012        # trim eğrisi artığı (tau_i ~2 s)
I_VH_MAX = 0.15      # integral yetkisi
E_VH_INT_BAND = 2.5  # integral YALNIZ |hata| bu bandın içindeyken birikir
```

`E_VH_INT_BAND` bir **teşhisin ürünü**: KP=0.024'te 0→10 m/s basamağında aşma
%20.2 çıktı. KP'yi 0.018'e düşürdüm → aşma **%23.7'ye BÜYÜDÜ** (suçlu P değilmiş).
CSV anatomisi kökü gösterdi: rampa boyunca integral +0.079 stick'e doluyor
(≈7 m/s'lik trim fazlası), hedef geçilirken stick'i trim üstünde tutuyor →
5 s'lik boşalma kuyruğu. Bant kapısı eklenince:

| Basamak | Aşma | Oturma | Kalıcı hata |
|---|---|---|---|
| 0→10 m/s | **%3.2** | 1.41 s | %0.0 |
| 10→18 m/s | **%3.5** | 1.42 s | %0.0 |

### 4.2 DİKEY: `throttle = TRIM + FF + PI` (satır 508-517)

```python
vz_up_sp = -sp[2]                            # NED aşağı(+) → yukarı(+)
e_vz     = vz_up_sp - vz_up_olc
thr = THR_TRIM + FF_VZ·vz_up_sp + KP_VZ·e_vz + i_vz
```

#### En önemli keşif: SDK belgesi yanlış

SDK ve README diyor ki: *"`set_throttle(0.0)` → hover (irtifasını korur)"*.

**Ölçüm** (`olcum_faz1.py --mod dikey`):
- thr **−0.38** → **+1.4 m/s tırmanış**
- thr **−0.617** → −0.18 m/s
- Oturmuş hover gazı: **−0.62 … −0.66**

Yani gerçek denge gazı **≈ −0.60**. Bu bulunmadan integratör −0.600 yetki
tavanına kilitleniyordu (yetkinin tamamını sabit yanlılık yiyordu).

```python
THR_TRIM = -0.60      # ileri besleme; integratör yalnız ARTIĞI kapatır
```

Bu, `ana_kontrol.py`'nin "tırmanma yanlılığı" savaşının aynı kökü — orada
`corr(vz,thr)=+0.7` iken `ort thr=−0.45`'te `ort vz=+80 cm/s` ölçülmüştü.

#### İşaret tuzağı

NED'de `vz` **AŞAĞI pozitif**, DoW throttle **YUKARI pozitif**. Kod boyunca
`vz_up` adıyla yukarı-pozitif ara değişken kullanılır; birim testi her iki yönü
de doğrular.

#### Kazançlar

`ana_kontrol`'ün uçuşta kanıtlı iç hız döngüsünden birim çevrimiyle (cm→m, ×100):

| ana_kontrol | → köprü |
|---|---|
| `KV_Z = 0.00220` thr/(cm/s) | `KP_VZ = 0.22` thr/(m/s) |
| `KI_Z_VEL = 0.00150` | `KI_VZ = 0.15` |
| `INT_Z_AUTH = 0.60` | `I_VZ_MAX = 0.60` |

**Dikey geri besleme kaynağı:** `HIZ_KAYNAK = "sonlu_fark"` (irtifa türevi +
EMA, `ana_kontrol._own_dikey_hiz` deseni). Ölçümde SDK velocity ve sonlu-fark
1 s'lik irtifa türevine karşı ikisi de yansız çıktı (+0.001 / −0.003 m/s);
kanıtlanmış olan korundu.

**Sonuç:** tırmanma +2.0 m/s isteğinde gerçek irtifa eğimi **+1.94 m/s**,
alçalma −2.0'da **−1.78 m/s**; 25 m/s ileri uçuşta irtifa eğimi **0.00 m/s**.

### 4.3 YAW: mutlak açı → dönüş hızı (satır 519-526)

```python
yaw_hata = sarmala_pi(yaw_sp_dow - yaw_dow)
yaw_hata = kirp(yaw_hata, ±YAW_HATA_MAX)      # KAÇAK KORUMASI
if |yaw_hata| < YAW_DEADBAND: yaw_hata = 0
yaw_cmd = kirp(KP_YAW · yaw_hata, ±YAW_MAX)
```

**Kaçak koruması neden var?** `gps_guidance`'ın `cmd_yaw`'ı **kalıcı bir
durumdur** (satır 440-445) ve aracın gerçek heading'ine demirlenmemiştir:

```python
cmd_yaw = normalize_angle(cmd_yaw + step)     # kendi üstüne birikir
```

Araç yetişemezse komut önde birikir ve araç kendi etrafında döner
(`adapter_copter.py` bu tuzağı ölçmüş: 1.0 tur yerine **7.4 tur**). Köprü
**üzerinde çalıştığı hatayı** ±90°'ye kırpar.

**Kalibrasyon** (`olcum_faz1.py --mod yaw`): stick 0.30 → 41.6°/s,
stick 0.60 → 88.0°/s ⇒ **~143°/s per birim stick**, %6 içinde doğrusal.

**`YAW_MAX = 0.85`** (0.60'tan yükseltildi): 0.85 ≈ **121°/s**, yasanın
`YAW_RATE_MAX=120°/s` rampasıyla **eşleşir**. 0.60 yalnız ~86°/s veriyordu —
hızlı kerteriz değişiminde komut önde birikiyordu.

Doğrulama: açık döngü 0.85 → 133.6°/s; ±90° adım oturma **1.11 s**, kalan hata
**0.0°**, toplam dönüş ±87.5° (**kaçak yok**). Angajmanda 75 s boyunca cmd_yaw
−612° ↔ gerçek −616° → birikme **+3.6°**.

### 4.4 Rate-limit + atomik gönderim (satır 557-565)

```python
def _uygula(self, thr, pitch, roll, yaw):
    thr   = rate_limit(thr,   onceki["thr"],   MAX_DELTA)
    ...
    sdk.set_control_surfaces(thr, pitch, roll, yaw, True)   # TEK TCP satırı
```

`MAX_DELTA = 0.05`/tik — `ana_kontrol.py:240`'tan (bank rate uyumlu, salınım
önleyici). 50 Hz'te 0→0.75 ≈ 0.3 s.

Atomik gönderim şart: `set_control_surfaces` dört kanalı **tek satırda** yollar;
ayrı `set_*` çağrıları ara karelerde throttle/pitch uyumsuzluğu yaratır.

### 4.5 Bayat setpoint koruması (satır 528-535)

Yasa 20 Hz yazar (normal ara 0.05 s). `BAYAT_S = 0.30` süre geçerse:
```python
pitch = roll = 0.0
thr   = THR_TRIM        # thr=0 DEĞİL — o +1.4 m/s tırmanış demek
```
Güdüm takılırsa araç gökyüzüne kaçmaz, yaklaşık seviyede kalır.

---

## 5. DÖNGÜ MİMARİSİ — neden iki hız

```
gps_guidance thread (20 Hz)          server/beyin döngüsü (50 Hz)
   run_gps_guidance(...)                  AvciKontrol.adim()
        │                                       │
        └─ send_velocity ─► set_hiz_ned()       └─► KopruGudum.adim()
             (yalnız setpoint yazar)                   └─► DowKopru.adim()
                                                            (kontrol + gönder)
```

**Neden ayrıldı?** İlk taslak kontrolü `send_velocity` anında yapıyordu (yani
20 Hz). Üç sorun:
1. `BAYAT_S` koruması **ölü koddu** — `_t_sp` her çağrıda tazelendiği için koşul
   asla tutmazdı
2. `MAX_DELTA=0.05` slew'i **50 Hz'e göre** kanıtlıydı; 20 Hz'te yarı hızda kalır
3. SDK 50 Hz kontrol döngüsü öneriyor

**Ölçülen sonuç:** yasa dt medyan **47.0 ms → 21.3 Hz** (hedef 20), köprü
**48.1 Hz ortalama** (tasarım 50; aralık iki tepeli 16/31 ms — Windows 15.6 ms
zamanlayıcı granülasyonu). Aliasing **%0.0** — her yasa tiki taze veri görüyor.

---

## 5b. AKTİF AYARLAR (yasaya verilen)

Köprü, yasayı şu değerlerle kurar (`ana_kontrol.Cfg.KOPRU_*` → env/setattr):

| Ayar | Değer | Sonuç |
|---|---|---|
| `RANGE_SET` | 6.9 m | istasyon slant menzili · kutu oranı %6.48 |
| `ISTASYON_ELEV_DEG` | **25°** | **6.25 m arka + 2.92 m alt** (ölçülen 2.89) |
| `V_MAX` | 22 m/s | hedef ≈18 m/s'e karşı kapanma marjı |
| `IC_KAYMA` | 0 | iç-daire kayması kapalı |
| `KALKIS_AGL` | 40 m | görev başı tırmanış |

Kamera tilt'i de 25° olduğundan `ELEV=25` hedefi kadraj merkezine oturtur
(ölçülen: kamera ekseninden ~3° sapma). Gerekçeler: [03_OLCUMLER.md](03_OLCUMLER.md)

---

## 6. KALKIŞ (satır 599-628 + `entegre.py`)

Gazebo'da kalkış ayrı hattı vardı (`_send_position_setpoint`, POZİSYON
typemask). DoW'da pozisyon komutu yok → **AGL-kapılı açık döngü tırmanış**:

```python
zemin  = görev başında aracın irtifası      # arac YERDE varsayımı
hedef  = zemin + KOPRU_KALKIS_AGL (40 m)
while AGL < hedef: _uygula(KALKIS_THR=0.60, 0, 0, 0)
sonra: hover (THR_TRIM) → yasa thread'i başlar
```

**Neden AGL?** `get_drone_altitude()` **dünya-Z** verir. Eski `ana_kontrol`
kapısı `drone_z >= SEARCH_ALT(5000 cm)` ile karşılaştırıyordu; DoW spawn zemini
4836 cm olduğundan kapı **fiilen hiç çalışmıyordu**. Bu ders pahalıya öğrenildi:
ilk ölçüm koşusunda script yerdeki aracı "48 m irtifada" sandı, alçalma segmenti
araziye kondu, araç sürtüp patladı.

Yasa thread'i **kalkış bittikten sonra** başlar — tırmanışla hız komutu
çakışmasın.

---

## 7. ARDUCOPTER'DA OLUP BİZDE OLMAYAN

| Bileşen | Köprüde | Ölçüm |
|---|---|---|
| Jerk-sınırlı şekillendirme (WPNAV_JERK=4) | ❌ **YOK** | Komut ivmesinin türevi: medyan **11.3**, p95 **204**, maks **244 m/s³**. Yüksek değerler komut **yönünün** dönmesinden (büyüklük basamağından değil); araç dinamiği + slew limiti emiyor → teslimat %99.5, takip %4 |
| Hız PID | ✅ farklı yapı | trim FF + PI |
| İvme→açı | ✅ ölçülmüş eşleme | trim eğrisi |
| Dikey kaskad | ✅ | TRIM+FF+PI |
| Yaw denetleyici | ✅ | P + sarma + kırpma |

**Limit önceliği** — köprü yasayı kısıtlıyor mu? (denetim, U koşusu)

| Limit | Bağlama oranı |
|---|---|
| KÖPRÜ \|pitch\| ≥ 0.749 | **%0.00** |
| KÖPRÜ \|roll\| ≥ 0.749 | **%0.00** |
| KÖPRÜ thr ≥ 0.699 | **%0.00** |
| KÖPRÜ throttle slew | %42.42 (etki yok: dikey teslimat %101-102) |
| YASA \|v_cmd\| ≥ V_MAX | %5.62 |
| YASA ivme ≥ MAX_ACCEL | %60.05 |

Yatayda köprü **hiç bağlamıyor** — yasa istediğini tam alıyor. Bağlayan tek şey
yasanın kendi `MAX_ACCEL`'i.

---

## 8. ÖLÇÜM KANCALARI (satır 295-299)

Uçuş kodunda kalıcı ama **varsayılan kapalı** kancalar. Ölçüm scriptleri bunları
kullanır; üretimde davranışı değiştirmezler:

| Kanca | Ne yapar |
|---|---|
| `PITCH_SABIT` / `ROLL_SABIT` | Yatay kanal kapalıyken sabit stick enjekte eder (trim eğrisi taraması) |
| `YAW_SABIT` | Yaw kontrolcüsü yerine sabit stick (açık-döngü kalibrasyon) |
| `YATAY_AKTIF` | Yatay kanalı komple kapatır (Faz 1'de dikey+yaw izole test edildi) |
| `HIZ_KAYNAK` | Dikey geri beslemenin kaynağı ("sdk" / "sonlu_fark") |
| `son_tani` | Her tikin tam iç durumu (CSV'ye yazılır) |

---

## 9. BAĞLAMA — tek satır

```python
import control.guidance.gps_guidance as gg
from kopru import dow_kopru

gg.send_velocity = dow_kopru.send_velocity      # yasaya dokunulmaz
run_gps_guidance(kopru, kopru.get_plane, kopru.get_iris, stop_event)
```

`conn` parametresi olarak `DowKopru` örneği geçer; yasa onu MAVLink bağlantısı
sanır, biz istediğimizi yaparız. Bu, dosyayı değiştirmeden davranışı yönlendirmenin
en temiz yolu.

→ Sayılar ve kanıtlar: **[03_OLCUMLER.md](03_OLCUMLER.md)**
→ Arayüze bağlanma: **[04_ENTEGRASYON.md](04_ENTEGRASYON.md)**

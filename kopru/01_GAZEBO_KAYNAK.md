# 01 — GAZEBO KAYNAK SİSTEMİ

> Bu belge **gönderilen sistemi** anlatır: hangi dosyalar geldi, her biri ne yapar,
> yasa nasıl çalışır ve ArduPilot ne iş görüyordu. Dönüştürücünün ne yerine
> geçtiğini anlamak için önce bu gerekiyor.

**Kaynak:** `GUDUM_TASIMA/1_GAZEBO_YENI_GUDUM/` ·
repo: `github.com/kayranecatikara/hamidiyesim` dal `kayramin_super_gudumu`,
yol `control/guidance/`
**Otopilot:** ArduPilot 4.6.0-beta1 (ArduCopter), **GUIDED** mod — PX4 değil.

---

## 1. GELEN DOSYALAR

| Dosya | Satır | Rol | Bizde kullanılıyor mu? |
|---|---|---|---|
| `gps_guidance.py` | 522 | **Güdüm yasası** — tek karar mercii | ✅ EVET, aynen |
| `common.py` | 106 | Ortak matematik + `send_velocity` | ✅ EVET (send_velocity değiştirilir) |
| `guidance_core.py` | 612 | Kadraj hatası ölçümü (kamera geometrisi) | ✅ EVET (yalnız ölçüm) |
| `hedef_kestirim.py` | 250 | IMM (CV+CA) durum kestirimi | ❌ HAYIR — yasa çağırmıyor |
| `frpn.py`, `frpn_guidance.py` | — | Alternatif güdüm (FRPN) | ❌ HAYIR — kapsam dışı |

**Sonradan tamamlananlar** (ilk pakette eksikti, import zinciri kırılıyordu):
- `guidance_core.py` → kullanıcı ekledi
- `vision/geometry.py` (325 satır) → pinli commit `0071fc4`'ten indirildi
  (repo **kökünde** `vision/`, `control/` altında değil — ilk aramada bu yüzden bulunamadı)

---

## 2. `gps_guidance.py` — YASA

### 2.1 Amaç (dosyanın kendi ifadesiyle)

> "Drone'u öyle konumlandır ki hedef sabit-kanatlı İHA kameranın TAM ORTASINDA,
> pose modelinin güvenilir çalıştığı menzil bandında ve KARARLI görünsün →
> supervisor görsel faza devretsin. **(Vuruş DEĞİL; vuruş görsel fazın işi.)**"

Bu cümle kritik: yasa bir **vuruş** yasası değil, bir **devir** yasası. Başarı
ölçütü "hedefe çarpmak" değil, "hedefi kararlı biçimde kadrajda tutup görsel faza
temiz devretmek".

### 2.2 Arayüz sözleşmesi

```python
run_gps_guidance(conn, get_plane, get_iris, stop_event, cfg=Cfg)

get_iris()  -> {x, y, z, roll, pitch, yaw, vx, vy, vz}   # m, rad, NED
get_plane() -> {x, y, z, yaw, frozen}                    # m, rad, NED
```

**Önemli:** Yasa `get_plane`'den yalnızca **x, y, z** ve `frozen`'ı okur
(`gps_guidance.py:297`); `yaw` kullanılmaz.
`get_iris`'ten yalnızca **x, y, z** (satır 290) ve **roll/pitch/yaw** (291-293)
okunur — **vx/vy/vz HİÇ kullanılmaz**. Attitude da yalnız satır 466'daki kadraj
ÖLÇÜMÜNE girer, komuta girmez.

Çıkışı tek noktadan verir: `send_velocity(conn, vx, vy, vz, yaw)` — satır 451
(ana), 269 (hover), 492 (durdurma).

### 2.3 Döngü akışı (20 Hz)

```
1) TAZELİK + FİLTRE      raw != last_raw ise: EMA konum (POS_EMA=0.4)
                          + sonlu-fark hız (VEL_EMA=0.3) + açısal hız (ω)
2) WARMUP / DROPOUT      kestirim yoksa hover; none_count·dt > HOLD_S ise DROPOUT
3) HATA / MENZİL         ex, ey → d_h (yatay), menzil (3B)
4) İSTASYON NOKTASI      hedefin gerisi + altı + iç-daire kayması  ← geometrinin kalbi
5) EMA TÜREV             istasyon hatasının türevi (de)
6) HIZ KOMUTU            v = v_hedef + KP_H·e + KD_H·de   (V_MAX'a kırpılır)
                          vz = vel_z + KP_Z·ez            (±VZ_MAX)
7) YAW                   burun GERÇEK hedefe; YAW_RATE_MAX ile rampalı
8) İVME SINIRI + GÖNDER  limit_acceleration(MAX_ACCEL) → send_velocity
9) KADRAJ HATASI         hedef_kadraj_hatasi() → yalnız CSV (başarı ölçütü)
10) DURUM                d_h < HANDOFF_RANGE ? "KILIT" : "ARAMA"
```

### 2.4 İstasyon geometrisi — yasanın kalbi

Yasa hedefe değil, hedefin **gerisinde-altında** bir noktaya gider:

```
r_eff       = min(menzil, RANGE_SET)          # yakınlaşınca ofset ORANTILI küçülür
d_behind    = r_eff · cos(ISTASYON_ELEV_DEG)  # hız yönünün gerisi (kuyruk)
d_below     = r_eff · sin(ISTASYON_ELEV_DEG)  # altı (NED: +z aşağı)
istasyon    = hedef + geri_yön·d_behind + (0,0,d_below) + iç_kayma
```

**Sayılarla — Gazebo ↔ bizde:**

| | RANGE_SET | ELEV | arka | **alt (hedefin altında)** |
|---|---|---|---|---|
| Gazebo orijinal | 11.0 | 25° | 9.97 m | **4.65 m** |
| Gazebo şimdiki | 11.0 | 15° | 10.63 m | 2.85 m |
| **DoW bizde** | **6.9** | **25°** | **6.25 m** | **2.92 m** (ölçülen 2.89) |

DoW'da `RANGE_SET` kilit kutu oranı için 6.9'a çekildi; dikey ayrım menzile bağlı
olduğundan `ELEV` 25°'ye (Gazebo'nun orijinali) geri alındı — gerekçe ve ölçüm:
[03_OLCUMLER.md](03_OLCUMLER.md#istasyon_elev_deg-15--25-kararı-2026-08-07).
Kamera tilt'i de 25° olduğundan hedef kadraj merkezine yakın oturur.

Üç tasarım kararı ve gerekçeleri (dosyanın kendi yorumlarından):

**(a) Neden gerisi-altı?** Avcı hedefin ALTINDA kalırsa arka plan **gökyüzü**
olur → siluet, yüksek kontrast, tespit kopmaz. Üstten bakışta hedef arazi
karmaşasına gömülür.

**(b) Neden sabit AÇI, sabit metre değil?** (2026-08-01 düzeltmesi) Sabit metre
ofset, menzil küçülünce giderek büyüyen bir LOS yükselişine dönüşüyordu:
menzil 11 m → 25°, 8 m → 35°, 6 m → 51°, 4 m → kadrajın DIŞI. Yani tasarım,
korumak istediği görsel temasını yakın menzilde kendi bozuyordu. `r_eff` ile
ofset menzille birlikte küçülür → yükseliş **her menzilde sabit** kalır.

**(c) Neden iç-daire kayması (`IC_KAYMA`)?** Dairesel kovalamacada zorunlu bağ:
`yarıçap = hız / açısal_hız`. İstasyon hedefin kendi çemberi üzerindeyse drone
aynı yarıçapta uçmak zorunda, dolayısıyla aynı hıza muhtaç. Ölçüm (Gazebo,
6 koşu): drone yarıçapı 38 m = hedef yarıçapı 38 m, menzil 29-34 m'de donuyor.
`V_MAX`'ı artırmak **ters tepiyor** (çember büyüyor, menzil açılıyor). Çözüm:
istasyonu dönüşün İÇİNE kaydır — drone daha küçük yarıçapta, daha az hızla aynı
açısal hızı tutturur. Gazebo ölçümü: kayma 0 → menzil 34.1 m; 8 m → 22.8 m;
**14 m → 9.8 m**.

> ⚠️ Bu mekanizma DoW'da **ters çalıştı** ve `IC_KAYMA=0` yapıldı — sebebi
> [03_OLCUMLER.md](03_OLCUMLER.md)'de.

### 2.5 Kontrol yasası

```python
vx = vel_x + KP_H·ex_cmd + KD_H·de[0]     # hedef-hızı İLERİ BESLEME + PD
vy = vel_y + KP_H·ey_cmd + KD_H·de[1]
# |v| > V_MAX ise YÖNÜ KORUYARAK ölçekle  ← kritik: kırpma oranı değil yönü korur
vz = clamp(vel_z + KP_Z·ez_cmd, ±VZ_MAX)
```

**İleri besleme neden var?** `vel_*` hedefin kestirilen hızıdır. Onu doğrudan
komuta eklemek, kilitlenince kararlı "hold" sağlar — P terimi yalnız artığı
kapatır.

**`KD_H` sönümleme DEĞİL, LEAD'dir** (2026-08-05 bulgusu, dosya yorumu):
`de[]` istasyon hatasının türevi ≈ göreli hız Δv. Yasa açılınca
`v_cmd = v_hedef + KP_H·Δp + KD_H·Δv` — yani "hedefin gideceği yere nişan alma"
miktarını bu katsayı belirler. Uçuşta taranarak 0.20 → **0.60** yapılmış
(oturmuş menzil 34.3 m → 29.4 m).

**⚠ Doyum tuzağı:** komut `V_MAX`'a kırpılırken **yön korunur, oran korunmaz**.
Hedef hızı kestirimi şişkinse ilk terim tek başına `V_MAX`'ı aşar ve kapanma
terimi (`KP_H·e`) tamamen silinir. DoW'da bu **ölçüldü**: doyum karelerinde
efektif kapanma ≈ 0 m/s (bkz. 03).

### 2.6 Cfg sabitleri — 25 tanesi, ne işe yararlar

| Sabit | Değer | Görevi |
|---|---|---|
| `LOOP_HZ` | 20.0 | Yasa döngü frekansı |
| `RANGE_SET` | 11.0 | İstasyonun slant menzili (pose tatlı noktası) |
| `ISTASYON_ELEV_DEG` | 15.0 | İstasyonun LOS yükselişi (kamera tilt'inden AYRI) |
| `CENTER_ELEV_DEG` | 25.0 | Kamera tilt'i — ölçüm/tanı referansı |
| `TRACK_MIN_SPD` | 3.0 | Üstünde istasyon hız yönünün gerisi, altında LOS gerisi |
| `LOOKUP_MIN_ALT` | 8.0 | Alçalma tabanı (yere çakılma koruması) |
| `KP_H` | 0.8 | Yatay konum hatası → hız (1/s) |
| `KD_H` | 0.60 | **LEAD** katsayısı (bkz. 2.5) |
| `IC_KAYMA` | 14.0 | İç-daire kayması (m) |
| `IC_OMEGA_REF` | 0.15 | Bu dönüş hızında tam kayma |
| `IC_OMEGA_EMA` | 0.15 | Açısal hız yumuşatma |
| `IC_ORAN` | 0.0 | Yarıçap-oranlı kayma (0 = kapalı, sabit metre geçerli) |
| `IC_KAYMA_MAX` | 25.0 | Oranlı kaymanın tavanı |
| `IC_R_MIN` | 15.0 | Bundan dar yarıçap kestirimi güvenilmez |
| `KP_Z` | 1.0 | Dikey konum hatası → hız (1/s) |
| `VZ_MAX` | 6.0 | Dikey hız tavanı |
| `V_MAX` | 18.0 | Yatay hız tavanı |
| `MAX_ACCEL` | 12.0 | Komut hızı değişim sınırı (m/s²) |
| `DERIV_EMA` | 0.2 | Hata türevi yumuşatma |
| `YAW_DEADBAND` | 3° | Yaw ölü bandı |
| `YAW_RATE_MAX` | 120°/s | Yaw komut rampası |
| `POS_EMA` | 0.4 | Hedef konum EMA |
| `VEL_EMA` | 0.3 | Hedef hız EMA |
| `HOLD_S` | 3.0 | Bu süre donuk telemetri → DROPOUT |
| `HANDOFF_RANGE` | 20.0 | d_h altında durum = KILIT (görsel devir bandı) |

Bunların **22'si DoW'da aynen kullanılıyor**; 3'ü değişti (03'te gerekçeleri).

`V_MAX`'ın kendi tarihçesi öğretici: 20 → 28 (telemetri 4→25 Hz düzelince hedefin
gerçek hızı ortaya çıktı) → **18** (28 m/s'de `MAX_ACCEL=12` ile durma mesafesi
32.7 m; istasyon standoff'u ise 10 m — araç geometrik olarak zamanında
yavaşlayamıyor, hedefin etrafında savruluyordu).

---

## 3. `common.py` — ORTAK KATMAN

Küçük ama kritik dosya. İçindekiler:

- `clamp`, `normalize_angle`, `vec3_len`, `timestamp_ms`
- `limit_acceleration(...)` — komut hız vektörünü önceki komuta göre `max_a·dt`
  ile sınırlar (tek 3B tavan; GPS fazı bunu kullanır)
- `limit_acceleration_split(...)` — yatay/dikey AYRI tavan (görsel faz için;
  gerekçe: quad ileri ivmelenmek için burnunu eğer, kamera düşer; yukarı
  ivmelenmek burun eğimi gerektirmez)
- **`send_velocity(conn, vx, vy, vz, yaw)`** — MAVLink
  `SET_POSITION_TARGET_LOCAL_NED`, frame `MAV_FRAME_LOCAL_NED`,
  **typemask 3015**

Typemask'in açılımı (neden 3015):
```
bit 0,1,2   = 1  → pozisyon YOK SAY
bit 6,7,8   = 1  → ivme YOK SAY
bit 9       = 1  → force YOK SAY
bit 11      = 1  → yaw_rate YOK SAY
------------------------------------
aktif kalan: vx, vy, vz + yaw (MUTLAK, radyan)
1+2+4+64+128+256+512+2048 = 3015
```

**Dönüştürücünün bağlandığı nokta tam burasıdır.** Yasa `send_velocity`'yi
çağırır; biz o ismi çalışma anında değiştiririz:

```python
import control.guidance.gps_guidance as gg
gg.send_velocity = dow_kopru.send_velocity     # yasaya TEK KARAKTER dokunulmaz
```

---

## 4. `guidance_core.py` — KADRAJ ÖLÇÜMÜ

`hedef_kadraj_hatasi(hedef_pos, iris_pos, roll, pitch, yaw)` → hedefin kamera
karesindeki yerini hesaplar: gövde çerçevesinde azimut (`yaw_hata`), yükseliş
(`elev`), ve piksel konumu (`u`, `v`).

- Kamera modeli: `vision/geometry.py` (FOV 125°, 640×480, +25° yukarı tilt)
- Talon boyutları: gövde 0.81 m, kanat açıklığı **1.28 m** (collision mesh'ten
  ölçülmüş — bu sayı DoW dönüşümünde kritik rol oynadı, bkz. 03)
- **Komuta GİRMEZ** — yalnızca `gps_guidance.py:466`'da çağrılıp CSV'ye yazılır.
  Başarı ölçütüdür: "hedef kadrajın neresinde?"

---

## 5. `hedef_kestirim.py` — IMM (KULLANILMIYOR)

CV (sabit hız) + CA (sabit ivme) modellerini ortak 9 boyutlu durumda birleştiren
IMM filtresi. Yazılma gerekçesi dosya başlığında:

> Mevcut kestirici EMA konum + sonlu fark hızdır. Gerçekle kıyaslandığında:
> gerçek hız medyan 16.00 m/s ↔ kestirim 19.30 m/s → **1.21× ŞİŞİK**;
> std 0.82 ↔ 2.59 → **3.2× GÜRÜLTÜLÜ**.

**Ama `gps_guidance.py` bu dosyayı import etmiyor** — yasa hâlâ kendi EMA+sonlu
fark kestirimini kullanıyor. Biz de taşımadık (kullanıcı kararı: "yeni bileşen
eklemeden önce, zaten sistemin parçası olanı taşıyalım").

> ⚠️ İleride açılırsa dikkat: ω kestirimi düzelirse `IC_ORAN=0.27` istasyonu
> devir bandının DIŞINA atar (`d_h = √(10.6² + 25²) = 27.2 m > HANDOFF_RANGE=20`).
> IMM gelirse `IC_ORAN` kapalı kalmalı, `IC_KAYMA` tavanı ~17 m'yi aşmamalı.

---

## 6. ARDUPILOT NE YAPIYORDU — dönüştürücünün doldurduğu boşluk

Yasa `send_velocity` ile hız komutu yollar; gerisini ArduCopter yapardı:

| ArduCopter katmanı | Ne yapar | DoW'da karşılığı |
|---|---|---|
| **Jerk-sınırlı şekillendirme** (`WPNAV_JERK=4`) | Komut hızını yumuşat | ❌ **YOK** (ölçüldü: bu turda zararsız) |
| **Hız PID → ivme** (`PSC_VELXY_P/I`) | Hız hatasını ivmeye çevir | ✅ Köprü: trim ileri-besleme + PI |
| **İvme → yatış açısı** (`açı = atan(a/g)`) | İvmeyi açıya çevir | ✅ Köprü: ölçülmüş trim eğrisi |
| **Dikey kaskad** | Konum→hız→itki | ✅ Köprü: TRIM + FF + PI |
| **Yaw denetleyicisi** | Mutlak açı → dönüş | ✅ Köprü: P + sarma + kaçak kırpma |
| **EKF durum kestirimi** | Konum/hız füzyonu | ⚠️ DoW SDK doğrudan veriyor (temiz) |

**Bir de ayrı hat:** kalkış/konum. Gazebo'da `drone_functions.py:90`
`_send_position_setpoint()` aynı MAVLink mesajını **POZİSYON** typemask'iyle
gönderiyordu (`takeoff_to_z`, `hold_position`, `_move_to`). DoW'da pozisyon
komutu **yok** → köprü kendi AGL-kapılı açık-döngü tırmanışını yapar.

---

## 7. ÖZET

Gelen sistem şu üç parçadan ibaret:
1. **Yasa** (`gps_guidance.py`) — istasyon geometrisi + ileri-beslemeli PD
2. **Gönderici** (`common.send_velocity`) — MAVLink hız setpoint'i
3. **Ölçüm** (`guidance_core`) — kadraj hatası, komuta girmez

Dönüştürücünün işi (2) ve ArduPilot'un altındaki her şeyi DoW için yeniden
kurmak; (1) ve (3)'e **dokunmamak**.

→ Devamı: **[02_DONUSTURUCU.md](02_DONUSTURUCU.md)**

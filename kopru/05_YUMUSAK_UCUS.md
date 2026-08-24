# 05 — GAZEBO'DAN DRONES OF WAR'A: dönüşüm nasıl çalışıyor

> **Bu belge tek başına okunur.** Gazebo/ArduPilot için yazılmış bir güdüm
> yasasının, hiç değiştirilmeden, Drones of War'da nasıl uçtuğunu anlatır:
> veriyi nasıl okuyoruz, komutu nasıl yazıyoruz, iki platform arasındaki fark
> ne, ve araç neden sarsıntısız hareket ediyor.
>
> Derinlemesine referanslar: [01_GAZEBO_KAYNAK](01_GAZEBO_KAYNAK.md) (yasanın
> iç yapısı) · [02_DONUSTURUCU](02_DONUSTURUCU.md) (satır satır dönüştürücü) ·
> [03_OLCUMLER](03_OLCUMLER.md) (her sabitin ölçümü)

---

## 1. Tek cümlelik özet

Yasa **ne isteyeceğini** söyler ve hiç değişmez; köprü **nasıl yapılacağını**
söyler ve platforma göre ölçülerek kurulur.

```
Gazebo:  yasa → MAVLink → ArduCopter → motorlar
DoW:     yasa → KÖPRÜ   →   (yok)    → stick komutları
                  ↑
        ArduCopter'ın yerini alan katman
```

Yasa dosyaları hash ile doğrulanır, **tek karakter değişmedi**:

```
gps_guidance.py   720 satır   BİREBİR
common.py         106 satır   BİREBİR
guidance_core.py  612 satır   BİREBİR
hedef_kestirim.py 250 satır   BİREBİR
```

---

## 2. İki platform yan yana — asıl fark burada

| | **Gazebo / ArduPilot** | **Drones of War** |
|---|---|---|
| **Bağlantı** | MAVLink (pymavlink) | TCP soket, `127.0.0.1:12345` |
| **Komut arayüzü** | `SET_POSITION_TARGET_LOCAL_NED` typemask 3015 → **hız + mutlak yaw** | `set_control_surfaces(thr, pitch, roll, yaw)` → **normalize açı**, hepsi −1..+1 |
| **Hız denetleyicisi** | **ArduCopter'da var** — hızı motora çevirir | **YOK** — köprü yapar |
| **Konum birimi** | metre | **santimetre** |
| **Hız birimi** | m/s | **cm/s** |
| **Açı birimi** | radyan | **derece** |
| **Çerçeve** | NED (x kuzey, y doğu, **z aşağı**) | dünya, **z yukarı** |
| **Zemin kotu** | 0 | ~4836 cm (harita yüksekliği) |
| **Hedef telemetrisi** | temiz | **bozuk**: gürültü, sıçrama, kesinti, gecikme; 5 Hz |
| **Açı modu** | — | Angle mode; ±1.0 = **60°** |
| **Gaz kanalı** | — | **asimetrik**; hover 0 değil (ölçüm: **−0.60**) |
| **Çarpma sensörü** | `sim_truth.temas` var | **yok** (oyun "mission complete" yazar) |

Bu tablodaki her satır köprüde bir dönüşüme karşılık gelir. En pahalı olanı
üçüncü satır: **ArduCopter'ın hız denetleyicisi yok**, onu baştan yazmak
gerekti (bölüm 6).

---

## 3. OKUMA TARAFI — DoW'u yasanın anlayacağı dile çevirmek

Yasa iki fonksiyon bekler ve ikisi de **SI + NED** ister:

```python
get_iris()  -> {x, y, z, roll, pitch, yaw, vx, vy, vz}   # m, m/s, rad, NED
get_plane() -> {x, y, z, yaw, frozen}                     # m, rad, NED
```

DoW ise cm, cm/s, derece ve z-yukarı verir. Köprü aradaki adaptördür.

### 3.1 Çerçeve dönüşümü — tek yerde, çift yönlü

```python
def dow_to_ned_vek(v):    return (v[0], -v[1], -v[2])     # y ve z işaret ters
def ned_to_dow_vek(v):    return (v[0], -v[1], -v[2])     # kendi tersi
def dow_yaw_to_ned(y):    return sarmala_pi(-y)           # yaw işareti ters
```

**Neden `diag(1, −1, −1)`:** DoW'un dünya çerçevesi z-yukarı ve y ekseni NED'in
tersine bakar. z'yi çevirmek (yukarı→aşağı) sağ-el kuralını bozar; y'yi de
çevirmek onu geri kazandırır.

**Doğrulama:** `det(diag(1,−1,−1)) = +1` — yani bu bir **öz rotasyon**, ayna
yansıması değil. Ayna olsaydı bütün dönüşler ters yöne çalışırdı. Fonksiyon
kendi tersidir; birim test bunu kilitler:
`ned_to_dow(dow_to_ned(v)) == v`.

### 3.2 Dikey orijin kaydırması — kolay gözden kaçan tuzak

DoW'da zemin ~4836 cm'dedir; Gazebo'da 0. Yasa "yere çakılma tabanı",
"tırmanma bütçesi" gibi kararları **AGL varsayarak** verir. Ham z verilseydi
yasa kendini sürekli 48 metre yukarıda sanardı.

```python
"z": -(p[2] - NED_ZEMIN_M)     # zemin görev başında okunur, sonra sabit
```

> Bu, ilk ölçüm koşusunda **aracın düşmesine** yol açan hataydı: dünya-Z'yi AGL
> sanmak. Zemin referansı, AGL<15 m koruması ve ışınlanma tespiti o kazadan
> sonra eklendi.
>
> ⚠ Hıza kaydırma **uygulanmaz** — sabit ofsetin türevi sıfırdır.

### 3.3 `get_iris()` — kendi durumumuz

```python
p, v, (roll, pitch, yaw) = self._drone_dow()      # cm, cm/s, derece
pn = dow_to_ned_vek(p);  vn = dow_to_ned_vek(v)
return {"x": pn[0], "y": pn[1], "z": -(p[2] - NED_ZEMIN_M),
        "vx": vn[0], "vy": vn[1], "vz": vn[2],
        "roll": roll, "pitch": pitch, "yaw": dow_yaw_to_ned(yaw)}
```

**pitch/roll işareti aynen geçer.** İki konvansiyonda da burun-yukarı ve
sağ-kanat-aşağı pozitiftir. Ayrıca bu ikisi yalnız **kadraj ölçümünü** besler,
komut yoluna hiç girmez — yanlış işaret uçuşu bozmaz, sadece telemetriyi.

> Bilinen açık: `roll` işaretinin DoW'da ters olduğu ölçüldü ama düzeltilmedi,
> çünkü yalnız kadraj ölçümünü etkiliyor. Kayıtlı, karar bekliyor.

### 3.4 `get_plane()` — hedef, ve bozuk GNSS yolu

Burası Gazebo'dan **en çok ayrılan** yer. DoW hedef telemetrisi kasıtlı olarak
bozuktur: gürültü, sabit kayma, ani sıçrama, kesinti, gecikme — ve 5 Hz.

```python
ham = tuple(x / CM for x in ham_cm)             # cm → m
donuk = (ham == self._son_hedef_ham)            # paket tazelendi mi
if GNSS_DUZELTICI_AKTIF and not truth_modu:
    if not donuk:                                # ⚠ SADECE taze pakette
        self._gnss_cikti = self._gnss_guncelle(ham_cm)   # CT-EKF
    if self._gnss_cikti is not None:
        p = self._gnss_cikti
pn = dow_to_ned_vek(p)
return {"x": pn[0], "y": pn[1], "z": -(p[2] - NED_ZEMIN_M),
        "yaw": dow_yaw_to_ned(yaw_dow), "frozen": donuk}
```

Üç ayrıntı önemli:

**① Filtre yalnız taze pakette ilerler.** Donmuş kare filtreye zaman
ilerletirse EKF, olmayan bir hareketi ekstrapole eder ve hedefi kaydırır.
5 Hz telemetriyi 50 Hz okuduğumuz için karelerin %90'ı donuktur.

**② `frozen` bayrağı yasaya taşınır.** Yasanın kendi tazelik kapısı vardır
(`raw != last_raw`); iki mekanizma aynı semantiktedir, çakışmaz.

**③ Zarif bozulma.** CT-EKF ısınmada veya hatada `None` döner; o zaman **ham**
konuma düşülür ve konsola gürültülü uyarı yazılır — sessizce yanlış veri
üretilmez.

**Kaynak seçici (arayüzden canlı):**

| Arayüzde | Köprü ne okur | Ölçülen oturmuş menzil |
|---|---|---|
| **v2 (İnovasyonlu J)** | bozuk kanal + CT-EKF | **39.0 m** |
| **🎯 Gerçek GPS (test)** | truth kanalı, filtre baypas | **7.1 m** |

Bu **5.5 katlık fark ölçüldü** (aynı yasa, aynı ayar, tek fark kaynak).
Yarışma koşulu bozuk GPS'tir; truth yalnız teşhis kanalıdır.

---

## 4. YAZMA TARAFI — hızı stick'e çevirmek

Yasa 20 Hz'de tek şey yapar:

```python
send_velocity(conn, vx, vy, vz, yaw)     # NED m/s + mutlak yaw
```

Köprü bunu değiştirir — **tek bağlama noktası**:

```python
gg.send_velocity = dow_kopru.send_velocity      # conn artık DowKopru örneği
```

`send_velocity` yalnız **setpoint yazar**; kontrol ayrı ve daha hızlı bir
döngüde koşar (bölüm 7). Gazebo'da bu satır MAVLink paketi gönderiyordu;
DoW'da bir sözlüğe hız yazıyor. Yasanın haberi yok, olması da gerekmiyor.

Bundan sonrası — hızın stick'e dönüşmesi — bölüm 5, 6 ve 7'nin konusu.

---

## 5. Neden sarsıntı yok: beş katman

Naif çözüm ("hız hatasını al, kazançla çarp") iki türlü de batar:

* **kazanç küçük** → geç tepki, hedefin gerisinde sürükleniş
* **kazanç büyük** → salınım: aş, geri dön, tekrar aş

Kamera gövdeye sabit olduğu için salınım doğrudan görüntüye yansır ve tespit
kopar. Aşağıdaki katmanlar bu ikilemi çözer.

### Katman 1 — Yasa stick değil hız düşünür

Hız fiziksel ve süreklidir; ani sıçraması için aracın gerçekten sıçraması
gerekir. "Komut zıplaması" daha en baştan yoktur.

### Katman 2 — Yasanın kendi frenleri

```python
MAX_ACCEL    = 12.0 m/s²    # komut hız vektörü tik başına bu kadar değişir
YAW_RATE_MAX = 120°/s       # yaw KOMUTU hedefe adım adım yürür
```

Dönüşlerin akıcı olmasının asıl sebebi ikincisidir:

```python
yaw_err = normalize_angle(bearing - cmd_yaw)
if abs(yaw_err) > YAW_DEADBAND:                    # 3°
    step    = clamp(yaw_err, ±YAW_RATE_MAX·dt)     # 20 Hz'de ±6°/tik
    cmd_yaw = normalize_angle(cmd_yaw + step)
```

Hedef 90° yana kaçsa bile komut **atlamaz**, sabit hızla yürür.

> **Ölçülmüş kanıt:** faz girişinde `cmd_yaw` eskiden doğrudan `bearing` ile
> başlatılıyordu. Görsel fazdan GPS'e dönüşte hedef genelde arkada kalır ve bu,
> tek karede **100–160°** yaw komutu sıçraması demekti (12 faz girişinin 6'sında
> >60°). Araç bunu yakalamak için yaw'ı doyuruyor, motorlar yaw torkuna gidince
> roll/pitch yetkisi kalmıyor ve **takla** atıyordu. Yeni sürüm `cmd_yaw`'ı
> aracın mevcut yaw'ıyla başlatıyor; normal takipte fark yok (burun zaten
> hedefteyken mevcut yaw ≈ bearing).

### Katman 3 — Ölçülmüş trim + küçük PI (köprünün kalbi)

Önce **ölçtük**: DoW'da stick ↔ yerleşik hız ilişkisi

```
dv/dstick ≈ 87.8   (m/s per stick birimi)
```

Ondan trim tablosu çıktı:

```python
YATAY_TRIM_NOKTA = ((0.0, 0.00), (8.7,  0.10), (13.2, 0.15),
                    (17.6, 0.20), (26.2, 0.30), (32.9, 0.45))
```

Dikeyde de aynısı yapıldı ve **SDK belgesinin yanlış olduğu bulundu** — belge
hover gazını 0 diyordu, ölçüm **−0.60** dedi:

```python
THR_TRIM = -0.60
```

Yasa "14 m/s" dediğinde köprü **anında** onu üreten stick'i basar; PI yalnız
kalan artığı toplar:

```python
sp_fwd, sp_right = dunya_to_govde(v_sp[0], v_sp[1], yaw)     # gövde çerçevesi
e_fwd = sp_fwd - olculen_fwd
pitch = yatay_trim_stick(sp_fwd) + KP_VH·e_fwd + I_fwd
thr   = THR_TRIM + FF_VZ·vz_sp + KP_VZ·e_vz + I_vz
```

```python
KP_VH = 0.024   KI_VH = 0.012        # yatay — çok küçük
KP_VZ = 0.22    KI_VZ = 0.15         # dikey
```

**Kazançlar neden bu kadar küçük olabiliyor?** Ağır işi ileri-besleme yapıyor:

* **küçük kazanç → salınım yok**
* **ileri-besleme → gecikme yok**

Saf geri-beslemede bu ikisi birbirinin düşmanıdır; ileri-besleme ikisini aynı
anda mümkün kılar.

### Katman 4 — İntegral bant kapısı (taşmayı öldüren)

```python
E_VH_INT_BAND = 2.5     # m/s; integral YALNIZ |hata| bu bandın içindeyken birikir
I_VH_MAX      = 0.15    # integral yetkisi tavanı
```

> **Hikâyesi öğretici:** basamak yanıtında taşma vardı. Klasik refleks kazancı
> düşürmekti — **denendi, taşma ARTTI.** CSV anatomisi sebebi gösterdi: sorun
> kazanç değil **integral sarımı**ydı. Büyük hata sürerken integral doluyor,
> hedefe varıldığında hâlâ boşalmamış oluyor ve aracı öteye itiyordu.

Bant kapısıyla hata büyükken (10 m/s) integral **hiç** birikmez; yalnız hedefe
yaklaşınca (<2.5 m/s) son kırıntıyı kapatır. Stick doyumdayken de dondurulur.

### Katman 5 — Son emniyet: tik başına değişim sınırı

```python
MAX_DELTA = 0.05        # 50 Hz'de tik başına en fazla bu kadar
```

Stick 0'dan 1'e **0.4 saniyeden hızlı gidemez**. Dört kanala da, tam gönderim
anında:

```python
def _uygula(self, thr, pitch, roll, yaw):
    thr   = rate_limit(thr,   önceki, MAX_DELTA)
    pitch = rate_limit(pitch, önceki, MAX_DELTA)
    roll  = rate_limit(roll,  önceki, MAX_DELTA)
    yaw   = rate_limit(yaw,   önceki, MAX_DELTA)
    sdk.set_control_surfaces(thr, pitch, roll, yaw, True)   # dördü ATOMİK
```

**Atomik olması da önemli:** ayrı ayrı gönderilse araç bir an tutarsız bir
komut bileşimi görürdü (yeni pitch + eski roll gibi).

---

## 6. ArduCopter'da olup bizde olmayan — ve yerine ne koyduk

| ArduCopter'ın yaptığı | Köprüde karşılığı |
|---|---|
| Hız → eğim → motor karışımı | **Trim tablosu + PI** (katman 3) |
| İvme sınırlama | Yasada `MAX_ACCEL` + `MAX_DELTA` (katman 2, 5) |
| Yaw hız denetimi | `KP_YAW` + `YAW_MAX` stick tavanı + hata kırpma |
| Konum tutma / hover | `THR_TRIM = −0.60` (ölçülen) |
| Duruş stabilizasyonu | **Oyun motoru** (DoW Angle mode) |
| Failsafe / arm mantığı | `BAYAT_S = 0.30 s` + `set_arm` |

Son satır önemli: DoW'un kendi Angle mode'u duruş stabilizasyonunu yapar, yani
tam bir uçuş kontrolcüsü yazmamız gerekmedi. Bizim doldurduğumuz boşluk
**hız denetleyicisi** katmanıdır.

---

## 7. Mimari: 20 Hz düşünce, 50 Hz eylem

```
gps_guidance thread (20 Hz)              web/server.py döngüsü (50 Hz)
   hesapla → send_velocity                     AvciKontrol.adim()
              ↓                                       ↓
        set_hiz_ned (yalnız setpoint)        KopruGudum.adim() → DowKopru.adim()
                                                       ↓
                                        FF+PI → rate_limit → set_control_surfaces
```

Yasa saniyede **20 karar** verir, stick'ler saniyede **50 kez** güncellenir.
Aradaki 30 tik rate-limit sayesinde rampa üretir — çıkış merdiven değildir.

Ayrı thread'in ikinci faydası: yasa ağır hesap yaparken (filtre, kestirim)
stick üretimi durmaz.

**Bayat koruması:** setpoint `BAYAT_S = 0.30 s` içinde tazelenmezse köprü
güvenli bırakmaya geçer — yasa thread'i ölürse araç son komutu sonsuza kadar
sürdürmez.

---

## 8. Küçük ama kritik: gövde çerçevesine çevirme

```python
sp_fwd, sp_right = dunya_to_govde(v_sp_dow[0], v_sp_dow[1], yaw_dow)
```

Araç dönerken dünya eksenleri gövdeye göre sürekli kayar. Çevirme olmasaydı
aynı dünya-komutu dönüş boyunca farklı stick'lere denk gelir, süreksizlik
doğardı. Bu sayede dönüş sırasında "ileri" ileri kalır.

---

## 9. Kaçak koruması

```python
YAW_HATA_MAX = 90°      # üstündeki yaw hatası kırpılır
YAW_MAX      = 0.85     # stick tavanı (0.60 → 0.85; ölçüm 143°/s gerektiriyordu)
PITCH_MAX = ROLL_MAX = 0.75
```

Yaw hatası 90°'yi aşarsa kırpılır; aksi halde `KP_YAW · hata` stick'i doyurur,
motorlar yaw torkuna gider, roll/pitch yetkisi kalmaz. Katman 2'deki yürüyen
yaw komutu bunu zaten büyük ölçüde engeller — bu ikinci emniyettir.

---

## 10. Özet tablo — hangi katman neyi çözüyor

| Sarsıntı kaynağı | Çözen katman | Değer |
|---|---|---|
| Komut sıçraması | Yasa hız üretir | — |
| Ani hız değişimi | İvme sınırı (yasa) | `MAX_ACCEL = 12 m/s²` |
| Dönüşte yaw atlaması | Yürüyen yaw komutu (yasa) | `YAW_RATE_MAX = 120°/s` |
| Geç tepki | Ölçülmüş trim ileri-beslemesi | `dv/dstick = 87.8` |
| Salınım | Küçük PI kazançları | `KP_VH = 0.024` |
| Taşma | İntegral bant kapısı | `E_VH_INT_BAND = 2.5 m/s` |
| Kalan her şey | Tik başına sınır | `MAX_DELTA = 0.05 @ 50 Hz` |
| Basamaklı çıkış | İki hızlı mimari | 20 Hz / 50 Hz |
| Dönüşte eksen kayması | Gövde çerçevesine çevirme | `dunya_to_govde` |
| Yaw doyumu → takla | Hata kırpma + stick tavanı | `YAW_HATA_MAX = 90°` |

---

## 11. Doğrulama — iddia değil ölçüm

Uçtan uca denetim (`docs/kopru_denetim.md`): yasanın istediği ile köprünün
ürettiği yan yana kondu.

```
çerçeve sapması   0.00 m        NED ↔ DoW dönüşümü kayıpsız
komut sapması     0.013 m/s     yasanın istediği ↔ köprünün ürettiği
stick eşleşmesi   tam
```

Görev başarımı: kilit isterisi (%5 kutu oranı, 10 sn'de 5 sn) gerçek GPS ile
**3/3** sağlandı.

Türetilmiş ayarlar (hepsi ölçümle, seçimle değil):

```
RANGE_SET     6.9 m    kutu oranı %6.48 (eşik %5); Gazebo'nun 11 m'si DoW'da %3.03 verirdi
ISTASYON_ELEV 25°      → 6.25 m arka + 2.92 m alt; ölçülen 2.89 m
V_MAX         22 m/s   Gazebo'nun karşı-örneği yanal ivme kısıtıydı, DoW'da bağlamıyor
IC_KAYMA      0        ölçüm: istasyon zaten 13.8 m'de, iç kayma gereksiz
```

---

## 12. En önemli nokta

**Bu katmanların hiçbiri güdüm yasasında değil, köprüdedir.**

Trim tablosu, PI, bant kapısı, rate limit, çerçeve çevirimi, GNSS düzeltici
kancası — hepsi `kopru/dow_kopru.py` içinde. Kayran'ın yasası ArduCopter'ın hız
denetleyicisine güveniyordu; DoW'da o katman olmadığı için yerine bu kondu.

Yasa dosyaları hash'le doğrulanır ve değişmez. Değişen yalnız "nasıl" kısmı —
ve o kısım tahminle değil, **DoW'da uçarak ölçülerek** kuruldu.

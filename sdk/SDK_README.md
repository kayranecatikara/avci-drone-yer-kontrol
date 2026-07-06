# Drone Of War - Yarışmacı SDK

Drone Of War yarışmasına hoş geldiniz! Bu paket, otonom drone kontrolü geliştirmeniz için gereken temel Python SDK'sını ve test araçlarını içerir.

## 📦 Paket İçeriği
- `drone_sdk.py`: Oyunla haberleşmeyi sağlayan ana kütüphane. (Yarışmacıların import edeceği dosya)


## 🚀 Hızlı Başlangıç

Dronunuzu kontrol etmek için kendi Python dosyanızı oluşturun ve SDK'yı import edin:

```python
import drone_sdk as drone
import time

# 1. Oyuna bağlan
if drone.connect():
    # 2. Motorları aktif et
    drone.set_arm(True)
    
    while True:
        # 3. Telemetri verilerini al
        konum = drone.get_drone_location()
        hedef = drone.get_target_location()
        hiz = drone.get_drone_speed()
        
        # 4. Kendi AI mantığınızı buraya yazın
        # Örnek: Basitçe yüksel
        drone.set_throttle(0.6)
        
        time.sleep(0.02) # 50Hz kontrol döngüsü
```

## 🛠️ Temel Fonksiyonlar

### Kontrol (Setters)
- `set_arm(bool)`: Dronu aktif/pasif yapar.
- `set_throttle(-1.0 - 1.0)`: **Dikey komut** (Angle Mode). `+1` = maksimum hızla **tırman**, `0` = **hover** (irtifa korunur), `-1` = yerçekimi telafisi **tamamen kapanır → dron FİZİKLE (yerçekimiyle) serbest DÜŞER**. `0` ile `-1` arası kısmi telafidir (yumuşak/kontrollü alçalma). Maksimum **tırmanma** hızı sabit **120 km/h** ile sınırlıdır; alçalma serbest düşüş olduğu için bu sınıra tabi değildir.
- `set_pitch(-1.0 - 1.0)`: İleri/Geri **yatış açısı** (Angle Mode).
- `set_roll(-1.0 - 1.0)`: Sağ/Sol **yatış açısı** (Angle Mode).
- `set_yaw(-1.0 - 1.0)`: Kendi ekseninde dönüş.
- `set_control_surfaces(throttle, pitch, roll, yaw, arm)`: Tüm eksenleri **tek komutta** gönderir (önerilir; ara karelerde tutarsızlığı önler).

### Telemetri (Getters)
- `get_drone_location()`: (x, y, z) konumu.
- `get_drone_rotation()`: (roll, pitch, yaw) rotasyonu.
- `get_drone_speed()`: Anlık hız (cm/s).
- `get_drone_altitude()`: Anlık irtifa (Z).
- `get_target_location()`: Hedefin (x, y, z) konumu.
- `get_target_speed()`: Hedefin hızı (cm/s).

## 💡 Önemli Notlar
- Oyunun çalışıyor ve "Play" modunda olması gerekmektedir.
- Varsayılan bağlantı adresi `127.0.0.1:12345` portudur.
- **Kamera tilt: 25° yukarı.** FPV kamerası burnu 25° yukarı eğik bakar.
- **Kamera FOV: 125°** (görüş alanı).
- Hedefi görüntü merkezine almak veya nişan hesaplamak için kamera tilt açısını (25°) pitch hesaplarında telafi etmeniz gerekebilir.
- Kontrol döngüsünün `0.02` saniye (50Hz) civarında olması stabilite için önerilir.

## 🎯 Hedef İHA — Talon
Yarışmadaki hedef platform **Talon İHA**'dır. Fiziksel boyutları:

| Parametre | Değer |
|-----------|-------|
| Kanat açıklığı | **1718 mm** |
| Gövde uzunluğu | **1100 mm** |

## ✈️ Uçuş Modeli — ANGLE MODE
Dron **Angle (self-leveling) modunda** uçar. Bu, `set_pitch` / `set_roll` ile gönderdiğiniz değerin bir **dönüş hızı (acro/rate)** değil, bir **hedef yatış açısı** olduğu anlamına gelir:
- `set_pitch(1.0)` → dron **ileri maksimum yatış açısına** eğilir, stick bırakılınca kendini düzler.
- `set_roll(1.0)` → dron **sağa maksimum yatış açısına** yatar.

Uçuş parametreleri **sabittir ve yarışmacı tarafından değiştirilemez** (oyun içine gömülüdür; herkes için aynıdır):

| Parametre | Değer | Anlamı |
|-----------|-------|--------|
| Maksimum yatış açısı (pitch/roll) | **60°** | Tam stick (±1.0) verildiğinde ulaşılan açı. Yatay hızı belirler. |
| Yatış hızı (interpolasyon) | **5.0** | Drona hedef yatış açısına ne kadar hızlı gideceği. |
| Maksimum **toplam** hız (düz uçuş + tırmanma) | **120 km/h** | Normal uçuşta dronun toplam (yatay+dikey birleşik) hızı bu değeri aşamaz. |
| Maksimum tırmanma hızı | **120 km/h** | `set_throttle(+1)` iken ulaşılan dikey hız. |

> **Toplam hız normalize edilir:** Yatay (ileri) ve dikey (tırmanma) hareket aynı anda tam verilse bile dronun **toplam hızı 120 km/h'ı aşmaz** (bileşenler birlikte sınırlanır).
>
> **Dalış istisnası:** Bu sınır yalnızca düz uçuş/tırmanışta geçerlidir. **Dalışta (burun aşağı + serbest düşüş)** dikey bileşen sınırlı olmadığı için **toplam hız 120 km/h'ı aşabilir.**

### Throttle = Dikey Komut (önemli)
Throttle artık bir itki oranı değil, bir **dikey komut**tur ve **yatay hareketten bağımsızdır** (yatay hareket sadece pitch/roll yatışından gelir):

- `set_throttle(1.0)` → maksimum hızla **tırman** (sabit **120 km/h** ile sınırlı).
- `set_throttle(0.0)` → **hover** (irtifasını korur; ekstra gaz gerekmez).
- `set_throttle(-1.0)` → yerçekimi telafisi **tamamen kapanır**, dron **fizikle (yerçekimiyle) serbest düşer**.
- `0.0` ile `-1.0` arası → telafi **kademeli** kalkar; yani kontrollü/yumuşak bir alçalma sağlar.

> Not: Tırmanma hızı sabit **120 km/h** ile sınırlıdır, fakat alçalma gerçek bir serbest düşüş olduğu için bu sınıra tabi değildir.

## 📡 Telemetri Hakkında — Gerçekçi Sensör Davranışı (Bilgilendirme)

> **NOT (Önemli):** Aşağıdaki davranışlar yarışmanın bir parçasıdır ve **sunucu (oyun) tarafında**
> otomatik olarak uygulanır. Bunlar yarışmacı tarafından **açılıp kapatılamaz, ayarlanamaz veya
> kapatılamaz**; SDK içinde bunları değiştiren bir fonksiyon **yoktur**. Bu bölüm yalnızca
> bilgilendirme amaçlıdır.

Gerçek bir İHA'da GPS/sensör verisi hiçbir zaman kusursuz değildir. Bu yarışmada da telemetri
verisi **bilerek gerçek dünya koşullarını taklit edecek** şekilde bozulabilir. Karşılaşabileceğiniz
durumlar şunlardır:

- **Düşük güncelleme hızı (hedef GPS):** Hedef (Talon) konum/hız telemetrisi gerçek bir GPS gibi **saniyede 5 kez (5 Hz)** güncellenir. Kendi dronunuzun telemetrisi tam hızda ve temiz gelir.
- **Ölçüm gürültüsü:** Konum, irtifa ve hız değerleri sürekli küçük rastgele sapmalar (titreme) içerebilir.
- **Sabit kayma (drift/offset):** Veride zamanla ortaya çıkan, sabit kalan küçük bir konum kayıklığı olabilir.
- **Ani sıçramalar (spike):** Değerler kısa bir an için gerçek dışı bir noktaya fırlayıp sonra düzelebilir.
- **Sinyal kesintisi (dropout):** Telemetri kesintisi **30. saniyeden sonra** başlayacak şekilde ayarlanmıştır; bu noktadan itibaren **her 10 saniyede bir 2 saniye** veri gelmeyebilir. Bu sırada SDK bağlantıyı **koparmaz**; `get_` fonksiyonları son bilinen değeri döndürmeye devam eder.
- **Gecikme (latency):** Gelen veri, dronun **şu anki** değil, kısa bir süre önceki durumunu yansıtabilir.

> ⚠️ **Bu etkilerin tam değerleri, zamanlaması ve hangi anda devreye gireceği açıklanmaz ve
> yarışmalar/oturumlar arasında değişebilir.** Amaç, sabit bir desene göre değil, gerçek belirsizliğe
> dayanıklı bir sistem geliştirmenizdir.

**Öneri:** AI mantığınızı tek bir okumaya güvenerek değil; **filtreleme (örn. hareketli ortalama,
Kalman), yumuşatma ve tahmin (prediction)** kullanarak bu belirsizliklere dayanıklı kurun.

Başarılar dileriz!

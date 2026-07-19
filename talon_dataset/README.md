# 🛸 Talon UAV Dataset Generator - Kullanım ve Kurulum Kılavuzu

Bu proje, *Drones of War* oyunundaki **Talon UAV (BPP_AIDroneTalon_C)** insansız hava aracının yapay zeka eğitiminde (YOLO/Yansıtma vb.) kullanılmak üzere sıfır hareket bulanıklığı (motion blur) ve yüksek çözünürlükle (1920x1080) veri kümesi (dataset) toplamak amacıyla geliştirilmiş yüksek mühendislik ürünü bir otomasyon sistemidir.

> [!IMPORTANT]
> **Sistem Güvenlik Garantisi:** Geliştirilen modda yer alan **Akıllı Menü Algılayıcı (IsInMenu)** sayesinde, oyundaki ana menüler, drone seçim ekranları, lobiler veya duraklatma menüleri asla bozulmaz ve her zaman %100 görünür ve tıklanabilir kalır! 
> Ayrıca Python scripti **otomatik indeks kaldığı yerden devam etme** özelliğine sahiptir. Oyunu veya bilgisayarı kapatsanız bile eski çekimlerin üzerine yazmaz, kaldığı numaradan devam eder!

---

## 🛠️ Gereksinimler ve Ön Kurulum

Sistemi çalıştırmadan önce bilgisayarınızda aşağıdaki gereksinimlerin sağlandığından emin olun:

1. **Python 3.x:** [python.org](https://www.python.org/downloads/) adresinden indirin. Kurulum yaparken alt kısımda bulunan **"Add Python to PATH"** (Python'ı PATH'e ekle) kutucuğunu işaretlemeyi kesinlikle unutmayın!
2. **UE4SS (Unreal Engine Short Scripting):** Oyuna yüklü ve aktif durumda olmalıdır.

---

## ⚙️ Adım Adım Kurulum Rehberi

Modu oyuna entegre etmek tek tıkla otomatik olarak gerçekleştirilir:

1. Bu klasörü (`talon_dataset`) bilgisayarınızda güvenli bir yere çıkartın.
2. Klasörün boş bir yerinde **Sağ Tık -> Terminalde Aç** veya (PowerShell/CMD) açın.
3. Şu komutu yazarak otomatik yükleyiciyi çalıştırın:
   ```bash
   python setup_installer.py
   ```
4. Terminal ekranında sizden oyunun kurulu olduğu yerdeki `Win64` klasörünün yolu istenecektir. Klasörün yolunu yapıştırıp Enter'a basın:
   * *Örnek Klasör Yolu:* `C:\Users\Zeylo\Desktop\drones_of_war\Drones of War Teknofest\DronesOfWar\Binaries\Win64`
5. Kurulum başarıyla tamamlanacaktır (`[SUCCESS]` yazısını göreceksiniz).

---

## 🚀 Adım Adım Çalıştırma ve Kullanım Rehberi

Sistemi tam performansla çalıştırmak için aşağıdaki adımları sırasıyla PowerShell üzerinden uygulayın:

### 1️⃣ ADIM: Oyunu Başlatın
PowerShell terminalini açın ve oyunu Shipping modunda başlatmak için sırasıyla aşağıdaki komutları çalıştırın:

```powershell
# 1. Oyunun Binaries yolunu değişkene tanımlayın
$win64 = "C:\Users\Zeylo\Desktop\drones_of_war\Drones of War Teknofest\DronesOfWar\Binaries\Win64"

# 2. Oyun dizinine geçiş yapın
cd "$win64"

# 3. Oyunu başlatın
.\DronesOfWar-Win64-Shipping.exe
```

### 2️⃣ ADIM: Drone Arayüzünü (GUI) Açın (İsteğe Bağlı)
Drone kontrol arayüzünü (GUI) çalıştırmak için yeni bir PowerShell penceresi açın ve şu komutları yazın:

```powershell
# 1. Oyun ana klasörüne gidin
cd "C:\Users\Zeylo\Desktop\drones_of_war"

# 2. Python kontrol panelini (GUI) başlatın
python drone_gui.py
```

### 3️⃣ ADIM: Çekim Scriptini Başlatın
Talon'u uçurup yanına spectator (izleyici) kamerasıyla yaklaştıktan sonra, terminalinizde şu komutu yazarak otomatik fotoğraf çekim döngüsünü başlatın:

```powershell
python c:\Users\Zeylo\Desktop\talon_dataset\capture_controller.py
```
> [!NOTE]
> Bu script çalıştırıldığında terminal penceresi arka plana kaybolmasın diye kendini otomatik olarak simge durumuna küçültecektir. Oyuna geri dönün ve **F11** tuşuna basarak oyunu **Tam Ekran (Fullscreen)** moduna alın!

---

## ⚠️ Dikkat Edilmesi Gerekenler

* **F11 Tam Ekran:** Fotoğrafların tam 1920x1080 kalitesinde ve DPI kayması olmadan çekilebilmesi için oyun mutlaka **F11 ile Tam Ekran** modunda olmalıdır.
* **Serbest Uçuş Süresi:** Her dondurulmuş istasyonda 50 adet farklı açılardan fotoğraf çekildikten sonra, drone **tam 2.5 saniye** boyunca serbest uçuşa bırakılır ve oyun normal fiziklerine döner. 2.5 saniye sonra sistem onu yeni ulaştığı koordinatta tekrar yakalar ve çekime devam eder.
* **Sonsuz Döngü Güvenliği:** Sistemde bellek sızıntısı (memory leak) sıfırdır. Bilgisayarınızı saatlerce açık bıraksanız bile şişme veya donma yapmadan binlerce fotoğrafı diskinize biriktirir.

---

## 💻 Unreal Engine Konsol Komutları Kütüphanesi

Oyun içerisinde `~` veya `"` tuşuna basarak açılan Unreal Engine konsoluna yazabileceğiniz, Talon UAV sistemine özel olarak entegre edilmiş tüm komutlar ve işlevleri aşağıda listelenmiştir:

```javascript
/**
 * PlayersOnly
 * Sahnede bulunan tüm yapay zeka aktörlerini ve fizik hareketlerini dondurur. 
 * Sadece oyuncu kamerası (Spectator) hareket etmeye devam edebilir.
 */

/**
 * ToggleDebugCamera
 * Standart oynanış kamerasından bağımsız, serbest uçuş modunda hareket 
 * edebilen hata ayıklama (Debug) kamerasını aktif veya pasif hale getirir.
 */

/**
 * pause
 * Oyunu tamamen duraklatır (Pause). Tekrar girildiğinde kaldığı yerden devam eder.
 */

/**
 * talon_find
 * Sahnede aktif olan Talon UAV (BPP_AIDroneTalon_C) aracını arar, 
 * bulur ve koordinatlarını hafızaya kaydeder.
 */

/**
 * talon_stop
 * Talon UAV aracının hareketini ve motorlarını anında dondurur, havada asılı bırakır.
 */

/**
 * talon_x [değer]
 * Talon UAV aracının X eksenindeki (İleri/Geri) dünya koordinatını 
 * belirtilen değere eşitler.
 */

/**
 * talon_y [değer]
 * Talon UAV aracının Y eksenindeki (Sağ/Sol) dünya koordinatını 
 * belirtilen değere eşitler.
 */

/**
 * talon_up [değer]
 * Talon UAV aracının dikey yüksekliğini (Z ekseni) belirtilen değer kadar yukarı taşır.
 * Örnek kullanım: talon_up 2000
 */

/**
 * talon_down [değer]
 * Talon UAV aracının dikey yüksekliğini (Z ekseni) belirtilen değer kadar aşağı indirir.
 * Örnek kullanım: talon_down 3000
 */

/**
 * talon_move
 * Dondurulmuş veya durdurulmuş olan Talon UAV aracının fiziksel hareketini 
 * yeniden aktif hale getirir, serbest bırakır.
 */

/**
 * talon_front [değer]
 * Spectator kamerasını, Talon UAV'ın tam önüne belirtilen mesafe (birim) 
 * uzaklıkta konumlandırır.
 * Örnek kullanım: talon_front 4000
 */

/**
 * talon_pitch [değer]
 * Talon UAV aracının dikey yunuslama (Pitch) açısını belirtilen dereceye ayarlar.
 * Örnek kullanım: talon_pitch 20
 */

/**
 * talon_yaw [değer]
 * Talon UAV aracının yatay sapma (Yaw) açısını yön olarak belirtilen dereceye çevirir.
 * Örnek kullanım: talon_yaw 45
 */

/**
 * talon_roll [değer]
 * Talon UAV aracının kendi ekseni etrafında yatış (Roll) açısını ayarlar.
 * Örnek kullanım: talon_roll 30
 */

/**
 * talon_rot
 * Talon UAV aracının o anki tüm dönüş (Rotasyon - Pitch, Yaw, Roll) 
 * değerlerini konsola yazdırır.
 */

/**
 * talon_here
 * Talon UAV aracını anında spectator kamerasının bulunduğu güncel koordinatlara ışınlar.
 */
```

---

*Geliştiren Yapay Zeka Ortağın Antigravity - İyi çalışmalar ve başarılar dilerim abiciğim! 🚀*

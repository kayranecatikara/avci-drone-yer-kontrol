# Talon UAV Dataset Generator - Release Notes

## [TR] 🚀 Sürüm v1.1.0 - Çökme Koruması, Strict Diversity Guard & Ekstrem Açı & 3D Telemetri Sürümü

Talon UAV (`BPP_AIDroneTalon_C`) için sıfır hata, maksimum kararlılık ve %100 temiz görsellerle veri kümesi (dataset) toplamak üzere geliştirilen modumuz, **v1.1.0** sürümüne güncellendi! Bu güncelleme; saatler süren kesintisiz çalışma için tam kararlılık, benzerlik engelleme teknolojisi, genişletilmiş çekim alanı ve 3D konum verileri içeren otomatik telemetri dosyaları getiriyor.

### 🌟 Öne Çıkan Yenilikler ve Çözümler:

1. **🛡️ Fatal Error Çökme Çözümü (Spectator Lens Koruması):**
   - **Sorun:** Shipping sürümünde spectator kamerasının alt bileşenlerini gizleyen kodlar, kameranın ana görüntü merceğini (`UCameraComponent`) devre dışı bırakıyor ve oyunun çökmesine sebep oluyordu.
   - **Çözüm:** Merceği kapatan hatalı döngüler tamamen silindi. Artık kamera gizleme işlemi native ve %100 güvenli şekilde `K2_SetActorHiddenInGame(true)` ile yapılarak **Fatal Error çökmesi kökten çözüldü!**

2. **✨ Strict Diversity Guard (Sıkı Benzerlik Engelleme Filtresi):**
   - **Yenilik:** Çekilen fotoğrafların birbirine benzer olmasını önlemek için Lua tarafına akıllı bir benzerlik filtresi entegre edildi.
   - **Çalışma Şekli:** Her yeni açıda üretilen koordinatlar, bir önceki fotoğrafın koordinatlarıyla (mesafe, yükseklik, yörünge açısı, drone yönü vb.) kıyaslanır. En az 3 temel parametrede **büyük bir değişim yoksa açı çöpe atılır ve anında tamamen farklı yeni bir açı üretilir.** Fotoğraflar arasında ufak bir benzerlik dahi olması engellenir!

3. **📊 3D Uzamsal Telemetri Dosyaları (JSON - 6D Pose Verileri):**
   - **Yenilik:** Her resmin (`talon_XXXX.png`) yanına otomatik olarak İHA'nın ve kameranın 3D uzamsal telemetri koordinatlarını yazan bir companion (`talon_XXXX.json`) dosyası kaydedilmesi sağlandı.
   - **Detaylar:** Bu dosya Talon İHA'sının dünyadaki tam geometrik merkez konumunu (`X, Y, Z`), onun o andaki dikey/yatış yönelimini (`Pitch, Yaw, Roll`), İHA'yı çeken Spectator (izleyici) kamerasının tam konumunu (`X, Y, Z`) ve kameranın bakış yönünü (`Pitch, Yaw, Roll`) içerir. Bu sayede 3D Bounding Box veya 6D Pose kestirim yapay zeka modelleri için kusursuz ve otomatik veri etiketleme/6 nokta çizimi sağlanmış olur!

4. **📏 Ekstrem Uzaklık ve Vahşi Açı Genişlemesi (4m - 40m):**
   - **Mesafe Aralığı:** Kamera mesafesi `4m` ile **`40m` (400 - 4000 Unreal birimi)** arasına çıkarıldı! Devasa bir çeşitlilik elde edildi.
   - **Drone Bank Açıları:** Drone'un havada sağa/sola yatış açısı **50 dereceye** (uçağın yan dönmesi), burnunu kaldırma/indirme açısı ise **40 dereceye** çıkarıldı (dikine dalış ve dikey tırmanış).
   - **Kamera Tilt (Roll) Açısı:** Kameranın çapraz yan yatış açısı **30 dereceye** çıkarılarak spektaküler fotoğraflar sağlandı.

5. **⚡ Sıfır Köprü Yükü ve Sınırsız Çalışma Kararlılığı:**
   - **Sorun:** Saniyede 4 kez arayüz ve kontrolcü sorgulanması, UE4SS köprüsünde bellek sızıntısına yol açıyor ve oyunu yaklaşık 1 saat sonra çökertebiliyordu.
   - **Çözüm:** Arayüz sıfırlama, zaman dondurma ve görsel yükleme işlemleri artık her karede tekrarlanmak yerine **durum geçişlerinde tamı tamına 1 kere** çalışır. Boşta beklerken köprü yükü sıfırlanarak kesintisiz 24 saat çalışma güvencesi sağlandı!

---

## [EN] 🚀 Release v1.1.0 - Crash Protection, Strict Diversity Guard & Extreme Angles & 3D Telemetry

We are thrilled to launch **v1.1.0** of the Talon UAV Dataset Generator! This major release focuses on absolute long-term stability, zero memory leaks, extreme dataset diversity, a smart algorithmic filter to prevent visual duplication, and automated 3D spatial metadata exports.

### 🌟 Key Features & Improvements:

1. **🛡️ Resolved Fatal Error Crash (Spectator Lens Protection):**
   - **Issue:** Hiding camera mesh components recursively was accidentally disabling the spectator camera's primary lens (`UCameraComponent`) in shipping builds, triggering null pointer access violations and Fatal Errors.
   - **Solution:** Removed dangerous component-hiding loops entirely. Hiding is now done natively and safely via `K2_SetActorHiddenInGame(true)`, ensuring **absolute crash-proof camera snapping!**

2. **✨ Strict Diversity Guard (Lua-Side Delta Filter):**
   - **Feature:** Implemented an active geometric coordinate scanner to fulfill the requirement of having **0% visual similarity** between captures.
   - **How it works:** Each random camera/drone pose is compared against the last capture across 6 axes. The pose is accepted **only if at least 3 parameters are drastically different** (e.g. distance change >= 6m, elevation change >= 15°). Duplicate or slightly similar captures are mathematically impossible!

3. **📊 Companion 3D Spatial Telemetry Files (JSON - 6D Pose Data):**
   - **Feature:** Added automatic saving of structured JSON companion files (`talon_XXXX.json`) next to every screenshot (`talon_XXXX.png`).
   - **Details:** Each JSON file contains the clean spatial telemetry of the target Talon UAV's geometric center world position (`X, Y, Z`), its bank/heading orientation (`Pitch, Yaw, Roll`), the spectator camera's exact rendering position (`X, Y, Z`), and the camera's control rotation (`Pitch, Yaw, Roll`). This provides a seamless pipeline for 3D bounding box regression or 6D pose estimation model training.

4. **📏 Extreme Capture Ranges & Bank Angles (4m - 40m):**
   - **Camera Distance:** Expanded from a narrow `4m - 13m` to an extreme **`4m - 40m` (400 to 4000 Unreal Units)**, providing excellent far-range and close-up variety!
   - **Drone Rotations:** Extended Drone Roll to **`50°`** (sharp banked turns) and Drone Pitch to **`40°`** (steep dives and climbs).
   - **Camera Roll (Tilt):** Increased up to **`30°`** for dramatic diagonal perspectives.

5. **⚡ Zero Polling Overhead & Infinite Uptime Stability:**
   - **Issue:** Polling controller names and widget status every tick (4 times a second) caused Lua-C++ bridge heap exhaustion and memory crashes during long sessions.
   - **Solution:** Heavy restorations (time dilation, HUD toggle, gravity changes) are now executed **exactly once** during state transitions instead of on every tick, dropping background overhead to virtually 0% and enabling infinite runtime stability.

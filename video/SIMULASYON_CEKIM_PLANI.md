# SİMÜLASYON ÇEKİM PLANI — B Bölümü (Simülasyon Uçuş Kanıtı)

> **Amaç:** Sistemin resmi simülasyon ortamında görevi **tamamen otonom** icra ettiğini,
> şartnamedeki görev akışını sırasıyla ve **kritik anlar gerçek zamanlı** olacak şekilde kanıtlamak.
> **Hedef süre:** ~3 dk. Kritik anlarda (tespit, takip, kilit, GNSS devre dışı, angajman, vuruş)
> **hızlandırma YASAK**. Yalnızca uzun bekleme/hazırlık kesitlerinde sınırlı hızlandırma yapılabilir
> ve ekranda **"Nx hızlandırılmıştır"** yazılır.

## 0. Kayıt öncesi kurulum (tek seferlik)
- **Kaynak seçimi:** Görev **"Görev Başlat (GNSS Filtre)"** ile başlatılır — yani drone **bozuk
  GNSS'i GNSS Filtre ile temizleyerek** güdülür. (⚠️ "Gerçek GPS" butonu yalnız sim/debug testi
  içindir; **kanıt videosunda KULLANILMAZ** — o modda bozuk GNSS kullanımı kanıtlanamaz.)
- **Otomatik akış:** Güdüm pipeline anahtarı **OTO** (varsayılan): sistem yakınlık + YOLO kilidiyle
  görsel faza kendiliğinden geçer; kayıpta GPS'e döner. Manuel switch KULLANILMAZ (otonomi şüphesi).
- **Debug/truth:** İç doğrulama panelleri (gerçek mesafe vb.) açık kalabilir ama anlatım "bozuk GNSS
  ile güdülüyoruz" mesajını korumalı. Manuel moda ve kumandaya hiç dokunulmaz.
- **Pencere:** Oyun penceresi görünür; FPV "📡 Görüntüyü Bağla" ile oyun penceresine bağlanır.

## Görev akışı — sırayla ve ekranda KANITLANARAK (şartname 4. bölüm 1-10)

| # | Görev adımı (şartname) | Ekranda kanıt | Hız | Seslendirme cue (opsiyonel) |
|---|---|---|---|---|
| 1 | Otonom başlama (insan girişi yok) | "Görev Başlat"a basılır → drone otonom kalkar; kumandaya el sürülmediği görünür; olay günlüğü "GÖREV BAŞLADI" | Gerçek zamanlı | "Görev tamamen otonom başlıyor; kumandaya müdahale yok." |
| 2 | Bozuk GNSS ile bölgeye yönelme | BOZUK GNSS kartı: aktif bozulma adları + ham/filtre hata; mini-harita: avcı hedefe yöneliyor; faz **YAKLAŞMA/ARAMA** | Uzun seyir kısmı **sınırlı hızlandırılabilir** ("Nx" yazısıyla) | "Hedefin bozuk GNSS'iyle bölgesine yöneliyoruz; filtre ham veriyi temizliyor." |
| 3 | Görüntü işleme ile tespit (vurgulu) | FPV'de **bbox belirir** + conf; olay günlüğü **"İLK TESPİT — ID:n"** | **Gerçek zamanlı** | "Hedef görüntüden otonom tespit edildi." |
| 4 | Takip algoritması otonom devreye girer | TAKİP kartı **AKTİF**; **ID:n** sabit; track durumu | **Gerçek zamanlı** | "Takip otonom devrede — hedefe kimlik atandı." |
| 5 | Görüntü üzerinden sürekli takip | FPV bbox hedefi izler; olay günlüğü takip sürekliliği; kayıp olursa **YENİDEN TESPİT** | **Gerçek zamanlı** | — |
| 6 | GNSS'in görsel fazda KULLANILMADIĞI | Faz **GÖRSEL GÜDÜM**; FPV'de **"GPS GÜDÜMÜ: KAPALI"** kırmızı rozeti; olay günlüğü "GORSEL GUDUME GECILDI — GPS yonelimi KAPALI" | **Gerçek zamanlı** | "Görsel temas kuruldu; artık yönelim yalnızca kameradan — GPS devre dışı." |
| 7 | Görüntüyle hedefe yaklaşma | IBVS GÜDÜM kartı: hata çizgisi küçülür; GÜDÜM KOMUTU kartı akan değerler; mesafe azalır | **Gerçek zamanlı** | "Görsel güdümle hedefe kapanıyoruz." |
| 8 | Angajman kararı otonom `[VURUŞ-BAĞIMLI]` | Kilit sayacı **10 sn pencerede 5 sn** dolar → **ANGAJMAN** çipi yanar; olay günlüğü "KİLİT İSTERİ SAĞLANDI" + "ANGAJMAN" | **Gerçek zamanlı** | "Kilit isteri doldu; sistem otonom angajman kararı verdi." |
| 9 | Vuruş / angajman sonucu `[VURUŞ-BAĞIMLI]` | Oyun görüntüsünde **fiziksel çarpışma**; arayüzde **VURUŞ!** banner (mesafe ≤ eşik) | **Gerçek zamanlı** | "Hedefe fiziksel temas — vuruş gerçekleşti." |
| 10 | Başarı + insan müdahalesi olmadığı | Kalıcı **"GÖREV BAŞARILI — HEDEF DÜŞÜRÜLDÜ"** banner; tüm süre boyunca kumanda/klavye kullanılmadığı görünür | **Gerçek zamanlı** | "Görev baştan sona insan müdahalesi olmadan tamamlandı." |

## Ekranda görünmesi beklenen teknik çıktılar (şartname 5. bölüm) — arayüzde MEVCUT
| Beklenen çıktı | Arayüzde nerede (hazır) |
|---|---|
| Simülasyon ekranı | Orta panel FPV |
| Drone + hedef saha konumu | Mini-harita (kuşbakışı) + AVCI/HEDEF konum kartları |
| Bozuk GNSS kullanımı çıktısı | BOZUK GNSS kartı (bozulma adları + KESİNTİ rozeti + ham/filtre hata) |
| Hedef tespit anı | FPV bbox + olay günlüğü "İLK TESPİT" |
| bbox + merkez + hedef ID + takip durumu | FPV overlay (bbox, merkez, ID:n) + TAKİP kartı |
| Tracker aktif/pasif | TAKİP kartı AKTİF/PASİF rozeti |
| Kayıp / yeniden tespit / süreklilik | Olay günlüğü + FPV KÖPRÜ rozeti (ölü-hesap) |
| Güdüm komut telemetrisi | GÜDÜM KOMUTU kartı (throttle/pitch/roll/yaw) + IBVS kartı |
| Angajman kararı + vuruş anı | Faz çipleri (ANGAJMAN/VURUŞ) + VURUŞ! banner |
| Görev sonu başarı | GÖREV BAŞARILI banner |

> **Kayıt öncesi arayüz eksiği YOK** — 10 çıktının hepsi mevcut arayüzde var (`web/index.html`).
> Tek dikkat: 8-9-10 **terminal faz + vuruşa bağlı** (bkz. YAPILACAKLAR).

## Kayıt ayarları
- **Çözünürlük:** en az 1080p; kod/arayüz metinleri okunur olmalı. **fps:** 30 (veya 60).
- **Tek parça ekran kaydı:** görev akışını gizleyen kesme YOK. Kritik anlar kesintisiz.
- **Hızlandırma:** yalnız 2. adımdaki uzun seyir; ekrana "Nx hızlandırılmıştır" yazısı bindirilir.
- **Ses:** B bölümünde de kısa cue'lar (yukarıdaki sütun) — zorunlu değil ama otonomi anlatımını güçlendirir.

## ⭐ KAYIT SIRALAMASI — EN KRİTİK KURAL
En riskli sahne **angajman/vuruş**tur. Bu yüzden:
1. **Terminal faz çalışır hale gelir gelmez İLK İŞ:** görevin **uçtan uca, kesintisiz, tam kaydını**
   almak (kalkış → tespit → takip → görsel → kilit → angajman → vuruş → başarı). Bu ham kayıt
   **garantiye alınmadan** kurgu/seslendirme/diğer işlere geçilmez.
2. Vuruş sahnesi **gerçek, kesintisiz simülasyon çıktısı** olmak zorunda. Kurguyla vuruş izlenimi
   oluşturmak şartnamede açıkça yasak; komite teslim edilen kodu **kendisi çalıştırıp** doğrulayabilir.
3. Terminal faz kayıt gününe kadar yetişmezse: 1-7 adımlar (otonom başlama → görsel takip →
   GNSS devre dışı → yaklaşma) tam çekilir; 8-10 için metindeki `[VURUŞ-BAĞIMLI]` cümleler
   revize edilir (TESLIM_KONTROL_LISTESI'nde madde).

# KONUŞMA METNİ — A Bölümü (OKU-BİTİR: anlatım + kod açıklaması tek metin)

> **Takım:** Hamidiye · **Yarışma:** TEKNOFEST 2026 Savaşan İHA Avcı Drone
>
> ### ✅ NASIL KULLANILIR: Bu metni baştan sona SESLİ OKU, başka bir şey yapma.
> Kod açıklaması cümlelerin **İÇİNDE** — "ekranda gördüğünüz şu fonksiyon…", "şu satırda…" derken
> zaten kodu anlatıyorsun. Ekranda, her bloğun başındaki `[EKRAN: …]` notunda yazan **dosya + fonksiyon**
> gösterilsin (editör hazırlar); sen yalnızca metni oku. Doğaçlama, ekleme gerekmez.
>
> **Kod DÜZEYİNDE açılan 3 çekirdek dosya:** `gnss_filtre.py`, `ana_kontrol.py`, `ibvs_gorsel.py`.
> Tespit/takip kısa geçilir (hazır kütüphane). Süre ~4 dk. `[VURUŞ-BAĞIMLI]` = vuruş kayda yetişmezse
> revize edilecek cümle. Adı geçen fonksiyonların hepsi kodda gerçekten var; rakamlar doğrulandı.

---

### [00:00–00:15] Açılış
`[EKRAN: Takım kartı "Hamidiye" → mimari diyagramı → kod dosyaları]`

Merhaba, biz Hamidiye takımıyız. Bu videoda hem sistemimizi anlatacağız, hem de ekranda kodumuzu
açıp üç çekirdek dosyayı göstereceğiz: GNSS filtremiz, karar mekanizmamız ve görsel güdüm yasamız.
Dronumuz tamamen otonom uçuyor; tüm karar yerde üretiliyor, drona sadece dört eksenlik uçuş komutu
gidiyor.

### [00:15–00:40] Beyin — ana_kontrol.py, adim()
`[EKRAN: guidance/ana_kontrol.py — adim() fonksiyonu + LOOP_HZ = 50.0 satırı vurgulu]`

Ekranda ilk açtığımız dosya ana_kontrol; yazılımın beyni burada, adim fonksiyonunda. Vurgulu satırda
gördüğünüz gibi bu fonksiyon saniyede elli kez çalışıyor ve üç durumlu bir makine gibi karar veriyor:
arama, kilit, görsel güdüm. Uzaktayken GPS'le hedefe yaklaşıyor; hedef menzile girip kilit verince
kontrolü kameraya devrediyor. Yani bütün faz geçişlerini bu tek fonksiyon yönetiyor.

### [00:40–01:20] Birinci çekirdek — gnss_filtre.py: spike_temizle, _egim
`[EKRAN: fusion/gnss_filtre.py — spike_temizle ve _egim fonksiyonları vurgulu]`

Şimdi birinci çekirdek koda, gnss_filtre dosyasına geçelim. Hedefin konumu bize kasten bozuk geliyor:
gürültü, ani sıçrama, kayma, kopma, bir de gecikme. Ekranda gördüğünüz spike_temizle fonksiyonları bu
bozulmayı temizliyor. Şöyle çalışıyor: her ölçüm için bir "beklenen değer" hesaplıyor; dikey eksende
ani bir türev sıçraması varsa, yatayda ise ölçüm hem hızıyla hem konumuyla birlikte saparsa, onu bir
sıçrama sayıp eliyor. Yerine de, şu egim fonksiyonuyla önceki noktalardan çizdiğimiz doğrunun tahminini
koyuyor. Bir de şu var: kontrolümüz elli hertz ama GPS beş hertz; o yüzden her tikte paketin gerçekten
yeni olup olmadığına bakıp donmuş veriyi tekrar işlemiyoruz, yoksa hedefe sahte bir hız uydururduk.

### [01:20–01:45] gnss_filtre.py — guncelle(): gecikme telafisi
`[EKRAN: gnss_filtre.py — guncelle() içinde lead + güven faktörü satırları vurgulu]`

Filtrenin en kritik işi, ekrandaki guncelle fonksiyonunda: gecikme telafisi. Simülasyon bize hedefin
bir saniye önceki konumunu veriyor; biz de hızını çıkarıp konumu bir saniye ileri taşıyarak hedefin şu
an gerçekte olduğu yeri tahmin ediyoruz. Şu güven faktörü satırlarında da tahmine körü körüne
güvenmiyoruz: anlık hızla yumuşatılmış hız ayrışırsa, ya da yeni bir kopmadan çıktıysak, ileri tahmini
otomatik kısıyoruz — gürültülü anlarda yanlış yere fırlamayalım diye.

### [01:45–02:08] GPS güdümü ve görüntü hattı (kısa)
`[EKRAN: gps_takip.py adim() → detection/gorsel_tespit.py + takip.py]`

Bu temiz konumu gps_takip dosyası kullanıyor: önce on metre kalkış, sonra hedefe bir PD ve bir PID'le
yaklaşma; veri kesilirse otuz saniyeye kadar son hızla ölü-hesap. Görüntü tarafını kısaca geçiyoruz —
hedefi kendi eğittiğimiz YOLO26s modeliyle buluyoruz, uzak hedefi kaçırmamak için kareyi dilimleyerek
tarıyoruz; sonra açık kaynak HybridSort takipçisi hedefe kalıcı bir kimlik verip izi ayakta tutuyor.

### [02:08–02:53] İkinci-üçüncü çekirdek — ibvs_gorsel.py: hesapla()
`[EKRAN: guidance/ibvs_gorsel.py — hesapla(); "GPS: KAPALI" rozeti; imza satırı vurgulu]`

Şimdi görsel güdüm yasamıza geldik: ibvs_gorsel dosyasındaki hesapla fonksiyonu. Ekranda gördüğünüz
gibi, görsel temas kurulduktan sonra komutu üreten tek fonksiyon bu. Mantığı sade: görüntünün merkeziyle
hedef kutusu arasındaki hatayı alıyor ve üç boyutlu konum hesabı yapmadan doğrudan yaw ve yükseklik
komutuna çeviriyor. Şu satırda bu hatayı önce bir EMA filtresinden geçiriyoruz ki tek karelik bir titreme
komuta yansımasın. Uçuş verimizin öğrettiği dersi de buraya koyduk: hedefe fazla sokulunca açısal hızı
burnumuzun dönüşünü aşıp kadrajdan kaçıyor; o yüzden dalmak yerine kilit boyutunun hemen üstünde durup
ortalıyoruz. Ve en önemlisi — şu imza satırına dikkat edin, burada konum bilgisi yok. Yani görsel fazda
GPS'i kullanmak yapısal olarak imkânsız; kuralı kodun mimarisiyle garantiledik.

### [02:53–03:23] Kilit — ana_kontrol.py, _kilit_degerlendir()
`[EKRAN: ana_kontrol._kilit_degerlendir() → kilit sayacı (10/5 sn) → ANGAJMAN → VURUŞ]`

Son olarak kilidi, yine ana_kontrol'deki kilit_degerlendir fonksiyonu ölçüyor: on saniyelik pencerede
toplam beş saniye boyunca hedef merkezde ve yeterince büyük kalırsa kilit onaylanıyor — şartnamedeki
kural bu. `[VURUŞ-BAĞIMLI]` Kilit sağlanınca araç terminal faza geçip nişanı doğrudan hedefe kaydırıyor;
vuruş ayrı bir komut değil, görsel hatayı sıfıra sürmenin doğal sonucu.

### [03:23–03:40] Dosya haritası ve kütüphaneler
`[EKRAN: dosya ağacı — modül adları okunur zoom]`

Özetle açtığımız üç çekirdek: gnss_filtre GNSS'i temizliyor, ana_kontrol kararı veriyor, ibvs_gorsel
görsel güdümü yürütüyor. Kullandığımız açık kaynak kütüphaneler: tespit için Ultralytics ve PyTorch,
takip için boxmot, görüntü için OpenCV. Ama filtre, karar ve güdüm mantığının tamamı — az önce açtığımız
kodlar — bize ait. Teşekkürler.

---

## Editör / sunan için kısa notlar
- Sen sadece **yukarıdaki metni oku**. Her blokta `[EKRAN: …]`'daki dosya + fonksiyon ekranda vurgulu
  dursun; metindeki "şu satırda / ekranda gördüğünüz" ifadeleri o vurgulanan yeri kastediyor.
- Ekranda gösterilecek fonksiyonlar: `ana_kontrol.adim`, `gnss_filtre.spike_temizle` + `_egim` +
  `guncelle`, `ibvs_gorsel.hesapla`, `ana_kontrol._kilit_degerlendir`. Hepsi kodda var.
- Rakamlar doğrulandı: 50 Hz kontrol / 5 Hz GPS, 10 m kalkış, 30 sn ölü-hesap, 1 sn gecikme telafisi,
  YOLO26s @960, kilit 10/5 sn, handoff 40 m. Yatay standoff 0 → "geride dur" demedik.
- **`[VURUŞ-BAĞIMLI]`** kayda yetişmezse: "…terminal faza geçip nişanı hedefe kaydırıyor…" → "…kilidi
  sürdürüp hedefe yaklaşmaya devam ediyor…"; vuruş cümlesi çıkarılır.

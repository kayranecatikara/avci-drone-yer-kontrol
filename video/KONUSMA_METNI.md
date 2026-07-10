# KONUŞMA METNİ — A Bölümü (Algoritma, Yazılım Mimarisi ve Kaynak Kod)

> **Takım:** Hamidiye · **Yarışma:** TEKNOFEST 2026 Savaşan İHA Avcı Drone
> **Bu metin:** Videonun ilk bölümü (algoritma + kod anlatımı). Hızlandırma YOK, sesli anlatım.
> **Hedef süre:** ~4 dk (≈560 kelime; 140 kelime/dk). Süre 3 dk'ya indirilmek gerekirse
> `[OPSİYONEL]` bloklar çıkarılır — kalan metin kendi içinde akıcı ve eksiksizdir.
> **Etiketler:** `[OPSİYONEL]` = süre için çıkarılabilir · `[VURUŞ-BAĞIMLI]` = terminal faz/vuruş
> kayıt gününe kadar yetişmezse revize edilecek cümle.
>
> **⛔ TUTARLILIK NOTU:** Her cümle koddaki karşılığıyla eşleştirildi (bkz. `MIMARI_ENVANTER.md`).
> Kodda olmayan hiçbir yetenek anlatılmıyor. Pose/keypoint bu sürümde KAPALI → hiç geçmiyor.

---

### [00:00–00:18] Açılış + genel mimari  · (43 kelime)
`[EKRAN: Takım adı "Hamidiye" + yarışma logosu açılış kartı → uçtan uca mimari diyagramı]`

Merhaba. Biz Hamidiye takımı olarak, avcı dronumuzu tamamen otonom çalışan bir **yer
kontrol istasyonu** yazılımıyla yönetiyoruz. Tüm algılama, filtreleme ve karar üretimi
yerde çalışır; drona yalnızca dört eksenlik kontrol komutu gider. Sistemimiz iki
bağımsız girdiyi birleştirir: **bozuk hedef GNSS'i** ve **kameradan gelen görüntüyü**.

### [00:18–00:45] Uçtan uca veri akışı  · (61 kelime)
`[EKRAN: Aynı diyagram üzerinde iki thread vurgulanır — 50 Hz kontrol + GPU dedektör]`

Mimarimiz iki paralel iş parçacığı üzerine kurulu. **Elli hertzlik kontrol döngüsü**
güdüm komutlarını üretir. Ayrı bir **dedektör döngüsü** ise oyun penceresinden aldığı
kareyi yapay zeka modeliyle işler. İkisini ayırdık; çünkü ağır görüntü işleme, kontrol
döngüsünü asla yavaşlatmamalı. Simülasyona bağlantıyı resmi `drone_sdk` sağlar; bu
dosya, şartnamedeki `input.py` muadilimizdir — telemetriyi okur, kontrol komutunu yollar.

### [00:45–01:20] Bozuk GNSS ve filtreleme  · (79 kelime)
`[EKRAN: fusion/gnss_filtre.py — spike temizleme fonksiyonları + ham vs filtre grafiği]`

Hedef İHA'nın GNSS verisi bize kasıtlı olarak bozuk gelir: konum gürültüsü, ani
sıçramalar, kayma ve veri kesintileri. Biz bu veriyi doğrudan doğru kabul etmiyoruz.
**GNSS Filtre** modülümüz her eksende bir pencere tutar; komşu ölçümlerden çizdiği
lineer eğimle bir sonraki konumu **öngörür**. Gelen ölçüm hem hız hem konum eşiğini
birlikte aşarsa, onu bir sıçrama sayıp öngörülen değerle değiştirir. Temizlenen seriden
hedefin **hızını** kestirir ve haberleşme gecikmesini telafi etmek için konumu bir
saniye ileri taşır. `[OPSİYONEL]` Bu ileri taşımayı **güven ağırlığıyla** ölçekleriz:
anlık hız ile yumuşatılmış hız birbirini tutmuyorsa güven düşer, öngörü kısılır.

### [01:20–01:45] GPS güdümü ve kesinti dayanıklılığı  · (55 kelime)
`[EKRAN: guidance/gps_takip.py — adim() + dead-reckoning bloğu]`

Temizlenmiş konumu **GPS güdüm** modülümüz kullanır. Kalkıştan sonra hedefe yatayda bir
**PD**, dikeyde bir **PID** yasasıyla yaklaşır; burnu sürekli hedefe döndürür. En kritik
kısım kesinti anıdır: GNSS paketi gelmeyi kestiğinde sistem donmaz, son bilinen hızla
**ölü-hesap** yaparak otuz saniyeye kadar tahminî konumu sürdürür. Amacımız, GNSS
güvenilmez olduğu anlarda bile göreve devam edebilmek.

### [01:45–02:20] Görüntü işleme ve hedef tespiti  · (76 kelime)
`[EKRAN: detection/gorsel_tespit.py + örnek tespit kareleri (bbox + conf)]`

Hedefi görüntüden kendi eğittiğimiz bir **YOLO26s** modeliyle tespit ediyoruz; model tek
sınıf tanır: Talon İHA. Kareyi dokuz yüz altmış piksel çözünürlükte, yarı hassasiyette
işleriz. Uzak ve küçük hedefi kaçırmamak için kendi yazdığımız **dilimleme** yöntemini
ekledik: kare yeterince yakın bir tespit vermezse, onu örtüşen parçalara bölüp her
parçada ayrı çıkarım yapar, sonuçları birleştiririz. `[OPSİYONEL]` Tek karelik yanlış
tespitlere güvenmeyiz; bir hedefin geçerli sayılması için üst üste beş kare doğrulanması
ve güven eşiğini geçmesi gerekir. Böylece anlık parazit, kilide dönüşmez.

### [02:20–02:50] Takip  · (62 kelime)
`[EKRAN: detection/takip.py — HybridSort; FPV'de ID:n etiketi + takip durumu]`

Tespit çıktısını doğrudan güdüme vermeyiz; önce bir **çoklu-nesne takipçisinden**
geçiririz. Açık kaynak **boxmot HybridSort** algoritmasını kullanıyoruz — bunu videoda
açıkça belirtiyoruz. Takipçi, hedefe kalıcı bir kimlik atar, kareler arası hareketini
kestirir ve kısa tespit deliklerinde izi ayakta tutar. Dedektörün gördüğü kısa boşluklarda
ise güdüm tarafında **görüntü-düzlemi köprüsü** devreye girer: kutuyu son ölçülen hızıyla
kısa süre ileri taşırız, böylece takip sürekli görünür.

### [02:50–03:30] Sensör füzyonu, güdüm ve karar  · (88 kelime)
`[EKRAN: guidance/ana_kontrol.py FSM → guidance/ibvs_gorsel.py; "GPS GÜDÜMÜ: KAPALI" rozeti]`

Karar mekanizmamız üç durumlu bir makinedir: **arama**, **kilit** ve **görsel güdüm**.
GPS ile hedef bölgesine yaklaşırız; hedef kırk metre menzile girip model üst üste kilit
verince, güdümü **kameraya devrederiz**. Bu an kritik: görsel temas kurulduktan sonra
hareket komutu **yalnızca görüntüden** üretilir. Görsel yasamız sade bir **görüntü-tabanlı
görsel servolama**dır — üç boyutlu konum kestirmeden, hedefin kadraj içindeki hata
açısını doğrudan komuta çevirir. Kameramız yirmi beş derece yukarı baktığından, hedefi
merkezin biraz üstünde tutmak aracı hedefin altına yerleştirir; gökyüzü arka planında
temiz takip sağlar. **Bu fazda GPS verisi komuta asla girmez — bunu kodun imzasıyla
yapısal olarak garanti ettik.**

### [03:30–03:55] Terminal faz ve angajman  · (52 kelime)
`[EKRAN: kilit sayacı (10 sn pencere / 5 sn) → ANGAJMAN çipi → VURUŞ]`

Kilitlenme şartnamedeki kuralla ölçülür: on saniyelik pencerede toplam beş saniye. `[VURUŞ-BAĞIMLI]`
Bu kilit sağlanıp hedef nişanda kararlı hale gelince sistem **terminal faza** geçer:
nişan noktasını doğrudan hedefe kaydırır, mesafe frenlerini kaldırır ve çarpışma rotasına
kilitlenir. `[VURUŞ-BAĞIMLI]` Vuruş ayrı bir komut değildir; araç görsel hatayı sıfıra
sürerek hedefin üzerine kapanır ve fiziksel temas gerçekleşir.

### [03:55–04:15] Kaynak kod turu ve kütüphaneler  · (44 kelime)
`[EKRAN: dosya ağacı — modül adları okunur zoom]`

Özetle: `drone_sdk` girdiyi sağlar, `gnss_filtre` GNSS'i temizler, `gps_takip` GPS
güdümünü, `ibvs_gorsel` görsel güdümü yürütür; `gorsel_tespit` ve `takip` görüntü
hattıdır, `ana_kontrol` hepsini bir karar makinesinde birleştirir. Kullandığımız açık
kaynak kütüphaneler: nesne tespiti için **Ultralytics** ve **PyTorch**, takip için
**boxmot**, görüntü işleme için **OpenCV**. Karar mantığının tamamı bizim özgün
kodumuzdur. Teşekkürler.

---

## Süre / kelime özeti
- **Toplam (tüm bloklar):** ≈ 560 kelime → **~4:00 dk** (140 kelime/dk).
- **`[OPSİYONEL]` bloklar çıkarılırsa** (3 cümle, ≈ 55 kelime) → ≈ 505 kelime → **~3:36 dk**.
  Daha da kısaltmak gerekirse §Takip ile §Görüntü işleme tek blokta özetlenebilir (bkz. STORYBOARD).
- **`[VURUŞ-BAĞIMLI]` cümleler:** §Terminal faz'daki 2 cümle. Terminal faz kayıt gününe kadar
  yetişmezse: "…terminal faza geçer…" → "…kilidi sürdürür ve hedefe yaklaşmaya devam eder…"
  şeklinde revize edilir, vuruş cümlesi çıkarılır (TESLIM_KONTROL_LISTESI'nde madde var).

## Anlatım notları (sunan için)
- Uzman terimleri ilk geçtiğinde bir cümleyle açıkladık: "görüntü-tabanlı görsel servolama —
  3B konum kestirmeden hedefin görüntü hatasını doğrudan komuta çeviren yaklaşım", "ölü-hesap —
  veri kesilince son hızla tahmin sürdürme".
- Rakamlar koddan **gerçek**: YOLO26s, imgsz 960, tek sınıf; kilit 10 sn/5 sn; handoff 40 m;
  ölü-hesap 30 sn; gecikme telafisi 1 sn; kesinti toleransı. Değiştirilirse bu metin de güncellenmeli.
- Eğitim seti kare sayısı gibi bir rakam **kasıtlı olarak verilmedi** (repoda kesin sayı yok);
  gerekirse takım kendi veri seti boyutunu ekler — bkz. `YAPILACAKLAR.md`.

# KOD AÇIKLAMASI — Önemli Modüller ve Fonksiyonları

> **Amaç:** Bu belge, sistemin çekirdek dosyalarını fonksiyon fonksiyon açıklar. Her başlık için
> **"ne yapar / temel fikir / dikkat edilecek satırlar"** verilmiştir. Takımın kodu **kendi
> cümleleriyle anlatabilmesi** için yazıldı — ezber değil, mantığı kavramak esas. Sunumda bir
> soru gelirse buradaki mantığı kendi ifadenizle söyleyin.

Sistem iki paralel iş parçacığı (thread) üzerine kuruludur:
- **Kontrol döngüsü (~50 Hz):** `ana_kontrol.AvciKontrol.adim()` her tikte bir karar üretir.
- **Dedektör döngüsü (GPU):** oyun karesini YOLO'dan geçirir, sonucu kontrol döngüsüne bırakır.

Ağır görüntü işlemenin kontrol döngüsünü yavaşlatmaması için ikisi ayrıldı. Aşağıdaki dosyalar
bu iki döngünün beynidir.

---

## 1) `fusion/gnss_filtre.py` — Bozuk GNSS'i temizleyen filtre

Hedef İHA'nın GNSS'i bize **kasıtlı bozuk** gelir: gürültü, ani sıçrama (spike), kayma, kesinti.
Bu modül veriyi düzeltir, hedefin hızını kestirir ve haberleşme gecikmesini telafi eder. Sınıf:
`GNSSFiltre`. Filtre **açıklanabilir** olsun diye bilerek sade tutuldu (Kalman gibi kara kutu değil).

### `_egim(ts, vs)` — en küçük kareler ile eğim (hız)
- **Ne yapar:** Zaman-değer nokta bulutuna bir doğru uydurup **eğimini** döndürür. Değer konumsa
  eğim = **hız**.
- **Temel fikir:** Tek noktadan hız çıkarmak gürültülüdür; son N noktaya doğru uydurmak
  gürültüyü bastırır. Formül klasik en-küçük-kareler eğimidir: `(N·Σxy − Σx·Σy) / (N·Σx² − (Σx)²)`.
- **Dikkat:** Payda ~0 ise (tüm noktalar aynı anda) 0 döner — sıfıra bölme koruması.

### `z_spike_temizle`, `x_spike_temizle`, `y_spike_temizle` — eksen bazlı sıçrama reddi
- **Ne yapar:** Her eksende diziyi gezer; her ölçüm için **beklenen** değeri (son temiz konum +
  hız × Δt) hesaplar. Gelen ölçüm beklenenden çok saparsa onu **sıçrama** sayıp yerine beklenen
  değeri koyar; makulse olduğu gibi kabul edip hız tahminini günceller.
- **Temel fikir (iki kapı):** Bir ölçümün "sıçrama" sayılması için **hem hız hem konum** eşiğini
  birlikte aşması gerekir (`hiz_sapma > hiz_esik AND konum_sapma > konum_esik`). Tek eşik yanlış
  alarm verir; iki kapı gerçek sıçramayı meşru hızlı hareketten ayırır.
- **`hold` sayacı (kritik güvenlik):** Arka arkaya en fazla `max_hold` kez ölçümü reddederiz. Eğer
  hedef gerçekten yön değiştirdiyse (sürekli "sapıyor"), sonsuza kadar reddedip filtreyi gerçeğe
  kör bırakmayız — `hold` dolunca yeni gerçeği kabul ederiz. "Sıçrama mı, yoksa gerçek manevra mı?"
  ikilemini bu sayaç çözer.
- **`dt > 5s` durumu:** Uzun kesinti sonrası hız sıfırlanır; eski hızla saçma tahmin yapılmaz.
- **Not:** X ve Y birlikte 2 boyutlu değerlendirilir (`x_spike_temizle` içinde y de taşınır);
  yatay sıçrama iki eksenin birlikte sapmasıdır. Z (irtifa) ayrı, daha sıkı eşiklerle.

### `guncelle(bozuk_x, bozuk_y, bozuk_z)` — akış (streaming) girişi, ana metod
Kontrol döngüsü her yeni GNSS ölçümünde bunu çağırır. Sırasıyla:
1. **Ham örneği pencereye ekle** (cm→m; spike eşikleri metre cinsinden). Pencere `self.pencere`
   boyutunu aşarsa en eskiyi at (bellek + hız).
2. **Batch temizle:** `x/y/z_spike_temizle` çağrılır; dizinin **son elemanı** = şu anki temiz konum.
3. **Hız kestir:** Son `vel_n` temiz nokta üzerinden `_egim` ile hız (cm/s).
4. **Gerçekçi tavana kırp:** Hız `MAX_HEDEF_HIZ` (~40 m/s) ile sınırlanır — filtre patlaması engellenir.
5. **EMA yumuşat:** Döngü jitter'ından gelen hız titremesi üstel ortalama ile bastırılır.
6. **Lead güven faktörü:** Kısa pencere hızı (`SHORT_N`) ile uzun pencere hızı karşılaştırılır.
   İkisi tutuyorsa hareket kararlı → güven yüksek; çelişiyorsa (belirsiz) → güven düşer.
7. **Gecikme telafisi (lead):** Ölçüm ~`gecikme_sn` saniye eskidir. Konumu `hız × gecikme × güven`
   kadar **ileri taşırız** → hedefin şu an olduğu yeri hedefleriz, olduğu yeri değil. Kesinti
   sonrası (`cooldown`) lead ağır kısılır (bayat hızla ileri fırlatma yok).
- **Döndürür:** Gecikme-telafili (lead'li) temiz konum. Güdüm bunu kullanır.

### `durum_gudum()` — güdüm için durum
- **Ne yapar:** `{pos, vel}` döndürür — **lead'siz** anlık temiz konum + hız. Kontrolcü ölü-hesap
  ekstrapolasyonunu kendi yaptığından ona lead'siz ham durumu veririz (çift telafi olmasın).

---

## 2) `guidance/gps_takip.py` — GPS fazı güdümü (kalkış → yaklaşma → devir)

Sınıf `GPSTakip`. GPS fazının **tek sahibi**: kalkış, filtre çağrısı, kesinti dayanıklılığı, PD/PID
güdüm. Sabitleri kendi `GPSCfg`'sindedir (görsel Cfg'den ayrı).

### `_hedef_temizle()` — filtreyi besle, durumu güncelle
- **Ne yapar:** Oyundan ham hedef GNSS'i alır. **Değişmemişse** (aynı paket) `_fresh=False` işaretler
  ve eski temizi döndürür — bayat veriyle döngü şişmez. Yeni ölçümü `GNSSFiltre.guncelle`'ye verir;
  sonucu `son_temiz`, hızı `son_hiz` olarak saklar, `_fresh=True` yapar.
- **Temel fikir:** `_fresh` bayrağı "bu tik gerçekten yeni GNSS geldi mi?" sorusunun cevabıdır —
  ölü-hesabın ne zaman devreye gireceğini bu belirler.

### `_derivative(e, t)` — EMA'lı hata türevi (PD'nin D'si)
- **Ne yapar:** Konum hatasının zaman türevini (hata hızı) hesaplar, EMA ile yumuşatır. Türev
  gürültüye çok duyarlıdır; ham türev drone'u titretir, EMA bunu sönümler.

### `adim()` — bir kontrol tiki (kalkış / yaklaşma / kesinti)
- **Kalkış:** Zemin irtifası kaydedilir; `TAKEOFF_ALT_AGL`'e ulaşana kadar sabit yukarı itki verilir.
- **Kesinti tespiti:** `_fresh` ise "son taze zaman" güncellenir. GNSS kesilirse (`not _fresh`),
  son taze andan bu yana geçen süre **ölü-hesap süresi** `dr_dt` olur (en fazla `DR_MAX_S=30 sn`).
- **Ölü-hesap (dead-reckoning):** Kesinti boyunca hedef konumu **son bilinen hızla ileri taşınır**
  (`tx = son_xy + vhx·dr_dt`). Yani GNSS gelmese de hedefin nereye gittiğini tahmin ederek göreve
  devam ederiz. 30 saniye sonra tahmine güvenmeyi bırakır (loiter).
- **Güdüm yasası:** Yatayda **PD** (hata + türevi), dikeyde **PID** (integral irtifa sapmasını da
  toplar). Hedefe tam üstüne değil `APPROACH_STANDOFF` mesafesinde yaklaşılır (üstüne binme yok).
  Burun sürekli hedefe döndürülür (yaw). Komutlar eksen bazlı **rate-limit**'ten geçer (ani sıçrama
  = sarsıntı yok).

---

## 3) `guidance/ana_kontrol.py` — Karar makinesi (FSM) ve görsel güdüm sahibi

Sınıf `AvciKontrol`. GPS fazını `GPSTakip`'e **devreder**; kendi işi: durum makinesi (arama→kilit→
görsel), görsel güdüm, kilit sayacı, uçuş logu. `Cfg` sınıfı tüm görsel-faz ayar sabitlerini tutar.

### `adim()` — ana durum makinesi (her tik)
- **Ne yapar:** Sistemin o anki durumuna göre (`ARAMA` / `KILIT_YAKLASMA` / `GORSEL_GUDUM`) doğru
  güdümü seçer. GPS fazındayken `self.gps.adim()`'e devreder. Hedef menzile girip model üst üste
  kilit verince görsel faza **otonom geçiş** (handoff) yapar. Görsel temas kesilirse (kayıp) kurala
  göre GPS'e geri döner.
- **Temel fikir:** Kaba yaklaşma GPS'in, hassas terminal takip kameranın işidir; FSM bu iki fazı
  temiz bir kilit kriteriyle birbirine bağlar.

### `set_gorsel_tespit(det)` — dedektör çıktısını al + görüntü hızını ölç
- **Ne yapar:** Dedektör thread'inin bulduğu bbox'u kontrol tarafına aktarır. Ardışık iki **gerçek**
  tespitten bbox'un **görüntü-düzlemi hızını** (piksel/s) ölçer — köprü (aşağıda) bunu kullanır.
- **Dürüstlük:** Uzun kesinti sonrası ilk tespitte hız **sıfırlanır** (bayat hızla köprü kurulmaz).

### `_gorsel_tespit_oku()` — görüntü-düzlemi köprüsü (kısa tespit deliklerini kapatır)
- **Ne yapar:** Gerçek tespit `VIS_STALE_S`'i aşınca (dedektör kısa süre kör), bbox'u son ölçülen
  hızıyla `VIS_KOPRU_S` boyunca **ileri taşıyıp** sanal bir tespit üretir. IBVS aynı yasayla bu sanal
  kutuyu izler; gerçek tespit dönünce devralır.
- **Temel fikir:** Sabit-hız varsayımı **açıklanabilir** (Kural 8) ve girdisi sadece kameradan gelen
  bbox + bbox hızı olduğundan görsel-faz GPS yasağına uyar. Köprü tiki **kilit sayacına sayılmaz**
  (rapor tespit oranı gerçek kalır).

### `_kilit_degerlendir(tespit, t)` — kilit isterinin ölçümü (salt gözlem)
- **Ne yapar:** Her görsel tikte hedef merkezi kadrajın orta bölgesinde mi (yatayda %25–75, dikeyde
  %10–90) ve bbox en az bir eksende `VIS_LOCK_PCT`'ten büyük mü diye bakar. 10 saniyelik pencerede
  toplam ≥5 saniye sağlanırsa **kilit** onaylanır (şartname kuralı).
- **Not:** Bu fonksiyon **komuta girmez** — sadece kilit kanıtı üretir (kırmızı dörtgen, angajman çipi,
  olay kaydı). Güdüm ayrı yürür.

### `_gorsel_guduum(tespit, t, ...)` — görsel fazın güdüm çağrısı
- **Ne yapar:** Bbox'u (ve pose kapalı olduğundan `poz=None`) `AvciIBVS.hesapla`'ya verir, dönen 4
  eksenlik komutu uygular. Kendi IMU roll/pitch'imizi ego-motion telafisi için geçirir (hedef verisi
  değil → kural OK).

### `_send(thr, pitch, roll, yaw)` — komut uygulama + hız limiti
- **Ne yapar:** Üretilen komutu drone'a yollamadan önce tik başına maksimum değişimi (`MAX_DELTA`)
  sınırlar → bank-rate uyumlu, salınımsız, sarsıntısız kontrol.

---

## 4) `guidance/ibvs_gorsel.py` — Görsel güdüm yasası (tek fonksiyon: `hesapla`)

Sınıf `AvciIBVS`. **Görüntü-Tabanlı Görsel Servolama (IBVS):** görüntünün merkezinden bbox merkezine
bir çizgi çek; bu çizginin **açısı** düzeltme yönünü, **büyüklüğü** merkeze sapmayı verir. Güdüm bu
çizgiyi sıfıra sürmektir. **3B konum kestirmeye gerek yok** — hedefin görüntü hatasını doğrudan komuta
çevirir. GPS yasağı **yapısal**: `hesapla` imzasında konum/hız/rotasyon yoktur (bir birim testi bunu
denetler).

### `hesapla(det, p, ...)` — bir görsel tikte 4 eksenlik komut üretir
Temel matematik:
- `ex = (cx − W/2) / (W/2)` → yatay sapma (−1 sol, +1 sağ)
- `ey = (cy − H/2) / (H/2)` → dikey sapma
- `yaw = K_YAW · ex` (hedef sağdaysa sağa dön), `thr = K_DIKEY · (−ey)` (yukarıdaysa tırman)
- `pitch = İLERİ · (1 − MERKEZ_FREN · r)` → merkezdeyken tam ileri, sapmışken kısar

Üzerine eklenen, **veriyle doğrulanmış** mekanizmalar:
- **Kilit-tut (stand-off):** İleri itki artık bbox boyutunu bir hedefe (`BOYUT_HEDEF`) süren bir
  P-yasadır. Uzaktayken tam gaz yaklaşır; hedef boyuta gelince **istasyon tutar** (dalmaz). Neden:
  hedefe fazla dalınca açısal hız yaw kapasitesini aşıp hedef kadrajdan kaçar — bir mesafede durmak
  merkezlemeyi mümkün kılar.
- **Yakınlık-ölçekli kazanç:** Yaklaştıkça (bbox büyüdükçe) yaw/dikey kazancı otomatik artar
  (`k_yakin = 1 + KAZANC · boyut/hedef`). Fizik: hedefin görüntüdeki açısal hızı ~ hız/mesafe; mesafe
  küçülünce sabit kazanç geride kalır. Bu ölçekleme kenara kaçmayı azaltır (uçuş verisi: yakınken
  yatay sapma 0.52 → 0.15).
- **Kapanma-hızı freni (TTC):** bbox hızlı büyüyorsa (hedefe hızlı kapanıyor → aşacak) ileri itki
  önceden kısılır → hedefi aşmadan kilit bandına oturur.
- **Alçalma freni + dikey nişan:** Kamera +25° yukarı sabit olduğundan hedefi merkezin biraz üstünde
  tutmak aracı hedefin **altına** yerleştirir (gökyüzü arka plan, temiz tespit). İrtifa mandallanmasın
  diye, hedef nişanın altındaysa ileri itki çarpımsal kısılır (negatif thr gerçekten alçaltsın).
- **Ego-pitch telafisi:** İleri itki gövdeyi öne yatırınca kamera düşer, hedef görüntüde sahte yukarı
  zıplar; dikey hatayı kendi pitch'imizden arındırırız (kendi IMU'muz = ego-motion, hedef verisi değil).
- **Yumuşak geçiş (handoff):** GPS'ten görsele geçince ileri itki ve dikey nişan `HANDOFF_S` boyunca
  0'dan rampalanır → ani lunge/alçalış yok, hedef kadrajda kalır.
- **EMA:** `ex/ey/boyut` üstel ortalamadan geçer — tek karelik YOLO sıçraması komutu titretmez.

---

## 5) `detection/takip.py` — Çoklu-nesne takipçisi (HybridSort adaptörü)

Sınıf `Takipci`. Açık kaynak **boxmot HybridSort** algoritmasını sarar (bunu videoda açıkça
belirtiyoruz — hazır kütüphane, kendi güdümümüz değil).
- **`guncelle(tespitler, ..., frame)`:** Dedektörün tüm kutularını takipçiye verir; takipçi hedefe
  **kalıcı bir kimlik (ID)** atar, kareler arası hareketini Kalman ile kestirir, kamera hareketini
  telafi eder. En yüksek güvenli izi güdüme döndürür.
- **Neden:** Ham "en yüksek güvenli kutu" seçimi kare-kare farklı nesneye atlayabilir; kalıcı ID,
  hedef sınıf/kimlik sürekliliği ve kısa delik dayanıklılığı sağlar.

---

## Kullandığımız açık kaynak kütüphaneler (dürüst beyan)
- **Ultralytics + PyTorch:** YOLO tespit modeli çıkarımı.
- **boxmot:** HybridSort çoklu-nesne takibi.
- **OpenCV:** görüntü işleme (kare yakalama, çizim, dilimleme).
- **NumPy:** vektör/matris işlemleri.

**Özgün olan (bizim yazdığımız):** GNSS filtresi, GPS güdüm yasası (PD/PID + ölü-hesap), IBVS görsel
güdüm yasası ve tüm iyileştirmeleri, karar makinesi (FSM), görüntü-düzlemi köprüsü, kilit ölçümü,
yer kontrol arayüzü. Hazır kütüphaneler yalnız tespit çıkarımı ve takip içindir; **karar ve güdüm
mantığının tamamı özgün kodumuzdur.**

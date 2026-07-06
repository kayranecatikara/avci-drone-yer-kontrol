# main ↔ yarisma-pipeline: Güdüm, Pose ve Merge — Basit Açıklama

*Bu belge geliştirme notudur; teslim paketine girmez. Amaç: merge kararını
verebilmek için "main'de ne var, bende ne var, çakışan ne" sorularını
sade dille cevaplamak.*

Tarih: 2026-07-05 · Branch'ler: `main` (takım) ↔ `yarisma-pipeline` (benim)

---

## 0) Tek cümlelik özet

- **main GPS FİLTRESİNİ değiştirmedi.** Merge sana filtre iyileştirmesi getirmez.
- main'in "gps" işi aslında **güdüm** (serhadcan'ın *standoff* takibi) — benim
  güdümümle **aynı iki soruna rakip çözüm** (çakışma bu yüzden).
- Pose'da **iki paralel iş** var: benimki uçuş-anı **PnP kestirici**, Berat'ınki
  offline **etiketleme + 3B tablo**. İkisi farklı 3B model → birleştirmek için
  uzlaştırma lazım.
- **Dataset** üretimi main ile **çakışmaz** (yeni klasör, uçuş çekirdeğine
  dokunmaz) → istersek yapabiliriz.

---

## 1) serhadcan'ın "GPS" işi tam olarak ne? (basitçe)

### Eski davranış (RAM / çarpma)
Drone bozuk GPS'i temizleyip hedefe gidiyor ve **hedefe dalıp çarpıyordu**
(kamikaze). Sahada gördüğün "çarpıyor ama kamera hedefe bakmıyor" bunun sonucu.

### serhadcan ne yaptı? (STANDOFF + kamera çerçeveleme)
GPS güdümünü "çarp"tan çıkarıp **"arkasında dur ve takip et"e** çevirdi.
Üç somut ayar (hepsi `guidance/ana_kontrol.py` içinde bayrak):

| Ayar | Ne yapar | Neden |
|------|----------|-------|
| `GPS_TERMINAL_STRIKE = False` | Çarpma/dalış modunu **kapatır** (kod silinmedi, sadece kapalı; `True` yaparsan eski çarpma geri gelir) | GPS öldürücü faz değil |
| `APPROACH_STANDOFF = 500 cm` | Hedefin **5 m arkasındaki** noktaya sürer → drone çarpmaz, hedefi *pace'ler* (hızını eşitleyip takip eder) | Çarpmayı ve "180° flip" savrulmasını önler |
| `APPROACH_ALT_OFFSET = 500 cm` | Drone hedefin **5 m altında** uçar → 25° eğik kamera hedefi **ekranda ortalar** | "Kamera hedefe bakmıyor" sorununu çözer |
| `APPROACH_LEAD_S = 0.5 s` | Nişan noktasına **kısa** öngörü (tam 2 sn'lik lead drone'u savuruyordu) | Manevrada nişan noktası savrulmasın |
| `AUTO_VISUAL_HANDOFF = False` | GPS standoff'ta **kalır**, görsel faza otomatik geçmez | Görsel model olgunlaşana kadar GPS'e güven |

**Yani serhadcan'ın çözümü:** *"Hedefe çarpma; 5 m altında-arkasında dur,
kamerayla çerçeve içinde tut, görsel olgunlaşınca devret."*

### Neden bu ÖNEMLİ?
Bu, senin sahada bildirdiğin **iki soruna da** (çarpıyor + kamera bakmıyor)
doğrudan çözüm. Ben aynı iki soruna **DÜZELTME-1** ile saldırmıştım
(dön-sonra-ilerle + dikey-FOV kapısı). **İkimiz aynı problemi iki farklı
yoldan çözdük.** "Çakışma" dediğim şey bu: aynı kod satırları, iki farklı
felsefe. Kötü değil — seçim meselesi.

> Not: main şu an tespit modeli iyi olmadığı için (0 gerçek Talon tespiti)
> "görsele geçme, GPS-standoff'ta kal" (serhadcan) **pratikte daha güvenli**.
> Benimki iyi bir görsel model VARSAYIYOR (görsele devrediyor).

---

## 2) `ana_kontrol.py`'de tam olarak ne çakışıyor? (detay)

İki taraf da aynı dosyanın aynı bölgelerini değiştirdi. Üç nokta:

**Çakışma 1 — Görsele geçiş (handoff):**
- **serhadcan:** `AUTO_VISUAL_HANDOFF = False` → GPS standoff'ta kal, görsele geçme.
- **ben:** CONFIRMED track olunca `ARAMA→YAKLASMA→GORSEL_TAKIP`'e geç (görsele devret).
- Ayrıca **FSM'in kendisi farklı:** main = 2 durum (`ARAMA → KILIT`), ben = 5 durum
  (`ARAMA→YAKLASMA→GORSEL_TAKIP→KILIT_BILDIR→ANGAJMAN`).

**Çakışma 2 — Dikey nişan:**
- **serhadcan:** `APPROACH_ALT_OFFSET` ile hedefin 5 m altında uç (kamera çerçeveleme).
- **ben:** hedef-Z **EMA** (hedefin yüksekliğini yumuşat) + geometrik dikey-FOV kapısı.

**Çakışma 3 — Terminal / yaklaşma mantığı:**
- **serhadcan:** standoff pace (çarpma kapalı), kısa lead.
- **ben:** DÜZELTME-1 dön-sonra-ilerle (yaw hatası büyükken ileri gazı kes,
  roll strafe'i bastır).

### İyi haber: ikisi de BAYRAK tabanlı
Hem serhadcan (`GPS_TERMINAL_STRIKE`, `AUTO_VISUAL_HANDOFF`) hem ben
(`YAKLASMA_BURUN_HEDEFE`) davranışları **bayrak arkasında** yazdık. Yani
merge'de **ikisini de koruyup bayrakla seçmek mümkün** — kimsenin işi çöpe gitmez.
(Zoru: 5-durum FSM ile 2-durum FSM'i tek dosyada birleştirmek dikkat ister.)

---

## 3) Pose — ben tam olarak ne yaptım? (basitçe)

### Önce: "pose" ve "PnP" nedir?
- **Pose** = hedefin **nasıl durduğu**: hangi yöne bakıyor (yaw), ne kadar
  yatık (roll), ve ne kadar uzakta.
- **PnP** (Perspective-n-Point) = klasik bir geometri yöntemi. Mantığı:
  > "Talon'un gerçekte kaç cm olduğunu **biliyorum** (burun-kuyruk 1.1 m,
  > kanat açıklığı 1.72 m). Kamerada bu noktaların **nerede** göründüğünü de
  > görüyorum. İkisini birleştirince Talon'un **3B'de nasıl durduğunu ve ne
  > kadar uzakta olduğunu** geri hesaplarım."

Basit benzetme: Elindeki bir kalemi biliyorsun (uzunluğu belli). Fotoğrafta
kalem kısa ve eğik görünüyorsa, beynin "demek ki bana doğru eğik tutuluyor"
der. PnP bunu matematikle yapar.

### Benim yaptığım dosyalar
| Dosya | Ne yapar |
|-------|----------|
| `detection/talon_pose_estimator.py` (270 satır) | **Uçuş anında** PnP çözücü. Tespit modelinin verdiği 6 keypoint (burun, kanatlar, kuyruk) → hedefin yön+mesafesi. OpenCV `solvePnPRansac` + reproj hata kapısı (8px). |
| `arac/egitim/pose_egit.py` (133 satır) | Pose modelini **eğitmek** için iskelet (geliştirme aracı). |
| `arac/pnp_sim_dogrula.py` (197 satır) | PnP'yi sim'de **doğrulamak** için araç. |

### Şu anki durumu
- Kod **tam ve test edilmiş** (sentetik keypoint round-trip unit testi var).
- Ama işe yaraması için bir **pose modeli (.pt)** gerekiyor (keypoint'leri
  çıkaracak ağ). O model olmadan bu faz **otomatik pasif** olur ve sistem
  IBVS'ye (basit görüntü-merkezleme) düşer — yani **pose'suz da tam çalışır**,
  sadece roll bilgisi olmaz.

---

## 4) "Benim PnP `talon_pose_estimator`" tam olarak nedir?

**Tek bir dosya:** `detection/talon_pose_estimator.py`. İçinde:

1. **Talon'un 3B modeli** (mm cinsinden, elle gömülü):
   - Origin = AM (aracın referans merkezi), gövde sağ-el çerçeve
     (+X kuyruğa, +Y yukarı, +Z sol kanat).
   - Ölçek: 1718 mm kanat açıklığı (SDK ile teyitli), burun→kuyruk 1087 mm.
2. **Şema-parametrik keypoint sırası** — pose modeli keypoint'leri hangi sırada
   verecek metadata'da yok, o yüzden iki şema destekli:
   - `"kuyruk_ucu"`: burun, kuyruk_ucu, sol_vtail, sag_vtail, sol_kanat, sag_kanat
   - `"motor"`: burun, motor, sol_vtail, sag_vtail, sol_kanat, sag_kanat
3. **PnP çözümü:** `cv2.solvePnPRansac` + `refineLM`, sonra reproj hatası 8px'i
   geçerse çözüm **reddedilir** (saçma poz süzülür).
4. **Çıktı:** hedefin kamera→dünya çerçevesinde konumu + yönelimi (roll/yaw) →
   OIPN güdümü bunu tüketir (hedefin yatışına göre nişan).

Özet: **hedefin 3B pozunu keypoint'lerden çözen matematik motoru.** Yön ve
mesafe verir; terminal görsel güdüme "hedef şöyle yatık, şu kadar uzakta" der.

---

## 5) Berat'ın `pose/` paketi vs benimki (neden "iki kaynak")

| | Benimki (yarisma) | Berat'ınki (main) |
|---|---|---|
| Amaç | **Uçuş anı** PnP çözücü | **Offline** keypoint etiketleme + kalibrasyon |
| Ana dosya | `detection/talon_pose_estimator.py` | `pose/` klasörü + `poz_tespit.py` |
| 3B model | mm, origin=AM, keypoint: burun/kuyruk_ucu/vtail'ler | cm, origin=telemetri-hedef, keypoint: burun/kanatlar/kuyruk-çifti/kuyruk_arka |
| Doğrulama | sentetik round-trip testi | `talon_keypoints.json` (sim'de doğrulanmış, flip_idx tanımlı) |
| Model (.pt) | henüz yok | `models/talon_pose.pt` var |

**Sorun:** İkisi de aynı fiziksel Talon'u (1.72 m) tarif ediyor **ama farklı
keypoint tanımı/sıra/birim/çerçeve** kullanıyor. Bu "**iki gerçek kaynağı**"
demek — dataset üretiminde hangisini baz alacağımıza karar verip diğerini ona
uydurmamız (ya da birini seçmemiz) lazım. Berat'ınki doğrulanmış + flip_idx'li
olduğu için **dataset'te onu baz almak** daha mantıklı; benim PnP çözücüm o 3B
tabloyu okuyacak şekilde ayarlanır.

---

## 6) Dataset üretimi main ile çakışır mı?

**Hayır.** Plan:
- Yeni klasör: `arac/dataset_uret/` (uçuş çekirdeğine **dokunmaz**).
- `kamera_model`, hareket-farkı hakemi, koşu-yöneticisi **import edilir,
  kopyalanmaz** (iki kaynak yasağı).
- main'deki `pose/` paketi ayrı dosyalar → **dosya çakışması yok.**
- Dataset klasörleri `.gitignore` ile git dışı.

→ **Dataset işi merge'den bağımsız yapılabilir.** Tek bağımlılık: 3B modeli
Berat'ın `talon_keypoints.json`'ından almak (çakışma değil, tercih).

---

## 7) Karar tablosu

| Konu | Durum | Öneri |
|------|-------|-------|
| GPS filtresi merge | main değiştirmemiş → **getiri yok** | Merge gerekçesi filtre DEĞİL |
| Güdüm (standoff↔intercept) | Aynı soruna 2 çözüm, ikisi de bayraklı | Merge'de **ikisini bayrakla koru** |
| Arayüz | İki farklı video-çıktı UI | Merge'in en zor kısmı; sonraya |
| Pose 3B model | İki kaynak (benim PnP ↔ Berat tablo) | Dataset'te **Berat'ı baz al** |
| Dataset | main ile çakışmaz | **Şimdi yapılabilir** |
| Merge | Gerekli değil (filtre yok), sonra denenebilir | Test için istersen bayrak-koru stratejisiyle kurarım |

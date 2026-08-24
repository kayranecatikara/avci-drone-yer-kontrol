# SABAH NOTLARI — 2026-08-18 (dikey kanalın tam denetimi)

> Kullanıcı: *"eminmisin dikey olarak kesinmi çünkü sanki faza geçtiğinde
> dikeyde sorunlar oluyor"* — **haklı çıktı.** Aşağısı o sorgunun ölçümü.

## ⭐ ÖNCE HATAMI DÜZELTİYORUM

Sabaha karşı "dikey düzeldi" derken **görsel fazın tamamının ortalamasını**
almıştım. Faz medyanı 5,79 s; ilk 1-2 saniyedeki bozulma o ortalamada erir.
Kullanıcının tarifi tam olarak o ilk saniyelerdi.

## Devir anının gerçek profili (10 Hz iz kaydı, geçerli satırlar)

| geçişten sonra | G3 öncesi (n=1895) | G3 sonrası (n=2306) |
|---|---|---|
| **t = 0** | −1,52 m | **−1,46 m** ← değişmedi |
| +0,75 s'e dek 1 m altı | %3 | **%6** ← değişmedi |
| +2,5-3 s (aşım tepesi) | +0,94 | **+0,41** |
| +4-5 s | −1,27 | **−0,11** |
| **doğru irtifadan geçip giden** | **%68** | **%69** ← değişmedi |

G3 **aşımı yarıya indirmiş**, ama devir anındaki açığı ve "geçip gitme"yi
hiç düzeltmemiş. Hatanın 1 m altına inmesi ~1,5 s sürüyor.

## ⚠ Devir anındaki −1,46 m bir ARIZA DEĞİL — tespiti ayakta tutuyor

`kareler.csv`, menzil bandı sabit tutularak:

| menzil | 1-2 m **altta** | **eş irtifa** | **üstte** |
|---|---|---|---|
| 5-10 m | %90 | %69 | %70 |
| 10-15 m | **%95** | %74 | %60 |
| 15-25 m | **%94** | %68 | **%48** |
| 25-40 m | %78 | %47 | **%22** |

Altta durmak her menzilde **20-26 puan tespit** kazandırıyor (hedef gökyüzü
fonunda kalıyor). Devir ölçütü 10 ardışık kare istediğine göre **ofseti
erken eritmek devrin kendisini bozar.** Çözüm ofseti kaldırmak değil,
geçişi SÖNÜMLEMEK.

## ✗ İKİ KAPI DA ÖLÜ — uçuştan ÖNCE yakalandı

- `AVCI_GPS_TERM_DIKEY`: son metrelerde direksiyonda %87-89 oranında
  **görsel yasa** var (0-4 m'de %89). GPS yasasının rampası orada
  fiilen hiç çalışmıyor.
- `AVCI_IBVS_TERM_DIKEY`: `DIKEY_UFUK` açıkken **kanıtlanabilir biçimde
  etkisiz**. Kodun kendi yorumu da söylüyor: *"ufuk kapısı açıkken w0 zaten
  ~0 olduğu için rampa doğal olarak etkisizleşir"*. Matematiği:
  `w0 = piksel_elev(taban) + pitch = −pitch + pitch = 0` → `cy = taban`.

Bu iki kontrol olmasa bir saatlik uçuş kampanyası hiçbir şey yapmayan bir
düğmeye harcanacaktı.

## ⭐⭐ KÖK NEDEN: seyir dalında SÖNÜMLEME YOK

`bbox_ibvs.py` içinde yalnız iki `vz =` ataması var:

| satır | dal | sönümleme |
|---|---|---|
| 1924 | `if terminal:` | **var** — `vz_nisan + K_VZ_D·(vz_nisan − vz_gerçek)` |
| 1930 | `else:` (TUTUŞ/seyir) | **YOK** — saf oransal |

Devir menzili medyan **12,7 m**, terminal mandalı çok daha yakında.
**Devirden sonraki bütün geçici davranış sönümlemesiz dalda yaşanıyor.**

Aşım oranı 0,41/1,46 = **%28** → `Mp = exp(−πζ/√(1−ζ²))` tersinden
**ζ ≈ 0,375** (az sönümlü; ideal ~0,7 → aşım ~%5). Saf oransal denetleyici
+ taşıma gecikmesi tam olarak bunu üretir.

**Bu, depoda BEŞİNCİ "yazılmış ama bağlanmamış" vaka.**

## Yama: `AVCI_IBVS_KVZD_SEYIR` (varsayılan 0 = kapalı)

Doğrulandı:
- kapalıyken **bit-aynı** (25/25 test noktası)
- açıkken tüm doymamış noktalarda **monoton sönümleme**
- durgunda kazanç oranı tam **1,600 = (1+Kd)** — teorinin öngördüğü
- test takımı: **6 kaldı / 566 geçti**, yamadan öncekiyle aynı

## Dikey komut → tepki zinciri SAĞLIKLI

⚠ **TUZAK:** `sp_vz` NED (+ = aşağı), `olc_vz` ise (+ = yukarı). Ham
korelasyon −0,774 çıkıyor ve "dikey ters çalışıyor" gibi görünüyor.
**Hakem: gerçek irtifa türevi.** `olc_vz` ile korelasyon +0,384 → yukarı;
`sp_vz` ile −0,254 → NED. Yani **kural farkı, arıza değil.**

Düzeltilmiş (ikisi de NED):

| küme | korelasyon | eğim | işaret uyumu |
|---|---|---|---|
| görsel faz | +0,774 | 0,717 | **%93** |
| görsel, <8 m | +0,845 | 0,715 | **%97** |
| görsel, <4 m | +0,894 | 0,669 | **%97** |

Yani yasa doğru yönü emrediyor, araç itaat ediyor — ama komutun ancak
**~%70'ini** uyguluyor.

**Sıfır komutta araç yine de 0,17 m/s tırmanıyor** (karelerin %66'sı),
5 saniyede 0,88 m. Bu momentumun geç sönmesidir — sönümleme yamasının
ölçülmüş gerekçesi.

## CPA ayrışımı: asıl kaçırma DİKEY DEĞİL, YATAY

| | G3 öncesi | G3 sonrası |
|---|---|---|
| en yakın menzil | 7,41 m | **3,28 m** |
| **yatay** | 7,24 m | **3,08 m** |
| **dikey** | 1,39 m | **1,00 m** |
| dikeyi 1 m altı | %20 | **%50** |

Dikeyin payı %24. ⚠ Hafızadaki "yatay 8-14 cm iken dikey 1,8-2,1 m" notu
birkaç iyi geçişten alınmıştı; toplu veride **tersi** doğru.

Ayrıca `VISUAL & r≤3 m` kümesinde dz medyanı G3 öncesi **+0,47 m**
(üstten geçiyorduk), sonrası **−0,35 m**, |dz| 1,04 → **0,84**. Yani
sistematik sapma kalmadı; kalan **saçılma**, ve saçılmayı sönümleme kapatır.

## Koşan deney: `arac/recete_sonum.json` (5 kol × 14 dk)

| kol | KVZD_SEYIR | K_VZ | amaç |
|---|---|---|---|
| S0_taban_a | 0 | 0,5 | taban |
| S1_sonum06 | 0,6 | 0,5 | terminalde kanıtlanmış değer |
| S0_taban_b | 0 | 0,5 | serpiştirilmiş taban tekrarı |
| **S2_kazanc_TEK** | 0 | **0,8** | **ayırt edici olumsuz kontrol** |
| S3_sonum10 | 1,0 | 0,5 | doz-cevap üst ucu |

**S1 vs S2 deneyin kalbi:** ikisinin durgun kazancı aynı (0,5×1,6 = 0,8),
ama S2'de hız geri beslemesi yok. S1 yenerse etki sönümlemedendir;
berabere kalırlarsa etki yalnız kazançtandır ve **terim geri alınır**.

Hüküm: `python arac/sonum_hukum.py` — mekanizma kapısı `sp_vz` içindeki
`olc_vz` katsayısını ölçer, **−Kd çıkmalı**; çıkmazsa o kolun sonucu okunmaz.

Yedek: `yedek/SEYIR_SONUM_ONCESI_20260818_091431/`

## ⭐⭐ ÖNCELİĞİ DEĞİŞTİREN BULGU: kaçırmanın %60'ı BOYUNA

En yakın geçiş anı, hedefin çerçevesinde ayrıştırıldı (n=1876, G3 sonrası):

| eksen | medyan | p75 | 1 m altı |
|---|---|---|---|
| **BOYUNA** | **2,63 m** | 5,67 | **%25** |
| YANAL | 0,78 m | 1,57 | %59 |
| DİKEY | 1,00 m | 1,37 | %50 |

**Paylar: boyuna %60 · yanal %18 · dikey %23.**
İşaretli boyuna medyan **−1,89 m** = en yakın anda hedefin ARKASINDAYIZ.

Tek başına 1 m'nin altına inmeyi engelleyen eksen:
- **yalnız BOYUNA > 1 m : %19,4**
- yalnız DİKEY  > 1 m : %7,3
- yalnız YANAL  > 1 m : %3,0
- üçü birden 1 m altı : %12,9

→ **Yanal eksen aslında EN İYİ durumda olan eksen.** Kullanıcının "yönü
açısı tutturmuyor" tarifinin ölçülebilir karşılığı yanal değil BOYUNA:
kuyruk takibinde kapanma 21−18 ≈ 3 m/s, en yakın ana geldiğimizde
(tanım gereği kapanma sıfırlanır) hâlâ ~1,9 m geride kalıyoruz.

⚠ Bu, dikeyin önemsiz olduğu anlamına GELMEZ (%23 pay, ve tek başına
%7,3 engelleyici) — ama bir sonraki büyük kazanç boyuna eksende.
⚠ İç daire kesme ve lead tavanını büyütme bu gece DENENDİ ve İKİSİ DE
KAYBETTİ; yani "kestirip öne geç" fikrinin naif biçimi çalışmıyor.

### ✗ "Kapanma bütçesini büyüt" hipotezi — UÇMADAN ÇÜRÜTÜLDÜ
İlk aklıma gelen "hız tavanını aç" idi. Ölçtüm (n=34363):

| ölçü | değer |
|---|---|
| bizim hız medyan | **20,2 m/s** |
| p90 / p99 | 23,8 / 25,4 |
| `V_MAX=18` üstünde geçen kare | **%65** |
| `V_MUTLAK=26` üstünde | **%0,5** |

İleri besleme koruması (`FF_KORU`) zaten V_MAX'i geçiriyor; gerçek tavan
26 ve ona neredeyse hiç dayanmıyoruz. **Hız bağlayıcı kısıt DEĞİL** →
o deney boşa giderdi. Boyuna kaçırma bir hız değil, GEOMETRİ sorunu.

⚠ Ayrıca `h_hiz` sütunu KULLANILMAZ: medyanı 0,0 (n=34363), yani hedef
hızını oradan okuyan her analiz çöp. Hedef hızı `hx,hy` türevinden alınmalı.

## ⭐⭐⭐ EN BÜYÜK KALDIRAÇ: YAKLAŞMA GEOMETRİSİ (aspect)

Ayna + G3 düzeltmelerinden SONRA yeniden ölçüldü (n=1842 CPA):

| CPA'daki aspect | pay | CPA medyan | **1,5 m altı** |
|---|---|---|---|
| 0-60° kesme | %19 | 2,44 | %22 |
| **60-90° kesme** | **%4** | **1,41** | **%55** |
| 90-120° | %6 | 1,76 | %39 |
| 120-150° | %17 | 2,65 | %22 |
| **150-180° saf kuyruk** | **%54** | **4,98** | **%9** |

aspect medyanı **154°**; 30 m'de kesme geometrisinde olma oranı **%6**.

**Yaklaşmaların yarısından fazlası en kötü bantta, en iyi bant ise
toplamın %4'ü.** 2026-08-17'deki "kesme %42 / kuyruk %0.5" bulgusu
düzeltmelerden sonra da AYAKTA — hatta bant ayrımı 6 kat.

### Bu, "boyuna %60" bulgusunun açıklaması
CPA'da 1,89 m geride kalmak bir ayar hatası değil, **kuyruk takibinin
imzası**. Ve kuyrukta kapatmak geometrik olarak kazanılamaz: dönüş
yarıçapımız 27,7 m, hedefinki 27,1 m — dönüşünün içine giremiyoruz.
Hız da suçlu değil: hedef 17,95 m/s sabit, biz 20,6-22,7 m/s, üstünlük
+2,8 m/s ve yakın menzilde EN BÜYÜK (+4,46). 1,89 m'yi 0,68 s'de
kapatacak hız var; kapatmayan şey geometri.

### Neden kuyruktayız: TASARIM
GPS istasyonu `bx,by = -vel/|vel|` ile hedefin **hız yönünün gerisine**
konuyor. Yani sistem bizi kasten kuyruğa götürüyor. Bu, uzaktan güvenli
yaklaşma ve kamera nişanı için mantıklıydı; ama vuruş için en kötü bant.

### Sıradaki iş (dikey deneyi bittikten SONRA)
Hedef **sabit oval** uçuyor: 17,99 m/s, 531 m tur, 29,63 s periyot, CCW,
oval 220×96 m. Tamamen öngörülebilir. Doğru hamle kovalamak değil,
**yolunun ilerisinde bir noktada kesişmek**.
⚠ "İç daire kesme" bunu denedi ve KAYBETTİ — ama o yalnız "içeri" kaydırdı,
"ileri" bileşenini hiç eklemedi. Ayrım bu olabilir.

## ✗ ÜÇÜNCÜ ÖLÜ DÜĞME: `recete_kestirim.json` yazılmamış bir özelliği çağırıyor

Reçetenin kolları `AVCI_IBVS_KESTIRIM_UFUK` ve `AVCI_IBVS_KESTIRIM_MODEL`
kullanıyor. **İkisi de kodda 0 yerde geçiyor.** Ve `AVCI_IBVS_KESTIRIM`
kodun kendi deyimiyle *"SALT GÖZLEM"* (:1415, :2722) — yalnız `kest_*`
sütunlarını doldurur, komuta dokunmaz.

→ O reçete koşulsaydı **dört kol da tabanla aynı** davranacak, sonuç
"kestirim işe yaramıyor" diye okunacaktı. **Tamamen yanlış bir çürütme.**
Öngörülü nişan ÖNCE YAZILMALI, sonra sınanmalı.

Bugün yakalanan ölü düğme sayısı: **3** (GPS TERM_DIKEY pratikte çalışmıyor,
IBVS TERM_DIKEY kanıtlanabilir no-op, KESTIRIM salt gözlem + 2 var olmayan
değişken). Hepsi uçuştan ÖNCE yakalandı.

## ▶ SIRADAKİ ADAY (dikey deneyi bittikten sonra): `AVCI_GPS_ARKA_KISALT`

Çalışan istasyon geometrisi:
| değişken | değer | ne yapar |
|---|---|---|
| `RANGE_SET` | 8,0 m | istasyon menzili |
| `ISTASYON_ELEV_DEG` | 15° | → 2,07 m alt, 7,73 m arka |
| `IC_KAYMA` | **14,0 m** (AÇIK) | dönüş merkezine kayma |
| **`ARKA_KISALT`** | **0,0 (KAPALI)** | dönüşte arka bileşeni eritir |

Kod bağlı ve gerçek: `d_arka = d_behind_eff * (1 - ARKA_KISALT * olcek_don)`.
Açılırsa istasyon dönüşte saf-içeriye kayar → aspect 128° yerine ~90°'ye,
yani **ölçülen en iyi banda** (%55 başarı) yaklaşır.

⚠ Bu, gecenin başarısız "iç daire kesme" denemesinden FARKLI bir düğme:
o `AVCI_KOPRU_IC` / `AVCI_GPS_IC_ORAN` idi; bu `AVCI_GPS_ARKA_KISALT`.
⚠ Mekanizma kapısı: `d_arka_m` sütunu (log'da var) dönüşlerde küçülmeli.

### ✗ `ARKA_KISALT` de ELENDİ (dördüncü düğme, yine uçmadan)

Saf geometri hesabı (n=209.361 örnek, istasyonun nerede duracağı):

| ARKA_KISALT | aspect medyan | 60-90 bandı | <90 (kesme) | 150+ (kuyruk) |
|---|---|---|---|---|
| 0,0 (bugün) | 148° | %0 | %0 | %49 |
| 0,5 | 143° | %0 | %0 | %46 |
| 0,7 | 141° | %0 | %0 | %45 |
| 1,0 | 136° | %0 | %0 | %44 |

**Kesme bandına hiç ulaşmıyor.** Sebep: hedefin dönüş hızı medyanı
**3,0 °/s**, oysa `IC_OMEGA_REF = 0,15 rad/s ≈ 8,6 °/s`'de tam açılıyor
→ ölçek çarpanı 0,35'te kalıyor, içeri kayma 14 m yerine 4,9 m.
Hedef zamanının %46'sını <5 °/s ile, yani **düz** uçuyor.

### ⭐ Bundan çıkan ASIL DERS
Kesme geometrisi istasyon yerleşiminin ürettiği bir şey DEĞİL. Hafızadaki
mekanizma doğru: *"kuyrukta aşıyoruz → hedef sabit pistinde dönüp bize
geliyor → kesme kazara oluşuyor."* Yani kaldıraç **yerleşimde değil,
ZAMANLAMADA**. Hedef 531 m'lik ovalini 29,63 s'de tamamlıyor; doğru hamle
onu kovalamak değil, **pistinin ileri bir noktasında buluşmak**.

Bu, mevcut hiçbir düğmeyle yapılamaz — **yazılması gerekir** (öngörülü
nişan; `recete_kestirim.json` bunu varsayıyor ama kodu yok). Riskli ve
büyük bir değişiklik olduğu için tek başına, gece yarısı, doğrulamasız
yapılmamalı. Önce dikey deneyi bitsin.

**Bugün elenen düğme sayısı: 4** — hepsi uçuştan önce, sıfır uçuş saati
harcanarak. (GPS TERM_DIKEY · IBVS TERM_DIKEY · KESTIRIM · ARKA_KISALT)

## ⭐⭐⭐ SÖNÜMLEME DENEYİ — HİPOTEZ ÇÜRÜDÜ (kendi olumsuz kontrolümle)

| kol | aşım | geçip giden | CPA anı | **\|dz\|@CPA** | <1,5 m | vuruş |
|---|---|---|---|---|---|---|
| S0_taban_a (fps 41) | %59 | %81 | 2,92 s | 0,90 | %13 | 4 |
| S0_taban_b (fps 23) | %54 | %82 | 2,45 s | 0,98 | %15 | 3 |
| **S1 sönümleme 0,6** | **%26** | **%61** | 2,40 s | **1,03** | %10 | 2 |
| **S2 kazanç TEK 0,8** | **%76** | %82 | **2,20 s** | **0,71** | **%28** | **6** |

### Mekanizma kapısı KUSURSUZ çalıştı
`eps~0 & tırmanırken artık` (taban ortalamasına göre kayma):
S0_a −0,011 · S0_b +0,011 · **S2 +0,014** · **S1 +0,163** (teorinin %40'ı).
S2'nin kazancı yüksek ama sönümlemesi yok → kapı onu doğru şekilde
"kapalı" okudu. Yani kapı gerçekten **sönümlemeyi** ölçüyor, kazancı değil.

### ✗ Neden hipotez çürüdü: AŞIM CPA'DAN SONRA OLUYOR
Dört kolun dördünde de aşım anı, en yakın geçişten **+0,63…+1,27 s SONRA**.
Sonuç o an çoktan belirlenmiş → **aşım vuruşu etkilemez.**

Ben aşımdan `Mp=exp(−πζ/√(1−ζ²))` ile ζ≈0,375 türetip "az sönümlü" teşhisi
koydum, yamayı yazdım, mekanizmasını doğruladım — **hepsi doğruydu ve yama
tam tasarlandığı gibi çalışıyor.** Ama önemi olmayan bir kusuru düzeltiyor.
Olumsuz kontrol olmasaydı bunu kazanç sanıp varsayılan yapacaktım.

### ⭐ Gerçek kaldıraç: DİKEY KAZANÇ (K_VZ)
Kazancı artırmak aşımı KÖTÜLEŞTİRİYOR (%76) ama:
- en yakın geçişe **daha erken** varıyor (2,20 s vs 2,45-2,92)
- **\|dz\|@CPA 0,71** (taban 0,94, sönümleme 1,03)
- `<1,5 m` %28 (taban %13/%15), `<1 m` %7 (taban %2/%2)

Önemli olan aşımı önlemek değil, **CPA'ya KADAR hatayı kapatmak**.
⭐ Bu, 2026-08-18 gecesinin `K_VZ=0.9` bulgusunun **BAĞIMSIZ TEKRARI**
(o gece: kapatma %69 vs %60,5, 8 vuruş). İki ayrı kampanya aynı yöne
işaret ediyor.

### ⚠ Henüz varsayılan YAPILMADI — eksikler
- S2'nin n'i düşük (29-33 yaklaşma), `<1,5 m` farkı 13-15 puan =
  gürültü p90'ı (17 puan) ile **sınırda**
- K_VZ için serpiştirilmiş, tekrarlı bir doğrulama koşusu şart
- `AVCI_IBVS_KVZD_SEYIR` varsayılan **0 (kapalı)** kalıyor; kod duruyor,
  bit-aynılığı test edilmiş, ileride terminal-sonrası davranış için lazım olabilir

### ▶ ÖNGÖRÜ (S3 sonucunu görmeden yazıldı)
S3 (sönümleme 1,0) aşımı S1'den de düşük gösterecek AMA `|dz|@CPA` ≥ 1,03
ve CPA anı ≥ 2,40 s çıkacak — çünkü sönümleme CPA'ya varışı yavaşlatıyor.

## ⚖ SÖNÜMLEME DENEYİ — NİHAİ HÜKÜM (5 kol, ~70 dk)

| kol | Kd | K_VZ | aşım | \|dz\|@CPA | <1,5 m | CPA anı | vuruş |
|---|---|---|---|---|---|---|---|
| S0_taban_a | 0 | 0,5 | %59 | 0,90 | %13 | 2,92 s | 4 |
| S0_taban_b | 0 | 0,5 | %54 | 0,98 | %15 | 2,45 s | 3 |
| S1_sönümleme | 0,6 | 0,5 | **%26** | 1,03 | %10 | 2,40 s | 2 |
| **S2_kazanç_TEK** | 0 | **0,8** | %76 | **0,71** | **%28** | **2,20 s** | 6 |
| S3_sönümleme | 1,0 | 0,5 | %39 | 0,81 | %21 | 2,83 s | 5 |

### ✓ Mekanizma kanıtlandı
Kapı (eps~0 & tırmanırken artık, taban ort.'na göre kayma):
S0_a −0,011 · S0_b +0,011 · **S2 +0,014** · S1 **+0,163** (teorinin %40'ı).
S2'nin kazancı yüksek, sönümlemesi yok → kapı "kapalı" okudu. Kapı gerçekten
sönümlemeyi ölçüyor. Ve kontrol teorisi doğrulandı: **kazanç tek başına
aşımı %76'ya çıkarıyor, sönümleme %26'ya indiriyor.**

### ✗ Ama hipotez ALAKASIZ çıktı
Aşım, en yakın geçişten **+0,63…+1,27 s SONRA** oluyor (5 kolun 5'inde).
Sonuç o an belirlenmiş → **aşım vuruşu etkilemez.** Yama çalışıyor ama
önemi olmayan bir kusuru düzeltiyor. → `AVCI_IBVS_KVZD_SEYIR` varsayılan
**0 (kapalı)** kalıyor. Kod duruyor, bit-aynılığı test edilmiş.

### ⚠ İKİ ÖNGÖRÜM DE TUTMADI — kayda geçsin
1. **S3 öngörüsü (sonucu görmeden yazmıştım):** "Kd=1,0 aşımı S1'den de
   düşük gösterecek, `|dz|@CPA` ≥ 1,03 olacak." Gerçek: aşım %39
   (S1'in %26'sından YÜKSEK), `|dz|@CPA` 0,81 (1,03'ten DÜŞÜK).
   **3 iddiadan 2'si yanlış.** Doz-cevap monoton değil → gürültü büyük.
2. **"`|dz|@CPA` sıkı bir ölçüt" sezgim:** iki tabanın 0,08 sapmasına
   bakıp öyle sanmıştım. 10 taban çiftiyle ölçünce medyan **0,144**,
   p90 **0,339**. Şanslı bir çiftmiş.

### Nihai: KESİN KAZANAN YOK
Gürültü tabanına göre (n=10 çift): `|dz|@CPA` medyan 0,144 / p90 0,339;
`<1,5 m` medyan 10 / p90 17 puan.
- S1 (+0,09) → gürültü · S3 (−0,13) → gürültü
- **S2 (−0,23) → SINIRDA** (ve `<1,5 m`'de +14 puan, p90 17 ile sınırda)

⭐ S2 = `K_VZ 0,5→0,8`. Bu, 2026-08-18 gecesinin `K_VZ=0.9` bulgusunun
**ikinci bağımsız tekrarı**. Üç kampanya aynı yöne işaret ediyor ama
hiçbiri tek başına gürültüyü aşmıyor → `arac/recete_kazanc.json`
(taban-aday-taban-aday-doz, 5 kol) KOŞUYOR.

## ⭐⭐⭐⭐ ANAHTAR ÖLÇÜM: hedef 30 s ilerisine kadar 0,65 m doğrulukla bilinebilir

Kısa ufuklu kestirim ZAYIF (bu yüzden lead tavanını büyütmek kaybetti):

| ufuk | sabit hız (CV) | sabit dönüş (CT) | CT p90 |
|---|---|---|---|
| 0,5 s | 1,24 m | 0,93 m | 2,07 |
| 1,0 s | 2,47 m | 1,59 m | 4,45 |
| 2,0 s | 6,42 m | 3,80 m | 12,69 |

→ 1-2 s'lik öngörülü nişan, düzeltmeye çalıştığı kadar hata sokar.

**AMA hedef KAPALI VE TEKRARLAYAN bir oval uçuyor.** Ölçülen periyot
**29,60 s** (p10 = p90 = 29,60; hafızadaki 29,63 ile birebir, n=40 parça).
"Bir tur öncesindeki konum" kestiricisi (n≈4100/ufuk):

| ufuk | medyan hata | p90 |
|---|---|---|
| 2 s | 1,06 m | 2,33 |
| 5 s | 0,72 m | 2,01 |
| **10 s** | **0,62 m** | **1,86** |
| **20 s** | **0,65 m** | **1,88** |
| **30 s** | **0,66 m** | 2,31 |

**Hata ufuktan BAĞIMSIZ ve ~0,65 m'de sabit.** Hedefin 30 s sonraki yeri,
2 s sonraki yerinden **6 kat daha doğru** biliniyor.

### Neden bu her şeyi değiştiriyor
Kesme geometrisi (aspect 60-90°) `<1,5 m` başarısını %9'dan **%55**'e
çıkarıyor ama bugün yaklaşmaların yalnız **%4'ü** orada — çünkü kesme
KAZARA oluşuyor (hedef ovalinde dönüp bize geliyor). Tekrar kestiricisiyle
kesme noktası **önceden hesaplanabilir**: pusu kurulabilir.

### Uygulama taslağı (KULLANICI ONAYI OLMADAN YAZILMAYACAK)
Aşamalı ve her aşama tek başına sınanabilir:
1. **Halka tampon**: hedefin son ~35 s konumu (10 Hz → 350 örnek, önemsiz bellek)
2. **Periyot kestirimi**: `argmin_P median|pos(t) − pos(t−P)|`, 20-42 s taraması.
   ⚠ Bir tur (30 s) gözlem şart → ilk 30 s eski davranış.
   ⚠ Mekanizma kapısı: kestirilen P, 29,6 ± 1,0 s dışındaysa kapı KAPALI kalsın.
3. **Buluşma noktası**: hedefin t+h konumunu tekrar kestiricisiyle al; bizim
   oraya varış süremizle tutarlı h'yi çöz (sabit nokta, 2-3 iterasyon yeter)
4. **İstasyonu oraya kur** — mevcut geometri kodu aynen kullanılabilir,
   yalnız `est_x, est_y` yerine öngörülen konum girer
5. **Olumsuz kontrol**: periyodu kasten %20 yanlış ver → sonuç KÖTÜLEŞMELİ.
   Kötüleşmezse kazanç kestirimden gelmiyor demektir.

⚠ Risk: bu davranışı değiştiren bir kapıdır → **çevrimdışı replay ile
değerlendirilemez** (off-policy tuzağı). Uçuşta ölçülmeli.
⚠ 8 varyant var; oval yönelim/irtifa/merkez olarak DEĞİŞİYOR. Periyot
her koşuda YENİDEN kestirilmeli, sabit yazılmamalı.

## ⭐⭐⭐⭐ KULLANICININ 3 GÖZLEMİ = TEK KÖK NEDEN: DÖNÜŞ TAVANI

Kullanıcı (2026-08-18 sabah): *"bi frenleme var faza geçtikten sonra"*,
*"arkadan geldiği halde aşağı iniyor"*, *"tam dönebilme kabiliyeti varken
dönmüyor"*, *"bbox kadrajdan çıkmaya başlayınca burnu o tarafa çevirsin"*.

### Ölçüm: hedefi kadrajda tutmak için gereken kerteriz hızı (n=88.665)

| menzil | gereken LOS hızı | tavanımız (12/V) | **tavanı aşan** |
|---|---|---|---|
| **0-3 m** | **122,7 °/s** | 29,8 | **%84** |
| 3-5 m | 72,6 | 30,2 | %75 |
| 5-8 m | 44,8 | 30,6 | %63 |
| 8-12 m | 25,8 | 31,9 | %39 |
| 12-18 m | 14,4 | 32,1 | %19 |
| 18-30 m | 8,0 | 31,6 | %3 |

**Yakın menzilde 4 KAT daha hızlı dönmek gerekiyor.** `ω_max = a_max/V`
bir ayar değil FİZİK: hız vektörünü döndürmek yanal ivme ister.
→ "Kabiliyet var ama dönmüyor" DEĞİL, **kabiliyet YOK çünkü hızlıyız.**

| hız | dönüş tavanı |
|---|---|
| 22 m/s | 31,3 °/s |
| 18 m/s | 38,2 |
| 14 m/s | 49,1 |
| 10 m/s | **68,8** |

### Bu, gözlemlerin HEPSİNİ açıklıyor
- kutu kadrajdan taşıyor (0-4 m'de kareler %12 kenarda, kenar tespit
  kaybı riskini **3,1 kat** artırıyor)
- manevrada tutturamıyor
- önünden geçerken dönemiyor
- **kullanıcının bbox-kenar fikri, önce bu çözülmeden İŞE YARAMAZ**
  (burun döner, araç dönmez)

### Diğer iki gözlem de doğrulandı
- **Frenleme**: medyan +0,03 m/s ama kuyruk gerçek — devirlerin **%17'sinde
  >1 m/s**, %5'inde >2 m/s frenleme (p5 −2,07).
- **Arkadan gelirken altta**: aspect>140°'de dz medyan **−1,31 m, %79 altta**.
  Tasarım gereği (istasyon 1,55-2,07 m altta; tespit avantajı için) ama
  vuruş anında da altta kalmamıza yol açıyor.

### ▶ SIRADAKİ TEST (K_VZ koşusu bitince): DÖNÜŞ BÜTÇESİ
`AVCI_IBVS_DONUS_BUTCE` + `AVCI_IBVS_ARAC_TAU` — terminalde hızı düşürüp
dönüş tavanını büyütür. Hafızada **"M3 kazandı: CPA 3,61→2,32, <3 m
%40→%58, temas 0→3"** yazılı ama **TEK KOŞU, hiç doğrulanmadı.**
Artık neden çalışması gerektiğinin fiziği de elimizde.

### Kayıt düzeltildi
- **Delik vardı**: 07:43→09:20 arası 1 s 37 dk kayıt yok (kullanıcı çıkarken
  durdurmuştum). Kapatıldı.
- Hız **1 Hz → 5 Hz** (`--hz 5 --sadece-yakin 60`): 2 saniyelik angajmanda
  5 örnek yerine 10+ örnek. 60 m dışında yazmaz → disk korunur.

## ⭐ "FRENLEME" GÖZLEMİ — doğrulandı, ölçüldü, maliyeti bulundu

Devirde **hız komutu sıçraması** (devir başına, n=1794):
p5 −2,41 · p25 +0,68 · **p50 +1,39** · p75 +2,54 · p95 +6,80 m/s
|sıçrama| > 2 m/s olan devir **%39**, > 4 m/s **%16**.
**%86 yukarı, %14 AŞAĞI (fren).**

Ve frenleyen devirler kötü bitiyor:

| devirde gerçek hız değişimi | n | en yakın | <1,5 m |
|---|---|---|---|
| **sert fren (<−1,5)** | 270 | **6,48 m** | **%1** |
| hafif fren | 289 | 6,93 | %2 |
| değişim yok | 487 | 5,14 | %4 |
| **hızlanma (>+0,5)** | 748 | **4,51 m** | %4 |

Fark **~2 m** — gürültü tabanının (0,91 m) iki katı. korelasyon −0,100
(zayıf ama grup farkı gerçek).

**Kök neden: devir hız komutunda da PÜRÜZSÜZ DEĞİL.** Dikeyde 2,91 m
setpoint sıçraması vardı; yatayda 1,4-2,3 m/s komut sıçraması var.
→ *bumpless transfer*: komutu basamak yerine RAMPAYLA devret.

## ▶ SIRADAKİ İKİ ADAY (ikisi de kullanıcının gözleminden çıktı)
1. **`arac/recete_donus.json` (HAZIR)** — dönüş bütçesi. Kollar:
   T0_taban_a · T1_m3_taban15 · T0_taban_b · T2_taban10 · T3_butce_TEK.
   ⚠ Hız tabanı 15 m/s YETMİYOR (tavan 45,8°/s; 3-5 m'de 72,6 gerekiyor)
   → T2 kolu tabanı 10'a indiriyor (tavan 68,8°/s). Fizik reçetede yazılı.
   ⚠ Mekanizma kapısı: bütçe açıkken korelasyon(|ω_talep|, hızımız) NEGATİF olmalı.
2. **Pürüzsüz devir (yazılacak)** — hız komutunu N saniyede rampala.
   Kapı varsayılan KAPALI, olumsuz kontrol: rampayı TERS yönde uygula.

## Kullanıcının bbox-kenar fikri — araştırma sonucu
Kutu genelde ortada (cx 0,512 / cy 0,548), kareler yalnız %3,9'unda kenarda.
AMA kenarda olmak tespit kaybı riskini **3,1 kat** artırıyor (%9 vs %3),
ve **0-4 m'de kenar oranı %12**. Yani fikir doğru yeri gösteriyor.
⚠ Ama tek başına uygulanamaz: 0-3 m'de gereken dönüş 122,7°/s, tavan 29,8°/s
→ burun döner, ARAÇ DÖNMEZ. **Önce dönüş bütçesi, sonra bu.**

## ⭐⭐ TEKRAR KESTIRICISI KISA UFUKTA DA KINEMATIGI YENIYOR

| ufuk | sabit hız (CV) | sabit dönüş (CT) | **tekrar** | kazanç |
|---|---|---|---|---|
| 0,3 s | 1,07 | 0,93 | **0,64** | %31 |
| 0,5 s | 1,46 | 1,12 | **0,60** | %47 |
| 1,0 s | 2,58 | 1,73 | **0,57** | **%67** |
| 1,5 s | 4,08 | 2,54 | **0,54** | %79 |
| 2,0 s | 6,14 | 3,68 | **0,49** | **%87** |

Tekrar hatası her ufukta **~0,5 m'de sabit**; kinematik patlıyor.
→ Bu, lead tavanını 9°'den büyütmenin neden KAYBETTİĞİNİ de açıklıyor:
kinematik lead 1 s'de zaten 2,58 m sapıyor, ileri bakmak hatayı büyütüyor.

### ⛔ AMA GÖRSEL FAZA BAĞLANAMAZ — YARIŞMA KURALI D0
`bbox_ibvs.py` başlığı: *"görsel temas varken hedefin GPS'i güdümde
KULLANILAMAZ — canlı GPS akışı yasak"*, ve döngünün canlı GPS'e erişimi
**yapısal olarak yok** (callback değil, sayı üçlüsü geçiliyor).
Tekrar kestiricisi sürekli hedef konumu ister → canlı GPS.

**Olası yol (KULLANICI KARARI ŞART):** devir anında hedefin bir turluk
yolunu + periyodunu DONDUR, görsel faz boyunca ondan kestir. Canlı GPS
okunmaz; mevcut `ff_hiz` dondurulmuş taşıyıcısıyla aynı sınıf. Lafza uyuyor;
ruhuna uygunluğu YORUM meselesi ve yanlış yorum DİSKALİFİYE demek.
⚠ Bu karar benim değil — sorulmadan yapılmayacak.

### ✓ PUSU bu kısıttan ETKİLENMİYOR
Pusu GPS fazında çalışır; GPS fazının hedef konumunu kullanması tasarımın
kendisidir (`get_plane()`). D0 yalnız GÖRSEL temas anını bağlar.

## 👁 KARELERE BAKARAK BULUNANLAR (kullanıcı: "sadece arkadan yapamazsın")

Gerçek kamera karelerine bakıldı (5 Hz kayıt). Loglardan görünmeyen dördü:

1. **Ağır hareket bulanıklığı ve büyük roll** — devir karesinde ufuk belirgin
   yatık, görüntü smear. Piksel türevinden (LOS hızı) beslenen her terim
   bundan zarar görür.
2. **Devir anında hedef ufuk çizgisinin ÜSTÜNDE, minicik bir nokta**
   (17,6 m'de ~8-10 px). Gökyüzü de değil yer de değil — en zor fon.
   ⭐ Bu, ofsetin METRE değil AÇI olması gerektiğini gösterdi: 17 m'de
   1,46 m altta olmak yalnız 4,7° yükseliş demek.
3. **Güneş kadrajın içinde** (2,18 m'lik geçişte hedefin hemen sağında).
4. **Kendi pervanelerimiz kadrajın kenarlarında.**

### ⭐ Ölçüm: TESPİT, METREYE DEĞİL AÇIYA BAĞLI
| hedefin yükseliş açısı | tespit | 15-30 m'de |
|---|---|---|
| < −5° (biz üstte) | %58 | %41 |
| −5..0 | %50 | %50 |
| 0..3 | %54 | %81 |
| **3..6** | **%89** | **%94** |
| **6..10** | **%90** | %91 |
| 10..20 | %64 | %96 |
| > 20 | %66 | %96 |

Mevcut açımız menzille DÜŞÜYOR: 5-10 m'de +5,6° → 25-40 m'de +2,5°
→ 40-70 m'de +1,6° (tespit %35). **İstasyon ofseti sabit metre olduğu için
uzakta açı kapanıyor ve tam da tespitin gerektiği yerde hedef ufka yapışıyor.**
→ Somut öneri: ofseti AÇI olarak tanımla (uzakta daha çok altta ol).

## ⚠ "lead dengesiz" — OLGU DOĞRU, ZARARI KANITLANMADI
Ölçüldü (`bbox_ibvs` logu, 5193 kare): lead **%32 tavanda** (±9/±25°),
`|d(lead)/dt|` p99 **421,9 °/s**, örneklerin %7'si >100 °/s, ardışık
işaret değişimi **%7,7**. Yani kullanıcının tarifi olgusal olarak DOĞRU.

**AMA sonuca zararı gösterilemedi.** Ham korelasyon −0,277 (zıplama arttıkça
CPA daha iyi) — bu TERS NEDENSELLİK: yakınlaştıkça LOS hızı 1/R ile büyür.
Menzil sabitlenince (n=697 epizot): 0-12 m'de düşük zıplama iyi (CPA 2,89
vs 3,42, n=36), 12-20 m'de fark yok, 20-40 m'de TERS. Korelasyonlar
−0,10…−0,25, zayıf.
→ **Şu an lead'i süzmeyi haklı çıkaracak kanıt YOK.** Ölçüm tekrarlanmalı.

## ⛔ OYUN ÇÖKTÜ — ve ölçüm bunu fark etmiyordu (kullanıcı yakaladı)
12:25-12:29 arası oyun süreci öldü; kampanya **donmuş telemetriyi** kaydetmeye
devam etti. O koşunun **%27,9'u donmuş satır**, en uzun donma **235 saniye**,
ve 8569 satırın **8568'i geçerlilik süzgecinden geçiyordu**.
Bugünkü diğer koşularda da %8,8-11,2 donmuş veri var.

→ `arac/gecerlilik.py` yazıldı, iki hüküm betiğine bağlandı.
→ Nöbetçi çökmeyi yakalayıp toparladı (275 s) ama kampanya o sürede kayıt
  almaya devam ediyor; boşluk ölçüm tarafında kapatıldı.
→ `K_VZ=0.8` kararı süzgeçten sonra YENİDEN DOĞRULANDI (|dz|@CPA 0,96→0,61).

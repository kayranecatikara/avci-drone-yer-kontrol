# GECE NOTLARI — 2026-08-18 (faz geçişi)

> Görev: **GPS → görsel faz geçişini sağlamlaştırmak.** Kilit sistemden
> çıkarıldı (kullanıcı talimatı, bulgusu `arac/KILIT_BULGUSU.md`'de).

## Ölçülen tablo — devir anının profili (715 devir, hedefin çerçevesinde)

| pencere | menzil | BOYUNA | YANAL | DİKEY |
|---|---|---|---|---|
| devir anı | 12,22 | −10,87 | +1,63 | −1,45 |
| +0,75 s | 9,62 | −9,06 | −0,12 | −1,09 |
| +1,5 s | 8,82 | −7,43 | −2,71 | −0,36 |
| +3 s | 13,73 | −8,50 | **−4,94** | +0,04 |

**Dikey ve boyuna kapanıyor; yanal sıfırı geçip ıraksıyor.**
En yakın an 2,02 s'de 5,11 m, sonra geçişlerin %88'i uzaklaşıyor.

⚠ Bu tablo 16 farklı ayardan karışıktı. Ayar bazında ayrıştırınca **nitel
iddia ayakta** (16 ayarın 15'inde yanal negatife gidiyor) ama büyüklükler
çok değişken (−0,26 … −11,32 m). Tek ortalama tablo yanıltıcı.

## ⭐ Kök neden: hedefin dönüşü, ve `ω × t_go`

Yanal ıraksama bizim kontrolümüz değil, **hedefin dönüşü**:

| hedef ne yapıyor | yanal (+2,5 s) | menzil (+2,5 s) |
|---|---|---|
| düz uçuyor | −1,81 m | **5,39 m** |
| dönüyor (15-30 °/s) | −8,53 m | 17,17 m |
| sert dönüyor | −15,07 m | 23,65 m |

Menzil kuşağı sabit tutulunca da duruyor (10-16 m: düz %52 <3m, dönüş %7)
→ **kafa karışıklığı değil.**

**Fizik:** kuyruk takibinde kapanma `V_biz − V_hedef ≈ 21 − 18 = 3 m/s`.
12 m'den yaklaşma `t = d/Vc ≈ 4 s` sürüyor; hedef 20 °/s dönüyorsa o sürede
**80°** dönüyor — vardığımız yerde artık yok. Saf takip **prensip olarak**
çalışamaz.

**Doğru kapı değişkeni `ω` değil, `ω × t_go`** (yaklaşma boyunca hedefin
döneceği açı). Normalize ölçütle (kapatma oranı) sınandı:

| ω × t_go | kapatma | ≥%70 |
|---|---|---|
| **<10°** | **%79** | **%57** |
| 10-25° | %55 | %31 |
| 25-60° | %37 | %21 |
| **>60°** | **%15** | **%14** |

korelasyon(ω, kapatma) = **−0,556**; korelasyon(menzil, kapatma) = −0,077
(yani menzil karışıklığı normalize ölçütte yok).

## Denenen / denenecek

| kol | ne | durum |
|---|---|---|
| H1/H2 | `AVCI_DEVIR_DONUS` 15 / 8 — hedef dönerken devretme | koşuyor |
| H3 | kapı + M3 manevra paketi | koşuyor |
| I1/I2 | `AVCI_KOPRU_IC` 6 / 12 — **iç daire kesme** | sırada |
| I3 | oranlı kayma (`AVCI_GPS_IC_ORAN`) | sırada |

**İç daire kesme neden önemli:** istasyonu hedefin dönüş merkezine kaydırıp
köşe keser. 2026-08-05 uçuş ölçümü: kayma 0 → en yakın 31,3 m; 8 m → 6,9 m;
14 m → 3,2 m. **Kapalıydı çünkü kilit bandını bozuyordu** (`√(6²+kayma²)`
> 6,45 m kilit kapısı). **Kilit çıkarıldı → kısıt kalktı.**

## Düzeltilen ölçüm hataları (bu gece)
1. `hedef_donus_deg` sütunu **boş** yazılıyordu — `status` ile CSV ayrı
   sözlükmüş, ikisine de yazmak gerekiyordu. Kapının mekanizma kapısı buydu.
2. Ham "en yakın menzil" ölçütü devir menziliyle **+0,991** korelasyonlu,
   yani gruplar arası kıyas için bozuk. Normalize edildi.
3. "Devir anında hedef kadrajın kenarında" iddiası **tek kareden
   genellemeydi** — toplu ölçümde açı medyanı 5,6°, yalnız %5'i >30°.

## Bilinen tuzak: FPS
Devir ölçütü **kare sayıyor** (`ardisik >= 10`). 56 fps'te 0,18 s, 15 fps'te
0,67 s eder. Oyun yavaşladıkça ölçüt kendiliğinden sıkılaşıyor → kollar
arası kıyasta fps'i not et.

## ⭐⭐ KULLANICININ TARIF ETTIGI SORUN — ölçüldü ve G3'ün çözdüğü doğrulandı

Kullanıcı: *"biz yukarıdayız, hedef biraz aşağıda, ona doğru gidiyor ama
irtifayı ve açıyı tutturmuyor."*

**Görsel fazda dikey komut, bizim konumumuza göre** (NED: + = alçal):

| bizim konum | G3 ÖNCESİ | **G3 SONRASI** |
|---|---|---|
| altta | tırman 1,09 | tırman 0,36 |
| eşit | **tırman 0,67** ✗ | ~0 ✓ |
| **üstte (+0,5..1,5)** | **tırman 0,68** ✗✗ | **alçal 0,25** ✓ |
| **çok üstte (>1,5)** | ~0 ✗ | **alçal 0,92** ✓ |

Üstteyken alçalma emreden kare: **%46 → %90**. Doğrusal uyum eğimi işaret
değiştirdi (−0,008 → +0,012). Yani yasa artık doğru yöne itiyor.

**Yasanın ham çıktısı zaten doğruydu** (bbox_ibvs logu, n=15060):
`vz_cmd / (K_VZ·V_NOM·eps_elev)` = **0,93**, VZ_MAX kırpması %1.
Sorun yasada değil **nişan noktasındaydı** — G3 öncesi yasa bizi hedefin
üstünde tutmayı "denge" sanıyordu.

**Kalan eksik: YETKİ.** 1 m hataya karşılık ~0,3 m/s komut çıkıyor,
teorik 0,75 olmalı. Denge doğru olduğuna göre ayrık ivme bütçesi
(`AVCI_ACCEL_SPLIT`) artık işe yaramalı — daha önce tek başına
kötüleştirmişti çünkü **yanlış dengeye daha hızlı** götürüyordu.
Sınama: `arac/recete_dikey3.json` (V1 split, V2 split+kazanç,
V3 = kazanç TEK BAŞINA olumsuz kontrol).

## Elenen hipotezler (kontrol edildi, sorun DEĞİL)
- **Faz kararsızlığı / sık gidip gelme:** görsel faz medyan **5,79 s**,
  yalnız %3'ü 2 s altında. Flapping yok.
- **Devir anında hedef kadrajın kenarında:** açı medyanı **5,6°**,
  yalnız %5'i >30°. (Tek karede 46° gördüm ve genelledim — yanlıştı.)
- **VZ_MAX tavanı:** kırpma %1.
- **Yasanın ham dikey çıktısı:** teorinin %93'ü, doğru.

## Sıradaki deneyler
1. `recete_devir.json` — devir kapısı (hedef dönerken bekle) — KOŞUYOR
2. `recete_ic.json` — iç daire kesme (kilit kalktı, kısıt yok)
3. `recete_dikey3.json` — dikey yetki (denge düzeldi, split artık anlamlı)

Şartname korunuyor: **10 ardışık kare → geç** birincil kural, aktif.
Geometri kapısı `AVCI_DEVIR_BEKLE` ile **sınırlı bekleme** olarak yazıldı —
engellemez, en fazla N saniye geciktirir, sonra şartname gereği devreder.


## ✗ ÇÜRÜTÜLEN HİPOTEZ: "oyunu taze tut, gecikme düşer, sonuç düzelir"

Literatür simülasyonu gecikme uçurumunun 0,40-0,60 s arasında olduğunu
söylüyordu. Ve FPS gerçekten çok değişiyor:

| durum | fps | det ms |
|---|---|---|
| taze oyun | **62,7** | **15,6** |
| 14 dk sonra | 21,5 | 44,7 |
| saatler sonra | 12-17 | 59-78 |

Yani taze oyunda gecikme ~320 ms, yıpranmışta ~443 ms. Uçurumun iki yanı
gibi görünüyordu. **AMA SAHA VERİSİ BUNU DESTEKLEMİYOR** (407 devir):

| fps | kapatma | ≥%70 | en yakın |
|---|---|---|---|
| <15 | %50 | %28 | 4,24 |
| 15-20 | %54 | %39 | 4,07 |
| 20-30 | %58 | %35 | 5,32 |
| >50 | %58 | %30 | 6,06 |

**korelasyon(fps, kapatma) = +0,022.** Düz.

**Sonuç:** 13-60 fps aralığında gecikme değişimi devir sonucunu ölçülebilir
biçimde değiştirmiyor. Muhtemelen baskın gecikme bileşeni fps'ten bağımsız
(yaw kanalı 280 ms + yakalama tamponu ~124 ms; det_ms yalnız 15-78 ms).
→ **Oyun tazeliğini performans kaldıracı olarak kovalamak YANLIŞ yol.**

⚠ Yine de fps ölçüm YÖNTEMİNİ etkiliyor: devir ölçütü KARE sayıyor
(`ardisik>=10`), yani 57 fps'te 0,18 s / 21 fps'te 0,48 s. Kollar arası
kıyasta fps'i mutlaka not et.


---

# ⏸ DURAKLATILDI — 2026-08-18 07:40 (kullanıcı çıktı)

## ✅ DOĞRULANAN TEK KAZANÇ: dikey (G3), aracın kendi verisiyle

Görsel fazda, geçerli satırlar (`menzil>=0.5 AND d_hiz>0.5`), dün / bu gece:

| ölçü | dün | **bu gece** |
|---|---|---|
| dikey hata medyanı | 1,34 m | **1,10 m** |
| p90 | 4,19 | **3,24** |
| \|dz\| < 1 m | %36 | **%46** |
| **menzil <6 m'de hata** | 1,23 m | **0,78 m** |
| **menzil <6 m'de <1 m** | %43 | **%64** |
| üstteyken alçalma emreden | %48 | **%87** |

n = 1716 (dün) / 8332 (gece). En büyük düzelme **yakın menzilde** —
vuruş geometrisinin belirlendiği yer. Mekanizma da doğrulandı: yasa
artık üstteyken doğru yöne (aşağı) itiyor.

⚠ Kıyas gün-bazlı, yani oyun sürümü/yıpranması gibi etkenlerle karışık.
Ama fark büyük ve komut davranışındaki işaret dönüşüyle tutarlı.

## ✗ BU GECE REDDEDİLEN 4 HİPOTEZ

| grup | denenen | sonuç |
|---|---|---|
| **I** iç daire kesme | 6 m / 12 m / oranlı | kapatma %53/%46/%50 vs taban %75/%58 → **ZARARLI, kayma arttıkça kötü** |
| **L** lead tavanı | 14° / 20° / 0° | %52/%60/%40 vs taban %65/%64 → **9° en iyi; hipotezim çürüdü** |
| **V** dikey yetki | split / split+kazanç | %61/%60 vs taban %65/%56 → **etkisiz** |
| **B** bbox yaw telafisi | 0,20 / +roll | %47/%62 vs taban %81/%67 → **ZARARLI (işaret şüphesi)** |

**Olumsuz kontroller çalıştı:** `lead=0` %40'a düştü (lead gerçekten değerli).

## ⚠⚠ ÇÖZÜLMEMİŞ: İKİ ÖLÇÜT ÇELİŞİYOR

| kol | kapatma | vuruş |
|---|---|---|
| L1_lead14 | %52 (kötü) | **7** (taban 2/1) |
| B1_hizala | %47 (kötü) | **5** (taban 2/3) |
| V3_kvz_TEK | **%69** (iyi) | **8** (taban 1/4) |

`lead14` ve `hizala` iki ölçütte TERS yönde. Sebep bulunmadan hiçbiri
entegre edilmemeli. Olası sebepler: (a) 14 dk'da 1-8 vuruş = Poisson
gürültüsü, (b) V3'te fps 53,8 iken diğerlerinde ~21 (karışıklık),
(c) `en_yakin=0.0` yazan 2 kol (L1, L3) geçersiz-satır artefaktı olabilir.

## ▶ DÖNÜNCE İLK YAPILACAKLAR (sırayla)

1. **`en_yakin=0.0` iki kolu doğrula** — geçersiz satır mı, gerçek mi.
   Bu, çelişkinin en olası açıklaması.
2. **`AVCI_IBVS_KVZ=0.9` tekrarı** — tek umut verici kol. Şart:
   **serpiştirilmiş** (taban-test-taban-test) ve **fps eşitlenmiş**.
3. **Yaw telafisinin İŞARETİNİ** doğrula (bbox ajanı "ters işaret 80×
   daha kötü" diye uyarmıştı) — zararlı çıkması işaret hatasına uyuyor.
4. Koşulmayan reçeteler: `recete_kestirim.json`, `recete_manevra_dogrulama.json`

## ⛔ DEĞİŞMEYEN KURALLAR
- **Kilit sisteme dahil edilmeyecek, çalıştırılmayacak** (bulgu: `arac/KILIT_BULGUSU.md`)
- `models/` altındaki eğitilmiş modeller silinmez/üzerine yazılmaz
- Tespit modeli, poz KAPALI; `AVCI_KAYIT` fotoğraf yolu bozulmaz
- Her ölçümden önce `arac/kol_hukum.py` başlığındaki tuzak listesini oku

## ▶ SİSTEMİ YENİDEN AYAĞA KALDIRMA
```
python main.py                         # sunucu
python arac/nobetci.py                 # MISSION COMPLETED -> PLAY AGAIN + E
python arac/saglik.py                  # bağlantı/kamera nöbeti
python arac/sira.py --recete arac/recete_XX.json   # deney zinciri
```
Yedek: `yedek/GECE_SONU_20260818_073816/` (152 .py, 21 reçete, 14 kanıt dosyası)

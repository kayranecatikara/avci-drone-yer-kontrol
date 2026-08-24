# GECE NOTLARI — 2026-08-19 (yarışma modu gerçeği)

> Kullanıcı: *"artık çöz sorunu… manevralarda hala berbat… tam yetki sende
> ben uyuyorum"*

## ⛔⛔ EN BÜYÜK BULGU: sistem İKİ KAT teşhis modundaydı

| katman | teşhis değeri | yarışma değeri |
|---|---|---|
| `HEDEF_TRUTH_AKTIF` (`dow_kopru.py:349`) | `True` = kusursuz hedef konumu | `False` |
| `kaynak` (istasyon, `/api/command`) | `start_gercek` = filtresiz | `start` → "v2" |

**Dünkü bütün ölçümler** (`K_VZ`, sönümleme, aspect, pusu, `dr/dt`) bu
modda yapıldı. Yani "yasa kusursuz veriyle ne yapıyor" sorusunu
cevaplıyorlar, "yarışmada ne olacak" sorusunu değil.

⚠ `tests/test_dow_kopru.py`'deki 5 "önceden kırık" test aslında truth
bayrağı yüzündenmiş — bayrak kapanınca **kendiliğinden geçtiler**
(6 kaldı → 1 kaldı). Test takımı bunu söylüyordu, ben duymadım.

### Ölçülen fark (10 dk, aynı ölçüt, drone gerçekten uçuyor)
| | teşhis | **yarışma** |
|---|---|---|
| yaklaşma | 31 | **4** |
| CPA medyan | 2,66 m | **9,15 m** |
| <1,5 m | %13 | **%0** |
| <3 m | %58 | **%0** |

## ⭐ KÖK NEDEN: hedef GPS'i — ve bozulma GÜRÜLTÜ DEĞİL, GECİKME

| kanal | medyan | p90 |
|---|---|---|
| ham bozuk GPS | 21,6 m | 39,5 |
| mevcut "j" filtresi | 14,9 m | 39,0 |
| **Fourier + 1,2 s ileri (nedensel)** | **5,8 m** | **10,1** |

Bozuk veriye periyodik model uydurulunca **artık yalnız 5 m** → sinyal
kendi içinde düzenli. Oyunun bildirdiği `delay_s = 1,00 s` × hedef
18 m/s ≈ 18 m; ölçülen 21,6 ile birebir.

**Bu yüzden iki naif yol da çalışmaz:** ortalama almak bias'ı silmez,
ham veriyi kaydırmak gürültüyü taşır. Önce düzleştir, sonra kaydır.

**Doz-cevap ve olumsuz kontrol:**
0,0 s → 21,3 m (ham seviyesi) · 0,6 → 11,2 · **1,2 → 5,8** · 1,5 → 6,8 · 2,0 → 14,5
`ileri=0` ham seviyesine dönüyor → kazanç kesinlikle gecikme telafisinden.

## ⚠ FİLTRENİN KENDİ RAPORU YANILTIYOR
`j.j_hata_ort_m = 0,023 m` **inovasyon artığıdır** (filtrenin kendi
ölçümüne uyumu), gerçek hata değil. Gerçek hata 14,9 m; dürüst olan
`kiyas.j_ort_m = 15,2`. Filtre kendini kusursuz sanıyor.

## Yazılanlar
- **`fusion/periyodik_kestirici.py`** + 12 test — Fourier periyodik model,
  arka plan iş parçacığı, `AVCI_PERIYODIK` kapısı (varsayılan KAPALI)
- **`arac/gozcu2.py`** — nöbetçinin göremediği 3 arızayı kapatır:
  sunucu ölümü · drone DISARMED/durgun · telemetri donması
- `dow_kopru.get_plane()` entegrasyonu + `[PK]` mekanizma kapısı logu

### İki tuzak ölçülerek çözüldü
1. **Sıçrama eşiği HIZ değil MUTLAK MESAFE olmalı.** Bozuk sinyal örnekler
   arası p99 **40 m** zıplıyor; hız eşiği (55 m/s = 12,4 m/örnek)
   örneklerin %5,5'ini "ışınlanma" sayıp tamponu sürekli sıfırlıyordu →
   kapı **hiç açılmadı (0/1055)**. Eşik 150 m.
2. **Uydurma AYRI İŞ PARÇACIĞINDA.** `guncelle()` p99 18,7 ms /
   maks 121,8 ms; 20 Hz döngüde iki tik düşerdi. Ayrı iplikle kontrol
   döngüsüne maliyet **maks 0,14 ms**.

## Testler
**1 kaldı / 602 geçti** — kalan tek hata gerçekten önceden kırık
(`test_varsayilanlar_KAYNAKLA_AYNI`, LEAD_ERKEN).

## ▶ SIRADAKİ
1. `[PK]` logundan mekanizma kapısını doğrula (kapı açılıyor mu, periyot
   29,6'ya kilitleniyor mu, sapma makul mü)
2. Yarışma modunda 12 dk ölçüm: kestirici AÇIK vs KAPALI
3. Kazanç doğrulanırsa `AVCI_PERIYODIK` varsayılan AÇIK
4. **Ancak ondan sonra** güdüm ayarlarına dönülür — 15 m konum hatası
   varken 0,3-0,8 m'lik ayarlar ölçülemez

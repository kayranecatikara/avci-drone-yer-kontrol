# KİLİT KAPISI — ölçülmüş sonuç (sistemde KAPALI)

> ⛔ **Kullanıcı talimatı 2026-08-18:** "kiliti komple boş ver, sisteme dahil
> etme, çalıştırma, bir yere kaydet." Kapı **kapalı**. Bu dosya sonucu saklar.
> Açmak için: `AVCI_KILIT_S=5 AVCI_KILIT_DOLULUK=0.80 AVCI_KILIT_CONF=0.25
> AVCI_KILIT_BOSLUK_MOD=sure`

## Kapı ÇALIŞIYOR — uçuşta ölçüldü (2026-08-17 gece)

| kol | GPS→görsel ≥5 s | TERMINAL ≥5 s | en düşük | vuruş | en yakın |
|---|---|---|---|---|---|
| taban (kapı kapalı) | %15 | %33 | 0,52 s | 2 | 0,81 m |
| **kapı AÇIK 5 s** | **%100** | **%100** | **5,00 s** | 2 | **0,46 m** |
| kapı 3 s | %20 | %54 | 3,01 s | 2 | 0,57 m |
| **kapı 5 s + doluluk %80** | **%100** | — | 5,00 s | **7** | 0,57 m |

**29 faz geçişi + 21 vuruş taahhüdü, sıfır ihlal.** Angajman çökmedi.

## Kapı kapatılma sebebi ölçüm değil, öncelik
Kullanıcı gece boyunca **faz geçişine** odaklanmamı istedi ve kilidin
sistemde çalışmasını istemedi. Ölçüm kapının işe yaradığını gösteriyor.

## Kapının gerçek tanımı (kod duruyor, yalnız varsayılan kapalı)
- `ESIK_S` — kesintisiz kilit süresi eşiği (s)
- `CONF_MIN` — kilide sayılacak minimum güven (0,25 boru hattıyla hizalar)
- `BOSLUK_MOD` — `"sure"`: tolerans ZAMANLA ölçülür (kare hızından bağımsız)
- `DOLULUK_MIN` — pencerenin en az bu oranı gerçek tespitle dolu olmalı

**Doluluk neden şart:** eski tanım bir boşluğun *uzunluğunu* sınırlıyor ama
*sayısını* sınırlamıyordu → "2 kare gör, 0,3 s kör kal" dizisi sonsuz
tekrarlanıp "5 s kesintisiz kilit" üretebiliyordu. Ölçüldü: ≥5 s
kilitlerin doluluk medyanı **%59,7** (pencerenin içinde ~2,3 s körlük).

**Boşluk toleransı 0,35 s truth ile doğrulandı:** o eşiğe kadar yeniden
yakalanan kutu **%94,3 aynı hedef**; ötesinde ~90 px sıçrıyor ve beşte biri
başka bir nesne.

## ⚠⚠ EN ÖNEMLİ DERS — OFF-POLICY TUZAĞI
Kapıyı açmadan önce çevrimdışı simülasyon "devir 1413 → 1'e çöker, şart
karşılanamaz" demişti. **YANLIŞTI.** Simülasyon eski kayıtlardaki kareleri
yeniden oynatıyordu; oysa kapı **yörüngeyi değiştirir** — araç farklı uçar,
farklı kareler görür.

Aynı tuzak algı yamalarında da vurdu: çevrimdışı "≥5 s epizod 0 → 57" dedi,
uçuşta **hiçbiri iyileşmedi** (P1 %8, P2 %8, P3 %22 vs taban %15-20;
P4 krop **%0** — düpedüz zararlı).

**KURAL: davranışı değiştiren bir kapıyı çevrimdışı replay ile
değerlendirme. Uçuşta ölç.**

## Denetim enstrümanı AÇIK kalıyor
`kilit_denetim_*.csv` her faz geçişinde yazılmaya devam ediyor (kapı kapalı
olsa da). Bu davranış değil, ölçüm. `python arac/kilit_denetim.py` ile
istediğin an "kaç geçiş kaç saniye kilitten sonra oldu" görülebilir.

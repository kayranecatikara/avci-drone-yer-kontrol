# DEDEKTÖR TESTİ — avci_yolo (Gazebo) vs models/best.pt (repo)

**Tarih:** 2026-08-06 · **Koşul:** U konfigürasyonu (gerçek GPS, `IC_KAYMA=0`,
`RANGE_SET=6.9`, `V_MAX=22`) · **Güdüm GPS'te kaldı; dedektör çıktısı komuta HİÇ
girmedi** — kareler uçuş sırasında kaydedildi, çıkarım **offline** koştu.
**Yakalama:** pencere içeriği 1920×1080 (FPV kamera görüntüsü), 5 Hz.
**Hakem:** her karede gerçek konum + attitude'dan hedefin beklenen kadraj yeri
(u, v) ve beklenen kutu oranı `1.718/(2R·tan62.5°)`.

## ⚠ KOŞU YARIM KALDI — 374 karenin yalnız 50'si geçerli

Drone hedefe **1.4 m**'ye kadar girip **çarptı**; tur bitti, oyun PLAY'den çıktı ve
**TCP kapandı**. SDK bu durumda sessizce son değeri döndürmeye devam ettiği için
(SDK_README:112) kalan 324 kare **donuk telemetriyle** kaydedildi (R=104.15 m sabit,
karelerin %87'si) ve elendi. Kalan 50 kare: menzil 1.4-178 m
(12+ m: 38 · 8-12 m: 3 · <8 m: 9) — yani **kilit bandının olduğu 8-15 m aralığı
neredeyse boş**. Aşağıdaki (b) ve (c) bu yüzden HÜKÜM VERMEYE YETMEZ.

## (g) MODEL KARŞILAŞTIRMASI — **hüküm verilebilir**

| Metrik | **avci_yolo (Gazebo)** | **best.pt (repo/DoW)** |
|---|---|---|
| Sınıflar | `{0: talon}` | `{0: talon}` |
| Hedefle **eşleşen** tespit (tümü) | **%4.0** | **%12.0** |
| — 12+ m | %0.0 | %7.9 |
| — 8-12 m | %33.3 (n=3) | **%100.0** (n=3) |
| — <8 m | %11.1 | %0.0 |
| Kutu üreten kare | %100.0 | %48.0 |
| **YANLIŞ POZİTİF** | **117 kutu / 48 kare (%96.0)** | 18 kutu / 14 kare (%28.0) |
| YP ortalama güven | 0.588 | 0.584 |
| Güven (eşleşen aday) medyan | 0.237 | **0.468** |
| Hız (imgsz=1280, offline) | 29.4 ms → 34.0 FPS | 23.8 ms → 41.9 FPS |

### HÜKÜM: Gazebo modeli DoW'da KULLANILAMAZ

`docs/dedektor_testi/gazebo_1_R27m.jpg` kanıtı: model kutuları **HUD metin
öğelerine** çiziyor — sol üstteki sinyal göstergesi ("−65 / 2:98") ve sol alttaki
batarya/akım okuması ("11.50A / 4.20v / 25.2v"). Uçakla ilgisi yok. Her karede kutu
üretiyor (%100) ama hedefle eşleşmesi %4. Bu, Gazebo'daki "%55 hayalet kutu"
davranışının DoW'da **daha kötü** hâli (%96). Repo modeli aynı sahnelerde bu HUD
kutularını üretmiyor.

`docs/dedektor_testi/repo_0_R1m.jpg`: **best.pt gerçek Talon'u yakalıyor** —
uçak sağda net görünüyor, iki kutu (conf **0.41** ve **0.78**) gövde/burun üzerinde.

**⇒ Reponun kendi `models/best.pt`'si kullanılacak. `avci_yolo.pt` bu turda
devre dışı** (zaten kapsam dışıydı; ölçüm bunu doğruladı).

## (a) TESPİT ORANI — ön veri

Yukarıdaki tabloda. **8-12 m bandında best.pt 3/3** (n=3, çok küçük örneklem);
12+ m'de %7.9 (uzak/küçük hedef, beklenen); <8 m'de %0 eşleşme — ama o 9 kare
çarpışma anına ait ve aşağıdaki hakem sorunu tam orada devrede.

## (b) KONUM ve (c) BOYUT — **HENÜZ HÜKÜM VERİLEMEZ**

Ham sayılar: konum sapması medyan **0.12** normalize (her iki modelde de,
du ≈ **+0.117** sistematik sağa); boyut best.pt için **beklenenin %78'i**
(n=6), Gazebo modeli %308 (n=2).

**Bu sayılara güvenilmez, iki nedenle:**

1. **Hakem kayması var.** İki bağımsız modelin aynı yönde (+0.117) sapması
   dedektörlerin değil, benim geometrik tahminimin kaydığını gösterir.
   `repo_0_R1m.jpg` bunu gözle doğruluyor: hedef sağda, kırmızı hakem kutusu
   sol üstte. Dikey iyi (dv ≈ +0.02), sapma **yalnız yatay** — yani zamanlama
   değil yaw eksenli bir kayma ya da yakalama gecikmesi.
   *Not:* R=1.4 m'de bu kare hakem testi için elverişsiz — hedefin kendi kanat
   açıklığı (1.7 m) menzilden büyük, "merkez" tanımı belirsizleşiyor.
2. **Örneklem çok küçük ve yanlış bantta** — kilit için kritik olan 8-15 m'de
   yalnız 3 kare var; (c)'nin medyanı 6 kareye dayanıyor.

**Kritik soru (dedektörün kutusu %5 kilit eşiğini geçiyor mu) bu veriyle
cevaplanamaz.** Ölçülen kilit metriği `max(w/W, h/H)` best.pt için medyan
**%2.73** ve karelerin **%0'ı ≥%5** — ama bu değerlerin çoğu 12+ m'den geliyor
(orada zaten geometrik beklenti de %3.7'nin altında), yani eşiği geçmemesi
**beklenen** bir sonuç, dedektör kusuru değil. Oturma menzili 8.1 m'de beklenen
**%5.5**; o bantta ölçüm yok.

## (d) YANLIŞ POZİTİF

Gazebo modeli: **%96 kare** (117 kutu, ort. güven 0.588) — HUD metinleri.
best.pt: **%28 kare** (18 kutu, ort. güven 0.584). best.pt'nin yanlış-pozitifleri
de incelenmeli (muhtemelen aynı HUD/pervane bölgeleri; repo'nun `PROP_MASKE`
mekanizması tam bunun için var ama şu an `[]` = kapalı).

## (e) GÜVEN

best.pt eşleşen adayda medyan **0.468**, p10 0.069; karelerin **%70.8**'i
`VIS_CONF_MIN=0.15` eşiğinin üstünde. Gazebo modeli medyan 0.237, %64.0.

## (f) HIZ

best.pt **23.8 ms/kare (41.9 FPS)**, avci_yolo 29.4 ms (34.0 FPS) — imgsz=1280,
oyun açıkken, offline çıkarım. Canlıda oyunla GPU paylaşımı bunu ~2-4× yavaşlatır
(CLAUDE.md perf notu).

## SONUÇ ve SIRADAKİ ADIM

**Cevaplanan:** Model sorusu. **Gazebo modeli DoW'da kullanılamaz** (HUD metinlerine
%96 hayalet kutu); **reponun `models/best.pt`'si kullanılacak** — gerçek hedefi
yakalıyor, HUD'a takılmıyor, daha hızlı ve daha güvenli.

**Cevaplanamayan:** "Dedektörün kutusu kilit eşiğini geçiyor mu?" Bunun için gereken:
1. Oyun **PLAY moduna** alınmalı (çarpışma turu kapattı).
2. Yakalamaya **donukluk koruması** eklenmeli (telemetri 2 s değişmezse dur) —
   bu koşuda 324 kare boşa gitti.
3. Yakalama **~15 Hz**'e çıkarılıp hakem gecikmesi **veriden ölçülmeli**
   (gecikme taraması: sapmayı en küçük yapan kaydırma) — sistematik +0.117
   ancak böyle temizlenir.
4. Örneklem **8-15 m bandında** yoğunlaştırılmalı (kilit bandı).

Bunlar yapılmadan (b)/(c) sayıları rapora hüküm olarak yazılmamalı.

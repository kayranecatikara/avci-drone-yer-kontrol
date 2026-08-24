# DEVİR (midcourse → terminal / GPS → görsel) — literatür taraması ve ölçümlerimizle eşleştirme

> Tarih: 2026-08-18. **SALT ARAŞTIRMA — hiçbir koda dokunulmadı.**
> Ölçüm tabanı: 713–715 gerçek devir + bu gece eklenen normalize kapatma ölçütü.
> Künye kuralı: her kaynak Crossref/arXiv/doğrudan PDF ile doğrulandı.
> Doğrulanamayanlar §7'de **KAYNAK YOK** olarak listelendi.

---

## 0. HÜKÜM ÖZETİ (önce oku)

1. **Devir ölçütümüz literatürün tanımladığı ölçütün TAM TERSİ türden.** Literatürde
   handover koşulu **geometriktir** (ZEM, kerteriz hızı, bakış açısı, menzil,
   kapanma hızı); bizimki **saf algı** (`ardisik_kare>=10`). Palumbo'nun handover
   analizi devir hatasını LOS'a **dik bileşen** `e⊥` olarak tanımlar ve
   "terminal fazın kapatmak zorunda olduğu ıska budur" der — bizim ölçtüğümüz
   **YANAL** eksen tam olarak `e⊥`'dir ve devir ölçütümüzde hiç geçmez.

2. **Senin bu gece bulduğun `ω × t_go` değişkeni literatürün ZEM'idir.**
   Hedef dairesel dönerken, düz-çizgi öngörüsünden sapma kapalı formda
   `ZEM_yanal = (V_T/ω)·(1 − cos(ω·t_go))` = `ρ(1 − cos φ)`, `φ = ω·t_go`.
   Küçük açıda `≈ a_T·t_go²/2` — klasik APN hedef-manevra terimi.
   Yani **`φ` tek başına ZEM'i belirler; ω ve menzil ayrı ayrı belirlemez.**
   Ölçtüğün `korelasyon(menzil, kapatma) = −0.077` (yok) vs
   `korelasyon(ω, kapatma) = −0.556` bunun doğrudan kanıtı.

   | φ = ω·t_go | ρ=51 m ile ZEM | senin kapatma | ≥%70 |
   |---|---|---|---|
   | <10° | **0,78 m** | %79 | %57 |
   | 10–25° | 0,78 → **4,8 m** | %55 | %31 |
   | 25–60° | 4,8 → **25,5 m** | %37 | %21 |
   | >60° | >25,5 m | %15 | %14 |

   Uçurum ZEM ≈ **5 m**'de. Ölçülen en yakın geçiş medyanı 5,11 m. Aynı sayı.

3. **Asıl darboğaz kapı değil GECİKME.** Kendi kinematik simülasyonumda
   (von Moll denklemleri, bizim sayılarımızla) ω=20 °/s'de:
   gecikme 0 s → **0,00 m** · 0,25 s → 0,78 m · 0,40 s → 0,92 m ·
   **0,60 s (bizim durumumuz) → 4,92 m** · 0,85 s → 8,89 m.
   0,40 s ile 0,60 s arasında **uçurum** var. Palumbo'nun 100/300/500 ms
   otopilot zaman sabiti eğrileri aynı şeyi gösteriyor.
   **Gecikmeyi 0,60 → 0,40 s'e indirmek, denediğim her kapıdan daha büyük kazanç.**

4. **ν = 1,19 yetersiz — ama eşik ν>2 değil, ν>√2 = 1,414.**
   Hafızadaki "Guelman ν>2 ister" kaydı **yanlış**. Ghose'un ders notlarındaki
   Teorem 11.2 (Guelman 1972'ye dayanır): manevra yapan hedefe karşı PPN için
   **garantili yakalama** `ν > √2` **ve** `(N−1)ν > 1` ister.
   Bizde ν=1,19 < 1,414. **Tavan hızımız 24 m/s'de bile ν=1,334 < 1,414** →
   şartı hiçbir ayarda sağlayamıyoruz. Gereken: **V_M ≥ 25,4 m/s**.
   (Bunlar YETER koşul, GEREK değil — altında yakalama imkânsız değil, *garanti* yok.)

5. **Yanal aşma kontrolcü aşması DEĞİL, geometri + gecikme.** Simülasyonda
   ω=20 °/s, d₀=13 m, gerçek gecikmelerle yanal eksen 0 → **−4,88 m**.
   Ölçtüğün: **+1,6 → −4,9 m.** Aynı sayı. Kazanç düşürmek/artırmak bunu çözmez;
   ileri-besleme veya kapı çözer.

6. **Şartname kısıtına literatürde tam karşılık VAR:** teslim kararı
   "koşul sağlanana kadar bekle" değil, **önceden tanımlı karar anı (decision
   time) + o ana kadar en iyi teslim noktasını seç** biçiminde kurulur
   (Merkulov–Shalumov–Shima 2025). Kontrol tarafında adı **dwell-time /
   hysteresis switching**: koşul sağlanırsa hemen, sağlanmazsa süre dolunca
   zorunlu geçiş. **Senin "sınırlı bekleme" tasarımın literatürün standart formu.**

---

## SORU 1 — Handover / teslim koşulu

### (a) Literatürün dediği

**Devir hatası LOS'a dik bileşendir.** Palumbo, Blauwkamp & Lloyd handover
analizinde tahmin edilen ile gerçek hedef konumu arasındaki hatayı `e` ile
gösterip LOS boyunca (`e∥`) ve LOS'a dik (`e⊥`) diye ayırır ve şunu yazar:
*"because the relative velocity vector is along the LOS to the predicted target
location, the error `e∥` will alter the time of intercept but does not contribute
to the final miss distance. Consequently, the miss distance that must be removed
by the interceptor after transition to terminal homing is contained in `e⊥`."*
→ **Devir ölçütü `e⊥` (yani ZEM) cinsinden yazılır. Boyuna hata ıska üretmez.**

**Devirin iki kanonik kısıtı** (Chinese Journal of Aeronautics ortak güdüm makalesi,
BIT sürümü):
1. *Detection range constraint*: tüm füzeler terminal başladığı anda hedeften
   belirli menzil bandında olmalı.
2. *FOV constraint*: LOS ile füze başı arasındaki açı, arayıcının görüş alanını
   ihlal etmemeli — ve terminal boyunca ihlal etmemeli.
   Aynı makale şunu da ekliyor: *"we consider the missiles as losing the track of
   target and seceding from the terminal guidance if they generate heading errors
   that are larger than the FOV constraint"*.
   Ayrıca: **time-to-go farkları yeterince küçük olmalı.**

**Teslim penceresi bir OPTİMİZASYON DEĞİŞKENİDİR, bir yan ürün değil.**
Merkulov, Shalumov & Shima (2025, JGCD): orta ve terminal safhalar
**önceden tanımlı bir karar anıyla** ayrılır; *"The pursuer's position and heading
at the decision time, referred to as a handover point, is optimized with respect
to a tradeoff between the expected miss distance and control effort... the handover
point is the only optimization parameter of the problem"* — aday teslim noktaları
orta safha sonundaki **erişilebilir kümeden** örneklenir.

**ZEM tabanlı formülasyon.** Morgan (2016, ACC): teslim anında **yeterince küçük
ZEM** sağlayan orta-safha yasası; füze önceden belirlenmiş bir t_go'dan sonra
kontrol uygulamaz → istenen "handover basket"e girmiş olur.
Zhang, Tang & Guo (2019): terminal handover kısıtları *"ideal zero effort terminal
engagement"* garantiler; hedef manevra yapmadıkça ek kontrol olmadan vurur.
Ve doğrudan bizim ölçütümüz olacak cümle: **"to make use of the zero-effort-miss
concept, the line-of-sight rate had better approach zero at the handover of the
midcourse and terminal phase."**

**Acquisition/handover basket.** Arayıcının aramak zorunda olduğu belirsizlik
hacmi. Büyük sepet → daha uzun tespit menzili ve daha büyük baş hatası gerektirir;
uzun tespit menzili baş hatasından doğan ıskayı azaltır (DTIC ADA386524 özeti —
⚠ tam metin erişilemedi, §7).

**ZEM tanımı (kullanacağımız hâl).** Palumbo/Blauwkamp/Lloyd, modern homing:
`ZEM_PN = r_y(t) + v_y(t)·t_go`, ve PN komutu `u_PN = N'·ZEM/t_go²`.

### (b) Kaynaklar

| # | Künye | Doğrulama |
|---|---|---|
| K1 | Palumbo, N. F., Blauwkamp, R. A., Lloyd, J. M., "Basic Principles of Homing Guidance", *Johns Hopkins APL Technical Digest*, **29**(1), 2010, s. 25–41. | PDF doğrudan okundu (17 s.) |
| K2 | Palumbo, N. F., Blauwkamp, R. A., Lloyd, J. M., "Modern Homing Missile Guidance Theory and Techniques", *JHU APL Tech. Digest*, **29**(1), 2010, s. 42–59. | PDF doğrudan okundu |
| K3 | Morgan, R., "Midcourse guidance with terminal handover constraint", *2016 American Control Conference (ACC)*, s. 6006–6011. DOI 10.1109/ACC.2016.7526612 | Crossref |
| K4 | Merkulov, G., Shalumov, V., Shima, T., "Integrated Midcourse-Terminal Guidance with Delayed Target Selection", *Journal of Guidance, Control, and Dynamics*, **48**(10), 2025, s. 2243–2256. DOI 10.2514/1.G009009 | Crossref + özet |
| K5 | Zhang, H., Tang, S., Guo, J., "Cooperative near-space interceptor mid-course guidance law with terminal handover constraints", *Proc. IMechE Part G: J. Aerospace Engineering*, **233**(6), 2019, s. 1960–1976. DOI 10.1177/0954410018769182 | Yayıncı sayfası |
| K6 | Sun, L., Yang, B., Ma, J., Ji, R., "A Midcourse and Terminal Guidance Handover Window based on Predicted Intercept Area", *2022 13th Asian Control Conference (ASCC)*, s. 2416–2421. DOI 10.23919/ASCC56756.2022.9828140 | Crossref (⚠ tam metin okunamadı) |
| K7 | Liu, X., Tang, S., Guo, J., Yun, Y., Chen, Z., "Midcourse Guidance Law Based on High Target Acquisition Probability Considering Angular Constraint and Line-of-Sight Angle Rate Control", *International Journal of Aerospace Engineering*, 2016, mad. 7634847. DOI 10.1155/2016/7634847 | Künye doğrulandı (⚠ tam metin 402/403, §7) |
| K8 | Zhao, J. vd. (BIT/PRIS ön baskısı), "A Joint Mid-course and Terminal Course Cooperative Guidance Law", *Chinese Journal of Aeronautics* sürümü. | PDF doğrudan okundu; ⚠ cilt/sayfa doğrulanamadı (§7) |

### (c) Bizim ölçümümüzle kıyas

**Mevcut ölçütümüz literatürdeki hiçbir kısıtı içermiyor:**

| Literatürün istediği | Bizde karşılığı | Durum |
|---|---|---|
| ZEM / `e⊥` küçük | — | **YOK** |
| Kerteriz hızı λ̇ → 0 | — | **YOK** |
| Bakış açısı (FOV/aspect) kısıtı | `AVCI_DEVIR_ASPECT` | **VAR ama KAPALI** (999) |
| Tespit menzili bandı | `AVCI_DEVIR_BOYUT=14 px` ≈ 16,6 m | **AÇIK** |
| Kapanma hızı > 0 | — | **YOK** |
| Ardışık tespit (algı) | `ardisik_kare>=10` | AÇIK — **tek fiilî ölçüt** |

**Senin `ω·t_go` tablosunun teorik karşılığı.** `ρ = V_T/ω`, `φ = ω·t_go`:
`ZEM_yanal = ρ(1 − cos φ)`. Depo ölçümüyle `ρ ≈ 51 m` (supervisor.py yorumu:
"530 m tur, 51 m yarıçap"; salt geometriden 220×96 oval için 48 m — ikisi de
aynı bandı verir). Bu formülle senin dört bandın ZEM karşılığı §0'daki tabloda.
**Uçurum ZEM ≈ 5 m'de, ölçülen CPA medyanı 5,11 m ile aynı yerde.**

Ve senin fizik gözlemin literatürün t_go tanımının ta kendisi:
`t_go = R/(V_M − V_T) = 12/3 = 4 s`, `φ = 20°/s × 4 s = 80°` → `ZEM = 51(1−cos80°)
= 42 m`. **Saf takip 42 m'lik bir ZEM'i 4 saniyede kapatamaz** — 12 m/s² ile
4 s'de üretilebilen yanal yer değiştirme `½·12·16 = 96 m` gibi görünse de
gecikme + boyuna kanalın payı sonrası fiilen 5 m civarında kalıyor (simülasyon).

`korelasyon(menzil, kapatma) = −0,077` bulgusu K1'i doğruluyor:
**boyuna (LOS boyunca) hata ıska üretmez** — Palumbo'nun `e∥` maddesi.

### (d) Somut öneri

**Ö-A. Devir ölçütüne ZEM kapısı ekle: `φ = ω_T · t_go < Θ`.**
`ω_T` GPS fazında zaten hesaplanıyor (`tgt_omega`), `t_go = R/(V_M − V_T)`.
Kapı **sınırlı bekleme** olarak (bkz. §3): `Θ = 25°` ile başla.
Beklenen kazanç: senin tablona göre `<25°` bandı %79 ve %55 kapatma
(havuz ortalaması ~%46) → **kapatma oranında +15…+25 puan.**

**Ö-B. Aspect kapısı zaten var, aç.** `AVCI_DEVIR_ASPECT=40` (kod yorumu
fiziğin ~25° istediğini söylüyor). Tek değişkenli, bit-aynı geri alınabilir.

### (e) Riskler / nasıl çürütülür

- **ÇEVRİMDIŞI TUZAK (KILIT_BULGUSU.md).** Kapı yörüngeyi değiştirir; eski
  kayıtları replay eden simülasyon kapının etkisini ÖNGÖREMEZ. **Uçuşta ölç.**
- Çürütme: `Θ` kapısı açıkken devir sayısı düşer ama kapatma oranı ARTMAZSA,
  `φ` hipotezi yanlıştır → `ω` ve `t_go` ayrı ayrı gate edilmeli.
- `ω_T` kestirimi bayatsa (yaw bayatlığı bulgusu, `talon-bbox-geometri`) kapı
  yanlış anda ateşler. Kapı açılmadan önce `ω_T` gecikmesi ölçülmeli.

---

## SORU 2 — Handover transient / bumpless transfer / durum başlatma

### (a) Literatürün dediği

**Problem tanımı.** İki kontrolcü arasında geçerken, devreye giren kontrolcünün
durumu geçmişi görmediği için çıkışı sıçrar. Bumpless transfer, geçiş anından
sonra gerçek tepki ile ideal tepki arasındaki farka L₂ sınırı koyan bir telafi
tasarımıdır.

**Temel koşul (tek satır).** Geçiş anı `t_s`'de:
`u_yeni(t_s) = u_eski(t_s⁻)`.
PI/PID için bu, integratörün **ön yüklenmesi** demektir:
`I(t_s) = u_eski(t_s⁻) − K_p·e(t_s)`.
Yani *durumu bir fizik büyüklüğüyle (kendi hızımız, hedef hız kestirimi)*
başlatmak DEĞİL, **çıkışı sürekli kılacak değerle** başlatmak.

**Üç standart mekanizma, artan güçte:**

1. **Tek seferlik durum başlatma (state initialization).** Yeni kontrolcünün
   durumu geçiş anında hesaplanır. En ucuzu; bizim `AVCI_IBVS_HIZ_SICAK` bunun
   örneği. Zayıflığı: yalnız geçiş anını düzeltir, öncesindeki farklı
   *denge noktası* problemine dokunmaz.
2. **Koşullandırma tekniği / izleme kipi (conditioning / tracking mode).**
   Bekleyen kontrolcü, GPS fazı boyunca **sürekli** aktif kontrolcünün çıkışını
   izler; durumu "gerçekleştirilebilir çıkış" ile sürülür. Geçişte sıçrama
   *yapısal olarak* olamaz. Hanus, Kinnaert & Henrotte (1987) bunun genel
   anti-windup + bumpless çerçevesini verir; Peng, Vrančić & Hanus (1996)
   PID bağlamında derler ve *conditioned transfer*'i bumpless transfer'e
   tercih eder. Åström–Hägglund geleneğinde izleme kazancı `K_t` ile
   `İ̇ = ... + (u_gerçek − u_hesaplanan)/T_t`.
3. **Optimal (LQ) bumpless transfer.** Turner & Walker (2000): kapalı-çevrim
   olmayan kontrolcünün girişini, iki çıkış arasındaki farkın karesel
   maliyetini minimize edecek biçimde sürer; tek Riccati denklemi çözülür ve
   **Hanus koşullandırma formüllerine özel hâlde indirgenir**. Graebe & Ahlén
   (1996) aynı problemi çift yönlü, durum erişimi gerektirmeyen bir
   **izleme (tracking) problemi** olarak kurar.

**⚠ Kritik ayrım.** Bumpless transfer **çıkış sürekliliğini** sağlar; iki
kontrolcünün **farklı denge noktasına** sahip olması ayrı ve daha ağır bir
hatadır. Denge noktaları ters işaretliyse, bumpless transfer sıçramayı yumuşatır
ama araç yine yanlış hedefe sürülür.

### (b) Kaynaklar

| # | Künye | Doğrulama |
|---|---|---|
| K9 | Hanus, R., Kinnaert, M., Henrotte, J.-L., "Conditioning technique, a general anti-windup and bumpless transfer method", *Automatica*, **23**(6), 1987, s. 729–739. DOI 10.1016/0005-1098(87)90029-X | Crossref |
| K10 | Peng, Y., Vrančić, D., Hanus, R., "Anti-windup, bumpless, and conditioned transfer techniques for PID controllers", *IEEE Control Systems (Magazine)*, **16**(4), 1996, s. 48–57. DOI 10.1109/37.526915 | Crossref |
| K11 | Turner, M. C., Walker, D. J., "Linear quadratic bumpless transfer", *Automatica*, **36**(8), 2000, s. 1089–1101. DOI 10.1016/S0005-1098(00)00021-2 | Crossref |
| K12 | Graebe, S. F., Ahlén, A. L. B., "Dynamic transfer among alternative controllers and its relation to antiwindup controller design", *IEEE Trans. Control Systems Technology*, **4**(1), 1996, s. 92–99. | IEEE Xplore kaydı |
| K13 | Kothare, M. V., Campo, P. J., Morari, M., Nett, C. N., "A unified framework for the study of anti-windup designs", *Automatica*, **30**(12), 1994, s. 1869–1883. DOI 10.1016/0005-1098(94)90048-5 | Crossref |

### (c) Bizim ölçümümüzle kıyas — **bu raporun en net eşleşmesi**

Bu gecenin dikey ölçümü literatürün "**denge noktası uyuşmazlığı**" vakasının
ders kitabı örneği:

| ölçüm | değer |
|---|---|
| GPS yasasının dengesi | hedefin **1,55 m ALTI** (tasarım) |
| Görsel yasanın dengesi | hedefin **ÜSTÜ** |
| Devirde dikey setpoint sıçraması | **2,91 m** |
| Görsel yasa üstteyken komut | **TIRMANMA** (işaret −0,68) |
| Alçalma emreden kare oranı | **%46** (yani yazı-tura) |
| Nişanı ufka bağladıktan sonra | **%90** |
| Yasanın ham çıktısı / teori | **0,93** → yasa DOĞRUYDU |

**Teşhis:** hata kontrolcüde değil, **referansta** (nişan noktası). Literatürün
diliyle: bu bir *bumpless transfer* eksikliği değil, **iki kontrolcünün farklı
denge noktasına regüle etmesi**. Bumpless transfer (sıçramayı yumuşatmak) bunu
ÇÖZMEZDİ — nitekim depoda "dikey kazancı tek başına artırmak 5/5 ölçüde
kötüleşti" olumsuz kontrolü de bunu doğrulamış: sorun yetki değil, hedef noktası.

**`AVCI_IBVS_HIZ_SICAK` literatürün hangi katmanında?** Katman 1 (tek seferlik
durum başlatma). Ve başlangıç değeri **yanlış kaynaktan** alınıyordu: GPS'in
hedef hız kestiriminden — ki o kestirimin **%62'si hedefin gerçek hızının
altında** ölçülmüş. Literatürün koşulu `u_yeni(t_s) = u_eski(t_s⁻)`; bizimki
"bir fizik büyüklüğü seç" idi. `HIZ_SICAK=1.5` ile kendi hızımızdan başlatmak
doğru yöne gitti (<2 m geçiş %22→%41, iki bağımsız koşuda) ama hâlâ katman 1.

### (d) Somut öneri

**Ö-C. Katman 2'ye geç: görsel yasayı GPS fazı boyunca "izleme kipinde" çalıştır.**
Görsel yasa GPS fazında da her tik hesaplansın (komut vermeden), integratörü
`(u_GPS − u_görsel)/T_t` ile sürülsün. Devir anında sıçrama yapısal olarak sıfır.
Ölçüt: devir anındaki `|Δvz_cmd|` ve `|Δyaw_rate_cmd|` → hedef **< 0,2 m/s** ve
**< 5 °/s**. Şu an dikeyde 2,91 m'lik setpoint sıçraması vardı.

**Ö-D. Denge noktalarını ÖNCE hizala, sonra bumpless yap.** `DIKEY_UFUK=1`
bunu yaptı (%46 → %90). Aynı denetimi **yanal/yaw** ekseni için de yap:
GPS standoff nişanı ile görsel nişan noktasının yanal ofseti aynı işarette mi?
(Bu ölçülmedi; bilinmiyor.)

**Ö-E. GPS fazının son N saniyesinde dikey ofseti rampayla sıfıra sür.**
Literatürde bu "handover'a hazırlanan orta safha" (K3, K4): teslim noktası
optimizasyon değişkenidir. Bizde `AVCI_IBVS_TERM_DIKEY` rampası zaten var.

### (e) Riskler / nasıl çürütülür

- İzleme kipi CPU maliyeti getirir; görsel yasa GPS fazında da her tik koşar.
  `talon-gecikme-ve-dpp` bulgusuna göre **gecikmenin kökü GIL** idi → yeni bir
  her-tik hesabı gecikmeyi büyütürse net ZARAR olur (§0 madde 3: gecikme
  0,60→0,85 s CPA'yı 4,92→8,89 m yapıyor). **Önce gecikmeyi ölç.**
- Çürütme: izleme kipi açıkken devir anındaki komut sıçraması ölçülür.
  Sıçrama düşüp CPA düzelmiyorsa, sıçrama zaten baskın etmen değildi.

---

## SORU 3 — Hedef manevrası sırasında teslim: **bekle mi, kestir mi?**

### (a) Literatürün dediği

**Hedef manevrası "gürültü" değil "bozucu"dur.** Palumbo (K1) güdüm bozulma
etmenlerini sayarken 1–5'i stokastik gürültü, 6–7'yi (başlangıç baş hatası ve
hedef ivmesi) **deterministik bozucu** sayar: *"target maneuver can have a
stochastic quality to it and, in some instances, it can induce very large final
miss distance. Target maneuver generally is considered a (potentially significant)
disturbance rather than noise."*

**Literatürün baskın cevabı: KESTİR.** Standart yol APN'dir — PN komutuna hedef
ivmesiyle orantılı bir terim eklenir. Ölçmek zorsa dolaylı yollar var:
"neoclassical / ZMD-PNG" kerteriz hızını türevleyen bir lead ağıyla hedef ivmesini
örtük olarak geri besler (Hodžić & Prljača 2025); Monte Carlo'da PN 14,85 m ıska
verirken neoklasik 6,34 m veriyor (hedef 4g yatay manevrada).

**Manevra × GECİKME çarpımı asıl katil.** Palumbo (K2), 100/300/500 ms otopilot
zaman sabitleriyle 0–5 g hedef manevrasını süpürür ve şunu yazar:
*"For an ideal autopilot response, PN-homing would result in acceleration
requirements of three times the target maneuver"* ve
*"as the missile time response deviates from the ideal case, guidance performance
(miss distance) degrades as target maneuver levels increase... when the missile
autopilot response time deviates further from that which PN assumes, respectively
higher acceleration is required."*
İdeal otopilotta ıska hedef manevrasına **neredeyse duyarsız**; gecikme büyüdükçe
duyarlılık patlıyor.

**"Düz kısmı bekleme" için KAYNAK YOK.** "Wait for the target to stop maneuvering",
"acquisition during target turn", "delay handover until straight segment" gibi
aramalar hiçbir güdüm makalesi vermedi. Literatür beklemiyor, kestiriyor. (§7)

**AMA "koşullu ama SINIRLI teslim" literatürde standarttır** — senin şartname
kısıtının tam karşılığı, üç ayrı gelenekte:

1. **Önceden tanımlı karar anı (güdüm).** Merkulov, Shalumov & Shima (2025, K4):
   safhalar *"separated by a predefined decision time"*; o ana kadar teslim
   noktası (konum + baş) erişilebilir küme içinden **beklenen ıska ↔ kontrol
   eforu** takasıyla seçilir. Yani: **süre sabit, koşul optimize edilir.**
   Morgan (2016, K3) de aynı mimari: önceden belirlenmiş bir t_go'dan sonra
   kontrol uygulanmaz.
2. **Kilitlenmiş olan girer, olmayan sonra katılır (kooperatif güdüm).** K8:
   *"missiles will not join the terminal cooperative guidance if they are not yet
   locked-on... the first several missiles that have locked-on activate the
   cooperative terminal guidance. Then, missiles that lock on later join."*
   Bekleme sonsuz değil; katılım penceresi var.
3. **Dwell-time / hysteresis switching (kontrol kuramı).** Anahtarlamalı
   sistemlerde kararlılık, geçişler arası **asgari bekleme süresi** ya da
   **ortalama dwell-time** ile garantilenir (Liberzon & Morse 1999;
   Hespanha & Morse 1999). Pratik form tam senin yazdığın şey:
   `koşul sağlandıysa GEÇ; sağlanmadıysa en fazla T_bekle kadar bekle, sonra ZORUNLU GEÇ.`
   Bu, hem üst sınırı olan bir gecikme hem de anahtarlama sıklığına sınır verir.
4. **Command governor (kısıtı engelleyici yapmadan uygula).** Lee, Cho & Kim
   (2025): görüş alanı kısıtı bir eşitsizlik kısıtı olarak konur ve komut,
   birincil amacı **bloklamadan** kısıtı sağlayacak şekilde yönetilir.
   Şartname gerilimine ikinci bir çıkış yolu: kapıyı "devretme" değil
   "devrederken komutu şekillendir" biçiminde kur.

**Beşinci yol — beklemek yerine ZAMANI KONTROL ET.** Impact-time control guidance
(Jeon, Lee & Tahk 2006): varış zamanı bir kontrol değişkenidir. Hedefin turu
sabit periyotluysa (bizde **29,63 s**), t_go'yu şekillendirerek temasın hedefin
**düz kısmına** denk gelmesi sağlanabilir. Bu "bekleme" değil, "faz seçimi" —
ve şartnamenin "10 kare → geçmelidir" hükmüyle çelişmez, çünkü devir yine olur.

### (b) Kaynaklar

| # | Künye | Doğrulama |
|---|---|---|
| K14 | Liberzon, D., Morse, A. S., "Basic problems in stability and design of switched systems", *IEEE Control Systems (Magazine)*, **19**(5), 1999, s. 59–70. DOI 10.1109/37.793443 | Crossref |
| K15 | Hespanha, J. P., Morse, A. S., "Stability of switched systems with average dwell-time", *Proc. 38th IEEE CDC*, 1999, cilt 3, s. 2655–2660. DOI 10.1109/CDC.1999.831330 | Crossref |
| K16 | Lee, S., Cho, N., Kim, Y., "Command governor for impact-angle guidance to fast targets under field-of-view constraint", *Aerospace Science and Technology*, **167**, 2025, mad. 110695. DOI 10.1016/j.ast.2025.110695 | Crossref |
| K17 | Jeon, I.-S., Lee, J.-I., Tahk, M.-J., "Impact-time-control guidance law for anti-ship missiles", *IEEE Trans. Control Systems Technology*, **14**(2), 2006, s. 260–266. DOI 10.1109/TCST.2005.863655 | Crossref |
| K18 | Hodžić, M., Prljača, N., "Performance analysis of proportional navigation, neoclassical and pseudoclassical guidance methods on a 6DOF missile model", *Elektrotehniški Vestnik*, **92**(1-2), 2025, s. 26–34. | PDF doğrudan okundu |
| K19 | Zarchan, P., "Proportional navigation and weaving targets", *J. Guidance, Control, and Dynamics*, **18**(5), 1995, s. 969–974. DOI 10.2514/3.21492 | Crossref (⚠ tam metin okunmadı) |

### (c) Bizim ölçümümüzle kıyas — **3× kuralı bizim uçurumumuzu tam yerinde kesiyor**

`ρ = 51 m`, `a_T = V_T²/ρ`, tavan `a_M = 12 m/s²`:

| ω (°/s) | ρ (m) | a_T (m/s²) | **a_M/a_T** | senin ölçtüğün <3 m |
|---|---|---|---|---|
| 1,5 | 687 | 0,47 | **25,5** | %44 |
| 5 | 206 | 1,57 | **7,6** | %28 |
| 11 | 94 | 3,45 | **3,5** | %40 |
| **20** (ovalin ucu) | **51** | **6,35** | **1,89** | **%7** |
| 35 | 29 | 10,99 | **1,09** | %8 |

**Palumbo'nun "3×" kuralı, oran 3,5 (→%40) ile 1,89 (→%7) arasındaki uçurumun
tam üstünde.** Literatürden türeyen eşik:
`a_T ≤ 12/3 = 4,0 m/s² → ω ≤ 12,7 °/s`.
Yanal eksene yalnız 8 m/s² kalırsa: `ω ≤ 8,5 °/s` — **koddaki
`AVCI_DEVIR_DONUS=8` önerisinin tam sayısal karşılığı.**
Senin ölçtüğün uçurum ise **15 °/s**'de. İki bağımsız yol, bir bant farkla
aynı yeri gösteriyor.

**Gecikme × manevra çarpımı, ölçülmüş hâliyle.** Von Moll'un kinematiğini
(`ḋ = V_T cos ψ − V_M`, `ψ̇ = −(V_T/d) sin ψ − κV_T/ρ`) bizim sayılarımızla
kartezyen entegre ettim (V_M=21,7, V_T=17,99, a_max=12, 4 s pencere, d₀=13 m):

| ω | **gecikmesiz** | **gerçek gecikme (τ=0,35 + 0,25 s)** |
|---|---|---|
| 5 °/s | 0,00 m | 0,09 m |
| 11 °/s | 0,00 m | 0,02 m |
| **20 °/s** | **0,00 m** | **4,92 m** |
| 35 °/s | 7,07 m | 9,55 m |

**Gecikmesiz saf takip 20 °/s'yi sorunsuz kapatıyor. Gecikmeli kapatamıyor.**
Yani 15–30 bandındaki çöküş **geometrik zorunluluk değil, gecikme eseri** —
Palumbo'nun 100/300/500 ms eğrilerinin aynısı. Bizim toplam gecikmemiz
(~0,60 s) onun **en hantal (500 ms) vakasından beter**.

Gecikme taraması (ω=20, d₀=13):

| toplam gecikme | en yakın | yanal sapma |
|---|---|---|
| 0,00 s | **0,00 m** | −0,3 m |
| 0,25 s | 0,78 m | −1,1 m |
| 0,40 s | 0,92 m | −2,2 m |
| **0,60 s (bizim)** | **4,92 m** | **−4,9 m** |
| 0,85 s | 8,89 m | −8,6 m |

**0,40 → 0,60 s arasında uçurum var ve biz uçurumun yanlış tarafındayız.**

**Kestirme (ileri-besleme) ne kadar kurtarıyor?** Aynı simülasyonda saf takibe
`ω_T` ileri-beslemesi ekledim (devir anında dondurulmuş, GPS'ten alınan `tgt_omega`):

| ω | ff=0 | ff=0,5 | ff=1,0 |
|---|---|---|---|
| 5 °/s | 0,09 m | 0,24 m | 0,75 m |
| 11 °/s | 0,02 m | 0,50 m | 1,60 m |
| **20 °/s** | **4,92 m** | **2,90 m** | 3,22 m |
| 35 °/s | 9,55 m | 8,39 m | **6,90 m** |

**Yüksek ω'da kestirme ~%40 kazandırıyor; düşük ω'da ZARAR veriyor.**
→ ileri-besleme **ω'ya göre programlanmalı** (düşük ω'da kapalı).
Kestirim hatasına dayanıklılık (ω=20, ff=1): hata +20% → 4,08 m, +40% → 5,26 m,
−30% → 2,69 m. **Aşırı kestirim, eksik kestirmekten daha zararlı** → ff'i 1,0
değil 0,5 seç.

### (d) Somut öneri

**Ö-F. SINIRLI BEKLEME (dwell-time'lı devir kapısı) — şartnameyle uyumlu.**
Formülasyon (literatürün standart formu, K14/K15/K4):

```
t_go   = R / max(V_M − V_T, ε)
phi    = omega_T * t_go                    # = ZEM argümanı
DEVRET eger  (ardisik_kare >= 10)  VE  ( phi <= THETA  VEYA  bekleme >= T_BEKLE )
```
`bekleme` = "10 kare şartı ilk sağlandığı andan beri geçen süre".
Başlangıç: `THETA = 25°`, `T_BEKLE = 3,0 s`.
Şartname ihlali yok: geçiş **en geç 3 s içinde** olur; yalnız iyi bir faz
varsa erken olur. Depoda `AVCI_DEVIR_DONUS` kapısı bunun ω-only sürümü olarak
zaten mevcut ama **KAPALI (999)** ve sınırsız (bekleme üst sınırı yok).

**Ö-G. `ω_T` ileri-beslemesi, ω'ya göre programlı.**
`ff = 0` (ω < 10 °/s) → `ff = 0,5` (ω ≥ 10 °/s). Beklenen: 15–30 bandında
CPA 4,9 → 2,9 m (%41 iyileşme, simülasyon).

**Ö-H. Faz seçimi (impact-time, K17).** Tur 29,63 s ve sabit. GPS fazında
standoff/hız ile t_go şekillendirilerek temas hedefin düz kısmına denk getirilir.
Bu, "bekleme"nin şartname-nötr sürümü. (Büyük iş; Ö-F başarısız olursa bak.)

### (e) Riskler / nasıl çürütülür

- ⚠⚠ **İŞARET RİSKİ — depoda ÜÇ KEZ vurdu** (`gorsel-yasa-ayna-hatasi`).
  `ω_T` ileri-beslemesi yanlış işaretle girerse simülasyonda ω=11'de 0,02 → 1,60 m
  (80× kötü). **Önce tek koşuda işaret doğrulanmalı**, sonra kazanç.
- **Şartname denetimi:** `T_BEKLE` mekanizması bir teste bağlanmalı; `T_BEKLE`
  büyütülünce testin kırılması gerekir (5 s kilit kapısında yapılan gibi).
- **ÇEVRİMDIŞI TUZAK:** iki öneri de yörüngeyi değiştirir → replay ile
  değerlendirilemez. Uçuşta A/B.
- **Çürütme:** `T_BEKLE=0` (yani kapı fiilen kapalı) olumsuz kontrol kolu olarak
  koşulmalı. `THETA` kolu tabandan iyi çıkmazsa `φ` hipotezi düşer.

---

## SORU 4 — Yanal aşma: kontrolcü aşması mı, geometrik zorunluluk mu?

### (a) Literatürün dediği

**Dairesel yörüngedeki hedefin saf takibi için KAPALI FORM YOK.** Von Moll,
Casbeer, Weintraub & Pachter (2024) bağıl kinematiği verir:

```
ḋ  =  V_T·cos ψ − V_M
ψ̇  = −(V_T/d)·sin ψ − κ·V_T/ρ
```
(`ψ` = hedefin hız vektörünün LOS'a göre açısı, `κ = ±1` dönüş yönü.)
Makale doğrudan söylüyor: *"The analytical solution of the kinematic equations of
motion is not feasible"*; hedef **düz** giderken (`ρ→∞`) sistem çözülebilir ve
`ψ` monoton olarak 0'a gider — **ama daire durumunda bu özellik kaybolur**,
`ψ` 0'a gitmez. Problem 1742'den beri (Ladies' Diary) açık; Shneydor'un kitabı
literatürün *"presents unusual difficulties"* değerlendirmesini aktarır.

**İşte yanal ıraksamanın kaynağı:** `ψ̇` denklemindeki `−κ·V_T/ρ` terimi
**mesafeyle sönmez**. Düz hedefte kuyruk hizasına oturunca `ψ̇ → 0`; dönen
hedefte `ψ̇ → −κ·ω_T ≠ 0`. Takipçi bu kaymayı ancak kendi hız vektörünü de
`ω_T` hızıyla döndürerek sıfırlayabilir — yani **istasyon tutmanın kendisi
sürekli yanal ivme ister.**

**Denge kuyruk açısı.** `ψ̇ = 0` ⇒ `sin ψ* = −κ·d/ρ`. Yani:
- Denge yalnız `d ≤ ρ` iken vardır. `d > ρ` ise takipçi hedefin arkasına
  **hiç oturamaz**, `ψ` sarılır.
- İstasyon tutmanın bedeli: `a_gerek = V_M · ω_T`.

**Küçük yarıçapta davranış.** Von Moll: `ρ` küçüldükçe takipçinin yörüngesi
*"exhibits small oscillations around heading toward the Target's turn circle
center"* — yani hedefin kendisini değil, **dönüş dairesinin merkezini** kovalar.

**Palumbo'nun `e⊥`'si.** (K1) Devir hatasının LOS'a dik bileşeni terminal fazın
kapatmak zorunda olduğu ıskadır. Bizim "YANAL" eksenimiz budur.

### (b) Kaynaklar

| # | Künye | Doğrulama |
|---|---|---|
| K20 | Von Moll, A., Casbeer, D. W., Weintraub, I. E., Pachter, M., "Pure Pursuit of a Target on a Circular Trajectory", AFRL Control Science Center / AFIT, 2024. | PDF doğrudan okundu (13 s.) — ⚠ konferans/dergi künyesi doğrulanamadı (§7) |
| K21 | Shneydor, N. A., *Missile Guidance and Pursuit: Kinematics, Dynamics and Control*, Horwood Publishing, 1998, 259 s. ISBN 9781904275374 (Böl. 3: Pure Pursuit). | Yayıncı/katalog kaydı — ⚠ içerik K20 üzerinden alıntılandı |

### (c) Bizim ölçümümüzle kıyas — **sayılar birebir tutuyor**

`ρ = 51 m`, `ω_T = 20,2 °/s = 0,353 rad/s`, `V_M = 21,7 m/s`:

| büyüklük | değer |
|---|---|
| İstasyon tutma ivmesi `V_M·ω_T` | **7,65 m/s²** = 3B bütçenin **%64'ü** |
| Denge kuyruk açısı, d=11 m | 12,5° |
| Denge kuyruk açısı, d=16 m | 18,2° |
| Denge kuyruk açısı, d=22 m | 25,6° |
| Denge yok olduğu menzil (`d>ρ`) | **> 51 m** |

**Simülasyon vs ölçüm (yanal eksen, hedefin çerçevesinde):**

| | başlangıç | 4 s sonra |
|---|---|---|
| **Senin ölçtüğün (715 devir)** | +1,6 m | **−4,9 m** |
| **Simülasyon** (ω=20, d₀=13, gerçek gecikme) | 0 m | **−4,88 m** |
| Simülasyon, **gecikmesiz** | 0 m | −0,3 m |
| Simülasyon, yanal bütçe 8 m/s²'ye kısılırsa | 0 m | **−14,6 m** |

**Hüküm: yanal aşma bir kontrolcü aşması DEĞİL.** Gecikmesiz aynı geometri
−0,3 m veriyor; gecikmeyle −4,9 m. Aşma = **dönüş geometrisinin ürettiği rampa
girdi × kontrol gecikmesi**. Depo bunu bağımsız olarak zaten türetmişti
(supervisor.py: *"saf takip yön kanalında SAF ORANSAL kontrolcüdür; rampa girdiye
kalıcı hatası e_ss = rampa_eğimi/K"*). Literatürdeki adı: **hedef ivmesinin
telafi edilmemesi** → çözümü **APN / ileri-besleme**, kazanç değil.

Ayrıca senin elediğin hipotezler bu hükmü destekliyor: **VZ_MAX kırpması %1**
(doyma değil), **kadraj açı medyanı 5,6°** (FOV kaybı değil), **görsel faz
medyanı 5,79 s** (kararsızlık değil).

Geçişlerin **%88'inin uzaklaşması** da geometriyle uyumlu: en yakın an 2,02 s'de,
sonrası `ψ`'nin sarılması — von Moll'un "`ψ` 0'a gitmez" maddesi.

### (d) Somut öneri

**Ö-I. Yanal kazancı ARTIRMA.** Literatür ve simülasyon aynı şeyi söylüyor:
kalıcı hata rampa girdiden geliyor, `K` sonlu olduğu sürece sıfırlanmaz.
Çözüm sırası: (1) gecikme, (2) `ω_T` ileri-beslemesi (Ö-G), (3) devir kapısı (Ö-F).

**Ö-J. Menzil kapısını `d < ρ` ile de sınırla.** `AVCI_DEVIR_BOYUT=14 px`
zaten ~16,6 m veriyor; `ρ=51 m` çok üstünde → bu kısıt bizde **bağlayıcı değil**,
kayda geçsin (gelecekte daha büyük ρ'lu senaryoda bağlayıcı olur).

### (e) Riskler / nasıl çürütülür

- Simülasyon 2B ve nokta-kütle; dikey kanal ve bbox gürültüsü yok. −4,88 ile
  −4,9'un birebir tutması **tesadüf olabilir**. Çürütme: gecikmeyi düşürüp
  yanal aşmanın küçülmesi ölçülmeli — küçülmezse model yanlıştır.
- Alternatif açıklama (test edilmedi): yanal ofset GPS fazından **miras** kalıyor
  olabilir (+1,6 m başlangıç). Devir anındaki yanalın dağılımı ölçülmeli.

---

## SORU 5 — ν = 1,19 ile yakalanabilirlik: literatür ne öneriyor?

### (a) Literatürün dediği

**PPN yakalanabilirlik teoremi (Guelman geleneği, Ghose'un ders notlarındaki
Teorem 11.1 / 11.2):**

| hedef | garantili yakalama YETER koşulu |
|---|---|
| manevrasız | `ν > 1` **ve** `(N−1)·ν > 1` |
| **manevralı** | **`ν > √2`** **ve** `(N−1)·ν > 1` |

artı: başlangıç hız vektörü `S⁺_α` sektörünün **dışında** olmalı, burada
`S⁺_α : −sin⁻¹(1/ν) − π ≤ α ≤ sin⁻¹(1/ν) − π` (α = füze hız vektörünün LOS'a
göre açısı). Notlar açıkça uyarır: bunlar **yeter** koşuldur, gerek değil —
gerçek yakalama bölgesi daha büyük olabilir.

**Saf takipte kapanma hızı.** `ḋ = V_M·(μ·cos ψ − 1)`; kuyrukta (`ψ=0`)
`ḋ = −(V_M − V_T)`. **T saniyelik bir pencerede kapatılabilen azami menzil
`R_max = (V_M − V_T)·T`.** μ→1 giderken bu sıfıra gider.

Bu, sahada iki kez bağımsız olarak raporlanmış:
- Bhattacharya (2021): PN-Heading ile **düz hedef, hedef hızı = araç hızının
  %100'ü** konfigürasyonunda isabet **her araç hızında 0**; gerekçe aynen
  *"during this chase period, the UAV's velocity is in the same direction as the
  target's. Therefore, the target's speed must be less than the UAV's, or it will
  be impossible to maintain a nonzero closing velocity."*
- Pliska vd. (2024): *"For the PN guidance law to converge towards interception,
  the relative velocity between the interceptor and the target must be negative"*
  — bu sınırı aşmak için GPN (General PN) değişkesi kullanıyorlar.

**ν < 1 olsaydı** (biz hedeften yavaş olsaydık) kanonik cevap **head pursuit**
olurdu (Shima & Golan 2007): hedefin ÖNÜNE geçip aynı yönde uçmak.
Bizim durumumuz ν > 1 olduğu için bu gerekli değil — ama ν'nün √2'ye
yakınlığı, "saf kuyruk takibi yeter" demeye izin vermiyor.

**Saf takip yerine kesme (collision course).** Von Moll (K20): CC varış zamanı
`t_cc`, saf takip varış zamanının **alt sınırıdır** ve kapalı formda verilir:
`t_cc = [d·μ·cosψ − d_c + √((d_c − d·μ·cosψ)² − (1−μ²)(d_c² − d²))] / (1 − μ²)`.
`(1−μ²)` paydası μ→1'de patlar — μ'nün 1'e yakınlığının maliyeti tam burada.

### (b) Kaynaklar

| # | Künye | Doğrulama |
|---|---|---|
| K22 | Ghose, D., *Guidance of Missiles*, NPTEL ders notları, Modül 10 / Ders 33: "PPN Capturability in the Relative Velocity Space", 2012, s. 207–211. | PDF doğrudan okundu |
| K23 | Guelman, M., "A qualitative study of proportional navigation", *IEEE Trans. Aerospace and Electronic Systems*, **AES-7**(4), 1971, s. 637–643. DOI 10.1109/TAES.1971.310406 | Crossref |
| K24 | Guelman, M., "Proportional Navigation with a Maneuvering Target", *IEEE Trans. Aerospace and Electronic Systems*, **AES-8**(3), 1972, s. 364–371. DOI 10.1109/TAES.1972.309520 | Crossref (⚠ tam metin okunmadı; içerik K22 üzerinden) |
| K25 | Shima, T., Golan, O. M., "Head Pursuit Guidance", *J. Guidance, Control, and Dynamics*, **30**(5), 2007, s. 1437–1444. DOI 10.2514/1.27737 | Crossref |
| K26 | Bhattacharya, A., "Toward Increased Airspace Safety: Quadrotor Guidance for Targeting Aerial Objects", CMU yüksek lisans tezi, arXiv:2107.01733, 2021. | PDF doğrudan okundu (58 s.) |
| K27 | Pliska, M., Vrba, M., Báča, T., Saska, M., "Towards Safe Mid-Air Drone Interception: Strategies for Tracking & Capture", *IEEE Robotics and Automation Letters*, 2024. DOI 10.1109/LRA.2024.3451768 (arXiv:2405.13542) | PDF doğrudan okundu |

### (c) Bizim ölçümümüzle kıyas

**⚠ HAFIZA DÜZELTMESİ.** Depo hafızasındaki *"Guelman koşulu manevra yapan hedef
için ν>2 istiyor"* kaydı **yanlış**. Doğrusu **ν > √2 ≈ 1,414**.

| | değer |
|---|---|
| Bizim ν (V_M ≈ 21,4) | **1,19** |
| Manevralı hedef için gereken | **1,414** |
| Gereken asgari hız | **V_M ≥ 25,44 m/s** |
| Tavan hızımızda (24 m/s) ν | **1,334** — **hâlâ altında** |
| Eksik | **1,44 m/s** |
| `(N−1)ν > 1` şartı | `N > 1,84` → N≥2 ile **sağlanıyor** |
| `S⁺_α` sektörü sınırı | `sin⁻¹(1/1,19) = 57,2°` → yasak sektör \|α\| ∈ [122,8°, 237,2°]; kuyruk takibinde **sorun yok** |

**`R_max = (V_M − V_T)·T` formülü senin iki bulgunu birden açıklıyor:**

| V_M | μ | ν | kapanma | **4 s'de kapatılabilir menzil** | senin ölçtüğün |
|---|---|---|---|---|---|
| 18,0 | 0,999 | 1,001 | **0,01 m/s** | **0,0 m** | <18 m/s → **%16** |
| 20,0 | 0,899 | 1,112 | 2,01 | 8,0 m | |
| 21,7 | 0,829 | 1,206 | 3,71 | **14,8 m** | 10–16 m **en iyi** |
| 24,0 | 0,750 | 1,334 | 6,01 | 24,0 m | >22 m/s → **%39** |
| 25,4 | 0,708 | **1,414** | 7,45 | 29,8 m | (teorik eşik) |

**Devir menzilinin ">22 m ölümcül (%0)" olması ayrı bir olgu değil:**
21,7 m/s'de 4 saniyelik pencerede kapatılabilen azami menzil 14,8 m'dir.
22 m'den devretmek, matematiksel olarak kapanamayacak bir angajmana girmektir.
Senin `korelasyon(menzil, kapatma) = −0,077` sonucunun normalize ölçütle
kaybolması da bununla tutarlı: menzil ham CPA'yı belirliyor ama **kapatma
ORANINI** belirlemiyor; asıl belirleyici `φ`.

**⚠ "Daha hızlı uç" monoton DEĞİL.** Simülasyonda ω=20 °/s, d₀=13 m:
V_M=21,7 → 4,92 m; **V_M=24 → 6,22 m (daha KÖTÜ)**; V_M=25,5 → 5,18 m;
V_M=28 → 3,85 m. Sebep: istasyon tutma ivmesi `V_M·ω_T` hızla büyür
(21,7'de 7,65 m/s², 24'te 8,47, 28'de 9,88 m/s²) → dönüş yetkisi azalır.
**Hız, dönüş bütçesiyle takas edilir** — depodaki `AVCI_IBVS_DONUS_BUTCE`
mekanizmasının tam olarak ölçtüğü takas.

### (d) Somut öneri

**Ö-K. Devir anında kapanma hızı kapısı: `V_M − V_T ≥ 3 m/s`.**
Literatürdeki karşılığı: "closing velocity must be negative" (K26, K27).
Bizde bu, GPS fazının fren/`V_CAP` mantığının devir anında bizi yavaşlatmamasını
garanti eder. Ölçüt: devir anındaki `V_M` dağılımı; %16'lık <18 m/s kuyruğu kesilir.

**Ö-L. Devir menzili tavanını kapanma hızına bağla:**
`R_devir ≤ (V_M − V_T) · T_pencere`. `T_pencere=4 s`, `V_M=21,7` → **14,8 m**.
Bugünkü `AVCI_DEVIR_BOYUT=14 px ≈ 16,6 m` buna zaten yakın; **16 px (≈14,6 m)**
tam oturur. Tek değişkenli, mevcut kapı.

**Ö-M. Uzun vade: V_M tavanını 25,5 m/s'ye çıkarmayı DEĞERLENDİR** (ν>√2).
⚠ Ama önce Ö-I/Ö-G yapılmalı — yukarıdaki tablo hızın tek başına kötüleşme
üretebileceğini gösteriyor.

### (e) Riskler / nasıl çürütülür

- `ν > √2` bir **yeter** koşul. Altında yakalama imkânsız değil; nitekim
  vuruşumuz var. Bunu "hız artmadan olmaz" diye okumak **hatalı çıkarım** olur.
- Ö-K, angajman sayısını düşürebilir (yavaşken devretmeyi reddeder).
  Çürütme kolu: kapı açıkken toplam vuruş sayısı düşerse öneri düşer.
- Ö-L, `AVCI_DEVIR_BOYUT` kapısının **kare geçerliliğini** de etkiliyor
  (`algi_sureklilik.py` bulgusu: kapı 20–30 m bandındaki karelerin %66'sını
  eliyor ve süreklilik sayacını sıfırlıyor). **`AVCI_DEVIR_BOYUT_MOD=devir`
  ile birlikte** denenmeli, yoksa 5 s kilit şartını kırar.

---

## SORU 6 — Benzer sistemler: anti-drone / önleyici İHA'larda devir ve bildirilen ıska

### (a) Literatürün dediği + (b) Kaynaklar

**K27 — Pliska, Vrba, Báča & Saska (2024), IEEE RA-L.** Ağ taşıyan bir çok
rotorlu önleyici, LiDAR tabanlı tespit + IMM filtresi + kendi geliştirdikleri
FRPN yasası. 100 farklı hedef yörüngesinde 500 simüle deney (~14 saat uçuş verisi),
sonra gerçek uçuş. Araç kısıtları: `v_max = 8 m/s`, `a_max = 4 m/s²`
(dikeyde 2), `ω_baş,max = 2 rad/s`. Gerçek dünyada **5 m/s** uçan hedef yakalandı;
önleme manevrası ~2 s.

| yasa | yörünge kapsamı | önleme/yörünge | ilk denemeye süre | doğruluk (tüm / ilk) |
|---|---|---|---|---|
| **Saf takip (PP)** | %72 | 4,40 | 32,22 s | **1,19 m** / 1,23 m |
| LPN | %95 | 12,65 | 19,73 s | 0,17 m / 0,03 m |
| GPN2 | %100 | 17,60 | 8,15 s | 0,18 m / 0,34 m |
| MPC (onların) | %98 | 16,55 | 11,98 s | 0,38 m / 0,38 m |
| **FRPN (onların)** | **%100** | **24,38** | **5,93 s** | **0,16 m** / 0,04 m |

**K26 — Bhattacharya (2021), CMU.** Quadrotor + tek kamera, "füze güdümünden
ilham alan" beş yasa, her konfigürasyonda 50 deneme. Süpürme: araç hızı 2–5 m/s,
hedef hızı aracın %25–%100'ü, 3 hedef yörüngesi (düz, sekiz, düğüm).
**Başarı tanımı** dikkat çekici — bizim ölçütlerimize doğrudan aday:
(1) hedefe 0,5 m yakınlık, (2) kovalama < 20 s, (3) araç arenayı terk etmesin,
(4) **hedef 3 s'den uzun süre kadraj dışında kalmasın**.
Bulgusu: TPN en iyi; ve **kapanma hızı arttıkça isabet DÜŞÜYOR** —
gerekçesi aynen bizimki: *"this results in lower hit rates, which may be due to
lag in the UAV controllers' ability to fulfill desired acceleration commands...
the moment of the aircraft and the response time of the controller both contribute
to lag in achieving the necessary roll angle."*

**K28 — Liou & Cheng (2026), arXiv:2607.12801.** Sabit kanat + pan-tilt kamera,
üç faz: görsel edinim → NMPC ile takip/loiter → **BPNG ile terminal**.
Faz geçişi "loiter yarıçapı ve irtifa ölçütleri sağlandığında" tetikleniyor.
Yazarların dürüst notu: *"This altitude serves as an arbitrarily chosen transition
threshold rather than a tuned parameter"* — yani onlarda da devir eşiği
geometriden türetilmiş değil. Ve devir geçici rejimini gözlüyorlar:
*"despite the transient spikes triggered by the tracking-to-terminal controller
handoff, the target pixel coordinates are kept tightly centered."*

### (c) Bizim ölçümümüzle kıyas — dürüst yerleştirme

| | Pliska (K27) | Bhattacharya (K26) | **BİZ** |
|---|---|---|---|
| Hedef hızı | 5 m/s (gerçek) | araç hızının %25–100'ü | **17,99 m/s** |
| Araç hızı | 8 m/s | 2–5 m/s | 18–24 m/s |
| ν = V_M/V_T | **1,6** | 1,0–4,0 | **1,19** |
| Yanal ivme tavanı | 4 m/s² | — | 12 m/s² |
| a_M / a_T | (hedef manevrası küçük) | — | **1,89** (ovalin ucunda) |
| Bildirilen doğruluk | 0,16 m (PN) / 1,19 m (PP) | 0,5 m eşikli isabet oranı | **CPA medyan 5,11 m**, en iyi 0,44 m |
| Algı gecikmesi | LiDAR, düşük | 30 Hz, basit segmentasyon | **~0,6 s uçtan uca** |

**Üç ayrı ders:**

1. **Saf takip ile PN arasındaki fark 7 kat.** K27'de PP 1,19 m, PN 0,17 m; ve
   PP yörüngelerin yalnız %72'sinde bir deneme bile üretebiliyor. Görsel fazımız
   özünde saf takiptir (IBVS hedefi merkeze alır). **Bu, `AVCI_IBVS_PN` kolunun
   yeniden değerlendirilmesi için literatürden gelen en güçlü argüman**
   (depo notu: "λ̇ kapısı zararlı" iddiası zaten çürümüştü).
2. **Metrik çerçevesi yanlış olabilir.** K27'nin birincil metrikleri
   *"ilk denemeye süre"* ve *"yörünge başına önleme sayısı"* — tek geçişin CPA'sı
   değil. Onların en iyi yasası bir yörüngede **24 deneme** yapıyor. Bizim tur
   süremiz 29,63 s ve görsel faz ömrümüz 5,79 s → prensipte turda birkaç deneme
   mümkün. **Tekrar-angajman oranını ölçmüyoruz.**
3. **Gecikme mekanizması bağımsız olarak iki yerde doğrulanmış** (K26 ve K2) —
   bizim §3'teki simülasyon bulgumuz tekil değil.

### (d) Somut öneri

**Ö-N. K26'nın başarı tanımını benimse.** Özellikle "hedef 3 s'den uzun kadraj
dışında kalmasın" ölçütü; bizde `algi_sureklilik.py` bu veriyi zaten üretiyor.

**Ö-O. Tekrar-angajman metriği ekle** (salt ölçüm, davranış değişmez):
tur başına devir sayısı, ilk devre kadar geçen süre, tur başına <3 m geçiş sayısı.

### (e) Riskler / nasıl çürütülür

- Ölçekler çok farklı: onların hedefi 5 m/s ve manevrası hafif; bizimki 18 m/s
  ve sürekli 6,35 m/s² çekiyor. **Doğruluk sayıları doğrudan kıyaslanamaz**;
  kıyaslanabilir olan **yasa sıralaması** ve **mekanizma**.
- K28 simülasyon-only ve hedefi deniz yüzeyi aracı — devir eşiği örneği
  yöntemsel, sayısal değil.

---

## 7. KAYNAK YOK / DOĞRULANAMADI — dürüstlük kaydı

**Aradım, BULAMADIM:**

1. **"Hedefin düz segmentini bekleyerek teslim"** — güdüm literatüründe
   *"wait for target to stop maneuvering"*, *"delay handover until straight
   segment"*, *"acquisition during target turn"* aramalarının hiçbiri bir
   çalışma vermedi. **Literatür beklemiyor, kestiriyor (APN).**
   Sınırlı beklemenin karşılığı ancak dolaylı: dwell-time switching (K14, K15),
   önceden tanımlı karar anı (K3, K4), command governor (K16).
2. **Zarchan'ın `N/(N−2)` gerekli ivme oranı formülü.** Arama motoru özetleri
   veriyor ama **birincil kaynakta doğrulayamadım**; Wikipedia'nın
   *Proportional navigation* maddesinde de yok. **Raporda kullanılmadı.**
   Yerine Palumbo'nun kelimesi kelimesine doğrulanmış ifadesi kullanıldı:
   *"For an ideal autopilot response, PN-homing would result in acceleration
   requirements of three times the target maneuver."* (K2)
3. **"Devirde t_go ≥ 10 × güdüm zaman sabiti olmalı" başparmak kuralı.**
   Yaygın olarak anılıyor ama birebir künyesini bulamadım. **Raporda iddia
   olarak kullanılmadı**; yerine kendi gecikme taramam ve K2'nin
   100/300/500 ms eğrileri kullanıldı.

**Künyesi doğru ama TAM METNİNE ERİŞEMEDİĞİM kaynaklar** (içerikleri yalnız
özet/arama sonucu düzeyinde, raporda ona göre işaretlendi):

- DTIC ADA386524, "Midcourse and Handover in Cruise Missile Defense" — DTIC
  sitesi bakımda (403 / bakım sayfası). Yalnız arama özeti kullanıldı.
- K7 (Liu vd. 2016, IJAE) — Wiley/Hindawi 402 Payment Required.
- K6 (Sun vd. 2022, ASCC) — yalnız Crossref kaydı; özet bile alınamadı.
- K19 (Zarchan 1995, weaving targets) — yalnız Crossref kaydı.
- K24 (Guelman 1972) — teorem içeriği K22 (Ghose ders notları) üzerinden alındı.
- K21 (Shneydor 1998) — kitap; içerik K20'nin alıntıları üzerinden.
- K8 (BIT/PRIS ortak güdüm PDF'i) — metin okundu ama **cilt/sayfa künyesi
  doğrulanamadı**; "Chinese Journal of Aeronautics" sürümü olduğu PDF başlığından.
- K20 (Von Moll vd. 2024) — PDF tam okundu, **konferans/dergi künyesi
  doğrulanamadı** (AFRL/AFIT çıktısı olarak yayımlanmış görünüyor).

**Simülasyon şeffaflığı.** Bu rapordaki simülasyon sayıları benim K20'nin
denklem (1)'ini bizim parametrelerimizle kartezyen entegre etmemden geliyor
(`V_T=17,99`, `V_M` değişken, `a_max=12 m/s²`, 1. mertebe araç gecikmesi `τ`,
saf ölçüm gecikmesi, 4 s pencere, `dt=2 ms`). **Depo koduna yazılmadı**;
betikler geçici dizinde. Denklem yukarıda verildi, yeniden üretilebilir.
⚠ 2B, nokta-kütle, bbox gürültüsü ve dikey kanal yok. **Uçuş ölçümünün yerine
geçmez** — nitekim depo bunun tam tersini yaşamıştı (çevrimdışı tuzak).

---

## 8. ÖNCELİK SIRASINA DİZİLMİŞ, TEK DEĞİŞKENLİ ÖNERİ LİSTESİ

> Kural: **her koşuda TEK değişken.** Her öneride olumsuz kontrol kolu var.
> ⚠ Hepsi yörüngeyi değiştirir → **çevrimdışı replay ile değerlendirilemez**
> (KILIT_BULGUSU.md dersi). Uçuşta A/B.

### D0 — ALTYAPI (deney değil, ön koşul)

| | |
|---|---|
| **İş** | Uçtan uca gecikme bütçesini ÖLÇ: kare zaman damgası → tespit → yasa → komut → araç tepkisi |
| **Env kapısı** | yok (salt ölçüm) |
| **Mekanizma** | mevcut loglar + `AVCI_IBVS_ARAC_TAU`'nun MODEL mi GERÇEK mi olduğunun ayrılması |
| **Başarı ölçütü** | toplam gecikmenin sayısı (hipotez: ~0,6 s) |
| **Neden 1. sırada** | Simülasyon 0,60 → 0,40 s'nin CPA'yı **4,92 → 0,92 m** yaptığını söylüyor. Bu, listedeki her şeyden büyük. Ölçmeden hangi bileşenin kesileceği bilinemez. |

### D1 — φ KAPISI + SINIRLI BEKLEME  ★ en yüksek beklenen kazanç

| | |
|---|---|
| **Env kapısı** | `AVCI_DEVIR_PHI=25` (yeni) + `AVCI_DEVIR_BEKLE_S=3.0` (yeni). Ara adım: mevcut `AVCI_DEVIR_DONUS=15` (ω-only sürüm, bekleme sınırı YOK) |
| **Mekanizma** | `phi = tgt_omega * R/max(V_M−V_T, ε)`; devir = `10 kare` VE (`phi≤Θ` VEYA `bekleme≥T`) |
| **Başarı ölçütü** | **normalize kapatma oranı** (senin ölçütün) ≥ %60 (taban ~%46); `<3 m` oranı; **ve devir sayısı düşmemeli** |
| **Beklenen kazanç** | senin tablondan: `φ<25°` bandı %79/%55 → kapatmada **+15…+25 puan** |
| **Olumsuz kontrol** | `AVCI_DEVIR_BEKLE_S=0` (kapı fiilen kapalı) |
| **Risk** | şartname; `T_BEKLE` bir testle korunmalı. `ω_T` bayatlığı (D0'da ölç) |

### D2 — `ω_T` İLERİ-BESLEMESİ (programlı)

| | |
|---|---|
| **Env kapısı** | `AVCI_IBVS_OMEGA_FF=0.5` (yeni), `AVCI_IBVS_OMEGA_FF_MIN=10` (°/s altında kapalı) |
| **Mekanizma** | görsel yasanın yaw hız komutuna `ff·ω_T` eklenir; `ω_T` **devir anında dondurulur** (görsel fazda hedef GPS'i YASAK — bu bir devir-anı parametresi) |
| **Başarı ölçütü** | 15–30 °/s bandında CPA 7,54 → **≤5,0 m**; yanal son değer −4,9 → **≥−3,5 m** |
| **Beklenen kazanç** | simülasyon: 4,92 → 2,90 m (%41) |
| **Olumsuz kontrol** | `AVCI_IBVS_OMEGA_FF=0` |
| **Risk** | ⚠⚠ **İŞARET.** Ayna hatası depoda 3 kez tekrarladı. Yanlış işaret ω=11'de 0,02 → 1,60 m. Önce tek koşuda işaret doğrulanır, sonra kazanç taranır. `ff=1.0` KULLANMA (aşırı kestirim eksikten zararlı) |

### D3 — BUMPLESS: GÖRSEL YASAYI İZLEME KİPİNDE ÇALIŞTIR

| | |
|---|---|
| **Env kapısı** | `AVCI_IBVS_IZLEME=1` (yeni), `AVCI_IBVS_IZLEME_TT=0.5` |
| **Mekanizma** | görsel yasa GPS fazında da her tik hesaplanır (komut vermez), durumu `(u_GPS − u_görsel)/T_t` ile sürülür (Hanus koşullandırma, K9/K10) |
| **Başarı ölçütü** | devir anında `\|Δvz_cmd\| < 0,2 m/s` ve `\|Δyaw_rate\| < 5 °/s`; sonra CPA |
| **Beklenen kazanç** | `HIZ_SICAK`'ın (tek seferlik başlatma) verdiği <2 m %22→%41 kazancının üstüne artımlı; dikey sıçrama zaten 2,91 m'den düşürüldü |
| **Olumsuz kontrol** | `AVCI_IBVS_IZLEME=0` |
| **Risk** | **CPU/GIL** — her tik ek hesap gecikmeyi büyütürse NET ZARAR (D0'ı bekle) |

### D4 — MEVCUT ASPECT KAPISINI AÇ

| | |
|---|---|
| **Env kapısı** | `AVCI_DEVIR_ASPECT=40` (kod yorumu fiziğin ~25° istediğini söylüyor) |
| **Mekanizma** | zaten yazılı (`supervisor.py`), varsayılan 999 = KAPALI |
| **Başarı ölçütü** | yandan geçiş devirlerinin oranı; kapatma oranı |
| **Beklenen kazanç** | kod notu "ölçülen faydası duruyor" diyor; D1'in bir alt kümesi olabilir → **D1'den SONRA, D1 yetmezse** |
| **Risk** | D1 ile örtüşür; ikisini aynı anda açma |

### D5 — DEVİR MENZİLİ TAVANINI KAPANMA HIZINA BAĞLA

| | |
|---|---|
| **Env kapısı** | `AVCI_DEVIR_BOYUT=16` (14'ten; ≈16,6 → ≈14,6 m) **+ `AVCI_DEVIR_BOYUT_MOD=devir`** |
| **Mekanizma** | mevcut boyut kapısı; `R_max = (V_M−V_T)·4 s = 14,8 m` |
| **Başarı ölçütü** | >22 m devir sayısı → 0; kapatma oranı |
| **Risk** | ⚠ `MOD=devir` OLMADAN yapma: kapı kare geçerliliğinden 20–30 m bandındaki karelerin %66'sını eliyor ve **5 s kilit şartını yapısal olarak imkânsız kılıyor** (`algi_sureklilik.py` ölçümü) |

### D6 — KAPANMA HIZI KAPISI

| | |
|---|---|
| **Env kapısı** | `AVCI_DEVIR_VKAPANMA=3.0` (yeni, m/s) |
| **Mekanizma** | devir anında `V_M − V_T_kestirim ≥ 3 m/s` değilse bekle (D1'in `T_BEKLE`'si geçerli) |
| **Başarı ölçütü** | <18 m/s devirlerin oranı → ~0; o kolun kapatma oranı |
| **Beklenen kazanç** | ölçülen: <18 m/s %16 vs >22 m/s %39 → o kuyruk kesilir |
| **Risk** | angajman sayısı düşebilir; toplam vuruş düşerse öneri düşer |

### D7 — YANAL DENGE NOKTASI DENETİMİ (ölçüm)

| | |
|---|---|
| **İş** | GPS standoff nişanının yanal ofseti ile görsel nişan noktasının yanal ofseti aynı işarette mi? Dikeyde ters işaretli çıkmıştı (2,91 m sıçrama) — **yanal hiç bakılmadı** |
| **Env kapısı** | yok (salt ölçüm) |
| **Başarı ölçütü** | devir anındaki yanal setpoint sıçraması (m) |
| **Neden önemli** | Dikeydeki hata "yasa doğruydu, nişan yanlıştı" çıktı (vz_cmd/teori 0,93). Aynı hata sınıfı yanalda da olabilir; ölçülmeden bilinmiyor |

### D8 — TEKRAR-ANGAJMAN METRİĞİ (ölçüm)

| | |
|---|---|
| **İş** | K27'nin metrikleri: tur başına devir sayısı, ilk devre kadar süre, tur başına <3 m geçiş |
| **Env kapısı** | yok |
| **Neden** | K27'de en iyi yasa yörünge başına **24 deneme** yapıyor; tek geçişin CPA'sı yanıltıcı olabilir. Bizim tur 29,63 s, görsel faz 5,79 s → turda birkaç deneme mümkün ama **ölçmüyoruz** |

### D9 — V_M TAVANI (uzun vade, ihtiyatlı)

| | |
|---|---|
| **Env kapısı** | hız tavanı (25,5 m/s → ν > √2) |
| **Risk** | ⚠ **monoton değil**: simülasyonda ω=20, d₀=13'te V_M=24, V_M=21,7'den KÖTÜ (6,22 vs 4,92) çünkü istasyon tutma ivmesi `V_M·ω_T` büyüyor. **D0–D2'den sonra** bak |

---

## 9. RAPORUN TEK SAYFALIK ÖZÜ

- Devir ölçütümüz literatürün istediği **hiçbir geometrik kısıtı içermiyor**;
  literatür teslim noktasını bir **optimizasyon değişkeni** sayar (K4).
- Senin `ω·t_go` bulgusu literatürün **ZEM**'idir: `ρ(1−cos(ω·t_go))`.
  Uçurum ZEM ≈ 5 m'de, CPA medyanımız 5,11 m ile aynı yerde.
- 15–30 °/s bandındaki çöküş **geometrik zorunluluk değil**: gecikmesiz
  simülasyon o bandı 0,00 m ile kapatıyor, gecikmeli 4,92 m'de kalıyor.
  **Asıl darboğaz 0,6 s'lik gecikme** (Palumbo'nun en hantal vakasından beter).
- Yanal aşma **kontrolcü aşması değil**: simülasyon −4,88 m, ölçüm −4,9 m.
  Kazanç değil, ileri-besleme/kapı/gecikme çözer.
- ν eşiği **√2 = 1,414** (hafızadaki "2" yanlış). Bizde 1,19; tavan hızda bile
  1,334. Ve `R_max = (V_M−V_T)·T` formülü hem ">22 m ölümcül" hem
  "<18 m/s kötü" bulgularını tek başına açıklıyor.
- Şartname gerilimine literatürde çözüm **var**: önceden tanımlı karar anı /
  dwell-time switching → **koşullu ama sınırlı teslim**. Senin tasarımın doğru.
- Sıra: **gecikmeyi ölç → φ kapısı (sınırlı bekleme) → ω_T ileri-beslemesi →
  izleme kipi.**

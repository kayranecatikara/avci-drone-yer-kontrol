# GÖRSEL GÜDÜMLÜ ÖNLEYİCİ: bbox'tan kontrol üretme — literatür taraması ve ölçümlerimizle eşleştirme

**Tarih:** 2026-08-17 · **Kapsam:** salt araştırma, kod değişikliği yok
**Yöntem:** arXiv API, Crossref API, Europe PMC API, Semantic Scholar API, açık erişim tam metinler. WebSearch bütçesi tükendiği için genel arama motoru kullanılamadı; DuckDuckGo/Mojeek CAPTCHA/403 verdi. Bu yüzden bazı klasik kitap kuralları (özellikle Zarchan'ın "t_go/τ ≥ 10" kuralı) **doğrulanamadı** ve öyle işaretlendi.
**Kaynak politikası:** her bulgu için yazar + başlık + yayın yeri + yıl + DOI/arXiv no. Bulunamayan yerde **KAYNAK YOK** yazılıdır, uydurulmamıştır.

---

## 0. HÜKÜM ÖZETİ (önce oku)

| # | Soru | Literatürün cevabı | Bizim durumumuza uyar mı | Sayı |
|---|---|---|---|---|
| 1 | IBVS özellik seti | Küresel (bearing) yön + √alan; piksel düzlemi kenarda bozuluyor | **Kısmen zaten yapıyoruz**; λ̇ hâlâ skaler azimutta | Kadraj kenarında dönme duyarlılığı merkeze göre **4.25×** |
| 2 | Strapdown λ̇ + parazitik döngü | Gövde hızı jiroyla ayrıştırılmalı; ayrıştırma hatası pozitif geri besleme | **Tam uyar — iki arızamız da kanonik parazitik döngü** | Piksel köprüsü 42.9°→70.9°; ayna işareti −0.86 eğim |
| 3 | Yasa seçimi (manevra bilinmiyor) | **Karma PN+PP** (düşük kazançlı), yakın takip için | **Uyar; DPP'miz yapı olarak aynı** | Şahin: N=0.7, K=1.2 s⁻¹, τ=0.09 s — bizim FF=1.0, k=1.4 s⁻¹, τ=0.375 s |
| 4 | Terminal nişan | Kasıtlı kayma ancak **açı kısıtı** olarak korunur; konum ofseti t_go ile sıfırlanmalı | Rampamız doğru formda ama **vekil menzil yüzünden CPA'da sıfırlanmıyor** | 4 m gerçekte k=0.50 (tasarım 0.33) |
| 5 | Algı sürekliliği | Düşük eşikli adayı ATMA, izleyiciyle doğrula; dilimli/ROI çıkarım | **Uyar ve kendi ölçümümüzle örtüşüyor** | conf hizalama ≥5 s epizod 43→57 (+%32.6); SAHI +5-7 AP |
| 6 | Gecikme telafisi | Kestirimci **filtre tarafında** işe yarar, **girdi tarafında** kararsızlık getirir | **Uyar — ölçümümüz literatürle çelişmiyor** | Bizde D=0.05 s en iyi (2.32°), D=0.25 → 5.42° |
| 7 | Benzer sistemler | Metre-altı ıska var ama **hep ≤8 m/s veya LiDAR/stereo ile** | Bizimki mono-bbox + 22-24 m/s → **sınıfında rakipsiz zor** | Normalize edilmiş ıskamız en iyinin 1.6-3.8 katı |
| 8 | Biyolojik önleyiciler | Yakın menzil + yüksek λ̇ → **DÜŞÜK N**; strapdown fovea; gecikme telafi edilmiyor | **Bizim rejimimizin tam eşi** | Coenosia N≈1.5 / 18 ms; Holcocephala N≈3 / 28 ms |

**Raporun tek cümlelik sonucu:** Literatürün bize söylediği en büyük şey bir yasa değil, bir **kimlik** — biz füze değil, quadrotor'uz. Füzede yanal ivme hıza bağlıdır (a ∝ V²), quadrotor'da sabittir (a = 12 m/s²). Bu yüzden füze/şahin için "hızlan" olan çözüm bizde **"yavaşla"**dır ve ölçülen %54.1'lik dönüş doygunluğumuzun tamamı bu tek değişkenle kapanabilir. Bu, depoda yazılı ama **hiç ölçülmemiş** M1 (dönüş bütçesi) yamasıdır.

---

## SORU 1 — IBVS: interaction matrix, underactuation, bbox için en iyi koşullanmış özellik seti

### (a) Literatürün dediği

**Klasik çekirdek.** IBVS'in temel denklemi `ṡ = L_s · v`; `L_s` (interaction matrix / image Jacobian) bir nokta özellik için 2×6'dır ve derinlik `Z`'yi içerir. Normalize görüntü koordinatı `x = X/Z`, `y = Y/Z` için satır:

```
L_x = [ −1/Z ,  0 ,  x/Z ,   x·y  , −(1+x²) ,  y ]
L_y = [  0 , −1/Z ,  y/Z , (1+y²) ,  −x·y   , −x ]
```

Buradaki **`−(1+x²)`** terimi bu raporun en önemli sayısal kaldıracıdır: kameranın dönmesinin görüntü üzerindeki etkisi eksenden uzaklaştıkça **kuadratik** büyür. Öteleme terimleri (`1/Z`) ise sabit kalır. Yani hedef kadraj kenarına yaklaştıkça, ölçülen piksel hareketinin **giderek daha büyük kısmı hedefin hareketi değil bizim kendi dönüşümüzdür**.

**Underactuated (quadrotor) uyarlaması.** Quadrotor 6 serbestlik derecesinden yalnız 4'ünü doğrudan sürer (itki + 3 tork). Yanal yer değiştirme ancak **yatırarak** olur, yatırma ise kamerayı döndürür — yani kontrol eyleminin kendisi görüntü özelliğini bozar. Literatürün üç ana cevabı:

1. **Sanal / seviyelenmiş görüntü düzlemi (de-rotation).** Ölçülen özelliği IMU'dan gelen roll/pitch ile yatay bir sanal çerçeveye döndür. Bu, `L_s`'nin dönme sütunlarını komuttan ayırır.
2. **Küresel izdüşüm (spherical projection).** Özelliği piksel yerine birim küre üzerinde bir yön vektörü `n` olarak tut. Küre üzerinde dönme etkileşimi `−[n]×`'dir; bu matrisin normu **her yerde 1**'dir — `1+x²` patlaması yoktur. Hamel & Mahony ailesi bunun üzerine pasiflik-benzeri kararlılık kurar.
3. **Moment tabanlı özellikler.** Görüntü momentleri, etkileşim matrisini mümkün olduğunca **köşegenleştirecek** şekilde seçilir. Chaumette'in sonucu: alan momenti `m00` derinliğin doğal değişmezidir (derinlik ∝ 1/√alan), merkezi momentler yön, ikinci derece oranlar yönelim taşır.

**Bbox'a indirgeme.** Bir bbox'tan çıkarılabilen momentler tam olarak üç tanedir: merkez `(cx, cy)`, alan `w·h`, ve en-boy oranı `w/h`. Moment teorisinin verdiği en iyi koşullanmış üçlü:

| Ölçü | Doğru form | Ne taşır | Neden |
|---|---|---|---|
| Yön | `n = normalize(K⁻¹[cx, cy, 1])` (birim küre) | kerteriz | dönme etkileşimi her yerde birim normlu |
| Ölçek | `√(w·h)` | menzil vekili | moment-teorik derinlik değişmezi (derinlik ∝ 1/√alan) |
| Yönelim | `w/h` | hedefin aspect'i | ikinci derece oran; **menzil için KULLANILMAMALI** |

### (b) Kaynaklar

- B. Espiau, F. Chaumette, P. Rives, "A new approach to visual servoing in robotics", *IEEE Transactions on Robotics and Automation*, 1992. DOI: 10.1109/70.143350
- F. Chaumette, S. Hutchinson, "Visual servo control. I. Basic approaches", *IEEE Robotics & Automation Magazine*, 2006. DOI: 10.1109/MRA.2006.250573
- F. Chaumette, S. Hutchinson, "Visual servo control. II. Advanced approaches", *IEEE Robotics & Automation Magazine*, 2007. DOI: 10.1109/MRA.2007.339609
- F. Chaumette, "Image Moments: A General and Useful Set of Features for Visual Servoing", *IEEE Transactions on Robotics*, 2004. DOI: 10.1109/TRO.2004.829463
- O. Tahri, F. Chaumette, "Point-based and region-based image moments for visual servoing of planar objects", *IEEE Transactions on Robotics*, 2005. DOI: 10.1109/TRO.2005.853500
- R. Mahony, T. Hamel, "Image-based visual servo control of aerial robotic systems using linear image features", *IEEE Transactions on Robotics*, 2005. DOI: 10.1109/TRO.2004.835446
- T. Hamel, R. Mahony, "Image based visual servo control for a class of aerial robotic systems", *Automatica*, 2007. DOI: 10.1016/j.automatica.2007.03.030
- O. Bourquardez, R. Mahony, N. Guenard, F. Chaumette, T. Hamel, L. Eck, "Image-Based Visual Servo Control of the Translation Kinematics of a Quadrotor Aerial Vehicle", *IEEE Transactions on Robotics*, 2009. DOI: 10.1109/TRO.2009.2011419
- O. Bourquardez et al., "Stability and performance of image based visual servo control using first order spherical image moments", *IROS 2006*. DOI: 10.1109/IROS.2006.281963
- P. Corke, "Spherical image-based visual servo and structure estimation", *ICRA 2010*. DOI: 10.1109/ROBOT.2010.5509199
- C. Qin, H. H. T. Liu, "PCVPC: Perception Constrained Visual Predictive Control For Agile Quadrotors", arXiv:2109.11063, 2021 — *"parameterizes features using bearing vectors to avoid depth sensitivity during intense orientation changes"*
- C. Qin, Q. Yu, H. H. T. Liu, "Model Predictive Spherical Image-Based Visual Servoing On SO(3) for Aggressive Aerial Tracking", arXiv:2212.09613, 2022 — küresel özelliğin **tekillikten arınık** olduğu ve büyük dönmelerde görünürlük için "attitude-compensation" gerektiği
- Z. Tang, R. Cunha, D. Cabecinhas, T. Hamel, C. Silvestre, "Quadrotor going through a window and landing: An image-based visual servo control approach", arXiv:2110.06328, 2021 — küresel görüntü ölçümlerinden merkez vektörleri
- E. Malis, P. Rives, "Robustness of image-based visual servoing with respect to depth distribution errors", *ICRA 2003*. DOI: 10.1109/ROBOT.2003.1241732
- Y. Zhang, Z. Ning, S. Zhao, "Observability-Enhanced Target Motion Estimation via Bearing-Box: Theory and MAV Applications", *IEEE Transactions on Robotics*, 2026. DOI: 10.1109/TRO.2026.3661714 — *"Unlike existing methods that rely on restrictive assumptions, such as isotropic target shape and lateral motion, our bearing-box estimator can estimate both the target's motion and its physical size"*

### (c) Bizim ölçümümüzle kıyas

**1. Kadraj kenarındaki dönme duyarlılığı — ölçümümüzü açıklıyor.**
`1+x²` faktörünü bizim sayılarımızla hesapladım (`x = tan(kerteriz)`):

| Kerteriz | `x = tan` | `1+x²` | Merkeze göre | Bizde ne oluyor |
|---|---|---|---|---|
| 0° (merkez) | 0.000 | 1.000 | 1.00× | tespit kaybı **0.036** |
| 39° | 0.810 | 1.656 | 1.66× | bu eşiğin ötesinde tespit kaybı **0.609** |
| 52° (ölüm anı medyanı) | 1.280 | 2.638 | **2.64×** | fazların %64.7'si burada ölüyor |
| 61° (kadraj sınırı) | 1.804 | 4.255 | **4.25×** | — |

Yani: fazlarımızın %64.7'si hedef **hâlâ kadrajın içindeyken** ölüyor ve ölüm anındaki medyan kerteriz 52°. O noktada ölçtüğümüz piksel hareketinin gövde dönüşüne duyarlılığı merkeze göre 2.64 kat. Bu, ölçülen **λ̇ şişmesinin (5.9-7.1×)** doğrudan yapısal açıklamasıdır ve `DURUM_2026-08-16.md`'deki ayrıştırmayla (kutu gecikmesi 6.3×, donuk yaw 5.0×, kenar yanlılığı 1.6×) tutarlıdır — "kenar yanlılığı 1.6×" kalemi tam olarak bu terimdir ve ölçümü 39° eşiğine göre yapılmış; 52°'de gerçek katkı 2.64×'tir.

**2. Zaten doğru yaptıklarımız.**
- `los_seviye(cx, cy, roll, pitch)` (`bbox_ibvs.py:1074-1106`, `ROLL_TELAFI=1`) tam olarak literatürün **sanal görüntü düzlemi** çözümüdür. Ölçülen kazanç: yatış 20-29° bandında hata 11.0°, 30-39° bandında 13.9° düzeltiliyor.
- `eps_yaw = atan((cx−CX)/FX)` piksel değil **açı** — bu zaten küresel parametreleştirmenin skaler halidir. Piksel ile çalışsaydık `1+x²` bozulmasını komutun içinde taşıyorduk.
- `boyut = sqrt(w·h)` (`bbox_ibvs.py:1171`) hız yasasında kullanılıyor — moment-teorik olarak **doğru** değişmez.

**3. Yanlış yaptığımız üç şey.**

- **(i) Menzil vekili `max(w,h)` kullanıyor.** `menzil × max(w,h) = 232.9 px·m` (yasa çerçevesi; DoW'da 743 px·m, `algi_sureklilik.py:51-58`). `max(w,h)` bir moment değişmezi **değildir** ve aspect'e bağlıdır. Ölçülen bedeli zaten depoda var: vekil/truth medyan **1.41** (n=8151), 3-6 m'de **2.13×**. Depo daha iyi bir model de ölçmüş: `R = F·0.856/(w^0.15·h^0.85)` → medyan hata %21 → **%6.2** (`bbox_ibvs.py:680-688`). Üs takımının (0.15, 0.85) neredeyse "yalnız h" demeye gelmesi tesadüf değil: veri tümüyle kuyruk takibi (aspect 138-166°), o geometride **w aspect'e göre değişir, h değişmez**. Zhang ve ark. (T-RO 2026) bunun tam adını koyuyor — mevcut yöntemler *isotropic target shape* varsayar, bearing-box bu varsayımı kaldırır ve hedefin fiziksel boyutunu birlikte kestirir.

- **(ii) λ̇ skaler azimutta hesaplanıyor.** `los_az = iyaw_lam + eps_seviye`, sonra en küçük kareler (`PN_PENCERE_S = 0.25 s`). Skaler azimut, yükselişte kazanç bozulması taşır (küresel koordinatta `dλ_az` gerçek açısal hıza `cos(elev)` ile ölçeklenir). Bizim kamera **+25° yukarı vidalı**, gövde pitch trimi −14.5° → etkin +11.7°; ama uçuşta ölçülen `iris_pitch` medyanı **−17.6°** (`bbox_ibvs.py:924-940`), yani hedef sık sık kayda değer yükseliş açısında. `cos` düzeltmesi olmadan azimut λ̇'sı sistematik olarak şişer. Doğrusu 3B birim vektör üzerinden: `ω_LOS = n × ṅ`, her yerde eşit koşullanmış.

- **(iii) Kutu-menzil vekili ile terminal kapı arasında sabit uyuşmazlığı var.** `MENZIL_PX_M = 202.6` (`bbox_ibvs.py:688`) ama terminal nişan kapısı hâlâ `160.0` kullanıyor (`bbox_ibvs.py:1938`). Kapı menzili **%21 küçük** hesaplıyor → `_yanal = _men·|tan(eps)|` de %21 küçük → 2.0 m eşiği fiilen ~2.53 m gibi davranıyor. Bu bir deney değil, bir tutarsızlık.

### (d) Somut öneri ve beklenen kazanç

| Öneri | Ne | Beklenen kazanç (sayıyla) |
|---|---|---|
| **Ö-1.1** | λ̇'yı 3B birim kerteriz vektöründen hesapla (`ω = n × ṅ`) | Yükseliş kaynaklı λ̇ şişmesi kalkar. Ölçülen toplam şişme 5.9×; `cos(elev)` teriminin payı elev=17.6° için 1/cos = **1.049** (küçük), ama elev p90'da (~35°) **1.22**. Küçük ama bedava. |
| **Ö-1.2** | Menzil vekilini `h`-ağırlıklı modele geçir (`w^0.15·h^0.85`) | Depo ölçümü: medyan hata **%21 → %6.2**. Terminal kapı, kapanma kestirimi ve TERM_DIKEY rampası aynı anda düzelir. |
| **Ö-1.3** | `160.0` → `MENZIL_PX_M` tutarlılığı (`bbox_ibvs.py:1938`) | Terminal nişan kapısı tasarlandığı sıkılıkta çalışır (fiilen 2.53 → 2.0 m). |
| **Ö-1.4** | Kerteriz > 39° olan karelerde λ̇ ağırlığını düşür (kenar güvensizliği) | Kenarda dönme duyarlılığı 1.66-4.25×; bu karelerde λ̇ zaten çoğunlukla kendi hareketimiz. |

### (e) Riskler / çürütme

- **Ö-1.2 tek değişken kuralını zorlar:** `MENZIL_PX_M`'i değiştirmek terminal mandalını (`boyut ≥ 25 px`), kapanma kestirimini ve TERM_DIKEY rampasını **aynı anda** kaydırır. Depo bunu zaten farkında (`bbox_ibvs.py:961-966`: *"tek-değişken kuralı gereği AYRI bir iş"*). Doğru yol: modeli bir bayrağın arkasına al, kapıları eski sabitle besleyen bir uyum katmanı bırak.
- **Ö-1.4 çürütülebilir:** depo `KADRAJ_ESIK_DEG = 0` bırakmış çünkü "kayıp sıçraması 39°, kadraj sınırı 61°". Kenar karelerini tamamen atmak sürekliliği daha da kısaltır — bu yüzden **atma değil ağırlık düşürme** öneriyorum.
- **Küresel λ̇'nın bize çok şey kazandırmayabileceği** dürüst ihtimali: ölçülen şişmenin baskın kaynağı kutu gecikmesi (6.3×) ve donuk yaw (5.0×); geometri düzeltmesi bunların yanında küçük kalır.

---

## SORU 2 — Strapdown seeker: λ̇ rekonstrüksiyonu, parazitik döngü, gövde hareketinin ayrıştırılması

### (a) Literatürün dediği

**Temel denklem.** Gövdeye sabit (strapdown) bir arayıcı **atalet** kerterizini değil, **gövdeye göre bakış açısını** ölçer. Atalet LOS açısı:

```
λ(t) = ψ_gövde(t) + ε(t)          (ε = kadraj içi bakış açısı)
λ̇(t) = ψ̇_gövde(t) + ε̇(t)
```

Yani λ̇ elde etmek için **jiro hızını eklemek zorunludur**. Bu literatürde "LOS rate reconstruction" adıyla geçer.

**Parazitik döngü (parasitic loop).** Zincir şudur: güdüm komutu → gövde döner → gövde dönüşü arayıcı çıktısında görünür → ayrıştırma kusurluysa artık sinyal güdüm komutuna geri döner. Kusur kaynakları: ölçek çarpanı hatası (scale factor), radome kırılması, montaj hizasızlığı, jiro gecikmesi ve **işaret hatası**. Literatür bu döngünün pozitif ya da negatif geri besleme olabildiğini ve güdüm sisteminin kararlılık bölgesini doğrudan daralttığını gösteriyor.

**Kazanç–gecikme sınırı.** Güdüm halkası kabaca bir integratör + saf gecikmedir; `L(s) = k·e^{−τs}/s` için faz payı `PM = 90° − k·τ·(180/π)`. Arayıcı gecikmesi ve otopilot kutbu bu paydan doğrudan yer.

### (b) Kaynaklar

- F. Nesline, P. Zarchan, "Line of sight reconstruction for faster homing guidance", *AIAA Guidance and Control Conference*, 1983. DOI: 10.2514/6.1983-2170
- F. Nesline, P. Zarchan, "Digital homing guidance — Stability vs. performance trade-offs", *AIAA Guidance and Control Conference*, 1983. DOI: 10.2514/6.1983-2167
- F. W. Nesline, P. Zarchan, "A New Look at Classical vs Modern Homing Missile Guidance", *Journal of Guidance and Control*, 4(1):78-85, 1981. DOI: 10.2514/3.56054
- Y. Du, "Study on stability of strapdown seeker scale factor error parasitical loop", *ICCMCEE 2010*. DOI: 10.1109/CMCE.2010.5609905
- S. Jianmei, "Stability region analysis of the parasitic loop of the semi-strapdown homing seeker", *Proc. IMechE Part I: Journal of Systems and Control Engineering*, 2011. DOI: 10.1177/0959651811421710
- J.-H. Hong, "Compensation of Parasitic Effect in Homing Loop with Strapdown Seeker via PID Control", *ICINCO 2014*. DOI: 10.5220/0005055907110717
- J.-H. Hong, "Homing Loop Design for Missiles with Strapdown Seeker", *Journal of the Korean Society for Aeronautical & Space Sciences*, 2014. DOI: 10.5139/JKSAS.2014.42.4.317
- L. Yue, "Influence of roll-pitch seeker DRR and parasitic loop on Lyapunov stability of guidance system", *Journal of Systems Engineering and Electronics*, 2021. DOI: 10.23919/JSEE.2021.000127
- B. Xiao, "Research on the Influence of the Parasitic Loop of the Roll-Pitch Seeker on the Stability of the Guidance System", *Journal of Physics: Conference Series* 2508:012023, 2023. DOI: 10.1088/1742-6596/2508/1/012023 — kaynak: *"the scale deviation between the detector, the frame angle sensor and the angular rate gyroscope"*; *"the positive and negative feedback characteristics of the disturbance rejection rate parasitic loop have a great influence on the stability of the guidance system"*
- C. Wang, "A hardware-in-the-loop simulation for LOS rate estimation of strapdown seeker based on EKF", *ICARCV 2016*. DOI: 10.1109/ICARCV.2016.7838644
- J. M. Maley, "Line of Sight Rate Estimation for Guided Projectiles with Strapdown Seekers", *AIAA GNC 2015*. DOI: 10.2514/6.2015-0344
- R. Evduzen, "Strapdown Seeker Line-of-Sight Rate Estimation via Pixel-Plane Kalman Filtering and Gyro Fusion", engrXiv preprint, 2026. DOI: 10.31224/7642 — piksel düzleminde sabit-hız KF, sonra **rigid-body transport theorem** ile jiro füzyonu. Ölçülen: gürültüsüz 3.13×10⁻⁴ °/s RMS, gerçekçi gürültüde **0.899 ± 0.028 °/s RMS**, kapalı çevrim **1.71 m ıska**.
- Y. Bai, "Miss Distance Error Analysis of Strapdown Seeker Imaging System", *Advanced Materials Research*, 2013. DOI: 10.4028/www.scientific.net/AMR.753-755.1976

### (c) Bizim ölçümümüzle kıyas — **bu raporun en güçlü eşleşmesi**

Depomuzun iki büyük arızası, ders kitabındaki parazitik döngü arızasının **birebir iki farklı biçimidir**:

**Arıza 1 — PİKSEL KÖPRÜSÜ (ölçek/model hatası biçimi).**
`bbox_ibvs.py:317-331`. Kutu yokken piksel hızıyla ekstrapolasyon yapıldı. Ölçülen sonuç:

| Köprü | Tüm karelerde yön hatası | **Görürken bile** |
|---|---|---|
| kapalı | 42.9° | 8.2° |
| 0.30 s | 54.8° | 15.0° |
| 0.60 s | **70.9°** | **25.7°** |

Deponun kendi teşhisi (`bbox_ibvs.py:322-331`): *"piksel hızı bizim kendi burun dönüşümüzü içeriyor → PARAZİTİK DÖNGÜ"*. Bu, literatürdeki tanımın **kelimesi kelimesine** aynısıdır: gövde hızı ayrıştırılmamış strapdown çıktısı komuta geri besleniyor. Kritik detay — **tespit olan karelerde de bozuluyor** (8.2° → 25.7°): bu, arızanın "kör dönemde ekstrapolasyon kötü" olmadığının, döngünün kendisinin bozulduğunun kanıtıdır. Literatür bunu tam olarak öngörür: parazitik döngü sistemin kutuplarını kaydırır, yalnız kör aralıkları değil.

**Arıza 2 — AYNA (işaret hatası biçimi).**
`kopru/tespit_akisi.py:124-150`. `dow_kopru.py:49-53` dünyayı aynalıyor (`NED_y = −DoW_y`, `yaw_NED = −yaw_DoW`) ama kamera aynalanmıyordu. Sonuç: her karede burun `2·ε` **ters** yöne sürüldü. Ölçülen imza:

- ε → 0.5 s sonraki yaw değişimi eğimi: **−0.863 / −0.902** (iki bağımsız ölçüm)
- Aynı işaret oranı yalnız **%10.2 / %8.6**
- `|Δyaw − yaw_cmd|` medyan **107.6°** vs `|Δyaw + yaw_cmd|` medyan **10.2°**
- `|ε|` faz boyunca 10° → **45.8°**, hedef **1.91 s**'de kadrajdan çıkıyor, komut karelerinin **%62.7'si hayalet**

Bu, ayrıştırma katsayısının **−1** olduğu durumdur; literatürdeki "disturbance rejection rate parasitic loop" analizinde en kötü pozitif geri besleme noktası. Düzeltme sonrası CPA yatay **4.44 → 2.17 m**.

**Arıza 3 (çözüm tarafı) — ATALET KÖPRÜSÜ = doğru rekonstrüksiyon.**
`KOR_KOPRU_ATALET_S = 1.5 s` (`bbox_ibvs.py:359`, `:1672-1682`):

```
son tespitte:  los_son = iris_yaw + ε
kör karede :  ε_köprü = normalize(los_son − iris_yaw(ŞİMDİ))
```

Bu, tam olarak `λ = ψ_gövde + ε` denkleminin **sıfırıncı dereceden atalet tutucusudur**: atalet LOS'u dondur, gövde dönüşünü şimdiki yaw ile geri çıkar. Ölçülen kazanç deponun en büyük tekil kazancı:

| Kol | Faz sayısı | Ömür | Iska |
|---|---|---|---|
| kapalı (C0) | 14 | 1.97 s | **12.12 m** |
| **ATALET 1.5 s** | 13 | **3.92 s** | **2.81 m** |
| kapalı (C2) | 14 | 1.95 s | 12.40 m |

İki bağımsız kontrol referansı 0.28 m ile örtüşüyor → ölçüm güçlü. Mekanizma: LOS dönüş hızı **40 → 6 °/s**. Bu, Evduzen (2026) ve Maley (2015)'in yaptığının basitleştirilmiş halidir; onlar KF + jiro füzyonu ile 0.899 °/s RMS'e iniyor, biz sıfırıncı derece tutucuyla 40→6 °/s.

**Kazanç–gecikme: deponun türetmesi eksik.**
`bbox_ibvs.py:385-394`:
```
L(s) = k·e^{−τs}/s → PM = 90° − k·τ·(180/π)
τ_eff = 0.375 s (250 ms hat + 4 FPS yarım örnek)
k = 1.4 → PM = 60°;  k = 2.0 → PM = 47°
```
Bu türetme aracı **saf integratör** kabul ediyor. Ama ölçülen bir de **yaw takip gecikmesi 0.28 s** var (birinci derece kutup). Kesim frekansı `ω_c ≈ k`:

| k | Gecikme fazı `k·τ` | Yaw kutbu fazı `atan(k·0.28)` | **Gerçek PM** |
|---|---|---|---|
| 1.4 | 30.1° | 21.4° | **38.5°** |
| 1.2 | 25.8° | 18.6° | 45.6° |
| **1.0** | 21.5° | 15.6° | **52.9°** |
| 0.9 | 19.3° | 14.1° | 56.6° |

Yani **deponun "PM = 60°" değeri iyimser; ölçülen yaw kutbu hesaba katılınca 38.5°.** 38.5° faz payı hâlâ kararlıdır ama aşımlı/salınımlıdır — ve depoda ölçülen "%54.1 doygunluk" bunun üstüne biner. Doygunluk altında etkin kazanç düşer ve faz gecikmesi artar; bu klasik oran-sınırlayıcı kaynaklı salınım mekanizmasıdır. *(Bu son cümlenin describing-function niceliği için erişebildiğim kaynaklarda somut sayı bulamadım → **KAYNAK YOK**; ama bizim doygunluk oranımız ölçülü: talep medyanı 39.4 °/s vs tavan 31.8 °/s, karelerin %54.1'i doygun.)*

### (d) Somut öneri ve beklenen kazanç

| Öneri | Ne | Beklenen kazanç |
|---|---|---|
| **Ö-2.1** | `AVCI_DPP_K` 1.4 → 1.0 | Faz payı 38.5° → **52.9°**. Talebin σ kaynaklı kısmı (%28 × 39.4 = 11.0 °/s) → 7.9 °/s; toplam talep 39.4 → **36.3 °/s** |
| **Ö-2.2** | Atalet köprüsünü **jiro-füzyonlu birinci dereceye** yükselt: dondurulmuş λ yerine `λ(t) = λ_son + λ̇_son·(t − t_son)` (λ̇ kırpması dar) | Evduzen 2026 ile analoji. **Ama riskli** — bkz. (e) |
| **Ö-2.3** | Köprü süresini yapısal kapıya oturt: `KOR_KOPRU_ATALET 1.5 → 1.8 s` | Yapısal kapı `KAYIP_M/31 Hz = 1.9 s`; 1.5 s bu kapının altında kalıyor, yani faz köprü bitmeden ölmüyor ama köprü faz bitmeden bitiyor |
| **Ö-2.4** | Ayna/işaret için **kalıcı bekçi**: her koşuda `|Δyaw − yaw_cmd|` vs `|Δyaw + yaw_cmd|` medyanlarını logla ve eşitsizlik terse dönerse koşuyu geçersiz say | Bu ayna hatasının **üçüncü tekrarı** olduğu depoda yazılı. Ölçüm maliyeti sıfır, yakalama gücü mutlak (107.6° vs 10.2°) |

### (e) Riskler / çürütme

- **Ö-2.2 muhtemelen zehirlidir ve öncelik listesine ALINMAMALI.** Deponun ölçümü net: λ̇ tahminimiz **5.9-7.1× şişik**. Şişik bir λ̇ ile birinci derece ekstrapolasyon yapmak, piksel köprüsünün yaptığı hatanın atalet çerçevesindeki eşdeğeridir. 1.5 s × 6× şişik λ̇ → devasa açı hatası. Sıfırıncı derece tutucunun 1.5 s dayanmasının sebebi tam olarak **hiçbir şey ekstrapole etmemesi**. Bunu ancak λ̇ şişmesi bağımsız olarak <1.5×'e indirildikten sonra denemek gerekir.
- **Ö-2.1 ile Soru 3'teki Ö-3.1 (FF düşürme) aynı anda denenemez** — tek değişken kuralı. İkisi de doygunluğa saldırıyor; hangisinin daha etkili olduğu λ̇ payının %72 olmasından belli: **önce FF**.
- **Ö-2.3 için karşı-ölçüm var:** OC-SORT'un uyarısı (Soru 5) uzun ölü hesabın hata biriktirdiği yönünde. 1.8 s'de hedefin medyan dönüşü (6.55 °/s) 11.8° birikir — kabul edilebilir; ama p90 dönüşünde (32.0 °/s) **57.6°** birikir ve bu kadraj sınırının (61°) tamamına yakınıdır. Yani dönüş rejiminde 1.8 s köprü hedefi kadrajın dışına "hayali olarak" taşır. Doğru form: **dönüş hızına bağlı köprü süresi** — `T_köprü = min(1.8 s, 30° / |ω_hedef_tahmini|)`.

---

## SORU 3 — Güdüm yasaları: PN / APN / OGL / DPP / ZEM-t_go, μ<1 yakalanabilirlik, N seçimi

### (a) Literatürün dediği

**PN ailesi.** `a_c = N · V_c · λ̇` (true PN) veya `ψ̇_v = N · λ̇` (kinematik/oran biçimi). Kinematik biçim **V_c gerektirmez** — kapanma hızı ölçemeyen sistemler için tek uygulanabilir biçimdir. Bu "yalnız LOS-hızı ölçümlü" aile literatürde ayrı bir dal.

**APN.** `a_c = N·V_c·λ̇ + (N/2)·a_T`. Hedef ivmesi `a_T` **bilinmesini** gerektirir. Ghosh & Ghose'un yakalanabilirlik analizleri APN'nin zamanla değişen hedef manevralarına karşı üstünlüğünü gösteriyor — **ama `a_T` biliniyorsa.** Kerteriz-tek ölçümde hedef manevrası gözlemlenebilir değildir (Nardone & Aidala 1980; Hepner & Geering 1987/1990: menzil ve manevra, gözlemci manevra etmedikçe gözlemlenemez).

**DPP (deviated pure pursuit).** Hız vektörünü LOS'tan **sabit bir sapma açısı** `σ_c` kadar önde tut. Bu, sabit-kerteriz (parallel navigation) geometrisinin açık-döngü yaklaşımıdır. Aktif literatür dalı: darbe-zamanı/darbe-açısı kısıtlı güdüm.

**Karma PN + PP.** Biyolojiden gelen ve bizim rejimimiz için literatürün **en net cevabı**:
```
γ̇(t) = N·λ̇(t−τ) − K·δ(t−τ)
```
`δ` = hız vektörü ile LOS arasındaki sapma açısı. Brighton & Taylor'ın (2019) gerekçesi doğrudan bize yazılmış gibi: *"This classical guidance law [PN] works well in the open, but performs sub-optimally against highly-manoeuvrable targets... Harris' Hawks use a mixed guidance law, coupling low-gain proportional navigation with a low-gain proportional pursuit element. This guidance law promotes tail-chasing and is not thrown off by erratic manoeuvres."*

**N seçimi ve gecikmeyle etkileşimi.** Füzeler `3 ≤ N ≤ 5`. Biyoloji sistematik olarak daha düşük N kullanıyor ve sebebi açıkça yazılmış (Fabian ve ark. 2018): açık gökyüzünde uzun menzilli avlanan sinek `N ≈ 3` / 28 ms gecikme; **yakın menzilde, çok yüksek LOS dönüş hızlarıyla** avlanan sinek `N ≈ 1.5` / 18 ms ve düşük N *"may allow Coenosia to cope with the extremely high line-of-sight rotation rates, which are due to close target proximity, and thus prevent overcompensation of steering."*

**ZEM/t_go.** Amaç `ZEM(t_f) = 0`. He, Su & Su (2026) "nonadvantageous engagements" — yani savunucunun hızda veya manevrada **belirgin üstünlüğü olmadığı** durumlar — için ZEM ve ZEAE'yi birlikte sıfıra süren kapalı-form yasa veriyor ve klasik PN'ye göre **kontrol eforunu ve tepe ivmeyi düşürdüğünü** bildiriyor.

### (b) Kaynaklar

- C. H. Brighton, A. L. R. Thomas, G. K. Taylor, "Terminal attack trajectories of peregrine falcons are described by the proportional navigation guidance law of missiles", *PNAS*, 2017. DOI: 10.1073/pnas.1714532114 — *"Whereas most guided missiles use navigation constants falling on the interval 3 ≤ N ≤ 5, peregrine attack trajectories are best fitted by lower navigation constants (median N < 3). This lower feedback gain is appropriate at the lower flight speed of a biological system, given its presumably higher error and longer delay."*
- C. H. Brighton, G. K. Taylor, "Hawks steer attacks using a guidance system tuned for close pursuit of erratically manoeuvring targets", *Nature Communications* 10:2462, 2019. DOI: 10.1038/s41467-019-10454-z. PMID 31186415, PMC6560099. **Uydurulan parametreler (50 uçuşa global uyum): N = 0.7, K = 1.2 s⁻¹, τ = 0.09 s.** Medyan öngörü hatası: karma **0.34 m** (%95 GA 0.24-0.53) vs saf PP 0.46 m (IQR 0.93-0.26) vs saf PN 0.51 m (IQR 0.96-0.19).
- S. T. Fabian, M. E. Sumner, T. J. Wardill, S. Rossoni, P. T. Gonzalez-Bellido, "Interception by two predatory fly species is explained by a proportional navigation feedback controller", *J. R. Soc. Interface*, 2018. DOI: 10.1098/rsif.2018.0466 — *"Only proportional navigation explains the timing and magnitude of fly steering responses"*; Holcocephala `N ≈ 3` / `≈28 ms`; Coenosia `N ≈ 1.5` / `≈18 ms`
- C. H. Brighton, K. J. Chapman, N. C. Fox, G. K. Taylor, "Attack behaviour in naive gyrfalcons is modelled by the same guidance law as in peregrine falcons", *J. Exp. Biol.*, 2021. DOI: 10.1242/jeb.238493
- P. Gurfil, M. Jodorkovsky, M. Guelman, "Zero-miss-distance guidance law based on line-of-sight rate measurement only", *Control Engineering Practice*, 2003. DOI: 10.1016/S0967-0661(02)00208-3 (konferans sürümü: DOI 10.2514/6.2001-4277)
- Y. Baba, R. Howe, "Suboptimal guidance with line-of-sight rate only measurements", *AIAA GNC 1988*. DOI: 10.2514/6.1988-4066
- S. Ghosh, D. Ghose, S. Raha, "Capturability of Augmented Pure Proportional Navigation Guidance Against Time-Varying Target Maneuvers", *Journal of Guidance, Control, and Dynamics*, 2014. DOI: 10.2514/1.G000561
- S. Ghosh, D. Ghose, S. Raha, "Capturability of Augmented Proportional Navigation (APN) guidance with nonlinear engagement dynamics", *ACC 2013*. DOI: 10.1109/ACC.2013.6579805
- M. Guelman, "The stability of proportional navigation systems", *AIAA GNC 1990*. DOI: 10.2514/6.1990-3380
- N. A. Shneydor, "Pure Pursuit" ve "Proportional Navigation", *Missile Guidance and Pursuit*, Horwood, 1998. DOI: 10.1533/9781782420590.47 ve 10.1533/9781782420590.101
- T. Shima, "Deviated Velocity Pursuit", *AIAA GNC 2007*. DOI: 10.2514/6.2007-6782
- R. Livermore, A. Ratnoo, "Deviated Pure-Pursuit-Based Optimal Guidance Law for Imposing Intercept Time and Angle", *JGCD*, 2018. DOI: 10.2514/1.G003179
- S. R. Kumar, D. Ghose, "Deviated Pursuit Based Interception at A Priori Fixed Time", *JGCD*, 2019. DOI: 10.2514/1.G004284
- S. R. Kumar, "Finite-Time Impact Time Guidance using Deviated Pursuit against Maneuvering Targets", *ACC 2020*. DOI: 10.23919/ACC45564.2020.9147789
- F. He, Y. Su, H. Su, "Zero-Effort-Miss/Zero-Effort-Angle-Error Guidance for UAV Interception in Nonadvantageous Engagements With Terminal Angle Constraint", *IEEE Transactions on Aerospace and Electronic Systems*, 2026. DOI: 10.1109/TAES.2026.3672747
- J. V. Breakwell, "The variable-speed tail-chase aerial combat problem", *JGCD*, 1981. DOI: 10.2514/3.19738
- D. Ghose, "Qualitative Analysis of Variable Speed Proportional Navigation Guidance Law", *AIAA SciTech 2024*. DOI: 10.2514/6.2024-1988
- A. Bhattacharya, "Toward Increased Airspace Safety: Quadrotor Guidance for Targeting Aerial Objects", arXiv:2107.01733, 2021 — *"demonstrate an optimal guidance method implemented on a quadrotor but not usable by missiles"*
- R. Mills, H. Hildenbrandt, G. K. Taylor, C. K. Hemelrijk, "Physics-based simulations of aerial attacks by peregrine falcons reveal that stooping at high speed maximizes catch success", *PLOS Computational Biology*, 2018. DOI: 10.1371/journal.pcbi.1006044

### (c) Bizim ölçümümüzle kıyas

**1. Yapı olarak zaten karma yasadayız — ve kazançlarımız şahininkine çok yakın.**

`bbox_ibvs.py:1287-1337`, DPP kolu:
```
w = k·(σ − σ_c) + FF·λ̇
```
Brighton & Taylor (2019): `γ̇ = N·λ̇(t−τ) − K·δ(t−τ)`

| Terim | Şahin (n=50 uçuş) | **Bizde (reçete)** | Oran |
|---|---|---|---|
| PN kazancı N | **0.7** | `DPP_FF_LAM = 1.0` | 1.43× |
| Takip kazancı K | **1.2 s⁻¹** | `DPP_K_SIGMA = 1.4 s⁻¹` | 1.17× |
| Gecikme τ | **0.09 s** | `τ_eff = 0.375 s` | **4.17×** |
| Boyutsuz `K·τ` | **0.108 rad (6.2°)** | **0.525 rad (30.1°)** | **4.86×** |

Kazançlarımız şahinin kazançlarına şaşırtıcı derecede yakın (1.17× ve 1.43×) — bu, deponun ampirik ayarının bağımsız olarak doğru bölgeye indiğinin güçlü kanıtıdır. **Ama gecikmemiz 4.17 kat** ve kontrol teorisinde önemli olan tek boyutsuz sayı `K·τ` çarpımıdır; oradaki farkımız **4.86 kat**. Yani biz şahinle aynı kazançları, onun dörtte bir kadar sağlam olan bir halkada çalıştırıyoruz.

**2. Coenosia eşleşmesi — rejimimizin tam adı.**
Fabian ve ark. iki sinek türünü ayırıyor: uzak menzil/açık gökyüzü → N≈3; **yakın menzil/çok yüksek λ̇** → N≈1.5, ve sebebi açıkça "aşırı düzeltmeyi önlemek". Bizim rejimimiz:
- Terminal mandal `boyut ≥ 25 px` ≈ **6.4 vekil m ≈ 4.5 gerçek m** → çok yakın menzil
- Ölçülen λ̇ **50-100 °/s** (`GECE_2026-08-17.md §5`)
- `PN_N = 1.6` (`bbox_ibvs.py:383`) ← **Coenosia'nın 1.5'i ile neredeyse aynı**

Depo ayrıca N taramasını yapmış: N ≤ 1.2 uçurum, N ≥ 3 ıraksar, yayla 1.4-1.6. Biyoloji aynı yaylayı bulmuş.

**3. Doygunluk: asıl kısıt burada, ve çözümü N'de değil V'de.**

Ölçülenler:
- İstenen `|w|` medyan **39.4 °/s**, p90 **142 °/s**
- Tavan `ω_max = a_max/V = 12/21.6 = 31.8 °/s`
- **%54.1 doygun** (terminalde %42.5)
- λ̇'nın talep payı **%72**

Ayrıştırma (kendi hesabım, deponun sayılarıyla):
```
λ̇ terimi  : 0.72 × 39.4 = 28.4 °/s  → FF=1.0 olduğu için λ̇_medyan ≈ 28.4 °/s
σ  terimi  : 0.28 × 39.4 = 11.0 °/s  → k=1.4 olduğu için σ_medyan ≈ 7.9°
```

**Kritik gözlem — quadrotor ≠ füze/şahin.** Yanal ivme:
- Şahin/füze: `a = ½ρV²S·C_L/m ∝ V²` → dönüş yarıçapı `r = V²/a = sabit`, dönüş hızı `ω = V/r ∝ V` → **hızlanınca daha hızlı döner**
- Quadrotor: `a = sabit = 12 m/s²` → `r = V²/a ∝ V²`, `ω = a/V ∝ 1/V` → **hızlanınca daha yavaş döner**

Bu, Mills ve ark. (2018) "stooping at high speed maximizes catch success" sonucunun bize **transfer olmadığının** kesin gerekçesidir ve Bhattacharya'nın (2021) "quadrotor'da yapılabilen ama füzede yapılamayan optimal yöntem" cümlesinin tam karşılığıdır.

Bizim `ω_max = 12/V` eğrimiz:

| V (m/s) | ω_max (°/s) | Dönüş yarıçapı r = V²/12 (m) | Medyan talebi (39.4 °/s) karşılar mı |
|---|---|---|---|
| 24 | 28.6 | 48.0 | ✗ (−%27) |
| 21.6 | 31.8 | 38.9 | ✗ (−%19) |
| **17.4** | **39.5** | **25.2** | **✓ tam sınırda** |
| 15 | 45.8 | 18.8 | ✓ (+%16) |
| 14 (DPP_V_MIN) | 49.1 | 16.3 | ✓ (+%25) |

Ve dönüş yarıçapı tarafı: hedefin ölçülen dönüş yarıçapı **27.1 m**, bizim p5'imiz **27.7 m** → hedefin dönüşünün içine giremiyoruz (`GECE_2026-08-17.md §4`). **15 m/s'de yarıçapımız 18.8 m olur — hedefin 27.1 m'sinin belirgin içinde.** Bu, ölçülen "dönüşte kapanma hızı negatif (−0.84 ila −4.33 m/s)" arızasının doğrudan mekanizmasıdır.

**4. Kuyruk takibi bir tuzak — ve ölçümümüz bunu ezici biçimde söylüyor.**

| Aspect @30 m | P(CPA < 3 m) | n |
|---|---|---|
| 60-90° (kesme) | **0.421** | — |
| 150-180° (kuyruk) | **0.005** | **191 denemede 0 vuruş** |

Cliff δ = −0.81 (vuruş aspect medyanı 73.8°, ıska 132.7°). Yani **sonuç 30 m'de belirleniyor**, terminalde değil.

**5. Kesme geometrisinin gerektirdiği öncüleme açısı — kapaklarımız 2-3 kat küçük.**
Sabit kerteriz (collision course) üçgeni: `sin(σ) = μ·sin(aspect)`, μ = 0.833.

| Ölçülen aspect | Gereken lead açısı σ | Bizim tavanımız |
|---|---|---|
| 73.8° (vuruş geometrisi) | **53.1°** | seyir **9°**, terminal **25°** |
| 132.7° (ıska geometrisi) | **37.7°** | seyir **9°**, terminal **25°** |
| 160° (saf kuyruk) | 16.4° | 9° / 25° |

**Seyir tavanı 9° iken kesme geometrisi geometrik olarak imkânsızdır.** Yalnız kuyruk takibi kalır, kuyruk takibi de μ=0.833 ve eşit dönüş yarıçaplarıyla kapanmaz.

**Ama:** depo lead tavanını yükseltmeyi denedi ve **kötü** çıktı (25° tavanda: 8 m içine giriş 4/65 → 2/15 kare, en yakın 2.1 → 13.2/10.0 m; 14° tavanda: en yakın ort. 7.1 → 8.8 m). Sebebi açık: mevcut lead **oran tabanlı** (`lead_az = lead_süre · λ̇`, `LEAD_SURE = 0.4 s`) ve λ̇ **5.9-7.1× şişik**. 0.4 s × 6× şişik λ̇ → tavan sürekli doyuyor (karelerin %27'si tavanda) → araç kesişmek yerine hedefi gölgeliyor. Yani ölçüm "lead kötü" demiyor, **"gürültüyle sürülen lead kötü"** diyor.

**6. APN doğru şekilde reddedilmiş.**
`bbox_ibvs.py:475-481`: `a_T = 19.5 × 0.375 = 7.3 m/s²`, `(N/2)·a_T → +16.3 °/s ek talep`; talep zaten tavanın 9.3 °/s üstünde. Literatür de aynı yöne işaret ediyor: APN'nin kazancı `a_T` bilgisinden gelir, `a_T` ise kerteriz-tek ölçümde gözlemlenebilir değildir (Nardone & Aidala 1980; Hepner & Geering 1990). Ek olarak deponun ikinci gerekçesi de doğru: DPP'de `FF·λ̇` zaten hedef manevrasının kerterize yansımasını taşır → **aynı bilgi iki kez sayılır**.

**7. `N > 1+μ` koşulu.** Depo `GECE_2026-08-17.md §5`'te N=1.6'nın "yakalanabilirlik teoreminin altında (gereken N > 1+μ = 1.833)" olduğunu yazıyor. Erişebildiğim özetlerde **bu tam eşitsizliği doğrulayamadım** → **KAYNAK YOK**. PPN yakalanabilirlik ailesi (Guelman 1990; Ghosh & Ghose 2013/2014) mevcut ama koşulun bu biçimini özetlerden teyit edemedim. Buna karşılık literatürün **ölçülmüş** cevabı şu: yakın menzil/yüksek λ̇ rejiminde gerçek avcılar N≈0.7-1.6 ile **başarıyla** yakalıyor (şahin 0.7, Coenosia 1.5, peregrin <3). Yani teorik alt sınır ihlali pratikte belirleyici görünmüyor; belirleyici olan **doygunluk**.

### (d) Somut öneri ve beklenen kazanç

| Öneri | Ne | Beklenen kazanç (sayıyla) |
|---|---|---|
| **Ö-3.1 (EN YÜKSEK ÖNCELİK)** | **M1 dönüş bütçesi** — `AVCI_IBVS_DONUS_BUTCE = 0.9`, `DONUS_VTABAN = 15`. Kod hazır (`bbox_ibvs.py:1339-1358`), **hiç ölçülmedi** | `V_tavan = 0.9·12/|w_talep|`. Talep 39.4 °/s'de → 15.7 m/s (tabana kırpılır 15). Dönüş yarıçapı 38.9 → **18.8 m**, hedefin 27.1 m'sinin İÇİ. Doygunluk %54.1 → medyanda **0**. Dönüşte kapanma −0.84 m/s → pozitife dönmeli |
| **Ö-3.2** | `AVCI_DPP_FF` 1.0 → **0.7** (Brighton & Taylor'ın uydurduğu N) | Talep 39.4 → **30.9 °/s** (−%21.6); tavanın %24 üstünden **%2.8 altına** iner. `K·τ` 0.525 → değişmez ama λ̇ gürültüsünün komuta geçişi %30 azalır |
| **Ö-3.3** | `AVCI_DPP_SIGMA_C` = **15°** (sabit geometrik bias; oran tabanlı lead'e DOKUNMA) | Aspect@30 m medyanı 132.7° → <110° hedefi. P(CPA<3m) kuyruk bandında 0.005, kesme bandında 0.421 → bant kayması doğrudan **~80× oranında** vuruş olasılığı taşır. Muhafazakâr: gereken 37.7-53.1°'nin üçte biri |
| **Ö-3.4** | `AVCI_DPP_K` 1.4 → 1.0 (Ö-2.1 ile aynı) | Faz payı 38.5° → 52.9° |
| **Ö-3.5** | APN'yi **açma** — literatür ve ölçüm hemfikir | — |

### (e) Riskler / çürütme

- **Ö-3.1'in ana riski:** yavaşlamak μ'yü 1'e iter. 15 m/s'de μ = 17.99/15 = **1.20 > 1** → o an hedeften geri kalırız. Bu yüzden yalnız **yüksek talep anlarında** ve **süre sınırlı** olmalı. Bütçe 0.9 ile kapı ~26 °/s talebin üstünde açılıyor; karelerin ~%54'ünde açılır — bu çok. **Muhafazakâr ilk deneme: bütçe 0.9, taban 18 m/s** (μ = 1.0, en kötü ihtimalle mesafe sabit kalır). 18 m/s'de yarıçap 27.0 m — hedefin 27.1 m'siyle **tam eşit**, yani en azından takip edebiliriz. Sonra 15'e inilebilir.
- **Ö-3.1 ikincil riski:** yavaşlama hız kanalının 0.72-0.93 s tau'suna tabi; komut ile gerçekleşme arasında ~1 s var. Talep 39.4 °/s'yi gördüğümüzde yavaşlamaya başlarsak, hız ancak dönüşün sonunda düşer. **Mekanizma kapısı zorunlu:** logda `v_cmd` ile gerçekleşen `v` arasındaki gecikme ölçülmeli; yavaşlama gerçekleşmiyorsa deney geçersiz.
- **Ö-3.2 çürütülebilir:** FF'i düşürmek λ̇'nın taşıdığı gerçek hedef-manevra bilgisini de kısar. DÜZ segmentteki P(<3 m) = 0.650 **düşmemeli**; düşerse geri al.
- **Ö-3.3 için güçlü karşı-kanıt var:** depo lead tavanını yükseltmeyi ölçtü ve kötü çıktı. Farkım (sabit bias vs oran tabanlı) gerçek ama **kanıtlanmamış bir ayrım**. Bu yüzden Ö-3.3'ü listede aşağıda tutuyorum ve küçük değerle (15°) öneriyorum.
- **Literatür içi çelişki:** Fabian ve ark. (2018) üç yasayı (saf takip, DPP, PN) test edip **yalnız PN'in** sinek verisini açıkladığını söylüyor — yani DPP'yi açıkça **reddediyor**. Brighton & Taylor (2019) ise şahinde karma PN+PP'nin her iki saf yasayı da yendiğini ölçüyor (0.34 m vs 0.46/0.51 m). Bu gerçek bir çelişkidir. Çözümü Brighton'ın kendi açıklamasında: sinekler açık gökyüzünde/uzak menzilde, şahinler yakın menzilde/karmaşık ortamda. **Bizim rejimimiz şahin rejimi** (terminal 4.5 m, λ̇ 50-100 °/s, hedef sabit oval ama bizim açımızdan "erratik"). Yine de bu çelişki, DPP'nin evrensel doğru olmadığının kaydıdır.

---

## SORU 4 — Terminal nişan noktası: kasıtlı kayma ne zaman korunur, ne zaman sıfırlanır

### (a) Literatürün dediği

**Temel kural (ZEM'den):** Güdümün amacı `ZEM(t_f) = 0`'dır. Kasıtlı bir **konum** ofseti, sıfır olmayan bir terminal ZEM talep etmek demektir; bu yüzden ya (i) `t_go` ile ölçeklenerek sıfıra sürülmeli, ya da (ii) hiç konum ofseti olarak değil, bir **terminal açı kısıtı** olarak ifade edilmelidir.

**Korunan biçim: terminal açı kısıtı.** Impact-angle-constrained guidance ailesi, terminal geometriyi (çarpma açısı) korurken ıskayı sıfıra sürer. He, Su & Su (2026) bunu ZEM + ZEAE (zero-effort-angle-error) olarak birleştiriyor ve Lyapunov ile **"convergence of the zero-effort variables to zero as the terminal time is approached"** ispatlıyor. Kim ve ark.'nın (2019) başlığı kuralın kendisidir: *"Guaranteeing Error Convergence **before Interception**"*.

**Sıfırlanan biçim: konum ofseti.** Statik bir nişan kayması, `t_go → 0`'da ıskaya birebir dönüşür. Bu yüzden menzil/`t_go` ile zamanlanmış bir rampa gerekir.

**Görüş alanı kısıtıyla birleşimi.** Strapdown arayıcıda nişan noktası seçimi, hedefi kadrajda tutma kısıtıyla çatışır; literatürde bu iki kısıtı birlikte çözen geniş bir dal var (look-angle constrained guidance).

**"t_go / τ ≥ 10" kuralı.** Zarchan'ın ders kitabındaki bu somut kuralı **erişebildiğim hiçbir kaynakta doğrulayamadım → KAYNAK YOK.** Doğrulayabildiğim şey, güdüm sistemi zaman sabiti ile ıska arasındaki ödünleşimin klasik literatürde Nesline & Zarchan tarafından kurulduğudur (aşağıdaki kaynaklar) ve adjoint tabanlı ıska analizinin standart yöntem olduğudur (Gutman 2011; Goldan & Gutman 2012).

### (b) Kaynaklar

- F. He, Y. Su, H. Su, "Zero-Effort-Miss/Zero-Effort-Angle-Error Guidance for UAV Interception in Nonadvantageous Engagements With Terminal Angle Constraint", *IEEE Trans. Aerospace and Electronic Systems*, 2026. DOI: 10.1109/TAES.2026.3672747
- B. A. White, "Aim point guidance: an extension of proportional navigation to the control of terminal guidance", *American Control Conference 2003*. DOI: 10.1109/ACC.2003.1238978
- J. Kim, "Field-of-View Constrained Impact Angle Control Guidance Guaranteeing Error Convergence before Interception", *AIAA SciTech 2019*. DOI: 10.2514/6.2019-1927
- A. Ratnoo, D. Ghose, "Pure Proportional Navigation for Impact Angle Constrained Interception of Stationary Targets", *AIAA GNC 2008*. DOI: 10.2514/6.2008-7306
- A. Ratnoo, "Satisfying Terminal Angular Constraint Using Proportional Navigation", *AIAA GNC 2009*. DOI: 10.2514/6.2009-6088
- H.-G. Kim, "Look-Angle-Shaping Guidance Law for Impact Angle and Time Control With Field-of-View Constraint", *IEEE Trans. Aerospace and Electronic Systems*, 2020. DOI: 10.1109/TAES.2019.2924175
- S. He, "A robust impact angle constraint guidance law with seeker's field-of-view limit", *Trans. Institute of Measurement and Control*, 2014. DOI: 10.1177/0142331214538278
- F. W. Nesline, P. Zarchan, "A New Look at Classical vs Modern Homing Missile Guidance", *J. Guidance and Control* 4(1):78-85, 1981. DOI: 10.2514/3.56054
- F. Nesline, "Miss distance dynamics in homing missiles", *AIAA 1984*. DOI: 10.2514/6.1984-1844
- S. Gutman, "Adjoint Stability and Miss-Distance in Proportional Navigation", *AIAA GNC 2011*. DOI: 10.2514/6.2011-6417 · O. Goldan, S. Gutman, *JGCD*, 2012. DOI: 10.2514/1.56143
- M.-J. Tahk, C.-K. Ryoo, H. Cho, "Recursive time-to-go estimation for homing guidance missiles", *IEEE Trans. Aerospace and Electronic Systems*, 2002. DOI: 10.1109/7.993225

### (c) Bizim ölçümümüzle kıyas

**1. Rampamızın formu literatüre uygun — ama vekil menzil onu CPA'da bozuyor.**

`bbox_ibvs.py:919-968`, `nisan_cy()`:
```
W0 = piksel_elev(CY_NISAN) + iris_pitch      # nişanın dünya yükselişi
k  = clamp(menzil / TERM_DIKEY_M, 0, 1)
cy = elev_piksel(W0·k − iris_pitch)
```
Bu tam olarak "ofseti menzille sıfıra ramp et" kuralıdır — doğru form. **Ama `menzil` burada kutu vekilidir ve vekil 3-6 m'de gerçeğin 2.13 katını okur.**

Sayısal sonuç (kendi hesabım, deponun 2.13× ölçümüyle):

| Gerçek menzil | Vekil okuma | `k` (TERM_DIKEY_M = 17) | Tasarlanan `k` (gerçek/12) | Kalan dikey ofset (W0 = −12.7°) |
|---|---|---|---|---|
| 12 m | 25.6 m | 1.00 | 1.00 | 2.70 m |
| 8 m | 17.0 m | 1.00 | 0.67 | tasarım 1.20 m → gerçekleşen **1.80 m** |
| **4 m** | 8.5 m | **0.50** | **0.33** | tasarım 0.30 m → gerçekleşen **0.45 m** |
| 2 m | 4.3 m | 0.25 | 0.17 | tasarım 0.076 m → gerçekleşen 0.11 m |

Yani rampanın **en kritik olduğu son 4 metrede kalan ofset tasarlanandan %50 fazla**. Mutlak fark 0.15 m; ölçülen CPA `|dz| = 1.19 m`'nin yanında baskın değil ama yönü kötü ve bedava düzeltilebilir.

**2. Nişan kaymamızın işareti sürpriz — ve ölçülmüş.**
`bbox_ibvs.py:924-940`: `W0 = −12.7°` (pitch medyanı −17.6°) → **negatif yükseliş = hedefin ÜSTÜNDEN geçiyoruz**. VISUAL CPA (r ≤ 3 m, n=61): `|dz|` medyan **1.19 m**, `dz` medyan **+0.96 m**, yalnız **%10'u altta**. Deponun kendi hükmü doğru: bu bir kontrol hatası değil, **tasarım ofseti**; ve GPS tarafındaki 1.553 m alt ofsetinin aynasıdır.

**3. Terminal fazımız fiilen BALİSTİK — bu raporun en sert bulgusu.**

Kapalı çevrim zaman sabitimizin alt sınırı:
```
dedektör gecikmesi   0.20-0.25 s
yaw takip gecikmesi  0.28 s
yatay kanal tau      0.72-0.93 s
──────────────────────────────
τ_kapalı_çevrim   ≈  1.20 - 1.46 s
```
Terminal mandal `boyut ≥ 25 px` ≈ 6.4 vekil m ≈ **4.5 gerçek m**'de kapanıyor. Terminal hızı 18 m/s. Ölçülen kapanma hızı: düz +1.40 m/s, manevrada **−0.77 m/s**.

`t_go` hesabı (kapanma hızıyla, `V_terminal` ile değil — çünkü ıskayı kapanma belirler):
- Düz uçuşta, R = 4.5 m ve kapanma 1.40 m/s → `t_go = 3.2 s` → **2.2-2.7 zaman sabiti**
- Manevrada kapanma negatif → **t_go tanımsız / sonsuz**, yani mesafe kapanmıyor

Ama gerçekte terminal taahhüt `TERMINAL_SURE = 2.0 s` sürüyor ve o sürede hedefe göreli hareketimiz kapanma × 2.0 = 2.8 m (düz) / −1.5 m (manevra).

**Hüküm:** Düz rejimde bile terminal faz **2.2-2.7 zaman sabiti** kadar sürüyor. Doğrulayamadığım "≥10 zaman sabiti" kuralının hangi biçimi alınırsa alınsın, 2.2-2.7 **çok azdır**: taahhüt anındaki yanal hata terminalde ancak kısmen düzeltilebilir. Manevra rejiminde ise hiç düzeltilemez. Bu, deponun bağımsız bulgusuyla birebir örtüşüyor: **sonuç 30 m'de belirleniyor** (aspect@30 m için Cliff δ = −0.81), terminalde değil.

**4. Terminal λ̇ kapısı doğru şekilde reddedilmiş — ve sebebi literatürle uyumlu.**
`bbox_ibvs.py:403-421`: eşik 12 °/s ile 18 terminal taahhüdün 15'i bloklanırdı ve **bloklananların CPA medyanı 2.66 m, geçenlerinki 4.83 m — ters korelasyon**. Sebebi de doğru teşhis edilmiş: 6-11 m'de küçük yanal ofset bile 40-70 °/s λ̇ üretir; bu hedefin dönüşü değil **bizim kendi geometrimizdir** (`λ̇ ≈ v_yanal/R`, R küçüldükçe patlar). Bu, terminal fazda λ̇ tabanlı hiçbir kapının çalışmayacağının yapısal gerekçesidir.

### (d) Somut öneri ve beklenen kazanç

| Öneri | Ne | Beklenen kazanç |
|---|---|---|
| **Ö-4.1** | `TERM_DIKEY` rampasını **aç** (`AVCI_IBVS_TERM_DIKEY = 17` vekil m ≈ 12 gerçek m) | Deponun sim taraması: eşik kapalı `\|dz\|` 1.04 → 8 m'de 0.93 → **12 m'de 0.82** → 20 m'de 0.66. Beklenen kazanç 12 m'de **0.22 m** |
| **Ö-4.2** | Rampanın menzil kaynağını `h`-ağırlıklı modele bağla (Ö-1.2 ile birleşir) | Son 4 m'de kalan ofset 0.45 → **0.30 m** (−0.15 m) |
| **Ö-4.3** | **Terminal kararı yerine taahhüt-öncesi kapı**: terminal mandalına `aspect < 110°` şartı ekle | Ölçülen: 150-180° bandında **191 denemede 0 vuruş**; 60-90° bandında P = 0.421. Kuyruk geometrisinde terminale hiç girmemek boşa harcanan taahhütleri keser |
| **Ö-4.4** | `TERMINAL_SURE`'yi kapanma hızına bağla: `min(2.0 s, R/max(kapanma, 0.5))` | Kapanma negatifken 2.0 s kör hücum, hedeften **1.5 m uzaklaşmak** demek. Bu süre boyunca algı da kapalı |

### (e) Riskler / çürütme

- **Ö-4.1 için depoda açık uyarı var:** *"dikeye daha çok yetki ver (ivme split) TEK BAŞINA görsel fazı KÖTÜLEŞTİRİR"* ve benzetimde yalnız-split `|dz|` 1.09 → 1.04 ama **medyan +0.21 → +0.64** (daha çok üstte). Sıralama zorunlu: **önce rampa (Ö-4.1), sonra split.**
- **Ö-4.3 riski:** aspect'i bbox'tan kestirmek gerekir (w/h'den). `w/h < 1.3` zaten hayalet kapısı olarak kullanılıyor ve 8-16 px bandında karelerin %27'sini eliyor → o bantta w/h gürültülü. Aspect kapısı bu yüzden **yalnız boyut ≥ 16 px** karelerde uygulanabilir. Aksi halde iyi taahhütleri de bloklar — tıpkı λ̇ kapısının yaptığı gibi.
- **Ö-4.4 riski:** kapanma hızı kestirimimizin SNR'ı **0.4** (σ(Vc) ≈ 0.24·R = ±5.3 m/s @22 m, gerçek Vc medyanı 2.07). Yani kapanmaya bağlı bir kapı, gürültüyle sürülen bir kapıdır. Anlamlılık eşiği deponun ölçtüğü gibi `Vc > 0.72·R`. **Bu yüzden Ö-4.4 ancak menzil modeli düzeltildikten sonra denenebilir.**
- **Genel çürütme riski:** "terminal balistik" hükmüm zaman sabitlerinin toplanabilir olduğu varsayımına dayanıyor; gerçek kapalı çevrim tepkisi ölçülmedi. Doğrulama yolu: terminal mandal anından CPA'ya kadar `eps` ve `v_cmd` izlerini çıkarıp, mandal anındaki yanal hatanın CPA'daki yanal hatayla korelasyonuna bakmak. Korelasyon ≈ 1 ise balistik hükmü doğrulanır.

---

## SORU 5 — Algı sürekliliği: küçük/uzak hedefte tespit, ölü hesap ne zaman güvenli ne zaman zehirli

### (a) Literatürün dediği

**1. Düşük skorlu kutuyu atma — izleyiciyle doğrula.** ByteTrack'in tek fikri budur: *"The objects with low detection scores, e.g. occluded objects, are simply thrown away, which brings non-negligible true object missing and fragmented trajectories... For the low score detection boxes, we utilize their similarities with tracklets to recover true objects and filter out the background detections."* 9 farklı izleyiciye uygulandığında IDF1'de **1 ila 10 puan** tutarlı iyileşme.

**2. Küçük nesnede dilimli çıkarım.** SAHI: yalnız çıkarım tarafında **+6.8 / +5.1 / +5.3 AP** (FCOS/VFNet/TOOD), dilimli ince ayarla birlikte **+12.7 / +13.4 / +14.5 AP**. Uyarlanabilir dilimleme ise AP'yi artırırken **çıkarım süresini %20-25 düşürüyor**. İrtifaya duyarlı dinamik döşeme küçük nesne mAP'sinde **+%38**.

**3. Ölü hesabın zehirliliği — OC-SORT'un tanısı.** *"While this assumption [linear motion] is acceptable for very short periods of occlusion, linear estimates of motion for prolonged time can be highly inaccurate. Moreover, when there is no measurement available to update Kalman filter parameters, the standard convention is to trust the priori state estimations for posteriori update. This leads to the accumulation of errors during a period of occlusion. The error causes significant motion direction variance in practice."* Çözümleri: kör dönemde filtreyi körü körüne ilerletme; nesne geri geldiğinde son gözlem ile yeni gözlem arasına **sanal yörünge** kurup filtreyi o aralık üzerinde yeniden koştur.

**4. Yanlış pozitif bedeli.** Radar/izleme literatüründe standart araç M-of-N onay mantığı ve çoklu hipotez onayıyla yanlış-iz oranı kontrolü.

### (b) Kaynaklar

- Y. Zhang, P. Sun, Y. Jiang, D. Yu, F. Weng, Z. Yuan, P. Luo, W. Liu, X. Wang, "ByteTrack: Multi-Object Tracking by Associating Every Detection Box", arXiv:2110.06864, 2021/2022 (ECCV 2022). MOT17 test: MOTA 80.3, IDF1 77.3, HOTA 63.1, 30 FPS V100
- J. Cao, J. Pang, X. Weng, R. Khirodkar, K. Kitani, "Observation-Centric SORT: Rethinking SORT for Robust Multi-Object Tracking", arXiv:2203.14360, 2022 (CVPR 2023)
- F. C. Akyon, S. O. Altinuc, A. Temizel, "Slicing Aided Hyper Inference and Fine-tuning for Small Object Detection", arXiv:2202.06934, 2022 (ICIP 2022)
- M. C. Keles, B. Salmanoglu, M. S. Guzel, B. Gursoy, G. E. Bostanci, "Evaluation of YOLO Models with Sliced Inference for Small Object Detection", arXiv:2203.04799, 2022
- F. Moretti, Y. Jin, G. Mario, "Adaptive Slicing-Assisted Hyper Inference for Enhanced Small Object Detection", arXiv:2604.19233, 2026
- S. Ahmed, O. Pizarro, "Maritime Small Object Detection from UAVs using Altitude-Aware Dynamic Tiling", arXiv:2511.19728, 2025
- K. Liu et al., "ESOD: Efficient Small Object Detection on High-Resolution Images", arXiv:2407.16424, 2024
- C. Xu, J. Wang, W. Yang, H. Yu, L. Yu, G.-S. Xia, "Detecting tiny objects in aerial images: A normalized Wasserstein distance and a new benchmark", arXiv:2206.13996, 2022 — IoU'nun küçük nesnelerde konum sapmasına **aşırı duyarlı** olduğu ve etiket atamasını bozduğu
- J. Wang, C. Xu, W. Yang, L. Yu, "A Normalized Gaussian Wasserstein Distance for Tiny Object Detection", arXiv:2110.13389, 2021
- C. Xu et al., "RFLA: Gaussian Receptive Field based Label Assignment for Tiny Object Detection", arXiv:2208.08738, 2022
- S. P. Noyes, "Control of false track rate using multiple hypothesis confirmation", *Target Tracking 2004: Algorithms and Applications*. DOI: 10.1049/ic:20040062
- J. Dezert, "Performance evaluation of a 2/2×m/n logic for track formation in clutter using a bi-band imaging sensor", *IEE Colloquium on Target Tracking*, 1999. DOI: 10.1049/ic:19990516
- W. Wu, "Track-Before-Detect for Dim Targets", in *Target Tracking with Random Finite Sets*, Springer, 2023. DOI: 10.1007/978-981-19-9815-7_10

### (c) Bizim ölçümümüzle kıyas

**1. Yanlış pozitifin gerçek bedelini SAYIYLA hesaplayabiliyoruz.**

Ölçülenler:
- Gerçek tespit varken hız yönü ↔ hedefe yön hatası: **8.3°** medyan
- Ölü hesap (son komut tekrarı) rejiminde faz geneli: **56.4°** medyan
- Hayalet karesinde kerteriz hatası: **141.6°** medyan (`bbox_ibvs.py:1894-1906`)

Eşiği 0.35 → 0.25 düşürmek **1713 kare (%5.6)** ekliyor. Bu karelerin `p` kesri yanlışsa, beklenen hata:
```
E[hata | eşik düşük] = p·141.6° + (1−p)·8.3°
Alternatif (kutu yok say → ölü hesap) = 56.4°
Başabaş:  p·141.6 + (1−p)·8.3 = 56.4
          p·133.3 = 48.1
          p = 0.361
```
**Karar kuralı: yeni kabul edilen kutuların %36'sından azı yanlışsa eşiği düşürmek KAZANÇTIR.** Bu, "precision" gibi soyut bir metrikten çok daha kullanışlı ve bizim yasamıza özgü bir ölçüttür.

Depo bu deneyi kısmen zaten yapmış: boru hattı 0.25'te çalışırken kilit kapısı 0.35'te → **1713 kare (%5.6) bu aralıkta ve kilit kırılmalarının %17.4'ünü tek başına yapıyor**. Hizalayınca **≥5 s epizod 43 → 57 (+%32.6)**, ≥5 s payı %31.5 → %38.9. Bu, ByteTrack'in "IDF1'de 1-10 puan" iyileşmesinin bizdeki karşılığıdır.

**Uyarı:** `MEVCUT_DURUM.md`'deki tarihsel referans koşuda **TP=0, FP=66 → precision %0** ve FP conf medyanı **0.74**. Yani bir konfigürasyonda yanlış pozitiflerin conf'u yüksekti. `p` **varsayılamaz, ölçülmelidir.**

**2. Tespit menzil eğrimiz literatürün tarif ettiği "tiny object" çöküşü.**

| Menzil | Dedektör kutu verme oranı | Truth: hedef kadrajda | **Kayıp = geri çağırma** |
|---|---|---|---|
| 20-30 m | %74 | ~%90-93 | %16-19 |
| 30-40 m | %57 | ~%90-93 | %33-36 |
| 50-60 m | **%24** | ~%90-93 | **%66-69** |

Ve conf < 0.35 oranı 10-20 m'de %1.5 iken 40-50 m'de **%31.5** — yani uzak menzilde model hedefi *görüyor ama emin olamıyor*. Bu, ByteTrack senaryosunun ders kitabı örneğidir.

Piksel boyutuna çevirelim: DoW'da `menzil × max(w,h) = 743 px·m` → 50 m'de kutu **14.9 px**, 30 m'de 24.8 px, 20 m'de 37 px. COCO'nun "small" tanımı 32×32 px; 50 m'deki hedefimiz **14.9 px** — literatürün "tiny" (<16 px) sınıfında. Xu ve ark.'nın gösterdiği IoU duyarlılığı ve etiket ataması çöküşü tam olarak bu boyutta başlıyor.

**3. Kopma sebeplerimiz ve literatürdeki karşılıkları.**

| Kopma sebebi | Pay | Literatürdeki çözüm | Bizde durum |
|---|---|---|---|
| Kutu yok | **%49.8** | dilimli/ROI çıkarım, TBD | `AVCI_KROP`, `AVCI_SAHI` env'leri **var, ölçülmemiş** |
| Boyut kapısı | **%29.5** | — (bizim kendi kapımız) | 20-30 m bandında karelerin **%66.4'ünü** eliyor |
| Hayalet | **%22.5** | M-of-N onay, izleyici doğrulaması | `w/h < 1.3` kapısı; 8-16 px bandında **%27.0** eliyor |
| conf < 0.35 | %5.6 | ByteTrack | ölçüldü: kırılmaların **%17.4'ü** |

**Boyut kapısı bizim en pahalı kendi kapımız.** DEVIR fazında karşı-olgu ölçümü var: kapı kaldırılınca MAX epizod **2.66 → 9.64 s**, ≥5 s epizod **0 → 22 (%2.72)**. Yani 5 s şartı, boyut kapısı yüzünden **yapısal olarak imkânsızdı**.

**4. Ölü hesabımız: hangi biçimi zehirli, hangisi güvenli — ölçülmüş.**

| Biçim | Ne yapıyor | Sonuç | OC-SORT'un tanısıyla uyum |
|---|---|---|---|
| **Piksel köprüsü** | Piksel hızıyla **birinci derece** ekstrapolasyon | ⛔ 42.9° → 70.9°; görürken bile 8.2° → 25.7° | **Tam uyum**: "linear estimates for prolonged time can be highly inaccurate" + parazitik döngü |
| **Son komut tekrarı** | Sıfırıncı derece, **gövde çerçevesinde** | ⚠ faz geneli 56.4°, %24'ü >90° | Kısmi: gövde döndükçe komut bayatlıyor |
| **Atalet köprüsü** | Sıfırıncı derece, **atalet çerçevesinde** | ✅ ömür 1.97 → 3.92 s, ıska 12.12 → 2.81 m | **Tam uyum**: hiçbir şey ekstrapole edilmiyor |

**Kural buradan çıkıyor:** *Ölü hesap, ekstrapole edilen büyüklüğün kendi hareketimizden arınmış olduğu ve türev alınmadığı ölçüde güvenlidir.* Bizim üç denememiz bu kuralın üç noktasıdır ve tam sıralamayı veriyor.

Süre duyarlılığı da ölçülü: **0.30 s ve 0.60 s etkisiz/zararlı, 1.5 s kazandırıyor.** Bu ilk bakışta ters — ama açıklaması var: `KAYIP_M = 60 kare ≈ 1.9 s`, yani faz 1.9 s kutusuzlukta ölüyor. 0.30-0.60 s'lik bir köprü fazı kurtaramaz, yalnız birkaç kare bulanıklaştırır. Köprünün işe yaraması için **`T_köprü` ile `KAYIP_M/f` aynı mertebeye gelmeli**. Deponun kendi ifadesi: *"Yapısal kapı: KOR_KOPRU > KAYIP_M/31Hz"* → **1.9 s**. Şu anki 1.5 s bu kapının **altında**.

### (d) Somut öneri ve beklenen kazanç

| Öneri | Ne | Beklenen kazanç |
|---|---|---|
| **Ö-5.1** | `AVCI_KILIT_CONF` 0.35 → **0.25** (boru hattıyla hizala) | Ölçülmüş: ≥5 s epizod **43 → 57 (+%32.6)**; conf kaynaklı kırılma %17.4 → ~0. Kabul koşulu: yeni kutuların yanlış payı **p < 0.361** |
| **Ö-5.2** | `AVCI_KROP` = 1 (öngörülen konum çevresinde ROI, sabit çıkarım maliyeti) | Literatür: dilimli çıkarım +5-7 AP; uyarlanabilir dilimleme süreyi %20-25 **düşürüyor**. Hedef: 30-40 m'de kutu oranı %57 → **>%70**, 50-60 m'de %24 → **>%35** |
| **Ö-5.3** | Boyut kapısını **menzile bağlı** yap (sabit px yerine) | Karşı-olgu ölçümü: DEVIR'de ≥5 s epizod **0 → 22 (%2.72)**, MAX 2.66 → 9.64 s |
| **Ö-5.4** | `KOR_KOPRU_ATALET` 1.5 → **1.8 s** (yapısal kapı 1.9 s) | Faz ömrü 3.92 s'den yukarı. **Ama** hedef dönüş hızına bağlı tavan şart (bkz. riskler) |
| **Ö-5.5** | Hayalet kapısını **M-of-N**'e çevir: tek karede w/h yerine, ardışık N karede tutarlılık | Hayalet %22.5 kopma payı; 8-16 px bandında **%27.0** eleme — bu bant tam olarak DEVİR bandı |

### (e) Riskler / çürütme

- **Ö-5.1'in kırılma testi zorunlu:** tarihsel koşuda FP conf medyanı **0.74** idi, yani 0.25 eşiği o modelde felaket olurdu. Deney öncesi `p`'yi truth ile ölç; `p ≥ 0.361` ise **hiç deneme**.
- **Ö-5.2'nin sert mekanizma kapısı:** `det_ms` şu an 41-70 ms, fps 13-25. Krop çıkarım maliyetini artırırsa döngü 32.3 Hz'in altına düşer ve **λ̇ penceresi (0.25 s) örnek bulamaz**. Kapı: `det_ms` p95 **70 ms'i AŞMAMALI**; aşarsa deney geçersiz. (Bu yüzden SAHI değil **krop** öneriyorum — SAHI 2×2 dilimleme det_ms'i 4× yapar: 164-280 ms, kesin ölüm.)
- **Ö-5.3 tehlikeli:** boyut kapısı hayalet/uzak-menzil gürültüsüne karşı gerçek bir savunma. Gevşetmek yanlış-pozitif payını (`p`) yükseltir ve Ö-5.1'in başabaş noktasını aşabilir. **Ö-5.1 ile aynı kampanyada denenmemeli.**
- **Ö-5.4'ün zehirlilik sınırı hesaplanabilir:** köprü süresince hedefin kerterizi `ω_hedef · T` kadar kayar. `T = 1.8 s`:
  - medyan dönüş 6.55 °/s → **11.8°** (kadraj sınırı 61°'nin %19'u) ✅
  - p90 dönüş 32.0 °/s → **57.6°** (sınırın %94'ü) ⚠
  - p95 dönüş 111.9 °/s → 201° ⛔
  Yani sabit 1.8 s **düz rejimde güvenli, dönüş rejiminde zehirli**. Doğru form: `T_köprü = min(1.8, 30°/|ω_hedef_tahmin|)`. Bu ölçülmemiş bir mekanizmadır ve tek başına bir deney gerektirir.
- **Genel çürütme:** deponun kendi uyarısı geçerli — ilk atalet köprüsü A/B'si köprünün işe **yaramadığını** söylemişti (68.3° / 64.4° / 82.3°) ve sonra tersi ölçüldü. Sebep: aynı ayarla iki koşu arasında **25° fark** (etkin örneklem ~10). **Her öneri en az iki bağımsız tekrarla ve serpiştirilmiş taban koluyla ölçülmeli.**

---

## SORU 6 — Gecikme telafisi: kestirimci öncüleme ne zaman işe yarar, ne zaman kararsızlık getirir

### (a) Literatürün dediği

**Smith predictor ailesi.** Gecikmeyi kapalı çevrim karakteristik denkleminden çıkarır — **ama bunu yapabilmesi için tesis modelinin ve gecikmenin doğru bilinmesi şarttır.** Model uyuşmazlığı ve **değişken gecikme** Smith predictor'ın bilinen zayıf noktasıdır; literatürde bu yüzden uyarlamalı sürümler var.

**Gecikmeli ölçüm füzyonu (OOSM / delayed KF).** Farklı bir şey: gecikmeli gelen ölçümü, filtre zaten ilerlemişken doğru zaman damgasına geri döndürüp (retrodiction) birleştirmek. Bu **kestirimci öncüleme değildir** — gecikmeyi tahminle kapatmaz, ölçümü doğru ana oturtur.

**Gecikmeli LOS hızıyla PN.** Dhananjay, Lum & Xu (2010) doğrudan bu problemi analiz ediyor: gecikmeli LOS hızıyla PN'in kararlılığı ve yakalanabilirliği. *(Bu makalenin özetine erişemedim — IEEE elemiş; sonuç cümlelerini alıntılayamıyorum → o noktada **KAYNAK YOK**, yalnız künye verilebilir.)*

**Biyolojinin cevabı: gecikmeyi telafi etme, kazancı düşür.** Brighton & Taylor'ın (2019) uydurduğu yasa **gecikmeli girdileri açıkça kullanıyor**: `γ̇(t) = N·λ̇(t−τ) − K·δ(t−τ)`, τ = 0.09 s. Şahin bunu ileri sarmıyor; τ'yu modelin içinde bırakıp N = 0.7 ve K = 1.2 s⁻¹ gibi **düşük** kazançlarla çalışıyor. Fabian ve ark. (2018) aynı ilkeyi iki sinekte niceliyor: daha kısa gecikmeli tür daha **düşük** N kullanıyor (Coenosia 18 ms / N≈1.5) çünkü LOS hızları çok yüksek; daha uzun gecikmeli tür daha yüksek N kullanabiliyor çünkü LOS hızları düşük. **Yani gecikme telafisi yerine kazanç-gecikme çarpımının yönetimi.**

**Görsel gecikmenin filtre tarafında telafisi işe yarıyor (karşı örnek).** Yan ve ark. (2024) IBVS+PNG sistemlerinde **delayed Kalman filter (DKF)** kullanıyor: *"combines smoother trajectories from the IBVS controller with high-frequency target 2D position estimation via a delayed Kalman filter (DKF) to minimize the impact of image processing delays on accuracy."* Ölçülen: CEP **0.457 m → 0.332 m → 0.089 m** (önceki iki çalışmaya göre; %72.8 iyileşme).

### (b) Kaynaklar

- N. Dhananjay, K.-Y. Lum, J.-X. Xu, "Analysis of proportional-navigation guidance law with delayed line-of-sight rate", *IEEE ICCA 2010*. DOI: 10.1109/ICCA.2010.5524249
- H. Yan, K. Yang, Y. Cheng, Z. Wang, D. Li, "Precise Interception Flight Targets by Image-based Visual Servoing of Multicopter", arXiv:2409.17497, 2024
- C. H. Brighton, G. K. Taylor, *Nature Communications* 10:2462, 2019. DOI: 10.1038/s41467-019-10454-z
- S. T. Fabian et al., *J. R. Soc. Interface*, 2018. DOI: 10.1098/rsif.2018.0466
- H. Xie, "Visual servoing with modified Smith predictor for micromanipulation tasks", *IEEE ICMA 2005*. DOI: 10.1109/ICMA.2005.1626525
- M. T. M. Rupp, "Cascaded Time Delay Compensation and Sensor Data Fusion for Visual Servoing", *IEEE SMC 2021*. DOI: 10.1109/SMC52423.2021.9659177
- A. Mohammed, "Compensation of Unknown Time Delay Measurement for Network Visual Servoing", *Studies in Informatics and Control*, 2018. DOI: 10.24846/v27i3y201804
- E. Dragolj, "Compensation of time-varying delay in networked control systems using adaptive Smith predictor", *IEEE Mechatronics 2011*. DOI: 10.1109/ICMECH.2011.5971258
- Y. Iwazaki, "An approach of visual servoing control considering compensation of time delay", *ISIE '97*. DOI: 10.1109/ISIE.1997.649085
- J. A. Kempton, C. H. Brighton, G. K. Taylor, "Visual versus visual-inertial guidance in hawks pursuing terrestrial targets", *J. R. Soc. Interface*, 2023. DOI: 10.1098/rsif.2023.0071 (n = 228 uçuş, N = 4 şahin)
- F. Nesline, P. Zarchan, "Line of sight reconstruction for faster homing guidance", 1983. DOI: 10.2514/6.1983-2170
- A. Loch, G. Haessig, M. Vincze, "Event-Based high-speed low-latency fiducial marker tracking", arXiv:2110.05819, 2021 — uçtan uca **3 ms** gecikme
- J. W. Lee, H. Lim, S. Yang, J. B. Choi, "Hybrid Vision Servoing with Deep Alignment and GRU-Based Occlusion Recovery", arXiv:2510.25233, 2025 — 30 Hz servo halkasında **<2 px** izleme hatası, tıkanmada GRU öngörücü

### (c) Bizim ölçümümüzle kıyas — **literatür bizim bulgumuzu DESTEKLİYOR**

**1. Bizim ölçümümüz (`bbox_ibvs.py:482-489`).**
Yasanın ürettiği LOS, `truth LOS(t−D)` ile kıyaslandı, D = −0.10 … 0.70 s taraması:
```
D = 0.00 → 2.50°
D = 0.05 → 2.32°   ← EN İYİ
D = 0.25 → 5.42°
D = 0.45 → 10.63°
```
**Etkin bayatlık yalnız 0.05 s.** Yapısal sebep depoda doğru teşhis edilmiş: yasa `iris_yaw(ŞİMDİ) + ε(t−D)` topluyor; kuyruk takibinde `ψ̇_gövde ≈ λ̇` olduğu için **yaw terimi gecikmeyi kendiliğinden kapatıyor**.

**Bu mekanizmanın literatürdeki adı var:** strapdown arayıcıda `λ = ψ_gövde + ε` (Soru 2). `ψ_gövde` **anlık** (jiro), `ε` **gecikmeli** (dedektör). Toplamda gecikme, yalnız `ε`'un `ψ_gövde`'den bağımsız kısmına etki eder. Kuyruk takibinde `ε` neredeyse sabittir (burun hedefe kilitli) ve tüm LOS değişimi `ψ_gövde`'den gelir → gecikme neredeyse görünmez. Bu, Nesline & Zarchan'ın "LOS reconstruction for faster homing guidance" çalışmasının ters yüzüdür: onlar gövde bilgisini **halkayı hızlandırmak** için kullanıyor; bizde aynı terim gecikmeyi **maskeliyor**.

**Sonuç: 0.225 s ileri sarma medyan hatayı 2.3° → 5.4°'ye ÇIKARIR.** Çünkü zaten kapatılmış bir gecikmeyi ikinci kez kapatmaya çalışıyor — **aşırı telafi**.

**2. Literatürün desteği.**
- Brighton & Taylor'ın şahini gecikmeyi telafi **etmiyor**; τ = 90 ms'lik girdiyle çalışıyor ve karma yasa saf yasaların ikisini de yeniyor (0.34 m vs 0.46/0.51 m). Yani biyolojik önleyicide gecikme telafisi **yok**, kazanç yönetimi **var**.
- Kempton ve ark. (2023) daha da ileri gidiyor: şahinin karma yasası, atalet λ̇ yerine **hedefin arka plana göre görsel hareketi** konduğunda da veriyi iyi modelliyor. Yani bearing-only, gövde çerçevesinde, gecikmeli bir sinyal yeterli.

**3. Ama bir karşı örnek var ve ciddiye alınmalı.**
Yan ve ark. (2024) DKF ile CEP'i 0.332 → **0.089 m**'ye indiriyor. Bu bizim sonucumuzla çelişiyor gibi görünüyor. **Çelişki değil — farklı yerde telafi:**

| | Yan ve ark. 2024 | Bizim çürütülen deneme |
|---|---|---|
| Nerede | **Kestirici** (2B hedef konumu KF'i) | **Yasanın girdisi** (kerteriz açısı) |
| Ne yapıyor | Gecikmeli ölçümü doğru zaman damgasına oturtuyor | Kerterizi ileriye tahmin ediyor |
| Ne gerektiriyor | Doğru zaman damgası | Doğru hedef modeli + kararlı gecikme |
| Bizdeki karşılığı | **Henüz yok** | Reddedildi (2.3° → 5.4°) |
| Rejim | terminal hız **5-6.3 m/s**, 16 cm balon | **22-24 m/s**, 1.28 m kanat |

Ayrıca Yan'ın rejiminde λ̇ çok daha küçüktür (yavaş kapanma, küçük hedef), bu yüzden ileri sarmanın kazandırdığı ile kaybettirdiği oranı bizden farklıdır.

**4. Bizde Smith predictor NEDEN kararsızlık getirir — sayıyla.**
Smith predictor sabit ve bilinen gecikme ister. Bizim gecikmelerimiz:

| Gecikme kaynağı | p50 | p95 | max | Kararlı mı |
|---|---|---|---|---|
| `det_ms` | 29.7 ms | 44.7 ms | — | ✅ makul |
| Yaw **bayatlığı** | — | **2.31 s** | **7.47 s** | ⛔ tiklerin **%59.4'ü bayat** |
| Görsel fazda bayat tik | %27.8 | — | — | ⛔ |
| Döngü | 21.3-32.3 Hz | — | — | ⚠ değişken |

**Yaw bayatlığı öldürücüdür:** Smith predictor tesis modelini `ψ_gövde` ile ilerletir; `ψ_gövde` karelerin %59.4'ünde bayatsa, öngörücü **yanlış bir durumdan** ileri sarar. p90 = 1.17 s bayatlıkta, 30 °/s dönüşle **35°** hatalı bir başlangıç noktası demektir. Hiçbir öngörücü bunu kurtaramaz.

**Bu, gecikme telafisi tartışmasının asıl cevabıdır: bizde çözülmesi gereken şey gecikme değil, BAYATLIK.**

**5. Çıkış tarafı telafisi (M2) doğru yer.**
`bbox_ibvs.py:519-544`: ölçülen `tau_arac = 16.4°/29.0 °/s = 0.57 s` (dönüşte hız vektörü sapması 16.4°, düzde 1.2°). `hiz_yonu += clamp(tau·w_uyg, ±25°)`, `ARAC_TAU = 0` (kapalı), önerilen 0.35. Ve deponun kritik notu: `psi_v` durumu **öngörüsüz bırakılıyor**, yoksa döngü kendi öncülemesini geri okuyup pozitif geri beslemeye döner.

Bu ayrım literatürde nettir: **ölçüm gecikmesi** girdi tarafındadır ve öngörü riskli; **eyleyici gecikmesi** çıkış tarafındadır ve ileri besleme ile telafi edilebilir çünkü komut değerini **biliyoruz** (ölçmüyoruz). M2, ölçülen ıska ayrıştırmasında %38.3'lük payı olan kalemi hedefliyor:
```
Manevra ıskası ayrıştırması (n = 1390 dönüş karesi):
  kerteriz hatası   −0.8°  (%1.9)
  SIGMA            −18.2°  (%42.5)
  ARAÇ GECİKMESİ   −16.4°  (%38.3)   ← M2 buraya
  ────────────────────────
  toplam           −42.8°
```

### (d) Somut öneri ve beklenen kazanç

| Öneri | Ne | Beklenen kazanç |
|---|---|---|
| **Ö-6.1** | **Yaw bayatlığını çöz** (telemetri hattı, GIL). Bu bir yasa değişikliği değil, altyapı | Tiklerin %59.4'ü bayat; λ̇ şişmesi ayrıştırmasında "donuk yaw" payı **5.0×**. Bu tek başına λ̇ kalitesini en çok iyileştirecek kalem |
| **Ö-6.2** | **M2 araç gecikme telafisi**: `AVCI_IBVS_ARAC_TAU = 0.35` (ölçülen 0.57, ihtiyatlı), `ARAC_TAU_MAX = 25°` | Ölçülen kalem: dönüş ıskasının **%38.3'ü**. 0.35 s × 29 °/s = **10.2°** geri kazanım (16.4°'nin %62'si) |
| **Ö-6.3** | Girdi tarafı öngörülemeyi **açma** — ölçüm ve biyoloji hemfikir | — |
| **Ö-6.4** | Smith predictor / gecikmeli EKF'i **şimdilik açma**; ancak Ö-6.1 çözüldükten sonra ve **yalnız kestirici tarafında** (Yan 2024 biçiminde) | — |

### (e) Riskler / çürütme

- **Ö-6.2'nin ana riski deponun kendi uyarısıdır:** `psi_v` durumu öngörülemesiz kalmalı. Uygulama zaten böyle (`bbox_ibvs.py:1362-1365`) ama A/B sırasında bu invaryant loglanmalı.
- **Ö-6.2 çift sayım riski:** `tau·w_uyg` ile `lead_az = lead_süre·λ̇` aynı bilgiyi taşıyabilir. DPP açıkken `lead_az` zaten hız yönünden çıkarılıyor (`bbox_ibvs.py:1239-1244`) → çakışma yok. **Ama PN kolunda çakışır.** M2 yalnız DPP koluyla denenmeli.
- **Ö-6.1 en yüksek kazançlı ama en pahalı iş** ve bir "tek değişkenli yasa deneyi" değil, altyapı düzeltmesi. Ölçüm kapısı: bayat tik oranı %59.4 → **<%10** olmalı; olmuyorsa yasa deneylerinin hiçbirinin ayrım gücü yok.
- **Karşı-kanıt kaydı:** Yan ve ark. (2024) gecikme telafisinin CEP'i 3.7× iyileştirdiğini ölçüyor. Bizim çürütmemiz **yalnız girdi-tarafı ileri sarma** için geçerlidir; bu bulgudan "gecikme telafisi işe yaramaz" genellemesi **çıkarılmamalıdır**.
- **`YAW_HIZALA_S = 0.045` tutarsızlığı çözülmeli:** varsayılan açık, ve süpürme mekanizmayı doğruluyor (λ̇ şişmesi H0 6.9× → H1 4.4× → H2 3.2×) ama `DURUM_2026-08-16.md` "yanlış büyüklükte" diyor (45 ms hizalama 1.17 s bayatlığı düzeltemez). İkisi de doğru: **hizalama gerçek bir mekanizma ama yanlış hastalığı tedavi ediyor.** Ö-6.1 çözülünce yeniden ayarlanmalı.

---

## SORU 7 — Benzer sistemler: bildirilen ıska mesafeleri, yakalama oranları, yasa ve algı boru hattı

### (a) Literatürün dediği + (b) Kaynaklar

| Sistem | Yasa | Algı | Bildirilen sonuç | Hızlar | Kaynak |
|---|---|---|---|---|---|
| **Yan ve ark. 2024** | IBVS + PNG (`K ≈ 3`) + **FOV-tutma PD** (`kp=0.03, kd=0.01`) + DKF | Mono, **120° FOV**, Jetson CSI, YOLOv7 | **CEP 0.089 m** (SITL); gerçek uçuşta **>%80 başarı** (rüzgâr ≤4 m/s), %40 (6 m/s). Önceki çalışmalar: CEP 0.457 → 0.332 → 0.089 m | terminal **5-6.3 m/s**; hedef 16 cm balon | arXiv:2409.17497 |
| **Pliska ve ark. 2024** (RA-L 9(10):8810-8817) | **EPN**: `a = G[(1−W)(Δp + Δv·t_go)/t_go² + W·Δp]` | LiDAR + **IMM filtre** (yeni ölçüm modeli), ağ ile yakalama | 500 denemede: EPN **%100 başarı, 24.38 önleme/yörünge, ilk önlemeye 5.93 s, doğruluk 0.16 m**; GPN2 %100 / 17.60 / 8.15 s / 0.18 m; LPN %95 / 12.65 / 19.73 s / 0.17 m. Gerçek uçuş: 5 m/s hedefte 3-4 önleme | hedef ≤8 m/s, ≤4 m/s²; menzil 5-25 m | arXiv:2405.13542 |
| **Rothe ve ark. 2026** | MHE izleme, ağ ile yakalama | **LiDAR + görüntü**: DBSCAN kümeleme + özel YOLO (**>%90 tespit oranı**) | **Tespit doğruluğu <0.4 m, >40 m menzilde** (RTK-GNSS truth); tespit menzili **60 m**'ye kadar; çoklu otonom önleme görevi tamamlandı | — | *Drones* 10(6):420. DOI: 10.3390/drones10060420 |
| **Barisic ve ark. 2021** (MBZIRC) | Yörünge tahmini (Bernoulli lemniskatı) + kesişim noktası | **Stereo** ZED Mini + YOLOv3-Tiny + histogram filtresi | Sahada **9/12 başarı**; simülasyonda kendisinden **%30 hızlı** hedefi yakaladı | — | arXiv:2107.00962 |
| **Bhattacharya 2021** (CMU Team Tartan, MBZIRC) | Füze güdümünden esinli; **"quadrotor'da uygulanabilen ama füzede uygulanamayan optimal yöntem"** | **Mono** kamera | "first-pass hit success ve pursuit duration" bildiriliyor; **özet sayı vermiyor**. Yarışmada basit LOS güdümü etkili | — | arXiv:2107.01733 |
| **Evduzen 2026** | PN | Strapdown EO; piksel-düzlemi KF + **jiro füzyonu** | LOS hızı RMS: gürültüsüz 3.13×10⁻⁴ °/s, gerçekçi gürültüde **0.899 ± 0.028 °/s**; kapalı çevrim **ıska 1.71 m** | — | engrXiv, DOI 10.31224/7642 |
| **Römer, Emmert, Schoellig 2024** | PN (kapalı-form kısıtlı optimizasyon) | **Mono LOS**, VIO yok, pist haritası yok | Hareketli kapılardan geçme; **özet sayı vermiyor** | — | arXiv:2410.15799 (ICRA 2025) |
| **Liou & Cheng 2026** | Quaternion tabanlı **BPNG** + NMPC + CBF | YOLO + UKF (görsel-atalet füzyon) | "kararlı, gürbüz izleme ve isabetli terminal önleme"; **özet sayı vermiyor** | sabit kanat | arXiv:2607.12801 |
| **Vrba & Saska 2019/2020** | — | Mono, marker'sız MAV tespiti (CNN) | (Ayrıntı için tam metin gerekli) | — | DOI 10.1109/LRA.2019.2927130; 10.1109/LRA.2020.2972819 |
| **BİZ** | **DPP** (`k=1.4 s⁻¹`, `FF=1.0`) + burun-LOS ayrık + kesişim dikey | **Mono**, HFOV **122.08°**, YOLO TensorRT 960², det 41-70 ms, 13-25 fps, **yalnız bbox** | **En yakın 0.55-0.88 m**; CPA dikey 1.1-1.2 m, yatay 1.2-2.2 m. DÜZ P(<3 m) **0.650**, DÖNÜŞ **0.147** | avcı **22-24 m/s**, hedef **17.99 m/s**, μ=0.833 | — |

### (c) Bizim ölçümümüzle kıyas — dürüst yerleştirme

**Ham sayıyla:** 0.55-1.2 m bandımız, Yan'ın 0.089 m'si ve Pliska'nın 0.16 m'si ile **kıyaslanamaz görünüyor** (6-13×). Ama üç yapısal fark var:

1. **Hız.** Yan'ın terminal hızı 5-6.3 m/s, Pliska'nın hedefi ≤8 m/s. Bizimki **22-24 m/s** — 3-4 kat.
2. **Menzil sensörü.** Pliska ve Rothe **LiDAR** kullanıyor, Barisic **stereo**. Bizde yalnız bbox — menzil bir **vekil** ve %41 şişik.
3. **Hedef boyutu.** Yan'ın hedefi 16 cm balon, sabit hızlı. Bizimki 1.28 m kanatlı, 17.99 m/s, sabit oval.

**Normalize kıyas (kendi kurduğum ölçüt, literatürden değil).** Görsel güdümde temel uzunluk ölçeği "bir tespit çevriminde kör kat edilen yol"dur:
```
kör_yol = V_avcı × dedektör_gecikmesi
```

| Sistem | V | Gecikme | Kör yol | Iska | **Iska / kör yol** |
|---|---|---|---|---|---|
| Yan 2024 | 6.0 m/s | ~0.10 s* | 0.60 m | 0.089 m | **0.148** |
| Yan 2024 (gecikme 0.20 s varsayımıyla) | 6.0 m/s | 0.20 s | 1.20 m | 0.089 m | 0.074 |
| Pliska 2024 | ~8 m/s* | LiDAR ~0.05 s* | 0.40 m | 0.16 m | **0.400** |
| **BİZ (en yakın)** | 22 m/s | 0.225 s | **4.95 m** | 0.55-0.88 m | **0.111 - 0.178** |
| **BİZ (CPA yatay)** | 22 m/s | 0.225 s | 4.95 m | 1.2-2.2 m | **0.242 - 0.444** |

*(\* = kaynakta belirtilmemiş, makul varsayım — bu satırlar **kesin değildir**.)*

**Hüküm:** En yakın geçiş ölçütünde (0.111-0.178) Yan'ın seviyesindeyiz; medyan CPA ölçütünde (0.242-0.444) Pliska'nın seviyesindeyiz. **Yani mutlak sayıda geride, hıza ve algı gecikmesine normalize edildiğinde rekabetçiyiz.** Erişebildiğim literatürde **mono-bbox-only ile 20+ m/s'de metre-altı önleme bildiren tek bir çalışma yok** — bu, bizim problem sınıfımızın gerçekten daha zor olduğunun kaydıdır.

**Ödünç alınabilecek üç somut şey:**
1. **Yan'ın FOV-tutma PD'si** (`kp = 0.03`, `kd = 0.01`, `e_x → 0`, `Δe_y ≤ ε`) — bizde `BURUN_LOS` var ve `BURUN_KD = 0.0` **kapalı**. Yan'ın oranı `kd/kp = 0.33 s`, bizim burun kanalı gecikmemiz 46 ms ölü + 211 ms ≈ 0.26 s → **aynı mertebe**. Bu, `BURUN_KD`'yi 0'dan açmak için literatür destekli bir başlangıç değeri veriyor.
2. **Yan'ın ivme kaynaklı LOS hatası sınırı:** `Δq_d ≤ arctan(k_a/g)`. Bizim 12 m/s² ivme tavanımızda `arctan(12/9.81) = 50.7°` — yani ivme, kamerayı 50.7°'ye kadar eğebilir. HFOV yarısı 61°. **Bu, tam ivmede hedefin kadrajı terk etmesine 10.3° kaldığını söylüyor** ve fazlarımızın %64.7'sinin hedef kadrajdayken ölmesiyle tutarlı.
3. **Pliska'nın kayıp-izde davranışı:** *"the planning is interrupted and the interceptor starts rotating in place to re-acquire the detection."* Bizde karşılığı yok — kutu yokken **son komut tekrarlanıyor** (56.4° medyan hata). Yerinde dönüp yeniden yakalama, atalet köprüsünün süresi dolduğunda mantıklı bir geri çekilme davranışıdır.

### (d) Somut öneri ve beklenen kazanç

| Öneri | Ne | Beklenen kazanç |
|---|---|---|
| **Ö-7.1** | `AVCI_IBVS_BURUN_KD` = **0.09 s** (Yan'ın `kd/kp = 0.33 s`'inin, bizim λ̇ şişmemiz 3.2-5.9× olduğu için ~3× küçültülmüş hali) | Burun kanalı 46 ms ölü + 211 ms gecikme; türev öncülemesi hedefi kadrajın ortasına yakın tutar. Ölçülen tespit kaybı merkezde 0.036, 39°+ 0.609 → **17× fark** |
| **Ö-7.2** | Atalet köprüsü süresi dolduğunda **yerinde tarama** (Pliska'nın davranışı), son komut tekrarı yerine | Son komut tekrarı medyan 56.4° hata, %24'ü >90°. Tarama en azından hatayı sınırlar |
| **Ö-7.3** | İvme–FOV bağını kayda geçir: `Δq = arctan(a/g)`; a=12 m/s² → 50.7° | Ö-3.1 (dönüş bütçesi) ile birleşince ikinci kazanç: yavaşlayınca gereken ivme de düşer → kamera daha az eğilir → hedef kadrajda kalır |

### (e) Riskler / çürütme

- **Normalize kıyasım literatürden değil, benim kurduğum bir ölçüttür.** Yan ve Pliska'nın gecikmelerini kaynaklarında bulamadım; o satırlar varsayımlıdır ve karar dayanağı yapılmamalıdır.
- **Ö-7.1 riski:** `BURUN_KD`'nin çarpanı `eps_hızı` **kadraj içi** kayma hızıdır, atalet λ̇ değil (`bbox_ibvs.py:1802-1814`). Depo bunu bilinçli seçmiş çünkü λ̇ 4-7 kat şişik. Yine de kadraj içi hız da kendi dönüşümüzü içerir → **küçük bir parazitik döngü riski**. 0.09 s küçük bir değer ama işaret kontrolü şart (Soru 2, Ö-2.4).
- **Ö-7.2 riski:** yerinde tarama görsel fazı bitirir ve GPS'e devreder; depo "GÖRSEL'de GPS'e dönme" kuralını **kaldırmıştı** (20 geçiş, mesafe 333 m'ye fırladı). Yani tarama, faz içinde ve süre sınırlı olmalı.

---

## SORU 8 — Biyolojik önleyiciler: nicel veriler

### (a) Literatürün dediği + (b) Kaynaklar

| Tür | Yasa | N | K | Gecikme τ | Diğer sayılar | Kaynak |
|---|---|---|---|---|---|---|
| **Harris şahini** (*Parabuteo unicinctus*) | **Karma PN+PP**: `γ̇ = N·λ̇(t−τ) − K·δ(t−τ)` | **0.7** | **1.2 s⁻¹** | **0.09 s** | Medyan öngörü hatası: karma **0.34 m** (%95 GA 0.24-0.53); saf PP 0.46 m; saf PN 0.51 m. n=5 kuş, 50 uçuş | Brighton & Taylor 2019, DOI 10.1038/s41467-019-10454-z |
| **Harris şahini** (görsel vs görsel-atalet) | Karma yasa; atalet λ̇ yerine **hedefin arka plana göre görsel hareketi** de veriyi iyi modelliyor | — | — | — | n=228 uçuş, N=4 kuş. Görsel-atalet biçim en iyi uyum ama üçü de yeterli | Kempton, Brighton & Taylor 2023, DOI 10.1098/rsif.2023.0071 |
| **Şahin (peregrin)** | **Saf PN** | **medyan < 3** | — | — | Füzeler 3 ≤ N ≤ 5. *"This lower feedback gain is appropriate at the lower flight speed of a biological system, given its presumably higher error and longer delay."* | Brighton, Thomas & Taylor 2017, DOI 10.1073/pnas.1714532114 |
| **Gyrfalcon (acemi)** | Aynı yasa | peregrinden **belirgin düşük** | — | — | Daha yavaş dönüş | Brighton ve ark. 2021, DOI 10.1242/jeb.238493 |
| **Robber fly** *Holcocephala fusca* | **Saf PN** (PP ve DPP **reddedildi**) | **≈3** | — | **≈28 ms** | Açık gökyüzü, uzun menzil. N=3 *"optimal, as it minimizes the control effort"* | Fabian ve ark. 2018, DOI 10.1098/rsif.2018.0466 |
| **Killer fly** *Coenosia attenuata* | **Saf PN** | **≈1.5** | — | **≈18 ms** | Karmaşık ortam, **çok yakın menzil**. Düşük N *"may allow Coenosia to cope with the extremely high line-of-sight rotation rates, which are due to close target proximity, and thus prevent overcompensation of steering"* | aynı |
| **Blowfly** | İki farklı takip stratejisi | — | — | **10 ms'e kadar** | "uçan hayvanlarda gözlenen en hızlı yönlendirme tepkisi" | Varennes ve ark. 2020, DOI 10.1038/s41598-020-77607-9 |
| **Yusufçuk** (*Plathemis lydia*) | **İç model tabanlı** (ileri + ters gövde dinamiği modeli + av hareketi modeli) | — | — | — | *"Predictive rotations of the dragonfly's head continuously track the prey's angular position"*; *"Model-driven control thus underlies the bulk of interception steering manoeuvres, while vision is used for reactions to unexpected prey movements"* | Mischiati ve ark. 2015 (Nature), DOI 10.1038/nature14045 |
| **Yusufçuk** | Retinal sabitleme | — | — | — | *"fly directly toward the point of prey interception by steering to minimize the movement of the prey's image on the retina"*; *"parallax information from head movements was not required"* | Olberg ve ark. 2000, DOI 10.1007/s003590050015 |
| **Yusufçuk** | Fovea sabitlemesi | — | — | — | Avlanma sırasında göz hareketi ve hedef fiksasyonu | Olberg ve ark. 2007, DOI 10.1007/s00359-007-0223-0 |
| **Yırtıcı kuşlar** | — | — | — | — | Yoğun av sürülerinde **sabit noktaları** hedefleyerek "confusion effect"ten kaçınıyor | Brighton ve ark. 2022, DOI 10.1038/s41467-022-32354-5 |
| **Şahin (peregrin, fizik simülasyonu)** | — | — | — | — | *"stooping at high speed maximizes catch success"* | Mills ve ark. 2018, DOI 10.1371/journal.pcbi.1006044 |

### (c) Bizim ölçümümüzle kıyas

**1. Kazanç eşleşmesi — bizim ampirik ayarımız şahininkine yakınsamış.**

| | Şahin (Brighton 2019) | Biz (reçete) | Oran |
|---|---|---|---|
| Yasa yapısı | `N·λ̇(t−τ) − K·δ(t−τ)` | `FF·λ̇ + k·(σ−σ_c)` | **aynı** |
| N | 0.7 | 1.0 | 1.43× |
| K | 1.2 s⁻¹ | 1.4 s⁻¹ | 1.17× |
| τ | 0.09 s | 0.375 s | **4.17×** |
| **K·τ** | **0.108** | **0.525** | **4.86×** |

**2. N eşleşmesi — Coenosia rejimindeyiz ve N'imiz onunki.**

| | Coenosia | Biz |
|---|---|---|
| Menzil | çok yakın | terminal ≈4.5 m |
| λ̇ | "aşırı yüksek" | **50-100 °/s** ölçüldü |
| N | **≈1.5** | `PN_N = 1.6` |
| Gecikme | 18 ms | **200-250 ms** (11-14×) |

Depo N taramasında yaylayı 1.4-1.6'da bulmuş; biyoloji aynı yaylada. Bu, N'i yükseltme dürtüsüne karşı **bağımsız bir kanıttır**.

**3. Yusufçuk: iki ders, biri bizde yok.**
- **Ders 1 (bizde var):** Olberg'in "retinadaki görüntü hareketini minimize et" tanımı, bizim `eps → 0` hedefimizle aynıdır ve **paralaks gerekmiyor** — yani menzil bilgisi olmadan da yönlendirme mümkün. Bu, bbox-only yaklaşımımızın biyolojik meşruiyetidir.
- **Ders 2 (bizde YOK):** Mischiati'nin bulduğu ayrım — **baş** avı sürekli takip ediyor, **gövde** ise iç modelle yönlendiriliyor; görme yalnız **beklenmedik** av hareketlerine tepki için kullanılıyor. Bizim karşılığımız `BURUN_LOS` ayrımıdır (`bbox_ibvs.py:546-554`: *"Füzede arayıcı başlık hedefe bakar, gövde PN uçar — iki ayrı iş"*) ve ölçümümüz bu ayrımın **zorunlu** olduğunu söylüyor: tek başına burun 0/40, PN ile birlikte **29/40**. Yani yusufçuğun baş/gövde ayrımı bizde ölçülmüş bir gereklilik. **Eksik olan "iç model" kısmı:** hedefimiz **sabit bir oval** (220×96 m, 29.63 s tur) ve asla kaçmıyor — yani öğrenilebilir bir yörünge. Yusufçuğun yaptığı tam olarak budur.

**4. Şahinin "hızlan" dersi bize transfer OLMUYOR — türetmesi.**
Mills ve ark. (2018) yüksek hızda dalışın yakalama başarısını maksimize ettiğini gösteriyor. Sebebi aerodinamiktir:
```
Şahin:      a = ½ρV²S·C_L/m ∝ V²  →  r = V²/a = sabit,  ω = V/r ∝ V
Quadrotor:  a = sabit (12 m/s²)   →  r = V²/a ∝ V²,     ω = a/V ∝ 1/V
```
**Yani hız arttıkça şahinin dönüş hızı ARTAR, bizimki AZALIR.** Optimumlar birbirinin tersidir. Bu, Soru 3'teki M1 önerisinin (dönüş bütçesi) biyolojik gerekçesidir ve Bhattacharya'nın (2021) "quadrotor'da yapılabilen ama füzede yapılamayan" cümlesinin niceliksel karşılığıdır.

**5. Gecikme telafisi biyolojide YOK.** Şahin `λ̇(t−0.09)` ile çalışıyor; sinekler 18-28 ms gecikmeyle. Hiçbiri ileri sarmıyor; hepsi kazanç–gecikme çarpımını yönetiyor. Bizim 2.3° → 5.4° ölçümümüzle tam uyum.

### (d) Somut öneri ve beklenen kazanç

| Öneri | Ne | Beklenen kazanç |
|---|---|---|
| **Ö-8.1** | `AVCI_DPP_FF` 1.0 → **0.7** (= Ö-3.2). Şahinin uydurulan N'i | Talep 39.4 → 30.9 °/s (−%21.6) |
| **Ö-8.2** | **Hedefin sabit ovalini öğren** (yusufçuğun iç modeli): 220×96 m, 17.99 m/s, tur 29.63 s. GPS fazında toplanan izden oval parametrelerini kestir; görsel fazda kutu yokken **ölü hesap yerine model tahmini** kullan | Şu an kör karede son komut tekrarlanıyor → 56.4° medyan hata. Oval modeli 1.9 s'lik kayıp penceresinde hedefin nerede olduğunu **±birkaç metre** verir. Barisic ve ark. 2021 aynı fikri (Bernoulli lemniskatı) kullanıp sahada 9/12 başarı almış |
| **Ö-8.3** | Baş/gövde ayrımını **koru ve derinleştir**: burun yalnız hedefe bakar (kadrajda tutma), gövde yasayla uçar. `BURUN_KD` aç (= Ö-7.1) | Ölçülmüş: burun tek başına 0/40, yasayla birlikte 29/40 |

### (e) Riskler / çürütme

- **Ö-8.2 en büyük fikirsel sıçrama ama en riskli:** Barisic'in başarısı **stereo** kamerayla 3B konum ölçtüğü içindi; bizim menzilimiz vekil ve %41 şişik, dolayısıyla oval uydurmasının 3B kalitesi düşük olur. Ayrıca hedef "asla kaçmıyor" bilgisi **yarışma senaryosuna özgü olabilir** — gerçek bir önleyici için aşırı uyum (overfit) riski taşır. Yarışma bağlamında meşru, genel çözüm olarak değil.
- **Ö-8.1'in biyolojik gerekçesi kusurlu olabilir:** şahinin N=0.7'si onun kendi hız/ivme zarfına göre ayarlıdır. Bizim ivme tavanımız (12 m/s²) şahininkinden farklıdır. Kazanç ödünç almak yerine **doygunluk oranını hedef almak** daha sağlamdır: hedef "doygun kare oranı < %45", FF değeri o hedefi tutturan sayı olsun.
- **Biyoloji literatürü içinde çelişki:** Fabian (2018) DPP'yi açıkça reddediyor, Brighton (2019) karma PN+PP'yi savunuyor. Kaydedilmiştir (Soru 3/e).

---

## 9. ÇELİŞEN KAYNAKLAR — kayıt

| # | Çelişki | Taraflar | Çözüm / durum |
|---|---|---|---|
| Ç1 | **DPP geçerli mi** | Fabian 2018: "yalnız PN açıklıyor, PP ve DPP reddedildi" ↔ Brighton & Taylor 2019: karma PN+PP her iki saf yasayı da yeniyor (0.34 vs 0.46/0.51 m) | Rejim farkı: sinekler açık gökyüzü/uzak menzil, şahinler yakın menzil/karmaşık. **Bizimki şahin rejimi.** Çözülmedi, kayıt altında |
| Ç2 | **Gecikme telafisi işe yarar mı** | Yan 2024: DKF ile CEP 0.332 → 0.089 m ↔ Bizim ölçüm: ileri sarma 2.3° → 5.4° | Farklı yer: **kestirici tarafı** vs **girdi tarafı**. Çelişki değil, ayrım |
| Ç3 | **N ne olmalı** | Füze pratiği 3 ≤ N ≤ 5 ↔ Peregrin N<3 ↔ Coenosia N≈1.5 ↔ Şahin N=0.7 | Menzil/λ̇ rejimine bağlı. Yakın menzil + yüksek λ̇ → düşük N. **Bizimki düşük N rejimi** |
| Ç4 | **Hızlı mı yavaş mı** | Mills 2018 (şahin): yüksek hız yakalamayı maksimize eder ↔ Bizim türetme: quadrotor'da `ω ∝ 1/V` | Aerodinamik fark (`a ∝ V²` vs `a = sabit`). **Şahin dersi bize transfer olmuyor** |
| Ç5 | **Depo içi: PN mi DPP mi** | Kod varsayılanı `PN_N = 1.6`, `DPP_K = 0` (`bbox_ibvs.py:383,395`) ↔ Tüm reçeteler `AVCI_IBVS_PN=0`, `AVCI_DPP_K=1.4` | Hangi ölçümün hangi rejime ait olduğu **kayıt altına alınmalı** |
| Ç6 | **Depo içi: 160.0 vs 202.6** | `MENZIL_PX_M = 202.6` (`:688`) ↔ terminal nişan kapısı `160.0` (`:1938`) | Kapı %21 gevşek. Tutarsızlık |
| Ç7 | **Depo içi: atalet köprüsü** | İlk A/B: köprü işe yaramadı (68.3/64.4/82.3°) ↔ İkinci ölçüm: en büyük tekil kazanç (12.12 → 2.81 m) | Ölçüm gücü: aynı ayarla iki koşu arasında **25° fark**, etkin örneklem ~10 |
| Ç8 | **Depo içi: YAW_HIZALA_S** | Süpürme mekanizmayı doğruluyor (λ̇ şişmesi 6.9 → 4.4 → 3.2×) ↔ "yanlış büyüklükte" (45 ms, p90 bayatlık 1.17 s) | İkisi de doğru: gerçek mekanizma, yanlış hastalık |
| Ç9 | **Tezgâh güvenilirliği** | Tezgâh PN'i açık ara kazanan ilan etti (0.15 m / 370-510) ↔ Oyunda dört ayar da ~19.5 m | `sim/tesis.py:kadraj()` tanım gereği tam LOS veriyor → **ölçüm hatası üretemiyor**. Tezgâh üç kez sahte bulgu üretmiş |

---

## 10. ÖNCELİK SIRASINA DİZİLMİŞ, TEK DEĞİŞKENLİ DENENEBİLİR ÖNERİ LİSTESİ

> **Kural:** her satır TEK değişken. Her kola serpiştirilmiş taban tekrarı (iki taban farkı kollar arası farktan büyükse tüm kampanya geçersiz). Mekanizma kapısı sağlanmayan deney **GEÇERSİZDİR**.

### Ö1 — M1 DÖNÜŞ BÜTÇESİ (hız ile dönüş yarıçapı takası)
- **Gerekçe:** quadrotor'da `ω = a/V`; ölçülen doygunluk **%54.1**; hedefin dönüş yarıçapı 27.1 m, bizimki 27.7 m → içine giremiyoruz. 18 m/s'de yarıçapımız 27.0 m, 15 m/s'de **18.8 m**.
- **Literatür:** Bhattacharya 2021 (arXiv:2107.01733) — quadrotor'un füzede olmayan serbestliği; Ghose 2024 (DOI 10.2514/6.2024-1988) değişken hızlı PN; Mills 2018 (DOI 10.1371/journal.pcbi.1006044) ters yönde kontrast.
- **Env kapısı:** `AVCI_IBVS_DONUS_BUTCE=0.9`, `AVCI_IBVS_DONUS_VTABAN=18` (ilk tur; ikinci turda 15). Kontrol kolu: `DONUS_BUTCE=0`.
- **Mekanizma kapısı:** logda `V_tavan < V_TOPLAM_MAX` olan tik oranı **>%20** olmalı; ayrıca `v_cmd` ile gerçekleşen `v` arasındaki gecikme <1.0 s olmalı (hız kanalı tau 0.72-0.93 s). Sağlanmazsa **geçersiz**.
- **Başarı ölçütü:**
  - Birincil: DÖNÜŞ kolunda (w ≥ 15 °/s) kapanma hızı **−0.84 m/s → > 0**
  - İkincil: DÖNÜŞ CPA medyanı **6.43/5.92 m → < 4.5 m**
  - Koruma: DÜZ kolunda P(CPA<3 m) **0.650'nin altına DÜŞMEMELİ**
  - Doygunluk: %54.1 → **<%35**
- **Risk:** 15 m/s'de μ = 1.20 > 1, hedeften geri kalırız. Bu yüzden ilk tur taban 18 m/s (μ = 1.00).

### Ö2 — conf EŞİĞİ HİZALAMA (0.35 → 0.25)
- **Gerekçe:** ölçülmüş — 1713 kare (%5.6) bu bantta ve kilit kırılmalarının **%17.4'ünü** tek başına yapıyor. Hizalama ≥5 s epizod **43 → 57 (+%32.6)**.
- **Literatür:** ByteTrack (arXiv:2110.06864) — düşük skorlu kutuyu izleyici benzerliğiyle doğrula; 9 izleyicide IDF1 +1..+10 puan.
- **Env kapısı:** `AVCI_KILIT_CONF=0.25` **ve** `AVCI_IBVS_CONF=0.25`. Kontrol: 0.35.
- **Ön koşul (deneyden ÖNCE ölç):** yeni kabul edilen kutuların yanlış-pozitif payı `p`. **`p ≥ 0.361` ise deneme.** (Başabaş: `p·141.6° + (1−p)·8.3° = 56.4°`.)
- **Mekanizma kapısı:** 0.25 ≤ conf < 0.35 bandındaki kutuların yasa tarafından kullanıldığı logda görünmeli (kare sayısı > 0).
- **Başarı ölçütü:** ≥5 s kesintisiz epizod **43 → ≥55**; gerçek tespitli karelerde kerteriz hatası medyanı 8.3°'den **%50'den fazla artmamalı**.

### Ö3 — DPP_FF 1.0 → 0.7 (şahinin N'i)
- **Gerekçe:** λ̇ talebin **%72'sini** oluşturuyor ve λ̇ tahminimiz 3.2-5.9× şişik. Talep 39.4 → 30.9 °/s (tavan 31.8).
- **Literatür:** Brighton & Taylor 2019 (DOI 10.1038/s41467-019-10454-z) N=0.7; Fabian 2018 (DOI 10.1098/rsif.2018.0466) yüksek λ̇'da düşük N.
- **Env kapısı:** `AVCI_DPP_FF=0.7`. Kontrol: 1.0.
- **Mekanizma kapısı:** logda `FF·λ̇` teriminin komuta katkısı medyanı **≥%25 düşmeli**.
- **Başarı ölçütü:** doygun kare oranı **%54.1 → <%45**; DÖNÜŞ CPA düşmeli; DÜZ P(<3 m) 0.650'nin altına inmemeli.

### Ö4 — M2 ARAÇ GECİKME TELAFİSİ (çıkış tarafı)
- **Gerekçe:** ölçülen ıska ayrıştırmasında **%38.3** pay (−16.4°); `tau_arac = 0.57 s` ölçüldü.
- **Literatür:** girdi tarafı öngörüleme reddedildi (bizim 2.3→5.4° ölçümümüz + Brighton'ın gecikmeli-girdi yasası); çıkış tarafı ileri besleme farklı ve meşru (Nesline & Zarchan 1983, DOI 10.2514/6.1983-2170).
- **Env kapısı:** `AVCI_IBVS_ARAC_TAU=0.35`, `AVCI_IBVS_ARAC_TAU_MAX=25`. Kontrol: 0.
- **Mekanizma kapısı:** `tau·w_uyg` düzeltmesinin uygulandığı tik oranı **>%30**; **ve** `psi_v` durumunun öngörülemesiz kaldığı invaryantı loglanmalı (yoksa pozitif geri besleme).
- **Başarı ölçütü:** DÖNÜŞ karelerinde hız vektörü sapması **16.4° → <10°**; DÖNÜŞ CPA düşmeli.
- **Kısıt:** **yalnız DPP kolunda** denenmeli (PN kolunda `lead_az` ile çift sayar).

### Ö5 — ROI KROP (algı geri çağırma)
- **Gerekçe:** kopmaların **%49.8'i "kutu yok"**; truth hedefin %90-93 kadrajda olduğunu söylüyor → kayıp **geri çağırma**. 50-60 m'de yalnız %24 kutu.
- **Literatür:** SAHI (arXiv:2202.06934) +5-7 AP yalnız çıkarımda; uyarlanabilir dilimleme (arXiv:2604.19233) süreyi %20-25 **düşürüyor**; irtifaya duyarlı döşeme (arXiv:2511.19728) küçük nesnede **+%38 mAP**.
- **Env kapısı:** `AVCI_KROP=1`, `AVCI_KROP_BOYUT`, `AVCI_KROP_BAYAT`. Kontrol: `AVCI_KROP=0`.
- **Mekanizma kapısı (SERT):** `det_ms` p95 **70 ms'i AŞMAMALI** ve fps **13'ün altına düşmemeli**; aşarsa λ̇ penceresi (0.25 s) bozulur → **deney geçersiz**. Ayrıca krop kullanılan kare oranı >%50.
- **Başarı ölçütü:** 30-40 m'de kutu oranı **%57 → >%70**; 50-60 m'de **%24 → >%35**; kesintisiz epizod medyanı **0.47 s → >0.8 s**.
- **Not:** SAHI (`AVCI_SAHI`) **denenmemeli** — 2×2 dilimleme det_ms'i 164-280 ms yapar, döngü ölür.

### Ö6 — TERM_DIKEY RAMPASI (terminal nişan ofsetini sıfıra sür)
- **Gerekçe:** ölçülen VISUAL CPA `dz` medyan **+0.96 m** (hedefin üstünden geçiyoruz), `|dz|` 1.19 m; sim taraması 12 vekil m eşiğinde **0.82 m** (kapalı 1.04) veriyor.
- **Literatür:** He, Su & Su 2026 (DOI 10.1109/TAES.2026.3672747) ZEM/ZEAE'nin terminalde sıfıra yakınsaması; Kim 2019 (DOI 10.2514/6.2019-1927) "error convergence **before** interception".
- **Env kapısı:** `AVCI_IBVS_TERM_DIKEY=17` (vekil m ≈ 12 gerçek m). Kontrol: 0.
- **Mekanizma kapısı:** `nisan_cy` çıktısının `CY_NISAN`'dan saptığı kare oranı **>%20**; sapma `NISAN_KAYMA_MAX=120 px`'e **doymuş olmamalı**.
- **Başarı ölçütü:** VISUAL CPA `|dz|` **1.19 → <1.00 m** ve `dz` medyanı **+0.96 → <+0.60 m**.
- **Sıralama kuralı:** `AVCI_ACCEL_SPLIT` **bundan SONRA** denenir. Depo uyarısı: yalnız-split `|dz|` 1.09→1.04 ama medyan **+0.21 → +0.64** (daha kötü).

### Ö7 — KÖPRÜ SÜRESİ 1.5 → 1.8 s
- **Gerekçe:** yapısal kapı `KAYIP_M/31 Hz = 1.9 s`; şu anki 1.5 s bunun altında.
- **Literatür:** OC-SORT (arXiv:2203.14360) — uzun ölü hesabın hata biriktirdiği; **ama** bizim köprümüz sıfırıncı derece (türev yok), doğrusal ekstrapolasyon değil.
- **Env kapısı:** `AVCI_IBVS_KOPRU_ATALET=1.8`. Kontrol: 1.5.
- **Mekanizma kapısı:** `kopru=1` karelerin süre dağılımında **>1.5 s kuyruk** görünmeli.
- **Başarı ölçütü:** faz ömrü **3.92 s'den artmalı** VE en yakın geçiş **2.81 m'den kötüleşmemeli**.
- **Zehirlilik sınırı (hesaplandı):** köprü boyunca kerteriz kayması `ω_hedef × T`. T=1.8 s → medyan dönüşte 11.8° ✅, p90 dönüşte **57.6°** (kadraj sınırı 61°) ⚠. Dönüş rejiminde ayrı bakılmalı.

### Ö8 — BURUN_KD 0 → 0.09 s (kadrajda tutma türev öncülemesi)
- **Gerekçe:** tespit kaybı merkezde 0.036, 39°+ **0.609** (17×); fazların %64.7'si hedef kadrajdayken ölüyor; burun kanalı 46 ms ölü + 211 ms gecikme.
- **Literatür:** Yan ve ark. 2024 FOV-tutma PD (`kp=0.03, kd=0.01`, oran 0.33 s); Falanga ve ark. PAMPC (arXiv:1804.04811) görünürlüğü maksimize + görüntü düzlemi hızını minimize; Tardioli ve ark. 2017 (DOI 10.2514/6.2017-1013) PN'in görünürlük artırımı.
- **Env kapısı:** `AVCI_IBVS_BURUN_KD=0.09`. Kontrol: 0.
- **Mekanizma kapısı:** `BURUN_KD·eps_hızı` teriminin burun komutuna katkısı medyanı **>2°** olmalı; **ve** ayna bekçisi geçmeli (`|Δyaw − yaw_cmd|` medyanı `|Δyaw + yaw_cmd|`'den **küçük** olmalı).
- **Başarı ölçütü:** ölüm anındaki `|eps|` medyanı **52° → <45°**; faz ömrü artmalı.

### Ö9 — DPP_K 1.4 → 1.0 (faz payı)
- **Gerekçe:** deponun PM=60° türetmesi ölçülen **0.28 s yaw kutbunu** saymıyor; gerçek PM **38.5°**. k=1.0'da PM **52.9°**.
- **Env kapısı:** `AVCI_DPP_K=1.0`. Kontrol: 1.4.
- **Mekanizma kapısı:** `k·σ` teriminin komuta katkısı **≥%25 düşmeli**.
- **Başarı ölçütü:** `w_uyg`'nin işaret değiştirme sıklığı (salınım vekili) düşmeli; doygunluk düşmeli; CPA kötüleşmemeli.
- **Kısıt:** Ö3 (FF) ile **aynı kampanyada olmaz** — ikisi de doygunluğa saldırıyor.

### Ö10 — DPP_SIGMA_C = 15° (sabit geometrik bias)
- **Gerekçe:** μ=0.833 ile kesme geometrisi `sin σ = μ·sin(aspect)` → aspect 132.7°'de **37.7°**, 73.8°'de **53.1°** lead ister; seyir tavanımız **9°**. Aspect 150-180° bandında **191 denemede 0 vuruş**.
- **Literatür:** Shima 2007 (DOI 10.2514/6.2007-6782); Livermore & Ratnoo 2018 (DOI 10.2514/1.G003179); Kumar & Ghose 2019 (DOI 10.2514/1.G004284).
- **Env kapısı:** `AVCI_DPP_SIGMA_C=15`. Kontrol: 0.
- **Mekanizma kapısı:** `σ − σ_c` hata sinyalinin medyanı `σ`'nın medyanından **ölçülebilir şekilde farklı** olmalı.
- **Başarı ölçütü:** aspect@30 m medyanı **132.7° → <110°**; DÖNÜŞ kapanma hızı iyileşmeli.
- **Güçlü karşı-kanıt:** depo lead tavanını yükseltmeyi ölçtü ve **kötü** çıktı (en yakın 2.1 → 13.2/10.0 m). Ayrımım (sabit geometrik bias ≠ oran tabanlı lead) **kanıtlanmamıştır**. Bu yüzden liste sonunda ve küçük değerle.

### ALTYAPI (deney değil, ön koşul)
| # | İş | Neden |
|---|---|---|
| **A1** | **Yaw bayatlığını çöz** — tiklerin %59.4'ü bayat, p90 1.17 s, max 7.47 s | λ̇ şişmesinin ikinci büyük kaynağı (5.0×). Çözülmeden Ö3/Ö9'un ayrım gücü düşük. Kapı: bayat tik oranı **<%10** |
| **A2** | `bbox_ibvs.py:1938`'deki `160.0` → `MENZIL_PX_M` | Terminal nişan kapısı %21 gevşek çalışıyor. Tutarsızlık düzeltmesi |
| **A3** | **Ayna bekçisi**: her koşuda `\|Δyaw − yaw_cmd\|` vs `\|Δyaw + yaw_cmd\|` logla | Bu hatanın üçüncü tekrarıydı; imza mutlak (107.6° vs 10.2°), maliyet sıfır |
| **A4** | Menzil modelini `w^0.15·h^0.85`'e geçir (bayrak arkasında, kapıları eski sabitle besleyerek) | Vekil/truth 1.41, 3-6 m'de 2.13×; model hatayı %21 → %6.2 yapıyor. Ö6'nın (TERM_DIKEY) doğru çalışması buna bağlı |
| **A5** | Tezgâhın `kadraj()` fonksiyonuna **ölçüm hatası** ekle | Tanım gereği tam LOS verdiği için ölçüm hatası üretemiyor; PN'i yanlışlıkla kazanan ilan etti. Üç kez sahte bulgu üretmiş |

---

## 11. KAYNAK YOK / DOĞRULANAMADI — dürüstlük kaydı

| Konu | Durum |
|---|---|
| Zarchan'ın **"t_go/τ ≥ 10"** kuralı | **KAYNAK YOK.** Nesline & Zarchan 1981/1983 künyeleri doğrulandı ama bu somut sayısal kural erişilebilir hiçbir özet/tam metinde bulunamadı. Kitabın kendisine erişilemedi |
| **`N > 1 + μ`** yakalanabilirlik eşitsizliği (depoda kullanılıyor) | **KAYNAK YOK.** PPN yakalanabilirlik ailesi mevcut (Guelman 1990; Ghosh & Ghose 2013/2014) ama bu tam biçim özetlerden teyit edilemedi |
| Dhananjay, Lum & Xu (2010) "PN with delayed LOS rate" **sonuçları** | Künye doğrulandı (DOI 10.1109/ICCA.2010.5524249) ama **özet erişilemedi** — sonuç cümleleri alıntılanamıyor |
| Strapdown parazitik döngünün **kapalı-form kararlılık eşitsizliği** | Konu literatürü zengin (Du 2010, Jianmei 2011, Yue 2021, Xiao 2023) ama açık erişimli somut eşitsizlik bulunamadı; Xiao 2023 yalnız niteliksel ifade veriyor |
| Oran sınırlayıcının (rate limiter) **describing-function faz kaybı** niceliği | **KAYNAK YOK.** Standart kontrol argümanı olarak sunuldu, sayı verilmedi |
| Yan 2024 ve Pliska 2024'ün **dedektör gecikmesi** değerleri | Kaynaklarda yok; normalize kıyas tablosundaki ilgili satırlar **varsayımlıdır** ve karar dayanağı değildir |
| Bourquardez 2009 ve Hamel/Mahony'nin **tam denklemleri** | Künyeler doğrulandı, tam metinlere erişilemedi (IEEE paywall). Küresel izdüşüm argümanı standart IBVS teorisinden türetilmiştir |
| Vrba & Saska 2019/2020'nin **tespit menzili sayıları** | Künyeler doğrulandı, sayılar alınamadı |
| Rothe 2026'nın **güdüm yasası ve hız** ayrıntıları | MDPI 403 verdi; özet Semantic Scholar üzerinden alındı, tam metin okunamadı |

---

## 12. RAPORUN TEK SAYFALIK ÖZÜ

1. **Yasamız yapısal olarak doğru.** DPP = `k·σ + FF·λ̇`, Harris şahininin ölçülen yasasıyla (`N·λ̇ − K·δ`) aynı; kazançlarımız (1.4 vs 1.2 s⁻¹; 1.0 vs 0.7) şaşırtıcı derecede yakın. Ama gecikmemiz **4.17 kat** ve önemli olan boyutsuz `K·τ` çarpımında **4.86 kat** geridiyiz.
2. **Asıl kısıt yasa değil doygunluk.** Talep 39.4 °/s, tavan 31.8 °/s, %54.1 doygun. Ve quadrotor'da `ω = a/V` olduğu için bunun çaresi ivmeyi artırmak (yok) değil **hızı düşürmek** — depoda yazılı ama hiç ölçülmemiş M1.
3. **Parazitik döngü teşhisi ders kitabı doğruluğunda.** Piksel köprüsü (model hatası) ve ayna (işaret hatası) strapdown literatürünün iki kanonik arızası; atalet köprüsü de kanonik çözümü. Bu üçlü, deponun en sağlam ölçüm zinciridir.
4. **Gecikme telafisi konusunda haklıyız — ama yanlış hastalığı tedavi ediyoruz.** Girdi tarafı ileri sarma hem bizde hem biyolojide reddediliyor. Gerçek hastalık **yaw bayatlığı** (tiklerin %59.4'ü, p90 1.17 s).
5. **Algı sürekliliğinde literatürün cevabı hazır ve ölçülebilir.** Düşük eşikli kutuyu at**ma** (başabaş noktası hesaplandı: yanlış payı **%36'nın altındaysa kazanç**), ROI ile geri çağırmayı yükselt.
6. **Terminal fazımız balistik.** Kapalı çevrim zaman sabiti 1.20-1.46 s, terminal t_go 2.2-2.7 zaman sabiti (manevrada tanımsız). Sonuç **30 m'de** belirleniyor (aspect Cliff δ = −0.81). Kaldıraç terminalde değil, taahhüt anındaki geometride.
7. **Kıyasta yerimiz dürüst:** mutlak sayıda geride (0.55-1.2 m vs 0.089-0.16 m), ama hıza ve algı gecikmesine normalize edildiğinde rekabetçi — ve literatürde **mono-bbox-only ile 20+ m/s'de metre-altı önleme bildiren başka çalışma yok.**

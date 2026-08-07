# KÖPRÜ DENETİMİ — köprü, ArduCopter'ın yerini doğru alıyor mu?

**Tarih:** 2026-08-06 · **Kaynak:** U koşusu (gerçek GPS, `RANGE_SET=6.9`, `ISTASYON_ELEV=15`, `IC_KAYMA=0`,
`V_MAX=22`, `KP_H=0.8`) — `veri/kopru_angajman_U_20260806_214418.csv` (n=10880, 3 bölüm)
+ `kopru/gazebo_kaynak/logs/gps_guidance_20260806_2144-2146*.csv` (n=1478/bölüm).
> ⚠️ 2026-08-07'de `ISTASYON_ELEV_DEG` 15→25 yapıldı (dikey ayrım 1.71→2.89 m).
> Bu denetimin bulguları (çeviri, limitler, zamanlama, teslimat) o değişiklikten
> BAĞIMSIZDIR; yalnız §B5/§E'deki kadraj sayıları 15° geometrisine aittir.

**Yöntem:** salt ölçüm, **kod değiştirilmedi**. Zincirin her adımı yasanın kendi
çıktısından BAĞIMSIZ olarak yeniden hesaplandı, sonra karşılaştırıldı.

## HÜKÜM

> **Köprü, ArduCopter'ın yerini doğru alıyor.** Çerçeve/birim çevrimi bit düzeyinde
> doğru (sapma 0.00 m), yasanın komutu köprüye kayıpsız geçiyor (0.013 m/s), köprünün
> hiçbir yatay limiti yasanınkinden önce bağlamıyor, teslimat %99.5, hedef kadrajın
> merkezinde (AV kutusu içinde %100) ve yaw kaçağı yok (75 sn'de 3.6°). Tek yapısal
> eksik **jerk şekillendirme**; ölçüm bu turda zarar vermediğini gösteriyor.

---

## A) TEK KARE UÇTAN UCA İZ — **GEÇTİ**

Oturmuş fazdan 3 kare; her adım bağımsız hesaplanıp yasanın/köprünün ürettiğiyle
karşılaştırıldı.

| Adım | Kare 1 | Kare 2 | Kare 3 | Sapma |
|---|---|---|---|---|
| 1→2 DoW ham → NED (`dow_kopru.py:368-380`) | (−188.37, +2411.26, −43.21) | (−39.56, +2386.89, −40.26) | (−132.24, +2348.02, −38.54) | **(0.00, 0.00, 0.00)** |
| 2→3 istasyon (`gps_guidance.py:395-397`) | (−188.30, +2411.21, −43.47) | (−39.36, +2387.07, −40.22) | (−132.80, +2347.29, −38.70) | **≤0.01 m** |
| 3→4 komut (`gps_guidance.py:440-459`) | (−7.95, +15.49, −1.21) | (+12.50, −12.49, +0.72) | (−14.10, +12.83, −1.11) | **0.01-0.03 m/s** |
| 4→5 stick (`dow_kopru.py:478-506`) | — | pitch +0.179 / roll −0.037 | pitch +0.229 / roll −0.041 | **TAM EŞLEŞME** |
| 5→6 gerçekleşen (+110-125 ms) | — | \|v\|=18.44 ↔ komut 17.64 | \|v\|=18.26 ↔ komut 19.02 | ~%4 |

**Havuzlanmış (tüm oturmuş faz):** `iris_z` sapması medyan **0.0030 m** (maks 0.060) ·
komut sapması medyan **0.0130 m/s** (p95 0.033) — CSV'nin 2 ondalık yuvarlamasıyla uyumlu.

**Yorum:** 2↔3 arası çeviri hatası **yok**; 4↔5 arası köprü hatası **yok** (stick birebir);
5↔6 arası takip %4 içinde (birinci mertebe tesis + 110 ms gecikme ile beklenen).

---

## B) `get_iris` DENETİMİ

**B1 — Alan kaynakları — GEÇTİ.** `_drone_dow()` (`dow_kopru.py:345-350`) tek kaynak:
`sdk.get_telemetry()["drone"]` → `position` (cm→m), `velocity` (cm/s→m/s),
`rotation` (derece→radyan, satır 350). `get_iris` (satır 368-380) bunları NED'e çevirir.

**B2 — `iris["z"] = −(irtifa − zemin)` — GEÇTİ.** Bağımsız kontrol: sapma medyan
**0.0030 m**, maks 0.060 (satır 378; `NED_ZEMIN_M=48.4`).

**B3 — HIZ TUTARSIZLIĞI — VAR ama ÖLÜ ALAN (GEÇTİ).**
Tutarsızlık gerçek: `get_iris` üç eksende de **SDK velocity** verir (satır 373), köprünün
kendi dikey döngüsü ise **konum sonlu-farkını** kullanır (satır 470, `HIZ_KAYNAK="sonlu_fark"`
satır 183). **Ama yasa `iris["vx","vy","vz"]`'yi HİÇ OKUMAZ** — `gps_guidance.py:290-293`
yalnız `x, y, z` ve `roll/pitch/yaw` alır; `vel_x/y/z` (satır 244, 316) **hedefin** hızıdır,
drone'un değil. Dolayısıyla alan ölü.
Sayısal olarak da zararsız: 1 s tabanlı irtifa türevine göre sapma **SDK +0.001 m/s**,
**sonlu-fark −0.003 m/s** (std 0.71 / 0.70) — iki kaynak da yansız.

**B4 — `iris` hızı ↔ gerçek hız — GEÇTİ.** Yatay: \|v\|_SDK medyan 18.43 ↔ konum türevi
18.39 m/s → sapma **+0.055 m/s**, std 0.83.

**B5 — roll/pitch/yaw — GEÇTİ (2026-08-06'da işaret de DOĞRULANDI).**
Derece→radyan yapılmış (satır 350) ✓. **pitch işareti çevrilmemiş** (bilinçli karar,
dosya başlığı madde 2) ve bu **DOĞRU** çıktı. Yasa bu üçünü yalnız
`gps_guidance.py:466`'da `hedef_kadraj_hatasi()` ölçümüne verir (komuta girmez), ama o
ölçüm E maddesinin geçme ölçütü olduğu için işaret ayrıca doğrulandı:

1. **DoW konvansiyonu:** ileri itki komutu (pitch stick medyan +0.208 = +12.5°) altında
   bildirilen gövde pitch'i **−12.50°**, korelasyon **−0.843** → burun aşağı gidiyor ve
   NEGATİF bildiriliyor ⇒ konvansiyon **burun-yukarı pozitif = NED ile aynı** ⇒ aynen
   geçirmek doğru. (Büyüklük de tutuyor: stick·60 = 12.5° ↔ bildirilen 12.5°.)
   Roll: korelasyon **−0.965** (aynı tutarlılık).
2. **Attitude'dan BAĞIMSIZ kilit sınama:** LOS yükselişi iki ayrı yoldan —
   gövde çerçevesi (attitude'lu) **+25.98°**, dünya çerçevesi (yalnız konumlardan,
   attitude'suz) **+13.87°**. Fark **+11.93°**; bildirilen pitch **−12.50°**.
   `elev_gövde = elev_dünya − pitch` hipotezinin medyan artığı **0.39°**,
   ters hipotezinki **24.40°** (korelasyon +0.885 ↔ −0.885). ⇒ **İŞARET DOĞRU.**
3. **Formül çapraz kontrolü:** kendi bağımsız DCM çözümüm ile yasanın çıktısı —
   yaw sapması **−0.009°**, elev sapması **+0.0003°** (maks 0.19°).

**B5-roll — KALDI (işaret TERS), etkisi ölçüldü: küçük.**
Aynı akıl yürütme roll için tersini veriyor. Ölçüm (U, oturmuş faz, n=984):
korelasyon(stick, bildirilen) **−0.965**; sola yatış komutunda (stick<0, n=733)
bildirilen roll **+4.70°**, sağa yatışta (n=3) **−0.70°**; büyüklük tutuyor
(\|stick\|·60 = 4.55° ↔ \|bildirilen\| 4.65°), regresyon eğimi **−55.0°/stick**
(beklenen büyüklük 60, işaret negatif). Yani **sağa yatışta DoW NEGATİF bildiriyor**;
NED/FRD'de sağ kanat aşağı = POZİTİF ⇒ **DoW roll = −NED roll**. `get_iris`
(`dow_kopru.py:380`) roll'ü **aynen geçiriyor** ⇒ yasa ters işaretli roll alıyor.
(Pitch'in aynen geçmesi doğru, roll'ünki değil — Unreal'in sol-el konvansiyonuyla
tutarlı bir asimetri.)
**Etkisi:** roll yalnız kadraj ÖLÇÜMÜNE girer (komuta değil) ve araç neredeyse düz
uçtuğundan (\|roll\| medyan 4.7°) etki küçük: roll çevrilince kadraj konumu
u 0.4712 → 0.4859, v 0.4896 → 0.4789; fark medyan **\|Δu\|=0.013**, **\|Δv\|=0.004**
(maks 0.051 / 0.056). **AV kutusu içinde kalma her iki durumda da %100** — E'nin
sonucu ayakta. Düzeltme yapılmadı (kural gereği).

---

## C) KÖPRÜ EKSİKLİK DENETİMİ

| ArduCopter bileşeni | Köprüde | Not |
|---|---|---|
| (1) Jerk-sınırlı kinematik şekillendirme (WPNAV_JERK=4) | **YOK** | aşağıda |
| (2) Hız PID → ivme | **VAR** (farklı yapı) | trim ileri-besleme + PI (`:478-501`); ivme ara değişkeni yok |
| (3) İvme → yatış açısı | **VAR** (ölçülmüş eşleme) | `yatay_trim_stick` — DoW'da ölçülen hız↔stick eğrisi (`:488-491`) |
| (4) Dikey kaskad | **VAR** | TRIM + FF + PI (`:508-517`) |
| (5) Yaw denetleyicisi | **VAR** | P + sarma + kaçak kırpma (`:519-526`) |

**(1) JERK — KALDI (yapısal eksik), etkisi ölçüldü: bu turda zararsız.**
Komut ivmesinin türevi: medyan **11.3**, p95 **204**, maks **244 m/s³** (ArduCopter'ın
WPNAV_JERK=4'üne karşı). Yüksek değerler komut **yönünün** dönmesinden geliyor (büyüklük
basamağından değil); araç dinamiği + köprünün slew limiti bunu emiyor — D maddesinde
teslimat %99.5 ve A'da takip %4. Düzeltme **yapılmadı** (kural: önce rapor).

**Limit bağlama — hangisi önce bağlıyor?**

| Limit | Bağlama oranı |
|---|---|
| KÖPRÜ \|pitch\| ≥ 0.749 | **%0.00** |
| KÖPRÜ \|roll\| ≥ 0.749 | **%0.00** |
| KÖPRÜ thr ≥ 0.699 (THR_UP) | **%0.00** |
| KÖPRÜ thr ≤ −0.999 (THR_DN) | %4.39 |
| KÖPRÜ rate-limit pitch (\|Δ\| ≥ 0.0499) | **%0.00** |
| KÖPRÜ rate-limit **throttle** | **%42.42** |
| YASA \|v_cmd\| ≥ 21.9 (V_MAX) | %5.62 |
| YASA \|vz_cmd\| ≥ 5.97 (VZ_MAX) | %3.25 |
| YASA ivme ≥ 11.9 (MAX_ACCEL) | %60.05 |

**Yatay: GEÇTİ** — köprünün hiçbir yatay limiti bağlamıyor; yasa istediğini tam alıyor.
**Dikey: GEÇTİ (etki yok), yapısal DİKKAT** — throttle slew'i tiklerin %42'sinde bağlıyor
(`MAX_DELTA=0.05`/tik, `dow_kopru.py:153,557-565`), THR_DN tabanı %4.4. Buna rağmen dikey
teslimat **%101-102** (D maddesi), yani performansı kısıtlamıyor; yasanın kendi
`MAX_ACCEL`'i zaten %60 bağlıyor.

---

## D) SİSTEMATİK EKSİK TESLİMAT — **GEÇTİ**

- **Yatay** \|v_gerçek\| / \|v_komut\| (oturmuş faz): medyan **0.9945**
  (p10 0.927 · p90 1.055) → sistematik eksik **%0.5**.
- **Dikey** (ayrı): tırmanma **1.021** (n=466) · alçalma **1.012** (n=396) — ikisi de
  hafif **fazla** teslim. Faz-1'deki %97/%89 açık-döngü basamak testiydi; kapalı çevrimde
  PI kapatıyor.
- U'daki alt bileşeni 1.65-1.71 m ↔ tasarım 1.79: istasyonun **kendi** alt bileşeni
  1.73-1.79 ölçüldü (menzil < RANGE_SET olduğunda `r_eff` küçülmesi, `gps_guidance.py:383-385`);
  drone onu 0.08-0.13 m içinde izliyor. **Alçalma açığından gelmiyor.**

---

## E) YAW / KADRAJ — **GEÇTİ**

1. **\|cmd_yaw − gerçek_yaw\|:** medyan **2.60°**, p95 **13.78°**.
2. **Kadraj** (yasanın kendi `hedef_kadraj_hatasi` çıktısı): \|yaw hatası\| medyan **7.0°**;
   LOS yükselişi medyan **+26.0°** ↔ kamera tilt 25° → **dikey sapma yalnız +1.0°**.
   Normalize yatay konum **u = 0.471** (merkez 0.5; p10-p90 = 0.423-0.503),
   **AV kutusu (%25-75) içinde %100**, hedef önde %100.
   **DoW GEOMETRİSİYLE YENİDEN HESAPLANDI** (B5 doğrulaması sonrası, Gazebo'nun 4:3
   modeli yerine DoW 16:9 + HFOV 125° + VFOV yarı 47.2°): kamera ekseninden sapma
   yatay **−6.31°** (p5 −17.8 / p95 +1.7), dikey **−1.28°** (p5 −3.8 / p95 +2.1);
   normalize **u = 0.471** (p10 0.423 · p90 0.503), **v = 0.490** (p10 0.473 · p90 0.512).
   **AV kutusu (yatay %25-75 ∧ dikey %10-90) içinde %100.0**; kare dışına çıkma %0.0.
   Yani kilidin iki geometrik ön şartından **kadraj şartı sağlanıyor** — boyut şartını
   (oturma 8.1 m ⇒ kutu %5.5) U koşusu zaten sağlamıştı.
3. **cmd_yaw kaçağı YOK:** 75 sn'de kümülatif cmd_yaw **−612°** ↔ gerçek **−616°** →
   birikme **+3.6°** (`gps_guidance.py:453-456` kalıcı durumu, köprünün ±90° kırpması
   `dow_kopru.py:521` ile birlikte).

---

## F) ZAMANLAMA — **GEÇTİ**

1. **Yasa dt:** medyan **47.0 ms** → **21.3 Hz** (hedef 20; p5 46, p95 63 — Windows
   15.6 ms zamanlayıcı granülasyonu). Yasa dt'yi gerçek geçen süreden ölçüyor
   (`gps_guidance.py:285-286`), türev/integral bundan etkilenmiyor.
2. **Köprü:** 3609 tik / 75.0 s = **48.1 Hz ortalama** (tasarım 50). Aralık iki tepeli
   (16 ms / 31 ms) — aynı granülasyon. Kopya örnek %0.4.
   *Not:* `MAX_DELTA` tik başına olduğundan slew hızı bu titreşimle ±%25 dalgalanır
   (ortalama tasarıma eşit).
3. **Aliasing YOK:** ardışık yasa tikinde aynı hedef değeri **%0.0** — her tik taze veri
   görüyor, kare atlama gözlenmedi.

---

## ÖZET TABLO

| Madde | Sonuç |
|---|---|
| A) Uçtan uca iz | **GEÇTİ** (çeviri 0.00 m · komut 0.013 m/s · stick birebir) |
| B1 kaynaklar | **GEÇTİ** |
| B2 z çevrimi | **GEÇTİ** (0.003 m) |
| B3 hız tutarsızlığı | **GEÇTİ** (var ama ölü alan; iki kaynak da yansız) |
| B4 hız doğruluğu | **GEÇTİ** (+0.055 m/s) |
| B5 pitch işareti | **GEÇTİ** — doğrulandı (artık 0.39° ↔ ters 24.40°) |
| B5 **roll işareti** | **KALDI** — DoW roll = −NED roll, `get_iris` aynen geçiriyor; etki \|Δu\|=0.013 (AV %100 değişmiyor) |
| C) jerk şekillendirme | **KALDI** (yok) — etki ölçüldü, bu turda zararsız |
| C) limit önceliği (yatay) | **GEÇTİ** (%0.00 bağlama) |
| C) limit önceliği (dikey) | **GEÇTİ** (etki yok) — throttle slew %42 bağlıyor, DİKKAT |
| D) eksik teslimat | **GEÇTİ** (%0.5 yatay; dikey fazla teslim) |
| E) yaw takibi / kadraj / kaçak | **GEÇTİ** (2.6° · merkez · +3.6°) |
| F) zamanlama / aliasing | **GEÇTİ** (21.3 / 48.1 Hz · %0.0 aliasing) |

**Düzeltme yapılmadı** (kural gereği). Açık tek kalem: jerk şekillendirme yokluğu ve
throttle slew'in %42 bağlaması — ikisi de ölçülen performansı bozmuyor, karar kullanıcının.

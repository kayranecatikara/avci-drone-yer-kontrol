# DEPO DENETİMİ — "iddia ettiğini yapmayan kod" avı

**Tarih:** 2026-08-16 · **Kapsam:** `avci-drone-yer-kontrol-kayran`
**Kural:** hiçbir dosya değiştirilmedi. Yeni dosyalar: bu rapor + `arac/denetim_kanit.py`.
**Kanıt betiği:** `python arac/denetim_kanit.py` (22 kanıt, hepsi DOĞRULANDI)
`arac/denetim_kanit.py B4` gibi tek tek de koşar. Betik salt-okuma: MAVLink/DoW
bağlantısı kurmaz, thread başlatmaz, `web/server.py`'yi **import etmez**
(import anında `AvciKontrol` kuruyor).

---

## ÖZET

| | |
|---|---|
| Toplam bulgu | **34** |
| Uçuşu doğrudan etkileyen | 8 |
| Sessizce etkisiz (ölü ayar / ezilen ayar) | 14 |
| Kafa karıştıran yorum / ölü kod / yanlış telemetri | 12 |
| Kanıt betiğiyle doğrulanan | 22 |
| Kanıtlayamadığım | 3 (aşağıda ayrı başlık) |
| Test durumu | **338 geçti / 7 kaldı** |

Aranan desen bu depoda **hâlâ üretiliyor**: bugün düzeltilen 7 vakanın
(`DEVIR_BOYUT_PX 24→14`, `KAYIP_M 20→60`, `MENZIL_PX_M 160→202.6`, …) en az
**üçü, düzeltmenin kendisi tarafından yeni bir sessiz etkisizlik doğurdu.**
En pahalı üç bulgu (D1, D2, D3) tam olarak bu türden.

---

## İLK 10 — ciddiyet sırası

Sıra: **uçuşu bozan > sessizce etkisiz > kafa karıştıran yorum**

---

### D1 · İstasyonun dikey ayrımı 1.56 m — deponun kendi "güvenli" eşiğinin ALTINDA

**Dosya:** `guidance/ana_kontrol.py:222` (`KOPRU_RANGE_SET = 9.0`) + `:249` (`KOPRU_ISTASYON_ELEV = 10.0`)

**Ne iddia ediyor:**
`:244-245` — *"10° + RANGE_SET 18 -> 3.13 m alt: doğrulanmış-güvenli 2.92 m'nin ÜZERİNDE"*
`:229-230` — *"15 deg -> 1.79 m alt (ölçülen 1.71) — Talon kanat açıklığı 1.718 m kadar; çarpışma payı YOK (bir koşuda 1.4 m'de çarptı)"*

**Gerçekte ne yapıyor:**
`ELEV = 10°` gerekçesi `RANGE_SET = 18` iken yazıldı. Sonra `:217`'de
`RANGE_SET 18.0 → 9.0` yapıldı ("SÜPÜRÜLDÜ", ıska eğrisinin dibi). O değişikliğin
yorum bloğu **dikey ayrımı hiç anmıyor.** Sonuç:

```
9.0 × sin(10°) = 1.56 m ALT   (ve 8.86 m arka)
```

1.56 m, deponun kendi yazdığı iki eşiğin de altında: "çarpışma payı YOK" dediği
1.79 m'nin ve "KALICI, +%63 pay" diye onayladığı 2.92 m'nin.

**KANIT:** `python arac/denetim_kanit.py B4`
```
RANGE  6.9 x ELEV 15 ->  1.79 m alt   'carpisma payi YOK, bir kosuda 1.4 m'de carpti'
RANGE  6.9 x ELEV 25 ->  2.92 m alt   '+%63 pay' -- KALICI diye onaylanan deger
RANGE 25.0 x ELEV 25 -> 10.57 m alt   gozden kacmis yan etki (bilinen bulgu #2)
RANGE 18.0 x ELEV 10 ->  3.13 m alt   ':244 bu degisiklikte GEREKCE olarak yazildi'
RANGE  9.0 x ELEV 10 ->  1.56 m alt   SIMDIKI
SONUC: 1.56 m < 1.718 m
```
Test çıktısında canlı doğrulama: `[KOPRU-GUDUM] istasyon: 8.86 m ARKA + 1.56 m ALT`.

**Tahmini etki:** GPS fazında, **görsel kilit dolmadan önce** kontrolsüz temas
riski. Bu bilinen bulgu #2'nin (`ELEV=25°` gerekçesi `RANGE_SET=6.9`'a aitti)
**birebir tekrarı** — aynı çift değişkenin öbür yarısı bu sefer düşürüldü.
⚠ Gerçek ıska mesafesini uçuşta ölçemedim; bu, deponun **kendi ölçütüne göre**
bir ihlal.

---

### D2 · `SupCfg.KAYIP_M = 60` her görevde 20'ye eziliyor — "UÇUŞTA DOĞRULANDI" notu etkisiz

**Dosya:** `kopru/gazebo_kaynak/control/guidance/supervisor.py:73-84` ↔ `guidance/ana_kontrol.py:286` ↔ `kopru/entegre.py:223-226`

**Ne iddia ediyor:** supervisor.py:73 — *"⚠ 20 -> 60 (2026-08-16, UÇUŞTA DOĞRULANDI)"*,
altında üç satırlık ölçüm tablosu: `K60 ömür 3.06 s, ıska 10.10 m, EN İYİ 3.71 m — günün rekoru`.

**Gerçekte ne yapıyor:** `entegre._kur()` her kurulumda
`sup.SupCfg.KAYIP_M = int(self.kayip_m)` yazıyor; değer `ana_kontrol.Cfg.KOPRU_KAYIP_M = 20`
(`:281-286`, *"2026-08-15: 60 -> 20 (şartname)"*). **Yasa dosyasındaki 60 hiç koşmuyor.**
İki sahip, iki tarih, ve `ana_kontrol` kazanıyor.

**KANIT:** `python arac/denetim_kanit.py B1`
```
yasa dosyasindaki deger  supervisor.SupCfg.KAYIP_M = 60
ana_kontrol.Cfg.KOPRU_KAYIP_M            = 20
-> entegre._kur() calistiktan SONRA: KAYIP_M = 20  (60'ten ezildi)
KOR PENCERE (olculen dongu 31.2 Hz):  60 kare -> 1.92 s | 20 kare -> 0.64 s
```

**Tahmini etki:** Görsel faz ömrü ölçülen 3.06 s yerine ~1.9 s. Ölçümün gösterdiği
en iyi ıska (3.71 m) erişilemiyor. Ayrıca `entegre.py:228` ekrana **üçüncü bir sayı**
basıyor: `~1.3 s @15 FPS` (ölçülen döngü 31.2 Hz → gerçek 0.64 s).

---

### D3 · `SONUM_T = 0.30` ve `LEAD_MAX_SEYIR_DEG = 9.0` hiçbir çıkışa dokunmuyor

**Dosya:** `kopru/gazebo_kaynak/control/guidance/bbox_ibvs.py:674` (`SONUM_T`), `:434` (`LEAD_MAX_SEYIR_DEG`), `:422` (`LEAD_ERKEN`)

**Ne iddia ediyor:**
`:659-673` — *"2026-08-14: 0.0 → 0.30 AÇILDI (ölçümle)"* + canlı DoW komut logu.
`:424-433` — *"9° bu veri setindeki en iyi değer"* + üç satırlık A/B tablosu
(`lead yok 8.0 m | lead 9° 7.1 m | lead 14° 8.8 m`).

**Gerçekte ne yapıyor:** İki varsayılan bu terimlerin **her iki çıkış yolunu da**
kapatıyor:
* `BURUN_LOS = 1` (`:355`) → `:842-846` `yaw_cmd`'yi `sonum`/`lead_az` **olmadan** kurar.
* `PN_N = 1.6 > 0` (`:343`) → `:915-932` `hiz_yonu`'nu `_taban = iris_yaw + K_YAW*eps_hiz`
  üzerinden yeniden kurar; `:903`'te hesaplanan `- sonum + lead_az` **üzerine yazılır.**

Geriye yalnız `lead_el` (terminal dikey, `:965`) kalıyor — `LEAD_SURE`/`LEAD_SONUM`
oradan yaşıyor, ama `SONUM_T`, `SONUM_MAX_DEG`, `LEAD_ERKEN`, `LEAD_MAX_SEYIR_DEG`
yalnızca CSV kolonu dolduruyor.

**KANIT:** `python arac/denetim_kanit.py B2` — aynı girdiyle A/B:
```
cikti      SONUM+LEAD ACIK IKISI DE KAPALI       fark
vx           14.400760577   14.400760577   0.00e+00
vy            5.651896574    5.651896574   0.00e+00
vz            0.323850256    0.323850256   0.00e+00
yaw_cmd       0.859617373    0.859617373   0.00e+00
tani['lead_az'] = 9.00 deg, tani['sonum'] = 0.2100 rad -> yalniz CSV'ye yaziliyor
MEKANIZMA KAPISI: PN=0 + BURUN_LOS=0 iken ayni A/B'nin yaw farki 0.0529 rad
  -> terimler CALISIR HALDE, sadece yol kapali.
```
(Son satır Gazebo ekibinin O6 mekanizma kapısı: özellik gerçekten var, sadece bağlı değil.)

**Tahmini etki:** İki ayarın panelde kaydırağı var (`gorsel_ozellikler.py:156`,
`LEAD_ERKEN :149`). Uçuşta çevrilirse **hiçbir şey değişmez** ama tune logunda
segment açılır → `tune_rapor` sahte A/B üretir. `bbox_ibvs.py` içindeki iki uzun
ölçüm bloğu artık geçersiz gerekçe.

---

### D4 · `MENZIL_PX_M` ikizi: yasa 202.6, nişan kapısı hâlâ çürütülmüş 160.0

**Dosya:** `bbox_ibvs.py:490` (`MENZIL_PX_M = 202.6`) ↔ `bbox_ibvs.py:1371` (`_men = 160.0 / boyut`)

**Ne iddia ediyor:** `:482-484` — *"⚠ 160.0 -> 202.6 (2026-08-16, ÖLÇÜLDÜ: 1788 tespitli
kare / 93 koşu). Eski sabit menzili sistematik %21 EKSİK sayıyordu."*
`:1371`'in kendi yorumu: `# kodun kalibrasyonu`.

**Gerçekte ne yapıyor:** Terminal **nişan kapısı** (`TERM_NISAN_MAX_M`, kör taahhüdü
engelleyen emniyet) hâlâ eski 160.0'ı kullanıyor. Menzil %21 küçük sanıldığı için
yanal sapma da %21 küçük hesaplanıyor → kapı **daha geçirgen.**

**KANIT:** `python arac/denetim_kanit.py B3` (eps_yaw = 20°)
```
   boyut      R@160    R@202.6  yanal160  yanal202  karar
      30       5.33       6.75      1.94      2.46  GEC / DUR(dogru)
-> kapi 27% FAZLA gecirgen (esik 2.0 m fiilen 2.53 m gibi davraniyor)
```

**Tahmini etki:** `TERM_NISAN_MAX_M`'in var oluş sebebi *"4-10 m yanal sapmayla kör
uçmak matematiksel olarak ıskadır"* (`:184`). Kapı tasarlandığından %27 gevşek.
Aynı ikizden iki yorum daha yanlışlandı: `TERMINAL_BOYUT 25 px ≈ 6.4 m` → **8.1 m**,
`BOYUT_REF 25 px = 6-7 m tutuş` → **8.1 m**.

---

### D5 · Kilit kancası bir kez başarısız olursa GÖRSEL devri **kalıcı olarak** kapanıyor

**Dosya:** `web/server.py:351-355` + `:326` + `:820-822` → etki `supervisor.py:474-481`

**Ne iddia ediyor:** `:330` — *"Saklanan zorla modunu supervisor'a yaz. Köprü yoksa False döner."*
Kontrol döngüsü `False` görürse tekrar denesin diye kurulmuş.

**Gerçekte ne yapıyor:**
```python
351:        except Exception as _ke:
352:            _sup.kilit_kaynagi = None        # kanca NULL'landi
353:            print("[GUDUM] !! kilit kaynagi baglanamadi: %r" % (_ke,))
354:        print("[GUDUM] supervisor zorla modu -> %s" % ...)
355:        return True                          # ... ama YINE DE True
```
`except` bloğu `return`'e düşmüyor. Çağıran (`:820-822`) `True`'yu "oldu, bir daha
deneme" diye yorumlayıp `_zorla_uygulandi[0]`'ı damgalıyor. `_zorla_uygulandi`
`:326`'da bir kez kuruluyor ve **`_gorev_sifirla` da (`:511-518`) `cmd=="stop"` da
(`:1978-1987`) sıfırlamıyor.** Bu andan sonra `kilit_kaynagi is None` →
supervisor `:474-481` `continue` der ve **GÖRSEL kipinde hiç devretmez.**
Ek kusur: `:352` yalnız `kilit_kaynagi`'yi null'lıyor, `kilit_sifirla` (`:347`) bağlı kalıyor.

**Tahmini etki:** Araç sürecin geri kalanında **GPS-only** uçar, arayüz ise
"GÖRSEL" gösterir. Konsolda tek satır uyarı var (`supervisor.py:479`) ama
uçuş devam eder. ⚠ Bu istisnanın canlıda gerçekten atıldığını **gözlemleyemedim**;
yol açıkça mevcut.

---

### D6 · Panelin 3 kaydırağı kaynak değişiminde sessizce geri alınıyor

**Dosya:** `kopru/gorsel_ozellikler.py:260` (`setattr`) ↔ `kopru/entegre.py:187-192, 226`

**Ne iddia ediyor:** `gorsel_ozellikler.py:11-14` — *"Sınıf niteliğini değiştirmek BİR
SONRAKİ kareden itibaren geçerli -> yeniden başlatma GEREKMEZ."*
`:48` (RANGE_SET) — *"Bu alan HER TIK okunur, canlı."*

**Gerçekte ne yapıyor:** Canlılık iddiası **doğru** (`gps_guidance.py:567`
`r_eff = min(menzil, cfg.RANGE_SET)` her tik okunur). Eksik olan şu:
`KOPRU_BIREBIR = False` (`ana_kontrol.py:181`) olduğu için `entegre._kur()`
her yeniden kurulumda 6 alanı `ana_kontrol.Cfg`'den geri yazıyor; bunların
**3'ü panelde var**.

**KANIT:** `python arac/denetim_kanit.py B16`
```
panel anahtari       modul  geri donen   ezen satir
V_MAX                gg     22.0         entegre.py:191  <- KAYNAK DEGISIMINDE SIFIRLANIR
RANGE_SET            gg     9.0          entegre.py:187  <- KAYNAK DEGISIMINDE SIFIRLANIR
KAYIP_M              sup    20           entegre.py:226  <- KAYNAK DEGISIMINDE SIFIRLANIR
panelde 28 anahtar var, bunlarin 3'u her _kur()'da geri yaziliyor.
```
Modül `ISTASYON_ELEV_DEG`'i bu tür bir sebeple **bilerek** panel dışında tutuyor
(`:206-210`) — aynı özen bu üçüne gösterilmemiş.

**Tahmini etki:** Uçuş sırasında ayarlanan üç değer, kaynak seçici (`v2`↔`gercek`)
her dokunulduğunda sessizce ilk hâline döner. Panelin kendi yardım metni
`KAYIP_M` için *"60 kare ~4 s tipik deliği yutar"* diyor; sistem 20'ye geri koyuyor.

---

### D7 · `Cfg.YAW_MAX` kaydırağı hiçbir şey yapmıyor (yanlış sınıfa yazıyor)

**Dosya:** `web/server.py:371` (`TUNE_ALLOW`) + `:2081` (`setattr`) ↔ `guidance/ana_kontrol.py:298`

**Ne iddia ediyor:** `TUNE_ALLOW = {"YAW_MAX", "VIS_CONF_MIN"}` — canlı ayarlanabilen
**iki** parametreden biri. `index.html` bunu yıldızlıyor: *"★ Yaw tavanı"*.

**Gerçekte ne yapıyor:** `Cfg.YAW_MAX`'ın tanım satırı ve kaydırağın kendisi dışında
**okuyucusu yok.** Yaw'ı fiilen kırpan başka bir sınıf: `dow_kopru.Cfg.YAW_MAX = 0.85`
(`kopru/dow_kopru.py:265`, kullanım `:626`). İki değer bugün **farklı** (0.60 vs 0.85).

**KANIT:** `python arac/denetim_kanit.py B19` — repo genelinde her kod-içi geçiş listelenir:
```
ana_kontrol.py :298   YAW_MAX = 0.60                     <- TANIM
server.py      :371   "YAW_MAX",                         <- SLIDER
dow_kopru.py   :626   yaw_cmd = kirp(..., -cfg.YAW_MAX)  <- BASKA BIR SINIF
ana_kontrol.Cfg.YAW_MAX = 0.60  <- slider bunu yaziyor, OKUYAN YOK
dow_kopru.Cfg.YAW_MAX   = 0.85  <- yaw'i FIILEN kirpan
```
İllüzyon kapalı devre: `GET /api/tune` (`:1919`) aynı ölü niteliği geri okuyor,
`tune_log_dongusu` (`:400`) 1 Hz'de logluyor.

**Tahmini etki:** Kaydırak değiştirilince tune logunda **segment açılıyor** ve
`tune_rapor` "Segment Kıyas" sayfası nedensel etkisi sıfır olan bir değişimi
A/B karşılaştırması diye sunuyor. Canlı-tune'un yarısı ölü.

---

### D8 · `tune_rapor.py` performans analizinin tamamı erişilemez

**Dosya:** `web/tune_rapor.py:132-137` ↔ `guidance/ana_kontrol.py:938`

**Ne iddia ediyor:** *"tek uçuşta birçok tune denemesi test edilir (uçuş başına tek set
kısıtı kalkar)"* (`server.py:376-381`).

**Gerçekte ne yapıyor:** Tüm metrikler `phase == "VISUAL"` filtresine bağlı
(`:132`, `:364`, `:403`). `ana_kontrol`'de **tek** log yazım noktası var ve faz
dizesini sabit veriyor: `:938 self._log_early("KOPRU", ...)`. `VISUAL` satırı
hiç üretilmiyor → `:135-137` `"UYARI: gorsel faz yok"` yazıp `return` ediyor.

**KANIT:** `python arac/denetim_kanit.py B21` — **bugünkü gerçek uçuş loglarında**:
```
ucus_log_20260816_183614.csv  56465 satir  fazlar={'KOPRU': 56465}  VISUAL=0
ucus_log_20260816_162527.csv 183148 satir  fazlar={'KOPRU': 183148} VISUAL=0
-> VISUAL satiri toplam: 0   (5 dosya / 328k satir)
```

**Tahmini etki:** Rapor her seferinde boş üretiliyor ama `server.py:2109-2145`
`{"ok": True, "dosya": ...}` dönüyor. `_LOG_COLS`'taki `vis_*`, `ibvs_*`,
`kilit_win_s` kolonları başlıkta var, hiç dolmuyor. Uçuş sonrası analiz aracı
**sessizce çalışmıyor.**

---

### D9 · `entegre.adim()`: `tani_log_kapat()` `return`'ün arkasında — kendi tarif ettiği hata duruyor

**Dosya:** `kopru/entegre.py:381-390`

**Ne iddia ediyor:** `:382-385` — *"Tanı logunun kuyruğu diske insin: yazıcı thread 250
satır birikmeden yazmıyor (50 Hz'de ~5 s). Kapatmadan çağrılmazsa **her görevin SON
0-5 saniyesi kayboluyordu** — logun var oluş sebebi olan çarpışma/kopma anını tam
orada kaybediyorduk."*

**Gerçekte ne yapıyor:**
```python
381:        return self._kopru.adim()
382:        # Tani logunun kuyrugu diske insin: ...
386:        try:
387:            if self._kopru is not None:
388:                self._kopru.tani_log_kapat()
```
`return`'den sonra. **Hiç çalışmıyor.** Yani yorumun tarif ettiği hata hâlâ aktif —
düzeltme yazılmış, bağlanmamış.

**KANIT:** `python arac/denetim_kanit.py B5` (AST ile erişilemezlik):
```
entegre.py fonksiyon `adim`: return satiri 381
return SONRASI 1 ifade var (satir 386) -> ERISILEMEZ:  try:
cagirilamayan: DowKopru.tani_log_kapat()
```
Tek gerçek çağrı yeri `dow_kopru.dongu_durdur():805` — ama `entegre` `DowKopru`'nun
kendi döngüsünü kullanmıyor, 50 Hz'de dışarıdan `adim()` tikliyor.

**Tahmini etki:** Her görevin son 0-5 saniyelik tanı verisi hâlâ kayboluyor.

---

### D10 · `DevirCfg` bloğu (29 satır gerekçe) devir kararına hiç girmiyor

**Dosya:** `guidance/ana_kontrol.py:52-80` ↔ `supervisor.py:520-523`

**Ne iddia ediyor:** `DevirCfg` docstring'i — *"LOCK_PCT %6 -> %2 : devir ~25 m'de olur
(açısal hız 41 °/s, kadrajı geçme 3.0 sn -> görsel yasaya devralma payı var)"*.
`server.py:337-339` — *"supervisor'ın GÖRSEL devir ölçütü arayüzdeki 'X.X / 5.0 s'
sayacıyla AYNI olsun diye bağlanıyor."*

**Gerçekte ne yapıyor:** `_devret = _kare_ok and _sure_ok and _geo_ok` ve son iki
terim varsayılanda **daima True**:

**KANIT:** `python arac/denetim_kanit.py B7`
```
SupCfg.ZORLA_MOD       = None  (server.py:323 _zorla_mod_istek=None)
SupCfg.KILIT_SURE_S    = 0.0 -> _sure_ok = (0.0 <= 0.0) = True
SupCfg.DEVIR_ASPECT_MAX= 999 -> _geo_ok daima True
SupCfg.DEVIR_DONUS_MAX = 999 -> _duz_ok daima True
=> _devret == _kare_ok == (ardisik_gor >= KILIT_N=10)
DevirCfg.LOCK_PCT=0.02 AV_X=0.35 AV_Y=0.25 -> yalnizca karar_log/telemetri
Gercek devir kapilari: DEVIR_BOYUT_PX=14 px, HAYALET w/h>=1.3, KILIT_N=10 ardisik
```
Üstelik varsayılan kip `ZORLA_MOD=None` → "OTO"; o kolda `kilit_kaynagi`'ye
**hiç bakılmıyor** (`supervisor.py:467` `if _z == "GORSEL"`).

⚠ İnce ayrım: kanca **değeri** kullanılmıyor ama **varlığı** kapı — `None` dönerse
GÖRSEL kipinde hiç devretmiyor (D5'in mekanizması bu).

**Tahmini etki:** Devir menzilini `DevirCfg.LOCK_PCT` ile ayarlamaya çalışmak
etkisiz. `server.py:349-350`'nin bastığı `"kilit kaynagi bagli (esik 5.0 s, boyut >=%2.0)"`
satırı hiçbir şeyi tarif etmiyor.

---

## KALAN BULGULAR — kategoriye göre

### A · Ölü / bağlanmamış özellikler

| # | Yer | Bulgu | Kanıt |
|---|---|---|---|
| A1 | `ana_kontrol.py:576,577` | `VIS_AV_X`, `VIS_AV_Y` — repo genelinde **0 okuma**. Gerçek AV bandını `KilitCfg.AV_X/AV_Y` veriyor. | B9 |
| A2 | `ana_kontrol.py:319` | `DEBUG_Z` — 0 okuma (yorumu *"Sorun çözülünce False yap"* diyor; zaten hiç okunmuyordu). | B9 |
| A3 | `bbox_ibvs.py:91` | `YAW_ESIK` — 0 okuma. Yorumu *"bu açının altında yaw komutu güncellenmez"* diyor; öyle bir kapı yok. | B9 |
| A4 | `web/dev_truth.py` (tüm dosya) | Repo genelinde **hiç import edilmiyor**; üstelik çağırdığı `AvciKontrol.set_hedef_kaynagi` (`:129,134`) **tanımlı değil**, `beyin.hedef_kaynak_ad` (`:142`) yok → `durum()["aktif"]` her zaman `False`. Docstring'i hâlâ *"server.py/index.html'deki DEV-ONLY çitli bağlantı noktaları"*ndan söz ediyor; `arac/paket_kontrol.py:83` var olmayan çitleri tarıyor. | ajan |
| A5 | `detection/kamera_model.py` | Üretimdeki tek tüketicisi `server.py:1511 cmc_homografi()`; sonucu `takip.guncelle(...)`'ye gidiyor ve `detection/takip.py:66` aynen şunu diyor: *"dt/H_cmc/cmc_max_kaydirma **yok sayilir**"*. → Modülün uçuş davranışına etkisi **sıfır**. `TAKIP_CMC_SIGN` / `TAKIP_CMC_MAX_KAYDIRMA` (`ana_kontrol.py:448,453`) buna bağlı emniyet knob'ları — ikisi de ölü. | ajan (doğruladım) |
| A6 | `kamera_model.py:85,205,78,197` | `ey_ref()`, `dikey_ekran_tahmini()`, `dfov_rad()`, `piksel_yon()` — üretimde 0 çağrı. Modül başlığı `:8` *"IBVS dikey referansı (VIS_EY_REF) buradan okur"* diyor; `VIS_EY_REF` diye bir sembol repoda yok. | ajan |
| A7 | `vision/geometry.py` | `KEYPOINT_FLIP_IDX`, `quat_to_rpy`, `rot_gt_goruntu`, `bbox_to_yolo`, `target_keypoints`, `talon_box_corners` — 0 okuma. Ayrıca `_MESH_DIR` (`:29`) bu depoda **var olmayan** bir dizini gösteriyor → mesh'e bağlı her fonksiyon burada `FileNotFoundError` atar. Canlı olan yalnız `CX, CY, FX, FY, IMG_W, IMG_H`. | ajan |
| A8 | `detection/pencere_yakala.py:110` | `pencere_icerik_bgr()` — 0 çağrı, ama 8 satırlık *"K sanity zinciri de bu yolla ölçüldü"* gerekçesi taşıyor. | ajan |
| A9 | `detection/model_yonetici.py`, `detection/algi_hatti.py` | `web/server.py` tarafından **import edilmiyor** (yalnız testler + `arac/`). `config.py:17` bunu yine de *"model registry (hot-swap)"* diye teslim hattının parçası ilan ediyor. | ajan |
| A10 | `server.py:1190-1195` | `POSE_MODEL_PATH` `Cfg.VIS_POSE_MODEL_PATH`'ten okunuyor, **5 satır sonra** `POSE_AKTIF = False` ile tüketicileri erişilemez hâle geliyor (`:1422 if not POSE_AKTIF`). | ajan |
| A11 | `supervisor.py:508-511` | Geometri kapısı açılırsa (`AVCI_DEVIR_DONUS<999`) ve `aspect_deg is None` ise `"%.0f" % None` → **TypeError**, `izci` thread'i sessizce ölür; o GPS fazında devir bir daha olmaz. | **B14** |

### B · Ezilen ayarlar — dışarıdan gerçekten ne değiştirilebilir?

**GERÇEKTEN çalışan dış ayarlar**
* `bbox_ibvs.Cfg`'nin tüm panel anahtarları (`V_TOPLAM_MAX`, `MAX_ACCEL`, `VZ_MAX`,
  `K_YAW`, `PN_N`, `PN_PENCERE_S`, `BURUN_LOS`, `CONF_MIN`, `ROLL_TELAFI`,
  `KAPANMA`, `YAW_HIZALA_S`, `KOR_KOPRU_*` …) — hiç ezilmiyor, her karede okunuyor.
* `SupCfg.KILIT_N`, `KILIT_ARDISIK`, `DEVIR_BOYUT_PX` — ezilmiyor.
* `SupCfg.ZORLA_MOD` — ezilmiyor (ama D5'e bak).
* `Cfg.VIS_CONF_MIN` — canlı, **ama** yalnız `server.py` içinde tüketiliyor; görsel
  yasanın eşiği ayrı (`bbox_ibvs.Cfg.CONF_MIN`).
* `AVCI_*` env'leri (`AVCI_IBVS_*`, `AVCI_DEVIR_*`, `AVCI_HAYALET*`, `AVCI_KURT*`,
  `AVCI_DOW_HFOV`, `AVCI_ZEMIN_M`) — sınıf tanımında okunur, ezilmez.

**SESSİZCE EZİLEN / ETKİSİZ olanlar**

| Ayar | Ne oluyor | Kanıt |
|---|---|---|
| `SupCfg.KAYIP_M` | `entegre.py:226` → 20 | D2 / B1 |
| `gg.Cfg.RANGE_SET` | `entegre.py:187` → 9.0 | D6 / B16 |
| `gg.Cfg.V_MAX` | `entegre.py:191` → 22.0 | D6 / B16 |
| `gg.Cfg.IC_KAYMA` | `entegre.py:188` → 0.0 | B16 |
| `gg.Cfg.ISTASYON_ELEV_DEG` | `entegre.py:189` → 10.0; **ayrıca** döngü öncesi bir kez çözülüyor (`gps_guidance.py:391`) → canlı ayarlanamaz | B16 |
| `gg.Cfg.ELEV_DINAMIK` | `entegre.py:190` → `False` (env `AVCI_GPS_ELEV_DIN` de `:163`'te `setdefault` ile 0) | B16 |
| `AVCI_GPS_RANGE/IC/ISTASYON_ELEV/ELEV_DIN` | `birebir=True` kipinde `entegre.py:146-148` **pop** eder; `birebir=False` kipinde `:142-144` **üzerine yazar** → **her iki kipte de dışarıdan set etmek etkisiz** | **B6** |
| `Cfg.YAW_MAX` (slider) | yanlış sınıfa yazıyor | D7 / B19 |
| `SONUM_T`, `LEAD_ERKEN`, `LEAD_MAX_SEYIR_DEG` (slider) | çıkışa ulaşmıyor | D3 / B2 |
| `DevirCfg.LOCK_PCT` / `AVCI_DEVIR_PCT` | devir kararına girmiyor | D10 / B7 |
| `dedektor` ctor `conf=Cfg.VIS_CONF_MIN` (`server.py:1405`) | **aynı iterasyonda** `:1461/1463` `dedektor.conf = min(UI_CONF_MIN=0.25, ...)` ile eziliyor → etkin eşik 0.25, hiç 0.35 değil | ajan |
| `config.py` — `WEB_HOST`, `WEB_PORT`, `PROJ_ROOT` | uçuş hattında **0 okuma**; `server.py:58,61` kendi kopyalarını kuruyor. Yalnız `fps_olc.py` `import config` yapıyor. Dosya başlığı yine de *"Bu dosya UÇUŞ pipeline'ının parçasıdır"* diyor. | **B22** |
| `gorsel_ozellikler.ayarla()` | `hasattr` kontrolü yok → var olmayan bir anahtar `setattr` ile **yaratılıyor**, `ok:true` dönüyor, uçuş logu olayı yazıyor, hiçbir şey okumuyor | ajan |

### C · Ölçümle çelişen sabitler ve yorumlar

| # | Yer | Çelişki |
|---|---|---|
| C1 | 3 dosya | **Kare hızı üç ayrı iddia:** `tespit_akisi.py:39` "~8-9 FPS" · `ana_kontrol.py:273` "~15 FPS" · `supervisor.py:74` "ölçülen döngü 31.2 Hz". Aynı 20-kare eşiği 2.2 s / 1.3 s / 0.64 s okunuyor. (**B8**) |
| C2 | `tespit_akisi.py:230-231` | `olcum()` `kilit_penceresi_s = 15.0/hz`, `kayip_esigi_s = 20.0/hz` — **gömülü sabit**. Gerçek ölçüt `KILIT_N=10` ardışık (15'lik kayan pencere `KILIT_ARDISIK=1` ile zaten kullanılmıyor) ve `KAYIP_M`. Fonksiyonun var oluş sebebi *"eşikler bu hıza göre SÜRE karşılığı kazanır"* — yanlış süre veriyor. (**B8**) |
| C3 | `entegre.py:228` | `"~%.1f s @15 FPS"` — 31.2 Hz ölçümüne rağmen 15 varsayıyor (2× hata). |
| C4 | `bbox_ibvs.py:162-168, 139-141` | `TERMINAL_BOYUT 25 px ≈ 6.4 m`, `BOYUT_REF 25 px = 6-7 m tutuş` — `MENZIL_PX_M=202.6` ile ikisi de **8.1 m**. (**B3**) |
| C5 | `bbox_ibvs.py:1394` | Yorum `Cfg.YAW_RATE_MAX` diyor; nitelik adı `YAW_RATE_MAX_DEG`. |
| C6 | `supervisor.py:7, 609` | Docstring *"conf ≥ POSE_CONF_MIN"* diyor, `:609` `conf≥{POSE_CONF_MIN:.2f}` basıyor → **`conf≥0.00`**. Eşik `:104`'te 0.0'a alınmış. |
| C7 | `supervisor.py:72` | `KILIT_PENCERE = 15  # ~0.5 s @30 Hz` — 31.2 Hz'de 0.48 s (küçük), ama zaten `KILIT_ARDISIK=1` ile hiç kullanılmıyor. |
| C8 | `supervisor.py:187-190` | *"şartnamedeki %5 kilit ölçütü = 32 px"* — çeviri `w_yasa = 0.3136·w_dow` olduğu için 1920'lik kadrajın %5'i (96 px) yasa çerçevesinde **30.1 px**, yani %4.7. %6 hata. |
| C9 | `entegre.py:28-30` | *"YASA DEĞERLERİ DONDURULDU: gps_guidance.Cfg'ye dosyadan/setattr'dan dokunulmaz … hepsi env üzerinden"* — `:186-194` tam olarak `setattr` yapıyor ve `:170-185` env'in yetmediğini açıklıyor. Docstring güncellenmemiş. |
| C10 | `ana_kontrol.py:80` | *"WIN_S / WIN_NEED_S … (5 s / 10 s pencere)"* — gerçek değerler `WIN_S=10.0`, `WIN_NEED_S=5.0`. Sıra ters. |
| C11 | `ana_kontrol.py:254-255` | Hibrit açıklaması hâlâ *"15 karelik pencerede 10 tespit, conf>=0.5"* + *"20 ardışık"* diyor; ölçüt 2026-08-10'da ardışık-10 + conf yok oldu. |
| C12 | `config.py:12` | `guidance/ibvs_gorsel.py` diye bir dosya **yok** (dizinde yalnız `__init__.py`, `ana_kontrol.py`, `kilit_sayaci.py`). `config.py:33` de "aktif model best.pt" derken `:49` `talon_v3` diyor. |
| C13 | `algi_hatti.py:43` vs `:53,160` | `Vc` docstring'de **px/s**, kodda **1/s** (bağıl *alan* büyüme oranı) — ve `A ∝ L²` olduğu için açısal büyüme oranının **2 katı**. Docstring `gecerli` diye bir anahtar da vaat ediyor, kod üretmiyor. |
| C14 | `algi_hatti.py:12` vs `:109` | Aynı dosyada tracker "ByteTrack + gyro-CMC" ve "HybridSort" olarak iki kez tarif ediliyor. |
| C15 | `talon_pose_estimator.py:255` | `k*~1 -> HFOV=125 hassas teyit` — ölçülen 122.0709'a göre doğru sonuç `k* = 531.36/499.75 = 1.063`. Test, "geçti" koşulunu **yanlış HFOV'u onaylayacak** şekilde tanımlıyor. |
| C16 | `takip.py:104` vs `server.py:1526-1528` | `tespit_mi` koşulsuz `True` yazılıyor → *"Coast (tespit_mi=False) da beyne GITMEZ"* dediği dal **erişilemez**. |
| C17 | `server.py:876` vs `:955-966` | `AVCI_KAYIT_ON` "bağlantıdan sonra kaç sn bekle" diye belgelenmiş; kod görev başlangıcından sayıyor. |
| C18 | `kurtarma.py:8-10, 23-26` | *"Eşikler ölçülmüş uçuş zarfının ÇOK dışında … sağlıklı uçuşta asla tetiklenmez"* — bu cümle `MAX_ACCEL=12` içindi. Panel `MAX_ACCEL`'i **4..38 m/s²** aralığında açıyor; `a > 17.0 m/s²`'de kararlı dönüş yatışı `atan(a/g) > 60°` = `KurtCfg.ACI_TETIK`. (**B17**, ⚠ aritmetik uyarı — gerçek yatışı ölçemedim) |

### D · Testler

```
python -m pytest tests -q   ->   7 failed, 338 passed in 26.89s
```
(`--timeout` desteklenmiyor: `pytest-timeout` kurulu değil.)

| Test | Ne koruyordu | Neden kalıyor |
|---|---|---|
| `test_kopru_konfig_kilidi.py::test_istasyon_geometrisi_tasarima_esit` | İstasyon geometrisi = **6.25 m arka + 2.92 m alt** (onaylı W koşusu) | Gerçek: `8.86 m arka + 1.56 m alt`. **Bekçi doğru çalışıyor — D1'i tam olarak bu yakaladı.** Bilinen bulgu #5, hâlâ FAIL. |
| `test_gorsel_ozellikler.py::test_varsayilanlar_KAYNAKLA_AYNI` | Dal HEAD'iyle aynı varsayılanlar: *"T1a AÇIK, gerisi KAPALI"* | `LEAD_ERKEN` `False` bekleniyor, `True`. M4 (2026-08-15) açtı, test güncellenmedi. ⚠ İronik: D3'e göre `LEAD_ERKEN` zaten **etkisiz** — test gerçek bir davranış farkını değil, bir bayrağı koruyor. |
| `test_dow_kopru.py` × 5 (`test_get_plane_cerceve_ve_frozen`, `test_gnss_duzeltici_{kapali_ham_gecer,acikken_filtre_zinciri,hata_zarif_duser}`, `test_ned_zemin_kaydirmasi`) | NED çerçeve çevrimi, zemin kaydırması, GNSS düzeltici zinciri | Hepsi aynı kök: `RuntimeError: HEDEF_TRUTH_AKTIF ama get_debug_truth YOK`. Testin sahte SDK'sında `get_debug_truth` yok; `dow_kopru.py:480` truth kipinde **sert hata** atıyor. Yani **NED çevrim sözleşmesinin 5 bekçisi de şu an bir şey korumuyor** — çerçeve/işaret hatası girse bu testler zaten kırmızı olduğu için fark edilmez. |

**Not:** 4 no'lu bilinen bulgu (`KAYIP_M` yorumu "~0.66 s") artık düzeltilmiş
(`supervisor.py:84` "~1.9 s @31 Hz") ama D2 yüzünden **sayının kendisi** koşmuyor.
6 no'lu bulgu (`VIS_KOPRU`) bu sürümde **yok** — `ana_kontrol.py:454-463`'te yalnız
açıklama bloğu kalmış, `VIS_KOPRU_S` diye bir sabit tanımlı değil (ölü yorum).

### E · Çerçeve / birim tuzakları

| # | Yer | Bulgu |
|---|---|---|
| E1 | `server.py:1695` ↔ `kilit_sayaci.py:119` | **`esik_pct` aynı sözlükte iki farklı birim.** Sayaç `esik_pct`'i **yüzde** (6.0) üretiyor; `server.py` onu atıp `Cfg.VIS_LOCK_PCT`'i **oran** (0.06) olarak koyuyor — ama yanındaki `boyut_pct` sayacın **yüzdesi** (6.2). Arayüz `6.2 >= 0.06` kıyaslıyor → **her zaman "geçti"**. 100 kat. Sayacın kendi kararı doğru; bozulan gösterim. (**B20**) |
| E2 | `supervisor.py:205` ↔ `kilit_sayaci.py:35` ↔ `ana_kontrol.py:77,573` | Aynı şartname kuralı (**"kadrajın ≥%5'i"**) dört yerde tanımlı: üçü **oran** (0.06 / 0.02 / 0.06), biri **piksel** (`DEVIR_BOYUT_PX=14`), üstelik farklı referans genişlikte (640 yasa çerçevesi vs 1920 DoW). Dönüşüm `supervisor.py:188`'de %6 hatalı (C8). |
| E3 | `dow_kopru.py:50-53` | NED sözleşmesi (`NED_y=-DoW_y`, `NED_z=-DoW_z`, `yaw_NED=-yaw_DoW`) **doğru ve tek kaynakta.** Ama **roll de çevriliyor** (`:212`, "DoW roll = -NED roll", ölçülen korelasyon -0.965) ve bu, `:50-53`'teki sözleşme bloğunda **listelenmiyor** → sözleşme eksik. Pitch bilerek çevrilmiyor (`:30`). |
| E4 | `arac/ariza_taksonomi.py:41-43,79` | *"DoW/Unreal sol-el; `NED_y=-DoW_y` bütün dünyayı aynalıyor. GPS güdümü ayna-simetrik olduğu için etkilenmez, **KAMERA etkilenir**"* → telafi bayrağı `AYNALI_X = True` **yalnızca teşhis aracında**. `detection/kamera_model.py`'de aynalama terimi **hiç yok** ve kendi başlığı (`:31-38`) pitch/roll işaretlerini *"VARSAYIM (>>> SİM'DE DOĞRULA <<<)"* diye işaretliyor. |
| E5 | Birim zinciri | SDK **cm/cm-s** → `dow_kopru.CM=100` → **m/m-s**; `talon_pose_estimator` obje noktaları **mm** (`:51-57`), `:204` mm→cm, `pose/poz_cozucu.py:49` `MESH_PIVOT_OFFSET_CM` **cm** → `:98`'de ×10 mm; `vision/geometry.py` **metre**. Tek fonksiyonun çevresinde 4 birim sistemi, tip yok. |
| E6 | `talon_pose_estimator.py:117` ↔ `pose/poz_cozucu.py:80,139` | İkisi de "8.0 px" reprojeksiyon eşiği, ama biri **ölçeklenmiyor**, öbürü `× W/1920` ile ölçekleniyor. DPI 1.25 ile 1536 px yakalamada %25 ayrışırlar. |
| E7 | `derece / radyan` | `kamera_model.py` API'si **derece**; `vision/geometry.py` **radyan**; `pose/geometri.py:35` **derece** *ve* farklı argüman sırası (`pitch, yaw, roll`). Üç konvansiyon. |
| E8 | `bbox_ibvs.py:1453` | CSV `kayip_sayac` kolonu normal karelerde **sabit 0**; köprü karesinde sayaç artmasına rağmen 0 yazılıyor. Bu kolona bakan analiz birikimi göremez. (**B15**) |

### F · Aynı kavramın iki yerde tanımlanması (birbirinden kayabilecek ikizler)

| # | Kavram | Kopyalar | Durum |
|---|---|---|---|
| F1 | **HFOV** | `kamera_model.py:46` = 125.0 · `pose/geometri.py:29` = 125.0 · `tespit_akisi.py:98` = **122.0709** · `sim/tesis.py:79` = 122.0709 · `vision/geometry.py:22` = 125° (Gazebo, bilerek) | **UYUŞMUYOR.** İlk ikisi 2.93° yanlış → `fx` %5.9 sapma. `kamera_model.py:11-13` bunu *"oyuna gömülü, değiştirilemez platform sabiti"* diye ilan ediyor; `tespit_akisi.py:84-88` motorun kendi `camera_fov: 122.0709` değerini 0.001 px artıkla çözmüş. PnP zinciri (`talon_pose_estimator.py:172`, `poz_cozucu.py:116`) bu %5.9'u taşıyor. Komut yolunda **değil** → şimdilik gizli. |
| F2 | **Menzil↔piksel çarpanı** | `bbox_ibvs.py:490` = 202.6 · `bbox_ibvs.py:1371` = 160.0 | **UYUŞMUYOR** → D4. |
| F3 | **`166.6` yasa odağı** | `vision/geometry.py:23` (hesaplanan) · `tespit_akisi.py:108` (sessiz fallback) · `sim/tesis.py:105` · `arac/ariza_taksonomi.py:76` · `arac/menzil_model.py:114` | Bugün **uyuşuyor**. Ama `geometry.HFOV_RAD` bir gün 122.07'ye "düzeltilirse" `tespit_akisi.py:108` import hatasında eski değeri **sessizce** korur — docstring'i bunu güvenlik diye sunuyor. |
| F4 | **Kamera tilt 25°** | `kamera_model.py:47` · `pose/geometri.py:29` · `ariza_taksonomi.py:78` · `vision/geometry.py:27` (-0.4363 rad) · `sim/tesis.py:82` | Beşi de 25.0 — **ama** `sim/tesis.py:82` yorumu *"ölçülen +22.9, kod 25"* diyor ve bu ölçüm hiçbirine yansıtılmamış. `kamera_model.py:9` ayrıca *"koda ikinci bir 25/125 sabiti YAZILMAZ"* diye söz veriyor; dört tane var. |
| F5 | **Kilit eşikleri** | `ana_kontrol.Cfg.VIS_LOCK_PCT/VIS_AV_X/VIS_AV_Y/VIS_WIN_S/VIS_WIN_NEED_S` ↔ `kilit_sayaci.KilitCfg.*` | Bugün **birebir uyuşuyor**; sayaç **yalnız** `KilitCfg`'yi okuyor, arayüz/rapor **yalnız** `Cfg.VIS_*`'ı basıyor. `VIS_AV_X/Y`'nin başka okuyucusu yok (A1). Biri değişirse arayüz yalan söyler. (**B10**) |
| F6 | **Keypoint sırası** | `vision/geometry.py:108` · `talon_pose_estimator.py:68` · `poz_tespit.py:14-16` · `poz_cozucu.py:45` (`EGITIM_SIRASI=[0,1,2,5,3,4]` — fiilen uygulanan) | **DÖRT FARKLI SIRA.** Flip listeleri de ayrışıyor: `geometry.py:109` `[0,1,3,2,5,4]` vs `pose/etiketle.py:66` `[0,2,1,4,3,5]`. Geometry'ninki ölü (A7) — eğitilmiş modelle **tutarsız** olduğu için şanslıyız. |
| F7 | **Güven eşiği** | `ana_kontrol.py:377`=0.35 · `bbox_ibvs.py:722`=0.35 · `gorsel_tespit.py:30`=0.35 · `server.py:69`=**0.25** · `model_yonetici.py:151`=0.25 · `supervisor.py:104`=**0.0** | Altı tanım. Etkin dedektör eşiği 0.25 (ctor'daki 0.35 aynı iterasyonda eziliyor). |
| F8 | **Model seçimi** | `config.py:49` `VIS_MODEL_ADI="talon_v3"` ↔ `ana_kontrol.py:344` `VIS_MODEL_PATH=.../talon_v3.pt` | Bugün uyuşuyor. `config.py.yedek_20260814_1644:36` daha önce ayrıştıklarını gösteriyor (`"best"`). |
| F9 | **PnP şeması** | `talon_pose_estimator.py:52-53` `_KUYRUK_UCU == _MOTOR == (536.8,-6.5,0.0)` | `SEMALAR["kuyruk_ucu"]` ile `SEMALAR["motor"]` **sayısal olarak aynı**; `sema_ayarla()` yine de yönelim filtresini sıfırlıyor → şema değiştirmek "bir şey yaptı" görüntüsü veriyor. |
| F10 | **`K_matrisi()`** | `kamera_model.py:58` ↔ `poz_cozucu.py:63-66` | İki bağımsız uygulama, ikisi de 125.0 kullandığı için bugün uyuşuyor. |
| F11 | **`YAW_MAX`** | `ana_kontrol.py:298`=0.60 (ölü) ↔ `dow_kopru.py:265`=0.85 (etkin) | **UYUŞMUYOR** → D7. |
| F12 | **`status` sözlüğü** | `gps_guidance.py:349` modül düzeyinde; `run_gps_guidance` onu **temizlemiyor** (`_hdg_gecmis` de öyle) | Görevler arası sızıntı: yeniden başlatılan görevin **ilk devrinde** `tgt_vx/vy/vz` (dondurulmuş taşıyıcı, `supervisor.py:628`) önceki görevin son değeri olabilir. (**B18**) |
| F13 | **Kilit sayacı örneği** | `ana_kontrol.py:658` `self.kilit` ↔ `:669` `self.kilit_devir` | `set_kaynak()` (`:698`) yalnız `self.kilit`'i sıfırlıyor; `kilit_devir`'in 10 s'lik penceresi ve `ok` mandalı önceki görevden **devrediyor**. (**B11**) |

### G · API hijyeni (uçuşu bozmaz, ama "başarılı" der)

* `server.py:1956/2039` — bilinmeyen `cmd` → `HTTP 200 {"ok": true, "msg": "Bilinmeyen komut"}`.
* `server.py:2019-2039` — `vismode` doğrulaması yapılıyor (`:2021`) ama sonuç **atılıyor**:
  `:2029` koşulsuz `_zorla_mod_istek = m` yazıyor, `:2030` onu `SupCfg.ZORLA_MOD`'a
  koyuyor. `{"mode":"banana"}` → yanıt `{"ok":true, "msg":"GECERSIZ mod: BANANA"}`,
  `ZORLA_MOD == "BANANA"`, supervisor sessizce OTO'ya düşüyor. Tek isteğe üç farklı cevap.
* `server.py:2059-2066` — `/api/manuel`: manuel kip kapalıyken dört eksen de atılıyor,
  `{"ok":true}` `if` bloğunun **dışında**.
* `server.py:1961-1963` — yorum *"set_kaynak köprüyü YIKIP yeniden kuruyor -> SupCfg
  sıfırlanır"* **yanlış**: `SupCfg` modül düzeyinde bir sınıf, köprü yıkımı onu
  etkilemez. Üstelik telafi amaçlı `:1963` çağrısı, tam da tarif edilen durumda
  **garantili no-op** — `set_kaynak` az önce `kopru_gudum = None` yaptığı için
  `_zorla_mod_uygula` `:334-335`'te hemen `False` döner.

---

## KANITLAYAMADIKLARIM

1. **D1'in uçuş sonucu.** 1.56 m dikey ayrımın gerçekten temasa yol açtığını
   ölçemedim; yalnız deponun kendi eşiklerine göre ihlal olduğunu gösterdim.
   Gereken: `veri/ucus_log_*.csv`'de `gercek_mesafe` minimumlarının GPS fazı
   dağılımı. (Log kolonu dolu, ama faz ayrımı yok — bkz. D8.)
2. **D5'in canlıda tetiklendiği.** `_zorla_mod_uygula` içindeki `except`'in
   gerçekten atıldığına dair log kanıtı bulamadım; yalnız yolun açık olduğunu
   gösterdim. Aranacak dize: `"[GUDUM] !! kilit kaynagi baglanamadi"`.
3. **B17 / C18'in gerçekliği.** `MAX_ACCEL > 17 m/s²`'de aracın **gerçekten**
   60°'yi aşan yatışa girdiğini ölçemedim — komut ivmesi ile gerçekleşen yatış
   arasındaki ilişki DoW'un uçuş modeline bağlı. Bu bir aritmetik uyarı.

---

## BAKTIĞIM YERLER

* `kopru/gazebo_kaynak/control/guidance/` — `supervisor.py` (tam), `bbox_ibvs.py` (tam),
  `gps_guidance.py` (Cfg + istasyon/status bölümleri), `kurtarma.py` (tam),
  `common.py`, `guidance_core.py` (Cfg referansları), `hedef_kestirim.py` (yüzeysel)
* `kopru/` — `entegre.py` (tam), `tespit_akisi.py` (tam), `gorsel_ozellikler.py` (tam),
  `yasa_senkron.py` (tam), `dow_kopru.py` (NED/birim sözleşmesi, `YAW_MAX`, `tani_log_kapat`)
* `guidance/ana_kontrol.py` — `Cfg` bloğu, `DevirCfg`, `__init__`, `set_kaynak`,
  `_log_early`, `KopruGudum` kurulumu
* `web/server.py` (tam, ajanla), `web/dev_truth.py`, `web/tune_rapor.py`
* `vision/geometry.py`, `detection/*` (tam, ajanla), `config.py`, `guidance/kilit_sayaci.py`
* `tests/` — tamamı koşuldu; kalan 7'nin her biri incelendi
* `veri/ucus_log_*.csv` — son 5 dosya, 328k satır (D8 kanıtı)

## BAKMADIĞIM YERLER

* `kopru/gazebo_kaynak/control/guidance/visual_lead.py` (577 satır) — arşiv yol
  (`_GORSEL_YASA` varsayılanı `bbox`, `AVCI_VISUAL=lead` verilmedikçe koşmaz)
* `kopru/gazebo_kaynak/control/guidance/adapter_copter.py` — ArduPilot adaptörü, DoW'da kullanılmıyor
* `kopru/olcum_faz*.py`, `kopru/kosu_faz31.py`, `kopru/olcum_gnss.py` — ölçüm scriptleri
* `arac/` altındaki 45 analiz/simülasyon aracı (`sim_*`, `ab_*`, `zarf_*` …) —
  uçuş hattında değiller; yalnız `sim_matris.py`/`sim_kirici.py`'ye çapraz kontrol için bakıldı
* `fusion/inovasyonlu_j_v2.py` (CT-EKF), `pose/` (kalibrasyon/etiketleme hattı),
  `veriseti/`, `sdk/`, `iletisim/`, `png_sim/`, `sim/`
* `web/index.html` — yalnız ajan birkaç satır alıntıladı, JS denetlenmedi
* `arsiv/`, `*.yedek_*`, `*_ONCEKI_*`, `.claude/worktrees/` — **kasıtla atlandı**
* `dow_kopru.py`'nin PID/stick dönüşüm gövdesi (`:540-700`) — kazanç denetimi yapılmadı

---

*Denetim: 2026-08-16. Hiçbir kaynak dosya değiştirilmedi.*

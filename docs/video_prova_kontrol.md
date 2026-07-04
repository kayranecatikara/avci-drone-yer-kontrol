# Sim Uçuş Kanıt Videosu — Görünürlük Kontrol Listesi

> **Amaç:** Sim Teslim Esasları dokümanının "videoda görülmesi beklenen teknik
> çıktılar" 10 kalemini FSM provası sırasında TEK KADRAJDA okunabilir tutmak.
> Her kalem arayüzde nerede görünür + "tek kadrajda okunuyor mu" (✓/✗) işaretle.

| # | Kalem (şartname) | Arayüzde nerede | Prova ✓ |
|---|---|---|---|
| 1 | Simülasyon ekranı | Orta panel FPV (mss/PrintWindow oyun karesi) | ☐ |
| 2 | Drone + hedef saha konumu | Sağ panel: 🛸 AVCI (x/y/z) + 🎯 HEDEF (x/y/z) | ☐ |
| 3 | Bozuk GNSS kullanımı çıktısı/arayüz | 🎯 HEDEF (ham GPS) + HAM GPS–AVCI mesafe + FPV **HEDEF GNSS** rozeti | ☐ ⚠️(bkz. DEV notu) |
| 4 | Tespit anı | FPV bbox belirir + 🎯 TAKİP/PnP kartı doldu | ☐ |
| 5 | bbox + merkez + hedef ID + takip durumu | FPV: yeşil bbox + merkez nokta + `#id DURUM`; sağ TAKİP kartı | ☐ |
| 6 | Tracker aktif/pasif | TAKİP kartı `track durumu` (TENTATIVE/CONFIRMED/LOST); MODEL paneli | ☐ |
| 7 | Hedef kaybı / yeniden-tespit / süreklilik | Üstte uçucu banner: **HEDEF KAYBEDİLDİ (coast)** / **YENİDEN TESPİT**; `tespit_mi` coast göstergesi | ☐ |
| 8 | Güdüm komut telemetrisi | Sağ panel **🎮 GÜDÜM KOMUTU** (throttle/pitch/roll/yaw) | ☐ |
| 9 | Angajman kararı + vuruş anı | FSM durumu **ANGAJMAN** (kilit paneli) + mesafe vuruş menziline iner | ☐ |
| 10 | Görev sonu başarı çıktısı | Tam ekran **🎯 GÖREV BAŞARILI** overlay (min mesafe + "insan müdahalesi yok") | ☐ |

## Ek video kanıt panelleri (şartname videosu vurguları)
- **GNSS bağımlılığının azalması:** GORSEL_GUDUM'a geçince HEDEF GNSS rozeti YEŞİL
  "KULLANILMIYOR ✓" olur (kalem 3'ün güçlü hali) — kilit panelinde FSM durumu da izlenir.
- **Kilit süreci (§6.1.4):** 🔒 KİLİT SAYACI paneli (kümülatif/5 + pencere doluluk çubuğu +
  eksen kaplama + AV çerçevesi FPV overlay'de). Kilit tamamlanamazsa `engel` alanı hangi
  koşulda takıldığını gösterir (video anlatımında "model şu an göremiyor" kanıtı).
- **Otonomi:** manuel hedef seçimi YOK; tespit+tracking otonom (MODEL paneli + tespit anı).

## ⚠️ DEV-kaynak prova koşusu notu (kalem 3)
Bu FSM prova koşusu **hedef kaynağı = GERÇEK (DEV)** ile uçar (üretim filtresi
İnovasyonlu J bu koşuda devrede DEĞİL; midcourse bozulmamış hedef konumuyla
güdülür — amaç görsel hattı/FSM'i filtreden bağımsız doğrulamak). Sonuç:
- **Kalem 3 (bozuk GNSS kullanımı) bu koşuda İŞARETLENMEZ** → drone bozuk GNSS
  ile değil truth ile güdülüyor; "kullanım" kanıtlanamaz. Arayüzde kırmızı
  **GERÇEK (DEV)** bandı görünür; CSV'ye `hedef_kaynak=gercek` yazılır.
- Kalem 3, **teslim-videosu koşusunda** (kaynak = FİLTRE; İnovasyonlu J bozuk
  GNSS'i temizler) doğrulanır — asıl "bozuk GNSS girdi + filtre" kanıtı orada.
- Diğer 9 kalem (tespit/tracking/kilit/FSM/başarı) bu koşuda geçerli ve işaretlenir.

## Prova protokolü — OTOMATİK (kullanıcı kalem işaretlemez)
Marking artık otomatik: **yakalama + "üretildi" denetimi + "okunuyor" değerlendirmesi
+ doküman doldurma** araç ve asistan tarafından yapılır. Kullanıcının rolü yalnız
**"hazır" + (gerekirse) PLAY/FLY/E ve raporu okumak**.

1. **Yakalama (canlı):** `python arac/prova_kaydedici.py` FSM provası boyunca arka
   planda koşar. `/api/telemetry`'yi ~8 Hz yoklar; olay tetikli TAM ARAYÜZ (tarayıcı
   penceresi, PrintWindow) karesi + her 10 sn GENEL kare → `veri/prova_kareleri/`
   (`<olay>_<ts>.png` + `_50.png` %50 kopya). Olaylar: İLK_TESPİT, COAST_BAŞLADI,
   YENİDEN_TESPİT, FSM_GEÇİŞ_*, GÖREV_SONU. `olaylar.json`'a yazılır.
2. **"Üretildi mi" [CSV] otomatik:** `python arac/prova_kaydedici.py --rapor` uçuş
   CSV'sinden (ilk bbox, track_durumu geçişleri, tespit_mi coast blokları, güdüm
   komut sütunları, fsm_durum zinciri) kalem başına üretildi tablosu çıkarır.
3. **"Okunuyor mu" [kare] asistan:** koşu sonrası `prova_kareleri/` görüntüleri
   okunur (tam + %50 vekil = YouTube sıkıştırma proxy'si). Küçükte okunmayan kalem
   → arayüz düzeltmesi yapılır, "yapılan düzeltmeler" listesine yazılır.
4. **Sonuç:** aşağıdaki tablo otomatik doldurulur. Zayıf model kilidi tamamlayamazsa
   kalem 4-8 yine üretilir; kalem 9-10 İYİ MODEL geldiğinde (runbook MEVCUT_DURUM'da).

## Otomatik sonuç — FSM provası 2026-07-04 20:34 (DEV kaynak)
> Koşu: `ucus_log_20260704_203553.csv` + `olaylar.json` (159 olay/kare, ~4 dk).
> FSM tam çalıştı: ARAMA→TAKIP→GORSEL_GUDUM döngüsü, kilit sayacı + engel teşhisi
> canlı. Zayıf detection modeli (best.pt) kilidi **tutamadı** (hedef sürekli
> coast/LOST → kümülatif 5 sn'ye ulaşmadı), bu yüzden kalem 9-10 üretilmedi
> (İYİ MODEL runbook — beklenen). Kalem 1-8 üretildi ve **%50 vekilde de okunur**.

| # | Kalem | Üretildi [CSV] | Okunuyor [kare] | Kanıt dosyası | Not |
|---|---|---|---|---|---|
| 1 | Sim ekranı | (kare) | ✓ (tam+%50) | `ILK_TESPIT_203710`, `GENEL_*` | FPV canlı oyun görüntüsü + HUD (otomatik `/api/frame`) |
| 2 | Drone+hedef konum | (kare) | ✓ | `ILK_TESPIT_203710` | AVCI DRONE + HEDEF İHA panelleri tek kadrajda |
| 3 | Bozuk GNSS | DEV-atlandı | — | — | DEV kaynak koşusu; teslim koşusunda (filtre) doğrulanır |
| 4 | Tespit anı | ✓ (satır 469) | ✓ | `ILK_TESPIT_203710` | FPV yeşil bbox + `conf=0.50` (ölçülen tespit) |
| 5 | bbox+ID+durum | ✓ (6847 satır) | ✓ | `ILK_TESPIT_203710` | bbox + merkez nokta + `ex/ey/conf`; track durumu KİLİT panelinde |
| 6 | Tracker aktif/pasif | ✓ (103 geçiş) | ✓ | `YENIDEN_TESPIT_203717` | Sayan EVET/coast; MODEL DETECT; CONFIRMED↔LOST |
| 7 | Kayıp/yeniden-tespit | ✓ (52 coast/51 yeniden) | ✓ | `YENIDEN_TESPIT_203717` | Kırmızı bant: **"HEDEF KAYBEDİLDİ — takip sürüyor (coast)"** |
| 8 | Güdüm komutu | ✓ (9242/9242) | ✓ (düzeltme sonrası) | `FIXCHECK` | Panel AVCI DRONE'un altına alındı → tek kadrajda (aşağıda) |
| 9 | Angajman/vuruş | YOK | — | — | Zayıf model kilidi tamamlayamadı → ANGAJMAN 0 kare (İYİ MODEL runbook) |
| 10 | Görev sonu başarı | YOK | — | — | Angajman olmadı → başarı ekranı tetiklenmedi |

**Ek gözlem (kalem 3'ün güçlü hali):** GORSEL_GUDUM'da FPV'de **HEDEF GNSS:
KULLANILMIYOR ✓** yeşil rozeti okundu — GNSS bağımlılığının azaldığı an görünür
(kalem 3'ün "kullanım" kanıtı yine teslim/filtre koşusuna bırakıldı).

**Yapılan arayüz düzeltmeleri (prova bulgusu → düzeltme):**
- **Kalem 8 tek-kadraj:** GÜDÜM KOMUTU paneli TELEMETRİ sütununda 6. sıradaydı;
  DEV bandıyla birlikte kadraj dışına (scroll altına) düşüyordu. Panel **AVCI
  DRONE'un hemen altına (2. sıra)** taşındı → throttle/pitch/roll/yaw artık üst
  kartlarla aynı karede. `FIXCHECK` karesiyle doğrulandı.

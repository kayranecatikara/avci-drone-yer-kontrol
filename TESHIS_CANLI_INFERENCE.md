# Canlı Inference Teşhisi — SONUÇ RAPORU (2026-07-08)

**Şikâyet:** best.pt kayıtlı videoda hızlı/isabetli; canlı ekran yakalamada gecikme,
"geç algılama" izlenimi.
**Branch:** `teshis/canli-inference`.
**Kök neden (ölçülmüş): GPU contention — UE sim + inference aynı RTX 4060'ta.
Kareler, renk, çözünürlük, model, capture hattı TEMİZ (aşağıda kanıtlar).**

---

## KANIT ZİNCİRİ (aşama aşama)

### Aşama 2 — Ortam: TEMİZ
python 3.12.10 (sistem; launcher venv kullanmıyor), torch 2.5.1+cu121, CUDA aktif,
RTX 4060 Laptop 8 GB, ultralytics 8.4.83. "CPU'da koşuyor" hipotezi ELENDİ.

### Aşama 3 — A/B kare testi: KARELER VE MODEL TEMİZ ✅
Canlı hattan dump edilen 100 kare (modele giren array'in birebiri) vs `araclar/vid.mp4`
(2935 kare, 60 fps, 1920×1080; her 29. kare → 100 örnek). Aynı model/imgsz/eşikler:

| metrik | A: canlı dump | B: video | fark |
|---|---|---|---|
| tespit @0.25 | %31.0 | %34.0 | −3.0 puan |
| tespit @0.45 (kilit) | %23.0 | %20.0 | +3.0 puan |
| conf ort (≥.25) | 0.578 | 0.503 | +0.075 |

→ ±%5 bandının İÇİNDE (kabul kriteri sağlandı); canlı conf hatta daha iyi.
Çapraz kontrol: dump anındaki canlı det oranı (%22-35) aynı karelerin offline
oranıyla (%31) tutarlı → canlı pipeline offline davranışı birebir üretiyor.

### Aşama 4 — Görüntü içeriği: TEMİZ ✅
Dump PNG göz kontrolü: gökyüzü MAVİ (BGR/RGB takası yok), doğal 1920×1080,
kadrajda yalnız oyunun kendi OSD'si (bizim panel yok), DPI kayması yok.

### Aşama 5 — Backlog: YOK ✅
`kare_yas` p50 ~20-33 ms, ZAMANLA BÜYÜMÜYOR (kuyruk yok — latest-frame tasarımı
doğrulandı). `kaynak` kolonu hep `wc` → sessiz mss fallback YOK.

### Aşama 6 — GPU contention: **KÖK NEDEN BU** ❌
Sabit karede 200-iter bench (`veri/teshis_bench.csv`):

| koşul | ort ms | p50 | p95 | efektif FPS |
|---|---|---|---|---|
| sim KAPALI (FP32) | 18.9 | 17.9 | 22.3 | 52.8 |
| sim KAPALI (half) | 18.0 | 17.4 | 20.0 | 55.6 → *half kazanç YOK (8.4'te deprecated)* |
| sim AÇIK | 40.6 | 37.2 | 65.6 | 24.7 → **2.1× yavaşlama (sim tek başına)** |
| sim AÇIK + arayüz dedektörü de koşuyor | 57.5 | 51.9 | 102.8 | 17.4 |
| sim AÇIK + dedektör + 2. bench | 86.0 | 84.5 | 138.3 | 11.6 → **yük yığıldıkça katlanıyor** |

Canlı görev ölçümü (`veri/teshis_zaman_20260708_215114.csv`, 811 kare):
**infer p50 60-118 ms (offline'ın 3-6×), FPS ort 10.8, uçtan-uca yaş ort 104 ms /
p95 176 ms** → "geç algılama" hissinin ta kendisi. Kare yakalama ise sağlıklı (~22 ms).

Kritik iki bulgu: (1) oyun `FrameRateLimit=0` (SINIRSIZ FPS) ile koşuyordu — GPU'nun
tamamını yiyor; (2) dedektör döngüsü sleep'siz SERBEST KOŞUda — boş GPU'da 53 Hz'e
kadar çıkıp oyunla kapışmayı büyütüyor (bench tablosundaki yığılma kanıtı).

### Aşama 7 — Hızlı kontroller: hepsi zaten doğru ✅
Model TEK sefer + warmup ile yükleniyor; `verbose=False`; çizim tarayıcı canvas'ında
(döngüde matplotlib yok); capture+inference worker thread'de, UI ayrı; kuyruk yok.

---

## UYGULANAN DÜZELTMELER (minimal diff)

1. **Oyun FPS sınırı 60** (master çözüm #1): `FrameRateLimit=0 → 60`
   `C:\Users\Zeylo\AppData\Local\DronesOfWar\Saved\Config\Windows\GameUserSettings.ini`
   (yedek: aynı yerde `.yedek_teshis_20260708`; oyun kapalıyken değiştirildi).
   Not: VSync açık ve `sg.ResolutionQuality=50` zaten performans modunda.
2. **Dedektör hız tavanı** (`web/server.py` `DEDEKTOR_HEDEF_HZ = 15.0`):
   döngü 15 Hz'den hızlıysa kalanı uyur → GPU sim'e döner. Contention'da sleep
   0'a düşer (bugünkü davranışla birebir); canlı ölçüm zaten ~11-16 Hz'ti →
   güdüm kadansı DÜŞMEZ (kilit 5 ardışık = 0.33 s @15 Hz < VIS_STALE_S=0.5).
   `0` = eski serbest koşu (tek satır geri dönüş).
3. **Çoklu-örnek koruması** (`web/server.py`): `allow_reuse_address=False`.
   Windows'ta http.server varsayılanı, port dinlenirken İKİNCİ sunucunun hatasız
   bağlanmasına izin veriyordu → 8 Tem doğrulamasında 3 "hayalet" arayüz üst üste
   birikti (yeni kod hiç devreye girmedi). Artık ikinci örnek `[HATA] 8000 portu
   açılamadı` deyip çıkar — bat'taki "TEK arayüz" uyarısının teknik karşılığı.
4. **TensorRT engine** (`models/best.engine`, 9 Tem): best.pt → GPU'ya derlenmiş
   FP16 engine. server.py görev başlangıcında engine VARSA otomatik yükler, yoksa
   .pt'ye zarif düşer (`Cfg.VIS_MODEL_PATH` yanındaki `.engine`). Engine MAKİNEYE
   ÖZELDİR → gitignore'lu; başka makinede `pip install tensorrt` + `python
   araclar\teshis_trt_export.py` (~8-10 dk, tek sefer) ile yeniden üretilir.
   **Doğrulama (`teshis_engine_kiyas.py`, aynı 100 canlı karede engine vs .pt):**
   det@.45 birebir aynı (%23=%23), conf farkı −0.021, kutu merkezi kayması medyan
   **0.6 px** → FP16 tespiti BOZMUYOR. Hız (sim kapalı, tek kare 200-iter):
   engine 17.6 ms ort / **max 32.6** vs .pt 18.9 ms / max 58.4 → engine kuyruğu
   (p95/max) yarıya indiriyor; asıl kazanç contention altında ölçülecek (aşağıda).
   Kare 1280×1280 kullanıldı (server'ın imgsz=1280 scalar sözleşmesiyle uyumlu;
   rect 736×1280 daha hızlı ama sabit-şekil çakışmasıyla canlıda çöküyor — export
   scriptindeki UYARI).
5. Uygulanmayanlar (ölçüm gerekçesiyle): `half=True` .pt'de (kazanç yok, deprecated;
   FP16 kazancı zaten engine'de), `max_det=1` (etkisiz), dxcam'e geçiş (WGC zaten
   latest-frame + occlusion-proof, yaş ~22 ms sağlıklı), 640-crop (engine yeterse gereksiz).

## Yan bulgular
- `models/talon_pose.pt` diskte YOK (24f1769'da silinmiş) → poz gözlemcisi sessizce
  kapalı; CLAUDE.md hâlâ "entegre" diyor. Kurtarma: `git checkout 7d329b4 -- models/talon_pose.pt`.
  Geri getirilecekse GPU maliyeti `--poz` bench'iyle ölçülmeli.
- A/B script'inde video kareleri arası uzun CPU-decode boşlukları GPU'yu
  downclock'a sokup inference'ı şişiriyor (77 ms) — offline hız kıyası için
  `teshis_gpu_bench.py` kullanılmalı (A/B yalnız doğruluk içindir).

## BEFORE / AFTER

Bench (sim KAPALI, tek kare 200-iter) — düzeltmelerin kendi başına etkisi:
| model | ort ms | p95 | max | not |
|---|---|---|---|---|
| best.pt (BEFORE) | 18.9 | 22.3 | 58.4 | kuyruklu |
| best.engine (AFTER) | 17.6 | 22.3 | **32.6** | FP16, kuyruk yarıya |

Canlı görev (sim AÇIK) — asıl ölçüm, KULLANICI UÇUŞU BEKLİYOR:
| metrik (sim açık, canlı görev) | BEFORE (8 Tem, ölçüldü) | AFTER (engine + FPS sınırı) | hedef |
|---|---|---|---|
| infer p50 | 60-118 ms | ölçülecek | — |
| uçtan-uca yaş ort / p95 | 104 / 176 ms | ölçülecek | < 50 ms ort, büyümüyor |
| dedektör FPS | 10.8 ort | ölçülecek | ≥ 30 (FPS bacağı kare+oyun; 15 Hz tavan bilinçli) |
| tespit doğruluğu | video ±%5 içinde ✅ | engine ±%5 (doğrulandı) | ±%5 |

**Son doğrulama (5 dk):** Oyunu aç (60 FPS sınırlı) → **arayüzü BİR kez** aç
(konsolda `[GORSEL] TensorRT engine yuklendi` satırını gör) → OTO görev ≥30 sn →
`[TESHIS]` satırlarını gönder (CSV'yi ben de okurum). Engine + FPS sınırı yetmezse
sıradaki kademe: 640 crop (LOCKED) — ama önce bunun sayısını görelim.

## Değişen dosyalar
- `web/server.py` — teşhis kronometreleri + `/api/teshis` + **DEDEKTOR_HEDEF_HZ tavanı**
  + `allow_reuse_address=False` + **engine otomatik yükleme** (yoksa .pt zarif düşüş)
- `detection/pencere_yakala.py` — kare varış zaman damgası
- `araclar/teshis_ab_test.py`, `teshis_gpu_bench.py`, `teshis_engine_kiyas.py`,
  `teshis_trt_export.py` — YENİ ölçüm/export araçları
- `requirements.txt` — opsiyonel tensorrt notu; `.gitignore` — engine/onnx/vid.mp4
- `GameUserSettings.ini` (repo dışı, yedekli) — FrameRateLimit 0→60
- `models/best.engine` (gitignore'lu, makineye özel) — TensorRT FP16 engine

# GÖREV: Model Registry — Modüler Model Test Altyapısı

## Bağlam
Yarışma pipeline'ı kuruldu (master_prompt_yarisma_pipeline.md kapsamı): `detection/algi_hatti.py` (tespit→takip→PnP tek döngü), `detection/kamera_model.py` (K + tilt tek kaynak), pose'suz mod, kilit kuralı/FSM. `detection/gorsel_tespit.py` şu an tek sabit model yolu kullanıyor. Elde birden fazla model var ve çoğalacak: zayıf detection (`models/best.pt`), zayıf pose .pt'ler, eğitilecek yeniler. Bunlar inference'te kıyaslanacak.

**Bu dosya YALNIZCA model registry/test altyapısını tanımlar.** PnP, OIPN, takip, kilit — hepsi pipeline'da zaten kurulu; burada yeniden tanımlanmaz, herhangi bir görünür çelişkide pipeline sözleşmeleri esastır.

**Başlamadan önce oku:** `CLAUDE.md`, `MEVCUT_DURUM.md`, `detection/gorsel_tespit.py`, `detection/algi_hatti.py`, `web/server.py`, `web/index.html`.

## Hedef
`models/` klasörüne yeni bir `.pt` atınca **kod değişikliği olmadan** arayüzde görünsün, uçuş/test sırasında takılıp çıkarılabilsin, performansı canlı izlensin ve CSV'ye loglansın.

## 1. Model Registry — yeni dosya: `detection/model_yonetici.py`
- `models/` klasörünü tarar, tüm `.pt` dosyalarını bulur (dosya adı = model kimliği; anlamlı adlandırma beklenir, örn. `yolov8n_pose_v005_640.pt`)
- **Task otomatik ayırt edilir:** yükleme sonrası `model.task` ('detect' / 'pose'). Pose modelinde `kpt_shape` okunur; `[6, 3]` beklenir — uymayan model arayüzde uyarıyla işaretlenir, yüklenemez.
- **Keypoint şeması burada sabitlenmez:** hangi isim/sıra şemasının geçerli olduğu pipeline'daki şema-keşfi sözleşmesine tabidir (eski motor'lu / yeni kuyruk_ucu'lu modeller birlikte var olabilir). Registry, model başına şema bilgisini metadata olarak taşır (aşağıdaki yaml), PnP tarafı object-points setini buna göre seçer.
- Her `.pt`'nin yanında aynı adlı `.yaml` varsa per-model config olarak okur:
```yaml
  imgsz: 640        # inference görüntü boyutu
  conf: 0.25        # SADECE görselleştirme/metrik eşiği (Kısıtlar'a bak)
  iou: 0.45         # NMS IoU eşiği
  half: true        # FP16 inference
  sema: kuyruk_ucu  # pose için: kuyruk_ucu | motor (PnP object-points seçimi)
  aciklama: "yolov8n-pose, v0.0.5 dataseti, 640px"
```
  `.yaml` yoksa default'lar kullanılır (şema default'u: pipeline'ın güncel şeması).
- API: `modelleri_listele()`, `tara()`, `model_yukle(ad)` (arka planda), `aktif_model()`, `metrikler()`

## 2. Çıktı sözleşmesi — pipeline'ınki ESASTIR
- Çekirdek `{cx, cy, conf}` + opsiyonel `keypoints` sözleşmesi pipeline'da zaten kurulu; registry bunu DEĞİŞTİRMEZ, yalnızca hangi modelin ürettiğini yönetir.
- Pose→detect swap'inde `keypoints` kaybolur → pipeline'ın mevcut davranışı devreye girer (PnP otomatik pasif, OIPN 0, IBVS fallback). Swap bu davranışı tetiklemekten fazlasını yapmamalı; guidance/FSM tarafına dokunulmaz.

## 3. Thread-safe hot-swap
1. Yeni model **arka plan thread'inde** yüklenir; algı döngüsü eski modelle kesintisiz devam eder
2. 3 dummy frame warmup (CUDA context + cuDNN autotune ısınması; warmup'sız ilk inference'ler gerçeğin 10–100 katı ölçülür ve swap anında stall olur)
3. Lock ile korunan **tek atomik referans ataması** ile swap
4. Eski referans bırakılır, `torch.cuda.empty_cache()`
5. Hata durumunda (bozuk .pt, VRAM yetmezliği) eski model aktif kalır, hata arayüze düşer
6. detect↔pose geçişi uçuş sırasında güvenli: FSM bozulmaz, keypoints'in gelip gitmesi pipeline'ın pose'suz-mod geçişini tetikler ve loglanır

## 4. Doğru latency ölçümü ve metrikler
- GPU'da ölçüm `torch.cuda.synchronize()` ile — CUDA çağrıları asenkrondur; synchronize olmadan yalnızca kernel launch süresi ölçülür, latency gerçeğin çok altında görünür
- Kayan pencere (son 100 frame): ortalama ve p95 inference süresi (ms), efektif FPS, frame başına tespit sayısı, ort/maks conf
- **Pose ekleri:** görünür keypoint sayısı, ortalama keypoint conf, **PnP-uygun frame oranı** (eşik üstü ≥4 keypoint'li frame yüzdesi) — pose modelinin "PnP'yi besleyebilme" kalitesini tek sayıda özetler
- Ultralytics `results[0].speed` ile kendi ölçümünün tutarlılığını bir kez doğrula; fark varsa yorum satırında belgele

## 5. Arayüz + CSV
- Model seçici dropdown + "Yükle" + "↻ Tara" + durum rozeti (hazır/yükleniyor/hata) + task rozeti (DETECT/POSE) + şema rozeti (pose için)
- Canlı metrik paneli: model adı, FPS, ort/p95 latency, son conf, (pose ise) keypoint metrikleri + PnP-uygun oranı
- `veri/model_test_YYYYMMDD_HHMMSS.csv`: `timestamp, model_adi, task, sema, inference_ms, tespit_sayisi, en_yuksek_conf, cx, cy, bbox_alan_orani, gorunur_kp, ort_kp_conf`
- Model swap olayları ayrı satır (offline kıyasta segment sınırı)

## Kısıtlar
- **Kilit/angajman kararını besleyen üretim conf eşiği yerinde kalır** (muhafazakâr; yanlış kilit paketi −30). Per-model yaml `conf` yalnızca görselleştirme/metrik içindir; kilit zincirine ASLA girmez.
- Pipeline sözleşmelerine (AlgiCiktisi, türev kuralı, 50 Hz timing, görüntü kaynağı, truth sert ayrımı) dokunulmaz; `fusion/` dokunulmaz; `CLAUDE.md` geçerli.
- Kapsam dışı: eşzamanlı iki-model A/B inference (FPS'i böler; kıyas CSV segmentleriyle offline yapılır); PnP/OIPN/takip/kilit tanımları (pipeline'da kurulu).

## Kabul kriterleri
1. `models/` içine yeni `.pt` kopyalanıp "↻ Tara" basılınca dropdown'da görünüyor
2. Uçuş/test sırasında swap yapılınca FSM bozulmuyor; algı kesintisiz akıyor
3. detect↔pose geçişi hatasız; pipeline'ın pose'suz moda düşüşü/çıkışı loglarda görünüyor
4. CPU fallback ayakta (GPU yoksa yavaş ama çalışır)
5. Warmup'ın çalıştığı loglardan kanıtlanabiliyor (öncesi/sonrası latency farkı)
6. Kasıtlı bozuk `.pt` yüklenmeye çalışılınca hata arayüzde, aktif model çalışmaya devam ediyor
7. Yanlış `kpt_shape`'li pose modeli reddediliyor ve nedeni arayüzde görünüyor

## Test planı
Model A (detect) ~30 sn → swap → model B (pose) ~30 sn: CSV'de segmentler swap satırıyla ayrık; her segmentin ort/p95 latency'si hesaplanabiliyor; pose segmentinde PnP panelinin aktifleştiği, detect segmentinde pasifleştiği loglardan izlenebiliyor. Aynı mekanizma **detect↔detect kıyası** için de geçerlidir: iki detection modeli art arda koşulur, segment metrikleri (FPS, latency, conf dağılımı, tespit sayısı) karşılaştırılır — "hangi detection daha iyi" sorusunun cevabı bu CSV kıyasından okunur.
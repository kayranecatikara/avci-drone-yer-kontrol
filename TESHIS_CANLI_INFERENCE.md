# Canlı Inference Teşhisi — Durum Raporu + Ölçüm Protokolü (2026-07-08)

**Amaç:** best.pt kayıtlı görüntüde hızlı/isabetli; canlı ekran yakalamada gecikme /
geç algılama izlenimi. Kök nedeni ÖLÇEREK bulmak (tahminle değişiklik yok).
**Branch:** `teshis/canli-inference` — yalnız ölçüm katmanı eklendi, güdüm/arayüz
davranışı DEĞİŞMEDİ.

---

## Aşama 0 — Keşif: iki hattın kıyası

| Boyut | CANLI hat (`web/server.py` dedektör döngüsü) | OFFLINE/video hattı | Master "hedef mimari"den sapma |
|---|---|---|---|
| Yakalama | **windows-capture** (WGC, pencere-içeriği, occlusion-proof) → `get_latest_bgr`; mss **fallback** | `cv2.imread` / `cv2.VideoCapture` | dxcam YOK — WGC eşdeğeri (latest-frame semantiği aynı, kuyruk yok) |
| Renk | BGR (WGC `convert_to_bgr`; mss BGRA→BGR) — ultralytics ndarray'i BGR varsayar ✓ | BGR ✓ | — |
| Çözünürlük | pencere DOĞAL boyutu (küçültme yok; 960 yalnız FPV JPEG) | kayıt çözünürlüğü | LOCKED 640×640 crop YOK — hep tam kare |
| imgsz | 1280 (640'ta uzak hedef çöküyor — bilinçli) | 1280 | — |
| conf | predict `min(0.25, VIS_CONF_MIN)`; güdüm kapısı 0.45 | ölçüm tabanı 0.10 | — |
| device / half / max_det | cuda ✓ / **FP32** / default(300) | cuda ✓ | `half=True` yok (ölçüldü: kazanç yok, aşağıda); `max_det=1` yok (etkisi ihmal) |
| verbose | False ✓ | False ✓ | — |
| Model yükleme | lazy TEK sefer + warmup ✓ (döngüde değil) | tek sefer + warmup | — |
| Threading | dedektör ayrı daemon thread; sonuç `beyin_lock` ile yazılır; çizim TARAYICI canvas'ında (matplotlib yok) | — | — |
| Kuyruk/backlog | YOK — hep en son kare | — | — |
| Pacing | kare varsa **sleep YOK → serbest koşu** (GPU'yu tek başına doyurur) | — | SEARCHING düşük frekans stratejisi yok — **şüpheli** |

## Aşama 2 — Ortam kontrolü: **GEÇTİ** (CPU hipotezi elendi)

```
python : 3.12.10 (sistem kurulumu; 2_Arayuzu_Baslat.bat venv KULLANMIYOR, PATH'teki python)
torch  : 2.5.1+cu121 | cuda: 12.1 | available: True
gpu    : NVIDIA GeForce RTX 4060 Laptop GPU (8 GB, sürücü 592.27)
ultra  : 8.4.83
```
Canlı kodda cihaz zaten basılıyor: `[GORSEL] best.pt yuklendi (device=cuda)` satırını doğrula.

## Baseline ölçümler (8 Tem, sim KAPALI, sentetik 1080p kare, n=200)

| etiket | ort ms | p50 | p95 | max | efektif FPS |
|---|---|---|---|---|---|
| sim_kapali (FP32) | 18.9 | 17.9 | 22.3 | 58.4 | **52.8** |
| sim_kapali_half | 18.0 | 17.4 | 20.0 | 41.8 | 55.6 |

Yorum: model offline HIZLI (bc1e0b3 commit'indeki 53 kare/sn ile birebir) → "videoda
hızlı" gözlemi doğrulandı. FP16 kazanç YOK (ultralytics 8.4'te `half` deprecated;
gerekirse doğru yol TensorRT export). Sorun ağırlıklarda değil, **canlı koşullarda**.

## Yan bulgular (önemli)

1. **`models/talon_pose.pt` diskte YOK** — `24f1769` (6 Tem temizlik) commit'inde
   silinmiş. Canlıda poz gözlemcisi sessizce KAPALI (konsolda `[POZ] ... yok ->
   poz kestirimi kapali`). CLAUDE.md hâlâ "entegre" diyor. Kurtarma tek komut:
   `git checkout 7d329b4 -- models/talon_pose.pt` (42 MB). **Sonuç:** bugünkü canlı
   GPU yükü = yalnız best.pt; "poz modeli GPU yiyor" hipotezi bugün İÇİN geçersiz.
   Geri getirilirse maliyeti `--poz` bench'iyle ölçülecek.
2. Dedektör döngüsünde kare varken sleep yok → **kendi inference'ımız GPU'yu serbest
   koşuda doyurur**; sim açıkken karşılıklı kapışmayı büyütebilir (H2).

## Hipotezler (öncelik sırasıyla; hepsi ölçümle karara bağlanacak)

- **H1 — GPU contention:** UE sim + inference aynı RTX 4060'ta. Kanıt: bench
  `sim_acik` vs `sim_kapali` farkı + dmon logu.
- **H2 — Serbest koşu katkısı:** dedektör sınırsız hızda koşup sim'in FPS'ini
  düşürüyor, sim de inference'ı yavaşlatıyor (sarmal). Kanıt: canlı `[TESHIS]`
  FPS/infer değerleri vs bench.
- **H3 — Kare yaşı / capture kadansı:** WGC kareyi oyunun render hızında üretir;
  oyun yük altında 20 FPS'e düşerse kare yaşı büyür. Kanıt: `kare_yas` / `uctan_uca`
  kolonları. `uctan_uca` ZAMANLA BÜYÜYORSA backlog/contention kesin bulgu.
- **H4 — Capture içeriği (renk/ölçek/bölge):** 6 Tem düzeltmeleri sonrası beklenti
  TEMİZ. Kanıt: A/B kare testi + dump PNG'lerine gözle bakış (gökyüzü MAVİ mi?).
- **H5 — Sessiz mss fallback:** WGC düşerse kaynak mss olur (yavaş + yanlış içerik
  riski). Kanıt: CSV `kaynak` kolonunda `mss` görünmesi.

## Eklenen ölçüm katmanı (davranış değiştirmez)

- `veri/teshis_zaman_<ts>.csv` — kare başına: `kare_yas_ms` (yakalama→inference
  başı), `capture_ms`, `infer_ms`, `poz_ms`, `yaz_ms` (kilit bekleme dahil),
  `dongu_ms`, `uctan_uca_ms` (**frame age**: yakalama→sonuç yayını), `fps`,
  `kaynak` (wc|mss), `det`, `conf`.
- Konsolda her ~10 sn `[TESHIS] ...` özet satırı (p50/p95).
- `GET /api/teshis` — son özet JSON. `POST /api/teshis {"dump_kare":100}` — modele
  giren array'in birebiri PNG olarak `veri/teshis_kareler/<ts>/` (dump sırasında
  FPS düşer, normal).
- Araçlar: `araclar/teshis_ab_test.py` (Aşama 3 A/B), `araclar/teshis_gpu_bench.py`
  (Aşama 6 contention; `--poz`, `--half`, `--dmon` seçenekleri).

---

# ÖLÇÜM PROTOKOLÜ (kullanıcı adımları — sırayla, hepsi repo kökünden)

**A. Sim AÇIK bench (H1/H2):** Oyunu başlat (PLAY modunda bekle), sonra:
```
python araclar\teshis_gpu_bench.py --etiket sim_acik --dmon
```
(Karşılaştırma satırı `veri/teshis_bench.csv`'ye eklenir; sim_kapali taban zaten orada.)

**B. Canlı görev ölçümü (30-60 sn):** Arayüzü başlat (`2_Arayuzu_Baslat.bat`),
OTONOM görevi başlat, hedef kamera görüşüne girecek şekilde ≥30 sn koştur.
Konsoldaki `[TESHIS]` satırlarını olduğu gibi kopyala (özellikle: FPS, kare_yas,
UCTAN-UCA p50/p95 ve bunların ZAMANLA büyüyüp büyümediği).

**C. Kare dump (görev SÜRERKEN, ayrı PowerShell penceresinde):**
```
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/teshis -Method Post -Body '{"dump_kare":100}' -ContentType 'application/json'
```
Çıktıdaki `klasor` yolunu not et. Bittiğinde konsolda `kare dump TAMAM` yazar.

**D. A/B testi (görev bittikten sonra; sim kapatılabilir):**
```
python araclar\teshis_ab_test.py --a veri\teshis_kareler\<KLASOR> --b "<referans video.mp4 veya kare klasörü>" --n 100 --adim 5
```
Referans video yoksa `--b`'siz de koş; script yorumu kendisi basar.
Ek göz kontrolü: dump PNG'lerinden birkaçını aç — gökyüzü mavi mi, kadrajda
arayüz/panel var mı, çözünürlük beklenen mi?

**E. Bana getir:** `[TESHIS]` satırları, `veri/teshis_zaman_*.csv`,
`veri/teshis_bench.csv`, A/B çıktısı, dump klasör yolu. Düzeltme kararları
(UE `t.MaxFPS`, dedektör hız tavanı, TensorRT, crop stratejisi) bu ölçümlere göre
ve minimal diff ile verilecek.

## Kabul kriterleri (master prompt)
- Sim açıkken uçtan uca gecikme (`uctan_uca_ms`) ort < 50 ms ve zamanla büyümüyor.
- FPS ≥ 30, stabil.
- Canlı karelerde ort. conf ve tespit oranı, referansın ±%5 bandında.
- Rapor + before/after tablo + değişen dosya listesi. *(Before kolonu B adımındaki
  ilk canlı ölçümden dolacak.)*

## Değişen dosyalar (bu branch)
- `detection/pencere_yakala.py` — kare varış zaman damgası (+`get_latest_bgr_t`)
- `web/server.py` — teşhis kronometreleri + CSV/özet + `/api/teshis` (GET özet,
  POST dump); `grab_frame_bgr_t()` (eski `grab_frame_bgr` imzası korunur)
- `araclar/teshis_ab_test.py` (YENİ), `araclar/teshis_gpu_bench.py` (YENİ)

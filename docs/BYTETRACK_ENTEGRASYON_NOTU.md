# ByteTrack Entegrasyon Notu (Kayra'nın hattı için — 2026-07-07)

*A/B kıyası bulgusu: mevcut hat tek en-yüksek-conf kutu (argmax) kullandığı için 120 sn
görevde 72 tespit-kaybı kenarı / 30 farklı ID üretti. `detection/takip.py` (ByteTrack +
gyro-CMC) ID sürekliliği + kayıpta kısa-süreli tahmin (coast) sağlar; video isteri
"tracking aktif" kanıtına da birebir. Modül bağımsızdır, güdüme dokunmaz.*

## Ne veriyor
- **BYTE eşleştirme:** yüksek-conf kutular track'lerle eşleşir; eşleşmeyen track'ler
  DÜŞÜK-conf kutularla ikinci tur eşleşir (zayıf tespit ID'yi yaşatır, yeni track AÇAMAZ).
- **Kalman + coast:** ölçüm yokken kısa süre tahminle sürer (`tespit_mi=False` işaretli).
- **gyro-CMC:** kendi dönüşün (roll/pitch/yaw) kutuları kaydırmasını homografiyle telafi
  eder → hızlı yaw'da ID kopmaz (`detection/kamera_model.cmc_homografi`).

## Minimal bağlama (server.py `dedektor_dongusu` içinde)
```python
from detection.takip import Takipci
from detection import kamera_model

takipci = Takipci()                    # dedektör kurulumunun yanında BİR KEZ
onceki_att, onceki_t = None, None
...
# MEVCUT:  det = dedektor.tespit_et(bgr)          (argmax tek kutu)
# YENİ:
dets = dedektor.tespit_hepsi(bgr)                  # TÜM kutular, conf azalan
att  = drone.get_drone_rotation()
simdi = time.perf_counter()
dt = (simdi - onceki_t) if onceki_t else 0.05
H_cmc = None
if onceki_att is not None and dets:
    W_, Hh = dets[0]["W"], dets[0]["H"]
    H_cmc = kamera_model.cmc_homografi(W_, Hh, onceki_att, att)
onceki_att, onceki_t = att, simdi
det = takipci.guncelle(dets, dt, H_cmc)            # en iyi CONFIRMED track | None
# det sözleşmesi mevcutla uyumlu: {cx,cy,w,h,conf,W,H} + track_id/track_durumu/tespit_mi
```

## Önemli ayarlar
- **Predict eşiğini DÜŞÜK tut** (0.10–0.25): BYTE'ın ikinci turu düşük-conf kutuları
  kullanır. Güdüm kapısı yine `conf >= VIS_CONF_MIN` kalır (track conf'u üzerinden) —
  davranış değişmez, sadece ID sürekliliği gelir.
- Eşikler `detection/takip.py` `TakipCfg` içinde: `CONF_YUKSEK/CONF_DUSUK/IOU_ESIK/
  MIN_HITS/MAX_COAST`.
- UI zaten `track_id`/`tespit_mi` alanlarını tanıyor (coast turuncu-kesikli çizim).

## Doğrulama
- Birim test: `python test/test_takip.py` (ID sürekliliği, coast, CMC senaryoları).
- Uçuşta ölçüm: `python arac/ab_kiyas.py kos --etiket main-bytetrack --n 3` →
  `python arac/ab_kiyas.py rapor --a main --b main-bytetrack`
  (bak: "takip kayıp med" 72'den düşüyor mu, başarı/en-yakın bozulmuyor mu).

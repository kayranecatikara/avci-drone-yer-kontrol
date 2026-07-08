# 2 — Takip (ByteTrack + gyro-CMC)

**Dosya:** `detection/takip.py`

- **Ne yapar:** YOLO bbox'larını zamansal olarak ID'li track'lere bağlar.
  Görüntü düzleminde Kalman CV (sabit hız) ile ara-kare tahmin; ölçüm gelmeyince
  **coast** (tahminle sürdürme). Avcının dönüşü eşleşmeden önce **gyro-CMC** ile
  telafi edilir (kamera hareketi track'i kaydırmasın).
- **Neden bu tasarım:** BYTE ilişkilendirme — yüksek conf'lular önce, eşleşmeyen
  track'ler düşük conf'lularla ikinci turda eşleşir; blur/parazitte conf düşen
  Talon izi **kopmaz**. Tek-kare yanlış pozitif CONFIRMED olamadan ölür
  (−30 puanlık yanlış kilide karşı zamansal filtre).
- **Elenen alternatif:** SORT (ego-motion telafisi yok → drone dönüşünde ID
  kopar); DeepSORT (görünüm ağı — ağır + "açıklanamaz", kural 8). Görüntü-tabanlı
  CMC (ORB/ECC) → gökyüzü feature'sız, gyro daha güvenilir.
- **Kritik parametreler (`TakipCfg`):** `CONF_YUKSEK=0.5` / `CONF_DUSUK=0.1`
  (BYTE iki eşik); `MIN_HITS=5` (CONFIRMED — FSM "5 kare onayı"); `MAX_COAST=25`
  tik (~0.5 s); `IOU_ESIK=0.2` (warp sonrası). CMC: `H=K·R_Δ·K⁻¹`,
  `R_Δ,kam = R_mount^T·R_Δ,gövde·R_mount`.
- **Video ipucu:** FPV'de `#id DURUM` + TAKİP kartı (TENTATIVE→CONFIRMED→LOST);
  kayıp/yeniden-tespit üst banner (kalem 7) tracking'in aktif olduğunun kanıtı.

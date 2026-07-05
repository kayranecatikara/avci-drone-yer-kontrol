# 3 — Sensör Füzyonu / GNSS Filtreleme

**Dosya:** `fusion/inovasyonlu_j_v2.py` (İnovasyonlu J, CT-EKF GNSS düzeltici)

- **Ne yapar:** Bozuk hedef GNSS'i temizler — sıçrama/gecikme/kayıp/gürültüyü
  bastırır ve **hedef hızını kestirir**. Bu hız güdüme lead (öngörü) sağlar:
  hedefin gideceği yere nişan alınır. Kayıpta `HOLD_TICKS` boyunca son kestirim
  tutulur, sonrası dropout → loiter.
- **Neden bu tasarım:** Ham GNSS'e nişan almak sıçramada rotayı savurur; filtre
  inovasyonu (ölçüm−tahmin) kapılayarak aykırı GNSS'i reddeder. **Tamamen
  bizim/açıklanabilir kodumuz** (kural 8) — takımca her terimi savunabiliyoruz.
- **Elenen alternatif:** ham GPS doğrudan (sıçrama/gecikme güdüme sızar);
  **IMM-EKF veya bakmadığımız hazır filtre** → kural 8 gereği ENTEGRE EDİLMEZ,
  açıklayamadığımız hiçbir modül girmez.
- **Kritik parametreler:** filtre süreç/ölçüm gürültüsü ve inovasyon kapısı
  (`fusion/inovasyonlu_j_v2.py`); dropout: `HOLD_TICKS=300` / `DROPOUT_TICKS=300`
  (`guidance/ana_kontrol.py::Cfg`). **SERT AYRIM:** filtre yalnız bozuk GNSS'i
  girdi alır; truth kanalına erişmez (doğrulama `arac/` altında, uçuş dışı).
- **Video ipucu:** "GNSS bağımlılığının azalması" → FPV **HEDEF GNSS** rozeti
  GÖRSEL TAKİP'te yeşil "KULLANILMIYOR ✓"; GNSS hata/sıçramada rota bozulmaz.

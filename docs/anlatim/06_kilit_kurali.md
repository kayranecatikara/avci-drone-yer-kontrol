# 6 — Kilit Kuralı (§6.1.4)

**Dosya:** `guidance/kilit_kurali.py` (saf mantık, unit-test edilebilir)

- **Ne yapar:** "Kilitlenme"yi kodda somutlaştırır. Her algı karesinde sayaç
  koşulları denetlenir; **10 sn kayan pencerede kümülatif ≥5 sn** sayan-kare →
  `kilit_tamam` (kenar-tetikli, bir kez). Ayrıca `surekli_kilit_sn` (kesintisiz)
  angajman ön şartı için tutulur.
- **Sayaç koşulu (hepsi):** conf ≥ üretim eşiği · track **CONFIRMED** ·
  `tespit_mi=True` (coast sayılmaz) · dörtgen kadraj içinde · **eksen kaplama**
  `max(w/W,h/H) ≥ 0.06` (koşul, merkez/AV'den ÖNCE) · merkez **AV** içinde.
- **Neden bu tasarım:** Şartname kilit tanımına **dürüst** — coast'ta bbox
  tahminîdir, kilit sayılmaz. Kaçak karelere güvenmeden yalnız geçerli karelerle
  5 sn doldurulur (yanlış kilit paketi −30 puan).
- **Elenen alternatif:** alan-oranı kaplama (şartname EKSEN diyor); kaçağı
  kümülatife eklemek (toleransa güven → sahte kilit).
- **Kritik parametreler (`KilitCfg`):** `KAPLAMA_ESIK=0.06` (eksen, %5+pay);
  `AV_YATAY=(0.25,0.75)` / `AV_DIKEY=(0.10,0.90)`; `PENCERE_SN=10`,
  `KUMULATIF_HEDEF_SN=5`, `SUREKLI_ANGAJMAN_SN=3`; `KACAK_TOLERANS_SN=0.2`
  (%5 = 200 ms; kümülatifi ETKİLEMEZ, yalnız kesintisiz sayaçta ≤200 ms köprüler
  — ilk/son karede köprü yok); `CIZGI_PX=3`, `DORTGEN_KADRAJ_MIN=0.90`.
- **Video ipucu:** 🔒 KİLİT SAYACI paneli (kümülatif/5 + pencere doluluk + eksen
  kaplama + AV çerçevesi). Tamamlanamazsa `engel` alanı hangi koşulda takıldığını
  gösterir ("model şu an göremiyor" kanıtı).

# 1 — Input + Hedef Tespit

**Dosyalar:** `sdk/drone_sdk.py` (input), `detection/algi_hatti.py` +
`detection/model_yonetici.py` + `detection/gorsel_tespit.py` (tespit)

- **Ne yapar:** `drone_sdk` sim I/O'dur — telemetri (drone GPS/rotasyon) ve
  **bozuk hedef GNSS**'i girdi alır, kontrol komutu döndürür. Tespit hattı
  oyun karesini (`pencere_yakala`) alır, YOLO ile Talon bbox + güven üretir.
- **Neden bu tasarım:** `drone_sdk` şartnamedeki `input.py` muadilidir (resmî
  verili SDK — kural 8). YOLO seçildi: eğitilebilir, gerçek-zamanlı, tek-sahne
  gökyüzü hedefinde sağlam. `model_yonetici` registry ile modeli **uçuş
  durmadan** sıcak-değiştirir (video sırasında model gösterimi).
- **Elenen alternatif:** klasik CV (renk/şekil eşik) — parlaklık/blur altında
  dayanıksız; kendi TCP istemcisi yazmak — resmî SDK dururken gereksiz risk.
- **Kritik parametreler:** `VIS_CONF_MIN=0.45` (kilit/komut asgari güveni,
  `guidance/ana_kontrol.py::Cfg`); başlangıç modeli `config.VIS_MODEL_ADI="best"`
  → `models/best.pt`. Bozuk GNSS ham haliyle alınır, temizleme füzyondadır (kart 3).
- **Video ipucu:** "bozuk GNSS girdi olarak alınıyor" → sağ panelde **🎯 HEDEF
  (ham GPS)** + **HEDEF GNSS** rozeti; tespit anında FPV'de bbox belirir.

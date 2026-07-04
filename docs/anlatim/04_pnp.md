# 4 — PnP Poz Kestirimi (Talon)

**Dosya:** `detection/talon_pose_estimator.py`

- **Ne yapar:** YOLO-pose 6 anahtar noktasını (2D) bilinen **6-nokta 3D Talon
  modeliyle** eşleştirip `solvePnPRansac`+`refineLM` ile hedefin pozunu (yönelim
  + relatif menzil) kestirir. Çıktısı OIPN'e hedef roll `φ_T` verir ve menzili
  çapraz-kontrol eder.
- **Neden bu tasarım:** OIPN'in erken-manevra sinyali için hedefin **roll**'una
  ihtiyaç var (koordineli dönüşte roll, heading değişiminden önce gelir). PnP bunu
  tek kameradan, geometrik ve açıklanabilir biçimde verir.
- **Elenen alternatif:** monoküler derinlik/pose ağı (kara-kutu, "açıklanamaz");
  stereo (tek kamera var). Uzak-alanda **k-taraması dejenere** (fx–tvec belirsizliği)
  → menzil kestirimi yalnız yakın-alanda anlamlı, `guvenilir` bayrağıyla işaretli.
- **Kritik parametreler:** reproj kapısı **8 px** (üstü → poz reddi), `kpt_shape=[6,3]`
  (model uygun değilse PnP otomatik **pasif**), şema-parametrik (`kuyruk_ucu | motor`).
  Poz güvenilmezse OIPN terimi **0** (kart 5), hat IBVS'e düşer.
- **Video ipucu:** PnP kartında reproj hata + `guvenilir`; **pose'suz TAM çalışır**
  (PnP/OIPN pasif → IBVS fallback), bunu anlatımda "güvenlik ağı" olarak göster.

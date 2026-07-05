# 7 — Görev FSM (ana_kontrol)

**Dosya:** `guidance/ana_kontrol.py` (FAZ 3 durum makinesi)

- **Ne yapar:** Görevi durum makinesiyle yürütür:
  **ARAMA → YAKLAŞMA → GÖRSEL_TAKİP → KİLİT_BİLDİR → ANGAJMAN.** ARAMA/YAKLAŞMA'da
  midcourse (füzyonlu GNSS ile bölgeye yaklaşma); CONFIRMED track + kilit koşulu
  oluşunca görsele devreder ve **hedef konumu artık YALNIZCA görsel** (bbox/PnP).
- **Adlandırma (şartname §6.1.2):** "takip" = GÖRSEL yönelim üretimidir. GNSS'li
  yaklaşma fazına "takip" demek video değerlendirmesinde yanlış-algı riskiydi →
  o faz **YAKLAŞMA (GNSS)**; görsel yönelim fazı **GÖRSEL TAKİP**. YAKLAŞMA kısa
  GNSS'li kapanıştır, **kilit/angajman zincirine dâhil değildir**.
- **Neden bu tasarım:** Şartname görev akışı + otonomi: manuel hedef seçimi YOK,
  tespit+tracking otonom devreye girer. GPS güdümü öldürücü faz değil — araca
  yönelip **kesintisiz görsel temas** kurup görsel faza temiz devretmektir.
- **Elenen alternatif:** tek-mod GPS güdüm (görsele devir yok → GNSS bozulunca
  kör); ham sayaç (FSM artık kilit'i `kilit_kurali`'na sorar, ByteTrack
  CONFIRMED'a devreder). Kayıpta erken vazgeçmek → `VIS_LOST_TO_GPS_S` ile
  YAKLAŞMA'ya (GPS) dönüş güvenlik ağı.
- **§6.1.2 üç "takip" şartının kanıt eşlemesi (GÖRSEL TAKİP fazı):**
  (1) **yönelim üretimi** → 🎮 GÜDÜM KOMUTU paneli + CSV `a_PN/a_APN_terim/a_OIPN_terim`;
  (2) **göreli konum güncelleme** → PnP (`reproj_err/phi_T`) / EKF hız kestirimi;
  (3) **tutarlı komutlar** → telemetri/CSV `thr_cmd/pitch_cmd/roll_cmd/yaw_cmd` kaydı.
- **Kritik parametreler (`Cfg`):** `HANDOFF_RANGE=4000` cm (tespit menzili),
  `VIS_N_LOCK=5` (ardışık geçerli-tespit → GÖRSEL TAKİP; handoff eşiği
  `VIS_CONF_MIN=0.45`), `VIS_LOST_TO_GPS_S=1.0`. Kilit AYRI sıkı eşik
  `KilitCfg.KILIT_CONF_MIN=0.72`; angajman `kilit_tamam` + kesintisiz ≥3 sn (kart 6).
- **Video ipucu / köprü cümlesi:** ATR belgesindeki **"TAKİP (Faz 2)"** = videodaki
  **GÖRSEL TAKİP**'tir; **YAKLAŞMA** kısa GNSS'li kapanıştır (kilit zincirine girmez).
  Panelde **FSM durumu**; GÖRSEL TAKİP'e geçiş anı "GNSS bağımlılığının azaldığı" an.

# 7 — Görev FSM (ana_kontrol)

**Dosya:** `guidance/ana_kontrol.py` (FAZ 3 durum makinesi)

- **Ne yapar:** Görevi durum makinesiyle yürütür:
  **ARAMA → TAKİP → GORSEL_GUDUM → KILIT_BILDIR → ANGAJMAN.** ARAMA/TAKİP'te
  midcourse (füzyonlu GNSS ile bölgeye yaklaşma); CONFIRMED track + kilit koşulu
  oluşunca görsele devreder ve **hedef konumu artık YALNIZCA görsel** (bbox/PnP).
- **Neden bu tasarım:** Şartname görev akışı + otonomi: manuel hedef seçimi YOK,
  tespit+tracking otonom devreye girer. GPS güdümü öldürücü faz değil — araca
  yönelip **kesintisiz görsel temas** kurup görsel faza temiz devretmektir.
- **Elenen alternatif:** tek-mod GPS güdüm (görsele devir yok → GNSS bozulunca
  kör); ham sayaç (FSM artık kilit'i `kilit_kurali`'na sorar, ByteTrack
  CONFIRMED'a devreder). Kayıpta erken vazgeçmek → `VIS_LOST_TO_GPS_S` ile GPS'e
  dönüş güvenlik ağı.
- **Kritik parametreler (`Cfg`):** `HANDOFF_RANGE=4000` cm (tespit menzili),
  `VIS_N_LOCK=5` (ardışık geçerli-tespit → GORSEL_GUDUM), `VIS_STALE_S=0.5`,
  `VIS_LOST_TO_GPS_S=1.0` (kayıp bu süreyi aşarsa GPS'e geri dön). Angajman:
  `kilit_tamam` + kesintisiz ≥3 sn (kart 6).
- **Video ipucu:** Kilit panelinde **FSM durumu**; GORSEL_GUDUM'a geçiş anı
  "GNSS bağımlılığının azaldığı" an — son 3 dk görev kanıtının çekirdeği.

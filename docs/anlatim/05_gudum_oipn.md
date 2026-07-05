# 5 — Güdüm + OIPN (APN + Yönelim-Bilgili PN)

**Dosyalar:** `guidance/gudum_yasasi.py` (saf yasa), `guidance/ana_kontrol.py`
(harmanlama + terminal)

- **Ne yapar:** GÖRSEL TAKİP fazında orta-safha kilit-tutma ivmesini üretir:
  `a_cmd = N·Vc·λ̇ + (N/2)·a_T + β·a_ff`. **APN** orantılı seyrüsefer +
  hedef-ivme telafisi; **OIPN** ileri-besleme `a_ff = g·tan(φ_T)` (hedef roll'undan
  erken manevra sinyali). Terminal vuruşa (çarpışma-rotası) dokunmaz.
- **§6.1.2 "yönelim üretimi" kanıtı:** bu yasa GÖRSEL TAKİP'in yönelim çıktısıdır;
  kanıt = 🎮 GÜDÜM KOMUTU paneli (throttle/pitch/roll/yaw) + CSV `a_PN /
  a_APN_terim / a_OIPN_terim` sütunları (üç takip şartından ilki — bkz. kart 7).
- **Neden bu tasarım:** Saf takip hedefin kuyruğunu kovalar; APN λ̇'yı sıfırlayarak
  kesişime gider, OIPN roll'u görünce **dönüşten önce** öne nişan alır. `gudum_yasasi`
  saf/sim-bağımsız → sentetik girdiyle unit-test.
- **Elenen alternatif:** saf pursuit (lead yok); hazır güdüm kütüphanesi (kural 6 —
  doğrudan kullanılmaz). OIPN'i agresif katmak → EKF `a_T` ile **çift-sayım**;
  bu yüzden β konservatif ve dead-zone'lu.
- **Kritik parametreler (`GudumCfg`):** `N=4.0`; `BETA=0.3` (OIPN katsayısı, **canlı
  slider**); `OIPN_DEADZONE_DEG=5.0` (|φ_T|<5° → OIPN 0, gürültü roll'u sızmasın);
  `A_MAX≈g·tan40°`. **PnP geçersiz veya arayüz anahtarı kapalı → OIPN terimi 0**
  (regresyon: OIPN kapalı + poz'suz = eski IBVS hattı birebir).
- **Video ipucu:** Sağ panelde a_PN / a_OIPN bileşenleri + β; OIPN anahtarını
  açık/kapalı göstererek katkının izlenebilirliğini anlat.

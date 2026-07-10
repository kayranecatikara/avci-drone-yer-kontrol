# YAPILACAKLAR — Video/Teslim öncesi açık işler

> Repo mevcut haliyle teslim `.zip`'ini üretebilir mi kontrolü + eksikler. Öncelik sırasıyla.

## 1) Teslim paketleme temizliği (kod tarafı — orta öncelik)
- **`python arac/paket_kontrol.py` şu an çıkış kodu 1 veriyor** — ama bu **yeni bir kırık DEĞİL**;
  bu branch HEAD'inde de aynıydı (DEV-ONLY çitleri bu branch'te bakımsız kalmış). Sebep: `ana_kontrol.py`
  ve `web/*` içindeki `truth/gercek/corruption/debug` anahtar kelimeleri DEV-ONLY çitiyle sarılı değil.
  - Aksiyon: teslim öncesi ya (a) truth/debug-ölçüm bloklarını `>>> DEV-ONLY >>>` … `<<< DEV-ONLY <<<`
    çitleriyle sar (paket_kontrol sökerek paketler), ya da (b) `_debug_olc` / `get_debug_truth`
    ölçüm yollarını teslim kopyasından elle çıkar. **Sim kanıt videosu paketleme kısıtından MUAF**
    olsa da temiz paket iyi izlenim bırakır.
  - `ZORUNLU_ICERIK` yeni dosyalara güncellendi (`fusion/gnss_filtre.py`, `guidance/gps_takip.py`).
- **`web/dev_truth.py` artık ÖLÜ** (server import etmiyor; yeni "Gerçek GPS" test modu
  `ana_kontrol._GercekGPSTakip` alt sınıfıyla çalışıyor). İçinde `beyin.filtre.durum_guduum()` ve
  `beyin.set_hedef_kaynagi()` gibi **artık var olmayan API** çağrıları duruyor (çalışmaz ama
  import edilmediği için sistem etkilenmez). Aksiyon: dosyayı sil veya "kullanım dışı" olarak işaretle.

## 2) Başıboş model kopyaları (teslim öncesi — kolay)
Repo kökünde/`models/` altında zip'e **girmemesi gereken** kopyalar var:
`best (1).pt`, `best 6.pt`, `best7.pt`, `best_son.pt`, `eniyi_bbox.pt`, `eniyi_pose.pt`,
`models/best_yolo26s960_20260710.pt` (best.pt ile aynı), `models/talon_pose_eski_20260709.pt`.
- Aksiyon: bunları sil veya repo dışına taşı. Teslim zip'i yalnız **`models/best.pt`** (+ isteğe
  bağlı `talon_pose.pt`, ama pose kapalı) içermeli. `paket_kontrol.py` `.pt`'leri glob'la aldığından
  başıboş kopyalar zip'i şişirir.

## 3) Terminal faz + otonom vuruş (kod — video kaydına kadar) `[VURUŞ-BAĞIMLI]`
Karar (kullanıcı, 10 Tem — **Paket A**): tetik `kilit_ok` latch'i + son ~1 sn `IBVS r < 0.20`
(hedef nişanda kararlı) + o sürede **gerçek tespit** (köprü/tahmin değil). Üçü birden →
terminal band: `IBVS_DIKEY_NISAN→1`, boyut regülasyonu (`IBVS_K_BOYUT=0`) + TTC freni kapalı,
`IBVS_ILERI` tam. Kayıpta abort → kilit-tut'a dönüş. Ayrı "vur" komutu yok, temas fiziksel.
- **Durum:** kodda henüz YOK (görsel yasa şu an kilit-tut modunda; `ibvs_gorsel.hesapla` içinde
  terminal-band dalı eklenecek + `ana_kontrol`'de `kilit_ok`+nişan-kararlılık+gerçek-tespit kapısı).
- Yetişmezse: `KONUSMA_METNI` §Terminal faz ve `SIMULASYON_CEKIM_PLANI` 8-10 için
  `TESLIM_KONTROL_LISTESI`'ndeki "Terminal faz yetişmezse" reçetesi uygulanır.

## 4) Üretilecek video görselleri (kayıt öncesi — STORYBOARD'da detay)
- **Açılış kartı** (takım + yarışma adı).
- **Uçtan uca mimari diyagramı** (STORYBOARD'da mermaid taslağı hazır → temiz görsele dönüştür).
- **Ham vs filtre grafiği** (`arac/gps_gorsellestir.py` veya `veri/kiyas_log.csv`'den matplotlib).
- **Örnek tespit kolajı** (dedektör gözü penceresi `set AVCI_DEBUG_PENCERE=1` veya offline predict).

## 5) Canlı doğrulama (yeni GPS yığını — kod kaydından ÖNCE) ⚠️
Yeni `gnss_filtre` + `gps_takip` **gerçek simülasyon uçuşunda henüz görülmedi** (sim'siz sahte-drone
testi + birim testler geçti). İlk uçuşta doğrula:
- Kalkış AGL (`TAKEOFF_ALT_AGL=10 m`) ve tırmanma davranışı doğru mu?
- GPS yaklaşma işaretleri (pitch/roll/yaw/throttle yönü) hedefe **yaklaştırıyor** mu? Ters ise
  `GPSCfg.PITCH_SIGN/ROLL_SIGN/YAW_SIGN/Z_SIGN` çevrilir (kodda hazır knob'lar).
- Kesintide ölü-hesap (`DR_MAX_S=30 s`) makul mü? Handoff mesafesi (`HANDOFF_RANGE=40 m`) uygun mu?
- Görsel faza geçiş + kayıpta GPS dönüşü akıcı mı (rate-limit sürekliliği)?

## 6) Küçük tutarsızlıklar (düşük öncelik — teslim engeli değil)
- `web/index.html` tune panelinde `IBVS_LEAD_S` slider'ı var ama `Cfg`'de/`TUNE_ALLOW`'da bu ad
  YOK (pre-existing) → slider'ı çalışmaz; kaldır veya `Cfg`'ye gerçek karşılığını ekle.
- `tests/test_prop_maske.py` 2/4 geçiyor (YOLO modeli gerektiren detection testi; **pre-existing**,
  GPS değişimiyle ilgisiz). Gerçek model + kare ile lokal koşulmalı.
- `docs/anlatim/*`, `MEVCUT_DURUM.md`, `docs/video_prova_kontrol.md`: yarisma-pipeline dönemi
  adları (ByteTrack, OIPN, İnovasyonlu J) bayat; akış iskeleti değerli. İstenirse güncellenir.

---
**Özet:** Video 5 dosyası hazır (`MIMARI_ENVANTER`, `KONUSMA_METNI`, `STORYBOARD`,
`SIMULASYON_CEKIM_PLANI`, `TESLIM_KONTROL_LISTESI`). Teslim engeli olan tek büyük iş **terminal
faz/vuruş** (3) ve onun `[VURUŞ-BAĞIMLI]` revizyon reçetesi hazır. Paketleme (1) + model temizliği
(2) + üretilecek görseller (4) kayıt gününe kadar tamamlanır. Canlı GPS doğrulaması (5) ilk uçuşta.

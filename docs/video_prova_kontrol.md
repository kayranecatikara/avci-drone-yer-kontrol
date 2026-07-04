# Sim Uçuş Kanıt Videosu — Görünürlük Kontrol Listesi

> **Amaç:** Sim Teslim Esasları dokümanının "videoda görülmesi beklenen teknik
> çıktılar" 10 kalemini FSM provası sırasında TEK KADRAJDA okunabilir tutmak.
> Her kalem arayüzde nerede görünür + "tek kadrajda okunuyor mu" (✓/✗) işaretle.

| # | Kalem (şartname) | Arayüzde nerede | Prova ✓ |
|---|---|---|---|
| 1 | Simülasyon ekranı | Orta panel FPV (mss/PrintWindow oyun karesi) | ☐ |
| 2 | Drone + hedef saha konumu | Sağ panel: 🛸 AVCI (x/y/z) + 🎯 HEDEF (x/y/z) | ☐ |
| 3 | Bozuk GNSS kullanımı çıktısı/arayüz | 🎯 HEDEF (ham GPS) + HAM GPS–AVCI mesafe + FPV **HEDEF GNSS** rozeti | ☐ |
| 4 | Tespit anı | FPV bbox belirir + 🎯 TAKİP/PnP kartı doldu | ☐ |
| 5 | bbox + merkez + hedef ID + takip durumu | FPV: yeşil bbox + merkez nokta + `#id DURUM`; sağ TAKİP kartı | ☐ |
| 6 | Tracker aktif/pasif | TAKİP kartı `track durumu` (TENTATIVE/CONFIRMED/LOST); MODEL paneli | ☐ |
| 7 | Hedef kaybı / yeniden-tespit / süreklilik | Üstte uçucu banner: **HEDEF KAYBEDİLDİ (coast)** / **YENİDEN TESPİT**; `tespit_mi` coast göstergesi | ☐ |
| 8 | Güdüm komut telemetrisi | Sağ panel **🎮 GÜDÜM KOMUTU** (throttle/pitch/roll/yaw) | ☐ |
| 9 | Angajman kararı + vuruş anı | FSM durumu **ANGAJMAN** (kilit paneli) + mesafe vuruş menziline iner | ☐ |
| 10 | Görev sonu başarı çıktısı | Tam ekran **🎯 GÖREV BAŞARILI** overlay (min mesafe + "insan müdahalesi yok") | ☐ |

## Ek video kanıt panelleri (şartname videosu vurguları)
- **GNSS bağımlılığının azalması:** GORSEL_GUDUM'a geçince HEDEF GNSS rozeti YEŞİL
  "KULLANILMIYOR ✓" olur (kalem 3'ün güçlü hali) — kilit panelinde FSM durumu da izlenir.
- **Kilit süreci (§6.1.4):** 🔒 KİLİT SAYACI paneli (kümülatif/5 + pencere doluluk çubuğu +
  eksen kaplama + AV çerçevesi FPV overlay'de). Kilit tamamlanamazsa `engel` alanı hangi
  koşulda takıldığını gösterir (video anlatımında "model şu an göremiyor" kanıtı).
- **Otonomi:** manuel hedef seçimi YOK; tespit+tracking otonom (MODEL paneli + tespit anı).

## Prova protokolü (FSM provası koşusunda)
1. `python main.py` → tarayıcı → **Görev Başlat**.
2. Yukarıdaki 10 kalemi sırayla işaretle; her biri **aynı ekran görüntüsünde** okunuyor mu?
3. Zayıf model kilidi tamamlayamazsa: kalem 4-6 (tespit/bbox/tracker) yine görünür,
   kalem 9-10 (angajman/başarı) İYİ MODEL geldiğinde tamamlanır (runbook MEVCUT_DURUM'da).
4. Eksik/okunmaz kalem varsa arayüz düzenlemesi (panel konumu/boyutu) not al.

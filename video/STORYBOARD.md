# STORYBOARD — A Bölümü (Algoritma + Kaynak Kod Anlatımı)

> Konuşma metnindeki (`KONUSMA_METNI.md`) her blokla ekran içeriği **birebir eşleşir**:
> anlatıcı GNSS filtresini anlatırken ekranda o modülün kodu / o grafiğin durması esastır.
> A bölümünde **hızlandırma YOK**. Kod ekranları okunur çözünürlükte (koyu tema, büyük font,
> ilgili fonksiyona zoom). Süre 3 dk'ya inecekse `[OPSİYONEL]` işaretli satırlar atlanır.

| Zaman | Konuşma özeti | Ekranda ne var | Hazırlık notu |
|---|---|---|---|
| 00:00–00:18 | Açılış + genel mimari | **Açılış kartı** (Takım: Hamidiye + yarışma adı, 5-8 sn) → **uçtan uca mimari diyagramı** | Kart hazır grafik (üretilecek). Diyagram: `MIMARI_ENVANTER §1` ASCII'sinden temiz bir görsel çizilecek (mermaid/figma). **ÜRETİLECEK GÖRSEL.** |
| 00:18–00:45 | İki paralel thread (50 Hz kontrol + GPU dedektör) | Aynı diyagram; **kontrol_dongusu** ve **dedektor_dongusu** kutuları sırayla vurgulanır | Diyagramda iki thread ayrı renkte. `web/server.py` `kontrol_dongusu`/`dedektor_dongusu` fonksiyon başlıkları yan pencerede gösterilebilir. |
| 00:45–01:20 | Bozuk GNSS + filtreleme | Sol: `fusion/gnss_filtre.py` `x/y/z_spike_temizle` + `guncelle` fonksiyonları (zoom). Sağ: **ham vs filtre grafiği** (bozuk zıplayan çizgi ↔ temiz çizgi) | Grafik: `veri/kiyas_log.csv` veya `veri/gps_log_canli.json`'dan üretilir → `arac/gps_gorsellestir.py` çıktısı kullanılabilir. **ÜRETİLECEK GÖRSEL** (aşağıda betik notu). |
| 01:20–01:45 | GPS güdümü + ölü-hesap | `guidance/gps_takip.py` `adim()` — kalkış, PD/PID, **dead-reckoning bloğu** (`dr_dt`, `DR_MAX_S`) vurgulu | Kodda `# -- Veri Kesintisi --` ve `# -- Dead-reckoning süresi --` yorumlarına zoom. Okunurluk için satır no açık. |
| 01:45–02:20 | Görüntü işleme + tespit | `detection/gorsel_tespit.py` (`tespit_hepsi`/`_sahi_ham`) + **örnek tespit kareleri** (bbox + conf etiketi) | Tespit kareleri: `set AVCI_DEBUG_PENCERE=1` ile "dedektör gözü" penceresinden ekran görüntüsü, veya offline `model.predict` kolajı. **ÜRETİLECEK GÖRSEL.** `[OPSİYONEL]` cümle = 5-kare doğrulama; atlanırsa kare kolajı kısa tutulur. |
| 02:20–02:50 | Takip (HybridSort) | `detection/takip.py` `TRACKER_PARAMS` + FPV kısa klip: **ID:n etiketi + takip durumu** hedefin üstünde | FPV klibi B bölümü kaydından 3-5 sn kesit (tekrar değil, destek). Açık kaynak beyanı ekranda "boxmot HybridSort" yazısıyla pekiştirilir. |
| 02:50–03:30 | Füzyon + güdüm + karar (FSM + IBVS) | `guidance/ana_kontrol.py` FSM (durum geçişleri) → `guidance/ibvs_gorsel.py` `hesapla`; FPV'de **"GPS GÜDÜMÜ: KAPALI"** kırmızı rozeti | FSM için `MIMARI_ENVANTER §2` tablosu görsele dönüştürülebilir. Rozet: B kaydından görsel faz anı. |
| 03:30–03:55 | Terminal faz + angajman `[VURUŞ-BAĞIMLI]` | Kilit sayacı paneli (**10 sn şerit / 5 sn**) → **ANGAJMAN çipi** → **VURUŞ!** banner | Kilit şeridi + çipler `web/index.html` KİLİTLENME kartından. Vuruş anı B kaydından. Terminal faz yetişmezse bu kare revize (bkz. checklist). |
| 03:55–04:15 | Kaynak kod turu + kütüphaneler | **Dosya ağacı** (modül adları okunur) + `requirements.txt` | Ağaç: VS Code explorer ekran görüntüsü veya düzenli liste. requirements.txt satırları okunur zoom. |

## Ekran havuzu — repodaki GERÇEK varlıklar (doğrudan kullanılabilir)
- **Kod dosyaları** (koyu tema, büyük font): `gnss_filtre.py`, `gps_takip.py`, `gorsel_tespit.py`,
  `takip.py`, `ana_kontrol.py`, `ibvs_gorsel.py`, `drone_sdk.py`, `requirements.txt`.
- **Canlı arayüz** (`web/index.html`): FPV + bbox overlay, BOZUK GNSS kartı, TAKİP kartı,
  KİLİTLENME kartı (10 sn şerit), IBVS GÜDÜM kartı, GÜDÜM KOMUTU kartı, mini-harita, olay günlüğü.
- **Dedektör gözü penceresi**: `set AVCI_DEBUG_PENCERE=1` → kare↔tespit senkron gösterim.

## Üretilecek görseller (repoda hazır DEĞİL — kayıt öncesi yapılacak)
1. **Açılış kartı** — takım + yarışma adı (basit grafik).
2. **Uçtan uca mimari diyagramı** — `MIMARI_ENVANTER §1` temel alınır. Mermaid taslağı:
   ```mermaid
   flowchart LR
     OYUN[Oyun / Drones of War] -->|bozuk GNSS + kendi telemetri| SDK[drone_sdk.py]
     OYUN -->|pencere görüntüsü| DET[dedektör: gorsel_tespit + takip]
     SDK --> KON[kontrol_dongusu 50Hz]
     KON --> GPS[gps_takip: gnss_filtre + PD/PID]
     KON --> FSM[ana_kontrol FSM]
     FSM -->|GPS fazı| GPS
     FSM -->|görsel faz| IBVS[ibvs_gorsel]
     DET --> FSM
     GPS --> OUT[set_control_surfaces → OYUN]
     IBVS --> OUT
   ```
3. **Ham vs filtre grafiği** — üretim betiği (repo araçlarından):
   `python arac/gps_gorsellestir.py` (bozuk + filtre-temiz konumu çizer) **veya** kısa bir
   matplotlib betiği `veri/kiyas_log.csv`'yi (paket, ham_m, filtre_m) okuyup iki eğri çizer.
4. **Örnek tespit kolajı** — 3-4 kare, bbox + conf; dedektör gözü penceresinden veya offline predict.

## Kural: senkron
Her blokta **ekran = anlatılan modül**. Anlatıcı GPS filtresini anlatırken ekranda görsel güdüm
kodu durmamalı. Blok geçişleri konuşmadaki zaman koduna hizalanır (yukarıdaki tablo).

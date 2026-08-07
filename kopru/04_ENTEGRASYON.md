# 04 — YER KONTROL İSTASYONUNA ENTEGRASYON

> Dönüştürücünün `avci-drone-yer-kontrol-kayran` arayüzüne bağlanması,
> 2026-08-07'de silinen eski yasa, ve GPS kaynağı seçicisi.

---

## 1. ÖNCE / SONRA

**Önce** — arayüz kendi GPS yasasını sürüyordu:
```
web/server.py (50 Hz) → AvciKontrol.adim()
                          ├─ KALKIS   → dünya-Z kapısı (SEARCH_ALT)
                          ├─ GPS faz  → ESKİ YASA (standoff + PD + kaskad)  ~190 satır
                          └─ GÖRSEL   → IBVS
```

**Sonra** — GPS fazı dönüştürücüye devredildi:
```
web/server.py (50 Hz) → AvciKontrol.adim()
                          ├─ GÖRSEL faz → IBVS (DEĞİŞMEDİ)
                          └─ GPS faz    → _kopru_tik()
                                            └─► KopruGudum.adim()
                                                  ├─ KALKIS (AGL kapılı)
                                                  └─► DowKopru.adim()
                                                        ▲
                                    gps_guidance thread (20 Hz)
                                    send_velocity → set_hiz_ned
```

---

## 2. BAĞLANTI NOKTALARI

### `kopru/entegre.py` — `KopruGudum`

Yasa + köprüyü tek nesnede paketler. Yaptıkları:

| Metot | Görevi |
|---|---|
| `_kur()` | env'i (`AVCI_GPS_RANGE`, `AVCI_GPS_IC`) **import'tan önce** set eder, yasayı import eder, `gg.send_velocity`'yi köprüye bağlar, `V_MAX`'ı setattr'lar, zemini alır |
| `baslat()` | köprüyü kurar (yasa thread'i **kalkış bitince** başlar) |
| `_kalkis_tik()` | bloklamayan AGL-kapılı tırmanış (server'ın 50 Hz döngüsünden) |
| `adim()` | kalkış bitmediyse tırmanış tiki, bittiyse `DowKopru.adim()` |
| `durum()` | `gg.status`'tan `{durum, d_h, menzil}` — arayüz telemetrisi |
| `komut` | köprünün uyguladığı son stick'ler — "uygulanan komut" kartı |
| `durdur()` | yasa thread'ini kapatır (yeni görevde taze başlasın) |

**Neden env import'tan önce?** `gps_guidance.Cfg` env'i **sınıf tanımında**
okur (`_env_f(...)`). Import edildikten sonra set etmek işe yaramaz.

### `guidance/ana_kontrol.py` — `_kopru_tik()`

GPS fazında çağrılır. Yaptıkları:
1. İlk tikte `KopruGudum`'u lazy kurar (kurulamazsa **gürültülü hata + hover** —
   sessizce başka yasaya düşmez, çünkü artık başka yasa yok)
2. `kopru_gudum.adim()` ile bir tik ilerletir
3. Arayüz için: `self.durum` ve `self.handoff`'u yasanın durumundan,
   `self.prev`'i köprünün uyguladığı stick'lerden günceller
4. Uçuş logu satırı yazar (`phase="KOPRU"`)

### `set_kaynak()` — yaşam döngüsü kancası

Server her "Görev Başlat"ta çağırır. Köprüyü **yıkar** (`durdur()` + `None`) →
sonraki GPS tikinde taze kurulur: yeni `gps_guidance` CSV'si, temiz filtre ve
istasyon durumu, yeni zemin referansı.

---

## 3. GPS KAYNAĞI SEÇİCİSİ ⚠️ ÖNEMLİ

Arayüzdeki mevcut kaynak butonları köprünün hedef kaynağını belirler:

| Arayüzde | Köprü ne yapar | Ölçülen menzil |
|---|---|---|
| **v2 (İnovasyonlu J)** | bozuk kanal + CT-EKF | **39.0 m** |
| **🎯 Gerçek GPS (test)** | truth kanalı, bozuk kanal hiç okunmaz, CT-EKF baypas | **7.1 m** |

Bu **5.5 kat fark** ölçülmüştür (aynı yasa, aynı ayarlar, aynı döngü hızı —
tek fark GPS kaynağı). Faz 3'te kilit isterisini sağlayan koşular (U, V3)
**gerçek GPS** ile uçmuştu.

```python
hedef_truth=(self.kaynak == "gercek")        # ana_kontrol._kopru_tik
```
`set_kaynak` köprüyü yıktığı için **canlı geçiş** çalışır — görevi yeniden
başlatmaya gerek yok. Konsol hangisinin aktif olduğunu yazar:

```
[KOPRU-GUDUM] hazir: HEDEF=GERCEK GPS (truth)  ... CT-EKF=BAYPAS
[KOPRU-GUDUM] -> Faz 3 teshis konfigurasyonu (U/V3): beklenen oturmus menzil ~7-8 m
```

> **Yarışma koşulu bozuk GPS'tir.** Gerçek GPS bir **teşhis** kanalıdır
> (`get_debug_truth`, index 18-26) ve yarışmada bulunmaz.

---

## 4. AYARLAR — `guidance/ana_kontrol.py:Cfg`

```python
KOPRU_RANGE_SET     = 6.9    # istasyon slant menzili (kutu %6.48; eşik %5)
KOPRU_ISTASYON_ELEV = 25.0   # istasyon LOS yükselişi → 2.92 m ALT + 6.25 m ARKA
KOPRU_V_MAX         = 22.0   # yasa istisnası (ölçümle)
KOPRU_IC_KAYMA      = 0.0    # iç-daire kayması KAPALI
KOPRU_GNSS_FILTRE   = True   # bozuk hedefi CT-EKF'ten geçir
KOPRU_KALKIS_AGL    = 40.0   # görev başı tırmanış (AGL)
```

Gerekçeleri: [03_OLCUMLER.md](03_OLCUMLER.md)

---

## 5. SİLİNENLER (2026-08-07, kullanıcı kararı)

Eski GPS yasası **bayrak arkasında saklanmadı, gerçekten silindi**.
`guidance/ana_kontrol.py`: **1490 → 1047 satır (−443)**

| Silinen | Ne kadar |
|---|---|
| Eski GPS kontrol yasası (`adim()` içinde): standoff nişan, PD + EMA-türev, `speed_cap`/frenleme profili, alçalma önceliği, dikey kaskad, yaw denetleyicisi, None/loiter yönetimi | ~190 satır |
| Ölü Cfg sabitleri: `KP_H, KD_H, VZ_MAX, KV_Z, KI_Z_VEL, INT_Z_*, APPROACH_*, LOOKUP_*, V_CAP_*, BRAKE_DIST, HANDOFF_RANGE/EXIT, SEARCH_ALT, TAKEOFF*, HOLD_TICKS, POS_DEADBAND, KP_YAW, DERIV_EMA` | ~70 satır |
| Ölü yardımcılar: `speed_cap`, `world_to_body`, `deadband`, `_derivative`, `_own_dikey_hiz`, `_loiter` + durum alanları | ~180 satır |
| `GUDUM_KOPRU` bayrağı (tek yol kalınca anlamsız) | — |
| Tune panelinden ölü slider: `KV_Z`, `VZ_MAX` (`web/server.py` + `index.html`) | 2 slider |

**Geri dönüş:** silinen kod GitHub'da `eca3b4a` commit'inde duruyor.

### Ne KALDI ve neden

| Kalan | Neden |
|---|---|
| **Görsel faz (IBVS) + kilit sayacı** | Kullanıcı kararı. Ayrıca taşınan yasanın kendi tanımı "vuruş değil, görsel faza devretmek" |
| **J filtresi + telemetri alanları** (`_hedef_temizle`, `son_temiz/son_ham/son_xy_anlik/son_z_anlik`) | Arayüzün GNSS karşılaştırma kartı ve görev izleyicisi bunları okuyor (`server.py`'de 22 kullanım) |
| **Komut tavanları + `_send`** | Görsel faz ve köprü kullanıyor |
| `web/server.py`, `index.html` | Yalnız ölü slider'lar çıktı |

---

## 6. DOĞRULAMA

```
164 birim testi geçiyor  (38'i köprüye ait)
web.server + main import OK
gps_guidance.py hash'i Gazebo orijinaliyle BİREBİR
```

Beklenen konsol çıktısı (görev başlatınca):
```
[KOPRU-GUDUM] hazir: HEDEF=BOZUK GPS  RANGE_SET=6.9 ELEV=25 V_MAX=22 IC_KAYMA=0 zemin=48.4 m CT-EKF=ACIK
[KOPRU-GUDUM] istasyon: 6.25 m ARKA + 2.92 m ALT (hedefin altinda)
[KOPRU-GUDUM] -> yarisma konfigurasyonu: kestirim hatasi ~10 m, beklenen oturmus menzil ~39-44 m
[KOPRU-GUDUM] kalkis: AGL 0.0 -> 40 m (zemin 48.4)
[KOPRU-GUDUM] kalkis TAMAM (AGL 39.x m) -> yasa devrede
============================================================
[GPS] Kadraj güdümü (yeniden inşa) — hedefi kamera merkezine getir
[GPS] setpoint: slant 6.9m → 6.7m arka + 1.8m alt; ...
============================================================
[GPS] ARAMA d_h=... menzil=... kadraj(yaw=...,elev=.../istasyon 15°) v=(...) tgt_v=...
```

Bu satırlar çıkıyorsa dönüştürücü hattı uçuyor demektir.

---

## 7. BİLİNEN AÇIKLAR

1. **Zemin referansı** görev başında aracın irtifasından alınır (**yerde**
   varsayımı). Havadayken "Görev Başlat"a basılırsa referans yanlış olur; tek
   sonucu yasanın yere-çakılma tabanının kayması (istasyon geometrisi hedefe
   göreli olduğundan sabit ofset iptal olur).
2. **İki J filtresi** çalışıyor: biri arayüzün GNSS kartı için (`ana_kontrol`),
   biri köprünün kontrol yolunda (`dow_kopru`). Zararsız ama tekilleştirilebilir.
3. **Uçuş logu** (`veri/ucus_log_*.csv`) köprü fazında yalnız meta+komut yazıyor;
   ayrıntılı güdüm verisi yasanın kendi CSV'sinde
   (`kopru/gazebo_kaynak/logs/gps_guidance_*.csv`).

← Geri: [README.md](README.md) · [03_OLCUMLER.md](03_OLCUMLER.md)

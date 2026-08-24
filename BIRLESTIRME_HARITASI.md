# Birleştirme haritası — `dow-sistem-guncel` ⟷ `main`

Bu branch DoW entegrasyonunun çalışan tam hâlidir. `main`'den belirgin şekilde
ayrışmıştır ama **ikisi rakip değil, tamamlayıcıdır**: ayrıştıkları noktaların
çoğunda farklı problemleri çözmüşler.

Ortak ata: `8a0666a`. O noktadan sonra `main` **1**, bu branch **8** commit almış.

---

## 1. `main`'de var, bizde yok — ALINMASI GEREKENLER

| Dosya | Ne | Öncelik |
|---|---|---|
| **`fusion/gnss_filtre.py`** | Yeni GNSS filtresi (234 satır) | ⭐ **YÜKSEK** |
| `guidance/ibvs_gorsel.py` | `main`'in görsel güdümü (297 satır) | kıyas için |
| `3_TESHIS_Kare_Kayit.bat` | Teşhis kare kaydedici | düşük |
| `tests/test_ibvs_gorsel.py`, `tests/test_kilit_takip.py` | testler | orta |

### ⭐ `fusion/gnss_filtre.py` neden acil

Bu branch hâlâ **eski** `fusion/inovasyonlu_j_v2.py`'yi taşıyor; `main` onu
`gnss_filtre.py` ile değiştirmiş. Ve **bizim yeni güdüm paketimiz zaten onu
bekliyor** — `dow/ayarlar.py:30-33`:

```python
#   Bu iş bitince GPS_KAYNAK="filtre" yapılıp gnss_filtre.py yeniden
#   devreye alınacak.
GPS_KAYNAK = os.environ.get("DOW_GPS_KAYNAK", "truth")   # "truth" | "filtre"
```

Yani yeni GPS güdümü şu an **truth** (geliştirme kipi) ile çalışıyor.
⛔ **Yarışmada truth kanalı gelmez.** `gnss_filtre.py` alınmadan yarışmada
GPS fazının besleme kaynağı yok.

`main`'de `gnss_filtre` şu dosyalardan çağrılıyor: `guidance/ana_kontrol.py`,
`web/server.py`, `arac/filtre_dogrulama.py`, `arac/gps_gorsellestir.py`.

---

## 2. Bizde var, `main`'de yok — 248 dosya

Kabaca:

* **`dow/`** — yeni güdüm paketi (gps + ibvs + kamera + ayarlar + amir +
  çevirici + doğrulama). Sistemin kalbi.
* **`kopru/`** — Gazebo güdümünü DoW'a taşıyan köprü + `gazebo_kaynak/`
  (supervisor, bbox_ibvs, bbox_geometri, gps_guidance, kesintisiz_kilit …)
* **`arac/`** (105 dosya) — ölçüm/analiz/A-B tezgâhları
* **`sim/`**, **`veriseti/`**, **`tests/`** (30 yeni test)
* Ölçüm notları (`GECE_*.md`, `DURUM*.md`, `arac/ARASTIRMA_*.md`)

Bunlar `main`'de hiç yok; **çakışma üretmezler**, doğrudan taşınabilirler.

---

## 3. İkisinde de var ama farklı — 18 dosya (ASIL ÇAKIŞMA YÜZEYİ)

| Dosya | Bizde | `main`'de | Not |
|---|---|---|---|
| `web/server.py` | tespit/telemetri katmanı, v5 | +79 satır (filtre + tracker) | ⚠ ikisi de değişmiş |
| `guidance/ana_kontrol.py` | `VIS_MODEL_PATH` → talon_v5 | +28 satır (gnss_filtre) | ⚠ ikisi de değişmiş |
| `detection/takip.py` | eski tracker | 417 satır değişmiş (sadeleştirme) | ⚠ büyük fark |
| `models/best.pt` | 5,2 MB | 19,2 MB | ⚠ ikili çakışma — **elle seç** |
| `config.py` | `VIS_MODEL_ADI` = v5 | v3 | bizimki güncel |
| `web/index.html` | — | +6 satır | küçük |
| `detection/gorsel_tespit.py`, `poz_tespit.py`, `pencere_yakala.py` | | | orta |
| `CLAUDE.md`, `.gitignore`, `*.sh`, `arac/*`, `tests/*` | | | küçük |

---

## 4. Önerilen sıra

1. **Önce sadece `fusion/gnss_filtre.py`'yi al** (çakışmasız, tek dosya):
   ```bash
   git checkout origin/main -- fusion/gnss_filtre.py
   git rm fusion/inovasyonlu_j_v2.py        # main onu kaldırmış
   ```
   Sonra `guidance/ana_kontrol.py` ve `web/server.py` içindeki import'ları
   `main`'deki hâline bakarak elle güncelle.

2. **`detection/takip.py`'yi kıyasla.** `main`'in sürümü ~340 satır daha kısa;
   sadeleştirme mi yoksa özellik kaybı mı olduğuna bakılmadan alınmamalı.
   `tests/test_takip.py` de aynı commit'te 282 satır değişmiş.

3. **`models/best.pt`'ye dokunma.** İki taraf farklı model taşıyor. Bu branch
   zaten `talon_v5.pt` kullanıyor (`config.py`), `best.pt` eski yol.

4. **`web/server.py` ve `guidance/ana_kontrol.py`'yi elle birleştir** —
   otomatik merge bu ikisinde güvenli değil.

5. En son tam merge:
   ```bash
   git merge origin/main        # çakışmaları yukarıdaki tabloya göre çöz
   python dow/dogrulama.py      # 34 sınama — merge sonrası MUTLAKA koş
   python -m pytest tests -q
   ```

---

## 5. Merge sonrası kırılmaması gerekenler

* `python dow/dogrulama.py` → **34/34** geçmeli (işaret/yön sınamaları;
  bu depoda ayna hatası üç kez tekrarladı).
* Faz ölçütü tek kaynaktan gelmeli: `dow/ayarlar.py::DEVIR_KARE=10` /
  `KAYIP_KARE=20` → `supervisor.SupCfg.KILIT_N` / `KAYIP_M`.
* `AVCI_YASA=eski` geri dönüş yolu çalışır kalmalı.
* Süpervizördeki **hayalet kapısı** `max(w,h)/min(w,h)` olarak kalmalı —
  `_w/_h`'ye dönerse yatık hedefte gerçek tespitlerin %59'u tekrar atılır.

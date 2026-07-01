# arsiv/bizim_gorsel — Görsel güdüm (bizim paralel sürüm), BİRLEŞTİRME BEKLİYOR

Bu klasör, `kubra` branch'inde geliştirilen **görsel güdüm (DÜZ IBVS)** implementasyonunun
**referans kopyasıdır**. Repo kayra'nın rol-bazlı yapısına geçirilirken (guidance/detection/
web/...), çakışan dosyalar için "önce yapıyı kur, kodu sonra" kararı alındı: kayra'nın
çalışan sürümü yerinde bırakıldı, bizimki buraya park edildi. **Bu dosyalar ÇALIŞTIRILMAK
için değil, sonraki turda `guidance/`, `detection/`, `web/` altına BİRLEŞTİRİLMEK içindir.**
(İmportları hâlâ düz-yapıya göre: `from inovasyonlu_j_v2 import ...` — taşınırken düzeltilecek.)

## Buradaki dosyalar (bizim sürüm) → hedef (kayra yapısı)
| Buradaki (bizim) | Birleşme hedefi | Kayra'da mevcut |
|---|---|---|
| `ana_kontrol.py` | `guidance/ana_kontrol.py` | var (kendi FSM'i) |
| `ibvs_guidance.py` (`AvciGorselGuduum`) | `guidance/ibvs_guidance.py` | var (`IBVSGuidance`) |
| `gorsel_tespit.py` (`HedefDedektor`) | `detection/gorsel_tespit.py` | var (`GorselTespit`, tracking'li) |
| `server.py` | `web/server.py` | var |
| `index.html` | `web/index.html` | var |
| `requirements.txt` | kök `requirements.txt` | var |

Bizim modelimiz (`best.pt`, ~42 MB) `origin/kubra` branch'inde (kök dizin). Kayra'nınki
`models/best.pt` (~52 MB). Birleştirmede tek model seçilecek.

## Bize özgü — birleştirmede kayra'nınkine EKLENECEK katman
Kayra'nın sürümünde OLMAYAN, taşınması gereken özellikler:
1. **Manuel güdüm switch** `vis_mode ∈ {OTO, GPS, GORSEL}` (`set_vis_mode`, adim() switch,
   server `/api/command "vismode"`, index OTO/GPS/GÖRSEL butonları).
2. **Canlı VIS_* tune sliderları** (`TUNE_ALLOW`, `/api/tune`, index `TUNE_DEFS` görsel grup).
3. **Tarayıcı "gorsel" telemetri bloğu** (`build_telemetry` + `_normalize_tespit`) ve
   **istemci-taraflı canvas overlay** ("GPS GÜDÜMÜ: KAPALI/AÇIK" rozeti, ex/ey/conf).
4. **Kademeli kayıp politikası**: kör-devam (`ibvs.kor_devam`, EMA dead-reckon) → hover
   (`VIS_LOST_TO_GPS_S`) → GPS'e geri dönüş; **zorla-GÖRSEL modunda asla dönmeme**.

## Kayra'da olup bizde OLMAYAN — birleştirmede KORUNACAK (kayra tabanı)
- **YOLO tracking** (bytetrack + `tid`) — CLAUDE.md zorunlu tutuyor.
- **Occlusion-proof pencere yakalama** (`detection/pencere_yakala.py`, windows-capture).
- Ayrı `tespit_lock` + kare ts-dedup; `veri/` çıktı klasörü.

## Sonraki tur (birleştirme) planı — özet
Taban = kayra'nın olgun sürümü (tracking + pencere yakalama + IBVS çekirdeği). Üstüne
yukarıdaki 1–4 katmanı taşınır. `ibvs_guidance`/`gorsel_tespit`: kayra'nın sınıfı taban,
bizim `kor_devam()` (dead-reckon) eklenir. Birleşme bitince **bu klasör silinir.**

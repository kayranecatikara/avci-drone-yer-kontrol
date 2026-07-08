# Anlatım Kartları — modül → video anlatımı

> **Amaç:** Sim Uçuş Kanıt Videosu'nun **ilk 3 dk** (sesli teknik anlatım)
> için her modülün 5-6 satırlık kartı. Her kart aynı iskelet:
> **Ne yapar · Neden bu tasarım · Elenen alternatif · Kritik parametreler
> (+kaynağı) · Video ipucu.** Değerler koddaki `Cfg` bloklarından birebir;
> değiştirirsen kartı da güncelle.

| # | Kart | Modül(ler) | Şartname eşlemesi |
|---|---|---|---|
| 1 | [Input + Tespit](01_input_tespit.md) | `sdk/drone_sdk.py`, `detection/algi_hatti.py`, `detection/model_yonetici.py` | bozuk GNSS girdisi + hedef tespit |
| 2 | [Takip (ByteTrack + gyro-CMC)](02_takip.md) | `detection/takip.py` | tracking |
| 3 | [Füzyon / Filtre](03_fuzyon.md) | `fusion/inovasyonlu_j_v2.py` | sensör füzyonu / GNSS filtreleme |
| 4 | [PnP Poz Kestirimi](04_pnp.md) | `detection/talon_pose_estimator.py` | (gözlemci: hedef poz/menzil kanıtı) |
| 7 | [Görev FSM](07_fsm.md) | `guidance/ana_kontrol.py` | görev akışı / otonomi |

> **NOT (2026-07-08):** 05 (Güdüm+OIPN) ve 06 (Kilit Kuralı) kartları SİLİNDİ —
> bizim görsel güdüm yasamız **basit IBVS + pose roll açı-beslemesi**
> (`guidance/ibvs_gorsel.py`); kilit isteri sayacı `ana_kontrol._kilit_degerlendir`
> içinde SALT GÖZLEM. APN/OIPN + kilit_kurali modülleri repoda YOK (yarisma-pipeline
> hattından geliyordu, kullanılmadığı için kaldırıldı; git geçmişinde durur).

**Akış (video anlatım sırası):** bozuk GNSS girdi (1) → füzyon temizler + hız
kestirir (3) → GPS ile bölgeye yönelme → YOLO tespit (1) → tracking ID
sürekliliği (2) → görsel güdüm: basit IBVS + roll lead (`ibvs_gorsel.py`) +
PnP gözlemci kanıtı (4) → kilit sayacı §6.1.4 (`_kilit_degerlendir`) →
FSM ANGAJMAN (7). **GNSS bağımlılığının azaldığı** an: GORSEL_GUDUM fazına
geçince hareket komutu artık YALNIZCA görsel veriden (bbox+keypoint).

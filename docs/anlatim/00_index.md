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
| 4 | [PnP Poz Kestirimi](04_pnp.md) | `detection/talon_pose_estimator.py` | (OIPN için hedef poz/menzil) |
| 5 | [Güdüm + OIPN](05_gudum_oipn.md) | `guidance/gudum_yasasi.py`, `guidance/ana_kontrol.py` | güdüm / karar |
| 6 | [Kilit Kuralı (§6.1.4)](06_kilit_kurali.md) | `guidance/kilit_kurali.py` | kilitlenme kararı |
| 7 | [Görev FSM](07_fsm.md) | `guidance/ana_kontrol.py` | görev akışı / otonomi |

**Akış (video anlatım sırası):** bozuk GNSS girdi (1) → füzyon temizler + hız
kestirir (3) → GPS ile bölgeye yönelme → YOLO tespit (1) → tracking ID
sürekliliği (2) → görsel güdüm + PnP/OIPN (4,5) → kilit sayacı §6.1.4 (6) →
FSM ANGAJMAN (7). **GNSS bağımlılığının azaldığı** an: FSM GÖRSEL TAKİP'e
geçince hedef konumu artık YALNIZCA görsel (bbox/PnP).

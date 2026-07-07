# A/B Güdüm Kıyası ve KARAR — main (PNG) ↔ yarisma-pipeline (APN/IBVS)

*Bu belge geliştirme notudur; teslim paketine girmez. Amaç: "hangi görsel güdüm
hattı yaşayacak" kararını VERİYLE vermek (kullanıcı talebi 2026-07-07:
"hangisi düzgün çalışıyorsa onu bırakalım, diğerini silelim").*

Tarih: 2026-07-07 · Ölçüm düzeneği: `arac/ab_kiyas.py` (kos + rapor)

> **✅ KARAR (2026-07-07): Görsel güdüm hattında `main` (Kayra'nın PNG hattı) BAZ
> alınacak.** Bizim IBVS/OIPN görsel yasası ve GPS intercept+ram (strike) profili
> EMEKLİYE ayrılır (silme, merge oturumunda; git tarihinde kalır). Bizim branch'ten
> aşağıdaki "TAŞINACAKLAR" listesi kazanan hatta taşınır. Merge ayrı bir oturumda,
> bu doküman + Kayra onayıyla yapılır. **Ortak 1 numaralı borç: TESPİT MODELİ**
> (HUD yanlış-pozitifleri + uzak menzil güveni) — başarı oranını asıl taşıyacak iş.

---

## 1) Ölçüm protokolü (adalet önlemleri)

- Her koşu: taze oyun + ilgili branch'in GERÇEK `web/server.py`'si (değişiklik yok),
  görev HTTP'den başlatılır, ~5 Hz telemetri JSONL'e kaydedilir (240 sn üst sınır).
- **Algı girdisi İKİ TARAFTA BİREBİR AYNI:** Kayra'nın `best_son` modeli, imgsz=1280,
  çalışma eşiği 0.45 (bizde `models/best_kayra_son.yaml` + `config.VIS_MODEL_ADI`).
- **Mesafe/vuruş gerçek 3B** (sim debug truth; bizde DEV-çitli `dev_truth`, main'de
  doğrudan) → `en_yakin_m` iki tarafta aynı cetvelle.
- Koşu sayıları: pipeline-standoff 3, pipeline-strike 2 (1 koşu PLAY kaçtı), main 3.
  **n küçük** — ama yön tüm metriklerde tutarlı.

## 2) Sonuç tablosu

| metrik | pipeline (standoff) | pipeline (STRIKE) | **main (PNG)** |
|---|---|---|---|
| görev başarısı | 0/3 | 0/2 | **1/3** |
| vuruş | — | — | **213 sn'de, 1.79 m** |
| en yakın medyan | 25.4 m | 12.0 m | **4.4 m** |
| görsel faza geçiş | HİÇ (0 tespit) | HİÇ (0 tespit) | ~5. sn |
| takip kayıp/ID churn | — (takip hiç yok) | — | 72 kayıp / 30 ID (FP-gürültülü) |

Ham veri: `veri/ab/<etiket>/kosu_*.jsonl` + `server_*.log`; özet `veri/ab/rapor_uclu.json`.

## 3) Gün içi kritik teşhisler (kararın bağlamı)

1. **Eski `best.pt` HUD-OVERFIT çıktı:** HUD yazılarını ("ARMED/TRIGGER", batarya
   bloğu, sinyal göstergesi) 0.3–0.9 güvenle "talon" sanıyor. Canlı koşuda ekran-sabit
   FP'ye görsel devir yapıldı → GPS kesildi → drone hedeften 500 m açıldı; CMC
   ekran-sabit kutuyla uyuşmadığından 120 sn'de 32 track ID. Görsel kanıt:
   `veri/ab/tani2/kareler/*_KUTULU.jpg`. → Bizim görsel zincirin bugüne dek gerçek
   modelle hiç doğrulanamamış olmasının kök sebebi.
2. **`best_son` 640'ta kör** (conf med 0.13); 1280 şart (main'in server yorumu +
   bizim tarama). 1920'de 12/12 kare buluyor ama **HUD metnine de 0.5–0.62 kutu
   basabiliyor** → FP borcu her iki hatta ortak.
3. Bizim iki profil de görsel faza hiç giremedi: 10–33 m bandında model conf'ları
   0.45 eşiğinin altında + bizim GPS yasaları kamerayı tespit-menzilinde uzun süre
   hedefte tutamıyor. main'in yaklaşması ise hedefe 4 m'ye kadar sokulup görselin
   işini kolaylaştırıyor (1.8 m vuruş bu şekilde geldi).

## 4) Neden main? (gerekçe)

- Uçtan uca görevi **tamamlayabilen tek hat** (1/3 + bir ıskalamada 4.35 m).
- Mesafeyi sistematik kapatıyor: en-yakın medyan 4.4 m ↔ bizde 12–25 m.
- Görsel faza gerçekten giriyor; bizim hattın görsel yasası (IBVS/OIPN) 5 koşuda
  hiç tetiklenmedi → gerçek koşullarda DOĞRULANMAMIŞ kod.
- Model + canlı tespit hattı Kayra tarafından bu hat üzerinde aktif geliştiriliyor;
  kullanıcı tercihi de main arayüzünden yana.
- Kural 8 (açıklanabilirlik) + video anlatımı: tek güdüm hattı, iki paralel hattan
  daha savunulabilir.

main'in bilinen zaafları (merge sonrası iş listesi): FP-gürültülü takip (tek-kutu
argmax; 72 kayıp kenarı), 1/3 başarı oranı, kilit §6.1.4 zinciri yok/gösterilmiyor.

## 5) TAŞINACAKLAR (bizden kazanan hatta)

| Parça | Neden | Zorunluluk |
|---|---|---|
| Kilit kuralı §6.1.4 (`guidance/kilit_kurali.py` + arayüz sayacı) | şartname zorunlu (5 sn kilit + hakem paketi) | **ZORUNLU** |
| ByteTrack + gyro-CMC takip (`detection/takip.py`) | video isteri "tracking" + FP'ye karşı ID sürekliliği; main'in argmax'ından sağlam | GÜÇLÜ ADAY (ölçerek) |
| SERT AYRIM düzeni (`web/dev_truth.py` çiti + `arac/paket_kontrol.py`) | main'de truth ÇİTSİZ server içinde — teslim paketinde ihlal riski | **ZORUNLU** |
| Video-ister arayüz kalemleri (olay günlüğü, GNSS kartı, mini-harita, VURUŞ/BAŞARI) | zaten ortak köken; eksik kalan main'e tamamlanır | ZORUNLU |
| Pose koşu-zamanı üçlüsü (PnP terminal mesafe) | terminal faz aracı; PNG'ye mesafe girdisi olabilir | OPSİYONEL (sonra) |
| Test + `arac/` altyapısı (91+ birim test, ab_kiyas, kosu_yonetici) | regresyon güvenliği | ZORUNLU |
| Hızlı `/api/gorsel` + yaş-telafili çizim | zaten iki tarafta var (152a7bc ↔ d3f8d2b) | — |

## 6) Merge planı (ayrı oturum)

1. Kayra ile bu doküman konuşulur → onay.
2. `origin/main` → `yarisma-pipeline` merge; **güdümde main tarafı baz** (bizim
   `ibvs_guidance.py`, OIPN bağları, GPS strike blokları bu kez SİLİNİR — karar gereği).
3. Taşınacaklar tablosu uygulanır (özellikle truth ÇİTLEME main server'ına!).
4. `arac/paket_kontrol.py` koşulur (truth sızıntı taraması) + tüm testler.
5. Sim regresyonu: `ab_kiyas kos --etiket merge-sonrasi --n 3` → başarı ≥ main'in
   bugünkü seviyesi olmalı.

## 7) Model borcu (kazanan hattan bağımsız, EN ÖNCELİKLİ)

- HUD yanlış-pozitifi: eğitim verisine HUD'lu negatif örnekler / HUD maskesi /
  HUD'suz kırpma. Hedef: "TRIGGER" yazısına 0.6 kutu basılmaması.
- Uzak menzil (30–100 m) güveni: küçük-nesne örnekleri, 1280+ eğitim çözünürlüğü.
- Ölçüm: `veri/ab/tani2/kareler/` + ab_kiyas koşuları hazır cetvel.

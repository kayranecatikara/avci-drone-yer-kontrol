# DURUM — 2026-08-18 07:40 (duraklatıldı, kullanıcı çıktı)

## SİSTEMDE AKTİF OLAN (varsayılan AÇIK, doğrulanmış)
1. **Ayna düzeltmesi** — `kopru/tespit_akisi.py::dow_pikseli_yasaya`
   Kök neden buydu. Uçuşta: eğim −0,863 → **+1,016**, aynı işaret %10,2 → **%99,7**.
2. **G3 dikey paketi** — `AVCI_IBVS_DIKEY_UFUK=1` + `AVCI_IBVS_HIZ_SICAK=1.5`
   Uçuşta doğrulandı (aşağıdaki tablo). Olumsuz kontrol 5/5 kötü.

## G3'ÜN UÇUŞTA DOĞRULANMASI (görsel faz, geçerli satırlar)
| ölçü | dün | bu gece |
|---|---|---|
| dikey hata medyanı | 1,34 m | **1,10 m** |
| menzil <6 m'de hata | 1,23 m | **0,78 m** |
| menzil <6 m'de <1 m olan | %43 | **%64** |
| üstteyken alçalma emreden | %48 | **%87** |

## SİSTEMDE KAPALI (bilinçli)
- **Kilit kapısı** — kullanıcı talimatı; ölçümü `arac/KILIT_BULGUSU.md`'de duruyor
- `AVCI_ACCEL_SPLIT`, `AVCI_KOPRU_IC`, `AVCI_IBVS_KOMUT_HIZALA`, `AVCI_IBVS_TERM_ROLL`,
  `AVCI_DEVIR_BEKLE`, `SICRAMA_KORU` — hepsi sınandı, kazanan çıkmadı

## AÇIK SORU (dönünce ilk iş)
İki ölçüt çelişiyor: `lead14` ve `hizala` kapatmada kötü ama vuruşta iyi.
Sebep bulunmadan entegre YOK. Ayrıntı ve yapılacaklar sırası: `GECE_NOTLARI.md` sonu.

## YEDEK
`yedek/GECE_SONU_20260818_073816/` — 152 .py + 21 reçete + 14 kanıt/log, `KUNYE.json` künyeli
Geri dönüş: `yedek/<damga>/kod/<klasör>/<dosya>.py` → yerine kopyala

## TESTLER
566 geçti / 6 kaldı — **6'sı önceden kırıktı**, bu gece bir şey kırılmadı

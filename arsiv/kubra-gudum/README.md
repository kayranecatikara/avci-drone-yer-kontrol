# kubra-gudum — arşivlenen güdüm hattı (2026-07-08)

Kübra'nın güdüm hattından, main'de silinen / koşu hattında kullanılmayan modüller.
`arsiv/` UÇUŞ DIŞIDIR; teslim paketine girmez. Buradaki kod referans/geri-dönüş içindir.

| Dosya | Ne | Not |
|---|---|---|
| `gudum_yasasi.py` | APN + OIPN güdüm yasası (PN ailesi) | main 9b5852d'de silmişti; emekli aday |
| `kilit_kurali.py` | Kilit kuralı §6.1.4 (KilitCfg eşik + sayaçlar, SAF mantık) | **Teslim öncesi hakem BİLDİRİMİ bağlanacaksa geri taşınacak ADAY** (CLAUDE.md "MERGE KALANLARI" 2. madde). Canlı kilit SAYACI zaten `ana_kontrol._kilit_degerlendir`'de yaşıyor (salt gözlem). |
| `test_kilit_kurali.py`, `test_kilit_dortgeni.py`, `test_gudum_hakem.py` | Bu modüllerin kabul testleri | `guidance.` import'ları eski yola göre; geri taşınırsa aynen çalışır |
| `kilit_dortgeni.py`, `tp_fp_analiz.py` | KilitCfg'ye bağımlı analiz araçları (eski `arac/`) | kilit_kurali ile birlikte taşındı |

Not: PNG görsel yasası (`guidance/png_gorsel.py`, main'in hattıydı) buraya alınmadı;
main v7 sıfırlamasında silindi, gerekirse git geçmişinde (89ed0fb öncesi / 176c2b3 merge'i).
İlgili anlatım kartları `docs/anlatim/05_gudum_oipn.md` + `06_kilit_kurali.md` yerinde duruyor.

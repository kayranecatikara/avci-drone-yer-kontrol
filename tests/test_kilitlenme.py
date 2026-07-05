# -*- coding: utf-8 -*-
"""
KILITLENME TAKIBI (sartname olcumu) — 8+1 senaryo testi.
Oyunsuz/SDK'siz calisir: KilitlenmeTakip sentetik det + sim saatiyle beslenir.

Kosum (repo kokunden):  python -m pytest tests/test_kilitlenme.py -q

Senaryolar, silinen eski 8-senaryoluk simden (kayan-pencere/kumulatif API'li
guidance/kilitlenme.py icindi) BUTCE API'sine uyarlanarak yeniden yazildi:
- KILITLENME = 5.0 sn kesintisiz gecerlilik (sure_s = duvar-saati, now - t0).
- Deneme icinde biriken GECERSIZ sure (gap_s) 0.2 sn butcesini asarsa deneme sifirlanir.
- Deneme GECERLI tikte baslar; basari GECERLI tikte ilan edilir (kenar kurali).
Sabitler ana_kontrol.Cfg KILIT_* ile ayni degerlerde yerel P sinifina klonlanir.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from guidance.ibvs_guidance import KilitlenmeTakip  # noqa: E402


class P:
    KILIT_SURE_S     = 5.0
    KILIT_ESIK_ORAN  = 0.06
    KILIT_TOLERANS_S = 0.2
    KILIT_ALAN_X     = 0.25
    KILIT_ALAN_Y     = 0.10


DT = 0.02
W, H = 1000.0, 1000.0


def det_yap(w=0.10, h=0.10, cx=0.5, cy=0.5):
    """Normalize olculerden px det sozlugu (gercek det semasiyla ayni alanlar)."""
    return {"cx": cx * W, "cy": cy * H, "w": w * W, "h": h * H, "W": W, "H": H}


class Surucu:
    """Sim saati + tik surucu. bayat=True -> det_t = now-0.25 (tazelik ihlali)."""

    def __init__(self):
        self.k = KilitlenmeTakip()
        self.now = 100.0

    def tikle(self, n, det=None, bayat=False):
        for _ in range(n):
            self.now += DT
            det_t = None if det is None else (self.now - 0.25 if bayat else self.now)
            self.k.guncelle(det, det_t, self.now, P, DT)
        return self.k


def test_surekli_5s_kilitlenir():
    s = Surucu()
    k = s.tikle(253, det_yap())               # 5.06 s kesintisiz gecerli (float payi)
    assert k.basarili and k.sayi == 1
    assert k.gecerli                          # basari GECERLI tikte ilan edildi
    k2 = s.tikle(50, det_yap())               # devam: sayac tekrar artmaz (deneme basina 1)
    assert k2.sayi == 1


def test_4s_yeterli_degil():
    s = Surucu()
    k = s.tikle(200, det_yap())               # 4.0 s
    assert not k.basarili and k.sayi == 0
    assert k.sure_s < P.KILIT_SURE_S


def test_kumulatif_butce_yasar():
    # 0.10 + 0.08 = 0.18 s gecersiz butce icinde -> deneme YASAR ve basarir
    # (sure_s duvar-saati oldugundan basari yine ~5 s duvar zamaninda gelir).
    s = Surucu()
    s.tikle(100, det_yap())                   # 2.0 s gecerli
    s.tikle(5, det_yap(), bayat=True)         # 0.10 s "kayip"
    s.tikle(50, det_yap())                    # 1.0 s gecerli
    s.tikle(4, det_yap(), bayat=True)         # 0.08 s -> toplam gap 0.18 <= 0.2
    assert s.k.t0 is not None                 # deneme hala ayakta
    k = s.tikle(120, det_yap())               # duvar saati 5 s'yi asar
    assert k.basarili and k.sayi == 1


def test_kumulatif_butce_asilirsa_sifirlanir():
    s = Surucu()
    s.tikle(100, det_yap())
    s.tikle(5, det_yap(), bayat=True)         # 0.10
    s.tikle(50, det_yap())
    s.tikle(4, det_yap(), bayat=True)         # 0.18
    s.tikle(3, det_yap(), bayat=True)         # 0.24 > 0.2 -> deneme SIFIRLANIR
    assert s.k.t0 is None and not s.k.basarili
    assert s.k.gap_s == 0.0 and s.k.sure_s == 0.0
    k = s.tikle(253, det_yap())               # temiz yeniden deneme -> basari
    assert k.basarili and k.sayi == 1


def test_boyut_yetersizse_asla_kilitlenmez():
    s = Surucu()
    k = s.tikle(150, det_yap(w=0.05, h=0.10))  # genislik %5 < %6 esik
    assert not k.basarili and k.t0 is None
    assert not k.gecerli and k.neden == "kucuk"


def test_alan_disi_asla_baslamaz():
    s = Surucu()
    k = s.tikle(150, det_yap(cx=0.80))        # sag kenar 0.85 > 0.75 (Av disina tasar)
    assert not k.basarili and k.t0 is None
    assert k.neden == "alan disi"


def test_gormeyince_ve_bayatken_neden_ve_butce():
    s = Surucu()
    k = s.tikle(50, det=None)                 # hic tespit yok: deneme yok, butce AKMAZ
    assert k.neden == "tespit yok" and k.t0 is None and k.gap_s == 0.0
    s.tikle(50, det_yap())                    # deneme basladi (1.0 s)
    k = s.tikle(3, det_yap(), bayat=True)     # bayat kare: "kayip" + butce yer
    assert k.neden == "kayip" and k.gap_s > 0.0 and k.t0 is not None


def test_alan_cikisi_denemeyi_sifirlar_ve_temiz_baslar():
    s = Surucu()
    s.tikle(150, det_yap())                   # 3.0 s gecerli
    s.tikle(15, det_yap(cx=0.80))             # 0.3 s alan disi -> butce asilir -> sifir
    assert s.k.t0 is None
    k = s.tikle(253, det_yap())               # yeniden giris: sifirdan sayar ve basarir
    assert k.basarili and k.sayi == 1
    assert k.sure_s < 5.3                     # eski 3 s'lik birikim TASINMADI


def test_sifirla_latch_ve_denemeyi_temizler():
    s = Surucu()
    k = s.tikle(253, det_yap())
    assert k.basarili
    k.sifirla()
    assert not k.basarili and k.sayi == 0 and k.t0 is None
    assert k.neden == "tespit yok" and k.sure_s == 0.0 and k.gap_s == 0.0


def test_tam_sinir_butce_float_tasmasi_yok():
    # TAM 0.200 s gecersiz (10 tik x 0.02): 1e-6 payi sayesinde SIFIRLANMAZ;
    # 11. tik (0.22) sifirlar. "200 ms'ye KADAR tolerans" siniri DAHIL.
    s = Surucu()
    s.tikle(50, det_yap())
    s.tikle(10, det_yap(), bayat=True)        # gap ~= 0.200
    assert s.k.t0 is not None                 # yasiyor
    s.tikle(1, det_yap(), bayat=True)         # 0.22 -> asti
    assert s.k.t0 is None

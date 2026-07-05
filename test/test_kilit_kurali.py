# -*- coding: utf-8 -*-
"""
FAZ 3 kabul testleri: guidance/kilit_kurali.py (§6.1.4 sayaci; SAF mantik).
Calistirma:  python test/test_kilit_kurali.py  (sim GEREKMEZ — sentetik girdi)
Senaryolar: pencere kenari (AV disi), kesinti, coast, kenar-tetik, angajman.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from guidance.kilit_kurali import KilitDurumu, KilitCfg

W, H = 1920, 1080
# NOT: kilit conf esigi artik KilitCfg.KILIT_CONF_MIN=0.72 (adim'a DISARIDAN
# gecilmez). _hedef varsayilan conf=0.9 -> kilit gecer; ara-bant testi 0.60 kullanir.


def _hedef(cx_n=0.5, cy_n=0.5, kap=0.20, conf=0.9, tespit_mi=True,
           durum="CONFIRMED"):
    # kap = EKSEN-max kaplama (max(w/W, h/H)); sartname eksen-bazli. Kucuk eksen
    # (H) uzerinden bbox: h/H = kap (max), w/W = kap*H/W < kap. Kare bbox (w=h).
    wh = kap * H
    return {"cx": cx_n * W, "cy": cy_n * H, "w": wh, "h": wh,
            "conf": conf, "tespit_mi": tespit_mi, "track_durumu": durum}


def _besle(kd, hedef, sn, dt=0.033, t0=0.0):
    """hedef'i sn boyunca (dt adimlarla) besle; son adim ciktisini dondur."""
    n = int(sn / dt)
    out = None
    t = t0
    for _ in range(n):
        t += dt
        out = kd.adim(hedef, W, H, t)
    return out, t


def test_ideal_kilit_5sn():
    kd = KilitDurumu()
    out, _ = _besle(kd, _hedef(), 5.5)
    assert out["kilit_tamam"] is True
    assert out["kumulatif_kilit_sn"] >= 5.0
    assert out["sayan"] is True


def test_kenar_tetik_bir_kez():
    kd = KilitDurumu()
    yeni_sayisi = 0
    t = 0.0
    for _ in range(int(7.0 / 0.033)):
        t += 0.033
        o = kd.adim(_hedef(), W, H, t)
        if o["yeni_kilit"]:
            yeni_sayisi += 1
    assert yeni_sayisi == 1, "kilit_tamam KENAR tetikli (bir kez)"


def test_av_disi_saymaz():
    kd = KilitDurumu()
    # yatay %80 (AV disi: 0.25-0.75) -> hic saymamali
    out, _ = _besle(kd, _hedef(cx_n=0.80), 6.0)
    assert out["sayan"] is False and out["kilit_tamam"] is False
    assert out["kumulatif_kilit_sn"] == 0.0
    # dikey %95 (AV disi: 0.10-0.90)
    kd2 = KilitDurumu()
    out2, _ = _besle(kd2, _hedef(cy_n=0.95), 6.0)
    assert out2["sayan"] is False


def test_kaplama_dusuk_saymaz():
    kd = KilitDurumu()
    out, _ = _besle(kd, _hedef(kap=0.04), 6.0)       # eksen-max 0.04 < 0.06 esik
    assert out["sayan"] is False and out["kilit_tamam"] is False
    assert out["engel"] == "kaplama_dusuk"


def test_kaplama_eksen_bir_eksende_yeter():
    # Sartname: EN AZ BIR eksende >=%5. Dar-yuksek bbox: w/W kucuk ama h/H >=%5 -> SAYAR.
    kd = KilitDurumu()
    W2, H2 = 1920, 1080
    # w/W = 0.02 (dar), h/H = 0.10 (yuksek) -> max=0.10 >= 0.06 -> gecerli
    h = {"cx": 0.5 * W2, "cy": 0.5 * H2, "w": 0.02 * W2, "h": 0.10 * H2,
         "conf": 0.9, "tespit_mi": True, "track_durumu": "CONFIRMED"}
    t = 0.0
    for _ in range(20):
        t += 0.05
        out = kd.adim(h, W2, H2, t)
    assert out["sayan"] is True, "bir eksende %5 yeter (alan orani DEGIL)"
    assert abs(out["kaplama_dikey"] - 0.10) < 1e-6 and abs(out["kaplama_yatay"] - 0.02) < 1e-6


def test_coast_saymaz():
    kd = KilitDurumu()
    out, _ = _besle(kd, _hedef(tespit_mi=False), 6.0)  # coast: tespit_mi False
    assert out["sayan"] is False


def test_tentative_saymaz():
    kd = KilitDurumu()
    out, _ = _besle(kd, _hedef(durum="TENTATIVE"), 6.0)
    assert out["sayan"] is False


def test_dusuk_conf_saymaz():
    kd = KilitDurumu()
    out, _ = _besle(kd, _hedef(conf=0.30), 6.0)      # kilit esigi 0.72 alti
    assert out["sayan"] is False


def test_conf_ara_bant_kilit_saymaz_track_gecerli():
    # 0.45-0.72 ARA BANT: handoff (VIS_CONF_MIN=0.45) gecer, track CONFIRMED olur;
    # AMA kilit sayaci SIKI esik (KILIT_CONF_MIN=0.72) -> SAYMAZ. engel=dusuk_conf
    # (track_onaysiz DEGIL: track gecerli, yalniz kilit conf'u sIKI). Esik AYRISMASI.
    kd = KilitDurumu()
    out, _ = _besle(kd, _hedef(conf=0.60), 6.0)      # 0.45<0.60<0.72
    assert out["sayan"] is False
    assert out["engel"] == "dusuk_conf"
    assert out["kumulatif_kilit_sn"] == 0.0
    # AYNI track 0.72 ustunde -> kilit ILERLER (esik farkinin kaniti)
    kd2 = KilitDurumu()
    out2, _ = _besle(kd2, _hedef(conf=0.75), 5.5)
    assert out2["kilit_tamam"] is True


def test_kesintili_kumulatif_pencere():
    # 3 sn say + 2 sn kesinti (AV disi) + 3 sn say = kumulatif 6 sn > 5 (10 sn
    # pencere ici) -> kilit_tamam. Kesinti surekli'yi sifirlar ama kumulatif tutar.
    kd = KilitDurumu()
    _, t = _besle(kd, _hedef(), 3.0)
    out2, t = _besle(kd, _hedef(cx_n=0.85), 2.0, t0=t)   # 2 sn AV disi
    assert out2["surekli_kilit_sn"] == 0.0               # kesinti -> surekli sifir
    out3, t = _besle(kd, _hedef(), 3.0, t0=t)
    assert out3["kilit_tamam"] is True                  # kumulatif 6 sn (pencere ici)


def test_pencere_kayar_eski_dusun():
    # 4 sn say -> 8 sn AV disi (eski 4 sn pencereden CIKAR) -> 4 sn say:
    # kumulatif hic 5'e ulasmaz (eski dusuyor). 10 sn pencere kaydigini kanitlar.
    kd = KilitDurumu()
    _, t = _besle(kd, _hedef(), 4.0)
    _, t = _besle(kd, _hedef(cx_n=0.85), 8.0, t0=t)     # 8 sn bosluk (>pencere-4)
    out, t = _besle(kd, _hedef(), 4.0, t0=t)
    assert out["kilit_tamam"] is False, "eski say-frame'ler penceredin dusmeli"
    assert out["kumulatif_kilit_sn"] < 5.0


def test_angajman_hazir_surekli():
    kd = KilitDurumu()
    # kesintisiz 5.5 sn -> kilit_tamam + surekli>=3 -> angajman hazir
    _besle(kd, _hedef(), 5.5)
    assert kd.angajman_hazir() is True
    # kesinti -> surekli sifirlanir -> angajman DEGIL (kilit_tamam kalir ama surekli<3)
    kd.adim(_hedef(cx_n=0.9), W, H, 100.0)
    assert kd.kilit_tamam is True and kd.angajman_hazir() is False


def test_kacak_kopru_kisa_dondurur_ama_angajman_bitiste_yok():
    # Kisa kacak (<=200 ms) surekli'yi DONDURUR (kopru) ama KOPRU ACIKKEN angajman
    # VERILMEZ (bitiste gecersiz); sonraki sayan kare kopruyu KAPATIR -> angajman.
    kd = KilitDurumu()
    _, t = _besle(kd, _hedef(), 5.5)           # kilit_tamam + surekli >=5
    surekli_once = kd.surekli_kilit_sn
    assert kd.kilit_tamam and surekli_once >= 5.0
    # 0.15 sn kisa kacak (<=0.2) -> surekli DONAR + kopru acik
    out, t = _besle(kd, _hedef(cx_n=0.9), 0.15, t0=t)
    assert abs(kd.surekli_kilit_sn - surekli_once) < 1e-6, "kisa kacak surekli'yi DONDURUR"
    assert kd._kopru_acik is True
    assert kd.angajman_hazir() is False        # KOPRU ACIK -> bitiste angajman YOK
    # tekrar sayan kare -> kopru KAPANIR -> angajman hazir
    out, t = _besle(kd, _hedef(), 0.1, t0=t)
    assert kd._kopru_acik is False and kd.surekli_kilit_sn > surekli_once
    assert kd.angajman_hazir() is True


def test_kacak_uzun_sifirlar():
    # Uzun kacak (>200 ms) KESINTISIZ sayaci SIFIRLAR.
    kd = KilitDurumu()
    _, t = _besle(kd, _hedef(), 3.5)
    assert kd.surekli_kilit_sn >= 3.0
    out, t = _besle(kd, _hedef(cx_n=0.9), 0.35, t0=t)  # 0.35 sn > 0.2 tolerans
    assert kd.surekli_kilit_sn == 0.0, "uzun kacak surekli'yi SIFIRLAR"
    assert kd.angajman_hazir() is False


def test_kopru_ilk_karede_yok():
    # ILK karede (surekli=0) kacak -> KOPRULEME YOK (surekli 0 kalir; baslangicta gecersiz)
    kd = KilitDurumu()
    out, _ = _besle(kd, _hedef(cx_n=0.9), 0.15)   # hic sayan yok, hep kacak
    assert kd.surekli_kilit_sn == 0.0 and kd._kopru_acik is False


def test_kumulatif_toleransa_guvenmez():
    # KUMULATIF toleransa GUVENMEZ: yalniz SAYAN karelerle 5.0 dolar. Serpistirilmis
    # kisa kaclar (kopru surekli'yi tutar) -> kumulatif kacak sirasinda ARTMAZ,
    # yalniz sayan karelerle dolar; yine de yeterli sayan-sure birikince kilit olur.
    kd = KilitDurumu()
    t = 0.0
    for blok in range(14):
        _, t = _besle(kd, _hedef(), 0.5, t0=t)          # 0.5 sn say
        _, t = _besle(kd, _hedef(cx_n=0.9), 0.05, t0=t) # 0.05 sn kacak (<=0.2 kopru)
    assert kd.kilit_tamam is True, "sayan kareler 5.0 sn'yi doldurur (kacak eklenmez)"


def test_engel_teshisi():
    # Kilit tamamlanamazsa hangi kosulun engel oldugu sayilir (teshis).
    kd = KilitDurumu()
    out, _ = _besle(kd, _hedef(cx_n=0.85), 3.0)        # hep AV disi yatay
    assert out["engel"] == "AV_disi_yatay"
    oz = kd.engel_ozeti()
    assert oz and "AV_disi_yatay" in oz and oz["AV_disi_yatay"] > 10
    # farkli engeller ayrik sayilir
    kd2 = KilitDurumu()
    _besle(kd2, _hedef(kap=0.02), 1.0)                # kaplama dusuk (eksen)
    _besle(kd2, _hedef(durum="TENTATIVE"), 1.0, t0=1.0)  # track onaysiz
    oz2 = kd2.engel_ozeti()
    assert "kaplama_dusuk" in oz2 and "track_onaysiz" in oz2


def test_sifirla():
    kd = KilitDurumu()
    _besle(kd, _hedef(), 5.5)
    kd.sifirla()
    assert kd.kilit_tamam is False and kd.surekli_kilit_sn == 0.0
    assert kd.adim(_hedef(), W, H, 0.0)["kumulatif_kilit_sn"] == 0.0


if __name__ == "__main__":
    testler = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in testler:
        t()
        print("OK  %s" % t.__name__)
    print("TUM TESTLER GECTI (%d)" % len(testler))

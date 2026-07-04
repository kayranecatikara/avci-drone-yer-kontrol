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
CONF = 0.45


def _hedef(cx_n=0.5, cy_n=0.5, kaplama=0.10, conf=0.9, tespit_mi=True,
           durum="CONFIRMED"):
    # kaplama = w*h/(W*H); kare bbox varsay -> w=h=sqrt(kaplama*W*H)
    wh = (kaplama * W * H) ** 0.5
    return {"cx": cx_n * W, "cy": cy_n * H, "w": wh, "h": wh,
            "conf": conf, "tespit_mi": tespit_mi, "track_durumu": durum}


def _besle(kd, hedef, sn, dt=0.033, t0=0.0):
    """hedef'i sn boyunca (dt adimlarla) besle; son adim ciktisini dondur."""
    n = int(sn / dt)
    out = None
    t = t0
    for _ in range(n):
        t += dt
        out = kd.adim(hedef, W, H, t, CONF)
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
        o = kd.adim(_hedef(), W, H, t, CONF)
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
    out, _ = _besle(kd, _hedef(kaplama=0.03), 6.0)   # esik 0.06 alti
    assert out["sayan"] is False and out["kilit_tamam"] is False


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
    out, _ = _besle(kd, _hedef(conf=0.30), 6.0)      # uretim esigi 0.45 alti
    assert out["sayan"] is False


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
    kd.adim(_hedef(cx_n=0.9), W, H, 100.0, CONF)
    assert kd.kilit_tamam is True and kd.angajman_hazir() is False


def test_kacak_tolerans_kisa_surekli_bozmaz():
    # Kisa kacak (<0.5 sn tolerans; tek-kare blur/parazit) KESINTISIZ sayaci
    # BOZMAZ: surekli donar, sifirlanmaz.
    kd = KilitDurumu()
    _, t = _besle(kd, _hedef(), 5.5)           # kilit_tamam + surekli >=5
    surekli_once = kd.surekli_kilit_sn
    assert kd.kilit_tamam and surekli_once >= 5.0
    # 0.3 sn kisa kacak (AV disi) -> tolerans altinda; surekli KORUNMALI
    out, t = _besle(kd, _hedef(cx_n=0.9), 0.3, t0=t)
    assert abs(kd.surekli_kilit_sn - surekli_once) < 1e-6, "kisa kacak surekli'yi DONDURUR"
    assert kd.angajman_hazir() is True         # kilit_tamam + surekli >=3 korundu
    # tekrar say -> surekli devam eder (sifirlanmadi)
    out, t = _besle(kd, _hedef(), 0.5, t0=t)
    assert kd.surekli_kilit_sn > surekli_once


def test_kacak_tolerans_uzun_sifirlar():
    # Uzun kacak (>0.5 sn tolerans) KESINTISIZ sayaci SIFIRLAR.
    kd = KilitDurumu()
    _, t = _besle(kd, _hedef(), 3.5)
    assert kd.surekli_kilit_sn >= 3.0
    out, t = _besle(kd, _hedef(cx_n=0.9), 0.8, t0=t)   # 0.8 sn > 0.5 tolerans
    assert kd.surekli_kilit_sn == 0.0, "uzun kacak surekli'yi SIFIRLAR"
    assert kd.angajman_hazir() is False


def test_kacak_tolerans_kumulatif_bozmaz():
    # %5 kare kacagi kumulatif sayaci "bozmaz": kacak kareler DUSURMEZ, yalniz
    # eklenmez -> kilit biraz gec ama olusur (pencere ici birikim korunur).
    kd = KilitDurumu()
    # 5.5 sn say arasinda serpistirilmis kisa kacaklar -> kumulatif yine >=5 olur
    t = 0.0
    for blok in range(12):
        _, t = _besle(kd, _hedef(), 0.5, t0=t)          # 0.5 sn say
        _, t = _besle(kd, _hedef(cx_n=0.9), 0.05, t0=t) # 0.05 sn kacak (%~9 ama kisa)
    assert kd.kilit_tamam is True, "serpistirilmis kisa kacak kilidi engellemez"


def test_engel_teshisi():
    # Kilit tamamlanamazsa hangi kosulun engel oldugu sayilir (teshis).
    kd = KilitDurumu()
    out, _ = _besle(kd, _hedef(cx_n=0.85), 3.0)        # hep AV disi yatay
    assert out["engel"] == "AV_disi_yatay"
    oz = kd.engel_ozeti()
    assert oz and "AV_disi_yatay" in oz and oz["AV_disi_yatay"] > 10
    # farkli engeller ayrik sayilir
    kd2 = KilitDurumu()
    _besle(kd2, _hedef(kaplama=0.02), 1.0)            # kaplama dusuk
    _besle(kd2, _hedef(durum="TENTATIVE"), 1.0, t0=1.0)  # track onaysiz
    oz2 = kd2.engel_ozeti()
    assert "kaplama_dusuk" in oz2 and "track_onaysiz" in oz2


def test_sifirla():
    kd = KilitDurumu()
    _besle(kd, _hedef(), 5.5)
    kd.sifirla()
    assert kd.kilit_tamam is False and kd.surekli_kilit_sn == 0.0
    assert kd.adim(_hedef(), W, H, 0.0, CONF)["kumulatif_kilit_sn"] == 0.0


if __name__ == "__main__":
    testler = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in testler:
        t()
        print("OK  %s" % t.__name__)
    print("TUM TESTLER GECTI (%d)" % len(testler))

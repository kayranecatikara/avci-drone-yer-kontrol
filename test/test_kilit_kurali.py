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

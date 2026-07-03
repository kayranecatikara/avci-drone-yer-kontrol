# -*- coding: utf-8 -*-
"""
FAZ 1 kabul testleri: detection/takip.py (ByteTrack) + kamera_model gyro-CMC.
Calistirma:  python test/test_takip.py   (sim/YOLO GEREKMEZ — sentetik tespit)
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from detection import takip as tk
from detection import kamera_model as km


def _det(cx, cy, w=40, h=30, conf=0.9, **ek):
    d = {"cx": float(cx), "cy": float(cy), "w": float(w), "h": float(h),
         "conf": float(conf), "W": 1920, "H": 1080}
    d.update(ek)
    return d


def test_iou_ve_kalman_donusum():
    assert abs(tk._iou((0, 0, 10, 10), (0, 0, 10, 10)) - 1.0) < 1e-9
    assert tk._iou((0, 0, 10, 10), (100, 100, 10, 10)) == 0.0
    # bbox->z->bbox gidis-donus
    cx, cy, w, h = tk._z_to_bbox(*tk._bbox_to_z((50, 60, 40, 20)))
    assert abs(cx - 50) < 1e-6 and abs(cy - 60) < 1e-6
    assert abs(w - 40) < 1e-6 and abs(h - 20) < 1e-6


def test_confirmed_min_hits():
    # 5 ardisik tespit -> CONFIRMED (mevcut FSM "5 kare" kurali)
    tp = tk.Takipci()
    cx = 500.0
    for i in range(4):
        out = tp.guncelle([_det(cx + i * 2, 400)], 0.02)
        assert out is None, i               # TENTATIVE: FSM'e sunulmaz
    out = tp.guncelle([_det(cx + 8, 400)], 0.02)   # 5. eslesme
    assert out is not None
    assert out["track_durumu"] == "CONFIRMED"
    assert out["tespit_mi"] is True
    assert "track_id" in out and "bbox" in out


def test_parazit_id_sabit():
    # conf dalgalanirken (0.9 <-> 0.2) track ID kopmamali (BYTE: dusuk conf surdurur)
    tp = tk.Takipci()
    for i in range(6):
        tp.guncelle([_det(500 + i, 400, conf=0.9)], 0.02)
    ilk = tp.en_iyi_track().id
    # conf dusuk (0.2: YUKSEK esigin altinda ama DUSUK esigin ustunde) -> ikinci tur
    for i in range(6, 14):
        out = tp.guncelle([_det(500 + i, 400, conf=0.2)], 0.02)
        assert out is not None, "dusuk-conf tespit track'i SURDURMELI (BYTE)"
        assert out["track_id"] == ilk, "ID kopmamali"
    assert out["track_durumu"] in ("CONFIRMED", "LOST")


def test_sahte_pozitif_confirmed_olamaz():
    # tek-kare parazit (ardisik olmayan): CONFIRMED'e ulasamaz, cabuk oler
    tp = tk.Takipci()
    for i in range(10):
        det = [_det(500, 400, conf=0.9)] if i % 3 == 0 else []   # 3 tikte 1 gorunur
        tp.guncelle(det, 0.02)
    # ardisik eslesme hic 5'e ulasmaz -> hic CONFIRMED yok
    assert tp.en_iyi_track() is None
    assert all(t.durum != "CONFIRMED" for t in tp.trackler)


def test_dusuk_conf_yeni_track_acamaz():
    tp = tk.Takipci()
    for _ in range(5):
        out = tp.guncelle([_det(500, 400, conf=0.2)], 0.02)   # hep dusuk conf
    assert len(tp.trackler) == 0, "dusuk-conf tespit YENI track baslatamaz"
    assert out is None


def test_coast_ve_tespit_mi():
    # CONFIRMED track olcumsuz kalinca coast eder: tespit_mi=False, ID surer
    tp = tk.Takipci()
    for i in range(6):
        tp.guncelle([_det(500 + i, 400)], 0.02)
    tid = tp.en_iyi_track().id
    # 3 tik olcumsuz (coast, MAX_COAST=25 altinda)
    for _ in range(3):
        out = tp.guncelle([], 0.02)
        assert out is not None and out["track_id"] == tid   # ID surer (coast)
        assert out["tespit_mi"] is False                    # ama gercek tespit YOK
        assert out["track_durumu"] == "LOST"
    # yeniden yakala -> CONFIRMED + tespit_mi True
    out = tp.guncelle([_det(510, 400)], 0.02)
    assert out["tespit_mi"] is True and out["track_durumu"] == "CONFIRMED"


def test_coast_asimi_removed():
    tp = tk.Takipci()
    for i in range(6):
        tp.guncelle([_det(500, 400)], 0.02)
    for _ in range(tk.TakipCfg.MAX_COAST + 2):
        tp.guncelle([], 0.02)
    assert tp.en_iyi_track() is None
    assert len(tp.trackler) == 0        # REMOVED temizlendi


def test_en_iyi_track_secimi():
    # iki track: biri uzun-yasayan (gercek Talon), biri kisa (bulut) -> uzun secilir
    tp = tk.Takipci()
    for i in range(12):
        tp.guncelle([_det(500, 400, conf=0.9)], 0.02)     # surekli hedef
    for i in range(6):
        tp.guncelle([_det(500, 400, conf=0.9), _det(1200, 200, conf=0.9)], 0.02)
    en = tp.en_iyi_track()
    assert abs(en.bbox()[0] - 500) < 60, "en uzun yasayan (hedef) secilmeli, bulut degil"


def test_keypoints_tasima():
    tp = tk.Takipci()
    kp = [[100, 200, 0.9]]
    for i in range(6):
        tp.guncelle([_det(500, 400, keypoints=kp)], 0.02)
    out = tp.en_iyi_cikti()
    assert out.get("keypoints") == kp
    # coast'ta bayat poz gitmesin: tespit_mi False -> keypoints yok
    out = tp.guncelle([], 0.02)
    assert "keypoints" not in out and out["tespit_mi"] is False


# ---- gyro-CMC homografi (kamera_model) ----
def test_cmc_homografi_ozdeslik():
    W, H = 1920, 1080
    Hm = km.cmc_homografi(W, H, (0, 0, 10), (0, 0, 10))     # donus yok
    assert np.allclose(Hm / Hm[2, 2], np.eye(3), atol=1e-9)


def test_cmc_isaret_yaw():
    # Saf YAW: kamera_model yaw CCW (+ = burun SOLA doner). Dunya-sabit hedef bu
    # durumda goruntude SAGA kayar (sola donerken ondeki hedef saga kacar) -> u
    # ARTMALI. CMC homografisi ONCEKI konumu YENI konuma tasir. (Sim'in gercek
    # yaw isareti kosu_yonetici CMC isaret testinde ayrica dogrulanir.)
    W, H = 1920, 1080
    Hm = km.cmc_homografi(W, H, (0.0, 0.0, 0.0), (0.0, 0.0, 5.0))
    q = Hm @ np.array([W / 2.0, H / 2.0, 1.0])
    u2 = q[0] / q[2]
    assert u2 > W / 2.0 + 5, "yaw+ (CCW, burun sola) -> hedef goruntude SAGA (u artar)"
    # buyukluk ~fx*tan(5): tilt 25 yaw'i saf z-donusu olmaktan cikardigindan tam
    # degil (%~10 sapma normal); isaret testi -> mertebe kontrolu (0.8x..1.2x).
    beklenen = km.fx_px(W) * math.tan(math.radians(5.0))
    assert abs((u2 - W / 2.0) - beklenen) < 0.20 * beklenen, (u2 - W / 2.0, beklenen)


def test_cmc_isaret_pitch():
    # Saf PITCH: burun YUKARI (pitch+) -> hedef goruntude ASAGI kaymali (v artar)
    W, H = 1920, 1080
    Hm = km.cmc_homografi(W, H, (0.0, 0.0, 0.0), (0.0, 5.0, 0.0))
    q = Hm @ np.array([W / 2.0, H / 2.0, 1.0])
    v2 = q[1] / q[2]
    assert v2 > H / 2.0 + 5, "pitch+ (burun yukari) -> hedef goruntude ASAGI (v artar)"


def test_cmc_track_warp_azaltir_kaymayi():
    # Uctan uca: hedef DUNYADA sabit, avci yaw doner. CMC warp'siz track kayar,
    # warp'li track olcumun uzerinde kalir (eslestirme kopmaz).
    W, H = 1920, 1080
    K = km.K_matrisi(W, H)
    hedef_dunya = np.array([10000.0, 0.0, 0.0])   # ileri-ufuk, cok uzak
    dron = np.array([0.0, 0.0, 0.0])

    def piksel(yaw):
        pk = km.dunya_to_kamera(hedef_dunya, dron, 0.0, 0.0, yaw)
        return km.izdusur(pk, K)

    tp_ham = tk.Takipci()
    tp_cmc = tk.Takipci()
    yaw = 0.0
    for i in range(8):                      # kilitle (yaw sabit)
        u, v = piksel(yaw)
        tp_ham.guncelle([_det(u, v)], 0.02)
        tp_cmc.guncelle([_det(u, v)], 0.02)
    # simdi avci yaw'i her tik +2 derece; SONRAKI olcum gelmeden CMC warp uygulanir
    kaymalar_ham, kaymalar_cmc = [], []
    for i in range(6):
        yaw_yeni = yaw + 2.0
        Hcmc = km.cmc_homografi(W, H, (0, 0, yaw), (0, 0, yaw_yeni))
        u, v = piksel(yaw_yeni)             # hedefin YENI gercek pikseli
        # predict+warp SONRASI track merkezi ne kadar olcumden uzak?
        tp_ham.guncelle([], 0.02)                       # olcum yok, warp yok
        for t in tp_cmc.trackler:                       # cmc: elle predict+warp
            t.tahmin(0.02, Hcmc)
        eh = tp_ham.en_iyi_track()
        ec = tp_cmc.en_iyi_track()
        kaymalar_ham.append(abs(eh.bbox()[0] - u))
        kaymalar_cmc.append(abs(ec.bbox()[0] - u))
        # cmc track'i olcumle guncelle (kilit sursun), ham da
        tp_cmc.trackler[0].guncelle(_det(u, v))
        tp_ham.guncelle([_det(u, v)], 0.02)
        yaw = yaw_yeni
    assert np.mean(kaymalar_cmc) < 0.5 * np.mean(kaymalar_ham), \
        (np.mean(kaymalar_cmc), np.mean(kaymalar_ham))


if __name__ == "__main__":
    testler = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in testler:
        t()
        print("OK  %s" % t.__name__)
    print("TUM TESTLER GECTI (%d)" % len(testler))

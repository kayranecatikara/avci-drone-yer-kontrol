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
    # ONAY_MIN_HIT olcumde CONFIRMED (toplam; ardisik SART DEGIL — 9 Tem canli dersi:
    # ~8 FPS dongude dedektor delikleri ardisik sayaci hep sifirlayip izi oldururdu)
    tp = tk.Takipci()
    cx = 500.0
    n = tk.TakipCfg.ONAY_MIN_HIT
    for i in range(n - 1):
        out = tp.guncelle([_det(cx + i * 2, 400)], 0.02)
        assert out is None, i               # TENTATIVE: FSM'e sunulmaz
    out = tp.guncelle([_det(cx + 2 * n, 400)], 0.02)   # n. olcum
    assert out is not None
    assert out["track_durumu"] == "CONFIRMED"
    assert out["tespit_mi"] is True
    assert "track_id" in out and "bbox" in out


def test_delikli_tespit_yine_onaylanir():
    # CANLI SENARYO (8 FPS, dt=0.12): olcumler arasinda tek-kare delik olsa da
    # iz olmez (TENT_COAST_S affi) ve toplam hit ONAY_MIN_HIT'e ulasinca onaylanir.
    tp = tk.Takipci()
    out = None
    for i in range(6):                       # var-yok-var-yok-var-yok
        dets = [_det(500 + i * 3, 400)] if i % 2 == 0 else []
        out = tp.guncelle(dets, 0.12)
    # son tik delik oldugundan iz LOST'ta olabilir; onemli olan ONAYLANMIS olmasi
    assert tp.en_iyi_track() is not None, \
        "delikli ama tekrarlanan tespit onaylanmali (eski kod burada izi olduruyordu)"


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
    # tek/cift-kare parazit: ONAY_MIN_HIT olcume ulasamadan TENT_COAST_S dolar, oler.
    # (dt=0.12 = canli ~8 FPS; parazit 2 kare gorunur, sonra kaybolur)
    tp = tk.Takipci()
    for i in range(8):
        det = [_det(500, 400, conf=0.9)] if i < 2 else []
        tp.guncelle(det, 0.12)
    assert tp.en_iyi_track() is None
    assert len(tp.trackler) == 0, "parazit izi TENT_COAST_S sonunda temizlenmeli"


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
    # 3 tik olcumsuz (coast; 3*0.02s = COAST_S altinda)
    for _ in range(3):
        out = tp.guncelle([], 0.02)
        assert out is not None and out["track_id"] == tid   # ID surer (coast)
        assert out["tespit_mi"] is False                    # ama gercek tespit YOK
        assert out["track_durumu"] == "LOST"
    # yeniden yakala -> CONFIRMED + tespit_mi True
    out = tp.guncelle([_det(510, 400)], 0.02)
    assert out["tespit_mi"] is True and out["track_durumu"] == "CONFIRMED"


def test_coast_asimi_removed():
    # olcumsuz sure COAST_S'i asinca iz REMOVED (sure-tabanli: dongu hizi ne olursa
    # olsun hayalet kutu en fazla COAST_S saniye yasar — 9 Tem canli dersi)
    tp = tk.Takipci()
    for i in range(6):
        tp.guncelle([_det(500, 400)], 0.02)
    dt = 0.12                                        # canli ~8 FPS
    for _ in range(int(tk.TakipCfg.COAST_S / dt) + 2):
        tp.guncelle([], dt)
    assert tp.en_iyi_track() is None
    assert len(tp.trackler) == 0        # REMOVED temizlendi


def test_olculen_iz_hayaleti_bastirir():
    # Iki CONFIRMED iz: eski/uzun-yasayan iz coast'a dustu (hayalet), yeni iz BU TIK
    # olculdu -> cikti OLCULEN izi vermeli (eski max(hits) hayaleti secip gercek
    # tespiti gizliyordu; 9 Tem canli regresyonun 3. kok nedeni).
    tp = tk.Takipci()
    for i in range(10):                              # eski iz: 10 hit
        tp.guncelle([_det(500, 400)], 0.02)
    # eski iz kayboldu, baska yerde yeni hedef cikti; ayni anda ikisi de var
    out = None
    for i in range(tk.TakipCfg.ONAY_MIN_HIT):        # yeni iz onaylanana kadar
        out = tp.guncelle([_det(1200, 300)], 0.02)   # eski iz coast'ta (LOST)
    assert out is not None
    assert abs(out["cx"] - 1200) < 60, "olculen taze iz secilmeli, coast'taki hayalet degil"
    assert out["tespit_mi"] is True


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


def test_cmc_clamp_asiri_warp_atlar():
    # Yanlis-isaret emniyeti: kutuyu ekran genisliginin yarisi kadar firlatan bir
    # homografi max_kaydirma tavanini asar -> warp ATLANIR (merkez oldugu yerde kalir).
    W, H = 1920, 1080
    kf = tk._KalmanKutu((W / 2.0, H / 2.0, 40 * 30, 40.0 / 30.0), tk.TakipCfg())
    cx0, cy0 = kf.x[0], kf.x[1]
    # +600 px oteleyen homografi (dogrudan translation)
    Hbig = np.array([[1.0, 0.0, 600.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    kf.warp_merkez(Hbig, max_kaydirma=0.25 * W)   # 600 > 480 -> atla
    assert abs(kf.x[0] - cx0) < 1e-6 and abs(kf.x[1] - cy0) < 1e-6, "asiri warp atlanmali"
    # kucuk warp (100 px < 480) uygulanir
    Hsmall = np.array([[1.0, 0.0, 100.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    kf.warp_merkez(Hsmall, max_kaydirma=0.25 * W)
    assert abs(kf.x[0] - (cx0 + 100)) < 1e-6, "mesru warp uygulanmali"


def test_cikti_t_ve_cls_tasima():
    # cikti() olcum tikinde son_det'in t/cls'ini tasir (server UI yas-telafisi +
    # sinif etiketi bunlara dayanir); coast tikinde t TASINMAZ (bayat zaman
    # damgasiyla asiri ileri-cizim olmasin — server 'simdi' atar).
    tp = tk.Takipci()
    out = None
    for i in range(6):
        out = tp.guncelle([_det(500 + i, 400, t=100.0 + i * 0.05, cls=0)], 0.02)
    assert out is not None
    assert out["cls"] == 0
    assert abs(out["t"] - (100.0 + 5 * 0.05)) < 1e-9
    assert out["tespit_mi"] is True
    out = tp.guncelle([], 0.02)                     # olcum yok -> coast
    assert out is not None and out["tespit_mi"] is False
    assert "t" not in out


if __name__ == "__main__":
    testler = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in testler:
        t()
        print("OK  %s" % t.__name__)
    print("TUM TESTLER GECTI (%d)" % len(testler))

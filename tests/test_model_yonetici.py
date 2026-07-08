# -*- coding: utf-8 -*-
"""
detection/model_yonetici.py sim'siz birim testleri (ultralytics/GPU GEREKMEZ).
Calistirma:  python test/test_model_yonetici.py
Kapsam: registry tarama (gercek models/ .pt'leri), yaml okuma, metrik penceresi,
kpt_shape kapisi karari (sahte dedektor), swap sonrasi metrik reset.
"""
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from detection import model_yonetici as my


def test_registry_tarar_gercek_modelleri():
    yon = my.ModelYonetici()
    adlar = [k["ad"] for k in yon.modelleri_listele()]
    assert len(adlar) >= 1, "models/ altinda .pt bekleniyor"
    # pose modeli kayitli (yolo26m_pose_best); henuz yuklenmedi -> task None
    assert any("pose" in a.lower() for a in adlar), adlar
    for k in yon.modelleri_listele():
        assert k["boyut_mb"] > 0 and "sema" in k


def test_yaml_okuma_minimal():
    import tempfile
    icerik = "imgsz: 960\nconf: 0.3\nhalf: true\nsema: motor\naciklama: test model\n"
    fd, yol = tempfile.mkstemp(suffix=".yaml")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(icerik)
    cfg = my._yaml_oku(yol)
    os.remove(yol)
    assert cfg["imgsz"] == 960 and cfg["conf"] == 0.3
    assert cfg["half"] is True and cfg["sema"] == "motor"
    assert cfg["aciklama"] == "test model"


def test_metrik_penceresi():
    m = my.MetrikPenceresi()
    for i in range(10):
        m.ekle(5.0 + i * 0.1, [{"conf": 0.8, "cx": 1, "cy": 1}])
    o = m.ozet()
    assert o["ornek"] == 10
    assert 5.0 <= o["inference_ms_ort"] <= 6.5
    assert o["fps"] > 0 and o["tespit_ort"] == 1.0
    assert 0.79 <= o["conf_ort"] <= 0.81
    # pose ekleri: keypoints'li tespit
    m2 = my.MetrikPenceresi()
    kp = [[1, 2, 0.9], [3, 4, 0.8], [5, 6, 0.9], [7, 8, 0.7], [9, 10, 0.2], [11, 12, 0.1]]
    m2.ekle(6.0, [{"conf": 0.9, "keypoints": kp}])
    o2 = m2.ozet()
    assert o2["kp_gorunur_ort"] == 4.0          # 4 kp >=0.5
    assert o2["pnp_uygun_oran"] == 1.0          # >=4 -> PnP uygun


def test_kpt_shape_kapisi_karari():
    # _yukle_isi'nin kpt_shape kapisini sahte HedefDedektor ile test et
    yon = my.ModelYonetici()
    if not yon.kayitlar:
        return
    ad = list(yon.kayitlar.keys())[0]

    class SahteDed:
        def __init__(self, yol, conf=0.25, imgsz=640):
            self.hazir = True
            self.task = "pose"
            self.kpt_shape = (5, 3)             # YANLIS -> reddedilmeli
            self.conf = conf

        def tespit_hepsi(self, frame):
            return []

    # gorsel_tespit.HedefDedektor'u gecici sahtele
    import detection.gorsel_tespit as gt
    orij = gt.HedefDedektor
    gt.HedefDedektor = SahteDed
    try:
        ok = yon._yukle_isi(ad)
        assert ok is False
        assert yon._hata and "kpt_shape" in yon._hata
        assert yon.hazir is False               # aktif model degismedi (eski kaldi=None)
    finally:
        gt.HedefDedektor = orij


def test_swap_metrik_reset():
    yon = my.ModelYonetici()
    if not yon.kayitlar:
        return
    ad = list(yon.kayitlar.keys())[0]

    class SahteDed:
        hazir = True
        task = "detect"
        kpt_shape = None

        def __init__(self, *a, **k):
            self.conf = 0.25

        def tespit_hepsi(self, frame):
            return [{"conf": 0.7, "cx": 1, "cy": 1, "w": 2, "h": 2}]

    import detection.gorsel_tespit as gt
    orij = gt.HedefDedektor
    gt.HedefDedektor = SahteDed
    try:
        yon.metrik.ekle(9.9, [{"conf": 0.5}])   # eski metrik
        ok = yon._yukle_isi(ad)
        assert ok and yon.hazir and yon.aktif_ad() == ad
        assert yon.metrikler()["ornek"] == 0    # swap -> yeni pencere (segment)
        yon.tespit_hepsi("x")                    # sahte frame
        assert yon.metrikler()["ornek"] == 1
    finally:
        gt.HedefDedektor = orij


if __name__ == "__main__":
    for ad, fn in sorted(globals().items()):
        if ad.startswith("test_"):
            fn()
            print("OK  %s" % ad)
    print("TUM TESTLER GECTI")

# -*- coding: utf-8 -*-
"""
arac/egitim/ iskelet testleri (ultralytics/GPU/dataset GEREKMEZ).
Calistirma:  python test/test_egitim_iskeleti.py
Kapsam: dataset_dogrula sentetik data.yaml (temiz / flip_idx yok / kpt_shape
yanlis); pose_egit PLAN modu (egitim BASLATMAZ).
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "arac", "egitim"))
import dataset_dogrula as dd


def _yaz(icerik):
    fd, yol = tempfile.mkstemp(suffix=".yaml")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(icerik)
    return yol


def test_temiz_dataset_gecer():
    yol = _yaz(
        "train: /content/train/images\nval: /content/val/images\n"
        "kpt_shape: [6, 3]\nflip_idx: [0, 1, 3, 2, 5, 4]\nnames:\n  0: talon\n")
    ok = dd.dogrula(yol)
    os.remove(yol)
    assert ok is True                # kritik hata yok (Colab yollari sadece UYARI)


def test_flip_idx_yok_uyari_ama_gecer():
    yol = _yaz("train: /c/t\nval: /c/v\nkpt_shape: [6, 3]\nnames:\n  0: talon\n")
    ok = dd.dogrula(yol)             # flip_idx yok -> UYARI ama egitilebilir
    os.remove(yol)
    assert ok is True


def test_kpt_shape_yanlis_kritik():
    yol = _yaz("train: /c/t\nval: /c/v\nkpt_shape: [17, 3]\nnames:\n  0: talon\n")
    ok = dd.dogrula(yol)             # kpt_shape != [6,3] -> KRITIK
    os.remove(yol)
    assert ok is False


def test_split_yok_kritik():
    yol = _yaz("kpt_shape: [6, 3]\nflip_idx: [0,1,3,2,5,4]\nnames:\n  0: talon\n")
    ok = dd.dogrula(yol)             # train/val yok -> KRITIK
    os.remove(yol)
    assert ok is False


def test_pose_egit_plan_modu_egitmez():
    # pose_egit PLAN modunda (--calistir yok) ultralytics'e DOKUNMADAN plan yazar.
    import pose_egit
    yol = _yaz("train: /c/t\nval: /c/v\nkpt_shape: [6, 3]\nflip_idx: [0,1,3,2,5,4]\n"
               "names:\n  0: talon\n")
    argv = sys.argv
    sys.argv = ["pose_egit.py", "--data", yol, "--agirlik", "models/x.pt"]
    try:
        rc = pose_egit.main()        # --calistir YOK -> plan; ultralytics import edilmez
        assert rc == 0
    finally:
        sys.argv = argv
        os.remove(yol)


if __name__ == "__main__":
    for ad, fn in sorted(globals().items()):
        if ad.startswith("test_"):
            fn()
            print("OK  %s" % ad)
    print("TUM TESTLER GECTI")

# -*- coding: utf-8 -*-
"""
ETIKETLE testleri — truth->projeksiyon oto-etiket cekirdegi (pose/etiketle.py).
Sentetik geometri: ultralytics/GPU/dataset GEREKMEZ (cv2 yalniz uctan-uca smoke).

Calistirma:  python -m pytest tests/test_etiketle.py -q
"""
import os
import sys
import json
import math
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pose import geometri
from pose import etiketle as et

W, H = 1000, 1000
FX = (W / 2.0) / math.tan(math.radians(geometri.KAMERA_HFOV_DEG) / 2.0)


def _kare(dpos, drot, tpos, trot, **kw):
    """kare_etiketi'ni TILT=0 ile kosar (deterministik geometri), globali geri koyar."""
    eski = geometri.KAMERA_TILT_DEG
    geometri.KAMERA_TILT_DEG = 0.0
    try:
        return et.kare_etiketi(dpos, drot, tpos, trot, W, H, **kw)
    finally:
        geometri.KAMERA_TILT_DEG = eski


def test_wrap_ve_interp():
    assert abs(et.wrap180(190.0) - (-170.0)) < 1e-9
    assert abs(et.wrap180(-190.0) - 170.0) < 1e-9
    assert abs(et.aci_interp(350.0, 10.0, 0.5)) < 1e-6      # kisa yol 0'dan gecer


def test_kutu_onden_merkezde():
    # Hedef tam onde, ayni irtifa, duz: kutu merkezde, genislik ~ fx*kanat/D.
    durum, kutu, uvs = _kare((0, 0, 0), (0, 0, 0), (1000, 0, 0), (0, 0, 0))
    assert durum == "ok" and all(uv is not None for uv in uvs)
    x0, y0, x1, y1 = kutu
    cx, w = (x0 + x1) / 2.0, x1 - x0
    beklenen_w = FX * 171.8 / 1000.0 * (1 + 2 * 0.06)       # kanat + marj
    assert abs(cx - W / 2.0) < 3.0
    assert 0.8 * beklenen_w < w < 1.2 * beklenen_w


def test_yandan_daha_dar():
    # Yandan bakis: yatay iz govde boyu (~108.7cm) -> onden (kanat 171.8) daha dar.
    _, k_on, _ = _kare((0, 0, 0), (0, 0, 0), (1000, 0, 0), (0, 0, 0))
    _, k_yan, _ = _kare((0, 0, 0), (0, 0, 0), (1000, 0, 0), (0, 0, 90))
    assert (k_yan[2] - k_yan[0]) < (k_on[2] - k_on[0]) * 0.75


def test_arkadaki_hedef_elenir():
    durum, kutu, _ = _kare((0, 0, 0), (0, 0, 0), (-1000, 0, 0), (0, 0, 0))
    assert durum == "arkada" and kutu is None


def test_kadraj_disi_elenir():
    # Onde ama FOV disina dusen hedef (u > W): kirpilmis alan 0.
    durum, kutu, _ = _kare((0, 0, 0), (0, 0, 0), (2000, 4500, 0), (0, 0, 0))
    assert durum == "kadraj_disi" and kutu is None


def test_cok_kucuk_elenir():
    # 600 m: kanat izi ~0.7 px -> etiketlenmez (gurultu olur).
    durum, kutu, _ = _kare((0, 0, 0), (0, 0, 0), (60000, 0, 0), (0, 0, 0))
    assert durum == "cok_kucuk" and kutu is None


def test_rot_sec_heading_sentetik():
    # Telemetri yaw 180 ama hedef 0 yonune ucuyor (hizli) -> heading-sentetik.
    rot, kaynak = et.rot_sec((0, 0, 180), 0.0, 1500.0)
    assert kaynak == "heading" and abs(rot[2]) < 1e-6 and rot[0] == 0.0
    # Yavas hedef: heading anlamsiz -> telemetri korunur, 'dogrulanamadi'.
    rot, kaynak = et.rot_sec((0, 0, 180), 0.0, 50.0)
    assert kaynak == "dogrulanamadi" and rot[2] == 180
    # Uyumlu yaw -> 'tel'.
    rot, kaynak = et.rot_sec((0, 0, 10), 0.0, 1500.0)
    assert kaynak == "tel" and rot[2] == 10


def test_akis_interp_yaw_wrap():
    fd, yol = tempfile.mkstemp(suffix=".jsonl")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(json.dumps({"t": 0.0, "dp": [0, 0, 0], "dr": [0, 0, 350],
                            "tp": [100, 0, 0], "tr": [0, 0, 350], "cm": 0}) + "\n")
        f.write(json.dumps({"t": 1.0, "dp": [10, 0, 0], "dr": [0, 0, 10],
                            "tp": [110, 0, 0], "tr": [0, 0, 10], "cm": 0}) + "\n")
    try:
        akis = et.Akis(yol)
        dp, dr, tp, tr = akis.durum(0.5)
        assert abs(dp[0] - 5.0) < 1e-6 and abs(tp[0] - 105.0) < 1e-6
        assert abs(et.wrap180(dr[2])) < 1e-6                # 350->10 kisa yol: 0
        assert abs(et.wrap180(tr[2])) < 1e-6
        # sinir disi sorgular kenara oturur
        assert akis.durum(-5.0)[0][0] == 0 and akis.durum(5.0)[0][0] == 10
    finally:
        os.remove(yol)


def test_yolo_satirlari():
    s = et.yolo_satiri((100, 200, 300, 400), W, H)
    assert s.split() == ["0", "0.200000", "0.300000", "0.200000", "0.200000"]
    # pose satiri: kadraj disi kp -> "0 0 0"
    uvs = [(500.0, 500.0)] * 5 + [(-10.0, 20.0)]
    sp = et.yolo_pose_satiri((100, 200, 300, 400), uvs, W, H).split()
    assert len(sp) == 5 + 6 * 3
    assert sp[5:8] == ["0.500000", "0.500000", "2"] and sp[-3:] == ["0", "0", "0"]


def test_oturum_ucundan_uca(tmp_path):
    # Sahte oturum: 1 iyi kare + 1 kadraj disi + 1 bozulmali -> 1 etiket, 2 eleme.
    import cv2
    ot = str(tmp_path / "oturum_test")
    os.makedirs(ot)
    img = np.zeros((240, 320, 3), dtype=np.uint8)
    for i in (1, 2, 3):
        cv2.imwrite(os.path.join(ot, "kare_%06d.png" % i), img)
    ortak = {"W": 320, "H": 240, "drone_pos": [0, 0, 0], "drone_rot_rpy": [0, 0, 0],
             "drone_vel": [0, 0, 0], "target_pos_ham": [800, 0, 0],
             "target_speed_ham": 1500.0, "truth_target_speed": 1500.0,
             "truth_drone_pos": [0, 0, 0], "hedef_heading_deg": 0.0}
    satirlar = [
        dict(ortak, t=1.0, kare="kare_000001.png", corruption_mask=0,
             truth_target_pos=[800, 0, 0], target_rot_rpy=[0, 0, 0], mesafe_cm=800),
        dict(ortak, t=2.0, kare="kare_000002.png", corruption_mask=0,
             truth_target_pos=[800, 4500, 0], target_rot_rpy=[0, 0, 0], mesafe_cm=4570),
        dict(ortak, t=3.0, kare="kare_000003.png", corruption_mask=4,
             truth_target_pos=[800, 0, 0], target_rot_rpy=[0, 0, 0], mesafe_cm=800),
    ]
    with open(os.path.join(ot, "telemetri.jsonl"), "w", encoding="utf-8") as f:
        for s in satirlar:
            f.write(json.dumps(s) + "\n")

    assert et.main(["--oturum", ot]) == 0
    lbl = os.path.join(ot, "labels", "kare_000001.txt")
    assert os.path.exists(lbl)
    deger = open(lbl, encoding="utf-8").read().split()
    assert len(deger) == 5 and all(0.0 <= float(v) <= 1.0 for v in deger[1:])
    assert not os.path.exists(os.path.join(ot, "labels", "kare_000002.txt"))
    rapor = json.load(open(os.path.join(ot, "etiket_rapor.json"), encoding="utf-8"))
    assert rapor["n_etiket"] == 1
    assert rapor["elemeler"]["kadraj_disi"] == 1 and rapor["elemeler"]["bozulma"] == 1


if __name__ == "__main__":
    fns = [(n, f) for n, f in sorted(globals().items())
           if n.startswith("test_") and callable(f)]
    ok = 0
    for n, f in fns:
        if "tmp_path" in f.__code__.co_varnames[:f.__code__.co_argcount]:
            import pathlib
            with tempfile.TemporaryDirectory() as td:
                f(pathlib.Path(td))
        else:
            f()
        ok += 1
        print("[OK] %s" % n)
    print("%d/%d test gecti" % (ok, len(fns)))

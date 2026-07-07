# -*- coding: utf-8 -*-
"""
Dogrulama testleri (python -m pytest tests/ veya python tests/test_guidance.py).

M2: PNG, CV hedefini yakalar ve pure pursuit'ten kisa/esit yol ucar.
M3: PNG, donen (turning) hedefi esik alti iskayla yakalar.
M4: donen hedefte PNG, pursuit'ten belirgin kisa yol + kucuk iska uretir.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import make_config, SCENARIOS
from simulator import run_sim
from metrics import compute_metrics


def _run(scenario, guidance):
    return compute_metrics(run_sim(make_config(scenario), guidance))


def test_png_cv_hedefini_yakalar():
    m = _run("cv", "png")
    assert m["hit"], f"PNG duz ucan (CV) hedefi yakalayamadi: {m}"
    assert m["miss_distance"] < 0.5


def test_pursuit_cv_hedefini_yakalar():
    m = _run("cv", "pursuit")
    assert m["hit"], f"Pure pursuit CV hedefi yakalayamadi: {m}"


def test_png_yolu_pursuitten_kisa_veya_esit_cv():
    png, pp = _run("cv", "png"), _run("cv", "pursuit")
    assert png["hit"] and pp["hit"]
    # kucuk sayisal pay: %2
    assert png["path_length"] <= pp["path_length"] * 1.02, (
        f"PNG yolu ({png['path_length']:.1f} m) pursuit'ten "
        f"({pp['path_length']:.1f} m) uzun!"
    )


def test_png_donen_hedefi_yakalar():
    m = _run("turning", "png")
    assert m["hit"], f"PNG donen hedefi yakalayamadi: {m}"
    assert m["miss_distance"] < 0.5


def test_png_tum_senaryolarda_yakalar():
    for sc in SCENARIOS:
        m = _run(sc, "png")
        assert m["hit"], f"PNG '{sc}' senaryosunda yakalayamadi: {m}"


def test_donen_hedefte_png_belirgin_kisa_yol():
    png, pp = _run("turning", "png"), _run("turning", "pursuit")
    assert png["hit"]
    if pp["hit"]:
        assert png["path_length"] < pp["path_length"], (
            f"Donen hedefte PNG yolu ({png['path_length']:.1f} m) "
            f"pursuit'ten ({pp['path_length']:.1f} m) kisa degil!"
        )
        assert png["time_to_intercept"] <= pp["time_to_intercept"]
    # pursuit hic yakalayamadiysa PNG'nin ustunlugu zaten kanitli


if __name__ == "__main__":
    # pytest'siz calistirma
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"OK  {fn.__name__}")
    print(f"\n{len(fns)} test gecti.")

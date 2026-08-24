# -*- coding: utf-8 -*-
"""TESPIT GUVEN ESIGI (VIS_CONF_MIN) — 0.35 -> 0.25 kararini kilitler.

NEDEN: gorsel faz her devirde "kayip" ile kopuyordu (olculdu: 170 s'de
9 devir, 9'u da kayip). Kok sebep dedektor bosluklari.

OLCULDU (canli /api/tune ile DONUSUMLU, 4 tur x 60 s; hedef KADRAJ ICINDE):
    menzil     conf0.35  conf0.25
    <10 m         89%      93%
    10-20 m       53%      78%     <- devir bandi
    20-40 m       30%      40%
OLUMSUZ KONTROL (hedef kadraj DISINDA; her tespit yanlis pozitif):
    >75 deg      3.0%     2.1%     -> ARTMIYOR
SONUC (4 tur x 85 s): kesintisiz kilit 0.29 -> 0.55 s; 30 m ici ornek 202 -> 525.
"""
import os
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)


def _cfg():
    import importlib
    m = importlib.import_module("guidance.ana_kontrol")
    return m.Cfg


def test_esik_025():
    """Uretim esigi 0.25 olmali (env ile ezilebilir)."""
    if os.environ.get("AVCI_VIS_CONF"):
        return
    assert float(_cfg().VIS_CONF_MIN) == 0.25


def test_esik_predict_tabanini_ALTINA_INMEZ():
    """⚠ server.py predict esigi min(0.25, VIS_CONF_MIN).

    0.25'in ALTI ham cikarimda yeni tespit URETMEZ -- yalnizca zayif
    kutulari gudume acar. Bu yuzden 0.25 tabandir, daha asagisi anlamsiz.
    """
    assert float(_cfg().VIS_CONF_MIN) >= 0.25


def test_gerekce_KODA_ISLENDI():
    """Olcum kodda yazili olmali; yoksa biri geri alir ve sebebini bilemez."""
    yol = os.path.join(KOK, "guidance", "ana_kontrol.py")
    s = open(yol, encoding="utf-8").read()
    for parca in ("53%", "78%", "OLUMSUZ KONTROL", "kesintisiz kilit"):
        assert parca in s, "gerekce eksik: %s" % parca

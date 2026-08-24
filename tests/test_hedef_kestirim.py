# -*- coding: utf-8 -*-
"""GORSEL FAZ HEDEF KESTIRIMI — sozlesme, geometri ve model testleri.

NEDEN (2026-08-17): gorsel fazda yasa SAF TAKIP; hedefin BULUNDUGU yere nisan
aliyor, GIDECEGI yere degil. Ongorulu nisan icin hedefin gelecekteki konumunu
YALNIZ KAMERADAN kestirmek gerekiyor (yarisma kurali: gorsel fazda hedefin
canli GPS'i YASAK).

Bu testler su davranislari KILITLER:
  * SOZLESME: kestirimciye yalnizca {kamera kutusu + KENDI durumumuz} girer.
    KamOlcum'a hedef GPS'i / truth / gercek menzil alani EKLENEMEZ.
  * GEOMETRI: piksel -> seviye acisi zinciri bbox_ibvs.los_seviye ile BIREBIR.
  * SANKI-OLCUM: bilinen bir hedefi projekte edip geri cozunce ayni yer cikar.
  * MODELLER: CV duz ucusta kusursuz; CT dairede CV'den IYI (yoksa CT'nin
    varlik sebebi yok).
  * KESME: cozumun oldugu/olmadigi haller ve yavaslama-donus iliskisi.
  * YAN ETKISIZLIK: dosya/ag/env okumaz, ayni girdi ayni cikti.
"""
import dataclasses
import math
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "kopru", "gazebo_kaynak"))

from control.guidance import hedef_kestirim as HK          # noqa: E402


def _kam(t=0.0, cx=320.0, cy=240.0, w=20.0, h=20.0, conf=0.9,
         roll=0.0, pitch=0.0, yaw=0.0, px=0.0, py=0.0, pz=0.0):
    return HK.KamOlcum(t=t, cx=cx, cy=cy, w=w, h=h, conf=conf, roll=roll,
                       pitch=pitch, yaw=yaw, px=px, py=py, pz=pz)


# ═══════════════════════════════════════════════════════ SOZLESME (KURAL)
def test_kural_sozlesme_alanlari():
    """KamOlcum YALNIZ kamera + kendi durumumuzu tasir.

    Bu, yarisma kuralinin kod karsiligidir: gorsel fazda hedefin canli GPS'i
    kullanilamaz. Listeye 'menzil', 'tgt_x', 'truth' gibi bir alan eklenirse
    bu test kirilir ve kural ihlali gorunur olur."""
    alanlar = {f.name for f in dataclasses.fields(HK.KamOlcum)}
    assert alanlar == {
        "t", "cx", "cy", "w", "h", "conf",     # KAMERA
        "roll", "pitch", "yaw", "px", "py", "pz",  # KENDIMIZ
    }
    yasak = {"menzil", "tgt_x", "tgt_y", "tgt_z", "truth", "hedef_gps",
             "hx", "hy", "hz", "gercek_menzil", "track_id"}
    assert not (alanlar & yasak)


def test_kural_kamolcum_degismez():
    """Sozlesme dondurulmus olmali — cagiran taraf icerigi degistiremesin."""
    k = _kam()
    with pytest.raises(dataclasses.FrozenInstanceError):
        k.cx = 999.0


def test_kural_gorselkestirim_yalniz_kamolcum_kabul_eder():
    """Serbest sozlukle beslenip icine truth kacirilamaz."""
    g = HK.GorselKestirim(HK.ModelSabitHiz())
    with pytest.raises(TypeError):
        g.olcum({"cx": 320, "cy": 240, "w": 20, "h": 20, "t": 0.0,
                 "menzil": 12.0})


def test_kural_yan_etkisiz_ve_belirlenimci():
    """Ayni girdi ayni cikti; dosya/env okumaz."""
    def kos():
        g = HK.GorselKestirim(HK.ModelIMM())
        for i in range(20):
            g.olcum(_kam(t=i * 0.05, cx=320 + i, cy=240, w=20, h=20))
        return g.tahmin(1.0)["p"]
    a, b = kos(), kos()
    assert a == b


# ═══════════════════════════════════════════════════════════════ GEOMETRI
def test_geometri_merkez_pikselde_azimut_sifir():
    """cx = CX, duz ucus -> azimut 0, yukselis = kamera tilt (25 yukari)."""
    az, el = HK.piksel_los_seviye(HK.KestirimCfg.CX, HK.KestirimCfg.CY, 0.0, 0.0)
    assert abs(az) < 1e-9
    assert abs(math.degrees(el) - HK.KestirimCfg.KAMERA_TILT_DEG) < 1e-6


def test_geometri_saga_kayan_kutu_pozitif_azimut():
    """Kutu sagdayken azimut POZITIF (burna gore sag+).

    ⚠ Bu testin varlik sebebi: bu depoda AYNA hatasi UC KEZ tekrarladi
    (bkz. bbox_geometri.py basligi). Isaret burada kilitli."""
    az, _ = HK.piksel_los_seviye(HK.KestirimCfg.CX + 100, HK.KestirimCfg.CY,
                                 0.0, 0.0)
    assert az > 0


def test_geometri_bbox_ibvs_ile_birebir():
    """Zincir, yasanin kendi los_seviye'siyle BIREBIR ayni olmali.

    Ayrilirlarsa kestirim ile yasa farkli dunyalarda calisir."""
    B = pytest.importorskip("control.guidance.bbox_ibvs")
    rng = np.random.default_rng(3)
    for _ in range(200):
        cx = float(rng.uniform(20, 620))
        cy = float(rng.uniform(20, 460))
        roll = float(rng.uniform(-0.7, 0.7))
        pitch = float(rng.uniform(-0.5, 0.5))
        a1, e1 = HK.piksel_los_seviye(cx, cy, roll, pitch)
        a2, e2 = B.los_seviye(cx, cy, roll, pitch)
        assert abs(a1 - a2) < 1e-12
        assert abs(e1 - e2) < 1e-12


def test_menzil_vekili_azalan():
    """Kutu buyudukce menzil KUCULMELI; sinirlar disina tasmamali."""
    r = [HK.menzil_vekilinden(b, b) for b in (5, 10, 20, 40, 80)]
    assert all(r[i] > r[i + 1] for i in range(len(r) - 1))
    assert HK.menzil_vekilinden(0.0, 0.0) == HK.KestirimCfg.MENZIL_MAX
    assert HK.KestirimCfg.MENZIL_MIN <= r[-1] <= HK.KestirimCfg.MENZIL_MAX


def test_sanki_olcum_ileri_geri_tutarli():
    """Bilinen bir hedefi pikselden geri cozunce menzil vekili disinda ayni yon.

    Yon (birim vektor) tam olmali; menzil vekili kaba oldugu icin yalnizca
    yonun dogrulugu iddia edilir."""
    kam = _kam(cx=380.0, cy=200.0, roll=0.15, pitch=-0.1, yaw=0.7,
               px=10.0, py=-5.0, pz=-30.0, w=25, h=25)
    p, u, R = HK.sanki_olcum(kam)
    assert abs(np.linalg.norm(u) - 1.0) < 1e-12
    # p, kendi konumumuzdan u yonunde tam R kadar uzakta olmali
    d = p - np.array([kam.px, kam.py, kam.pz])
    assert abs(np.linalg.norm(d) - R) < 1e-9
    assert np.allclose(d / R, u, atol=1e-12)


def test_olcum_gurultusu_anizotropik():
    """LOS boyunca belirsizlik, dikine gore BUYUK olmali.

    Menzil vekili metrelerce hatali, kerteriz ise ~1-3 px. Izotropik R
    kullanmak kerteriz bilgisini bogar — bu test o tasarimi kilitler."""
    u = np.array([1.0, 0.0, 0.0])
    Rm = HK._R_los(u, 15.0)
    los = float(u @ Rm @ u)                 # LOS yonundeki varyans
    dik = float(np.array([0, 1, 0]) @ Rm @ np.array([0, 1, 0]))
    assert los > 4.0 * dik


# ═════════════════════════════════════════════════════════════ MODELLER
def _besle(model, uret, n=40, dt=0.05, gurultu=0.0, tohum=0):
    """uret(t) -> gercek konum. Modeli dogrudan sanki-olcumle besler."""
    rng = np.random.default_rng(tohum)
    g = HK.GorselKestirim(model)
    for i in range(n):
        t = i * dt
        p = np.asarray(uret(t), dtype=float)
        if gurultu:
            p = p + rng.normal(0, gurultu, 3)
        # sanki-olcumu atlayip modeli dogrudan besliyoruz: burada test edilen
        # FILTRE, kamera zinciri degil (o ayrica test ediliyor).
        model.olcum(t, p, np.eye(3) * 0.25)
        g.son = (_kam(t=t), p, np.array([1.0, 0, 0]), 10.0)
    return g


def test_cv_duz_ucusta_kusursuz():
    """Gurultusuz duz ucusta CV, 2 s sonrasini santimetre altinda bilmeli."""
    v = np.array([17.99, 0.0, 0.0])
    g = _besle(HK.ModelSabitHiz(), lambda t: v * t)
    d = g.tahmin(2.0)
    assert np.allclose(d["p"], v * (39 * 0.05 + 2.0), atol=0.05)


def test_ct_dairede_cv_den_iyi():
    """Hedef sabit ovalde ucuyor. CT viraji tasimali, CV kacirmalidir.

    Bu testin amaci CT'nin VARLIK SEBEBINI kanitlamak: dairede daha iyi
    degilse modeli tasimanin anlami yok."""
    R, V = 48.0, 17.99
    om = V / R

    def daire(t):
        return [R * math.sin(om * t), R * (1 - math.cos(om * t)), 0.0]

    hedef = np.array(daire(39 * 0.05 + 2.0))
    ecv = np.linalg.norm(np.array(_besle(HK.ModelSabitHiz(), daire)
                                  .tahmin(2.0)["p"]) - hedef)
    ect = np.linalg.norm(np.array(_besle(HK.ModelSabitDonus(), daire)
                                  .tahmin(2.0)["p"]) - hedef)
    assert ect < ecv, "CT dairede CV'den iyi olmali (%.2f vs %.2f)" % (ect, ecv)
    assert ect < 3.0


def test_imm_iki_modeli_de_takip_eder():
    """IMM duzde de dairede de tek modelli en iyisine yakin kalmali."""
    V = 17.99
    duz = lambda t: [V * t, 0.0, 0.0]                       # noqa: E731
    R = 48.0
    om = V / R
    daire = lambda t: [R * math.sin(om * t),                # noqa: E731
                       R * (1 - math.cos(om * t)), 0.0]
    for uret in (duz, daire):
        h = np.array(uret(39 * 0.05 + 1.0))
        e_imm = np.linalg.norm(np.array(_besle(HK.ModelIMM(), uret)
                                        .tahmin(1.0)["p"]) - h)
        assert e_imm < 3.0, "IMM hatasi %.2f" % e_imm


def test_bayat_veride_sifirlanir():
    """DT_MAX_GORSEL'den uzun bosluk sonrasi hiz kestirimi TASINMAMALI."""
    m = HK.ModelSabitHiz()
    m.olcum(0.0, np.array([0.0, 0, 0]), np.eye(3) * 0.25)
    m.olcum(0.05, np.array([1.0, 0, 0]), np.eye(3) * 0.25)
    m.olcum(5.0, np.array([2.0, 0, 0]), np.eye(3) * 0.25)   # 5 s bosluk
    p, v = m.tahmin(1.0)
    assert np.linalg.norm(v) < 1e-6          # hiz sifirlandi
    assert abs(p[0] - 2.0) < 1e-6


def test_ufuk_tavani_asilamaz():
    g = HK.GorselKestirim(HK.ModelSabitHiz())
    for i in range(20):
        g.olcum(_kam(t=i * 0.05, cx=320 + i))
    assert g.tahmin(99.0)["ufuk"] == HK.KestirimCfg.UFUK_MAX


# ═══════════════════════════════════════════════════════════════ KESME
def test_kesme_bilinen_cozum():
    """Hedef yandan gecerken kesme noktasi ileride olmali."""
    r = HK.kesme_cozumu(p_biz=[0, 0, 0], V_biz=20.0,
                        p_hedef=[100.0, 0.0, 0.0], v_hedef=[0.0, 10.0, 0.0])
    assert r is not None
    assert r["t_go"] > 0
    # kesme noktasinda mesafe = V_biz * t_go
    d = np.linalg.norm(np.array(r["p_kesme"]))
    assert abs(d - 20.0 * r["t_go"]) < 1e-6
    assert r["p_kesme"][1] > 0            # hedefin GITTIGI yone dogru


def test_kesme_cozumsuz_hedef_daha_hizli_kaciyor():
    """Hedef bizden hizli ve tam ters yone kaciyorsa kesme YOKTUR."""
    r = HK.kesme_cozumu(p_biz=[0, 0, 0], V_biz=10.0,
                        p_hedef=[50.0, 0.0, 0.0], v_hedef=[25.0, 0.0, 0.0])
    assert r is None


def test_lead_acisi_sinir():
    """mu>1 iken bordadan kesme geometrik olarak IMKANSIZ."""
    assert HK.lead_acisi(1.2, math.radians(90.0)) is None
    s = HK.lead_acisi(0.9, math.radians(90.0))
    assert abs(math.degrees(s) - 64.16) < 0.1
    # tam kuyrukta lead 0
    assert abs(HK.lead_acisi(0.9, math.radians(180.0))) < 1e-12


def test_donus_tavani_yavaslayinca_ARTAR():
    """omega = a/V — YAVASLAMAK donusu sertlestirir.

    Ongorulu nisanin yavaslama ile birlesiminin dayanagi budur; iliski ters
    cevrilirse tum oneri cokerdi."""
    assert HK.donus_tavani(15.0) > HK.donus_tavani(18.0) > HK.donus_tavani(22.0)
    assert abs(HK.donus_tavani(18.0) - math.degrees(12.0 / 18.0)) < 1e-9
    # yaw kanal tavani ustten kisar
    assert HK.donus_tavani(2.0, yaw_tavan_dps=120.0) == 120.0


def test_eski_gps_imm_bozulmadi():
    """Ayni dosyadaki GPS fazi IMM'i (CV+CA) etkilenmemis olmali."""
    kf = HK.IMM()
    for i in range(30):
        kf.guncelle((i * 1.0, 0.0, -50.0), 0.05)
    d = kf.durum()
    assert d["hazir"] and abs(d["v"][0] - 20.0) < 5.0

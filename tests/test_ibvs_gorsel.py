# -*- coding: utf-8 -*-
"""
BASIT IBVS dogrulama (oyunsuz): goruntu merkezi -> bbox merkezi cizgisi.

Test edilenler:
  1) Yon eslemesi: hedef SAGDA -> yaw>0; SOLDA -> yaw<0; YUKARIDA -> thr>0
     (tirman); ASAGIDA -> thr<0; MERKEZDE -> yaw~0, thr~0, ileri TAM.
  2) Merkez freni: cizgi buyudukce ileri itki kisilir.
  3) Aci/buyukluk aritmetigi: sag=0, yukari=+90, asagi=-90.
  4) Clamp'ler: |yaw| <= YAW_MAX, thr THR_DN..THR_UP; roll HEP 0.
  5) EMA: tek-kare sicrama yumusatilir (ilk kare aynen alinir).
  6) GPS'siz imza: hesapla yalniz (det, p) alir — konum/hiz/rotasyon parametresi
     YOK -> "gorsel fazda GPS yasak" yarisma kurali YAPISAL olarak saglanir.

Calistirma:  python tests/test_ibvs_gorsel.py     (pytest de calisir)
"""
import inspect
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from guidance.ibvs_gorsel import AvciIBVS
from guidance.ana_kontrol import Cfg

# CEKIRDEK YASA testleri yumusak-gecis rampasini KAPALI test eder (ilk tik = tam yasa
# ciktisi; rampa yoksa s=1). Rampa davranisi AYRI olarak test_handoff_* ile dogrulanir.
# (Rampa acikken ilk tik s=0 -> ileri=0/nisan=merkez oldugundan cekirdek geometri testleri
# rampayi izole etmek icin kapatir; bu modul-duzeyi ayar tum test surecini etkiler.)
Cfg.IBVS_HANDOFF_S = 0.0

W, H = 1920.0, 1080.0


def _det(cxn=0.5, cyn=0.5, wp=0.08, hp=0.04, t=0.0):
    return {"cx": cxn * W, "cy": cyn * H, "w": wp * W, "h": hp * H,
            "conf": 0.9, "cls": 0, "W": W, "H": H, "t": t}


class _Cfg0:
    """Cfg kopyasi ama IBVS_DIKEY_NISAN=0 (dikey nisan=merkez) -> cekirdek cizgi-geometrisini
    tilt-aim ozelliginden yalitir (ey_ref=0 -> eski merkez-tabanli davranis)."""
    def __getattr__(self, k):
        return 0.0 if k == "IBVS_DIKEY_NISAN" else getattr(Cfg, k)


CFG0 = _Cfg0()


def _ey_ref(p=Cfg):
    return (float(p.IBVS_DIKEY_NISAN) * math.tan(math.radians(float(p.IBVS_TILT_DEG)))
            / math.tan(math.radians(float(p.IBVS_VFOV_HALF_DEG))))


def _tek(cxn, cyn, p=CFG0, wp=0.08, hp=0.04):
    """Tek kare besle (ilk kare EMA'siz). Varsayilan CFG0 (nisan=merkez) -> cekirdek yasa.
    wp/hp: bbox oranlari — KILIT-TUT boyut yasasini etkiler (kucuk=uzak=istek doygun)."""
    return AvciIBVS().hesapla(_det(cxn=cxn, cyn=cyn, wp=wp, hp=hp), p)


class _CfgVar:
    """Cfg kopyasi + secilen alanlar override (negatif-nisan / alcalma-freni testleri)."""
    def __init__(self, **kw):
        self._kw = kw

    def __getattr__(self, k):
        if k == "_kw":
            raise AttributeError(k)
        return self._kw[k] if k in self._kw else getattr(Cfg, k)


def test_yon_eslemesi():
    # CFG0 (nisan=merkez): cekirdek yon eslemesi (ey_ref=0 -> merkez setpoint)
    thr, _, _, yaw = _tek(0.75, 0.5)             # hedef SAGDA
    assert yaw > 0 and abs(thr) < 1e-9, "sagda: yaw>0 thr=0 bekleniyordu"
    _, _, _, yaw = _tek(0.25, 0.5)               # SOLDA
    assert yaw < 0
    thr, _, _, yaw = _tek(0.5, 0.25)             # YUKARIDA
    assert thr > 0 and abs(yaw) < 1e-9, "yukarida: thr>0 (tirman) bekleniyordu"
    thr, _, _, _ = _tek(0.5, 0.75)               # ASAGIDA
    assert thr < 0, "asagida: thr<0 (alcal) bekleniyordu"


def test_nisanda_tam_ileri():
    """UZAK hedef NISAN noktasinda (ex=0, ey=ey_ref) -> yaw~0, thr~0, tam ileri TAVAN
    (r=0; kucuk bbox -> boyut istegi doygun -> pitch = ILERI)."""
    ey_ref = _ey_ref(Cfg)
    cyn = 0.5 + ey_ref / 2.0                       # ey = ey_ref
    thr, pitch, roll, yaw = _tek(0.5, cyn, p=Cfg, wp=0.02, hp=0.01)
    assert abs(yaw) < 1e-9 and abs(thr) < 2e-3, "nisan noktasinda yaw~0 thr~0"
    assert abs(pitch - Cfg.PITCH_SIGN * Cfg.IBVS_ILERI) < 1e-6, "uzakta ileri itki TAVAN (kisma=1)"


def test_dikey_nisan_tilt_farkinda():
    """ey_ref = NISAN*tan(TILT)/tan(VFOV_yari) (~0.43 @25 ve NISAN=1); nisan ustunde tirman,
    altinda alcal. NISAN default'u tune ile degisir (8 Tem: 0.1) -> mekanizma NISAN=1'de denenir."""
    eski = Cfg.IBVS_DIKEY_NISAN
    Cfg.IBVS_DIKEY_NISAN = 1.0
    try:
        ey_ref = _ey_ref(Cfg)
        assert 0.35 < ey_ref < 0.55, "tilt=25 icin ey_ref ~0.43 bekleniyordu: %.3f" % ey_ref
        g = AvciIBVS(); g.hesapla(_det(cxn=0.5, cyn=0.5 + ey_ref / 2.0), Cfg)
        assert abs(g.durum()["ey_ref"] - round(ey_ref, 3)) < 1e-3
        # nisanin USTUNDE (ey<ey_ref): tirman (thr>0); ALTINDA (ey>ey_ref): alcal (thr<0)
        thr_ust = _tek(0.5, 0.5, p=Cfg)[0]             # ey=0 < ey_ref -> tirman
        thr_alt = _tek(0.5, 0.95, p=Cfg)[0]            # ey=0.9 > ey_ref -> alcal
        assert thr_ust > 0 and thr_alt < 0, "nisan ustu tirman / alti alcal (thr %.2f/%.2f)" % (thr_ust, thr_alt)
    finally:
        Cfg.IBVS_DIKEY_NISAN = eski


def test_negatif_nisan_altta_kal():
    """ALTTAN VURUS onermesi: NISAN=-0.25 -> ey_ref<0 (hedef merkez USTUNDE tutulur).
    Hedef MERKEZDE gorunuyorsa (ey=0) 'fazla yuksektesin' demektir -> thr<0 (ALCAL)."""
    p = _CfgVar(IBVS_DIKEY_NISAN=-0.25)
    g = AvciIBVS()
    thr, _, _, yaw = g.hesapla(_det(cxn=0.5, cyn=0.5), p)
    d = g.durum()
    assert d["ey_ref"] < 0, "negatif nisanda ey_ref<0 bekleniyordu: %s" % d["ey_ref"]
    assert thr < 0, "merkezdeki hedef = fazla yuksek -> alcal (thr<0), gelen: %.3f" % thr
    assert abs(yaw) < 1e-9
    # hedef tam nisan noktasindaysa (merkezin USTUNDE) thr~0 (denge alttan-takipte)
    cyn = 0.5 + d["ey_ref"] / 2.0
    thr2, _, _, _ = AvciIBVS().hesapla(_det(cxn=0.5, cyn=cyn), p)
    assert abs(thr2) < 2e-3, "nisan noktasinda thr~0 bekleniyordu: %.3f" % thr2


def test_nisan_clamp_negatif():
    """Asiri negatif NISAN koddaki -1.0 tabanina oturur (guvenlik siniri)."""
    g = AvciIBVS()
    g.hesapla(_det(), _CfgVar(IBVS_DIKEY_NISAN=-5.0))
    beklenen = -1.0 * math.tan(math.radians(float(Cfg.IBVS_TILT_DEG))) \
        / math.tan(math.radians(float(Cfg.IBVS_VFOV_HALF_DEG)))
    assert abs(g.durum()["ey_ref"] - round(beklenen, 3)) < 1e-3, g.durum()["ey_ref"]


# Alcalma freni artik YALNIZ kilit-tut bandinda (yak<1, boyut hedefe yakin) ileri
# itkiyi kisar; UZAKTA (yak=1) frenler baypas (yaklasma-agirlikli fren, 2026-07-08).
# Bu yardimci kilit-tut bandi kurar: hedef=0.10, K=10, ILERI=1.0, wp=0.09 -> istek=0.1,
# yak=0.1 -> frenler ~tam devrede; MERKEZ_FREN=0 ile alcal izole.
def _band(**kw):
    d = dict(IBVS_DIKEY_NISAN=0.0, IBVS_MERKEZ_FREN=0.0, IBVS_BOYUT_HEDEF=0.10,
             IBVS_K_BOYUT=10.0, IBVS_ILERI=1.0)
    d.update(kw)
    return _CfgVar(**d)


def test_alcalma_freni_ustteyken_ileriyi_kisar():
    """KILIT-TUT bandinda hedef nisanin ALTINDA (eyy>0 = fazla yuksekteyiz) -> ileri
    itki alcal ile kisilir (lift carry kirilir), thr<0. Duz referansa gore kuculur."""
    p = _band(IBVS_ALCAL_FREN=2.0)
    g0 = AvciIBVS(); _, p0, _, _ = g0.hesapla(_det(cxn=0.5, cyn=0.5, wp=0.09, hp=0.09), p)   # eyy=0
    g1 = AvciIBVS(); thr, p1, _, _ = g1.hesapla(_det(cxn=0.5, cyn=0.65, wp=0.09, hp=0.09), p)  # eyy=+0.3
    assert p1 < p0, "alcal kilit-tut bandinda ileriyi kismali: %.3f vs %.3f" % (p1, p0)
    assert thr < 0
    assert abs(g1.durum()["alcal"] - 0.4) < 1e-3
    # fren buyudukce pitch kuculur (ayni sapma, daha sert fren)
    g2 = AvciIBVS(); _, p2, _, _ = g2.hesapla(_det(cxn=0.5, cyn=0.65, wp=0.09, hp=0.09),
                                              _band(IBVS_ALCAL_FREN=3.0))
    assert p2 < p1


def test_alcalma_freni_tirmanista_dokunmaz():
    """Hedef nisanin USTUNDE (eyy<0 = alttayiz, tirman) -> alcal=1 (yak'tan bagimsiz)."""
    p = _band(IBVS_ALCAL_FREN=2.0)
    g = AvciIBVS()
    thr, pitch, _, _ = g.hesapla(_det(cxn=0.5, cyn=0.35, wp=0.09, hp=0.09), p)  # eyy=-0.3
    assert g.durum()["alcal"] == 1.0, "tirmanista alcal=1 bekleniyordu"
    assert thr > 0


def test_alcalma_taban():
    """Buyuk sapmada ham fren TABANA oturur (asla tam durma; biraz kapanis kalir)."""
    p = _band(IBVS_ALCAL_FREN=2.0)
    g = AvciIBVS()
    _, pitch, _, _ = g.hesapla(_det(cxn=0.5, cyn=0.95, wp=0.09, hp=0.09), p)  # eyy=+0.9
    assert abs(g.durum()["alcal"] - float(Cfg.IBVS_ALCAL_TABAN)) < 1e-6
    assert abs(pitch) > 0, "tabanda bile ileri itki tam SIFIRLANMAZ"


def test_yaklasmada_fren_baypas():
    """KOK-NEDEN (gorsel fazda hizlanamiyor): UZAK hedef (yak=1) kenarda+yuksekte
    OLSA BILE frenler baypas -> tam ileri TAVAN. Eskiden kisma*alcal bunu ~0.05'e
    eziyordu; artik uzakta mesafe kapatilir."""
    p = _CfgVar(IBVS_DIKEY_NISAN=0.0, IBVS_MERKEZ_FREN=1.4, IBVS_ALCAL_FREN=2.0)
    g = AvciIBVS()
    _, pitch, _, _ = g.hesapla(_det(cxn=0.9, cyn=0.9, wp=0.02, hp=0.01), p)  # uzak+kenar+yuksek
    assert abs(pitch - Cfg.PITCH_SIGN * Cfg.IBVS_ILERI) < 1e-6, \
        "uzakta fren baypas -> tam TAVAN bekleniyordu: %.3f" % pitch
    assert g.durum()["yak"] == 1.0


# ---------------------------------------------------------------------------
#  KILIT-TUT: boyut-reguleli ileri itki (Faz 2, sartname 6.1.2/6.1.4)
# ---------------------------------------------------------------------------
def test_boyut_uzakta_tavan():
    """Uzak hedef (boyut %2) -> istek doygun -> pitch = ILERI TAVAN (eski yaklasma hizi)."""
    g = AvciIBVS()
    _, pitch, _, _ = g.hesapla(_det(cxn=0.5, cyn=0.5, wp=0.02, hp=0.01), CFG0)
    assert abs(pitch - Cfg.PITCH_SIGN * Cfg.IBVS_ILERI) < 1e-6
    assert g.durum()["ileri_istek"] == round(float(Cfg.IBVS_ILERI), 3), "istek tavanda olmali"


def test_boyut_hedefte_dur():
    """boyut == BOYUT_HEDEF -> ileri istek 0 (istasyon tut; hata sifir)."""
    p = _CfgVar(IBVS_DIKEY_NISAN=0.0, IBVS_BOYUT_HEDEF=0.08)
    g = AvciIBVS()
    _, pitch, _, _ = g.hesapla(_det(cxn=0.5, cyn=0.5, wp=0.08, hp=0.04), p)
    assert abs(pitch) < 1e-9, "hedef boyutta pitch=0 bekleniyordu: %.4f" % pitch
    assert g.durum()["boyut"] == 0.08


def test_boyut_fazla_yakin_geri_tavanli():
    """boyut >> hedef -> GERI itki (kacis), tavani GERI_MAX; kenarda/yuksekte bile
    AYNI geri (kisma/alcal GERI'yi FRENLEMEZ — kacis manevrasi); GERI_MAX=0 -> geri yok."""
    p = _CfgVar(IBVS_DIKEY_NISAN=0.0)
    g = AvciIBVS()
    _, pitch, _, _ = g.hesapla(_det(cxn=0.5, cyn=0.5, wp=0.30, hp=0.15), p)
    assert abs(pitch - (-Cfg.PITCH_SIGN * Cfg.IBVS_GERI_MAX)) < 1e-6, \
        "geri kacis -GERI_MAX bekleniyordu: %.3f" % pitch
    # kenarda + fazla yuksekte (kisma~0, alcal<1) -> geri AYNI kalmali
    g2 = AvciIBVS()
    _, pitch2, _, _ = g2.hesapla(_det(cxn=0.95, cyn=0.95, wp=0.30, hp=0.15), p)
    assert abs(pitch2 - pitch) < 1e-6, "geri komut frenlenmemeli: %.3f vs %.3f" % (pitch2, pitch)
    # geri kapatilabilir
    g3 = AvciIBVS()
    _, pitch3, _, _ = g3.hesapla(_det(cxn=0.5, cyn=0.5, wp=0.30, hp=0.15),
                                 _CfgVar(IBVS_DIKEY_NISAN=0.0, IBVS_GERI_MAX=0.0))
    assert pitch3 == 0.0, "GERI_MAX=0 -> asla geri: %.3f" % pitch3


def test_boyut_k0_eski_sabit_ileri():
    """IBVS_K_BOYUT=0 -> regulasyon KAPALI: dev bbox'ta bile eski sabit-ileri yasa."""
    p = _CfgVar(IBVS_DIKEY_NISAN=0.0, IBVS_K_BOYUT=0.0)
    g = AvciIBVS()
    _, pitch, _, _ = g.hesapla(_det(cxn=0.5, cyn=0.5, wp=0.30, hp=0.15), p)
    assert abs(pitch - Cfg.PITCH_SIGN * Cfg.IBVS_ILERI) < 1e-6, "K=0 eski yasa: %.3f" % pitch


def test_boyut_ema_ve_sifirla():
    """boyut ex/ey ile ayni EMA'dan gecer; sifirla() taze baslatir."""
    p = _CfgVar(IBVS_DIKEY_NISAN=0.0)
    g = AvciIBVS()
    g.hesapla(_det(wp=0.02, hp=0.01), p)
    assert g.boyut_f == 0.02, "ilk kare EMA'siz alinmali"
    g.hesapla(_det(wp=0.10, hp=0.05), p)
    assert 0.02 < g.boyut_f < 0.10, "ikinci kare EMA'li olmali: %.3f" % g.boyut_f
    g.sifirla()
    assert g.boyut_f == 0.0


def test_boyut_telemetri():
    """durum() kilit-tut alanlarini tasir: boyut / boyut_hedef / ileri_istek."""
    g = AvciIBVS()
    g.hesapla(_det(wp=0.08, hp=0.04), Cfg)
    d = g.durum()
    assert d["boyut"] == 0.08 and d["boyut_hedef"] == round(float(Cfg.IBVS_BOYUT_HEDEF), 3)
    assert "ileri_istek" in d


def test_ego_pitch_telafi():
    """KACAK-TIRMANMA senaryosu (8 Tem log 204331): drone hedefin ALTINDA, govde one
    yatiyor (burun asagi -20 derece) -> hedef goruntude sahte YUKARI ziplar (ey=-0.2).
    Telafisiz yasa TIRMAN derdi; ego-pitch telafisi gercek bakis-hattini geri kurar
    -> thr artik pozitife sapmamali (alcal/notr). GAIN=0 ile eski davranis kiyasi."""
    det = _det(cxn=0.5, cyn=0.40)                    # ey = -0.2 (sahte 'yukarida')
    p0 = _CfgVar(IBVS_DIKEY_NISAN=0.0, IBVS_EGO_PITCH_GAIN=0.0)
    thr0, _, _, _ = AvciIBVS().hesapla(_det(cxn=0.5, cyn=0.40), p0,
                                       own_pitch_rad=math.radians(-20.0))
    assert thr0 > 0, "GAIN=0 (telafisiz): sahte 'yukarida' -> tirman beklenirdi (kok neden)"
    p1 = _CfgVar(IBVS_DIKEY_NISAN=0.0, IBVS_EGO_PITCH_GAIN=1.0)
    g = AvciIBVS()
    thr1, _, _, _ = g.hesapla(det, p1, own_pitch_rad=math.radians(-20.0))
    # tan(-20)/tan(47.2) ~ -0.337 -> ey_kul = -0.2 + 0.337 = +0.137 -> ALCAL (thr<0)
    assert thr1 < 0, "telafili yasa tirmanmamali (thr=%.3f)" % thr1
    assert abs(g.durum()["ey_ego"] - (-0.2 + math.tan(math.radians(20.0))
                                      / math.tan(math.radians(47.2)))) < 5e-3
    # govde duz ise telafi no-op (ey_ego == ey)
    g2 = AvciIBVS()
    g2.hesapla(_det(cxn=0.5, cyn=0.40), p1, own_pitch_rad=0.0)
    assert abs(g2.durum()["ey_ego"] - (-0.2)) < 1e-6


def test_ego_pitch_yokken_eski_davranis():
    """own_pitch_rad verilmezse (None) yasa bit-bit eski haliyle calisir."""
    p = _CfgVar(IBVS_DIKEY_NISAN=0.0)
    k1 = AvciIBVS().hesapla(_det(cxn=0.6, cyn=0.4), p)
    k2 = AvciIBVS().hesapla(_det(cxn=0.6, cyn=0.4), p, own_pitch_rad=None)
    assert k1 == k2


def test_merkez_freni_ileriyi_kisar():
    # KILIT-TUT bandinda (yak<1) merkez freni etkili: sapma buyudukce ileri kisilir.
    # (Uzakta yak=1 -> fren baypas oldugundan bandi _band ile kurariz; MERKEZ_FREN acik.)
    p = _band(IBVS_MERKEZ_FREN=1.4)
    p_merkez = abs(AvciIBVS().hesapla(_det(cxn=0.5, cyn=0.5, wp=0.09, hp=0.09), p)[1])
    p_kenar = abs(AvciIBVS().hesapla(_det(cxn=0.98, cyn=0.5, wp=0.09, hp=0.09), p)[1])
    assert p_kenar < p_merkez, "sapma buyuyunce ileri itki kisilmali"


def test_aci_ve_buyukluk():
    # CFG0 (nisan=merkez): cizgi geometrisi merkeze gore
    g = AvciIBVS(); g.hesapla(_det(cxn=0.75, cyn=0.5), CFG0)
    d = g.durum()
    assert abs(d["aci_deg"] - 0.0) < 1e-6, "sag = 0 derece"
    assert abs(d["buyukluk"] - 0.5) < 1e-6
    g = AvciIBVS(); g.hesapla(_det(cxn=0.5, cyn=0.25), CFG0)
    assert abs(g.durum()["aci_deg"] - 90.0) < 1e-6, "yukari = +90 derece"
    g = AvciIBVS(); g.hesapla(_det(cxn=0.5, cyn=0.75), CFG0)
    assert abs(g.durum()["aci_deg"] + 90.0) < 1e-6, "asagi = -90 derece"


def test_clamp_ve_roll_sifir():
    thr, _, roll, yaw = _tek(1.0, 0.0)           # sag-ust kose (asiri sapma)
    assert abs(yaw) <= Cfg.YAW_MAX + 1e-9, "yaw YAW_MAX'i asmamali"
    assert Cfg.THR_DN - 1e-9 <= thr <= Cfg.THR_UP + 1e-9
    assert roll == 0.0, "roll HEP 0 (bank yok)"
    thr2 = _tek(0.5, 1.0)[0]                     # tam alt kenar
    assert thr2 >= Cfg.THR_DN - 1e-9


def test_ema_yumusatma():
    g = AvciIBVS()
    g.hesapla(_det(cxn=0.5, cyn=0.5, t=0.0), Cfg)    # merkez (ilk kare)
    g.hesapla(_det(cxn=0.9, cyn=0.5, t=0.1), Cfg)    # ani sicrama (ex=0.8)
    assert 0.0 < g.ex_f < 0.8, "EMA sicramayi yumusatmali (tam 0.8'e atlamamali)"


def test_gps_siz_imza():
    """hesapla girdileri: det (bbox px) + p (Cfg) + poz (kamera keypoint) + own_roll_rad/
    own_pitch_rad (KENDI IMU'muz, ego-motion telafileri). Hedef YONU %100 kameradan;
    own_roll/pitch yalniz gorsel OLCUMU temizler (hedefi konumlamaz). YASAK olan HEDEF
    GPS/J kestirimidir (son_temiz/son_hiz/...) ve genel kinematik dump (drone_pos/v_own/rot)."""
    params = list(inspect.signature(AvciIBVS.hesapla).parameters)
    assert set(params) <= {"self", "det", "p", "poz", "own_roll_rad", "own_pitch_rad"}, \
        "beklenmedik parametre: %s" % params
    yasak = {"drone_pos", "v_own", "v_own_xy", "rot", "rot_rpy", "drone_rot_rpy",
             "yaw_rad", "drone_z", "son_temiz", "son_hiz", "son_xy_anlik", "son_z_anlik"}
    sizan = set(params) & yasak
    assert not sizan, "GPS/J hedef-kestirimi ya da kinematik dump imzaya sizdi (DISKALIFIYE): %s" % sizan


def test_ego_roll_telafi():
    """own_roll_rad = goruntu-roll'unden (GAIN ile) cikarilir -> DUZ hedef + kendi bank'imiz
    varken telafili roll ~0'a yakinsar (kendi roll'umuz sinyalden temizlenir)."""
    det = _det(cxn=0.5, cyn=0.5)
    # Goruntude kanat cizgisi ~duz (dy=0 -> roll_img~0). own_roll = +10 deg dayatalim.
    poz = _poz(0.40, 0.50, 0.60, 0.50)                # yatay kanat (roll_img=0)
    orr = math.radians(10.0)
    g = AvciIBVS(); g.hesapla(dict(det), Cfg, poz=poz, own_roll_rad=orr)
    d = g.durum()
    # ham roll ~0; telafili roll = 0 - GAIN*10deg -> GAIN=+1'de ~-10 deg (kendi bank'imiz cikti)
    assert abs(d["roll_raw_deg"]) < 1.0, "ham goruntu-roll ~0 olmali (duz kanat): %s" % d["roll_raw_deg"]
    bek = -float(Cfg.IBVS_EGO_ROLL_GAIN) * 10.0
    assert abs(d["roll_deg"] - bek) < 1.0, \
        "ego-telafili roll = -GAIN*own bekleniyordu (%.1f), gelen %.1f" % (bek, d["roll_deg"])
    # own_roll_rad=None -> telafi yok, ham=telafili
    g2 = AvciIBVS(); g2.hesapla(dict(det), Cfg, poz=poz, own_roll_rad=None)
    assert abs(g2.durum()["roll_deg"]) < 1.0, "own=None -> telafi yok, roll ~ham"


# ---------------------------------------------------------------------------
#  ONGORULU YAW LEAD (pose kanat uclarindan hedef ROLL/bank)
# ---------------------------------------------------------------------------
def _poz(uL, vL, uR, vR, cL=0.9, cR=0.9, aspect=170.0):
    """Normalize poz dict: kp[1]=sol kanat, kp[2]=sag kanat [u,v,conf]. aspect=None -> alan yok."""
    kp = [[0.5, 0.40, 0.9], [uL, vL, cL], [uR, vR, cR],
          [0.48, 0.55, 0.9], [0.52, 0.55, 0.9], [0.5, 0.60, 0.9]]
    d = {"kp": kp, "conf": 0.9, "ok": aspect is not None}
    if aspect is not None:
        d["aspect_deg"] = aspect
    return d


def test_roll_lead_sag_bank_mekanizma():
    """Sag kanat ALCAK (v buyuk) -> roll_img>0 -> lead uretilir; yaw komutu TAM lead kadar
    kayar; lead isareti = IBVS_SIGN_ROLL (isaret-bagimsiz: mekanizmayi test eder, yonu degil).
    (Yonun DOGRULUGU veriyle belirlenir: araclar/pose_ongoru_analiz.py -> IBVS_SIGN_ROLL.)"""
    det = _det(cxn=0.5, cyn=0.5)                          # merkez -> ex=0 -> yaw yalniz lead'den
    p = _CfgVar(IBVS_K_ROLL_LEAD=0.5)                     # ongoru default 0 -> testte AC
    k0 = AvciIBVS().hesapla(dict(det), p)                # poz yok -> lead 0, yaw 0
    g1 = AvciIBVS(); k1 = g1.hesapla(dict(det), p, poz=_poz(0.40, 0.48, 0.60, 0.56))
    d = g1.durum()
    assert d["roll_ok"] is True and abs(d["lead"]) > 1e-6, "sag bank -> lead uretilmeli"
    # yaw(ex=0) = clamp(lead). d["lead"] telemetride round(.,3)'lu -> 3-basamak toleransi.
    assert abs((k1[3] - k0[3]) - d["lead"]) < 1.5e-3, "yaw komutu lead kadar kaymali (ex=0)"
    assert math.copysign(1, d["lead"]) == math.copysign(1, float(Cfg.IBVS_SIGN_ROLL)), \
        "roll_img>0 -> lead isareti IBVS_SIGN_ROLL ile ayni olmali"


def test_roll_lead_sol_bank_ters_isaret():
    """Sol kanat ALCAK -> roll_img<0 -> lead isareti sag-bankin TERSI (yon simetrik)."""
    det = _det(cxn=0.5, cyn=0.5)
    p = _CfgVar(IBVS_K_ROLL_LEAD=0.5)                     # ongoru default 0 -> testte AC
    gs = AvciIBVS(); gs.hesapla(dict(det), p, poz=_poz(0.40, 0.48, 0.60, 0.56)); lead_sag = gs.durum()["lead"]
    gl = AvciIBVS(); gl.hesapla(dict(det), p, poz=_poz(0.40, 0.56, 0.60, 0.48)); lead_sol = gl.durum()["lead"]
    assert lead_sag * lead_sol < 0.0, "sag ve sol bank zit isaretli lead uretmeli"


def test_roll_lead_dusuk_conf_kapali():
    """Kanat ucu guveni dusuk -> ongoru kapisi kapali -> lead=0."""
    det = _det(cxn=0.5, cyn=0.5)
    g = AvciIBVS(); g.hesapla(dict(det), Cfg, poz=_poz(0.40, 0.48, 0.60, 0.56, cL=0.2, cR=0.2))
    assert g.durum()["roll_ok"] is False and abs(g.durum()["lead"]) < 1e-9


def test_roll_lead_aspect_kapisi():
    """Kafa kafaya (aspect<esik) -> kanat cizgisi bank'i temsil etmez -> lead=0."""
    det = _det(cxn=0.5, cyn=0.5)
    g = AvciIBVS(); g.hesapla(dict(det), Cfg, poz=_poz(0.40, 0.48, 0.60, 0.56, aspect=30.0))
    assert g.durum()["roll_ok"] is False


def test_roll_lead_poz_yok_eski_komut():
    """poz=None ile poz argumansiz cagri BIT-BIT ayni komut (geriye uyumlu)."""
    det = _det(cxn=0.7, cyn=0.4)
    a = AvciIBVS().hesapla(dict(det), Cfg)
    b = AvciIBVS().hesapla(dict(det), Cfg, poz=None)
    assert a == b, "poz=None eski davranisi bit-bit korumali: %s vs %s" % (a, b)


# ============================================================
#  YUMUSAK GECIS (soft-handoff) RAMPASI — GPS->gorsel surekliligi
# ============================================================
def test_handoff_ileri_rampalanir():
    # Uzak/kucuk bbox (istek tavanda). Rampa ACIK: ilk tik (t=handoff) ileri~0;
    # pencere sonrasi (t=HANDOFF_S) ileri TAVANA ulasir. Merkezdeki hedef -> saf ileri.
    p = _CfgVar(IBVS_HANDOFF_S=1.0, IBVS_DIKEY_NISAN=0.0)
    ibvs = AvciIBVS()
    # ilk gorsel tik: pencere baslar (t=100.0). Kucuk bbox -> istek doygun.
    _, pitch0, _, _ = ibvs.hesapla(_det(0.5, 0.5, wp=0.02, hp=0.01, t=100.0), p)
    assert abs(pitch0) < 1e-6, "ilk tik (s=0) ileri itki ~0 olmali (lunge yok): %.3f" % pitch0
    # pencere ortasi (t=100.5, s=0.5): ileri kismi acilmis olmali
    _, pitch_mid, _, _ = ibvs.hesapla(_det(0.5, 0.5, wp=0.02, hp=0.01, t=100.5), p)
    # pencere sonu (t=101.0, s=1.0): tavana ulasmali
    _, pitch_full, _, _ = ibvs.hesapla(_det(0.5, 0.5, wp=0.02, hp=0.01, t=101.0), p)
    assert pitch_full > pitch_mid > pitch0, ("ileri itki rampa boyunca ARTMALI: %.3f<%.3f<%.3f"
                                             % (pitch0, pitch_mid, pitch_full))
    assert abs(pitch_full - float(Cfg.IBVS_ILERI)) < 1e-6, \
        "pencere sonunda ileri TAVANA ulasmali: %.3f vs %.3f" % (pitch_full, Cfg.IBVS_ILERI)


def test_handoff_nisan_merkezden_baslar():
    # Merkezdeki hedef + negatif nisan. Rampa ACIK: ilk tik ey_ref_eff=0 -> eyy=0 -> thr~0
    # (ani alcalis YOK); pencere sonrasi ey_ref tam alttan-vur -> merkezdeki hedef icin thr<0.
    p = _CfgVar(IBVS_HANDOFF_S=1.0, IBVS_DIKEY_NISAN=-0.25)
    ibvs = AvciIBVS()
    thr0, _, _, _ = ibvs.hesapla(_det(0.5, 0.5, t=200.0), p)       # ilk tik: nisan=merkez
    assert abs(thr0) < 1e-6, "ilk tik merkezdeki hedef -> thr~0 (ani alcalis yok): %.3f" % thr0
    tlm0 = ibvs.durum()
    assert abs(tlm0["ey_ref"]) < 1e-6, "ilk tik ey_ref_eff~0 (merkez): %.3f" % tlm0["ey_ref"]
    # pencere sonu: tam nisan -> merkezdeki hedef icin thr negatif (alttan-vur alcaltir)
    thr_full, _, _, _ = ibvs.hesapla(_det(0.5, 0.5, t=201.0), p)
    assert thr_full < -1e-3, "pencere sonu merkezdeki hedef -> thr<0 (alttan-vur): %.3f" % thr_full


def test_handoff_kapali_eski_davranis():
    # IBVS_HANDOFF_S=0 -> s=1 hep -> rampa YOK -> cikti eski yasayla bit-ayni.
    p_off = _CfgVar(IBVS_HANDOFF_S=0.0, IBVS_DIKEY_NISAN=-0.25)
    p_yok = _CfgVar(IBVS_DIKEY_NISAN=-0.25)   # HANDOFF_S alani yok -> getattr default 0.0
    d = _det(0.6, 0.4, wp=0.03, hp=0.02, t=5.0)
    a = AvciIBVS().hesapla(dict(d), p_off)
    b = AvciIBVS().hesapla(dict(d), p_yok)
    assert a == b, "HANDOFF_S=0 ile yok ayni olmali: %s vs %s" % (a, b)
    # ve ilk tik zaten TAM ileri (rampa yok) — kucuk bbox istek doygun
    _, pitch, _, _ = AvciIBVS().hesapla(_det(0.5, 0.5, wp=0.02, hp=0.01, t=5.0), p_off)
    assert abs(pitch - float(Cfg.IBVS_ILERI)) < 1e-6, \
        "rampa kapali -> ilk tik TAM ileri: %.3f vs %.3f" % (pitch, Cfg.IBVS_ILERI)


if __name__ == "__main__":
    fns = [(n, f) for n, f in sorted(globals().items())
           if n.startswith("test_") and callable(f)]
    gecen = 0
    for n, f in fns:
        try:
            f()
            print("OK  " + n)
            gecen += 1
        except AssertionError as e:
            print("FAIL " + n + " -> " + str(e))
        except Exception as e:
            print("ERR  " + n + " -> " + repr(e))
    print("\n%d/%d test gecti." % (gecen, len(fns)))
    sys.exit(0 if gecen == len(fns) else 1)

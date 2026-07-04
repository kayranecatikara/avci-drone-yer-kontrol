# -*- coding: utf-8 -*-
"""
FAZ 3: ana_kontrol FSM entegrasyonu testleri (sim GEREKMEZ — sahte drone).
Calistirma:  python test/test_fsm_faz3.py
Kapsam: REGRESYON (pose'suz + OIPN kapali -> mevcut IBVS davranisi degismez),
FSM sirasi (CONFIRMED->GORSEL_GUDUM, kilit_tamam->KILIT_BILDIR->paket->ANGAJMAN),
kayipta GPS'e donuste kilit/hakem reset.
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from guidance.ana_kontrol import AvciKontrol, Cfg, _GORSEL_AILE
from detection.algi_hatti import AlgiCiktisi


class SahteDrone:
    def __init__(self):
        self.pos = (0.0, 0.0, 5000.0)
        self.rot = (0.0, 0.0, 0.0)
        self._last = None

    def get_drone_location(self):
        return self.pos

    def get_drone_rotation(self):
        return self.rot

    def get_drone_speed(self):
        return 0.0

    def get_target_location(self):
        return (10000.0, 0.0, 5000.0)

    def get_target_rotation(self):
        return (0.0, 0.0, 0.0)

    def set_control_surfaces(self, thr, pit, rol, yaw, arm):
        self._last = (thr, pit, rol, yaw, arm)


def _hedef(cx_n=0.5, cy_n=0.5, kaplama=0.10, conf=0.9, durum="CONFIRMED",
           tespit_mi=True, keypoints=None):
    W, H = 1920, 1080
    wh = (kaplama * W * H) ** 0.5
    d = {"track_id": 1, "cx": cx_n * W, "cy": cy_n * H, "w": wh, "h": wh,
         "conf": conf, "W": W, "H": H, "track_durumu": durum, "tespit_mi": tespit_mi,
         "t": None}
    if keypoints:
        d["keypoints"] = keypoints
    return d


def _ciktiyla(hedef, pnp=None, lam_dot=0.0, Vc=0.0):
    c = AlgiCiktisi()
    c.hedef = hedef
    c.pnp = pnp
    c.lam_dot = lam_dot
    c.Vc = Vc
    return c


def _kur(vis_mode="GORSEL"):
    d = SahteDrone()
    b = AvciKontrol(d)
    Cfg.TAKEOFF = False
    b._kalkis_done = True
    b.set_vis_mode(vis_mode)
    return b, d


def test_confirmed_gorsel_kilit():
    # OTO mod: CONFIRMED track -> GORSEL_GUDUM (eski "5 kare" yerine tracker sorgusu)
    b, d = _kur("OTO")
    import time
    for _ in range(3):
        h = _hedef(durum="CONFIRMED")
        h["t"] = time.perf_counter()
        b.set_algi(_ciktiyla(h))
        b.adim()
    assert b.durum in _GORSEL_AILE, b.durum


def test_tentative_gorsel_kilit_olmaz():
    b, d = _kur("OTO")
    import time
    for _ in range(5):
        h = _hedef(durum="TENTATIVE")
        h["t"] = time.perf_counter()
        b.set_algi(_ciktiyla(h))
        b.adim()
    assert b.durum not in _GORSEL_AILE       # TENTATIVE -> gorsel kilit YOK


def test_regresyon_oipn_kapali_posesuz():
    # OIPN kapali + PnP yok (pose'suz): _oipn_harmanla sonucu AYNEN dondurur.
    b, d = _kur()
    b.oipn_acik = False
    sonuc = (0.1, 0.2, 0.0, 0.3)
    out = b._oipn_harmanla(sonuc, np.array([0.0, 0.0, 5000.0]), 0.0)
    assert out == sonuc, "OIPN kapali -> IBVS komutu degismez (regresyon)"
    # OIPN acik ama PnP gecersiz -> yine degismez
    b.oipn_acik = True
    b._algi_pnp = {"gecerli": False}
    assert b._oipn_harmanla(sonuc, np.array([0.0, 0.0, 5000.0]), 0.0) == sonuc


def test_oipn_pnp_gecerli_harmanlar():
    # PnP gecerli + OIPN acik -> yaw bileseni DEGISIR (katki eklenir)
    b, d = _kur()
    b.oipn_acik = True
    b._algi_pnp = {"gecerli": True, "phi_T": 25.0, "rel_konum_dunya": (5000.0, 0.0, 0.0)}
    b._algi_lam_dot = 0.02
    b._algi_Vc = 500.0
    b.son_hiz = np.array([2000.0, 0.0, 0.0])
    sonuc = (0.1, 0.2, 0.0, 0.0)
    out = b._oipn_harmanla(sonuc, np.array([0.0, 0.0, 5000.0]), 0.0)
    assert out[:3] == sonuc[:3]              # thr/pitch/roll degismez
    assert abs(out[3] - sonuc[3]) > 1e-6     # yaw katki eklendi


def test_fsm_kesintisiz_paket_once_angajman_sonra():
    # KESINTISIZ kilit: kumulatif 5s'ye ulasinca surekli de >=3 -> ayni tikte
    # KILIT_BILDIR->ANGAJMAN. Kritik SIRALAMA: hakem paketi ANGAJMAN'dan ONCE (+400
    # once garanti, +500 sonra). Paket bir kez.
    b, d = _kur("GORSEL")
    b.durum = "GORSEL_GUDUM"
    tt = 0.0
    paket_tik = angajman_tik = None
    for i in range(int(7.0 / 0.05)):
        tt += 0.05
        onceki_gonderildi = b.hakem.kilit_gonderildi
        b._faz3_kilit_fsm(_hedef(durum="CONFIRMED"), tt, np.array([0.0, 0.0, 5000.0]))
        if paket_tik is None and b.hakem.kilit_gonderildi and not onceki_gonderildi:
            paket_tik = i
        if angajman_tik is None and b.durum == "ANGAJMAN":
            angajman_tik = i
    assert paket_tik is not None and angajman_tik is not None
    assert paket_tik <= angajman_tik, "hakem paketi (+400) ANGAJMAN'dan (+500) ONCE"
    assert b.durum == "ANGAJMAN"


def test_fsm_kesintili_kilit_bildirde_bekler():
    # KESINTILI kilit: kumulatif 5s (kilit_tamam) AMA surekli<3 -> KILIT_BILDIR'de
    # TAKILIR. Sonra kesintisiz 3.5s -> surekli>=3 -> ANGAJMAN. KILIT_BILDIR gorunur.
    b, d = _kur("GORSEL")
    b.durum = "GORSEL_GUDUM"
    tt = 0.0
    durumlar = []
    # Faz 1: her 1 sn'de 0.85 say + 0.15 kesinti -> kumulatif buyur, surekli kucuk
    for blok in range(9):
        for _ in range(17):                      # 0.85 sn say (0.05*17)
            tt += 0.05
            b._faz3_kilit_fsm(_hedef(durum="CONFIRMED"), tt, np.array([0, 0, 5000.0]))
            durumlar.append(b.durum)
        for _ in range(3):                       # 0.15 sn kesinti (AV disi -> saymaz)
            tt += 0.05
            b._faz3_kilit_fsm(_hedef(cx_n=0.9), tt, np.array([0, 0, 5000.0]))
            durumlar.append(b.durum)
        if b.durum == "ANGAJMAN":
            break
    # KILIT_BILDIR gorunmus olmali (kesinti surekli'yi sifirlarken kilit_tamam olustu)
    assert "KILIT_BILDIR" in durumlar, "kesintili -> KILIT_BILDIR'de beklemeli"
    # Faz 2: kesintisiz 3.5 sn -> surekli>=3 -> ANGAJMAN
    for _ in range(int(3.6 / 0.05)):
        tt += 0.05
        b._faz3_kilit_fsm(_hedef(durum="CONFIRMED"), tt, np.array([0, 0, 5000.0]))
    assert b.durum == "ANGAJMAN", b.durum


def test_kayip_gpse_donus_reset():
    # OTO: GORSEL_GUDUM'dayken uzun kayip -> ARAMA + kilit/hakem reset
    b, d = _kur("OTO")
    b.durum = "GORSEL_GUDUM"
    b.hakem.kilit_gonderildi = True
    # tespit None uzun sure -> _gorsel_guduum 3. asama (GPS'e don)
    Cfg.VIS_LOST_TO_GPS_S = 0.1
    for _ in range(50):
        sonuc = b._gorsel_guduum(None, 0.0, revert_izin=True)
        if sonuc is None:
            break
    assert b.durum == "ARAMA"
    assert b.hakem.kilit_gonderildi is False   # hakem reset (yeni kilit gonderilebilir)


def test_gps_mod_gorselden_doner_reset():
    b, d = _kur("GORSEL")
    b.durum = "KILIT_BILDIR"                    # gorsel ailesi
    b.hakem.kilit_gonderildi = True
    b.set_vis_mode("GPS")                       # -> reset
    assert b.hakem.kilit_gonderildi is False


if __name__ == "__main__":
    testler = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in testler:
        t()
        print("OK  %s" % t.__name__)
    print("TUM TESTLER GECTI (%d)" % len(testler))

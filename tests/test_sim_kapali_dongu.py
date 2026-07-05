# -*- coding: utf-8 -*-
"""
KAPALI-DONGU SIM HARNESS — IBVS gorsel guduumu SENTETIK plant + GERCEK kamera
projeksiyonuyla (pose/geometri.py) 50 Hz kapali dongude kosturur. Oyun/SDK YOK.

Nicin var (v1 dersi): dikey yasanin ilk surumu birim testlerden gecip canlida
(eski kodla test edildigi sanilarak) sinif gecti sanildi; kapali dongu davranis
ancak plant'la gorulur. Bu harness ozellikle F1 (durus->goruntu baglasimi)
kabul testini icerir: comp KAPALI cevrim imzasini URETMELI, ACIK yakinsamali.

PLANT (SDK_README + Cfg sabitlerinden; docs/olcumle gerekcelendirilmis):
  - lean (pitch/roll): hedef aci = cmd*60 derece; birinci-derece izleme (rate 5.0 /s).
  - yatay:  v' = g*tan(lean) - k_d*v ;  k_d = g*tan(60)/3333 -> tam yatista uc hiz 3333 cm/s.
  - dikey:  thr>0 -> vz hedefi thr*3333'e birinci-derece (tau=0.2 s; sim'in hiz dongusu);
            thr=0 -> vz hedefi 0 (irtifa-tut);  thr<0 -> vz' = thr*g (ivme alani, sinirsiz).
  - toplam hiz tavani 3333 cm/s (yatay + TIRMANIS bileseni; dalis MUAF).
  - yaw: cmd * YAW_RATE_DPS (SDK belgesiz -> PARAMETRE; mutlak assert'ler buna duyarsiz).
KAMERA: gercek pose/geometri.kamera_pozu + projekte (tilt 25, hFOV 125) -> F1'in
fizigi plant'in ICINDE, varsayim degil. bbox: w_px = fx*KANAT/d, h = w/2.22.

Kosum:  python -m pytest tests/sim_kapali_dongu.py -q   (deterministik; tohumlu)
"""
import math
import os
import random
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from guidance.ibvs_guidance import AvciGorselGuduum, KilitlenmeTakip  # noqa: E402
from pose.geometri import fx_from_hfov, kamera_pozu, projekte         # noqa: E402


# --- Kontrolcu sabitleri (ana_kontrol.Cfg klonu; degerler birebir) -----------
class P:
    VIS_EMA = 0.4; VIS_EY_REF = 0.43
    VIS_ATT_COMP = 1.0; VIS_CAM_TILT_DEG = 25.0; VIS_HFOV_DEG = 125.0
    VIS_SIGN_YAW = +1.0; VIS_SIGN_VZ = -1.0; VIS_SIGN_PITCH = +1.0; VIS_SIGN_ROLL = +1.0
    VIS_K_YAW = 0.5; VIS_K_ROLL = 0.0
    VIS_K_VZ = 2.0; VIS_VZ_MAX = 1100.0; VIS_KV_Z = 0.0020; VIS_ALC_MIN = 0.5
    VIS_K_FWD = 0.4; VIS_FWD_MAX = 0.5; VIS_CENTER_GATE = 0.35; VIS_W_STOP = 0.30
    VIS_USE_POSE_DIST = 0.0; VIS_DIST_SLOW_M = 12.0; VIS_DIST_STOP_M = 4.0
    THR_DN = -1.00; THR_UP = 0.70; VZ_MAX = 3333.0
    VIS_STALE_S = 0.5; VIS_DEADRECKON_S = 0.5
    KILIT_SURE_S = 5.0; KILIT_ESIK_ORAN = 0.06; KILIT_TOLERANS_S = 0.2
    KILIT_ALAN_X = 0.25; KILIT_ALAN_Y = 0.10


DT = 0.02                       # 50 Hz kontrol
MAX_DELTA = 0.05                # ana_kontrol._send rate limiti (klon)
G = 981.0                       # cm/s^2
LEAN_MAX = 60.0                 # derece (cmd=1)
LEAN_RATE = 5.0                 # UE FInterpTo hizi (1/s)
V_CAP = 3333.0                  # cm/s toplam hiz tavani
K_DRAG = G * math.tan(math.radians(LEAN_MAX)) / V_CAP   # 0.5098 -> uc hiz tutarli
KANAT_CM = 171.8                # Talon kanat acikligi (bbox genisligi kaynagi)
BBOX_ASPECT = 2.22              # w/h (gozlenen ~1.25 normalize @16:9 -> px oraninda 2.22)
W_PX, H_PX = 960.0, 540.0
FX = fx_from_hfov(W_PX)


def clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x


def rate_limit(hedef, onceki):
    return onceki + clamp(hedef - onceki, -MAX_DELTA, MAX_DELTA)


class Plant:
    """Asimetrik dikey + lean-tabanli yatay + parametrik yaw plant'i."""

    def __init__(self, pos, yaw_deg=0.0, yaw_rate_dps=90.0):
        self.pos = list(pos)            # cm (x, y, z)
        self.v = [0.0, 0.0]             # yatay hiz (dunya, cm/s)
        self.vz = 0.0                   # dikey hiz (cm/s, +yukari)
        self.lean = 0.0                 # one yatis (derece, + = one)
        self.yaw = yaw_deg              # derece
        self.yaw_rate_dps = yaw_rate_dps

    @property
    def pitch_ue(self):
        return -self.lean               # UE FRotator: one yatis = NEGATIF pitch

    def step(self, thr, pitch_cmd, roll_cmd, yaw_cmd, dt=DT):
        # lean birinci-derece izleme
        self.lean += (pitch_cmd * LEAN_MAX - self.lean) * min(1.0, LEAN_RATE * dt)
        # yatay: govde-ileri yonunde ivme + dogrusal surukleme
        a = G * math.tan(math.radians(clamp(self.lean, -75.0, 75.0)))
        yr = math.radians(self.yaw)
        ileri = (math.cos(yr), math.sin(yr))
        self.v[0] += (a * ileri[0] - K_DRAG * self.v[0]) * dt
        self.v[1] += (a * ileri[1] - K_DRAG * self.v[1]) * dt
        # dikey (asimetrik!)
        if thr > 0.0:
            self.vz += (thr * V_CAP - self.vz) * min(1.0, dt / 0.2)   # hiz komutu (sim izler)
        elif thr == 0.0:
            self.vz += (0.0 - self.vz) * min(1.0, dt / 0.2)           # irtifa-tut freni
        else:
            self.vz += thr * G * dt                                    # ivme alani (serbest dusus)
        # toplam hiz tavani (dalis MUAF)
        vh = math.hypot(self.v[0], self.v[1])
        vklim = math.hypot(vh, max(self.vz, 0.0))
        if vklim > V_CAP:
            olcek = V_CAP / vklim
            self.v[0] *= olcek; self.v[1] *= olcek
            if self.vz > 0.0:
                self.vz *= olcek
        # yaw + konum
        self.yaw += yaw_cmd * self.yaw_rate_dps * dt
        self.pos[0] += self.v[0] * dt
        self.pos[1] += self.v[1] * dt
        self.pos[2] += self.vz * dt


def bbox_uret(plant, hedef_pos):
    """Gercek projeksiyonla hedef bbox'i (px) | None (kamera arkasi/kadraj disi)."""
    cam_pos, R_cam = kamera_pozu(plant.pos, (0.0, plant.pitch_ue, plant.yaw))
    uv = projekte(hedef_pos, cam_pos, R_cam, FX, W_PX, H_PX)
    if uv is None:
        return None, None
    u, v = uv
    d = math.dist(plant.pos, hedef_pos)
    w = FX * KANAT_CM / max(d, 1.0)
    h = w / BBOX_ASPECT
    if u < -w or u > W_PX + w or v < -h or v > H_PX + h:
        return None, d                   # kadraj disi (kayip)
    return {"cx": u, "cy": v, "w": w, "h": h, "conf": 0.9, "cls": 0,
            "W": W_PX, "H": H_PX}, d


class GorselDongu:
    """ana_kontrol GORSEL dalinin saf klonu: bayatlik + kor-devam + rate limit + kilit."""

    def __init__(self, p):
        self.p = p
        self.ibvs = AvciGorselGuduum()
        self.kilit = KilitlenmeTakip()
        self.prev = {"thr": 0.0, "pitch": 0.0, "roll": 0.0, "yaw": 0.0}
        self.son_det = None
        self.son_det_t = None
        self._lost = 0
        self.raw_pitch = 0.0            # kapi-flip metrigi icin ham ileri komut

    def adim(self, det, now, vz, pitch_ue, poz_cm=None):
        if det is not None:
            self.son_det, self.son_det_t = det, det["t"]
        self.kilit.guncelle(self.son_det, self.son_det_t, now, self.p, DT)
        taze = None
        if self.son_det is not None and (now - self.son_det_t) <= self.p.VIS_STALE_S:
            taze = self.son_det
        if taze is not None:
            self._lost = 0
            cmd = self.ibvs.hesapla((taze["cx"], taze["cy"]), taze["W"], taze["H"],
                                    (taze["w"], taze["h"]), self.p, vz=vz,
                                    pitch_deg=pitch_ue, det_t=taze["t"], poz_cm=poz_cm)
        else:
            self._lost += 1
            if self._lost * DT <= self.p.VIS_DEADRECKON_S:
                cmd = self.ibvs.kor_devam(self.p, vz)
            else:
                cmd = (0.0, 0.0, 0.0, 0.0)
        self.raw_pitch = cmd[1]
        for ad, deger in zip(("thr", "pitch", "roll", "yaw"), cmd):
            self.prev[ad] = rate_limit(deger, self.prev[ad])
        return self.prev


def kosu(p, sure_s, hedef_fn, det_hz=10.0, dropout=0.0, tohum=42,
         baslangic=(0.0, 0.0, 5000.0), poz_ver=False, yaw_rate_dps=90.0,
         dur_mesafe_cm=None):
    """Senaryoyu kostur; metrik sozlugu doner. hedef_fn(t) -> (x,y,z) cm.
    dur_mesafe_cm: verilirse hedefe bu kadar yaklasinca kosu biter (yaklasma-penceresi
    olcumu; genislik-freni standoff dinamigi ayri senaryolarin konusu)."""
    rnd = random.Random(tohum)
    plant = Plant(baslangic, yaw_deg=0.0, yaw_rate_dps=yaw_rate_dps)
    dongu = GorselDongu(p)
    det_periyot = 1.0 / det_hz
    son_ornek = -1e9
    m = {"thr_poz_ihlal": 0, "kapi_flip": 0, "alt0": plant.pos[2], "alt_min": plant.pos[2],
         "alt_max": plant.pos[2], "ey_kare_top": 0.0, "ey_n": 0, "kilit": False,
         "kilit_t": None, "gordu": 0, "tik": 0}
    onceki_ileri_var = False
    t = 0.0
    while t < sure_s:
        t += DT
        hedef = hedef_fn(t)
        det = None
        if (t - son_ornek) >= det_periyot - 1e-9:
            son_ornek = t
            bb, d = bbox_uret(plant, hedef)
            if bb is not None and rnd.random() >= dropout:
                bb["t"] = t
                det = bb
        poz_cm = None
        if poz_ver:
            poz_cm = math.dist(plant.pos, hedef_fn(t))       # mukemmel poz (mesafe)
        cmd = dongu.adim(det, t, plant.vz, plant.pitch_ue, poz_cm=poz_cm)
        # degismezler / metrikler
        if dongu.ibvs.son_vz_des is not None and dongu.ibvs.son_vz_des < 0.0 \
                and cmd["thr"] > 1e-9:
            m["thr_poz_ihlal"] += 1
        ileri_var = dongu.raw_pitch > 1e-6
        if t > 2.0 and ileri_var != onceki_ileri_var:
            m["kapi_flip"] += 1
        onceki_ileri_var = ileri_var
        if dongu.ibvs.son_eyd is not None and t > 3.0:
            m["ey_kare_top"] += dongu.ibvs.son_eyd ** 2
            m["ey_n"] += 1
        if det is not None:
            m["gordu"] += 1
        if dongu.kilit.basarili and not m["kilit"]:
            m["kilit"], m["kilit_t"] = True, t
        plant.step(cmd["thr"], cmd["pitch"], cmd["roll"], cmd["yaw"])
        m["alt_min"] = min(m["alt_min"], plant.pos[2])
        m["alt_max"] = max(m["alt_max"], plant.pos[2])
        m["tik"] += 1
        if dur_mesafe_cm is not None and math.dist(plant.pos, hedef_fn(t)) < dur_mesafe_cm:
            break
    m["alt_net_m"] = (plant.pos[2] - m["alt0"]) / 100.0
    m["alt_zirve_m"] = (m["alt_max"] - m["alt0"]) / 100.0    # sahte-tirmanis imzasi (F1)
    m["alt_cukur_m"] = (m["alt0"] - m["alt_min"]) / 100.0
    m["eyd_rms"] = math.sqrt(m["ey_kare_top"] / m["ey_n"]) if m["ey_n"] else None
    return m


# =============================================================================
#  TESTLER
# =============================================================================
def _sabit_hedef(pos):
    return lambda t: pos


class P_KAPALI(P):
    VIS_ATT_COMP = 0.0


def test_f1_kabul_comp_kapali_cevrim_acik_yakinsar():
    """F1 KABUL TESTI: ayni tohum/senaryo, tek bayrak farki.
    comp KAPALI -> durus->goruntu baglasimi cevrim imzasi uretir (net tirmanis
    ve/veya kapi cirpinmasi); comp ACIK -> dikey sakin, kapi kararli."""
    # 40 m onde, AYNI irtifa. Olcum YAKLASMA PENCERESI: 10 m'ye varinca kosu biter
    # (genislik-freninin standoff/asma dinamigi bu testin konusu degil — F1 dikey
    # baglasimi olcer; asma dinamigi poz-profilli senaryoda sinanir).
    hedef = _sabit_hedef((4000.0, 0.0, 5000.0))
    kapali = kosu(P_KAPALI, 15.0, hedef, dur_mesafe_cm=1000.0)
    acik = kosu(P, 15.0, hedef, dur_mesafe_cm=1000.0)
    # KAPALI: cevrim imzasi — one yatis apparent-ey'yi dusurur, sabit REF bunu
    # "hedef yukarida" sanip TIRMANIR (zirve tirmanisi) ve/veya kapi cirpinir.
    assert (kapali["alt_zirve_m"] > 3.0) or (kapali["kapi_flip"] >= 6), \
        "comp KAPALI cevrim imzasi uretmedi: %r" % kapali
    # ACIK: ayni irtifadaki hedefe yaklasirken dikey SAKIN + kapi kararli.
    assert acik["alt_zirve_m"] < 2.0 and abs(acik["alt_net_m"]) < 2.0, \
        "comp ACIK irtifa surukledi: %r" % acik
    assert acik["kapi_flip"] <= 2, "comp ACIK kapi cirpindi: %r" % acik
    assert acik["eyd_rms"] is not None and acik["eyd_rms"] < 0.08, \
        "comp ACIK eyd RMS yuksek: %r" % acik
    assert kapali["eyd_rms"] > 2.0 * acik["eyd_rms"], \
        "comp farki eyd RMS'e yansimadi: %r vs %r" % (kapali["eyd_rms"], acik["eyd_rms"])
    assert acik["thr_poz_ihlal"] == 0 and kapali["thr_poz_ihlal"] == 0


def test_inis_talebinde_thr_asla_pozitif_degil():
    """Degismez: vz_des<0 iken uygulanan thr hicbir tikte pozitif olamaz
    (v2 asimetrik yasanin cekirdek guvencesi; kesen + alcalan hedefte de)."""
    def alcalan(t):
        return (3000.0 + 400.0 * t, 0.0, 5000.0 - 200.0 * t)   # 4 m/s uzaklasan, 2 m/s alcalan
    m = kosu(P, 12.0, alcalan)
    assert m["thr_poz_ihlal"] == 0, m
    def kesen(t):
        return (2500.0, -1500.0 + 500.0 * t, 4800.0)           # 5 m/s yanal kesis
    m2 = kosu(P, 10.0, kesen)
    assert m2["thr_poz_ihlal"] == 0, m2


def test_kadans_kilit_matematigi():
    """F2 dogrulamasi (plant'siz): mukemmel geometriye ragmen dedektor kadansi
    dusukse KILITLENME imkansiz; ~5 Hz ustunde mumkun."""
    def kilit_dene(hz, sure=8.0):
        k = KilitlenmeTakip()
        periyot, son, det_t = 1.0 / hz, -1e9, None
        det = {"cx": 480.0, "cy": 270.0, "w": 100.0, "h": 60.0, "W": W_PX, "H": H_PX}
        t = 0.0
        while t < sure:
            t += DT
            if (t - son) >= periyot - 1e-9:
                son, det_t = t, t
            k.guncelle(det, det_t, t, P, DT)
        return k.basarili
    assert not kilit_dene(2.0), "2 Hz'de kilit IMKANSIZ olmali (tazelik 0.2 s)"
    assert not kilit_dene(4.0), "4 Hz'de butce yetmemeli"
    assert kilit_dene(10.0), "10 Hz'de kilit olmali"
    assert kilit_dene(20.0), "20 Hz'de kilit olmali"


class P_POZ(P):
    VIS_USE_POSE_DIST = 1.0


def test_poz_profili_yaklas_tut_kilitlen():
    """F5 kapali-dongu: poz-mesafeli profil 4 m'de durdurur (asiri yaklasip Av'dan
    tasma YOK) ve sartname kilitlenmesi tamamlanir."""
    hedef = _sabit_hedef((500.0, 0.0, 5000.0))               # 5 m onde, ayni irtifa
    m = kosu(P_POZ, 20.0, hedef, det_hz=10.0, poz_ver=True)
    assert m["kilit"], "poz-profilli tutusta kilitlenme gelmedi: %r" % m
    assert m["thr_poz_ihlal"] == 0
    assert abs(m["alt_net_m"]) < 2.0


def test_kesen_hedef_ve_dropout_raporu(capsys):
    """F6 kanit tabani (RAPOR; mutlak assert yalniz degismezlerde): kesen hedefte
    P-lag ve %27 dropout'ta kilit fizibilitesi olculur, yazdirilir."""
    print("\n--- KESEN HEDEF / DROPOUT RAPORU (yaw_rate=90 dps varsayimi) ---")
    for om in (5.0, 10.0):                                   # LOS acisal hizi ~ derece/s
        r = 2500.0
        def kesen(t, om=om, r=r):
            a = math.radians(om) * t
            return (r * math.cos(a), r * math.sin(a), 5000.0)
        m = kosu(P, 10.0, kesen)
        print("  omega=%4.1f dps: eyd_rms=%s kapi_flip=%d alt_net=%.1f m kilit=%s"
              % (om, ("%.3f" % m["eyd_rms"]) if m["eyd_rms"] else "-",
                 m["kapi_flip"], m["alt_net_m"], m["kilit"]))
        assert m["thr_poz_ihlal"] == 0
    md = kosu(P, 15.0, _sabit_hedef((1500.0, 0.0, 5000.0)), det_hz=10.0, dropout=0.27)
    print("  10 Hz + %%27 dropout: kilit=%s (t=%s) gordu=%d"
          % (md["kilit"], md["kilit_t"], md["gordu"]))
    assert md["thr_poz_ihlal"] == 0

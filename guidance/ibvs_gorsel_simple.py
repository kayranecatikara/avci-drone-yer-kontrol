# -*- coding: utf-8 -*-
"""
BASIT IBVS — SADE GORSEL GUDUM  (goruntu merkezi -> bbox merkezi cizgisi)
=========================================================================
TEK FIKIR: goruntunun NISAN NOKTASINDAN tespit kutusunun (bbox) merkezine bir
cizgi cek. Cizginin YATAY bileseni yaw'a, DIKEY bileseni throttle'a gider;
BUYUKLUGU (sapma) ileri itkiyi kisar. Cizgiyi sifira surerken surekli ileri
ucmak = saf takip (pure pursuit); rota hedefin uzerine kapanir.

    ex = (cx - W/2) / (W/2)         -1..+1   (+ = hedef SAGDA)
    ey = (cy - H/2) / (H/2)         -1..+1   (+ = hedef ASAGIDA)
    eyy = ey - EY_HEDEF                       nisandan dikey sapma
    r   = hypot(ex, eyy)                      (0 = nisan noktasinda)

    yaw   = K_YAW   * ex                      hedef sagda  -> saga don
    thr   = K_DIKEY * (-eyy)                  hedef nisanin ustunde -> tirman
    pitch = ILERI * (1 - MERKEZ_FREN*r)       nisandayken tam ileri; sapinca kis
    roll  = 0                                 cerceveleme yaw'in isi; bank YOK

EY_HEDEF (tek sabit): kamera govdeye +25 derece YUKARI tilt'li. Hedefi kadraj
MERKEZINDE degil biraz USTUNDE tutmak = arac hedefin ALTINDA kalir (gokyuzu arka
plan / alttan yaklasma). Eski surumdeki tan(TILT)/tan(VFOV) turevi TEK bir sayiya
(~ -0.1) iniyordu; burada dogrudan sabit girilir.

TASARIM: ILERI itki UYSAL ve ~sabit tutulur. Agresif ileri itki govdeyi one
yatirir, govdeye sabit kamera duser, hedef goruntude yukari ziplar -> dikey kanal
kaosu. Eski surumdeki ego-pitch telafi / alcalma freni / yak-agirlikli fren /
soft-handoff KATMANLARININ HEPSI bu bagi kovaliyordu. Ileri uysal olunca bag
zayif, o katmanlar GEREKMEZ -> bilincli olarak YOK.

YARISMA KURALI: gorsel temas SONRASI komut YALNIZCA gorsel veriden (bbox
pikselleri). hesapla imzasinda konum/hiz/rotasyon YOK -> GPS/J yapisal olarak
giremez (test_gps_siz_imza). poz/own_roll/own_pitch parametreleri ARAYUZ uyumu
icin kabul edilir ama bu sade yasada KULLANILMAZ.
"""
import math


def clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x


class AvciIBVS:
    """Basit IBVS: tek durum ex/ey EMA'si (tek-kare YOLO sicramasini yumusatir)."""

    def __init__(self):
        self.sifirla()

    def sifirla(self):
        """Gorev basi / kaynak degisimi / GPS'e donus: filtreyi taze basla."""
        self.ex_f = 0.0          # EMA yatay sapma (-1 sol .. +1 sag)
        self.ey_f = 0.0          # EMA dikey sapma (-1 ust .. +1 alt)
        self._had = False        # ilk kare EMA'siz alinir
        self._tlm = {}           # son telemetri (server build_telemetry okur)

    # ------------------------------------------------------------------
    #  det: {cx,cy,w,h,conf,W,H,t} (piksel) -> (thr, pitch, roll, yaw) [-1..1]
    #  poz/own_roll_rad/own_pitch_rad: arayuz uyumu icin kabul; KULLANILMAZ.
    # ------------------------------------------------------------------
    def hesapla(self, det, p, poz=None, own_roll_rad=None, own_pitch_rad=None):
        W = float(det["W"]); H = float(det["H"])
        ex = (float(det["cx"]) - W / 2.0) / (W / 2.0) if W > 1 else 0.0
        ey = (float(det["cy"]) - H / 2.0) / (H / 2.0) if H > 1 else 0.0

        # EMA yumusatma (tek-kare yanlis tespiti bastir)
        a = clamp(float(getattr(p, "VIS_EMA", 0.4)), 0.0, 1.0)
        if self._had:
            self.ex_f = (1.0 - a) * self.ex_f + a * ex
            self.ey_f = (1.0 - a) * self.ey_f + a * ey
        else:
            self.ex_f, self.ey_f = ex, ey
            self._had = True

        # DIKEY NISAN: tek sabit (kamera tilt'i icin; negatif = hedefi merkez ustunde tut).
        ey_hedef = float(getattr(p, "IBVS_EY_HEDEF", -0.1))
        eyy = self.ey_f - ey_hedef                     # nisandan dikey sapma
        r = math.hypot(self.ex_f, eyy)
        aci = math.degrees(math.atan2(-eyy, self.ex_f)) if r > 1e-9 else 0.0

        # KOMUTLAR
        yaw = clamp(float(getattr(p, "IBVS_SIGN_YAW", 1.0)) * float(p.IBVS_K_YAW) * self.ex_f,
                    -float(p.YAW_MAX), float(p.YAW_MAX))
        thr = clamp(float(getattr(p, "IBVS_SIGN_DIKEY", 1.0)) * float(p.IBVS_K_DIKEY) * (-eyy),
                    float(p.THR_DN), float(p.THR_UP))
        kisma = clamp(1.0 - float(p.IBVS_MERKEZ_FREN) * r, 0.0, 1.0)
        pitch = float(getattr(p, "PITCH_SIGN", 1.0)) * float(p.IBVS_ILERI) * kisma
        roll = 0.0

        self._tlm = {
            "law": "IBVS-SIMPLE",
            "ex": round(self.ex_f, 3), "ey": round(self.ey_f, 3),
            "ey_ref": round(ey_hedef, 3),
            "buyukluk": round(r, 3),
            "aci_deg": round(aci, 1),
            "kisma": round(kisma, 3),
            "dikey": round(thr, 3), "ileri": round(pitch, 3), "yaw": round(yaw, 3),
        }
        return float(thr), float(pitch), float(roll), float(yaw)

    # ------------------------------------------------------------------
    #  Telemetri (server build_telemetry okur; guduum girdisi DEGIL).
    # ------------------------------------------------------------------
    def durum(self):
        return dict(self._tlm)

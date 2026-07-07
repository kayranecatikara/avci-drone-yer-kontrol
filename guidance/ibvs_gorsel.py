# -*- coding: utf-8 -*-
"""
HAMIDIYE — BASIT IBVS GORSEL GUDUM  (goruntu merkezi -> bbox merkezi cizgisi)
=============================================================================
TEK FIKIR: goruntunun ORTA NOKTASINDAN tespit kutusunun (bbox) MERKEZINE bir
cizgi cek. Bu cizginin ACISI duzeltmenin yonunu, BUYUKLUGU ise merkeze olan
sapma "mesafesini" verir. Guduum bu cizgiyi SIFIRA surmekten ibarettir:
cizgi kuculdukce hedef kadraj merkezine oturur; hedef merkezde tutulup
surekli ILERI ucunca rota kendiliginden hedefin uzerine kapanir (saf takip /
pure pursuit). Kamera govdeye +25 derece YUKARI tilt'li oldugundan hedefi
merkezde tutmak araci hedefin ALTINDA tutar (gokyuzu arka plan / alttan
yaklasma) — bunun icin ekstra kod GEREKMEZ, geometriden bedava gelir.

    ex = (cx - W/2) / (W/2)     -1..+1   (+ = hedef goruntude SAGDA)
    ey = (cy - H/2) / (H/2)     -1..+1   (+ = hedef goruntude ASAGIDA)
    buyukluk  r = hypot(ex, ey)          (0 = tam merkez, ~1.41 = kose)
    aci         = atan2(-ey, ex)         (0 = saga, +90 = yukari; derece)

    yaw   = K_YAW   * ex                 hedef sagda  -> saga don
    thr   = K_DIKEY * (-ey)              hedef yukarida -> tirman
    pitch = ILERI * (1 - MERKEZ_FREN*r)  merkezde tam ileri; sapmisken kis
    roll  = 0                            cerceveleme yaw'in isi; bank YOK
                                         (eski PN'de bank hedefi kadrajdan
                                          atip kamerayi yere ceviriyordu)

YARISMA KURALI (KATI): gorsel temas SONRASI hareket komutu YALNIZCA gorsel
veriden turetilir. Bu yasaya zaten SADECE bbox pikselleri girer — GPS/GNSS,
J-filtre, konum/hiz telemetrisi hicbir sekilde KULLANILMAZ (diskalifiye
kurali yapisal olarak saglanir; fonksiyon imzasinda konum parametresi yok).

Eski PN/PNG yigini (LOS vektoru, Omega, pinhole menzil, kapanma regulasyonu,
look-up geometrisi, soft-start, lead-yaw, YAKLASMA/TAKIP/TERMINAL alt-FSM)
2026-07-07'de kullanici karariyla KOMPLE SILINDI; git gecmisinde durur.
Parametreler disaridan `p` (Cfg) ile gelir; ana_kontrol IMPORT EDILMEZ.
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
        self.ex_f = 0.0              # EMA yatay sapma (-1 sol .. +1 sag)
        self.ey_f = 0.0              # EMA dikey sapma (-1 ust .. +1 alt)
        self._had = False            # ilk kare EMA'siz alinir
        self._tlm = {}               # son telemetri (server build_telemetry okur)

    # ------------------------------------------------------------------
    #  det: {cx,cy,w,h,conf,W,H,t} (piksel) -> (thr, pitch, roll, yaw) [-1..1]
    #  Server ayni det'i VIS_STALE_S boyunca sunar; ayni kareyi tekrar gormek
    #  zararsizdir (EMA sabit degere yakinsar = son komutu tutar).
    # ------------------------------------------------------------------
    def hesapla(self, det, p):
        W = float(det["W"]); H = float(det["H"])
        ex = (float(det["cx"]) - W / 2.0) / (W / 2.0) if W > 1 else 0.0
        ey = (float(det["cy"]) - H / 2.0) / (H / 2.0) if H > 1 else 0.0
        a = clamp(float(p.VIS_EMA), 0.0, 1.0)
        if self._had:
            self.ex_f = (1.0 - a) * self.ex_f + a * ex
            self.ey_f = (1.0 - a) * self.ey_f + a * ey
        else:
            self.ex_f, self.ey_f = ex, ey
            self._had = True

        # merkez -> bbox cizgisi: buyukluk (sapma "mesafesi") + aci
        r = math.hypot(self.ex_f, self.ey_f)
        aci = math.degrees(math.atan2(-self.ey_f, self.ex_f)) if r > 1e-9 else 0.0

        # cizginin yatay bileseni -> yaw, dikey bileseni -> throttle (tirman/alcal)
        yaw = clamp(float(p.IBVS_SIGN_YAW) * float(p.IBVS_K_YAW) * self.ex_f,
                    -float(p.YAW_MAX), float(p.YAW_MAX))
        thr = clamp(float(p.IBVS_SIGN_DIKEY) * float(p.IBVS_K_DIKEY) * (-self.ey_f),
                    float(p.THR_DN), float(p.THR_UP))
        # ileri itki: cizgi buyudukce kisilir (once don/ortala, sonra bas gitsin)
        kisma = clamp(1.0 - float(p.IBVS_MERKEZ_FREN) * r, 0.0, 1.0)
        pitch = float(p.PITCH_SIGN) * clamp(float(p.IBVS_ILERI), 0.0, 1.0) * kisma
        roll = 0.0

        self._tlm = {
            "law": "IBVS",
            "ex": round(self.ex_f, 3), "ey": round(self.ey_f, 3),
            "buyukluk": round(r, 3),          # cizgi buyuklugu (0=merkez)
            "aci_deg": round(aci, 1),         # cizgi acisi (0=sag, +90=yukari)
            "kisma": round(kisma, 3),         # ileri itki carpani (1=tam gaz)
            "dikey": round(thr, 3), "ileri": round(pitch, 3), "yaw": round(yaw, 3),
        }
        return float(thr), float(pitch), float(roll), float(yaw)

    # ------------------------------------------------------------------
    #  Telemetri (server build_telemetry okur; guduum girdisi DEGIL).
    # ------------------------------------------------------------------
    def durum(self):
        return dict(self._tlm)

# -*- coding: utf-8 -*-
"""
HAMIDIYE - GORSEL GUDUM (DUZ IBVS: image-based visual servoing)
================================================================================
Gorsel temas sonrasi YONELIM komutu YALNIZCA kameradan uretilir (yarisma kurali:
bu asamada GPS yonelimi KULLANILMAZ). Tek hata sinyali: best.pt bbox MERKEZININ
goruntu merkezinden sapmasi. PnP / derinlik / poz / ROLL YOK (roll=0; sonraki asama).

Goruntu ekseni: sol-ust orijin, x -> SAGA, y -> ASAGI.
  ex = (cx - W/2) / (W/2)   [-1..1]  (+ = hedef SAGDA)
  ey = (cy - H/2) / (H/2)   [-1..1]  (+ = hedef ALTTA)

EKSEN ESLEME (SDK fizigi ile TUTARLI):
  SDK'da  pitch/roll = YATAY ivme (ileri/sag),  throttle = DIKEY hiz (tirman/alc).
  Niyet: "TIKLANAN/TESPIT EDILEN noktaya UC" (LOS = bakis hatti guduumu):
    yaw      <- ex            : hedefi YATAYDA ortala (burnu/govdeyi dondur)
    throttle <- LOS dikey acisi: bbox merkezi bir BAKIS YONU'dur. Kamera TILT
                derece YUKARI egik oldugundan pikselin ufka gore gercek acisi
                  elev = TILT - atan(ey * tan(vFOV/2))
                throttle = K_VZ * tan(elev)  (+ = tirman; SDK: thr = dikey hiz).
                elev=0 cizgisi (ey = tan(TILT)/tan(vFOV/2) ~ 0.43, turuncu REF)
                = ayni-irtifa duz ucus -> eski REF davranisiyla birebir uyumlu,
                ama artik alcalma/tirmanma SIMETRIK ve geometrik olarak dogru.
    pitch    <- ILERI         : yatayda hizalanmissa YAKLAS (bbox buyudukce
                                yavasla). Kapi YALNIZ |ex| — dikey hata ileriyi
                                BLOKLAMAZ (dikey, throttle ile eszamanli cozulur).
    roll     = 0              : bu asamada kapali (agility/sonraki asama)

Rate-limit BURADA yapilmaz; AvciKontrol._send() zaten yapar (komut surekliligi).
Parametreler (TILT, K_*, ...) disaridan `p` (Cfg) ile gelir -> canli tune bedava,
dongusel import yok (bu dosya ana_kontrol'u import ETMEZ).
"""

import math


def clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x


class AvciGorselGuduum:

    def __init__(self):
        self.ex_f = None            # EMA-yumusatilmis yatay hata (tek-kare yanlis tespiti bastirir)
        self.ey_f = None
        self._son = None            # (ex_f, ey_f, area) - kayipta kor-devam icin son gecerli durum

    def sifirla(self):
        """Re-acquire / gorev basi: EMA ve kor-devam durumunu temizle."""
        self.ex_f = self.ey_f = None
        self._son = None

    # ------------------------------------------------------------------
    #  Yeni bbox ile komut uret (gorsel temas VAR).
    #  bbox_merkez=(cx,cy) px, W,H goruntu px, bbox_boyut=(w,h) px, p=Cfg, dt.
    #  return: (throttle, pitch, roll, yaw) hepsi [-1,1].
    # ------------------------------------------------------------------
    def hesapla(self, bbox_merkez, W, H, bbox_boyut, p, dt=0.02):
        cx, cy = bbox_merkez
        W = float(W); H = float(H)
        ex = (cx - W / 2.0) / (W / 2.0) if W > 1 else 0.0     # + = sagda
        ey = (cy - H / 2.0) / (H / 2.0) if H > 1 else 0.0     # + = altta

        a = float(p.VIS_EMA)                                  # EMA yumusatma
        if self.ex_f is None:
            self.ex_f, self.ey_f = ex, ey
        else:
            self.ex_f = (1.0 - a) * self.ex_f + a * ex
            self.ey_f = (1.0 - a) * self.ey_f + a * ey

        w, h = bbox_boyut
        area = (w * h) / (W * H) if (W > 1 and H > 1) else 0.0  # bbox alan orani (yakinlik olcusu)
        self._son = (self.ex_f, self.ey_f, area)
        return self._komut(self.ex_f, self.ey_f, area, p)

    # ------------------------------------------------------------------
    #  Kayip (dead-reckon): yeni bbox yok -> son EMA yonuyle KISA sure devam.
    #  Suru asilinca AvciKontrol hover'a gecirir.
    # ------------------------------------------------------------------
    def kor_devam(self, p):
        if self._son is None:
            return 0.0, 0.0, 0.0, 0.0                          # hic tespit olmadi -> hover
        exf, eyf, area = self._son
        return self._komut(exf, eyf, area, p)

    # ------------------------------------------------------------------
    #  Ortak komut hesabi (angle-mode).
    # ------------------------------------------------------------------
    def _komut(self, exf, eyf, area, p):
        # YATAY ortala: burnu/govdeyi hedefe dondur (yaw hiz komutu)
        yaw = clamp(p.VIS_SIGN_YAW * p.VIS_K_YAW * exf, -1.0, 1.0)
        # DIKEY (LOS): bbox merkezi bir BAKIS YONU'dur; ufka gore gercek dikey aci:
        #   elev = TILT - atan(eyf * tan(vFOV/2))
        # (piksel ofseti aciya LINEER degil, tan-uzayinda baglidir). elev>0 ->
        # nokta ufkun ustunde -> TIRMAN (+thr); elev<0 -> ALCAL. elev=0 cizgisi
        # ey~0.43 (turuncu REF) = ayni-irtifa duz ucus (eski davranisla uyumlu).
        # tan(elev): dikey/ileri hiz orani -> tiklanan LOS boyunca ucus.
        elev = (math.radians(float(getattr(p, "VIS_TILT_DEG", 25.0)))
                - math.atan(eyf * math.tan(math.radians(float(getattr(p, "VIS_VFOV_YARIM_DEG", 47.2))))))
        throttle = clamp(p.VIS_K_VZ * math.tan(elev), -1.0, 1.0)
        roll = 0.0                                             # bu asamada kapali
        # ILERI yaklas: kapi YALNIZ YATAY hiza (|ex|) bakar — dikey hata ileriyi
        # BLOKLAMAZ (dikey, throttle ile eszamanli cozuluyor; eski eyd kosulu
        # "asagi tikla -> ileri kesiliyor" hatasina yol aciyordu). bbox buyudukce
        # (area -> AREA_STOP) yaklasma hizi 0'a iner.
        if abs(exf) < p.VIS_CENTER_GATE:
            fwd = max(0.0, p.VIS_K_FWD * (1.0 - area / max(p.VIS_AREA_STOP, 1e-6)))  # >=0: geri gitme YOK, sadece yavasla
            pitch = clamp(p.VIS_SIGN_PITCH * fwd, -p.VIS_FWD_MAX, p.VIS_FWD_MAX)
        else:
            pitch = 0.0                                        # once hizala, sonra yaklas
        return float(throttle), float(pitch), float(roll), float(yaw)

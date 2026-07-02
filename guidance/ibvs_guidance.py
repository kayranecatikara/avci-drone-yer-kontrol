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
  Kullanicinin niyeti "hedefi ortala + yaklas". Fizige gore dogru eslesme:
    yaw      <- ex            : hedefi YATAYDA ortala (burnu/govdeyi dondur)
    throttle <- (ey - EY_REF) : hedefi DIKEY REFERANSTA tut. SDK v2.2: kamera 25
                                derece YUKARI tilt'li -> ayni irtifadaki hedef
                                merkezin ALTINDA gorunur; referans cizgisi
                                (VIS_EY_REF~0.43) o noktadir. Tam merkeze ortalamak
                                drone'u hedefin ALTINA oturturdu (tilt telafisi).
    pitch    <- ILERI         : referansa yakinsa YAKLAS (bbox buyudukce yavasla)
    roll     = 0              : bu asamada kapali (agility/sonraki asama)
  (Kullanici spec'inde pitch<-ey yaziyordu; SDK'da pitch=YATAY oldugundan dikey
   ortalama throttle'a takaslandi. SIGN_* + canli tune ile dogrulanir.)

Rate-limit BURADA yapilmaz; AvciKontrol._send() zaten yapar (komut surekliligi).
Parametreler (SIGN_*, K_*, ...) disaridan `p` (Cfg) ile gelir -> canli tune bedava,
dongusel import yok (bu dosya ana_kontrol'u import ETMEZ).
"""


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
        # DIKEY: hedefi REFERANS cizgisinde tut (kamera 25 derece tilt telafisi).
        # eyd = referansa gore hata; referans=0 ise eski "tam merkeze ortala" davranisi.
        eyd = eyf - float(getattr(p, "VIS_EY_REF", 0.0))
        throttle = clamp(p.VIS_SIGN_VZ * p.VIS_K_VZ * eyd, -1.0, 1.0)
        roll = 0.0                                             # bu asamada kapali
        # ILERI yaklas: SADECE hedef makul hizalandiysa (kapi REFERANSA gore) ve bbox
        # kucukse (uzak). bbox buyudukce (area -> AREA_STOP) yaklasma hizi 0'a iner.
        if abs(exf) < p.VIS_CENTER_GATE and abs(eyd) < p.VIS_CENTER_GATE:
            fwd = max(0.0, p.VIS_K_FWD * (1.0 - area / max(p.VIS_AREA_STOP, 1e-6)))  # >=0: geri gitme YOK, sadece yavasla
            pitch = clamp(p.VIS_SIGN_PITCH * fwd, -p.VIS_FWD_MAX, p.VIS_FWD_MAX)
        else:
            pitch = 0.0                                        # once hizala, sonra yaklas
        return float(throttle), float(pitch), float(roll), float(yaw)

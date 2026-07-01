# -*- coding: utf-8 -*-
"""
================================================================================
 IBVS GUDUM  (Image-Based Visual Servoing) — DUZ / tek hata sinyali
================================================================================
Gorsel temas saglandiktan SONRA devreye giren duz IBVS guduum modulu.
Tek hata sinyali: best.pt bounding-box MERKEZININ goruntu merkezinden sapmasi.
PnP / derinlik / poz / ROLL bu asamada YOK — sadece bbox merkezi + bbox boyutu.

SAF MODUL: drone/SDK bagimliligi yok (yalniz math + dataclass) -> birim-test edilebilir.
Cikti angle-mode komut sozlugu; tum isaret/kazanc parametreleri IBVSConfig'te.

EKSEN ESLEMESI (SDK-dogru: throttle = DIKEY hiz, pitch = ILERI egim):
  ex = (cx - W/2)/(W/2)   # [-1..1] saga +
  ey = (cy - H/2)/(H/2)   # [-1..1] asagi +   (goruntu y ekseni ASAGI)
  yaw      = SIGN_YAW  * K_YAW  * ex     # yatay ortala (burnu cevir)
  roll     = SIGN_ROLL * K_ROLL * ex     # opsiyonel; K_ROLL=0 ile pasif
  throttle = SIGN_THR  * K_THR  * ey     # DIKEY ortala (tirman/alcal)
  pitch    = SIGN_PITCH * K_APPR*(1-doluluk) * gate
                                         # ILERI yaklasma; buyuk bbox = yakin = yavasla;
                                         # hedef merkezde DEGILSE gate~0 -> once ortala
Goruntu ekseni: sol-ust orijin, x saga, y ASAGI. Kamera DUZ (0 derece) -> tilt telafisi YOK.
================================================================================
"""
from dataclasses import dataclass
import math


def _clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x


def _deadband(x, db):
    return 0.0 if abs(x) < db else x


@dataclass
class IBVSConfig:
    """Tum IBVS parametreleri. Kalibrasyon = ilgili satiri tek tek degistir."""
    # --- ISARETLER (kalibrasyon = tek satir cevir) ---
    SIGN_YAW:   float = +1.0   # ex>0 (hedef sagda) -> saga don. SDK yaw isareti BELGESIZ: ilk ucusta dogrula.
    SIGN_ROLL:  float = +1.0   # SDK: roll +1 = saga
    SIGN_THR:   float = -1.0   # = -Z_SIGN. ey>0 (hedef altta) -> alcal (thr<0)
    SIGN_PITCH: float = +1.0   # SDK/PITCH_SIGN: +pitch = ileri
    # --- KAZANCLAR ---
    K_YAW:   float = 0.80
    K_ROLL:  float = 0.00      # opsiyonel; VARSAYILAN 0 (roll bu asamada pasif)
    K_THR:   float = 0.70
    K_APPR:  float = 0.50      # ileri yaklasma kazanci
    KD_YAW:  float = 0.00      # opsiyonel LOS-rate sonumleme (dt kullanir)
    # --- YUMUSATMA ---
    EMA_ALPHA: float = 0.40    # bbox merkezi EMA'si (inference karesi basina ilerler)
    # --- GATE / YAKLASMA MODULASYONU ---
    GATE_R:      float = 0.35  # radyal merkez hatasi; bu degerde yaklasma pitch'i -> 0
    DOLULUK_REF: float = 0.45  # bbox "yakin" sayildigi doluluk orani (yaklasma -> 0)
    DOLULUK_MODE: str  = "h"   # "h"=yukseklik orani (saglam) | "area"=alan orani
    APPR_FLOOR:  float = 0.00  # kilitliyken minimum ileri surunme tabani
    # --- DEADBAND / CLAMP ---
    DEADBAND:  float = 0.03    # |ex|,|ey| alti -> 0 (jitter onler)
    YAW_MAX:   float = 0.45
    ROLL_MAX:  float = 0.45
    THR_MAX:   float = 0.60
    PITCH_MAX: float = 0.60


class IBVSGuidance:
    """Duz IBVS guduum: bbox merkezi -> angle-mode komut.
    Durum: EMA-filtreli merkez (piksel) + onceki hata (LOS-rate icin)."""

    def __init__(self, cfg=None):
        self.cfg = cfg if cfg is not None else IBVSConfig()
        self.cx_s = None        # EMA-filtreli merkez (piksel)
        self.cy_s = None
        self.ex_prev = 0.0      # KD_YAW (LOS-rate) icin
        self.ey_prev = 0.0

    def reset(self, seed_cx=None, seed_cy=None):
        """GORSEL_GUDUM'a HER giriste cagrilir: bayat EMA merkezini temizle,
        ilk tespitle tohumla (seed varsa ilk komut sicramaz)."""
        self.cx_s = seed_cx
        self.cy_s = seed_cy
        self.ex_prev = 0.0
        self.ey_prev = 0.0

    def update(self, cx, cy, W, H, bbox_w, bbox_h, dt):
        """Bir inference karesi icin angle-mode komut uret.
          cx,cy   : bbox merkezi (piksel, kare koordinatinda)
          W,H     : kare boyutu (tespit['frame_w'/'frame_h'] — sabit kodlanmaz)
          bbox_w,bbox_h : kutu boyutu (piksel)
          dt      : son inference karesinden bu yana gecen sure (sn)
        Donus: {throttle,pitch,roll,yaw, ex,ey, doluluk,gate}."""
        cfg = self.cfg
        # Emniyet: gecersiz kare -> notr komut (hover/seviye)
        if W <= 0 or H <= 0:
            return {"throttle": 0.0, "pitch": 0.0, "roll": 0.0, "yaw": 0.0,
                    "ex": 0.0, "ey": 0.0, "doluluk": 0.0, "gate": 0.0}

        # 1) EMA merkez (tek-kare yanlis tespite karsi yumusatma)
        a = cfg.EMA_ALPHA
        if self.cx_s is None:
            self.cx_s, self.cy_s = float(cx), float(cy)
        else:
            self.cx_s = (1.0 - a) * self.cx_s + a * cx
            self.cy_s = (1.0 - a) * self.cy_s + a * cy

        # 2) Normalize hata [-1..1]  (sag +, asagi +)
        ex = (self.cx_s - W * 0.5) / (W * 0.5)
        ey = (self.cy_s - H * 0.5) / (H * 0.5)

        # 3) Deadband (yalniz KOMUTTA; donen ex/ey ham kalir -> overlay/CSV dogru gosterir)
        exd = _deadband(ex, cfg.DEADBAND)
        eyd = _deadband(ey, cfg.DEADBAND)

        # 4) Yatay ortala: yaw (+ opsiyonel LOS-rate sonumleme) ve roll
        d_ex = ((ex - self.ex_prev) / dt) if dt > 1e-6 else 0.0
        yaw = _clamp(cfg.SIGN_YAW * (cfg.K_YAW * exd + cfg.KD_YAW * d_ex),
                     -cfg.YAW_MAX, cfg.YAW_MAX)
        roll = _clamp(cfg.SIGN_ROLL * cfg.K_ROLL * exd, -cfg.ROLL_MAX, cfg.ROLL_MAX)

        # 5) Dikey ortala: throttle (throttle = DIKEY hiz komutu)
        throttle = _clamp(cfg.SIGN_THR * cfg.K_THR * eyd, -cfg.THR_MAX, cfg.THR_MAX)

        # 6) bbox doluluk (yaklasma hiz modulasyonu: buyuk bbox = yakin = yavasla)
        if cfg.DOLULUK_MODE == "area":
            doluluk = _clamp((bbox_w * bbox_h) / (W * H) / cfg.DOLULUK_REF, 0.0, 1.0)
        else:
            doluluk = _clamp((bbox_h / H) / cfg.DOLULUK_REF, 0.0, 1.0)

        # 7) gate: merkeze yakinken ileri git, kenardayken DUR ve ortala (yumusak gecis)
        r = math.hypot(ex, ey)
        gate = _clamp(1.0 - r / cfg.GATE_R, 0.0, 1.0) if cfg.GATE_R > 1e-6 else 1.0

        # 8) Ileri yaklasma (buyukluk >=0; isaret sonra uygulanir -> SIGN_PITCH=-1 de dogru calisir)
        appr_mag = _clamp((cfg.K_APPR * (1.0 - doluluk) + cfg.APPR_FLOOR) * gate,
                          0.0, cfg.PITCH_MAX)
        pitch = cfg.SIGN_PITCH * appr_mag

        self.ex_prev, self.ey_prev = ex, ey
        return {"throttle": throttle, "pitch": pitch, "roll": roll, "yaw": yaw,
                "ex": ex, "ey": ey, "doluluk": doluluk, "gate": gate}

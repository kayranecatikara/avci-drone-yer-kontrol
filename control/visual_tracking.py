# -*- coding: utf-8 -*-
"""
control/visual_tracking.py — GORSEL FAZ: IBVS

AMAÇ: Kontrol hatasını doğrudan görüntü uzayında tanımlama (pixel)

    menzil (R)   = RANGE_C_REF / kutu_boyutu
    kerteriz     = piksel + kendi IMU'muz
    yaw          = burnu kerterize çevir
    ileri hız    = kapanma hızı denetimi: v_yer = v_hedef_LOS + K*(R - TRAIL) -> profil TRAIL_RANGE_M'de sıfırlanır, araç kuyruğa oturur
    dikey hız    = hedefi kadraja sabit yükseklikte tut (cy -> cy_ref)
"""
import math
import time

from control.common import ConverterCfg, VelocityToStick, clamp, wrap_deg


# ==========================================================
#  KAMERA MODELİ (kalibrasyon referansı 1920x1080)
# ==========================================================
REF_W, REF_H = 1920.0, 1080.0
TILT_DEG = 26.50     # kamera ekseninin burna göre açısı
F_PX_REF = 540.4     # odak uzunluğu (px) @1920 genislik; fx = fy
RANGE_C_REF = 997.0  # px*m @1920;  R = RANGE_C_REF / kutu boyutu

def _scale(W):
    """Yakalanan kare genişliğinin kalibrasyon referansına oranı"""
    return float(W) / REF_W

def f_px(W):
    return F_PX_REF * _scale(W)

def range_m(box_px, W):
    """Kutu boyutundan menzil (m)"""
    if box_px <= 0:
        return None
    return (RANGE_C_REF * _scale(W)) / float(box_px)


def pixel_angle(cx_px, cy_px, W, H):
    """Kadraj konumundan kamera eksenine göre (yatay, dikey) açı (derece)"""
    f = f_px(W)
    return (math.degrees(math.atan((cx_px - W / 2.0) / f)),
            math.degrees(math.atan((H / 2.0 - cy_px) / f)))


def pixel_bearing(cx_px, cy_px, own_pitch_deg, own_roll_deg, W, H):
    """Kadraj konumundan gövdeden bağımsız kerteriz (azimut, yükseliş) derece"""
    horiz, vert = pixel_angle(cx_px, cy_px, W, H)
    elevation = vert + TILT_DEG + own_pitch_deg
    if own_roll_deg:
        r = math.radians(own_roll_deg)
        c, s = math.cos(r), math.sin(r)
        horiz, elevation = horiz * c - elevation * s, horiz * s + elevation * c
    return horiz, elevation


def bearing_pixel(azimuth_deg, elevation_deg, own_pitch_deg, own_roll_deg, W, H):
    """`pixel_bearing`in TAM TERSI: kerterizden kadraj konumu (cx, cy)"""
    # Sırası önemlidir. İleri dönüşümde önce kaydırır (dil + tilt + pitch) sonra roll ile döndürür.
    horiz, elev = azimuth_deg, elevation_deg
    if own_roll_deg:
        r = math.radians(own_roll_deg)
        c, s = math.cos(r), math.sin(r)
        horiz, elev = horiz * c + elev * s, -horiz * s + elev * c
    vert = elev - TILT_DEG - own_pitch_deg
    f = f_px(W)
    return (W / 2.0 + f * math.tan(math.radians(horiz)),
            H / 2.0 - f * math.tan(math.radians(vert)))


# ==========================================================
#  AYARLAR
# ==========================================================
class VisualCfg:
    # ============ GÜVENİLİRLİK ============
    CONF_MIN = 0.40     # Doğruluk değeri
    SIZE_MIN_PX = 8.0   # px @1920; kutu boyutu güvenilirliği
    RANGE_MAX_M = 50.0  # m; görsel devir sınırı
    RANGE_MIN_M = 3.0   # m; takip mesafesi
    STALE_S = 0.5       # s; tespitin geçerli sayıldığı süre

    # ============ DEVIR KİLİDİ ============
    HANDOFF_LOCK_S = 1.0  # s; kesintisiz görsel kanıt süresi
    HANDOFF_FRAMES = 10   # art arda geçerli kare sayısı
   
    # ============ İLERİ HIZ ============
    V_MAX = 28.0          # m/s; yatay hız tavanı
    V_MIN = 0.0           # m/s; yatay hız tabanı

    TRAIL_RANGE_M = 3.0   # m; kapanma hızının sıfırlandığı menzil
    K_CLOSE = 0.6         # 1/s; v_kapanma = K_CLOSE * (R - TRAIL_RANGE_M)
    V_CLOSE_MAX = 12.0    # m/s; azami kapanma hızı
    R_TAU = 0.20          # s; profilde kullanılan menzilin süzgeci
    V_TGT_TAU = 0.5       # s; hedef hızı kestirimin süzgeci

    # ============ YAW ============
    K_YAW = 1.0           # kerteriz -> burun hedefi
    KP_YAW_RATE = 3.0     # yaw hatasi (derece) -> yaw hizi (derece/s)
    YAW_RATE_MAX = ConverterCfg.YAW_RATE_MAX_DEG
    YAW_DEADBAND = 1.0    # derece; yaw düzeltmesi sınırı

    # ============ DİKEY: KADRAJ REGULASYONU ============
    K_CY = 0.014             # (m/s)/px @1080 yukseklik
    CY_REF = 470.0           # px @1080; hedefi merkezin üstünde tut
    VZ_CAP_VISUAL = 4.0      # m/s; dikey yumuşatma tavanı
    VZ_MAX_CLIMB = ConverterCfg.VZ_MAX_CLIMB
    VZ_MAX_DESCENT = ConverterCfg.VZ_MAX_DESCENT

    # ============ KUTU KÖPRÜSÜ ============
    BRIDGE_S = 1.0  # s;

# ==========================================================
#  KAPILAR
# ==========================================================
def aim_box(det, cfg=VisualCfg):
    """Bu tespit güdüme girebilir mi? Giremezse tespit yok sayılır."""
    if det is None:
        return None
    W = float(det.get("W", 0)); H = float(det.get("H", 0))
    if W <= 1 or H <= 1:
        return None
    if float(det.get("conf", 0.0)) < float(cfg.CONF_MIN):
        return None
    s = _scale(W)
    size = max(float(det.get("w", 0.0)), float(det.get("h", 0.0)))
    if size < float(cfg.SIZE_MIN_PX) * s:
        return None
    R = range_m(size, W)
    if R is None or R > float(cfg.RANGE_MAX_M) or R < float(cfg.RANGE_MIN_M):
        return None
    cx = float(det.get("cx", -1.0)); cy = float(det.get("cy", -1.0))
    if not (0 <= cx < W and 0 <= cy < H):
        return None
    return det

def is_stale(det, cfg=VisualCfg, now=None):
    """Tespit STALE_S'ten eski mi?"""
    if det is None or det.get("t") is None:
        return True
    now = time.perf_counter() if now is None else now
    return (now - float(det["t"])) > float(cfg.STALE_S)

# ==========================================================
#  GORSEL FAZ SÜRÜCÜSÜ
# ==========================================================
class VisualTracker:
    """IBVS gorsel güdüm"""

    def __init__(self, cfg=VisualCfg):
        self.cfg = cfg
        self.conv = VelocityToStick()
        self.reset()

    def reset(self):
        """Her yeni görsel faz başında çağrılır."""
        self._bridge = None     # son geçerli kutunun atalet yönü
        self._bridge_count = 0  # mekanizma sütunu
        self._R_f = None        # süzülmüş menzil (m)
        self._R_prev = None     # son ölçüm menzili
        self._dt_acc = 0.0      # iki menzil ölçümü arasi birikmiş süre (s)
        self._Rdot = 0.0        # menzil türevi (m/s)
        self._v_tgt_los = None  # hedefin LOS boyunca hızı (m/s)
        self._v_cmd = 0.0       # son ileri hız komutu
        self._tlm = {}

    # ------------------------------------------------------------------
    def _closing_speed(self, R, yaw_des_deg, own_vel_ms, dt, bridge):
        """Kapanma hızı denetimli ileri hız hesabı (m/s)"""
        p = self.cfg
        if R is None or dt <= 0.0:
            return self._v_cmd
        if bridge and self._v_tgt_los is not None:
            return self._v_cmd

        self._R_f = R if self._R_f is None else (
            self._R_f + (dt / (float(p.R_TAU) + dt)) * (R - self._R_f))

        self._dt_acc += dt
        h = math.radians(yaw_des_deg)
        own_los = own_vel_ms[0] * math.cos(h) + own_vel_ms[1] * math.sin(h)
        if self._R_prev is None:
            self._R_prev = R
            self._dt_acc = 0.0
            if self._v_tgt_los is None:
                self._v_tgt_los = clamp(own_los, 0.0, float(p.V_MAX))
        elif R != self._R_prev and self._dt_acc > 1e-6:
            self._Rdot = (R - self._R_prev) / self._dt_acc
            self._R_prev = R
            raw = own_los + self._Rdot
            b = self._dt_acc / (float(p.V_TGT_TAU) + self._dt_acc)
            self._v_tgt_los += b * (raw - self._v_tgt_los)
            self._v_tgt_los = clamp(self._v_tgt_los, 0.0, float(p.V_MAX))
            self._dt_acc = 0.0

        gap = max(0.0, self._R_f - float(p.TRAIL_RANGE_M))
        v_close = min(float(p.V_CLOSE_MAX), float(p.K_CLOSE) * gap)
        self._v_cmd = clamp(self._v_tgt_los + v_close,
                            float(p.V_MIN), float(p.V_MAX))
        return self._v_cmd

    # ------------------------------------------------------------------
    #  KUTU SEÇİMİ
    # ------------------------------------------------------------------
    def box(self, det, own_att_deg, t):
        """Güdüme verilecek kutuyu döndür"""
        roll, pitch, yaw = own_att_deg
        if det is not None:
            W = float(det["W"]); H = float(det["H"])
            az, el = pixel_bearing(float(det["cx"]), float(det["cy"]), pitch, roll, W, H)
            self._bridge = {"az": yaw + az, "el": el,
                            "w": float(det["w"]), "h": float(det["h"]),
                            "conf": float(det.get("conf", 0.0)),
                            "W": W, "H": H, "t": t}
            return det

        k = self._bridge
        if not k or float(self.cfg.BRIDGE_S) <= 0.0:
            return None
        if (t - k["t"]) > float(self.cfg.BRIDGE_S):
            return None
        az = wrap_deg(k["az"] - yaw)
        cx, cy = bearing_pixel(az, k["el"], pitch, roll, k["W"], k["H"])
        if not (0 <= cx < k["W"] and 0 <= cy < k["H"]):
            return None
        self._bridge_count += 1
        return {"cx": cx, "cy": cy, "w": k["w"], "h": k["h"],
                "conf": k["conf"], "W": k["W"], "H": k["H"], "t": k["t"],
                "bridge": True}

    # ------------------------------------------------------------------
    #  IBVS YASASI
    # ------------------------------------------------------------------
    def compute(self, det, own_att_deg, own_vel_ms, dt):
        """(thr, pitch, roll, yaw) çubuk konumu"""
        p = self.cfg
        own_roll, own_pitch, own_yaw = own_att_deg
        W = float(det["W"]); H = float(det["H"])
        cx = float(det["cx"]); cy = float(det["cy"])
        sh = float(H) / REF_H

        # --- 1) MENZİL ---
        size = max(float(det["w"]), float(det["h"]))
        R = range_m(size, W)

        # --- 2) KERTERİZ ---
        azimuth, _ = pixel_bearing(cx, cy, own_pitch, own_roll, W, H)

        # --- 3) YAW (Burnu hedefe çevirir) ---
        eps_yaw = 0.0 if abs(azimuth) < float(p.YAW_DEADBAND) else azimuth
        yaw_des = own_yaw + float(p.K_YAW) * eps_yaw
        yaw_rate = clamp(float(p.KP_YAW_RATE) * wrap_deg(yaw_des - own_yaw), -float(p.YAW_RATE_MAX), float(p.YAW_RATE_MAX))

        # --- 4) İLERİ HIZ: KAPANMA HIZI DENETİMİ ---
        v = self._closing_speed(R, yaw_des, own_vel_ms, dt, bridge=bool(det.get("bridge")))

        # --- 5) YATAY ---
        heading = math.radians(yaw_des)
        vx = v * math.cos(heading)
        vy = v * math.sin(heading)

        # --- 6) DİKEY ---
        cy_ref = float(p.CY_REF) * sh
        e_cy = cy - cy_ref  # + = hedef kadrajda ASAGIDA
        vz_raw = -(float(p.K_CY) / sh) * e_cy
        vz_up = clamp(vz_raw, -float(p.VZ_CAP_VISUAL), float(p.VZ_CAP_VISUAL))
        vz_up = clamp(vz_up, -float(p.VZ_MAX_DESCENT), float(p.VZ_MAX_CLIMB))

        # --- 7) HIZ -> ÇUBUK ---
        thr, pitch, roll, yaw = self.conv.convert((vx, vy, -vz_up), own_vel_ms, math.radians(own_yaw), yaw_rate)

        self._tlm = {
            "range_m": round(R, 2) if R else -1.0,
            "size_px": round(size, 1),
            "v_fwd": round(v, 2),
            "e_cy": round(e_cy, 1),
            "bridge": int(bool(det.get("bridge"))), "bridge_frames": self._bridge_count,
            "thr": round(thr, 3), "pitch": round(pitch, 3),
            "roll": round(roll, 3), "yaw": round(yaw, 3),
        }
        self._tlm.update(self.conv.diag)
        return float(thr), float(pitch), float(roll), float(yaw)

    def status(self):
        return dict(self._tlm)

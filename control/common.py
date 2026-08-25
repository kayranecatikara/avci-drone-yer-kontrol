# -*- coding: utf-8 -*-
"""
control/common.py — BIRIM SINIRI + HIZ->ÇUBUK ÇEVİRİCİSİ + TEK KOMUT KAPISI
"""
import math

CM_TO_M = 0.01    # cm   -> m
CMS_TO_MS = 0.01  # cm/s -> m/s

# ==========================================================
#  SKALER YARDIMCILAR
# ==========================================================
def clamp(x, lo, hi):
    """Değeri [lo, hi] aralığına alır."""
    return lo if x < lo else hi if x > hi else x


def wrap_deg(a):
    """Açıyı -180..+180 aralığına alır (derece)."""
    return (a + 180.0) % 360.0 - 180.0


def rate_limit(target, prev, max_delta):
    """Tik başı değişimi +-max_delta ile sınırlar."""
    return prev + clamp(target - prev, -max_delta, max_delta)


def world_to_body(ex, ey, yaw_rad, y_sign=None):
    """Dünya yatay vektörünü gövde çerçevesine çevirir -> (ileri, sağ)."""
    if y_sign is None:
        y_sign = ConverterCfg.Y_SIGN
    c, s = math.cos(yaw_rad), math.sin(yaw_rad)
    fwd = ex * c + ey * s
    right = y_sign * (-ex * s + ey * c)
    return fwd, right


# ==========================================================
#  BİRİM SINIRI — SDK (cm, derece)  ->  güdüm (m, m/s, derece)
# ==========================================================
class Telemetry:

    def __init__(self, drone):
        self.drone = drone

    def connected(self):
        return self.drone.is_connected()

    def position_m(self):
        """(x, y, z) metre"""
        x, y, z = self.drone.get_drone_location()
        return x * CM_TO_M, y * CM_TO_M, z * CM_TO_M

    def orientation_deg(self):
        """(roll, pitch, yaw) derece"""
        r, p, y = self.drone.get_drone_rotation()
        return float(r), float(p), float(y)

    def velocity_ms(self):
        """(vx, vy, vz) m/s"""
        try:
            vx, vy, vz = self.drone.get_telemetry()["drone"]["velocity"]
        except Exception:
            return 0.0, 0.0, 0.0
        return vx * CMS_TO_MS, vy * CMS_TO_MS, vz * CMS_TO_MS

    def altitude_m(self):
        return self.drone.get_drone_altitude() * CM_TO_M

    # -- hedef (bozuk GNSS) --------------------------------------------
    def target_raw_cm(self):
        return self.drone.get_target_location()


# ==========================================================
#  HIZ -> KUMANDA ÇUBUĞU ÇEVİRİCİSİ
# ==========================================================
class ConverterCfg:
    """
      yatay hız tavanı ....... 34.6 m/s
      tırmanma tavanı ........ +33.51 m/s
      alçalma tavanı ......... -6.95 m/s
      yatay ivme ............. 34-39 m/s²
      yatış zaman sabiti ..... 0.211 s
      ölü zaman .............. 46 ms
      yaw tavanı ............. 214 derece/s
    """

    # --- EKSEN ---
    Z_SIGN = -1.0  # NED
    Y_SIGN = -1.0

    # --- YATAY İÇ DÖNGÜ ---
    K_V = 1.5

    # --- İVME -> ÇUBUK ---
    MODEL = "direct"
    A_MAX = 34.0         # m/s²; tam çubuğun ivmesi
    MAX_BANK_DEG = 60.0

    POS_SLOPE = 32.64      # (m/s)/birim;  vz = 32.64*thr + 0.869   (thr > 0)
    POS_INTERCEPT = 0.869  # m/s
    NEG_SLOPE = 16.78      # (m/s)/birim;  vz = 16.78*thr + 9.835   (thr <= HOVER_THR)
    NEG_INTERCEPT = 9.835  # m/s
    HOVER_THR = -0.586     # vz=0 veren throttle
    HOLD_BAND = 0.05
    VZ_MAX_CLIMB = 33.51   # m/s;
    VZ_MAX_DESCENT = 6.95  # m/s;

    # --- YAW ---
    YAW_RATE_MAX_DEG = 120.0


class VelocityToStick:
    """Hız setpoint'ini kumanda çubuğuna çevirir."""

    def __init__(self, cfg=ConverterCfg):
        self.cfg = cfg
        self.diag = {}

    # ---------------- İvme -> Çubuk ----------------
    def _accel_stick(self, a):
        c = self.cfg
        if c.MODEL == "angle":
            return clamp(math.degrees(math.atan2(a, 9.81)) / c.MAX_BANK_DEG, -1.0, 1.0)
        return clamp(a / c.A_MAX, -1.0, 1.0)

    def vz_stick(self, vz_up):
        """İstenen dikey hızı (m/s) throttle'a çevirir."""
        c = self.cfg
        if abs(vz_up) < c.HOLD_BAND:
            return c.HOVER_THR
        if vz_up > 0.0:
            return clamp((vz_up - c.POS_INTERCEPT) / c.POS_SLOPE, 0.0, 1.0)
        return clamp((vz_up - c.NEG_INTERCEPT) / c.NEG_SLOPE, -1.0, c.HOVER_THR)

    # ---------------- Ana ----------------
    def convert(self, v_des, v_meas, yaw_rad, yaw_rate_des_deg=0.0):
        c = self.cfg
        vx_des, vy_des, vz_des_ned = v_des
        vx_meas, vy_meas, _vz_meas = v_meas

        # [1] iki hızı da göve çerçevesine al
        fwd_des, right_des = world_to_body(vx_des, vy_des, yaw_rad, c.Y_SIGN)
        fwd_meas, right_meas = world_to_body(vx_meas, vy_meas, yaw_rad, c.Y_SIGN)

        # [2] hız hatası -> istenen ivme
        a_fwd = c.K_V * (fwd_des - fwd_meas)
        a_right = c.K_V * (right_des - right_meas)

        # [3] ivme -> çubuk
        pitch = self._accel_stick(a_fwd)
        roll = self._accel_stick(a_right)

        # [4] dikey
        vz_up = c.Z_SIGN * vz_des_ned
        thr = self.vz_stick(vz_up)

        # [5] yaw
        yaw = clamp(yaw_rate_des_deg / c.YAW_RATE_MAX_DEG, -1.0, 1.0)

        # mekanizma sütunu
        self.diag = {
            "conv_fwd_err": fwd_des - fwd_meas,
            "conv_right_err": right_des - right_meas,
            "conv_a_fwd": a_fwd,
            "conv_a_right": a_right,
            "conv_vz_up": vz_up,
            "conv_sat": int(abs(pitch) >= 1.0 or abs(roll) >= 1.0 or abs(thr) >= 1.0),
        }
        return thr, pitch, roll, yaw


# ==========================================================
#  TEK KOMUT KAPISI
# ==========================================================
class CommandSender:
    """Oyuna giden Tek komut kapısı (throttle/pitch/roll/yaw + arm)"""

    MAX_DELTA = 0.15

    def __init__(self, drone):
        self.drone = drone
        self.prev = {"thr": 0.0, "pitch": 0.0, "roll": 0.0, "yaw": 0.0}

    def reset(self):
        self.prev = {"thr": 0.0, "pitch": 0.0, "roll": 0.0, "yaw": 0.0}

    def send(self, thr, pitch, roll, yaw):
        d = self.MAX_DELTA
        self.send_raw(rate_limit(thr, self.prev["thr"], d),
                      rate_limit(pitch, self.prev["pitch"], d),
                      rate_limit(roll, self.prev["roll"], d),
                      rate_limit(yaw, self.prev["yaw"], d))

    def send_raw(self, thr, pitch, roll, yaw):
        thr = clamp(float(thr), -1.0, 1.0)
        pitch = clamp(float(pitch), -1.0, 1.0)
        roll = clamp(float(roll), -1.0, 1.0)
        yaw = clamp(float(yaw), -1.0, 1.0)
        self.prev = {"thr": thr, "pitch": pitch, "roll": roll, "yaw": yaw}
        self.drone.set_control_surfaces(thr, pitch, roll, yaw, True)

    def loiter(self):
        """Hedef/veri yokken bekler. İrtifayı tutar, yatay komut vermez."""
        self.send(ConverterCfg.HOVER_THR, 0.0, 0.0, 0.0)

    def cut(self):
        """Motorları kapatır (görev durdurulur)"""
        self.prev = {"thr": 0.0, "pitch": 0.0, "roll": 0.0, "yaw": 0.0}
        self.drone.set_control_surfaces(0.0, 0.0, 0.0, 0.0, False)

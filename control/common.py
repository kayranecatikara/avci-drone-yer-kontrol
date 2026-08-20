# -*- coding: utf-8 -*-
"""
control/common.py — iki guduum hattinin (GPS + gorsel) paylastigi skaler
yardimcilar ve TEK komut cikisi.

KomutGonderici NEDEN ORTAK: faz degistiginde (GPS -> GORSEL veya geri) komut
sicramasin diye rate-limit "onceki komut" durumu TEK yerde tutulur. Iki fazin
ayri gonderici tutmasi, devir aninda prev'in sifirdan baslamasina ve gorunur
bir sarsintiya yol acardi.
"""
import math


def clamp(x, lo, hi):
    """Degeri [lo, hi] araligina alir."""
    return lo if x < lo else hi if x > hi else x


def wrap_pi(a):
    """Aciyi -pi..+pi araligina alir."""
    return (a + math.pi) % (2.0 * math.pi) - math.pi


def deadband(x, db):
    """Kucuk degerleri (|x| < db) sifirlar -> jitter onler."""
    return 0.0 if abs(x) < db else x


def rate_limit(target, prev, max_delta):
    """Tick basi degisimi +-max_delta ile sinirlar."""
    return prev + clamp(target - prev, -max_delta, max_delta)


def world_to_body(ex, ey, yaw_rad):
    """Dunya cercevesindeki yatay hatayi govde (ileri/sag) cercevesine cevirir."""
    c, s = math.cos(yaw_rad), math.sin(yaw_rad)
    e_fwd = ex * c + ey * s
    e_right = ex * s - ey * c
    return e_fwd, e_right


class KomutGonderici:
    """Oyuna giden TEK komut kapisi (throttle/pitch/roll/yaw + arm).

    gonder()  : rate-limit'li (tik basina en fazla MAX_DELTA_* degisim) — normal ucus.
    gonder_ham(): rate-limit YOK — kalkis gibi tam komutun aninda uygulanmasi
                  gereken durumlar icin (yumusatma tirmanisi geciktiriyordu).
    """

    MAX_DELTA_THR = 0.12
    MAX_DELTA_PITCH = 0.08
    MAX_DELTA_ROLL = 0.08
    MAX_DELTA_YAW = 0.08

    def __init__(self, drone):
        self.drone = drone
        self.prev = {"thr": 0.0, "pitch": 0.0, "roll": 0.0, "yaw": 0.0}

    def sifirla(self):
        self.prev = {"thr": 0.0, "pitch": 0.0, "roll": 0.0, "yaw": 0.0}

    def gonder(self, thr, pitch, roll, yaw):
        thr = rate_limit(thr, self.prev["thr"], self.MAX_DELTA_THR)
        pitch = rate_limit(pitch, self.prev["pitch"], self.MAX_DELTA_PITCH)
        roll = rate_limit(roll, self.prev["roll"], self.MAX_DELTA_ROLL)
        yaw = rate_limit(yaw, self.prev["yaw"], self.MAX_DELTA_YAW)
        self.gonder_ham(thr, pitch, roll, yaw)

    def gonder_ham(self, thr, pitch, roll, yaw):
        self.prev = {"thr": thr, "pitch": pitch, "roll": roll, "yaw": yaw}
        self.drone.set_control_surfaces(thr, pitch, roll, yaw, True)

    def loiter(self):
        """Komutlari yumusakca sifira cek (hedef yok / veri yok)."""
        self.gonder(0.0, 0.0, 0.0, 0.0)

    def kes(self):
        """Motorlari kes (gorev sonu / Ctrl+C)."""
        self.prev = {"thr": 0.0, "pitch": 0.0, "roll": 0.0, "yaw": 0.0}
        self.drone.set_control_surfaces(0.0, 0.0, 0.0, 0.0, False)

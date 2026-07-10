import math
import os
import time
import numpy as np

try:
    from fusion.gnss_filtre import GNSSFiltre
except ImportError:
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from fusion.gnss_filtre import GNSSFiltre


class GPSCfg:
    # Isaretler / eksen yonu
    ROT_IN_DEGREES = True
    PITCH_SIGN = +1.0
    ROLL_SIGN  = +1.0
    YAW_SIGN   = +1.0
    Z_SIGN     = +1.0

    # Dongu
    LOOP_HZ = 50.0
    DT = 1.0 / LOOP_HZ

    # Komut tavanlari
    PITCH_MAX = 0.75
    ROLL_MAX  = 0.75
    THR_UP    = 0.70
    THR_DN    = -1.00
    YAW_MAX   = 0.45

    # Tik basi degisim limiti
    MAX_DELTA_THR   = 0.12
    MAX_DELTA_PITCH = 0.08
    MAX_DELTA_ROLL  = 0.08
    MAX_DELTA_YAW   = 0.08

    # Burun -> hedef yaw
    KP_YAW = 1.3
    YAW_DEADBAND = math.radians(3)

    # Kalkis
    TAKEOFF = True
    TAKEOFF_ALT_AGL = 1000.0    # cm; tirmanilacak yukseklik
    TAKEOFF_THR = 0.6

    # Takip mesafesi
    APPROACH_STANDOFF   = 000.0 # cm; yatay
    APPROACH_ALT_OFFSET = 500.0 # cm; dikey

    # PID kazanclari
    KP_H = 0.00025
    KD_H = 0.00060
    KP_Z = 0.00040
    KD_Z = 0.00100
    KI_Z = 0.00020
    INT_Z_BAND = 2500.0         # cm; anti-windup bandi
    INT_Z_MAX  = 5000.0         # cm; integral tavani

    # Filtre / deadband
    DERIV_EMA = 0.20
    POS_DEADBAND = 150.0        # cm; yakinda yatay jitter'i onle

    # GNSS kesintisi (olu-hesap)
    DR_MAX_S = 30.0             # sn; kesintide ileri tahmin tavani

    # GNSS filtre
    GECIKME_SN = 1.0


def wrap_pi(a):         # Aciyi -pi..+pi araligina alir
    return (a + math.pi) % (2.0 * math.pi) - math.pi


def clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x


def deadband(x, db):    # |x|<db ise 0
    return 0.0 if abs(x) < db else x


def rate_limit(target, prev, max_delta):
    return prev + clamp(target - prev, -max_delta, max_delta)


def world_to_body(ex, ey, yaw_rad):         # Yatay hatayi govde (ileri/sag) cercevesine cevirir
    c, s = math.cos(yaw_rad), math.sin(yaw_rad)
    e_fwd   = ex * c + ey * s
    e_right = ex * s - ey * c
    return e_fwd, e_right


# GPS-yaklasma kontrolu: kalkis + PD/PID + olu-hesap
class GPSTakip:
    def __init__(self, drone):
        self.drone = drone
        self.filtre = None
        self.sifirla()

    # Yeni gorev icin durumu sifirla
    def sifirla(self):
        self.filtre = GNSSFiltre(gecikme_sn=GPSCfg.GECIKME_SN)

        # hedef kestirimi
        self.son_ham = None
        self.son_temiz = None
        self.son_z_anlik = None
        self.son_xy_anlik = None
        self.son_hiz = None
        self._fresh = False
        self._son_fresh_t = None

        # kontrol durumu
        self.prev = {'thr': 0.0, 'pitch': 0.0, 'roll': 0.0, 'yaw': 0.0}
        self.e_prev = None
        self.t_prev = None
        self.de = [0.0, 0.0, 0.0]    # EMA-filtreli hata turevi
        self._ez_int = 0.0           # dikey integral birikimi

        # kalkis durumu
        self._kalkis_done = (not GPSCfg.TAKEOFF)
        self._zemin_z = None

    def _send(self, thr, pitch, roll, yaw):
        thr   = rate_limit(thr,   self.prev['thr'],   GPSCfg.MAX_DELTA_THR)
        pitch = rate_limit(pitch, self.prev['pitch'], GPSCfg.MAX_DELTA_PITCH)
        roll  = rate_limit(roll,  self.prev['roll'],  GPSCfg.MAX_DELTA_ROLL)
        yaw   = rate_limit(yaw,   self.prev['yaw'],   GPSCfg.MAX_DELTA_YAW)
        self.prev = {'thr': thr, 'pitch': pitch, 'roll': roll, 'yaw': yaw}
        self.drone.set_control_surfaces(thr, pitch, roll, yaw, True)

    def _send_ham(self, thr, pitch, roll, yaw):
        self.prev = {'thr': thr, 'pitch': pitch, 'roll': roll, 'yaw': yaw}
        self.drone.set_control_surfaces(thr, pitch, roll, yaw, True)

    def _loiter(self):
        self._send(0.0, 0.0, 0.0, 0.0)

    # GNSS temizleme + hedef hiz/konum guncelle
    def _hedef_temizle(self):
        ham = self.drone.get_target_location()
        if ham == self.son_ham:
            self._fresh = False
            return self.son_temiz
        self.son_ham = ham
        sonuc = self.filtre.guncelle(ham[0], ham[1], ham[2])
        if sonuc is None:
            self._fresh = False
            return self.son_temiz
        self.son_temiz = np.array(sonuc)
        self._fresh = True
        durum = self.filtre.durum_gudum()
        self.son_hiz = None if durum is None else np.array(durum["vel"], float)
        self.son_z_anlik = float(self.son_temiz[2])
        self.son_xy_anlik = np.array([self.son_temiz[0], self.son_temiz[1]], float)
        return self.son_temiz

    # EMA-filtreli hata turevi
    def _derivative(self, e, t):
        if self.e_prev is None:
            self.e_prev, self.t_prev = e, t
            return self.de
        dt = t - self.t_prev
        if dt > 1e-3:
            a = GPSCfg.DERIV_EMA
            for i in range(3):
                raw = (e[i] - self.e_prev[i]) / dt
                self.de[i] = (1.0 - a) * self.de[i] + a * raw
            self.e_prev, self.t_prev = e, t
        return self.de

    # Kontrol adimi
    def adim(self):
        drone_pos = np.array(self.drone.get_drone_location())
        yaw_m = self.drone.get_drone_rotation()[2]
        drone_yaw = math.radians(yaw_m) if GPSCfg.ROT_IN_DEGREES else yaw_m
        t = time.perf_counter()
        self._hedef_temizle()
        
        if not self._kalkis_done:
            if self._zemin_z is None:
                self._zemin_z = float(drone_pos[2])
            hedef_z = self._zemin_z + GPSCfg.TAKEOFF_ALT_AGL
            if drone_pos[2] < hedef_z:
                self._send_ham(GPSCfg.TAKEOFF_THR, 0.0, 0.0, 0.0)
                return
            self._kalkis_done = True

        # -- Veri Kesintisi --
        if self._fresh:
            self._son_fresh_t = t
        est = self.son_temiz

        if est is None:
            self._loiter()
            return

        # -- Dead-reckoning süresi --
        dr_dt = 0.0
        if (not self._fresh) and self._son_fresh_t is not None:
            dr_dt = clamp(t - self._son_fresh_t, 0.0, GPSCfg.DR_MAX_S)
        vhx = float(self.son_hiz[0]) if self.son_hiz is not None else 0.0
        vhy = float(self.son_hiz[1]) if self.son_hiz is not None else 0.0
        vhz = float(self.son_hiz[2]) if self.son_hiz is not None else 0.0

        # -- Dikey nisan --
        z_hedef = (self.son_z_anlik + vhz * dr_dt) if self.son_z_anlik is not None else float(est[2])
        z_ref = z_hedef - GPSCfg.APPROACH_ALT_OFFSET
        ez = float(z_ref - drone_pos[2])

        # -- Yatay nisan --
        if self.son_xy_anlik is not None:
            tx = float(self.son_xy_anlik[0]) + vhx * dr_dt
            ty = float(self.son_xy_anlik[1]) + vhy * dr_dt
        else:
            tx, ty = float(est[0]), float(est[1])
        ex = tx - float(drone_pos[0])
        ey = ty - float(drone_pos[1])
        d_h = math.hypot(ex, ey)

        # -- Takip mesafesi --
        if d_h > 1e-6:
            _ux, _uy = ex / d_h, ey / d_h
            _dcmd = d_h - GPSCfg.APPROACH_STANDOFF
            ex_cmd, ey_cmd = _ux * _dcmd, _uy * _dcmd
        else:
            ex_cmd = ey_cmd = 0.0

        # -- Turev (EMA) + Yatay PD
        de = self._derivative((ex_cmd, ey_cmd, ez), t)
        e_fwd, e_right = world_to_body(ex_cmd, ey_cmd, drone_yaw)
        de_fwd, de_right = world_to_body(de[0], de[1], drone_yaw)
        pitch_raw = GPSCfg.PITCH_SIGN * (GPSCfg.KP_H * e_fwd   + GPSCfg.KD_H * de_fwd)
        roll_raw  = GPSCfg.ROLL_SIGN  * (GPSCfg.KP_H * e_right + GPSCfg.KD_H * de_right)
        pitch_raw = clamp(pitch_raw, -GPSCfg.PITCH_MAX, GPSCfg.PITCH_MAX)
        roll_raw  = clamp(roll_raw,  -GPSCfg.ROLL_MAX,  GPSCfg.ROLL_MAX)

        # -- Dikey-Yatay ayristirma
        if ez < 0.0:
            alc = clamp(1.0 + ez / 800.0, 0.15, 1.0)
            pitch_raw *= alc
            roll_raw  *= alc

        # -- Irtifa PID --
        if abs(ez) < GPSCfg.INT_Z_BAND:
            self._ez_int = clamp(self._ez_int + ez * GPSCfg.DT, -GPSCfg.INT_Z_MAX, GPSCfg.INT_Z_MAX)
        else:
            self._ez_int = 0.0
        thr_raw = clamp(GPSCfg.Z_SIGN * (GPSCfg.KP_Z * ez + GPSCfg.KI_Z * self._ez_int + GPSCfg.KD_Z * de[2]),
                        GPSCfg.THR_DN, GPSCfg.THR_UP)

        # -- Yaw (Burnu hedefe cevir)
        bearing = math.atan2(ey, ex)
        yaw_err = deadband(wrap_pi(bearing - drone_yaw), GPSCfg.YAW_DEADBAND)
        yaw_raw = GPSCfg.YAW_SIGN * clamp(GPSCfg.KP_YAW * yaw_err, -GPSCfg.YAW_MAX, GPSCfg.YAW_MAX)

        # -- Deadband --
        if d_h < GPSCfg.POS_DEADBAND:
            pitch_raw = 0.0
            roll_raw = 0.0

        self._send(thr_raw, pitch_raw, roll_raw, yaw_raw)
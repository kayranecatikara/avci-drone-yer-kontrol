"""
Avci Drone - Gorev FSM + Kilit Mantigi  [SAF-GPS MODU]
======================================================
Strateji: Goruntu isleme (kamera/FOV/in_frame) AKTIF DEGIL. Simulasyonun verdigi
yuksek dogruluklu 3D GPS konumu kullaniliyor. GPS varsa dron HIC BEKLEMEDEN
TRACK/APN'e gecip hedefe ucar; throttle hedefin Z'sine gore dinamik (avci_guidance).

LockEvaluator   : SAF-GPS kilit -> hedef lock_radius icinde ise; 10 s pencere kumulatif
MissionFSM      : SEARCH -> (GPS var) -> TRACK -> (yakin) -> ENGAGE -> RETURN/ABORT
MissionManager  : ana donguden tek update(); imza degismedi (avci_main uyumlu)
CameraModel     : PASIF - CV (YOLO/keypoint) hazir olunca geri devreye girer; saklandi.
"""

import numpy as np
from collections import deque


# --------------------------------------------------------------------------- yardimci
def _Rz(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])

def _Ry(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])

def _Rx(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


# =========================================================================== KAMERA (PASIF)
class CameraModel:
    """PASIF - Saf-GPS modunda KULLANILMIYOR. CV (YOLO/keypoint) hazir olunca
    kilit/projeksiyon icin geri devreye girer. Govde: x ileri, y sol, z yukari;
    kamera govdeden tilt kadar YUKARI bakar."""

    def __init__(self, hfov_deg=105.0, aspect=4/3, tilt_deg=35.0,
                 wingspan=1.718, u_sign=1.0):
        self.hfov = np.radians(hfov_deg)
        self.vfov = self.hfov / aspect              # 4:3 -> ~78.8 deg
        self.tilt = np.radians(tilt_deg)
        self.wingspan = wingspan
        self.u_sign = u_sign                        # goruntu yatay yon isareti (kalibre)

    def project(self, tgt_pos, own_pos, own_euler):
        R = np.asarray(tgt_pos, float) - np.asarray(own_pos, float)
        rng = np.linalg.norm(R)
        if rng < 1e-6:
            rng = 1e-6
        roll, pitch, yaw = own_euler
        Rwb = _Rz(yaw) @ _Ry(pitch) @ _Rx(roll)     # body -> world
        v = Rwb.T @ (R / rng)                        # LOS govde cercevesinde
        horiz = np.hypot(v[0], v[1])
        az = np.arctan2(v[1], v[0])                  # govde azimut (+ sol)
        el_body = np.arctan2(v[2], horiz)            # govde yukselis (+ yukari)
        el_cam = el_body - self.tilt                 # kamera 35 yukari -> kompanze
        u = 0.5 - self.u_sign * az / self.hfov       # 0=sol,1=sag
        vv = 0.5 - el_cam / self.vfov                # 0=ust,1=alt
        in_frame = (v[0] > 0 and abs(az) <= self.hfov / 2
                    and abs(el_cam) <= self.vfov / 2)
        coverage = (self.wingspan / rng) / self.hfov  # lineer genislik orani
        return {"u": u, "v": vv, "coverage": coverage, "in_frame": in_frame,
                "range": rng, "az_deg": np.degrees(az), "el_cam_deg": np.degrees(el_cam)}


# =========================================================================== KILIT (SAF-GPS)
class LockEvaluator:
    """SAF-GPS kilit: hedef lock_radius (m) icindeyse 'kilit'. 10 s pencerede kumulatif sure.
    (CV hazir olunca sartname 6.1.4 kamera-tabanli kilit geri gelir; CameraModel saklandi.)
    NOT: Bu GPS-proxy kilittir; gercek +400 hakem kriterleri kamera-tabanlidir."""

    def __init__(self, dt=0.02, lock_radius=20.0,
                 window_s=10.0, required_s=5.0, tolerance_s=0.20):
        self.dt = dt
        self.lock_radius = lock_radius
        self.window_s = window_s
        self.required_s = required_s
        self.tol = tolerance_s
        self.win = deque()                # (t, valid)
        self.continuous = 0.0
        self.last_valid_t = -1e9
        self.secured = False              # kumulatif >=5 s (latch)
        self.secured_t = None

    def update(self, rng, t, measured=True):
        valid = bool(measured and rng <= self.lock_radius)

        # 10 s kayan pencere -> kumulatif kilit suresi
        self.win.append((t, valid))
        while self.win and self.win[0][0] < t - self.window_s:
            self.win.popleft()
        cumulative = sum(self.dt for (_, vd) in self.win if vd)

        # surekli kilit - tolerans kadar bosluga musamaha
        if valid:
            self.continuous += self.dt
            self.last_valid_t = t
        elif t - self.last_valid_t <= self.tol:
            pass
        else:
            self.continuous = 0.0

        newly = False
        if not self.secured and cumulative >= self.required_s:
            self.secured = True
            self.secured_t = t
            newly = True                  # +400 paketi bu karede raporlanmali

        return {"valid": valid, "cumulative": cumulative,
                "continuous": self.continuous, "secured": self.secured,
                "lock_report": newly}


# =========================================================================== FSM (SAF-GPS)
class MissionFSM:
    """SAF-GPS FSM: GPS varsa ANINDA TRACK (FOV/bekleme yok). Yakinlik tabanli ENGAGE/fire.
    Jam'de (GPS yok) kisa sure coast (TRACK'te kalir); uzun kayipta RETURN, GPS donunce TRACK."""

    def __init__(self, dt=0.02, engage_tgo=3.5, fire_tgo=1.2,
                 lost_limit_s=2.0, grace_s=3.0):
        self.dt = dt
        self.engage_tgo = engage_tgo
        self.fire_tgo = fire_tgo
        self.lost_limit = lost_limit_s
        self.grace_s = grace_s                # TRACK girisinden sonra ENGAGE'e gecmeden once
        self.state = "SEARCH"                 # beklenecek sure (startup stabilizasyon kilidi)
        self.lost_timer = 0.0
        self.track_timer = 0.0                # TRACK'te gecirilen sure (grace icin)

    def _go(self, s):
        if s != self.state:
            self.state = s
            if s == "TRACK":
                self.track_timer = 0.0        # TRACK'e her giriste grace sayacini sifirla

    def update(self, rng, t_go, lock, measured=True, los_rate=0.0, boundary_imminent=False):
        self.lost_timer = 0.0 if measured else self.lost_timer + self.dt
        if self.state == "TRACK":
            self.track_timer += self.dt
        fire = False

        if self.state == "SEARCH":
            if measured:                          # GPS VAR -> ANINDA TRACK (bekleme yok)
                self._go("TRACK")

        elif self.state == "TRACK":
            if self.lost_timer > self.lost_limit:
                self._go("RETURN")
            # GRACE KILIDI: ilk grace_s saniye ENGAGE YOK (sahte t_go spike'i dalisi engellenir)
            elif self.track_timer >= self.grace_s and t_go < self.engage_tgo:
                self._go("ENGAGE")

        elif self.state == "ENGAGE":
            if boundary_imminent:
                self._go("ABORT")
            elif self.lost_timer > self.lost_limit:
                self._go("RETURN")
            elif t_go < self.fire_tgo:            # cok yakin -> onleme commit
                fire = True

        elif self.state == "RETURN":
            if measured:                          # hedef GPS geri geldi -> tekrar takip
                self._go("TRACK")

        mode = {"SEARCH": "SEARCH_PATTERN", "TRACK": "APN", "ENGAGE": "APN",
                "RETURN": "RTL", "ABORT": "SAFE"}[self.state]
        return {"state": self.state, "fire": fire, "control_mode": mode}


# =========================================================================== UST SARMAL (SAF-GPS)
class MissionManager:
    """Ana donguden tek cagri. Imza avci_main ile UYUMLU (own_euler/confidence yok sayilir).
    Kamera projeksiyonu YOK -> menzil/t_go dogrudan GPS'ten."""

    def __init__(self, dt=0.02, lock_radius=20.0, grace_s=3.0,
                 engage_tgo=3.5, fire_tgo=1.2, lost_limit_s=2.0):
        self.dt = dt
        self.lock = LockEvaluator(dt=dt, lock_radius=lock_radius)
        self.fsm = MissionFSM(dt=dt, engage_tgo=engage_tgo, fire_tgo=fire_tgo,
                              lost_limit_s=lost_limit_s, grace_s=grace_s)

    def update(self, t, own_pos, own_euler, tgt_pos,
               closing_speed, measured=True, confidence=1.0,
               los_rate=0.0, boundary_imminent=False):
        own_pos = np.asarray(own_pos, float)
        tgt_pos = np.asarray(tgt_pos, float)
        rng = float(np.linalg.norm(tgt_pos - own_pos))
        t_go = rng / closing_speed if closing_speed > 1e-3 else np.inf
        lock = self.lock.update(rng, t, measured=measured)
        fsm = self.fsm.update(rng, t_go, lock, measured=measured,
                              los_rate=los_rate, boundary_imminent=boundary_imminent)
        proj = {"range": rng, "coverage": 0.0, "in_frame": True}  # uyumluluk (kamera pasif)
        return {"proj": proj, "lock": lock, "t_go": t_go, **fsm}


def _wrap(a):
    return (a + np.pi) % (2 * np.pi) - np.pi


# =========================================================================== TARAMA
class SearchPattern:
    """
    Kapsama taramasi (SEARCH durumu davranisi).
    Seviye ucus + dwell-sinirli yaw supurme (azimut) + tam turda irtifa katmani atlama.
    Kamera 35 yukari + genis VFOV -> tek pitch genis yukselis bandi kapsar; asil DOF yaw.
    Dwell siniri: hedef HFOV'da >=dwell_s kalmali ki SEARCH->TRACK kararliligi (1.5 s) yakalansin.
    """
    def __init__(self, dt=0.02, hover_throttle=0.5, max_yaw_rate_deg=120.0,
                 hfov_deg=105.0, dwell_s=1.5, scan_rate_deg=30.0,
                 alt_layers=(15.0, 25.0, 35.0), alt_kp=0.03,
                 mode="spin", sector_deg=(-90.0, 90.0)):
        self.dt = dt
        self.hover = hover_throttle
        self.max_yaw_rate = max_yaw_rate_deg
        self.scan_rate = min(scan_rate_deg, hfov_deg / dwell_s)   # dwell siniri
        self.alt_layers = list(alt_layers)
        self.alt_kp = alt_kp
        self.mode = mode
        self.sector = np.radians(sector_deg)
        self.reset()

    def reset(self):
        self.layer_idx = 0
        self.swept = 0.0
        self.dir = 1.0
        self.prev_yaw = None

    def update(self, own_pos, own_euler):
        yaw = own_euler[2]
        if self.prev_yaw is not None:
            self.swept += abs(_wrap(yaw - self.prev_yaw))
        self.prev_yaw = yaw
        if self.swept >= 2 * np.pi:                  # tam azimut tarandi -> sonraki katman
            self.swept = 0.0
            self.layer_idx = (self.layer_idx + 1) % len(self.alt_layers)

        rate = self.scan_rate
        if self.mode == "sector":
            if yaw >= self.sector[1]:
                self.dir = -1.0
            elif yaw <= self.sector[0]:
                self.dir = 1.0
            rate *= self.dir
        yaw_cmd = float(np.clip(rate / self.max_yaw_rate, -1.0, 1.0))

        alt_target = self.alt_layers[self.layer_idx]
        throttle = float(np.clip(self.hover + self.alt_kp * (alt_target - own_pos[2]), 0.0, 1.0))
        return {"roll": 0.0, "pitch": 0.0, "yaw": yaw_cmd, "throttle": throttle,
                "layer": self.layer_idx, "alt_target": alt_target,
                "scan_rate_deg": self.scan_rate}


# =========================================================================== DEMO
if __name__ == "__main__":
    # Senaryo: hedef 120 m'den yaklasir; avci ~13 m'de PACE eder (kilit bankalar),
    # 5 s kumulatif sonra terminal kapanis -> ENGAGE -> fire.
    dt = 0.02
    mgr = MissionManager(dt=dt)
    own_euler = np.array([0.0, 0.0, 0.0])           # seviye; hedef kamera ekseninde
    own_pos = np.array([0.0, 0.0, 20.0])
    boresight = np.array([np.cos(np.radians(35)), 0.0, np.sin(np.radians(35))])

    def range_at(t):
        if t < 6.0:    return 120.0 - (120.0 - 13.0) * (t / 6.0)   # 120->13 yaklasma
        if t < 13.0:   return 13.0 + 0.8 * np.sin(t - 6.0)         # ~12-14 pace (kilit)
        return max(4.0, 13.0 - 9.0 * (t - 13.0))                   # terminal kapanis

    prev_state = None
    secured_print = fired = False
    for k in range(900):                 # 18 s
        t = k * dt
        rng = range_at(t)
        tgt_pos = own_pos + rng * boresight          # kamera ekseninde -> merkezli
        vc = (range_at(t) - range_at(t + dt)) / dt   # kapanis hizi
        out = mgr.update(t, own_pos, own_euler, tgt_pos, max(vc, 0.0))
        s, lk = out["state"], out["lock"]
        if s != prev_state:
            print(f"t={t:5.2f}s  STATE -> {s:7s} | menzil={rng:5.1f}m "
                  f"t_go={out['t_go']:.2f}s")
            prev_state = s
        if lk["lock_report"] and not secured_print:
            print(f"t={t:5.2f}s  >>> GPS-KILIT BANKLANDI (kumulatif {lk['cumulative']:.1f}s)")
            secured_print = True
        if out["fire"] and not fired:
            print(f"t={t:5.2f}s  >>> FIRE / ONLEME COMMIT (t_go={out['t_go']:.2f}, "
                  f"surekli kilit={lk['continuous']:.1f}s)")
            fired = True
    print("FSM/kilit demo tamam.")

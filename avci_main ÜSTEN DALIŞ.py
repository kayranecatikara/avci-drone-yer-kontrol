"""
Avci Drone - Ince Ana Dongu (50 Hz)  [FSM + kilit + sunucu telemetri entegre]
=============================================================================
Akis: SDK oku -> kendi durum -> IMM-EKF -> APN geometri -> MissionManager (FSM/kilit)
      -> komutu duruma gore kapila -> SDK'ya bas -> sunucuya telemetri

'>>> SDK'    : komite SDK'sina gore doldur (SDKAdapter)
'>>> SUNUCU' : hakem sunucusu protokolune gore doldur (ServerLink)
"""

import time
import numpy as np
from avci_guidance import APN_Guidance, IMMEKF_Filter
from avci_fsm import MissionManager, SearchPattern

# --------------------------------------------------------------------------- CONFIG
RATE_HZ = 50.0
DT = 1.0 / RATE_HZ
HOVER_THROTTLE = 0.58
CAM_TILT_DEG = 35.0
MAX_YAW_RATE_DEG = 120.0
TELEMETRY_HZ = 2.0                         # sunucuya periyodik (1-5 Hz araliginda)
SEARCH_YAW_RATE = 0.25                     # tarama tarama yaw (normalize)

# Kendi attitude formati (drone_sdk: rotation (Roll,Pitch,Yaw) DERECE - Unreal)
OWN_ATT_DEGREES = True                     # drone_sdk derece veriyor
OWN_ATT_RPY_ORDER = (0, 1, 2)              # SDK: (Roll, Pitch, Yaw)
OWN_ATT_QUAT_WXYZ = True                   # (kullanilmiyor; SDK euler veriyor)


def _valid(v, n):
    if v is None:
        return False
    a = np.asarray(v, float).ravel()
    return a.shape[0] == n and np.all(np.isfinite(a))


def euler_from_attitude(att):
    """SDK attitude -> [roll,pitch,yaw] (radyan). att: skaler|euler(3)|quat(4)|None."""
    if att is None:
        return None
    a = np.asarray(att, float).ravel()
    if a.size == 1:
        return np.array([0.0, 0.0, float(a[0]) * (np.pi/180 if OWN_ATT_DEGREES else 1.0)])
    if a.size == 3:
        ri, pi, yi = OWN_ATT_RPY_ORDER
        e = np.array([a[ri], a[pi], a[yi]], float)
        return np.radians(e) if OWN_ATT_DEGREES else e
    if a.size == 4:
        w, x, y, z = (a[0], a[1], a[2], a[3]) if OWN_ATT_QUAT_WXYZ else (a[3], a[0], a[1], a[2])
        roll = np.arctan2(2*(w*x + y*z), 1 - 2*(x*x + y*y))
        pitch = np.arcsin(np.clip(2*(w*y - z*x), -1, 1))
        yaw = np.arctan2(2*(w*z + x*y), 1 - 2*(y*y + z*z))
        return np.array([roll, pitch, yaw])
    return None


# =========================================================================== SDK ADAPTER
class SDKAdapter:
    """
    drone_sdk (Drone of War) sarmali. Kullanim:
        import drone_sdk
        drone_sdk.connect(); 
        io = SDKAdapter(drone_sdk); io.arm(True)
        loop = InterceptorLoop(io); loop.run()

    SDK eslemesi:
      get_drone_location/rotation  -> kendi pos (cm->m) + euler (derece->rad)
      get_target_location          -> hedef pos (cm->m)
      get_target_speed             -> SKALER cm/s (yon yok) -> hiz VEKTORU konumdan turetilir
      set_control_surfaces         -> (throttle, pitch, roll, yaw, arm) tek TCP satiri
      is_connected                 -> dongu kosulu

    SIM'DE DOGRULA:
      * POS_SCALE: bilinen bir mesafe metre mi cm mi? (cm ise 0.01 dogru)
      * Donus yonu: avci hedefe DOGRU mu donuyor? Degilse APN sign_yaw / CameraModel u_sign flip.
      * OWN_ATT_DEGREES gercekten derece mi (Unreal evet).
    """
    POS_SCALE = 0.01      # Unreal cm -> m

    def __init__(self, sdk, dt=DT, armed=False, jam_check=None):
        self.sdk = sdk
        self.dt = dt
        self.armed = armed
        # jam_check: kendi GNSS jammer arayuzunuz. Cagrilabilir -> True ise jam aktif:
        # hedef/own konumu KESILIR (z=None) -> EKF coast eder. Or: SDKAdapter(drone, jam_check=jammer.is_active)
        self.jam_check = jam_check

    def _jamming(self):
        try:
            return bool(self.jam_check()) if self.jam_check else False
        except Exception:
            return False

    # --- baglanti / arm ---
    def connect(self, host='127.0.0.1', port=12345):
        return self.sdk.connect(host, port)

    def arm(self, state=True):
        self.armed = state
        self.sdk.set_arm(state)

    @staticmethod
    def _try(fn):
        try:
            return fn()
        except Exception:
            return None

    # --- telemetri ---
    def read_target(self):
        """POS-ONLY: yalniz hedef konumu (m) doner; jam/gecersiz -> None (EKF coast eder).
        Hedef HIZI artik SDK'dan UYDURULMAZ -> EKF konumdan kestirir (gecikme yok)."""
        if self._jamming():
            return None                        # jammer aktif -> veri kesik -> coast
        pos = self._try(self.sdk.get_target_location)
        if not _valid(pos, 3):
            return None
        return np.asarray(pos, float) * self.POS_SCALE             # cm -> m

    def read_own(self):
        """Konum (m) + euler (rad). Jam'de konum None -> OwnStateEstimator dead-reckon eder;
        attitude (IMU) jam'den etkilenmez, okunmaya devam."""
        rot = self._try(self.sdk.get_drone_rotation)               # (Roll,Pitch,Yaw) derece (IMU)
        euler = euler_from_attitude(rot)                           # derece -> rad
        if self._jamming():
            return None, None, euler           # konum jam -> dead-reckon; tutum gecerli
        pos = self._try(self.sdk.get_drone_location)
        pos = np.asarray(pos, float) * self.POS_SCALE if _valid(pos, 3) else None
        return pos, None, euler         # own hiz vektoru OwnStateEstimator'da konumdan turetilir

    # --- kontrol ---
    def send_command(self, roll, pitch, yaw, throttle):
        # SDK parametre sirasi: (throttle, pitch, roll, yaw, arm)
        self.sdk.set_control_surfaces(throttle, pitch, roll, yaw, self.armed)

    def is_running(self):
        return self.sdk.is_connected()


# =========================================================================== SUNUCU
class ServerLink:
    """Hakem sunucusu baglantisi. Sistem saati zaman damgasiyla GPS/irtifa/kilit gonderir."""
    def __init__(self):
        self.lock_count = 0
        self.tlm_count = 0

    def send_lock(self, ts, payload):
        self.lock_count += 1
        # >>> SUNUCU: kilit (+400) paketini POST/socket ile gonder; payload icinde
        #     timestamp, own GPS, hedef konum, kilit suresi. Yanlis paket -> ceza.

    def send_telemetry(self, ts, payload):
        self.tlm_count += 1
        # >>> SUNUCU: periyodik GPS/irtifa/durum paketi (1-5 Hz)


# =========================================================================== KENDI DURUM
class OwnStateEstimator:
    def __init__(self, dt, vel_lp=0.3, move_thresh=1.0):
        self.dt = dt
        self.vel_lp = vel_lp
        self.move_thresh = move_thresh
        self.pos = None
        self.vel = np.zeros(3)
        self.euler = np.zeros(3)
        self.prev_pos = None

    def update(self, raw_pos, raw_vel, raw_euler, cmd_yaw_rate=0.0):
        if raw_pos is not None:
            self.pos = raw_pos.copy()
        elif self.pos is not None:
            self.pos = self.pos + self.vel * self.dt
        if raw_vel is not None:
            self.vel = raw_vel.copy()
        elif self.pos is not None and self.prev_pos is not None:
            d = (self.pos - self.prev_pos) / self.dt
            self.vel = (1 - self.vel_lp) * self.vel + self.vel_lp * d
        if raw_euler is not None:
            self.euler = raw_euler.copy()
        else:
            # SDK attitude yok: roll/pitch=0, yaw heading/komuttan
            if np.hypot(self.vel[0], self.vel[1]) > self.move_thresh:
                yaw = np.arctan2(self.vel[1], self.vel[0])
            else:
                yaw = self.euler[2] + cmd_yaw_rate * self.dt
            self.euler = np.array([0.0, 0.0, yaw])
        self.prev_pos = None if self.pos is None else self.pos.copy()
        return self.pos, self.vel, self.euler


# =========================================================================== ANA DONGU
class InterceptorLoop:
    def __init__(self, adapter, server=None, dt=DT,
                 # --- TEK MERKEZ TUNING (saha kalibrasyonu buradan) ---
                 sign_pitch=-1.0, sign_yaw=1.0, sign_roll=1.0,  # Unreal yon invertorleri
                 kp_alt=1.0, kd_alt=2.0,                        # dinamik irtifa PD kazanclari
                 grace_s=3.0,                                   # TRACK->ENGAGE guvenlik kilidi (s)
                 max_closing=45.0,                              # closing_speed tavani (m/s)
                 lock_radius=20.0,                              # GPS-kilit yaricapi (m)
                 debug_mode="full"):                            # "full"|"hover"|"vertical"|"horizontal"
        self.io = adapter
        self.server = server or ServerLink()
        self.dt = dt
        self.debug_mode = debug_mode                            # izolasyon: APN mi dikey gaz mi?
        self._hold_alt = None                                   # hover modunda yakalanan irtifa
        self.ekf = IMMEKF_Filter(dt=dt)
        self.apn = APN_Guidance(dt=dt, cam_tilt_deg=CAM_TILT_DEG,
                                hover_throttle=HOVER_THROTTLE, max_yaw_rate_deg=MAX_YAW_RATE_DEG,
                                kp_alt=kp_alt, kd_alt=kd_alt, max_closing=max_closing,
                                sign_pitch=sign_pitch, sign_yaw=sign_yaw, sign_roll=sign_roll)
        self.own = OwnStateEstimator(dt=dt)
        self.mission = MissionManager(dt=dt, lock_radius=lock_radius, grace_s=grace_s)
        self.search = SearchPattern(dt=dt, hover_throttle=HOVER_THROTTLE,
                                    max_yaw_rate_deg=MAX_YAW_RATE_DEG)
        self.last_yaw_rate = 0.0
        self.tlm_period = max(1, int(RATE_HZ / TELEMETRY_HZ))
        self.k = 0

    # komut kapilari (FSM control_mode'a gore)
    def _send_search(self, own_pos, own_euler):
        c = self.search.update(own_pos, own_euler)
        self.io.send_command(c["roll"], c["pitch"], c["yaw"], c["throttle"])
        self.last_yaw_rate = np.radians(c["yaw"] * MAX_YAW_RATE_DEG)

    def _send_apn(self, cmd):
        self.io.send_command(cmd["roll"], cmd["pitch"], cmd["yaw"], cmd["throttle"])
        self.last_yaw_rate = np.radians(cmd["yaw_rate_deg"])

    def _send_debug(self, cmd, own_pos, own_vel):
        """Izolasyon modlari: sorun APN (yatay) mi yoksa dinamik gaz (dikey) mi?"""
        m = self.debug_mode
        if m == "hover":
            # Kalkis irtifasini yakala, orada sabit dur (yatay=0). Airframe/dikey stabilite testi.
            if self._hold_alt is None:
                self._hold_alt = float(own_pos[2])
            thr = HOVER_THROTTLE + 0.05 * (self._hold_alt - own_pos[2]) - 0.10 * own_vel[2]
            self.io.send_command(0.0, 0.0, 0.0, max(0.0, min(1.0, thr)))
            self.last_yaw_rate = 0.0
        elif m == "vertical":
            # Dikey PD (hedef Z'ye tirmanis) IZOLE; yatay komut yok.
            self.io.send_command(0.0, 0.0, 0.0, cmd["throttle"])
            self.last_yaw_rate = 0.0
        elif m == "horizontal":
            # APN yatay IZOLE; gaz sabit hover (dikey kuplaj kapali).
            self.io.send_command(cmd["roll"], cmd["pitch"], cmd["yaw"], HOVER_THROTTLE)
            self.last_yaw_rate = np.radians(cmd["yaw_rate_deg"])
        else:
            self.io.send_command(0.0, 0.0, 0.0, HOVER_THROTTLE)
            self.last_yaw_rate = 0.0

    def _send_rtl(self):
        self.io.send_command(0.0, 0.0, 0.0, HOVER_THROTTLE)   # >>> RTL davranisi
        self.last_yaw_rate = 0.0

    def _send_safe(self):
        self.io.send_command(0.0, 0.0, 0.0, HOVER_THROTTLE * 0.9)
        self.last_yaw_rate = 0.0

    def step_once(self):
        t = self.k * self.dt
        # 1) HEDEF (POS-ONLY 3B; jam/gecersiz -> None -> EKF coast)
        tpos = self.io.read_target()
        lost = tpos is None
        z = None if lost else tpos
        # 2) KENDI DURUM
        rp, rv, re = self.io.read_own()
        own_pos, own_vel, own_euler = self.own.update(rp, rv, re, cmd_yaw_rate=self.last_yaw_rate)
        # 3) KESTIR
        self.ekf.step(z)
        measured = (z is not None) and (not self.ekf.last_rejected) and self.ekf.initialized

        if not self.ekf.initialized or own_pos is None:
            self.io.send_command(0.0, 0.0, 0.0, HOVER_THROTTLE)
            self.last_yaw_rate = 0.0
            self.k += 1
            return {"state": "INIT", "fire": False}

        # 4) APN geometri (her adim; komut yalniz TRACK/ENGAGE'de gonderilir)
        cmd = self.apn.compute(own_pos, own_vel, own_euler,
                               self.ekf.get_position(), self.ekf.get_velocity(),
                               self.ekf.get_acceleration())
        # 5) MISSION (FSM + kilit)
        m = self.mission.update(t, own_pos, own_euler, self.ekf.get_position(),
                                cmd["closing_speed"], measured=measured,
                                confidence=1.0, los_rate=cmd["los_rate"])
        mode = m["control_mode"]
        # 6) KOMUT KAPISI  (debug modu aktifse FSM'i bypass edip izolasyon komutu gonderir)
        if self.debug_mode != "full":
            self._send_debug(cmd, own_pos, own_vel)
        elif mode == "SEARCH_PATTERN":
            self._send_search(own_pos, own_euler)
        else:
            self.search.reset()                       # SEARCH'ten cikinca taramayi sifirla
            if mode == "APN":
                self._send_apn(cmd)
            elif mode == "RTL":
                self._send_rtl()
            else:
                self._send_safe()

        # 7) SUNUCU TELEMETRI
        ts = time.time()                                  # sistem saati zaman damgasi
        if m["lock"]["lock_report"]:
            self.server.send_lock(ts, {"own": own_pos.tolist(),
                                       "tgt": self.ekf.get_position().tolist(),
                                       "lock_s": m["lock"]["cumulative"]})
        if self.k % self.tlm_period == 0:
            self.server.send_telemetry(ts, {"own": own_pos.tolist(),
                                            "alt": float(own_pos[2]), "state": m["state"],
                                            "t_go": float(m["t_go"]), "fire": m["fire"]})
        self.k += 1
        return {"state": m["state"], "fire": m["fire"], "lock": m["lock"],
                "proj": m["proj"], "t_go": m["t_go"], "z_none": z is None,
                "rejected": self.ekf.last_rejected,
                "coasting": (z is None) or self.ekf.last_rejected}

    def run(self, max_steps=None, realtime=True, verbose=True):
        """50 Hz sabit-periyot dongu. is_connected()=False olunca ya da Ctrl+C ile durur."""
        next_t = time.perf_counter()
        prev_state = None
        last_coast = -10.0
        try:
            while self.io.is_running():
                info = self.step_once()
                if verbose:
                    t = self.k * self.dt
                    st = info.get("state")
                    if st != prev_state:
                        print(f"[{t:7.2f}s] DURUM -> {st}")
                        prev_state = st
                    if info.get("lock", {}).get("lock_report"):
                        print(f"[{t:7.2f}s] >>> KILIT +400 sunucuya")
                    if info.get("fire"):
                        print(f"[{t:7.2f}s] >>> FIRE / onleme commit")
                    if info.get("coasting") and t - last_coast > 1.0:
                        last_coast = t
                        kind = "JAM (veri kesik)" if info.get("z_none") else "SAHTE (gating reddetti)"
                        print(f"[{t:7.2f}s] ~~ COAST: {kind} -> EKF tahminle suruyor")
                if max_steps and self.k >= max_steps:
                    break
                if realtime:
                    next_t += self.dt
                    sleep = next_t - time.perf_counter()
                    if sleep > 0:
                        time.sleep(sleep)
                    else:
                        next_t = time.perf_counter()
        except KeyboardInterrupt:
            print("\n[Ctrl+C] gorev durduruluyor...")
        finally:
            self.io.send_command(0.0, 0.0, 0.0, HOVER_THROTTLE)


# =========================================================================== DEMO (Mock SDK)
class MockSDK:
    """drone_sdk PUBLIC API taklidi (offline test). Birimler: konum cm, rotasyon derece, hiz cm/s.
    Hedef azimut 90 (FOV disi) -> avci tarayip bulur; menzil kapanir -> kilit -> engage."""
    M2CM = 100.0

    def __init__(self):
        self.t = 0.0
        self.own_yaw = 0.0                          # radyan (ic)
        self.op = np.array([0.0, 0.0, 20.0])        # metre (ic)
        az, el = np.radians(90.0), np.radians(35.0)
        self.dir = np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])

    def _range(self, t):
        if t < 6.0:  return 120.0 - (120.0 - 13.0) * (t / 6.0)
        if t < 13.0: return 13.0 + 0.8 * np.sin(t - 6.0)
        return max(4.0, 13.0 - 9.0 * (t - 13.0))

    def _tp(self, t): return self.op + self._range(t) * self.dir

    # --- public API (adapter'in cagirdiklari) ---
    def connect(self, host='127.0.0.1', port=12345): return True
    def is_connected(self): return True
    def set_arm(self, state): pass
    def get_drone_location(self): return (self.op * self.M2CM).tolist()              # cm
    def get_drone_rotation(self): return [0.0, 0.0, float(np.degrees(self.own_yaw))] # (R,P,Y) derece
    def get_drone_speed(self): return 0.0
    def get_target_location(self):
        true = self._tp(self.t)
        if 8.4 <= self.t < 8.8:                                   # GURULTULU SAHTE (jammer)
            return ((true + np.random.randn(3) * 30.0) * self.M2CM).tolist()  # buyuk rastgele sicrama
        return ((true + np.random.randn(3) * 0.15) * self.M2CM).tolist()      # normal (cm)
    def get_target_speed(self):                                                       # SKALER cm/s
        v = (self._tp(self.t + DT) - self._tp(self.t)) / DT
        return float(np.linalg.norm(v) * self.M2CM)
    def set_control_surfaces(self, throttle, pitch, roll, yaw, arm):
        self.own_yaw += np.radians(yaw * MAX_YAW_RATE_DEG) * DT                       # yaw entegre
        self.t += DT


def _offline_test():
    """MockSDK ile cevrimdisi dogrulama (gercek oyun olmadan). Calistirmak icin
    asagidaki __main__'de gercek baglanti yerine bu fonksiyonu cagir."""
    np.random.seed(0)
    srv = ServerLink()
    mock = MockSDK()
    jam_check = lambda: 5.0 <= mock.t < 5.6        # ornek jam penceresi
    io = SDKAdapter(mock, jam_check=jam_check)
    io.arm(True)
    loop = InterceptorLoop(io, server=srv)
    for _ in range(900):
        info = loop.step_once()
        t = loop.k * DT
        if info.get("lock", {}).get("lock_report"):
            print(f"t={t:5.2f}s  >>> KILIT +400 (kumulatif {info['lock']['cumulative']:.1f}s)")
        if info.get("fire"):
            print(f"t={t:5.2f}s  >>> FIRE (t_go={info['t_go']:.2f})"); break
    print(f"Offline test tamam. kilit={srv.lock_count} telemetri={srv.tlm_count}")


# ===========================================================================
# PRODUCTION: GERCEK OYUNA (drone_sdk / Unreal Engine) BAGLAN VE OTONOM UC
# ===========================================================================
if __name__ == "__main__":
    import drone_sdk

    # --- JAMMER KANCASI: simdilik KAPALI (None) ---
    # Aktif etmek icin kendi GNSS jammer arayuzunu bagla, ornegin:
    #     jam_check = my_jammer.is_active        # cagrilabilir -> bool
    # Aktifken hedef/own konumu kesilir, EKF coast eder (sahte kilit riski yok).
    jam_check = None

    # --- 1) Oyuna baglan (Unreal Engine TCP - varsayilan 127.0.0.1:12345) ---
    print("drone_sdk'ya baglaniliyor...")
    if not drone_sdk.connect():
        print("HATA: Baglanti kurulamadi. Oyun acik ve TCP sunucusu (12345) calisiyor mu?")
        raise SystemExit(1)
    print("Baglandi. Telemetri akisi bekleniyor...")

    # --- 2) Ilk telemetri paketlerinin gelmesini bekle (alici thread parse etsin) ---
    time.sleep(1.0)
    print(f"  drone konum (cm) = {drone_sdk.get_drone_location()}")
    print(f"  hedef konum (cm) = {drone_sdk.get_target_location()}")
    print(f"  drone rotasyon   = {drone_sdk.get_drone_rotation()}")

    # --- 3) Adapter + sunucu + dongu ---
    io = SDKAdapter(drone_sdk, jam_check=jam_check)

    # ============================ SAHA KALIBRASYON (TEK MERKEZ) ============================
    # Ilk ucusta sirayla dene: takla atiyorsa sign_pitch'i cevir; yon sapmasi varsa sign_yaw/roll;
    # tirmanista salinim varsa kp_alt dusur / kd_alt artir.
    loop = InterceptorLoop(
        io, server=ServerLink(),
        sign_pitch=-1.0,   # Unreal pitch ters ise -1 (nose-up/backflip); duzse +1
        sign_yaw=1.0,      # yon ters donuyorsa -1
        sign_roll=1.0,     # lateral ters ise -1
        kp_alt=1.0,        # irtifa tirmanis agresifligi
        kd_alt=2.0,        # dikey hiz sonumleme (overshoot)
        grace_s=4.0,       # TRACK->ENGAGE guvenlik kilidi (s)
        # IZOLASYON: once "hover" ile dikey/airframe'i, sonra "horizontal" ile APN'i test et,
        # ikisi de stabilse "full" yap. ("vertical" = sadece tirmanis testi)
        debug_mode="full",  # "full" | "hover" | "vertical" | "horizontal"
    )
    # ======================================================================================

    # --- 4) ARM ve gercek zamanli otonom gorev (50 Hz) ---
    try:
        io.arm(True)
        print("ARM edildi. Otonom gorev basladi. Durdurmak icin Ctrl+C.\n")
        loop.run(realtime=True)            # baglanti kopana ya da Ctrl+C'ye kadar
    finally:
        io.arm(False)                      # DISARM (guvenli)
        drone_sdk.disconnect()
        print("Disarm + baglanti kapatildi. Gorev sonu.")

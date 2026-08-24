import time

# ==========================================================
# Constants
# ==========================================================
CM_TO_M = 0.01
M_TO_CM = 100.0
# cm/s; gercekci hedef hiz tavani (~40 m/s). Ham lead-hizi bununla kirpilir.
MAX_TARGET_SPEED = 4000.0
VEL_EMA = 0.15              # lead-hizi yumusatma orani
MAX_LEAD = 600.0            # cm; lead-mesafe tavani
# cm/s; anlik vs yumusak hiz farki bu degerde lead guveni 0'a duser
CONSISTENCY_SCALE = 1500.0
GAP_DT           = 2.5      # sn; dropout/kesinti -> cooldown baslat
COOLDOWN_N       = 3        # ornek; bosluk sonrasi lead'i agir kistigimiz ornek sayisi
COOLDOWN_CONF   = 0.2       # cooldown suresince lead carpani

# ==========================================================
# HELPERS
# ==========================================================
def _slope(ts, vs):
    m = len(ts)
    if m < 2:
        return 0.0
    t0 = ts[-1]
    sx = sy = sxx = sxy = 0.0
    for a in range(m):
        dtk = ts[a] - t0
        sx += dtk; sy += vs[a]; sxx += dtk * dtk; sxy += dtk * vs[a]
    denom = m * sxx - sx * sx
    return 0.0 if abs(denom) < 1e-9 else (m * sxy - sx * sy) / denom


def _time_axis(times, n):
    if times is None:
        return [0.2 * i for i in range(n)]
    return list(map(float, times))


# ==========================================================
# SPIKE TEMIZLEYICILER
# ==========================================================
def z_despike(z_dizi, times=None, thresh=3.0, max_hold=8, vz_ema=0.3, max_vz=5.0):
    z = list(map(float, z_dizi))
    if not z:
        return z
    tt = _time_axis(times, len(z))
    clean = [z[0]]
    last = z[0]; last_t = tt[0]; vz = 0.0; hold = 0
    for i in range(1, len(z)):
        dt = tt[i] - last_t
        if dt <= 0:
            dt = 0.2
        if dt > 5.0:
            vz = 0.0
            clean.append(z[i]); last = z[i]; last_t = tt[i]; hold = 0
            continue
        expected = last + vz * dt
        if abs(z[i] - expected) > thresh and hold < max_hold:
            clean.append(expected); last = expected; last_t = tt[i]; hold += 1
        else:
            vz = (1 - vz_ema) * vz + vz_ema * (z[i] - last) / dt
            vz = max(-max_vz, min(max_vz, vz))
            clean.append(z[i]); last = z[i]; last_t = tt[i]; hold = 0
    return clean


def x_despike(x_dizi, y_dizi=None, times=None,
              speed_thresh=12.0, pos_thresh=8.0, N=5, max_hold=6, max_speed=40.0):
    x = list(map(float, x_dizi))
    n = len(x)
    if n < 3:
        return x
    y = list(map(float, y_dizi)) if y_dizi is not None else [0.0] * n
    two_d = y_dizi is not None
    tt = _time_axis(times, n)
    clean = [x[0]]
    gt = [tt[0]]; gx = [x[0]]; gy = [y[0]]
    last_t = tt[0]; hold = 0
    for i in range(1, n):
        dt = tt[i] - last_t
        if dt <= 0:
            dt = 0.2
        if dt > 5.0:
            clean.append(x[i]); gt.append(tt[i]); gx.append(x[i]); gy.append(y[i])
            last_t = tt[i]; hold = 0
            continue
        k = min(N, len(gx))
        if k >= 2:
            vx = max(-max_speed, min(max_speed, _slope(gt[-k:], gx[-k:])))
            exp_x = gx[-1] + vx * dt
            vadx = (x[i] - gx[-1]) / dt
            if two_d:
                vy = max(-max_speed, min(max_speed, _slope(gt[-k:], gy[-k:])))
                exp_y = gy[-1] + vy * dt
                vady = (y[i] - gy[-1]) / dt
                speed_dev = ((vadx - vx) ** 2 + (vady - vy) ** 2) ** 0.5
                pos_dev = ((x[i] - exp_x) ** 2 + (y[i] - exp_y) ** 2) ** 0.5
            else:
                exp_y = 0.0
                speed_dev = abs(vadx - vx)
                pos_dev = abs(x[i] - exp_x)
        else:
            exp_x = x[i]; exp_y = y[i]; speed_dev = 0.0; pos_dev = 0.0
        if speed_dev > speed_thresh and pos_dev > pos_thresh and hold < max_hold:
            clean.append(exp_x); gt.append(tt[i]); gx.append(exp_x); gy.append(exp_y)
            last_t = tt[i]; hold += 1
        else:
            clean.append(x[i]); gt.append(tt[i]); gx.append(x[i]); gy.append(y[i])
            last_t = tt[i]; hold = 0
    return clean


def y_despike(y_dizi, times=None, speed_thresh=15.0, pos_thresh=6.0,
              N=5, max_hold=6, max_speed=25.0):
    y = list(map(float, y_dizi))
    n = len(y)
    if n < 3:
        return y
    tt = _time_axis(times, n)
    clean = [y[0]]
    gt = [tt[0]]; gy = [y[0]]
    last_t = tt[0]; hold = 0
    for i in range(1, n):
        dt = tt[i] - last_t
        if dt <= 0:
            dt = 0.2
        if dt > 5.0:
            clean.append(y[i]); gt.append(tt[i]); gy.append(y[i])
            last_t = tt[i]; hold = 0
            continue
        k = min(N, len(gy))
        if k >= 2:
            v_last = max(-max_speed, min(max_speed, _slope(gt[-k:], gy[-k:])))
            v_step = (y[i] - gy[-1]) / dt
            exp = gy[-1] + v_last * dt
        else:
            v_last = 0.0; v_step = 0.0; exp = y[i]
        if (abs(v_step - v_last) > speed_thresh
                and abs(y[i] - exp) > pos_thresh and hold < max_hold):
            clean.append(exp); gt.append(tt[i]); gy.append(exp)
            last_t = tt[i]; hold += 1
        else:
            clean.append(y[i]); gt.append(tt[i]); gy.append(y[i])
            last_t = tt[i]; hold = 0
    return clean


# ==========================================================
# STREAMING SARMALAYICI
# ==========================================================
class GNSSFilter:
    def __init__(self, delay_s=1.0, window=400, vel_n=7):
        # delay_s : olcum ~bu kadar eski -> ileri-tahminle telafi edilir
        # window  : tutulan ham ornek penceresi
        # vel_n   : hiz kestiriminde son N nokta (buyuk = daha yumusak)
        self.delay_s = float(delay_s)
        self.window = int(window)
        self.vel_n = int(vel_n)
        self._xs = []; self._ys = []; self._zs = []; self._ts = []   # ham (m) + zaman
        self._pos = None     # son telafisiz temiz konum (cm)
        self._vel = None     # son hiz (cm/s) — yumusatilmis (guduum + lead ortak)
        self._v_lead = None  # lead-hizi EMA durumu
        self._cooldown = 0   # dropout/kesinti sonrasi lead-kisma sayaci

    def update(self, noisy_x, noisy_y, noisy_z):
        t = time.perf_counter()
        self._xs.append(float(noisy_x) * CM_TO_M)  # cm -> m (spike esikleri metre)
        self._ys.append(float(noisy_y) * CM_TO_M)
        self._zs.append(float(noisy_z) * CM_TO_M)
        self._ts.append(t)
        if len(self._ts) > self.window:  # pencereyi gergin tut (bellek + hiz)
            self._xs.pop(0); self._ys.pop(0); self._zs.pop(0); self._ts.pop(0)
        if len(self._ts) < 2:  # tek ornek: hiz yok, isinmadi
            return None

        # -- Batch temizleme (son eleman = simdiki temiz kestirim)
        zt = z_despike(self._zs, self._ts)
        xt = x_despike(self._xs, self._ys, self._ts)
        yt = y_despike(self._ys, self._ts)
        px = xt[-1] * M_TO_CM; py = yt[-1] * M_TO_CM; pz = zt[-1] * M_TO_CM
        self._pos = (px, py, pz)

        # -- Hiz (son vel_n temiz nokta uzerinden lineer egim)
        k = min(self.vel_n, len(self._ts))
        ts_k = self._ts[-k:]
        vx = _slope(ts_k, xt[-k:]) * M_TO_CM
        vy = _slope(ts_k, yt[-k:]) * M_TO_CM
        vz = _slope(ts_k, zt[-k:]) * M_TO_CM

        # -- Ham hizi gercekci hedef hizina kirp 
        vx = max(-MAX_TARGET_SPEED, min(MAX_TARGET_SPEED, vx))
        vy = max(-MAX_TARGET_SPEED, min(MAX_TARGET_SPEED, vy))
        vz = max(-MAX_TARGET_SPEED, min(MAX_TARGET_SPEED, vz))

        # -- EMA (dongu jitter'ından gelen hiz titremesini onler)
        if self._v_lead is None:
            self._v_lead = (vx, vy, vz)
        else:
            a = VEL_EMA
            self._v_lead = ((1.0 - a) * self._v_lead[0] + a * vx,
                            (1.0 - a) * self._v_lead[1] + a * vy,
                            (1.0 - a) * self._v_lead[2] + a * vz)
        self._vel = self._v_lead

        # --- Lead guven faktoru
        dt_last = self._ts[-1] - self._ts[-2]
        if dt_last <= 1e-3:
            dt_last = 0.2
        vadx = (xt[-1] - xt[-2]) / dt_last * M_TO_CM
        vady = (yt[-1] - yt[-2]) / dt_last * M_TO_CM
        vadz = (zt[-1] - zt[-2]) / dt_last * M_TO_CM
        fark = ((vadx - self._v_lead[0]) ** 2 + (vady - self._v_lead[1]) ** 2
                + (vadz - self._v_lead[2]) ** 2) ** 0.5
        conf_w = max(0.0, 1.0 - fark / CONSISTENCY_SCALE)
        if dt_last > GAP_DT:
            self._cooldown = COOLDOWN_N
        if self._cooldown > 0:
            conf_w *= COOLDOWN_CONF
            self._cooldown -= 1

        # -- Gecikme telafisi
        g = self.delay_s
        lx = max(-MAX_LEAD, min(MAX_LEAD, self._v_lead[0] * g)) * conf_w
        ly = max(-MAX_LEAD, min(MAX_LEAD, self._v_lead[1] * g)) * conf_w
        lz = max(-MAX_LEAD, min(MAX_LEAD, self._v_lead[2] * g)) * conf_w
        return (px + lx, py + ly, pz + lz)

    def guidance_state(self):
        if self._pos is None or self._vel is None:
            return None
        return {"pos": self._pos, "vel": self._vel}

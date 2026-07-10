import time

# Sabitler
CM_TO_M = 0.01
M_TO_CM = 100.0
MAX_HEDEF_HIZ = 4000.0    # cm/s; hedef hiz tavani
VEL_EMA = 0.15            # lead-hizi yumusatma
SHORT_N = 4               # kisa-pencere nokta sayisi
MAX_LEAD = 3000.0         # cm; lead tavani
TUTARLILIK_OLCEK = 1500.0  # cm/s
GAP_DT           = 2.5     # sn; kesinti esigi
COOLDOWN_N       = 3
COOLDOWN_GUVEN   = 0.2


def _egim(ts, vs):
    m = len(ts)
    if m < 2:
        return 0.0
    t0 = ts[-1]
    sx = sy = sxx = sxy = 0.0
    for a in range(m):
        dtk = ts[a] - t0
        sx += dtk; sy += vs[a]; sxx += dtk * dtk; sxy += dtk * vs[a]
    payda = m * sxx - sx * sx
    return 0.0 if abs(payda) < 1e-9 else (m * sxy - sx * sy) / payda


def _zaman_ekseni(zamanlar, n):
    if zamanlar is None:
        return [0.2 * i for i in range(n)]
    return list(map(float, zamanlar))


# Eksen-bazli spike temizleme
def z_spike_temizle(z_dizi, zamanlar=None, esik=3.0, max_hold=8, vz_ema=0.3, max_vz=5.0):
    z = list(map(float, z_dizi))
    if not z:
        return z
    tt = _zaman_ekseni(zamanlar, len(z))
    temiz = [z[0]]
    son = z[0]; son_t = tt[0]; vz = 0.0; hold = 0
    for i in range(1, len(z)):
        dt = tt[i] - son_t
        if dt <= 0:
            dt = 0.2
        if dt > 5.0:
            vz = 0.0
            temiz.append(z[i]); son = z[i]; son_t = tt[i]; hold = 0
            continue
        beklenen = son + vz * dt
        if abs(z[i] - beklenen) > esik and hold < max_hold:
            temiz.append(beklenen); son = beklenen; son_t = tt[i]; hold += 1
        else:
            vz = (1 - vz_ema) * vz + vz_ema * (z[i] - son) / dt
            vz = max(-max_vz, min(max_vz, vz))
            temiz.append(z[i]); son = z[i]; son_t = tt[i]; hold = 0
    return temiz


def x_spike_temizle(x_dizi, y_dizi=None, zamanlar=None,
                    hiz_esik=12.0, konum_esik=8.0, N=5, max_hold=6, max_hiz=40.0):
    x = list(map(float, x_dizi))
    n = len(x)
    if n < 3:
        return x
    y = list(map(float, y_dizi)) if y_dizi is not None else [0.0] * n
    iki_d = y_dizi is not None
    tt = _zaman_ekseni(zamanlar, n)
    temiz = [x[0]]
    gt = [tt[0]]; gx = [x[0]]; gy = [y[0]]
    son_t = tt[0]; hold = 0
    for i in range(1, n):
        dt = tt[i] - son_t
        if dt <= 0:
            dt = 0.2
        if dt > 5.0:
            temiz.append(x[i]); gt.append(tt[i]); gx.append(x[i]); gy.append(y[i])
            son_t = tt[i]; hold = 0
            continue
        k = min(N, len(gx))
        if k >= 2:
            vx = max(-max_hiz, min(max_hiz, _egim(gt[-k:], gx[-k:])))
            bekx = gx[-1] + vx * dt
            vadx = (x[i] - gx[-1]) / dt
            if iki_d:
                vy = max(-max_hiz, min(max_hiz, _egim(gt[-k:], gy[-k:])))
                beky = gy[-1] + vy * dt
                vady = (y[i] - gy[-1]) / dt
                hiz_sapma = ((vadx - vx) ** 2 + (vady - vy) ** 2) ** 0.5
                konum_sapma = ((x[i] - bekx) ** 2 + (y[i] - beky) ** 2) ** 0.5
            else:
                beky = 0.0
                hiz_sapma = abs(vadx - vx)
                konum_sapma = abs(x[i] - bekx)
        else:
            bekx = x[i]; beky = y[i]; hiz_sapma = 0.0; konum_sapma = 0.0
        if hiz_sapma > hiz_esik and konum_sapma > konum_esik and hold < max_hold:
            temiz.append(bekx); gt.append(tt[i]); gx.append(bekx); gy.append(beky)
            son_t = tt[i]; hold += 1
        else:
            temiz.append(x[i]); gt.append(tt[i]); gx.append(x[i]); gy.append(y[i])
            son_t = tt[i]; hold = 0
    return temiz


def y_spike_temizle(y_dizi, zamanlar=None, hiz_esik=15.0, konum_esik=6.0,
                    N=5, max_hold=6, max_hiz=25.0):
    y = list(map(float, y_dizi))
    n = len(y)
    if n < 3:
        return y
    tt = _zaman_ekseni(zamanlar, n)
    temiz = [y[0]]
    gt = [tt[0]]; gy = [y[0]]
    son_t = tt[0]; hold = 0
    for i in range(1, n):
        dt = tt[i] - son_t
        if dt <= 0:
            dt = 0.2
        if dt > 5.0:
            temiz.append(y[i]); gt.append(tt[i]); gy.append(y[i])
            son_t = tt[i]; hold = 0
            continue
        k = min(N, len(gy))
        if k >= 2:
            v_son = max(-max_hiz, min(max_hiz, _egim(gt[-k:], gy[-k:])))
            v_adim = (y[i] - gy[-1]) / dt
            bek = gy[-1] + v_son * dt
        else:
            v_son = 0.0; v_adim = 0.0; bek = y[i]
        if abs(v_adim - v_son) > hiz_esik and abs(y[i] - bek) > konum_esik and hold < max_hold:
            temiz.append(bek); gt.append(tt[i]); gy.append(bek)
            son_t = tt[i]; hold += 1
        else:
            temiz.append(y[i]); gt.append(tt[i]); gy.append(y[i])
            son_t = tt[i]; hold = 0
    return temiz


# Akis sarmalayici: ham GNSS -> temiz konum + hiz + gecikme telafisi
class GNSSFiltre:
    def __init__(self, gecikme_sn=1.0, pencere=400, vel_n=7):
        self.gecikme_sn = float(gecikme_sn)   # olcum gecikmesi (ileri-tahminle telafi)
        self.pencere = int(pencere)           # ham ornek penceresi
        self.vel_n = int(vel_n)               # hiz kestiriminde son N nokta
        self._xs = []; self._ys = []; self._zs = []; self._ts = []
        self._pos = None                      # son temiz konum (cm)
        self._vel = None                      # son hiz (cm/s)
        self._vlead = None                    # lead-hizi EMA durumu
        self._cooldown = 0                    # kesinti sonrasi lead-kisma sayaci

    def guncelle(self, bozuk_x, bozuk_y, bozuk_z):
        t = time.perf_counter()
        self._xs.append(float(bozuk_x) * CM_TO_M)   # cm -> m
        self._ys.append(float(bozuk_y) * CM_TO_M)
        self._zs.append(float(bozuk_z) * CM_TO_M)
        self._ts.append(t)
        if len(self._ts) > self.pencere:
            self._xs.pop(0); self._ys.pop(0); self._zs.pop(0); self._ts.pop(0)
        if len(self._ts) < 2:
            return None

        # Batch temizleme (son eleman = simdiki kestirim)
        zt = z_spike_temizle(self._zs, self._ts)
        xt = x_spike_temizle(self._xs, self._ys, self._ts)
        yt = y_spike_temizle(self._ys, self._ts)
        px = xt[-1] * M_TO_CM; py = yt[-1] * M_TO_CM; pz = zt[-1] * M_TO_CM
        self._pos = (px, py, pz)

        # Hiz (son vel_n temiz nokta, lineer egim)
        k = min(self.vel_n, len(self._ts))
        ts_k = self._ts[-k:]
        vx = _egim(ts_k, xt[-k:]) * M_TO_CM
        vy = _egim(ts_k, yt[-k:]) * M_TO_CM
        vz = _egim(ts_k, zt[-k:]) * M_TO_CM

        # Hedef hizina kirp
        vx = max(-MAX_HEDEF_HIZ, min(MAX_HEDEF_HIZ, vx))
        vy = max(-MAX_HEDEF_HIZ, min(MAX_HEDEF_HIZ, vy))
        vz = max(-MAX_HEDEF_HIZ, min(MAX_HEDEF_HIZ, vz))

        # EMA yumusatma
        if self._vlead is None:
            self._vlead = (vx, vy, vz)
        else:
            a = VEL_EMA
            self._vlead = ((1.0 - a) * self._vlead[0] + a * vx,
                           (1.0 - a) * self._vlead[1] + a * vy,
                           (1.0 - a) * self._vlead[2] + a * vz)
        self._vel = self._vlead

        # Lead guven faktoru
        dt_son = self._ts[-1] - self._ts[-2]
        if dt_son <= 1e-3:
            dt_son = 0.2
        ks = min(SHORT_N, len(self._ts))
        ts_s = self._ts[-ks:]
        vsx = _egim(ts_s, xt[-ks:]) * M_TO_CM
        vsy = _egim(ts_s, yt[-ks:]) * M_TO_CM
        vsz = _egim(ts_s, zt[-ks:]) * M_TO_CM
        fark = ((vsx - self._vlead[0]) ** 2 + (vsy - self._vlead[1]) ** 2
                + (vsz - self._vlead[2]) ** 2) ** 0.5
        guven = max(0.0, 1.0 - fark / TUTARLILIK_OLCEK)
        if dt_son > GAP_DT:
            self._cooldown = COOLDOWN_N
        if self._cooldown > 0:
            guven *= COOLDOWN_GUVEN
            self._cooldown -= 1

        # Gecikme telafisi
        g = self.gecikme_sn
        lx = max(-MAX_LEAD, min(MAX_LEAD, self._vlead[0] * g)) * guven
        ly = max(-MAX_LEAD, min(MAX_LEAD, self._vlead[1] * g)) * guven
        lz = max(-MAX_LEAD, min(MAX_LEAD, self._vlead[2] * g)) * guven
        return (px + lx, py + ly, pz + lz)

    def durum_gudum(self):
        if self._pos is None or self._vel is None:
            return None
        return {"pos": self._pos, "vel": self._vel}

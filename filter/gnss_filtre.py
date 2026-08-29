# -*- coding: utf-8 -*-
"""
filter/gnss_filtre.py — ONCEKI SURUM GNSS temizleyici (ARTIK CAGRILMIYOR).

Aktif kestirici `gnss_filtre_v2.py :: GNSSFilterV2`dir (CT-EKF). Bu dosya
karsilastirma ve geri donus icin DURUYOR; silmeden once yenisinin canlida
dogrulandigindan emin olun. Geri donerken dikkat: bu surum `lead_s=` degil
`delay_s=` parametresi alir.

YAKLASIM FARKI (ikisi de ayni sozlesmeyi saglar):
    ESKI (bu dosya)  pencere tabanli SPIKE KAPILARI + son N noktadan lineer
                     hiz egimi + GUVEN AGIRLIKLI lead
    YENI (v2)        CT-EKF cekirdegi + Mahalanobis kapilari + kacis mekanizmasi

⛔ NEDEN DEGISTIRILDI (olculdu; sentetik jammer, 120 s x 5 tohum):
       konum hatasi medyan  21.86 m  ->  3.15 m   (6.9x)
       hiz hatasi medyan     4.31 m/s ->  0.43 m/s (10x)
   Kok neden: buradaki lead GUVEN AGIRLIKLI oldugu icin gecikmeyi fiilen
   KAPATMIYORDU — 21.9 m ~= 18 m/s x 1.13 s, yani hata tam olarak telafi
   edilmemis gecikmenin kendisiydi.

Birimler: giristeki olcum ve ciktinin tamami SANTIMETRE (cm, cm/s). Spike
kapilari icerideyken METRE alaninda calisir (esikler metre cinsinden daha
okunakli oldugu icin); donusum update() icinde yapilir.
"""
import time

# ==========================================================
# SABITLER
# ==========================================================
CM_TO_M = 0.01    # carpan; cm -> m
M_TO_CM = 100.0   # carpan; m -> cm
MAX_TARGET_SPEED = 4000.0   # cm/s; gercekci hedef hiz tavani (~40 m/s). Egimden
                            # cikan ham hiz bununla kirpilir; jammer sicramasi
                            # egime girdiginde anlamsiz buyuk hiz uretir.
VEL_EMA = 0.15              # 0..1; hiz kestiriminin EMA katsayisi. Kucuk = sakin
                            # ama gec; dongu jitter'indan gelen titremeyi onler.
MAX_LEAD = 600.0            # cm; gecikme telafisinin eksen basina tavani (6 m).
                            # Hiz kestirimi bozulursa lead'in hedefi metrelerce
                            # oteye firlatmasini engeller.
CONSISTENCY_SCALE = 1500.0  # cm/s; ANLIK hiz ile YUMUSAK hiz farki bu degere
                            # ulastiginda lead guveni 0'a duser (lead tamamen
                            # kapanir). Tutarsiz hiz = guvenilmez lead demektir.
GAP_DT           = 2.5      # s; iki paket arasi bundan uzunsa "kesinti" sayilir
                            # ve cooldown baslar
COOLDOWN_N       = 3        # adet ornek; kesinti sonrasi lead'in agir kisildigi
                            # ornek sayisi (hiz kestirimi henuz toparlanmamistir)
COOLDOWN_CONF   = 0.2       # carpan; cooldown suresince lead'e uygulanan katsayi

# ==========================================================
# YARDIMCILAR
# ==========================================================
def _slope(ts, vs):
    """En kucuk kareler dogru uydurup EGIMI dondurur (hiz kestirimi).

    ts : [s]; zaman damgalari
    vs : [deger]; ayni uzunlukta olcum dizisi
    -> egim, yani deger/saniye (ts saniye ise). Iki noktadan az varsa 0.0.

    Iki nokta arasi basit fark yerine bu kullanilir: gurultulu olcumde
    ardisik fark gurultuyu 1/dt ile BUYUTUR, egim ise N noktaya yayar.
    """
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
    """Zaman ekseni uretir: `times` verilmisse onu, verilmemisse 0.2 s'lik
    esit araliklarla varsayilan bir eksen (n eleman).

    Varsayilan aralik nominal GNSS paket periyodudur (5 Hz).
    """
    if times is None:
        return [0.2 * i for i in range(n)]
    return list(map(float, times))


# ==========================================================
# SPIKE TEMIZLEYICILER — hepsi METRE alaninda calisir
# ==========================================================
def z_despike(z_dizi, times=None, thresh=3.0, max_hold=8, vz_ema=0.3, max_vz=5.0):
    """Irtifa dizisindeki jammer sicramalarini temizler.

    z_dizi   : [m]; ham irtifa dizisi
    times    : [s]; damgalar (None -> 0.2 s'lik varsayilan eksen)
    thresh   : m;   olcum, ONGORULEN degerden bu kadar uzaksa SICRAMA sayilir
                    ve yerine ongoru konur
    max_hold : adet; ust uste en fazla kac ornek degistirilebilir. Sinir
                    ZORUNLUDUR: hedef gercekten tirmaniyorsa filtre onu sonsuza
                    kadar "sicrama" sayip gercekten kopardi.
    vz_ema   : 0..1; dikey hiz kestiriminin EMA katsayisi
    max_vz   : m/s;  dikey hiz kestiriminin tavani
    -> temizlenmis dizi (ayni uzunlukta, [m])

    Yontem: bir onceki temiz noktadan hizla ONGORU uret, olcum ongoruden
    `thresh`ten uzaksa olcumu degil ONGORUYU yaz.
    """
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
    """Yatay X (istege bagli olarak X-Y birlikte) dizisini temizler.

    x_dizi       : [m]; ham X dizisi
    y_dizi       : [m]; verilirse sapma 2B olarak olculur (daha secici)
    times        : [s]; damgalar
    speed_thresh : m/s; olcumun ima ettigi hiz, egimden gelen hizdan bu kadar
                   sapiyorsa suphelidir
    pos_thresh   : m;   VE olcum, ongorulen konumdan bu kadar uzaksa
    N            : adet; hiz egiminin hesaplandigi son nokta sayisi
    max_hold     : adet; ust uste degistirilebilecek azami ornek
    max_speed    : m/s;  egimden gelen hizin kirpma tavani
    -> temizlenmis X dizisi ([m])

    ⭐ IKI KOSUL BIRDEN aranir (hem hiz hem konum sapmasi). Tek kosul yeterli
      sayilsaydi hedefin gercek manevrasi sicrama sanilirdi: manevrada hiz
      degisir ama konum ongoruye yakin kalir.
    """
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
    """Yatay Y dizisini TEK BOYUTLU olarak temizler (parametreler `x_despike`
    ile ayni anlamda; esikler yalnizca bu eksen icin ayri secilmistir).

    y_dizi       : [m]; ham Y dizisi
    speed_thresh : m/s; hiz sapmasi esigi
    pos_thresh   : m;   konum sapmasi esigi
    N            : adet; egim penceresi
    max_hold     : adet; ust uste azami degistirme
    max_speed    : m/s;  egim kirpma tavani
    -> temizlenmis Y dizisi ([m])
    """
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
# AKIS SARMALAYICISI
# ==========================================================
class GNSSFilter:
    """Yukaridaki toplu (batch) temizleyicileri AKIS arayuzune ceviren sarmalayici.

    Her yeni olcumde pencerenin TAMAMI yeniden temizlenir ve son eleman
    "simdiki temiz kestirim" olarak alinir. Bu, EKF'e gore pahalidir ama
    durum tasimadigi icin sicrama sonrasi kendini toparlar.

    SOZLESME (v2 ile ayni; degistirilecekse ikisi de degistirilmeli):
        update(x, y, z)  -> (x, y, z) cm TELAFILI temiz konum | None (isinmadi)
        guidance_state() -> {"pos": (x,y,z), "vel": (vx,vy,vz)} cm, cm/s | None
    """

    def __init__(self, delay_s=1.0, window=400, vel_n=7):
        """delay_s : s;     olcumun gecikmesi — cikis bu kadar ILERI tasinir
        window  : adet; bellekte tutulan ham ornek sayisi (pencere).
                  Buyutmek gecmisi uzatir ama her guncellemede TUM pencere
                  yeniden temizlendigi icin maliyeti dogrudan arttirir.
        vel_n   : adet; hiz egiminin hesaplandigi son nokta sayisi.
                  Buyuk = daha yumusak ama daha gec hiz kestirimi.
        """
        self.delay_s = float(delay_s)
        self.window = int(window)
        self.vel_n = int(vel_n)
        self._xs = []; self._ys = []; self._zs = []; self._ts = []  # ham ornek penceresi:
                             # konumlar METRE, damgalar saniye (perf_counter)
        self._pos = None     # (x,y,z) cm; son TELAFISIZ temiz konum
        self._vel = None     # (vx,vy,vz) cm/s; son yumusatilmis hiz — hem guduume
                             # ileri beslenir hem lead hesabinda kullanilir
        self._v_lead = None  # (vx,vy,vz) cm/s; hiz EMA'sinin ic durumu
        self._cooldown = 0   # adet; kesinti sonrasi lead'in kisildigi kalan ornek

    def update(self, noisy_x, noisy_y, noisy_z):
        """HAM (bozuk) GNSS olcumunu isler ve TEMIZ hedef konumunu dondurur.

        noisy_x/y/z : cm; SDK'nin get_target_location() ciktisi
        -> (x, y, z) cm — gecikmesi telafi edilmis konum, ya da None (tek
           ornek var, hiz kestirilemedi)

        Adimlar: pencereye ekle -> uc ekseni de topluca temizle -> son
        `vel_n` noktadan hiz egimi -> zarfa kirp -> EMA -> lead guveni ->
        gecikme telafisi.
        """
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

        # --- Lead guven faktoru: ANLIK hiz ile YUMUSAK hiz ne kadar tutarli?
        #     Ikisi ayrisiyorsa hiz kestirimine guvenilmez, dolayisiyla o hizla
        #     yapilacak ileri tasima da guvenilmez -> lead kisilir.
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
        """Istasyon yasasinin ILERI BESLEDIGI durum.

        -> {"pos": (x,y,z) cm, "vel": (vx,vy,vz) cm/s} | None (isinmadi)

        ⚠ `pos` TELAFISIZ (lead uygulanmamis) konumdur; `update()`in dondurdugu
          konum ise ileri tasinmistir. Ikisini karistirmak gecikme x hedef hizi
          kadar, yani 18 m/s'de ~18 m sabit hata verir.
        """
        if self._pos is None or self._vel is None:
            return None
        return {"pos": self._pos, "vel": self._vel}

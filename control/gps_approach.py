# -*- coding: utf-8 -*-
"""
control/gps_approach.py — GPS FAZI: ISTASYON TUTMA

AMAÇ: Hedefin kuyruğundaki bir noktaya (istasyon) oturmak ve görsel temas kurmak

TERIMLER
  * İstasyon : Hedefe göre sabit göreli bir konum (x m gerisinde, y m altında)

  * İleri besleme (feedforward): Hatayı beklemeden hedefin hızını doğrudan komuta eklemek

  * Kalıcı gecikme hatası: Saf P kontrolcü hareketli referansı izlerken hep geride kalır.
"""
import math

from control.common import (CM_TO_M, ConverterCfg, Telemetry, VelocityToStick, clamp, wrap_deg)
from filter.gnss_filtre_v2 import GNSSFilterV2


class GPSCfg:
    # --- DÖNGÜ ---
    LOOP_HZ = 50.0
    DT = 1.0 / LOOP_HZ

    # --- İSTASYON (GPS fazının hedefi) ---
    STATION_RANGE_M = 8.0     # m; hedefin arkasında durulacak mesafe
    STATION_ALT_RATIO = 0.75  # alt ofseti menzile ORANTILI: h = R * ORAN
    STATION_ALT_M = 15.0      # m; ORAN 0 ise kullanilan SABIT alt ofset
    STATION_KP = 0.9          # 1/s; yatay konum hatasu -> hız
    STATION_KP_Z = 0.9        # 1/s; dikey konum hatası -> hız
    STATION_FEEDFWD = True    # İleri besleme

    # --- ZARF ---
    VZ_MAX_CLIMB = ConverterCfg.VZ_MAX_CLIMB      # m/s;
    VZ_MAX_DESCENT = ConverterCfg.VZ_MAX_DESCENT  # m/s;
    YAW_RATE_MAX = ConverterCfg.YAW_RATE_MAX_DEG  # derece/s

    # --- POLİTİKA ---
    V_MAX = 33.0           # m/s; yatay hız tavanı
    KP_YAW = 3.0           # yaw hatası (derece) -> yaw hızı (derece/s)

    # --- HEDEF YÖNÜ ---
    HEADING_MIN_SPEED = 1.0  # m/s;

    # --- GNSS FİLTRE ---
    DELAY_S = 1.0  # s; ham GNSS gecikmesi
    FILTER_EVERY_TICK = True

# ==========================================================
#  ISTASYON YASASI
# ==========================================================
def station_point(target_p, target_heading_deg, cfg=GPSCfg):
    """Hedefin kuyruğundaki istasyon noktası (m, Unreal dünya ekseni)"""
    hx, hy, hz = target_p
    if cfg.STATION_ALT_RATIO > 0:
        z = hz - cfg.STATION_RANGE_M * cfg.STATION_ALT_RATIO
    else:
        z = hz - cfg.STATION_ALT_M
    if target_heading_deg is None:
        return hx, hy, z
    r = math.radians(target_heading_deg)
    return (hx - math.cos(r) * cfg.STATION_RANGE_M, hy - math.sin(r) * cfg.STATION_RANGE_M, z)


def command(drone_p, drone_yaw_deg, target_p, target_v, target_heading_deg, cfg=GPSCfg):
    """İstasyon tutma komutu

    ÇIKTI: ((vx, vy), vz_ned, yaw_rate_deg_s, tani)
      vx, vy : m/s, Unreal dünya yatay düzlemi
      vz_ned : m/s, Pozitif = Aşağı (çevirici tarafından ters çevrilir)

    YASA:  v = v_des (ileri besleme) + Kp * (istasyon - konum)
      İlk terim hedefle aynı hızda uçmayı sağlar (kalıcı hata sıfır),
      ikinci terim istasyona oturtur.

    BURUN: her zaman hedefe donuk (Kamera tespiti için)
    """
    sx, sy, sz = station_point(target_p, target_heading_deg, cfg)
    ex = sx - drone_p[0]
    ey = sy - drone_p[1]
    ez = sz - drone_p[2]

    ff_x, ff_y, ff_z = (target_v if cfg.STATION_FEEDFWD else (0.0, 0.0, 0.0))

    vx = ff_x + cfg.STATION_KP * ex
    vy = ff_y + cfg.STATION_KP * ey
    n = math.hypot(vx, vy)
    if n > cfg.V_MAX:
        vx *= cfg.V_MAX / n
        vy *= cfg.V_MAX / n

    vz_up = ff_z + cfg.STATION_KP_Z * ez
    vz_up = clamp(vz_up, -cfg.VZ_MAX_DESCENT, cfg.VZ_MAX_CLIMB)

    bearing = math.degrees(math.atan2(target_p[1] - drone_p[1], target_p[0] - drone_p[0]))
    yaw_err = wrap_deg(bearing - drone_yaw_deg)
    yaw_rate = clamp(cfg.KP_YAW * yaw_err, -cfg.YAW_RATE_MAX, cfg.YAW_RATE_MAX)

    diag = {
        "station_x": sx, "station_y": sy, "station_z": sz,
        "station_err_m": math.sqrt(ex * ex + ey * ey + ez * ez),
        "station_err_horiz": math.hypot(ex, ey),
        "station_err_vert": ez,
        "target_range_m": math.dist(drone_p, target_p),
        "target_speed": math.hypot(target_v[0], target_v[1]),
        "target_heading": target_heading_deg,
        "yaw_err": yaw_err,
        "v_cmd": math.hypot(vx, vy),
    }
    return (vx, vy), -vz_up, yaw_rate, diag


# ==========================================================
#  GPS FAZI SÜRÜCÜSÜ
# ==========================================================
class GPSTracker:
    """Bozuk GNSS ile istasyon tutma"""

    def __init__(self, drone, sender, cfg=GPSCfg):
        self.cfg = cfg
        self.drone = drone
        self.tlm = Telemetry(drone)
        self.sender = sender
        self.conv = VelocityToStick()
        self.filter = None
        self.reset()

    def _filter_lost(self):
        """Filtre kilidini GERCEKTEN kaybetti mi? (sıcak taşımanın tek istisnası)

        Sıcak filtreyi görevler arası taşımak doğru olanıdır — ama oyun yeniden
        başlatılıp hedef BAŞKA YERDE doğduysa filtre eski kilidinde kalır ve
        kaçış mekanizması (P şişirme) devreye girene kadar hedefi yüzlerce
        metre yanlış gösterir. Ölçüldü (hedef 500 m ışınlandı, n=4): yeniden
        kilitlenme **medyan 2.60 s, max 2.80 s**. Soğuk kurulum ise ~0.40 s'de
        çıkış verir. Yani filtre kilidini kaybetmişken onu taşımak, ısınma
        transientinden DAHA kötüdür.

        Ölçüt filtrenin kendi teşhisidir: `ret` = üst üste kapı reddi sayacı.
        Tek bir jammer sıçraması 1-2 ret üretir ve bu SAĞLIKLI çalışmadır;
        eşiğin yarısını geçmişse artık rejim değişmiş demektir.

        ⚠ ŞÜPHEDE KALIRSA FİLTREYİ KORU. Soğuk kurulum bilinen bir bozulmadır
          (ısınma transienti); kilidini kaybetmiş filtre ise nadir bir durum.
          Bu yüzden teşhis okunamazsa `False` döner.
        """
        try:
            d = self.filter.diag()
            if not d.get("started"):
                return True  # zaten ısınmamış -> taşımanın anlamı yok
            return d.get("ret", 0) >= max(1, int(d.get("escape_thresh", 12)) // 2)
        except Exception:
            return False

    def reset(self, cold_filter=False):
        """Yeni görev için GÖREV KAPSAMLI durumu sıfırlar.

        ⭐ FİLTRE KORUNUR (`cold_filter=True` denmedikçe) — ve bu, görevi
          durdurup yeniden başlatmanın en kritik ayrıntısıdır.

          `web/server.py :: control_loop` görev PASİFKEN de her tik
          `clean_target()` çağırır; tek amacı filtrenin ISINMIŞ kalmasıdır.
          Filtreyi burada yeniden kurmak o ısınmayı **tam işe yarayacağı anda
          çöpe atardı** ve o satır fiilen ölü kod olurdu.

        ⛔ NEDEN ÖNEMLİ: ısınma transienti ilk ~4 saniyededir (pencere medyanı
          23.6 m, max 52 m). İLK görevde bunu KALKIŞ maskeler (kalkış ~4 s
          sürer ve o sırada yatay komut üretilmez). Ama görev havadayken
          yeniden başlatılırsa kalkış kapısının 2. kolu (hedefin irtifasına
          TAKEOFF_TARGET_GAP_M kadar yaklaşıldı) daha ilk tikte açılır —
          kalkış saniyenin onda birinde biter ve **maske kalkar**. O zaman
          transient doğrudan istasyon fazına, yani yatay komutun ÜRETİLDİĞİ
          yere düşer: hedef 20-50 m yanlış yerde görünür, yasa büyük bir hız
          komutu üretir ve araç sapıtır. Sıcak filtre bu zinciri kökünden
          keser.

          Gerçekten soğuk başlangıç isterseniz (ör. hedef değişti):
          `brain.reset(cold_filter=True)`.
        """
        if cold_filter or self.filter is None or self._filter_lost():
            self.filter = GNSSFilterV2(lead_s=self.cfg.DELAY_S)

        self.last_raw = None             # SDK'nin dondurdugu ham demet (paket izleme)
        self.target_p = None             # temiz hedef konumu (m)
        self.target_v = (0.0, 0.0, 0.0)  # temiz hedef hizi (m/s)
        self.target_heading = None       # hedefin gidiş yönü (derece) | None
        self._fresh = False

        self.phase = "STATION"
        self.range_h = None      # m; hedefe olan menzil
        self.station_err = None  # m; istasyon hatası
        self.diag = {}

    # ----------------------------------------------------------------
    #  BOZUK GNSS -> TEMIZ HEDEF (konum + hız + yön)
    # ----------------------------------------------------------------
    def clean_target(self):
        """Ham GNSS paketini filtreye ver, temiz hedef konumunu döndür.

        GÖRSEL FAZDA da çağrılır fakat hiçbir komut göndermez. Amaç filtrenin sıcak kalmasıdır.
        """
        raw = self.tlm.target_raw_cm()
        self._fresh = (raw != self.last_raw)
        if not self._fresh and not self.cfg.FILTER_EVERY_TICK:
            return self.target_p
        self.last_raw = raw
        clean_cm = self.filter.update(raw[0], raw[1], raw[2])
        if clean_cm is None:
            return self.target_p

        self.target_p = (clean_cm[0] * CM_TO_M, clean_cm[1] * CM_TO_M, clean_cm[2] * CM_TO_M)
        gs = self.filter.guidance_state()
        if gs is not None:
            v = gs["vel"]
            self.target_v = (v[0] * CM_TO_M, v[1] * CM_TO_M, v[2] * CM_TO_M)
            speed_horiz = math.hypot(self.target_v[0], self.target_v[1])
            if speed_horiz > self.cfg.HEADING_MIN_SPEED:
                self.target_heading = math.degrees(math.atan2(self.target_v[1], self.target_v[0]))
        return self.target_p

    # ================================================================
    #  KONTROL ADIMI
    # ================================================================
    def step(self):
        dp = self.tlm.position_m()
        _roll, _pitch, yaw = self.tlm.orientation_deg()
        v_meas = self.tlm.velocity_ms()
        hp = self.clean_target()

        # ---- Hedef Yok ----
        if hp is None:
            self.range_h = None
            self.station_err = None
            self.sender.loiter()
            self.diag = {"state": "NO_TARGET"}
            return

        # ---- İstasyon tutma ----
        (vx, vy), vz_ned, yaw_rate, diag = command(dp, yaw, hp, self.target_v, self.target_heading, self.cfg)
        thr, pitch, roll, yaw_c = self.conv.convert((vx, vy, vz_ned), v_meas, math.radians(yaw), yaw_rate)
        self.sender.send(thr, pitch, roll, yaw_c)

        self.range_h = diag["target_range_m"] 
        self.station_err = diag["station_err_m"]
        diag.update(self.conv.diag)
        diag["state"] = "STATION"
        diag["filter"] = self.filter.diag()
        self.diag = diag

    def status(self):
        return dict(self.diag)

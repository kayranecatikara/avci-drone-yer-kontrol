# -*- coding: utf-8 -*-
"""
control/gps_approach.py — GPS FAZI: ISTASYON TUTMA.

AMAC: hedefin KUYRUGUNDAKI bir noktaya (istasyon) hizla oturmak ve orada
KALMAK. Gorsel devir oradan yapilir.

⚠ KALKIS BU MODULDE DEGILDIR. Tirmanma yasasi `control/takeoff.py`, "kalkis
   bitti mi?" karari `control/main.py :: PhaseSupervisor.takeoff_tick`
   icindedir. Bu sinif ilk `step()`inde aracin ZATEN HAVADA oldugunu varsayar
   ve dogrudan yatay komut uretir.

⛔ YARISMA KURALI: bu modul YALNIZ gorsel temas YOKKEN cagrilir. Gorsel faz
   basladiginda `step()` hic calistirilmaz; yalnizca `clean_target()`
   cagrilabilir ve onun dondurdugu deger HICBIR KOMUTA GIRMEZ (filtre
   isinmis kalsin diyedir).

TERIMLER
  * istasyon : hedefe gore SABIT bir goreli konum (kuyrugunda R m, altinda h m).
               Hedef hareket ettikce istasyon da hareket eder.
  * ileri besleme (feedforward): hatayi beklemeden, BILINEN bozucuyu dogrudan
               komuta eklemek. Burada bozucu = hedefin kendi hizi.
  * kalici gecikme hatasi: saf P kontrolcu hareketli referansi izlerken hep
               GERIDE kalir. v = Kp*e kadar hiz uretebildigi icin denge
               e = V/Kp'de kurulur, SIFIRA INMEZ. Kp=0.9 ve V=18 m/s ise
               kalici hata 20 m. Ileri besleme bunu SIFIRLAR.

NEDEN BOYLE (olculdu, kardes depo drones_of_war_entegrasyon):
  * Ileri beslemesiz surumde arac hedefe hic oturamadi; menzil 100-255 m
    arasi salindi, kapanma hizi medyan -3.78 m/s (yani UZAKLASIYORDU).
  * Eski surumumuz cubugu DOGRUDAN PD ile suruyordu (KP_H, KP_Z...). Bu,
    olculmus arac zarfini (asimetrik dikey, iki kollu throttle haritasi,
    ivme tavani) hic bilmiyordu. Artik yasa HIZ SETPOINT'i uretir ve
    control.common.VelocityToStick olculmus modelle cubuga cevirir.

ISTASYON GEOMETRISI — OLCULDU (kampanya GK+GK2, 24 ucus, donusumlu A/B).
  Gercek tespit orani medyani:
     15 m / 0.45  -> %66.9   kutu 47.7 px   yanlis-pozitif %11.4
      8 m / 0.45  -> %76.0   kutu 73.5 px   yanlis-pozitif  %4.0
      8 m / 0.75  -> %88.8   kutu 69.3 px   yanlis-pozitif  %3.7   <- SECILDI
  Kollarin araliklari HIC ORTUSMUYOR. Iki dugme BIRBIRINDEN BAGIMSIZ:
     MENZIL yalniz KUTU BOYUTUNU degistirir (R 15->8 m: 61 -> 114 px)
     ORAN   yalniz GOK PAYINI degistirir    (0.45->0.75: 232 -> 362 px)
  cunku yukselis acisi atan(oran) — menzilden BAGIMSIZ. Gok payi buyudukce
  hedefin arka plani gokyuzu olur (dedektor icin temiz zemin).
"""
import math

from control.common import (CM_TO_M, ConverterCfg, Telemetry, VelocityToStick,
                            clamp, wrap_deg)
from filter.gnss_filtre_v2 import GNSSFilterV2


class GPSCfg:
    # --- DONGU ---
    LOOP_HZ = 50.0
    DT = 1.0 / LOOP_HZ

    # --- ISTASYON (GPS fazinin HEDEFI) ---
    STATION_RANGE_M = 8.0     # m; hedefin kac metre ARKASINDA duracagiz
    STATION_ALT_RATIO = 0.75  # alt ofseti menzile ORANTILI: h = R * ORAN
    STATION_ALT_M = 15.0      # m; ORAN 0 ise kullanilan SABIT alt ofset
    STATION_KP = 0.9          # 1/s; yatay konum hatasi -> hiz
    STATION_KP_Z = 0.9        # 1/s; dikey konum hatasi -> hiz
    STATION_FEEDFWD = True    # hedef hizini ileri besle (KAPATMA: bkz. baslik)

    # --- ZARF: OLCULMUS degerler TEK KAYNAKTAN gelir (ConverterCfg) ---
    # ⛔ Buraya sayi YAZMAYIN. Zarf uc katmanda (cevirici, GPS yasasi, gorsel
    #   yasa) tekrar edildiginde tirmanma tavani 33.51 / 33.5 / 33.5 diye
    #   ZATEN KAYMISTI. Olcum degisirse tek yer guncellenir.
    VZ_MAX_CLIMB = ConverterCfg.VZ_MAX_CLIMB      # m/s; olculdu
    VZ_MAX_DESCENT = ConverterCfg.VZ_MAX_DESCENT  # m/s; ⚠ 4.8 kat asimetrik —
                           #   tek tavan kullanmak alcalma komutunu ~5 kat abartir
    YAW_RATE_MAX = ConverterCfg.YAW_RATE_MAX_DEG  # derece/s

    # --- POLITIKA (zarf DEGIL: zarfin altinda bilincli secim) ---
    V_MAX = 33.0           # m/s; yatay hiz tavani (arac 34.6 yapabiliyor)
    KP_YAW = 3.0           # yaw hatasi (derece) -> yaw hizi (derece/s)

    # --- HEDEF YONU (istasyonun kuyruga kurulmasi icin) ---
    HEADING_MIN_SPEED = 1.0  # m/s; bunun altinda yon guvenilmez -> son yon tutulur

    # --- GNSS FILTRE (filter/gnss_filtre_v2.py :: GNSSFilterV2) ---
    DELAY_S = 1.0  # s; olculen ham GNSS gecikmesi (~1.13) telafi edilir
    # ⭐ HER TIK BESLE: filtre paket tekrarini KENDI tanir (np.allclose) ve
    #   arada OLU-HESAPLA ileri gider. Yalnizca yeni pakette beslersek o
    #   mekanizma hic calismaz ve hedef konumu 50 Hz'lik yasaya ~5 Hz'lik
    #   MERDIVEN olarak girer. False = eski davranis (paket tekrarinda dondur).
    FILTER_EVERY_TICK = True


# ==========================================================
#  ISTASYON YASASI (saf fonksiyonlar — test edilebilir)
# ==========================================================
def station_point(target_p, target_heading_deg, cfg=GPSCfg):
    """Hedefin KUYRUGUNDAKI istasyon noktasi (m, Unreal dunya ekseni).

    Yon bilinmiyorsa (hedef duruyor / yon henuz kestirilemedi) hedefin
    kendisi + alt ofset dondurulur.

    ALT OFSETI MENZILE ORANTILI: kamera TILT derece YUKARI baktigi icin
    hedefin kadraj merkezinde durmasi h = R*tan(TILT) ister. Sabit h
    kullanmak, menzil degisince hedefi kadrajda yukari/asagi kaydirir.
    """
    hx, hy, hz = target_p
    if cfg.STATION_ALT_RATIO > 0:
        z = hz - cfg.STATION_RANGE_M * cfg.STATION_ALT_RATIO
    else:
        z = hz - cfg.STATION_ALT_M
    if target_heading_deg is None:
        return hx, hy, z
    r = math.radians(target_heading_deg)
    return (hx - math.cos(r) * cfg.STATION_RANGE_M,
            hy - math.sin(r) * cfg.STATION_RANGE_M,
            z)


def command(drone_p, drone_yaw_deg, target_p, target_v, target_heading_deg, cfg=GPSCfg):
    """Istasyon tutma komutu.

    CIKTI: ((vx, vy), vz_ned, yaw_rate_deg_s, tani)
      vx, vy : m/s, Unreal dunya yatay duzlemi
      vz_ned : m/s, POZITIF = ASAGI (cevirici ters cevirir)

    YASA:  v = v_des (ileri besleme) + Kp * (istasyon - konum)
      Ilk terim hedefle AYNI hizda ucmayi saglar (kalici hata SIFIR),
      ikinci terim istasyona oturtur.

    BURUN: her zaman HEDEFE donuk (istasyona degil) — kamera hedefe baksin
    ki gorsel devir kurulabilsin.
    """
    sx, sy, sz = station_point(target_p, target_heading_deg, cfg)
    ex = sx - drone_p[0]
    ey = sy - drone_p[1]
    ez = sz - drone_p[2]

    ff_x, ff_y, ff_z = (target_v if cfg.STATION_FEEDFWD else (0.0, 0.0, 0.0))

    vx = ff_x + cfg.STATION_KP * ex
    vy = ff_y + cfg.STATION_KP * ey
    n = math.hypot(vx, vy)  # yatay tavan — YONU koruyarak kirp
    if n > cfg.V_MAX:
        vx *= cfg.V_MAX / n
        vy *= cfg.V_MAX / n

    vz_up = ff_z + cfg.STATION_KP_Z * ez
    vz_up = clamp(vz_up, -cfg.VZ_MAX_DESCENT, cfg.VZ_MAX_CLIMB)

    bearing = math.degrees(math.atan2(target_p[1] - drone_p[1],
                                      target_p[0] - drone_p[0]))
    yaw_err = wrap_deg(bearing - drone_yaw_deg)
    yaw_rate = clamp(cfg.KP_YAW * yaw_err, -cfg.YAW_RATE_MAX, cfg.YAW_RATE_MAX)

    diag = {
        "station_x": sx, "station_y": sy, "station_z": sz,
        "station_err_m": math.sqrt(ex * ex + ey * ey + ez * ez),  # BIRINCIL OLCUT
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
#  GPS FAZI SURUCUSU
# ==========================================================
class GPSTracker:
    """Bozuk GNSS ile kalkis + istasyon tutma. Her tik `step()` cagrilir (50 Hz)."""

    def __init__(self, drone, sender, cfg=GPSCfg):
        self.cfg = cfg
        self.drone = drone
        self.tlm = Telemetry(drone)
        self.sender = sender
        self.conv = VelocityToStick()  # DURUMSUZ; faz devrinde tasinacak sey yok
        self.filter = None
        self.reset()

    # ----------------------------------------------------------------
    def reset(self):
        """Yeni gorev icin durumu sifirla."""
        self.filter = GNSSFilterV2(lead_s=self.cfg.DELAY_S)

        # hedef kestirimi (hepsi SI: m, m/s, derece)
        self.last_raw = None             # SDK'nin dondurdugu ham demet (paket izleme)
        self.target_p = None             # temiz hedef konumu (m)
        self.target_v = (0.0, 0.0, 0.0)  # temiz hedef hizi (m/s)
        self.target_heading = None       # hedefin gidis yonu (derece) | None
        self._fresh = False

        # gozetmen/arayuz icin durum (guduume GIRMEZ)
        self.phase = "STATION"
        self.range_h = None      # m; hedefe 3B menzil (devir kapisi okur)
        self.station_err = None  # m; istasyon hatasi (devir kapisi okur)
        self.diag = {}

    # ----------------------------------------------------------------
    #  BOZUK GNSS -> TEMIZ HEDEF (konum + hiz + yon)
    # ----------------------------------------------------------------
    def clean_target(self):
        """Ham GNSS paketini filtreye ver, temiz hedef konumunu (m) dondur.

        ⛔ GORSEL FAZDA da cagrilir ama donen deger HICBIR KOMUTA GIRMEZ —
          amac filtrenin (ve hiz/yon kestiriminin) sicak kalmasidir; faz
          geri donerse sifirdan isinmak gerekmesin.

        ⚠ `last_raw` GERCEK paket kimligidir ve YALNIZ paket degisince tazelenir:
          gozetmenin/arayuzun "GNSS bayat mi" izlemesi buna bakar. Filtreyi her
          tik beslemek bu izlemeyi BOZMAZ, cunku bayrak ayri tutulur.
        """
        raw = self.tlm.target_raw_cm()
        self._fresh = (raw != self.last_raw)
        if not self._fresh and not self.cfg.FILTER_EVERY_TICK:
            return self.target_p  # eski davranis: tekrarda dondur
        self.last_raw = raw
        # Tekrar eden pakette filtre KENDI olu-hesap dalina duser (bkz. GPSCfg).
        clean_cm = self.filter.update(raw[0], raw[1], raw[2])
        if clean_cm is None:  # filtre henuz isinmadi
            return self.target_p

        # cm -> m sinirini burada gec (filtre cm alaninda calisir)
        self.target_p = (clean_cm[0] * CM_TO_M, clean_cm[1] * CM_TO_M,
                         clean_cm[2] * CM_TO_M)
        gs = self.filter.guidance_state()
        if gs is not None:   # ⭐ hiz = ILERI BESLEME girdisi
            v = gs["vel"]
            self.target_v = (v[0] * CM_TO_M, v[1] * CM_TO_M, v[2] * CM_TO_M)
            # Hedefin GIDIS YONU: istasyonu kuyruga kurmak icin gerekir.
            # Yavasken atan2 gurultuden ibarettir -> son guvenilir yon tutulur.
            speed_horiz = math.hypot(self.target_v[0], self.target_v[1])
            if speed_horiz > self.cfg.HEADING_MIN_SPEED:
                self.target_heading = math.degrees(math.atan2(self.target_v[1],
                                                              self.target_v[0]))
        return self.target_p

    # ================================================================
    #  KONTROL ADIMI
    # ================================================================
    def step(self):
        """Bir tik istasyon tutma. ⚠ Arac ZATEN HAVADA varsayilir: kalkis
        `control/takeoff.py`de, karari gozetmendedir."""
        dp = self.tlm.position_m()
        _roll, _pitch, yaw = self.tlm.orientation_deg()
        v_meas = self.tlm.velocity_ms()
        hp = self.clean_target()

        # ---- HEDEF YOK: irtifayi tut, savrulma ----
        if hp is None:
            self.range_h = None
            self.station_err = None
            self.sender.loiter()
            self.diag = {"state": "NO_TARGET"}
            return

        # ---- ISTASYON TUTMA ----
        (vx, vy), vz_ned, yaw_rate, diag = command(dp, yaw, hp, self.target_v,
                                                   self.target_heading, self.cfg)
        thr, pitch, roll, yaw_c = self.conv.convert((vx, vy, vz_ned), v_meas,
                                                    math.radians(yaw), yaw_rate)
        self.sender.send(thr, pitch, roll, yaw_c)

        self.range_h = diag["target_range_m"]  # gozetmen (devir kapisi) okur
        self.station_err = diag["station_err_m"]
        diag.update(self.conv.diag)
        diag["state"] = "STATION"
        diag["filter"] = self.filter.diag()  # kapi/kacis teshisi (gosterge)
        self.diag = diag

    # ----------------------------------------------------------------
    def status(self):
        """Son tikin ic degerleri (konsol/arayuz icin; guduume GIRMEZ)."""
        return dict(self.diag)

# -*- coding: utf-8 -*-
"""
control/takeoff.py — KALKIS YASASI (yalniz DIKEY tirmanis).

Bu dosya bir YASA'dir: hiz setpoint'i uretir ve OLCULMUS cevirici ile cubuga
cevirip gonderir. FAZ KARARI BURADA DEGILDIR — "kalkis bitti mi?" sorusunu
`control/main.py :: PhaseSupervisor.takeoff_tick` yanitlar.

    YASA (bu dosya)   ->  ne kadar hizli tirmanalim  (TakeoffCfg.VZ)
    KAPI (main.py)    ->  ne zaman bitti             (Cfg.TAKEOFF_ALT_M / _TOL_M)

Ayrim bilinclidir ve projenin geri kalaniyla ayni: kapi esikleri TEK YERDE,
gozetmende durur. Esik yasanin icine kacarsa kosturucu degistiginde kapinin
da degismesi mumkun olur; kardes depoda faz cirpinmasinin kok nedeni buydu.

⛔ YATAY KOMUT YOKTUR — pitch/roll/yaw kalkis boyunca SIFIRDIR.
  Sebep olculdu: GNSS filtresinin ISINMA TRANSIENTI ilk ~4 saniyededir
  (pencere medyani 23.6 m, max 52 m). Kalkis tam o pencereyi kapatir; yatay
  komut uretmedigimiz icin transient guduume HIC girmez. Kalkisi kisaltirsaniz
  ya da buraya yatay komut eklerseniz bu maske KALKAR.

⚠ ZEMIN REFERANSI ilk `step()` cagrisinda alinir (arm ani). `height` MUTLAK
  irtifa degil, o referansa GORELIDIR — oyun haritasinin z sifiri nerede
  olursa olsun 45 m hep 45 m'dir.
"""
import math

from control.common import Telemetry, VelocityToStick


class TakeoffCfg:
    # ⚠ YASA parametresi (ne kadar hizli), KAPI DEGIL. "Ne zaman bitti"
    #   esikleri control/main.py :: Cfg.TAKEOFF_* icindedir.
    VZ = 12.0  # m/s; tirmanma hizi setpoint'i (zarf tavani 33.51 — bilincli dusuk:
               #  sert tirmanis throttle'i sicratir, kamera govdeye sabittir)


class TakeoffLaw:
    """Dikey tirmanis. Her tik `step()` cagrilir (50 Hz); faz karari CAGIRANA aittir.

    Kapinin okudugu iki alan:
      height : m, zemine goreli yukseklik
      alt_z  : m, mutlak z (hedefin irtifasiyla karsilastirma icin)
    """

    def __init__(self, drone, sender, cfg=TakeoffCfg):
        self.cfg = cfg
        self.tlm = Telemetry(drone)
        self.sender = sender
        self.conv = VelocityToStick()  # DURUMSUZ; faz devrinde tasinacak sey yok
        self.reset()

    # ----------------------------------------------------------------
    def reset(self):
        """Yeni gorev: zemin referansi ve yukseklik sifirlanir."""
        self._ground_z = None
        self.height = 0.0
        self.alt_z = 0.0
        self.diag = {}

    # ----------------------------------------------------------------
    def step(self):
        """Bir tik: tirmanma komutunu gonder, `height`/`alt_z` alanlarini tazele."""
        dp = self.tlm.position_m()
        _roll, _pitch, yaw = self.tlm.orientation_deg()
        v_meas = self.tlm.velocity_ms()

        if self._ground_z is None:
            self._ground_z = dp[2]  # ARM anindaki zemin
        self.alt_z = dp[2]
        self.height = dp[2] - self._ground_z

        # ⚠ vz_ned: POZITIF = ASAGI -> tirmanmak icin NEGATIF verilir.
        thr, _pitch_c, _roll_c, _yaw_c = self.conv.convert(
            (0.0, 0.0, -self.cfg.VZ), v_meas, math.radians(yaw), 0.0)
        self.sender.send(thr, 0.0, 0.0, 0.0)

        self.diag = {"state": "TAKEOFF", "height": self.height,
                     "vz_cmd": self.cfg.VZ, "thr": thr}

    # ----------------------------------------------------------------
    def status(self):
        """Son tikin ic degerleri (konsol/arayuz icin; guduume GIRMEZ)."""
        return dict(self.diag)

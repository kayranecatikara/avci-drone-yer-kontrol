# -*- coding: utf-8 -*-
"""
control/takeoff.py — KALKIŞ FAZI: yalnız dikey tırmanış yasası

Faz akışının ilk halkasıdır (KALKIŞ -> GPS -> GÖRSEL -> ÇARPMA). Tek işi
sabit hızla tırmanmaktır; "kalkış bitti mi?" kararı burada DEĞİL,
`control/main.py :: PhaseSupervisor.takeoff_tick` içindedir — yasa ile kapı
bilinçli olarak ayrı tutulur.

⛔ KALKIŞTA YATAY KOMUT YOKTUR ve bu bir tercih değil, bir KORUMADIR.
   GNSS filtresinin ısınma transienti ilk ~4 saniyededir (pencere medyanı
   23.6 m, max 52 m) ve kalkış tam o pencereyi kapatır: o sırada yatay komut
   üretilmediği için transient güdüme HİÇ girmez. `step()` bu yüzden
   pitch/roll/yaw kanallarına sıfır yazar. Buraya yatay komut eklenirse
   maske kalkar ve 23.6 m medyanlı hata doğrudan güdüme girer.
"""
import math

from control.common import Telemetry, VelocityToStick


class TakeoffCfg:
    """Kalkış yasasının tek ayarı."""

    VZ = 12.0  # m/s; kalkışta istenen SABİT tırmanma hızı (yukarı pozitif).
               # Aracın tavanı 33.51 m/s; kasıtlı olarak çok altında tutulur —
               # kalkışın kısalması GNSS filtresinin ısınma maskesini daraltır
               # (bkz. modül başlığı).


class TakeoffLaw:
    """Dikey tırmanış yasası — sabit `TakeoffCfg.VZ` ile yukarı.

    Kendi durumundan yalnız ZEMİN REFERANSINI tutar: ilk tikteki irtifa
    "zemin" sayılır ve `height` ona göre ölçülür. Faz kararı vermez.
    """

    def __init__(self, drone, sender, cfg=TakeoffCfg):
        """drone: SDK; sender: TEK komut kapısı; cfg: kalkış ayarları."""
        self.cfg = cfg
        self.tlm = Telemetry(drone)
        self.sender = sender
        self.conv = VelocityToStick()
        self.reset()

    def reset(self):
        """Yeni görev: zemin referansını ve yüksekliği sıfırlar.

        ⚠ ZEMİN REFERANSI HAVADA DA ALINIR — bilinçli. Görev araç havadayken
          yeniden başlatılırsa ilk tikteki irtifa "zemin" sayılır ve `height`
          sıfırdan başlar. Araç bu yüzden boşuna tırmanmaz: kalkış kapısının
          2. kolu (hedefin irtifasına `TAKEOFF_TARGET_GAP_M` kadar yaklaşmak)
          bu durumu zaten karşılar ve faz hemen biter.
        """
        self._ground_z = None  # m; ilk tikte okunan "zemin" irtifası
        self.height = 0.0      # m; zemine göreli yükseklik (kalkış kapısının 1. kolu)
        self.alt_z = 0.0       # m; mutlak z (kapının 2. kolu bunu hedefinkiyle karşılaştırır)
        self.diag = {}

    def step(self):
        """Bir kalkış tiki: sabit tırmanma hızını çubuğa çevirip gönderir.

        Yalnız throttle yazılır; pitch/roll/yaw SIFIRDIR (bkz. modül başlığı).
        Kapı için gereken `height` ve `alt_z` bu adımda tazelenir.
        """
        dp = self.tlm.position_m()
        _roll, _pitch, yaw = self.tlm.orientation_deg()
        v_meas = self.tlm.velocity_ms()

        if self._ground_z is None:
            self._ground_z = dp[2]
        self.alt_z = dp[2]
        self.height = dp[2] - self._ground_z

        thr, _pitch_c, _roll_c, _yaw_c = self.conv.convert((0.0, 0.0, -self.cfg.VZ), v_meas, math.radians(yaw), 0.0)
        self.sender.send(thr, 0.0, 0.0, 0.0)

        self.diag = {"state": "TAKEOFF", "height": self.height, "vz_cmd": self.cfg.VZ, "thr": thr}

    def status(self):
        """Son tikin telemetrisi (yalnız gösterge; komuta girmez)."""
        return dict(self.diag)

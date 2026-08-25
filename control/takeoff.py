# -*- coding: utf-8 -*-
"""
control/takeoff.py — Kalkış
"""
import math

from control.common import Telemetry, VelocityToStick


class TakeoffCfg:
    VZ = 12.0  # m/s; Tırmanma hızı


class TakeoffLaw:
    """Dikey tırmanış"""

    def __init__(self, drone, sender, cfg=TakeoffCfg):
        self.cfg = cfg
        self.tlm = Telemetry(drone)
        self.sender = sender
        self.conv = VelocityToStick()
        self.reset()

    def reset(self):
        """Zemin referansı ve yüksekliği sıfırlar."""
        self._ground_z = None
        self.height = 0.0
        self.alt_z = 0.0
        self.diag = {}

    def step(self):
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
        return dict(self.diag)

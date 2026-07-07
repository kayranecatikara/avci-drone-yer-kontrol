# -*- coding: utf-8 -*-
"""
Hedef manevra modelleri (kinematik).

Hepsi ortak arayuz sunar:
    t.p  -> konum (3B numpy)
    t.v  -> hiz (3B numpy)
    t.step(dt) -> bir adim ilerlet

Modeller:
    CV   - sabit hiz (duz ucus)
    CA   - sabit ivme (giderek hizlanan)
    SM   - sinuzoidal/yilankavi: yatay duzlemde yanal ivme = A*sin(2*pi*f*t)
    TURN - sabit donus hiziyla dairesel viraj (+ opsiyonel dikey hiz)
"""
import numpy as np


class _TargetBase:
    def __init__(self, p0, v0):
        self.p = np.asarray(p0, dtype=float).copy()
        self.v = np.asarray(v0, dtype=float).copy()
        self.t = 0.0

    def step(self, dt: float):
        raise NotImplementedError


class ConstantVelocity(_TargetBase):
    """CV: duz, sabit hizli ucus."""
    def step(self, dt):
        self.p += self.v * dt
        self.t += dt


class ConstantAcceleration(_TargetBase):
    """CA: sabit ivmeyle hizlanan hedef."""
    def __init__(self, p0, v0, a):
        super().__init__(p0, v0)
        self.a = np.asarray(a, dtype=float)

    def step(self, dt):
        self.v += self.a * dt
        self.p += self.v * dt
        self.t += dt


class Sinusoidal(_TargetBase):
    """
    SM: ileri hiz sabit, yatay duzlemde yanal ivme A*sin(2*pi*f*t).
    Yanal ivme, hiz vektorune dik (yatay duzlemde, z-ekseni etrafinda 90 derece
    dondurulmus) yonde uygulanir; sonra hiz eski buyuklugune normalize edilir
    ("ileri hiz sabit" kosulunu saglamak icin).
    """
    def __init__(self, p0, v0, amp, freq):
        super().__init__(p0, v0)
        self.amp = float(amp)
        self.freq = float(freq)
        self.speed0 = np.linalg.norm(self.v)

    def step(self, dt):
        # yatay hiz yonune dik birim vektor (z etrafinda +90 derece)
        vh = self.v.copy(); vh[2] = 0.0
        n = np.linalg.norm(vh)
        if n > 1e-9:
            perp = np.array([-vh[1], vh[0], 0.0]) / n
        else:
            perp = np.array([0.0, 1.0, 0.0])
        a_lat = self.amp * np.sin(2.0 * np.pi * self.freq * self.t) * perp
        self.v += a_lat * dt
        # hizi sabit tut (yalnizca yon degisir)
        sp = np.linalg.norm(self.v)
        if sp > 1e-9:
            self.v *= self.speed0 / sp
        self.p += self.v * dt
        self.t += dt


class Turning(_TargetBase):
    """
    TURN: yatay duzlemde sabit acisal hizla (omega) donus = dairesel viraj.
    Hiz vektorunun yatay bileseni her adimda omega*dt kadar dondurulur.
    Opsiyonel vz ile sarmal (helis) yorunge elde edilir.
    Donus yaricapi R = |v_yatay| / |omega|.
    """
    def __init__(self, p0, v0, omega, vz=0.0):
        super().__init__(p0, v0)
        self.omega = float(omega)
        self.v[2] = float(vz)

    def step(self, dt):
        c, s = np.cos(self.omega * dt), np.sin(self.omega * dt)
        vx, vy = self.v[0], self.v[1]
        self.v[0] = c * vx - s * vy
        self.v[1] = s * vx + c * vy
        self.p += self.v * dt
        self.t += dt


def make_target(params: dict) -> _TargetBase:
    """config.SCENARIOS sozlugunden hedef nesnesi uret."""
    p = dict(params)          # orijinali bozma
    model = p.pop("model")
    if model == "cv":
        return ConstantVelocity(p["p0"], p["v0"])
    if model == "ca":
        return ConstantAcceleration(p["p0"], p["v0"], p["a"])
    if model == "sm":
        return Sinusoidal(p["p0"], p["v0"], p["amp"], p["freq"])
    if model == "turn":
        return Turning(p["p0"], p["v0"], p["omega"], p.get("vz", 0.0))
    raise ValueError(f"Bilinmeyen hedef modeli: {model!r}")

# -*- coding: utf-8 -*-
"""
Onleyici (interceptor) dinamigi - nokta-kutle modeli.

Durum: konum p (3B), hiz v (3B).
Kisitlar: |a_yanal| <= a_max, |v| <= v_max.

VARSAYIM: Yercekimi, aracin itki sistemi tarafindan surekli telafi edilir
(hover-yetenekli cok-rotor). Yani gudumden gelen a_cmd "net" ivmedir;
entegrasyona ayrica -g eklenmez. Ileride gercekci cok-rotor modelinde
egim/itki limitleriyle birlikte acik yercekimi eklenebilir (README/M6).
"""
import numpy as np


class Interceptor:
    """Nokta-kutle onleyici. step() ile gudum komutunu entegre eder."""

    def __init__(self, p0, v0, v_max: float, a_max: float, k_speed: float):
        self.p = np.asarray(p0, dtype=float).copy()
        self.v = np.asarray(v0, dtype=float).copy()
        self.v_max = float(v_max)
        self.a_max = float(a_max)
        self.k_speed = float(k_speed)
        self.last_a = np.zeros(3)   # metrik icin son uygulanan toplam ivme

    def step(self, a_lat_cmd: np.ndarray, r_hat: np.ndarray, dt: float):
        """
        a_lat_cmd : gudumden gelen yanal ivme komutu (zaten a_max ile kirpilmis olmali,
                    yine de burada guvenlik icin tekrar kirpilir)
        r_hat     : LOS birim vektoru (ileri ivme bu yonde eklenir)
        """
        # Guvenlik kirpmasi: yanal komut a_max'i asamaz (yonu korunarak)
        a_lat = clip_norm(np.asarray(a_lat_cmd, dtype=float), self.a_max)

        # Hiz tutma: v_max'a ulasmak/korumak icin LOS yonunde ileri ivme (basit P)
        speed = np.linalg.norm(self.v)
        a_fwd = self.k_speed * (self.v_max - speed) * np.asarray(r_hat, dtype=float)

        # Toplam ivme de itki limitini asamaz: |a_lat + a_fwd| <= a_max.
        # (Yanal manevra ile hizlanma ayni itki butcesini paylasir.)
        a_total = clip_norm(a_lat + a_fwd, self.a_max)
        self.last_a = a_total

        # Entegrasyon (yari-ortuk Euler): once hiz, sonra konum
        self.v = self.v + a_total * dt
        self.v = clip_norm(self.v, self.v_max)   # hiz limiti
        self.p = self.p + self.v * dt


def clip_norm(vec: np.ndarray, max_norm: float) -> np.ndarray:
    """Vektoru, YONUNU KORUYARAK |vec| <= max_norm olacak sekilde kirp."""
    n = np.linalg.norm(vec)
    if n > max_norm and n > 0.0:
        return vec * (max_norm / n)
    return vec

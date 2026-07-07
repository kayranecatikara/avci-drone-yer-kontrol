# -*- coding: utf-8 -*-
"""
PNG interceptor simulasyonu - merkezi konfigurasyon.

Tum fiziksel parametreler, gudum sabitleri ve hedef senaryo tanimlari burada.
Deger degistirmek icin bu dosyayi duzenlemek yeterli; kod tarafinda sabit yok.
"""
from dataclasses import dataclass, field
import numpy as np


@dataclass
class SimConfig:
    # --- Zaman ---
    dt: float = 0.01          # entegrasyon adimi [s] (100 Hz)
    t_max: float = 60.0       # zaman asimi [s]

    # --- Onleyici (interceptor) kisitlari ---
    v_max: float = 22.0       # maksimum hiz [m/s]
    a_max: float = 30.0       # maksimum yanal ivme [m/s^2] (~3g)
    k_speed: float = 4.0      # hiz tutma kazanci (ileri ivme icin P kazanci)
    p0_i: tuple = (0.0, 0.0, 10.0)   # baslangic konumu [m]
    v0_i: tuple = (5.0, 0.0, 0.0)    # baslangic hizi [m/s]

    # --- Gudum ---
    N: float = 4.0            # PN navigasyon sabiti (tipik 3..5)
    k_pursuit: float = 2.0    # pure pursuit kazanci

    # --- Isabet / sonlandirma ---
    r_interceptor: float = 0.15   # onleyici yaricapi [m]
    r_target: float = 0.25        # hedef yaricapi [m]
    # isabet esigi = iki yaricap toplami + pay
    r_hit: float = 0.5            # R < r_hit ise DALIS BASARILI [m]
    escape_r: float = 400.0       # R bunu asar ve acilmaya devam ederse "hedef kacti"
    escape_time: float = 3.0      # kac saniye kesintisiz acilirsa kacti sayilir [s]

    # --- Tekrarureti̇lebi̇li̇rli̇k ---
    seed: int = 42

    # --- Hedef senaryosu (target_models.make_target bunlari okur) ---
    scenario: str = "turning"
    target_params: dict = field(default_factory=dict)


# Senaryo on-tanimlari: hedefin baslangic konumu/hizi + manevra parametreleri.
# Hepsi yatay duzlemde ~40-80 m mesafeden baslar; onleyici (0,0,10)'da.
SCENARIOS = {
    # Sabit hizli duz ucus
    "cv": dict(
        model="cv",
        p0=(60.0, 40.0, 20.0),
        v0=(-6.0, 4.0, 0.0),
    ),
    # Sabit ivmeyle hizlanan hedef
    "ca": dict(
        model="ca",
        p0=(60.0, 40.0, 20.0),
        v0=(-4.0, 3.0, 0.0),
        a=(1.5, 1.0, 0.0),          # sabit ivme [m/s^2]
    ),
    # Sinuzoidal / yilankavi manevra
    "sm": dict(
        model="sm",
        p0=(70.0, 0.0, 20.0),
        v0=(-8.0, 0.0, 0.0),
        amp=8.0,                    # yanal ivme genligi A [m/s^2]
        freq=0.25,                  # sinus frekansi f [Hz]
    ),
    # EN ONEMLISI: sabit donus hiziyla viraj (dairesel)
    "turning": dict(
        model="turn",
        p0=(70.0, 0.0, 20.0),
        v0=(0.0, 12.0, 0.0),
        omega=np.deg2rad(20.0),     # donus hizi [rad/s] (+: saat yonu tersi)
        vz=0.0,                     # opsiyonel dikey hiz bileseni [m/s]
    ),
}


def make_config(scenario: str = "turning", **overrides) -> SimConfig:
    """Senaryo adi verip hazir konfigurasyon uret."""
    if scenario not in SCENARIOS:
        raise ValueError(f"Bilinmeyen senaryo: {scenario!r}. Secenekler: {list(SCENARIOS)}")
    cfg = SimConfig(scenario=scenario, target_params=dict(SCENARIOS[scenario]))
    for k, v in overrides.items():
        if not hasattr(cfg, k):
            raise AttributeError(f"SimConfig'te olmayan alan: {k}")
        setattr(cfg, k, v)
    return cfg

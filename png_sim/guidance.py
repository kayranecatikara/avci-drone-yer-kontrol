# -*- coding: utf-8 -*-
"""
Gudum yasalari - projenin kalbi.

Ortak arayuz:
    a_cmd = law(p_i, v_i, p_t, v_t)   ->  yanal ivme komutu (3B, |a| <= a_max)

1) PNG (vektorel / true proportional navigation) - ANA yontem:
   Gorus hatti (LOS) donme vektoru Omega'yi sifira surer. LOS donmuyorsa
   geometri "carpisma ucgeni"ne oturmustur: hedef donse bile onleyici hedefin
   GIDECEGI noktaya nisan alir (kose keser) -> mumkun olan en kisa yol.

     r     = p_t - p_i                  (LOS vektoru)
     v_rel = v_t - v_i                  (bagil hiz)
     Vc    = -(r . v_rel) / |r|         (kapanma hizi; + ise yaklasiyoruz)
     Omega = (r x v_rel) / (r . r)      (LOS donme vektoru)
     a_cmd = N * Vc * (Omega x r_hat)   (yanal PN komutu, N ~ 3..5)

2) Pure pursuit (saf takip) - SADECE kiyas baz cizgisi:
   Hiz vektorunu her an hedefin SU ANKI konumuna yoneltir. Hedef donunce
   "kuyruk kovalamasi"na duser: surekli hedefin eski yerine kosar, kavisli
   ve daha UZUN bir yol izler. PNG ile fark tam burada gorunur.
"""
import numpy as np
from dynamics import clip_norm


class PNG:
    """Oransal seyrusefer gudumu (true PN, vektorel form)."""

    name = "PNG"

    def __init__(self, N: float, a_max: float, v_max: float):
        self.N = float(N)
        self.a_max = float(a_max)
        self.v_max = float(v_max)

    def command(self, p_i, v_i, p_t, v_t) -> np.ndarray:
        r = p_t - p_i
        R = np.linalg.norm(r)
        if R < 1e-9:
            return np.zeros(3)
        r_hat = r / R
        v_rel = v_t - v_i

        vc = -float(np.dot(r, v_rel)) / R              # kapanma hizi
        omega = np.cross(r, v_rel) / float(np.dot(r, r))  # LOS donme vektoru
        a_cmd = self.N * vc * np.cross(omega, r_hat)   # yanal PN ivmesi

        # Kapanma hizi negatifse (aciliyoruz) PN terimi ters yonde is gorur;
        # bu durumda once burnu hedefe cevirmek icin pursuit benzeri yardimci
        # terim ekle (PN, Vc>0 rejiminde anlamlidir).
        if vc <= 0.0:
            a_cmd = a_cmd + self.a_max * r_hat

        # Yonu koruyarak a_max'a kirp
        return clip_norm(a_cmd, self.a_max)


class PurePursuit:
    """Saf takip: hiz vektorunu hedefin su anki konumuna yonelt (kiyas icin)."""

    name = "PurePursuit"

    def __init__(self, k: float, a_max: float, v_max: float):
        self.k = float(k)
        self.a_max = float(a_max)
        self.v_max = float(v_max)

    def command(self, p_i, v_i, p_t, v_t) -> np.ndarray:
        r = p_t - p_i
        R = np.linalg.norm(r)
        if R < 1e-9:
            return np.zeros(3)
        d = r / R                                   # istenen hiz yonu
        a_cmd = self.k * (self.v_max * d - v_i)     # hiz vektorunu d'ye sur
        return clip_norm(a_cmd, self.a_max)


def make_guidance(name: str, cfg):
    """Isimden gudum nesnesi uret ('png' | 'pursuit')."""
    name = name.lower()
    if name == "png":
        return PNG(cfg.N, cfg.a_max, cfg.v_max)
    if name in ("pursuit", "pure_pursuit", "pp"):
        return PurePursuit(cfg.k_pursuit, cfg.a_max, cfg.v_max)
    raise ValueError(f"Bilinmeyen gudum: {name!r} ('png' veya 'pursuit')")

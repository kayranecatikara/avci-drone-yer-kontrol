# -*- coding: utf-8 -*-
"""
================================================================================
GUDUM YASASI — APN + OIPN (YARISMA PIPELINE FAZ 3)
================================================================================
GORSEL_TAKIP birincil hatti. Orta-safha kilit-tutma/takip iyilestirmesi;
TERMINAL vurus mantigina (ana_kontrol carpisma-rotasi) DOKUNMAZ.

  a_cmd = N·Vc·λ̇  +  (N/2)·a_T  +  β·a_ff
          [--- APN ---]  [--- OIPN ---]

- APN (Augmented Proportional Navigation): N·Vc·λ̇ orantili seyrusefer +
  (N/2)·a_T hedef-ivme telafisi. λ̇ (LOS acisal hizi) ve Vc (kapanma) ALGI
  hattinda hazir (turev kurali); a_T fusion'dan (yoksa 0, yorumla belgeli).
- OIPN (Orientation-Informed PN): a_ff = g·tan(φ_T), hedef hiz vektorune dik
  yatayda. Fizik: koordineli donuste ψ̇ = (g/V_T)·tan(φ_T) — ROLL heading
  degisiminden ONCE gelir; erken manevra sinyali budur. V_T fusion/EKF'ten
  (PnP relatif olcumdur, hedef yer hizini tek basina VERMEZ). φ_T PnP'den.
  β konservatif (0.3): EKF a_T'si ayni manevrayi yakalayinca OIPN cift-sayabilir;
  |φ_T|<5 dead-zone (gurultu roll'u sizmasin). PnP gecersizse OIPN terimi 0.

- FALLBACK: PnP gecersiz VE OIPN yok -> ibvs_guidance (bbox merkez hatasi) devrede
  (frame bazinda; ana_kontrol _send prev surekliligi -> sarsintisiz gecis).
  IBVS SILINMEZ, guvenlik agidir.

SAF hesap: sim/guduum durumundan bagimsiz -> sentetik girdiyle unit test.
Cikti: LOS'a dik ivme komutu (dunya duzlemi) + bilesenler (log/tune).
================================================================================
"""
import math


class GudumCfg:
    N = 4.0             # PN sabiti (baslangic)
    BETA = 0.3          # OIPN feedforward katsayisi (konservatif; canli slider)
    OIPN_DEADZONE_DEG = 5.0   # |φ_T| bu esik altinda OIPN 0 (gurultu bastir)
    G = 981.0           # cm/s^2 (yer cekimi; birim cm/s ile tutarli)
    A_MAX = 981.0 * math.tan(math.radians(40.0))   # yatay ivme tavani (~40 deg yatis)


def _birim(vx, vy):
    n = math.hypot(vx, vy)
    return (vx / n, vy / n) if n > 1e-9 else (0.0, 0.0)


def apn_oipn(lam_dot, Vc, los_yon, a_T=None, phi_T=None, V_T=None,
            oipn_acik=True, cfg=None, beta=None):
    """APN + OIPN ivme komutu (dunya yatay duzlem, cm/s^2).

    lam_dot : LOS acisal hizi (rad/s; algi hattindan)
    Vc      : kapanma hizi (cm/s; + = yaklasiyor)
    los_yon : LOS birim vektoru (dunya yatay) (ux, uy)
    a_T     : hedef ivme vektoru (cm/s^2, dunya) | None (fusion'dan; yoksa 0)
    phi_T   : hedef roll (derece; PnP'den) | None -> OIPN 0
    V_T     : hedef yer hizi (cm/s; fusion'dan) | None -> OIPN 0
    oipn_acik: OIPN terimi devrede mi (arayuz anahtari)
    beta    : OIPN feedforward katsayisi (canli-tune; None -> cfg.BETA)
    -> {a_cmd:(ax,ay), a_pn, a_apn, a_oipn, kullanildi}
    """
    c = cfg or GudumCfg()
    b_oipn = c.BETA if beta is None else float(beta)
    ux, uy = los_yon
    # LOS'a dik birim (saga-dik): (uy, -ux). PN ivmesi bu yonde, buyukluk N·Vc·λ̇.
    px, py = uy, -ux
    a_pn_mag = c.N * Vc * lam_dot
    ax = a_pn_mag * px
    ay = a_pn_mag * py

    # APN: hedef ivme telafisi (N/2)·a_T (LOS'a dik bileseni)
    a_apn_mag = 0.0
    if a_T is not None:
        aTx, aTy = a_T
        a_apn_mag = (c.N / 2.0) * (aTx * px + aTy * py)   # dik bilesen
        ax += a_apn_mag * px
        ay += a_apn_mag * py

    # OIPN: a_ff = g·tan(φ_T), hedef hiz vektorune dik yatayda, LOS'a dik izdusum
    a_oipn_mag = 0.0
    kullanildi = "APN"
    if (oipn_acik and phi_T is not None and V_T is not None
            and abs(phi_T) >= c.OIPN_DEADZONE_DEG):
        # hedef hiz yonu = -Vc·LOS + ... (yaklasik LOS; V_T buyuklugu). Basit:
        # hedef hiz vektorune dik yatay = LOS'a dik (yakin geometri) -> px,py.
        a_ff = c.G * math.tan(math.radians(phi_T))
        a_oipn_mag = b_oipn * a_ff
        ax += a_oipn_mag * px
        ay += a_oipn_mag * py
        kullanildi = "APN+OIPN"

    # toplam ivme tavani
    am = math.hypot(ax, ay)
    if am > c.A_MAX:
        ax *= c.A_MAX / am
        ay *= c.A_MAX / am

    return {"a_cmd": (ax, ay), "a_pn": a_pn_mag, "a_apn": a_apn_mag,
            "a_oipn": a_oipn_mag, "kullanildi": kullanildi}

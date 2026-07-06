# -*- coding: utf-8 -*-
"""
Ana simulasyon dongusu.

Her adimda (sabit dt):
  1. hedefi guncelle
  2. LOS buyukluklerini hesapla
  3. secili gudumden a_cmd al
  4. onleyiciyi entegre et
  5. isabet / zaman asimi / kacis kontrolu
  6. durumu logla
"""
from dataclasses import dataclass, field
import numpy as np

from config import SimConfig
from dynamics import Interceptor
from target_models import make_target
from guidance import make_guidance


@dataclass
class SimResult:
    """Tum zaman serileri + sonlanma bilgisi."""
    t: np.ndarray = None          # [n]
    p_i: np.ndarray = None        # onleyici konum [n,3]
    v_i: np.ndarray = None        # onleyici hiz   [n,3]
    a_i: np.ndarray = None        # uygulanan ivme [n,3]
    p_t: np.ndarray = None        # hedef konum    [n,3]
    v_t: np.ndarray = None        # hedef hiz      [n,3]
    range_: np.ndarray = None     # |r| [n]
    vc: np.ndarray = None         # kapanma hizi [n]
    dt: float = 0.0
    hit: bool = False
    hit_index: int = -1
    end_reason: str = ""
    guidance_name: str = ""
    scenario: str = ""


def run_sim(cfg: SimConfig, guidance_name: str = "png") -> SimResult:
    """Bir senaryoyu verilen gudumle kos, tum zaman serisini dondur."""
    rng = np.random.default_rng(cfg.seed)   # su an gurultu yok; M6 Monte Carlo icin hazir
    _ = rng

    target = make_target(cfg.target_params)
    law = make_guidance(guidance_name, cfg)
    intc = Interceptor(cfg.p0_i, cfg.v0_i, cfg.v_max, cfg.a_max, cfg.k_speed)

    n_max = int(cfg.t_max / cfg.dt) + 1
    log = {k: [] for k in ("t", "p_i", "v_i", "a_i", "p_t", "v_t", "R", "vc")}

    hit, hit_index, end_reason = False, -1, "zaman asimi"
    opening_time = 0.0   # kesintisiz acilma suresi (kacis tespiti)

    for k in range(n_max):
        t = k * cfg.dt

        # LOS buyuklukleri
        r = target.p - intc.p
        R = float(np.linalg.norm(r))
        r_hat = r / R if R > 1e-9 else np.zeros(3)
        v_rel = target.v - intc.v
        vc = -float(np.dot(r, v_rel)) / R if R > 1e-9 else 0.0

        # logla
        log["t"].append(t)
        log["p_i"].append(intc.p.copy()); log["v_i"].append(intc.v.copy())
        log["p_t"].append(target.p.copy()); log["v_t"].append(target.v.copy())
        log["R"].append(R); log["vc"].append(vc)

        # isabet kontrolu
        if R < cfg.r_hit:
            hit, hit_index, end_reason = True, k, "ISABET"
            log["a_i"].append(np.zeros(3))
            break

        # kacis kontrolu: uzak + surekli acilma
        if vc < 0.0 and R > cfg.escape_r:
            opening_time += cfg.dt
            if opening_time >= cfg.escape_time:
                end_reason = "hedef kacti"
                log["a_i"].append(np.zeros(3))
                break
        else:
            opening_time = 0.0

        # gudum + entegrasyon
        a_cmd = law.command(intc.p, intc.v, target.p, target.v)
        intc.step(a_cmd, r_hat, cfg.dt)
        target.step(cfg.dt)
        log["a_i"].append(intc.last_a.copy())

    return SimResult(
        t=np.array(log["t"]),
        p_i=np.array(log["p_i"]), v_i=np.array(log["v_i"]), a_i=np.array(log["a_i"]),
        p_t=np.array(log["p_t"]), v_t=np.array(log["v_t"]),
        range_=np.array(log["R"]), vc=np.array(log["vc"]),
        dt=cfg.dt, hit=hit, hit_index=hit_index, end_reason=end_reason,
        guidance_name=law.name, scenario=cfg.scenario,
    )

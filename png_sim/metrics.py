# -*- coding: utf-8 -*-
"""
Yakalama kriteri ve performans metrikleri.

Simulasyon kaydindan (SimResult) hesaplanan metrikler:
  hit               : R < r_hit gerceklesti mi (dalis basarili)
  miss_distance     : minimum R (en yakin gecis mesafesi; CEP benzeri hassasiyet)
  time_to_intercept : isabet ani [s] (isabet yoksa None)
  path_length       : onleyici yol uzunlugu = integral |v_i| dt [m]
  max_lat_accel     : uygulanan maksimum ivme buyuklugu [m/s^2]
  vc_profile        : kapanma hizi zaman serisi (grafik icin)
"""
import numpy as np


def compute_metrics(res) -> dict:
    """res: simulator.SimResult"""
    R = res.range_          # |r| zaman serisi
    miss = float(np.min(R))
    hit = bool(res.hit)
    tti = float(res.t[res.hit_index]) if hit else None
    speed = np.linalg.norm(res.v_i, axis=1)
    path_length = float(np.sum(speed * res.dt))
    max_lat = float(np.max(np.linalg.norm(res.a_i, axis=1))) if len(res.a_i) else 0.0
    return {
        "guidance": res.guidance_name,
        "scenario": res.scenario,
        "hit": hit,
        "miss_distance": miss,
        "time_to_intercept": tti,
        "path_length": path_length,
        "max_lat_accel": max_lat,
        "end_reason": res.end_reason,
    }


def format_metrics(m: dict) -> str:
    """Konsol icin tek satirlik ozet."""
    tti = f"{m['time_to_intercept']:.2f} s" if m["time_to_intercept"] is not None else "-"
    return (f"[{m['guidance']:>11s} | {m['scenario']:>7s}] "
            f"isabet={'EVET' if m['hit'] else 'HAYIR'}  "
            f"iska={m['miss_distance']:.3f} m  sure={tti}  "
            f"yol={m['path_length']:.1f} m  maks_ivme={m['max_lat_accel']:.1f} m/s^2  "
            f"({m['end_reason']})")


def format_table(rows: list) -> str:
    """PNG-vs-pursuit karsilastirma tablosu (M4 ciktisi)."""
    hdr = f"{'Senaryo':<9}{'Gudum':<13}{'Isabet':<8}{'Iska [m]':<11}{'Sure [s]':<10}{'Yol [m]':<10}{'MaksIvme':<9}"
    lines = [hdr, "-" * len(hdr)]
    for m in rows:
        tti = f"{m['time_to_intercept']:.2f}" if m["time_to_intercept"] is not None else "-"
        lines.append(
            f"{m['scenario']:<9}{m['guidance']:<13}"
            f"{'EVET' if m['hit'] else 'HAYIR':<8}"
            f"{m['miss_distance']:<11.3f}{tti:<10}{m['path_length']:<10.1f}"
            f"{m['max_lat_accel']:<9.1f}"
        )
    return "\n".join(lines)

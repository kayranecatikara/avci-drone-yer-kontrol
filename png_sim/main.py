# -*- coding: utf-8 -*-
"""
PNG interceptor simulasyonu - komut satiri girisi.

Ornekler:
    python main.py --scenario turning --guidance png
    python main.py --scenario turning --guidance both --animate
    python main.py --compare            # tum senaryolarda PNG vs pursuit tablosu
"""
import argparse
import os

from config import make_config, SCENARIOS
from simulator import run_sim
from metrics import compute_metrics, format_metrics, format_table
import visualize


def main():
    ap = argparse.ArgumentParser(description="PNG interceptor drone simulasyonu")
    ap.add_argument("--scenario", default="turning", choices=list(SCENARIOS),
                    help="hedef manevra senaryosu (varsayilan: turning)")
    ap.add_argument("--guidance", default="png", choices=["png", "pursuit", "both"],
                    help="gudum yasasi; 'both' = ikisini kiyasla (varsayilan: png)")
    ap.add_argument("--animate", action="store_true", help="3B animasyon gif'i uret")
    ap.add_argument("--compare", action="store_true",
                    help="TUM senaryolarda PNG vs pursuit metrik tablosu (M4)")
    ap.add_argument("--outdir", default="cikti", help="cikti klasoru")
    ap.add_argument("--seed", type=int, default=None, help="random seed (config'i ezer)")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    overrides = {} if args.seed is None else {"seed": args.seed}

    if args.compare:
        rows = []
        for sc in SCENARIOS:
            cfg = make_config(sc, **overrides)
            for g in ("png", "pursuit"):
                m = compute_metrics(run_sim(cfg, g))
                rows.append(m)
                print(format_metrics(m))
        print("\n=== PNG vs Pure Pursuit karsilastirma tablosu ===")
        print(format_table(rows))
        return

    cfg = make_config(args.scenario, **overrides)
    laws = ["png", "pursuit"] if args.guidance == "both" else [args.guidance]
    results = [run_sim(cfg, g) for g in laws]
    for res in results:
        print(format_metrics(compute_metrics(res)))

    tag = f"{args.scenario}_{args.guidance}"
    p = visualize.plot_static(results, os.path.join(args.outdir, f"yorunge_{tag}.png"))
    print(f"Grafik kaydedildi: {p}")

    if args.animate:
        g = visualize.animate(results[0], os.path.join(args.outdir, f"animasyon_{tag}.gif"))
        print(f"Animasyon kaydedildi: {g}")


if __name__ == "__main__":
    main()

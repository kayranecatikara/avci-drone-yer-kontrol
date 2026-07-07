# -*- coding: utf-8 -*-
"""
Gorsellestirme: statik yorunge grafikleri + 3B animasyon (gif).

- plot_static(results, ...)  : 3B yorunge + ustten (x-y) + yandan (x-z) gorunum.
  Birden fazla sonuc (PNG + pure pursuit) ayni figurde ust uste cizilir ->
  kisa yol / uzun yol farki net gorunur. Metrik ozeti panel olarak eklenir.
- animate(result, ...)       : matplotlib FuncAnimation ile 3B animasyon,
  pillow ile gif kaydi. Birkac karede LOS cizgisi, isabette yildiz.
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")   # basliksiz/otomatik kosumda pencere acmadan kaydet
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter

from metrics import compute_metrics

RENK = {"PNG": "tab:blue", "PurePursuit": "tab:red"}


def _renk(name):
    return RENK.get(name, "tab:green")


def plot_static(results, out_path="cikti_yorunge.png", title=""):
    """results: SimResult listesi (ayni senaryo, farkli gudumler)."""
    fig = plt.figure(figsize=(14, 9))
    ax3d = fig.add_subplot(2, 2, 1, projection="3d")
    ax_xy = fig.add_subplot(2, 2, 2)
    ax_xz = fig.add_subplot(2, 2, 3)
    ax_txt = fig.add_subplot(2, 2, 4); ax_txt.axis("off")

    # hedef yorungesi (en uzun kosumdan) referans olarak siyah kesikli
    ref = max(results, key=lambda r: len(r.t))
    for ax, ix, iy in ((ax_xy, 0, 1), (ax_xz, 0, 2)):
        ax.plot(ref.p_t[:, ix], ref.p_t[:, iy], "k--", lw=1.2, label="Hedef")
    ax3d.plot(ref.p_t[:, 0], ref.p_t[:, 1], ref.p_t[:, 2], "k--", lw=1.2, label="Hedef")

    lines = []
    for res in results:
        m = compute_metrics(res)
        c = _renk(res.guidance_name)
        lbl = f"{res.guidance_name} (yol={m['path_length']:.0f} m)"
        ax3d.plot(res.p_i[:, 0], res.p_i[:, 1], res.p_i[:, 2], color=c, lw=1.8, label=lbl)
        ax_xy.plot(res.p_i[:, 0], res.p_i[:, 1], color=c, lw=1.8, label=lbl)
        ax_xz.plot(res.p_i[:, 0], res.p_i[:, 2], color=c, lw=1.8, label=lbl)
        if res.hit:   # isabet noktasi yildiz
            hp = res.p_i[res.hit_index]
            ax3d.scatter(*hp, marker="*", s=220, color=c, zorder=5)
            ax_xy.scatter(hp[0], hp[1], marker="*", s=220, color=c, zorder=5)
            ax_xz.scatter(hp[0], hp[2], marker="*", s=220, color=c, zorder=5)
        tti = f"{m['time_to_intercept']:.2f} s" if m["time_to_intercept"] is not None else "-"
        lines.append(
            f"{res.guidance_name:>12s}: isabet={'EVET' if m['hit'] else 'HAYIR'}  "
            f"iska={m['miss_distance']:.3f} m\n"
            f"{'':>12s}  sure={tti}  yol={m['path_length']:.1f} m  "
            f"maks ivme={m['max_lat_accel']:.1f} m/s2"
        )

    ax3d.set_title("3B yorunge"); ax3d.set_xlabel("x [m]"); ax3d.set_ylabel("y [m]"); ax3d.set_zlabel("z [m]")
    ax_xy.set_title("Ustten gorunum (x-y)"); ax_xy.set_xlabel("x [m]"); ax_xy.set_ylabel("y [m]")
    ax_xz.set_title("Yandan gorunum (x-z)"); ax_xz.set_xlabel("x [m]"); ax_xz.set_ylabel("z [m]")
    for ax in (ax_xy, ax_xz):
        ax.grid(alpha=0.3); ax.set_aspect("equal", adjustable="datalim"); ax.legend(fontsize=8)
    ax3d.legend(fontsize=8)

    ax_txt.set_title("Metrik ozeti")
    ax_txt.text(0.02, 0.95, "\n\n".join(lines), family="monospace", fontsize=10,
                va="top", transform=ax_txt.transAxes)

    fig.suptitle(title or f"Senaryo: {results[0].scenario}", fontsize=13)
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)
    return out_path


def animate(res, out_path="cikti_animasyon.gif", fps=25, speedup=4, los_every=25):
    """
    Tek kosumun 3B animasyonu -> gif (pillow).
    speedup  : her karede kac sim adimi atlanir (gif boyutunu makul tutar)
    los_every: kac KAREDE bir LOS cizgisi kalici cizilir
    """
    n = len(res.t)
    idx = np.arange(0, n, speedup)
    if idx[-1] != n - 1:
        idx = np.append(idx, n - 1)

    fig = plt.figure(figsize=(8, 7))
    ax = fig.add_subplot(projection="3d")

    allp = np.vstack([res.p_i, res.p_t])
    ax.set_xlim(allp[:, 0].min() - 5, allp[:, 0].max() + 5)
    ax.set_ylim(allp[:, 1].min() - 5, allp[:, 1].max() + 5)
    ax.set_zlim(allp[:, 2].min() - 5, allp[:, 2].max() + 5)
    ax.set_xlabel("x [m]"); ax.set_ylabel("y [m]"); ax.set_zlabel("z [m]")

    c = _renk(res.guidance_name)
    ln_i, = ax.plot([], [], [], color=c, lw=2, label=f"Onleyici ({res.guidance_name})")
    ln_t, = ax.plot([], [], [], "k--", lw=1.5, label="Hedef")
    pt_i, = ax.plot([], [], [], "o", color=c, ms=7)
    pt_t, = ax.plot([], [], [], "ks", ms=7)
    ttl = ax.set_title("")
    ax.legend(loc="upper left", fontsize=9)

    def update(fi):
        k = idx[fi]
        ln_i.set_data(res.p_i[:k + 1, 0], res.p_i[:k + 1, 1]); ln_i.set_3d_properties(res.p_i[:k + 1, 2])
        ln_t.set_data(res.p_t[:k + 1, 0], res.p_t[:k + 1, 1]); ln_t.set_3d_properties(res.p_t[:k + 1, 2])
        pt_i.set_data([res.p_i[k, 0]], [res.p_i[k, 1]]); pt_i.set_3d_properties([res.p_i[k, 2]])
        pt_t.set_data([res.p_t[k, 0]], [res.p_t[k, 1]]); pt_t.set_3d_properties([res.p_t[k, 2]])
        # arada bir LOS cizgisi birak (gorus hattinin donmedigini gostermek icin)
        if fi % los_every == 0:
            ax.plot([res.p_i[k, 0], res.p_t[k, 0]],
                    [res.p_i[k, 1], res.p_t[k, 1]],
                    [res.p_i[k, 2], res.p_t[k, 2]], color="gray", lw=0.6, alpha=0.6)
        ttl.set_text(f"t={res.t[k]:.2f} s   R={res.range_[k]:.1f} m   Vc={res.vc[k]:.1f} m/s")
        # son karede isabet yildizi
        if res.hit and k == idx[-1]:
            ax.scatter(*res.p_i[res.hit_index], marker="*", s=300, color="gold",
                       edgecolor="k", zorder=6)
            ttl.set_text(ttl.get_text() + "   DALIS BASARILI!")
        return ln_i, ln_t, pt_i, pt_t

    anim = FuncAnimation(fig, update, frames=len(idx), interval=1000 / fps, blit=False)
    anim.save(out_path, writer=PillowWriter(fps=fps))
    plt.close(fig)
    return out_path

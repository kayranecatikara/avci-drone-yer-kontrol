# -*- coding: utf-8 -*-
"""
kopru/olcum_faz3on.py — FAZ 3.0 ON OLCUMLERI (angajman ONCESI, salt gozlem).

TAMAMEN PASIF: gudum baglanmaz, arm edilmez, hicbir komut gonderilmez.
60 sn boyunca yalniz HEDEF telemetrisi izlenir.

  A) HEDEF HIZI: yatay hiz medyan/p95/max + manevra deseni (duz/daire/karisik).
     Karar esigi: gps_guidance V_MAX=18 — hedef 15+ ise marj kritik, 18+ ise
     angajman matematiksel kapanmaz (KULLANICIYA RAPORLANIR, karar onun).
  B) KESTIRIM GURULTUSU: gps_guidance'in kendi kestiricisi (POS_EMA=0.4 EMA
     konum + VEL_EMA=0.3 sonlu-fark hiz; gps_guidance.py:285-323 BIREBIR
     kopya) ile ham konum-farki hizinin karsilastirmasi, std.

Kullanim: python -m kopru.olcum_faz3on   (oyun PLAY'de olmali)
"""
from __future__ import annotations

import math
import time

import numpy as np

from sdk import drone_sdk as drone
from kopru.dow_kopru import CM
from kopru.olcum_faz1 import baglan_ve_dogrula

SURE_S = 60.0
# gps_guidance.Cfg sabitleri (gps_guidance.py:198-199) — import ETMIYORUZ
# (o modul pymavlink+guidance_core+vision zinciri ister; salt sabit kopyasi):
POS_EMA = 0.4
VEL_EMA = 0.3


def izle():
    print(f"[ON-OLCUM] Hedef {SURE_S:.0f} sn izleniyor (salt gozlem, komut yok)...")
    t0 = time.monotonic()
    son_ham = None
    taze = []                      # (t, x_m, y_m, z_m) yalniz YENI telemetri
    # gps_guidance kestirici durumu (birebir: est EMA + vel EMA)
    est = None
    vel = np.zeros(3)
    t_son_taze = None
    est_vel_serisi = []            # (t, vx, vy) kestirilen hedef hizi
    while time.monotonic() - t0 < SURE_S:
        tp = drone.get_target_location()
        simdi = time.monotonic()
        if tp != son_ham:
            son_ham = tp
            p = (tp[0] / CM, tp[1] / CM, tp[2] / CM)
            taze.append((simdi, p[0], p[1], p[2]))
            # --- gps_guidance:292-306 birebir ---
            if est is None:
                est = np.array(p)
            else:
                n = POS_EMA * np.array(p) + (1 - POS_EMA) * est
                if t_son_taze is not None:
                    fdt = simdi - t_son_taze
                    if 1e-3 < fdt < 2.0:
                        vel = VEL_EMA * ((n - est) / fdt) + (1 - VEL_EMA) * vel
                est = n
            t_son_taze = simdi
            est_vel_serisi.append((simdi, float(vel[0]), float(vel[1])))
        time.sleep(0.02)
    return taze, est_vel_serisi


def analiz(taze, est_vel):
    print(f"[ON-OLCUM] {len(taze)} taze ornek "
          f"({len(taze) / SURE_S:.1f} Hz etkin guncelleme)")
    # guncelleme araligi + dropout
    aralar = [taze[i][0] - taze[i-1][0] for i in range(1, len(taze))]
    dropout = [a for a in aralar if a > 0.5]
    print(f"guncelleme araligi medyan {np.median(aralar)*1000:.0f} ms; "
          f"dropout (>0.5 s) sayisi {len(dropout)}"
          + (f", en uzun {max(dropout):.1f} s" if dropout else ""))

    # ── A) HIZ: farkli taban cizgileriyle (bozuk-GPS sicramasina dayaniklilik) ──
    def taban_hiz(taban_s):
        v = []
        i0 = 0
        for i in range(len(taze)):
            while taze[i][0] - taze[i0][0] > taban_s:
                i0 += 1
            dt = taze[i][0] - taze[i0][0]
            if 0.6 * taban_s <= dt <= 1.4 * taban_s and i0 < i:
                v.append((taze[i][0],
                          (taze[i][1] - taze[i0][1]) / dt,
                          (taze[i][2] - taze[i0][2]) / dt))
        return v

    hedef_alt = [s[3] for s in taze]
    print("\n===== A) HEDEF HIZI (yatay) =====")
    v1 = taban_hiz(1.0)
    for taban_s in (1.0, 3.0, 5.0):
        v = taban_hiz(taban_s)
        spd = np.array([math.hypot(x[1], x[2]) for x in v])
        med = float(np.median(spd))
        # ROBUST: tek-ornek sicramalarini ele (|v| > 2x medyan), medyani yenile
        temiz = spd[spd <= 2.0 * med]
        print(f"taban {taban_s:.0f} s: ham medyan {med:.2f} | ROBUST medyan "
              f"{np.median(temiz):.2f} | robust p95 {np.percentile(temiz, 95):.2f} | "
              f"max(ham) {spd.max():.2f} m/s (atilan sicrama {len(spd)-len(temiz)})")
    print(f"hedef irtifa bandi (dunya-z): {min(hedef_alt):.1f} .. "
          f"{max(hedef_alt):.1f} m")

    # manevra deseni: heading + donus hizi
    hdg = np.unwrap([math.atan2(v[2], v[1]) for v in v1])
    tv = np.array([v[0] for v in v1])
    om = np.degrees(np.diff(hdg) / np.clip(np.diff(tv), 1e-3, None))
    om_med = float(np.median(np.abs(om)))
    toplam_donus = math.degrees(hdg[-1] - hdg[0])
    ayni_yon = float(np.mean(np.sign(om) == np.sign(np.median(om)))) if om_med > 0.5 else 0.0
    print(f"donus hizi |omega| medyan {om_med:.1f} deg/s; toplam heading degisimi "
          f"{toplam_donus:+.0f} deg; ayni-yon orani %{ayni_yon*100:.0f}")
    if om_med < 1.5:
        desen = "DUZ agirlikli"
    elif ayni_yon > 0.8:
        r = float(np.median(spd)) / math.radians(om_med)
        desen = f"DAIRE agirlikli (R ~ {r:.0f} m)"
    else:
        desen = "KARISIK/rastgele manevra"
    print(f"desen: {desen}")
    # V_MAX marj degerlendirmesi (rapor; karar kullanicinin)
    print(f"V_MAX=18 marji: medyana gore {18 - np.median(spd):+.2f} m/s, "
          f"p95'e gore {18 - np.percentile(spd, 95):+.2f} m/s")

    # ── B) KESTIRIM GURULTUSU: gps_guidance kestirimi vs ham 0.2 s farki ──
    print("\n===== B) HEDEF HIZ KESTIRIMI GURULTUSU =====")
    ham_v = []    # ardisik taze ciftlerden (≈0.2 s) ham hiz
    for i in range(1, len(taze)):
        dt = taze[i][0] - taze[i-1][0]
        if 0.05 <= dt <= 0.6:
            ham_v.append((taze[i][0],
                          (taze[i][1] - taze[i-1][1]) / dt,
                          (taze[i][2] - taze[i-1][2]) / dt))
    # zaman hizala (est_vel ayni taze anlarinda uretildi; ham_v bir eksik)
    n = min(len(ham_v), len(est_vel) - 1)
    ev = np.array([[e[1], e[2]] for e in est_vel[1:n+1]])
    hv = np.array([[h[1], h[2]] for h in ham_v[:n]])
    fark = ev - hv
    print(f"kestirim(gps_guidance) vs ham-fark hiz (n={n}):")
    print(f"  fark std: vx {np.std(fark[:, 0]):.2f} m/s, "
          f"vy {np.std(fark[:, 1]):.2f} m/s, "
          f"|v| {np.std(np.linalg.norm(ev, axis=1) - np.linalg.norm(hv, axis=1)):.2f} m/s")
    # her serinin kendi puruzu (0.6 s EMA'ya gore artik) — komut titremesi gostergesi
    def puruz(x, hz=5.0, tau=0.6):
        a = 1.0 / (tau * hz)
        f = x[0]
        art = []
        for v in x:
            f += a * (v - f)
            art.append(v - f)
        return float(np.std(art))
    print(f"  seri puruzu (0.6 s duzlestirmeye gore std):")
    print(f"    ham vx {puruz(hv[:, 0]):.2f} / vy {puruz(hv[:, 1]):.2f} m/s")
    print(f"    kestirim vx {puruz(ev[:, 0]):.2f} / vy {puruz(ev[:, 1]):.2f} m/s")
    print(f"  KOMUT ETKISI: kestirim komutun BASKIN terimi (vx = vel_hedef + ...);"
          f" kestirim puruzu ~ komut titremesi tabani.")


def main():
    baglan_ve_dogrula()
    taze, est_vel = izle()
    if len(taze) < 30:
        print("[ON-OLCUM] Yeterli taze hedef telemetrisi YOK — oyun/hedef durumunu "
              "kontrol et.")
        return
    analiz(taze, est_vel)
    print("\n[ON-OLCUM] Bitti (hic komut gonderilmedi).")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
======================================================================
 PICK DIVERSE  —  Talon'un GORUNUR oryantasyonuna gore etiket sirasi
======================================================================
Neden: Drone'un kareye nasil yansidigi (on/yan/arka, ust/alt, bank/roll)
hem drone_rotation HEM kamera konumuna baglidir. Bu script ikisini birlikte
kullanip "kameradan bakilan gercek gorunum acisini" hesaplar, acilari kovalara
boler, her kovadan sirayla ornek alarak CESITLI-ONCE bir sira uretir.

Boylece ILK etiket partisi Talon'u tum acilarda gorur -> egitilen model her
oryantasyonda calisir. Cikti: 'oncelik.txt' (editor bu sirayi otomatik kullanir).
======================================================================
"""

import os
import json
import math
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "dataset")
OUT = os.path.join(BASE, "oncelik.txt")

ASPECT_BINS = 6    # drone'a bakis acisi: on(0) .. yan(90) .. arka(180)
ELEV_BINS = 4      # ustten / seviyeden / alttan
ROLL_BINS = 4      # banking (roll)


def _R(pitch, yaw, roll):
    """Unreal Engine donus matrisi (draw_keypoints ile ayni konvansiyon)."""
    sp, cp = math.sin(math.radians(pitch)), math.cos(math.radians(pitch))
    sy, cy = math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
    sr, cr = math.sin(math.radians(roll)), math.cos(math.radians(roll))
    return [[cp * cy, sr * sp * cy - cr * sy, -(cr * sp * cy + sr * sy)],
            [cp * sy, sr * sp * sy + cr * cy, cy * sr - cr * sp * sy],
            [sp,      -sr * cp,               cr * cp]]


def _mul(R, v):
    return [sum(R[i][k] * v[k] for k in range(3)) for i in range(3)]


def _norm(v):
    n = math.sqrt(sum(c * c for c in v)) or 1.0
    return [c / n for c in v]


def main():
    if not os.path.isdir(SRC):
        print("[HATA] dataset yok:", SRC)
        return

    items = []
    for j in os.listdir(SRC):
        if not j.endswith(".json"):
            continue
        base = os.path.splitext(j)[0]
        if not os.path.exists(os.path.join(SRC, base + ".png")):
            continue
        try:
            d = json.load(open(os.path.join(SRC, j), encoding="utf-8"))
            dr = d.get("drone_rotation", {})
            dl = d.get("drone_location", {})
            cl = d.get("camera_location", {})
            pitch, yaw, roll = float(dr.get("pitch", 0)), float(dr.get("yaw", 0)), float(dr.get("roll", 0))
            fwd = _norm(_mul(_R(pitch, yaw, roll), [1, 0, 0]))          # drone burun yonu (dunya)
            if dl and cl:
                view = _norm([dl.get("x", 0) - cl.get("x", 0),
                              dl.get("y", 0) - cl.get("y", 0),
                              dl.get("z", 0) - cl.get("z", 0)])          # kamera -> drone yonu
            else:
                view = [1, 0, 0]
            dot = max(-1.0, min(1.0, sum(fwd[k] * view[k] for k in range(3))))
            aspect = math.degrees(math.acos(dot))                       # 0=on, 90=yan, 180=arka
            elev = math.degrees(math.asin(max(-1.0, min(1.0, view[2])))) # -90=alttan, +90=ustten
            items.append((base, aspect, elev, roll))
        except Exception:
            continue

    if not items:
        print("[HATA] uygun json bulunamadi.")
        return

    def bucket(aspect, elev, roll):
        ab = min(ASPECT_BINS - 1, int(aspect / 180.0 * ASPECT_BINS))
        eb = min(ELEV_BINS - 1, int((elev + 90.0) / 180.0 * ELEV_BINS))
        rb = int((roll % 360) / 360.0 * ROLL_BINS) % ROLL_BINS
        return (ab, eb, rb)

    groups = defaultdict(list)
    for base, a, e, r in items:
        groups[bucket(a, e, r)].append(base)

    # Round-robin: her gorunum kovasindan sirayla -> cesitlilik basa gelir
    order, idx = [], {k: 0 for k in groups}
    while len(order) < len(items):
        moved = False
        for k in list(groups.keys()):
            if idx[k] < len(groups[k]):
                order.append(groups[k][idx[k]])
                idx[k] += 1
                moved = True
        if not moved:
            break

    with open(OUT, "w", encoding="utf-8") as f:
        for b in order:
            f.write(b + ".png\n")

    print(f"Toplam {len(items)} kare, {len(groups)} farkli GORUNUM kovasi (on/yan/arka x ust/alt x bank).")
    print(f"'oncelik.txt' yazildi ({len(order)} kare) - editor cesitli-once acacak.")
    print("Once ilk ~200-300'u etiketle (tum acilari gorur), sonra EGIT_train.bat.")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
# ============================================================================
# PNP MESAFE ANALIZI
# Ucus kaydindaki her saniye icin:
#   1) Gercek mesafe (motor konumlari)                -> gps_mesafe.json
#   2) Motor-keypoint + PnP mesafesi (geometri tavani) -> pnp_mesafe_MOTOR.json
#   3) best.pt poz modeli + PnP mesafesi               -> pnp_mesafe_best.json
# ve hepsini tek grafikte karsilastirir (pnp_karsilastirma.png + rapor.txt).
#
# Kamera modeli Faz-0'da dogrulandi: loglanan FOV ile medyan yeniden-projeksiyon
# hatasi 0.01 px. ("FOV=125" varsayimi YANLISTI; gercek 122.07 / zoom 37.5 -
# her ornekte kendi loglanan FOV'u kullanilir.)
# ============================================================================
import os
import sys
import json
import math
import glob

import numpy as np
import cv2

WORKSPACE = r"c:\Users\Zeylo\Desktop\talon_dataset"
MODEL_PATH = r"C:\Users\Zeylo\Desktop\best.pt"
KP_CONF_MIN = 0.30       # model keypoint guven esigi
MIN_PTS = 4              # PnP icin en az nokta
REPROJ_BAD_PX = 2.0      # motor-kp yeniden projeksiyonu bundan kotuyse "gecis ani" say

# Talon yerel keypoint koordinatlari (cm, olceksiz) - Lua ile birebir ayni
KEYPOINTS_LOCAL = {
    "Nose":           (61.11, -0.07, -2.32),
    "Left_Wingtip":   (3.50, -89.00, 4.66),
    "Right_Wingtip":  (1.50, 88.91, 5.09),
    "Tail":           (-48.81, 0.03, 0.56),
    "Left_Tail_Fin":  (-38.86, 24.80, 15.16),
    "Right_Tail_Fin": (-37.80, -25.02, 15.61),
}
# Modelin egitimdeki keypoint sirasi (prepare_yolo_dataset.py:101)
MODEL_KP_ORDER = ["Nose", "Left_Wingtip", "Right_Wingtip",
                  "Tail", "Left_Tail_Fin", "Right_Tail_Fin"]


def ue_basis(pitch, yaw, roll):
    sp, cp = math.sin(math.radians(pitch)), math.cos(math.radians(pitch))
    sy, cy = math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
    sr, cr = math.sin(math.radians(roll)), math.cos(math.radians(roll))
    fwd = (cp * cy, cp * sy, sp)
    right = (sr * sp * cy - cr * sy, sr * sp * sy + cr * cy, -sr * cp)
    up = (-(cr * sp * cy + sr * sy), cy * sr - cr * sp * sy, cr * cp)
    return fwd, right, up


def project_engine(rec, wp, fov):
    """UE dunya noktasi -> piksel (Faz-0'da 0.01 px medyan hatayla dogrulandi)."""
    c, r = rec["cam_loc"], rec["cam_rot"]
    fwd, right, up = ue_basis(r["pitch"], r["yaw"], r["roll"])
    d = (wp["x"] - c["x"], wp["y"] - c["y"], wp["z"] - c["z"])
    zc = sum(a * b for a, b in zip(d, fwd))
    xc = sum(a * b for a, b in zip(d, right))
    yc = -sum(a * b for a, b in zip(d, up))
    if zc <= 1e-6:
        return None
    fx = 960.0 / math.tan(math.radians(fov / 2))
    return (960.0 + fx * xc / zc, 540.0 + fx * yc / zc)


def K_from_fov(fov):
    fx = 960.0 / math.tan(math.radians(fov / 2))
    return np.array([[fx, 0, 960.0], [0, fx, 540.0], [0, 0, 1]], dtype=np.float64)


def obj_point_cv(local_cm, scale):
    """UE yerel (cm) -> OpenCV nesne cercevesi (m). Eksen esleme: (y, -z, x)."""
    x, y, z = local_cm
    return (y * scale / 100.0, -z * scale / 100.0, x * scale / 100.0)


def solve_distance(names, img_pts, K, scale):
    obj = np.array([obj_point_cv(KEYPOINTS_LOCAL[n], scale) for n in names], dtype=np.float64)
    img = np.array(img_pts, dtype=np.float64)
    try:
        ok, rvec, tvec = cv2.solvePnP(obj, img, K, None, flags=cv2.SOLVEPNP_SQPNP)
        if not ok:
            return None
        rvec, tvec = cv2.solvePnPRefineLM(obj, img, K, None, rvec, tvec)
        return float(np.linalg.norm(tvec))
    except cv2.error:
        return None


def in_frame(rec, margin=10):
    """Talon GERCEKTEN kadrajda mi? ('on' bayragi 'kamera onunde' demek,
    kadraj ici demek DEGIL - t_0299 vakasiyla kanitlandi.)"""
    for p in rec["kp2d"].values():
        if not p.get("on"):
            return False
        if p["x"] < margin or p["x"] > 1920 - margin or p["y"] < margin or p["y"] > 1080 - margin:
            return False
    return True


def main():
    runs = sorted(glob.glob(os.path.join(WORKSPACE, "flight_log", "ucus_*")))
    run = sys.argv[1] if len(sys.argv) > 1 else runs[-1]
    print("[INFO] Ucus:", run)
    recs = [json.loads(l) for l in open(os.path.join(run, "truth_log.jsonl"), encoding="utf-8")]
    n_total = len(recs)
    recs = [r for r in recs if in_frame(r)]
    print("[INFO] Ornek: %d (toplam %d; Talon kadraj disinda oldugu icin %d haric)"
          % (len(recs), n_total, n_total - len(recs)))

    # ---- Talon'un gercek olcegi: kp3d ciftleri / yerel ciftler orani ----
    ratios = []
    r0 = recs[0]["kp3d"]
    names = list(KEYPOINTS_LOCAL)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = r0[names[i]], r0[names[j]]
            dw = math.dist((a["x"], a["y"], a["z"]), (b["x"], b["y"], b["z"]))
            la, lb = KEYPOINTS_LOCAL[names[i]], KEYPOINTS_LOCAL[names[j]]
            dl = math.dist(la, lb)
            if dl > 1:
                ratios.append(dw / dl)
    scale = float(np.median(ratios))
    print("[INFO] Talon olcek carpani: %.4f (kanat acikligi ~%.2f m)"
          % (scale, 177.91 * scale / 100.0))

    # ---- Gercek mesafeler + motor-kp PnP ----
    gps_out, motor_out = [], []
    bad_transition = 0
    for rec in recs:
        c, tl = rec["cam_loc"], rec["talon_loc"]
        true_d = math.dist((c["x"], c["y"], c["z"]), (tl["x"], tl["y"], tl["z"])) / 100.0
        av = rec.get("avci_loc")
        d_avci = (math.dist((av["x"], av["y"], av["z"]), (tl["x"], tl["y"], tl["z"])) / 100.0) if av else None
        gps_out.append({"t": rec["t"], "mesafe_m": round(true_d, 3),
                        "mesafe_avci_m": round(d_avci, 3) if d_avci else None,
                        "fov": rec["fov"]})

        # gecis-ani filtresi: motor kp'yi kendi projeksiyonumuzla dogrula
        errs = []
        for n in names:
            pr = project_engine(rec, rec["kp3d"][n], rec["fov"])
            gt = rec["kp2d"][n]
            if pr and gt.get("on"):
                errs.append(math.dist(pr, (gt["x"], gt["y"])))
        clean = len(errs) == 6 and float(np.median(errs)) < REPROJ_BAD_PX

        entry = {"t": rec["t"], "cozum": False}
        if clean:
            pts = [(rec["kp2d"][n]["x"], rec["kp2d"][n]["y"]) for n in names]
            dist = solve_distance(names, pts, K_from_fov(rec["fov"]), scale)
            if dist:
                entry = {"t": rec["t"], "cozum": True, "mesafe_m": round(dist, 3), "kp": 6}
        else:
            bad_transition += 1
        motor_out.append(entry)

    print("[INFO] Kamera-gecis ani (analiz disi): %d ornek" % bad_transition)

    # ---- Model: best.pt ----
    from ultralytics import YOLO
    model = YOLO(MODEL_PATH)
    model_out = []
    order_err = {n: [] for n in MODEL_KP_ORDER}
    for rec in recs:
        frame = os.path.join(run, rec["png"].replace("/", os.sep))
        entry = {"t": rec["t"], "cozum": False, "sebep": "tespit yok"}
        try:
            res = model.predict(frame, imgsz=1920, conf=0.10, verbose=False)[0]
        except Exception as e:
            entry["sebep"] = "model hatasi: %s" % e
            model_out.append(entry)
            continue
        if res.keypoints is None or len(res.boxes) == 0:
            model_out.append(entry)
            continue
        bi = int(res.boxes.conf.argmax())
        kxy = res.keypoints.xy[bi].cpu().numpy()
        kcf = (res.keypoints.conf[bi].cpu().numpy()
               if res.keypoints.conf is not None else np.ones(len(kxy)))

        # ISABET kontrolu: model kutusunun merkezi, gercek Talon bolgesine mi dusuyor?
        tx = [rec["kp2d"][n]["x"] for n in names]
        ty = [rec["kp2d"][n]["y"] for n in names]
        gx0, gy0, gx1, gy1 = min(tx), min(ty), max(tx), max(ty)
        gw, gh = max(gx1 - gx0, 20), max(gy1 - gy0, 20)
        bx1, by1, bx2, by2 = res.boxes.xyxy[bi].tolist()
        bcx, bcy = (bx1 + bx2) / 2, (by1 + by2) / 2
        hit = (gx0 - gw <= bcx <= gx1 + gw) and (gy0 - gh <= bcy <= gy1 + gh)

        use_names, use_pts = [], []
        for i, name in enumerate(MODEL_KP_ORDER):
            if i < len(kxy) and kcf[i] >= KP_CONF_MIN:
                use_names.append(name)
                use_pts.append((float(kxy[i][0]), float(kxy[i][1])))
                gt = rec["kp2d"].get(name)
                if gt and gt.get("on"):
                    order_err[name].append(math.dist(use_pts[-1], (gt["x"], gt["y"])))

        if len(use_names) < MIN_PTS:
            entry["sebep"] = "guvenli keypoint %d/6 (<%d)" % (len(use_names), MIN_PTS)
            entry["isabet"] = hit
            model_out.append(entry)
            continue
        dist = solve_distance(use_names, use_pts, K_from_fov(rec["fov"]), scale)
        if dist is None:
            entry["sebep"] = "PnP cozemedi"
            entry["isabet"] = hit
            model_out.append(entry)
            continue
        model_out.append({"t": rec["t"], "cozum": True, "mesafe_m": round(dist, 3),
                          "kp": len(use_names), "isabet": hit})

    # ---- Keypoint sira dogrulamasi (durustluk kontrolu) ----
    print("[SIRA KONTROLU] model kp -> motor kp ortalama sapma (px):")
    for n in MODEL_KP_ORDER:
        v = order_err[n]
        print("   %-15s %s" % (n, ("%.1f px (n=%d)" % (float(np.mean(v)), len(v))) if v else "veri yok"))

    # ---- JSON ciktilar ----
    def dump(name, data):
        p = os.path.join(run, name)
        json.dump(data, open(p, "w", encoding="utf-8"), indent=2)
        print("[YAZILDI]", p)
    dump("gps_mesafe.json", gps_out)
    dump("pnp_mesafe_MOTOR.json", motor_out)
    dump("pnp_mesafe_best.json", model_out)

    # ---- Metrikler ----
    true_by_t = {g["t"]: g["mesafe_m"] for g in gps_out}
    fov_by_t = {g["t"]: g["fov"] for g in gps_out}

    def metrics(series):
        rows = [(e["t"], e["mesafe_m"], true_by_t[e["t"]])
                for e in series if e.get("cozum") and e["t"] in true_by_t]
        if not rows:
            return None
        err = np.array([p - t for _, p, t in rows])
        rel = np.array([abs(p - t) / t * 100 for _, p, t in rows if t > 0.5])
        return {"n": len(rows), "mae": float(np.mean(np.abs(err))),
                "rmse": float(np.sqrt(np.mean(err ** 2))),
                "bias": float(np.mean(err)), "mape": float(np.mean(rel)),
                "medape": float(np.median(rel)), "rows": rows}

    m_motor, m_model = metrics(motor_out), metrics(model_out)
    model_hits = [e for e in model_out if e.get("isabet")]
    m_model_hit = metrics(model_hits)
    n_hit = len(model_hits)
    n_det = sum(1 for e in model_out if "isabet" in e)

    rapor = []
    rapor.append("PNP MESAFE DOGRULUK RAPORU - %s" % os.path.basename(run))
    rapor.append("=" * 64)
    rapor.append("Analiz kumesi: %d kare (yalnizca Talon'un GERCEKTEN kadrajda oldugu kareler)" % len(recs))
    rapor.append("Kamera-gecis ani nedeniyle motor-PnP disinda tutulan: %d | Talon olcek: %.4f" % (bad_transition, scale))
    rapor.append("FAZ-0: loglanan FOV ile medyan yeniden-projeksiyon 0.01 px (dogrulandi).")
    rapor.append("NOT: 'FOV=125' varsayimi YANLIS cikti; motor 122.07 bildiriyor (zoomda 37.5).")
    rapor.append("NOT: kayit dondurmasiz; goruntu-konum arasi ~50-100 ms -> ~%1-2 belirsizlik.")
    rapor.append("")
    rapor.append("MODEL TESPIT KALITESI (kadraj-ici karelerde):")
    rapor.append("  Tespit ureten kare : %d / %d" % (n_det, len(recs)))
    rapor.append("  Kutusu Talon'a ISABETLI kare: %d / %d (%%%.0f)"
                 % (n_hit, len(recs), 100.0 * n_hit / max(1, len(recs))))
    for lo, hi, lbl in ((0, 20, "  0-20 m"), (20, 40, " 20-40 m"), (40, 80, " 40-80 m"), (80, 1e9, "   80+ m")):
        tot = [e for e in model_out if lo <= true_by_t.get(e["t"], -1) < hi]
        hitb = [e for e in tot if e.get("isabet")]
        if tot:
            rapor.append("    %s: isabet %d/%d" % (lbl, len(hitb), len(tot)))
    for label, m in (("MOTOR-KEYPOINT PnP (geometri tavani)", m_motor),
                     ("MODEL (best.pt) PnP - TUM kadraj-ici kareler", m_model),
                     ("MODEL (best.pt) PnP - SADECE ISABETLI kareler", m_model_hit)):
        rapor.append("")
        rapor.append(label)
        if not m:
            rapor.append("  cozum yok!")
            continue
        rapor.append("  cozulen saniye : %d / %d" % (m["n"], len(recs)))
        rapor.append("  MAE            : %.2f m" % m["mae"])
        rapor.append("  RMSE           : %.2f m" % m["rmse"])
        rapor.append("  Sapma (bias)   : %+.2f m" % m["bias"])
        rapor.append("  Ort. %% hata    : %.1f%%" % m["mape"])
        rapor.append("  Medyan %% hata  : %.1f%%" % m["medape"])
        # mesafe bantlarina gore
        for lo, hi in ((0, 20), (20, 40), (40, 80), (80, 1e9)):
            band = [abs(p - t) / t * 100 for _, p, t in m["rows"] if lo <= t < hi and t > 0.5]
            if band:
                rapor.append("    %3.0f-%s m bandi: medyan %%%.1f hata (n=%d)"
                             % (lo, ("%.0f" % hi) if hi < 1e8 else "+", float(np.median(band)), len(band)))
    txt = "\n".join(rapor)
    open(os.path.join(run, "rapor.txt"), "w", encoding="utf-8").write(txt)
    print()
    print(txt)

    # ---- Grafik (dataviz referans paleti, dogrulanmis set) ----
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    SURFACE = "#fcfcfb"; INK = "#0b0b0b"; INK2 = "#52514e"; MUTED = "#898781"
    GRID = "#e1e0d9"; BASE = "#c3c2b7"
    C_TRUE = "#2a78d6"   # slot 1 mavi  - gercek mesafe
    C_MODEL = "#1baf7a"  # slot 2 aqua  - model PnP
    C_MOTOR = "#eda100"  # slot 3 sari  - motor-kp PnP (tavan)

    t0 = recs[0]["t"]
    def xs_ys(series):
        pts = [(e["t"] - t0, e["mesafe_m"]) for e in series if e.get("cozum")]
        return [p[0] for p in pts], [p[1] for p in pts]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12.8, 7.6), sharex=True,
                                   gridspec_kw={"height_ratios": [2.4, 1]})
    fig.patch.set_facecolor(SURFACE)
    for ax in (ax1, ax2):
        ax.set_facecolor(SURFACE)
        ax.grid(True, color=GRID, linewidth=0.8)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            ax.spines[s].set_color(BASE)
        ax.tick_params(colors=MUTED, labelsize=9)

    gx = [g["t"] - t0 for g in gps_out]
    gy = [g["mesafe_m"] for g in gps_out]
    ax1.plot(gx, gy, color=C_TRUE, linewidth=2.0, label="Gerçek mesafe (GPS/motor)")
    mx, my = xs_ys(motor_out)
    ax1.plot(mx, my, color=C_MOTOR, linewidth=2.0, alpha=0.9, label="PnP – motor keypoint (tavan)")
    bx, by = xs_ys(model_out)
    ax1.plot(bx, by, color=C_MODEL, linewidth=2.0, label="PnP – best.pt modeli")
    ax1.set_ylabel("Mesafe (m)", color=INK2, fontsize=10)
    ax1.legend(loc="upper right", frameon=False, fontsize=9, labelcolor=INK2)
    hdr = "PnP mesafe tahmini vs gerçek mesafe (yalnız Talon kadrajdayken)"
    sub = ("isabet %d/%d  |  isabetli karelerde medyan hata %%%.1f  |  FOV: loglanan değer (125 değil)"
           % (n_hit, len(recs), m_model_hit["medape"])) if m_model_hit else "model çözüm üretemedi"
    ax1.set_title(hdr + "\n" + sub, loc="left", fontsize=12, color=INK, pad=12)

    # yuzde hata paneli (ayni renk ayni varlik)
    def err_pts(series):
        pts = [(e["t"] - t0, (e["mesafe_m"] - true_by_t[e["t"]]) / true_by_t[e["t"]] * 100)
               for e in series if e.get("cozum") and true_by_t.get(e["t"], 0) > 0.5]
        return [p[0] for p in pts], [p[1] for p in pts]
    ex, ey = err_pts(model_out)
    ax2.plot(ex, ey, color=C_MODEL, linewidth=1.6)
    ex2, ey2 = err_pts(motor_out)
    ax2.plot(ex2, ey2, color=C_MOTOR, linewidth=1.6, alpha=0.9)
    ax2.axhline(0, color=BASE, linewidth=1.0)
    ax2.set_ylabel("Hata (%)", color=INK2, fontsize=10)
    ax2.set_xlabel("Uçuş süresi (saniye)", color=INK2, fontsize=10)
    ax2.set_ylim(-60, 60)

    out_png = os.path.join(run, "pnp_karsilastirma.png")
    fig.tight_layout()
    fig.savefig(out_png, dpi=130, facecolor=SURFACE)
    print("[YAZILDI]", out_png)


if __name__ == "__main__":
    main()

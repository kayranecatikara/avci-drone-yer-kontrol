# -*- coding: utf-8 -*-
"""
================================================================================
 KALIBRE — kamera tilt (+ latency) olcumu  (best.pt gercek referans)
================================================================================
Sorun: truth pozdan projekte ettigimiz hedef merkezi ile GORUNTUDEKI gercek Talon
(best.pt bbox merkezi) tutmuyor. Iki bilinmeyen: (1) kamera montaj TILT'i (yukari
pitch + olasi yaw ofseti), (2) telemetri<->kare LATENCY'si dt.

Bu arac ikisini de VERIDEN olcer: best.pt her karede gercek Talon merkezini verir;
biz (dt, tilt_pitch, tilt_yaw) uzayinda projeksiyon<->tespit piksel hatasini
minimize ederiz. Cikan degerler dogrudan geometri.py'ye yazilir.

Latency icin telemetri_akis.jsonl (surekli 50Hz akis) gerekir: kareyi (t - dt)
anindaki poz'la eslestiririz. Akis yoksa dt=0 (eski kayitlar) — sadece tilt cozer,
ama latency artigi kalir (uyarilir). En guvenilir sonuc: YAVAS/sabit kayittan.

Kullanim (repo kokunden):
    python pose\\kalibre.py                      # en son oturum
    python pose\\kalibre.py --oturum C:\\...\\oturum_XX
    python pose\\kalibre.py --yavas-only         # sadece dusuk acisal hizli kareler (latency azalir)
"""
import os
import sys
import json
import glob
import math
import argparse
import warnings

warnings.filterwarnings("ignore")
_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _KOK not in sys.path:
    sys.path.insert(0, _KOK)

import numpy as np
import cv2
from pose import geometri


def _en_son_oturum(kok=r"C:\talon_pose_data\ham"):
    ler = sorted(glob.glob(os.path.join(kok, "oturum_*")))
    return ler[-1] if ler else None


def _oku_jsonl(yol):
    if not os.path.isfile(yol):
        return []
    return [json.loads(l) for l in open(yol, encoding="utf-8") if l.strip()]


class AkisInterp:
    """Surekli telemetri akisini zaman -> (drone_pos, drone_rot, target_pos) interpole eder."""
    def __init__(self, akis):
        self.t = np.array([a["t"] for a in akis])
        self.dp = np.array([a["dp"] for a in akis], float)
        self.dr = np.array([a["dr"] for a in akis], float)
        self.tp = np.array([a["tp"] for a in akis], float)
        self.var = len(self.t) > 1

    def at(self, tq):
        i = int(np.clip(np.searchsorted(self.t, tq), 1, len(self.t) - 1))
        t0, t1 = self.t[i - 1], self.t[i]
        w = 0.0 if t1 == t0 else np.clip((tq - t0) / (t1 - t0), 0.0, 1.0)
        dp = self.dp[i - 1] * (1 - w) + self.dp[i] * w
        tp = self.tp[i - 1] * (1 - w) + self.tp[i] * w
        d = ((self.dr[i] - self.dr[i - 1] + 180) % 360) - 180     # aci farki (wrap)
        dr = self.dr[i - 1] + d * w
        return dp, dr, tp


def _tespitleri_al(oturum, sat, conf_esik=0.4):
    """best.pt ile her karede gercek Talon merkezi. Cache: <oturum>/best_tespit.json."""
    cache = os.path.join(oturum, "best_tespit.json")
    if os.path.isfile(cache):
        d = json.load(open(cache, encoding="utf-8"))
        print("[KALIBRE] tespit cache okundu (%d kare)" % len(d))
        return d
    from detection.gorsel_tespit import HedefDedektor
    det = HedefDedektor(os.path.join(_KOK, "models", "best.pt"), conf=0.25)
    if not det.hazir:
        print("[HATA] best.pt yuklenemedi:", det.hata)
        return {}
    out = {}
    print("[KALIBRE] best.pt %d karede calisiyor..." % len(sat))
    for k, s in enumerate(sat):
        img = cv2.imread(os.path.join(oturum, s["kare"]))
        if img is None:
            continue
        r = det.tespit_et(img)
        if r is not None:
            out[s["kare"]] = {"cx": r["cx"], "cy": r["cy"], "conf": r["conf"]}
        if (k + 1) % 40 == 0:
            print("   ... %d/%d" % (k + 1, len(sat)))
    json.dump(out, open(cache, "w", encoding="utf-8"))
    print("[KALIBRE] %d tespit, cache yazildi." % len(out))
    return out


def _rot_hiz(sat):
    """ardisik kareler arasi drone acisal hiz (deg/s) — latency hassasiyeti gostergesi."""
    hiz = {}
    prev = None
    for s in sat:
        if prev is not None:
            dt = max(s["t"] - prev["t"], 1e-3)
            dch = max(abs(((s["drone_rot_rpy"][i] - prev["drone_rot_rpy"][i] + 180) % 360) - 180)
                      for i in range(3)) / dt
            hiz[s["kare"]] = dch
        prev = s
    return hiz


def calistir(args):
    oturum = args.oturum or _en_son_oturum()
    if not oturum or not os.path.isdir(oturum):
        print("[HATA] Oturum yok. --oturum ver."); return 1
    sat = _oku_jsonl(os.path.join(oturum, "telemetri.jsonl"))
    akis = _oku_jsonl(os.path.join(oturum, "telemetri_akis.jsonl"))
    if not sat:
        print("[HATA] telemetri.jsonl bos."); return 1
    print("[KALIBRE] oturum: %s" % oturum)
    print("[KALIBRE] kare=%d, akis=%d %s" %
          (len(sat), len(akis), "(latency cozulebilir)" if akis else "(akis YOK -> dt=0, sadece tilt)"))

    tespit = _tespitleri_al(oturum, sat)
    if len(tespit) < 15:
        print("[HATA] Yeterli best.pt tespiti yok (%d). conf dusur / daha cok kare." % len(tespit))
        return 1

    interp = AkisInterp(akis) if (akis and len(akis) > 1) else None
    hiz = _rot_hiz(sat) if args.yavas_only else None

    # kalibrasyon kayitlari: (frame_t, W,H, cx,cy, [fallback dp,dr,tp])
    kayit = []
    for s in sat:
        d = tespit.get(s["kare"])
        if d is None or d["conf"] < args.conf:
            continue
        if hiz is not None and hiz.get(s["kare"], 999) > args.yavas_esik:
            continue
        kayit.append((s["t"], int(s["W"]), int(s["H"]), d["cx"], d["cy"],
                      s["drone_pos"], s["drone_rot_rpy"], s["truth_target_pos"]))
    print("[KALIBRE] kalibrasyonda kullanilan kare: %d" % len(kayit))
    if len(kayit) < 15:
        print("[HATA] Filtreden sonra cok az kare kaldi."); return 1

    def hata(dt, pitch, yaw):
        es = []
        for ft, W, H, cx, cy, dp0, dr0, tp0 in kayit:
            if interp is not None:
                dp, dr, tp = interp.at(ft - dt)
            else:
                dp, dr, tp = dp0, dr0, tp0            # akis yok -> dt etkisiz
            cam_pos, R_cam = geometri.kamera_pozu(dp, dr, tilt_deg=pitch, tilt_yaw_deg=yaw)
            fx = geometri.fx_from_hfov(W)
            uv = geometri.projekte(tp, cam_pos, R_cam, fx, W, H)
            if uv is not None:
                es.append(math.hypot(uv[0] - cx, uv[1] - cy))
        if not es:
            return 9e9, 9e9
        return float(np.mean(es)), float(np.median(es))

    # --- kaba grid: (dt, pitch, yaw) ---
    dt_grid = np.arange(0.0, 0.301, 0.03) if interp is not None else np.array([0.0])
    p_grid = np.arange(0.0, 41.0, 5.0)
    y_grid = np.arange(-15.0, 15.1, 5.0)
    print("[KALIBRE] kaba tarama: dt=%d x pitch=%d x yaw=%d ..." %
          (len(dt_grid), len(p_grid), len(y_grid)))
    best = (None, 9e9, 9e9)
    for dt in dt_grid:
        for p in p_grid:
            for y in y_grid:
                m, med = hata(dt, p, y)
                if med < best[2]:
                    best = ((dt, p, y), m, med)
    (dt0, p0, y0), _, _ = best
    # --- ince tarama ---
    dt_f = np.arange(max(0, dt0 - 0.03), dt0 + 0.031, 0.01) if interp is not None else np.array([0.0])
    for dt in dt_f:
        for p in np.arange(p0 - 5, p0 + 5.1, 1.0):
            for y in np.arange(y0 - 5, y0 + 5.1, 1.0):
                m, med = hata(dt, p, y)
                if med < best[2]:
                    best = ((dt, p, y), m, med)
    (dtb, pb, yb), mb, medb = best
    m0, med0 = hata(0.0, 0.0, 0.0)

    print("\n" + "=" * 60)
    print("SONUC")
    print("=" * 60)
    print("tilt=0, dt=0 (baslangic)   -> ort %.1f px, medyan %.1f px" % (m0, med0))
    print("EN IYI                     -> ort %.1f px, medyan %.1f px" % (mb, medb))
    print("  KAMERA_TILT_DEG      = %.1f   (yukari pitch)" % pb)
    print("  KAMERA_TILT_YAW_DEG  = %.1f" % yb)
    if interp is not None:
        print("  LATENCY dt           = %.0f ms" % (dtb * 1000))
    else:
        print("  LATENCY dt           = OLCULEMEDI (akis yok; yeni kayitta olculur)")
    print("-" * 60)
    if medb > 25:
        print("UYARI: artik hata hala YUKSEK (%.0f px). Muhtemel neden: latency + hizli"
              " manevra + motion blur. YAVAS/sabit kayit sart. (--yavas-only dene.)" % medb)
    else:
        print("Artik hata dusuk -> geometri.py'ye sunlari yaz:")
        print("    KAMERA_TILT_DEG     = %.1f" % pb)
        print("    KAMERA_TILT_YAW_DEG = %.1f" % yb)
    print("=" * 60)
    return 0


def main():
    ap = argparse.ArgumentParser(description="Kamera tilt + latency kalibrasyonu (best.pt referans)")
    ap.add_argument("--oturum", default=None, help="oturum klasoru (vars: en son)")
    ap.add_argument("--conf", type=float, default=0.45, help="min best.pt guveni (vars 0.45)")
    ap.add_argument("--yavas-only", action="store_true", dest="yavas_only",
                    help="sadece dusuk acisal hizli kareler (latency etkisini azaltir)")
    ap.add_argument("--yavas-esik", type=float, default=20.0, dest="yavas_esik",
                    help="yavas kare esigi deg/s (vars 20)")
    sys.exit(calistir(ap.parse_args()))


if __name__ == "__main__":
    main()

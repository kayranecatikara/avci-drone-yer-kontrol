# -*- coding: utf-8 -*-
"""
================================================================================
  UCUS KAMERA KAYDI  --  saniyede 1 kare + O ANIN TAM DURUMU
================================================================================
NEDEN
--------------------------------------------------------------------------------
Sayilar "ne oldugunu" soyluyor ama "neden" sorusunda tikaniyoruz: hedef kadrajin
neresindeydi, kutu var miydi, hayalet miydi, biz nereye bakiyorduk. Her karenin
YANINA o anin tam durumu yazilirsa kayit kendi kendini acikliyor.

⚠ MEVCUT FOTO CEKME YOLUNA DOKUNULMADI. Bu arac AYRI BIR SUREC olarak calisir
   ve yalnizca sunucunun /api/frame + /api/telemetry uclarini okur. Arayuz
   /api/frame'i zaten hic kullanmiyor -> dedektor dongusune EK YUK BINMEZ.
   Veri seti cekimi (AVCI_KAYIT) bundan tamamen bagimsizdir.

NE KAYDEDER (her saniye)
    kare_XXXXXX.jpg          ham oyun karesi
    kareler.csv satiri       ayni anin telemetrisi:
        BIZIM ARAC : x,y,z, irtifa, hiz, roll, pitch, yaw
        HEDEF      : x,y,z (bozulmamis truth), hiz
        GEOMETRI   : menzil, irtifa farki, yatay ayrim, aspect, kapanma hizi
        GUDUM      : faz, durum, kilit sayaci, gecis sayisi, mod
        GORU       : tespit var mi, conf, kutu px, kadraj konumu, kopru mu
        PERF       : det_ms, fps

CALISTIR
    python arac/ucus_kamera_kaydi.py                 # 1 Hz, sinirsiz
    python arac/ucus_kamera_kaydi.py --hz 2 --dk 30  # 2 Hz, 30 dakika
    python arac/ucus_kamera_kaydi.py --sadece-yakin 30   # yalniz menzil<30 m
================================================================================
"""
import os
import csv
import sys
import json
import time
import math
import argparse
import urllib.request

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUNUCU = "http://127.0.0.1:8000"

ALANLAR = [
    "kare", "t_wall", "t_perf", "dosya",
    # bizim arac
    "d_x", "d_y", "d_z", "d_irtifa", "d_hiz", "d_roll", "d_pitch", "d_yaw",
    # hedef (bozulmamis truth)
    "h_x", "h_y", "h_z", "h_hiz",
    # geometri
    "menzil", "irtifa_farki", "yatay_ayrim", "aspect_deg", "kapanma_ms",
    # guduum
    "faz", "durum", "mod", "kilit_s", "gecis", "gorev_faz", "vurus", "en_yakin",
    # goru
    "tespit", "conf", "kutu_w_px", "kutu_h_px", "kutu_cx", "kutu_cy", "kopru",
    "tespit_orani",
    # ── KOMUT (yasanin ISTEDIGI) ────────────────────────────────────────
    "sp_vx", "sp_vy", "sp_vz", "sp_yaw_deg", "sp_hiz", "sp_ileri", "sp_sag",
    # ── TEPKI (aracin YAPTIGI) ──────────────────────────────────────────
    "olc_hiz", "olc_ileri", "olc_sag", "olc_vz", "yaw_gercek_deg",
    # ── HATA (komut - tepki) ────────────────────────────────────────────
    "e_ileri", "e_sag", "e_vz", "yaw_hata_deg",
    # ── CUBUK (koprunun urettigi) ───────────────────────────────────────
    "cbk_thr", "cbk_pitch", "cbk_roll", "cbk_yaw", "thr_doydu",
    # ── TAZELIK (komut bayat mi, SDK kanallari donmus mu) ───────────────
    "sp_bayat", "yaw_yas_s", "v_yas_s",
    # perf
    "det_ms", "fps",
]


def _get_json(yol, zaman=4.0):
    with urllib.request.urlopen(SUNUCU + yol, timeout=zaman) as r:
        return json.loads(r.read().decode("utf-8"))


def _get_jpeg(zaman=6.0):
    with urllib.request.urlopen(SUNUCU + "/api/frame", timeout=zaman) as r:
        if r.status != 200:
            return None
        return r.read()


def _durum(onceki):
    """Telemetriden tek satirlik tam durum. onceki: kapanma hizi icin."""
    t = _get_json("/api/telemetry")
    d, h = t["drone"], t["target"]
    g, gd, gv = t["gorsel"], t["gudum"], t["gorev"]
    hb = gd.get("hibrit", {}) or {}
    ak = hb.get("akis", {}) or {}
    ts = g.get("tespit") or {}
    hr = (t.get("debug") or {}).get("target_real") or {}
    hx = hr.get("x", h.get("x"))
    hy = hr.get("y", h.get("y"))
    hz = hr.get("z", h.get("z"))
    dx, dy, dz = d["x"], d["y"], d["z"]
    menzil = yatay = irt = aspect = float("nan")
    if None not in (hx, hy, hz):
        menzil = math.dist((hx, hy, hz), (dx, dy, dz))
        yatay = math.hypot(hx - dx, hy - dy)
        irt = dz - hz
    kapanma = float("nan")
    simdi = time.perf_counter()
    if onceki and onceki[1] == onceki[1] and menzil == menzil:
        dt = simdi - onceki[0]
        if 0.2 < dt < 10.0:
            kapanma = (menzil - onceki[1]) / dt
    s = {
        "t_wall": round(time.time(), 3), "t_perf": round(simdi, 3),
        "d_x": dx, "d_y": dy, "d_z": dz,
        "d_irtifa": d.get("altitude_m"), "d_hiz": d.get("speed_ms"),
        "d_roll": d.get("roll"), "d_pitch": d.get("pitch"), "d_yaw": d.get("yaw"),
        "h_x": hx, "h_y": hy, "h_z": hz, "h_hiz": h.get("speed_ms"),
        "menzil": None if menzil != menzil else round(menzil, 3),
        "irtifa_farki": None if irt != irt else round(irt, 3),
        "yatay_ayrim": None if yatay != yatay else round(yatay, 3),
        "aspect_deg": None,
        "kapanma_ms": None if kapanma != kapanma else round(kapanma, 2),
        "faz": hb.get("faz"), "durum": gd.get("durum"), "mod": gd.get("mod"),
        "kilit_s": hb.get("kilit_sayac"), "gecis": hb.get("gecis_sayisi"),
        "gorev_faz": gv.get("faz"), "vurus": gv.get("vurus"),
        "en_yakin": gv.get("en_yakin_m"),
        "tespit": bool(ts.get("tespit_mi")), "conf": ts.get("conf"),
        "kutu_w_px": round((ts.get("w") or 0) * 1920, 1),
        "kutu_h_px": round((ts.get("h") or 0) * 1080, 1),
        "kutu_cx": ts.get("cx"), "kutu_cy": ts.get("cy"),
        "kopru": bool(g.get("kopru")),
        "tespit_orani": round(100 * (ak.get("tespit_orani") or 0), 1),
        "det_ms": (g.get("perf") or {}).get("det_ms"),
        "fps": (g.get("perf") or {}).get("fps"),
    }
    # ── KOMUT -> TEPKI (koprunun son_tani'si; telemetriye 2026-08-17'de eklendi)
    #   Bu blok olmadan "neden bu komut verildi, arac ne yapti" sorusu
    #   kareye bakarak cevaplanamiyordu.
    kt = g.get("kopru_tani") or {}
    r = lambda k, n=3: (round(kt[k], n) if isinstance(kt.get(k), (int, float)) else None)
    s2 = {
        "sp_vx": r("sp_vx"), "sp_vy": r("sp_vy"), "sp_vz": r("sp_vz"),
        "sp_yaw_deg": r("sp_yaw_ned_deg", 1), "sp_hiz": r("vh_sp"),
        "sp_ileri": r("sp_fwd"), "sp_sag": r("sp_right"),
        "olc_hiz": r("vh_sdk"), "olc_ileri": r("olc_fwd"), "olc_sag": r("olc_right"),
        "olc_vz": r("vz_up_sdk"), "yaw_gercek_deg": r("yaw_dow_deg", 1),
        "e_ileri": r("e_fwd"), "e_sag": r("e_right"), "e_vz": r("e_vz"),
        "yaw_hata_deg": r("yaw_hata_deg", 1),
        "cbk_thr": r("thr"), "cbk_pitch": r("pitch"),
        "cbk_roll": r("roll"), "cbk_yaw": r("yaw"),
        "thr_doydu": kt.get("thr_doydu"),
        "sp_bayat": kt.get("bayat"),
        "yaw_yas_s": r("yaw_yas_s", 2), "v_yas_s": r("v_yas_s", 2),
    }
    s.update(s2)
    return s, (simdi, menzil)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hz", type=float, default=1.0, help="kare/saniye")
    ap.add_argument("--dk", type=float, default=0.0, help="0 = sinirsiz")
    ap.add_argument("--sadece-yakin", type=float, default=0.0,
                    help="yalniz bu menzilin altinda kaydet (0 = hep)")
    ap.add_argument("--kalite", type=int, default=85)
    a = ap.parse_args()

    damga = time.strftime("%Y%m%d_%H%M%S")
    klasor = os.path.join(KOK, "veri", "ucus_kamera", damga)
    os.makedirs(klasor, exist_ok=True)
    csv_yol = os.path.join(klasor, "kareler.csv")
    f = open(csv_yol, "w", newline="", encoding="utf-8")
    yaz = csv.writer(f)
    yaz.writerow(ALANLAR)
    f.flush()

    print("=" * 70)
    print("  UCUS KAMERA KAYDI  ->  %s" % klasor)
    print("  %.1f Hz | %s | %s" % (
        a.hz, ("%.0f dk" % a.dk) if a.dk else "sinirsiz",
        ("yalniz menzil<%.0f m" % a.sadece_yakin) if a.sadece_yakin else "tum kareler"))
    print("  ⚠ mevcut foto cekme yoluna DOKUNULMADI (ayri surec, /api/frame)")
    print("=" * 70, flush=True)

    n = 0
    atlanan = 0
    onceki = None
    t0 = time.perf_counter()
    periyot = 1.0 / max(a.hz, 0.05)
    son_bilgi = 0.0
    while True:
        dongu = time.perf_counter()
        if a.dk and (dongu - t0) > a.dk * 60:
            break
        try:
            s, onceki = _durum(onceki)
        except Exception as e:
            if time.perf_counter() - son_bilgi > 20:
                son_bilgi = time.perf_counter()
                print("  telemetri yok (%r) -- bekleniyor" % (e,), flush=True)
            time.sleep(2.0)
            continue

        m = s.get("menzil")
        if a.sadece_yakin and (m is None or m > a.sadece_yakin):
            atlanan += 1
        else:
            try:
                jpeg = _get_jpeg()
            except Exception:
                jpeg = None
            ad = "kare_%06d.jpg" % n
            if jpeg:
                with open(os.path.join(klasor, ad), "wb") as g:
                    g.write(jpeg)
            else:
                ad = ""
            s["kare"] = n
            s["dosya"] = ad
            yaz.writerow([s.get(k) for k in ALANLAR])
            n += 1
            if n % 20 == 0:
                f.flush()
            if time.perf_counter() - son_bilgi > 30:
                son_bilgi = time.perf_counter()
                print("  %5d kare | menzil %6s m | faz %-6s | kilit %4s | "
                      "tespit %-3s | atlanan %d"
                      % (n, ("%.1f" % m) if m else "—", s.get("faz"),
                         s.get("kilit_s"), "VAR" if s.get("tespit") else "yok",
                         atlanan), flush=True)

        kal = periyot - (time.perf_counter() - dongu)
        if kal > 0:
            time.sleep(kal)
    f.close()
    print("\n  BITTI: %d kare -> %s" % (n, klasor))


if __name__ == "__main__":
    main()

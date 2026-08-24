# -*- coding: utf-8 -*-
"""
================================================================================
  KAMERA TILTINI OLC  --  25 derece DoW'un mu, Gazebo'dan miras mi?
================================================================================
SORU
--------------------------------------------------------------------------------
Kodda kamera tilti TEK sayi olarak duruyor:
    detection/kamera_model.py        TILT_DEG        = 25.0
    gps_guidance.Cfg                 CENTER_ELEV_DEG = 25.0
        yorumu: "kamera tilt'i (FIZIKSEL, iris_cam modelinden)"
"iris_cam" GAZEBO'nun quadcopter kamerasidir. Ayni dosyalarda HFOV de
Gazebo'dan geliyordu (125) ve DoW'un gercegi 122.0709 cikti. Yani 25 de
DoW'da ASLA OLCULMEMIS, miras bir sayi OLABILIR. Bu betik onu olcer.

⚠ NEDEN LOGDAKI u_px/v_px KULLANILAMAZ: `hedef_kadraj_hatasi` piksel
  izdusumunu `Cfg.KAMERA_TILT_DEG` KULLANARAK hesapliyor -> dongusel.
  Tilt'i dogrulamak icin DEDEKTORUN GERCEKTEN OLCTUGU piksel gerekir.

YONTEM
--------------------------------------------------------------------------------
Iki bagimsiz kaynak zaman uzerinden birlestirilir (ayni surec, ayni perf_counter):

  veri/ucus_log_*.csv                 -> hedefin ve bizim GERCEK konumumuz (UE cm)
                                         + gövde tutumu (roll/pitch/yaw)
  gazebo_kaynak/logs/bbox_ibvs_*.csv  -> DEDEKTORUN olctugu kutu merkezi (cx, cy)

  1) Dunya LOS vektoru = hedef - biz            (tilt'ten BAGIMSIZ)
  2) Govde cercevesine dondur (roll/pitch/yaw)  -> azimut, yukselis
  3) Piksel acisi = atan((CY - cy) / FY)        (kadraj merkezine gore)
  4) TILT = govde_yukselisi - piksel_acisi

⚠⚠ KOORDINAT GELENEGI VARSAYILMAZ, VERIDEN BULUNUR.
   Bu depoda ayna/isaret hatasi UC KEZ tekrarladi. Betik sekiz isaret
   kombinasyonunu dener ve hangisinin AZIMUTU dedektorun cx'iyle
   ortustugunu olcer. Azimut kanali dogrulanmadan yukselis kanalina
   guvenilmez -- ikisi ayni donusumden cikar.

⚠⚠ DUVAR SAATI KAPISI ZORUNLU. `t_perf` SUREC BASINA sifirlanir; iki ayri
   gunun loglari sayisal olarak CAKISABILIR. Ilk denemede 21 Agustos ucusu
   18 Agustos gorusuyle eslesti (t 36686 vs 36679) ve sahte 25 derece azimut
   sapmasi uretti. Bu yuzden yalniz ucus logunun DOSYA ZAMAN PENCERESINE
   dusen bbox_ibvs dosyalari kullanilir.

⚠ Piksel acisinda YASA CERCEVESI kullanilir (640x480, FX=FY=166.6).
   Bu Gazebo sabiti ama B12 denetimi gosterdi ki cevirme+yasa AYNI FX'i
   kullandigi icin ACI kanalinda sadelesiyor: yasa piksellerinden
   hesaplanan aci, DoW icsellikleriyle hesaplanan aciya BIREBIR esit.

KULLANIM
--------------------------------------------------------------------------------
    python arac/kamera_tilt_olc.py
    python arac/kamera_tilt_olc.py --ucus veri/ucus_log_X.csv
================================================================================
"""
import argparse
import bisect
import csv
import glob
import math
import os
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGD = os.path.join(KOK, "kopru", "gazebo_kaynak", "logs")
CM = 100.0
JOIN_TOL = 0.15           # s
# yasa cercevesi (vision/geometry.py)
IMG_W, IMG_H = 640.0, 480.0
FX = FY = (IMG_W / 2.0) / math.tan(math.radians(125.0) / 2.0)     # ~166.6
CX, CY = IMG_W / 2.0, IMG_H / 2.0


def f(s):
    try:
        v = float(s)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def y(v, q):
    if not v:
        return float("nan")
    s = sorted(v)
    return s[min(len(s) - 1, max(0, int(round(q * (len(s) - 1)))))]


def govde(dx, dy, dz, roll, pitch, yaw, s_yaw, s_pitch, s_roll):
    """Dunya LOS -> govde cercevesi. Isaretler DISARIDAN verilir (taranir)."""
    cy_, sy_ = math.cos(s_yaw * yaw), math.sin(s_yaw * yaw)
    fwd = dx * cy_ + dy * sy_
    rgt = -dx * sy_ + dy * cy_
    up = dz
    cp, sp = math.cos(s_pitch * pitch), math.sin(s_pitch * pitch)
    fwd2 = fwd * cp + up * sp
    up2 = -fwd * sp + up * cp
    cr, sr = math.cos(s_roll * roll), math.sin(s_roll * roll)
    rgt3 = rgt * cr + up2 * sr
    up3 = -rgt * sr + up2 * cr
    az = math.atan2(rgt3, fwd2)
    el = math.atan2(up3, math.hypot(fwd2, rgt3))
    return az, el


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ucus", default=None)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    up = a.ucus or (sorted(glob.glob(os.path.join(KOK, "veri", "ucus_log_*.csv")),
                           key=os.path.getmtime) or [None])[-1]
    if not up:
        print("ucus_log yok"); return 1
    print("[TILT] ucus logu : %s" % os.path.basename(up))

    T = []
    for r in csv.DictReader(open(up, newline="", encoding="utf-8", errors="replace")):
        t = f(r.get("t_perf"))
        dx, dy, dz = f(r.get("drone_x")), f(r.get("drone_y")), f(r.get("drone_z"))
        tx, ty, tz = f(r.get("true_tx")), f(r.get("true_ty")), f(r.get("true_tz"))
        ro, pi, ya = (f(r.get("drone_roll")), f(r.get("drone_pitch")),
                      f(r.get("drone_yaw_deg")))
        d = f(r.get("gercek_mesafe"))
        if None in (t, dx, dy, dz, tx, ty, tz, ro, pi, ya, d) or d <= 200.0:
            continue                       # <2 m: gurultulu, kadraj disi riski
        T.append((t, (tx - dx) / CM, (ty - dy) / CM, (tz - dz) / CM, ro, pi, ya))
    if len(T) < 200:
        print("[TILT] yeterli truth yok (%d)" % len(T)); return 1
    T.sort()
    tt = [r[0] for r in T]
    print("[TILT] truth ornegi: %d  (t %.0f..%.0f)" % (len(T), tt[0], tt[-1]))

    # ── DUVAR SAATI PENCERESI (t_perf tek basina YETMEZ, bkz. baslik) ──
    import datetime as _dt
    _ad = os.path.basename(up)                       # ucus_log_YYYYMMDD_HHMMSS.csv
    try:
        _p = _ad.replace("ucus_log_", "").replace(".csv", "")
        _bas = _dt.datetime.strptime(_p, "%Y%m%d_%H%M%S").timestamp()
    except Exception:
        _bas = os.path.getmtime(up) - 3600.0
    _son = os.path.getmtime(up)
    print("[TILT] kosu penceresi (duvar saati): %s .. %s"
          % (_dt.datetime.fromtimestamp(_bas).strftime("%Y-%m-%d %H:%M:%S"),
             _dt.datetime.fromtimestamp(_son).strftime("%H:%M:%S")))

    ciftler = []
    kul = 0
    _atlanan = 0
    for e in os.scandir(LOGD):
        if not (e.name.startswith("bbox_ibvs_") and e.name.endswith(".csv")):
            continue
        _m = e.stat().st_mtime
        if not (_bas - 120.0 <= _m <= _son + 120.0):
            _atlanan += 1
            continue
        try:
            for r in csv.DictReader(open(e.path, newline="", encoding="utf-8",
                                         errors="replace")):
                t = f(r.get("t"))
                cx, cyv = f(r.get("cx")), f(r.get("cy"))
                cf = f(r.get("conf"))
                if None in (t, cx, cyv) or not (tt[0] - 2 <= t <= tt[-1] + 2):
                    continue
                if cf is not None and cf < 0.35:
                    continue
                i = bisect.bisect_left(tt, t)
                en = None
                for j in (i - 1, i, i + 1):
                    if 0 <= j < len(T):
                        d = abs(tt[j] - t)
                        if en is None or d < en[0]:
                            en = (d, T[j])
                if en and en[0] <= JOIN_TOL:
                    ciftler.append((en[1], cx, cyv))
                    kul += 1
        except Exception:
            continue
    print("[TILT] pencere disi atilan bbox_ibvs dosyasi: %d" % _atlanan)
    print("[TILT] eslesen (truth + DEDEKTOR pikseli) ornek: %d" % kul)
    if kul < 100:
        print("[TILT] ⛔ yeterli eslesme yok -> gorsel fazda kare gerekiyor.")
        print("       Gorsel faz kisa oldugu icin uzun bir kosu sart.")
        return 1

    # ── 1) KOORDINAT GELENEGINI VERIDEN BUL ──
    print()
    print("  ── gelenek taramasi: hangi isaret azimutu dedektorun cx'iyle ortusturur ──")
    print("    %-18s %14s %12s" % ("(yaw,pitch,roll)", "azimut hatasi", "n"))
    en_iyi = None
    for sy in (1, -1):
        for sp in (1, -1):
            for sr in (1, -1):
                h = []
                for (t, lx, ly, lz, ro, pi, ya), cx, cyv in ciftler:
                    az, _el = govde(lx, ly, lz, math.radians(ro), math.radians(pi),
                                    math.radians(ya), sy, sp, sr)
                    az_px = math.atan((cx - CX) / FX)
                    h.append(abs(math.degrees(az - az_px)))
                m = y(h, .5)
                print("    %-18s %13.2f° %12d" % ("(%+d,%+d,%+d)" % (sy, sp, sr), m, len(h)))
                if en_iyi is None or m < en_iyi[0]:
                    en_iyi = (m, sy, sp, sr)

    m, sy, sp, sr = en_iyi
    print()
    print("  EN IYI gelenek: yaw%+d pitch%+d roll%+d  -> azimut hatasi ortanca %.2f°"
          % (sy, sp, sr, m))
    if m > 6.0:
        print("  ⛔ AZIMUT KANALI OTURMADI (%.2f° > 6°). Yukselis olcumu GECERSIZ." % m)
        print("     Sebep: kestirim gecikmesi, yanlis kolon ya da farkli cerceve.")
        return 1
    print("  ✓ azimut kanali oturdu -> ayni donusumden cikan yukselis GUVENILIR")

    # ── 2) TILT ──
    tl, azh = [], []
    for (t, lx, ly, lz, ro, pi, ya), cx, cyv in ciftler:
        az, el = govde(lx, ly, lz, math.radians(ro), math.radians(pi),
                       math.radians(ya), sy, sp, sr)
        el_px = math.atan((CY - cyv) / FY)
        tl.append(math.degrees(el - el_px))
        azh.append(abs(math.degrees(az - math.atan((cx - CX) / FX))))
    print()
    print("  ── OLCULEN KAMERA TILTI ──")
    print("    ortanca %.2f°   |  p10 %.2f°  p90 %.2f°  |  n=%d"
          % (y(tl, .5), y(tl, .1), y(tl, .9), len(tl)))
    print("    yayilim (p90-p10) %.2f°" % (y(tl, .9) - y(tl, .1)))
    print()
    print("    koddaki deger : 25.00°  (kamera_model.TILT_DEG / Cfg.CENTER_ELEV_DEG)")
    fark = y(tl, .5) - 25.0
    print("    FARK          : %+.2f°" % fark)
    if abs(fark) <= 2.0:
        print("    ✓ 25° OLCUMLE UYUMLU.")
    else:
        print("    ⛔ 25° OLCUMLE UYUMSUZ -> tilt sabiti gozden gecirilmeli.")
    print()
    print("    ⚠ Yayilim buyukse (>6°) tek bir sabit tilt varsayimi zayif demektir;")
    print("      sebebi kestirim gecikmesi ya da tutum enterpolasyonu olabilir.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

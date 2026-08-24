# -*- coding: utf-8 -*-
"""
================================================================================
  UCUS 3B DISAKTAR  --  gercek ucus loglarini 3B tekrar icin JSON'a cevirir
================================================================================
NE BIRLESTIRIR
    veri/hedef_iz/*.csv          200 Hz TRUTH: iki aracin konumu + TUTUMU
                                 (roll/pitch/yaw) + hiz vektoru + faz damgasi
    kopru/.../logs/bbox_ibvs_*   gorsel faz: gordugumuz KUTU (cx,cy,w,h),
                                 yasanin acisi (eps_yaw) ve VERDIGI KOMUT

⚠ IKI LOG AYNI SAAT EKSENINDE: hedef_iz.t_mutlak <-> bbox_ibvs.t
   (ikisi de time.perf_counter). Hizalama np.interp gerektirmiyor, dogrudan.

⚠ CERCEVE: hedef_iz HAM OYUN DUNYASI (z yukari). Guduum loglari NED.
   dow_kopru.py:49-52 -> NED_y = -DoW_y, yaw_NED = -yaw_DoW.
   Bu dosya her seyi OYUN DUNYASINDA tutar ve yasadan gelen acilari
   oyun dunyasina cevirir; boylece 3B sahne tek cercevede kalir.

⚠ HEDEFIN TUTUMU: oyun target paketinde `rotation` VERMIYOR (olculdu, alan
   bos geliyor). Hedefin burun yonu KONUM TUREVINDEN cikariliyor. Sabit
   kanat oldugu icin burun ~ hiz yonu; bu kabul, roll icin gecerli DEGIL,
   o yuzden hedefin yatisi cizilmiyor (uydurmak yerine yok sayiliyor).

CALISTIR
    python arac/ucus_3b_disaktar.py            son ucus, otomatik segment secimi
    python arac/ucus_3b_disaktar.py --n 8      en fazla 8 segment
================================================================================
"""
import os
import csv
import glob
import json
import math
import bisect
import argparse
import statistics as st

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IZ_DIR = os.path.join(KOK, "veri", "hedef_iz")
IBVS_DIR = os.path.join(KOK, "kopru", "gazebo_kaynak", "logs")
F_YASA = 166.6            # yasa cercevesi odak (vision/geometry.py)
CX_YASA, CY_YASA = 320.0, 240.0
TX_MAX, TY_MAX = 1.8067, 1.0163   # gercek DoW kadrajinin acisal siniri


def _f(r, ad):
    v = r.get(ad, "")
    if v in ("", None):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def truth_yukle(yol):
    R = []
    with open(yol, newline="", encoding="utf-8", errors="replace") as f:
        for r in csv.DictReader(f):
            t = _f(r, "t_mutlak")
            hx, hy, hz = _f(r, "hx_m"), _f(r, "hy_m"), _f(r, "hz_m")
            dx, dy, dz = _f(r, "dx_m"), _f(r, "dy_m"), _f(r, "dz_m")
            if None in (t, hx, hy, hz, dx, dy, dz):
                continue
            R.append({
                "t": t, "faz": (r.get("faz") or "?"), "gecis": _f(r, "gecis"),
                "hx": hx, "hy": hy, "hz": hz, "dx": dx, "dy": dy, "dz": dz,
                "d_roll": _f(r, "d_roll"), "d_pitch": _f(r, "d_pitch"),
                "d_yaw": _f(r, "d_yaw"),
                "d_vx": _f(r, "d_vx"), "d_vy": _f(r, "d_vy"), "d_vz": _f(r, "d_vz"),
                "h_vx": _f(r, "h_vx"), "h_vy": _f(r, "h_vy"),
            })
    R.sort(key=lambda x: x["t"])
    return R


def hedef_yonu(R, i, pencere=0.4):
    """Hedefin burun yonu (derece, oyun dunyasi). Konum turevinden."""
    j = i
    while j > 0 and R[i]["t"] - R[j]["t"] < pencere:
        j -= 1
    dx, dy = R[i]["hx"] - R[j]["hx"], R[i]["hy"] - R[j]["hy"]
    if abs(dx) < 1e-9 and abs(dy) < 1e-9:
        return None
    return math.degrees(math.atan2(dy, dx))


def ibvs_yukle(t0, t1):
    """[t0,t1] araligindaki gorsel faz kayitlarini tek listede topla."""
    K = []
    for y in glob.glob(os.path.join(IBVS_DIR, "bbox_ibvs_*.csv")):
        try:
            rows = list(csv.DictReader(open(y, encoding="utf-8", errors="replace")))
        except OSError:
            continue
        ts = [_f(r, "t") for r in rows]
        ts = [x for x in ts if x is not None]
        if not ts or max(ts) < t0 or min(ts) > t1:
            continue
        for r in rows:
            t = _f(r, "t")
            if t is None or not (t0 <= t <= t1):
                continue
            K.append({
                "t": t, "cx": _f(r, "cx"), "cy": _f(r, "cy"),
                "w": _f(r, "w"), "h": _f(r, "h"), "boyut": _f(r, "boyut"),
                "conf": _f(r, "conf"),
                "eps": _f(r, "eps_yaw_deg"), "eps_el": _f(r, "eps_elev_deg"),
                "vx": _f(r, "vx_cmd"), "vy": _f(r, "vy_cmd"), "vz": _f(r, "vz_cmd"),
                "yaw_cmd": _f(r, "yaw_cmd_deg"),
                "lam": _f(r, "los_hiz_az"), "pn_sap": _f(r, "pn_sapma_deg"),
                "psi_v": _f(r, "psi_v_deg"),
                # ── KARARIN GEREKCESI: yasa NEDEN bu komutu verdi ──────────
                "durum": (r.get("durum") or ""),        # KUTU_YOK / TERM_KOR / normal
                "kopru": _f(r, "kopru"),                # kor kopru karesi mi
                "b_hata": _f(r, "boyut_hata"),          # BOYUT_REF - boyut  (+ = uzak)
                "hiz_I": _f(r, "hiz_I"),                # hiz integrali (~hedef hizi)
                "v_los": _f(r, "v_los"),                # SONUC: istenen hiz
                "eps_hiz": _f(r, "eps_hiz_deg"),        # hiz yonunu belirleyen aci
                "dosya": os.path.basename(y),
            })
    K.sort(key=lambda x: x["t"])
    return K


def segmentler(R, oncesi=4.0, sonrasi=2.0):
    """GORSEL faz araliklarini bul; oncesine GPS, sonrasina kuyruk ekle."""
    seg = []
    i = 0
    n = len(R)
    while i < n:
        if str(R[i]["faz"]).startswith("VIS"):
            j = i
            while j + 1 < n and str(R[j + 1]["faz"]).startswith("VIS"):
                j += 1
            seg.append((R[i]["t"], R[j]["t"]))
            i = j + 1
        else:
            i += 1
    # bitisikleri birlestir (kisa GPS sicramalarini yut)
    bir = []
    for a, b in seg:
        if bir and a - bir[-1][1] < 1.0:
            bir[-1] = (bir[-1][0], b)
        else:
            bir.append((a, b))
    return [(a - oncesi, b + sonrasi) for a, b in bir]


def en_yakin(R, t0, t1):
    v = [math.dist((r["hx"], r["hy"], r["hz"]), (r["dx"], r["dy"], r["dz"]))
         for r in R if t0 <= r["t"] <= t1]
    return min(v) if v else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=6, help="en fazla segment")
    ap.add_argument("--hz", type=float, default=30.0, help="cikti ornekleme")
    ap.add_argument("--cikti", default=None)
    a = ap.parse_args()

    izl = sorted(glob.glob(os.path.join(IZ_DIR, "hedef_iz_*.csv")),
                 key=os.path.getmtime)
    if not izl:
        print("  truth iz bulunamadi."); return
    yol = izl[-1]
    R = truth_yukle(yol)
    if len(R) < 50:
        print("  truth iz cok kisa (%d satir)." % len(R)); return
    print("  truth : %s  (%d satir, %.0f s)"
          % (os.path.basename(yol), len(R), R[-1]["t"] - R[0]["t"]))

    tutum_var = sum(1 for r in R if r["d_yaw"] is not None)
    print("  tutum : bizim %%%.0f dolu | hedefin rotation'i oyun VERMIYOR "
          "-> burun yonu konum turevinden" % (100.0 * tutum_var / len(R)))

    segs = segmentler(R)
    print("  gorsel faz: %d adet" % len(segs))
    if not segs:
        print("  gorsel faz yok -> disa aktarilacak sey yok."); return

    # ilginc olanlari sec: en yakin gecisi kucuk olanlar + en uzun olan
    puanli = []
    for (t0, t1) in segs:
        ey = en_yakin(R, t0, t1)
        if ey is None:
            continue
        puanli.append({"t0": t0, "t1": t1, "en_yakin": ey, "sure": t1 - t0})
    puanli.sort(key=lambda s: s["en_yakin"])
    sec = puanli[:max(1, a.n - 1)]
    uzun = max(puanli, key=lambda s: s["sure"])
    if uzun not in sec:
        sec.append(uzun)
    sec.sort(key=lambda s: s["t0"])

    T = [r["t"] for r in R]
    adim = 1.0 / max(a.hz, 1.0)
    cik = {"kaynak": os.path.basename(yol), "segmentler": []}

    for s in sec:
        K = ibvs_yukle(s["t0"], s["t1"])
        Kt = [k["t"] for k in K]
        kare = []
        t = s["t0"]
        while t <= s["t1"]:
            i = min(max(bisect.bisect_left(T, t), 1), len(R) - 1)
            r = R[i]
            men = math.dist((r["hx"], r["hy"], r["hz"]), (r["dx"], r["dy"], r["dz"]))
            hh = hedef_yonu(R, i)
            # en yakin ibvs kaydi (0.15 s icinde)
            kk = None
            if Kt:
                j = min(max(bisect.bisect_left(Kt, t), 0), len(K) - 1)
                for c in (j - 1, j, j + 1):
                    if 0 <= c < len(K) and abs(K[c]["t"] - t) < 0.15:
                        if kk is None or abs(K[c]["t"] - t) < abs(kk["t"] - t):
                            kk = K[c]
            # gerceklesen hiz yonu (oyun dunyasi)
            hy = None
            if r["d_vx"] is not None and r["d_vy"] is not None:
                if abs(r["d_vx"]) > 1e-6 or abs(r["d_vy"]) > 1e-6:
                    hy = math.degrees(math.atan2(r["d_vy"], r["d_vx"]))
            # KOMUT yonu: yasa NED'de veriyor -> oyun dunyasina cevir (y ve yaw ters)
            ky = None
            if kk and kk["vx"] is not None and kk["vy"] is not None:
                ky = math.degrees(math.atan2(-kk["vy"], kk["vx"]))
            kare.append([
                round(t - s["t0"], 3),
                round(r["hx"], 2), round(r["hy"], 2), round(r["hz"], 2),
                (round(hh, 1) if hh is not None else None),
                round(r["dx"], 2), round(r["dy"], 2), round(r["dz"], 2),
                # d_yaw ZATEN oyun dunyasi. Olculdu 2026-08-16: truth'un d_yaw'i
                # yasanin iris_yaw_deg'inin (NED) TAM TERSI -> medyan fark 0.03°,
                # 1904 ornek. Yani d_yaw = -yaw_NED = yaw_DoW. Burada negatiflemek
                # HATA idi (burun 3B sahnede ters cizilir, LOS ile hic tutmaz).
                (round(r["d_yaw"], 1) if r["d_yaw"] is not None else None),
                (round(r["d_roll"], 1) if r["d_roll"] is not None else None),
                (round(r["d_pitch"], 1) if r["d_pitch"] is not None else None),
                round(men, 2),
                1 if str(r["faz"]).startswith("VIS") else 0,
                (round(kk["cx"], 1) if kk and kk["cx"] is not None else None),
                (round(kk["cy"], 1) if kk and kk["cy"] is not None else None),
                (round(kk["boyut"], 1) if kk and kk["boyut"] is not None else None),
                (round(kk["conf"], 2) if kk and kk["conf"] is not None else None),
                (round(kk["eps"], 1) if kk and kk["eps"] is not None else None),
                (round(ky, 1) if ky is not None else None),
                (round(hy, 1) if hy is not None else None),
                # ── GEREKCE ──
                (round(kk["v_los"], 1) if kk and kk.get("v_los") is not None else None),
                (round(kk["b_hata"], 1) if kk and kk.get("b_hata") is not None else None),
                (round(kk["hiz_I"], 1) if kk and kk.get("hiz_I") is not None else None),
                ((kk.get("durum") or "") if kk else ""),
                (1 if (kk and kk.get("kopru")) else 0),
                # ── GEOMETRI: kacisin asil sebebi bu ucu ──────────────────
                (round(kk["eps_el"], 1) if kk and kk.get("eps_el") is not None else None),
                (round(kk["lam"], 2) if kk and kk.get("lam") is not None else None),
                (round(kk["psi_v"], 1) if kk and kk.get("psi_v") is not None else None),
            ])
            t += adim
        cik["segmentler"].append({
            "en_yakin": round(s["en_yakin"], 2),
            "sure": round(s["t1"] - s["t0"], 2),
            "kare": kare,
        })
        print("    segment: %.2f s | en yakin %.2f m | %d kare | %d ibvs kaydi"
              % (s["t1"] - s["t0"], s["en_yakin"], len(kare), len(K)))

    cik["alanlar"] = ["t", "hx", "hy", "hz", "h_hdg", "dx", "dy", "dz",
                      "d_yaw", "d_roll", "d_pitch", "menzil", "gorsel",
                      "cx", "cy", "boyut", "conf", "eps", "komut_yon", "hiz_yon",
                      "v_los", "b_hata", "hiz_I", "durum", "kopru",
                      "eps_el", "los_hiz", "psi_v"]
    cik["geo"] = {"F": F_YASA, "CX": CX_YASA, "CY": CY_YASA,
                  "TXMAX": TX_MAX, "TYMAX": TY_MAX, "TILT": 25.0,
                  "CY_NISAN": 301.0}
    yolc = a.cikti or os.path.join(KOK, "veri", "ucus_3b.json")
    with open(yolc, "w", encoding="utf-8") as f:
        json.dump(cik, f, separators=(",", ":"))
    print("  -> %s  (%.0f KB)" % (yolc, os.path.getsize(yolc) / 1024.0))


if __name__ == "__main__":
    main()

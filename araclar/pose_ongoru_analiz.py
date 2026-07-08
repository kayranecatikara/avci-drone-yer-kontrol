# -*- coding: utf-8 -*-
"""
POSE ONGORU ANALIZI - "arac saga donecek dedigi an gercekten saga donuyor mu?"
================================================================================
Pose modelinin kanat-ucu ROLL'unden turetilen ONGORULU YAW LEAD'i (guidance/
ibvs_gorsel) DOGRULAR: tahmin anindaki roll ile hedefin BIR AN SONRAKI gercek
hareketini (truth konumdan) korele eder. Boylece (a) pose'un donus ongorusu
gecerli mi, (b) IBVS_SIGN_ROLL isareti dogru mu, (c) ongoru kac saniye onceden
haberli, sayilarla gorunur.

NASIL OLCER (truth-tabanli, kameradan bagimsiz DOGRULAMA):
  - Hedefin avciya gore ACISAL konumu (goruntu yatay karsiligi): truth'tan
    rel_bearing = wrap(atan2(ty-dy, tx-dx) - drone_yaw). Isaret, vis_cx (goruntu
    yatay, +=sag) ile KALIBRE edilir -> s = "hedef goruntude ne kadar sagda" proxy'si.
  - Gelecek surukleme: ds(H) = s(t+H) - s(t). ds>0 = hedef H sn icinde SAGA kaydi.
  - Tahmin: roll (ibvs_roll, isaretli). corr(roll, ds) ve isaret-uyumu (%).
  - Ufuk taramasi H=0.1..1.5 sn -> |corr| en yuksek ufuk = ongorunun ne kadar
    onceden haberli oldugu. Onerilen IBVS_SIGN_ROLL = sign(corr) (SIGN_YAW=+1 ile).

KULLANIM:
    python araclar/pose_ongoru_analiz.py [ucus_log.csv]   # yoksa en yeni log
Cikti: uyum %, korelasyon, en iyi ufuk, SIGN_ROLL onerisi, karisiklik tablosu,
       ve hedefin gercekten manevra yapip yapmadigi (yeterlilik kontrolu).
"""
import csv
import glob
import math
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_VERI = os.path.join(os.path.dirname(_HERE), "veri")


def wrap(a):
    return (a + math.pi) % (2.0 * math.pi) - math.pi


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _en_yeni_log():
    ler = sorted(glob.glob(os.path.join(_VERI, "ucus_log_*.csv")))
    return ler[-1] if ler else None


def yukle(path):
    """VISUAL satirlari: (t, roll_deg, lead, roll_ok, vis_cx, rel_bearing) - truth sart."""
    ornekler = []
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r.get("phase") != "VISUAL":
                continue
            t = _f(r.get("t_perf")) or _f(r.get("t_wall"))
            roll = _f(r.get("ibvs_roll"))
            tx, ty = _f(r.get("true_tx")), _f(r.get("true_ty"))
            dx, dy = _f(r.get("true_dx")), _f(r.get("true_dy"))
            yaw = _f(r.get("drone_yaw_rad"))
            if None in (t, roll, tx, ty, dx, dy, yaw):
                continue
            rb = wrap(math.atan2(ty - dy, tx - dx) - yaw)   # hedefin buruna gore acisi (rad)
            ok_raw = r.get("ibvs_roll_ok")
            ok = (ok_raw in ("1", "1.0")) if ok_raw not in (None, "") else None  # eski log: None
            # EGO-COMP A/B icin: kendi roll (drone_roll, deg) + HAM goruntu-roll.
            # ibvs_roll_raw yeni loglarda ham (ego-telafisiz); eski logda yok -> ibvs_roll
            # zaten ham'di (o zaman ego-comp yoktu) -> roll'u ham kabul et.
            roll_raw = _f(r.get("ibvs_roll_raw"))
            if roll_raw is None:
                roll_raw = roll
            ornekler.append({
                "t": t, "roll": roll, "lead": _f(r.get("ibvs_lead")),
                "roll_ok": ok, "vis_cx": _f(r.get("vis_cx")), "rb": rb,
                "own_roll": _f(r.get("drone_roll")), "roll_raw": roll_raw,
            })
    ornekler.sort(key=lambda o: o["t"])
    return ornekler


def _corr(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) < 3 or a.std() < 1e-9 or b.std() < 1e-9:
        return 0.0
    return float(np.corrcoef(a, b)[0, 1])


def _gelecek_index(ts, i, H, tol=0.35):
    """t[i]+H'ye en yakin ileri index (tol icinde); yoksa None."""
    hedef = ts[i] + H
    for j in range(i + 1, len(ts)):
        if ts[j] >= hedef:
            return j if (ts[j] - hedef) <= tol else None
        if ts[j] - ts[i] > H + tol:
            return None
    return None


def analiz(ornekler):
    if len(ornekler) < 20:
        print("Yetersiz VISUAL/truth satiri (%d). Once vismode=GORSEL/OTO ile ucup log al." % len(ornekler))
        return
    ts = [o["t"] for o in ornekler]

    # 1) KALIBRASYON: rel_bearing isaretini vis_cx (goruntu, +=sag) ile hizala.
    cal = [(o["rb"], o["vis_cx"]) for o in ornekler if o["vis_cx"] is not None]
    if len(cal) >= 10:
        c_cal = _corr([x for x, _ in cal], [y for _, y in cal])
        k_img = 1.0 if c_cal >= 0 else -1.0
        kal_notu = "vis_cx ile kalibre (corr=%.2f, n=%d)" % (c_cal, len(cal))
    else:
        k_img = 1.0
        kal_notu = "vis_cx az (%d) -> kalibrasyon YOK; s=rel_bearing varsayildi (isaret belirsiz)" % len(cal)
    for o in ornekler:
        o["s"] = k_img * o["rb"]          # +=hedef goruntude saga dogru (proxy)

    # 2) "TAZE tahmin" alt kumesi: roll_ok varsa onu kullan, yoksa lead!=0 (kapi acikti).
    def taze(o):
        if o["roll_ok"] is not None:
            return o["roll_ok"]
        return o["lead"] is not None and abs(o["lead"]) > 1e-6
    idx_taze = [i for i, o in enumerate(ornekler) if taze(o)]

    # 3) HEDEF MANEVRA SEVIYESI (yeterlilik): s'nin turevinin std'si (rad/s).
    dsdt = []
    for i in range(1, len(ornekler)):
        dt = ts[i] - ts[i - 1]
        if 1e-3 < dt < 0.5:
            dsdt.append(wrap(ornekler[i]["s"] - ornekler[i - 1]["s"]) / dt)
    manevra = float(np.std(dsdt)) if dsdt else 0.0

    # 4) UFUK TARAMASI: corr(roll, gelecek ds) + isaret uyumu.
    print("=" * 70)
    print("POSE ONGORU ANALIZI -", len(ornekler), "VISUAL satir |", len(idx_taze), "taze tahmin")
    print("kalibrasyon:", kal_notu)
    print("hedef manevra (s turevi std): %.3f rad/s %s" % (
        manevra, "(DUSUK - hedef az manevra yapmis, sonuc zayif olabilir)" if manevra < 0.05 else ""))
    print("-" * 70)
    print("%-7s %8s %8s %7s   %s" % ("ufuk", "corr", "uyum%", "n", "not"))
    en_iyi = None
    for H in [0.1, 0.2, 0.3, 0.4, 0.5, 0.7, 1.0, 1.5]:
        rolls, dss = [], []
        for i in idx_taze:
            j = _gelecek_index(ts, i, H)
            if j is None:
                continue
            ds = wrap(ornekler[j]["s"] - ornekler[i]["s"])   # s zaten k_img'li; wrap guvenli
            rolls.append(ornekler[i]["roll"])
            dss.append(ds)
        if len(rolls) < 8:
            print("%-7.1f %8s %8s %7d   %s" % (H, "-", "-", len(rolls), "az ornek"))
            continue
        c = _corr(rolls, dss)
        # isaret uyumu: |roll|>1deg ve |ds|>0.5deg olan anlamli orneklerde
        cift = [(r, d) for r, d in zip(rolls, dss)
                if abs(r) > 1.0 and abs(d) > math.radians(0.5)]
        if cift:
            k = 1.0 if c >= 0 else -1.0          # isareti hizala -> uyum yon-bagimsiz
            uyum = 100.0 * np.mean([1.0 if (math.copysign(1, r) == math.copysign(1, k * d)) else 0.0
                                    for r, d in cift])
        else:
            uyum = float("nan")
        print("%-7.1f %8.2f %8.0f %7d   %s" % (H, c, uyum, len(rolls),
              ("<-- en guclu" if (en_iyi is None or abs(c) > abs(en_iyi[1])) else "")))
        if en_iyi is None or abs(c) > abs(en_iyi[1]):
            en_iyi = (H, c, uyum, len(rolls))

    print("-" * 70)
    if en_iyi is None:
        print("SONUC: yeterli ileri-pencere ornegi yok (log kisa / tespit seyrek).")
        return
    H, c, uyum, n = en_iyi
    sign_rec = "+1.0" if c >= 0 else "-1.0"
    guc = abs(c)
    if manevra < 0.05:
        verdict = "BELIRSIZ - hedef neredeyse manevra yapmamis; donusu olan bir kosu gerek."
    elif guc >= 0.30 and (uyum == uyum and uyum >= 65):
        verdict = ("GECERLI - pose bank ongorusu hedefin donusunu ~%.1f sn onceden yakaliyor. "
                   "IBVS_SIGN_ROLL = %s kullan." % (H, sign_rec))
    elif guc >= 0.15:
        verdict = ("ZAYIF-POZITIF - sinyal var ama gurultulu. IBVS_SIGN_ROLL = %s dene; "
                   "IBVS_K_ROLL_LEAD'i dusuk tut, IBVS_ROLL_CONF_MIN'i artir." % sign_rec)
    else:
        verdict = ("ANLAMSIZ - roll ile gercek donus arasi korelasyon yok. Olasi nedenler: "
                   "yandan/onden gorunum (aspect kapisi), keypoint gurultusu, ya da hedef manevrasi az. "
                   "IBVS_K_ROLL_LEAD=0 (ongoruyu kapat) veya keypoint sirasini dogrula.")
    print("EN IYI UFUK: %.1f sn | corr=%.2f | uyum=%.0f%% | n=%d" % (H, c, uyum, n))
    print("ONERI: IBVS_SIGN_ROLL =", sign_rec)
    print("VERDICT:", verdict)

    # 5) KARISIKLIK TABLOSU (en iyi ufukta, onerilen isaretle): "saga dedi -> saga gitti?"
    k = 1.0 if c >= 0 else -1.0
    tp = fp = tn = fn = 0
    for i in idx_taze:
        j = _gelecek_index(ts, i, H)
        if j is None:
            continue
        r = ornekler[i]["roll"]
        ds = wrap(ornekler[j]["s"] - ornekler[i]["s"])
        if abs(r) <= 1.0 or abs(ds) <= math.radians(0.5):
            continue
        dedi_sag = (k * r) > 0            # onerilen isaretle "saga donecek" dedi mi
        gitti_sag = ds > 0
        if dedi_sag and gitti_sag: tp += 1
        elif dedi_sag and not gitti_sag: fp += 1
        elif (not dedi_sag) and (not gitti_sag): tn += 1
        else: fn += 1
    print("-" * 70)
    print("KARISIKLIK (en iyi ufuk, onerilen isaret):")
    print("  'SAGA' dedi -> SAGA gitti : %3d   |  'SAGA' dedi -> SOLA gitti : %3d" % (tp, fp))
    print("  'SOLA' dedi -> SOLA gitti : %3d   |  'SOLA' dedi -> SAGA gitti : %3d" % (tn, fn))
    top = tp + fp + tn + fn
    if top:
        print("  toplam dogru yon: %d/%d = %.0f%%" % (tp + tn, top, 100.0 * (tp + tn) / top))

    # 6) EGO-MOTION TELAFI A/B: kendi roll'u cikarmak ongoruyu iyilestiriyor mu?
    #    HAM vs (roll_raw - own) vs (roll_raw + own) -> truth ile |corr| en yuksek olan kazanir.
    own_vals = [o["own_roll"] for o in ornekler if o["own_roll"] is not None]
    print("-" * 70)
    if len(own_vals) < 20:
        print("EGO-COMP A/B: drone_roll logda yok/az -> atlaniyor.")
        print("=" * 70)
        return
    own_std = float(np.std(own_vals))

    def _variant_best(valfn):
        best = None
        for H in [0.2, 0.3, 0.4, 0.5]:
            rr, dd = [], []
            for i in idx_taze:
                if ornekler[i]["own_roll"] is None or ornekler[i]["roll_raw"] is None:
                    continue
                j = _gelecek_index(ts, i, H)
                if j is None:
                    continue
                rr.append(valfn(ornekler[i]))
                dd.append(wrap(ornekler[j]["s"] - ornekler[i]["s"]))
            if len(rr) < 8:
                continue
            c = _corr(rr, dd)
            if best is None or abs(c) > abs(best[1]):
                best = (H, c, len(rr))
        return best

    print("EGO-MOTION TELAFI A/B (kendi roll std=%.1f deg):" % own_std)
    varyant = [
        ("HAM (telafisiz)", lambda o: o["roll_raw"]),
        ("EGO gain=+1 (-own)", lambda o: o["roll_raw"] - o["own_roll"]),
        ("EGO gain=-1 (+own)", lambda o: o["roll_raw"] + o["own_roll"]),
    ]
    sonuc = []
    for ad, fn in varyant:
        b = _variant_best(fn)
        if b:
            sonuc.append((ad, b))
            print("  %-22s |corr|=%.2f @%.1fsn (n=%d)" % (ad, abs(b[1]), b[0], b[2]))
    if sonuc:
        en = max(sonuc, key=lambda x: abs(x[1][1]))
        if own_std < 2.0:
            print("  -> Kendi roll cok kucuk (std<2 deg): ego-comp bu logda EGZERSIZ EDILMEDI "
                  "(fark ihmal edilebilir). BANKLI bir kosuda tekrar olc.")
        elif en[0] == "HAM (telafisiz)":
            print("  -> HAM en iyi: ego-comp fayda saglamadi -> IBVS_EGO_ROLL_GAIN=0 dusunulebilir.")
        else:
            g = "+1.0" if "gain=+1" in en[0] else "-1.0"
            print("  -> KAZANAN: %s -> ego-comp IYILESTIRDI. IBVS_EGO_ROLL_GAIN=%s kullan." % (en[0], g))
    print("=" * 70)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else _en_yeni_log()
    if not path or not os.path.exists(path):
        print("Ucus logu bulunamadi. Once ucup veri/ucus_log_*.csv uret.")
        return 1
    print("log:", os.path.basename(path))
    analiz(yukle(path))
    return 0


if __name__ == "__main__":
    sys.exit(main())

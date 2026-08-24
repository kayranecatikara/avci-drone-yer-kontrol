# -*- coding: utf-8 -*-
"""
================================================================================
 DENETLE — "kutu gercekten ucagin uzerinde mi?" BAGIMSIZ dogrulama
================================================================================
GELISTIRME ARACI — teslim paketine girmez.

DERT: etiketler truth projeksiyonundan uretiliyor. Ayni projeksiyonla kontrol
etmek TOTOLOJIDIR -- hata varsa ikisi de ayni sekilde yanilir. Gercek denetim
BASKA kaynaklardan gelmeli.

--------------------------------------------------------------------------------
 DORT BAGIMSIZ SINYAL
--------------------------------------------------------------------------------
 1) DEDEKTOR UYUMU   (piksellerden ogrenilmis, geometriden BAGIMSIZ)
      best.pt kareyi kendi basina bulur; etiketle IoU'su dusukse ikisinden biri
      yanlis. Dedektor de hatali olabilir -> tek basina hukum degil, SINYAL.

 2) ICERIK KONTRASTI (saf piksel, ne geometri ne model)
      Talon fon(gok/zemin) icinde KOYU bir cisim. Kutunun ICI ile cevresindeki
      HALKA karsilastirilir: ic tarafta belirgin koyu piksel yoksa kutu bos
      havaya cizilmis demektir. "Kutu dolu mu?" sorusunun dogrudan olcumu.

 3) ZAMAN SUREKLILIGI (komsu karelerden)
      0.2 sn arayla cekilen kareler arasinda kutu SICRAYAMAZ. Merkez kaymasi
      kendi boyutuna gore ani buyukse o kare tek basina bozuk demektir.

 4) BOYUT-MENZIL TUTARLILIGI (fizik)
      Talon 1.718 m; W piksel ve HFOV bilinirken belli menzilde kutunun kac
      piksel olmasi GEREKTIGI hesaplanir. Olculen/beklenen orani 1'den cok
      sapiyorsa kutu ya sisik ya ezik.

--------------------------------------------------------------------------------
 ESIKLER NEREDEN GELIYOR (kritik)
--------------------------------------------------------------------------------
 Esikleri ELLE SECMEK uydurma olurdu. Bunun yerine dort olcum once INSANIN
 DOGRULADIGI karelerde hesaplanir; o dagilimin yuzdelikleri esik olur. Yani
 "insanin onayladigi kareler nasil goruyorsa" ondan sapan kareler isaretlenir.
 Referans yoksa (--gozden-gecirilen verilmezse) arac sadece rapor cikarir,
 hukum vermez.

CIKTI
    denetim_rapor.json        tum sayilar + esikler + en kotu kareler
    _denetim/*.jpg            en kotu N kare, kutu + sebep cizili
    ekrana ozet + "SUPHELI" liste (etiketleyicide --basla ile acilir)

KULLANIM
    python veriseti/denetle.py --klasor C:\\...\\talon_pozitif --gozden-gecirilen 770
    python veriseti/denetle.py --klasor ... --gozden-gecirilen 770 --ornek 800
================================================================================
"""
import os
import sys
import json
import math
import argparse

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _KOK not in sys.path:
    sys.path.insert(0, _KOK)

import numpy as np

from veriseti.bbox_etiketle import telemetri_oku, yolo_oku, kare_listesi
from veriseti.kalibre_et import iou

TALON_KANAT_M = 1.718          # gercek kanat acikligi (DoW modeli)


# =============================================================================
#  Saf olcumler (birim testli: tests/test_denetle.py)
# =============================================================================

def beklenen_genislik_px(menzil_m, W, hfov_deg):
    """Verilen menzilde Talon'un kadrajda kac piksel GENIS olmasi gerektigi.

    Kucuk aci yaklasimi degil, tam formul: yari-genislik acisi atan ile.
    Menzil sifira giderse tavan W (kadraji doldurur)."""
    if menzil_m <= 0.01:
        return float(W)
    yari = math.atan((TALON_KANAT_M / 2.0) / menzil_m)
    yari_fov = math.radians(hfov_deg / 2.0)
    return min(float(W), 2.0 * (yari / yari_fov) * (W / 2.0))


def icerik_kontrasti(gri, kutu, halka_carpan=2.0):
    """Kutunun ICI fona gore ne kadar KOYU/farkli? -> skor (buyuk = dolu)

    Talon fonun icinde koyu bir siluet. Olcu: halkanin medyani ile kutu icindeki
    en koyu %5'in farki, halkanin kendi sacilimina BOLUNUR -- boylece parlak gok
    ile alacakaranlik zemin ayni olcege gelir.

    Kutu bos havaya cizilmisse ic ile halka ayni istatistige sahiptir -> ~0."""
    H, W = gri.shape[:2]
    x0, y0, x1, y1 = [int(round(v)) for v in kutu]
    x0 = max(0, min(x0, W - 1)); x1 = max(x0 + 1, min(x1, W))
    y0 = max(0, min(y0, H - 1)); y1 = max(y0 + 1, min(y1, H))
    ic = gri[y0:y1, x0:x1]
    if ic.size < 4:
        return 0.0
    kw, kh = (x1 - x0), (y1 - y0)
    hx0 = max(0, int(x0 - kw * (halka_carpan - 1) / 2))
    hx1 = min(W, int(x1 + kw * (halka_carpan - 1) / 2))
    hy0 = max(0, int(y0 - kh * (halka_carpan - 1) / 2))
    hy1 = min(H, int(y1 + kh * (halka_carpan - 1) / 2))
    dis = gri[hy0:hy1, hx0:hx1].astype(np.float32).copy()
    # halkadan kutunun kendisini CIKAR (yoksa ucak hem ic hem dis sayilir)
    dis[y0 - hy0:y1 - hy0, x0 - hx0:x1 - hx0] = np.nan
    d = dis[~np.isnan(dis)]
    if d.size < 8:
        return 0.0
    d_med = float(np.median(d))
    d_std = float(np.std(d))
    ic_koyu = float(np.percentile(ic.astype(np.float32), 5))
    return (d_med - ic_koyu) / (d_std + 1.0)


def merkez_atlamasi(kutu_a, kutu_b):
    """Iki komsu kare kutusu arasindaki merkez kaymasi, KUTU BOYUTU biriminde.
    Boyuta bolunur cunku 100 px'lik kutuda 10 px kayma normal, 20 px'likte degil."""
    if kutu_a is None or kutu_b is None:
        return 0.0
    ax = (kutu_a[0] + kutu_a[2]) / 2.0; ay = (kutu_a[1] + kutu_a[3]) / 2.0
    bx = (kutu_b[0] + kutu_b[2]) / 2.0; by = (kutu_b[1] + kutu_b[3]) / 2.0
    olcek = max(kutu_a[2] - kutu_a[0], kutu_a[3] - kutu_a[1],
                kutu_b[2] - kutu_b[0], kutu_b[3] - kutu_b[1], 1.0)
    return math.hypot(bx - ax, by - ay) / olcek


def esik_yuzdelik(degerler, yuzde):
    """Referans dagilimindan esik. Bos listede None (esik uydurulmaz)."""
    v = [x for x in degerler if x is not None and math.isfinite(x)]
    if not v:
        return None
    return float(np.percentile(np.asarray(v, float), yuzde))


def bayrak_ver(olcum, esik, dusuk_kotu=True):
    """Olcum esigin kotu tarafinda mi? Esik yoksa (referans yok) hukum VERME."""
    if esik is None or olcum is None or not math.isfinite(olcum):
        return False
    return (olcum < esik) if dusuk_kotu else (olcum > esik)


# =============================================================================
#  Ana
# =============================================================================

def main(argv=None):
    ap = argparse.ArgumentParser(description="Etiketleri BAGIMSIZ sinyallerle denetle")
    ap.add_argument("--klasor", required=True)
    ap.add_argument("--ad", default="talon1")
    ap.add_argument("--gozden-gecirilen", type=int, default=-1,
                    help="bu numaraya kadar olan kareler INSAN onayli -> esikler "
                         "bu dagilimdan ogrenilir")
    ap.add_argument("--ornek", type=int, default=0,
                    help="kac kare denetlensin (0 = hepsi)")
    ap.add_argument("--model", default=os.path.join(_KOK, "models", "best.pt"))
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--hfov", type=float, default=125.0)
    ap.add_argument("--onizle", type=int, default=40, help="en kotu N kareyi ciz")
    ap.add_argument("--yuzdelik", type=float, default=2.0,
                    help="insan dagiliminin bu yuzdeliginden kotu olanlar isaretlenir")
    args = ap.parse_args(argv)

    import cv2
    tel = telemetri_oku(args.klasor)
    pngler = kare_listesi(args.klasor, args.ad)
    if args.ornek and args.ornek < len(pngler):
        adim = max(1, len(pngler) // args.ornek)
        pngler = pngler[::adim][:args.ornek]
    print("=" * 68)
    print("  DENETIM: %d kare  (klasor: %s)" % (len(pngler), args.klasor))

    ded = None
    try:
        from detection.gorsel_tespit import HedefDedektor
        ded = HedefDedektor(args.model, conf=0.25, imgsz=args.imgsz)
        if not ded.hazir:
            print("  [UYARI] dedektor yuklenemedi (%s) -> 1. sinyal DEVRE DISI"
                  % ded.hata)
            ded = None
    except Exception as e:
        print("  [UYARI] dedektor yok (%r) -> 1. sinyal DEVRE DISI" % e)

    kayit = []
    onceki = None
    for n, png in enumerate(pngler):
        base = os.path.basename(png)
        try:
            no = int(os.path.splitext(base)[0][len(args.ad) + 1:])
        except ValueError:
            continue
        sat = tel.get(base)
        txt = os.path.splitext(png)[0] + ".txt"
        W = int(sat["W"]) if sat else 1920
        H = int(sat["H"]) if sat else 1080
        try:
            with open(txt, encoding="utf-8") as f:
                kutu = yolo_oku(f.readline(), W, H)
        except OSError:
            kutu = None
        r = {"ad": base, "no": no, "kutu": kutu,
             "insan": (0 <= no <= args.gozden_gecirilen)}
        if kutu is None:
            r["bos"] = True
            kayit.append(r); onceki = None
            continue

        bgr = cv2.imread(png)
        if bgr is None:
            r["okunamadi"] = True
            kayit.append(r); onceki = None
            continue
        gri = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

        # 1) dedektor uyumu
        if ded is not None:
            d = ded.tespit_et(bgr)
            if d is not None and d["conf"] >= 0.40:
                dk = [d["cx"] - d["w"] / 2, d["cy"] - d["h"] / 2,
                      d["cx"] + d["w"] / 2, d["cy"] + d["h"] / 2]
                r["det_iou"] = iou(kutu, dk)
                r["det_conf"] = float(d["conf"])
        # 2) icerik kontrasti
        r["kontrast"] = icerik_kontrasti(gri, kutu)
        # 3) zaman surekliligi (yalniz ardisik NUMARALARDA anlamli)
        if onceki is not None and no == onceki[0] + 1:
            r["atlama"] = merkez_atlamasi(onceki[1], kutu)
        onceki = (no, kutu)
        # 4) boyut-menzil tutarliligi
        if sat and sat.get("truth_target_pos") and sat.get("truth_drone_pos"):
            menzil = float(np.linalg.norm(
                np.asarray(sat["truth_target_pos"], float)
                - np.asarray(sat["truth_drone_pos"], float))) / 100.0
            bek = beklenen_genislik_px(menzil, W, args.hfov)
            r["menzil"] = menzil
            r["boyut_orani"] = (kutu[2] - kutu[0]) / max(bek, 1e-6)
        kayit.append(r)
        if (n + 1) % 500 == 0:
            print("  ... %d/%d" % (n + 1, len(pngler)))

    # ---- ESIKLER: insan onayli karelerin dagilimindan ----
    ref = [r for r in kayit if r.get("insan") and not r.get("bos")]
    print("-" * 68)
    print("  REFERANS (insan onayli): %d kare" % len(ref))
    if len(ref) < 30:
        print("  [UYARI] referans cok kucuk -> esik ogrenilemez, sadece rapor.")
    esik = {
        "det_iou":    esik_yuzdelik([r.get("det_iou") for r in ref], args.yuzdelik),
        "kontrast":   esik_yuzdelik([r.get("kontrast") for r in ref], args.yuzdelik),
        "atlama":     esik_yuzdelik([r.get("atlama") for r in ref], 100 - args.yuzdelik),
        "boyut_alt":  esik_yuzdelik([r.get("boyut_orani") for r in ref], args.yuzdelik),
        "boyut_ust":  esik_yuzdelik([r.get("boyut_orani") for r in ref], 100 - args.yuzdelik),
    }
    print("  OGRENILEN ESIKLER (insan dagiliminin %%%.0f / %%%.0f yuzdeligi):"
          % (args.yuzdelik, 100 - args.yuzdelik))
    for k, v in esik.items():
        print("    %-11s %s" % (k, "yok" if v is None else "%.4f" % v))

    # ---- bayraklama ----
    for r in kayit:
        b = []
        if r.get("bos"):
            b.append("ETIKET_YOK")
        if r.get("okunamadi"):
            b.append("KARE_OKUNAMADI")
        if bayrak_ver(r.get("det_iou"), esik["det_iou"]):
            b.append("dedektor_uyusmuyor")
        if bayrak_ver(r.get("kontrast"), esik["kontrast"]):
            b.append("kutu_BOS_gorunuyor")
        if bayrak_ver(r.get("atlama"), esik["atlama"], dusuk_kotu=False):
            b.append("zaman_sicramasi")
        if bayrak_ver(r.get("boyut_orani"), esik["boyut_alt"]):
            b.append("kutu_KUCUK")
        if bayrak_ver(r.get("boyut_orani"), esik["boyut_ust"], dusuk_kotu=False):
            b.append("kutu_BUYUK")
        r["bayrak"] = b

    supheli = [r for r in kayit if r["bayrak"]]
    supheli.sort(key=lambda r: (-len(r["bayrak"]), r.get("det_iou", 1.0)))
    oto = [r for r in kayit if not r.get("insan")]
    oto_sup = [r for r in oto if r["bayrak"]]

    print("-" * 68)
    print("  SONUC")
    print("    denetlenen        : %d" % len(kayit))
    print("    insan onayli      : %d   (bunlarin %d'i bayrakli = referans gurultusu)"
          % (len(ref), sum(1 for r in ref if r["bayrak"])))
    print("    OTO etiketli      : %d" % len(oto))
    print("    OTO'da SUPHELI    : %d  (%%%.1f)"
          % (len(oto_sup), 100.0 * len(oto_sup) / max(len(oto), 1)))
    say = {}
    for r in supheli:
        for x in r["bayrak"]:
            say[x] = say.get(x, 0) + 1
    for k, v in sorted(say.items(), key=lambda kv: -kv[1]):
        print("      %-22s %d" % (k, v))
    iyi = [r.get("det_iou") for r in oto if r.get("det_iou") is not None]
    if iyi:
        iyi = np.asarray(iyi)
        print("    OTO dedektor-IoU  : ort %.4f  medyan %.4f  >=0.7 %%%.0f"
              % (iyi.mean(), np.median(iyi), 100 * (iyi >= 0.7).mean()))
    rf = [r.get("det_iou") for r in ref if r.get("det_iou") is not None]
    if rf:
        rf = np.asarray(rf)
        print("    INSAN dedektor-IoU: ort %.4f  medyan %.4f  >=0.7 %%%.0f"
              % (rf.mean(), np.median(rf), 100 * (rf >= 0.7).mean()))
        print("    -> OTO ile INSAN farki: %+.4f IoU" % (iyi.mean() - rf.mean()))

    # ---- onizleme ----
    if args.onizle > 0 and supheli:
        onz = os.path.join(args.klasor, "_denetim")
        os.makedirs(onz, exist_ok=True)
        for k, r in enumerate(supheli[:args.onizle]):
            p = os.path.join(args.klasor, r["ad"])
            bgr = cv2.imread(p)
            if bgr is None or r["kutu"] is None:
                continue
            x0, y0, x1, y1 = [int(v) for v in r["kutu"]]
            cv2.rectangle(bgr, (x0, y0), (x1, y1), (0, 0, 255), 2)
            cv2.putText(bgr, r["ad"], (12, 30), cv2.FONT_HERSHEY_SIMPLEX,
                        0.8, (0, 0, 255), 2)
            for j, t in enumerate(r["bayrak"]):
                cv2.putText(bgr, t, (12, 62 + j * 26), cv2.FONT_HERSHEY_SIMPLEX,
                            0.7, (0, 0, 255), 2)
            cv2.putText(bgr, "detIoU %.2f  kontrast %.2f  boyut %.2f"
                        % (r.get("det_iou", -1), r.get("kontrast", -1),
                           r.get("boyut_orani", -1)),
                        (12, bgr.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, (0, 255, 255), 2)
            cv2.imwrite(os.path.join(onz, "%03d_%s.jpg" % (k, r["ad"][:-4])), bgr)
        print("    onizleme: %d kare -> %s" % (min(args.onizle, len(supheli)), onz))

    with open(os.path.join(args.klasor, "denetim_rapor.json"), "w",
              encoding="utf-8") as f:
        json.dump({"esik": esik, "denetlenen": len(kayit),
                   "insan": len(ref), "oto": len(oto),
                   "oto_supheli": len(oto_sup), "bayrak_sayim": say,
                   "en_kotu": [{"ad": r["ad"], "bayrak": r["bayrak"],
                                "det_iou": r.get("det_iou"),
                                "kontrast": r.get("kontrast"),
                                "boyut_orani": r.get("boyut_orani")}
                               for r in supheli[:200]]},
                  f, indent=2, ensure_ascii=False)
    print("=" * 68)
    return 0


if __name__ == "__main__":
    sys.exit(main())

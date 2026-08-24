# -*- coding: utf-8 -*-
"""
================================================================================
 KUTU DOGRULA — "bu kutunun ICINDE Talon var mi?" DOGRUDAN test
================================================================================
GELISTIRME ARACI — teslim paketine girmez.

denetle.py'deki kontrast olcumu zayifti: "koyu bir cisim var mi" diye soruyordu,
"TALON var mi" diye degil. Bulut golgesi, zemin lekesi, HUD yazisi da koyu.

BU ARAC UC SORUYU AYRI AYRI YANITLIYOR:

  1) KUTUNUN ICINDE Talon var mi?
     Kutu bolgesi kirpilir, buyutulur, DEDEKTORE verilir. Kirpilmis goruntude
     hedef kadraji doldurdugu icin bu, tam kareye gore COK daha kolay bir soru
     -> dedektor burada guvenilirdir. Talon varsa yuksek guvenle bulur.

  2) KAREDE hic Talon var mi?
     Tam kare dedektore verilir (SAHI dilimlemesiyle, uzak/kucuk hedef icin).
     Hicbir yerde bulunamiyorsa o karede gorunur bir Talon olmayabilir --
     kullanicinin dedigi durum. Boyle kareler ETIKETLENMEMELI.

  3) Kutu DOGRU Talon'un uzerinde mi?
     Tam karede bulunan en iyi kutu ile etiketin ortusmesi (IoU).

--------------------------------------------------------------------------------
 ESIKLER: INSANIN ONAYLADIGI 766 KAREDEN
--------------------------------------------------------------------------------
Esik uydurulmaz. Ayni uc olcum once insanin cizdigi kutularda hesaplanir; o
dagilimin alt yuzdeligi esik olur. Olcut sudur: "insanin OK dedigi kutular
nasil goruniyorsa". Referans yoksa arac hukum vermez.

--------------------------------------------------------------------------------
 HUKUMLER
--------------------------------------------------------------------------------
  OK          kutunun icinde Talon var (kirpma testi gecti)
  KUTU_YANLIS kutuda Talon yok AMA karede var -> kutu yanlis yerde, ONARILABILIR
  TALON_YOK   ne kutuda ne karede Talon var -> kare etiketlenmemeli, ATILMALI
  BELIRSIZ    kanit yetersiz -> insan baksin (asla sessizce degistirilmez)

KULLANIM
    python veriseti/kutu_dogrula.py --klasor C:\\...\\talon_pozitif --gozden-gecirilen 770
    python veriseti/kutu_dogrula.py --klasor ... --gozden-gecirilen 770 --ornek 600
================================================================================
"""
import os
import sys
import json
import argparse

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _KOK not in sys.path:
    sys.path.insert(0, _KOK)

import numpy as np

from veriseti.bbox_etiketle import telemetri_oku, yolo_oku, kare_listesi
from veriseti.kalibre_et import iou

OK, KUTU_YANLIS, TALON_YOK, BELIRSIZ = "OK", "KUTU_YANLIS", "TALON_YOK", "BELIRSIZ"


# =============================================================================
#  Saf yardimcilar (birim testli: tests/test_kutu_dogrula.py)
# =============================================================================

def kirpma_kutusu(kutu, W, H, pay=0.6, asgari=64):
    """Kutu etrafinda dedektore verilecek KIRPMA bolgesi. -> (x0,y0,x1,y1) int

    `pay` kadar genisletilir: dedektorun nesneyi taniyabilmesi icin cevresinden
    biraz baglam gerekir, ayrica kutu biraz kaymissa hedef yine kirpmaya girer.
    `asgari` ile cok kucuk kirpmalar buyutulur (10 px'lik kirpma taninmaz)."""
    x0, y0, x1, y1 = kutu
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    w = max(x1 - x0, asgari) * (1.0 + pay)
    h = max(y1 - y0, asgari) * (1.0 + pay)
    kx0 = int(max(0, round(cx - w / 2))); kx1 = int(min(W, round(cx + w / 2)))
    ky0 = int(max(0, round(cy - h / 2))); ky1 = int(min(H, round(cy + h / 2)))
    if kx1 <= kx0: kx0, kx1 = 0, min(W, asgari)
    if ky1 <= ky0: ky0, ky1 = 0, min(H, asgari)
    return kx0, ky0, kx1, ky1


def hukum_ver(kirp_conf, kare_conf, kare_iou, kirp_esik, kare_esik, iou_esik):
    """Uc olcumden hukum. -> (hukum, sebep)

    Sira onemli: once "kutuda var mi", sonra "karede var mi". Kutuda varsa
    kutunun yeri dogrudur, baska kanita gerek yok."""
    if kirp_conf is not None and kirp_conf >= kirp_esik:
        if kare_iou is not None and kare_iou < iou_esik and \
                kare_conf is not None and kare_conf >= kare_esik:
            # kutuda bir sey var ama karedeki EN IYI hedef baska yerde:
            # ikinci bir ucak ya da kutu yanlis ucakta olabilir -> insan baksin
            return BELIRSIZ, "kutuda_var_ama_karede_baska_hedef_daha_guclu"
        return OK, "kutuda_talon_var"
    if kare_conf is not None and kare_conf >= kare_esik:
        return KUTU_YANLIS, "kutuda_yok_ama_karede_var"
    if kirp_conf is not None and kare_conf is not None:
        return TALON_YOK, "ne_kutuda_ne_karede_talon_yok"
    return BELIRSIZ, "olcum_alinamadi"


def alt_yuzdelik(degerler, yuzde):
    v = [x for x in degerler if x is not None and np.isfinite(x)]
    if not v:
        return None
    return float(np.percentile(np.asarray(v, float), yuzde))


# =============================================================================
#  Ana
# =============================================================================

def main(argv=None):
    ap = argparse.ArgumentParser(description="Kutunun icinde Talon var mi?")
    ap.add_argument("--klasor", required=True)
    ap.add_argument("--ad", default="talon1")
    ap.add_argument("--gozden-gecirilen", type=int, required=True)
    ap.add_argument("--ornek", type=int, default=0)
    ap.add_argument("--model", default=os.path.join(_KOK, "models", "best.pt"))
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--yuzdelik", type=float, default=5.0,
                    help="insan dagiliminin bu yuzdeligi esik olur")
    ap.add_argument("--onizle", type=int, default=40)
    args = ap.parse_args(argv)

    import cv2
    from detection.gorsel_tespit import HedefDedektor
    tel = telemetri_oku(args.klasor)
    pngler = kare_listesi(args.klasor, args.ad)
    if args.ornek and args.ornek < len(pngler):
        pngler = pngler[::max(1, len(pngler) // args.ornek)][:args.ornek]

    # DUSUK esikli dedektor: burada karar vermiyoruz, OLCUM aliyoruz.
    # Esikleri sonra insan dagilimindan ogrenecegiz.
    ded = HedefDedektor(args.model, conf=0.05, imgsz=args.imgsz)
    if not ded.hazir:
        print("[HATA] dedektor yuklenemedi: %s" % ded.hata)
        return 2
    # tam kare taramasi SAHI ile (uzak/kucuk hedef kacmasin)
    ded_kare = HedefDedektor(args.model, conf=0.05, imgsz=args.imgsz, sahi=True,
                             sahi_dilim=640, sahi_ortusme=0.2, sahi_tam_kare=True)

    print("=" * 70)
    print("  KUTU DOGRULAMA: %d kare" % len(pngler))
    kayit = []
    for n, png in enumerate(pngler):
        base = os.path.basename(png)
        try:
            no = int(os.path.splitext(base)[0][len(args.ad) + 1:])
        except ValueError:
            continue
        sat = tel.get(base)
        W = int(sat["W"]) if sat else 1920
        H = int(sat["H"]) if sat else 1080
        txt = os.path.splitext(png)[0] + ".txt"
        try:
            with open(txt, encoding="utf-8") as f:
                kutu = yolo_oku(f.readline(), W, H)
        except OSError:
            kutu = None
        r = {"ad": base, "no": no, "insan": 0 <= no <= args.gozden_gecirilen,
             "kutu": kutu}
        bgr = cv2.imread(png)
        if bgr is None or kutu is None:
            r["hukum"] = BELIRSIZ; r["sebep"] = "kare_veya_etiket_yok"
            kayit.append(r); continue

        # 1) KUTUNUN ICI
        kx0, ky0, kx1, ky1 = kirpma_kutusu(kutu, W, H)
        kirp = bgr[ky0:ky1, kx0:kx1]
        kd = ded.tespit_et(kirp) if kirp.size else None
        r["kirp_conf"] = float(kd["conf"]) if kd else 0.0
        # 2) TUM KARE
        td = ded_kare.tespit_et(bgr)
        if td:
            tk = [td["cx"] - td["w"] / 2, td["cy"] - td["h"] / 2,
                  td["cx"] + td["w"] / 2, td["cy"] + td["h"] / 2]
            r["kare_conf"] = float(td["conf"])
            r["kare_iou"] = iou(kutu, tk)
            r["kare_kutu"] = tk
        else:
            r["kare_conf"] = 0.0
            r["kare_iou"] = 0.0
        kayit.append(r)
        if (n + 1) % 400 == 0:
            print("  ... %d/%d" % (n + 1, len(pngler)))

    # ---- ESIKLER: insanin onayladigi karelerden ----
    ref = [r for r in kayit if r["insan"] and r.get("kutu") is not None]
    kirp_esik = alt_yuzdelik([r.get("kirp_conf") for r in ref], args.yuzdelik)
    kare_esik = alt_yuzdelik([r.get("kare_conf") for r in ref], args.yuzdelik)
    iou_esik = alt_yuzdelik([r.get("kare_iou") for r in ref], args.yuzdelik)
    print("-" * 70)
    print("  REFERANS: %d insan onayli kare" % len(ref))
    print("  OGRENILEN ESIKLER (insan dagiliminin %%%.0f yuzdeligi):" % args.yuzdelik)
    print("    kutu-ici conf : %s" % ("yok" if kirp_esik is None else "%.3f" % kirp_esik))
    print("    tam-kare conf : %s" % ("yok" if kare_esik is None else "%.3f" % kare_esik))
    print("    kutu-kare IoU : %s" % ("yok" if iou_esik is None else "%.3f" % iou_esik))
    if kirp_esik is None:
        print("  [HATA] referans yok, hukum verilemez."); return 2

    for r in kayit:
        if r.get("hukum"):
            continue
        r["hukum"], r["sebep"] = hukum_ver(
            r.get("kirp_conf"), r.get("kare_conf"), r.get("kare_iou"),
            kirp_esik, kare_esik, iou_esik)

    oto = [r for r in kayit if not r["insan"]]
    print("-" * 70)
    for grup, ad in ((ref, "INSAN (766)"), (oto, "OTO")):
        say = {}
        for r in grup:
            say[r["hukum"]] = say.get(r["hukum"], 0) + 1
        top = max(len(grup), 1)
        print("  %-12s  %s" % (ad, "  ".join(
            "%s %d (%%%.1f)" % (k, say.get(k, 0), 100.0 * say.get(k, 0) / top)
            for k in (OK, KUTU_YANLIS, TALON_YOK, BELIRSIZ))))
    kirp = np.array([r.get("kirp_conf", 0) for r in ref])
    kirp_o = np.array([r.get("kirp_conf", 0) for r in oto])
    print("  kutu-ici guven: INSAN ort %.3f medyan %.3f | OTO ort %.3f medyan %.3f"
          % (kirp.mean(), np.median(kirp), kirp_o.mean(), np.median(kirp_o)))

    sorunlu = [r for r in oto if r["hukum"] in (KUTU_YANLIS, TALON_YOK)]
    sorunlu.sort(key=lambda r: r.get("kirp_conf", 0))
    if args.onizle > 0 and sorunlu:
        onz = os.path.join(args.klasor, "_kutu_dogrula")
        os.makedirs(onz, exist_ok=True)
        for k, r in enumerate(sorunlu[:args.onizle]):
            bgr = cv2.imread(os.path.join(args.klasor, r["ad"]))
            if bgr is None:
                continue
            x0, y0, x1, y1 = [int(v) for v in r["kutu"]]
            cv2.rectangle(bgr, (x0, y0), (x1, y1), (0, 0, 255), 2)
            cv2.putText(bgr, "ETIKET", (x0, max(y0 - 8, 14)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            if r.get("kare_kutu"):
                a, b, c, d = [int(v) for v in r["kare_kutu"]]
                cv2.rectangle(bgr, (a, b), (c, d), (0, 255, 0), 2)
                cv2.putText(bgr, "DEDEKTOR", (a, max(b - 8, 14)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.putText(bgr, "%s  %s" % (r["hukum"], r["sebep"]), (12, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            cv2.putText(bgr, "kutu-ici %.2f  kare %.2f  IoU %.2f"
                        % (r.get("kirp_conf", 0), r.get("kare_conf", 0),
                           r.get("kare_iou", 0)), (12, 62),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv2.imwrite(os.path.join(onz, "%03d_%s.jpg" % (k, r["ad"][:-4])), bgr)
        print("  onizleme: %d kare -> %s" % (min(args.onizle, len(sorunlu)), onz))

    with open(os.path.join(args.klasor, "kutu_dogrula_rapor.json"), "w",
              encoding="utf-8") as f:
        json.dump({"esik": {"kirp": kirp_esik, "kare": kare_esik, "iou": iou_esik},
                   "hukum": {r["ad"]: r["hukum"] for r in kayit},
                   "sorunlu": [{"ad": r["ad"], "hukum": r["hukum"],
                                "sebep": r["sebep"], "kirp_conf": r.get("kirp_conf"),
                                "kare_conf": r.get("kare_conf"),
                                "kare_iou": r.get("kare_iou"),
                                "kare_kutu": r.get("kare_kutu")}
                               for r in sorunlu]}, f, indent=2, ensure_ascii=False)
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())

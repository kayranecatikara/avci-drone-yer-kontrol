# -*- coding: utf-8 -*-
"""
================================================================================
 OLC-ONAR — etiketleri tam-kare dedektorle olc, KIRIK olanlari onar
================================================================================
GELISTIRME ARACI — teslim paketine girmez.

Kirpma testi basarisiz oldu (best.pt 640'ta KUCUK hedefle egitildi; buyutulmus
kirpmayi tanimiyor -- insan onayli kutularda bile guven medyani 0.19). Calisan
tek bagimsiz sinyal TAM KARE dedektorudur:
    insan etiketi  <-> dedektor : IoU 0.9266
    oto etiketi    <-> dedektor : IoU 0.8474

--------------------------------------------------------------------------------
 NEDEN HER UYUSMAZLIK ONARILMIYOR (kritik karar)
--------------------------------------------------------------------------------
Etiketi her farkta dedektorun kutusuyla degistirmek, veri setini dedektorun
KENDI CIKTISINA cevirir. O zaman yeni model yalnizca best.pt'nin bildigini
ogrenir; truth geometrisinden gelen BAGIMSIZ bilgi ve dedektorun goremedigi
kareler kaybolur (kendi ciktisiyla egitim = hatalarin pekismesi).

O yuzden dedektor SADECE KIRIGI TAMIR ETMEK icin kullanilir:
  * IoU < `--kirik-esik` (varsayilan 0.50): kutular BASKA BASKA yerleri
    gosteriyor -- bu stil farki degil, biri acikca yanlis.
  * dedektor guveni >= `--conf-esik`: hangisinin yanlis oldugunu soyleyebilmek
    icin dedektorun kendinden emin olmasi gerekir.
Hafif farklarda (IoU 0.5-0.87) projeksiyon KORUNUR: truth geometrisi taraflidir
diye bir kanit yok, sadece insan stilinden biraz uzak.

KORUMA: --koru-kadar sinirindaki insan emegine dokunulmaz.
SILME:  dedektor de bulamiyorsa kare `_silinen/` altina TASINIR (geri alinabilir).

KULLANIM
    python veriseti/olc_onar.py --klasor C:\\...\\talon_pozitif --koru-kadar 770
    python veriseti/olc_onar.py --klasor ... --koru-kadar 770 --kuru
================================================================================
"""
import os
import sys
import json
import shutil
import argparse

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _KOK not in sys.path:
    sys.path.insert(0, _KOK)

import numpy as np

from veriseti.bbox_etiketle import (telemetri_oku, yolo_oku, yolo_satiri,
                                    kare_listesi, silme_hedefi)
from veriseti.kalibre_et import iou

ONAR, SIL, BIRAK = "onar", "sil", "birak"


# =============================================================================
#  Saf karar (birim testli: tests/test_olc_onar.py)
# =============================================================================

def onarim_karari(etiket_var, det_kutu, det_conf, etiket_det_iou,
                  kirik_esik=0.50, conf_esik=0.80):
    """-> (karar, sebep)

    etiket_var     : karede etiket (kutu) var mi
    det_kutu/conf  : tam-kare dedektorun kutusu ve guveni (bulamadiysa None)
    etiket_det_iou : ikisinin ortusmesi
    """
    guvenli_det = det_kutu is not None and det_conf is not None and det_conf >= conf_esik
    if not etiket_var:
        # etiket yok: dedektor guvenle bulduysa doldur, bulamadiysa kareyi at
        return (ONAR, "etiket_yoktu_dedektor_buldu") if guvenli_det \
            else (SIL, "etiket_yok_dedektor_de_bulamadi")
    if etiket_det_iou is None:
        return BIRAK, "olcum_yok"
    if etiket_det_iou >= kirik_esik:
        return BIRAK, "uyumlu_veya_hafif_fark"
    if guvenli_det:
        return ONAR, "kirik_dedektor_guvenli"
    return BIRAK, "kirik_ama_dedektor_emin_degil"


def dagilim(v):
    """IoU dagilim ozeti (rapor + kiyas icin)."""
    a = np.asarray([x for x in v if x is not None], float)
    if a.size == 0:
        return {}
    return {"n": int(a.size), "ort": float(a.mean()), "medyan": float(np.median(a)),
            "p10": float(np.percentile(a, 10)), "p90": float(np.percentile(a, 90)),
            "ge70": float((a >= 0.70).mean()), "ge85": float((a >= 0.85).mean()),
            "lt50": float((a < 0.50).mean())}


def yaz_dagilim(ad, d):
    if not d:
        print("  %-22s (olcum yok)" % ad); return
    print("  %-22s ort %.4f  medyan %.4f  p10 %.4f  >=0.7 %%%.0f  >=0.85 %%%.0f  <0.5 %%%.1f"
          % (ad, d["ort"], d["medyan"], d["p10"], 100 * d["ge70"],
             100 * d["ge85"], 100 * d["lt50"]))


# =============================================================================
#  Ana
# =============================================================================

def main(argv=None):
    ap = argparse.ArgumentParser(description="Etiketleri olc, kirik olanlari onar")
    ap.add_argument("--klasor", required=True)
    ap.add_argument("--ad", default="talon1")
    ap.add_argument("--koru-kadar", type=int, default=-1)
    ap.add_argument("--model", default=os.path.join(_KOK, "models", "best.pt"))
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--kirik-esik", type=float, default=0.50)
    ap.add_argument("--conf-esik", type=float, default=0.80)
    ap.add_argument("--kuru", action="store_true")
    ap.add_argument("--onizle", type=int, default=30)
    args = ap.parse_args(argv)

    import cv2
    from detection.gorsel_tespit import HedefDedektor
    ded = HedefDedektor(args.model, conf=0.25, imgsz=args.imgsz)
    if not ded.hazir:
        print("[HATA] dedektor yuklenemedi: %s" % ded.hata); return 2

    tel = telemetri_oku(args.klasor)
    pngler = kare_listesi(args.klasor, args.ad)
    print("=" * 74)
    print("  OLC-ONAR %s   kare: %d"
          % ("(KURU KOSU)" if args.kuru else "", len(pngler)))
    print("  kirik esigi %.2f   dedektor conf esigi %.2f"
          % (args.kirik_esik, args.conf_esik))

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
        bgr = cv2.imread(png)
        if bgr is None:
            continue
        d = ded.tespit_et(bgr)
        dk = dc = None
        if d is not None:
            dk = [d["cx"] - d["w"] / 2, d["cy"] - d["h"] / 2,
                  d["cx"] + d["w"] / 2, d["cy"] + d["h"] / 2]
            dc = float(d["conf"])
        io = iou(kutu, dk) if (kutu is not None and dk is not None) else None
        kayit.append({"ad": base, "no": no, "txt": txt, "png": png,
                      "insan": 0 <= no <= args.koru_kadar,
                      "kutu": kutu, "det": dk, "conf": dc, "iou": io,
                      "W": W, "H": H})
        if (n + 1) % 800 == 0:
            print("  ... %d/%d" % (n + 1, len(pngler)))

    insan = [r for r in kayit if r["insan"]]
    oto = [r for r in kayit if not r["insan"]]
    print("-" * 74)
    print("  ONCE")
    yaz_dagilim("INSAN (%d)" % len(insan), dagilim([r["iou"] for r in insan]))
    yaz_dagilim("OTO   (%d)" % len(oto), dagilim([r["iou"] for r in oto]))

    say = {ONAR: 0, SIL: 0, BIRAK: 0}
    sebepler = {}
    onarilan = []
    for r in oto:
        karar, sebep = onarim_karari(r["kutu"] is not None, r["det"], r["conf"],
                                     r["iou"], args.kirik_esik, args.conf_esik)
        r["karar"] = karar
        say[karar] += 1
        sebepler[sebep] = sebepler.get(sebep, 0) + 1
        if karar == ONAR:
            onarilan.append(r)
            if not args.kuru:
                with open(r["txt"], "w", encoding="utf-8") as f:
                    f.write(yolo_satiri(r["det"], r["W"], r["H"]) + "\n")
            r["yeni_iou"] = 1.0            # dedektorun kutusu gecti
        elif karar == SIL:
            if not args.kuru:
                hp, ht = silme_hedefi(r["png"], args.klasor)
                os.makedirs(os.path.dirname(hp), exist_ok=True)
                try:
                    shutil.move(r["png"], hp)
                    if os.path.exists(r["txt"]):
                        shutil.move(r["txt"], ht)
                except Exception:
                    pass

    print("-" * 74)
    print("  KARARLAR (yalniz OTO bolgesi; insan %d kare dokunulmadi)" % len(insan))
    print("    ONARILAN %d   SILINEN %d   BIRAKILAN %d"
          % (say[ONAR], say[SIL], say[BIRAK]))
    for k, v in sorted(sebepler.items(), key=lambda kv: -kv[1]):
        print("      %-34s %d" % (k, v))

    kalan = [r for r in oto if r.get("karar") != SIL]
    sonra = [r.get("yeni_iou", r["iou"]) for r in kalan]
    print("-" * 74)
    print("  SONRA")
    yaz_dagilim("INSAN (degismedi)", dagilim([r["iou"] for r in insan]))
    yaz_dagilim("OTO   (%d)" % len(kalan), dagilim(sonra))

    if args.onizle > 0 and onarilan:
        onz = os.path.join(args.klasor, "_onarim")
        os.makedirs(onz, exist_ok=True)
        for k, r in enumerate(onarilan[:args.onizle]):
            bgr = cv2.imread(os.path.join(args.klasor, r["ad"]))
            if bgr is None:
                continue
            if r["kutu"]:
                a, b, c, e = [int(v) for v in r["kutu"]]
                cv2.rectangle(bgr, (a, b), (c, e), (0, 0, 255), 2)
                cv2.putText(bgr, "ESKI", (a, max(b - 8, 14)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            a, b, c, e = [int(v) for v in r["det"]]
            cv2.rectangle(bgr, (a, b), (c, e), (0, 255, 0), 2)
            cv2.putText(bgr, "YENI (conf %.2f)" % r["conf"], (a, max(b - 8, 14)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.putText(bgr, "%s  eski IoU %.2f" % (r["ad"], r["iou"] or -1),
                        (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            cv2.imwrite(os.path.join(onz, "%03d_%s.jpg" % (k, r["ad"][:-4])), bgr)
        print("  onizleme: %d kare -> %s" % (min(args.onizle, len(onarilan)), onz))

    with open(os.path.join(args.klasor, "olc_onar_rapor.json"), "w",
              encoding="utf-8") as f:
        json.dump({"kuru": args.kuru, "say": say, "sebepler": sebepler,
                   "once": {"insan": dagilim([r["iou"] for r in insan]),
                            "oto": dagilim([r["iou"] for r in oto])},
                   "sonra": {"oto": dagilim(sonra)},
                   "onarilan": [r["ad"] for r in onarilan]},
                  f, indent=2)
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())

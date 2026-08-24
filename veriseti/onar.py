# -*- coding: utf-8 -*-
"""
================================================================================
 ONAR — denetimin yakaladigi bozuk etiketleri duzelt ya da AT
================================================================================
GELISTIRME ARACI — teslim paketine girmez.

denetle.py bozuk etiketleri buluyor ama duzeltmiyor. Bu arac, iki BAGIMSIZ
sinyalin ayni yone isaret ettigi durumlarda karar verir.

--------------------------------------------------------------------------------
 KARAR MANTIGI (onar_karari)
--------------------------------------------------------------------------------
Her supheli kare icin iki kutu var: PROJEKSIYON (mevcut etiket) ve DEDEKTOR.
Her ikisinin de "icerik kontrasti" olculur -- kutunun icinde gercekten koyu bir
cisim var mi.

  ONAR   : projeksiyon kutusu BOS gorunuyor, dedektor kutusu DOLU, ikisi de
           birbirinden uzak (IoU dusuk) ve dedektor GUVENLI.
           -> iki bagimsiz sinyal "etiket yanlis yerde, dogrusu burada" diyor.
  SIL    : projeksiyon kutusu BOS ve dedektor de kurtaracak bir sey bulamadi.
           -> karede ne oldugunu bilmiyoruz; bilinmeyen etiket egitime GIRMEZ.
  BIRAK  : projeksiyon kutusu DOLU (etiket muhtemelen dogru, sadece gevsek) ya
           da kanit yetersiz. SUPHE TEK BASINA MUDAHALE SEBEBI DEGILDIR.

Neden bu kadar temkinli: yanlis "onarim" sessizce bozuk etiket uretir ve bunu
sonradan yakalamak cok zordur. Kanit iki kaynaktan da gelmiyorsa dokunmuyoruz.

SILME = TASIMA: dosyalar `_silinen/` altina gider, geri alinabilir.
KORUMA: --koru-kadar sinirindaki insan emegine HICBIR kosulda dokunulmaz.

KULLANIM
    python veriseti/onar.py --klasor C:\\...\\talon_pozitif --koru-kadar 770
    python veriseti/onar.py --klasor ... --koru-kadar 770 --kuru   (deneme, yazma yok)
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
from veriseti.denetle import icerik_kontrasti
from veriseti.kalibre_et import iou


# =============================================================================
#  Saf karar (birim testli: tests/test_onar.py)
# =============================================================================

ONAR, SIL, BIRAK = "onar", "sil", "birak"


def onar_karari(proj_kontrast, det_kutu, det_kontrast, det_conf, proj_det_iou,
                kontrast_esik, conf_esik=0.60, ayrik_iou=0.30):
    """Bozuk etiket icin ne yapmali? -> (karar, sebep)

    proj_kontrast : mevcut etiketin ic-kontrasti (dusuk = kutu bos)
    det_kutu      : dedektorun kutusu (yoksa None)
    det_kontrast  : dedektor kutusunun ic-kontrasti
    det_conf      : dedektor guveni
    proj_det_iou  : iki kutunun ortusmesi (dusuk = farkli yerleri gosteriyorlar)
    """
    proj_bos = proj_kontrast is not None and proj_kontrast < kontrast_esik
    if not proj_bos:
        return BIRAK, "etiket_dolu_gorunuyor"
    if det_kutu is None or det_conf is None or det_conf < conf_esik:
        return SIL, "kutu_bos_ve_dedektor_bulamadi"
    if det_kontrast is None or det_kontrast < kontrast_esik:
        return SIL, "kutu_bos_ve_dedektor_kutusu_da_bos"
    if proj_det_iou is not None and proj_det_iou >= ayrik_iou:
        return BIRAK, "kutular_zaten_ayni_yerde"
    return ONAR, "dedektor_dolu_kutu_gosteriyor"


# =============================================================================
#  Ana
# =============================================================================

def main(argv=None):
    ap = argparse.ArgumentParser(description="Bozuk etiketleri onar veya at")
    ap.add_argument("--klasor", required=True)
    ap.add_argument("--ad", default="talon1")
    ap.add_argument("--koru-kadar", type=int, default=-1,
                    help="bu numaraya kadar olan kareler INSAN emegi -> dokunulmaz")
    ap.add_argument("--rapor", default="",
                    help="denetim_rapor.json (vars: klasor icinden)")
    ap.add_argument("--model", default=os.path.join(_KOK, "models", "best.pt"))
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--conf-esik", type=float, default=0.60)
    ap.add_argument("--kuru", action="store_true",
                    help="DENEME: hicbir dosya yazilmaz/tasinmaz, sadece sayilir")
    args = ap.parse_args(argv)

    import cv2
    rapor_yolu = args.rapor or os.path.join(args.klasor, "denetim_rapor.json")
    with open(rapor_yolu, encoding="utf-8") as f:
        rapor = json.load(f)
    kontrast_esik = rapor["esik"]["kontrast"]
    print("=" * 68)
    print("  ONARIM %s" % ("(KURU KOSU - hicbir sey yazilmaz)" if args.kuru else ""))
    print("  kontrast esigi (insan dagilimindan): %.4f" % kontrast_esik)

    # denetimden "kutu_BOS_gorunuyor" bayrakli kareler; rapor ilk 200'u tutuyor,
    # tam liste icin kontrasti yeniden olcecegiz -> tum OTO kareleri tara.
    tel = telemetri_oku(args.klasor)
    from detection.gorsel_tespit import HedefDedektor
    ded = HedefDedektor(args.model, conf=0.25, imgsz=args.imgsz)
    if not ded.hazir:
        print("  [HATA] dedektor yuklenemedi: %s" % ded.hata)
        return 2

    say = {ONAR: 0, SIL: 0, BIRAK: 0, "korundu": 0, "atlandi": 0}
    sebepler = {}
    onarilan, silinen = [], []
    pngler = kare_listesi(args.klasor, args.ad)
    for n, png in enumerate(pngler):
        base = os.path.basename(png)
        try:
            no = int(os.path.splitext(base)[0][len(args.ad) + 1:])
        except ValueError:
            continue
        if 0 <= no <= args.koru_kadar:
            say["korundu"] += 1
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
            say["atlandi"] += 1
            continue
        gri = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

        pk = icerik_kontrasti(gri, kutu) if kutu is not None else -1.0
        if kutu is not None and pk >= kontrast_esik:
            say[BIRAK] += 1                      # dolu gorunuyor: hizli yol
            if (n + 1) % 500 == 0:
                print("  ... %d/%d" % (n + 1, len(pngler)))
            continue

        d = ded.tespit_et(bgr)
        dk = dc = dkon = None
        if d is not None:
            dk = [d["cx"] - d["w"] / 2, d["cy"] - d["h"] / 2,
                  d["cx"] + d["w"] / 2, d["cy"] + d["h"] / 2]
            dc = float(d["conf"])
            dkon = icerik_kontrasti(gri, dk)
        pd_iou = iou(kutu, dk) if (kutu is not None and dk is not None) else None
        karar, sebep = onar_karari(pk, dk, dkon, dc, pd_iou, kontrast_esik,
                                   args.conf_esik)
        say[karar] += 1
        sebepler[sebep] = sebepler.get(sebep, 0) + 1
        if karar == ONAR:
            onarilan.append((base, pk, dkon, dc))
            if not args.kuru:
                with open(txt, "w", encoding="utf-8") as f:
                    f.write(yolo_satiri(dk, W, H) + "\n")
        elif karar == SIL:
            silinen.append((base, pk, dc))
            if not args.kuru:
                hp, ht = silme_hedefi(png, args.klasor)
                os.makedirs(os.path.dirname(hp), exist_ok=True)
                try:
                    shutil.move(png, hp)
                    if os.path.exists(txt):
                        shutil.move(txt, ht)
                except Exception:
                    pass
        if (n + 1) % 500 == 0:
            print("  ... %d/%d" % (n + 1, len(pngler)))

    print("-" * 68)
    print("  KORUNAN (insan)   : %d" % say["korundu"])
    print("  BIRAKILAN         : %d  (etiket dolu gorunuyor)" % say[BIRAK])
    print("  ONARILAN          : %d  (dedektor kutusu gecirildi)" % say[ONAR])
    print("  SILINEN           : %d  (-> _silinen/, geri alinabilir)" % say[SIL])
    if say["atlandi"]:
        print("  atlandi           : %d" % say["atlandi"])
    print("  sebep kirilimi:")
    for k, v in sorted(sebepler.items(), key=lambda kv: -kv[1]):
        print("    %-38s %d" % (k, v))
    if onarilan[:5]:
        print("  onarim ornekleri (proj kontrast -> det kontrast, conf):")
        for a, pk, dkon, dc in onarilan[:5]:
            print("    %-18s %5.2f -> %5.2f  (conf %.2f)" % (a, pk, dkon, dc))
    with open(os.path.join(args.klasor, "onarim_rapor.json"), "w",
              encoding="utf-8") as f:
        json.dump({"say": say, "sebepler": sebepler, "kuru": args.kuru,
                   "onarilan": [a for a, _, _, _ in onarilan],
                   "silinen": [a for a, _, _ in silinen]}, f, indent=2)
    print("=" * 68)
    return 0


if __name__ == "__main__":
    sys.exit(main())

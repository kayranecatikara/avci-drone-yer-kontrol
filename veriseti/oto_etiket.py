# -*- coding: utf-8 -*-
"""
================================================================================
 OTO ETIKET — truth projeksiyonundan TOPLU bbox etiketi
================================================================================
GELISTIRME ARACI — teslim paketine girmez.

Yakalanan karelerin .txt'lerini truth projeksiyonundan doldurur. Elle cizmeye
gerek kalmaz; insan yalnizca ONIZLEMEDEN gozle dogrular.

NEDEN GUVENILIR (olculdu, 10 elle cizilmis kare):
    marj_x=0.07 marj_y=0.10 ile elle cizim <-> projeksiyon
        IoU ortalama 0.868   medyan 0.907   max 0.961
    (marj degerleri kullanicinin KENDI cizim tarziyla kalibre edildi:
     0.06/0.20 -> IoU 0.825 idi, kutu dikeyde fazla sisiyordu)

ATLANANLAR (etiket YAZILMAZ, .txt bos kalir -> etiketleyicide elle cizilir):
    truth_yok        telemetride truth konum yok
    arkada           hedef kamera arkasinda
    kismi            projekte kutu kadraja TAM sigmiyor (zarf guvenilmez)
    cok_kucuk        kisa kenar < --min-px (birkac piksellik kutu ogretmez)
    kare_yok         telemetri satiri var, PNG yok

VARSAYILAN: mevcut DOLU .txt'lere DOKUNULMAZ (elle duzelttigin etiket korunur).
--ustune-yaz ile hepsi yeniden yazilir.

KULLANIM
    python veriseti/oto_etiket.py --klasor C:\\...\\talon_pozitif
    python veriseti/oto_etiket.py --klasor ... --onizle 40   # QA cizimleri
    python veriseti/oto_etiket.py --klasor ... --ustune-yaz
================================================================================
"""
import os
import sys
import json
import argparse

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _KOK not in sys.path:
    sys.path.insert(0, _KOK)

from veriseti.bbox_etiketle import (telemetri_oku, projeksiyon_kutusu, Akis,
                                    yolo_satiri, etiketli_mi, kare_listesi)


def kalibrasyon_yukle(yol):
    """kalibre_et.py'nin urettigi duzeltme modelini yukle. -> dict | None"""
    if not yol:
        return None
    import numpy as np
    with open(yol, encoding="utf-8") as f:
        m = json.load(f)
    m["ort"] = np.asarray(m["ort"], float)
    m["std"] = np.asarray(m["std"], float)
    m["kats"] = {k: np.asarray(v, float) for k, v in m["kats"].items()}
    return m


def kalibre_uygula(kutu, model, sat, durum, W, H):
    """Ogrenilen duzeltmeyi kutuya uygula. Model yoksa kutu aynen doner."""
    if model is None:
        return kutu
    import numpy as np
    from veriseti.kalibre_et import ozellikler, kutu_duzelt, aspect_acisi
    dpos, drot, tpos, trot = (np.asarray(v, float) for v in durum)
    menzil = float(np.linalg.norm(tpos - dpos)) / 100.0
    asp = aspect_acisi(dpos, tpos, float(trot[2]))
    kisa = min(kutu[2] - kutu[0], kutu[3] - kutu[1])
    ozl = ozellikler(float(trot[0]), asp, menzil, kisa)
    ozl = (np.asarray(ozl, float) - model["ort"]) / model["std"]
    return kutu_duzelt(kutu, model["kats"], ozl)


def sebep_bul(sat, marj_x, marj_y, min_px, akis=None, dt=0.0):
    """Kare neden etiketlenemedi? -> (kutu | None, sebep)

    akis verilmisse kutu (t - dt) anindaki duruma gore projekte edilir
    (kare telemetriden eski; olculen dt = 0.10 sn)."""
    if not sat or sat.get("truth_target_pos") is None:
        return None, "truth_yok"
    d = None
    if akis is not None and len(akis) > 1:
        if not akis.kapsar(sat["t"] - dt):
            return None, "akis_disi"
        d = akis.durum(sat["t"] - dt)
    kutu = projeksiyon_kutusu(sat, marj_x, marj_y, durum=d)
    if kutu is None:
        # projeksiyon_kutusu iki sebepten None doner; ayirt etmek icin
        # kenar toleransini sinirsiz yapip tekrar dene
        genis = projeksiyon_kutusu(sat, marj_x, marj_y, kenar_tol=1e9, durum=d)
        return None, ("arkada" if genis is None else "kismi")
    if min(kutu[2] - kutu[0], kutu[3] - kutu[1]) < min_px:
        return None, "cok_kucuk"
    return kutu, "ok"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Truth projeksiyonundan toplu bbox etiketi")
    ap.add_argument("--klasor", required=True)
    ap.add_argument("--ad", default="talon1")
    ap.add_argument("--marj-x", type=float, default=0.07)
    ap.add_argument("--marj-y", type=float, default=0.10)
    ap.add_argument("--min-px", type=float, default=8.0,
                    help="kisa kenar bundan kucukse etiketleme (vars 8 px)")
    ap.add_argument("--kalibrasyon", default="",
                    help="veriseti/kalibre_et.py ciktisi (kalibrasyon.json). "
                         "Ogrenilen duzeltmeyi uygular; sabit ofsetin yerine gecer.")
    ap.add_argument("--ofset-x", type=float, default=0.0,
                    help="kutuya sabit yatay kaydirma (px). 461 elle duzeltilmis "
                         "kareyle olculdu: +4 -> IoU 0.835 -> 0.855")
    ap.add_argument("--ofset-y", type=float, default=0.0)
    ap.add_argument("--koru-kadar", type=int, default=-1,
                    help="bu NUMARAYA kadar (dahil) olan kareler KORUNUR, hic "
                         "dokunulmaz. Elle gozden gecirilmis bolgeyi korur.")
    ap.add_argument("--dt", type=float, default=0.10,
                    help="kare-telemetri gecikmesi sn (OLCULDU: 0.10; 0 = telafi yok)")
    ap.add_argument("--ustune-yaz", action="store_true",
                    help="DOLU .txt'leri de yeniden yaz (vars: dokunma)")
    ap.add_argument("--onizle", type=int, default=0,
                    help="N adet QA cizimi uret (_onizleme/ altina)")
    args = ap.parse_args(argv)

    tel = telemetri_oku(args.klasor)
    pngler = kare_listesi(args.klasor, args.ad)
    akis = Akis(os.path.join(args.klasor, "telemetri_akis.jsonl"))
    kmodel = kalibrasyon_yukle(args.kalibrasyon)
    if len(akis) < 2:
        akis = None
        if args.dt:
            print("  [UYARI] telemetri_akis.jsonl yok/kisa -> dt TELAFISI YAPILAMAZ")
    print("=" * 60)
    print("  klasor : %s" % args.klasor)
    print("  kare   : %d   telemetri satiri: %d" % (len(pngler), len(tel)))
    print("  marj   : x=%.2f y=%.2f   min kenar: %.0f px   dt=%.2f sn"
          % (args.marj_x, args.marj_y, args.min_px, args.dt))
    if args.koru_kadar >= 0:
        print("  KORUNAN: %s_0000 .. %s_%04d (elle gozden gecirildi)"
              % (args.ad, args.ad, args.koru_kadar))
    if kmodel is not None:
        cv = kmodel.get("cv", {})
        print("  KALIBRASYON: %d ornek, capraz-dog. IoU %.4f -> %.4f"
              % (kmodel.get("ornek", 0), cv.get("ham", 0), cv.get("model", 0)))
    if args.ofset_x or args.ofset_y:
        print("  ofset  : %+.0f, %+.0f px" % (args.ofset_x, args.ofset_y))

    say = {"yazildi": 0, "korundu": 0, "truth_yok": 0, "arkada": 0,
           "kismi": 0, "cok_kucuk": 0, "akis_disi": 0}
    yazilan = []
    for png in pngler:
        ad = os.path.basename(png)
        txt = os.path.splitext(png)[0] + ".txt"
        # ELLE GOZDEN GECIRILEN BOLGE: numarasi esikte veya altindaysa DOKUNMA.
        # (--ustune-yaz bile bu sinira uyar; insan emegi hicbir kosulda ezilmez.)
        if args.koru_kadar >= 0:
            try:
                no = int(os.path.splitext(ad)[0][len(args.ad) + 1:])
            except ValueError:
                no = -1
            if 0 <= no <= args.koru_kadar:
                say["korundu"] += 1
                continue
        if etiketli_mi(txt) and not args.ustune_yaz:
            say["korundu"] += 1
            continue
        sat = tel.get(ad)
        kutu, sebep = sebep_bul(sat, args.marj_x, args.marj_y, args.min_px,
                                akis, args.dt)
        if kutu is not None and kmodel is not None and akis is not None:
            kutu = kalibre_uygula(kutu, kmodel, sat,
                                  akis.durum(sat["t"] - args.dt),
                                  int(sat["W"]), int(sat["H"]))
        if kutu is None:
            say[sebep] = say.get(sebep, 0) + 1
            open(txt, "w").close()               # BOS birak -> elle cizilecek
            continue
        W, H = int(sat["W"]), int(sat["H"])
        # SABIT KAYMA TELAFISI: 461 elle duzeltilmis kareyle olculdu -- kullanici
        # kutuyu projeksiyondan tutarli sekilde ~4 px SAGDA cizyor (dt ve marjlar
        # zaten optimumdu, tek kalan sistematik fark buydu). Kaydirma sonrasi
        # kadraja kirpilir.
        if args.ofset_x or args.ofset_y:
            kutu = [kutu[0] + args.ofset_x, kutu[1] + args.ofset_y,
                    kutu[2] + args.ofset_x, kutu[3] + args.ofset_y]
            kutu = [max(0.0, min(kutu[0], W)), max(0.0, min(kutu[1], H)),
                    max(0.0, min(kutu[2], W)), max(0.0, min(kutu[3], H))]
        with open(txt, "w", encoding="utf-8") as f:
            f.write(yolo_satiri(kutu, W, H) + "\n")
        say["yazildi"] += 1
        yazilan.append((png, kutu))

    print("-" * 60)
    for k in ("yazildi", "korundu", "truth_yok", "arkada", "kismi",
              "cok_kucuk", "akis_disi"):
        print("    %-12s %d" % (k, say.get(k, 0)))
    kapsam = (100.0 * say["yazildi"] / max(len(pngler) - say["korundu"], 1))
    print("    OTO KAPSAM  %.1f%% (elle cizilecek: %d)"
          % (kapsam, say["truth_yok"] + say["arkada"] + say["kismi"] + say["cok_kucuk"]))

    if args.onizle > 0 and yazilan:
        import cv2
        onz = os.path.join(args.klasor, "_onizleme")
        os.makedirs(onz, exist_ok=True)
        adim = max(1, len(yazilan) // args.onizle)
        n = 0
        for png, kutu in yazilan[::adim][:args.onizle]:
            bgr = cv2.imread(png)
            if bgr is None:
                continue
            cv2.rectangle(bgr, (int(kutu[0]), int(kutu[1])),
                          (int(kutu[2]), int(kutu[3])), (0, 255, 0), 2)
            cv2.putText(bgr, "%s  %dx%d px" % (os.path.basename(png),
                                               int(kutu[2] - kutu[0]),
                                               int(kutu[3] - kutu[1])),
                        (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.imwrite(os.path.join(onz, os.path.basename(png).replace(".png", ".jpg")), bgr)
            n += 1
        print("    onizleme: %d kare -> %s" % (n, onz))

    with open(os.path.join(args.klasor, "oto_etiket_rapor.json"), "w",
              encoding="utf-8") as f:
        json.dump({"sayac": say, "marj": [args.marj_x, args.marj_y],
                   "min_px": args.min_px, "kare": len(pngler)}, f, indent=2)
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())

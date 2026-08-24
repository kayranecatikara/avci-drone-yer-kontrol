# -*- coding: utf-8 -*-
"""
================================================================================
 VERISETI DOGRULAYICI — "YOLO bunu gercekten okuyor mu?"
================================================================================
GELISTIRME ARACI — teslim paketine girmez.

Etiket formatinin dogru oldugunu IDDIA ETMEK yetmez. Bu arac iki katman
calistirir:

  KATMAN 1 — BICIM (kendi kontrolumuz, ultralytics'siz):
      * dosya eslesmesi (her .png'nin .txt'si var mi, tersi)
      * satir bicimi: "cls cx cy w h", 5 alan, sinif TAMSAYI
      * deger araligi: cx,cy,w,h hepsi [0,1]; w,h > 0
      * kutu kadraji TASMIYOR: cx±w/2 ve cy±h/2 icinde
      * bos .txt sayimi (= ETIKETSIZ; egitime girerse NEGATIF sayilir!)
      * suphe: asiri kucuk / asiri buyuk kutu, ayni kutunun tekrari

  KATMAN 2 — GERCEK YUKLEYICI (ultralytics'in KENDI kodu):
      Gecici bir dataset kokune sembolik olmayan KOPYA ile images/ + labels/
      duzeni kurar, data.yaml yazar, `check_det_dataset` + `YOLODataset`
      calistirir ve OKUNAN kutulari geri sayar. Ultralytics kac etiket gordu,
      bizim yazdigimizla ayni mi -> tek kanit budur.

KULLANIM
    python veriseti/dogrula.py --klasor C:\\...\\talon_pozitif [--ad talon1]
    python veriseti/dogrula.py --klasor ... --disari C:\\...\\dataset
        (--disari: dogrulama sonrasi EGITIME HAZIR duzeni kalici yazar:
         images/train images/val labels/train labels/val + data.yaml;
         ETIKETSIZ kareler DISARIDA BIRAKILIR -> yanlislikla negatif olmazlar)
================================================================================
"""
import os
import sys
import json
import glob
import random
import shutil
import argparse

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _KOK not in sys.path:
    sys.path.insert(0, _KOK)


# =============================================================================
#  Katman 1 — bicim (saf; birim testli)
# =============================================================================

def satir_dogrula(satir):
    """Tek YOLO satirini denetle. -> (ok, sebep). Sebep '' ise gecerli."""
    p = satir.split()
    if len(p) != 5:
        return False, "5 alan degil (%d)" % len(p)
    try:
        c = int(p[0])
    except ValueError:
        return False, "sinif tamsayi degil: %r" % p[0]
    if c < 0:
        return False, "sinif negatif: %d" % c
    try:
        cx, cy, w, h = (float(v) for v in p[1:])
    except ValueError:
        return False, "sayi olmayan alan"
    for ad, v in (("cx", cx), ("cy", cy), ("w", w), ("h", h)):
        if not (0.0 <= v <= 1.0):
            return False, "%s araligin disinda: %.6f" % (ad, v)
    if w <= 0 or h <= 0:
        return False, "sifir alanli kutu"
    # Kutu kadraji tasiyor mu (kucuk kayan nokta payi birakilir)
    if (cx - w / 2 < -1e-6 or cx + w / 2 > 1 + 1e-6 or
            cy - h / 2 < -1e-6 or cy + h / 2 > 1 + 1e-6):
        return False, "kutu kadraj disina tasiyor"
    return True, ""


def dosya_dogrula(txt_yolu):
    """Bir .txt dosyasini denetle. -> (durum, satirlar, hatalar)
    durum: 'bos' | 'ok' | 'hatali'"""
    try:
        with open(txt_yolu, encoding="utf-8") as f:
            ham = [s.strip() for s in f if s.strip()]
    except OSError as e:
        return "hatali", [], ["okunamadi: %r" % e]
    if not ham:
        return "bos", [], []
    hatalar = []
    for i, s in enumerate(ham):
        ok, sebep = satir_dogrula(s)
        if not ok:
            hatalar.append("satir %d: %s" % (i + 1, sebep))
    return ("ok" if not hatalar else "hatali"), ham, hatalar


def kutu_alani(satir):
    """Normalize kutu alani (supheli kucuk/buyuk taramasi icin)."""
    p = satir.split()
    return float(p[3]) * float(p[4])


# =============================================================================
#  Katman 2 — gercek ultralytics yukleyicisi
# =============================================================================

def ultralytics_ile_dogrula(ciftler, gecici_kok):
    """images/ + labels/ duzeni kur, data.yaml yaz, ULTRALYTICS'IN KENDI
    yukleyicisiyle oku. -> rapor dict. Ultralytics yoksa {'atlandi': ...}."""
    try:
        from ultralytics.data.dataset import YOLODataset
        from ultralytics.data.utils import check_det_dataset
        import ultralytics
    except Exception as e:
        return {"atlandi": "ultralytics yok/yuklenemedi: %r" % e}

    im_dir = os.path.join(gecici_kok, "images", "train")
    lb_dir = os.path.join(gecici_kok, "labels", "train")
    os.makedirs(im_dir, exist_ok=True)
    os.makedirs(lb_dir, exist_ok=True)
    for png, txt in ciftler:
        shutil.copy2(png, os.path.join(im_dir, os.path.basename(png)))
        shutil.copy2(txt, os.path.join(lb_dir, os.path.basename(txt)))

    yaml_yolu = os.path.join(gecici_kok, "data.yaml")
    with open(yaml_yolu, "w", encoding="utf-8") as f:
        f.write("path: %s\ntrain: images/train\nval: images/train\n"
                "nc: 1\nnames:\n  0: talon\n" % gecici_kok.replace("\\", "/"))

    rapor = {"ultralytics": ultralytics.__version__, "yaml": yaml_yolu}
    try:
        veri = check_det_dataset(yaml_yolu)
        rapor["check_det_dataset"] = "OK"
        rapor["names"] = veri.get("names")
        rapor["nc"] = veri.get("nc")
    except Exception as e:
        rapor["check_det_dataset"] = "HATA: %r" % e
        return rapor

    try:
        ds = YOLODataset(img_path=im_dir, data=veri, task="detect")
        rapor["yuklenen_goruntu"] = len(ds.labels)
        rapor["okunan_kutu"] = int(sum(len(l["bboxes"]) for l in ds.labels))
        rapor["etiketsiz_goruntu"] = int(sum(1 for l in ds.labels
                                             if len(l["bboxes"]) == 0))
        ilk = next((l for l in ds.labels if len(l["bboxes"])), None)
        if ilk is not None:
            rapor["ornek_bbox_xywhn"] = [round(float(v), 6)
                                         for v in ilk["bboxes"][0]]
            rapor["ornek_sinif"] = int(ilk["cls"][0][0])
            rapor["bbox_format"] = ilk.get("bbox_format")
            rapor["normalized"] = ilk.get("normalized")
        rapor["YOLODataset"] = "OK"
    except Exception as e:
        rapor["YOLODataset"] = "HATA: %r" % e
    return rapor


# =============================================================================
#  Egitime hazir disari aktarim
# =============================================================================

def disari_aktar(ciftler, hedef, val_orani=0.1, tohum=0):
    """ETIKETLI ciftleri standart YOLO duzenine yaz + data.yaml.
    ETIKETSIZ olanlar hic gelmez (yanlislikla negatif sayilmasinlar)."""
    rnd = random.Random(tohum)
    sirali = sorted(ciftler)
    rnd.shuffle(sirali)
    n_val = max(1, int(len(sirali) * val_orani)) if sirali else 0
    bolum = {"val": sirali[:n_val], "train": sirali[n_val:]}
    for b, liste in bolum.items():
        im = os.path.join(hedef, "images", b)
        lb = os.path.join(hedef, "labels", b)
        os.makedirs(im, exist_ok=True)
        os.makedirs(lb, exist_ok=True)
        for png, txt in liste:
            shutil.copy2(png, os.path.join(im, os.path.basename(png)))
            shutil.copy2(txt, os.path.join(lb, os.path.basename(txt)))
    with open(os.path.join(hedef, "data.yaml"), "w", encoding="utf-8") as f:
        f.write("path: %s\ntrain: images/train\nval: images/val\n"
                "nc: 1\nnames:\n  0: talon\n" % hedef.replace("\\", "/"))
    return {b: len(v) for b, v in bolum.items()}


# =============================================================================
#  Ana
# =============================================================================

def main(argv=None):
    ap = argparse.ArgumentParser(description="Veriseti dogrulayici (bicim + gercek yukleyici)")
    ap.add_argument("--klasor", required=True)
    ap.add_argument("--ad", default="talon1")
    ap.add_argument("--disari", default="", help="egitime hazir duzeni buraya yaz")
    ap.add_argument("--val-orani", type=float, default=0.1)
    ap.add_argument("--ornek", type=int, default=40,
                    help="gercek yukleyiciye kac kare verilsin (0=hepsi)")
    args = ap.parse_args(argv)

    pngler = sorted(glob.glob(os.path.join(args.klasor, args.ad + "_*.png")))
    print("=" * 64)
    print("  KLASOR: %s" % args.klasor)
    print("  PNG   : %d" % len(pngler))
    if not pngler:
        print("  [HATA] kare yok.")
        return 2

    # ---- Katman 1: bicim ----
    say = {"ok": 0, "bos": 0, "hatali": 0, "txt_yok": 0}
    hata_ornek, etiketli_cift, alanlar, satir_sayaci = [], [], [], {}
    for png in pngler:
        txt = os.path.splitext(png)[0] + ".txt"
        if not os.path.exists(txt):
            say["txt_yok"] += 1
            continue
        durum, satirlar, hatalar = dosya_dogrula(txt)
        say[durum] += 1
        if durum == "ok":
            etiketli_cift.append((png, txt))
            for s in satirlar:
                alanlar.append(kutu_alani(s))
                satir_sayaci[s] = satir_sayaci.get(s, 0) + 1
        elif durum == "hatali" and len(hata_ornek) < 8:
            hata_ornek.append((os.path.basename(txt), hatalar[:2]))

    print("-" * 64)
    print("  BICIM DENETIMI")
    print("    gecerli etiketli : %d" % say["ok"])
    print("    BOS (etiketsiz)  : %d   <- egitime girerse NEGATIF sayilir" % say["bos"])
    print("    HATALI           : %d" % say["hatali"])
    print("    .txt YOK         : %d" % say["txt_yok"])
    for ad, h in hata_ornek:
        print("      %s: %s" % (ad, "; ".join(h)))
    if alanlar:
        alanlar.sort()
        print("    kutu alani (kadrajin %%'si): min=%.4f  medyan=%.4f  max=%.4f"
              % (alanlar[0] * 100, alanlar[len(alanlar) // 2] * 100, alanlar[-1] * 100))
        tekrar = sum(1 for v in satir_sayaci.values() if v > 1)
        if tekrar:
            en = max(satir_sayaci.items(), key=lambda kv: kv[1])
            print("    UYARI: %d farkli kutu BIREBIR tekrar ediyor "
                  "(en cok %d kez) -> dokunulmadan Enter'lanmis olabilir"
                  % (tekrar, en[1]))

    # ---- Katman 2: gercek yukleyici ----
    print("-" * 64)
    print("  GERCEK YUKLEYICI (ultralytics)")
    if not etiketli_cift:
        print("    atlandi: gecerli etiketli kare yok")
        rapor = {"atlandi": "etiketli kare yok"}
    else:
        ornek = etiketli_cift if args.ornek <= 0 else etiketli_cift[:args.ornek]
        gecici = os.path.join(args.klasor, "_dogrulama_gecici")
        shutil.rmtree(gecici, ignore_errors=True)
        try:
            rapor = ultralytics_ile_dogrula(ornek, gecici)
            for k in ("ultralytics", "check_det_dataset", "nc", "names",
                      "YOLODataset", "yuklenen_goruntu", "okunan_kutu",
                      "etiketsiz_goruntu", "ornek_sinif", "ornek_bbox_xywhn",
                      "bbox_format", "normalized", "atlandi"):
                if k in rapor:
                    print("    %-20s %s" % (k, rapor[k]))
            bekle = len(ornek)
            if rapor.get("okunan_kutu") is not None:
                print("    %-20s %s" % ("BEKLENEN kutu", bekle))
                print("    %-20s %s" % (
                    "SONUC",
                    "UYGUN — ultralytics kutulari okudu"
                    if rapor.get("okunan_kutu") == bekle and
                    rapor.get("etiketsiz_goruntu") == 0
                    else "UYUSMAZLIK — yukaridaki sayilara bak"))
        finally:
            shutil.rmtree(gecici, ignore_errors=True)

    # ---- Disari aktarim ----
    if args.disari:
        print("-" * 64)
        bol = disari_aktar(etiketli_cift, args.disari, args.val_orani)
        print("  EGITIME HAZIR -> %s" % args.disari)
        print("    train=%d  val=%d   (ETIKETSIZ %d kare DAHIL EDILMEDI)"
              % (bol.get("train", 0), bol.get("val", 0), say["bos"]))
        print("    data.yaml yazildi (nc=1, names: {0: talon})")

    print("=" * 64)
    with open(os.path.join(args.klasor, "dogrulama_rapor.json"), "w",
              encoding="utf-8") as f:
        json.dump({"bicim": say, "ultralytics": rapor}, f, indent=2,
                  ensure_ascii=False, default=str)
    return 0 if say["hatali"] == 0 and say["txt_yok"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

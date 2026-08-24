# -*- coding: utf-8 -*-
"""
================================================================================
 PAKETLE — egitime hazir YOLO veri seti (pozitif + negatif, blok-bazli ayrim)
================================================================================
GELISTIRME ARACI — teslim paketine girmez.

--------------------------------------------------------------------------------
 EN KRITIK KARAR: TRAIN/VAL AYRIMI RASTGELE OLAMAZ
--------------------------------------------------------------------------------
Kareler TEK bir ucustan, 5 Hz ile alindi -> ardisik kareler 0.2 sn arayla,
neredeyse AYNI goruntu. Rastgele bolme yapilirsa kare N train'e, N+1 val'e
duser; val aslinda train'in kopyasi olur. Sonuc: val mAP'i sahte yuksek cikar,
model secimi anlamsizlasir, ezberleme fark edilmez.

DOGRUSU BLOK BAZLI: ucus ardisik bloklara bolunur, her blok BUTUN HALINDE ya
train'e ya val'e gider. Ayrica blok sinirlarinda `--tampon` kadar kare ATILIR --
sinirin iki yanindaki kareler hala birbirine cok benzer.

Val bloklari ucusa YAYILIR (basta/ortada/sonda), cunku ucusun basi uzak-mesafe,
sonu yakin-mesafe. Sadece kuyrugu val yapmak, val'i tek mesafeye hapseder.

--------------------------------------------------------------------------------
 SERT BAGLANTI (hardlink)
--------------------------------------------------------------------------------
Goruntuler KOPYALANMAZ, ayni diskte sert baglanti kurulur: 11 GB aninda ve
diskte yer kaplamadan. Icerik ayni dosyadir; zip/upload normal calisir.
Farkli diskte veya baglanti kurulamazsa otomatik KOPYAYA duser.

KULLANIM
    python veriseti/paketle.py --pozitif C:\\...\\talon_pozitif \\
        --negatif C:\\...\\talon_negatif_1000 --cikti C:\\...\\talon_dataset_v1
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

from veriseti.bbox_etiketle import kare_listesi, etiketli_mi


# =============================================================================
#  Saf bolme mantigi (birim testli: tests/test_paketle.py)
# =============================================================================

def blok_ayir(n, blok_sayisi=20, val_blok=3, tampon=5, tohum=0):
    """n kareyi ardisik bloklara bol, val bloklarini ucusa YAY. -> (train, val)

    Donen listeler INDEKS listesidir. Blok sinirlarindaki `tampon` kare hicbir
    kumeye girmez (sizinti onleme).

    val bloklari esit araliklarla secilir; `tohum` ile kaydirilir ki farkli
    calistirmalarda farkli ama yine YAYILMIS bloklar secilebilsin."""
    if n <= 0:
        return [], []
    blok_sayisi = max(1, min(blok_sayisi, n))
    val_blok = max(0, min(val_blok, blok_sayisi))
    sinir = [round(i * n / blok_sayisi) for i in range(blok_sayisi + 1)]
    if val_blok == 0:
        val_set = set()
    else:
        adim = blok_sayisi / float(val_blok)
        val_set = {int((k + 0.5) * adim + tohum) % blok_sayisi for k in range(val_blok)}
    train, val = [], []
    for b in range(blok_sayisi):
        a, z = sinir[b], sinir[b + 1]
        # tampon: blogun IKI ucundan `tampon` kare at (komsu bloga benzeyenler)
        ia = a + tampon if b > 0 else a
        iz = z - tampon if b < blok_sayisi - 1 else z
        if iz <= ia:
            continue
        (val if b in val_set else train).extend(range(ia, iz))
    return train, val


def data_yaml(kok):
    return ("path: %s\ntrain: images/train\nval: images/val\n"
            "nc: 1\nnames:\n  0: talon\n" % kok.replace("\\", "/"))


# =============================================================================
#  Kopyalama
# =============================================================================

def bagla(kaynak, hedef):
    """Once SERT BAGLANTI dene (anlik, yer kaplamaz); olmazsa kopyala.
    -> 'link' | 'kopya' | 'hata'"""
    try:
        if os.path.exists(hedef):
            os.remove(hedef)
        os.link(kaynak, hedef)
        return "link"
    except Exception:
        try:
            shutil.copy2(kaynak, hedef)
            return "kopya"
        except Exception:
            return "hata"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Egitime hazir YOLO veri seti paketle")
    ap.add_argument("--pozitif", required=True)
    ap.add_argument("--negatif", default="")
    ap.add_argument("--cikti", required=True)
    ap.add_argument("--ad", default="talon1")
    ap.add_argument("--blok", type=int, default=20)
    ap.add_argument("--val-blok", type=int, default=3)
    ap.add_argument("--tampon", type=int, default=5,
                    help="blok sinirlarinda atilacak kare (sizinti onleme)")
    args = ap.parse_args(argv)

    for b in ("train", "val"):
        os.makedirs(os.path.join(args.cikti, "images", b), exist_ok=True)
        os.makedirs(os.path.join(args.cikti, "labels", b), exist_ok=True)

    print("=" * 70)
    ozet = {}
    yontem = {"link": 0, "kopya": 0, "hata": 0}

    # ---- POZITIF ----
    poz = [p for p in kare_listesi(args.pozitif, args.ad)
           if etiketli_mi(os.path.splitext(p)[0] + ".txt")]
    atlanan = len(kare_listesi(args.pozitif, args.ad)) - len(poz)
    tr, va = blok_ayir(len(poz), args.blok, args.val_blok, args.tampon)
    print("  POZITIF : %d etiketli kare  (%d ETIKETSIZ atlandi)" % (len(poz), atlanan))
    print("    blok %d, val blok %d, tampon %d -> train %d  val %d  (atilan %d)"
          % (args.blok, args.val_blok, args.tampon, len(tr), len(va),
             len(poz) - len(tr) - len(va)))
    for kume, idx in (("train", tr), ("val", va)):
        for i in idx:
            png = poz[i]
            ad = os.path.basename(png)
            yontem[bagla(png, os.path.join(args.cikti, "images", kume, ad))] += 1
            bagla(os.path.splitext(png)[0] + ".txt",
                  os.path.join(args.cikti, "labels", kume,
                               os.path.splitext(ad)[0] + ".txt"))
    ozet["pozitif"] = {"toplam": len(poz), "train": len(tr), "val": len(va),
                       "etiketsiz_atlandi": atlanan}

    # ---- NEGATIF ----
    if args.negatif:
        nim = os.path.join(args.negatif, "images")
        nlb = os.path.join(args.negatif, "labels")
        neg = sorted(os.path.join(nim, a) for a in os.listdir(nim)
                     if a.lower().endswith(".png"))
        ntr, nva = blok_ayir(len(neg), args.blok, args.val_blok, args.tampon)
        print("  NEGATIF : %d kare -> train %d  val %d" % (len(neg), len(ntr), len(nva)))
        for kume, idx in (("train", ntr), ("val", nva)):
            for i in idx:
                png = neg[i]
                ad = os.path.basename(png)
                yontem[bagla(png, os.path.join(args.cikti, "images", kume, ad))] += 1
                t = os.path.join(nlb, os.path.splitext(ad)[0] + ".txt")
                h = os.path.join(args.cikti, "labels", kume,
                                 os.path.splitext(ad)[0] + ".txt")
                if os.path.exists(t):
                    bagla(t, h)
                else:
                    open(h, "w").close()
        ozet["negatif"] = {"toplam": len(neg), "train": len(ntr), "val": len(nva)}

    with open(os.path.join(args.cikti, "data.yaml"), "w", encoding="utf-8") as f:
        f.write(data_yaml(args.cikti))

    # ---- son sayim (diskten, iddia degil) ----
    say = {}
    for b in ("train", "val"):
        im = len(os.listdir(os.path.join(args.cikti, "images", b)))
        lb = os.listdir(os.path.join(args.cikti, "labels", b))
        dolu = sum(1 for t in lb if os.path.getsize(
            os.path.join(args.cikti, "labels", b, t)) > 0)
        say[b] = {"goruntu": im, "etiket": len(lb), "pozitif": dolu,
                  "negatif": len(lb) - dolu}
    print("-" * 70)
    for b in ("train", "val"):
        s = say[b]
        print("  %-6s goruntu %5d  etiket %5d  (pozitif %5d  negatif %4d  = %%%.1f)"
              % (b, s["goruntu"], s["etiket"], s["pozitif"], s["negatif"],
                 100.0 * s["negatif"] / max(s["etiket"], 1)))
    print("  dosya: %d sert baglanti, %d kopya, %d hata"
          % (yontem["link"], yontem["kopya"], yontem["hata"]))
    ozet["sayim"] = say
    ozet["yontem"] = yontem
    with open(os.path.join(args.cikti, "paket_rapor.json"), "w", encoding="utf-8") as f:
        json.dump(ozet, f, indent=2)
    print("  -> %s" % args.cikti)
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())

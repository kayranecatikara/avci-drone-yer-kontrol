# -*- coding: utf-8 -*-
"""Etiketlenmis dagitim paketlerini talon_hepsi'ne GERI birlestirir.

KULLANIM
    python veriseti/dagitim_birlestir.py --gelen C:/.../GELEN
    python veriseti/dagitim_birlestir.py --gelen C:/.../GELEN --uygula

`--uygula` verilmezse HICBIR SEY YAZILMAZ; yalnizca ne olacagini raporlar.
Bu bilincli: 20351 etiketin ustune yazan bir islem once gorulmeli.

GELEN klasoru: her hocanin gonderdigi klasor (veya acilmis zip) yan yana.
    GELEN/
        TALON_ETIKET_01/  _esleme.json  veri/talon_0000.jpg .txt ...
        TALON_ETIKET_03/  ...

NE YAPAR
  1) `_esleme.json` ile dagitim adini (talon_0007) orijinale (talon5_3412) cevirir
  2) her etiketi BICIM ve DEGER olarak denetler (bozuk satir -> reddedilir)
  3) mevcut etiketle karsilastirir: AYNI / DEGISTI / DOLDURULDU / BOSALTILDI
  4) `veri/_silinen/` altindakileri "kare atildi" olarak raporlar
  5) --uygula ile labels/ altina atomik yazar, oncesinde YEDEK alir

SUPHELI olani yazmaz, ayri listeler:
  - kasitli negatife (dow_neg) kutu cizilmis
  - kutu cok buyuk (>%80 kadraj) veya cok kucuk (kisa kenar <4 px)
  - ayni orijinal kare iki paketten farkli etiketle donmus
"""
from __future__ import print_function

import argparse
import io
import json
import os
import shutil
import sys
import time

# dow_neg = truth projeksiyonuyla dogrulanmis kasitli negatifler. Bunlara
# kutu gelmesi kural disi degil ama SUPHELI -> otomatik yazilmaz.
KASITLI_NEGATIF = ("dow_neg",)
BUYUK_ORAN = 0.80      # kadrajin bu kadarini kaplayan kutu supheli
KUCUK_PX = 4.0         # 1920x1080 uzerinden kisa kenar alt siniri


def etiket_dogrula(metin):
    """-> (durum, temiz_metin, sebep)
    durum: 'bos' | 'ok' | 'bozuk'"""
    s = (metin or "").strip()
    if not s:
        return ("bos", "", "")
    satirlar = [x for x in s.splitlines() if x.strip()]
    ciktilar = []
    for st in satirlar:
        p = st.split()
        if len(p) != 5:
            return ("bozuk", "", "5 alan bekleniyordu, %d geldi" % len(p))
        try:
            c = int(float(p[0]))
            cx, cy, w, h = (float(x) for x in p[1:])
        except ValueError:
            return ("bozuk", "", "sayiya cevrilemedi: %r" % st)
        if c != 0:
            return ("bozuk", "", "sinif 0 olmali, %d geldi" % c)
        for ad, v in (("cx", cx), ("cy", cy), ("w", w), ("h", h)):
            if not (0.0 <= v <= 1.0):
                return ("bozuk", "", "%s araligin disinda: %.4f" % (ad, v))
        if w <= 0 or h <= 0:
            return ("bozuk", "", "sifir/negatif kutu")
        ciktilar.append("0 %.6f %.6f %.6f %.6f" % (cx, cy, w, h))
    return ("ok", "\n".join(ciktilar) + "\n", "")


def supheli_mi(orij_ad, durum, metin, W=1920.0, H=1080.0):
    """-> sebep | None"""
    if durum != "ok":
        return None
    on = orij_ad.rsplit("_", 1)[0]
    if on in KASITLI_NEGATIF:
        return "kasitli negatife kutu cizilmis"
    for st in metin.strip().splitlines():
        _, _, _, w, h = st.split()
        w, h = float(w), float(h)
        if w > BUYUK_ORAN and h > BUYUK_ORAN:
            return "kutu kadrajin %%%.0f'ini kapliyor" % (100 * max(w, h))
        if min(w * W, h * H) < KUCUK_PX:
            return "kutu kisa kenari %.1f px" % min(w * W, h * H)
    return None


def paket_oku(kok):
    """-> (paket_no, [(orijinal_ad, durum, metin, sebep)], atilanlar) | None"""
    ej = os.path.join(kok, "_esleme.json")
    if not os.path.exists(ej):
        return None
    with io.open(ej, encoding="utf-8") as f:
        veri = json.load(f)
    esleme = veri["esleme"]
    vd = os.path.join(kok, "veri")
    kayitlar = []
    for yeni, orij in sorted(esleme.items()):
        yol = os.path.join(vd, yeni + ".txt")
        if not os.path.exists(yol):
            kayitlar.append((orij, "yok", "", "gonderide .txt bulunamadi"))
            continue
        with io.open(yol, encoding="utf-8") as f:
            durum, temiz, sebep = etiket_dogrula(f.read())
        kayitlar.append((orij, durum, temiz, sebep))
    atilan = []
    sil = os.path.join(vd, "_silinen")
    if os.path.isdir(sil):
        for f in sorted(os.listdir(sil)):
            gov = os.path.splitext(f)[0]
            if gov in esleme:
                atilan.append(esleme[gov])
    return (veri.get("paket"), kayitlar, sorted(set(atilan)))


def main(argv=None):
    ap = argparse.ArgumentParser(description="dagitim paketlerini geri birlestir")
    ap.add_argument("--gelen", required=True, help="paket klasorlerinin bulundugu dizin")
    ap.add_argument("--set", default=r"C:\Users\Zeylo\Desktop\talon_hepsi",
                    help="hedef veri seti (images/ + labels/)")
    ap.add_argument("--uygula", action="store_true",
                    help="GERCEKTEN yaz (verilmezse yalniz rapor)")
    a = ap.parse_args(argv)

    lb = os.path.join(a.set, "labels")
    if not os.path.isdir(lb):
        print("HATA: labels klasoru yok: %s" % lb)
        return 1

    paketler = []
    for d in sorted(os.listdir(a.gelen)):
        p = os.path.join(a.gelen, d)
        if os.path.isdir(p):
            r = paket_oku(p)
            if r:
                paketler.append((d,) + r)
    if not paketler:
        print("HATA: %s icinde _esleme.json iceren paket yok." % a.gelen)
        return 1

    ayni = degisti = dolduruldu = bosaltildi = 0
    bozuklar, suphelier, eksikler, atilanlar = [], [], [], []
    cakisma = {}
    yazilacak = {}

    print("=" * 66)
    print("%-22s %6s %7s %8s %8s %7s" % ("paket", "kare", "DEGIS", "DOLDUR",
                                         "BOSALT", "BOZUK"))
    for ad, no, kayitlar, atilan in paketler:
        d_ = do_ = bo_ = bz_ = 0
        for orij, durum, metin, sebep in kayitlar:
            if durum == "yok":
                eksikler.append((ad, orij, sebep))
                continue
            if durum == "bozuk":
                bozuklar.append((ad, orij, sebep))
                bz_ += 1
                continue
            mevcut = ""
            my = os.path.join(lb, orij + ".txt")
            if os.path.exists(my):
                with io.open(my, encoding="utf-8") as f:
                    mevcut = f.read()
            m_var, y_var = bool(mevcut.strip()), (durum == "ok")
            sup = supheli_mi(orij, durum, metin)
            if sup:
                suphelier.append((ad, orij, sup))
                continue
            if not m_var and not y_var:
                ayni += 1
                continue
            if m_var and y_var:
                _, m_temiz, _ = etiket_dogrula(mevcut)
                if m_temiz == metin:
                    ayni += 1
                    continue
                degisti += 1
                d_ += 1
            elif y_var:
                dolduruldu += 1
                do_ += 1
            else:
                bosaltildi += 1
                bo_ += 1
            if orij in yazilacak and yazilacak[orij][1] != metin:
                cakisma.setdefault(orij, []).append(ad)
            yazilacak[orij] = (ad, metin)
        atilanlar += [(ad, o) for o in atilan]
        print("%-22s %6d %7d %8d %8d %7d"
              % (ad, len(kayitlar), d_, do_, bo_, bz_))
    print("=" * 66)
    print("AYNI %d | DEGISTI %d | DOLDURULDU %d | BOSALTILDI %d"
          % (ayni, degisti, dolduruldu, bosaltildi))
    print("yazilacak toplam: %d" % len(yazilacak))

    for baslik, liste in (("BOZUK (yazilmayacak)", bozuklar),
                          ("SUPHELI (yazilmayacak, elle bak)", suphelier),
                          ("GONDERIDE EKSIK", eksikler)):
        if liste:
            print()
            print("--- %s: %d ---" % (baslik, len(liste)))
            for x in liste[:25]:
                print("   %-22s %-24s %s" % x)
            if len(liste) > 25:
                print("   ... +%d" % (len(liste) - 25))
    if atilanlar:
        print()
        print("--- KARE ATILMIS (Shift+Delete), %d ---" % len(atilanlar))
        for ad, o in atilanlar[:25]:
            print("   %-22s %s" % (ad, o))
        if len(atilanlar) > 25:
            print("   ... +%d" % (len(atilanlar) - 25))
        print("   NOT: bunlar otomatik SILINMEZ. Bakip karar ver.")
    if cakisma:
        print()
        print("--- CAKISMA: ayni kare farkli etiketle donmus, %d ---" % len(cakisma))
        for o, ps in list(cakisma.items())[:25]:
            print("   %-24s %s" % (o, ps))

    if not a.uygula:
        print()
        print("RAPOR MODU — hicbir dosya yazilmadi.")
        print("Yazmak icin ayni komuta --uygula ekle.")
        return 0

    yedek = os.path.join(a.set, "labels_yedek_%s" % time.strftime("%Y%m%d_%H%M%S"))
    os.makedirs(yedek)
    print()
    print("yedek aliniyor -> %s" % yedek)
    for orij in yazilacak:
        k = os.path.join(lb, orij + ".txt")
        if os.path.exists(k):
            shutil.copy2(k, os.path.join(yedek, orij + ".txt"))

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from veriseti.bbox_etiketle import guvenli_yaz   # atomik + geri-oku dogrulama
    n = 0
    for orij, (paket, metin) in sorted(yazilacak.items()):
        guvenli_yaz(os.path.join(lb, orij + ".txt"), metin)
        n += 1
    print("YAZILDI: %d etiket. Yedek: %s" % (n, yedek))
    return 0


if __name__ == "__main__":
    sys.exit(main())

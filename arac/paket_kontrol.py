# -*- coding: utf-8 -*-
"""
================================================================================
GELISTIRME/DOGRULAMA ARACI — gorev ucusunda ve degerlendirme kosusunda
kullanilmaz. (Paketleme kapisi; teslim zip'inin kendisi degil.)
================================================================================
TESLIM PAKETI KONTROLU (CLAUDE.md "TESLIM PAKETI KURALI")
================================================================================
Yarismaya gidecek kod paketi = UCUS PIPELINE'i. Bu arac:
  1) Paket iceriginin dosya listesini cikarir (PAKET_KOKLERI + PAKET_DOSYALAR),
  2) Icerigi truth anahtar kelimeleri icin tarar (kod+yorum+string dahil),
  3) TEK eslesmede paketlemeyi REDDEDER (exit 1) ve eslesmeleri listeler,
  4) Temizse rapor verir; --zip ile teslim zip'ini olusturur.

ISTISNA: sdk/drone_sdk.py RESMI VERILI dosyadir; truth API'sinin orada TANIMLI
olmasi bizim kullanmamiz degildir -> taramada atlanir (raporda not edilir).
arac/, arsiv/, test/, veri/ paket DISIDIR (zaten listeye girmez).

KULLANIM:
    python arac/paket_kontrol.py            # tara + rapor
    python arac/paket_kontrol.py --zip      # temizse veri/teslim_paketi_*.zip yaz
================================================================================
"""
import argparse
import os
import sys
import time
import zipfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJ_ROOT = os.path.dirname(_HERE)

# --- Paket icerigi (teslim .zip'ine girecekler) ---
PAKET_KOKLERI = ["detection", "guidance", "fusion", "web", "sdk", "models"]
PAKET_DOSYALAR = ["main.py", "README.md", "requirements.txt"]
# Paket koklerinde bile atlanacaklar (calisma ciktisi/cop)
ATLA_UZANTI = {".pyc", ".log", ".csv", ".png", ".jpg", ".jpeg", ".zip"}
ATLA_DIZIN = {"__pycache__"}
# Taranacak metin uzantilari (model .pt gibi ikililer taranmaz, sadece listelenir)
METIN_UZANTI = {".py", ".md", ".txt", ".html", ".css", ".js", ".json", ".yaml",
                ".yml", ".cfg", ".ini", ".bat"}

# --- Truth anahtar kelimeleri (kucuk-harf karsilastirma; yorum/string dahil) ---
ANAHTARLAR = ["truth", "corruption", "get_debug_truth", "get_active_corruption",
              "telemetry_truth"]

# RESMI VERILI SDK: truth API tanimi burada; bizim kullanim sayilmaz -> tarama disi
TARAMA_ISTISNA = {os.path.join("sdk", "drone_sdk.py")}


def paket_dosyalari():
    """Teslim paketine girecek dosyalarin (goreli yol) listesi."""
    dosyalar = []
    for kok in PAKET_KOKLERI:
        kok_yol = os.path.join(_PROJ_ROOT, kok)
        if not os.path.isdir(kok_yol):
            continue
        for dizin, altlar, adlar in os.walk(kok_yol):
            altlar[:] = [a for a in altlar if a not in ATLA_DIZIN]
            for ad in adlar:
                if os.path.splitext(ad)[1].lower() in ATLA_UZANTI:
                    continue
                tam = os.path.join(dizin, ad)
                dosyalar.append(os.path.relpath(tam, _PROJ_ROOT))
    for ad in PAKET_DOSYALAR:
        if os.path.isfile(os.path.join(_PROJ_ROOT, ad)):
            dosyalar.append(ad)
    return sorted(dosyalar)


def tara(dosyalar):
    """Truth anahtar kelime taramasi -> [(dosya, satir_no, anahtar, satir_ozeti)]."""
    bulgular = []
    atlanan_istisna = []
    for gorel in dosyalar:
        if gorel.replace("/", os.sep) in TARAMA_ISTISNA:
            atlanan_istisna.append(gorel)
            continue
        if os.path.splitext(gorel)[1].lower() not in METIN_UZANTI:
            continue                                    # ikili (orn. .pt): tarama yok
        tam = os.path.join(_PROJ_ROOT, gorel)
        try:
            with open(tam, "r", encoding="utf-8", errors="replace") as f:
                for no, satir in enumerate(f, 1):
                    kucuk = satir.lower()
                    for a in ANAHTARLAR:
                        if a in kucuk:
                            bulgular.append((gorel, no, a, satir.strip()[:90]))
                            break                        # satir basina tek bulgu yeter
        except OSError as e:
            bulgular.append((gorel, 0, "OKUNAMADI", str(e)))
    return bulgular, atlanan_istisna


def zip_yaz(dosyalar):
    os.makedirs(os.path.join(_PROJ_ROOT, "veri"), exist_ok=True)
    yol = os.path.join(_PROJ_ROOT, "veri",
                       time.strftime("teslim_paketi_%Y%m%d_%H%M%S.zip"))
    with zipfile.ZipFile(yol, "w", zipfile.ZIP_DEFLATED) as z:
        for gorel in dosyalar:
            z.write(os.path.join(_PROJ_ROOT, gorel), arcname=gorel)
    return yol


def main():
    ap = argparse.ArgumentParser(description="Teslim paketi truth-temizlik kontrolu")
    ap.add_argument("--zip", action="store_true",
                    help="tarama temizse teslim zip'ini olustur (veri/ altina)")
    arg = ap.parse_args()

    dosyalar = paket_dosyalari()
    bulgular, istisna = tara(dosyalar)

    print("=" * 68)
    print(" TESLIM PAKETI KONTROLU")
    print("=" * 68)
    print(" paket icerigi   : %d dosya (%s + %s)"
          % (len(dosyalar), ", ".join(PAKET_KOKLERI), ", ".join(PAKET_DOSYALAR)))
    print(" tarama istisnasi: %s (resmi verili SDK; truth API tanimi kullanim degildir)"
          % (", ".join(istisna) if istisna else "-"))
    print(" anahtarlar      : %s" % ", ".join(ANAHTARLAR))
    if bulgular:
        print("\n [RED] %d truth izi bulundu — PAKETLEME REDDEDILDI:" % len(bulgular))
        for dosya, no, anahtar, ozet in bulgular[:50]:
            print("   %s:%d  [%s]  %s" % (dosya, no, anahtar, ozet))
        if len(bulgular) > 50:
            print("   ... (+%d bulgu daha)" % (len(bulgular) - 50))
        print("\n Kural: ucus pipeline'inda truth izi YASAK (CLAUDE.md SERT AYRIM).")
        print(" Izleri kaldir, sonra tekrar calistir.")
        sys.exit(1)

    print("\n [TEMIZ] Paket iceriginde truth izi YOK.")
    if arg.zip:
        yol = zip_yaz(dosyalar)
        print(" [ZIP] Teslim paketi yazildi: %s" % yol)
    else:
        print(" (zip olusturmak icin: python arac/paket_kontrol.py --zip)")
    sys.exit(0)


if __name__ == "__main__":
    main()

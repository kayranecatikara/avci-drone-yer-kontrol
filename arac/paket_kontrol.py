# -*- coding: utf-8 -*-
"""
================================================================================
GELISTIRME/DOGRULAMA ARACI — gorev ucusunda ve degerlendirme kosusunda
kullanilmaz. (Paketleme kapisi; teslim zip'inin kendisi degil.)
================================================================================
TESLIM PAKETI KONTROLU (CLAUDE.md "TESLIM PAKETI KURALI")
================================================================================
Yarismaya gidecek kod paketi = UCUS PIPELINE'i. Bu arac:
  1) Paket dosya listesini cikarir (PAKET_KOKLERI + PAKET_DOSYALAR);
     web/dev_truth.py PAKETE GIRMEZ (dev modul, dislanir),
  2) web/server.py ve web/index.html'deki DEV-ONLY citli bloklari paket
     kopyasindan OTOMATIK SILER (cit isaretcileri: >>> DEV-ONLY >>> ...
     <<< DEV-ONLY <<<; dengesiz cit = RED). Sokulmus server.py ayrica
     py_compile ile derlenir (soküm sozdizimi bozmasin),
  3) Kalan TUM paket icerigini anahtar kelimeler icin tarar (kod+yorum+string):
     truth / corruption / get_debug_truth / get_active_corruption /
     telemetry_truth / dev_truth / dev-only / gercek / gerçek
     TEK eslesmede paketlemeyi REDDEDER (exit 1),
  4) Temizse rapor verir; --zip ile teslim zip'ini (soküm uygulanmis haliyle)
     olusturur. GONDERILECEK VIDEO KOSUSU DA BU PAKETIN KODUNDAN YAPILIR.

ISTISNA: sdk/drone_sdk.py RESMI VERILI dosyadir; truth API'sinin orada TANIMLI
olmasi bizim kullanmamiz degildir -> taramada atlanir (raporda not edilir).
arac/, arsiv/, test/, veri/ paket DISIDIR (listeye zaten girmez).

KULLANIM:
    python arac/paket_kontrol.py            # tara + rapor
    python arac/paket_kontrol.py --zip      # temizse veri/teslim_paketi_*.zip yaz
================================================================================
"""
import argparse
import os
import py_compile
import sys
import tempfile
import time
import zipfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJ_ROOT = os.path.dirname(_HERE)

# --- Paket icerigi (teslim .zip'ine girecekler) ---
PAKET_KOKLERI = ["detection", "guidance", "fusion", "web", "sdk", "models"]
PAKET_DOSYALAR = ["main.py", "README.md", "requirements.txt"]
# Dev modul: pakete HIC girmez (madde a)
PAKET_HARIC = {os.path.join("web", "dev_truth.py")}
# Paket koklerinde bile atlanacaklar (calisma ciktisi/cop)
ATLA_UZANTI = {".pyc", ".log", ".csv", ".png", ".jpg", ".jpeg", ".zip"}
ATLA_DIZIN = {"__pycache__"}
# Taranacak metin uzantilari (model .pt gibi ikililer taranmaz, sadece listelenir)
METIN_UZANTI = {".py", ".md", ".txt", ".html", ".css", ".js", ".json", ".yaml",
                ".yml", ".cfg", ".ini", ".bat"}

# --- DEV-ONLY cit isaretcileri (satir icinde GECMESI yeterli; py ve html ayni) ---
CIT_BAS = ">>> DEV-ONLY >>>"
CIT_SON = "<<< DEV-ONLY <<<"
CITLI_DOSYALAR = {os.path.join("web", "server.py"),
                  os.path.join("web", "index.html")}

# --- Anahtar kelimeler (kucuk-harf karsilastirma; yorum/string dahil) ---
ANAHTARLAR = ["truth", "corruption", "get_debug_truth", "get_active_corruption",
              "telemetry_truth", "dev_truth", "dev-only", "gercek", "gerçek"]

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
                gorel = os.path.relpath(os.path.join(dizin, ad), _PROJ_ROOT)
                if gorel in PAKET_HARIC:
                    continue                             # dev modul pakete girmez
                dosyalar.append(gorel)
    for ad in PAKET_DOSYALAR:
        if os.path.isfile(os.path.join(_PROJ_ROOT, ad)):
            dosyalar.append(ad)
    return sorted(dosyalar)


def cit_ayikla(metin, dosya_adi):
    """DEV-ONLY citli bloklari (isaretci satirlari DAHIL) metinden cikar.
    (temiz_metin, blok_sayisi) doner; dengesiz cit -> ValueError (paket RED)."""
    out = []
    icinde = False
    n_blok = 0
    for no, satir in enumerate(metin.splitlines(), 1):
        if CIT_BAS in satir:
            if icinde:
                raise ValueError("%s:%d ic ice DEV-ONLY citi" % (dosya_adi, no))
            icinde = True
            n_blok += 1
            continue
        if CIT_SON in satir:
            if not icinde:
                raise ValueError("%s:%d acilmamis cit kapanisi" % (dosya_adi, no))
            icinde = False
            continue
        if not icinde:
            out.append(satir)
    if icinde:
        raise ValueError("%s: kapanmamis DEV-ONLY citi (dosya sonu)" % dosya_adi)
    return "\n".join(out) + "\n", n_blok


def paket_icerik(gorel):
    """Paket kopyasindaki METIN icerigi: citli dosyalarda sokulmus, digerlerinde
    oldugu gibi. (icerik, blok_sayisi|None) doner."""
    tam = os.path.join(_PROJ_ROOT, gorel)
    with open(tam, "r", encoding="utf-8", errors="replace") as f:
        metin = f.read()
    if gorel.replace("/", os.sep) in CITLI_DOSYALAR:
        return cit_ayikla(metin, gorel)
    return metin, None


def tara(dosyalar):
    """Anahtar kelime taramasi (paket KOPYASI uzerinde: citler sokulmus).
    (bulgular, istisnalar, cit_bilgi) doner."""
    bulgular = []
    atlanan_istisna = []
    cit_bilgi = {}
    for gorel in dosyalar:
        if gorel.replace("/", os.sep) in TARAMA_ISTISNA:
            atlanan_istisna.append(gorel)
            continue
        if os.path.splitext(gorel)[1].lower() not in METIN_UZANTI:
            continue                                    # ikili (orn. .pt): tarama yok
        try:
            icerik, n_blok = paket_icerik(gorel)
        except (OSError, ValueError) as e:
            bulgular.append((gorel, 0, "CIT/OKUMA HATASI", str(e)))
            continue
        if n_blok is not None:
            cit_bilgi[gorel] = n_blok
        for no, satir in enumerate(icerik.splitlines(), 1):
            kucuk = satir.lower()
            for a in ANAHTARLAR:
                if a in kucuk:
                    bulgular.append((gorel, no, a, satir.strip()[:90]))
                    break                               # satir basina tek bulgu yeter
    return bulgular, atlanan_istisna, cit_bilgi


def sokulmus_server_derlenir_mi():
    """Cit sokumu server.py sozdizimini bozmadi mi? (paket kalite kapisi)"""
    icerik, _ = paket_icerik(os.path.join("web", "server.py"))
    gecici = None
    try:
        fd, gecici = tempfile.mkstemp(suffix=".py")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(icerik)
        py_compile.compile(gecici, doraise=True)
        return True, ""
    except py_compile.PyCompileError as e:
        return False, str(e)
    finally:
        if gecici and os.path.exists(gecici):
            try:
                os.remove(gecici)
                cf = gecici + "c"
                if os.path.exists(cf):
                    os.remove(cf)
            except OSError:
                pass


def zip_yaz(dosyalar):
    os.makedirs(os.path.join(_PROJ_ROOT, "veri"), exist_ok=True)
    yol = os.path.join(_PROJ_ROOT, "veri",
                       time.strftime("teslim_paketi_%Y%m%d_%H%M%S.zip"))
    with zipfile.ZipFile(yol, "w", zipfile.ZIP_DEFLATED) as z:
        for gorel in dosyalar:
            if gorel.replace("/", os.sep) in CITLI_DOSYALAR:
                icerik, _ = paket_icerik(gorel)          # sokulmus hali paketlenir
                z.writestr(gorel.replace(os.sep, "/"), icerik.encode("utf-8"))
            else:
                z.write(os.path.join(_PROJ_ROOT, gorel),
                        arcname=gorel.replace(os.sep, "/"))
    return yol


def main():
    ap = argparse.ArgumentParser(description="Teslim paketi temizlik kontrolu")
    ap.add_argument("--zip", action="store_true",
                    help="tarama temizse teslim zip'ini olustur (veri/ altina)")
    arg = ap.parse_args()

    dosyalar = paket_dosyalari()
    bulgular, istisna, cit_bilgi = tara(dosyalar)
    derlendi, derleme_hata = sokulmus_server_derlenir_mi()

    print("=" * 68)
    print(" TESLIM PAKETI KONTROLU")
    print("=" * 68)
    print(" paket icerigi   : %d dosya (%s + %s)"
          % (len(dosyalar), ", ".join(PAKET_KOKLERI), ", ".join(PAKET_DOSYALAR)))
    print(" dislanan        : %s (dev modul; pakete girmez)"
          % ", ".join(sorted(PAKET_HARIC)))
    print(" cit sokumu      : %s"
          % ("; ".join("%s -> %d blok silindi" % kv for kv in sorted(cit_bilgi.items()))
             or "-"))
    print(" sokulmus server : %s" % ("derleniyor (py_compile OK)" if derlendi
                                     else "DERLENMIYOR! " + derleme_hata))
    print(" tarama istisnasi: %s (resmi verili SDK; API taniminin orada olmasi"
          % (", ".join(istisna) if istisna else "-"))
    print("                   bizim kullanmamiz degildir)")
    print(" anahtarlar      : %s" % ", ".join(ANAHTARLAR))

    if bulgular or not derlendi:
        if bulgular:
            print("\n [RED] %d iz bulundu — PAKETLEME REDDEDILDI:" % len(bulgular))
            for dosya, no, anahtar, ozet in bulgular[:50]:
                print("   %s:%d  [%s]  %s" % (dosya, no, anahtar, ozet))
            if len(bulgular) > 50:
                print("   ... (+%d bulgu daha)" % (len(bulgular) - 50))
        if not derlendi:
            print("\n [RED] Cit sokumu server.py'yi bozuyor — cit yerlesimini duzelt.")
        print("\n Kural: teslim paketinde dev/truth izi YASAK (CLAUDE.md).")
        sys.exit(1)

    print("\n [TEMIZ] Paket kopyasinda yasakli iz YOK; sokulmus server derleniyor.")
    if arg.zip:
        yol = zip_yaz(dosyalar)
        print(" [ZIP] Teslim paketi yazildi: %s" % yol)
        print("       GONDERILECEK VIDEO KOSUSU bu paketten cikan kodla yapilir.")
    else:
        print(" (zip olusturmak icin: python arac/paket_kontrol.py --zip)")
    sys.exit(0)


if __name__ == "__main__":
    main()

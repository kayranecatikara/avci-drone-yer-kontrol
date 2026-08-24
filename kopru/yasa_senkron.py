# -*- coding: utf-8 -*-
"""
kopru/yasa_senkron.py — GAZEBO YASASINI DALDAN BIREBIR CEK.

Kaynak: C:\\Users\\Zeylo\\Desktop\\hamidiyesim  (dal: kayramin_super_gudumu)
Hedef : kopru/gazebo_kaynak/

NE YAPAR
  1. Once mevcut hali YEDEKLER (kopru/gazebo_kaynak_ONCEKI_<zaman>/)
  2. Yasa dosyalarini dalin HEAD'inden BIREBIR kopyalar (tek satir degistirmez)
  3. Her dosyayi `git hash-object` ile DOGRULAR: bizdeki blob == HEAD blob mu?
  4. kopru/gazebo_kaynak/VERSIYON.txt yazar (commit, tarih, dosya hash'leri)

NEDEN SCRIPT: elle kopyalamada "acaba hangisi guncel" sorusu hep kaliyordu.
Bu script calistiktan sonra VERSIYON.txt kanittir.

KULLANIM
    python -m kopru.yasa_senkron            # senkronla
    python -m kopru.yasa_senkron --kontrol  # DOKUNMA, yalnizca fark raporu

⛔ YASA DOSYALARI DEGISTIRILMEZ. Ayarlar (RANGE_SET, ELEV, IC, V_MAX...) env /
setattr ile kopru katmanindan verilir — bkz. kopru/entegre.py.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time

KAYNAK_REPO = r"C:\Users\Zeylo\Desktop\hamidiyesim"
DAL = "kayramin_super_gudumu"
_HERE = os.path.dirname(os.path.abspath(__file__))
HEDEF = os.path.join(_HERE, "gazebo_kaynak")

# Dalda yol -> bizdeki yol (ikisi de repo-goreli)
DOSYALAR = [
    "control/guidance/__init__.py",
    "control/guidance/gps_guidance.py",
    "control/guidance/common.py",
    "control/guidance/guidance_core.py",
    "control/guidance/hedef_kestirim.py",
    "control/guidance/supervisor.py",
    "control/guidance/bbox_ibvs.py",
    "control/guidance/visual_lead.py",
    "control/guidance/kurtarma.py",
    "control/guidance/adapter_copter.py",
    "vision/__init__.py",
    "vision/geometry.py",
]


def git(*args, repo=KAYNAK_REPO):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True,
                          text=True, encoding="utf-8", errors="replace").stdout.strip()


def blob(yol):
    """Dosyanin git blob hash'i (satir sonu normalize edilir)."""
    return subprocess.run(["git", "-C", KAYNAK_REPO, "hash-object", yol],
                          capture_output=True, text=True).stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kontrol", action="store_true",
                    help="DOKUNMA — yalnizca fark raporu")
    a = ap.parse_args()

    if not os.path.isdir(os.path.join(KAYNAK_REPO, ".git")):
        print("[HATA] Kaynak repo yok:", KAYNAK_REPO); sys.exit(2)

    dal = git("rev-parse", "--abbrev-ref", "HEAD")
    commit = git("rev-parse", "HEAD")
    tarih = git("log", "-1", "--format=%ad", "--date=short")
    konu = git("log", "-1", "--format=%s")
    kirli = git("status", "--porcelain")
    print("KAYNAK : %s" % KAYNAK_REPO)
    print("DAL    : %s%s" % (dal, "  ⚠ BEKLENEN: " + DAL if dal != DAL else ""))
    print("HEAD   : %s  %s  %s" % (commit[:10], tarih, konu[:60]))
    if kirli:
        print("⚠ UYARI: kaynak repoda commit'lenmemis degisiklik var!")
    print()

    rapor, guncellenecek = [], []
    for f in DOSYALAR:
        kaynak = os.path.join(KAYNAK_REPO, *f.split("/"))
        hedef = os.path.join(HEDEF, *f.split("/"))
        if not os.path.isfile(kaynak):
            rapor.append((f, "KAYNAKTA YOK", None)); continue
        head_blob = git("rev-parse", "HEAD:%s" % f)
        biz_blob = blob(hedef) if os.path.isfile(hedef) else ""
        if biz_blob == head_blob:
            rapor.append((f, "zaten guncel", head_blob))
        else:
            durum = "YENI (bizde yoktu)" if not biz_blob else "GUNCELLENECEK"
            rapor.append((f, durum, head_blob))
            guncellenecek.append((f, kaynak, hedef))

    for f, durum, h in rapor:
        print("  %-42s %-20s %s" % (f, durum, (h or "")[:10]))
    print("\n%d dosya guncellenecek." % len(guncellenecek))

    if a.kontrol:
        print("(--kontrol: hicbir sey yazilmadi)"); return
    if not guncellenecek:
        print("Yapacak is yok."); return

    # 1) YEDEK
    yedek = os.path.join(_HERE, time.strftime("gazebo_kaynak_ONCEKI_%Y%m%d_%H%M%S"))
    shutil.copytree(HEDEF, yedek, ignore=shutil.ignore_patterns("__pycache__"))
    print("\nYEDEK: %s" % yedek)

    # 2) KOPYALA (birebir)
    for f, kaynak, hedef in guncellenecek:
        os.makedirs(os.path.dirname(hedef), exist_ok=True)
        shutil.copyfile(kaynak, hedef)
        print("  kopyalandi: %s" % f)

    # 3) DOGRULA
    print("\nDOGRULAMA (bizdeki blob == HEAD blob):")
    hepsi_ok = True
    satirlar = []
    for f in DOSYALAR:
        hedef = os.path.join(HEDEF, *f.split("/"))
        if not os.path.isfile(hedef):
            continue
        head_blob = git("rev-parse", "HEAD:%s" % f)
        biz = blob(hedef)
        ok = (biz == head_blob)
        hepsi_ok &= ok
        print("  %-42s %s" % (f, "BIREBIR" if ok else "!!! FARKLI"))
        satirlar.append("%s  %s" % (biz[:12], f))

    # 4) VERSIYON.txt
    with open(os.path.join(HEDEF, "VERSIYON.txt"), "w", encoding="utf-8") as fh:
        fh.write("GAZEBO YASASI — KAYNAK SURUM KAYDI\n")
        fh.write("senkron zamani : %s\n" % time.strftime("%Y-%m-%d %H:%M:%S"))
        fh.write("kaynak repo    : %s\n" % KAYNAK_REPO)
        fh.write("dal            : %s\n" % dal)
        fh.write("commit         : %s\n" % commit)
        fh.write("commit tarihi  : %s\n" % tarih)
        fh.write("commit konusu  : %s\n\n" % konu)
        fh.write("DOSYA HASH'LERI (git blob):\n")
        fh.write("\n".join("  " + s for s in satirlar) + "\n")
    print("\nVERSIYON.txt yazildi.")
    print("SONUC: %s" % ("TUM DOSYALAR DALIN HEAD'IYLE BIREBIR" if hepsi_ok
                         else "!!! BAZI DOSYALAR FARKLI — INCELE"))


if __name__ == "__main__":
    main()

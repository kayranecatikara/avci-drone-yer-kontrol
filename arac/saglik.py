# -*- coding: utf-8 -*-
"""
================================================================================
  SAGLIK  --  gozetimsiz kosarken bozulmayi YAKALA ve KAYDA GEC
================================================================================
NEDEN
--------------------------------------------------------------------------------
Kullanici yokken saatlerce olcum kosuyor. Bugun ogrenildi ki bir olcum
sessizce COP uretebilir ve fark edilmezse saatler bosa gider. En sinsi ikisi:

  1. `connected` orani duserse KOMUTLAR ARACA ULASMIYOR demektir; o pencerede
     toplanan HER sonuc gecersizdir. (Olculdu: %7.6'ya dustu, arac 900 m'ye
     tirmandi, kontrol kaybi 1-3 -> 99.)
  2. Kampanya sureci olur/cakilir ve zincir sessizce durur.

Bu betik 60 s'de bir bakar, YALNIZCA anormallik varsa yazar (sessiz saglik).
Hicbir seye mudahale ETMEZ -- tespit eder, kayda gecer. Duzeltme nobetcinin isi.

CIKTI: veri/gece/saglik.log   (temiz kosuda neredeyse bos kalir)
================================================================================
"""
import io
import os
import sys
import json
import time
import argparse
import subprocess
import urllib.request

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(KOK, "veri", "gece", "saglik.log")


def _yaz(m):
    s = "[SAGLIK] %s %s" % (time.strftime("%H:%M:%S"), m)
    try:
        print(s, flush=True)
    except UnicodeEncodeError:
        print(s.encode("ascii", "replace").decode("ascii"), flush=True)
    try:
        with io.open(LOG, "a", encoding="utf-8") as f:
            f.write(s + "\n")
    except OSError:
        pass


def _tel(zaman=3.0):
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000/api/telemetry",
                                    timeout=zaman) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


def _baglanti_orani(n=12, arali=0.5):
    """⚠ SDK portuna DOKUNMAZ -- yalniz HTTP telemetri."""
    ok = top = 0
    for _ in range(n):
        t = _tel()
        if t is not None:
            top += 1
            if t.get("connected"):
                ok += 1
        time.sleep(arali)
    return (ok / top) if top else None


def _surecler():
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
         "Select-Object ProcessId,@{n='c';e={$_.CommandLine}} | ConvertTo-Json -Compress"],
        capture_output=True, text=True, timeout=60)
    try:
        d = json.loads(r.stdout or "[]")
        return d if isinstance(d, list) else [d]
    except Exception:
        return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--periyot", type=float, default=60.0)
    ap.add_argument("--esik", type=float, default=0.85,
                    help="baglanti orani bunun altina duserse UYAR")
    a = ap.parse_args()
    _yaz("=" * 56)
    _yaz("basladi | %.0f s periyot | baglanti esigi %%%.0f"
         % (a.periyot, 100 * a.esik))

    onceki_kampanya = None
    kotu_ust_uste = 0
    son_sira = None
    while True:
        S = _surecler()
        kampanya = next((x for x in S if "kampanya.py" in (x.get("c") or "")), None)
        sira = any("sira.py" in (x.get("c") or "") for x in S)
        nobetci = any("nobetci.py" in (x.get("c") or "") for x in S)

        if not nobetci:
            _yaz("⚠ NOBETCI YOK -- oyun dusunce toparlayan kimse kalmadi")
        # ⚠ 2026-08-17: kare kaydi bir temizlik sirasinda kapatildi ve 9.5 SAAT
        #   fark edilmedi ("her saniye kayit aliyorum" dedigim halde alinmiyordu).
        #   Sessizce olmesine bir daha izin verme.
        kamera = any("ucus_kamera_kaydi" in (x.get("c") or "") for x in S)
        if not kamera:
            _yaz("⚠ KARE KAYDI YOK -- 'her saniye kare+komut' toplanmiyor "
                 "(baslat: python arac/ucus_kamera_kaydi.py --hz 1)")
        if son_sira is None:
            son_sira = sira
        elif son_sira and not sira:
            _yaz("★ SIRA BITTI (zincirdeki tum receteler kosuldu)")
            son_sira = sira
        if kampanya and onceki_kampanya and \
                kampanya["ProcessId"] != onceki_kampanya:
            _yaz("kampanya degisti -> pid %s" % kampanya["ProcessId"])
        if not kampanya and sira:
            pass                      # receteler arasi gecis, normal
        onceki_kampanya = kampanya["ProcessId"] if kampanya else onceki_kampanya

        if kampanya:                  # yalniz olcum kosarken baglanti onemli
            k = _baglanti_orani()
            if k is None:
                _yaz("⚠ sunucu telemetrisi CEVAPSIZ")
            elif k < a.esik:
                kotu_ust_uste += 1
                _yaz("⚠⚠ BAGLANTI %%%.0f (esik %%%.0f) -- bu penceredeki OLCUM "
                     "SUPHELI, %d. kez" % (100 * k, 100 * a.esik, kotu_ust_uste))
                if kotu_ust_uste >= 3:
                    _yaz("★ UC KEZ UST USTE -- oyun yipranmis olabilir; "
                         "nobetcinin tam yeniden baslatmasi beklenmeli")
            else:
                kotu_ust_uste = 0
        time.sleep(a.periyot)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        _yaz("durduruldu")

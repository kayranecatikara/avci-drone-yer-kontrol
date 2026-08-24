# -*- coding: utf-8 -*-
"""
================================================================================
  SIRA  --  receteleri ARDI ARDINA kosar (gozetimsiz calisma icin)
================================================================================
NEDEN
--------------------------------------------------------------------------------
gozcu_devret tek bir devir yapiyor. Kullanici yokken saatlerce surecek bir
deney zinciri gerekiyor. Bu betik:
  1. Kosan kampanya varsa BITMESINI bekler (asla oldurmez),
  2. Verilen receteleri sirayla kosar,
  3. Her recetenin sonunda hukum betigini calistirir (varsa),
  4. Her adimi veri/gece/sira.log'a yazar.

⚠ OYUNA/SUNUCUYA DOKUNMAZ. Nobetci zaten ayri calisiyor ve oyunu ayakta
   tutuyor; bu betik yalnizca kampanya sureclerini sirayla baslatir.

CALISTIR
    python arac/sira.py recete_algi.json recete_kilit.json
    python arac/sira.py --dk 14 recete_algi.json
================================================================================
"""
import io
import os
import sys
import time
import json
import argparse
import subprocess

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(KOK, "veri", "gece", "sira.log")


def _log(m):
    s = "[SIRA] %s %s" % (time.strftime("%H:%M:%S"), m)
    try:
        print(s, flush=True)
    except UnicodeEncodeError:
        print(s.encode("ascii", "replace").decode("ascii"), flush=True)
    try:
        with io.open(LOG, "a", encoding="utf-8") as f:
            f.write(s + "\n")
    except OSError:
        pass


def kampanya_kosuyor():
    """Baska bir kampanya.py ayakta mi?  (bizim baslattigimiz haric)"""
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
         "Select-Object ProcessId,@{n='c';e={$_.CommandLine}} | ConvertTo-Json -Compress"],
        capture_output=True, text=True, timeout=60)
    try:
        d = json.loads(r.stdout or "[]")
        d = d if isinstance(d, list) else [d]
    except Exception:
        return False
    return any("kampanya.py" in (x.get("c") or "") for x in d)


def hukum_calistir(recete_adi):
    """Recetenin kendi hukum betigi varsa kosar (yorumsuz sonuc)."""
    esle = {"recete_gecis": "gecis_hukum.py", "recete_dogrulama": "gecis_hukum.py",
            "recete_tekrar": "tekrar_hukum.py", "recete_kilit": "kilit_denetim.py",
            "recete_algi": "algi_sureklilik.py"}
    kok_ad = os.path.splitext(os.path.basename(recete_adi))[0]
    bet = esle.get(kok_ad)
    if not bet:
        return
    yol = os.path.join(KOK, "arac", bet)
    if not os.path.exists(yol):
        _log("  hukum betigi yok: %s" % bet)
        return
    _log("  hukum: %s" % bet)
    ort = dict(os.environ)
    ort["PYTHONIOENCODING"] = "utf-8"
    ort["PYTHONUTF8"] = "1"
    try:
        r = subprocess.run([sys.executable, "-u", yol], cwd=KOK, env=ort,
                           capture_output=True, text=True, timeout=600)
        for satir in (r.stdout or "").splitlines():
            _log("   | " + satir)
    except Exception as e:
        _log("  hukum hatasi: %r" % (e,))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("receteler", nargs="+")
    ap.add_argument("--dk", type=float, default=14.0)
    ap.add_argument("--tur", type=int, default=1)
    ap.add_argument("--bekle-dk", type=float, default=240.0,
                    help="kosan kampanya icin en fazla bu kadar bekle")
    a = ap.parse_args()

    _log("=" * 60)
    _log("sira basladi: %s" % ", ".join(a.receteler))

    t0 = time.time()
    while kampanya_kosuyor() and time.time() - t0 < a.bekle_dk * 60:
        time.sleep(30)
    if kampanya_kosuyor():
        _log("⚠ kosan kampanya %.0f dk'da bitmedi -- yine de basliyorum" % a.bekle_dk)

    ort = dict(os.environ)
    ort["PYTHONIOENCODING"] = "utf-8"
    ort["PYTHONUTF8"] = "1"

    for r in a.receteler:
        yol = r if os.path.isabs(r) else os.path.join("arac", os.path.basename(r))
        tam = os.path.join(KOK, yol)
        if not os.path.exists(tam):
            _log("✗ recete yok, atlaniyor: %s" % yol)
            continue
        try:
            n = len(json.load(io.open(tam, encoding="utf-8")))
        except Exception:
            n = -1
        _log("▶ %s  (%d kol x %.0f dk x %d tur)" % (yol, n, a.dk, a.tur))
        p = subprocess.Popen([sys.executable, "-u", "arac/kampanya.py",
                              "--recete", yol, "--dk", str(a.dk),
                              "--tur", str(a.tur)], cwd=KOK, env=ort)
        _log("  pid %d" % p.pid)
        p.wait()
        _log("✓ bitti (cikis %s)" % p.returncode)
        time.sleep(20)
        hukum_calistir(yol)

    _log("SIRA TAMAMLANDI")


if __name__ == "__main__":
    main()

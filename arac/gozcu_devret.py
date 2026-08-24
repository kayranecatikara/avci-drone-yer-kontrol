# -*- coding: utf-8 -*-
"""Kosan kampanyanin SIRADAKI AYAR SINIRINDA temiz devralinmasi.

NEDEN: recete_ayna.json --tur 99 ile sonsuz donuyor. Ayna sonucu artik
olculdu; sirada (a) vurusun TEKRARLANABILIR oldugunu kanitlamak,
(b) dikey ivme butcesi yamasini tek degiskenli sinamak var.

Ayarin ORTASINDA oldurmek o ayarin olcumunu yarida birakir; bu gozcu
"SONUC <ayar>" satirini bekler -> ayar sinirinda devralir.
"""
import io
import os
import re
import sys
import time
import subprocess

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(KOK, "veri", "gece", "kampanya.log")
BEKLENEN = sys.argv[1] if len(sys.argv) > 1 else "C_ayna"
PID = int(sys.argv[2]) if len(sys.argv) > 2 else 0
RECETE = sys.argv[3] if len(sys.argv) > 3 else "arac/recete_tekrar.json"
TUR = int(sys.argv[4]) if len(sys.argv) > 4 else 1     # varsayilan 1 tur
SONRAKI = sys.argv[5] if len(sys.argv) > 5 else ""     # zincir: bitince bunu baslat


def _log(m):
    print("[gozcu] %s %s" % (time.strftime("%H:%M:%S"), m), flush=True)


def _bitti():
    try:
        t = io.open(LOG, encoding="utf-8", errors="replace").read()
    except OSError:
        return False
    return re.search(r"SONUC\s+%s" % re.escape(BEKLENEN), t) is not None


def _ayakta(pid):
    if not pid:
        return False
    r = subprocess.run(["powershell", "-NoProfile", "-Command",
                        "(Get-Process -Id %d -ErrorAction SilentlyContinue) -ne $null" % pid],
                       capture_output=True, text=True)
    return "True" in r.stdout


_log("bekleniyor: '%s' ayarinin SONUC satiri (pid %d)" % (BEKLENEN, PID))
t0 = time.time()
while time.time() - t0 < 3 * 3600:
    if _bitti():
        _log("ayar sinirina gelindi -> devralinyor")
        break
    if PID and not _ayakta(PID):
        _log("kampanya sureci zaten bitmis -> devralinyor")
        break
    time.sleep(15)
else:
    _log("3 saat doldu, yine de devraliniyor")

if PID and _ayakta(PID):
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    "Stop-Process -Id %d -Force" % PID], capture_output=True)
    _log("eski kampanya durduruldu (pid %d)" % PID)
    time.sleep(20)          # sunucu/oyun otursun

_log("YENI KAMPANYA: %s" % RECETE)
# ⚠ 2026-08-17: ortam VERILMEDIGI icin alt surec cp1252'ye dustu ve
#   kampanya ilk "★" satirinda UnicodeEncodeError ile oldu. UTF-8 SART.
_ort = dict(os.environ)
_ort["PYTHONIOENCODING"] = "utf-8"
_ort["PYTHONUTF8"] = "1"
p = subprocess.Popen([sys.executable, "-u", "arac/kampanya.py",
                      "--recete", RECETE, "--dk", "14", "--tur", str(TUR)],
                     cwd=KOK, env=_ort)
_log("baslatildi, pid %d" % p.pid)
p.wait()
_log("kampanya bitti (cikis %s)" % p.returncode)

# ── zincir: sirada baska bir recete varsa onu baslat ──────────────────
if SONRAKI:
    _log("ZINCIR -> %s" % SONRAKI)
    time.sleep(20)
    q = subprocess.Popen([sys.executable, "-u", "arac/kampanya.py",
                          "--recete", SONRAKI, "--dk", "14", "--tur", "1"],
                         cwd=KOK, env=_ort)
    _log("baslatildi, pid %d" % q.pid)
    q.wait()
    _log("zincir kampanyasi bitti (cikis %s)" % q.returncode)

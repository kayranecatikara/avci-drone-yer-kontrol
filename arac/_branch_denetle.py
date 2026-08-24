# -*- coding: utf-8 -*-
"""Branch'e girecek dosyalarin import zincirini denetler.

Amac: arkadasin `git checkout model-fps` yaptiginda ImportError almamasi.
Calisan sistemin import agacini gezip, branch'te OLMAYAN modulleri listeler.
"""
import ast
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def git(*a):
    return subprocess.run(["git"] + list(a), capture_output=True, text=True).stdout.split()


takipli = set(git("ls-files"))
hazir = set(git("diff", "--cached", "--name-only"))
silinen = set(git("diff", "--cached", "--name-only", "--diff-filter=D"))
mevcut = (takipli | hazir) - silinen


def modul_yolu(m):
    p = m.replace(".", "/")
    for c in (p + ".py", p + "/__init__.py"):
        if os.path.exists(c):
            return c.replace(os.sep, "/")
    return None


HEDEF = ["main.py", "web/server.py", "guidance/ana_kontrol.py",
         "detection/gorsel_tespit.py", "arac/motor_kur.py",
         "arac/kurulum_kontrol.py", "arac/fps_teshis.py", "config.py"]

eksik = {}
gorulen = set()
yigin = list(HEDEF)
while yigin:
    f = yigin.pop()
    if f in gorulen or not os.path.exists(f):
        continue
    gorulen.add(f)
    try:
        t = ast.parse(open(f, encoding="utf-8", errors="replace").read())
    except Exception:
        continue
    for n in ast.walk(t):
        mods = []
        if isinstance(n, ast.Import):
            mods = [a.name for a in n.names]
        elif isinstance(n, ast.ImportFrom) and n.module and n.level == 0:
            mods = [n.module]
        for m in mods:
            y = modul_yolu(m)
            if y:
                if y not in mevcut:
                    eksik.setdefault(y, set()).add(f)
                yigin.append(y)

print("  taranan dosya : %d" % len(gorulen))
if eksik:
    print("  ⛔ BRANCH'TE OLMAYAN AMA GEREKLI %d MODUL:" % len(eksik))
    for y, kim in sorted(eksik.items()):
        print("     %-40s <- %s" % (y, ", ".join(sorted(kim))[:44]))
else:
    print("  ✔ butun import zinciri branch'te mevcut")

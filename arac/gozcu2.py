# -*- coding: utf-8 -*-
"""
================================================================================
  GOZCU2  --  sistemi AYAKTA ve UCUYOR tutar
================================================================================
NEDEN (2026-08-18, bir gunluk kayip zamanin sebebi)
--------------------------------------------------------------------------------
Mevcut `nobetci.py` yalniz TEK durumu izliyor: "SDK portu kapandi ->
MISSION COMPLETED -> PLAY AGAIN + E". Bugun olculen UC BASKA arizada
sessizce bekledi ve saatlerce cop veri toplandi:

  1. SUNUCU OLDU (main.py cikti) -> telemetri ucu yok, hicbir sey kosmuyor.
  2. DRONE DISARMED -> oyun acik, port acik, "GOREVDE" gorunuyor ama arac
     YERDE duruyor (hiz 0.0, ALT 0 m, ekranda DISARMED). Nobetci bunu
     "gorevde" sayiyor. Ekran goruntusuyle dogrulandi.
  3. TELEMETRI DONDU -> oyun sureci coktugunde sunucu SON degerleri
     yazmaya devam ediyor; satirlar gecerli gorunuyor ama degismiyor
     (olculdu: bir kosunun %27.9'u, en uzun donma 235 s).

Bu betik ucunu de kapatir. `nobetci.py` ile BIRLIKTE calisir (o PLAY AGAIN
dizisini biliyor); gozcu2 onu tamamlar, yerine gecmez.

⚠ TASARIM KURALI: SDK portuna (12345) ASLA dokunma. 2026-08-17'de bir
  nobetci surumu 0.4 s'de bir o porta baglanip `connected`i %7.6'ya
  dusurdu, komutlar araca ulasmadi, arac 900 m'ye tirmandi. Yalniz HTTP
  telemetrisi okunur.

KULLANIM
    python arac/gozcu2.py                 # varsayilan: kaynak v2 (yarisma)
    python arac/gozcu2.py --kaynak gercek # teshis modu
    python arac/gozcu2.py --sessiz
================================================================================
"""
import os
import sys
import json
import time
import math
import argparse
import subprocess
import urllib.request

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)

TEL = "http://127.0.0.1:8000/api/telemetry"
KOMUT = "http://127.0.0.1:8000/api/command"
LOG = os.path.join(KOK, "veri", "gece", "gozcu2.log")


def _log(m):
    s = "[GOZCU2] %s %s" % (time.strftime("%H:%M:%S"), m)
    try:
        print(s, flush=True)
    except Exception:
        pass
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(s + "\n")
    except Exception:
        pass


def tel(zaman=3.0):
    try:
        return json.loads(urllib.request.urlopen(TEL, timeout=zaman).read())
    except Exception:
        return None


def komut(c):
    try:
        d = json.dumps({"cmd": c}).encode()
        r = urllib.request.Request(KOMUT, data=d,
                                   headers={"Content-Type": "application/json"})
        return json.loads(urllib.request.urlopen(r, timeout=8).read())
    except Exception as e:
        return {"ok": False, "hata": repr(e)[:80]}


def sunucu_ayakta():
    return tel(2.0) is not None


def sunucu_baslat():
    """main.py'yi arka planda baslat. Cift ornek RISKI: once port kontrolu."""
    if sunucu_ayakta():
        return True
    _log("sunucu YOK -> baslatiliyor")
    ev = dict(os.environ)
    ev["PYTHONIOENCODING"] = "utf-8"
    # ⚠ Sunucu ciktisi DOSYAYA yazilir: kopru [PK] tani satirlarini
    #   (periyodik kestirici mekanizma kapisi) oradan okuyoruz. DEVNULL
    #   yapilirsa kapinin calisip calismadigi DOGRULANAMAZ.
    slog = os.path.join(KOK, "veri", "gece", "sunucu_gozcu2.log")
    try:
        os.makedirs(os.path.dirname(slog), exist_ok=True)
        sf = open(slog, "a", encoding="utf-8", errors="replace")
        sf.write("\n===== %s sunucu baslatildi =====\n"
                 % time.strftime("%H:%M:%S"))
        sf.flush()
    except Exception:
        sf = subprocess.DEVNULL
    try:
        subprocess.Popen([sys.executable, "-u", "main.py"], cwd=KOK, env=ev,
                         stdout=sf, stderr=subprocess.STDOUT,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except Exception as e:
        _log("sunucu baslatilamadi: %r" % e)
        return False
    for _ in range(30):
        time.sleep(2)
        if sunucu_ayakta():
            _log("sunucu ayakta")
            return True
    _log("sunucu 60 s'de acilmadi")
    return False


def oyun_ayakta():
    try:
        from arac import oyun_kurtar as OK
        return OK.oyun_calisiyor()
    except Exception:
        return True          # bilemiyorsak karar verme


def oyun_baslat():
    try:
        from arac import oyun_kurtar as OK
        _log("oyun sureci YOK -> aciliyor")
        OK.oyunu_baslat()
        for _ in range(40):
            time.sleep(3)
            if OK.oyun_calisiyor():
                _log("oyun ayakta")
                return True
    except Exception as e:
        _log("oyun acilamadi: %r" % e)
    return False


def gorev_dogur():
    """PLAY AGAIN + E dizisi (nobetci'nin kanitlanmis yolu)."""
    try:
        from arac import nobetci as NB
        return bool(NB.yeniden_baslat(gorsel_kayit=False))
    except Exception as e:
        _log("gorev dogurma hatasi: %r" % e)
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kaynak", default="v2", choices=["v2", "gercek"],
                    help="v2 = Inovasyonlu J (YARISMA) | gercek = filtresiz (teshis)")
    ap.add_argument("--periyot", type=float, default=2.0)
    ap.add_argument("--durgun-s", type=float, default=25.0,
                    help="bu kadar sure hiz ~0 ise gorev yeniden baslatilir")
    ap.add_argument("--donuk-s", type=float, default=20.0,
                    help="telemetri bu kadar sure DEGISMEZSE cokme sayilir")
    a = ap.parse_args()
    baslat_cmd = "start" if a.kaynak == "v2" else "start_gercek"

    _log("=" * 56)
    _log("basladi | kaynak %s (%s)" % (a.kaynak, baslat_cmd))
    _log("izlenen: sunucu olumu · drone DISARMED/durgun · telemetri donmasi")

    durgun_t0 = None
    donuk_t0 = None
    son_imza = None
    son_mudahale = 0.0

    while True:
        time.sleep(a.periyot)
        d = tel()

        # ── 1) SUNUCU OLDU MU ────────────────────────────────────────────
        if d is None:
            if not oyun_ayakta():
                oyun_baslat()
            if sunucu_baslat():
                time.sleep(6)
                if time.time() - son_mudahale > 30:
                    son_mudahale = time.time()
                    _log("sunucu geldi -> gorev baslatiliyor")
                    _log("  %s" % komut(baslat_cmd).get("msg", "?"))
            continue

        dr = d.get("drone") or {}
        hiz = float(dr.get("speed_ms") or 0.0)
        aktif = bool(d.get("gorev_aktif"))
        kaynak = d.get("kaynak")

        # ── 2) TELEMETRI DONDU MU ───────────────────────────────────────
        imza = (round(dr.get("x", 0), 2), round(dr.get("y", 0), 2),
                round((d.get("target") or {}).get("x", 0), 2))
        simdi = time.time()
        if imza == son_imza:
            if donuk_t0 is None:
                donuk_t0 = simdi
            elif simdi - donuk_t0 > a.donuk_s and simdi - son_mudahale > 45:
                son_mudahale = simdi
                _log("TELEMETRI %ds DONDU -> oyun/gorev yeniden" % a.donuk_s)
                if not oyun_ayakta():
                    oyun_baslat()
                gorev_dogur()
                _log("  %s" % komut(baslat_cmd).get("msg", "?"))
                donuk_t0 = None
                durgun_t0 = None
        else:
            donuk_t0 = None
        son_imza = imza

        # ── 3) GOREV KAPALI ya da DRONE DURGUN (DISARMED) ───────────────
        if not aktif:
            if simdi - son_mudahale > 20:
                son_mudahale = simdi
                _log("gorev_aktif=False -> baslatiliyor (%s)" % baslat_cmd)
                _log("  %s" % komut(baslat_cmd).get("msg", "?"))
            durgun_t0 = None
            continue

        if kaynak and kaynak != a.kaynak and simdi - son_mudahale > 20:
            son_mudahale = simdi
            _log("kaynak '%s' beklenen '%s' DEGIL -> duzeltiliyor"
                 % (kaynak, a.kaynak))
            _log("  %s" % komut(baslat_cmd).get("msg", "?"))
            continue

        if hiz < 1.0:
            if durgun_t0 is None:
                durgun_t0 = simdi
            elif simdi - durgun_t0 > a.durgun_s and simdi - son_mudahale > 45:
                son_mudahale = simdi
                _log("drone %ds DURGUN (hiz %.2f) -> DISARMED olabilir, "
                     "gorev yeniden dogruluyor" % (a.durgun_s, hiz))
                if not oyun_ayakta():
                    oyun_baslat()
                gorev_dogur()
                _log("  %s" % komut(baslat_cmd).get("msg", "?"))
                durgun_t0 = None
        else:
            durgun_t0 = None


if __name__ == "__main__":
    main()

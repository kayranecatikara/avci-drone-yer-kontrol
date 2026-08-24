# -*- coding: utf-8 -*-
"""
================================================================================
  NOBETCI  --  gorev biter bitmez ANINDA yeniden baslat
================================================================================
NEDEN
--------------------------------------------------------------------------------
Gorev "MISSION COMPLETED" ile bitince SDK portu (12345) kapanir ve sistem
olcum yapamaz hale gelir. Kampanyanin kendi kurtarmasi ancak ayar sinirinda
ya da uzun beklemelerden sonra devreye giriyordu -> dakikalarca olu zaman.
Bu nobetci portu 0.4 s'de bir yoklar ve kapanir kapanmaz basar.

ALGILAMA (memory'den, olculdu)
    port 12345 KAPALI  +  oyun sureci AYAKTA   =  gorevden dustu
    (surec olseydi RAM/pencere de giderdi -> o zaman tam acilis gerekir)

BASILAN DIZI (kullanicinin tarif ettigi)
    PLAY AGAIN tik (%78.6,%84.5)  ->  ~6 s loading  ->  E (x4, 2.5 s arayla)

⚠ GUVENLIK
    - Pencere ONE GELMEZSE hicbir tus/tik gonderilmez (yanlis pencereye
      tus gitmesi daha once yasandi -- kullanicinin VS Code terminaline).
    - ALT/F4/Win/Ctrl asla gonderilmez.
    - Ust uste basarisiz olursa tam acilis dizisine duser, sonra bekler.

CALISTIR
    python arac/nobetci.py                  # sinirsiz
    python arac/nobetci.py --periyot 0.4
================================================================================
"""
import os
import sys
import time
import argparse
import json
import subprocess

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)

from arac import oyun_kurtar as OK      # noqa: E402

CIK = os.path.join(KOK, "veri", "gece")


def _log(m):
    s = "[NOBETCI] %s %s" % (time.strftime("%H:%M:%S"), m)
    try:
        print(s, flush=True)
    except UnicodeEncodeError:
        print(s.encode("ascii", "replace").decode("ascii"), flush=True)
    try:
        with open(os.path.join(CIK, "nobetci.log"), "a", encoding="utf-8") as f:
            f.write(s + "\n")
    except OSError:
        pass


def yeniden_baslat(gorsel_kayit=True):
    """PLAY AGAIN -> loading -> E.  Basari: port acildi."""
    h = OK.oyun_penceresi()
    if not h:
        _log("oyun penceresi YOK -> tam acilis gerekiyor")
        return OK.oyunu_ac_ve_goreve_sok(_log)
    if gorsel_kayit:
        try:
            OK.ekran_goruntusu(os.path.join(
                CIK, "nobetci_%s.png" % time.strftime("%Y%m%d_%H%M%S")))
        except Exception:
            pass
    if not OK.one_al(h):
        _log("pencere ONE GELMEDI -> tus GONDERILMEDI (guvenlik)")
        return False
    _log("PLAY AGAIN (%%%.0f,%%%.0f)" % (OK.TEKRAR_OYNA_TIK[0] * 100,
                                         OK.TEKRAR_OYNA_TIK[1] * 100))
    OK._tikla_oran(*OK.TEKRAR_OYNA_TIK)
    time.sleep(getattr(OK, "YUKLEME_BEKLE_S", 6.0))
    for i in range(4):
        if not OK.one_al(h):
            _log("odak kayboldu -> DUR")
            return False
        OK.tus_bas("e")
        time.sleep(2.5)
        if gorevde_mi():                # HTTP -- SDK soketine dokunmaz
            _log("✓ GOREVDE (PLAY AGAIN + E x%d)" % (i + 1))
            return True
    _log("PLAY AGAIN + E tutmadi -> tam acilis dizisi")
    return OK.oyunu_ac_ve_goreve_sok(_log)


def gorevde_mi():
    """Gorevde miyiz? -- ⚠ SDK PORTUNA DOKUNMADAN.

    ★★ 2026-08-17 KOK NEDEN (benim kendi hatam):
      Ilk surum `OK.port_acik()` ile 12345'e 0.4 s'de bir TCP baglantisi
      acip kapatiyordu = dakikada ~150 baglanti. O port TEK ISTEMCILIK ve
      sunucumuz oradan KOMUT gonderiyor. Nobetci surekli araya girince
      baglanti dustu:
          nobetci KAPALI, temiz oyun -> connected %100.0, 0 kopma
          nobetci ACIK               -> connected %7.6, 72 s'de 21 kopma
      Sonucu: komutlar araca ulasmadi, arac 900 m'ye tirmandi, 2752 °/s
      takla atti, kontrol kaybi 1-3 -> 99. Saatlerce "gudum bozuldu" diye
      arandi; gudum SUCSUZDU, nobetci yokluyordu.

    Dogru yol: sunucunun HTTP telemetrisini oku. SDK soketine dokunmaz.
    """
    import urllib.request
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000/api/telemetry",
                                    timeout=3) as r:
            t = json.loads(r.read().decode())
    except Exception:
        return None                     # sunucu yok -> karar verme
    if t.get("connected"):
        return True
    d = t.get("drone") or {}
    return None if d.get("x") is None else False


def _baglanti_kalitesi(n=16, arali=0.5):
    """Sunucunun oyuna baglantisinin ne kadarinin AYAKTA oldugu (0..1).

    ⚠ 2026-08-17 OLCULDU -- gunun en onemli operasyonel dersi:
      Gorev yeniden baslatmalari (PLAY AGAIN) OYUNU YIPRATIYOR. Onlarca
      tekrardan sonra SDK sunucusu bozuldu:
          connected orani %7.6, 72 s'de 21 kez kopma
          gaz komutu <-> dikey hiz korelasyonu -0.03 (yani komut ULASMIYOR)
          arac kendi basina tirmaniyor/donuyor, gudum sucsuz
      OYUNU KOMPLE KAPATIP ACINCA:  connected %100.0, 0 kopma.
      Yani "PLAY AGAIN" sonsuza kadar yetmiyor; belirli araliklarla TAM
      yeniden baslatma sart.
    """
    import urllib.request
    ok = 0
    top = 0
    for _ in range(n):
        try:
            with urllib.request.urlopen("http://127.0.0.1:8000/api/telemetry",
                                        timeout=3) as r:
                t = json.loads(r.read().decode())
            top += 1
            if t.get("connected"):
                ok += 1
        except Exception:
            pass
        time.sleep(arali)
    return (ok / top) if top else None


def tam_yeniden_baslat():
    """Oyunu KAPAT, soketler temizlensin diye bekle, sifirdan ac."""
    _log("★ TAM YENIDEN BASLATMA (baglanti kalitesi dustu)")
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    "Get-Process | Where-Object { $_.ProcessName -match "
                    "'DronesOfWar' } | Stop-Process -Force"],
                   capture_output=True)
    time.sleep(30)                     # TimeWait soketleri temizlensin
    return OK.oyunu_ac_ve_goreve_sok(_log, toplam_s=300.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--periyot", type=float, default=1.0)
    ap.add_argument("--kalite-esik", type=float, default=0.6,
                    help="baglanti bu oranin altina duserse TAM yeniden baslat")
    ap.add_argument("--kalite-periyot", type=float, default=180.0,
                    help="kac saniyede bir baglanti kalitesi olculsun")
    ap.add_argument("--tam-her", type=int, default=10,
                    help="kac PLAY AGAIN'den sonra proaktif TAM yeniden baslat")
    ap.add_argument("--onay", type=int, default=3,
                    help="kac ardisik KAPALI okumadan sonra tetiklensin")
    a = ap.parse_args()

    _log("=" * 60)
    _log("basladi | periyot %.1f s | onay %d ardisik kapali okuma"
         % (a.periyot, a.onay))
    _log("algi: port 12345 KAPALI + oyun sureci AYAKTA -> gorevden dustu")

    kapali = 0
    son_tetik = 0.0
    son_kalite = time.time()
    tekrar_sayaci = 0
    onceki_acik = bool(gorevde_mi())
    _log("baslangic: port %s" % ("ACIK" if onceki_acik else "KAPALI"))

    bilinmez = 0
    while True:
        _d = gorevde_mi()               # ⚠ SDK portuna DOKUNMAZ
        if _d is None:                  # sunucu yok/cevapsiz -> karar verme
            bilinmez += 1
            if bilinmez % 30 == 1:
                _log("sunucu telemetrisi yok -> beklemede (karar verilmiyor)")
            time.sleep(2.0)
            continue
        bilinmez = 0
        acik = bool(_d)

        if acik:
            if kapali:
                _log("port geri geldi (tetiklemeden)")
            kapali = 0
            onceki_acik = True
            # ── BAGLANTI KALITESI DENETIMI (periyodik) ──────────────────
            if time.time() - son_kalite > a.kalite_periyot:
                son_kalite = time.time()
                k = _baglanti_kalitesi()
                if k is not None:
                    _log("baglanti kalitesi %%%.0f" % (100 * k))
                    if k < a.kalite_esik:
                        _log("esik %%%.0f altinda -> oyun yipranmis"
                             % (100 * a.kalite_esik))
                        tam_yeniden_baslat()
                        tekrar_sayaci = 0
                        son_kalite = time.time()
            time.sleep(a.periyot)
            continue

        kapali += 1
        if kapali < a.onay:
            time.sleep(a.periyot)
            continue

        # ── gerçekten düştü ────────────────────────────────────────────
        if time.time() - son_tetik < 25:      # arka arkaya tetiklenmesin
            time.sleep(1.0)
            continue
        if not OK.oyun_calisiyor():
            _log("oyun sureci de YOK -> tam acilis")
            son_tetik = time.time()
            yeniden_baslat(gorsel_kayit=False)
            kapali = 0
            continue

        gecen = "" if onceki_acik else " (baslangictan beri kapali)"
        _log("★ GOREV BITTI algilandi%s -> ANINDA yeniden baslat" % gecen)
        son_tetik = time.time()
        t0 = time.time()
        tekrar_sayaci += 1
        if a.tam_her and tekrar_sayaci >= a.tam_her:
            _log("%d gorev tekrarindan sonra PROAKTIF tam yeniden baslatma"
                 % tekrar_sayaci)
            ok = tam_yeniden_baslat()
            tekrar_sayaci = 0
        else:
            ok = yeniden_baslat()
        _log("sonuc: %s (%.0f s)" % ("GOREVDE" if ok else "BASARISIZ",
                                     time.time() - t0))
        kapali = 0
        onceki_acik = bool(gorevde_mi())
        if not ok:
            _log("30 s bekleyip tekrar denenecek")
            time.sleep(30)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        _log("durduruldu")

# -*- coding: utf-8 -*-
"""
================================================================================
  FPS TESHISI  --  darbogazi TAHMIN etme, OLC
================================================================================
"Model 14 FPS ile calisiyor" gibi bir sikayette suclu dort yerden biridir ve
hangisi oldugu MAKINEYE GORE DEGISIR:

    1) EKRAN YAKALAMA   oyun penceresinden kare almak (CPU)
    2) ON ISLEME        1920x1080 -> letterbox imgsz (CPU, kare basina kopya)
    3) CIKARIM          modelin kendisi (GPU)          <- .pt / .engine farki
    4) GIL REKABETI     ayni surecte kosan diger thread'ler (telemetri, log)

Bu betik dordunu AYRI AYRI olcer ve tavan FPS'i hesaplar. Boylece "engine
uret" ya da "poz kapat" gibi bir tavsiye TAHMIN degil OLCUM olur.

⚠ IKI KIP:
  * oyun KAPALIYKEN  -> sentetik kare, yalniz model hizi olculur (temiz tavan)
  * oyun ACIKKEN     -> gercek yakalama + gercek kare (canli tavan)
  Ikisi arasindaki fark YAKALAMA + ON ISLEME maliyetidir.

⚠ Bu betigi SUNUCU KAPALIYKEN calistir. Sunucu koauyorsa GPU'yu paylasir ve
  butun sayilar sisik cikar (bu tuzaga bir kez dusuldu: ayni engine bir
  olcumde 50 ms, temiz olcumde 10 ms gorundu).

KULLANIM
--------------------------------------------------------------------------------
    python arac/fps_teshis.py                # otomatik (oyun varsa canli)
    python arac/fps_teshis.py --tekrar 60
================================================================================
"""
import argparse
import os
import sys
import time

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if KOK not in sys.path:
    sys.path.insert(0, KOK)


def y(v, q):
    if not v:
        return float("nan")
    s = sorted(v)
    return s[min(len(s) - 1, max(0, int(round(q * (len(s) - 1)))))]


def _yaz(s=""):
    print(s, flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tekrar", type=int, default=40)
    ap.add_argument("--model", default=None)
    ap.add_argument("--imgsz", type=int, default=None)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    import numpy as np

    # ── sunucu kosuyor mu (olcumu kirletir) ──
    try:
        import subprocess
        cik = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
             "Where-Object { $_.CommandLine -match 'main\\.py' } | Measure-Object).Count"],
            capture_output=True, text=True, timeout=30)
        if cik.stdout.strip() not in ("", "0"):
            _yaz("⚠⚠ SUNUCU (main.py) KOSUYOR -> olcum KIRLI olur. Once kapat.")
            _yaz()
    except Exception:
        pass

    # ⚠ Cfg config.py'de DEGIL, guidance/ana_kontrol.py icinde tanimli.
    from guidance.ana_kontrol import Cfg
    model_yol = a.model or os.environ.get("AVCI_MODEL", "").strip() or Cfg.VIS_MODEL_PATH
    if not os.path.isabs(model_yol):
        model_yol = os.path.join(KOK, model_yol)
    eng = model_yol[:-3] + ".engine" if model_yol.endswith(".pt") else model_yol
    motor_var = os.path.exists(eng)

    _yaz("=" * 74)
    _yaz("  FPS TESHISI")
    _yaz("=" * 74)
    _yaz("  model      : %s" % os.path.basename(model_yol))
    _yaz("  .engine    : %s" % ("VAR" if motor_var else "YOK  ⛔"))

    # ── 1) EKRAN YAKALAMA ──
    yakalama = []
    kare = None
    try:
        from web import server as S
        # ⚠ SUNUCU windows-capture MOTORUNU BASLATIR, bu betik BASLATMAZSA
        #   grab_frame_bgr() mss fallback'ine duser ve OLCUM YANLIS OLUR
        #   (mss ~119 ms, windows-capture cok daha ucuz). Sunucunun yaptigini
        #   birebir yapiyoruz.
        _pym = getattr(S, "pencere_yakala_motoru", None)
        if _pym is not None:
            try:
                if not _pym.calisiyor():
                    _pym.baslat()
                for _ in range(30):                 # ilk kare gelene kadar bekle
                    if _pym.get_latest_bgr() is not None:
                        break
                    time.sleep(0.1)
            except Exception as _e:
                _yaz("  windows-capture baslatilamadi: %r -> mss ile olculecek" % (_e,))
        for _ in range(6):
            S.grab_frame_bgr()
        for _ in range(a.tekrar):
            t = time.perf_counter()
            bgr, w, h = S.grab_frame_bgr()
            yakalama.append((time.perf_counter() - t) * 1000.0)
            if bgr is not None:
                kare = bgr
    except Exception as e:
        _yaz("  yakalama olculemedi: %r" % (e,))

    canli = kare is not None
    if canli:
        _yaz("  kare       : %dx%d  (canli yakalama)" % (kare.shape[1], kare.shape[0]))
    else:
        kare = np.zeros((1080, 1920, 3), dtype="uint8")
        _yaz("  kare       : 1920x1080 SENTETIK (oyun kapali -> temiz model tavani)")

    if a.imgsz:
        imgsz = a.imgsz
    else:
        try:
            from web import server as _S2
            imgsz = int(getattr(_S2, "MODEL_IMGSZ", 960))
        except Exception:
            imgsz = 960
    _yaz("  imgsz      : %d" % imgsz)
    _yaz()

    # ── 2+3) CIKARIM ──
    # ⚠⚠ HER MODEL AYRI SURECTE OLCULUR. Ayni surecte once .pt sonra .engine
    #   olculunce ikincisi SISIYOR (iki model birden GPU'da duruyor):
    #   ayni engine tek basina 16.9 ms, .pt'den sonra 49.9 ms olctu -- 3 kat
    #   fark, tamamen olcum artefakti. Bu tuzaga bu projede IKI KEZ dusuldu.
    import json as _json
    import subprocess as _sp
    import tempfile as _tf

    _kare_yolu = os.path.join(_tf.gettempdir(), "_fps_teshis_kare.npy")
    np.save(_kare_yolu, kare)

    _COCUK = r"""
import sys, time, json
import numpy as np
from ultralytics import YOLO
yol, kare_yolu, imgsz, n = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
kare = np.load(kare_yolu)
try:
    m = YOLO(yol, task="detect") if yol.endswith(".engine") else YOLO(yol)
    for _ in range(10):
        m.predict(kare, imgsz=imgsz, device=0, verbose=False)
    v = []
    for _ in range(n):
        t = time.perf_counter()
        m.predict(kare, imgsz=imgsz, device=0, verbose=False)
        v.append((time.perf_counter() - t) * 1000.0)
    print("SONUC" + json.dumps(v))
except Exception as e:
    print("HATA" + repr(e))
"""

    def olc_model(yol):
        try:
            cik = _sp.run([sys.executable, "-c", _COCUK, yol, _kare_yolu,
                           str(imgsz), str(a.tekrar)],
                          capture_output=True, text=True, timeout=600, cwd=KOK)
            for satir in (cik.stdout or "").splitlines():
                if satir.startswith("SONUC"):
                    return _json.loads(satir[5:])
                if satir.startswith("HATA"):
                    _yaz("    %s olculemedi: %s" % (os.path.basename(yol), satir[4:]))
                    return []
            _yaz("    %s: cocuk surec sonuc vermedi" % os.path.basename(yol))
            return []
        except Exception as e:
            _yaz("    %s olculemedi: %r" % (os.path.basename(yol), e))
            return []

    pt_v = olc_model(model_yol)
    en_v = olc_model(eng) if motor_var else []
    try:
        os.remove(_kare_yolu)
    except OSError:
        pass

    _yaz("  ── ASAMA MALIYETLERI (ortanca / p90, ms) ──")
    if yakalama:
        _yaz("    ekran yakalama    %7.2f / %7.2f" % (y(yakalama, .5), y(yakalama, .9)))
    if pt_v:
        _yaz("    cikarim .pt       %7.2f / %7.2f" % (y(pt_v, .5), y(pt_v, .9)))
    if en_v:
        _yaz("    cikarim .engine   %7.2f / %7.2f" % (y(en_v, .5), y(en_v, .9)))
    _yaz()

    # ── TAVAN FPS ──
    yak = y(yakalama, .5) if yakalama else 0.0
    _yaz("  ── TAVAN FPS (yakalama + cikarim, tek thread) ──")
    for ad, v in ((".pt", pt_v), (".engine", en_v)):
        if v:
            top = yak + y(v, .5)
            _yaz("    %-9s %6.1f ms/kare  ->  %5.1f FPS" % (ad, top, 1000.0 / top))
    _yaz()

    # ── HUKUM ──
    _yaz("  ── HUKUM ──")
    if not motor_var:
        _yaz("    ⛔ TensorRT engine YOK. Uret:  python arac/motor_uret.py")
        _yaz("       (.engine dosyalari MAKINEYE OZELDIR, kopyalanamaz)")
    elif pt_v and en_v:
        kaz = y(pt_v, .5) / y(en_v, .5)
        _yaz("    engine kazanci %.1f kat (bu makinede, bu yukte)" % kaz)
        if kaz < 1.2:
            _yaz("    ⚠ Kazanc kucuk -> darbogaz cikarimda DEGIL. Asagiya bak.")
    if yakalama and pt_v:
        pay = 100.0 * yak / (yak + y(en_v or pt_v, .5))
        _yaz("    ekran yakalama toplam surenin %%%.0f'i" % pay)
        if pay > 35:
            _yaz("    ⚠ YAKALAMA baskin. Oyunu pencere kipinde ve daha kucuk")
            _yaz("      cozunurlukte calistirmak dogrudan FPS kazandirir.")
    if canli:
        _yaz("    (canli kip: gercek oyun karesi kullanildi)")
    else:
        _yaz("    (oyun kapali: bu TEMIZ TAVAN. Canli FPS bunun altinda olur.)")
    _yaz()
    _yaz("  NOT: canli FPS'i ayrica telemetriden oku -> gorsel.perf.fps / det_ms.")
    _yaz("  Poz acikken (AVCI_POSE=1) ayni GPU paylasilir; olculen bedel ~%17 FPS.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

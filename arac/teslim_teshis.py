# -*- coding: utf-8 -*-
"""
================================================================================
  TESLIM TESHISI  --  "bende talonu algiliyor, onda yazilari algiliyor"
================================================================================
AYNI MODEL, AYNI KOD, FARKLI MAKINE -> farkli tespitler. Sebep modelde DEGIL,
modele VERILEN GORUNTUDE. Bu betik dedektorun GERCEKTEN NE GORDUGUNU resmeder.

NE YAPAR
--------------------------------------------------------------------------------
1) Kareyi dedektorun aldigi YOLDAN alir (windows-capture -> mss bolge -> mss
   tum ekran; sunucunun kullandigi zincirin aynisi)
2) HANGI KAYNAKTAN geldigini yazar   <-- ASIL SORU BU
3) Ekran cozunurlugu, DPI olcegi, oyun penceresi dikdortgeni
4) Dedektoru kosturur ve TUM tespitleri kutulariyla cizer
5) Sonucu iki dosya olarak masaustune kaydeder:
       teslim_teshis.png   (kareyi kutularla)
       teslim_teshis.txt   (rapor)

⚠ SUNUCUYU (main.py) CALISTIRMAYIN. Bu betik kendi basina calisir.
⚠ Oyun ACIK ve gorevde olsun; hedef kadrajda olmasa da olur.

KULLANIM
--------------------------------------------------------------------------------
    python arac/teslim_teshis.py

Cikan iki dosyayi geri gonderin. Tek bakista sebep belli olur:
  * kare masaustunu/tarayiciyi gosteriyorsa -> KAYNAK yanlis (bkz. rapor)
  * kare oyunu gosteriyor ama HUD yazisi kutulanmissa -> model yanlis-pozitifi
================================================================================
"""
import ctypes
import os
import sys
import time

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if KOK not in sys.path:
    sys.path.insert(0, KOK)

CIKTI_PNG = os.path.join(os.path.expanduser("~"), "Desktop", "teslim_teshis.png")
CIKTI_TXT = os.path.join(os.path.expanduser("~"), "Desktop", "teslim_teshis.txt")

_satir = []


def yaz(s=""):
    print(s, flush=True)
    _satir.append(s)


def ekran_bilgi():
    try:
        u = ctypes.windll.user32
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass
        w = u.GetSystemMetrics(0)
        h = u.GetSystemMetrics(1)
        dc = u.GetDC(0)
        lx = ctypes.windll.gdi32.GetDeviceCaps(dc, 88)     # LOGPIXELSX
        u.ReleaseDC(0, dc)
        return w, h, lx / 96.0
    except Exception as e:
        return None, None, None


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    yaz("=" * 74)
    yaz("  TESLIM TESHISI")
    yaz("  " + time.strftime("%Y-%m-%d %H:%M:%S"))
    yaz("=" * 74)

    # ── makine ──
    sw, sh, dpi = ekran_bilgi()
    yaz("  ekran        : %sx%s   DPI olcegi: %s"
        % (sw, sh, ("%.2f" % dpi) if dpi else "?"))
    try:
        import torch
        yaz("  GPU          : %s" % (torch.cuda.get_device_name(0)
                                     if torch.cuda.is_available() else "CUDA YOK"))
    except Exception as e:
        yaz("  GPU          : torch yok (%r)" % (e,))

    # ── oyun penceresi ──
    try:
        from detection.pencere_yakala import pencere_bul
        from web.server import GAME_TITLE_HINTS
        baslik, hwnd = pencere_bul(GAME_TITLE_HINTS)
        yaz("  oyun penceresi: %s  (hwnd=%s)" % (baslik or "BULUNAMADI", hwnd))
        if hwnd:
            r = ctypes.wintypes.RECT()
            ctypes.windll.user32.GetWindowRect(ctypes.c_void_p(hwnd), ctypes.byref(r))
            yaz("  pencere alani : (%d,%d)-(%d,%d)  = %dx%d"
                % (r.left, r.top, r.right, r.bottom, r.right - r.left, r.bottom - r.top))
    except Exception as e:
        yaz("  oyun penceresi: sorgulanamadi (%r)" % (e,))

    # ── kareyi SUNUCUNUN YOLUNDAN al ──
    yaz()
    yaz("  ── KARE KAYNAGI (asil soru) ──")
    try:
        from web import server as S
    except Exception as e:
        yaz("  ⛔ web.server yuklenemedi: %r" % (e,))
        return 1

    pym = getattr(S, "pencere_yakala_motoru", None)
    if pym is not None:
        try:
            if not pym.calisiyor():
                pym.baslat()
            for _ in range(40):
                if pym.get_latest_bgr() is not None:
                    break
                time.sleep(0.1)
        except Exception as e:
            yaz("  windows-capture baslatilamadi: %r" % (e,))
    else:
        yaz("  ⚠ windows-capture motoru YOK -> mss'e dusulecek")

    bgr, w, h = S.grab_frame_bgr()
    if bgr is None:
        yaz("  ⛔ HIC KARE ALINAMADI.")
        return 1

    kaynak = "?"
    try:
        if pym is not None and pym.hazir and pym.calisiyor() and pym.get_latest_bgr() is not None:
            kaynak = "windows-capture (pencere icerigi)  ✔ DOGRU YOL"
        else:
            kaynak = "mss  ⛔ YANLIS YOL (masaustu/ekran girebilir)"
    except Exception:
        pass
    yaz("  kaynak       : %s" % kaynak)
    yaz("  kare boyutu  : %dx%d" % (w, h))
    if sw and (w != sw or h != sh):
        yaz("  not          : kare ekrandan farkli -> pencere bolgesi aliniyor")
    if sw and w == sw and h == sh:
        yaz("  ⚠ UYARI      : kare TAM EKRAN boyutunda. Oyun kenarliksiz pencere")
        yaz("                 degilse dedektor MASAUSTUNU goruyor olabilir.")

    # ── dedektor ──
    yaz()
    yaz("  ── DEDEKTOR ──")
    model_yol = getattr(S, "MODEL_YOL", None)
    imgsz = int(getattr(S, "MODEL_IMGSZ", 960))
    conf_ui = float(getattr(S, "UI_CONF_MIN", 0.25))
    yaz("  model        : %s" % model_yol)
    yaz("  imgsz        : %d   conf esigi: %.2f" % (imgsz, conf_ui))
    eng = (model_yol[:-3] + ".engine") if (model_yol or "").endswith(".pt") else None
    yaz("  .engine      : %s" % ("VAR" if eng and os.path.exists(eng) else "YOK  (FPS yarilanir)"))

    try:
        from ultralytics import YOLO
        m = YOLO(eng, task="detect") if (eng and os.path.exists(eng)) else YOLO(model_yol)
        res = m.predict(bgr, imgsz=imgsz, conf=conf_ui, device=0, verbose=False)[0]
    except Exception as e:
        yaz("  ⛔ dedektor kosmadi: %r" % (e,))
        return 1

    n = 0 if res.boxes is None else len(res.boxes)
    yaz("  TESPIT       : %d kutu" % n)
    kutular = []
    for i in range(n):
        x1, y1, x2, y2 = [float(v) for v in res.boxes.xyxy[i]]
        c = float(res.boxes.conf[i])
        kutular.append((c, x1, y1, x2, y2))
    kutular.sort(reverse=True)
    for i, (c, x1, y1, x2, y2) in enumerate(kutular[:8]):
        nx, ny = (x1 + x2) / 2 / w, (y1 + y2) / 2 / h
        yaz("    #%d conf %.2f  kutu %.0fx%.0f px  merkez (%.2f, %.2f)"
            % (i + 1, c, x2 - x1, y2 - y1, nx, ny))
        if 0.30 <= nx <= 0.70 and 0.48 <= ny <= 0.66:
            yaz("        ⚠ bu kutu HUD YAZISI bolgesinde (ARMED / TRIGGER: NOT READY)")

    # ── ciz ve kaydet ──
    try:
        from PIL import Image, ImageDraw
        img = Image.fromarray(bgr[:, :, ::-1].copy())
        d = ImageDraw.Draw(img)
        for c, x1, y1, x2, y2 in kutular:
            renk = (0, 255, 0) if c >= 0.5 else (255, 160, 0)
            d.rectangle([x1, y1, x2, y2], outline=renk, width=3)
            d.text((x1 + 4, max(0, y1 - 14)), "%.2f" % c, fill=renk)
        # HUD bolgesini isaretle
        d.rectangle([0.30 * w, 0.48 * h, 0.70 * w, 0.66 * h],
                    outline=(255, 0, 0), width=2)
        d.text((0.30 * w + 4, 0.48 * h + 4), "HUD bolgesi", fill=(255, 0, 0))
        img.save(CIKTI_PNG, quality=92)
        yaz()
        yaz("  goruntu kaydedildi: %s" % CIKTI_PNG)
    except Exception as e:
        yaz("  goruntu kaydedilemedi: %r" % (e,))

    yaz()
    yaz("=" * 74)
    yaz("  NASIL OKUNUR")
    yaz("=" * 74)
    yaz("  1) PNG oyunu mu gosteriyor, masaustunu/tarayiciyi mi?")
    yaz("       masaustu ise -> KARE KAYNAGI yanlis.")
    yaz("       Cozum: oyunu TAM EKRAN degil KENARLIKSIZ PENCERE kipinde ac.")
    yaz("  2) Oyunu gosteriyorsa: kutular nerede?")
    yaz("       kirmizi HUD kutusunun icinde ise -> model yazi uzerinde")
    yaz("       yanlis-pozitif veriyor (belgeli davranis, conf ~0.76).")
    yaz("       Cozum: PROP_MASKE'yi ac (guidance/ana_kontrol.py).")
    yaz("  3) Hicbiri degilse raporu geri gonderin.")

    try:
        with open(CIKTI_TXT, "w", encoding="utf-8") as f:
            f.write("\n".join(_satir) + "\n")
        print("\nrapor kaydedildi: %s" % CIKTI_TXT)
    except Exception as e:
        print("rapor kaydedilemedi: %r" % (e,))
    return 0


if __name__ == "__main__":
    import ctypes.wintypes  # noqa: F401  (RECT icin)
    raise SystemExit(main())

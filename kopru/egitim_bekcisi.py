# -*- coding: utf-8 -*-
"""
================================================================================
 EGITIM BEKCISI — egitim bitince DOGRULA, sonra bilgisayari kapat
================================================================================
Kullanici yetkisi: "model egitimi bittikten sonra kapat ve teyit et" (2026-08-09).

NE YAPAR
  1. Egitim surecini (PID) izler, BITMESINI bekler.
  2. Bittiginde SONUCU DOGRULAR: son epoch, best.pt var mi, mAP ne oldu.
  3. Ozeti masaustune yazar (EGITIM_SONUC.txt) — makine kapaninca da kalsin.
  4. Ancak ondan sonra kapatma verir; 120 sn geri sayimla, IPTAL EDILEBILIR.

NEDEN SURE DEGIL SUREC IZLENIYOR
  "1.5 saat sonra kapat" korlemesine olurdu: egitim erken biterse bosuna
  beklenir, gec biterse YARIDA kesilir ve 2 saatlik is coper. Surecin
  bitmesini beklemek tek dogru olcut.

GUVENLIK
  * `--kuru` : kapatma KOMUTU verilmez, sadece dogrulama yapilir (deneme).
  * `--gecikme` : kapatma geri sayimi (vars 120 s). Bu sure icinde
    `shutdown /a` ile iptal edilir.
  * `--azami-saat` : bu kadar surede egitim bitmezse bekci KENDINI kapatir,
    makineyi KAPATMAZ (asili kalmis bir kapatma emrinden iyidir).
  * Egitim COKMUSSE (best.pt yok / results.csv bos) kapatma YAPILMAZ --
    kullanici hatayi gormeli.

KULLANIM
    python kopru/egitim_bekcisi.py --pid 6436 --kosu <talon_v1 klasoru>
    python kopru/egitim_bekcisi.py --pid 6436 --kosu <...> --kuru
================================================================================
"""
import argparse
import csv
import os
import subprocess
import sys
import time

MASAUSTU = os.path.join(os.path.expanduser("~"), "Desktop")


def surec_yasiyor(pid):
    """PID hala calisiyor mu (Windows tasklist ile)."""
    try:
        out = subprocess.run(["tasklist", "/FI", "PID eq %d" % pid, "/FO", "CSV"],
                             capture_output=True, text=True, timeout=30).stdout
        return ('"%d"' % pid) in out
    except Exception:
        return False


def sonuc_oku(kosu):
    """results.csv + weights -> dogrulama ozeti. -> (ok, ozet_metni, dict)"""
    rcsv = os.path.join(kosu, "results.csv")
    best = os.path.join(kosu, "weights", "best.pt")
    last = os.path.join(kosu, "weights", "last.pt")
    d = {"kosu": kosu, "best_var": os.path.exists(best),
         "last_var": os.path.exists(last), "epoch": 0}
    satir = []
    if not os.path.exists(rcsv):
        return False, "results.csv YOK -> egitim hic baslamamis olabilir", d
    try:
        with open(rcsv, encoding="utf-8") as f:
            r = list(csv.DictReader(f))
    except Exception as e:
        return False, "results.csv okunamadi: %r" % e, d
    if not r:
        return False, "results.csv BOS -> egitim cokmus olabilir", d

    def g(row, ad):
        for k in row:
            if k.strip() == ad:
                return row[k]
        return None

    try:
        m = [float(g(x, "metrics/mAP50-95(B)")) for x in r]
        m50 = [float(g(x, "metrics/mAP50(B)")) for x in r]
        sure = float(g(r[-1], "time"))
    except (TypeError, ValueError) as e:
        return False, "metrik kolonlari okunamadi: %r" % e, d
    d.update(epoch=len(r), map5095_son=m[-1], map5095_eniyi=max(m),
             eniyi_epoch=m.index(max(m)) + 1, map50_son=m50[-1], sure_s=sure)
    if d["best_var"]:
        d["best_mb"] = os.path.getsize(best) / 1048576.0
    satir.append("tamamlanan epoch : %d" % d["epoch"])
    satir.append("gecen sure       : %.0f dk" % (sure / 60))
    satir.append("mAP50 son        : %.4f" % d["map50_son"])
    satir.append("mAP50-95 son     : %.4f" % d["map5095_son"])
    satir.append("mAP50-95 EN IYI  : %.4f  (epoch %d)"
                 % (d["map5095_eniyi"], d["eniyi_epoch"]))
    satir.append("best.pt          : %s" % ("VAR (%.1f MB)" % d["best_mb"]
                                            if d["best_var"] else "YOK"))
    # BASARILI sayilma olcutu: en az 1 epoch bitmis VE best.pt yazilmis
    ok = d["epoch"] >= 1 and d["best_var"]
    return ok, "\n".join(satir), d


def main(argv=None):
    ap = argparse.ArgumentParser(description="Egitim bitince dogrula ve kapat")
    ap.add_argument("--pid", type=int, required=True, help="egitim sureci PID'i")
    ap.add_argument("--kosu", required=True, help="talon_v1 klasoru")
    ap.add_argument("--gecikme", type=int, default=120,
                    help="kapatma geri sayimi (s); bu sure icinde 'shutdown /a'")
    ap.add_argument("--azami-saat", type=float, default=4.0,
                    help="bu surede bitmezse bekci cikar, KAPATMAZ")
    ap.add_argument("--kuru", action="store_true",
                    help="kapatma komutu VERME, sadece dogrula")
    args = ap.parse_args(argv)

    t0 = time.time()
    print("[BEKCI] egitim sureci izleniyor: PID %d" % args.pid)
    print("[BEKCI] azami bekleme: %.1f saat  |  kuru kosu: %s"
          % (args.azami_saat, args.kuru))
    sys.stdout.flush()

    while surec_yasiyor(args.pid):
        if (time.time() - t0) > args.azami_saat * 3600:
            print("[BEKCI] AZAMI SURE doldu, egitim hala kosuyor -> "
                  "makine KAPATILMADI, bekci cikiyor.")
            return 2
        time.sleep(20)

    gecen = (time.time() - t0) / 60.0
    print("[BEKCI] egitim sureci bitti (%.0f dk sonra). Dogrulaniyor..." % gecen)
    time.sleep(10)                      # son dosyalar diske insin

    ok, ozet, d = sonuc_oku(args.kosu)
    baslik = "EGITIM %s  —  %s" % ("TAMAMLANDI" if ok else "SORUNLU",
                                   time.strftime("%Y-%m-%d %H:%M:%S"))
    metin = baslik + "\n" + "=" * len(baslik) + "\n" + ozet + "\n"
    if ok:
        metin += "\nAgirlik: %s\n" % os.path.join(args.kosu, "weights", "best.pt")
        metin += ("\nSIRADAKI OLCUM (Windows acilinca):\n"
                  "  1) HUD yanlis-pozitif testi — ayni 1074 karelik havuz.\n"
                  "     Bugunku model 5228 yanlis kutu uretiyor, %90'i HUD'da.\n"
                  "     python veriseti\\negatif_topla.py --oturum "
                  "C:\\talon_dataset_v2\\negatif_ham\\oturum_20260809_080936 "
                  "--model <best.pt> --n 1000 --cikti <klasor>\n"
                  "  2) Etiket uyumu — 766 elle cizilmis kareye karsi (bugun 0.9266).\n")
    else:
        metin += "\n[UYARI] Dogrulama GECMEDI -> makine KAPATILMADI.\n"
    print(metin)
    try:
        with open(os.path.join(MASAUSTU, "EGITIM_SONUC.txt"), "w",
                  encoding="utf-8") as f:
            f.write(metin)
        print("[BEKCI] ozet yazildi: %s" % os.path.join(MASAUSTU, "EGITIM_SONUC.txt"))
    except Exception as e:
        print("[BEKCI] ozet yazilamadi: %r" % e)

    if not ok:
        print("[BEKCI] egitim dogrulanamadi -> KAPATMA YAPILMIYOR.")
        return 1
    if args.kuru:
        print("[BEKCI] KURU KOSU -> kapatma komutu verilmedi.")
        return 0

    print("[BEKCI] kapatma veriliyor: %d sn sonra. IPTAL: shutdown /a"
          % args.gecikme)
    sys.stdout.flush()
    try:
        subprocess.run(["shutdown", "/s", "/t", str(args.gecikme), "/c",
                        "Egitim tamamlandi (mAP50-95 %.4f) - bilgisayar kapaniyor. "
                        "Iptal: shutdown /a" % d.get("map5095_eniyi", 0.0)],
                       timeout=30)
    except Exception as e:
        print("[BEKCI] kapatma komutu verilemedi: %r" % e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

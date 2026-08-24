# -*- coding: utf-8 -*-
"""
================================================================================
  KAMPANYA OZET  --  gece sonuclarini AYAR bazinda topla ve siralari ver
================================================================================
Her ayar birden cok kez kosuldu (tur). Bu arac turlari BIRLESTIRIR, cunku tek
tur gurultuludur: 11 dakikada 1-3 angajman oluyor ve vurus olasiligi ~%8.
Tek turda "R3 kazandi" demek TESADUFU raporlamaktir.

⚠ ISTATISTIK UYARISI: n kucukse fark anlamli DEGILDIR. Arac her ayar icin
   toplam angajman sayisini yazar; n < 10 ise "yetersiz" isareti koyar.

CALISTIR
    python arac/kampanya_ozet.py
    python arac/kampanya_ozet.py --iz     # tik izinden menzil/tespit profili de
================================================================================
"""
import os
import csv
import glob
import math
import argparse
from collections import defaultdict

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CIK = os.path.join(KOK, "veri", "gece")


def _f(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def taban_ad(a):
    return str(a).split("#")[0]


def ozet():
    p = os.path.join(CIK, "kampanya_sonuc.csv")
    if not os.path.exists(p):
        print("  kampanya_sonuc.csv yok -- kampanya henuz ilk ayari bitirmedi.")
        return
    R = list(csv.DictReader(open(p, encoding="utf-8")))
    if not R:
        print("  sonuc bos.")
        return

    G = defaultdict(list)
    for r in R:
        G[taban_ad(r["ayar"])].append(r)

    print("=" * 118)
    print("GECE KAMPANYASI — AYAR BAZINDA (turlar birlestirildi)")
    print("=" * 118)
    bas = ("%-20s %4s %5s %6s %7s %8s %7s %7s %8s %7s %7s %7s %6s"
           % ("ayar", "tur", "dk", "kosu", "VURUS", "en_yakin", "<5m%", "<10m%",
              "kilit_mx", "kilit5%", "tespit%", "kopru%", "fps"))
    print(bas)
    print("-" * 118)

    sira = []
    for ad in sorted(G):
        rs = G[ad]
        n = len(rs)
        dk = sum(_f(r["sure_dk"]) for r in rs)
        kosu = sum(int(_f(r["kosu"])) for r in rs)
        # oyun mandali (yeni) + respawn (kesin)
        oy = sum(int(_f(r.get("oyun_vurus"))) for r in rs)
        rv = sum(int(_f(r["vurus"])) for r in rs)
        eny = min([_f(r["en_yakin_m"], 1e9) for r in rs if r["en_yakin_m"]] or [1e9])
        ort = lambda k: (sum(_f(r.get(k)) for r in rs) / n) if n else 0.0
        mx = lambda k: max([_f(r.get(k)) for r in rs] or [0.0])
        d = {
            "ad": ad, "tur": n, "dk": dk, "kosu": kosu, "oyun_vurus": oy,
            "respawn_vurus": rv, "en_yakin": eny,
            "alt5": ort("alt5_%"), "alt10": ort("alt10_%"),
            "kilit_mx": mx("kilit_max_s"), "kilit5": ort("kilit5_%"),
            "tespit": ort("tespit_%"), "kopru": ort("kopru_%"),
            "gorsel": ort("gorsel_%"), "fps": ort("fps_med"),
            "det": ort("det_ms_med"), "menzil": ort("menzil_med"),
        }
        sira.append(d)
        print("%-20s %4d %5.0f %6d %7s %8.2f %7.2f %7.1f %8.1f %7.1f %7.1f %7.1f %6.1f"
              % (ad, n, dk, kosu, "%d/%d" % (oy, rv), eny if eny < 1e8 else -1,
                 d["alt5"], d["alt10"], d["kilit_mx"], d["kilit5"],
                 d["tespit"], d["kopru"], d["fps"]))
    print("-" * 118)
    print("  VURUS sutunu = oyun_mandali(<3 m) / respawn_dogrulanmis")
    print("  en_yakin = TUM turlarin en iyisi (tek olay, gurultulu -- tek basina karar verme)")

    # ── SIRALAMA: once <5 m zamani, sonra kilit ─────────────────────────
    print()
    print("SIRALAMA — 'hedefe yakin gecirilen zaman' (alt5_%) esas olcut")
    print("  gerekce: tek vurus tesaduf olabilir; <5 m'de gecen zaman orani")
    print("           angajman basina degil ZAMAN basina olculur, cok daha kararli.")
    print("-" * 60)
    for i, d in enumerate(sorted(sira, key=lambda x: -x["alt5"]), 1):
        yeter = "" if d["dk"] >= 30 else "   ⚠ n yetersiz (%.0f dk)" % d["dk"]
        print("  %d. %-20s <5m %%%.2f | kilit_max %.1f s | vurus %d/%d%s"
              % (i, d["ad"], d["alt5"], d["kilit_mx"],
                 d["oyun_vurus"], d["respawn_vurus"], yeter))

    print()
    print("SIRALAMA — kilit (kullanicinin sart kostugu 5 saniye)")
    print("-" * 60)
    for i, d in enumerate(sorted(sira, key=lambda x: (-x["kilit5"], -x["kilit_mx"])), 1):
        print("  %d. %-20s kilit>=5s zaman %%%.1f | en uzun %.1f s | tespit %%%.0f"
              % (i, d["ad"], d["kilit5"], d["kilit_mx"], d["tespit"]))

    toplam_dk = sum(d["dk"] for d in sira)
    toplam_oy = sum(d["oyun_vurus"] for d in sira)
    toplam_rv = sum(d["respawn_vurus"] for d in sira)
    print()
    print("TOPLAM: %.0f dakika ucus | %d oyun-mandali vurus | %d respawn-dogrulanmis"
          % (toplam_dk, toplam_oy, toplam_rv))


def iz_profili():
    """Tik izinden: menzile gore TESPIT ORANI. Gecenin tek kritik bilinmeyeni."""
    ys = sorted(glob.glob(os.path.join(CIK, "kampanya_iz_*.csv")),
                key=os.path.getmtime)
    if not ys:
        print("\n  iz dosyasi yok.")
        return
    kova = defaultdict(lambda: [0, 0])
    kova_ayar = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    n = 0
    for y in ys[-3:]:
        try:
            for r in csv.DictReader(open(y, encoding="utf-8", errors="replace")):
                m = _f(r.get("menzil"), -1)
                if m <= 0 or m > 80:
                    continue
                b = int(m // 5) * 5
                t = 1 if str(r.get("tespit")).lower() in ("true", "1") else 0
                kova[b][0] += t
                kova[b][1] += 1
                a = taban_ad(r.get("ayar", "?"))
                kova_ayar[a][b][0] += t
                kova_ayar[a][b][1] += 1
                n += 1
        except OSError:
            continue
    if not n:
        return
    print()
    print("=" * 70)
    print("TESPIT ORANI x MENZIL  (gecenin en kritik olculmemis parametresiydi)")
    print("=" * 70)
    print("  %-12s %10s %10s   %s" % ("menzil", "tespit%", "ornek", "bar"))
    for b in sorted(kova):
        t, tot = kova[b]
        if tot < 30:
            continue
        o = 100.0 * t / tot
        print("  %-12s %9.1f%% %10d   %s"
              % ("%d-%d m" % (b, b + 5), o, tot, "#" * int(o / 2)))
    print("\n  ⚠ Bu tablo kilit zincirinin tabanidir: kilit ancak tespit VARKEN")
    print("     birikir. 7-12 m bandinda %80+ degilse 5 s kesintisiz kilit")
    print("     ISTATISTIKSEL OLARAK imkansizdir.")


def hayalet_orani():
    """Ayar bazinda GERCEK hayalet kare orani.

    ⚠ NEDEN AYRI: kampanyanin `kopru_%` sutunu telemetrideki /gorsel/kopru'yu
      okuyor, o da `beyin.vis_kopru` -- ana_kontrol'un KENDI olu-hesap koprusu.
      bbox_ibvs'in hayalet karesi ORASI DEGIL. Gercek olcum yasanin kendi
      logundadir (`kopru` sutunu). Bu ayrimi fark etmeden "hayaletsiz" ayarini
      degerlendirmek yanlis sonuc verirdi.
    """
    import re
    import time
    kl = os.path.join(CIK, "kampanya.log")
    if not os.path.exists(kl):
        return
    # ayar -> (baslangic, bitis) duvar saati
    pencere = []
    ad = None
    t0 = None
    gun = None
    for satir in open(kl, encoding="utf-8", errors="replace"):
        m = re.match(r"^(\d\d):(\d\d):(\d\d)\s+AYAR\s+(\S+)", satir)
        if m:
            if ad and t0 is not None:
                pencere.append((ad, t0, _saniye(m.group(1), m.group(2), m.group(3))))
            ad = m.group(4).split("#")[0]
            t0 = _saniye(m.group(1), m.group(2), m.group(3))
    if ad and t0 is not None:
        pencere.append((ad, t0, t0 + 3600))
    if not pencere:
        return
    # bbox_ibvs dosyalarini duvar saatine gore ayarlara dagit
    from collections import defaultdict
    say = defaultdict(lambda: [0, 0, 0])       # ad -> [kare, hayalet, terminal]
    for y in glob.glob(os.path.join(KOK, "kopru", "gazebo_kaynak", "logs",
                                    "bbox_ibvs_*.csv")):
        b = os.path.basename(y)
        m = re.search(r"_(\d{6})\.csv$", b)
        if not m:
            continue
        hh, mm, ss = m.group(1)[:2], m.group(1)[2:4], m.group(1)[4:]
        ts = _saniye(hh, mm, ss)
        hedef = None
        for a_, s_, e_ in pencere:
            if s_ <= ts <= e_:
                hedef = a_
                break
        if hedef is None:
            continue
        try:
            for r in csv.DictReader(open(y, encoding="utf-8", errors="replace")):
                say[hedef][0] += 1
                if str(r.get("kopru", "0")).strip() in ("1", "1.0"):
                    say[hedef][1] += 1
                if "TERM" in str(r.get("durum", "")):
                    say[hedef][2] += 1
        except OSError:
            continue
    if not say:
        return
    print()
    print("=" * 70)
    print("GERCEK HAYALET KARE ORANI (bbox_ibvs logundan, telemetriden DEGIL)")
    print("=" * 70)
    print("  %-20s %8s %10s %10s" % ("ayar", "komut", "hayalet%", "terminal%"))
    for a_ in sorted(say):
        n, k, t = say[a_]
        if n < 50:
            continue
        print("  %-20s %8d %9.1f%% %9.1f%%" % (a_, n, 100.0 * k / n, 100.0 * t / n))
    print()
    print("  ⚠ 'hayaletsiz' ayarinda bu sutun ~0 olmali. Degilse yama tutmamis.")


def _saniye(hh, mm, ss):
    return int(hh) * 3600 + int(mm) * 60 + int(ss)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--iz", action="store_true")
    a = ap.parse_args()
    ozet()
    if a.iz:
        iz_profili()
        hayalet_orani()

# -*- coding: utf-8 -*-
"""SON SUPURME: istasyon mesafesi ile clamp'lerin AYRI etkisini olcer.

Olculen gerilim: kapatmak icin hiz gerekiyor, hiz izi olduruyor.
    istasyon 18 -> 18.7m | 13 -> 15.6m | 9 -> 13.7m   (kisa DAHA IYI)
    clamp'ler acilinca faz omru 1.59 -> 1.07 s        (hiz ZARARLI)
Bu supurme ikisini ayirir ve istasyonu vurus esigine (3 m) dogru zorlar.
"""
import json, time, sys, urllib.request

KOK = 'http://127.0.0.1:8000'
YENI = {"V_TOPLAM_MAX": 26.0, "MAX_ACCEL": 25.0, "VZ_MAX": 4.0}
ESKI = {"V_TOPLAM_MAX": 24.0, "MAX_ACCEL": 12.0, "VZ_MAX": 3.0}

# ⚠ OLCULDU (16 Agu, ayni istasyonda tek degisken): ACIK clamp'ler ZARARLI.
#     S9_yeni (26/25/4) 15.25m omur 1.06s  |  S9_eski (24/12/3) 12.73m omur 1.28s
# Hiz artisi hedefin yanindan daha hizli supurup izi olduruyor. Bu yuzden
# asagidaki supurme ESKI clamp'lerle kosuyor ve yalniz istasyonu kisaltiyor.
AYARLAR = [
    ("E7_eski",  dict(ESKI, RANGE_SET=7.0)),
    ("E5_eski",  dict(ESKI, RANGE_SET=5.0)),
]


def ayarla(a, d):
    req = urllib.request.Request(KOK + '/api/gudum_ozellikleri',
                                 data=json.dumps({"anahtar": a, "deger": d}).encode(),
                                 headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=6) as r:
        return json.loads(r.read().decode('utf-8', 'replace'))


def aktif():
    try:
        with urllib.request.urlopen(KOK + '/api/telemetry', timeout=4) as r:
            return json.loads(r.read().decode('utf-8', 'replace')).get('gorev_aktif')
    except Exception:
        return False


def main():
    sure = float(sys.argv[1]) if len(sys.argv) > 1 else 130.0
    while not aktif():
        time.sleep(2.0)
    kayit = []
    for ad, kw in AYARLAR:
        for k, v in kw.items():
            r = ayarla(k, v)
            if not r.get("ok"):
                print("  !! %s=%s : %s" % (k, v, r.get("hata")), flush=True)
        t0 = time.perf_counter()
        print("  [%s] %s" % (ad, kw), flush=True)
        time.sleep(sure)
        kayit.append({"ad": ad, "ayar": dict(kw), "t0": t0, "t1": time.perf_counter()})
        print("  [%s] bitti" % ad, flush=True)
    with open("veri/ab_pn_pencereler.json", "w", encoding="utf-8") as f:
        json.dump(kayit, f, indent=1)
    print("  -> python arac/pn_kiyas.py", flush=True)


if __name__ == "__main__":
    main()

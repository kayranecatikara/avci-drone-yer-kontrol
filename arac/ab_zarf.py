# -*- coding: utf-8 -*-
"""Ucus sirasinda ZARF CLAMP suprumu: kapanma hizini kademeli acar.

NEDEN: 4 guduum yasasi A/B'si hepsi ~19.5 m verdi -> bu calisma noktasinda
yasa fark etmiyor. Olculen kapanma hizi +3.4 m/s, hiz orani 1.2:1, faz 1.8 s.
Once kapanma hizini yaratmak lazim.

⚠ ZAMAN DAMGASI perf_counter ile yazilir (bbox_ibvs loglariyla ayni eksen).
   Ilk surumde time.time() yazilmisti ve pencereler loglarla eslesmedi.
"""
import json, time, sys, urllib.request

KOK = 'http://127.0.0.1:8000'


def ayarla(anahtar, deger):
    req = urllib.request.Request(KOK + '/api/gudum_ozellikleri',
                                 data=json.dumps({"anahtar": anahtar, "deger": deger}).encode(),
                                 headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=6) as r:
        return json.loads(r.read().decode('utf-8', 'replace'))


def gorev_var():
    try:
        with urllib.request.urlopen(KOK + '/api/telemetry', timeout=4) as r:
            return json.loads(r.read().decode('utf-8', 'replace')).get('gorev_aktif')
    except Exception:
        return False


AYARLAR = [
    # (ad, {anahtar: deger})   — zarf: yanal 39.22, hiz 34.6, tirmanma 33.7
    ("Z0_temel",   {"V_TOPLAM_MAX": 24.0, "MAX_ACCEL": 12.0, "VZ_MAX": 3.0}),
    ("Z1_hiz",     {"V_TOPLAM_MAX": 30.0, "MAX_ACCEL": 12.0, "VZ_MAX": 3.0}),
    ("Z2_hiz_ivme", {"V_TOPLAM_MAX": 30.0, "MAX_ACCEL": 25.0, "VZ_MAX": 3.0}),
    ("Z3_hepsi",   {"V_TOPLAM_MAX": 30.0, "MAX_ACCEL": 25.0, "VZ_MAX": 9.0}),
]


def main():
    sure = float(sys.argv[1]) if len(sys.argv) > 1 else 150.0
    print("  gorev bekleniyor (arayuzde GPS Guduum'e basin)...", flush=True)
    while not gorev_var():
        time.sleep(2.0)
    print("  gorev aktif -> supurme basliyor", flush=True)

    kayit = []
    for ad, kw in AYARLAR:
        for k, v in kw.items():
            r = ayarla(k, v)
            if not r.get("ok"):
                print("  !! %s=%s yazilamadi: %s" % (k, v, r.get("hata")), flush=True)
        t0 = time.perf_counter()
        print("  [%s] %s" % (ad, kw), flush=True)
        time.sleep(sure)
        kayit.append({"ad": ad, "ayar": kw, "t0": t0, "t1": time.perf_counter()})
        print("  [%s] bitti" % ad, flush=True)

    with open("veri/ab_pn_pencereler.json", "w", encoding="utf-8") as f:
        json.dump(kayit, f, indent=1)
    print("  -> veri/ab_pn_pencereler.json  (python arac/pn_kiyas.py ile coz)", flush=True)


if __name__ == "__main__":
    main()

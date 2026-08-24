# -*- coding: utf-8 -*-
"""Ucus sirasinda A/B: ozelligi canli degistirir, pencereyi damgalar.

Faz kendiliginden ~28 s'de bir tekrarladigi icin her ayarda birkac angajman
toplanir. Ciktidaki damgalar arac/pn_kiyas.py ile loglara eslenir.
"""
import json, time, sys, urllib.request

KOK = 'http://127.0.0.1:8000'


def ayarla(anahtar, deger):
    req = urllib.request.Request(KOK + '/api/gudum_ozellikleri',
                                 data=json.dumps({"anahtar": anahtar, "deger": deger}).encode(),
                                 headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=6) as r:
        return json.loads(r.read().decode('utf-8', 'replace'))


def main():
    sure = float(sys.argv[1]) if len(sys.argv) > 1 else 150.0
    ayarlar = [
        ("C_mevcut",   {"PN_N": 1.6, "BURUN_LOS": True,  "SONUM_T": 0.30}),
        ("A_burun_off", {"PN_N": 1.6, "BURUN_LOS": False, "SONUM_T": 0.30}),
        ("B_pn_off",    {"PN_N": 0.0, "BURUN_LOS": True,  "SONUM_T": 0.30}),
        ("D_temel",     {"PN_N": 0.0, "BURUN_LOS": False, "SONUM_T": 0.30}),
    ]
    kayit = []
    for ad, kw in ayarlar:
        for k, v in kw.items():
            r = ayarla(k, v)
            if not r.get("ok"):
                print("  !! %s=%s yazilamadi: %s" % (k, v, r.get("hata")), flush=True)
        t0 = time.time()
        print("  [%s] basladi  %s" % (ad, kw), flush=True)
        time.sleep(sure)
        t1 = time.time()
        kayit.append({"ad": ad, "ayar": kw, "t0": t0, "t1": t1})
        print("  [%s] bitti  (%.0f s)" % (ad, t1 - t0), flush=True)
    with open("veri/ab_pn_pencereler.json", "w", encoding="utf-8") as f:
        json.dump(kayit, f, indent=1)
    print("  -> veri/ab_pn_pencereler.json", flush=True)


if __name__ == "__main__":
    main()

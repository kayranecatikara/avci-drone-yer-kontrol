# -*- coding: utf-8 -*-
"""KOK NEDEN supurmesi: (1) lam zaman hizalamasi, (2) istasyon menzili.

1) YAW_HIZALA_S: lam_sisme'yi EN AZ yapan deger GERCEK dedektor gecikmesidir.
   Hem duzeltir hem mekanizmayi dogrular. lam_sisme dusmezse mekanizma yanlis.
2) RANGE_SET: gorsel fazin KAPATMASI GEREKEN mesafe, faz omrune sigmali.
   Olculen: kapanma ~4 m/s, faz 1.8 s -> ~7 m kapatabiliyoruz. Istasyon 18 m.
"""
import json, time, sys, urllib.request

KOK = 'http://127.0.0.1:8000'


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


AYARLAR = [
    ("H0_hizalama_yok", {"YAW_HIZALA_S": 0.00, "RANGE_SET": 18.0}, 90),
    ("H1_hizalama_45",  {"YAW_HIZALA_S": 0.045}, 90),
    ("H2_hizalama_90",  {"YAW_HIZALA_S": 0.090}, 90),
    ("R13_istasyon",    {"YAW_HIZALA_S": 0.045, "RANGE_SET": 13.0}, 150),
    ("R9_istasyon",     {"RANGE_SET": 9.0}, 150),
]


def main():
    print("  gorev bekleniyor...", flush=True)
    while not aktif():
        time.sleep(2.0)
    kayit = []
    for ad, kw, sure in AYARLAR:
        for k, v in kw.items():
            r = ayarla(k, v)
            if not r.get("ok"):
                print("  !! %s=%s : %s" % (k, v, r.get("hata")), flush=True)
        t0 = time.perf_counter()
        print("  [%s] %s  (%d s)" % (ad, kw, sure), flush=True)
        time.sleep(sure)
        kayit.append({"ad": ad, "ayar": dict(kw), "t0": t0, "t1": time.perf_counter()})
        print("  [%s] bitti" % ad, flush=True)
    with open("veri/ab_pn_pencereler.json", "w", encoding="utf-8") as f:
        json.dump(kayit, f, indent=1)
    print("  -> python arac/pn_kiyas.py", flush=True)


if __name__ == "__main__":
    main()

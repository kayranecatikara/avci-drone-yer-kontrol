# -*- coding: utf-8 -*-
"""RECETE: dort parametreyi AYNI ANDA uygular, sonra FPS ve fazi izler.

NEDEN HEPSI BIRDEN: 16 Agustos'ta her biri AYRI denendi ve hicbiri en yakin
gecisi oynatmadi. Yakalanabilirlik analizi bunun sebebini veriyor:
    sadece D->16              0/10
    D->16 + dikey->4m         0/10
    TAM RECETE (D,V,a,vz)     9/10   medyan iska 0.16 m
Kok yasa: MAX_ACCEL >= V^2/51 (hedefin yayinda kalmak). a=12 iken V tavani
24.7 m/s -- ivme acilmadan hiz artirmak ZARARLI (V=31,a=12 -> 3/10).
"""
import json, time, sys, urllib.request, statistics as st

KOK = 'http://127.0.0.1:8000'

RECETE = {
    "RANGE_SET":     12.0,   # olculen: 18->18.7m, 13->15.6m, 9->13.7m (kisa daha iyi)
    "V_TOPLAM_MAX":  26.0,   # V^2/51 = 13.3 <= MAX_ACCEL 25  ✓
    "MAX_ACCEL":     25.0,   # olculen: a=18 -> 5/10, a=25 -> 9/10
    "VZ_MAX":         4.0,   # h<=4 m'de 9/10
    "KAPANMA":      False,   # kutudan kapanma hizi SNR 0.4 -> sabitten kotu
    "YAW_HIZALA_S":  0.12,   # supurme 0->0.045->0.090'da lam sismesi 6.9->4.4->3.2
}


def ayarla(a, d):
    req = urllib.request.Request(KOK + '/api/gudum_ozellikleri',
                                 data=json.dumps({"anahtar": a, "deger": d}).encode(),
                                 headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=6) as r:
        return json.loads(r.read().decode('utf-8', 'replace'))


def tel():
    with urllib.request.urlopen(KOK + '/api/telemetry', timeout=4) as r:
        return json.loads(r.read().decode('utf-8', 'replace'))


def main():
    izle = float(sys.argv[1]) if len(sys.argv) > 1 else 240.0
    print("  gorev bekleniyor (arayuzde GPS Guduum -> sonra OTO)...", flush=True)
    while True:
        try:
            if tel().get('gorev_aktif'):
                break
        except Exception:
            pass
        time.sleep(2.0)

    print("  gorev aktif -> RECETE uygulaniyor", flush=True)
    for k, v in RECETE.items():
        r = ayarla(k, v)
        print("    %-14s = %-7s %s" % (k, v, "OK" if r.get("ok") else "!! " + str(r.get("hata"))), flush=True)

    # pipeline OTO
    req = urllib.request.Request(KOK + '/api/command',
                                 data=json.dumps({"cmd": "vismode", "mode": "OTO"}).encode(),
                                 headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=6) as r:
        print("    pipeline    -> %s" % json.loads(r.read().decode())['msg'], flush=True)

    t0 = time.perf_counter()
    fps = []
    det = []
    gecis0 = None
    print("\n  %7s %7s %8s %7s %8s %7s" % ("t", "fps", "det_ms", "faz", "menzil", "gecis"), flush=True)
    son = 0.0
    while time.perf_counter() - t0 < izle:
        try:
            t = tel()
        except Exception:
            time.sleep(0.5)
            continue
        g = t.get('gorsel', {}) or {}
        p = g.get('perf', {}) or {}
        h = (t.get('gudum', {}) or {}).get('hibrit', {}) or {}
        if p.get('fps'):
            fps.append(p['fps'])
        if p.get('det_ms'):
            det.append(p['det_ms'])
        if gecis0 is None and h.get('gecis_sayisi') is not None:
            gecis0 = h['gecis_sayisi']
        if time.perf_counter() - son >= 8.0:
            son = time.perf_counter()
            print("  %6.0fs %7s %8s %7s %8s %7s" % (
                son - t0, p.get('fps', '-'), p.get('det_ms', '-'), h.get('faz', '-'),
                round(t.get('gercek_mesafe_m') or 0, 1), h.get('gecis_sayisi', '-')), flush=True)
        time.sleep(0.4)

    print("\n  === OZET ===", flush=True)
    if fps:
        print("  FPS medyan %.1f (min %.1f)   det_ms medyan %.1f" %
              (st.median(fps), min(fps), st.median(det) if det else 0), flush=True)
        print("  kiyas: 14:12 -> 46.0/21.2 | 14:43 sonrasi -> 12.1/78.5", flush=True)
    try:
        h = (tel().get('gudum', {}) or {}).get('hibrit', {}) or {}
        print("  toplam gecis: %s" % h.get('gecis_sayisi'), flush=True)
    except Exception:
        pass
    print("  -> python arac/ariza_taksonomi.py   (en yakin gecis + olum sekli)", flush=True)


if __name__ == "__main__":
    main()

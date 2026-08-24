# -*- coding: utf-8 -*-
"""
================================================================================
  KAMPANYA  --  gece boyu gozetimsiz A/B: ayar -> kos -> puanla -> sonraki
================================================================================
NEDEN
--------------------------------------------------------------------------------
"Bazen sans eseri vuruyor" iddiasini elemenin tek yolu AYNI ayarla COK kosu.
Tek vurus kanit degildir. Bu surucu her ayari SABIT sure kosturur, ayni sekilde
puanlar ve sonuclari tek dosyada biriktirir. Ayarlar arasinda sunucu YENIDEN
BASLATILIR (env import aninda okunuyor).

AKIS (her ayar icin)
    1. sunucuyu oldur
    2. env'i kur, sunucuyu baslat, ayaga kalkmasini bekle
    3. oyun baglantisini dogrula; yoksa oyun kurtarmayi dene
    4. gorevi baslat (OTO + gercek GPS)
    5. SURE_DK boyunca 10 Hz telemetri topla; isinlanma = kosu sonu
    6. puanla, kaydet, sonrakine gec

DAYANIKLILIK
    * sunucu duserse yeniden baslatilir
    * oyun duserse arac/oyun_kurtar.py dizisi calistirilir
    * telemetri kesilirse beklenir, kampanya DURMAZ
    * Ctrl+C ile temiz cikis

CALISTIR
    python arac/kampanya.py --dk 12                  # varsayilan recete
    python arac/kampanya.py --recete recete.json --dk 15
================================================================================
"""
import os
import sys
import csv
import json
import time
import math
import signal
import argparse
import subprocess
import urllib.request

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "arac"))
CIK = os.path.join(KOK, "veri", "gece")
SUNUCU = "http://127.0.0.1:8000"

import oyun_kurtar as OK                                    # noqa: E402


# ─────────────────────────────────────────────────────────────────────────
#  VARSAYILAN RECETE
#  Her giris: (ad, env sozlugu, aciklama)
#  ⚠ TEK DEGISKEN kurali: ardisik ayarlar arasinda mumkun oldugunca tek fark.
# ─────────────────────────────────────────────────────────────────────────
VARSAYILAN = [
    ("A0_taban", {
        "AVCI_GPS_FF_KORU": "0",          # ESKI davranis: toplam kirpma
        "AVCI_IBVS_KOPRU_ATALET": "1.5",  # hayalet kutu ACIK (eski)
    }, "Referans: bu geceden ONCEKI davranis (sadece perf yamalari ile)"),

    ("B1_ff_koru", {
        "AVCI_GPS_FF_KORU": "1",          # ileri besleme korunur
        "AVCI_IBVS_KOPRU_ATALET": "1.5",
    }, "TEK FARK: ileri besleme kirpilmaz -> arkadan takip + hiz esleme"),

    ("B2_ff_hayaletsiz", {
        "AVCI_GPS_FF_KORU": "1",
        "AVCI_IBVS_KOPRU_ATALET": "0.0",  # hayalet kutu KAPALI
    }, "B1 + hayalet kutu kapali"),

    ("C1_yavas", {
        "AVCI_GPS_FF_KORU": "1",
        "AVCI_IBVS_KOPRU_ATALET": "0.0",
        "AVCI_GPS_KAPANMA_MIN": "3.0",    # daha sakin kapanma
        "AVCI_GPS_V_MUTLAK": "24.0",
    }, "B2 + daha yavas/sakin kapanma (kullanici istegi)"),

    ("C2_yakin_istasyon", {
        "AVCI_GPS_FF_KORU": "1",
        "AVCI_IBVS_KOPRU_ATALET": "0.0",
        "AVCI_GPS_RANGE": "5.0",          # istasyon 5 m arkada
    }, "B2 + istasyon 7 -> 5 m (kilit kutusu buyusun)"),

    ("C3_dusuk_conf", {
        "AVCI_GPS_FF_KORU": "1",
        "AVCI_IBVS_KOPRU_ATALET": "0.0",
        "AVCI_VIS_CONF": "0.22",          # tespit orani icin
    }, "B2 + dedektor guven esigi 0.35 -> 0.22"),
]

TEMEL_ENV = {
    "AVCI_POSE": "0",             # kullanici: yalniz detection
    "AVCI_IZ_HZ": "50",           # 200 Hz GIL yukunu dusur
    "AVCI_GIL_HIZLI": "1",
    "AVCI_GPS_LOG_S": "20",
    "AVCI_GPS_LOG_MAX": "3000",
}


# ─────────────────────────────────────────────────────────────────────────
def gunluk(s):
    os.makedirs(CIK, exist_ok=True)
    z = time.strftime("%H:%M:%S")
    # ⚠ 2026-08-17: "★" (★) cp1252'ye kodlanamayip UnicodeEncodeError
    #   firlatti ve 3.5 saatlik kampanyayi OLDURDU. Bir gunluk satiri
    #   olcumu asla dusurmemeli -> kodlama hatasi yutulur, ASCII'ye duser.
    try:
        print("%s %s" % (z, s), flush=True)
    except UnicodeEncodeError:
        print(("%s %s" % (z, s)).encode("ascii", "replace").decode("ascii"),
              flush=True)
    try:
        with open(os.path.join(CIK, "kampanya.log"), "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (z, s))
    except Exception:
        pass


def _get(yol, zaman=4.0):
    with urllib.request.urlopen(SUNUCU + yol, timeout=zaman) as r:
        return json.loads(r.read().decode("utf-8"))


def _post(yol, govde, zaman=8.0):
    d = json.dumps(govde).encode("utf-8")
    q = urllib.request.Request(SUNUCU + yol, data=d,
                               headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(q, timeout=zaman) as r:
        return json.loads(r.read().decode("utf-8"))


def sunucu_ayakta():
    try:
        _get("/api/telemetry", 3.0)
        return True
    except Exception:
        return False


def oyun_baglandi(deneme=6, arali=1.5):
    """Oyun baglantisi -- TOLERANSLI.

    ⚠ 2026-08-17 OLCULDU: `connected` bayragi ARDISIK okumalarda gidip
      geliyor. Tek okumaya bakinca kampanya "sunucu oyuna baglandi (9 s)"
      dedikten hemen sonra "oyun hala bagli degil" deyip ayari ATLIYORDU;
      olcum hic kosamadi. Birkac saniye icinde BIR KEZ bile True gorursek
      bagliyiz. Ek kanit: aracin konumu degisiyorsa veri akiyor demektir.
    """
    onc = None
    for i in range(max(deneme, 1)):
        try:
            t = _get("/api/telemetry", 3.0)
        except Exception:
            t = None
        if t:
            if t.get("connected"):
                return True
            d = t.get("drone") or {}
            kon = (d.get("x"), d.get("y"), d.get("z"))
            if onc is not None and None not in kon and kon != onc:
                return True          # veri akiyor -> fiilen bagli
            onc = kon
        if i < deneme - 1:
            time.sleep(arali)
    return False


def sunucu_oldur():
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command",
                        "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
                        "Where-Object { $_.CommandLine -like '*main.py*' } | "
                        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"],
                       capture_output=True, timeout=40)
    except Exception as e:
        gunluk("sunucu oldurulemedi: %r" % (e,))
    t0 = time.time()
    while time.time() - t0 < 25 and sunucu_ayakta():
        time.sleep(1.0)


def sunucu_baslat(env_ek):
    """Sunucuyu YENI env ile baslat ve GERCEKTEN yeni surecin cevap verdigini DOGRULA.

    ⚠ 2026-08-17 DENETIMDE YAKALANDI: sunucu_oldur() eski sureci oldurememisti;
      yeni surecler portu alamayip 0 BAYTLIK log birakti, ama sunucu_ayakta()
      ESKI surece cevap verdiginden kampanya "sunucu ayakta (0 s)" yazip
      devam etti. Sonuc: K1/K2/K3 ayarlari ISTENEN env ile DEGIL, bayat
      sunucuyla kosuldu (loglarda pn_n=1.6 istenirken 0, conf 0.354 istenirken
      0.25) -> o blogun TUM sonuclari GECERSIZ.
      Artik uc kapi: (a) port gercekten bosalmis mi, (b) yeni surec yasiyor mu,
      (c) LOG DOSYASI DOLDU mu (0 bayt = surec portu alamadi demektir).
    """
    ev = dict(os.environ)
    ev.update(TEMEL_ENV)
    ev.update(env_ek)
    if sunucu_ayakta():
        gunluk("  ⚠ port hala dolu -> ikinci oldurme denemesi")
        sunucu_oldur()
        if sunucu_ayakta():
            gunluk("  ⚠ PORT BOSALMADI -> bu ayar ATLANIYOR (bayat sunucu riski)")
            return None
    log = os.path.join(CIK, "sunucu_%s.log" % time.strftime("%Y%m%d_%H%M%S"))
    f = open(log, "a", encoding="utf-8", errors="replace")
    p = subprocess.Popen([sys.executable, "-u", "main.py"], cwd=KOK, env=ev,
                         stdout=f, stderr=subprocess.STDOUT)
    t0 = time.time()
    while time.time() - t0 < 120:
        if sunucu_ayakta():
            try:
                boy = os.path.getsize(log)
            except OSError:
                boy = 0
            if boy < 200:
                gunluk("  ⚠ sunucu cevap veriyor ama log BOS (%d bayt) -> BAYAT "
                       "SUNUCU olabilir, ayar ATLANIYOR" % boy)
                try:
                    p.kill()
                except Exception:
                    pass
                return None
            gunluk("  sunucu ayakta (%.0f s, log %d bayt, pid %s)"
                   % (time.time() - t0, boy, p.pid))
            return p
        if p.poll() is not None:
            gunluk("  sunucu ANINDA DUSTU -> %s" % log)
            return None
        time.sleep(2.0)
    gunluk("  sunucu 120 s'de ayaga kalkmadi")
    return p


def gorev_kur():
    try:
        _post("/api/command", {"cmd": "vismode", "mode": "OTO"})
        time.sleep(0.4)
        _post("/api/command", {"cmd": "start_gercek"})
        return True
    except Exception as e:
        gunluk("  gorev kurulamadi: %r" % (e,))
        return False


# ─────────────────────────────────────────────────────────────────────────
#  OLCUM
# ─────────────────────────────────────────────────────────────────────────
DOGUM_IRTIFA_M, DOGUM_TOL, SICRAMA_M, VURUS_MENZIL_M = 49.1, 3.0, 40.0, 6.0


def durum():
    t = _get("/api/telemetry")
    d, h = t["drone"], t["target"]
    g, gd, gv = t["gorsel"], t["gudum"], t["gorev"]
    hb = gd.get("hibrit", {}) or {}
    ts = g.get("tespit") or {}
    hr = (t.get("debug") or {}).get("target_real") or {}
    hx, hy, hz = hr.get("x", h.get("x")), hr.get("y", h.get("y")), hr.get("z", h.get("z"))
    men = (math.dist((hx, hy, hz), (d["x"], d["y"], d["z"]))
           if None not in (hx, hy, hz) else float("nan"))
    return {"dx": d["x"], "dy": d["y"], "dz": d["z"], "d_hiz": d.get("speed_ms"),
            "d_yaw": d.get("yaw"), "d_roll": d.get("roll"), "d_pitch": d.get("pitch"),
            "hx": hx, "hy": hy, "hz": hz, "menzil": men,
            "irt_fark": (d["z"] - hz) if hz is not None else float("nan"),
            "faz": hb.get("faz"), "kilit": hb.get("kilit_sayac") or 0.0,
            "gecis": hb.get("gecis_sayisi") or 0,
            "tespit": bool(ts.get("tespit_mi")), "kopru": bool(g.get("kopru")),
            "vurus": bool(gv.get("vurus")), "en_yakin": gv.get("en_yakin_m"),
            "det_ms": (g.get("perf") or {}).get("det_ms"),
            "fps": (g.get("perf") or {}).get("fps"),
            "durum_yasa": gd.get("durum")}


def ayar_kos(ad, sure_s, iz_yaz):
    """SURE boyunca ol. Isinlanmalari kosu sinirlari olarak sayar."""
    t0 = time.perf_counter()
    onc = None
    kosu = {"vurus": 0, "olum": 0, "kosu": 0}
    men_hepsi, kilit_hepsi, det_hepsi, fps_hepsi, irt_hepsi = [], [], [], [], []
    tespit_n = kopru_n = gorsel_n = n = 0
    oyun_vurus = 0          # oyunun kendi <3 m mandali (respawn'dan BAGIMSIZ)
    onceki_vurus = False
    en_yakin_glob = float("inf")
    kosu_en_yakin = float("inf")
    kilit_max_glob = 0.0
    son_nabiz = 0.0
    hata_n = 0

    while time.perf_counter() - t0 < sure_s:
        tik = time.perf_counter()
        try:
            s = durum()
            hata_n = 0
        except Exception:
            hata_n += 1
            if hata_n == 5:
                gunluk("  telemetri kesildi, bekleniyor...")
            if hata_n > 60:
                gunluk("  telemetri 60 tik kesik -> oyun dustu mu diye bakiliyor")
                try:
                    if not OK.port_acik():
                        gunluk("  oyun GOREVDE DEGIL -> otomatik acilis")
                        if OK.oyunu_ac_ve_goreve_sok(gunluk):
                            gorev_kur()
                            hata_n = 0
                            time.sleep(3)
                            continue
                except Exception as e:
                    gunluk("  otomatik acilis hatasi: %r" % (e,))
                gunluk("  toparlanamadi -> ayar erken bitiriliyor")
                break
            time.sleep(1.0)
            continue

        n += 1
        m = s["menzil"]
        if m == m:
            men_hepsi.append(m)
            en_yakin_glob = min(en_yakin_glob, m)
            kosu_en_yakin = min(kosu_en_yakin, m)
        kilit_hepsi.append(s["kilit"])
        kilit_max_glob = max(kilit_max_glob, float(s["kilit"] or 0))
        if s["det_ms"]:
            det_hepsi.append(float(s["det_ms"]))
        if s["fps"]:
            fps_hepsi.append(float(s["fps"]))
        if s["irt_fark"] == s["irt_fark"]:
            irt_hepsi.append(s["irt_fark"])
        if s["vurus"] and not onceki_vurus:
            oyun_vurus += 1
            gunluk("    [%s] ★ OYUN VURUS MANDALI (mesafe<3 m) | o an menzil %.2f m"
                   % (ad, m if m == m else -1))
        onceki_vurus = s["vurus"]
        tespit_n += s["tespit"]
        # ⚠ NOT: asagidaki kopru sayaci telemetrinin gorsel.kopru'sunu okur ve o
        #   beyin.vis_kopru'dur -- bbox_ibvs'in HAYALET karesi DEGIL. Denetimde
        #   yakalandi: 22 kosunun 22'sinde 0.0 yazarken ham yasa logunda satirlarin
        #   %39-80'i kopru=1 idi. Gercek hayalet orani icin kampanya_ozet.py'nin
        #   hayalet_orani() fonksiyonunu kullan (bbox_ibvs CSV'sinden okur).
        kopru_n += s["kopru"]
        gorsel_n += str(s["faz"]).startswith("VIS")
        iz_yaz(ad, s)

        if onc is not None:
            adim = math.dist((s["dx"], s["dy"], s["dz"]),
                             (onc["dx"], onc["dy"], onc["dz"]))
            dogum = abs(s["dz"] - DOGUM_IRTIFA_M) < DOGUM_TOL
            if adim > SICRAMA_M and dogum:
                sm = onc["menzil"]
                vur = (sm == sm and sm < VURUS_MENZIL_M)
                kosu["kosu"] += 1
                kosu["vurus" if vur else "olum"] += 1
                gunluk("    [%s] kosu %d -> %s (sicrama menzili %.1f m, kosu en yakin %.2f m)"
                       % (ad, kosu["kosu"], "VURUS" if vur else "olum",
                          sm if sm == sm else -1, kosu_en_yakin))
                kosu_en_yakin = float("inf")
                try:
                    OK.tus_bas("e")
                except Exception:
                    pass
                time.sleep(1.0)
                gorev_kur()
                time.sleep(1.5)
                onc = None
                continue
        onc = s

        if time.perf_counter() - son_nabiz > 60.0:
            son_nabiz = time.perf_counter()
            kalan = (sure_s - (time.perf_counter() - t0)) / 60.0
            gunluk("    [%s] %4.1f dk kaldi | menzil %5.1f | faz %-6s | kilit %4.1f | "
                   "tespit %s | fps %s | det %s | en yakin %.2f"
                   % (ad, kalan, m if m == m else -1, s["faz"], s["kilit"],
                      "VAR" if s["tespit"] else "yok", s["fps"], s["det_ms"],
                      en_yakin_glob if en_yakin_glob < 1e8 else -1))

        kal = 0.1 - (time.perf_counter() - tik)
        if kal > 0:
            time.sleep(kal)

    p = lambda v, q: (sorted(v)[int(q * (len(v) - 1))] if v else None)
    o = lambda a, b: (100.0 * a / b) if b else 0.0
    return {
        "ayar": ad, "sure_dk": round(sure_s / 60.0, 1), "tik": n,
        "kosu": kosu["kosu"], "vurus": kosu["vurus"], "olum": kosu["olum"],
        "oyun_vurus": oyun_vurus,
        "vurus_orani_%": round(o(kosu["vurus"], kosu["kosu"]), 1),
        "en_yakin_m": round(en_yakin_glob, 2) if en_yakin_glob < 1e8 else "",
        "menzil_p10": round(p(sorted(men_hepsi), .10), 1) if men_hepsi else "",
        "menzil_med": round(p(sorted(men_hepsi), .50), 1) if men_hepsi else "",
        "alt3_%": round(o(sum(1 for x in men_hepsi if x < 3), len(men_hepsi)), 2),
        "alt5_%": round(o(sum(1 for x in men_hepsi if x < 5), len(men_hepsi)), 2),
        "alt10_%": round(o(sum(1 for x in men_hepsi if x < 10), len(men_hepsi)), 1),
        "alt15_%": round(o(sum(1 for x in men_hepsi if x < 15), len(men_hepsi)), 1),
        "kilit_max_s": round(kilit_max_glob, 2),
        "kilit_med": round(p(sorted(kilit_hepsi), .50), 2) if kilit_hepsi else "",
        "kilit5_%": round(o(sum(1 for x in kilit_hepsi if x >= 5.0), len(kilit_hepsi)), 1),
        "tespit_%": round(o(tespit_n, n), 1),
        "kopru_%": round(o(kopru_n, n), 1),
        "gorsel_%": round(o(gorsel_n, n), 1),
        "irt_fark_med": round(p(sorted(irt_hepsi), .50), 2) if irt_hepsi else "",
        "det_ms_med": round(p(sorted(det_hepsi), .50), 1) if det_hepsi else "",
        "det_ms_p95": round(p(sorted(det_hepsi), .95), 1) if det_hepsi else "",
        "fps_med": round(p(sorted(fps_hepsi), .50), 1) if fps_hepsi else "",
        "damga": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


ALANLAR = ["ayar", "sure_dk", "tik", "kosu", "vurus", "oyun_vurus", "olum", "vurus_orani_%",
           "en_yakin_m", "menzil_p10", "menzil_med", "alt3_%", "alt5_%", "alt10_%",
           "alt15_%", "kilit_max_s", "kilit_med", "kilit5_%", "tespit_%", "kopru_%",
           "gorsel_%", "irt_fark_med", "det_ms_med", "det_ms_p95", "fps_med", "damga"]

IZ_ALAN = ["ayar", "t", "dx", "dy", "dz", "d_hiz", "d_yaw", "d_roll", "d_pitch",
           "hx", "hy", "hz", "menzil", "irt_fark", "faz", "kilit", "gecis",
           "tespit", "kopru", "vurus", "det_ms", "fps", "durum_yasa"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dk", type=float, default=12.0, help="her ayar kac dakika")
    ap.add_argument("--recete", help="JSON recete yolu")
    ap.add_argument("--tur", type=int, default=99, help="receteyi kac kez donsun")
    a = ap.parse_args()

    os.makedirs(CIK, exist_ok=True)
    recete = VARSAYILAN
    if a.recete and os.path.exists(a.recete):
        with open(a.recete, encoding="utf-8") as f:
            recete = [(x["ad"], x["env"], x.get("not", "")) for x in json.load(f)]

    sonuc_yol = os.path.join(CIK, "kampanya_sonuc.csv")
    yeni = not os.path.exists(sonuc_yol)
    # ⚠ 2026-08-17: SEMA KAYMASI YASAGI. Dosya varken ALANLAR'a yeni bir sutun
    #   eklersem baslik ESKI kalir ve yeni satirlar hizasiz yazilir -- bir kez
    #   oldu ve ozet tablosu tamamen yanlis cikti (en_yakin 0.00, fps 61).
    #   Basligi oku; uyusmuyorsa dosyayi ARSIVLE ve temiz basla.
    if not yeni:
        try:
            with open(sonuc_yol, encoding="utf-8") as _f:
                _bas = next(csv.reader(_f), [])
            if _bas != ALANLAR:
                _ars = sonuc_yol.replace(".csv", "_eskisema_%s.csv"
                                         % time.strftime("%Y%m%d_%H%M%S"))
                os.replace(sonuc_yol, _ars)
                gunluk("  ⚠ sonuc semasi degismis -> eski dosya arsivlendi: %s"
                       % os.path.basename(_ars))
                yeni = True
        except Exception:
            pass
    sf = open(sonuc_yol, "a", newline="", encoding="utf-8")
    sw = csv.writer(sf)
    if yeni:
        sw.writerow(ALANLAR)
        sf.flush()

    izf = open(os.path.join(CIK, "kampanya_iz_%s.csv" % time.strftime("%Y%m%d_%H%M%S")),
               "w", newline="", encoding="utf-8")
    izw = csv.writer(izf)
    izw.writerow(IZ_ALAN)
    _t0 = time.time()

    def iz_yaz(ad, s):
        izw.writerow([ad, round(time.time() - _t0, 2)] + [s.get(k) for k in IZ_ALAN[2:]])

    gunluk("=" * 78)
    gunluk("KAMPANYA basladi | %d ayar x %.0f dk x %d tur" % (len(recete), a.dk, a.tur))

    try:
        for tur in range(1, a.tur + 1):
            for ad, env, notu in recete:
                etiket = "%s#t%d" % (ad, tur)
                gunluk("-" * 78)
                gunluk("AYAR %s | %s" % (etiket, notu))
                gunluk("  env: %s" % json.dumps(env))
                sunucu_oldur()
                p = sunucu_baslat(env)
                if p is None or not sunucu_ayakta():
                    gunluk("  sunucu kalkmadi -> bu ayar ATLANDI")
                    continue
                if not oyun_baglandi():
                    # ⚠ 2026-08-17: kullanicinin KAYDEDILEN dizisinden ogrenilen
                    #   uyarlanabilir acilis. Test edildi: oyun kapaliyken
                    #   51 saniyede goreve girdi (baslik tiki -> harita tiki -> E).
                    #   Eski "kor tus dizisi" yolu yedek olarak duruyor.
                    gunluk("  OYUN BAGLI DEGIL -> otomatik acilis deneniyor")
                    try:
                        OK.oyunu_ac_ve_goreve_sok(gunluk)
                    except Exception as e:
                        gunluk("  otomatik acilis hatasi: %r" % (e,))
                    # ⚠ 2026-08-17: PORT ACILMASI ile SUNUCUNUN BAGLANMASI ayni
                    #   sey DEGIL. Otomatik acilis portu 23 s'de acti ama
                    #   kampanya tek seferlik kontrol yapip ayari ATLADI.
                    #   Sunucunun SDK'ya yeniden baglanmasi icin sure taniyoruz.
                    _t = time.time()
                    while time.time() - _t < 60 and not oyun_baglandi():
                        time.sleep(3)
                    if oyun_baglandi():
                        gunluk("  sunucu oyuna baglandi (%.0f s)" % (time.time() - _t))
                    else:
                        try:
                            OK.kurtar(oyun_baglandi, gunluk,
                                      sadece_tus=OK.oyun_calisiyor())
                        except Exception as e:
                            gunluk("  yedek kurtarma hatasi: %r" % (e,))
                    if not oyun_baglandi():
                        gunluk("  oyun hala bagli degil -> 60 s bekle, sonrakine gec")
                        time.sleep(60)
                        continue
                gorev_kur()
                time.sleep(3.0)
                r = ayar_kos(etiket, a.dk * 60.0, iz_yaz)
                sw.writerow([r.get(k, "") for k in ALANLAR])
                sf.flush()
                izf.flush()
                gunluk("  SONUC %s: kosu %d | RESPAWN-VURUS %d | OYUN-VURUS %d | en yakin %s m | "
                       "kilit_max %s s | <5m %%%s | tespit %%%s | vis_kopru %%%s"
                       " (HAYALET DEGIL -> kampanya_ozet.py) | fps %s"
                       % (etiket, r["kosu"], r["vurus"], r["oyun_vurus"],
                          r["en_yakin_m"], r["kilit_max_s"], r["alt5_%"],
                          r["tespit_%"], r["kopru_%"], r["fps_med"]))
    except KeyboardInterrupt:
        gunluk("kullanici durdurdu.")
    finally:
        sf.close()
        izf.close()


if __name__ == "__main__":
    main()

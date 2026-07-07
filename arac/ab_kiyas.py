# -*- coding: utf-8 -*-
"""
================================================================================
GELISTIRME/DOGRULAMA ARACI - gorev ucusunda ve degerlendirme kosusunda
kullanilmaz. (A/B guduum kiyasi; teslim paketine girmez.)
================================================================================
AB KIYAS - iki branch'in gorev performansini AYNI protokolle olcup kiyaslar
================================================================================
AMAC (CLAUDE.md "BEKLEYEN IS" 2026-07-07): main'in PNG gorsel gudumu ile
yarisma-pipeline'in APN/OIPN+IBVS hattindan hangisinin gorevi daha iyi
tamamladigina VERIyle karar vermek. Silme/merge karari bu olcumden SONRA,
karar dokumaniyla verilir ("kazanan gorsel YASA secilir"; kaybedenin
sartname-zorunlu parcalari kazanana tasinir).

PROTOKOL (kosu basina; zombilesme kurali geregi her kosu TAZE oyunla):
  1) oyunu ac (kosu_yonetici) -> ilgili KOKUN web/server.py'sini subprocess
     olarak baslat (PYTHONPATH=kok; gercek gorev yazilimi, degisiklik yok),
  2) PLAY bekle: menu otomasyonu best-effort (klavye, TCP degil); tutmazsa
     insan PLAY/FLY'a basar, arac telemetriyi HTTP'den otomatik algilar,
  3) POST /api/command {"cmd":"start"} -> ~5 Hz GET /api/telemetry kaydi
     (JSONL; 'olaylar' yalniz YENI olay olarak yazilir, sisirme yok),
  4) bitis: gorev.basari (+birkac sn kuyruk) | --sure timeout | kopma,
  5) POST stop -> server kapat -> OYUNU KAPAT (arm'li kosu -> taze oyun).

OLCUM SIMETRISI: sim debug truth ACIKKEN iki branch'te de VURUS/en_yakin
latch'i GERCEK 3B mesafeyle olculur (bizde web/dev_truth.py DEV-citli yolu,
main'de dogrudan _mesafe_olc). Truth kapaliysa iki taraf da J-temiz'e duser;
kullanilan kaynak VURUS olay metninden ayiklanip raporda gosterilir.
Gorsel faz sinyali branch-bagimsiz: gorsel.gps_kesildi (adlar farkli:
bizde GORSEL_TAKIP ailesi, main'de GORSEL_GUDUM).

KULLANIM:
  # main olcum worktree'si (BIR KEZ; 2026-07-07'de olusturuldu):
  #   git worktree add ..\\avci-ab-main origin/main
  python arac/ab_kiyas.py kos --etiket pipeline --n 5
  python arac/ab_kiyas.py kos --etiket main --kok ..\\avci-ab-main --n 5
  python arac/ab_kiyas.py rapor --a pipeline --b main
Kayitlar: veri/ab/<etiket>/kosu_*.jsonl (+server_*.log). Rapor: veri/ab/rapor_*.json
================================================================================
"""
import argparse
import glob
import json
import os
import re
import statistics
import subprocess
import sys
import time
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJ_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _PROJ_ROOT)
sys.path.insert(0, _HERE)

TABAN = "http://127.0.0.1:8000"          # her iki branch'te WEB_PORT=8000
AB_DIR = os.path.join(_PROJ_ROOT, "veri", "ab")
TIK_S = 0.2                              # kayit temposu (~5 Hz)
BASARI_KUYRUK_S = 4.0                    # basari latch'inden sonra ek kayit
KOPMA_TIK = 25                           # ardisik HTTP hatasi -> server koptu (~5 sn)


# ----------------------------------------------------------------------------
#  HTTP yardimcilari (stdlib; ek bagimlilik yok)
# ----------------------------------------------------------------------------
def _http_get(yol, timeout=1.5):
    with urllib.request.urlopen(TABAN + yol, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _http_post(yol, veri, timeout=2.0):
    b = json.dumps(veri).encode("utf-8")
    istek = urllib.request.Request(TABAN + yol, data=b,
                                   headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(istek, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


# ----------------------------------------------------------------------------
#  Server yasam dongusu (hedef kokun GERCEK gorev yazilimi)
# ----------------------------------------------------------------------------
def server_baslat(kok, log_yolu):
    srv = os.path.join(kok, "web", "server.py")
    if not os.path.isfile(srv):
        raise SystemExit("web/server.py yok: %s\n(main icin: git worktree add "
                         "..\\avci-ab-main origin/main)" % kok)
    ortam = os.environ.copy()                 # 'from sdk import...' calissin diye
    ortam["PYTHONPATH"] = kok + os.pathsep + ortam.get("PYTHONPATH", "")
    logf = open(log_yolu, "w", encoding="utf-8", errors="replace")
    p = subprocess.Popen([sys.executable, srv], cwd=kok, env=ortam,
                         stdout=logf, stderr=subprocess.STDOUT)
    return p, logf


def server_kapat(p, logf):
    try:
        p.terminate()
        p.wait(timeout=6)
    except Exception:
        try:
            p.kill()
        except Exception:
            pass
    try:
        logf.close()
    except Exception:
        pass


# ----------------------------------------------------------------------------
#  PLAY bekleme - kosu_yonetici deseni, ama TCP'ye DOKUNMADAN (tek TCP server'da;
#  biz yalniz HTTP telemetriyi izler + klavye otomasyonu deneriz).
# ----------------------------------------------------------------------------
def play_bekle(sure_s=180.0, oto_play=True):
    import kosu_yonetici as ky
    t0 = time.perf_counter()
    ayakta = False
    while time.perf_counter() - t0 < 30.0:    # 1) server HTTP ayaga kalksin
        try:
            _http_get("/api/telemetry")
            ayakta = True
            break
        except Exception:
            time.sleep(0.5)
    if not ayakta:
        print("[AB] Server HTTP acilmadi (log dosyasina bak).")
        return False
    if oto_play:                              # 2) menu otomasyonu (best-effort)
        ky._play_otomasyonu()
    istem = False
    while time.perf_counter() - t0 < sure_s:  # 3) baglanti + telemetri bekle
        try:
            t = _http_get("/api/telemetry")
            d = t.get("drone") or {}
            if t.get("connected") and any(abs(float(d.get(k) or 0.0)) > 1e-6
                                          for k in ("x", "y", "z")):
                print("[AB] Telemetri basladi (+%.0f sn)." % (time.perf_counter() - t0))
                return True
        except Exception:
            pass
        if not istem and time.perf_counter() - t0 > 12.0:
            istem = True
            print("      >>> OTOMASYON TUTMADIYSA: OYUNDA PLAY / FLY'a BAS <<<"
                  "  (arac otomatik algilar, bir sey yazma)")
        time.sleep(0.5)
    print("[AB] Telemetri gelmedi (PLAY'e gecilmedi?).")
    return False


# ----------------------------------------------------------------------------
#  Kayit dongusu: her tik tam telemetri (olaylar -> yalniz YENI olaylar)
# ----------------------------------------------------------------------------
def kosu_kaydet(dosya, sure_s):
    t0 = time.perf_counter()
    son_olay_id = 0
    hata_ust_uste = 0
    kopuk_s = None
    basari_t = None
    durum = "TIMEOUT"
    with open(dosya, "w", encoding="utf-8") as f:
        while True:
            t_rel = time.perf_counter() - t0
            if t_rel > sure_s:
                durum = "TIMEOUT"
                break
            try:
                t = _http_get("/api/telemetry")
                hata_ust_uste = 0
            except Exception:
                hata_ust_uste += 1
                if hata_ust_uste >= KOPMA_TIK:
                    durum = "SERVER_KOPTU"
                    break
                time.sleep(TIK_S)
                continue
            satir = dict(t)
            satir["t"] = round(t_rel, 2)
            olaylar = satir.pop("olaylar", None) or []
            yeni = [o for o in olaylar if int(o.get("id", 0)) > son_olay_id]
            if yeni:
                son_olay_id = max(int(o.get("id", 0)) for o in yeni)
                satir["olay_yeni"] = yeni
            f.write(json.dumps(satir, ensure_ascii=False) + "\n")
            if not t.get("connected"):
                kopuk_s = t_rel if kopuk_s is None else kopuk_s
                if t_rel - kopuk_s > 15.0:
                    durum = "OYUN_KOPTU"
                    break
            else:
                kopuk_s = None
            g = t.get("gorev") or {}
            if g.get("basari") and basari_t is None:
                basari_t = t_rel
                print("[AB] GOREV BASARILI (+%.1f sn) - kuyruk kaydi..." % t_rel)
            if basari_t is not None and t_rel - basari_t >= BASARI_KUYRUK_S:
                durum = "BASARI"
                break
            time.sleep(TIK_S)
    return durum


# ----------------------------------------------------------------------------
#  KOS alt komutu - N kosuluk seri (her kosu taze oyun + taze server)
# ----------------------------------------------------------------------------
def kos(arg):
    import kosu_yonetici as ky
    kok = os.path.abspath(arg.kok)
    cikti = os.path.join(AB_DIR, arg.etiket)
    os.makedirs(cikti, exist_ok=True)
    print("=" * 68)
    print(" AB KIYAS - etiket: %s | kok: %s | %d kosu | sure %d sn"
          % (arg.etiket, kok, arg.n, arg.sure))
    print("=" * 68)
    sonuclar = []
    for i in range(arg.n):
        print("\n--- KOSU %d/%d ---" % (i + 1, arg.n))
        if not (arg.oyun_hazir and i == 0 and ky.oyun_calisiyor_mu()):
            ok, hata = ky.oyunu_baslat()
            if not ok:
                print("[HATA] %s" % hata)
                break
        damga = time.strftime("%Y%m%d_%H%M%S")
        p, logf = server_baslat(kok, os.path.join(cikti, "server_%s.log" % damga))
        dosya = os.path.join(cikti, "kosu_%s.jsonl" % damga)
        durum = "PLAY_YOK"
        try:
            if play_bekle(oto_play=not arg.oto_play_kapali):
                _http_post("/api/command", {"cmd": "start"})
                print("[AB] Gorev basladi; kayit: %s" % os.path.basename(dosya))
                durum = kosu_kaydet(dosya, arg.sure)
                try:
                    _http_post("/api/command", {"cmd": "stop"})
                except Exception:
                    pass
        except KeyboardInterrupt:
            durum = "IPTAL"
            print("\n[AB] Kullanici iptali - kosu kapatiliyor.")
        finally:
            server_kapat(p, logf)
            ky.oyunu_kapat()                  # zombilesme: arm'li kosu -> taze oyun
        m = analiz_kosu(dosya) if os.path.isfile(dosya) else None
        kayit = {"damga": damga, "durum": durum, "metrik": m}
        sonuclar.append(kayit)
        with open(os.path.join(cikti, "ozet.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(kayit, ensure_ascii=False) + "\n")
        if m:
            print("[AB] %s | basari=%s vurus_t=%s en_yakin=%s m (%s) kilit=%s s"
                  % (durum, m["basari"], _f(m["vurus_t_s"]), _f(m["en_yakin_m"]),
                     m["mesafe_kaynak"] or "?", _f(m["kilit_kum_max_s"])))
        else:
            print("[AB] %s | metrik yok (kayit bos/olusmadi)" % durum)
        if durum == "IPTAL":
            break
        time.sleep(2.0)
    basarili = sum(1 for s in sonuclar if s["metrik"] and s["metrik"]["basari"])
    ky.kosu_bitti_bildir("ab-kiyas %s: %d kosu, %d basari"
                         % (arg.etiket, len(sonuclar), basarili))
    return 0


# ----------------------------------------------------------------------------
#  ANALIZ - kosu JSONL -> metrikler (branch-bagimsiz adapter: .get zinciri)
# ----------------------------------------------------------------------------
def _yukle(dosya):
    satirlar = []
    with open(dosya, encoding="utf-8") as f:
        for hat in f:
            hat = hat.strip()
            if hat:
                try:
                    satirlar.append(json.loads(hat))
                except Exception:
                    pass                      # yarim satir (kopma ani) atla
    return satirlar


def analiz_kosu(dosya):
    """Tek kosu JSONL -> metrik sozlugu | None (bos kayit)."""
    satirlar = _yukle(dosya)
    if not satirlar:
        return None
    vurus_t = None
    basari = False
    en_yakin = None
    kaynak = None
    gorsel_t = None
    kilit_max = None
    onceki_aktif = False
    kayip = 0
    idler = set()
    kes_tik = 0
    kes_epizot = 0
    onceki_kes = False
    for s in satirlar:
        t = float(s.get("t", 0.0))
        g = s.get("gorev") or {}
        if g.get("vurus") and vurus_t is None:
            vurus_t = t
        if g.get("basari"):
            basari = True
        if g.get("en_yakin_m") is not None:
            en_yakin = float(g["en_yakin_m"])          # latch monoton azalir
        gs = s.get("gorsel") or {}
        if gorsel_t is None and gs.get("gps_kesildi"):
            gorsel_t = t                               # gorsel faza ilk gecis
        kl = gs.get("kilit") or {}
        if kl.get("kumulatif_sn") is not None:         # main'de yok -> None kalir
            kilit_max = max(kilit_max or 0.0, float(kl["kumulatif_sn"]))
        tk = s.get("takip") or {}
        aktif = bool(tk.get("aktif"))
        if onceki_aktif and not aktif:
            kayip += 1
        onceki_aktif = aktif
        if tk.get("id") is not None:
            idler.add(tk["id"])
        kes = bool((s.get("gnss") or {}).get("kesinti"))
        kes_tik += 1 if kes else 0
        if kes and not onceki_kes:
            kes_epizot += 1
        onceki_kes = kes
        for o in s.get("olay_yeni") or []:
            e = re.search(r"VURUS!.*\((\w+) kaynak\)", str(o.get("m", "")))
            if e:
                kaynak = e.group(1)                    # gercek | temiz
    return {
        "dosya": os.path.basename(dosya), "sure_s": float(satirlar[-1].get("t", 0.0)),
        "basari": basari, "vurus": vurus_t is not None, "vurus_t_s": vurus_t,
        "en_yakin_m": en_yakin, "mesafe_kaynak": kaynak,
        "gorsel_gecis_t_s": gorsel_t, "kilit_kum_max_s": kilit_max,
        "takip_kayip": kayip, "takip_id_sayisi": len(idler),
        "gnss_kesinti_oran": kes_tik / float(len(satirlar)),
        "gnss_kesinti_epizot": kes_epizot,
    }


def analiz_etiket(etiket):
    desen = os.path.join(AB_DIR, etiket, "kosu_*.jsonl")
    dosyalar = sorted(glob.glob(desen))
    metrikler = [analiz_kosu(d) for d in dosyalar]
    return [m for m in metrikler if m is not None]


# ----------------------------------------------------------------------------
#  RAPOR alt komutu - iki etiketin kiyas tablosu (karar VERMEZ; veri sunar)
# ----------------------------------------------------------------------------
def _f(v, bicim="%.1f"):
    return "-" if v is None else (bicim % v)


def _med(degerler):
    d = [v for v in degerler if v is not None]
    return statistics.median(d) if d else None


def _ozet(ms):
    n = len(ms)
    return {
        "n": n,
        "basari": sum(1 for m in ms if m["basari"]),
        "vurus": sum(1 for m in ms if m["vurus"]),
        "vurus_t_med_s": _med([m["vurus_t_s"] for m in ms]),
        "en_yakin_med_m": _med([m["en_yakin_m"] for m in ms]),
        "gorsel_gecis_med_s": _med([m["gorsel_gecis_t_s"] for m in ms]),
        "kilit_kum_med_s": _med([m["kilit_kum_max_s"] for m in ms]),
        "takip_kayip_med": _med([float(m["takip_kayip"]) for m in ms]),
        "takip_id_med": _med([float(m["takip_id_sayisi"]) for m in ms]),
        "kesinti_oran_med": _med([m["gnss_kesinti_oran"] for m in ms]),
        "kaynaklar": sorted({m["mesafe_kaynak"] for m in ms if m["mesafe_kaynak"]}),
    }


def rapor(arg):
    A, B = analiz_etiket(arg.a), analiz_etiket(arg.b)
    if not A or not B:
        print("Eksik veri: %s=%d kosu, %s=%d kosu (once 'kos' calistir)."
              % (arg.a, len(A), arg.b, len(B)))
        return 1
    oA, oB = _ozet(A), _ozet(B)
    G = 26
    print("\n" + "=" * 78)
    print(" AB KIYAS RAPORU - %s (n=%d)  vs  %s (n=%d)" % (arg.a, oA["n"], arg.b, oB["n"]))
    print("=" * 78)
    satirlar = [
        ("gorev basarisi",        "%d/%d" % (oA["basari"], oA["n"]), "%d/%d" % (oB["basari"], oB["n"])),
        ("vurus latch",           "%d/%d" % (oA["vurus"], oA["n"]),  "%d/%d" % (oB["vurus"], oB["n"])),
        ("vurus suresi med (s)",  _f(oA["vurus_t_med_s"]),           _f(oB["vurus_t_med_s"])),
        ("en yakin med (m)",      _f(oA["en_yakin_med_m"], "%.2f"),  _f(oB["en_yakin_med_m"], "%.2f")),
        ("gorsel gecis med (s)",  _f(oA["gorsel_gecis_med_s"]),      _f(oB["gorsel_gecis_med_s"])),
        ("kilit kumulatif med (s)", _f(oA["kilit_kum_med_s"]),       _f(oB["kilit_kum_med_s"])),
        ("takip kayip med (adet)", _f(oA["takip_kayip_med"]),        _f(oB["takip_kayip_med"])),
        ("takip ID med (adet)",   _f(oA["takip_id_med"]),            _f(oB["takip_id_med"])),
        ("GNSS kesinti orani med", _f(oA["kesinti_oran_med"], "%.2f"), _f(oB["kesinti_oran_med"], "%.2f")),
        ("mesafe kaynagi",        ",".join(oA["kaynaklar"]) or "-",  ",".join(oB["kaynaklar"]) or "-"),
    ]
    print(" %-*s | %-18s | %-18s" % (G, "metrik", arg.a, arg.b))
    print(" " + "-" * (G + 42))
    for ad, a, b in satirlar:
        print(" %-*s | %-18s | %-18s" % (G, ad, a, b))
    print("\n NOT: mesafe kaynagi 'gercek' = sim debug truth (3B); 'temiz' = J-temiz")
    print(" kestirim. Iki etikette kaynak FARKLIYSA en-yakin kiyasi temkinli okunmali.")
    print(" Kilit kumulatif main telemetrisinde yoksa '-' gorunur (yasa farki degil,")
    print(" gosterge farki). Karar: kazanan GORSEL YASA - karar dokumaniyla.")
    for etiket, ms in ((arg.a, A), (arg.b, B)):
        print("\n KOSULAR - %s:" % etiket)
        for m in ms:
            print("  %s | basari=%-5s vurus_t=%-6s en_yakin=%-6s (%s) kilit=%-5s "
                  "kayip=%d id=%d kesinti=%.2f"
                  % (m["dosya"], m["basari"], _f(m["vurus_t_s"]),
                     _f(m["en_yakin_m"], "%.2f"), m["mesafe_kaynak"] or "?",
                     _f(m["kilit_kum_max_s"]), m["takip_kayip"],
                     m["takip_id_sayisi"], m["gnss_kesinti_oran"]))
    os.makedirs(AB_DIR, exist_ok=True)
    ciktida = os.path.join(AB_DIR, time.strftime("rapor_%Y%m%d_%H%M%S.json"))
    with open(ciktida, "w", encoding="utf-8") as f:
        json.dump({"a": {"etiket": arg.a, "ozet": oA, "kosular": A},
                   "b": {"etiket": arg.b, "ozet": oB, "kosular": B}},
                  f, ensure_ascii=False, indent=2)
    print("\n Rapor JSON: %s\n" % ciktida)
    return 0


def main():
    ap = argparse.ArgumentParser(description="A/B guduum kiyasi (kos + rapor)")
    alt = ap.add_subparsers(dest="komut", required=True)
    k = alt.add_parser("kos", help="N kosuluk olcum serisi (taze oyun + gercek server)")
    k.add_argument("--etiket", required=True, help="kayit etiketi (or. pipeline / main)")
    k.add_argument("--kok", default=_PROJ_ROOT,
                   help="calistirilacak repo koku (main icin worktree yolu)")
    k.add_argument("--n", type=int, default=5, help="kosu sayisi (vars. 5)")
    k.add_argument("--sure", type=float, default=240.0, help="kosu ust suresi sn (vars. 240)")
    k.add_argument("--oyun-hazir", action="store_true",
                   help="ILK kosuda oyun zaten acik/PLAY'de (baslatma)")
    k.add_argument("--oto-play-kapali", action="store_true",
                   help="menu klavye otomasyonunu deneme (elle PLAY'e bas)")
    r = alt.add_parser("rapor", help="iki etiketin kiyas tablosu")
    r.add_argument("--a", required=True, help="birinci etiket")
    r.add_argument("--b", required=True, help="ikinci etiket")
    arg = ap.parse_args()
    sys.exit(kos(arg) if arg.komut == "kos" else rapor(arg))


if __name__ == "__main__":
    main()

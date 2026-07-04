# -*- coding: utf-8 -*-
"""
================================================================================
GELISTIRME/DOGRULAMA ARACI — gorev ucusunda ve degerlendirme kosusunda
kullanilmaz. (Prova kanit kaydedici; teslim paketine GIRMEZ.)
================================================================================
PROVA KARE KAYDEDICI — sim video 10-kalem OTOMATIK isaretleme (yakalama katmani)
================================================================================
FSM provasi sirasinda calisir. /api/telemetry'yi ~8 Hz yoklar; OLAY tetikli TAM
ARAYUZ (tarayici penceresi) karesi + her 10 sn GENEL kare kaydeder. Kareler
veri/prova_kareleri/<olay>_<ts>.png (+ _50.png = %50 kopya, YouTube sikistirma
vekili). Olaylar veri/prova_kareleri/olaylar.json'a yazilir.

Bu arac YALNIZ yakalar; "okunuyor mu" degerlendirmesi (kare okuma) insan/asistan
isidir. Tarayici penceresini PrintWindow ile yakalar (occlusion-proof; oyunla
AYNI katman, detection.pencere_yakala.pencere_icerik_bgr) -> siyah donerse mss
pencere-dikdortgenine, o da olmazsa birincil monitore duser.

OLAYLAR (sartname kalem eslemesi):
  ILK_TESPIT      kalem 4        : gorsel.tespit None -> dolu (ilk kez)
  COAST_BASLADI   kalem 7        : track.tespit_mi True->False (veya durum LOST)
  YENIDEN_TESPIT  kalem 7        : coast/LOST -> CONFIRMED + tespit_mi True
  FSM_GECIS_<X>   kalem 9        : gorsel.durum degisti (ANGAJMAN dahil)
  GOREV_SONU      kalem 10       : gorsel.gorev_sonu.basarili True
  GENEL           kalem 1-2-3-5-6-8 : her 10 sn (tum panolar okunur kare)

KULLANIM:
  python arac/prova_kaydedici.py           # CANLI yakalama (provada; arka planda calistir)
  python arac/prova_kaydedici.py --rapor    # kosu SONRASI: uretildi tablosu (CSV + olaylar)
  python arac/prova_kaydedici.py --sure 600 # azami sure sn (varsayilan 900)
================================================================================
"""
import argparse
import csv
import glob
import json
import os
import sys
import time
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJ_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _PROJ_ROOT)

_VERI = os.path.join(_PROJ_ROOT, "veri")
_KARE_DIR = os.path.join(_VERI, "prova_kareleri")
_OLAY_JSON = os.path.join(_KARE_DIR, "olaylar.json")
_URL = "http://127.0.0.1:8000/api/telemetry"
_TARAYICI_EXE = ("brave", "chrome", "msedge", "firefox", "opera", "vivaldi")


# ----------------------------------------------------------------------------
#  Telemetri + tarayici penceresi
# ----------------------------------------------------------------------------
def _telemetri_al(url, zaman_asimi=1.0):
    try:
        with urllib.request.urlopen(url, timeout=zaman_asimi) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None


def _tarayici_pencere_bul():
    """Arayuz sekmesini gosteren TARAYICI penceresini bul -> (hwnd, baslik).
    Baslik 'yer kontrol' icermeli (sayfa <title>). Bulamazsa (None, None)."""
    try:
        import pygetwindow as gw
    except Exception:
        return None, None
    try:
        from detection.pencere_yakala import _pencere_pid, _surec_adi
    except Exception:
        _pencere_pid = _surec_adi = None
    for w in gw.getAllWindows():
        t = (w.title or "").strip()
        tl = t.lower()
        if not t or getattr(w, "width", 0) < 200:
            continue
        if "yer kontrol" in tl or ("avc" in tl and "drone" in tl):
            hwnd = getattr(w, "_hWnd", None)
            # Tarayici sureci mi (dogrulama; psutil varsa)
            if _pencere_pid and _surec_adi and hwnd:
                ad = _surec_adi(_pencere_pid(hwnd))
                if ad and not any(b in ad for b in _TARAYICI_EXE):
                    continue
            return hwnd, t
    return None, None


def _pencere_rect(hwnd):
    import ctypes
    r = (ctypes.c_long * 4)()
    if ctypes.windll.user32.GetWindowRect(int(hwnd), ctypes.byref(r)):
        return int(r[0]), int(r[1]), int(r[2] - r[0]), int(r[3] - r[1])
    return None


def _one_getir(hwnd):
    try:
        import ctypes
        u32 = ctypes.windll.user32
        if u32.IsIconic(int(hwnd)):
            u32.ShowWindow(int(hwnd), 9)          # SW_RESTORE
        u32.SetForegroundWindow(int(hwnd))
        return True
    except Exception:
        return False


def _mss_rect_bgr(bolge):
    import mss
    import numpy as np
    with mss.mss() as sct:
        if bolge:
            left, top, w, h = bolge
            bbox = {"left": left, "top": top, "width": w, "height": h}
        else:
            bbox = sct.monitors[1]
        raw = sct.grab(bbox)
        fr = np.frombuffer(raw.bgra, dtype=np.uint8).reshape(raw.height, raw.width, 4)
        return fr[:, :, :3].copy()


def _kare_yakala(hwnd):
    """TAM ARAYUZ (tarayici) BGR karesi + kaynak adi. PrintWindow -> mss-rect ->
    birincil monitor. hwnd None ise dogrudan tam ekran."""
    if hwnd is not None:
        try:
            from detection.pencere_yakala import pencere_icerik_bgr
            fr = pencere_icerik_bgr(hwnd)
            if fr is not None:
                return fr, "PrintWindow (tarayici penceresi)"
        except Exception:
            pass
        rect = _pencere_rect(hwnd)
        if rect:
            try:
                return _mss_rect_bgr(rect), "mss (tarayici dikdortgeni; pencere onde olmali)"
            except Exception:
                pass
    return _mss_rect_bgr(None), "mss (TUM EKRAN; son care)"


def _kaydet(bgr, olay, ts_str):
    """<olay>_<ts>.png (tam) + _50.png (%50 vekil). (tam_yol, kucuk_yol) doner."""
    import numpy as np
    try:
        import cv2
    except Exception:
        cv2 = None
    os.makedirs(_KARE_DIR, exist_ok=True)
    ad = "%s_%s" % (olay, ts_str)
    tam = os.path.join(_KARE_DIR, ad + ".png")
    kucuk = os.path.join(_KARE_DIR, ad + "_50.png")
    if cv2 is not None:
        cv2.imwrite(tam, bgr)
        h, w = bgr.shape[:2]
        cv2.imwrite(kucuk, cv2.resize(bgr, (max(1, w // 2), max(1, h // 2))))
    else:
        from PIL import Image
        Image.fromarray(bgr[:, :, ::-1]).save(tam)                 # BGR->RGB
        im = Image.fromarray(bgr[:, :, ::-1])
        im.resize((max(1, im.width // 2), max(1, im.height // 2))).save(kucuk)
    return tam, kucuk


# ----------------------------------------------------------------------------
#  Olay tespiti (telemetri gecisleri)
# ----------------------------------------------------------------------------
def _olaylari_bul(prev, cur):
    olaylar = []
    g = cur.get("gorsel") or {}
    gp = (prev or {}).get("gorsel") or {}
    if g.get("tespit") is not None and gp.get("tespit") is None:
        olaylar.append("ILK_TESPIT")
    tr = g.get("track") or {}
    trp = gp.get("track") or {}
    tm, tmp = tr.get("tespit_mi"), trp.get("tespit_mi")
    du, dup = tr.get("durum"), trp.get("durum")
    if (tmp is True and tm is False) or (du == "LOST" and dup not in (None, "LOST")):
        olaylar.append("COAST_BASLADI")
    if (tmp is False and tm is True) or (dup == "LOST" and du == "CONFIRMED"):
        olaylar.append("YENIDEN_TESPIT")
    d, dp = g.get("durum"), gp.get("durum")
    if d != dp and dp is not None:
        olaylar.append("FSM_GECIS_%s" % d)
    gs = (g.get("gorev_sonu") or {}).get("basarili")
    gsp = (gp.get("gorev_sonu") or {}).get("basarili")
    if gs and not gsp:
        olaylar.append("GOREV_SONU")
    return olaylar


def _ts():
    lt = time.localtime()
    ms = int((time.time() % 1) * 1000)
    return time.strftime("%H%M%S", lt) + "_%03d" % ms


def canli(url, hz, genel_sn, sure_max):
    """Canli yakalama dongusu. Ctrl+C / sure_max / GOREV_SONU+grace ile biter."""
    os.makedirs(_KARE_DIR, exist_ok=True)
    print("=" * 68)
    print(" PROVA KARE KAYDEDICI (canli) — %s" % url)
    print("=" * 68)
    hwnd, baslik = _tarayici_pencere_bul()
    if hwnd:
        _one_getir(hwnd)
        print(" tarayici penceresi: '%s'  (bir kez one getirildi)" % baslik)
    else:
        print(" [UYARI] arayuz tarayici penceresi bulunamadi (baslik 'yer kontrol'?).")
        print("         Tam-ekran yakalanacak; arayuzu acik/onde tut.")
    print(" kayit dizini: %s" % _KARE_DIR)
    print(" olaylar: ILK_TESPIT / COAST_BASLADI / YENIDEN_TESPIT / FSM_GECIS_* /")
    print("          GOREV_SONU + her %d sn GENEL. Durdurmak icin Ctrl+C." % genel_sn)

    olay_kayit = []
    if os.path.isfile(_OLAY_JSON):                    # onceki kosuyu ARSIVLE (uzerine yazma)
        try:
            os.replace(_OLAY_JSON, _OLAY_JSON.replace(".json", "_%s.json" % _ts()))
        except OSError:
            pass
    prev = None
    son_genel = 0.0
    t0 = time.perf_counter()
    bitis_t = None
    ilk_kaynak_yazildi = False
    try:
        while True:
            t = time.perf_counter()
            cur = _telemetri_al(url)
            if cur is None:
                time.sleep(1.0 / hz)
                continue
            tetik = [] if prev is None else _olaylari_bul(prev, cur)
            if t - son_genel >= genel_sn:
                tetik.append("GENEL")
                son_genel = t
            for olay in tetik:
                ts = _ts()
                try:
                    bgr, kaynak = _kare_yakala(hwnd)
                    tam, kucuk = _kaydet(bgr, olay, ts)
                except Exception as e:
                    print(" [HATA] kare yakalanamadi (%s): %s" % (olay, e))
                    continue
                if not ilk_kaynak_yazildi:
                    print(" kare kaynagi -> %s" % kaynak)
                    ilk_kaynak_yazildi = True
                kayit = {"olay": olay, "ts": ts, "t_perf": round(t - t0, 2),
                         "dosya": os.path.basename(tam), "dosya_50": os.path.basename(kucuk),
                         "kaynak": kaynak, "fsm": (cur.get("gorsel") or {}).get("durum"),
                         "hedef_kaynak": ((cur.get("dev") or {}).get("aktif"))}
                olay_kayit.append(kayit)
                with open(_OLAY_JSON, "w", encoding="utf-8") as f:
                    json.dump(olay_kayit, f, ensure_ascii=False, indent=2)
                print("  [%6.1fs] %-16s -> %s" % (t - t0, olay, os.path.basename(tam)))
                if olay == "GOREV_SONU" and bitis_t is None:
                    bitis_t = t + 8.0             # basaridan 8 sn sonra dur (son kareler)
            prev = cur
            if bitis_t and t >= bitis_t:
                print(" GOREV_SONU + grace tamam -> kayit bitti.")
                break
            if sure_max and (t - t0) > sure_max:
                print(" azami sure (%ds) doldu -> kayit bitti." % sure_max)
                break
            time.sleep(1.0 / hz)
    except KeyboardInterrupt:
        print("\n Ctrl+C -> kayit durduruldu.")
    print(" toplam %d olay/kare. olaylar.json: %s" % (len(olay_kayit), _OLAY_JSON))
    return 0


# ----------------------------------------------------------------------------
#  RAPOR: ucus CSV + olaylar.json -> "uretildi [CSV]" tablosu (markdown)
# ----------------------------------------------------------------------------
def _son_csv():
    lst = sorted(glob.glob(os.path.join(_VERI, "ucus_log_*.csv")))
    return lst[-1] if lst else None


def _csv_oku(yol):
    with open(yol, "r", encoding="utf-8", errors="replace", newline="") as f:
        return list(csv.DictReader(f))


def _dolu(v):
    return v not in (None, "", "None")


def _uretildi_tablosu(satirlar, olaylar):
    """Kalem basina (uretildi_mi, kanit) sozlugu."""
    def ilk(pred):
        for i, s in enumerate(satirlar):
            if pred(s):
                return i, s
        return None, None

    R = {}
    # kalem 4: ilk bbox (vis_gordu==1 veya track_id dolu)
    i, s = ilk(lambda r: r.get("vis_gordu") in ("1", "1.0", "True") or _dolu(r.get("track_id")))
    R[4] = (i is not None, ("ilk tespit t_wall=%s (satir %s)" % (s.get("t_wall"), i)) if s else "CSV'de tespit yok")
    # kalem 5: bbox+ID+durum dolu satir sayisi
    n5 = sum(1 for r in satirlar if _dolu(r.get("track_id")) and _dolu(r.get("track_durumu")))
    R[5] = (n5 > 0, "%d satirda track_id+durumu dolu" % n5)
    # kalem 6: tracker durumlari + gecis sayisi
    durumlar, gecis, onceki = set(), 0, None
    for r in satirlar:
        d = r.get("track_durumu")
        if _dolu(d):
            durumlar.add(d)
            if onceki is not None and d != onceki:
                gecis += 1
            onceki = d
    R[6] = (len(durumlar) > 0, "durumlar={%s}, %d gecis" % (",".join(sorted(durumlar)) or "-", gecis))
    # kalem 7: coast bloklari + yeniden-tespit sayisi (tespit_mi True/False dizisi)
    coast_blok, yeniden, prev_tm = 0, 0, None
    for r in satirlar:
        tm = r.get("tespit_mi")
        if tm in ("False", "0", "0.0"):
            if prev_tm in ("True", "1", "1.0"):
                coast_blok += 1
            prev_tm = "False"
        elif tm in ("True", "1", "1.0"):
            if prev_tm == "False":
                yeniden += 1
            prev_tm = "True"
    R[7] = (coast_blok > 0 or yeniden > 0, "%d coast blogu, %d yeniden-tespit" % (coast_blok, yeniden))
    # kalem 8: guduum komut sutunlari (thr/pitch/roll/yaw_cmd dolu oran)
    n8 = sum(1 for r in satirlar if all(_dolu(r.get(c)) for c in
             ("thr_cmd", "pitch_cmd", "roll_cmd", "yaw_cmd")))
    R[8] = (n8 > 0, "%d/%d satirda 4 eksen komut dolu" % (n8, len(satirlar)))
    # kalem 9: fsm ANGAJMAN'a ulasti mi + min d_s
    ang = [r for r in satirlar if r.get("fsm_durum") == "ANGAJMAN" or r.get("durum") == "ANGAJMAN"]
    ds = [float(r["d_s"]) for r in satirlar if _dolu(r.get("d_s"))]
    R[9] = (len(ang) > 0, ("ANGAJMAN %d kare; min d_s=%.0f cm" %
            (len(ang), min(ds))) if ang and ds else ("ANGAJMAN %d kare" % len(ang)))
    # kalem 10: gorev sonu (olaylar.json'dan; CSV'de yok)
    gs = [o for o in olaylar if o.get("olay") == "GOREV_SONU"]
    R[10] = (len(gs) > 0, ("GOREV_SONU olayi: %s" % gs[0]["dosya"]) if gs else "olaylar.json'da GOREV_SONU yok")
    return R


def rapor():
    csv_yol = _son_csv()
    olaylar = []
    if os.path.isfile(_OLAY_JSON):
        try:
            olaylar = json.load(open(_OLAY_JSON, encoding="utf-8"))
        except Exception:
            olaylar = []
    print("=" * 68)
    print(" PROVA RAPORU (uretildi [CSV] denetimi)")
    print("=" * 68)
    print(" ucus CSV : %s" % (csv_yol or "YOK (ucus_log_*.csv bulunamadi)"))
    print(" olaylar  : %s (%d olay/kare)" % (_OLAY_JSON if olaylar else "-", len(olaylar)))
    if not csv_yol:
        print(" [!] CSV yok -> uretildi tablosu cikarilazmaz. Once provayi kosun.")
        return 1
    satirlar = _csv_oku(csv_yol)
    R = _uretildi_tablosu(satirlar, olaylar)
    kalem_ad = {1: "Sim ekrani", 2: "Drone+hedef konum", 3: "Bozuk GNSS (DEV: teslimde)",
                4: "Tespit ani", 5: "bbox+ID+durum", 6: "Tracker aktif/pasif",
                7: "Kayip/yeniden-tespit", 8: "Guduum komutu", 9: "Angajman/vurus",
                10: "Gorev sonu basari"}
    print("\n kalem | uretildi[CSV] | kanit")
    print(" ------+---------------+-------------------------------------------")
    for k in range(1, 11):
        if k in (1, 2):
            print(" %4d  | (kare)        | GENEL karelerde okunur (panel telemetrisi)" % k)
            continue
        if k == 3:
            print("    3  | DEV-atlandi   | DEV kaynak kosusu; teslim videosunda (filtre)")
            continue
        var, kanit = R.get(k, (False, "-"))
        print(" %4d  | %-13s | %s" % (k, "VAR" if var else "YOK", kanit))
    # olaylar ozeti
    say = {}
    for o in olaylar:
        say[o["olay"]] = say.get(o["olay"], 0) + 1
    print("\n olay dagilimi:", ", ".join("%s=%d" % kv for kv in sorted(say.items())) or "-")
    print(" kareler: %s" % _KARE_DIR)
    print("\n NOT: 'okunuyor mu' degerlendirmesi kare OKUYARAK yapilir (asistan);")
    print("      docs/video_prova_kontrol.md bu tablo + okunabilirlikle doldurulur.")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Prova kare kaydedici / raporlayici")
    ap.add_argument("--rapor", action="store_true", help="kosu sonrasi uretildi tablosu")
    ap.add_argument("--url", default=_URL)
    ap.add_argument("--hz", type=float, default=8.0, help="telemetri yoklama frekansi")
    ap.add_argument("--genel", type=float, default=10.0, help="GENEL kare araligi (sn)")
    ap.add_argument("--sure", type=float, default=900.0, help="azami kayit suresi (sn)")
    arg = ap.parse_args()
    if arg.rapor:
        return rapor()
    return canli(arg.url, arg.hz, arg.genel, arg.sure)


if __name__ == "__main__":
    sys.exit(main())

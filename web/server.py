# -*- coding: utf-8 -*-
"""
============================================================
 AVCI DRONE - YER KONTROL ISTASYONU (Backend / Python beyni)
============================================================
Bu program 3 is yapar:
  1) drone_sdk ile oyuna baglanir (oyun kapaliysa veya baglanti
     koparsa, arka planda otomatik yeniden baglanmayi dener),
  2) gelen telemetriyi okuyup SANTIMETRE -> METRE cevirir,
  3) tarayicidaki HTML arayuze veri sunan kucuk bir yerel web
     sunucusu acar.

Calistirmak icin:   python server.py
Sonra tarayicida:   http://127.0.0.1:8000
Kapatmak icin:      Ctrl + C
"""

import io
import json
import os
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from sdk import drone_sdk as drone
from guidance.ana_kontrol import AvciKontrol
from fusion.inovasyonlu_j_v2 import GNSSDuzeltici as JFiltre  # Inovasyonlu J: TEK uretim filtresi (sapma olcumu de bununla)
import numpy as np

# Ekran yakalama icin
import mss
from PIL import Image
try:
    import pygetwindow as gw
except Exception:
    gw = None

# Gorsel tespit (YOLO best.pt) + cv2 overlay — OPSIYONEL.
# Yoksa CV_OK=False -> gorsel faz pasif, sistem saf GPS ile BUGUNKUYLE AYNI calisir.
try:
    import cv2
    from detection.gorsel_tespit import GorselTespit
    CV_OK = True
except Exception as _cv_e:
    CV_OK = False
    print("[SERVER] gorsel faz pasif (cv2/ultralytics yuklenemedi: %s)." % _cv_e)

# ----------------------------------------------------------
#  Sabitler
# ----------------------------------------------------------
CM_TO_M = 0.01      # Oyun santimetre verir -> metre icin 0.01 ile carp
MS_TO_KMH = 3.6     # metre/saniye -> kilometre/saat
WEB_PORT = 8000     # Arayuzun acilacagi yerel port

HERE = os.path.dirname(os.path.abspath(__file__))          # .../web (server.py + index.html)
PROJ_ROOT = os.path.dirname(HERE)                          # depo koku
MODEL_DIR = os.path.join(PROJ_ROOT, "models")              # egitilmis modeller (.pt)
VERI_DIR = os.path.join(PROJ_ROOT, "veri")                 # calisma ciktilari (log/json/png)
os.makedirs(VERI_DIR, exist_ok=True)

# Goruntude oyun penceresini tanimak icin baslik ipuclari
GAME_TITLE_HINTS = ["dronesofwar", "drones of war", "drone of war"]
CAM_MAX_WIDTH = 960   # Yakalanan kareyi bu genislige olcekle (akiciligi artirir)
CAM_JPEG_QUALITY = 60

# --- GORSEL TESPIT MODELI (KOLAY DEGISTIR) ---
# Yeni model gelince: .pt'yi models/ klasorune koy, SADECE MODEL_YOLU'nu degistir, server'i yeniden baslat.
MODEL_YOLU = os.path.join(MODEL_DIR, "best.pt")   # tespit modeli (.pt): models/best.pt
MODEL_CONF = 0.30            # YOLO tespit esigi: overlay bu esigin USTUNDEKI kutulari CIZER.
                             # Dusuk tut (0.25-0.35) -> herhangi bir modelin NE algiladigini gor
                             # (FP'ler de gorunur, model degerlendirmesi icin). Drone yalnizca
                             # ana_kontrol.Cfg.GORSEL_CONF_MIN (0.65) USTUNDE gorsel faza ENGAGE olur.


# ----------------------------------------------------------
#  Ekran yakalama
#  Onceligi oyun penceresine verir; bulamazsa tum ekrani yakalar.
# ----------------------------------------------------------
# mss her is parcaciginda (thread) ayri ornek ister; thread-local tutuyoruz.
_thread_local = threading.local()


def _get_sct():
    if not hasattr(_thread_local, "sct"):
        _thread_local.sct = mss.mss()
    return _thread_local.sct


def _find_game_region():
    """Oyun penceresinin (left, top, width, height) bolgesini doner.
    Bulamazsa None (o zaman tum ekran yakalanir)."""
    if gw is None:
        return None
    try:
        for w in gw.getAllWindows():
            title = (w.title or "").lower()
            if any(h in title for h in GAME_TITLE_HINTS):
                if w.width > 0 and w.height > 0 and w.visible:
                    return (w.left, w.top, w.width, w.height)
    except Exception:
        pass
    return None


def grab_frame_jpeg():
    """Oyun penceresini (yoksa tum ekrani) yakalayip JPEG bayt dizisi doner."""
    sct = _get_sct()
    region = _find_game_region()
    if region:
        left, top, width, height = region
        bbox = {"left": left, "top": top, "width": width, "height": height}
    else:
        bbox = sct.monitors[1]  # birincil monitor (tum ekran)

    raw = sct.grab(bbox)
    img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")

    if img.width > CAM_MAX_WIDTH:
        ratio = CAM_MAX_WIDTH / img.width
        img = img.resize((CAM_MAX_WIDTH, int(img.height * ratio)))

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=CAM_JPEG_QUALITY)
    return buf.getvalue()


def _olcekle_bgr(bgr):
    """BGR kareyi CAM_MAX_WIDTH'e olcekle, contiguous yap; (kare, W, H) doner."""
    if bgr.shape[1] > CAM_MAX_WIDTH:
        ratio = CAM_MAX_WIDTH / bgr.shape[1]
        bgr = cv2.resize(bgr, (CAM_MAX_WIDTH, int(bgr.shape[0] * ratio)))
    bgr = np.ascontiguousarray(bgr)                        # cv2/ultralytics contiguous ister
    h, w = bgr.shape[:2]
    return bgr, w, h


def grab_frame_bgr():
    """(BGR numpy kare, W, H) doner. ONCE pencere-icerigi yakalama (occlusion-proof:
    oyun arkada olsa bile dogru kare). O tercih ediliyor ama kare henuz yoksa
    (None, 0, 0) doner -> inference o turu atlar (ayna/yanlis kare gostermez).
    windows-capture yoksa mss ekran-bolgesine duser (eski davranis)."""
    pym = pencere_yakala_motoru
    if pym is not None and pym.hazir:
        if pym.calisiyor():
            bgr = pym.get_latest_bgr()
            if bgr is not None:
                return _olcekle_bgr(bgr)
        return None, 0, 0                                  # pencere-yakalama tercih ama kare yok

    # Fallback: mss ekran-bolgesi (windows-capture yoksa)
    sct = _get_sct()
    region = _find_game_region()
    if region:
        left, top, width, height = region
        bbox = {"left": left, "top": top, "width": width, "height": height}
    else:
        bbox = sct.monitors[1]
    raw = sct.grab(bbox)
    frame = np.frombuffer(raw.bgra, dtype=np.uint8).reshape(raw.height, raw.width, 4)
    return _olcekle_bgr(frame[:, :, :3])                   # BGRA -> BGR (alpha at)


def fpv_jpeg():
    """Mevcut FPV JPEG: (1) gorev aktif + overlay hazirsa overlay'li kare,
    (2) degilse pencere-yakalama ham karesi (gorev oncesi canli on-izleme),
    (3) windows-capture yoksa mss. Hicbiri yoksa None (-> 503 -> placeholder)."""
    if CV_OK and inference_aktif:
        with tespit_lock:
            data = son_overlay_jpeg
        if data is not None:
            return data
    pym = pencere_yakala_motoru
    if pym is not None and pym.calisiyor():
        bgr = pym.get_latest_bgr()
        if bgr is not None:
            b2, _w, _h = _olcekle_bgr(bgr)
            ok, enc = cv2.imencode(".jpg", b2, [int(cv2.IMWRITE_JPEG_QUALITY), CAM_JPEG_QUALITY])
            if ok:
                return enc.tobytes()
    if pym is None or not pym.hazir:
        return grab_frame_jpeg()                           # mss fallback (windows-capture yoksa)
    return None


def overlay_ciz(frame_bgr, tespit, dbg):
    """mss karesine HUD ciz (yerinde): goruntu merkezi +, bbox, merkez nokta, hata
    vektoru, durum, 'GPS GUDUMU: KAPALI' rozeti (yalniz gorsel_aktif), ex/ey, conf.
    cv2 Hershey TR karakter basamaz -> ASCII metin."""
    img = frame_bgr
    h, w = img.shape[:2]
    cx0, cy0 = w // 2, h // 2
    cv2.drawMarker(img, (cx0, cy0), (255, 255, 255), cv2.MARKER_CROSS, 22, 1)  # goruntu merkezi +

    durum = dbg.get("durum", "ARAMA")
    gorsel_aktif = bool(dbg.get("gorsel_aktif", False))

    if tespit.get("var"):
        x1, y1, x2, y2 = [int(v) for v in tespit["bbox_xyxy"]]
        tcx, tcy = int(tespit["cx"]), int(tespit["cy"])
        renk = (0, 230, 0) if gorsel_aktif else (0, 200, 255)   # BGR: yesil / turuncu
        cv2.rectangle(img, (x1, y1), (x2, y2), renk, 2)
        cv2.circle(img, (tcx, tcy), 4, renk, -1)
        cv2.line(img, (cx0, cy0), (tcx, tcy), renk, 1)          # hata vektoru
        et = "HEDEF %.2f" % tespit.get("conf", 0.0)
        if tespit.get("tid") is not None:
            et += " id:%d" % tespit["tid"]
        cv2.putText(img, et, (x1, max(14, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, renk, 1, cv2.LINE_AA)
    else:
        cv2.putText(img, "HEDEF YOK", (10, h - 12), cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (0, 0, 255), 1, cv2.LINE_AA)

    cv2.putText(img, "DURUM: %s" % durum.replace("_", " "), (10, 22),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)

    if gorsel_aktif:
        cv2.rectangle(img, (10, 32), (252, 58), (0, 0, 200), -1)   # kirmizi rozet
        cv2.putText(img, "GPS GUDUMU: KAPALI", (16, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(img, "ex=%+.2f ey=%+.2f" % (dbg.get("ex", 0.0), dbg.get("ey", 0.0)),
                    (16, 78), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 230, 0), 1, cv2.LINE_AA)
    return img


# ----------------------------------------------------------
#  Baglanti yoneticisi
#  Oyun kapaliyken veya baglanti kopunca surekli yeniden dener.
# ----------------------------------------------------------
def connection_manager():
    while True:
        if not drone.is_connected():
            # Yeniden baglanmadan once eski baglantiyi temizle (cift baglanmayi onler)
            try:
                drone.disconnect()
            except Exception:
                pass
            drone.connect()  # oyun kapaliysa sessizce False doner, sorun olmaz
        # Pencere-yakalamayi ayakta tut: oyun penceresi acilinca baslar; kapaninca
        # on_closed birakir -> burada (her 2 sn) yeniden baslar.
        if (pencere_yakala_motoru is not None and pencere_yakala_motoru.hazir
                and not pencere_yakala_motoru.calisiyor()):
            pencere_yakala_motoru.baslat()
        time.sleep(2.0)


# ----------------------------------------------------------
#  Gorev kontrol beyni (arkadasin AvciKontrol'u)
#  KADEME 1: gorev_aktif=False -> drone UCMAZ, sadece J olcumu yapilir.
#  KADEME 2: buton ile gorev_aktif=True -> drone hedefe gider.
# ----------------------------------------------------------
beyin = AvciKontrol(drone)
beyin_lock = threading.Lock()
gorev_aktif = False

# ----------------------------------------------------------
#  GORSEL TESPIT (YOLO) — ayri inference thread'i ile paylasim
#  Inference thread Tespit uretir; kontrol dongusu beyin.gorsel_guncelle ile besler.
#  tespit_lock: yalniz son_tespit/son_overlay_jpeg yaziminda (beyin_lock'tan AYRI;
#  iki kilit ASLA ic ice tutulmaz -> deadlock yok).
# ----------------------------------------------------------
# NOT: pose modeli (bestpose.pt) verilirse SADECE .boxes (bbox) kullanilir, keypoint'ler
# yok sayilir (duz IBVS = bbox merkezi). Model + esik yukaridaki MODEL_YOLU / MODEL_CONF'ta.
tespit_motoru = GorselTespit(MODEL_YOLU, conf=MODEL_CONF) if CV_OK else None
tespit_lock = threading.Lock()
EMPTY_TESPIT = {"var": False, "bbox_xyxy": None, "cx": 0.0, "cy": 0.0,
                "w": 0.0, "h": 0.0, "conf": 0.0, "tid": None,
                "frame_w": 0, "frame_h": 0, "ts": 0.0}
son_tespit = dict(EMPTY_TESPIT)   # son Tespit (inference thread yazar, kontrol dongusu okur)
son_overlay_jpeg = None           # son overlay'li JPEG (/api/frame doner)
inference_aktif = False           # gorev basladiginda + model hazirsa True

# Pencere-icerigi yakalama (occlusion-proof): tek monitorde oyun tarayicinin
# ARKASINDA olsa bile dogru oyun karesini alir (mss ekran-bolgesinin aksine).
# windows-capture yoksa hazir=False -> grab_frame_bgr mss'e duser.
# connection_manager oyun penceresi acilinca otomatik baslatir.
try:
    from detection.pencere_yakala import PencereYakala
    pencere_yakala_motoru = PencereYakala(title_hints=GAME_TITLE_HINTS) if CV_OK else None
except Exception as _py_e:
    pencere_yakala_motoru = None
    print("[SERVER] pencere_yakala yuklenemedi: %s" % _py_e)

# ----------------------------------------------------------
#  MANUEL MOD (klavyeyle kontrol)
#  Tarayici klavye tuslarini okuyup eksen komutuna cevirir ve /api/manuel
#  ile buraya akitir. Kontrol dongusu bu komutu drona uygular.
#  gorev_aktif ile KARSILIKLI DISLAR: ikisi ayni anda acik olamaz.
# ----------------------------------------------------------
manuel_aktif = False
# Tarayicidan gelen son kontrol komutu (hepsi -1..1; hiz slideri carpani
# tarayicida zaten uygulanmis halde gelir).
manuel_kontrol = {"throttle": 0.0, "pitch": 0.0, "roll": 0.0, "yaw": 0.0}
manuel_son_giris = 0.0       # son manuel giris zamani (failsafe icin, time.time())
MANUEL_TIMEOUT = 0.7         # sn: bu sureden uzun giris gelmezse HOVER'a gec
                             # (sekme/baglanti koparsa drone kacmaz, oldugu yerde durur)

# Telafi tarama testi tamamlandi -> en iyi telafi_sn=2.0 (Efe'nin orijinal ayari).

# ----------------------------------------------------------
#  SAPMA OLCUMU: tek uretim filtresi Inovasyonlu J, GERCEGE hatasi.
#  Ham taban cizgisiyle birlikte. Gudume DOKUNMAZ; sadece sim/debug olcum.
#  (Eski v1 / v2.4 kiyas adaylari kaldirildi; tek filtre kaldi.)
# ----------------------------------------------------------
_kiyas_j = JFiltre()        # Inovasyonlu J: uretim filtresi (sapma olcumu)
_kiyas_idx = 0
_kiyas_son_ham = None
# Son ~80 olcumun penceresi (anlik performans; eski veriye takilmaz)
_kiyas_ham_hata = deque(maxlen=80)
_kiyas_j_hata = deque(maxlen=80)

# Olcum CSV log: her paket icin ham/J hatasi (m). Her baslangicta sifirlanir.
_KIYAS_LOG = os.path.join(VERI_DIR, "kiyas_log.csv")
try:
    _kiyas_log_f = open(_KIYAS_LOG, "w", encoding="utf-8")
    _kiyas_log_f.write("paket,ham_m,j_m\n")
    _kiyas_log_f.flush()
except Exception:
    _kiyas_log_f = None

# GORSEL GUDUM (IBVS) zaman-indeksli log (50 Hz). gorsel_aktif iken yazilir.
# kiyas_log.csv paket-indeksli (~1 Hz) oldugundan KARISTIRILMAZ -> ayri dosya.
_GORSEL_LOG = os.path.join(VERI_DIR, "gorsel_log.csv")
try:
    _gorsel_log_f = open(_GORSEL_LOG, "w", encoding="utf-8")
    _gorsel_log_f.write("t_ms,durum,gorsel_aktif,conf,cx,cy,ex,ey,doluluk,gate,"
                        "cmd_thr,cmd_pitch,cmd_roll,cmd_yaw,"
                        "raw_thr,raw_pitch,raw_roll,raw_yaw,"
                        "gordu,kayip,drone_z\n")
    _gorsel_log_f.flush()
except Exception:
    _gorsel_log_f = None
_gorsel_log_t0 = None
_gorsel_log_n = 0

# --- GPS JSON KAYIT: target (hedef IHA) GPS'in BOZUK / GERCEK / J-FILTRELI halleri ---
# Saniye bazinda, METRE. _kiyas_guncelle her pakette son degerleri gunceller;
# _gps_json_yaz saniyede bir gps_kayit.json'a yazar. Her server basinda sifirlanir.
_GPS_JSON = os.path.join(VERI_DIR, "gps_kayit.json")
_gps_kayit = []
_gps_son_bozuk = None       # [x,y,z] m - ham (bozuk) GNSS
_gps_son_gercek = None      # [x,y,z] m - gercek (bozulmamis) konum
_gps_son_j = None           # [x,y,z] m - Inovasyonlu J (v2) filtreli
_gps_log_t0 = None
_gps_log_son = 0.0


def _kiyas_guncelle():
    """Her YENI ham pakette Inovasyonlu J'yi besle, gercege hatasini olc."""
    global _kiyas_idx, _kiyas_son_ham, _gps_son_bozuk, _gps_son_gercek, _gps_son_j
    ham = drone.get_target_location()
    if ham == _kiyas_son_ham:
        return
    _kiyas_son_ham = ham
    truth = drone.get_debug_truth()
    if not truth.get("available"):
        return
    gercek = np.array(truth["target"]["position"], float)
    idx = _kiyas_idx
    _kiyas_idx += 1
    hx, hy, hz = ham
    ham_e = float(np.linalg.norm(np.array(ham, float) - gercek))
    _kiyas_ham_hata.append(ham_e)
    j_e = None

    # Inovasyonlu J (uretim): anlik cikti -> su anki gercekle karsilastir
    j_out = _kiyas_j.guncelle(hx, hy, hz)
    if j_out is not None:
        j_e = float(np.linalg.norm(np.array(j_out, float) - gercek))
        _kiyas_j_hata.append(j_e)

    # GPS JSON icin son degerleri sakla (metre): bozuk / gercek / J-filtreli target GPS
    _gps_son_bozuk  = [round(hx * CM_TO_M, 2), round(hy * CM_TO_M, 2), round(hz * CM_TO_M, 2)]
    _gps_son_gercek = [round(float(gercek[0]) * CM_TO_M, 2), round(float(gercek[1]) * CM_TO_M, 2),
                       round(float(gercek[2]) * CM_TO_M, 2)]
    _gps_son_j = ([round(float(j_out[0]) * CM_TO_M, 2), round(float(j_out[1]) * CM_TO_M, 2),
                   round(float(j_out[2]) * CM_TO_M, 2)] if j_out is not None else None)

    # CSV log (metre): bos sutun = o pakette cikti yok (None/isinma)
    if _kiyas_log_f is not None:
        he = "%.2f" % (ham_e / 100.0)
        js = ("%.2f" % (j_e / 100.0)) if j_e is not None else ""
        try:
            _kiyas_log_f.write("%d,%s,%s\n" % (idx, he, js))
            _kiyas_log_f.flush()
        except Exception:
            pass


def _gps_json_yaz():
    """Saniyede bir: target GPS'in BOZUK / GERCEK / J-FILTRELI hallerini (metre, x/y/z)
    gps_kayit.json'a yaz. Degerler _kiyas_guncelle'de her pakette guncellenir."""
    global _gps_log_t0, _gps_log_son
    if _gps_son_bozuk is None or _gps_son_gercek is None:
        return                                        # henuz veri / truth yok
    now = time.time()
    if _gps_log_t0 is None:
        _gps_log_t0 = now
    if now - _gps_log_son < 1.0:                       # saniyede bir ornek
        return
    _gps_log_son = now
    _gps_kayit.append({
        "t":        round(now - _gps_log_t0, 1),
        "bozuk":    _gps_son_bozuk,
        "gercek":   _gps_son_gercek,
        "filtreli": _gps_son_j,
    })
    try:
        with open(_GPS_JSON, "w", encoding="utf-8") as f:
            json.dump({
                "birim": "metre",
                "eksenler": ["x", "y", "z"],
                "aciklama": "hedef IHA GPS - bozuk: ham GNSS, gercek: gercek konum, "
                            "filtreli: Inovasyonlu J (v2) ile temizlenmis",
                "ornek_sayisi": len(_gps_kayit),
                "kayitlar": _gps_kayit,
            }, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _gorsel_log_yaz():
    """gorsel_aktif iken IBVS telemetrisini gorsel_log.csv'ye yaz (beyin_lock altinda
    cagrilir). raw=IBVS ham komut (beyin.g_cmd), cmd=rate-limit SONRASI (beyin.prev).
    ~25 satirda bir flush."""
    global _gorsel_log_t0, _gorsel_log_n
    if _gorsel_log_f is None or not beyin.gorsel_aktif:
        return
    now = time.perf_counter()
    if _gorsel_log_t0 is None:
        _gorsel_log_t0 = now
    t = beyin.son_tespit or {}
    raw = beyin.g_cmd
    snt = beyin.prev                      # rate-limit SONRASI gonderilen komut
    try:
        dz = drone.get_drone_location()[2]
    except Exception:
        dz = 0.0
    try:
        _gorsel_log_f.write(
            "%.0f,%s,%d,%.3f,%.1f,%.1f,%+.4f,%+.4f,%.3f,%.3f,"
            "%+.4f,%+.4f,%+.4f,%+.4f,%+.4f,%+.4f,%+.4f,%+.4f,%d,%d,%.0f\n" % (
                (now - _gorsel_log_t0) * 1000.0, beyin.durum,
                1 if beyin.gorsel_aktif else 0, beyin.g_conf,
                t.get("cx", 0.0), t.get("cy", 0.0), beyin.g_ex, beyin.g_ey,
                beyin.g_doluluk, beyin.g_gate,
                snt['thr'], snt['pitch'], snt['roll'], snt['yaw'],
                raw['thr'], raw['pitch'], raw['roll'], raw['yaw'],
                beyin.gordu_sayac, beyin.kayip_sayac, dz))
        _gorsel_log_n += 1
        if _gorsel_log_n % 25 == 0:
            _gorsel_log_f.flush()
    except Exception:
        pass


def _manuel_uygula():
    """Manuel modda: tarayicidan gelen son kontrol komutunu drona gonderir.
    FAILSAFE: giris bayatladiysa (sekme kapandi / baglanti koptu) yatay
    hareketi sifirla; drone oldugu yerde HOVER eder (irtifa korunur, motorlar
    acik kalir), boylece kacip gitmez. Eksenler tarayicida hiz slideri ile
    zaten olceklenmis gelir; burada sadece [-1..1] sinirina sokup yollariz."""
    if time.time() - manuel_son_giris > MANUEL_TIMEOUT:
        thr = pit = rol = yaw = 0.0       # giris bayat -> sabit hover
    else:
        thr = manuel_kontrol["throttle"]
        pit = manuel_kontrol["pitch"]
        rol = manuel_kontrol["roll"]
        yaw = manuel_kontrol["yaw"]
    drone.set_control_surfaces(thr, pit, rol, yaw, True)


def inference_dongusu():
    """Ayri thread (inference hizinda, ~10-30 Hz): mss grab -> YOLO -> Tespit ->
    overlay -> JPEG; sonucu tespit_lock altinda paylasir. 50 Hz kontrolu BLOKLAMAZ.
    Kilit sirasi: YOLO(kilitsiz) -> beyin_lock(kisa snapshot) -> overlay(kilitsiz) ->
    tespit_lock(yaz). Iki kilit ASLA ic ice tutulmaz."""
    global son_tespit, son_overlay_jpeg
    while True:
        if not (CV_OK and inference_aktif and tespit_motoru is not None
                and tespit_motoru.hazir and drone.is_connected()):
            time.sleep(0.05)
            continue
        # Pencere-yakalama tercih ediliyorsa ve calismyorsa baslatmayi dene
        if (pencere_yakala_motoru is not None and pencere_yakala_motoru.hazir
                and not pencere_yakala_motoru.calisiyor()):
            pencere_yakala_motoru.baslat()
        try:
            bgr, w, h = grab_frame_bgr()
            if bgr is None:                               # oyun penceresi/kare henuz yok -> atla
                time.sleep(0.05)
                continue
            ham = tespit_motoru.tespit_et(bgr)            # KILITSIZ (agir is)
            ts = time.perf_counter()
            if ham is not None:
                x1, y1, x2, y2 = ham["bbox_xyxy"]
                tespit = {"var": True, "bbox_xyxy": ham["bbox_xyxy"],
                          "cx": (x1 + x2) * 0.5, "cy": (y1 + y2) * 0.5,
                          "w": (x2 - x1), "h": (y2 - y1),
                          "conf": ham["conf"], "tid": ham.get("tid"),
                          "frame_w": w, "frame_h": h, "ts": ts}
            else:
                tespit = {"var": False, "bbox_xyxy": None, "cx": 0.0, "cy": 0.0,
                          "w": 0.0, "h": 0.0, "conf": 0.0, "tid": None,
                          "frame_w": w, "frame_h": h, "ts": ts}
            with beyin_lock:                              # kisa snapshot (overlay icin)
                dbg = {"durum": beyin.durum, "gorsel_aktif": beyin.gorsel_aktif,
                       "ex": beyin.g_ex, "ey": beyin.g_ey}
            overlay_ciz(bgr, tespit, dbg)                 # KILITSIZ
            ok, enc = cv2.imencode(".jpg", bgr,
                                   [int(cv2.IMWRITE_JPEG_QUALITY), CAM_JPEG_QUALITY])
            jpg = enc.tobytes() if ok else None
            with tespit_lock:
                son_tespit = tespit
                if jpg is not None:
                    son_overlay_jpeg = jpg
        except Exception:
            time.sleep(0.02)


def kontrol_dongusu():
    while True:
        if drone.is_connected():
            try:
                # Gorsel Tespit'i beyin_lock DISINDA oku (iki kilit ic ice gecmesin)
                with tespit_lock:
                    t_now = son_tespit
                with beyin_lock:
                    if manuel_aktif:
                        beyin._hedef_temizle()    # J telemetrisi pasif aksin (guduuma dokunmaz)
                        _manuel_uygula()          # klavye komutunu uygula (kontrol)
                    elif gorev_aktif:
                        beyin.gorsel_guncelle(t_now)  # gorsel temas FSM (giris/cikis)
                        beyin.adim()              # gorsel_aktif ise IBVS, degilse GPS yaklasma
                        _gorsel_log_yaz()         # gorsel_aktif iken IBVS CSV
                    else:
                        beyin._hedef_temizle()    # sadece J'yi guncelle (olcum)
                        if beyin.debug_olc:
                            beyin._debug_olc()    # ham vs J hatasini olc
                    # Kiyas HER ZAMAN calisir (drone ucsa da uctmasa da donmaz)
                    _kiyas_guncelle()             # Inovasyonlu J sapma olcumu (ham vs J)
                _gps_json_yaz()                   # saniyede bir GPS JSON: bozuk/gercek/filtreli target
            except Exception:
                pass
        time.sleep(0.02)   # 50 Hz


# ----------------------------------------------------------
#  Telemetriyi oku ve arayuz icin sade bir sozluge cevir.
#  Tum konum/irtifa degerleri METRE, hizlar hem m/s hem km/h.
# ----------------------------------------------------------
def build_telemetry():
    connected = drone.is_connected()

    dpos = drone.get_drone_location()    # (x, y, z) cm
    drot = drone.get_drone_rotation()    # (roll, pitch, yaw) derece
    dspd = drone.get_drone_speed()       # cm/s
    dalt = drone.get_drone_altitude()    # cm
    tpos = drone.get_target_location()   # (x, y, z) cm  (HAM - bozuk olabilir)
    tspd = drone.get_target_speed()      # cm/s

    # Santimetre -> metre
    dx, dy, dz = (c * CM_TO_M for c in dpos)
    tx, ty, tz = (c * CM_TO_M for c in tpos)
    drone_alt_m = dalt * CM_TO_M
    drone_spd_ms = dspd * CM_TO_M
    target_spd_ms = tspd * CM_TO_M

    # Avci ile hedef arasindaki 3 boyutlu mesafe (metre)
    distance_m = ((dx - tx) ** 2 + (dy - ty) ** 2 + (dz - tz) ** 2) ** 0.5

    # (Debug) Gercek (bozulmamis) degerler - oyunda debug acikken gelir.
    truth = drone.get_debug_truth()
    debug_info = {"available": bool(truth.get("available"))}
    if debug_info["available"]:
        adx, ady, adz = (c * CM_TO_M for c in truth["drone"]["position"])
        tgx, tgy, tgz = (c * CM_TO_M for c in truth["target"]["position"])
        debug_info["drone_real"] = {"x": adx, "y": ady, "z": adz}
        debug_info["target_real"] = {"x": tgx, "y": tgy, "z": tgz}
        # Hedef HAM GPS ile GERCEK konum arasindaki fark (bozulma miktari, metre)
        debug_info["target_raw_error_m"] = (
            (tx - tgx) ** 2 + (ty - tgy) ** 2 + (tz - tgz) ** 2) ** 0.5
        # Avci okumasi ile gercegi arasindaki fark (temiz olmali ~0)
        debug_info["drone_error_m"] = (
            (dx - adx) ** 2 + (dy - ady) ** 2 + (dz - adz) ** 2) ** 0.5
        debug_info["corruptions"] = list(truth.get("corruption_active", []))

    # J (GNSS duzeltici) durumu ve canli olcum (beyin_lock ile guvenli oku)
    with beyin_lock:
        j_durum = beyin.durum
        j_kaynak = beyin.kaynak           # aktif guduum kaynagi (Inovasyonlu J / gercek)
        j_temiz = None if beyin.son_temiz is None else (
            float(beyin.son_temiz[0]), float(beyin.son_temiz[1]), float(beyin.son_temiz[2]))
        ham_list = list(beyin.ham_hatalar)
        j_list = list(beyin.j_hatalar)
    j_info = {"durum": j_durum, "hazir": j_temiz is not None}
    if j_temiz is not None:
        j_info["temiz"] = {"x": j_temiz[0] * CM_TO_M,
                           "y": j_temiz[1] * CM_TO_M,
                           "z": j_temiz[2] * CM_TO_M}
    if ham_list:
        n = len(ham_list)
        ham_ort = float(sum(ham_list)) / n / 100.0   # cm -> m, ortalama
        j_ort = float(sum(j_list)) / n / 100.0
        j_info["ham_hata_ort_m"] = ham_ort
        j_info["j_hata_ort_m"] = j_ort
        j_info["kazanc_pct"] = (100.0 * (ham_ort - j_ort) / ham_ort) if ham_ort > 0 else 0.0
        j_info["ornek"] = n

    # Sapma ozeti (gercege hata, metre): uretim Inovasyonlu J + Ham taban cizgisi
    with beyin_lock:
        ham_h = list(_kiyas_ham_hata)
        j_h = list(_kiyas_j_hata)
    kiyas = {}
    if ham_h:
        kiyas["ham_ort_m"] = sum(ham_h) / len(ham_h) / 100.0
    # Ozet: ortalama (tipik), std (dalgalanma), max (en kotu sapma).
    def _ozet(ad, hlist):
        if not hlist:
            return
        a = np.array(hlist, float) / 100.0          # cm -> m
        kiyas[ad + "_ort_m"] = float(a.mean())
        kiyas[ad + "_std_m"] = float(a.std())
        kiyas[ad + "_max_m"] = float(a.max())
        kiyas[ad + "_ornek"] = int(a.size)
    _ozet("j", j_h)

    return {
        "connected": connected,
        "drone": {
            "x": dx, "y": dy, "z": dz,
            "altitude_m": drone_alt_m,
            "speed_ms": drone_spd_ms,
            "speed_kmh": drone_spd_ms * MS_TO_KMH,
            "roll": drot[0], "pitch": drot[1], "yaw": drot[2],
        },
        "target": {
            "x": tx, "y": ty, "z": tz,
            "speed_ms": target_spd_ms,
            "speed_kmh": target_spd_ms * MS_TO_KMH,
        },
        "distance_m": distance_m,
        "debug": debug_info,
        "j": j_info,
        "gorev_aktif": gorev_aktif,
        "manuel_aktif": manuel_aktif,
        "kaynak": j_kaynak,
        "kiyas": kiyas,
    }


# ----------------------------------------------------------
#  HTTP istek isleyici
# ----------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # konsolu gereksiz log ile kirletme

    def _send(self, code, content, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            try:
                with open(os.path.join(HERE, "index.html"), "rb") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
            except FileNotFoundError:
                self._send(404, "index.html bulunamadi".encode("utf-8"),
                           "text/plain; charset=utf-8")
        elif self.path == "/api/telemetry":
            payload = json.dumps(build_telemetry()).encode("utf-8")
            self._send(200, payload, "application/json")
        elif self.path.startswith("/api/frame"):
            try:
                data = fpv_jpeg()                 # overlay'li kare / ham oyun karesi / mss
                if data is None:
                    self._send(503, "kare yok (oyun penceresi bekleniyor)".encode("utf-8"),
                               "text/plain; charset=utf-8")
                else:
                    self._send(200, data, "image/jpeg")
            except Exception as e:
                self._send(500, ("goruntu hatasi: %s" % e).encode("utf-8"),
                           "text/plain; charset=utf-8")
        else:
            self._send(404, b"yok", "text/plain; charset=utf-8")

    def do_POST(self):
        global gorev_aktif, manuel_aktif, manuel_son_giris, inference_aktif
        if self.path == "/api/command":
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length).decode("utf-8") if length else "{}"
            try:
                data = json.loads(raw)
            except Exception:
                data = {}
            cmd = data.get("cmd", "")
            msg = "Bilinmeyen komut"
            if cmd in ("start", "start_v2", "start_gercek"):
                kaynak = {"start": "v2", "start_v2": "v2", "start_gercek": "gercek"}[cmd]
                with beyin_lock:
                    beyin.set_kaynak(kaynak)  # guduum kaynagini ayarla (v2 / gercek)
                gorev_aktif = True
                manuel_aktif = False          # gorev ve manuel ayni anda olmaz
                # Gorsel faz: model hazirsa inference thread'i devreye girsin (yoksa saf GPS)
                inference_aktif = bool(CV_OK and tespit_motoru is not None and tespit_motoru.hazir)
                _ad = {"v2": "Inovasyonlu J", "gercek": "GERCEK GPS"}[kaynak]
                msg = "GOREV BASLATILDI - kaynak: %s%s" % (
                    _ad, " (filtre yok, gercek konuma gidiyor)" if kaynak == "gercek" else "")
            elif cmd == "stop":
                gorev_aktif = False
                manuel_aktif = False
                inference_aktif = False       # gorsel faz dur
                # Guvenlik: drone'u durdur (motorlari kes -> arm=False)
                try:
                    drone.set_control_surfaces(0.0, 0.0, 0.0, 0.0, False)
                except Exception:
                    pass
                msg = "GOREV DURDURULDU - drone pasif (motorlar kapali)"
            elif cmd == "manuel_on":
                gorev_aktif = False           # gorev ve manuel ayni anda olmaz
                inference_aktif = False       # manuel modda gorsel faz pasif
                # Tek kilit altinda: durumu kur + arm/hover yolla (50Hz dongu ile
                # ayni anda TCP'ye yazmayi onler).
                with beyin_lock:
                    manuel_kontrol["throttle"] = 0.0
                    manuel_kontrol["pitch"] = 0.0
                    manuel_kontrol["roll"] = 0.0
                    manuel_kontrol["yaw"] = 0.0
                    manuel_son_giris = time.time()
                    manuel_aktif = True
                    # Arm + hover (ilk klavye girisi gelene kadar oldugu yerde dursun)
                    try:
                        drone.set_control_surfaces(0.0, 0.0, 0.0, 0.0, True)
                    except Exception:
                        pass
                msg = "MANUEL MOD ACIK - klavye: W/A/S/D, Q/E (don), R/F (yuksel/alcal)"
            elif cmd == "manuel_off":
                # Motoru KESMEZ: drone havada sabit kalsin (hover). Tamamen
                # durdurmak icin kullanici 'Gorev Durdur'a basar.
                with beyin_lock:
                    manuel_aktif = False
                    try:
                        drone.set_control_surfaces(0.0, 0.0, 0.0, 0.0, True)
                    except Exception:
                        pass
                msg = "MANUEL MOD KAPALI - drone havada sabit (hover)"
            payload = json.dumps({"ok": True, "msg": msg,
                                  "gorev_aktif": gorev_aktif,
                                  "manuel_aktif": manuel_aktif})
            self._send(200, payload.encode("utf-8"), "application/json")
        elif self.path == "/api/manuel":
            # Yuksek frekansli manuel kontrol akisi (klavye -> eksen komutu).
            # Status yazisini kirletmemek icin /api/command'dan ayri tutulur.
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length).decode("utf-8") if length else "{}"
            try:
                data = json.loads(raw)
            except Exception:
                data = {}

            def _eksen(x):
                try:
                    return max(-1.0, min(1.0, float(x)))
                except Exception:
                    return 0.0

            with beyin_lock:
                if manuel_aktif:
                    manuel_kontrol["throttle"] = _eksen(data.get("throttle", 0.0))
                    manuel_kontrol["pitch"] = _eksen(data.get("pitch", 0.0))
                    manuel_kontrol["roll"] = _eksen(data.get("roll", 0.0))
                    manuel_kontrol["yaw"] = _eksen(data.get("yaw", 0.0))
                    manuel_son_giris = time.time()
            self._send(200, b'{"ok":true}', "application/json")
        else:
            self._send(404, b"yok", "text/plain; charset=utf-8")


# ----------------------------------------------------------
#  Ana program
# ----------------------------------------------------------
def main():
    # Arka planda baglanti yoneticisini ve gorev kontrol beynini baslat
    threading.Thread(target=connection_manager, daemon=True).start()
    threading.Thread(target=kontrol_dongusu, daemon=True).start()
    if CV_OK:
        threading.Thread(target=inference_dongusu, daemon=True).start()   # gorsel tespit thread'i

    server = ThreadingHTTPServer(("127.0.0.1", WEB_PORT), Handler)
    print("=" * 52)
    print("  AVCI DRONE - YER KONTROL ISTASYONU calisiyor")
    print("  Tarayicida ac:  http://127.0.0.1:%d" % WEB_PORT)
    print("  Kapatmak icin:  Ctrl + C")
    print("=" * 52)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nKapatiliyor...")
    finally:
        drone.disconnect()


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""AVCI DRONE - YER KONTROL ISTASYONU (backend): oyuna baglanir, telemetriyi
cm->m cevirir, HTML arayuze veri sunan yerel web sunucusu acar (python server.py)."""

import io
import json
import os
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from sdk import drone_sdk as drone
from guidance.ana_kontrol import AvciKontrol, Cfg
from fusion.gnss_filtre import GNSSFiltre   # uretim GNSS filtresi
import numpy as np

# Ekran yakalama icin
import mss
from PIL import Image
try:
    import pygetwindow as gw
except Exception:
    gw = None

# cv2 opsiyonel; yoksa FPV mss+PIL yoluna duser.
try:
    import cv2
except Exception:
    cv2 = None

# ----------------------------------------------------------
#  Sabitler
# ----------------------------------------------------------
CM_TO_M = 0.01      # Oyun santimetre verir -> metre icin 0.01 ile carp
MS_TO_KMH = 3.6     # metre/saniye -> kilometre/saat
WEB_PORT = 8000     # Arayuzun acilacagi yerel port

HERE = os.path.dirname(os.path.abspath(__file__))           # .../web (server.py + index.html)
PROJ_ROOT = os.path.dirname(HERE)                           # depo koku
VERI_DIR = os.path.join(PROJ_ROOT, "veri")                  # calisma ciktilari (log/csv; gitignore'lu)
os.makedirs(VERI_DIR, exist_ok=True)

# Goruntude oyun penceresini tanimak icin baslik ipuclari
GAME_TITLE_HINTS = ["dronesofwar", "drones of war", "drone of war"]
CAM_MAX_WIDTH = 960   # FPV JPEG akisini bu genislige olcekle (dedektor DOGAL alir)
CAM_JPEG_QUALITY = 60
UI_CONF_MIN = 0.25    # dedektor predict esigi (gudum/kilit yalnizca conf>=Cfg.VIS_CONF_MIN gorur)
POZ_HER_N = 5         # poz inference'i her N dedektor turunda bir (gozlemci)
# FP16 (half) inference; set AVCI_FP16=0 ile FP32'ye don.
FP16_AKTIF = os.environ.get("AVCI_FP16", "1").strip() == "1"


# ----------------------------------------------------------
#  Ekran yakalama (oncelik oyun penceresi; bulamazsa tum ekran)
# ----------------------------------------------------------
# mss her thread'de ayri ornek ister -> thread-local.
_thread_local = threading.local()


def _get_sct():
    if not hasattr(_thread_local, "sct"):
        _thread_local.sct = mss.mss()
    return _thread_local.sct


def _find_game_region():
    """Oyun penceresinin (left, top, width, height) bolgesi | None (tum ekran)."""
    if gw is None:
        return None
    try:
        from detection.pencere_yakala import pencere_bul
        baslik, hwnd = pencere_bul(GAME_TITLE_HINTS)
        if baslik is None:
            return None
        for w in gw.getAllWindows():
            if (hwnd is not None and getattr(w, "_hWnd", None) == hwnd) or \
               (hwnd is None and (w.title or "").strip() == baslik):
                if w.width > 0 and w.height > 0 and w.visible:
                    return (w.left, w.top, w.width, w.height)
    except Exception:
        pass
    return None


def grab_frame_jpeg():
    """mss FALLBACK: oyun bolgesini (yoksa tum ekrani) yakalayip JPEG doner."""
    sct = _get_sct()
    region = _find_game_region()
    if region:
        left, top, width, height = region
        bbox = {"left": left, "top": top, "width": width, "height": height}
    else:
        bbox = sct.monitors[1]  # tum ekran
    raw = sct.grab(bbox)
    img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
    if img.width > CAM_MAX_WIDTH:
        ratio = CAM_MAX_WIDTH / img.width
        img = img.resize((CAM_MAX_WIDTH, int(img.height * ratio)))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=CAM_JPEG_QUALITY)
    return buf.getvalue()


# ----------------------------------------------------------
#  PENCERE-ICERIGI YAKALAMA (occlusion-proof FPV)
#  Oyun penceresi arkada olsa bile ICERIGINI yakalar. windows-capture yoksa
#  hazir=False -> mss ekran-bolgesine duser. False yap -> mss fallback (oyun ONDE).
# ----------------------------------------------------------
PENCERE_YAKALA_AKTIF = True
pencere_yakala_motoru = None
if PENCERE_YAKALA_AKTIF:
    try:
        from detection.pencere_yakala import PencereYakala
        pencere_yakala_motoru = PencereYakala(title_hints=GAME_TITLE_HINTS)
    except Exception as _py_e:
        print("[SERVER] pencere_yakala yuklenemedi (%s) -> mss fallback." % _py_e)
else:
    print("[SERVER] pencere-yakalama KAPALI -> dedektor kare kaynagi mss "
          "(oyun penceresi gorunur/kucultulmemis olmali).")


def _olcekle_bgr(bgr):
    """BGR kareyi CAM_MAX_WIDTH'e olcekle, contiguous yap; (kare, W, H) doner."""
    if cv2 is not None and bgr.shape[1] > CAM_MAX_WIDTH:
        ratio = CAM_MAX_WIDTH / bgr.shape[1]
        bgr = cv2.resize(bgr, (CAM_MAX_WIDTH, int(bgr.shape[0] * ratio)))
    bgr = np.ascontiguousarray(bgr)                        # ultralytics contiguous ister
    h, w = bgr.shape[:2]
    return bgr, w, h


# FPV kaynagi degistiginde bir kez konsola yaz.
_fpv_kaynak = {"ad": None}
def _fpv_log(ad, ekstra=""):
    if _fpv_kaynak["ad"] != ad:
        _fpv_kaynak["ad"] = ad
        print("[FPV] goruntu kaynagi -> %s%s" % (ad, ekstra))


def _mss_grab_bgr():
    """mss ile oyun bolgesini (bulunursa), yoksa tum ekrani BGR ndarray yakala -> (kaynak, bgr)."""
    sct = _get_sct()
    region = _find_game_region()
    if region:
        left, top, width, height = region
        bbox = {"left": left, "top": top, "width": width, "height": height}
        kaynak = "mss (oyun penceresi bolgesi)"
    else:
        bbox = sct.monitors[1]                             # tum ekran
        kaynak = "mss (TUM EKRAN - oyun penceresi bulunamadi; ayna olursa oyunu KENARLIKSIZ PENCERE yap)"
    raw = sct.grab(bbox)
    frame = np.frombuffer(raw.bgra, dtype=np.uint8).reshape(raw.height, raw.width, 4)
    return kaynak, frame[:, :, :3].copy()                  # BGRA -> BGR


def grab_frame_bgr():
    """(BGR kare, W, H) — YOLO dedektorunun kare kaynagi (DOGAL cozunurluk, kucultme yok).
    Fallback zinciri: windows-capture -> mss oyun bolgesi -> mss tum ekran; hepsi
    basarisizsa (None, 0, 0)."""
    pym = pencere_yakala_motoru
    if pym is not None and pym.hazir and pym.calisiyor():
        bgr = pym.get_latest_bgr()
        if bgr is not None:
            _fpv_log("windows-capture (pencere icerigi)")
            bgr = np.ascontiguousarray(bgr)            # ultralytics contiguous ister
            return bgr, bgr.shape[1], bgr.shape[0]
    # Fallback: mss
    try:
        kaynak, bgr = _mss_grab_bgr()
        _fpv_log(kaynak)
        bgr = np.ascontiguousarray(bgr)
        return bgr, bgr.shape[1], bgr.shape[0]
    except Exception as e:
        _fpv_log("KARE YOK", " (%s)" % e)
        return None, 0, 0


def fpv_jpeg():
    """/api/frame HAM oyun karesi (overlay yok); kaynak yoksa None. Kare 960'a kucultulur."""
    bgr, _w, _h = grab_frame_bgr()
    if bgr is None:
        return None
    bgr, _w, _h = _olcekle_bgr(bgr)
    if cv2 is not None:
        ok, enc = cv2.imencode(".jpg", bgr, [int(cv2.IMWRITE_JPEG_QUALITY), CAM_JPEG_QUALITY])
        if ok:
            return enc.tobytes()
    img = Image.fromarray(bgr[:, :, ::-1].copy())          # BGR->RGB
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=CAM_JPEG_QUALITY)
    return buf.getvalue()


# ----------------------------------------------------------
#  Baglanti yoneticisi (kopunca surekli yeniden dener)
# ----------------------------------------------------------
def connection_manager():
    _conn_prev = None
    while True:
        c = drone.is_connected()
        if c and _conn_prev != True:            # ilk / yeniden baglanma
            olay_ekle("iyi", "Oyuna baglanildi")
        elif (not c) and _conn_prev == True:    # kopma
            olay_ekle("uyari", "Oyun baglantisi koptu")
        _conn_prev = c
        if not c:
            try:
                drone.disconnect()              # eski baglantiyi temizle (cift baglanmayi onle)
            except Exception:
                pass
            drone.connect()  # oyun kapaliysa sessizce False doner
        # Pencere-yakalamayi ayakta tut (oyun penceresi kapaninca yeniden baslat)
        pym = pencere_yakala_motoru
        if pym is not None and pym.hazir:
            if not pym.calisiyor():
                pym.baslat()
            elif pym.yeniden_baglanmali(stale_s=2.5):
                # WATCHDOG: kare bayat/yok ya da pencere degisti -> taze yeniden bagla
                print("[PENCERE_YAKALA] WATCHDOG: kare bayat/yanlis pencere -> yeniden baglaniliyor")
                pym.durdur()
                pym.baslat()
        time.sleep(2.0)


# ----------------------------------------------------------
#  Gorev kontrol beyni (gorev_aktif=False -> olcum; True -> drone hedefe gider)
# ----------------------------------------------------------
beyin = AvciKontrol(drone)
beyin_lock = threading.Lock()
gorev_aktif = False

# ----------------------------------------------------------
#  CANLI TUNE: arayuz slider'lari Cfg'yi calisirken degistirir (her tik okunur,
#  restart gerekmez). Guvenlik icin sadece bu allowlist.
# ----------------------------------------------------------
TUNE_ALLOW = {
    "IBVS_ILERI",        # ileri itki TAVANI — yaklasma hizi siniri (boyut yasasi asamaz)
    "IBVS_BOYUT_HEDEF",  # kilit-tut: bbox eksen orani hedefi (kilit esiginin ustunde tut)
    "IBVS_K_BOYUT",      # kilit-tut: boyut hatasi -> ileri kazanci (0=KAPALI/eski yasa)
    "IBVS_GERI_MAX",     # kilit-tut: fazla yakinken geri itki tavani (0=asla geri)
    "IBVS_FREN_HIZ",     # kapanma-hizi freni (TTC): bbox hizli buyuyorse ileriyi kis (hedefi asma)
    "IBVS_K_YAW",        # yatay kazanc (cizginin yatay bileseni -> yaw)
    "IBVS_K_DIKEY",      # dikey kazanc (cizginin dikey bileseni -> throttle)
    "IBVS_YAKIN_KAZANC", # yakinlik-olcekli kazanc: yakinken (buyuk bbox) yaw/dikey'i sikilastir (0=kapali)
    "IBVS_DIKEY_NISAN",  # dikey nisan (0=merkez/altta-kal, 1=hiz-vektoru hedefte; tilt-farkinda)
    "IBVS_MERKEZ_FREN",  # sapma buyuyunce ileriyi kis (0=hep tam gaz)
    "IBVS_HANDOFF_S",    # GPS->gorsel yumusak gecis rampasi (s); 0=kapali (uzunsa gecikir, kisaysa lunge)
    "IBVS_ALCAL_FREN",   # alcalma freni: hedef nisanin ALTINDAysa ileriyi kis
    "VIS_EMA",           # ex/ey yumusatma (kucuk=yumusak, buyuk=tepkili)
    "YAW_MAX",           # yaw tavani (doygunluk)
    "VIS_CONF_MIN",      # tespit guven esigi
    "VIS_LOST_TO_GPS_S", # kayipta GPS'e donmeden once bekleme (hover) suresi
    "VIS_KOPRU_S",       # goruntu-duzlemi kopru (olu-hesap) suresi; 0 = kapali
    # NOT: GPS-yaklasma sabitleri guidance/gps_takip.GPSCfg'dedir (burada DEGIL).
}

# ----------------------------------------------------------
#  TUNE LOGU (1 Hz): slider degerleri veri/tune_log_*.csv'ye yazilir; rapor bunu
#  ucus loguyla hizalayip parametre-degisim segmentlerini kiyaslar.
# ----------------------------------------------------------
_TUNE_LOG_PATH = None
_TUNE_LOG_KOLON = None   # sirali param listesi


def tune_log_dongusu():
    global _TUNE_LOG_PATH, _TUNE_LOG_KOLON
    _TUNE_LOG_KOLON = sorted(TUNE_ALLOW)
    _TUNE_LOG_PATH = os.path.join(VERI_DIR, time.strftime("tune_log_%Y%m%d_%H%M%S.csv"))
    try:
        f = open(_TUNE_LOG_PATH, "w", encoding="utf-8")
        f.write("t_wall," + ",".join(_TUNE_LOG_KOLON) + "\n")
        f.flush()
    except Exception as e:
        print("[TUNE_LOG] acilamadi:", e)
        _TUNE_LOG_PATH = None
        return
    while True:
        try:
            vals = [getattr(Cfg, k) for k in _TUNE_LOG_KOLON]
            # degismese de yazilir (kesintisiz zaman ekseni)
            f.write("%.3f," % time.time()
                    + ",".join("%g" % float(v) for v in vals) + "\n")
            f.flush()
        except Exception:
            pass
        time.sleep(1.0)


# Excel raporuna slider setine EK yazilan sabitler (kosu kosullari; hasattr ile okunur).
TUNE_SABIT_RAPOR = (
    "IBVS_SIGN_YAW", "IBVS_SIGN_DIKEY", "IBVS_TILT_DEG", "IBVS_VFOV_HALF_DEG",
    "VIS_WIN_NEED_S", "VIS_LOCK_PCT", "VIS_STALE_S",
)

# ----------------------------------------------------------
#  MANUEL MOD (klavyeyle kontrol; gorev_aktif ile karsilikli dislar)
# ----------------------------------------------------------
manuel_aktif = False
# Tarayicidan gelen son kontrol komutu (hepsi -1..1)
manuel_kontrol = {"throttle": 0.0, "pitch": 0.0, "roll": 0.0, "yaw": 0.0}
manuel_son_giris = 0.0       # son manuel giris zamani (failsafe)
MANUEL_TIMEOUT = 0.7         # sn: bu sureden uzun giris gelmezse HOVER'a gec

# ----------------------------------------------------------
#  SAPMA OLCUMU: uretim GNSS filtresinin gercege hatasi + ham taban. Gudume dokunmaz.
# ----------------------------------------------------------
_kiyas_filtre = GNSSFiltre()   # uretim filtresi ornegi (yalniz sapma olcumu)
_kiyas_idx = 0
_kiyas_son_ham = None
# Son ~80 olcumun penceresi
_kiyas_ham_hata = deque(maxlen=80)
_kiyas_filtre_hata = deque(maxlen=80)

# Olcum CSV log: her paket icin ham/J hatasi (m).
_KIYAS_LOG = os.path.join(VERI_DIR, "kiyas_log.csv")
try:
    _kiyas_log_f = open(_KIYAS_LOG, "w", encoding="utf-8")
    _kiyas_log_f.write("paket,ham_m,j_m\n")
    _kiyas_log_f.flush()
except Exception:
    _kiyas_log_f = None

# --- GPS SAPMA LOGU (bozuk + gercek konum; sapma analizi icin) ----------------
# Her yeni ham pakette bozuk+gercek konum + zaman + corruption biriktirilir,
# ~5 sn'de bir atomik yazilir. Gudume dokunmaz.
_GPS_LOG = os.path.join(VERI_DIR, "gps_log_canli.json")
_gps_log_kayitlar = []
_gps_log_t0 = None
_gps_log_son_yaz = 0.0


# ============================================================
#  GOREV OLAY GUNLUGU + GOREV IZLEYICI  (video isterleri 3/4/6/7/8/9/10)
#  GUDUME DOKUNMAZ: her sey beyin'in var olan alanlarindan kenar-tespitiyle
#  (onceki tik <-> bu tik) turetilir. ana_kontrol.py / gorsel_tespit.py degismez.
# ============================================================
GNSS_KESINTI_S    = 1.0    # sn; hedef GPS paketi bu suredir yenilenmediyse KESINTI
VURUS_ESIK_M      = 3.0    # m; angajmanda mesafe bu esigin altinda -> VURUS
BASARI_GECIKME_S  = 1.5    # sn; VURUS latch'inden sonra BASARI ilani
TAKIP_TAM_KAYIP_S = Cfg.VIS_STALE_S + Cfg.VIS_LOST_TO_GPS_S   # ~2.5 s; takip-ID kapanma esigi

olay_lock = threading.Lock()          # yaprak kilit
_olaylar  = deque(maxlen=400)         # {"id","t","sv","m"}
_olay_id  = 0


def olay_ekle(sv, mesaj):
    """Gorev olayini gunluge ekle. sv: bilgi|iyi|uyari|kritik. Thread-safe."""
    global _olay_id
    with olay_lock:
        _olay_id += 1
        _olaylar.append({"id": _olay_id, "t": time.time(), "sv": sv, "m": mesaj})


# --- Izleyici durumu: yalniz kontrol thread'i yazar; build_telemetry beyin_lock ile okur ---
# id: gercek ByteTrack track_id (yoksa sentetik sayac). ilk: bu gorevde ILK TESPIT ilan edildi mi.
_takip = {"id": None, "sonraki": 1, "yeniden": 0, "aktif": False, "kayip_t": None, "ilk": False}
_gorev = {"faz": "HAZIR", "t0": None, "vurus": False, "basari": False,
          "en_yakin_m": None, "vurus_t": None, "mesafe_kaynak": None}
_izci = {"durum_prev": None, "handoff_prev": False, "kilit_ilan": False,
         "angajman_ilan": False, "angajman_min": None, "iska_ilan": False,
         "kesinti": False, "son_paket_t": None, "kilit_ok_prev": False}


def _gorev_sifirla(faz):
    """Yeni gorev baslarken izleyici latch'lerini sifirla (basari banner'i dahil)."""
    _takip.update(id=None, sonraki=1, yeniden=0, aktif=False, kayip_t=None, ilk=False)
    _gorev.update(faz=faz, t0=time.time(), vurus=False, basari=False,
                  en_yakin_m=None, vurus_t=None, mesafe_kaynak=None)
    _izci.update(durum_prev=None, handoff_prev=False, kilit_ilan=False,
                 angajman_ilan=False, angajman_min=None, iska_ilan=False,
                 kilit_ok_prev=False)


def _mesafe_olc():
    """VURUS/BASARI mesafesi (m): truth varsa gercek 3B, yoksa filtre-temiz; ham asla.
    -> (mesafe_m, kaynak) | (None, None)."""
    truth = drone.get_debug_truth()
    if truth.get("available"):
        adx, ady, adz = truth["drone"]["position"]
        tgx, tgy, tgz = truth["target"]["position"]
        d = ((adx - tgx) ** 2 + (ady - tgy) ** 2 + (adz - tgz) ** 2) ** 0.5
        return d * CM_TO_M, "gercek"
    if beyin.son_xy_anlik is not None and beyin.son_z_anlik is not None:
        dp = drone.get_drone_location()
        tx, ty, tz = float(beyin.son_xy_anlik[0]), float(beyin.son_xy_anlik[1]), float(beyin.son_z_anlik)
        d = ((dp[0] - tx) ** 2 + (dp[1] - ty) ** 2 + (dp[2] - tz) ** 2) ** 0.5
        return d * CM_TO_M, "temiz"
    return None, None


def _gorev_izle():
    """Her tik (beyin_lock altinda): beyin alanlarindan olay/durum turetir. Gudume dokunmaz."""
    now = time.time()

    # 1) GNSS KESINTI: paket yasi
    spt = _izci["son_paket_t"]
    yas = (now - spt) if spt is not None else None
    kesinti_simdi = (yas is not None and yas > GNSS_KESINTI_S)
    if kesinti_simdi and not _izci["kesinti"]:
        _izci["kesinti"] = True
        olay_ekle("uyari", "GNSS KESINTISI — hedef GPS paketi gelmiyor")
    elif (not kesinti_simdi) and _izci["kesinti"]:
        _izci["kesinti"] = False
        olay_ekle("iyi", "GNSS geri geldi — kesinti bitti (%.1f s)" % (yas if yas else 0.0))

    if not gorev_aktif:
        return   # gorev pasif: FSM/takip/vurus izlenmez (sadece kesinti yukarida)

    # 2) TAKIP-ID makinesi (girdi: beyin.son_tespit_t tazeligi; ID = ByteTrack track_id)
    stt = beyin.son_tespit_t
    taze = (stt is not None) and ((time.perf_counter() - stt) <= Cfg.VIS_STALE_S)
    if taze:
        gid, conf = None, 0.0
        try:
            gid = beyin.son_tespit.get("track_id")
            conf = float(beyin.son_tespit.get("conf", 0.0))
        except Exception:
            pass
        if _takip["id"] is None:                       # ACILIS
            _takip["id"] = gid if gid is not None else _takip["sonraki"]
            try:
                _takip["sonraki"] = int(_takip["id"]) + 1   # sentetik sayac gercek ID'yi gecmesin
            except Exception:
                pass
            _takip["kayip_t"] = None
            if not _takip["ilk"]:
                _takip["ilk"] = True
                olay_ekle("iyi", "ILK TESPIT — ID:%s (talon, conf=%.2f)" % (_takip["id"], conf))
            else:
                _takip["yeniden"] += 1
                olay_ekle("iyi", "YENIDEN TESPIT — yeni ID:%s (conf=%.2f)" % (_takip["id"], conf))
        elif gid is not None and gid != _takip["id"]:  # taze ama IZ DEGISTI (ByteTrack yeni track acti)
            _takip["id"] = gid
            try:
                _takip["sonraki"] = int(gid) + 1
            except Exception:
                pass
            _takip["yeniden"] += 1
            _takip["kayip_t"] = None
            olay_ekle("iyi", "YENIDEN TESPIT — yeni ID:%s (conf=%.2f)" % (gid, conf))
        elif not _takip["aktif"]:                      # blip koprulendi
            olay_ekle("iyi", "TAKIP SURUYOR — ID:%s korundu" % _takip["id"])
            _takip["kayip_t"] = None
        _takip["aktif"] = True
    else:
        if _takip["id"] is not None:
            if _takip["aktif"]:
                _takip["aktif"] = False
                _takip["kayip_t"] = now
                olay_ekle("uyari", "TESPIT KAYBI — ID:%d (kor-devam)" % _takip["id"])
            elif _takip["kayip_t"] is not None and (now - _takip["kayip_t"]) >= TAKIP_TAM_KAYIP_S:
                olay_ekle("uyari", "TAKIP KAPANDI — ID:%d (%.1f s kayip)"
                          % (_takip["id"], now - _takip["kayip_t"]))
                _takip["id"] = None
                _takip["kayip_t"] = None

    # 3) FSM kenarlari (beyin.durum / beyin.handoff / kilit sayaci)
    durum = beyin.durum
    if durum != _izci["durum_prev"]:
        if durum == "GORSEL_GUDUM":
            olay_ekle("iyi", "GORSEL GUDUME GECILDI — GPS yonelimi KAPALI (yonelim yalniz kamera)")
        elif durum in ("ARAMA", "KILIT") and _izci["durum_prev"] == "GORSEL_GUDUM":
            olay_ekle("uyari", "GPS'e DONULDU — yeniden yaklasma")
        _izci["durum_prev"] = durum
    if beyin.handoff and not _izci["handoff_prev"]:
        olay_ekle("bilgi", "Tespit menzilinde — KILIT")
    _izci["handoff_prev"] = bool(beyin.handoff)
    if (not _izci["kilit_ilan"]) and beyin._vis_pos_count >= Cfg.VIS_N_LOCK:
        _izci["kilit_ilan"] = True
        olay_ekle("iyi", "GORSEL KILIT hazir (%d/%d)" % (beyin._vis_pos_count, Cfg.VIS_N_LOCK))
    elif beyin._vis_pos_count == 0:
        _izci["kilit_ilan"] = False

    # 3.5) KILITLENME ISTERI kenari (beyin.kilit_ok latch'i; sartname 6.1.2/6.1.4)
    if getattr(beyin, "kilit_ok", False) and not _izci["kilit_ok_prev"]:
        _izci["kilit_ok_prev"] = True
        olay_ekle("iyi", "KILIT ISTERI SAGLANDI — 10 sn pencerede >= %.0f sn kumulatif kilit"
                  % float(getattr(Cfg, "VIS_WIN_NEED_S", 5.0)))
    elif not getattr(beyin, "kilit_ok", False):
        _izci["kilit_ok_prev"] = False

    # 4) GOREV FAZI + VURUS/BASARI (mesafe 50 Hz olculur -> vurus ani atlanmaz)
    mesafe, kaynak = _mesafe_olc()
    if mesafe is not None:
        if _gorev["en_yakin_m"] is None or mesafe < _gorev["en_yakin_m"]:
            _gorev["en_yakin_m"] = mesafe

    # ANGAJMAN: gorsel faz + takip canli + kilit isteri saglanmis (sartname 6.1.3)
    angajman = (durum == "GORSEL_GUDUM" and _takip["aktif"] and bool(getattr(beyin, "kilit_ok", False)))

    if _gorev["basari"]:
        _gorev["faz"] = "BASARI"
    elif _gorev["vurus"]:
        _gorev["faz"] = "VURUS"
        if _gorev["vurus_t"] is not None and (now - _gorev["vurus_t"]) >= BASARI_GECIKME_S:
            _gorev["basari"] = True
            _gorev["faz"] = "BASARI"
            olay_ekle("iyi", "GOREV BASARILI — HEDEF DUSURULDU")
    elif angajman:
        _gorev["faz"] = "ANGAJMAN"
        if not _izci["angajman_ilan"]:
            _izci["angajman_ilan"] = True
            olay_ekle("kritik", "ANGAJMAN — kilit isteri dolu, gorsel (IBVS) yaklasma suruyor")
        if mesafe is not None and mesafe < VURUS_ESIK_M:          # VURUS latch (kalici)
            _gorev["vurus"] = True
            _gorev["vurus_t"] = now
            _gorev["mesafe_kaynak"] = kaynak
            olay_ekle("kritik", "VURUS! mesafe=%.1f m (%s kaynak)" % (mesafe, kaynak))
        elif mesafe is not None:                                  # ISKA tespiti (angajman icinde)
            am = _izci["angajman_min"]
            if am is None or mesafe < am:
                _izci["angajman_min"] = mesafe
            elif (not _izci["iska_ilan"]) and mesafe > am + 15.0:
                _izci["iska_ilan"] = True
                olay_ekle("uyari", "ISKA — en yakin %.1f m; yeniden angajman" % am)
    else:
        _izci["angajman_ilan"] = False
        _izci["angajman_min"] = None
        _izci["iska_ilan"] = False
        # GORSEL_GUDUM ama kilit isteri henuz dolmadi -> KILIT cipi
        _gorev["faz"] = "KILIT" if durum in ("KILIT", "GORSEL_GUDUM") else "YAKLASMA"


def _gps_log_yaz():
    """Biriken bozuk/gercek konum logunu diske atomik yaz."""
    if not _gps_log_kayitlar:
        return
    try:
        veri = {
            "birim": "cm (SDK ham)",
            "eksenler": ["x", "y", "z"],
            "aciklama": "web/server.py canli log: bozuk=get_target_location, "
                        "gercek=get_debug_truth target",
            "ornek_sayisi": len(_gps_log_kayitlar),
            "kayitlar": _gps_log_kayitlar,
        }
        tmp = _GPS_LOG + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(veri, f, indent=2)
        os.replace(tmp, _GPS_LOG)
    except Exception:
        pass


def _kiyas_guncelle():
    """Her yeni ham pakette GNSS filtresini besle, gercege hatasini olc."""
    global _kiyas_idx, _kiyas_son_ham, _gps_log_t0, _gps_log_son_yaz
    ham = drone.get_target_location()
    if ham == _kiyas_son_ham:
        return
    _kiyas_son_ham = ham
    _izci["son_paket_t"] = time.time()    # yeni paket -> kesinti izleyici yasi sifirlanir
    truth = drone.get_debug_truth()
    if not truth.get("available"):
        return
    gercek = np.array(truth["target"]["position"], float)

    # --- GPS sapma logu: bozuk + gercek konum + aktif corruption ---
    _now = time.time()
    if _gps_log_t0 is None:
        _gps_log_t0 = _now
    _gps_log_kayitlar.append({
        "t": round(_now - _gps_log_t0, 3),
        "bozuk": [round(float(c), 3) for c in ham],
        "gercek": [round(float(c), 3) for c in gercek],
        "corruption": drone.get_active_corruption(),
    })
    if _now - _gps_log_son_yaz > 5.0:   # her ~5 sn diske flush
        _gps_log_yaz()
        _gps_log_son_yaz = _now

    idx = _kiyas_idx
    _kiyas_idx += 1
    hx, hy, hz = ham
    ham_e = float(np.linalg.norm(np.array(ham, float) - gercek))
    _kiyas_ham_hata.append(ham_e)
    filtre_e = None

    # GNSS filtre: telafisiz anlik temiz konum (durum_gudum["pos"]) -> gercekle karsilastir
    _kiyas_filtre.guncelle(hx, hy, hz)
    durum = _kiyas_filtre.durum_gudum()
    if durum is not None:
        filtre_e = float(np.linalg.norm(np.array(durum["pos"], float) - gercek))
        _kiyas_filtre_hata.append(filtre_e)

    # CSV log (metre): bos sutun = o pakette cikti yok
    if _kiyas_log_f is not None:
        he = "%.2f" % (ham_e / 100.0)
        js = ("%.2f" % (filtre_e / 100.0)) if filtre_e is not None else ""
        try:
            _kiyas_log_f.write("%d,%s,%s\n" % (idx, he, js))
            _kiyas_log_f.flush()
        except Exception:
            pass


def _manuel_uygula():
    """Manuel modda son kontrol komutunu drona gonderir; giris bayatsa HOVER (failsafe)."""
    if time.time() - manuel_son_giris > MANUEL_TIMEOUT:
        thr = pit = rol = yaw = 0.0       # giris bayat -> sabit hover
    else:
        thr = manuel_kontrol["throttle"]
        pit = manuel_kontrol["pitch"]
        rol = manuel_kontrol["roll"]
        yaw = manuel_kontrol["yaw"]
    drone.set_control_surfaces(thr, pit, rol, yaw, True)


def kontrol_dongusu():
    while True:
        if drone.is_connected():
            try:
                with beyin_lock:
                    if manuel_aktif:
                        beyin._hedef_temizle()    # J telemetrisi pasif aksin
                        _manuel_uygula()          # klavye komutunu uygula
                    elif gorev_aktif:
                        beyin.adim()              # tam kontrol (drone hedefe gider)
                    else:
                        beyin._hedef_temizle()    # sadece J'yi guncelle (olcum)
                        if beyin.debug_olc:
                            beyin._debug_olc()    # ham vs J hatasini olc
                    _kiyas_guncelle()             # GNSS filtre sapma olcumu (hep calisir)
                    try:
                        _gorev_izle()             # olay/durum izleyici (gudume dokunmaz)
                    except Exception as e:
                        if not _izci.get("_hata_bildirildi"):
                            _izci["_hata_bildirildi"] = True
                            print("[IZLEYICI HATA] %r" % e)
            except Exception:
                pass
        time.sleep(0.02)   # 50 Hz


# ----------------------------------------------------------
#  GORSEL TESPIT (YOLO best.pt) — AYRI thread.
#  Agir inference beyin_lock DISINDA kosar, sonuc kilit ICINDE beyne yazilir.
#  Lazy yukleme; ultralytics/torch yoksa hazir=False -> sistem GPS ile devam eder.
# ----------------------------------------------------------
dedektor = None
_son_tespit_ui = None      # UI/telemetri icin son normalize tespit

# --- POZ KESTIRIMI (talon_pose.pt + PnP) — PARALEL GOZLEMCI --------------------
# best.pt akisina ILAVE kosar (6 keypoint + PnP -> kameradan mesafe/yonelim).
# Gudume girmez, sadece overlay/telemetri besler.
POSE_MODEL_PATH = getattr(Cfg, "VIS_POSE_MODEL_PATH",
                          os.path.join(PROJ_ROOT, "models", "talon_pose.pt"))
# POSE KAPALI (kullanici istegi): sadece detection (bbox) kalsin, GPU bbox'a.
POSE_AKTIF = False
poz_dedektor = None        # PozDedektor | None (lazy; ilk gorev tikinde denenir)
poz_cozucu = None          # pose.poz_cozucu.PozCozucu (PnP + EMA)
_poz_sira = None           # model kpt sirasi -> talon_keypoints.json REF sirasi
_son_poz_ui = None         # UI icin son NORMALIZE poz (beyin_lock ile korunur)


def _normalize_tespit(det):
    """Dedektor px ciktisini overlay/telemetri icin normalize et (cozunurluk-bagimsiz)."""
    if det is None:
        return None
    W = float(det.get("W", 0) or 0); H = float(det.get("H", 0) or 0)
    if W <= 1 or H <= 1:
        return None
    cls = int(det.get("cls", -1))                  # dedektor sinif indeksi
    sinif = "hedef"
    try:
        if dedektor is not None and getattr(dedektor, "names", None):
            sinif = dedektor.names.get(cls, "hedef")
    except Exception:
        pass
    return {
        "ex": (det["cx"] - W / 2.0) / (W / 2.0),   # + = hedef SAGDA
        "ey": (det["cy"] - H / 2.0) / (H / 2.0),   # + = hedef ALTTA
        "cx": det["cx"] / W, "cy": det["cy"] / H,  # normalize merkez [0..1]
        "w": det["w"] / W, "h": det["h"] / H,      # normalize bbox boyut [0..1]
        "conf": float(det.get("conf", 0.0)),
        "cls": cls, "sinif": sinif,                # hedef ID etiketi (overlay)
        # ByteTrack alanlari: iz kimligi + coast bayragi (tespit_mi=False -> Kalman tahmini)
        "track_id": det.get("track_id"),
        "track_durumu": det.get("track_durumu"),
        "tespit_mi": bool(det.get("tespit_mi", True)),
    }


def _normalize_poz(pdet, poz, yaw_pitch):
    """Poz + PnP ciktisini UI icin normalize et (kp REF sirasina cevrilir)."""
    if pdet is None:
        return None
    W = float(pdet.get("W", 0) or 0); H = float(pdet.get("H", 0) or 0)
    if W <= 1 or H <= 1:
        return None
    kp_ref = [None] * 6
    for i in range(6):
        r = _poz_sira[i] if _poz_sira else i
        u, v = pdet["kp_xy"][i]
        kp_ref[r] = [u / W, v / H, round(float(pdet["kp_conf"][i]), 3)]
    d = {"kp": kp_ref, "conf": float(pdet.get("conf", 0.0)),
         "ok": poz is not None,                      # ok=False: nokta var, PnP oturmadi
         "t_poz": float(pdet.get("t", time.perf_counter()))}   # kare zamani (yas telafisi)
    if poz is not None:
        d["mesafe_m"] = poz["mesafe_cm"] / 100.0
        d["mesafe_ema_m"] = poz["mesafe_ema_cm"] / 100.0
        d["aspect_deg"] = poz["aspect_deg"]
        d["rms_px"] = poz["rms_px"]
        d["n_kp"] = poz["n_kp"]
        if yaw_pitch is not None:                    # dunya yonelimi (tilt'e bagli)
            d["yaw_deg"] = yaw_pitch[0] % 360.0
            d["pitch_deg"] = yaw_pitch[1]
    return d


# ----------------------------------------------------------
#  DEDEKTOR DEBUG PENCERESI (istege bagli): set AVCI_DEBUG_PENCERE=1 ile ac.
#  Islenen karenin uzerine AYNI karenin tespit/poz ciktisini OpenCV penceresinde
#  cizer (kare<->cikti senkron). Guduma etkisi yok; kapaliyken sifir maliyet.
# ----------------------------------------------------------
DEBUG_PENCERE = os.environ.get("AVCI_DEBUG_PENCERE", "0").strip() == "1"
_DEBUG_PENCERE_W = 960          # gosterim genisligi px
# OLCUM MODU: set AVCI_OLC_TESPIT=1 -> her tespitin normalize kutusunu (PROP_MASKE icin) basar.
OLC_TESPIT = os.environ.get("AVCI_OLC_TESPIT", "0").strip() == "1"


def _debug_pencere_goster(bgr, det, det_gecti, poz):
    """Islenen kare uzerine tespit/poz ciktisini ciz (dedektor_dongusu thread'inde)."""
    h, w = bgr.shape[:2]
    s = _DEBUG_PENCERE_W / float(w)
    hd = int(h * s)
    img = cv2.resize(bgr, (_DEBUG_PENCERE_W, hd))
    for m in (getattr(Cfg, "PROP_MASKE", None) or []):       # pervane maskesi (koyu kirmizi)
        cv2.rectangle(img, (int(m[0] * _DEBUG_PENCERE_W), int(m[1] * hd)),
                      (int(m[2] * _DEBUG_PENCERE_W), int(m[3] * hd)), (0, 0, 180), 1)
    if det is not None:
        renk = (0, 220, 0) if det_gecti else (0, 165, 255)   # yesil=gudume gitti, turuncu=zayif
        x0 = int((det["cx"] - det["w"] / 2) * s); y0 = int((det["cy"] - det["h"] / 2) * s)
        x1 = int((det["cx"] + det["w"] / 2) * s); y1 = int((det["cy"] + det["h"] / 2) * s)
        cv2.rectangle(img, (x0, y0), (x1, y1), renk, 2)
        cv2.putText(img, "%.2f" % float(det.get("conf", 0.0)), (x0, max(14, y0 - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, renk, 1, cv2.LINE_AA)
    if poz is not None and poz.get("kp"):
        pts = [None if (p is None or p[2] < 0.25) else
               (int(p[0] * _DEBUG_PENCERE_W), int(p[1] * hd)) for p in poz["kp"]]
        for a, b in ((0, 5), (1, 2), (0, 1), (0, 2), (3, 5), (4, 5), (3, 4)):
            if pts[a] and pts[b]:
                cv2.line(img, pts[a], pts[b], (230, 230, 90), 1, cv2.LINE_AA)
        for p in pts:
            if p:
                cv2.circle(img, p, 3, (255, 200, 0), -1)
    cv2.putText(img, "DEDEKTOR GOZU (kare<->tespit senkron)", (8, 18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.imshow("AVCI dedektor", img)
    cv2.waitKey(1)                                           # pencere olay dongusu (1 ms)


# ----------------------------------------------------------
#  DEDEKTOR PERFORMANS OLCUMU: her inference'in gercek suresi (cuda.synchronize ile)
#  olculur; ort/p95 + FPS telemetriye ve perf_log'a yazilir. Gudume dokunmaz.
# ----------------------------------------------------------
_perf = {"det_ms": None, "det_p95": None, "poz_ms": None, "fps": None, "gpu": None}
_perf_det = deque(maxlen=120)     # best.pt inference ms
_perf_poz = deque(maxlen=60)      # pose inference ms
_perf_dongu = deque(maxlen=120)   # dongu periyodu (s) -> FPS
# KALICI PERF LOGU: ~1 Hz veri/perf_log_*.csv; her gorev basinda yeni dosya.
_perf_log_f = None
_perf_log_path = None


def _perf_log_yaz(det_ms, det_p95, poz_ms, fps, gpu):
    global _perf_log_f, _perf_log_path
    if _perf_log_f is None:
        try:
            _perf_log_path = os.path.join(VERI_DIR, time.strftime("perf_log_%Y%m%d_%H%M%S.csv"))
            _perf_log_f = open(_perf_log_path, "w", encoding="utf-8")
            _perf_log_f.write("t_wall,det_ms,det_p95,poz_ms,fps,gpu\n")
        except Exception:
            _perf_log_f = None
            return
    try:
        _perf_log_f.write("%.1f,%s,%s,%s,%s,%s\n" % (
            time.time(), det_ms, det_p95, poz_ms, fps, gpu))
        _perf_log_f.flush()
    except Exception:
        pass


def _cuda_senkron():
    """GPU async kernel'i bitene kadar bekle -> olculen sure gercek latency olsun."""
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.synchronize()
    except Exception:
        pass


def _perf_ozet(p95_kaynak):
    """deque -> (ort, p95) ms; bos ise (None, None)."""
    if not p95_kaynak:
        return None, None
    v = sorted(p95_kaynak)
    ort = sum(v) / len(v)
    p95 = v[min(len(v) - 1, int(0.95 * len(v)))]
    return round(ort, 1), round(p95, 1)


def dedektor_dongusu():
    global dedektor, _son_tespit_ui, poz_dedektor, poz_cozucu, _poz_sira, _son_poz_ui
    from detection.gorsel_tespit import HedefDedektor   # ultralytics opsiyonel (import-guard modulde)
    from detection.takip import Takipci                  # ByteTrack: ID surekliligi + coast + FP filtresi
    from detection import kamera_model                   # gyro-CMC homografisi
    takipci = Takipci()                                  # zamansal takip (guduma dokunmaz)
    onceki_att = None                                    # onceki tur drone rotasyonu (CMC icin)
    onceki_takip_t = None                                # onceki takip guncelleme ani (Kalman dt)
    poz_sayac = 0                                        # POZ_HER_N sayaci
    onceki_ui = None                                     # (cx, cy, t, track_id) — UI hiz kestirimi
    _t_dongu = None                                      # onceki dongu damgasi (FPS)
    _t_konsol = 0.0                                      # son konsol ozeti zamani
    while True:
        # Sadece otonom gorev sirasinda tespit yap
        if not (drone.is_connected() and gorev_aktif and not manuel_aktif):
            if takipci.trackler:                         # yeni gorev bayat track ile baslamasin
                takipci.sifirla()
            onceki_att = onceki_takip_t = None
            time.sleep(0.05)
            continue
        if dedektor is None:                          # LAZY: ilk gorev tikinde yukle
            # imgsz=960 (aktif model 960'ta egitildi). SAHI yalniz best.pt'ye uygulanir.
            dedektor = HedefDedektor(Cfg.VIS_MODEL_PATH, conf=Cfg.VIS_CONF_MIN,
                                     imgsz=960, half=FP16_AKTIF,
                                     sahi=bool(getattr(Cfg, "SAHI_AKTIF", False)),
                                     sahi_dilim=getattr(Cfg, "SAHI_DILIM_PX", 640),
                                     sahi_ortusme=getattr(Cfg, "SAHI_ORTUSME", 0.2),
                                     sahi_tam_kare=getattr(Cfg, "SAHI_TAM_KARE", True),
                                     sahi_nms_iou=getattr(Cfg, "SAHI_NMS_IOU", 0.5),
                                     sahi_kosul_conf=getattr(Cfg, "SAHI_KOSUL_CONF", 0.5))
            if dedektor.hazir:
                print("[GORSEL] best.pt yuklendi (device=%s, half=%s, sahi=%s). Siniflar: %s"
                      % (dedektor.device, dedektor.half, dedektor.sahi, dedektor.names))
            else:
                print("[GORSEL] Dedektor YUKLENEMEDI (%s) -> sistem GPS ile devam eder."
                      % dedektor.hata)
        if not dedektor.hazir:
            time.sleep(1.0)                           # kurulum yok -> CPU yakma
            continue
        try:
            # Predict esigi UI icin dusuk (UI_CONF_MIN); gudum yalnizca conf>=VIS_CONF_MIN
            # gorur (det_beyin kapisi). Tracker acikken taban CONF_DUSUK (BYTE 2. turu).
            takip_aktif = bool(getattr(Cfg, "TAKIP_AKTIF", True))
            if takip_aktif:
                dedektor.conf = min(UI_CONF_MIN, float(Cfg.VIS_CONF_MIN), takipci.cfg.CONF_DUSUK)
            else:
                dedektor.conf = min(UI_CONF_MIN, float(Cfg.VIS_CONF_MIN))
            bgr, _fw, _fh = grab_frame_bgr()          # AGIR is: pencere karesi al (kilit disinda)
            # Pervane maskesi canli okunur (Cfg.PROP_MASKE); TUM kutular maske sonrasi alinir.
            _t_inf = time.perf_counter()
            dets = (dedektor.tespit_hepsi(bgr, maske=getattr(Cfg, "PROP_MASKE", None))
                    if bgr is not None else [])
            if bgr is not None:
                _cuda_senkron()
                _perf_det.append((time.perf_counter() - _t_inf) * 1000.0)
            # OLCUM MODU: maskesiz TUM kutulari normalize (x0,y0,x1,y1) bas
            if OLC_TESPIT and bgr is not None:
                _oh, _ow = bgr.shape[:2]
                for _d in dedektor.tespit_hepsi(bgr, maske=None):
                    _x0 = (_d["cx"] - _d["w"] / 2) / _ow; _y0 = (_d["cy"] - _d["h"] / 2) / _oh
                    _x1 = (_d["cx"] + _d["w"] / 2) / _ow; _y1 = (_d["cy"] + _d["h"] / 2) / _oh
                    print("[OLC] kutu=(%.3f, %.3f, %.3f, %.3f) conf=%.2f"
                          % (_x0, _y0, _x1, _y1, _d["conf"]))
        except Exception:
            bgr, dets = None, []
        # BYTETRACK + GYRO-CMC: kutulari zamansal bagla; det = en iyi CONFIRMED track | None.
        # TAKIP_AKTIF=False -> tracker atlanir, ham argmax (dets[0]) dogrudan gecer.
        det = None
        if bgr is not None and not takip_aktif:
            if takipci.trackler:
                takipci.sifirla()                     # kapaliyken bayat iz birikmesin
            det = dets[0] if dets else None           # tespit_hepsi conf-azalan -> [0] = argmax
        elif bgr is not None:
            simdi = time.perf_counter()
            H_cmc = None
            cmc_cap = None
            try:
                att = drone.get_drone_rotation()      # (roll,pitch,yaw) derece
                # gyro-CMC: kendi donusumuzun kutu kaymasini onceden telafi et
                # (TAKIP_CMC_SIGN ters cevirir; TAKIP_CMC_MAX_KAYDIRMA px tavani).
                if onceki_att is not None and getattr(Cfg, "TAKIP_CMC_AKTIF", False):
                    a1, a2 = onceki_att, att
                    if float(getattr(Cfg, "TAKIP_CMC_SIGN", 1.0)) < 0:
                        a1, a2 = a2, a1               # warp yonunu tersine cevir
                    H_cmc = kamera_model.cmc_homografi(bgr.shape[1], bgr.shape[0], a1, a2)
                    frac = float(getattr(Cfg, "TAKIP_CMC_MAX_KAYDIRMA", 0.0) or 0.0)
                    if frac > 0:
                        cmc_cap = frac * bgr.shape[1]  # kare genisligi orani -> px
            except Exception:
                att = None
            dt_takip = (simdi - onceki_takip_t) if onceki_takip_t is not None else 0.05
            onceki_att, onceki_takip_t = att, simdi
            det = takipci.guncelle(dets, dt_takip, H_cmc, cmc_cap, frame=bgr)
            if det is not None:
                det.setdefault("t", simdi)            # coast ciktisi: tahmin ani = simdi
        # GUDUM KAPISI: zayif/coast tespit beyne gitmez (gorsel faz kendi koprusunu yonetir).
        det_beyin = (det if det is not None and det.get("tespit_mi", True)
                     and float(det.get("conf", 0.0)) >= float(Cfg.VIS_CONF_MIN) else None)
        # POZ kestirimi: ayni kare uzerinde ILAVE inference + PnP (seyrek, her POZ_HER_N turda).
        # Gozlemci-only; hata poz'u None yapar, gudum akisini etkilemez.
        poz_ui, poz_kostu = None, False
        poz_sayac += 1
        if (poz_dedektor is not None and poz_dedektor.hazir
                and poz_cozucu is not None and bgr is not None
                and det is not None and det.get("tespit_mi", True)   # coast karesinde poz kosma
                and poz_sayac % POZ_HER_N == 0):
            poz_kostu = True
            try:
                _t_poz = time.perf_counter()
                pdet = poz_dedektor.tespit_et(bgr)
                _cuda_senkron()
                _perf_poz.append((time.perf_counter() - _t_poz) * 1000.0)
                if pdet is not None:
                    poz = poz_cozucu.coz(pdet["kp_xy"], pdet["kp_conf"],
                                         pdet["W"], pdet["H"], t=pdet["t"])
                    yp = None
                    if poz is not None:
                        try:   # dunya yaw/pitch: kare anindaki drone rotasyonuyla
                            yp = poz_cozucu.dunya_yonelim(poz, drone.get_drone_rotation())
                        except Exception:
                            yp = None
                    poz_ui = _normalize_poz(pdet, poz, yp)
            except Exception:
                poz_ui = None
        # UI tespiti + normalize hiz (vx,vy): arayuz bbox'u tespit yasi kadar ileri cizer.
        ui_det = _normalize_tespit(det)
        if ui_det is not None and det is not None:
            t_det = float(det.get("t", time.perf_counter()))
            ui_det["t_det"] = t_det
            # ayni track_id sarti: ID degistiyse (yeni iz) onceki konumdan hiz turetme
            if (onceki_ui is not None and onceki_ui[3] == ui_det.get("track_id")
                    and 0.0 < (t_det - onceki_ui[2]) < 0.5):
                dt_ui = t_det - onceki_ui[2]
                ui_det["vx"] = (ui_det["cx"] - onceki_ui[0]) / dt_ui
                ui_det["vy"] = (ui_det["cy"] - onceki_ui[1]) / dt_ui
            onceki_ui = (ui_det["cx"], ui_det["cy"], t_det, ui_det.get("track_id"))
        with beyin_lock:                              # sonucu anlik yaz (kilit icinde)
            beyin.set_gorsel_tespit(det_beyin)
            if poz_kostu and poz_ui is not None:      # taze poz -> beyne (ongorulu yaw lead)
                beyin.set_gorsel_poz(poz_ui)          # gorsel veri (keypoint); GPS/J degil
            _son_tespit_ui = ui_det
            if poz_kostu or det is None:              # ara turlarda son pozu tut; hedef yoksa temizle
                _son_poz_ui = poz_ui
        # DEBUG PENCERESI
        if DEBUG_PENCERE and cv2 is not None and bgr is not None:
            try:
                _debug_pencere_goster(bgr, det, det_beyin is not None,
                                      poz_ui if poz_ui is not None else _son_poz_ui)
            except Exception:
                pass                                  # gosterim hatasi dedektoru durdurmaz
        # OLCUM: dongu periyodu -> FPS (yalniz kare islenen turlar)
        if bgr is not None:
            _now = time.perf_counter()
            if _t_dongu is not None:
                dp = _now - _t_dongu
                if 0.0 < dp < 1.0:
                    _perf_dongu.append(dp)
            _t_dongu = _now
            _perf["det_ms"], _perf["det_p95"] = _perf_ozet(_perf_det)
            _perf["poz_ms"], _ = _perf_ozet(_perf_poz)
            _perf["fps"] = (round(len(_perf_dongu) / sum(_perf_dongu), 1)
                            if _perf_dongu and sum(_perf_dongu) > 0 else None)
            if _perf["gpu"] is None:
                try:
                    import torch
                    _perf["gpu"] = (torch.cuda.get_device_name(0)
                                    if torch.cuda.is_available() else "CPU")
                except Exception:
                    _perf["gpu"] = "?"
            # periyodik CSV (her ~1 sn)
            if _now - _t_konsol > 1.0:
                _t_konsol = _now
                _perf_log_yaz(_perf["det_ms"], _perf["det_p95"], _perf["poz_ms"],
                              _perf["fps"], _perf["gpu"])
        else:
            time.sleep(0.05)                          # oyun karesi henuz yok


# ----------------------------------------------------------
#  Telemetriyi oku ve arayuz icin sade sozluge cevir (konum m, hiz m/s + km/h).
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

    # Avci-hedef 3B mesafe — HAM GPS ile (bozuk; ekrandaki ana deger)
    distance_m = ((dx - tx) ** 2 + (dy - ty) ** 2 + (dz - tz) ** 2) ** 0.5

    # (Debug) Gercek (bozulmamis) degerler - oyunda debug acikken gelir.
    truth = drone.get_debug_truth()
    debug_info = {"available": bool(truth.get("available"))}
    gercek_mesafe_m = None                       # avci <-> GERCEK hedef 3B mesafe (debug varsa)
    if debug_info["available"]:
        adx, ady, adz = (c * CM_TO_M for c in truth["drone"]["position"])
        tgx, tgy, tgz = (c * CM_TO_M for c in truth["target"]["position"])
        debug_info["drone_real"] = {"x": adx, "y": ady, "z": adz}
        debug_info["target_real"] = {"x": tgx, "y": tgy, "z": tgz}
        # GERCEK mesafe: gercek avci konumu <-> gercek hedef konumu (bozulmamis)
        gercek_mesafe_m = ((adx - tgx) ** 2 + (ady - tgy) ** 2 + (adz - tgz) ** 2) ** 0.5
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
        j_kaynak = beyin.kaynak           # aktif guduum kaynagi (filtre / gercek)
        j_temiz = None if beyin.son_temiz is None else (
            float(beyin.son_temiz[0]), float(beyin.son_temiz[1]), float(beyin.son_temiz[2]))
        ham_list = list(beyin.ham_hatalar)
        j_list = list(beyin.filtre_hatalar)
        vis_tespit = _son_tespit_ui       # normalize son tespit (dedektor thread yazar)
        vis_poz = _son_poz_ui             # normalize son POZ kestirimi (ayni thread yazar)
        vis_pos = beyin._vis_pos_count
        vis_lost = beyin._vis_lost_count
        vis_mode = getattr(beyin, "vis_mode", "OTO")   # guduum pipeline switch
        ibvs_tlm = dict(getattr(beyin, "ibvs_tlm", {}) or {})  # gorsel IBVS ic durumu
        # KILITLENME ISTERI sayaci (sartname 6.1.2/6.1.4)
        b_kilit = {"anlik": bool(getattr(beyin, "kilit_anlik", False)),
                   "sure": round(float(getattr(beyin, "kilit_sure", 0.0)), 2),
                   "gerek": float(getattr(Cfg, "VIS_WIN_NEED_S", 5.0)),
                   "pencere": float(getattr(Cfg, "VIS_WIN_S", 10.0)),
                   "ok": bool(getattr(beyin, "kilit_ok", False)),
                   "esik_pct": float(getattr(Cfg, "VIS_LOCK_PCT", 0.06)),
                   "boyut_pct": (round(float(beyin.kilit_boyut), 4)
                                 if getattr(beyin, "kilit_boyut", None) is not None else None)}
        # --- IZLEYICI/GUDUM alanlari (video isterleri) — anlik kopya ---
        prev_cmd = dict(beyin.prev)                    # uygulanan 4 komut
        b_handoff = bool(beyin.handoff)
        son_xy = None if beyin.son_xy_anlik is None else (
            float(beyin.son_xy_anlik[0]), float(beyin.son_xy_anlik[1]))
        son_ham_full = None if beyin.son_ham is None else (
            float(beyin.son_ham[0]), float(beyin.son_ham[1]), float(beyin.son_ham[2]))
        son_z_anl = None if beyin.son_z_anlik is None else float(beyin.son_z_anlik)
        takip_s = dict(_takip)
        gorev_s = dict(_gorev)
        izci_kesinti = bool(_izci["kesinti"])
        izci_spt = _izci["son_paket_t"]
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

    # Sapma ozeti (gercege hata, metre): uretim GNSS filtresi + Ham taban cizgisi
    with beyin_lock:
        ham_h = list(_kiyas_ham_hata)
        j_h = list(_kiyas_filtre_hata)
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

    # (GECICI TANI) kontrolcunun son gonderdigi dikey/ileri komut (drone davranisini degistirmez)
    try:
        _cmd_thr = float(drone._drone.throttle)
        _cmd_pit = float(drone._drone.pitch)
    except Exception:
        _cmd_thr = _cmd_pit = None

    # --- IZLEYICI TELEMETRISI (video isterleri 3/6/7/8/9/10) ---
    _now = time.time()
    # d_h (yatay mesafe, m): temiz kestirim, yoksa ham
    d_h_m = None
    _txy = son_xy if son_xy is not None else (
        (son_ham_full[0], son_ham_full[1]) if son_ham_full is not None else None)
    if _txy is not None:
        d_h_m = (((dpos[0] - _txy[0]) ** 2 + (dpos[1] - _txy[1]) ** 2) ** 0.5) * CM_TO_M
    # J duzeltme buyuklugu (truth GEREKTIRMEZ): ham <-> anlik temiz fark (m)
    j_duzeltme_m = None
    if son_ham_full is not None and son_xy is not None and son_z_anl is not None:
        _jd = ((son_ham_full[0] - son_xy[0]) ** 2 + (son_ham_full[1] - son_xy[1]) ** 2
               + (son_ham_full[2] - son_z_anl) ** 2) ** 0.5
        j_duzeltme_m = _jd * CM_TO_M
    paket_yasi_s = (_now - izci_spt) if izci_spt is not None else None

    gnss_info = {
        "paket_yasi_s": paket_yasi_s,
        "kesinti": izci_kesinti,
        "bozulmalar": list(debug_info.get("corruptions", [])),
        "ham_hata_m": debug_info.get("target_raw_error_m"),
        "j_duzeltme_m": j_duzeltme_m,
    }
    gudum_info = {
        "thr": prev_cmd.get("thr", 0.0), "pitch": prev_cmd.get("pitch", 0.0),
        "roll": prev_cmd.get("roll", 0.0), "yaw": prev_cmd.get("yaw", 0.0),
        "durum": j_durum, "mod": vis_mode, "kaynak": j_kaynak,
        "handoff": b_handoff, "d_h_m": d_h_m,
        "law": "IBVS",                              # tek gorsel yasa: basit IBVS (merkez->bbox cizgisi)
        "ibvs": ibvs_tlm,                           # {law,ex,ey,buyukluk,aci_deg,kisma,dikey,ileri,yaw} | {}
    }
    kayip_s = 0.0
    if takip_s.get("id") is not None and (not takip_s.get("aktif")) and takip_s.get("kayip_t"):
        kayip_s = _now - takip_s["kayip_t"]
    takip_info = {
        "id": takip_s.get("id"), "aktif": bool(takip_s.get("aktif")),
        "kayip_s": kayip_s, "yeniden": int(takip_s.get("yeniden", 0)),
        "pos_count": vis_pos, "n_lock": Cfg.VIS_N_LOCK,
    }
    gorev_info = {
        "faz": gorev_s.get("faz", "HAZIR"), "vurus": bool(gorev_s.get("vurus")),
        "basari": bool(gorev_s.get("basari")), "en_yakin_m": gorev_s.get("en_yakin_m"),
        "mesafe_kaynak": gorev_s.get("mesafe_kaynak"), "vurus_t": gorev_s.get("vurus_t"),
        "t0": gorev_s.get("t0"), "esik_m": VURUS_ESIK_M,
    }
    with olay_lock:
        olay_listesi = list(_olaylar)[-60:]           # son 60 olay (durumsuz; F5/iki-sekme sorunsuz)

    # GORSEL GUDUM durumu + son normalize tespit (durum GORSEL_GUDUM -> GPS yonelimi kesik)
    if vis_tespit is not None:                        # paylasilan dict'i bozmadan kopyala + ID iliştir
        vis_tespit = dict(vis_tespit)
        vis_tespit["id"] = takip_s.get("id")
    gorsel = {
        "durum": j_durum,                          # ARAMA | GORSEL_GUDUM
        "mod": vis_mode,                           # OTO | GPS | GORSEL (manuel switch)
        "gps_kesildi": (j_durum == "GORSEL_GUDUM"),
        "pos_count": vis_pos, "lost_count": vis_lost, "n_lock": Cfg.VIS_N_LOCK,
        "dedektor_hazir": bool(dedektor is not None and getattr(dedektor, "hazir", False)),
        "kare_kaynak": _fpv_kaynak.get("ad"),      # dedektorun gordugu kaynak (windows-capture / mss)
        "conf_esik": float(Cfg.VIS_CONF_MIN),      # gudum/kilit esigi (alti = zayif, UI turuncu cizer)
        "kopru": bool(getattr(beyin, "vis_kopru", False)),  # olu-hesap koprusu aktif mi (FPV rozeti)
        "perf": dict(_perf),                       # dedektor performansi (det_ms/p95, poz_ms, fps, gpu)
        "tespit": vis_tespit,                      # None | {ex,ey,cx,cy,w,h,conf,cls,sinif,id} (normalize)
        "kilit": b_kilit,                          # {anlik,sure,gerek,pencere,ok,esik_pct,boyut_pct}
        # PERVANE MASKESI (yanlis-poz engelleme): UI kirmizi tarama ile cizer (kullanici dogrular)
        "prop_maske": [list(r) for r in (getattr(Cfg, "PROP_MASKE", None) or [])],
    }
    # POZ KESTIRIMI (kamera): gozlemci akisi; yaw_gercek kiyas icin eklenir
    if vis_poz is not None:
        vis_poz = dict(vis_poz)                    # paylasilan dict'i bozmadan kopyala
        try:
            trot = drone.get_target_rotation()     # (roll, pitch, yaw) — deger bozulmaz
            vis_poz["yaw_gercek"] = float(trot[2]) % 360.0
        except Exception:
            pass
    gorsel["poz"] = vis_poz                        # None | {kp,ok,mesafe_m,yaw_deg,...}
    gorsel["poz_hazir"] = bool(poz_dedektor is not None
                               and getattr(poz_dedektor, "hazir", False))

    return {
        "connected": connected,
        "drone": {
            "x": dx, "y": dy, "z": dz,
            "altitude_m": drone_alt_m,
            "speed_ms": drone_spd_ms,
            "speed_kmh": drone_spd_ms * MS_TO_KMH,
            "roll": drot[0], "pitch": drot[1], "yaw": drot[2],
            "cmd_throttle": _cmd_thr, "cmd_pitch": _cmd_pit,
        },
        "target": {
            "x": tx, "y": ty, "z": tz,
            "speed_ms": target_spd_ms,
            "speed_kmh": target_spd_ms * MS_TO_KMH,
        },
        "distance_m": distance_m,               # HAM GPS-avci mesafe (ekrandaki ana deger)
        "gercek_mesafe_m": gercek_mesafe_m,     # GERCEK GPS-avci mesafe (debug; bozulmamis)
        "debug": debug_info,
        "j": j_info,
        "gorev_aktif": gorev_aktif,
        "manuel_aktif": manuel_aktif,
        "kaynak": j_kaynak,
        "kiyas": kiyas,
        "gorsel": gorsel,
        "olaylar": olay_listesi,                # [{id,t,sv,m}] son 60 (video: olay gunlugu)
        "gnss": gnss_info,                      # bozuk GNSS girdisi + kesinti (ister 3)
        "gudum": gudum_info,                    # uygulanan komutlar + karar (ister 8)
        "takip": takip_info,                    # ID + aktif/pasif + kayip/yeniden (ister 5/6/7)
        "gorev": gorev_info,                    # faz + vurus/basari (ister 9/10)
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
        elif self.path == "/api/gorsel":
            # HIZLI GORSEL KANAL (~15 Hz): yalniz son tespit + poz (dusuk kutu gecikmesi).
            # yas_s: tespitin bu yanit anindaki yasi (istemci lead-cizim yapar).
            with beyin_lock:
                det = dict(_son_tespit_ui) if _son_tespit_ui is not None else None
                poz = dict(_son_poz_ui) if _son_poz_ui is not None else None
            if det is not None and "t_det" in det:
                det["yas_s"] = round(max(0.0, time.perf_counter() - det.pop("t_det")), 3)
            if det is not None and det.get("id") is None:
                det["id"] = det.get("track_id")       # hizli kanal ID etiketi (ByteTrack)
            if poz is not None and "t_poz" in poz:
                # iskelet yas telafisi: istemci kp'leri bbox hiziyla yas kadar ileri kaydirir
                poz["yas_s"] = round(max(0.0, time.perf_counter() - poz.pop("t_poz")), 3)
            self._send(200, json.dumps({"tespit": det, "poz": poz}).encode("utf-8"),
                       "application/json")
        elif self.path == "/api/tune":
            # Mevcut tune parametre degerlerini dondur (slider'lari baslatmak icin).
            vals = {k: getattr(Cfg, k) for k in TUNE_ALLOW}
            self._send(200, json.dumps(vals).encode("utf-8"), "application/json")
        elif self.path.startswith("/api/frame"):
            try:
                jpeg = fpv_jpeg()                 # ham oyun karesi (pencere-icerigi / mss)
                if jpeg is None:
                    self._send(503, "kare yok (oyun penceresi bekleniyor)".encode("utf-8"),
                               "text/plain; charset=utf-8")
                else:
                    self._send(200, jpeg, "image/jpeg")
            except Exception as e:
                self._send(500, ("goruntu hatasi: %s" % e).encode("utf-8"),
                           "text/plain; charset=utf-8")
        else:
            self._send(404, b"yok", "text/plain; charset=utf-8")

    def do_POST(self):
        global gorev_aktif, manuel_aktif, manuel_son_giris, _perf_log_f
        if self.path == "/api/command":
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length).decode("utf-8") if length else "{}"
            try:
                data = json.loads(raw)
            except Exception:
                data = {}
            cmd = data.get("cmd", "")
            msg = "Bilinmeyen komut"
            if cmd in ("start", "start_v2", "start_filtre", "start_gercek"):
                # start* -> uretim GNSS filtresi; start_gercek -> truth (test)
                kaynak = "gercek" if cmd == "start_gercek" else "filtre"
                with beyin_lock:
                    beyin.set_kaynak(kaynak)  # guduum kaynagi
                    beyin.log_dondur()        # her "Gorev Baslat" = yeni ucus logu/klasoru
                    _gorev_sifirla("YAKLASMA")   # izleyici latch'lerini sifirla
                # yeni gorev -> yeni perf logu (kapat, sonraki tik acar)
                if _perf_log_f is not None:
                    try: _perf_log_f.close()
                    except Exception: pass
                    _perf_log_f = None
                gorev_aktif = True
                manuel_aktif = False          # gorev ve manuel ayni anda olmaz
                _ad = {"filtre": "GNSS Filtre", "gercek": "GERCEK GPS"}[kaynak]
                msg = "GOREV BASLATILDI - kaynak: %s%s" % (
                    _ad, " (filtre yok, gercek konuma gidiyor)" if kaynak == "gercek" else "")
                olay_ekle("iyi", "GOREV BASLADI — kaynak: %s" % _ad)
            elif cmd == "stop":
                gorev_aktif = False
                manuel_aktif = False
                # Guvenlik: drone'u durdur (motorlari kes)
                try:
                    drone.set_control_surfaces(0.0, 0.0, 0.0, 0.0, False)
                except Exception:
                    pass
                msg = "GOREV DURDURULDU - drone pasif (motorlar kapali)"
                olay_ekle("uyari", "GOREV DURDURULDU")   # basari latch'i korunur
            elif cmd == "manuel_on":
                gorev_aktif = False           # gorev ve manuel ayni anda olmaz
                # Tek kilit altinda durumu kur + arm/hover yolla
                with beyin_lock:
                    manuel_kontrol["throttle"] = 0.0
                    manuel_kontrol["pitch"] = 0.0
                    manuel_kontrol["roll"] = 0.0
                    manuel_kontrol["yaw"] = 0.0
                    manuel_son_giris = time.time()
                    manuel_aktif = True
                    # Arm + hover (ilk klavye girisine kadar sabit)
                    try:
                        drone.set_control_surfaces(0.0, 0.0, 0.0, 0.0, True)
                    except Exception:
                        pass
                msg = "MANUEL MOD ACIK - klavye: W/A/S/D, Q/E (don), R/F (yuksel/alcal)"
                olay_ekle("bilgi", "MANUEL MOD ACIK")
            elif cmd == "manuel_off":
                # Motoru kesmez: drone havada sabit (hover); durdurmak icin 'Gorev Durdur'.
                with beyin_lock:
                    manuel_aktif = False
                    try:
                        drone.set_control_surfaces(0.0, 0.0, 0.0, 0.0, True)
                    except Exception:
                        pass
                msg = "MANUEL MOD KAPALI - drone havada sabit (hover)"
                olay_ekle("bilgi", "MANUEL MOD KAPALI")
            elif cmd == "vismode":
                # GUDUM PIPELINE SWITCH (test): OTO | GPS | GORSEL
                m = str(data.get("mode", "OTO")).upper()
                with beyin_lock:
                    ok = beyin.set_vis_mode(m)
                _aciklama = {"OTO": "otomatik (kilit/geri-donus)",
                             "GPS": "ZORLA GPS (gorsel kapali)",
                             "GORSEL": "ZORLA GORSEL (GPS kapali)"}.get(m, "")
                msg = ("GUDUM MODU: %s - %s" % (m, _aciklama)) if ok else "GECERSIZ mod: %s" % m
                if ok:
                    olay_ekle("bilgi", "Guduum modu -> %s" % m)
            payload = json.dumps({"ok": True, "msg": msg,
                                  "gorev_aktif": gorev_aktif,
                                  "manuel_aktif": manuel_aktif})
            self._send(200, payload.encode("utf-8"), "application/json")
        elif self.path == "/api/manuel":
            # Yuksek frekansli manuel kontrol akisi (klavye -> eksen komutu)
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
        elif self.path == "/api/tune":
            # CANLI TUNE: {param, value} -> Cfg.<param> = float(value) (allowlist'te ise).
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length).decode("utf-8") if length else "{}"
            try:
                data = json.loads(raw)
            except Exception:
                data = {}
            p = data.get("param", "")
            ok = False
            val = None
            if p in TUNE_ALLOW:
                try:
                    val = float(data.get("value"))
                    setattr(Cfg, p, val)      # atomik (GIL) -> kilit gerekmez
                    ok = True
                except Exception:
                    ok = False
            self._send(200, json.dumps({"ok": ok, "param": p, "value": val}).encode("utf-8"),
                       "application/json")
        elif self.path == "/api/tune_rapor":
            # "DEGERLERI YAZDIR": canli tune degerleri + ucusun gorsel-faz metrikleri
            # -> veri/tune_rapor_*.xlsx. Metrik kaynagi: aktif ucus logu (yoksa en yeni).
            try:
                from web.tune_rapor import (rapor_uret, en_yeni_log,
                                            ucus_klasoru, dosyayi_klasore_al)
                tune_vals = {k: getattr(Cfg, k) for k in TUNE_ALLOW}
                sabit_vals = {k: getattr(Cfg, k) for k in TUNE_SABIT_RAPOR if hasattr(Cfg, k)}
                with beyin_lock:
                    lf = getattr(beyin, "_log_f", None)
                    log_path = lf.name if lf is not None else None
                    if lf is not None:
                        try:
                            lf.flush()        # son tikler de rapora girsin
                        except Exception:
                            pass
                if log_path is None:
                    log_path = en_yeni_log(VERI_DIR)
                # UCUS KLASORU: bu ucusun tum verileri veri/tune_parametreler/ucus_N altinda
                klasor = ucus_klasoru(os.path.join(VERI_DIR, "tune_parametreler"),
                                      log_path)
                dosyayi_klasore_al(log_path, klasor)
                dosyayi_klasore_al(_TUNE_LOG_PATH, klasor)
                yol, ozet = rapor_uret(tune_vals, sabit_vals, log_path, klasor,
                                       kilit_gerek_s=float(getattr(Cfg, "VIS_WIN_NEED_S", 5.0)),
                                       tune_log_path=_TUNE_LOG_PATH)
                self._send(200, json.dumps({"ok": True, "dosya": yol,
                                            "klasor": klasor,
                                            "log": os.path.basename(log_path) if log_path else None,
                                            "ozet": ozet}).encode("utf-8"), "application/json")
            except Exception as e:
                # openpyxl yok / log okunamadi vb. -> arayuze sebebi soyle, cokme yok
                self._send(200, json.dumps({"ok": False, "hata": str(e)}).encode("utf-8"),
                           "application/json")
        else:
            self._send(404, b"yok", "text/plain; charset=utf-8")


# ----------------------------------------------------------
#  Ana program
# ----------------------------------------------------------
def main():
    # Sessiz olum teshisi: native kutuphane cokerse konsolda sebebi gorunsun.
    import faulthandler, traceback
    faulthandler.enable()

    # Arka plan thread'leri: baglanti, kontrol beyni, gorsel tespit, tune logu
    threading.Thread(target=connection_manager, daemon=True).start()
    threading.Thread(target=kontrol_dongusu, daemon=True).start()
    threading.Thread(target=dedektor_dongusu, daemon=True).start()
    threading.Thread(target=tune_log_dongusu, daemon=True).start()

    try:
        server = ThreadingHTTPServer(("127.0.0.1", WEB_PORT), Handler)
    except OSError as e:
        print("[HATA] %d portu acilamadi (baska bir arayuz ornegi calisiyor olabilir): %s"
              % (WEB_PORT, e))
        return
    print("=" * 52)
    print("  AVCI DRONE - YER KONTROL ISTASYONU calisiyor")
    print("  Tarayicida ac:  http://127.0.0.1:%d" % WEB_PORT)
    print("  Kapatmak icin:  Ctrl + C")
    if DEBUG_PENCERE:
        print("  DEBUG PENCERE: ACIK (dedektor gozu; gorev aktifken gorunur)")
    print("=" * 52)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nKapatiliyor... (Ctrl+C)")
    except Exception:
        print("\n[HATA] Sunucu beklenmedik istisnayla dustu:")
        traceback.print_exc()
    finally:
        drone.disconnect()


if __name__ == "__main__":
    main()

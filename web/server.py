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
from guidance.ana_kontrol import AvciKontrol, Cfg
from fusion.inovasyonlu_j_v2 import GNSSDuzeltici as JFiltre  # Inovasyonlu J: TEK uretim filtresi (sapma olcumu de bununla)
import numpy as np

# Ekran yakalama icin
import mss
from PIL import Image
try:
    import pygetwindow as gw
except Exception:
    gw = None

# cv2 OPSIYONEL (pencere-yakalama karesini olcekle/JPEG'e cevir; ultralytics ile
# birlikte gelir). Yoksa FPV mss+PIL yoluna duser, sistem cokmez.
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
CAM_MAX_WIDTH = 960   # FPV JPEG akisini bu genislige olcekle (bant genisligi; dedektor DOGAL alir)
CAM_JPEG_QUALITY = 60
UI_CONF_MIN = 0.25    # dedektor predict esigi: zayif tespit arayuzde TURUNCU gorunur;
                      # gudum/kilit yalnizca conf>=Cfg.VIS_CONF_MIN gorur (dedektor_dongusu kapisi)
POZ_HER_N = 3         # poz inference'i her N dedektor turunda bir (gozlemci; GPU dedektore kalsin)
DEDEKTOR_HEDEF_HZ = 15.0   # dedektor dongusu UST SINIRI (Hz); 0 = sinirsiz (eski serbest kosu).
                      # 8 Tem teshisi: serbest kosu GPU'yu doyurup sim'le kapismayi buyutuyordu
                      # (bench sim-only 40.6 ms; +dedektor/bench yigilinca 57-86 ms). Canli olcum
                      # zaten ~11-16 Hz'ti -> tavan gudum kadansini DUSURMEZ (kilit 5 ardisik
                      # tespit = 0.33 s @15 Hz, VIS_STALE_S=0.5 icinde); bosta kalan GPU sim'e
                      # doner -> hem oyun FPS'i hem inference suresi iyilesir (TESHIS_CANLI_INFERENCE.md).


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
    Bulamazsa None (o zaman tum ekran yakalanir). Pencere secimi
    detection.pencere_yakala.pencere_bul ile yapilir (SUREC-ADI oncelikli;
    tarayici sekmesi basliginda 'Drones of War' gecmesi yaniltamaz)."""
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
    """mss FALLBACK: oyun penceresi bolgesini (yoksa tum ekrani) yakalayip JPEG doner.
    windows-capture kuruluysa buraya dusulmez (fpv_jpeg pencere-icerigini kullanir)."""
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


# ----------------------------------------------------------
#  PENCERE-ICERIGI YAKALAMA (kayra'nin katmani — occlusion-proof FPV)
#  Oyun penceresinin ICERIGINI yakalar: pencere tarayicinin ARKASINDA olsa bile
#  dogru kare gelir; arayuz goruntusu PENCERE SECMEDEN otomatik akar.
#  windows-capture yoksa hazir=False -> mss ekran-bolgesine duser (cokme yok).
#  connection_manager oyun penceresi acilinca yakalamayi otomatik baslatir.
# ----------------------------------------------------------
# ACIK (2026-07-06, Win11): mss ekran-bolgesi yakalama, oyun penceresi Chrome'un
# ARKASINDA kalinca dedektore masaustu/tarayici pikselini besliyordu -> canli
# gorevde dedektor KOR kaldi (87.6 sn'de 1 tespit; ayni goruntude offline %62
# kilit-esigi-ustu). windows-capture PENCERE ICERIGINI yakalar (occlusion-proof).
# Eski Win10 LTSC 19044 makinede 'capture border' API'si olmadigi icin kapatilmisti;
# sorun cikarsa False yap -> mss fallback aynen calisir (o zaman oyun ONDE tutulmali).
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
    bgr = np.ascontiguousarray(bgr)                        # cv2/ultralytics contiguous ister
    h, w = bgr.shape[:2]
    return bgr, w, h


# FPV kaynagi DEGISTIGINDE bir kez konsola yaz (spam yok; tani icin).
_fpv_kaynak = {"ad": None}
def _fpv_log(ad, ekstra=""):
    if _fpv_kaynak["ad"] != ad:
        _fpv_kaynak["ad"] = ad
        print("[FPV] goruntu kaynagi -> %s%s" % (ad, ekstra))


def _mss_grab_bgr():
    """mss ile oyun BOLGESINI (pencere_bul bulursa), yoksa TUM EKRANI BGR ndarray yakala.
    (kaynak_adi, bgr) doner. Tum-ekran modunda tarayici FPV'yi kaplarsa AYNA olusabilir
    -> oyunu KENARLIKSIZ PENCERE yapmak veya windows-capture bunu cozer."""
    sct = _get_sct()
    region = _find_game_region()
    if region:
        left, top, width, height = region
        bbox = {"left": left, "top": top, "width": width, "height": height}
        kaynak = "mss (oyun penceresi bolgesi)"
    else:
        bbox = sct.monitors[1]                             # birincil monitor (tum ekran)
        kaynak = "mss (TUM EKRAN - oyun penceresi bulunamadi; ayna olursa oyunu KENARLIKSIZ PENCERE yap)"
    raw = sct.grab(bbox)
    frame = np.frombuffer(raw.bgra, dtype=np.uint8).reshape(raw.height, raw.width, 4)
    return kaynak, frame[:, :, :3].copy()                  # BGRA -> BGR (alpha at)


def grab_frame_bgr_t():
    """(BGR kare, W, H, t_kare) doner — YOLO dedektorunun kare kaynagi. DOGAL COZUNURLUK
    (kucultme YOK): YOLO zaten imgsz=1280'e kendi letterbox'lar; kareyi once 960'a
    indirip modele geri buyuttermek kucuk/uzak hedefin detayini olduruyordu
    (canli 20-40 m tespit orani offline'in cok altindaydi, 6 Tem log analizi).
    960 kucultme yalnizca FPV JPEG akisinda (fpv_jpeg) yapilir.
    t_kare: karenin YAKALANDIGI perf_counter ani (windows-capture: WGC thread'inin
    kareyi teslim ettigi an; mss: grab su anda yapildigi icin simdi). Kare yasi
    (yakalama -> sonuc yayini) teshisi bununla olculur; kare yoksa None.
    HER ZAMAN kare uretmeye calisir (fallback zinciri):
      1) windows-capture canli karesi (occlusion-proof; oyun arkada olsa bile dogru)
      2) mss oyun-penceresi bolgesi (oyun goruunur/onde ise)
      3) mss tum ekran (son care; ayna riski)
    Yalnizca mss de basarisizsa (None, 0, 0, None)."""
    pym = pencere_yakala_motoru
    if pym is not None and pym.hazir and pym.calisiyor():
        bgr, t_kare = pym.get_latest_bgr_t()
        if bgr is not None:
            _fpv_log("windows-capture (pencere icerigi)")
            bgr = np.ascontiguousarray(bgr)            # cv2/ultralytics contiguous ister
            return bgr, bgr.shape[1], bgr.shape[0], t_kare
    # Fallback: mss (windows-capture yok / henuz kare uretmedi / pencere bulunamadi)
    try:
        kaynak, bgr = _mss_grab_bgr()
        _fpv_log(kaynak)
        bgr = np.ascontiguousarray(bgr)
        return bgr, bgr.shape[1], bgr.shape[0], time.perf_counter()
    except Exception as e:
        _fpv_log("KARE YOK", " (%s)" % e)
        return None, 0, 0, None


def grab_frame_bgr():
    """Eski imza (FPV/fpv_jpeg kullanir): (BGR kare, W, H). Zaman damgasiz sarmalayici."""
    bgr, w, h, _t = grab_frame_bgr_t()
    return bgr, w, h


def fpv_jpeg():
    """/api/frame'in dondurdugu HAM oyun karesi (overlay YOK — bbox/rozet istemci
    canvas'inda cizilir). grab_frame_bgr fallback zincirini kullanir -> gorunur bir
    oyun/ekran varsa HER ZAMAN kare doner. Hicbir kaynak yoksa None (-> 503).
    Akis bant genisligi icin kare BURADA 960'a kucultulur (dedektor dogal alir)."""
    bgr, _w, _h = grab_frame_bgr()
    if bgr is None:
        return None
    bgr, _w, _h = _olcekle_bgr(bgr)
    if cv2 is not None:
        ok, enc = cv2.imencode(".jpg", bgr, [int(cv2.IMWRITE_JPEG_QUALITY), CAM_JPEG_QUALITY])
        if ok:
            return enc.tobytes()
    img = Image.fromarray(bgr[:, :, ::-1].copy())          # BGR->RGB (cv2 yoksa PIL ile)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=CAM_JPEG_QUALITY)
    return buf.getvalue()


# ----------------------------------------------------------
#  Baglanti yoneticisi
#  Oyun kapaliyken veya baglanti kopunca surekli yeniden dener.
# ----------------------------------------------------------
def connection_manager():
    _conn_prev = None
    while True:
        c = drone.is_connected()
        if c and _conn_prev != True:            # ilk basarili baglanma / yeniden baglanma
            olay_ekle("iyi", "Oyuna baglanildi")
        elif (not c) and _conn_prev == True:    # True -> False kenari (kopma)
            olay_ekle("uyari", "Oyun baglantisi koptu")
        _conn_prev = c
        if not c:
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
#  CANLI TUNE: arayuzdeki slider'lar Cfg'yi calisirken degistirir.
#  Kontrol dongusu Cfg.X'i HER tik okudugundan degisiklik ANINDA etki eder
#  (server yeniden baslatmaya gerek YOK). Guvenlik icin sadece bu allowlist.
# ----------------------------------------------------------
TUNE_ALLOW = {
    # (GPS terminal vurus/strike parametreleri 2026-07-06 temizliginde kaldirildi —
    #  vurus gorsel PNG fazinin isi; PNG tunable'lari asagida)
    # komut yumusakligi
    "MAX_DELTA",
    # yaw / burun
    "YAW_MAX", "KP_YAW",
    # yatay yaklasma
    "KP_H", "KD_H",
    # yaklasma hiz profili (kontrollu yaklasma; speed_cap her tik Cfg okur -> canli)
    "V_CAP_FAR", "V_CAP_NEAR", "BRAKE_DIST",
    # dikey (irtifa) PID
    "KP_Z", "KI_Z", "KD_Z", "THR_UP", "THR_DN",
    # GORSEL GUDUM (PNG): yaw kanali + kilit guveni + PN cekirdek parametreleri
    # (IBVS-only tunable'lar 2026-07-06 temizliginde IBVS ile birlikte kaldirildi)
    "VIS_SIGN_YAW", "VIS_K_YAW", "VIS_EMA", "VIS_CONF_MIN",
    "VIS_KP_CLOSE",  # kapanma hizi talebi (v_close_des = KP*R) — 1 numarali tune dugmesi
    "VIS_PN_N",      # navigasyon sabiti (3..5)
    "VIS_PN_TILT",   # PN ivme -> pitch/roll yetki carpani
    "VIS_TAU_Z",     # dikey kanal ataklik zaman sabiti
    "VIS_EY_REF",   # arayuz turuncu REF cizgisi (elev=0 gostergesi; sim'de kalibre)
    "VIS_TILT_DEG", # kamera tilt (png_gorsel LOS geometrisine katar)
}

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

# --- GPS SAPMA LOGU (bozuk + gercek konum; sapma analizi icin) ----------------
# (Fatih'in gps-log-server branch'inden main yapisina PORT edildi. Fark: cikti
# HERE/gps_analiz yerine VERI_DIR altina yazilir — proje kulturu: tum calisma
# ciktilari veri/ altinda ve zaten gitignore'lu; arac/ analizcileri de oradan okur.)
# Her YENI ham pakette bozuk (get_target_location) + gercek (debug truth) konum,
# zaman damgasi + aktif corruption ile biriktirilir; ~5 sn'de bir ATOMIK yazilir
# (kopmada veri durur). gps_bozuk_gercek.json ile ayni sema. Gudume DOKUNMAZ.
_GPS_LOG = os.path.join(VERI_DIR, "gps_log_canli.json")
_gps_log_kayitlar = []
_gps_log_t0 = None
_gps_log_son_yaz = 0.0


# ============================================================
#  GOREV OLAY GUNLUGU + GOREV IZLEYICI  (video isterleri 3/4/6/7/8/9/10)
#  Bu blok GUDUME DOKUNMAZ: her sey beyin'in VAR OLAN alanlarindan
#  kenar-tespitiyle (onceki tik <-> bu tik) turetilir. ana_kontrol.py ve
#  gorsel_tespit.py DEGISMEZ. Kural 8 uyumu: sadece "durum degisti mi?".
# ============================================================
GNSS_KESINTI_S    = 1.0    # sn; hedef GPS paketi bu suredir yenilenmediyse KESINTI
                           # (nominal 5 Hz -> 0.2 s; sartname kesintisi ~2 s -> 5x marj)
VURUS_ESIK_M      = 3.0    # m; angajmanda mesafe bu esigin altina inerse VURUS (sim'de kalibre)
BASARI_GECIKME_S  = 1.5    # sn; VURUS latch'inden sonra BASARI ilani
TAKIP_TAM_KAYIP_S = Cfg.VIS_STALE_S + Cfg.VIS_LOST_TO_GPS_S   # 1.5 s; takip-ID kapanma esigi
                           # (gudumun GPS'e donus penceresiyle AYNI -> tutarli anlatim)

olay_lock = threading.Lock()          # YAPRAK kilit: tutulurken asla beyin_lock/SDK cagrisi YOK
_olaylar  = deque(maxlen=400)         # {"id","t","sv","m"}
_olay_id  = 0


def olay_ekle(sv, mesaj):
    """Gorev olayini gunluge ekle. sv: bilgi|iyi|uyari|kritik. Thread-safe (yaprak kilit).
    Kilit sirasi tek yonlu (beyin_lock -> olay_lock) oldugundan deadlock imkansiz."""
    global _olay_id
    with olay_lock:
        _olay_id += 1
        _olaylar.append({"id": _olay_id, "t": time.time(), "sv": sv, "m": mesaj})
    print("[OLAY] %s" % mesaj)         # konsol kaydi da videoyla tutarli kalsin


# --- Izleyici durumu: YALNIZ kontrol thread'i yazar (tek-yazar); build_telemetry beyin_lock ile okur ---
_takip = {"id": None, "sonraki": 1, "yeniden": 0, "aktif": False, "kayip_t": None}
_gorev = {"faz": "HAZIR", "t0": None, "vurus": False, "basari": False,
          "en_yakin_m": None, "vurus_t": None, "mesafe_kaynak": None}
_izci = {"durum_prev": None, "handoff_prev": False, "kilit_ilan": False,
         "angajman_ilan": False, "angajman_min": None, "iska_ilan": False,
         "kesinti": False, "son_paket_t": None, "png_ilan": False}


def _gorev_sifirla(faz):
    """Yeni gorev baslarken izleyici latch'lerini sifirla (basari banner'i dahil)."""
    _takip.update(id=None, sonraki=1, yeniden=0, aktif=False, kayip_t=None)
    _gorev.update(faz=faz, t0=time.time(), vurus=False, basari=False,
                  en_yakin_m=None, vurus_t=None, mesafe_kaynak=None)
    _izci.update(durum_prev=None, handoff_prev=False, kilit_ilan=False,
                 angajman_ilan=False, angajman_min=None, iska_ilan=False, png_ilan=False)


def _mesafe_olc():
    """VURUS/BASARI icin DURUST mesafe (m): truth varsa gercek 3B, yoksa J-temiz kestirim.
    HAM ASLA kullanilmaz (buyuk ham hata sahte vurus tetikler). -> (mesafe_m, kaynak) | (None, None)."""
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
    """kontrol_dongusu icinde, beyin_lock ALTINDA, her tik (~50 Hz). GUDUME DOKUNMAZ:
    beyin'in alanlarini okuyup olay/durum turetir. Kesinti gorev pasifken de izlenir."""
    now = time.time()

    # 1) GNSS KESINTI: paket yasi (_izci["son_paket_t"] _kiyas_guncelle'de her yeni pakette yazilir)
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

    # 2) TAKIP-ID makinesi (girdi: beyin.son_tespit_t tazeligi — gudumdeki tanimla ayni)
    stt = beyin.son_tespit_t
    taze = (stt is not None) and ((time.perf_counter() - stt) <= Cfg.VIS_STALE_S)
    if taze:
        if _takip["id"] is None:                       # ACILIS
            _takip["id"] = _takip["sonraki"]; _takip["sonraki"] += 1
            _takip["kayip_t"] = None
            try:
                conf = float(beyin.son_tespit.get("conf", 0.0))
            except Exception:
                conf = 0.0
            if _takip["id"] == 1:
                olay_ekle("iyi", "ILK TESPIT — ID:1 (talon, conf=%.2f)" % conf)
            else:
                _takip["yeniden"] += 1
                olay_ekle("iyi", "YENIDEN TESPIT — yeni ID:%d (conf=%.2f)" % (_takip["id"], conf))
        elif not _takip["aktif"]:                      # blip koprulendi
            olay_ekle("iyi", "TAKIP SURUYOR — ID:%d korundu" % _takip["id"])
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

    # 4) GOREV FAZI + VURUS/BASARI (mesafe 50 Hz olculur -> vurus ani atlanmaz)
    mesafe, kaynak = _mesafe_olc()
    if mesafe is not None:
        if _gorev["en_yakin_m"] is None or mesafe < _gorev["en_yakin_m"]:
            _gorev["en_yakin_m"] = mesafe

    # ANGAJMAN: gorsel faz aktif + takip canli (GPS-strike test kipi 2026-07-06'da kaldirildi)
    angajman = (durum == "GORSEL_GUDUM" and _takip["aktif"])

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
            olay_ekle("kritik", "ANGAJMAN — gorsel yaklasma basladi")
        # PN GUDUM AKTIF olayi (kenar-tespitli, tek sefer): gorsel yasa PNG ise carpisma-rotasi
        if not _izci["png_ilan"] and getattr(Cfg, "VIS_LAW", "IBVS") == "PNG":
            _izci["png_ilan"] = True
            _pt = getattr(beyin, "png_tlm", {}) or {}
            _r = _pt.get("R_m"); _vc = _pt.get("Vc_ms")
            olay_ekle("bilgi", "PN GUDUM AKTIF — carpisma rotasi (R=%s Vc=%s)" % (
                ("%.1fm" % _r) if _r is not None else "?",
                ("%.1fm/s" % _vc) if _vc is not None else "?"))
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
        _gorev["faz"] = "KILIT" if durum == "KILIT" else "YAKLASMA"


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
    """Her YENI ham pakette Inovasyonlu J'yi besle, gercege hatasini olc."""
    global _kiyas_idx, _kiyas_son_ham, _gps_log_t0, _gps_log_son_yaz
    ham = drone.get_target_location()
    if ham == _kiyas_son_ham:
        return
    _kiyas_son_ham = ham
    _izci["son_paket_t"] = time.time()    # YENI paket geldi -> kesinti izleyici icin yas sifirlanir
                                          # (truth erken donusunden ONCE: gercek yarismada truth yokken de calisir)
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
    j_e = None

    # Inovasyonlu J (uretim): anlik cikti -> su anki gercekle karsilastir
    j_out = _kiyas_j.guncelle(hx, hy, hz)
    if j_out is not None:
        j_e = float(np.linalg.norm(np.array(j_out, float) - gercek))
        _kiyas_j_hata.append(j_e)

    # CSV log (metre): bos sutun = o pakette cikti yok (None/isinma)
    if _kiyas_log_f is not None:
        he = "%.2f" % (ham_e / 100.0)
        js = ("%.2f" % (j_e / 100.0)) if j_e is not None else ""
        try:
            _kiyas_log_f.write("%d,%s,%s\n" % (idx, he, js))
            _kiyas_log_f.flush()
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


def kontrol_dongusu():
    while True:
        if drone.is_connected():
            try:
                with beyin_lock:
                    if manuel_aktif:
                        beyin._hedef_temizle()    # J telemetrisi pasif aksin (guduuma dokunmaz)
                        _manuel_uygula()          # klavye komutunu uygula (kontrol)
                    elif gorev_aktif:
                        beyin.adim()              # tam kontrol (drone hedefe gider)
                    else:
                        beyin._hedef_temizle()    # sadece J'yi guncelle (olcum)
                        if beyin.debug_olc:
                            beyin._debug_olc()    # ham vs J hatasini olc
                    # Kiyas HER ZAMAN calisir (drone ucsa da uctmasa da donmaz)
                    _kiyas_guncelle()             # Inovasyonlu J sapma olcumu (ham vs J)
                    try:
                        _gorev_izle()             # olay/durum izleyici (GUDUME DOKUNMAZ)
                    except Exception as e:
                        if not _izci.get("_hata_bildirildi"):
                            _izci["_hata_bildirildi"] = True
                            print("[IZLEYICI HATA] %r" % e)
            except Exception:
                pass
        time.sleep(0.02)   # 50 Hz


# ----------------------------------------------------------
#  GORSEL TESPIT (YOLO best.pt) — AYRI thread.
#  Agir inference beyin_lock DISINDA kosar; sonuc beyin_lock ICINDE beyne yazilir
#  (kontrol dongusu 50Hz akici kalir). LAZY yukleme: ilk gorev tikinde model
#  yuklenir (boot yavaslamaz). ultralytics/torch YOKSA hazir=False -> sistem GPS
#  ile devam eder (gorsel faz sessizce devreye girmez, cokme YOK).
# ----------------------------------------------------------
dedektor = None
_son_tespit_ui = None      # UI/telemetri icin son NORMALIZE tespit (beyin_lock ile korunur)

# --- POZ KESTIRIMI (talon_pose.pt + PnP) — PARALEL GOZLEMCI --------------------
# best.pt akisina ILAVE kosar: ayni karede 6 keypoint bulur, PnP ile KAMERADAN
# mesafe/yonelim cikarir. GUDUME GIRMEZ (beyin girdisi best.pt bbox'i olarak
# kalir) -> mevcut sistem bozulmaz; sadece overlay/telemetri beslenir. Model
# dosyasi yoksa veya yuklenemezse sessizce kapali (hazir=False deseni).
# Kalite notu (pose/degerlendir_foto.py, egitim karelerinde iyimser): <10 m'de
# mesafe medyan ~%8, yaw medyan ~6 der; 15 m+ guvenilmez -> terminal faz araci.
POSE_MODEL_PATH = os.path.join(PROJ_ROOT, "models", "talon_pose.pt")
poz_dedektor = None        # PozDedektor | None (lazy; ilk gorev tikinde denenir)
poz_cozucu = None          # pose.poz_cozucu.PozCozucu (PnP + EMA)
_poz_sira = None           # model kpt sirasi -> talon_keypoints.json REF sirasi
_son_poz_ui = None         # UI icin son NORMALIZE poz (beyin_lock ile korunur)


# ----------------------------------------------------------
#  CANLI INFERENCE TESHISI (2026-07-08 — olcum katmani, davranis DEGISTIRMEZ)
#  dedektor_dongusu'nun her turunu asamalara kronometreler:
#    kare_yas  : karenin yakalanma ani -> inference baslangici (capture tazeligi)
#    capture   : grab_frame_bgr_t suresi (windows-capture'da ~0; mss'te gercek grab)
#    infer     : best.pt predict suresi (letterbox dahil)
#    poz       : talon_pose.pt + PnP suresi (yalniz kostugu turlarda)
#    yaz       : normalize + beyin_lock bekleme + sonuc yazimi
#    uctan_uca : yakalama ani -> sonucun beyne/UI'ya yazildigi an ("frame age")
#  Cikti: veri/teshis_zaman_<ts>.csv (kare basina satir) + her ~10 sn konsol ozeti
#  + GET /api/teshis (son ozet JSON). Kuyruk YOK (latest-frame tasarimi) ama
#  uctan_uca ZAMANLA BUYUYORSA backlog/contention var demektir (kesin bulgu).
#  A/B kare testi: POST /api/teshis {"dump_kare":100} -> modele giren array'in
#  BIREBIR aynisi PNG olarak veri/teshis_kareler/<ts>/ altina yazilir (Asama 3).
# ----------------------------------------------------------
TESHIS_AKTIF = True
TESHIS_OZET_S = 10.0        # konsol ozet periyodu (sn)
_teshis_lock = threading.Lock()
_teshis_dump = {"kalan": 0, "toplam": 0, "klasor": None}
_teshis_ozet = {}           # son pencere ozeti (GET /api/teshis dondurur)
_teshis_birikim = []        # ozet penceresindeki satirlar (yalniz dedektor thread'i yazar)
_teshis_son_ozet_t = None
_teshis_son_t4 = None       # onceki turun bitis ani (FPS icin)
_teshis_csv_f = None
_teshis_csv_yol = None


def _teshis_csv():
    """Teshis CSV'sini lazy ac (ilk olculen karede; bos dosya birakmaz)."""
    global _teshis_csv_f, _teshis_csv_yol
    if _teshis_csv_f is None:
        _teshis_csv_yol = os.path.join(
            VERI_DIR, "teshis_zaman_%s.csv" % time.strftime("%Y%m%d_%H%M%S"))
        _teshis_csv_f = open(_teshis_csv_yol, "w", encoding="utf-8")
        _teshis_csv_f.write("t,kaynak,kare_yas_ms,capture_ms,infer_ms,poz_ms,"
                            "yaz_ms,dongu_ms,uctan_uca_ms,fps,det,conf\n")
        print("[TESHIS] zamanlama logu -> %s" % _teshis_csv_yol)
    return _teshis_csv_f


def _teshis_kaydet(t0, t_kare, t1, t2, t3, t4, det, poz_kostu):
    """Bir dedektor turunun olcumunu CSV'ye yaz + ~10 sn'de bir ozet bas.
    Yalniz dedektor thread'i cagirir (kilit gerekmez); toplam maliyet ~0.1 ms."""
    global _teshis_son_ozet_t, _teshis_son_t4
    if not TESHIS_AKTIF:
        return
    kaynak_ad = _fpv_kaynak["ad"] or "?"
    kaynak = "wc" if kaynak_ad.startswith("windows") else ("mss" if "mss" in kaynak_ad else "?")
    fps = None
    if _teshis_son_t4 is not None and t4 > _teshis_son_t4:
        fps = 1.0 / (t4 - _teshis_son_t4)
    _teshis_son_t4 = t4
    satir = {
        "kare_yas_ms": (t1 - t_kare) * 1000.0 if t_kare is not None else None,
        "capture_ms": (t1 - t0) * 1000.0,
        "infer_ms": (t2 - t1) * 1000.0,
        "poz_ms": (t3 - t2) * 1000.0 if poz_kostu else None,
        "yaz_ms": (t4 - t3) * 1000.0,
        "dongu_ms": (t4 - t0) * 1000.0,
        "uctan_uca_ms": (t4 - t_kare) * 1000.0 if t_kare is not None else None,
        "fps": fps, "kaynak": kaynak,
        "det": 1 if det is not None else 0,
        "conf": float(det.get("conf", 0.0)) if det is not None else None,
    }
    try:
        f = _teshis_csv()
        f.write("%.3f,%s,%s,%.1f,%.1f,%s,%.2f,%.1f,%s,%s,%d,%s\n" % (
            time.time(), kaynak,
            ("%.1f" % satir["kare_yas_ms"]) if satir["kare_yas_ms"] is not None else "",
            satir["capture_ms"], satir["infer_ms"],
            ("%.1f" % satir["poz_ms"]) if satir["poz_ms"] is not None else "",
            satir["yaz_ms"], satir["dongu_ms"],
            ("%.1f" % satir["uctan_uca_ms"]) if satir["uctan_uca_ms"] is not None else "",
            ("%.1f" % fps) if fps is not None else "",
            satir["det"],
            ("%.3f" % satir["conf"]) if satir["conf"] is not None else ""))
        f.flush()
    except Exception:
        pass
    _teshis_birikim.append(satir)
    simdi = time.perf_counter()
    if _teshis_son_ozet_t is None:
        _teshis_son_ozet_t = simdi
    if simdi - _teshis_son_ozet_t >= TESHIS_OZET_S and _teshis_birikim:
        _teshis_son_ozet_t = simdi
        _teshis_ozetle()


def _teshis_ozetle():
    """Biriken pencereyi ozetle: konsola bas + _teshis_ozet'i guncelle (API okur)."""
    global _teshis_birikim
    rows = _teshis_birikim
    _teshis_birikim = []

    def _ist(ad):
        v = [r[ad] for r in rows if r.get(ad) is not None]
        if not v:
            return None
        a = np.array(v, float)
        return {"ort": float(a.mean()), "p50": float(np.percentile(a, 50)),
                "p95": float(np.percentile(a, 95)), "n": int(a.size)}
    ozet = {"n_kare": len(rows), "pencere_s": TESHIS_OZET_S,
            "kaynak": rows[-1]["kaynak"], "t": time.time()}
    for ad in ("kare_yas_ms", "capture_ms", "infer_ms", "poz_ms",
               "yaz_ms", "dongu_ms", "uctan_uca_ms", "fps"):
        ozet[ad] = _ist(ad)
    det_n = sum(r["det"] for r in rows)
    ozet["det_orani"] = det_n / float(len(rows))
    confs = [r["conf"] for r in rows if r["conf"] is not None]
    ozet["conf_ort"] = (sum(confs) / len(confs)) if confs else None
    with _teshis_lock:
        _teshis_ozet.clear()
        _teshis_ozet.update(ozet)

    def _f(d, k="p50"):
        return ("%.0f" % d[k]) if d else "-"
    print("[TESHIS] %d kare | kaynak=%s | FPS ort %s | kare_yas p50/p95 %s/%s ms | "
          "infer p50/p95 %s/%s ms | poz p50 %s ms (n=%s) | yaz p50 %s ms | "
          "UCTAN-UCA p50/p95 %s/%s ms | det %%%d%s" % (
              ozet["n_kare"], ozet["kaynak"],
              ("%.1f" % ozet["fps"]["ort"]) if ozet["fps"] else "-",
              _f(ozet["kare_yas_ms"]), _f(ozet["kare_yas_ms"], "p95"),
              _f(ozet["infer_ms"]), _f(ozet["infer_ms"], "p95"),
              _f(ozet["poz_ms"]), ozet["poz_ms"]["n"] if ozet["poz_ms"] else 0,
              _f(ozet["yaz_ms"]),
              _f(ozet["uctan_uca_ms"]), _f(ozet["uctan_uca_ms"], "p95"),
              round(ozet["det_orani"] * 100),
              (" (conf ort %.2f)" % ozet["conf_ort"]) if ozet["conf_ort"] else ""))


def _teshis_kare_dump(bgr):
    """A/B testi (Asama 3): modele giren BGR array'in birebir aynisini PNG yaz.
    Sonuc yazildiktan SONRA cagrilir -> PNG yazimi zamanlama olcumune karismaz
    (dump sirasinda FPS dusebilir, normal). cv2 yoksa PIL ile yazar."""
    if bgr is None or _teshis_dump["kalan"] <= 0:
        return
    with _teshis_lock:
        if _teshis_dump["kalan"] <= 0:
            return
        klasor = _teshis_dump["klasor"]
        idx = _teshis_dump["toplam"] - _teshis_dump["kalan"]
        _teshis_dump["kalan"] -= 1
        kalan = _teshis_dump["kalan"]
    try:
        if idx == 0:                       # ilk karede oturum metasi (A/B raporu icin)
            with open(os.path.join(klasor, "meta.json"), "w", encoding="utf-8") as mf:
                json.dump({"W": int(bgr.shape[1]), "H": int(bgr.shape[0]),
                           "kaynak": _fpv_kaynak["ad"], "t": time.time(),
                           "not": "modele giren array birebir (BGR->PNG)"}, mf, indent=2)
        yol = os.path.join(klasor, "kare_%04d.png" % idx)
        if cv2 is not None:
            cv2.imwrite(yol, bgr)
        else:
            Image.fromarray(bgr[:, :, ::-1].copy()).save(yol)
        if kalan == 0:
            print("[TESHIS] kare dump TAMAM (%d kare) -> %s" % (_teshis_dump["toplam"], klasor))
    except Exception as e:
        print("[TESHIS] kare dump hatasi: %r" % e)


def _normalize_tespit(det):
    """Dedektor px ciktisini overlay/telemetri icin normalize et (cozunurluk-bagimsiz)."""
    if det is None:
        return None
    W = float(det.get("W", 0) or 0); H = float(det.get("H", 0) or 0)
    if W <= 1 or H <= 1:
        return None
    cls = int(det.get("cls", -1))                  # dedektor sinif indeksi (gorsel_tespit uretir)
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
        "cls": cls, "sinif": sinif,                # hedef ID etiketi icin (overlay)
    }


def _normalize_poz(pdet, poz, yaw_pitch):
    """Poz dedektor + PnP ciktisini UI/telemetri icin normalize et.
    kp listesi REF SIRAYA cevrilir (0 burun, 1 sol_kanat, 2 sag_kanat,
    3 sol_kuyruk, 4 sag_kuyruk, 5 kuyruk_arka) — overlay renk/iskeleti sabit."""
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
         "ok": poz is not None}                      # ok=False: nokta var, PnP oturmadi
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


def dedektor_dongusu():
    global dedektor, _son_tespit_ui, poz_dedektor, poz_cozucu, _poz_sira, _son_poz_ui
    from detection.gorsel_tespit import HedefDedektor   # import-guard modul icinde (ultralytics opsiyonel)
    from detection.poz_tespit import PozDedektor        # ayni desen (hazir=False zarif bozulma)
    poz_sayac = 0                                        # POZ_HER_N seyreklestirme sayaci
    onceki_ui = None                                     # (cx, cy, t) — UI bbox hiz kestirimi icin
    while True:
        # Sadece OTONOM gorev sirasinda tespit yap (manuel/pasifken bosuna donme).
        if not (drone.is_connected() and gorev_aktif and not manuel_aktif):
            time.sleep(0.05)
            continue
        if dedektor is None:                          # LAZY: ilk gorev tikinde yukle
            # imgsz=1280: yeni model (v3 pose, 5 Tem) 1280'de egitildi — 640'ta uzak/kucuk
            # hedef kacar. Sadece BBOX ciktisi kullaniliyor (pose keypoint'leri simdilik yok).
            # TENSORRT (9 Tem teshis kapanisi): models/best.engine VARSA once o denenir —
            # ayni model GPU'ya derlenmis hali (sim'le GPU kapismasinda inference
            # suresini kisaltir; kanit: TESHIS_CANLI_INFERENCE.md bench tablosu).
            # Engine MAKINEYE OZELDIR (gitignore'lu; araclar/teshis_trt_export.py uretir).
            # Yuklenemezse best.pt'ye ZARIF dusulur — davranis eskisiyle ayni kalir.
            _engine_yol = os.path.splitext(Cfg.VIS_MODEL_PATH)[0] + ".engine"
            if os.path.exists(_engine_yol):
                dedektor = HedefDedektor(_engine_yol, conf=Cfg.VIS_CONF_MIN, imgsz=1280)
                if dedektor.hazir:
                    print("[GORSEL] TensorRT engine yuklendi: %s" % os.path.basename(_engine_yol))
                else:
                    print("[GORSEL] engine yuklenemedi (%s) -> best.pt'ye dusuluyor."
                          % dedektor.hata)
                    dedektor = None
            if dedektor is None:
                dedektor = HedefDedektor(Cfg.VIS_MODEL_PATH, conf=Cfg.VIS_CONF_MIN, imgsz=1280)
            if dedektor.hazir:
                print("[GORSEL] dedektor hazir (device=%s). Siniflar: %s"
                      % (dedektor.device, dedektor.names))
            else:
                print("[GORSEL] Dedektor YUKLENEMEDI (%s) -> sistem GPS ile devam eder."
                      % dedektor.hata)
            # POZ modeli (ILAVE gozlemci) — best.pt ile AYNI anda, bir kez denenir.
            if os.path.exists(POSE_MODEL_PATH):
                # conf=0.35: 0.20'de eski model bos gokyuzune "talon" diyordu (canli
                # test, 4 Tem) -> overlay'e cop iskelet ciziliyordu; canlida yanlis-
                # alarm maliyeti yuksek. imgsz=1280: v3 model (5 Tem) 1280'de egitildi.
                poz_dedektor = PozDedektor(POSE_MODEL_PATH, conf=0.35, imgsz=1280)
                if poz_dedektor.hazir:
                    try:
                        from pose.poz_cozucu import PozCozucu, EGITIM_SIRASI
                        poz_cozucu = PozCozucu(conf_esik=0.5, ema_alpha=0.4)
                        _poz_sira = list(EGITIM_SIRASI)
                        print("[POZ] talon_pose.pt yuklendi (device=%s) -> PnP poz "
                              "kestirimi AKTIF (gozlemci; gudume girmez)." % poz_dedektor.device)
                    except Exception as e:
                        poz_dedektor.hazir = False
                        print("[POZ] PnP cozucu yuklenemedi (%r) -> poz kapali." % e)
                else:
                    print("[POZ] pose modeli YUKLENEMEDI (%s) -> poz kapali "
                          "(best.pt/GPS normal calisir)." % poz_dedektor.hata)
            else:
                print("[POZ] %s yok -> poz kestirimi kapali." % POSE_MODEL_PATH)
        if not dedektor.hazir:
            time.sleep(1.0)                           # kurulum yok -> CPU yakma
            continue
        t0 = time.perf_counter()                      # TESHIS: tur baslangici
        t_kare = None
        try:
            # Predict esigi UI icin dusuk (UI_CONF_MIN): zayif tespitler arayuzde
            # turuncu cizilir. GUDUM yine yalnizca conf>=VIS_CONF_MIN gorur
            # (asagida det_beyin kapisi) -> beyin/kilit davranisi DEGISMEZ.
            # Slider VIS_CONF_MIN'i daha da dusururse predict onu izler (canli-tune).
            dedektor.conf = min(UI_CONF_MIN, float(Cfg.VIS_CONF_MIN))
            bgr, _fw, _fh, t_kare = grab_frame_bgr_t()   # AGIR is: pencere karesi al (kilit DISINDA)
            t1 = time.perf_counter()                  # TESHIS: capture bitti
            # ultralytics ndarray'i BGR varsayar -> grab_frame_bgr ciktisi DOGRU renk.
            det = dedektor.tespit_et(bgr) if bgr is not None else None
        except Exception:
            bgr, det = None, None
            t1 = time.perf_counter()
        t2 = time.perf_counter()                      # TESHIS: best.pt inference bitti
        # GUDUM KAPISI: zayif (yalnizca-UI) tespit beyne GITMEZ -> kilit sayaci,
        # takip rozeti, gorsel guduum eski predict-esigi davranisiyla BIREBIR ayni.
        det_beyin = (det if det is not None
                     and float(det.get("conf", 0.0)) >= float(Cfg.VIS_CONF_MIN) else None)
        # POZ kestirimi: AYNI kare uzerinde ILAVE inference + PnP (kilit DISINDA).
        # SEYREK kosar: best.pt hedef gormusken her POZ_HER_N turda bir. Gozlemci-only
        # bir ozellik icin GPU'nun yarisini yemesin: her turda kosunca dedektor canli
        # ~5-7 Hz'e dusuyordu -> takip delikleri (6 Tem log analizi).
        # Her turlu hata poz'u None yapar; best.pt/gudum akisini ETKILEYEMEZ.
        poz_ui, poz_kostu = None, False
        poz_sayac += 1
        if (poz_dedektor is not None and poz_dedektor.hazir
                and poz_cozucu is not None and bgr is not None
                and det is not None and poz_sayac % POZ_HER_N == 0):
            poz_kostu = True
            try:
                pdet = poz_dedektor.tespit_et(bgr)
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
        t3 = time.perf_counter()                      # TESHIS: poz inference bitti
        # UI tespiti + NORMALIZE HIZ (vx,vy [1/s]): arayuz bbox'u tespit YASI kadar
        # ILERI cizer (inference + aktarim gecikmesi telafisi; /api/gorsel tasir).
        ui_det = _normalize_tespit(det)
        if ui_det is not None and det is not None:
            t_det = float(det.get("t", time.perf_counter()))
            ui_det["t_det"] = t_det
            if onceki_ui is not None and 0.0 < (t_det - onceki_ui[2]) < 0.5:
                dt_ui = t_det - onceki_ui[2]
                ui_det["vx"] = (ui_det["cx"] - onceki_ui[0]) / dt_ui
                ui_det["vy"] = (ui_det["cy"] - onceki_ui[1]) / dt_ui
            onceki_ui = (ui_det["cx"], ui_det["cy"], t_det)
        with beyin_lock:                              # sonucu ANLIK yaz (kilit ICINDE)
            beyin.set_gorsel_tespit(det_beyin)
            _son_tespit_ui = ui_det
            if poz_kostu or det is None:              # ara turlarda SON pozu tut (iskelet
                _son_poz_ui = poz_ui                  # yanip sonmesin); hedef yoksa temizle
        t4 = time.perf_counter()                      # TESHIS: sonuc yayinlandi
        if bgr is not None:
            _teshis_kaydet(t0, t_kare, t1, t2, t3, t4, det, poz_kostu)
            _teshis_kare_dump(bgr)                    # A/B dumpi EN SONDA (olcume karismaz)
        if bgr is None:
            time.sleep(0.05)                          # oyun karesi henuz yok -> CPU'yu bosalt
        elif DEDEKTOR_HEDEF_HZ > 0:
            # HIZ TAVANI (8 Tem teshis duzeltmesi): dongu hedeften hizliysa kalani uyu
            # -> GPU sim'e nefes alir. Contention'da dongu zaten yavas -> sleep 0'a
            # duser, davranis eskisiyle birebir (tavan yalniz BOL GPU'da devreye girer).
            kalan_s = (1.0 / DEDEKTOR_HEDEF_HZ) - (time.perf_counter() - t0)
            if kalan_s > 0:
                time.sleep(kalan_s)


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

    # Avci-hedef 3B mesafe — HAM GPS ile (bozuk). Ekranda gosterilen ana deger budur;
    # bozuk GPS spoof/sicramasinda ziplayabilir (bu normal, ham veri gostergesi).
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
        j_kaynak = beyin.kaynak           # aktif guduum kaynagi (Inovasyonlu J / gercek)
        j_temiz = None if beyin.son_temiz is None else (
            float(beyin.son_temiz[0]), float(beyin.son_temiz[1]), float(beyin.son_temiz[2]))
        ham_list = list(beyin.ham_hatalar)
        j_list = list(beyin.j_hatalar)
        vis_tespit = _son_tespit_ui       # normalize son tespit (dedektor thread yazar)
        vis_poz = _son_poz_ui             # normalize son POZ kestirimi (ayni thread yazar)
        vis_pos = beyin._vis_pos_count
        vis_lost = beyin._vis_lost_count
        vis_mode = getattr(beyin, "vis_mode", "OTO")   # guduum pipeline switch
        png_tlm = dict(getattr(beyin, "png_tlm", {}) or {})   # gorsel PNG ic durumu (salt-okunur)
        # --- IZLEYICI/GUDUM alanlari (video isterleri) — hepsi ayni kilit altinda anlik kopya ---
        prev_cmd = dict(beyin.prev)                    # uygulanan 4 komut (tek dogruluk kaynagi)
        b_handoff = bool(beyin.handoff)
        b_none = int(getattr(beyin, "none_count", 0))
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

    # (GECICI TANI) kontrolcunun SON gonderdigi dikey/ileri komut -> tani_irtifa.py icin.
    # Drone davranisini DEGISTIRMEZ; sadece son komutu gosterir. Sorun cozulunce silinebilir.
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
        "none_count": b_none,
    }
    gudum_info = {
        "thr": prev_cmd.get("thr", 0.0), "pitch": prev_cmd.get("pitch", 0.0),
        "roll": prev_cmd.get("roll", 0.0), "yaw": prev_cmd.get("yaw", 0.0),
        "durum": j_durum, "mod": vis_mode, "kaynak": j_kaynak,
        "handoff": b_handoff, "d_h_m": d_h_m,
        "law": getattr(Cfg, "VIS_LAW", "IBVS"),     # aktif gorsel yasa (PNG | IBVS)
        "png": png_tlm,                             # {law,R_m,Vc_ms,omega_rads,commit,kaynak} | {}
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

    # GORSEL GUDUM durumu + son NORMALIZE tespit (overlay/rozet icin). durum
    # GORSEL_GUDUM ise GPS yonelimi MIMARI olarak kesilmistir -> index.html
    # "GPS GUDUMU: KAPALI" rozetini kirmizi yakar.
    if vis_tespit is not None:                        # paylasilan dict'i BOZMADAN kopyala + ID iliştir
        vis_tespit = dict(vis_tespit)
        vis_tespit["id"] = takip_s.get("id")
    gorsel = {
        "durum": j_durum,                          # ARAMA | GORSEL_GUDUM
        "mod": vis_mode,                           # OTO | GPS | GORSEL (manuel switch)
        "ey_ref": float(getattr(Cfg, "VIS_EY_REF", 0.0)),   # dikey referans (tilt telafisi; overlay cizer)
        "gps_kesildi": (j_durum == "GORSEL_GUDUM"),
        "pos_count": vis_pos, "lost_count": vis_lost, "n_lock": Cfg.VIS_N_LOCK,
        "dedektor_hazir": bool(dedektor is not None and getattr(dedektor, "hazir", False)),
        "conf_esik": float(Cfg.VIS_CONF_MIN),      # gudum/kilit esigi (alti = zayif, UI turuncu cizer)
        "tespit": vis_tespit,                      # None | {ex,ey,cx,cy,w,h,conf,cls,sinif,id} (normalize)
    }
    # POZ KESTIRIMI (kamera): gozlemci akisi — kp REF sirada normalize, mesafe/yaw
    # KAMERADAN. yaw_gercek kiyas icin telemetriden eklenir (sim/debug gostergesi).
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
            # HIZLI GORSEL KANAL (~15 Hz istemci): yalniz son tespit + poz. Telemetri
            # 200 ms dongusunu beklemeden taze bbox -> arayuzde kutu gecikmesi dusuk.
            # yas_s: tespitin bu yaniti urettigimiz andaki yasi (istemci lead-cizim yapar).
            with beyin_lock:
                det = dict(_son_tespit_ui) if _son_tespit_ui is not None else None
                poz = _son_poz_ui
            if det is not None and "t_det" in det:
                det["yas_s"] = round(max(0.0, time.perf_counter() - det.pop("t_det")), 3)
            self._send(200, json.dumps({"tespit": det, "poz": poz}).encode("utf-8"),
                       "application/json")
        elif self.path == "/api/tune":
            # Mevcut tune parametre degerlerini dondur (slider'lari baslatmak icin).
            vals = {k: getattr(Cfg, k) for k in TUNE_ALLOW}
            self._send(200, json.dumps(vals).encode("utf-8"), "application/json")
        elif self.path == "/api/teshis":
            # TESHIS OZETI: dedektor dongusunun son ~10 sn zamanlama istatistikleri
            # (konsol ozetinin JSON hali) + dump durumu + aktif CSV yolu.
            with _teshis_lock:
                ozet = dict(_teshis_ozet)
                ozet["dump"] = dict(_teshis_dump)
            ozet["csv"] = _teshis_csv_yol
            self._send(200, json.dumps(ozet).encode("utf-8"), "application/json")
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
        global gorev_aktif, manuel_aktif, manuel_son_giris
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
                    _gorev_sifirla("YAKLASMA")   # izleyici latch'lerini sifirla (basari banner dahil)
                gorev_aktif = True
                manuel_aktif = False          # gorev ve manuel ayni anda olmaz
                _ad = {"v2": "Inovasyonlu J", "gercek": "GERCEK GPS"}[kaynak]
                msg = "GOREV BASLATILDI - kaynak: %s%s" % (
                    _ad, " (filtre yok, gercek konuma gidiyor)" if kaynak == "gercek" else "")
                olay_ekle("iyi", "GOREV BASLADI — kaynak: %s" % _ad)
            elif cmd == "stop":
                gorev_aktif = False
                manuel_aktif = False
                # Guvenlik: drone'u durdur (motorlari kes -> arm=False)
                try:
                    drone.set_control_surfaces(0.0, 0.0, 0.0, 0.0, False)
                except Exception:
                    pass
                msg = "GOREV DURDURULDU - drone pasif (motorlar kapali)"
                olay_ekle("uyari", "GOREV DURDURULDU")   # basari latch'i KORUNUR (banner ekranda kalir)
            elif cmd == "manuel_on":
                gorev_aktif = False           # gorev ve manuel ayni anda olmaz
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
                olay_ekle("bilgi", "MANUEL MOD ACIK")
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
        elif self.path == "/api/teshis":
            # A/B KARE DUMPI (Asama 3): {"dump_kare": N} -> dedektore giden SIRADAKI
            # N kare, modele girmeden onceki haliyle PNG yazilir (gorev aktif olmali).
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length).decode("utf-8") if length else "{}"
            try:
                n = int(json.loads(raw).get("dump_kare", 0))
            except Exception:
                n = 0
            if n > 0:
                n = min(n, 1000)                      # disk emniyeti (1080p PNG ~2-3 MB/kare)
                klasor = os.path.join(VERI_DIR, "teshis_kareler",
                                      time.strftime("%Y%m%d_%H%M%S"))
                os.makedirs(klasor, exist_ok=True)
                with _teshis_lock:
                    _teshis_dump.update(kalan=n, toplam=n, klasor=klasor)
                print("[TESHIS] kare dump basladi: %d kare -> %s" % (n, klasor))
                self._send(200, json.dumps({"ok": True, "kare": n, "klasor": klasor})
                           .encode("utf-8"), "application/json")
            else:
                self._send(200, json.dumps({"ok": False, "msg": "dump_kare > 0 gonder"})
                           .encode("utf-8"), "application/json")
        else:
            self._send(404, b"yok", "text/plain; charset=utf-8")


# ----------------------------------------------------------
#  Ana program
# ----------------------------------------------------------
def main():
    # SESSIZ OLUM TESHISI: native bir kutuphane (torch/cv2/windows-capture...) coker
    # ya da beklenmedik bir istisna serve_forever'i dusururse konsolda SEBEBI gorunsun
    # ("Sunucu durdu" ama neden belli degil durumunu bitirir).
    import faulthandler, traceback
    faulthandler.enable()

    # Arka planda baglanti yoneticisini ve gorev kontrol beynini baslat
    threading.Thread(target=connection_manager, daemon=True).start()
    threading.Thread(target=kontrol_dongusu, daemon=True).start()
    # Gorsel tespit (YOLO) AYRI thread: gorev aktifken best.pt ile hedef bbox uretir.
    threading.Thread(target=dedektor_dongusu, daemon=True).start()

    # COKLU-ORNEK KORUMASI (8 Tem teshisi): http.server varsayilani allow_reuse_address=True,
    # Windows'ta SO_REUSEADDR "port zaten dinleniyorken bile" ikinci baglanmaya izin verir ->
    # bat'a ikinci tiklama HATASIZ ikinci bir "hayalet" arayuz acar, trafik ikiye bolunur
    # (8 Tem: 3 ornek ustuste birikti, dogrulama olcumunu bozdu). False ile ikinci ornek
    # asagidaki OSError'a duser ve zaten yazili [HATA] mesaji gorunur (kodun niyeti buydu).
    ThreadingHTTPServer.allow_reuse_address = False
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

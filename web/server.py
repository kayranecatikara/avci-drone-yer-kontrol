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

import ctypes
import io
import json
import os
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from sdk import drone_sdk as drone
from guidance.ana_kontrol import AvciKontrol, Cfg
import numpy as np

# >>> SERT AYRIM (CLAUDE.md): web/ UCUS PIPELINE'inin parcasidir; yalnizca
#     yarismada mevcut telemetriyle calisir. Filtre dogrulama/sapma olcumu
#     arac/ altindaki gelistirme scriptlerinin isidir (arayuzden kaldirildi). <<<

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
try:
    from config import WEB_HOST, WEB_PORT   # merkezi config (teslim kalemi)
except Exception:
    WEB_HOST, WEB_PORT = "127.0.0.1", 8000  # config yoksa guvenli varsayilan

HERE = os.path.dirname(os.path.abspath(__file__))           # .../web (server.py + index.html)
PROJ_ROOT = os.path.dirname(HERE)                           # depo koku
VERI_DIR = os.path.join(PROJ_ROOT, "veri")                  # calisma ciktilari (log/csv; gitignore'lu)
os.makedirs(VERI_DIR, exist_ok=True)

# Goruntude oyun penceresini tanimak icin baslik ipuclari
GAME_TITLE_HINTS = ["dronesofwar", "drones of war", "drone of war"]
CAM_MAX_WIDTH = 960   # Yakalanan kareyi bu genislige olcekle (akiciligi artirir)
CAM_JPEG_QUALITY = 60


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


# ----------------------------------------------------------
#  PENCERE-ICERIGI YAKALAMA (kayra'nin katmani — occlusion-proof FPV)
#  Oyun penceresinin ICERIGINI yakalar: pencere tarayicinin ARKASINDA olsa bile
#  dogru kare gelir; arayuz goruntusu PENCERE SECMEDEN otomatik akar.
#  windows-capture yoksa hazir=False -> mss ekran-bolgesine duser (cokme yok).
#  connection_manager oyun penceresi acilinca yakalamayi otomatik baslatir.
# ----------------------------------------------------------
# windows-capture bu makinede (Win10 LTSC 19044) KARARSIZ: 'capture border' API'si
# desteklenmiyor -> her baslatmada oturum hatasi + native kutuphane cokmesi riski
# (sunucunun sessizce olmesine yol acabiliyor). KAPALI tutuyoruz; dedektor kare
# kaynagi mss'tir (oyun penceresi gorunur olmali). Win11'de denemek icin True yap.
PENCERE_YAKALA_AKTIF = False
pencere_yakala_motoru = None
if PENCERE_YAKALA_AKTIF:
    try:
        from detection.pencere_yakala import PencereYakala
        pencere_yakala_motoru = PencereYakala(title_hints=GAME_TITLE_HINTS)
    except Exception as _py_e:
        print("[SERVER] pencere_yakala yuklenemedi (%s) -> mss fallback." % _py_e)
else:
    print("[SERVER] windows-capture KAPALI -> birincil kare kaynagi PrintWindow "
          "(occlusion-proof, saf Win32; tarayici onde iken bile oyunu yakalar). "
          "PrintWindow siyah donerse mss'e duser.")


# ----------------------------------------------------------
#  PrintWindow kare kaynagi (occlusion-proof, saf Win32 -> bu makinede KARARLI;
#  windows-capture GEREKMEZ). Tek monitorde arayuz oyunun onunde olsa bile dogru
#  oyun karesini verir (mss'in "oyun onde olmali" sartini kaldirir). K sanity
#  zinciriyle AYNI yakalama yolu -> kalibrasyon tutarli.
# ----------------------------------------------------------
_pw_hwnd_cache = {"hwnd": None}
def _printwindow_grab_bgr():
    """(kaynak_adi, BGR) | None. Oyun hwnd'sini coz (onbellekli; gecersizse yeniden
    bul) + PrintWindow ile pencere icerigini yakala. windows-capture'a bagimli degil."""
    try:
        from detection.pencere_yakala import pencere_icerik_bgr, pencere_bul
    except Exception:
        return None
    h = _pw_hwnd_cache["hwnd"]
    gecerli = False
    if h:
        try:
            gecerli = bool(ctypes.windll.user32.IsWindow(int(h)))
        except Exception:
            gecerli = False
    if not gecerli:
        _, h = pencere_bul(GAME_TITLE_HINTS)     # SUREC-ADI oncelikli (dogru pencere garantisi)
        _pw_hwnd_cache["hwnd"] = h
    if not h:
        return None
    bgr = pencere_icerik_bgr(h)
    if bgr is None:
        return None
    return "PrintWindow (pencere icerigi; occlusion-proof)", bgr


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


def grab_frame_bgr():
    """(BGR kare, W, H) doner — hem YOLO dedektoru hem FPV bunu kullanir.
    HER ZAMAN kare uretmeye calisir (fallback zinciri):
      1) windows-capture canli karesi (varsa; bu makinede KAPALI)
      2) PrintWindow pencere-icerigi (occlusion-proof, saf Win32; BIRINCIL yol —
         tarayici oyunun onunde olsa bile dogru oyun karesi)
      3) mss oyun-penceresi bolgesi (oyun goruunur/onde ise)
      4) mss tum ekran (son care; ayna riski)
    Yalnizca hepsi basarisizsa (None, 0, 0)."""
    pym = pencere_yakala_motoru
    if pym is not None and pym.hazir and pym.calisiyor():
        bgr = pym.get_latest_bgr()
        if bgr is not None:
            _fpv_log("windows-capture (pencere icerigi)")
            return _olcekle_bgr(bgr)
    # 2) PrintWindow (occlusion-proof; windows-capture kapali olsa bile calisir).
    #    Tek monitorde arayuz onde iken mss'in tarayiciyi/aynayi yakalamasini onler.
    try:
        pw = _printwindow_grab_bgr()
    except Exception:
        pw = None
    if pw is not None:
        _fpv_log(pw[0])
        return _olcekle_bgr(pw[1])
    # 3-4) Fallback: mss (PrintWindow siyah dondu / pencere bulunamadi)
    try:
        kaynak, bgr = _mss_grab_bgr()
        _fpv_log(kaynak)
        return _olcekle_bgr(bgr)
    except Exception as e:
        _fpv_log("KARE YOK", " (%s)" % e)
        return None, 0, 0


def _bgr_jpeg(bgr):
    """BGR kareyi JPEG'e cevirir (HAM oyun karesi; overlay YOK — bbox/rozet istemci
    canvas'inda cizilir). cv2 varsa hizli yol, yoksa PIL."""
    if cv2 is not None:
        ok, enc = cv2.imencode(".jpg", bgr, [int(cv2.IMWRITE_JPEG_QUALITY), CAM_JPEG_QUALITY])
        if ok:
            return enc.tobytes()
    img = Image.fromarray(bgr[:, :, ::-1].copy())          # BGR->RGB (cv2 yoksa PIL ile)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=CAM_JPEG_QUALITY)
    return buf.getvalue()


# ----------------------------------------------------------
#  KARE URETICI — FPV akiciliginin cozumu (TEK yakalayici thread)
#  ESKI: her /api/frame istegi + dedektor dongusu AYRI AYRI PrintWindow cagirirdi;
#  kare basina yakalama (20-60 ms) HTTP yaniti icinde beklenir, gorev sirasinda
#  iki thread ayni pencereyi yakalamak icin yarisirdi -> arayuz FPV'si takilirdi.
#  YENI: bu thread ~KARE_FPS temposunda yakalar ve SON kareyi yayinlar:
#    - /api/frame long-poll ile HAZIR JPEG'i aninda alir (yakalama istek yolunda degil),
#    - dedektor ayni BGR kareyi tuketir (cift yakalama yuku kalkti).
#  Tarayici kapali + gorev pasifken yakalama da durur (bosuna CPU yok).
# ----------------------------------------------------------
KARE_FPS = 25.0              # yakalama temposu (PrintWindow ~20-40 ms -> surdurulebilir)
_kare = {"bgr": None, "jpeg": None, "seq": 0, "ts": 0.0, "tp": 0.0}
_kare_cond = threading.Condition()
_fpv_talep_ts = 0.0          # son /api/frame ani (tarayici FPV izliyor mu?)


def _fpv_talep_var():
    return (time.time() - _fpv_talep_ts) < 3.0


def _kare_gerekli():
    """Yakalama kossun mu? Tarayici FPV istiyor VEYA otonom gorev algisi calisiyor."""
    return _fpv_talep_var() or (drone.is_connected() and gorev_aktif and not manuel_aktif)


def kare_uretici_dongusu():
    while True:
        if not _kare_gerekli():
            time.sleep(0.15)
            continue
        t0 = time.perf_counter()
        try:
            bgr, _w, _h = grab_frame_bgr()
        except Exception:
            bgr = None
        tp = time.perf_counter()               # yakalama ani (tespit yasi bundan olculur)
        # Tarayici izlemiyorsa (kareyi yalniz dedektor tuketiyor) JPEG encode'a girme.
        jpeg = _bgr_jpeg(bgr) if (bgr is not None and _fpv_talep_var()) else None
        with _kare_cond:
            _kare["bgr"] = bgr
            _kare["jpeg"] = jpeg
            _kare["seq"] += 1
            _kare["ts"] = time.time()
            _kare["tp"] = tp
            _kare_cond.notify_all()
        if bgr is None:
            time.sleep(0.25)                       # kaynak yok -> CPU'yu bosalt
            continue
        kalan = (1.0 / KARE_FPS) - (time.perf_counter() - t0)
        if kalan > 0:
            time.sleep(kalan)                      # sabit tempo (yakalama jitter'ini torpuler)


def kare_bekle_yeni(son_seq, timeout):
    """son_seq'ten YENI yayin gelene kadar bekler; (bgr, guncel_seq, tp) doner
    (tp = karenin yakalanma ani, perf_counter; tespit yasi bundan olculur).
    Timeout'ta (None, son_seq, None); yayin var ama kare alinamadiysa (None, yeni_seq, tp)."""
    bitis = time.monotonic() + timeout
    with _kare_cond:
        while _kare["seq"] == son_seq:
            kalan = bitis - time.monotonic()
            if kalan <= 0:
                return None, son_seq, None
            _kare_cond.wait(kalan)
        return _kare["bgr"], _kare["seq"], _kare["tp"]


# ----------------------------------------------------------
#  Baglanti yoneticisi
#  Oyun kapaliyken veya baglanti kopunca surekli yeniden dener.
# ----------------------------------------------------------
def connection_manager():
    deneme = 0
    onceki_bagli = None
    while True:
        bagli = drone.is_connected()
        if not bagli:
            # Yeniden baglanmadan once eski baglantiyi temizle (cift baglanmayi onler)
            try:
                drone.disconnect()
            except Exception:
                pass
            bagli = drone.connect()  # oyun kapaliysa sessizce False doner, sorun olmaz
        if bagli and onceki_bagli is not True:
            print("[BAGLANTI] Oyuna baglanildi.")
            olay_ekle("iyi", "Oyuna baglanildi")
            deneme = 0
        elif (not bagli) and onceki_bagli is True:     # True -> False kenari (kopma)
            olay_ekle("uyari", "Oyun baglantisi koptu")
        elif not bagli:
            deneme += 1
            if deneme == 1 or deneme % 15 == 0:      # ilk deneme + ~30 sn'de bir hatirlat
                print("[BAGLANTI] Oyuna baglanilamiyor (deneme %d) - oyun acik ve PLAY "
                      "modunda mi? (Oyun TEK TCP kabul eder; onceki istemci koptuysa "
                      "oyunu yeniden baslatmak gerekebilir.)" % deneme)
        onceki_bagli = bagli
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

# >>> DEV-ONLY >>>
# Gelistirme hedef-kaynagi modulu (web/dev_truth.py). Yoksa/yuklenemezse sunucu
# NORMAL baslar, arayuzde DEV butonu hic gorunmez. Paketlemede bu blok silinir.
dev_yardimci = None
try:
    from web.dev_truth import DevTruthKaynagi
    dev_yardimci = DevTruthKaynagi(drone)
    print("[SERVER] dev_truth yuklendi -> KAYNAK: FILTRE/GERCEK(DEV) butonu aktif.")
except Exception as _dev_e:
    print("[SERVER] dev_truth yuklenmedi (%s) -> DEV kaynak butonu kapali." % _dev_e)
# <<< DEV-ONLY <<<

# ----------------------------------------------------------
#  CANLI TUNE: arayuzdeki slider'lar Cfg'yi calisirken degistirir.
#  Kontrol dongusu Cfg.X'i HER tik okudugundan degisiklik ANINDA etki eder
#  (server yeniden baslatmaya gerek YOK). Guvenlik icin sadece bu allowlist.
# ----------------------------------------------------------
TUNE_ALLOW = {
    # terminal vurus / carpma
    "V_CLOSE", "V_CLOSE_MIN", "KP_CLOSE", "KV_STRIKE", "STRIKE_TILT",
    "STRIKE_RANGE", "COMMIT_RANGE",
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
    # GORSEL TAKIP (IBVS): isaret/kazanc/kapi + kilit guveni (SIM'de canli kalibrasyon)
    "VIS_SIGN_YAW", "VIS_SIGN_VZ", "VIS_SIGN_PITCH",
    "VIS_K_YAW", "VIS_K_VZ", "VIS_K_FWD", "VIS_FWD_MAX",
    "VIS_CENTER_GATE", "VIS_AREA_STOP", "VIS_EMA", "VIS_CONF_MIN",
    "VIS_EY_REF",   # kamera 25 derece tilt telafisi (dikey referans; sim'de kalibre)
    # DUZELTME-1 (YAKLASMA burun-hedefe) — C segmenti ONCE/SONRA icin canli toggle
    # (0.0=kapali eski omnidirek, 1.0=acik turn-then-advance) + kisma/EMA tau.
    "YAKLASMA_BURUN_HEDEFE", "YAKLASMA_ROLL_KIS", "YAKLASMA_DIKEY_KIS",
    "HEDEF_Z_EMA_TAU_SN",
    # MERGE 2026-07-06 (main/serhadcan standoff profili) — iki profil canli secilebilir:
    # GPS_TERMINAL_STRIKE 0.0=standoff (serhadcan) / 1.0=intercept+ram (bizim eski);
    # AUTO_VISUAL_HANDOFF ve HANDOFF_YAKINLIK_SART gorsel devir kapilari (0/1).
    "GPS_TERMINAL_STRIKE", "AUTO_VISUAL_HANDOFF", "HANDOFF_YAKINLIK_SART",
    "APPROACH_STANDOFF", "APPROACH_LEAD_S", "APPROACH_ALT_OFFSET",
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


# ============================================================
#  GOREV IZLEYICI + OLAY GUNLUGU (video isterleri 3-10)
#  MERGE 2026-07-06: main'in _gorev_izle deseninden alinip BIZIM 5-durum
#  FSM'e (ARAMA->YAKLASMA->GORSEL_TAKIP->KILIT_BILDIR->ANGAJMAN) uyarlandi.
#  TEMEL KURAL: tum sinyaller beyin'in VAR OLAN alanlarindan KENAR-TESPITIYLE
#  (onceki tik <-> bu tik) turetilir; gudume DOKUNMAZ (kural 8: izleyici
#  "durum degisti mi?" karsilastirmasindan ibaret, takimca aciklanabilir).
# ============================================================
GNSS_KESINTI_S    = 1.0    # sn; hedef GPS paketi bu suredir yenilenmediyse KESINTI
                           # (nominal 5 Hz -> 0.2 s; sartname kesintisi ~2 s -> 5x marj)
VURUS_ESIK_M      = 3.0    # m; ANGAJMAN'da mesafe altina inerse VURUS (sim'de kalibre)
BASARI_GECIKME_S  = 1.5    # sn; VURUS latch'inden sonra BASARI ilani
TAKIP_TAM_KAYIP_S = Cfg.VIS_STALE_S + Cfg.VIS_LOST_TO_GPS_S   # takip-ID kapanma esigi
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
_takip = {"id": None, "yeniden": 0, "aktif": False, "kayip_t": None}
_gorev = {"faz": "HAZIR", "t0": None, "vurus": False, "basari": False,
          "en_yakin_m": None, "vurus_t": None, "mesafe_kaynak": None}
_izci = {"durum_prev": None, "handoff_prev": False, "confirmed_ilan": False,
         "angajman_ilan": False, "angajman_min": None, "iska_ilan": False,
         "kesinti": False, "son_paket_t": None, "son_ham_prev": None}


def _gorev_sifirla(faz):
    """Yeni gorev baslarken izleyici latch'lerini sifirla (basari banner'i dahil)."""
    _takip.update(id=None, yeniden=0, aktif=False, kayip_t=None)
    _gorev.update(faz=faz, t0=time.time(), vurus=False, basari=False,
                  en_yakin_m=None, vurus_t=None, mesafe_kaynak=None)
    _izci.update(durum_prev=None, handoff_prev=False, confirmed_ilan=False,
                 angajman_ilan=False, angajman_min=None, iska_ilan=False)


def _mesafe_olc():
    """VURUS/BASARI icin DURUST mesafe (m): J-temiz kestirim (ucusta mevcut tek
    guvenilir kaynak). HAM ASLA kullanilmaz (buyuk ham hata sahte vurus tetikler).
    -> (mesafe_m, kaynak) | (None, None)."""
    m, kaynak = None, None
    if beyin.son_xy_anlik is not None and beyin.son_z_anlik is not None:
        dp = drone.get_drone_location()
        tx, ty, tz = float(beyin.son_xy_anlik[0]), float(beyin.son_xy_anlik[1]), float(beyin.son_z_anlik)
        d = ((dp[0] - tx) ** 2 + (dp[1] - ty) ** 2 + (dp[2] - tz) ** 2) ** 0.5
        m, kaynak = d * CM_TO_M, "temiz"
    # >>> DEV-ONLY >>>
    # DEV kosusunda latch'i gercek 3B mesafeyle olc (dev_truth modulu uzerinden;
    # paketlenmis kodda bu blok yok -> J-temiz kalir).
    if dev_yardimci is not None:
        try:
            g = dev_yardimci.mesafe_m()
            if g is not None:
                m, kaynak = g, "gercek"
        except Exception:
            pass
    # <<< DEV-ONLY <<<
    return m, kaynak


def _yatay_mesafe_cm():
    """Avci <-> hedef YATAY mesafe (cm): temiz kestirim, yoksa ham. Panel/angajman icin."""
    dp = drone.get_drone_location()
    if beyin.son_xy_anlik is not None:
        tx, ty = float(beyin.son_xy_anlik[0]), float(beyin.son_xy_anlik[1])
    elif beyin.son_ham is not None:
        tx, ty = float(beyin.son_ham[0]), float(beyin.son_ham[1])
    else:
        return None
    return ((dp[0] - tx) ** 2 + (dp[1] - ty) ** 2) ** 0.5


_GORSEL_AILE_UI = ("GORSEL_TAKIP", "KILIT_BILDIR", "ANGAJMAN")


def _gorev_izle():
    """kontrol_dongusu icinde, beyin_lock ALTINDA, her tik (~50 Hz). GUDUME DOKUNMAZ:
    beyin'in alanlarini okuyup olay/durum turetir. Kesinti gorev pasifken de izlenir."""
    now = time.time()

    # 1) GNSS KESINTI: paket yasini beyin.son_ham degisiminden izle (yeni paket ->
    #    son_ham degisir; _hedef_temizle zaten yalniz yeni pakette gunceller).
    sh = beyin.son_ham
    if sh is not None and sh != _izci["son_ham_prev"]:
        _izci["son_ham_prev"] = sh
        _izci["son_paket_t"] = now
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

    # 2) TAKIP olaylari (girdi: beyin.son_tespit_t tazeligi + ByteTrack ID'si)
    det = beyin.son_tespit
    stt = beyin.son_tespit_t
    taze = (stt is not None) and ((time.perf_counter() - stt) <= Cfg.VIS_STALE_S)
    tid = (det or {}).get("track_id")
    if taze:
        if _takip["id"] is None:                       # ACILIS
            _takip["id"] = tid if tid is not None else 1
            _takip["kayip_t"] = None
            try:
                conf = float((det or {}).get("conf", 0.0))
            except Exception:
                conf = 0.0
            if _takip["yeniden"] == 0:
                olay_ekle("iyi", "ILK TESPIT — ID:%s (conf=%.2f)" % (_takip["id"], conf))
            else:
                olay_ekle("iyi", "YENIDEN TESPIT — ID:%s (conf=%.2f)" % (_takip["id"], conf))
        elif tid is not None and tid != _takip["id"]:  # tracker yeni ID acti
            _takip["id"] = tid
            _takip["yeniden"] += 1
            olay_ekle("iyi", "YENIDEN TESPIT — yeni ID:%s" % tid)
        elif not _takip["aktif"]:                      # blip koprulendi
            olay_ekle("iyi", "TAKIP SURUYOR — ID:%s korundu" % _takip["id"])
            _takip["kayip_t"] = None
        _takip["aktif"] = True
    else:
        if _takip["id"] is not None:
            if _takip["aktif"]:
                _takip["aktif"] = False
                _takip["kayip_t"] = now
                olay_ekle("uyari", "TESPIT KAYBI — ID:%s (kor-devam)" % _takip["id"])
            elif _takip["kayip_t"] is not None and (now - _takip["kayip_t"]) >= TAKIP_TAM_KAYIP_S:
                olay_ekle("uyari", "TAKIP KAPANDI — ID:%s (%.1f s kayip)"
                          % (_takip["id"], now - _takip["kayip_t"]))
                _takip["id"] = None
                _takip["yeniden"] += 1                 # sonraki acilis "YENIDEN TESPIT" desin
                _takip["kayip_t"] = None

    # 3) FSM kenarlari (beyin.durum / beyin.handoff / tracker CONFIRMED)
    durum = beyin.durum
    dp_ = _izci["durum_prev"]
    if durum != dp_:
        if durum == "GORSEL_TAKIP" and dp_ not in _GORSEL_AILE_UI:
            olay_ekle("iyi", "GORSEL TAKIBE GECILDI — GPS yonelimi KAPALI (yonelim yalniz kamera)")
        elif durum == "KILIT_BILDIR":
            olay_ekle("iyi", "KILIT TAMAM — hakem paketi gonderildi (+400)")
        elif durum == "ANGAJMAN" and dp_ != "ANGAJMAN":
            pass                                       # angajman olayi asagida (latch ile)
        elif durum in ("ARAMA", "YAKLASMA") and dp_ in _GORSEL_AILE_UI:
            olay_ekle("uyari", "GPS'e DONULDU — yeniden yaklasma")
        _izci["durum_prev"] = durum
    if beyin.handoff and not _izci["handoff_prev"]:
        olay_ekle("bilgi", "Tespit menzilinde — YAKLASMA (gorus devralabilir)")
    _izci["handoff_prev"] = bool(beyin.handoff)
    # tracker CONFIRMED kenari (bizim kilit on-kosulu; _vis_pos_count yeni hatta kullanilmiyor)
    confirmed = bool(det and det.get("track_durumu") == "CONFIRMED" and taze)
    if confirmed and not _izci["confirmed_ilan"]:
        _izci["confirmed_ilan"] = True
        olay_ekle("iyi", "TRACKER CONFIRMED — gorsel kilit on-kosulu saglandi")
    elif not confirmed and not taze:
        _izci["confirmed_ilan"] = False

    # 4) GOREV FAZI + VURUS/BASARI (mesafe 50 Hz olculur -> vurus ani atlanmaz)
    mesafe, kaynak = _mesafe_olc()
    if mesafe is not None:
        if _gorev["en_yakin_m"] is None or mesafe < _gorev["en_yakin_m"]:
            _gorev["en_yakin_m"] = mesafe

    angajman = (durum == "ANGAJMAN" and _takip["aktif"])
    if Cfg.GPS_TERMINAL_STRIKE:                        # test kipi: GPS ram menzilinde de angajman
        dh = _yatay_mesafe_cm()
        if dh is not None and dh < Cfg.STRIKE_RANGE:
            angajman = True

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
            olay_ekle("kritik", "ANGAJMAN — terminal gorsel yaklasma basladi")
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
        _gorev["faz"] = durum          # ARAMA | YAKLASMA | GORSEL_TAKIP | KILIT_BILDIR


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
                        beyin._hedef_temizle()    # sadece J'yi guncelle (pasif izleme)
                    _gorev_izle()                 # olay/durum izleyici (GUDUME DOKUNMAZ)
            except Exception:
                pass
        time.sleep(0.02)   # 50 Hz


# ----------------------------------------------------------
#  GORSEL ALGI HATTI (tespit->takip->PnP) — AYRI thread.
#  Agir inference beyin_lock DISINDA kosar; sonuc beyin_lock ICINDE beyne yazilir
#  (kontrol dongusu 50Hz akici kalir). Model registry (model_yonetici) aktif
#  modeli yonetir (hot-swap); algi_hatti frame-senkron tespit->takip->PnP yapar.
#  ultralytics/torch YOKSA model hazir olmaz -> sistem GPS ile devam eder (cokme YOK).
# ----------------------------------------------------------
model_yon = None           # ModelYonetici (lazy)
algi = None                # AlgiHatti (lazy)
_son_tespit_ui = None      # UI/telemetri icin son NORMALIZE tespit (beyin_lock ile korunur)
_son_pnp_ui = None         # UI icin son PnP ozeti

# --- SAHTE TESPIT (mouse ile hedef isaretleme) — YZ modeli olgun DEGILKEN guduum testi ---
# MERGE 2026-07-06 (main'den): arayuzde FPV uzerinde mouse BASILI tutulunca normalize
# (cx,cy) buraya akar ve dedektor dongusunde asil algi ciktisinin YERINE gecer (ayni
# det sozlugu, ayni beyin.set_gorsel_tespit yolu) -> gorsel guduum "model bu noktayi
# verdi" senaryosuyla test edilir. Mesaj SAHTE_TAZE_S icinde yenilenmezse otomatik
# kapanir (failsafe: tarayici kapanirsa/donarsa drone eski noktaya kilitli KALMAZ).
# GELISTIRME KOLAYLIGIDIR; yarisma kosusunda kullanilmaz (video isteri: manuel
# isaretleme YOK) — teslim oncesi arayuz butonuyla birlikte devre disi birakilir.
SAHTE_TAZE_S = 0.6
_sahte = {"aktif": False, "cx": 0.5, "cy": 0.5, "t": 0.0}   # beyin_lock ile korunur


def _sahte_oku():
    """Taze sahte-tespit verisi varsa kopyasini dondur, yoksa None."""
    with beyin_lock:
        s = dict(_sahte)
    if s["aktif"] and (time.time() - s["t"]) <= SAHTE_TAZE_S:
        return s
    return None


def _normalize_tespit(det):
    """Algi hedef ciktisini overlay/telemetri icin normalize et (cozunurluk-bagimsiz).
    Track alanlari (id/durum/tespit_mi) korunur; keypoints normalize edilir."""
    if det is None:
        return None
    W = float(det.get("W", 0) or 0); H = float(det.get("H", 0) or 0)
    if W <= 1 or H <= 1:
        return None
    n = {
        "ex": (det["cx"] - W / 2.0) / (W / 2.0),   # + = hedef SAGDA
        "ey": (det["cy"] - H / 2.0) / (H / 2.0),   # + = hedef ALTTA
        "cx": det["cx"] / W, "cy": det["cy"] / H,  # normalize merkez [0..1]
        "w": det["w"] / W, "h": det["h"] / H,      # normalize bbox boyut [0..1]
        "conf": float(det.get("conf", 0.0)),
        "track_id": det.get("track_id"),
        "track_durumu": det.get("track_durumu"),
        "tespit_mi": det.get("tespit_mi"),
        "sahte": bool(det.get("sahte", False)),    # UI rozeti: tespit mouse'tan mi geldi?
        "sinif": ("manuel" if det.get("sahte") else det.get("sinif", "hedef")),
    }
    kp = det.get("keypoints")
    if kp:                                          # normalize keypoints (overlay ciz)
        n["keypoints"] = [[float(x) / W, float(y) / H, float(c)] for x, y, c in kp]
    return n


def _ui_hiz_damgala(ui_det, t_det, onceki):
    """UI tespitine yakalama-ani (t_det) + normalize hiz (vx,vy [1/s]) damgalar
    (merge 2026-07-07: main 152a7bc mekanizmasinin bizim hatta portu). Arayuz
    kutuyu tespit YASI kadar ILERI cizer (/api/gorsel tasir) -> yakalama +
    inference + aktarim gecikmesi telafi edilir. Hiz yalniz AYNI track_id'den
    ardisik iki olcumle hesaplanir (ID degisiminde sicrama-hizi uretilmez).
    -> yeni onceki-durum (cx, cy, t, track_id) | None."""
    if ui_det is None:
        return None
    t_det = float(t_det) if t_det else time.perf_counter()
    ui_det["t_det"] = t_det
    tid = ui_det.get("track_id")
    if onceki is not None and onceki[3] == tid and 0.0 < (t_det - onceki[2]) < 0.5:
        dt = t_det - onceki[2]
        ui_det["vx"] = (ui_det["cx"] - onceki[0]) / dt
        ui_det["vy"] = (ui_det["cy"] - onceki[1]) / dt
    return (ui_det["cx"], ui_det["cy"], t_det, tid)


def _pnp_ui_ozet(pnp):
    """PnP sonucundan arayuz ozeti (mesafe cm->m; None->None)."""
    if not pnp:
        return None
    o = {"gecerli": bool(pnp.get("gecerli")), "sema": pnp.get("sema"),
         "origin": pnp.get("origin"), "kullanilan_kp": pnp.get("kullanilan_kp")}
    if pnp.get("gecerli"):
        o["mesafe_m"] = float(pnp["mesafe"]) / 100.0
        o["reproj_err"] = float(pnp.get("reproj_err", 0.0))
        o["phi_T"] = float(pnp.get("phi_T", 0.0))
        o["psi_T"] = float(pnp.get("psi_T", 0.0))
    else:
        o["sebep"] = pnp.get("sebep")
    return o


def _algi_kur():
    """Model registry + algi hatti + PnP lazy kurulumu (ilk gorev tikinde)."""
    global model_yon, algi
    from detection.model_yonetici import ModelYonetici
    from detection.algi_hatti import AlgiHatti
    from detection.talon_pose_estimator import TalonPozKestirici
    model_yon = ModelYonetici(baslangic_conf=Cfg.VIS_CONF_MIN)
    algi = AlgiHatti(dedektor=model_yon)
    algi.pnp_baglan(TalonPozKestirici(sema=model_yon.aktif_sema()))
    # baslangic modeli: once config.VIS_MODEL_ADI, yoksa Cfg.VIS_MODEL_PATH adi; o da
    # yoksa ilk bulunan .pt (registry secer)
    try:
        from config import VIS_MODEL_ADI as tercih
    except Exception:
        tercih = os.path.splitext(os.path.basename(Cfg.VIS_MODEL_PATH))[0]
    adlar = [k["ad"] for k in model_yon.modelleri_listele()]
    baslangic = tercih if tercih in adlar else (adlar[0] if adlar else None)
    if baslangic:
        model_yon.model_yukle(baslangic, arka_plan=False)
        print("[GORSEL] Registry: %d model; aktif '%s' (task=%s)."
              % (len(adlar), model_yon.aktif_ad(), model_yon.durum().get("task")))
    else:
        print("[GORSEL] models/ altinda .pt YOK -> sistem GPS ile devam eder.")


def dedektor_dongusu():
    global _son_tespit_ui, _son_pnp_ui
    kare_seq = 0               # kare_uretici'den tuketilen son yayin sirasi
    onceki_ui = None           # (cx, cy, t, track_id) — UI bbox hizi (vx,vy) kestirimi
    while True:
        # Sadece OTONOM gorev sirasinda algi yap (manuel/pasifken bosuna donme).
        if not (drone.is_connected() and gorev_aktif and not manuel_aktif):
            time.sleep(0.05)
            continue
        # SAHTE TESPIT: mouse verisi tazeyken ASIL algi hattinin YERINE gecer (o
        # dongude inference HIC kosulmaz — GPU bosa yanmaz, ByteTrack sahteyle
        # kirlenmez). Sozluk eski det semasiyla birebir; track_durumu YOK ->
        # beyin._confirmed_track 5-kare fallback sayaciyla kilitlenir (ayni esik).
        sahte = _sahte_oku()
        if sahte is not None:
            with _kare_cond:
                _bgr = _kare["bgr"]
            if _bgr is not None:
                H_, W_ = _bgr.shape[:2]
            else:                                     # kare yok -> nominal cozunurluk
                W_, H_ = 1920.0, 1080.0               # (normalize edildigi icin sonuc ayni)
            det = {"cx": sahte["cx"] * W_, "cy": sahte["cy"] * H_,
                   "w": 0.06 * W_, "h": 0.05 * H_,    # nominal bbox (guduum ex/ey merkezi kullanir)
                   "conf": 1.0, "cls": -1, "sahte": True,
                   "W": W_, "H": H_, "t": time.perf_counter()}
            ui_det = _normalize_tespit(det)
            onceki_ui = _ui_hiz_damgala(ui_det, det["t"], onceki_ui)
            with beyin_lock:                          # enjeksiyon (kilit ICINDE)
                beyin.set_gorsel_tespit(det)
                beyin._algi_pnp = None                # bayat PnP OIPN'e sizmasin
                _son_tespit_ui = ui_det
                _son_pnp_ui = None
            time.sleep(0.03)                          # ~30 Hz enjeksiyon temposu
            continue
        if algi is None:                              # LAZY: ilk gorev tikinde kur
            try:
                _algi_kur()
            except Exception as e:
                print("[GORSEL] Algi hatti kurulamadi (%s) -> GPS ile devam." % e)
                time.sleep(1.0)
                continue
        if model_yon is None or not model_yon.hazir:
            time.sleep(1.0)                           # model yok -> CPU yakma
            continue
        try:
            model_yon.conf = float(Cfg.VIS_CONF_MIN)  # canli-tune predict esigi (yalniz gorsel/metrik)
            # Kareyi kare_uretici'den TUKET (kendi PrintWindow cagrisi YOK -> FPV ile
            # ayni kare; cift yakalama yarisi bitti). Yeni yayin yoksa kisa bekler.
            bgr, kare_seq, kare_tp = kare_bekle_yeni(kare_seq, timeout=0.3)
            att = drone.get_drone_rotation()          # gyro-CMC icin attitude (temiz/tam-hizli)
            # t=kare_tp: takip dt'si + PnP low-pass + UI tespit-yasi AYNI yakalama
            # anini kullanir (t=None olsaydi adim kendi saatini basardi).
            cikti = algi.adim(bgr, att, t=kare_tp) if bgr is not None else None
        except Exception:
            bgr, cikti, kare_tp = None, None, None
        # AlgiCiktisi.hedef eski det sozlesmesiyle uyumlu (cx,cy,w,h,conf,W,H) ->
        # beyin.set_gorsel_tespit geriye uyumlu (FSM tracker sorgusu FAZ 3'te).
        hedef = cikti.hedef if cikti else None
        ui_det = _normalize_tespit(hedef)
        onceki_ui = _ui_hiz_damgala(ui_det, kare_tp, onceki_ui)
        with beyin_lock:                              # sonucu ANLIK yaz (kilit ICINDE)
            beyin.set_algi(cikti)                     # AlgiCiktisi snapshot (hedef + PnP + turevler)
            _son_tespit_ui = ui_det
            _son_pnp_ui = (cikti.pnp if cikti else None)
        # Kare yoksa kare_bekle_yeni timeout'u zaten bekletti (spin yok); kare varsa
        # bir sonraki yayini bekleyerek inference dogal pace'lenir (ayni kare iki kez
        # islenmez). Ekstra sleep GEREKMEZ.


# (GOREV SONU / VURUS degerlendirmesi _gorev_izle icine tasindi — MERGE 2026-07-06:
#  eski ham-GPS'li latch yerine izleyicinin J-temiz[/DEV] mesafeli VURUS/BASARI
#  latch'i tek dogruluk kaynagi; arayuzdeki gorev_sonu anahtari oradan beslenir.)


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
    # bozuk GPS sicramasinda ziplayabilir (bu normal, ham veri gostergesi).
    distance_m = ((dx - tx) ** 2 + (dy - ty) ** 2 + (dz - tz) ** 2) ** 0.5

    # J (GNSS duzeltici) durumu (beyin_lock ile guvenli oku)
    with beyin_lock:
        j_durum = beyin.durum
        j_kaynak = beyin.kaynak           # aktif guduum kaynagi (Inovasyonlu J)
        j_temiz = None if beyin.son_temiz is None else (
            float(beyin.son_temiz[0]), float(beyin.son_temiz[1]), float(beyin.son_temiz[2]))
        vis_tespit = _son_tespit_ui       # normalize son tespit (dedektor thread yazar)
        vis_pos = beyin._vis_pos_count
        vis_lost = beyin._vis_lost_count
        vis_mode = getattr(beyin, "vis_mode", "OTO")   # guduum pipeline switch
        kilit_bilgi = dict(getattr(beyin, "_son_kilit_bilgi", {}) or {})
        kilit_engel = beyin.kilit.engel_ozeti() if hasattr(beyin, "kilit") else None
        oipn_acik = bool(getattr(beyin, "oipn_acik", True))
        oipn_beta = float(getattr(beyin, "oipn_beta", 0.3))
        # --- IZLEYICI/GUDUM alanlari (video isterleri) — ayni kilit altinda anlik kopya ---
        prev_cmd = dict(beyin.prev)                    # uygulanan 4 komut (rate-limit sonrasi)
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

    # GUDUM KOMUT TELEMETRISI (video kalem 8): kontrolcunun SON gonderdigi TUM
    # eksenler (throttle/pitch/roll/yaw). Drone davranisini DEGISTIRMEZ; gosterir.
    try:
        _cmd_thr = float(drone._drone.throttle)
        _cmd_pit = float(drone._drone.pitch)
        _cmd_rol = float(drone._drone.roll)
        _cmd_yaw = float(drone._drone.yaw)
    except Exception:
        _cmd_thr = _cmd_pit = _cmd_rol = _cmd_yaw = None

    # GORSEL TAKIP durumu + son NORMALIZE tespit (overlay/rozet icin). durum
    # GORSEL_TAKIP ise GPS yonelimi MIMARI olarak kesilmistir -> index.html
    # "GPS GUDUMU: KAPALI" rozetini kirmizi yakar.
    gorsel = {
        "durum": j_durum,                          # ARAMA | GORSEL_TAKIP
        "mod": vis_mode,                           # OTO | GPS | GORSEL (manuel switch)
        "ey_ref": float(getattr(Cfg, "VIS_EY_REF", 0.0)),   # dikey referans (tilt telafisi; overlay cizer)
        "gps_kesildi": (j_durum == "GORSEL_TAKIP"),
        "pos_count": vis_pos, "lost_count": vis_lost, "n_lock": Cfg.VIS_N_LOCK,
        "dedektor_hazir": bool(model_yon is not None and model_yon.hazir),
        "tespit": vis_tespit,                      # None | {ex,ey,cx,cy,w,h,conf} (normalize)
        "track": ({"id": vis_tespit.get("track_id"), "durum": vis_tespit.get("track_durumu"),
                   "tespit_mi": vis_tespit.get("tespit_mi")} if isinstance(vis_tespit, dict)
                  and vis_tespit.get("track_id") is not None else None),
        "pnp": (_pnp_ui_ozet(_son_pnp_ui)),        # None | {gecerli, mesafe, reproj_err, phi_T, psi_T}
        # FAZ 4: kilit sayaci gostergesi + AV sinirlari + OIPN anahtari/beta
        "kilit": {
            "kumulatif_sn": kilit_bilgi.get("kumulatif_kilit_sn", 0.0),
            "surekli_sn": kilit_bilgi.get("surekli_kilit_sn", 0.0),
            "hedef_sn": 5.0, "pencere_doluluk": kilit_bilgi.get("pencere_doluluk", 0.0),
            "sayan": bool(kilit_bilgi.get("sayan", False)),
            "engel": kilit_bilgi.get("engel"),     # bu kare saymadiysa hangi kosul
            "engel_ozet": kilit_engel,             # kilit tamamlanamadiysa dagilim (teshis)
            "kilit_tamam": bool(kilit_bilgi.get("kilit_tamam", False)),
            "kaplama_yatay": kilit_bilgi.get("kaplama_yatay", 0.0),   # w/W (eksen)
            "kaplama_dikey": kilit_bilgi.get("kaplama_dikey", 0.0),   # h/H (eksen)
            "av_yatay": [0.25, 0.75], "av_dikey": [0.10, 0.90], "kaplama_esik": 0.06,
        },
        "oipn": {"acik": oipn_acik, "beta": oipn_beta},
        # HEDEF GNSS: GORSEL ailesinde (GORSEL_TAKIP/KILIT_BILDIR/ANGAJMAN) KULLANILMIYOR
        "gnss_kullaniliyor": (j_durum in ("ARAMA", "YAKLASMA")),
        # GOREV SONU / VURUS (video kalem 9-10): izleyicinin latch'inden (J-temiz mesafe).
        "gorev_sonu": {"basarili": bool(gorev_s.get("basari")),
                       "vurus_menzili": bool(gorev_s.get("vurus")),
                       "min_mesafe_m": gorev_s.get("en_yakin_m")},
    }
    # MODEL REGISTRY durumu + canli metrikler (arayuz paneli)
    if model_yon is not None:
        gorsel["model"] = {"durum": model_yon.durum(),
                           "liste": model_yon.modelleri_listele(),
                           "metrik": model_yon.metrikler()}

    # --- IZLEYICI TELEMETRISI (video isterleri 3/6/7/8/9/10) — MERGE 2026-07-06 ---
    _now = time.time()
    # d_h (yatay mesafe, m): temiz kestirim, yoksa ham
    d_h_m = None
    _txy = son_xy if son_xy is not None else (
        (son_ham_full[0], son_ham_full[1]) if son_ham_full is not None else None)
    if _txy is not None:
        d_h_m = (((dpos[0] - _txy[0]) ** 2 + (dpos[1] - _txy[1]) ** 2) ** 0.5) * CM_TO_M
    # J duzeltme buyuklugu (ucus telemetrisinden): ham <-> anlik temiz fark (m)
    j_duzeltme_m = None
    if son_ham_full is not None and son_xy is not None and son_z_anl is not None:
        _jd = ((son_ham_full[0] - son_xy[0]) ** 2 + (son_ham_full[1] - son_xy[1]) ** 2
               + (son_ham_full[2] - son_z_anl) ** 2) ** 0.5
        j_duzeltme_m = _jd * CM_TO_M
    paket_yasi_s = (_now - izci_spt) if izci_spt is not None else None

    gnss_info = {
        "paket_yasi_s": paket_yasi_s,
        "kesinti": izci_kesinti,
        "j_duzeltme_m": j_duzeltme_m,
        "none_count": b_none,
    }
    gudum_info = {
        "thr": prev_cmd.get("thr", 0.0), "pitch": prev_cmd.get("pitch", 0.0),
        "roll": prev_cmd.get("roll", 0.0), "yaw": prev_cmd.get("yaw", 0.0),
        "durum": j_durum, "mod": vis_mode, "kaynak": j_kaynak,
        "handoff": b_handoff, "d_h_m": d_h_m,
        "profil": ("intercept+ram" if getattr(Cfg, "GPS_TERMINAL_STRIKE", False)
                   else "standoff"),               # aktif GPS yaklasma profili (bayrak)
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
        olay_listesi = list(_olaylar)[-60:]           # son 60 olay (durumsuz; F5 sorunsuz)

    veri = {
        "connected": connected,
        "drone": {
            "x": dx, "y": dy, "z": dz,
            "altitude_m": drone_alt_m,
            "speed_ms": drone_spd_ms,
            "speed_kmh": drone_spd_ms * MS_TO_KMH,
            "roll": drot[0], "pitch": drot[1], "yaw": drot[2],
            "cmd_throttle": _cmd_thr, "cmd_pitch": _cmd_pit,
            "cmd_roll": _cmd_rol, "cmd_yaw": _cmd_yaw,     # video kalem 8: tam komut
        },
        "target": {
            "x": tx, "y": ty, "z": tz,
            "speed_ms": target_spd_ms,
            "speed_kmh": target_spd_ms * MS_TO_KMH,
        },
        "distance_m": distance_m,               # HAM GPS-avci mesafe (ekrandaki ana deger)
        "j": j_info,
        "gorev_aktif": gorev_aktif,
        "manuel_aktif": manuel_aktif,
        "kaynak": j_kaynak,
        "gorsel": gorsel,
        "olaylar": olay_listesi,                # [{id,t,sv,m}] son 60 (video: olay gunlugu)
        "gnss": gnss_info,                      # bozuk GNSS girdisi + kesinti (ister 3)
        "gudum": gudum_info,                    # uygulanan komutlar + karar + profil (ister 8)
        "takip": takip_info,                    # ID + aktif/pasif + kayip/yeniden (ister 5/6/7)
        "gorev": gorev_info,                    # faz + vurus/basari (ister 9/10)
    }
    # >>> DEV-ONLY >>>
    if dev_yardimci is not None:
        with beyin_lock:
            veri["dev"] = dev_yardimci.durum(beyin)
    # <<< DEV-ONLY <<<
    return veri


# ----------------------------------------------------------
#  HTTP istek isleyici
# ----------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    # HTTP/1.1 keep-alive: FPV long-poll + telemetri ayni TCP baglantisini yeniden
    # kullanir (istek basina baglanti kurulumu/TIME_WAIT birikimi olmaz). Tum
    # yanitlar Content-Length gonderdigi icin guvenlidir.
    protocol_version = "HTTP/1.1"

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
            # HIZLI GORSEL KANAL (~15 Hz istemci; merge 2026-07-07, main 152a7bc port):
            # yalniz son tespit (keypoints dahil) — telemetri tick'ini beklemeden taze
            # bbox. yas_s = tespitin SU ANKI yasi (kare yakalama anindan); istemci
            # kutuyu vx,vy ile yas kadar ILERI cizer -> kutu hedefin simdiki yerine oturur.
            with beyin_lock:
                det = dict(_son_tespit_ui) if _son_tespit_ui is not None else None
            if det is not None and "t_det" in det:
                det["yas_s"] = round(max(0.0, time.perf_counter() - det.pop("t_det")), 3)
            self._send(200, json.dumps({"tespit": det}).encode("utf-8"),
                       "application/json")
        elif self.path == "/api/tune":
            # Mevcut tune parametre degerlerini dondur (slider'lari baslatmak icin).
            vals = {k: getattr(Cfg, k) for k in TUNE_ALLOW}
            self._send(200, json.dumps(vals).encode("utf-8"), "application/json")
        elif self.path.startswith("/api/frame"):
            # LONG-POLL: istemci son aldigi kare sirasini (?seq=N) verir; N'den YENI
            # kare yayinlanana kadar (<=1 sn) bekler, HAZIR JPEG'i aninda doneriz.
            # Yakalama bu yolda DEGIL (kare_uretici_dongusu yapar) -> istek basina
            # PrintWindow gecikmesi kalkti; FPV sabit tempoda akar. seq'siz eski
            # cagrilar (?t=...) en son kareyi hemen alir (geriye uyumlu).
            global _fpv_talep_ts
            _fpv_talep_ts = time.time()           # talep isareti (uretici thread kossun)
            try:
                q = parse_qs(urlparse(self.path).query)
                istemci_seq = int(q.get("seq", ["-1"])[0])
            except Exception:
                istemci_seq = -1
            try:
                bitis = time.monotonic() + 1.0
                with _kare_cond:
                    # Yeni + JPEG'li + TAZE yayin bekle (bosta kalmis bayat kare donmesin)
                    while (_kare["jpeg"] is None or _kare["seq"] == istemci_seq
                           or (time.time() - _kare["ts"]) > 1.5):
                        kalan = bitis - time.monotonic()
                        if kalan <= 0:
                            break
                        _kare_cond.wait(kalan)
                    jpeg, seq, ts = _kare["jpeg"], _kare["seq"], _kare["ts"]
                if jpeg is None or (time.time() - ts) > 2.5:
                    self._send(503, "kare yok (oyun penceresi bekleniyor)".encode("utf-8"),
                               "text/plain; charset=utf-8")
                else:
                    self.send_response(200)
                    self.send_header("Content-Type", "image/jpeg")
                    self.send_header("Content-Length", str(len(jpeg)))
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("X-Kare-Seq", str(seq))   # istemci sonraki istekte geri verir
                    self.end_headers()
                    self.wfile.write(jpeg)
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
            if cmd in ("start", "start_v2"):
                with beyin_lock:
                    beyin.set_kaynak("v2")    # tek guduum kaynagi: Inovasyonlu J
                    _gorev_sifirla("ARAMA")   # izleyici latch'lerini sifirla (basari banner dahil)
                gorev_aktif = True
                manuel_aktif = False          # gorev ve manuel ayni anda olmaz
                msg = "GOREV BASLATILDI - kaynak: Inovasyonlu J"
                olay_ekle("iyi", "GOREV BASLADI — kaynak: Inovasyonlu J")
            elif cmd == "stop":
                gorev_aktif = False
                manuel_aktif = False
                # Guvenlik: drone'u durdur (motorlari kes -> arm=False)
                try:
                    drone.set_control_surfaces(0.0, 0.0, 0.0, 0.0, False)
                except Exception:
                    pass
                msg = "GOREV DURDURULDU - drone pasif (motorlar kapali)"
                olay_ekle("uyari", "GOREV DURDURULDU")   # basari latch'i KORUNUR (banner kalir)
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
            # >>> DEV-ONLY >>>
            elif cmd == "dev_kaynak":
                # KAYNAK secici (gelistirme): "gercek" <-> "filtre". Gudum modu
                # anahtarina (vismode) dokunmaz; yalnizca midcourse beslemesi.
                m = str(data.get("mod", "filtre")).lower()
                if dev_yardimci is None:
                    msg = "DEV kaynak modulu yuklu degil (web/dev_truth.py yok)"
                else:
                    with beyin_lock:
                        _ok, msg = dev_yardimci.uygula(beyin, m)
            # <<< DEV-ONLY <<<
            elif cmd == "oipn":
                # OIPN anahtari + beta (canli tune). Yalniz gorsel guduum katkisini
                # etkiler; PnP gecersizken zaten pasif (regresyon yok).
                with beyin_lock:
                    if "acik" in data:
                        beyin.oipn_acik = bool(data.get("acik"))
                    if "beta" in data:
                        try:
                            beyin.oipn_beta = max(0.0, min(1.0, float(data.get("beta"))))
                        except Exception:
                            pass
                    msg = "OIPN: %s (beta=%.2f)" % (
                        "ACIK" if beyin.oipn_acik else "KAPALI", beyin.oipn_beta)
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
        elif self.path == "/api/sahte":
            # SAHTE TESPIT akisi (mouse -> normalize hedef merkezi). /api/manuel ile
            # ayni desen: yuksek frekansli, status yazisini kirletmez. aktif=false
            # gelirse veya mesaj SAHTE_TAZE_S boyunca kesilirse enjeksiyon durur ->
            # asil algi ciktisina kendiliginden geri donulur (failsafe).
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length).decode("utf-8") if length else "{}"
            try:
                data = json.loads(raw)
            except Exception:
                data = {}

            def _n01(x):
                try:
                    return max(0.0, min(1.0, float(x)))
                except Exception:
                    return 0.5

            with beyin_lock:
                _sahte["aktif"] = bool(data.get("aktif"))
                _sahte["cx"] = _n01(data.get("cx", _sahte["cx"]))
                _sahte["cy"] = _n01(data.get("cy", _sahte["cy"]))
                _sahte["t"] = time.time()
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
        elif self.path == "/api/model":
            # MODEL REGISTRY: {cmd: "tara"|"yukle", ad?}. Hot-swap arka planda.
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length).decode("utf-8") if length else "{}"
            try:
                data = json.loads(raw)
            except Exception:
                data = {}
            cmd = data.get("cmd", "")
            msg, ok = "model yonetici hazir degil (once Gorev Baslat)", False
            if model_yon is not None:
                if cmd == "tara":
                    adlar = model_yon.tara()
                    ok, msg = True, "Tarandi: %d model" % len(adlar)
                elif cmd == "yukle":
                    ad = str(data.get("ad", ""))
                    ok = model_yon.model_yukle(ad, arka_plan=True)
                    # pose sema'sini PnP kestiriciye yansit (swap sonrasi)
                    if ok and algi is not None and algi._pnp is not None:
                        try:
                            algi._pnp.sema_ayarla(model_yon.aktif_sema())
                        except Exception:
                            pass
                    msg = ("'%s' yukleniyor (arka plan)" % ad) if ok else (model_yon._hata or "yuklenemedi")
            self._send(200, json.dumps({"ok": ok, "msg": msg}).encode("utf-8"),
                       "application/json")
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

    # ACILISTA hemen baglan (kullanici tiki beklenmez); olmadiysa connection_manager
    # arka planda 2 sn'de bir denemeye devam eder ve durumu konsola/arayuze yansitir.
    if drone.connect():
        print("[BAGLANTI] Oyuna baglanildi (acilista).")
    else:
        print("[BAGLANTI] Acilista baglanilamadi - arka planda denenmeye devam "
              "(oyun acik ve PLAY modunda mi?).")

    # Arka planda baglanti yoneticisini ve gorev kontrol beynini baslat
    threading.Thread(target=connection_manager, daemon=True).start()
    threading.Thread(target=kontrol_dongusu, daemon=True).start()
    # Gorsel tespit (YOLO) AYRI thread: gorev aktifken best.pt ile hedef bbox uretir.
    threading.Thread(target=dedektor_dongusu, daemon=True).start()
    # Kare uretici: FPV + dedektor icin TEK yakalayici (talep varken ~KARE_FPS).
    threading.Thread(target=kare_uretici_dongusu, daemon=True).start()

    try:
        server = ThreadingHTTPServer((WEB_HOST, WEB_PORT), Handler)
    except OSError as e:
        print("[HATA] %d portu acilamadi (baska bir arayuz ornegi calisiyor olabilir): %s"
              % (WEB_PORT, e))
        return
    print("=" * 52)
    print("  AVCI DRONE - YER KONTROL ISTASYONU calisiyor")
    print("  Tarayicida ac:  http://%s:%d" % (WEB_HOST, WEB_PORT))
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

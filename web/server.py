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
import socket
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# OpenBLAS thread tamponlarini kisitla: varsayilani cekirdek sayisi kadar thread acip
# her birine buyuk tampon ayirmak; 16GB makinede oyun+CUDA yaninda acilis "OpenBLAS:
# Memory allocation failed" ile cokuyordu. Filtre matrisleri kucuk (EKF 4x4-6x6) ->
# 1 thread hem daha hizli hem kucuk. numpy'i ceken TUM importlardan ONCE set edilmeli.
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

# ── GIL DEVIR GECIKMESI (2026-08-17 gece, OLCULDU) ───────────────────────
# Varsayilan sys.getswitchinterval() = 5 ms. Ultralytics predict() her cagrida
# GIL'i onlarca kez birakip geri aliyor (6x torch.cuda.synchronize + torch/cv2
# cagrilari). O anda baska bir thread SAF PYTHON kosuyorsa her geri-alma 5 ms'lik
# kuyruga giriyor. Olcum (60 birak-al dongusu):
#     rakipsiz            41.9 ms
#     1 saf-Python rakip  926.2 ms   (22.1x)
#     4 rakip            3437.2 ms   (82.1x)
#   sys.setswitchinterval(0.0005) sonrasi: 1 rakip 45.8 ms, 4 rakip 47.7 ms
# Bu, det_ms'in 43 ms'ten 250-450 ms'e cikmasinin BIRINCIL carpani.
# Davranisi degistirmez, yalniz thread zamanlamasini incelestirir.
# Kapatmak icin: AVCI_GIL_HIZLI=0
import sys as _sys
if os.environ.get("AVCI_GIL_HIZLI", "1").strip() not in ("", "0"):
    _sys.setswitchinterval(0.0005)

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
POZ_HER_N = int(os.environ.get("AVCI_POZ_HER_N", "5"))   # poz her N turda bir
# ⚠ POZ YALNIZ YAKINDA KOSAR (2026-08-16). Kodun kendi kalite notu:
# "<10 m'de mesafe medyan ~%8, yaw ~6 der; 15 m+ GUVENILMEZ -> terminal faz
# araci." Ama poz UCUSUN TAMAMINDA kosuyordu: zamanin cogunu 20-60 m'de
# geciriyoruz, orada poz hem ISE YARAMIYOR hem dedektorden GPU caliyor.
# OLCULDU: poz acikken FPS 53 -> 14.5, det_ms 18.7 -> 58.2 (dedektorun
# KENDISI 3 kat yavasladi -- GPU cekismesi). Tespit surekliligi faz omrunu
# belirledigi icin bu net ZARAR.
# COZUM: kutu bu esigin USTUNDEyken kos (yani yakinken). Olculen bagintiyla
# max(w,h) >= 40 px ~ 6 m icinde. Uzakta poz HIC kosmaz, dedektor tam hizda.
POZ_MIN_KUTU_PX = float(os.environ.get("AVCI_POZ_MIN_KUTU", "40"))
                      # 3->5 (8 Tem perf: pose ~180ms FP32, gudumde kullanilmiyor -> seyreltip
                      # best.pt'ye GPU birak; ongoru acilirsa geri dusurulur)
# FP16 (half) inference: RTX 4060 (Ada) ~2x hizlanma, dogruluk kaybi ihmal edilebilir.
# set AVCI_FP16=0 ile FP32'ye don (A/B / dogruluk suphesi). Cpu'da zaten otomatik kapali.
FP16_AKTIF = os.environ.get("AVCI_FP16", "1").strip() == "1"

# --- DEDEKTOR MODELI: env ile degistirilebilir (A/B; varsayilan DEGISMEZ) ---------
#   set AVCI_MODEL=C:\...\avci_yolo.pt   -> baska bir .pt ile kos
#   set AVCI_IMGSZ=1280                  -> inference cozunurlugu (verilmezse modelin
#                                           KENDI egitim imgsz'i okunur; o da yoksa 640)
#   set AVCI_SAHI=0                      -> SAHI dilimlemeyi kapat (Cfg.SAHI_AKTIF'i ezer)
# Hicbiri verilmezse: Cfg.VIS_MODEL_PATH @ egitim imgsz'i (best.pt -> 640) = bugunku hal.
MODEL_YOL = os.environ.get("AVCI_MODEL", "").strip() or Cfg.VIS_MODEL_PATH


def _egitim_imgsz(pt_yolu, varsayilan=640):
    """Checkpoint'in train_args.imgsz'ini oku. Model 1280 egitilmisken 640'ta kosmak
    (veya tersi) uzak/kucuk hedef recall'unu oldurur; el ile vermeyi unutmak diye
    modelin kendi kaydindan aliyoruz. Okunamazsa varsayilana duser (gurultusuz)."""
    try:
        import torch
        ck = torch.load(pt_yolu, map_location="cpu", weights_only=False)
        v = int((ck.get("train_args") or {}).get("imgsz") or 0)
        del ck
        return v if v > 0 else int(varsayilan)
    except Exception:
        return int(varsayilan)


_env_imgsz = os.environ.get("AVCI_IMGSZ", "").strip()
MODEL_IMGSZ = int(_env_imgsz) if _env_imgsz.isdigit() else _egitim_imgsz(MODEL_YOL, 640)
_env_sahi = os.environ.get("AVCI_SAHI", "").strip()
SAHI_ZORLA = None if _env_sahi == "" else (_env_sahi == "1")


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


def grab_frame_bgr():
    """(BGR kare, W, H) doner — YOLO dedektorunun kare kaynagi. DOGAL COZUNURLUK
    (kucultme YOK): YOLO zaten imgsz=1280'e kendi letterbox'lar; kareyi once 960'a
    indirip modele geri buyuttermek kucuk/uzak hedefin detayini olduruyordu
    (canli 20-40 m tespit orani offline'in cok altindaydi, 6 Tem log analizi).
    960 kucultme yalnizca FPV JPEG akisinda (fpv_jpeg) yapilir.
    HER ZAMAN kare uretmeye calisir (fallback zinciri):
      1) windows-capture canli karesi (occlusion-proof; oyun arkada olsa bile dogru)
      2) mss oyun-penceresi bolgesi (oyun goruunur/onde ise)
      3) mss tum ekran (son care; ayna riski)
    Yalnizca mss de basarisizsa (None, 0, 0)."""
    pym = pencere_yakala_motoru
    if pym is not None and pym.hazir and pym.calisiyor():
        bgr = pym.get_latest_bgr()
        if bgr is not None:
            _fpv_log("windows-capture (pencere icerigi)")
            bgr = np.ascontiguousarray(bgr)            # cv2/ultralytics contiguous ister
            return bgr, bgr.shape[1], bgr.shape[0]
    # Fallback: mss (windows-capture yok / henuz kare uretmedi / pencere bulunamadi)
    try:
        kaynak, bgr = _mss_grab_bgr()
        _fpv_log(kaynak)
        bgr = np.ascontiguousarray(bgr)
        return bgr, bgr.shape[1], bgr.shape[0]
    except Exception as e:
        _fpv_log("KARE YOK", " (%s)" % e)
        return None, 0, 0


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
        pym = pencere_yakala_motoru
        if pym is not None and pym.hazir:
            if not pym.calisiyor():
                pym.baslat()
            elif pym.yeniden_baglanmali(stale_s=2.5):
                # WATCHDOG: 'calisyor' ama kare bayat/yok ya da pencere degisti
                # (oyun penceresi yeniden yaratildi / WGC dondu / yanlis pencereye
                # baglanildi -> dedektor farkli yeri goruyordu). TAZE yeniden bagla.
                print("[PENCERE_YAKALA] WATCHDOG: kare bayat/yanlis pencere -> yeniden baglaniliyor")
                pym.durdur()
                pym.baslat()
        time.sleep(2.0)


# ----------------------------------------------------------
#  Gorev kontrol beyni (arkadasin AvciKontrol'u)
#  KADEME 1: gorev_aktif=False -> drone UCMAZ, sadece J olcumu yapilir.
#  KADEME 2: buton ile gorev_aktif=True -> drone hedefe gider.
# ----------------------------------------------------------
beyin = AvciKontrol(drone)

# ── GUDUM ZORLA MODU (2026-08-14) ───────────────────────────────────────────
# Arayuzdeki "GPS Güdüm" / "Görsel Güdüm" butonlarinin GERCEK karsiligi.
# beyin.set_vis_mode() yalnizca gosterim icin saklar (kendi docstring'i:
# "HIBRITTE ETKISIZ ... guduume GIRMEZ") -> fazi belirleyen supervisor'a
# (kopru/gazebo_kaynak/control/guidance/supervisor.SupCfg.ZORLA_MOD) yaziyoruz.
# Istek burada saklanir cunku: (a) arayuz modu gorevden ONCE gonderiyor,
# (b) set_kaynak() koprutu yikip yeniden kuruyor -> SupCfg tazeleniyor.
_zorla_mod_istek = None            # None | "GPS" | "GORSEL"
# Son BASARIYLA uygulanan mod (liste = closure'dan yazilabilsin).
# kontrol_dongusu her tikte kiyaslar; farkliysa tekrar dener.
_zorla_uygulandi = [object()]      # baslangicta istekten farkli olsun


def _zorla_mod_uygula():
    """Saklanan zorla modunu supervisor'a yaz. Kopru yoksa False doner."""
    try:
        # 2026-08-24: eski supervisor KALDIRILDI. Faz zorlamasi yeni hatta
        # env ile yapilir (DOW_KILIT_N / DOW_KAYIP_N) -> burada islevsiz.
        _kg = getattr(beyin, "kopru_gudum", None)
        _sup = getattr(_kg, "_sup", None) if _kg is not None else None
        if _sup is None:
            return False
        _sup.SupCfg.ZORLA_MOD = _zorla_mod_istek
        # SARTNAME KILIT SAYACI KANCASI: supervisor'in "GORSEL" devir olcutu
        # arayuzdeki "X.X / 5.0 s" sayaciyla AYNI olsun diye baglaniyor.
        # (Ham tespit saymak yanlisti: model 100 m'de de goruyor ama o kilit degil.)
        try:
            # DEVIR sayaci (faz kapisi YOK) -- sartname sayaci (beyin.kilit)
            # yalniz GORSEL fazda saydigi icin devir olcutu olarak kullanilamaz
            # (dongusel bagimlilik; bkz. ana_kontrol.__init__ aciklamasi).
            _sup.kilit_kaynagi = lambda: beyin.kilit_devir.durum()
            # Devirde sayaci sifirla (sahte ikinci devir olmasin; bkz.
            # supervisor.kilit_sifirla aciklamasi).
            _sup.kilit_sifirla = lambda: beyin.kilit_devir.sifirla()
            _kd = _sup.kilit_kaynagi()
            print("[GUDUM] kilit kaynagi bagli (esik %.1f s, boyut >=%%%.1f)"
                  % (_kd.get("gereken_s", 5.0), _kd.get("esik_pct", 6.0)))
        except Exception as _ke:
            _sup.kilit_kaynagi = None
            print("[GUDUM] !! kilit kaynagi baglanamadi: %r" % (_ke,))
        print("[GUDUM] supervisor zorla modu -> %s" % (_zorla_mod_istek or "OTO"))
        return True
    except Exception as e:
        print("[GUDUM] zorla mod uygulanamadi: %r" % (e,))
        return False
beyin_lock = threading.Lock()
gorev_aktif = False

# ----------------------------------------------------------
#  CANLI TUNE: arayuzdeki slider'lar Cfg'yi calisirken degistirir.
#  Kontrol dongusu Cfg.X'i HER tik okudugundan degisiklik ANINDA etki eder
#  (server yeniden baslatmaya gerek YOK). Guvenlik icin sadece bu allowlist.
# ----------------------------------------------------------
#  BASIT IBVS SETI (2026-07-07): arayuz slider'lariyla 1:1. Eski PN knob yigini
#  yasayla birlikte SILINDI. Yapisal sabitler (isaretler, FSM zamanlamalari, GPS PD)
#  Cfg'de sabit (gerekirse ana_kontrol.py'den duzenle). Yeni slider = TUNE_DEFS ile ES.
TUNE_ALLOW = {
    "YAW_MAX",           # yaw tavani (doygunluk)
    "VIS_CONF_MIN",      # tespit guven esigi
}

# ----------------------------------------------------------
#  TUNE LOGU (1 Hz): slider degerleri SANIYE BAZINDA veri/tune_log_*.csv'ye yazilir.
#  Amac: ucus SIRASINDA parametre degistirip "iyilesti mi?" bakabilmek — rapor
#  (web/tune_rapor.py) bu logu ucus loguyla t_wall uzerinden hizalar ve her
#  parametre-degisim SEGMENTI icin metrikleri ayri satirda kiyaslar. Boylece tek
#  ucusta bircok tune denemesi test edilir (ucus basina tek set kisiti kalkar).
# ----------------------------------------------------------
_TUNE_LOG_PATH = None
_TUNE_LOG_KOLON = None   # sirali param listesi (baslikla ayni sira garanti)


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
            # DEGISMEDIYSE de yazilir (saniye bazli kesintisiz zaman ekseni);
            # dosya kucuk kalir (~saatte 300 KB'den az), rapor hizalamasi basit olur.
            f.write("%.3f," % time.time()
                    + ",".join("%g" % float(v) for v in vals) + "\n")
            f.flush()
        except Exception:
            pass
        time.sleep(1.0)


# "Degerleri Yazdir" Excel raporuna slider setine EK yazilan sabitler: kosu kosullarini
# tam kayda gecirmek icin (isaretler + ongoru kapilari + kilit isteri esikleri).
# hasattr ile okunur -> Cfg'den kalkan bir isim raporu KIRMAZ, sadece dusurulur.
TUNE_SABIT_RAPOR = (
    "VIS_WIN_NEED_S", "VIS_LOCK_PCT", "VIS_STALE_S",
)

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
# ⚠ 2026-08-17 gece OLCULDU — GECIKME DALGALANMASININ KOKU BURASIYDI.
#   Liste HIC kirpilmiyordu ve her 5 sn'de TUM birikim json.dump(..., indent=2)
#   ile yeniden serilestiriliyordu. indent verildigi icin CPython'un C encoder'i
#   DEVRE DISI kalir -> saf Python _make_iterencode calisir:
#        1.000 kayit   33.5 ms
#        5.000 kayit   88.0 ms
#       10.000 kayit  167.7 ms
#       22.243 kayit  353.5 ms   <- o anki dosya 11.6 MB
#   Ustelik bu kod `with beyin_lock:` ALTINDA kosuyor -> dedektorun sonuc yazma
#   blogunu ve /api/telemetry'yi de kilitliyordu. Sonuc: det_ms oturum boyunca
#   66 ms -> 443 ms'e TIRMANIYORDU (dogrusal, kayit sayisiyla).
#   Kirpma + daha uzun periyot: GIL tutma %7.1 -> %0.27 ve TIRMANMA DURUR.
#   Tamamen kapatmak icin: AVCI_GPS_LOG=0
_gps_log_kayitlar = deque(maxlen=int(os.environ.get("AVCI_GPS_LOG_MAX", "3000") or 3000))
_GPS_LOG_ACIK = os.environ.get("AVCI_GPS_LOG", "1").strip() not in ("", "0")
_GPS_LOG_PERIYOT = float(os.environ.get("AVCI_GPS_LOG_S", "20") or 20)
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
# Takip-ID kapanma esigi. ESKIDEN Cfg.VIS_STALE_S + Cfg.VIS_LOST_TO_GPS_S idi;
# VIS_LOST_TO_GPS_S eski gorsel yasaya aitti ve 2026-08-11'de SILINDI (kayip
# karari artik supervisor'in: KAYIP_M=20 kare). Deger korunuyor: 0.5 + 2.0.
TAKIP_TAM_KAYIP_S = Cfg.VIS_STALE_S + 2.0   # ~2.5 s; takip-ID kapanma esigi
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


# --- Izleyici durumu: YALNIZ kontrol thread'i yazar (tek-yazar); build_telemetry beyin_lock ile okur ---
# id: GERCEK ByteTrack track_id (beyin.son_tespit tasir); tracker yoksa sentetik sayac (sonraki).
# ilk: bu gorevde ILK TESPIT ilan edildi mi (ILK/YENIDEN ayrimi ID degerine bagli degil).
_takip = {"id": None, "sonraki": 1, "yeniden": 0, "aktif": False, "kayip_t": None, "ilk": False}
_gorev = {"faz": "HAZIR", "t0": None, "vurus": False, "basari": False,
          "en_yakin_m": None, "vurus_t": None, "mesafe_kaynak": None}
# Kontrol dongusu hata sayaci (sessiz yutma yerine gorunur sayim)
_kontrol_hata = {"n": 0}
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


def _hibrit_bilgi(beyin):
    """Supervisor durum sozlugu {faz, gecis_sayisi, kilit_sayac, ...} | None."""
    # 2026-08-24: faz mercii artik dow/amir.py (eski supervisor kaldirildi).
    dg = getattr(beyin, "dow_gudum", None)
    if dg is not None:
        try:
            return dg.faz_ozet() or None
        except Exception:
            return None
    return None


def _kilit_durum(beyin):
    """KilitSayaci durumu (sartname 6.1.2/6.1.4). Yoksa bos sozluk."""
    k = getattr(beyin, "kilit", None)
    if k is None:
        return {}
    try:
        return k.durum()
    except Exception:
        return {}


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

    # 2) TAKIP-ID makinesi (girdi: beyin.son_tespit_t tazeligi — gudumdeki tanimla ayni).
    #    ID kaynagi GERCEK ByteTrack track_id'si (beyin.son_tespit icinde tasinir);
    #    alan yoksa (tracker devre disi) eski sentetik sayaca geri duser.
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
    # HIBRIT: gorsel faz bilgisi supervisor'dan gelir (beyin.durum'dan DEGIL).
    # Eski kod `durum=="GORSEL_GUDUM"` bakiyordu; hibritte o durum hic olusmaz
    # -> ILK TESPIT / ANGAJMAN / VURUS kenarlari sessizce olmustu (2026-08-11).
    _hib = _hibrit_bilgi(beyin)
    _faz = (_hib or {}).get("faz")
    _gorsel_aktif = (_faz == "VISUAL") if _faz is not None else (durum == "GORSEL_GUDUM")
    _kil = _kilit_durum(beyin)
    if durum != _izci["durum_prev"]:
        if _gorsel_aktif:
            olay_ekle("iyi", "GORSEL GUDUME GECILDI — GPS yonelimi KAPALI (yonelim yalniz kamera)")
        elif (not _gorsel_aktif) and _izci["durum_prev"] == "GORSEL_GUDUM":
            olay_ekle("uyari", "GPS'e DONULDU — yeniden yaklasma")
        _izci["durum_prev"] = durum
    if beyin.handoff and not _izci["handoff_prev"]:
        olay_ekle("bilgi", "Tespit menzilinde — KILIT")
    _izci["handoff_prev"] = bool(beyin.handoff)
    # Supervisor'in kendi kilit sayaci (15 karelik pencerede N tespit).
    # Eskiden beyin._vis_pos_count + Cfg.VIS_N_LOCK idi; ikisi de eski gorsel
    # yasayla birlikte SILINDI (2026-08-11).
    _sup_say = int((_hib or {}).get("kilit_sayac") or 0)
    _sup_gerek = 10
    if (not _izci["kilit_ilan"]) and _sup_say >= _sup_gerek:
        _izci["kilit_ilan"] = True
        olay_ekle("iyi", "GORSEL KILIT hazir (%d/%d)" % (_sup_say, _sup_gerek))
    elif _sup_say == 0:
        _izci["kilit_ilan"] = False

    # 3.5) KILITLENME ISTERI kenari (KilitSayaci latch'i; sartname 6.1.2/6.1.4
    #      isterinin olay gunlugu kaniti — kural 8: sadece kenar tespiti. Eski
    #      YAKLASMA/TAKIP/TERMINAL alt-FSM'i basit-IBVS gecisinde SILINDI.)
    if _kil.get("ok") and not _izci["kilit_ok_prev"]:
        _izci["kilit_ok_prev"] = True
        olay_ekle("iyi", "KILIT ISTERI SAGLANDI — 10 sn pencerede >= %.0f sn kumulatif kilit"
                  % float(getattr(Cfg, "VIS_WIN_NEED_S", 5.0)))
    elif not _kil.get("ok"):
        _izci["kilit_ok_prev"] = False

    # 4) GOREV FAZI + VURUS/BASARI (mesafe 50 Hz olculur -> vurus ani atlanmaz)
    mesafe, kaynak = _mesafe_olc()
    if mesafe is not None:
        if _gorev["en_yakin_m"] is None or mesafe < _gorev["en_yakin_m"]:
            _gorev["en_yakin_m"] = mesafe

    # ANGAJMAN: gorsel faz aktif + takip canli + KILIT ISTERI SAGLANMIS (kilit_ok latch).
    # Sartname 6.1.3: angajman cipi ancak kilitlenme isteri (5/10 sn) doldugunda yanar;
    # oncesinde faz cipi "KILIT"te kalir. (Guduum yasasi tek: basit IBVS; cip salt gosterim.)
    # HIBRIT: gorsel faz bilgisi artik supervisor'dan gelir (durum degil).
    # Eski ifade `durum=="GORSEL_GUDUM"` idi; hibritte o durum hic olusmadigi
    # icin ANGAJMAN/VURUS/BASARI mandallari SESSIZCE OLUYDU (2026-08-11).
    angajman = (_gorsel_aktif and _takip["aktif"] and bool(_kil.get("ok")))

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
        if mesafe is not None:                                    # ISKA tespiti (angajman icinde)
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
        # GORSEL_GUDUM ama kilit isteri henuz dolmadi -> KILIT cipi: sartname akisinda
        # bu "kilitlenme ve takip asamasi"dir; ANGAJMAN ancak kilit_ok latch'i ile.
        _gorev["faz"] = "KILIT" if (_gorsel_aktif or durum == "KILIT") else "YAKLASMA"

    # ── VURUS: MESAFE OLCUTU ANGAJMAN CIPINDEN AYRILDI (2026-08-16 gece) ─────
    # Eski hali `elif angajman:` blogunun ICINDEydi. angajman = gorsel_faz AND
    # takip AND kilit.ok. Kilit mandali (sartname sayaci, LOCK_PCT=0.06) hedefin
    # ekranin %6'sini kaplamasini, yani R <= 8.6 m'yi ve ayni anda VISUAL fazda
    # olmayi gerektiriyor; gorsel faz ise OLCULDU 10/10 fazda bizi 11.7 m'den
    # 32.1 m'ye ATIYOR -> mandal hic kapanmadi -> `mesafe < VURUS_ESIK_M`
    # karsilastirmasi HIC CALISTIRILMADI. Telemetride en_yakin_m 0.49 m
    # gorunurken vurus=False cikmasinin sebebi buydu; yani deneyleri
    # PUANLAYAMIYORDUK.
    # ⚠ ANGAJMAN cipi (sartname 6.1.3) DEGISMEDI, yukarida aynen duruyor.
    # ⚠ `gorev_aktif` kapisi _gorev_izle() basinda zaten var -> gorev pasifken
    #   buraya hic gelinmez, sahte vurus riski yok.
    if (not _gorev["vurus"]) and mesafe is not None and mesafe < VURUS_ESIK_M:
        _gorev["vurus"] = True
        _gorev["vurus_t"] = now
        _gorev["mesafe_kaynak"] = kaynak
        olay_ekle("kritik", "VURUS! mesafe=%.1f m (%s kaynak)" % (mesafe, kaynak))


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
            "kayitlar": list(_gps_log_kayitlar),   # deque -> json serilestirilebilir
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
    if _GPS_LOG_ACIK and _now - _gps_log_son_yaz > _GPS_LOG_PERIYOT:
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
                        # ⚠ 2026-08-14: ZORLA MOD'u BURADA uygula.
                        # Kopru (beyin.kopru_gudum) ILK GUDUM TIKINDE tembel
                        # kuruluyor; buton anlarinda henuz YOK -> yazma sessizce
                        # dusuyordu. Kanit: karar logunda 82 satirin hepsi "OTO",
                        # sunucu logunda "zorla modu ->" satiri HIC yok.
                        # Burada her tikte denenip BIR KEZ basarili olunca durur.
                        if _zorla_uygulandi[0] != _zorla_mod_istek:
                            if _zorla_mod_uygula():
                                _zorla_uygulandi[0] = _zorla_mod_istek
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
            except Exception as e:
                # SESSIZ YUTMA KALDIRILDI (2026-08-10 denetimi): bu blok
                # beyin.adim() -> _kopru_tik -> DowKopru.adim() -> SDK zincirinin
                # TAMAMINI kapsiyor. Istisna surekliyse arac SON stick'le
                # suresiz ucar ve konsolda tek satir cikmazdi. Kural: "thread
                # asla sessiz olmesin". Dongu yine DEVAM eder (tek kotu tik
                # ucusu dusurmesin) ama ilk hata + periyodik sayim bildirilir.
                _kontrol_hata["n"] += 1
                if _kontrol_hata["n"] == 1 or _kontrol_hata["n"] % 250 == 0:
                    print("[KONTROL HATA] tik %d: %r" % (_kontrol_hata["n"], e))
                    if _kontrol_hata["n"] == 1:
                        import traceback as _tb
                        _tb.print_exc()
        time.sleep(0.02)   # 50 Hz


# ----------------------------------------------------------
#  NEGATIF VERI KAYDI (Hat C) — AYRI thread, env ile ACILIR.
#
#  NEDEN SERVER'DA: manuel ucus arayuzden yapiliyor (tarayici klavyesi ->
#  /api/manuel -> SDK), yani UI sunucusu TCP'yi tutuyor. Oyun TEK baglanti
#  kabul ettigi icin pose/kayit_ucusu.py ayni anda kayit ALAMAZ. Cozum:
#  kullanici her zamanki gibi Manuel Mod'da ucar, kayit AYNI baglantidan
#  buradan akar.
#
#  FORMAT pose/kayit_ucusu.py ile BIREBIR (kare_*.png + telemetri.jsonl +
#  telemetri_akis.jsonl + meta.json) -> veriseti/negatif_topla.py degismeden okur.
#
#  ACMA:  set AVCI_NEG_KAYIT=C:\talon_dataset_v2\negatif_ham
#         [set AVCI_NEG_HZ=2]        kare sikligi (vars 2; ardisik kare
#                                    birbirinin kopyasi olmasin)
#  Env verilmezse thread HIC baslamaz -> sifir maliyet, davranis degismez.
# ----------------------------------------------------------
NEG_KAYIT_DIR = os.environ.get("AVCI_NEG_KAYIT", "").strip()
NEG_KAYIT_HZ = float(os.environ.get("AVCI_NEG_HZ", "2") or 2)
_neg_durum = {"aktif": False, "kare": 0, "oturum": None, "hata": None}

# --- POZITIF YAKALAMA (elle bbox etiketlenecek kareler) --------------------
#   set AVCI_KAYIT=C:\talon_dataset_v2\pozitif    -> yakalama ACIK
#   [set AVCI_KAYIT_AD=talon1]   dosya on eki  -> talon1_0000.png/.txt
#   [set AVCI_KAYIT_ON=25]       baglantidan sonra kac sn BEKLE (kalkis payi)
#   [set AVCI_KAYIT_HZ=2]        kare sikligi
# Her kare icin BOS bir .txt de yazilir; veriseti/bbox_etiketle.py bunu doldurur.
# BOS .txt = "henuz etiketlenmedi" (dosya boyutu = durum; ayri state dosyasi yok).
KAYIT_DIR = os.environ.get("AVCI_KAYIT", "").strip()
KAYIT_AD = os.environ.get("AVCI_KAYIT_AD", "talon1").strip() or "talon1"
KAYIT_ON_S = float(os.environ.get("AVCI_KAYIT_ON", "25") or 25)
KAYIT_HZ = float(os.environ.get("AVCI_KAYIT_HZ", "2") or 2)
# Kac kareden sonra DURSUN (0 = sinirsiz). Deneme koşusu icin: 10 cek, bak,
# sonra sinirsiz ac. Sayac klasordeki MEVCUT kareleri de sayar.
KAYIT_MAX = int(os.environ.get("AVCI_KAYIT_MAX", "0") or 0)
_kayit_durum = {"aktif": False, "kare": 0, "klasor": None, "geri_sayim": None}


def pozitif_kayit_dongusu():
    """Kareleri <ad>_NNNN.png + BOS <ad>_NNNN.txt olarak yazar.

    Baglanti kurulduktan AVCI_KAYIT_ON saniye sonra baslar (kalkis/tirmanis
    kadraja girmesin diye). Telemetriyi de yazar: etiketleme icin sart degil
    ama sonradan mesafe katmanlamasi / oto-etiket dogrulamasi icin lazim olur,
    maliyeti sifir."""
    import queue
    if not KAYIT_DIR:
        return
    try:
        import cv2
    except Exception as e:
        print("[KAYIT] cv2 yuklenemedi -> yakalama KAPALI (%r)" % e)
        return

    os.makedirs(KAYIT_DIR, exist_ok=True)
    _kayit_durum["klasor"] = KAYIT_DIR

    # Klasorde kare varsa NUMARADAN DEVAM et (ikinci ucus ustune yazmasin).
    mevcut = [a for a in os.listdir(KAYIT_DIR)
              if a.startswith(KAYIT_AD + "_") and a.endswith(".png")]
    n = 0
    for a in mevcut:
        try:
            n = max(n, int(a[len(KAYIT_AD) + 1:-4]) + 1)
        except ValueError:
            pass
    if n:
        print("[KAYIT] klasorde %d kare var -> %s_%04d'den devam" % (len(mevcut), KAYIT_AD, n))

    kuyruk = queue.Queue(maxsize=64)
    dusen = {"n": 0}

    def _yazici():
        while True:
            is_ = kuyruk.get()
            if is_ is None:
                break
            yol, kare = is_
            try:
                cv2.imwrite(yol, kare)
            except Exception:
                pass
    threading.Thread(target=_yazici, daemon=True).start()

    jsonl = open(os.path.join(KAYIT_DIR, "telemetri.jsonl"), "a", encoding="utf-8")
    # SUREKLI AKIS (~20 Hz). Kare-telemetri GECIKMESI olculdu: kare telemetriden
    # eski ve manevrada bagil geometri hizli degistigi icin projekte kutu kayiyor
    # (|roll|>=20 karelerde IoU 0.83 -> 0.68). Telafi ancak yeterli ORNEKLEME
    # varsa ise yarar: 2 Hz'de ara-degerlemenin kendisi hatali (dt suprumu 50
    # elle duzeltilmis kareyle olculdu, net kazanc CIKMADI). 20 Hz akisla dt
    # gercekten cozulebilir -> veriseti/oto_etiket.py --dt.
    akis = open(os.path.join(KAYIT_DIR, "telemetri_akis.jsonl"), "a",
                encoding="utf-8")
    print("[KAYIT] POZITIF yakalama -> %s  (on ek=%s, %.1f Hz, %.0f sn bekleme)"
          % (KAYIT_DIR, KAYIT_AD, KAYIT_HZ, KAYIT_ON_S))

    periyot = 1.0 / max(KAYIT_HZ, 0.1)
    baglanti_t = None
    son_kare = 0.0
    son_bilgi = 0.0
    try:
        while True:
            t = time.perf_counter()
            # Geri sayim BAGLANTIDAN degil GOREV BASLANGICINDAN. Aksi halde
            # kullanici "Gorev Baslat"a basana kadar yerde duran arac
            # kaydedilir (yuzlerce ise yaramaz kare). 25 sn = kalkis/tirmanis
            # payi; o sure kadraja girmesin.
            if not (drone.is_connected() and gorev_aktif):
                baglanti_t = None
                _kayit_durum["aktif"] = False
                time.sleep(0.2)
                continue
            if baglanti_t is None:
                baglanti_t = t
                print("[KAYIT] gorev basladi -> %.0f sn sonra yakalama baslar."
                      % KAYIT_ON_S)
            bekleyen = KAYIT_ON_S - (t - baglanti_t)
            if bekleyen > 0:
                _kayit_durum["geri_sayim"] = bekleyen
                if t - son_bilgi >= 5.0:
                    son_bilgi = t
                    print("[KAYIT] baslamaya %.0f sn" % bekleyen)
                time.sleep(0.2)
                continue
            if _kayit_durum["geri_sayim"] is not None:
                _kayit_durum["geri_sayim"] = None
                print("[KAYIT] BASLADI.")
            _kayit_durum["aktif"] = True

            # --- SUREKLI AKIS: her tik (~20 Hz), kareyle AYNI saat (perf_counter) ---
            try:
                _tel = drone.get_telemetry()
                _tru = drone.get_debug_truth()
                if _tru.get("available"):
                    akis.write(json.dumps({
                        "t": t,
                        "dp": list(_tru["drone"]["position"]),
                        "dr": list(_tel["drone"]["rotation"]),
                        "tp": list(_tru["target"]["position"]),
                        "tr": list(_tel["target"]["rotation"]),
                    }) + "\n")
            except Exception:
                pass

            if (t - son_kare) < periyot:
                time.sleep(0.02)
                continue
            son_kare = t
            bgr, _w, _h = grab_frame_bgr()
            if bgr is None:
                continue
            H, W = bgr.shape[:2]
            ad = "%s_%04d" % (KAYIT_AD, n)
            try:
                kuyruk.put_nowait((os.path.join(KAYIT_DIR, ad + ".png"), bgr))
            except queue.Full:
                dusen["n"] += 1
                continue
            # BOS .txt: "kare var, etiket YOK". Etiketleyici doldurunca boyut > 0
            # olur -> dosya boyutu tek dogruluk kaynagi (ayri state dosyasi yok).
            open(os.path.join(KAYIT_DIR, ad + ".txt"), "w").close()
            try:
                tel = drone.get_telemetry()
                tru = drone.get_debug_truth()
                jsonl.write(json.dumps({
                    "t": t, "kare": ad + ".png", "W": W, "H": H,
                    "drone_pos": list(tel["drone"]["position"]),
                    "drone_rot_rpy": list(tel["drone"]["rotation"]),
                    "truth_drone_pos": list(tru["drone"]["position"])
                    if tru.get("available") else None,
                    "truth_target_pos": list(tru["target"]["position"])
                    if tru.get("available") else None,
                    "target_rot_rpy": list(tel["target"]["rotation"]),
                }) + "\n")
                jsonl.flush()
            except Exception:
                pass
            n += 1
            _kayit_durum["kare"] = n
            if n % 25 == 0:
                print("[KAYIT] %d kare (kuyruk=%d dusen=%d)"
                      % (n, kuyruk.qsize(), dusen["n"]))
            if KAYIT_MAX and n >= KAYIT_MAX:
                print("[KAYIT] SINIR (%d kare) doldu -> yakalama DURDU. "
                      "Sinirsiz icin AVCI_KAYIT_MAX'i kaldirip yeniden baslat."
                      % KAYIT_MAX)
                _kayit_durum["aktif"] = False
                break                       # finally: dosyalar duzgun kapansin
    except Exception as e:
        print("[KAYIT] DURDU: %r" % e)
    finally:
        try:
            jsonl.close()
        except Exception:
            pass


def neg_kayit_dongusu():
    """Kareleri + truth telemetriyi kayit_ucusu formatinda diske yazar."""
    import queue
    if not NEG_KAYIT_DIR:
        return
    try:
        import cv2
    except Exception as e:
        _neg_durum["hata"] = "cv2 yok: %r" % e
        print("[NEG-KAYIT] cv2 yuklenemedi -> kayit KAPALI (%r)" % e)
        return

    oturum = os.path.join(NEG_KAYIT_DIR, time.strftime("oturum_%Y%m%d_%H%M%S"))
    os.makedirs(oturum, exist_ok=True)
    _neg_durum["oturum"] = oturum

    # PNG yazimi AGIR -> ayri thread + kuyruk; yakalama dongusu bloklanmasin.
    kuyruk = queue.Queue(maxsize=64)
    dusen = {"n": 0}

    def _yazici():
        while True:
            is_ = kuyruk.get()
            if is_ is None:
                break
            yol, kare = is_
            try:
                cv2.imwrite(yol, kare)
            except Exception:
                pass
    threading.Thread(target=_yazici, daemon=True).start()

    with open(os.path.join(oturum, "meta.json"), "w", encoding="utf-8") as f:
        json.dump({
            "kaynak": "web/server.py neg_kayit_dongusu (manuel ucus)",
            "hz": NEG_KAYIT_HZ,
            "hfov_deg": None, "kamera_tilt_deg": None,
            "birimler": "cm, derece, cm/s; rot tuple sirasi SDK: (roll, pitch, yaw)",
            "not": ("Hat C negatif havuzu. Etiket URETILMEZ; negatif karari "
                    "veriseti/negatif_topla.py:negatif_mi() ile verilir."),
        }, f, ensure_ascii=False, indent=2)

    jsonl = open(os.path.join(oturum, "telemetri.jsonl"), "w", encoding="utf-8")
    akis = open(os.path.join(oturum, "telemetri_akis.jsonl"), "w", encoding="utf-8")
    print("[NEG-KAYIT] ACIK -> %s  (%.1f Hz)" % (oturum, NEG_KAYIT_HZ))
    print("[NEG-KAYIT] Manuel Mod'da uc; hedefe BAKMA (etrafa/yere/goge don).")

    periyot = 1.0 / max(NEG_KAYIT_HZ, 0.1)
    son_kare = 0.0
    n = 0
    truth_uyari = False
    try:
        while True:
            t = time.perf_counter()
            if not drone.is_connected():
                _neg_durum["aktif"] = False
                time.sleep(0.2)
                continue
            try:
                tel = drone.get_telemetry()
                tru = drone.get_debug_truth()
            except Exception:
                time.sleep(0.2)
                continue
            if not tru.get("available"):
                if not truth_uyari:
                    truth_uyari = True
                    print("[NEG-KAYIT] truth telemetri YOK (available=False) -> "
                          "kayit bekliyor. Oyunda debug/truth acik olmali.")
                _neg_durum["aktif"] = False
                time.sleep(0.5)
                continue
            truth_uyari = False
            _neg_durum["aktif"] = True

            dpos = tel["drone"]["position"]
            drot = tel["drone"]["rotation"]
            hpos = tru["target"]["position"]
            trot = tel["target"]["rotation"]
            akis.write(json.dumps({
                "t": t, "dp": list(dpos), "dr": list(drot),
                "tp": list(hpos), "tr": list(trot),
                "cm": int(tru.get("corruption_mask", 0)),
            }) + "\n")

            if (t - son_kare) >= periyot:
                son_kare = t
                bgr, _w, _h = grab_frame_bgr()
                if bgr is not None:
                    H, W = bgr.shape[:2]
                    n += 1
                    ad = "kare_%06d.png" % n
                    try:
                        kuyruk.put_nowait((os.path.join(oturum, ad), bgr))
                    except queue.Full:
                        dusen["n"] += 1
                        n -= 1
                    else:
                        jsonl.write(json.dumps({
                            "t": t, "kare": ad, "W": W, "H": H,
                            "drone_pos": list(dpos), "drone_rot_rpy": list(drot),
                            "truth_drone_pos": list(tru["drone"]["position"]),
                            "truth_target_pos": list(hpos),
                            "target_rot_rpy": list(trot),
                            "corruption_mask": int(tru.get("corruption_mask", 0)),
                        }) + "\n")
                        jsonl.flush()
                        _neg_durum["kare"] = n
                        if n % 20 == 0:
                            print("[NEG-KAYIT] %d kare (kuyruk=%d dusen=%d)"
                                  % (n, kuyruk.qsize(), dusen["n"]))
            kalan = 0.05 - (time.perf_counter() - t)
            if kalan > 0:
                time.sleep(kalan)
    except Exception as e:                              # ASLA sessiz olme
        _neg_durum["hata"] = repr(e)
        print("[NEG-KAYIT] DURDU: %r" % e)
    finally:
        try:
            jsonl.close(); akis.close()
        except Exception:
            pass


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
POSE_MODEL_PATH = getattr(Cfg, "VIS_POSE_MODEL_PATH",
                          os.path.join(PROJ_ROOT, "models", "talon_pose.pt"))
# POSE TAMAMEN KAPALI (2026-07-10 kullanici istegi): sadece detection (bbox) kalsin.
# Pose gozlemci/lead idi ve ~200ms/tik GPU'yu bbox'tan caliyordu. False -> pose modeli
# HIC yuklenmez, hic kosmaz; roll-lead/poz telemetrisi zarif kapali (poz_dedektor=None).
# ⚠ 2026-08-16: env ile ACILABILIR yapildi (kullanici: "pose modeli entegre et").
# Varsayilan ACIK ama tek degiskenle kapanir: AVCI_POSE=0
# Kapatma gerekcesi (2026-07-10) PyTorch .pt ile olculen ~200 ms/tik idi;
# artik TensorRT .engine kullaniliyor. MALIYETI OLC: telemetride perf.poz_ms.
# fps 30'un altina duserse KAPAT -- dedektor sureklilikleri fazin omrunu
# belirliyor ve bugun olculdu ki bbox'i yavaslatmak her seyi bozar.
# ⚠ 2026-08-16 20:50 GERI ALINDI -> varsayilan KAPALI.
# Olculdu: poz acikken FPS 53 -> 14.5, det_ms 18.7 -> 58.2. Poz kendisi
# 40.3 ms/kare (eski .pt gerekcesi 200 ms'ti, yani engine cok daha ucuz)
# AMA ayni GPU'da dedektorle yarisiyor ve dedektoru 3 KAT yavaslatiyor.
# Bugun defalarca olculdu ki TESPIT SUREKLILIGI faz omrunu belirliyor;
# dedektoru yavaslatan her sey net ZARAR. Denemek icin: AVCI_POSE=1
# ⚠ 2026-08-16 gece: VARSAYILAN 1 -> 0. Kullanici acik talimat verdi:
#   "pose modeli kapat sadece detectionla ilerle".
#   OLCUM de ayni yone isaret ediyordu: poz_ms medyan 90 ms (en kotu 183 ms) ve
#   /gorsel/poz cikti = None, yani bedeli odenip hicbir sey uretmiyordu.
#   Poz zaten GOZLEMCI idi, gudume girmiyordu -> kapatmak davranisi degistirmez,
#   yalnizca GPU/GIL'i tespite birakir.
#   Geri acmak icin:  AVCI_POSE=1
POSE_AKTIF = (os.environ.get("AVCI_POSE", "0").strip() not in ("", "0"))
# ── KROP POZ YOLU (2026-08-21) ─────────────────────────────────────────────
# Tam-kare poz modeli 960x960 kosar; hedef 12-25 m'de 28x12 px'e duser ve 6
# keypoint o kadar pikselden cikmaz. Krop modeli dedektorun kutusunu 1.5x payla
# kesip SABIT 256x96'ya getirir -> hedef her menzilde ayni buyuklukte gorunur.
# 1532 val karesinde OLCULDU (orijinal kare pikseli, gercek dedektor kutusuyla):
#   12-25 m ortanca 1.36 vs 1.77 px | p90 3.78 vs 5.02 | genel p90 19.46 vs 23.50
#   sag kanat p90 18.04 vs 27.21 | sol kanat p90 20.18 vs 36.98 (tam-kare model
#   sol kanatta asimetrik kotu) | hedefi kacirma %0.4 vs %1.6
# Tam-kare model yalniz 0-6 / 6-12 m ORTANCASINDA az onde; genel ortancanin onu
# gostermesi veri kusuru (orneklerin %53'u 0-6 m bandinda).
# ⚠ VARSAYILAN KAPALI. Acmak icin IKISI birden:
#     AVCI_POZ_KROP=1
#     AVCI_POSE_MODEL=<...>/runs/pose/talon_pose_krop_v2/weights/best.pt
#   Krop modeli 256x96'dir; tam kareye 960 ile verilirse COP uretir.
# ⚠ Poz hala GOZLEMCI -- guduume girmez. Bu bayrak yalnizca hangi poz modelinin
#   nasil beslendigini degistirir; bbox/gudum akisi AYNEN kalir.
POZ_KROP_AKTIF = (os.environ.get("AVCI_POZ_KROP", "0").strip() not in ("", "0"))
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
        # ByteTrack alanlari (detection/takip.py): GERCEK iz kimligi + coast bayragi.
        # tespit_mi=False -> bu tik OLCUM yok, kutu Kalman tahmini (UI kesikli cizer).
        "track_id": det.get("track_id"),
        "track_durumu": det.get("track_durumu"),
        "tespit_mi": bool(det.get("tespit_mi", True)),
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
         "ok": poz is not None,                      # ok=False: nokta var, PnP oturmadi
         # kare zamani: /api/gorsel yas_s hesaplar -> arayuz iskeleti tespit hiziyla
         # ILERI kaydirir (poz POZ_HER_N=3 seyrekliginde kosar, bbox'tan da bayattir).
         "t_poz": float(pdet.get("t", time.perf_counter()))}
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
#  DEDEKTOR DEBUG PENCERESI (istege bagli):  set AVCI_DEBUG_PENCERE=1  ile ac.
#  Dedektorun ISLEDIGI karenin uzerine AYNI karenin tespit/poz ciktisini cizip
#  yerel bir OpenCV penceresinde gosterir -> kutu/iskelet hedefin TAM ustunde
#  (kare<->cikti %100 senkron). Arayuzde "kutu geride kaliyor" gorunumu, canli
#  ekran paylasimi (~0 ms) ile inference cikisi (~100-300 ms) arasindaki fizik
#  farkidir; bu pencere o farki SIFIRLAR (pencere butunuyle inference suresi
#  kadar geridedir ama kendi icinde gecikmesizdir). Guduma etkisi YOK (salt
#  gosterim; bayrak kapaliyken sifir maliyet). Yalniz gorev aktifken gunceller
#  (dedektor dongusu o zaman calisir).
# ----------------------------------------------------------
DEBUG_PENCERE = os.environ.get("AVCI_DEBUG_PENCERE", "0").strip() == "1"
_DEBUG_PENCERE_W = 960          # gosterim genisligi px (oran korunur)
# OLCUM MODU (maske koordinati bulmak icin): set AVCI_OLC_TESPIT=1 -> her tespitin
# normalize kutusunu (x0,y0,x1,y1) formatinda basar (dogrudan PROP_MASKE'ye yapistir).
# MASKESIZ okur ki maskelenmis HUD/pervane kutulari da gorunsun. Kapaliyken sifir maliyet.
OLC_TESPIT = os.environ.get("AVCI_OLC_TESPIT", "0").strip() == "1"


def _debug_pencere_goster(bgr, det, det_gecti, poz):
    """dedektor_dongusu icinden cagrilir (ayni thread; imshow tek thread'de kalmali).
    det: gorsel_tespit ciktisi (PIKSEL cx/cy/w/h) | None. poz: normalize kp'li dict | None."""
    h, w = bgr.shape[:2]
    s = _DEBUG_PENCERE_W / float(w)
    hd = int(h * s)
    img = cv2.resize(bgr, (_DEBUG_PENCERE_W, hd))
    for m in (getattr(Cfg, "PROP_MASKE", None) or []):       # pervane maskesi (koyu kirmizi)
        cv2.rectangle(img, (int(m[0] * _DEBUG_PENCERE_W), int(m[1] * hd)),
                      (int(m[2] * _DEBUG_PENCERE_W), int(m[3] * hd)), (0, 0, 180), 1)
    if det is not None:
        renk = (0, 220, 0) if det_gecti else (0, 165, 255)   # yesil=gudume gitti, turuncu=zayif(UI-only)
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
#  DEDEKTOR PERFORMANS OLCUMU (2026-07-08): "modelden tam performans aliyor muyuz?"
#  sorusunu VERIYLE cevaplamak icin. Canli dongude her inference'in GERCEK suresi
#  (torch.cuda.synchronize ile async-kernel bitene kadar beklenir -> dogru latency)
#  olculur; son ~120 orneğin ort/p95'i + dongu FPS'i telemetriye (gorsel.perf) ve
#  periyodik konsola yazilir. Gudume DOKUNMAZ (salt gozlem). TensorRT/FP16 karari
#  bu sayilara gore: DET_ms yuksek + FPS dusukse export mantikli; recall sorunuysa
#  export cozmez (egitim isi).
# ----------------------------------------------------------
_perf = {"det_ms": None, "det_p95": None, "poz_ms": None, "fps": None, "gpu": None,
         # KROP olcumu (2026-08-17): mekanizma kapisi -- AVCI_KROP=1 deneyinde
         # krop_oran 0 ise krop hic devreye girmemistir, deney GECERSIZ.
         "krop": 0, "krop_oran": 0.0}
from detection import krop as _krop   # dedektore 1:1 pencere (bkz. detection/krop.py)

_perf_det = deque(maxlen=120)     # best.pt inference ms
_perf_poz = deque(maxlen=60)      # pose inference ms (seyrek kosar)
_perf_dongu = deque(maxlen=120)   # dongu periyodu (s) -> FPS
# KALICI PERF LOGU: ~1 Hz veri/perf_log_*.csv (uctan sonra Claude buradan analiz eder;
# konsol/FPV anlik, bu kalici). Her gorev basinda yeni dosya.
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
    """GPU async kernel'i bitene kadar bekle -> olculen sure GERCEK latency olsun."""
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
    from detection.gorsel_tespit import HedefDedektor   # import-guard modul icinde (ultralytics opsiyonel)
    from detection.poz_tespit import PozDedektor        # ayni desen (hazir=False zarif bozulma)
    from detection.takip import Takipci                  # HybridSort adaptoru: ID surekliligi + FP filtresi
    from detection import kamera_model                   # gyro-CMC homografisi (kendi donusumuz telafi)
    # boxmot kurulu degilse Takipci() ModuleNotFoundError firlatir; guard olmadan TUM
    # dedektor thread'i gorev baslamadan olur (0 tespit, sessiz). Kurulamazsa None ->
    # asagidaki ham argmax yolu (TAKIP_AKTIF=False davranisi) devreye girer.
    takipci = None
    if bool(getattr(Cfg, "TAKIP_AKTIF", True)):
        try:
            takipci = Takipci()                          # zamansal takip (guduma dokunmaz; secim katmani)
        except Exception as e:
            print("[TAKIP] Takipci kurulamadi (%s) -> tracker DEVRE DISI, ham argmax tespit." % e)
    onceki_att = None                                    # onceki tur drone rotasyonu (CMC icin)
    onceki_takip_t = None                                # onceki takip guncelleme ani (Kalman dt)
    poz_sayac = 0                                        # POZ_HER_N seyreklestirme sayaci
    onceki_ui = None                                     # (cx, cy, t, track_id) — UI bbox hiz kestirimi icin
    _t_dongu = None                                      # onceki dongu damgasi (FPS)
    _t_konsol = 0.0                                      # son konsol ozeti zamani
    while True:
        # Sadece OTONOM gorev sirasinda tespit yap (manuel/pasifken bosuna donme).
        if not (drone.is_connected() and gorev_aktif and not manuel_aktif):
            if takipci is not None and takipci.trackler:  # yeni gorev bayat track/ID ile baslamasin
                takipci.sifirla()
            onceki_att = onceki_takip_t = None
            time.sleep(0.05)
            continue
        if dedektor is None:                          # LAZY: ilk gorev tikinde yukle
            # Model + imgsz artik MODEL_YOL/MODEL_IMGSZ'den (env ile degistirilebilir;
            # verilmezse modelin KENDI egitim imgsz'i). best.pt 640 egitimli -> 640, yani
            # varsayilan davranis DEGISMEDI. SAHI (Cfg.SAHI_*): SADECE detect modeline
            # (uzak/kucuk hedef recall); AVCI_SAHI=0 ile kapatilabilir.
            _sahi = bool(getattr(Cfg, "SAHI_AKTIF", False)) if SAHI_ZORLA is None else SAHI_ZORLA
            dedektor = HedefDedektor(MODEL_YOL, conf=Cfg.VIS_CONF_MIN,
                                     imgsz=MODEL_IMGSZ, half=FP16_AKTIF,
                                     sahi=_sahi,
                                     sahi_dilim=getattr(Cfg, "SAHI_DILIM_PX", 640),
                                     sahi_ortusme=getattr(Cfg, "SAHI_ORTUSME", 0.2),
                                     sahi_tam_kare=getattr(Cfg, "SAHI_TAM_KARE", True),
                                     sahi_nms_iou=getattr(Cfg, "SAHI_NMS_IOU", 0.5),
                                     sahi_kosul_conf=getattr(Cfg, "SAHI_KOSUL_CONF", 0.5))
            if dedektor.hazir:
                print("[GORSEL] MODEL: %s  (imgsz=%d, device=%s, half=%s, sahi=%s). Siniflar: %s"
                      % (os.path.basename(MODEL_YOL), MODEL_IMGSZ, dedektor.device,
                         dedektor.half, dedektor.sahi, dedektor.names))
            else:
                print("[GORSEL] Dedektor YUKLENEMEDI (%s) -> sistem GPS ile devam eder."
                      % dedektor.hata)
            # POZ modeli (ILAVE gozlemci) — best.pt ile AYNI anda, bir kez denenir.
            # POSE_AKTIF=False -> pose sistemden TAMAMEN cikarildi (sadece detection).
            if not POSE_AKTIF:
                print("[POZ] KAPALI (POSE_AKTIF=False) -> yalnizca detection (bbox). GPU bbox'a kalir.")
            elif os.path.exists(POSE_MODEL_PATH):
                # conf=0.35: 0.20'de eski model bos gokyuzune "talon" diyordu (canli
                # test, 4 Tem) -> overlay'e cop iskelet ciziliyordu; canlida yanlis-alarm
                # maliyeti yuksek. imgsz=960: pose modeli 960'ta EGITILDI (POSE_REHBERI);
                # 1280'de kosmak hem yavas (~180ms) hem egitim-uyumsuz. 960 ~%40 hizli +
                # egitimle tutarli. half=FP16 ~2x. Tespit% kotulesirse imgsz=1280 geri.
                poz_dedektor = PozDedektor(POSE_MODEL_PATH, conf=0.35, imgsz=960,
                                           half=FP16_AKTIF)
                if poz_dedektor.hazir:
                    try:
                        from pose.poz_cozucu import PozCozucu, EGITIM_SIRASI
                        poz_cozucu = PozCozucu(conf_esik=0.5, ema_alpha=0.4)
                        _poz_sira = list(EGITIM_SIRASI)
                        print("[POZ] talon_pose.pt yuklendi (device=%s, half=%s, imgsz=%d) -> PnP poz "
                              "kestirimi AKTIF (gozlemci; gudume girmez)."
                              % (poz_dedektor.device, poz_dedektor.half, poz_dedektor.imgsz))
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
        try:
            # Predict esigi UI icin dusuk (UI_CONF_MIN): zayif tespitler arayuzde
            # turuncu cizilir. GUDUM yine yalnizca conf>=VIS_CONF_MIN gorur
            # (asagida det_beyin kapisi) -> beyin/kilit davranisi DEGISMEZ.
            # BYTE ikinci turu icin taban CONF_DUSUK: dusuk-conf kutu YENI track
            # ACAMAZ ama mevcut izi yasatir (zayif karede ID kopmaz). Tracker kapaliysa
            # (TAKIP_AKTIF=False) eski esik davranisi (dusuk-conf kutulara gerek yok).
            # Slider VIS_CONF_MIN'i daha da dusururse predict onu izler (canli-tune).
            takip_aktif = bool(getattr(Cfg, "TAKIP_AKTIF", True)) and takipci is not None
            if takip_aktif:
                dedektor.conf = min(UI_CONF_MIN, float(Cfg.VIS_CONF_MIN), takipci.cfg.CONF_DUSUK)
            else:
                dedektor.conf = min(UI_CONF_MIN, float(Cfg.VIS_CONF_MIN))
            bgr, _fw, _fh = grab_frame_bgr()          # AGIR is: pencere karesi al (kilit DISINDA)
            # ultralytics ndarray'i BGR varsayar -> grab_frame_bgr ciktisi DOGRU renk.
            # PERVANE MASKESI canli okunur (Cfg.PROP_MASKE) -> kendi pervanemiz elenir
            # (argmax degil TUM kutular: maskeli kutu takipciye hic girmez).
            # OLCUM: best.pt inference GERCEK suresi (synchronize sonrasi).
            # ── KROP: dedektore hedefin etrafindan 1:1 pencere ver ────────
            # Motor statik 960x960; tam kare verilince hedef YARI boyutta
            # gorunur ve girdinin %44'u gri bant olur. Krop ikisini de kaldirir.
            # ⚠ Maske TAM KARE koordinatinda tanimli -> krop varken maskeyi
            # UYGULAMA (yanlis yere denk gelir); tam karede eskisi gibi calisir.
            _kr_img, _kx0, _ky0 = _krop.hazirla(bgr)
            _t_inf = time.perf_counter()
            dets = (dedektor.tespit_hepsi(
                        _kr_img,
                        maske=(None if (_kx0 or _ky0)
                               else getattr(Cfg, "PROP_MASKE", None)))
                    if bgr is not None else [])
            if bgr is not None:
                _cuda_senkron()
                _perf_det.append((time.perf_counter() - _t_inf) * 1000.0)
            # ── KROP -> TAM KARE koordinatina geri cevir ───────────────────
            # Bundan sonrasi hicbir sey fark etmez: tespit_akisi ve yasa hep
            # tam-kare pikseli gorur.
            if (_kx0 or _ky0) and dets:
                for _d in dets:
                    _d["cx"] += _kx0
                    _d["cy"] += _ky0
            if dets:
                _krop.tespit_bildir(dets[0]["cx"], dets[0]["cy"])
            # OLCUM MODU: maskesiz TUM kutulari normalize (x0,y0,x1,y1) bas -> mask koordinati.
            if OLC_TESPIT and bgr is not None:
                _oh, _ow = bgr.shape[:2]
                for _d in dedektor.tespit_hepsi(bgr, maske=None):
                    _x0 = (_d["cx"] - _d["w"] / 2) / _ow; _y0 = (_d["cy"] - _d["h"] / 2) / _oh
                    _x1 = (_d["cx"] + _d["w"] / 2) / _ow; _y1 = (_d["cy"] + _d["h"] / 2) / _oh
                    print("[OLC] kutu=(%.3f, %.3f, %.3f, %.3f) conf=%.2f"
                          % (_x0, _y0, _x1, _y1, _d["conf"]))
        except Exception:
            bgr, dets = None, []
        # BYTETRACK + GYRO-CMC: kutulari ZAMANSAL bagla — tek-kare parazit CONFIRMED
        # olamadan olur, kisa tespit deliginde iz coast'la surer (tespit_mi=False),
        # kendi donusumuzun kutu kaydirmasi homografiyle telafi edilir (hizli yaw'da
        # ID kopmaz). det = en iyi CONFIRMED track | None (sozlesme argmax'la uyumlu).
        # TAKIP_AKTIF=False -> tracker atlanir, ham argmax (dets[0]) dogrudan gecer
        # (ByteTrack oncesi davranis; canli sorunda hizli geri-donus anahtari).
        det = None
        if bgr is not None and not takip_aktif:
            if takipci is not None and takipci.trackler:
                takipci.sifirla()                     # kapaliyken bayat iz birikmesin
            det = dets[0] if dets else None           # tespit_hepsi conf-azalan -> [0] = argmax
        elif bgr is not None:
            simdi = time.perf_counter()
            H_cmc = None
            cmc_cap = None
            try:
                att = drone.get_drone_rotation()      # (roll,pitch,yaw) derece
                # gyro-CMC: kendi donusumuzun kutu kaymasini ONCEDEN telafi et.
                # ISARET: sim attitude konvansiyonu dogrulanmadi (Blokor B) -> TAKIP_CMC_SIGN
                # ile canli cevrilebilir (-1: att sirasi takas -> warp yonu ters). EMNIYET:
                # TAKIP_CMC_MAX_KAYDIRMA orani px tavana cevrilir (yanlis-isaret + buyuk yaw
                # kutuyu ekrandan firlatmasin; asilirsa o track o tik CMC'siz predict eder).
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
            # HybridSort kareyi ISTER (frame=bgr); dt/H_cmc/cmc_cap adaptorde yok sayilir.
            det = takipci.guncelle(dets, dt_takip, H_cmc, cmc_cap, frame=bgr)
            if det is not None:
                det.setdefault("t", simdi)            # coast ciktisi: tahmin ani = simdi
        # GUDUM KAPISI: zayif (yalnizca-UI) tespit beyne GITMEZ -> kilit sayaci,
        # takip rozeti, gorsel guduum eski predict-esigi davranisiyla BIREBIR ayni.
        # Coast (tespit_mi=False) da beyne GITMEZ: gorsel fazin kendi koprusu
        # (ana_kontrol olu-hesap) delikleri yonetir; cift olu-hesap olmasin.
        det_beyin = (det if det is not None and det.get("tespit_mi", True)
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
                and det is not None and det.get("tespit_mi", True)   # coast karesinde poz kosma
                # ⚠ YAKINLIK KAPISI: poz terminal aracidir (bkz. POZ_MIN_KUTU_PX)
                and max(float(det.get("w", 0.0)) * (bgr.shape[1] if bgr is not None else 0),
                        float(det.get("h", 0.0)) * (bgr.shape[0] if bgr is not None else 0)
                        ) >= POZ_MIN_KUTU_PX
                and poz_sayac % POZ_HER_N == 0):
            poz_kostu = True
            try:
                _t_poz = time.perf_counter()
                if POZ_KROP_AKTIF:
                    # 256x96 top-down yol: dedektor kutusundan 1.5x payla kes.
                    # TAM KARE (bgr) verilir -- _kr_img zaten kirpilmis olabilir ve
                    # ust uste iki kirpma koordinati bozardi. Donen keypoint'ler
                    # TAM KARE pikselindedir, asagidaki kaydirma UYGULANMAZ.
                    pdet = poz_dedektor.tespit_krop(bgr, det)
                else:
                    # ⚠ AYNI KROP: poz motoru da 960x960 -> krop ona BIREBIR oturur
                    pdet = poz_dedektor.tespit_et(_kr_img)
                _cuda_senkron()
                _perf_poz.append((time.perf_counter() - _t_poz) * 1000.0)
                # keypoint'leri TAM KARE koordinatina cevir; W/H tam kare kalsin
                if pdet is not None and not POZ_KROP_AKTIF and (_kx0 or _ky0):
                    try:
                        for _k in pdet["kp_xy"]:
                            _k[0] += _kx0
                            _k[1] += _ky0
                        pdet["W"], pdet["H"] = bgr.shape[1], bgr.shape[0]
                    except (KeyError, TypeError, IndexError):
                        pass
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
        # UI tespiti + NORMALIZE HIZ (vx,vy [1/s]): arayuz bbox'u tespit YASI kadar
        # ILERI cizer (inference + aktarim gecikmesi telafisi; /api/gorsel tasir).
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
        with beyin_lock:                              # sonucu ANLIK yaz (kilit ICINDE)
            beyin.set_gorsel_tespit(det_beyin)
            # ── HIBRIT: Kayran'in gorsel yasasina TESPIT AKISI ──
            # Her KAREDE bir kez yazilir; det_beyin None ise de yazilir cunku
            # yasa "kutusuz kare"yi KAYIP_M sayacina katmak zorunda -- yutulursa
            # gorsel temas kesildigi HIC anlasilmaz ve faz sonsuza kadar surer.
            # Kopru kapaliysa (KOPRU_HIBRIT=False) `tespit` None -> sifir maliyet.
            _kg = getattr(beyin, "kopru_gudum", None)
            if _kg is not None and getattr(_kg, "tespit", None) is not None:
                _kg.tespit.yaz(det_beyin)
            if poz_kostu and poz_ui is not None:      # TAZE poz -> beyne (ongorulu yaw lead besler)
                beyin.set_gorsel_poz(poz_ui)          # GORSEL veri (kameradan keypoint); GPS/J DEGIL
            _son_tespit_ui = ui_det
            if poz_kostu or det is None:              # ara turlarda SON pozu tut (iskelet
                _son_poz_ui = poz_ui                  # yanip sonmesin); hedef yoksa temizle
        # DEBUG PENCERESI: islenen karenin uzerine AYNI karenin ciktisi (senkron gosterim).
        if DEBUG_PENCERE and cv2 is not None and bgr is not None:
            try:
                _debug_pencere_goster(bgr, det, det_beyin is not None,
                                      poz_ui if poz_ui is not None else _son_poz_ui)
            except Exception:
                pass                                  # gosterim hatasi dedektoru ASLA durdurmaz
        # OLCUM: dongu periyodu -> FPS (yalniz kare islenen turlar; bekleme turlari haric)
        if bgr is not None:
            _now = time.perf_counter()
            if _t_dongu is not None:
                dp = _now - _t_dongu
                if 0.0 < dp < 1.0:
                    _perf_dongu.append(dp)
            _t_dongu = _now
            # global ozeti tazele (telemetri build_telemetry'de okur)
            _perf["det_ms"], _perf["det_p95"] = _perf_ozet(_perf_det)
            _perf["poz_ms"], _ = _perf_ozet(_perf_poz)
            _perf["fps"] = (round(len(_perf_dongu) / sum(_perf_dongu), 1)
                            if _perf_dongu and sum(_perf_dongu) > 0 else None)
            # KROP MEKANIZMA KAPISI (2026-08-17): AVCI_KROP=1 ile kosulan bir
            # deneyde `krop_oran` 0 kalirsa krop FIILEN CALISMAMISTIR (hedef hic
            # taze tespit edilmemis, hep tam kareye dusulmus) -> o kosunun A/B
            # sonucu GECERSIZDIR. Salt gozlem; guduume girmez.
            try:
                _kd = _krop.durum()
                _perf["krop"] = 1 if _kd.get("aktif") else 0
                _perf["krop_oran"] = round(float(_kd.get("krop_oran") or 0.0), 3)
            except Exception:
                pass
            if _perf["gpu"] is None:
                try:
                    import torch
                    _perf["gpu"] = (torch.cuda.get_device_name(0)
                                    if torch.cuda.is_available() else "CPU")
                except Exception:
                    _perf["gpu"] = "?"
            # periyodik konsol ozeti + KALICI CSV (her ~1 sn; uctan sonra analiz)
            if _now - _t_konsol > 1.0:
                _t_konsol = _now
                _perf_log_yaz(_perf["det_ms"], _perf["det_p95"], _perf["poz_ms"],
                              _perf["fps"], _perf["gpu"])
        else:
            time.sleep(0.05)                          # oyun karesi henuz yok -> CPU'yu bosalt
        # kare varsa inference kendi hizinda pace'lenir (GPU ~30-60 FPS); ekstra sleep YOK


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
        # (2026-08-11) beyin._vis_pos_count/_vis_lost_count SILINDI (eski gorsel
        # FSM). Karsiligi supervisor'in kendi sayaci: 15 karelik pencerede
        # gecerli tespit sayisi. Kayip sayaci yasada ic durumdur -> 0 verilir.
        _hb = _hibrit_bilgi(beyin) or {}
        vis_pos = int(_hb.get("kilit_sayac") or 0)
        vis_lost = 0
        vis_mode = getattr(beyin, "vis_mode", "OTO")   # guduum pipeline switch
        # ESKI IBVS telemetrisi SILINDI (2026-08-11): gorsel guduum artik
        # bbox_ibvs'te ve onun Python status sozlugu YOK (yalniz CSV log).
        # Alan bos birakiliyor -> index.html nisan/bank overlay'i cizmez.
        ibvs_tlm = {}
        # KILITLENME ISTERI sayaci (sartname 6.1.2/6.1.4) — anlik kopya
        _kd = _kilit_durum(beyin)
        b_kilit = {"anlik": bool(_kd.get("anlik", False)),
                   "sure": round(float(_kd.get("sure", 0.0)), 2),
                   "gerek": float(getattr(Cfg, "VIS_WIN_NEED_S", 5.0)),
                   "pencere": float(getattr(Cfg, "VIS_WIN_S", 10.0)),
                   "ok": bool(_kd.get("ok", False)),
                   "esik_pct": float(getattr(Cfg, "VIS_LOCK_PCT", 0.06)),
                   "boyut_pct": _kd.get("boyut_pct")}
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
        "law": "IBVS",                              # tek gorsel yasa: basit IBVS (merkez->bbox cizgisi)
        "ibvs": ibvs_tlm,                           # {law,ex,ey,buyukluk,aci_deg,kisma,dikey,ileri,yaw} | {}
    }
    # HIBRIT FAZ (Kayran supervisor'u) — SALT GOZLEM. Kopru kapaliysa hibrit:False.
    # `akis` alani tespit akisinin GERCEK hizini tasir: yasanin kare-sayisi
    # esikleri (kilit 15 kare / kayip 20 kare) o hizda kac SANIYE ediyor, orada
    # gorunur. 30 Hz varsayimi bizde tutmuyor; etkisi gizlenmesin.
    try:
        _dg = getattr(beyin, "dow_gudum", None)
        gudum_info["hibrit"] = _dg.faz_ozet() if _dg is not None else {"hibrit": False}
    except Exception:
        gudum_info["hibrit"] = {"hibrit": False}
    kayip_s = 0.0
    if takip_s.get("id") is not None and (not takip_s.get("aktif")) and takip_s.get("kayip_t"):
        kayip_s = _now - takip_s["kayip_t"]
    takip_info = {
        "id": takip_s.get("id"), "aktif": bool(takip_s.get("aktif")),
        "kayip_s": kayip_s, "yeniden": int(takip_s.get("yeniden", 0)),
        "pos_count": vis_pos, "n_lock": 10,
    }
    gorev_info = {
        "faz": gorev_s.get("faz", "HAZIR"), "vurus": bool(gorev_s.get("vurus")),
        "basari": bool(gorev_s.get("basari")), "en_yakin_m": gorev_s.get("en_yakin_m"),
        "mesafe_kaynak": gorev_s.get("mesafe_kaynak"), "vurus_t": gorev_s.get("vurus_t"),
        "t0": gorev_s.get("t0"), "esik_m": VURUS_ESIK_M,
    }
    # ── KOPRU TANISI: KOMUT -> TEPKI zinciri (2026-08-17) ────────────────
    # Kullanicinin istegi: "verilen komutu, o anki tepkiyi ve NEDENINI de logla".
    # Kopru zaten her tikte son_tani sozlugunu doldurup CSV'ye yaziyordu ama
    # TELEMETRIDE YOKTU -> kare kaydiyla ayni anda okunamiyordu.
    # ⚠ Salt okuma, kopya: kopru dict'ine dokunulmaz.
    # ⚠ Neden onemli: kendi yaptigim degisikligin GERCEKTEN uygulanip
    #   uygulanmadigini buradan dogrulayabiliyorum (ornegin sp_vz komutu
    #   dikey kapanma sonrasi degisti mi).
    kopru_tani = None
    try:
        _dg2 = getattr(beyin, "dow_gudum", None)
        _st = getattr(_dg2, "tani", None) if _dg2 is not None else None
        if isinstance(_st, dict) and _st:
            _al = ("faz", "menzil_m", "en_yakin_m", "agl_m",
                   "sp_vx", "sp_vy", "sp_vz_ned", "sp_yaw_rate",
                   "v_own", "vz_own", "roll", "pitch", "yaw",
                   "thr", "pitch_stick", "roll_stick", "yaw_stick",
                   "cev_ileri_hata", "cev_sag_hata", "cev_a_ileri", "cev_a_sag",
                   "cev_vz_yukari", "cev_doyum",
                   "ibvs_menzil_m", "ibvs_azimut", "ibvs_yukselis",
                   "ibvs_e_cy", "ibvs_cy_ref", "ibvs_v", "ibvs_vz_yukari",
                   "ibvs_yaw_rate", "ist_hata_m", "hedef_hiz",
                   "kutu_var", "kutu_gecerli", "red_sebep", "kutu_yas_s",
                   "kilit", "kayip", "devir")
            kopru_tani = {k: _st.get(k) for k in _al if k in _st}
    except Exception:
        kopru_tani = None

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
        "gps_kesildi": (j_durum == "GORSEL_GUDUM"),
        "pos_count": vis_pos, "lost_count": vis_lost, "n_lock": 10,
        "dedektor_hazir": bool(dedektor is not None and getattr(dedektor, "hazir", False)),
        "kare_kaynak": _fpv_kaynak.get("ad"),      # dedektorun gordugu kaynak (windows-capture / mss)
        "conf_esik": float(Cfg.VIS_CONF_MIN),      # gudum/kilit esigi (alti = zayif, UI turuncu cizer)
        "kopru": bool(getattr(beyin, "vis_kopru", False)),  # olu-hesap koprusu aktif mi (FPV rozeti)
        "perf": dict(_perf),                       # dedektor performansi (det_ms/p95, poz_ms, fps, gpu)
        "kopru_tani": kopru_tani,                  # KOMUT -> TEPKI zinciri (bkz. yukarisi)
        "tespit": vis_tespit,                      # None | {ex,ey,cx,cy,w,h,conf,cls,sinif,id} (normalize)
        "kilit": b_kilit,                          # {anlik,sure,gerek,pencere,ok,esik_pct,boyut_pct}
        # PERVANE MASKESI (yanlis-poz engelleme): UI kirmizi tarama ile cizer (kullanici dogrular)
        "prop_maske": [list(r) for r in (getattr(Cfg, "PROP_MASKE", None) or [])],
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
                poz = dict(_son_poz_ui) if _son_poz_ui is not None else None
            if det is not None and "t_det" in det:
                det["yas_s"] = round(max(0.0, time.perf_counter() - det.pop("t_det")), 3)
            if det is not None and det.get("id") is None:
                det["id"] = det.get("track_id")       # hizli kanal ID etiketi (ByteTrack)
            if poz is not None and "t_poz" in poz:
                # iskelet yas telafisi: poz seyrek (POZ_HER_N) -> bbox'tan da bayat;
                # istemci kp'leri bbox hiziyla yas kadar ILERI kaydirir.
                poz["yas_s"] = round(max(0.0, time.perf_counter() - poz.pop("t_poz")), 3)
            self._send(200, json.dumps({"tespit": det, "poz": poz}).encode("utf-8"),
                       "application/json")
        elif self.path == "/api/tune":
            # Mevcut tune parametre degerlerini dondur (slider'lari baslatmak icin).
            vals = {k: getattr(Cfg, k) for k in TUNE_ALLOW}
            self._send(200, json.dumps(vals).encode("utf-8"), "application/json")
        elif self.path == "/api/gudum_ozellikleri":
            # GORSEL/HIBRIT yasa anahtarlari (bbox_ibvs.Cfg + supervisor.SupCfg).
            # Liste kopru/gorsel_ozellikler.py'den gelir; arayuz onu render eder
            # -> yeni ozellik eklerken HTML/JS'e DOKUNULMAZ (kaynak CLAUDE.md §5).
            try:
                from kopru import gorsel_ozellikler as goz
                self._send(200, json.dumps({"ok": True, "liste": goz.hepsi()}).encode("utf-8"),
                           "application/json")
            except Exception as e:
                self._send(200, json.dumps({"ok": False, "hata": repr(e), "liste": []})
                           .encode("utf-8"), "application/json")
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
            if cmd in ("start", "start_v2", "start_gercek"):
                kaynak = {"start": "v2", "start_v2": "v2", "start_gercek": "gercek"}[cmd]
                with beyin_lock:
                    beyin.set_kaynak(kaynak)  # guduum kaynagini ayarla (v2 / gercek)
                    # set_kaynak koprutu YIKIP yeniden kuruyor -> SupCfg sifirlanir.
                    # Arayuzun sectigi zorla modu burada TEKRAR yaziyoruz.
                    _zorla_mod_uygula()
                    beyin.log_dondur()        # KOSULSUZ yeni ucus logu: ayni kaynak
                    # ust uste secilse de her "Gorev Baslat" = ayri ucus dosyasi/klasoru
                    _gorev_sifirla("YAKLASMA")   # izleyici latch'lerini sifirla (basari banner dahil)
                # yeni gorev -> yeni perf logu (ucusla ayni ritim; kapat, sonraki tik acar)
                if _perf_log_f is not None:
                    try: _perf_log_f.close()
                    except Exception: pass
                    _perf_log_f = None
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
                # ── 2026-08-14: MODU GERCEKTEN UYGULA ───────────────────────
                # beyin.set_vis_mode() yalnizca arayuz icin deger SAKLIYOR
                # (kendi docstring'i: "HIBRITTE ETKISIZ ... guduume GIRMEZ").
                # Fazi belirleyen supervisor -> zorlamayi ORAYA yaziyoruz.
                # Istek her halukarda saklanir: arayuz vismode'u gorevden ONCE
                # gonderiyor ve o an kopru henuz kurulmamis olabiliyor. Gorev
                # baslarken _zorla_mod_uygula() bunu tekrar yaziyor.
                globals()["_zorla_mod_istek"] = None if m == "OTO" else m
                _sup_ok = _zorla_mod_uygula()
                _aciklama = {"OTO": "otomatik (kilit/geri-donus)",
                             "GPS": "ZORLA GPS (gorsel kapali)",
                             "GORSEL": "ZORLA GORSEL (GPS kapali)"}.get(m, "")
                if not _sup_ok:
                    _aciklama += "  [UYARI: supervisor'a yazilamadi -- kopru henuz kurulmadi]"
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
        elif self.path == "/api/gudum_ozellikleri":
            # CANLI OZELLIK AC/KAPA: {anahtar, deger}. bbox_ibvs.Cfg / SupCfg
            # sinif nitelikleri her karede okundugundan bir sonraki kareden
            # itibaren gecerli — yeniden baslatma YOK.
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length).decode("utf-8") if length else "{}"
            try:
                data = json.loads(raw)
            except Exception:
                data = {}
            try:
                from kopru import gorsel_ozellikler as goz
                yeni, hata = goz.ayarla(data.get("anahtar", ""), data.get("deger"))
            except Exception as e:
                yeni, hata = None, repr(e)
            if hata is None:
                # Olay gunlugune yaz: hangi ozelligin NE ZAMAN degistigi ucus
                # kaydinda gorunsun (A/B kiyasinda segment siniri budur).
                olay_ekle("bilgi", "OZELLIK: %s = %s" % (data.get("anahtar"), yeni))
            self._send(200, json.dumps({"ok": hata is None, "hata": hata,
                                        "anahtar": data.get("anahtar"), "deger": yeni})
                       .encode("utf-8"), "application/json")
        elif self.path == "/api/tune_rapor":
            # "DEGERLERI YAZDIR" RAPORU: canli tune degerleri + bu ucusun gorsel-faz
            # performans metrikleri (ilk tespit / kilit / takip surekliligi / merkezleme /
            # hareket tutarliligi / yaklasma) -> veri/tune_rapor_*.xlsx (web/tune_rapor.py).
            # Metrik kaynagi: beynin yazdigi AKTIF ucus logu (yoksa en yeni ucus_log_*.csv).
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
                # UCUS KLASORU: veri/tune_parametreler/ucus_N -> bu ucusun TUM
                # verileri tek yerde (log kopyalari + raporlar; kiyas kolay).
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
    # Tune logu (1 Hz): slider degerlerini saniye bazinda kaydet -> raporda
    # parametre-degisim segmentleri ucus performansiyla kiyaslanir.
    threading.Thread(target=tune_log_dongusu, daemon=True).start()

    # Negatif veri kaydi (Hat C) — YALNIZ AVCI_NEG_KAYIT verilmisse.
    if NEG_KAYIT_DIR:
        threading.Thread(target=neg_kayit_dongusu, daemon=True).start()
    # Pozitif yakalama (elle bbox) — YALNIZ AVCI_KAYIT verilmisse.
    if KAYIT_DIR:
        threading.Thread(target=pozitif_kayit_dongusu, daemon=True).start()

    # HEDEF IZ KAYDI (~50 Hz, truth GPS + gercek surat) — hedefin desenini ve
    # hizini olcmek icin. Oyun TEK baglanti kabul ettigi icin ayri bir betik
    # ayni anda kayit ALAMAZ; bu yuzden AYNI baglantidan burada akiyor.
    # Kapatmak icin: set AVCI_IZ_KAPALI=1
    try:
        from arac import hedef_iz_kaydi
        hedef_iz_kaydi.baslat(drone, os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))))
    except Exception as _ize:
        print("[IZ] !! hedef iz kaydi baslatilamadi: %r" % (_ize,))

    # CIFT ORNEK KAPISI: Windows'ta HTTPServer.allow_reuse_address=1 oldugundan ikinci
    # bir sunucu AYNI porta SESSIZCE baglanabiliyor. Iki ornek de oyunun TCP'sine
    # baglanmaya calisir -> soketi birbirinden koparirlar (is_connected() yanip soner,
    # kopru hic calismaz) ve tarayicinin hangisinden cevap aldigi belirsizdir. Bu tuzak
    # canlida iki kez yasandi; artik bind'dan ONCE porta baglanmayi deneyip gurultuyle
    # reddediyoruz (sessiz bozulma yerine acik hata).
    _yoklama = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _yoklama.settimeout(0.3)
    _mesgul = (_yoklama.connect_ex(("127.0.0.1", WEB_PORT)) == 0)
    _yoklama.close()
    if _mesgul:
        print("=" * 52)
        print("  [HATA] %d portunda ZATEN bir arayuz calisiyor." % WEB_PORT)
        print("  Ikinci ornek BASLATILMADI (iki sunucu oyun baglantisini koparir).")
        print("  Once calisani kapat (o pencerede Ctrl+C), sonra tekrar baslat.")
        print("=" * 52)
        return
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

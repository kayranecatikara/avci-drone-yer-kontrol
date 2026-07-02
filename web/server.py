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
try:
    from detection.pencere_yakala import PencereYakala
    pencere_yakala_motoru = PencereYakala(title_hints=GAME_TITLE_HINTS)
except Exception as _py_e:
    pencere_yakala_motoru = None
    print("[SERVER] pencere_yakala yuklenemedi (%s) -> mss fallback." % _py_e)


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
      1) windows-capture canli karesi (occlusion-proof; oyun arkada olsa bile dogru)
      2) mss oyun-penceresi bolgesi (oyun goruunur/onde ise)
      3) mss tum ekran (son care; ayna riski)
    Yalnizca mss de basarisizsa (None, 0, 0)."""
    pym = pencere_yakala_motoru
    if pym is not None and pym.hazir and pym.calisiyor():
        bgr = pym.get_latest_bgr()
        if bgr is not None:
            _fpv_log("windows-capture (pencere icerigi)")
            return _olcekle_bgr(bgr)
    # Fallback: mss (windows-capture yok / henuz kare uretmedi / pencere bulunamadi)
    try:
        kaynak, bgr = _mss_grab_bgr()
        _fpv_log(kaynak)
        return _olcekle_bgr(bgr)
    except Exception as e:
        _fpv_log("KARE YOK", " (%s)" % e)
        return None, 0, 0


def fpv_jpeg():
    """/api/frame'in dondurdugu HAM oyun karesi (overlay YOK — bbox/rozet istemci
    canvas'inda cizilir). grab_frame_bgr fallback zincirini kullanir -> gorunur bir
    oyun/ekran varsa HER ZAMAN kare doner. Hicbir kaynak yoksa None (-> 503)."""
    bgr, _w, _h = grab_frame_bgr()
    if bgr is None:
        return None
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
    # dikey (irtifa) PID
    "KP_Z", "KI_Z", "KD_Z", "THR_UP", "THR_DN",
    # GORSEL GUDUM (IBVS): isaret/kazanc/kapi + kilit guveni (SIM'de canli kalibrasyon)
    "VIS_SIGN_YAW", "VIS_SIGN_VZ", "VIS_SIGN_PITCH",
    "VIS_K_YAW", "VIS_K_VZ", "VIS_K_FWD", "VIS_FWD_MAX",
    "VIS_CENTER_GATE", "VIS_AREA_STOP", "VIS_EMA", "VIS_CONF_MIN",
    "VIS_EY_REF",   # kamera 25 derece tilt telafisi (dikey referans; sim'de kalibre)
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


def _kiyas_guncelle():
    """Her YENI ham pakette Inovasyonlu J'yi besle, gercege hatasini olc."""
    global _kiyas_idx, _kiyas_son_ham
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


def _normalize_tespit(det):
    """Dedektor px ciktisini overlay/telemetri icin normalize et (cozunurluk-bagimsiz)."""
    if det is None:
        return None
    W = float(det.get("W", 0) or 0); H = float(det.get("H", 0) or 0)
    if W <= 1 or H <= 1:
        return None
    return {
        "ex": (det["cx"] - W / 2.0) / (W / 2.0),   # + = hedef SAGDA
        "ey": (det["cy"] - H / 2.0) / (H / 2.0),   # + = hedef ALTTA
        "cx": det["cx"] / W, "cy": det["cy"] / H,  # normalize merkez [0..1]
        "w": det["w"] / W, "h": det["h"] / H,      # normalize bbox boyut [0..1]
        "conf": float(det.get("conf", 0.0)),
    }


def dedektor_dongusu():
    global dedektor, _son_tespit_ui
    from detection.gorsel_tespit import HedefDedektor   # import-guard modul icinde (ultralytics opsiyonel)
    while True:
        # Sadece OTONOM gorev sirasinda tespit yap (manuel/pasifken bosuna donme).
        if not (drone.is_connected() and gorev_aktif and not manuel_aktif):
            time.sleep(0.05)
            continue
        if dedektor is None:                          # LAZY: ilk gorev tikinde yukle
            dedektor = HedefDedektor(Cfg.VIS_MODEL_PATH, conf=Cfg.VIS_CONF_MIN)
            if dedektor.hazir:
                print("[GORSEL] best.pt yuklendi (device=%s). Siniflar: %s"
                      % (dedektor.device, dedektor.names))
            else:
                print("[GORSEL] Dedektor YUKLENEMEDI (%s) -> sistem GPS ile devam eder."
                      % dedektor.hata)
        if not dedektor.hazir:
            time.sleep(1.0)                           # kurulum yok -> CPU yakma
            continue
        try:
            dedektor.conf = float(Cfg.VIS_CONF_MIN)   # canli-tune: predict esigi slider'i izler
            bgr, _fw, _fh = grab_frame_bgr()          # AGIR is: pencere karesi al (kilit DISINDA)
            # ultralytics ndarray'i BGR varsayar -> grab_frame_bgr ciktisi DOGRU renk.
            det = dedektor.tespit_et(bgr) if bgr is not None else None
        except Exception:
            bgr, det = None, None
        with beyin_lock:                              # sonucu ANLIK yaz (kilit ICINDE)
            beyin.set_gorsel_tespit(det)
            _son_tespit_ui = _normalize_tespit(det)
        if bgr is None:
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
        vis_pos = beyin._vis_pos_count
        vis_lost = beyin._vis_lost_count
        vis_mode = getattr(beyin, "vis_mode", "OTO")   # guduum pipeline switch
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

    # GORSEL GUDUM durumu + son NORMALIZE tespit (overlay/rozet icin). durum
    # GORSEL_GUDUM ise GPS yonelimi MIMARI olarak kesilmistir -> index.html
    # "GPS GUDUMU: KAPALI" rozetini kirmizi yakar.
    gorsel = {
        "durum": j_durum,                          # ARAMA | GORSEL_GUDUM
        "mod": vis_mode,                           # OTO | GPS | GORSEL (manuel switch)
        "ey_ref": float(getattr(Cfg, "VIS_EY_REF", 0.0)),   # dikey referans (tilt telafisi; overlay cizer)
        "gps_kesildi": (j_durum == "GORSEL_GUDUM"),
        "pos_count": vis_pos, "lost_count": vis_lost, "n_lock": Cfg.VIS_N_LOCK,
        "dedektor_hazir": bool(dedektor is not None and getattr(dedektor, "hazir", False)),
        "tespit": vis_tespit,                      # None | {ex,ey,cx,cy,w,h,conf} (normalize)
    }

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
                gorev_aktif = True
                manuel_aktif = False          # gorev ve manuel ayni anda olmaz
                _ad = {"v2": "Inovasyonlu J", "gercek": "GERCEK GPS"}[kaynak]
                msg = "GOREV BASLATILDI - kaynak: %s%s" % (
                    _ad, " (filtre yok, gercek konuma gidiyor)" if kaynak == "gercek" else "")
            elif cmd == "stop":
                gorev_aktif = False
                manuel_aktif = False
                # Guvenlik: drone'u durdur (motorlari kes -> arm=False)
                try:
                    drone.set_control_surfaces(0.0, 0.0, 0.0, 0.0, False)
                except Exception:
                    pass
                msg = "GOREV DURDURULDU - drone pasif (motorlar kapali)"
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
        else:
            self._send(404, b"yok", "text/plain; charset=utf-8")


# ----------------------------------------------------------
#  Ana program
# ----------------------------------------------------------
def main():
    # Arka planda baglanti yoneticisini ve gorev kontrol beynini baslat
    threading.Thread(target=connection_manager, daemon=True).start()
    threading.Thread(target=kontrol_dongusu, daemon=True).start()
    # Gorsel tespit (YOLO) AYRI thread: gorev aktifken best.pt ile hedef bbox uretir.
    threading.Thread(target=dedektor_dongusu, daemon=True).start()

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

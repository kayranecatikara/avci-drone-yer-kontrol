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
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

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
            deneme = 0
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
    }
    kp = det.get("keypoints")
    if kp:                                          # normalize keypoints (overlay ciz)
        n["keypoints"] = [[float(x) / W, float(y) / H, float(c)] for x, y, c in kp]
    return n


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
    # baslangic modeli: Cfg.VIS_MODEL_PATH adi (best) varsa onu, yoksa ilk .pt
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
    while True:
        # Sadece OTONOM gorev sirasinda algi yap (manuel/pasifken bosuna donme).
        if not (drone.is_connected() and gorev_aktif and not manuel_aktif):
            time.sleep(0.05)
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
            bgr, _fw, _fh = grab_frame_bgr()          # AGIR is: pencere karesi (kilit DISINDA)
            att = drone.get_drone_rotation()          # gyro-CMC icin attitude (temiz/tam-hizli)
            cikti = algi.adim(bgr, att) if bgr is not None else None
        except Exception:
            bgr, cikti = None, None
        # AlgiCiktisi.hedef eski det sozlesmesiyle uyumlu (cx,cy,w,h,conf,W,H) ->
        # beyin.set_gorsel_tespit geriye uyumlu (FSM tracker sorgusu FAZ 3'te).
        hedef = cikti.hedef if cikti else None
        with beyin_lock:                              # sonucu ANLIK yaz (kilit ICINDE)
            beyin.set_gorsel_tespit(hedef)
            _son_tespit_ui = _normalize_tespit(hedef)
            _son_pnp_ui = (cikti.pnp if cikti else None)
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
    j_info = {"durum": j_durum, "hazir": j_temiz is not None}
    if j_temiz is not None:
        j_info["temiz"] = {"x": j_temiz[0] * CM_TO_M,
                           "y": j_temiz[1] * CM_TO_M,
                           "z": j_temiz[2] * CM_TO_M}

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
        "dedektor_hazir": bool(model_yon is not None and model_yon.hazir),
        "tespit": vis_tespit,                      # None | {ex,ey,cx,cy,w,h,conf} (normalize)
        "track": ({"id": vis_tespit.get("track_id"), "durum": vis_tespit.get("track_durumu"),
                   "tespit_mi": vis_tespit.get("tespit_mi")} if isinstance(vis_tespit, dict)
                  and vis_tespit.get("track_id") is not None else None),
        "pnp": (_pnp_ui_ozet(_son_pnp_ui)),        # None | {gecerli, mesafe, reproj_err, phi_T, psi_T}
    }
    # MODEL REGISTRY durumu + canli metrikler (arayuz paneli)
    if model_yon is not None:
        gorsel["model"] = {"durum": model_yon.durum(),
                           "liste": model_yon.modelleri_listele(),
                           "metrik": model_yon.metrikler()}

    veri = {
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
        "j": j_info,
        "gorev_aktif": gorev_aktif,
        "manuel_aktif": manuel_aktif,
        "kaynak": j_kaynak,
        "gorsel": gorsel,
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
            if cmd in ("start", "start_v2"):
                with beyin_lock:
                    beyin.set_kaynak("v2")    # tek guduum kaynagi: Inovasyonlu J
                gorev_aktif = True
                manuel_aktif = False          # gorev ve manuel ayni anda olmaz
                msg = "GOREV BASLATILDI - kaynak: Inovasyonlu J"
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

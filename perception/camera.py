# -*- coding: utf-8 -*-
"""
perception/camera.py — kare yakalama -> tespit -> takip -> detection_state.

IKI IS PARCACIGI, TEK YON:

    [URETICI]  kaynaktan kare al  ->  _latest  (yalniz EN TAZE kare durur)
    [TUKETICI] _latest'i oku      ->  YOLO -> takipci -> detection_state

Faz kapisi (control/main.py :: PhaseSupervisor) ve gorsel faz detection_state'ten
okur; donguyu web/server.py kosturur.

⭐ NEDEN AYRI THREAD (olculdu, n>=30/nokta).
   Eski surumde yakalama ve cikarim AYNI dongudeydi, yani
   toplam = yakalama + cikarim:
       mss 15.6 + BGRA->BGR 8.6 + YOLO 10.3 = 34.5 ms  ->  29.9 FPS
   Ayri thread'de toplam = max(yakalama, cikarim) olur.
   GERCEK KAMERADA fark cok daha buyuktur: cv2.VideoCapture.read() bir SONRAKI
   kareyi BEKLER (olculdu: 32.00 ms @30 fps). Senkron dongude bu sure tamamen
   OLU BEKLEMEDIR; ayri thread'de cikarimla ortusur ve kritik yoldan cikar.

⛔ BAYAT KARE (capture kartlarin klasik tuzagi).
   Surucu kuyrugunda bekleyen kare read()'te ANINDA doner (olculdu: 0.1 ms;
   gercek yeni kare bir kare periyodu bekletir). Guduum o kareyi taze sanip
   bir periyot eski goruntuyle komut uretir. Iki katmanli onlem:
     1) yapisal — uretici SUREKLI okur, kuyruk hic birikemez;
     2) acilista ve her duraklama sonrasi DeviceSource.drain() kuyrugu bosaltir.
   CAP_PROP_BUFFERSIZE=1 de denenir ama backend'ler bunu sessizce yok sayabilir
   (DSHOW'da -1 okundu) -> tek basina GUVENILMEZ, yedek degil takviyedir.

⚠ `_latest` YALNIZ SON KAREYI TUTAR. Tuketici yavassa aradaki kareler DUSER
  (status()["dropped"] sayar). Bu KASITLIDIR: guduum icin bir kare gecikmek,
  kuyruktan bayat kare tuketmekten iyidir.

Goruntu kaynagi (ortam degiskeni):
    AVCI_DEVICE=0            cv2.VideoCapture ile capture kart / USB kamera
                             (VERILMEZSE ekran yakalama = Unreal simulasyonu)
    AVCI_DEVICE_SIZE="1920,1080"   istenen cozunurluk
    AVCI_DEVICE_FPS=60             istenen kare hizi
    AVCI_DEVICE_FOURCC=MJPG        kare formati (MJPG dusuk bant, YUYV sikistirmasiz)
    AVCI_REGION="left,top,w,h"     yalniz bu dikdortgeni yakala (ekran kaynagi)
    AVCI_CAP_FPS=60                ekran kaynaginda uretici hiz siniri
    AVCI_DEBUG_WINDOW=1            dedektorun GORDUGU kareyi kutularla goster
    AVCI_FP16=0                    FP16 inference'i kapat

    OYUN PENCERESI GORUNUR OLMALIDIR (ekran kaynagi). mss EKRANI yakalar; oyun
    baska pencerenin arkasinda kalirsa dedektore masaustu pikseli gider.
    Oyunu KENARLIKSIZ PENCERE modunda ONDE tut.

Cozunurluk: kare DOGAL cozunurlukte dedektore verilir (kucultme YOK). Kareyi
once kucultup modele geri buyutturmek uzaktaki kucuk hedefin detayini oldurur.
"""
import os
import threading
import time

import numpy as np

from perception import detection_state
from perception.detector import MODEL_PATH, TargetDetector
from perception.tracking import Tracker

FP16 = os.environ.get("AVCI_FP16", "1").lower() not in ("0", "off", "false")
DEBUG_WINDOW = os.environ.get("AVCI_DEBUG_WINDOW", "0").lower() in ("1", "on", "true")

# Ekran kaynaginda ureticinin hiz siniri. Tuketiciden hizli uretmek bayatligi
# dusurur (60 Hz -> en fazla 16.7 ms eski kare) ama bir cekirdek yakar; oyunun
# da ayni makinede kostugunu unutmayin.
CAP_FPS = float(os.environ.get("AVCI_CAP_FPS", "60"))

_state = {"frames": 0, "fps": 0.0, "det_ms": 0.0, "source": None, "error": None,
          "cap_frames": 0, "cap_fps": 0.0, "age_ms": 0.0, "dropped": 0}

# --- uretici -> tuketici koprusu: YALNIZ EN TAZE KARE ---
_latest_lock = threading.Lock()
_latest = {"frame": None, "seq": 0, "t": 0.0}


def _publish_frame(frame, t):
    with _latest_lock:
        _latest["frame"] = frame
        _latest["seq"] += 1
        _latest["t"] = t


def _take_frame():
    """(kare, seq, yakalama_zamani) — tuketicinin tek atislik goruntusu."""
    with _latest_lock:
        return _latest["frame"], _latest["seq"], _latest["t"]


def _bgra_to_bgr(bgra):
    """BGRA -> BGR. cv2 varsa onu kullan: numpy dilimi 1920x1200'de 8.56 ms,
    cv2.cvtColor 1.11 ms (olculdu). Uretici maliyeti dogrudan yakalama hizini
    belirledigi icin bu fark hattin tavanina yansir."""
    try:
        import cv2
        return cv2.cvtColor(bgra, cv2.COLOR_BGRA2BGR)
    except Exception:
        return np.ascontiguousarray(bgra[:, :, :3])


# ==========================================================
#  GORUNTU KAYNAKLARI
# ==========================================================
class ScreenSource:
    """mss ile oyun EKRANINI yakalar (Unreal simulasyonu).

    read() BLOKLAMAZ: o anki ekran tamponunu okur, kare daima tazedir. Bu
    yuzden kuyruk/bayatlik sorunu YOKTUR; tek sinir uretici hiz siniridir.
    """

    def __init__(self):
        self._sct = None
        self._next_t = 0.0
        self.name = "mss"

    def _region(self):
        raw = os.environ.get("AVCI_REGION", "").strip()
        if not raw:
            return None
        try:
            l, t, w, h = [int(v) for v in raw.replace(" ", "").split(",")]
            return {"left": l, "top": t, "width": w, "height": h}
        except Exception:
            print("[KAMERA] AVCI_REGION cozulemedi (%r) -> tum ekran." % raw)
            return None

    def open(self):
        import mss
        self._sct = mss.mss()  # mss her is parcaciginda AYRI ornek ister
        bbox = self._region()
        self.name = "mss (AVCI_REGION)" if bbox else "mss (tum ekran)"

    def read(self):
        # hiz siniri: tuketiciden cok hizli uretmek bosa CPU yakar
        if CAP_FPS > 0:
            now = time.perf_counter()
            if now < self._next_t:
                time.sleep(self._next_t - now)
            self._next_t = max(time.perf_counter(), self._next_t) + 1.0 / CAP_FPS
        bbox = self._region() or self._sct.monitors[1]
        raw = self._sct.grab(bbox)
        bgra = np.frombuffer(raw.bgra, dtype=np.uint8).reshape(raw.height, raw.width, 4)
        return _bgra_to_bgr(bgra)

    def drain(self):
        return 0  # ekran tamponunda kuyruk yoktur

    def idle(self):
        time.sleep(0.05)

    def close(self):
        try:
            self._sct.close()
        except Exception:
            pass
        self._sct = None


class DeviceSource:
    """cv2.VideoCapture — capture kart (video link) veya USB kamera.

    ⛔ read() BLOKLAR: bir sonraki kareyi bekler (olculdu 32.00 ms @30 fps).
      Bu sure ureticide harcanir, tuketici bu sirada cikarim yapar.
    """

    def __init__(self, spec):
        self._cap = None
        self._spec = spec
        self.period_ms = 33.3
        self.name = "cv2 (device %s)" % spec

    def open(self):
        import cv2
        dev = int(self._spec) if str(self._spec).isdigit() else self._spec
        backends = [("DSHOW", getattr(cv2, "CAP_DSHOW", 0))] if os.name == "nt" else []
        backends.append(("ANY", getattr(cv2, "CAP_ANY", 0)))
        cap = None
        for tag, be in backends:
            c = cv2.VideoCapture(dev, be) if be else cv2.VideoCapture(dev)
            if c.isOpened():
                cap, backend_tag = c, tag
                break
            c.release()
        if cap is None:
            raise RuntimeError("cihaz acilamadi: %r" % (self._spec,))

        # SIRA ONEMLI: once format, sonra cozunurluk, sonra kare hizi.
        fourcc = os.environ.get("AVCI_DEVICE_FOURCC", "MJPG").strip()
        if fourcc:
            try:
                mk = getattr(cv2, "VideoWriter_fourcc", None) or cv2.VideoWriter.fourcc
                cap.set(cv2.CAP_PROP_FOURCC, mk(*fourcc[:4]))
            except Exception:
                pass
        size = os.environ.get("AVCI_DEVICE_SIZE", "").replace(" ", "")
        if size:
            try:
                w, h = [int(v) for v in size.split(",")]
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
            except Exception:
                print("[KAMERA] AVCI_DEVICE_SIZE cozulemedi (%r)." % size)
        fps_req = os.environ.get("AVCI_DEVICE_FPS", "").strip()
        if fps_req:
            try:
                cap.set(cv2.CAP_PROP_FPS, float(fps_req))
            except Exception:
                pass
        # Takviye — backend yok sayabilir, yapisal onlem uretici dongusudur.
        try:
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass

        self._cap = cap
        got_fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        self.period_ms = (1000.0 / got_fps) if got_fps > 1.0 else 33.3
        self.name = "cv2 %s %dx%d @%.0f fps" % (
            backend_tag, int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)), got_fps)
        self.drain()

    def read(self):
        ok, frame = self._cap.read()
        return frame if ok else None

    def drain(self):
        """Kuyrukta BEKLEYEN bayat kareleri at; ilk GERCEK yeni karede dur.

        Ayirt etme olcusu olculdu: kuyruktaki kare aninda doner (0.1 ms),
        gercek yeni kare bir kare periyodu bekletir. Esik periyodun yarisi.
        """
        dropped = 0
        for _ in range(8):
            t0 = time.perf_counter()
            ok, _f = self._cap.read()
            if not ok:
                break
            if (time.perf_counter() - t0) * 1000.0 >= self.period_ms * 0.5:
                break  # gercek yeni kare -> kuyruk bosaldi
            dropped += 1
        return dropped

    def idle(self):
        """Gorev yokken de OKU: okumazsak kuyruk birikir ve gorev basladiginda
        guduum bayat kareyle acilir."""
        self._cap.read()

    def close(self):
        try:
            self._cap.release()
        except Exception:
            pass
        self._cap = None


def _make_source():
    spec = os.environ.get("AVCI_DEVICE", "").strip()
    return DeviceSource(spec) if spec else ScreenSource()


def capture_bgr():
    """Tek atislik yakalama — (BGR ndarray, kaynak_adi) | (None, sebep).

    Guduum hattinda KULLANILMAZ (o hat uretici thread'inden besleniyor);
    kalibrasyon icin durur: AVCI_REGION ayarlarken ve RANGE_C_REF olcerken
    dedektorun gordugu kareyi tek karede almak gerekir.
    """
    src = _make_source()
    try:
        src.open()
        frame = src.read()
        return (frame, src.name) if frame is not None else (None, "KARE YOK")
    except Exception as e:
        return None, "KARE YOK (%s)" % e
    finally:
        src.close()


# ==========================================================
#  URETICI
# ==========================================================
def _producer(active):
    """Kaynaktan surekli kare cekip _latest'i tazeler. Tek isi budur."""
    source = _make_source()
    opened = False
    was_idle = True
    t_prev = None
    while True:
        if not opened:
            try:
                source.open()
                opened = True
                _state["source"] = source.name
                _state["error"] = None
                print("[KAMERA] goruntu kaynagi -> %s" % source.name)
            except Exception as e:
                _state["error"] = repr(e)
                print("[KAMERA] kaynak ACILAMADI (%s) -> 2 s sonra tekrar." % e)
                time.sleep(2.0)
                continue

        if not active():
            try:
                source.idle()
            except Exception:
                pass
            was_idle = True
            continue

        try:
            if was_idle:
                # Duraklamada kuyruk birikmis olabilir -> gorev BAYAT kareyle acilmasin.
                n = source.drain()
                if n:
                    _state["dropped"] += n
                    print("[KAMERA] kuyruktaki %d bayat kare atildi." % n)
                was_idle = False

            frame = source.read()
        except Exception as e:
            _state["error"] = repr(e)
            print("[KAMERA] okuma hatasi (%s) -> kaynak yeniden aciliyor." % e)
            source.close()
            opened = False
            time.sleep(0.5)
            continue

        if frame is None:
            time.sleep(0.02)
            continue

        t = time.perf_counter()
        _publish_frame(frame, t)
        _state["cap_frames"] += 1
        if t_prev is not None:
            dt = t - t_prev
            if dt > 1e-6:
                _state["cap_fps"] = 0.8 * _state["cap_fps"] + 0.2 * (1.0 / dt)
        t_prev = t


# ==========================================================
#  TUKETICI
# ==========================================================
def _debug_draw(bgr, det):
    """Dedektorun ISLEDIGI karenin uzerine AYNI karenin ciktisini ciz (kare<->cikti
    %100 senkron). Yalnizca AVCI_DEBUG_WINDOW=1 iken; kapaliyken sifir maliyet."""
    try:
        import cv2
        img = bgr.copy()
        if det is not None:
            x1 = int(det["cx"] - det["w"] / 2); y1 = int(det["cy"] - det["h"] / 2)
            x2 = int(det["cx"] + det["w"] / 2); y2 = int(det["cy"] + det["h"] / 2)
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            label = "ID:%s %.2f" % (det.get("track_id", "-"), det.get("conf", 0.0))
            cv2.putText(img, label, (x1, max(20, y1 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        if img.shape[1] > 1280:
            img = cv2.resize(img, (1280, int(img.shape[0] * 1280 / img.shape[1])))
        cv2.imshow("dedektor gozu", img)
        cv2.waitKey(1)
    except Exception:
        pass


def loop(active):
    """Tespit/takip is parcacigi — _latest'ten okur, ASLA yakalama beklemez.

    active : her turda cagrilan, "gorev calisiyor mu" sorusunu yanitlayan islev.
    """
    detector = None
    tracker = Tracker()
    last_seq = 0
    _t_prev = None
    while True:
        if not active():
            if tracker.tracks:
                tracker.reset()  # yeni gorev bayat ID ile baslamasin
            last_seq = 0
            _t_prev = None
            time.sleep(0.05)
            continue

        if detector is None:  # LAZY: ilk gorev tikinde yukle
            detector = TargetDetector(half=(True if FP16 else False))
            if detector.ready:
                # Model adi SABIT DEGIL (AVCI_MODEL ile degisir) -> yolu yazdir.
                print("[KAMERA] %s yuklendi (device=%s, half=%s, imgsz=%d). Siniflar: %s"
                      % (os.path.basename(MODEL_PATH), detector.device,
                         detector.half, detector.imgsz, detector.names))
                if not tracker.ready:
                    print("[KAMERA] takipci YUKLENEMEDI (%s) -> ham tespit kullanilir."
                          % tracker.error)
            else:
                print("[KAMERA] Dedektor YUKLENEMEDI (%s) -> sistem GPS fazinda devam eder."
                      % detector.error)
        if not detector.ready:
            time.sleep(1.0)  # kurulum yok -> CPU yakma
            continue

        frame, seq, t_cap = _take_frame()
        if frame is None or seq == last_seq:
            time.sleep(0.001)  # uretici henuz yeni kare koymadi
            continue
        # Aradaki kareler bilerek DUSURULDU: en tazesiyle calisiyoruz.
        if last_seq:
            _state["dropped"] += max(0, seq - last_seq - 1)
        last_seq = seq

        t0 = time.perf_counter()
        dets = detector.detect_all(frame)
        det = tracker.update(dets, frame)
        t1 = time.perf_counter()

        detection_state.publish(det, frame_t=t1)
        _state["frames"] += 1
        _state["det_ms"] = (t1 - t0) * 1000.0
        _state["age_ms"] = (t0 - t_cap) * 1000.0  # kare cikarima girerken kac ms eskiydi
        if _t_prev is not None:
            dt = t1 - _t_prev
            if dt > 1e-6:
                _state["fps"] = 0.8 * _state["fps"] + 0.2 * (1.0 / dt)
        _t_prev = t1

        if DEBUG_WINDOW:
            _debug_draw(frame, det)


def start(active):
    """Uretici + tuketici is parcaciklarini arka planda baslat."""
    prod = threading.Thread(target=_producer, args=(active,), daemon=True,
                            name="camera-capture")
    prod.start()
    cons = threading.Thread(target=loop, args=(active,), daemon=True, name="camera")
    cons.start()
    return cons


def status():
    """Kamera hatti ozeti.

    frames/fps/det_ms/source — TUKETICI (tespit) tarafi; arayuz bunlari okur.
    cap_frames/cap_fps       — URETICI (yakalama) tarafi.
    age_ms                   — kare cikarima girerken kac ms eskiydi.
    dropped                  — uretilip hic islenmeyen kare (tuketici yavas).
    """
    return dict(_state)

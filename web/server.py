# -*- coding: utf-8 -*-
"""
AVCI DRONE — YER KONTROL ISTASYONU
Calistir: python -m web.server   ->   http://127.0.0.1:8001   (Ctrl+C: kapat)

Bu sunucu GUDUM URETMEZ ve GUDUM YASASI ICERMEZ. Yalnizca donguyu kosturur:
komutu `control/` uretir, arayuz gosterir ve baslat/durdur eder.

IKI MOD
  GPS     — kalkis (`control.takeoff.TakeoffLaw`) + bozuk GNSS'i temizleyip
            hedefin kuyrugundaki istasyona oturma
            (`control.gps_approach.GPSTracker`).
            Kamera hatti HIC calismaz (dedektor yuklenmez).
  HIBRIT  — GPS + KAMERA. Ayni kalkis/GPS fazlari ile baslar; devir kapisi acilinca
            (`control.main.PhaseSupervisor`) gorsel faza gecer ve komut
            YALNIZCA kameradan turer (`control.visual_tracking.VisualTracker`).
            Hedef kaybolursa GPS istasyon tutmaya geri donulur.

⛔ GORSEL FAZDA GPS/GNSS KOMUTA GIRMEZ (yarisma kurali; aksi diskalifiye).
  Yapisal garanti `VisualTracker.compute` imzasindadir: hedefe ait tek veri
  bbox pikselleridir. Bu dosyanin gorsel fazda cagirdigi tek GPS islevi
  `beyin.clean_target()`'dir ve donen deger HICBIR KOMUTA GIRMEZ — amaci
  filtreyi sicak tutmaktir (faz geri donerse sifirdan isinmasin).

⛔ `get_debug_truth()` KULLANILMAZ. O kanal yalnizca oyunun debug secenegi
  acikken gelir, yarismada YOKTUR; arayuzun ona bagli bir gostergesi olursa
  yarisma kosusunda sessizce bos kalir. Gosterilen her mesafe ya HAM GNSS'ten
  ya da FILTRELENMIS kestirimden turer.

⚠ Ekran paylasimi/kamera goruntusu YOKTUR. Hibrit modda kamera hatti
  (perception/camera.py) oyun EKRANINI yakalar; oyun penceresi GORUNUR/ONDE
  kalmalidir, yoksa dedektore masaustu pikseli gider.
"""
import json
import os
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from control.common import CM_TO_M, CommandSender, Telemetry
from control.visual_tracking import VisualCfg, VisualTracker
from control.gps_approach import GPSCfg, GPSTracker
from control.main import Cfg as PhaseCfg, PhaseSupervisor
from control.takeoff import TakeoffLaw
from perception import camera, detection_state
from sdk import drone_sdk as drone

MS_TO_KMH = 3.6
WEB_PORT = 8001
HERE = os.path.dirname(os.path.abspath(__file__))
GNSS_GAP_S = 1.0
CAMERA_WARN_S = 15.0  # s; hibrit modda bu kadar kare gelmezse uyar

MODE_GPS = "GPS"
MODE_HYBRID = "HYBRID"


# ==========================================================
# BEYIN + PAYLASILAN DURUM
# ==========================================================
tlm = Telemetry(drone)
sender = CommandSender(drone)      # oyuna giden TEK komut kapisi
takeoff = TakeoffLaw(drone, sender)  # kalkis fazi (yalniz dikey tirmanis)
brain = GPSTracker(drone, sender)  # GPS fazi (istasyon tutma)
visual = VisualTracker()           # gorsel faz (IBVS)
supervisor = PhaseSupervisor()     # YALNIZ faz kapisi — komut uretmez
brain_lock = threading.Lock()
mission_active = False
mission_mode = MODE_GPS

event_lock = threading.Lock()
_events = deque(maxlen=400)
_event_id = 0

_last_raw_packet = None
_last_det = None  # son GECERLI tespit (yalniz gosterge)

_mission = {"phase": "READY", "t0": None}
_watch = {"gap": False, "last_packet_t": None,
          "_error_reported": False, "camera_frames": False, "camera_warned": False,
          "camera_frames0": 0}


def add_event(sv, message):
    """Olay gunluge ekle. sv: bilgi|iyi|uyari|kritik."""
    global _event_id
    with event_lock:
        _event_id += 1
        _events.append({"id": _event_id, "t": time.time(), "sv": sv, "m": message})
    print("[OLAY] %s" % message)


def _mission_reset(phase):
    _mission.update(phase=phase, t0=time.time())
    # ⚠ camera.status()["kare"] KUMULATIFTIR (gorevler arasi sifirlanmaz) ->
    #   "ilk kare geldi" olayi bu gorevin TABANINA gore olculur, yoksa ikinci
    #   koşuda daha hicbir kare gelmeden "calisiyor" derdi.
    _watch.update(camera_frames=False, camera_warned=False,
                  camera_frames0=camera.status().get("frames", 0))


# ==========================================================
# BAGLANTI YONETICISI
# ==========================================================
def connection_manager():
    _conn_prev = None
    while True:
        c = drone.is_connected()
        if c and _conn_prev is not True:
            add_event("good", "Oyuna baglanildi")
        elif (not c) and _conn_prev is True:
            add_event("warn", "Oyun baglantisi koptu")
        _conn_prev = c
        if not c:
            try:
                drone.disconnect()
            except Exception:
                pass
            drone.connect()
        time.sleep(2.0)


# ==========================================================
# IZLEYICI
# ==========================================================
def _track_packet():
    """Yeni ham pakette last_packet_t'yi tazele (GNSS kesinti izleyicisi icin)."""
    global _last_raw_packet
    raw = brain.last_raw
    if raw is None or raw == _last_raw_packet:
        return
    _last_raw_packet = raw
    _watch["last_packet_t"] = time.time()


def _watch_camera():
    """Hibrit modda kamera hatti gercekten calisiyor mu? (yalniz gosterge)

    Dedektor TEMBEL yuklenir (ilk hibrit tikinde). torch/ultralytics kurulu
    degilse `camera.loop` sessizce bekler ve kare sayaci hic ilerlemez —
    bu SESSIZ bir bozulmadir, arayuzun bunu soylemesi gerekir.
    """
    if mission_mode != MODE_HYBRID or not mission_active:
        return
    frames = camera.status().get("frames", 0)
    if frames > _watch.get("camera_frames0", 0):
        if not _watch["camera_frames"]:
            _watch["camera_frames"] = True
            add_event("good", "Kamera hatti calisiyor — tespit kareleri geliyor")
        return
    t0 = _mission.get("t0")
    if (not _watch["camera_warned"] and t0 is not None
            and (time.time() - t0) > CAMERA_WARN_S):
        _watch["camera_warned"] = True
        add_event("critical", "Kamera hattindan %.0f s'dir KARE GELMEDI — dedektor "
                            "yuklenemedi olabilir (torch/ultralytics). Gorev GPS "
                            "fazinda devam eder." % CAMERA_WARN_S)


def _watch_mission():
    """Her tik: GNSS kesintisi + faz metni. Kesinti gorev pasifken de izlenir."""
    now = time.time()
    spt = _watch["last_packet_t"]
    age = (now - spt) if spt is not None else None
    gap_now = (age is not None and age > GNSS_GAP_S)
    if gap_now and not _watch["gap"]:
        _watch["gap"] = True
        add_event("warn", "GNSS KESINTISI — hedef GPS paketi gelmiyor")
    elif (not gap_now) and _watch["gap"]:
        _watch["gap"] = False
        add_event("good", "GNSS geri geldi — kesinti bitti (%.1f s)" % (age or 0.0))

    if not mission_active:
        _mission["phase"] = "READY"
        return

    # ⚠ Faz metni TEK KAYNAKTAN — gozetmenden — gelir. `brain.phase` artik
    #   yalnizca "STATION" uretir; kalkis GPSTracker'dan CIKARILDI. Kalkis
    #   bitisi olayini `_takeoff_step` yazar (kapiyi o an gozetmen acar);
    #   burada ayrica izlenmez, yoksa iki yerde iki ayri kalkis tanimi olurdu.
    in_visual = (mission_mode == MODE_HYBRID
                 and supervisor.phase == PhaseSupervisor.VISUAL)
    in_takeoff = (supervisor.phase == PhaseSupervisor.TAKEOFF)
    _mission["phase"] = ("VISUAL" if in_visual
                         else "TAKEOFF" if in_takeoff else brain.phase)
    _watch_camera()


# ==========================================================
# KALKIS ADIMI — her iki modda da AYNI (kamera fark etmez)
# ==========================================================
def _takeoff_step(t):
    """KALKIS fazinin bir tiki: dikey tirmanis + kalkis kapisi.

    Bu islev KAPI KARARI VERMEZ ve GUDUM YASASI ICERMEZ: komutu
    `control.takeoff.TakeoffLaw`, kapiyi `PhaseSupervisor.takeoff_tick` uretir.

    ⭐ FILTRE BURADA DA BESLENIR — atlanmasi SESSIZ bir bozulma olurdu.
      GNSS filtresinin ISINMA TRANSIENTI ilk ~4 saniyededir (pencere medyani
      23.6 m, max 52 m) ve kalkis tam o pencereyi kapatir. Kalkista
      beslemezsek transient oldugu gibi ISTASYON fazinin ilk saniyelerine —
      yani yatay komutun URETILDIGI yere — tasinir.
    """
    global _last_det
    takeoff.step()
    brain.clean_target()  # KOMUTA GIRMEZ; filtre isinsin diyedir (bkz. docstring)

    # Kamera yalnizca hibrit modda calisir; GPS modunda tespit okunmaz.
    det = seq = None
    if mission_mode == MODE_HYBRID:
        det, seq = supervisor.read_detection(t)
        _last_det = det

    # Hedefin irtifasina gore bosluk (kalkis kapisinin (b) kolu); hedef yoksa None.
    gap = None
    if brain.target_p is not None:
        gap = takeoff.alt_z - brain.target_p[2]

    if supervisor.takeoff_tick(t, takeoff.height, target_alt_gap=gap,
                               det=det, seq=seq, last_raw=brain.last_raw):
        add_event("good", supervisor.handoff_message())


# ==========================================================
# HIBRIT ADIM — faz kapisi gozetmende, guduum control/ icinde
# ==========================================================
def _hybrid_step(t, dt):
    """GPS <-> GORSEL faz akisinin bir tiki. Bu islev KAPI KARARI VERMEZ ve
    GUDUM YASASI ICERMEZ: kapiyi `gozetmen`, komutu `beyin`/`gorsel` uretir."""
    global _last_det
    det, seq = supervisor.read_detection(t)
    _last_det = det

    # ==================== GPS FAZI ====================
    # (KALKIS fazi buraya HIC girmez: kontrol dongusu onu `_takeoff_step`e
    #  yonlendirir, cunku kalkis moddan BAGIMSIZDIR.)
    if supervisor.phase == PhaseSupervisor.GPS:
        brain.step()  # istasyon tutma
        if supervisor.gps_tick(t, det, seq,
                               station_err=brain.station_err, range_h=brain.range_h,
                               last_raw=brain.last_raw):
            visual.reset()  # taze integral + taze kopru
            add_event("good", "[DEVIR] " + supervisor.handoff_message())
        return

    # ==================== GORSEL FAZ ====================
    # Filtreyi taze tut (KOMUTA GIRMEZ; faz geri donerse isinmis olsun).
    brain.clean_target()

    own_att = tlm.orientation_deg()  # KENDI IMU'muz (ego-motion)
    own_vel = tlm.velocity_ms()      # KENDI hiz vektorumuz

    box = visual.box(det, own_att, t)  # taze tespit ya da KOPRU (olu-hesap)
    if box is not None:
        thr, pitch, roll, yaw = visual.compute(box, own_att, own_vel, dt)
        sender.send(thr, pitch, roll, yaw)
    else:
        # ⛔ DERS: burada son komut AYNEN tutuluyordu. Son komut sert bir
        #   donusse (roll +-1) arac KOR halde firil firil doner ve hedefi bir
        #   daha bulamaz. DONUS SIFIRLANIR; ileri ve dikey korunur — hedef
        #   kadrajda kaldigi yerde kalsin.
        prev_cmd = sender.prev
        sender.send(prev_cmd["thr"], prev_cmd["pitch"], 0.0, 0.0)

    if supervisor.visual_tick(t, det, seq, box_ok=(box is not None),
                              last_raw=brain.last_raw):
        visual.reset()
        add_event("warn", "[DEVIR] " + supervisor.handoff_message())


# ==========================================================
# KONTROL DONGUSU (50 Hz)
# ==========================================================
def control_loop():
    t_prev = None
    while True:
        if not drone.is_connected():
            t_prev = None
            time.sleep(GPSCfg.DT)
            continue
        # dt OLCULUR (nominal DT degil): gorsel fazin ileri hiz PI'si ve
        # kopru omru gercek adim suresiyle calisir.
        t = time.perf_counter()
        dt = GPSCfg.DT if t_prev is None else max(1e-4, t - t_prev)
        t_prev = t
        try:
            with brain_lock:
                if not mission_active:
                    brain.clean_target()  # gorev pasifken bile filtre isinsin
                elif supervisor.phase == PhaseSupervisor.TAKEOFF:
                    _takeoff_step(t)      # kalkis IKI MODDA da ayni
                elif mission_mode == MODE_HYBRID:
                    _hybrid_step(t, dt)
                else:
                    brain.step()
                _track_packet()
                try:
                    _watch_mission()
                except Exception as e:
                    if not _watch.get("_error_reported"):
                        _watch["_error_reported"] = True
                        print("[IZLEYICI HATA] %r" % e)
        except Exception:
            pass
        time.sleep(GPSCfg.DT)


# ==========================================================
# TELEMETRI
# ==========================================================
def build_telemetry():
    connected = drone.is_connected()
    dx, dy, dz = tlm.position_m()
    drot = tlm.orientation_deg()
    dspd = drone.get_drone_speed() * CM_TO_M  # m/s
    tpos = tlm.target_raw_cm()  # HAM (bozuk) GNSS
    tx, ty, tz = (c * CM_TO_M for c in tpos)
    distance_m = ((dx - tx) ** 2 + (dy - ty) ** 2 + (dz - tz) ** 2) ** 0.5

    with brain_lock:
        prev_cmd = dict(sender.prev)
        target_p = brain.target_p
        range_h = brain.range_h
        diag = brain.status()
        mission_s = dict(_mission)
        watch_gap = bool(_watch["gap"])
        sup = supervisor.status()
        gt = visual.status()
        det = dict(_last_det) if _last_det else None
        mode = mission_mode

    j_info = {}
    if target_p is not None:
        j_info["clean"] = {"x": target_p[0], "y": target_p[1], "z": target_p[2]}
    if diag.get("station_x") is not None:
        j_info["station"] = {"x": diag["station_x"], "y": diag["station_y"],
                             "z": diag["station_z"]}

    cam = camera.status()
    visual_range = gt.get("range_m")
    if visual_range is not None and visual_range <= 0:
        visual_range = None

    with event_lock:
        event_list = list(_events)[-60:]

    return {
        "connected": connected,
        "mission_active": mission_active,
        "mode": mode,  # GPS | HIBRIT
        "drone": {
            "x": dx, "y": dy, "z": dz,
            "speed_kmh": dspd * MS_TO_KMH, "yaw": drot[2],
        },
        # HAM (bozuk) GNSS. ⛔ HIZ ALANI YOK: SDK'nin get_target_speed()'i
        # DAIMA 0 doner (kardes depoda 234587 ornekte dogrulandi), yani panele
        # kalici bir "0.0 km/h" yazardi. Gercek hiz kestirimi FILTREDEDIR ve
        # su an arayuze hic tasinmaz (istasyon paneli kaldirildi).
        "target": {"x": tx, "y": ty, "z": tz},
        "distance_m": distance_m,     # ham GNSS'e gore
        "clean_distance_m": range_h,  # FILTRELENMIS kestirime gore
        "overlay": j_info,
        "gap": watch_gap,
        "guidance": {
            "thr": prev_cmd.get("thr", 0.0), "pitch": prev_cmd.get("pitch", 0.0),
            "roll": prev_cmd.get("roll", 0.0), "yaw": prev_cmd.get("yaw", 0.0),
        },
        # --- GORSEL FAZ (yalniz HIBRIT modda anlamli) ---
        # ⚠ Faz metni BURADA YOK: tek kaynak "mission.phase" (gozetmenden gelir).
        #   Ayrica tasinirsa arayuzde iki ayri faz gostergesi olusur.
        "visual": {
            "lock": sup["lock"], "lock_need": sup["lock_need"],
            "lock_s": sup["lock_s"], "lock_s_need": sup["lock_s_need"],
            "station_ticks": sup["station_ticks"],
            "station_ticks_need": sup["station_ticks_need"],
            "handoff_count": sup["handoff_count"],
            "gnss_stale": sup["gnss_stale"],
            "camera_only_gate": sup["camera_only_gate"],
            "conf": det.get("conf") if det else None,
            "conf_min": VisualCfg.CONF_MIN,
            "range_m": visual_range,  # KUTUDAN (GPS'ten degil)
            "size_px": gt.get("size_px"),
            "v_fwd": gt.get("v_fwd"),
            "e_cy": gt.get("e_cy"),
            "bridge": bool(gt.get("bridge")),
            "bridge_frames": gt.get("bridge_frames"),
        },
        "camera": {
            "frames": cam.get("frames", 0), "fps": cam.get("fps", 0.0),
            "det_ms": cam.get("det_ms", 0.0),
        },
        "mission": {
            "phase": mission_s.get("phase", "READY"),
            "t0": mission_s.get("t0"),
        },
        "events": event_list,
    }


# ==========================================================
# GOREV BASLAT / DURDUR
# ==========================================================
def mission_start(mode):
    """Yeni gorev: TUM durum sifirdan. mod: MODE_GPS | MODE_HYBRID."""
    global mission_active, mission_mode
    with brain_lock:
        takeoff.reset()  # zemin referansi ARM aninda yeniden alinsin
        brain.reset()
        sender.reset()
        visual.reset()
        supervisor.reset()
        detection_state.reset()  # yeni gorev bayat kutuyla baslamasin
        _mission_reset("TAKEOFF")
        # ⚠ mod ve aktif bayragi AYNI kilit altinda kurulur: kamera thread'i
        #   ikisine BIRLIKTE bakar (camera_active), kontrol dongusu de oyle.
        #   Ayri ayri yazilsa arada bir tik "aktif ama mod eski" hali olurdu.
        mission_mode = mode
        mission_active = True

    if mode == MODE_HYBRID:
        msg = ("HIBRIT TAKIP BASLATILDI — GPS ile hedefin %.0f m gerisindeki "
               "istasyona oturulacak, kilit kurulunca komut KAMERAYA devredilir"
               % GPSCfg.STATION_RANGE_M)
        add_event("good", "HIBRIT TAKIP BASLADI (GPS + KAMERA) — devir kapisi: "
                         "%.1f s VE %d kare kilit + istasyon hatasi <%.0f m"
                         % (VisualCfg.HANDOFF_LOCK_S, VisualCfg.HANDOFF_FRAMES,
                            PhaseCfg.HANDOFF_STATION_ERR_M))
    else:
        msg = ("GPS TAKIBI BASLATILDI — bozuk GNSS temizlenip hedefin "
               "%.0f m gerisindeki istasyona oturuluyor"
               % GPSCfg.STATION_RANGE_M)
        add_event("good", "GPS TAKIBI BASLADI — kaynak: bozuk GNSS (GNSSFilterV2, CT-EKF)")
    return msg


def mission_stop():
    """Motorlari kes. ⚠ KILIT ALTINDA: kilitsiz kesilirse kontrol dongusu ayni
    tikte `_hybrid_step`in ortasinda olabilir ve `cut()`ten HEMEN SONRA komut
    gonderip motorlari yeniden armlar. Durdur, DURDURMAK demektir."""
    global mission_active
    with brain_lock:
        mission_active = False
        try:
            sender.cut()  # motorlari kes (TEK komut kapisi)
        except Exception:
            pass
        # Faz BURADA sifirlanir, izleyicide degil: izleyici yalnizca oyuna
        # BAGLIYKEN kosar; baglanti yokken arayuz "KALKIS"ta asili kalirdi.
        _mission["phase"] = "READY"
    add_event("warn", "GOREV DURDURULDU")
    return "GOREV DURDURULDU — drone pasif (motorlar kapali)"


# ==========================================================
# HTTP ISTEK ISLEYICI
# ==========================================================
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, code, content, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        if self.path in ("/", "/index.html", "/server.html"):
            try:
                with open(os.path.join(HERE, "server.html"), "rb") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
            except FileNotFoundError:
                self._send(404, "server.html bulunamadi".encode("utf-8"),
                           "text/plain; charset=utf-8")
        elif self.path == "/api/telemetry":
            self._send(200, json.dumps(build_telemetry()).encode("utf-8"),
                       "application/json")
        else:
            self._send(404, b"yok", "text/plain; charset=utf-8")

    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def do_POST(self):
        if self.path == "/api/command":
            data = self._read_json()
            cmd = data.get("cmd", "")
            msg = "Bilinmeyen komut"
            if cmd == "start_gps":
                msg = mission_start(MODE_GPS)
            elif cmd == "start_hybrid":
                msg = mission_start(MODE_HYBRID)
            elif cmd == "stop":
                msg = mission_stop()
            self._send(200, json.dumps({"ok": True, "msg": msg,
                                        "mission_active": mission_active,
                                        "mode": mission_mode}).encode("utf-8"),
                       "application/json")
        else:
            self._send(404, b"yok", "text/plain; charset=utf-8")


# ==========================================================
# ANA PROGRAM
# ==========================================================
def camera_active():
    """Kamera hatti YALNIZ hibrit gorev kosarken calissin.

    Dedektor TEMBEL yuklenir (ilk `True` doneninde) -> GPS modunda torch hic
    ice aktarilmaz, VRAM ayrilmaz, ekran yakalanmaz.
    """
    return mission_active and mission_mode == MODE_HYBRID and drone.is_connected()


def main():
    import faulthandler, traceback
    faulthandler.enable()

    threading.Thread(target=connection_manager, daemon=True).start()
    threading.Thread(target=control_loop, daemon=True).start()
    camera.start(camera_active)

    try:
        server = ThreadingHTTPServer(("127.0.0.1", WEB_PORT), Handler)
    except OSError as e:
        print("[HATA] %d portu acilamadi (baska bir ornek calisiyor olabilir): %s"
              % (WEB_PORT, e))
        return
    print("  YER KONTROL ISTASYONU  ->  http://127.0.0.1:%d   (Ctrl+C: kapat)"
          % WEB_PORT)
    print("  Modlar: GPS (yalniz istasyon tutma) | HIBRIT (GPS + kamera)")
    print("  Hibrit modda oyun penceresi GORUNUR/ONDE kalmali (ekran yakalanir).")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nKapatiliyor...")
    except Exception:
        traceback.print_exc()
    finally:
        try:
            sender.cut()
        except Exception:
            pass
        drone.disconnect()


if __name__ == "__main__":
    main()

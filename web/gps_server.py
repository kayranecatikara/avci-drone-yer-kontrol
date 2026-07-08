# -*- coding: utf-8 -*-
"""
GPS TAKIP - YER KONTROL ISTASYONU
Calistir: python -m web.gps_server   ->   http://127.0.0.1:8001   (Ctrl+C: kapat)
"""
import json
import os
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from sdk import drone_sdk as drone
from guidance.gps_takip import GPSTakip, GPSCfg

CM_TO_M = 0.01
MS_TO_KMH = 3.6
WEB_PORT = 8001
HERE = os.path.dirname(os.path.abspath(__file__))
GNSS_KESINTI_S = 1.0


# ==========================================================
# BEYIN + PAYLASILAN DURUM
# ==========================================================
beyin = GPSTakip(drone)
beyin_lock = threading.Lock()
gorev_aktif = False

olay_lock = threading.Lock()
_olaylar = deque(maxlen=400)
_olay_id = 0

_son_paket_ham = None

_gorev = {"faz": "HAZIR", "t0": None, "en_yakin_m": None}
_izci = {"kesinti": False, "son_paket_t": None, "kalkis_prev": None, "_hata_bildirildi": False}


def olay_ekle(sv, mesaj):
    """Olay gunluge ekle. sv: bilgi|iyi|uyari|kritik."""
    global _olay_id
    with olay_lock:
        _olay_id += 1
        _olaylar.append({"id": _olay_id, "t": time.time(), "sv": sv, "m": mesaj})
    print("[OLAY] %s" % mesaj)


def _gorev_sifirla(faz):
    _gorev.update(faz=faz, t0=time.time(), en_yakin_m=None)
    _izci.update(kalkis_prev=None)


# ==========================================================
# BAGLANTI YONETICISI
# ==========================================================
def connection_manager():
    _conn_prev = None
    while True:
        c = drone.is_connected()
        if c and _conn_prev is not True:
            olay_ekle("iyi", "Oyuna baglanildi")
        elif (not c) and _conn_prev is True:
            olay_ekle("uyari", "Oyun baglantisi koptu")
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
def _paket_izle():
    """Yeni ham pakette son_paket_t'yi tazele (kesinti izleyici icin; truth gerekmez)."""
    global _son_paket_ham
    ham = beyin.son_ham
    if ham is None or ham == _son_paket_ham:
        return
    _son_paket_ham = ham
    _izci["son_paket_t"] = time.time()


def _mesafe_olc():
    """En-yakin takibi icin durust mesafe (m): truth varsa gercek 3B, yoksa temiz(anlik)."""
    truth = drone.get_debug_truth()
    if truth.get("available"):
        adx, ady, adz = truth["drone"]["position"]
        tgx, tgy, tgz = truth["target"]["position"]
        d = ((adx - tgx) ** 2 + (ady - tgy) ** 2 + (adz - tgz) ** 2) ** 0.5
        return d * CM_TO_M
    if beyin.son_xy_anlik is not None and beyin.son_z_anlik is not None:
        dp = drone.get_drone_location()
        tx, ty, tz = float(beyin.son_xy_anlik[0]), float(beyin.son_xy_anlik[1]), float(beyin.son_z_anlik)
        d = ((dp[0] - tx) ** 2 + (dp[1] - ty) ** 2 + (dp[2] - tz) ** 2) ** 0.5
        return d * CM_TO_M
    return None


def _gorev_izle():
    """Her tik: kesinti + faz + en-yakin mesafe. Kesinti gorev pasifken de izlenir."""
    now = time.time()
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
        _gorev["faz"] = "HAZIR"
        return

    _gorev["faz"] = "KALKIS" if not beyin._kalkis_done else "YAKLASMA"
    if beyin._kalkis_done and _izci["kalkis_prev"] is False:
        olay_ekle("iyi", "Kalkis tamamlandi (~%.0f m) — GPS takibi basladi" % (GPSCfg.TAKEOFF_ALT_AGL / 100.0))
    _izci["kalkis_prev"] = bool(beyin._kalkis_done)

    mesafe = _mesafe_olc()
    if mesafe is not None and (_gorev["en_yakin_m"] is None or mesafe < _gorev["en_yakin_m"]):
        _gorev["en_yakin_m"] = mesafe


# ==========================================================
# KONTROL DONGUSU (50 Hz)
# ==========================================================
def kontrol_dongusu():
    while True:
        if drone.is_connected():
            try:
                with beyin_lock:
                    if gorev_aktif:
                        beyin.adim()
                    else:
                        beyin._hedef_temizle()
                    _paket_izle()
                    try:
                        _gorev_izle()
                    except Exception as e:
                        if not _izci.get("_hata_bildirildi"):
                            _izci["_hata_bildirildi"] = True
                            print("[IZLEYICI HATA] %r" % e)
            except Exception:
                pass
        time.sleep(0.02)


# ==========================================================
# TELEMETRI
# ==========================================================
def build_telemetry():
    connected = drone.is_connected()
    dpos = drone.get_drone_location()    # cm
    drot = drone.get_drone_rotation()    # derece
    dspd = drone.get_drone_speed()       # cm/s
    dalt = drone.get_drone_altitude()    # cm
    tpos = drone.get_target_location()   # cm (Ham)
    tspd = drone.get_target_speed()      # cm/s

    dx, dy, dz = (c * CM_TO_M for c in dpos)
    tx, ty, tz = (c * CM_TO_M for c in tpos)
    distance_m = ((dx - tx) ** 2 + (dy - ty) ** 2 + (dz - tz) ** 2) ** 0.5

    truth = drone.get_debug_truth()
    gercek_mesafe_m = None
    if truth.get("available"):
        adx, ady, adz = (c * CM_TO_M for c in truth["drone"]["position"])
        tgx, tgy, tgz = (c * CM_TO_M for c in truth["target"]["position"])
        gercek_mesafe_m = ((adx - tgx) ** 2 + (ady - tgy) ** 2 + (adz - tgz) ** 2) ** 0.5
    with beyin_lock:
        prev_cmd = dict(beyin.prev)
        son_xy = None if beyin.son_xy_anlik is None else (float(beyin.son_xy_anlik[0]), float(beyin.son_xy_anlik[1]))
        son_z_anl = None if beyin.son_z_anlik is None else float(beyin.son_z_anlik)
        gorev_s = dict(_gorev)
        izci_kesinti = bool(_izci["kesinti"])
    j_info = {}

    if son_xy is not None and son_z_anl is not None:
        j_info["temiz"] = {"x": son_xy[0] * CM_TO_M, "y": son_xy[1] * CM_TO_M, "z": son_z_anl * CM_TO_M}

    with olay_lock:
        olay_listesi = list(_olaylar)[-60:]

    return {
        "connected": connected,
        "gorev_aktif": gorev_aktif,
        "drone": {
            "x": dx, "y": dy, "z": dz, "altitude_m": dalt * CM_TO_M,
            "speed_kmh": dspd * CM_TO_M * MS_TO_KMH, "yaw": drot[2],
        },
        "target": {
            "x": tx, "y": ty, "z": tz, "speed_kmh": tspd * CM_TO_M * MS_TO_KMH,
        },
        "distance_m": distance_m,
        "gercek_mesafe_m": gercek_mesafe_m,
        "j": j_info,
        "kesinti": izci_kesinti,
        "gudum": {
            "thr": prev_cmd.get("thr", 0.0), "pitch": prev_cmd.get("pitch", 0.0),
            "roll": prev_cmd.get("roll", 0.0), "yaw": prev_cmd.get("yaw", 0.0),
        },
        "gorev": {                                      # faz + en yakin mesafe
            "faz": gorev_s.get("faz", "HAZIR"), "en_yakin_m": gorev_s.get("en_yakin_m"),
            "t0": gorev_s.get("t0"),
        },
        "olaylar": olay_listesi,
    }


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
        if self.path in ("/", "/index.html", "/gps_index.html"):
            try:
                with open(os.path.join(HERE, "gps_index.html"), "rb") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
            except FileNotFoundError:
                self._send(404, "gps_index.html bulunamadi".encode("utf-8"), "text/plain; charset=utf-8")
        elif self.path == "/api/telemetry":
            self._send(200, json.dumps(build_telemetry()).encode("utf-8"), "application/json")
        else:
            self._send(404, b"yok", "text/plain; charset=utf-8")

    def _oku_json(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def do_POST(self):
        global gorev_aktif
        if self.path == "/api/command":
            data = self._oku_json()
            cmd = data.get("cmd", "")
            msg = "Bilinmeyen komut"
            if cmd in ("start", "start_gnss"):
                with beyin_lock:
                    beyin.sifirla()
                    _gorev_sifirla("KALKIS")
                gorev_aktif = True
                msg = "GPS TAKIBI BASLATILDI — bozuk GNSS temizlenerek hedefe yaklasiliyor"
                olay_ekle("iyi", "GPS TAKIBI BASLADI — kaynak: bozuk GNSS (GNSSFiltre)")
            elif cmd == "stop":
                gorev_aktif = False
                try:
                    drone.set_control_surfaces(0.0, 0.0, 0.0, 0.0, False)   # motorlari kes
                except Exception:
                    pass
                msg = "GPS TAKIBI DURDURULDU — drone pasif (motorlar kapali)"
                olay_ekle("uyari", "GPS TAKIBI DURDURULDU")
            self._send(200, json.dumps({"ok": True, "msg": msg, "gorev_aktif": gorev_aktif}).encode("utf-8"),
                       "application/json")
        else:
            self._send(404, b"yok", "text/plain; charset=utf-8")


# ==========================================================
# ANA PROGRAM
# ==========================================================
def main():
    import faulthandler, traceback
    faulthandler.enable()

    threading.Thread(target=connection_manager, daemon=True).start()
    threading.Thread(target=kontrol_dongusu, daemon=True).start()

    try:
        server = ThreadingHTTPServer(("127.0.0.1", WEB_PORT), Handler)
    except OSError as e:
        print("[HATA] %d portu acilamadi (baska bir ornek calisiyor olabilir): %s" % (WEB_PORT, e))
        return
    print("  GPS TAKIP calisiyor  ->  http://127.0.0.1:%d   (Ctrl+C: kapat)" % WEB_PORT)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nKapatiliyor...")
    except Exception:
        traceback.print_exc()
    finally:
        drone.disconnect()


if __name__ == "__main__":
    main()

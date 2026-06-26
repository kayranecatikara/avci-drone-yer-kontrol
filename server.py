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

import drone_sdk as drone
from ana_kontrol import AvciKontrol
from blok_j import GNSSDuzeltici
from omer_filtre import OnlineGNSSDenoiserV6, patch_leading_invalid
import numpy as np

# Ekran yakalama icin
import mss
from PIL import Image
try:
    import pygetwindow as gw
except Exception:
    gw = None

# ----------------------------------------------------------
#  Sabitler
# ----------------------------------------------------------
CM_TO_M = 0.01      # Oyun santimetre verir -> metre icin 0.01 ile carp
MS_TO_KMH = 3.6     # metre/saniye -> kilometre/saat
WEB_PORT = 8000     # Arayuzun acilacagi yerel port

HERE = os.path.dirname(os.path.abspath(__file__))

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
        time.sleep(2.0)


# ----------------------------------------------------------
#  Gorev kontrol beyni (arkadasin AvciKontrol'u)
#  KADEME 1: gorev_aktif=False -> drone UCMAZ, sadece J olcumu yapilir.
#  KADEME 2: buton ile gorev_aktif=True -> drone hedefe gider.
# ----------------------------------------------------------
beyin = AvciKontrol(drone)
beyin_lock = threading.Lock()
gorev_aktif = False

# Telafi tarama testi tamamlandi -> en iyi telafi_sn=2.0 (Efe'nin orijinal ayari).

# ----------------------------------------------------------
#  FILTRE KIYASI: Efe (blok_j) vs Omer (omer_filtre)
#  Ayni ham hedef veriyle iki filtreyi de besler, her birinin GERCEGE
#  hatasini olcer. Gudume DOKUNMAZ; sadece olcum/karsilastirma.
#  ADIL: her cikti KENDI referans zamaninin gercegiyle karsilastirilir
#  (Omer ciktisi 6 paket gecikmeli gelir; o yuzden indeksli eslesme).
# ----------------------------------------------------------
_kiyas_efe = GNSSDuzeltici()
# dt=1.0: oyun ~1.1 Hz veri yolluyor (olculdu) -> 1 paket ~= 1 sn.
# delay_samples=3.0: olculen gercek gecikme ~3 sn = ~3 paket.
# (Omer'in orijinal dt=2.0/delay=4 ayari 0.5 Hz'lik test verisine goreydi.)
_kiyas_omer = OnlineGNSSDenoiserV6(dt=1.0, lag=6, d_gate=4.5,
                                   compensate_delay=True, delay_samples=3.0,
                                   delay_max=6.0, curve_fill=True)
_kiyas_idx = 0
_kiyas_gercek = {}          # idx -> gercek hedef konumu (cm)
_kiyas_son_ham = None
# Son ~80 olcumun penceresi (anlik performans; eski veriye takilmaz)
_kiyas_ham_hata = deque(maxlen=80)
_kiyas_efe_hata = deque(maxlen=80)
_kiyas_omer_hata = deque(maxlen=80)
_omer_warmup = []
_omer_kalibre = False

# Kiyas CSV log: her paket icin ham/efe/omer hatasi (m). Her baslangicta sifirlanir.
_KIYAS_LOG = os.path.join(HERE, "kiyas_log.csv")
try:
    _kiyas_log_f = open(_KIYAS_LOG, "w", encoding="utf-8")
    _kiyas_log_f.write("paket,ham_m,efe_m,omer_m\n")
    _kiyas_log_f.flush()
except Exception:
    _kiyas_log_f = None


def _kiyas_guncelle():
    """Her YENI ham pakette iki filtreyi de besle, gercege hatalarini olc."""
    global _kiyas_idx, _kiyas_son_ham, _omer_kalibre
    ham = drone.get_target_location()
    if ham == _kiyas_son_ham:
        return
    _kiyas_son_ham = ham
    truth = drone.get_debug_truth()
    if not truth.get("available"):
        return
    gercek = np.array(truth["target"]["position"], float)
    idx = _kiyas_idx
    _kiyas_gercek[idx] = gercek
    _kiyas_idx += 1
    hx, hy, hz = ham
    ham_e = float(np.linalg.norm(np.array(ham, float) - gercek))
    _kiyas_ham_hata.append(ham_e)
    efe_e = None
    omer_e = None

    # EFE: anlik cikti -> su anki gercekle karsilastir
    efe_out = _kiyas_efe.guncelle(hx, hy, hz)
    if efe_out is not None:
        efe_e = float(np.linalg.norm(np.array(efe_out, float) - gercek))
        _kiyas_efe_hata.append(efe_e)

    # OMER: once 24 paket kalibrasyon, sonra gecikmeli cikti (kendi referansiyla)
    if not _omer_kalibre:
        _omer_warmup.append([hx, hy, hz])
        if len(_omer_warmup) >= 24:
            arr = patch_leading_invalid(np.array(_omer_warmup, float))
            _kiyas_omer.calibrate(arr)
            for w in arr:
                em = _kiyas_omer.update(np.array(w, float))
                if em is not None and em[0] in _kiyas_gercek:
                    _kiyas_omer_hata.append(
                        float(np.linalg.norm(em[1] - _kiyas_gercek[em[0]])))
            _omer_kalibre = True
    else:
        em = _kiyas_omer.update(np.array([hx, hy, hz], float))
        if em is not None and em[0] in _kiyas_gercek:
            omer_e = float(np.linalg.norm(em[1] - _kiyas_gercek[em[0]]))
            _kiyas_omer_hata.append(omer_e)

    # CSV log (metre): bos sutun = o pakette o filtreden cikti yok (None/isinma)
    if _kiyas_log_f is not None:
        he = "%.2f" % (ham_e / 100.0)
        ee = ("%.2f" % (efe_e / 100.0)) if efe_e is not None else ""
        oe = ("%.2f" % (omer_e / 100.0)) if omer_e is not None else ""
        try:
            _kiyas_log_f.write("%d,%s,%s,%s\n" % (idx, he, ee, oe))
            _kiyas_log_f.flush()
        except Exception:
            pass

    # bellek: cok eski gercek kayitlarini at (Omer en fazla ~6 geriden ister)
    if len(_kiyas_gercek) > 120:
        esik = idx - 60
        for kk in [k for k in _kiyas_gercek if k < esik]:
            del _kiyas_gercek[kk]


def kontrol_dongusu():
    while True:
        if drone.is_connected():
            try:
                with beyin_lock:
                    if gorev_aktif:
                        beyin.adim()              # tam kontrol (drone hedefe gider)
                    else:
                        beyin._hedef_temizle()    # sadece J'yi guncelle (olcum)
                        if beyin.debug_olc:
                            beyin._debug_olc()    # ham vs J hatasini olc
                    # Kiyas HER ZAMAN calisir (drone ucsa da uctmasa da donmaz)
                    _kiyas_guncelle()             # Efe vs Omer filtre kiyasi
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

    # Filtre kiyasi ozeti (Efe vs Omer) - ortalama hata (m)
    with beyin_lock:
        ham_h = list(_kiyas_ham_hata)
        efe_h = list(_kiyas_efe_hata)
        omer_h = list(_kiyas_omer_hata)
        _o_sg = _kiyas_omer.sigma_gnss
        _o_scv = (None if _kiyas_omer.sigma_cv is None
                  else [float(x) for x in np.atleast_1d(_kiyas_omer.sigma_cv)])
        _o_kabul = (sum(_kiyas_omer.log_accept) / len(_kiyas_omer.log_accept)
                    if _kiyas_omer.log_accept else None)
    kiyas = {}
    # Omer teshis: neden iraksiyor? (kalibrasyon + kabul orani + son anlik hata)
    kiyas["omer_dbg"] = {
        "kalibre": _omer_kalibre,
        "sigma_gnss": (round(float(_o_sg), 1) if _o_sg is not None else None),
        "sigma_cv": ([round(v, 1) for v in _o_scv] if _o_scv is not None else None),
        "kabul_oran": (round(_o_kabul, 2) if _o_kabul is not None else None),
        "son_hata_m": (round(omer_h[-1] / 100.0, 1) if omer_h else None),
    }
    if ham_h:
        kiyas["ham_ort_m"] = sum(ham_h) / len(ham_h) / 100.0
    if efe_h:
        kiyas["efe_ort_m"] = sum(efe_h) / len(efe_h) / 100.0
        kiyas["efe_ornek"] = len(efe_h)
    if omer_h:
        kiyas["omer_ort_m"] = sum(omer_h) / len(omer_h) / 100.0
        kiyas["omer_ornek"] = len(omer_h)
    if "efe_ort_m" in kiyas and "omer_ort_m" in kiyas:
        kiyas["kazanan"] = "EFE" if kiyas["efe_ort_m"] <= kiyas["omer_ort_m"] else "OMER"

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
                jpeg = grab_frame_jpeg()
                self._send(200, jpeg, "image/jpeg")
            except Exception as e:
                self._send(500, ("goruntu hatasi: %s" % e).encode("utf-8"),
                           "text/plain; charset=utf-8")
        else:
            self._send(404, b"yok", "text/plain; charset=utf-8")

    def do_POST(self):
        global gorev_aktif
        if self.path == "/api/command":
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length).decode("utf-8") if length else "{}"
            try:
                data = json.loads(raw)
            except Exception:
                data = {}
            cmd = data.get("cmd", "")
            msg = "Bilinmeyen komut"
            if cmd == "start":
                gorev_aktif = True
                msg = "GOREV BASLATILDI - drone hedefe yoneliyor"
            elif cmd == "stop":
                gorev_aktif = False
                # Guvenlik: drone'u durdur (motorlari kes -> arm=False)
                try:
                    drone.set_control_surfaces(0.0, 0.0, 0.0, 0.0, False)
                except Exception:
                    pass
                msg = "GOREV DURDURULDU - drone pasif (motorlar kapali)"
            payload = json.dumps({"ok": True, "msg": msg, "gorev_aktif": gorev_aktif})
            self._send(200, payload.encode("utf-8"), "application/json")
        else:
            self._send(404, b"yok", "text/plain; charset=utf-8")


# ----------------------------------------------------------
#  Ana program
# ----------------------------------------------------------
def main():
    # Arka planda baglanti yoneticisini ve gorev kontrol beynini baslat
    threading.Thread(target=connection_manager, daemon=True).start()
    threading.Thread(target=kontrol_dongusu, daemon=True).start()

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

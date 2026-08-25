# -*- coding: utf-8 -*-
"""
control/main.py — FAZ GÖZETMENİ
"""
import time

from control.visual_tracking import VisualCfg, is_stale, aim_box
from perception import detection_state


class Cfg:
    # --- KALKIS KAPISI ---
    TAKEOFF = True
    TAKEOFF_ALT_M = 45.0         # m; zemine göreli hedef tırmanma yüksekliği
    TAKEOFF_TOL_M = 3.0          # m; kalkış yüksekliği toleransı
    TAKEOFF_TARGET_GAP_M = 20.0  # m; hedefin irtifasinin bu kadar altina gelindiyse tirmanmaya devam etmek gereksiz

    # --- DEVİR KAPISI ---
    CAMERA_ONLY_GATE = False     # Sadece kamera takibi
    HANDOFF_RANGE_M = 20.0       # m; hedefe GPS menzili
    HANDOFF_STATION_ERR_M = 8.0  # m; istasyon hatası bunun altındaysa "oturdu"
    HANDOFF_STATION_TICKS = 25   # ard arda tik (~0.5 s) oturmuş kalmalı
    GPS_STALE_S = 2.0            # s; hedef GNSS paketi bundan eskiyse "bayat"

    # --- GÖRSEL FAZDAN DÖNÜŞ ---
    LOST_S = 2.0                 # s;


class PhaseSupervisor:

    TAKEOFF = "TAKEOFF"
    GPS = "GPS"
    VISUAL = "VISUAL"

    def __init__(self, cfg=Cfg, visual_cfg=VisualCfg):
        self.cfg = cfg
        self.visual_cfg = visual_cfg
        self.reset()

    def reset(self):
        self.phase = self.TAKEOFF if self.cfg.TAKEOFF else self.GPS
        self.handoff_count = 0
        self._lock = 0              # ard arda geçerli kare
        self._lock_since = None     # kesintisiz kanıt zincirinin başlangıç damgası
        self._last_frame_t = None   # son yeni karenin damgası
        self._last_seq = None       # sayaca işlenmiş son kare no
        self._station_ticks = 0     # ard arda "istasyona oturmuş" tik
        self._last_valid_t = None
        self._last_raw = None
        self._last_packet_t = None
        self._message = ""

    # ================================================================
    #  GİRDİ OKUMA
    # ================================================================
    def read_detection(self, t=None):
        """detection_state'ten güdüme girebilecek tespitleri okur -> (det, seq)."""
        t = time.perf_counter() if t is None else t
        det, seq, _ = detection_state.status()
        if is_stale(det, self.visual_cfg, now=t):
            return None, seq
        return aim_box(det, self.visual_cfg), seq

    def _track_packet(self, last_raw, t):
        """Yeni ham GNSS paketi geldiyse zaman damgasını tazeler"""
        if last_raw is not None and last_raw != self._last_raw:
            self._last_raw = last_raw
            self._last_packet_t = t

    def gnss_stale(self, t=None):
        """Hedef GNSS paketi GPS_STALE_S'ten eski mi?"""
        if self._last_packet_t is None:
            return False
        t = time.perf_counter() if t is None else t
        return (t - self._last_packet_t) > self.cfg.GPS_STALE_S

    def _process_frame(self, t, det, seq):
        """Kanıt zincirini sürdürür."""
        if (self._last_frame_t is not None and (t - self._last_frame_t) > self.visual_cfg.STALE_S):
            self._lock = 0
            self._lock_since = None
        if det is None:
            self._lock = 0
            self._lock_since = None
            self._last_seq = seq
            return
        self._last_valid_t = t
        if seq == self._last_seq:
            return
        self._last_seq = seq
        self._last_frame_t = t
        if self._lock_since is None:
            self._lock_since = t
        self._lock += 1

    def _lock_s(self, t):
        """Kesintisiz görsel kanıt süresi (s)."""
        return 0.0 if self._lock_since is None else (t - self._lock_since)

    def _is_locked(self, t):
        """Görsel kilit kuruldu mu?"""
        if self._lock_since is None:
            return False
        if self._lock < self.visual_cfg.HANDOFF_FRAMES:
            return False
        return self._lock_s(t) >= self.visual_cfg.HANDOFF_LOCK_S

    def _is_settled(self, t, station_err, range_h):
        """Araç istasyona oturdu ve hedefe devir menzilinde mi?"""
        if self.cfg.CAMERA_ONLY_GATE:
            return True
        if self.gnss_stale(t):
            return True
        if station_err is None or range_h is None:
            self._station_ticks = 0
            return False
        if (station_err <= self.cfg.HANDOFF_STATION_ERR_M
                and range_h <= self.cfg.HANDOFF_RANGE_M):
            self._station_ticks += 1
        else:
            self._station_ticks = 0
        return self._station_ticks >= self.cfg.HANDOFF_STATION_TICKS

    def _is_climbed(self, height, target_alt_gap):
        """Kalkış bitti mi?"""
        if (target_alt_gap is not None and target_alt_gap >= -self.cfg.TAKEOFF_TARGET_GAP_M):
            return True
        return height >= (self.cfg.TAKEOFF_ALT_M - self.cfg.TAKEOFF_TOL_M)

    # ================================================================
    #  KAPILAR
    # ================================================================
    def takeoff_tick(self, t, height, target_alt_gap=None, det=None, seq=None, last_raw=None):
        self._track_packet(last_raw, t)
        self._process_frame(t, det, seq)
        if not self._is_climbed(height, target_alt_gap):
            return False

        self.phase = self.GPS
        self._message = ("Kalkış tamamlandı (%.0f m)" % height)
        return True

    def gps_tick(self, t, det, seq, station_err=None, range_h=None, last_raw=None):
        self._track_packet(last_raw, t)
        self._process_frame(t, det, seq)
        settled = self._is_settled(t, station_err, range_h)
        if not (self._is_locked(t) and settled):
            return False

        self.phase = self.VISUAL
        self.handoff_count += 1
        distance = ("%.0f m" % range_h) if range_h else "?"
        self._message = ("Görsel temas kuruldu (#%d, menzil %s, kilit %.1f s / %d kare%s) - " % (self.handoff_count, distance, self._lock_s(t), self._lock,
                            "GNSS bayat" if self.gnss_stale(t) else ""))
        return True

    def visual_tick(self, t, det, seq, box_ok, last_raw=None):
        self._track_packet(last_raw, t)
        self._process_frame(t, det, seq)
        if box_ok:
            return False

        lost_s = (t - self._last_valid_t) if self._last_valid_t else 0.0
        if lost_s <= self.cfg.LOST_S:
            return False

        self.phase = self.GPS
        self._lock = 0
        self._lock_since = None
        self._station_ticks = 0
        self._message = ("Hedef %.1f s kayıp. GPS takibine geçildi" % lost_s)
        return True

    # ================================================================
    #  GÖSTERGE
    # ================================================================
    def handoff_message(self):
        return self._message

    def status(self, t=None):
        t = time.perf_counter() if t is None else t
        return {
            "phase": self.phase,
            "lock": self._lock,
            "lock_need": self.visual_cfg.HANDOFF_FRAMES,
            "lock_s": self._lock_s(t),
            "lock_s_need": self.visual_cfg.HANDOFF_LOCK_S,
            "station_ticks": self._station_ticks,
            "station_ticks_need": self.cfg.HANDOFF_STATION_TICKS,
            "handoff_count": self.handoff_count,
            "gnss_stale": self.gnss_stale(t),
            "camera_only_gate": bool(self.cfg.CAMERA_ONLY_GATE),
        }


# ==========================================================
#  MAIN
# ==========================================================
if __name__ == "__main__":
    print("Görevi çalıştırmak için:  python -m web.server ->  http://127.0.0.1:8001")

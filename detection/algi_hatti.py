# -*- coding: utf-8 -*-
"""
================================================================================
ALGI HATTI — tek algi dongusu (YOLO thread'inde, frame-senkron ardisik)
================================================================================
YARISMA PIPELINE FAZ 1. Dosya = sorumluluk, dongu = zamanlama:
Frame-senkron isler (tespit -> takip -> [PnP]) AYNI dongude ardisik calisir;
guduum 50 Hz KENDI thread'inde AlgiCiktisi snapshot'ini lock'lu okur.

  [oyun karesi] -> gorsel_tespit (YOLO: bbox+conf, pose ise +keypoints)
               -> takip (ByteTrack + gyro-CMC -> onayli track)
               -> [talon_pose_estimator (PnP)  — FAZ 2, opsiyonel]
               -> AlgiCiktisi (timestamp'li; lam_dot/Vc BURADA, algi frame
                  timestamp'iyle hesaplanir — turev kurali)

TUREV KURALI (kritik): lam_dot (LOS acisal hizi) ve Vc (kapanma hizi) algi
dongusunde, algi frame timestamp'leriyle hesaplanir. Guduum thread'i HAZIR
degerleri tuketir. Sebep: algi FPS'i guduum frekansinin (50 Hz) altindaysa
guduum ayni olcumu birden fazla kez gorur (zero-order hold); turev guduum
frekansiyla alinirsa sifirlanma/cift-sayim hatasi olur.

GYRO-CMC BESLEME: avci attitude'u frame timestamp'lerine gore alinir; onceki
ve simdiki attitude'dan kamera_model.cmc_homografi ile H kurulur, takip'e verilir
(R_mount tilt otomatik girer). Attitude enterpolasyonu: algi ~30-60 FPS, attitude
tam-hizli/temiz -> her frame en yakin okuma yeterli (agir enterpolasyon gereksiz).

MODEL YOKLUGUNDA (graceful degradation): dedektor hazir degilse AlgiCiktisi.hedef
None kalir (sistem GPS ile ucar). Pose modeli yoksa keypoints gelmez -> PnP pasif.
================================================================================
"""
import threading
import time

import numpy as np

from detection import kamera_model
from detection.takip import Takipci, TakipCfg


class AlgiCiktisi:
    """Algi dongusunun tek atomik ciktisi (guduum lock'lu snapshot okur).
    hedef: takip.Track.cikti() sozlesmesi | None.
    turev: {lam_dot (rad/s), Vc (px/s ~ yaklasim), gecerli} — algi timestamp'iyle."""

    __slots__ = ("t", "hedef", "pnp", "lam_dot", "Vc", "los_aci", "goruntu_wh")

    def __init__(self):
        self.t = None
        self.hedef = None          # {track_id, bbox, cx, cy, conf, keypoints?, tespit_mi, track_durumu}
        self.pnp = None            # FAZ 2: {gecerli, tvec, mesafe, phi_T, psi_T, ...}
        self.lam_dot = 0.0         # LOS acisal hizi (rad/s) — goruntu-duzlemi bearing turevi
        self.Vc = 0.0              # kapanma hizi vekili (bbox buyume orani, 1/s)
        self.los_aci = None        # son LOS acisi (rad; goruntu merkezine gore)
        self.goruntu_wh = None     # (W, H)


class AlgiHatti:
    """Frame-senkron algi hatti. adim(frame, attitude, t) her YOLO tikinde cagrilir;
    thread-guvenli son_cikti() ile guduum snapshot okur."""

    def __init__(self, dedektor=None, takip_cfg=None):
        self.dedektor = dedektor            # HedefDedektor | None (graceful degradation)
        self.takipci = Takipci(takip_cfg or TakipCfg())
        self._lock = threading.Lock()
        self._cikti = AlgiCiktisi()
        self._onceki_att = None             # gyro-CMC: onceki frame attitude (roll,pitch,yaw)
        self._onceki_t = None
        self._onceki_bearing = None         # lam_dot icin
        self._onceki_alan = None            # Vc icin
        self._son_wh = None                 # goruntu boyutu (tespitsiz frame'de de CMC icin)
        self._pnp = None                    # FAZ 2'de talon_pose_estimator baglanir

    def pnp_baglan(self, pnp_kestirici):
        """FAZ 2: PnP kestiricisini tak (None birakilirsa PnP pasif)."""
        self._pnp = pnp_kestirici

    def adim(self, frame, attitude, t=None):
        """Tek algi tiki. frame: BGR ndarray | None. attitude: (roll,pitch,yaw) deg.
        t: frame timestamp (sn; None -> perf_counter). -> AlgiCiktisi (ayni snapshot)."""
        t = time.perf_counter() if t is None else float(t)
        dt = (t - self._onceki_t) if self._onceki_t is not None else 0.02
        if dt <= 0:
            dt = 1e-3

        # 1) TESPIT (YOLO) — tum kutular (takip secer)
        tespitler = []
        W = H = None
        if self.dedektor is not None and getattr(self.dedektor, "hazir", False) and frame is not None:
            tespitler = self.dedektor.tespit_hepsi(frame)
            if tespitler:
                W, H = tespitler[0].get("W"), tespitler[0].get("H")
        if W is None and hasattr(frame, "shape"):        # tespitsiz kare: shape'ten
            H, W = frame.shape[0], frame.shape[1]
        if W is None:                                    # coast/sahte: son bilinen boyut
            if self._son_wh is not None:
                W, H = self._son_wh
        else:
            self._son_wh = (W, H)

        # 2) GYRO-CMC homografisi (onceki->simdiki attitude)
        H_cmc = None
        if (attitude is not None and self._onceki_att is not None
                and W is not None and H is not None):
            try:
                H_cmc = kamera_model.cmc_homografi(W, H, self._onceki_att, attitude)
            except Exception:
                H_cmc = None

        # 3) TAKIP (HybridSort) -> onayli track. Frame SART (HybridSort kendi ECC-CMC'si icin).
        hedef = self.takipci.guncelle(tespitler, dt, H_cmc, frame=frame)

        # 4) PnP (FAZ 2; hedef keypoints'i varsa) — opsiyonel. t verilir ki
        # oryantasyon low-pass'i algi timestamp'iyle calissin.
        pnp = None
        if self._pnp is not None and hedef is not None and hedef.get("keypoints"):
            try:
                pnp = self._pnp.kestir(hedef["keypoints"], attitude, W, H, t)
            except Exception:
                pnp = None

        # 5) TUREVLER (algi timestamp'iyle — turev kurali) yalniz OLCULEN tespitte
        lam_dot, Vc, los_aci = self._turevler(hedef, W, H, dt)

        # 6) atomik snapshot yaz
        yeni = AlgiCiktisi()
        yeni.t = t
        yeni.hedef = hedef
        yeni.pnp = pnp
        yeni.lam_dot = lam_dot
        yeni.Vc = Vc
        yeni.los_aci = los_aci
        yeni.goruntu_wh = (W, H) if W else None
        with self._lock:
            self._cikti = yeni

        self._onceki_att = attitude
        self._onceki_t = t
        return yeni

    def _turevler(self, hedef, W, H, dt):
        """LOS acisal hizi (rad/s) + kapanma vekili Vc (bbox buyume orani, 1/s).
        Yalniz OLCULEN tespitte (tespit_mi) guncellenir; coast'ta son deger tutulur
        (bbox tahmini turev uretmemeli — sartnamenin kilit tanimina durustluk)."""
        if hedef is None or not hedef.get("tespit_mi") or W is None:
            self._onceki_bearing = None      # kayip -> turev serisini resetle
            self._onceki_alan = None
            return 0.0, 0.0, (self.son_cikti().los_aci)
        cx, cy = hedef["cx"], hedef["cy"]
        # goruntu merkezine gore bearing (LOS acisi, atan2). Tilt telafisi guduumde;
        # burada goruntu-duzlemi acisal hizi yeterli (isaret guduumde ayarlanir).
        bearing = np.arctan2(cy - H / 2.0, cx - W / 2.0)
        alan = hedef["w"] * hedef["h"]
        lam_dot = 0.0
        Vc = 0.0
        if self._onceki_bearing is not None:
            dbear = (bearing - self._onceki_bearing + np.pi) % (2 * np.pi) - np.pi
            lam_dot = float(dbear / dt)
        if self._onceki_alan is not None and self._onceki_alan > 1e-6:
            # bbox buyume orani ~ kapanma vekili: dA/A / dt (yaklasirken alan buyur)
            Vc = float((alan - self._onceki_alan) / self._onceki_alan / dt)
        self._onceki_bearing = bearing
        self._onceki_alan = alan
        return lam_dot, Vc, float(bearing)

    def son_cikti(self):
        """Thread-guvenli son AlgiCiktisi snapshot'i (guduum thread'i cagirir)."""
        with self._lock:
            return self._cikti

    def sifirla(self):
        self.takipci.sifirla()
        self._onceki_att = self._onceki_t = None
        self._onceki_bearing = self._onceki_alan = None
        self._son_wh = None
        with self._lock:
            self._cikti = AlgiCiktisi()

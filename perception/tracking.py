# -*- coding: utf-8 -*-
"""
perception/tracking.py — HybridSort (boxmot) ile kareler-arasi kimlik surekliligi.

Dedektor TEK kareyi gorur; takipci kareler ARASI kimligi surdurur: kisa tespit
bosluklarini Kalman ongorusuyle koprular (max_age), zayif tespitleri BYTE
eslesmesiyle degerlendirir (use_byte + low_thresh) ve tek-kare parazitin izi
kapmasini engeller (min_hits).

Bu sarmalayici tek-hedef sozlesmesi sunar:
    Takipci().guncelle(tespitler, frame) -> en iyi (en guvenli) iz | None

Cikti yalnizca O KARDE OLCULEN izleri icerir (coast/tahmin kutusu yayinlanmaz):
guduum ancak gercek gorsel temasla komut uretsin; tespit deliklerini gorsel faz
kendi bayatlik esigiyle (control.gorsel_takip.Cfg.STALE_S) yonetir.

DAYANIKLILIK: boxmot kurulu degilse hazir=False -> guncelle() ham argmax kutusunu
dondurur (takip katmani devre disi, sistem calismaya devam eder).
"""
import numpy as np

# Takipci parametreleri (boxmot HybridSort varsayilanlari; sim karesinde denendi).
TRACKER_PARAMS = {
    # BaseTracker
    "det_thresh": 0.3, "max_age": 30, "max_obs": 50, "min_hits": 3,
    "iou_threshold": 0.3, "asso_func": "iou",
    # HybridSort
    "with_reid": False, "low_thresh": 0.1, "delta_t": 3, "inertia": 0.05,
    "use_byte": True, "longterm_bank_length": 30, "alpha": 0.9, "track_thresh": 0.5,
    "EG_weight_high_score": 4.6, "EG_weight_low_score": 1.3,
    "TCM_first_step": True, "TCM_byte_step": True, "TCM_byte_step_weight": 1.0,
    "high_score_matching_thresh": 0.7, "with_longterm_reid": True,
    "longterm_reid_weight": 0.0, "with_longterm_reid_correction": True,
    "longterm_reid_correction_thresh": 0.4, "longterm_reid_correction_thresh_low": 0.4,
}
CMC_METHOD = "ecc"      # kamera-hareket telafisi (HybridSort kendi karesiyle yapar)


def _hybridsort_sinifi():
    """boxmot surumleri arasinda modul yolu degisti — sirayla dene."""
    try:                                   # v19+
        from boxmot.trackers.bbox.hybridsort.hybridsort import HybridSort
        return HybridSort
    except ImportError:
        pass
    from boxmot.trackers.hybridsort.hybridsort import HybridSort   # eski duzen
    return HybridSort


def _sessizlestir():
    """ECC "did not converge" gibi kare basi WARNING selini keser (dokusu az
    gokyuzu karelerinde her karede basar). ERROR gorunmeye devam eder.
    DIKKAT: boxmot kendi logger'ini kurarken seviyeyi INFO'ya geri cekiyor ->
    bu cagri tracker OLUSTURULDUKTAN SONRA yapilmali."""
    import logging
    logging.getLogger("boxmot").setLevel(logging.ERROR)


class Takipci:

    def __init__(self):
        self.hazir = False
        self.hata = None
        self._tr = None
        self.trackler = []
        self.sifirla()

    def sifirla(self):
        """Yeni gorev: bayat iz/kimlikle baslamasin."""
        self.trackler = []
        try:
            HybridSort = _hybridsort_sinifi()
            self._tr = HybridSort(reid_model=None, cmc_method=CMC_METHOD, **TRACKER_PARAMS)
            _sessizlestir()
            self.hazir = True
        except Exception as e:
            self._tr = None
            self.hazir = False
            self.hata = repr(e)

    def guncelle(self, tespitler, frame):
        """tespitler: detector.tespit_hepsi ciktisi (PIKSEL); frame: BGR ndarray.
        -> en iyi iz dict {track_id, cx, cy, w, h, conf, W, H, t} | None"""
        if not self.hazir or frame is None or not hasattr(frame, "shape"):
            self.trackler = []
            return tespitler[0] if tespitler else None      # takip yok -> ham argmax

        if tespitler:
            arr = np.empty((len(tespitler), 6), dtype=np.float32)
            for i, d in enumerate(tespitler):
                cx, cy, w, h = float(d["cx"]), float(d["cy"]), float(d["w"]), float(d["h"])
                arr[i] = (cx - w / 2.0, cy - h / 2.0, cx + w / 2.0, cy + h / 2.0,
                          float(d.get("conf", 0.9)), float(d.get("cls", 0)))
        else:
            arr = np.empty((0, 6), dtype=np.float32)

        try:
            out = np.asarray(self._tr.update(arr, frame))
        except Exception:
            self.trackler = []
            return None
        self.trackler = out.tolist() if len(out) else []
        if not len(out):
            return None

        best = out[int(np.argmax(out[:, 5]))]        # en yuksek conf'lu iz
        x1, y1, x2, y2, tid, conf, cls, ind = [float(v) for v in best]
        cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0

        # Eslesen ORIJINAL tespitten kare olculerini/zaman damgasini tasi.
        src = None
        ii = int(round(ind))
        if tespitler and 0 <= ii < len(tespitler):
            src = tespitler[ii]
        d = {"track_id": int(round(tid)),
             "cx": cx, "cy": cy, "w": x2 - x1, "h": y2 - y1, "conf": conf,
             "cls": int(round(cls)),
             "W": int(src["W"]) if src else int(frame.shape[1]),
             "H": int(src["H"]) if src else int(frame.shape[0])}
        if src is not None and "t" in src:
            d["t"] = src["t"]
        return d

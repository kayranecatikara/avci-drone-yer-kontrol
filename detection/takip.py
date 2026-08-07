# -*- coding: utf-8 -*-
"""
================================================================================
TAKIP — HybridSort (boxmot) adaptoru
================================================================================
2026-07-09 (kullanici karari): eski EL-YAZIMI ByteTrack + gyro-CMC KALDIRILDI,
yerine boxmot kutuphanesinin HybridSort'u geldi (kullanicinin hybridsort_tracker.py
dosyasindaki TRACKER_PARAMS birebir). HybridSort: observation-centric SORT +
uzun-donem izleme + (opsiyonel) ReID; burada with_reid=False (yalniz hareket) ve
ECC tabanli kamera-hareket telafisi (kendi frame'iyle; ~3.5 ms/kare, ihmal edilir).

Bu modul, sistemin geri kalani DEGISMESIN diye eski `Takipci` + `TakipCfg`
ARAYUZUNU korur:
  - Takipci().guncelle(tespitler, dt, H_cmc, cmc_max_kaydirma, frame) -> en iyi track dict | None
  - Takipci().sifirla(), .trackler (bool kontrolu), .cfg.CONF_DUSUK (predict esigi)
DIKKAT: HybridSort kareyi (frame=bgr) ISTER -> server ve algi_hatti gecirir.
dt / H_cmc / cmc_max_kaydirma YOK SAYILIR (HybridSort kendi Kalman + ECC-CMC'sini
kullanir). Bos tespitte HybridSort track dondurmez (coast ciktisi yok) -> None;
delik yonetimi ana_kontrol KOPRU'sunde (goruntu-duzlemi olu-hesap) kalir.
================================================================================
"""
import numpy as np

# Kullanicinin hybridsort_tracker.py'sindeki TRACKER_PARAMS (birebir) + cmc.
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
CMC_METHOD = "ecc"      # kamera-hareket telafisi (ecc|orb|sift|sof); ecc = HybridSort varsayilani


class TakipCfg:
    """Eski API uyumu: server `takipci.cfg.CONF_DUSUK`'u predict esiginde kullanir
    (dusuk-conf kutular HybridSort'un BYTE ikinci turuna girsin diye taban dusuk)."""
    CONF_YUKSEK = float(TRACKER_PARAMS["track_thresh"])   # 0.5
    CONF_DUSUK  = float(TRACKER_PARAMS["low_thresh"])      # 0.1


class Takipci:
    """boxmot HybridSort'u eski Takipci arayuzune saran adaptor."""

    def __init__(self, cfg=None):
        self.cfg = cfg or TakipCfg()
        self._tr = None
        self.trackler = []          # server 'if takipci.trackler' ile bos-mu diye bakar
        self.sifirla()

    def sifirla(self):
        # Lazy import: modul yuklenirken agir boxmot'u cekme; ilk tracker'da yukle.
        # boxmot 22.x yerlesimi: hybridsort paket DEGIL tek modul (.../bbox/hybridsort.py).
        from boxmot.trackers.bbox.hybridsort import HybridSort
        self._tr = HybridSort(reid_model=None, cmc_method=CMC_METHOD, **TRACKER_PARAMS)
        self.trackler = []

    def guncelle(self, tespitler, dt=None, H_cmc=None, cmc_max_kaydirma=None, frame=None):
        """tespitler: [{cx,cy,w,h,conf,cls?,W,H,t?,keypoints?}] (PIKSEL); frame: bgr (SART).
        -> en iyi (en yuksek conf) track dict | None. dt/H_cmc/cmc_max_kaydirma yok sayilir."""
        if frame is None or not hasattr(frame, "shape"):
            self.trackler = []
            return None
        Wf, Hf = int(frame.shape[1]), int(frame.shape[0])
        # tespitler -> boxmot Nx6 [x1,y1,x2,y2,conf,cls]
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

        # TEK-HEDEF sozlesmesi: en yuksek conf'lu track (eski en_iyi_cikti muadili).
        best = out[int(np.argmax(out[:, 5]))]
        x1, y1, x2, y2, tid, conf, cls, ind = [float(v) for v in best]
        cx = (x1 + x2) / 2.0; cy = (y1 + y2) / 2.0; w = x2 - x1; h = y2 - y1

        # Eslesen ORIJINAL tespitten ekstra alanlari tasi (W/H/t/keypoints/cls).
        src = None
        ii = int(round(ind))
        if tespitler and 0 <= ii < len(tespitler):
            src = tespitler[ii]
        W = int(src.get("W", Wf)) if src else Wf
        H = int(src.get("H", Hf)) if src else Hf
        d = {"track_id": int(round(tid)), "bbox": (cx, cy, w, h),
             "cx": cx, "cy": cy, "w": w, "h": h, "conf": conf,
             "tespit_mi": True, "track_durumu": "CONFIRMED",   # HybridSort ciktisi = OLCULEN iz
             "W": W, "H": H, "cls": int(round(cls))}
        if src is not None:
            if "t" in src:
                d["t"] = src["t"]
            kp = src.get("keypoints")
            if kp is not None:
                d["keypoints"] = kp
        return d

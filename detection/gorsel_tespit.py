# -*- coding: utf-8 -*-
"""
HAMIDIYE - GORSEL TESPIT (YOLO best.pt inference sarmalayici)
================================================================================
best.pt'yi yukler, bir kareden EN-YUKSEK-conf bbox'i dondurur. Agir inference
AYRI thread'de kosar (server.py:dedektor_dongusu); bu modul sadece "model + tek
kare -> bbox" isini yapar.

DAYANIKLILIK: ultralytics/torch KURULU DEGILSE veya model yuklenemezse sessizce
`hazir=False` olur ve `tespit_et()` hep None doner -> sistem GPS ile calismaya
DEVAM eder (gorsel faz devreye girmez, ama cokme YOK). requirements.txt'e
ultralytics + torch (CUDA wheel) eklenmeli; model models/best.pt'de durur.

Renk notu: ultralytics numpy diziyi BGR varsayar; web.server.grab_frame_bgr() BGR
ndarray dondurdugunden dogrudan gecmek DOGRU renktir (PIL RGB de kabul edilir).
"""


class HedefDedektor:

    _nan_uyarildi = False        # nan/inf kutu ilk elendiginde bir kez uyar (FP16 tasma teshisi)

    def __init__(self, model_path, conf=0.35, imgsz=640, device=None, half=None):
        self.hazir = False
        self.model = None
        self.names = {}
        self.conf = float(conf)
        self.imgsz = int(imgsz)
        self.device = device
        self.half = half
        self._q = {}                                     # FP16 predict kwarg (bir kez sabitlenir)
        self.hata = None
        try:
            from ultralytics import YOLO
            if self.device is None:                       # cihaz otomatik: cuda varsa GPU 0
                try:
                    import torch
                    self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
                except Exception:
                    self.device = "cpu"
            # NOT (GTX 1650 Ti, 2026-07-08 olcum): FP16 bu kartta hem YAVAS (115 vs 40 ms) hem
            # nan kutu uretiyor (regresyon tasmasi) -> VARSAYILAN FP32 (half=False). FP16'yi
            # zorlamak icin half=True gecir (onerilmez). CPU'da da FP16 zaten kapali.
            if self.half is None:
                self.half = False
            self.model = YOLO(model_path)
            self.names = dict(getattr(self.model, "names", {}) or {})
            # FP16 kwarg: ultralytics >= 8.4 'quantize=fp16' (deprecated 'half' HER karede
            # uyari basar -> spam). Bir kez yoklanir; eski surumde 'half=True'e duser.
            if self.half:
                try:
                    import numpy as _np
                    self.model.predict(_np.zeros((32, 32, 3), "uint8"), imgsz=32,
                                       device=self.device, quantize="fp16", verbose=False)
                    self._q = {"quantize": "fp16"}
                except Exception:
                    self._q = {"half": True}
            self.hazir = True
            self._warmup()                                # ilk predict yavas -> onceden isit
        except Exception as e:
            self.hazir = False
            self.hata = repr(e)                           # neden yuklenemedi (log icin)

    def _warmup(self):
        try:
            import numpy as np
            bos = np.zeros((self.imgsz, self.imgsz, 3), dtype="uint8")
            self.model.predict(bos, imgsz=self.imgsz, conf=self.conf,
                               device=self.device, verbose=False, **self._q)
        except Exception:
            pass

    @staticmethod
    def _maskede(cxn, cyn, maske):
        """Normalize merkez (cxn,cyn) verilen dikdortgenlerden birinin ICINDE mi?
        maske: [(x0,y0,x1,y1), ...] normalize (0..1). None/bos -> False."""
        if not maske:
            return False
        for r in maske:
            try:
                x0, y0, x1, y1 = r
            except Exception:
                continue
            if x0 <= cxn <= x1 and y0 <= cyn <= y1:
                return True
        return False

    def tespit_et(self, frame, maske=None):
        """frame: PIL Image (RGB, tercih) veya ndarray. -> en-yuksek-conf bbox dict | None.
        dict: {cx,cy,w,h,conf,cls,W,H,t}  (px + perf_counter zaman damgasi).
        maske: PERVANE bolgeleri [(x0,y0,x1,y1),...] normalize; MERKEZI icinde olan
        kutular ELENIR (argmax ONCESI) -> kendi pervanemiz hedef sanilmaz. Tum kutular
        maskeliyse None doner (o kare tespit yok)."""
        if not self.hazir:
            return None
        import time as _t
        import math as _m
        try:
            res = self.model.predict(frame, imgsz=self.imgsz, conf=self.conf,
                                     device=self.device, verbose=False, **self._q)[0]
        except Exception:
            return None
        boxes = getattr(res, "boxes", None)
        if boxes is None or len(boxes) == 0:
            return None
        try:
            H, W = int(res.orig_shape[0]), int(res.orig_shape[1])
            confs = boxes.conf
            xyxy = boxes.xyxy
            cls_t = boxes.cls
            # PERVANE MASKESI: merkezi maskede olan kutulari ele, kalanlardan en-yuksek conf.
            en_i, en_c = -1, -1.0
            for j in range(len(confs)):
                x1, y1, x2, y2 = [float(v) for v in xyxy[j]]
                if not (_m.isfinite(x1) and _m.isfinite(y1) and _m.isfinite(x2) and _m.isfinite(y2)):
                    if not HedefDedektor._nan_uyarildi:   # bir kez uyar (FP16 tasma teshisi)
                        HedefDedektor._nan_uyarildi = True
                        print("[GORSEL] UYARI: nan/inf koordinatli kutu elendi -> gudume/CSV'ye "
                              "GITMEZ. Surerse FP16 sorunudur (HedefDedektor half=False -> FP32).")
                    continue                              # bozuk kutu -> ELE (argmax'a girmez)
                if maske and W > 0 and H > 0:
                    cxn = ((x1 + x2) / 2.0) / W
                    cyn = ((y1 + y2) / 2.0) / H
                    if self._maskede(cxn, cyn, maske):
                        continue                          # kendi pervanemiz -> atla
                c = float(confs[j])
                if c > en_c:
                    en_c, en_i = c, j
            if en_i < 0:                                   # tum kutular maskeli -> tespit yok
                return None
            x1, y1, x2, y2 = [float(v) for v in xyxy[en_i]]
            cls = int(cls_t[en_i]) if cls_t is not None else -1
            return {
                "cx": (x1 + x2) / 2.0, "cy": (y1 + y2) / 2.0,
                "w": (x2 - x1), "h": (y2 - y1),
                "conf": float(confs[en_i]), "cls": cls,
                "W": W, "H": H, "t": _t.perf_counter(),
            }
        except Exception:
            return None


def siniflar(model_path):
    """DOGRULAMA yardimcisi: best.pt siniflarini (model.names) yazdir."""
    try:
        from ultralytics import YOLO
        m = YOLO(model_path)
        print("best.pt siniflari (model.names):", dict(m.names))
        return dict(m.names)
    except Exception as e:
        print("YOLO yuklenemedi:", repr(e))
        return None


if __name__ == "__main__":
    import os
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # depo koku
    siniflar(os.path.join(_root, "models", "best.pt"))

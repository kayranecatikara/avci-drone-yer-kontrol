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

    def __init__(self, model_path, conf=0.35, imgsz=640, device=None):
        self.hazir = False
        self.model = None
        self.names = {}
        self.conf = float(conf)
        self.imgsz = int(imgsz)
        self.device = device
        self.hata = None
        try:
            from ultralytics import YOLO
            if self.device is None:                       # cihaz otomatik: cuda varsa kullan
                try:
                    import torch
                    self.device = "cuda" if torch.cuda.is_available() else "cpu"
                except Exception:
                    self.device = "cpu"
            self.model = YOLO(model_path)
            self.names = dict(getattr(self.model, "names", {}) or {})
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
                               device=self.device, verbose=False)
        except Exception:
            pass

    def tespit_et(self, frame):
        """frame: PIL Image (RGB, tercih) veya ndarray. -> en-yuksek-conf bbox dict | None.
        dict: {cx,cy,w,h,conf,cls,W,H,t}  (px + perf_counter zaman damgasi)."""
        if not self.hazir:
            return None
        import time as _t
        try:
            res = self.model.predict(frame, imgsz=self.imgsz, conf=self.conf,
                                     device=self.device, verbose=False)[0]
        except Exception:
            return None
        boxes = getattr(res, "boxes", None)
        if boxes is None or len(boxes) == 0:
            return None
        try:
            confs = boxes.conf
            i = int(confs.argmax())                       # EN-YUKSEK-conf kutu (sinif-agnostik)
            x1, y1, x2, y2 = [float(v) for v in boxes.xyxy[i]]
            cls = int(boxes.cls[i]) if boxes.cls is not None else -1
            H, W = int(res.orig_shape[0]), int(res.orig_shape[1])
            return {
                "cx": (x1 + x2) / 2.0, "cy": (y1 + y2) / 2.0,
                "w": (x2 - x1), "h": (y2 - y1),
                "conf": float(confs[i]), "cls": cls,
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

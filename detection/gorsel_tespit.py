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
        self.task = None            # 'detect' | 'pose' (yukleme sonrasi)
        self.kpt_shape = None       # pose ise (n, dim); PnP [6,3] bekler
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
            self.task = getattr(self.model, "task", None)
            if self.task == "pose":
                ks = getattr(getattr(self.model, "model", None), "kpt_shape", None)
                self.kpt_shape = tuple(ks) if ks is not None else None
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
        hepsi = self.tespit_hepsi(frame, maske=maske)
        return hepsi[0] if hepsi else None

    def tespit_hepsi(self, frame, maske=None):
        """Karedeki TUM tespitler, conf'a gore AZALAN sirali liste (bos olabilir).
        Cok-nesneli sahnede (orn. park etmis ikinci Talon) cagiranin SECIM
        yapabilmesi icin; uretim tek-kutu API'si (tespit_et) ilk elemani alir,
        davranisi degismez. Eleman semasi tespit_et ile ayni; pose modelinde her
        kutuya 'keypoints' [[x,y,conf],...] eklenir (detect modelinde alan yok).
        maske: pervane bolgeleri — merkezi maskede olan kutular listeye GIRMEZ."""
        if not self.hazir:
            return []
        import time as _t
        import numpy as np
        try:
            res = self.model.predict(frame, imgsz=self.imgsz, conf=self.conf,
                                     device=self.device, verbose=False)[0]
        except Exception:
            return []
        boxes = getattr(res, "boxes", None)
        if boxes is None or len(boxes) == 0:
            return []
        try:
            H, W = int(res.orig_shape[0]), int(res.orig_shape[1])
            t = _t.perf_counter()
            # POSE modeli ise keypoints da gelir (pose'suz detect modelinde None ->
            # PnP tuketicisi otomatik pasif). Her kutuya kendi keypoint setini esle.
            kpts = getattr(res, "keypoints", None)
            kp_xy = kp_conf = None
            if kpts is not None:
                try:
                    kp_xy = kpts.xy.cpu().numpy() if hasattr(kpts.xy, "cpu") else np.asarray(kpts.xy)
                    kc = getattr(kpts, "conf", None)
                    if kc is not None:
                        kp_conf = kc.cpu().numpy() if hasattr(kc, "cpu") else np.asarray(kc)
                except Exception:
                    kp_xy = kp_conf = None
            cikti = []
            for i in range(len(boxes)):
                x1, y1, x2, y2 = [float(v) for v in boxes.xyxy[i]]
                # PERVANE MASKESI: merkezi maskede olan kutu listeye girmez.
                if maske and W > 0 and H > 0:
                    cxn = ((x1 + x2) / 2.0) / W
                    cyn = ((y1 + y2) / 2.0) / H
                    if self._maskede(cxn, cyn, maske):
                        continue                          # kendi pervanemiz -> atla
                d = {
                    "cx": (x1 + x2) / 2.0, "cy": (y1 + y2) / 2.0,
                    "w": (x2 - x1), "h": (y2 - y1),
                    "conf": float(boxes.conf[i]),
                    "cls": int(boxes.cls[i]) if boxes.cls is not None else -1,
                    "W": W, "H": H, "t": t,
                }
                if kp_xy is not None and i < len(kp_xy):
                    # [[x,y,conf], ...] biciminde (PnP tuketicisi bekler)
                    if kp_conf is not None and i < len(kp_conf):
                        d["keypoints"] = [[float(x), float(y), float(c)]
                                          for (x, y), c in zip(kp_xy[i], kp_conf[i])]
                    else:
                        d["keypoints"] = [[float(x), float(y), 1.0] for x, y in kp_xy[i]]
                cikti.append(d)
            cikti.sort(key=lambda d: -d["conf"])
            return cikti
        except Exception:
            return []


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

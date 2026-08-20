# -*- coding: utf-8 -*-
"""
perception/detector.py — YOLO tabanli hedef (Talon) tespiti.

    HedefDedektor(model_yolu).tespit_hepsi(bgr) -> [{cx,cy,w,h,conf,cls,W,H,t}, ...]
                                                   (conf'a gore AZALAN sirali)

Model: perception/models/best.pt (task=detect, tek sinif: talon).

DAYANIKLILIK: ultralytics/torch kurulu degilse veya model yuklenemezse sessizce
`hazir=False` olur ve tespit hep bos doner -> sistem GPS fazinda calismaya DEVAM
eder (gorsel faz devreye girmez, ama cokme yok).

Renk notu: ultralytics numpy diziyi BGR varsayar; camera.py BGR ndarray uretir
-> dogrudan gecmek DOGRU renktir.

PERVANE MASKESI: avcinin KENDI pervanesi arada bir "ucak" olarak algilaniyor ve
kadrajda SABIT bir bolgede duruyor. Merkezi maskede kalan kutular listeye hic
girmez (secim ONCESI elenir) -> kendi pervanemiz hedef sanilmaz.
"""
import os
import time

# Kadrajda kendi pervanemizin gorunduğu normalize bolgeler [(x0,y0,x1,y1), ...].
# Canli FPV'de maske pervaneyi tam ortmuyorsa bu listeyi duzenle.
PROP_MASKE = [(0.80, 0.55, 1.0, 0.95)]

MODEL_YOLU = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "models", "best.pt")

# Predict esigi: guduum kapisi (control.gorsel_takip.Cfg.CONF_MIN) bunun USTUNDE
# calisir. Taban dusuk tutulur ki takipci (HybridSort/BYTE) zayif kutularla mevcut
# izi yasatabilsin — dusuk-conf kutu yeni iz ACAMAZ.
CONF_TABAN = 0.10

# Aktif model 640'ta egitildi -> native cozunurluk. Model 1280'de egitilmis bir
# agirlikla degistirilirse burayi da degistir (yoksa uzak/kucuk hedef kaybolur).
IMGSZ = 640


class HedefDedektor:

    def __init__(self, model_path=MODEL_YOLU, conf=CONF_TABAN, imgsz=IMGSZ,
                 device=None, half=None):
        self.hazir = False
        self.model = None
        self.names = {}
        self.conf = float(conf)
        self.imgsz = int(imgsz)
        self.device = device
        self.half = half            # FP16 (None -> cuda'da otomatik AC, cpu'da kapali)
        self._fp16_kwargs = {}
        self.hata = None
        try:
            from ultralytics import YOLO
            if self.device is None:
                try:
                    import torch
                    self.device = "cuda" if torch.cuda.is_available() else "cpu"
                except Exception:
                    self.device = "cpu"
            if self.half is None:
                self.half = (self.device == "cuda")
            self.model = YOLO(model_path)
            self.names = dict(getattr(self.model, "names", {}) or {})
            self.hazir = True
            self._isit()
        except Exception as e:
            self.hazir = False
            self.hata = repr(e)

    def _isit(self):
        """Ilk predict yavastir -> onceden isit. Ayni anda FP16 API'sini sec:
        yeni ultralytics `quantize="fp16"`, eskisinde bu arg YOK -> `half=True`."""
        try:
            import numpy as np
            bos = np.zeros((self.imgsz, self.imgsz, 3), dtype="uint8")
            adaylar = ([{"quantize": "fp16"}, {"half": True}] if self.half else [{}])
            for kw in adaylar:
                try:
                    self.model.predict(bos, imgsz=self.imgsz, conf=self.conf,
                                       device=self.device, verbose=False, **kw)
                    self._fp16_kwargs = kw
                    return
                except TypeError:
                    continue
            self._fp16_kwargs = {}
            self.model.predict(bos, imgsz=self.imgsz, conf=self.conf,
                               device=self.device, verbose=False)
        except Exception:
            pass

    @staticmethod
    def _maskede(cxn, cyn, maske):
        """Normalize merkez verilen dikdortgenlerden birinin ICINDE mi?"""
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

    def tespit_hepsi(self, frame, maske=PROP_MASKE):
        """Karedeki TUM tespitler, conf'a gore AZALAN sirali (bos olabilir)."""
        if not self.hazir or frame is None:
            return []
        try:
            res = self.model.predict(frame, imgsz=self.imgsz, conf=self.conf,
                                     device=self.device, verbose=False,
                                     **self._fp16_kwargs)[0]
        except Exception:
            return []
        boxes = getattr(res, "boxes", None)
        if boxes is None or len(boxes) == 0:
            return []
        try:
            H, W = int(res.orig_shape[0]), int(res.orig_shape[1])
            t = time.perf_counter()
            cikti = []
            for i in range(len(boxes)):
                x1, y1, x2, y2 = [float(v) for v in boxes.xyxy[i]]
                if maske and W > 0 and H > 0:
                    if self._maskede(((x1 + x2) / 2.0) / W, ((y1 + y2) / 2.0) / H, maske):
                        continue                      # kendi pervanemiz -> atla
                cikti.append({
                    "cx": (x1 + x2) / 2.0, "cy": (y1 + y2) / 2.0,
                    "w": (x2 - x1), "h": (y2 - y1),
                    "conf": float(boxes.conf[i]),
                    "cls": int(boxes.cls[i]) if boxes.cls is not None else -1,
                    "W": W, "H": H, "t": t,
                })
            cikti.sort(key=lambda d: -d["conf"])
            return cikti
        except Exception:
            return []

    def tespit_et(self, frame, maske=PROP_MASKE):
        """En yuksek guvenli tek kutu (yoksa None)."""
        hepsi = self.tespit_hepsi(frame, maske=maske)
        return hepsi[0] if hepsi else None

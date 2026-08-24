# -*- coding: utf-8 -*-
"""
perception/detector.py — YOLO tabanli hedef (Talon) tespiti.

    TargetDetector(model_yolu).detect_all(bgr) -> [{cx,cy,w,h,conf,cls,W,H,t}, ...]
                                                   (conf'a gore AZALAN sirali)

Model: perception/models/talon_v3.pt (task=detect, tek sinif: talon).
Ortam degiskeniyle degistirilebilir: AVCI_MODEL=... / AVCI_IMGSZ=...

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
PROP_MASK = [(0.80, 0.55, 1.0, 0.95)]

_MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")

# ⭐ AKTIF MODEL: talon_v3.pt (2026-08-15, 60 epoch, ultralytics 8.4.83).
#   Onceki best.pt (2026-07-07, 200 epoch, 8.4.90) DEPODA DURUYOR ve tek
#   degisken ile geri alinabilir:  AVCI_MODEL=best.pt
#   Ikisi de yolo11s tabanli, task=detect, TEK sinif ("talon") -> sinif
#   indisleri ayni; asagidaki hicbir mantik degismez.
#
# ⛔ MODEL DEGISINCE IKI SEY DE DEGISIR, unutulursa sessizce bozulur:
#   1) IMGSZ — egitim cozunurlugu (asagi bak).
#   2) control/visual_tracking.py :: RANGE_C_REF — menzil kestirimi kutu
#      BOYUTUNDAN turer, kutu boyutu ise modelin kutulama sikiligina baglidir.
#      Farkli sikilikta kutulayan bir model tum menzilleri kaydirir ve
#      aim_box'nun 3-50 m kapisi yanlis yerde acilir/kapanir.
_DEFAULT_MODEL = "talon_v3.pt"
MODEL_PATH = os.path.join(_MODEL_DIR,
                          os.environ.get("AVCI_MODEL", _DEFAULT_MODEL))

# Predict esigi: guduum kapisi (control.visual_tracking.Cfg.CONF_MIN) bunun USTUNDE
# calisir. Taban dusuk tutulur ki takipci (HybridSort/BYTE) zayif kutularla mevcut
# izi yasatabilsin — dusuk-conf kutu yeni iz ACAMAZ.
CONF_FLOOR = 0.10

# ⛔ EGITIM COZUNURLUGU — MODELE BAGLIDIR, sabit degildir.
#   Checkpoint metadata'sindan OKUNDU (train_args.imgsz):
#       talon_v3.pt -> 960      <- AKTIF
#       best.pt     -> 640
#   Modeli degistirip burayi unutmak SESSIZ bir bozulmadir: cikarim egitimden
#   farkli olcekte kosar, uzak/kucuk hedef once kaybolur (kutu hic cikmaz),
#   sonra gorsel faz hic acilmaz. Bu yuzden varsayilan MODELDEN turetilir.
_IMGSZ_BY_MODEL = {"talon_v3.pt": 960, "best.pt": 640}
IMGSZ = int(os.environ.get(
    "AVCI_IMGSZ",
    _IMGSZ_BY_MODEL.get(os.path.basename(MODEL_PATH), 640)))


class TargetDetector:

    def __init__(self, model_path=MODEL_PATH, conf=CONF_FLOOR, imgsz=IMGSZ,
                 device=None, half=None):
        self.ready = False
        self.model = None
        self.names = {}
        self.conf = float(conf)
        self.imgsz = int(imgsz)
        self.device = device
        self.half = half  # FP16 (None -> cuda'da otomatik AC, cpu'da kapali)
        self._fp16_kwargs = {}
        self.error = None
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
            self.ready = True
            self._warmup()
        except Exception as e:
            self.ready = False
            self.error = repr(e)

    def _warmup(self):
        """Ilk predict yavastir -> onceden isit. Ayni anda FP16 API'sini sec:
        yeni ultralytics `quantize="fp16"`, eskisinde bu arg YOK -> `half=True`."""
        try:
            import numpy as np
            blank = np.zeros((self.imgsz, self.imgsz, 3), dtype="uint8")
            candidates = ([{"quantize": "fp16"}, {"half": True}] if self.half else [{}])
            for kw in candidates:
                try:
                    self.model.predict(blank, imgsz=self.imgsz, conf=self.conf,
                                       device=self.device, verbose=False, **kw)
                    self._fp16_kwargs = kw
                    return
                except TypeError:
                    continue
            self._fp16_kwargs = {}
            self.model.predict(blank, imgsz=self.imgsz, conf=self.conf,
                               device=self.device, verbose=False)
        except Exception:
            pass

    @staticmethod
    def _in_mask(cxn, cyn, mask):
        """Normalize merkez verilen dikdortgenlerden birinin ICINDE mi?"""
        if not mask:
            return False
        for r in mask:
            try:
                x0, y0, x1, y1 = r
            except Exception:
                continue
            if x0 <= cxn <= x1 and y0 <= cyn <= y1:
                return True
        return False

    def detect_all(self, frame, mask=PROP_MASK):
        """Karedeki TUM tespitler, conf'a gore AZALAN sirali (bos olabilir)."""
        if not self.ready or frame is None:
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
            out = []
            for i in range(len(boxes)):
                x1, y1, x2, y2 = [float(v) for v in boxes.xyxy[i]]
                if mask and W > 0 and H > 0:
                    if self._in_mask(((x1 + x2) / 2.0) / W, ((y1 + y2) / 2.0) / H, mask):
                        continue  # kendi pervanemiz -> atla
                out.append({
                    "cx": (x1 + x2) / 2.0, "cy": (y1 + y2) / 2.0,
                    "w": (x2 - x1), "h": (y2 - y1),
                    "conf": float(boxes.conf[i]),
                    "cls": int(boxes.cls[i]) if boxes.cls is not None else -1,
                    "W": W, "H": H, "t": t,
                })
            out.sort(key=lambda d: -d["conf"])
            return out
        except Exception:
            return []


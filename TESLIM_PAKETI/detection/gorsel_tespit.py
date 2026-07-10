# -*- coding: utf-8 -*-
"""YOLO best.pt sarmalayici: bir kareden en-yuksek-conf bbox'i dondurur.
Model yuklenemezse hazir=False ve tespit_et() None doner (sistem GPS ile devam eder)."""


class HedefDedektor:

    def __init__(self, model_path, conf=0.35, imgsz=640, device=None, half=None,
                 sahi=False, sahi_dilim=640, sahi_ortusme=0.2, sahi_tam_kare=True,
                 sahi_nms_iou=0.5, sahi_kosul_conf=0.5):
        self.hazir = False
        self.model = None
        self.names = {}
        self.conf = float(conf)
        self.imgsz = int(imgsz)
        self.device = device
        self.half = half            # FP16 (None -> cuda'da otomatik acik)
        # SAHI: kareyi ortusen dilimlere bol, her dilimde predict, kutulari
        # tam-kare koordina tasi + NMS ile birlestir (uzak/kucuk hedef recall).
        self.sahi = bool(sahi)
        self.sahi_dilim = int(sahi_dilim)
        self.sahi_ortusme = float(sahi_ortusme)
        self.sahi_tam_kare = bool(sahi_tam_kare)
        self.sahi_nms_iou = float(sahi_nms_iou)
        self.sahi_kosul_conf = float(sahi_kosul_conf)
        self._fp16_kwargs = {}
        self.hata = None
        self.task = None            # 'detect' | 'pose'
        self.kpt_shape = None       # pose ise (n, dim)
        try:
            from ultralytics import YOLO
            if self.device is None:                       # cihaz otomatik
                try:
                    import torch
                    self.device = "cuda" if torch.cuda.is_available() else "cpu"
                except Exception:
                    self.device = "cpu"
            if self.half is None:
                self.half = (self.device == "cuda")
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
            self.hata = repr(e)

    def _warmup(self):
        # FP16 API secimi + isitma: yeni ultralytics 'quantize="fp16"', eski surumde
        # bu arg yok -> TypeError -> 'half=True'ya dus. Secilen arg _fp16_kwargs'a yazilir.
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
                    continue                      # bu FP16 arg'i bu surumde yok -> digerini dene
            self._fp16_kwargs = {}
            self.model.predict(bos, imgsz=self.imgsz, conf=self.conf,
                               device=self.device, verbose=False)
        except Exception:
            pass

    @staticmethod
    def _maskede(cxn, cyn, maske):
        """Normalize merkez (cxn,cyn) maske dikdortgenlerinden birinin icinde mi?"""
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
        """En-yuksek-conf bbox dict | None. maske: merkezi icinde olan kutular elenir."""
        hepsi = self.tespit_hepsi(frame, maske=maske)
        return hepsi[0] if hepsi else None

    def tespit_hepsi(self, frame, maske=None):
        """Karedeki tum tespitler, conf'a gore azalan sirali (bos olabilir).
        maske: merkezi maskede olan kutular listeye girmez. sahi=True ise SAHI yolu."""
        if not self.hazir:
            return []
        import time as _t
        try:
            ham, W, H = (self._sahi_ham(frame) if self.sahi
                         else self._tek_ham(frame))
        except Exception:
            return []
        t = _t.perf_counter()
        cikti = []
        for d in ham:
            cx = (d["x1"] + d["x2"]) / 2.0
            cy = (d["y1"] + d["y2"]) / 2.0
            if maske and W > 0 and H > 0 and self._maskede(cx / W, cy / H, maske):
                continue                                  # pervane maskesi -> atla
            e = {
                "cx": cx, "cy": cy,
                "w": (d["x2"] - d["x1"]), "h": (d["y2"] - d["y1"]),
                "conf": d["conf"], "cls": d["cls"],
                "W": W, "H": H, "t": t,
            }
            if d.get("kp") is not None:
                e["keypoints"] = d["kp"]
            cikti.append(e)
        cikti.sort(key=lambda d: -d["conf"])
        return cikti

    # Inference yollari: _tek_ham (tek predict) / _sahi_ham (dilimleme).
    # Ikisi de -> (ham_kutu_listesi, W, H). ham kutu: {x1,y1,x2,y2,conf,cls,kp}.
    def _tek_ham(self, frame):
        """Tek tam-kare predict. Keypoint tasinir (pose)."""
        res = self.model.predict(frame, imgsz=self.imgsz, conf=self.conf,
                                 device=self.device, verbose=False, **self._fp16_kwargs)[0]
        return self._res_kutular(res, 0.0, 0.0, kp_al=True)

    def _sahi_ham(self, frame):
        """SAHI: tam-kare + ortusen dilim predict'leri -> offset + NMS merge.
        Tam-karede conf>=sahi_kosul_conf kutu varsa dilimleme atlanir. kp=None."""
        import numpy as np
        arr = np.asarray(frame)
        if arr.ndim != 3:                     # PIL/beklenmedik -> guvenli tek predict
            return self._tek_ham(frame)
        Hf, Wf = int(arr.shape[0]), int(arr.shape[1])
        res = self.model.predict(frame, imgsz=self.imgsz, conf=self.conf,
                                 device=self.device, verbose=False, **self._fp16_kwargs)[0]
        tam, tW, tH = self._res_kutular(res, 0.0, 0.0, kp_al=False)
        W, H = (tW or Wf), (tH or Hf)
        # Kosullu perf kapisi: yakin/buyuk hedef zaten tam-karede yakalandiysa dilimleme yok
        if (self.sahi_kosul_conf > 0.0
                and max((d["conf"] for d in tam), default=0.0) >= self.sahi_kosul_conf):
            return tam, W, H
        kutular = list(tam) if self.sahi_tam_kare else []
        for (x0, y0, x1, y1) in self._dilimler(W, H, self.sahi_dilim, self.sahi_ortusme):
            tile = arr[y0:y1, x0:x1]
            if tile.size == 0:
                continue
            try:
                r = self.model.predict(tile, imgsz=self.imgsz, conf=self.conf,
                                       device=self.device, verbose=False, **self._fp16_kwargs)[0]
            except Exception:
                continue
            sub, _, _ = self._res_kutular(r, float(x0), float(y0), kp_al=False)
            kutular.extend(sub)
        return self._nms(kutular, self.sahi_nms_iou), W, H

    def _res_kutular(self, res, ox, oy, kp_al):
        """ultralytics res -> (ham_kutu_listesi, W, H). Koordlara (ox,oy) offset eklenir."""
        import numpy as np
        boxes = getattr(res, "boxes", None)
        H = int(res.orig_shape[0]) if getattr(res, "orig_shape", None) is not None else 0
        W = int(res.orig_shape[1]) if getattr(res, "orig_shape", None) is not None else 0
        out = []
        if boxes is None or len(boxes) == 0:
            return out, W, H
        kp_xy = kp_conf = None
        if kp_al:
            kpts = getattr(res, "keypoints", None)
            if kpts is not None:
                try:
                    kp_xy = kpts.xy.cpu().numpy() if hasattr(kpts.xy, "cpu") else np.asarray(kpts.xy)
                    kc = getattr(kpts, "conf", None)
                    if kc is not None:
                        kp_conf = kc.cpu().numpy() if hasattr(kc, "cpu") else np.asarray(kc)
                except Exception:
                    kp_xy = kp_conf = None
        for i in range(len(boxes)):
            x1, y1, x2, y2 = [float(v) for v in boxes.xyxy[i]]
            d = {
                "x1": x1 + ox, "y1": y1 + oy, "x2": x2 + ox, "y2": y2 + oy,
                "conf": float(boxes.conf[i]),
                "cls": int(boxes.cls[i]) if boxes.cls is not None else -1,
                "kp": None,
            }
            if kp_xy is not None and i < len(kp_xy):
                if kp_conf is not None and i < len(kp_conf):
                    d["kp"] = [[float(x) + ox, float(y) + oy, float(c)]
                               for (x, y), c in zip(kp_xy[i], kp_conf[i])]
                else:
                    d["kp"] = [[float(x) + ox, float(y) + oy, 1.0] for x, y in kp_xy[i]]
            out.append(d)
        return out, W, H

    @staticmethod
    def _dilimler(W, H, dilim, ortusme):
        """SAHI dilim izgarasi -> [(x0,y0,x1,y1), ...] tam-kare px. Son dilim kenari kaplar."""
        dilim = int(dilim)
        if dilim <= 0 or (W <= dilim and H <= dilim):
            return []
        adim = max(1, int(dilim * (1.0 - float(ortusme))))
        xs = list(range(0, max(1, W - dilim + 1), adim)) or [0]
        ys = list(range(0, max(1, H - dilim + 1), adim)) or [0]
        if xs[-1] + dilim < W:
            xs.append(W - dilim)
        if ys[-1] + dilim < H:
            ys.append(H - dilim)
        out = []
        for y in ys:
            for x in xs:
                x0, y0 = max(0, x), max(0, y)
                out.append((x0, y0, min(W, x0 + dilim), min(H, y0 + dilim)))
        return out

    @staticmethod
    def _iou_xyxy(a, b):
        ix1, iy1 = max(a["x1"], b["x1"]), max(a["y1"], b["y1"])
        ix2, iy2 = min(a["x2"], b["x2"]), min(a["y2"], b["y2"])
        iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
        kes = iw * ih
        aa = max(0.0, a["x2"] - a["x1"]) * max(0.0, a["y2"] - a["y1"])
        ab = max(0.0, b["x2"] - b["x1"]) * max(0.0, b["y2"] - b["y1"])
        bir = aa + ab - kes
        return kes / bir if bir > 1e-9 else 0.0

    @staticmethod
    def _nms(kutular, iou_esik):
        """Sinif-agnostik greedy NMS: en yuksek conf tutulur, IoU>esik olanlar elenir."""
        if len(kutular) <= 1:
            return list(kutular)
        sirali = sorted(kutular, key=lambda d: -d["conf"])
        tut = []
        for d in sirali:
            if all(HedefDedektor._iou_xyxy(d, k) <= iou_esik for k in tut):
                tut.append(d)
        return tut


def siniflar(model_path):
    """best.pt siniflarini (model.names) yazdir."""
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
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    siniflar(os.path.join(_root, "models", "best.pt"))

# -*- coding: utf-8 -*-
"""
POZ TESPIT (YOLO-pose talon_pose.pt inference sarmalayici)  [POSE_REHBERI Faz 7]
================================================================================
gorsel_tespit.HedefDedektor KALIBININ pose surumu: bir kareden EN-YUKSEK-conf
tespitin bbox'ini + 6 KEYPOINT'ini (u,v,conf) dondurur. PnP cozumu AYRI modulde
(pose/poz_cozucu.py); bu modul sadece "model + tek kare -> bbox + noktalar".

DAYANIKLILIK: ultralytics/torch KURULU DEGILSE veya model yuklenemezse sessizce
hazir=False olur ve tespit_et() hep None doner -> sistem best.pt + GPS ile
calismaya DEVAM eder (poz kestirimi devreye girmez, cokme YOK).

NOT — keypoint SIRASI: model ciktisi EGITIM sirasindadir (pose/sira_bul.py ile
deneysel bulundu): [burun, sol_kanat, sag_kanat, kuyruk_arka, sol_kuyruk,
sag_kuyruk]. talon_keypoints.json REFERANS sirasina cevirme poz_cozucu
(EGITIM_SIRASI) ve server._normalize_poz'da yapilir — burada HAM sira doner.
"""


class PozDedektor:

    def __init__(self, model_path, conf=0.20, imgsz=960, device=None):
        self.hazir = False
        self.model = None
        self.conf = float(conf)
        self.imgsz = int(imgsz)          # egitim imgsz'ine esitle (v3 model: 1280; cagiran verir)
        self.device = device
        self.hata = None
        try:
            from ultralytics import YOLO
            if self.device is None:
                try:
                    import torch
                    self.device = "cuda" if torch.cuda.is_available() else "cpu"
                except Exception:
                    self.device = "cpu"
            self.model = YOLO(model_path)
            if getattr(self.model, "task", None) != "pose":
                raise ValueError("model 'pose' degil: %r" % getattr(self.model, "task", None))
            self.hazir = True
            self._warmup()
        except Exception as e:
            self.hazir = False
            self.hata = repr(e)

    def _warmup(self):
        try:
            import numpy as np
            bos = np.zeros((self.imgsz, self.imgsz, 3), dtype="uint8")
            self.model.predict(bos, imgsz=self.imgsz, conf=self.conf,
                               device=self.device, verbose=False)
        except Exception:
            pass

    def tespit_et(self, frame):
        """frame: BGR ndarray (grab_frame_bgr ciktisi) veya PIL. None | dict doner:
        {cx,cy,w,h,conf,cls,W,H,t, kp_xy:[[u,v]x6] px, kp_conf:[c x6]}  (MODEL sirasi)."""
        if not self.hazir:
            return None
        import time as _t
        try:
            res = self.model.predict(frame, imgsz=self.imgsz, conf=self.conf,
                                     device=self.device, verbose=False)[0]
        except Exception:
            return None
        boxes = getattr(res, "boxes", None)
        kps = getattr(res, "keypoints", None)
        if boxes is None or kps is None or len(boxes) == 0:
            return None
        try:
            i = int(boxes.conf.argmax())                  # EN-YUKSEK-conf tespit
            x1, y1, x2, y2 = [float(v) for v in boxes.xyxy[i]]
            kxy = kps.xy[i].cpu().numpy()                 # (6,2) px
            kcf = (kps.conf[i].cpu().numpy() if kps.conf is not None else None)
            if kxy.shape[0] != 6:
                return None                               # beklenmedik kpt sayisi
            H, W = int(res.orig_shape[0]), int(res.orig_shape[1])
            return {
                "cx": (x1 + x2) / 2.0, "cy": (y1 + y2) / 2.0,
                "w": (x2 - x1), "h": (y2 - y1),
                "conf": float(boxes.conf[i]),
                "cls": int(boxes.cls[i]) if boxes.cls is not None else -1,
                "W": W, "H": H, "t": _t.perf_counter(),
                "kp_xy": [[float(u), float(v)] for u, v in kxy],
                "kp_conf": ([1.0] * 6 if kcf is None else [float(c) for c in kcf]),
            }
        except Exception:
            return None


if __name__ == "__main__":
    import os
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    d = PozDedektor(os.path.join(_root, "models", "talon_pose.pt"))
    print("hazir:", d.hazir, "| device:", d.device, "| hata:", d.hata)

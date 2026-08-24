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

    def __init__(self, model_path, conf=0.20, imgsz=960, device=None, half=None):
        self.hazir = False
        self.model = None
        self.conf = float(conf)
        self.imgsz = int(imgsz)          # egitim imgsz'ine esitle (v3 model: 1280; cagiran verir)
        self.device = device
        self.half = half                 # FP16 (None -> cuda'da otomatik AC; cpu'da kapali)
        self._fp16_kwargs = {}           # predict FP16 arg'i (API'ye gore quantize/half)
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
            # ⚠ TensorRT .engine gorev bilgisi TASIMIYOR: ultralytics
            # "assuming task=detect" deyip tahmin ediyor, bu kontrol de haklı
            # olarak reddediyordu. Cozum: gorevi ACIKCA ver.
            #   [POZ] pose modeli YUKLENEMEDI (ValueError("model 'pose' degil:
            #         'detect'")) -- 2026-08-16, talon_pose_v2.engine
            if str(model_path).lower().endswith((".engine", ".onnx", ".plan")):
                self.model = YOLO(model_path, task="pose")
            else:
                self.model = YOLO(model_path)
            if getattr(self.model, "task", None) != "pose":
                raise ValueError("model 'pose' degil: %r" % getattr(self.model, "task", None))
            self.hazir = True
            self._warmup()
        except Exception as e:
            self.hazir = False
            self.hata = repr(e)

    def _warmup(self):
        # FP16 API secimi + isitma (gorsel_tespit ile ayni desen): yeni ultralytics
        # 'quantize="fp16"' (uyarisiz), eski surumde TypeError -> 'half=True'ya dus.
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

    def tespit_et(self, frame):
        """frame: BGR ndarray (grab_frame_bgr ciktisi) veya PIL. None | dict doner:
        {cx,cy,w,h,conf,cls,W,H,t, kp_xy:[[u,v]x6] px, kp_conf:[c x6]}  (MODEL sirasi)."""
        if not self.hazir:
            return None
        import time as _t
        try:
            res = self.model.predict(frame, imgsz=self.imgsz, conf=self.conf,
                                     device=self.device, verbose=False, **self._fp16_kwargs)[0]
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

    # ── KROP YOLU (256x96 top-down poz modeli) ──────────────────────────────
    # NEDEN: tam-kare poz modeli 960x960 kosar ve hedef 12-25 m'de 28x12 px'e
    # duser -> 6 keypoint'i o kadar pikselden regresyona sokmak umutsuz. Krop
    # modeli dedektorun kutusunu 1.5x payla kesip SABIT 256x96'ya getirir; hedef
    # her menzilde ayni piksel buyuklugune gelir.
    # OLCULDU (1532 val karesi, orijinal kare pikselinde, dedektor kutusuyla):
    #     12-25 m ortanca 1.36 vs 1.77 px  (krop %23 iyi)
    #     12-25 m p90     3.78 vs 5.02 px  (krop %25 iyi)
    #     sag kanat p90  18.04 vs 27.21    sol kanat p90 20.18 vs 36.98
    #     genel p90      19.46 vs 23.50    hedefi kacirma %0.4 vs %1.6
    # Tam-kare model yalniz 0-6 / 6-12 m ORTANCASINDA az onde.
    # ⚠ GEOMETRI krop_uret.py ile BIREBIR ayni olmali (PAY=1.5, oran 256/96,
    #   kadraj disina tasinca ICERI kaydir). Farkli olursa model transfer etmez:
    #   egitimdeki kroplar bu geometriyle uretildi.
    # ⚠ Dedektor kutusunun gurultusu SORUN DEGIL: egitimde jitter (+-%12 kaydirma,
    #   +-%20 olcek) vardi ve olculdu ki GT kutu -> dedektor kutusu gecisi
    #   ortancayi %0.1 degistiriyor.
    KROP_W, KROP_H, KROP_PAY = 256, 96, 1.5

    def _krop_penceresi(self, cx, cy, bw, bh, W, H):
        """krop_uret.py:krop_kutusu ile birebir (jitter kapali)."""
        ar = self.KROP_W / float(self.KROP_H)
        cw = max(bw * self.KROP_PAY, bh * self.KROP_PAY * ar)
        ch = cw / ar
        x0, y0 = cx - cw / 2.0, cy - ch / 2.0
        x0 = min(max(x0, 0.0), max(0.0, W - cw))
        y0 = min(max(y0, 0.0), max(0.0, H - ch))
        return x0, y0, cw, ch

    def tespit_krop(self, frame, det):
        """frame: TAM KARE BGR ndarray. det: dedektor sonucu (cx,cy,w,h NORMALIZE).
        tespit_et() ile AYNI sozlesmede dict doner; keypoint'ler TAM KARE
        pikselindedir (cagiran ayrica kaydirma yapmamali)."""
        if not self.hazir or frame is None or det is None:
            return None
        import time as _t
        try:
            H, W = int(frame.shape[0]), int(frame.shape[1])
            cx, cy = float(det["cx"]), float(det["cy"])
            bw, bh = float(det["w"]), float(det["h"])
            # ⚠ SOZLESME KARISIKLIGI (2026-08-21 olculdu): depoda IKI kutu birimi
            # dolasiyor. gorsel_tespit.tespit_et/tespit_hepsi PIKSEL dondurur
            # ("px + perf_counter zaman damgasi"), _normalize_tespit ise 0..1
            # NORMALIZE uretir. server.py'de poz cagri noktasindaki `det`
            # dets[0]/takipci ciktisidir, yani PIKSEL. Ama hemen ustundeki
            # yakinlik kapisi `det["w"] * bgr.shape[1]` diye carpiyor, yani
            # NORMALIZE varsayiyor -> o kapi pratikte hicbir seyi engellemiyor
            # (piksel x genislik daima POZ_MIN_KUTU_PX'i asar).
            # Burada birimi TAHMIN ETMEK yerine OLCUYORUZ: normalize kutu
            # tanimi geregi 1.0'i asamaz. Yanlis birim krop penceresini kadraj
            # disina atar, pencere kenara kirpilir, hedef icine girmez ve
            # tespit sessizce None doner -- canli testte tam bu oldu.
            if max(bw, bh) <= 1.5 and 0.0 <= cx <= 1.5 and 0.0 <= cy <= 1.5:
                cx, cy, bw, bh = cx * W, cy * H, bw * W, bh * H
            if bw <= 0 or bh <= 0:
                return None
            x0, y0, cw, ch = self._krop_penceresi(cx, cy, bw, bh, W, H)
            if cw < 8 or ch < 4:
                return None
            ix0, iy0 = int(round(x0)), int(round(y0))
            ix1, iy1 = int(round(x0 + cw)), int(round(y0 + ch))
            kesit = frame[iy0:iy1, ix0:ix1]
            if kesit.size == 0:
                return None
            try:                                   # egitimdeki gibi tek yeniden olcek
                import cv2
                kesit = cv2.resize(kesit, (self.KROP_W, self.KROP_H),
                                   interpolation=cv2.INTER_LINEAR)
            except Exception:
                pass                               # ultralytics kendi letterbox'i ile devam
            res = self.model.predict(kesit, imgsz=(self.KROP_H, self.KROP_W),
                                     conf=self.conf, device=self.device,
                                     verbose=False, **self._fp16_kwargs)[0]
        except Exception:
            return None
        boxes = getattr(res, "boxes", None)
        kps = getattr(res, "keypoints", None)
        if boxes is None or kps is None or len(boxes) == 0:
            return None
        try:
            i = int(boxes.conf.argmax())
            kxy = kps.xy[i].cpu().numpy()
            if kxy.shape[0] != 6:
                return None
            kcf = (kps.conf[i].cpu().numpy() if kps.conf is not None else None)
            # kesit koordinati -> TAM KARE pikseli
            sx, sy = cw / float(self.KROP_W), ch / float(self.KROP_H)
            kp = [[x0 + float(u) * sx, y0 + float(v) * sy] for u, v in kxy]
            bx1, by1, bx2, by2 = [float(v) for v in boxes.xyxy[i]]
            return {
                "cx": x0 + (bx1 + bx2) / 2.0 * sx, "cy": y0 + (by1 + by2) / 2.0 * sy,
                "w": (bx2 - bx1) * sx, "h": (by2 - by1) * sy,
                "conf": float(boxes.conf[i]),
                "cls": int(boxes.cls[i]) if boxes.cls is not None else -1,
                "W": W, "H": H, "t": _t.perf_counter(),
                "kp_xy": kp,
                "kp_conf": ([1.0] * 6 if kcf is None else [float(c) for c in kcf]),
            }
        except Exception:
            return None


if __name__ == "__main__":
    import os
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    d = PozDedektor(os.path.join(_root, "models", "talon_pose.pt"))
    print("hazir:", d.hazir, "| device:", d.device, "| hata:", d.hata)

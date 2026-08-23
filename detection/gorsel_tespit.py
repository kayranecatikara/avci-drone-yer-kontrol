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


import os


def _np_bos(n):
    """engine isitma/dogrulama icin bos kare (yukleme gercekten calisiyor mu)."""
    import numpy as _np
    return _np.zeros((int(n), int(n), 3), dtype=_np.uint8)


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
        self.half = half            # FP16 inference (None -> cuda'da otomatik AC; cpu'da kapali)
        # --- SAHI (Slicing Aided Hyper Inference) — bizim temiz impl, sahi paketi GEREKMEZ.
        # Kareyi ortusen dilimlere bol, HER dilimde predict, kutulari tam-kare koordina
        # tasi + NMS ile birlestir -> uzak/kucuk hedef recall artar (kural 8 aciklanabilir).
        # SADECE detect modelinde kullan; pose modelinde KAPALI (keypoint dilim-merge yok).
        self.sahi = bool(sahi)
        self.sahi_dilim = int(sahi_dilim)
        self.sahi_ortusme = float(sahi_ortusme)
        self.sahi_tam_kare = bool(sahi_tam_kare)
        self.sahi_nms_iou = float(sahi_nms_iou)
        self.sahi_kosul_conf = float(sahi_kosul_conf)
        self._fp16_kwargs = {}      # predict'e eklenen FP16 arg'i (API'ye gore quantize/half)
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
            # FP16: cuda'da ~2x hizlanma, dogruluk kaybi ihmal edilebilir. CPU'da FP16
            # anlamsiz/yavas -> otomatik kapali. Cagiran acikca half=True/False verebilir.
            if self.half is None:
                self.half = (self.device == "cuda")
            # ── MOTOR SECIMI: TensorRT .engine varsa ONU kullan (2026-08-11) ──
            # OLCULDU (RTX 4060, oyun+sunucu kosarken, ayni 40 kare):
            #     motor    tam-kare   SAHI batch8   kare/sn   IoU ort   IoU>0.9
            #     .pt       113.5 ms     205.1 ms      3.1     1.0000      —
            #     .onnx     752.4 ms     877.0 ms      0.6     0.9840     ...
            #     .engine    13.1 ms      33.9 ms     21.3     0.9861    %100
            # -> 7 kat hiz, tespit sayisi BIREBIR ayni (20/20), kutu kaymasi yok.
            # ONNX ELENDI: onnxruntime GPU degil, CPU'da kosuyor.
            # engine GPU/TensorRT surumune BAGLIDIR -> yuklenemezse .pt'ye doner
            # ve SEBEBI YAZAR (sessiz dusme yok). AVCI_MOTOR=pt ile kapatilir.
            self.motor = "pt"
            _istek = os.environ.get("AVCI_MOTOR", "auto").strip().lower()
            _yol = str(model_path)
            if _istek != "pt" and _yol.lower().endswith(".pt"):
                _eng = _yol[:-3] + ".engine"
                if os.path.exists(_eng):
                    try:
                        self.model = YOLO(_eng, task="detect")
                        self.model.predict(_np_bos(self.imgsz), imgsz=self.imgsz,
                                           device=self.device, verbose=False)
                        self.motor = "engine"
                        _yol = _eng
                    except Exception as e:
                        print("[GORSEL] TensorRT engine yuklenemedi -> .pt'ye "
                              "donuluyor. Sebep: %r" % (e,))
                        self.model = None
                elif _istek == "engine":
                    print("[GORSEL] AVCI_MOTOR=engine istendi ama dosya YOK: %s" % _eng)
                else:
                    # ⚠ SESSIZ DUSME ARTIK SESSIZ DEGIL (2026-08-21).
                    # Engine YOKSA eskiden hicbir sey yazilmiyordu ve sistem
                    # 7 KAT yavas kosuyordu. Yeni bir makinede kurulum yapan
                    # kisi bunu FPS'e bakarak anlamak zorunda kaliyordu --
                    # nitekim oyle oldu: "model 14 fps ile calisiyor".
                    # .engine dosyalari GPU/surucu/TensorRT surumune ozeldir,
                    # makineden makineye KOPYALANAMAZ; her makinede uretilir.
                    print("[GORSEL] ⚠ TensorRT engine YOK (%s) -> .pt ile kosuluyor."
                          % os.path.basename(_eng))
                    print("[GORSEL]   OLCULDU: .pt 113.5 ms (3.1 kare/sn)  vs  "
                          ".engine 13.1 ms (21.3 kare/sn) = 7 KAT.")
                    print("[GORSEL]   Uretmek icin:  python arac/motor_uret.py")
            if self.model is None:
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
        # FP16 API SECIMI + isitma: yeni ultralytics 'quantize="fp16"' (uyarisiz),
        # eski surumde bu arg YOK -> TypeError -> 'half=True'ya dus (fonksiyonel).
        # Secilen arg self._fp16_kwargs'a yazilir, tum predict'lerde kullanilir.
        # (ilk predict yavas oldugundan warmup zaten sart; API testini birlestirdik.)
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
            # FP16 adaylarinin hicbiri gecmedi -> FP32 warmup (garanti)
            self._fp16_kwargs = {}
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
        maske: pervane bolgeleri — merkezi maskede olan kutular listeye GIRMEZ.
        self.sahi=True ise SAHI dilimleme yolu kosar (uzak/kucuk hedef recall);
        ciktisi tam-kare piksel koordinda -> downstream (maske/sema/sort) ayni."""
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
            # PERVANE MASKESI: merkezi maskede olan kutu listeye girmez.
            if maske and W > 0 and H > 0 and self._maskede(cx / W, cy / H, maske):
                continue                                  # kendi pervanemiz -> atla
            e = {
                "cx": cx, "cy": cy,
                "w": (d["x2"] - d["x1"]), "h": (d["y2"] - d["y1"]),
                "conf": d["conf"], "cls": d["cls"],
                "W": W, "H": H, "t": t,
            }
            if d.get("kp") is not None:
                e["keypoints"] = d["kp"]                   # [[x,y,conf],...] (PnP tuketicisi)
            cikti.append(e)
        cikti.sort(key=lambda d: -d["conf"])
        return cikti

    # ------------------------------------------------------------------
    #  Inference yollari: _tek_ham (tek predict) / _sahi_ham (dilimleme)
    #  ikisi de -> (ham_kutu_listesi, W, H). ham kutu: {x1,y1,x2,y2,conf,cls,kp}
    #  tam-kare piksel koordinda (kp: keypoint listesi | None).
    # ------------------------------------------------------------------
    def _tek_ham(self, frame):
        """Tek tam-kare predict (eski davranis, bit-ayni). Keypoint TASINIR (pose)."""
        res = self.model.predict(frame, imgsz=self.imgsz, conf=self.conf,
                                 device=self.device, verbose=False, **self._fp16_kwargs)[0]
        return self._res_kutular(res, 0.0, 0.0, kp_al=True)

    def _sahi_ham(self, frame):
        """SAHI: tam-kare + ortusen dilim predict'leri -> offset + NMS merge.
        KOSULLU: tam-karede conf>=sahi_kosul_conf kutu VARSA dilimleme ATLANIR
        (yakin hedef -> tek inference; N-dilim maliyeti yalniz uzak/kucukte).
        Detect modeli varsayilir -> keypoint YOK (kp=None)."""
        import numpy as np
        arr = np.asarray(frame)
        if arr.ndim != 3:                     # PIL/beklenmedik -> guvenli tek predict
            return self._tek_ham(frame)
        Hf, Wf = int(arr.shape[0]), int(arr.shape[1])
        res = self.model.predict(frame, imgsz=self.imgsz, conf=self.conf,
                                 device=self.device, verbose=False, **self._fp16_kwargs)[0]
        tam, tW, tH = self._res_kutular(res, 0.0, 0.0, kp_al=False)
        W, H = (tW or Wf), (tH or Hf)
        # KOSULLU perf kapisi: yakin/buyuk hedef zaten tam-karede yakalandiysa dilimleme yok
        if (self.sahi_kosul_conf > 0.0
                and max((d["conf"] for d in tam), default=0.0) >= self.sahi_kosul_conf):
            return tam, W, H
        kutular = list(tam) if self.sahi_tam_kare else []
        # ── DILIMLER TEK BATCH'TE (2026-08-10, olculdu) ────────────────────
        # ONCEDEN: her dilim ayri predict cagrisi (8 dilim = 8 GPU turu).
        # ultralytics liste kabul ediyor -> tek forward. AYNI dilimler, AYNI
        # sonuc, daha az GPU turu. OLCUM (90 uzak kare, 40-120 m, RTX 4060):
        #     SAHI kapali    : tespit  0.0%   25.2 ms/kare  (39.6 FPS)
        #     640 SERI (eski): tespit 71.1%  118.4 ms/kare  ( 8.4 FPS)
        #     640 BATCH (yeni): tespit 71.1%  55.4 ms/kare  (18.0 FPS)  <- 2.1x
        #     1080 batch     : tespit 13.3%   40.0 ms/kare  -> recall COKER
        # Yani recall'den hicbir sey vermeden arama fazi ikiye katlaniyor.
        # Batch basarisiz olursa (bellek/surum) SERI yola dusulur — sessiz
        # kalmaz, davranis eskisiyle bit-ayni olur.
        dilimler = [(x0, y0, x1, y1)
                    for (x0, y0, x1, y1) in self._dilimler(W, H, self.sahi_dilim,
                                                           self.sahi_ortusme)
                    if arr[y0:y1, x0:x1].size > 0]
        if dilimler:
            tiles = [arr[y0:y1, x0:x1] for (x0, y0, x1, y1) in dilimler]
            sonuc = None
            try:
                sonuc = self.model.predict(tiles, imgsz=self.imgsz, conf=self.conf,
                                           device=self.device, verbose=False,
                                           **self._fp16_kwargs)
                if len(sonuc) != len(dilimler):
                    sonuc = None                           # beklenmedik -> seri yol
            except Exception as e:
                if not getattr(self, "_batch_uyari", False):
                    self._batch_uyari = True
                    print("[GORSEL] SAHI batch basarisiz, seri yola dusuldu: %r" % (e,))
                sonuc = None
            if sonuc is not None:
                for (x0, y0, _, _), r in zip(dilimler, sonuc):
                    sub, _, _ = self._res_kutular(r, float(x0), float(y0), kp_al=False)
                    kutular.extend(sub)
            else:
                for (x0, y0, x1, y1) in dilimler:          # geri-donus: eski seri yol
                    try:
                        r = self.model.predict(arr[y0:y1, x0:x1], imgsz=self.imgsz,
                                               conf=self.conf, device=self.device,
                                               verbose=False, **self._fp16_kwargs)[0]
                    except Exception:
                        continue
                    sub, _, _ = self._res_kutular(r, float(x0), float(y0), kp_al=False)
                    kutular.extend(sub)
        return self._nms(kutular, self.sahi_nms_iou), W, H

    def _res_kutular(self, res, ox, oy, kp_al):
        """ultralytics res -> (ham_kutu_listesi, W, H). Koordlara (ox,oy) offset eklenir
        (dilim -> tam-kare). kp_al=True ise keypoint (varsa) tasinir + offsetlenir."""
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
        # ⚠ 2026-08-17: eskiden kutu basina ALTI ayri GPU->CPU aktarimi vardi
        #   (float(boxes.xyxy[i]) x4 + conf + cls). Her biri ortuk senkron +
        #   GIL birak/al demek; conf=0.25'te tipik 8-15 kutu -> kare basina
        #   50-90 gidis-donus. GIL devir gecikmesiyle carpilinca dogrudan
        #   det_ms'e biniyordu. Tek seferde numpy'a al, sonra oradan oku.
        _xyxy = boxes.xyxy.cpu().numpy() if hasattr(boxes.xyxy, "cpu") else np.asarray(boxes.xyxy)
        _cnf = boxes.conf.cpu().numpy() if hasattr(boxes.conf, "cpu") else np.asarray(boxes.conf)
        _cls = None
        if boxes.cls is not None:
            _cls = boxes.cls.cpu().numpy() if hasattr(boxes.cls, "cpu") else np.asarray(boxes.cls)
        for i in range(len(boxes)):
            x1, y1, x2, y2 = (float(_xyxy[i][0]), float(_xyxy[i][1]),
                              float(_xyxy[i][2]), float(_xyxy[i][3]))
            d = {
                "x1": x1 + ox, "y1": y1 + oy, "x2": x2 + ox, "y2": y2 + oy,
                "conf": float(_cnf[i]),
                "cls": int(_cls[i]) if _cls is not None else -1,
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
        """SAHI dilim izgarasi -> [(x0,y0,x1,y1), ...] tam-kare px. Son dilim kareyi
        kaplar (kenarda bosluk kalmasin); kare zaten dilimden kucukse bos liste."""
        dilim = int(dilim)
        if dilim <= 0 or (W <= dilim and H <= dilim):
            return []
        adim = max(1, int(dilim * (1.0 - float(ortusme))))
        xs = list(range(0, max(1, W - dilim + 1), adim)) or [0]
        ys = list(range(0, max(1, H - dilim + 1), adim)) or [0]
        if xs[-1] + dilim < W:
            xs.append(W - dilim)                          # son sutun kenari kaplasin
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
        """Sinif-agnostik greedy NMS (tek sinif talon). Dilim+tam-kare cift kutulari
        birlestirir: en yuksek conf tutulur, IoU>esik olanlar elenir."""
        if len(kutular) <= 1:
            return list(kutular)
        sirali = sorted(kutular, key=lambda d: -d["conf"])
        tut = []
        for d in sirali:
            if all(HedefDedektor._iou_xyxy(d, k) <= iou_esik for k in tut):
                tut.append(d)
        return tut


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

# -*- coding: utf-8 -*-
"""
================================================================================
 GORSEL TESPIT  (best.pt / YOLO sarmalayici) — hedef tespit + tracking
================================================================================
best.pt (ultralytics YOLO) modelini yukleyip bir BGR kareden hedefi tespit eder.
IBVS guduum bu modulun verdigi bbox MERKEZINI tek hata sinyali olarak kullanir.

ZARIF BOZULMA (kritik): ultralytics/torch kurulu degilse VEYA model yuklenemezse
'hazir=False' olur, tespit_et() daima None doner. Boylece sistem COKMEZ; gorsel
faz devreye girmez ve mevcut saf GPS yaklasma davranisi BUGUNKUYLE BIREBIR kalir.

Cikti (ham tespit): {"bbox_xyxy":(x1,y1,x2,y2), "conf":float, "cls":int, "tid":int|None}
veya None (kutu yok). Tam 'Tespit' sozlugunu (cx,cy,w,h,frame_w,frame_h,ts,var)
cagiran (server.py) birlestirir — bu modul zaman/kare bilgisi tasimaz (saf kalir).

Renk uzayi: ultralytics BGR bekler -> dogrudan mss/cv2 BGR karesi verilir.
Tracking: takip=True iken model.track(persist=True, tracker="bytetrack.yaml")
(sartname "tracking aktif" isteri); persist sirali tek-thread cagri ister, bu da
tek inference thread'i ile garanti edilir.
================================================================================
"""


class GorselTespit:
    def __init__(self, model_path="best.pt", conf=0.65, imgsz=640,
                 device=None, hedef_sinif=None, takip=True):
        """
          model_path : YOLO agirligi (.pt)
          conf       : minimum guven esigi (model tarafinda filtrelenir)
          imgsz      : inference goruntu boyutu (ultralytics dahili letterbox)
          device     : None=otomatik (CUDA varsa GPU, yoksa CPU) | 'cpu' | 0 (GPU)
          hedef_sinif: yalniz bu sinif id'sini dikkate al (None=tum siniflar)
          takip      : True=model.track (bytetrack) | False=model.predict
        """
        self.model_path = model_path
        self.conf = conf
        self.imgsz = imgsz
        self.device = device
        self.hedef_sinif = hedef_sinif
        self.takip = takip
        self.hazir = False
        self.names = {}
        self._model = None
        self._uyari_basildi = False

        try:
            from ultralytics import YOLO
            self._model = YOLO(model_path)
            self.names = getattr(self._model, "names", {}) or {}
            self.hazir = True
            try:
                import torch
                _dev = ("GPU: %s" % torch.cuda.get_device_name(0)) if torch.cuda.is_available() else "CPU (yavas)"
            except Exception:
                _dev = "?"
            print("[GORSEL_TESPIT] model yuklendi: %s | siniflar: %s | takip=%s | calisma: %s"
                  % (model_path, self.names, takip, _dev))
        except Exception as e:
            # ultralytics yok / model dosyasi yok / yukleme hatasi -> zarif bozulma
            self.hazir = False
            print("[GORSEL_TESPIT] model YUKLENEMEDI (%s). Gorsel faz pasif, saf GPS surer." % e)

    def tespit_et(self, frame_bgr):
        """Bir BGR kareden EN YUKSEK guvenli TEK hedefi dondur, yoksa None.
        Donus: {"bbox_xyxy":(x1,y1,x2,y2), "conf":float, "cls":int, "tid":int|None}."""
        if not self.hazir or frame_bgr is None:
            return None
        try:
            if self.takip:
                res = self._model.track(
                    frame_bgr, imgsz=self.imgsz, conf=self.conf, device=self.device,
                    persist=True, tracker="bytetrack.yaml", verbose=False)
            else:
                res = self._model.predict(
                    frame_bgr, imgsz=self.imgsz, conf=self.conf, device=self.device,
                    verbose=False)
        except Exception as e:
            if not self._uyari_basildi:
                print("[GORSEL_TESPIT] inference hatasi (bir kez loglanir): %s" % e)
                self._uyari_basildi = True
            return None

        if not res:
            return None
        boxes = getattr(res[0], "boxes", None)
        if boxes is None or len(boxes) == 0:
            return None

        # Tensorleri guvenli listelere cevir (CPU/GPU farketmez)
        try:
            xyxy = boxes.xyxy.tolist()
            confs = boxes.conf.tolist()
            clss = boxes.cls.tolist() if boxes.cls is not None else [-1] * len(confs)
            ids = boxes.id.tolist() if getattr(boxes, "id", None) is not None else [None] * len(confs)
        except Exception:
            return None

        # Opsiyonel hedef-sinif filtresi
        adaylar = range(len(confs))
        if self.hedef_sinif is not None:
            adaylar = [i for i in adaylar if int(clss[i]) == int(self.hedef_sinif)]
            if not adaylar:
                return None

        # En yuksek guven -> TEK kutu
        i = max(adaylar, key=lambda k: confs[k])
        x1, y1, x2, y2 = xyxy[i]
        tid = ids[i]
        return {
            "bbox_xyxy": (float(x1), float(y1), float(x2), float(y2)),
            "conf": float(confs[i]),
            "cls": int(clss[i]),
            "tid": (int(tid) if tid is not None else None),
        }

# -*- coding: utf-8 -*-
"""
perception/detector.py — YOLO tabanli hedef (Talon) tespiti.

    TargetDetector(model_yolu).detect_all(bgr) -> [{cx,cy,w,h,conf,cls,W,H,t}, ...]
                                                   (conf'a gore AZALAN sirali)

Model: perception/models/talon_v3 (task=detect, tek sinif: talon).
AGIRLIK SECIMI (bkz. _resolve_model): ayni agirligin TensorRT motoru
(talon_v3.engine) varsa ONCELIKLIDIR, yoksa .pt kosar. Motor
`python -m scripts.export_engine` ile URETILIR, burada uretilmez.
Ortam degiskenleri: AVCI_MODEL=... / AVCI_IMGSZ=... / AVCI_ENGINE=0

DAYANIKLILIK: ultralytics/torch kurulu degilse veya model yuklenemezse sessizce
`hazir=False` olur ve tespit hep bos doner -> sistem GPS fazinda calismaya DEVAM
eder (gorsel faz devreye girmez, ama cokme yok).

Renk notu: ultralytics numpy diziyi BGR varsayar; camera.py BGR ndarray uretir
-> dogrudan gecmek DOGRU renktir.

PERVANE MASKESI: avcinin KENDI pervanesi arada bir "ucak" olarak algilaniyor ve
kadrajda SABIT bir bolgede duruyor. Merkezi maskede kalan kutular listeye hic
girmez (secim ONCESI elenir) -> kendi pervanemiz hedef sanilmaz.
"""
import ast
import json
import os
import time

# Kadrajda kendi pervanemizin gorundugu bolgeler: [(x0, y0, x1, y1), ...],
# hepsi NORMALIZE (0..1) kare kordinatinda — cozunurluk degisse de gecerlidir.
# Merkezi bu dikdortgenlerden birine dusen kutu listeye HIC girmez, yani secim
# ONCESI elenir; boylece kendi pervanemiz hedef sanilmaz.
# Canli FPV'de maske pervaneyi tam ortmuyorsa bu listeyi duzenleyin.
PROP_MASK = [(0.80, 0.55, 1.0, 0.95)]

MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")  # agirliklarin klasoru

# ⭐ AKTIF MODEL: talon_v3 (2026-08-15, 60 epoch, ultralytics 8.4.83).
#   Onceki best (2026-07-07, 200 epoch, 8.4.90) DEPODA DURUYOR ve tek
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

# 0..1; dedektorun predict esigi = kutu URETMEK icin gereken asgari guven.
# Guduum kapisi (`control.visual_tracking.VisualCfg.CONF_MIN` = 0.40) bunun
# USTUNDE calisir; taban bilerek dusuk tutulur ki takipci (HybridSort/BYTE)
# zayif kutularla MEVCUT bir izi yasatabilsin. Dusuk guvenli kutu yeni iz ACAMAZ,
# guduume de giremez — yalnizca sureklilige katki saglar.
CONF_FLOOR = 0.10

# ⛔ EGITIM COZUNURLUGU — MODELE BAGLIDIR, sabit degildir.
#   Checkpoint metadata'sindan OKUNDU (train_args.imgsz):
#       talon_v3 -> 960      <- AKTIF
#       best     -> 640
#   Modeli degistirip burayi unutmak SESSIZ bir bozulmadir: cikarim egitimden
#   farkli olcekte kosar, uzak/kucuk hedef once kaybolur (kutu hic cikmaz),
#   sonra gorsel faz hic acilmaz. Bu yuzden varsayilan MODELDEN turetilir.
#
# ⭐ TABLO UZANTISIZ ANAHTARLANIR. Ayni agirligin .pt ve .engine surumu AYNI
#   olcekte kosar; uzantiyla anahtarlansaydi motor tabloda bulunamaz, sessizce
#   640'a duser ve uzak hedef kaybolurdu.
_IMGSZ_BY_MODEL = {"talon_v3": 960, "best": 640}


def imgsz_for_model(path):
    """Bir agirligin EGITIM cozunurlugunu tablodan okur.

    path : agirlik dosyasinin yolu (.pt ya da .engine — uzanti onemsizdir)
    -> px; kare kenar olcusu (tabloda yoksa 640)
    """
    return _IMGSZ_BY_MODEL.get(os.path.splitext(os.path.basename(path))[0], 640)


def engine_imgsz(path):
    """.engine basligina GOMULU imgsz — TensorRT'nin gercekten kostugu olcek.

    Ultralytics motorun onune 4 bayt uzunluk + JSON basligi yazar. Bu okuma
    SALT stdlib'dir: torch/tensorrt import EDILMEZ, modul yukleme maliyeti
    degismez (dedektor tembel yuklenir ama bu dosya erken import edilir).
    Baslik yoksa/bozuksa None doner.
    """
    try:
        with open(path, "rb") as f:
            n = int.from_bytes(f.read(4), "little")
            if not (0 < n <= f.seek(0, 2) - 4):
                return None
            f.seek(4)
            meta = json.loads(f.read(n))
        sz = meta.get("imgsz")
        if isinstance(sz, str):
            sz = ast.literal_eval(sz)
        if isinstance(sz, (list, tuple)):
            return int(max(sz))
        return int(sz) if sz else None
    except Exception:
        return None


# ⭐ TENSORRT MOTORU VARSA VARSAYILAN ODUR (2026-08-27).
#   Ayni agirligin .engine surumu perception/models/ icinde duruyorsa dedektor
#   onu yukler, yoksa .pt'ye duser. Motor burada URETILMEZ, yalnizca KULLANILIR:
#       python -m scripts.export_engine
#   Kapatmak icin:  AVCI_ENGINE=0
#
# ⛔ MOTOR TASINMAZ ve REPOYA KONMAZ (.gitignore: *.engine). Karta, surucuye
#   ve TensorRT surumune derlenir; baska makinede acilmaz. Acilmazsa
#   TargetDetector SESSIZCE degil, GEREKCESIYLE .pt'ye doner (self.fallback).
USE_ENGINE = os.environ.get("AVCI_ENGINE", "1").lower() not in ("0", "off", "false")


def _resolve_model():
    """(yol, gerekce) — hangi agirlik yuklenecek?"""
    name = os.environ.get("AVCI_MODEL")
    if name:  # elle secim her seyi ezer: uzantisi neyse o kosar
        return os.path.join(MODELS_DIR, name), "AVCI_MODEL"
    pt = os.path.join(MODELS_DIR, _DEFAULT_MODEL)
    engine = os.path.splitext(pt)[0] + ".engine"
    if not USE_ENGINE:
        return pt, "AVCI_ENGINE=0"
    if not os.path.isfile(engine):
        return pt, "motor yok"
    # ⚠ AVCI_IMGSZ MOTORU EZEMEZ. Static motorun girdi sekli derlenirken
    #   sabitlendi; baska olcek TensorRT arka ucunda assert atar ve detect_all
    #   SESSIZCE bos doner. Cakisirsa .pt'ye duseriz — boylece uzak menzil
    #   taramasi (AVCI_IMGSZ=1920) bir sey bozmadan calismaya devam eder.
    want = os.environ.get("AVCI_IMGSZ")
    have = engine_imgsz(engine)
    try:
        clash = bool(want) and have is not None and int(want) != have
    except ValueError:
        clash = False
    if clash:
        return pt, "AVCI_IMGSZ=%s motorun %d olcusuyle cakisti" % (want, have)
    return engine, "TensorRT motoru"


MODEL_PATH, MODEL_REASON = _resolve_model()

# Motorun olcegi tablodan degil BASLIKTAN okunur: motor hangi olcekte
# derlendiyse hat o olcekte kosmak ZORUNDADIR (aksi halde assert -> bos liste).
_ENGINE_SZ = engine_imgsz(MODEL_PATH) if MODEL_PATH.endswith(".engine") else None
IMGSZ = _ENGINE_SZ or int(os.environ.get("AVCI_IMGSZ") or imgsz_for_model(MODEL_PATH))


class TargetDetector:
    """YOLO tabanli hedef (Talon) dedektoru — bir kareden kutu listesi uretir.

    DURUM ALANLARI (arayuz ve gunluk bunlari okur)
        ready       : model yuklendi mi? False ise `detect_all` HEP bos doner ve
                      sistem GPS fazinda calismaya devam eder (cokme yok)
        engine      : TensorRT motoru mu kosuyor, yoksa .pt mi?
        fallback    : motordan .pt'ye DUSULDUYSE gerekcesi (None = dusulmedi)
        fails       : `detect_all` icinde yutulan hata sayisi. Bos liste "hedef
                      yok" ile ayni gorundugu icin hatanin en azindan SAYILMASI
                      gerekir, yoksa bozulma sessiz olur.
        last_error  : yutulan son hatanin metni
    """

    def __init__(self, model_path=MODEL_PATH, conf=CONF_FLOOR, imgsz=IMGSZ,
                 device=None, half=None):
        """Agirligi yukler; yuklenemezse `ready=False` ile sessizce devam eder.

        model_path : yuklenecek agirlik (.pt ya da .engine)
        conf       : 0..1; predict esigi (kutu uretmek icin asgari guven)
        imgsz      : px; cikarim olcegi. Modelin EGITIM olcegiyle ayni olmalidir;
                     farkli olursa uzak/kucuk hedef once kaybolur.
        device     : "cuda" | "cpu" | None (None -> CUDA varsa cuda)
        half       : FP16 cikarim; None -> cuda'da acik, cpu'da kapali.
                     TensorRT motorunda kesinlik DERLENIRKEN gomuldugu icin
                     yok sayilir.
        """
        self.ready = False
        self.model = None
        self.names = {}
        self.conf = float(conf)
        self.imgsz = int(imgsz)
        self.device = device
        self.half = half  # FP16 (None -> cuda'da otomatik AC, cpu'da kapali)
        self.model_path = model_path
        self.engine = False       # TensorRT motoru mu kosuyor?
        self.fallback = None      # motordan .pt'ye dusuldiyse GEREKCESI
        self.fails = 0            # detect_all icinde yutulan hata sayisi
        self.last_error = None
        self._fp16_kwargs = {}
        self.error = None
        try:
            if self.device is None:
                try:
                    import torch
                    self.device = "cuda" if torch.cuda.is_available() else "cpu"
                except Exception:
                    self.device = "cpu"
            if self.half is None:
                self.half = (self.device == "cuda")
            self._load(model_path)
        except Exception as e:
            self.ready = False
            self.error = repr(e)

    def _load(self, path):
        """Agirligi yukle; TensorRT motoru acilmazsa GEREKCESIYLE .pt'ye don.

        ⛔ SESSIZ DUSUS YOK. Motor karta/surucuye/TensorRT surumune derlenir,
           yani makine degisince ACILMAZ. O anda dedektoru tamamen kaybetmek
           (gorsel faz hic acilmaz) .pt ile devam etmekten KOTUDUR — ama
           dustugumuz `self.fallback`'e yazilir ve camera.py ekrana basar.
        """
        from ultralytics import YOLO

        engine = str(path).endswith(".engine")
        if engine and self.device != "cuda":
            # Motor yalnizca GPU'da kosar; CPU'da deserialize bile edilmez.
            return self._load_pt(path, "CUDA yok")
        try:
            self.model = YOLO(path)
            self.model_path = path
            self.engine = engine
            # ⚠ MOTORDA KESINLIK DERLENIRKEN GOMULDU. predict'e half/quantize
            #   gecmek anlamsizdir: TensorRT arka ucu girdi tipini motorun
            #   baglantilarindan okur, arg'i yok sayar (bazi surumlerde hata verir).
            if engine:
                self.half = False
            self._warmup(strict=engine)
            self.names = dict(getattr(self.model, "names", {}) or {})
            self.ready = True
        except Exception as e:
            if engine:
                return self._load_pt(path, repr(e))
            raise

    def _load_pt(self, engine_path, why):
        """Motor kullanilamadi -> ayni agirligin .pt surumune don."""
        self.fallback = why
        self.engine = False
        self.half = (self.device == "cuda")
        pt = os.path.splitext(engine_path)[0] + ".pt"
        # Olcu MOTORUN basligindan degil, artik AGIRLIGIN tablosundan gelir.
        self.imgsz = int(os.environ.get("AVCI_IMGSZ") or imgsz_for_model(pt))
        self._load(pt)

    def _warmup(self, strict=False):
        """Ilk predict yavastir -> onceden isit. Ayni anda FP16 API'sini sec:
        yeni ultralytics `quantize="fp16"`, eskisinde bu arg YOK -> `half=True`.

        strict=True (TensorRT motoru): hata YUTULMAZ. Motorun girdi sekli
        derlenirken sabitlendi; yanlis olcekte arka uc assert atar ve o hata
        yutulursa detect_all omur boyu BOS liste doner — sessiz bozulma.
        """
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
            if strict:
                raise

    @staticmethod
    def _in_mask(cxn, cyn, mask):
        """NORMALIZE (0..1) merkez, verilen dikdortgenlerden birinin ICINDE mi?

        cxn, cyn : 0..1; kutu merkezinin normalize kordinati
        mask     : [(x0,y0,x1,y1), ...] normalize dikdortgenler
        -> True ise kutu elenir
        """
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
        """Bir karedeki TUM tespitleri dondurur.

        frame : BGR ndarray (ultralytics numpy diziyi BGR varsayar)
        mask  : normalize [(x0,y0,x1,y1), ...]; merkezi bu bolgelerde kalan
                kutular ELENIR (varsayilan: kendi pervanemiz)
        -> [{cx, cy, w, h, conf, cls, W, H, t}, ...] — conf'a gore AZALAN sirali,
           bos olabilir. Koordinatlar PIKSEL, `t` bir perf_counter damgasidir.

        ⚠ Hata durumunda da BOS LISTE doner (hata yutulur) — cunku tek bir kotu
          kare yuzunden guduum dongusunun cokmesi kabul edilemez. Yutulan hata
          `fails`/`last_error`e yazilir ve `camera.py` ilkini ekrana basar.
        """
        if not self.ready or frame is None:
            return []
        try:
            res = self.model.predict(frame, imgsz=self.imgsz, conf=self.conf,
                                     device=self.device, verbose=False,
                                     **self._fp16_kwargs)[0]
        except Exception as e:
            # Bos liste "hedef yok" ile ayni gorunur -> hatayi en azindan SAY.
            self.fails += 1
            self.last_error = repr(e)
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


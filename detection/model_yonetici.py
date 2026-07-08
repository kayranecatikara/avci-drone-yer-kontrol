# -*- coding: utf-8 -*-
"""
================================================================================
MODEL YONETICI — models/ registry + thread-safe hot-swap + canli metrikler
================================================================================
(docs/master_prompt_model_yonetimi.md). Amac: models/ altina .pt atinca KOD
DEGISIKLIGI OLMADAN arayuzde gorunsun, ucus/test sirasinda takilip cikarilsin,
performansi canli izlensin, CSV'ye loglansin. Kotu detection + kotu pose'lar +
gelecek yeniler kiyaslanabilsin (yeni modelin hedefini SAYIYLA koyar).

PIPELINE SOZLESMELERI ESAS: cekirdek {cx,cy,conf}+opsiyonel keypoints
degismez; pose->detect swap'inde keypoints kaybolur -> pipeline pose'suz moda
duser (PnP pasif, OIPN 0, IBVS fallback) — guidance/FSM'e DOKUNULMAZ.
Per-model yaml 'conf' YALNIZCA gorsellestirme/metrik; kilit zincirine GIRMEZ
(uretim conf esigi Cfg.VIS_CONF_MIN, muhafazakar, yerinde).

HOT-SWAP: yeni model ARKA PLAN thread'inde yuklenir (algi eski modelle
kesintisiz devam) -> 3 dummy warmup (CUDA context + autotune) -> lock'lu TEK
atomik referans atamasi -> eski birak + empty_cache. Hata -> eski aktif kalir.

LATENCY: GPU'da torch.cuda.synchronize() ile olculur (async kernel launch degil
fiili sure). Kayan pencere (100 frame): ort/p95 ms, FPS, tespit sayisi,
ort/maks conf, (pose) gorunur kp + ort kp conf + PnP-uygun oran.
================================================================================
"""
import glob
import os
import threading
import time
from collections import deque

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJ_ROOT = os.path.dirname(_HERE)
MODELS_DIR = os.path.join(_PROJ_ROOT, "models")

BEKLENEN_KPT_SHAPE = (6, 3)     # PnP sozlesmesi; uymayan pose modeli reddedilir
PENCERE = 100                   # kayan metrik penceresi (frame)


def _yaml_oku(yol):
    """Basit yaml okuyucu (PyYAML varsa onu, yoksa satir-bazli minimal parser).
    Beklenen anahtarlar: imgsz, conf, iou, half, sema, aciklama."""
    cfg = {}
    if not os.path.isfile(yol):
        return cfg
    try:
        import yaml
        with open(yol, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        return cfg if isinstance(cfg, dict) else {}
    except Exception:
        pass
    try:                                    # PyYAML yoksa: key: value satirlari
        with open(yol, "r", encoding="utf-8") as f:
            for satir in f:
                s = satir.split("#", 1)[0].strip()
                if ":" not in s:
                    continue
                k, v = s.split(":", 1)
                k, v = k.strip(), v.strip()
                if not k:
                    continue
                vl = v.lower()
                if vl in ("true", "false"):
                    cfg[k] = (vl == "true")
                else:
                    try:
                        cfg[k] = int(v) if v.isdigit() else float(v)
                    except ValueError:
                        cfg[k] = v.strip('"\'')
    except Exception:
        pass
    return cfg


class ModelKaydi:
    """models/ altindaki tek .pt'nin metadata'si (yuklemeden once bilinen)."""

    def __init__(self, yol):
        self.yol = yol
        self.ad = os.path.splitext(os.path.basename(yol))[0]
        self.yaml = _yaml_oku(os.path.splitext(yol)[0] + ".yaml")
        self.boyut_mb = round(os.path.getsize(yol) / (1024 * 1024), 1)
        # yuklendikten sonra doldurulur
        self.task = None
        self.kpt_shape = None
        self.uyumsuz = None       # None=bilinmiyor, ""=uyumlu, "..."=red nedeni

    @property
    def sema(self):
        return str(self.yaml.get("sema", "kuyruk_ucu"))

    def ozet(self):
        return {"ad": self.ad, "boyut_mb": self.boyut_mb, "task": self.task,
                "kpt_shape": list(self.kpt_shape) if self.kpt_shape else None,
                "sema": self.sema, "uyumsuz": self.uyumsuz,
                "aciklama": self.yaml.get("aciklama", "")}


class MetrikPenceresi:
    """Son PENCERE frame'in metrik ozeti (thread-guvenli degil; tek algi thread'i yazar)."""

    def __init__(self):
        self.ms = deque(maxlen=PENCERE)
        self.tespit_n = deque(maxlen=PENCERE)
        self.conf = deque(maxlen=PENCERE)
        self.kp_gorunur = deque(maxlen=PENCERE)
        self.kp_conf = deque(maxlen=PENCERE)
        self.pnp_uygun = deque(maxlen=PENCERE)     # 1/0: >=4 kp esik ustu

    def ekle(self, ms, tespitler):
        self.ms.append(ms)
        self.tespit_n.append(len(tespitler))
        en = max((float(d.get("conf", 0)) for d in tespitler), default=0.0)
        self.conf.append(en)
        # pose ekleri (ilk/en-yuksek-conf tespitin keypoints'i)
        kp = tespitler[0].get("keypoints") if tespitler else None
        if kp:
            confs = [c for *_xy, c in kp]
            gorunur = sum(1 for c in confs if c >= 0.5)
            self.kp_gorunur.append(gorunur)
            self.kp_conf.append(sum(confs) / len(confs) if confs else 0.0)
            self.pnp_uygun.append(1 if gorunur >= 4 else 0)

    def ozet(self):
        import numpy as np
        d = {}
        if self.ms:
            a = np.array(self.ms)
            d["inference_ms_ort"] = float(a.mean())
            d["inference_ms_p95"] = float(np.percentile(a, 95))
            d["fps"] = float(1000.0 / max(a.mean(), 1e-6))
        if self.tespit_n:
            d["tespit_ort"] = float(sum(self.tespit_n) / len(self.tespit_n))
        if self.conf:
            d["conf_ort"] = float(sum(self.conf) / len(self.conf))
            d["conf_max"] = float(max(self.conf))
        if self.kp_gorunur:
            d["kp_gorunur_ort"] = float(sum(self.kp_gorunur) / len(self.kp_gorunur))
            d["kp_conf_ort"] = float(sum(self.kp_conf) / len(self.kp_conf))
            d["pnp_uygun_oran"] = float(sum(self.pnp_uygun) / len(self.pnp_uygun))
        d["ornek"] = len(self.ms)
        return d


class ModelYonetici:
    """models/ registry + aktif model + hot-swap + metrik. Algi thread'i
    tespit_hepsi() cagirir (aktif modelle inference + metrik); arayuz thread'i
    model_yukle()/metrikler()/durum() cagirir."""

    def __init__(self, baslangic_conf=0.25, imgsz=640):
        self._lock = threading.Lock()
        self.kayitlar = {}                 # ad -> ModelKaydi
        self._aktif = None                 # HedefDedektor (atomik referans)
        self._aktif_ad = None
        self._yukleniyor = None            # yuklenmekte olan ad (arayuz rozeti)
        self._hata = None
        self.conf = float(baslangic_conf)
        self.imgsz = int(imgsz)
        self.metrik = MetrikPenceresi()
        self._swap_olaylari = []           # CSV segment sinirlari (ad, t)
        self.tara()

    # ---- registry ----
    def tara(self):
        """models/ tarar; yeni .pt'leri kayitlara ekler (mevcutu korur)."""
        yeni = {}
        for yol in sorted(glob.glob(os.path.join(MODELS_DIR, "*.pt"))):
            ad = os.path.splitext(os.path.basename(yol))[0]
            yeni[ad] = self.kayitlar.get(ad) or ModelKaydi(yol)
        with self._lock:
            self.kayitlar = yeni
        return list(yeni.keys())

    def modelleri_listele(self):
        with self._lock:
            return [k.ozet() for k in self.kayitlar.values()]

    def aktif_ad(self):
        return self._aktif_ad

    # ---- hot-swap ----
    def model_yukle(self, ad, arka_plan=True):
        """Modeli (arka plan thread'inde) yukle + warmup + atomik swap.
        Hata -> eski aktif kalir, self._hata dolar."""
        if ad not in self.kayitlar:
            self._hata = "model yok: %s" % ad
            return False
        if arka_plan:
            threading.Thread(target=self._yukle_isi, args=(ad,), daemon=True).start()
            return True
        return self._yukle_isi(ad)

    def _yukle_isi(self, ad):
        from detection.gorsel_tespit import HedefDedektor
        self._yukleniyor = ad
        self._hata = None
        kayit = self.kayitlar[ad]
        imgsz = int(kayit.yaml.get("imgsz", self.imgsz))
        try:
            ded = HedefDedektor(kayit.yol, conf=self.conf, imgsz=imgsz)
        except Exception as e:
            self._hata = "yukleme hatasi (%s): %r" % (ad, e)
            self._yukleniyor = None
            return False
        if not ded.hazir:
            self._hata = "yuklenemedi (%s): %s" % (ad, ded.hata)
            self._yukleniyor = None
            return False
        # metadata + kpt_shape kapisi (pose icin)
        kayit.task = ded.task
        kayit.kpt_shape = ded.kpt_shape
        if ded.task == "pose" and ded.kpt_shape != BEKLENEN_KPT_SHAPE:
            kayit.uyumsuz = "kpt_shape %s != %s (PnP uyumsuz)" % (
                ded.kpt_shape, BEKLENEN_KPT_SHAPE)
            self._hata = kayit.uyumsuz
            self._yukleniyor = None
            return False
        kayit.uyumsuz = ""
        # 3 dummy warmup (CUDA context + autotune; ilk inference'ler 10-100x yavas)
        try:
            import numpy as np
            bos = np.zeros((imgsz, imgsz, 3), dtype="uint8")
            for _ in range(3):
                ded.tespit_hepsi(bos)
        except Exception:
            pass
        # atomik swap (lock'lu tek referans atamasi)
        with self._lock:
            eski = self._aktif
            self._aktif = ded
            self._aktif_ad = ad
            self._swap_olaylari.append((ad, time.time()))
        self.metrik = MetrikPenceresi()      # yeni model -> yeni pencere (segment)
        # eski birak + VRAM temizle
        del eski
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass
        self._yukleniyor = None
        return True

    # ---- inference (algi thread'i) ----
    @property
    def hazir(self):
        """algi_hatti getattr(dedektor,'hazir') ile uyum -> property (metod degil)."""
        return self._aktif is not None and getattr(self._aktif, "hazir", False)

    def tespit_hepsi(self, frame):
        """Aktif modelle inference + metrik. Model yoksa []."""
        ded = self._aktif
        if ded is None or not ded.hazir or frame is None:
            return []
        ded.conf = float(self.conf)          # canli conf (yalniz gorsel/metrik)
        t0 = time.perf_counter()
        try:
            tespitler = ded.tespit_hepsi(frame)
        except Exception:
            tespitler = []
        self._senkron()
        ms = (time.perf_counter() - t0) * 1000.0
        try:
            self.metrik.ekle(ms, tespitler)
        except Exception:
            pass
        return tespitler

    def _senkron(self):
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.synchronize()     # dogru latency (async kernel degil)
        except Exception:
            pass

    # ---- arayuz ----
    def metrikler(self):
        return self.metrik.ozet()

    def durum(self):
        with self._lock:
            aktif = self._aktif_ad
        kayit = self.kayitlar.get(aktif) if aktif else None
        return {"aktif": aktif, "yukleniyor": self._yukleniyor, "hata": self._hata,
                "task": (kayit.task if kayit else None),
                "sema": (kayit.sema if kayit else None),
                "kpt_shape": (list(kayit.kpt_shape) if kayit and kayit.kpt_shape else None),
                "flip_idx_uyari": (kayit.task == "pose" if kayit else False)}

    def aktif_sema(self):
        with self._lock:
            aktif = self._aktif_ad
        kayit = self.kayitlar.get(aktif) if aktif else None
        return kayit.sema if kayit else "kuyruk_ucu"

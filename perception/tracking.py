# -*- coding: utf-8 -*-
"""
perception/tracking.py — HybridSort (boxmot) ile kareler-arasi kimlik surekliligi.

Dedektor TEK kareyi gorur; takipci kareler ARASI kimligi surdurur: kisa tespit
bosluklarini Kalman ongorusuyle koprular (max_age), zayif tespitleri BYTE
eslesmesiyle degerlendirir (use_byte + low_thresh) ve tek-kare parazitin izi
kapmasini engeller (min_hits).

Bu sarmalayici tek-hedef sozlesmesi sunar:
    Tracker().update(detections, frame) -> en iyi (en guvenli) iz | None

Cikti yalnizca O KARDE OLCULEN izleri icerir (coast/tahmin kutusu yayinlanmaz):
guduum ancak gercek gorsel temasla komut uretsin; tespit deliklerini gorsel faz
kendi bayatlik esigiyle (control.visual_tracking.VisualCfg.STALE_S) yonetir.

DAYANIKLILIK: boxmot kurulu degilse ready=False -> update() ham argmax kutusunu
dondurur (takip katmani devre disi, sistem calismaya devam eder).
"""
import numpy as np

# Takipci parametreleri — boxmot HybridSort'un KENDI varsayilanlari. Tek bilincli
# sapma `with_reid=False`tur (asagida gerekcesi var); geri kalani, ustunde kendi
# olcumumuz olmadigi icin kasitli olarak varsayilanda birakilmistir.
TRACKER_PARAMS = {
    # --- BaseTracker: izin YASAM DONGUSU ---
    "det_thresh": 0.3,      # 0..1; bir tespitin ize beslenebilmesi icin gereken asgari guven
    "max_age": 30,          # kare; iz, eslesen tespit gelmeden bu kadar kare YASAR
                            # (kisa tespit bosluklarini Kalman ongorusuyle koprular)
    "max_obs": 50,          # adet; iz basina saklanan gecmis gozlem sayisi
    "min_hits": 3,          # kare; iz ONAYLANMADAN once gereken art arda eslesme.
                            # TEK KARELIK parazitin iz kapmasini engelleyen sey budur.
    "iou_threshold": 0.3,   # 0..1; tespit <-> iz eslestirmesinde asgari IoU ortusmesi
    "asso_func": "iou",     # eslestirme olcutu (IoU)

    # --- HybridSort'a ozgu ---
    "with_reid": False,     # ⭐ BILINCLI SAPMA: gorunum (ReID) modeli KAPALI. Tek
                            # sinifli ve tek hedefli bir gorevde kimligi gorunumden
                            # ayirt etmeye gerek yok; acik olsaydi her karede ayri
                            # bir ag kosardi.
    "low_thresh": 0.1,      # 0..1; BYTE'in IKINCI asamasinda degerlendirilen dusuk
                            # guvenli tespitlerin alt siniri. Bu kutular MEVCUT bir izi
                            # yasatabilir ama YENI iz ACAMAZ.
    "delta_t": 3,           # kare; iz yonunun (hiz vektorunun) kac kare geriye bakilarak
                            # kestirildigi
    "inertia": 0.05,        # 0..1; eslestirme maliyetinde yon tutarliliginin agirligi
    "use_byte": True,       # BYTE iki asamali eslestirme acik mi?
    "longterm_bank_length": 30,  # kare; uzun donem gorunum bankasinin uzunlugu (ReID kapali -> etkisiz)
    "alpha": 0.9,           # 0..1; gorunum gomulmesinin EMA katsayisi (ReID kapali -> etkisiz)
    "track_thresh": 0.5,    # 0..1; yuksek/dusuk guven ayrimi (BYTE'in iki asamasini bolen esik)
    "EG_weight_high_score": 4.6,  # agirlik; gomulme-guduumlu eslestirmenin yuksek guvenli asamadaki payi
    "EG_weight_low_score": 1.3,   # agirlik; ayni seyin dusuk guvenli asamadaki payi
    "TCM_first_step": True,       # zamansal tutarlilik dizgesi birinci asamada uygulansin mi?
    "TCM_byte_step": True,        # ... BYTE asamasinda uygulansin mi?
    "TCM_byte_step_weight": 1.0,  # agirlik; o asamadaki payi
    "high_score_matching_thresh": 0.7,  # 0..1; yuksek guvenli eslestirmenin kabul esigi
    # Asagidaki dort deger UZUN DONEM ReID icindir; `longterm_reid_weight = 0.0`
    # oldugu ve `with_reid` kapali oldugu icin fiilen ETKISIZDIRLER.
    "with_longterm_reid": True,
    "longterm_reid_weight": 0.0,
    "with_longterm_reid_correction": True,
    "longterm_reid_correction_thresh": 0.4,
    "longterm_reid_correction_thresh_low": 0.4,
}
# Kamera-hareket telafisi. OLCULDU (1920x1200, n=30/kol, update() basina):
#     ecc  9.66 ms   |  sof  3.51 ms   |  yok  0.41 ms   |  ecc@yari-coz  1.76 ms
# ⛔ ECC KULLANMAYIN. Asagidaki _silence() yorumunun kendisi ECC'nin dokusu az
#   GOKYUZU karelerinde "did not converge" bastigini soyluyor — yani 9.66 ms
#   yakip guvenilmez bir donusum uretiyor. `sof` (seyrek optik akis) ayni isi
#   3.5 ms'de ve gokyuzunde daha saglam yapar.
#   Gecerli degerler (boxmot 22): "ecc", "orb", "sift", "sof".
CMC_METHOD = "sof"

# boxmot modul duzeni surumler arasinda IKI KEZ degisti; en YENIDEN eskiye dene.
# ⚠ 22.0.0'da `hybridsort` bir PAKET degil, duz MODULDUR -> eski iki yol da
#   ModuleNotFoundError verir. Bu SESSIZ bir bozulmaydi: ready=False olunca
#   sistem ham argmax'a duser, kimlik surekliligi ve tek-kare parazit filtresi
#   kaybolur ama hicbir sey cokmez.
_HYBRIDSORT_PATHS = (
    "boxmot.trackers.bbox.hybridsort",            # v22+  (duz modul)
    "boxmot.trackers.bbox.hybridsort.hybridsort",  # v19-v21
    "boxmot.trackers.hybridsort.hybridsort",       # eski duzen
)


def _hybridsort_class():
    """Kurulu boxmot surumune uyan HybridSort sinifini bulur."""
    import importlib
    errors = []
    for path in _HYBRIDSORT_PATHS:
        try:
            return getattr(importlib.import_module(path), "HybridSort")
        except (ImportError, AttributeError) as e:
            errors.append("%s: %s" % (path, e))
    raise ImportError("HybridSort bulunamadi -> " + " | ".join(errors))


def _silence():
    """ECC "did not converge" gibi kare basi WARNING selini keser (dokusu az
    gokyuzu karelerinde her karede basar). ERROR gorunmeye devam eder.
    DIKKAT: boxmot kendi logger'ini kurarken seviyeyi INFO'ya geri cekiyor ->
    bu cagri tracker OLUSTURULDUKTAN SONRA yapilmali."""
    import logging
    logging.getLogger("boxmot").setLevel(logging.ERROR)


class Tracker:
    """HybridSort sarmalayicisi — cok-hedefli takipciyi TEK HEDEF sozlesmesine indirger.

    ready  : takipci kuruldu mu? False ise `update()` HAM ARGMAX kutusuna duser
             (boxmot kurulu degil ya da modul yolu tutmadi). Sistem cokmez, yalnizca
             kimlik surekliligi ve tek-kare parazit filtresi kaybolur.
    error  : `ready=False` ise sebebi (arayuz bunu yazdirir)
    tracks : son karenin ham iz listesi — yalnizca gosterge/tani icin
    """

    def __init__(self):
        """Takipciyi kurar; kurulamazsa `ready=False` ile sessizce devam eder."""
        self.ready = False
        self.error = None
        self._tr = None
        self.tracks = []
        self.reset()

    def reset(self):
        """Takipciyi YENIDEN KURAR — yeni gorev bayat iz/kimlikle baslamasin.

        ⛔ ORNEK YENIDEN KURULUR, yalnizca liste temizlenmez. HybridSort'un ic
          durumu (Kalman izleri, kare sayaci, kimlik dagitici) ornegin
          KENDISINDEDIR; sadece `self.tracks`i bosaltmak onlari birakirdi ve
          takipci izleri `max_age` kadar ileri tasidigi icin yeni gorev HAYALET
          kutuyla acilirdi.
        """
        self.tracks = []
        try:
            HybridSort = _hybridsort_class()
            self._tr = HybridSort(reid_model=None, cmc_method=CMC_METHOD, **TRACKER_PARAMS)
            _silence()
            self.ready = True
        except Exception as e:
            self._tr = None
            self.ready = False
            self.error = repr(e)

    def update(self, detections, frame):
        """Bu karenin tespitlerini takipciden gecirir ve EN IYI izi dondurur.

        detections : `detector.detect_all` ciktisi (PIKSEL, conf'a gore sirali)
        frame      : BGR ndarray — kamera-hareket telafisi (CMC) icin gerekir
        -> {track_id, cx, cy, w, h, conf, cls, W, H, t} | None (iz yok)

        "En iyi" olcut EN YUKSEK GUVENdir. Kare olculeri ve zaman damgasi
        eslesen ORIJINAL tespitten tasinir: takipci kutuyu yeniden hesaplar
        ama `t` damgasini uretmez, bayatlik hesabi ise ona baglidir.
        """
        if not self.ready or frame is None or not hasattr(frame, "shape"):
            self.tracks = []
            return detections[0] if detections else None  # takip yok -> ham argmax

        if detections:
            arr = np.empty((len(detections), 6), dtype=np.float32)
            for i, d in enumerate(detections):
                cx, cy, w, h = float(d["cx"]), float(d["cy"]), float(d["w"]), float(d["h"])
                arr[i] = (cx - w / 2.0, cy - h / 2.0, cx + w / 2.0, cy + h / 2.0,
                          float(d.get("conf", 0.9)), float(d.get("cls", 0)))
        else:
            arr = np.empty((0, 6), dtype=np.float32)

        try:
            out = np.asarray(self._tr.update(arr, frame))
        except Exception:
            self.tracks = []
            return None
        self.tracks = out.tolist() if len(out) else []
        if not len(out):
            return None

        best = out[int(np.argmax(out[:, 5]))]  # en yuksek conf'lu iz
        x1, y1, x2, y2, tid, conf, cls, ind = [float(v) for v in best]
        cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0

        # Eslesen ORIJINAL tespitten kare olculerini/zaman damgasini tasi.
        src = None
        ii = int(round(ind))
        if detections and 0 <= ii < len(detections):
            src = detections[ii]
        d = {"track_id": int(round(tid)),
             "cx": cx, "cy": cy, "w": x2 - x1, "h": y2 - y1, "conf": conf,
             "cls": int(round(cls)),
             "W": int(src["W"]) if src else int(frame.shape[1]),
             "H": int(src["H"]) if src else int(frame.shape[0])}
        if src is not None and "t" in src:
            d["t"] = src["t"]
        return d

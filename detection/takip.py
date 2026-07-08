# -*- coding: utf-8 -*-
"""
================================================================================
TAKIP — ByteTrack (tek-hedef sadelestirmesiyle, coklu-track destekli) + gyro-CMC
================================================================================
YARISMA PIPELINE FAZ 1. best.pt bbox'larini ZAMANSAL olarak baglar: parazit/blur
aninda conf dusen Talon izi kopmaz, tek-kare yanlis pozitifler CONFIRMED olamadan
oler (−30 puanlik yanlis kilit paketine karsi zamansal filtre).

BYTE ASSOCIATION (ByteTrack ozu):
  tespitler conf'a gore IKIYE ayrilir. Yuksek conf'lular mevcut track'lerle ONCE
  eslesir (IoU); eslesmeyen track'ler dusuk conf'lularla IKINCI tur eslesir.
  Dusuk conf'lu tespit YENI track baslatamaz, yalniz mevcut track'i surdurur.

DURUMLAR: TENTATIVE -> (min_hits ardisik eslesme) CONFIRMED -> (eslesme yok)
  LOST/coast -> (max_coast asimi) REMOVED. min_hits mevcut FSM'nin "5 kare YOLO
  onayi" kuralini devralir (ana_kontrol'deki ham sayac kalkar, FSM bunu sorgular).

KALMAN: goruntu duzleminde CV (sabit hiz) modeli. state = [cx, cy, s, r,
  vcx, vcy, vs] (s=alan, r=en-boy; r hizsiz — SORT konvansiyonu). Coast =
  olcumsuz tahminle izi surdurme (max ~0.5 sn).

GYRO-CMC (kamera hareket telafisi): avcinin donusu track tahminlerini
  eslestirme ONCESI warp eder (H = K·R_Δ·K⁻¹). Homografi/R_Δ algi_hattinda
  hesaplanip guncelle(H=...) ile verilir; bu modul saf tuketicidir. Goruntu-
  tabanli CMC (ORB/ECC) KULLANILMAZ (gokyuzu feature'siz).

SAF MANTIK: sim/YOLO olmadan sentetik tespitle unit-test edilir (test/).
Cfg deseni + Turkce isimlendirme (proje konvansiyonu).
================================================================================
"""
import numpy as np


class TakipCfg:
    # --- BYTE conf esikleri ---
    CONF_YUKSEK = 0.5      # >= : birinci tur eslestirme + yeni track acabilir
    CONF_DUSUK  = 0.1      # >= (ve < YUKSEK) : yalniz ikinci tur (mevcut track'i surdur)
    # --- Track yasam dongusu ---
    MIN_HITS   = 5         # TENTATIVE->CONFIRMED ardisik eslesme (FSM "5 kare" kurali)
    MAX_COAST  = 25        # olcumsuz tahminle surdurme tavani (tik; 50Hz'de ~0.5 sn)
    IOU_ESIK   = 0.2       # eslesme icin asgari IoU (warp sonrasi)
    # --- Kalman gurultu ---
    STD_OLCUM_KONUM = 1.0  # px olcum gurultusu (cx,cy)
    STD_OLCUM_ALAN  = 10.0 # alan/en-boy olcum gurultusu (izafi)
    STD_SUREC_KONUM = 1.0  # surec (ivme) gurultusu konum
    STD_SUREC_HIZ   = 0.01 # surec gurultusu hiz


# ============================================================
#  Kalman filtresi — goruntu duzlemi CV (SORT tarzi)
# ============================================================
class _KalmanKutu:
    """bbox durumu [cx, cy, s, r] + hizlari [vcx, vcy, vs]. r (en-boy) hizsiz."""

    def __init__(self, bbox, cfg):
        cx, cy, s, r = _bbox_to_z(bbox)
        self.x = np.array([cx, cy, s, r, 0.0, 0.0, 0.0], float)
        self.P = np.diag([10.0, 10.0, 10.0, 10.0, 1e4, 1e4, 1e4]).astype(float)
        self.cfg = cfg
        self._son_alan = s

    def _F(self, dt):
        F = np.eye(7)
        F[0, 4] = dt      # cx += vcx*dt
        F[1, 5] = dt      # cy += vcy*dt
        F[2, 6] = dt      # s  += vs*dt
        return F

    def _Q(self, dt):
        c = self.cfg
        q = np.zeros((7, 7))
        for i in (0, 1, 2):
            q[i, i] = (c.STD_SUREC_KONUM * dt) ** 2
        for i in (4, 5, 6):
            q[i, i] = (c.STD_SUREC_HIZ) ** 2
        q[3, 3] = 1e-4    # en-boy yavas degisir
        return q

    def tahmin(self, dt):
        F = self._F(dt)
        self.x = F @ self.x
        if self.x[2] <= 0:               # alan negatife dusmesin
            self.x[2] = max(self.x[2], 1.0)
        self.P = F @ self.P @ F.T + self._Q(dt)
        return self.x

    def guncelle_olcum(self, bbox):
        z = np.array(_bbox_to_z(bbox), float)
        H = np.zeros((4, 7))
        H[0, 0] = H[1, 1] = H[2, 2] = H[3, 3] = 1.0
        c = self.cfg
        R = np.diag([c.STD_OLCUM_KONUM ** 2, c.STD_OLCUM_KONUM ** 2,
                     c.STD_OLCUM_ALAN ** 2, (c.STD_OLCUM_ALAN * 0.1) ** 2])
        y = z - H @ self.x
        S = H @ self.P @ H.T + R
        K = self.P @ H.T @ np.linalg.inv(S)
        self.x = self.x + K @ y
        self.P = (np.eye(7) - K @ H) @ self.P
        self._son_alan = self.x[2]

    def warp_merkez(self, H):
        """gyro-CMC: merkez (cx,cy)'yi homografiyle tasi (eslestirme oncesi)."""
        if H is None:
            return
        p = np.array([self.x[0], self.x[1], 1.0])
        q = H @ p
        if abs(q[2]) > 1e-9:
            self.x[0] = q[0] / q[2]
            self.x[1] = q[1] / q[2]

    def bbox(self):
        return _z_to_bbox(self.x[0], self.x[1], self.x[2], self.x[3])


def _bbox_to_z(bbox):
    """(cx,cy,w,h) -> (cx, cy, s=alan, r=en-boy w/h)."""
    cx, cy, w, h = bbox
    return cx, cy, float(w) * float(h), (float(w) / float(h) if h > 1e-6 else 1.0)


def _z_to_bbox(cx, cy, s, r):
    """(cx,cy,s,r) -> (cx,cy,w,h). w=sqrt(s*r), h=s/w."""
    s = max(float(s), 1.0)
    r = max(float(r), 1e-3)
    w = np.sqrt(s * r)
    h = s / w if w > 1e-6 else 1.0
    return float(cx), float(cy), float(w), float(h)


def _iou(a, b):
    """IoU: a,b = (cx,cy,w,h)."""
    ax1, ay1 = a[0] - a[2] / 2, a[1] - a[3] / 2
    ax2, ay2 = a[0] + a[2] / 2, a[1] + a[3] / 2
    bx1, by1 = b[0] - b[2] / 2, b[1] - b[3] / 2
    bx2, by2 = b[0] + b[2] / 2, b[1] + b[3] / 2
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    kesisim = iw * ih
    birlesim = a[2] * a[3] + b[2] * b[3] - kesisim
    return kesisim / birlesim if birlesim > 1e-9 else 0.0


# ============================================================
#  Track
# ============================================================
_TENTATIVE, _CONFIRMED, _LOST, _REMOVED = "TENTATIVE", "CONFIRMED", "LOST", "REMOVED"


class Track:
    _sonraki_id = 1

    def __init__(self, det, cfg):
        self.cfg = cfg
        self.id = Track._sonraki_id
        Track._sonraki_id += 1
        self.kf = _KalmanKutu((det["cx"], det["cy"], det["w"], det["h"]), cfg)
        self.durum = _TENTATIVE
        self.hits = 1                 # toplam eslesme
        self.ardisik_hit = 1          # ardisik eslesme (TENTATIVE->CONFIRMED)
        self.coast = 0                # ardisik olcumsuz tik
        self.yas = 1                  # toplam tik
        self.conf = float(det.get("conf", 0.0))
        self.conf_toplam = self.conf
        self.conf_n = 1
        self.son_det = det            # son OLCULEN tespit (keypoints tasima icin)
        self.tespit_mi = True         # bu tik OLCUM eslesti mi (coast'ta False)

    @property
    def ort_conf(self):
        return self.conf_toplam / max(self.conf_n, 1)

    def tahmin(self, dt, H_cmc=None):
        self.kf.tahmin(dt)
        self.kf.warp_merkez(H_cmc)     # gyro-CMC: eslestirme oncesi warp
        self.yas += 1
        self.tespit_mi = False         # eslesirse guncelle()'de True olur

    def guncelle(self, det):
        self.kf.guncelle_olcum((det["cx"], det["cy"], det["w"], det["h"]))
        self.hits += 1
        self.ardisik_hit += 1
        self.coast = 0
        self.conf = float(det.get("conf", 0.0))
        self.conf_toplam += self.conf
        self.conf_n += 1
        self.son_det = det
        self.tespit_mi = True
        if self.durum == _TENTATIVE and self.ardisik_hit >= self.cfg.MIN_HITS:
            self.durum = _CONFIRMED
        elif self.durum == _LOST:
            self.durum = _CONFIRMED    # yeniden yakalandi

    def eslesmedi(self):
        self.ardisik_hit = 0
        self.coast += 1
        self.tespit_mi = False
        if self.durum == _TENTATIVE:
            self.durum = _REMOVED      # tek-kare parazit: dogrulanamadan ol
        elif self.durum == _CONFIRMED:
            self.durum = _LOST
        if self.coast > self.cfg.MAX_COAST:
            self.durum = _REMOVED

    def bbox(self):
        return self.kf.bbox()

    def cikti(self):
        """AlgiCiktisi.hedef sozlesmesi (geriye uyum: cx,cy,conf cekirdegi)."""
        cx, cy, w, h = self.bbox()
        d = {"track_id": self.id, "bbox": (cx, cy, w, h),
             "cx": cx, "cy": cy, "w": w, "h": h,
             "conf": self.conf, "tespit_mi": self.tespit_mi,
             "track_durumu": self.durum}
        kp = self.son_det.get("keypoints") if self.son_det else None
        if kp is not None and self.tespit_mi:
            d["keypoints"] = kp        # coast'ta keypoint tasima (bayat poz gitmesin)
        # son OLCULEN tespitin W/H'sini (goruntu boyutu) + sinif indeksini tasi
        if self.son_det:
            d["W"] = self.son_det.get("W")
            d["H"] = self.son_det.get("H")
            d["cls"] = self.son_det.get("cls", -1)
            if self.tespit_mi and "t" in self.son_det:
                d["t"] = self.son_det["t"]   # olcum tiki: kare zamani (UI yas telafisi)
        return d


# ============================================================
#  Takipci — BYTE association + yasam dongusu
# ============================================================
class Takipci:
    def __init__(self, cfg=None):
        self.cfg = cfg or TakipCfg()
        self.trackler = []

    def guncelle(self, tespitler, dt, H_cmc=None):
        """tespitler: [{cx,cy,w,h,conf,W,H,keypoints?}], dt: sn, H_cmc: 3x3 | None.
        -> en iyi CONFIRMED track ciktisi | None. Tum track'ler self.trackler'da."""
        cfg = self.cfg
        # 1) PREDICT + gyro-CMC warp
        for t in self.trackler:
            t.tahmin(dt, H_cmc)

        yuksek = [d for d in tespitler if float(d.get("conf", 0)) >= cfg.CONF_YUKSEK]
        dusuk = [d for d in tespitler
                 if cfg.CONF_DUSUK <= float(d.get("conf", 0)) < cfg.CONF_YUKSEK]

        aktif = [t for t in self.trackler if t.durum != _REMOVED]
        # 2) BIRINCI TUR: yuksek conf <-> tum aktif track
        es1, kalan_t, kalan_d = self._eslestir(aktif, yuksek)
        for ti, di in es1:
            aktif[ti].guncelle(yuksek[di])
        # 3) IKINCI TUR: eslesmeyen track <-> dusuk conf (yeni track ACAMAZ)
        kalan_track = [aktif[i] for i in kalan_t]
        es2, kalan_t2, _kd2 = self._eslestir(kalan_track, dusuk)
        for ti, di in es2:
            kalan_track[ti].guncelle(dusuk[di])
        # 4) hala eslesmeyen track'ler -> coast/kayip
        eslesmeyen = [kalan_track[i] for i in kalan_t2]
        for t in eslesmeyen:
            t.eslesmedi()
        # 5) eslesmeyen YUKSEK conf tespitleri -> yeni track (dusuk conf ACAMAZ)
        for di in kalan_d:
            self.trackler.append(Track(yuksek[di], cfg))
        # 6) REMOVED temizle
        self.trackler = [t for t in self.trackler if t.durum != _REMOVED]
        return self.en_iyi_cikti()

    def _eslestir(self, trackler, detler):
        """Greedy IoU eslestirme (tek-hedefte optimal). Warp edilmis track bbox'i
        kullanilir. -> (eslesmeler[(ti,di)], eslesmeyen_track_idx, eslesmeyen_det_idx)."""
        if not trackler or not detler:
            return [], list(range(len(trackler))), list(range(len(detler)))
        M = np.zeros((len(trackler), len(detler)))
        for i, t in enumerate(trackler):
            tb = t.bbox()
            for j, d in enumerate(detler):
                M[i, j] = _iou(tb, (d["cx"], d["cy"], d["w"], d["h"]))
        eslesmeler = []
        kullanilan_t, kullanilan_d = set(), set()
        # en yuksek IoU'dan baslayarak greedy
        ciftler = sorted(((M[i, j], i, j) for i in range(len(trackler))
                          for j in range(len(detler))), reverse=True)
        for iou, i, j in ciftler:
            if iou < self.cfg.IOU_ESIK:
                break
            if i in kullanilan_t or j in kullanilan_d:
                continue
            eslesmeler.append((i, j))
            kullanilan_t.add(i)
            kullanilan_d.add(j)
        kalan_t = [i for i in range(len(trackler)) if i not in kullanilan_t]
        kalan_d = [j for j in range(len(detler)) if j not in kullanilan_d]
        return eslesmeler, kalan_t, kalan_d

    def confirmed_trackler(self):
        return [t for t in self.trackler if t.durum in (_CONFIRMED, _LOST)]

    def en_iyi_track(self):
        """FSM'e sunulacak tek track: CONFIRMED'lar arasinda en uzun yasayan
        (esitlikte en yuksek ort conf). LOST da dahildir (coast suruyor)."""
        adaylar = self.confirmed_trackler()
        if not adaylar:
            return None
        return max(adaylar, key=lambda t: (t.hits, t.ort_conf))

    def en_iyi_cikti(self):
        t = self.en_iyi_track()
        return t.cikti() if t is not None else None

    def sifirla(self):
        self.trackler = []

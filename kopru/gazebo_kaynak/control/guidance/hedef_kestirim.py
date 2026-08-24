"""
hedef_kestirim.py — Hedef durum kestirimi: IMM (CV + CA). Saf matematik.

NEDEN VAR (ölçüm, 2026-08-04): mevcut kestirici EMA konum + sonlu fark hızdır.
gps_guidance_20260804_122519.csv'de gerçekle (2 s pencereli) kıyaslandığında:
    gerçek hız medyan 16.00 m/s  ↔  kestirim medyan 19.30 m/s   → 1.21× ŞİŞİK
    gerçek std       0.82        ↔  kestirim std       2.59     → 3.2× GÜRÜLTÜLÜ
    mutlak sapma medyan 3.11 m/s, en kötü 12.82 m/s
Bu hız güdümün ÜÇ teriminin de içine giriyor (ileri besleme, istasyon yönü,
göreli hız terimi) — yani gürültü doğrudan komuta sızıyor.

CTU Prag (arXiv 2405.13542) aynı problemde IMM (CV+CA) kullanıp tek modelli
Kalman'a göre kestirim hatasını %58 düşürmüş. Burada uygulanan da o.

TASARIM — İKİ MODEL, ORTAK DURUM UZAYI:
Klasik IMM'de modeller farklı boyutlu olur (CV 6, CA 9) ve karıştırma adımında
boyut dönüşümü gerekir. Burada her iki model de 9 boyutlu ortak durumu
kullanır: x = [p(3), v(3), a(3)]. Fark yalnız geçiş matrisi ve süreç
gürültüsündedir:
    CV: ivmeyi taşımaz (a sönümlenir), süreç gürültüsü hıza biner   → σ_a
    CA: ivmeyi taşır,   süreç gürültüsü ivmeye biner (jerk)         → σ_j
Böylece karıştırma düz ağırlıklı ortalama olur; boyut dönüşümü ve onun
getirdiği hata kaynağı ortadan kalkar.

Ölçüm yalnız KONUM (telemetriden gelen): H = [I 0 0].

Kullanım:
    kf = IMM()
    kf.guncelle((x, y, z), dt)   → {"p":…, "v":…, "a":…, "w_cv":…, "w_ca":…}
    kf.tahmin(ileri_s)           → ölçüm yokken ileriye taşı (bayat telemetri)
"""

import math

import numpy as np


class Cfg:
    # ── Süreç gürültüsü (F3'te grid-search ile ayarlanacak) ──
    # SIGMA_A, CV modelinin "hedef ivmelenebilir" toleransıdır ve MODEL AYRIM
    # GÜCÜNÜ o belirler. Ölçüldü (2026-08-04): 2.0 ile modeller ayrışmıyordu,
    # ağırlıklar 0.44-0.59 bandında takılı kalıyordu. Sebep fiziksel: gerçek
    # daire deseninin merkezcil ivmesi 5.9 m/s² (R=39 m, v=15.2), ama 20 Hz'de
    # bir adımda ürettiği konum farkı ½·5.9·0.05² = 0.0074 m — 1.5 m'lik ölçüm
    # gürültüsünün 200'de biri, yani görünmez. CV'yi katılaştırmadan ayrım
    # olmuyor. 0.5'te CV manevrayı açıklayamıyor ve IMM CA'ya geçiyor.
    SIGMA_A = 0.5        # m/s²  ; CV modelinin ivme toleransı (KATI olmalı)
    SIGMA_J = 8.0        # m/s³  ; CA modelinin jerk toleransı

    # ── Ölçüm gürültüsü ──
    SIGMA_Z = 1.5        # m ; telemetri konum gürültüsü (GPS + ağ)

    # ── IMM geçiş olasılıkları ──
    # Yapışkan: model bir kez seçilince kolay kolay bırakmasın (gürültüyle
    # model zıplaması komutu titretir). 0.95 kalma, 0.05 geçme.
    P_KAL = 0.95

    # ── Sayısal koruma ──
    DT_MIN = 1e-3
    DT_MAX = 2.0         # bundan uzun boşlukta filtre SIFIRLANIR (bayat veri)


def _F_cv(dt):
    """Sabit hız: p += v·dt. İvme durumu taşınmaz (0'a çekilir)."""
    F = np.eye(9)
    F[0:3, 3:6] = np.eye(3) * dt
    F[6:9, 6:9] = np.zeros((3, 3))       # a → 0
    return F


def _F_ca(dt):
    """Sabit ivme: p += v·dt + ½a·dt², v += a·dt."""
    F = np.eye(9)
    F[0:3, 3:6] = np.eye(3) * dt
    F[0:3, 6:9] = np.eye(3) * (0.5 * dt * dt)
    F[3:6, 6:9] = np.eye(3) * dt
    return F


def _Q_cv(dt, sigma_a):
    """Gürültü hıza binen sürekli-beyaz ivme modeli."""
    Q = np.zeros((9, 9))
    q = sigma_a ** 2
    Q[0:3, 0:3] = np.eye(3) * (q * dt ** 4 / 4.0)
    Q[0:3, 3:6] = np.eye(3) * (q * dt ** 3 / 2.0)
    Q[3:6, 0:3] = np.eye(3) * (q * dt ** 3 / 2.0)
    Q[3:6, 3:6] = np.eye(3) * (q * dt ** 2)
    Q[6:9, 6:9] = np.eye(3) * 1e-6       # a kullanılmıyor; tekil olmasın
    return Q


def _Q_ca(dt, sigma_j):
    """Gürültü ivmeye binen (jerk) model."""
    Q = np.zeros((9, 9))
    q = sigma_j ** 2
    Q[0:3, 0:3] = np.eye(3) * (q * dt ** 6 / 36.0)
    Q[0:3, 3:6] = np.eye(3) * (q * dt ** 5 / 12.0)
    Q[0:3, 6:9] = np.eye(3) * (q * dt ** 4 / 6.0)
    Q[3:6, 0:3] = np.eye(3) * (q * dt ** 5 / 12.0)
    Q[3:6, 3:6] = np.eye(3) * (q * dt ** 4 / 4.0)
    Q[3:6, 6:9] = np.eye(3) * (q * dt ** 3 / 2.0)
    Q[6:9, 0:3] = np.eye(3) * (q * dt ** 4 / 6.0)
    Q[6:9, 3:6] = np.eye(3) * (q * dt ** 3 / 2.0)
    Q[6:9, 6:9] = np.eye(3) * (q * dt ** 2)
    return Q


_H = np.zeros((3, 9))
_H[0:3, 0:3] = np.eye(3)


class _Model:
    """Tek bir Kalman süzgeci (CV ya da CA)."""

    def __init__(self, F_fn, Q_fn, gurultu):
        self._F_fn, self._Q_fn, self._gurultu = F_fn, Q_fn, gurultu
        self.x = np.zeros(9)
        self.P = np.eye(9) * 1e3

    def tahmin(self, dt):
        F = self._F_fn(dt)
        self.x = F @ self.x
        self.P = F @ self.P @ F.T + self._Q_fn(dt, self._gurultu)

    def guncelle(self, z, R):
        """Dönüş: bu ölçümün bu modele göre olabilirliği (likelihood)."""
        y = z - _H @ self.x                       # yenilik
        S = _H @ self.P @ _H.T + R
        try:
            S_inv = np.linalg.inv(S)
        except np.linalg.LinAlgError:
            return 1e-12
        K = self.P @ _H.T @ S_inv
        self.x = self.x + K @ y
        I_KH = np.eye(9) - K @ _H
        # Joseph formu: simetri ve pozitif tanımlılık sayısal olarak korunur
        self.P = I_KH @ self.P @ I_KH.T + K @ R @ K.T
        det = np.linalg.det(S)
        if det <= 0:
            return 1e-12
        ust = float(-0.5 * y.T @ S_inv @ y)
        L = math.exp(max(-700.0, ust)) / math.sqrt(((2 * math.pi) ** 3) * det)
        return max(L, 1e-12)


class IMM:
    """Interacting Multiple Model: CV + CA.

    guncelle(z, dt) her yeni TELEMETRİ ölçümünde çağrılır. Ölçüm gelmeyen
    karelerde tahmin(dt) ile ileri taşınabilir (yarışmada telemetri 1-2 Hz,
    güdüm 20 Hz → aradaki kareler bununla doldurulur).
    """

    def __init__(self, cfg=Cfg):
        self.cfg = cfg
        self._kur()

    def _kur(self):
        self.cv = _Model(_F_cv, _Q_cv, self.cfg.SIGMA_A)
        self.ca = _Model(_F_ca, _Q_ca, self.cfg.SIGMA_J)
        self.w = np.array([0.5, 0.5])            # model olasılıkları [cv, ca]
        p, q = self.cfg.P_KAL, 1.0 - self.cfg.P_KAL
        self.Pi = np.array([[p, q], [q, p]])     # geçiş matrisi
        self.baslatildi = False
        self.R = np.eye(3) * (self.cfg.SIGMA_Z ** 2)

    def sifirla(self):
        self._kur()

    # ── karıştırma (IMM'in "interacting" kısmı) ──
    def _karistir(self):
        c = self.Pi.T @ self.w                   # normalizasyon
        c = np.maximum(c, 1e-12)
        mu = (self.Pi * self.w[:, None]) / c[None, :]   # mu[i,j]: i→j ağırlığı
        modeller = [self.cv, self.ca]
        x_yeni, P_yeni = [], []
        for j in range(2):
            xj = sum(mu[i, j] * modeller[i].x for i in range(2))
            Pj = np.zeros((9, 9))
            for i in range(2):
                d = (modeller[i].x - xj).reshape(-1, 1)
                Pj += mu[i, j] * (modeller[i].P + d @ d.T)
            x_yeni.append(xj)
            P_yeni.append(Pj)
        for j, m in enumerate(modeller):
            m.x, m.P = x_yeni[j], P_yeni[j]
        return c

    # ── API: TAHMİN ve ÖLÇÜM AYRI ──
    # Bunlar bilerek ayrıldı. Tek bir guncelle(z, dt) çağrısı hem ilerletip hem
    # ölçüm uygularsa, 20 Hz döngüde 1-2 Hz telemetriyle çalışan çağıran taraf
    # zamanı ÇİFT SAYAR: ara kareleri tahmin(dt) ile ilerletir, sonra ölçüm
    # geldiğinde guncelle(z, Δt_ölçüm) aynı süreyi bir daha ilerletir.
    # Ölçüldü (2026-08-04): bu hata 1 Hz telemetride hız hatasını 0.9 m/s'den
    # 7.9 m/s'ye çıkarıyordu — EMA'dan 9 kat KÖTÜ.
    # Doğru kullanım (gerçek güdüm döngüsü):
    #     her kare:            kf.tahmin(dt_kare)
    #     telemetri geldiyse:  kf.olcum(z)

    def tahmin(self, dt):
        """Zamanı ilerlet (ölçüm yok). Her güdüm karesinde çağrılır."""
        if not self.baslatildi or dt is None or dt <= 0:
            return self.durum()
        if dt > self.cfg.DT_MAX:
            self.baslatildi = False          # bayat: hız/ivme artık geçersiz
            return self.durum()
        self.cv.tahmin(max(dt, self.cfg.DT_MIN))
        self.ca.tahmin(max(dt, self.cfg.DT_MIN))
        return self.durum()

    def olcum(self, z):
        """Yeni konum ölçümü uygula (zaman İLERLETMEZ)."""
        z = np.asarray(z, dtype=float)
        if not self.baslatildi:
            for m in (self.cv, self.ca):
                m.x = np.zeros(9)
                m.x[0:3] = z
                m.P = np.eye(9) * 1e2
                m.P[0:3, 0:3] = self.R * 4.0
            self.w = np.array([0.5, 0.5])
            self.baslatildi = True
            return self.durum()

        c = self._karistir()
        L = np.array([self.cv.guncelle(z, self.R),
                      self.ca.guncelle(z, self.R)])
        w_yeni = L * c
        toplam = w_yeni.sum()
        self.w = (w_yeni / toplam) if toplam > 1e-300 else np.array([0.5, 0.5])
        # tam 0/1'e kilitlenmesin — kilitlenirse diğer model bir daha uyanamaz
        self.w = np.clip(self.w, 1e-4, 1.0 - 1e-4)
        self.w /= self.w.sum()
        return self.durum()

    def guncelle(self, z, dt):
        """Kolaylık: tahmin(dt) + olcum(z). Ara karelerde tahmin() ÇAĞIRMAYAN
        basit kullanım için (telemetri hızı = güdüm hızı olduğunda)."""
        self.tahmin(dt)
        return self.olcum(z)

    def durum(self):
        """Birleştirilmiş kestirim (model olasılıklarıyla ağırlıklı)."""
        if not self.baslatildi:
            return {"p": (0.0, 0.0, 0.0), "v": (0.0, 0.0, 0.0),
                    "a": (0.0, 0.0, 0.0), "w_cv": 0.5, "w_ca": 0.5,
                    "hazir": False}
        x = self.w[0] * self.cv.x + self.w[1] * self.ca.x
        return {"p": tuple(x[0:3]), "v": tuple(x[3:6]), "a": tuple(x[6:9]),
                "w_cv": float(self.w[0]), "w_ca": float(self.w[1]),
                "hazir": True}


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  GÖRSEL FAZ KESTİRİMİ — YALNIZ KAMERA (2026-08-17)                       ║
# ╚══════════════════════════════════════════════════════════════════════════╝
#
# NEDEN AYRI: yukarıdaki IMM, GPS fazının 3B konum ölçümü içindir. Görsel fazda
# hedefin CANLI GPS'i YASAK (yarışma kuralı; tespit_akisi.py sözleşmesi
# {conf,cx,cy,w,h} ile kilitli). Aşağıdaki blok yalnız şunları girdi alır:
#     KAMERA  : cx, cy, w, h, conf
#     KENDİMİZ: roll, pitch, yaw, kendi NED konumumuz  (kural serbest)
# Hedefin truth'u/menzili/GPS'i hiçbir imzada YOKTUR — KamOlcum bunu kilitler.
#
# ZİNCİR (üç adım, hepsi kendi sensörümüzle):
#     1. piksel + kendi duruşumuz -> SEVİYE çerçevesinde LOS birim vektörü
#     2. kutu boyutu              -> menzil vekili (yanlılık düzeltmeli)
#     3. p_hedef = p_kendi + R*u  -> ATALET çerçevesinde SANKİ-ÖLÇÜM
# Bundan sonrası klasik hedef izleme: filtre -> ileri tahmin -> kesme noktası.
#
# ⚠ SANKİ-ÖLÇÜMÜN ZAYIF EKSENİ MENZİLDİR. Kerteriz (bearing) hatası ~1-3 px
# (0.3-1.0°) iken menzil vekilinin hatası metrelerce. Bu yüzden ölçüm gürültüsü
# R matrisi İZOTROPİK DEĞİL: LOS boyunca büyük, dike küçük (aşağıda _R_los).
# İzotropik R kullanmak kerteriz bilgisini menzil gürültüsüyle boğar.

import collections
from dataclasses import dataclass


class KestirimCfg:
    # ── kamera (vision/geometry.py ile birebir) ──
    IMG_W, IMG_H = 640, 480
    HFOV_RAD = 2.18166                      # 125 deg (SDF ile tutarli)
    # ⚠ 166.6 diye YUVARLAMA: bbox_ibvs geo.FX'i tam hesapliyor ve iki zincir
    # ayrilirsa kestirim ile yasa farkli kameralar varsayar (olculen sapma
    # 8.9e-05 rad). Ayni ifade burada da kullanilir.
    FX = FY = (IMG_W / 2.0) / math.tan(HFOV_RAD / 2.0)   # ~166.58
    CX, CY = 320.0, 240.0
    KAMERA_TILT_DEG = 25.0          # kamera gövdeye YUKARI vidalı

    # ── menzil vekili:  R = MENZIL_A / (boyut - MENZIL_B) ──
    # boyut = sqrt(w*h). ÖLÇÜLDÜ (2026-08-17, sim/kestirim.py menzil komutu,
    # 134104 tespitli kare truth ile eşlenerek):
    #     R = 202.6/boyut      (kodda)  |hata| medyan 4.91 m, yanlılık +2.58 m
    #     R = 232.2/(boyut+4.11)        |hata| medyan 3.35 m, yanlılık +0.06 m
    #     R = 68.6/(w^0.39·h^0.20)      |hata| medyan 3.25 m, yanlılık +0.16 m
    # İki parametreli biçim üç parametreliyle aynı işi görüyor; o seçildi.
    #
    # ⚠⚠ TOPLAM YANLILIK SIFIRA GELSE DE DİLİM YANLILIĞI BÜYÜK:
    #      0-5 m   +5.06 m   (yakında menzili AŞIRI büyük sanıyor)
    #      8-12 m  +2.15 m
    #     16-22 m  -1.25 m
    #     30-60 m -14.23 m
    # Yani menzil vekili İŞE YARAR DEĞİL, yalnız kaba bir ölçektir. Kestirim
    # zincirinin TAŞIYICI bilgisi KERTERİZDİR (1-3 px ~ 0.3-1.0°). _R_los bu
    # yüzden anizotropiktir; izotropik R kullanmak kerterizi menzil gürültüsüne
    # boğar ve tüm kestirimi çöpe çevirir.
    MENZIL_A = 232.2
    MENZIL_B = -4.11
    MENZIL_MIN, MENZIL_MAX = 1.0, 80.0

    # ── sanki-ölçüm gürültüsü (anizotropik) ──
    # SIGMA_MENZIL_ORAN ölçüldü: bağıl hata p16/p84 -0.355/+0.419 → ~0.39.
    SIGMA_KERTERIZ_PX = 3.0         # px ; kutu merkezi titremesi
    SIGMA_MENZIL_ORAN = 0.38        # menzilin oranı olarak 1 sigma (ÖLÇÜLDÜ)
    SIGMA_MENZIL_TABAN = 1.5        # m

    # ── süreç gürültüsü ──
    Q_IVME = 6.0                    # m/s^2  CV modelinin manevra toleransı
    Q_OMEGA = 0.6                   # rad/s^2 CT dönüş hızı sürüklenmesi

    # ── genel ──
    DT_MAX_GORSEL = 0.6             # s ; bundan uzun boşlukta durum bayat
    PENCERE_S = 2.0                 # s ; polinom/oval uydurma penceresi
    UFUK_MAX = 3.0                  # s ; bunun ötesine tahmin verilmez


# ───────────────────────────────────────────── SÖZLEŞME: yalnız kamera + biz
@dataclass(frozen=True)
class KamOlcum:
    """Tek karenin kestirimciye giren TÜM bilgisi.

    ⛔ Bu sınıfa hedefin GPS'i / truth'u / gerçek menzili EKLENEMEZ. Alan listesi
    yarışma kuralının kod karşılığıdır; tests/test_hedef_kestirim.py bunu
    test_kural_sozlesme_alanlari ile kilitler.
    """
    t: float                        # s   (monotonik)
    cx: float                       # px  kutu merkezi
    cy: float                       # px
    w: float                        # px  kutu genişliği
    h: float                        # px  kutu yüksekliği
    conf: float                     # 0-1 dedektör güveni
    roll: float                     # rad KENDİ duruşumuz
    pitch: float                    # rad
    yaw: float                      # rad
    px: float                       # m   KENDİ NED konumumuz
    py: float                       # m
    pz: float                       # m


# ──────────────────────────────────────────────────── 1. piksel -> kerteriz
def piksel_los_seviye(cx, cy, roll, pitch, cfg=KestirimCfg):
    """Piksel + kendi duruşumuz -> SEVİYE çerçevesinde (azimut, yükseliş) rad.

    bbox_ibvs.los_seviye ile BİREBİR aynı zincir (kamera->gövde->seviye).
    Burada kopyalanmasının sebebi bağımlılık yönü: hedef_kestirim saf matematik
    kalmalı, bbox_ibvs'i import ederse döngüsel bağımlılık doğar.
    Azimut burna göre sağ+, yükseliş yukarı+.
    """
    x = (cx - cfg.CX) / cfg.FX          # kamera sağ
    y = (cy - cfg.CY) / cfg.FY          # kamera aşağı
    t = math.radians(cfg.KAMERA_TILT_DEG)
    ct, st = math.cos(t), math.sin(t)
    bx = ct + st * y                    # gövde ileri
    by = x                              # gövde sağ
    bz = ct * y - st                    # gövde aşağı
    cr, sr = math.cos(roll), math.sin(roll)
    y1 = by * cr - bz * sr
    z1 = by * sr + bz * cr
    cp, sp = math.cos(pitch), math.sin(pitch)
    x2 = bx * cp + z1 * sp
    z2 = -bx * sp + z1 * cp
    return math.atan2(y1, x2), math.atan2(-z2, math.hypot(x2, y1))


def menzil_vekilinden(w, h, cfg=KestirimCfg):
    """Kutu boyutundan menzil (m). R = A/(boyut - B), boyut = sqrt(w*h).

    Tek sabitli R = K/boyut biçimi menzille değişen bir yanlılık taşır; B terimi
    o eğimi soğurur. Aralık dışına taşma kırpılır (bölme patlamasın)."""
    boyut = math.sqrt(max(w, 0.0) * max(h, 0.0))
    if boyut <= 0.5:
        return cfg.MENZIL_MAX          # kutu yok/anlamsiz -> en uzak varsay
    payda = boyut - cfg.MENZIL_B
    if payda <= 0.25:
        return cfg.MENZIL_MAX
    return min(max(cfg.MENZIL_A / payda, cfg.MENZIL_MIN), cfg.MENZIL_MAX)


def sanki_olcum(kam, cfg=KestirimCfg):
    """KamOlcum -> (p_hedef_atalet, u_los, R). Truth YOK; yalnız kamera+kendimiz.

    Dönüş NED: x kuzey, y doğu, z aşağı.
    """
    az_b, el = piksel_los_seviye(kam.cx, kam.cy, kam.roll, kam.pitch, cfg)
    az = kam.yaw + az_b                             # seviye çerçevesi mutlak
    R = menzil_vekilinden(kam.w, kam.h, cfg)
    ce = math.cos(el)
    u = np.array([ce * math.cos(az), ce * math.sin(az), -math.sin(el)])
    p = np.array([kam.px, kam.py, kam.pz]) + R * u
    return p, u, R


def _R_los(u, R, cfg=KestirimCfg):
    """Anizotropik ölçüm kovaryansı: LOS boyunca menzil hatası, dikinde kerteriz.

    sigma_dik = R * (sigma_px/FX) — piksel hatası menzille ölçeklenip metreye
    döner. sigma_los = max(taban, oran*R).
    """
    s_dik = max(R * cfg.SIGMA_KERTERIZ_PX / cfg.FX, 0.05)
    s_los = max(cfg.SIGMA_MENZIL_TABAN, cfg.SIGMA_MENZIL_ORAN * R)
    u = np.asarray(u, dtype=float)
    n = np.linalg.norm(u)
    u = u / n if n > 1e-9 else np.array([1.0, 0.0, 0.0])
    P = np.eye(3) - np.outer(u, u)                  # LOS'a dik izdüşüm
    return (s_los ** 2) * np.outer(u, u) + (s_dik ** 2) * P


# ══════════════════════════════════════════════════════════════ MODELLER
# Ortak arayüz:  olcum(t, p, Rm) -> None    ;   tahmin(ufuk) -> (p, v) | None
# Hepsi yan etkisiz sınıf; kurucu argümanı yok (tezgâh fabrika gibi çağırır).

class _Taban:
    ad = "taban"

    def __init__(self, cfg=KestirimCfg):
        self.cfg = cfg
        self.t = None
        self.hazir = False

    def sifirla(self):
        self.__init__(self.cfg)


class ModelSabitHiz(_Taban):
    """CV — sabit hız Kalman. x = [p(3), v(3)]."""
    ad = "sabit_hiz"

    def __init__(self, cfg=KestirimCfg):
        super().__init__(cfg)
        self.x = np.zeros(6)
        self.P = np.eye(6) * 1e3
        self._L = 1.0

    def _F(self, dt):
        F = np.eye(6)
        F[0:3, 3:6] = np.eye(3) * dt
        return F

    def _Q(self, dt):
        q = self.cfg.Q_IVME ** 2
        Q = np.zeros((6, 6))
        Q[0:3, 0:3] = np.eye(3) * (q * dt ** 4 / 4)
        Q[0:3, 3:6] = np.eye(3) * (q * dt ** 3 / 2)
        Q[3:6, 0:3] = np.eye(3) * (q * dt ** 3 / 2)
        Q[3:6, 3:6] = np.eye(3) * (q * dt ** 2)
        return Q

    def olcum(self, t, p, Rm):
        p = np.asarray(p, dtype=float)
        if not self.hazir:
            self.x = np.zeros(6)
            self.x[0:3] = p
            self.P = np.eye(6) * 100.0
            self.P[0:3, 0:3] = Rm
            self.t, self.hazir = t, True
            return
        dt = t - self.t
        if dt <= 0 or dt > self.cfg.DT_MAX_GORSEL:
            self.hazir = False
            return self.olcum(t, p, Rm)
        F = self._F(dt)
        self.x = F @ self.x
        self.P = F @ self.P @ F.T + self._Q(dt)
        H = np.zeros((3, 6))
        H[0:3, 0:3] = np.eye(3)
        y = p - H @ self.x
        S = H @ self.P @ H.T + Rm
        try:
            K = self.P @ H.T @ np.linalg.inv(S)
        except np.linalg.LinAlgError:
            return
        self.x = self.x + K @ y
        I_KH = np.eye(6) - K @ H
        self.P = I_KH @ self.P @ I_KH.T + K @ Rm @ K.T
        self.t = t
        self._L = _olabilirlik(y, S)

    def tahmin(self, ufuk):
        if not self.hazir:
            return None
        x = self._F(ufuk) @ self.x
        return x[0:3], x[3:6]


def _olabilirlik(y, S):
    try:
        det = np.linalg.det(S)
        if det <= 0:
            return 1e-12
        u = float(-0.5 * y @ np.linalg.solve(S, y))
        return max(math.exp(max(-700.0, u))
                   / math.sqrt(((2 * math.pi) ** 3) * det), 1e-12)
    except np.linalg.LinAlgError:
        return 1e-12


def _ct_ilerlet(x, dt):
    """Eşgüdümlü dönüş (yatay düzlemde) ile durum ilerletme.
    x = [px,py,pz, vx,vy,vz, omega].

    ⚠ om=0 CIVARINDA SERI ACILIMI KULLANILIR, DALLANMA DEGIL.
    Sert bir "if |om| < eps: dogrusal" dali koyarsak, sayisal Jakobiyen om'u
    ±1e-6 oynatirken AYNI dalda kalir ve d(durum)/d(om) TAM SIFIR cikar; boylece
    om hicbir zaman gozlemlenebilir olmaz ve CT modeli CV'ye dejenere olur.
    OLCULDU: dallanmali surumde CT ile CV dairede BIREBIR ayni hatayi
    veriyordu (18.82 m) — yani CT'nin varlik sebebi yok oluyordu.
    Asagidaki A/B katsayilari om'da analitik ve puruzsuzdur.
        A = sin(om·dt)/om ,  B = (1-cos(om·dt))/om
    """
    px, py, pz, vx, vy, vz, om = x
    th = om * dt
    if abs(th) < 1e-3:                      # seri (puruzsuz, om'da turevli)
        A = dt * (1.0 - th * th / 6.0 + th ** 4 / 120.0)
        B = dt * (th / 2.0 - th ** 3 / 24.0)
    else:
        A = math.sin(th) / om
        B = (1.0 - math.cos(th)) / om
    c, s = math.cos(th), math.sin(th)
    return np.array([
        px + vx * A - vy * B,
        py + vx * B + vy * A,
        pz + vz * dt,
        vx * c - vy * s,
        vx * s + vy * c,
        vz, om])


def _jakobi(f, x, dt, eps=1e-5):
    """Sayısal Jakobiyen (merkezi fark). 7 boyutta ucuz ve analitikten güvenli.

    Adim, konum/hiz (metre olcegi) ile omega (rad/s olcegi) icin ayni olamaz;
    omega'da cok kucuk adim yuvarlama gurultusune bogulur."""
    n = len(x)
    J = np.zeros((n, n))
    for i in range(n):
        h = eps * (100.0 if i == 6 else 1.0)
        d = np.zeros(n)
        d[i] = h
        J[:, i] = (f(x + d, dt) - f(x - d, dt)) / (2 * h)
    return J


class ModelSabitDonus(_Taban):
    """CT — sabit dönüş hızı EKF. x = [p(3), v(3), omega].

    Hedef sabit ovalde uçtuğu için dönüş hızı parça parça SABİT (düzde 0,
    virajda V/R). Bu model tam da o yapıyı taşır; CV virajı kaçırır."""
    ad = "sabit_donus"

    def __init__(self, cfg=KestirimCfg):
        super().__init__(cfg)
        self.x = np.zeros(7)
        self.P = np.eye(7) * 1e3
        self._L = 1.0

    def _Q(self, dt):
        q = self.cfg.Q_IVME ** 2
        Q = np.zeros((7, 7))
        Q[0:3, 0:3] = np.eye(3) * (q * dt ** 4 / 4)
        Q[0:3, 3:6] = np.eye(3) * (q * dt ** 3 / 2)
        Q[3:6, 0:3] = np.eye(3) * (q * dt ** 3 / 2)
        Q[3:6, 3:6] = np.eye(3) * (q * dt ** 2)
        Q[6, 6] = (self.cfg.Q_OMEGA ** 2) * dt
        return Q

    def olcum(self, t, p, Rm):
        p = np.asarray(p, dtype=float)
        if not self.hazir:
            self.x = np.zeros(7)
            self.x[0:3] = p
            self.P = np.eye(7) * 100.0
            self.P[0:3, 0:3] = Rm
            self.P[6, 6] = 1.0
            self.t, self.hazir = t, True
            return
        dt = t - self.t
        if dt <= 0 or dt > self.cfg.DT_MAX_GORSEL:
            self.hazir = False
            return self.olcum(t, p, Rm)
        F = _jakobi(_ct_ilerlet, self.x, dt)
        self.x = _ct_ilerlet(self.x, dt)
        self.P = F @ self.P @ F.T + self._Q(dt)
        H = np.zeros((3, 7))
        H[0:3, 0:3] = np.eye(3)
        y = p - H @ self.x
        S = H @ self.P @ H.T + Rm
        try:
            K = self.P @ H.T @ np.linalg.inv(S)
        except np.linalg.LinAlgError:
            return
        self.x = self.x + K @ y
        I_KH = np.eye(7) - K @ H
        self.P = I_KH @ self.P @ I_KH.T + K @ Rm @ K.T
        # omega doygunluğu: fiziksel tavan V/R_min (oval yarıçapı 48 m, V 18)
        self.x[6] = max(-1.2, min(1.2, self.x[6]))
        self.t = t
        self._L = _olabilirlik(y, S)

    def tahmin(self, ufuk):
        if not self.hazir:
            return None
        x = _ct_ilerlet(self.x, ufuk)
        return x[0:3], x[3:6]


class ModelIMM(_Taban):
    """CV + CT karışımı. Düz segmentte CV, virajda CT ağır basar.

    Karıştırma ortak (p,v) alt-uzayında yapılır; omega yalnız CT'de olduğu için
    CV'ye karışırken düşer, CT'de korunur. Farklı boyutlu IMM'in standart ele
    alışı budur."""
    ad = "imm"

    def __init__(self, cfg=KestirimCfg):
        super().__init__(cfg)
        self.cv = ModelSabitHiz(cfg)
        self.ct = ModelSabitDonus(cfg)
        self.w = np.array([0.5, 0.5])
        p = 0.92
        self.Pi = np.array([[p, 1 - p], [1 - p, p]])

    def sifirla(self):
        self.__init__(self.cfg)

    def olcum(self, t, p, Rm):
        c = self.Pi.T @ self.w
        c = np.maximum(c, 1e-12)
        mu = (self.Pi * self.w[:, None]) / c[None, :]
        if self.cv.hazir and self.ct.hazir:
            xcv, xct = self.cv.x.copy(), self.ct.x.copy()
            for j, mdl in enumerate((self.cv, self.ct)):
                mdl.x[0:6] = mu[0, j] * xcv[0:6] + mu[1, j] * xct[0:6]
        self.cv.olcum(t, p, Rm)
        self.ct.olcum(t, p, Rm)
        L = np.array([self.cv._L, self.ct._L])
        wn = L * c
        s = wn.sum()
        self.w = (wn / s) if s > 1e-300 else np.array([0.5, 0.5])
        self.w = np.clip(self.w, 1e-3, 1 - 1e-3)
        self.w /= self.w.sum()
        self.hazir = self.cv.hazir and self.ct.hazir
        self.t = t

    def tahmin(self, ufuk):
        a, b = self.cv.tahmin(ufuk), self.ct.tahmin(ufuk)
        if a is None or b is None:
            return a if a is not None else b
        return (self.w[0] * a[0] + self.w[1] * b[0],
                self.w[0] * a[1] + self.w[1] * b[1])


class ModelPolinom(_Taban):
    """Kısa ufuklu polinom: son PENCERE_S saniyeye eksen başına 2. derece uydur.

    Filtre yok — ham sanki-ölçümlere en küçük kareler. Gürültüye açık ama
    gecikmesiz; kısa ufukta filtreye rakip olup olmadığı ÖLÇÜLECEK."""
    ad = "polinom"
    DERECE = 2

    def __init__(self, cfg=KestirimCfg):
        super().__init__(cfg)
        self.buf = collections.deque(maxlen=200)
        self._fit = None

    def sifirla(self):
        self.__init__(self.cfg)

    def olcum(self, t, p, Rm):
        if self.buf and (t - self.buf[-1][0]) > self.cfg.DT_MAX_GORSEL:
            self.buf.clear()
        self.buf.append((t, np.asarray(p, dtype=float)))
        while self.buf and (t - self.buf[0][0]) > self.cfg.PENCERE_S:
            self.buf.popleft()
        self.t = t
        self.hazir = len(self.buf) >= 5

    def _katsayi(self):
        """Eksen basina polinom katsayilari. Ayni karede tekrar cagrilirsa
        yeniden uydurulmaz (ufuk taramasi ucuz kalsin)."""
        if self._fit is not None and self._fit[0] == self.t:
            return self._fit[1]
        ts = np.array([b[0] for b in self.buf]) - self.t
        P = np.stack([b[1] for b in self.buf])
        der = min(self.DERECE, len(self.buf) - 2)
        if der < 1:
            return None
        cs = [np.polyfit(ts, P[:, k], der) for k in range(3)]
        self._fit = (self.t, cs)
        return cs

    def tahmin(self, ufuk):
        if not self.hazir:
            return None
        cs = self._katsayi()
        if cs is None:
            return None
        return (np.array([float(np.polyval(c, ufuk)) for c in cs]),
                np.array([float(np.polyval(np.polyder(c), ufuk)) for c in cs]))


class ModelOval(_Taban):
    """Yörünge uydurma: son PENCERE_S'lik yatay ize ÇEMBER uydur, üstünde taşı.

    Hedef 220x96 m sabit ovalde uçuyor; virajda yarıçap 48 m, düzde sonsuz. Tek
    bir çember (yarıçap serbest) her iki hâli de temsil eder.
    ⚠ ZAYIFLIK: görsel fazda görülen yay çok kısa (ölçülen medyan iz ~1.0 s
    ~= 18 m ~= 21 derece yay). Kısa yayda çember uydurma menzil gürültüsüne
    aşırı duyarlıdır. Bu modelin AMACI o zayıflığı SAYIYLA göstermektir."""
    ad = "oval"

    def __init__(self, cfg=KestirimCfg):
        super().__init__(cfg)
        self.buf = collections.deque(maxlen=200)
        self._fit = None

    def sifirla(self):
        self.__init__(self.cfg)

    def olcum(self, t, p, Rm):
        if self.buf and (t - self.buf[-1][0]) > self.cfg.DT_MAX_GORSEL:
            self.buf.clear()
        self.buf.append((t, np.asarray(p, dtype=float)))
        while self.buf and (t - self.buf[0][0]) > self.cfg.PENCERE_S:
            self.buf.popleft()
        self.t = t
        self.hazir = len(self.buf) >= 6

    def tahmin(self, ufuk):
        if not self.hazir:
            return None
        ts = np.array([b[0] for b in self.buf]) - self.t
        P = np.stack([b[1] for b in self.buf])
        x, y = P[:, 0], P[:, 1]
        n = min(len(ts), 8)
        vz = float(np.polyfit(ts[-n:], P[-n:, 2], 1)[0])

        def _duz():
            vx = float(np.polyfit(ts[-n:], x[-n:], 1)[0])
            vy = float(np.polyfit(ts[-n:], y[-n:], 1)[0])
            return (np.array([x[-1] + vx * ufuk, y[-1] + vy * ufuk,
                              P[-1, 2] + vz * ufuk]), np.array([vx, vy, vz]))

        # cebirsel çember uydurma:  x^2+y^2 = a*x + b*y + c
        A = np.column_stack([x, y, np.ones(len(x))])
        rhs = x ** 2 + y ** 2
        try:
            sol, *_ = np.linalg.lstsq(A, rhs, rcond=None)
        except np.linalg.LinAlgError:
            return _duz()
        cx, cy = sol[0] / 2, sol[1] / 2
        r2 = sol[2] + cx ** 2 + cy ** 2
        if not np.isfinite(r2) or r2 <= 1.0:
            return _duz()
        r = math.sqrt(r2)
        if r > 400.0:                       # neredeyse düz -> çemberi kullanma
            return _duz()
        ds = np.hypot(np.diff(x), np.diff(y))
        dt = np.diff(ts)
        V = float(np.median(ds / np.maximum(dt, 1e-6))) if len(ds) else 0.0
        th = math.atan2(y[-1] - cy, x[-1] - cx)
        th0 = math.atan2(y[0] - cy, x[0] - cx)
        sap = (th - th0 + math.pi) % (2 * math.pi) - math.pi
        yon = 1.0 if sap > 0 else -1.0
        om = yon * V / r
        th2 = th + om * ufuk
        return (np.array([cx + r * math.cos(th2), cy + r * math.sin(th2),
                          P[-1, 2] + vz * ufuk]),
                np.array([-om * r * math.sin(th2), om * r * math.cos(th2), vz]))


# ══════════════════════════════════════════════════════════ SARMALAYICI
class GorselKestirim:
    """Kamera ölçümlerini alır, seçilen modeli besler, ileri tahmin verir.

    Yan etkisiz: dosya/ağ/env okumaz. Girdi YALNIZ KamOlcum.
    """

    def __init__(self, model=None, cfg=KestirimCfg):
        self.cfg = cfg
        self.model = model if model is not None else ModelIMM(cfg)
        self.son = None
        self.n = 0

    def sifirla(self):
        self.model.sifirla()
        self.son = None
        self.n = 0

    def olcum(self, kam):
        """Yeni kamera karesi. kam KamOlcum olmalı (sözleşme)."""
        if not isinstance(kam, KamOlcum):
            raise TypeError("GorselKestirim yalnız KamOlcum kabul eder "
                            "(yarışma kuralı: görsel fazda hedef GPS'i yasak)")
        p, u, R = sanki_olcum(kam, self.cfg)
        self.model.olcum(kam.t, p, _R_los(u, R, self.cfg))
        self.son = (kam, p, u, R)
        self.n += 1
        return self.durum()

    def tahmin(self, ufuk):
        """Hedefin ufuk saniye sonraki ATALET konumu/hızı. None = hazır değil."""
        if self.son is None:
            return None
        ufuk = max(0.0, min(float(ufuk), self.cfg.UFUK_MAX))
        r = self.model.tahmin(ufuk)
        if r is None:
            return None
        p, v = r
        return {"p": tuple(float(z) for z in p),
                "v": tuple(float(z) for z in v), "ufuk": ufuk}

    def durum(self):
        if self.son is None:
            return {"hazir": False}
        kam, p, u, R = self.son
        d = self.tahmin(0.0)
        return {"hazir": d is not None, "n": self.n, "menzil_vekil": R,
                "p_olcum": tuple(float(z) for z in p),
                "p_kestirim": d["p"] if d else None,
                "v_kestirim": d["v"] if d else None}


# ══════════════════════════════════════════════════════════ KESME NOKTASI
def kesme_cozumu(p_biz, V_biz, p_hedef, v_hedef, tol=1e-4, tmax=6.0):
    """Sabit hızlı kesme: V_biz hızımızla hedefin düz uzantısını kesmek için
    gereken (t_go, kesme noktası, gereken yön). Çözüm yoksa None.

    |p_h + v_h*t - p_b| = V_b*t  ->  ikinci derece denklem.
    """
    p_b = np.asarray(p_biz, dtype=float)
    p_h = np.asarray(p_hedef, dtype=float)
    v_h = np.asarray(v_hedef, dtype=float)
    d = p_h - p_b
    a = float(v_h @ v_h) - V_biz ** 2
    b = 2.0 * float(d @ v_h)
    c = float(d @ d)
    if abs(a) < 1e-9:
        if abs(b) < 1e-12:
            return None
        t = -c / b
        if t <= tol:
            return None
    else:
        disk = b * b - 4 * a * c
        if disk < 0:
            return None
        k = math.sqrt(disk)
        kok = [x for x in ((-b - k) / (2 * a), (-b + k) / (2 * a)) if x > tol]
        if not kok:
            return None
        t = min(kok)
    if t > tmax:
        return None
    pk = p_h + v_h * t
    yon = pk - p_b
    n = np.linalg.norm(yon)
    if n < 1e-9:
        return None
    return {"t_go": float(t), "p_kesme": tuple(float(z) for z in pk),
            "yon": tuple(float(z) for z in (yon / n))}


def lead_acisi(mu, aspect_rad):
    """sin(sigma) = mu*sin(aspect). Çözüm yoksa None (kesme imkânsız).

    mu = V_hedef / V_biz ; aspect = hedefin kuyruk açısı (180 = tam kuyruk).
    """
    s = mu * math.sin(aspect_rad)
    if abs(s) > 1.0:
        return None
    return math.asin(s)


def donus_tavani(V, a_max=12.0, yaw_tavan_dps=120.0):
    """Hız zarfı: verilen V'de saniyede kaç derece dönebiliriz (derece/s).

    omega = a/V — quadrotor'da ivme sabit clamp'li olduğu için YAVAŞLAMAK
    dönüşü SERTLEŞTİRİR. Yaw kanal tavanı ayrıca üstten kısar."""
    return min(math.degrees(a_max / max(V, 1e-3)), yaw_tavan_dps)

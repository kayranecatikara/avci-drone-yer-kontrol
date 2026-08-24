# -*- coding: utf-8 -*-
"""OMUR SUPURMESI (simulator) - fazi yasatan ucuz kaldiraclar.

⚠ SADECE OKUR. sim/tesis.py, sim/deney.py ve kopru/ altindaki yasa
DEGISTIRILMEZ; hepsi aynen import edilir. Ekstra kaldiraclar (KAYIP_M,
conf esigi, koprüleme) tesiste YOK, o yuzden dongunun kendisi burada
yeniden yazildi — ama deney.kosu() ile BIT-AYNI olacak sekilde
(bkz. `sinama_gerileme()`, varsayilan kaldiraclarla iki dongu ayni sayiyi
verir; tutmazsa betik durur).

OLCULEN SAHA GERCEKLERI (DURUM_2026-08-16.md §11/§17, 569 faz):
    istasyon 9 m, clamp 24/12/3 -> iska p50 12.73 m, en iyi 6.88 m
    faz omru p50 1.28 s   (p90 1.84) | gorsel temas p50 1.00 s
    devir menzili p50 17.7 m | devir kutusu 9.0 px | aspect 18.5°
    faz ici sureklilik %78.5 | faz boyu kutulu kare orani 0.41
    olum: %64.7 kadraj ICINDE tespit oluyor (|az| p50 52°, sinir 61°),
          %32 yandan cikis, %0.9 dikey | olum kutusu 11.1 px, conf 0.58
    dedektor 21.3 Hz, det_ms p50 23 / p95 46 ms
"""
import math
import os
import random
import statistics as st
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "kopru", "gazebo_kaynak"))
sys.path.insert(0, os.path.join(KOK, "sim"))

import tesis as T                                                 # noqa: E402
from tesis import (Avci, Hedef, Olcum, kadraj, F_YASA, CX, CY,    # noqa: E402
                   TX_MAX, TY_MAX, HataAyari, Algi, tespit_olasilik)
from control.guidance import bbox_ibvs as IB                      # noqa: E402
import deney as D                                                 # noqa: E402


# ══════════════════════════════════════════════════════════════════════════
#  SAHA KURULUMU (kalici ayar, DURUM_2026-08-16.md §17)
# ══════════════════════════════════════════════════════════════════════════
class SahaCfg(IB.Cfg):
    """Oyunda KALICI olan ayar. Yasa kodu degismedi, yalniz alanlar."""
    YAW_HIZALA_S = 0.12          # (simulatorde etkisiz: lam'i deney dongusu kurar)
    KAPANMA = False              # olculdu: kutudan kapanma hizi SNR 0.4 -> zararli
    # V_TOPLAM_MAX 24 / MAX_ACCEL 12 / VZ_MAX 3 zaten varsayilan
    # PN_N 1.6, BURUN_LOS acik, MENZIL_PX_M 202.6 zaten varsayilan


def cfg_ile(**kw):
    """SahaCfg'nin alan-degistirilmis alt sinifi (yasa kodu degismez)."""
    return type("Cfg_", (SahaCfg,), kw)


# ══════════════════════════════════════════════════════════════════════════
#  DEDEKTOR MODELI — conf esigi ve kadraj-kenari cezasi
# ══════════════════════════════════════════════════════════════════════════
# ⚠ NEDEN AYRI: tesis.tespit_olasilik() YALNIZ kutu boyutuna bakiyor. Sahanin
# BASKIN olum kipi ise (%64.7) hedef kadrajin ICINDEYKEN tespitin olmesi ve
# olum aninda |az| p50 = 52° (sinir 61°). Yani tespit olasiligi OFF-AXIS
# aciyla da dusuyor; tesis bu ekseni hic modellemiyor, o yuzden faz olmuyor.
#
# OLCULEN conf ~ |eps_yaw| tablosu (bbox_ibvs_*.csv, n=14.350; tesis.py:456-464):
#       0-10°  0.656 | 30-40° 0.674 | 40-50° 0.629 | 50-60° 0.560 | 60-70° 0.536
# Bunu 0-10° kutusuna GORE kaydirma olarak kullaniyoruz.
KENAR_EGRI = [(5.0, 0.000), (35.0, +0.018), (45.0, -0.027),
              (55.0, -0.096), (65.0, -0.120)]

# conf DAGILIMININ genisligi (lojistik olcek) — UC OLCUMDEN COZULDU:
#   (a) faz ici sureklilik %78.5, kapi 0.35 -> P(conf>=0.35) = 0.785
#   (b) tespit edilen karelerde conf medyani 0.656  (KIRPILMIS medyan)
# Lojistik: (mu-0.35)/s = logit(0.785) = 1.295
#           (mu-0.656)/s = logit(0.5*0.785) = -0.4366
#   -> s = 0.306/1.7316 = 0.177,  mu = 0.579
# CAPRAZ DOGRULAMA 1: olum anindaki conf OLCULDU = 0.58; model mu = 0.579.
# CAPRAZ DOGRULAMA 2: bu s ile kapi 0.35->0.28 surekliligi %78.5 -> %84.4
#   yapiyor; deponun BAGIMSIZ tahmini "%85-88" (DURUM_2026-08-16.md:116).
# ⚠ ab_omur.py'deki 0.527/0.383 ciftinden cikan s=0.0655 YANLIS: o ornek
#   zaten conf>=0.35 ile kirpilmis, kirpilmis kuyruk s'i kucuk gosterir.
S_CONF = 0.177
MU_CONF = 0.579                  # kutu 11.1 px, eksende (OLCULEN olum kosulu)
KUTU_REF_PX = 11.1               # OLCULEN olum kutusu (boyut = sqrt(w*h))
# conf'un kutu boyutuyla egimi: tesisin lojistik egimi (0.22 /px) conf'a
# cevrildi -> 0.22 * s = 0.039 conf/px.
EGIM_CONF = Olcum.TESPIT_EGIM * S_CONF

# YANLIS NESNE hizinin conf esigiyle buyumesi. OLCULEN capa: negatif-kare
# conf tavani 0.219 (ab_omur.py:13) — esik oraya inince dedektor arka plana
# ates etmeye baslar. Ustel kuyruk: hiz(c) = 0.085*exp((0.35-c)/lam) ve
# hiz(0.219) = 1.0 olay/s (sel) -> lam = 0.131/ln(1/0.085) = 0.0531.
# ⚠ TAHMIN (kuyrugun sekli olculmedi, iki nokta capa).
LAM_FP = 0.0531


def _kenar_kaydirma(eps_deg):
    e = abs(eps_deg)
    if e <= KENAR_EGRI[0][0]:
        return KENAR_EGRI[0][1]
    for i in range(len(KENAR_EGRI) - 1):
        a, va = KENAR_EGRI[i]
        b, vb = KENAR_EGRI[i + 1]
        if a <= e <= b:
            return va + (vb - va) * (e - a) / (b - a)
    return KENAR_EGRI[-1][1]


class Dedektor:
    """Kutu boyutu + off-axis aci + conf esigi -> tespit olasiligi.

    P = lojistik( EGIM*(b - YARI) + (kenar_kaydirma(eps) - (conf-0.35))/s )

    conf = 0.35 ve kenar=KAPALI iken tesis.tespit_olasilik() ile AYNIDIR
    (yari=14.0 varsayilaninda) — yani "tesis kalibrasyonu" ozel hal.
    """

    def __init__(self, conf=0.35, yari_px=Olcum.TESPIT_YARI, kenar=True,
                 s_conf=S_CONF, fp=True, metrik="max"):
        self.conf = float(conf)
        self.yari = float(yari_px)
        self.kenar = bool(kenar)
        self.s = float(s_conf)
        self.fp = bool(fp)
        # ⚠ KUTU OLCUSU: tesis.tespit_olasilik() max(w,h) besliyor, ama
        # TESPIT_YARI=14 px "olculen medyan kutu 12.7 px" ile kalibre edildi
        # ve SAHADAKI o sayi boyut = sqrt(w*h). Tesisin modelledigi kutu cok
        # YASSI (h = 0.30*govde) oldugu icin max(w,h) ~ 2.3 * sqrt(w*h):
        # dedektor, kalibrasyonun kastettiginden 2.3 KAT buyuk bir kutu
        # goruyor ve faz hic olmuyor. metrik="sqrt" bunu duzeltir.
        self.metrik = metrik

    def _boy(self, w, h):
        return math.sqrt(max(w, 1e-9) * max(h, 1e-9)) if self.metrik == "sqrt" else max(w, h)

    def olasilik(self, w, h, cx):
        z = Olcum.TESPIT_EGIM * (self._boy(w, h) - self.yari)
        z -= (self.conf - 0.35) / self.s
        if self.kenar:
            eps = math.degrees(math.atan((cx - CX) / F_YASA))
            z += _kenar_kaydirma(eps) / self.s
        return 1.0 / (1.0 + math.exp(-max(-40.0, min(40.0, z))))

    def yanlis_hiz(self, taban=0.085):
        if not self.fp:
            return taban
        return taban * math.exp((0.35 - self.conf) / LAM_FP)

    def yeni_kare(self):
        pass

    def klon(self, tohum):
        return self

    def __repr__(self):
        return "Dedektor(conf=%.2f, yari=%.1f, kenar=%s)" % (
            self.conf, self.yari, self.kenar)


def _phi(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


class DedektorAR:
    """conf SURECI (AR-1) - tespit kaybini KORELE eden model.

    ⚠ NEDEN GEREKLI: tesisin tespit kaybi kareler arasi BAGIMSIZ. Sahada
    %78.5 sureklilik varken 20 ardisik kaybin olasiligi 0.215^20 = 4e-14 —
    yani BAGIMSIZ bir model 93/93 fazin bitisindeki "olum serisi"ni
    URETEMEZ. Faz olumu KORELE bir arizadir; bu sinif onu modeller.

    conf_t = mu(kutu, eps) + s * lojistik_kuantil( Phi(z_t) )
    z_t    = rho*z_{t-1} + sqrt(1-rho^2)*eps_t          (standart Gauss AR-1)
    tespit <=> conf_t >= kapi

    Marjinal dagilim TANIMI GEREGI lojistik(mu, s) kalir -> sureklilik
    dogrudan yukaridaki OLCULEN kalibrasyondan gelir; rho YALNIZ bosluk
    UZUNLUK dagilimini belirler ve OLCULEN "kurtarilan bosluklarin %69.5'i
    <= 4 kare" istatistigine oturtulur (bkz. kalibre_rho()).
    """

    # ── OLUMCUL COKUS (fatal gap) ─────────────────────────────────────────
    # ⚠⚠ NEDEN ELLE EKLENDI ve NEDEN SERBEST PARAMETRE:
    # Saha sayilari KENDI ICINDE bir celiski tasiyor:
    #     faz ici sureklilik %78.5  +  bosluklarin %69.5'i <=4 karede kapaniyor
    #     AMA gorsel temas yalnizca 0.69 s (~15 tik, ~2-3 bosluk) suruyor
    # Yani bosluklarin KABACA UCTE BIRI hic kapanmiyor. Duzgun (AR) bir
    # gurultu sureci bu IKI TEPELI dagilimi uretemez (rho=0.93'te >=20 karelik
    # bosluk orani yalnizca %4.2). Demek ki iki AYRI mekanizma var:
    #     (i) titresme  -> kisa bosluk, kendi kapanir
    #     (ii) COKUS    -> conf kaliciya yakin dusuyor, faz oluyor
    # ⚠ (ii)'nin SURESI SAHADAN OLCULEMEZ: gozlem penceresi KAYIP_M=20 karede
    # bitiyor, yani "kalici mi, 25 karede donuyor mu" sorusunun cevabi verinin
    # DISINDA. KAYIP_M'in degeri TAM DA bu bilinmeyene bagli oldugu icin
    # `tau_f` sabit degil, SUPURULEN parametredir (0.6 / 2.0 / sonsuz).
    def __init__(self, conf=0.35, rho=0.85, s_conf=S_CONF, kenar=True,
                 fp=True, mu0=MU_CONF, egim=EGIM_CONF, tohum=0,
                 h_olum=0.0, tau_f=2.0, delta_ort=0.35):
        self.conf = float(conf)
        self.rho = float(rho)
        self.s = float(s_conf)
        self.kenar = bool(kenar)
        self.fp = bool(fp)
        self.mu0 = float(mu0)
        self.egim = float(egim)
        self.h_olum = float(h_olum)       # 1/s — cokus tehlike orani
        self.tau_f = float(tau_f)         # s   — cokus suresi ortalamasi (inf ok)
        self.delta_ort = float(delta_ort)  # conf — cokus derinligi ortalamasi
        self.rnd = random.Random(104729 * tohum + 7)
        self.z = self.rnd.gauss(0.0, 1.0)
        self.cokus = 0.0                  # kalan cokus suresi (s)
        self.delta = 0.0
        self._dt = 1.0 / 21.3

    def yeni_kare(self, dt=None):
        # ⚠ COKUS tehlike orani ZAMAN basinadir (sahnenin ozelligi), kare
        # basina degil: kamera hizi degisince olay hizi degismemeli.
        dt = self._dt if dt is None else max(dt, 1e-6)
        self.z = (self.rho * self.z +
                  math.sqrt(max(1.0 - self.rho ** 2, 0.0)) * self.rnd.gauss(0.0, 1.0))
        if self.cokus > 0.0:
            self.cokus -= dt
            if self.cokus <= 0.0:
                self.delta = 0.0
        elif self.h_olum > 0.0 and self.rnd.random() < self.h_olum * dt:
            self.cokus = (float("inf") if self.tau_f == float("inf")
                          else self.rnd.expovariate(1.0 / self.tau_f))
            self.delta = self.rnd.expovariate(1.0 / self.delta_ort)

    def mu(self, w, h, cx):
        boyut = math.sqrt(max(w, 1e-9) * max(h, 1e-9))
        m = self.mu0 + self.egim * (boyut - KUTU_REF_PX)
        if self.kenar:
            m += _kenar_kaydirma(math.degrees(math.atan((cx - CX) / F_YASA)))
        return m - (self.delta if self.cokus > 0.0 else 0.0)

    def olasilik(self, w, h, cx):
        """AR durumu VERILDIGINDE tespit ikili karari (0/1 doner)."""
        u = _phi(self.z)
        u = min(max(u, 1e-12), 1.0 - 1e-12)
        conf_t = self.mu(w, h, cx) + self.s * math.log(u / (1.0 - u))
        return 1.0 if conf_t >= self.conf else 0.0

    def yanlis_hiz(self, taban=0.085):
        if not self.fp:
            return taban
        return taban * math.exp((0.35 - self.conf) / LAM_FP)

    def klon(self, tohum):
        return DedektorAR(conf=self.conf, rho=self.rho, s_conf=self.s,
                          kenar=self.kenar, fp=self.fp, mu0=self.mu0,
                          egim=self.egim, tohum=tohum, h_olum=self.h_olum,
                          tau_f=self.tau_f, delta_ort=self.delta_ort)

    def __repr__(self):
        return ("DedektorAR(conf=%.2f, rho=%.2f, h=%.2f, tau_f=%s)"
                % (self.conf, self.rho, self.h_olum, self.tau_f))


def kalibre_rho(hedef=0.695, p=0.785, n=400000):
    """rho'yu OLCULEN bosluk dagilimina oturt: kurtarilan bosluklarin
    %69.5'i <= 4 kare (gorev brifingi). Marjinal tespit orani p sabit."""
    esik = math.log(p / (1.0 - p))            # lojistik kuantil esigi
    en_iyi = None
    for rho in [0.0, 0.2, 0.4, 0.55, 0.65, 0.75, 0.8, 0.85, 0.9, 0.93, 0.95]:
        rnd = random.Random(12345)
        z = rnd.gauss(0, 1)
        k = math.sqrt(max(1 - rho ** 2, 0.0))
        bosluk = []
        uzun = 0
        for _ in range(n):
            z = rho * z + k * rnd.gauss(0, 1)
            u = min(max(_phi(z), 1e-12), 1 - 1e-12)
            var = math.log(u / (1 - u)) >= -esik
            if var:
                if uzun:
                    bosluk.append(uzun)
                uzun = 0
            else:
                uzun += 1
        if not bosluk:
            continue
        kisa = sum(1 for x in bosluk if x <= 4) / len(bosluk)
        p20 = sum(1 for x in bosluk if x >= 20) / len(bosluk)
        d = abs(kisa - hedef)
        if en_iyi is None or d < en_iyi[0]:
            en_iyi = (d, rho, kisa, p20, sum(bosluk) / len(bosluk))
        print("    rho %.2f : <=4 kare %.3f | >=20 kare %.4f | ort %.2f kare"
              % (rho, kisa, p20, sum(bosluk) / len(bosluk)))
    print("  -> rho = %.2f (hedef <=4 kare orani %.3f, model %.3f)"
          % (en_iyi[1], hedef, en_iyi[2]))
    return en_iyi[1]


# ══════════════════════════════════════════════════════════════════════════
#  YARDIMCI
# ══════════════════════════════════════════════════════════════════════════
def _hata_kopya(h, **kw):
    y = HataAyari()
    for k in dir(HataAyari):
        if k.startswith("_") or k.isupper():
            continue
        v = getattr(HataAyari, k)
        if callable(v):
            continue
        setattr(y, k, getattr(h, k))
    for k, v in kw.items():
        setattr(y, k, v)
    return y


def _aci(av, hx, hy, hz):
    """kadraj() ile AYNI zincir; (tx, ty, onde) doner (gorunurluk taniisi)."""
    dx, dy, dz = hx - av.x, hy - av.y, hz - av.z
    c, s = math.cos(-av.yaw), math.sin(-av.yaw)
    f = dx * c - dy * s
    r = dx * s + dy * c
    d = -dz
    pc, ps = math.cos(av.pitch), math.sin(av.pitch)
    f, d = f * pc - d * ps, f * ps + d * pc
    rc, rs = math.cos(av.roll), math.sin(av.roll)
    r, d = r * rc + d * rs, -r * rs + d * rc
    t = math.radians(Olcum.TILT)
    tc, ts = math.cos(t), math.sin(t)
    kf = f * tc - d * ts
    kd = f * ts + d * tc
    if kf <= 0.3:
        return 0.0, 0.0, False
    return r / kf, kd / kf, True


def _med(x):
    return st.median(x) if x else float("nan")


def _p(x, q):
    if not x:
        return float("nan")
    y = sorted(x)
    return y[max(0, min(len(y) - 1, int(q / 100.0 * (len(y) - 1))))]


# ══════════════════════════════════════════════════════════════════════════
#  ANGAJMAN — deney.kosu() ile BIT-AYNI + dort yeni kaldirac
# ══════════════════════════════════════════════════════════════════════════
def kosu(cfg=SahaCfg, hata=None, devir_m=17.7, sure=20.0, dt=1 / 62.0,
         tohum=0, faz0=0.0, devir_aci=0.0, hedef_yon=+1,
         pencere=0.25, tau=0.10, yasa_ici=True,
         kayip_m=20, dedektor=None, kopru_n=0, kopru_temas=False):
    """Tek gorsel faz.

    kayip_m   : gorsel fazi birakma esigi (ardisik kutusuz YASA dongusu)
    dedektor  : Dedektor | None (None -> tesisin kendi tespit_olasilik'i)
    kopru_n   : kayip karede son 2 gercek tespitten piksel hiziyla ileri
                tasi, EN FAZLA bu kadar ardisik kare (0 = kapali)
    kopru_temas: koprulenen kare "temas" sayilsin mi (kayip sayacini sifirlar)
    """
    if hata is None:
        hata = HataAyari()
    if dedektor is not None:
        dedektor = dedektor.klon(tohum)
        # tespit dusurmesini BEN yapacagim -> Algi'nin kendi kaybini kapat
        hata = _hata_kopya(hata, tespit_kaybi=False,
                           yanlis_hiz=dedektor.yanlis_hiz(hata.yanlis_hiz))
    algi = Algi(hata, tohum=tohum)
    rnd = random.Random(7919 * tohum + 13)          # dedektor icin AYRI akis

    hed = Hedef(faz0=faz0, yon=hedef_yon)
    hx, hy, hz, hvx, hvy, _ = hed.durum()
    hdg = math.atan2(hvy, hvx)
    yon = hdg + math.pi + math.radians(devir_aci)
    av = Avci(x=hx + devir_m * math.cos(yon), y=hy + devir_m * math.sin(yon),
              z=hz - 3.0, yaw=hdg, max_accel=cfg.MAX_ACCEL,
              v_max=cfg.V_TOPLAM_MAX, vz_max=cfg.VZ_MAX,
              yaw_rate_max=cfg.YAW_RATE_MAX_DEG)
    av.vx, av.vy = Olcum.HEDEF_HIZ * math.cos(hdg), Olcum.HEDEF_HIZ * math.sin(hdg)
    av.yaw = math.atan2(hy - av.y, hx - av.x)

    psi_v = math.atan2(av.vy, av.vx)
    psi_v_yasa = None
    hiz_I = Olcum.HEDEF_HIZ
    t = 0.0
    kayip = 0
    terminal = False
    los_o = t_o = None
    lam_f = 0.0
    gecmis = []
    en_yakin = 1e9
    gor = 0
    top = 0
    son_yasa_t = -1e9
    son_kare_kendi = -1e9                     # Algi'nin kamera kapisinin AYNISI

    # kopruleme durumu
    kop_gecmis = []          # son 2 GERCEK teslim: (t, cx, cy, w, h)
    kop_say = 0
    kop_kare = 0             # tani: kac kare koprulendi
    kop_kurtarma = 0         # tani: koprunun icinde gercek tespit dondu

    # tani
    t_ilk_kutu = t_son_kutu = None
    n_kutu = 0
    n_tik = 0                 # toplam YASA tiki
    n_doyum = 0               # yaw hizi tavana yapisan sim adimi
    bosluk = 0                # ardisik GERCEK kutusuz yasa tiki
    kurtarilan = []           # kapanan bosluklarin uzunlugu (tik)
    tik_ilk = tik_son = None  # ilk/son GERCEK kutunun tik indeksi
    n_tik_temas = 0
    son_eps = son_boyut = None
    lam_ic = []
    en_yakin_kesik = 1e9
    kilit = False

    while t < sure:
        hed.adim(dt)
        hx, hy, hz, hvx, hvy, _ = hed.durum()
        av._hedef_yon = math.atan2(hvy, hvx)
        k = kadraj(av, hx, hy, hz)
        top += 1
        d_simdi = math.dist((av.x, av.y, av.z), (hx, hy, hz))
        en_yakin = min(en_yakin, d_simdi)
        # ADIL ISKA: son GERCEK tespitten 0.5 s sonrasina kadar (kor kuyrugun
        # uzunlugu KAYIP_M ile degistigi icin ham en_yakin taraflidir).
        if not kilit:
            en_yakin_kesik = min(en_yakin_kesik, d_simdi)
            if t_son_kutu is not None and t > t_son_kutu + 0.5:
                kilit = True

        # ── DEDEKTOR KAPISI (kendi modelim; Algi'nin kamera kapisiyle AYNI an)
        k_ver = k
        if dedektor is not None:
            yeni_kare = not (hata.kamera_hz > 0.0 and
                             t - son_kare_kendi < 1.0 / hata.kamera_hz - 1e-9)
            # ⚠ LOCKSTEP: Algi'nin kamera kapisi da AYNI kosulu, AYNI baslangic
            # degeriyle kullaniyor -> ayni adimlarda ateslenir. Kamera karesi
            # OLMAYAN adimlarda Algi zaten k'yi yok sayar.
            if yeni_kare:
                dedektor.yeni_kare(t - son_kare_kendi if son_kare_kendi > -1e8 else None)
                son_kare_kendi = t
                self_p = 0.0 if k is None else dedektor.olasilik(k[2], k[3], k[0])
                if k is not None and rnd.random() >= self_p:
                    k_ver = None
        algi.kare_ver(t, av, k_ver)

        if hata.yasa_hz > 0.0 and t - son_yasa_t < 1.0 / hata.yasa_hz - 1e-9:
            av.adim(dt, t)
            t += dt
            continue
        dt_yasa = dt if son_yasa_t < 0.0 else max(t - son_yasa_t, dt)
        son_yasa_t = t
        n_tik += 1
        poz = algi.oku(t)
        yaw_olc = algi.yaw_oku(t)
        roll_olc, pitch_olc = algi.tutum_oku(t)
        if poz is not None:
            gor += 1

        # ── KOPRULEME: kayip karede kutuyu piksel hiziyla ileri tasi ──────
        kopru = False
        if poz is not None:
            if not kop_gecmis or abs(t - kop_gecmis[-1][0]) > 1e-9:
                kop_gecmis.append((t, poz[0], poz[1], poz[2], poz[3]))
                if len(kop_gecmis) > 2:
                    kop_gecmis.pop(0)
            if kop_say > 0:
                kop_kurtarma += 1
            kop_say = 0
        elif kopru_n > 0 and kop_say < kopru_n and len(kop_gecmis) >= 2:
            (t1, x1, y1, _, _), (t2, x2, y2, w2, h2) = kop_gecmis[-2], kop_gecmis[-1]
            dtk = t2 - t1
            if dtk > 1e-6:
                vx_px = (x2 - x1) / dtk
                vy_px = (y2 - y1) / dtk
                dtt = t - t2
                poz = (x2 + vx_px * dtt, y2 + vy_px * dtt, w2, h2)
                kop_say += 1
                kop_kare += 1
                kopru = True

        if poz is None or kopru:
            bosluk += 1
        if poz is None:
            kayip += 1
            if kayip >= kayip_m:
                break
        else:
            if not kopru:
                kayip = 0
                n_kutu += 1
                if t_ilk_kutu is not None and bosluk > 0:
                    kurtarilan.append(bosluk)
                bosluk = 0
                if t_ilk_kutu is None:
                    t_ilk_kutu = t
                    tik_ilk = n_tik
                t_son_kutu = t
                tik_son = n_tik
                kilit = False
                tx, ty, onde = _aci(av, hx, hy, hz)
                son_eps = abs(math.degrees(math.atan(tx)))
                son_boyut = math.sqrt(k[2] * k[3]) if k else None
            elif kopru_temas:
                kayip = 0
            else:
                kayip += 1
                if kayip >= kayip_m:
                    break
            cx, cy, w, h = poz
            los = yaw_olc + math.atan((cx - cfg.CX_NISAN) / F_YASA)
            if pencere > 0.0:
                if gecmis:
                    onc = gecmis[-1][1]
                    los_a = onc + ((los - onc + math.pi) % (2 * math.pi) - math.pi)
                else:
                    los_a = los
                gecmis.append((t, los_a))
                while gecmis and t - gecmis[0][0] > pencere:
                    gecmis.pop(0)
                if len(gecmis) >= 3:
                    n_ = len(gecmis)
                    tm = sum(g[0] for g in gecmis) / n_
                    lm = sum(g[1] for g in gecmis) / n_
                    sxx = sum((g[0] - tm) ** 2 for g in gecmis)
                    lam_f = (sum((g[0] - tm) * (g[1] - lm) for g in gecmis) / sxx) if sxx > 1e-12 else 0.0
                    lam_f = max(-6.0, min(6.0, lam_f))
                else:
                    lam_f = 0.0
            else:
                lam = 0.0
                if los_o is not None and t_o is not None and t - t_o > 1e-6:
                    lam = ((los - los_o + math.pi) % (2 * math.pi) - math.pi) / (t - t_o)
                    lam = max(-6.0, min(6.0, lam))
                los_o, t_o = los, t
                a = 1.0 if tau <= 0 else min(1.0, dt_yasa / max(tau, dt_yasa))
                lam_f += a * (lam - lam_f)
            lam_ic.append(abs(math.degrees(lam_f)))
            n_tik_temas += 1

            boyut = math.sqrt(w * h)
            if not terminal and boyut >= cfg.TERMINAL_BOYUT:
                terminal = True
            vx, vy, vz, yaw_cmd, hiz_I, tani = IB.komut(
                cx, cy, w, h, yaw_olc, hiz_I, dt_yasa, cfg, terminal,
                (lam_f, 0.0),
                pitch_olc, av.vz, None, roll_olc, av.yaw_hizi, psi_v_yasa)
            if yasa_ici:
                psi_v_yasa = tani.get("psi_v")
            psi_v = math.atan2(vy, vx)
            av.setpoint(vx, vy, vz, yaw_cmd, t)
        # YAW DOYUMU: saha "karelerin %23-47'si 120 deg/s tavaninda" olctu.
        # Tezgahta bu oran ~0 ise yaw kaldiracinin sinanacak yeri YOK demektir.
        if abs(math.degrees(av.yaw_hizi)) >= 0.95 * cfg.YAW_RATE_MAX_DEG:
            n_doyum += 1
        av.adim(dt, t)
        t += dt

    # ── OLUM SEKLI: fazin bittigi an hedef kadrajda miydi? ────────────────
    hx, hy, hz, _, _, _ = hed.durum()
    tx, ty, onde = _aci(av, hx, hy, hz)
    if not onde:
        olum = "arka"
    elif abs(tx) > TX_MAX:
        olum = "yan"
    elif abs(ty) > TY_MAX:
        olum = "dikey"
    else:
        olum = "ici"

    temas = (t_son_kutu - t_ilk_kutu) if (t_ilk_kutu is not None and
                                          t_son_kutu is not None) else 0.0
    return {
        "en_yakin": en_yakin,
        # ADIL ISKA: kor kuyrugun uzunlugu KAYIP_M ile degistigi ve en_yakin
        # bir MINIMUM oldugu icin ham metrik KAYIP_M'i otomatik odullendirir.
        # Bu metrik pencereyi son gercek tespitten +0.5 s'te KESER (ayni
        # pencere her kurulumda) -> kaldirac karsilastirmasi tarafsizlasir.
        "iska_adil": en_yakin_kesik if kilit else en_yakin,
        "omur": t, "temas": temas,
        "kesildi": t >= sure - 1e-6,
        "gorus": gor / max(top, 1),
        "kutu_orani": n_kutu / max(n_tik_temas + (gor - n_kutu) + 1e-9, 1e-9),
        "n_kutu": n_kutu,
        # SUREKLILIK: temas penceresindeki YASA tiklerinin kac tanesi kutu
        # tasiyor (saha tanimi: "faz ici sureklilik", olum serisi HARIC).
        "sureklilik": (n_kutu / max(1, tik_son - tik_ilk + 1)
                       if (tik_ilk is not None and tik_son > tik_ilk) else float("nan")),
        # KUTULU KARE ORANI: faz BOYUNCA (kor kuyruk DAHIL) — saha 0.41
        "kutu_orani_faz": n_kutu / max(1, n_tik),
        "olum": olum, "olum_eps": son_eps, "olum_kutu": son_boyut,
        "lam_p50": _med(lam_ic), "lam_p90": _p(lam_ic, 90),
        "kop_kare": kop_kare, "kop_kurtarma": kop_kurtarma,
        "yaw_doyum": n_doyum / max(top, 1),
        "kurtarilan": kurtarilan,
    }


def parti(n=120, **kw):
    return [kosu(faz0=i / n, tohum=i, **kw) for i in range(n)]


def ozet(r):
    e = [x["en_yakin"] for x in r]
    a = [x["iska_adil"] for x in r]
    o = [x["omur"] for x in r]
    return {
        "iska": _med(e), "iska_iyi": min(e), "iska_p10": _p(e, 10),
        "adil": _med(a), "adil_iyi": min(a),
        "omur": _med(o), "omur_p90": _p(o, 90),
        "temas": _med([x["temas"] for x in r]),
        "sur": _med([x["sureklilik"] for x in r if x["sureklilik"] == x["sureklilik"]]),
        "kor": _med([x["kutu_orani_faz"] for x in r]),
        "lam": _med([x["lam_p50"] for x in r if x["lam_p50"] == x["lam_p50"]]),
        "eps": _med([x["olum_eps"] for x in r if x["olum_eps"] is not None]),
        "kutu": _med([x["olum_kutu"] for x in r if x["olum_kutu"] is not None]),
        "doyum": _med([x["yaw_doyum"] for x in r]),
        "kurt": [g for x in r for g in x["kurtarilan"]],
        "ici": sum(1 for x in r if x["olum"] == "ici") / len(r),
        "yan": sum(1 for x in r if x["olum"] == "yan") / len(r),
        "v3": sum(1 for x in r if x["en_yakin"] < 3.0),
        "v3a": sum(1 for x in r if x["iska_adil"] < 3.0),
        "kes": sum(1 for x in r if x["kesildi"]),
        "n": len(r),
    }


BAS = ("  %-26s %7s %7s %7s %7s %6s %6s %5s %5s %5s %5s %4s" %
       ("kurulum", "iska", "eniyi", "adil", "omur", "temas", "sur", "kor",
        "eps", "ici", "lam", "<3m"))


def satir(ad, s):
    return ("  %-26s %6.2fm %6.2fm %6.2fm %6.2fs %5.2fs %5.0f%% %5.2f %4.0f° "
            "%4.0f%% %4.0f %2d/%d" %
            (ad, s["iska"], s["iska_iyi"], s["adil"], s["omur"], s["temas"],
             100 * s["sur"], s["kor"], s["eps"], 100 * s["ici"], s["lam"],
             s["v3"], s["n"]))


# ══════════════════════════════════════════════════════════════════════════
#  GERILEME SINAMASI — kendi dongum deney.kosu() ile BIT-AYNI mi?
# ══════════════════════════════════════════════════════════════════════════
def sinama_gerileme(n=12):
    kotu = []
    for i in range(n):
        kw = dict(faz0=i / n, tohum=i, devir_m=13.0, sure=8.0,
                  pencere=0.25, yasa_ici=True, cfg=SahaCfg)
        a = D.kosu(**kw)
        b = kosu(**kw)
        if abs(a["en_yakin"] - b["en_yakin"]) > 1e-9 or abs(a["sure"] - b["omur"]) > 1e-9:
            kotu.append((i, a["en_yakin"], b["en_yakin"], a["sure"], b["omur"]))
    print("  GERILEME (kendi dongu == deney.kosu): %s" %
          ("TAMAM (%d/%d)" % (n, n) if not kotu else "KALDI"))
    for x in kotu:
        print("    ! %s" % (x,))
    return kotu


# ══════════════════════════════════════════════════════════════════════════
#  IKI TEZGAH
# ══════════════════════════════════════════════════════════════════════════
DEVIR = 17.7          # m — OLCULEN devir menzili p50 (569 faz, §11)
N = 120

# TEZGAH A: tesis AYNEN (kendi tespit_olasilik'i). Faz 7-12 s yasiyor,
#           yani OMUR KISITI YOK -> omur kaldiraclari icin SAGIR.
# TEZGAH B: omur-kisitli, sahaya kalibre (bkz. DedektorAR).
B_TABAN = dict(rho=0.93, h_olum=1.4, tau_f=2.0, delta_ort=0.35,
               kenar=True, fp=True)


def tezgah_b(conf=0.35, **kw):
    d = dict(B_TABAN)
    d.update(kw)
    return DedektorAR(conf=conf, **d)


def kos(ad, plant, **kw):
    d = None if plant == "A" else tezgah_b(**kw.pop("det", {}))
    r = parti(n=N, devir_m=kw.pop("devir_m", DEVIR), dedektor=d, sure=20.0, **kw)
    s = ozet(r)
    print(satir(ad, s), flush=True)
    return s


def main():
    ne = sys.argv[1] if len(sys.argv) > 1 else "hepsi"
    if ne in ("hepsi", "sinama"):
        sinama_gerileme()
        T.dogrula()
        print()
    if ne in ("hepsi", "temel"):
        print("  -- SAHA vs TEZGAH (devir %.1f m, saha cfg, hata ACIK) --" % DEVIR)
        print("  %-26s %6s  %6s  %6s  %6s  %5s  %5s  %5s  %4s" %
              ("SAHA OLCUMU", "12.73m", "6.88m", "-", "1.28s", "0.69s",
               "79%", "0.41", "52d"))
        print(BAS)
        kos("A tesis (as-is)", "A")
        kos("B omur-kisitli", "B")
        kos("A hata KAPALI", "A", hata=HataAyari.kapali())
        kos("B hata KAPALI", "B", hata=HataAyari.kapali())
        print()
    if ne in ("hepsi", "kayip"):
        print("  -- 1) KAYIP_M --")
        print(BAS)
        for p in ("A", "B"):
            for km in (15, 20, 30, 45, 60):
                kos("%s KAYIP_M %d" % (p, km), p, kayip_m=km)
        print("  -- B, cokus suresi tau_f duyarliligi (OLCULEMEZ parametre) --")
        for tf in (0.6, 2.0, float("inf")):
            for km in (20, 30, 60):
                kos("B tau_f %-4s KAYIP_M %d" % (tf, km), "B",
                    kayip_m=km, det=dict(tau_f=tf))
        print()
    if ne in ("hepsi", "conf"):
        print("  -- 2) TESPIT GUVEN ESIGI (yanlis-tespit riski ACIK) --")
        print(BAS)
        for c in (0.25, 0.28, 0.32, 0.35, 0.40):
            kos("B conf %.2f (FP acik)" % c, "B", det=dict(conf=c))
        print("  -- FP KAPALI (yalniz sureklilik kazanci) --")
        for c in (0.25, 0.28, 0.35):
            kos("B conf %.2f (FP kapali)" % c, "B", det=dict(conf=c, fp=False))
        print("  -- cokus derinligi delta_ort duyarliligi --")
        for dl in (0.20, 0.35, 0.70):
            for c in (0.28, 0.35):
                kos("B delta %.2f conf %.2f" % (dl, c), "B",
                    det=dict(conf=c, delta_ort=dl))
        print()
    if ne in ("hepsi", "kopru"):
        print("  -- 3) KOPRULEME (kayip karede kutuyu ileri tasi) --")
        print(BAS)
        for p in ("A", "B"):
            for kn in (0, 2, 4, 6, 8):
                kos("%s kopru %d (temas yok)" % (p, kn), p, kopru_n=kn)
        print("  -- kopru TEMAS sayilsin (kayip sayacini sifirlar) --")
        for kn in (2, 4, 6, 8):
            kos("B kopru %d + temas" % kn, "B", kopru_n=kn, kopru_temas=True)
        print()
    if ne in ("hepsi", "yaw"):
        print("  -- 4) YAW_RATE_MAX_DEG --")
        print(BAS)
        for p in ("A", "B"):
            for yr in (60.0, 120.0, 180.0, 214.0):
                kos("%s yaw %.0f" % (p, yr), p, cfg=cfg_ile(YAW_RATE_MAX_DEG=yr))
        print()
    if ne in ("hepsi", "kombo"):
        print("  -- 5) KOMBINASYON --")
        print(BAS)
        kos("B taban (K20, conf35)", "B")
        kos("B K30", "B", kayip_m=30)
        kos("B K45", "B", kayip_m=45)
        kos("B K60", "B", kayip_m=60)
        kos("B conf30", "B", det=dict(conf=0.30))
        kos("B K30+conf30", "B", kayip_m=30, det=dict(conf=0.30))
        kos("B K45+conf30", "B", kayip_m=45, det=dict(conf=0.30))
        kos("B K60+conf30", "B", kayip_m=60, det=dict(conf=0.30))
        kos("B K45+conf30+kopru2", "B", kayip_m=45, det=dict(conf=0.30), kopru_n=2)
        kos("B K45+conf30+kopru2T", "B", kayip_m=45, det=dict(conf=0.30),
            kopru_n=2, kopru_temas=True)
        kos("B K45+conf30+yaw180", "B", kayip_m=45, det=dict(conf=0.30),
            cfg=cfg_ile(YAW_RATE_MAX_DEG=180.0))
        print("  -- ayni kombo, TEZGAH A (omur kisiti YOK) --")
        kos("A taban", "A")
        kos("A K45+kopru2", "A", kayip_m=45, kopru_n=2)
        print("  -- SAGLAMLIK: kombo, degisik devir menzili ve donus yonu --")
        for dm in (13.0, 17.7, 22.0):
            kos("B K45+conf30 devir %.0f" % dm, "B", kayip_m=45,
                det=dict(conf=0.30), devir_m=dm)
        kos("B K45+conf30 yon -1", "B", kayip_m=45, det=dict(conf=0.30),
            hedef_yon=-1)
        print("  -- UCURUM: cok buyuk KAYIP_M --")
        for km in (60, 90, 120):
            kos("B K%d+conf30" % km, "B", kayip_m=km, det=dict(conf=0.30))
        print()


if __name__ == "__main__":
    main()

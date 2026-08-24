# -*- coding: utf-8 -*-
"""BURUN (yaw) KONTROLCUSU TARAMASI - hedefi kadrajda tutmak.

⚠ SADECE OKUR. sim/tesis.py, sim/deney.py, arac/sim_omur.py ve kopru/
altindaki YASA KODU DEGISTIRILMEZ; hepsi aynen import edilir.

NEDEN BURUN
--------------------------------------------------------------------------
Olculen (569 faz):
    faz omru <-> LOS azimut hizi    rho = -0.657   (en guclu bagintili)
    tespit kayip orani  merkezde 0.036, >39° 0.609 (17 kat)
    fazlarin %64.7'si hedef kadrajin ICINDEYKEN tespit olerek bitiyor
    olum aninda |eps| p50 52°  (kadraj siniri 61°)
Yani kadraj = faz omru = tek gercek kisit.

NASIL DEGISTIRILIYOR (yasaya DOKUNMADAN)
--------------------------------------------------------------------------
Yasanin kendi burun satiri (bbox_ibvs.py:813-817):
    yaw_cmd = iris_yaw + K_YAW*eps_yaw + BURUN_KD*eps_hizi
BURUN_KD ve eps_hizi ZATEN yasanin arayuzunde var (nose-only: komut()
icinde yalniz yaw_cmd'yi etkiler, hiz yolunu HIC etkilemez). Kp ve ofset
icin komut()'un dondurdugu yaw_cmd'ye tani["eps_yaw"] ile TAM ayni
formulden ek terim bindirilir:
    yaw_cmd' = yaw_cmd + (Kp-1)*eps_yaw + ofset
Kp'yi cfg.K_YAW ile degistirmek YANLIS OLURDU: K_YAW hiz yonunu de
(eps_hiz / _taban) etkiler, o zaman tek degisken kurali kirilirdi.
Kp=1, Kd=0, ofset=0'da bu dongu sim_omur.kosu() ile BIT-AYNIDIR
(sinama_gerileme(), tutmazsa betik durur).

eps_hizi = kutunun KADRAJ ICI kayma hizi (rad/s). SAF PIKSEL:
atan((cx-CX)/F)'in en kucuk kareler egimi, YALNIZ gercek tespitlerden.
Atalet LOS hizi (lam) DEGIL — lam olculen sekilde 4-7 kat sisik.
⚠ Kadraj ici kayma = LOS_hizi - yaw_hizi, yani D terimi hem hedef
onceleme hem KENDI yaw'ina sonum katar; iki isi birden yapar.

⚠⚠ TEZGAHIN BU SORUDAKI ZAYIFLIGI (baska bir ajan olctu, dogrulandi)
--------------------------------------------------------------------------
Tezgah B, sahanin |eps| ve yaw doyumu rejimini URETEMIYOR:
    olum aninda |eps|   saha 52°      tezgah   6°
    yaw tavanina yapisan kare  saha %23-47   tezgah ~%3
Yani burun DOYUMU sorusunda tezgah SAGIR. Bu yuzden:
  (a) tek "olum |eps|" degil, faz BOYUNCA |eps| p50/p90 ve >39° tik orani
      raporlanir (bunlar doyum olmadan da ayirt ediyor),
  (b) SAHA GRIDI'ne devir 8 m ve aspect ±40° gibi lam'i yukari iten
      kosullar KONULDU (orada doyum gercekten oluyor),
  (c) sonuc buna gore NITELENIR, kesin konusulmaz.

════════════════════════════════════════════════════════════════════════════
SONUC (2880 angajman/varyant, ESLENMIS kiyas — `python arac/sim_burun.py`)
════════════════════════════════════════════════════════════════════════════
MEVCUT BURUN KAZANIYOR. Denenen 9 aile (sessiz P, PD 2B, doygun ofset, yaw
hiz siniri, kor burun surdurme, kazanc cizelgesi, varsayimsal yaw gecikmesi,
doyum rejimi) icinde referansi ESLENMIS olarak geceni YOK.
    referans (P, K_YAW=1.0, 120°/s): |eps| p50 10.3° p90 26.8° | >39° tik %2
    yandan cikis %12 | faz omru 3.77 s | TESPITLI sure 2.66 s | iska 9.4 m
YAYLA : Kp 0.7-1.6 ve yaw tavani 90-214 °/s istatistiksel olarak AYNI.
UCURUM: Kp <= 0.3 (temas t-4.3, eps90 +4.5°, yandan cikis +5.3 puan) ve
        yaw tavani <= 40-60 °/s. Yani "sessiz burun kazaniyor" YANLIS —
        sessiz burun DONUSTE kaybediyor (t-3.7), duzde yalnizca NOTR.
D TERIMI (BURUN_KD) ve DOYGUN OFSET: Kd/ofset buyudukce TEK YONLU kotulesme
        (Kd 0->0.70: eps90 26.8->56.0, temas 2.85->1.69 s). Bu, yaw kanali
        1. mertebe gecikiyor VARSAYILDIGINDA da (tau_y 0.10/0.21 s), yaw
        tavani 40/60 °/s'ye kisilip DOYUM uretildiginde de degismedi.
        Sebep: burun zaten bir INTEGRATOR ve Kp=1 deadbeat; u = Kp*e + Kd*e'
        koyunca kapali dongu e'(1+Kd/T) = lam - Kp*e/T olur — kalici hata
        DEGISMEZ, yalnizca yanit YAVASLAR. D terimi burada ONDELEME degil
        SONUM katiyor.
TAVAN  : KAHIN burun (yaw_cmd = truth kerteriz) temas +0.65 s (t+10),
        eps90 -11.5° (t-26), yandan cikis -8.6 puan. Yani burun kanalinda
        GERCEK bir acik VAR — ama uygulanabilir hicbir kazanc ayari onun
        bir kismini bile almiyor. Acik KAZANCTA degil GIRDIDE:
            yanlis nesne kapali : temas +0.92 s, eps90 -4.1°, cikis -4.6 p
            kutu gecikmesi yok  : temas +1.12 s
            yaw hatasi yok      : temas +0.25 s
            kenar yanliligi yok : ETKISIZ (t 0.4)
⚠ Dongu hizi satirlari (30/42/62 Hz) KARISIK DEGISKEN: yasa_hz ayni zamanda
  PN'in lam penceresindeki ornek sayisini degistiriyor, yani HIZ yolunu da
  oynatiyor. Burun bulgusu olarak OKUNMAMALI.
DIKEY : hicbir varyant dikeyi bozmuyor da duzeltmiyor de — ayrim +1.8..+2.2 m,
        yukselis +5.5..+6.4°, vz doyumu %9-12, dikeyden cikis %3.3-6.1.
        Elenen varyantlar YATAY gerekcesiyle elendi, dikey gerekcesiyle degil.
════════════════════════════════════════════════════════════════════════════
"""
import math
import os
import statistics as st
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "kopru", "gazebo_kaynak"))
sys.path.insert(0, os.path.join(KOK, "sim"))
sys.path.insert(0, os.path.join(KOK, "arac"))

import tesis as T                                                  # noqa: E402
from tesis import (Avci, Hedef, Olcum, kadraj, F_YASA, CX,         # noqa: E402
                   TX_MAX, TY_MAX, HataAyari, Algi)
from control.guidance import bbox_ibvs as IB                       # noqa: E402
import sim_omur as SO                                              # noqa: E402
from sim_omur import (SahaCfg, cfg_ile, tezgah_b, _hata_kopya,     # noqa: E402
                      _aci, _med, _p)


# ══════════════════════════════════════════════════════════════════════════
#  BURUN YASASI — tek noktada toplandi
# ══════════════════════════════════════════════════════════════════════════
def _norm(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


class Burun:
    """Burun (yaw) yasasi varyanti.

    yaw_cmd = iris_yaw + Kp*eps_yaw + Kd*eps_hizi + ofset(eps_hizi)
    ofset   = OFS * tanh(eps_hizi / OFS_REF)      [KAYMA YONUNDE, doygun]

    ⚠ ofset ve Kd AYNI ISARETLI: ikisi de kutuyu kaymanin GELDIGI tarafa
    kaydirir (hedef sola kayiyorsa kutu kadrajin sagina oturur, sol tarafta
    butce birikir). Yani "ofset" = DOYGUN bir D terimi, ayri bir mekanizma
    degil. Fark: D dogrusal ve gurultuye acik, ofset tavanli.

    kor  : KOR BURUN SURDURME (s). Kutu yokken burun DONUYORDU (setpoint
           tekrarlaniyor). Bu, son iki kutulu tikin yaw_cmd egimiyle burnu
           SURDURUR — hiz komutu AYNEN tekrarlanir, yani NOSE-ONLY.
    """

    __slots__ = ("kp", "kd", "ofs", "ofs_ref", "kor", "pencere", "yawrate",
                 "tau_y", "kp2", "eps_c", "kahin", "ad")

    def __init__(self, ad="P 1.0", kp=1.0, kd=0.0, ofs=0.0, ofs_ref=30.0,
                 kor=0.0, pencere=0.30, yawrate=120.0, tau_y=0.0,
                 kp2=None, eps_c=25.0, kahin=False):
        self.ad = ad
        self.kp = float(kp)
        self.kd = float(kd)                 # s
        self.ofs = float(ofs)               # deg (tavan)
        self.ofs_ref = float(ofs_ref)       # deg/s (doyum olcegi)
        self.kor = float(kor)               # s (0 = kapali)
        self.pencere = float(pencere)       # s (eps_hizi en kucuk kareler)
        self.yawrate = float(yawrate)       # deg/s
        # ⚠⚠ VARSAYIM EKSENI, OLCUM DEGIL. tesis.Avci yaw kanalina YALNIZ
        # 46 ms olu zaman + hiz siniri koyar; 211 ms zaman sabiti SADECE
        # vx/vy/vz'ye uygulanir (Avci.adim). Yani tezgahta burun neredeyse
        # SAF INTEGRATOR: Kp=1 deadbeat'tir ve TUREV TERIMININ TELAFI
        # EDECEGI GECIKME YOKTUR. Depoda yaw basamak yaniti OLCULMEMIS.
        # tau_y > 0, "yaw da vx gibi 1. mertebe gecikseydi" varsayimini
        # kurar (komut yolunda 1. mertebe suzgec). SONUC NITELENEREK
        # okunmali: tau_y=0 sutunu OLCULMUS tezgah, digerleri HIPOTEZ.
        self.tau_y = float(tau_y)           # s (0 = tezgahin kendisi)
        # ── KURTARMA KAZANCI (kazanc cizelgesi) ──────────────────────────
        # Merkez civarinda SAKIN, kenarda SERT. Gerekce: olculen tespit
        # kaybi merkezde 0.036, >39°'de 0.609 — yani hata BUYUDUKCE
        # marjinal maliyet PATLIYOR. Sabit kazanc bu asimetriyi gormez.
        # kp2=None -> kapali (kp sabit).
        self.kp2 = None if kp2 is None else float(kp2)
        self.eps_c = float(eps_c)           # deg; rampanin BASI (55°'de doyar)
        # ── KAHIN BURUN (TAVAN OLCUMU, UYGULANAMAZ) ──────────────────────
        # yaw_cmd = hedefe GERCEK kerteriz (truth). Yani sifir olcum hatasi,
        # sifir gecikme, sifir kayip: HICBIR burun yasasi bundan iyi olamaz.
        # ⚠ Bu bir varyant DEGIL, UST SINIR. "Hicbir sey kazanmiyor"
        # sonucunu "kaldiraci bulamadim"dan ayirmanin tek yolu.
        self.kahin = bool(kahin)

    def kazanc(self, eps_yaw):
        if self.kp2 is None:
            return self.kp
        e = abs(math.degrees(eps_yaw))
        u = (e - self.eps_c) / max(55.0 - self.eps_c, 1e-6)
        u = 0.0 if u < 0.0 else (1.0 if u > 1.0 else u)
        return self.kp + (self.kp2 - self.kp) * u

    def ek(self, eps_yaw, eps_hizi):
        """Yasanin yaw_cmd'sine BINDIRILECEK ek (rad). Kp=1,Kd=0,ofs=0 -> 0."""
        e = (self.kazanc(eps_yaw) - 1.0) * eps_yaw
        if self.ofs != 0.0:
            e += math.radians(self.ofs) * math.tanh(
                math.degrees(eps_hizi) / max(self.ofs_ref, 1e-6))
        return e

    def yasa_kd(self):
        """Yasanin KENDI BURUN_KD alanina verilecek deger (nose-only)."""
        return self.kd

    def __repr__(self):
        return self.ad


def burun_ile(**kw):
    return Burun(**kw)


class BurunH(Burun):
    """Burun + hangi OLCUM HATASI kurulumunda kosulacagi (ablation)."""
    __slots__ = ("_h",)

    def __init__(self, *a, **kw):
        h = kw.pop("hata_ad", "tam")
        Burun.__init__(self, *a, **kw)
        self._h = h


# ══════════════════════════════════════════════════════════════════════════
#  SAHA GRIDI — "duz de olsa manevra da olsa" (tek senaryoya optimize etme)
# ══════════════════════════════════════════════════════════════════════════
# Oval pistin yay uzunlugu: duz kenar 104.78 m, donus yayi pi*51 = 160.2 m.
#   faz0 [0.000, 0.198) 1. DUZ | [0.198, 0.500) 1. DONUS
#        [0.500, 0.698) 2. DUZ | [0.698, 1.000) 2. DONUS
_L = (Olcum.TUR_UZUNLUK - 2 * math.pi * Olcum.DONUS_YARICAP) / 2.0
_CEV = 2 * _L + 2 * math.pi * Olcum.DONUS_YARICAP
DUZ_SON = _L / _CEV                                  # 0.1977
DONUS_ORTA = (_L + math.pi * Olcum.DONUS_YARICAP / 2.0) / _CEV   # 0.3489

# hedef davranisi (4 kip) — hepsi 20.1 °/s olculen donus hizini kullanir
KIPLER = ("duz", "donus+", "donus-", "orta")

# tespit surekliligi: kalibre taban conf 0.35 / h_olum 1.4 (Tezgah B)
DET_IYI = dict(conf=0.30, h_olum=0.9)
DET_KOTU = dict(conf=0.40, h_olum=2.0)


def _faz0(kip, i, n):
    """Kip icinde deterministik, tekrarlanabilir baslangic fazi.

    ⚠ i MUTLAKA modulo alinir. Ilk surumde alinmiyordu: faz0 1'i asinca
    Hedef.durum() dongunun ILK adiminda s'i modulo aliyor ve hedef
    ISINLANIYORDU (kurulum geometrisi baska yerde, ilk kare baska yerde).
    Donus hucrelerinin temas suresi 0.00 s cikmasinin sebebi buydu.
    """
    u = ((i % n) + 0.5) / n
    if kip == "duz":
        return 0.02 + 0.10 * u                      # 1. duz kenarin ici
    if kip == "orta":
        return DONUS_ORTA + 0.010 * (u - 0.5)       # DONUSUN TAM ORTASI
    return 0.22 + 0.22 * u                          # 1. donus boyunca


def saha(tekrar=2):
    """Tam capraz grid; her varyant AYNI listeyle sinanir.

    4 menzil x 5 aspect x 3 dikey ofset x 4 kip x 2 tespit = 480 hucre.
    """
    g = []
    i = 0
    for dm in (8.0, 13.0, 20.0, 30.0):
        for da in (-40.0, -20.0, 0.0, 20.0, 40.0):
            for dz in (0.0, 3.0, 8.0):
                for kip in KIPLER:
                    for det_ad in ("iyi", "kotu"):
                        for k in range(tekrar):
                            g.append(dict(
                                devir_m=dm, devir_aci=da, dikey=dz, kip=kip,
                                det_ad=det_ad,
                                hedef_yon=(-1 if kip == "donus-" else +1),
                                faz0=_faz0(kip, i + 37 * k, 97),
                                tohum=i * 7 + k))
                            i += 1
    return g


# ══════════════════════════════════════════════════════════════════════════
#  ANGAJMAN — sim_omur.kosu() ile BIT-AYNI + burun kaldiraci + kadraj tanisi
# ══════════════════════════════════════════════════════════════════════════
def kosu(burun=None, cfg=None, hata=None, devir_m=17.7, sure=20.0, dt=1 / 62.0,
         tohum=0, faz0=0.0, devir_aci=0.0, hedef_yon=+1, dikey=3.0,
         pencere=0.25, tau=0.10, yasa_ici=True, kayip_m=20, dedektor=None):
    """Tek gorsel faz. burun=None -> yasanin MEVCUT burnu (P, K_YAW=1)."""
    if burun is None:
        burun = Burun()
    if cfg is None:
        cfg = SahaCfg
    if burun.kd != 0.0 or getattr(cfg, "BURUN_KD", 0.0) != 0.0:
        cfg = cfg_ile(BURUN_KD=burun.yasa_kd())      # yasanin KENDI alani
    if burun.yawrate != cfg.YAW_RATE_MAX_DEG:
        cfg = type("Cfg_", (cfg,), dict(YAW_RATE_MAX_DEG=burun.yawrate))
    if hata is None:
        hata = HataAyari()
    if dedektor is not None:
        dedektor = dedektor.klon(tohum)
        hata = _hata_kopya(hata, tespit_kaybi=False,
                           yanlis_hiz=dedektor.yanlis_hiz(hata.yanlis_hiz))
    algi = Algi(hata, tohum=tohum)
    import random
    rnd = random.Random(7919 * tohum + 13)

    hed = Hedef(faz0=faz0, yon=hedef_yon)
    hx, hy, hz, hvx, hvy, _ = hed.durum()
    hdg = math.atan2(hvy, hvx)
    yon = hdg + math.pi + math.radians(devir_aci)
    av = Avci(x=hx + devir_m * math.cos(yon), y=hy + devir_m * math.sin(yon),
              z=hz - dikey, yaw=hdg, max_accel=cfg.MAX_ACCEL,
              v_max=cfg.V_TOPLAM_MAX, vz_max=cfg.VZ_MAX,
              yaw_rate_max=cfg.YAW_RATE_MAX_DEG)
    av.vx, av.vy = Olcum.HEDEF_HIZ * math.cos(hdg), Olcum.HEDEF_HIZ * math.sin(hdg)
    av.yaw = math.atan2(hy - av.y, hx - av.x)

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
    son_kare_kendi = -1e9

    t_ilk_kutu = t_son_kutu = None
    n_kutu = 0
    n_tik = 0
    n_doyum = 0
    bosluk = 0
    tik_ilk = tik_son = None
    n_tik_temas = 0
    son_eps = son_boyut = None
    lam_ic = []
    en_yakin_kesik = 1e9
    kilit = False

    # ── BURUN TANISI ──────────────────────────────────────────────────────
    d_gec = []            # (t, eps_piksel_rad) — YALNIZ gercek tespitler
    eps_hizi = 0.0
    eps_ler = []          # |eps| TRUTH (deg), faz boyunca her yasa tikinde
    eps_temas = []        # |eps| TRUTH, yalniz kutulu tiklerde
    n_disari = 0          # kadrajin GERCEK acisal sinirinin disindaki tik
    n_vz_doyum = 0
    ayrim = []            # hz - av.z  (m, + = hedef yukarda)
    yukselis = []         # deg, TRUTH
    son_cmd = None        # (vx, vy, vz, yaw_cmd) — kor surdurme icin
    kor_w = 0.0           # yaw_cmd'nin son egimi (rad/s)
    kor_t = None
    onc_yaw_cmd = onc_yaw_t = None
    n_kor = 0
    yaw_f = None          # varsayimsal yaw gecikmesi suzgeci (tau_y)

    while t < sure:
        hed.adim(dt)
        hx, hy, hz, hvx, hvy, _ = hed.durum()
        av._hedef_yon = math.atan2(hvy, hvx)
        k = kadraj(av, hx, hy, hz)
        top += 1
        d_simdi = math.dist((av.x, av.y, av.z), (hx, hy, hz))
        en_yakin = min(en_yakin, d_simdi)
        if not kilit:
            en_yakin_kesik = min(en_yakin_kesik, d_simdi)
            if t_son_kutu is not None and t > t_son_kutu + 0.5:
                kilit = True

        k_ver = k
        if dedektor is not None:
            yeni_kare = not (hata.kamera_hz > 0.0 and
                             t - son_kare_kendi < 1.0 / hata.kamera_hz - 1e-9)
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

        # ── KADRAJ TANISI (TRUTH) — her yasa tikinde ─────────────────────
        tx_t, ty_t, onde_t = _aci(av, hx, hy, hz)
        if onde_t:
            eps_ler.append(abs(math.degrees(math.atan(tx_t))))
            if abs(tx_t) > TX_MAX or abs(ty_t) > TY_MAX:
                n_disari += 1
        else:
            eps_ler.append(90.0)
            n_disari += 1
        ayrim.append(hz - av.z)
        yukselis.append(math.degrees(math.atan2(
            hz - av.z, max(math.hypot(hx - av.x, hy - av.y), 1e-6))))

        if poz is None:
            bosluk += 1
            kayip += 1
            # ── KOR BURUN SURDURME (nose-only) ───────────────────────────
            if (burun.kor > 0.0 and son_cmd is not None and kor_t is not None
                    and t - kor_t <= burun.kor and abs(kor_w) > 1e-6):
                yaw_k = _norm(son_cmd[3] + kor_w * (t - kor_t))
                av.setpoint(son_cmd[0], son_cmd[1], son_cmd[2], yaw_k, t)
                n_kor += 1
            if kayip >= kayip_m:
                break
        else:
            kayip = 0
            n_kutu += 1
            if t_ilk_kutu is not None and bosluk > 0:
                pass
            bosluk = 0
            if t_ilk_kutu is None:
                t_ilk_kutu = t
                tik_ilk = n_tik
            t_son_kutu = t
            tik_son = n_tik
            kilit = False
            son_eps = eps_ler[-1]
            son_boyut = math.sqrt(k[2] * k[3]) if k else None
            eps_temas.append(eps_ler[-1])

            cx, cy, w, h = poz
            # ── eps_hizi: SAF PIKSEL kadraj-ici kayma (en kucuk kareler) ──
            eps_px = math.atan((cx - cfg.CX_NISAN) / F_YASA)
            d_gec.append((t, eps_px))
            while d_gec and t - d_gec[0][0] > burun.pencere:
                d_gec.pop(0)
            if len(d_gec) >= 3:
                n_ = len(d_gec)
                tm = sum(g[0] for g in d_gec) / n_
                em = sum(g[1] for g in d_gec) / n_
                sxx = sum((g[0] - tm) ** 2 for g in d_gec)
                eps_hizi = (sum((g[0] - tm) * (g[1] - em) for g in d_gec) / sxx
                            if sxx > 1e-12 else 0.0)
                eps_hizi = max(-6.0, min(6.0, eps_hizi))
            else:
                eps_hizi = 0.0

            los = yaw_olc + math.atan((cx - cfg.CX_NISAN) / F_YASA)
            if pencere > 0.0:
                if gecmis:
                    onc = gecmis[-1][1]
                    los_a = onc + _norm(los - onc)
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
                    lam = _norm(los - los_o) / (t - t_o)
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
                pitch_olc, av.vz, None, roll_olc, av.yaw_hizi, psi_v_yasa,
                eps_hizi)
            # ── BURUN EKI (Kp ve doygun ofset) ───────────────────────────
            if burun.kahin:
                yaw_cmd = math.atan2(hy - av.y, hx - av.x)   # TRUTH kerteriz
            else:
                ek = burun.ek(tani["eps_yaw"], eps_hizi)
                if ek != 0.0:
                    yaw_cmd = _norm(yaw_cmd + ek)
            # ── VARSAYIMSAL YAW GECIKMESI (bkz. Burun.tau_y) ─────────────
            if burun.tau_y > 0.0:
                if yaw_f is None:
                    yaw_f = yaw_cmd
                else:
                    a_ = 1.0 - math.exp(-dt_yasa / burun.tau_y)
                    yaw_f = _norm(yaw_f + a_ * _norm(yaw_cmd - yaw_f))
                yaw_cmd = yaw_f
            if yasa_ici:
                psi_v_yasa = tani.get("psi_v")
            av.setpoint(vx, vy, vz, yaw_cmd, t)
            son_cmd = (vx, vy, vz, yaw_cmd)
            if onc_yaw_cmd is not None and t - onc_yaw_t > 1e-6:
                kor_w = max(-math.radians(burun.yawrate),
                            min(math.radians(burun.yawrate),
                                _norm(yaw_cmd - onc_yaw_cmd) / (t - onc_yaw_t)))
            onc_yaw_cmd, onc_yaw_t = yaw_cmd, t
            kor_t = t
            _vzt = cfg.VZ_MAX_TERM if terminal else cfg.VZ_MAX
            if abs(vz) >= 0.95 * _vzt:
                n_vz_doyum += 1
        if abs(math.degrees(av.yaw_hizi)) >= 0.95 * cfg.YAW_RATE_MAX_DEG:
            n_doyum += 1
        av.adim(dt, t)
        t += dt

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
        "iska_adil": en_yakin_kesik if kilit else en_yakin,
        "omur": t, "temas": temas,
        "kesildi": t >= sure - 1e-6,
        "gorus": gor / max(top, 1),
        "n_kutu": n_kutu,
        "sureklilik": (n_kutu / max(1, tik_son - tik_ilk + 1)
                       if (tik_ilk is not None and tik_son > tik_ilk) else float("nan")),
        "kutu_orani_faz": n_kutu / max(1, n_tik),
        "olum": olum, "olum_eps": son_eps, "olum_kutu": son_boyut,
        "lam_p50": _med(lam_ic),
        "yaw_doyum": n_doyum / max(top, 1),
        # ── burun metrikleri ──
        "eps_p50": _med(eps_ler), "eps_p90": _p(eps_ler, 90),
        "eps_max": max(eps_ler) if eps_ler else float("nan"),
        "eps_t50": _med(eps_temas),
        "eps39": sum(1 for e in eps_ler if e > 39.0) / max(1, len(eps_ler)),
        "disari": n_disari / max(1, n_tik),
        # ── dikey metrikleri ──
        "ayrim": _med(ayrim), "yukselis": _med(yukselis),
        "vz_doyum": n_vz_doyum / max(1, n_tik_temas),
        "kor_tik": n_kor,
    }


# ══════════════════════════════════════════════════════════════════════════
#  GERILEME — burun VARSAYILANDA sim_omur.kosu() ile BIT-AYNI mi?
# ══════════════════════════════════════════════════════════════════════════
def sinama_gerileme(n=16):
    kotu = []
    for i in range(n):
        kw = dict(faz0=i / n, tohum=i, devir_m=13.0, sure=8.0, pencere=0.25)
        a = SO.kosu(cfg=SahaCfg, **kw)
        b = kosu(burun=Burun(), cfg=SahaCfg, dikey=3.0, **kw)
        if (abs(a["en_yakin"] - b["en_yakin"]) > 1e-9 or
                abs(a["omur"] - b["omur"]) > 1e-9 or a["olum"] != b["olum"]):
            kotu.append((i, a["en_yakin"], b["en_yakin"], a["omur"], b["omur"]))
    # ayni sinama TEZGAH B dedektoru ile
    for i in range(n):
        kw = dict(faz0=i / n, tohum=i, devir_m=17.7, sure=10.0, pencere=0.25)
        a = SO.kosu(cfg=SahaCfg, dedektor=tezgah_b(), **kw)
        b = kosu(burun=Burun(), cfg=SahaCfg, dikey=3.0, dedektor=tezgah_b(), **kw)
        if (abs(a["en_yakin"] - b["en_yakin"]) > 1e-9 or
                abs(a["omur"] - b["omur"]) > 1e-9):
            kotu.append(("B%d" % i, a["en_yakin"], b["en_yakin"],
                         a["omur"], b["omur"]))
    print("  GERILEME (burun varsayilan == sim_omur.kosu): %s" %
          ("TAMAM (%d/%d)" % (2 * n, 2 * n) if not kotu else "KALDI"))
    for x in kotu:
        print("    ! %s" % (x,))
    return kotu


def sinama_isaret():
    """ISARET ve OLCEK: D terimi ve ofset kutuyu DOGRU tarafa itiyor mu?

    ⚠ Bu bir birim testi: yasanin kendi komut() cagrisi ile.
    Kutu SAGDA (cx>CX) ve SAGA kayiyorsa (eps_hizi>0):
        burun DAHA COK saga donmeli mi?  HAYIR — onceleme demek burnu
        kaymanin GITTIGI yone atmak demektir, yani yaw_cmd ARTAR.
        Sonucta kutu kadrajin SOLUNA oturur ve sag tarafta butce birikir.
    Kayma NEGATIFSE isaret de negatif olmali (simetri).
    """
    h = []
    ar = dict(cx=CX + 40.0, cy=300.0, w=12.0, h=6.0, iris_yaw=0.0,
              hiz_I=18.0, dt=0.047)
    c0 = cfg_ile(BURUN_KD=0.0)
    c1 = cfg_ile(BURUN_KD=0.20)
    y0 = IB.komut(ar["cx"], ar["cy"], ar["w"], ar["h"], 0.0, 18.0, 0.047,
                  c0, False, (0.0, 0.0), 0.0, 0.0, None, 0.0, 0.0, None, 0.5)[3]
    y1 = IB.komut(ar["cx"], ar["cy"], ar["w"], ar["h"], 0.0, 18.0, 0.047,
                  c1, False, (0.0, 0.0), 0.0, 0.0, None, 0.0, 0.0, None, 0.5)[3]
    if abs((y1 - y0) - 0.20 * 0.5) > 1e-9:
        h.append("BURUN_KD olcegi: %.5f, beklenen %.5f" % (y1 - y0, 0.1))
    y2 = IB.komut(ar["cx"], ar["cy"], ar["w"], ar["h"], 0.0, 18.0, 0.047,
                  c1, False, (0.0, 0.0), 0.0, 0.0, None, 0.0, 0.0, None, -0.5)[3]
    if not (y2 < y0 < y1):
        h.append("BURUN_KD isaret simetrisi bozuk")
    b = Burun(ofs=20.0, ofs_ref=45.0)
    if not (b.ek(0.0, +0.5) > 0.0 > b.ek(0.0, -0.5)):
        h.append("ofset isareti kayma yonunde degil")
    if abs(b.ek(0.0, 10.0) - math.radians(20.0)) > 1e-3:
        h.append("ofset tavani %.3f deg" % math.degrees(b.ek(0.0, 10.0)))
    if abs(Burun(kp=0.3).ek(0.5, 0.0) - (-0.35)) > 1e-9:
        h.append("Kp eki yanlis: %.4f" % Burun(kp=0.3).ek(0.5, 0.0))
    print("  SINAMA (burun isaret/olcek): %s" %
          ("TAMAM (5/5)" if not h else "KALDI"))
    for x in h:
        print("    ! %s" % x)
    return h


# ══════════════════════════════════════════════════════════════════════════
#  PARTI / OZET
# ══════════════════════════════════════════════════════════════════════════
def _det(ad):
    return tezgah_b(**(DET_IYI if ad == "iyi" else DET_KOTU))


# (hata uretici, kayip_m) — ⚠ KAYIP_M TIK cinsindendir. Dongu hizini
# degistiren satirlarda kor zaman asimini SANIYE cinsinden SABIT tutmak
# icin olceklenir; yoksa "62 Hz faz omrunu 3'e boluyor" gibi SAHTE bir
# sonuc cikar (ilk kosuda tam da bu oldu).
HATALAR = {
    "tam": (lambda: HataAyari(), 20),
    "-yaw": (lambda: HataAyari.haric("yaw"), 20),
    "-gecikme": (lambda: HataAyari.haric("gecikme"), 20),
    "-kenar": (lambda: HataAyari.haric("kenar"), 20),
    "-yanlis": (lambda: HataAyari.haric("yanlis"), 20),
    "-dongu": (lambda: HataAyari.haric("dongu"), 58),
    "dongu30": (lambda: HataAyari(yasa_hz=30.0), 28),
    "dongu42": (lambda: HataAyari(yasa_hz=42.0), 39),
    "dongu62": (lambda: HataAyari(yasa_hz=62.0), 58),
    "hicbiri": (lambda: HataAyari.kapali(), 20),
    "hicbiri62": (lambda: HataAyari.kapali(), 58),
}


def parti(burun, grid, kayip_m=20, sure=20.0, hata_ad="tam"):
    r = []
    hf, kayip_m = HATALAR[hata_ad]
    for g in grid:
        r.append(kosu(burun=burun, hata=hf(), devir_m=g["devir_m"],
                      devir_aci=g["devir_aci"], dikey=g["dikey"],
                      hedef_yon=g["hedef_yon"], faz0=g["faz0"],
                      tohum=g["tohum"], dedektor=_det(g["det_ad"]),
                      kayip_m=kayip_m, sure=sure))
        r[-1]["_g"] = g
    return r


def ozet(r):
    if not r:
        return None
    # ⚠ ANGAJE ALT KUMESI: >=3 kutu gelmis fazlar. Burun yasasi ancak TAKIP
    # VARKEN is yapar; hic yakalanamamis hucreler (uzak devir + kotu tespit)
    # medyani doldurup kaldiraci gorunmez yapiyor. IKISI DE raporlanir.
    a = [x for x in r if x["n_kutu"] >= 3]
    return {
        "n": len(r), "a_n": len(a),
        "yakala": 100.0 * len(a) / len(r),
        "a_temas": _med([x["temas"] for x in a]) if a else float("nan"),
        "a_temas_ort": (sum(x["temas"] for x in a) / len(a)) if a else float("nan"),
        "a_eps50": _med([x["eps_p50"] for x in a]) if a else float("nan"),
        "a_eps90": _med([x["eps_p90"] for x in a]) if a else float("nan"),
        "a_eps39": 100.0 * _med([x["eps39"] for x in a]) if a else float("nan"),
        "a_yan": 100.0 * sum(1 for x in a if x["olum"] == "yan") / len(a) if a else float("nan"),
        "a_dikey": 100.0 * sum(1 for x in a if x["olum"] == "dikey") / len(a) if a else float("nan"),
        "a_omur": _med([x["omur"] for x in a]) if a else float("nan"),
        "a_iska": _med([x["iska_adil"] for x in a]) if a else float("nan"),
        "a_disari": 100.0 * sum(x["disari"] for x in a) / len(a) if a else float("nan"),
        "eps50": _med([x["eps_p50"] for x in r]),
        "eps90": _med([x["eps_p90"] for x in r]),
        "eps39": 100.0 * _med([x["eps39"] for x in r]),
        "yan": 100.0 * sum(1 for x in r if x["olum"] == "yan") / len(r),
        "dikey": 100.0 * sum(1 for x in r if x["olum"] == "dikey") / len(r),
        "ici": 100.0 * sum(1 for x in r if x["olum"] == "ici") / len(r),
        "omur": _med([x["omur"] for x in r]),
        "omur_p90": _p([x["omur"] for x in r], 90),
        "temas": _med([x["temas"] for x in r]),
        "temas_ort": sum(x["temas"] for x in r) / len(r),
        "iska": _med([x["iska_adil"] for x in r]),
        "iska_ham": _med([x["en_yakin"] for x in r]),
        "v3": 100.0 * sum(1 for x in r if x["iska_adil"] < 3.0) / len(r),
        "sur": 100.0 * _med([x["sureklilik"] for x in r
                             if x["sureklilik"] == x["sureklilik"]]),
        "lam": _med([x["lam_p50"] for x in r if x["lam_p50"] == x["lam_p50"]]),
        "doyum": 100.0 * _med([x["yaw_doyum"] for x in r]),
        "doyum_ort": 100.0 * sum(x["yaw_doyum"] for x in r) / len(r),
        "ayrim": _med([x["ayrim"] for x in r]),
        "yuks": _med([x["yukselis"] for x in r]),
        "vz": 100.0 * sum(x["vz_doyum"] for x in r) / len(r),
    }


BAS = ("  %-24s | %5s %5s %4s %4s %5s %5s %5s %5s %4s | %5s %5s %5s %4s" %
       ("burun yasasi", "eps50", "eps90", ">39", "yan%", "dis%", "omur",
        "temas", "iska", "doy%", "dik%", "ayrm", "yuks", "vz%"))
NOT = ("  (| solu = ANGAJE fazlar (>=3 kutu); sagi = dikey saglik, TUM grid;"
       " doy% = yaw tavani)")


def satir(ad, s):
    return ("  %-24s | %4.1fd %4.1fd %3.0f%% %3.0f%% %4.1f%% %4.2fs %4.2fs "
            "%4.1fm %3.0f%% | %4.1f%% %+4.1f %+4.1fd %3.0f%%" %
            (ad, s["a_eps50"], s["a_eps90"], s["a_eps39"], s["a_yan"],
             s["a_disari"], s["a_omur"], s["a_temas"], s["a_iska"],
             s["doyum_ort"], s["dikey"], s["ayrim"], s["yuks"], s["vz"]))


# ══════════════════════════════════════════════════════════════════════════
#  VARYANTLAR
# ══════════════════════════════════════════════════════════════════════════
def varyantlar():
    v = []
    v.append(Burun("1 MEVCUT P Kp1.0"))
    for kp in (0.2, 0.3, 0.5, 0.7):
        v.append(Burun("2 sessiz P Kp%.1f" % kp, kp=kp))
    for kp in (0.3, 0.5, 0.7, 1.0):
        for kd in (0.10, 0.20, 0.30, 0.45):
            v.append(Burun("3 PD %.1f/%.2f" % (kp, kd), kp=kp, kd=kd))
    for of in (10.0, 20.0, 35.0):
        for rf in (20.0, 45.0):
            v.append(Burun("4 ofs %.0f/%.0f" % (of, rf), ofs=of, ofs_ref=rf))
    for yr in (60.0, 180.0, 214.0):
        v.append(Burun("5 yaw %.0f" % yr, yawrate=yr))
    for kor in (0.25, 0.60, 1.50):
        v.append(Burun("6 kor burun %.2fs" % kor, kor=kor))
    return v


# ══════════════════════════════════════════════════════════════════════════
#  KOSTURMA (paralel)
# ══════════════════════════════════════════════════════════════════════════
_GRID = {}


def _isci(spec):
    spec = dict(spec)
    tk = spec.pop("tekrar")
    ha = spec.pop("hata_ad", "tam")
    if tk not in _GRID:                 # islem basina bir kez kurulur
        _GRID[tk] = saha(tk)
    b = Burun(**spec)
    r = parti(b, _GRID[tk], hata_ad=ha)
    dilim = {}
    for anahtar in ("kip", "devir_m", "devir_aci", "dikey", "det_ad"):
        d = {}
        for x in r:
            d.setdefault(x["_g"][anahtar], []).append(x)
        dilim[anahtar] = {k: ozet(v) for k, v in sorted(d.items(), key=lambda p: str(p[0]))}
    # ESLENMIS kiyas icin angajman-basi vektor (grid SIRASI korunur)
    esli = [(x["temas"], x["eps_p90"], 1.0 if x["olum"] == "yan" else 0.0,
             x["omur"], x["n_kutu"], x["eps39"]) for x in r]
    return spec["ad"], ozet(r), dilim, esli


def _spec(b):
    return dict(ad=b.ad, kp=b.kp, kd=b.kd, ofs=b.ofs, ofs_ref=b.ofs_ref,
                kor=b.kor, pencere=b.pencere, yawrate=b.yawrate,
                tau_y=b.tau_y, kp2=b.kp2, eps_c=b.eps_c, kahin=b.kahin)


TEKRAR = 2


def kostur(vs, isci=None):
    from concurrent.futures import ProcessPoolExecutor
    specs = [dict(_spec(b), tekrar=TEKRAR, hata_ad=getattr(b, "_h", "tam"))
             for b in vs]
    n = isci or min(os.cpu_count() or 4, 20)
    out = {}
    with ProcessPoolExecutor(max_workers=n) as ex:
        for ad, s, dil, esli in ex.map(_isci, specs):
            out[ad] = (s, dil, esli)
    return out


def esli_kiyas(out, ref_ad, adlar):
    """ESLENMIS kiyas: ayni senaryo + ayni tohum, varyant - referans.

    ⚠ Etkiler kucuk (%1-3). Eslenmemis medyan farki bu buyuklukte
    GURULTUDEN AYIRT EDILEMEZ; ayni angajmani ikisinde de kostugumuz icin
    fark VEKTORUNUN standart hatasi cok daha kucuk. t = ort/se.
    ⚠ YALNIZ ikisinde de angaje (>=3 kutu) olan angajmanlar sayilir.
    """
    r0 = out[ref_ad][2]
    print("  -- ESLENMIS FARK (varyant - referans), t = ort/se --")
    print("    %-24s %18s %18s %18s" %
          ("", "temas (s)", "|eps| p90 (deg)", "yandan cikis"))
    for ad in adlar:
        r1 = out[ad][2]
        d = [(b[0] - a[0], b[1] - a[1], b[2] - a[2])
             for a, b in zip(r0, r1) if a[4] >= 3 and b[4] >= 3]
        n = len(d)
        if n < 5:
            continue
        cik = []
        for j in range(3):
            v = [x[j] for x in d]
            m = sum(v) / n
            sd = (sum((x - m) ** 2 for x in v) / max(n - 1, 1)) ** 0.5
            se = sd / (n ** 0.5) if sd > 0 else 1e-12
            cik.append("%+7.3f (t%+5.1f)" % (m, m / se))
        print("    %-24s %s   n=%d" % (ad, " ".join(cik), n))
    print("    (|t| < 2 -> GURULTU. temas + iyi, eps90 - iyi, cikis - iyi)")
    print()


def _tablo(out, vs, baslik):
    print("  " + baslik)
    print(BAS)
    for b in vs:
        s = out[b.ad][0]
        print(satir(b.ad, s))
    print(NOT)
    print()


def _kirilim(out, adlar, anahtarlar=("kip", "devir_m", "devir_aci", "dikey",
                                     "det_ad")):
    for anahtar in anahtarlar:
        ks = list(out[adlar[0]][1][anahtar].keys())
        print("  == %s ==   (hucre: ANGAJE temas medyani / |eps| p90)" % anahtar)
        print("    %-22s %s" % ("", " ".join("%13s" % str(k) for k in ks)))
        for ad in adlar:
            d = out[ad][1][anahtar]
            print("    %-22s %s" % (ad, " ".join(
                ("%5.2fs/%4.1fd" % (d[k]["a_temas"], d[k]["a_eps90"])
                 if d[k] and d[k]["a_n"] else "        --   ")
                for k in ks)))
        print()


def esli_kirilim(out, ref_ad, adlar, anahtar="kip", tekrar=None):
    """ESLENMIS fark, SENARYO EKSENINE gore dilimlenmis.

    "Hangi senaryoda hangisi kazaniyor" sorusunun tek durust cevabi bu:
    toplamda kaybeden bir yasa tek bir kipte kazaniyor olabilir.
    """
    g = saha(tekrar or TEKRAR)
    ks = sorted({str(x[anahtar]) for x in g})
    r0 = out[ref_ad][2]
    print("  -- ESLENMIS FARK, %s ekseninde (temas s / t) --" % anahtar)
    print("    %-22s %s" % ("", " ".join("%16s" % k for k in ks)))
    for ad in adlar:
        r1 = out[ad][2]
        huc = []
        for k in ks:
            d = [b[0] - a[0] for x, a, b in zip(g, r0, r1)
                 if str(x[anahtar]) == k and a[4] >= 3 and b[4] >= 3]
            n = len(d)
            if n < 5:
                huc.append("%16s" % "--")
                continue
            m = sum(d) / n
            sd = (sum((v - m) ** 2 for v in d) / max(n - 1, 1)) ** 0.5
            t_ = m / (sd / n ** 0.5) if sd > 0 else 0.0
            huc.append("%16s" % ("%+6.3f (t%+5.1f)" % (m, t_)))
        print("    %-22s %s" % (ad, " ".join(huc)))
    print()


def senaryo(tekrar=6):
    """Kip bazinda ESLENMIS kiyas — tek kazanan var mi?"""
    global TEKRAR
    TEKRAR = tekrar
    vs = [Burun("MEVCUT P Kp1.0"),
          Burun("sessiz P Kp0.3", kp=0.3),
          Burun("sessiz P Kp0.5", kp=0.5),
          Burun("Kp 1.3", kp=1.3),
          Burun("PD 1.0/0.10", kd=0.10),
          Burun("ofs 10/45", ofs=10.0, ofs_ref=45.0),
          Burun("kor 0.10s", kor=0.10),
          Burun("yaw 60", yawrate=60.0),
          Burun("KAHIN (ust sinir)", kahin=True)]
    out = kostur(vs)
    _tablo(out, vs, "senaryo kirilimi icin taban")
    for a in ("kip", "devir_m", "det_ad"):
        esli_kirilim(out, vs[0].ad, [b.ad for b in vs[1:]], anahtar=a,
                     tekrar=tekrar)
    return out


def tavan(tekrar=6):
    """BURUN TAVANI NEREDEN GELIYOR — kaldirac yasada mi, GIRDIDE mi?

    Kahin burun (sifir olcum hatasi) referanstan belirgin iyi cikiyor, ama
    UYGULANABILIR hicbir yasa varyanti o farkin bir kismini bile almiyor.
    O halde acik KAZANCTA degil GIRDIDE. Bunu sinamak icin AYNI yasa
    (P, K_YAW=1.0) tek tek sondurulen olcum hatalariyla kosulur.
    """
    global TEKRAR
    TEKRAR = tekrar
    print("  -- BURUN TAVANI: ayni yasa (P Kp1.0), olcum hatalari TEK TEK "
          "sonduruluyor --")
    vs = [BurunH("tam hata (referans)", hata_ad="tam"),
          BurunH("- yaw hatasi", hata_ad="-yaw"),
          BurunH("- kutu gecikmesi", hata_ad="-gecikme"),
          BurunH("- kenar yanliligi", hata_ad="-kenar"),
          BurunH("- yanlis nesne", hata_ad="-yanlis"),
          BurunH("- dongu 62Hz (adil kor)", hata_ad="-dongu"),
          BurunH("dongu 30 Hz", hata_ad="dongu30"),
          BurunH("dongu 42 Hz", hata_ad="dongu42"),
          BurunH("hicbir olcum hatasi", hata_ad="hicbiri62"),
          BurunH("KAHIN (tam hata)", kahin=True, hata_ad="tam")]
    out = kostur(vs)
    _tablo(out, vs, "olcum hatasi ablasyonu")
    esli_kiyas(out, vs[0].ad, [b.ad for b in vs[1:]])
    return out


def main():
    ne = sys.argv[1] if len(sys.argv) > 1 else "hepsi"
    if ne == "tavan":
        tavan(int(sys.argv[2]) if len(sys.argv) > 2 else 6)
        return
    if ne == "senaryo":
        senaryo(int(sys.argv[2]) if len(sys.argv) > 2 else 6)
        return
    if ne == "final":
        final(int(sys.argv[2]) if len(sys.argv) > 2 else 6)
        return
    if ne in ("hepsi", "sinama"):
        sinama_gerileme()
        sinama_isaret()
        T.dogrula()
        print()
        if ne == "sinama":
            return
    g = saha(TEKRAR)
    print("  SAHA GRIDI: %d angajman/varyant" % len(g))
    print("  (4 menzil x 5 aspect x 3 dikey x 4 kip x 2 tespit x %d tekrar)"
          % TEKRAR)
    print()

    vs = varyantlar()
    out = kostur(vs)
    _tablo(out, vs, "-- 1) TEZGAH OLCULDUGU GIBI (yaw kanalinda tau YOK) --")
    ref = out[vs[0].ad][0]
    print("  yakalama orani (>=3 kutu): %%%.0f | referans yaw doyumu %%%.1f "
          "(saha %%23-47 -> TEZGAH BU EKSENDE SAGIR)"
          % (ref["yakala"], ref["doyum_ort"]))
    print()

    sira = sorted(out.items(),
                  key=lambda p: (-p[1][0]["a_temas_ort"], p[1][0]["a_eps90"]))
    adlar = [vs[0].ad] + [a for a, _ in sira[:5] if a != vs[0].ad][:4]
    _kirilim(out, adlar)

    # ── 2) VARSAYIMSAL YAW GECIKMESI (bkz. Burun.tau_y) ──────────────────
    print("  -- 2) HIPOTEZ: yaw kanali da 1. mertebe gecikseydi --")
    print("  !! tau_y OLCULMEMIS bir varsayim. Tezgahta yaw ~saf integrator")
    print("     oldugu icin turev teriminin telafi edecegi gecikme YOK;")
    print("     PD'nin sinanabilmesi icin gecikme VAR SAYILIYOR.")
    print()
    for ty in (0.10, 0.21):
        v2 = [Burun("L%.2f MEVCUT Kp1.0" % ty, tau_y=ty),
              Burun("L%.2f Kp0.5" % ty, kp=0.5, tau_y=ty),
              Burun("L%.2f PD 1.0/0.10" % ty, kd=0.10, tau_y=ty),
              Burun("L%.2f PD 1.0/0.20" % ty, kd=0.20, tau_y=ty),
              Burun("L%.2f PD 1.0/0.30" % ty, kd=0.30, tau_y=ty),
              Burun("L%.2f PD 0.7/0.20" % ty, kp=0.7, kd=0.20, tau_y=ty),
              Burun("L%.2f PD 0.7/0.30" % ty, kp=0.7, kd=0.30, tau_y=ty),
              Burun("L%.2f PD 0.5/0.30" % ty, kp=0.5, kd=0.30, tau_y=ty),
              Burun("L%.2f ofs 20/45" % ty, ofs=20.0, ofs_ref=45.0, tau_y=ty),
              Burun("L%.2f kor 0.25s" % ty, kor=0.25, tau_y=ty)]
        o2 = kostur(v2)
        _tablo(o2, v2, "tau_y = %.2f s" % ty)

    # ── 3) UCURUM ARAMASI: en iyi adaylarin uc degerleri ────────────────
    print("  -- 3) UCURUM (yayla mi, tepe mi?) --")
    v3 = [Burun("Kp %.2f" % kp, kp=kp) for kp in
          (0.1, 0.2, 0.3, 0.5, 0.7, 1.0, 1.3, 1.6, 2.0)]
    o3 = kostur(v3)
    _tablo(o3, v3, "saf P kazanci yaylasi")
    v4 = [Burun("Kd %.2f" % kd, kd=kd) for kd in
          (0.0, 0.05, 0.10, 0.20, 0.30, 0.45, 0.70)]
    o4 = kostur(v4)
    _tablo(o4, v4, "Kp=1.0 sabit, Kd yaylasi")
    v5 = [Burun("yaw %.0f" % yr, yawrate=yr) for yr in
          (40.0, 60.0, 90.0, 120.0, 180.0, 214.0)]
    o5 = kostur(v5)
    _tablo(o5, v5, "yaw hiz siniri yaylasi")
    v6 = [Burun("kor %.2fs" % k, kor=k) for k in
          (0.0, 0.10, 0.20, 0.25, 0.35, 0.50, 1.00)]
    o6 = kostur(v6)
    _tablo(o6, v6, "kor burun surdurme yaylasi")
    v7 = [Burun("pencere %.2fs" % p, kd=0.20, pencere=p) for p in
          (0.15, 0.20, 0.30, 0.45, 0.60)]
    o7 = kostur(v7)
    _tablo(o7, v7, "eps_hizi penceresi (Kd=0.20)")

    # ── 4) SERT REJIM: burun GERCEKTEN doyuyor ──────────────────────────
    # Tezgahin varsayilaninda yaw doyumu ~%5, sahada %23-47. Yani "doymus
    # hiz sinirlayici faz gecikmesi katar, D terimi onu kurtarir" iddiasi
    # tezgahin varsayilaninda SINANAMIYOR. Burun tavani 40/60 °/s'ye
    # cekilerek doyum REJIMI kurulur ve ayni kaldiraclar orada sinanir.
    print("  -- 4) SERT REJIM: yaw tavani kisilarak DOYUM uretiliyor --")
    for yr in (40.0, 60.0):
        v8 = [Burun("S%.0f MEVCUT Kp1.0" % yr, yawrate=yr),
              Burun("S%.0f Kp0.5" % yr, kp=0.5, yawrate=yr),
              Burun("S%.0f Kp1.6" % yr, kp=1.6, yawrate=yr),
              Burun("S%.0f PD 1.0/0.10" % yr, kd=0.10, yawrate=yr),
              Burun("S%.0f PD 1.0/0.20" % yr, kd=0.20, yawrate=yr),
              Burun("S%.0f PD 1.0/0.30" % yr, kd=0.30, yawrate=yr),
              Burun("S%.0f PD 0.7/0.20" % yr, kp=0.7, kd=0.20, yawrate=yr),
              Burun("S%.0f ofs 20/45" % yr, ofs=20.0, ofs_ref=45.0, yawrate=yr),
              Burun("S%.0f kor 0.20s" % yr, kor=0.20, yawrate=yr),
              Burun("S%.0f cizelge 1->1.6" % yr, kp2=1.6, yawrate=yr)]
        o8 = kostur(v8)
        _tablo(o8, v8, "yaw tavani %.0f deg/s" % yr)

    # ── 5) KAZANC CIZELGESI (kendi fikrim) ──────────────────────────────
    print("  -- 5) KURTARMA KAZANCI (merkezde sakin, kenarda sert) --")
    v9 = [Burun("cizelge yok (Kp1.0)"),
          Burun("Kp1.6 sabit", kp=1.6),
          Burun("1.0 -> 1.6 @25d", kp2=1.6, eps_c=25.0),
          Burun("1.0 -> 2.0 @25d", kp2=2.0, eps_c=25.0),
          Burun("1.0 -> 2.5 @25d", kp2=2.5, eps_c=25.0),
          Burun("1.0 -> 2.0 @15d", kp2=2.0, eps_c=15.0),
          Burun("1.0 -> 2.0 @35d", kp2=2.0, eps_c=35.0),
          Burun("0.7 -> 2.0 @25d", kp=0.7, kp2=2.0, eps_c=25.0)]
    o9 = kostur(v9)
    _tablo(o9, v9, "kazanc cizelgesi")


def final(tekrar=6):
    """FINALISTLER, buyuk orneklem (gurultuyu kucultmek icin)."""
    global TEKRAR
    TEKRAR = tekrar
    g = saha(tekrar)
    print("  -- FINAL: %d angajman/varyant --" % len(g))
    vs = [Burun("MEVCUT P Kp1.0"),
          Burun("KAHIN (ust sinir)", kahin=True),
          Burun("sessiz P Kp0.3", kp=0.3),
          Burun("sessiz P Kp0.5", kp=0.5),
          Burun("Kp 1.3", kp=1.3),
          Burun("Kp 1.6", kp=1.6),
          Burun("cizelge 1.0->2.0@25d", kp2=2.0, eps_c=25.0),
          Burun("PD 1.0/0.10", kd=0.10),
          Burun("PD 0.5/0.20", kp=0.5, kd=0.20),
          Burun("ofs 10/45", ofs=10.0, ofs_ref=45.0),
          Burun("kor 0.10s", kor=0.10),
          Burun("yaw 60", yawrate=60.0),
          Burun("yaw 180", yawrate=180.0)]
    out = kostur(vs)
    _tablo(out, vs, "TAM GRID")
    esli_kiyas(out, vs[0].ad, [b.ad for b in vs[1:]])
    _kirilim(out, [b.ad for b in vs[:6]])
    return out


if __name__ == "__main__":
    main()

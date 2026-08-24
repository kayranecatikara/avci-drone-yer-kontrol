# -*- coding: utf-8 -*-
"""
================================================================================
  TRAIL-HOLD  --  ARKADAN TAKIP + HIZ ESLEME  (cevrimdisi tezgah)
================================================================================
AMAC
--------------------------------------------------------------------------------
Bugunku sistem hedefi YANDAN kesiyor: carpisma rotasi icin gereken onalma 43°,
GPS kosusunda kurs hatasi medyan 16.8° -> kerteriz yaklasma boyunca 103°
supuruyor, 8 m'de 50-100 °/s'e ciciyor, hedef 0.5-2.1 s icinde 61°'lik
yari-HFOV'u gecip kadrajdan CIKIYOR.

ISTENEN BASKA BIR SEY: hedefin ARKASINA gecip HIZINA ESLESMEK ve 7-10 m
arkasinda ASILI KALMAK. Orada kerteriz hizi ~0 olur, hedef kadrajin ortasinda
sabit durur, sartname kiliti (5 s) birikir.

⚠ BU DOSYA YALNIZ sim/ ALTINDADIR. Oyun/yasa/kopru kodu DEGISTIRILMEDI.
   tesis.py hic elden gecmedi; kutu olcegi ve boyut gurultusu burada,
   tesis.kadraj()'in CIKISINA uygulanan bir SARMAL ile duzeltiliyor.

================================================================================
 ⚠ TEZGAH KUSURLARI — bu dosya UC yeni tanesini duzeltir
================================================================================
Tezgah gecmiste UC sahte bulgu uretti (isaretli roll, yanlis odak uzunlugu,
ters dikey isaret). Trail-hold sorusunu sormadan once tezgahin kendi olcum
zincirini yeniden denetledim; UC yeni kusur daha cikti ve ucu de tam bu
gorevin cevabini bozacak yerdeydi:

(4) KUTU YUKSEKLIGI 2.23 KAT KUCUK.  tesis.kadraj: h = F*1.10*0.30/R
    ("ince govde", TAHMIN).  OLCULEN (arac/menzil_model.py, 1788 tespitli
    kare / 93 kosu, truth menzille eslenmis):
        R * sqrt(w*h)          = 202.6 px*m
        R * w^0.15 * h^0.85    = 142.6 px*m
    Bu ikisi w ve h'yi TEK BASINA cozer:  w/h = 2.728,
        R*w = 334.6 px*m   (tesis 296.5 -> 1.128x kucuk)
        R*h = 122.7 px*m   (tesis  55.0 -> 2.231x kucuk)
    NEDEN OLDURUCU: sartname kiliti bir KUTU BOYUTU olcutudur
    (max(w/1920, h/1080) >= 0.06). Tesis kutusuyla esik R <= 8.21 m,
    OLCULEN kutuyla R <= 9.26 m cikar. R_set secimi dogrudan bu sayidir.

(5) KUTU BOYUTUNDA GURULTU YOK.  HataAyari.jitter_px yalniz cx,cy'ye
    biniyor; w,h TERTEMIZ. Yani menzil ve menzil-hizi tezgahta KUSURSUZ
    olcuuluyor -> "menzil+menzil-hizi denetimi" (yaklasim b) sahte sekilde
    parlar. OLCULEN gercek: menzil modelinin kalan sacilimi std(log)=0.147
    (tek kare), korelasyon suresi ~0.3 s.  Bu dosya OU (Ornstein-Uhlenbeck)
    bir log-olcek gurultusu ekler ve OLCULEN sonucu yeniden uretir:
        sigma(Vc) = 0.24 * R  m/s   (0.8 s pencere, egim gurultusu 0.239 1/s)
    -> R=8 m'de +-1.9 m/s. Trail-hold'da gercek kapanma 0-3 m/s. SNR<1.
    ⚠ Yani "kutu buyumesinden kapanma hizi" TRAIL-HOLD'DA KULLANILAMAZ
    (arac/menzil_model.py UYARI 3 bunu bagimsiz olarak yaziyor).

(6) SARTNAME KILIDI HIC OLCULMEMISTI.  Tezgahin butun olcutleri "en yakin
    menzil" idi; oysa gorev "5 s kilit". Burada GERCEK sayac import edilip
    (guidance/kilit_sayaci.py, DEGISTIRILMEDEN) besleniyor.

================================================================================
 KADRAJ / KILIT GEOMETRISI (turetildi, sabit degil)
================================================================================
Yasa cercevesi 640x480 F=166.6; GERCEK kadraj 1920x1080 fx=531.36.
Aci korunur: tx=(cx-320)/166.6 her ikisinde de aynidir.
    cxn = 0.5 + tx*531.36/1920 = 0.5 + tx*0.27675
    cyn = 0.5 + ty*531.36/1080 = 0.5 + ty*0.49200
Sartname (kilit_sayaci.KilitCfg, DEGISTIRILMEZ):
    0.25 <= cxn <= 0.75   ->  |tx| <= 0.9033   (|eps_yaw| <= 42.1°)
    0.10 <= cyn <= 0.90   ->  |ty| <= 0.8130   (kamera ekseninden 39.1°)
    max(w/1920, h/1080) >= 0.06
    10 s pencerede kumulatif >= 5 s
KAMERA 25° YUKARI vidali. Hedef AYNI irtifadaysa ty = tan(25°) = 0.466.
    * hedefin USTUNDE ucmak OLDURUCU: R=8 m'de 2.80 m'den fazla yukarida
      olursak ty > TY_MAX -> hedef kadrajin ALTINDAN cikar.
    * ALTINDA ucmak serbest: 7.5 m'ye kadar iceride kalir.
    * ty = 0 (dikey tam merkez) kosulu:  dz_alt = R*sin(25°) = 0.423*R.
      R_set=8 m icin 3.38 m ALTTA, yatayda 7.25 m geride.
================================================================================
 SONUC — KAZANAN DENETLEYICI (tezgahta OLCULDU, 120 kosu/yapilandirma)
================================================================================
(c) KERTERIZ-KILITLI TRAIL  --  hedefin IZINI takip et, hizina ESLES.

  u_T  : hedef birim hiz yonu (kestirim)   n_T = sol normal
  V    : hedef surati = 17.98 m/s (OLCULEN SABIT, GPS fazindan devralinir)
  om   : hedefin donus hizi (kestirim)     d_set = sqrt(R_set^2 - dz^2)
  s    = -(p - p_T) . u_T                              (yaklasik geri mesafe)
  Dpsi = clamp(om * s / V, +-1.2 rad)                  (yol yonu farki)
  u_p  = cos(Dpsi)*u_T - sin(Dpsi)*n_T                 (IZDUSUMDEKI teget)
  n_p  = sol_normal(u_p)
  p_st = p_T - (V/om) sin(om d_set/V) u_T + (V/om)(1-cos(om d_set/V)) n_T
  e    = p_st - p ;  e_par = e.u_p ;  e_yan = clamp(K_dik*(e.n_p), +-15 m/s)
  ---------------------------------------------------------------------------
  v_yatay = V*u_p  +  K_par*e_par*u_p  +  e_yan*n_p
  v_dikey = K_z*R_set*( u_z - min(sin 25deg, DZ_TAVAN/R) )  + clamp(vT_z,+-2)
  yaw     = atan2(u_y, u_x) + T_lead * om_LOS
  ---------------------------------------------------------------------------
  Komut, hiz vektorune DIK bileseni A_YAN_MAX*tau, PARALEL bileseni
  A_ILERI_MAX*tau ile kisilarak uygulanir (tau = 0.211 s OLCULDU).

ONERILEN KAZANCLAR (tarandi)
  R_set     6.0 m (slant)   -> yatay 5.4 m geri + 2.54 m alt
  K_par     0.9  (m/s)/m    K_dik   1.6  (m/s)/m   (yanal terim tavani 15 m/s)
  K_z       1.0             DZ_TAVAN 4.0 m         T_lead  0.20 s
  v_max     22-24 m/s       A_YAN_MAX = A_ILERI_MAX = MAX_ACCEL = 12 m/s^2
  Kestirim: radyal alfa/beta 0.16/0.006 | teget 0.60/0.045 | soguk baslangic
            1.2 s en-kucuk-kareler | kapi radyal max(2 m, 0.45R), teget
            max(1 m, 0.22R) | omega EMA 0.4 s (esgudumlu donus ongorusu)

OLCULEN BASARI (gercekci olcum hatasi, n=120: 4 senaryo x 3 devir acisi x 10)
  5 s KESINTISIZ kilit   %80.0        sartname sayaci (5 s / 10 s)   %82.5
  duz %86.7 | 20 deg/s donus %66.7 | dikey manevra %83.3 | olculen oval %83.3
  R_set'e ilk varis 5.4 s | oturunca menzil salinimi std 0.41 m
  hedefin kadraj merkezinden yatay sapmasi: medyan 2.2 deg, p95 10.3 deg
  (kadraj siniri 61 deg, sartname AV siniri 42.1 deg)
  Kiyas: (a) saf istasyon %0  |  (b) menzil+menzil-hizi %0-13  |  (c) %80

NEREDE BOZULUYOR
  * 40 deg/s hedef donusu: %0. FIZIKSEL: istasyon noktasi hedefle ayni yayda,
    a = V^2/r = 17.98^2/25.76 = 12.55 m/s^2 > MAX_ACCEL 12.0. %4.6 ile
    ULASILAMAZ. (20 deg/s icin gereken 6.28 m/s^2 -- rahat.)
  * 4 s'de bir isaret degistiren donus (s20): %0. omega kestirimi 0.4 s EMA
    ile her tersinmede ~0.8 s yanlis; istasyon noktasi savruluyor.
  * GPS devri BORDADAN sonra: aspect 90 deg -> %80, 135 deg -> %20,
    180 deg (karsidan) -> %0. Sure uzatmak DUZELTMIYOR (40/60/90 s ayni).
  * MAX_ACCEL 12 -> 8 m/s^2: %98 -> %52.   v_max 24 -> 19 (mu 0.95): %98 -> %72.
  * R_set 6 -> 7 m: %98 -> %58 (kesintisiz). Sebep kutu-boyut kilidi:
    esik 9.26 m ama kutu %15 (1-sigma) gurultulu; 5 s = 107 ardisik kare
    icin ~3 sigma pay lazim -> 9.26/e^(3*0.147) = 5.96 m.
  * Kestirim ablasyonu: tutumu ivmeden kestirmemek %98 -> %68;
    egrilik ileri-beslemesi kapali %98 -> %72; V_T sabiti yok %98 -> %88;
    ESKI (kalibre edilmemis) tesis kutusu %98 -> %22.
================================================================================
"""
import os
import sys
import math
import random
import argparse

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)

import tesis as T                                                # noqa: E402
from tesis import Avci, Olcum, kadraj, F_YASA, CX, CY, HataAyari, Algi  # noqa
from tesis import TX_MAX, TY_MAX, tespit_olasilik                # noqa: E402
from guidance.kilit_sayaci import KilitSayaci, KilitCfg          # noqa: E402


# ══════════════════════════════════════════════════════════════════════════
#  OLCULMUS SABITLER (bu dosyaya ozel — kaynak yorumda)
# ══════════════════════════════════════════════════════════════════════════
class Kal:
    """Kutu kalibrasyonu ve olcum gurultusu — HEPSI OLCULDU."""
    # arac/menzil_model.py: 1788 tespitli kare, aspect 138-166° (kuyruk takibi)
    K_SQRT = 202.6        # px*m ; R * sqrt(w*h)
    K_WH = 142.6          # px*m ; R * w^0.15 * h^0.85
    A_W, A_H = 0.15, 0.85
    # yukaridan cozulen tek-tek kutu olcekleri (bkz. dosya basi, kusur 4)
    W_OLCEK = 334.5993 / (F_YASA * Olcum.KANAT_ACIKLIGI)          # 1.1283
    H_OLCEK = 122.6744 / (F_YASA * Olcum.GOVDE_UZUNLUK * 0.30)    # 2.2313
    # kutu boyutu gurultusu (kusur 5): log-olcek OU sureci
    BOYUT_SIGMA = 0.147   # OLCULDU: std(log R*boyut), tek kare
    BOYUT_TAU = 0.30      # s ; OLCULDU: "kutunun 0.3 s korelasyon sureli"
    # DoW kadraj olcekleri
    DOW_F = (1920.0 / 2.0) / math.tan(math.radians(Olcum.HFOV / 2.0))   # 531.36
    KX = DOW_F / F_YASA / 1920.0          # tx -> cxn kesri (0.27675)
    KY = DOW_F / F_YASA / 1080.0          # ty -> cyn kesri (0.49200)
    KW = DOW_F / F_YASA / 1920.0          # w_yasa -> w/W
    KH = DOW_F / F_YASA / 1080.0          # h_yasa -> h/H


def kilit_esik_menzil(olcek=True):
    """Sartname kutu-boyut olcutunun izin verdigi EN BUYUK menzil (kuyruk)."""
    w1 = F_YASA * Olcum.KANAT_ACIKLIGI * (Kal.W_OLCEK if olcek else 1.0)
    h1 = F_YASA * Olcum.GOVDE_UZUNLUK * 0.30 * (Kal.H_OLCEK if olcek else 1.0)
    return max(w1 * Kal.KW, h1 * Kal.KH) / KilitCfg.LOCK_PCT


# ══════════════════════════════════════════════════════════════════════════
#  KUTU SARMALI — tesis.kadraj cikisini OLCULEN kalibrasyona getirir
# ══════════════════════════════════════════════════════════════════════════
class Kutu:
    """tesis.kadraj()'i sarar: olcek duzeltmesi + OLCULEN boyut gurultusu.

    ⚠ tesis.py'ye DOKUNULMADI. Duzeltme burada, cikista.
    olcek=False  -> eski tesis kutusu (gerileme kiyasi icin)
    gurultu=False-> boyut gurultusu kapali (tezgahin eski hali)
    """

    def __init__(self, tohum=0, olcek=True, gurultu=True):
        self.rnd = random.Random(tohum * 7919 + 13)
        self.olcek = olcek
        self.gurultu = gurultu
        self.n = 0.0                       # OU durumu (log-olcek)

    def __call__(self, av, hx, hy, hz, dt):
        # OU: dn = -n/tau*dt + sigma*sqrt(2*dt/tau)*N(0,1)
        if self.gurultu and Kal.BOYUT_TAU > 0.0:
            a = dt / Kal.BOYUT_TAU
            self.n += -self.n * a + Kal.BOYUT_SIGMA * math.sqrt(
                max(2.0 * a, 0.0)) * self.rnd.gauss(0.0, 1.0)
        k = kadraj(av, hx, hy, hz)
        if k is None:
            return None
        cx, cy, w, h, menzil = k
        if self.olcek:
            w *= Kal.W_OLCEK
            h *= Kal.H_OLCEK
        if self.gurultu:
            g = math.exp(self.n)
            w *= g
            h *= g
        return cx, cy, max(w, 1.0), max(h, 1.0), menzil


# ══════════════════════════════════════════════════════════════════════════
#  HEDEF YOLU — sabit hiz, senaryoya gore manevra
# ══════════════════════════════════════════════════════════════════════════
class HedefYol:
    """Sabit 17.98 m/s. Donus hizi ve tirmanma senaryo ile verilir.

    ⚠ Hiz SABIT tutulur (24682 ornekli truth kaydiyla dogrulandi); manevra
    yalnizca YON degistirir.
    """
    SENARYOLAR = ("duz", "donus20", "donus40", "s20", "dikey", "oval")

    def __init__(self, senaryo="duz", x=0.0, y=0.0, z=None, hdg=0.0):
        if senaryo not in self.SENARYOLAR:
            raise KeyError("bilinmeyen senaryo: %r" % senaryo)
        self.senaryo = senaryo
        self.x, self.y = x, y
        self.z = Olcum.HEDEF_IRTIFA if z is None else z
        self.hdg = hdg
        self.t = 0.0
        self.v = Olcum.HEDEF_HIZ
        self._oval = T.Hedef(faz0=0.0) if senaryo == "oval" else None
        if self._oval is not None:
            self._oval.z = self.z

    def _omega_vz(self):
        """(donus hizi rad/s, tirmanma m/s) — senaryo tanimi."""
        s, t = self.senaryo, self.t
        if s == "duz":
            return 0.0, 0.0
        if s == "donus20":
            return math.radians(20.0), 0.0
        if s == "donus40":
            return math.radians(40.0), 0.0
        if s == "s20":                       # 4 s'de bir isaret degistirir
            return math.radians(20.0) * (1.0 if int(t / 4.0) % 2 == 0 else -1.0), 0.0
        if s == "dikey":                     # +-2 m/s, 8 s periyot
            return 0.0, 2.0 * math.sin(2.0 * math.pi * t / 8.0)
        return 0.0, 0.0

    def adim(self, dt):
        if self._oval is not None:
            self._oval.adim(dt)
            self.t += dt
            return
        om, vz = self._omega_vz()
        self.hdg += om * dt
        # sabit YER hizi: yatay bilesen tirmanma ile kucultulmez (Talon
        # olculen 17.98 m/s YATAY hiz; dikey oynama ayri kanal).
        self.x += self.v * math.cos(self.hdg) * dt
        self.y += self.v * math.sin(self.hdg) * dt
        self.z += vz * dt
        self.t += dt

    def durum(self):
        if self._oval is not None:
            return self._oval.durum()
        om, vz = self._omega_vz()
        return (self.x, self.y, self.z,
                self.v * math.cos(self.hdg), self.v * math.sin(self.hdg), vz)

    def donus_deg(self):
        if self._oval is not None:
            return self._oval.donus_hizi_deg()
        return math.degrees(self._omega_vz()[0])


# ══════════════════════════════════════════════════════════════════════════
#  GORUS HATTI — piksel + tutum -> DUNYA birim vektoru
# ══════════════════════════════════════════════════════════════════════════
def los_dunya(tx, ty, yaw, pitch, roll, tilt_deg=None):
    """kadraj() zincirinin TAM TERSI. Doner: (ex, ey, ez), ez YUKARI.

    ⚠ Bu fonksiyon tezgahin en kirilgan yeri: kadraj()'daki her donusun
    tersi AYNI SIRADA alinmali. dogrula_trail() 3. sinamasi bunu rastgele
    tutumlarda truth'a karsi olcer (tezgahin isaret hatasi gecmisi var).
    """
    t = math.radians(Olcum.TILT if tilt_deg is None else tilt_deg)
    tc, ts = math.cos(t), math.sin(t)
    kf, r3, kd = 1.0, tx, ty                  # kamera cercevesi (ileri,sag,asagi)
    # 4) tilt geri
    f2 = kf * tc + kd * ts
    d3 = -kf * ts + kd * tc
    # 3) roll geri
    rc, rs = math.cos(roll), math.sin(roll)
    r2 = r3 * rc - d3 * rs
    d2 = r3 * rs + d3 * rc
    # 2) pitch geri
    pc, ps = math.cos(pitch), math.sin(pitch)
    f1 = f2 * pc + d2 * ps
    d1 = -f2 * ps + d2 * pc
    # 1) yaw geri
    c, s = math.cos(yaw), math.sin(yaw)
    dx = f1 * c - r2 * s
    dy = f1 * s + r2 * c
    dz = -d1                                   # d asagi idi -> yukari
    n = math.sqrt(dx * dx + dy * dy + dz * dz)
    return dx / n, dy / n, dz / n


def _sar(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


# ══════════════════════════════════════════════════════════════════════════
#  KESTIRIM — kutu + (bayat) telemetri -> hedef durumu
# ══════════════════════════════════════════════════════════════════════════
class Kestirim:
    """Denetleyicilerin GORDUGU tek sey. GPS/truth YOK.

    Girdiler (hepsi OLCUM):
        kutu (cx,cy,w,h)  : ~63 ms yasli (OLCULDU)
        iris_yaw/roll/pitch: BAYAT (tiklerin %59'u; yas p95 2.3 s, max 7.5 s)
        jiroskop yaw hizi : TAZE (ayri kanal, bias/gurultu eklendi)
        kendi hizi/konumu : TAZE (SDK v_yas p90 0.031 s — OLCULDU)

    Ciktilar: R, Rdot, LOS birim vektoru, hedef konum/hiz kestirimi.
    """
    YAS_NOM = 0.063          # s ; OLCULEN ortalama kutu yasi (dogrula #8)

    def __init__(self, tohum=0, tutum_modeli=True, vt_sabit=None,
                 jiro_bias_deg=0.5, jiro_gurultu_deg=1.0,
                 alfa=0.16, beta=0.006, alfa_t=0.60, beta_t=0.045,
                 pencere_s=0.80, yas_nom=None, ilk_s=1.2,
                 kapi_m=2.0, kapi_oran=0.45, kapi_max=12,
                 kapi_t_m=1.0, kapi_t_oran=0.22):
        rnd = random.Random(tohum * 104729 + 7)
        self.rnd = rnd
        # ⚠ KUTU YASI TELAFISI. 63 ms x 18 m/s = 1.13 m. Telafi edilmezse
        # menzil kestirimi TAM O KADAR yanli cikar ve trail 1.1 m GERIDE
        # oturur (dogrula_trail #6 bunu yakaliyor). Yas OLCULEN bir boru
        # hatti sabitidir (kare 17 ms + cikarim 23 ms + yarim kamera
        # periyodu 23 ms), yani yasa da bilebilir.
        if yas_nom is not None:
            self.YAS_NOM = yas_nom
        self.bias = math.radians(rnd.gauss(0.0, jiro_bias_deg))
        self.jg = math.radians(jiro_gurultu_deg)
        self.tutum_modeli = tutum_modeli
        self.vt_sabit = vt_sabit
        self.alfa, self.beta = alfa, beta          # RADYAL (menzil) kanali
        self.alfa_t, self.beta_t = alfa_t, beta_t  # TEGET (kerteriz) kanali
        self.pencere = pencere_s
        self.ilk_s = ilk_s
        self.ilk = []                              # soguk baslangic tamponu
        # ⚠ OLCUM KAPISI (innovation gating) — OLMAZSA OLMAZ.
        # "YANLIS NESNE" olayi OLCULDU: 0.085 1/s hizla kutu 153 px sicriyor
        # (0.4 s). 153 px = atan(153/166.6) = 42.6° kerteriz sicramasi;
        # 8 m'de 5.4 m yanal konum hatasi demek. Kapi olmadan alfa-beta
        # suzgecinin HIZ durumu tek karede birkac m/s savruluyor, hedef
        # kadrajdan cikiyor ve bir daha DONMUYOR (kosu 1: menzil 326 m).
        self.kapi_m, self.kapi_oran, self.kapi_max = kapi_m, kapi_oran, kapi_max
        self.kapi_t_m, self.kapi_t_oran = kapi_t_m, kapi_t_oran
        self.red = 0
        self.red_top = 0
        self.k = 0                      # kabul edilen olcum sayisi
        self.yaw_hat = None
        self._son_yaw_olc = None
        self.roll_hat = self.pitch_hat = 0.0
        self._v_onc = None
        self._a_ema = (0.0, 0.0)
        self._b_roll = self._b_pitch = 0.0
        self._tut = []                  # (t, yaw, roll, pitch) gecmisi
        self.u_ham = (1.0, 0.0, 0.0)    # son OLCUMUN LOS'u (suzulmemis)
        self.R1 = None                  # 1B menzil suzgeci
        self.c1 = 0.0                   # hedefin LOS boyunca hiz bileseni
        self.Rdot1 = 0.0
        self.R_ham = None
        self.pT = None                  # hedef konum kestirimi (dunya)
        self.vT = None                  # hedef hiz kestirimi (dunya)
        self.R = None
        self.Rdot_kutu = 0.0            # kutu buyumesinden (GURULTULU)
        self.Rdot = 0.0                 # kinematik (ONERILEN)
        self.u = (1.0, 0.0, 0.0)
        self.hazir = False
        self.gec = []                   # (t, log boyut) — egim penceresi
        self.omega = 0.0                # hedef donus hizi kestirimi (rad/s)
        self.om_los = 0.0               # LOS acisal hizi (yatay, rad/s)
        self._hdg_o = None
        self.yas_s = 0.0

    # ---- tutum ----
    def _tutum(self, t, dt, yaw_olc, roll_olc, pitch_olc, jiro, a_yan_cmd, v_oz):
        if self.yaw_hat is None:
            self.yaw_hat = yaw_olc
            self._son_yaw_olc = yaw_olc
        g = jiro + self.bias + self.rnd.gauss(0.0, self.jg)
        self.yaw_hat = _sar(self.yaw_hat + g * dt)
        taze = (self._son_yaw_olc is None
                or abs(_sar(yaw_olc - self._son_yaw_olc)) > 1e-12)
        if taze:
            self._son_yaw_olc = yaw_olc
            # taze ornek 20 ms yasli (OLCULEN SDK tasima gecikmesi)
            self.yaw_hat = _sar(self.yaw_hat + 0.35 * _sar(
                yaw_olc + g * 0.020 - self.yaw_hat))
        if not self.tutum_modeli:
            self.roll_hat, self.pitch_hat = roll_olc, pitch_olc
            return
        # ══ ROLL/PITCH: OZ IVMEDEN, BAYAT OLCUMDEN DEGIL ══════════════════
        # ⚠ roll/pitch ATTITUDE mesajinda yaw ile AYNI kutuda gelir; yaw
        # donunca (tiklerin %59'u, p95 2.3 s) onlar da DONAR.
        # ⚠⚠ ILK DENEMEM "roll'u KOMUT ivmesinden kestir" idi ve OLCTUM:
        # hata std 15°, p95 34°. Sebep: komut ANLIK, arac 0.046 s olu zaman
        # + 0.211 s tau ile cevap veriyor; hizli yatis terslerinde kestirim
        # aracin 46 ms ONUNDE. Bu hata dogrudan LOS AZIMUTUNA sizar
        # (kayma ~ ty * roll_hatasi) ve KAPALI DONGU limit cevrimi kurar:
        # roll hatasi -> kerteriz hatasi -> yanal komut -> daha buyuk roll.
        # Olculen sonuc: ±33° roll, ±0.65 tx, ~1 Hz — hedef kadrajdan cikiyor.
        # DOGRUSU: cok-pervaneli aracta itki vektoru = a + g, yani tutum
        # KENDI IVMEMIZDEN cikar. Ivme, TAZE hiz telemetrisinin (v_yas p90
        # 0.031 s — OLCULDU) turevidir; komuttan degil OLCUMDEN gelir.
        # Model hatasi (ve montaj ofseti) icin bayat olcumle YAVAS bir bias
        # kestirimi tutulur — donmadan etkilenmez, cunku yalniz taze
        # orneklerde guncellenir.
        if self._v_onc is not None and dt > 1e-6:
            ax = (v_oz[0] - self._v_onc[0]) / dt
            ay = (v_oz[1] - self._v_onc[1]) / dt
            k = min(1.0, dt / 0.06)
            self._a_ema = (self._a_ema[0] + k * (ax - self._a_ema[0]),
                           self._a_ema[1] + k * (ay - self._a_ema[1]))
        self._v_onc = (v_oz[0], v_oz[1])
        s = math.hypot(v_oz[0], v_oz[1])
        if s > 0.5:
            ux, uy = v_oz[0] / s, v_oz[1] / s
            a_dik = self._a_ema[0] * (-uy) + self._a_ema[1] * ux
            a_ile = self._a_ema[0] * ux + self._a_ema[1] * uy
        else:
            a_dik = a_ile = 0.0
        roll_m = math.atan2(a_dik, 9.81)
        pitch_m = -math.atan2(a_ile, 9.81)
        # Ofset TAZE ornekte hizli duzeltilir (olcum + model FARKI semasi):
        # donma boyunca modelin ARTISI tasir, taze gelince olcume oturur.
        if taze:
            self._b_roll += 0.70 * _sar(roll_olc - roll_m - self._b_roll)
            self._b_pitch += 0.70 * _sar(pitch_olc - pitch_m - self._b_pitch)
        self.roll_hat = roll_m + self._b_roll
        self.pitch_hat = pitch_m + self._b_pitch
        # ⚠⚠ TUTUM GECMISI: kutu t-yas aninda yakalandi; LOS o ANIN
        # tutumuyla kurulmali. tesis.py'nin belgeledigi ariza kipi tam bu:
        # "LOS_yasa = iris_yaw(SIMDI) + eps(GECMIS)" -> sahte LOS hizi,
        # sahada lam 7 KAT sisiyor. Burada 63 ms'lik kutu yasi ve limit
        # cevrimindeki 100-200 °/s yaw hizi 6-13°'lik azimut hatasi
        # uretiyordu — kapali dongude yeterli.
        self._tut.append((t, self.yaw_hat, self.roll_hat, self.pitch_hat))
        while len(self._tut) > 2 and self._tut[1][0] < t - self.YAS_NOM - 0.05:
            self._tut.pop(0)

    def _tutum_gec(self, ts):
        """Yakalama anindaki (yaw, roll, pitch) — dogrusal interpolasyon."""
        g = self._tut
        if not g:
            return self.yaw_hat, self.roll_hat, self.pitch_hat
        if ts <= g[0][0]:
            return g[0][1], g[0][2], g[0][3]
        for i in range(len(g) - 1):
            t0, t1 = g[i][0], g[i + 1][0]
            if t0 <= ts <= t1:
                o = 0.0 if t1 - t0 < 1e-12 else (ts - t0) / (t1 - t0)
                return (g[i][1] + o * _sar(g[i + 1][1] - g[i][1]),
                        g[i][2] + o * (g[i + 1][2] - g[i][2]),
                        g[i][3] + o * (g[i + 1][3] - g[i][3]))
        return g[-1][1], g[-1][2], g[-1][3]

    def guncelle(self, t, dt, kutu, yaw_olc, roll_olc, pitch_olc, jiro,
                 p_oz, v_oz, a_yan_cmd=0.0, yeni=True):
        """Bir yasa tiki. kutu None ya da yeni=False ise yalniz ONGORU.

        ⚠ `yeni` OLMAZSA OLMAZ. Yasa 21.3 Hz, kamera 21.3 Hz ve iki saat
        BAGIMSIZ; bazi tiklerde AYNI kutu ikinci kez okunur (sifirinci
        mertebe tutucu). Ayni olcumu tekrar fuzyonlamak alfa'yi carpar ve
        hiz durumunu geriye ceker: ilk surumde bu tek satir yuzunden
        "yalniz gecikme" ablasyonunda medyan menzil 8 m yerine 21 m
        cikiyordu — TEZGAH KUSURU, denetleyici kusuru degil.
        """
        self._tutum(t, dt, yaw_olc, roll_olc, pitch_olc, jiro, a_yan_cmd, v_oz)
        # ---- ongoru: EŞGUDUMLU DONUS modeli ----
        # ⚠ Sabit-hiz modeli donen hedefte YAPISAL olarak geride kalir:
        # alfa-beta suzgecinin ongorulen hiz hatasi a*(2*zeta/wn) = 6.3*0.63
        # = 4.0 m/s -> 12° yon hatasi (OLCULDU: 10-20°). Hedefin donusu
        # SABIT HIZLI oldugu icin (20.1 °/s, olculen oval) omega'yi ayri
        # kestirip hiz vektorunu ONGORUDE DONDURMEK bu hatayi buyuk olcude
        # kaldirir — klasik "coordinated turn" modeli.
        if self.pT is not None:
            if abs(self.omega) > 1e-6:
                a = self.omega * dt
                c, sn = math.cos(a), math.sin(a)
                self.vT = (self.vT[0] * c - self.vT[1] * sn,
                           self.vT[0] * sn + self.vT[1] * c, self.vT[2])
            self.pT = tuple(self.pT[i] + self.vT[i] * dt for i in range(3))
        if kutu is None or not yeni:
            if self.pT is not None:
                self._turet(p_oz, v_oz, dt)
            return
        cx, cy, w, h = kutu
        tx, ty = (cx - CX) / F_YASA, (cy - CY) / F_YASA
        yk, rk, pk = self._tutum_gec(t - self.YAS_NOM)   # YAKALAMA ani tutumu
        u = los_dunya(tx, ty, yk, pk, rk)
        self.u_ham = u
        # ---- menzil: OLCULEN model R = F*S_ETK/(w^0.15 h^0.85) ----
        R_ham = Kal.K_WH / (max(w, 1e-3) ** Kal.A_W * max(h, 1e-3) ** Kal.A_H)
        self.R_ham = R_ham
        # ── BAGIMSIZ 1B MENZIL SUZGECI (yaklasim b'nin tek ihtiyaci) ──────
        # Model: Rdot = c - v_oz.u ,  c = hedefin LOS boyunca hiz bileseni
        # (yavas degisir, [-20,20]). Kendi hizimiz TAZE ve TAM bilindigi
        # icin ongoru neredeyse hatasiz; suzgec yalniz c'yi ogrenir.
        # ⚠ Kutu buyumesinden dogrudan Rdot CIKMAZ: OLCULDU sigma = 0.24*R
        # m/s (0.8 s pencere) — trail-hold'da gercek kapanma 0-3 m/s, SNR<1
        # (arac/menzil_model.py UYARI 3).
        if self.R1 is None:
            self.R1, self.c1 = R_ham, 0.0
        else:
            i1 = R_ham - self.R1
            if abs(i1) < max(2.0, 0.60 * self.R1):
                self.R1 += 0.20 * i1
                self.c1 = max(-20.0, min(20.0, self.c1 + 0.010 / max(dt, 1e-3) * i1))
        # kutu buyume egimi (yalniz TANI/kiyas icin — bkz. kusur 5)
        b = math.log(max(w, 1e-3) ** Kal.A_W * max(h, 1e-3) ** Kal.A_H)
        self.gec.append((t, b))
        while self.gec and t - self.gec[0][0] > self.pencere:
            self.gec.pop(0)
        if len(self.gec) >= 4:
            n = len(self.gec)
            tm = sum(g[0] for g in self.gec) / n
            bm = sum(g[1] for g in self.gec) / n
            sxx = sum((g[0] - tm) ** 2 for g in self.gec)
            egim = (sum((g[0] - tm) * (g[1] - bm) for g in self.gec) / sxx
                    if sxx > 1e-12 else 0.0)
            self.Rdot_kutu = -R_ham * egim
        # ---- olcum: hedefin SIMDIKI konumu ------------------------------
        # ⚠ Kutu t-yas aninda yakalandi. O anki olcum hedefin t-yas'taki
        # konumunu verir; suzgec durumu ise t aninda. Dogru ileri tasima:
        #   z(t) = p_oz(t-yas) + R*u + v_T*yas = p_oz(t) + R*u + (v_T-v_oz)*yas
        # Ilk surumde son terim YOKTU: pT hedefin 17.98*0.063 = 1.13 m
        # GERISINE oturuyor, menzil o kadar EKSIK okunuyor ve trail 1-2 m
        # UZAKTA dengeleniyordu. BAGIL hiz ~0 oldugu icin dogru telafi
        # trail-hold'da SIFIRA yakinsar — yani "duzeltmemek" daha dogruydu.
        vt = self.vT if self.vT is not None else v_oz
        z = tuple(p_oz[i] + R_ham * u[i] + (vt[i] - v_oz[i]) * self.YAS_NOM
                  for i in range(3))
        # ══ SOGUK BASLANGIC: EN KUCUK KARELER PENCERESI ══════════════════
        # ⚠ Hedefin YONU tek kareden (hatta iki kareden) BILINEMEZ.
        #   * Ilk surum "hedef bizim gittigimiz yone gidiyor" varsayiyordu;
        #     GPS devri bordadan (aspect0=90°) olunca 90° yanlis oluyor,
        #     istasyon TERS tarafa konuyor, hedef bir daha goruinmuyordu.
        #   * Ikinci surum genisleyen bellek kazanci kullandi: k=2'de
        #     beta/dt = 21 -> 1 m'lik menzil gurultusu 21 m/s'lik hiz
        #     sicramasi uretti. Daha da kotu.
        #   * OLCULEN gurultu %15 menzilde: 47 ms tabanla hiz kestirimi
        #     ~30 m/s hatali olur. Fizik geregi ~1 s TABAN sarttir:
        #     sigma_v = sigma_p*sqrt(12/(N*T^2)); T=1.2 s, N=26, sigma_p=0.9 m
        #     -> 0.53 m/s.
        self.ilk.append((t, z))
        while self.ilk and t - self.ilk[0][0] > self.ilk_s:
            self.ilk.pop(0)
        if self.pT is None:
            if len(self.ilk) >= 8 and t - self.ilk[0][0] >= 0.7 * self.ilk_s:
                n = len(self.ilk)
                tm = sum(g[0] for g in self.ilk) / n
                sxx = sum((g[0] - tm) ** 2 for g in self.ilk)
                p0, v0 = [], []
                for j in range(3):
                    zm = sum(g[1][j] for g in self.ilk) / n
                    eg = (sum((g[0] - tm) * (g[1][j] - zm)
                              for g in self.ilk) / sxx) if sxx > 1e-9 else 0.0
                    p0.append(zm + eg * (t - tm))
                    v0.append(eg)
                self.pT, self.vT = tuple(p0), tuple(v0)
                self._zarf()
                self.hazir = True
                self._turet(p_oz, v_oz, dt)
            return

        # ══ ANIZOTROP GUNCELLEME ══════════════════════════════════════════
        # ⚠ Olcum gurultusu YONE GORE 25 KAT farkli:
        #     menzil (radyal) : %15 (OLCULDU std(log)=0.147) -> 6 m'de 0.9 m
        #     kerteriz (teget): 1 px = 0.34°                 -> 6 m'de 0.04 m
        # Izotropik alfa-beta bu bilgiyi CÖPE ATAR: ya menzil gurultusunu
        # kerteriz kanalina sizdirir, ya kerterizi gereksiz yavaslatir.
        u_p = self.u                                   # ongorulen LOS
        e = [z[i] - self.pT[i] for i in range(3)]
        e_r = sum(e[i] * u_p[i] for i in range(3))     # radyal bilesen
        e_t = [e[i] - e_r * u_p[i] for i in range(3)]  # teget bilesen
        esik = max(self.kapi_m, self.kapi_oran * R_ham)
        # ⚠ KAPI IKI KANALDA AYRI. Radyal kapi genis (menzil %15 gurultulu),
        # TEGET kapi DAR (kerteriz 0.34°). "Yanlis nesne" olayi (OLCULDU:
        # 153 px = 42.6°, 0.085 1/s) TEGET bir sicramadir; yalniz radyal
        # kapiyla GECIYOR ve LOS azimut hatasini std 2.1° -> 7.1° yapiyordu.
        e_t_n = math.sqrt(sum(x * x for x in e_t))
        esik_t = max(self.kapi_t_m, self.kapi_t_oran * R_ham)
        if ((abs(e_r) > esik or e_t_n > esik_t)
                and self.red < self.kapi_max):
            self.red += 1
            self.red_top += 1
            self._turet(p_oz, v_oz, dt)
            return
        if self.red >= self.kapi_max:            # kapi cok uzun kapali kaldi
            self.pT = z                          # gercekten sasirmisiz, SIFIRLA
            self.red = 0
            self.ilk = []
            self._turet(p_oz, v_oz, dt)
            return
        self.red = 0
        idt = 1.0 / max(dt, 1e-3)
        self.pT = tuple(self.pT[i] + self.alfa * e_r * u_p[i]
                        + self.alfa_t * e_t[i] for i in range(3))
        self.vT = tuple(self.vT[i] + self.beta * idt * e_r * u_p[i]
                        + self.beta_t * idt * e_t[i] for i in range(3))
        self._zarf()
        self._turet(p_oz, v_oz, dt)

    def _zarf(self):
        """Hiz zarfi: Talon SABIT 17.98 m/s (OLCULDU 24682 ornek)."""
        vh = math.hypot(self.vT[0], self.vT[1])
        hedef_v = self.vt_sabit if self.vt_sabit else min(max(vh, 12.0), 24.0)
        if vh > 1e-6:
            g = hedef_v / vh
            self.vT = (self.vT[0] * g, self.vT[1] * g,
                       max(-4.0, min(4.0, self.vT[2])))

    def _turet(self, p_oz, v_oz, dt):
        r = [self.pT[i] - p_oz[i] for i in range(3)]
        R = math.sqrt(sum(x * x for x in r)) or 1e-6
        self.R = R
        self.u = tuple(x / R for x in r)
        # ⚠ KAPANMA HIZI KUTUDAN DEGIL KINEMATIKTEN (arac/menzil_model UYARI 3:
        # kutu egiminin gurultusu sigma=0.24*R m/s; trail-hold'da SNR<1).
        self.Rdot = sum((self.vT[i] - v_oz[i]) * self.u[i] for i in range(3))
        # 1B kanal (vektor suzgecinden BAGIMSIZ): ongoru + turetme
        if self.R1 is not None:
            voz_u = sum(v_oz[i] * self.u[i] for i in range(3))
            self.Rdot1 = self.c1 - voz_u
            self.R1 = max(0.5, self.R1 + self.Rdot1 * dt)
        # LOS acisal hizi (yatay) — yaw onalmasi icin, EMA ile yumusatilmis
        uh = math.hypot(self.u[0], self.u[1]) or 1e-6
        ux, uy = self.u[0] / uh, self.u[1] / uh
        om = ((self.vT[0] - v_oz[0]) * (-uy)
              + (self.vT[1] - v_oz[1]) * ux) / max(R * uh, 0.5)
        self.om_los += min(1.0, dt / 0.25) * (om - self.om_los)
        hdg = math.atan2(self.vT[1], self.vT[0])
        if self._hdg_o is not None and dt > 1e-6:
            w = _sar(hdg - self._hdg_o) / dt
            self.omega += min(1.0, dt / 0.40) * (w - self.omega)
        self._hdg_o = hdg

    # ---- turetilmis buyuklukler ----
    def uT(self):
        n = math.hypot(self.vT[0], self.vT[1]) or 1e-6
        return self.vT[0] / n, self.vT[1] / n

    def aspect_sapma(self, p_oz):
        """Kuyruktan sapma (derece). 0 = tam arkada."""
        ux, uy = self.uT()
        dx, dy = p_oz[0] - self.pT[0], p_oz[1] - self.pT[1]
        n = math.hypot(dx, dy) or 1e-6
        return math.degrees(math.acos(max(-1.0, min(1.0,
                            -(dx * ux + dy * uy) / n))))


# ══════════════════════════════════════════════════════════════════════════
#  DENETLEYICILER
# ══════════════════════════════════════════════════════════════════════════
class Denetim:
    """Ortak: yaw = LOS, dikey = sabit dz altta. Fark YALNIZ yatay kanalda."""
    ad = "taban"
    T_lead = 0.20        # s ; yaw komutuna LOS hizi ile onalma
    # ── YANAL IVME (= YATIS) SINIRI ──────────────────────────────────────
    # ⚠ Hiz komutu birinci mertebe gecikmeyle uygulanir: a_baslangic =
    # (v_kom - v)/tau, tau=0.211 s (OLCULDU). Komutu kismadan MAX_ACCEL=12'ye
    # dayaniyoruz -> yatis atan(12/9.81) = 50.7°. O yatista (i) goruntu doner,
    # (ii) BAYAT roll ile LOS geri cozumu bozulur, (iii) kullanicinin istedigi
    # "yavas sakin" davranis kaybolur.
    # ALT SINIR FIZIKSEL: donen hedefin arkasinda kalmak icin gereken ivme
    #   R_set=6 m icin (istasyon hedefle AYNI yay uzerinde, a = V²/r):
    #   20 °/s hedef: 6.28 m/s²  |  40 °/s hedef: 12.55 m/s² (> 12.0 TAVAN)
    # ⚠ OLCULDU (tezgah): A_YAN_MAX=9 secilince 20 °/s donuste bile
    # 5 s kilit orani %100 -> %0'a dusuyor ve menzil 6 m yerine 44 m'de
    # dengeleniyor. Gereken 6.3 m/s² gibi gorunse de saf-takip kursunu
    # KORUMAK icin V*omega_LOS = 24*0.35 = 8.4 m/s² lazim ve 21.3 Hz'de
    # komutun ancak %20'si bir periyotta uygulaniyor -> 9 TAVANI YETMIYOR.
    # Bu yuzden varsayilan MAX_ACCEL ile AYNI: 12.0 (yatis 50.7°).
    A_YAN_MAX = 12.0     # m/s²  (yatis 50.7°)
    A_ILERI_MAX = 12.0   # m/s²  (ileri/geri hizlanma — yatis uretmez)
    DZ_TAVAN = 4.0       # m ; hedefin altinda kalinabilecek EN COK fark
    K_EDINIM = 0.6       # (m/s)/m ; edinim kipi menzil kazanci

    def __init__(self, R_set=6.0, dz=None, v_max=24.0, K_z=1.0, **kw):
        self.R_set = R_set
        self.dz = R_set * math.sin(math.radians(Olcum.TILT)) if dz is None else dz
        self.v_max = v_max
        self.K_z = K_z
        for k, v in kw.items():
            setattr(self, k, v)

    def yatay(self, k, p, v):
        raise NotImplementedError

    def edinim(self, k, p, v):
        """EDINIM KIPI — vektor kestirimi (hedef YONU) hazir olmadan once.

        ⚠ Hedefin yonu ~1 s'lik taban olmadan kestirilemez (olculen %15
        menzil gurultusu 47 ms tabanla 30 m/s'lik hiz hatasi verir). Ilk
        surumde bu sure boyunca arac SEYIR ediyordu; GPS devri BORDADAN
        (aspect0=90°) oldugunda baslangic hizi hedefi GOSTERDIGI icin arac
        1.2 s'de 20 m -> 5 m kapatip hedefin onunden geciyor ve bir daha
        goremiyordu (olculdu: aspect0=90/135'te basari %45/%5, sure
        uzatmak DUZELTMIYOR).
        Dogrusu: menzil ve kerteriz TEK KAREDEN bilinir; hedef yonu
        gerekmeyen saf takip + menzil tutma ile basla.
            |v| = V_T + Kp*(R - R_set)   ,  yon = LOS
        """
        u = k.u_ham
        R = k.R1 if k.R1 is not None else (k.R or self.R_set)
        hiz = max(0.0, min(self.v_max,
                           Olcum.HEDEF_HIZ + self.K_EDINIM * (R - self.R_set)))
        n = math.hypot(u[0], u[1]) or 1e-6
        vx, vy = hiz * u[0] / n, hiz * u[1] / n
        s_hed = min(math.sin(math.radians(Olcum.TILT)),
                    self.DZ_TAVAN / max(R, 1.0))
        vz = -max(-3.0, min(3.0, self.K_z * self.R_set * (u[2] - s_hed)))
        return vx, vy, vz, math.atan2(u[1], u[0])

    def __call__(self, k, p, v):
        """(vx, vy, vz_NED, yaw_cmd). k=Kestirim, p=konum, v=hiz (dunya)."""
        vx, vy = self.yatay(k, p, v)
        n = math.hypot(vx, vy)
        if n > self.v_max:
            vx, vy = vx * self.v_max / n, vy * self.v_max / n
        # ---- yanal/ileri ivme sekillendirmesi (yatis denetimi) ----
        sp = math.hypot(v[0], v[1])
        if sp > 1.0:
            ux, uy = v[0] / sp, v[1] / sp
            dvx, dvy = vx - v[0], vy - v[1]
            d_par = dvx * ux + dvy * uy
            d_dik = dvx * (-uy) + dvy * ux
            tau = Olcum.ZAMAN_SABITI
            lp = self.A_ILERI_MAX * tau
            ld = self.A_YAN_MAX * tau
            d_par = max(-lp, min(lp, d_par))
            d_dik = max(-ld, min(ld, d_dik))
            vx = v[0] + d_par * ux - d_dik * uy
            vy = v[1] + d_par * uy + d_dik * ux
            n = math.hypot(vx, vy)
            if n > self.v_max:
                vx, vy = vx * self.v_max / n, vy * self.v_max / n
        # ── DIKEY: ACI UZERINDEN, MENZIL KESTIRIMINE BAGLI DEGIL ──────────
        # ⚠ Ilk surum dz'yi metre olarak (R_hat*u_z) denetliyordu; menzil
        # %15 gurultulu oldugu icin dikey hata da %15 olcekleniyor ve arac
        # yavas yavas hedefin ALTINA kaciyordu (dz -2.5 -> -5.4 m).
        # LOS ACISI cok daha temiz (1 px = 0.34°). Hatayi NOMINAL menzille
        # metreye cevir: e_z = R_set*u_z - dz. Kurulum noktasinda TAM sifir,
        # isareti her menzilde dogru.
        # ⚠ HEDEFIN USTUNE CIKMAK OLDURUCU: R=8 m'de 2.80 m'den fazla
        # yukaridaysak hedef kadrajin ALTINDAN cikar (TILT 25° + VFOV/2 45.5°).
        # Kurulum: hedefi DIKEYDE MERKEZDE tut (u_z = sin 25°) — ama uzak
        # menzilde bu 0.423*R metre ALTTA olmak demektir (30 m'de 12.7 m).
        # ⚠ Olculdu: tavan konmadan arac donuste 15 m dibe iniyor, dikey
        # yetkiyi (VZ_MAX=3) tuketiyor ve yaklasirken geri tirmanamiyor.
        # Bu yuzden dikey ofset DZ_TAVAN ile sinirlanir; kadraj yine
        # rahat icerdedir (R=30, dz=4 -> cyn 0.65; sinir 0.90).
        s_hed = min(math.sin(math.radians(Olcum.TILT)),
                    self.DZ_TAVAN / max(k.R or self.R_set, 1.0))
        vz_yukari = (self.K_z * self.R_set * (k.u[2] - s_hed)
                     + max(-2.0, min(2.0, k.vT[2])))
        vz = -max(-3.0, min(3.0, vz_yukari))          # NED asagi-pozitif
        # yaw = LOS + T_lead * LOS_hizi. Onalma olmadan yaw HEP geride kalir
        # (120 °/s tavan + 0.211 s tau + 47 ms dongu). LOS hizi kestirimden
        # gelir ve gurultuludur -> EMA ile yumusatilir.
        yaw = math.atan2(k.u[1], k.u[0]) + self.T_lead * k.om_los
        return vx, vy, vz, yaw


class DenetimA(Denetim):
    """(a) SAF ISTASYON TAKIBI — bugunku hali.

        p_ist = p_T - R_yatay * u_T          (hedefin arkasinda bir NOKTA)
        v_cmd = K * (p_ist - p)              HIZ ILERI-BESLEMESI YOK

    ⚠ Kalici hata: duz kosuda denge |v|=V_T gerektirir, yani K*e_ss = V_T
    -> e_ss = 17.98/K. K=1'de 18 m GERIDE takilir. Yaklasimin kok kusuru bu.
    """
    ad = "a-saf-istasyon"
    K = 1.0

    def yatay(self, k, p, v):
        ux, uy = k.uT()
        d = math.sqrt(max(self.R_set ** 2 - self.dz ** 2, 0.25))
        ix, iy = k.pT[0] - d * ux, k.pT[1] - d * uy
        return self.K * (ix - p[0]), self.K * (iy - p[1])


class DenetimB(Denetim):
    """(b) MENZIL + MENZIL-HIZI (saf takip yonu).

        yon   = LOS (saf takip)
        |v|   = V_T_kestirim + Kp*(R - R_set) + Kd*Rdot

    Kuyruga gecmeyi SAF TAKIP dinamigi yapar (esit hizda saf takip hedefin
    kuyruguna asimptotik yakinsar); aci acikca denetlenmez.
    ⚠ Rdot kaynagi secilebilir: 'kin' (kinematik, ONERILEN) / 'kutu'
    (kutu buyumesi — OLCULEN gurultusu sigma=0.24*R m/s).
    """
    ad = "b-menzil-hiz"
    Kp = 0.8
    Kd = 1.2
    rdot_kaynak = "kin"

    def yatay(self, k, p, v):
        # ⚠ Bu yasa HEDEF YONUNU (u_T, omega) HIC KULLANMAZ. Yalniz
        # 1B menzil kanalini ve LOS yonunu ister — yani kestirimin
        # gozlenebilirligi en yuksek iki parcasini.
        R = k.R1 if k.R1 is not None else k.R
        rd = {"kutu": k.Rdot_kutu, "vektor": k.Rdot}.get(
            self.rdot_kaynak, k.Rdot1)
        vT = math.hypot(k.vT[0], k.vT[1])
        hiz = vT + self.Kp * (R - self.R_set) + self.Kd * rd
        hiz = max(0.0, min(self.v_max, hiz))
        ux, uy = k.u[0], k.u[1]
        n = math.hypot(ux, uy) or 1e-6
        return hiz * ux / n, hiz * uy / n


class DenetimC(Denetim):
    """(c) KERTERIZ-KILITLI TRAIL — hedefin IZINI takip et, dogrusunu degil.

    ⚠ ONCE DOGRUSAL SURUMU DENENDI VE DONUSTE COKTU (olculdu):
        v_cmd = v_T + K_par*e_par*u_T + K_dik*e_dik*n_T
      Bu, istasyonu "hedefin ARKASINDA d metre" diye DUZ CIZGIDE tanimlar
      ve ileri-beslemeyi HEDEFIN konumundaki tegete esitler. Arac 30 m
      geride iken 51 m yaricapli daire uzerinde 34° geride demektir; o
      noktadaki teget 34° farklidir. Sonuc: komut araci daireden DISARI
      itti, menzil 14 m -> 39 m'ye acildi, 12/12 donus kosusu ISKA.

    DOGRUSU — YEREL TEGET. Hedefin izi yerel olarak r = V/omega yaricapli
    bir yay; aracin izdusumundeki teget u_T'nin GERIYE dondurulmusudur:
        s     = -(p - p_T).u_T                  (yaklasik geri mesafe)
        Dpsi  = omega * s / V                   (o noktada yol yonu farki)
        u_p   = rot(u_T, -Dpsi)                 (IZDUSUMDEKI teget)
        p_ist = p_T - r sin(D0) u_T + r(1-cos D0) n_T ,  D0 = omega*d_set/V
        e     = p_ist - p ;  e_par = e.u_p ;  e_yan = e.n_p
        v_cmd = V*u_p + K_par*e_par*u_p + K_dik*e_yan*n_p
    ⚠ NEDEN C MERKEZLI SURUM DEGIL: "C = p_T + (V/omega)*n_T" formu
      omega'ya 1/omega ile baglidir. Olculen omega kestirimi 0-39 °/s
      arasinda gezindiginde r 26 m ile SONSUZ arasinda ziplar, yanal hata
      |p-C|-|r| 25 m'lik hayalet degerler alir ve komut surekli DOYAR.
      Yerel teget formu omega'ya YALNIZ birinci mertebeden baglidir
      (Dpsi = omega*s/V) ve tutus rejiminde s=5.4 m oldugu icin omega
      hatasinin etkisi ~6°'ye duser.
    """
    ad = "c-kerteriz-trail"
    K_par = 0.9
    K_dik = 1.6
    YAN_MAX = 15.0                     # m/s ; yanal terim tavani
    ff_omega = True                    # False -> egrilik yok sayilir

    def yatay(self, k, p, v):
        ux, uy = k.uT()
        nx, ny = -uy, ux                          # sol normal
        V = math.hypot(k.vT[0], k.vT[1]) or Olcum.HEDEF_HIZ
        d_set = math.sqrt(max(self.R_set ** 2 - self.dz ** 2, 0.25))
        om = k.omega if self.ff_omega else 0.0
        om = max(-1.2, min(1.2, om))
        ex, ey = p[0] - k.pT[0], p[1] - k.pT[1]
        s = -(ex * ux + ey * uy)
        dps = max(-1.2, min(1.2, om * s / max(V, 1.0)))
        cd, sd = math.cos(dps), math.sin(dps)
        px, py = cd * ux - sd * nx, cd * uy - sd * ny      # yerel teget
        qx, qy = -py, px                                   # yerel sol normal
        # istasyon noktasi da yay uzerinde (d_set kucuk oldugu icin kucuk duzeltme)
        d0 = om * d_set / max(V, 1.0)
        if abs(om) > 1e-6:
            r = V / om
            ix = k.pT[0] - r * math.sin(d0) * ux + r * (1 - math.cos(d0)) * nx
            iy = k.pT[1] - r * math.sin(d0) * uy + r * (1 - math.cos(d0)) * ny
        else:
            ix, iy = k.pT[0] - d_set * ux, k.pT[1] - d_set * uy
        gx, gy = ix - p[0], iy - p[1]
        e_par = gx * px + gy * py
        e_yan = gx * qx + gy * qy
        e_yan = max(-self.YAN_MAX, min(self.YAN_MAX, self.K_dik * e_yan))
        vx = V * px + self.K_par * e_par * px + e_yan * qx
        vy = V * py + self.K_par * e_par * py + e_yan * qy
        return vx, vy


DENETIMLER = {"a": DenetimA, "b": DenetimB, "c": DenetimC}


# ══════════════════════════════════════════════════════════════════════════
#  KOSU
# ══════════════════════════════════════════════════════════════════════════
def kosu(denetim="c", senaryo="duz", R_set=6.0, R0=20.0, aspect0=45.0,
         sure=40.0, dt=1.0 / 62.0, tohum=0, hata=None, v_max=24.0,
         max_accel=12.0, kutu_olcek=True, kutu_gurultu=True,
         vt_sabit=Olcum.HEDEF_HIZ, tutum_modeli=True, kayit=False,
         kayip_kopru_s=0.7, kes_kw=None, tani=False, **kw):
    """Tek trail-hold angajmani.

    aspect0 : baslangicta KUYRUKTAN sapma (derece). 0 = tam arkada,
              90 = borda, 180 = karsidan. GPS devri buraya birakir.
    R0      : devir menzili (SAHA medyani 32.9 m; eski calismada 13 m).
    vt_sabit: hedef SUR'ATI (skaler) ileri-beslemesi. Varsayilan OLCULEN
              17.98 m/s — 24682 ornekli truth kaydinda SABIT cikti ve GPS
              fazi zaten devirden once olcuyor. None verilirse suret de
              kutudan kestirilir (ablasyon: "V_T kestirimi").
    """
    if hata is None:
        hata = HataAyari()
    algi = Algi(hata, tohum=tohum)
    kutu = Kutu(tohum=tohum, olcek=kutu_olcek, gurultu=kutu_gurultu)
    sayac = KilitSayaci()
    sayac._ilan = True          # binlerce kosuda "[KILIT] ..." basmasin
                                # (yalniz yazdirma bayragi; karar mantigi ayni)

    hed = HedefYol(senaryo)
    hx, hy, hz, hvx, hvy, hvz = hed.durum()
    hdg = math.atan2(hvy, hvx)

    # avci: hedeften R0 uzakta, kuyruk yonunden aspect0 kadar sapmis
    yon = hdg + math.pi + math.radians(aspect0)
    dz0 = min(3.0, 0.4 * R0)
    yatay0 = math.sqrt(max(R0 ** 2 - dz0 ** 2, 1.0))
    D = denetim if isinstance(denetim, Denetim) else DENETIMLER[denetim](
        R_set=R_set, v_max=v_max, **kw)
    av = Avci(x=hx + yatay0 * math.cos(yon), y=hy + yatay0 * math.sin(yon),
              z=hz - dz0, yaw=0.0, max_accel=max_accel, v_max=v_max,
              vz_max=3.0, yaw_rate_max=120.0)
    av.yaw = math.atan2(hy - av.y, hx - av.x)
    av.vx = Olcum.HEDEF_HIZ * math.cos(av.yaw)
    av.vy = Olcum.HEDEF_HIZ * math.sin(av.yaw)

    # kutu yasi boru hattinin OLCULEN sabitlerinden turetilir (dogrula #8)
    yas_nom = (hata.kare_gecikme_s + hata.det_gecikme_s
               + (0.5 / hata.kamera_hz if hata.kamera_hz > 0.0 else 0.0))
    kes = Kestirim(tohum=tohum, tutum_modeli=tutum_modeli, vt_sabit=vt_sabit,
                   yas_nom=yas_nom, **(kes_kw or {}))

    t = 0.0
    son_yasa_t = -1e9
    son_poz = None
    son_yaw_cmd = av.yaw
    a_yan_cmd = 0.0
    kayip_s = 0.0
    kayip_top = 0.0
    Rs = []            # (t, truth menzil)
    epsy = []          # |eps_yaw| deg (truth)
    marj = []          # AV kenar payi (1.0 = tam sinirda)
    asp = []           # kuyruktan sapma (truth, deg)
    kilit_iz = []      # (t, anlik kilit)
    iz = []
    tn_roll = []       # tani: roll kestirim hatasi (deg)
    tn_az = []         # tani: LOS azimut geri-cozum hatasi (deg)
    v_cmd = (av.vx, av.vy, 0.0)

    while t < sure:
        hed.adim(dt)
        hx, hy, hz, hvx, hvy, hvz = hed.durum()
        hdg = math.atan2(hvy, hvx)
        av._hedef_yon = hdg
        k = kutu(av, hx, hy, hz, dt)
        algi.kare_ver(t, av, k)

        # ---- TRUTH olcutleri (her sim adiminda) ----
        Rt = math.dist((av.x, av.y, av.z), (hx, hy, hz))
        Rs.append((t, Rt))
        if k is not None:
            tx, ty = (k[0] - CX) / F_YASA, (k[1] - CY) / F_YASA
            epsy.append(abs(math.degrees(math.atan(tx))))
            marj.append(max(abs(tx * Kal.KX) / KilitCfg.AV_X,
                            abs(ty * Kal.KY) / (0.5 - KilitCfg.AV_Y)))
        else:
            epsy.append(90.0)
            marj.append(9.0)
        dxa, dya = av.x - hx, av.y - hy
        na = math.hypot(dxa, dya) or 1e-6
        asp.append(math.degrees(math.acos(max(-1.0, min(1.0,
                   -(dxa * math.cos(hdg) + dya * math.sin(hdg)) / na)))))

        # ---- yasa dongusu 21.3 Hz ----
        if hata.yasa_hz > 0.0 and t - son_yasa_t < 1.0 / hata.yasa_hz - 1e-9:
            av.adim(dt, t)
            t += dt
            continue
        dt_yasa = dt if son_yasa_t < 0.0 else max(t - son_yasa_t, dt)
        son_yasa_t = t

        poz = algi.oku(t)
        yaw_olc = algi.yaw_oku(t)
        roll_olc, pitch_olc = algi.tutum_oku(t)

        # ---- SARTNAME KILIT SAYACI (gercek modul, degistirilmeden) ----
        tespit = None
        if poz is not None:
            cxp, cyp, wp, hp = poz
            txp, typ = (cxp - CX) / F_YASA, (cyp - CY) / F_YASA
            tespit = {"cx": (0.5 + txp * Kal.KX) * 1920.0,
                      "cy": (0.5 + typ * Kal.KY) * 1080.0,
                      "w": wp * (Kal.DOW_F / F_YASA),
                      "h": hp * (Kal.DOW_F / F_YASA),
                      "W": 1920.0, "H": 1080.0}
        anlik = sayac.guncelle(tespit, t, gorsel_faz=True)
        kilit_iz.append((t, anlik))

        if poz is None:
            kayip_s += dt_yasa
            kayip_top += dt_yasa
        else:
            kayip_s = 0.0

        # TANI: tutum ve LOS geri-cozum hatasi (yalniz olcum, denetime girmez)
        if tani and kes.hazir and poz is not None and poz is not son_poz:
            tn_roll.append(math.degrees(_sar(kes.roll_hat - av.roll)))
            uh = kes.u_ham
            dd = (hx - av.x, hy - av.y, hz - av.z)
            nn = math.sqrt(sum(x * x for x in dd)) or 1e-6
            tn_az.append(abs(math.degrees(_sar(
                math.atan2(uh[1], uh[0]) - math.atan2(dd[1], dd[0])))))
        # ⚠ AYNI kutuyu iki kez fuzyonlama (bkz. Kestirim.guncelle `yeni`).
        # Gercekte tespit mesaji kare zaman damgasi tasir; burada nesne
        # kimligi ayni isi gorur (Algi tutucu AYNI demeti dondurur).
        yeni_kutu = poz is not None and poz is not son_poz
        son_poz = poz
        kes.guncelle(t, dt_yasa, poz, yaw_olc, roll_olc, pitch_olc,
                     av.yaw_hizi, (av.x, av.y, av.z), (av.vx, av.vy, -av.vz),
                     a_yan_cmd, yeni_kutu)
        if kes.hazir:
            vx, vy, vz, yaw_cmd = D(kes, (av.x, av.y, av.z),
                                    (av.vx, av.vy, -av.vz))
            # ── KAYIP POLITIKASI ──────────────────────────────────────────
            # ⚠ Kutu kaybolunca HAYALETI KOVALAMA. Ilk surumde kestirim
            # ongoruyle ilerliyor, denetleyici o hayalete gidiyordu: bir
            # kosuda menzil 326 m'ye, irtifa farki +97 m'ye kacti. Dogrusu
            # SEYIR: hedefin son kestirilen hizini surdur, dikeyi dondur,
            # burnu son LOS'ta tut — hedefin kadraja geri girmesine sans ver.
            if kayip_s > kayip_kopru_s:
                vx, vy = kes.vT[0], kes.vT[1]
                vz = 0.0
                # burun ONGORULEN LOS'ta kalir: kadraji hedefin OLMASI
                # gereken yere cevir, kor ucus yapma.
                yaw_cmd = math.atan2(kes.pT[1] - av.y, kes.pT[0] - av.x)
            # kendi roll'umuzu modelden kestirmek icin komut ivmesi
            dvx = (vx - av.vx) / max(Olcum.ZAMAN_SABITI, 1e-6)
            dvy = (vy - av.vy) / max(Olcum.ZAMAN_SABITI, 1e-6)
            am = math.hypot(dvx, dvy)
            if am > max_accel and am > 1e-9:
                dvx, dvy = dvx * max_accel / am, dvy * max_accel / am
            sp = math.hypot(av.vx, av.vy)
            if sp > 0.5:
                a_yan_cmd = dvx * (-av.vy / sp) + dvy * (av.vx / sp)
            av.setpoint(vx, vy, vz, yaw_cmd, t)
            v_cmd = (vx, vy, vz)
        elif kes.R1 is not None:
            # EDINIM KIPI (bkz. Denetim.edinim) — hedef yonu gerekmez.
            vx, vy, vz, yaw_cmd = D.edinim(kes, (av.x, av.y, av.z),
                                           (av.vx, av.vy, -av.vz))
            av.setpoint(vx, vy, vz, yaw_cmd, t)
        else:
            # ⚠ Henuz TEK kutu bile yok. tesis.Avci HIC setpoint almamissa
            # KONUMU BILE ILERLETMEZ (adim() sp None iken erken doner);
            # ilk surumde arac donuyor, hedef 21.6 m uzaklasiyordu.
            yc = kes.yaw_hat if kes.yaw_hat is not None else av.yaw
            if poz is not None:
                yc = yc + math.atan((poz[0] - CX) / F_YASA)
            av.setpoint(av.vx, av.vy, 0.0, yc, t)
        if kayit:
            iz.append([round(t, 2), round(Rt, 2),
                       round(kes.R or 0.0, 2),
                       round(epsy[-1], 1), round(asp[-1], 1),
                       round(math.hypot(av.vx, av.vy), 2),
                       round(av.z - hz, 2), 1 if anlik else 0,
                       round(math.degrees(_sar(
                           (kes.yaw_hat if kes.yaw_hat is not None else av.yaw)
                           - av.yaw)), 1),
                       round(math.degrees(_sar(math.atan2(
                           kes.vT[1], kes.vT[0]) - hdg)), 1)
                       if kes.vT else 0.0,
                       round(kes.Rdot, 2), kes.red_top])
        av.adim(dt, t)
        t += dt

    out = _olc(Rs, epsy, marj, asp, kilit_iz, sayac, R_set, kayip_top, t, iz)
    if tn_roll:
        m = sum(tn_roll) / len(tn_roll)
        out["tani_roll_std"] = math.sqrt(
            sum((x - m) ** 2 for x in tn_roll) / len(tn_roll))
        s = sorted(tn_az)
        out["tani_az_med"] = s[len(s) // 2]
    else:
        out["tani_roll_std"] = out["tani_az_med"] = None
    return out


def _olc(Rs, epsy, marj, asp, kilit_iz, sayac, R_set, kayip_top, sure, iz):
    """Olcutler. TRUTH'tan hesaplanir (denetleyici bunlari GORMEZ)."""
    def med(v):
        if not v:
            return None
        s = sorted(v)
        n = len(s)
        return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])

    def p95(v):
        return sorted(v)[int(0.95 * (len(v) - 1))] if v else None

    # (i) oturma: |R-R_set|<=1.0 olup SONUNA KADAR +-1.5 icinde kalan ilk an
    otur = None
    n = len(Rs)
    son_ihlal = -1                       # |R-R_set|>1.5 olan SON ornek
    for i in range(n - 1, -1, -1):
        if abs(Rs[i][1] - R_set) > 1.5:
            son_ihlal = i
            break
    for i in range(son_ihlal + 1, n):
        if abs(Rs[i][1] - R_set) <= 1.0:
            otur = Rs[i][0]
            break
    # (ii) oturduktan sonraki salinim
    if otur is not None:
        kal = [r for tt, r in Rs if tt >= otur]
        m = sum(kal) / len(kal)
        std = math.sqrt(sum((x - m) ** 2 for x in kal) / len(kal))
    else:
        kal, std = [], None
    # (iv) 5 s KESINTISIZ kilit
    en_uzun = 0.0
    bas = None
    for i, (tt, a) in enumerate(kilit_iz):
        if a and bas is None:
            bas = tt
        elif not a and bas is not None:
            en_uzun = max(en_uzun, tt - bas)
            bas = None
    if bas is not None and kilit_iz:
        en_uzun = max(en_uzun, kilit_iz[-1][0] - bas)
    kilit_orani = (sum(1 for _, a in kilit_iz if a) / len(kilit_iz)
                   if kilit_iz else 0.0)
    # oturduktan SONRAKI pencere — asil ilgilendigimiz rejim
    i0 = son_ihlal + 1 if otur is not None else 0
    ilk = next((tt for tt, r in Rs if abs(r - R_set) <= 1.0), None)
    return {
        "otur_s": otur, "ilk_s": ilk,
        "R_std": std,
        "R_med": med([r for _, r in Rs]),
        "R_son": Rs[-1][1] if Rs else None,
        "R_min": min((r for _, r in Rs), default=None),
        "eps_med": med(epsy), "eps_p95": p95(epsy),
        "marj_med": med(marj), "marj_p95": p95(marj),
        "asp_med": med(asp), "asp_p95": p95(asp),
        "eps_med_o": med(epsy[i0:]) if otur is not None else None,
        "eps_p95_o": p95(epsy[i0:]) if otur is not None else None,
        "asp_med_o": med(asp[i0:]) if otur is not None else None,
        "marj_p95_o": p95(marj[i0:]) if otur is not None else None,
        "kesintisiz_s": en_uzun,
        "kesintisiz_ok": en_uzun >= KilitCfg.WIN_NEED_S,
        "sartname_ok": bool(sayac.ok),
        "kilit_orani": kilit_orani,
        "kayip_s": kayip_top, "sure": sure, "iz": iz,
    }


def parti(n=12, **kw):
    """n angajman: baslangic fazi ve tohum degisir."""
    out = []
    for i in range(n):
        kw2 = dict(kw)
        kw2["tohum"] = i
        out.append(kosu(**kw2))
    return out


def ozet(ad, r, gen=24):
    import statistics as st

    def med(v, f="%.1f"):
        v = [x for x in v if x is not None]
        return (f % st.median(v)) if v else "  -"
    ok = sum(1 for x in r if x["kesintisiz_ok"])
    sok = sum(1 for x in r if x["sartname_ok"])
    return ("  %-*s %5.0f%% %5.0f%% %6s %6s %5s %6s %6s %5s %5s" % (
        gen, ad, 100.0 * ok / len(r), 100.0 * sok / len(r),
        med([x["ilk_s"] for x in r]),
        med([x["R_std"] for x in r], "%.2f"),
        med([x["R_min"] for x in r]),
        med([x["eps_med_o"] for x in r]),
        med([x["eps_p95_o"] for x in r]),
        med([x["asp_med"] for x in r]),
        med([x["kayip_s"] for x in r])))


def basliksatiri(gen=24):
    return ("  %-*s %5s %5s %6s %6s %5s %6s %6s %5s %5s" % (
        gen, "yapilandirma", "5s", "sart", "ilk_s", "Rstd", "Rmin",
        "eps50", "eps95", "asp", "kayip")
        + "\n  " + "-" * (gen + 57))


# degerlendirme kumesi: donus40 ve s20 AYRI raporlanir (fiziksel sinir disi)
SENARYO = ("duz", "donus20", "dikey", "oval")
ASPECT = (0.0, 45.0, 90.0)


def kume(n=5, senaryolar=SENARYO, aspectler=ASPECT, denetim="c", **kw):
    r = []
    for sen in senaryolar:
        for asp in aspectler:
            r += parti(n=n, denetim=denetim, senaryo=sen, aspect0=asp, **kw)
    return r


# ══════════════════════════════════════════════════════════════════════════
#  OZ-SINAMA
# ══════════════════════════════════════════════════════════════════════════
def dogrula_trail(sessiz=False):
    """Trail katmaninin ISARET/OLCEK dogrulugu. HER TARAMADAN ONCE."""
    h = []
    # 0) alt tezgah
    if T.dogrula(sessiz=True):
        h.append("tesis.dogrula() KALDI — once onu duzelt")

    # 1) KUTU KALIBRASYONU: kuyruk aspect'inde OLCULEN iki sabiti vermeli
    class _A:
        x = y = z = 0.0
        yaw = pitch = roll = 0.0
        _hedef_yon = 0.0
    a = _A()
    a.yaw = 0.0
    a._hedef_yon = 0.0          # hedef bizden UZAKLASIYOR degil: beta=180
    ku = Kutu(tohum=1, olcek=True, gurultu=False)
    R = 20.0
    a.x, a.y, a.z = -R, 0.0, 0.0
    a._hedef_yon = 0.0          # hedef +x'e uciyor, biz arkasindayiz -> kuyruk
    k = ku(a, 0.0, 0.0, 0.0, 1 / 62.0)
    if k is None:
        h.append("kalibrasyon karesi kadraj disi")
    else:
        w, hh = k[2], k[3]
        k1 = R * math.sqrt(w * hh)
        k2 = R * w ** Kal.A_W * hh ** Kal.A_H
        if abs(k1 - Kal.K_SQRT) / Kal.K_SQRT > 0.02:
            h.append("R*sqrt(wh)=%.1f, OLCULEN %.1f" % (k1, Kal.K_SQRT))
        if abs(k2 - Kal.K_WH) / Kal.K_WH > 0.02:
            h.append("R*w^.15h^.85=%.1f, OLCULEN %.1f" % (k2, Kal.K_WH))

    # 2) KILIT ESIK MENZILI: olculen kutuyla 9.26 m, tesis kutusuyla 8.21 m
    e1, e0 = kilit_esik_menzil(True), kilit_esik_menzil(False)
    if abs(e1 - 9.264) > 0.05 or abs(e0 - 8.210) > 0.05:
        h.append("kilit esik menzili %.2f/%.2f m, beklenen 9.26/8.21" % (e1, e0))
    # gercek sayacla capraz kontrol
    s = KilitSayaci()
    for i, RR in enumerate((e1 - 0.3, e1 + 0.3)):
        a.x, a.y, a.z = -RR, 0.0, 0.0
        kk = ku(a, 0.0, 0.0, 0.0, 1 / 62.0)
        tx, ty = (kk[0] - CX) / F_YASA, (kk[1] - CY) / F_YASA
        an = s.guncelle({"cx": (0.5 + tx * Kal.KX) * 1920.0,
                         "cy": (0.5 + ty * Kal.KY) * 1080.0,
                         "w": kk[2] * Kal.DOW_F / F_YASA,
                         "h": kk[3] * Kal.DOW_F / F_YASA,
                         "W": 1920.0, "H": 1080.0}, i * 0.05)
        if i == 0 and not an:
            h.append("esigin ICINDE (%.1f m) sayac kilit vermedi" % RR)
        if i == 1 and an:
            h.append("esigin DISINDA (%.1f m) sayac kilit verdi" % RR)

    # 3) LOS TERSI: rastgele tutumlarda truth yonu birebir vermeli
    rnd = random.Random(11)
    enb = 0.0
    for _ in range(200):
        a.yaw = rnd.uniform(-math.pi, math.pi)
        a.pitch = math.radians(rnd.uniform(-20, 20))
        a.roll = math.radians(rnd.uniform(-60, 60))
        a.x, a.y, a.z = 0.0, 0.0, 0.0
        hx, hy, hz = (rnd.uniform(-40, 40), rnd.uniform(-40, 40),
                      rnd.uniform(-15, 15))
        kk = kadraj(a, hx, hy, hz)
        if kk is None:
            continue
        tx, ty = (kk[0] - CX) / F_YASA, (kk[1] - CY) / F_YASA
        u = los_dunya(tx, ty, a.yaw, a.pitch, a.roll)
        n = math.sqrt(hx * hx + hy * hy + hz * hz)
        c = (u[0] * hx + u[1] * hy + u[2] * hz) / n
        enb = max(enb, math.degrees(math.acos(max(-1.0, min(1.0, c)))))
    if enb > 0.05:
        h.append("los_dunya() tersi tutmadi (enb %.3f°)" % enb)
    a.yaw = a.pitch = a.roll = 0.0

    # 4) KUTU BOYUT GURULTUSU, OLCULEN egim gurultusunu vermeli:
    #    sigma(Vc) = 0.239 * R  (0.8 s nedensel pencere, 21.3 Hz)
    rr = 20.0
    egimler = []
    for tohum in range(40):
        ku2 = Kutu(tohum=tohum, olcek=True, gurultu=True)
        gec = []
        dtl = 1.0 / 21.3
        for i in range(60):
            for _ in range(3):                    # 62 Hz sim adimi
                pass
            kk = ku2(a, rr, 0.0, 0.0, dtl)
            b = math.log(kk[2] ** Kal.A_W * kk[3] ** Kal.A_H)
            gec.append((i * dtl, b))
            while gec and i * dtl - gec[0][0] > 0.80:
                gec.pop(0)
        n = len(gec)
        tm = sum(g[0] for g in gec) / n
        bm = sum(g[1] for g in gec) / n
        sxx = sum((g[0] - tm) ** 2 for g in gec)
        egimler.append(sum((g[0] - tm) * (g[1] - bm) for g in gec) / sxx)
    m = sum(egimler) / len(egimler)
    sg = math.sqrt(sum((x - m) ** 2 for x in egimler) / len(egimler))
    if not (0.12 <= sg <= 0.45):
        h.append("kutu egim gurultusu %.3f 1/s, OLCULEN 0.239" % sg)

    # 5) DIKEY ISARET: kamera 25° YUKARI. Hedefin ALTINDA olmak ty'yi
    #    KUCULTUR; USTUNDE olmak buyutur ve 2.8 m'den sonra kadrajdan CIKARIR.
    dz5 = 8.0 * math.sin(math.radians(Olcum.TILT))          # 3.381 m
    a.x, a.y = -8.0 * math.cos(math.radians(Olcum.TILT)), 0.0
    a.z = -dz5                                              # 3.38 m ALTTA
    k1 = kadraj(a, 0.0, 0.0, 0.0)
    if k1 is None or abs((k1[1] - CY) / F_YASA) > 0.02:
        h.append("R=8 m'de %.2f m altta ty=%.3f, beklenen ~0"
                 % (dz5, 9.9 if k1 is None else (k1[1] - CY) / F_YASA))
    # ustte: kadrajdan cikis siniri  elev = TY_MAX acisi - TILT
    ust = 8.0 * math.sin(math.atan(TY_MAX) - math.radians(Olcum.TILT))  # 2.80 m
    a.x, a.z = -math.sqrt(64.0 - (ust - 0.3) ** 2), (ust - 0.3)
    if kadraj(a, 0.0, 0.0, 0.0) is None:
        h.append("hedefin %.2f m ustunde kadraj disi cikti (beklenen: ICERIDE)"
                 % (ust - 0.3))
    a.x, a.z = -math.sqrt(64.0 - (ust + 0.3) ** 2), (ust + 0.3)
    if kadraj(a, 0.0, 0.0, 0.0) is not None:
        h.append("hedefin %.2f m ustunde hala kadrajda (beklenen: CIKAR)"
                 % (ust + 0.3))
    a.x = a.z = 0.0

    # 6) DENETLEYICI ISARETI (KUSURSUZ sensor, duz hedef): c oturmali
    r = kosu(denetim="c", senaryo="duz", R_set=8.0, R0=20.0, aspect0=0.0,
             sure=30.0, hata=HataAyari.kapali(), kutu_gurultu=False,
             tutum_modeli=False)
    if r["otur_s"] is None or abs(r["R_son"] - 8.0) > 0.5:
        h.append("kusursuz sensorde (c) R_set'e oturmadi (son %.2f m, otur %s)"
                 % (r["R_son"], r["otur_s"]))
    if r["asp_p95"] is None or r["asp_med"] > 5.0:
        h.append("kusursuz sensorde (c) kuyruga gecmedi (asp_med %.1f°)"
                 % r["asp_med"])

    # 7) KALICI HATA: (a) saf istasyon K=1'de ~V_T/K kadar GERIDE takilmali
    ra = kosu(denetim="a", senaryo="duz", R_set=8.0, R0=20.0, aspect0=0.0,
              sure=40.0, hata=HataAyari.kapali(), kutu_gurultu=False,
              tutum_modeli=False, K=1.0)
    bkl = 8.0 + Olcum.HEDEF_HIZ / 1.0
    if abs(ra["R_son"] - bkl) > 4.0:
        h.append("(a) K=1 kalici hatasi %.1f m, beklenen ~%.1f m"
                 % (ra["R_son"], bkl))

    # 8) DIKEY MANEVRA ISARETI: hedef tirmaninca biz de tirmanmaliyiz
    rz = kosu(denetim="c", senaryo="dikey", R_set=8.0, R0=15.0, aspect0=0.0,
              sure=20.0, hata=HataAyari.kapali(), kutu_gurultu=False,
              tutum_modeli=False, kayit=True)
    dz = [x[6] for x in rz["iz"][int(0.3 * len(rz["iz"])):]]
    if dz and (max(dz) - min(dz)) > 4.0:
        h.append("dikey manevrada irtifa farki %.1f m saliniyor (>4 m)"
                 % (max(dz) - min(dz)))

    # 9) ⭐ TUTUM/LOS ZINCIRI — tezgahin en pahali arizasinin bekcisi.
    #    Roll'u KOMUT ivmesinden kestirmek (std 15°) ya da LOS'u SIMDIKI
    #    tutumla kurmak (kutu 63 ms yasli) kapali dongu limit cevrimi
    #    uretiyordu. Bu sinama ikisini birden yakalar.
    r9 = kosu(denetim="c", senaryo="duz", R_set=6.0, R0=20.0, aspect0=0.0,
              sure=25.0, tohum=3, tani=True)
    if r9["tani_roll_std"] is None or r9["tani_roll_std"] > 6.0:
        h.append("roll kestirim hatasi std %.1f°, esik 6° (ivmeden kestirim "
                 "bozuldu mu?)" % (r9["tani_roll_std"] or -1))
    if r9["tani_az_med"] is None or r9["tani_az_med"] > 3.0:
        h.append("LOS azimut hatasi medyan %.1f°, esik 3° (yakalama ani "
                 "tutumu kullanilmiyor olabilir)" % (r9["tani_az_med"] or -1))

    # 10) EDINIM KIPI: vektor kestirimi hazir olmadan MENZIL TUTMALI.
    #     Bordadan devirde (aspect0=90) ilk 1.2 s'de arac hedefin uzerine
    #     dalmamali — en yakin menzil 3 m'nin altina inmemeli.
    r10 = [kosu(denetim="c", senaryo="duz", R_set=6.0, R0=20.0, aspect0=90.0,
                sure=12.0, tohum=i) for i in range(4)]
    if min(x["R_min"] for x in r10) < 3.0:
        h.append("bordadan devirde en yakin menzil %.1f m (<3 m): edinim "
                 "kipi menzil tutmuyor" % min(x["R_min"] for x in r10))

    if not sessiz:
        print("  TRAIL OZ-SINAMASI: %s" % ("TAMAM (10/10)" if not h else "KALDI"))
        for x in h:
            print("    ! " + x)
    return h


# ══════════════════════════════════════════════════════════════════════════
#  CLI
# ══════════════════════════════════════════════════════════════════════════
def main():
    ap = argparse.ArgumentParser(description="trail-hold tezgahi")
    ap.add_argument("--dogrula", action="store_true", help="oz-sinama (10/10)")
    ap.add_argument("--kiyas", action="store_true", help="a/b/c kiyasi")
    ap.add_argument("--rset", action="store_true", help="R_set taramasi")
    ap.add_argument("--tara", action="store_true", help="kazanc taramasi")
    ap.add_argument("--limit", action="store_true", help="nerede bozuluyor")
    ap.add_argument("--tek", action="store_true", help="tek angajman dokumu")
    ap.add_argument("--hepsi", action="store_true")
    ap.add_argument("--n", type=int, default=5, help="senaryo/aspect basi kosu")
    ap.add_argument("--sure", type=float, default=40.0)
    ap.add_argument("--rs", type=float, default=6.0, help="R_set (m)")
    ap.add_argument("--vmax", type=float, default=24.0)
    a = ap.parse_args()
    try:                      # Windows konsolu cp1252; UTF-8 zorla
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    hepsi = a.hepsi or not any((a.dogrula, a.kiyas, a.rset, a.tara,
                                a.limit, a.tek))
    ORT = dict(sure=a.sure, v_max=a.vmax)

    print("=" * 96)
    print("TRAIL-HOLD TEZGAHI   R_set=%.1f m  v_max=%.1f (mu=%.3f)  "
          "kilit esik menzili: %.2f m (olculen kutu) / %.2f m (eski tesis)"
          % (a.rs, a.vmax, Olcum.HEDEF_HIZ / a.vmax,
             kilit_esik_menzil(True), kilit_esik_menzil(False)))
    print("  5s   = 5 sn KESINTISIZ kilit kosu orani (ANA OLCUT)")
    print("  sart = sartname sayaci (10 s pencerede kumulatif 5 s; "
          "guidance/kilit_sayaci.py)")
    print("  ilk_s= |R-R_set|<=1 m'ye ilk varis | Rstd = oturduktan sonraki "
          "menzil salinimi")
    print("  eps50/95 = oturduktan sonra hedefin kadraj merkezinden yatay "
          "sapmasi (derece)")
    print("=" * 96)

    if a.dogrula or hepsi:
        assert not dogrula_trail(), "OZ-SINAMA KALDI — tarama gecersiz"

    if a.tek or hepsi:
        r = kosu(denetim="c", senaryo="oval", R_set=a.rs, R0=20.0,
                 aspect0=45.0, kayit=True, **ORT)
        print("\n  TEK ANGAJMAN (c, oval, R0=20 m, aspect0=45°)")
        print("    5s kesintisiz %.1f s | sartname %s | ilk varis %s s | "
              "Rstd %s | en yakin %.2f m"
              % (r["kesintisiz_s"], r["sartname_ok"],
                 ("%.1f" % r["ilk_s"]) if r["ilk_s"] is not None else "-",
                 ("%.2f" % r["R_std"]) if r["R_std"] else "-", r["R_min"]))
        print("    %6s%8s%8s%7s%7s%7s%7s%5s%8s%8s%7s%5s" % (
            "t", "R", "R_kes", "eps", "asp", "|v|", "dz", "kl",
            "yawerr", "vThata", "Rdot", "red"))
        iz = r["iz"]
        for i in range(0, len(iz), max(1, len(iz) // 22)):
            print("    %6.1f%8.2f%8.2f%7.1f%7.1f%7.2f%7.2f%5d%8.1f%8.1f%7.2f%5d"
                  % tuple(iz[i]))

    if a.kiyas or hepsi:
        print("\n" + "=" * 96)
        print("KIYAS — UC YAKLASIM, GERCEKCI olcum hatasi")
        print("=" * 96)
        for sen in ("duz", "donus20", "dikey", "oval", "donus40", "s20"):
            print("\n  == senaryo: %s%s ==" % (
                sen, "   (FIZIKSEL SINIR DISI — asagiya bak)"
                if sen in ("donus40", "s20") else ""))
            print(basliksatiri())
            for ad, d, ek in (
                    ("(a) saf istasyon K=1", "a", dict(K=1.0)),
                    ("(a) saf istasyon K=3", "a", dict(K=3.0)),
                    ("(b) menzil+menzil-hizi", "b", {}),
                    ("(b) Rdot KUTUDAN", "b", dict(rdot_kaynak="kutu")),
                    ("(c) kerteriz-kilitli trail", "c", {}),
                    ("(c) egrilik ff KAPALI", "c", dict(ff_omega=False))):
                r = kume(a.n, (sen,), ASPECT, denetim=d, R_set=a.rs,
                         **dict(ORT, **ek))
                print(ozet(ad, r))

    if a.rset or hepsi:
        print("\n" + "=" * 96)
        print("R_set TARAMASI (c) — kutu-boyut kiliti %.2f m'de kesiliyor, "
              "ama kutu %%15 gurultulu:" % kilit_esik_menzil(True))
        print("  5 s KESINTISIZ icin ~107 ardisik kare esigi GECMELI -> "
              "3-sigma pay gerekir -> R_set <= %.1f m" %
              (kilit_esik_menzil(True) / math.exp(3 * Kal.BOYUT_SIGMA)))
        print("=" * 96)
        print(basliksatiri())
        for rs in (4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0):
            print(ozet("R_set=%.0f m" % rs,
                       kume(a.n, R_set=rs, **ORT)))

    if a.tara or hepsi:
        print("\n" + "=" * 96)
        print("KAZANC TARAMASI (c, R_set=%.1f m)" % a.rs)
        print("=" * 96)
        print(basliksatiri())
        for kp in (0.5, 0.9, 1.5):
            for kd in (1.0, 1.6, 2.4):
                print(ozet("K_par=%.1f K_dik=%.1f" % (kp, kd),
                           kume(a.n, R_set=a.rs, K_par=kp, K_dik=kd, **ORT)))
        for tl in (0.0, 0.2, 0.4):
            print(ozet("T_lead=%.1f s" % tl,
                       kume(a.n, R_set=a.rs, T_lead=tl, **ORT)))
        for dz in (2.5, 4.0, 6.0):
            print(ozet("DZ_TAVAN=%.1f m" % dz,
                       kume(a.n, R_set=a.rs, DZ_TAVAN=dz, **ORT)))

    if a.limit or hepsi:
        print("\n" + "=" * 96)
        print("NEREDE BOZULUYOR (c, R_set=%.1f m)" % a.rs)
        print("=" * 96)
        print(basliksatiri(26))
        gr = [("== DEVIR ACISI (GPS fazi burayi birakir) ==", None)]
        for asp in (0.0, 45.0, 90.0, 135.0, 180.0):
            gr.append(("aspect0=%.0f°" % asp, dict(aspectler=(asp,))))
        gr.append(("== DEVIR MENZILI ==", None))
        for r0 in (13.0, 20.0, 33.0, 45.0):
            gr.append(("R0=%.0f m%s" % (r0, "  (saha medyani)"
                                        if r0 == 33.0 else ""),
                       dict(R0=r0)))
        gr.append(("== ARAC ZARFI ==", None))
        for vm in (19.0, 20.0, 22.0, 24.0, 28.0):
            gr.append(("v_max=%.0f (mu=%.2f)" % (vm, Olcum.HEDEF_HIZ / vm),
                       dict(v_max=vm)))
        for ac in (8.0, 12.0, 16.0, 20.0):
            gr.append(("MAX_ACCEL=%.0f m/s²" % ac,
                       dict(max_accel=ac, A_YAN_MAX=ac)))
        gr.append(("== HEDEF MANEVRASI ==", None))
        for sen in ("duz", "donus20", "donus40", "s20", "dikey", "oval"):
            gr.append(("hedef: %s" % sen, dict(senaryolar=(sen,))))
        gr.append(("== OLCUM/KESTIRIM ABLASYONU ==", None))
        gr += [("olcum hatasi KAPALI", dict(hata=HataAyari.kapali(),
                                            kutu_gurultu=False)),
               ("kutu boyut gurultusu KAPALI", dict(kutu_gurultu=False)),
               ("yaw donmasi KAPALI", dict(hata=HataAyari.haric("yaw"))),
               ("yanlis nesne KAPALI", dict(hata=HataAyari.haric("yanlis"))),
               ("kutu gecikmesi KAPALI", dict(hata=HataAyari.haric("gecikme"))),
               ("tutum ivmeden KESTIRIM YOK", dict(tutum_modeli=False)),
               ("V_T sabiti YOK (kestirim)", dict(vt_sabit=None)),
               ("egrilik ff KAPALI", dict(ff_omega=False)),
               ("yaw onalma KAPALI", dict(T_lead=0.0)),
               ("ESKI TESIS kutusu", dict(kutu_olcek=False))]
        for ad, kw in gr:
            if kw is None:
                print("  %s" % ad)
                continue
            kw = dict(kw)
            sens = kw.pop("senaryolar", SENARYO)
            asps = kw.pop("aspectler", (0.0, 45.0))
            print(ozet(ad, kume(a.n, sens, asps, R_set=a.rs,
                                **dict(ORT, **kw)), 26))


if __name__ == "__main__":
    main()

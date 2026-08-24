# -*- coding: utf-8 -*-
"""
================================================================================
  TESIS (plant)  --  DoW aracinin ve hedefin OLCULMUS fizigi
================================================================================
AMAC
--------------------------------------------------------------------------------
Gorsel guduum yasasini oyunu acmadan, kusursuz ground truth'la ve gercek
zamandan HIZLI kosturmak. Boylece:
    * tek deney 40 dakika yerine milisaniye surer
    * olcum gurultusu YOK -> etki gurultuden buyuk olur
    * degisken izole edilebilir (tespit gurultusunu kapatip yasayi tek basina
      sinamak gibi)

⚠ SADIKLIK KURALI
--------------------------------------------------------------------------------
Buradaki HER sabit OLCULDU, tahmin degil. Kaynak: DOW_ARAC_PARAMETRELERI.md
(kumanda cubugu dogrudan surulerek yapilan zarf testleri + 275500 ornekli
truth iz kaydi). Sadik olmayan bir simulator KENDINDEN EMIN YANLIS cevap
verir; tek savunma olculmus sayilar ve degistirilmemis gudum kodudur.

⚠ NE MODELLENMEZ (bilerek)
--------------------------------------------------------------------------------
    * ruzgar        : olculdu, YOK (9.7 s notr cubukta 0.06 m surukleme)
    * aerodinamik   : olculdu, MODELLENMIYOR (yavaslama a ~ V^0.03, aktif fren)
    * GPS bozulmasi : gorsel fazda zaten kullanilmiyor (yarisma kurali)
Bunlarin yoklugu simulatoru GERCEKTEN BASITLESTIRIR, kabul degil.

⚠ NE MODELLENIYOR (2026-08-16 eklendi): OLCUM HATASI — bkz. HataAyari/Algi.
Tesis 510 angajmanda "PN cok daha iyi" dedi, oyunda HIC fark cikmadi. Sebep:
kadraj() piksel acisini GERCEK geometriden uretiyordu ve yasa LOS'u
iris_yaw + atan((cx-CX)/F) ile kuruyor — simulatorde bu ikisi TANIMI GEREGI
esitti, yani olcum hatasi SIFIRDI. Artik tesis o arizayi URETEBILIYOR.

SAHA OLCUMU (arac/pn_kiyas.py, 7 gorsel faz):
    lam_sisme = lam_yasa/lam_truth medyan 5.9x  (3.8 - 8.2, bir aykiri 52)
    lam_yasa p95 81-159 °/s | lam_truth p95 19-23 °/s
    faz omru 1.6-2.1 s | en yakin 15.1-22.6 m | sureklilik %30-52
TESIS, HATA ACIKKEN (40-60 angajman):
    devir 13.0 m : sisme 3.0x | lam_yasa 146-165 | omur 7 s  | en yakin 4.1 m
    devir 32.9 m : sisme 1.8x | lam_yasa  67     | omur 6.8 s| en yakin 23.7 m
    (saha devir medyani 32.9 m; orada tesis SAHANIN ~19.5 m'sini veriyor)
TEK TEK (devir 13 m, PN_N=1.6):  gecikme 6.3x · yaw 5.0x · yanlis 2.2x
    kayip 2.3x · kenar 1.6x · dongu 1.5x · KUSURSUZ sensor 1.6x (metrik tabani)
PN USTUNLUGU (saf takip ıskası − PN ıskası):
    hata yok 3.40 m -> gecikme acik 0.50 m -> hepsi acik 0.31 m  (KAYBOLUYOR)
    yaw/kenar/dongu tek basina ustunlugu YOK ETMIYOR (3.5-8.9 m kaliyor).
⚠ Yani "PN cok daha iyi" bulgusunu oldureN sey KUTU GECIKMESI.
================================================================================
"""
import math
import random


# ══════════════════════════════════════════════════════════════════════════
#  OLCULMUS SABITLER
# ══════════════════════════════════════════════════════════════════════════
class Olcum:
    # ---- HEDEF (Talon) — 24682 ornekli truth kaydindan ----
    HEDEF_HIZ = 17.98          # m/s, SABIT (pencere testiyle dogrulandi)
    TUR_UZUNLUK = 530.0        # m
    TUR_SURE = 29.5            # s
    DONUS_YARICAP = 51.0       # m (medyan)
    DUZ_ORAN = 0.52            # yolun %52'si duz
    HEDEF_IRTIFA = 90.0        # m (olculen 85-95, ortalama)
    KANAT_ACIKLIGI = 1.78      # m
    GOVDE_UZUNLUK = 1.10       # m

    # ---- AVCI — kumanda cubugu dogrudan surulerek olculen ZARF ----
    ZARF_IVME = 39.22          # m/s²  (esdeger yatis 76 derece)
    ZARF_HIZ = 34.6            # m/s
    ZARF_TIRMANMA = 33.7       # m/s
    ZARF_ALCALMA = -5.6        # m/s   (6 kat asimetrik — olculdu)
    ZARF_YAW = 214.0           # deg/s
    OLU_ZAMAN = 0.046          # s  (komut -> ivmenin %10'u)
    ZAMAN_SABITI = 0.211       # s  (ivmenin %63'u)

    # ---- KAMERA — motor projeksiyonundan en kucuk karelerle cozuldu ----
    HFOV = 122.0709            # derece
    VFOV = 90.93               # derece
    GEN = 640                  # yasa cercevesi (tespit_akisi._yasa_icsellik)
    YUK = 480
    TILT = 25.0                # derece yukari (olculen +22.9, kod 25)

    # ---- ALGI — 12562 tespitli kareden ----
    # Kutu buyudukce tespit guvenilirligi artiyor. Olculen surekliligi
    # kaba bir lojistik egriyle temsil ediyoruz (bkz. tespit_olasilik).
    TESPIT_YARI = 14.0         # px; bu boyutta olasilik %50
    TESPIT_EGIM = 0.22         # egrinin dikligi


# ── ⚠ IKI AYRI CERCEVE VAR, KARISTIRMA ────────────────────────────────────
# 1) DEDEKTORUN gordugu GERCEK kare: DoW 1920x1080, KARE piksel,
#    fx_dow = fy_dow = (1920/2)/tan(122.0709/2) = 531.36.
#    Hedefin KADRAJDAN CIKIP CIKMADIGI burada belli olur.
# 2) YASANIN calistigi cerceve: 640x480, F_YASA = 166.6.
#    tespit_akisi.dow_pikseli_yasaya() 1'den 2'ye ACIYI KORUYARAK cevirir:
#        cx_yasa = 320 + F_YASA * tan(azimut)
#    Yasa da atan((cx-320)/F_YASA) ile geri cevirir -> F_YASA SADELESIR.
#    Bu yuzden F_YASA'nin "yanlis" olmasi (Gazebo'nun 125° iris kamerasindan
#    kalma) ZARARSIZ: ceviri ile yasa ayni sabiti kullaniyor.
#    ⚠ Simulatorun ILK surumu buraya gercek DoW icselligini (FY=236.2)
#    koymustu; bu, yasaya %42 sahte dikey olcek hatasi veriyordu ve
#    "dikeyde batiyoruz" diye YANLIS bir bulgu uretti. Duzeltildi.
F_YASA = 166.6                                   # vision/geometry.py: FX=FY
CX, CY = Olcum.GEN / 2.0, Olcum.YUK / 2.0        # 320, 240
FX = FY = F_YASA                                 # kadraj() YASA pikseli uretir

# gercek kadrajin acisal siniri (tanjant cinsinden) — gorunurluk testi
_FX_DOW = (1920.0 / 2.0) / math.tan(math.radians(Olcum.HFOV / 2.0))   # 531.36
TX_MAX = (1920.0 / 2.0) / _FX_DOW                # tan(61.04°) = 1.8067
TY_MAX = (1080.0 / 2.0) / _FX_DOW                # tan(45.47°) = 1.0163


# ══════════════════════════════════════════════════════════════════════════
#  HEDEF — oval pist (stadyum)
# ══════════════════════════════════════════════════════════════════════════
class Hedef:
    """Olculen oval: iki duz kenar + iki 180 derece donus, SABIT hizda.

    Geometri turetilmesi: tur = 2*duz + 2*(pi*R). Olculen tur 530 m ve
    R = 51 m ise duz kenar = (530 - 2*pi*51)/2 = 105.7 m. Duz oran
    2*105.7/530 = %40 cikar; olculen %52 ile tam ortusmuyor cunku gercek
    yorunge tam stadyum degil (uclar yumurta bicimli). Fark kabul edilir:
    onemli olan DONUS HIZI (20.1 deg/s) ve HIZIN SABITLIGI.
    """

    def __init__(self, faz0=0.0, irtifa=None, yon=+1):
        self.R = Olcum.DONUS_YARICAP
        self.duz = max((Olcum.TUR_UZUNLUK - 2 * math.pi * self.R) / 2.0, 1.0)
        self.cevre = 2 * self.duz + 2 * math.pi * self.R
        self.s = faz0 * self.cevre           # yay uzunlugu boyunca konum
        self.z = irtifa if irtifa is not None else Olcum.HEDEF_IRTIFA
        self.yon = yon                        # +1 saat yonu tersi

    def adim(self, dt):
        self.s = (self.s + Olcum.HEDEF_HIZ * dt) % self.cevre

    def durum(self):
        """(x, y, z, vx, vy, vz) — NED benzeri duzlem (x ileri, y sag)."""
        s, R, L = self.s, self.R, self.duz
        if s < L:                                   # 1. duz kenar (+x yonu)
            x, y, hdg = s, 0.0, 0.0
        elif s < L + math.pi * R:                   # 1. donus (ust uc)
            a = (s - L) / R
            x = L + R * math.sin(a)
            y = R * (1 - math.cos(a))
            hdg = a
        elif s < 2 * L + math.pi * R:               # 2. duz kenar (-x yonu)
            d = s - (L + math.pi * R)
            x, y, hdg = L - d, 2 * R, math.pi
        else:                                       # 2. donus (alt uc)
            a = (s - (2 * L + math.pi * R)) / R
            x = -R * math.sin(a)
            y = 2 * R - R * (1 - math.cos(a))
            hdg = math.pi + a
        hdg *= self.yon
        y *= self.yon
        v = Olcum.HEDEF_HIZ
        return x, y, self.z, v * math.cos(hdg), v * math.sin(hdg), 0.0

    def donus_hizi_deg(self):
        """Anlik donus hizi (deg/s). Duz kenarda 0, donuste v/R."""
        s, R, L = self.s, self.R, self.duz
        donuste = (L <= s < L + math.pi * R) or (s >= 2 * L + math.pi * R)
        return math.degrees(Olcum.HEDEF_HIZ / R) if donuste else 0.0


# ══════════════════════════════════════════════════════════════════════════
#  AVCI — hiz setpoint arayuzu + olculen gecikme ve clamp'ler
# ══════════════════════════════════════════════════════════════════════════
class Avci:
    """Hiz setpoint alir, OLCULEN dinamikle uygular.

    MODEL: birinci mertebe gecikme + olu zaman + ivme clamp.
        olu zaman  0.046 s   (komut kuyruga girer)
        tau        0.211 s   (ivmenin %63'u)
        |dv/dt|   <= MAX_ACCEL  (yazilim clamp'i; zarf 39.22)
    Bu, basamak testinden CIKARILDI, varsayilmadi.
    """

    def __init__(self, x=0.0, y=0.0, z=80.0, yaw=0.0,
                 max_accel=12.0, v_max=24.0, vz_max=3.0,
                 yaw_rate_max=120.0):
        self.x, self.y, self.z = x, y, z
        self.vx = self.vy = self.vz = 0.0
        self.yaw = yaw
        self.roll = self.pitch = 0.0
        self.yaw_hizi = 0.0
        self.max_accel = max_accel
        self.v_max = v_max
        self.vz_max = vz_max
        self.yaw_rate_max = yaw_rate_max
        self._kuyruk = []                  # olu zaman kuyrugu

    def setpoint(self, vx, vy, vz, yaw, t):
        self._kuyruk.append((t + Olcum.OLU_ZAMAN, vx, vy, vz, yaw))

    def adim(self, dt, t):
        # olu zamani gecmis en yeni komutu al
        hedef = None
        while self._kuyruk and self._kuyruk[0][0] <= t:
            hedef = self._kuyruk.pop(0)
        if hedef is not None:
            self._sp = hedef[1:]
        sp = getattr(self, "_sp", None)
        if sp is None:
            return
        svx, svy, svz, syaw = sp

        # hiz clamp'leri (yazilim)
        vmag = math.hypot(svx, svy)
        if vmag > self.v_max and vmag > 1e-9:
            k = self.v_max / vmag
            svx, svy = svx * k, svy * k
        svz = max(-self.vz_max, min(self.vz_max, svz))

        # birinci mertebe gecikme
        a = dt / max(Olcum.ZAMAN_SABITI, 1e-6)
        a = min(a, 1.0)
        dvx = (svx - self.vx) * a
        dvy = (svy - self.vy) * a
        dvz = (svz - self.vz) * a

        # ivme clamp — YATAY (asil bagliyan)
        amag = math.hypot(dvx, dvy) / max(dt, 1e-9)
        if amag > self.max_accel:
            k = self.max_accel / amag
            dvx, dvy = dvx * k, dvy * k
        self.vx += dvx
        self.vy += dvy
        self.vz += dvz

        # yaw: hiz sinirli
        fark = (syaw - self.yaw + math.pi) % (2 * math.pi) - math.pi
        adim_ = math.radians(self.yaw_rate_max) * dt
        d = max(-adim_, min(adim_, fark))
        self.yaw = (self.yaw + d + math.pi) % (2 * math.pi) - math.pi
        self.yaw_hizi = d / max(dt, 1e-9)

        # ATTITUDE — multirotor: yatis, HIZA DIK ivme bileseninden turetilir.
        # ⚠ ISARETLI olmali. Ilk surumde atan2(hypot(...), g) yazilmisti ve
        # hypot daima >=0 oldugu icin roll HEP POZITIF cikiyordu; yasa
        # los_seviye() ile roll telafisi yaptigindan bu ona cop besliyordu.
        # Dogrusu: ivmenin hiz yonune DIK bileseni (isaretli, sag donus +).
        vmag = math.hypot(self.vx, self.vy)
        if vmag > 0.5 and dt > 1e-9:
            ux, uy = self.vx / vmag, self.vy / vmag
            a_dik = (dvx / dt) * (-uy) + (dvy / dt) * ux     # sag pozitif
            self.roll = math.atan2(a_dik, 9.81)
            # pitch: hiz yonundeki ivme (ileri hizlanma -> burun asagi)
            a_ileri = (dvx / dt) * ux + (dvy / dt) * uy
            self.pitch = -math.atan2(a_ileri, 9.81) * 0.5
        else:
            self.roll = self.pitch = 0.0
        self.x += self.vx * dt
        self.y += self.vy * dt
        # ⚠ ISARET: self.vz yasanin cikardigi gibi NED ASAGI-POZITIF tutulur
        # (iris_vz olarak yasaya geri beslenecegi icin oyle olmali). self.z ise
        # IRTIFA (yukari). Bu yuzden CIKARILIR. Ilk surumde toplaniyordu:
        # tirmanma komutu alcalma uretiyor, hedef kadrajin USTUNDEN kaciyordu.
        self.z -= self.vz * dt


# ══════════════════════════════════════════════════════════════════════════
#  KAMERA — hedefi kadraja yansitir
# ══════════════════════════════════════════════════════════════════════════
def kadraj(avci, hx, hy, hz):
    """Hedefi avcinin kamerasina yansitir.

    Kamera GOVDEYE SABIT, TILT derece yukari vidali. Tam attitude zinciri:
        dunya --yaw--> --pitch--> --roll--> govde(FRD) --tilt--> kamera
    ⚠ ROLL MODELLENIYOR. Yasa los_seviye() ile roll telafisi yapiyor;
    tesis roll'u kadraja katmazsa o telafi HIC SINANMAZ (ve simulatorde
    "sorun yok" gorunur). Yanlis donus suphesinin tam merkezi burasi.

    Cikti YASA CERCEVESI pikselidir (bkz. F_YASA notu). Gorunurluk ise
    GERCEK DoW kadrajinin acisal siniriyla (TX_MAX/TY_MAX) sinanir.

    Doner: (cx, cy, w, h, menzil) veya kadraj disindaysa None.
    """
    dx, dy, dz = hx - avci.x, hy - avci.y, hz - avci.z
    menzil = math.sqrt(dx * dx + dy * dy + dz * dz)
    if menzil < 0.3:
        return None

    # 1) yaw: dunya -> yaw'lanmis cerceve.  FRD: ileri, sag, ASAGI
    c, s = math.cos(-avci.yaw), math.sin(-avci.yaw)
    f = dx * c - dy * s
    r = dx * s + dy * c
    d = -dz                                   # dz yukari idi -> asagi

    # 2) pitch (burun yukari +)
    pc, ps = math.cos(avci.pitch), math.sin(avci.pitch)
    f, d = f * pc - d * ps, f * ps + d * pc

    # 3) roll (sag kanat asagi +)
    rc, rs = math.cos(avci.roll), math.sin(avci.roll)
    r, d = r * rc + d * rs, -r * rs + d * rc

    # 4) kamera tilt (sabit, yukari)
    t = math.radians(Olcum.TILT)
    tc, ts = math.cos(t), math.sin(t)
    kf = f * tc - d * ts                      # kamera ileri
    kd = f * ts + d * tc                      # kamera asagi
    if kf <= 0.3:                             # arkada
        return None

    tx, ty = r / kf, kd / kf                  # acisal (tanjant)
    if abs(tx) > TX_MAX or abs(ty) > TY_MAX:  # GERCEK kadrajin disinda
        return None

    cx = CX + F_YASA * tx
    cy = CY + F_YASA * ty                     # cy asagi dogru buyur

    # kutu: gorunur genislik BAKIS ACISINA bagli (rapor E maddesi).
    # kuyruktan bakinca kanat acikligini, yandan bakinca govdeyi goruruz.
    beta = _bakis_acisi(avci, hx, hy)
    gen_m = math.hypot(Olcum.KANAT_ACIKLIGI * math.cos(beta),
                       Olcum.GOVDE_UZUNLUK * math.sin(beta))
    w = F_YASA * gen_m / menzil
    h = F_YASA * Olcum.GOVDE_UZUNLUK * 0.30 / menzil     # ince govde
    return cx, cy, max(w, 1.0), max(h, 1.0), menzil


def _bakis_acisi(avci, hx, hy):
    """Hedefin burun yonu ile bize olan yon arasindaki aci (0 = tam kuyruk)."""
    hd = getattr(avci, "_hedef_yon", None)
    if hd is None:
        return 0.0
    ax = math.atan2(avci.y - hy, avci.x - hx)     # hedeften BIZE
    return (ax - hd + math.pi) % (2 * math.pi) - math.pi


def tespit_olasilik(w, h):
    """Kutu boyutuna gore tespit olasiligi (lojistik).

    Olculdu (12562 tespitli kare): kutu buyudukce sureklilik artiyor.
    Yari-nokta 14 px secildi — olculen medyan kutu 12.7 px ve o rejimde
    faz ici sureklilik %13-30 araligindaydi.
    """
    b = max(w, h)
    return 1.0 / (1.0 + math.exp(-Olcum.TESPIT_EGIM * (b - Olcum.TESPIT_YARI)))


# ══════════════════════════════════════════════════════════════════════════
#  OLCUM HATASI — yasanin GORDUGU ile GERCEGIN farki
# ══════════════════════════════════════════════════════════════════════════
# ⚠⚠ BU BOLUM NEDEN VAR — TESISIN UCUNCU (VE EN PAHALI) SAHTE BULGUSU
# --------------------------------------------------------------------------
# Tesis 510 angajmanda "PN saf takipten cok daha iyi" dedi (37/480 -> 357/480).
# Oyunda dort ayarin DORDU DE ~19.5 m verdi: HIC FARK YOK.
#
# Kok neden: yasa LOS'u iki AYRI sensorden kuruyor —
#       LOS_yasa = iris_yaw (telemetri)  +  atan((cx - CX)/F) (dedektor)
# Eski tesiste cx'i kadraj() ayni anin GERCEK avci.yaw'iyla uretiyordu, yani
# LOS_yasa == LOS_gercek TANIMI GEREGI. Olcum hatasi tam SIFIRDI. Oysa gercek
# ucusta (36 angajman):
#       faz basi   : LOS_yasa - LOS_truth = + 8.3 derece
#       faz sonu   :                        +59.2 derece
#       lam_yasa / lam_truth = 7.1  (36/36 angajmanda)
# PN dogrudan lam ile calisir; lam 7 kat sisince PN'in "avantaji" sahte olur.
# Simulator bu arizayi URETEMEDIGI icin YANLIS KAZANAN sectI.
#
# ASIL MEKANIZMA — ZAMAN UYUMSUZLUGU: cx GECMISTEKI bir kareden gelir
# (yakalama + dedektor), iris_yaw ise NEREDEYSE ANLIK. Arac donerken
#       LOS_yasa(t) = yaw(t) + eps(t-D) = LOS_truth(t-D) + [yaw(t) - yaw(t-D)]
#                   ~ LOS_truth(t-D) + yaw_hizi * D
# Turevi lam_truth + yaw_ivmesi*D olur; BURUN_LOS ile yaw LOS'u kovaladigi
# icin bu KAPALI DONGU — kendini besler ve limit cevrimine oturur. Radome
# slope / parasitic feedback'in aynisi.
# --------------------------------------------------------------------------


class HataAyari:
    """Olcum hata kaynaklari. HEPSI KAPATILABILIR, varsayilan GERCEKCI.

    Ablation icin:  HataAyari.tek("gecikme")   -> yalniz o kaynak acik
                    HataAyari.haric("gecikme") -> yalniz o kaynak kapali
                    HataAyari.kapali()         -> hepsi kapali (ESKI tesis)
    """

    # ── 1) IRIS_YAW OKUMA HATASI (telemetri kanali) ───────────────────────
    # Yasa iris_yaw'i ARAC TELEMETRISINDEN alir; kutu ise goruntu boru
    # hattindan. Iki kanal ayri hizda akar — ve yaw kanali BAYAT olani.
    #
    # ⚠⚠ OLCULDU ve TAHMIN EDILENDEN COK DAHA KOTU. kopru_tani_*.csv icindeki
    # `yaw_yas_s` (ayni yaw degerinin kac saniyedir tekrarlandigi), 6 dosya /
    # 419.505 kopru tiki (62.5 Hz):
    #     tiklerin %59.4'u BAYAT bir yaw tasiyor
    #     yas: p50 0.016 s | p90 1.172 s | p95 2.313 s | p99 4.766 s
    #          MAX 7.469 s
    #     kiyas: SDK hizi (`v_yas_s`) p90 0.031 s, max 0.140 s — HIZ TAZE,
    #     BAYAT OLAN YAW.
    # dow_kopru.py:673-679 ayni seyi bagimsiz sekilde yaziyor: "attitude'un
    # tiklerin %17-51'inde DONUK kaldigi (yaw'da 7 s'ye varan bloklar)".
    #
    # MODEL: iki bilesen. (a) taban yayin hizi, (b) nadir uzun BLOK'lar.
    # Blok suresi D ~ lognormal(medyan, p95). Kalibrasyon dogrudan olculen
    # yas kuyruguna oturtuldu (blok icinde yas > a olan zaman orani
    # = blok_hiz * E[(D-a)+]):
    #     E[(D-1.17)+]*hiz = 0.10   -> olculen p90 1.172 s
    #     E[(D-2.31)+]*hiz = 0.05   -> olculen p95 2.313 s
    #     E[(D-4.77)+]*hiz = 0.01   -> olculen p99 4.766 s
    # med=1.5 / p95=5.0 / hiz=0.106 uculuyu birden tutturuyor; blok gorev
    # cevrimi = 0.106 * E[D] 1.96 s = %20.8.
    # yaw_hz : blok DISINDA yayin hizi (her tikte p=yaw_hz*dt olasilikla
    #          taze ornek; boylece adim suresinden bagimsiz). Toplam taze
    #          oran = p*(1-0.208) = 0.406 -> yaw_hz = 32 Hz.
    #          0.0 = her adimda taze (KAPALI).
    yaw_hz = 32.0                  # Hz  — OLCULDU'den turetildi
    yaw_blok_hiz = 0.106           # 1/s — OLCULDU'den turetildi (yas kuyrugu)
    yaw_blok_med_s = 1.5           # s   — OLCULDU'den turetildi
    yaw_blok_p95_s = 5.0           # s   — OLCULDU'den turetildi (yas MAX 7.47 s)
    # tasima gecikmesi ve gurultu
    # ⚠ TAHMIN: ATTITUDE tasima gecikmesi ayri olculmedi (SDK HIZI icin
    # olculen 0-20 ms'ten alindi: kopru/03_OLCUMLER.md:78).
    yaw_gecikme_s = 0.020          # s   — TAHMIN
    # ⚠ TAHMIN: depoda yaw sensor gurultusu (std/RMS/jitter) HICBIR YERDE YOK.
    # 03_OLCUMLER.md:338'deki 2.6° KAPALI DONGU izleme hatasi, sensor
    # gurultusu degil. Buyukluk tamamen tahmindir.
    yaw_gurultu_deg = 0.30         # deg — TAHMIN

    # ── 2) TESPIT KUTUSUNUN GECIKMESI ─────────────────────────────────────
    # kamera_hz : yasaya YENI kutu gelme hizi. Iki kare arasinda yasa AYNI
    #             kutuyu tekrar okur (sifirinci mertebe tutucu). 0.0 = her
    #             sim adiminda yakala (KAPALI).
    # OLCULDU: bbox_ibvs_*.csv, kutu tasiyan (durum==IBVS) satirlarda dt
    # medyani 47.0 ms = 21.3 Hz (n=14.305). Bagimsiz dogrulama:
    # docs/kopru_denetim.md:175 "yasa dt medyani 47.0 ms -> 21.3 Hz".
    # ⚠ Cfg.LOOP_HZ=20.0 yalnizca bir uyku tabani, gercek hiz bu.
    kamera_hz = 21.3               # Hz  — OLCULDU
    # kare_gecikme_s : yakalama -> dedektorun eline gecmesi (grab + kopya).
    # ⚠ TAHMIN: bbox_ibvs.py:1011 bu alani (`gecikme_s`) OLCMEK icin acmis ve
    # "tahminle konmamali" diye yazmis, ama alan TUM loglarda BOS. Olculmedi.
    kare_gecikme_s = 0.017         # s   — TAHMIN
    # det_gecikme : dedektor cikarim suresi. OLCULDU: veri/perf_log_*.csv
    # `det_ms`, guncel boru hatti (15-16 Agu, n=13.370): p50 23.0 ms,
    # p95 45.9 ms. Dagilim lognormal — medyan ve p95'i AYNEN tutturur
    # (sigma = ln(p95/med)/1.645).
    # ⚠ Gorevde verilen 25.3/36.5 cifti depoda HICBIR dosyada yok; 276 perf
    # logunun hicbiri o araligi vermiyor. Olculen degerler kullanildi.
    det_gecikme_s = 0.0230         # s   — OLCULDU (det_ms p50)
    det_gecikme_p95_s = 0.0459     # s   — OLCULDU (det_ms p95)

    # ── 2b) YASA DONGU HIZI ───────────────────────────────────────────────
    # Simulator yasayi 62 Hz'de cagiriyordu; GERCEKTE 21.3 Hz kosuyor.
    # Bu tek basina bir "hata kaynagi" degil ama lam kestirimini dogrudan
    # etkiler (0.25 s pencere 62 Hz'de 15 ornek, 21.3 Hz'de 5 ornek) ve
    # kontrol bant genisligini 3 KAT dusurur. Ayri ablate edilebilsin diye
    # ayri tutuldu.  0.0 = her sim adiminda cagir (KAPALI).
    yasa_hz = 21.3                 # Hz  — OLCULDU (docs/kopru_denetim.md:175)

    # ── 3) KUTU MERKEZI YANLILIGI (kadraj kenari) ─────────────────────────
    # OLCULDU (bbox_ibvs_*.csv, `conf` x `eps_yaw_deg`, n=14.350):
    #     |eps|  0-10°  medyan conf 0.656
    #           30-40°              0.674   (henuz dusme yok)
    #           40-50°              0.629
    #           50-60°              0.560
    #           60-70°              0.536
    # ⚠ Gorevde verilen "0.83 -> 0.41" DUSUS 4 KAT ABARTILI: o cift,
    # 0-10° kutusunun p90'i (0.823) ile 40-50° kutusunun p10'u (0.427)
    # kiyaslanarak olusmus gorunuyor — ayni istatistik degil. Gercek medyan
    # dususu 0.656 -> 0.560, yani %15 goreli. Model buna gore KISILDI.
    kenar_baslangic_deg = 40.0     # deg — OLCULDU (dususun basladigi kutu)
    kenar_doyum_deg = 60.0         # deg — OLCULDU (conf 0.560'a indigi kutu)
    # ⚠ TAHMIN: piksel cinsinden kayma OLCULMEDI (elde yalniz conf var).
    # Kutu boyutunun kesri; 0.25 = doyumda kutunun ceyregi kadar kayma.
    # Olculen medyan kutu ~12.7 px -> ~3 px. Kayma MERKEZE dogru (kenarda
    # gorunur uzanti kirpilir + duzeltilmemis radyal bozulma iceri ceker):
    # yani arayici olcek carpani hatasi, off-axis aci OLDUGUNDAN KUCUK gorunur.
    kenar_yanlilik_kutu = 0.25     # kutu kesri — TAHMIN
    kenar_gurultu_kutu = 0.25      # kutu kesri — TAHMIN (ek sigma)

    # ── 4) YANLIS NESNE ───────────────────────────────────────────────────
    # OLCULDU (bbox_ibvs_*.csv IBVS satirlarinda ardisik |dcx|, n=1369):
    #     p50 2.8 px | p90 15.3 | p95 21.9 | p99 54.0 | MAX 388.8
    #     |dcx| > 100 px olan kareler: %0.80   |dcx| > 150 px: %0.22
    # Bir "yanlis nesne" olayi IKI buyuk sicrama uretir (gidis + donus),
    # yani olay hizi = 0.0080/2 * 21.3 Hz = 0.085 1/s.
    # ⚠ Gorevde verilen "12 angajmanin 1'inde 153 px" depoda YOK; 153 sayisi
    # hicbir dosyada gecmiyor. Ancak buyukluk olculen >150 px nufusunun
    # icinde kaliyor, o yuzden genlik olarak korundu.
    # ⚠ Olayin SURESI olculmedi (TAHMIN).
    yanlis_hiz = 0.085             # 1/s — OLCULDU'den turetildi
    yanlis_sapma_px = 153.0        # px  — olculen >150 px nufusu icinde
    yanlis_sure_s = 0.40           # s   — TAHMIN

    # ── (onceden de vardi) tespit surekliligi ve piksel jitter'i ──────────
    # ⚠ SADIKLIK NOTU: gercekte bbox_ibvs satirlarinin %74.2'sinde HIC kutu
    # yok (46.498/62.689). tespit_olasilik() medyan kutuda ~%43 verir, yani
    # tesis gercekten DAHA IYIMSER. Bu sabit degistirilmedi (olculmus
    # tespit_olasilik egrisi bu dosyanin baska bir kalibrasyonu).
    tespit_kaybi = True            # tespit_olasilik(w,h) ile kare dusurme
    jitter_px = 1.0                # px  — kutu merkezi gurultusu (sigma)

    # kaynak -> alan eslemesi (ablation icin)
    KAYNAKLAR = {
        "yaw":     ("yaw_hz", "yaw_blok_hiz", "yaw_gecikme_s",
                    "yaw_gurultu_deg"),
        "gecikme": ("kamera_hz", "kare_gecikme_s",
                    "det_gecikme_s", "det_gecikme_p95_s"),
        "kenar":   ("kenar_yanlilik_kutu", "kenar_gurultu_kutu"),
        "yanlis":  ("yanlis_hiz",),
        "dongu":   ("yasa_hz",),
        "kayip":   ("tespit_kaybi", "jitter_px"),
    }

    def __init__(self, **kw):
        for k, v in kw.items():
            if not hasattr(HataAyari, k) or k.isupper():
                raise KeyError("bilinmeyen hata ayari: %r" % k)
            setattr(self, k, v)

    def __repr__(self):
        return "HataAyari(%s)" % ", ".join(
            "%s=%s" % (k, getattr(self, k)) for k in sorted(self.__dict__))

    @classmethod
    def _sifirla(cls, adlar):
        return {a: (False if a == "tespit_kaybi" else 0.0) for a in adlar}

    @classmethod
    def kapali(cls, **kw):
        """Butun hata kaynaklari KAPALI — KUSURSUZ sensor (tespit kaybi bile
        yok). Ariza kipinin varligini/yoklugunu ayirmak icin referans."""
        d = {}
        for adlar in cls.KAYNAKLAR.values():
            d.update(cls._sifirla(adlar))
        d.update(kw)
        return cls(**d)

    @classmethod
    def eski(cls, **kw):
        """2026-08-16 ONCESI tesis, BIT-AYNI: yalniz tespit kaybi + 1 px
        jitter vardi, olcum hatasi YOKTU. Gerileme kiyasi icin."""
        return cls.kapali(tespit_kaybi=True, jitter_px=1.0, **kw)

    @classmethod
    def tek(cls, *kaynak, **kw):
        """YALNIZ verilen kaynak(lar) acik, digerleri kapali."""
        kapa = [a for ad, alanlar in cls.KAYNAKLAR.items()
                if ad not in kaynak for a in alanlar]
        d = cls._sifirla(kapa)
        d.update(kw)
        return cls(**d)

    @classmethod
    def haric(cls, *kaynak, **kw):
        """Verilen kaynak(lar) KAPALI, digerleri acik (tek-tek sondurme)."""
        kapa = [a for ad in kaynak for a in cls.KAYNAKLAR[ad]]
        d = cls._sifirla(kapa)
        d.update(kw)
        return cls(**d)


class Algi:
    """Tespit boru hatti: kamera -> dedektor -> yasa.

    Yasanin gordugu IKI girdiyi de burasi uretir ve ikisi AYRI zaman
    damgasindan gelir:
        oku(t)     -> (cx, cy, w, h)  ESKI bir kareden (yakalama+cikarim)
        yaw_oku(t) -> iris_yaw        neredeyse ANLIK (ayri, kucuk gecikme)
    Aradaki fark yasanin LOS kestirimini kaydirir ve SAHTE LOS HIZI uretir.

    Kullanim (her sim adiminda):
        algi.kare_ver(t, avci, kadraj(avci, hx, hy, hz))
        olcum = algi.oku(t)          # None ise yasa "kayip" sayar
        yaw   = algi.yaw_oku(t)      # av.yaw YERINE yasaya bu verilir
    """

    def __init__(self, ayar=None, tohum=0):
        self.a = HataAyari() if ayar is None else ayar
        self.rnd = random.Random(tohum)
        self._yaw = []            # (t, yaw_ACILMIS) — sarma olmadan interp
        self._rp = []             # (t, roll, pitch) — yaw ile AYNI mesaj
        self._yaw_ham = None
        self._yaw_ac = 0.0
        self._yayin_v = None      # son YAYINLANAN yaw (donmus olabilir)
        self._yayin_rp = None     # son YAYINLANAN (roll, pitch)
        self._yayin_t = -1e9
        self._blok_bitis = -1e9
        self._bekleyen = []       # (t_hazir, t_yakalama, olcum|None)
        self._son_kare = -1e9
        self._son_t = None
        self._teslim = None       # (t_yakalama, cx, cy, w, h) | None
        self._yanlis_bitis = -1e9
        self._yanlis_d = (0.0, 0.0)
        self.son_yas = 0.0        # tani: teslim edilen kutunun YASI (s)
        self.yaw_yas = 0.0        # tani: yayinlanan yaw'in YASI (s)

    # ---------------- telemetri (yaw) kanali ----------------
    def _lognorm(self, med, p95):
        if med <= 0.0:
            return 0.0
        if p95 <= med:
            return med
        return self.rnd.lognormvariate(math.log(med),
                                       math.log(p95 / med) / 1.6449)

    def _yaw_ara(self, ts):
        """Yaw gecmisini ts aninda dogrusal interpolasyonla oku (ACILMIS)."""
        if ts <= self._yaw[0][0]:
            return self._yaw[0][1]
        for i in range(len(self._yaw) - 1):
            t0, y0 = self._yaw[i]
            t1, y1 = self._yaw[i + 1]
            if t0 <= ts <= t1:
                o = 0.0 if t1 - t0 < 1e-12 else (ts - t0) / (t1 - t0)
                return y0 + o * (y1 - y0)
        return self._yaw[-1][1]

    def _yaw_yaz(self, t, avci, dt):
        """Gercek tutumu kaydet, sonra YAYIN kanalini isle (donma dahil).

        ⚠ YAW, ROLL, PITCH AYNI MESAJDA gelir (ATTITUDE). Yaw donunca
        roll/pitch de DONAR — yasanin los_seviye() roll telafisi de o anda
        bayat veriyle calisir. Ayri modellemek fiziksel olarak yanlis olurdu.
        """
        yaw = avci.yaw
        if self._yaw_ham is not None:
            d = (yaw - self._yaw_ham + math.pi) % (2 * math.pi) - math.pi
            self._yaw_ac += d
        else:
            self._yaw_ac = yaw
        self._yaw_ham = yaw
        self._yaw.append((t, self._yaw_ac))
        self._rp.append((t, avci.roll, avci.pitch))
        sinir = t - self.a.yaw_gecikme_s - 0.05
        while len(self._yaw) > 2 and self._yaw[1][0] < sinir:
            self._yaw.pop(0)
            self._rp.pop(0)

        a = self.a
        # ⚠ DONMA (yaw_yas_s ile OLCULDU): tiklerin %59'unda yaw tekrar
        # ediyor, kuyrukta 7.5 s'ye varan bloklar var. Blok BOYUNCA yasanin
        # gordugu tutum sabit kalir; blok bitince TEK KAREDE sicrar — LOS
        # kestiriminde devasa bir sahte lam basamagi olusur.
        if t < self._blok_bitis:
            self.yaw_yas = t - self._yayin_t
            return
        if (a.yaw_blok_hiz > 0.0 and self._yayin_v is not None
                and self.rnd.random() < a.yaw_blok_hiz * dt):
            self._blok_bitis = t + self._lognorm(a.yaw_blok_med_s,
                                                 a.yaw_blok_p95_s)
            self.yaw_yas = t - self._yayin_t
            return
        # taze ornek gelme olasiligi p = yaw_hz*dt (adim suresinden bagimsiz)
        if a.yaw_hz > 0.0 and self._yayin_v is not None:
            if self.rnd.random() >= min(1.0, a.yaw_hz * dt):
                self.yaw_yas = t - self._yayin_t
                return
        # TAZE ornek yayinla (tasima gecikmesi + gurultu ornekle DONAR)
        ts = t - a.yaw_gecikme_s
        y = self._yaw_ara(ts)
        r, p = self._rp_ara(ts)
        if a.yaw_gurultu_deg > 0.0:
            s = math.radians(a.yaw_gurultu_deg)
            y += self.rnd.gauss(0.0, s)
            r += self.rnd.gauss(0.0, s)
            p += self.rnd.gauss(0.0, s)
        self._yayin_v = y
        self._yayin_rp = (r, p)
        self._yayin_t = t
        self.yaw_yas = 0.0

    def _rp_ara(self, ts):
        """Roll/pitch gecmisini ts aninda oku (yaw ile AYNI zaman damgasi)."""
        if ts <= self._rp[0][0]:
            return self._rp[0][1], self._rp[0][2]
        for i in range(len(self._rp) - 1):
            t0, r0, p0 = self._rp[i]
            t1, r1, p1 = self._rp[i + 1]
            if t0 <= ts <= t1:
                o = 0.0 if t1 - t0 < 1e-12 else (ts - t0) / (t1 - t0)
                return r0 + o * (r1 - r0), p0 + o * (p1 - p0)
        return self._rp[-1][1], self._rp[-1][2]

    def yaw_oku(self, t):
        """Yasaya verilecek iris_yaw: BAYAT/DONUK + gecikmeli + gurultulu."""
        if self._yayin_v is None:
            return 0.0 if not self._yaw else (
                (self._yaw[-1][1] + math.pi) % (2 * math.pi) - math.pi)
        return (self._yayin_v + math.pi) % (2 * math.pi) - math.pi

    def tutum_oku(self, t):
        """(roll, pitch) — yaw ile AYNI (bayat) ATTITUDE ornegi."""
        if self._yayin_rp is None:
            return (self._rp[-1][1], self._rp[-1][2]) if self._rp else (0.0, 0.0)
        return self._yayin_rp

    # ---------------- goruntu kanali ----------------
    def _det_suresi(self):
        """Cikarim suresi ornegi. Medyan ve p95'i AYNEN tutturan lognormal."""
        return self._lognorm(self.a.det_gecikme_s, self.a.det_gecikme_p95_s)

    def _bozup_ver(self, t, k):
        """Kadraj cikisini DEDEKTOR ciktisina cevirir (3 ve 4. kaynak)."""
        a = self.a
        cx, cy, w, h = k[0], k[1], k[2], k[3]

        # (3) KENAR YANLILIGI: off-axis aci buyudukce kutu merkeze kayar
        if a.kenar_yanlilik_kutu > 0.0 or a.kenar_gurultu_kutu > 0.0:
            eps = abs(math.degrees(math.atan((cx - CX) / F_YASA)))
            genis = max(a.kenar_doyum_deg - a.kenar_baslangic_deg, 1e-6)
            u = (eps - a.kenar_baslangic_deg) / genis
            u = max(0.0, min(1.0, u))
            if u > 0.0:
                b = max(w, h)
                if cx != CX:
                    cx -= (1.0 if cx > CX else -1.0) * a.kenar_yanlilik_kutu * b * u
                s = a.kenar_gurultu_kutu * b * u
                if s > 0.0:
                    cx += self.rnd.gauss(0.0, s)
                    cy += self.rnd.gauss(0.0, s)

        # (4) YANLIS NESNE: dusuk olasilikla kutu bambaska bir yere sicrar
        if t >= self._yanlis_bitis and a.yanlis_hiz > 0.0:
            # kare basina tehlike orani (kamera periyodu kadar)
            per = (1.0 / a.kamera_hz) if a.kamera_hz > 0.0 else 1.0 / 62.0
            if self.rnd.random() < a.yanlis_hiz * per:
                th = self.rnd.uniform(-math.pi, math.pi)
                self._yanlis_d = (a.yanlis_sapma_px * math.cos(th),
                                  a.yanlis_sapma_px * math.sin(th))
                self._yanlis_bitis = t + a.yanlis_sure_s
        if t < self._yanlis_bitis:
            cx += self._yanlis_d[0]
            cy += self._yanlis_d[1]

        # piksel jitter'i (onceden deney.py'deydi)
        if a.jitter_px > 0.0:
            cx += self.rnd.gauss(0.0, a.jitter_px)
            cy += self.rnd.gauss(0.0, a.jitter_px)
        return (cx, cy, w, h)

    def kare_ver(self, t, avci, k):
        """Bir sim adimi: telemetriyi yaz, gerekiyorsa kare yakala."""
        dt = (1.0 / 62.0) if self._son_t is None else max(t - self._son_t, 0.0)
        self._son_t = t
        self._yaw_yaz(t, avci, dt)
        a = self.a
        # kamera ornekleme (0 -> her adimda yakala)
        if a.kamera_hz > 0.0:
            if t - self._son_kare < (1.0 / a.kamera_hz) - 1e-9:
                self._hazirla(t)
                return
        self._son_kare = t

        olcum = None
        if k is not None:
            w, h = k[2], k[3]
            # tespit surekliligi: kucuk kutu -> dedektor bulamaz (BOS kare)
            if (not a.tespit_kaybi) or self.rnd.random() < tespit_olasilik(w, h):
                olcum = self._bozup_ver(t, k)
        # ⚠ BOS kare de KUYRUGA GIRER: gercekte dedektor "bulamadim" sonucunu
        # da gecikmeyle teslim eder ve yasa o an kutuyu KAYBEDER.
        self._bekleyen.append((t + a.kare_gecikme_s + self._det_suresi(),
                               t, olcum))
        self._hazirla(t)

    def _hazirla(self, t):
        """Suresi dolan sonuclari teslim et (en yenisi gecerli olur)."""
        kalan = []
        for kayit in self._bekleyen:
            if kayit[0] <= t:
                if self._teslim is None or kayit[1] >= self._teslim[0]:
                    self._teslim = (kayit[1], kayit[2])
            else:
                kalan.append(kayit)
        self._bekleyen = kalan

    def oku(self, t):
        """Yasanin o an gordugu kutu: (cx, cy, w, h) ya da None."""
        if self._teslim is None:
            self.son_yas = 0.0
            return None
        self.son_yas = t - self._teslim[0]
        return self._teslim[1]


# ══════════════════════════════════════════════════════════════════════════
#  OZ-SINAMA — tesisin ISARET ve OLCEK dogrulugu
# ══════════════════════════════════════════════════════════════════════════
def dogrula(sessiz=False):
    """Tesisin yasayla uyumunu sinar. HER TARAMADAN ONCE kosulmali.

    NEDEN VAR: bu simulatorde ust uste IKI tesis hatasi cikti ve ikisi de
    "yasada bug var" gibi gorunen SAHTE bulgu uretti:
      1) kadraj gercek DoW icselligini (FY=236) kullaniyordu; yasa ise
         F_YASA=166.6 ile kurulmus piksel bekliyor -> %42 sahte dikey hata.
      2) irtifa entegrasyonu isaret ters idi (z += vz); vz NED asagi-pozitif
         oldugu icin tirmanma komutu alcalma uretiyordu.
    Ikisi de sessizdi. Artik degil.
    """
    h = []

    class _A:
        x = y = z = 0.0
        yaw = pitch = roll = 0.0
        _hedef_yon = 0.0

    # 1) seviye + onde -> cy = CY + F*tan(TILT)
    k = kadraj(_A(), 100.0, 0.0, 0.0)
    bkl = CY + F_YASA * math.tan(math.radians(Olcum.TILT))
    if k is None or abs(k[1] - bkl) > 0.5:
        h.append("seviye hedef cy=%s, beklenen %.1f" % (k and round(k[1], 1), bkl))
    if k and abs(k[0] - CX) > 0.5:
        h.append("seviye hedef cx=%.1f, beklenen %.1f" % (k[0], CX))

    # 2) hedef SAGDA -> cx > CX ;  hedef YUKARDA -> cy kucul
    if kadraj(_A(), 50.0, 10.0, 0.0)[0] <= CX:
        h.append("hedef sagda ama cx buyumedi")
    if kadraj(_A(), 50.0, 0.0, 5.0)[1] >= kadraj(_A(), 50.0, 0.0, 0.0)[1]:
        h.append("hedef yukarda ama cy kuculmedi")

    # 3) TIRMANMA: vz<0 (NED) irtifayi ARTIRMALI
    a = Avci(x=0, y=0, z=0, yaw=0, vz_max=3.0)
    a.vx = 10.0
    for i in range(400):
        a.setpoint(10.0, 0.0, -3.0, 0.0, i / 62.0)
        a.adim(1 / 62.0, i / 62.0)
    if a.z <= 0.5:
        h.append("vz=-3 komutuna ragmen irtifa artmadi (z=%.2f)" % a.z)

    # 4) ALCALMA: vz>0 irtifayi AZALTMALI
    b = Avci(x=0, y=0, z=0, yaw=0, vz_max=3.0)
    b.vx = 10.0
    for i in range(400):
        b.setpoint(10.0, 0.0, +3.0, 0.0, i / 62.0)
        b.adim(1 / 62.0, i / 62.0)
    if b.z >= -0.5:
        h.append("vz=+3 komutuna ragmen irtifa azalmadi (z=%.2f)" % b.z)

    # 5) YAW: komut edilen yona doner
    c = Avci(x=0, y=0, z=0, yaw=0.0, yaw_rate_max=120.0)
    for i in range(200):
        c.setpoint(10.0, 0.0, 0.0, math.radians(60.0), i / 62.0)
        c.adim(1 / 62.0, i / 62.0)
    if abs(math.degrees(c.yaw) - 60.0) > 5.0:
        h.append("yaw 60° komutuna gitmedi (%.1f°)" % math.degrees(c.yaw))

    # ══════════════════════════════════════════════════════════════════════
    #  OLCUM HATASI SINAMALARI (2026-08-16)
    #  Ucuncu sahte bulgu tam da bu blogun YOKLUGUNDAN cikti: tesis olcum
    #  hatasini uretemedigi icin "PN cok daha iyi" dedi, oyunda fark yoktu.
    # ══════════════════════════════════════════════════════════════════════
    DT = 1.0 / 62.0

    class _Y:                       # yaw'i sabit hizla donen sanal avci
        x = y = z = 0.0
        pitch = roll = 0.0
        _hedef_yon = 0.0
        yaw = 0.0

    # 6) KAPALI ayar ESKI tesisi BIT-AYNI vermeli (gerileme kilidi).
    #    Bu tutmazsa eski tum olcumler gecersizlesir.
    al = Algi(HataAyari.kapali(), tohum=1)
    _y = _Y()
    kotu6 = 0
    for i in range(60):
        t = i * DT
        _y.yaw = math.radians(20.0) * t
        k = kadraj(_y, 100.0, 0.0, 0.0)
        al.kare_ver(t, _y, k)
        o = al.oku(t)
        if k is None or o is None:
            kotu6 += 1
        elif abs(o[0] - k[0]) > 1e-9 or abs(o[1] - k[1]) > 1e-9:
            kotu6 += 1
        elif abs(al.yaw_oku(t) - _y.yaw) > 1e-9:
            kotu6 += 1
        elif al.tutum_oku(t) != (_y.roll, _y.pitch):
            kotu6 += 1
    if kotu6:
        h.append("HataAyari.kapali() eski tesisi vermiyor (%d/60 kare)" % kotu6)

    # 7) YAW OKUMA GECIKMESI: olculen yaw, gercekten w*gecikme kadar GERIDE.
    #    (donma ve gurultu kapali — burada YALNIZ tasima gecikmesi sinaniyor)
    a7 = HataAyari.tek("yaw", yaw_gurultu_deg=0.0, yaw_gecikme_s=0.040,
                       yaw_hz=0.0, yaw_blok_hiz=0.0)
    al = Algi(a7, tohum=2)
    w7 = math.radians(50.0)
    _y = _Y()
    fark7 = None
    for i in range(60):
        t = i * DT
        _y.yaw = w7 * t
        al.kare_ver(t, _y, kadraj(_y, 100.0, 0.0, 0.0))
        if t > 0.5:
            fark7 = _y.yaw - al.yaw_oku(t)
    bkl7 = w7 * 0.040
    if fark7 is None or abs(fark7 - bkl7) > math.radians(0.2):
        h.append("yaw gecikmesi %.3f rad, beklenen %.3f" % (fark7 or -1, bkl7))

    # 8) KUTU YASI: teslim edilen kutu GECMISTEN gelmeli.
    #    beklenen ortalama = kare_gecikme + det_medyan + yarim kamera periyodu
    al = Algi(HataAyari.tek("gecikme"), tohum=3)
    _y = _Y()
    yaslar = []
    for i in range(200):
        t = i * DT
        _y.yaw = 0.0
        al.kare_ver(t, _y, kadraj(_y, 100.0, 0.0, 0.0))
        if al.oku(t) is not None and t > 0.3:
            yaslar.append(al.son_yas)
    ort8 = sum(yaslar) / max(len(yaslar), 1)
    bkl8 = (HataAyari.kare_gecikme_s + HataAyari.det_gecikme_s
            + 0.5 / HataAyari.kamera_hz)
    if not yaslar or abs(ort8 - bkl8) > 0.015:
        h.append("kutu yasi ort %.3f s, beklenen ~%.3f s" % (ort8, bkl8))

    # 9) ⭐ ASIL ARIZA KIPI: yasanin LOS'u, IKI KANALIN ZAMAN UYUMSUZLUGU
    #    kadar truth'tan sapmali:
    #      LOS_yasa - LOS_truth = yaw_hizi * (kutu_yasi - yaw_yasi - gecikme)
    #    Arac SABIT (sadece donuyor), hedef SABIT -> LOS_truth = 0, yani
    #    olculen farkin TAMAMI hatadir.
    #    ⚠ ESKI tesiste bu fark TANIMI GEREGI 0'di; sinama tam onu yakalar.
    #    ⚠ TILT gecici olarak 0: 25° tilt azimutu 1/cos(25°) kadar OLCEKLER
    #    (eps = atan(tan(yaw)/cos TILT)) ve tahmini kirletir. Burada sinanan
    #    ZAMAN UYUMSUZLUGU, projeksiyon degil.
    a9 = HataAyari.tek("gecikme", "yaw", yaw_gurultu_deg=0.0)
    al = Algi(a9, tohum=4)
    w9 = math.radians(40.0)
    _y = _Y()
    kotu9 = 0; ornek9 = 0; enb9 = 0.0
    _tilt_yedek = Olcum.TILT
    try:
        Olcum.TILT = 0.0
        for i in range(400):
            t = i * DT
            _y.yaw = w9 * t
            al.kare_ver(t, _y, kadraj(_y, 100.0, 0.0, 0.0))
            o = al.oku(t)
            if o is None or t < 0.4:
                continue
            los_yasa = al.yaw_oku(t) + math.atan((o[0] - CX) / F_YASA)
            fark = (los_yasa + math.pi) % (2 * math.pi) - math.pi   # truth = 0
            bkl = w9 * (al.son_yas - al.yaw_yas - a9.yaw_gecikme_s)
            ornek9 += 1
            enb9 = max(enb9, abs(math.degrees(fark)))
            if abs(fark - bkl) > math.radians(0.3):
                kotu9 += 1
    finally:
        Olcum.TILT = _tilt_yedek
    if ornek9 < 50 or kotu9:
        h.append("LOS hatasi mekanizmasi tutmadi (%d/%d ornek sapti)"
                 % (kotu9, ornek9))
    if enb9 < 0.5:
        h.append("zaman uyumsuzlugu LOS hatasi URETMIYOR (enb %.2f°)" % enb9)

    # 10) KENAR YANLILIGI: kadraj kenarinda kutu MERKEZE dogru kayar,
    #     eksende hic kaymaz.
    al = Algi(HataAyari.tek("kenar", kenar_gurultu_kutu=0.0), tohum=5)
    kutu = (CX + 300.0, CY, 12.0, 6.0)          # eps = atan(300/166.6) = 61°
    o10 = al._bozup_ver(0.0, kutu)
    if not (CX < o10[0] < kutu[0]):
        h.append("kenar yanliligi merkeze dogru kaydirmadi (%.1f)" % o10[0])
    o10b = al._bozup_ver(0.0, (CX, CY, 12.0, 6.0))
    if abs(o10b[0] - CX) > 1e-9:
        h.append("eksendeki hedefte kenar yanliligi olusmus (%.2f)" % o10b[0])

    # 11) YANLIS NESNE: sicrama buyuklugu OLCULEN 153 px, ve SONA ERIYOR.
    al = Algi(HataAyari.tek("yanlis", yanlis_hiz=1e9), tohum=6)
    o11 = al._bozup_ver(0.0, (CX, CY, 12.0, 6.0))
    d11 = math.hypot(o11[0] - CX, o11[1] - CY)
    if abs(d11 - HataAyari.yanlis_sapma_px) > 1.0:
        h.append("yanlis nesne sapmasi %.0f px, beklenen %.0f"
                 % (d11, HataAyari.yanlis_sapma_px))
    al.a.yanlis_hiz = 0.0                       # yeni olay olmasin
    o11b = al._bozup_ver(HataAyari.yanlis_sure_s + 0.01, (CX, CY, 12.0, 6.0))
    if math.hypot(o11b[0] - CX, o11b[1] - CY) > 1.0:
        h.append("yanlis nesne olayi bitmedi")

    # 12) YAW DONMASI, OLCULEN dagilima uymali (kopru_tani `yaw_yas_s`):
    #     bayat tik orani ~%59, yas p90 ~1.2 s, p95 ~2.3 s, MAX ~7.5 s.
    #     ⚠ ASIL ONEMLI OLAN BU: 25 ms'lik kutu gecikmesinin yanina
    #     SANIYELER suren donuk yaw geliyor.
    al = Algi(HataAyari.tek("yaw", yaw_gurultu_deg=0.0), tohum=7)
    _y = _Y()
    yas12 = []
    for i in range(int(600.0 * 62)):            # 600 s — kuyrugu gorebilmek icin
        t = i * DT
        _y.yaw = math.radians(30.0) * t
        al.kare_ver(t, _y, None)
        yas12.append(al.yaw_yas)
    yas12.sort()
    n12 = len(yas12)
    bayat = sum(1 for x in yas12 if x > 1e-9) / n12
    p90 = yas12[int(0.90 * n12)]
    p95 = yas12[int(0.95 * n12)]
    if not (0.45 <= bayat <= 0.72):
        h.append("bayat yaw orani %.2f, olculen ~0.59" % bayat)
    if not (0.5 <= p90 <= 2.2):
        h.append("yaw yasi p90 %.2f s, olculen ~1.17 s" % p90)
    if not (1.0 <= p95 <= 4.0):
        h.append("yaw yasi p95 %.2f s, olculen ~2.31 s" % p95)
    if yas12[-1] < 3.0:
        h.append("yaw donma kuyrugu yok (max %.2f s, olculen 7.47 s)" % yas12[-1])

    if not sessiz:
        print("  TESIS OZ-SINAMASI: %s" % ("TAMAM (12/12)" if not h else "KALDI"))
        for x in h:
            print("    ! " + x)
    return h


if __name__ == "__main__":
    dogrula()

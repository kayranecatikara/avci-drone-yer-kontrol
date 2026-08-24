# -*- coding: utf-8 -*-
"""
================================================================================
  DEVIR TEZGAHI  --  GPS -> GORSEL devrinin ILK SANIYELERI, KAPALI CEVRIM
================================================================================
SORU (kullanici, 2026-08-17)
--------------------------------------------------------------------------------
  "faza gectiginde dikeyi (irtifayi) tutmuyor, yatayda (x ekseninde) de ayni."

sim/dikey.py TERMINAL dikeyini olcuyor ve yatay kanali BILEREK iyi tutuyor.
Bu dosya TAM TERSI soruyu sorar: devrin ILK 3 SANIYESINDE gorsel yasanin
KENDISI (bbox_ibvs.komut, TUTUS dali) dikeyi ve boyunayi tutuyor mu?

⚠ GERCEK YASA CAGRILIR. bbox_ibvs.komut() import edilip cagriliyor; burada
  bulunan her sey oyunda da gecerlidir.
⚠ HICBIR CANLI DOSYA DEGISTIRILMEZ. tesis.py / trail.py / dikey.py / kopru
  SALT OKUNUR. Aday yamalar burada cfg VEKILI ile modellenir; ancak
  tezgahta kazandiktan sonra gercek dosyaya env kapisiyla girer.

--------------------------------------------------------------------------------
 BASLANGIC KOSULU  --  UYDURULMADI, 295 GERCEK DEVIRDEN OLCULDU
--------------------------------------------------------------------------------
arac/devir_sicrama.py, kaynak: veri/hedef_iz/*.csv (truth, ~30 Hz) x
kopru/gazebo_kaynak/logs/bbox_ibvs_*.csv (yasa ici sinyaller), ayni
time.monotonic saati uzerinden eslestirilmis. 2026-08-17, ayna duzeltmesi
SONRASI kayitlar. Taze paket orani %100 (donmus paket yok).

    menzil (truth)        p10  7.95   medyan 13.87   p90 17.69   m
    dikey dz-hz           p10 -1.74   medyan -1.48   p90 -1.13   m  (ALTTAYIZ)
    kendi yatay hizimiz                medyan 19.58                m/s
    hedefin gercek hizi                medyan 18.02                m/s
    govde pitch                        medyan -10.75               derece
    kerteriz hatasi                    medyan  -1.9                derece
    ff_hiz (hiz_I sicak baslangici) - hedefin GERCEK hizi:
                          p10 -8.56   medyan -0.50   p90 +1.17    m/s
                          %62'si hedefin hizindan DUSUK, %33'u |hata|>3 m/s

⚠ SON SATIR BU DOSYANIN VAR OLMA SEBEBIDIR: sicak baslangic kotu olan
  fazlarda saha EN YAKIN MENZILI 11.85 m, iyi olanlarda 3.95 m (n=304,
  devir menzili 12-18 m'ye sabitlendiginde 12.01 vs 3.04 m; hedefin donus
  hizi sabitlendiginde de etki KALIYOR -> curutulemedi).

--------------------------------------------------------------------------------
 TEZGAH KUSURLARI  --  hangileri KAPATILDI, hangileri ACIK KALDI
--------------------------------------------------------------------------------
KAPATILDI (sim/dikey.py'nin bulduklari devralindi):
  (7) govde pitch trimi  -> AvciD(pitch_trim=-13.3 deg). DIKEY SORU ICIN
      HAYATI: nisanin dunya yukselisi W0 = piksel_elev(CY_NISAN) + pitch.
      Pitch modellenmezse yasanin dikey DENGE NOKTASI 13 derece yanlis olur
      ve tezgah "dikey sorun yok" der.
  (8) dikey ivme siniri  -> AvciD(az_max=3.0 m/s^2, OLCULEN p95)
  (b) kutu boyutu olcegi + OU gurultusu -> trail.Kutu

ACIK KALDI (sonuclari bu yonde okuyun):
  (i)  ARKA PLAN: tespit olasiligi yalnizca kutu boyutuna bakiyor. Gercekte
       hedefin ALTINDAN bakmak gokyuzu arka plani verir. Tezgah bunu
       modellemedigi icin "ofseti kaldir" secenegini YAPISAL OLARAK KAYIRIR.
       --arka_plan ile ceza verilebilir (1.0 = ceza yok); yamanin kendini
       hangi cezada amorti ettigi TARANIR.
  (ii) MENZIL VEKIL YANLILIGI: yasa menzili 202.6/boyut ile kestiriyor ve
       SAHADA +4.60 m (p90 +8.19) YUKARI yanli olcum var. Tezgahtaki kutu
       olcegi trail.Kal'dan geliyor; yanlilik birebir ayni olmayabilir.
  (iii) Hedefin GPS fazindaki davranisi modellenmiyor: devir ANINDAN
       basliyoruz. "Devir esigini degistir" adayi bu tezgahta SINANAMAZ.

CALISTIR
    python sim/devir.py                    tek kosu, zaman serisi
    python sim/devir.py --ab               A/B: taban vs adaylar
    python sim/devir.py --ab --n 240       daha buyuk ornek
    python sim/devir.py --ab --arka_plan 0.6
================================================================================
"""
import os
import sys
import math
import random
import argparse
import statistics as st

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "kopru", "gazebo_kaynak"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ══════════════════════════════════════════════════════════════════════════
#  ⚠⚠ UCULAN AYAR  --  arac/recete_taban.json "TABAN_HERSEY_KAPALI"
# ══════════════════════════════════════════════════════════════════════════
# TEZGAH KUSURU OLURDU: bbox_ibvs.Cfg env'i IMPORT ANINDA okur. Env
# verilmezse tezgah PN_N=1.6 ve DPP KAPALI ile, yani SAHADA UCULMAYAN bir
# yasa ile kosar. Ilk denememde tam bu oldu (menzil 9.8 -> 39 m aciliyordu).
# Sahada ne kosuldugu loglardan DOGRULANDI: pn_n=0, w_talep DOLU (DPP acik),
# v_los - hiz_I = 7.0 m/s @ R_kutu 21.8 m  =>  DPP_KR*DPP_RSAT = 0.7*10.
UCULAN_ENV = {
    "AVCI_IBVS_PN": "0", "AVCI_DPP_K": "1.4", "AVCI_DPP_KR": "0.7",
    "AVCI_DPP_RSET": "6.0", "AVCI_DPP_FF": "1.0", "AVCI_IBVS_CONF": "0.25",
    "AVCI_ACCEL_SPLIT": "0", "AVCI_IBVS_TERM_DIKEY": "0",
    "AVCI_IBVS_DIKEY_ROLL": "0", "AVCI_IBVS_DONUS_BUTCE": "0",
    "AVCI_IBVS_ARAC_TAU": "0",
    # ⚠⚠ 2026-08-17, KAPILAR VARSAYILAN ACIK OLDUKTAN SONRA ZORUNLU OLDU.
    #   D1/Y1 ucus A/B'sini kazandi ve bbox_ibvs.Cfg varsayilani ACIK yapildi.
    #   BU IKI SATIR OLMAZSA `T0_taban` adayi (hic override vermeyen aday)
    #   sessizce ACIK kapilarla kosar, yani TABAN ARTIK TABAN OLMAZ ve tum
    #   A/B farklari 0'a yakinsar. Tezgah "yama etkisiz" diye SAHTE bir
    #   bulgu uretirdi. Taban BILEREK eski davranista sabitlenir; adaylar
    #   kapilari CfgVekil ile acikca ACAR.
    "AVCI_IBVS_DIKEY_UFUK": "0", "AVCI_IBVS_HIZ_SICAK": "-1",
    "AVCI_IBVS_KVZ": "0.5",
}
for _k, _v in UCULAN_ENV.items():
    os.environ.setdefault(_k, _v)

import tesis as T                                                   # noqa: E402
from tesis import Olcum, tespit_olasilik, HataAyari                  # noqa: E402
from trail import Kutu                                              # noqa: E402
from dikey import AvciD, HedefD, Dik                                # noqa: E402
from control.guidance import bbox_ibvs as IB                        # noqa: E402


# ══════════════════════════════════════════════════════════════════════════
#  OLCULEN DEVIR DURUMU  (arac/devir_sicrama.py, n=295-304)
# ══════════════════════════════════════════════════════════════════════════
class Devir:
    R0_MED = 13.9          # m   truth menzil, devir ani
    R0_P10, R0_P90 = 7.95, 17.69
    DZ0_MED = -1.48        # m   dz - hz  (- = BIZ ALTTAYIZ)
    DZ0_SD = 0.25
    V_KENDI = 19.58        # m/s kendi yatay hizimiz
    KERT_MED = -1.9        # derece; hiz vektoru ile LOS arasi
    # ff_hiz hatasi (hiz_I sicak baslangici - hedefin gercek hizi), OLCULEN
    # dagilim: %62 negatif, p10 -8.56, medyan -0.50, p90 +1.17.
    # Iki bilesenli model: %67 "iyi" (N(-0.2, 0.9)), %33 "kotu" (U(-10,-3)).
    # ⚠ Bu bir MODEL; ham dagilimin p10/medyan/p90'ini tutturuyor.
    FF_KOTU_ORAN = 0.33
    FF_IYI_MU, FF_IYI_SD = -0.2, 0.9
    FF_KOTU_LO, FF_KOTU_HI = -10.0, -3.0


def ff_hatasi(rnd):
    if rnd.random() < Devir.FF_KOTU_ORAN:
        return rnd.uniform(Devir.FF_KOTU_LO, Devir.FF_KOTU_HI)
    return rnd.gauss(Devir.FF_IYI_MU, Devir.FF_IYI_SD)


# ══════════════════════════════════════════════════════════════════════════
#  (10) YENI TEZGAH KUSURU  --  KUTU BOYUTU %40 BUYUK
# ══════════════════════════════════════════════════════════════════════════
# trail.Kutu + tesis.kadraj carpimi TAM 202.6 px*m veriyor (yasanin
# MENZIL_PX_M sabiti). SAHADA OLCULEN (29718 kare, bbox_ibvs boyut x truth
# menzil, ayni monotonic saat):
#     R  5- 8 m -> 117    R  8-12 m -> 135
#     R 12-16 m -> 146    R 16-22 m -> 152      genel medyan 145
# yani tezgahin kutusu %40 BUYUK. IKI SONUCU VAR ve ikisi de bu dosyanin
# sorusunu bozar:
#   (a) TERMINAL MANDALI (boyut>=25) tezgahta R=8.1 m'de, sahada R=5.8 m'de
#       kapaniyor -> tezgah TUTUS dalini erken bitirip olcumu kaciriyor.
#   (b) Yasanin menzil VEKILI (202.6/boyut) tezgahta YANSIZ, sahada
#       1.40 KAT YUKARI yanli -> DPP menzil dongusu ve dikey rampa yanlis
#       menzille kosar.
# DUZELTME: kutu w/h'si sabit KUTU_CARPIM ile kisilir.
# ⚠ ACIK KALAN: saha carpimi menzille degisiyor (117 -> 152); tek sabit
#   carpim bu egilimi modellemiyor. Yakin menzilde tezgah hala biraz
#   iyimser kalir.
KUTU_CARPIM = 145.0 / 202.6        # 0.7157


class KutuD:
    """trail.Kutu + saha kalibreli boyut carpimi (bkz. kusur 10)."""

    def __init__(self, tohum=0, gurultu=True, carpim=KUTU_CARPIM):
        self._k = Kutu(tohum=tohum, olcek=True, gurultu=gurultu)
        self.carpim = carpim

    def __call__(self, av, hx, hy, hz, dt):
        r = self._k(av, hx, hy, hz, dt)
        if r is None:
            return None
        cx, cy, w, h, m = r
        return cx, cy, max(w * self.carpim, 1.0), max(h * self.carpim, 1.0), m


# ══════════════════════════════════════════════════════════════════════════
#  AVCI  --  AvciD + TUTUM DINAMIGI  (bu dosyanin bulduğu 9. tezgah kusuru)
# ══════════════════════════════════════════════════════════════════════════
class AvciDev(AvciD):
    """AvciD + birinci mertebe PITCH/ROLL dinamigi.

    ⚠ (9) YENI TEZGAH KUSURU — DIKEY SORU ICIN OLDURUCU.
    tesis.Avci pitch'i ANLIK ivmeden ANINDA turetiyor (tutum dinamigi yok).
    Yasa kare kare ivme komutu degistirdigi icin tezgah pitch'i +12 ile
    -39 derece arasinda ZIPLATIYORDU. Nisanin dunya yukselisi
    W0 = piksel_elev(CY_NISAN) + pitch oldugu icin bu, dikey hata terimine
    dogrudan +-25 derecelik SAHTE gurultu enjekte eder ve tezgahi dikey
    soruda kullanilmaz yapar.

    OLCULEN gercek (bbox_ibvs_*.csv iris_pitch_deg, gorsel fazlarin ilk
    kareleri, n=280):  p10 -16.2   medyan -10.8   p90 -3.0   (yayilim ~5 deg)
    Sahada pitch YAVAS ve DAR. Model: tau ile alcak geciren + emniyet clamp.
    tau, olculen yayilimi tutturacak sekilde secildi (asagida dogrulanir).
    """
    PITCH_TAU = 0.45          # s   (kalibrasyon: asagidaki tutum_dogrula())
    ROLL_TAU = 0.30           # s
    PITCH_CLAMP = math.radians(40.0)

    def adim(self, dt, t):
        p0, r0 = self.pitch, self.roll
        super().adim(dt, t)
        a = min(1.0, dt / max(self.PITCH_TAU, 1e-6))
        b = min(1.0, dt / max(self.ROLL_TAU, 1e-6))
        self.pitch = max(-self.PITCH_CLAMP,
                         min(self.PITCH_CLAMP, p0 + (self.pitch - p0) * a))
        self.roll = r0 + (self.roll - r0) * b


# ══════════════════════════════════════════════════════════════════════════
#  ADAY YAMALAR  --  cfg VEKILI (gercek dosya DEGISTIRILMEDEN modellenir)
# ══════════════════════════════════════════════════════════════════════════
class CfgVekil:
    """IB.Cfg'yi sarar; yalniz verilen alanlari degistirir.

    ⚠ komut() cfg'den OKUR, YAZMAZ -> vekil guvenli.
    ⚠ CY_NISAN'i KARE KARE degistirmek, gercek koddaki nisan_cy() kapisiyla
      MATEMATIKSEL OLARAK AYNI SEYDIR (komut() cy_nisan'i yalniz
      nisan_cy(iris_pitch, boyut, cfg) uzerinden alir ve eps_elev'de
      kullanir). Yamayi gercek dosyaya tasirken nisan_cy() icine girecek.
    """

    def __init__(self, **kw):
        self._kw = kw

    def __getattr__(self, ad):
        if ad in self._kw:
            return self._kw[ad]
        return getattr(IB.Cfg, ad)


def nisan_ufuk(pitch, ufuk_elev_deg=0.0):
    """ADAY V1 -- nisanin DUNYA yukselisini sabitle (varsayilan: UFUK).

    Mevcut yasa: nisan GOVDEYE sabit piksel (CY_NISAN=301). Nisanin dunya
    yukselisi W0 = piksel_elev(301) + pitch = 4.888 + pitch. Pitch -10.75
    iken W0 = -5.86 derece, yani yasa hedefi 5.86 derece ALTINDA tutmak
    ISTIYOR -> denge noktasi D* = -R*tan(W0) = +R*0.1026, R=14 m'de
    BIZ HEDEFIN 1.4 m USTUNDE. Ustelik hizlanirken pitch daha da asagi
    gidiyor ve denge YUKARI kaciyor (pozitif geri besleme).

    Bu yama W0'i sabitler: cy_nisan = elev_piksel(W_istenen - pitch).
    W_istenen = 0 -> ES IRTIFA, her menzilde D* = 0 ve pitch kuplaji YOK.
    """
    return IB.elev_piksel(math.radians(ufuk_elev_deg) - pitch, IB.Cfg)


ADAYLAR = {
    "T0_taban":      dict(),
    "V1_ufuk0":      dict(ufuk=0.0),
    "V1b_ufuk2":     dict(ufuk=2.0),        # 2 derece ALTINDA kal (gokyuzu payi)
    "V2_hizsicak":   dict(hiz_pay=1.5),
    "V3_ufuk+hiz":   dict(ufuk=0.0, hiz_pay=1.5),
    "V4_termdikey":  dict(term_dikey=17.0),  # depoda YAZILI mevcut aday
    "V5_dikeyroll":  dict(dikey_roll=True),
    # ⚠ V6/V7: DENGE NOKTASI DUZELDIKTEN SONRA yetki artirmak.
    #   MEMORY dersi: AVCI_ACCEL_SPLIT TEK BASINA gorsel fazi KOTULESTIRDI
    #   (|dz| 1.12 -> 1.41 m) cunku acik ivme degil YANLIS DENGE idi; daha
    #   cok yetki araci yanlis dengeye daha HIZLI goturuyordu. Denge V1 ile
    #   duzeldiginde ayni yetkinin isareti DEGISMELI. Bu sinama o dersi test
    #   eder: degismezse V1'in "denge" aciklamasi ZAYIFLAR.
    "V6_ufuk+hiz+kvz": dict(ufuk=0.0, hiz_pay=1.5, k_vz=0.9),
    "V6b_kvz_tek":     dict(k_vz=0.9),
}
# ⚠ AVCI_ACCEL_SPLIT BU TEZGAHTA SINANAMAZ ve bilerek aday listesinde YOK.
#   Sebep: ayrik tavan run_bbox_ibvs'in limit_acceleration cagrisinda,
#   komut()'ta DEGIL. Tezgahin araci (tesis.Avci) yatay ivmeyi hypot(dvx,dvy)
#   uzerinden, dikeyi ise ayri (vz_max / AvciD.az_max) kisiyor -- yani
#   tezgah ZATEN AYRIK. Buraya bir "split" adayi koymak, hicbir sey
#   degistirmeyen bir kapiyi "etkisiz" ilan eden SAHTE BIR BULGU uretirdi.


# ══════════════════════════════════════════════════════════════════════════
#  TEK KOSU
# ══════════════════════════════════════════════════════════════════════════
def kosu(aday="T0_taban", senaryo="duz", tohum=0, sure=6.0, dt=1.0 / 62.0,
         R0=None, dz0=None, aspect0=None, arka_plan=1.0, kayit=False,
         gurultu=True, hata=None):
    """Devir anindan baslayan tek gorsel faz. -> olcut sozlugu."""
    p = ADAYLAR[aday]
    rnd = random.Random(tohum * 7717 + 11)
    if hata is None:
        hata = HataAyari()

    hed = HedefD(senaryo)
    hx, hy, hz, hvx, hvy, _ = hed.durum()
    hdg = math.atan2(hvy, hvx)

    if R0 is None:
        R0 = max(6.0, rnd.gauss(Devir.R0_MED, 3.6))
    if dz0 is None:
        dz0 = rnd.gauss(Devir.DZ0_MED, Devir.DZ0_SD)
    if aspect0 is None:
        aspect0 = abs(rnd.gauss(0.0, 14.0))     # olculen yanal/boyuna orani
    yatay0 = math.sqrt(max(R0 ** 2 - dz0 ** 2, 1.0))
    yon = hdg + math.pi + math.radians(aspect0)

    av = AvciDev(x=hx + yatay0 * math.cos(yon), y=hy + yatay0 * math.sin(yon),
               z=hz + dz0, yaw=0.0,
               max_accel=IB.Cfg.MAX_ACCEL, v_max=IB.Cfg.V_TOPLAM_MAX,
               vz_max=IB.Cfg.VZ_MAX, yaw_rate_max=IB.Cfg.YAW_RATE_MAX_DEG,
               pitch_trim=Dik.PITCH_TRIM, az_max=Dik.AZ_MAX)
    av.yaw = math.atan2(hy - av.y, hx - av.x) + math.radians(Devir.KERT_MED)
    av.vx = Devir.V_KENDI * math.cos(av.yaw)
    av.vy = Devir.V_KENDI * math.sin(av.yaw)

    # ── SICAK BASLANGIC: OLCULEN ff_hiz hatasiyla ──
    hiz_I = max(0.0, Olcum.HEDEF_HIZ + ff_hatasi(rnd))
    pay = p.get("hiz_pay")
    if pay is not None:
        # ADAY V2: kendi hizimizdan (KENDI sensorumuz, canli GPS DEGIL) taban
        hiz_I = max(hiz_I, math.hypot(av.vx, av.vy) - pay)
    hiz_I = min(hiz_I, IB.Cfg.I_MAX)

    kutu = KutuD(tohum=tohum, gurultu=gurultu)
    kuyruk = []                       # goruntu boru hatti gecikmesi
    gecikme = hata.kare_gecikme_s + hata.det_gecikme_s
    t = 0.0
    son_yasa_t = -1e9
    kayip = 0
    terminal = False
    los_onceki = [None, None]
    los_hiz = [0.0, 0.0]
    psi_v = None
    en_yakin = 1e9
    iz = []
    dz_t = {}
    kap_t = {}
    kadraj_ic = [0, 0]

    while t < sure:
        hed.adim(dt)
        hx, hy, hz, hvx, hvy, _ = hed.durum()
        hdg = math.atan2(hvy, hvx)
        av._hedef_yon = hdg
        k = kutu(av, hx, hy, hz, dt)
        kadraj_ic[0 if k is None else 1] += 1
        if k is not None and arka_plan < 1.0:
            # ARKA PLAN CEZASI (bkz. dosya basi, acik kusur i)
            el = math.atan2(hz - av.z, math.hypot(hx - av.x, hy - av.y))
            u = max(0.0, min(1.0, 0.5 - el / math.radians(10.0)))
            if rnd.random() > (1.0 - u * (1.0 - arka_plan)):
                k = None
        if k is not None:
            pk = tespit_olasilik(k[2], k[3]) if gurultu else 1.0
            if rnd.random() < pk:
                kuyruk.append((t + gecikme, k))

        # TRUTH olcutleri (her adimda)
        R = math.dist((av.x, av.y, av.z), (hx, hy, hz))
        en_yakin = min(en_yakin, R)
        for m in (0.5, 1.0, 1.5, 2.0, 3.0, 4.0):
            if m not in dz_t and t >= m:
                dz_t[m] = av.z - hz
                kap_t[m] = R
        if kayit:
            iz.append((t, R, av.z - hz, math.degrees(av.pitch),
                       math.hypot(av.vx, av.vy), av.vz))

        # yasa hizinda calis
        if t - son_yasa_t < 1.0 / hata.yasa_hz - 1e-9:
            av.adim(dt, t)
            t += dt
            continue
        ydt = t - son_yasa_t if son_yasa_t > -1e8 else 1.0 / hata.yasa_hz
        son_yasa_t = t

        taze = None
        while kuyruk and kuyruk[0][0] <= t:
            taze = kuyruk.pop(0)[1]
        if taze is None:
            kayip += 1
            if kayip >= 20:
                break
            av.adim(dt, t)
            t += dt
            continue
        kayip = 0
        cx, cy, w, h, _m = taze
        boyut = math.sqrt(w * h)

        # atalet LOS hizlari (yasanin bekledigi girdi)
        _az = av.yaw + math.atan((cx - IB.Cfg.CX_NISAN) / T.FX)
        _el = IB.piksel_elev(cy, IB.Cfg) + av.pitch
        if los_onceki[0] is not None and ydt > 1e-6:
            d = (_az - los_onceki[0] + math.pi) % (2 * math.pi) - math.pi
            los_hiz[0] = 0.4 * (d / ydt) + 0.6 * los_hiz[0]
            los_hiz[1] = 0.4 * ((_el - los_onceki[1]) / ydt) + 0.6 * los_hiz[1]
        los_onceki = [_az, _el]

        if not terminal and boyut >= IB.Cfg.TERMINAL_BOYUT:
            terminal = True

        # ── ADAY YAMASI: cfg vekili ──
        kw = {}
        if p.get("ufuk") is not None:
            # ⚠ 2026-08-17: yama ARTIK GERCEK DOSYADA (bbox_ibvs.Cfg.DIKEY_UFUK
            #   + nisan_cy). Tezgah da GERCEK KAPIYI kullanir; boylece
            #   "tezgahta calisti ama koda baska turlu girdi" riski KALKAR.
            #   Eski vekil yol (CY_NISAN'i kare kare yazmak) nisan_ufuk()'ta
            #   duruyor ve dogrulama testinde ikisinin AYNI cy'yi verdigi
            #   sinaniyor (tests/test_ibvs_dikey.py).
            kw["DIKEY_UFUK"] = True
            kw["UFUK_ELEV_DEG"] = p["ufuk"]
        if p.get("term_dikey"):
            kw["TERM_DIKEY_M"] = p["term_dikey"]
        if p.get("dikey_roll"):
            kw["DIKEY_ROLL"] = True
        if p.get("k_vz"):
            kw["K_VZ"] = p["k_vz"]
        cfg = CfgVekil(**kw) if kw else IB.Cfg

        vx, vy, vz, yaw_cmd, hiz_I, tani = IB.komut(
            cx, cy, w, h, av.yaw, hiz_I, ydt, cfg, terminal,
            tuple(los_hiz), av.pitch, av.vz, None, av.roll, av.yaw_hizi,
            psi_v)
        psi_v = tani.get("psi_v", psi_v)
        av.setpoint(vx, vy, vz, yaw_cmd, t)
        av.adim(dt, t)
        t += dt

    # ── OLCUTLER ──
    hx, hy, hz, hvx, hvy, _ = hed.durum()
    out = {"en_yakin": en_yakin, "sure": t, "terminal": terminal,
           "kadraj": kadraj_ic[1] / max(sum(kadraj_ic), 1), "iz": iz}
    for m in (0.5, 1.0, 1.5, 2.0, 3.0, 4.0):
        out["dz%.1f" % m] = dz_t.get(m, float("nan"))
        out["R%.1f" % m] = kap_t.get(m, float("nan"))
    return out


# ══════════════════════════════════════════════════════════════════════════
#  A/B
# ══════════════════════════════════════════════════════════════════════════
SENARYO = ("duz", "don8", "don20", "oval")


def _med(v):
    v = [x for x in v if x == x]
    return st.median(v) if v else float("nan")


def ab(n=160, sure=6.0, arka_plan=1.0, adaylar=None, gurultu=True):
    adaylar = adaylar or list(ADAYLAR)
    print("=" * 96)
    print("DEVIR TEZGAHI A/B  --  n=%d kosu/aday, senaryo=%s, arka_plan_cezasi=%.2f"
          % (n, "/".join(SENARYO), arka_plan))
    print("=" * 96)
    print("  olcut: dz = bizim irtifa - hedefin irtifasi  (+ = BIZ USTTE, 0 = ES IRTIFA)")
    print("         devir aninda dz0 = %.2f m (OLCULEN)" % Devir.DZ0_MED)
    print()
    bas = ("%-15s" % "aday" + "".join("%8s" % s for s in
           ("dz@1s", "dz@2s", "dz@3s", "|dz|@2s", "|dz|@3s", "R@2s", "R@3s",
            "enyakin", "vurus%", "kadraj%")))
    print(bas)
    print("-" * len(bas))
    tab = {}
    for ad in adaylar:
        R = []
        for i in range(n):
            sen = SENARYO[i % len(SENARYO)]
            R.append(kosu(ad, senaryo=sen, tohum=i, sure=sure,
                          arka_plan=arka_plan, gurultu=gurultu))
        vur = 100.0 * sum(1 for r in R if r["en_yakin"] < 0.9) / len(R)
        sat = dict(
            dz1=_med([r["dz1.0"] for r in R]), dz2=_med([r["dz2.0"] for r in R]),
            dz3=_med([r["dz3.0"] for r in R]),
            adz2=_med([abs(r["dz2.0"]) for r in R]),
            adz3=_med([abs(r["dz3.0"]) for r in R]),
            R2=_med([r["R2.0"] for r in R]), R3=_med([r["R3.0"] for r in R]),
            ey=_med([r["en_yakin"] for r in R]), vur=vur,
            kad=100.0 * _med([r["kadraj"] for r in R]))
        tab[ad] = sat
        print("%-15s%8.2f%8.2f%8.2f%8.2f%8.2f%8.2f%8.2f%8.2f%8.1f%8.1f"
              % (ad, sat["dz1"], sat["dz2"], sat["dz3"], sat["adz2"],
                 sat["adz3"], sat["R2"], sat["R3"], sat["ey"], sat["vur"],
                 sat["kad"]))
    print()
    t0 = tab.get("T0_taban")
    if t0:
        print("  TABANA GORE (T0_taban):")
        for ad, s in tab.items():
            if ad == "T0_taban":
                continue
            print("    %-15s |dz|@2s %+6.1f%%   |dz|@3s %+6.1f%%   en yakin %+6.1f%%   vurus %+.1f puan"
                  % (ad, 100 * (s["adz2"] / t0["adz2"] - 1),
                     100 * (s["adz3"] / t0["adz3"] - 1),
                     100 * (s["ey"] / t0["ey"] - 1), s["vur"] - t0["vur"]))
    return tab


def tek(aday="T0_taban", senaryo="duz", tohum=0, sure=6.0):
    r = kosu(aday, senaryo=senaryo, tohum=tohum, sure=sure, kayit=True)
    print("=" * 78)
    print("TEK DEVIR  aday=%s senaryo=%s  |  en yakin %.2f m, sure %.2f s, "
          "kadraj %%%.0f" % (aday, senaryo, r["en_yakin"], r["sure"],
                             100 * r["kadraj"]))
    print("=" * 78)
    print("  %6s%9s%9s%9s%9s%9s" % ("t", "menzil", "dz", "pitch", "yatayV", "vz"))
    iz = r["iz"]
    for i in range(0, len(iz), max(1, len(iz) // 24)):
        t, R, dz, pi, vh, vz = iz[i]
        print("  %6.2f%9.2f%9.2f%9.1f%9.2f%9.2f" % (t, R, dz, pi, vh, vz))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ab", action="store_true")
    ap.add_argument("--n", type=int, default=160)
    ap.add_argument("--sure", type=float, default=6.0)
    ap.add_argument("--arka_plan", type=float, default=1.0)
    ap.add_argument("--aday", default="T0_taban")
    ap.add_argument("--senaryo", default="duz")
    ap.add_argument("--gurultusuz", action="store_true")
    a = ap.parse_args()
    if a.ab:
        ab(a.n, a.sure, a.arka_plan, gurultu=not a.gurultusuz)
    else:
        tek(a.aday, a.senaryo, sure=a.sure)


if __name__ == "__main__":
    main()

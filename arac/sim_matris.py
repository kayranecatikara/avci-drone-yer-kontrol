# -*- coding: utf-8 -*-
"""
================================================================================
  SIM_MATRIS  --  COKLU SENARYO DAYANIKLILIK MATRISI
================================================================================
SORU: "Talon ister duz ister manevra, HER TURLU seye karsi" -- hangi ayar
      TEK senaryoda degil, SENARYO UZAYININ TAMAMINDA ayakta kaliyor?

⚠ BU BETIK HICBIR CANLI DOSYAYI DEGISTIRMEZ.
   kopru/ altindaki yasa, sim/tesis.py, sim/deney.py, arac/sim_omur.py,
   arac/sim_yasa.py, arac/sim_devir.py, arac/sim_kopru.py, arac/sim_burun.py
   hepsi SALT OKUNUR olarak import edilir. Burada YALNIZCA olcum yapilir.

--------------------------------------------------------------------------------
 NEDEN AYRI BIR BETIK
--------------------------------------------------------------------------------
Bugune kadarki taramalar TEK EKSENLIYDI (bir parametre, bir senaryo). Sonuc:
    - "yaw bayat"  YANLIS cikti (gecikme taramasi: en iyi uyum 0.00 s)
    - "PN cozum"   YANLIS cikti (oyunda dort varyant da ~19.5 m)
    - "zarfi ac"   YANLIS cikti (iska 12.73 -> 15.25 m)
Ortak kusur: ORTALAMA raporlandi, EN KOTU SENARYO raporlanmadi. Bir ayarin
ortalamasi iyi ama tek bir senaryoda cokuyorsa o ayar SAGLAM DEGILDIR.
Bu betigin ASIL CIKTISI ortalama degil, "kac senaryoda kazaniyor / kac
senaryoda kaybediyor / EN KOTU senaryosu ne" uclusudur.

--------------------------------------------------------------------------------
 TEZGAH SECIMI  (⚠ varsayilan tezgah sahayi URETMIYOR)
--------------------------------------------------------------------------------
sim/tesis.py'nin kendi tespit_kaybi'yla faz 7-12 s yasar ve iska ~4.3 m cikar
(saha 12.73). Yani omur kaldiraclari icin SAGIR. Burada sim_devir.SahaAlgi
kullanilir: |eps| suruclu KUMELI tespit kaybi + olculen suruklenme acigi.
O tezgah dort bagimsiz olcutle kalibre edilmisti; BU betik ayrica KAYIP_M
supurmesinin IKI ucunu birden yeniden uretebildigini gosterir (--kalibre):

    UCUS OLCUMU (supervisor.py:76-81, tek degisken KAYIP_M)
        K20  omur 1.91 s   iska 12.47 m
        K60  omur 3.06 s   iska 10.10 m
    BU TEZGAH (ayni iki ayar, 40 tohum)     -> --kalibre ciktisina bak

Iki NOKTALI bir supurmeyi tutturmak, tek noktaya kalibre olmaktan farklidir:
tezgah KAYIP_M'e verilen TEPKIYI dogru uretiyor demektir.

--------------------------------------------------------------------------------
 EKSENLER
--------------------------------------------------------------------------------
hedef durumu (7)  DUZ | DONUS+ | DONUS- | GIRIS+ | GIRIS- | CIKIS+ | CIKIS-
                  (donus hizi 20.1 deg/s; +/- = hedefin donus yonu.
                   GIRIS = angajman duz baslar, ~0.2 s sonra donuse girer.
                   CIKIS = donuste baslar, ~0.15 s sonra duze cikar.)
devir menzili (5) 8 / 13 / 20 / 30 / 40 m
devir aspect  (5) 0 / +-20 / +-40 deg   (isaret = avcinin hangi yanda oldugu;
                  donus yonuyle carpimi "donusun ICINDE mi DISINDA mi" verir)
dikey ofset   (3) 0 / 3 / 8 m  (avci hedefin KAC METRE ALTINDA)
tespit kalitesi(3) iyi / saha / kotu   (tehlike tablosu carpani, asagida)
piksel jitter (3) 0 / 1 / 3 px  (HataAyari.jitter_px; saha degeri 1.0)

⚠ RANGE_SET 9 bu matriste EKSEN DEGILDIR: gorsel faz GPS'siz kosar, istasyon
mesafesi yalnizca DEVIR MENZILI dagilimini kaydirir -- o da zaten ayri bir
eksen olarak (8..40 m) tam supuruluyor. RANGE_SET'in etkisi menzil ekseninin
hangi noktasinda durdugunuzdur, ayri bir davranis degil.

--------------------------------------------------------------------------------
 OLCUTLER  (UCU BIRDEN -- biri tek basina yaniltir)
--------------------------------------------------------------------------------
1) NISAN   : |hiz yonu - hedefe olan gercek yon|, faz GENELINDE (kor kareler
             DAHIL) her yasa tikinde ornekleniyor. Medyan + >90 deg orani.
             SAHA REFERANSI: medyan 56.4 deg, %24'u >90 deg.
2) OMUR    : faz omru (s) VE tespitli gecen sure (s). KOR sure ayri sayilir
             -- "faz yasadi" ile "faz gordu" ayni sey degil.
3) ISKA    : en yakin gecis medyani (m) ve <3 m orani.

--------------------------------------------------------------------------------
 KAZANMA / KAYBETME KURALI  (hucre basina, MEVCUT'a karsi, ESLENMIS tohum)
--------------------------------------------------------------------------------
KAZANIR : iska medyani >= 0.50 m iyilesiyor  VE  nisan medyani > 5 deg bozulmuyor
KAYBEDER: iska medyani >= 0.50 m bozuluyor   VEYA nisan medyani > 15 deg bozuluyor
digerleri BERABERE. Esik gurultu tabanindan gelir (ayni hucrede tohum-arasi
iska degiskenligi ~0.3 m, 16 tohum eslenmis).

⚠ OLCUM HATASI ACIK KOSULUR (HataAyari varsayilani). Kapali tezgah 16 Agustos
sabahi YANLIS KAZANAN secti. Ayrica her siralamа SURUKLEME_EK ACIK ve KAPALI
kosulur: siralama degismiyorsa sonuc kalibrasyona dayanmiyor demektir.

--------------------------------------------------------------------------------
 ⚠ KOSU SIRASINDA DEGISEN GERCEK (2026-08-16 18:32)
--------------------------------------------------------------------------------
Matris koserken bbox_ibvs.py guncellendi: PIKSEL koprusu UCUSTA olculdu ve
ZARARLI cikti (Cfg.KOR_KOPRU_S artik "(ZARARLI)" diye isaretli):
        ayar        TUM     gorurken   korken   >90 deg
        kopru yok  42.9      8.2       73.3     %17
        0.30 s     54.8     15.0       93.2     %30
        0.60 s     70.9     25.7      110.6     %40
Sebep: piksel hizi hedefin hareketi degil, icinde BIZIM BURUN DONUSUMUZ var
-> parazitik dongu. Ayni saatte DOGRU surum eklendi: KOR_KOPRU_ATALET_S.
BU TEZGAH AYNI YONU BAGIMSIZ URETTI (--matris: KOPRU.3/.6 net EKSI, gercek
tespit sayisi 781 -> 607 dusuyor), ama BUYUKLUGU KUCUK gosterdi -- ayni
suruklenme acigi. Atalet surumu icin --atalet ile IKINCI matris kosulur:
atalet koprusu "hedefin kerterizi SABIT" varsayar, yani DONUSTE bozulmasi
beklenir; matrisin hedef-durumu ekseni tam bunu olcer.

CALISTIR
    python arac/sim_matris.py --kalibre    tezgah sahayi uretiyor mu (once bu)
    python arac/sim_matris.py --kapsam     akilli ornekleme neyi kaciriyor
    python arac/sim_matris.py --matris     tam dayaniklilik matrisi
    python arac/sim_matris.py --atalet     ayni matris, ATALET koprusu adaylari
    python arac/sim_matris.py --matris --hizli    kucuk ornek (duman testi)
    (argumansiz = kalibre + kapsam + matris)

⚠ Windows'ta dosyaya yonlendirirken PYTHONIOENCODING=utf-8 gerekir.
================================================================================
"""
import argparse
import math
import os
import statistics as st
import sys
import time

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "arac"))

import sim_devir as SD                                             # noqa: E402
import tesis as T                                                  # noqa: E402
from tesis import Avci, Hedef, Olcum, kadraj, F_YASA, HataAyari     # noqa: E402
from control.guidance import bbox_ibvs as IB                       # noqa: E402


# ══════════════════════════════════════════════════════════════════════════
#  CANLI SISTEMIN GERCEK ANAHTARLARI
# ══════════════════════════════════════════════════════════════════════════
# supervisor.SupCfg.KAYIP_M = 60 (2026-08-16, ucusta dogrulandi)
# ⚠ sim_devir.py modul sabiti hala 20 -- ORASI DEGISTIRILMEDI, burada
#   canli deger acikca gecilir.
KAYIP_M_CANLI = 60

# tespit kalitesi -> SahaAlgi tehlike tablosu carpani.
# ⚠ Bu carpanlar MEKANIZMA DEGIL, GOZLENEBILIR bir seviyeye baglanmis
#   etiketlerdir: her seviyenin URETTIGI "faz ici kutulu kare orani"
#   --kalibre ciktisinda basilir; saha olcumu 0.33-0.41.
KALITE = {"iyi": 0.45, "saha": 1.00, "kotu": 2.20}


def cfg_ile(**kw):
    """IB.Cfg'nin alan-degistirilmis alt sinifi. YASA KODU DEGISMEZ."""
    return type("Cfg_", (IB.Cfg,), kw)


# ── ADAYLAR ───────────────────────────────────────────────────────────────
# MEVCUT: RANGE_SET 9, V 24, a 12, vz 3, KAYIP_M 60, PN_N 1.6, K_YAW 1.0,
#         KOR_KOPRU_S 0   (V/a/vz zaten IB.Cfg varsayilani -- acikca yazildi)
_TABAN = dict(V_TOPLAM_MAX=24.0, MAX_ACCEL=12.0, VZ_MAX=3.0)

# ⚠ KOPRU.15 gorevde ISTENMEDI, OLCUMDEN turetildi ve bilerek eklendi:
#   bbox_ibvs.py:308 "kurtarilan bosluklarin %69.5'i <=4 kare". Yasa 33.3 Hz'de
#   kostuguna gore 4 kare = 0.12 s. Yani 0.3 s kopru olculen kurtarma
#   penceresinin 2.5 KATI, 0.6 s ise 5 KATI: o sürenin otesinde kopru artik
#   "kapanacak bosluğu" degil, KAPANMAYACAK boslugu ekstrapole ediyor --
#   duz saymaca surukleme enjekte ediyor. Olcume UYAN degeri de sinamak
#   gerekir, yoksa "kor kopru kotu" hukmu yanlis genellenir.
ADAYLAR = [
    # (ad,                 PN_N, K_YAW, KOR_KOPRU_S)
    ("MEVCUT",              1.6,  1.0,  0.0),
    ("KOPRU.15",            1.6,  1.0,  0.15),
    ("KOPRU.3",             1.6,  1.0,  0.3),
    ("KOPRU.6",             1.6,  1.0,  0.6),
    ("SESSIZ",              1.6,  0.3,  0.0),
    ("PN0",                 0.0,  1.0,  0.0),
    ("KOPRU.15+SESSIZ",     1.6,  0.3,  0.15),
    ("KOPRU.3+SESSIZ",      1.6,  0.3,  0.3),
    ("KOPRU.6+SESSIZ",      1.6,  0.3,  0.6),
    ("KOPRU.3+PN0",         0.0,  1.0,  0.3),
    ("KOPRU.6+PN0",         0.0,  1.0,  0.6),
    ("SESSIZ+PN0",          0.0,  0.3,  0.0),
    ("KOPRU.6+SESSIZ+PN0",  0.0,  0.3,  0.6),
]


# ── ATALET KOPRUSU ADAYLARI (2026-08-16 18:32, bbox_ibvs.py'ye EKLENDI) ──
# ⚠⚠ GOREV BRIFINGINDEN SONRA UCUSTA OLCULDU: PIKSEL koprusu ZARARLI.
#        ayar        TUM     gorurken   korken   >90 deg
#        kopru yok  42.9      8.2       73.3     %17
#        0.30 s     54.8     15.0       93.2     %30
#        0.60 s     70.9     25.7      110.6     %40
#    Sebep (bbox_ibvs.py:320-325): piksel hizi hedefin hareketi DEGIL, icinde
#    BIZIM BURUN DONUSUMUZ de var -> parazitik dongu.
#    Repo ayni saatte DOGRU surumu ekledi: KOR_KOPRU_ATALET_S. Hedefin ATALET
#    kerterizini saklar, kor karede GUNCEL yaw ile piksele geri cevirir:
#        eps_kopru = los_son - iris_yaw(SIMDI);  cx = CX + FX*tan(eps_kopru)
#    Kendi donusumuz ACIKCA cikarildigi icin parazitik dongu YAPISAL OLARAK
#    kurulamaz.
# ⚠ AMA: bu surum "hedefin ATALET KERTERIZI SABIT" varsayar. Hedef kor surede
#   DONUYORSA kerteriz kayar. Yani tam olarak BU MATRISIN sorusu: ayar duzde
#   iyi olup manevrada cokuyor mu? Onun icin ikinci matris kosulur.
ADAYLAR_ATALET = [
    # (ad,               PN_N, K_YAW, KOR_KOPRU_S, KOR_KOPRU_ATALET_S)
    ("MEVCUT",            1.6,  1.0,  0.0,  0.0),
    ("KOPRU.3 (piksel)",  1.6,  1.0,  0.3,  0.0),   # ucusta ZARARLI -- kontrol
    ("ATALET.15",         1.6,  1.0,  0.0,  0.15),
    ("ATALET.3",          1.6,  1.0,  0.0,  0.30),
    ("ATALET.6",          1.6,  1.0,  0.0,  0.60),
    ("ATALET.3+SESSIZ",   1.6,  0.3,  0.0,  0.30),
]


def _al(a, i, vars_=0.0):
    return a[i] if len(a) > i else vars_


def aday_cfg(a):
    return cfg_ile(PN_N=a[1], K_YAW=a[2], KOR_KOPRU_S=_al(a, 3),
                   KOR_KOPRU_ATALET_S=_al(a, 4), **_TABAN)


# ══════════════════════════════════════════════════════════════════════════
#  ALGI -- SahaAlgi + tespit KALITESI carpani
# ══════════════════════════════════════════════════════════════════════════
class MatrisAlgi(SD.SahaAlgi):
    """sim_devir.SahaAlgi, tek eklentiyle: tehlike tablosuna sabit carpan.

    ⚠ kare_ver() SahaAlgi'nin AYNISI; tek fark _tehlike_p ve _bulus_p'nin
    carpanla olceklenmesi. Kalite ekseni budur.
    """

    def __init__(self, *a, **kw):
        self.tc = float(kw.pop("tehlike_carpan", 1.0))
        SD.SahaAlgi.__init__(self, *a, **kw)

    def kare_ver(self, t, avci, k):
        if not self.saha_kayip or self.tc == 1.0:
            return SD.SahaAlgi.kare_ver(self, t, avci, k)
        a = self.a
        yeni = (a.kamera_hz <= 0.0
                or t - self._son_kare >= (1.0 / a.kamera_hz) - 1e-9)
        if yeni:
            dtk = (1.0 / max(a.kamera_hz, 1e-6) if self._kare_t is None
                   else max(t - self._kare_t, 1e-6))
            self._kare_t = t
            if k is None:
                self.gorunur = False
                self.eps_gercek = 90.0
            else:
                eps = math.degrees(math.atan((k[0] - T.CX) / F_YASA))
                self.eps_gercek = abs(eps)
                if self.surukleme_ek > 0.0 and self.faz_t0 is not None:
                    eps = abs(eps) + self.surukleme_ek * max(t - self.faz_t0, 0.0)
                b = max(k[2], k[3])
                h = min(0.98, SD._tehlike_p(eps, b) * self.tc)
                bul = SD._bulus_p(eps, b) / self.tc
                if self.gorunur:
                    if self.rnd.random() < SD._oran_cevir(h, dtk):
                        self.gorunur = False
                else:
                    if self.rnd.random() < SD._oran_cevir(bul, dtk):
                        self.gorunur = True
        return T.Algi.kare_ver(self, t, avci, (k if self.gorunur else None))


# ══════════════════════════════════════════════════════════════════════════
#  TEK ANGAJMAN
# ══════════════════════════════════════════════════════════════════════════
# ⚠ Govde sim_devir.gorsel_angajman()'in AYNISI (o dosya DEGISTIRILMEDI).
#   Buraya UC sey eklendi, hepsi CANLI koddan birebir:
#     1) KOR_KOPRU_S  -- bbox_ibvs.dongu:1141-1206'nin aynisi. Kopru karesi
#        GERCEK TESPIT SAYILMAZ (kayip sayaci isler), yalniz komut tazelenir.
#     2) NISAN olcutu -- |hiz yonu - hedefe gercek yon|, HER yasa tikinde
#        (kor kareler DAHIL). Faz genelinde olculur; saha 56.4 deg / %24.
#     3) KOR SURE     -- tespitli sure ile kor sure ayri sayilir.
def angajman(menzil=15.7, aspect=17.0, dikey=1.5, v0=21.6, faz0=0.0,
             tohum=0, cfg=IB.Cfg, hata=None, kayip_m=KAYIP_M_CANLI,
             dt=1.0 / 62.0, sure=12.0, hedef_yon=+1, yon_isaret=+1,
             surukleme_ek=None, kor_kopru_s=0.0, tehlike_carpan=1.0,
             jitter_px=None, kopru_atalet_s=0.0):
    if hata is None:
        hata = HataAyari()
    if jitter_px is not None:
        hata = HataAyari(**{k: getattr(hata, k) for k in
                            ("yaw_hz", "yaw_blok_hiz", "yaw_gecikme_s",
                             "yaw_gurultu_deg", "kamera_hz", "kare_gecikme_s",
                             "det_gecikme_s", "det_gecikme_p95_s",
                             "kenar_yanlilik_kutu", "kenar_gurultu_kutu",
                             "yanlis_hiz", "yanlis_sapma_px", "yanlis_sure_s",
                             "tespit_kaybi")})
        hata.jitter_px = float(jitter_px)
    hata.yasa_hz = SD.Saha.YASA_HZ
    hata.kamera_hz = SD.Saha.YASA_HZ
    algi = MatrisAlgi(hata, tohum=tohum, saha_kayip=True, gorunur=True,
                      surukleme_ek=(SD.SURUKLEME_EK if surukleme_ek is None
                                    else surukleme_ek),
                      tehlike_carpan=tehlike_carpan)
    algi.faz_t0 = 0.0

    hed = Hedef(faz0=faz0, yon=hedef_yon)
    hx, hy, hz, hvx, hvy, _ = hed.durum()
    hdg = math.atan2(hvy, hvx)
    chi = math.radians(aspect) * yon_isaret
    yatay = math.sqrt(max(menzil ** 2 - dikey ** 2, 1.0))
    av = Avci(x=hx + yatay * math.cos(hdg + math.pi + chi),
              y=hy + yatay * math.sin(hdg + math.pi + chi),
              z=hz - dikey, yaw=hdg,
              max_accel=cfg.MAX_ACCEL, v_max=cfg.V_TOPLAM_MAX,
              vz_max=cfg.VZ_MAX, yaw_rate_max=SD.YAW_RATE_ETKIN)
    los0 = math.atan2(hy - av.y, hx - av.x)
    av.yaw = los0
    av.vx, av.vy = v0 * math.cos(los0), v0 * math.sin(los0)

    hiz_I = v0
    psi_v = None
    terminal = False
    kayip = 0
    los_gecmis = []
    kop_gecmis = []                 # PIKSEL koprusu: son GERCEK teslimler
    son_tespit = None               # ATALET koprusu: (t, los_ham, cy, w, h)
    lam = 0.0
    en_yakin = menzil
    t = 0.0
    son_yasa_t = -1e9
    kutulu = tik = kopru_tik = 0
    temas_s = kor_s = 0.0
    nisan = []                      # her yasa tikinde |hiz yonu - hedefe yon|
    donus_izi = []
    while t < sure:
        hed.adim(dt)
        hx, hy, hz, hvx, hvy, _ = hed.durum()
        av._hedef_yon = math.atan2(hvy, hvx)
        k = kadraj(av, hx, hy, hz)
        algi.kare_ver(t, av, k)
        en_yakin = min(en_yakin, math.dist((av.x, av.y, av.z), (hx, hy, hz)))
        if t - son_yasa_t < 1.0 / hata.yasa_hz - 1e-9:
            av.adim(dt, t)
            t += dt
            continue
        dt_yasa = dt if son_yasa_t < 0.0 else max(t - son_yasa_t, dt)
        son_yasa_t = t
        poz = algi.oku(t)
        yaw_olc = algi.yaw_oku(t)
        roll_olc, pitch_olc = algi.tutum_oku(t)
        tik += 1
        donus_izi.append(hed.donus_hizi_deg())

        # ── OLCUT 1: NISAN (kor kareler DAHIL, faz GENELINDE) ────────────
        vh = math.hypot(av.vx, av.vy)
        if vh > 0.5:
            d = (math.atan2(hy - av.y, hx - av.x) - math.atan2(av.vy, av.vx)
                 + math.pi) % (2 * math.pi) - math.pi
            nisan.append(abs(math.degrees(d)))

        # ── KOR KOPRU (bbox_ibvs.dongu:1170-1200 birebir, ayni SIRAYLA) ──
        kopru_kare = False
        if poz is not None:
            kop_gecmis.append((t, poz[0], poz[1], poz[2], poz[3]))
            while len(kop_gecmis) > 6:
                kop_gecmis.pop(0)
        elif kopru_atalet_s > 0.0 and son_tespit is not None:
            # ATALET KOPRUSU: kerterizi koru, GUNCEL yaw ile piksele cevir.
            _yas = t - son_tespit[0]
            if 0.0 < _yas <= kopru_atalet_s:
                _eps_b = ((son_tespit[1] - yaw_olc + math.pi)
                          % (2 * math.pi) - math.pi)
                _eps_b = max(-1.15, min(1.15, _eps_b))      # ~66 deg kirpma
                poz = (cfg.CX_NISAN + IB.geo.FX * math.tan(_eps_b),
                       son_tespit[2], son_tespit[3], son_tespit[4])
                kopru_kare = True
                kopru_tik += 1
        elif kor_kopru_s > 0.0 and len(kop_gecmis) >= 2:
            _a, _b = kop_gecmis[-2], kop_gecmis[-1]
            _yas = t - _b[0]
            _dt = _b[0] - _a[0]
            if 1e-3 < _dt < 0.6 and 0.0 < _yas <= kor_kopru_s:
                _vx = max(-900.0, min(900.0, (_b[1] - _a[1]) / _dt))
                _vy = max(-900.0, min(900.0, (_b[2] - _a[2]) / _dt))
                poz = (_b[1] + _vx * _yas, _b[2] + _vy * _yas, _b[3], _b[4])
                kopru_kare = True
                kopru_tik += 1

        if poz is None:
            kayip += 1
            kor_s += dt_yasa
            if kayip >= kayip_m:
                break
        else:
            # ⚠ DURUSTLUK: kopru karesi GERCEK TESPIT SAYILMAZ.
            if kopru_kare:
                kayip += 1
                kor_s += dt_yasa
                if kayip >= kayip_m:
                    break
            else:
                kayip = 0
                kutulu += 1
                temas_s += dt_yasa
            cx, cy, w, h = poz
            lo = lo_ham = yaw_olc + math.atan((cx - cfg.CX_NISAN) / F_YASA)
            if los_gecmis:
                onc = los_gecmis[-1][1]
                lo = onc + ((lo - onc + math.pi) % (2 * math.pi) - math.pi)
            los_gecmis.append((t, lo))
            while los_gecmis and t - los_gecmis[0][0] > cfg.PN_PENCERE_S:
                los_gecmis.pop(0)
            if len(los_gecmis) >= 3:
                n_ = len(los_gecmis)
                tm = sum(g[0] for g in los_gecmis) / n_
                lm = sum(g[1] for g in los_gecmis) / n_
                sxx = sum((g[0] - tm) ** 2 for g in los_gecmis)
                lam = (max(-6.0, min(6.0, sum((g[0] - tm) * (g[1] - lm)
                                              for g in los_gecmis) / sxx))
                       if sxx > 1e-12 else 0.0)
            # atalet koprusu icin son GERCEK tespitin kerterizi (dongu:1323)
            # ⚠ SARILMAMIS `lo` DEGIL, HAM kerteriz saklanir: `lo` lambda
            #   kestirimi icin surekli hale getiriliyor (2*pi biriktirebilir),
            #   canli kodda saklanan `los_az` ise normalize_angle'li olan.
            if not kopru_kare:
                son_tespit = (t, lo_ham, cy, w, h)
            boyut = math.sqrt(w * h)
            if not terminal and boyut >= cfg.TERMINAL_BOYUT:
                terminal = True
            vx, vy, vz, yaw_cmd, hiz_I, tani = IB.komut(
                cx, cy, w, h, yaw_olc, hiz_I, dt_yasa, cfg, terminal,
                (lam, 0.0), pitch_olc, av.vz, None, roll_olc,
                av.yaw_hizi, psi_v)
            psi_v = tani.get("psi_v")
            av.setpoint(vx, vy, vz, yaw_cmd, t)
        av.adim(dt, t)
        t += dt

    nis = sorted(nisan)
    return {"omur": t, "en_yakin": en_yakin,
            "temas_s": temas_s, "kor_s": kor_s,
            "kutulu": kutulu / max(tik, 1),
            "kopru_oran": kopru_tik / max(tik, 1),
            "nisan_p50": (nis[len(nis) // 2] if nis else float("nan")),
            "nisan_90": (sum(1 for x in nis if x > 90.0) / len(nis)
                         if nis else float("nan")),
            "nisan_ham": nis,
            "donus_ort": (sum(donus_izi) / len(donus_izi)) if donus_izi else 0.0}


# ══════════════════════════════════════════════════════════════════════════
#  SENARYO UZAYI
# ══════════════════════════════════════════════════════════════════════════
# Hedef yay uzunlugu: duz kenar 104.8 m, donus yayi 160.2 m, cevre 530 m.
# faz0 = yayin kesri.  Hedef 17.98 m/s -> 1 s = 0.034 faz.
_R = Olcum.DONUS_YARICAP
_DUZ = (Olcum.TUR_UZUNLUK - 2 * math.pi * _R) / 2.0
_CEV = 2 * _DUZ + 2 * math.pi * _R
_F_DUZ_SON = _DUZ / _CEV                     # 0.1977 -- donuse giris
_F_DON_SON = (_DUZ + math.pi * _R) / _CEV    # 0.5000 -- donusten cikis

DURUMLAR = [
    # (ad,       faz0,                    hedef_yon)
    ("DUZ",      0.05,                    +1),   # 4.3 s boyunca duz
    ("DONUS+",   0.33,                    +1),   # 20.1 deg/s, sol donus
    ("DONUS-",   0.33,                    -1),   # 20.1 deg/s, sag donus
    ("GIRIS+",   _F_DUZ_SON - 0.008,      +1),   # 0.24 s sonra donuse girer
    ("GIRIS-",   _F_DUZ_SON - 0.008,      -1),
    ("CIKIS+",   _F_DON_SON - 0.006,      +1),   # 0.18 s sonra duze cikar
    ("CIKIS-",   _F_DON_SON - 0.006,      -1),
]

MENZILLER = [8.0, 13.0, 20.0, 30.0, 40.0]
ASPECTLER = [(0.0, +1), (20.0, +1), (20.0, -1), (40.0, +1), (40.0, -1)]
DIKEYLER = [0.0, 3.0, 8.0]


def senaryolar(hizli=False):
    """Akilli ornekleme. KAPSAM raporlanir (bkz. --matris basligi).

    BLOK A -- durum x menzil x aspect x dikey   (kalite=saha, jitter=1 px)
              tam carpim: 7*5*5*3 = 525 hucre. Guduum eksenlerinin TAMAMI
              carpilir; burada kesme YOK.
    BLOK B -- durum x menzil(3) x kalite(3) x jitter(3)  (aspect +20, dikey 3)
              7*3*3*3 = 189 hucre. Algi bozulmasi ekseni.
    ⚠ KESILEN SEY, ACIKCA: tam carpim (A x B) 4725 hucre olurdu. Kesilen
      etkilesim KALITE/JITTER x ASPECT/DIKEY'dir. Bu kesme bir VARSAYIM
      degil, OLCULMUS bir varsayimdir: `--kapsam` modu tam o etkilesimi
      kosar ve "aday siralamasi kalite seviyeleri arasinda ayni mi"
      sorusunu sayiyla yanitlar. Cikti raporda verilir.
    """
    men = MENZILLER[:2] if hizli else MENZILLER
    asp = ASPECTLER[:2] if hizli else ASPECTLER
    dik = DIKEYLER[:2] if hizli else DIKEYLER
    dur = DURUMLAR[:3] if hizli else DURUMLAR
    S = []
    for (dad, faz0, hyon) in dur:
        for m in men:
            for (a, ai) in asp:
                for d in dik:
                    S.append(dict(blok="A", durum=dad, faz0=faz0, hedef_yon=hyon,
                                  menzil=m, aspect=a, yon_isaret=ai, dikey=d,
                                  kalite="saha", jitter=1.0))
    men_b = [8.0, 20.0, 40.0] if not hizli else [8.0]
    kal_b = ["iyi", "saha", "kotu"] if not hizli else ["saha", "kotu"]
    jit_b = [0.0, 1.0, 3.0] if not hizli else [1.0]
    for (dad, faz0, hyon) in dur:
        for m in men_b:
            for kal in kal_b:
                for j in jit_b:
                    S.append(dict(blok="B", durum=dad, faz0=faz0, hedef_yon=hyon,
                                  menzil=m, aspect=20.0, yon_isaret=+1, dikey=3.0,
                                  kalite=kal, jitter=j))
    return S


def sen_ad(s):
    return ("%s|R%.0f|a%+.0f|h%.0f|%s|j%.0f"
            % (s["durum"], s["menzil"], s["aspect"] * s["yon_isaret"],
               s["dikey"], s["kalite"], s["jitter"]))


# ══════════════════════════════════════════════════════════════════════════
#  HUCRE KOSUSU
# ══════════════════════════════════════════════════════════════════════════
def hucre(s, aday, tohumlar, surukleme_ek=None):
    """Tek (senaryo, aday) hucresi. Tohumlar ESLENMIS (adaylar arasi ayni)."""
    cfg = aday_cfg(aday)
    r = [angajman(menzil=s["menzil"], aspect=s["aspect"], dikey=s["dikey"],
                  faz0=s["faz0"], hedef_yon=s["hedef_yon"],
                  yon_isaret=s["yon_isaret"], cfg=cfg, tohum=tt,
                  kor_kopru_s=_al(aday, 3),
                  kopru_atalet_s=_al(aday, 4), kayip_m=KAYIP_M_CANLI,
                  tehlike_carpan=KALITE[s["kalite"]], jitter_px=s["jitter"],
                  surukleme_ek=surukleme_ek)
         for tt in tohumlar]
    nis = sorted(x for q in r for x in q["nisan_ham"])
    ey = [q["en_yakin"] for q in r]
    return {"iska_p50": st.median(ey),
            "iska_lt3": sum(1 for x in ey if x < 3.0) / len(ey),
            "iska_min": min(ey),
            "nisan_p50": nis[len(nis) // 2] if nis else float("nan"),
            "nisan_90": (sum(1 for x in nis if x > 90.0) / len(nis)
                         if nis else float("nan")),
            "omur_p50": st.median([q["omur"] for q in r]),
            "temas_p50": st.median([q["temas_s"] for q in r]),
            "kor_p50": st.median([q["kor_s"] for q in r]),
            "kutulu": st.median([q["kutulu"] for q in r])}


ISKA_ESIK = 0.50       # m  -- anlamli iska farki (tohum-arasi gurultu ~0.3 m)
NISAN_IYI = 5.0        # deg -- bu kadar bozulma "kazanc" saymayi engeller
NISAN_KOTU = 15.0      # deg -- bu kadar bozulma tek basina KAYIP


def karar(a, m):
    """Aday hucresi `a` vs MEVCUT hucresi `m` -> +1 kazandi / -1 kaybetti / 0."""
    d_iska = m["iska_p50"] - a["iska_p50"]        # + = aday daha yakin gecti
    d_nis = a["nisan_p50"] - m["nisan_p50"]       # + = aday daha kotu nisan
    if d_iska <= -ISKA_ESIK or d_nis > NISAN_KOTU:
        return -1
    if d_iska >= ISKA_ESIK and d_nis <= NISAN_IYI:
        return +1
    return 0


# ══════════════════════════════════════════════════════════════════════════
#  KALIBRASYON -- tezgah sahayi uretiyor mu
# ══════════════════════════════════════════════════════════════════════════
def kalibre(n=40):
    th = list(range(n))
    print("=" * 78)
    print("  KALIBRASYON -- tezgah sahayi uretiyor mu")
    print("=" * 78)
    print("  Devir durumu SAHADAN: 15.7 m, aspect 17 deg, 1.5 m alt, 21.6 m/s")
    print("  olcum hatasi ACIK | surukleme_ek %.0f deg/s | %d tohum\n"
          % (SD.SURUKLEME_EK, n))
    cfg = aday_cfg(ADAYLAR[0])
    print("  %-24s %7s %7s %7s %7s %7s" %
          ("", "omur", "iska", "temas", "kor", "kutulu"))
    print("  " + "-" * 66)
    for ad, km, sm_om, sm_is in (("SAHA ucus  KAYIP_M=20", 20, 1.91, 12.47),
                                 ("SAHA ucus  KAYIP_M=60", 60, 3.06, 10.10)):
        r = [angajman(cfg=cfg, tohum=t, kayip_m=km, kor_kopru_s=0.0)
             for t in th]
        print("  %-24s %7.2f %7.2f %7s %7s %7s   <- SAHA %.2f s / %.2f m"
              % (ad.replace("SAHA ucus  ", "tezgah  "),
                 st.median([x["omur"] for x in r]),
                 st.median([x["en_yakin"] for x in r]), "", "", "",
                 sm_om, sm_is))
        print("  %-24s %7s %7s %7.2f %7.2f %7.2f"
              % ("", "", "",
                 st.median([x["temas_s"] for x in r]),
                 st.median([x["kor_s"] for x in r]),
                 st.median([x["kutulu"] for x in r])))
    r = [angajman(cfg=cfg, tohum=t, kayip_m=KAYIP_M_CANLI) for t in th]
    nis = sorted(x for q in r for x in q["nisan_ham"])
    print("\n  NISAN olcutu (faz genelinde, kor kareler dahil):")
    print("      tezgah  medyan %5.1f deg   >90 deg %5.1f %%"
          % (nis[len(nis) // 2], 100.0 * sum(1 for x in nis if x > 90) / len(nis)))
    print("      SAHA    medyan  56.4 deg   >90 deg  24.0 %")
    print("\n  TESPIT KALITESI ekseninin URETTIGI 'faz ici kutulu kare orani'")
    print("      ⚠ ANCHOR KAYIP_M=20'de okunur: sahanin 0.33-0.41 olcumu O")
    print("        pencerede yapildi. K60'ta ayni fiziksel algi daha uzun bir")
    print("        KOR kuyrukla bolundugu icin oran mekanik olarak duser --")
    print("        algi kotulesti demek DEGILDIR.")
    print("      %-6s %10s %10s %10s %10s" % ("", "kutulu@K20", "kutulu@K60",
                                              "omur@K60", "iska@K60"))
    for kal, c in KALITE.items():
        r20 = [angajman(cfg=cfg, tohum=t, kayip_m=20, tehlike_carpan=c)
               for t in th]
        r60 = [angajman(cfg=cfg, tohum=t, kayip_m=KAYIP_M_CANLI,
                        tehlike_carpan=c) for t in th]
        print("      %-6s %10.2f %10.2f %10.2f %10.1f"
              % (kal, st.median([x["kutulu"] for x in r20]),
                 st.median([x["kutulu"] for x in r60]),
                 st.median([x["omur"] for x in r60]),
                 st.median([x["en_yakin"] for x in r60])))
    print("      SAHA   %10s" % "0.33-0.41")
    print("\n  ⚠⚠ TEZGAHIN BILINEN ACIGI -- NISAN OLCUTUNUN MUTLAK SEVIYESI")
    print("     Tezgah 21 deg / %14 uretiyor, saha 56.4 deg / %24. Ayni acik")
    print("     sim_devir.py'de de yazili: kadraj ici suruklenme tezgahta")
    print("     2-5 deg/s, sahada 22 deg/s ve sebep tezgahin MODELLEDIGI")
    print("     hicbir kanalda degil. SURUKLEME_EK bu acigi yalniz TEHLIKE")
    print("     hesabinda kapatir, yasanin gordugu kutuya DOKUNMAZ.")
    print("     SONUC: nisan MUTLAK degeri sahaya oturmaz, ADAYLAR ARASI")
    print("     FARKI oturur. Matriste nisan hep MEVCUT'a GORE okunur.")
    print()


# ══════════════════════════════════════════════════════════════════════════
#  MATRIS
# ══════════════════════════════════════════════════════════════════════════
def matris(hizli=False, n_tohum=16, surukleme_ek=None, sessiz=False):
    S = senaryolar(hizli)
    th = list(range(n_tohum))
    if not sessiz:
        print("=" * 78)
        print("  DAYANIKLILIK MATRISI")
        print("=" * 78)
        print("  senaryo hucresi %d | aday %d | tohum %d (ESLENMIS) | kosu %d"
              % (len(S), len(ADAYLAR), n_tohum, len(S) * len(ADAYLAR) * n_tohum))
        print("  surukleme_ek %s | olcum hatasi ACIK | KAYIP_M %d"
              % ("KALIBRE %.0f" % SD.SURUKLEME_EK if surukleme_ek is None
                 else "%.0f" % surukleme_ek, KAYIP_M_CANLI))
    t0 = time.time()
    sonuc = {}          # (sen_idx, aday_ad) -> hucre ozeti
    for i, s in enumerate(S):
        for a in ADAYLAR:
            sonuc[(i, a[0])] = hucre(s, a, th, surukleme_ek=surukleme_ek)
        if not sessiz and (i + 1) % 50 == 0:
            print("    ... %d/%d hucre (%.0f s)" % (i + 1, len(S), time.time() - t0),
                  flush=True)
    if not sessiz:
        print("  bitti: %.0f s\n" % (time.time() - t0))
    return S, sonuc


def rapor(S, sonuc, surukleme_ek=None):
    ad0 = ADAYLAR[0][0]
    print("-" * 78)
    print("  TABLO 1 -- ADAY BASINA DAYANIKLILIK (%d senaryo hucresi)" % len(S))
    print("-" * 78)
    print("  %-20s %5s %5s %5s | %6s %6s | %6s %6s | %s"
          % ("ADAY", "KAZ", "KAY", "BER", "iska", "<3m%", "nisan", ">90%",
             "EN KOTU SENARYO (iska farki)"))
    print("  " + "-" * 108)
    ozet = {}
    for a in ADAYLAR:
        ad = a[0]
        kaz = kay = ber = 0
        en_kotu = None
        iska = []
        lt3 = []
        nis = []
        n90 = []
        for i, s in enumerate(S):
            c = sonuc[(i, ad)]
            m = sonuc[(i, ad0)]
            k = karar(c, m)
            kaz += k > 0
            kay += k < 0
            ber += k == 0
            iska.append(c["iska_p50"])
            lt3.append(c["iska_lt3"])
            nis.append(c["nisan_p50"])
            n90.append(c["nisan_90"])
            d = c["iska_p50"] - m["iska_p50"]
            if en_kotu is None or d > en_kotu[0]:
                en_kotu = (d, sen_ad(s), c["iska_p50"], m["iska_p50"])
        ozet[ad] = dict(kaz=kaz, kay=kay, ber=ber, iska=st.median(iska),
                        lt3=100 * st.mean(lt3), nis=st.median(nis),
                        n90=100 * st.median(n90), kotu=en_kotu)
        ek = ("%s  %+.1f m (%.1f vs %.1f)"
              % (en_kotu[1], en_kotu[0], en_kotu[2], en_kotu[3])) if ad != ad0 else "-"
        print("  %-20s %5d %5d %5d | %6.2f %6.1f | %6.1f %6.1f | %s"
              % (ad, kaz, kay, ber, ozet[ad]["iska"], ozet[ad]["lt3"],
                 ozet[ad]["nis"], ozet[ad]["n90"], ek))
    print("\n  KAZ/KAY: MEVCUT'a karsi ESLENMIS tohumla hucre sayimi.")
    print("  iska/nisan sutunlari HUCRE MEDYANIDIR -- tek basina bakma,")
    print("  KAZ/KAY ve EN KOTU sutunlari ile birlikte oku.")
    return ozet


def rapor_kirilim(S, sonuc, ozet):
    ad0 = ADAYLAR[0][0]
    # en iyi 4 aday (kaz-kay farkina gore)
    sirali = sorted([a[0] for a in ADAYLAR if a[0] != ad0],
                    key=lambda x: -(ozet[x]["kaz"] - ozet[x]["kay"]))[:4]
    adlar = [ad0] + sirali
    print("\n" + "-" * 78)
    print("  TABLO 2 -- HEDEF DURUMUNA GORE ISKA MEDYANI (m)")
    print("-" * 78)
    print("  %-10s" % "DURUM" + "".join("%14s" % a[:13] for a in adlar))
    for (dad, _f, _y) in DURUMLAR:
        idx = [i for i, s in enumerate(S) if s["durum"] == dad]
        if not idx:
            continue
        print("  %-10s" % dad + "".join(
            "%14.2f" % st.median([sonuc[(i, a)]["iska_p50"] for i in idx])
            for a in adlar))
    print("\n" + "-" * 78)
    print("  TABLO 3 -- DEVIR MENZILINE GORE ISKA MEDYANI (m)")
    print("-" * 78)
    print("  %-10s" % "MENZIL" + "".join("%14s" % a[:13] for a in adlar))
    for m in MENZILLER:
        idx = [i for i, s in enumerate(S) if abs(s["menzil"] - m) < 1e-6]
        if not idx:
            continue
        print("  %-10s" % ("%.0f m" % m) + "".join(
            "%14.2f" % st.median([sonuc[(i, a)]["iska_p50"] for i in idx])
            for a in adlar))
    print("\n" + "-" * 78)
    print("  TABLO 4 -- TESPIT KALITESI x JITTER (BLOK B) ISKA MEDYANI (m)")
    print("-" * 78)
    print("  %-14s" % "KALITE/JIT" + "".join("%14s" % a[:13] for a in adlar))
    for kal in ("iyi", "saha", "kotu"):
        for j in (0.0, 1.0, 3.0):
            idx = [i for i, s in enumerate(S) if s["blok"] == "B"
                   and s["kalite"] == kal and abs(s["jitter"] - j) < 1e-6]
            if not idx:
                continue
            print("  %-14s" % ("%s / %.0f px" % (kal, j)) + "".join(
                "%14.2f" % st.median([sonuc[(i, a)]["iska_p50"] for i in idx])
                for a in adlar))
    print("\n" + "-" * 78)
    print("  TABLO 5 -- OMUR / TESPITLI SURE / KOR SURE (s), tum hucre medyani")
    print("-" * 78)
    print("  %-20s %8s %8s %8s %8s" % ("ADAY", "omur", "temas", "kor", "kor%"))
    for a in adlar:
        om = st.median([sonuc[(i, a)]["omur_p50"] for i in range(len(S))])
        te = st.median([sonuc[(i, a)]["temas_p50"] for i in range(len(S))])
        ko = st.median([sonuc[(i, a)]["kor_p50"] for i in range(len(S))])
        print("  %-20s %8.2f %8.2f %8.2f %8.0f" % (a, om, te, ko,
                                                   100.0 * ko / max(om, 1e-9)))
    return adlar


def rapor_net(S, sonuc, baslik, anahtar, degerler):
    """Eksen degerine gore NET (KAZ - KAY) hucre sayimi, TUM adaylar.

    ⚠ Bu tablo raporun kalbi: bir aday bir eksen degerinde ARTI, digerinde
    EKSI veriyorsa o aday TEK SENARYOYA optimize edilmis demektir.
    """
    ad0 = ADAYLAR[0][0]
    print("\n" + "-" * 78)
    print("  %s -- NET (KAZ - KAY) hucre, MEVCUT'a karsi" % baslik)
    print("-" * 78)
    grup = {}
    for i, s in enumerate(S):
        grup.setdefault(anahtar(s), []).append(i)
    deg = [d for d in degerler if d in grup]
    print("  %-20s" % "ADAY" + "".join("%8s" % str(d)[:7] for d in deg)
          + "%9s" % "EN KOTU")
    for a in ADAYLAR[1:]:
        ad = a[0]
        sat = []
        for d in deg:
            n = 0
            for i in grup[d]:
                n += karar(sonuc[(i, ad)], sonuc[(i, ad0)])
            sat.append(n)
        # eksen degerine gore normalize edilmis en kotu dilim
        kotu = min(sat[j] / max(len(grup[deg[j]]), 1) for j in range(len(deg)))
        print("  %-20s" % ad + "".join("%+8d" % x for x in sat)
              + "%9.2f" % kotu)
    print("  EN KOTU = en kotu dilimdeki net/hucre orani (-1.00 = o dilimin")
    print("            HER hucresinde kaybediyor). Sifirin altindaki her sayi")
    print("            'bu ayar o senaryoda MEVCUT'tan kotu' demektir.")


def rapor_bosluk(S, sonuc):
    """HICBIR adayin ise yaramadigi senaryolar -- geriye kalan gercek bosluk."""
    print("\n" + "-" * 78)
    print("  TABLO 6 -- HICBIR ADAYIN ISE YARAMADIGI SENARYOLAR")
    print("-" * 78)
    print("  Olcut: TUM adaylarin iska medyani > 8 m (yani hicbiri yaklasamiyor)")
    kotu = []
    for i, s in enumerate(S):
        en_iyi = min(sonuc[(i, a[0])]["iska_p50"] for a in ADAYLAR)
        if en_iyi > 8.0:
            kotu.append((en_iyi, sen_ad(s), s))
    print("  %d / %d hucre (%.0f %%)" % (len(kotu), len(S), 100.0 * len(kotu) / len(S)))
    if kotu:
        say = {}
        for _e, _a, s in kotu:
            for k, v in (("durum", s["durum"]), ("menzil", "%.0f m" % s["menzil"]),
                         ("aspect", "%+.0f" % (s["aspect"] * s["yon_isaret"])),
                         ("dikey", "%.0f m" % s["dikey"]),
                         ("kalite", s["kalite"])):
                say.setdefault(k, {}).setdefault(v, 0)
                say[k][v] += 1
        top = {}
        for i, s in enumerate(S):
            for k, v in (("durum", s["durum"]), ("menzil", "%.0f m" % s["menzil"]),
                         ("aspect", "%+.0f" % (s["aspect"] * s["yon_isaret"])),
                         ("dikey", "%.0f m" % s["dikey"]),
                         ("kalite", s["kalite"])):
                top.setdefault(k, {}).setdefault(v, 0)
                top[k][v] += 1
        for k in ("durum", "menzil", "aspect", "dikey", "kalite"):
            print("    %-8s " % k + "  ".join(
                "%s %d/%d" % (v, say[k].get(v, 0), tot)
                for v, tot in sorted(top[k].items())))
        kotu.sort(key=lambda x: -x[0])
        print("  en kotu 8 hucre (en iyi adayin iskasi):")
        for e, a, _s in kotu[:8]:
            print("      %-34s %6.2f m" % (a, e))
    return kotu


def kapsam(n_tohum=10):
    """AKILLI ORNEKLEMENIN BEDELI: kesilen etkilesimi OLC.

    BLOK A kalite=saha'da, BLOK B aspect=+20/dikey=3'te kosuluyor. Kesilen
    sey KALITE x (ASPECT, DIKEY) etkilesimi. Burada TAM o kesit kosulur:
    aspect x dikey x kalite, ve her kalite seviyesinde ADAY SIRALAMASI
    cikarilir. Siralamalar ortusuyorsa kesme bedelsizdir.
    """
    print("\n" + "=" * 78)
    print("  KAPSAM SINAMASI -- akilli ornekleme neyi kaciriyor")
    print("=" * 78)
    S = []
    for (a, ai) in ASPECTLER:
        for d in DIKEYLER:
            for kal in ("iyi", "saha", "kotu"):
                S.append(dict(blok="K", durum="DONUS+", faz0=0.33, hedef_yon=+1,
                              menzil=13.0, aspect=a, yon_isaret=ai, dikey=d,
                              kalite=kal, jitter=1.0))
    th = list(range(n_tohum))
    son = {}
    for i, s in enumerate(S):
        for a in ADAYLAR:
            son[(i, a[0])] = hucre(s, a, th)
    print("  %d hucre (aspect 5 x dikey 3 x kalite 3), %d tohum" % (len(S), n_tohum))
    print("\n  Her kalite seviyesinde ADAY SIRALAMASI (iska medyanina gore):")
    sira = {}
    for kal in ("iyi", "saha", "kotu"):
        idx = [i for i, s in enumerate(S) if s["kalite"] == kal]
        pu = sorted(((st.median([son[(i, a[0])]["iska_p50"] for i in idx]), a[0])
                     for a in ADAYLAR))
        sira[kal] = [x[1] for x in pu]
        print("    %-5s : %s" % (kal, " > ".join("%s(%.1f)" % (b, v)
                                                 for v, b in pu[:5])))
    ad = [a[0] for a in ADAYLAR]
    for x, y in (("iyi", "saha"), ("saha", "kotu"), ("iyi", "kotu")):
        rx = [sira[x].index(b) for b in ad]
        ry = [sira[y].index(b) for b in ad]
        print("    Spearman(%s, %s) = %+.2f" % (x, y, SD.spearman(rx, ry)))
    print("  ⚠ YORUM: Spearman yuksekse (>0.7) kalite seviyesi SIRALAMAYI")
    print("    degistirmiyor -> BLOK A'yi yalniz saha kalitesinde kosmak")
    print("    bedelsizdir. Dusukse akilli ornekleme bir seyi KACIRIYOR ve")
    print("    bu rapor o kadar zayiflar.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kalibre", action="store_true")
    ap.add_argument("--matris", action="store_true")
    ap.add_argument("--kapsam", action="store_true")
    ap.add_argument("--atalet", action="store_true",
                    help="ayni matris, ATALET koprusu adaylariyla")
    ap.add_argument("--hizli", action="store_true")
    ap.add_argument("--tohum", type=int, default=16)
    a = ap.parse_args()
    if not (a.kalibre or a.matris or a.kapsam or a.atalet):
        a.kalibre = a.matris = a.kapsam = True
    if a.atalet:
        # ⚠ Ikinci matris: PIKSEL koprusu ucusta ZARARLI cikti (bbox_ibvs.py:
        #   312-325, 2026-08-16). Repo ayni saatte ATALET surumunu ekledi.
        #   Ayni 714 hucre, ayni olcutler, ayni kazanma kurali.
        global ADAYLAR
        ADAYLAR = ADAYLAR_ATALET
        a.matris = True
        print("=" * 78)
        print("  ⚠ ATALET MATRISI -- adaylar KOR_KOPRU_ATALET_S ile")
        print("=" * 78)
    if a.kalibre:
        kalibre()
    if a.kapsam:
        kapsam()
    if a.matris:
        S, sonuc = matris(hizli=a.hizli, n_tohum=a.tohum)
        ozet = rapor(S, sonuc)
        rapor_net(S, sonuc, "TABLO 2A: HEDEF DURUMU",
                  lambda s: s["durum"], [d[0] for d in DURUMLAR])
        rapor_net(S, sonuc, "TABLO 3A: DEVIR MENZILI",
                  lambda s: "%.0fm" % s["menzil"],
                  ["%.0fm" % m for m in MENZILLER])
        rapor_net(S, sonuc, "TABLO 3B: DEVIR ASPECT",
                  lambda s: "%+.0f" % (s["aspect"] * s["yon_isaret"]),
                  ["%+.0f" % x for x in (-40, -20, 0, 20, 40)])
        rapor_net(S, sonuc, "TABLO 3C: DIKEY OFSET",
                  lambda s: "%.0fm" % s["dikey"],
                  ["%.0fm" % d for d in DIKEYLER])
        rapor_net(S, sonuc, "TABLO 4A: TESPIT KALITESI (blok B)",
                  lambda s: s["kalite"] if s["blok"] == "B" else None,
                  ["iyi", "saha", "kotu"])
        rapor_net(S, sonuc, "TABLO 4B: PIKSEL JITTER (blok B)",
                  lambda s: ("%.0fpx" % s["jitter"]) if s["blok"] == "B" else None,
                  ["0px", "1px", "3px"])
        adlar = rapor_kirilim(S, sonuc, ozet)
        rapor_bosluk(S, sonuc)
        # ── KALIBRASYON BAGIMSIZLIK SINAMASI ─────────────────────────────
        print("\n" + "-" * 78)
        print("  TABLO 7 -- SURUKLEME_EK = 0 (kalibrasyon KAPALI) ile TEKRAR")
        print("-" * 78)
        print("  Siralama degismiyorsa sonuc kalibrasyona DAYANMIYOR demektir.")
        S2, son2 = matris(hizli=True if a.hizli else False, n_tohum=8,
                          surukleme_ek=0.0, sessiz=True)
        print("  %-20s %5s %5s | %5s %5s" % ("ADAY", "KAZ*", "KAY*", "KAZ", "KAY"))
        for ad in [x[0] for x in ADAYLAR]:
            kaz = kay = 0
            for i in range(len(S2)):
                k = karar(son2[(i, ad)], son2[(i, ADAYLAR[0][0])])
                kaz += k > 0
                kay += k < 0
            print("  %-20s %5d %5d | %5d %5d"
                  % (ad, kaz, kay, ozet[ad]["kaz"], ozet[ad]["kay"]))
        print("  (* = surukleme_ek 0, 8 tohum)")


if __name__ == "__main__":
    main()

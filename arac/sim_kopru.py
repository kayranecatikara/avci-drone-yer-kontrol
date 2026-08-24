# -*- coding: utf-8 -*-
"""
================================================================================
  KOR KOPRU  --  tespit boslugunda komutu TAZELEME stratejileri + DAYANIKLILIK
================================================================================
⚠ SADECE OKUR. sim/tesis.py, sim/deney.py, arac/sim_omur.py ve kopru/ altindaki
yasa DEGISTIRILMEZ; hepsi aynen import edilir. Dongu burada yeniden yazildi
(kopru stratejileri sim_omur'da YOK) ama `sinama_gerileme()` ile kopru KAPALI
iken sim_omur.kosu() ile BIT-AYNI oldugu her kosuda dogrulanir.

OLCULEN KOK NEDEN (bugun, saha)
--------------------------------------------------------------------------------
Gorsel fazda yasa karelerin ancak %40'inda komut uretiyor. Kalan %60'ta kutu
yok ve `son_v_cmd` AYNEN tekrarlaniyor -- icinde yaw da var, yani BURUN DONUYOR.
    tespit VARKEN  |hiz yonu - hedefe yon| : medyan  8.3°   (iyi)
    faz GENELINDE                          : medyan 56.4°, %24'u >90°
Kisir dongu: tespit kesildi -> burun dondu -> kutu kadrajda kaymaya devam etti
-> kenara gitti -> tespit geri gelemedi.

⚠ KAYIP_M'i buyutmek bunu COZMEZ, kor sureyi UZATIR (ucusta olculdu: omur
1.91 -> 3.06 s ama iska duzelmedi).

ALTI STRATEJI (kestirici x kanal olarak dik iki eksene ayrildi)
--------------------------------------------------------------------------------
  kestirici : kutu kor karede NASIL tasinir
      sabit  1) son IKI tespitten px/s ile ileri tasi      (su an uygulanan)
      ivme   2) son UC tespitten px/s² ile ileri tasi
      ab     3) alfa-beta izleyici (kutu merkezi + hizi durum)
      sonum  4) SONUMLU: yer degistirme doyar / son LOS'a geri doner
      atalet 6) KENDI FIKRIM -- asagida
  kanal     : koprulenen kutudan HANGI komut alinir
      tam    tam komut (hiz + burun)
      burun  5) YALNIZ BURUN: hiz komutu DONAR, burun tazelenir

6) ATALET (ARAYICI) KOPRUSU -- kendi fikrim
--------------------------------------------------------------------------------
Piksel hizi UC seyi karistirir: (a) hedefin hareketi, (b) BIZIM yaw donusumuz,
(c) bizim otelememiz. Kor karede burun koprulenen kutuyu kovaladigi icin piksel
ekstrapolasyonu KENDI DUZELTMESINI geri besler -- pozitif geri besleme.
Cozum: kutuyu piksel yerine ATALET LOS acisinda tasi ve HER TIK GUNCEL yaw ile
yeniden projelendir:
        los(t) = los_son + kazanc * lam * (t - t_son)
        cx(t)  = CX + F * tan( los(t) - yaw(t) )
Burun donse bile kutu atalette YERINDE kalir -> dongu kirilir. kazanc=0 en
muhafazakar hal (LOS'u DONDUR); yasanin lam'i olculen sekilde 3-6 kat sisik
oldugu icin kazanc SUPURULUR, guvenilmez.

NE OLCULUR (ucu birden; tek basina iska yaniltir)
--------------------------------------------------------------------------------
  1) sapma  : faz GENELINDE |hiz yonu - hedefe yon| medyani ve >90° orani
              <- ASIL OLCUT. Saha: 56.4° / %24. Tespitli altkume: 8.3°.
  2) omur   : faz omru ve TESPITLI gecen sure (kor sure AYRI)
  3) iska   : en yakin gecis medyani ve <3 m orani (adil pencereli hali de)
"""
import math
import os
import random
import statistics as st
import sys

_BURASI = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(_BURASI)
sys.path.insert(0, os.path.join(KOK, "kopru", "gazebo_kaynak"))
sys.path.insert(0, os.path.join(KOK, "sim"))
sys.path.insert(0, _BURASI)

import tesis as T                                                  # noqa: E402
from tesis import (Avci, Hedef, Olcum, kadraj, F_YASA, CX,          # noqa: E402
                   TX_MAX, TY_MAX, HataAyari, Algi)
from control.guidance import bbox_ibvs as IB                        # noqa: E402
import sim_omur as O                                                # noqa: E402


# ══════════════════════════════════════════════════════════════════════════
#  KOPRU STRATEJILERI
# ══════════════════════════════════════════════════════════════════════════
class Kopru:
    """Taban sinif. `gozlem()` yalniz GERCEK tespitte, `tahmin()` kor karede.

    sure   : koprunun azami YASI (s). 0 = kapali.
    tavan  : piksel hizi tavani (px/s). Tek kotu kare kopruyu savurmasin.
             ⚠ Uygulanan yasada bu 900 px/s (bbox_ibvs.py:1155).
    kanal  : "tam" (hiz+burun) | "burun" (hiz DONAR, yalniz burun tazelenir)
    """

    ad = "yok"

    def __init__(self, sure=0.0, tavan=900.0, kanal="tam", dedup=False):
        self.sure = float(sure)
        self.tavan = float(tavan)
        self.kanal = kanal
        # ⚠ DEDUP -- IZDE GORULEN GERCEK ARIZA: yasa 21.3 Hz tikliyor, kamera
        # da 21.3 Hz ama FAZLARI kaymis; ayni teslim edilen kutu bazen IKI
        # tikte okunuyor (kutu_yas 0.048 -> 0.097). Piksel hizi o ciftte
        # SIFIR cikar ve kestirimi bozar. dedup=True ayni icerikli kutuyu
        # ikinci kez KAYDA ALMAZ. Uygulanan yasa bunu yapmiyor (sadik hal
        # False); ucuz bir duzeltme oldugu icin ayri olculdu.
        self.dedup = bool(dedup)
        self.ret = 0                 # tani: cift bayat oldugu icin reddedilen
        self.sifirla()

    def sifirla(self):
        self.g = []                  # (t, cx, cy, w, h, yaw, lam)

    def gozlem(self, t, cx, cy, w, h, yaw, lam):
        if (self.dedup and self.g
                and abs(cx - self.g[-1][1]) < 1e-9
                and abs(cy - self.g[-1][2]) < 1e-9):
            return                              # ayni kutu, YENI olcum degil
        self.g.append((t, cx, cy, w, h, yaw, lam))
        while len(self.g) > 4:
            self.g.pop(0)

    def yas(self, t):
        return (t - self.g[-1][0]) if self.g else 1e9

    def acik(self, t):
        return self.sure > 0.0 and bool(self.g) and 0.0 < self.yas(t) <= self.sure

    def _kis(self, v):
        return max(-self.tavan, min(self.tavan, v))

    # ⚠ Uygulanan yasanin kapisi: ardisik CIFT 0.6 s'ten eskiyse kopru YOK
    # (bbox_ibvs.py:1151). Sadik kalindi; reddedilen kareler sayiliyor.
    def _cift(self, i=-1):
        if len(self.g) < abs(i) + 1:
            return None
        a, b = self.g[i - 1], self.g[i]
        d = b[0] - a[0]
        if not (1e-3 < d < 0.6):
            return None
        return a, b, d

    def tahmin(self, t, yaw_simdi):
        return None

    def __repr__(self):
        return "%s(%.1fs, %.0fpx/s, %s)" % (self.ad, self.sure, self.tavan,
                                            self.kanal)


class KSabit(Kopru):
    """1) SABIT HIZ -- son iki tespitten px/s. Uygulanan yasanin AYNISI."""

    ad = "sabit"

    def tahmin(self, t, yaw_simdi):
        c = self._cift()
        if c is None:
            self.ret += 1
            return None
        a, b, d = c
        vx = self._kis((b[1] - a[1]) / d)
        vy = self._kis((b[2] - a[2]) / d)
        y = t - b[0]
        return (b[1] + vx * y, b[2] + vy * y, b[3], b[4])


class KIvme(Kopru):
    """2) SABIT IVME -- son UC tespit. Tavan ANLIK hiza uygulanir, yer
    degistirme trapezle integre edilir (yoksa tavan ivmeyi hic baglamaz)."""

    ad = "ivme"

    def tahmin(self, t, yaw_simdi):
        c2, c1 = self._cift(-1), self._cift(-2)
        if c2 is None:
            self.ret += 1
            return None
        a2, b2, d2 = c2
        v2x, v2y = (b2[1] - a2[1]) / d2, (b2[2] - a2[2]) / d2
        y = t - b2[0]
        if c1 is None:                       # ivme kestirilemiyor -> sabit hiz
            ax = ay = 0.0
        else:
            a1, b1, d1 = c1
            v1x, v1y = (b1[1] - a1[1]) / d1, (b1[2] - a1[2]) / d1
            orta = 0.5 * (d1 + d2)
            ax, ay = (v2x - v1x) / orta, (v2y - v1y) / orta
        vx0, vy0 = self._kis(v2x), self._kis(v2y)
        vx1, vy1 = self._kis(v2x + ax * y), self._kis(v2y + ay * y)
        return (b2[1] + 0.5 * (vx0 + vx1) * y,
                b2[2] + 0.5 * (vy0 + vy1) * y, b2[3], b2[4])


class KAB(Kopru):
    """3) ALFA-BETA izleyici -- durum (konum, piksel hizi).

    beta = alfa²/(2-alfa) : kritik sonumlu (standart alfa-beta bagintisi).
    Duzensiz araliklara dayanikli: her GERCEK tespitte olcum dt'siyle guncellenir.
    ⚠ 0.6 s'ten uzun boslukta izleyici YENIDEN BASLATILIR (hiz durumu artik
    hedefe degil, boslugun kendisine ait olurdu).
    """

    ad = "ab"

    def __init__(self, sure=0.0, tavan=900.0, kanal="tam", dedup=False, alfa=0.5):
        self.alfa = float(alfa)
        self.beta = self.alfa ** 2 / max(2.0 - self.alfa, 1e-6)
        Kopru.__init__(self, sure, tavan, kanal, dedup)

    def sifirla(self):
        Kopru.sifirla(self)
        self.x = self.y = self.t0 = None
        self.vx = self.vy = 0.0

    def gozlem(self, t, cx, cy, w, h, yaw, lam):
        Kopru.gozlem(self, t, cx, cy, w, h, yaw, lam)
        if self.x is None or self.t0 is None or (t - self.t0) > 0.6:
            self.x, self.y, self.t0 = cx, cy, t
            self.vx = self.vy = 0.0
            return
        d = t - self.t0
        if d <= 1e-6:
            return
        px, py = self.x + self.vx * d, self.y + self.vy * d
        rx, ry = cx - px, cy - py
        self.x, self.y = px + self.alfa * rx, py + self.alfa * ry
        self.vx = self._kis(self.vx + self.beta * rx / d)
        self.vy = self._kis(self.vy + self.beta * ry / d)
        self.t0 = t

    def tahmin(self, t, yaw_simdi):
        if self.x is None or self.t0 is None or not self.g:
            self.ret += 1
            return None
        y = t - self.t0
        return (self.x + self.vx * y, self.y + self.vy * y,
                self.g[-1][3], self.g[-1][4])

    def __repr__(self):
        return "ab%.1f(%.1fs, %.0fpx/s, %s)" % (self.alfa, self.sure,
                                                self.tavan, self.kanal)


class KSonum(Kopru):
    """4) SONUMLU KOPRU -- agresif ekstrapolasyon yerine sonumlu.

    IKI SEKIL var, ikisi de sinandi:
      geri=False (DOY) : yer degistirme = v*tau*(1-exp(-yas/tau)) -> DOYAR.
                         Ekstrapolasyon HIZI soner, kutu sabit bir ofsette durur.
      geri=True  (GERI): yer degistirme = v*yas*exp(-yas/tau) -> SON BILINEN
                         LOS'a GERI DONER (gorevde tarif edilen hal).
    ⚠ GERI seklinin bilinen riski: yer degistirme MONOTON DEGIL (once buyur,
    sonra kuculur). Bu, LOS kestiriminde SAHTE BIR YON DEGISIMI uretir ve PN
    onu N katlar. Olculdu, asagida.
    """

    ad = "sonum"

    def __init__(self, sure=0.0, tavan=900.0, kanal="tam", dedup=False,
                 tau=0.30, geri=False):
        self.tau = float(tau)
        self.geri = bool(geri)
        Kopru.__init__(self, sure, tavan, kanal, dedup)

    def tahmin(self, t, yaw_simdi):
        c = self._cift()
        if c is None:
            self.ret += 1
            return None
        a, b, d = c
        vx = self._kis((b[1] - a[1]) / d)
        vy = self._kis((b[2] - a[2]) / d)
        y = t - b[0]
        k = (y * math.exp(-y / self.tau) if self.geri
             else self.tau * (1.0 - math.exp(-y / self.tau)))
        return (b[1] + vx * k, b[2] + vy * k, b[3], b[4])

    def __repr__(self):
        return "sonum%s%.2f(%.1fs, %.0fpx/s, %s)" % (
            "G" if self.geri else "D", self.tau, self.sure, self.tavan, self.kanal)


class KAtalet(Kopru):
    """6) ATALET (ARAYICI) KOPRUSU -- KENDI FIKRIM.

    Piksel yerine ATALET LOS acisini tasi, kutuyu GUNCEL yaw ile yeniden uret:
        los(t) = los_son + kazanc * lam_son * (t - t_son)
        cx(t)  = CX_NISAN + F * tan( los(t) - yaw(t) )
    Boylece bizim BURUN DONUSUMUZ kopruye sizmaz; kor karede burun koprulenen
    kutuyu kovalarken kendi duzeltmesini geri beslemez.
    kazanc = 0.0 -> LOS'u DONDUR (en muhafazakar, hedef manevrasina KOR)
    kazanc = 1.0 -> yasanin lam'i ile tam tasi (lam OLCULEN sekilde 3-6 kat
                    sisik oldugu icin bu tehlikeli; supuruldu)
    ⚠ KAPSAM: yalniz AZIMUT. Dikey kanal (cy) sonumlu piksel tasimasi ile
    birakildi -- olculen olumlerin %0.9'u dikeyden, %32'si YANDAN; geri
    besleme dongusu azimutta yasiyor.
    """

    ad = "atalet"

    def __init__(self, sure=0.0, tavan=900.0, kanal="tam", dedup=False,
                 kazanc=0.0, tau=0.30):
        self.kazanc = float(kazanc)
        self.tau = float(tau)
        Kopru.__init__(self, sure, tavan, kanal, dedup)

    def tahmin(self, t, yaw_simdi):
        if not self.g:
            self.ret += 1
            return None
        t2, x2, y2, w2, h2, yaw2, lam2 = self.g[-1]
        y = t - t2
        los = yaw2 + math.atan((x2 - IB.Cfg.CX_NISAN) / F_YASA)
        los += self.kazanc * lam2 * y
        eps = (los - yaw_simdi + math.pi) % (2 * math.pi) - math.pi
        # kadraj disina tasmayi engelle (tan patlamasin): sinir 70° > 61°
        eps = max(-1.2217, min(1.2217, eps))
        cx = IB.Cfg.CX_NISAN + F_YASA * math.tan(eps)
        # DIKEY: sonumlu piksel tasimasi (azimut disi kanal)
        cy = y2
        c = self._cift()
        if c is not None:
            a, b, d = c
            vy = self._kis((b[2] - a[2]) / d)
            cy = y2 + vy * self.tau * (1.0 - math.exp(-y / self.tau))
        return (cx, cy, w2, h2)

    def __repr__(self):
        return "atalet%.1f(%.1fs, %.0fpx/s, %s)" % (self.kazanc, self.sure,
                                                    self.tavan, self.kanal)


KESTIRICI = {"sabit": KSabit, "ivme": KIvme, "ab": KAB,
             "sonum": KSonum, "atalet": KAtalet}


def kopru_yap(kestirici, sure, tavan=900.0, kanal="tam", **kw):
    if not kestirici or sure <= 0.0:
        return None
    return KESTIRICI[kestirici](sure=sure, tavan=tavan, kanal=kanal, **kw)


# ══════════════════════════════════════════════════════════════════════════
#  ANGAJMAN
# ══════════════════════════════════════════════════════════════════════════
def kosu(cfg=O.SahaCfg, hata=None, devir_m=O.DEVIR, sure=20.0, dt=1 / 62.0,
         tohum=0, faz0=0.0, devir_aci=0.0, hedef_yon=+1,
         pencere=0.25, tau=0.10, yasa_ici=True,
         kayip_m=20, dedektor=None, kopru=None, kopru_temas=False,
         lam_kopru=True, kor_pencere=None):
    """Tek gorsel faz.

    kopru       : Kopru | None   (None = eski davranis: son komut TEKRARLANIR)
    kopru_temas : koprulenen kare "temas" sayilsin mi (kayip sayacini sifirlar)
                  ⚠ VARSAYILAN FALSE -- yasadaki durustluk kurali: kopru
                  karesi tespit SAYILMAZ, faz yine zamaninda biter.
    lam_kopru   : koprulenen kutu lam (LOS hizi) kestirimini BESLESIN mi.
                  True = uygulanan yasayla sadik (kopru kutusu ayni yoldan
                  gecer). False = lam yalniz GERCEK tespitlerden.
    kor_pencere : (t0, t1) -- SINAV modu: bu aralikta tespit ZORLA kesilir.
    """
    if hata is None:
        hata = HataAyari()
    if dedektor is not None:
        dedektor = dedektor.klon(tohum)
        hata = O._hata_kopya(hata, tespit_kaybi=False,
                             yanlis_hiz=dedektor.yanlis_hiz(hata.yanlis_hiz))
    algi = Algi(hata, tohum=tohum)
    rnd = random.Random(7919 * tohum + 13)
    if kopru is not None:
        kopru.sifirla()
        kopru.ret = 0

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

    kop_kare = 0
    kop_kurtarma = 0
    kop_acikti = False

    t_ilk_kutu = t_son_kutu = None
    n_kutu = 0
    n_tik = 0
    bosluk = 0
    kurtarilan = []
    tik_ilk = tik_son = None
    n_tik_temas = 0
    son_eps = son_boyut = None
    lam_ic = []
    en_yakin_kesik = 1e9
    kilit = False

    # ── ASIL OLCUT: |hiz yonu - hedefe olan yon| (her SIM adiminda) ────────
    sapma_hep = []
    sapma_kutulu = []
    sapma_kor = []
    n_adim_kutulu = 0
    kutulu_tik = False          # son yasa tikinde GERCEK kutu var miydi
    # sinav tanisi: koprunun LOS hatasi (derece) ve o andaki kopru YASI
    kop_los_hata = []           # (yas, hata_deg)
    t_kurtarma = None           # zorlanmis pencereden SONRA ilk GERCEK tespit
    son_v_cmd = None            # kanal="burun" icin dondurulan hiz komutu

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

        # ── SAPMA (asil olcut) ────────────────────────────────────────────
        vmag = math.hypot(av.vx, av.vy)
        if vmag > 1.0:
            s_ = abs(math.degrees(
                (math.atan2(av.vy, av.vx) - math.atan2(hy - av.y, hx - av.x)
                 + math.pi) % (2 * math.pi) - math.pi))
            sapma_hep.append(s_)
            if kutulu_tik:
                sapma_kutulu.append(s_)
                n_adim_kutulu += 1
            else:
                sapma_kor.append(s_)

        # ── DEDEKTOR KAPISI (sim_omur ile AYNI sira, AYNI rastgele akis) ──
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
        # SINAV: zorlanmis kor pencere (rastgele akisi BOZMAZ -- en sonda)
        if kor_pencere is not None and kor_pencere[0] <= t < kor_pencere[1]:
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
        kutulu_tik = poz is not None

        # ── KOPRU ─────────────────────────────────────────────────────────
        kopru_kare = False
        if poz is not None:
            if kopru is not None and (not kopru.g
                                      or abs(t - kopru.g[-1][0]) > 1e-9):
                kopru.gozlem(t, poz[0], poz[1], poz[2], poz[3], yaw_olc, lam_f)
            if kop_acikti:
                kop_kurtarma += 1
            kop_acikti = False
            if (kor_pencere is not None and t_kurtarma is None
                    and t >= kor_pencere[1]):
                t_kurtarma = t - kor_pencere[1]
        elif kopru is not None and kopru.acik(t):
            tah = kopru.tahmin(t, yaw_olc)
            if tah is not None:
                poz = tah
                kopru_kare = True
                kop_kare += 1
                kop_acikti = True
                los_k = yaw_olc + math.atan((tah[0] - cfg.CX_NISAN) / F_YASA)
                los_g = math.atan2(hy - av.y, hx - av.x)
                kop_los_hata.append((kopru.yas(t), abs(math.degrees(
                    (los_k - los_g + math.pi) % (2 * math.pi) - math.pi))))

        if poz is None or kopru_kare:
            bosluk += 1
        if poz is None:
            kayip += 1
            if kayip >= kayip_m:
                break
        else:
            if not kopru_kare:
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
                tx, ty, onde = O._aci(av, hx, hy, hz)
                son_eps = abs(math.degrees(math.atan(tx)))
                son_boyut = math.sqrt(k[2] * k[3]) if k else None
            elif kopru_temas:
                kayip = 0
            else:
                kayip += 1
                if kayip >= kayip_m:
                    break
            cx, cy, w, h = poz
            # ── LOS HIZI ──────────────────────────────────────────────────
            # ⚠ lam_kopru=False iken KOPRU karesi lam'i BESLEMEZ: kopru kendi
            # ekstrapolasyonunu LOS hizi olarak geri okuyup PN'e vermesin.
            if lam_kopru or not kopru_kare:
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
                        lam_f = (sum((g[0] - tm) * (g[1] - lm)
                                     for g in gecmis) / sxx) if sxx > 1e-12 else 0.0
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
            hiz_I_yedek, psi_v_yedek = hiz_I, psi_v_yasa
            vx, vy, vz, yaw_cmd, hiz_I, tani = IB.komut(
                cx, cy, w, h, yaw_olc, hiz_I, dt_yasa, cfg, terminal,
                (lam_f, 0.0),
                pitch_olc, av.vz, None, roll_olc, av.yaw_hizi, psi_v_yasa)
            if yasa_ici:
                psi_v_yasa = tani.get("psi_v")
            # ── KANAL: "burun" -> HIZ DONAR, yalniz burun tazelenir ───────
            if (kopru_kare and kopru is not None and kopru.kanal == "burun"
                    and son_v_cmd is not None):
                vx, vy, vz = son_v_cmd
                # hiz durumu (integral + PN yonu) KIRLETILMEZ
                hiz_I, psi_v_yasa = hiz_I_yedek, psi_v_yedek
            else:
                son_v_cmd = (vx, vy, vz)
            av.setpoint(vx, vy, vz, yaw_cmd, t)
        av.adim(dt, t)
        t += dt

    hx, hy, hz, _, _, _ = hed.durum()
    tx, ty, onde = O._aci(av, hx, hy, hz)
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
    n_ad = max(len(sapma_hep), 1)
    return {
        "en_yakin": en_yakin,
        "iska_adil": en_yakin_kesik if kilit else en_yakin,
        "omur": t, "temas": temas,
        "kesildi": t >= sure - 1e-6,
        # TESPITLI / KOR sure: son yasa tikinde gercek kutu var miydi
        "tespitli_s": n_adim_kutulu * dt,
        "kor_s": (len(sapma_hep) - n_adim_kutulu) * dt,
        "gorus": gor / max(top, 1),
        "n_kutu": n_kutu,
        "sureklilik": (n_kutu / max(1, tik_son - tik_ilk + 1)
                       if (tik_ilk is not None and tik_son > tik_ilk) else float("nan")),
        "kutu_orani_faz": n_kutu / max(1, n_tik),
        "olum": olum, "olum_eps": son_eps, "olum_kutu": son_boyut,
        "lam_p50": O._med(lam_ic),
        "kop_kare": kop_kare, "kop_kurtarma": kop_kurtarma,
        "kop_ret": (kopru.ret if kopru is not None else 0),
        "kop_los_hata": (O._med([x[1] for x in kop_los_hata])
                         if kop_los_hata else float("nan")),
        # koprunun SONUNDAKI hata (yas > yarim kopru suresi) -- asil sinav
        "kop_los_son": O._med([e for y, e in kop_los_hata
                               if kopru is not None and y > 0.5 * kopru.sure]),
        "kurtarma_s": t_kurtarma if t_kurtarma is not None else float("nan"),
        "kurtarilan": kurtarilan,
        # ── ASIL OLCUT ────────────────────────────────────────────────────
        "sapma": O._med(sapma_hep) if sapma_hep else float("nan"),
        "sapma90": sum(1 for x in sapma_hep if x > 90.0) / n_ad,
        "sapma_kutulu": O._med(sapma_kutulu) if sapma_kutulu else float("nan"),
        "sapma_kor": O._med(sapma_kor) if sapma_kor else float("nan"),
    }


def parti(n=120, **kw):
    return [kosu(faz0=i / n, tohum=i, **kw) for i in range(n)]


def _iyi(x):
    return [v for v in x if v == v]


def ozet(r):
    e = [x["en_yakin"] for x in r]
    a = [x["iska_adil"] for x in r]
    return {
        "sapma": O._med(_iyi([x["sapma"] for x in r])),
        "s90": O._med(_iyi([x["sapma90"] for x in r])),
        "s90ort": sum(x["sapma90"] for x in r) / len(r),
        "sk": O._med(_iyi([x["sapma_kutulu"] for x in r])),
        "skor": O._med(_iyi([x["sapma_kor"] for x in r])),
        "omur": O._med([x["omur"] for x in r]),
        "tesp": O._med([x["tespitli_s"] for x in r]),
        "kor": O._med([x["kor_s"] for x in r]),
        "iska": O._med(e), "iyi": min(e), "adil": O._med(a),
        "v3": sum(1 for x in e if x < 3.0),
        "v3a": sum(1 for x in a if x < 3.0),
        "sur": O._med(_iyi([x["sureklilik"] for x in r])),
        "kutu": O._med([x["kutu_orani_faz"] for x in r]),
        "kop": O._med([x["kop_kare"] for x in r]),
        "kurt": sum(x["kop_kurtarma"] for x in r),
        "ret": sum(x["kop_ret"] for x in r),
        "ici": sum(1 for x in r if x["olum"] == "ici") / len(r),
        # OLUM ANINDAKI |eps| -- saha 52° (kadraj siniri 61°). Bu, sapma
        # olcutunun tezgahta URETILIP URETILMEDIGININ dogrudan gostergesi.
        "eps": O._med([x["olum_eps"] for x in r if x["olum_eps"] is not None]),
        "n": len(r),
    }


BAS = ("  %-24s %6s %5s %6s %6s %6s %6s %6s %5s %5s %5s %5s" %
       ("kurulum", "sapma", ">90°", "sap|k", "omur", "tespit", "kor",
        "iska", "adil", "eps", "<3m", "kurt"))
CIZ = "  " + "-" * 99


def satir(ad, s):
    return ("  %-24s %5.1f° %4.0f%% %5.1f° %5.2fs %5.2fs %5.2fs %5.2fm %4.2fm "
            "%4.0f° %2d/%-2d %4d" %
            (ad, s["sapma"], 100 * s["s90ort"], s["sk"], s["omur"], s["tesp"],
             s["kor"], s["iska"], s["adil"], s["eps"], s["v3"], s["n"],
             s["kurt"]))


# ══════════════════════════════════════════════════════════════════════════
#  GERILEME SINAMASI -- kopru KAPALI iken sim_omur.kosu() ile BIT-AYNI mi?
# ══════════════════════════════════════════════════════════════════════════
def sinama_gerileme(n=16):
    kotu = []
    for i in range(n):
        for det in (None, "B"):
            kw = dict(faz0=i / n, tohum=i, devir_m=13.0, sure=8.0,
                      pencere=0.25, yasa_ici=True, cfg=O.SahaCfg, kayip_m=20)
            d1 = None if det is None else O.tezgah_b()
            d2 = None if det is None else O.tezgah_b()
            a = O.kosu(dedektor=d1, kopru_n=0, **kw)
            b = kosu(dedektor=d2, kopru=None, **kw)
            for alan_a, alan_b in (("en_yakin", "en_yakin"), ("omur", "omur"),
                                   ("temas", "temas"), ("n_kutu", "n_kutu"),
                                   ("iska_adil", "iska_adil")):
                if abs(a[alan_a] - b[alan_b]) > 1e-9:
                    kotu.append((i, det, alan_a, a[alan_a], b[alan_b]))
    print("  GERILEME (sim_kopru == sim_omur, kopru kapali): %s" %
          ("TAMAM (%d/%d x2 dedektor)" % (n, n) if not kotu else "KALDI"))
    for x in kotu[:8]:
        print("    ! %s" % (x,))
    return kotu


# ══════════════════════════════════════════════════════════════════════════
#  TEZGAH -- sim_omur'un sahaya kalibre "Tezgah B"si (ORNEK ALINDI)
# ══════════════════════════════════════════════════════════════════════════
N = 120
SURE = (0.0, 0.2, 0.4, 0.6, 1.0)
TAVAN = (100.0, 200.0, 400.0, 900.0)

SAHA = {"sapma": 56.4, "s90": 24.0, "sk": 8.3, "omur": 1.28, "temas": 0.69,
        "iska": 12.73, "iyi": 3.71, "kutu": 0.41, "sur": 0.785}


def kos(ad, kopru=None, n=N, det=None, **kw):
    d = O.tezgah_b(**(det or {}))
    kw.setdefault("devir_m", O.DEVIR)
    kw.setdefault("sure", 20.0)
    r = parti(n=n, dedektor=d, kopru=kopru, **kw)
    s = ozet(r)
    print(satir(ad, s), flush=True)
    return s


# ══════════════════════════════════════════════════════════════════════════
#  KRITIK SINAV -- kopru NE ZAMAN ZARAR VERIR
# ══════════════════════════════════════════════════════════════════════════
# Hedefin oval pisti: duz1 [0, L)  donus1 [L, L+piR)  duz2  donus2
#   L = 104.78 m, piR = 160.22 m, cevre = 530 m, hiz 17.98 m/s
# Kor pencere t_KOR'da baslar; hedefin O ANDAKI yay konumu senaryoyu belirler.
L_DUZ = (Olcum.TUR_UZUNLUK - 2 * math.pi * Olcum.DONUS_YARICAP) / 2.0
CEVRE = 2 * L_DUZ + 2 * math.pi * Olcum.DONUS_YARICAP
T_KOR = 1.2               # s -- faz oturduktan sonra
L_KOR = 1.0               # s -- sinav penceresi (en uzun kopru suresi kadar)

SENARYO = {
    # ad          : hedefin t_KOR'daki yay konumu (m)
    "duz":        40.0,    # bastan sona DUZ
    "duz>donus":  100.0,   # kor BASLADIKTAN sonra donuse girer (L=104.78)
    "donus_orta": 180.0,   # kor DONUSUN ORTASINDA baslar, donuste kalir
    "donus>duz":  258.0,   # kor donuste baslar, hedef DUZE CIKAR (264.99)
}


def _faz0(s_kor):
    return ((s_kor - Olcum.HEDEF_HIZ * T_KOR) % CEVRE) / CEVRE


def sinav_kosu(kopru, s_kor, tohum=0, hedef_yon=+1, devir_m=O.DEVIR):
    """SINAV: tespit kaybi KAPALI, tek kor pencere ZORLANMIS.

    ⚠ Olcum hatasi (bayat yaw, kutu gecikmesi, kenar yanliligi, yasa dongusu)
    ACIK kalir -- gorevin kurali. YALNIZ `yanlis nesne` kapatildi: 153 px'lik
    rastgele bir sicrama manevra sinyalini bogar ve sinav manevrayi olcuyor.
    """
    h = O._hata_kopya(HataAyari(), tespit_kaybi=False, yanlis_hiz=0.0)
    return kosu(hata=h, dedektor=None, kopru=kopru, tohum=tohum,
                faz0=_faz0(s_kor), hedef_yon=hedef_yon, devir_m=devir_m,
                sure=T_KOR + L_KOR + 2.5, kayip_m=200,
                kor_pencere=(T_KOR, T_KOR + L_KOR))


def sinav(kopru, tekrar=24):
    """Her senaryo icin (sapma, kurtarma, iska). Cift yon, yay ofseti jitter."""
    out = {}
    for ad, s0 in SENARYO.items():
        r = []
        for i in range(tekrar):
            ds = (i % 4 - 1.5) * 2.5                 # +-3.75 m yay ofseti
            yn = +1 if i < tekrar // 2 else -1
            r.append(sinav_kosu(kopru, s0 + ds, tohum=i, hedef_yon=yn))
        kur = _iyi([x["kurtarma_s"] for x in r])
        out[ad] = {
            # KOR PENCEREDEKI nisan hatasi -- sinavin ASIL olcutu
            "kor": O._med(_iyi([x["sapma_kor"] for x in r])),
            "sapma": O._med(_iyi([x["sapma"] for x in r])),
            "s90": sum(x["sapma90"] for x in r) / len(r),
            # koprunun kendi kestirim hatasi, pencerenin SONUNDA
            "los": O._med(_iyi([x["kop_los_son"] for x in r])),
            "adil": O._med([x["iska_adil"] for x in r]),
            # KURTARMA: pencere bittikten sonra tespit kac saniyede dondu
            "kur": O._med(kur) if kur else float("nan"),
            "kuroran": len(kur) / len(r),
            "omur": O._med([x["omur"] for x in r]),
            "n": len(r),
        }
    return out


def senaryo_agirlik(l_kor):
    """Kor pencerenin senaryolara dusme OLASILIGI (oval pistte duzgun dagilim).

    Yay uzunlugu A = v*l_kor. Pistte 2 duz->donus ve 2 donus->duz siniri var;
    pencere bir siniri iceriyorsa gecis senaryosudur (P = A/CEVRE her sinir).
    """
    a = Olcum.HEDEF_HIZ * l_kor
    g = a / CEVRE
    return {"duz": max(2 * L_DUZ - 2 * a, 0.0) / CEVRE,
            "duz>donus": 2 * g,
            "donus_orta": max(2 * math.pi * Olcum.DONUS_YARICAP - 2 * a, 0.0) / CEVRE,
            "donus>duz": 2 * g}


# ══════════════════════════════════════════════════════════════════════════
def main():
    ne = sys.argv[1] if len(sys.argv) > 1 else "hepsi"

    if ne in ("hepsi", "sinama"):
        sinama_gerileme()
        T.dogrula()
        print()

    if ne in ("hepsi", "taban"):
        print("  == 0) TEZGAH SAHAYI URETIYOR MU? (Tezgah B, hata ACIK) ==")
        print(BAS)
        print("  %-24s %5.1f° %4.0f%% %5.1f° %5.2fs %5s %5s %5.2fm %5s %5s %5s"
              % ("SAHA OLCUMU", SAHA["sapma"], SAHA["s90"], SAHA["sk"],
                 SAHA["omur"], "-", "-", SAHA["iska"], "-", "-", "-"))
        print(CIZ)
        kos("B taban (kopru YOK)")
        kos("B KAYIP_M 45", kayip_m=45)
        print()

    if ne in ("hepsi", "strateji"):
        # ⚠ IKI CALISMA NOKTASI. K20 saha varsayilani AMA tezgah orada
        # patolojiyi URETMIYOR (sapma 6.3° / saha 56.4°) -> kaldiraca SAGIR.
        # K45 tezgahin patolojiyi URETTIGI en yakin nokta (23.9° / %10).
        # Ikisi de basiliyor; siralama K45'ten okunur, K20 "zarar var mi"dir.
        for km in (45, 20):
            print("  == 1) STRATEJI x KOPRU SURESI  [KAYIP_M %d, tavan 900] =="
                  % km)
            print(BAS)
            print(CIZ)
            kos("kopru YOK", kayip_m=km)
            for kes in ("sabit", "ivme", "ab", "sonum", "atalet"):
                for s in SURE[1:]:
                    kos("%-6s %.1fs" % (kes, s), kopru_yap(kes, s), kayip_m=km)
                print(CIZ)
            print("  -- 5) YALNIZ BURUN (hiz DONAR, burun tazelenir) --")
            for kes in ("sabit", "atalet"):
                for s in SURE[1:]:
                    kos("BURUN %-6s %.1fs" % (kes, s),
                        kopru_yap(kes, s, kanal="burun"), kayip_m=km)
                print(CIZ)
            print()

    if ne in ("hepsi", "tavan"):
        # ⚠ K45'te kosulur: K20'de tezgah patolojiyi uretmedigi icin tavan
        # taramasi TAMAMEN DUZ cikiyor (olculdu) ve yanlis "duyarsiz" der.
        print("  == 2) PIKSEL HIZI TAVANI  [KAYIP_M 45] ==")
        print(BAS)
        print(CIZ)
        kos("kopru YOK", kayip_m=45)
        print(CIZ)
        for kes in ("sabit", "atalet"):
            for s in (0.4, 1.0):
                for tv in TAVAN:
                    kos("%-6s %.1fs tavan %3.0f" % (kes, s, tv),
                        kopru_yap(kes, s, tavan=tv), kayip_m=45)
                print(CIZ)
        print("  == 2b) KOPRU SURESI UCURUMU  [KAYIP_M 45; kapi 45/21.3=2.11 s] ==")
        for s in (1.0, 1.5, 2.0, 2.5, 3.0):
            kos("atalet %.1fs" % s, kopru_yap("atalet", s), kayip_m=45)
        print(CIZ)
        for s in (1.0, 1.5, 2.0, 2.5, 3.0):
            kos("sabit  %.1fs" % s, kopru_yap("sabit", s), kayip_m=45)
        print(CIZ)
        print("  == 2c) atalet KAZANCI (lam ile tasima)  [KAYIP_M 45] ==")
        for kz in (0.0, 0.3, 0.6, 1.0):
            kos("atalet kazanc %.1f 1.0s" % kz,
                kopru_yap("atalet", 1.0, kazanc=kz), kayip_m=45)
        print()

    if ne in ("hepsi", "ayar"):
        print("  == 3) STRATEJI IC AYARLARI ==")
        print(BAS)
        print(CIZ)
        for al in (0.3, 0.5, 0.8):
            kos("ab alfa %.1f 0.6s" % al, kopru_yap("ab", 0.6, alfa=al))
        print(CIZ)
        for tu in (0.15, 0.30, 0.60):
            kos("sonumD tau %.2f 0.6s" % tu, kopru_yap("sonum", 0.6, tau=tu))
        for tu in (0.15, 0.30, 0.60):
            kos("sonumG tau %.2f 0.6s" % tu,
                kopru_yap("sonum", 0.6, tau=tu, geri=True))
        print(CIZ)
        for kz in (0.0, 0.3, 0.6, 1.0):
            kos("atalet kazanc %.1f 0.6s" % kz,
                kopru_yap("atalet", 0.6, kazanc=kz))
        print(CIZ)
        print("  -- lam'i kopru BESLESIN mi (PN geri beslemesi) --")
        for kes in ("sabit", "atalet"):
            kos("%s 0.6s lam ACIK" % kes, kopru_yap(kes, 0.6), lam_kopru=True)
            kos("%s 0.6s lam KAPALI" % kes, kopru_yap(kes, 0.6), lam_kopru=False)
        print(CIZ)
        print("  -- kopru TEMAS sayilsin mi (kayip sayacini sifirlar) --")
        for kes in ("sabit", "atalet"):
            kos("%s 0.6s temas YOK" % kes, kopru_yap(kes, 0.6))
            kos("%s 0.6s temas VAR" % kes, kopru_yap(kes, 0.6), kopru_temas=True)
        print()

    if ne in ("hepsi", "sinav"):
        print("  == 4) KRITIK SINAV -- kopru NE ZAMAN ZARAR VERIR ==")
        print("  Kor pencere %.1f s, t=%.1f s'de ZORLA baslar. Tespit kaybi"
              " KAPALI." % (L_KOR, T_KOR))
        ag = senaryo_agirlik(L_KOR)
        print("  senaryo agirliklari (oval pist, %.1f s pencere): %s" %
              (L_KOR, ", ".join("%s %.1f%%" % (k, 100 * v) for k, v in ag.items())))
        print()
        adaylar = [("kopru YOK", None)]
        for kes in ("sabit", "ivme", "ab", "sonum", "atalet"):
            adaylar.append((kes, kopru_yap(kes, 1.0)))
        # ⚠ ADIL OLSUN: piksel tabanli koprulerin 900 px/s tavani, IZDE
        # olculen yaw limit-cevriminde (±120 °/s = 349 px/s taban, tepe
        # 1534 px/s) neredeyse TAVANSIZ demek. Dusuk tavanla da sinanir.
        for tv in (100.0, 200.0):
            adaylar.append(("sabit tav%.0f" % tv, kopru_yap("sabit", 1.0, tavan=tv)))
        adaylar.append(("sabit dedup", kopru_yap("sabit", 1.0, tavan=200.0,
                                                 dedup=True)))
        adaylar.append(("ab tav200", kopru_yap("ab", 1.0, tavan=200.0)))
        adaylar.append(("sonumD tav200", kopru_yap("sonum", 1.0, tavan=200.0)))
        adaylar.append(("atalet k1.0", kopru_yap("atalet", 1.0, kazanc=1.0)))
        adaylar.append(("BURUN sabit", kopru_yap("sabit", 1.0, kanal="burun")))
        adaylar.append(("BURUN sab200", kopru_yap("sabit", 1.0, tavan=200.0,
                                                  kanal="burun")))
        adaylar.append(("BURUN atalet", kopru_yap("atalet", 1.0, kanal="burun")))

        sonuc = {}
        print("  -- KOR PENCEREDEKI NISAN HATASI (|hiz yonu - hedefe yon|) --")
        print("  %-14s" % "strateji" + "".join(" %11s" % s for s in SENARYO))
        for ad, kp in adaylar:
            sonuc[ad] = sinav(kp)
            print("  %-14s" % ad + "".join(
                " %10.1f°" % sonuc[ad][s]["kor"] for s in SENARYO), flush=True)

        print()
        print("  -- KOPRUNUN KENDI LOS KESTIRIM HATASI (pencerenin SONUNDA) --")
        print("  %-14s" % "strateji" + "".join(" %11s" % s for s in SENARYO))
        for ad, _ in adaylar:
            if ad == "kopru YOK":
                continue
            print("  %-14s" % ad + "".join(
                " %10.1f°" % sonuc[ad][s]["los"] for s in SENARYO))

        print()
        print("  -- KURTARMA: pencere bitince tespit kac s'de dondu --")
        print("  %-14s" % "strateji" + "".join(" %11s" % s for s in SENARYO))
        for ad, _ in adaylar:
            print("  %-14s" % ad + "".join(
                " %10.2fs" % sonuc[ad][s]["kur"] for s in SENARYO))

        print()
        print("  -- TABANA GORE NET (kor sapma farki; + = KOPRU ZARARLI) --")
        tb = sonuc["kopru YOK"]
        print("  %-14s" % "strateji" + "".join(" %11s" % s for s in SENARYO)
              + " |  AGIRLIKLI NET")
        for ad, _ in adaylar:
            if ad == "kopru YOK":
                continue
            d = {s: sonuc[ad][s]["kor"] - tb[s]["kor"] for s in SENARYO}
            net = sum(ag[s] * d[s] for s in SENARYO)
            print("  %-14s" % ad + "".join(" %+10.1f°" % d[s] for s in SENARYO)
                  + " | %+9.1f°" % net)
        print()

    if ne in ("hepsi", "final"):
        print("  == 5) FINAL: yayla adaylari, saglamlik (devir menzili/yon) ==")
        print(BAS)
        print(CIZ)
        adaylar = [("kopru YOK", None),
                   ("sabit 0.4s", kopru_yap("sabit", 0.4)),
                   ("sabit 0.6s", kopru_yap("sabit", 0.6)),
                   ("atalet 0.6s", kopru_yap("atalet", 0.6)),
                   ("atalet 1.0s", kopru_yap("atalet", 1.0)),
                   ("BURUN atalet 0.6s", kopru_yap("atalet", 0.6, kanal="burun"))]
        for dm in (13.0, 17.7, 22.0):
            for ad, kp in adaylar:
                kos("%-18s d%.0f" % (ad, dm), kp, devir_m=dm)
            print(CIZ)
        for ad, kp in adaylar:
            kos("%-18s yon-1" % ad, kp, hedef_yon=-1)
        print(CIZ)
        print("  -- UCURUM taramasi: cok uzun kopru --")
        for s in (1.0, 1.5, 2.0, 3.0):
            kos("atalet %.1fs" % s, kopru_yap("atalet", s))
            kos("sabit  %.1fs" % s, kopru_yap("sabit", s))
        print()


if __name__ == "__main__":
    main()

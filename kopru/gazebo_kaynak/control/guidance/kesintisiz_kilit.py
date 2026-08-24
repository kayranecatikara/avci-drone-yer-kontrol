# -*- coding: utf-8 -*-
"""
================================================================================
 kesintisiz_kilit.py — GERCEK "5 saniye KESINTISIZ kilit" kapisi + denetim kaydi
================================================================================
NEDEN VAR (2026-08-17, olculerek bulundu)
--------------------------------------------------------------------------
Kullanici sarti: "arac hedefi 5 saniye KESINTISIZ kilitte tutmadan terminal /
vurus fazina gecmemeli". Depoda bu sarti UYGULAYAN hicbir kapi YOKTU:

  1) GPS -> VISUAL devri (supervisor.py, ETKIN mod OTO) olcut olarak
     `ardisik` degiskenini kullaniyor: KESINTISIZ KARE SAYISI (KILIT_N=10).
     Olculen dedektor hizi 2026-08-17'de medyan 0.050 s/kare (20.0 fps),
     ortalama 0.0568 s/kare (17.6 fps)  ->  10 kare = 0.45-0.51 SANIYE.
     Yani kapi fiilen ~0.5 s sart kosuyordu, 5 s degil.

  2) `SupCfg.KILIT_SURE_S = 5.0` VAR ama YALNIZ `ZORLA_MOD == "GORSEL"`
     kolunda okunuyor (supervisor.py:531). Olculen: 62 karar logunun
     2026-08-17 tarihli 32'sinde mod %100 "OTO" -> o kol HIC calismadi.

  3) O kol calissa bile olcut `KilitSayaci.sure`dir ve o sayac 10 s'lik kayan
     pencerede KUMULATIF toplar (kilit_sayaci.py:96-101), KESINTISIZ DEGIL.
     %50 gorunen bir hedef 10 saniyede 5.0'a ulasir -> "5 s kesintisiz" sarti
     saglanmadan kapi acilir.

  4) TERMINAL mandali (bbox_ibvs.py:1550) kilit suresine HIC bakmiyor:
     yalniz `not kopru_kare and conf > 0 and boyut >= TERMINAL_BOYUT` + nisan
     kapisi. Tek bir gercek karede terminale taahhut edilebiliyor.
     Olculen: mandal aninda kesintisiz gercek tespit medyani 0.16 s (2026-08-17).

Bu modul, EKSIK olan tek seyi ekler: gercekten KESINTISIZ olcen bir sayac,
`AVCI_KILIT_S` ile kapili (VARSAYILAN 0 = KAPALI, davranis BIT-AYNI) ve
kapi kapaliyken de calisan bir DENETIM KAYDI.

KILIT TANIMI (bu modulun sozlesmesi)
--------------------------------------------------------------------------
Bir kare kilide SAYILIR ancak ve ancak:
  * GERCEK tespit var (dedektor kutusu) — hayalet/kor-kopru karesi DEGIL
  * conf >= CONF_MIN (varsayilan 0.35, dedektorun kendi esigi)
  * kutu gecerli (w > 0, h > 0)
  * hedef merkezi KADRAJDA (kenar payi KADRAJ_PAY ile)
Sayilmayan kare BOSLUKTUR. Bosluk toleransi: ust uste en fazla BOSLUK_KARE
kare VE en fazla BOSLUK_S saniye. Bu asilirsa kilit KIRILIR ve sure SIFIRDAN
baslar. Tolerans icindeki bosluk sureyi sifirlamaz (dedektor titremesi kilidi
oldurmesin) ama kaydedilir — denetim CSV'sinde kac kare tolere edildigi yazar.

⚠ OLCULEN GERCEK: 2026-08-17 supervisor akisinda bosluk toleransi 0/1/2/3/5/8/12
kare icin 5 s'ye ulasan kosu orani sirasiyla %0.02/%0.03/%0.03/%0.10/%0.14/
%0.53/%1.03. Yani 5 s kesintisiz kilit MEVCUT tespit surekliligiyle nadiren
mumkun. Kapi ACILIRSA devir sayisi cok duser — bu bir kod hatasi degil, algi
surekliligi limitidir. Varsayilan KAPALI olmasinin sebebi budur.

ORTAM DEGISKENLERI
--------------------------------------------------------------------------
  AVCI_KILIT_S        0.0   kapi esigi (s). 0 = KAPALI (varsayilan davranis)
  AVCI_KILIT_CONF     0.35  kilide sayilacak minimum guven
  AVCI_KILIT_BOSLUK   3     tolere edilen ust uste bosluk KARE sayisi
  AVCI_KILIT_BOSLUK_S 0.35  tolere edilen ust uste bosluk SURESI (s)
  AVCI_KILIT_KADRAJ   0.02  kadraj kenar payi (oran); merkez bu bandin icinde
  AVCI_KILIT_KADRAJ_MOD yasa  "yasa" = 640x480 (OLU KOD, hic ateslemez)
                              "dow"  = gercek DoW sinirlari (bkz. KADRAJ_MOD)
  AVCI_KILIT_SART_S   5.0   DENETIM referansi (ihlal bayragi bununla hesaplanir)
  AVCI_KILIT_DENETIM  1     denetim CSV'si (1 = HER ZAMAN acik, kapi kapali olsa da)

⚠ CONF ESIGI UYUSMAZLIGI (2026-08-17, OLCULDU)
--------------------------------------------------------------------------
CONF_MIN varsayilani 0.35 SABIT, ama boru hattinin kendi esigi
Cfg.VIS_CONF_MIN'dir (server.py:1621 det_beyin kapisi) ve kampanya onu
AVCI_VIS_CONF=0.25 ile kuruyor. Arada kalan kutular yasaya GIRER ama kilide
SAYILMAZ. Olculdu (30733 kare, ayna sonrasi): 1713 kare (%5.6) bu araliktaydi
ve KILIT KIRILMALARININ %17.4'unu tek basina bu uyusmazlik yapti. Hizalayinca
>=5 s epizod 43 -> 57 (%+32.6), kilit zamaninin >=5 s icindeki payi
%31.5 -> %38.9. Hizalamak icin: AVCI_KILIT_CONF = AVCI_VIS_CONF.
supervisor.run_hybrid basta bu uyusmazligi UYARI olarak basar.
================================================================================
"""
import os
import statistics
import threading
import time


def _f(ad, vars):
    try:
        return float(os.environ.get(ad, vars))
    except (TypeError, ValueError):
        return float(vars)


def _i(ad, vars):
    try:
        return int(float(os.environ.get(ad, vars)))
    except (TypeError, ValueError):
        return int(vars)


class KilitKapiCfg:
    """Kapi ayarlari. ESIK_S = 0 -> kapi KAPALI, davranis bit-ayni."""
    # Kapi esigi. 0.0 = KAPALI (varsayilan). 5.0 verilince gercek 5 s sart olur.
    # ══ VARSAYILAN ACIK 2026-08-17 -- UCUSTA OLCULDU, ANGAJMAN COKMEDI ══
    # Kullanicinin 1 NUMARALI sarti: 5 s KESINTISIZ kilit, sonra vurus.
    #   K0 taban (kapi KAPALI): GPS_VISUAL %15 >=5s, TERMINAL %33, min 0.52 s
    #   K5 kapi ACIK 5 s      : GPS_VISUAL %100,     TERMINAL %100, min 5.00 s
    #                           29 faz gecisi + 21 vurus taahhudu, SIFIR IHLAL
    #   Bedeli YOK: vurus 2 -> 2, en yakin gecis 0.81 -> 0.46 m (gunun en iyisi)
    #   K5 + doluluk 0.80     : GPS_VISUAL %100, VURUS 7 (gunun rekoru)
    # ⚠ ESKI CEVRIMDISI TAHMIN ("kapi acilinca devir 1413 -> 1 coker") YANLIS
    #   cikti: off-policy idi (eski kayitlari oynatiyordu), oysa kapi
    #   YORUNGEYI degistirir. Ucus tahmini curuttu.
    # Kapatmak: AVCI_KILIT_S=0. Yedek: yedek/KILIT_ONCESI_20260817_221853
    # ⛔ KULLANICI TALIMATI 2026-08-18: "kiliti komple bos ver, sisteme dahil
    #    etme, calistirma; bir yere kaydet." Kapi KAPATILDI.
    #    Olculen sonuc KAYBOLMASIN diye `arac/KILIT_BULGUSU.md`'ye yazildi:
    #      kapi ACIK 5 s -> GPS_VISUAL %100 / TERMINAL %100 >=5 s, min 5.00 s,
    #      50 gecis SIFIR ihlal, vurus 2->2, en yakin 0.81 -> 0.46 m
    #      kapi + doluluk 0.80 -> vurus 7 (o gunun rekoru)
    #    Yeniden acmak icin: AVCI_KILIT_S=5 AVCI_KILIT_DOLULUK=0.80
    ESIK_S = _f("AVCI_KILIT_S", 0.0)
    # Dedektorun kendi esigi 0.35; supervisor'in POSE_CONF_MIN'i 0.0 (kapali).
    # Kilit "gecerli tespit" istedigi icin burada GERCEK bir esik uygulanir.
    # 0.35 -> 0.25 (2026-08-17): boru hatti AVCI_VIS_CONF=0.25 gecirirken
    # kilit 0.35 istiyordu; arada kalan kutular yasaya GIRIYOR ama kilide
    # SAYILMIYORDU -- kilit kirilmalarinin %17.4'u tek basina bu uyusmazliktan.
    CONF_MIN = _f("AVCI_KILIT_CONF", 0.35)
    # Bosluk toleransi: ust uste en fazla bu kadar KARE ve bu kadar SANIYE.
    BOSLUK_KARE = _i("AVCI_KILIT_BOSLUK", 3)
    BOSLUK_S = _f("AVCI_KILIT_BOSLUK_S", 0.35)

    # ── ⚠ BOSLUK TOLERANSI KARE ILE OLCULURSE KILIT TANIMI KARE HIZINA
    #    BAGLI OLUR (2026-08-17, tezgahta olculdu) ────────────────────────
    # BOSLUK_KARE=3, olculen kare periyoduna gore SU KADAR sure eder:
    #     0.04 s/kare (25.0 fps) -> 0.12 s      (karar_20260817_123827)
    #     0.05 s/kare (20.0 fps) -> 0.15 s      (cogu kosu)
    #     0.07 s/kare (14.3 fps) -> 0.21 s      (karar_20260817_131933)
    # Yani AYNI kilit tanimi, dedektor yavaslayinca KENDILIGINDEN gevsiyor.
    # Oysa kilidin fiziksel anlami ZAMANDIR: "hedefin son gorulen yerinden
    # ne kadar sure sonra hala ayni hedef oldugunu soyleyebiliriz". O sinir
    # BOSLUK_S'tir ve truth ile olculmustur (bkz. asagidaki tablo).
    #   "kare"  : ikisi de uygulanir (BUGUNKU davranis, BIT-AYNI) -- varsayilan
    #   "sure"  : YALNIZ BOSLUK_S uygulanir; tanim kare hizindan BAGIMSIZ olur
    # ⚠ VARSAYILAN "sure" YAPILDI 2026-08-17: fizik ZAMANDA. 0.35 s siniri
    #   truth ile dogrulandi (o esige kadar yeniden yakalanan kutu %94.3 AYNI
    #   hedef; otesinde ~90 px sicriyor ve beste biri BASKA nesne).
    BOSLUK_MOD = (os.environ.get("AVCI_KILIT_BOSLUK_MOD", "kare")
                  or "kare").strip().lower()

    # ── DOLULUK (izleme kalitesi) ────────────────────────────────────────
    # ⚠ 2026-08-17'de tezgahta bulunan TANIM ACIGI: bugunku kilit, tek bir
    # bosluğun UZUNLUGUNU sinirliyor ama bosluk SAYISINI sinirlamiyor. Yani
    # "2 kare gor, 0.3 s kor kal" dizisi sonsuza kadar tekrarlanabilir ve
    # 5 saniyelik "KESINTISIZ" kilit uretir. Olculen (12 adet >=5 s epizod):
    #     doluluk medyan %62.1, EN KOTU %51.1, kilit icindeki KOR sure 2.27 s
    # Yani bugunku tanimla "5 s kesintisiz kilit" pratikte "5 s icinde 2.3 s
    # kor" demek. DOLULUK bunu OLCER ve istege bagli olarak SINIRLAR.
    #   0.0 = yalniz OLC, sinirlama YOK (varsayilan, davranis BIT-AYNI)
    # ══ VARSAYILAN 0.80 YAPILDI 2026-08-17 ══════════════════════════════
    # Sure sarti TEK BASINA yetmiyor (yukaridaki tanim acigi). Ucusta 0.80
    # tabani ile: GPS_VISUAL %100 >=5s VE vurus 7 (gunun rekoru) -- yani
    # daha SIKI tanim performansi DUSURMEDI. Gevsetmek: AVCI_KILIT_DOLULUK=0
    DOLULUK_MIN = _f("AVCI_KILIT_DOLULUK", 0.0)
    # Kadraj kenar payi (oran). Merkez [PAY, 1-PAY] bandinda olmali.
    KADRAJ_PAY = _f("AVCI_KILIT_KADRAJ", 0.02)
    # Yasa cercevesi (tespit_akisi._yasa_icsellik: CX=320, CY=240 -> 640x480).
    W = _f("AVCI_KILIT_W", 640.0)
    H = _f("AVCI_KILIT_H", 480.0)

    # ── ⛔ KADRAJ KAPISI OLU KOD IDI (2026-08-17, OLCULDU) ─────────────────
    # Kullanici kilit tanimi "hedef kadrajda" diyor ama bu kapi 20976 gorsel
    # faz karesinde HIC atesLENMEDI. Sebep GEOMETRIK, ayar degil:
    #   Yasa cercevesi 640x480 / HFOV 125 (vision/geometry.py) varsayilir,
    #   ama gercek goruntu DoW'un 1920x1080 / HFOV 122.07 karesidir ve
    #   tespit_akisi.dow_pikseli_yasaya ACI koruyarak cevirir. DoW kenari
    #   yasa cercevesinde  u[19.3, 620.7]  v[70.7, 409.3]  noktalarina duser.
    #   PAY=0.02 kapisi ise [12.8, 627.2] x [9.6, 470.4] istiyor -- ERISILEBILIR
    #   BOLGEYI TAMAMEN KAPSIYOR. Yani gercek bir tespit bu kapinin disina
    #   MATEMATIKSEL OLARAK cikamaz; sart uygulanmiyor.
    #
    # "dow" MODU gercek DoW sinirlarini kullanir; PAY o sinira uygulanir.
    #   dikeyde 70.7..409.3 (339 px) -> %2 pay = 6.8 px
    # ⚠ Bu kapiyi acmak kilidi SIKILASTIRIR (epizod SAYISI artar, sure kisalir).
    #   Tanimi durustlestirmek icindir, sureklilik icin DEGIL. Varsayilan
    #   "yasa" = bugunku (fiilen kapali) davranis, BIT-AYNI.
    KADRAJ_MOD = (os.environ.get("AVCI_KILIT_KADRAJ_MOD", "yasa") or "yasa").strip().lower()
    # DoW karesinin yasa cercevesindeki gercek siniri (geometri, ayar DEGIL):
    #   FX_yasa = 166.582 (640/2 / tan(125/2)),  fx_dow = 531.360 (960 / tan(122.0709/2))
    DOW_U0, DOW_U1 = 320.0 - 166.582 * (960.0 / 531.360), 320.0 + 166.582 * (960.0 / 531.360)
    DOW_V0, DOW_V1 = 240.0 - 166.582 * (540.0 / 531.360), 240.0 + 166.582 * (540.0 / 531.360)
    # DENETIM referansi: kapi kapali olsa da ihlal bu esige gore isaretlenir.
    SART_S = _f("AVCI_KILIT_SART_S", 5.0)

    @classmethod
    def acik(cls):
        return float(cls.ESIK_S) > 0.0


class KesintisizKilit:
    """KESINTISIZ kilit sayaci.

    `KilitSayaci` (guidance/kilit_sayaci.py) ile KARISTIRMA: o sartname kaniti
    icin 10 s pencerede KUMULATIF sayar. Bu sinif KESINTISIZ sayar ve kilit
    kirilinca SIFIRDAN baslar.

        kk = KesintisizKilit()
        kk.guncelle(tespit, t, hayalet=False)   # her dedektor karesinde
        kk.sure        -> float, o anki KESINTISIZ kilit suresi (s)
        kk.gecti()     -> bool, kapi acik mi / esik dolduysa True
        kk.ozet()      -> denetim kaydi icin sozluk
    """

    def __init__(self, cfg=KilitKapiCfg, t0=None, kare0=0):
        self.cfg = cfg
        self._t0 = t0                # kesintisiz kilidin BASLADIGI monoton an
        self._son_ok_t = t0          # son GECERLI karenin ani
        self._simdi = t0
        self.kare = int(kare0)       # bu kosuda sayilan GERCEK tespit karesi
        self.bosluk_kare = 0         # su an ust uste tolere edilen bosluk
        self.bosluk_top = 0          # bu kosuda TOPLAM tolere edilen bosluk
        self.hayalet_kare = 0        # bu kosuda tolere edilen HAYALET kare
        self.hayalet_top = 0         # faz boyunca reddedilen toplam hayalet
        self.kirilma = 0             # bu faz boyunca kilit kac kez kirildi
        self._conf = []              # bu kosudaki conf degerleri (medyan icin)
        self.son_sebep = "baslamadi"
        # ── DOLULUK olcumu ───────────────────────────────────────────────
        self._kor_s = 0.0            # bu kilit icinde TOPLAM kor sure (s)
        self._dt = []                # son kare araliklari (periyot kestirimi)
        self._onceki_t = None        # bir onceki KARE ani (gecerli olmasa da)

    # ------------------------------------------------------------------ okuma
    @property
    def sure(self):
        """O anki KESINTISIZ kilit suresi (s). Kilit yoksa 0.0."""
        if self._t0 is None or self._son_ok_t is None:
            return 0.0
        return max(0.0, float(self._son_ok_t) - float(self._t0))

    @property
    def kare_periyodu(self):
        """Dedektorun olculen kare periyodu (s). Sabit VARSAYILMAZ: olculen
        deger loga gore 0.04-0.07 s arasinda degisiyor."""
        if not self._dt:
            return 0.05
        return statistics.median(self._dt)

    @property
    def kor_s(self):
        """Bu kilit icinde tolere edilmis TOPLAM kor sure (s)."""
        return round(self._kor_s, 3)

    @property
    def doluluk(self):
        """Kilidin GERCEKTEN gozlemlenen orani: (sure - kor) / sure.
        Kilit yoksa 1.0. 1.0 = hicbir kare kacirilmadi."""
        s = self.sure
        if s <= 0.0:
            return 1.0
        return max(0.0, min(1.0, (s - self._kor_s) / s))

    def gecti(self):
        """Kapi acik mi? Kapi KAPALIYSA (ESIK_S<=0) her zaman True — yani
        varsayilan kurulumda davranis DEGISMEZ."""
        if not self.cfg.acik():
            return True
        if self.sure < float(self.cfg.ESIK_S):
            return False
        # DOLULUK tabani (varsayilan 0 = kapali -> davranis BIT-AYNI).
        d_min = float(getattr(self.cfg, "DOLULUK_MIN", 0.0) or 0.0)
        if d_min > 0.0 and self.doluluk < d_min:
            return False
        return True

    def conf_medyan(self):
        return statistics.median(self._conf) if self._conf else None

    # ------------------------------------------------------------------ yazma
    def _kare_gecerli(self, tespit):
        """Kare kilide sayilir mi? (sebep ile birlikte)"""
        if tespit is None:
            return False, "tespit yok"
        try:
            conf = float(tespit.get("conf", 0.0) or 0.0)
            w = float(tespit.get("w", 0.0) or 0.0)
            h = float(tespit.get("h", 0.0) or 0.0)
            cx = float(tespit.get("cx", 0.0) or 0.0)
            cy = float(tespit.get("cy", 0.0) or 0.0)
        except (TypeError, ValueError):
            return False, "bozuk tespit"
        if w <= 0.0 or h <= 0.0:
            return False, "kutu bos"
        if conf < float(self.cfg.CONF_MIN):
            return False, "conf %.2f < %.2f" % (conf, self.cfg.CONF_MIN)
        p = float(self.cfg.KADRAJ_PAY)
        if getattr(self.cfg, "KADRAJ_MOD", "yasa") == "dow":
            # GERCEK DoW kadraj siniri (bkz. KADRAJ_MOD aciklamasi). Pay,
            # yasa cercevesinin degil ERISILEBILIR bolgenin kenarina uygulanir.
            u0, u1 = float(self.cfg.DOW_U0), float(self.cfg.DOW_U1)
            v0, v1 = float(self.cfg.DOW_V0), float(self.cfg.DOW_V1)
            mu, mv = p * (u1 - u0), p * (v1 - v0)
            if not (u0 + mu <= cx <= u1 - mu and v0 + mv <= cy <= v1 - mv):
                return False, "hedef kadraj disinda (dow)"
            return True, "gecerli"
        W, H = float(self.cfg.W), float(self.cfg.H)
        if W > 1 and H > 1:
            if not (p * W <= cx <= (1.0 - p) * W and p * H <= cy <= (1.0 - p) * H):
                return False, "hedef kadraj disinda"
        return True, "gecerli"

    def guncelle(self, tespit, t, hayalet=False):
        """Bir dedektor karesi isle; guncel KESINTISIZ kilit suresini dondur.

        tespit : {"cx","cy","w","h","conf"} | None  (YASA cercevesi pikseli)
        t      : monoton zaman (s)
        hayalet: kare hayalet/kor-kopru uretimi mi. True ise GERCEK tespit
                 sayilmaz (kullanici sarti: "gercek tespit, hayalet DEGIL").
        """
        t = float(t)
        self._simdi = t
        # Kare periyodu kestirimi (DOLULUK icin) — gecerli/gecersiz FARK ETMEZ,
        # olculen sey dedektorun CADENCE'idir.
        if self._onceki_t is not None:
            _d = t - self._onceki_t
            if 0.0 < _d < 1.0:
                self._dt.append(_d)
                if len(self._dt) > 200:
                    del self._dt[0]
        self._onceki_t = t
        if hayalet:
            self.hayalet_top += 1
            gecerli, sebep = False, "hayalet kare"
        else:
            gecerli, sebep = self._kare_gecerli(tespit)
        self.son_sebep = sebep

        if gecerli:
            if self._t0 is None:
                self._t0 = t
                self.kare = 0
                self.bosluk_top = 0
                self.hayalet_kare = 0
                self._conf = []
                self._kor_s = 0.0
            elif self._son_ok_t is not None:
                # KOR SURE: iki gecerli kare arasindaki, bir kare
                # periyodunu ASAN kisim. (Normal kare adimi korluk DEGILDIR.)
                _bos = (t - float(self._son_ok_t)) - self.kare_periyodu
                if _bos > 0.5 * self.kare_periyodu:
                    self._kor_s += _bos
            self.kare += 1
            self.bosluk_kare = 0
            self._son_ok_t = t
            try:
                self._conf.append(float(tespit.get("conf", 0.0) or 0.0))
            except (TypeError, ValueError):
                pass
            return self.sure

        # --- gecersiz kare: bosluk toleransi ---
        if self._t0 is None:
            return 0.0                       # zaten kilit yok
        self.bosluk_kare += 1
        self.bosluk_top += 1
        if hayalet:
            self.hayalet_kare += 1
        bos_s = t - float(self._son_ok_t if self._son_ok_t is not None else t)
        # "sure" modunda KARE sayisi olcut DEGILDIR -> tanim kare hizindan
        # bagimsiz olur. "kare" (varsayilan) modunda ikisi de uygulanir.
        _kare_asti = (getattr(self.cfg, "BOSLUK_MOD", "kare") != "sure"
                      and self.bosluk_kare > int(self.cfg.BOSLUK_KARE))
        if _kare_asti or bos_s > float(self.cfg.BOSLUK_S):
            self.kir()
        return self.sure

    def kir(self):
        """Kilidi KIR: sure sifirdan baslar."""
        if self._t0 is not None:
            self.kirilma += 1
        self._t0 = None
        self._son_ok_t = None
        self.kare = 0
        self.bosluk_kare = 0
        self.bosluk_top = 0
        self.hayalet_kare = 0
        self._conf = []
        self._kor_s = 0.0

    # ------------------------------------------------------- denetim ozeti
    def ozet(self):
        """Denetim kaydi icin sozluk (bagimsiz dogrulanabilir alanlar)."""
        sure = self.sure
        simdi_w = time.time()
        simdi_m = self._simdi if self._simdi is not None else time.monotonic()
        # monoton -> duvar saati cevirisi (fark BAGIMSIZ dogrulanabilsin)
        gecis_w = simdi_w
        kilit_t0_w = (simdi_w - (float(simdi_m) - float(self._t0))
                      if self._t0 is not None else None)
        return {
            "kesintisiz_kilit_s": round(sure, 3),
            "kilit_t0_wall": (round(kilit_t0_w, 3)
                              if kilit_t0_w is not None else ""),
            "gecis_wall": round(gecis_w, 3),
            "fark_s": (round(gecis_w - kilit_t0_w, 3)
                       if kilit_t0_w is not None else ""),
            "kare_gercek": self.kare,
            "kare_bosluk": self.bosluk_top,
            "hayalet_kare": self.hayalet_kare,
            "hayalet_top": self.hayalet_top,
            "kirilma": self.kirilma,
            "conf_medyan": (round(self.conf_medyan(), 3)
                            if self.conf_medyan() is not None else ""),
            # ⚠ DOLULUK: "5 s kesintisiz kilit"in yuzde kaci GERCEKTEN
            # gozlemlendi. Bu olmadan kilit suresi TEK BASINA yaniltir.
            "doluluk": round(self.doluluk, 3),
            "kor_s": round(self._kor_s, 3),
            "kare_periyot_s": round(self.kare_periyodu, 4),
        }

    def devret_t0(self):
        """Devirde tasinacak kilit baslangici (monoton) — faz gecerken kilit
        SIFIRLANMASIN diye. Kilit yoksa None."""
        return self._t0


# ══════════════════════════════════════════════════════════════════════════
#  DENETIM KAYDI — "5 saniye sarti gercekten saglandi mi" TEK DOSYADAN
# ══════════════════════════════════════════════════════════════════════════
# HER faz gecisinde bir satir. Kapi KAPALI olsa da yazilir: amac mevcut
# davranisin ne kadar ihlal urettigini OLCMEK.
_LOG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "logs")

BASLIKLAR = [
    "t_mono", "t_wall_iso", "olay",
    "kesintisiz_kilit_s", "kilit_t0_wall", "gecis_wall", "fark_s",
    "kare_gercek", "kare_bosluk", "hayalet_kare", "hayalet_top", "kirilma",
    "conf_medyan", "doluluk", "kor_s", "kare_periyot_s",
    "kapi", "kapi_esik_s", "kapi_acik",
    "sart_s", "ihlal", "menzil_m", "boyut_px", "not",
]


class DenetimLog:
    """kilit_denetim_*.csv — gorev basina bir dosya, thread-guvenli."""

    def __init__(self):
        self._f = None
        self._kilit = threading.Lock()
        self._t0 = time.monotonic()
        self.yol = None
        self.satir = 0

    def acik_mi(self):
        return os.environ.get("AVCI_KILIT_DENETIM", "1") != "0"

    def ac(self, yeni=True):
        """Yeni gorev -> yeni dosya. yeni=False ise zaten aciksa dokunmaz."""
        if not self.acik_mi():
            return
        with self._kilit:
            if self._f is not None and not yeni:
                return
            self._kapat_ic()
            try:
                os.makedirs(_LOG_DIR, exist_ok=True)
                # Dosya adi 1 s cozunurluklu: ayni saniyede iki gorev baslarsa
                # eskisinin USTUNE yazilirdi -> denetim satiri sessizce kaybolur.
                ad = time.strftime("kilit_denetim_%Y%m%d_%H%M%S.csv")
                _k = 1
                while os.path.exists(os.path.join(_LOG_DIR, ad)):
                    ad = time.strftime("kilit_denetim_%Y%m%d_%H%M%S_") + "%d.csv" % _k
                    _k += 1
                self.yol = os.path.join(_LOG_DIR, ad)
                self._f = open(self.yol, "w", encoding="utf-8", buffering=1)
                self._f.write(",".join(BASLIKLAR) + "\n")
                self._t0 = time.monotonic()
                self.satir = 0
                print("[KILIT-DENETIM] kayit: %s  (kapi %s, esik %.1f s)"
                      % (ad, "ACIK" if KilitKapiCfg.acik() else "KAPALI",
                         KilitKapiCfg.ESIK_S))
            except Exception as e:
                print("[KILIT-DENETIM] kayit acilamadi: %r" % (e,))
                self._f = None

    def yaz(self, olay, kk, kapi, ek=None):
        """Bir faz gecisini kaydet.

        olay : "GPS_VISUAL" | "TERMINAL" | serbest metin
        kk   : KesintisizKilit  (ozet() cagrilir)
        kapi : gecise IZIN VEREN kapinin adi (orn. "ardisik_kare>=10")
        ek   : {"menzil_m":..,"boyut_px":..,"not":..} opsiyonel
        """
        if not self.acik_mi():
            return
        if self._f is None:
            self.ac(yeni=False)
        if self._f is None:
            return
        ek = ek or {}
        try:
            o = kk.ozet() if kk is not None else {}
            sure = float(o.get("kesintisiz_kilit_s") or 0.0)
            sart = float(KilitKapiCfg.SART_S)
            sat = {
                "t_mono": "%.3f" % (time.monotonic() - self._t0),
                "t_wall_iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "olay": olay,
                "kesintisiz_kilit_s": "%.3f" % sure,
                "kilit_t0_wall": _s(o.get("kilit_t0_wall")),
                "gecis_wall": _s(o.get("gecis_wall")),
                "fark_s": _s(o.get("fark_s")),
                "kare_gercek": o.get("kare_gercek", ""),
                "kare_bosluk": o.get("kare_bosluk", ""),
                "hayalet_kare": o.get("hayalet_kare", ""),
                "hayalet_top": o.get("hayalet_top", ""),
                "kirilma": o.get("kirilma", ""),
                "conf_medyan": o.get("conf_medyan", ""),
                "doluluk": o.get("doluluk", ""),
                "kor_s": o.get("kor_s", ""),
                "kare_periyot_s": o.get("kare_periyot_s", ""),
                "kapi": kapi,
                "kapi_esik_s": "%.2f" % float(KilitKapiCfg.ESIK_S),
                "kapi_acik": 1 if KilitKapiCfg.acik() else 0,
                "sart_s": "%.2f" % sart,
                "ihlal": 0 if sure >= sart else 1,
                "menzil_m": _s(ek.get("menzil_m")),
                "boyut_px": _s(ek.get("boyut_px")),
                "not": str(ek.get("not", "")).replace(",", ";"),
            }
            with self._kilit:
                if self._f is None:
                    return
                self._f.write(",".join(str(sat.get(k, "")) for k in BASLIKLAR) + "\n")
                self.satir += 1
        except Exception:
            pass          # denetim kaydi ASLA guduumu dusurmez

    def _kapat_ic(self):
        try:
            if self._f:
                self._f.close()
        except Exception:
            pass
        self._f = None

    def kapat(self):
        with self._kilit:
            self._kapat_ic()


def _s(v, n=3):
    try:
        return "" if v is None or v == "" else ("%.*f" % (n, float(v)))
    except (TypeError, ValueError):
        return ""


# Modul-duzeyi tekil: supervisor ve bbox_ibvs AYNI dosyaya yazar.
denetim = DenetimLog()

# -*- coding: utf-8 -*-
"""
================================================================================
KILIT KURALI — sartname §6.1.4 kilit sayaci (SAF mantik, unit-test edilebilir)
================================================================================
YARISMA PIPELINE FAZ 3. "Kilitlenme" tanimini kodda somutlastirir: hedefi
Angajman Volumu (AV) icinde, yeterli ekran kaplamasiyla, ONAYLI (CONFIRMED)
track olarak ve OLCULEN tespitle (coast degil) tutma suresi. Sim/guduum
BAGIMSIZ: sentetik girdiyle test edilir; ana_kontrol FSM bunu besler/sorgular.

SAYAC KOSULU (HEPSI saglanmali; biri bile bozulunca o frame SAYILMAZ):
  - conf >= uretim esigi (muhafazakar; yanlis kilit paketi -30 puan)
  - track CONFIRMED
  - tespit_mi = True  (coast'ta bbox TAHMINIDIR; ekran kaplama guvenilmez ->
    sartnamenin kilit tanimina DURUST yaklasim: coast kilit sayilmaz)
  - bbox merkez AV icinde: yatay %25-75, dikey %10-90 (goruntuye oranli)
  - ekran kaplama orani >= esik (0.06 baslangic; sartname %5 + pay)

CIKTILAR:
  - kumulatif_kilit_sn: 10 sn KAYAN pencerede sayan-frame sureleri toplami
  - kilit_tamam: kumulatif >= 5 sn ilk kez asildiginda True (KENAR tetikli,
    bir kez; +400 kilit paketini garanti altina alir)
  - surekli_kilit_sn: KESINTISIZ sayan-frame suresi (ilk bozulmada sifirlanir;
    angajman on sarti: >=3 sn ayri kosul)
================================================================================
"""
from collections import deque


class KilitCfg:
    # KILIT CONF ESIGI (handoff'tan AYRI, DAHA SIKI). Handoff (GORSEL_TAKIP'e gecis)
    # UCUZ-GERI-DONUSLU: yanlis gecis olursa VIS_LOST_TO_GPS ile YAKLASMA'ya (GPS)
    # geri donulur -> dusuk esik (VIS_CONF_MIN=0.45) tolere edilir. Kilit PAKETI ise
    # -30 puan riskli (yanlis kilit); geri donusu yok. Bu yuzden kilit sayaci ve
    # ANGAJMAN on sarti AYRI, DAHA YUKSEK esik ister. NOT: 0.72 gerekli ama YETERSIZ
    # (model FP'ye 0.90 verebiliyor; kalici savunma dataset negatif/background).
    KILIT_CONF_MIN = 0.72       # kilit sayaci + angajman icin asgari guven (handoff DEGIL)
    AV_YATAY = (0.25, 0.75)     # merkez cx/W bu bantta (Hedef Vurus Alani yatay)
    AV_DIKEY = (0.10, 0.90)     # merkez cy/H bu bantta
    KAPLAMA_ESIK = 0.06         # EKSEN-bazli: max(w/W, h/H) >= bu (sartname %5 + pay).
                                # ALAN orani DEGIL -> hedef ekranin YATAY veya DIKEY
                                # ekseninin en az %5'ini kaplamali (sartname §6.1.4).
    PENCERE_SN = 10.0           # kayan pencere
    KUMULATIF_HEDEF_SN = 5.0    # kilit_tamam esigi
    SUREKLI_ANGAJMAN_SN = 3.0   # angajman on sarti (kesintisiz)
    # KARE KACAGI TOLERANSI (sartname §6.1.4 + Sim Teslim Esaslari): 5 sn kilitlenme
    # icin %5 = 200 ms. KUMULATIF sayac toleransa GUVENMEZ -> yalnizca gecerli
    # (sayan) karelerle 5.0 sn'yi doldurur (kacak kareler EKLENMEZ; tolerans
    # kumulatif'i ETKILEMEZ). KESINTISIZ-3sn sayacinda: <=200 ms kaclar KOPRULENIR
    # (surekli donar, sifirlanmaz) AMA kilit araliginin ILK karesinde (surekli=0
    # iken) ve SON karesinde (kopru acikken angajman verilmez) KOPRULEME YOK
    # ("baslangic/bitiste gecersiz").
    KACAK_TOLERANS_SN = 0.2
    # KILIT DORTGENI (tespit kurali — her asamada gecerli): video/kilit paketine
    # giden dortgen (= bbox) kurallari. Cizgi kalinligi <=3 px (video kaydedici
    # sabiti). "Dortgen hedefin >=%90'ini icermeli" + "merkez farki yatayda w/2,
    # dikeyde h/2'yi asamaz" REFERANS hedef sinirini gerektirir -> UCUS pipeline'inda
    # YAPILAMAZ (SERT AYRIM: pipeline referans kanalina erisemez). Pipeline PROXY:
    # dortgen KADRAJ icinde (>=%90'i ekranda), makul boyut. Referans-tam dogrulama
    # arac/kilit_dortgeni.py'de (gelistirme araci).
    CIZGI_PX = 3                # video kilit dortgeni cizgi kalinligi (max)
    DORTGEN_KADRAJ_MIN = 0.90  # bbox'in en az bu orani KADRAJ ICINDE olmali
    # GEOMETRIK DIKEY KAPISI (ucuz FP kalkani, YALNIZ kilit zinciri — handoff'a girmez):
    # hedefin ham-GPS irtifasi+drone irtifasi+tilt'ten kestirilen dikey ekran konumu
    # (kamera_model.dikey_ekran_tahmini) ile bbox merkezi bu banttan COK uzaksa
    # tespit geometrik imkansiz -> kilit SAYMAZ (track surer). Band GENIS: ham GPS
    # bozuk + pitch attitude-bagimsiz varsayildi (gross imkansizlari eler, orn.
    # "228 m asagidaki hedef ekran merkezinde"). geometrik_uygun None ise (poz/ham
    # yok, test) KAPI PASIF (geriye-uyumlu).
    GEOMETRIK_DIKEY_BAND = 0.45  # GIRIS (siki): normalize |cy - v_pred| bu ustundeyse imkansiz
    GEOMETRIK_DIKEY_CIKIS = 0.60  # CIKIS (gevsek): histerezis; uygunken bu asilinca duser


class KilitDurumu:
    """Her algi frame'inde adim() cagrilir; kilit sayaclarini gunceller.
    Kilit conf esigi KENDI sabitidir (KilitCfg.KILIT_CONF_MIN=0.72); handoff
    esiginden (Cfg.VIS_CONF_MIN=0.45) AYRI ve daha sikidir (bkz. KilitCfg)."""

    def __init__(self, cfg=None):
        self.cfg = cfg or KilitCfg()
        self._pencere = deque()      # (t, dt) sayan-frame'ler (10 sn kayan)
        self._kumulatif = 0.0        # pencere ici toplam sayan-sure
        self.surekli_kilit_sn = 0.0
        self.kilit_tamam = False     # kenar-tetikli (bir kez)
        self._son_t = None
        self._son_sayan = False
        self._kacak_ardisik = 0.0    # ardisik kacak (saymayan) suresi (kopru toleransi)
        self._kopru_acik = False     # kesintisiz sayacta aktif kopru (kaçak koprulendi,
                                     # henuz sayan kare gelmedi) -> bitiste angajman YOK
        self._engel_sayac = {}       # kilit tamamlanamazsa: hangi kosul kac kez engel

    def sifirla(self):
        self._pencere.clear()
        self._kumulatif = 0.0
        self.surekli_kilit_sn = 0.0
        self.kilit_tamam = False
        self._son_t = None
        self._son_sayan = False
        self._kacak_ardisik = 0.0
        self._kopru_acik = False
        self._engel_sayac = {}

    def engel_ozeti(self):
        """Kilit tamamlanamadiysa: en cok hangi kosul engel oldu (teshis)."""
        if not self._engel_sayac:
            return None
        return dict(sorted(self._engel_sayac.items(), key=lambda kv: -kv[1]))

    @staticmethod
    def dortgen_kadraj_orani(hedef, W, H):
        """Kilit dortgeninin (bbox) KADRAJ ICINDE kalan alan orani [0..1].
        Referans-bagimsiz PROXY: dortgen ekrandan tasarsa hedefi guvenilir
        gosteremez (tam '%90 icerme' referansla arac/'ta). 1.0 = tamamen ekranda."""
        if not hedef or W <= 1 or H <= 1:
            return 0.0
        w, h = float(hedef["w"]), float(hedef["h"])
        if w <= 0 or h <= 0:
            return 0.0
        x1, y1 = hedef["cx"] - w / 2.0, hedef["cy"] - h / 2.0
        x2, y2 = hedef["cx"] + w / 2.0, hedef["cy"] + h / 2.0
        gx = max(0.0, min(x2, W) - max(x1, 0.0))     # gorunur genislik
        gy = max(0.0, min(y2, H) - max(y1, 0.0))     # gorunur yukseklik
        return (gx * gy) / (w * h)

    @staticmethod
    def kaplama_eksen(hedef, W, H):
        """EKSEN-bazli kaplama (sartname): hedefin ekranin yatay VE dikey eksenini
        ne kadar kapladigi -> (yatay=w/W, dikey=h/H). Sartname 'en az BIRINDE >=%5'
        ister -> max(yatay, dikey) kullanilir (alan orani DEGIL)."""
        if not hedef or W <= 1 or H <= 1:
            return 0.0, 0.0
        return float(hedef["w"]) / W, float(hedef["h"]) / H

    def _sayar_mi(self, hedef, W, H):
        """Bu frame kilit sayacinda sayilir mi? (sayan, engel). engel: sayilmadiysa
        HANGI kosulun engel oldugu (kilit tamamlanamazsa teshis).
        SIRA (sartname): conf/track/olcum -> KAPLAMA (eksen; AV'ye girmenin on
        sarti) -> MERKEZ (AV bandi). Kaplama merkezden ONCE: eksen kaplamasi
        %5 altindaysa hedef AV'ye GIRMEMIS sayilir.
        CONF esigi = KilitCfg.KILIT_CONF_MIN (handoff'tan AYRI, sikidir): 0.45-0.72
        arasi tespit sayaci ILERLETMEZ (dusuk_conf) ama track/handoff'u besler."""
        if hedef is None or W is None or H is None or W <= 1 or H <= 1:
            return False, "hedef_yok"
        if not hedef.get("tespit_mi"):
            return False, "coast"                # olcum yok (bbox tahmini)
        if hedef.get("track_durumu") != "CONFIRMED":
            return False, "track_onaysiz"        # TENTATIVE/LOST
        if float(hedef.get("conf", 0.0)) < self.cfg.KILIT_CONF_MIN:
            return False, "dusuk_conf"           # handoff'u gecmis olabilir ama kilit SIKI
        # GEOMETRIK DIKEY KAPISI: ham-GPS geometrisiyle tutarsiz (gross imkansiz) tespit
        # kilit saymaz. geometrik_uygun ana_kontrol'de hesaplanip hedef'e yazilir; None
        # ise (test/poz yok) PASIF. handoff'a GIRMEZ (yalniz burada, kilit zinciri).
        if hedef.get("geometrik_uygun") is False:
            return False, "geometrik_imkansiz"
        c = self.cfg
        # KILIT DORTGENI: kadraj-ici proxy (dortgen ekrandan >%10 tasarsa gecersiz)
        if self.dortgen_kadraj_orani(hedef, W, H) < c.DORTGEN_KADRAJ_MIN:
            return False, "dortgen_tasma"        # bbox kadraj disina cok tasti
        # KAPLAMA (eksen-bazli) merkezden ONCE: en az bir eksende >=%5
        kap_y, kap_d = self.kaplama_eksen(hedef, W, H)
        if max(kap_y, kap_d) < c.KAPLAMA_ESIK:
            return False, "kaplama_dusuk"        # hedef cok uzak/kucuk -> AV'ye girmedi
        cx_n = float(hedef["cx"]) / W
        cy_n = float(hedef["cy"]) / H
        if not (c.AV_YATAY[0] <= cx_n <= c.AV_YATAY[1]):
            return False, "AV_disi_yatay"        # merkez yatayda AV disinda
        if not (c.AV_DIKEY[0] <= cy_n <= c.AV_DIKEY[1]):
            return False, "AV_disi_dikey"
        return True, None

    def adim(self, hedef, W, H, t):
        """Bir algi frame'i isle. hedef: AlgiCiktisi.hedef | None. t: sn (algi
        timestamp). Kilit conf esigi KilitCfg.KILIT_CONF_MIN'dir (handoff'tan AYRI).
        -> {sayan, kumulatif_kilit_sn, surekli_kilit_sn, kilit_tamam, yeni_kilit}.
        yeni_kilit: bu frame'de kilit_tamam ilk kez True oldu mu."""
        c = self.cfg
        dt = (t - self._son_t) if self._son_t is not None else 0.0
        if dt < 0:
            dt = 0.0
        self._son_t = t
        sayan, engel = self._sayar_mi(hedef, W, H)
        if engel is not None:
            self._engel_sayac[engel] = self._engel_sayac.get(engel, 0) + 1

        # kayan pencere: sayan-frame surelerini ekle, 10 sn'den eskiyi at
        if sayan and dt > 0:
            self._pencere.append((t, dt))
            self._kumulatif += dt
        while self._pencere and (t - self._pencere[0][0]) > c.PENCERE_SN:
            _te, de = self._pencere.popleft()
            self._kumulatif -= de
        if self._kumulatif < 0:
            self._kumulatif = 0.0

        # kesintisiz sayac + KOPRULEME (kare kacagi toleransi):
        #  - sayan: +dt; kacak sifir; kopru KAPANIR (sayan kare koprüyü tamamlar)
        #  - saymayan: ILK karede (surekli=0) VEYA kacak>200ms -> sifirla (kopru YOK);
        #    aksi halde surekli DONAR + kopru_acik=True (bitiste angajman verilmez)
        if sayan:
            self.surekli_kilit_sn += dt
            self._kacak_ardisik = 0.0
            self._kopru_acik = False
        else:
            self._kacak_ardisik += dt
            if self.surekli_kilit_sn <= 0.0 or self._kacak_ardisik > self.cfg.KACAK_TOLERANS_SN:
                self.surekli_kilit_sn = 0.0      # ILK kare / uzun kacak -> koprü YOK
                self._kopru_acik = False
            else:
                self._kopru_acik = True          # kisa kacak: surekli DONAR, kopru aday

        # kilit_tamam: kumulatif >=5 sn ilk kez -> kenar tetik
        yeni_kilit = False
        if not self.kilit_tamam and self._kumulatif >= c.KUMULATIF_HEDEF_SN:
            self.kilit_tamam = True
            yeni_kilit = True

        kap_y, kap_d = self.kaplama_eksen(hedef, W or 0, H or 0)
        self._son_sayan = sayan
        return {"sayan": sayan, "engel": engel,
                "kumulatif_kilit_sn": self._kumulatif,
                "surekli_kilit_sn": self.surekli_kilit_sn,
                "kilit_tamam": self.kilit_tamam,
                "yeni_kilit": yeni_kilit,
                "kaplama_yatay": kap_y, "kaplama_dikey": kap_d,
                "pencere_doluluk": min(1.0, self._kumulatif / c.KUMULATIF_HEDEF_SN)}

    def angajman_hazir(self):
        """Angajman on sarti: kilit paketi gonderilebilir VE kesintisiz >=3 sn.
        BITISTE KOPRU GECERSIZ: kopru_acik iken (kaçak devam, sayan kare gelmedi)
        kesintisiz garanti YOK -> angajman verilmez (kopru sayan kareyle tamamlanmali)."""
        return (self.kilit_tamam and not self._kopru_acik
                and self.surekli_kilit_sn >= self.cfg.SUREKLI_ANGAJMAN_SN)

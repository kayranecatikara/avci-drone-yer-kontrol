"""
================================================================================
AVCI DRONE — ANA KONTROL DONGUSU
================================================================================
J (GNSSDuzeltici) + guduum + kamera devri + debug olcumu, tek dosyada.

AKIS:
  1. SDK'dan BOZUK hedef konumu al  -> J temizler
  2. Kendi TEMIZ konumunu al (get_drone_location)
  3. Bagil konum hesapla, hedefe yonel (guduum)
  4. ARAMA(GPS) durumunda: J'li hedefe git
  5. Kamera Talon'u gorunce -> KILIT(kamera) durumuna gec
  6. KILIT'te: kameranin verdigi gercek bagil konuma hassas yonel

KULLANIM (gercek oyun):
    import drone_sdk
    from ana_kontrol import AvciKontrol
    k = AvciKontrol(drone_sdk)
    k.calistir()

KULLANIM (test):
    import mock_drone_sdk
    k = AvciKontrol(mock_drone_sdk)
    # test harness mock.adim(dt) ile ilerletir, k.adim() cagirir

>>> ISARET UYARISI: pitch/roll/yaw isaretleri oyunun koordinat sistemine
    baglidir. Gercek oyunda dron ters yone giderse, asagidaki ISARET
    sabitlerini (-1/+1) cevir. Mock'ta dogru calisiyor.
================================================================================
"""
import math
import time
import numpy as np
from inovasyonlu_j_v2 import GNSSDuzeltici as V2Filtre      # v2: tek uretim filtresi

# --- guduum isaret sabitleri (gercek oyunda gerekirse cevir) ---
PITCH_ISARET = +1.0
ROLL_ISARET  = +1.0
YAW_ISARET   = +1.0

# --- HIZ-TAKIPLI KUYRUK TAKIBI (tail-chase) sabitleri ---
# Tam gaz dalis YERINE: istenen hiz vektoru -> sonumlu ivme -> tilt. Hedefin
# hizina ESITLENIP arkasina (kuyruguna) oturur; salinim ve "onune gecme" biter.
# (Tum guduum matematigi METRE'de calisir; g=9.81 m/s^2.)
STANDOFF_M  = 20.0   # kuyrukta durulacak mesafe (m); KILIT'te 0.4x (daha sokul)
KP_CLOSE    = 0.5    # menzil hatasi -> ekstra kapanis hizi (1/s)
KAPANIS_MAX = 12.0   # ekstra kapanis hizi tavani (m/s)
GERI_MAX    = 3.0    # cok yakinsa geri cekilme tavani (m/s)
KP_VEL      = 1.2    # hiz hatasi -> ivme kazanci (1/s); sonumleme saglar
A_MAX       = 8.0    # yatay ivme tavani (m/s^2)
MAX_TILT    = math.radians(35.0)   # normalize tilt komutu olcegi
KZ          = 0.5    # irtifa hatasi (m) -> dikey komut
KDZ         = 0.30   # dikey hiz sonumleme
RAMP_S      = 1.5    # soft-start suresi (s): ilk sicramayi onler

# --- kamera ---
KAMERA_FOV_YARIM = math.radians(62.5)   # 125 derece / 2
KAMERA_MENZIL    = 5000.0               # cm (50 m)
KILIT_KARE       = 5                     # kac ardisik kare goruunce kilit
KAYIP_KARE       = 15                    # kac kare goruunmezse arama'ya don


# Guduum kaynagi -> filtre fabrikasi. "gercek" filtre kullanmaz (truth'a gider).
def _filtre_uret(kaynak):
    if kaynak == "gercek":
        return None                # Gercek GPS: filtre yok, truth'a git (sim/test)
    return V2Filtre()              # varsayilan ve tek uretim filtresi: v2


class AvciKontrol:
    def __init__(self, drone, debug_olc=True, kaynak="v2"):
        self.drone = drone
        self.kaynak = kaynak           # "v2" | "gercek"
        self.filtre = _filtre_uret(kaynak)
        self.durum = "ARAMA"            # ARAMA -> KILIT
        self.son_ham = None
        self.son_temiz = None           # J'nin son gecerli ciktisi (cm)
        self.son_hiz = None             # J'nin kestirdigi hedef hizi (cm/s, 3B) - hiz esleme icin
        # kendi hiz vektoru kestirimi (temiz konum turevi) + soft-start
        self._own_prev = None           # onceki kendi konum (cm)
        self._own_t    = None           # onceki olcum zamani (perf_counter)
        self._own_yon  = np.zeros(3)    # konum turevinden YON kestirimi (cm/s, suzulmus)
        self._own_vel  = np.zeros(3)    # kendi hiz (cm/s, 3B): yon*SDK_skaler_hiz
        self._ramp_t   = None           # gorev basi soft-start zaman damgasi
        self.gordu_sayac = 0
        self.kayip_sayac = 0
        # debug olcum birikimi
        self.debug_olc = debug_olc
        self.ham_hatalar = []
        self.j_hatalar = []
        self.bozukluk_sayac = {}

    # ----------------------------------------------------------------
    #  Guduum kaynagini CANLI degistir (v2/Gercek butonlari)
    #  Yeni filtre taze baslar; son_temiz korunur ki filtre isinirken drone
    #  son hedefe gitmeye devam etsin (hover'a dusmesin).
    # ----------------------------------------------------------------
    def set_kaynak(self, kaynak):
        if kaynak == self.kaynak and (self.filtre is not None or kaynak == "gercek"):
            return                          # zaten o kaynak -> dokunma
        self.kaynak = kaynak
        self.filtre = _filtre_uret(kaynak)
        self.son_ham = None                 # yeni filtre taze beslensin
        self.son_hiz = None                 # hiz esleme kapali baslasin (filtre isinana dek)
        self._ramp_t = None                 # yeni gorevde temiz soft-start
        self._own_yon = np.zeros(3)         # yon kestirimini sifirla
        self._own_vel = np.zeros(3)         # kendi hiz kestirimini sifirla

    # ----------------------------------------------------------------
    #  J: bozuk hedef konumu temizle (sadece YENI telemetri gelince)
    # ----------------------------------------------------------------
    def _hedef_temizle(self):
        # GERCEK GPS modu: filtreyi atla, oyunun GERCEK hedef konumunu hedef al.
        # (Yalnizca debug truth varken anlamli; sim/test icin "ust sinir" guduum.)
        if self.kaynak == "gercek":
            self.son_ham = self.drone.get_target_location()   # debug olcumu icin tut
            dbg = self.drone.get_debug_truth()
            if dbg.get("available"):
                self.son_temiz = np.array(dbg["target"]["position"], float)
            self.son_hiz = None               # gercek modda lead yok (saf pursuit)
            return self.son_temiz
        ham = self.drone.get_target_location()
        if ham != self.son_ham:               # yeni telemetri
            self.son_ham = ham
            sonuc = self.filtre.guncelle(ham[0], ham[1], ham[2])
            if sonuc is not None:
                self.son_temiz = np.array(sonuc)
                # J hedef hizini da kestirir -> ongorulu (lead) yonelime besle.
                durum = self.filtre.durum_guduum()
                self.son_hiz = None if durum is None else np.array(durum["vel"], float)
        return self.son_temiz                  # None olabilir (isinma/donma)

    # ----------------------------------------------------------------
    #  Kamera: hedef goruus alaninda mi?  (STUB)
    #  >>> GERCEK SISTEM: burayi YOLO ile degistir. YOLO Talon'u kutu
    #      icine alirsa (gordu=True) ve goruntuden bagil konum cikarirsa
    #      onu dondur. Debug truth SADECE testte var; yarismada YOLO sart.
    # ----------------------------------------------------------------
    def _kamera_kontrol(self, drone_pos, drone_yaw):
        dbg = self.drone.get_debug_truth()
        if not dbg.get("available"):
            # Gercek yarisma: debug yok -> YOLO buraya baglanir
            return False, None
        hedef_gercek = np.array(dbg["target"]["position"])
        v = hedef_gercek[:2] - drone_pos[:2]
        mesafe = np.linalg.norm(hedef_gercek - drone_pos)
        if mesafe > KAMERA_MENZIL:
            return False, None
        # boresight = drone yaw yonu; hedef o koni icinde mi?
        bearing = math.atan2(v[1], v[0])
        aci = abs(self._sar(bearing - drone_yaw))
        if aci < KAMERA_FOV_YARIM:
            return True, hedef_gercek          # kamera gercek bagil konumu verir
        return False, None

    @staticmethod
    def _sar(a):
        while a > math.pi: a -= 2*math.pi
        while a < -math.pi: a += 2*math.pi
        return a

    # ----------------------------------------------------------------
    #  Kendi hiz VEKTORU kestirimi.
    #  BUYUKLUK: SDK'nin DOGRU skaler hizi (get_drone_speed). Konum turevi
    #  oyunda guvenilmez (telemetri her tikte tazelenmez -> turev 0 cikip
    #  kontrolcuye "duruyorum" dedirtir, fren yapmaz, maks hiza firlar).
    #  YON: konum turevi (suzulmus); turev yoksa drone heading'i.
    #  Boylece kontrolcu gercek hizini gorur ve frenler.
    # ----------------------------------------------------------------
    def _kendi_hiz(self, drone_pos):
        now = time.perf_counter()
        if self._own_prev is not None and self._own_t is not None:
            dt = now - self._own_t
            if 0.005 <= dt <= 0.2:                          # makul ardisik adim
                v = (drone_pos - self._own_prev) / dt       # cm/s (yon icin)
                self._own_yon = 0.7 * self._own_yon + 0.3 * v
            else:                                           # bayat/bosluk -> taze baslangic
                self._own_yon = np.zeros(3)
                self._ramp_t = None
        self._own_prev = drone_pos.copy()
        self._own_t = now

        spd = float(self.drone.get_drone_speed())           # cm/s (DOGRU buyukluk)
        n = float(np.linalg.norm(self._own_yon))
        if n > 50.0:                                        # >0.5 m/s: turev yonu guvenilir
            self._own_vel = self._own_yon * (spd / n)
        else:                                               # yon yok -> heading'i kullan
            yaw = math.radians(self.drone.get_drone_rotation()[2])
            self._own_vel = np.array([spd*math.cos(yaw), spd*math.sin(yaw), 0.0])

    # ----------------------------------------------------------------
    #  Guduum: hedefe yonel (ongorulu/lead pursuit + yaw hizalama)
    # ----------------------------------------------------------------
    def _guduum(self, drone_pos, drone_yaw, hedef_pos, agresif=1.0):
        # HIZ-TAKIPLI KUYRUK TAKIBI: tam gaz dalis DEGIL. Bir "istenen hiz
        # vektoru" hesaplanir; hedefin hizina ESITLENIP arkasina (kuyruguna)
        # oturulur. Sonumlu ivme (Kp*(v_istenen - kendi_hizin)) salinimi ve
        # asiri hizi keser. Matematik METRE'de; g=9.81 m/s^2.
        CM2M = 0.01
        dp = np.asarray(drone_pos, float) * CM2M
        tp = np.asarray(hedef_pos, float) * CM2M                 # hedefin GUNCEL yeri (lead YOK)
        tv = (np.asarray(self.son_hiz, float) * CM2M) if self.son_hiz is not None else np.zeros(3)
        ov = self._own_vel * CM2M

        # === YATAY: istenen hiz vektoru (stalking) ===
        los = tp[:2] - dp[:2]
        R = float(np.linalg.norm(los))
        u = los / max(R, 1e-6)
        hedef_hiz = float(np.linalg.norm(tv[:2]))
        # uzakta biraz hizli kapat, STANDOFF'ta hedef hizina ESITLE (kuyrukta dur).
        standoff = STANDOFF_M * (0.4 if self.durum == "KILIT" else 1.0)
        kapanis = float(np.clip(KP_CLOSE * (R - standoff), -GERI_MAX, KAPANIS_MAX))
        istek_hiz = max(hedef_hiz + kapanis, 0.0)
        v_des = istek_hiz * u

        # sonumlu ivme + tavan
        a_des = KP_VEL * (v_des - ov[:2])
        n = float(np.linalg.norm(a_des))
        if n > A_MAX:
            a_des = a_des * (A_MAX / n)

        # dunya -> govde, ivme -> normalize tilt komutu (ANGLE MODE)
        cy, sy = math.cos(drone_yaw), math.sin(drone_yaw)
        a_fwd   =  a_des[0] * cy + a_des[1] * sy
        a_right = -a_des[0] * sy + a_des[1] * cy
        pitch_cmd = PITCH_ISARET * np.clip(math.atan2(a_fwd,  9.81) / MAX_TILT, -1, 1)
        roll_cmd  = ROLL_ISARET  * np.clip(math.atan2(a_right, 9.81) / MAX_TILT, -1, 1)

        # yaw: hedefe bak (kamera hedefe donuk kalsin -> surekli gorsel temas)
        rel = self._sar(math.atan2(los[1], los[0]) - drone_yaw)
        yaw_cmd = YAW_ISARET * np.clip(rel / math.radians(45), -1, 1)

        # === DIKEY: hedef irtifasina, dikey hiz sonumlemeli ===
        dz = tp[2] - dp[2]
        throttle_cmd = float(np.clip(KZ * dz - KDZ * ov[2], -1, 1))

        # SOFT-START: gorev baslayinca ilk RAMP_S saniye komut otoritesi 0->1
        if self._ramp_t is None:
            self._ramp_t = time.perf_counter()
        ramp = min(1.0, (time.perf_counter() - self._ramp_t) / RAMP_S)
        return throttle_cmd * ramp, pitch_cmd * ramp, roll_cmd * ramp, yaw_cmd

    # ----------------------------------------------------------------
    #  Debug olcum: J gercekten ham'dan iyi mi?
    # ----------------------------------------------------------------
    def _debug_olc(self):
        dbg = self.drone.get_debug_truth()
        if not dbg.get("available") or self.son_temiz is None: return
        gercek = np.array(dbg["target"]["position"])
        ham = np.array(self.son_ham)
        self.ham_hatalar.append(np.linalg.norm(ham - gercek))
        self.j_hatalar.append(np.linalg.norm(self.son_temiz - gercek))
        for ad in self.drone.get_active_corruption():
            self.bozukluk_sayac[ad] = self.bozukluk_sayac.get(ad, 0) + 1

    # ----------------------------------------------------------------
    #  TEK kontrol adimi (donguude bir kez cagrilir)
    # ----------------------------------------------------------------
    def adim(self):
        drone_pos = np.array(self.drone.get_drone_location())   # TEMIZ
        self._kendi_hiz(drone_pos)                              # kendi hiz vektorunu guncelle
        # Oyun yaw'i DERECE verir; guduum/kamera RADYAN bekler -> cevir.
        drone_yaw = math.radians(self.drone.get_drone_rotation()[2])

        # 1) J ile bozuk hedefi temizle
        j_hedef = self._hedef_temizle()
        if self.debug_olc: self._debug_olc()

        # 2) kamera kontrol (devir mantigi)
        gordu, kamera_hedef = self._kamera_kontrol(drone_pos, drone_yaw)
        if gordu:
            self.gordu_sayac += 1; self.kayip_sayac = 0
        else:
            self.kayip_sayac += 1
            if self.kayip_sayac > KAYIP_KARE: self.gordu_sayac = 0

        # 3) durum gecisi
        if self.durum == "ARAMA" and self.gordu_sayac >= KILIT_KARE:
            self.durum = "KILIT"
        elif self.durum == "KILIT" and self.kayip_sayac > KAYIP_KARE:
            self.durum = "ARAMA"

        # 4) hangi hedefi kullanacagiz?
        if self.durum == "KILIT" and kamera_hedef is not None:
            hedef = kamera_hedef          # kamera = gercek bagil konum
            agresif = 1.0
        elif j_hedef is not None:
            hedef = j_hedef               # J'li GPS hedefi
            agresif = 1.0
        else:
            # henuz J ciktisi yok -> hover bekle
            self.drone.set_control_surfaces(0.0, 0.0, 0.0, 0.0, True)
            return

        # 5) guduum -> kontrol komutu
        thr, pit, rol, yaw = self._guduum(drone_pos, drone_yaw, hedef, agresif)
        self.drone.set_control_surfaces(thr, pit, rol, yaw, True)

    # ----------------------------------------------------------------
    #  Gercek oyun ana donguusu
    # ----------------------------------------------------------------
    def calistir(self):
        if not self.drone.connect():
            print("Baglanti kurulamadi (oyun acik ve Play modunda mi?)")
            return
        self.drone.set_arm(True)
        try:
            while True:
                self.adim()
                time.sleep(0.02)   # 50 Hz
        except KeyboardInterrupt:
            self.drone.disconnect()

    # ----------------------------------------------------------------
    #  Debug ozet (test sonrasi)
    # ----------------------------------------------------------------
    def ozet(self):
        if not self.ham_hatalar:
            return "Debug olcum yok."
        import numpy as np
        h = np.array(self.ham_hatalar)/100; j = np.array(self.j_hatalar)/100
        s = []
        s.append(f"Ham hedef hatasi : {h.mean():.1f} m")
        s.append(f"J hedef hatasi   : {j.mean():.1f} m")
        s.append(f"J kazanci        : %{100*(h.mean()-j.mean())/h.mean():.0f}  "
                 f"({'J IYI' if j.mean()<h.mean() else 'J KOTU!'})")
        s.append(f"Aktif bozukluklar: {self.bozukluk_sayac}")
        return "\n".join(s)

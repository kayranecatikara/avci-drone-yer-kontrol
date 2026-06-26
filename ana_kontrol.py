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
from blok_j import GNSSDuzeltici

# --- guduum isaret sabitleri (gercek oyunda gerekirse cevir) ---
PITCH_ISARET = +1.0
ROLL_ISARET  = +1.0
YAW_ISARET   = +1.0

# --- kamera ---
KAMERA_FOV_YARIM = math.radians(62.5)   # 125 derece / 2
KAMERA_MENZIL    = 5000.0               # cm (50 m)
KILIT_KARE       = 5                     # kac ardisik kare goruunce kilit
KAYIP_KARE       = 15                    # kac kare goruunmezse arama'ya don


class AvciKontrol:
    def __init__(self, drone, debug_olc=True):
        self.drone = drone
        self.filtre = GNSSDuzeltici()
        self.durum = "ARAMA"            # ARAMA -> KILIT
        self.son_ham = None
        self.son_temiz = None           # J'nin son gecerli ciktisi (cm)
        self.gordu_sayac = 0
        self.kayip_sayac = 0
        # debug olcum birikimi
        self.debug_olc = debug_olc
        self.ham_hatalar = []
        self.j_hatalar = []
        self.bozukluk_sayac = {}

    # ----------------------------------------------------------------
    #  J: bozuk hedef konumu temizle (sadece YENI telemetri gelince)
    # ----------------------------------------------------------------
    def _hedef_temizle(self):
        ham = self.drone.get_target_location()
        if ham != self.son_ham:               # yeni telemetri
            self.son_ham = ham
            sonuc = self.filtre.guncelle(ham[0], ham[1], ham[2])
            if sonuc is not None:
                self.son_temiz = np.array(sonuc)
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
    #  Guduum: hedefe yonel (pure pursuit + yaw hizalama)
    # ----------------------------------------------------------------
    def _guduum(self, drone_pos, drone_yaw, hedef_pos, agresif=1.0):
        v = hedef_pos[:2] - drone_pos[:2]
        mesafe_yatay = np.linalg.norm(v)
        bearing = math.atan2(v[1], v[0])
        rel = self._sar(bearing - drone_yaw)

        # yaw: hedefe don (kamera hedefe baksin)
        yaw_cmd = YAW_ISARET * np.clip(rel / math.radians(60), -1, 1)

        # govde cercevesinde ileri/sag bilesen
        ileri = math.cos(rel)
        sag   = math.sin(rel)
        # mesafeyle olcekle: uzakta tam gaz, yakinda yavasla
        gaz = np.clip(mesafe_yatay / 3000.0, 0.15, 1.0) * agresif
        pitch_cmd = PITCH_ISARET * np.clip(ileri * gaz, -1, 1)
        roll_cmd  = ROLL_ISARET  * np.clip(sag * gaz * 0.6, -1, 1)

        # irtifa: hedef yuksekligine git
        irtifa_hata = (hedef_pos[2] - drone_pos[2]) / 2000.0
        throttle_cmd = np.clip(irtifa_hata, -1, 1)

        return throttle_cmd, pitch_cmd, roll_cmd, yaw_cmd

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

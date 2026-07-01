# -*- coding: utf-8 -*-
"""
================================================================================
AVCI DRONE — ANA KONTROL DONGUSU  (FAZ 1: GNSS ile Yaklasma)
================================================================================
J (GNSSDuzeltici) + FAZ-1 guduum + handoff + debug olcumu, tek dosyada.

>>> BU DOSYA YENI GUDUM ILE DEGISTIRILDI <<<
    Eski "RAM / hiz-takipli kuyruk takibi" yaklasma mantigi (V_RAM, STANDOFF,
    KP_CLOSE, KP_VEL, _kendi_hiz, agresif dalis...) TAMAMEN KALDIRILDI.
    Yerine "faz1_gnss_yaklasma" guudumu gomuldu:
      PD + EMA-filtreli turev -> sonumleme, mesafeye gore komut tavani
      (overshoot guard), komut hiz limiti (rate limit), holonomik oteleme +
      yavas yaw, sure-tabanli None yonetimi, genis HISTEREZISLI handoff.

TASARIM TEZI (cevik hedefe dayaniklilik):
  GNSS gecikme-baskin + ~29 m hata tabani. Bu yuzden FAZ 1 HEDEFI "kestirilen
  noktaya hassas oturmak" DEGIL, "tespit yaricapina yaklasip devretmek"
  (PROXIMITY). Manevra yapan hedefi kotu GNSS ile hassas kovalamak hem bosuna
  hem salinim uretir; hassasiyet gorus/CV fazinin isidir.

AKIS:
  1. SDK'dan BOZUK hedef konumu al  -> J (inovasyonlu_j_v2) temizler (+2sn lead)
  2. Kendi TEMIZ konumunu al (get_drone_location)
  3. Bagil hatayi GOVDE cercevesine cevir -> PD ile yaklasma komutu uret
  4. Tespit menziline (HANDOFF_RANGE) girince -> durum "KILIT" (gorus devralabilir)
  5. Gorus/CV fazi [YAPILACAK]: _kamera_kontrol stub'i yerine YOLO baglanacak

KULLANIM (gercek oyun):
    import drone_sdk
    from ana_kontrol import AvciKontrol
    k = AvciKontrol(drone_sdk)
    k.calistir()

KULLANIM (test / web arayuz):
    server.py beyin = AvciKontrol(drone) yapip 50 Hz beyin.adim() cagirir.
    Manuel/pasif modda beyin._hedef_temizle() ile sadece J olcumu akar.

>>> SIMDE DOGRULA (frame/birim/isaret) <<<
  - Konum birimi cm (filtre R=100, hiz_max=3000 -> cm; get_drone_speed cm/s).
  - get_drone_rotation DERECE dondurur (Cfg.ROT_IN_DEGREES=True).
  - Isaret yonleri yanlissa Cfg.PITCH_SIGN / ROLL_SIGN / YAW_SIGN cevir.
    (Tuning sirasi: once SIGN/frame, sonra yaw, yatay KP, KD, hiz tavanlari.)

>>> KISIT: Asagidaki GAIN ve HIZ TAVANLARI sim'de elle tune edilecektir;
    KP_H/KD_H/KP_Z/KD_Z/KP_YAW ve V_CAP_FAR/V_CAP_NEAR/BRAKE_DIST verili
    baslangic degerleridir, kod entegrasyonunda DEGISTIRILMEZ.
================================================================================
"""
import math
import time
import numpy as np
from fusion.inovasyonlu_j_v2 import GNSSDuzeltici as V2Filtre   # v2: tek uretim filtresi
from guidance.ibvs_guidance import IBVSGuidance, IBVSConfig     # gorsel faz: duz IBVS guduum


# ==========================================================
# CONFIG  (faz1_gnss_yaklasma'dan; gain/tavan degerleri AYNEN)
# ==========================================================
class Cfg:
    # --- BIRIM / FRAME / ISARET (SIMDE DOGRULA) ---
    ROT_IN_DEGREES = True       # get_drone_rotation derece dondururse True
    PITCH_SIGN = +1.0           # ileri hareket +pitch degilse -1
    ROLL_SIGN  = +1.0           # saga strafe +roll degilse -1
    YAW_SIGN   = +1.0           # hedefe donus icin +yaw degilse -1
    # Dikey isaret: SDK +1=tirman / UE Z-yukari -> dogru deger +1.0 (sim ile dogrulandi:
    # +1 hedef irtifasina yakinsar, -1 irtifayi artirip kacar). Oyunun Z ekseni
    # gercekten TERS oldugu KANITLANIRSA -1 yap; aksi halde +1 birak.
    Z_SIGN     = +1.0

    # --- DONGU (server.py / calistir 50 Hz surer) ---
    LOOP_HZ = 50.0
    DT = 1.0 / LOOP_HZ

    # --- KALKIS / ARAMA IRTIFASI ---
    SEARCH_ALT = 5000.0         # cm; arama irtifasi (TUNE). Kalkis ayrı katmanda ise TAKEOFF=False.
    TAKEOFF = True
    ALT_TOL = 200.0             # cm; irtifa ulasma tolerasi
    TAKEOFF_THR = 0.6           # tirmanma throttle

    # --- HANDOFF (histerezisli) ---
    HANDOFF_RANGE = 4000.0      # cm; tespit menziline gore TUNE et (genis tut)
    HANDOFF_EXIT  = 5000.0      # bu mesafenin disina cikinca handoff iptal

    # --- YAKLASMA HIZI PROFILI (overshoot guard) — DEGISTIRME ---
    V_CAP_FAR  = 2500.0         # cm/s uzakta (120km/h = 3333 cm/s'in altinda)
    V_CAP_NEAR = 500.0          # cm/s handoff yakininda
    BRAKE_DIST = 7000.0         # cm; bu mesafe altinda hizi kademeli dusur

    # --- PD GAINS (hata cm cinsinden) — DEGISTIRME ---
    KP_H = 0.00025              # yatay konum -> komut
    KD_H = 0.00060             # yatay turev -> sonumleme (modest; filtre zaten lead'liyor)
    KP_Z = 0.00040             # irtifa -> throttle
    KD_Z = 0.00100
    KP_YAW = 1.0               # yaw hatasi (rad) -> yaw komutu

    # --- KOMUT TAVANLARI ---
    PITCH_MAX = 0.75
    ROLL_MAX  = 0.75
    THR_UP    = 0.70
    THR_DN    = -0.40          # nazik alcalma; ASLA -1 (serbest dusus) DEGIL
    YAW_MAX   = 0.45

    # --- HIZ LIMITI (bank rate uyumlu; salinim onleyici) ---
    MAX_DELTA = 0.05           # komut/tik max degisim

    # --- FILTRELEME / DEADBAND ---
    DERIV_EMA = 0.20
    POS_DEADBAND = 150.0       # cm; yakinda jitter onle
    YAW_DEADBAND = math.radians(3)

    # --- None YONETIMI (tik @50Hz) ---
    # GPS ~1Hz -> normal donmus kare serisi ~50 tik. Dropout bundan UZUN.
    HOLD_TICKS = 75            # ~1.5s: bu sureye kadar son kestirimi tut
    DROPOUT_TICKS = 75         # otesi: dropout -> loiter

    # --- TESHIS (irtifa kacma sorununu cozmek icin gecici) ---
    # True: ~2Hz konsola [Z] satiri basar. drone_z vs hedef irtifasi (filtre & GERCEK),
    # ez, thr, hiz, pitch. Sorun cozulunce False yap.
    DEBUG_Z = True

    # --- GORSEL GUDUM (IBVS) FSM — tik @50Hz, inference-kare dedup edilir ---
    GORSEL_GIRIS_N  = 5      # N ardisik GECERLI tespit -> GORSEL_GUDUM (gorsel temas)
    GORSEL_KAYIP_M  = 15     # M ardisik kayip -> kayip dogrulandi
    GORSEL_HOLD_S   = 0.50   # kayip sonrasi son gorsel komutu kisa sure koru (sn)
    GORSEL_CONF_MIN = 0.65   # gecerli tespit icin min confidence (HUD-yazi sahte-pozitifini eler)
    GORSEL_LOST_S   = 0.60   # inference STALL emniyeti (M'in duvar-saati karsiligi)


# ==========================================================
# HELPERS  (faz1_gnss_yaklasma'dan AYNEN)
# ==========================================================
def wrap_pi(a):
    return (a + math.pi) % (2.0 * math.pi) - math.pi

def clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x

def deadband(x, db):
    return 0.0 if abs(x) < db else x

def rate_limit(target, prev, max_delta):
    return prev + clamp(target - prev, -max_delta, max_delta)

def world_to_body(ex, ey, yaw_rad):
    """World yatay hatayi govde cercevesine cevirir.
    Varsayim: RH, z-up, yaw CCW, burun=+x. Yanlissa Cfg.*_SIGN ile duzelt."""
    c, s = math.cos(yaw_rad), math.sin(yaw_rad)
    e_fwd   = ex * c + ey * s
    e_right = ex * s - ey * c
    return e_fwd, e_right

def speed_cap(d_horiz):
    """Mesafeye gore izin verilen yaklasma hizi tavani (cm/s)."""
    if d_horiz >= Cfg.BRAKE_DIST:
        return Cfg.V_CAP_FAR
    t = d_horiz / Cfg.BRAKE_DIST                      # 0..1
    return Cfg.V_CAP_NEAR + (Cfg.V_CAP_FAR - Cfg.V_CAP_NEAR) * t


# --- kamera devir esikleri (gorus fazi hook'u icin) ---
KAMERA_FOV_YARIM = math.radians(65.77)  # 131.54 derece / 2
KAMERA_MENZIL    = 5000.0               # cm (50 m)


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
        self.durum = "ARAMA"            # ARAMA(yaklasma) -> KILIT(handoff/gorus)
        self.son_ham = None
        self.son_temiz = None           # J'nin son gecerli ciktisi (cm, 2sn lead) - YATAY icin
        self.son_z_anlik = None         # J'nin ANLIK (lead'siz) irtifa kestirimi (cm) - DIKEY icin
        self.son_hiz = None             # J'nin kestirdigi hedef hizi (cm/s, 3B) - olcum/ileri kullanim
        self._fresh = False             # bu tik J'den YENI gecerli kestirim geldi mi?

        # --- FAZ-1 guduum durumu (faz1_gnss_yaklasma.Faz1Guidance'tan) ---
        self.prev = {'thr': 0.0, 'pitch': 0.0, 'roll': 0.0, 'yaw': 0.0}
        self.e_prev = None
        self.t_prev = None
        self.de = [0.0, 0.0, 0.0]       # EMA-filtreli hata turevi (cm/s)
        self.none_count = 0
        self.last_est = None
        self.handoff = False
        self.handoff_announced = False
        self._kalkis_done = (not Cfg.TAKEOFF)

        # --- GORSEL GUDUM (IBVS) durumu — gorsel temas sonrasi devralir ---
        # Isaretler mevcut (kalibreli) GPS guduminden miras; SIGN_THR=-Z_SIGN (goruntu
        # y-asagi terslemesi). SIGN_YAW SDK'da belgesiz -> ilk ucusta dogrula.
        self.gorsel = IBVSGuidance(IBVSConfig(
            SIGN_PITCH=Cfg.PITCH_SIGN, SIGN_ROLL=Cfg.ROLL_SIGN,
            SIGN_THR=-Cfg.Z_SIGN, SIGN_YAW=+1.0))
        self.gorsel_aktif   = False     # True iken adim() GPS YONELIM blogunu (382-436) ATLAR
        self.son_tespit     = None      # son GECERLI tespit (dict)
        self.gordu_sayac    = 0         # ardisik gecerli inference karesi
        self.kayip_sayac    = 0         # ardisik kayip inference karesi
        self.kayip_hold_t0  = None      # kayip-hold baslangici (perf_counter)
        self._son_tespit_ts = None      # inference-kare dedup (ayni kareyi 2x sayma)
        self._t_son_gecerli = 0.0       # son gecerli tespit zamani (perf_counter)
        self._komut_ts      = None      # son IBVS hesabinin tespit ts'i (coast tespiti)
        self.son_gorsel_komut = None    # son IBVS komutu (coast icin)
        # overlay/CSV debug alanlari (server bunlari beyin_lock ile okur):
        self.g_ex = 0.0; self.g_ey = 0.0
        self.g_doluluk = 0.0; self.g_gate = 0.0
        self.g_conf = 0.0
        self.g_cmd = {'thr': 0.0, 'pitch': 0.0, 'roll': 0.0, 'yaw': 0.0}

        # debug olcum birikimi
        self.debug_olc = debug_olc
        self.ham_hatalar = []
        self.j_hatalar = []
        self.bozukluk_sayac = {}

    # ----------------------------------------------------------------
    #  Guduum kaynagini CANLI degistir (v2/Gercek butonlari)
    #  Yeni filtre taze baslar; FAZ-1 durumu da sifirlanir (temiz soft-start).
    # ----------------------------------------------------------------
    def set_kaynak(self, kaynak):
        if kaynak == self.kaynak and (self.filtre is not None or kaynak == "gercek"):
            return                          # zaten o kaynak -> dokunma
        self.kaynak = kaynak
        self.filtre = _filtre_uret(kaynak)
        self.son_ham = None                 # yeni filtre taze beslensin
        self.son_z_anlik = None
        self.son_hiz = None
        self._fresh = False
        # FAZ-1 durumunu sifirla: komutlar 0'dan rate-limit'lensin, turev/handoff temiz.
        self.prev = {'thr': 0.0, 'pitch': 0.0, 'roll': 0.0, 'yaw': 0.0}
        self.e_prev = None
        self.t_prev = None
        self.de = [0.0, 0.0, 0.0]
        self.none_count = 0
        self.last_est = None
        self.handoff = False
        self.handoff_announced = False
        self.durum = "ARAMA"
        self._kalkis_done = (not Cfg.TAKEOFF)
        # GORSEL GUDUM bayraklarini da sifirla (kaynak degisimi = soft-restart)
        self.gorsel_aktif = False
        self.son_tespit = None
        self.gordu_sayac = 0
        self.kayip_sayac = 0
        self.kayip_hold_t0 = None
        self._son_tespit_ts = None
        self._komut_ts = None
        self.son_gorsel_komut = None
        self.gorsel.reset()

    # ----------------------------------------------------------------
    #  J: bozuk hedef konumu temizle (sadece YENI telemetri gelince).
    #  self._fresh: bu cagride J'den YENI gecerli kestirim geldi mi? FAZ-1
    #  None yonetimi (hold vs dropout) bunu kullanir.
    # ----------------------------------------------------------------
    def _hedef_temizle(self):
        # GERCEK GPS modu: filtreyi atla, oyunun GERCEK hedef konumunu hedef al.
        if self.kaynak == "gercek":
            self.son_ham = self.drone.get_target_location()   # debug olcumu icin tut
            dbg = self.drone.get_debug_truth()
            if dbg.get("available"):
                self.son_temiz = np.array(dbg["target"]["position"], float)
                self.son_z_anlik = float(self.son_temiz[2])   # gercekte lead yok -> ayni z
                self._fresh = True
            else:
                self._fresh = False
            self.son_hiz = None               # gercek modda lead yok (saf pursuit)
            return self.son_temiz

        ham = self.drone.get_target_location()
        if ham != self.son_ham:               # yeni telemetri paketi
            self.son_ham = ham
            sonuc = self.filtre.guncelle(ham[0], ham[1], ham[2])
            if sonuc is not None:
                self.son_temiz = np.array(sonuc)   # 2sn lead'li (YATAY intercept icin)
                self._fresh = True            # YENI gecerli kestirim
                # J hedef hizini + ANLIK irtifayi da al. DIKEY icin lead'siz z kullanilir:
                # 2sn dikey lead, hedef dikey manevra yapinca irtifayi cok abartiyor (sim:
                # manevrada +55m sapma). Anlik z gercegi cok daha iyi takip eder.
                durum = self.filtre.durum_guduum()
                if durum is None:
                    self.son_hiz = None
                    self.son_z_anlik = float(self.son_temiz[2])   # fallback
                else:
                    self.son_hiz = np.array(durum["vel"], float)
                    self.son_z_anlik = float(durum["pos"][2])     # lead'siz anlik irtifa
            else:
                self._fresh = False           # isinma/donma -> kestirim yok
        else:
            self._fresh = False               # ratelimit ile donmus kare (yeni bilgi yok)
        return self.son_temiz                  # None olabilir (isinma)

    # ----------------------------------------------------------------
    #  Kamera: hedef goruus alaninda mi?  (STUB — GORUS FAZI HOOK'U)
    #  >>> GERCEK SISTEM: burayi YOLO ile degistir. YOLO Talon'u kutu icine
    #      alirsa (gordu=True) ve goruntuden bagil konum cikarirsa onu dondur.
    #      Debug truth SADECE testte var; yarismada YOLO sart. FAZ-1 handoff
    #      proximity-tabanlidir; gorus fazi devraldiginda bu hook kullanilacak.
    # ----------------------------------------------------------------
    def _kamera_kontrol(self, drone_pos, drone_yaw):
        dbg = self.drone.get_debug_truth()
        if not dbg.get("available"):
            return False, None                 # Gercek yarisma: YOLO buraya baglanir
        hedef_gercek = np.array(dbg["target"]["position"])
        v = hedef_gercek[:2] - drone_pos[:2]
        mesafe = np.linalg.norm(hedef_gercek - drone_pos)
        if mesafe > KAMERA_MENZIL:
            return False, None
        bearing = math.atan2(v[1], v[0])
        aci = abs(wrap_pi(bearing - drone_yaw))
        if aci < KAMERA_FOV_YARIM:
            return True, hedef_gercek
        return False, None

    # ----------------------------------------------------------------
    #  EMA-filtreli hata turevi (degisken update-rate'e dayanikli)
    # ----------------------------------------------------------------
    def _derivative(self, e, t):
        if self.e_prev is None:
            self.e_prev, self.t_prev = e, t
            return self.de
        dt = t - self.t_prev
        if dt > 1e-3:
            a = Cfg.DERIV_EMA
            for i in range(3):
                raw = (e[i] - self.e_prev[i]) / dt
                self.de[i] = (1.0 - a) * self.de[i] + a * raw
            self.e_prev, self.t_prev = e, t
        return self.de

    # ----------------------------------------------------------------
    #  Komut gonder (rate-limit + atomik set_control_surfaces)
    # ----------------------------------------------------------------
    def _send(self, thr, pitch, roll, yaw):
        thr   = rate_limit(thr,   self.prev['thr'],   Cfg.MAX_DELTA)
        pitch = rate_limit(pitch, self.prev['pitch'], Cfg.MAX_DELTA)
        roll  = rate_limit(roll,  self.prev['roll'],  Cfg.MAX_DELTA)
        yaw   = rate_limit(yaw,   self.prev['yaw'],   Cfg.MAX_DELTA)
        self.prev = {'thr': thr, 'pitch': pitch, 'roll': roll, 'yaw': yaw}
        self.drone.set_control_surfaces(thr, pitch, roll, yaw, True)

    def _loiter(self):
        # dropout / veri yok: agresifligi kes, hover (thr=0 -> irtifa korunur), seviyelen
        self._send(0.0, 0.0, 0.0, 0.0)

    # ----------------------------------------------------------------
    #  GORSEL GUDUM (IBVS) — gorsel temas FSM'i + komut adimi
    #  >>> Yarisma kurali: gorsel temas SONRASI yonelim icin GPS KULLANILMAZ.
    #      gorsel_aktif True iken adim() GPS YONELIM blogunu (382-436) ATLAR.
    # ----------------------------------------------------------------
    def _faz1_turev_sifirla(self):
        """Gorsel moddan GPS yaklasmaya donerken FAZ-1 turev/None state'ini temizle
        (prev'e DOKUNMA -> komut rate-limit surekliligi korunur)."""
        self.e_prev = None
        self.t_prev = None
        self.de = [0.0, 0.0, 0.0]
        self.none_count = 0

    def gorsel_guncelle(self, tespit):
        """server kontrol dongusunden HER tikte (adim oncesi) cagrilir; giris/cikis
        FSM'ini surer. Sayaclar INFERENCE-KARESI basina ilerler (ts-dedup): 50 Hz tik
        ayni kareyi tekrar gorur; tik-sayimi 'N ardisik' anlamini ve tek-kare yanlis-
        pozitif korumasini bozardi."""
        now = time.perf_counter()
        yeni_kare = (tespit is not None and tespit.get('ts') != self._son_tespit_ts)
        if yeni_kare:
            self._son_tespit_ts = tespit.get('ts')
            gecerli = bool(tespit.get('var')) and tespit.get('conf', 0.0) >= Cfg.GORSEL_CONF_MIN
            if gecerli:
                self.gordu_sayac += 1
                self.kayip_sayac = 0
                self.son_tespit = tespit
                self._t_son_gecerli = now
                self.g_conf = float(tespit.get('conf', 0.0))
            else:
                self.kayip_sayac += 1
                self.gordu_sayac = 0

        if not self.gorsel_aktif:
            # GIRIS: N ardisik gecerli inference karesi -> GORSEL_GUDUM
            if self.gordu_sayac >= Cfg.GORSEL_GIRIS_N and self.son_tespit is not None:
                self.gorsel_aktif = True
                self.durum = "GORSEL_GUDUM"
                self.kayip_hold_t0 = None
                self._komut_ts = None
                self.son_gorsel_komut = None
                self.gorsel.reset(self.son_tespit.get('cx'), self.son_tespit.get('cy'))
                print("[GORSEL] gorsel temas (%d kare, conf=%.2f) -> GORSEL_GUDUM. "
                      "GPS YONELIMI KAPALI." % (Cfg.GORSEL_GIRIS_N, self.g_conf))
        else:
            # KAYIP: M ardisik kayip VEYA inference stall -> kisa hold -> ARAMA
            kayip = (self.kayip_sayac >= Cfg.GORSEL_KAYIP_M
                     or (now - self._t_son_gecerli) >= Cfg.GORSEL_LOST_S)
            if kayip:
                if self.kayip_hold_t0 is None:
                    self.kayip_hold_t0 = now                  # son gorsel komutu kisa sure koru
                elif (now - self.kayip_hold_t0) >= Cfg.GORSEL_HOLD_S:
                    self.gorsel_aktif = False                 # CIK -> ARAMA (GPS yeniden-yaklasma)
                    self.durum = "ARAMA"
                    self.gordu_sayac = 0
                    self.kayip_hold_t0 = None
                    self._faz1_turev_sifirla()                # re-approach temiz baslasin
                    print("[GORSEL] hedef kayip (hold %.2fs doldu) -> ARAMA "
                          "(GPS yeniden-yaklasma)." % Cfg.GORSEL_HOLD_S)
            else:
                self.kayip_hold_t0 = None                      # yeniden temas -> hold iptal

    def _ibvs_adim(self):
        """GORSEL_GUDUM komut adimi (adim() icinden, gorsel_aktif iken cagrilir).
        gorsel.update YALNIZ yeni tespit ts'inde cagrilir (EMA inference hizinda
        ilerlesin); bayat tikte son komut COAST edilir. Her tik _send ile gonderilir
        (rate-limit korunur)."""
        t = self.son_tespit
        if t is not None and t.get('ts') != self._komut_ts:
            ts = t.get('ts')
            if self._komut_ts is None or not isinstance(ts, (int, float)):
                dt = Cfg.DT
            else:
                dt = ts - self._komut_ts
                if dt < 1e-3:
                    dt = Cfg.DT
            out = self.gorsel.update(t['cx'], t['cy'], t['frame_w'], t['frame_h'],
                                     t['w'], t['h'], dt)
            self._komut_ts = ts
            self.son_gorsel_komut = {'thr': out['throttle'], 'pitch': out['pitch'],
                                     'roll': out['roll'], 'yaw': out['yaw']}
            self.g_ex = out['ex']; self.g_ey = out['ey']
            self.g_doluluk = out['doluluk']; self.g_gate = out['gate']
            self.g_cmd = dict(self.son_gorsel_komut)
        if self.son_gorsel_komut is None:
            self._loiter()                  # emniyet (normalde giris N tespit garanti eder)
            return
        k = self.son_gorsel_komut
        self._send(k['thr'], k['pitch'], k['roll'], k['yaw'])   # coast: ayni hedefi tekrar gonder

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
    #  TEK kontrol adimi (donguude bir kez cagrilir) — FAZ-1 guduum
    # ----------------------------------------------------------------
    def adim(self):
        drone_pos = np.array(self.drone.get_drone_location())   # TEMIZ (cm)
        # Oyun yaw'i DERECE verir; guduum RADYAN bekler -> cevir.
        yaw_m = self.drone.get_drone_rotation()[2]
        drone_yaw = math.radians(yaw_m) if Cfg.ROT_IN_DEGREES else yaw_m
        t = time.perf_counter()

        # 1) J ile bozuk hedefi temizle (self._fresh: yeni kestirim geldi mi?)
        self._hedef_temizle()
        if self.debug_olc: self._debug_olc()

        # 2) KALKIS (non-blocking): arama irtifasina tirman, sonra yaklasmaya gec.
        if not self._kalkis_done:
            if drone_pos[2] >= Cfg.SEARCH_ALT - Cfg.ALT_TOL:
                self._kalkis_done = True
            else:
                self._send(Cfg.TAKEOFF_THR, 0.0, 0.0, 0.0)      # tirman, seviye
                return

        # 2.5) GORSEL GUDUM: gorsel temas varsa IBVS DEVRALIR ve GPS YONELIM blogu
        #      (382-436) mimari olarak KESILIR. Yarisma kurali: gorsel temas sonrasi
        #      yonelim GPS'ten DEGIL goruntuden (bbox merkezi) uretilir.
        if self.gorsel_aktif:
            self._ibvs_adim()
            return

        # 3) None yonetimi: normal donmus kare (hold) vs dropout (loiter)
        if not self._fresh:
            self.none_count += 1
            if self.none_count <= Cfg.HOLD_TICKS and self.son_temiz is not None:
                est = self.son_temiz                            # son 2sn-lead kestirimi tut
            else:
                self._loiter()                                  # uzun None -> dropout -> bekle
                return
        else:
            self.none_count = 0
            est = self.son_temiz

        if est is None:                                          # isinma: henuz kestirim yok
            self._loiter()
            return
        self.last_est = est

        # YATAY: 2sn lead'li kestirim (intercept). DIKEY: lead'siz anlik irtifa
        # (lead dikeyde irtifa asimina/yukari kacmaya yol aciyor).
        z_ref = self.son_z_anlik if self.son_z_anlik is not None else float(est[2])
        ex = float(est[0] - drone_pos[0])
        ey = float(est[1] - drone_pos[1])
        ez = float(z_ref - drone_pos[2])
        d_h = math.hypot(ex, ey)

        # 4) HANDOFF (histerezisli) -> durum: ARAMA / KILIT
        if not self.handoff and d_h < Cfg.HANDOFF_RANGE:
            self.handoff = True
        elif self.handoff and d_h > Cfg.HANDOFF_EXIT:
            self.handoff = False
            self.handoff_announced = False
        self.durum = "KILIT" if self.handoff else "ARAMA"

        # 5) turev (EMA)
        de = self._derivative((ex, ey, ez), t)

        # 6) yatay: hata ve turevi govde cercevesine cevir
        e_fwd, e_right = world_to_body(ex, ey, drone_yaw)
        de_fwd, de_right = world_to_body(de[0], de[1], drone_yaw)

        pitch_raw = Cfg.PITCH_SIGN * (Cfg.KP_H * e_fwd   + Cfg.KD_H * de_fwd)
        roll_raw  = Cfg.ROLL_SIGN  * (Cfg.KP_H * e_right + Cfg.KD_H * de_right)

        # 7) mesafe-tabanli hiz tavani -> komut buyuklugunu kisitla (overshoot guard)
        vcap = speed_cap(d_h)
        spd = self.drone.get_drone_speed()                      # skaler cm/s (yaklasik)
        if spd > vcap:                                          # tavandan hizliysa ileri itiyi fren et
            brake = clamp((spd - vcap) / max(vcap, 1.0), 0.0, 1.0)
            pitch_raw *= (1.0 - 0.8 * brake)
        mag_scale = clamp(vcap / Cfg.V_CAP_FAR, 0.15, 1.0)      # yakinda kucuk tavan

        pitch_raw = clamp(pitch_raw, -Cfg.PITCH_MAX, Cfg.PITCH_MAX) * mag_scale
        roll_raw  = clamp(roll_raw,  -Cfg.ROLL_MAX,  Cfg.ROLL_MAX)  * mag_scale

        # 8) irtifa (PD) — Z_SIGN ile dikey yon duzeltmesi (THR_DN/THR_UP duzeltilmis cercevede:
        #    nazik alcalma -0.40, daha guclu tirmanma +0.70). KP_Z/KD_Z DEGISMEZ.
        thr_raw = clamp(Cfg.Z_SIGN * (Cfg.KP_Z * ez + Cfg.KD_Z * de[2]), Cfg.THR_DN, Cfg.THR_UP)

        # 9) yaw: nazikce burnu hedefe cevir (handoff'ta kamera ortalansin)
        bearing = math.atan2(ey, ex)
        yaw_err = deadband(wrap_pi(bearing - drone_yaw), Cfg.YAW_DEADBAND)
        yaw_raw = Cfg.YAW_SIGN * clamp(Cfg.KP_YAW * yaw_err, -Cfg.YAW_MAX, Cfg.YAW_MAX)

        # 10) deadband (cok yakinda yatay jitter onle)
        if d_h < Cfg.POS_DEADBAND:
            pitch_raw = 0.0
            roll_raw = 0.0

        # --- TESHIS: irtifa kacma sorununu olcmek icin (Cfg.DEBUG_Z=False ile kapat) ---
        if Cfg.DEBUG_Z:
            self._dbgz = getattr(self, "_dbgz", 0) + 1
            if self._dbgz % 25 == 0:                         # ~2 Hz
                dbg = self.drone.get_debug_truth()
                ztrue = (dbg["target"]["position"][2] if dbg.get("available") else None)
                raw_z = (self.son_ham[2] if self.son_ham is not None else None)
                ztrue_s = f"{ztrue:8.0f}" if ztrue is not None else "    NA  "
                raw_s   = f"{raw_z:8.0f}" if raw_z is not None else "    NA  "
                corr = ",".join(self.drone.get_active_corruption()) or "-"
                print(f"[Z] dz={drone_pos[2]:8.0f} zref={z_ref:8.0f} ztrue={ztrue_s} "
                      f"zlead={float(est[2]):8.0f} rawz={raw_s} ez={ez:+7.0f} dez={de[2]:+7.0f} "
                      f"thr={thr_raw:+.2f} spd={spd:6.0f} pit={pitch_raw:+.2f} dh={d_h:7.0f} "
                      f"{self.durum} corr=[{corr}]")

        if self.handoff and not self.handoff_announced:
            print(f"[HANDOFF] tespit menzilinde (mesafe<{Cfg.HANDOFF_RANGE:.0f}cm). Gorus devralabilir.")
            self.handoff_announced = True

        self._send(thr_raw, pitch_raw, roll_raw, yaw_raw)

    # ----------------------------------------------------------------
    #  Gercek oyun ana donguusu
    # ----------------------------------------------------------------
    def calistir(self):
        if not self.drone.connect():
            print("Baglanti kurulamadi (oyun acik ve Play modunda mi?)")
            return
        self.drone.set_arm(True)
        print("FAZ 1: GNSS ile yaklasma basladi. (Filtre warm-up'inda hover eder.)")
        try:
            while True:
                self.adim()
                time.sleep(Cfg.DT)   # 50 Hz
        except KeyboardInterrupt:
            self.drone.set_control_surfaces(0.0, 0.0, 0.0, 0.0, True)   # hover ile birak
            self.drone.disconnect()

    # ----------------------------------------------------------------
    #  Debug ozet (test sonrasi)
    # ----------------------------------------------------------------
    def ozet(self):
        if not self.ham_hatalar:
            return "Debug olcum yok."
        h = np.array(self.ham_hatalar)/100; j = np.array(self.j_hatalar)/100
        s = []
        s.append(f"Ham hedef hatasi : {h.mean():.1f} m")
        s.append(f"J hedef hatasi   : {j.mean():.1f} m")
        s.append(f"J kazanci        : %{100*(h.mean()-j.mean())/h.mean():.0f}  "
                 f"({'J IYI' if j.mean()<h.mean() else 'J KOTU!'})")
        s.append(f"Aktif bozukluklar: {self.bozukluk_sayac}")
        return "\n".join(s)
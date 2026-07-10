# -*- coding: utf-8 -*-
"""AVCI DRONE ana kontrol dongusu (guduum + karar). main.py -> web.server.main()
-> AvciKontrol(drone), 50 Hz adim(). GPS fazi gps_takip + gnss_filtre'ye devreder;
AvciKontrol'un isi: FSM (ARAMA/KILIT <-> GORSEL_GUDUM), gorsel faz (basit IBVS),
kilit sayaci, ucus logu. Birim: konum cm, get_drone_rotation derece."""
import csv
import math
import os
import time
from collections import deque
import numpy as np
from guidance.gps_takip import GPSTakip                         # GPS fazi: filtre+guduum (tek sahip)
from guidance.ibvs_gorsel import AvciIBVS                       # gorsel: merkez->bbox cizgisi (basit IBVS)

# --- UCUS LOGU: dosya dizini + sabit kolon sirasi (arac/analiz_ucus.py isimle okur) ---
_HERE = os.path.dirname(os.path.abspath(__file__))          # .../guidance
_PROJ_ROOT = os.path.dirname(_HERE)                         # depo koku
_VERI_DIR = os.path.join(_PROJ_ROOT, "veri")                # calisma ciktilari (gitignore'lu)
_LOG_COLS = [
    # meta
    "t_perf", "t_wall", "phase", "kaynak", "durum", "handoff", "fresh", "none_count",
    # drone durumu (cm / derece / rad)
    "drone_x", "drone_y", "drone_z", "drone_roll", "drone_pitch", "drone_yaw_deg",
    "drone_yaw_rad", "drone_speed", "vown_x", "vown_y",
    # hedef (FILTRE): est=2sn lead, anlik=lead'siz, ham=bozuk
    "est_x", "est_y", "est_z", "z_ref", "xy_anlik_x", "xy_anlik_y", "son_z_anlik",
    "son_hiz_x", "son_hiz_y", "son_hiz_z", "son_ham_x", "son_ham_y", "son_ham_z",
    # hedef rotasyon (ANA/bozuk akis; guvenilmez)
    "tgt_roll", "tgt_pitch", "tgt_yaw",
    # hata / guduum ici
    "ex", "ey", "ez", "d_h", "e_fwd", "e_right", "vcap", "mag_scale", "alc_oncelik", "ez_int",
    # terminal vurus (strike)
    "d_s", "v_close", "vdx", "vdy", "ax", "ay", "a_fwd", "a_right",
    # yaw & FOV (nose_off_true = burun ile GERCEK hedef arasi aci, DERECE)
    "bearing", "yaw_err", "nose_off_true",
    # ham komut (rate-limit ONCESI) vs uygulanan komut (rate-limit SONRASI = self.prev)
    "thr_raw", "pitch_raw", "roll_raw", "yaw_raw", "thr_cmd", "pitch_cmd", "roll_cmd", "yaw_cmd",
    # GORSEL GUDUM (VISUAL fazi): normalize bbox-merkez hatasi + gordu/conf/alan
    "vis_ex", "vis_ey", "vis_gordu", "vis_conf", "vis_area",
    # ESKI PNG kolonlari (PN yigini silindi): sema uyumu icin durur, BOS yazilir.
    "png_R_m", "png_Vc", "png_omega",
    # vis_faz BOS (eski alt-FSM); kilit_win_s = penceredeki kumulatif kilit suresi.
    "vis_faz", "kilit_win_s",
    # HAM normalize yatay tespit konumu (pervane yanlis-poz konumlamasi; EMA'siz).
    "vis_cx",
    # basit IBVS: merkez->bbox cizgisi buyuklugu + acisi.
    "ibvs_r", "ibvs_aci",
    # ongorulu yaw lead (pose kanat uclarindan): roll + lead + kapi + ham roll.
    "ibvs_roll", "ibvs_lead", "ibvs_roll_ok", "ibvs_roll_raw",
    # bu tik olu-hesap kopru bbox'la mi calisti?
    "vis_kopru",
    # alttan-vurus teshisi: dikey nisan + alcalma freni carpani.
    "ibvs_eyref", "ibvs_alcal",
    # ego-pitch telafili dikey hata (yasa girdisi).
    "ibvs_eyego",
    # kilit-tut: EMA'li bbox eksen orani.
    "ibvs_boyut",
]


# ==========================================================
# CONFIG — faz bantlari: [ORTAK] birim/dongu/log, [FSM] gorsel-devir kapisi,
# [GORSEL] basit IBVS + kilit sayaci. GPS-yaklasma sabitleri gps_takip.GPSCfg'de.
# Canli-tune: web /api/tune, TUNE_ALLOW listesi.
# ==========================================================
class Cfg:
    # ================= [ORTAK] =================
    # --- BIRIM / FRAME / ISARET ---
    ROT_IN_DEGREES = True       # get_drone_rotation derece dondururse True
    PITCH_SIGN = +1.0           # gorsel fazda ileri hareket +pitch degilse -1

    # --- DONGU (50 Hz) ---
    LOOP_HZ = 50.0
    DT = 1.0 / LOOP_HZ

    # ================= [FSM / GORSEL DEVIR KAPISI] =================
    # GPS-yaklasma guduumunun kendisi gps_takip.py'de. Burada yalniz gorsel-devir
    # kapisi: yaklasinca durum KILIT (histerezisli), YOLO kilidiyle GORSEL_GUDUM'a gec.
    HANDOFF_RANGE = 4000.0      # cm; tespit menziline gore tune (genis tut)
    HANDOFF_EXIT  = 5000.0      # bu mesafenin disina cikinca handoff iptal
    # OTOMATIK GORSEL DEVIR: yakinlik + ard arda VIS_N_LOCK tespit -> kameraya devret.
    AUTO_VISUAL_HANDOFF = True

    # --- GORSEL FAZ KOMUT SINIRLARI (ibvs_gorsel.hesapla clamp'leri) ---
    THR_UP    = 0.70            # gorsel dikey komut tavani (tirmanis)
    THR_DN    = -1.00          # gorsel dikey komut tabani (tam inme yetkisi)
    YAW_MAX   = 0.80           # gorsel yaw tavani

    # --- HIZ LIMITI (gorsel faz _send'i; salinim onleyici) ---
    MAX_DELTA = 0.05           # gorsel komut/tik max degisim

    # ================= [ORTAK] =================

    # --- UCUS LOGU (davranis teshisi; her tik zengin CSV) ---
    LOG_ENABLE = True

    # ================= [GORSEL] (basit IBVS + kilit isteri sayaci) =================
    # --- GORSEL GUDUM — gorsel temas SONRASI yonelim (YALNIZCA kamera) ---
    # Gecis: conf>=VIS_CONF_MIN kareler ard arda VIS_N_LOCK olunca GORSEL_GUDUM'a gec.
    # Kayipta (OTO): VIS_LOST_TO_GPS_S kadar hover, sonra GPS'e don (0 = ANINDA don).
    VIS_MODEL_PATH   = os.path.join(_PROJ_ROOT, "models", "best.pt")   # tespit modeli (detect)
    VIS_POSE_MODEL_PATH = os.path.join(_PROJ_ROOT, "models", "talon_pose.pt")  # poz modeli (pose)
    # PERVANE/HUD MASKESI: normalize [x0,y0,x1,y1] dikdortgenler; merkezi maskede olan
    # kutular dedektorde ELENIR (argmax oncesi). Bos liste = kapali.
    PROP_MASKE = []   # KAPALI: yanlis-poz riski artik tracker onayi ile emilir.
                      # Geri istersen: [(0.80,0.55,1.0,0.95),(0.31,0.49,0.70,0.65)].
    VIS_CONF_MIN     = 0.15     # kilit/komut icin asgari guven (cok yanlis tespitte yukselt)
    # --- SAHI (Slicing Aided Hyper Inference) — uzak/kucuk hedef recall ---
    # Kareyi ortusen dilimlere bol, her dilimde best.pt kosur, kutulari NMS ile birlestir
    # -> uzak hedef dedektor korlugu azalir. Yalniz detect; kendi impl (gorsel_tespit).
    SAHI_AKTIF       = True     # False -> tek tam-kare predict (eski davranis)
    SAHI_DILIM_PX    = 640      # dilim kenari (px)
    SAHI_ORTUSME     = 0.2      # komsu dilim ortusme orani
    SAHI_TAM_KARE    = True     # dilimlere EK tam-kare predict
    SAHI_NMS_IOU     = 0.5      # dilim+tam-kare kutu birlestirme IoU esigi
    SAHI_KOSUL_CONF  = 0.5      # tam-karede conf>=bu kutu VARSA dilimleme atla (0=her kare)
    VIS_N_LOCK       = 5        # ardisik gecerli-tespit -> GORSEL_GUDUM (yanlis-poz bastir)
    VIS_STALE_S      = 0.5      # tespit bu sureden eskiyse yok say (kayip mantigi)
    VIS_LOST_TO_GPS_S = 0.0     # kayipta GPS'e donmeden hover suresi (yalniz OTO; 0=aninda don)
    VIS_EMA          = 0.4      # ex/ey EMA yumusatma (tek-kare yanlis tespiti bastir)
    # --- TAKIP (ByteTrack) ANAHTARI ---
    TAKIP_AKTIF      = True     # False -> tracker kapali, ham argmax tespit dogrudan beyne
    # --- gyro-CMC (jiroskop hareket telafisi) ---
    # Avcinin kendi donusunun bbox'a etkisini IMU attitude homografisiyle onceden telafi
    # eder (girdi = kendi attitude = ego-motion -> GPS yasagina uygun).
    TAKIP_CMC_AKTIF  = False    # canli kotulestirdi -> kapali (sim attitude isareti supheli)
    TAKIP_CMC_SIGN   = +1.0     # warp ters yonde kaydiriyorsa -1 yap
    TAKIP_CMC_MAX_KAYDIRMA = 0.25  # tek tikte CMC max kaydirma (kare-genisligi orani); 0=kapali
    # --- GORUNTU-DUZLEMI KOPRU / OLU-HESAP ---
    # Dedektor deligi acilinca bbox son olculen goruntu-hiziyla VIS_KOPRU_S boyunca ileri
    # tasinir; IBVS onu izler. Kopru tespiti KILIT SAYACINA SAYILMAZ (durustluk).
    VIS_KOPRU_S      = 1.2      # kopru suresi (s); 0 = kapali ⚙
    VIS_KOPRU_V_EMA  = 0.5      # goruntu-hizi EMA katsayisi
    # --- BASIT IBVS: goruntu merkezi -> bbox merkezi cizgisi ---
    # TEK gorsel yasa (ibvs_gorsel.py): cizginin yatay bileseni yaw'a, dikey bileseni
    # throttle'a; buyuklugu ileri itkiyi kisar (once ortala, sonra ilerle). Roll hep 0.
    # Kamera +25 tilt -> hedefi merkezde tutmak araci hedefin altinda tutar (alttan yaklasma).
    IBVS_K_YAW       = 1.2       # yatay kazanc: yaw = SIGN*K*ex (clamp +-YAW_MAX) ⚙
    IBVS_SIGN_YAW    = +1.0     # ex>0 (hedef sagda) -> burnu saga; ters tepki gorursen -1
    IBVS_K_DIKEY     = 2.15      # dikey kazanc: thr = SIGN*K*(-ey) (clamp THR_DN..THR_UP) ⚙
    IBVS_SIGN_DIKEY  = +1.0     # hedef yukarida (ey<0) -> tirman; ters tepki gorursen -1
    # --- YAKINLIK-OLCEKLI KAZANC ---
    # Yaklastikca hedefin goruntudeki acisal hizi artar; sabit kazanc geride kalir. yaw+dikey
    # kazanci bbox boyutuyla olceklenir: k_yakin = 1 + YAKIN_KAZANC*clamp(boyut_f/BOYUT_HEDEF,0,2).
    IBVS_YAKIN_KAZANC = 1.0     # yakinlik kazanc artisi (0=kapali; stand-off 2x, yakin 3x) ⚙
    IBVS_ILERI       = 0.75     # ileri itki TAVANI (0..1; boyut yasasi bunu asamaz) ⚙
    # --- KILIT-TUT / BOYUT REGULASYONU (sartname 6.1.2/6.1.4) ---
    # VURUS degil MESAFE TUTMA: bbox eksen orani (max(w/W,h/H)) HEDEF'e P-yasayla surulur:
    #   ileri = clamp(K_BOYUT*(BOYUT_HEDEF - boyut_f), -GERI_MAX, IBVS_ILERI)
    # Uzakta tavan hiziyla yaklas, hedef boyutta stand-off tut, fazla yakinsa geri kacis.
    # K_BOYUT=0 -> regulasyon kapali (eski sabit-ileri yasa). Girdi yalniz bbox pikselleri.
    IBVS_BOYUT_HEDEF = 0.08     # bbox eksen orani hedefi (>= VIS_LOCK_PCT + marj) ⚙
    IBVS_K_BOYUT     = 20.0     # boyut hatasi -> ileri itki kazanci (0=kapali/eski yasa) ⚙
    IBVS_GERI_MAX    = 0.30     # fazla yakinken geri itki tavani (0=asla geri gitme) ⚙
    # --- KAPANMA-HIZI FRENI (TTC / looming) ---
    # bbox hizli buyuyorsa (carpacak) ileri itkiyi onceden kis: ileri -= FREN_HIZ*max(0,dboyut/dt).
    IBVS_FREN_HIZ    = 8.0      # kapanma-hizi -> ileri fren kazanci ⚙ (0=kapali)
    IBVS_MERKEZ_FREN = 1.1       # sapma buyudukce ileri kis: pitch *= max(0, 1-FREN*r) ⚙
                                # (0 = hep tam gaz; buyuk deger = once ortala sonra ilerle)
    # --- DIKEY NISAN (tilt-farkinda; hiz vektorunu hedefe kilitle) ---
    # Kamera +TILT yukari sabit; ey_ref = NISAN * tan(TILT)/tan(VFOV_yari) (tilt'ten turetilir).
    IBVS_TILT_DEG      = 25.0   # kamera yukari tilt (dogrulandi)
    IBVS_VFOV_HALF_DEG = 47.2   # dikey FOV yari acisi
    IBVS_DIKEY_NISAN   = -0.25  # negatif = hedefi merkez ustunde tut (alttan vurus); 0=merkez;
                                # 1 = hiz vektorunu hedefe nisanla (terminal carpisma) ⚙
    # --- YUMUSAK GECIS / SOFT-HANDOFF (GPS->gorsel gecis surekliligi) ---
    # Gorsel faz basindan bu sure boyunca ileri-itki ve dikey-nisan 0'dan rampalanir
    # (yaw/dikey-ortalama ilk tikten tam) -> gecis aninda hedef kadrajda kalir. 0=kapali.
    IBVS_HANDOFF_S     = 1.0    # gorsel faz basi yumusak-gecis rampasi (s); 0 = kapali ⚙
    # --- ALCALMA FRENI (gorsel anti-lift-carry) ---
    # Hedef nisanin altindaysa (eyy>0 = cok yuksekteyiz) ileri itki carpimsal kisilir:
    #   pitch *= clamp(1 - ALCAL_FREN*max(0,eyy), ALCAL_TABAN, 1). Tirmanis (eyy<0) etkilenmez.
    IBVS_ALCAL_FREN  = 1.5      # 0=kapali; buyudukce ileri itki daha cok frenlenir ⚙
    IBVS_ALCAL_TABAN = 0.2      # fren tabani (asla tam durma); slider DISI.
    # --- EGO-PITCH TELAFISI (kacak-tirmanma) ---
    # Ileri itki govdeyi yatirinca kamera duser, hedef goruntude sahte yukari ziplar. Dikey
    # hata kendi pitch'ten arindirilir: ey_dunya = ey_f - GAIN*tan(own_pitch)/tan(VFOV_yari).
    IBVS_EGO_PITCH_GAIN = 0.4   # ego-pitch telafi kazanci (0=kapali)
    # ONGORULU YAW LEAD (pose) kaldirildi: pose kapali, ibvs_gorsel._roll_lead no-op (lead=0).

    # --- KILITLENME ISTERI SAYACI (sartname 6.1.2 + 6.1.4) — SALT GOZLEM ---
    # Gudume karismaz; arayuz/video kaniti icin sayilir (kirmizi dortgen + 5/10 sn pencere).
    # Kilit (her tik): hedef merkezi AV icinde VE bbox en az bir eksende >= VIS_LOCK_PCT.
    VIS_LOCK_PCT     = 0.06     # bbox eksen orani esigi (sartname >=0.05; marjli 0.06)
    VIS_AV_X         = 0.25     # AV yatay kenar payi (%25-%75 bandi)
    VIS_AV_Y         = 0.10     # AV dikey kenar payi (%10-%90 bandi)
    VIS_WIN_S        = 10.0     # degerlendirme penceresi (sartname sabiti)
    VIS_WIN_NEED_S   = 5.0      # pencerede gereken kumulatif kilit (sartname sabiti)


# ==========================================================
# HELPERS
# ==========================================================
def wrap_pi(a):
    return (a + math.pi) % (2.0 * math.pi) - math.pi

def clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x

def rate_limit(target, prev, max_delta):
    return prev + clamp(target - prev, -max_delta, max_delta)


# GPS-takip fabrikasi: tek uretim yolu (fusion/gnss_filtre + guidance/gps_takip).
# NOT: truth-tabanli "gercek GPS" test modu yarisma teslimi icin KALDIRILDI;
# guduum artik HER ZAMAN uretim (filtre) yolunu kullanir.
def _gps_uret(drone, kaynak):
    return GPSTakip(drone)


class AvciKontrol:
    def __init__(self, drone, debug_olc=True, kaynak="filtre"):
        self.drone = drone
        if kaynak not in ("filtre", "v2"):  # truth/"gercek" test modu kaldirildi -> hep filtre
            kaynak = "filtre"
        if kaynak == "v2":                  # eski ad (geriye-uyum)
            kaynak = "filtre"
        self.kaynak = kaynak                # her zaman "filtre" (telemetri alani korunur)
        self.gps = _gps_uret(drone, kaynak)  # GPS fazinin tek sahibi (kalkis+filtre+PD/PID)
        self.durum = "ARAMA"                # ARAMA -> KILIT -> GORSEL_GUDUM
        self.handoff = False

        # kendi yatay hiz vektoru (konum sonlu-fark, EMA) — yalniz log/teshis
        self._own_pxy = None
        self._own_tv = None
        self._own_v = np.zeros(2)

        # debug olcum birikimi (filtre ciktisinin gercege hatasi; sim/teshis)
        self.debug_olc = debug_olc
        self.ham_hatalar = []
        self.filtre_hatalar = []
        self.bozukluk_sayac = {}

        # ucus logu (lazy-open, zaman-damgali dosya)
        self._log_f = None
        self._log_w = None

        # --- GORSEL GUDUM (basit IBVS) durumu ---
        self.son_tespit = None          # {cx,cy,w,h,conf,W,H,t} | None (server yazar)
        self.son_tespit_t = None        # tespit perf_counter zamani (bayatlik kontrolu)
        self.son_poz = None             # normalize poz dict | None (pose kapali; arayuz uyumu)
        self.son_poz_t = None
        self._vis_pos_count = 0         # ardisik gecerli-tespit (kilit histerezisi)
        self._vis_lost_count = 0        # ardisik kayip (hover -> GPS'e donus)
        self._vis_ilan = False          # anons bir kez basilsin
        self._vis_v = None              # goruntu-hizi (px/s; son iki tespitten, EMA'li)
        self.vis_kopru = False          # bu tik kopru (olu-hesap) tespitiyle mi?
        self.ibvs = AvciIBVS()          # tek gorsel yasa (basit IBVS)
        self.ibvs_tlm = {}              # son IBVS telemetrisi
        self.vis_mode = "OTO"           # pipeline switch: OTO | GPS | GORSEL
        # --- KILITLENME ISTERI SAYACI (SALT GOZLEM, komuta girmez) ---
        self.kilit_win = deque()        # (t, kilit_anlik) — son VIS_WIN_S penceresi
        self.kilit_sure = 0.0           # penceredeki kumulatif kilit suresi (s)
        self.kilit_anlik = False        # bu tik kilit kosulu
        self.kilit_ok = False           # LATCH: pencere isteri saglandi
        self.kilit_boyut = None         # bu tik bbox eksen orani (telemetri)

    # ---- GPS durum PROXY'leri: tek dogruluk kaynagi gps_takip ----
    @property
    def son_ham(self): return self.gps.son_ham
    @property
    def son_temiz(self): return self.gps.son_temiz
    @property
    def son_z_anlik(self): return self.gps.son_z_anlik
    @property
    def son_xy_anlik(self): return self.gps.son_xy_anlik
    @property
    def son_hiz(self): return self.gps.son_hiz
    @property
    def _fresh(self): return self.gps._fresh
    # Uygulanan son komut da gps_takip'te yasar -> GPS<->GORSEL gecislerinde rate-limit surer.
    @property
    def prev(self): return self.gps.prev
    @prev.setter
    def prev(self, v): self.gps.prev = dict(v)

    # ----------------------------------------------------------------
    #  Guduum kaynagini canli degistir (Filtre/Gercek). Yeni GPSTakip + FSM/gorsel
    #  durum taze baslar.
    # ----------------------------------------------------------------
    def set_kaynak(self, kaynak):
        if kaynak not in ("filtre", "v2"):  # truth/"gercek" test modu kaldirildi -> hep filtre
            kaynak = "filtre"
        if kaynak == "v2":
            kaynak = "filtre"               # eski ad (geriye-uyum)
        if kaynak == self.kaynak and self.gps is not None:
            return                          # zaten o kaynak -> dokunma
        self.kaynak = kaynak
        self.gps = _gps_uret(self.drone, kaynak)
        self.durum = "ARAMA"
        self.handoff = False
        self._own_pxy = None
        self._own_tv = None
        self._own_v = np.zeros(2)
        # GORSEL GUDUM: yeni gorev -> gorsel kilit/kopru durumunu da taze basla
        self.son_tespit = None
        self.son_tespit_t = None
        self.son_poz = None
        self.son_poz_t = None
        self._vis_pos_count = 0
        self._vis_lost_count = 0
        self._vis_ilan = False
        self._vis_v = None
        self.vis_kopru = False
        self.ibvs.sifirla()
        self.ibvs_tlm = {}
        # kilitlenme isteri sayaci: yeni gorev -> pencere ve latch dahil taze basla
        self.kilit_win.clear()
        self.kilit_sure = 0.0
        self.kilit_anlik = False
        self.kilit_ok = False
        self.kilit_boyut = None
        self.log_dondur()   # yeni gorev -> yeni log dosyasi (sonraki tik acar)

    # ----------------------------------------------------------------
    #  Ucus logunu dondur: acik dosyayi kapat; sonraki tik taze dosya acar.
    #  Server her "Gorev Baslat"ta cagirir -> her gorev kendi log dosyasini alir.
    # ----------------------------------------------------------------
    def log_dondur(self):
        if self._log_f is not None:
            try: self._log_f.close()
            except Exception: pass
            self._log_f = self._log_w = None

    # Hedef GNSS isleme -> gps_takip'e devredilir (server pasif modda da cagirir).
    def _hedef_temizle(self):
        return self.gps._hedef_temizle()

    # Kendi yatay hiz vektoru (cm/s): konum sonlu-fark + EMA. Yalniz log/teshis.
    def _own_hiz(self, pxy, t):
        if self._own_pxy is None or self._own_tv is None:
            self._own_pxy = pxy.copy(); self._own_tv = t
            return self._own_v
        dt = t - self._own_tv
        if 1e-3 < dt < 0.5:
            raw = (pxy - self._own_pxy) / dt
            self._own_v = 0.7 * self._own_v + 0.3 * raw
            self._own_pxy = pxy.copy(); self._own_tv = t
        elif dt >= 0.5:                                # bayat -> resetle
            self._own_pxy = pxy.copy(); self._own_tv = t
        return self._own_v

    # Komut gonder (rate-limit + atomik set_control_surfaces).
    def _send(self, thr, pitch, roll, yaw):
        thr   = rate_limit(thr,   self.prev['thr'],   Cfg.MAX_DELTA)
        pitch = rate_limit(pitch, self.prev['pitch'], Cfg.MAX_DELTA)
        roll  = rate_limit(roll,  self.prev['roll'],  Cfg.MAX_DELTA)
        yaw   = rate_limit(yaw,   self.prev['yaw'],   Cfg.MAX_DELTA)
        self.prev = {'thr': thr, 'pitch': pitch, 'roll': roll, 'yaw': yaw}
        self.drone.set_control_surfaces(thr, pitch, roll, yaw, True)

    # ----------------------------------------------------------------
    #  Ucus logu: her tik zengin teshis satiri (lazy-open, zaman-damgali dosya).
    #  Truth + rotasyonlar + nose_off_true burada hesaplanir. d: cagri yeri alanlari.
    # ----------------------------------------------------------------
    def _log(self, phase, d):
        if not Cfg.LOG_ENABLE:
            return
        if self._log_f is None:                                  # ilk yazim -> dosya ac
            os.makedirs(_VERI_DIR, exist_ok=True)
            fn = time.strftime("ucus_log_%Y%m%d_%H%M%S.csv")
            self._log_f = open(os.path.join(_VERI_DIR, fn), "w", newline="", encoding="utf-8")
            self._log_w = csv.writer(self._log_f)
            self._log_w.writerow(_LOG_COLS)
            self._log_f.flush()
        # --- truth + rotasyonlar (guvenli; hata olursa alan bos kalir) ---
        try:
            rot = self.drone.get_drone_rotation()
            d["drone_roll"], d["drone_pitch"] = float(rot[0]), float(rot[1])
        except Exception:
            pass
        try:
            trot = self.drone.get_target_rotation()             # ana (bozuk) akis - guvenilmez
            d["tgt_roll"], d["tgt_pitch"], d["tgt_yaw"] = float(trot[0]), float(trot[1]), float(trot[2])
        except Exception:
            pass
        d["phase"] = phase
        d["t_wall"] = time.time()

        def _c(x):
            if x is None:
                return ""
            if isinstance(x, (float, np.floating)):
                return round(float(x), 4)
            return x
        self._log_w.writerow([_c(d.get(k)) for k in _LOG_COLS])
        self._log_f.flush()

    # ----------------------------------------------------------------
    #  Guduum pipeline switch (test): "OTO" otomatik kilit/revert; "GPS" zorla GPS;
    #  "GORSEL" zorla gorsel (kilidi atla, kayipta GPS'e donme).
    # ----------------------------------------------------------------
    def set_vis_mode(self, mode):
        m = str(mode).upper()
        if m not in ("OTO", "GPS", "GORSEL"):
            return False
        self.vis_mode = m
        self._vis_pos_count = 0          # switch -> gorsel durum temiz baslasin
        self._vis_lost_count = 0
        self._vis_ilan = False
        self._vis_v = None
        self.vis_kopru = False
        self.ibvs.sifirla()
        # switch = yeni deneme -> kilit penceresi/latch taze baslasin
        self.kilit_win.clear()
        self.kilit_sure = 0.0
        self.kilit_anlik = False
        self.kilit_ok = False
        self.kilit_boyut = None
        return True

    def set_gorsel_tespit(self, det):
        if det is not None:
            t_det = det.get("t", time.perf_counter())
            # goruntu-hizi (px/s, EMA'li): son iki tespitten; kopru bunu kullanir.
            # Uzun aradan sonra hiz bayat sayilir ve sifirlanir.
            if self.son_tespit is not None and self.son_tespit_t is not None:
                dt = t_det - self.son_tespit_t
                if 0.0 < dt <= Cfg.VIS_STALE_S:
                    vx = (float(det["cx"]) - float(self.son_tespit["cx"])) / dt
                    vy = (float(det["cy"]) - float(self.son_tespit["cy"])) / dt
                    W = float(det.get("W", 0) or 0)
                    if W > 1:                       # tavan: sacma tek-kare sicramasini keser
                        vmax = 0.8 * W
                        vx = max(-vmax, min(vmax, vx))
                        vy = max(-vmax, min(vmax, vy))
                    if self._vis_v is None:
                        self._vis_v = (vx, vy)
                    else:
                        a = float(Cfg.VIS_KOPRU_V_EMA)
                        self._vis_v = (a * vx + (1 - a) * self._vis_v[0],
                                       a * vy + (1 - a) * self._vis_v[1])
                elif dt > Cfg.VIS_STALE_S:
                    self._vis_v = None
            self.son_tespit = det
            self.son_tespit_t = t_det
        # det None ise eski tespiti silme (tek bos kare kilidi dusurmesin); bayatlik _oku'da elenir.

    def set_gorsel_poz(self, poz):
        """Pose dedektor normalize ciktisini beyne yaz (gorsel veri, ongorulu yaw lead
        girdisi). None ise eskisini silme (bayatlik _gorsel_guduum'da elenir)."""
        if poz is not None:
            self.son_poz = poz
            self.son_poz_t = time.perf_counter()

    def _gorsel_tespit_oku(self):
        """Bayat-olmayan son tespiti dondur. Bayatsa (yalniz GORSEL_GUDUM'da) kopruyu
        dene: bbox son olculen hizla ileri tasinir (kopru=True). Bittiyse None."""
        self.vis_kopru = False
        det = self.son_tespit
        if det is None or self.son_tespit_t is None:
            return None
        yas = time.perf_counter() - self.son_tespit_t
        if yas <= Cfg.VIS_STALE_S:
            return det
        # --- KOPRU (olu-hesap): sabit goruntu-hizi varsayimiyla sanal bbox ---
        kopru_s = float(getattr(Cfg, "VIS_KOPRU_S", 0.0))
        if (kopru_s > 0.0 and self._vis_v is not None
                and self.durum == "GORSEL_GUDUM"          # yalniz gorsel fazda
                and yas <= Cfg.VIS_STALE_S + kopru_s):
            W = float(det.get("W", 0) or 0); H = float(det.get("H", 0) or 0)
            if W > 1 and H > 1:
                d2 = dict(det)
                d2["cx"] = min(max(float(det["cx"]) + self._vis_v[0] * yas, 0.0), W)
                # dikey ekstrapole EDILMEZ (kacak-tirmanma dersi): cy donar, dikey komut 0.
                d2["kopru"] = True                        # kilit sayaci + log bunu ayirt eder
                self.vis_kopru = True
                return d2
        return None

    # GORSEL_GUDUM logu (phase="VISUAL"): meta+drone+komut + vis_* kolonlari.
    def _log_gorsel(self, t, drone_pos, yaw_m, drone_yaw, v_own, tespit):
        if not Cfg.LOG_ENABLE:
            return
        d = {
            "t_perf": t, "kaynak": self.kaynak, "durum": self.durum,
            "drone_x": drone_pos[0], "drone_y": drone_pos[1], "drone_z": drone_pos[2],
            "drone_yaw_deg": yaw_m, "drone_yaw_rad": drone_yaw,
            "vown_x": v_own[0], "vown_y": v_own[1],
            "thr_cmd": self.prev['thr'], "pitch_cmd": self.prev['pitch'],
            "roll_cmd": self.prev['roll'], "yaw_cmd": self.prev['yaw'],
            "drone_pos": drone_pos, "drone_yaw": drone_yaw,
            # vis_ex: IBVS EMA'li yatay hata; vis_ey: ham normalize dikey hata.
            "vis_ex": self.ibvs.ex_f,
            "vis_ey": (((float(tespit["cy"]) - float(tespit["H"]) / 2.0)
                        / (float(tespit["H"]) / 2.0))
                       if (tespit is not None and float(tespit.get("H", 0) or 0) > 1) else None),
            # vis_gordu: yalniz gercek tespit (kopru haric); vis_kopru: kopru tiki mi.
            "vis_gordu": 1 if (tespit is not None and not tespit.get("kopru")) else 0,
            "vis_kopru": 1 if (tespit is not None and tespit.get("kopru")) else 0,
            "kilit_win_s": self.kilit_sure,
            # ham normalize yatay konum (pervane konumlamasi)
            "vis_cx": (((float(tespit["cx"]) - float(tespit["W"]) / 2.0)
                        / (float(tespit["W"]) / 2.0))
                       if (tespit is not None and float(tespit.get("W", 0) or 0) > 1) else None),
        }
        if tespit is not None:
            d["vis_conf"] = float(tespit.get("conf", 0.0))
            W = float(tespit.get("W", 0) or 0); H = float(tespit.get("H", 0) or 0)
            if W > 1 and H > 1:
                d["vis_area"] = (float(tespit["w"]) * float(tespit["h"])) / (W * H)
        it = self.ibvs_tlm or {}
        if it:
            # merkez->bbox cizgisi: buyukluk + aci
            d["ibvs_r"] = it.get("buyukluk"); d["ibvs_aci"] = it.get("aci_deg")
            # ongorulu yaw lead + kapi (roll_ok=1 -> roll taze, lead uygulandi)
            d["ibvs_roll"] = it.get("roll_deg"); d["ibvs_lead"] = it.get("lead")
            d["ibvs_roll_ok"] = 1 if it.get("roll_ok") else 0
            d["ibvs_roll_raw"] = it.get("roll_raw_deg")   # ham goruntu-roll
            # alttan-vurus teshisi: dikey nisan + alcalma freni carpani
            d["ibvs_eyref"] = it.get("ey_ref"); d["ibvs_alcal"] = it.get("alcal")
            d["ibvs_eyego"] = it.get("ey_ego")    # ego-pitch telafili dikey (yasa girdisi)
            d["ibvs_boyut"] = it.get("boyut")     # kilit-tut: EMA'li bbox eksen orani
        self._log("VISUAL", d)

    # ----------------------------------------------------------------
    #  Kilitlenme penceresi (sartname 6.1.4): her gorsel tikte kilit kosulunu
    #  degerlendir + kayan penceredeki kumulatif kilit suresini guncelle. Kilit:
    #  hedef merkezi AV icinde VE bbox en az bir eksende >= VIS_LOCK_PCT. Kesintili
    #  kilit sayilir; VIS_WIN_NEED_S dolunca kilit_ok latch. SALT GOZLEM.
    # ----------------------------------------------------------------
    def _kilit_degerlendir(self, tespit, t):
        kilit = False
        self.kilit_boyut = None                      # bu tik bbox eksen orani (telemetri)
        if tespit is not None:
            W = float(tespit.get("W", 0) or 0); H = float(tespit.get("H", 0) or 0)
            if W > 1 and H > 1:
                cxn = float(tespit["cx"]) / W
                cyn = float(tespit["cy"]) / H
                boyut = max(float(tespit["w"]) / W, float(tespit["h"]) / H)
                self.kilit_boyut = boyut
                av_x = float(Cfg.VIS_AV_X); av_y = float(Cfg.VIS_AV_Y)
                kilit = (av_x <= cxn <= 1.0 - av_x
                         and av_y <= cyn <= 1.0 - av_y
                         and boyut >= float(Cfg.VIS_LOCK_PCT))
        self.kilit_anlik = kilit
        win = self.kilit_win
        win.append((t, kilit))
        while win and (t - win[0][0]) > float(Cfg.VIS_WIN_S):
            win.popleft()
        # kumulatif sure: onceki ornek kilitliyse iki ornek arasi dt sayilir (0.5 sn ustu bosluk sayilmaz)
        sure = 0.0
        for i in range(1, len(win)):
            dt = win[i][0] - win[i - 1][0]
            if win[i - 1][1] and 0.0 < dt < 0.5:
                sure += dt
        self.kilit_sure = sure
        if (not self.kilit_ok) and sure >= float(Cfg.VIS_WIN_NEED_S):
            self.kilit_ok = True                     # kalici latch (gorev boyunca)
            print("[KILIT] %.0f sn pencerede %.1f sn kumulatif kilit -> KILIT ISTERI SAGLANDI "
                  "(sartname 6.1.4: >= %.0f sn)." % (Cfg.VIS_WIN_S, sure, Cfg.VIS_WIN_NEED_S))
        return kilit

    # ----------------------------------------------------------------
    #  GORSEL GUDUM (basit IBVS) — yonelim yalnizca kameradan (GPS/filtre kullanilmaz;
    #  ibvs_gorsel.hesapla'ya sadece bbox pikselleri girer, kural yapisal saglanir).
    #  tespit VAR -> ibvs.hesapla; YOK -> hover, VIS_LOST_TO_GPS_S asilirsa (OTO) GPS'e
    #  don (None dondur). return: (thr,pitch,roll,yaw) | None. _send rate-limit'ler.
    # ----------------------------------------------------------------
    def _gorsel_guduum(self, tespit, t, revert_izin=True, own_roll_rad=None,
                       own_pitch_rad=None):
        # revert_izin=False (manuel GORSEL): kayipta GPS'e donme, hover'da kal.
        # own_roll/pitch_rad: kendi IMU (ego-motion telafisi; hedef verisi degil).
        # KILIT SAYACI: salt gozlem; kopru tiki sayaca girmez (tespitsiz gibi islenir).
        kopru = bool(tespit is not None and tespit.get("kopru"))
        self._kilit_degerlendir(None if kopru else tespit, t)
        # KURAL: gorsel temastan sonra komut yalniz gorsel veriden; IBVS yalniz bbox okur.
        if tespit is not None:
            self._vis_lost_count = 0
            # taze poz (bayat degilse yaw lead'i besler; yoksa None -> saf IBVS)
            poz = self.son_poz
            if poz is None or self.son_poz_t is None or \
                    (time.perf_counter() - self.son_poz_t) > float(getattr(Cfg, "IBVS_POZ_STALE_S", 0.6)):
                poz = None
            komut = self.ibvs.hesapla(tespit, Cfg, poz=poz, own_roll_rad=own_roll_rad,
                                      own_pitch_rad=own_pitch_rad)
            self.ibvs_tlm = self.ibvs.durum()
            # koprude dikey-tut (kopru bbox tahmindir): thr=0 (irtifa-tut), yatay takip surer.
            if kopru:
                komut = (0.0, komut[1], komut[2], komut[3])
                self.ibvs_tlm["dikey"] = 0.0          # telemetri uygulanani gostersin
            return komut
        # --- KAYIP: (OTO) VIS_LOST_TO_GPS_S kadar hover, sonra GPS'e don (0=aninda).
        #     Manuel GORSEL'de hep hover. ---
        self._vis_lost_count += 1
        lost_s = self._vis_lost_count * Cfg.DT
        if (not revert_izin) or lost_s <= float(Cfg.VIS_LOST_TO_GPS_S):
            return 0.0, 0.0, 0.0, 0.0            # hover
        # uzun kayip (yalniz OTO) -> GPS guduumune don (yeniden yaklas/kilitle)
        self.durum = "ARAMA"
        self._vis_pos_count = 0
        self._vis_lost_count = 0
        self._vis_ilan = False
        self.ibvs.sifirla()
        # kilit penceresi temizlenir; kilit_ok LATCH korunur (gecmiste saglandiysa gecerli).
        self.kilit_win.clear()
        self.kilit_sure = 0.0
        self.kilit_anlik = False
        return None                              # -> adim() GPS yoluna duser (bu tik)

    # ----------------------------------------------------------------
    #  Tek kontrol adimi (50 Hz). GPS fazi gps_takip'e devredilmistir. Bu metodun isi:
    #    1) gorsel tespit + FSM anahtari (ARAMA/KILIT <-> GORSEL_GUDUM),
    #    2) GORSEL fazda basit IBVS komutu (yalnizca kameradan),
    #    3) GPS fazinda gps.adim() + handoff mesafesi + ucus logu.
    # ----------------------------------------------------------------
    def adim(self):
        drone_pos = np.array(self.drone.get_drone_location())   # temiz (cm)
        rot_rpy = self.drone.get_drone_rotation()               # (roll,pitch,yaw) derece
        yaw_m = rot_rpy[2]
        drone_yaw = math.radians(yaw_m) if Cfg.ROT_IN_DEGREES else yaw_m
        t = time.perf_counter()
        v_own = self._own_hiz(drone_pos[:2], t)                 # yalniz log/teshis

        # 1) Pipeline secimi (vis_mode): OTO otomatik kilit/revert; GPS zorla GPS;
        #    GORSEL zorla gorsel. GORSEL kilitliyken GPS yolu calismaz. prev tek kaynak.
        tespit = self._gorsel_tespit_oku()
        mod = getattr(self, "vis_mode", "OTO")
        if mod == "GPS":
            if self.durum == "GORSEL_GUDUM":              # manuel: gorselden GPS'e don
                self.durum = "ARAMA"; self._vis_ilan = False
            self._vis_pos_count = 0
        elif mod == "GORSEL":
            if self.durum != "GORSEL_GUDUM":              # manuel: hemen gorsel (kilit sayaci yok)
                self.durum = "GORSEL_GUDUM"; self._vis_lost_count = 0
                if not self._vis_ilan:
                    print("[GORSEL] Manuel switch -> GORSEL GUDUM (GPS yonelimi kapali).")
                    self._vis_ilan = True
        else:  # OTO — otomatik kilit: yakinlik + YOLO kilidi (ikisi birden)
            if self.durum != "GORSEL_GUDUM":
                if tespit is not None and float(tespit.get("conf", 0.0)) >= Cfg.VIS_CONF_MIN:
                    self._vis_pos_count += 1
                else:
                    self._vis_pos_count = 0
                # HANDOFF: GPS yeterince yaklasmis (self.handoff) VE ard arda VIS_N_LOCK
                # tespit -> saldiri kameraya devredilir; oncesinde GPS yaklasmaya devam eder.
                if (Cfg.AUTO_VISUAL_HANDOFF
                        and self._vis_pos_count >= Cfg.VIS_N_LOCK and self.handoff):
                    self.durum = "GORSEL_GUDUM"
                    # yumusak gecis: gorsel yasayi taze basla (EMA + soft-handoff rampasi)
                    self.ibvs.sifirla()
                    if not self._vis_ilan:
                        self._vis_ilan = True

        if self.durum == "GORSEL_GUDUM":
            # kendi roll+pitch'imiz (IMU) -> ego-motion telafileri (hedef verisi degil)
            own_roll_rad = (math.radians(float(rot_rpy[0])) if Cfg.ROT_IN_DEGREES
                            else float(rot_rpy[0]))
            own_pitch_rad = (math.radians(float(rot_rpy[1])) if Cfg.ROT_IN_DEGREES
                             else float(rot_rpy[1]))
            sonuc = self._gorsel_guduum(tespit, t, revert_izin=(mod == "OTO"),
                                        own_roll_rad=own_roll_rad,
                                        own_pitch_rad=own_pitch_rad)
            if sonuc is not None:
                thr, pitch, roll, yaw = sonuc
                self._send(thr, pitch, roll, yaw)
                # GNSS filtresini SICAK tut: gorselde de paketler islenir (DR sayaci sahte
                # kesinti gormez). Cikti gorsel fazda komuta GIRMEZ (IBVS yalniz bbox okur).
                self.gps._hedef_temizle()
                if self.gps._fresh:
                    self.gps._son_fresh_t = t
                self._log_gorsel(t, drone_pos, yaw_m, drone_yaw, v_own, tespit)
                return
            # sonuc None (yalniz OTO) -> gorsel uzun kayip -> GPS yolu bu tik calisir

        # ==================== [GPS-YAKLASMA — gps_takip devraldi] ====================
        # Kalkis + GNSS temizleme + DR + PD/PID + rate-limit + gonderim gps.adim() icinde.
        self.gps.adim()

        # HANDOFF (histerezisli) -> durum: ARAMA / KILIT (gorsel devir kapisi).
        d_h = None
        ex_l = ey_l = None
        sxy = self.gps.son_xy_anlik
        if sxy is not None:
            ex_l = float(sxy[0]) - float(drone_pos[0])
            ey_l = float(sxy[1]) - float(drone_pos[1])
            d_h = math.hypot(ex_l, ey_l)
            if not self.handoff and d_h < Cfg.HANDOFF_RANGE:
                self.handoff = True
            elif self.handoff and d_h > Cfg.HANDOFF_EXIT:
                self.handoff = False
        self.durum = "KILIT" if self.handoff else "ARAMA"

        # --- UCUS LOGU: GPS fazi (faz etiketi kalkis/isinma/yaklasma) ---
        if Cfg.LOG_ENABLE:
            faz = ("TAKEOFF" if not self.gps._kalkis_done
                   else ("WARMUP" if self.gps.son_temiz is None else "APPROACH"))
            est = self.gps.son_temiz
            sh = self.gps.son_hiz
            sm = self.gps.son_ham
            try:
                spd = self.drone.get_drone_speed()
            except Exception:
                spd = None
            self._log(faz, {
                "t_perf": t, "kaynak": self.kaynak, "durum": self.durum,
                "handoff": int(self.handoff), "fresh": int(self.gps._fresh),
                "drone_x": drone_pos[0], "drone_y": drone_pos[1], "drone_z": drone_pos[2],
                "drone_yaw_deg": yaw_m, "drone_yaw_rad": drone_yaw, "drone_speed": spd,
                "vown_x": v_own[0], "vown_y": v_own[1],
                "est_x": (est[0] if est is not None else None),
                "est_y": (est[1] if est is not None else None),
                "est_z": (est[2] if est is not None else None),
                "xy_anlik_x": (sxy[0] if sxy is not None else None),
                "xy_anlik_y": (sxy[1] if sxy is not None else None),
                "son_z_anlik": self.gps.son_z_anlik,
                "son_hiz_x": (sh[0] if sh is not None else None),
                "son_hiz_y": (sh[1] if sh is not None else None),
                "son_hiz_z": (sh[2] if sh is not None else None),
                "son_ham_x": (sm[0] if sm is not None else None),
                "son_ham_y": (sm[1] if sm is not None else None),
                "son_ham_z": (sm[2] if sm is not None else None),
                "ex": ex_l, "ey": ey_l, "d_h": d_h,
                "thr_cmd": self.prev['thr'], "pitch_cmd": self.prev['pitch'],
                "roll_cmd": self.prev['roll'], "yaw_cmd": self.prev['yaw'],
                "drone_pos": drone_pos, "drone_yaw": drone_yaw,   # _log: nose_off_true icin
            })

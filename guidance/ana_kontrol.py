# -*- coding: utf-8 -*-
"""
================================================================================
AVCI DRONE — ANA KONTROL DONGUSU  (guduum + karar mekanizmasi, tek dosya)
================================================================================
GIRIS NOKTASI: main.py -> web.server.main() -> beyin = AvciKontrol(drone),
50 Hz beyin.adim(). Manuel/pasif modda server yalnizca beyin._hedef_temizle()
cagirir (J olcumu akar, ucus komutu uretilmez). Ayrinti: guidance/GUDUM_HARITA.md

FAZLAR / FSM (self.durum):
  ARAMA  -> GPS yaklasma: bozuk GNSS'i J (fusion/inovasyonlu_j_v2) temizler
            (+2sn lead), PD + EMA-turev + mesafeye gore hiz tavani (speed_cap
            FRENLEME profili) + STANDOFF nisan noktasi ile hedefe yaklasir.
            YALNIZ bu fazda calisan mekanikler: kalkis kapisi, loiter/dropout,
            APPROACH_STANDOFF/ALT_OFFSET (kamera kadraji icin hedefin 5 m alti),
            speed_cap/fren. GORSEL fazda BUNLARIN HICBIRI CALISMAZ (erken return).
  KILIT  -> ayni GPS yaklasma; d_h < HANDOFF_RANGE histerezisiyle isaretlenir
            (gorsel faz devralmaya hazir).
  GORSEL_GUDUM -> yonelim YALNIZCA kameradan: YOLO bbox (server dedektor thread
            -> set_gorsel_tespit) -> _gorsel_guduum -> guidance/png_gorsel.py
            (PNG carpisma rotasi, Cfg.VIS_LAW). Kayipta kademeli: kor-devam ->
            hover -> (OTO'da) GPS'e geri don.
  Otomatik gecis (vis_mode=OTO): AUTO_VISUAL_HANDOFF + ard arda VIS_N_LOCK
  gecerli tespit + handoff yakinligi. Manuel: set_vis_mode GPS/GORSEL zorlar.

TASARIM TEZI (cevik hedefe dayaniklilik):
  GNSS gecikme-baskin + ~29 m hata tabani. GPS fazinin HEDEFI "kestirilen
  noktaya hassas oturmak" DEGIL, "tespit yaricapina yaklasip gorsel faza
  devretmek" (PROXIMITY). Hassas terminal is gorsel fazin (PNG) isidir.

>>> SIMDE DOGRULA (frame/birim/isaret) <<<
  - Konum birimi cm (filtre R=100, hiz_max=3000 -> cm; get_drone_speed cm/s).
  - get_drone_rotation DERECE dondurur (Cfg.ROT_IN_DEGREES=True).
  - Isaret yonleri yanlissa Cfg.PITCH_SIGN / ROLL_SIGN / YAW_SIGN cevir.
================================================================================
"""
import csv
import math
import os
import time
import numpy as np
from fusion.inovasyonlu_j_v2 import GNSSDuzeltici as V2Filtre   # v2: tek uretim filtresi
from guidance.ibvs_guidance import AvciGorselGuduum             # gorsel faz: bbox -> angle-mode (bagimsiz)
from guidance.png_gorsel import AvciPNGGuduum                   # gorsel PNG: bbox -> LOS -> carpisma rotasi

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
    # hedef (GERCEK / truth) + drone truth + gercek mesafe + hedef rotasyon (guvenilmez)
    "true_tx", "true_ty", "true_tz", "true_dx", "true_dy", "true_dz", "gercek_mesafe",
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
    # GORSEL PNG (VIS_LAW="PNG"): kamera-menzil (m), kapanma hizi (m/s), LOS donme (rad/s)
    "png_R_m", "png_Vc", "png_omega",
]


# ==========================================================
# CONFIG — FAZ BANTLARINA AYRILMISTIR (hangi sabit hangi fazda calisir):
#   [ORTAK]         : her fazda gecerli (birim/isaret/dongu/komut tavani/log)
#   [GPS-YAKLASMA]  : YALNIZ durum != GORSEL_GUDUM iken (kalkis, standoff,
#                     fren/speed_cap, PD, None yonetimi). Gorsel faza KARISMAZ.
#   [GORSEL]        : kilit/kayip FSM'i + PNG carpisma rotasi (png_gorsel.py).
# Canli-tune: web arayuzu /api/tune ile TUNE_ALLOW listesindekileri degistirir.
# ==========================================================
class Cfg:
    # ================= [ORTAK] =================
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

    # ================= [GPS-YAKLASMA] (durum != GORSEL_GUDUM) =================
    # --- KALKIS / ARAMA IRTIFASI ---
    SEARCH_ALT = 5000.0         # cm; arama irtifasi (TUNE). Kalkis ayrı katmanda ise TAKEOFF=False.
    TAKEOFF = True
    ALT_TOL = 200.0             # cm; irtifa ulasma tolerasi
    TAKEOFF_THR = 0.6           # tirmanma throttle

    # --- HANDOFF (histerezisli) ---
    HANDOFF_RANGE = 4000.0      # cm; tespit menziline gore TUNE et (genis tut)
    HANDOFF_EXIT  = 5000.0      # bu mesafenin disina cikinca handoff iptal
    # OTOMATIK GORSEL DEVRI (YOLO kilidi + yakinlik -> GORSEL_GUDUM).
    # ACIK (2026-07-06): gorsel faz olgunlasti (PNG carpisma-rotasi + kamera-menzil).
    # Yakinlik (d_h<HANDOFF_RANGE) + ard arda VIS_N_LOCK gecerli tespit saglaninca
    # saldiri KAMERAYA devredilir -> otonom angajman/vurus zinciri (Ister 9/10).
    # Manuel GORSEL switch (set_vis_mode "GORSEL") bu bayraktan BAGIMSIZ calisir.
    AUTO_VISUAL_HANDOFF = True

    # --- TERMINAL VURUS (GPS ile CARPMA) — VARSAYILAN KAPALI ---
    # GOREV MIMARISI: GPS yalnizca hedefe YETERINCE YAKLASIR (yaklasma + hedefi kadraj/FOV'da
    # tutma); SALDIRI (vurus) KAMERA VERISIYLE yapilir (gorsel faz). Bu yuzden GPS terminal
    # carpmasi (asagidaki ram blogu) VARSAYILAN OLARAK DEVRE DISI. Silinmedi -> kavram korunur,
    # gerekirse tek bayrakla geri acilir. Kamera-tabanli vurus mantigi SONRA eklenecek.
    #   True  : d < STRIKE_RANGE'de GPS carpisma-rotasiyla hedefe dalar (eski davranis).
    #   False : GPS terminalde de sadece YAKLASIR/kadrajlar; yakinlik+YOLO kilidinde kameraya devreder.
    GPS_TERMINAL_STRIKE = False
    # Carpisma-rotasi (yalnizca GPS_TERMINAL_STRIKE=True iken): v_des = v_hedef + v_close*LOS;
    # v_close = clamp(KP_CLOSE*d, V_CLOSE_MIN, V_CLOSE); uzakta hizli, yakinda kademeli yavaslar.
    STRIKE_RANGE = 6000.0       # cm (60 m); bu menzil altinda vurus moduna gec
    V_CLOSE      = 1200.0       # cm/s (12 m/s) kapanis hizi TAVANI (uzakta)
    KP_CLOSE     = 0.6          # 1/s; kapanis hizi = KP_CLOSE*mesafe -> yakinda kademeli yavaslar
    V_CLOSE_MIN  = 700.0        # cm/s (7 m/s) kapanis hizi TABANI (COMMIT/RAM). Eskiden
                               # v_close temasta 0'a iniyor + hiz-eslemesi drone'u frenliyordu
                               # -> ~1.3 m'de GERI ATILMA (ucus logu: 16 bounce). Taban ile
                               # drone hedefin ICINE itmeye devam eder -> delip gecer (hit).
    KV_STRIKE    = 2.5          # hiz izleme kazanci [1/s] (dusuk -> yumusak; ivme = KV*(v_des-v_own))
    A_MAX_STRIKE = 9.81 * math.tan(math.radians(35.0)) * 100.0   # ~687 cm/s^2 yatay ivme tavani
    STRIKE_TILT  = 0.8          # vurus tilt yetkisi (1.0 yerine 0.8 -> daha az agresif)
    COMMIT_RANGE = 500.0        # cm (5 m); bu menzil altinda YANAL (LOS'a dik) ivmeyi kis ->
                               # temasta LOS acisal hizi patliyor (log: 7783 deg/s) -> komut
                               # cilginca donup salinim/burun-kaybi yapiyor. Yakinda hedefe
                               # DUZ dal (commit), yani kovalamayi birak.
    VZ_MAX       = 3333.0       # cm/s; oyun max dikey hiz (120 km/h). Terminal 3D-carpmada
                               # throttle ~ (istenen dikey hiz)/VZ_MAX olceginde kullanilir.

    # --- YAKLASMA HIZI PROFILI / FRENLEME (overshoot guard) ---
    # speed_cap(): hedefe BRAKE_DIST altinda yaklastikca hiz tavani V_CAP_FAR'dan
    # V_CAP_NEAR'a kademeli iner; hiz tavani asilirsa pitch sonumlenir (fren).
    # YALNIZ GPS-yaklasma fazinda calisir; gorsel fazda devrede DEGIL. Etkisi:
    # gorsel handoff ANINDAKI hizi/geometriyi bu profil belirler (V_CAP_NEAR
    # dusukse handoff yavas ama kontrollu baslar).
    V_CAP_FAR  = 2500.0         # cm/s uzakta (120km/h = 3333 cm/s'in altinda)
    V_CAP_NEAR = 500.0          # cm/s handoff yakininda
    BRAKE_DIST = 7000.0         # cm; bu mesafe altinda hizi kademeli dusur

    # --- ANTI-OVERSHOOT STANDOFF (B) — yalnizca GPS_TERMINAL_STRIKE=False (yaklasma-only) ---
    # GPS hedefin USTUNE ucup GECMESIN diye pozisyon komutu hedefe DEGIL, hedeften
    # APPROACH_STANDOFF kadar GERIDEKI noktaya surulur -> drone standoff'ta durur/paceler,
    # hedef HEP ONDE (FOV'da) kalir; kamera devralana kadar gorsel temas korunur (nose_off
    # ~180 flip'leri biter). KISA lead (APPROACH_LEAD_S), 2sn tam lead'in manevrada nisan
    # noktasini savurup drone'u hedefin KARSISINA atmasini onler. (GPS_TERMINAL_STRIKE=True
    # iken bu blok DEVRE DISI -> eski ram davranisi birebir korunur.)
    APPROACH_STANDOFF = 500.0   # cm (5 m) KOMUT; EFEKTIF takip mesafesi bunun USTUNDE cikar:
                               # hareketli hedefi kovalarken PD gecikmesi (pursuit lag) fazladan
                               # mesafe ekler -> komut ~2x'i efektif olur. Sim gozlemi: komut 10m ->
                               # efektif ~20m; efektifi ~10m'ye indirmek icin komut 5m'ye cekildi.
                               # TUNE (sim): hala uzaksa dusur / KP_H veya V_CAP_NEAR ile kapanisi guclendir.
                               # (sim-tune 2026-07-03: 30m -> 10m; 2026-07-04: efektif ~20m -> komut 5m)
    APPROACH_LEAD_S   = 0.5     # s; yaklasma nisan noktasi icin KISA lead (tam 2sn overshoot yapiyordu)
    # KAMERA CERCEVELEME (dikey): drone hedefin bu kadar ALTINDA ucar -> kamera 25 derece
    # YUKARI tilt'li oldugundan hedef kadrajin MERKEZININ BIRAZ USTUNDE durur (net gorunur,
    # gorsel kilide hazir). Geometri (~10 m standoff'ta): ~466 cm hedefi tam ortalar; "biraz
    # ustu" icin biraz fazlasi. TUNE (sim): kadrajda hedefi istedigin yukseklige getir.
    # NOT: yalnizca yaklasma-only'de uygulanir (GPS_TERMINAL_STRIKE=True iken carpma bozulmasin).
    APPROACH_ALT_OFFSET = 500.0  # cm (5 m); drone hedefin ALTINDA kalacagi dikey ofset

    # --- PD GAINS (hata cm cinsinden) — DEGISTIRME ---
    KP_H = 0.00025              # yatay konum -> komut
    KD_H = 0.00060             # yatay turev -> sonumleme (modest; filtre zaten lead'liyor)
    KP_Z = 0.00040             # irtifa -> throttle
    KD_Z = 0.00100
    KI_Z = 0.00020             # YENI dikey INTEGRAL: ileri-ucus tasimasi yuzunden P-only
                               # hedefin ~14 m USTUNDE dengeleniyordu (kalici hata). I terimi
                               # bu yanliligi zamanla toplayip kapatir -> drone hedef irtifasina
                               # oturur (sim: 14 m -> ~0). Anti-windup icin band+clamp asagida.
    INT_Z_BAND = 2500.0        # cm; integrali SADECE |ez|<25 m iken biriktir (tirmanista windup yok)
    INT_Z_MAX  = 5000.0        # cm; integral clamp (KI_Z*INT_Z_MAX = 1.0 -> tavani asmaz)
    KP_YAW = 1.3               # yaw hatasi (rad) -> yaw komutu (sim-tune 2026-07-03: 1.0->1.3, burun hizli)

    # --- KOMUT TAVANLARI ---
    PITCH_MAX = 0.75
    ROLL_MAX  = 0.75
    THR_UP    = 0.70
    THR_DN    = -1.00          # DUZELTME: eski -0.40 cok zayifti. Tani verisi: drone hedefin
                              # ustundeyken THR=-0.40 komutuna RAGMEN +3 m/s tirmanmaya devam
                              # ediyordu (ileri-ucus tasimasi -0.40'i yeniyor). Tam inme yetkisi
                              # gerekli; PD sadece cok yukaridayken -1'e gider, hedefe yakinda 0'a doner.
    YAW_MAX   = 0.45           # burnu (kamerayi) hedefe donuk tutar (sim-tune 2026-07-03: 0.30->0.45,
                               # burun manevrali hedefe daha hizli doner -> FOV kaybi azalir; salinim yok).

    # --- HIZ LIMITI (bank rate uyumlu; salinim onleyici) ---
    MAX_DELTA = 0.05           # komut/tik max degisim

    # --- FILTRELEME / DEADBAND ---
    DERIV_EMA = 0.20
    POS_DEADBAND = 150.0       # cm; yakinda jitter onle
    YAW_DEADBAND = math.radians(3)

    # --- None YONETIMI (tik @50Hz) ---
    # SIM v0.0.5: hedef GPS NOMINAL 5 Hz (yarisma kosulu; eskiden 1 Hz'di) ve
    # KESINTI ZAMANLAMASI tanimlandi: 30. saniyeden sonra her 10 sn'de bir ~2 sn
    # veri gelmeyebilir (+ gecikme/gurultu bozulmalari surer, degerleri aciklanmaz).
    # 6 sn'lik tutma penceresi 2 sn'lik kesintileri bol marjla kapatir; filtre
    # kestirimi lead'li oldugundan tasimak guvenli. Loiter yalnizca GERCEK uzun
    # kesintide devreye girer.
    HOLD_TICKS = 300           # ~6s: bu sureye kadar son kestirimi tut; otesi dropout -> loiter

    # ================= [ORTAK] =================
    # --- TESHIS (irtifa kacma sorununu cozmek icin gecici) ---
    # True: ~2Hz konsola [Z] satiri basar. drone_z vs hedef irtifasi (filtre & GERCEK),
    # ez, thr, hiz, pitch. Sorun cozulunce False yap.
    DEBUG_Z = True

    # --- UCUS LOGU (davranis teshisi) ---
    # True iken adim() HER kontrol-tikini (~50 Hz) zengin bir CSV'ye yazar
    # (ucus_log_<zaman>.csv). analiz_ucus.py bunu okuyup geri-cekilme / salinim /
    # gorsel-temas-kaybi teshisi yapar. Yarismada/uretimde False yap.
    LOG_ENABLE = True

    # ================= [GORSEL] (kilit/kayip FSM + yasalar) =================
    # --- GORSEL GUDUM (DUZ IBVS) — gorsel temas SONRASI yonelim (YALNIZCA kamera) ---
    # Kilit: conf>=VIS_CONF_MIN kareler ard arda VIS_N_LOCK olunca GORSEL_GUDUM'a gec
    # ve BIR DAHA GPS'e donme (yarisma kurali). Isaret/gain'ler CANLI tune ile
    # kalibre edilir (once tek eksen: yaw<-ex, sonra throttle<-ey, en son ileri).
    VIS_MODEL_PATH   = os.path.join(_PROJ_ROOT, "models", "best.pt")   # tespit modeli (task=detect, sinif: talon)
    VIS_CONF_MIN     = 0.45     # kilit/komut icin asgari guven
    VIS_N_LOCK       = 5        # ardisik gecerli-tespit -> GORSEL_GUDUM (yanlis-poz bastir)
    VIS_STALE_S      = 0.5      # tespit bu sureden eskiyse yok say (kayip mantigi devreye girer)
    VIS_DEADRECKON_S = 0.5      # kayipta son EMA yonuyle KISA kor-devam, sonra hover
    VIS_LOST_TO_GPS_S = 1.0     # kayip bu sureyi asarsa GPS guduumune GERI DON (yeniden yaklas +
                               # gorseli yeniden kilitle). 0 = asla donme (eski "hover sonsuza"
                               # davranisi). Sure _vis_lost_count ile olculur -> son gorusten
                               # itibaren ~ (VIS_STALE_S + bu) toplam kayipta GPS'e doner.
    VIS_EMA          = 0.4      # ex/ey EMA yumusatma (tek-kare yanlis tespiti bastir)
    # DIKEY REFERANS — KAMERA 25 DERECE YUKARI TILT TELAFISI (SDK v2.2 resmilesti).
    # Kamera burnu 25 derece yukari baktigindan "bbox tam merkezde" = hedef burnun
    # 25 derece USTUNDE demek -> drone dengelenmek icin hedefin ALTINA iner (20 m'de
    # ~9 m!). Cozum: hedefi merkezin ALTINDAKI su referans cizgide tut; dikey hata
    # (ey - VIS_EY_REF) olur -> yaklasma DUZ/ayni-irtifa geometrisinde kalir.
    # Deger: tan(25)/tan(vFOV/2). 125 derece YATAY FOV (dogrulandi) + 16:9 ->
    # vFOV/2 ~47.2 derece -> ref ~0.43. Ince ayar SIM'DE: hedef seninle AYNI
    # irtifadayken slider'i bbox merkezinin oturdugu cizgiye getir (turuncu REF).
    VIS_EY_REF       = 0.43     # yalniz ARAYUZ turuncu REF cizgisi (elev=0 gostergesi);
                                # guduum artik LOS formulunden turetir (asagidaki TILT/vFOV)
    # LOS (bakis hatti) geometrisi — dikey komut buradan turetilir:
    #   elev = VIS_TILT_DEG - atan(ey * tan(VIS_VFOV_YARIM_DEG))   (ufka gore aci)
    #   throttle = VIS_K_VZ * tan(elev)  -> tiklanan/tespit edilen noktaya UC.
    VIS_TILT_DEG     = 25.0     # kamera yukari tilt (SDK v2.2 resmi)
    VIS_VFOV_YARIM_DEG = 47.2   # dikey yarim FOV: 125 der YATAY (dogrulandi) + 16:9
    # Isaretler (SIM'de kalibre et: komut hatayi AZALTMALI; artiriyorsa isareti ters cevir)
    VIS_SIGN_YAW     = +1.0     # ex>0 (hedef SAGDA) -> burnu hedefe cevir
    VIS_SIGN_VZ      = -1.0     # LOS modunda KULLANILMIYOR (isaret geometriden gelir; elev>0=tirman)
    VIS_SIGN_PITCH   = +1.0     # ileri yaklasma +pitch (Cfg.PITCH_SIGN ile ayni mantik)
    # Kazanclar / kapilar
    VIS_K_YAW        = 0.5      # yatay ortalama kazanci (yaw = SIGN*K*ex)
    VIS_K_VZ         = 1.5      # dikey LOS kazanci (throttle = K*tan(elev); tan-uzayi ->
                                # eski 0.5 cok zayif kalir; alt kenar ~ -0.61, REF cizgisi 0)
    VIS_K_FWD        = 0.4      # ileri yaklasma kazanci (merkez-kapisi ACIKKEN)
    VIS_FWD_MAX      = 0.5      # ileri (pitch) komut tavani
    VIS_CENTER_GATE  = 0.35     # YALNIZ |ex| bu esigin ALTINDA ise ILERI'ye izin ver (dikey
                                # hata ileriyi bloklamaz; throttle eszamanli cozer)
    VIS_AREA_STOP    = 0.20     # bbox alan orani buna yaklasinca ileri hizi 0'a iner (yakin -> yavasla)

    # --- GORSEL PNG (bbox -> LOS -> oransal seyrusefer carpisma rotasi) ---
    # Terminal gorsel yasa: hedefin GIDECEGI noktayi kesen carpisma rotasi (PN). IBVS'in
    # yanina konur; VIS_LAW ile secilir (varsayilan PNG, IBVS kiyas/yedek). Ayrinti:
    # guidance/png_gorsel.py docstring. Menzil = bbox + pinhole (GNSS bagimsizligi isteri).
    VIS_LAW          = "PNG"    # "PNG" | "IBVS"
    VIS_PN_N         = 4.0      # navigasyon sabiti (3..5); png_sim'de dogrulandi
    VIS_PN_A_MAX     = A_MAX_STRIKE   # cm/s^2 yanal ivme tavani (GPS strike ile ayni ~687)
    VIS_PN_TILT      = 0.8      # ivme -> pitch/roll yetki carpani (STRIKE_TILT mantigi)
    VIS_SPAN_CM      = 171.8    # Talon kanat acikligi (talon_keypoints ile dogrulandi)
    VIS_R_EMA        = 0.25     # pinhole menzil EMA
    VIS_VC_EMA       = 0.30     # kapanma hizi EMA
    VIS_OMEGA_EMA    = 0.35     # LOS donme vektoru EMA
    VIS_OMEGA_MAX    = 3.0      # rad/s; Omega bilesen clamp (tek-kare bbox sicramasi patlatmasin)
    VIS_R_MIN        = 100.0    # cm; menzil taban clamp
    VIS_R_MAX        = 30000.0  # cm; menzil tavan clamp (300 m otesi guvenilmez)
    VIS_W_PX_MIN     = 4.0      # px; bbox bundan darsa menzil GUNCELLEME (tut / J-yedek)
    VIS_VC_CAP       = V_CLOSE      # cm/s; kapanma hizi tavani (GPS strike ile ayni)
    VIS_VC_MIN       = V_CLOSE_MIN  # cm/s; kapanma hizi tabani (temasta geri atilmayi onler)
    VIS_KP_CLOSE     = 0.6      # 1/s; v_close_des = clamp(KP*R, VC_MIN, VC_CAP)
    VIS_KV_CLOSE     = 2.5      # 1/s; LOS-boyu ivme = KV*(v_close_des - Vc)
    VIS_COMMIT_R     = 500.0    # cm; altinda yanal PN kisilir (LOS-rate singularitesi)
    VIS_COMMIT_LAT   = 0.25     # commit'te yanal yetki tabani
    VIS_TAU_Z        = 0.5      # s; dikey PN ivmesi -> dikey hiz komutu zaman sabiti
    VIS_PN_SIGN_VZ   = -1.0     # dikey komut isareti (SIM'de dogrulandi: LOS-z ile TERS calisiyordu
                               # -> hedef yukarida iken alcaliyordu). +1 yaparsan eski/duz esleme.
    VIS_PN_FALLBACK_J = True    # menzil gecersizken Vc/R BUYUKLUGU J'den (YON asla kameradan cikmaz)


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
    """[GPS-YAKLASMA] Mesafeye gore yaklasma hizi tavani (cm/s) — FRENLEME profili.
    adim() icinde hiz tavani asilirsa pitch sonumlenir. GORSEL fazda CALISMAZ
    (adim gorsel yolda erken doner); handoff ANINDAKI hizi bu profil belirler."""
    if d_horiz >= Cfg.BRAKE_DIST:
        return Cfg.V_CAP_FAR
    t = d_horiz / Cfg.BRAKE_DIST                      # 0..1
    return Cfg.V_CAP_NEAR + (Cfg.V_CAP_FAR - Cfg.V_CAP_NEAR) * t


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
        self.son_xy_anlik = None        # J'nin ANLIK (lead'siz) yatay konumu (cm) - terminal vurus LOS'u
        self.son_hiz = None             # J'nin kestirdigi hedef hizi (cm/s, 3B) - olcum/ileri kullanim
        self._fresh = False             # bu tik J'den YENI gecerli kestirim geldi mi?

        # --- FAZ-1 guduum durumu (faz1_gnss_yaklasma.Faz1Guidance'tan) ---
        self.prev = {'thr': 0.0, 'pitch': 0.0, 'roll': 0.0, 'yaw': 0.0}
        self.e_prev = None
        self.t_prev = None
        self.de = [0.0, 0.0, 0.0]       # EMA-filtreli hata turevi (cm/s)
        self._ez_int = 0.0              # dikey INTEGRAL birikimi (cm*s) - kalici irtifa hatasini kapatir
        # kendi YATAY hiz vektoru (temiz konum sonlu-fark, EMA) - terminal vurus icin
        self._own_pxy = None            # onceki kendi yatay konum (cm)
        self._own_tv = None             # onceki olcum zamani
        self._own_v = np.zeros(2)       # kendi yatay hiz (cm/s, dunya)
        # GERCEK modda hedef hizi (truth konum sonlu-fark) - carpisma-rotasi icin
        self._gt_prev_p = None          # onceki truth hedef konum (cm)
        self._gt_prev_t = None
        self._gt_vel = np.zeros(3)      # hedef hizi (cm/s, 3B)
        self.none_count = 0
        self.last_est = None
        self.handoff = False
        self.handoff_announced = False
        self._kalkis_done = (not Cfg.TAKEOFF)

        # debug olcum birikimi
        self.debug_olc = debug_olc
        self.ham_hatalar = []
        self.j_hatalar = []
        self.bozukluk_sayac = {}

        # ucus logu (Cfg.LOG_ENABLE) - lazy-open, uzunca zaman-damgali dosya
        self._log_f = None
        self._log_w = None

        # --- GORSEL GUDUM (IBVS) durumu ---
        # son_tespit: server.dedektor_dongusu'nin beyin_lock icinde yazdigi son bbox dict.
        self.son_tespit = None          # {cx,cy,w,h,conf,W,H,t} | None
        self.son_tespit_t = None        # o tespitin perf_counter zamani (bayatlik kontrolu)
        self._vis_pos_count = 0         # ardisik gecerli-tespit (kilit histerezisi)
        self._vis_lost_count = 0        # ardisik kayip (kor-devam -> hover karari)
        self._vis_ilan = False          # "GPS kesildi" anonsu bir kez basilsin
        self.ibvs = AvciGorselGuduum()  # bbox -> angle-mode komut (bagimsiz modul, canli-tune)
        self.pngg = AvciPNGGuduum()     # bbox -> LOS -> PN carpisma rotasi (Cfg.VIS_LAW="PNG")
        self.png_tlm = {}               # son PNG telemetrisi (server build_telemetry okur; salt-okunur)
        self.vis_mode = "OTO"           # guduum pipeline switch (test): OTO | GPS | GORSEL

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
        self.son_xy_anlik = None
        self.son_hiz = None
        self._fresh = False
        # FAZ-1 durumunu sifirla: komutlar 0'dan rate-limit'lensin, turev/handoff temiz.
        self.prev = {'thr': 0.0, 'pitch': 0.0, 'roll': 0.0, 'yaw': 0.0}
        self.e_prev = None
        self.t_prev = None
        self.de = [0.0, 0.0, 0.0]
        self._ez_int = 0.0              # dikey integrali taze baslat
        self._own_pxy = None            # kendi yatay hiz kestirimini taze baslat
        self._own_tv = None
        self._own_v = np.zeros(2)
        self.none_count = 0
        self.last_est = None
        self.handoff = False
        self.handoff_announced = False
        self.durum = "ARAMA"
        self._kalkis_done = (not Cfg.TAKEOFF)
        # GORSEL GUDUM: yeni gorev -> gorsel kilit/kor-devam durumunu da taze basla
        self.son_tespit = None
        self.son_tespit_t = None
        self._vis_pos_count = 0
        self._vis_lost_count = 0
        self._vis_ilan = False
        self.ibvs.sifirla()
        self.pngg.sifirla()
        self.png_tlm = {}
        # ucus logu: yeni gorev -> yeni dosya (sonraki tik taze zaman-damgali acar).
        # NOT: ayni kaynak ust uste secilirse bu metod erken doner (yukarida) -> dosya
        # donmez; temiz dosya icin server'i yeniden baslat ya da kaynak degistir.
        if self._log_f is not None:
            try: self._log_f.close()
            except Exception: pass
            self._log_f = self._log_w = None

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
                p = np.array(dbg["target"]["position"], float)
                self.son_temiz = p
                self.son_z_anlik = float(p[2])                # gercekte lead yok -> ayni z
                self.son_xy_anlik = np.array([p[0], p[1]], float)  # carpisma-rotasi LOS'u icin
                self.son_hiz = self._gercek_hedef_hiz(p)      # hedef hizi (truth sonlu-fark)
                self._fresh = True                            # -> terminal vurus GERCEK modda da acilir
            else:
                self._fresh = False
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
                    self.son_xy_anlik = None
                else:
                    self.son_hiz = np.array(durum["vel"], float)
                    self.son_z_anlik = float(durum["pos"][2])     # lead'siz anlik irtifa
                    # lead'siz ANLIK yatay konum -> terminal vurus (carpisma-rotasi) LOS'u
                    # bunu kullanir; lead son_temiz'de degil, hedef hizini eslemede otomatik.
                    self.son_xy_anlik = np.array([durum["pos"][0], durum["pos"][1]], float)
            else:
                self._fresh = False           # isinma/donma -> kestirim yok
        else:
            self._fresh = False               # ratelimit ile donmus kare (yeni bilgi yok)
        return self.son_temiz                  # None olabilir (isinma)

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
    #  Kendi YATAY hiz vektoru (cm/s, dunya): temiz konum sonlu-fark + EMA.
    #  Terminal vurus (carpisma-rotasi) hiz-izleme icin kullanir.
    # ----------------------------------------------------------------
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

    # ----------------------------------------------------------------
    #  GERCEK modda hedef hizi (cm/s, 3B): truth konum sonlu-fark + EMA.
    #  Carpisma-rotasi (v_des = v_hedef + V_CLOSE*LOS) icin gerekli; truth temiz
    #  oldugundan sonlu-fark guvenli.
    # ----------------------------------------------------------------
    def _gercek_hedef_hiz(self, p):
        now = time.perf_counter()
        if self._gt_prev_p is None or self._gt_prev_t is None:
            self._gt_prev_p = p.copy(); self._gt_prev_t = now
            return self._gt_vel
        dt = now - self._gt_prev_t
        if 1e-3 < dt < 0.5:
            raw = (p - self._gt_prev_p) / dt
            self._gt_vel = 0.7 * self._gt_vel + 0.3 * raw
            self._gt_prev_p = p.copy(); self._gt_prev_t = now
        elif dt >= 0.5:
            self._gt_prev_p = p.copy(); self._gt_prev_t = now
        return self._gt_vel

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

    # ----------------------------------------------------------------
    #  UCUS LOGU: her tik zengin teshis satiri (Cfg.LOG_ENABLE). Lazy-open,
    #  zaman-damgali dosya. Truth + drone/hedef rotasyon + nose_off_true burada
    #  hesaplanir (loglama modu; her tik birkac SDK cagrisi kabul edilir).
    #  d: cagri yerinden gelen alanlar (+ 'drone_pos','drone_yaw' -> nose_off_true icin).
    # ----------------------------------------------------------------
    def _log(self, phase, d):
        if not Cfg.LOG_ENABLE:
            return
        if self._log_f is None:                                  # ilk yazim -> dosya ac
            os.makedirs(_VERI_DIR, exist_ok=True)                # ciktilar veri/ altina
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
            trot = self.drone.get_target_rotation()             # ANA (bozuk) akis - guvenilmez
            d["tgt_roll"], d["tgt_pitch"], d["tgt_yaw"] = float(trot[0]), float(trot[1]), float(trot[2])
        except Exception:
            pass
        try:
            dbg = self.drone.get_debug_truth()
            if dbg.get("available"):
                tp = dbg["target"]["position"]; dp = dbg["drone"]["position"]
                d["true_tx"], d["true_ty"], d["true_tz"] = float(tp[0]), float(tp[1]), float(tp[2])
                d["true_dx"], d["true_dy"], d["true_dz"] = float(dp[0]), float(dp[1]), float(dp[2])
                d["gercek_mesafe"] = math.sqrt((tp[0]-dp[0])**2 + (tp[1]-dp[1])**2 + (tp[2]-dp[2])**2)
                dpos = d.get("drone_pos"); dyaw = d.get("drone_yaw")
                if dpos is not None and dyaw is not None:        # burun ile GERCEK hedef acisi (deg)
                    d["nose_off_true"] = math.degrees(
                        wrap_pi(math.atan2(tp[1] - dpos[1], tp[0] - dpos[0]) - dyaw))
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

    def _log_early(self, phase, t, drone_pos, yaw_m, drone_yaw, v_own):
        # Erken-donus tikleri (TAKEOFF/DROPOUT/WARMUP): sadece meta+drone+uygulanan komut.
        if not Cfg.LOG_ENABLE:
            return
        self._log(phase, {
            "t_perf": t, "kaynak": self.kaynak, "none_count": self.none_count,
            "drone_x": drone_pos[0], "drone_y": drone_pos[1], "drone_z": drone_pos[2],
            "drone_yaw_deg": yaw_m, "drone_yaw_rad": drone_yaw,
            "vown_x": v_own[0], "vown_y": v_own[1],
            "thr_cmd": self.prev['thr'], "pitch_cmd": self.prev['pitch'],
            "roll_cmd": self.prev['roll'], "yaw_cmd": self.prev['yaw'],
            "drone_pos": drone_pos, "drone_yaw": drone_yaw,
        })

    def _loiter(self):
        # dropout / veri yok: agresifligi kes, hover (thr=0 -> irtifa korunur), seviyelen
        self._send(0.0, 0.0, 0.0, 0.0)

    # ----------------------------------------------------------------
    #  GORSEL TESPIT KOPRUSU (thread-guvenli): server.dedektor_dongusu AGIR YOLO
    #  inference'i beyin_lock DISINDA kosar, sonucu beyin_lock ICINDE buraya yazar;
    #  adim() ayni kilit altinda _gorsel_tespit_oku ile okur -> inference tik'ten
    #  DECOUPLE (kontrol dongusu 50Hz akici kalir).
    #  det: {cx,cy,w,h,conf,W,H,t} | None  (gorsel_tespit.HedefDedektor.tespit_et)
    # ----------------------------------------------------------------
    # ----------------------------------------------------------------
    #  GUDUM PIPELINE SWITCH (test icin): hangi yol aktif?
    #    "OTO"    -> otomatik: N_LOCK tespitte gorsel kilitlenir, kayipta GPS'e doner
    #    "GPS"    -> ZORLA GPS: gorsel yol kapali (gorseldeysen GPS'e doner)
    #    "GORSEL" -> ZORLA GORSEL: kilidi atla, hemen gorsel; kayipta GPS'e DONMEZ
    # ----------------------------------------------------------------
    def set_vis_mode(self, mode):
        m = str(mode).upper()
        if m not in ("OTO", "GPS", "GORSEL"):
            return False
        self.vis_mode = m
        self._vis_pos_count = 0          # switch -> gorsel kilit/EMA temiz baslasin
        self._vis_lost_count = 0
        self._vis_ilan = False
        self.ibvs.sifirla()
        self.pngg.sifirla()
        return True

    def set_gorsel_tespit(self, det):
        if det is not None:
            self.son_tespit = det
            self.son_tespit_t = det.get("t", time.perf_counter())
        # det None ise ESKI tespiti SILME: tek bos kare kilidi dusurmesin. Bayatlik
        # (VIS_STALE_S) _oku'da elenir; kayip histerezisini _vis_lost_count yonetir.

    def _gorsel_tespit_oku(self):
        """Bayat-olmayan son tespiti dondur; yoksa/bayatsa None (kayip mantigi devreye girer)."""
        det = self.son_tespit
        if det is None or self.son_tespit_t is None:
            return None
        if (time.perf_counter() - self.son_tespit_t) > Cfg.VIS_STALE_S:
            return None
        return det

    # ----------------------------------------------------------------
    #  GORSEL_GUDUM logu (phase="VISUAL"): meta+drone+uygulanan komut + normalize
    #  gorsel hata (vis_ex/ey), gordu/conf/area. _LOG_COLS'daki vis_* kolonlarini
    #  doldurur; digerleri bos kalir (sema-guvenli; analiz_ucus.py etkilenmez).
    # ----------------------------------------------------------------
    def _log_gorsel(self, t, drone_pos, yaw_m, drone_yaw, v_own, tespit):
        if not Cfg.LOG_ENABLE:
            return
        d = {
            "t_perf": t, "kaynak": self.kaynak, "durum": self.durum,
            "none_count": self.none_count,
            "drone_x": drone_pos[0], "drone_y": drone_pos[1], "drone_z": drone_pos[2],
            "drone_yaw_deg": yaw_m, "drone_yaw_rad": drone_yaw,
            "vown_x": v_own[0], "vown_y": v_own[1],
            "thr_cmd": self.prev['thr'], "pitch_cmd": self.prev['pitch'],
            "roll_cmd": self.prev['roll'], "yaw_cmd": self.prev['yaw'],
            "drone_pos": drone_pos, "drone_yaw": drone_yaw,
            "vis_ex": self.ibvs.ex_f, "vis_ey": self.ibvs.ey_f,
            "vis_gordu": 1 if tespit is not None else 0,
        }
        if tespit is not None:
            d["vis_conf"] = float(tespit.get("conf", 0.0))
            W = float(tespit.get("W", 0) or 0); H = float(tespit.get("H", 0) or 0)
            if W > 1 and H > 1:
                d["vis_area"] = (float(tespit["w"]) * float(tespit["h"])) / (W * H)
        pt = self.png_tlm or {}
        if pt:
            d["png_R_m"] = pt.get("R_m"); d["png_Vc"] = pt.get("Vc_ms")
            d["png_omega"] = pt.get("omega_rads")
        self._log("VISUAL", d)

    # ----------------------------------------------------------------
    #  GORSEL GUDUM (DUZ IBVS) — YONELIM YALNIZCA KAMERADAN.
    #  Gorsel temas VARKEN GPS/filtre YONELIMI KULLANILMAZ (yarisma kurali).
    #  tespit VAR -> ibvs.hesapla(bbox merkezi -> angle-mode komut).
    #  tespit YOK -> KADEMELI: (1) VIS_DEADRECKON_S kor-devam, (2) VIS_LOST_TO_GPS_S'e
    #  kadar hover (ararken bekle), (3) o da asilirsa GPS guduumune GERI DON (re-acquire)
    #  -> durumu ARAMA yap, gorsel kilidi sifirla, None dondur (adim() GPS yoluna duser).
    #  return: (throttle,pitch,roll,yaw) | None (=GPS'e don). _send rate-limit'ler.
    # ----------------------------------------------------------------
    def _gorsel_guduum(self, tespit, t, drone_pos, rot_rpy, v_own, revert_izin=True):
        # revert_izin=False (manuel GORSEL switch): kayipta GPS'e DONME, hover'da kal.
        # YASA SECIMI: Cfg.VIS_LAW == "PNG" -> carpisma-rotasi (png_gorsel), aksi -> IBVS servo.
        png = (Cfg.VIS_LAW == "PNG")
        if tespit is not None:
            self._vis_lost_count = 0
            if png:
                komut = self.pngg.hesapla(tespit, drone_pos, rot_rpy, v_own, Cfg,
                                          j_fallback=self._j_fallback(drone_pos, v_own))
                self.png_tlm = self.pngg.durum()
                return komut
            bbox_merkez = (tespit["cx"], tespit["cy"])
            bbox_boyut  = (tespit["w"], tespit["h"])
            return self.ibvs.hesapla(bbox_merkez, tespit["W"], tespit["H"],
                                     bbox_boyut, Cfg, dt=Cfg.DT)
        # --- KAYIP: kademeli tepki ---
        self._vis_lost_count += 1
        lost_s = self._vis_lost_count * Cfg.DT
        if lost_s <= Cfg.VIS_DEADRECKON_S:
            if png:                              # 1) son Omega/Vc ile LOS'u ilerlet
                komut = self.pngg.kor_devam(Cfg, Cfg.DT)
                self.png_tlm = self.pngg.durum()
                return komut
            return self.ibvs.kor_devam(Cfg)      # 1) son EMA yonuyle KISA kor-devam
        if (not revert_izin) or Cfg.VIS_LOST_TO_GPS_S <= 0 or lost_s <= Cfg.VIS_LOST_TO_GPS_S:
            return 0.0, 0.0, 0.0, 0.0            # 2) hover: ararken bekle (manuel GORSEL'de KAL)
        # 3) UZUN kayip (yalnizca OTO) -> GPS guduumune GERI DON (yeniden yaklas, yeniden kilitle)
        print("[GORSEL] Hedef %.1fs kayip -> GPS guduumune GERI DONULDU (yeniden yaklas)." % lost_s)
        self.durum = "ARAMA"
        self._vis_pos_count = 0
        self._vis_lost_count = 0
        self._vis_ilan = False
        self.ibvs.sifirla()
        self.pngg.sifirla()
        return None                              # -> adim() GPS yoluna DUSER (bu tik)

    # ----------------------------------------------------------------
    #  J-YEDEK (yalniz BUYUKLUK): bbox menzili gecersizken PNG'ye R/Vc buyuklugu ver.
    #  YON verilmez (yarisma kurali: gorsel fazda yonelim yalniz kameradan). son_xy_anlik/
    #  son_z_anlik lead'siz ANLIK kestirim (LOS icin dogru), son_hiz hedef hizi.
    #  Doner: (R_cm, Vc_cms) | None (J kestirimi yoksa).
    # ----------------------------------------------------------------
    def _j_fallback(self, drone_pos, v_own):
        if not Cfg.VIS_PN_FALLBACK_J or self.son_xy_anlik is None or self.son_z_anlik is None:
            return None
        r = np.array([float(self.son_xy_anlik[0]) - float(drone_pos[0]),
                      float(self.son_xy_anlik[1]) - float(drone_pos[1]),
                      float(self.son_z_anlik) - float(drone_pos[2])])
        R = float(np.linalg.norm(r))
        if R < 1e-6:
            return None
        u = r / R
        Vc = None
        if self.son_hiz is not None:
            # Vc = kapanma hizi = dot(u, v_own - v_target) ; own dikey hiz ~0 kabul
            v_i = np.array([float(v_own[0]), float(v_own[1]), 0.0])
            v_t = np.array([float(self.son_hiz[0]), float(self.son_hiz[1]), float(self.son_hiz[2])])
            Vc = float(np.dot(u, v_i - v_t))
        return (R, Vc)

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
        rot_rpy = self.drone.get_drone_rotation()               # (roll,pitch,yaw) deg — PNG LOS icin tam tutum
        yaw_m = rot_rpy[2]
        drone_yaw = math.radians(yaw_m) if Cfg.ROT_IN_DEGREES else yaw_m
        t = time.perf_counter()
        v_own = self._own_hiz(drone_pos[:2], t)                 # kendi yatay hiz (cm/s, dunya)

        # 1) J ile bozuk hedefi temizle (self._fresh: yeni kestirim geldi mi?)
        self._hedef_temizle()
        if self.debug_olc: self._debug_olc()

        # 2) KALKIS (non-blocking): arama irtifasina tirman, sonra yaklasmaya gec.
        if not self._kalkis_done:
            if drone_pos[2] >= Cfg.SEARCH_ALT - Cfg.ALT_TOL:
                self._kalkis_done = True
            else:
                self._send(Cfg.TAKEOFF_THR, 0.0, 0.0, 0.0)      # tirman, seviye
                self._log_early("TAKEOFF", t, drone_pos, yaw_m, drone_yaw, v_own)
                return

        # 2.5) GUDUM PIPELINE SECIMI (switch: self.vis_mode) + GORSEL kesme.
        #      OTO   : conf>=VIS_CONF_MIN kareler ard arda VIS_N_LOCK olunca GORSEL'e kilitlenir;
        #              kayip VIS_LOST_TO_GPS_S'i asarsa GPS'e geri doner (re-acquire).
        #      GPS   : gorsel yol KAPALI (gorseldeysen GPS'e doner) -> hep GPS.
        #      GORSEL: kilidi ATLA, hemen GORSEL; kayipta GPS'e DONME (zorlanmis).
        #      GORSEL kilitliyken asagidaki TUM GPS yonelimi ATLANIR (return) -> gorsel
        #      temas VARKEN GPS yonelimi kullanilmaz. _send prev surekliligi -> sarsintisiz.
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
        else:  # OTO — otomatik kilit: YAKINLIK + YOLO kilidi (ikisi birden)
            if self.durum != "GORSEL_GUDUM":
                if tespit is not None and float(tespit.get("conf", 0.0)) >= Cfg.VIS_CONF_MIN:
                    self._vis_pos_count += 1
                else:
                    self._vis_pos_count = 0
                # HANDOFF: GPS hedefe YETERINCE YAKLASMIS OLMALI (self.handoff = d_h<HANDOFF_RANGE,
                # onceki tikte hesaplanir) VE YOLO kilidi (ard arda VIS_N_LOCK gecerli tespit).
                # Ikisi birden saglaninca saldiri KAMERAYA devredilir; oncesinde GPS yaklasmaya
                # devam eder (uzaktan yanlis-kilit yok).
                # ACIK (Cfg.AUTO_VISUAL_HANDOFF=True, 2026-07-06): kilit+yakinlik saglaninca
                # OTONOM olarak GORSEL_GUDUM'a gecilir (Ister 9/10 angajman zinciri).
                # Manuel GORSEL/GPS switch bu bayraktan bagimsiz calisir.
                if (Cfg.AUTO_VISUAL_HANDOFF
                        and self._vis_pos_count >= Cfg.VIS_N_LOCK and self.handoff):
                    self.durum = "GORSEL_GUDUM"
                    if not self._vis_ilan:
                        print("[GORSEL] Yakinlik + gorsel kilit saglandi -> GPS YAKLASMAYI BIRAKTI, "
                              "yonelim/saldiri yalnizca KAMERA verisiyle.")
                        self._vis_ilan = True

        if self.durum == "GORSEL_GUDUM":
            sonuc = self._gorsel_guduum(tespit, t, drone_pos, rot_rpy, v_own,
                                        revert_izin=(mod == "OTO"))
            if sonuc is not None:
                thr, pitch, roll, yaw = sonuc
                self._send(thr, pitch, roll, yaw)
                self._log_gorsel(t, drone_pos, yaw_m, drone_yaw, v_own, tespit)
                return
            # sonuc None (yalnizca OTO) -> gorsel UZUN kayip -> GPS yolu BU tik calisir

        # ==================== [GPS-YAKLASMA YOLU] ====================
        # Buradan asagisi YALNIZ durum != GORSEL_GUDUM iken calisir (gorsel yol
        # yukarida return etti): None yonetimi, standoff nisan, PD, speed_cap/
        # fren, alcalma onceligi, dikey PID, yaw. Gorsel guduume KARISMAZ.
        # 3) None yonetimi: normal donmus kare (hold) vs dropout (loiter)
        if not self._fresh:
            self.none_count += 1
            if self.none_count <= Cfg.HOLD_TICKS and self.son_temiz is not None:
                est = self.son_temiz                            # son 2sn-lead kestirimi tut
            else:
                self._loiter()                                  # uzun None -> dropout -> bekle
                self._log_early("DROPOUT", t, drone_pos, yaw_m, drone_yaw, v_own)
                return
        else:
            self.none_count = 0
            est = self.son_temiz

        if est is None:                                          # isinma: henuz kestirim yok
            self._loiter()
            self._log_early("WARMUP", t, drone_pos, yaw_m, drone_yaw, v_own)
            return
        self.last_est = est

        # YATAY nisan noktasi:
        #   - GPS_TERMINAL_STRIKE=True (ram): 2sn lead'li kestirim (est) = intercept (eski davranis).
        #   - approach-only (ram KAPALI): B) ANTI-OVERSHOOT STANDOFF -> hedefi GECMEDEN onunde
        #     dur. KISA lead (APPROACH_LEAD_S) ile nisan (savrulmayi onler); pozisyon KOMUTU
        #     hedefe DEGIL, APPROACH_STANDOFF kadar GERIYE surulur -> drone standoff'ta paceler.
        # DIKEY: lead'siz anlik irtifa (lead dikeyde irtifa asimina/yukari kacmaya yol aciyor).
        z_ref = self.son_z_anlik if self.son_z_anlik is not None else float(est[2])
        # KAMERA CERCEVELEME: hedefi kadrajda merkezin BIRAZ USTUNDE tut. z_ref'i (hedef
        # irtifasi) APPROACH_ALT_OFFSET kadar ASAGI cek -> drone hedefin altinda dengelenir
        # -> 25 derece yukari-tilt kamerada hedef LOS'u yukselir -> kadrajda yukari kayar.
        # Yalnizca yaklasma-only'de (ram KAPALI); carpma geometrisini bozmasin.
        if not Cfg.GPS_TERMINAL_STRIKE:
            z_ref -= Cfg.APPROACH_ALT_OFFSET
        ez = float(z_ref - drone_pos[2])
        if (not Cfg.GPS_TERMINAL_STRIKE) and self.son_xy_anlik is not None and self.son_hiz is not None:
            tx = float(self.son_xy_anlik[0]) + Cfg.APPROACH_LEAD_S * float(self.son_hiz[0])  # kisa lead
            ty = float(self.son_xy_anlik[1]) + Cfg.APPROACH_LEAD_S * float(self.son_hiz[1])
        else:
            tx, ty = float(est[0]), float(est[1])                 # ram / fallback: 2sn lead
        ex = tx - float(drone_pos[0])                             # HEDEFE hata (yaw/handoff/FOV/log)
        ey = ty - float(drone_pos[1])
        d_h = math.hypot(ex, ey)
        # POZISYON KOMUT hatasi (PD bunu surer): ram'de hedefe git; approach-only'de standoff'a.
        if not Cfg.GPS_TERMINAL_STRIKE:
            if d_h > 1e-6:
                _ux, _uy = ex / d_h, ey / d_h
                _dcmd = d_h - Cfg.APPROACH_STANDOFF              # +: yaklas, 0: dur, -: cok yakin -> geri cekil
                ex_cmd, ey_cmd = _ux * _dcmd, _uy * _dcmd
            else:
                ex_cmd = ey_cmd = 0.0
        else:
            ex_cmd, ey_cmd = ex, ey

        # ZORUNLU None-init (ucus logu icin): strike/alc bloklari calismazsa bile bu
        # degiskenler 559'daki log dict'inde referanslanir -> NameError'i onle (yoksa
        # beyin_lock'taki try/except o log satirini sessizce yutar).
        ex_s = ey_s = d_s = ux = uy = v_close = vdx = vdy = ax = ay = a_fwd = a_right = None
        alc_oncelik = None

        # 4) HANDOFF (histerezisli) -> durum: ARAMA / KILIT
        if not self.handoff and d_h < Cfg.HANDOFF_RANGE:
            self.handoff = True
        elif self.handoff and d_h > Cfg.HANDOFF_EXIT:
            self.handoff = False
            self.handoff_announced = False
        self.durum = "KILIT" if self.handoff else "ARAMA"

        # 5) turev (EMA) — YATAY komut hatasi (standoff'lu) uzerinden; dikey ez uzerinden
        de = self._derivative((ex_cmd, ey_cmd, ez), t)

        # 6) yatay: KOMUT hatasini (standoff) ve turevini govde cercevesine cevir
        e_fwd, e_right = world_to_body(ex_cmd, ey_cmd, drone_yaw)
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

        # 7b) DIKEY-YATAY AYRISTIRMA DUZELTMESI (tani verisiyle kanitlandi):
        #     Drone hedefin irtifasini ASTIGINDA (ez<0) hizli ileri-ucus YUKARI TASIMA
        #     uretip alcalmayi engelliyordu (THR=-0.40'a ragmen +3 m/s tirmanis). Cozum:
        #     ne kadar ustteyse kovalamayi (pitch/roll) o kadar KIS -> tasima dussun ->
        #     drone alcalabilsin. Hedef irtifasina donunce tam kovalama geri gelir.
        if ez < 0.0:
            alc_oncelik = clamp(1.0 + ez / 800.0, 0.15, 1.0)   # ez=-8 m'de %15'e iner
            pitch_raw *= alc_oncelik
            roll_raw  *= alc_oncelik

        # 8) irtifa (PID) — Z_SIGN ile dikey yon. P: KP_Z*ez, I: kalici acigi kapatir
        #    (ileri-ucus tasimasina karsi ~14 m ustte dengelenmeyi onler), D: KD_Z*de[2].
        #    KP_Z/KD_Z DEGISMEZ; THR_DN=-1.0 tam inme yetkisi.
        #    Anti-windup: integrali sadece hedefe MAKUL yakinken (|ez|<band) biriktir ve
        #    clamp'le; uzaktayken (tirmanis) sifirla ki windup olmasin.
        if abs(ez) < Cfg.INT_Z_BAND:
            self._ez_int = clamp(self._ez_int + ez * Cfg.DT, -Cfg.INT_Z_MAX, Cfg.INT_Z_MAX)
        else:
            self._ez_int = 0.0
        thr_raw = clamp(Cfg.Z_SIGN * (Cfg.KP_Z * ez + Cfg.KI_Z * self._ez_int + Cfg.KD_Z * de[2]),
                        Cfg.THR_DN, Cfg.THR_UP)

        # 9) yaw: nazikce burnu hedefe cevir (handoff'ta kamera ortalansin)
        bearing = math.atan2(ey, ex)
        yaw_err = deadband(wrap_pi(bearing - drone_yaw), Cfg.YAW_DEADBAND)
        yaw_raw = Cfg.YAW_SIGN * clamp(Cfg.KP_YAW * yaw_err, -Cfg.YAW_MAX, Cfg.YAW_MAX)

        # 10) deadband (cok yakinda yatay jitter onle)
        if d_h < Cfg.POS_DEADBAND:
            pitch_raw = 0.0
            roll_raw = 0.0

        # 10b) TERMINAL VURUS (COMMIT / RAM) — hedefin ICINE dal, delip GEC (hit).
        #      >>> VARSAYILAN KAPALI (Cfg.GPS_TERMINAL_STRIKE=False): GPS VURMAZ, sadece yaklasir;
        #          saldiri KAMERA verisiyle (gorsel faz) yapilir. Blok korunur, bayrakla acilir. <<<
        #      v_des = v_hedef + v_close*LOS.  v_close = clamp(KP_CLOSE*d, V_CLOSE_MIN, V_CLOSE):
        #      uzakta hizli, YAKINDA TABAN'da (V_CLOSE_MIN) kalir -> temasta 0'a inmez, drone
        #      hedefin icine itmeye devam eder (GERI ATILMA yok). Hedef hizini esledigimiz
        #      icin lead OTOMATIK. ivme = KV*(v_des - v_own). Cok yakinda (d_s<COMMIT_RANGE)
        #      YANAL (LOS'a dik) ivme kisilir -> LOS singula rite salinimi kovalanmaz, DUZ dalinir.
        if (Cfg.GPS_TERMINAL_STRIKE and d_h < Cfg.STRIKE_RANGE
                and self.son_hiz is not None and self.son_xy_anlik is not None):
            # LOS = lead'siz ANLIK hedefe (carpisma icin gercek yon; lead son_temiz'de DEGIL).
            ex_s = float(self.son_xy_anlik[0] - drone_pos[0])
            ey_s = float(self.son_xy_anlik[1] - drone_pos[1])
            d_s = math.hypot(ex_s, ey_s)
            ux, uy = ex_s / max(d_s, 1e-6), ey_s / max(d_s, 1e-6)      # LOS birim (dunya)
            # BURUN/KAMERA DUZELTMESI: terminalde burun ANLIK hedefe doner (2sn-lead
            # noktasina DEGIL). Carpisma lead'i hiz-eslemede ZATEN var (v_des =
            # v_hedef + v_close*LOS); burnu lead'e cevirmek kamerayi gercek hedeften
            # kaciriyordu (yakin mesafede manevrali hedefte ~50 dereceye varan sapma
            # -> gorsel temas kaybi). Kamera gorsel fazin sensorudur; hep hedefte kalsin.
            bearing = math.atan2(ey_s, ex_s)
            yaw_err = deadband(wrap_pi(bearing - drone_yaw), Cfg.YAW_DEADBAND)
            yaw_raw = Cfg.YAW_SIGN * clamp(Cfg.KP_YAW * yaw_err, -Cfg.YAW_MAX, Cfg.YAW_MAX)
            v_close = clamp(Cfg.KP_CLOSE * d_s, Cfg.V_CLOSE_MIN, Cfg.V_CLOSE)  # TABAN'li -> ram
            vdx = float(self.son_hiz[0]) + v_close * ux               # istenen hiz (cm/s, dunya)
            vdy = float(self.son_hiz[1]) + v_close * uy
            # 3D CARPMA (DIKEY): hedefin uzerinden/altindan GECMESIN -> mevcut irtifa-PID'ine
            # dikey KAPANIS feedforward'u EKLE (PID'i ezme -> pozisyon+lift telafisi korunur).
            # ez=dikey hata, d3d=3B mesafe, losz=LOS dikey bileseni. hedefin dikey hizini esle
            # (son_hiz_z) + v_close*losz ile dikeyi yatayla SENKRON kapat. throttle olcegi: /VZ_MAX.
            d3d = math.hypot(d_s, ez)
            losz = ez / max(d3d, 1e-6)
            thr_ff = (float(self.son_hiz[2]) + v_close * losz) / Cfg.VZ_MAX
            thr_raw = clamp(thr_raw + Cfg.Z_SIGN * thr_ff, Cfg.THR_DN, Cfg.THR_UP)
            ax = Cfg.KV_STRIKE * (vdx - float(v_own[0]))               # ivme = KV*(v_des - v_own)
            ay = Cfg.KV_STRIKE * (vdy - float(v_own[1]))
            if d_s < Cfg.COMMIT_RANGE:                                 # COMMIT: yanal ivmeyi kis
                along = ax * ux + ay * uy                              # LOS boyunca (ram) bilesen
                kperp = clamp(d_s / Cfg.COMMIT_RANGE, 0.25, 1.0)       # temasta %25'e iner
                ax = along * ux + (ax - along * ux) * kperp
                ay = along * uy + (ay - along * uy) * kperp
            am = math.hypot(ax, ay)
            if am > Cfg.A_MAX_STRIKE:                                  # TOPLAM ivme tavani
                ax *= Cfg.A_MAX_STRIKE / am; ay *= Cfg.A_MAX_STRIKE / am
            a_fwd, a_right = world_to_body(ax, ay, drone_yaw)          # dunya -> govde
            pitch_raw = Cfg.PITCH_SIGN * clamp(a_fwd  / Cfg.A_MAX_STRIKE, -1.0, 1.0) * Cfg.STRIKE_TILT
            roll_raw  = Cfg.ROLL_SIGN  * clamp(a_right / Cfg.A_MAX_STRIKE, -1.0, 1.0) * Cfg.STRIKE_TILT

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

        # --- UCUS LOGU: ana yol (APPROACH/STRIKE) tam teshis satiri ---
        if Cfg.LOG_ENABLE:
            mod = "STRIKE" if (Cfg.GPS_TERMINAL_STRIKE and d_h < Cfg.STRIKE_RANGE
                               and self.son_hiz is not None
                               and self.son_xy_anlik is not None) else "APPROACH"
            sh = self.son_hiz; sx = self.son_xy_anlik; sm = self.son_ham
            self._log(mod, {
                "t_perf": t, "kaynak": self.kaynak, "durum": self.durum,
                "handoff": int(self.handoff), "fresh": int(self._fresh), "none_count": self.none_count,
                "drone_x": drone_pos[0], "drone_y": drone_pos[1], "drone_z": drone_pos[2],
                "drone_yaw_deg": yaw_m, "drone_yaw_rad": drone_yaw, "drone_speed": spd,
                "vown_x": v_own[0], "vown_y": v_own[1],
                "est_x": est[0], "est_y": est[1], "est_z": est[2], "z_ref": z_ref,
                "xy_anlik_x": (sx[0] if sx is not None else None),
                "xy_anlik_y": (sx[1] if sx is not None else None),
                "son_z_anlik": self.son_z_anlik,
                "son_hiz_x": (sh[0] if sh is not None else None),
                "son_hiz_y": (sh[1] if sh is not None else None),
                "son_hiz_z": (sh[2] if sh is not None else None),
                "son_ham_x": (sm[0] if sm is not None else None),
                "son_ham_y": (sm[1] if sm is not None else None),
                "son_ham_z": (sm[2] if sm is not None else None),
                "ex": ex, "ey": ey, "ez": ez, "d_h": d_h, "e_fwd": e_fwd, "e_right": e_right,
                "vcap": vcap, "mag_scale": mag_scale, "alc_oncelik": alc_oncelik, "ez_int": self._ez_int,
                "d_s": d_s, "v_close": v_close, "vdx": vdx, "vdy": vdy, "ax": ax, "ay": ay,
                "a_fwd": a_fwd, "a_right": a_right,
                "bearing": bearing, "yaw_err": yaw_err,
                "thr_raw": thr_raw, "pitch_raw": pitch_raw, "roll_raw": roll_raw, "yaw_raw": yaw_raw,
                "thr_cmd": self.prev['thr'], "pitch_cmd": self.prev['pitch'],
                "roll_cmd": self.prev['roll'], "yaw_cmd": self.prev['yaw'],
                "drone_pos": drone_pos, "drone_yaw": drone_yaw,   # _log: truth + nose_off_true icin
            })


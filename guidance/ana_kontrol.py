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
            -> set_gorsel_tespit) -> _gorsel_guduum -> guidance/ibvs_gorsel.py
            (BASIT IBVS: goruntu merkezi -> bbox merkezi cizgisi; acisi+buyuklugu
            komuta cevrilir). Kayipta: hover -> (OTO'da) GPS'e geri don.
  Otomatik gecis (vis_mode=OTO): AUTO_VISUAL_HANDOFF + ard arda VIS_N_LOCK
  gecerli tespit + handoff yakinligi. Manuel: set_vis_mode GPS/GORSEL zorlar.
  NOT (2026-07-07): eski PN/PNG gorsel yigini (LOS/Omega/kapanma/look-up/
  soft-start/lead-yaw/alt-FSM) kullanici karariyla KOMPLE SILINDI -> git gecmisi.

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
from collections import deque
import numpy as np
from fusion.inovasyonlu_j_v2 import GNSSDuzeltici as V2Filtre   # v2: tek uretim filtresi
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
    # ESKI PNG kolonlari (PN yigini 2026-07-07 SILINDI): sema uyumu icin durur, BOS yazilir.
    "png_R_m", "png_Vc", "png_omega",
    # KILITLENME ISTERI (sartname 6.1.2/6.1.4): vis_faz eski alt-FSM'indi (artik BOS);
    # kilit_win_s = 10 sn penceredeki kumulatif kilit suresi (sayac YASIYOR, salt gozlem).
    "vis_faz", "kilit_win_s",
    # HAM normalize yatay tespit konumu (vis_ey zaten dikey) — pervane yanlis-poz
    # konumlamasi icin (EMA'siz; vis_ex EMA'li oldugundan kose kumeleri bulaniktir).
    "vis_cx",
    # BASIT IBVS (2026-07-07): merkez->bbox cizgisi buyuklugu + acisi (SONA eklendi; sema-guvenli)
    "ibvs_r", "ibvs_aci",
]


# ==========================================================
# CONFIG — FAZ BANTLARINA AYRILMISTIR (hangi sabit hangi fazda calisir):
#   [ORTAK]         : her fazda gecerli (birim/isaret/dongu/komut tavani/log)
#   [GPS-YAKLASMA]  : YALNIZ durum != GORSEL_GUDUM iken (kalkis, standoff,
#                     fren/speed_cap, PD, None yonetimi). Gorsel faza KARISMAZ.
#   [GORSEL]        : basit IBVS (ibvs_gorsel.py) + kilit isteri sayaci + kayip yonetimi.
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
    # 40m -> 20m (2026-07-07 log analizi, ucus_log_20260707_200927): 40m'de OTO
    # gorsele devredince PNG aralikli tespitle (~%32 @30m) kararli carpisma rotasi
    # kuramiyordu -> hedefi eksen disi birakip UZAKLASIYORDU (her blokta mesafe artti,
    # 17->86m; |nose_off| 89°'ye) -> GPS'e donup ZIPLIYORDU. GPS mukemmel nisan aliyor;
    # gorsel o mesafede tutamiyor. Cozum: GPS hedefi 20m'ye kadar merkezde GETIRSIN
    # (bbox ~%2.2, tespit yogun), SONRA gorsel devralsin. self.durum GPS komutunu
    # DEGISTIRMEZ (KILIT==ARAMA yaklasma; sadece rozet/handoff kapisi).
    HANDOFF_RANGE = 2000.0      # cm (20m); tespit menziline gore TUNE et
    HANDOFF_EXIT  = 3000.0      # cm (30m); bu mesafenin disina cikinca handoff iptal (10m band)
    # OTOMATIK GORSEL DEVRI (YOLO kilidi + yakinlik -> GORSEL_GUDUM).
    # ACIK (2026-07-06): gorsel faz olgunlasti (PNG carpisma-rotasi + kamera-menzil).
    # Yakinlik (d_h<HANDOFF_RANGE) + ard arda VIS_N_LOCK gecerli tespit saglaninca
    # saldiri KAMERAYA devredilir -> otonom angajman/vurus zinciri (Ister 9/10).
    # Manuel GORSEL switch (set_vis_mode "GORSEL") bu bayraktan BAGIMSIZ calisir.
    AUTO_VISUAL_HANDOFF = True

    # NOT (2026-07-06 temizligi): Eski "GPS terminal vurus/ram" blogu (GPS_TERMINAL_STRIKE
    # + STRIKE_* sabitleri) SILINDI — gorev mimarisinde saldiri KAMERA verisiyle yapilir
    # (gorsel PNG fazi). Ihtiyac olursa git gecmisinde: adim() 10b blogu.

    # --- YAKLASMA HIZI PROFILI / FRENLEME (overshoot guard) ---
    # speed_cap(): hedefe BRAKE_DIST altinda yaklastikca hiz tavani V_CAP_FAR'dan
    # V_CAP_NEAR'a kademeli iner; hiz tavani asilirsa pitch sonumlenir (fren).
    # YALNIZ GPS-yaklasma fazinda calisir; gorsel fazda devrede DEGIL. Etkisi:
    # gorsel handoff ANINDAKI hizi/geometriyi bu profil belirler (V_CAP_NEAR
    # dusukse handoff yavas ama kontrollu baslar).
    V_CAP_FAR  = 2500.0         # cm/s uzakta (120km/h = 3333 cm/s'in altinda)
    V_CAP_NEAR = 500.0          # cm/s handoff yakininda
    BRAKE_DIST = 7000.0         # cm; bu mesafe altinda hizi kademeli dusur

    # --- ANTI-OVERSHOOT STANDOFF (B) ---
    # GPS hedefin USTUNE ucup GECMESIN diye pozisyon komutu hedefe DEGIL, hedeften
    # APPROACH_STANDOFF kadar GERIDEKI noktaya surulur -> drone standoff'ta durur/paceler,
    # hedef HEP ONDE (FOV'da) kalir; gorsel faz devralana kadar gorsel temas korunur
    # (nose_off ~180 flip'leri biter). KISA lead (APPROACH_LEAD_S), 2sn tam lead'in
    # manevrada nisan noktasini savurup drone'u hedefin KARSISINA atmasini onler.
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
    # BILINEN GERILIM (6 Tem log analizi): bu ofset yuzunden gorsel handoff hedefin
    # ~5-8 m ALTINDA baslar -> PNG'nin endgame'de kapatmasi gereken dikey acik.
    # Kucultmek kadraji bozabilir; degistirirken kamera cerceveleme ile birlikte tune et.
    APPROACH_ALT_OFFSET = 500.0  # cm (5 m); drone hedefin ALTINDA kalacagi ASGARI dikey ofset
                                 # (LOOKUP_ELEV_DEG menzil-olcekli offset bunun UZERINE cikar)

    # --- LOOK-UP GEOMETRISI (asagi-bakma/clutter cozumu) ---
    # PROBLEM: avci hedefin USTUNDEN takip edince kamera ASAGI bakar; hedef arazi
    # dokusu (clutter) onunde dusuk kontrast -> YOLO tespiti kopar. ALTTAN (look-up)
    # bakista arka plan GOKYUZU -> siluet, yuksek kontrast + planform izdusumu maksimum.
    # COZUM: avci hedefin ALTINDA kalsin, LOS YUKSELIS acisi her an >= LOOKUP_ELEV_DEG.
    # SABIT irtifa farki YETMEZ: ayni dh uzak menzilde kucuk aci verir -> menzil-olcekli:
    #   GPS fazi: z_ref = z_hedef - max(APPROACH_ALT_OFFSET, tan(eps)*d_h)  [aci >= eps garanti]
    #   Gorsel faz (PNG): asin(u_hat[2]) < eps iken alcalma bias'i (u_hat[2]=sin(elev)).
    LOOKUP_ELEV_DEG   = 6.0      # eps; LOS yukselis aci SETPOINT'i (deg). 0 = look-up KAPALI.
                                # Gorsel faz dikeyi bu aciyi TUTAR (alt->alcal, ust->tirman).
                                # 5-8 tavsiye (kucuk=zayif siluet, buyuk=cok alttan; 7 Tem: 8->6
                                # cunku v1 tek-yon bias hedefi ust kenara atiyordu, ey_ort -0.19)
    LOOKUP_MIN_ALT_CM = 800.0   # cm; alcalma TABAN irtifasi (yere cakilma korumasi; taban
                                # altinda ALCALMA dayatilmaz ama tirmanisa izin var)

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
    YAW_MAX   = 0.60           # burnu (kamerayi) hedefe donuk tutar (sim-tune 2026-07-03: 0.30->0.45;
                               # 7 Tem: 0.45->0.60 — canli logda gorsel kayip anlarinin %42'sinde yaw
                               # DOYGUNLUKTA (0.45'e dayanmis) + hedef kenarda -> tavan yukseltildi).

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

    # ================= [GORSEL] (basit IBVS + kilit isteri sayaci) =================
    # --- GORSEL GUDUM — gorsel temas SONRASI yonelim (YALNIZCA kamera) ---
    # Gecis: conf>=VIS_CONF_MIN kareler ard arda VIS_N_LOCK olunca GORSEL_GUDUM'a gec.
    # Kayipta: HOVER (yeniden tespit bekle) -> (OTO'da) VIS_LOST_TO_GPS_S sonra GPS'e don.
    VIS_MODEL_PATH   = os.path.join(_PROJ_ROOT, "models", "best.pt")   # tespit modeli (task=detect, sinif: talon)
    # PERVANE MASKESI (yanlis-pozitif engelleme): avcinin KENDI pervanesi arada bir
    # "ucak" olarak algilaniyor (dedektor sinif-agnostik en-yuksek-conf'u secer -> bir
    # karede pervane hedefi bastirabilir). Pervane KADRAJDA SABIT konumdadir (kendi
    # aracimizda). Bu bolgelerde MERKEZI olan kutular dedektorde ELENIR (argmax ONCESI).
    # Normalize (0..1) dikdortgen listesi [x0,y0,x1,y1]; bos liste = kapali.
    # DEGER: 7 Tem log analizi — 60 kesin yanlis-poz (gercek hedef 126m uzak/kadraj disi
    # iken conf~0.48 tespit) SAG-ALT'ta kumelendi (ex~0.75-1.0, ey~0.25). Canli FPV'de
    # dogrula/rafine et (arayuz maskeyi kirmizi tarama ile cizer; vis_cx/vis_ey loglanir).
    PROP_MASKE = [(0.80, 0.55, 1.0, 0.95)]   # sag-alt kose (on-sag pervane)
    VIS_CONF_MIN     = 0.45     # kilit/komut icin asgari guven
    VIS_N_LOCK       = 5        # ardisik gecerli-tespit -> GORSEL_GUDUM (yanlis-poz bastir)
    VIS_STALE_S      = 0.5      # tespit bu sureden eskiyse yok say (kayip mantigi devreye girer)
    VIS_LOST_TO_GPS_S = 2.0     # kayip bu sureyi asarsa GPS guduumune GERI DON (yeniden yaklas +
                               # gorseli yeniden kilitle). 0 = asla donme. Sure _vis_lost_count
                               # ile olculur -> son gorusten itibaren ~(VIS_STALE_S + bu) toplam
                               # kayipta doner. Kayip boyunca komut = HOVER (yerinde bekle).
    VIS_EMA          = 0.4      # ex/ey EMA yumusatma (tek-kare yanlis tespiti bastir)
    # --- BASIT IBVS (2026-07-07): goruntu merkezi -> bbox merkezi cizgisi ---
    # TEK gorsel yasa (guidance/ibvs_gorsel.py): cizginin YATAY bileseni yaw'a,
    # DIKEY bileseni throttle'a gider; BUYUKLUGU (merkeze sapma "mesafesi") ileri
    # itkiyi kisar (once ortala, sonra ilerle). Roll HEP 0 (bank yok — eski PN'de
    # bank hedefi kadrajdan atip kamerayi yere ceviriyordu). Kamera +25 tilt'li
    # oldugundan hedefi MERKEZDE tutmak araci hedefin ALTINDA tutar (gokyuzu
    # arka plan / alttan yaklasma) — ekstra dikey geometri kodu GEREKMEZ.
    IBVS_K_YAW       = 0.8      # yatay kazanc: yaw = SIGN*K*ex (clamp +-YAW_MAX) ⚙
    IBVS_SIGN_YAW    = +1.0     # ex>0 (hedef SAGDA) -> burnu SAGA cevir; ters tepki gorursen -1
    IBVS_K_DIKEY     = 1.2      # dikey kazanc: thr = SIGN*K*(-ey) (clamp THR_DN..THR_UP) ⚙
    IBVS_SIGN_DIKEY  = +1.0     # hedef YUKARIDA (ey<0) -> TIRMAN (thr>0; GPS faziyla ayni kanon).
                                # SIM'de dikey TERS tepki gorursen -1 yap (tek isaret, tek yer).
    IBVS_ILERI       = 0.45     # sabit ileri itki komutu (0..1; pitch kanali) ⚙
    IBVS_MERKEZ_FREN = 1.0      # sapma buyudukce ileri kis: pitch *= max(0, 1 - FREN*r).
                                # 0 = hep tam gaz; buyuk deger = once ortala sonra ilerle ⚙

    # (ESKI "GORSEL PNG" blogu — VIS_LAW/PN_N/PN_A_MAX/PN_TILT/TRACK_TILT/VZ_MAX/
    #  SPAN_CM/R_EMA/OMEGA_*/W_PX_MIN/VC_CAP — 2026-07-07 SILINDI; git gecmisinde.)
    # (ESKI kapanma/soft-start/look-up sabitleri — VIS_KP_CLOSE/KV_CLOSE/TERM_PCT/
    #  COMMIT_PCT/TAKIP_VC/SOFTSTART_*/COMMIT_LAT/TAU_Z/PN_SIGN_VZ/LOOKUP_VZ/HOLD_PCT —
    #  2026-07-07 SILINDI; git gecmisinde. LOOKUP_ELEV_DEG yalniz GPS z_ref'te yasar.)

    # --- KILITLENME ISTERI SAYACI (sartname 6.1.2 + 6.1.4, Sekil 2) — SALT GOZLEM ---
    # Gudume KARISMAZ (eski YAKLASMA/TAKIP/TERMINAL alt-FSM'i silindi); arayuz/video
    # kaniti icin sayilir: kirmizi kilit dortgeni + 5/10 sn pencere + ANGAJMAN cipi.
    # Kilit tanimi (her tik): AH (bbox) TAMAMEN Hedef Vurus Alani (AV) icinde (dort kenar
    # da; MERKEZ degil) VE bbox EN AZ BIR ekseninde >= VIS_LOCK_PCT. Kesintili kilit sayilir.
    VIS_LOCK_PCT     = 0.06     # bbox eksen orani esigi. Sartname kurali >=0.05 ama
                                # tam sinirda calisan algoritma hakem incelemesinde
                                # "hatali kilit paketi" sayilabilir -> tavsiye edilen 0.06
    VIS_AV_X         = 0.25     # AV yatay kenar payi (sartname sabiti: %25-%75 bandi)
    VIS_AV_Y         = 0.10     # AV dikey kenar payi (sartname sabiti: %10-%90 bandi)
    VIS_WIN_S        = 10.0     # degerlendirme penceresi (sartname sabiti)
    VIS_WIN_NEED_S   = 5.0      # pencerede gereken kumulatif kilit (sartname sabiti)
    # --- ZAMAN-TABANLI SEGMENT MOTORU (2026-07-08): kilit suresi wall-clock damgalarla ---
    # Gecerli kilit karesinden sonraki bosluk BRIDGE_S altiysa koprulenir (kilide sayilir);
    # koprulenen toplam bosluk segmentin en fazla BRIDGE_PCT'i olabilir; segment bas/sonu
    # GERCEK gecerli tespit (temiz uc). Bosluk BRIDGE_S'i asarsa segment son gecerlide kapanir.
    VIS_LOCK_BRIDGE_S   = 0.2    # gecerli kareler arasi koprulenebilir azami bosluk (s)
    VIS_LOCK_BRIDGE_PCT = 0.05   # koprulenen toplam bosluk / segment suresi ust siniri (%5)
    # --- SAHTE-POZITIF KAPISI (2026-07-08, SAF GORSEL — PnP/GPS DEGIL): uzak clutter/pervane
    # >=%6 in-AV cikabiliyor (110m'de %6 fiziksel imkansiz). Gecerli kilit karesi icin EK sart:
    # (1) conf >= esik; (2) bbox en/boy (w/h) talonun makul araliginda (talon GENIS; dar/dikey
    # = sahte). 8 Tem olcum: gercek yakin conf 0.56-0.89 asp 1.6-3.2; sahte uzak asp 0.5-0.9 dikey.
    VIS_LOCK_CONF_MIN   = 0.50   # kilit karesi asgari conf (sahte-pozitif kapisi)
    VIS_LOCK_ASPECT_MIN = 1.5    # bbox en/boy (w/h) alt siniri UZAK/kucuk bbox (talon GENIS; dikey=sahte)
    VIS_LOCK_ASPECT_MAX = 6.0    # bbox en/boy ust siniri (her iki durumda ayni)
    VIS_LOCK_ASPECT_MIN_NEAR = 0.8   # YAKIN (buyuk bbox) aspect alt siniri: terminal fazda talon
                                     # belly-on -> kare/dikey (aspect ~1.0); conf+AV zaten sahteyi
                                     # ayirir (7 Tem kosu t=44.8-45.3: conf 0.75-0.91, aspect 0.93-1.22).
    VIS_LOCK_BBOX_NEAR  = 0.05   # "yakin" esigi: bbox herhangi ekseni >= %5 -> gevsek aspect uygula
    # --- GORSEL DEVIR (handover) ESIGI (2026-07-08): OTO/GPS'ten gorsele gecis, hedef YETERINCE
    # YAKIN+BUYUK olana kadar OLMAZ. Devir sarti: talon_gate + bbox >= VIS_HANDOFF_PCT (kilit %6'nin
    # altinda ama clutter'dan yukarida) + ard arda VIS_N_LOCK kare STABIL. bbox kucukse (uzak) IBVS
    # mesafe kapatamaz -> GPS/OTO yaklasmaya devam. Devir-alti'na (histerezis) dusulurse GPS'e revert.
    VIS_HANDOFF_PCT   = 0.035    # gorsele devir icin asgari bbox eksen orani (~%3.5; yakin+buyuk)
    VIS_REVERT_HYST   = 0.7      # revert esigi = VIS_HANDOFF_PCT * bu (histerezis; salinim onler)


# ==========================================================
# HELPERS  (faz1_gnss_yaklasma'dan AYNEN)
# ==========================================================
def talon_gate(tespit):
    """SAHTE-POZITIF KAPISI (SAF GORSEL — PnP/GPS DEGIL): tespit conf + en-boy (w/h) talon
    araliginda mi. True = gercek talon adayi -> KILIT degerlendirme VE gorsel guduum (IBVS)
    girdisi VE CSV isareti bunu kullanir (TEK dogruluk kaynagi). False = sahte (uzak clutter/
    pervane: zayif conf veya kucuk-bbox'ta dar/dikey en-boy). ASPECT alt siniri BBOX-KOSULLU:
    yakin (buyuk bbox) talon belly-on gorunup kare/dikeye duser -> gevsek; uzak/kucuk -> siki."""
    if tespit is None:
        return False
    try:
        h = float(tespit["h"])
        w = float(tespit["w"])
        if h <= 0:
            return False
        if float(tespit.get("conf", 0.0)) < float(Cfg.VIS_LOCK_CONF_MIN):
            return False                                   # conf kapisi (DEGISMEDI) — sahtenin ana filtresi
        aspect = w / h
        # BBOX-KOSULLU ASPECT ALT SINIRI: yakin terminal fazda (bbox buyuk) talon belly-on ->
        # aspect ~1.0; sabit [1.5,6] gercek yakin talonu elerdi (7 Tem: conf 0.75-0.91, bbox %9-11,
        # menzil 5-7m). bbox herhangi ekseni >= VIS_LOCK_BBOX_NEAR ise alt sinir gevser
        # (VIS_LOCK_ASPECT_MIN_NEAR); kucuk/UZAK bbox'ta [1.5,6] KALIR (orada aspect sahte ayrimi
        # icin degerli). Ust sinir (6.0) her iki durumda ayni.
        W = float(tespit.get("W", 0.0)); H = float(tespit.get("H", 0.0))
        yatay = (w / W) if W > 0 else 0.0
        dikey = (h / H) if H > 0 else 0.0
        buyuk = max(yatay, dikey) >= float(Cfg.VIS_LOCK_BBOX_NEAR)
        amin = float(Cfg.VIS_LOCK_ASPECT_MIN_NEAR) if buyuk else float(Cfg.VIS_LOCK_ASPECT_MIN)
        return amin <= aspect <= float(Cfg.VIS_LOCK_ASPECT_MAX)
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return False


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
        self.son_xy_anlik = None        # J'nin ANLIK (lead'siz) yatay konumu (cm) - TESHIS-only (terminal artik son_temiz)
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

        # --- GORSEL GUDUM (basit IBVS) durumu ---
        # son_tespit: server.dedektor_dongusu'nin beyin_lock icinde yazdigi son bbox dict.
        self.son_tespit = None          # {cx,cy,w,h,conf,W,H,t} | None
        self.son_tespit_t = None        # o tespitin perf_counter zamani (bayatlik kontrolu)
        self._vis_pos_count = 0         # ardisik gecerli-tespit (kilit histerezisi)
        self._vis_lost_count = 0        # ardisik kayip (hover -> GPS'e donus karari)
        self._vis_ilan = False          # "GPS kesildi" anonsu bir kez basilsin
        self.ibvs = AvciIBVS()          # merkez->bbox cizgisi (tek gorsel yasa; basit IBVS)
        self.ibvs_tlm = {}              # son IBVS telemetrisi (server build_telemetry okur; salt-okunur)
        self.vis_mode = "OTO"           # guduum pipeline switch (test): OTO | GPS | GORSEL
        # --- KILITLENME ISTERI SAYACI (sartname 6.1.2/6.1.4; SALT GOZLEM, komuta girmez) ---
        self.kilit_win = deque()        # KAPALI temiz segmentler (bas, son) — son VIS_WIN_S penceresi
        self.kilit_sure = 0.0           # penceredeki kumulatif kilit suresi (s)
        self.kilit_en_uzun = 0.0        # penceredeki EN UZUN tek segment (s) = tek-geciste potansiyel
        self.kilit_anlik = False        # bu tik kilit kosulu (AV icinde + boyut >= LOCK_PCT)
        self.kilit_ok = False           # LATCH: pencere isteri (>=WIN_NEED_S) saglandi
        self.kilit_boyut = None         # bu tik bbox eksen orani max(w/W, h/H) (telemetri)
        self.kilit_sahte = False        # bu tik >=%6+AV ama sahte-pozitif kapisinda ELENDI mi
        self.kilit_enboy = None         # bu tik bbox en/boy orani w/h (telemetri)
        self._kseg_reset()              # zaman-tabanli segment motoru ic durumu

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
        self.ibvs_tlm = {}
        # kilitlenme isteri sayaci: yeni gorev -> pencere ve latch dahil taze basla
        self.kilit_win.clear()
        self.kilit_sure = 0.0
        self.kilit_en_uzun = 0.0
        self.kilit_anlik = False
        self.kilit_ok = False
        self.kilit_boyut = None
        self._kseg_reset()
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
            sonuc = self.filtre.guncelle(ham[0], ham[1], ham[2], time.time())  # adaptif dt: wall-clock
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
                    # lead'siz ANLIK yatay konum. 2026-07-08'den beri terminal LOS+menzil BUNU
                    # DEGIL son_temiz (lead) kullanir (olcum: anlik nisan 20.5m/menzil -12.8m vs
                    # lead 3.9m/-0.9m). son_xy_anlik yalniz TESHIS icin loglanir (xy_anlik_x/y).
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
        # switch = yeni deneme -> kilitlenme penceresi ve latch de taze baslasin
        self.kilit_win.clear()
        self.kilit_sure = 0.0
        self.kilit_en_uzun = 0.0
        self.kilit_anlik = False
        self.kilit_ok = False
        self.kilit_boyut = None
        self._kseg_reset()
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
            # vis_ex: IBVS'in EMA'li yatay hatasi (yaw kanali girdisi); vis_ey: ham
            # tespitten normalize dikey hata (ayni tanim: (cy-H/2)/(H/2)).
            "vis_ex": self.ibvs.ex_f,
            "vis_ey": (((float(tespit["cy"]) - float(tespit["H"]) / 2.0)
                        / (float(tespit["H"]) / 2.0))
                       if (tespit is not None and float(tespit.get("H", 0) or 0) > 1) else None),
            "vis_gordu": 1 if tespit is not None else 0,
            # kilitlenme isteri sayaci (sartname isteri teshisi; vis_faz kolonu bos kalir)
            "kilit_win_s": self.kilit_sure,
            # HAM normalize yatay konum (pervane konumlamasi; vis_ey dikey karsiligi)
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
            # merkez->bbox cizgisi: buyukluk (0=merkez) + aci (0=sag, +90=yukari)
            d["ibvs_r"] = it.get("buyukluk"); d["ibvs_aci"] = it.get("aci_deg")
        self._log("VISUAL", d)

    # ----------------------------------------------------------------
    #  KILITLENME PENCERESI (sartname 6.1.4): her gorsel tikte kilit kosulunu
    #  degerlendir + 10 sn kayan penceredeki KUMULATIF kilit suresini guncelle.
    #  Kilit kosulu: hedef MERKEZI AV icinde (yatay %25-%75, dikey %10-%90) VE
    #  bbox EN AZ BIR eksende >= VIS_LOCK_PCT. Kesintili kilit sayilir (sartname
    #  ornegi: 1+2+2 sn = 5 sn -> gecerli). VIS_WIN_NEED_S dolunca kilit_ok
    #  LATCH'lenir -> arayuz ANGAJMAN cipi / kirmizi dortgen / olay kaydi.
    #  SALT GOZLEM: sonucu hicbir kontrol komutuna GIRMEZ (basit IBVS tek yasa).
    # ----------------------------------------------------------------
    def _kseg_reset(self):
        """Zaman-tabanli segment motoru ic durumu (kilit_win ayrica temizlenir)."""
        self._kseg_start = None          # ACIK segment basi (ilk gecerli kare)
        self._kseg_last = None           # ACIK segment SON GECERLI karesi (temiz uc)
        self._kseg_bridged = 0.0         # segmentte koprulenen toplam bosluk (s)
        self._kseg_prev_valid = False    # onceki tik gecerli miydi (kesintisiz kapsama ayrimi)
        self._kseg_prev_t = None         # onceki tik zamani (sureklilik/geri-saat korumasi)

    def _kseg_kapat(self):
        """ACIK segmenti SON GECERLI karede finalize et (temiz uc) ve pencereye ekle."""
        if (self._kseg_start is not None and self._kseg_last is not None
                and self._kseg_last > self._kseg_start):
            self.kilit_win.append((self._kseg_start, self._kseg_last))
        self._kseg_start = None
        self._kseg_last = None
        self._kseg_bridged = 0.0

    def _kseg_metrik(self, t):
        """Pencere(VIS_WIN_S) icindeki KAPALI + ACIK segmentlerden kilit_sure/en_uzun/ok."""
        win = self.kilit_win
        pb = t - float(Cfg.VIS_WIN_S)
        while win and win[0][1] < pb:
            win.popleft()
        parcalar = list(win)
        if (self._kseg_start is not None and self._kseg_last is not None
                and self._kseg_last > self._kseg_start):
            parcalar.append((self._kseg_start, self._kseg_last))   # ACIK segment (son gecerliye kadar)
        sure = 0.0
        en_uzun = 0.0
        for (s, e) in parcalar:
            a = s if s > pb else pb                    # pencereye kirp
            if e > a:
                sure += (e - a)
            if (e - s) > en_uzun:                      # en uzun tek segment (kirpmasiz)
                en_uzun = e - s
        self.kilit_sure = sure
        self.kilit_en_uzun = en_uzun
        if (not self.kilit_ok) and sure >= float(Cfg.VIS_WIN_NEED_S):
            self.kilit_ok = True                       # kalici latch (gorev boyunca)
            print("[KILIT] %.0f sn pencerede %.1f sn kumulatif (zaman-tabanli segment) -> KILIT "
                  "ISTERI SAGLANDI (sartname 6.1.4: >= %.0f sn)." % (Cfg.VIS_WIN_S, sure, Cfg.VIS_WIN_NEED_S))

    def _kilit_degerlendir(self, tespit, t):
        # 1) GECERLI KILIT KARESI: taze det + AH TAMAMEN AV-ici (full-box) + en az bir eksen
        #    >= VIS_LOCK_PCT + SAHTE-POZITIF KAPISI (conf + en/boy).
        kilit = False
        self.kilit_boyut = None
        self.kilit_sahte = False
        self.kilit_enboy = None
        if tespit is not None:
            W = float(tespit.get("W", 0) or 0); H = float(tespit.get("H", 0) or 0)
            if W > 1 and H > 1:
                cxn = float(tespit["cx"]) / W; cyn = float(tespit["cy"]) / H
                wn = float(tespit["w"]) / W; hn = float(tespit["h"]) / H
                boyut = max(wn, hn)
                self.kilit_boyut = boyut
                hpx = float(tespit["h"])
                aspect = (float(tespit["w"]) / hpx) if hpx > 0 else 0.0   # en/boy w/h
                self.kilit_enboy = aspect
                av_x = float(Cfg.VIS_AV_X); av_y = float(Cfg.VIS_AV_Y)
                av_ici = (av_x <= cxn - wn / 2.0 and cxn + wn / 2.0 <= 1.0 - av_x
                          and av_y <= cyn - hn / 2.0 and cyn + hn / 2.0 <= 1.0 - av_y)
                boy_ok = boyut >= float(Cfg.VIS_LOCK_PCT)
                # SAHTE-POZITIF KAPISI (saf gorsel): >=%6+AV ama zayif conf VEYA dar/dikey
                # en-boy -> SAHTE (talon GENIS). Kilit sayilmaz; kilit_sahte isaretlenir.
                gercek = talon_gate(tespit)               # SAHTE-POZITIF KAPISI (tek kaynak)
                kilit = (av_ici and boy_ok and gercek)
                self.kilit_sahte = (av_ici and boy_ok and not gercek)
        self.kilit_anlik = kilit

        # 2) ZAMAN-TABANLI SEGMENT (wall-clock): gecerli kareler kesintisizse dogrudan uzatilir;
        #    aralarinda bosluk varsa (onceki tik gecersiz) bosluk BRIDGE_S altinda VE koprulenen
        #    toplam <= BRIDGE_PCT*segment ise koprulenir, degilse segment SON GECERLI'de kapanir.
        B = float(Cfg.VIS_LOCK_BRIDGE_S); P = float(Cfg.VIS_LOCK_BRIDGE_PCT)
        prev_t = self._kseg_prev_t
        self._kseg_prev_t = t
        if prev_t is not None and (t < prev_t or (t - prev_t) > 1.0):   # sureklilik kopmasi
            self._kseg_kapat(); self._kseg_prev_valid = False
        if self._kseg_start is not None and (t - self._kseg_last) > B:  # bosluk BRIDGE_S'i asti -> kapat
            self._kseg_kapat()
        if kilit:
            if self._kseg_start is None:
                self._kseg_start = self._kseg_last = t; self._kseg_bridged = 0.0
            elif self._kseg_prev_valid:
                self._kseg_last = t                    # kesintisiz kapsama -> uzat (bosluk yok)
            else:
                gap = t - self._kseg_last              # bosluk bitti (onceki tik gecersizdi)
                dur = t - self._kseg_start
                if (self._kseg_bridged + gap) <= P * dur:   # %5 butcesi -> kopru (kilide say)
                    self._kseg_bridged += gap; self._kseg_last = t
                else:                                  # butce asildi -> yeni segment (temiz uc)
                    self._kseg_kapat()
                    self._kseg_start = self._kseg_last = t; self._kseg_bridged = 0.0
        self._kseg_prev_valid = kilit

        # 3) pencere metrigi (kilit_sure / kilit_en_uzun / kilit_ok)
        self._kseg_metrik(t)
        return kilit

    # ----------------------------------------------------------------
    #  GORSEL GUDUM (basit IBVS) — YONELIM YALNIZCA KAMERADAN.
    #  Gorsel temas VARKEN GPS/filtre YONELIMI KULLANILMAZ (yarisma kurali;
    #  ibvs_gorsel.hesapla'ya zaten YALNIZ bbox pikselleri girer — konum/hiz
    #  parametresi imzada bile yok, kural yapisal olarak saglanir).
    #  tespit VAR -> ibvs.hesapla (merkez->bbox cizgisi -> thr/pitch/roll/yaw).
    #  tespit YOK -> HOVER (server son tespiti VIS_STALE_S boyunca sunar; buraya
    #  dusen gercek kayiptir) -> VIS_LOST_TO_GPS_S asilirsa (yalniz OTO) GPS'e
    #  GERI DON: durum=ARAMA, None dondur -> adim() GPS yoluna duser.
    #  return: (throttle,pitch,roll,yaw) | None (=GPS'e don). _send rate-limit'ler.
    # ----------------------------------------------------------------
    def _gorsel_guduum(self, tespit, t, revert_izin=True):
        # revert_izin=False (manuel GORSEL switch): kayipta GPS'e DONME, hover'da kal.
        # KILITLENME ISTERI SAYACI (sartname 6.1.2/6.1.4): SALT GOZLEM — kirmizi
        # dortgen / ANGAJMAN cipi / olay gunlugu icin sayilir, KOMUTA GIRMEZ.
        self._kilit_degerlendir(tespit, t)
        # YARISMA KURALI: gorsel temastan SONRA hareket komutu YALNIZ GORSEL veriden.
        # GPS/J (yon YA DA buyukluk) GECIRILMEZ -> diskalifiye. IBVS yalniz bbox okur.
        if tespit is not None:
            # DEVIR-ALTI KONTROL: bbox devir esiginin altina (histerezis) dustuyse hedef UZAKLASTI;
            # IBVS mesafe kapatamaz -> "kayip gibi" say (sustained ise GPS'e revert -> yeniden yaklas).
            _Wd = float(tespit.get("W", 0) or 0); _Hd = float(tespit.get("H", 0) or 0)
            _boyut = (max(float(tespit["w"]) / _Wd, float(tespit["h"]) / _Hd) if _Wd > 1 and _Hd > 1 else 0.0)
            if _boyut >= float(Cfg.VIS_HANDOFF_PCT) * float(Cfg.VIS_REVERT_HYST):
                self._vis_lost_count = 0
                komut = self.ibvs.hesapla(tespit, Cfg)
                self.ibvs_tlm = self.ibvs.durum()
                return komut
            # bbox devir-alti (hedef uzak) -> asagidaki kayip/revert yoluna DUS (hover -> GPS'e don)
        # --- KAYIP veya DEVIR-ALTI: HOVER (bekle) -> uzarsa (yalniz OTO) GPS'e don ---
        self._vis_lost_count += 1
        lost_s = self._vis_lost_count * Cfg.DT
        if (not revert_izin) or Cfg.VIS_LOST_TO_GPS_S <= 0 or lost_s <= Cfg.VIS_LOST_TO_GPS_S:
            return 0.0, 0.0, 0.0, 0.0            # hover: bekle (manuel GORSEL'de HEP)
        # UZUN kayip/devir-alti (yalnizca OTO) -> GPS guduumune GERI DON (yeniden yaklas)
        print("[GORSEL] Hedef %.1fs kayip/devir-alti -> GPS guduumune GERI DONULDU (yeniden yaklas)." % lost_s)
        self.durum = "ARAMA"
        self._vis_pos_count = 0
        self._vis_lost_count = 0
        self._vis_ilan = False
        self.ibvs.sifirla()
        # kilit penceresi temizlenir; kilit_ok LATCH'i KORUNUR (sartname isteri
        # gecmiste saglandiysa gecerli kalir; sayac yeniden dolmak zorunda degil).
        self.kilit_win.clear()
        self.kilit_sure = 0.0
        self.kilit_en_uzun = 0.0
        self.kilit_anlik = False
        self._kseg_reset()                       # segment motoru taze; kilit_ok LATCH KORUNUR
        return None                              # -> adim() GPS yoluna DUSER (bu tik)

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
        else:  # OTO — otomatik DEVIR: hedef YETERINCE YAKIN+BUYUK olunca (bbox-tabanli, saf gorsel)
            if self.durum != "GORSEL_GUDUM":
                # DEVIR SARTI: kapiyi gecen GERCEK tespit (talon_gate) VE bbox >= VIS_HANDOFF_PCT
                # (yeterince BUYUK = yakin; kilit %6'nin altinda ama clutter'dan yukarida), ard arda
                # VIS_N_LOCK kare STABIL. bbox kucukse (uzak) DEVRETME -> GPS/OTO yaklasmaya devam
                # etsin (IBVS mesafe kapatamaz, sikisir). GPS-mesafe kapisi (self.handoff) KALDIRILDI:
                # bbox boyutu daha guvenilir + SAF-GORSEL bir yakinlik olcusudur.
                _dbuyuk = False
                if talon_gate(tespit):
                    _Wd = float(tespit.get("W", 0) or 0); _Hd = float(tespit.get("H", 0) or 0)
                    if _Wd > 1 and _Hd > 1:
                        _dbuyuk = (max(float(tespit["w"]) / _Wd, float(tespit["h"]) / _Hd)
                                   >= float(Cfg.VIS_HANDOFF_PCT))
                self._vis_pos_count = (self._vis_pos_count + 1) if _dbuyuk else 0
                if Cfg.AUTO_VISUAL_HANDOFF and self._vis_pos_count >= Cfg.VIS_N_LOCK:
                    self.durum = "GORSEL_GUDUM"
                    _db = max(float(tespit["w"]) / float(tespit["W"]),
                              float(tespit["h"]) / float(tespit["H"]))
                    print("[GORSEL] DEVIR: hedef yeterince yakin+buyuk (bbox=%.1f%% >= %.1f%%, %d kare "
                          "stabil) -> gorsel guduume gecildi (GPS yaklasma birakildi)."
                          % (_db * 100.0, Cfg.VIS_HANDOFF_PCT * 100.0, Cfg.VIS_N_LOCK))
                    self._vis_ilan = True

        if self.durum == "GORSEL_GUDUM":
            sonuc = self._gorsel_guduum(tespit, t, revert_izin=(mod == "OTO"))
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

        # YATAY nisan noktasi: B) ANTI-OVERSHOOT STANDOFF -> hedefi GECMEDEN onunde dur; pozisyon
        #     KOMUTU hedefe DEGIL, APPROACH_STANDOFF kadar GERIYE surulur -> drone standoff'ta paceler.
        #     ex/ey/d_h ONCE hesaplanir: dikey look-up nisan noktasi d_h'ye (menzile) baglidir.
        # NISAN + MENZIL(d_h) = son_temiz (LEAD), ANLIK DEGIL (2026-07-08 olcum, KILIT fazi): lead
        # nisan hatasi 3.9m vs anlik 20.5m; lead menzil sapmasi -0.9m vs anlik -12.8m -> anlik
        # gecikme-lag'i hedefi ~13m YAKIN gosterip terminali erken devrediyor/sabote ediyordu. Ayni
        # tx,ty ARAMA+KILIT icin ortak -> faz gecisinde estimate DEGISMEZ (tutarli, ikisi de son_temiz).
        tx, ty = float(est[0]), float(est[1])                    # son_temiz = lead (telafi_sn ufku)
        ex = tx - float(drone_pos[0])                             # HEDEFE hata (yaw/handoff/FOV/log)
        ey = ty - float(drone_pos[1])
        d_h = math.hypot(ex, ey)

        # DIKEY nisan (LOOK-UP geometrisi): avci hedefin ALTINDA kalsin, LOS yukselis
        # acisi her an >= LOOKUP_ELEV_DEG olsun -> hedef GOKYUZUNE karsi siluet, YOLO
        # tespiti kopmaz (asagi-bakma/clutter cozumu). SABIT ofset yetmez (ayni dh uzak
        # menzilde kucuk aci) -> MENZIL-OLCEKLI: dh_off = tan(eps)*d_h; asgari
        # APPROACH_ALT_OFFSET (kadraj icin). z_ref taban LOOKUP_MIN_ALT_CM'e clamp'lenir
        # (hedef cok alcaksa nisanin yere sokulmasini onler). DIKEY: lead'siz anlik irtifa.
        z_tgt = self.son_z_anlik if self.son_z_anlik is not None else float(est[2])
        dh_off = (math.tan(math.radians(Cfg.LOOKUP_ELEV_DEG)) * d_h
                  if Cfg.LOOKUP_ELEV_DEG > 0.0 else 0.0)
        alt_off = max(Cfg.APPROACH_ALT_OFFSET, dh_off)            # aci >= eps garanti + kadraj tabani
        z_ref = max(z_tgt - alt_off, Cfg.LOOKUP_MIN_ALT_CM)       # yere cakilma korumasi
        ez = float(z_ref - drone_pos[2])
        # POZISYON KOMUT hatasi (PD bunu surer): standoff noktasina git.
        if d_h > 1e-6:
            _ux, _uy = ex / d_h, ey / d_h
            _dcmd = d_h - Cfg.APPROACH_STANDOFF              # +: yaklas, 0: dur, -: cok yakin -> geri cekil
            ex_cmd, ey_cmd = _ux * _dcmd, _uy * _dcmd
        else:
            ex_cmd = ey_cmd = 0.0

        # ZORUNLU None-init (ucus logu icin): alc blogu calismazsa bile bu degiskenler
        # log dict'inde referanslanir -> NameError'i onle (yoksa beyin_lock'taki
        # try/except o log satirini sessizce yutar). (strike kolonlari log semasi
        # icin sabit kalir, hep None/bos yazilir.)
        d_s = v_close = vdx = vdy = ax = ay = a_fwd = a_right = None   # eski strike kolonlari (bos)
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

        # (2026-07-06 temizligi: eski "10b) GPS TERMINAL VURUS/RAM" blogu SILINDI.
        #  Saldiri/vurus KAMERA verisiyle gorsel PNG fazinda yapilir; GPS yalnizca
        #  yaklasir + kadrajlar. Eski blok git gecmisinde.)

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

        # --- UCUS LOGU: ana yol (APPROACH) tam teshis satiri ---
        if Cfg.LOG_ENABLE:
            mod = "APPROACH"
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


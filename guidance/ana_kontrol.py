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
    # ONGORULU YAW LEAD (pose kanat uclarindan hedef bank): roll (ego-telafili, deg) + yaw lead +
    # kapi durumu + HAM goruntu-roll (ego-telafisiz; ego-comp A/B analizi icin).
    "ibvs_roll", "ibvs_lead", "ibvs_roll_ok", "ibvs_roll_raw",
    # GORUNTU-DUZLEMI KOPRU (2026-07-08): bu tik olu-hesap sanal bbox'la mi calisti?
    # (vis_gordu o tik 0 yazilir -> tespit% durust; kopru katkisi bu kolondan izlenir)
    "vis_kopru",
    # ALTTAN-VURUS teshisi (2026-07-08): dikey nisan (negatif=hedef merkez ustunde tutulur)
    # + alcalma freni carpani (1=serbest, taban=tam fren; eyy>0'da devreye girer).
    "ibvs_eyref", "ibvs_alcal",
    # EGO-PITCH TELAFISI (2026-07-08): yasanin kullandigi ego-telafili dikey hata
    # (vis_ey ham kalir; ikisinin farki = telafinin o tik sildigi kirlilik).
    "ibvs_eyego",
    # KILIT-TUT (2026-07-08 Faz 2): EMA'li bbox eksen orani (ileri kanal bunu
    # BOYUT_HEDEF'e surer; kilit esigi VIS_LOCK_PCT ile ayni olcu).
    "ibvs_boyut",
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
    HANDOFF_RANGE = 4000.0      # cm; tespit menziline gore TUNE et (genis tut)
    HANDOFF_EXIT  = 5000.0      # bu mesafenin disina cikinca handoff iptal
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
    # Kayipta (OTO): VIS_LOST_TO_GPS_S kadar hover, sonra GPS'e don (0 = ANINDA don).
    VIS_MODEL_PATH   = os.path.join(_PROJ_ROOT, "models", "best.pt")   # tespit modeli (task=detect, sinif: talon)
    VIS_POSE_MODEL_PATH = os.path.join(_PROJ_ROOT, "models", "talon_pose.pt")  # poz modeli (task=pose, 6 keypoint)
    # PERVANE MASKESI (yanlis-pozitif engelleme): avcinin KENDI pervanesi arada bir
    # "ucak" olarak algilaniyor (dedektor sinif-agnostik en-yuksek-conf'u secer -> bir
    # karede pervane hedefi bastirabilir). Pervane KADRAJDA SABIT konumdadir (kendi
    # aracimizda). Bu bolgelerde MERKEZI olan kutular dedektorde ELENIR (argmax ONCESI).
    # Normalize (0..1) dikdortgen listesi [x0,y0,x1,y1]; bos liste = kapali.
    # DEGER: 7 Tem log analizi — 60 kesin yanlis-poz (gercek hedef 126m uzak/kadraj disi
    # iken conf~0.48 tespit) SAG-ALT'ta kumelendi (ex~0.75-1.0, ey~0.25). Canli FPV'de
    # dogrula/rafine et (arayuz maskeyi kirmizi tarama ile cizer; vis_cx/vis_ey loglanir).
    PROP_MASKE = [(0.80, 0.55, 1.0, 0.95)]   # sag-alt kose (on-sag pervane)
    VIS_CONF_MIN     = 0.15     # kilit/komut icin asgari guven. 0.45->0.15 (8 Tem ucus_1
                                # segment kiyasi: tespit %22-33 -> %50-64; yanlis-poz ana
                                # kumesi PROP_MASKE ile zaten eleniyor). Cok yanlis tespit
                                # gorursen slider'dan yukselt.
    VIS_N_LOCK       = 5        # ardisik gecerli-tespit -> GORSEL_GUDUM (yanlis-poz bastir)
    VIS_STALE_S      = 0.5      # tespit bu sureden eskiyse yok say (kayip mantigi devreye girer)
    VIS_LOST_TO_GPS_S = 0.0     # kayipta GPS'e donmeden once hover suresi (yalniz OTO).
                               # 0 = ANINDA GPS'e don (hover fazi yok; kullanici istegi
                               # 2026-07-08 — ara bekleme kafa karistiriyordu). Dedektor
                               # titremesi (tek-kare atlama) zaten VIS_STALE_S ile koprulenir;
                               # son gorusten itibaren toplam ~(VIS_STALE_S + bu) sn'de doner.
                               # Manuel GORSEL switch'te donus YOK (revert_izin=False), hep hover.
    VIS_EMA          = 0.4      # ex/ey EMA yumusatma (tek-kare yanlis tespiti bastir)
    # --- GORUNTU-DUZLEMI KOPRU / OLU-HESAP (2026-07-08, kullanici onayi) ---
    # Sorun: dedektor 15-40 m'de duzenli 0.5+ sn delik aciyor -> VIS_STALE_S dolunca
    # gorsel faz dusuyordu (8 Tem ucus_2: 22 episodun hepsi 1-2.4 sn; kilit isteri
    # matematiksel imkansiz). Cozum: gercek tespit bayatlayinca bbox, son iki GERCEK
    # tespitten olculen goruntu-hiziyla (px/s, EMA'li) VIS_KOPRU_S boyunca ILERI
    # tasinir; IBVS ayni yasayla onu izler. Gercek tespit donunce devralir, donmezse
    # kayip mantigi (VIS_LOST_TO_GPS_S) calisir. ACIKLANABILIR: sabit-hiz varsayimi,
    # kameradan turetilmis veri (son bbox + bbox hizi) -> gorsel-faz GPS yasagina uygun.
    # DURUSTLUK: kopru tespiti KILIT SAYACINA SAYILMAZ (vis_gordu=0, vis_kopru=1
    # loglanir); yalniz GORSEL_GUDUM fazinda uygulanir (OTO kilit sayacini sisirmez).
    VIS_KOPRU_S      = 1.2      # kopru suresi (s); 0 = kapali ⚙
    VIS_KOPRU_V_EMA  = 0.5      # goruntu-hizi EMA katsayisi (yeni olcum agirligi)
    # --- BASIT IBVS (2026-07-07): goruntu merkezi -> bbox merkezi cizgisi ---
    # TEK gorsel yasa (guidance/ibvs_gorsel.py): cizginin YATAY bileseni yaw'a,
    # DIKEY bileseni throttle'a gider; BUYUKLUGU (merkeze sapma "mesafesi") ileri
    # itkiyi kisar (once ortala, sonra ilerle). Roll HEP 0 (bank yok — eski PN'de
    # bank hedefi kadrajdan atip kamerayi yere ceviriyordu). Kamera +25 tilt'li
    # oldugundan hedefi MERKEZDE tutmak araci hedefin ALTINDA tutar (gokyuzu
    # arka plan / alttan yaklasma) — ekstra dikey geometri kodu GEREKMEZ.
    IBVS_K_YAW       = 0.8      # yatay kazanc: yaw = SIGN*K*ex (clamp +-YAW_MAX) ⚙
    IBVS_SIGN_YAW    = +1.0     # ex>0 (hedef SAGDA) -> burnu SAGA cevir; ters tepki gorursen -1
    IBVS_K_DIKEY     = 1.3      # dikey kazanc: thr = SIGN*K*(-ey) (clamp THR_DN..THR_UP) ⚙
                                # 8 Tem ucus_2: 1.3 en iyi merkezleme (1.9 asiri tepkili,
                                # 0.65 yetersiz kaldi — episod kiyasi r_ort medyan ~0.21).
    IBVS_SIGN_DIKEY  = +1.0     # hedef YUKARIDA (ey<0) -> TIRMAN (thr>0; GPS faziyla ayni kanon).
                                # SIM'de dikey TERS tepki gorursen -1 yap (tek isaret, tek yer).
    IBVS_ILERI       = 0.45     # ileri itki TAVANI (0..1; boyut yasasi bunu asamaz) ⚙
    # --- KILIT-TUT / BOYUT REGULASYONU (2026-07-08, Faz 2 sartname 6.1.2/6.1.4) ---
    # VURUS degil MESAFE TUTMA: bbox eksen orani (max(w/W,h/H) — kilit sayaci metriğiyle
    # AYNI olcu) HEDEF'e P-yasayla surulur:
    #   ileri = clamp(K_BOYUT*(BOYUT_HEDEF - boyut_f), -GERI_MAX, IBVS_ILERI)
    # Uzakta istek doygun -> tavan hiziyla yaklas (eski davranis); hedef boyutta cruise
    # dengesi boyut_eq = HEDEF - ileri_eq/K (0.09 - 0.25/15 ~ 0.073 >= VIS_LOCK_PCT) ->
    # hedefin gerisinde istasyon tut, kilit penceresi dolsun; fazla yakinsa GERI kacis.
    # K_BOYUT=0 -> regulasyon KAPALI = eski sabit-ileri yasa (canli A/B + kacis kapisi).
    # Girdi yalniz bbox pikselleri -> gorsel-faz GPS yasagina uygun. Terminal vurus AYRI
    # faz olarak sonra (kilit_ok sonrasi karar; o zaman NISAN/ILERI ayri banda gecer).
    IBVS_BOYUT_HEDEF = 0.09     # bbox eksen orani hedefi (>= VIS_LOCK_PCT 0.06 + marj) ⚙
    IBVS_K_BOYUT     = 15.0     # boyut hatasi -> ileri itki kazanci (0=KAPALI/eski yasa) ⚙
    IBVS_GERI_MAX    = 0.15     # fazla yakinken geri itki tavani (0=asla geri gitme) ⚙
    IBVS_MERKEZ_FREN = 1.4      # sapma buyudukce ileri kis: pitch *= max(0, 1 - FREN*r).
                                # 0 = hep tam gaz; buyuk deger = once ortala sonra ilerle ⚙
                                # 1.0->1.4 (8 Tem ucus_2: fren artisi sonrasi episodlar oturakli).
    # --- DIKEY NISAN (tilt-farkinda; hiz vektorunu hedefe kilitle) ---
    # Kamera +TILT derece YUKARI sabit. Hedefi kadraj MERKEZINDE tutmak = hiz vektorunu
    # hedefin ~TILT altina nisanlamak (kronik dikey undershoot). Hedefi hiz vektorunun
    # goruntudeki yerine (FOE) tutarsak "hedefte" = "burun hedefe kilitli" -> dogrudan
    # carpisma rotasi. ey_ref = NISAN * tan(TILT) / tan(VFOV_yari) (tilt'ten TURETILIR).
    IBVS_TILT_DEG      = 25.0   # kamera YUKARI tilt (DOGRULANDI; kullanici teyidi)
    IBVS_VFOV_HALF_DEG = 47.2   # dikey FOV yari acisi (16:9 + HFOV 125'ten)
    IBVS_DIKEY_NISAN   = -0.25  # NEGATIF = hedefi merkez USTUNDE tut -> LOS > TILT -> arac
                                # orantili olarak hedefin ALTINDA + gokyuzu arka plan (ALTTAN
                                # VURUS). 0 = merkez; 1 = hiz vektorunu hedefe nisanla ⚙
                                # 0.1->-0.25 (8 Tem: arac hedefin USTUNE cikip zemin clutter'da
                                # tespit kaybediyordu; -0.25 -> ey_ref~-0.108 -> hedef cyn~0.45'te,
                                # AV %10-90 bandinin rahat icinde. Daha da alttan: -0.4.)
    # --- ALCALMA FRENI (gorsel anti-lift-carry, 2026-07-08) ---
    # GPS yolundaki alc_oncelik'in gorsel-faz aynasi: hedef nisan noktasinin ALTINDAysa
    # (eyy>0 = arac cok yuksekte) ileri itki carpimsal kisilir ->
    #   pitch *= clamp(1 - ALCAL_FREN*max(0,eyy), ALCAL_TABAN, 1)
    # Ileri-ucus tasimasi (lift carry) dusunce negatif thr gercekten alcaltir (THR_DN
    # yorumundaki ders: tam ileri ucusta -0.40 bile tirmanmayi durduramiyordu).
    # Tirmanis tarafi (eyy<0) etkilenmez. Girdi yalniz goruntu buyuklugu -> kural uygun.
    IBVS_ALCAL_FREN  = 2.0      # 0=kapali; 2.0 -> eyy~0.4'te tabana iner ⚙
    IBVS_ALCAL_TABAN = 0.2      # fren tabani (asla tam durma; biraz kapanis kalsin).
                                # GPS alc_oncelik 0.15 tabaninin gorsel karsiligi; slider DISI.
    # --- EGO-PITCH TELAFISI (2026-07-08; kacak-tirmanma kok nedeni) ---
    # Ileri itki govdeyi one yatirinca kamera (govdeye sabit) asagi doner -> hedef goruntude
    # YUKARI ziplar -> yasa "hedef kacti, TIRMAN" okuyordu (log 204331: corr(pitch,ey)=0.70;
    # drone hedefin 10 m ALTINDAYKEN +0.70 tirmanis). Dikey hata kendi pitch'ten arindirilir:
    #   ey_dunya = ey_f - GAIN*tan(own_pitch)/tan(VFOV_yari)   (ibvs_gorsel.hesapla)
    # Kendi IMU'muz = ego-motion (ego-roll telafisiyle ayni emsal) -> kural ihlali DEGIL.
    IBVS_EGO_PITCH_GAIN = 1.0   # 0=kapali (A/B icin); ters etki gorulurse once 0'la kiyasla.
    # --- ONGORULU YAW LEAD (pose kanat uclarindan hedef ROLL/bank) ---
    # Hedefi ARKADAN takip ederken iki kanat ucu pikselinden (kp[1]=sol, kp[2]=sag)
    # goruntu-uzayi bank acisi: roll_img=atan2(dy,dx). Bankli ucak alcak kanadi yonune
    # doner -> hedefin GIDECEGI yon oncelenir, yaw'a ILERI-BESLEME eklenir:
    # yaw = K_YAW*ex + SIGN_ROLL*K_ROLL_LEAD*roll_img. Sadece YAW; thr/pitch/roll degismez.
    # Pose GORSEL veri (kameradan keypoint) -> yarisma kuralina uygun (GPS/J degil).
    IBVS_K_ROLL_LEAD   = 0.5    # roll_img (rad) -> yaw lead kazanci ⚙ (0 = ongoru kapali)
    IBVS_SIGN_ROLL     = -1.0   # bank -> yaw isareti. VERI ile belirlendi (7 Tem, ucus_log_220539):
                                # araclar/pose_ongoru_analiz.py corr=-0.86 @0.2sn, %86 uyum -> SIGN=-1.
                                # (roll_img>0 iken hedef goruntude SOLA gidiyor; +1 TERS'ti.) Yeni pose
                                # modeli/kamera degisince analizi tekrar kos, ONERI'yi uygula.
    IBVS_ROLL_CONF_MIN = 0.5    # iki kanat ucu icin asgari keypoint guveni (kapi) ⚙
    IBVS_ROLL_EMA      = 0.4    # roll yumusatma (pose seyrek/gurultulu; POZ_HER_N=3)
    # EGO-MOTION TELAFISI: kamera govdeye sabit -> biz yatinca (kendi roll) kanat cizgisi de
    # doner ve "hedef bank"i kirletir. Kendi roll'umuzu (IMU) goruntu-roll'unden cikaririz:
    # roll_comp = roll_img - GAIN*own_roll. GAIN=0 kapali; isaret canlida araclar/
    # pose_ongoru_analiz ego A-B'siyle dogrulanir (+1 varsayildi, veriyle teyit et).
    # NOT: own_roll KENDI IMU'muz (ego-motion), hedef konumu DEGIL -> yarisma kurali ihlali degil.
    IBVS_EGO_ROLL_GAIN = 1.0
    IBVS_ASPECT_MIN    = 120.0  # arkadan-takip kapisi (deg; yalniz aspect PnP'den mevcutken).
                                # yandan/onden gorunumde kanat cizgisi bank'i temsil etmez -> lead=0
    IBVS_POZ_STALE_S   = 0.6    # poz bayatlik esigi (guduumde): bundan eski poz -> lead yok

    # (ESKI "GORSEL PNG" blogu — VIS_LAW/PN_N/PN_A_MAX/PN_TILT/TRACK_TILT/VZ_MAX/
    #  SPAN_CM/R_EMA/OMEGA_*/W_PX_MIN/VC_CAP — 2026-07-07 SILINDI; git gecmisinde.)
    # (ESKI kapanma/soft-start/look-up sabitleri — VIS_KP_CLOSE/KV_CLOSE/TERM_PCT/
    #  COMMIT_PCT/TAKIP_VC/SOFTSTART_*/COMMIT_LAT/TAU_Z/PN_SIGN_VZ/LOOKUP_VZ/HOLD_PCT —
    #  2026-07-07 SILINDI; git gecmisinde. LOOKUP_ELEV_DEG yalniz GPS z_ref'te yasar.)

    # --- KILITLENME ISTERI SAYACI (sartname 6.1.2 + 6.1.4, Sekil 2) — SALT GOZLEM ---
    # Gudume KARISMAZ (eski YAKLASMA/TAKIP/TERMINAL alt-FSM'i silindi); arayuz/video
    # kaniti icin sayilir: kirmizi kilit dortgeni + 5/10 sn pencere + ANGAJMAN cipi.
    # Kilit tanimi (her tik): hedef MERKEZI Hedef Vurus Alani (AV) icinde VE bbox
    # ekranin EN AZ BIR ekseninde >= VIS_LOCK_PCT. Kesintili kilit sayilir.
    VIS_LOCK_PCT     = 0.06     # bbox eksen orani esigi. Sartname kurali >=0.05 ama
                                # tam sinirda calisan algoritma hakem incelemesinde
                                # "hatali kilit paketi" sayilabilir -> tavsiye edilen 0.06
    VIS_AV_X         = 0.25     # AV yatay kenar payi (sartname sabiti: %25-%75 bandi)
    VIS_AV_Y         = 0.10     # AV dikey kenar payi (sartname sabiti: %10-%90 bandi)
    VIS_WIN_S        = 10.0     # degerlendirme penceresi (sartname sabiti)
    VIS_WIN_NEED_S   = 5.0      # pencerede gereken kumulatif kilit (sartname sabiti)


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

        # --- GORSEL GUDUM (basit IBVS) durumu ---
        # son_tespit: server.dedektor_dongusu'nin beyin_lock icinde yazdigi son bbox dict.
        self.son_tespit = None          # {cx,cy,w,h,conf,W,H,t} | None
        self.son_tespit_t = None        # o tespitin perf_counter zamani (bayatlik kontrolu)
        self.son_poz = None             # normalize poz dict {kp,conf,ok,aspect_deg,...} | None (GORSEL veri)
        self.son_poz_t = None           # o pozun perf_counter zamani (bayatlik; POZ_HER_N seyrek)
        self._vis_pos_count = 0         # ardisik gecerli-tespit (kilit histerezisi)
        self._vis_lost_count = 0        # ardisik kayip (hover -> GPS'e donus karari)
        self._vis_ilan = False          # "GPS kesildi" anonsu bir kez basilsin
        self._vis_v = None              # goruntu-hizi (px/s; son iki GERCEK tespitten, EMA'li)
        self.vis_kopru = False          # bu tik KOPRU (olu-hesap) tespitiyle mi? (telemetri/log)
        self.ibvs = AvciIBVS()          # merkez->bbox cizgisi (tek gorsel yasa; basit IBVS)
        self.ibvs_tlm = {}              # son IBVS telemetrisi (server build_telemetry okur; salt-okunur)
        self.vis_mode = "OTO"           # guduum pipeline switch (test): OTO | GPS | GORSEL
        # --- KILITLENME ISTERI SAYACI (sartname 6.1.2/6.1.4; SALT GOZLEM, komuta girmez) ---
        self.kilit_win = deque()        # (t, kilit_anlik) ornekleri — son VIS_WIN_S penceresi
        self.kilit_sure = 0.0           # penceredeki kumulatif kilit suresi (s)
        self.kilit_anlik = False        # bu tik kilit kosulu (AV icinde + boyut >= LOCK_PCT)
        self.kilit_ok = False           # LATCH: pencere isteri (>=WIN_NEED_S) saglandi
        self.kilit_boyut = None         # bu tik bbox eksen orani max(w/W, h/H) (telemetri)

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
        # ucus logu: yeni gorev -> yeni dosya (sonraki tik taze zaman-damgali acar).
        # NOT: ayni kaynak ust uste secilirse bu metod erken doner (yukarida) -> dosya
        # donmez; server "Gorev Baslat"ta log_dondur()'u AYRICA kosulsuz cagirir
        # (her gorev = ayri ucus_log dosyasi = veri/tune_parametreler/ucus_N klasoru).
        self.log_dondur()

    # ----------------------------------------------------------------
    #  UCUS LOGUNU DONDUR (gudum-disi; salt dosya yasam dongusu): acik log
    #  dosyasini kapatir; sonraki tik taze zaman-damgali dosya acar. Server
    #  her "Gorev Baslat"ta cagirir -> her gorev kendi ucus_log dosyasini
    #  (dolayisiyla kendi tune_parametreler/ucus_N klasorunu) alir.
    # ----------------------------------------------------------------
    def log_dondur(self):
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
        self._vis_v = None               # kopru hizi da taze baslasin
        self.vis_kopru = False
        self.ibvs.sifirla()
        # switch = yeni deneme -> kilitlenme penceresi ve latch de taze baslasin
        self.kilit_win.clear()
        self.kilit_sure = 0.0
        self.kilit_anlik = False
        self.kilit_ok = False
        self.kilit_boyut = None
        return True

    def set_gorsel_tespit(self, det):
        if det is not None:
            t_det = det.get("t", time.perf_counter())
            # GORUNTU-HIZI (px/s, EMA'li): son iki GERCEK tespitten. KOPRU (olu-hesap)
            # bu hizla bbox'u ileri tasir. Uzun aradan sonraki ilk tespitte hiz BAYAT
            # sayilir ve sifirlanir (delik oncesi hizla kopru kurulmasin).
            if self.son_tespit is not None and self.son_tespit_t is not None:
                dt = t_det - self.son_tespit_t
                if 0.0 < dt <= Cfg.VIS_STALE_S:
                    vx = (float(det["cx"]) - float(self.son_tespit["cx"])) / dt
                    vy = (float(det["cy"]) - float(self.son_tespit["cy"])) / dt
                    W = float(det.get("W", 0) or 0)
                    if W > 1:                       # tavan: kare genisligi / 1.25 sn
                        vmax = 0.8 * W              # (sacma tek-kare sicramasini keser)
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
        # det None ise ESKI tespiti SILME: tek bos kare kilidi dusurmesin. Bayatlik
        # (VIS_STALE_S) _oku'da elenir; kayip histerezisini _vis_lost_count yonetir.

    def set_gorsel_poz(self, poz):
        """Pose dedektor NORMALIZE ciktisini (kp/conf/aspect_deg...) beyne yaz — GORSEL
        veri (kameradan keypoint), ONGORULU yaw lead'i besler. server.dedektor_dongusu
        beyin_lock altinda TAZE pose kostugunda cagirir. det deseni: None ise eskisini
        SILME (bayatlik _gorsel_guduum'da IBVS_POZ_STALE_S ile elenir)."""
        if poz is not None:
            self.son_poz = poz
            self.son_poz_t = time.perf_counter()

    def _gorsel_tespit_oku(self):
        """Bayat-olmayan son tespiti dondur. Bayatsa: (yalniz GORSEL_GUDUM'da) once
        GORUNTU-DUZLEMI KOPRUSU dene — bbox son olculen hizla ileri tasinir,
        kopru=True isaretlenir. Kopru de bittiyse None (kayip mantigi devreye girer)."""
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
                and self.durum == "GORSEL_GUDUM"          # yalniz gorsel fazda (kilit sayaci sismesin)
                and yas <= Cfg.VIS_STALE_S + kopru_s):
            W = float(det.get("W", 0) or 0); H = float(det.get("H", 0) or 0)
            if W > 1 and H > 1:
                d2 = dict(det)
                d2["cx"] = min(max(float(det["cx"]) + self._vis_v[0] * yas, 0.0), W)
                # DIKEY EKSTRAPOLE EDILMEZ (2026-07-08 kacak-tirmanma dersi): olculen vy
                # cogunlukla EGO-PITCH sallanmasinin urunu; kopru onu surdurup sanal kutuyu
                # kadraj tepesine mihliyor ve ~1.7 sn kor TAM TIRMANIS komutu uretiyordu
                # (log 204331: ey=-1.0 kuyruklari). cy son GERCEK olcumde DONAR; dikey
                # komut da koprude 0'a cekilir (_gorsel_guduum) -> irtifa-tut.
                d2["kopru"] = True                        # kilit sayaci + log bunu ayirt eder
                self.vis_kopru = True
                return d2
        return None

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
            # vis_gordu: yalniz GERCEK tespit (kopru HARIC -> rapor tespit% durust kalir);
            # vis_kopru: bu tik olu-hesap koprusuyle mi calisti (analiz ayirt eder).
            "vis_gordu": 1 if (tespit is not None and not tespit.get("kopru")) else 0,
            "vis_kopru": 1 if (tespit is not None and tespit.get("kopru")) else 0,
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
            # ongorulu yaw lead (pose kanat uclarindan hedef bank) + kapi (roll_ok):
            # roll_ok=1 -> roll TAZE (kanat conf + aspect + bayatlik kapisi gecti, lead uygulandi);
            # 0 -> kapi kapali, ibvs_roll stale (analiz bu satirlari elemeli).
            d["ibvs_roll"] = it.get("roll_deg"); d["ibvs_lead"] = it.get("lead")
            d["ibvs_roll_ok"] = 1 if it.get("roll_ok") else 0
            d["ibvs_roll_raw"] = it.get("roll_raw_deg")   # ham goruntu-roll (ego-comp A/B)
            # alttan-vurus teshisi: dikey nisan + alcalma freni carpani (tune analizi)
            d["ibvs_eyref"] = it.get("ey_ref"); d["ibvs_alcal"] = it.get("alcal")
            d["ibvs_eyego"] = it.get("ey_ego")    # ego-pitch telafili dikey (yasa girdisi)
            d["ibvs_boyut"] = it.get("boyut")     # kilit-tut: EMA'li bbox eksen orani
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
        # kumulatif sure: onceki ornek kilitliyse iki ornek arasi dt sayilir
        # (0.5 sn ustu bosluk = gorsel faz disinda gecen zaman; sayilmaz)
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
    def _gorsel_guduum(self, tespit, t, revert_izin=True, own_roll_rad=None,
                       own_pitch_rad=None):
        # revert_izin=False (manuel GORSEL switch): kayipta GPS'e DONME, hover'da kal.
        # own_roll_rad: aracin KENDI roll'u (IMU) — pose roll ego-motion telafisi (hedef degil).
        # KILITLENME ISTERI SAYACI (sartname 6.1.2/6.1.4): SALT GOZLEM — kirmizi
        # dortgen / ANGAJMAN cipi / olay gunlugu icin sayilir, KOMUTA GIRMEZ.
        # DURUSTLUK: KOPRU (olu-hesap) tespiti sayaca GIRMEZ — kilit yalniz GERCEK
        # gorsel temasla dolar (kopru tik'i tespitsiz tik gibi islenir).
        kopru = bool(tespit is not None and tespit.get("kopru"))
        self._kilit_degerlendir(None if kopru else tespit, t)
        # YARISMA KURALI: gorsel temastan SONRA hareket komutu YALNIZ GORSEL veriden.
        # GPS/J (yon YA DA buyukluk) GECIRILMEZ -> diskalifiye. IBVS yalniz bbox okur.
        if tespit is not None:
            self._vis_lost_count = 0
            # TAZE poz (GORSEL keypoint): bayat degilse ongorulu yaw lead'i besler.
            # Pose seyrek (POZ_HER_N) -> bayatlik esigi IBVS_POZ_STALE_S. Yoksa None -> saf IBVS.
            poz = self.son_poz
            if poz is None or self.son_poz_t is None or \
                    (time.perf_counter() - self.son_poz_t) > float(getattr(Cfg, "IBVS_POZ_STALE_S", 0.6)):
                poz = None
            komut = self.ibvs.hesapla(tespit, Cfg, poz=poz, own_roll_rad=own_roll_rad,
                                      own_pitch_rad=own_pitch_rad)
            self.ibvs_tlm = self.ibvs.durum()
            # KOPRUDE DIKEY-TUT (2026-07-08 kacak-tirmanma dersi): kopru bbox'i TAHMINDIR
            # (cy zaten donduruldu); tahminle irtifa entegre etme -> thr=0 (irtifa-tut),
            # yatay takip (pitch/yaw) surer. Gercek tespit donunce normal yasa devralir.
            if kopru:
                komut = (0.0, komut[1], komut[2], komut[3])
                self.ibvs_tlm["dikey"] = 0.0          # telemetri uygulanani gostersin
            return komut
        # --- KAYIP: (OTO) VIS_LOST_TO_GPS_S kadar HOVER, sonra GPS'e don.
        #     0 = ANINDA GPS (hover fazi yok; dedektor titremesini zaten VIS_STALE_S
        #     koprular — buraya dusen GERCEK kayiptir). Manuel GORSEL'de HEP hover. ---
        self._vis_lost_count += 1
        lost_s = self._vis_lost_count * Cfg.DT
        if (not revert_izin) or lost_s <= float(Cfg.VIS_LOST_TO_GPS_S):
            return 0.0, 0.0, 0.0, 0.0            # hover: ararken bekle (manuel GORSEL'de HEP)
        # UZUN kayip (yalnizca OTO) -> GPS guduumune GERI DON (yeniden yaklas, yeniden kilitle)
        print("[GORSEL] Hedef %.1fs kayip -> GPS guduumune GERI DONULDU (yeniden yaklas)." % lost_s)
        self.durum = "ARAMA"
        self._vis_pos_count = 0
        self._vis_lost_count = 0
        self._vis_ilan = False
        self.ibvs.sifirla()
        # kilit penceresi temizlenir; kilit_ok LATCH'i KORUNUR (sartname isteri
        # gecmiste saglandiysa gecerli kalir; sayac yeniden dolmak zorunda degil).
        self.kilit_win.clear()
        self.kilit_sure = 0.0
        self.kilit_anlik = False
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
            # kendi roll+pitch'imiz (IMU) -> ego-motion telafileri (hedef verisi DEGIL):
            # roll pose-lead'i temizler; pitch dikey hatayi (ileri yatista kamera dusmesi
            # hedefi goruntude yukari ziplatiyordu -> sahte TIRMAN) temizler.
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

        # YATAY nisan noktasi: B) ANTI-OVERSHOOT STANDOFF -> hedefi GECMEDEN onunde
        #     dur. KISA lead (APPROACH_LEAD_S) ile nisan (savrulmayi onler); pozisyon KOMUTU
        #     hedefe DEGIL, APPROACH_STANDOFF kadar GERIYE surulur -> drone standoff'ta paceler.
        #     ex/ey/d_h ONCE hesaplanir: dikey look-up nisan noktasi d_h'ye (menzile) baglidir.
        if self.son_xy_anlik is not None and self.son_hiz is not None:
            tx = float(self.son_xy_anlik[0]) + Cfg.APPROACH_LEAD_S * float(self.son_hiz[0])  # kisa lead
            ty = float(self.son_xy_anlik[1]) + Cfg.APPROACH_LEAD_S * float(self.son_hiz[1])
        else:
            tx, ty = float(est[0]), float(est[1])                 # fallback: 2sn lead
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


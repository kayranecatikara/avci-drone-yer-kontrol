# -*- coding: utf-8 -*-
"""
================================================================================
AVCI DRONE — ANA KONTROL DONGUSU  (guduum + karar mekanizmasi, tek dosya)
================================================================================
GIRIS NOKTASI: main.py -> web.server.main() -> beyin = AvciKontrol(drone),
50 Hz beyin.adim(). Manuel/pasif modda server yalnizca beyin._hedef_temizle()
cagirir (filtre olcumu akar, ucus komutu uretilmez). Ayrinti: guidance/GUDUM_HARITA.md

>>> GPS YIGINI DEGISTI (2026-07-10, kullanici karari) <<<
Eski GPS tarafi (Inovasyonlu J CT-EKF + PD/standoff/speed_cap/cascade dikey)
KOMPLE SILINDI. GPS fazi artik IKI yeni moduldedir ve AvciKontrol onlara DEVREDER:
  fusion/gnss_filtre.py   -> GNSSFiltre: eksen-bazli spike temizleme (pencereli
                             lineer-egim tahmini; sapan olcum tahminle degistirilir)
                             + egimden hiz kestirimi + guven-agirlikli gecikme telafisi.
  guidance/gps_takip.py   -> GPSTakip: kalkis (AGL), GNSS temizleme cagrisi,
                             kesintide olu-hesap (DR, <=30 sn), yatay PD + dikey
                             PID, alcalma onceligi, eksen-bazli rate-limit, yaw.
AvciKontrol'un kalan isi: FSM (ARAMA/KILIT <-> GORSEL_GUDUM), GORSEL faz (basit
IBVS), kilitlenme isteri sayaci, ucus logu, telemetri alanlari.

FAZLAR / FSM (self.durum):
  ARAMA  -> GPS yaklasma: gps_takip.GPSTakip.adim() (yukaridaki zincir).
  KILIT  -> ayni GPS yaklasma; d_h < HANDOFF_RANGE histerezisiyle isaretlenir
            (gorsel faz devralmaya hazir).
  GORSEL_GUDUM -> yonelim YALNIZCA kameradan: YOLO bbox (server dedektor thread
            -> set_gorsel_tespit) -> _gorsel_guduum -> guidance/ibvs_gorsel.py
            (BASIT IBVS: goruntu merkezi -> bbox merkezi cizgisi; acisi+buyuklugu
            komuta cevrilir). Kayipta: hover -> (OTO'da) GPS'e geri don.
  Otomatik gecis (vis_mode=OTO): AUTO_VISUAL_HANDOFF + ard arda VIS_N_LOCK
  gecerli tespit + handoff yakinligi. Manuel: set_vis_mode GPS/GORSEL zorlar.
  NOT (2026-07-07): eski PN/PNG gorsel yigini kullanici karariyla SILINDI.

>>> SIMDE DOGRULA (frame/birim/isaret) <<<
  - Konum birimi cm; get_drone_speed cm/s.
  - get_drone_rotation DERECE dondurur (Cfg.ROT_IN_DEGREES=True).
  - GPS fazi isaret/kazanclari gps_takip.GPSCfg'de; gorsel isaretler Cfg.IBVS_SIGN_*.
================================================================================
"""
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
#   [ORTAK]  : her fazda gecerli (birim/isaret/dongu/log).
#   [FSM]    : gorsel-devir kapisi (handoff). GPS-YAKLASMA guduumunun sabitleri
#              BURADA DEGIL guidance/gps_takip.GPSCfg'dedir (2026-07-10 devri).
#   [GORSEL] : basit IBVS (ibvs_gorsel.py) + kilit isteri sayaci + kayip yonetimi.
# Canli-tune: web arayuzu /api/tune ile TUNE_ALLOW listesindekileri degistirir.
# ==========================================================
class Cfg:
    # ================= [ORTAK] =================
    # --- BIRIM / FRAME / ISARET ---
    ROT_IN_DEGREES = True       # get_drone_rotation derece dondururse True
    PITCH_SIGN = +1.0           # gorsel fazda ileri hareket +pitch degilse -1
                                # (GPS fazinin isaret/kazanclari gps_takip.GPSCfg'de)

    # --- DONGU (server.py / calistir 50 Hz surer) ---
    LOOP_HZ = 50.0
    DT = 1.0 / LOOP_HZ

    # ================= [FSM / GORSEL DEVIR KAPISI] =================
    # GPS-yaklasma guduumunun KENDISI guidance/gps_takip.py'dedir (kalkis, GNSS
    # temizleme fusion/gnss_filtre, olu-hesap/DR, PD/PID, kendi GPSCfg sabitleri).
    # Burada yalniz FSM'in gorsel-devir kapisi yasar: hedefe yeterince yaklasinca
    # durum KILIT olur (histerezisli); YOLO kilidiyle birlikte GORSEL_GUDUM'a gecilir.
    HANDOFF_RANGE = 4000.0      # cm; tespit menziline gore TUNE et (genis tut)
    HANDOFF_EXIT  = 5000.0      # bu mesafenin disina cikinca handoff iptal
    # OTOMATIK GORSEL DEVIR: yakinlik (d_h<HANDOFF_RANGE) + ard arda VIS_N_LOCK
    # gecerli tespit -> saldiri KAMERAYA devredilir (Ister 9/10 angajman zinciri).
    # Manuel GORSEL switch (set_vis_mode "GORSEL") bu bayraktan BAGIMSIZ calisir.
    AUTO_VISUAL_HANDOFF = True

    # --- GORSEL FAZ KOMUT SINIRLARI (ibvs_gorsel.hesapla clamp'leri) ---
    THR_UP    = 0.70            # gorsel dikey komut tavani (tirmanis)
    THR_DN    = -1.00          # gorsel dikey komut tabani: TAM inme yetkisi (tam ileri
                              # ucusta lift-carry'yi ancak tam negatif throttle yener)
    YAW_MAX   = 0.80           # gorsel yaw tavani (10 Tem: 0.60->0.80 — 062231'de YAKINken
                               # yaw_cmd 0.60 tavaninda doyup yetismiyordu -> donus yetkisi artir)

    # --- HIZ LIMITI (gorsel faz _send'i; salinim onleyici) ---
    MAX_DELTA = 0.05           # gorsel komut/tik max degisim (GPS fazi kendi limitlerini
                               # gps_takip.GPSCfg.MAX_DELTA_* ile uygular)

    # ================= [ORTAK] =================

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
    # 2. kutu: oyun HUD metni ("ARMED / TRIGGER: NOT READY") yanlis "talon" olarak
    # algilaniyordu (conf~0.76; T ve Y harfleri tetikliyor). Kadraj MERKEZINDE (ufuk
    # altinda) SABIT konumda -> maskele. KOORDINAT TAM KAREDEN OLCULDU (9 Tem ekran
    # goruntusu): ARMED x0.44-0.55/y0.51-0.55 + TRIGGER:NOT READY x0.34-0.67/y0.58-0.63.
    # NOT: bu bant kadraj MERKEZI -> ufuk ALTINDA kalan hedefi de eleyebilir; kamera
    # +25 tilt hedefi ufuk USTUNDE (gokyuzu) tuttugundan pratikte guvenli. FPV kirmizi
    # overlay'e bakip daralt/genislet.
    PROP_MASKE = []   # KAPALI (2026-07-10 kullanici istegi): sag(pervane)+orta(HUD) eleme
                      # bolgeleri KALDIRILDI. Bos liste = hic kutu konuma gore elenmez.
                      # Pervane/HUD yanlis-pozitif riski artik tracker (HybridSort onay) ile emilir.
                      # Geri istersen: [(0.80,0.55,1.0,0.95),(0.31,0.49,0.70,0.65)] (sag pervane + orta HUD).
    VIS_CONF_MIN     = 0.15     # kilit/komut icin asgari guven. 0.45->0.15 (8 Tem ucus_1
                                # segment kiyasi: tespit %22-33 -> %50-64; yanlis-poz ana
                                # kumesi PROP_MASKE ile zaten eleniyor). Cok yanlis tespit
                                # gorursen slider'dan yukselt.
    # --- SAHI (Slicing Aided Hyper Inference) — uzak/kucuk hedef recall (2026-07-09) ---
    # Kareyi ortusen dilimlere bol, HER dilimde best.pt kosur, kutulari tam-kare
    # koordina tasi + NMS ile birlestir. Uzak hedef dilim icinde buyuk oran kaplar
    # -> dedektor korlugu (15-40 m) azalir. SADECE best.pt (detect); pose modeline
    # UYGULANMAZ (keypoint dilim-merge yok). Bizim temiz impl (gorsel_tespit._sahi_ham),
    # sahi paketi GEREKMEZ; kural 8 aciklanabilir. MALIYET: N dilim -> N x inference;
    # GPU oyunla paylasimli -> SAHI_KOSUL_CONF ile yakin hedefte dilimleme atlanir.
    SAHI_AKTIF       = True     # False -> tek tam-kare predict (eski davranis, bit-ayni)
    SAHI_DILIM_PX    = 640      # dilim kenari (px); best.pt imgsz'ine yakin
    SAHI_ORTUSME     = 0.2      # komsu dilim ortusme orani (kenardaki hedef bolunmesin)
    SAHI_TAM_KARE    = True     # dilimlere EK tam-kare predict (yakin/buyuk hedef kesilmesin)
    SAHI_NMS_IOU     = 0.5      # dilim+tam-kare kutu birlestirme IoU esigi
    SAHI_KOSUL_CONF  = 0.5      # tam-karede conf>=bu kutu VARSA dilimleme ATLA (perf).
                                # 0 = HER kare dilimlenir (en yuksek recall, en yavas)
    VIS_N_LOCK       = 5        # ardisik gecerli-tespit -> GORSEL_GUDUM (yanlis-poz bastir)
    VIS_STALE_S      = 0.5      # tespit bu sureden eskiyse yok say (kayip mantigi devreye girer)
    VIS_LOST_TO_GPS_S = 0.0     # kayipta GPS'e donmeden once hover suresi (yalniz OTO).
                               # 0 = ANINDA GPS'e don (hover fazi yok; kullanici istegi
                               # 2026-07-08 — ara bekleme kafa karistiriyordu). Dedektor
                               # titremesi (tek-kare atlama) zaten VIS_STALE_S ile koprulenir;
                               # son gorusten itibaren toplam ~(VIS_STALE_S + bu) sn'de doner.
                               # Manuel GORSEL switch'te donus YOK (revert_izin=False), hep hover.
    VIS_EMA          = 0.4      # ex/ey EMA yumusatma (tek-kare yanlis tespiti bastir)
    # --- TAKIP (ByteTrack) ANAHTARLARI (2026-07-09, canli regresyon sonrasi) ---
    # TAKIP_AKTIF=False -> tracker DEVRE DISI: ham argmax tespit dogrudan beyne
    # (ByteTrack oncesi davranisla bire bir) -> canli sorun cikarsa hizli geri-donus.
    TAKIP_AKTIF      = True
    # --- gyro-CMC (jiroskop hareket telafisi) ---
    # Avcinin donusu (yaw/pitch/roll) uzak hedefin goruntudeki kutusunu kaydirir;
    # CMC bu kaymayi IMU attitude'undan turetilen homografiyle ONCEDEN telafi eder
    # (eslestirme oncesi Kalman merkezini warp'lar) -> hizli donuste iz kopmaz.
    # Girdi = KENDI attitude'umuz (ego-motion), HEDEF konumu DEGIL -> gorsel-faz
    # GPS yasagina UYGUN (ego-roll/pitch telafisinin emsali).
    # 2026-07-09: acildi -> CANLI KOTULESTIRDI (kullanici gozlemi + veri: CMC-acik ucus
    # 258 sn'de GORSEL_GUDUM'a HIC giremedi; CMC-kapali ucus girmisti). Muhtemelen
    # sim attitude isareti ters (Blokor B) -> ters CMC kaymayi 2x yapip donuste izi
    # kiriyor. KAPATILDI. Kod + emniyet knob'lari duruyor; DOGRU acmak icin once
    # arac/attitude_dogrula.py ile isaret dogrulanmali (gerekirse TAKIP_CMC_SIGN=-1).
    TAKIP_CMC_AKTIF  = False
    # ISARET ANAHTARI: sim attitude konvansiyonu (R_govde_to_dunya pitch/roll isareti
    # + Euler sirasi) bu simde truth ile HENUZ dogrulanmadi ("Blokor B", MEVCUT_DURUM).
    # Warp TERS yonde kaydiriyorsa (FPV'de donuste kutu hedeften UZAKLASIYOR) bunu
    # -1 yap -> att sirasi takas edilir, warp yonu tersine doner (kodu degistirmeden
    # canli duzeltme). Kesin dogrulama: arac/cmc_isaret_testi.py / attitude_dogrula.py.
    TAKIP_CMC_SIGN   = +1.0
    # EMNIYET: tek tikte CMC kutuyu en fazla bu kadar (kare genisligi orani) kaydirir.
    # Yanlis-isaret + buyuk yaw kutuyu ekrandan firlatip esleşmeyi aninda kirmasin;
    # asilirsa o tik warp ATLANIR (CMC'siz predict). Mesru hizli yaw ~%6·W/tik (8 FPS,
    # 60°/s) -> %25 tavani 4x marj birakir. 0 = clamp kapali.
    TAKIP_CMC_MAX_KAYDIRMA = 0.25
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
    IBVS_K_YAW       = 1.2       # yatay kazanc: yaw = SIGN*K*ex (clamp +-YAW_MAX) ⚙
                                # 0.85->1.2 (10 Tem VERI ucus 062231: YAKINken |ex| medyan
                                # 0.52/p90 0.75 -> hedef kadraj kenarina kaciyordu; sikilastir).
    IBVS_SIGN_YAW    = +1.0     # ex>0 (hedef SAGDA) -> burnu SAGA cevir; ters tepki gorursen -1
    IBVS_K_DIKEY     = 2.15      # dikey kazanc: thr = SIGN*K*(-ey) (clamp THR_DN..THR_UP) ⚙
                                # 8 Tem ucus (222830): kullanici 2.25 kullandi; 2.0'a cektim
                                # (2.25 salinim/asiri tepki riski). Dikey hata buyukse thr zaten
                                # doygun (clamp) — K'yi asiri buyutmek merkezlemeyi iyilestirmez.
    IBVS_SIGN_DIKEY  = +1.0     # hedef YUKARIDA (ey<0) -> TIRMAN (thr>0; GPS faziyla ayni kanon).
                                # SIM'de dikey TERS tepki gorursen -1 yap (tek isaret, tek yer).
    # --- YAKINLIK-OLCEKLI KAZANC (2026-07-10 VERI: yakinken merkezleyememe kok nedeni) ---
    # Fizik: hedefin GORUNTUDEKI acisal hizi ~ v_yan / mesafe. Yaklastikca (bbox buyudukce)
    # mesafe kuculur -> ayni yan hiz cok daha hizli piksel kaymasi yapar -> SABIT K_YAW/K_DIKEY
    # geride kalir, hedef kadraj KENARINA kacar (062231: YAKINken |ex| 0.52, yaw_cmd 0.60
    # TAVANDA doyuyor ama yetismiyordu). Cozum: yaw+dikey kazancini bbox boyutuyla OLCEKLE:
    #   k_yakin = 1 + YAKIN_KAZANC * clamp(boyut_f / BOYUT_HEDEF, 0, 2)
    # Uzakta (boyut~0) k_yakin=1 (yaklasma kararli, eski davranis); stand-off boyutunda
    # (boyut=HEDEF) k_yakin=1+KAZANC; daha yakinda 1+2*KAZANC tavani. Girdi yalniz bbox
    # boyutu (kameradan) -> GPS yasagina uygun. 0 = KAPALI (olcekleme yok, sabit kazanc).
    IBVS_YAKIN_KAZANC = 1.0     # yakinlik kazanc artisi (0=kapali; 1=stand-off'ta 2x, yakinda 3x) ⚙
    IBVS_ILERI       = 0.75     # ileri itki TAVANI (0..1; boyut yasasi bunu asamaz) ⚙
                                # 8 Tem ucus: kullanici 0.65 kullandi; 0.70'e (hedef ~18 m/s
                                # kaciyor, daha yakina sokulmak icin agresif yaklasma tavani).
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
    IBVS_BOYUT_HEDEF = 0.08     # bbox eksen orani hedefi (>= VIS_LOCK_PCT 0.06 + marj) ⚙
                                # 0.12->0.08 (10 Tem VERI 062231: %12'ye DALINCA hedefin acisal
                                # hizi yaw tavanini asiyor -> kadraj kenarina kaciyor, kilit
                                # dolmuyor. %8 = kilit esigi %6'nin uzerinde AMA merkezleyebildigin
                                # mesafede DUR (dalma) -> gereken donus hizi ~%33 azalir, kilit
                                # penceresi dolabilir. "Dal" yerine "stand-off'ta ortala" stratejisi).
    IBVS_K_BOYUT     = 20.0     # boyut hatasi -> ileri itki kazanci (0=KAPALI/eski yasa) ⚙
                                # 10->20 (10 Tem: BOYUT_HEDEF 0.08'e dusunce K=10 cok ERKEN
                                # frenliyordu — %2'de bile tavan yerine 0.6. K=20 -> ~%4.25'e
                                # kadar TAM yaklasma, sonra 4-8% bandinda frenleyip stand-off'ta
                                # otur: "uzaktan hizli yaklas, %8'de firmly dur" stratejisi).
    IBVS_GERI_MAX    = 0.30     # fazla yakinken geri itki tavani (0=asla geri gitme) ⚙
    # --- KAPANMA-HIZI FRENI (TTC / looming, 2026-07-10) ---
    # bbox HIZLI buyuyorsa (hedefe hizli kapaniyor -> ASACAK/carpacak) ileri itkiyi ONCEDEN
    # kis -> hedefi ASMADAN kilit bandina otur (boyut yasasi P->PD; D = bbox buyume hizi).
    # ileri -= FREN_HIZ * max(0, dboyut/dt). Tek knob. 0 = kapali. Hedefi asip kaybediyorsan
    # (kilit penceresi kisa) ARTIR; drone erken duruyor/yaklasamiyorsa DUSUR. TTC telemetride.
    IBVS_FREN_HIZ    = 8.0      # kapanma-hizi (dboyut/dt) -> ileri fren kazanci ⚙ (0=kapali)
    IBVS_MERKEZ_FREN = 1.1       # sapma buyudukce ileri kis: pitch *= max(0, 1 - FREN*r).
                                # 0 = hep tam gaz; buyuk deger = once ortala sonra ilerle ⚙
                                # 0.60->1.1 (10 Tem: hedef kenardayken ILERI'yi sertce kes ->
                                # "once ortala SONRA yaklas"; kenara kacarken dalip kaybetmeyi onler).
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
    # --- YUMUSAK GECIS / SOFT-HANDOFF (GPS->gorsel gecis surekliligi, 2026-07-09) ---
    # GPS ve gorsel yasa farkli mimaride; gecis aninda gorsel yasa (1) uzakta tam ILERI
    # lunge verip govdeyi yatirinca kamera dusuyor, (2) dikey nisani merkezden alttan-vur'a
    # ANIDEN kaydirinca ani alcalis veriyor -> hedef kadrajdan cikip gorsel temas kesiliyordu.
    # Cozum: gorsel faz basindan itibaren bu SURE boyunca ileri-itki ve dikey-nisan 0'dan
    # rampalanir (ibvs_gorsel.hesapla, s: 0->1). Yaw/dikey-ortalama ilk tikten tam guctedir.
    # Salt kamera verisi + faz-giris zamanlayicisi -> gorsel-faz GPS yasagina UYGUN.
    # 0 = KAPALI (eski davranis bit-ayni). Canli tune: cok uzunsa yaklasma gecikir, cok
    # kisaysa lunge geri gelir (slider; 0.6-1.5 sn dene).
    IBVS_HANDOFF_S     = 1.0    # gorsel faz basi yumusak-gecis rampasi (s); 0 = kapali ⚙
    # --- ALCALMA FRENI (gorsel anti-lift-carry, 2026-07-08) ---
    # GPS yolundaki alc_oncelik'in gorsel-faz aynasi: hedef nisan noktasinin ALTINDAysa
    # (eyy>0 = arac cok yuksekte) ileri itki carpimsal kisilir ->
    #   pitch *= clamp(1 - ALCAL_FREN*max(0,eyy), ALCAL_TABAN, 1)
    # Ileri-ucus tasimasi (lift carry) dusunce negatif thr gercekten alcaltir (THR_DN
    # yorumundaki ders: tam ileri ucusta -0.40 bile tirmanmayi durduramiyordu).
    # Tirmanis tarafi (eyy<0) etkilenmez. Girdi yalniz goruntu buyuklugu -> kural uygun.
    IBVS_ALCAL_FREN  = 1.5      # 0=kapali; ~eyy 0.53'te tabana iner ⚙ (8 Tem ucus:
                                # kullanici 2.0->1.5 kullandi — ileri itki daha az frenlensin,
                                # yaklasma acilsin; yak-agirlikli fren zaten uzakta baypas ediyor).
    IBVS_ALCAL_TABAN = 0.2      # fren tabani (asla tam durma; biraz kapanis kalsin).
                                # GPS alc_oncelik 0.15 tabaninin gorsel karsiligi; slider DISI.
    # --- EGO-PITCH TELAFISI (2026-07-08; kacak-tirmanma kok nedeni) ---
    # Ileri itki govdeyi one yatirinca kamera (govdeye sabit) asagi doner -> hedef goruntude
    # YUKARI ziplar -> yasa "hedef kacti, TIRMAN" okuyordu (log 204331: corr(pitch,ey)=0.70;
    # drone hedefin 10 m ALTINDAYKEN +0.70 tirmanis). Dikey hata kendi pitch'ten arindirilir:
    #   ey_dunya = ey_f - GAIN*tan(own_pitch)/tan(VFOV_yari)   (ibvs_gorsel.hesapla)
    # Kendi IMU'muz = ego-motion (ego-roll telafisiyle ayni emsal) -> kural ihlali DEGIL.
    IBVS_EGO_PITCH_GAIN = 0.4   # 1.0->0.4 (9 Tem ucus 000321 VERI: GAIN=1.0 kalici govde
                                # yatikligini (-37 deg, ileri itki artinca) "sahte yukari"
                                # sanip ASIRI telafi ediyordu -> ey isareti donuyordu (ham
                                # -0.36 -> telafili +0.37) -> yasa surekli sert ALCAL veriyordu
                                # (thr -0.63, %93) -> drone hedefin altina inip hedefi kadraj
                                # USTUNDEN kaciriyordu (dikey merkezleme cokuyordu). Veriden
                                # taranan optimal: 0.4 -> eyy~0 (hedef nisanda) + |ey| dikey
                                # kadraj-ici en iyi (p90 0.77->0.59). 0=tam kapali.
    # --- ONGORULU YAW LEAD (pose) — 2026-07-10 KALDIRILDI (pose kapali) ---
    # Pose sistemden cikarildi (POSE_AKTIF=False) -> kanat-ucu roll-lead OLU parametreler
    # IBVS_K_ROLL_LEAD/SIGN_ROLL/ROLL_CONF_MIN/ROLL_EMA/EGO_ROLL_GAIN/ASPECT_MIN/POZ_STALE_S
    # SILINDI (git gecmisinde). ibvs_gorsel._roll_lead artik no-op (lead=0).

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

def rate_limit(target, prev, max_delta):
    return prev + clamp(target - prev, -max_delta, max_delta)


# ==========================================================
#  GERCEK-GPS (DEV/test) kaynagi: filtreyi ATLAyip oyunun debug-truth hedef
#  konumunu kullanir (filtre/guduum ayristirma testi: sorun filtrede mi
#  guduumde mi?). GPSTakip'in YALNIZ hedef-temizleme adimini override eder;
#  kontrol yasasi (kalkis/PD/PID/DR) birebir ayni calisir.
# ==========================================================
class _GercekGPSTakip(GPSTakip):
    def sifirla(self):
        super().sifirla()
        self._gt_prev_p = None          # truth sonlu-fark hiz kestirimi durumu
        self._gt_prev_t = None
        self._gt_vel = np.zeros(3)

    def _truth_hiz(self, p):
        now = time.perf_counter()
        if self._gt_prev_p is None or self._gt_prev_t is None:
            self._gt_prev_p = p.copy(); self._gt_prev_t = now
            return self._gt_vel
        dt = now - self._gt_prev_t
        if 1e-3 < dt < 0.5:
            raw = (p - self._gt_prev_p) / dt
            self._gt_vel = 0.7 * self._gt_vel + 0.3 * raw
            self._gt_prev_p = p.copy(); self._gt_prev_t = now
        elif dt >= 0.5:                                # bayat -> resetle
            self._gt_prev_p = p.copy(); self._gt_prev_t = now
        return self._gt_vel

    def _hedef_temizle(self):
        self.son_ham = self.drone.get_target_location()   # debug olcumu icin tut
        dbg = self.drone.get_debug_truth()
        if dbg.get("available"):
            p = np.array(dbg["target"]["position"], float)
            self.son_temiz = p
            self.son_z_anlik = float(p[2])
            self.son_xy_anlik = np.array([p[0], p[1]], float)
            self.son_hiz = self._truth_hiz(p)
            self._fresh = True
        else:
            self._fresh = False
        return self.son_temiz


# Guduum kaynagi -> GPS-takip fabrikasi. "gercek" truth'a gider (sim/test);
# "filtre" = tek uretim yolu (fusion/gnss_filtre + guidance/gps_takip).
def _gps_uret(drone, kaynak):
    return _GercekGPSTakip(drone) if kaynak == "gercek" else GPSTakip(drone)


class AvciKontrol:
    def __init__(self, drone, debug_olc=True, kaynak="filtre"):
        self.drone = drone
        if kaynak == "v2":                  # eski ad (geriye-uyum) -> tek uretim filtresi
            kaynak = "filtre"
        self.kaynak = kaynak                # "filtre" | "gercek"
        # GPS fazinin TEK SAHIBI: kalkis + GNSS temizleme (fusion/gnss_filtre) +
        # olu-hesap (DR) + PD/PID + kendi rate-limit'iyle komut gonderimi.
        self.gps = _gps_uret(drone, kaynak)
        self.durum = "ARAMA"                # ARAMA(yaklasma) -> KILIT(handoff) -> GORSEL_GUDUM
        self.handoff = False

        # kendi YATAY hiz vektoru (konum sonlu-fark, EMA) — YALNIZ log/teshis
        self._own_pxy = None
        self._own_tv = None
        self._own_v = np.zeros(2)

        # debug olcum birikimi (filtre ciktisinin gercege hatasi; sim/teshis)
        self.debug_olc = debug_olc
        self.ham_hatalar = []
        self.filtre_hatalar = []
        self.bozukluk_sayac = {}

        # ucus logu (Cfg.LOG_ENABLE) - lazy-open, uzunca zaman-damgali dosya
        self._log_f = None
        self._log_w = None

        # --- GORSEL GUDUM (basit IBVS) durumu ---
        # son_tespit: server.dedektor_dongusu'nin beyin_lock icinde yazdigi son bbox dict.
        self.son_tespit = None          # {cx,cy,w,h,conf,W,H,t} | None
        self.son_tespit_t = None        # o tespitin perf_counter zamani (bayatlik kontrolu)
        self.son_poz = None             # normalize poz dict | None (pose kapali; arayuz uyumu)
        self.son_poz_t = None
        self._vis_pos_count = 0         # ardisik gecerli-tespit (kilit histerezisi)
        self._vis_lost_count = 0        # ardisik kayip (hover -> GPS'e donus karari)
        self._vis_ilan = False          # "GPS kesildi" anonsu bir kez basilsin
        self._vis_v = None              # goruntu-hizi (px/s; son iki GERCEK tespitten, EMA'li)
        self.vis_kopru = False          # bu tik KOPRU (olu-hesap) tespitiyle mi? (telemetri/log)
        self.ibvs = AvciIBVS()          # merkez->bbox cizgisi (tek gorsel yasa; basit IBVS)
        self.ibvs_tlm = {}              # son IBVS telemetrisi (server build_telemetry okur)
        self.vis_mode = "OTO"           # guduum pipeline switch (test): OTO | GPS | GORSEL
        # --- KILITLENME ISTERI SAYACI (sartname 6.1.2/6.1.4; SALT GOZLEM, komuta girmez) ---
        self.kilit_win = deque()        # (t, kilit_anlik) ornekleri — son VIS_WIN_S penceresi
        self.kilit_sure = 0.0           # penceredeki kumulatif kilit suresi (s)
        self.kilit_anlik = False        # bu tik kilit kosulu (AV icinde + boyut >= LOCK_PCT)
        self.kilit_ok = False           # LATCH: pencere isteri (>=WIN_NEED_S) saglandi
        self.kilit_boyut = None         # bu tik bbox eksen orani max(w/W, h/H) (telemetri)

    # ---- GPS durum PROXY'leri: tek dogruluk kaynagi gps_takip (server/log okur) ----
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
    # Uygulanan SON komut da gps_takip'te yasar: gorsel _send ayni sozlugu
    # guncelledigi icin GPS<->GORSEL gecislerinde rate-limit SUREKLI kalir
    # (gecis aninda komut sicramasi olmaz).
    @property
    def prev(self): return self.gps.prev
    @prev.setter
    def prev(self, v): self.gps.prev = dict(v)

    # ----------------------------------------------------------------
    #  Guduum kaynagini CANLI degistir (Filtre / Gercek butonlari).
    #  Yeni GPSTakip TAZE baslar (filtre + kontrol + kalkis durumu); FSM ve
    #  gorsel durum sifirlanir (temiz soft-start).
    # ----------------------------------------------------------------
    def set_kaynak(self, kaynak):
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
        # ucus logu: yeni gorev -> yeni dosya (sonraki tik taze zaman-damgali acar).
        # NOT: ayni kaynak ust uste secilirse bu metod erken doner (yukarida) -> dosya
        # donmez; server "Gorev Baslat"ta log_dondur()'u AYRICA kosulsuz cagirir.
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
    #  Hedef GNSS isleme — gps_takip'e DEVREDILDI ("gercek" modda truth).
    #  Server manuel/pasif modlarda da cagirir: filtre olcumu gorev disinda da aksin.
    # ----------------------------------------------------------------
    def _hedef_temizle(self):
        return self.gps._hedef_temizle()

    # ----------------------------------------------------------------
    #  Kendi YATAY hiz vektoru (cm/s, dunya): konum sonlu-fark + EMA.
    #  YALNIZ ucus logu/teshis icin (vown_x/y kolonlari); komuta girmez.
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
    #  Debug olcum: filtre gercekten ham'dan iyi mi? (sim/teshis; gudume girmez)
    # ----------------------------------------------------------------
    def _debug_olc(self):
        dbg = self.drone.get_debug_truth()
        if not dbg.get("available") or self.son_temiz is None or self.son_ham is None:
            return
        gercek = np.array(dbg["target"]["position"])
        ham = np.array(self.son_ham)
        self.ham_hatalar.append(np.linalg.norm(ham - gercek))
        self.filtre_hatalar.append(np.linalg.norm(np.asarray(self.son_temiz, dtype=float) - gercek))
        for ad in self.drone.get_active_corruption():
            self.bozukluk_sayac[ad] = self.bozukluk_sayac.get(ad, 0) + 1

    # ----------------------------------------------------------------
    #  TEK kontrol adimi (50 Hz, server.kontrol_dongusu cagirir).
    #  GPS fazi TAMAMEN guidance/gps_takip.GPSTakip'e devredilmistir: kalkis,
    #  GNSS temizleme (fusion/gnss_filtre), kesintide olu-hesap (DR), yatay PD +
    #  dikey PID ve komut gonderimi ONUN icindedir. Bu metodun isi:
    #    1) gorsel tespit + FSM anahtari (ARAMA/KILIT <-> GORSEL_GUDUM),
    #    2) GORSEL fazda basit IBVS komutu (yonelim YALNIZCA kameradan),
    #    3) GPS fazinda gps.adim() delegasyonu + handoff mesafesi + ucus logu.
    # ----------------------------------------------------------------
    def adim(self):
        drone_pos = np.array(self.drone.get_drone_location())   # TEMIZ (cm)
        rot_rpy = self.drone.get_drone_rotation()               # (roll,pitch,yaw) DERECE
        yaw_m = rot_rpy[2]
        drone_yaw = math.radians(yaw_m) if Cfg.ROT_IN_DEGREES else yaw_m
        t = time.perf_counter()
        v_own = self._own_hiz(drone_pos[:2], t)                 # yalniz log/teshis

        # 1) GUDUM PIPELINE SECIMI (switch: self.vis_mode) + GORSEL kesme.
        #    OTO   : conf>=VIS_CONF_MIN kareler ard arda VIS_N_LOCK olunca GORSEL'e kilitlenir;
        #            kayip VIS_LOST_TO_GPS_S'i asarsa GPS'e geri doner (re-acquire).
        #    GPS   : gorsel yol KAPALI (gorseldeysen GPS'e doner) -> hep GPS.
        #    GORSEL: kilidi ATLA, hemen GORSEL; kayipta GPS'e DONME (zorlanmis).
        #    GORSEL kilitliyken GPS yolu HIC calismaz (return) -> gorsel temas
        #    VARKEN GPS yonelimi kullanilmaz. prev tek kaynak (gps.prev) -> gecisler sarsintisiz.
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
                # HANDOFF: GPS hedefe YETERINCE YAKLASMIS OLMALI (self.handoff, onceki GPS
                # tikinde d_h<HANDOFF_RANGE ile isaretlenir) VE YOLO kilidi (ard arda
                # VIS_N_LOCK gecerli tespit). Ikisi birden saglaninca saldiri KAMERAYA
                # devredilir; oncesinde GPS yaklasmaya devam eder (uzaktan yanlis-kilit yok).
                if (Cfg.AUTO_VISUAL_HANDOFF
                        and self._vis_pos_count >= Cfg.VIS_N_LOCK and self.handoff):
                    self.durum = "GORSEL_GUDUM"
                    # YUMUSAK GECIS: gorsel yasayi TAZE basla -> EMA sifirdan + soft-handoff
                    # rampa penceresi (ibvs._handoff_t) ilk gorsel tikte damgalanir.
                    self.ibvs.sifirla()
                    if not self._vis_ilan:
                        self._vis_ilan = True

        if self.durum == "GORSEL_GUDUM":
            # kendi roll+pitch'imiz (IMU) -> ego-motion telafileri (hedef verisi DEGIL):
            # pitch, ileri yatista kameranin dusmesinin urettigi sahte dikey hatayi temizler.
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
                # GNSS filtresini SICAK tut: gorselde de yeni paketler islenir -> GPS'e
                # ani donuste kestirim taze olur ve gps_takip'in DR sayaci sahte "uzun
                # kesinti" gormez. KURAL NOTU: bu cagri yalnizca filtre DURUMUNU gunceller;
                # ciktisi gorsel fazda HICBIR hareket komutuna girmez (IBVS yalniz bbox okur).
                self.gps._hedef_temizle()
                if self.gps._fresh:
                    self.gps._son_fresh_t = t
                if self.debug_olc:
                    self._debug_olc()
                self._log_gorsel(t, drone_pos, yaw_m, drone_yaw, v_own, tespit)
                return
            # sonuc None (yalnizca OTO) -> gorsel UZUN kayip -> GPS yolu BU tik calisir

        # ==================== [GPS-YAKLASMA — gps_takip devraldi] ====================
        # Kalkis + GNSS temizleme + kesintide DR + PD/PID + rate-limit + gonderim
        # gps.adim() icinde (guidance/gps_takip.py; sabitleri GPSCfg).
        self.gps.adim()
        if self.debug_olc:
            self._debug_olc()

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
                "drone_pos": drone_pos, "drone_yaw": drone_yaw,   # _log: truth + nose_off_true icin
            })

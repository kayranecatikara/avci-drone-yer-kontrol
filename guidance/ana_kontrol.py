# -*- coding: utf-8 -*-
"""
================================================================================
AVCI DRONE — ANA KONTROL DONGUSU  (guduum + karar mekanizmasi, tek dosya)
================================================================================
GIRIS NOKTASI: main.py -> web.server.main() -> beyin = AvciKontrol(drone),
50 Hz beyin.adim(). Manuel/pasif modda server yalnizca beyin._hedef_temizle()
cagirir (J olcumu akar, ucus komutu uretilmez). Ayrinti: guidance/GUDUM_HARITA.md

FAZLAR / FSM (self.durum):
  KALKIS -> AGL kapili tirmanis (kopru/entegre.py). Zemin, gorev basinda aracin
            irtifasindan alinir; KOPRU_KALKIS_AGL'e ulasinca yasa devreye girer.
  ARAMA  -> GPS yaklasma: GAZEBO'DAN TASINAN YASA (control/guidance/gps_guidance.py,
            DEGISMEZ) hiz komutu uretir; KOPRU (kopru/dow_kopru.py) bunu DoW
            stick'ine cevirir — kopru ArduCopter'in yerini alir. Bozuk hedef GPS'i
            koprude CT-EKF'ten (fusion/inovasyonlu_j_v2) gecer. Istasyon: hedefin
            RANGE_SET slant menzilinde, hiz yonunun gerisi + alti.
            Denetim/olcumler: docs/kopru_denetim.md
  KILIT  -> ayni hat; yasanin d_h < 20 m esigi (gorsel faz devralmaya hazir).
  NOT (2026-08-07): eski PD/standoff/speed_cap GPS yasasi kullanici karariyla
  SILINDI (~300 satir). Gerekirse git gecmisinde: eca3b4a.
  GORSEL_GUDUM -> yonelim YALNIZCA kameradan: YOLO bbox (server dedektor thread
            -> set_gorsel_tespit) -> kopru/tespit_akisi -> supervisor/bbox_ibvs
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
from guidance.kilit_sayaci import KilitSayaci, KilitCfg             # gorsel: merkez->bbox cizgisi (basit IBVS)


class DevirCfg(KilitCfg):
    """GPS -> GORSEL DEVIR olcutu (SARTNAME SAYACI DEGIL).

    ── NEDEN AYRI (2026-08-14, canli olcumle bulundu) ────────────────────────
    Sartname kilidi kutu >= %6 istiyor. Talon 1.7 m acikliginda; 1920 px
    kadrajda kutu ~945/mesafe piksel eder:
          30 m -> %1.6   20 m -> %2.5   12 m -> %4.1   8 m -> %6.2
    Yani sartname kilidi ANCAK ~8 metrede dolabiliyor -> devir hep 8 m'de
    oluyordu.  Ama 8 metrede hedefin acisal hizi:
          w = v/d = 18/8 = 2.25 rad/s = 129 °/s
    Kameranin yatay gorusu 122° -> hedef kadraji 0.9 SANIYEDE terk ediyor.
    GPS yasasi o ana kadar hedefi aktif merkezliyordu; devirde GPS kesilince
    gorsel yasa devralana dek hedef ucup gidiyordu.
    KANIT (14 Agu, 5 gorsel faz): uc fazda kutu goren kare 0/59, 0/59, 1/71
    ve yaw komutu HIC degismemis (elinde kutu yok, neye gore donsun?).

    ── COZUM ────────────────────────────────────────────────────────────────
    Devir olcutunu SARTNAMEDEN AYIR ve daha UZAKTA tetikle:
      * LOCK_PCT %6 -> %2   : devir ~25 m'de olur (acisal hiz 41 °/s, kadraji
                              gecme 3.0 sn -> gorsel yasaya devralma payi var)
      * AV bandi daraltildi : hedef devir aninda kadrajin ORTASINA yakin olsun
                              ki gorsel yasa marjla baslasin (25-75 -> 35-65)
    Sartname sayaci (AvciKontrol.kilit) DOKUNULMADI; ekrandaki "X/5.0 s"
    ve yarisma kanit zinciri aynen kalir.
    """
    LOCK_PCT = float(os.environ.get("AVCI_DEVIR_PCT", 0.02))   # ~25 m
    AV_X = 0.35            # yatay %35-%65 (sartname %25-%75'ten dar)
    AV_Y = 0.25            # dikey  %25-%75 (sartname %10-%90'dan dar)
    # WIN_S / WIN_NEED_S / BOSLUK_MAX_S: KilitCfg'den aynen (5 s / 10 s pencere)

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
#   [GPS-YAKLASMA]  : YALNIZ durum != GORSEL_GUDUM iken. Yasanin KENDI kazanclari
#                     gps_guidance.Cfg'de (DONDURULDU); burada yalniz KOPRU_*
#                     baglama parametreleri var. Gorsel faza KARISMAZ.
#   [GORSEL]        : basit IBVS (ibvs_gorsel.py) + kilit isteri sayaci + kayip yonetimi.
# Canli-tune: web arayuzu /api/tune ile TUNE_ALLOW listesindekileri degistirir.
# ==========================================================
class Cfg:
    # ================= [ORTAK] =================
    # --- BIRIM / FRAME / ISARET (SIMDE DOGRULA) ---
    ROT_IN_DEGREES = True       # get_drone_rotation derece dondururse True
    # Dikey isaret: SDK +1=tirman / UE Z-yukari -> dogru deger +1.0 (sim ile dogrulandi:
    # +1 hedef irtifasina yakinsar, -1 irtifayi artirip kacar). Oyunun Z ekseni
    # gercekten TERS oldugu KANITLANIRSA -1 yap; aksi halde +1 birak.

    # --- DONGU (server.py / calistir 50 Hz surer) ---
    LOOP_HZ = 50.0

    # ================= [GPS-YAKLASMA] (durum != GORSEL_GUDUM) =================
    # --- KALKIS / ARAMA IRTIFASI ---

    # --- HANDOFF (histerezisli) ---

    # --- GPS HATTI: Gazebo yasasi + DoW koprusu (2026-08-07) ---
    # GPS yaklasmasi Gazebo'dan tasinan yasayla yapilir (gps_guidance.py DEGISMEZ);
    # hiz komutu kopru (kopru/dow_kopru.py) tarafindan DoW stick'ine cevrilir —
    # kopru ArduCopter'in yerini alir. Denetim: docs/kopru_denetim.md.
    # KALKIS da bu hatta (AGL kapili). Eski PD/standoff yasasi 2026-08-07'de
    # kullanici karariyla SILINDI; gerekirse git gecmisinde: eca3b4a.
    # ── BIREBIR KIPI (2026-08-10, kullanici karari) ───────────────────────────
    # "aynen birebir olmasi lazim". True = Kayran'in yasasi KENDI sabitleriyle
    # kosar; asagidaki KOPRU_* degerleri (eski yasa icin olculmustu) UYGULANMAZ.
    # Yasa dosyalari zaten klonla hash-birebir; ezilen sey calisma degerleriydi:
    #   RANGE_SET 8.0 | ISTASYON_ELEV 15 | IC_KAYMA 14 | V_MAX 18 | ELEV_DIN True
    # False yaparsan eski onayli konfig geri gelir (A/B icin duruyor).
    # ⚠ 2026-08-10 DUZELTME: birebir=True YANLISTI. "Birebir" derken yasanin
    # branch'teki HAM VARSAYILANLARINI uyguladim; oysa kullanicinin DoW'da
    # onayladigi konfigurasyon bu dortlu istisnaydi (hepsi olcumle turetildi,
    # kopru/README.md B.7): RANGE_SET=6.9, ISTASYON_ELEV=25, IC_KAYMA=0,
    # V_MAX=22 + ELEV_DINAMIK kapali. birebir=True bunlari atinca arac
    # bambaska karakterde uctu (RANGE 8, ELEV 15, IC 14, V_MAX 18, ELEV_DIN
    # ACIK) -> kullanici hakli olarak "bu benim GPS'im degil" dedi.
    # False = aylarca ucurdugumuz, onayli DoW konfigurasyonu.
    KOPRU_BIREBIR      = False
    # V_MAX tek istisna kancasi. None = yasanin kendi 18'i.
    # OLCUM: DoW hedefi zamanin %62-66'sinda 18 m/s USTUNDE (ort 18.2, tepe 20.8)
    # -> 18'de arac hedeften yavas kalir. Istasyon tutulamiyorsa 22.0 yap.
    KOPRU_VMAX_ISTISNA = None
    # ── 2026-08-14: 6.9 -> 25.0 (canli olcumle) ────────────────────────────
    # ESKI GEREKCE: "kutu orani 0.4472/R -> 6.9 m'de %6.5, esik %5" yani
    # istasyon, SARTNAME kilidinin boyut esigini tuttursun diye 6.9 m'ye
    # kurulmustu. O hesap dogru ama TEK BOYUTLU: acisal hizi hic saymamis.
    #
    # ATLANAN FIZIK: hedefi kadrajin ortasinda tutmak icin arac hedefle AYNI
    # acisal hizda donmek zorunda -> w = v/d  (hedef ~18 m/s daire ciziyor):
    #        25 m ->  41 °/s      15 m ->  69 °/s      10 m -> 103 °/s
    #       6.9 m -> 150 °/s     2.8 m -> 368 °/s
    # 150 °/s bir hava araci icin ulasilamaz. Yani istasyon TAM DA takibin
    # imkansiz oldugu mesafeye kuruluyordu.
    # KANIT (14 Agu kaydi): drone hedefin 2.8 m'sine kadar girdi (vurus esigi
    # 3.0 m -- yani GPS yasasi isini yapti) ama "GORUSTEN CIKIS: 10 kez" ve
    # kilit 2.2/5.0 s'de takildi; her cikista sayac sifirlandi.
    #
    # YENI AKIS: 25 m'de istasyon tut -> 41 °/s ulasilabilir -> hedef kadrajda
    # kalir -> devir kilidi (DevirCfg, %2) 5 sn dolar -> GORSEL faz devralir ->
    # kapanmayi/dalisi gorsel yasa yapar (bbox_ibvs BOYUT_REF ile).
    # Yani "uzaktan kilitle, sonra dal" -- gercek angajman sirasi.
    # Geri almak: 6.9 yaz.
    # ⚠ 25.0 -> 18.0 (2026-08-16, UCUSTA OLCULDU).
    # Istasyon = RANGE_SET*cos(ELEV) arka + RANGE_SET*sin(ELEV) alt.
    # 25 m / 25° -> 22.66 m arka + 10.57 m ALT. Truth ile dogrulandi: hedef
    # bizden +10.2 m yukarida (22277 ornek). Iki sonucu vardi:
    #   1) DEVIR KAPISI dolmuyor: olculen R*max(w,h)=310 px·m, kapi 14 px ->
    #      ancak 22.2 m ICINDE atesleniyor; istasyon 22.66 m'de oldugu icin
    #      yalnizca gecici sarkmalarda geciyor.
    #   2) DIKEY: gorsel yasanin nisan DENGESI hedefin ~5° altidir; istasyon
    #      25° altta birakiyor. 20° fark VZ_MAX=3 ile kapatilamiyor, vz faz
    #      boyunca tavana yapisik kaliyor ve faz 1.8 s'de oluyor.
    # 18 m -> 17.7 m arka + 3.1 m alt (ELEV=10 ile). Geri almak: 25.0.
    # ⚠ 18.0 -> 9.0 (2026-08-16, SUPURULDU). Istasyon mesafesi-iska egrisi:
    #     22.7m -> 19.54 | 18m -> 18.73 | 13m -> 15.62 | 9m -> 12.73
    #      7m -> 13.60   |  5m -> 13.75      -> DIP 9 m'de, altinda kotulesiyor
    # (9 m'nin altinda gereken acisal hiz firliyor: 10 m'de 103 deg/s ve
    #  MAX_ACCEL=12 onu karsilamiyor -- bkz. yukaridaki :191-196 argumani.)
    # ⚠ 9.0 -> 7.0 (2026-08-16). SEBEP: KILIT ISTERI, iska degil.
    # Sartname (kilit_sayaci.py 6.1.2/6.1.4): bbox EN AZ BIR eksende ekranin
    # >=%5'i (biz %6 marjla sayiyoruz) + merkez AV icinde + 10 s pencerede
    # kumulatif >=5 s. Kutu orani = 531.36*1.78/(1920*R) = 0.493/R:
    #     R=25 m -> %2.0   (ekran kaydinda gorulen: "boyut %2 / %6 ✗")
    #     R= 9 m -> %5.5   (onceki istasyon -- %6 esiginin KIL PAYI ALTINDA)
    #     R= 7 m -> %7.0   (marj var)
    # ⚠ Bugun "en yakin gecis"i optimize etmistim; gorevin olcutu O DEGIL.
    # Gorev 8 m'de 5 s DURMAYI istiyor -> kesisme degil ISTASYON TUTMA problemi.
    # ⚠ 2026-08-17: ENV'e acildi (AVCI_KOPRU_RANGE) ve gerekce OLCULDU.
    #   menzil x max(w,h) = 743 px*m (n=966 canli tespit). Sartname kilit
    #   sayaci kutunun ekranin %6'si olmasini istiyor = 115 px -> R <= 6.45 m.
    #   7.0 m'de kutu 106 px = %5.5 -> sayac TIKLAMAZ (kil payi kacirir).
    #   Tezgahta gercek Talon yorungesinde istasyonu 8.5 -> 6.0 m cekmek
    #   5 s kesintisiz kilit oranini %20 -> %71 yapti.
    KOPRU_RANGE_SET    = float(os.environ.get("AVCI_KOPRU_RANGE", "6.0") or 6.0)
    KOPRU_V_MAX        = 22.0   # m/s; onaylanmis TEK yasa istisnasi (olcumle)
    # ⚠ 2026-08-17 ENV'e acildi (AVCI_KOPRU_IC). Gerekce ve SINIR:
    #   Ic-daire kaymasi istasyonu hedefin donus MERKEZINE dogru iter -> kose
    #   keser. Arkeoloji bunu istiyor: kesme geometrisinde (aspect<90) vurus
    #   %42, saf kuyrukta %0.5 (191 denemede 0).
    #   AMA kayma istasyonu hedeften UZAKLASTIRIR ve kilit bandini bozar:
    #      istasyon_hedef_mesafesi = sqrt(RANGE_SET^2 + kayma^2)
    #   Kilit kapisi 6.45 m (olculen K=743 px*m, LOCK_PCT=0.06). RANGE_SET=6.0
    #   ile kayma en fazla sqrt(6.45^2 - 6.0^2) = 2.37 m olabilir.
    #   Eski 14 m SABIT kayma tam bu yuzden kilidi imkansiz kiliyordu (yorum
    #   dogruydu). ORANLI surum (AVCI_GPS_IC_ORAN) hedefin ~25 m yaricapinda
    #   0.09 orani ile ~2.3 m verir -- bandi bozmadan kose keser.
    KOPRU_IC_KAYMA     = float(os.environ.get("AVCI_KOPRU_IC", "0.0") or 0.0)
    KOPRU_GNSS_FILTRE  = True   # bozuk hedef GPS'i CT-EKF'ten gecir (fusion/inovasyonlu_j_v2)
    KOPRU_KALKIS_AGL   = 40.0   # m AGL; gorev basi tirmanis (eski dunya-Z kapisi silindi)
    # Istasyonun LOS yukselisi. Dikey ayrim = RANGE_SET * sin(ELEV):
    #     15 deg -> 1.79 m alt (olculen 1.71) — Talon kanat acikligi 1.718 m
    #               kadar; carpisma payi YOK (bir kosuda 1.4 m'de carpti)
    #     25 deg -> 2.92 m alt (+%63 pay) + hedef kamera merkezine oturur
    #               (kamera tilt'i de 25 deg) + kutu orani DEGISMEZ (yalniz R'ye bagli)
    # Gazebo'da ORIJINALI 25'ti; 15'e inis sebebi ArduPilot'un WP_ACC_Z=1 m/s^2
    # dikey rampasiydi (terminalde 4.65 m'yi kapatmaya sure yetmiyordu). DoW'da
    # dikey kanal KOPRUNUN kendisi ve ~1.3 m/s^2 olculdu -> o kisit YOK.
    # KALICI (2026-08-07, W kosusu + kullanici onayi). Geri donus: 15.0.
    # ⚠ 25.0 -> 10.0 (2026-08-16). Yukaridaki 25° gerekcesi RANGE_SET=6.9
    # iken yazilmisti; o zaman dikey ayrim 6.9*sin(25°) = 2.92 m idi ve
    # "+%63 carpisma payi" hesabi ONA aitti. 2026-08-14'te RANGE_SET 6.9 -> 25
    # yapilinca dikey ayrim 2.92 -> 10.57 m'ye (3.6 KAT) cikti ve bu, o
    # degisiklige ait yorum blokunda HIC anilmadi -- tasarim degil, gozden
    # kacmis yan etki. (Kanit: tests/test_kopru_konfig_kilidi.py hala
    # "6.25 m arka + 2.92 m alt" iddia ediyor ve FAIL veriyor.)
    # 10° + RANGE_SET 18 -> 3.13 m alt: dogrulanmis-guvenli 2.92 m'nin
    # UZERINDE, ve gorsel yasanin 5°'lik nisan dengesine yakin.
    # ⚠ CANLI AYARLANAMAZ: ist_elev dongu ONCESI bir kez hesaplaniyor
    # (gps_guidance.py:391) ve ELEV_DINAMIK kapali. Degisiklik icin YENIDEN
    # BASLATMA sart -- slider'a koymak SAHTE A/B uretir.
    # ⚠ 10.0 -> 15.0 (2026-08-16). RANGE_SET 9->7 olunca dikey ayrim
    # 7*sin(10°) = 1.22 m'ye duserdi; Talon kanat acikligi 1.718 m ->
    # ISTENMEYEN TEMAS riski. 15° -> 7*sin(15°) = 1.81 m, kanat acikliginin
    # hemen ustunde. ⚠ Bu bir odunlesme: acik buyudukce kamera cercevelemesi
    # bozulur (yasanin nisan dengesi +4.9°), kucuk kaldikca temas riski artar.
    KOPRU_ISTASYON_ELEV = 15.0

    # ── HIBRIT GUDUM: GPS <-> GORSEL faz dongusu (Kayran'in supervisor'u) ──
    # False = bugunku davranis (yalniz GPS fazi, gorsel faz eski IBVS'imizde).
    # True  = kopru run_hybrid kosar:
    #     GPS fazi --[15 karelik pencerede 10 tespit, conf>=0.5]--> GORSEL faz
    #     GORSEL   --[20 ardisik tespitsiz kare]--> GPS fazina don
    #   Menzil kapisi KAPALI (D0 kurali: gorsel temas kurulunca GPS YASAK).
    #   Gorsel yasa bbox_ibvs — imzasinda get_plane YOK, GPS erisimi YAPISAL
    #   olarak imkansiz. Tespit akisi kopru/tespit_akisi.py uzerinden.
    # ⚠ Esikler KARE SAYISI cinsinden ve yasa ~30 Hz varsayiyor; bizim dedektor
    #   ~8-9 FPS -> kilit ~1.7 s, kayip ~2.2 s'ye denk gelir (kullanici karari:
    #   sayilara DOKUNULMADI). Etkisi telemetride `akis` alaninda gorunur.
    # 2026-08-10: ILK HIBRIT UCUSU icin ACILDI (kullanici karari). Gorsel faz
    # DoW'da bugune kadar HIC kosmadi; bu ucus dogrulama ucusudur.
    # 2026-08-13: GORSEL FAZIN DoW'DAKI ILK KOSUSU icin ACILDI.
    # Once yapilanlar: (1) yasa dal HEAD'ine senkronlandi (12/12 birebir),
    # (2) get_iris roll ISARETI duzeltildi — yeni gorsel yasa roll'u T1a
    #     telafisinde KOMUTA sokuyor, ters isaret 14.6 deg'e kadar ters yonde
    #     hata uretiyordu, (3) GPS-only regresyon kosusu temiz (R2: istasyon
    #     2.91 m alt / 25.0 deg, kilit %5 3/3), (4) panel anahtarlari baglandi.
    # Sorun cikarsa TEK SATIR: False -> yalniz GPS fazi, davranis bit-ayni.
    KOPRU_HIBRIT = True
    # GORSEL FAZ KAYIP ESIGI (kare). Yasanin kendi degeri 20 -> 30 Hz varsayimiyla
    # 0.66 s demekti. Bizim dedektor CANLI ~15 FPS (olculdu) ve duzenli 0.5-1 s
    # tespit deligi aciyor -> 20 kare ~1.3 s'de faz OLUYOR. OLCUM (11 Agu, 5 dk):
    #   hibrit ACIK : 130 gecis, gorsel faz ort 2.7 s, istasyonda kalma %32
    #   hibrit KAPALI: istasyonda kalma %100, arka 5.80 m (tasarim 6.25)
    # Yani surekli faz degisimi GPS yasasini her seferinde SOGUK baslatiyor ve
    # istasyon hic oturmuyor. 60 kare ~4 s: tipik dedektor deligini yutar, gercek
    # kaybi hala yakalar. Yasa DOSYASINA dokunulmaz; kopru setattr ile uygular.
    # 0 = yasanin kendi degeri (20) kullanilir.
    # 2026-08-15: 60 -> 20 (sartname: "ust uste 20 karede tespit edemezse
    # GPS gudumune gecmelidir"). 60'a cikarilma gerekcesi "dedektor 15 FPS
    # ve 0.5-1 s tespit deligi aciyor" idi; o olcum talon_v2 ile yapilmisti.
    # talon_v3 ile OLCULDU: hedef kadrajdayken tespit 31/31 kare = %100.
    # Gerekce ortadan kalkti -> yasanin kendi degeri (20) kullaniliyor.
    KOPRU_KAYIP_M = 20

    # NOT (2026-07-06 temizligi): Eski "GPS terminal vurus/ram" blogu (GPS_TERMINAL_STRIKE
    # + STRIKE_* sabitleri) SILINDI — gorev mimarisinde saldiri KAMERA verisiyle yapilir
    # (gorsel PNG fazi). Ihtiyac olursa git gecmisinde: adim() 10b blogu.
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

    # --- None YONETIMI (tik @50Hz) ---
    # SIM v0.0.5: hedef GPS NOMINAL 5 Hz (yarisma kosulu; eskiden 1 Hz'di) ve
    # KESINTI ZAMANLAMASI tanimlandi: 30. saniyeden sonra her 10 sn'de bir ~2 sn
    # veri gelmeyebilir (+ gecikme/gurultu bozulmalari surer, degerleri aciklanmaz).
    # 6 sn'lik tutma penceresi 2 sn'lik kesintileri bol marjla kapatir; filtre
    # kestirimi lead'li oldugundan tasimak guvenli. Loiter yalnizca GERCEK uzun
    # kesintide devreye girer.

    # ================= [ORTAK] =================
    # --- TESHIS (irtifa kacma sorununu cozmek icin gecici) ---
    # True: ~2Hz konsola [Z] satiri basar. drone_z vs hedef irtifasi (filtre & GERCEK),
    # ez, thr, hiz, pitch. Sorun cozulunce False yap.
    DEBUG_Z = False

    # --- UCUS LOGU (davranis teshisi) ---
    # True iken adim() HER kontrol-tikini (~50 Hz) zengin bir CSV'ye yazar
    # (ucus_log_<zaman>.csv). analiz_ucus.py bunu okuyup geri-cekilme / salinim /
    # gorsel-temas-kaybi teshisi yapar. Yarismada/uretimde False yap.
    LOG_ENABLE = True

    # ================= [GORSEL] (basit IBVS + kilit isteri sayaci) =================
    # --- GORSEL GUDUM — gorsel temas SONRASI yonelim (YALNIZCA kamera) ---
    # Gecis: conf>=VIS_CONF_MIN kareler ard arda VIS_N_LOCK olunca GORSEL_GUDUM'a gec.
    # Kayipta (OTO): VIS_LOST_TO_GPS_S kadar hover, sonra GPS'e don (0 = ANINDA don).
    # 2026-08-15: talon_v3'e gecildi (v2 SILINMEDI, models/talon_v2.pt duruyor).
    #   talon_v3 = talon_v2 uzerine INCE AYAR; 16332 kare (14023 train / 2309 val),
    #   yolo11s @960, 60 epoch, lr0 0.002, 10.60 saat, RTX 4060.
    #   AYNI val setinde durust kiyas:
    #                mAP50   mAP50-95   precision   recall
    #     v2 (eski)  0.9221    0.7697      0.9510   0.9055
    #     v3 (yeni)  0.9419    0.8070      0.9537   0.9230
    #   -> mAP50-95 +0.0373. Kutu OTURMASI belirgin duzeldi (mAP50-95 kutu
    #      hassasiyetini olcer; mAP50 sadece "buldu mu"ya bakar).
    #   Yaninda talon_v3.engine (TensorRT FP16) var -> gorsel_tespit otomatik secer.
    #   DIKKAT: config.py'deki VIS_MODEL_ADI AYRI bir ayardir (arayuz model
    #   listesi/hot-swap icin). Tespit dongusu BU yolu kullanir; ikisi de
    #   talon_v3'u gostermeli. Geri donmek icin: "talon_v2.pt" yaz.
    # ── 2026-08-23: talon_v4'e gecildi (v3 SILINMEDI, models/talon_v3.pt duruyor) ──
    #   talon_v4 = talon_v3 uzerine INCE AYAR. 19024 kare:
    #     16326 train / 2698 val,  40 epoch,  imgsz 960,  patience KAPALI
    #     + 1629 YENI kare 15-43 m (uzak agirlikli: %27'si 35-43 m)
    #     + 966 NEGATIF kare (hedefin sahnede HIC olmadigi) -> negatif orani
    #       %1.21'den %6.7'ye cikti; 51 "zor negatif" 3 kat tekrarlandi.
    #   AYNI dogrulama setinde v3'e karsi OLCULDU (v4_test_c.py):
    #     tespit           %93.0 -> %93.6   (hic bulamama %2.6 -> %2.1)
    #     35-50 m tespit   %75   -> %81     <- zayif tarafimiz, en buyuk kazanc
    #     25-30 m tespit   %85   -> %90
    #     YANLIS POZITIF   %4.7  -> %0.0    <- "yazilari algiliyor" sikayeti
    #     IoU ortanca      0.94  -> 0.94    (kutu kalitesi korundu)
    #   Yaninda talon_v4.engine (TensorRT FP16, imgsz 960) var -> otomatik secilir.
    #   Geri donmek icin: "talon_v3.pt" yaz.
    # ══ talon_v5 (2026-08-24) ══════════════════════════════════════════════
    # OLCULDU: v4 ile v5, AYNI karelerde (v4'un val'i, talonR; yeni cekimler
    # DISARIDA -- v5 onlarin %85'iyle egitildi, iceri alsak haksiz avantaj olur).
    #     bant        v4      v5
    #     15-20 m   100.0%  100.0%
    #     20-25 m    94.4%   97.2%
    #     25-30 m    89.7%   89.7%
    #     30-35 m    92.2%   94.1%
    #     35-43 m    80.9%   89.7%
    #     TUMU       90.6%   93.9%
    # ASIL KAZANC 35-43 m ZEMIN arka planinda: %65.6 -> %84.4 (+18.8).
    # GOK tarafi %94.4 -> %94.4: iyi calisan yari BOZULMADI (tasarim boyleydi).
    # ⚠ TEK BEDEL: 169 negatif karenin BIRINDE guven 0.272 (v4'te maks 0.099).
    #   Esigi 0.30'a cekmek onu eler AMA iki gercek tespiti de kaybettirir
    #   (biri 15-20 m -- terminal menzil). Esik 0.25'te BIRAKILDI cunku
    #   takipci zaten min_hits=3 istiyor: tek karelik yanlis pozitif
    #   ONAYLANMIS iz uretemez, dolayisiyla kilide donusemez.
    VIS_MODEL_PATH   = os.path.join(_PROJ_ROOT, "models", "talon_v5.pt")   # tespit modeli (task=detect, sinif: talon)
    # ⚠ talon_pose.pt (9 Tem) -> talon_pose_v2.engine (16 Agu 09:20).
    # v2 gece egitildi: mAP50-95 0.9212 (v1'in cok ustunde), 6 keypoint,
    # flip_idx [0,2,1,3,5,4]. TensorRT .engine secildi cunku POSE 2026-07-10'da
    # "tik basina ~200 ms GPU'yu bbox'tan caliyor" gerekcesiyle kapatilmisti --
    # o olcum PyTorch .pt ile yapilmisti, engine cok daha ucuz.
    # Geri donmek: AVCI_POSE_MODEL ile yol ver, ya da AVCI_POSE=0 ile kapat.
    VIS_POSE_MODEL_PATH = os.environ.get(
        "AVCI_POSE_MODEL",
        os.path.join(_PROJ_ROOT, "models", "talon_pose_v2.engine"))
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
    # 2026-08-14: 0.15 -> 0.35 (talon_v2 modeliyle birlikte).
    # NEDEN 0.15'ti: eski best.pt az tespit ediyordu (8 Tem: %22-33), esigi
    #   dusurmek tespit oranini %50-64'e cikariyordu. Yani dusuk esik zayif
    #   modelin bedeliydi -- ve zayif tespitlere ERKEN kilitlenip sonra
    #   kaybetme riskini getiriyordu (14 Agu bbox_ibvs logu: 17x6 px kutuyla
    #   IBVS'e girdi, 20 sn sonra KUTU_YOK, kayip sayaci tirmandi).
    # NEDEN ARTIK 0.35: talon_v2'nin GERCEK hedeflerdeki ortalama guveni
    #   olculdu -> 2-6m 0.858 | 6-12m 0.892 | 12-20m 0.868 | 20-30m 0.821
    #   | 30-45m 0.776.  Yani 0.35 hicbir gercek tespiti kesmez.
    #   Negatif karelerde uretilen en yuksek yanlis guven ise 0.219 idi ->
    #   0.35 esigi o gurultuyu TAMAMEN eler.
    # Geri almak icin: 0.15 yaz (yedek: ana_kontrol.py.yedek_*).
    # ⚠ 2026-08-17: sabit deger ENV'e acildi (AVCI_VIS_CONF). Sebep: guven
    #   esigi IKI ayri yerde kapiliyor -- burasi (kilit + komut) ve
    #   bbox_ibvs.CONF_MIN (AVCI_IBVS_CONF). Yalniz birini indirmek yetmiyor,
    #   yasa yine 0.35 altini atiyordu. Kampanya ikisini birlikte supurebilsin.
    #   Dedektorun KENDISI zaten 0.10'da kosuyor (server.py: min(UI, Cfg,
    #   takipci.CONF_DUSUK)) -- yani bu kapilar ByteTrack'i degil GUDUMU kisiyor.
    # ── TESPIT GUVEN ESIGI: 0.35 -> 0.25 (2026-08-19, OLCUMDEN) ──────────
    # SORUN: gorsel faz her devirde "kayip" ile kopuyordu (170 s'de 9 devir,
    #   9'u da kayip). Sebep dedektor bosluklari: hedef KADRAJ ICINDEYKEN
    #   (|kerteriz| < FOV/2) tespit orani menzille cokuyor.
    # OLCULDU (canli /api/tune ile DONUSUMLU, 4 tur x 60 s, binlerce kare):
    #        menzil     conf 0.35   conf 0.25
    #        <10 m          89%        93%
    #        10-20 m        53%        78%    <- DEVIR BANDI
    #        20-40 m        30%        40%
    #        40+  m          3%         7%
    # OLUMSUZ KONTROL (hedef kadraj DISINDA -> her tespit yanlis pozitif):
    #        >75 deg       3.0%       2.1%
    #        >100 deg      2.4%       1.9%
    #   -> esigi dusurmek yanlis pozitifi ARTIRMIYOR.
    # SONUC (dönüşümlü, 4 tur x 85 s):
    #        kesintisiz kilit ort   0.29 s -> 0.55 s   (p90 1.45 -> 1.99)
    #        30 m ici gecirilen ornek  202 -> 525      (medyan 20.4 -> 16.9 m)
    #   Dort turun DORDUNDE de ayni yonde.
    # ⚠ 0.25'in ALTINA inmek ise ETKISIZ: server.py predict esigi zaten
    #   min(0.25, VIS_CONF_MIN) -- ham cikarim 0.25'in altini uretmiyor.
    VIS_CONF_MIN     = float(os.environ.get("AVCI_VIS_CONF", "0.25") or 0.25)
                                # kilit/komut icin asgari guven. Cok yanlis tespit
                                # gorursen slider'dan oynayabilirsin.
    # --- SAHI (Slicing Aided Hyper Inference) — uzak/kucuk hedef recall (2026-07-09) ---
    # Kareyi ortusen dilimlere bol, HER dilimde best.pt kosur, kutulari tam-kare
    # koordina tasi + NMS ile birlestir. Uzak hedef dilim icinde buyuk oran kaplar
    # -> dedektor korlugu (15-40 m) azalir. SADECE best.pt (detect); pose modeline
    # UYGULANMAZ (keypoint dilim-merge yok). Bizim temiz impl (gorsel_tespit._sahi_ham),
    # sahi paketi GEREKMEZ; kural 8 aciklanabilir. MALIYET: N dilim -> N x inference;
    # GPU oyunla paylasimli -> SAHI_KOSUL_CONF ile yakin hedefte dilimleme atlanir.
    # 2026-08-14: True -> False (talon_v2 ile birlikte).
    # SAHI eski best.pt'nin UZAK HEDEF KORLUGUNU kapatmak icin vardi: o model
    # dilimleme olmadan 40-120 m'de %0 goruyordu, SAHI ile %71'e cikiyordu.
    # BEDELI: kare basina ~9 inference (1 tam-kare + 8 dilim).
    #   olculdu (kod yorumu, oyun+sunucu kosarken): tam-kare 13.1 ms -> SAHI 33.9 ms
    # talon_v2 ise SAHI'SIZ, TEK GECISTE su recall'u veriyor (1257 val karesi,
    # 291'i mesafe etiketli, model bu kareleri egitimde gormedi):
    #     2-6 m %100 | 6-12 m %98.3 | 12-20 m %96.7 | 20-30 m %98.3 | 30-45 m %98.0
    # Yani kullanicinin ihtiyaci olan 30-40 m araliginda dilimlemeye GEREK YOK.
    # 100 m+ hedefler bu modelin (ve veri setinin) kapsami disinda -- kullanici
    # o mesafeyi istemedigini acikca belirtti.
    # Geri acmak icin: True yaz (ya da AVCI_SAHI=1 ortam degiskeni).
    SAHI_AKTIF       = False    # False -> tek tam-kare predict (eski davranis, bit-ayni)
    SAHI_DILIM_PX    = 640      # dilim kenari (px); best.pt imgsz'ine yakin
    SAHI_ORTUSME     = 0.2      # komsu dilim ortusme orani (kenardaki hedef bolunmesin)
    SAHI_TAM_KARE    = True     # dilimlere EK tam-kare predict (yakin/buyuk hedef kesilmesin)
    SAHI_NMS_IOU     = 0.5      # dilim+tam-kare kutu birlestirme IoU esigi
    SAHI_KOSUL_CONF  = 0.5      # tam-karede conf>=bu kutu VARSA dilimleme ATLA (perf).
                                # 0 = HER kare dilimlenir (en yuksek recall, en yavas)
    VIS_STALE_S      = 0.5      # tespit bu sureden eskiyse yok say (kayip mantigi devreye girer)
                               # 0 = ANINDA GPS'e don (hover fazi yok; kullanici istegi
                               # 2026-07-08 — ara bekleme kafa karistiriyordu). Dedektor
                               # titremesi (tek-kare atlama) zaten VIS_STALE_S ile koprulenir;
                               # son gorusten itibaren toplam ~(VIS_STALE_S + bu) sn'de doner.
                               # Manuel GORSEL switch'te donus YOK (revert_izin=False), hep hover.
    # --- TAKIP (ByteTrack) ANAHTARLARI (2026-07-09, canli regresyon sonrasi) ---
    # TAKIP_AKTIF=False -> tracker DEVRE DISI: ham argmax tespit dogrudan beyne
    # (ByteTrack oncesi davranisla bire bir) -> canli sorun cikarsa hizli geri-donus.
    # 2026-08-14: True -> False.  NEDEN (olculdu, tahmin degil):
    #   Kullanici ekran goruntusu 17:36:20 -> hedef Talon kadrajda AÇIKÇA gorunuyor,
    #   uygulama HIC kutu cizmiyor, ekranda "TAKIP: PASIF / YENIDEN ARANIYOR" yaziyor.
    #   AYNI kareyi talon_v2'ye verdim: conf 0.940, kutu 394x304 -> model hedefi
    #   sorunsuz goruyor.  Demek ki kayip DEDEKTORDE degil, ARADAKI TAKIPCIDE.
    #   HybridSort ayarlari: min_hits=3 (yeni iz 3 ardisik kare ister),
    #   iou_threshold=0.3 (ardisik kutular %30 ORTUSMELI).  Hedef 20 m/s goreli
    #   hizla yanimizdan gecerken kutu kareler arasi cok yer degistiriyor ->
    #   %30 ortusme saglanamiyor -> iz ASLA onaylanmiyor -> gudum
    #   `det = en iyi CONFIRMED track` oldugu icin BOS aliyor.
    #   Ayrica ekranda cizilen kutu ham tespit degil takipcinin Kalman tahmini ->
    #   hizli harekette geride kaliyor ("kutu tam oturmuyor" sikayeti).
    # False = ham argmax dogrudan beyne (ByteTrack oncesi davranisla bire bir).
    # BEDELI: tek-kare yanlis pozitifi suzen katman gider. talon_v2 ile risk dusuk:
    #   24 negatif karede uretilen en yuksek yanlis guven 0.219, esigimiz 0.35.
    # GERI ALMAK: True yaz (yedek: ana_kontrol.py.yedek_takip_*).
    TAKIP_AKTIF      = False
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
    # --- BASIT IBVS (2026-07-07): goruntu merkezi -> bbox merkezi cizgisi ---
    # TEK gorsel yasa (guidance/ibvs_gorsel.py): cizginin YATAY bileseni yaw'a,
    # DIKEY bileseni throttle'a gider; BUYUKLUGU (merkeze sapma "mesafesi") ileri
    # itkiyi kisar (once ortala, sonra ilerle). Roll HEP 0 (bank yok — eski PN'de
    # bank hedefi kadrajdan atip kamerayi yere ceviriyordu). Kamera +25 tilt'li
    # oldugundan hedefi MERKEZDE tutmak araci hedefin ALTINDA tutar (gokyuzu
    # arka plan / alttan yaklasma) — ekstra dikey geometri kodu GEREKMEZ.
                                # 8 Tem ucus (222830): kullanici 2.25 kullandi; 2.0'a cektim
                                # (2.25 salinim/asiri tepki riski). Dikey hata buyukse thr zaten
                                # doygun (clamp) — K'yi asiri buyutmek merkezlemeyi iyilestirmez.
                                # SIM'de dikey TERS tepki gorursen -1 yap (tek isaret, tek yer).
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
                                # 0.09->0.12 (8 Tem ucus 222830: 8-9 m'de bile bbox ~%6.6,
                                # kilit esigi %6'da salinip dolmuyordu; hedefi 0.12 yapmak
                                # dengeyi ~%8.5'e cikarir -> istek uzun doygun kalir, drone
                                # yapabildigi EN YAKINA gider, boyut esigi guvenli gecer).
                                # 15->20 (denge boyutunu HEDEF'e yaklastirir: boyut_eq =
                                # HEDEF - ileri_eq/K; K buyuk -> daha kararli ve yuksek boyut).
                                # 0 = hep tam gaz; buyuk deger = once ortala sonra ilerle ⚙
                                # 1.0->1.4 (8 Tem ucus_2: fren artisi sonrasi episodlar oturakli).
    # --- DIKEY NISAN (tilt-farkinda; hiz vektorunu hedefe kilitle) ---
    # Kamera +TILT derece YUKARI sabit. Hedefi kadraj MERKEZINDE tutmak = hiz vektorunu
    # hedefin ~TILT altina nisanlamak (kronik dikey undershoot). Hedefi hiz vektorunun
    # goruntudeki yerine (FOE) tutarsak "hedefte" = "burun hedefe kilitli" -> dogrudan
    # carpisma rotasi. ey_ref = NISAN * tan(TILT) / tan(VFOV_yari) (tilt'ten TURETILIR).
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
    # --- ALCALMA FRENI (gorsel anti-lift-carry, 2026-07-08) ---
    # GPS yolundaki alc_oncelik'in gorsel-faz aynasi: hedef nisan noktasinin ALTINDAysa
    # (eyy>0 = arac cok yuksekte) ileri itki carpimsal kisilir ->
    #   pitch *= clamp(1 - ALCAL_FREN*max(0,eyy), ALCAL_TABAN, 1)
    # Ileri-ucus tasimasi (lift carry) dusunce negatif thr gercekten alcaltir (THR_DN
    # yorumundaki ders: tam ileri ucusta -0.40 bile tirmanmayi durduramiyordu).
    # Tirmanis tarafi (eyy<0) etkilenmez. Girdi yalniz goruntu buyuklugu -> kural uygun.
                                # kullanici 2.0->1.5 kullandi — ileri itki daha az frenlensin,
                                # yaklasma acilsin; yak-agirlikli fren zaten uzakta baypas ediyor).
                                # GPS alc_oncelik 0.15 tabaninin gorsel karsiligi; slider DISI.
    # --- EGO-PITCH TELAFISI (2026-07-08; kacak-tirmanma kok nedeni) ---
    # Ileri itki govdeyi one yatirinca kamera (govdeye sabit) asagi doner -> hedef goruntude
    # YUKARI ziplar -> yasa "hedef kacti, TIRMAN" okuyordu (log 204331: corr(pitch,ey)=0.70;
    # drone hedefin 10 m ALTINDAYKEN +0.70 tirmanis). Dikey hata kendi pitch'ten arindirilir:
    #   ey_dunya = ey_f - GAIN*tan(own_pitch)/tan(VFOV_yari)   (ibvs_gorsel.hesapla)
    # Kendi IMU'muz = ego-motion (ego-roll telafisiyle ayni emsal) -> kural ihlali DEGIL.
                                # yatikligini (-37 deg, ileri itki artinca) "sahte yukari"
                                # sanip ASIRI telafi ediyordu -> ey isareti donuyordu (ham
                                # -0.36 -> telafili +0.37) -> yasa surekli sert ALCAL veriyordu
                                # (thr -0.63, %93) -> drone hedefin altina inip hedefi kadraj
                                # USTUNDEN kaciriyordu (dikey merkezleme cokuyordu). Veriden
                                # taranan optimal: 0.4 -> eyy~0 (hedef nisanda) + |ey| dikey
                                # kadraj-ici en iyi (p90 0.77->0.59). 0=tam kapali.
    # --- ONGORULU YAW LEAD (pose kanat uclarindan hedef ROLL/bank) ---
    # Hedefi ARKADAN takip ederken iki kanat ucu pikselinden (kp[1]=sol, kp[2]=sag)
    # goruntu-uzayi bank acisi: roll_img=atan2(dy,dx). Bankli ucak alcak kanadi yonune
    # doner -> hedefin GIDECEGI yon oncelenir, yaw'a ILERI-BESLEME eklenir:
    # yaw = K_YAW*ex + SIGN_ROLL*K_ROLL_LEAD*roll_img. Sadece YAW; thr/pitch/roll degismez.
    # Pose GORSEL veri (kameradan keypoint) -> yarisma kuralina uygun (GPS/J degil).
                                # 8 Tem: kilit-tut fazinda KAPALI (kullanici tercihi) — hedef
                                # cogunlukla duz kaciyor, oncelu donus geregi az.
                                # ⚠ 9 Tem canli (ucus 175052): slider'dan 0.6'ya cekilince "yaw
                                # yanlis tarafa doniyor" hissi -> ANA yaw (ex-tabanli) DOGRU
                                # (truth bearing %100 uyum, |ex| 0.125->0.072 yakinsiyor); suclu
                                # LEAD: hedefin gercek donusunu yalniz %38 dogru ongordu (n=8) ve
                                # 0.373'e sicrayip ex-terimini (~0.08) bastirdi. KAPALI KALSIN.
                                # Acmadan once araclar/pose_ongoru_analiz.py ile YENI modelde
                                # isaret+dogruluk dogrulanmali (n buyuk); duz-kacan hedefte fayda az.
                                # araclar/pose_ongoru_analiz.py corr=-0.86 @0.2sn, %86 uyum -> SIGN=-1.
                                # (roll_img>0 iken hedef goruntude SOLA gidiyor; +1 TERS'ti.) Yeni pose
                                # modeli/kamera degisince analizi tekrar kos, ONERI'yi uygula.
    # EGO-MOTION TELAFISI: kamera govdeye sabit -> biz yatinca (kendi roll) kanat cizgisi de
    # doner ve "hedef bank"i kirletir. Kendi roll'umuzu (IMU) goruntu-roll'unden cikaririz:
    # roll_comp = roll_img - GAIN*own_roll. GAIN=0 kapali; isaret canlida araclar/
    # pose_ongoru_analiz ego A-B'siyle dogrulanir (+1 varsayildi, veriyle teyit et).
    # NOT: own_roll KENDI IMU'muz (ego-motion), hedef konumu DEGIL -> yarisma kurali ihlali degil.
                                # yandan/onden gorunumde kanat cizgisi bank'i temsil etmez -> lead=0

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
        # kendi YATAY hiz vektoru (temiz konum sonlu-fark, EMA) - terminal vurus icin
        self._own_pxy = None            # onceki kendi yatay konum (cm)
        self._own_tv = None             # onceki olcum zamani
        self._own_v = np.zeros(2)       # kendi yatay hiz (cm/s, dunya)
        # kendi DIKEY hiz (drone_z sonlu-fark, EMA) - dikey overshoot sonumleme (anti-firlama)
        # GERCEK modda hedef hizi (truth konum sonlu-fark) - carpisma-rotasi icin
        self._gt_prev_p = None          # onceki truth hedef konum (cm)
        self._gt_prev_t = None
        self._gt_vel = np.zeros(3)      # hedef hizi (cm/s, 3B)
        self.none_count = 0
        self.last_est = None
        self.handoff = False
        self.handoff_announced = False

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
        self.vis_mode = "OTO"           # guduum pipeline switch (test): OTO | GPS | GORSEL
        # --- KILITLENME ISTERI SAYACI (sartname 6.1.2/6.1.4; SALT GOZLEM, komuta girmez) ---

        # --- GPS HATTI (yasa + kopru) — lazy kurulur, ilk GPS tikinde baslar ---
        self.kopru_gudum = None
        # ZEMIN DATUMU: bir kez olculur, gorev/kaynak degisimlerinde KORUNUR.
        # Kopru yeniden kurulunca havadaki irtifadan yeniden olculuyordu ->
        # NED dusey cercevesi kayiyor, arac hedefin ustune cikip kadraji
        # kaybediyordu (11 Agu canli kanit: 48.4 -> 83.0 -> 92.3 m).
        self.kopru_zemin_m = None       # m; ilk YERDE kurulumda doldurulur
        # KILITLENME ISTERI SAYACI (sartname 6.1.2/6.1.4) — guduumden BAGIMSIZ
        # gozlemci. Eskiden eski gorsel yasanin icindeydi ve hibritte OLU
        # kalmisti (ANGAJMAN/VURUS mandallari hic tetiklenmiyordu).
        self.kilit = KilitSayaci()
        # ── DEVIR SAYACI (2026-08-14) ─────────────────────────────────────
        # self.kilit SARTNAME sayacidir ve KASITEN yalniz GORSEL fazda sayar
        # (kilit_sayaci.guncelle: "GPS fazinda gecen zaman kilit sayilmaz").
        # Ama supervisor'in GPS->GORSEL devir olcutu de kilit suresi olunca
        # DONGUSEL BAGIMLILIK olusuyordu:
        #     kilit dolsun -> gorsel faza gec ;  gorsel faza gec -> kilit dolsun
        # Kanit (14 Agu karar logu): 2060 karede tespit vardi (conf 0.85,
        # mesafe 13-26 m) ama kilit_s hep 0.00, boyut_pct hep bos.
        # COZUM: AYNI kurallari isleten ama faz kapisi OLMAYAN ikinci sayac.
        # Sartname sayaci (self.kilit) DEGISMEDI -- kanit zinciri bozulmaz.
        self.kilit_devir = KilitSayaci(cfg=DevirCfg)
        self.kopru_durum = {}           # yasanin durumu (arayuz/telemetri; salt okuma)

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
        self._own_pxy = None            # kendi yatay hiz kestirimini taze baslat
        self._own_tv = None
        self._own_v = np.zeros(2)
        self.none_count = 0
        self.last_est = None
        self.handoff = False
        self.handoff_announced = False
        self.durum = "ARAMA"
        # GORSEL GUDUM: yeni gorev -> gorsel kilit/kopru durumunu da taze basla
        self.son_tespit = None
        self.son_tespit_t = None
        self.son_poz = None
        self.son_poz_t = None
        # kilitlenme isteri sayaci: yeni gorev -> pencere ve latch dahil taze basla
        self.kilit.sifirla()          # sartname kilit sayaci (gozlemci) taze basla
        # YENI GPS HATTI: yeni gorev -> yasa thread'ini TAZE basla (yeni gps_guidance
        # CSV'si, temiz filtre/istasyon durumu). Sonraki GPS tikinde yeniden kurulur.
        if self.kopru_gudum is not None:
            try: self.kopru_gudum.durdur()
            except Exception: pass
            self.kopru_gudum = None
            self.kopru_durum = {}
        # ucus logu: yeni gorev -> yeni dosya (sonraki tik taze zaman-damgali acar).
        # NOT: ayni kaynak ust uste secilirse bu metod erken doner (yukarida) -> dosya
        # donmez; server "Gorev Baslat"ta log_dondur()'u AYRICA kosulsuz cagirir
        # (her gorev = ayri ucus_log dosyasi = veri/tune_parametreler/ucus_N klasoru).
        self.log_dondur()

    def log_dondur(self):
        if self._log_f is not None:
            try: self._log_f.close()
            except Exception: pass
            self._log_f = self._log_w = None

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

    def _send(self, thr, pitch, roll, yaw):
        thr   = rate_limit(thr,   self.prev['thr'],   Cfg.MAX_DELTA)
        pitch = rate_limit(pitch, self.prev['pitch'], Cfg.MAX_DELTA)
        roll  = rate_limit(roll,  self.prev['roll'],  Cfg.MAX_DELTA)
        yaw   = rate_limit(yaw,   self.prev['yaw'],   Cfg.MAX_DELTA)
        self.prev = {'thr': thr, 'pitch': pitch, 'roll': roll, 'yaw': yaw}
        self.drone.set_control_surfaces(thr, pitch, roll, yaw, True)

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

    def set_vis_mode(self, mode):
        """Arayuz GPS/GORSEL/OTO switch'i — HIBRITTE ETKISIZ.

        (2026-08-11) Faz kararini artik SUPERVISOR veriyor (10/15 kare kilit ->
        gorsel; 20 kayip kare -> GPS). Eski FSM silindi. Deger yalnizca
        arayuzde gosterilmek uzere saklanir; guduume GIRMEZ.
        """
        m = (mode or "OTO").upper()
        if m not in ("OTO", "GPS", "GORSEL"):
            return False
        self.vis_mode = m
        return True

    def set_gorsel_tespit(self, det):
        """Dedektor thread'i cagirir. YALNIZ son tespiti saklar.

        (2026-08-11) Goruntu-hizi/olu-hesap kestirimi SILINDI: tek tuketicisi
        eski gorsel yasanin koprusuydu, o da kalkti. Kayip/koprulme karari
        artik yasanin: supervisor KAYIP_M=20 kare.
        """
        if det is not None:
            t_det = det.get("t", time.perf_counter())
            self.son_tespit = det
            self.son_tespit_t = t_det
        # det None ise ESKI tespiti SILME: tek bos kare kilidi dusurmesin. Bayatlik
        # (VIS_STALE_S) _oku'da elenir; kayip histerezisini _vis_lost_count yonetir.

    def set_gorsel_poz(self, poz):
        """Pose dedektor NORMALIZE ciktisini (kp/conf/aspect_deg...) beyne yaz — GORSEL
        veri (kameradan keypoint), ONGORULU yaw lead'i besler. server.dedektor_dongusu
        beyin_lock altinda TAZE pose kostugunda cagirir. det deseni: None ise eskisini
        SILME (poz artik guduume girmiyor; yalniz arayuz gozlemi)."""
        if poz is not None:
            self.son_poz = poz
            self.son_poz_t = time.perf_counter()

    def _gorsel_tespit_oku(self):
        """Bayat-olmayan son tespiti dondur, yoksa None.

        (2026-08-11) GORUNTU-DUZLEMI KOPRUSU (olu-hesap) SILINDI: eski gorsel
        yasaya aitti. Dedektor deliklerini artik YASA yonetiyor — supervisor
        20 kayip kare sonra GPS'e doner; bbox_ibvs kendi ic durumunu tutar.
        Cift olu-hesap istemiyoruz.
        """
        det = self.son_tespit
        if det is None or self.son_tespit_t is None:
            return None
        if (time.perf_counter() - self.son_tespit_t) <= Cfg.VIS_STALE_S:
            return det
        return None

    def _kopru_tik(self, t, drone_pos, yaw_m, drone_yaw, v_own):
        if self.kopru_gudum is None:
            try:
                from kopru.entegre import KopruGudum
            except Exception as e:
                if not getattr(self, "_kopru_hata_ilan", False):
                    self._kopru_hata_ilan = True
                    print("[KOPRU] entegre modul YUKLENEMEDI -> ucus YOK:", repr(e))
                self._send(0.0, 0.0, 0.0, 0.0)
                return False
            self.kopru_gudum = KopruGudum(
                self.drone, range_set=Cfg.KOPRU_RANGE_SET, v_max=Cfg.KOPRU_V_MAX,
                ic_kayma=Cfg.KOPRU_IC_KAYMA, gnss_duzeltici=Cfg.KOPRU_GNSS_FILTRE,
                kalkis_agl=Cfg.KOPRU_KALKIS_AGL,
                istasyon_elev=Cfg.KOPRU_ISTASYON_ELEV,
                hibrit=bool(getattr(Cfg, "KOPRU_HIBRIT", False)),
                birebir=bool(getattr(Cfg, "KOPRU_BIREBIR", True)),
                vmax_istisna=getattr(Cfg, "KOPRU_VMAX_ISTISNA", None),
                zemin_m=self.kopru_zemin_m,        # None ise kopru YERDE olcer
                kayip_m=int(getattr(Cfg, "KOPRU_KAYIP_M", 0) or 0),
                # HEDEF KAYNAGI arayuzun kaynak secicisine BAGLI:
                #   "Gercek GPS (test)" butonu -> truth (bozuk kanal okunmaz)
                #   "v2" (Inovasyonlu J)       -> bozuk kanal + CT-EKF
                # set_kaynak() kopruyu yikip yeniden kurdugundan canli gecis calisir.
                hedef_truth=(self.kaynak == "gercek"))
            # Olculen datumu SAKLA: sonraki kurulumlarda yeniden olculmesin.
            if self.kopru_zemin_m is None:
                self.kopru_zemin_m = getattr(self.kopru_gudum, "_zemin", None)
            if not self.kopru_gudum.baslat():
                if not getattr(self, "_kopru_hata_ilan", False):
                    self._kopru_hata_ilan = True
                    print("[KOPRU] kurulum BASARISIZ -> ucus YOK")
                self._send(0.0, 0.0, 0.0, 0.0)
                return False
        tani = self.kopru_gudum.adim()
        if tani is None:
            return False
        # Arayuz/telemetri: yasanin durumunu ve uygulanan komutu yansit.
        self.kopru_durum = self.kopru_gudum.durum()
        d = self.kopru_durum.get("durum")
        if d in ("ARAMA", "KILIT", "KALKIS", "DROPOUT", "WARMUP"):
            self.durum = d
            self.handoff = (d == "KILIT")
        k = self.kopru_gudum.komut
        if k:
            self.prev = dict(k)                  # "uygulanan komut" karti dogru kalsin
        self._log_early("KOPRU", t, drone_pos, yaw_m, drone_yaw, v_own)
        return True

    def _debug_olc(self):
        dbg = self.drone.get_debug_truth()
        if not dbg.get("available") or self.son_temiz is None: return
        gercek = np.array(dbg["target"]["position"])
        ham = np.array(self.son_ham)
        self.ham_hatalar.append(np.linalg.norm(ham - gercek))
        self.j_hatalar.append(np.linalg.norm(self.son_temiz - gercek))
        for ad in self.drone.get_active_corruption():
            self.bozukluk_sayac[ad] = self.bozukluk_sayac.get(ad, 0) + 1

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

        # 2) KALKIS: artik KOPRU hattinda (AGL kapili, kopru/entegre.py).
        #    Eski dunya-Z kapisi (SEARCH_ALT) 2026-08-07'de silindi — DoW spawn
        #    zemini 48.4 m oldugundan fiilen hic calismiyordu.

        # 2.5) GUDUM PIPELINE SECIMI (switch: self.vis_mode) + GORSEL kesme.
        #      OTO   : conf>=VIS_CONF_MIN kareler ard arda VIS_N_LOCK olunca GORSEL'e kilitlenir;
        #              kayip VIS_LOST_TO_GPS_S'i asarsa GPS'e geri doner (re-acquire).
        #      GPS   : gorsel yol KAPALI (gorseldeysen GPS'e doner) -> hep GPS.
        #      GORSEL: kilidi ATLA, hemen GORSEL; kayipta GPS'e DONME (zorlanmis).
        #      GORSEL kilitliyken asagidaki TUM GPS yonelimi ATLANIR (return) -> gorsel
        #      temas VARKEN GPS yonelimi kullanilmaz. _send prev surekliligi -> sarsintisiz.
        tespit = self._gorsel_tespit_oku()
        # ⛔ HIBRITTE ESKI GORSEL YASA DEVRE DISI (2026-08-10, canli yakalandi)
        # Kayran'in supervisor'i faz kararini KENDI veriyor (10/15 kare kilit ->
        # bbox_ibvs; 20 kayip kare -> GPS). Bizim eski IBVS'imiz de ayni anda
        # kosarsa IKI kumandan olur: asagidaki blok bir sonuc dondurdugunde
        # _send edip RETURN ediyor -> _kopru_tik HIC calismiyor, yani supervisor
        # ve kopru komple baypas ediliyordu (ilk hibrit ucusunda telemetride
        # goruldu: durum=GORSEL_GUDUM iken supervisor faz=GPS'te asili kaldi;
        # tespit yokken bizim yasa hover donduruyor ve yasanin tikini yiyordu).
        # Hibritte tek karar mercii supervisor -> bu blok atlanir, akis dogrudan
        # _kopru_tik'e gider. KOPRU_HIBRIT=False'ta davranis BIT-AYNI kalir.
        _hibrit_aktif = bool(getattr(Cfg, "KOPRU_HIBRIT", False))
        if _hibrit_aktif:
            # KILIT SAYACI: supervisor GORSEL fazdayken taze tespitle beslenir.
            # Guduume GIRMEZ; yalnizca sartname kanit zincirini (ANGAJMAN cipi,
            # VURUS/BASARI mandallari, olay gunlugu) uretir.
            _faz = "GPS"
            if self.kopru_gudum is not None:
                try:
                    _faz = (self.kopru_gudum.faz() or {}).get("faz") or "GPS"
                except Exception:
                    _faz = "GPS"
            self.kilit.guncelle(tespit, t, gorsel_faz=(_faz == "VISUAL"))
            # Devir sayaci: FAZ FARK ETMEKSIZIN sayar (bkz. __init__ aciklamasi).
            # Supervisor'in GPS->GORSEL devir olcutu budur.
            self.kilit_devir.guncelle(tespit, t, gorsel_faz=True)
            if self.durum == "GORSEL_GUDUM":
                self.durum = "KILIT"      # gorunum: faz bilgisi supervisor'dan gelir

        # ⛔ ESKI GORSEL YASA SILINDI (2026-08-11, kullanici karari).
        # Gorsel guduum artik TAMAMEN Kayran'in yasasinda: supervisor faz
        # kararini verir, bbox_ibvs komutu uretir, kopru DoW stick'ine cevirir.
        # Tek guduum hatti = _kopru_tik. Eski AvciIBVS/_gorsel_guduum yolu ve
        # kilit FSM'i kaldirildi; sartname kilit sayaci guidance/kilit_sayaci.py
        # icinde BAGIMSIZ gozlemci olarak yasiyor.

        # ==================== [GPS FAZI: yasa + kopru] ====================
        # GPS yaklasmasi Gazebo'dan tasinan yasayla yapilir
        # (control/guidance/gps_guidance.py — DEGISMEZ), hiz komutu koprude
        # (kopru/dow_kopru.py) DoW stick'ine cevrilir. Kopru ArduCopter'in
        # yerini alir; denetim: docs/kopru_denetim.md. KALKIS da bu hatta
        # (AGL kapili, kopru/entegre.py). Eski PD/standoff yasasi 2026-08-07'de
        # SILINDI (kullanici karari) — git gecmisinde: eca3b4a.
        self._kopru_tik(t, drone_pos, yaw_m, drone_yaw, v_own)

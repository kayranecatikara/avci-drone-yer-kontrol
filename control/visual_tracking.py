# -*- coding: utf-8 -*-
"""
control/visual_tracking.py — GÖRSEL FAZ: IBVS (görüntü tabanlı güdüm)

AMAÇ: Kontrol hatasını 3B dünyada değil doğrudan GÖRÜNTÜ UZAYINDA (piksel)
tanımlamak. Hedefin konumu/hızı hiç kestirilmez; kutunun kadrajdaki YERİ ve
BOYUTU doğrudan hata sinyalidir.

    menzil (R)   = RANGE_C_REF / kutu_boyutu            (px·m / px = m)
    kerteriz     = piksel + KENDİ IMU'muz (ego-motion telafisi)
    yaw          = burnu kerterize çevir
    ileri hız    = kapanma hızı denetimi:
                   v_yer = v_hedef_LOS + K_CLOSE*(R - TRAIL_RANGE_M)
                   profil `TRAIL_RANGE_M`de sıfırlanır -> araç kuyruğa OTURUR ve KALIR
    dikey hız    = hedefi kadrajda sabit yükseklikte tut (cy -> CY_REF)

⛔ KATI KURAL — BU DOSYADA GPS/GNSS YOKTUR (diskalifiye sebebi). Kural
   YAPISAL olarak sağlanır: `VisualTracker.compute(det, own_att_deg,
   own_vel_ms, dt)` imzasında hedefe ait tek veri BBOX PİKSELLERİDİR.
   `own_*` değerleri KENDİ IMU/hızımızdır (ego-motion telafisi), hedef
   verisi değildir. Konum/hız/GNSS kestirimi parametre olarak bile geçmez.

⚠ Kamera modeli sabitleri (`TILT_DEG`, `F_PX_REF`, `RANGE_C_REF`) OYUNUN
  sanal kamerasına aittir. Gerçek kameraya geçilirse üçü de geçersizdir ve
  yeniden kalibrasyon şarttır.
"""
import math
import time

from control.common import ConverterCfg, VelocityToStick, clamp, wrap_deg


# ==========================================================
#  KAMERA MODELİ — KALİBRE EDİLDİ (referans çözünürlük 1920x1080)
# ==========================================================
# Model çözünürlükten BAĞIMSIZDIR: bütün piksel sabitleri `_scale(W)` ile
# ölçeklenir, yani 1280x720 kaynakla da aynı açıları/menzilleri üretir.
REF_W, REF_H = 1920.0, 1080.0  # px; sabitlerin ölçüldüğü referans kare boyutu
TILT_DEG = 26.50     # derece; kamera ekseninin burna göre YUKARI bakma açısı.
                     # Kalibre edildi (artık 2.6 px, n=614; bootstrap 26.57° ± 0.11°).
                     # ⛔ SDK başlığının yazdığı 25° kesin olarak elenir.
F_PX_REF = 540.4     # px @1920 genişlik; odak uzunluğu (fx = fy varsayılır).
                     # Açı <-> piksel dönüşümünün tek katsayısıdır.
RANGE_C_REF = 997.0  # px·m @1920; menzil sabiti:  R = RANGE_C_REF / kutu_boyutu.
                     # Fiziksel anlamı "1 m mesafede hedef kaç piksel görünür"dür,
                     # yani hedefin gerçek boyutu ile odak uzunluğunun çarpımı.
                     # ⚠ Modelin KUTULAMA SIKILIĞINA bağlıdır: dedektör değişirse
                     #   yeniden ölçülmelidir, yoksa 3-50 m kapıları yanlış yerde
                     #   açılıp kapanır.

def _scale(W):
    """Yakalanan kare genişliğinin kalibrasyon referansına oranı (birimsiz).

    W = 1920 -> 1.0,  W = 1280 -> 0.667. Piksel cinsinden her sabit bununla
    çarpılır; model böylece çözünürlükten bağımsız kalır.
    """
    return float(W) / REF_W

def f_px(W):
    """Bu kare genişliği için odak uzunluğu (px)."""
    return F_PX_REF * _scale(W)

def range_m(box_px, W):
    """Kutu boyutundan menzil kestirir.

    box_px : px; kutunun BÜYÜK kenarı (max(w, h))
    W      : px; kare genişliği (ölçekleme için)
    -> menzil (m) | None (boyut geçersiz)

    ⚠ Bu bir TERSLEMEDİR: `size`daki simetrik gürültü `R`de çarpık ve ağır
      kuyruklu olur. Bu yüzden yumuşatma `R`ye değil `size`a uygulanır
      (bkz. `VisualTracker.compute`).
    """
    if box_px <= 0:
        return None
    return (RANGE_C_REF * _scale(W)) / float(box_px)


def pixel_angle(cx_px, cy_px, W, H):
    """Kadraj konumundan KAMERA EKSENİNE göre açı.

    cx_px, cy_px : px; kutu merkezi
    W, H         : px; kare ölçüleri
    -> (yatay, dikey) derece; dikeyde YUKARI pozitiftir
    """
    f = f_px(W)
    return (math.degrees(math.atan((cx_px - W / 2.0) / f)),
            math.degrees(math.atan((H / 2.0 - cy_px) / f)))


def pixel_bearing(cx_px, cy_px, own_pitch_deg, own_roll_deg, W, H):
    """Kadraj konumundan GÖVDEDEN BAĞIMSIZ kerteriz üretir (ego-motion telafisi).

    cx_px, cy_px  : px; kutu merkezi
    own_pitch_deg : derece; KENDİ pitch'imiz
    own_roll_deg  : derece; KENDİ roll'ümüz
    W, H          : px; kare ölçüleri
    -> (azimut, yükseliş) derece — burnumuza göre, ama yatışımızdan arındırılmış

    Sıra önemlidir: önce kaydırma (kamera tilt + kendi pitch'imiz), sonra
    roll ile döndürme. Girdi yalnız piksel ve KENDİ IMU'muzdur; hedefe ait
    hiçbir konum/hız verisi kullanılmaz.
    """
    horiz, vert = pixel_angle(cx_px, cy_px, W, H)
    elevation = vert + TILT_DEG + own_pitch_deg
    if own_roll_deg:
        r = math.radians(own_roll_deg)
        c, s = math.cos(r), math.sin(r)
        horiz, elevation = horiz * c - elevation * s, horiz * s + elevation * c
    return horiz, elevation


def bearing_pixel(azimuth_deg, elevation_deg, own_pitch_deg, own_roll_deg, W, H):
    """`pixel_bearing`in TAM TERSİ: kerterizden kadraj konumu üretir.

    -> (cx, cy) px

    KUTU KÖPRÜSÜNÜN çekirdeğidir: tespit gelmediğinde son kutunun ATALET
    yönü saklanır ve o yön, ARADA DÖNMÜŞ olan kendi gövdemize göre yeniden
    kadraja yansıtılır. Böylece bayat kutu, kendi hareketimiz telafi edilerek
    ileri taşınır.
    """
    # Sırası önemlidir. İleri dönüşümde önce kaydırır (dil + tilt + pitch) sonra roll ile döndürür.
    horiz, elev = azimuth_deg, elevation_deg
    if own_roll_deg:
        r = math.radians(own_roll_deg)
        c, s = math.cos(r), math.sin(r)
        horiz, elev = horiz * c + elev * s, -horiz * s + elev * c
    vert = elev - TILT_DEG - own_pitch_deg
    f = f_px(W)
    return (W / 2.0 + f * math.tan(math.radians(horiz)),
            H / 2.0 - f * math.tan(math.radians(vert)))


# ==========================================================
#  AYARLAR
# ==========================================================
class VisualCfg:
    """Görsel fazın ayarları: geçerlilik kapıları, kilit, kazançlar, köprü.

    Dikey/yaw tavanları burada TANIMLANMAZ, `ConverterCfg`ten okunur.
    `SpikeCfg` de yaw ve dikey kanal sabitlerini buradan okur — kamera ve
    araç sabitleri faza ait değildir, tek kaynakta durur.
    """

    # ============ GEÇERLİLİK KAPILARI (`aim_box`) ============
    CONF_MIN = 0.40     # 0..1; dedektör güveni bunun altındaki kutu güdüme HİÇ girmez.
                        # Ölçüldü: eşik 0.10'da tespit %49 / argmax doğru %43;
                        # 0.40'ta %40 / %40 — yani ~9 puan tespit karşılığında
                        # yanlış-pozitifin argmax'ı çalması TAMAMEN biter.
    SIZE_MIN_PX = 8.0   # px @1920; bundan küçük kutunun boyut ölçümü güvenilmezdir
                        # (menzil `C/size` olduğu için küçük kutuda hata patlar)
    RANGE_MAX_M = 50.0  # m; ÜST menzil kapısı. Ölçüldü: 60-90 m'de tespit %9 —
                        # orada görsel faz açılmaz, GPS fazı sürer.
    RANGE_MIN_M = 3.0   # m; ALT menzil kapısı. Bunun altındaki kutu gerçek hedef
                        # değil DEV YANLIŞ-POZİTİFtir: dedektör 140 m'de bu boyutta
                        # kutu üretiyordu, güdüm "temas" sanıp tam hücum veriyor ve
                        # araç yere çakılıyordu (iki koşu, "Player ☠").
                        # ⛔ DÜŞÜRMEYİN. Terminal fazın ihtiyacı `TERMINAL_GROWTH`
                        #   istisnasıyla, bu kapı silinmeden karşılanır.
    STALE_S = 0.5       # s; tespit bundan eskiyse artık güdüme giremez ("bayat")

    # ============ DEVİR KİLİDİ (GPS -> GÖRSEL kapısının 1. koşulu) ============
    # ⭐ İKİSİ BİRDEN GEREKİR; fiilî kapı = max(süre, kare/dedektör_hızı).
    #   Yalnız KARE saysaydık kapı dedektör hızlandıkça SESSİZCE zayıflardı:
    #       8-10 Hz -> 1.00 s | 29.9 FPS -> 0.33 s | 53.2 FPS -> 0.19 s
    #   Yalnız SÜRE saysaydık DONMUŞ kamerayla açılırdı (duvar saati ilerler,
    #   kare sayacı durur). Kapı geç açılıyorsa ÖNCE `HANDOFF_LOCK_S`i düşürün;
    #   hızlı dedektörde bağlayan koşul süredir, kare değildir.
    HANDOFF_LOCK_S = 1.0  # s; kanıt zincirinin kesintisiz sürmesi gereken SÜRE
    HANDOFF_FRAMES = 10   # adet; ayrı ayrı KARE sayısı (aynı kare tekrar sayılmaz)
   
    # ============ İLERİ HIZ: KAPANMA HIZI DENETİMİ ============
    V_MAX = 28.0          # m/s; ileri hız TAVANI — "hücum hızı" DEĞİLDİR.
                          # Hedef (Talon) 17.98 m/s uçuyor: 18 ile kapanma
                          # 0.02 m/s = asla yakalayamayız. 28 -> kapanma ~10 m/s.
    V_MIN = 0.0           # m/s; ileri hız TABANI — asla geri gitme

    # ⛔ MARJ ZORUNLU: TRAIL_RANGE_M > RANGE_MIN_M olmalı, EŞİT OLAMAZ.
    #   Yasa aracı tam olarak buraya oturtur; `aim_box` ise R < RANGE_MIN_M
    #   olan kutuyu REDDEDER. İkisi eşitken kararlı çalışma noktası ret
    #   sınırının ÜSTÜNDE durur ve kutu boyutundaki her bozulma sınırı
    #   geçirir. Dönüşte hedef bank yapınca kutu büyür, R = C/size KÜÇÜK
    #   okunur ve zincir şu olur:
    #       kutu büyür -> R < 3 -> aim_box RED -> BRIDGE_S(1 s) -> LOST_S(2 s)
    #       -> GPS fazı; hedef bu 3 saniyede dönüşünü tamamlar ve kaçar.
    #   Marj kutu büyüme oranından TÜRER (yeni tune düğmesi değildir):
    #       TRAIL_RANGE_M >= RANGE_MIN_M * (1 + g_max)
    #   ⭐ g_max ARTIK ÖLÇÜLDÜ (canlı kayıt, 135 s / 3567 kare, TensorRT):
    #     0.5 s'lik pencerede kutu tepe/taban oranı  p90 = 1.58, p99 = 3.76.
    #     Yani g_max(p90) = %58  ->  gereken marj 3.0 x 1.58 = 4.74 m.
    #     4.5 bunun hemen altındadır ve BİLİNÇLİDİR: p90 bir GEÇİCİ olaydır
    #     (on karede bir), `BRIDGE_S`(1 s) onu zaten yutar; kalıcı marj için
    #     ödenecek kapanma gücü bedeli buna değmez (aşağı bak).
    #   ⛔ AŞAĞI ÇEKMEYİN. TRAIL=3.0'da R_ölçülen = 3.0/(1+g) ve g>0 olan HER
    #     kare reddedilir — ölçülen medyan oran 1.10 olduğuna göre kareler
    #     kabaca YARISI. 3.5-4.0 da yetmez (g>%17 / %33 reddeder).
    #   ⛔ RANGE_MIN_M'i DÜŞÜREREK çözmeyin: o kapı 140 m'deki dev
    #     yanlış-pozitifleri kesen kapıdır (iki koşuda araç onsuz yere çakıldı).
    TRAIL_RANGE_M = 4.5   # m; kapanma profilinin SIFIRLANDIĞI menzil = aracın
                          # oturacağı denge noktası. `ATTACK_RANGE_M`(1 m) DEĞİLDİR:
                          # görü sınırının (RANGE_MIN_M) ALTINA regüle etmek,
                          # ulaşılamayan bir noktaya nişan almak olurdu.
    K_CLOSE = 0.6         # 1/s; menzil fazlasını kapanma hızına çeviren P kazancı:
                          # v_kapanma = K_CLOSE * (R - TRAIL_RANGE_M)
    V_CLOSE_MAX = 12.0    # m/s; azami kapanma hızı. Aynı zamanda `Rdot` fiziksel
                          # kapamasının sınırıdır — yasa bundan hızlı kapanma
                          # komut etmediğine göre bundan hızlı bir ÖLÇÜM de
                          # gerçek olamaz (bkz. `_closing_speed`).
    R_TAU = 0.20          # s; menzil yumuşatmasının zaman ölçeği. Hem EMA zaman
                          # sabiti hem de `size` medyan penceresi budur.
    V_TGT_TAU = 0.5       # s; hedefin LOS hızı kestiriminin EMA zaman sabiti

    # ============ YAW: BURNU KERTERİZE ÇEVİR ============
    K_YAW = 1.0           # oran (birimsiz); azimut hatasının ne kadarı burun
                          # hedefine yansıtılsın — 1.0 = TAM düzeltme
    KP_YAW_RATE = 3.0     # 1/s; yaw hatasını (derece) dönüş hızına (derece/s) çeviren P kazancı
    YAW_RATE_MAX = ConverterCfg.YAW_RATE_MAX_DEG  # derece/s; azami dönüş hızı (tek kaynak).
                          # Araç 214 yapabiliyor ama 120'de tutuluyor: hızlı yaw
                          # görüntüyü bulandırıp dedektörü kırar — BİLİNÇLİ.
    YAW_DEADBAND = 1.0    # derece; azimut hatası bunun altındaysa yaw düzeltmesi
                          # HİÇ verilmez (gürültüye karşı sakin burun)

    # ============ DİKEY: KADRAJ REGÜLASYONU (saf takip DEĞİL) ============
    # ⛔ SAF TAKİP DENENDİ VE ÇÖKTÜ. Hız vektörünü 3B'de hedefe nişanlamak,
    #   24° yükselişte 28*sin(24°) = 11.4 m/s tırmanma komutu veriyor; araç
    #   hedefin hizasına çıkıyor ve kamera 26.5° YUKARI baktığı için hedef
    #   görünmez oluyordu (tespit %90 -> %12-15, isabet 0/3). Yerine hedefi
    #   kadrajda sabit bir yükseklikte tutan regülasyon kondu.
    K_CY = 0.014             # (m/s)/px @1080 yükseklik; dikey kadraj hatasını
                             # dikey hıza çeviren P kazancı
    CY_REF = 470.0           # px @1080; hedefin tutulacağı kadraj yüksekliği (nişan
                             # noktası). Merkezin (540) ÜSTÜNDEDİR: kameranın 26.5°
                             # yukarı bakışıyla uyumlu olarak altta kalıp yukarı bakarız.
    VZ_CAP_VISUAL = 4.0      # m/s; dikey hız komutunun tavanı. Kazançla BİRLİKTE
                             # ayarlandı (0.06/1.5 -> 0.014/4.0): doyum oranı %97 -> %17.7,
                             # yani dikey kanal aç-kapa anahtarı olmaktan çıkıp gerçek
                             # bir orantılı kontrolcü oldu (doğrusal aralık ±25 -> ±286 px).
                             # Mekanizma: dikey komut throttle'ı sıçratır, araç savrulur,
                             # 70 px'lik hedef bulanır — |throttle| tespiti EN ÇOK bozan
                             # büyüklüktür (0.300 tespit var / 0.669 yok).
    VZ_MAX_CLIMB = ConverterCfg.VZ_MAX_CLIMB      # m/s; aracın zarfı (tek kaynak)
    VZ_MAX_DESCENT = ConverterCfg.VZ_MAX_DESCENT  # m/s; aracın zarfı (tek kaynak)

    # ============ KUTU KÖPRÜSÜ (ölü-hesap) ============
    # Çıkarım ~10-50 Hz, döngü 50 Hz: aradaki her tikte ve her tespit boşluğunda
    # güdüm kutusuz kalırdı. Köprü, son geçerli kutunun ATALET yönünü saklar ve
    # KENDİ dönüşümüzü telafi ederek kadraja geri yansıtır.
    # ⭐ Girdi yalnız son kutu + kendi IMU'muzdur: GPS yok, menzil yok.
    BRIDGE_S = 1.0  # s; bayat kutunun ileri taşınabileceği azami süre. Tarandı:
                    # 0.3 -> 3.35 m | 0.5 -> 1.90 m | 1.0 -> 1.34 m (en yakın menzil,
                    # kazanan) | 2.0 ek kazanç vermedi.

    # ============ TERMİNAL SÜREKLİLİK (yalnız ÇARPMA fazında) ============
    # ⛔ VARSAYILAN OLARAK ETKİSİZDİR. `aim_box` bu istisnayı yalnızca
    #   çağıran `last_size`/`last_age` VERİRSE uygular; vermezse davranış
    #   bit bit eskisiyle aynıdır. Gözetmen bunları YALNIZ SPIKE fazında
    #   geçirir — yani istisna yapısal olarak faz kapsamlıdır.
    #
    # NEDEN GEREKLİ: `RANGE_MIN_M`(3 m) altındaki kutu reddedilir, ardından
    #   `BRIDGE_S`(1 s) + `LOST_S`(2 s) gelir → son metrelerde KÖR uçuş.
    #   Çarpma fazının nişanı `ATTACK_RANGE_M`(1 m) olduğuna göre bu, tam da
    #   vuruşun son yarım saniyesinde güdümü kendi süzgecimizin kör etmesi
    #   demektir.
    # NEDEN KAPI SİLİNMİYOR: sebebi meşru. Dedektör 140 m'de dev
    #   yanlış-pozitif üretiyor, kutudan menzil 1.3 m çıkıyor, güdüm "temas"
    #   sanıp tam hücum veriyor ve araç yere çakılıyor (iki koşu, "Player ☠").
    # AYIRT EDİCİ FİZİK: dev yanlış-pozitif YOKTAN var olur; gerçek hedef
    #   BÜYÜYEREK gelir. İstisna bu sürekliliği arar — (a) son KABUL EDİLEN
    #   kutu taze mi (yaş <= BRIDGE_S), (b) yeni kutu ondan en fazla kaç kat
    #   büyük (<= TERMINAL_GROWTH). İkisi de sağlanmazsa eski davranış geçerli.
    # ⛔ GPS YOK: koşulun iki girdisi de piksel ve zamandır (§KATI KURAL temiz).
    TERMINAL_GROWTH = 2.0  # kat; son kabul edilen kutuya göre azami büyüme

# px; kutu kenarı kare sınırına bu kadar yaklaşmışsa KIRPILMIŞ sayılır.
# Tolerans değil, kayan nokta payıdır: dedektör kutuyu tam 0/W'ye kırpar.
EDGE_EPS_PX = 1.0


def _median(vals):
    """Küçük bir dizinin medyanı (boş dizide None).

    ⛔ ORTALAMA/EMA DEĞİL. Kutu boyutu gürültüsü DARBELİDİR (ardışık iki
      karede 4.26 kat sıçrama ölçüldü); EMA darbeyi silmez, zamana yayar.
      Medyan aykırı değeri tümden atar.
    """
    v = sorted(vals)
    n = len(v)
    if not n:
        return None
    return v[n // 2] if n % 2 else 0.5 * (v[n // 2 - 1] + v[n // 2])

# ==========================================================
#  KAPILAR
# ==========================================================
def aim_box(det, cfg=VisualCfg, last_size=None, last_age=None):
    """Bu tespit güdüme girebilir mi? Giremezse tespit yok sayılır.

    last_size / last_age : son KABUL EDİLEN kutunun boyutu (px) ve yaşı (s).
        VERİLMEZSE (None) davranış bit bit eskisiyle AYNIdır. Verilirse
        `RANGE_MIN_M` altındaki kutu için TERMİNAL SÜREKLİLİK istisnası
        açılır — bkz. `VisualCfg.TERMINAL_GROWTH`. Gözetmen bunları yalnız
        ÇARPMA fazında geçirir.
    """
    if det is None:
        return None
    W = float(det.get("W", 0)); H = float(det.get("H", 0))
    if W <= 1 or H <= 1:
        return None
    if float(det.get("conf", 0.0)) < float(cfg.CONF_MIN):
        return None
    s = _scale(W)
    size = max(float(det.get("w", 0.0)), float(det.get("h", 0.0)))
    if size < float(cfg.SIZE_MIN_PX) * s:
        return None
    R = range_m(size, W)
    if R is None or R > float(cfg.RANGE_MAX_M):
        return None
    if R < float(cfg.RANGE_MIN_M):
        # TERMİNAL SÜREKLİLİK İSTİSNASI — bkz. VisualCfg.TERMINAL_GROWTH.
        # Girdi verilmezse (None) burası HİÇ açılmaz ve eski davranış sürer.
        continuous = (last_size is not None and last_age is not None
                      and float(last_size) > 0.0
                      and float(last_age) <= float(cfg.BRIDGE_S)
                      and size <= float(cfg.TERMINAL_GROWTH) * float(last_size))
        if not continuous:
            return None
    cx = float(det.get("cx", -1.0)); cy = float(det.get("cy", -1.0))
    if not (0 <= cx < W and 0 <= cy < H):
        return None
    # ⛔ KIRPILMIS KUTU MENZİLİ BOZAR. Dedektör kutuyu kare sınırına kırpar;
    #   hedefin bir kısmı dışarıdaysa `size` KÜÇÜK ölçülür ve `R = C/size`
    #   BÜYÜK çıkar. Ölçüldü: hedef 8 m'deyken kadrajda %50'si kalırsa menzil
    #   16.0 m okunur ve kapanma hızı 3.0 yerine 7.8 m/s komut edilir — yani
    #   araç, sandığının YARISI kadar yakın olan hedefe doğru hızlanır.
    #   Kutunun KENARLARI kadrajın içinde olmalı, yalnız merkezi değil.
    #   Reddedilen kare KÖR bırakmaz: `BRIDGE_S` boyunca son geçerli kutu
    #   kendi dönüşümüzle ileri taşınır (bkz. CLAUDE.md — kısıt ve köprü
    #   birlikte anlamlıdır).
    w = float(det.get("w", 0.0)); h = float(det.get("h", 0.0))
    if (cx - w / 2.0 <= EDGE_EPS_PX or cx + w / 2.0 >= W - EDGE_EPS_PX
            or cy - h / 2.0 <= EDGE_EPS_PX or cy + h / 2.0 >= H - EDGE_EPS_PX):
        return None
    return det


# ⛔ DEVİR KADRAJ KAPISI — YENİ SABİT YOKTUR, ikisi de mevcut güdüm
#   sabitlerinden TÜRER. Kural tek cümle: *devir, görsel yasanın ilk
#   komutunu DOYURACAĞI bir noktada yapılmaz.*
#
#   Neden: devir anında hedef kadrajın kenarındaysa yaw çubuğu ±1'e, dikey
#   komut ±VZ_CAP_VISUAL'e çakılır. Ölçülmüş gerekçeler zaten dokümanda:
#   hızlı yaw görüntüyü bulandırıp dedektörü kırar (bu yüzden YAW_RATE_MAX
#   aracın 214'ü yerine 120'de tutuluyor) ve |throttle| tespiti en çok bozan
#   büyüklüktür (B7: 0.300 var / 0.669 yok). Köşede throttle HOVER_THR
#   −0.586'dan +0.096'ya sıçrar. Sonuç: savrul -> bulanıklaş -> kutuyu
#   kaybet -> LOST_S -> GPS'e dön, yani faz çırpınması.
#
#   ⚠ BU KAPI YALNIZ DEVİR KARARINA UYGULANIR, güdüme DEĞİL. Görsel faz
#     sürerken hedef kenara kayarsa yasa TAM DA yaw'ı doyurup onu geri
#     getirmelidir; orada reddetmek aracı kör bırakırdı.
#
#   ⚠ TEK KAPI KURALI KORUNUR: `handoff_framed` = `aim_box` VE kadraj
#     penceresi. Yani devirden geçen her kutu görsel fazın da kabul ettiği
#     kutudur; tersi (devrin, görsel fazın reddettiği kutuyla açılması)
#     mümkün değildir — CLAUDE.md'nin uyardığı çırpınma yönü budur.
def handoff_frame_limits(W, H, cfg=VisualCfg):
    """(dx, dy) — devir için izin verilen kadraj penceresinin yarı genişliği.

    dx: yaw doyum sınırı. `yaw_rate = KP_YAW_RATE * K_YAW * azimut` ve tavan
        `YAW_RATE_MAX` -> doyum azimutu = YAW_RATE_MAX/(KP_YAW_RATE*K_YAW).
        Piksele çevirisi ters kamera modelidir: dx = f_px * tan(azimut).
    dy: dikey doyum sınırı. `vz = (K_CY/sh) * e_cy` ve tavan
        `VZ_CAP_VISUAL` -> |e_cy| = VZ_CAP_VISUAL * sh / K_CY.
        Pencere kadrajın ORTASINA değil `CY_REF`e (nişan noktası) göredir.
    """
    az_sat = float(cfg.YAW_RATE_MAX) / (float(cfg.KP_YAW_RATE) * float(cfg.K_YAW))
    dx = f_px(W) * math.tan(math.radians(min(az_sat, 89.0)))
    sh = float(H) / REF_H
    dy = float(cfg.VZ_CAP_VISUAL) * sh / float(cfg.K_CY)
    return dx, dy


def handoff_framed(det, cfg=VisualCfg):
    """Bu kutuyla DEVİR yapılabilir mi? (güdüm geçerliliği için `aim_box`)"""
    if det is None:
        return False
    W = float(det.get("W", 0.0)); H = float(det.get("H", 0.0))
    if W <= 1 or H <= 1:
        return False
    dx, dy = handoff_frame_limits(W, H, cfg)
    cy_ref = float(cfg.CY_REF) * (H / REF_H)
    return (abs(float(det.get("cx", 0.0)) - W / 2.0) < dx
            and abs(float(det.get("cy", 0.0)) - cy_ref) < dy)

def spike_aim_limit(W, H, cfg=VisualCfg):
    """ÇARPMA kapısı için izin verilen DİKEY nişan hatası (px, yarı pencere).

    ⛔ NEDEN DEVİR PENCERESİNDEN ÇOK DAHA DAR. `handoff_frame_limits`in dy'si
      "komut DOYAR mı" sorusunu sorar (VZ_CAP_VISUAL*sh/K_CY = 286 px @1080).
      Çarpma için bu ölçüt YETMEZ: ölçülen iki ıskada dikey komut başlangıçta
      doymamıştı (1.92 ve 1.26 m/s, tavan 4.0) — koşu SÜRERKEN doydu.

    ⭐ DOĞRU ÖLÇÜT GEOMETRİKTİR: menzil kapandıkça açısal hata 1/R ile ŞİŞER.
      Sabit bir `d` sapmasında açı θ ≈ d/R ve kapanma |Ṙ| ile

          dθ/dt = ḋ/R + d·|Ṙ|/R²

      Açının BÜYÜMEMESİ için düzeltme hızı ḋ, `tan(θ)·|Ṙ|` değerini aşmalıdır.
      Elimizdeki düzeltme yetkisi `VZ_CAP_VISUAL`, en kötü kapanma ise hücum
      hızı `V_MAX` (hedef dursa bile o hızla kapanırız). Yani:

          tan(θ_max) = VZ_CAP_VISUAL / V_MAX
          dy_spike   = f_px(W) · tan(θ_max)

      ⚠ `sh` ÇARPANI YOKTUR — `f_px(W)` ölçeklemeyi zaten yapar (fx = fy).
        `handoff_frame_limits`teki dy'de `sh` vardır çünkü ORADA ölçüt
        `vz = (K_CY/sh)·e_cy` doyumudur ve `K_CY` @1080 tanımlıdır; burada
        ölçüt bir AÇI, dolayısıyla dönüşüm salt `f_px·tan(θ)`dır.
      @1920×1080: 540.4 × 4.0/28.0 = 77 px.  @1280×720: 51 px.

    ⭐ YENİ TUNE DÜĞMESİ YOK — ikisi de mevcut ölçülmüş sabit.

    ⚠ ÖLÇÜLEN AYRIM (2026-08-27 uçuşu, 5 isabet / 2 ıska, @720):
          isabetler |e_cy| =  9 ve 17 px  -> GEÇER
          ıskalar   |e_cy| = 60 ve 91 px  -> REDDEDİLİR
      Eşik 51 px ikisini de temiz ayırıyor. ⚠ TEK UÇUŞ — n<4, eşiğin kendisi
      canlıda doğrulanmalı.

    ⚠ YALNIZ DİKEY. O uçuşta ayırt edici değişken dikeydi; yatay kanal için
      aynı türetimi yapmak ölçüsüz bir varsayım olurdu, eklenmedi.
    """
    v_max = float(cfg.V_MAX)
    if v_max <= 1e-6:
        return float("inf")
    return f_px(W) * (float(cfg.VZ_CAP_VISUAL) / v_max)


def spike_framed(det, cfg=VisualCfg):
    """Bu kutuyla ÇARPMA fazına geçilebilir mi? (dikey nişan oturmuş mu)

    Devir kapısındaki ilkenin aynısı — *"faz, yasanın düzeltemeyeceği bir
    noktada değiştirilmez"* — ama çarpma için ölçüt doyum değil, terminal
    geometride açının BÜYÜMEMESİDİR (bkz. `spike_aim_limit`).
    """
    if det is None:
        return False
    W = float(det.get("W", 0.0)); H = float(det.get("H", 0.0))
    if W <= 1 or H <= 1:
        return False
    cy_ref = float(cfg.CY_REF) * (H / REF_H)
    return abs(float(det.get("cy", 0.0)) - cy_ref) < spike_aim_limit(W, H, cfg)


def is_stale(det, cfg=VisualCfg, now=None):
    """Tespit `STALE_S`ten eski mi? -> True ise güdüme giremez.

    det : tespit kaydı; `t` alanı perf_counter damgasıdır
    now : s; karşılaştırma anı (verilmezse şimdi)

    Tespitin HİÇ olmaması da bayat sayılır (None -> True).
    """
    if det is None or det.get("t") is None:
        return True
    now = time.perf_counter() if now is None else now
    return (now - float(det["t"])) > float(cfg.STALE_S)

# ==========================================================
#  GORSEL FAZ SÜRÜCÜSÜ
# ==========================================================
class VisualTracker:
    """GÖRSEL fazın sürücüsü — IBVS yasası + kutu köprüsü.

    İki dış yöntemi vardır:
        box(...)      hangi kutuyla uçacağız? (taze tespit ya da köprü)
        compute(...)  o kutudan çubuk komutu üret

    Araç hedefin KUYRUĞUNA oturur ve orada KALIR; temas etmez. Terminal hücum
    ayrı bir fazın (`control/spike.py`) işidir.
    """

    def __init__(self, cfg=VisualCfg):
        """cfg: görsel faz ayarları (varsayılan `VisualCfg`)."""
        self.cfg = cfg
        self.conv = VelocityToStick()
        self.reset()

    def reset(self):
        """Her yeni görsel faz başında çağrılır — kestirim durumu TAZE başlar.

        Taşınırsa bir önceki angajmanın menzil/hız kestirimi yeni angajmanın
        ilk tikine ön yük olarak girer ve komut sıçrar.
        """
        self._bridge = None     # son geçerli kutunun ATALET yönü {az, el, w, h, ...} | None
        self._bridge_count = 0  # adet; köprüden üretilen kare sayısı (mekanizma sütunu)
        self._size_buf = []     # [(t, kutu boyutu px)]; medyan süzgecinin penceresi.
                                # ⭐ SÜZGEÇ `size`A UYGULANIR, `R`YE DEĞİL (bkz. compute)
        self._R_f = None        # m; EMA ile süzülmüş menzil (kapanma profilinin girdisi)
        self._R_prev = None     # m; son menzil ÖLÇÜMÜ (türev için)
        self._dt_acc = 0.0      # s; iki menzil ölçümü arasında biriken süre
        self._Rdot = 0.0        # m/s; menzilin değişim hızı (negatif = kapanıyoruz)
        self._v_tgt_los = None  # m/s; hedefin LOS (görüş hattı) boyunca hızı | None
        self._v_cmd = 0.0       # m/s; son ileri hız komutu (köprü karesinde tekrarlanır)
        self._tlm = {}          # son tikin telemetrisi

    # ------------------------------------------------------------------
    def _closing_speed(self, R, yaw_des_deg, own_vel_ms, dt, bridge, no_brake=False):
        """KAPANMA HIZI DENETİMİ — ileri hız komutunu üretir (m/s).

        R           : m; bu karenin menzil ölçümü | None
        yaw_des_deg : derece; istenen burun yönü (LOS ekseni)
        own_vel_ms  : (vx, vy, vz) m/s; KENDİ hızımız
        dt          : s; ölçülmüş tik süresi
        bridge      : bu kare köprüden mi geldi? True ise kestirim ilerletilmez
        -> ileri hız komutu (m/s)

        YASA:  v_yer = v_hedef_LOS + K_CLOSE * (R - TRAIL_RANGE_M)
        Hedefin LOS hızı KUTU BÜYÜMESİNDEN kestirilir (`Rdot`), GPS'ten değil.
        Profil `TRAIL_RANGE_M`de sıfırlandığı için araç kuyrukta oturur.

        no_brake : ÇARPMA fazına geçişten hemen önceki ön-hızlanma penceresi
            (`Cfg.SPIKE_LEAD_S`). True iken kapanma profili menzille
            KÜÇÜLMEZ, tavanda tutulur — yani araç frenlemeyi bırakır ve
            geçişe `V_ATTACK`a yakın hızla girer. Gerekçe ve süre türetimi
            `control/main.py :: Cfg.SPIKE_LEAD_S`tedir.
        """
        p = self.cfg
        if R is None or dt <= 0.0:
            return self._v_cmd
        if bridge and self._v_tgt_los is not None:
            return self._v_cmd

        self._R_f = R if self._R_f is None else (
            self._R_f + (dt / (float(p.R_TAU) + dt)) * (R - self._R_f))

        self._dt_acc += dt
        h = math.radians(yaw_des_deg)
        own_los = own_vel_ms[0] * math.cos(h) + own_vel_ms[1] * math.sin(h)
        if self._R_prev is None:
            self._R_prev = R
            self._dt_acc = 0.0
            if self._v_tgt_los is None:
                self._v_tgt_los = clamp(own_los, 0.0, float(p.V_MAX))
        elif R != self._R_prev and self._dt_acc > 1e-6:
            # ⛔ FİZİKSEL KAPAMA — YOKSA DEDEKTÖR GÜRÜLTÜSÜ DOĞRUDAN FREN OLUR.
            #   `R = C/size` ve `size` dedektörün kutulama gürültüsünü AYNEN
            #   taşır. Canlı kayıtta (135 s, 3567 kare) ölçüldü: kutu boyutu
            #   ARDIŞIK iki karede **4.26 kat** sıçrayabiliyor. Ham türev o
            #   zaman |Rdot| = 1085 m/s veriyor — fiziksel olarak imkânsız.
            #   Zincir: Rdot -> raw -> `_v_tgt_los` SIFIRA çöküyor -> v_cmd
            #   3.49 m/s'ye iniyor (hedef 18 m/s uçarken) -> araç yavaşlıyor
            #   -> hedef kadrajdan çıkıyor -> "tespit yok" -> LOST_S.
            #   Canlı kayıtta uzun tespit-kaybı epizotlarının **7/8'i**
            #   öncesindeki 3 s içinde v_cmd < 12 m/s olan epizotlardı; OSD de
            #   doğruluyor (t=67.2 s'de SPD 31 km/h, normal seyir 64-66).
            #
            #   Sınır `V_CLOSE_MAX`'TAN TÜRER, yeni tune düğmesi YOKTUR: yasa
            #   zaten bundan hızlı bir kapanma KOMUT ETMEZ ve kuyruk takibinde
            #   menzil bundan hızlı kapanamaz. Ölçüldü (gerçek tespit dizisi):
            #       kapama yok  -> v_cmd min  3.49  | v_cmd<18 m/s: %11.0
            #       |Rdot|<=28  -> v_cmd min 12.89  | %5.4
            #       |Rdot|<=12  -> v_cmd min 16.35  | %3.0   <- SECILDI
            #   Medyan davranış değişmiyor (20.13 -> 20.39): sağlıklı rejime
            #   dokunmaz, yalnız imkânsız değerleri keser.
            self._Rdot = clamp((R - self._R_prev) / self._dt_acc,
                               -float(p.V_CLOSE_MAX), float(p.V_CLOSE_MAX))
            self._R_prev = R
            raw = own_los + self._Rdot
            b = self._dt_acc / (float(p.V_TGT_TAU) + self._dt_acc)
            self._v_tgt_los += b * (raw - self._v_tgt_los)
            self._v_tgt_los = clamp(self._v_tgt_los, 0.0, float(p.V_MAX))
            self._dt_acc = 0.0

        if no_brake:
            # ⛔ FREN KAPALI — profil menzille küçülmez, tavanda oturur.
            #   `v_tgt_los`(~16-18) + V_CLOSE_MAX(12) = ~28-30 -> V_MAX'a
            #   kırpılır, yani çarpma yasasının isteyeceği hızın TA KENDİSİ.
            #   Böylece faz geçişinde ileri kanalda BASAMAK KALMAZ.
            v_close = float(p.V_CLOSE_MAX)
        else:
            gap = max(0.0, self._R_f - float(p.TRAIL_RANGE_M))
            v_close = min(float(p.V_CLOSE_MAX), float(p.K_CLOSE) * gap)
        self._v_cmd = clamp(self._v_tgt_los + v_close,
                            float(p.V_MIN), float(p.V_MAX))
        return self._v_cmd

    # ------------------------------------------------------------------
    #  KUTU SEÇİMİ
    # ------------------------------------------------------------------
    def box(self, det, own_att_deg, t):
        """Güdüme verilecek kutuyu seçer: TAZE tespit ya da KÖPRÜ.

        det         : `aim_box`tan geçmiş tespit | None
        own_att_deg : (roll, pitch, yaw) derece; KENDİ yönelimimiz
        t           : s (perf_counter)
        -> kutu dict | None (köprü de üretemedi)

        Taze tespit varsa köprü durumu ONUNLA tazelenir ve tespit aynen
        döner. Tespit yoksa son kutunun atalet yönü, arada dönmüş olan kendi
        gövdemize göre kadraja geri yansıtılır ve `"bridge": True` işaretiyle
        döner — bu işaret yasada önemlidir: köprü karesinde menzil kestirimi
        ve integral İLERLETİLMEZ (aynı kutuyu tekrar kanıt saymamak için).

        ⭐ ÇARPMA fazı da bu köprüyü kullanır — köprü TEK KAYNAKTADIR.
        """
        roll, pitch, yaw = own_att_deg
        if det is not None:
            W = float(det["W"]); H = float(det["H"])
            az, el = pixel_bearing(float(det["cx"]), float(det["cy"]), pitch, roll, W, H)
            self._bridge = {"az": yaw + az, "el": el,
                            "w": float(det["w"]), "h": float(det["h"]),
                            "conf": float(det.get("conf", 0.0)),
                            "W": W, "H": H, "t": t}
            return det

        k = self._bridge
        if not k or float(self.cfg.BRIDGE_S) <= 0.0:
            return None
        if (t - k["t"]) > float(self.cfg.BRIDGE_S):
            return None
        az = wrap_deg(k["az"] - yaw)
        cx, cy = bearing_pixel(az, k["el"], pitch, roll, k["W"], k["H"])
        if not (0 <= cx < k["W"] and 0 <= cy < k["H"]):
            return None
        self._bridge_count += 1
        return {"cx": cx, "cy": cy, "w": k["w"], "h": k["h"],
                "conf": k["conf"], "W": k["W"], "H": k["H"], "t": k["t"],
                "bridge": True}

    # ------------------------------------------------------------------
    #  IBVS YASASI
    # ------------------------------------------------------------------
    def compute(self, det, own_att_deg, own_vel_ms, dt, no_brake=False):
        """IBVS YASASI — kutudan çubuk komutu üretir.

        det         : kutu (taze tespit ya da köprü); hedefe ait TEK veri budur
        own_att_deg : (roll, pitch, yaw) derece; KENDİ yönelimimiz (ego-motion)
        own_vel_ms  : (vx, vy, vz) m/s; KENDİ hız vektörümüz
        dt          : s; ölçülmüş tik süresi
        no_brake    : ön-hızlanma penceresi — bkz. `_closing_speed`
        -> (thr, pitch, roll, yaw), dördü de -1..+1 çubuk konumu

        ⛔ İmzada hedefe ait konum/hız/GNSS verisi YOKTUR ve olamaz; katı
          kural yapısal olarak burada sağlanır.
        """
        p = self.cfg
        own_roll, own_pitch, own_yaw = own_att_deg
        W = float(det["W"]); H = float(det["H"])
        cx = float(det["cx"]); cy = float(det["cy"])
        sh = float(H) / REF_H

        # --- 1) MENZİL ---
        # ⭐ SÜZGEÇ `size`'A UYGULANIR, `R`'YE DEĞİL — çünkü gürültü size'dadır
        #   ve `R = C/size` bir TERSLEMEdir. Simetrik piksel gürültüsü
        #   terslemeden sonra ÇARPIK ve AĞIR KUYRUKLU olur: küçük bir kutunun
        #   aşağı yönlü titremesi R'de dev bir sıçrama üretir. Ters sırada
        #   (önce R, sonra süzgeç) o sıçramalar süzgece girmiş olur.
        #   ⛔ ORTALAMA/EMA DEĞİL MEDYAN: gürültü darbelidir (canlı kayıtta
        #     ardışık iki karede 4.26 kat sıçrama ölçüldü); EMA darbeyi
        #     silmez, zamana yayar. Medyan aykırı değeri tümden atar.
        #   ⭐ PENCERE SÜREYLE, KARE SAYISIYLA DEĞİL. Dedektör hızı değişkendir
        #     (senkron 29.9 / ayrı thread 53.2 / TensorRT daha da hızlı);
        #     "son N kare" bir süre değildir ve hat hızlandıkça süzgeç
        #     SESSİZCE zayıflar — devir kapısında öğrenilen dersin aynısı.
        #   ⭐ PENCERE = `R_TAU`, yeni tune düğmesi YOKTUR: "menzili ne kadar
        #     sürede yumuşatıyoruz" ölçeği zaten odur. Ölçüldü (iki canlı
        #     kayıt, fiziksel olarak imkânsız |Rdot|>28 m/s oranı):
        #         pencere      video 1        video 2
        #         ham          %10.9          %35.1
        #         0.2 s (=R_TAU) %4.2          %12.7   <- SEÇİLDİ
        #         0.3 s         %3.7          %11.3
        #         0.5 s         %3.1           %9.2
        #     Uzun pencere biraz daha temizler ama medyan bir rampayı
        #     pencere/2 kadar GECİKTİRİR; 0.5 s'te bu 0.25 s, ~8 m/s kapanmada
        #     2 m bayat menzil demektir. 0.2 s kazancın çoğunu 0.1 s gecikmeyle
        #     alır.
        #
        #   ⚠ BEDELİ VAR VE ÖLÇÜLDÜ — iki ölçüt ÇELİŞİYOR. Aynı kod yolunda
        #     A/B (tek fark bu medyan):
        #         ölçüt                     video 1        video 2
        #         |Rdot| medyan          4.16 -> 1.65   12.00 -> 5.08   ⭐ iyi
        #         kapama doyumu         %21.3 -> %9.1   %59.2 -> %26.7  ⭐ iyi
        #         v_fwd p10             19.17 -> 18.98  20.67 -> 19.82  ⛔ kötü
        #         v_fwd < 18 m/s         %3.0 -> %4.7    %1.9 -> %3.6   ⛔ kötü
        #     Yani kestirim belirgin temizleniyor, komut biraz tembelleşiyor.
        #     ⛔ BU VERİYLE KARAR VERİLEMEZ: replay AÇIK ÇEVRİMDİR — kayıt
        #       ESKİ yasayla uçulmuş bir yörüngeden geliyor, yeni yasa farklı
        #       uçurur, farklı menzil ve farklı tespit üretirdi. Ayrıca
        #       "v<18" ölçütü hedefin 18 m/s uçtuğu VARSAYIMINA dayanır.
        #       Karar canlı uçuşla verilmeli. Geri alma: bu blokta `size`i
        #       `size_raw` yap (tampon telemetride kalmaya devam eder).
        #
        #   ⛔ DENENDİ, İŞE YARAMADI — HAMPEL (medyanı sinyal değil AYKIRI
        #     DEĞER REDDEDİCİ kullanmak: normal karede ham boyutu geçir,
        #     yalnız medyandan K kat sapanı reddet -> gecikmesiz temizlik).
        #     K=1.5/2.0/3.0 denendi, karelerin yalnız %0.2-2.0'si reddedildi
        #     ve |Rdot| medyanı video 2'de 12.00'de KALDI. Sebep: bu gürültü
        #     ara sıra gelen DARBE değil, SÜREKLİ geniş bantlı titremedir —
        #     her kare biraz yanlıştır, ayıklanacak tek bir aykırı yoktur.
        #     Bu yüzden gerçek yumuşatma dışında seçenek yok ve gecikme onun
        #     kaçınılmaz bedelidir.
        #   ⚠ KÖPRÜ KARELERİ TAMPONA GİRMEZ: köprü aynı kutuyu ileri taşır,
        #     onu tekrar tekrar beslemek medyanı yapay olarak dondururdu.
        size_raw = max(float(det["w"]), float(det["h"]))
        if not det.get("bridge"):
            t_det = float(det.get("t", 0.0))
            self._size_buf.append((t_det, size_raw))
            t_min = t_det - float(p.R_TAU)
            self._size_buf = [x for x in self._size_buf if x[0] >= t_min]
        size = _median([x[1] for x in self._size_buf]) or size_raw
        R = range_m(size, W)

        # --- 2) KERTERİZ ---
        azimuth, _ = pixel_bearing(cx, cy, own_pitch, own_roll, W, H)

        # --- 3) YAW (Burnu hedefe çevirir) ---
        eps_yaw = 0.0 if abs(azimuth) < float(p.YAW_DEADBAND) else azimuth
        yaw_des = own_yaw + float(p.K_YAW) * eps_yaw
        yaw_rate = clamp(float(p.KP_YAW_RATE) * wrap_deg(yaw_des - own_yaw), -float(p.YAW_RATE_MAX), float(p.YAW_RATE_MAX))

        # --- 4) İLERİ HIZ: KAPANMA HIZI DENETİMİ ---
        v = self._closing_speed(R, yaw_des, own_vel_ms, dt,
                                bridge=bool(det.get("bridge")), no_brake=no_brake)

        # --- 5) YATAY ---
        heading = math.radians(yaw_des)
        vx = v * math.cos(heading)
        vy = v * math.sin(heading)

        # --- 6) DİKEY ---
        cy_ref = float(p.CY_REF) * sh
        e_cy = cy - cy_ref  # + = hedef kadrajda ASAGIDA
        vz_raw = -(float(p.K_CY) / sh) * e_cy
        vz_up = clamp(vz_raw, -float(p.VZ_CAP_VISUAL), float(p.VZ_CAP_VISUAL))
        vz_up = clamp(vz_up, -float(p.VZ_MAX_DESCENT), float(p.VZ_MAX_CLIMB))

        # --- 7) HIZ -> ÇUBUK ---
        thr, pitch, roll, yaw = self.conv.convert((vx, vy, -vz_up), own_vel_ms, math.radians(own_yaw), yaw_rate)

        self._tlm = {
            "range_m": round(R, 2) if R else -1.0,
            "size_px": round(size, 1), "size_raw": round(size_raw, 1),
            "v_fwd": round(v, 2),
            "e_cy": round(e_cy, 1),
            "bridge": int(bool(det.get("bridge"))), "bridge_frames": self._bridge_count,
            "no_brake": int(bool(no_brake)),   # mekanizma sütunu: fren kapali mi
            "thr": round(thr, 3), "pitch": round(pitch, 3),
            "roll": round(roll, 3), "yaw": round(yaw, 3),
        }
        self._tlm.update(self.conv.diag)
        return float(thr), float(pitch), float(roll), float(yaw)

    def status(self):
        """Son tikin telemetrisi (yalnız gösterge; komuta girmez).

        `size_px` (süzülmüş) ile `size_raw` (ham) birlikte yayınlanır: ikisinin
        farkı, medyan süzgecinin o an ne kadar iş yaptığını doğrudan gösterir.
        """
        return dict(self._tlm)

# -*- coding: utf-8 -*-
"""
control/main.py — FAZ GÖZETMENİ (yalnız KAPILAR)

    KALKIŞ ──(irtifa)──> GPS ──(devir)──> GÖRSEL ──(10 s güdüm)──> ÇARPMA
                          ^                 │                        │
                          └──(kayıp, LOST_S)┴────────────────────────┘

Dört fazın da YASASI ayrı bir modüldedir (`takeoff.py`, `gps_approach.py`,
`visual_tracking.py`, `spike.py`); bu dosyada yalnız "hangi yasa koşacak?"
kararı vardır. `PhaseSupervisor` KOMUT ÜRETMEZ, döngü tutmaz ve giriş noktası
değildir — `python -m control.main` çalışmaz, görev `python -m web.server`
ile koşturulur.

Ayrımın sebebi: koşturucu (arayüz) değişse de kapı eşikleri tek yerde,
burada kalır. Kapıların OKUDUĞU veriler dışarıdan PARAMETRE olarak geçer
(`station_err=`, `range_h=`); gözetmen `GPSTracker`e bakmaz.

⛔ GÖRSEL/ÇARPMA FAZLARINDA HEDEFE AİT GPS VERİSİ KULLANILMAZ. Devir ve kalkış
   kapılarının hedef GNSS'ini okuması MEŞRUDUR: onlar bir FAZ GEÇİŞİ kararıdır,
   güdüm yasası değildir ve o anda henüz görsel temas yoktur. Görsel faz
   başladıktan sonra `visual_tick`/`spike_tick` imzalarında hedefe ait tek
   veri "kutu var mı yok mu"dur.
"""
import time

from control.visual_tracking import (VisualCfg, is_stale, aim_box, handoff_framed,
                                     spike_framed)
from perception import detection_state


class Cfg:
    """Faz KAPILARININ eşikleri — güdüm yasası değil, yalnız geçiş ölçütleri.

    Yasaların kendi sabitleri kendi modüllerindedir (`TakeoffCfg`, `GPSCfg`,
    `VisualCfg`, `SpikeCfg`). Burada yalnız "faz değişsin mi?" sorusunun
    eşikleri durur; koşturucu değişse de bu eşikler değişmez.
    """

    # --- KALKIŞ KAPISI ---
    TAKEOFF = True               # görev KALKIŞ fazıyla mı başlasın? False -> doğrudan
                                 # GPS fazından başlanır (araç zaten havadaysa)
    TAKEOFF_ALT_M = 45.0         # m; zemine göreli hedef tırmanma yüksekliği
    TAKEOFF_TOL_M = 3.0          # m; kalkış yüksekliğinin toleransı — kapı fiilen
                                 # (TAKEOFF_ALT_M - TAKEOFF_TOL_M) = 42 m'de açılır
    TAKEOFF_TARGET_GAP_M = 20.0  # m; hedefin irtifasına bu kadar yaklaşıldıysa
                                 # tırmanmaya devam etmek boşuna yoldur (kapının
                                 # 2. kolu). Hedef alçaktayken 45 m'ye çıkmak,
                                 # sonra tekrar inmek demek olurdu.

    # --- DEVİR KAPISI (GPS -> GÖRSEL) ---
    CAMERA_ONLY_GATE = False     # True -> devir kapısının 2. koşulu (istasyona
                                 # oturma) YAPISAL olarak devre dışı kalır ve sistem
                                 # KAMERA-TEK kapıya düşer.
                                 # ⚠ Ölçüldü: kamera kapısı tek başınayken araç daha
                                 #   oturmadan ateşliyordu — devir 22.7 m'de, 14.9 s'de,
                                 #   istasyon hatası hâlâ 34.6 m. "Otur, SONRA devret"
                                 #   hiç gerçekleşmiyordu.
    HANDOFF_RANGE_M = 20.0       # m; hedefe olan menzil bunun altında olmalı (2. koşul)
    HANDOFF_STATION_ERR_M = 8.0  # m; istasyon hatası bunun altındaysa "oturdu" sayılır
    HANDOFF_STATION_TICKS = 25   # tik; "oturmuş" durumun ARD ARDA sürmesi gereken tik
                                 # sayısı (50 Hz'de ~0.5 s). Tek tiklik tesadüfi
                                 # yakınlaşmayla devir açılmasın diye vardır.
    GPS_STALE_S = 2.0            # s; hedefin GNSS paketi bundan eskiyse "bayat" sayılır
                                 # ve devir kapısının 2. koşulu DÜŞER (kutu kapısı tek
                                 # başına yeter) — bayat GPS'e dayanarak beklemek anlamsızdır

    # --- GÖRSEL/ÇARPMA FAZINDAN DÖNÜŞ ---
    LOST_S = 2.0                 # s; bu kadar süre GÜDÜME GİREBİLECEK kutu gelmezse
                                 # GPS fazına dönülür. Kare sayısıyla DEĞİL SÜREYLE
                                 # yazıldı ki kamera thread'i donduğunda da tetiklensin
                                 # (donmuş kamerada kare sayacı hiç ilerlemez).

    # --- ÇARPMA KAPISI (GÖRSEL -> SPIKE) ---
    # ⭐ KURAL (kullanıcı kararı): 10 s görsel güdümden SONRA çarpma fazı.
    #   Süre GÖRSEL FAZA GİRİŞTEN itibaren sayılır ve faz GPS'e düşerse
    #   sıfırlanır — yani "10 saniye boyunca hedefi görsel olarak güttük"
    #   demektir, "görev başlayalı 10 s oldu" değil.
    SPIKE = True                 # ANA ANAHTAR (A/B): False iken HİÇBİR mod çarpma
                                 # fazını açamaz. Mod seçimiyle VE'lenir — mod
                                 # kararı göreve özeldir, bu ise derleme-zamanı
                                 # anahtarıdır.
    SPIKE_AFTER_VISUAL_S = 10.0  # s; çarpma fazının açılması için gereken KESİNTİSİZ
                                 # görsel güdüm süresi

    # --- ÖN-HIZLANMA PENCERESİ (fren, geçişten önce kapatılır) ---
    # ⛔ NEDEN GEREKLİ. Görsel faz hedefin kuyruğunda oturur: `v_close` menzil
    #   `TRAIL_RANGE_M`e yaklaştıkça küçülür, yani araç geçiş anına kadar
    #   FRENLEMEKTEDİR (canlıda ölçüldü: seyir 64-67 km/h ≈ 18 m/s). Çarpma
    #   yasası ise ilk tikte `V_ATTACK`(28 m/s) ister. Fren kalkmazsa geçiş
    #   anında istenen pitch adımı:
    #       pitch = K_V*(28-18)/A_MAX = 1.5*10/34 = 0.441
    #   ve bu `CommandSender.MAX_DELTA`(0.15)'in **2.9 KATI** — eğim sınırı
    #   ~3 tik (59 ms) boyunca DOYAR. Doymuş pitch = burun aşağı savrulma =
    #   bulanık görüntü = tam da dedektörü kıran şey (B7).
    #
    # ⭐ SÜRE ÖLÇÜLDÜ, TAHMİN EDİLMEDİ. Gerçek zincir (VelocityToStick ->
    #   MAX_DELTA eğim sınırı -> 46 ms ölü zaman -> 0.211 s yatış sabiti)
    #   simüle edildi; 18 -> 28 m/s tırmanışı:
    #       %63 (24.3 m/s) 0.74 s · %90 0... 1.22 s · %95 1.40 s · %99 1.70 s
    #
    #   ALT SINIR — geçişte ilk komut eğim sınırını aşmasın:
    #       dv <= MAX_DELTA*A_MAX/K_V = 0.15*34/1.5 = 3.40 m/s
    #       yani geçişte hız >= 24.60 m/s olmalı
    #       v0=18 -> 0.78 s | v0=17 -> 0.82 s | v0=16 -> 0.86 s  ==> 0.86 s
    #
    #   ÜST SINIR — ön-hızlanma sırasında menzil görüş tabanının altına inmesin
    #   (hedef 18 m/s, biz hızlanıyoruz, menzil kapanıyor):
    #       R0=6 m -> 0.90 s | R0=7 m -> 1.04 s | R0=8 m -> 1.16 s  ==> 0.90 s
    #
    #   GÜVENLİ PENCERE 0.86-0.90 s  ->  seçilen 0.90 s.
    #
    # ⚠ ÜST SINIR YAPISAL OLARAK KALDIRILDI. Pencere çok dardı ve canlıda
    #   ölçülen EN YAKIN menzil 4.5 m idi — oradan başlarsa üst sınır alt
    #   sınırın altına düşer ve ayar kendi kendini bozardı (menzil tabanı
    #   aşılır, kutu reddedilir, kapı TAZE kutu istediği için HİÇ açılamaz ve
    #   araç hedefin içinden geçer). Bu yüzden ön-hızlanma penceresinde
    #   TERMİNAL SÜREKLİLİK İSTİSNASI da açılır (bkz. `read_detection`):
    #   menzil kapanması artık kutuyu kaybettiremez. İstisna süreklilik şartı
    #   (taze + <= TERMINAL_GROWTH kat) ile korumalıdır; yalnız kapsamı 0.9 s
    #   genişler, gevşemez.
    SPIKE_LEAD_S = 0.90          # s; çarpma fazına geçişten bu kadar ÖNCE görsel
                                 # yasanın freni kapatılır (ön-hızlanma penceresi).
                                 # Aynı süre, nişan oturmasının TUTMA süresidir.
    # ⛔ SÜRE TEK BAŞINA YETMEZ — kapı ayrıca O ANDA GEÇERLİ bir kutu ister.
    #   Kamera donarsa `seq` durur ama duvar saati ilerler; saf süre kapısı
    #   DONMUŞ bir görüntüyle çarpma fazını açardı. Devir kapısında ölçülmüş
    #   ve kayıtlı olan dersin aynısı (53 Hz'de 0.20 s'de donan kamera saf
    #   süre kapısını 1.00 s'de açıyordu). Çarpmada bedeli daha ağırdır:
    #   bayat kanıtla çarpışma rotasına girilir.


class PhaseSupervisor:
    """Faz durum makinesi. Komut ÜRETMEZ, yalnız "hangi faz?" sorusunu yanıtlar.

    Koşturucu her tikte içinde bulunulan faza karşılık gelen `*_tick`
    yöntemini çağırır; yöntem True dönerse FAZ DEĞİŞTİ demektir ve yeni faz
    `self.phase`tedir. Faz değişimini açıklayan insan-okur metin
    `handoff_message()` ile alınır.

    Gözetmen kendi başına telemetri okumaz: kapıların ihtiyaç duyduğu her şey
    (istasyon hatası, menzil, ham GNSS demeti, tespit) dışarıdan PARAMETRE
    olarak geçer. Böylece kapılar `GPSTracker`in iç yapısına bağlı kalmaz.
    """

    TAKEOFF = "TAKEOFF"  # kalkış: yalnız dikey tırmanış
    GPS = "GPS"          # istasyon tutma (arayüzde "STATION" etiketiyle görünür)
    VISUAL = "VISUAL"    # IBVS görsel takip — kuyrukta oturur ve kalır
    SPIKE = "SPIKE"      # terminal hücum

    def __init__(self, cfg=Cfg, visual_cfg=VisualCfg):
        """cfg: kapı eşikleri; visual_cfg: kutu kapısının/kilidin ölçütleri."""
        self.cfg = cfg
        self.visual_cfg = visual_cfg
        self._spike_mode = True  # henüz bir görev modu seçilmedi -> karar
                                 # yalnız `Cfg.SPIKE`ta (eski davranışın aynısı)
        self.reset()

    def reset(self, spike=None):
        """Yeni görev: fazı başa al ve TÜM kanıt sayaçlarını sıfırla.

        spike : bu GÖREVDE çarpma fazına izin verilsin mi? (mod kararı)
                True  -> HİBRİT + ÇARPMA
                False -> GPS ve düz HİBRİT (görsel faz kuyrukta oturur ve kalır)
                None  -> önceki görevin kararı KORUNUR

        ⛔ ÇARPMA KARARI ÖRNEKTE DURUR, `Cfg`DE DEĞİL. Mod seçimi `Cfg.SPIKE`i
          yazsaydı bir sonraki görev onu DEVRALIRDI: "hibrit + çarpma"
          koşusundan sonra "hibrit" seçilse bile çarpma fazı açılmaya devam
          ederdi. Bu, görevi durdurup yeniden başlatmada ölçülüp giderilen
          MODÜL DURUMU kusurlarının tam olarak aynısı olurdu.

        ⚠ `spike=None` VARSAYILANI "AÇ" DEMEZ, önceki kararı KORUR. Bir gün
          buraya mod bilgisi taşımayan ikinci bir `reset()` çağrısı eklenirse
          (ör. faz sıfırlaması), düz HİBRİT görevde çarpma fazını SESSİZCE
          geri açmasın diye.

        Buradaki her alan GÖREV KAPSAMLIDIR; taşınırsa yeni görev bir önceki
        görevin kanıtıyla açılır (ör. dolu bir kilit sayacı devri ilk tikte
        ateşler).
        """
        if spike is not None:
            self._spike_mode = bool(spike)
        self.phase = self.TAKEOFF if self.cfg.TAKEOFF else self.GPS
        self.handoff_count = 0      # adet; bu görevde kaç kez GPS -> GÖRSEL devri oldu
        self._lock = 0              # adet; ard arda kilit koşulunu sağlayan KARE sayısı
        self._lock_since = None     # s (perf_counter); kesintisiz kanıt zincirinin başlangıcı
        self._last_frame_t = None   # s; son YENİ karenin damgası (donmuş kamera tespiti)
        self._last_seq = None       # kare sayacı; aynı kareyi iki kez saymamak için
        self._station_ticks = 0     # adet; ard arda "istasyona oturmuş" TİK sayısı
        self._framed = False        # son kare devrin kadraj penceresinde miydi?
        self._aim_settled = False   # son kare ÇARPMA nişan penceresinde miydi?
        self._aim_settled_t = None  # s; nişanın SON oturduğu an (ön-hızlanma tutması)
        self._last_valid_t = None   # s; güdüme girebilecek son kutunun damgası (LOST_S sayacı)
        self._visual_since = None   # s; GÖRSEL faza giriş damgası (çarpma kapısının sayacı)
        self._last_ok_size = None   # px; son KABUL EDİLEN kutunun boyutu
        self._last_ok_t = None      # s; ... ve damgası — terminal süreklilik istisnası için
        self._spike_count = 0       # adet; bu görevde kaç kez çarpma fazı açıldı
        self._last_raw = None       # ham GNSS demeti; yeni paket geldi mi anlamak için
        self._last_packet_t = None  # s; son YENİ GNSS paketinin damgası (bayatlık ölçümü)
        self._message = ""          # son faz değişiminin insan-okur açıklaması

    @property
    def spike_enabled(self):
        """Bu görevde ÇARPMA fazı açılabilir mi? -> True/False

        İKİ ANAHTARIN VE'sidir ve VE yalnız burada yapılır:
          `Cfg.SPIKE`  — ANA anahtar (A/B). False iken HİÇBİR mod çarpma
                         fazını açamaz.
          mod kararı   — görev başında `reset(spike=...)` ile verilir
                         (HİBRİT + ÇARPMA -> True, diğerleri -> False).

        ⛔ ÖZNİTELİK DEĞİL ÖZELLİK (property) OLMASI BİLİNÇLİDİR. Bir kez
          hesaplanıp saklansaydı `Cfg.SPIKE` değiştirildiğinde BAYAT kalırdı;
          ayrıca VE'yi hem kapıların hem telemetrinin ayrı ayrı yapması, iki
          yerin zamanla ayrışması demek olurdu — arayüz "AÇIK" derken kapının
          kapalı olması gibi SESSİZ bir çelişki.
        """
        return bool(self.cfg.SPIKE) and bool(self._spike_mode)

    # ================================================================
    #  GİRDİ OKUMA
    # ================================================================
    def read_detection(self, t=None):
        """detection_state'ten güdüme girebilecek tespitleri okur -> (det, seq)."""
        t = time.perf_counter() if t is None else t
        det, seq, _ = detection_state.status()
        if is_stale(det, self.visual_cfg, now=t):
            return None, seq
        # ⛔ TERMİNAL SÜREKLİLİK YALNIZ ÇARPMA FAZINDA. Diğer fazlarda
        #   `last_size`/`last_age` geçirilmez, yani `aim_box` bit bit eski
        #   davranışını sürdürür ve `RANGE_MIN_M` altındaki dev yanlış-pozitif
        #   korumasında hiçbir gevşeme olmaz.
        if (self.phase == self.SPIKE or self.spike_armed(t)) and self._last_ok_size is not None:
            return aim_box(det, self.visual_cfg,
                           last_size=self._last_ok_size,
                           last_age=(t - self._last_ok_t) if self._last_ok_t else None), seq
        return aim_box(det, self.visual_cfg), seq

    def _track_packet(self, last_raw, t):
        """Yeni ham GNSS paketi geldiyse damgayı tazeler (bayatlık ölçümü için).

        last_raw : `GPSTracker.last_raw` — SDK'nın döndürdüğü ham demet
        t        : s (perf_counter); bu tikin zamanı
        """
        if last_raw is not None and last_raw != self._last_raw:
            self._last_raw = last_raw
            self._last_packet_t = t

    def gnss_stale(self, t=None):
        """Hedefin GNSS paketi `GPS_STALE_S`ten eski mi? -> True/False

        True iken devir kapısının 2. koşulu (istasyona oturma) DÜŞER: bayat
        GPS'e dayanarak "oturduk mu?" diye beklemenin anlamı yoktur.
        """
        if self._last_packet_t is None:
            return False
        t = time.perf_counter() if t is None else t
        return (t - self._last_packet_t) > self.cfg.GPS_STALE_S

    def _process_frame(self, t, det, seq):
        """Bu tikin tespitini kanıt zincirine işler — her fazda çağrılır.

        t   : s (perf_counter); tikin zamanı
        det : `aim_box`tan geçmiş tespit | None
        seq : kare sayacı (`detection_state`ten); aynı kareyi tekrar saymamak için

        Sürdürdüğü şeyler: kilit sayacı/süresi, kayıp sayacı (`_last_valid_t`),
        kadraj ve nişan pencereleri, terminal süreklilik istisnasının girdisi.

        ⚠ KAPI TİK DEĞİL, KARE SAYAR. Döngü 50 Hz, dedektör çok daha yavaş —
          aynı kutu onlarca tik boyunca tekrar görünür. Ayırt edilmezse "10
          kare" şartı fiilen 10 tik = 0.2 s olur ve kapı TEK tespitle açılır.
          Ayrım `seq` ile yapılır.
        """
        if (self._last_frame_t is not None and (t - self._last_frame_t) > self.visual_cfg.STALE_S):
            self._lock = 0
            self._lock_since = None
        if det is None:
            self._lock = 0
            self._lock_since = None
            self._last_seq = seq
            self._framed = False
            self._aim_settled = False
            return
        # Kutu GÜDÜM için geçerli (aim_box'tan geçti) -> LOST_S sayacı tazelenir.
        # Bu satır kadraj koşulundan ÖNCEDEDIR ve öyle kalmalıdır: kenardaki
        # kutu devri açmaz ama görsel faz sürerken hedefi KAYIP saydırmaz.
        self._last_valid_t = t
        # Terminal süreklilik istisnasının girdisi: SON KABUL EDİLEN kutu.
        # Köprü kareleri buraya hiç gelmez (gözetmen ham tespiti görür).
        try:
            self._last_ok_size = max(float(det["w"]), float(det["h"]))
            self._last_ok_t = t
        except (KeyError, TypeError, ValueError):
            pass
        if seq == self._last_seq:
            return
        self._last_seq = seq
        self._last_frame_t = t

        # ⛔ DEVİR İÇİN EK KOŞUL: KADRAJ PENCERESİ (yalnız kilit zincirine).
        #   Kutu, görsel yasanın ilk komutunu doyuracağı bir noktadaysa kanıt
        #   zinciri KIRILIR — devir orada açılmaz. Eşikler yeni sabit değil,
        #   mevcut güdüm sabitlerinden türer (visual_tracking.handoff_framed).
        self._aim_settled = spike_framed(det, self.visual_cfg)
        if self._aim_settled:
            self._aim_settled_t = t
        self._framed = handoff_framed(det, self.visual_cfg)
        if not self._framed:
            self._lock = 0
            self._lock_since = None
            return
        if self._lock_since is None:
            self._lock_since = t
        self._lock += 1

    def _lock_s(self, t):
        """Kanıt zinciri kaç saniyedir kesintisiz sürüyor? -> s (0.0 = zincir yok)"""
        return 0.0 if self._lock_since is None else (t - self._lock_since)

    def _is_locked(self, t):
        """Görsel kilit kuruldu mu? (devir kapısının 1. koşulu)

        ÜÇ şart birden: hem `HANDOFF_FRAMES` kadar ayrı KARE, hem
        `HANDOFF_LOCK_S` kadar SÜRE, hem de zincirin kırılmamış olması.

        ⭐ İkisi birden gerekir çünkü tek başına hiçbiri yetmez: yalnız kare
          sayarsak kapı dedektör hızlandıkça SESSİZCE zayıflar (10 kare 8 Hz'de
          1.00 s, 53 Hz'de 0.19 s eder); yalnız süre sayarsak DONMUŞ bir
          kamerayla açılır (duvar saati ilerler, `seq` durur).
        """
        if self._lock_since is None:
            return False
        if self._lock < self.visual_cfg.HANDOFF_FRAMES:
            return False
        return self._lock_s(t) >= self.visual_cfg.HANDOFF_LOCK_S

    def _is_settled(self, t, station_err, range_h):
        """Araç istasyona oturdu ve devir menziline girdi mi? (2. koşul)

        station_err : m; istasyon noktasına olan hata | None
        range_h     : m; hedefe olan menzil | None

        Koşulun sağlanmış SAYILDIĞI iki istisna vardır: `CAMERA_ONLY_GATE`
        açıksa (yapısal olarak kamera-tek kapıya düşülür) ve GNSS bayatsa.
        """
        if self.cfg.CAMERA_ONLY_GATE:
            return True
        if self.gnss_stale(t):
            return True
        if station_err is None or range_h is None:
            self._station_ticks = 0
            return False
        if (station_err <= self.cfg.HANDOFF_STATION_ERR_M
                and range_h <= self.cfg.HANDOFF_RANGE_M):
            self._station_ticks += 1
        else:
            self._station_ticks = 0
        return self._station_ticks >= self.cfg.HANDOFF_STATION_TICKS

    def _is_climbed(self, height, target_alt_gap):
        """Kalkış bitti mi? İki yoldan BİRİ yeter.

        height         : m; zemine göreli yükseklik
        target_alt_gap : m; kendi irtifamız - hedefin irtifası (hedef yoksa None)

        1. zemine göreli (TAKEOFF_ALT_M - TAKEOFF_TOL_M) = 42 m'ye ulaşıldı, YA DA
        2. hedefin irtifasına `TAKEOFF_TARGET_GAP_M` kadar yaklaşıldı — hedef
           alçaktaysa 45 m'ye tırmanmak boşuna yoldur.

        ⛔ 2. kol hedefin GPS'ini okur ve MEŞRUDUR: bu bir faz geçişi kapısıdır,
          güdüm yasası değildir ve o anda henüz görsel temas yoktur.
        """
        if (target_alt_gap is not None and target_alt_gap >= -self.cfg.TAKEOFF_TARGET_GAP_M):
            return True
        return height >= (self.cfg.TAKEOFF_ALT_M - self.cfg.TAKEOFF_TOL_M)

    # ================================================================
    #  KAPILAR
    # ================================================================
    def takeoff_tick(self, t, height, target_alt_gap=None, det=None, seq=None, last_raw=None):
        """KALKIŞ fazının kapısı. -> True ise faz GPS'e geçti.

        t              : s (perf_counter)
        height         : m; zemine göreli yükseklik (`TakeoffLaw.height`)
        target_alt_gap : m; kendi irtifamız - hedefin irtifası | None
        det, seq       : tespit ve kare sayacı — komuta girmez, yalnız kanıt
                         zinciri kalkış boyunca da işlensin diyedir
        last_raw       : ham GNSS demeti (bayatlık izleme)
        """
        self._track_packet(last_raw, t)
        self._process_frame(t, det, seq)
        if not self._is_climbed(height, target_alt_gap):
            return False

        self.phase = self.GPS
        self._message = ("Kalkış tamamlandı (%.0f m)" % height)
        return True

    def gps_tick(self, t, det, seq, station_err=None, range_h=None, last_raw=None):
        """DEVİR KAPISI (GPS -> GÖRSEL). -> True ise faz GÖRSEL'e geçti.

        İki koşul BİRLİKTE sağlanmalıdır:
          1. görsel kilit  (`_is_locked`)  — kesintisiz süre VE kare
          2. istasyona oturma (`_is_settled`) — hata VE menzil, ard arda tik

        station_err / range_h : m; kapının 2. koşulunun girdileri. Gözetmen
            bunları kendisi okumaz, koşturucu geçirir.
        """
        self._track_packet(last_raw, t)
        self._process_frame(t, det, seq)
        settled = self._is_settled(t, station_err, range_h)
        if not (self._is_locked(t) and settled):
            return False

        self.phase = self.VISUAL
        self._visual_since = t      # ÇARPMA kapısının sayacı burada başlar
        self.handoff_count += 1
        distance = ("%.0f m" % range_h) if range_h else "?"
        self._message = ("Görsel temas kuruldu (#%d, menzil %s, kilit %.1f s / %d kare%s) - " % (self.handoff_count, distance, self._lock_s(t), self._lock,
                            "GNSS bayat" if self.gnss_stale(t) else ""))
        return True

    def visual_s(self, t):
        """GÖRSEL faza gireli kaç saniye oldu? -> s (0.0 = görsel fazda değiliz)

        Faz GPS'e düşerse sıfırlanır; yani "10 saniyedir hedefi GÖRSEL olarak
        güdüyoruz" demektir, "görev başlayalı 10 s oldu" değil.
        """
        return 0.0 if self._visual_since is None else (t - self._visual_since)

    def spike_armed(self, t=None):
        """ÖN-HIZLANMA penceresinde miyiz? (fren kapalı + terminal istisna açık)

        Çarpma kapısının açılmasına `SPIKE_LEAD_S` kaldıysa True olur. İki şey
        birden yapar (ikisi de aynı pencerede olmalı, bkz. Cfg.SPIKE_LEAD_S):
          1. Görsel yasanın FRENİNİ kapatır -> araç geçişe hızlı girer.
          2. `aim_box`ın terminal süreklilik istisnasını açar -> hızlanmanın
             kapattığı menzil kutuyu KAYBETTİREMEZ.
        """
        # ⭐ DÜZ HİBRİT MODDA BU PENCERE HİÇ AÇILMAZ (`spike_enabled` False).
        #   Sonucu yalnız fren değildir: `read_detection` terminal süreklilik
        #   istisnasını da bu pencereye bakarak açar, dolayısıyla o modda
        #   `aim_box` bit bit ESKİ davranışındadır — `RANGE_MIN_M` korumasında
        #   hiçbir gevşeme olmaz.
        if not self.spike_enabled or self.phase != self.VISUAL:
            return False
        t = time.perf_counter() if t is None else t
        need = float(self.cfg.SPIKE_AFTER_VISUAL_S) - float(self.cfg.SPIKE_LEAD_S)
        if self.visual_s(t) < need:
            return False
        # ⛔ NİŞAN OTURMAMIŞSA ÖN-HIZLANMA DA BAŞLAMAZ. Aksi halde araç
        #   frenini bırakıp ~5 m'ye kadar kapanır, sonra çarpma kapısı
        #   nişan koşulundan geçmediği için AÇILMAZ ve araç istasyonun çok
        #   içinde, frensiz kalır. İki kapı AYNI koşula bağlıdır.
        #
        # ⚠ AMA TUTMA SÜRESİYLE — yoksa ÇIRPINIR. Ölçüldü: nişan penceresi
        #   canlı kayıtta karelerin yalnız %29.4'ünde açık. Ham koşula
        #   bağlansaydı fren açılıp kapanır, ileri komut 18 <-> 28 m/s
        #   arasında salınır ve her salınım 0.44'lük bir pitch adımı
        #   (MAX_DELTA'nın 2.9 katı) üretirdi — tam da bu mekanizmayla
        #   önlemeye çalıştığımız şey.
        # ⭐ TUTMA = `SPIKE_LEAD_S`, yeni sabit yok: ön-hızlanma penceresinin
        #   kendisi kadar. Nişan bu süre içinde bir kez oturduysa hazır sayılır.
        if self._aim_settled_t is None:
            return False
        return (t - self._aim_settled_t) <= float(self.cfg.SPIKE_LEAD_S)

    def _is_spike_ready(self, t, det):
        """Çarpma fazı açılsın mı? İKİ koşul BİRLİKTE.

        1. GÖRSEL fazda kesintisiz `SPIKE_AFTER_VISUAL_S` (10 s) geçmiş olmalı.
        2. O ANDA güdüme girebilecek TAZE bir kutu bulunmalı (`det` dolu, yani
           `aim_box`tan geçmiş ve `STALE_S`ten taze).

        ⛔ 2. KOŞUL VAZGEÇİLMEZDİR. Kamera donarsa kare sayacı durur ama duvar
          saati ilerler; saf süre kapısı çarpma fazını DONMUŞ bir görüntüyle
          açardı. Devir kapısında ölçülen dersin aynısı — ama bedeli daha
          ağır, çünkü burada bayat kanıtla çarpışma rotasına girilir.
        """
        if not self.spike_enabled:
            return False
        if det is None:
            return False
        # ⛔ 3. KOŞUL: DİKEY NİŞAN OTURMUŞ OLMALI (2026-08-27, canlı ıskadan).
        #   Ölçüldü — 5 isabet / 2 ıska ayni uçusta, ayirt edici tek değişken
        #   hücuma girerkenki dikey hataydı:
        #       isabetler |e_cy| =  9 / 17 px @720, dikey komut DOYUMU %0.0
        #       ıskalar   |e_cy| = 60 / 91 px @720, doyum %9.8 ve %20.9
        #   Iskalarda hedef tırmanan kaçamak dönüş yaptı; açı koşu boyunca
        #   KAPANMAK yerine BÜYÜDÜ (47° -> 69°) ve araç altından geçti.
        #   Terminal fazda bu düzeltilemiyor: OSD'ye göre araç 79 km/h'de
        #   yalnız 0.88 m/s tırmanabildi (yasa 4.0 istiyordu) — ileri hız,
        #   itkinin çoğunu ileri harcıyor. Çare hücuma HATASIZ girmektir.
        #   Eşik `spike_aim_limit`te TÜRETİLİR (yeni tune düğmesi yok).
        if not spike_framed(det, self.visual_cfg):
            return False
        return self.visual_s(t) >= float(self.cfg.SPIKE_AFTER_VISUAL_S)

    def visual_tick(self, t, det, seq, box_ok, last_raw=None):
        """GÖRSEL fazın kapısı. -> True ise faz DEĞİŞTİ (ÇARPMA ya da GPS).

        İki çıkış vardır: yukarı doğru ÇARPMA kapısı (`_is_spike_ready`),
        aşağı doğru `LOST_S` kadar kutu gelmemesi.

        box_ok : güdüme fiilen bir kutu verilebildi mi? (taze tespit YA DA
                 köprünün ileri taşıdığı kutu). `det`ten ayrıdır: köprü
                 karesinde `det` None olabilir ama `box_ok` True'dur.
        """
        self._track_packet(last_raw, t)
        self._process_frame(t, det, seq)

        # ---- ÇARPMA KAPISI (GÖRSEL -> SPIKE) ----
        # Kayıp kontrolünden ÖNCEDEDİR ve öyle olmalıdır: kapı zaten TAZE kutu
        # şart koşuyor, yani kayıp durumdayken hiç açılamaz.
        if self._is_spike_ready(t, det):
            self.phase = self.SPIKE
            self._spike_count += 1
            self._message = ("ÇARPMA fazı (#%d, %.1f s görsel güdüm sonrası)"
                             % (self._spike_count, self.visual_s(t)))
            return True

        if box_ok:
            return False

        lost_s = (t - self._last_valid_t) if self._last_valid_t else 0.0
        if lost_s <= self.cfg.LOST_S:
            return False

        self.phase = self.GPS
        self._visual_since = None
        self._aim_settled_t = None
        self._lock = 0
        self._lock_since = None
        self._station_ticks = 0
        self._framed = False
        self._message = ("Hedef %.1f s kayıp. GPS takibine geçildi" % lost_s)
        return True

    def spike_tick(self, t, det, seq, box_ok, last_raw=None):
        """ÇARPMA fazının kapısı — tek çıkışı hedefi kaybetmektir.

        ⛔ KAYIPTA DOĞRUDAN GPS'E DÖNÜLÜR, GÖRSEL FAZA UĞRANMAZ. İlk sürümde
          "önce görsele dön, o toparlayamazsa GPS'e insin" diye iki kademeli
          yazmıştım; kuru koşuda o ara adımın **BOŞ** olduğu görüldü: iki faz
          da aynı `_last_valid_t`ye bakar, dolayısıyla görsel faz daha ilk
          tikte aynı kaybı görüp GPS'e düşüyordu (ölçüldü: SPIKE -> VISUAL
          t=27.00, VISUAL -> GPS t=27.02 — 20 ms'lik sahte bir kademe).
          Görsel fazın elinde çarpma fazından FAZLA bilgi yoktur.

        ⭐ GPS DOĞRU HEDEFTİR: temas menzilinde 28 m/s ile kutuyu kaybetmişsek
          saniyenin onda birinde hedefin yanından geçmiş oluruz. O noktada
          yapılacak şey istasyonu yeniden kurmaktır — ve bunun için ısınmış
          GNSS filtresi zaten hazır bekliyor (çarpma fazında da beslendi).
        """
        self._track_packet(last_raw, t)
        self._process_frame(t, det, seq)
        if box_ok:
            return False

        lost_s = (t - self._last_valid_t) if self._last_valid_t else 0.0
        if lost_s <= self.cfg.LOST_S:
            return False

        self.phase = self.GPS
        self._visual_since = None
        self._aim_settled_t = None
        self._lock = 0
        self._lock_since = None
        self._station_ticks = 0
        self._framed = False
        self._message = ("Hedef %.1f s kayıp. ÇARPMA bırakıldı, GPS takibine geçildi"
                         % lost_s)
        return True

    # ================================================================
    #  GÖSTERGE
    # ================================================================
    def handoff_message(self):
        """SON faz değişimini açıklayan insan-okur metin (olay günlüğü için)."""
        return self._message

    def status(self, t=None):
        """Kapıların o anki durumu — arayüz telemetrisi; komuta GİRMEZ.

        Her "X" alanının yanında bir "X_need" alanı vardır: kapının hangi
        koşulda takıldığı arayüzden doğrudan okunabilsin diye.
        """
        t = time.perf_counter() if t is None else t
        return {
            "phase": self.phase,
            "lock": self._lock,
            "lock_need": self.visual_cfg.HANDOFF_FRAMES,
            "lock_s": self._lock_s(t),
            "lock_s_need": self.visual_cfg.HANDOFF_LOCK_S,
            "framed": bool(self._framed),
            "station_ticks": self._station_ticks,
            "station_ticks_need": self.cfg.HANDOFF_STATION_TICKS,
            "handoff_count": self.handoff_count,
            "visual_s": self.visual_s(t),
            # ⚠ İSTENEN değil GERÇEKLEŞEN değer: mod açmış olsa da `Cfg.SPIKE`
            #   kapalıysa çarpma fazı koşmaz, arayüz de "KAPALI" göstermelidir.
            "spike_enabled": self.spike_enabled,
            "spike_s_need": self.cfg.SPIKE_AFTER_VISUAL_S,
            "spike_count": self._spike_count,
            "spike_armed": self.spike_armed(t),
            "aim_settled": bool(self._aim_settled),
            "gnss_stale": self.gnss_stale(t),
            "camera_only_gate": bool(self.cfg.CAMERA_ONLY_GATE),
        }


# ==========================================================
#  MAIN
# ==========================================================
if __name__ == "__main__":
    print("Görevi çalıştırmak için:  python -m web.server ->  http://127.0.0.1:8001")

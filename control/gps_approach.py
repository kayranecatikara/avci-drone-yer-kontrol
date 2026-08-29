# -*- coding: utf-8 -*-
"""
control/gps_approach.py — GPS FAZI: İSTASYON TUTMA

AMAÇ: Hedefin kuyruğundaki bir noktaya (istasyon) oturmak ve orada KALARAK
kesintisiz görsel temas kurmak. Bu faz ÖLDÜRÜCÜ faz değildir; son yaklaşma
görsel fazın işidir. Dört işi vardır:
    1. bozuk GNSS'i temizle ve hedefin hızını kestir (`clean_target`)
    2. istasyona otur ve orada kal (`command`)
    3. burnu hedefe dönük tut ki kamera hedefi görsün
    4. görsel faza temiz devret (kapı `control/main.py`dedir, burada değil)

TERİMLER
  * İstasyon — hedefe göre SABİT göreli bir nokta: `STATION_RANGE_M` metre
    arkası, `STATION_RANGE_M * STATION_ALT_RATIO` metre altı.
  * İleri besleme (feedforward) — hatanın oluşmasını beklemeden hedefin
    kestirilen hızını doğrudan komuta eklemek.
  * Kalıcı gecikme hatası — saf P kontrolcü hareketli referansı izlerken
    dengeye `e = V/Kp`de oturur, yani HEP geride kalır. İleri beslemenin
    varlık sebebi budur (bkz. `GPSCfg.STATION_FEEDFWD`).

⛔ Bu dosyanın çıktısı YALNIZ GPS fazında komuta girer. Görsel temas
   kurulduktan sonra hedefe ait hiçbir GNSS türevi komuta giremez (yarışma
   kuralı). Görsel/çarpma fazlarında yalnızca `clean_target()` çağrılır ve
   dönen değer HİÇBİR KOMUTA GİRMEZ — amacı filtreyi sıcak tutmaktır.
"""
import math

from control.common import (CM_TO_M, ConverterCfg, Telemetry, VelocityToStick, clamp, wrap_deg)
from filter.gnss_filtre_v2 import GNSSFilterV2


class GPSCfg:
    """GPS fazının ayarları: istasyon geometrisi, kazançlar, zarf ve filtre.

    Dikey/yaw tavanları burada TANIMLANMAZ, `ConverterCfg`ten okunur —
    zarf tek kaynakta durur (üçe kopyalandıkları sürümde değerler kaymıştı).
    """

    # --- DÖNGÜ ---
    LOOP_HZ = 50.0      # Hz; koşturucunun (web/server.py) nominal tik hızı
    DT = 1.0 / LOOP_HZ  # s; bir tikin nominal süresi (döngü uykusu ve ilk tik için)

    # --- İSTASYON (GPS fazının nişan aldığı nokta) ---
    # ⭐ GEOMETRİ ÖLÇÜLDÜ (24 uçuş, dönüşümlü A/B). Karşılaştırılan kollar ve
    #   ortaya çıkan gerçek tespit oranları:
    #       15 m / 0.45 -> %66.9   |   8 m / 0.45 -> %76.0
    #       8 m / 0.75  -> %88.8   <- SEÇİLDİ (yanlış-pozitif de en düşük: %3.7)
    #   İki düğme BAĞIMSIZDIR: MENZİL yalnız kutu boyutunu, ORAN yalnız gök
    #   payını değiştirir. Oran büyüdükçe hedefin arka planı gökyüzü olur ve
    #   dedektör onu daha temiz ayırır.
    STATION_RANGE_M = 8.0     # m; hedefin TAM ARKASINDA durulacak mesafe
    STATION_ALT_RATIO = 0.75  # oran (birimsiz); alt ofset = STATION_RANGE_M * bu değer.
                              # Yükseliş açısı atan(oran) olur, yani menzilden BAĞIMSIZDIR.
                              # 0 verilirse yerine sabit STATION_ALT_M kullanılır.
    STATION_ALT_M = 15.0      # m; YALNIZ STATION_ALT_RATIO = 0 iken geçerli sabit alt ofset
    STATION_KP = 0.9          # 1/s; yatay konum hatasını (m) hız komutuna (m/s) çeviren P kazancı
    STATION_KP_Z = 0.9        # 1/s; dikey konum hatasını (m) dikey hıza (m/s) çeviren P kazancı
    STATION_FEEDFWD = True    # hedefin kestirilen hızı komuta doğrudan eklensin mi?
                              # ⭐ ŞART: saf P kontrolcü hareketli hedefi ASLA
                              #   yakalayamaz, denge e = V/Kp'de kurulur (Kp=0.9,
                              #   V=18 m/s -> 20 m KALICI hata). İleri beslemesiz
                              #   sürümde menzil 100-255 m salındı ve kapanma hızı
                              #   medyan -3.78 m/s idi, yani araç UZAKLAŞIYORDU.

    # --- ZARF (tek kaynak: ConverterCfg; buraya sayı YAZILMAZ) ---
    VZ_MAX_CLIMB = ConverterCfg.VZ_MAX_CLIMB      # m/s; azami tırmanma hızı
    VZ_MAX_DESCENT = ConverterCfg.VZ_MAX_DESCENT  # m/s; azami alçalma hızı (asimetrik, çok daha küçük)
    YAW_RATE_MAX = ConverterCfg.YAW_RATE_MAX_DEG  # derece/s; azami dönüş hızı

    # --- POLİTİKA ---
    V_MAX = 33.0  # m/s; istasyona giderken izin verilen azami YATAY hız
    KP_YAW = 3.0  # 1/s; yaw hatasını (derece) dönüş hızına (derece/s) çeviren P kazancı

    # --- HEDEF YÖNÜ ---
    HEADING_MIN_SPEED = 1.0  # m/s; hedefin kestirilen yatay hızı bunun altındaysa
                             # gidiş yönü GÜVENİLMEZ sayılır ve istasyon hedefin
                             # arkasına değil doğrudan üstüne/altına kurulur
                             # (durgun hedefte atan2 gürültüden yön üretir).

    # --- GNSS FİLTRESİ ---
    DELAY_S = 1.0  # s; ham GNSS'in ölçülen gecikmesi (~1.13 s). Filtre çıkışını
                   # bu kadar İLERİ taşır; kapatılmazsa 18 m/s'de ~20 m sabit hata olur.
    FILTER_EVERY_TICK = True  # filtre her tikte mi beslensin (50 Hz), yalnız yeni
                              # pakette mi (~5 Hz)? ⭐ True olmalı: filtre paket
                              # tekrarını kendi tanır ve arada ölü-hesapla ilerler.
                              # False iken hedef konumu 50 Hz'lik yasaya ~5 Hz'lik
                              # MERDİVEN olarak girer.

# ==========================================================
#  ISTASYON YASASI
# ==========================================================
def station_point(target_p, target_heading_deg, cfg=GPSCfg):
    """Hedefin kuyruğundaki istasyon noktasını hesaplar.

    target_p            : (x, y, z) m — TEMİZ (filtrelenmiş) hedef konumu
    target_heading_deg  : derece — hedefin gidiş yönü; None ise arkaya kaydırma
                          yapılmaz, yalnız alt ofset uygulanır
    -> (x, y, z) m, Unreal dünya ekseni
    """
    hx, hy, hz = target_p
    if cfg.STATION_ALT_RATIO > 0:
        z = hz - cfg.STATION_RANGE_M * cfg.STATION_ALT_RATIO
    else:
        z = hz - cfg.STATION_ALT_M
    if target_heading_deg is None:
        return hx, hy, z
    r = math.radians(target_heading_deg)
    return (hx - math.cos(r) * cfg.STATION_RANGE_M, hy - math.sin(r) * cfg.STATION_RANGE_M, z)


def command(drone_p, drone_yaw_deg, target_p, target_v, target_heading_deg, cfg=GPSCfg):
    """İSTASYON TUTMA YASASI — hız setpoint'i üretir (çubuk DEĞİL).

    GİRDİ
      drone_p            : (x, y, z) m — kendi konumumuz
      drone_yaw_deg      : derece — kendi burun yönümüz
      target_p           : (x, y, z) m — TEMİZ hedef konumu (filtre çıkışı)
      target_v           : (vx, vy, vz) m/s — TEMİZ hedef hızı (ileri beslenen terim)
      target_heading_deg : derece | None — hedefin gidiş yönü
    ÇIKTI
      ((vx, vy), vz_ned, yaw_rate_deg_s, diag)
        vx, vy         : m/s, Unreal dünya yatay düzlemi
        vz_ned         : m/s, POZİTİF = AŞAĞI (çevirici tersine çevirir)
        yaw_rate_deg_s : derece/s, istenen dönüş hızı
        diag           : yalnız telemetri/kapı verisi; komuta girmez

    YASA:  v = v_hedef (ileri besleme) + Kp * (istasyon - konum)
      İlk terim hedefle AYNI hızda uçmayı sağlar (kalıcı hatayı sıfırlar),
      ikinci terim istasyon noktasına oturtur.

    BURUN: her zaman hedefe dönük tutulur — kamera gövdeye sabit olduğu için
    hedefin kadrajda kalmasının tek yolu budur.
    """
    sx, sy, sz = station_point(target_p, target_heading_deg, cfg)
    ex = sx - drone_p[0]
    ey = sy - drone_p[1]
    ez = sz - drone_p[2]

    ff_x, ff_y, ff_z = (target_v if cfg.STATION_FEEDFWD else (0.0, 0.0, 0.0))

    vx = ff_x + cfg.STATION_KP * ex
    vy = ff_y + cfg.STATION_KP * ey
    n = math.hypot(vx, vy)
    if n > cfg.V_MAX:
        vx *= cfg.V_MAX / n
        vy *= cfg.V_MAX / n

    vz_up = ff_z + cfg.STATION_KP_Z * ez
    vz_up = clamp(vz_up, -cfg.VZ_MAX_DESCENT, cfg.VZ_MAX_CLIMB)

    bearing = math.degrees(math.atan2(target_p[1] - drone_p[1], target_p[0] - drone_p[0]))
    yaw_err = wrap_deg(bearing - drone_yaw_deg)
    yaw_rate = clamp(cfg.KP_YAW * yaw_err, -cfg.YAW_RATE_MAX, cfg.YAW_RATE_MAX)

    diag = {
        "station_x": sx, "station_y": sy, "station_z": sz,
        "station_err_m": math.sqrt(ex * ex + ey * ey + ez * ez),
        "station_err_horiz": math.hypot(ex, ey),
        "station_err_vert": ez,
        "target_range_m": math.dist(drone_p, target_p),
        "target_speed": math.hypot(target_v[0], target_v[1]),
        "target_heading": target_heading_deg,
        "yaw_err": yaw_err,
        "v_cmd": math.hypot(vx, vy),
    }
    return (vx, vy), -vz_up, yaw_rate, diag


# ==========================================================
#  GPS FAZI SÜRÜCÜSÜ
# ==========================================================
class GPSTracker:
    """GPS fazının sürücüsü: bozuk GNSS -> temiz hedef -> istasyon tutma.

    `command()` yasasını GNSS filtresi, telemetri ve komut kapısıyla
    birleştirir. Faz kararı VERMEZ; `phase` özniteliği yalnızca "STATION"
    üretir (kalkış bu sınıftan çıkarıldı) ve `step()` aracın ZATEN HAVADA
    olduğunu varsayar.

    ⚠ `self.filter` bir ÖZNİTELİKTİR, `filter` builtin'ini gölgelemez.
    """

    def __init__(self, drone, sender, cfg=GPSCfg):
        """drone: SDK; sender: TEK komut kapısı; cfg: GPS fazı ayarları."""
        self.cfg = cfg
        self.drone = drone
        self.tlm = Telemetry(drone)
        self.sender = sender
        self.conv = VelocityToStick()
        self.filter = None
        self.reset()

    def _filter_lost(self):
        """Filtre kilidini GERCEKTEN kaybetti mi? (sıcak taşımanın tek istisnası)

        Sıcak filtreyi görevler arası taşımak doğru olanıdır — ama oyun yeniden
        başlatılıp hedef BAŞKA YERDE doğduysa filtre eski kilidinde kalır ve
        kaçış mekanizması (P şişirme) devreye girene kadar hedefi yüzlerce
        metre yanlış gösterir. Ölçüldü (hedef 500 m ışınlandı, n=4): yeniden
        kilitlenme **medyan 2.60 s, max 2.80 s**. Soğuk kurulum ise ~0.40 s'de
        çıkış verir. Yani filtre kilidini kaybetmişken onu taşımak, ısınma
        transientinden DAHA kötüdür.

        Ölçüt filtrenin kendi teşhisidir: `ret` = üst üste kapı reddi sayacı.
        Tek bir jammer sıçraması 1-2 ret üretir ve bu SAĞLIKLI çalışmadır;
        eşiğin yarısını geçmişse artık rejim değişmiş demektir.

        ⚠ ŞÜPHEDE KALIRSA FİLTREYİ KORU. Soğuk kurulum bilinen bir bozulmadır
          (ısınma transienti); kilidini kaybetmiş filtre ise nadir bir durum.
          Bu yüzden teşhis okunamazsa `False` döner.
        """
        try:
            d = self.filter.diag()
            if not d.get("started"):
                return True  # zaten ısınmamış -> taşımanın anlamı yok
            return d.get("ret", 0) >= max(1, int(d.get("escape_thresh", 12)) // 2)
        except Exception:
            return False

    def reset(self, cold_filter=False):
        """Yeni görev için GÖREV KAPSAMLI durumu sıfırlar.

        ⭐ FİLTRE KORUNUR (`cold_filter=True` denmedikçe) — ve bu, görevi
          durdurup yeniden başlatmanın en kritik ayrıntısıdır.

          `web/server.py :: control_loop` görev PASİFKEN de her tik
          `clean_target()` çağırır; tek amacı filtrenin ISINMIŞ kalmasıdır.
          Filtreyi burada yeniden kurmak o ısınmayı **tam işe yarayacağı anda
          çöpe atardı** ve o satır fiilen ölü kod olurdu.

        ⛔ NEDEN ÖNEMLİ: ısınma transienti ilk ~4 saniyededir (pencere medyanı
          23.6 m, max 52 m). İLK görevde bunu KALKIŞ maskeler (kalkış ~4 s
          sürer ve o sırada yatay komut üretilmez). Ama görev havadayken
          yeniden başlatılırsa kalkış kapısının 2. kolu (hedefin irtifasına
          TAKEOFF_TARGET_GAP_M kadar yaklaşıldı) daha ilk tikte açılır —
          kalkış saniyenin onda birinde biter ve **maske kalkar**. O zaman
          transient doğrudan istasyon fazına, yani yatay komutun ÜRETİLDİĞİ
          yere düşer: hedef 20-50 m yanlış yerde görünür, yasa büyük bir hız
          komutu üretir ve araç sapıtır. Sıcak filtre bu zinciri kökünden
          keser.

          Gerçekten soğuk başlangıç isterseniz (ör. hedef değişti):
          `brain.reset(cold_filter=True)`.
        """
        if cold_filter or self.filter is None or self._filter_lost():
            self.filter = GNSSFilterV2(lead_s=self.cfg.DELAY_S)

        self.last_raw = None             # SDK'nın döndürdüğü ham GNSS demeti; yeni
                                         # paket geldi mi anlamak için karşılaştırılır
        self.target_p = None             # (x, y, z) m; TEMİZ hedef konumu | None (filtre ısınmadı)
        self.target_v = (0.0, 0.0, 0.0)  # (vx, vy, vz) m/s; TEMİZ hedef hızı (ileri beslenen terim)
        self.target_heading = None       # derece; hedefin gidiş yönü | None (hedef çok yavaş)
        self._fresh = False              # son okumada YENİ paket geldi mi?

        self.phase = "STATION"   # bu sınıfın ürettiği tek faz etiketi (arayüz için)
        self.range_h = None      # m; hedefe olan 3B (eğik) menzil — devir kapısının girdisi
        self.station_err = None  # m; istasyon noktasına olan 3B hata — devir kapısının girdisi
        self.diag = {}           # son tikin telemetrisi

    # ----------------------------------------------------------------
    #  BOZUK GNSS -> TEMIZ HEDEF (konum + hız + yön)
    # ----------------------------------------------------------------
    def clean_target(self):
        """Ham GNSS paketini filtreye verir; TEMİZ hedef konumunu döndürür.

        -> (x, y, z) m | None (filtre henüz ısınmadı)

        Yan etki olarak `target_v` (m/s) ve `target_heading` (derece) da
        tazelenir; istasyon yasası ikisini de kullanır.

        ⚠ BİRİM SINIRI BURADA AÇIKÇA GEÇİLİR: filtre cm alanında çalışır,
          çıktısı burada metreye çevrilir. `control/` içinde `*0.01`in
          `Telemetry` dışında görüldüğü TEK yer burasıdır.

        ⭐ GÖRSEL VE ÇARPMA FAZLARINDA DA, HATTA GÖREV PASİFKEN DE ÇAĞRILIR —
          ama dönen değer o fazlarda HİÇBİR KOMUTA GİRMEZ. Tek amaç filtrenin
          ISINMIŞ kalmasıdır: faz GPS'e geri düşerse ya da görev yeniden
          başlatılırsa soğuk filtreyle açılmasın. (Soğuk filtrenin bedeli
          ölçüldü: istasyon fazının ilk 1.5 s'inde hedef konum hatası medyan
          39.2 m, korunduğunda 2.5 m.)
        """
        raw = self.tlm.target_raw_cm()
        self._fresh = (raw != self.last_raw)
        if not self._fresh and not self.cfg.FILTER_EVERY_TICK:
            return self.target_p
        self.last_raw = raw
        clean_cm = self.filter.update(raw[0], raw[1], raw[2])
        if clean_cm is None:
            return self.target_p

        self.target_p = (clean_cm[0] * CM_TO_M, clean_cm[1] * CM_TO_M, clean_cm[2] * CM_TO_M)
        gs = self.filter.guidance_state()
        if gs is not None:
            v = gs["vel"]
            self.target_v = (v[0] * CM_TO_M, v[1] * CM_TO_M, v[2] * CM_TO_M)
            speed_horiz = math.hypot(self.target_v[0], self.target_v[1])
            if speed_horiz > self.cfg.HEADING_MIN_SPEED:
                self.target_heading = math.degrees(math.atan2(self.target_v[1], self.target_v[0]))
        return self.target_p

    # ================================================================
    #  KONTROL ADIMI
    # ================================================================
    def step(self):
        """Bir GPS tiki: temiz hedefi al, istasyon komutunu üret, çubuğa yaz.

        Hedef henüz yoksa (filtre ısınmadı) komut üretmez, `loiter()` ile
        irtifayı tutar. Kapıların okuduğu `range_h` ve `station_err` bu
        adımda tazelenir.
        """
        dp = self.tlm.position_m()
        _roll, _pitch, yaw = self.tlm.orientation_deg()
        v_meas = self.tlm.velocity_ms()
        hp = self.clean_target()

        # ---- Hedef Yok ----
        if hp is None:
            self.range_h = None
            self.station_err = None
            self.sender.loiter()
            self.diag = {"state": "NO_TARGET"}
            return

        # ---- İstasyon tutma ----
        (vx, vy), vz_ned, yaw_rate, diag = command(dp, yaw, hp, self.target_v, self.target_heading, self.cfg)
        thr, pitch, roll, yaw_c = self.conv.convert((vx, vy, vz_ned), v_meas, math.radians(yaw), yaw_rate)
        self.sender.send(thr, pitch, roll, yaw_c)

        self.range_h = diag["target_range_m"] 
        self.station_err = diag["station_err_m"]
        diag.update(self.conv.diag)
        diag["state"] = "STATION"
        diag["filter"] = self.filter.diag()
        self.diag = diag

    def status(self):
        """Son tikin telemetrisi (yalnız gösterge; komuta girmez)."""
        return dict(self.diag)

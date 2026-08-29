# -*- coding: utf-8 -*-
"""
control/common.py — BİRİM SINIRI + HIZ->ÇUBUK ÇEVİRİCİSİ + TEK KOMUT KAPISI

Bu dosya güdüm YASASI içermez. Yasaların (takeoff / gps_approach /
visual_tracking / spike) ürettiği hız setpoint'ini aracın gerçekten kabul
ettiği şeye — kumanda çubuğuna — çeviren ORTAK ALT KATMANDIR. Üç işi vardır:

    Telemetry       SDK'nın cm/derece çıktısını m, m/s, dereceye çevirir
                    (BİRİM SINIRI: `control/` içinde başka yerde *0.01 olmaz)
    VelocityToStick m/s cinsinden hız setpoint'ini çubuğa çevirir; aracın
                    ÖLÇÜLMÜŞ zarfını (asimetrik dikey, iki kollu throttle
                    haritası, ivme tavanı) burası bilir, yasalar bilmez
    CommandSender   oyuna giden TEK komut çıkışı; eğim sınırı ve [-1,+1]
                    kırpması burada, tek yerde uygulanır

Katman ayrımı kasıtlıdır: yasaya dokunmadan çevirici değiştirilebilir, tersi
de doğrudur. DoW SDK'sı yalnız çubuk (-1..+1) kabul ettiği ve arada bir
hız/konum kontrolcüsü BULUNMADIĞI için bu ara katman zorunludur.
"""
import math

CM_TO_M = 0.01    # çarpan; SDK'nın verdiği konumu cm -> m yapar
CMS_TO_MS = 0.01  # çarpan; SDK'nın verdiği hızı cm/s -> m/s yapar

# ==========================================================
#  SKALER YARDIMCILAR
# ==========================================================
def clamp(x, lo, hi):
    """x'i [lo, hi] aralığına kırpar; aralıktaysa olduğu gibi döndürür."""
    return lo if x < lo else hi if x > hi else x


def wrap_deg(a):
    """Açıyı (derece) -180..+180 aralığına sarar.

    Yaw hatası hesaplarken şarttır: 350° ile 10° arasındaki fark sarmasız
    hesaplanırsa +340° çıkar ve araç kısa yol yerine uzun yoldan döner.
    """
    return (a + 180.0) % 360.0 - 180.0


def rate_limit(target, prev, max_delta):
    """Eğim sınırı: `prev`ten `target`a en çok `max_delta` kadar yaklaşır.

    target, prev : çubuk konumu (-1..+1, birimsiz)
    max_delta    : birim/tik; tek tikte izin verilen azami değişim
    -> bir sonraki çubuk değeri
    """
    return prev + clamp(target - prev, -max_delta, max_delta)


def world_to_body(ex, ey, yaw_rad, y_sign=None):
    """Dünya yatay düzlemindeki bir vektörü gövde çerçevesine çevirir.

    ex, ey   : dünya ekseninde vektör (hız m/s ya da konum hatası m — dönüşüm
               birimsizdir, hangi birim girerse o çıkar)
    yaw_rad  : aracın burun yönü (radyan)
    y_sign   : yanal eksen işareti; None ise `ConverterCfg.Y_SIGN` kullanılır
    -> (ileri, sağ) aynı birimde
    """
    if y_sign is None:
        y_sign = ConverterCfg.Y_SIGN
    c, s = math.cos(yaw_rad), math.sin(yaw_rad)
    fwd = ex * c + ey * s
    right = y_sign * (-ex * s + ey * c)
    return fwd, right


# ==========================================================
#  BİRİM SINIRI — SDK (cm, derece)  ->  güdüm (m, m/s, derece)
# ==========================================================
class Telemetry:
    """SDK telemetrisini güdümün birimlerine çeviren ince sarmalayıcı.

    ⚠ BİRİM DÖNÜŞÜMÜ TEK YERDE. `control/` içinde bu sınıfın DIŞINDA `*0.01`
      görülmemelidir; dönüşüm dağılırsa "iki kez çevirme" ya da "hiç
      çevirmeme" hatası sessizce oluşur ve 100 kat yanlış bir konum, yasaya
      doğrudan tam çubuk komutu olarak girer. Tek istisna
      `gps_approach.clean_target`'tir: GNSS filtresi cm alanında çalışır ve
      sınır orada AÇIKÇA geçilir.
    """

    def __init__(self, drone):
        """drone: sdk.drone_sdk modülü (ya da aynı arayüzü sunan bir nesne)."""
        self.drone = drone

    def connected(self):
        """Oyunla bağlantı ayakta mı? -> True/False"""
        return self.drone.is_connected()

    def position_m(self):
        """Kendi konumumuz — (x, y, z) metre, Unreal dünya ekseni."""
        x, y, z = self.drone.get_drone_location()
        return x * CM_TO_M, y * CM_TO_M, z * CM_TO_M

    def orientation_deg(self):
        """Kendi yönelimimiz — (roll, pitch, yaw) derece."""
        r, p, y = self.drone.get_drone_rotation()
        return float(r), float(p), float(y)

    def velocity_ms(self):
        """Kendi hız vektörümüz — (vx, vy, vz) m/s, dünya ekseni.

        Telemetri okunamazsa (0, 0, 0) döner: çevirici hız hatasını "ölçülen
        hız sıfır" varsayımıyla hesaplar, yani komut üretmeyi sürdürür.
        """
        try:
            vx, vy, vz = self.drone.get_telemetry()["drone"]["velocity"]
        except Exception:
            return 0.0, 0.0, 0.0
        return vx * CMS_TO_MS, vy * CMS_TO_MS, vz * CMS_TO_MS

    def altitude_m(self):
        """Aracın SDK'dan okunan irtifası (m)."""
        return self.drone.get_drone_altitude() * CM_TO_M

    # -- hedef (bozuk GNSS) --------------------------------------------
    def target_raw_cm(self):
        """Hedefin HAM (jammer'la bozulmuş) GNSS konumu — (x, y, z) SANTİMETRE.

        ⚠ BİLEREK ÇEVRİLMEZ. Bu değerin tek tüketicisi GNSS filtresidir ve o
          filtre cm alanında çalışır (kapı eşikleri, ölçüm ve süreç
          kovaryansları cm cinsindendir). Çevirip geri çarpmak bir şey
          kazandırmaz, karıştırma riski getirir.
        """
        return self.drone.get_target_location()


# ==========================================================
#  HIZ -> KUMANDA ÇUBUĞU ÇEVİRİCİSİ
# ==========================================================
class ConverterCfg:
    """Aracın ÖLÇÜLMÜŞ hareket zarfı — hız setpoint'i ile çubuk arasındaki eşleme.

    Aşağıdaki sabitler uçuş kaydından ÖLÇÜLMÜŞTÜR; "böyle iyi geldi" diye
    seçilmiş ayar düğmeleri değildir. Her biri fiziksel bir büyüklüğün
    değeridir ve o büyüklük yeniden ölçülmedikçe değişmez:

      yatay hız tavanı ....... 34.6 m/s
      tırmanma tavanı ........ +33.51 m/s
      alçalma tavanı ......... -6.95 m/s      (tırmanmanın 4.8 KATI asimetrik)
      yatay ivme ............. 34-39 m/s²     (tam çubukta)
      yatış zaman sabiti ..... 0.211 s        (çubuk -> gerçek yatış)
      ölü zaman .............. 46 ms          (komut -> tepki)
      yaw tavanı ............. 214 derece/s   (aracın yapabildiği; biz 120 kullanırız)

    ⭐ ZARF TEK KAYNAKTA. `VZ_MAX_CLIMB`, `VZ_MAX_DESCENT` ve
      `YAW_RATE_MAX_DEG` YALNIZ burada tanımlıdır; `GPSCfg`, `VisualCfg` ve
      `SpikeCfg` bu üç adı buradan OKUR. Üçe kopyalandıkları sürümde tırmanma
      tavanı 33.51 / 33.5 / 33.5 diye zaten kaymıştı.
    """

    # --- EKSEN İŞARETLERİ (birimsiz; yalnız +1.0 ya da -1.0) ---
    Z_SIGN = -1.0  # dikey eksen çevirisi: yasalar NED verir (z aşağı +),
                   # throttle haritası ise YUKARI pozitif ister
    Y_SIGN = -1.0  # yanal eksen çevirisi: Unreal SOL ELLİDİR. +1 yazılırsa
                   # yanal komut TERS yöne gider, hata büyür, roll ±1'e
                   # çakılır ve araç hedefe gitmek yerine daire çizer.

    # --- YATAY İÇ DÖNGÜ (hız hatası -> ivme) ---
    K_V = 1.5  # 1/s; hız hatasını (m/s) istenen ivmeye (m/s²) çeviren P kazancı

    # --- İVME -> ÇUBUK ---
    MODEL = "direct"     # eşleme biçimi: "direct" = a/A_MAX (aktif),
                         # "angle" = atan2(a, g) açısını MAX_BANK_DEG'e oranlar
    A_MAX = 34.0         # m/s²; tam çubuğun (|pitch| = 1) ürettiği yatay ivme
    MAX_BANK_DEG = 60.0  # derece; YALNIZ MODEL="angle" iken tam çubuğun yatış açısı

    # --- DİKEY: ÖLÇÜLMÜŞ THROTTLE HARİTASI (iki kollu, parçalı doğrusal) ---
    POS_SLOPE = 32.64      # (m/s)/birim; tırmanma kolunun eğimi: vz = 32.64*thr + 0.869  (thr > 0)
    POS_INTERCEPT = 0.869  # m/s; tırmanma kolunun sabit terimi — thr = 0'da bile 0.88 m/s TIRMANIR
    NEG_SLOPE = 16.78      # (m/s)/birim; alçalma kolunun eğimi: vz = 16.78*thr + 9.835  (thr <= HOVER_THR)
    NEG_INTERCEPT = 9.835  # m/s; alçalma kolunun sabit terimi
    HOVER_THR = -0.586     # birim; vz = 0 veren NÖTR throttle (orada ölçülen vz = -0.235 m/s)
    HOLD_BAND = 0.05       # m/s; istenen |vz| bunun altındaysa "irtifayı tut" sayılır -> HOVER_THR gönderilir
    VZ_MAX_CLIMB = 33.51   # m/s; azami tırmanma hızı (tam throttle)
    VZ_MAX_DESCENT = 6.95  # m/s; azami alçalma hızı — tırmanmanın 4.8 KATI ASİMETRİK,
                           # yani inmek tırmanmaktan çok daha yavaştır

    # --- YAW ---
    YAW_RATE_MAX_DEG = 120.0  # derece/s; tam yaw çubuğunun (|yaw| = 1) karşılığı.
                              # Araç 214 yapabiliyor ama 120'de TUTULUYOR: hızlı
                              # yaw görüntüyü bulandırıp dedektörü kırar.

    # ⛔ THROTTLE MAYINI — "eksi binde bir" irtifa TUTMAZ.
    #   Ölçüldü: thr = -0.001 -> +9.31 m/s TIRMANMA, thr = 0.000 -> +0.88 m/s.
    #   Yani sıfır civarı throttle nötr DEĞİLDİR; nötr nokta `HOVER_THR`tir
    #   (-0.586). Eski koddaki "kaçak tırmanma"nın kök nedeni tam olarak buydu;
    #   `CommandSender.loiter()` bu yüzden 0 değil `HOVER_THR` gönderir.


class VelocityToStick:
    """Hız setpoint'ini (m/s) kumanda çubuğuna (-1..+1) çeviren ara katman.

    Yasalar "şu hızda uç" der; araç ise yalnız çubuk kabul eder. Aradaki
    eşleme aracın ÖLÇÜLMÜŞ zarfıdır ve buradadır — yasaların içinde değil.
    Böylece zarf yeniden ölçüldüğünde tek bir dosya değişir.
    """

    def __init__(self, cfg=ConverterCfg):
        """cfg: kullanılacak zarf sabitleri (varsayılan `ConverterCfg`)."""
        self.cfg = cfg
        self.diag = {}  # son çevrimin mekanizma sütunu (yalnız telemetri)

    # ---------------- İvme -> Çubuk ----------------
    def _accel_stick(self, a):
        """İstenen yatay ivmeyi (m/s²) çubuk konumuna (-1..+1) çevirir."""
        c = self.cfg
        if c.MODEL == "angle":
            return clamp(math.degrees(math.atan2(a, 9.81)) / c.MAX_BANK_DEG, -1.0, 1.0)
        return clamp(a / c.A_MAX, -1.0, 1.0)

    def vz_stick(self, vz_up):
        """İstenen dikey hızı throttle'a çevirir — ölçülmüş haritanın TERSİ.

        vz_up : m/s, POZİTİF = YUKARI (NED DEĞİL)
        -> throttle (-1..+1)

        |vz| < HOLD_BAND ise nötr `HOVER_THR`, yukarı isteniyorsa tırmanma
        kolu, aşağı isteniyorsa alçalma kolu kullanılır.
        """
        c = self.cfg
        if abs(vz_up) < c.HOLD_BAND:
            return c.HOVER_THR
        if vz_up > 0.0:
            return clamp((vz_up - c.POS_INTERCEPT) / c.POS_SLOPE, 0.0, 1.0)
        return clamp((vz_up - c.NEG_INTERCEPT) / c.NEG_SLOPE, -1.0, c.HOVER_THR)

    # ---------------- Ana ----------------
    def convert(self, v_des, v_meas, yaw_rad, yaw_rate_des_deg=0.0):
        """Hız setpoint'i + ölçülen hız -> dört çubuk kanalı.

        v_des            : (vx, vy, vz_ned) m/s — istenen hız, dünya ekseni;
                           vz POZİTİF = AŞAĞI (NED)
        v_meas           : (vx, vy, vz) m/s — ölçülen kendi hızımız, dünya ekseni
        yaw_rad          : kendi burun yönümüz (radyan)
        yaw_rate_des_deg : derece/s; istenen dönüş hızı
        -> (thr, pitch, roll, yaw) — dördü de -1..+1 birimsiz çubuk konumu

        Yatay kanal KAPALI ÇEVRİMDİR (hız hatası -> ivme -> çubuk); dikey ve
        yaw kanalları ölçülmüş haritaların doğrudan tersidir.
        """
        c = self.cfg
        vx_des, vy_des, vz_des_ned = v_des
        vx_meas, vy_meas, _vz_meas = v_meas

        # [1] iki hızı da gövde çerçevesine al (hata gövdede hesaplanır)
        fwd_des, right_des = world_to_body(vx_des, vy_des, yaw_rad, c.Y_SIGN)
        fwd_meas, right_meas = world_to_body(vx_meas, vy_meas, yaw_rad, c.Y_SIGN)

        # [2] hız hatası -> istenen ivme
        a_fwd = c.K_V * (fwd_des - fwd_meas)
        a_right = c.K_V * (right_des - right_meas)

        # [3] ivme -> çubuk
        pitch = self._accel_stick(a_fwd)
        roll = self._accel_stick(a_right)

        # [4] dikey
        vz_up = c.Z_SIGN * vz_des_ned
        thr = self.vz_stick(vz_up)

        # [5] yaw: istenen dönüş hızını tam-çubuk karşılığına oranla
        yaw = clamp(yaw_rate_des_deg / c.YAW_RATE_MAX_DEG, -1.0, 1.0)

        # Mekanizma sütunu — yalnız telemetri/tanı, hiçbir komuta girmez.
        # `conv_sat` özellikle önemlidir: doymuş bir kanal, o tikte yasanın
        # istediğinin ARACIN VEREBİLDİĞİNDEN fazla olduğunu söyler.
        self.diag = {
            "conv_fwd_err": fwd_des - fwd_meas,
            "conv_right_err": right_des - right_meas,
            "conv_a_fwd": a_fwd,
            "conv_a_right": a_right,
            "conv_vz_up": vz_up,
            "conv_sat": int(abs(pitch) >= 1.0 or abs(roll) >= 1.0 or abs(thr) >= 1.0),
        }
        return thr, pitch, roll, yaw


# ==========================================================
#  TEK KOMUT KAPISI
# ==========================================================
class CommandSender:
    """Oyuna giden TEK komut kapısı (throttle/pitch/roll/yaw + arm).

    Bütün fazlar komutu buradan gönderir. Tek kapı olması iki şeyi garanti
    eder: (1) eğim sınırı ve [-1,+1] kırpması her komuta AYNI biçimde
    uygulanır, (2) `mission_stop()` tek bir `cut()` ile gerçekten susturur.
    """

    # ⚠ EĞİM SINIRI TEK YERDE. Çevirici de sınırlarsa iki sönümleme üst üste
    #   biner ve araç gereksiz hantallaşır; aracın yatışı zaten 0.211 s'lik
    #   zaman sabitiyle kendiliğinden yumuşuyor.
    MAX_DELTA = 0.15  # birim/tik; bir kanalın tek tikte değişebileceği azami miktar

    def __init__(self, drone):
        """drone: sdk.drone_sdk modülü (ya da aynı arayüzü sunan bir nesne)."""
        self.drone = drone
        self.prev = {"thr": 0.0, "pitch": 0.0, "roll": 0.0, "yaw": 0.0}

    def reset(self):
        """Eğim sınırının referansını sıfırlar (yeni görev başında)."""
        self.prev = {"thr": 0.0, "pitch": 0.0, "roll": 0.0, "yaw": 0.0}

    def send(self, thr, pitch, roll, yaw):
        """Komutu EĞİM SINIRINDAN geçirip gönderir — normal yol budur."""
        d = self.MAX_DELTA
        self.send_raw(rate_limit(thr, self.prev["thr"], d),
                      rate_limit(pitch, self.prev["pitch"], d),
                      rate_limit(roll, self.prev["roll"], d),
                      rate_limit(yaw, self.prev["yaw"], d))

    def send_raw(self, thr, pitch, roll, yaw):
        """Komutu eğim sınırı UYGULAMADAN gönderir (yalnız [-1,+1] kırpması).

        Tek adımda tam komut gereken yerler içindir; normal güdüm `send()`
        kullanır.
        """
        thr = clamp(float(thr), -1.0, 1.0)
        pitch = clamp(float(pitch), -1.0, 1.0)
        roll = clamp(float(roll), -1.0, 1.0)
        yaw = clamp(float(yaw), -1.0, 1.0)
        self.prev = {"thr": thr, "pitch": pitch, "roll": roll, "yaw": yaw}
        self.drone.set_control_surfaces(thr, pitch, roll, yaw, True)

    def loiter(self):
        """Hedef/veri yokken beklet: irtifayı tutar, yatay komut vermez.

        ⛔ Throttle SIFIR DEĞİL `HOVER_THR`tir. Sıfır throttle irtifa tutmaz,
          0.88 m/s tırmandırır (bkz. `ConverterCfg` — THROTTLE MAYINI).
        """
        self.send(ConverterCfg.HOVER_THR, 0.0, 0.0, 0.0)

    def cut(self):
        """Motorları keser ve disarm eder (görev durduruldu)."""
        self.prev = {"thr": 0.0, "pitch": 0.0, "roll": 0.0, "yaw": 0.0}
        self.drone.set_control_surfaces(0.0, 0.0, 0.0, 0.0, False)

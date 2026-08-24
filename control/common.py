# -*- coding: utf-8 -*-
"""
control/common.py — BIRIM SINIRI + HIZ->CUBUK CEVIRICISI + TEK KOMUT KAPISI.

Bu dosyada GUDUM YASASI YOKTUR. Uc isi vardir; ucu de "tek yerde yapilsin"
diye burada toplanmistir:

 1) BIRIM SINIRI (`Telemetri`) — SDK her seyi SANTIMETRE ve DERECE verir;
    guduum yasalari METRE ve m/s ile calisir. Bu donusumu yasanin icine
    serpistirmek "100 kat" hatalarinin klasik kaynagidir. Bu dosyanin
    disinda hicbir yerde `*0.01` ya da `/100` gorulmemelidir.

 2) HIZ -> CUBUK (`VelocityToStick`) — yasalar HIZ SETPOINT'i (m/s) uretir,
    oyun ise yalnizca kumanda cubugu (-1..+1) kabul eder. Arada ArduPilot'un
    AC_PosControl'u gibi bir katman YOKTUR; EKSIK KATMAN BUDUR. Sabitleri
    tahmin degil, DoW V5.0.0 uzerinde OLCULDU (kardes depo:
    drones_of_war_entegrasyon/dow/gudum/cevirici.py).

 3) TEK KOMUT KAPISI (`CommandSender`) — oyuna giden tek cikis. Egim sinirini
    (rate limit) burada uygular ve faz devrinde "onceki komut" surekliligini
    korur. Iki fazin AYRI gonderici tutmasi, devir aninda prev'in sifirdan
    baslamasina ve gorunur bir sarsintiya yol acardi.

⚠ EGIM SINIRI TEK YERDEDIR. Cevirici de kissaydi iki sonumleme ust uste biner
  ve tepki gecikirdi (aracin yatis zaman sabiti zaten 0.211 s). Cevirici HAM
  cubugu doner; kisma yalnizca CommandSender'de olur.
"""
import math

CM_TO_M = 0.01    # cm   -> m
CMS_TO_MS = 0.01  # cm/s -> m/s


# ==========================================================
#  SKALER YARDIMCILAR
# ==========================================================
def clamp(x, lo, hi):
    """Degeri [lo, hi] araligina alir."""
    return lo if x < lo else hi if x > hi else x


def wrap_deg(a):
    """Aciyi -180..+180 araligina alir (derece)."""
    return (a + 180.0) % 360.0 - 180.0


def rate_limit(target, prev, max_delta):
    """Tik basi degisimi +-max_delta ile sinirlar."""
    return prev + clamp(target - prev, -max_delta, max_delta)


def world_to_body(ex, ey, yaw_rad, y_sign=None):
    """Dunya yatay vektorunu GOVDE cercevesine cevirir -> (ileri, sag).

    ⛔ YANAL EKSEN ISARETI OLCULDU, TAHMIN DEGIL (kardes depo; 200 m'de 3 s
      saf komut, gercek yer degisimi):
        pitch +0.6 -> govde ileri +66.6 m, govde sag  -0.0   dogru
        roll  +0.6 -> govde ileri  +6.6 m, govde sag -66.8   TERS
      Unreal SOL-ELLIDIR (X ileri, Y sag, Z yukari). Sag-elli donusum yanal
      komutu TERS yone gonderir: hata kapanacagina buyur, roll -1'e cakilir
      ve arac hedefe gitmek yerine DAIRE cizer.
    """
    if y_sign is None:
        y_sign = ConverterCfg.Y_SIGN
    c, s = math.cos(yaw_rad), math.sin(yaw_rad)
    fwd = ex * c + ey * s
    right = y_sign * (-ex * s + ey * c)
    return fwd, right


# ==========================================================
#  BIRIM SINIRI — SDK (cm, derece)  ->  guduum (m, m/s, derece)
# ==========================================================
class Telemetry:
    """SDK'yi SI birimlerinde sunan ince sarmalayici.

    Aci birimi DERECE kalir (yasalar derece ile calisir; radyan yalnizca
    cevirici ve trigonometri icinde kullanilir).
    """

    def __init__(self, drone):
        self.drone = drone

    def connected(self):
        return self.drone.is_connected()

    def position_m(self):
        """(x, y, z) METRE — Unreal ekseni, Z YUKARI."""
        x, y, z = self.drone.get_drone_location()
        return x * CM_TO_M, y * CM_TO_M, z * CM_TO_M

    def orientation_deg(self):
        """(roll, pitch, yaw) DERECE. Olculdu: pitch NEGATIF = burun ASAGI."""
        r, p, y = self.drone.get_drone_rotation()
        return float(r), float(p), float(y)

    def velocity_ms(self):
        """(vx, vy, vz) m/s — Unreal ekseni. SDK telemetrisinin velocity alani."""
        try:
            vx, vy, vz = self.drone.get_telemetry()["drone"]["velocity"]
        except Exception:
            return 0.0, 0.0, 0.0
        return vx * CMS_TO_MS, vy * CMS_TO_MS, vz * CMS_TO_MS

    def altitude_m(self):
        """⚠ Su an CAGRILMIYOR (kalkis yukseklik farkindan hesaplaniyor) ama
        BILINCLI duruyor: birim siniri EKSIK kalirsa biri irtifayi baska bir
        dosyada `* 0.01` ile cevirir ve bu dosyanin tek isi olan kural bozulur."""
        return self.drone.get_drone_altitude() * CM_TO_M

    # -- hedef (BOZUK GNSS) --------------------------------------------
    def target_raw_cm(self):
        """(x, y, z) SANTIMETRE — jammer'li ham paket; DOGRUDAN filtreye girer.

        ⚠ `get_target_speed()` DAIMA 0 doner (kardes depoda 234587 ornekte
          dogrulandi) -> hedef hizi konumdan kestirilmek ZORUNDADIR; bunu
          filter/gnss_filtre_v2.py yapar (CT-EKF durumundan dogrudan).
        ⛔ Bu kanal YALNIZ gorsel temas YOKKEN guduume girebilir.
        """
        return self.drone.get_target_location()


# ==========================================================
#  HIZ -> KUMANDA CUBUGU CEVIRICISI  (sabitler OLCULDU)
# ==========================================================
class ConverterCfg:
    """DoW V5.0.0 uzerinde olculmus arac zarfi.

    OLCULEN ZARF
      yatay hiz tavani ....... 34.6 m/s    (belge 120 km/h = 33.33)
      tirmanma tavani ........ +33.51 m/s
      ALCALMA tavani ......... -6.95 m/s   ⚠ 4.8 KAT ASIMETRIK
      yatay ivme ............. 34-39 m/s²  (60 derece yatista beklenenin 2.3 kati)
      yatis zaman sabiti ..... 0.211 s
      olu zaman .............. 46 ms
      yaw tavani ............. 214 derece/s
    """

    # --- EKSEN ---
    Z_SIGN = -1.0  # NED vz (asagi+) -> Unreal yukari hizi
    Y_SIGN = -1.0  # olculdu: +roll araci SOLA goturuyor (bkz. world_to_body)

    # --- YATAY IC DONGU ---
    # a_istenen = K_V * (v_des - v_meas);  K_V birimi 1/s, tau = 1/K_V.
    # Yatis tau'su 0.211 s -> ic dongu ONDAN YAVAS olmali, yoksa iki dongu
    # birbirini kovalar ve salinir. K_V=1.5 -> tau=0.67 s = 3.2 kat yavas.
    K_V = 1.5

    # --- IVME -> CUBUK ---
    # "dogru": oyun ivmeyi dogrudan uyguluyor. Zarf olcumu 60 derece yatista
    # 34-39 m/s² buldu; klasik aci modeli (a = g*tan(phi)) 17.0 ongorur -> elendi.
    MODEL = "direct"
    A_MAX = 34.0         # m/s²; tam cubugun ivmesi
    MAX_BANK_DEG = 60.0  # yalnizca "aci" modeli icin (kiyas amacli durur)

    # --- DIKEY: OLCULMUS IKI KOLLU TERS MODEL ---
    # throttle bir HIZ komutudur (ivme kademesi YOK) ama esleme IKI KOLLU ve
    # tam sifirda SUREKSIZ. Olcum (her nokta 5-6 s kararli hal, n=26):
    #
    #   thr  +1.00 +0.75 +0.50 +0.25 +0.10 +0.05 +0.01 | 0.00 | -0.001 -0.10 -0.60 -1.00
    #   vz   33.51 25.04 16.80  8.79  4.06  2.47  1.20 | 0.88 |  9.31   7.93 -0.24 -6.95
    #
    # ⛔⛔ MAYIN: thr = -0.001 -> +9.31 m/s TIRMANMA; thr = 0.000 -> +0.88.
    #    Yani "eksi binde bir" irtifa tutmak yerine 9 m/s tirmandirir.
    #    KURAL: 0 ile HOVER_THR arasina ASLA hedef komut verilmez.
    #    Eski kodun "kacak tirmanma"sinin kok nedeni tam olarak buydu: irtifa
    #    PID'i cubugu DOGRUDAN suruyor ve bu zehirli banda giriyordu.
    POS_SLOPE = 32.64      # (m/s)/birim;  vz = 32.64*thr + 0.869   (thr > 0)
    POS_INTERCEPT = 0.869  # m/s
    NEG_SLOPE = 16.78      # (m/s)/birim;  vz = 16.78*thr + 9.835   (thr <= HOVER_THR)
    NEG_INTERCEPT = 9.835  # m/s
    HOVER_THR = -0.586     # vz=0 veren throttle (negatif kolun sifir gecisi)
    HOLD_BAND = 0.05       # |vz_istenen| bunun altindaysa HOVER_THR
    VZ_MAX_CLIMB = 33.51   # m/s; OLCULDU
    VZ_MAX_DESCENT = 6.95  # m/s; OLCULDU @thr=-1
    # ⚠ BELGE YANLIS: README "-1 = serbest dusus" diyor; serbest dusus 5 s'de
    #   -49 m/s verirdi, OLCULEN -6.95.

    # --- YAW ---
    # Arac 214 derece/s yapabiliyor AMA hizli yaw goruntuyu bulandirip
    # dedektoru kirar -> 120 sinirinda BILINCLI olarak tutuluyor.
    YAW_RATE_MAX_DEG = 120.0


class VelocityToStick:
    """Hiz setpoint'ini kumanda cubuguna cevirir. DURUMSUZDUR (state yok) —
    her faz kendi ornegini tutabilir; devirde tasinacak bir sey yoktur.

        thr, pitch, roll, yaw = cev.convert(
            v_des=(vx, vy, vz_ned),        # m/s; xy Unreal dunya, vz NED (asagi+)
            v_meas=(vx, vy, vz),          # m/s; Unreal (SDK)
            yaw_rad=...,                     # aracin burun acisi
            yaw_rate_des_deg=...)          # derece/s
    """

    def __init__(self, cfg=ConverterCfg):
        self.cfg = cfg
        self.diag = {}

    # ---------------- ivme -> cubuk ----------------
    def _accel_stick(self, a):
        c = self.cfg
        if c.MODEL == "angle":
            return clamp(math.degrees(math.atan2(a, 9.81)) / c.MAX_BANK_DEG, -1.0, 1.0)
        return clamp(a / c.A_MAX, -1.0, 1.0)

    def vz_stick(self, vz_up):
        """Istenen dikey hizi (m/s, +yukari) throttle'a cevirir — OLCULMUS model.
        Dogrulandi (istenen -> olculen): +10 -> +10.38 | -2 -> -1.88 |
        -5 -> -4.78 | -6.5 -> -6.26  (hata %4-6)."""
        c = self.cfg
        if abs(vz_up) < c.HOLD_BAND:
            # ⛔ BURADA 0.0 DONMEK YANLIS: oyunun "irtifa tut" kipi (thr=0)
            #    aslinda +0.88 m/s TIRMANIYOR. Dogru notr HOVER_THR (-0.586);
            #    orada olculen vz = -0.235 m/s (hafif alcalma = guvenli taraf).
            return c.HOVER_THR
        if vz_up > 0.0:
            return clamp((vz_up - c.POS_INTERCEPT) / c.POS_SLOPE, 0.0, 1.0)
        # alcalma: negatif kol. Sonuc ASLA (HOVER_THR, 0) zehirli bandina dusmez.
        return clamp((vz_up - c.NEG_INTERCEPT) / c.NEG_SLOPE, -1.0, c.HOVER_THR)

    # ---------------- ana ----------------
    def convert(self, v_des, v_meas, yaw_rad, yaw_rate_des_deg=0.0):
        c = self.cfg
        vx_des, vy_des, vz_des_ned = v_des
        vx_meas, vy_meas, _vz_meas = v_meas

        # [1] iki hizi da GOVDE cercevesine al
        fwd_des, right_des = world_to_body(vx_des, vy_des, yaw_rad, c.Y_SIGN)
        fwd_meas, right_meas = world_to_body(vx_meas, vy_meas, yaw_rad, c.Y_SIGN)

        # [2] hiz hatasi -> istenen ivme
        a_fwd = c.K_V * (fwd_des - fwd_meas)
        a_right = c.K_V * (right_des - right_meas)

        # [3] ivme -> cubuk
        pitch = self._accel_stick(a_fwd)
        roll = self._accel_stick(a_right)

        # [4] dikey: olculmus iki kollu ters model
        vz_up = c.Z_SIGN * vz_des_ned
        thr = self.vz_stick(vz_up)

        # [5] yaw
        yaw = clamp(yaw_rate_des_deg / c.YAW_RATE_MAX_DEG, -1.0, 1.0)

        # mekanizma sutunu: bu alanlar sifirsa cevirici calismiyordur
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
    """Oyuna giden TEK komut kapisi (throttle/pitch/roll/yaw + arm).

    send()     : egim sinirli (tik basina en fazla MAX_DELTA degisim).
    send_raw() : sinir YOK — cubugun aninda uygulanmasi gereken durumlar icin.

    EGIM SINIRI (MAX_DELTA=0.15) OLCULDU: aracin yatisi zaten 0.211 s zaman
    sabitiyle yumusuyor; sinir ONDAN GEVSEK olmali, yoksa iki sonumleme ust
    uste binip tepkiyi geciktirir. 50 Hz'de 0.15 -> tam cubuk 0.13 s'de.
    """

    MAX_DELTA = 0.15

    def __init__(self, drone):
        self.drone = drone
        self.prev = {"thr": 0.0, "pitch": 0.0, "roll": 0.0, "yaw": 0.0}

    def reset(self):
        self.prev = {"thr": 0.0, "pitch": 0.0, "roll": 0.0, "yaw": 0.0}

    def send(self, thr, pitch, roll, yaw):
        d = self.MAX_DELTA
        self.send_raw(rate_limit(thr, self.prev["thr"], d),
                      rate_limit(pitch, self.prev["pitch"], d),
                      rate_limit(roll, self.prev["roll"], d),
                      rate_limit(yaw, self.prev["yaw"], d))

    def send_raw(self, thr, pitch, roll, yaw):
        thr = clamp(float(thr), -1.0, 1.0)
        pitch = clamp(float(pitch), -1.0, 1.0)
        roll = clamp(float(roll), -1.0, 1.0)
        yaw = clamp(float(yaw), -1.0, 1.0)
        self.prev = {"thr": thr, "pitch": pitch, "roll": roll, "yaw": yaw}
        self.drone.set_control_surfaces(thr, pitch, roll, yaw, True)

    def loiter(self):
        """Hedef/veri yokken bekle: irtifayi TUT, yatay komut verme.

        ⛔ thr=0 GONDERILMEZ — oyunun "irtifa tut" kipi orada +0.88 m/s
          TIRMANIYOR (bkz. ConverterCfg). Kosular arasinda oyle birakinca arac
          180 m'den 5821 m'ye cikmisti. Dogru notr HOVER_THR'dir.
        """
        self.send(ConverterCfg.HOVER_THR, 0.0, 0.0, 0.0)

    def cut(self):
        """Motorlari kes (gorev sonu / Ctrl+C)."""
        self.prev = {"thr": 0.0, "pitch": 0.0, "roll": 0.0, "yaw": 0.0}
        self.drone.set_control_surfaces(0.0, 0.0, 0.0, 0.0, False)

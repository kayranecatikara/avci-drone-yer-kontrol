# -*- coding: utf-8 -*-
"""
control/spike.py — ÇARPMA (SPIKE) FAZI: terminal hücum yasası

Görsel fazın ARDINDAN gelir. Görevi tek cümledir: hedefin kuyruğunda oturmayı
bırak, TEMAS menziline kadar kapan.

    ileri hız  = kutu boyutu hatası üzerinden PI, sıfır noktası TEMAS (1 m)
    dikey      = kadraj regülasyonu, nişan noktası YAKINDA merkeze KAYAR
    yaw        = burnu kerterize çevir (görsel fazla AYNI yasa)

⛔ KATI KURAL — GPS/GNSS YASAK. Bu faz görsel temastan SONRA gelir, yani
   kuralın tam merkezindedir. `compute()` imzasında hedefe ait tek veri
   **bbox pikselleri**dir; `own_*` değerleri KENDİ IMU/hızımızdır
   (ego-motion telafisi), hedef verisi değildir. Konum/hız/GNSS kestirimi
   parametre olarak bile geçmez.

⭐ ZARF VE ORTAK SABİTLER TEK KAYNAKTAN. Yaw ve dikey kanal sabitleri
   `VisualCfg`ten OKUNUR, buraya kopyalanmaz — onlar kameranın ve aracın
   ölçülmüş sabitleridir, faza ait değildir. Bu dosyada yalnız ÇARPMAYA
   ait olanlar tanımlıdır (PI kazançları, temas menzili, terminal nişan).

KAYNAK: sabitler kardeş depodan (`drones_of_war_entegrasyon/dow/gudum/ibvs.py`)
   değil, BU DEPONUN kendi git geçmişinden geri alındı (`47eeddd~1`) — ikisi
   zaten aynı ölçüm soyundan gelir ve birebir aynıdır. 2026-08-25'te "şu anki
   amaç temas değil, kamera takibini iyileştirmek" gerekçesiyle silinmişlerdi;
   şimdi kendi fazına konuyor (CLAUDE.md o gün "spike fazı yazılırken buraya
   konmalıdır" diye not düşmüştü).
"""
import math

from control.common import VelocityToStick, clamp, wrap_deg
from control.visual_tracking import (REF_H, RANGE_C_REF, VisualCfg, _scale,
                                     pixel_bearing, range_m)


# ==========================================================
#  AYARLAR
# ==========================================================
class SpikeCfg:
    """Çarpma fazının ayarları — YALNIZ bu faza ait olanlar.

    Yaw ve dikey kanal sabitleri buraya KOPYALANMAZ, `VisualCfg`ten okunur:
    onlar kameranın ve aracın ölçülmüş sabitleridir, faza ait değildir.
    Burada tanımlı olanlar hücuma özgüdür: PI kazançları, temas menzili ve
    terminal nişan kayması.
    """

    # ============ İLERİ HIZ: TEMASA KADAR PI ============
    # ⛔ GÖRSEL FAZDAN FARKI BURADADIR. Görsel faz `TRAIL_RANGE_M`(4.5 m)
    #   profilini sıfırlar — yani KUYRUĞA OTURUR ve orada kalır. Çarpma fazı
    #   ise sıfır noktasını TEMAS menziline koyar: hata hep pozitif kalır,
    #   hız tavanda oturur, kapanma sabit olur. "Şu menzilde dur" noktası YOK.
    ATTACK_RANGE_M = 1.0  # m; PI'nin SIFIR NOKTASI = temas menzili. Hedef "şu
                          # menzilde dur" değil, "temasa kadar kapan"dır; bu yüzden
                          # hata pratikte hep pozitif kalır ve hız tavanda oturur.
    K_FWD = 0.35          # (m/s)/px @1920; kutu boyutu hatasını ileri hıza çeviren
                          # P kazancı (hata TEMAS kutusu - şimdiki kutu, px)
    K_I = 0.04            # (m/s)/(px·s) @1920; aynı hatanın I kazancı — kalıcı
                          # kapanma eksikliğini zamanla kapatır
    I_MAX = 8.0           # m/s; integralin doyum sınırı (windup önleyici). İntegral
                          # bu değeri aşamaz, yani PI çıkışına en fazla 8 m/s ekler.

    # ⭐ V_ATTACK BİR HIZ TAVANIDIR, "hücum hızı" DEĞİL. Talon 17.98 m/s
    #   uçuyor; 18 ile kapanma 0.02 m/s = asla yakalayamayız. 28 -> ~10 m/s.
    V_ATTACK = VisualCfg.V_MAX  # m/s; görsel fazla AYNI tavan (tek kaynak)
    V_MIN = VisualCfg.V_MIN     # m/s; asla geri gitme

    # ============ TERMİNAL NİŞAN (dikey referans kayması) ============
    # ⭐ BU KAYMA BİLEREK GÖRSEL YASADAN ALINIP BURAYA KONDU (2026-08-25'te
    #   `VisualCfg`ten silinmişti). Gerekçesi kayıtlı: "spike'a nişan alma"
    #   davranışıdır, takip yasasının değil. Uzakta hedefi merkezin ÜSTÜNDE
    #   tutmak kameranın 26.5° yukarı bakışıyla uyumludur (altta kal, gör);
    #   yakında merkeze almak NİŞAN ALMAKTIR.
    #
    # ⛔ BAŞLANGIÇ NOKTASI TEK KAYNAKTAN: `VisualCfg.CY_REF`. Sayı BURAYA
    #   YAZILMAZ — çarpma fazının nişanı, görsel fazın hedefi BIRAKTIĞI yerden
    #   başlamak ZORUNDADIR. İkisi ayrı yazılırsa aralarındaki fark, faz
    #   geçişinde doğrudan bir dikey BASAMAK olur (aşağıya bak).
    CY_REF_FAR = VisualCfg.CY_REF   # px @1080; harmanın BAŞLANGICI = görsel fazın
                                    # hedefi bıraktığı nişan noktası (tek kaynak)
    CY_REF_NEAR = 540.0             # px @1080; harmanın BİTİŞİ = kadrajın tam ortası.
                                    # Temasta hedefi merkeze almak "nişan almak"tır.

    # ⛔ HARMAN GİRİŞ KUTUSUNA ÇAPALANIR — SABİT PİKSELE DEĞİL.
    #   Devralınan sürümde harman sabit 40->90 px (~25 m -> ~11 m) idi. O,
    #   terminal nişanın UZUN bir yaklaşma boyunca kaydığı bir mimariden
    #   geliyordu. BİZDE çarpma fazı ~5 m'de açılıyor ve kutu orada zaten
    #   ~199 px — yani harman GEÇİŞ ANINDA ÇOKTAN DOYMUŞ (k=1.0) ve nişan
    #   470'ten 540'a BİR ANDA atlıyordu. Ölçüldü:
    #       e_cy basamagi = -70 px  ->  vz = +0.98 m/s  ->  throttle
    #       HOVER_THR(-0.586) -> 0.000 = 0.586 birim = MAX_DELTA'nin 3.9 KATI
    #       -> egim siniri 78 ms DOYAR (dikey kanalda, ileri kanaldan daha kotu)
    #
    #   ⛔ ZAMANLA YAYMAK ÇÖZMEZ — ölçülmüş throttle haritası "yumuşak
    #     tırmanma" bölgesi İÇERMİYOR: pozitif dal 0.869 m/s'den başlar ve
    #     [0,1]'e kırpılır, dolayısıyla `HOLD_BAND`(0.05) aşılan HER an
    #     throttle aynı basamağı atar. Rampanın hızı fark etmez.
    #     Çözülecek şey rampa değil, **geçiş anında e_cy'nin SIFIR olması**.
    #
    #   ⭐ ÇÖZÜM YAPISALDIR: harman, faza GİRİŞTEKİ kutu boyutundan başlar.
    #     Girişte k=0 -> nişan = `VisualCfg.CY_REF` -> görsel fazın hedefi
    #     tuttuğu yerin TA KENDİSİ -> e_cy = 0 -> BASAMAK YOK. Ve bu, faz
    #     hangi menzilde açılırsa açılsın geçerlidir (5 m'de de, 8 m'de de).
    #     Harman TEMAS kutusunda tamamlanır; ikisi de türetilir, yeni tune
    #     düğmesi YOKTUR.

    # ============ ORTAK SABİTLER — TEK KAYNAK: VisualCfg ============
    # ⛔ BURAYA SAYI YAZMAYIN. Bunlar kameranın/aracın ölçülmüş sabitleridir
    #   ve faza ait değildir; iki yerde tutulurlarsa kayarlar (zarf sabitleri
    #   üç yere kopyalandığında tırmanma tavanı 33.51/33.5/33.5 diye ZATEN
    #   kaymıştı — bkz. CLAUDE.md).
    K_YAW = VisualCfg.K_YAW                  # oran; azimut hatasının burun hedefine yansıyan payı
    KP_YAW_RATE = VisualCfg.KP_YAW_RATE      # 1/s; yaw hatası (derece) -> dönüş hızı (derece/s)
    YAW_RATE_MAX = VisualCfg.YAW_RATE_MAX    # derece/s; azami dönüş hızı
    YAW_DEADBAND = VisualCfg.YAW_DEADBAND    # derece; bunun altındaki azimut hatası düzeltilmez
    K_CY = VisualCfg.K_CY                    # (m/s)/px @1080; dikey kadraj hatası -> dikey hız
    VZ_CAP_VISUAL = VisualCfg.VZ_CAP_VISUAL  # m/s; dikey hız komutunun tavanı
    VZ_MAX_CLIMB = VisualCfg.VZ_MAX_CLIMB    # m/s; aracın tırmanma zarfı
    VZ_MAX_DESCENT = VisualCfg.VZ_MAX_DESCENT  # m/s; aracın alçalma zarfı (asimetrik)
    BRIDGE_S = VisualCfg.BRIDGE_S            # s; kutu köprüsünün azami ömrü


# ==========================================================
#  ÇARPMA FAZI SÜRÜCÜSÜ
# ==========================================================
class SpikeLaw:
    """ÇARPMA fazının sürücüsü — terminal hücum yasası.

    Görsel fazdan tek farkı İLERİ HIZ ve DİKEY NİŞANDIR: kuyrukta oturmayı
    bırakıp temas menziline kadar kapanır, nişanı da yaklaştıkça kadrajın
    ortasına kaydırır. Yaw kanalı görsel fazla BİREBİR aynıdır.

    Kutu köprüsü BU SINIFTA YOKTUR: köprü tek kaynaktadır (`VisualTracker.box`)
    ve koşturucu çarpma fazında da onu çağırır.

    ⛔ Girdi yalnız kutu pikselleri + kendi IMU'muzdur; `compute()` imzasında
      hedefe ait konum/hız/GNSS verisi geçmez.
    """

    def __init__(self, cfg=SpikeCfg):
        """cfg: çarpma fazı ayarları (varsayılan `SpikeCfg`)."""
        self.cfg = cfg
        self.conv = VelocityToStick()
        self.reset()

    def reset(self):
        """Her çarpma fazı girişinde çağrılır — integral TAZE başlar.

        ⛔ INTEGRALI TAŞIMAYIN. Faz geri dönüp tekrar girilirse eski integral
          `I_MAX`(8 m/s) kadar bir ön yükle başlar ve ilk komut doyar.
        """
        self._entry_size = None  # px @1920; faza GİRİŞTEKİ kutu boyutu — terminal
                                 # nişan harmanının çapası (girişte k=0 olsun diye)
        self._i = 0.0      # m/s; PI'nin integral durumu (±I_MAX ile sınırlı)
        self._v_cmd = 0.0  # m/s; son ileri hız komutu (köprü karesinde tekrarlanır)
        self._tlm = {}     # son tikin telemetrisi

    # ------------------------------------------------------------------
    def _aim_cy(self, size_px, W, H):
        """Terminal nişan noktasını hesaplar.

        size_px : px; bu karenin kutu boyutu
        W, H    : px; kare ölçüleri
        -> (cy_ref, k) — nişan yüksekliği (px, bu karenin ölçeğinde) ve harman
           oranı k (0 = giriş nişanı, 1 = temas nişanı)

        Nişan GİRİŞ kutusundan TEMAS kutusuna doğrusal olarak kayar.

        Girişte k=0 olduğu için nişan `VisualCfg.CY_REF`tir: görsel fazın
        hedefi tuttuğu nokta. Bu yüzden faz geçişinde e_cy = 0'dır ve dikey
        kanalda BASAMAK OLUŞMAZ (bkz. SpikeCfg'deki gerekçe).
        """
        p = self.cfg
        sw = _scale(W)
        sh = float(H) / REF_H
        size_1920 = float(size_px) / sw  # kazançlar @1920, ölçeğe normalize
        if self._entry_size is None:
            self._entry_size = size_1920
        # TEMAS kutusu: harmanın tamamlandığı yer (ATTACK_RANGE_M'den TÜRER)
        contact = RANGE_C_REF / float(p.ATTACK_RANGE_M)
        span = contact - self._entry_size
        if span <= 1e-6:
            # Faz zaten temas kutusundan büyük bir kutuyla açıldı (patolojik);
            # nişanı kaydırmak basamak üretir, kaydırma.
            k = 0.0
        else:
            k = clamp((size_1920 - self._entry_size) / span, 0.0, 1.0)
        cy_ref = float(p.CY_REF_FAR) + k * (float(p.CY_REF_NEAR) - float(p.CY_REF_FAR))
        return cy_ref * sh, k

    # ------------------------------------------------------------------
    def _attack_speed(self, size_px, W, dt, bridge):
        """İleri hız komutu — kutu boyutu hatası üzerinden PI.

        size_px : px; bu karenin kutu boyutu
        W       : px; kare genişliği (kazançlar @1920 tanımlı, normalize edilir)
        dt      : s; ölçülmüş tik süresi
        bridge  : bu kare köprüden mi geldi? True ise integral İLERLETİLMEZ
        -> ileri hız komutu (m/s), [V_MIN, V_ATTACK] arasında

        Hata = TEMAS kutusu - şimdiki kutu (px). Menzil kapandıkça kutu büyür,
        hata küçülür; temasta sıfırlanır.

        ⚠ SÜZGEÇ YOK — bilinçli. Görsel fazda `size`e medyan süzgeç uygulanır
          (dedektör gürültüsü `R = C/size` terslemesinde şişer). Burada
          uygulanmaz, iki sebeple:
          1. Terminal fazda kutu DEVDİR (1-3 m'de 330-1000 px @1920); bağıl
             gürültü küçüktür — ölçülen oynaklık uzak/küçük kutuda kötüydü.
          2. Medyan bir rampayı pencere/2 = 0.1 s geciktirir; `V_ATTACK`
             28 m/s'de bu **2.8 m bayat menzil** demektir — `ATTACK_RANGE_M`in
             kendisinden büyük. Terminal fazda gecikme, gürültüden pahalıdır.

        ⚠ KÖPRÜ KARESİNDE INTEGRAL İLERLETİLMEZ. Köprü aynı kutuyu ileri
          taşır; onu tekrar tekrar hataya çevirmek integrali gerçek olmayan
          bir kanıtla şişirirdi.
        """
        p = self.cfg
        if bridge or dt <= 0.0:
            return self._v_cmd
        sw = _scale(W)
        target_size = (RANGE_C_REF * sw) / float(p.ATTACK_RANGE_M)
        err_px = (target_size - float(size_px)) / sw  # 1920 referansına normalize
        self._i = clamp(self._i + float(p.K_I) * err_px * dt,
                        -float(p.I_MAX), float(p.I_MAX))
        self._v_cmd = clamp(float(p.K_FWD) * err_px + self._i,
                            float(p.V_MIN), float(p.V_ATTACK))
        return self._v_cmd

    # ------------------------------------------------------------------
    #  YASA
    # ------------------------------------------------------------------
    def compute(self, det, own_att_deg, own_vel_ms, dt):
        """(thr, pitch, roll, yaw) çubuk konumu — girdi yalnız piksel + IMU."""
        p = self.cfg
        own_roll, own_pitch, own_yaw = own_att_deg
        W = float(det["W"]); H = float(det["H"])
        cx = float(det["cx"]); cy = float(det["cy"])
        size = max(float(det["w"]), float(det["h"]))
        bridge = bool(det.get("bridge"))

        # --- 1) KERTERİZ ---
        azimuth, _ = pixel_bearing(cx, cy, own_pitch, own_roll, W, H)

        # --- 2) YAW (görsel fazla AYNI yasa) ---
        eps_yaw = 0.0 if abs(azimuth) < float(p.YAW_DEADBAND) else azimuth
        yaw_des = own_yaw + float(p.K_YAW) * eps_yaw
        yaw_rate = clamp(float(p.KP_YAW_RATE) * wrap_deg(yaw_des - own_yaw),
                         -float(p.YAW_RATE_MAX), float(p.YAW_RATE_MAX))

        # --- 3) İLERİ HIZ: TEMASA KADAR PI ---
        v = self._attack_speed(size, W, dt, bridge)

        # --- 4) YATAY ---
        heading = math.radians(yaw_des)
        vx = v * math.cos(heading)
        vy = v * math.sin(heading)

        # --- 5) DİKEY: terminal nişanla kadraj regülasyonu ---
        sh = float(H) / REF_H
        cy_ref, blend = self._aim_cy(size, W, H)
        e_cy = cy - cy_ref  # + = hedef kadrajda AŞAĞIDA
        vz_raw = -(float(p.K_CY) / sh) * e_cy
        vz_up = clamp(vz_raw, -float(p.VZ_CAP_VISUAL), float(p.VZ_CAP_VISUAL))
        vz_up = clamp(vz_up, -float(p.VZ_MAX_DESCENT), float(p.VZ_MAX_CLIMB))

        # --- 6) HIZ -> ÇUBUK ---
        thr, pitch, roll, yaw = self.conv.convert(
            (vx, vy, -vz_up), own_vel_ms, math.radians(own_yaw), yaw_rate)

        R = range_m(size, W)
        self._tlm = {
            "range_m": round(R, 2) if R else -1.0,
            "size_px": round(size, 1),
            "v_fwd": round(v, 2),
            "pi_i": round(self._i, 2),      # mekanizma sütunu: integral doyuyor mu
            "cy_ref": round(cy_ref, 1),
            "aim_blend": round(blend, 3),   # 0 = uzak nişan, 1 = terminal nişan
            "e_cy": round(e_cy, 1),
            "bridge": int(bridge),
            "thr": round(thr, 3), "pitch": round(pitch, 3),
            "roll": round(roll, 3), "yaw": round(yaw, 3),
        }
        self._tlm.update(self.conv.diag)
        return float(thr), float(pitch), float(roll), float(yaw)

    def status(self):
        """Son tikin telemetrisi (yalnız gösterge; komuta girmez).

        `pi_i` integralin doyup doymadığını, `aim_blend` nişan harmanının ne
        kadar ilerlediğini (0 = giriş, 1 = temas) doğrudan gösterir.
        """
        return dict(self._tlm)

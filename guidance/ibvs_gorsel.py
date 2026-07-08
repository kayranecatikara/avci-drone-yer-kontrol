# -*- coding: utf-8 -*-
"""
HAMIDIYE — BASIT IBVS GORSEL GUDUM  (goruntu merkezi -> bbox merkezi cizgisi)
=============================================================================
TEK FIKIR: goruntunun ORTA NOKTASINDAN tespit kutusunun (bbox) MERKEZINE bir
cizgi cek. Bu cizginin ACISI duzeltmenin yonunu, BUYUKLUGU ise merkeze olan
sapma "mesafesini" verir. Guduum bu cizgiyi SIFIRA surmekten ibarettir:
cizgi kuculdukce hedef kadraj merkezine oturur; hedef merkezde tutulup
surekli ILERI ucunca rota kendiliginden hedefin uzerine kapanir (saf takip /
pure pursuit). Kamera govdeye +25 derece YUKARI tilt'li oldugundan hedefi
merkezde tutmak araci hedefin ALTINDA tutar (gokyuzu arka plan / alttan
yaklasma) — bunun icin ekstra kod GEREKMEZ, geometriden bedava gelir.

    ex = (cx - W/2) / (W/2)     -1..+1   (+ = hedef goruntude SAGDA)
    ey = (cy - H/2) / (H/2)     -1..+1   (+ = hedef goruntude ASAGIDA)
    buyukluk  r = hypot(ex, ey)          (0 = tam merkez, ~1.41 = kose)
    aci         = atan2(-ey, ex)         (0 = saga, +90 = yukari; derece)

    yaw   = K_YAW   * ex                 hedef sagda  -> saga don
    thr   = K_DIKEY * (-ey)              hedef yukarida -> tirman
    pitch = ILERI * (1 - MERKEZ_FREN*r)  merkezde tam ileri; sapmisken kis
    roll  = 0                            cerceveleme yaw'in isi; bank YOK
                                         (eski PN'de bank hedefi kadrajdan
                                          atip kamerayi yere ceviriyordu)

ONGORULU (LEAD) YAW — POSE'DAN HEDEF ROLL (2026-07-07):
Pose modeli (talon_pose.pt) hedefin 6 keypoint'ini verir. Hedefi ARKADAN takip
ederken iki KANAT UCU pikselinden (kp[1]=sol, kp[2]=sag) goruntu-uzayi bank acisi
cikarilir: roll_img = atan2(dy, dx). Banklı ucak alcak kanadi yonune doner
(koordineli donus) -> hedefin BIR AN SONRA gidecegi yon oncelenir ve yaw komutuna
ILERI-BESLEME (lead) olarak eklenir: yaw = K_YAW*ex + K_ROLL*roll_img. Burun
hedefin gidecegi yere onceden doner (geriden kovalamayi onler). Sadece YAW kanali;
thr/pitch/roll degismez. Kapilar (kanat conf, arkadan-takip aspect'i, bayatlik)
dususe lead=0 -> saf IBVS (zarif dusus).

YARISMA KURALI (KATI): gorsel temas SONRASI hareket komutu YALNIZCA gorsel
veriden turetilir. Bu yasaya giren HER sey KAMERADAN gelir: bbox pikselleri
(det) + pose KEYPOINT pikselleri (poz). Ikisi de gorsel -> kurala UYGUN.
GPS/GNSS, J-filtre, konum/hiz/rotasyon telemetrisi hicbir sekilde KULLANILMAZ
(imzada det + p + poz var; drone_pos/v_own/rot GIRMEZ -> test_gps_siz_imza kilitler).

Eski PN/PNG yigini (LOS vektoru, Omega, pinhole menzil, kapanma regulasyonu,
look-up geometrisi, soft-start, PN lead-yaw, YAKLASMA/TAKIP/TERMINAL alt-FSM)
2026-07-07'de kullanici karariyla KOMPLE SILINDI; git gecmisinde durur.
Parametreler disaridan `p` (Cfg) ile gelir; ana_kontrol IMPORT EDILMEZ.
"""
import math


def clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x


def kanat_roll_img(L, R, W, H):
    """Iki kanat ucu (normalize [u,v,conf]) -> GORUNTU-UZAYI bank acisi (rad).
    L=sol kanat, R=sag kanat. Normalize u/v ayri ayri W/H'ye bolundugunden aci
    aspect'ten bozulur -> piksel-orana geri olceklenir. Seviye+arkadan: du>0, dv~0
    -> ~0. Sag kanat ALCAK (v buyuk) -> dv>0 -> roll_img>0 (hedef saga bank/saga doner)."""
    dx = (float(R[0]) - float(L[0])) * float(W)
    dy = (float(R[1]) - float(L[1])) * float(H)
    if abs(dx) < 1e-9 and abs(dy) < 1e-9:
        return 0.0
    return math.atan2(dy, dx)


class AvciIBVS:
    """Basit IBVS: tek durum ex/ey EMA'si (tek-kare YOLO sicramasini yumusatir)."""

    def __init__(self):
        self.sifirla()

    def sifirla(self):
        """Gorev basi / kaynak degisimi / GPS'e donus: filtreyi taze basla."""
        self.ex_f = 0.0              # EMA yatay sapma (-1 sol .. +1 sag)
        self.ey_f = 0.0              # EMA dikey sapma (-1 ust .. +1 alt)
        self._had = False            # ilk kare EMA'siz alinir
        self.roll_f = 0.0            # EMA hedef bank (EGO-TELAFILI roll, rad; pose kanat uclarindan)
        self._roll_had = False       # ilk gecerli roll EMA'siz alinir
        self._roll_raw_deg = 0.0     # ANLIK ham goruntu-roll (ego-telafisiz, EMA'siz; teshis/A-B)
        self._tlm = {}               # son telemetri (server build_telemetry okur)

    # ------------------------------------------------------------------
    #  Pose kanat uclarindan ONGORULU yaw lead (rad). poz normalize kp tasir
    #  (kameradan gorsel veri — GPS/J DEGIL). Kapi dususe (0.0, False) -> saf IBVS.
    #  W,H ayni kareden (det) gelir -> normalize kp'yi piksel-orana olcekler.
    #  own_roll_rad: aracin KENDI roll'u (IMU/jiroskop) — EGO-MOTION telafisi icin
    #  goruntu-roll'unden cikarilir (kamera govdeye sabit -> biz yatinca kanat cizgisi
    #  de doner; bu bizim bank'imiz, hedefin degil). Hedef YONU hala %100 kameradan;
    #  own_roll yalnizca gorsel OLCUMU temizler (hedef konumu DEGIL -> kural ihlali degil).
    # ------------------------------------------------------------------
    def _roll_lead(self, poz, W, H, p, own_roll_rad=None):
        if poz is None:
            return 0.0, False
        kp = poz.get("kp")
        if not kp or len(kp) < 3 or kp[1] is None or kp[2] is None:
            return 0.0, False
        L, R = kp[1], kp[2]                       # sol, sag kanat ucu [u,v,conf] normalize
        if len(L) < 3 or len(R) < 3:
            return 0.0, False
        cmin = float(getattr(p, "IBVS_ROLL_CONF_MIN", 0.5))
        if float(L[2]) < cmin or float(R[2]) < cmin:
            return 0.0, False                     # kanat ucu guveni dusuk -> roll guvenilmez
        asp = poz.get("aspect_deg")               # yalniz PnP oturunca var (0=kafa kafaya,180=arkadan)
        if asp is not None and float(asp) < float(getattr(p, "IBVS_ASPECT_MIN", 120.0)):
            return 0.0, False                     # yandan/onden: kanat cizgisi bank'i temsil etmez
        roll_img = kanat_roll_img(L, R, float(W), float(H))   # HAM goruntu-roll (kendi bank'imiz dahil)
        self._roll_raw_deg = math.degrees(roll_img)
        # EGO-MOTION TELAFISI: kendi roll'umuzu cikar -> hedefin GERCEK bank'ina yaklas.
        gain = float(getattr(p, "IBVS_EGO_ROLL_GAIN", 1.0))
        orr = float(own_roll_rad) if own_roll_rad is not None else 0.0
        roll_comp = roll_img - gain * orr
        a = clamp(float(getattr(p, "IBVS_ROLL_EMA", 0.4)), 0.0, 1.0)
        if self._roll_had:
            self.roll_f = (1.0 - a) * self.roll_f + a * roll_comp
        else:
            self.roll_f = roll_comp
            self._roll_had = True
        lead = float(getattr(p, "IBVS_SIGN_ROLL", 1.0)) * float(getattr(p, "IBVS_K_ROLL_LEAD", 0.0)) * self.roll_f
        return lead, True

    # ------------------------------------------------------------------
    #  det: {cx,cy,w,h,conf,W,H,t} (piksel) -> (thr, pitch, roll, yaw) [-1..1]
    #  poz: normalize keypoint dict (kameradan gorsel; kanat uclarindan yaw lead) | None
    #  Server ayni det'i VIS_STALE_S boyunca sunar; ayni kareyi tekrar gormek
    #  zararsizdir (EMA sabit degere yakinsar = son komutu tutar).
    # ------------------------------------------------------------------
    def hesapla(self, det, p, poz=None, own_roll_rad=None):
        W = float(det["W"]); H = float(det["H"])
        ex = (float(det["cx"]) - W / 2.0) / (W / 2.0) if W > 1 else 0.0
        ey = (float(det["cy"]) - H / 2.0) / (H / 2.0) if H > 1 else 0.0
        a = clamp(float(p.VIS_EMA), 0.0, 1.0)
        if self._had:
            self.ex_f = (1.0 - a) * self.ex_f + a * ex
            self.ey_f = (1.0 - a) * self.ey_f + a * ey
        else:
            self.ex_f, self.ey_f = ex, ey
            self._had = True

        # DIKEY NISAN (tilt-farkinda): kamera +TILT derece YUKARI baktigindan, hedefi kadraj
        # MERKEZINDE tutmak = hiz vektorunu hedefin ~TILT altina nisanlamak. Hedefi hiz
        # vektorunun goruntudeki yerine (FOE) tutmak icin dikey setpoint:
        #   ey_ref = NISAN * tan(TILT) / tan(VFOV_yari)   (NISAN=0 merkez/altta-kal, 1 hiz-vektoru).
        # Boylece "hedefte" = "burun hedefe kilitli" (dogrudan carpisma; 25-alti nisanlama biter).
        # NEGATIF NISAN (2026-07-08, alttan-vurus): hedefi merkez USTUNDE tut -> LOS > TILT ->
        # arac orantili olarak hedefin ALTINDA kalir + hedef gokyuzu arka planinda (zemin
        # clutter'da tespit olumu biter). Eski 0.0 tabani yasanin "hedefin ustune cikma"
        # egilimini yapisal kilitliyordu; -1.0'a acildi.
        nisan = clamp(float(getattr(p, "IBVS_DIKEY_NISAN", 1.0)), -1.0, 1.5)
        tilt = math.radians(float(getattr(p, "IBVS_TILT_DEG", 25.0)))
        vfov_h = math.radians(float(getattr(p, "IBVS_VFOV_HALF_DEG", 47.2)))
        tan_v = math.tan(vfov_h)
        ey_ref = nisan * math.tan(tilt) / tan_v if abs(tan_v) > 1e-9 else 0.0

        # NISAN NOKTASINDAN -> bbox cizgisi: yatay ex, dikey (ey - ey_ref) = nisandan sapma.
        eyy = self.ey_f - ey_ref                      # dikey sapma (nisan noktasina gore)
        r = math.hypot(self.ex_f, eyy)
        aci = math.degrees(math.atan2(-eyy, self.ex_f)) if r > 1e-9 else 0.0

        # ONGORULU YAW LEAD: hedef bank'ından (pose kanat uclari, ego-telafili) bir an
        # sonraki donusu oncele. Kapi dususe lead=0 -> saf IBVS. Sadece yaw kanalini etkiler.
        lead, roll_ok = self._roll_lead(poz, W, H, p, own_roll_rad=own_roll_rad)

        # cizginin yatay bileseni (+ongoru lead) -> yaw, dikey sapmasi -> throttle (nisana sur)
        yaw = clamp(float(p.IBVS_SIGN_YAW) * float(p.IBVS_K_YAW) * self.ex_f + lead,
                    -float(p.YAW_MAX), float(p.YAW_MAX))
        thr = clamp(float(p.IBVS_SIGN_DIKEY) * float(p.IBVS_K_DIKEY) * (-eyy),
                    float(p.THR_DN), float(p.THR_UP))
        # ileri itki: cizgi (nisandan sapma) buyudukce kisilir (once nisanla, sonra bas gitsin)
        kisma = clamp(1.0 - float(p.IBVS_MERKEZ_FREN) * r, 0.0, 1.0)
        # ALCALMA FRENI (anti-lift-carry; GPS alc_oncelik'in gorsel-faz aynasi, 2026-07-08):
        # hedef nisan noktasinin ALTINDAysa (eyy>0 = biz cok YUKSEKTEYIZ) ileri itkiyi
        # carpimsal kis -> ileri-ucus tasimasi (lift carry) dussun -> negatif thr GERCEKTEN
        # alcaltsin (GPS dersi ana_kontrol.THR_DN yorumunda: tam ileri ucusta -0.40 bile
        # tirmanmayi durduramiyordu). TIRMAN tarafi (eyy<0) DOKUNULMAZ. TABAN: asla tam
        # durma, biraz kapanis kalsin. Girdi yalniz goruntu buyuklugu (eyy) -> kural uygun.
        alcal = clamp(1.0 - float(getattr(p, "IBVS_ALCAL_FREN", 2.0)) * max(0.0, eyy),
                      float(getattr(p, "IBVS_ALCAL_TABAN", 0.2)), 1.0)
        pitch = float(p.PITCH_SIGN) * clamp(float(p.IBVS_ILERI), 0.0, 1.0) * kisma * alcal
        roll = 0.0

        self._tlm = {
            "law": "IBVS",
            "ex": round(self.ex_f, 3), "ey": round(self.ey_f, 3),
            "ey_ref": round(ey_ref, 3),       # dikey nisan (hiz-vektoru FOE; tilt'ten)
            "buyukluk": round(r, 3),          # nisandan sapma (0=hedef nisan noktasinda)
            "aci_deg": round(aci, 1),         # cizgi acisi (0=sag, +90=yukari)
            "kisma": round(kisma, 3),         # ileri itki carpani (1=tam gaz)
            "alcal": round(alcal, 3),         # alcalma freni carpani (1=serbest; eyy>0'da kisar)
            "dikey": round(thr, 3), "ileri": round(pitch, 3), "yaw": round(yaw, 3),
            # ONGORU (pose kanat uclarindan hedef bank -> yaw lead)
            "roll_deg": round(math.degrees(self.roll_f), 1),  # hedef bank (EGO-TELAFILI, EMA'li)
            "roll_raw_deg": round(self._roll_raw_deg, 1),     # ham goruntu-roll (telafisiz; A-B/teshis)
            "lead": round(lead, 3),           # yaw'a eklenen ongoru katkisi
            "roll_ok": bool(roll_ok),         # ongoru aktif mi (kapilar gecti mi)
        }
        return float(thr), float(pitch), float(roll), float(yaw)

    # ------------------------------------------------------------------
    #  Telemetri (server build_telemetry okur; guduum girdisi DEGIL).
    # ------------------------------------------------------------------
    def durum(self):
        return dict(self._tlm)

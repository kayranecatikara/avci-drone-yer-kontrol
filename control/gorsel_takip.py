# -*- coding: utf-8 -*-
"""
control/gorsel_takip.py — BASIT IBVS gorsel guduum (Faz 2).

TEK FIKIR: goruntudeki NISAN NOKTASINDAN tespit kutusunun (bbox) merkezine bir
cizgi cek. Cizginin ACISI duzeltmenin yonunu, BUYUKLUGU sapmanin miktarini verir.
Guduum bu cizgiyi SIFIRA surmekten ibarettir; hedef nisanda tutulup surekli ILERI
ucunca rota kendiliginden hedefin uzerine kapanir (saf takip / pure pursuit).

    ex = (cx - W/2) / (W/2)     -1..+1   (+ = hedef goruntude SAGDA)
    ey = (cy - H/2) / (H/2)     -1..+1   (+ = hedef goruntude ASAGIDA)
    eyy = ey_ego - ey_ref                (nisandan dikey sapma)
    r   = hypot(ex, eyy)                 (0 = hedef nisanda)

    yaw   = SIGN_YAW   * K_YAW   * ex          hedef sagda -> saga don
    thr   = SIGN_DIKEY * K_DIKEY * (-eyy)      hedef nisanin ustunde -> tirman
    pitch = ILERI * fren                       nisandayken tam ileri
    roll  = 0                                  cerceveleme yaw'in isi; bank YOK

Yasadaki her terim yalnizca KAMERADAN gelir (bbox pikselleri). Konum/hiz/GNSS
kestirimi bu fonksiyona GIRMEZ — `hesapla(det, own_pitch_rad)` imzasinda hedefe
ait tek veri bbox'tir. Bu yapisal bir kilittir: gorsel temas kurulduktan sonra
hedefi GPS ile yonlendirmek yarisma kuralinca yasaktir.
`own_pitch_rad` KENDI IMU pitch'imizdir (ego-motion), hedef verisi degildir.

DIKEY NISAN (tilt-farkinda): kamera govdeye +25 derece YUKARI tiltli. Hedefi
kadraj merkezinde tutmak araci hedefin altinda tutar; nisan noktasini merkezin
BIRAZ USTUNE almak (negatif NISAN) bu ayrimi buyutur -> hedef gokyuzu arka
planinda kalir (zemin clutter'inda tespit olmez), yaklasma alttan olur.

EGO-PITCH TELAFISI: ileri itki govdeyi one yatirir, govdeye sabit kamera duser
ve hedef goruntude sahte YUKARI ziplar. Yasa bunu "hedef kacti -> tirman" diye
okuyup kacak tirmanma yapiyordu. Dikey hata kendi pitch'imizden aritilir:
    ey_ego = ey - EGO_PITCH_GAIN * tan(own_pitch) / tan(VFOV_yari)

YUMUSAK GECIS: GPS'ten devir aninda hedef uzak -> ileri itki tavana doyar ve
ilk tikte tam lunge verir (govde one yatar, hedef kadrajin ustunden kacar).
Gorsel fazin ilk HANDOFF_S saniyesinde ILERI ITKI ve DIKEY NISAN 0'dan acilir;
yaw ve dikey ortalama ilk tikten TAM guctedir (hedefi kadrajda tutan kanallar).
"""
import math
import time

from control.common import clamp


class Cfg:
    # ================= TESPIT KAPISI / KAYIP =================
    CONF_MIN   = 0.15      # bu guvenin altindaki kutu guduume GIRMEZ
    STALE_S    = 0.5       # tespit bundan eskiyse yok say (dedektor titremesi koprusu)
    N_LOCK     = 5         # ard arda gecerli tespit -> gorsel faza gec (yanlis-poz bastir)
    LOST_S     = 0.8       # kayipta hover suresi; asilirsa GPS fazina geri don

    # ================= KOMUT TAVANLARI (GPS faziyla ayni kanon) =================
    PITCH_SIGN = +1.0
    THR_UP     = 0.70
    THR_DN     = -1.00
    YAW_MAX    = 0.45

    # ================= IBVS KAZANCLARI =================
    EMA        = 0.4       # ex/ey/boyut EMA (tek-kare YOLO sicramasini bastir)
    K_YAW      = 0.8       # yaw = SIGN_YAW * K_YAW * ex
    SIGN_YAW   = +1.0      # ters tepki gorursen -1 (canlida BIR KEZ dogrula)
    K_DIKEY    = 2.0       # thr = SIGN_DIKEY * K_DIKEY * (-eyy)
    SIGN_DIKEY = +1.0      # hedef YUKARIDA -> TIRMAN (GPS faziyla ayni kanon)
    ILERI      = 0.70      # ileri itki TAVANI (0..1)
    MERKEZ_FREN = 1.4      # sapma buyudukce ileri kis: fren = max(0, 1 - FREN*r)

    # --- BOYUT-REGULELI ILERI (istasyon tutma) ---
    # ileri = clamp(K_BOYUT * (BOYUT_HEDEF - boyut), -GERI_MAX, ILERI)
    # K_BOYUT = 0 -> regulasyon KAPALI: sabit ILERI tavaniyla hedefe kapan (takip/vurus).
    # K_BOYUT > 0 -> bbox hedef boyuta gelince hedefin gerisinde ISTASYON TUT.
    K_BOYUT     = 0.0
    BOYUT_HEDEF = 0.12     # bbox eksen orani hedefi max(w/W, h/H)
    GERI_MAX    = 0.15     # fazla yakinken geri kacis tavani

    # --- DIKEY NISAN (kamera tilt geometrisi) ---
    TILT_DEG      = 25.0   # kamera YUKARI tilt (platform sabiti, SDK basliginda yazili)
    VFOV_HALF_DEG = 47.2   # dikey FOV yari acisi (16:9 + HFOV 125'ten)
    DIKEY_NISAN   = -0.25  # NEGATIF = hedefi merkezin USTUNDE tut -> alttan yaklas
                           # 0 = merkezde tut; +1 = hiz vektorunu hedefe nisanla

    # --- ALCALMA FRENI (anti lift-carry) ---
    # Hedef nisanin ALTINDAysa (eyy>0 = fazla yuksekteyiz) ileri itkiyi kis ->
    # ileri-ucus tasimasi dussun -> negatif throttle GERCEKTEN alcaltsin.
    ALCAL_FREN  = 1.5
    ALCAL_TABAN = 0.2      # fren tabani (asla tam durma; biraz kapanis kalsin)

    # --- EGO-MOTION TELAFISI ---
    EGO_PITCH_GAIN = 0.4   # 1.0 asiriydi (kalici govde yatikligini "sahte yukari" sanip
                           # surekli alcalis veriyordu); 0.4 ucus verisiyle secildi

    # --- YUMUSAK GECIS (GPS -> gorsel) ---
    HANDOFF_S = 1.0        # ileri itki + dikey nisan rampasi (s); 0 = kapali


def nisan_kutusu(det, cfg=Cfg):
    """Guduume girebilecek kutu mu? Degilse None (tespit yok sayilir).

    TEK DOGRULUK KAYNAGI: gozetmenin devir kapisi da (control/main.py) bu
    fonksiyonu kullanir. Iki katmana ayri esik yazmak, gorsel fazin ayni karede
    reddettigi bir kutuyla devir yapilmasina ve faz sekmesine yol acar.
    """
    if det is None:
        return None
    if float(det.get("conf", 0.0)) < float(cfg.CONF_MIN):
        return None
    if float(det.get("W", 0)) <= 1 or float(det.get("H", 0)) <= 1:
        return None
    return det


def bayat_mi(det, cfg=Cfg, simdi=None):
    """Tespit STALE_S'ten eski mi? (dedektor 8-10 Hz, guduum 50 Hz -> ayni kutu
    birkac tik tekrar gorunur; bu normaldir, bayatlik esigi gercek kaybi ayirir.)"""
    if det is None or det.get("t") is None:
        return True
    simdi = time.perf_counter() if simdi is None else simdi
    return (simdi - float(det["t"])) > float(cfg.STALE_S)


class GorselTakip:
    """Basit IBVS gorsel guduum. Durum: ex/ey/boyut EMA + gecis rampasi."""

    def __init__(self, cfg=Cfg):
        self.cfg = cfg
        self.sifirla()

    def sifirla(self):
        """Her yeni gorsel faz basinda cagrilir (devir / GPS'e donus sonrasi)."""
        self.ex_f = 0.0          # EMA yatay sapma (-1 sol .. +1 sag)
        self.ey_f = 0.0          # EMA dikey sapma (-1 ust .. +1 alt)
        self.boyut_f = 0.0       # EMA bbox eksen orani max(w/W, h/H)
        self._had = False        # ilk kare EMA'siz alinir
        self._handoff_t = None   # gorsel faza giris ani (ilk hesapla tikinde damgalanir)
        self._tlm = {}

    # ------------------------------------------------------------------
    #  det: {cx,cy,w,h,conf,W,H,t} (piksel) -> (thr, pitch, roll, yaw) [-1..1]
    #  own_pitch_rad: KENDI IMU pitch'imiz (ego-motion telafisi; hedef verisi DEGIL)
    # ------------------------------------------------------------------
    def hesapla(self, det, own_pitch_rad=None):
        p = self.cfg
        W = float(det["W"]); H = float(det["H"])
        ex = (float(det["cx"]) - W / 2.0) / (W / 2.0)
        ey = (float(det["cy"]) - H / 2.0) / (H / 2.0)
        boyut = max(float(det["w"]) / W, float(det["h"]) / H)

        a = clamp(float(p.EMA), 0.0, 1.0)
        if self._had:
            self.ex_f = (1.0 - a) * self.ex_f + a * ex
            self.ey_f = (1.0 - a) * self.ey_f + a * ey
            self.boyut_f = (1.0 - a) * self.boyut_f + a * boyut
        else:
            self.ex_f, self.ey_f, self.boyut_f = ex, ey, boyut
            self._had = True

        # --- YUMUSAK GECIS RAMPASI (s: 0 -> 1) ---
        t_now = det.get("t")
        if self._handoff_t is None and t_now is not None:
            self._handoff_t = float(t_now)
        hs = float(p.HANDOFF_S)
        if hs <= 1e-6 or t_now is None or self._handoff_t is None:
            s = 1.0
        else:
            s = clamp((float(t_now) - self._handoff_t) / hs, 0.0, 1.0)

        # --- DIKEY NISAN (tilt geometrisi) ---
        nisan = clamp(float(p.DIKEY_NISAN), -1.0, 1.5)
        tan_v = math.tan(math.radians(float(p.VFOV_HALF_DEG)))
        ey_ref = (nisan * math.tan(math.radians(float(p.TILT_DEG))) / tan_v
                  if abs(tan_v) > 1e-9 else 0.0)

        # --- EGO-PITCH TELAFISI (kendi yatikligimizi dikey hatadan cikar) ---
        ey_ego = self.ey_f
        if own_pitch_rad is not None and abs(tan_v) > 1e-9:
            g = float(p.EGO_PITCH_GAIN)
            if g != 0.0:
                ey_ego = self.ey_f - g * math.tan(float(own_pitch_rad)) / tan_v

        # --- NISANDAN SAPMA CIZGISI ---
        ey_ref_eff = s * ey_ref                   # rampa: merkezden nisana kademeli kay
        eyy = ey_ego - ey_ref_eff
        r = math.hypot(self.ex_f, eyy)
        aci = math.degrees(math.atan2(-eyy, self.ex_f)) if r > 1e-9 else 0.0

        # --- KOMUTLAR ---
        yaw = clamp(float(p.SIGN_YAW) * float(p.K_YAW) * self.ex_f,
                    -float(p.YAW_MAX), float(p.YAW_MAX))
        thr = clamp(float(p.SIGN_DIKEY) * float(p.K_DIKEY) * (-eyy),
                    float(p.THR_DN), float(p.THR_UP))

        # ileri itki: once nisanla, sonra bas git
        kisma = clamp(1.0 - float(p.MERKEZ_FREN) * r, 0.0, 1.0)
        alcal = clamp(1.0 - float(p.ALCAL_FREN) * max(0.0, eyy),
                      float(p.ALCAL_TABAN), 1.0)
        ileri_cap = clamp(float(p.ILERI), 0.0, 1.0)
        kb = float(p.K_BOYUT)
        geri = max(0.0, float(p.GERI_MAX))
        ileri_istek = (clamp(kb * (float(p.BOYUT_HEDEF) - self.boyut_f), -geri, ileri_cap)
                       if kb > 0.0 else ileri_cap)
        # YAKLASMA-AGIRLIKLI FREN: iki fren CARPIMSAL bindiginde ileri itkiyi eziyor
        # ve hedefe hic yaklasilamiyordu. Frenler yalniz istasyon bandinda (istek
        # dusukken) devrede; UZAKTA (istek tavanda -> yak=1) baypas edilir.
        yak = clamp(ileri_istek / ileri_cap, 0.0, 1.0) if ileri_cap > 1e-6 else 0.0
        kisma_eff = yak + (1.0 - yak) * kisma
        alcal_eff = yak + (1.0 - yak) * alcal
        # rampa yalnizca ILERI (pozitif) itkiyi olcekler; geri kacis dokunulmaz
        pitch = float(p.PITCH_SIGN) * (max(ileri_istek, 0.0) * kisma_eff * alcal_eff * s
                                       + min(ileri_istek, 0.0))
        roll = 0.0

        self._tlm = {
            "ex": round(self.ex_f, 3), "ey": round(self.ey_f, 3),
            "ey_ego": round(ey_ego, 3), "ey_ref": round(ey_ref_eff, 3),
            "sapma": round(r, 3), "aci_deg": round(aci, 1),
            "boyut": round(self.boyut_f, 4),
            "kisma": round(kisma, 3), "alcal": round(alcal, 3), "yak": round(yak, 3),
            "handoff_s": round(s, 3),
            "thr": round(thr, 3), "pitch": round(pitch, 3), "yaw": round(yaw, 3),
        }
        return float(thr), float(pitch), float(roll), float(yaw)

    def durum(self):
        """Son tikin ic degerleri (konsol/tani icin; guduume GIRMEZ)."""
        return dict(self._tlm)

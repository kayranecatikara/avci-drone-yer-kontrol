# -*- coding: utf-8 -*-
"""Basit IBVS gorsel gudum: goruntu merkezinden bbox merkezine cizgi -> yaw/thr/ileri.
Ileri kanal bbox boyutunu hedefe surer (kilit-tut). Pose kanat uclarindan ongorulu yaw lead.
Girdi yalniz kamera verisi (bbox + pose keypoint) -> gorsel-faz GPS yasagina uygun."""
import math


def clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x


def kanat_roll_img(L, R, W, H):
    """Iki kanat ucu (normalize [u,v,conf]) -> goruntu-uzayi bank acisi (rad)."""
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
        self.boyut_f = 0.0           # EMA bbox eksen orani max(w/W,h/H)
        self._had = False            # ilk kare EMA'siz alinir
        # kapanma-hizi freni (TTC) durumu
        self._boyut_prev = 0.0
        self._t_prev = None
        self._dboyut_ema = 0.0
        self._dboyut_dt = 0.0        # yumusatilmis boyut hizi (fraction/s)
        self.roll_f = 0.0            # EMA hedef bank (ego-telafili, rad)
        self._roll_had = False
        self._roll_raw_deg = 0.0     # ham goruntu-roll (teshis)
        self._handoff_t = None       # gorsel faza giris ani (yumusak-gecis rampasi)
        self._tlm = {}               # son telemetri

    # Pose kanat uclarindan ongorulu yaw lead (rad). own_roll_rad: ego-motion telafisi.
    # Kapi dususe (0.0, False) -> saf IBVS.
    def _roll_lead(self, poz, W, H, p, own_roll_rad=None):
        if poz is None:
            return 0.0, False
        kp = poz.get("kp")
        if not kp or len(kp) < 3 or kp[1] is None or kp[2] is None:
            return 0.0, False
        L, R = kp[1], kp[2]                       # sol, sag kanat ucu [u,v,conf]
        if len(L) < 3 or len(R) < 3:
            return 0.0, False
        cmin = float(getattr(p, "IBVS_ROLL_CONF_MIN", 0.5))
        if float(L[2]) < cmin or float(R[2]) < cmin:
            return 0.0, False                     # kanat ucu guveni dusuk
        asp = poz.get("aspect_deg")               # yalniz PnP oturunca var
        if asp is not None and float(asp) < float(getattr(p, "IBVS_ASPECT_MIN", 120.0)):
            return 0.0, False                     # yandan/onden: kanat cizgisi bank'i temsil etmez
        roll_img = kanat_roll_img(L, R, float(W), float(H))
        self._roll_raw_deg = math.degrees(roll_img)
        # ego-motion telafisi: kendi roll'umuzu cikar
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

    # det: {cx,cy,w,h,conf,W,H,t} (piksel) -> (thr, pitch, roll, yaw) [-1..1]
    # poz: normalize keypoint dict (yaw lead) | None
    def hesapla(self, det, p, poz=None, own_roll_rad=None, own_pitch_rad=None):
        W = float(det["W"]); H = float(det["H"])
        ex = (float(det["cx"]) - W / 2.0) / (W / 2.0) if W > 1 else 0.0
        ey = (float(det["cy"]) - H / 2.0) / (H / 2.0) if H > 1 else 0.0
        # bbox eksen orani (kilit-tut ileri kanali girdisi)
        boyut = (max(float(det["w"]) / W, float(det["h"]) / H)
                 if (W > 1 and H > 1) else 0.0)
        a = clamp(float(p.VIS_EMA), 0.0, 1.0)
        if self._had:
            self.ex_f = (1.0 - a) * self.ex_f + a * ex
            self.ey_f = (1.0 - a) * self.ey_f + a * ey
            self.boyut_f = (1.0 - a) * self.boyut_f + a * boyut
        else:
            self.ex_f, self.ey_f, self.boyut_f = ex, ey, boyut
            self._had = True

        # kapanma-hizi (TTC): bbox buyume hizi dboyut/dt (EMA'li)
        t_now = det.get("t")
        if self._t_prev is not None and t_now is not None:
            dt_b = float(t_now) - self._t_prev
            if 0.0 < dt_b < 1.0:
                ham_hiz = (self.boyut_f - self._boyut_prev) / dt_b
                self._dboyut_ema = 0.7 * self._dboyut_ema + 0.3 * ham_hiz
                self._dboyut_dt = self._dboyut_ema
        self._boyut_prev = self.boyut_f
        if t_now is not None:
            self._t_prev = float(t_now)

        # yumusak-gecis (soft-handoff) rampasi s:0->1 (IBVS_HANDOFF_S sn) — GPS->gorsel
        # gecisinde ileri-itki + dikey-nisan kanallarini yumusatir. s=1 -> kapali.
        t_now = det.get("t")
        if self._handoff_t is None and t_now is not None:
            self._handoff_t = float(t_now)             # ilk gorsel tik: pencereyi baslat
        hs = float(getattr(p, "IBVS_HANDOFF_S", 0.0))
        if hs <= 1e-6 or t_now is None or self._handoff_t is None:
            s = 1.0
        else:
            s = clamp((float(t_now) - self._handoff_t) / hs, 0.0, 1.0)

        # dikey nisan (tilt-farkinda): ey_ref = NISAN*tan(TILT)/tan(VFOV_yari).
        # negatif NISAN = alttan vur (hedef merkez ustunde -> arac hedefin altinda).
        nisan = clamp(float(getattr(p, "IBVS_DIKEY_NISAN", 1.0)), -1.0, 1.5)
        tilt = math.radians(float(getattr(p, "IBVS_TILT_DEG", 25.0)))
        vfov_h = math.radians(float(getattr(p, "IBVS_VFOV_HALF_DEG", 47.2)))
        tan_v = math.tan(vfov_h)
        ey_ref = nisan * math.tan(tilt) / tan_v if abs(tan_v) > 1e-9 else 0.0

        # ego-pitch telafisi: dikey hatayi kendi pitch'imizden arindir
        #   ey_dunya = ey_f - GAIN * tan(own_pitch) / tan(VFOV_yari)
        ey_kul = self.ey_f
        if own_pitch_rad is not None:
            g = float(getattr(p, "IBVS_EGO_PITCH_GAIN", 1.0))
            if g != 0.0 and abs(tan_v) > 1e-9:
                ey_kul = self.ey_f - g * math.tan(float(own_pitch_rad)) / tan_v

        # nisan noktasindan bbox cizgisi. rampa: ey_ref_eff gecis boyunca 0'dan tam nisana kayar.
        ey_ref_eff = s * ey_ref
        eyy = ey_kul - ey_ref_eff                     # dikey sapma (nisana gore)
        r = math.hypot(self.ex_f, eyy)
        aci = math.degrees(math.atan2(-eyy, self.ex_f)) if r > 1e-9 else 0.0

        # ongorulu yaw lead (pose kanat uclarindan); kapi dususe lead=0
        lead, roll_ok = self._roll_lead(poz, W, H, p, own_roll_rad=own_roll_rad)

        # yakinlik-olcekli kazanc: k_yakin = 1 + YAKIN_KAZANC*clamp(boyut_f/BOYUT_HEDEF,0,2).
        # Yaklastikca artan acisal hiza uyar. 0 = kapali.
        yk_ref = float(getattr(p, "IBVS_BOYUT_HEDEF", 0.08))
        oran = clamp(self.boyut_f / yk_ref, 0.0, 2.0) if yk_ref > 1e-6 else 0.0
        k_yakin = 1.0 + float(getattr(p, "IBVS_YAKIN_KAZANC", 0.0)) * oran
        # yatay -> yaw, dikey sapma -> throttle
        yaw = clamp(float(p.IBVS_SIGN_YAW) * float(p.IBVS_K_YAW) * k_yakin * self.ex_f + lead,
                    -float(p.YAW_MAX), float(p.YAW_MAX))
        thr = clamp(float(p.IBVS_SIGN_DIKEY) * float(p.IBVS_K_DIKEY) * k_yakin * (-eyy),
                    float(p.THR_DN), float(p.THR_UP))
        # ileri itki: nisandan sapma buyudukce kisilir
        kisma = clamp(1.0 - float(p.IBVS_MERKEZ_FREN) * r, 0.0, 1.0)
        # alcalma freni (anti-lift-carry): hedef nisan altindaysa (eyy>0) ileri kisilir; tirman etkilenmez
        alcal = clamp(1.0 - float(getattr(p, "IBVS_ALCAL_FREN", 2.0)) * max(0.0, eyy),
                      float(getattr(p, "IBVS_ALCAL_TABAN", 0.2)), 1.0)
        # kilit-tut: ileri kanal boyut-reguleli P-yasa (uzakta tavan, hedef boyutta dur, yakinsa geri).
        # K_BOYUT<=0 -> regulasyon kapali (sabit-ileri).
        ileri_cap = clamp(float(p.IBVS_ILERI), 0.0, 1.0)
        kb = float(getattr(p, "IBVS_K_BOYUT", 0.0))
        hedef_boyut = float(getattr(p, "IBVS_BOYUT_HEDEF", 0.09))
        geri = max(0.0, float(getattr(p, "IBVS_GERI_MAX", 0.0)))
        ileri_istek = (clamp(kb * (hedef_boyut - self.boyut_f), -geri, ileri_cap)
                       if kb > 0.0 else ileri_cap)
        # kapanma-hizi freni (TTC): bbox hizli buyuyorsa ileri itkiyi onceden kis (yalniz buyurken)
        fren_hiz = float(getattr(p, "IBVS_FREN_HIZ", 0.0))
        if fren_hiz > 0.0:
            ileri_istek = clamp(ileri_istek - fren_hiz * max(0.0, self._dboyut_dt),
                                -geri, ileri_cap)
        # yaklasma-agirlikli fren: frenler yalniz kilit-tut bandinda (yak->0) devrede; uzakta (yak=1) kapali
        yak = clamp(ileri_istek / ileri_cap, 0.0, 1.0) if ileri_cap > 1e-6 else 0.0
        kisma_eff = yak + (1.0 - yak) * kisma
        alcal_eff = yak + (1.0 - yak) * alcal
        # rampa: yalniz pozitif ileri itki s ile olceklenir (gecis aninda lunge yok); geri-kacis dokunulmaz
        pitch = float(p.PITCH_SIGN) * (max(ileri_istek, 0.0) * kisma_eff * alcal_eff * s
                                       + min(ileri_istek, 0.0))
        roll = 0.0

        self._tlm = {
            "law": "IBVS",
            "ex": round(self.ex_f, 3), "ey": round(self.ey_f, 3),
            "ey_ref": round(ey_ref_eff, 3),   # dikey nisan (rampa sonrasi efektif)
            "ey_ref_hedef": round(ey_ref, 3), # tam nisan hedefi
            "handoff_s": round(s, 3),         # yumusak-gecis rampa faktoru (0=giris, 1=tamam)
            "ey_ego": round(ey_kul, 3),       # ego-pitch telafili dikey hata
            "buyukluk": round(r, 3),          # nisandan sapma
            "aci_deg": round(aci, 1),         # cizgi acisi
            "kisma": round(kisma, 3),         # merkez freni
            "alcal": round(alcal, 3),         # alcalma freni
            "yak": round(yak, 3),             # yaklasma agirligi (1=uzak, 0=hedefte)
            "k_yakin": round(k_yakin, 2),     # yakinlik-olcekli kazanc carpani
            "boyut": round(self.boyut_f, 4),
            "boyut_hedef": round(hedef_boyut, 3),
            "ileri_istek": round(ileri_istek, 3),
            "dboyut_dt": round(self._dboyut_dt, 4),   # bbox buyume hizi (fraction/s)
            "ttc_s": (round(self.boyut_f / self._dboyut_dt, 1)   # ~carpisma suresi (s)
                      if self._dboyut_dt > 1e-4 else None),
            "dikey": round(thr, 3), "ileri": round(pitch, 3), "yaw": round(yaw, 3),
            "roll_deg": round(math.degrees(self.roll_f), 1),  # hedef bank (ego-telafili)
            "roll_raw_deg": round(self._roll_raw_deg, 1),     # ham goruntu-roll
            "lead": round(lead, 3),           # yaw'a eklenen ongoru katkisi
            "roll_ok": bool(roll_ok),         # ongoru aktif mi
        }
        return float(thr), float(pitch), float(roll), float(yaw)

    # Telemetri (server okur; gudum girdisi degil)
    def durum(self):
        return dict(self._tlm)

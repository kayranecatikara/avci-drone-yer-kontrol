# -*- coding: utf-8 -*-
"""
================================================================================
 arac/kopru_alt.py — ALTERNATIF cevirici (YALNIZ SIMULASYON)
================================================================================
⚠ UCUSTA KULLANILMAZ. kopru/dow_kopru.py DOKUNULMADI; bu dosya onu ALT SINIF
  yapar ve YALNIZ iki seyi degistirir. Amac: denetimde olculen tek kusuru
  (yatay hiz dongusunun bant genisligi) izole edip simulatorde kanitlamak.

DENETIM BULGUSU (arac/kopru_denetim.py, 2026-08-16, 611192 tik canli log)
--------------------------------------------------------------------------------
ACIK DONGU TESIS KIMLIGI (veri/kopru_olcum_f2trim_{pitch,roll}, sabit cubuk):
    v_ss = K * stick      K = 91.0 (m/s)/stick   (0.15/0.20/0.30 basamaklari,
                                                  iki eksende de, RMS 0.3-0.7)
    tau_v = 2.28 s        (2.27 / 2.30 / 2.27 / 2.27 / 2.30 — cok tutarli)
    ic gecikme ~0.25 s    (olu zaman 0.046 + ivme tau 0.211)

KAPALI DONGU (mevcut kopru): stick = trim(v_sp) + KP_VH*e + i
    trim() tesisin DC tersidir (1/91) -> kalici hata YOK, dogru tasarim.
    Gecici tepki tamamen KP_VH'ye bagli:
        tau_kapali = tau_v / (1 + K*KP_VH) = 2.28 / (1 + 91*0.024) = 0.72 s
    Yani yatay hiz dongusu ~0.7 s'lik bir birinci mertebe sistem.

OLCULEN SONUC (canli, seyir tikleri):
    |yaw hizi| > 120 deg/s olan tiklerde (ucusun %5.1'i)
        yanal hiz hatasi |e_right| p50 = 9.18 m/s (p90 14.5)
        buna karsi uretilen roll   |roll| p50 = 0.31   (tavan 0.75)
    Cunku KP_VH*9.18 = 0.22 stick. Tavan DEGIL, KAZANC bagliyor.
    Mevcut kazancla 9.18 m/s'lik hatayi kapatmak ~0.7 s; ayni araca 0.75 roll
    verilse 0.24 s'de kapanirdi. Yatay dongu tesisin izin verdiginin ~3'te 1'i
    hizinda kosuyor.

BU DOSYADAKI IKI DEGISIKLIK
--------------------------------------------------------------------------------
 1) KP_VH 0.024 -> 0.070
        tau_kapali = 2.28 / (1 + 91*0.070) = 0.31 s   (2.3x hizli)
        Neden 0.070'te durduk: ic gecikme ~0.25 s. Kesim frekansi
        w_c ~ (1+K*Kp)/tau_v = 3.2 rad/s; 0.25 s gecikmenin oradaki faz kaybi
        46 deg -> faz payi ~44 deg. KP_VH=0.12'de w_c 5.2 rad/s, faz kaybi
        75 deg, pay ~15 deg — SALINIM riski. 0.07 kasitli olarak muhafazakar.
        Ayrica 0.070 * 10.7 m/s = 0.75 -> hata 10.7 m/s'yi asinca cubuk TAVANA
        oturur; hard-turn p90 hatasi (14.5) tam yetkiyi cagirir. Istenen bu.
 2) MAX_DELTA yalniz PITCH/ROLL icin 0.05 -> 0.15 (thr ve yaw 0.05'te KALIR)
        ⚠ ONCE BEKLENEN GEREKCE OLCUMLE CURUDU. "0.05 slew'i manevrada bagliyor"
        hipotezi YANLIS cikti: tezgahta MAX_DELTA'yi TEK BASINA 0.15 yapmak
        yanal basamak yukselme suresini 1.580 -> 1.560 s yapti (%1). KP_VH ile
        BIRLIKTE de katkisi kucuk: 1.040 -> 0.980 s (%6). Yani manevra icin
        gerekli DEGIL.
        GERCEK GEREKCE (gurultu tezgahi, olculen SDK hiz gurultusu sigma=0.30):
            KP_VH=0.070'te roll cubugunun tik-tik degisimi |diff| p95 = 0.062
            — yani 0.05 tavaninin USTUNDE. Kazanc buyuyunce olcum gurultusu
            tek basina hiz butcesinin tamamini yiyor; manevra geldiginde
            butce kalmiyor. 0.15 bu payi acar (gurultu 0.062'yi kullanir,
            manevraya 0.09 kalir).
        ⚠ throttle'a UYGULANMAZ: dikey kanal HIZ_KAYNAK="sonlu_fark" yuzunden
        gurultulu (thr_ham |diff| p90 = 0.127 stick). Orada MAX_DELTA=0.05
        gercekte gurultu filtresi gorevi goruyor (tiklerin %36.6'sinda bagliyor)
        ve KALDIRILMAMALI. yaw'da da 0.05 korunur (yaw kanalinda kusur bulunmadi).

DEGISMEYENLER (kasitli): trim tablosu, KI_VH, I_VH_MAX, E_VH_INT_BAND, tum
dikey kanal, tum yaw kanali, cerceve cevrimi, bayat mantigi. Denetimde bunlarin
hicbirinde olculebilir kusur BULUNMADI.
"""

from __future__ import annotations

from kopru.dow_kopru import Cfg as _Cfg, DowKopru, kirp, rate_limit


class CfgAlt(_Cfg):
    """Yalniz KP_VH degisir; MAX_DELTA_PR yeni bir alandir (taban sinif gormez)."""
    KP_VH = 0.070
    MAX_DELTA_PR = 0.15        # pitch/roll icin tik basina azami degisim
    # MAX_DELTA (0.05) taban siniftan aynen gelir -> thr ve yaw ONA baglidir.


class KopruAlt(DowKopru):
    """DowKopru + eksen basina hiz siniri. adim() HIC degismedi."""

    def __init__(self, sdk, cfg=CfgAlt):
        super().__init__(sdk, cfg=cfg)

    def _uygula(self, thr, pitch, roll, yaw):
        """dow_kopru._uygula ile ayni; tek fark pitch/roll'un ayri MAX_DELTA'si."""
        c = self.cfg
        d_pr = float(getattr(c, "MAX_DELTA_PR", c.MAX_DELTA))
        thr = rate_limit(thr, self._onceki["thr"], c.MAX_DELTA)
        pitch = rate_limit(pitch, self._onceki["pitch"], d_pr)
        roll = rate_limit(roll, self._onceki["roll"], d_pr)
        yaw = rate_limit(yaw, self._onceki["yaw"], c.MAX_DELTA)
        self._onceki = {"thr": thr, "pitch": pitch, "roll": roll, "yaw": yaw}
        self.sdk.set_control_surfaces(thr, pitch, roll, yaw, True)

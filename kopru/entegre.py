# -*- coding: utf-8 -*-
"""
kopru/entegre.py — YENI GUDUM HATTI'nin yer kontrol istasyonuna baglanmasi.

NE YAPAR: Gazebo'dan tasinan yasayi (control/guidance/gps_guidance.py, DEGISMEZ)
+ DoW koprusunu (kopru/dow_kopru.py) TEK bir nesne halinde paketler ve
AvciKontrol'un GPS fazinin yerine gecirilebilir hale getirir.

MIMARI (arayuz/gorsel faz BOZULMAZ):
    web/server.py  --50Hz-->  AvciKontrol.adim()
                                 |
                                 +-- GORSEL faz  -> eskisi gibi (IBVS, dokunulmadi)
                                 +-- GPS faz     -> BU MODUL:
                                        KopruGudum.adim()  ->  DowKopru.adim()
                                                                  ^
                                        gps_guidance thread (20Hz) |
                                        send_velocity -> set_hiz_ned

  * Yasa AYRI thread'de 20 Hz kosar ve yalnizca SETPOINT yazar.
  * Kopru, server'in 50 Hz kontrol dongusunde tiklenir (ayri thread YOK ->
    cift gonderim ve kilit cakismasi yok).
  * get_plane/get_iris koprunun kendi adaptorleri (cm->m, z-yukari->NED).

TEK GPS HATTI: eski ana_kontrol PD/standoff yasasi 2026-08-07'de SILINDI
(kullanici karari). Bu hat kurulamazsa arac UCMAZ (gurultulu hata + hover) —
sessizce baska bir yasaya dusmez.

YASA DEGERLERI DONDURULDU: gps_guidance.Cfg'ye dosyadan/setattr'dan
dokunulmaz. Onaylanmis TEK istisna V_MAX=22 ve olculerek turetilmis
RANGE_SET=6.9 / IC_KAYMA=0 — hepsi env uzerinden, import ONCESI verilir.
"""
from __future__ import annotations

import math
import os
import threading
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_KAYNAK = os.path.join(_HERE, "gazebo_kaynak")


class KopruGudum:
    """Yasa + kopru paketi. AvciKontrol GPS fazinda bunu tikler."""

    def __init__(self, drone, zemin_m=None, range_set=6.9, v_max=22.0,
                 ic_kayma=0.0, gnss_duzeltici=True, kalkis_agl=40.0,
                 hedef_truth=False, istasyon_elev=15.0):
        self.drone = drone
        self.hazir = False
        self.hata = None
        self._gg = None
        self._kopru = None
        self._th = None
        self._stop = threading.Event()
        self._zemin = zemin_m
        # HEDEF KAYNAGI — arayuzdeki kaynak secicisine bagli (AvciKontrol.kaynak):
        #   "gercek" -> hedef_truth=True : bozuk kanal HIC okunmaz, truth (index
        #               18-26) kullanilir, CT-EKF BAYPAS (kusursuz veri filtrelenmez).
        #               Faz 3 teshis kosularinin (U/V3) konfigurasyonu: menzil ~7-8 m.
        #   "v2"     -> hedef_truth=False: bozuk kanal + CT-EKF (yarisma-uyumlu).
        #               Kestirim hatasi ~10.6 m -> oturmus menzil ~39-44 m.
        # ⚠ Ikisi AYNI ucusu vermez; fark OLCULDU (2026-08-07: 7.1 m vs 39.0 m).
        self.hedef_truth = bool(hedef_truth)
        self._ayar = dict(range_set=range_set, v_max=v_max, ic_kayma=ic_kayma,
                          gnss=(gnss_duzeltici and not hedef_truth),
                          elev=istasyon_elev)
        # --- KALKIS (bloklamayan; eski ana_kontrol kalkis kapisinin yerine) ---
        # Eski kapi DUNYA-Z ile karsilastiriyordu (SEARCH_ALT=5000 cm); DoW spawn
        # zemini 4836 cm oldugundan fiilen HIC calismiyordu. Bu kapi AGL tabanli.
        self.kalkis_agl = float(kalkis_agl)
        self.kalkis_tamam = False
        self._kalkis_uyari = False

    # ── kurulum: yasa import'u env'e BAGLI oldugundan burada yapilir ──
    def _kur(self):
        import sys
        if _KAYNAK not in sys.path:
            sys.path.insert(0, _KAYNAK)
        # gps_guidance.Cfg env'i SINIF TANIMINDA okur -> import'tan ONCE set
        os.environ["AVCI_GPS_RANGE"] = str(self._ayar["range_set"])
        os.environ["AVCI_GPS_IC"] = str(self._ayar["ic_kayma"])
        os.environ["AVCI_GPS_ISTASYON_ELEV"] = str(self._ayar["elev"])
        import control.guidance.gps_guidance as gg
        from kopru import dow_kopru
        from kopru.dow_kopru import CM, Cfg as KCfg, DowKopru

        gg.send_velocity = dow_kopru.send_velocity      # TEK baglama noktasi
        setattr(gg.Cfg, "V_MAX", float(self._ayar["v_max"]))   # onayli istisna

        if self._zemin is None:                         # arac YERDE varsayimi
            self._zemin = self.drone.get_drone_altitude() / CM
        cfg = type("CfgEntegre", (KCfg,), {
            "YATAY_AKTIF": True,
            "NED_ZEMIN_M": float(self._zemin),
            "HEDEF_TRUTH_AKTIF": self.hedef_truth,
            "GNSS_DUZELTICI_AKTIF": bool(self._ayar["gnss"]),
        })
        self._gg = gg
        self._kopru = DowKopru(self.drone, cfg=cfg)
        self.hazir = True
        import math as _m
        _e = gg.Cfg.ISTASYON_ELEV_DEG
        print("[KOPRU-GUDUM] hazir: HEDEF=%s  RANGE_SET=%.1f ELEV=%.0f "
              "V_MAX=%.0f IC_KAYMA=%.0f zemin=%.1f m CT-EKF=%s"
              % ("GERCEK GPS (truth)" if self.hedef_truth else "BOZUK GPS",
                 gg.Cfg.RANGE_SET, _e, gg.Cfg.V_MAX, gg.Cfg.IC_KAYMA,
                 self._zemin, "ACIK" if self._ayar["gnss"] else "BAYPAS"))
        print("[KOPRU-GUDUM] istasyon: %.2f m ARKA + %.2f m ALT (hedefin altinda)"
              % (gg.Cfg.RANGE_SET * _m.cos(_m.radians(_e)),
                 gg.Cfg.RANGE_SET * _m.sin(_m.radians(_e))))
        if self.hedef_truth:
            print("[KOPRU-GUDUM] -> Faz 3 teshis konfigurasyonu (U/V3): "
                  "beklenen oturmus menzil ~7-8 m")
        else:
            print("[KOPRU-GUDUM] -> yarisma konfigurasyonu: kestirim hatasi ~10 m,"
                  " beklenen oturmus menzil ~39-44 m")

    def baslat(self):
        """Kopruyu kur (yasa thread'i KALKIS bitince baslar)."""
        try:
            if not self.hazir:
                self._kur()
        except Exception as e:                          # ASLA sessiz olme
            self.hata = repr(e)
            print("[KOPRU-GUDUM] KURULAMADI:", e)
            return False
        return True

    def _yasa_baslat(self):
        """gps_guidance thread'ini ayaga kaldir — YALNIZ kalkis bittikten sonra
        (kalkis tirmanisiyla yasanin hiz komutu cakismasin)."""
        if self._th is not None and self._th.is_alive():
            return
        self._stop.clear()
        self._th = threading.Thread(
            target=self._gg.run_gps_guidance,
            args=(self._kopru, self._kopru.get_plane, self._kopru.get_iris,
                  self._stop),
            daemon=True)
        self._th.start()

    # ── KALKIS: bloklamayan tek tik (server'in 50 Hz dongusunden) ──
    def _kalkis_tik(self):
        from kopru.dow_kopru import CM
        agl = self.drone.get_drone_altitude() / CM - self._zemin
        c = self._kopru.cfg
        if agl >= self.kalkis_agl - c.KALKIS_TOL_M:
            self.kalkis_tamam = True
            self._kopru.hover()                         # TRIM hover (thr=0 DEGIL)
            print("[KOPRU-GUDUM] kalkis TAMAM (AGL %.1f m) -> yasa devrede" % agl)
            self._yasa_baslat()
            return {"faz": "KALKIS_BITTI", "agl_m": agl}
        if not self._kalkis_uyari:
            print("[KOPRU-GUDUM] kalkis: AGL %.1f -> %.0f m (zemin %.1f)"
                  % (agl, self.kalkis_agl, self._zemin))
            self._kalkis_uyari = True
        self.drone.set_arm(True)
        self._kopru._uygula(c.KALKIS_THR, 0.0, 0.0, 0.0)   # duz tirman, seviye
        return {"faz": "KALKIS", "agl_m": agl}

    def durdur(self):
        self._stop.set()
        if self._th is not None:
            self._th.join(timeout=1.5)
            self._th = None

    # ── server'in 50 Hz dongusunden tiklenir ──
    def adim(self):
        """Bir tik ilerlet. Once KALKIS (AGL kapisi), sonra yasa+kopru.
        Donus: tani sozlugu | None (kurulamadi)."""
        if not self.hazir or self._kopru is None:
            return None
        if not self.kalkis_tamam:
            return self._kalkis_tik()
        return self._kopru.adim()

    def hover(self):
        if self._kopru is not None:
            self._kopru.hover()

    # ── arayuz/telemetri icin yasanin durumu ──
    def durum(self):
        """{'durum','d_h','menzil'} — gps_guidance.status'tan (salt okuma)."""
        if not self.kalkis_tamam:
            return {"durum": "KALKIS", "d_h": None, "menzil": None}
        if self._gg is None:
            return {}
        try:
            s = self._gg.status
            return {"durum": s.get("durum"), "d_h": s.get("d_h"),
                    "menzil": s.get("menzil")}
        except Exception:
            return {}

    @property
    def komut(self):
        """Koprunun uyguladigi son stick'ler (arayuz 'uygulanan komut' karti)."""
        if self._kopru is None:
            return None
        return dict(self._kopru._onceki)

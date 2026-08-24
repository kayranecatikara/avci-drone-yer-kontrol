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

# ── ZEMIN DATUMU KALICI KAYDI ───────────────────────────────────────────────
# Harita zemini SABIT bir fiziksel buyukluk; her gorevde yeniden olculmesi icin
# hicbir sebep yok. Yeniden olcum 11 Agu'da canli hataya yol acti (kopru kaynak
# degisiminde HAVADA kurulunca datum 48.4 -> 83.0 -> 92.3 m kaydi, yasa hedefi
# yer altinda gordu). Bir kez YERDE olculur, buraya yazilir, sonsuza kadar
# okunur. AVCI_ZEMIN_M env ile elle verilebilir (dosyayi da ezer).
_ZEMIN_DOSYA = os.path.join(_HERE, "zemin_datumu.txt")


def zemin_datumu_oku():
    """Kayitli zemin datumu (m) | None. Env > dosya onceligi."""
    e = os.environ.get("AVCI_ZEMIN_M", "").strip()
    if e:
        try:
            return float(e)
        except ValueError:
            pass
    try:
        with open(_ZEMIN_DOSYA, encoding="utf-8") as f:
            return float(f.read().split()[0])
    except Exception:
        return None


def zemin_datumu_yaz(z):
    """Olculen datumu kalici yaz (hata olursa sessiz gecme, bildir)."""
    try:
        with open(_ZEMIN_DOSYA, "w", encoding="utf-8") as f:
            f.write("%.3f\n" % float(z))
    except Exception as e:
        print("[KOPRU-GUDUM] zemin datumu diske YAZILAMADI: %r" % (e,))


class KopruGudum:
    """Yasa + kopru paketi. AvciKontrol GPS fazinda bunu tikler."""

    def __init__(self, drone, zemin_m=None, range_set=6.9, v_max=22.0,
                 ic_kayma=0.0, gnss_duzeltici=True, kalkis_agl=40.0,
                 hedef_truth=False, istasyon_elev=15.0, hibrit=False,
                 birebir=True, vmax_istisna=None, kayip_m=0):
        self.drone = drone
        # HIBRIT: Kayran'in supervisor'u (GPS <-> GORSEL faz dongusu).
        # VARSAYILAN KAPALI -> bugunku davranis (yalniz GPS fazi) bit-ayni kalir.
        # Acilinca run_gps_guidance yerine run_hybrid kosar; gorsel faz
        # tespit_akisi'ndan beslenir (bkz. kopru/tespit_akisi.py).
        self.hibrit = bool(hibrit)
        self.tespit = None          # TespitAkisi (hibritte kurulur)
        self._bi = self._sup = None
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
        # ── BIREBIR (2026-08-10, kullanici karari) ────────────────────────────
        # Kullanici: "yeni yaptigim gps gudumu ve gorsel gudumu karistirmissin,
        # aynen birebir olmasi lazim". HAKLI: yasa DOSYALARI klonla birebir
        # (hash dogrulandi) ama calisma aninda 5 sabiti eziyorduk:
        #     RANGE_SET 8.0->6.9 | ISTASYON_ELEV 15->25 | IC_KAYMA 14->0
        #     V_MAX 18->22       | ELEV_DINAMIK True->False
        # Bu dortlu ESKI yasa icin olculup onaylanmisti (kopru/README.md B.7);
        # yeni yasa gelince dusurulmesi gerekirken tasindi, ustune ELEV_DINAMIK
        # kapatildi. Sonuc: kosan sey kullanicinin yasasi DEGILDI.
        # birebir=True -> HICBIR yasa degeri ezilmez; yasa yazildigi gibi kosar.
        # birebir=False -> eski onayli ezmeler geri gelir (kaybolmadi, A/B icin).
        self.birebir = bool(birebir)
        # V_MAX TEK ISTISNA KANCASI (kapali=None). Olcum: DoW hedefi zamanin
        # %62-66'sinda 18 m/s USTUNDE (ort 18.2-18.4, tepe 20.8-26.1). Yasanin
        # kendi V_MAX'i 18 -> birebirde arac hedeften yavas kalir, istasyon
        # tutulamaz. Bu bir AYAR tercihi degil platform farki (DoW hedefi
        # Gazebo'dakinden hizli). Gerekirse vmax_istisna=22.0 ile acilir.
        self.vmax_istisna = None if vmax_istisna is None else float(vmax_istisna)
        self.kayip_m = int(kayip_m or 0)   # 0 = yasanin kendi degeri
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
        # gps_guidance.Cfg env'i SINIF TANIMINDA okur -> import'tan ONCE set.
        # BIREBIR kipinde HICBIRI set EDILMEZ: yasa kendi degerleriyle kosar.
        if not self.birebir:
            os.environ["AVCI_GPS_RANGE"] = str(self._ayar["range_set"])
            os.environ["AVCI_GPS_IC"] = str(self._ayar["ic_kayma"])
            os.environ["AVCI_GPS_ISTASYON_ELEV"] = str(self._ayar["elev"])
        else:
            for _k in ("AVCI_GPS_RANGE", "AVCI_GPS_IC", "AVCI_GPS_ISTASYON_ELEV",
                       "AVCI_GPS_ELEV_DIN"):
                os.environ.pop(_k, None)     # onceki kosudan kalinti kalmasin
        # ── DINAMIK ISTASYON YUKSELISI: SIMDILIK KAPALI (2026-08-09) ──
        # Kayran'in yeni gps_guidance'i istasyon yukselisini gövde pitch'inden
        # tureten bir kip getiriyor (elev = 25° + pitch, varsayilan ACIK) --
        # kamera gövdeye vidali oldugu icin sabit aci hedefi kadrajda tutmuyor.
        # BIZDE OLCULDU (ucus logu 113105, 31164 seyir tiki): govde pitch seyirde
        # ort -13.3° (burun asagi) -> dinamik kip elev'i 25° -> ~11.8°'ye indirir,
        # yani dikey ayrim 2.92 m -> 1.41 m'ye DUSER. Kullanici dikey ayrimi
        # bilerek 25°'ye cekmisti (W kosusu). Kadraj hatasi olcumu de var:
        # hedef merkezin ort +7.6° ustunde oturuyor -- dinamik kip bunu duzeltir.
        # IKISI KARSIT; hangisinin daha degerli oldugu UCUSLA belli olur.
        # Gorsel faz yeni geliyor; ayni anda GPS geometrisini de oynatmak
        # bozulma halinde hangisi oldugunu bilinmez kilar -> once KAPALI,
        # sonra tek degiskenli A/B (AVCI_GPS_ELEV_DIN=1).
        if not self.birebir:
            os.environ.setdefault("AVCI_GPS_ELEV_DIN", "0")
        import control.guidance.gps_guidance as gg
        from kopru import dow_kopru
        from kopru.dow_kopru import CM, Cfg as KCfg, DowKopru

        gg.send_velocity = dow_kopru.send_velocity      # TEK baglama noktasi

        # ── YENI YASA (dow/amir.py) BAGLAMASI (2026-08-24) ──────────────
        # amir.py de send_velocity'yi KENDI isim alaninda tutuyor; buraya
        # baglanmazsa iki faz da araca hicbir komut gondermez ve arac
        # SESSIZCE havada asili kalir (en kotu bozulma turu). amir.py bu
        # durumda RuntimeError atiyor ama baglamak yine de BURASININ isi.
        if os.environ.get("AVCI_YASA", "dow").strip().lower() == "dow":
            try:
                _DEPO = os.path.abspath(os.path.join(
                    os.path.dirname(os.path.abspath(__file__)), ".."))
                if _DEPO not in sys.path:
                    sys.path.insert(0, _DEPO)
                from dow import amir as _amir
                _amir.send_velocity = dow_kopru.send_velocity
                print("[KOPRU-GUDUM] YENI YASA bagli: dow/gps.py + dow/ibvs.py "
                      "(eskiye donus: AVCI_YASA=eski)")
            except Exception as _e:
                raise RuntimeError(
                    "[KOPRU-GUDUM] dow/amir.py baglanamadi: %r — yanlis "
                    "konfigle ucmaktansa durmak yeglenir" % (_e,))

        # ⛔ 2026-08-13 CANLI YAKALANAN AGIR HATA — ENV TEK BASINA YETMEZ.
        # gg.Cfg env'i SINIF TANIMINDA okur. Yukaridaki env yazimlari yalnizca
        # gps_guidance HENUZ IMPORT EDILMEMISSE ise yarar. Ama modul, gorev
        # baslamadan once BASKA bir yoldan cekilebiliyor:
        #     kopru/gorsel_ozellikler.py (panel) -> control.guidance.supervisor
        #     supervisor.py:23-24        -> control.guidance.gps_guidance
        # Panel bir kez sorgulanirsa (arayuz Tune'u acmak yeter) Cfg HAM
        # VARSAYILANLARLA kurulur ve sonraki env yazimlari ETKISIZ kalir.
        # CANLI KANIT (bu hatanin yakalandigi kosu): konsol
        #     "RANGE_SET=8.0 ELEV=15 IC_KAYMA=14 ELEV_DIN=True"
        # yazdi; olmasi gereken 6.9 / 25 / 0 / False idi. Arac yanlis
        # konfigurasyonla ucuyordu (kullanicinin daha once "bu benim GPS'im
        # degil" dedigi durumun ayni tekrari).
        # COZUM: import SONRASI degerleri ACIKCA setattr et — import sirasindan
        # BAGIMSIZ. env yazimi (yukarida) yine duruyor: alt-surecler ve
        # kosu scriptleri icin gecerli yol o.
        if not self.birebir:
            for _ad, _dg in (("RANGE_SET", float(self._ayar["range_set"])),
                             ("IC_KAYMA", float(self._ayar["ic_kayma"])),
                             ("ISTASYON_ELEV_DEG", float(self._ayar["elev"])),
                             ("ELEV_DINAMIK", False),
                             ("V_MAX", float(self._ayar["v_max"]))):
                setattr(gg.Cfg, _ad, _dg)
        elif self.vmax_istisna is not None:
            setattr(gg.Cfg, "V_MAX", self.vmax_istisna)   # tek acik istisna

        # DOGRULAMA: zorlananlar gercekten oturdu mu? Oturmadiysa SESSIZ KALMA.
        if not self.birebir:
            _bek = {"RANGE_SET": float(self._ayar["range_set"]),
                    "IC_KAYMA": float(self._ayar["ic_kayma"]),
                    "ISTASYON_ELEV_DEG": float(self._ayar["elev"]),
                    "V_MAX": float(self._ayar["v_max"])}
            _sapan = {k: (getattr(gg.Cfg, k), v) for k, v in _bek.items()
                      if abs(float(getattr(gg.Cfg, k)) - v) > 1e-6}
            if _sapan or getattr(gg.Cfg, "ELEV_DINAMIK", False):
                raise RuntimeError(
                    "[KOPRU-GUDUM] YASA KONFIGURASYONU OTURMADI: %s ELEV_DIN=%s "
                    "— ucus IPTAL (yanlis konfigle ucmaktansa durmak yeglenir)"
                    % (_sapan, getattr(gg.Cfg, "ELEV_DINAMIK", "?")))

        # ── HIBRIT (GPS <-> GORSEL) ICIN IKINCI BAGLAMA ──
        # bbox_ibvs, send_velocity'yi KENDI modul isim alanina import ediyor
        # (`from control.guidance.common import ... send_velocity ...`), yani
        # gps_guidance'i yamamak ONU KAPSAMAZ. Ayrica yamanmazsa gorsel faz
        # MAVLink'e komut gondermeye calisir ve DoW'da sessizce hicbir sey
        # olmaz -- en kotu bozulma turu. O yuzden burada ACIKCA baglaniyor.
        if self.hibrit:
            import control.guidance.bbox_ibvs as bi
            import control.guidance.supervisor as sup
            bi.send_velocity = dow_kopru.send_velocity
            self._bi, self._sup = bi, sup
            # GORSEL FAZ KAYIP ESIGI — yasa dosyasina DOKUNMADAN, calisma aninda.
            # Gerekce + olcum: guidance/ana_kontrol.Cfg.KOPRU_KAYIP_M yorumunda.
            if self.kayip_m:
                try:
                    _eski = int(sup.SupCfg.KAYIP_M)
                    sup.SupCfg.KAYIP_M = int(self.kayip_m)
                    print("[KOPRU-GUDUM] gorsel faz kayip esigi: %d -> %d kare "
                          "(~%.1f s @15 FPS)" % (_eski, self.kayip_m, self.kayip_m / 15.0))
                except Exception as e:
                    print("[KOPRU-GUDUM] kayip esigi uygulanamadi: %r" % (e,))

        # ── ZEMIN DATUMU (2026-08-11: CANLI YAKALANAN AGIR HATA) ────────────
        # ESKIDEN: zemin her kurulumda o anki irtifadan olculuyordu ("arac YERDE
        # varsayimi"). Kaynak degistirilince (set_kaynak) kopru YIKILIP yeniden
        # kuruluyor -- ve o an arac HAVADA oluyor. Canli kanit (11 Agu konsolu):
        #     zemin=48.4 m  (ilk kurulum, arac yerde -> DOGRU)
        #     zemin=83.0 m  (ikinci kurulum, arac havada)
        #     zemin=92.3 m  (ucuncu kurulum, daha yukarida)
        # Sonuc: tum NED dusey cercevesi ~44 m kaydi. Yasa hedefi YER ALTINDA
        # gordu (tgt_z=+7.06), istasyonu hedefin 15 m USTUNE kurdu, arac hedefin
        # 14.5 m ustunde ucup kadraji 79 derece kacirdi. Ayrica kalkis_tamam
        # sifirlandigi icin her kurulumda 40 m DAHA tirmandi.
        # SIMDI: datum dışarıdan verilirse AYNEN kullanilir (ana_kontrol onu
        # gorevler/kaynak degisimleri boyunca saklar); verilmediyse ancak arac
        # GERCEKTEN yerdeyse olculur. Havadayken olcum REDDEDILIR -- sessizce
        # yanlis datum kurmaktansa gurultulu hata verip ucusu durdurmak yegdir.
        if self._zemin is None:
            self._zemin = zemin_datumu_oku()        # diskte kayitli mi
            if self._zemin is not None:
                print("[KOPRU-GUDUM] zemin datumu DISKTEN: %.1f m (%s)"
                      % (self._zemin, _ZEMIN_DOSYA))
        if self._zemin is None:
            alt = self.drone.get_drone_altitude() / CM
            hiz = 0.0
            try:
                v = self.drone.get_telemetry()["drone"]["velocity"]
                hiz = math.sqrt(sum((x / CM) ** 2 for x in v))
            except Exception:
                pass
            if hiz > 2.0:                       # havada suzuluyor -> datum GUVENSIZ
                raise RuntimeError(
                    "ZEMIN DATUMU OLCULEMEZ: arac havada (irtifa %.1f m, hiz %.1f m/s) "
                    "ve diskte kayit yok. Gorevi arac YERDEYKEN baslat, ya da "
                    "AVCI_ZEMIN_M=<metre> ile acikca ver." % (alt, hiz))
            self._zemin = alt
            zemin_datumu_yaz(alt)
            print("[KOPRU-GUDUM] zemin datumu OLCULDU: %.1f m (arac yerde, hiz %.1f m/s) "
                  "-> diske yazildi" % (alt, hiz))
        else:
            print("[KOPRU-GUDUM] zemin datumu KORUNDU: %.1f m (yeniden olculmedi)"
                  % self._zemin)
        cfg = type("CfgEntegre", (KCfg,), {
            "YATAY_AKTIF": True,
            "NED_ZEMIN_M": float(self._zemin),
            "HEDEF_TRUTH_AKTIF": self.hedef_truth,
            "GNSS_DUZELTICI_AKTIF": bool(self._ayar["gnss"]),
        })
        self._gg = gg
        self._kopru = DowKopru(self.drone, cfg=cfg)
        if self.hibrit:
            from kopru.tespit_akisi import TespitAkisi
            self.tespit = TespitAkisi()
        self.hazir = True
        import math as _m
        _e = gg.Cfg.ISTASYON_ELEV_DEG
        print("[KOPRU-GUDUM] YASA KIPI: %s"
              % ("BIREBIR (yasa kendi degerleriyle kosuyor%s)"
                 % ("" if self.vmax_istisna is None
                    else "; TEK istisna V_MAX=%.0f" % self.vmax_istisna)
                 if self.birebir else "EZILMIS (eski onayli sabitler zorlaniyor)"))
        print("[KOPRU-GUDUM] hazir: HEDEF=%s  RANGE_SET=%.1f ELEV=%.0f "
              "V_MAX=%.0f IC_KAYMA=%.0f ELEV_DIN=%s zemin=%.1f m CT-EKF=%s"
              % ("GERCEK GPS (truth)" if self.hedef_truth else "BOZUK GPS",
                 gg.Cfg.RANGE_SET, _e, gg.Cfg.V_MAX, gg.Cfg.IC_KAYMA,
                 getattr(gg.Cfg, "ELEV_DINAMIK", "?"),
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
        if self.hibrit:
            # get_temas=None: DoW'da carpma sensoru YOK; oyun hedefe carpinca
            # "mission complete" yaziyor (kullanici bildirdi). Yasa temassiz
            # calisir -- vurus mandali olmaz, faz kayip/stop ile biter.
            # get_plane_truth/get_menzil/get_gercek KASITEN None: bunlar yalniz
            # ARSIV visual_lead icin; bbox yasasi onlari zaten almiyor (D0).
            hedef = self._sup.run_hybrid
            args = (self._kopru, self._kopru.get_plane, self._kopru.get_iris,
                    self.tespit.bekle, None, self._stop)
        else:
            hedef = self._gg.run_gps_guidance
            args = (self._kopru, self._kopru.get_plane, self._kopru.get_iris,
                    self._stop)
        self._th = threading.Thread(target=hedef, args=args, daemon=True)
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
        # Kopruye HANGI FAZDA oldugumuzu bildir. Yalniz bayatlik esigi secimine
        # girer (GORSEL yasa kare-guduumlu, komut araligi p99 1.23 s olculdu);
        # komut/kontrol yolu DEGISMEZ, GPS fazinda davranis bit-ayni kalir.
        if self.hibrit and self._sup is not None:
            try:
                self._kopru.gorsel_faz = (self._sup.status.get("faz") == "VISUAL")
            except Exception:
                self._kopru.gorsel_faz = False
        return self._kopru.adim()
        # Tani logunun kuyrugu diske insin: yazici thread 250 satir
        # birikmeden yazmiyor (50 Hz'de ~5 s). Kapatmadan cagrilmazsa
        # her gorevin SON 0-5 saniyesi kayboluyordu -- logun var olus
        # sebebi olan carpisma/kopma anini tam orada kaybediyorduk.
        try:
            if self._kopru is not None:
                self._kopru.tani_log_kapat()
        except Exception:
            pass

    def hover(self):
        if self._kopru is not None:
            self._kopru.hover()

    # ── arayuz/telemetri icin yasanin durumu ──
    def faz(self):
        """Hibrit faz durumu (arayuz/telemetri icin; salt gozlem)."""
        if not (self.hibrit and self._sup):
            return {"faz": "GPS", "gecis_sayisi": 0, "kilit_sayac": 0,
                    "son_sebep": None, "hibrit": False}
        d = dict(self._sup.status)
        d["hibrit"] = True
        if self.tespit is not None:
            d["akis"] = self.tespit.olcum()
        return d

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

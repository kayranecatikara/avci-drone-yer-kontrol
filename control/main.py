# -*- coding: utf-8 -*-
"""
control/main.py — FAZ GOZETMENI (yalnizca faz gecisi).

Bu dosyada GUDUM YOKTUR, DONGU YOKTUR, GIRIS NOKTASI YOKTUR. Ne komut uretir,
ne komut gonderir, ne de kendi basina calisir. Tek isi su soruyu yanitlamaktir:

    "Su anda GPS fazinda mi, GORSEL fazda mi olmaliyiz?"

KOSTURUCU `web/server.py`'dir (yer kontrol arayuzu, hibrit mod). Dongu,
telemetri, kamera hatti ve komut gonderimi orada; KAPILAR burada. Ayirmanin
sebebi: kapi esikleri (HANDOFF_FRAMES, HANDOFF_STATION_ERR_M, LOST_S...) OLCULMUS
degerlerdir ve tek bir yerde durmalidir — kosturucu degisince kapinin da
degismesi, kardes depoda faz cirpinmasinin kok nedeniydi.

FAZ AKISI
    GPS (kalkis + istasyon) -> (devir kapisi) -> GORSEL -> (kayip) -> GPS ...

DEVIR KAPISI (GPS -> GORSEL). Iki kosul BIRLIKTE saglanmalidir:
  1) GORSEL KILIT — kesintisiz olarak HEM en az HANDOFF_LOCK_S saniye HEM de
     en az HANDOFF_FRAMES ayri karede guduume girebilecek kutu
     (control.visual_tracking.aim_box; gorsel fazin KULLANDIGI kapinin
     AYNISI. Ayri esik yazmak iki katmani ayristirir ve devirden hemen sonra
     "kayip" verip faz sekmesine yol acar).
     ⭐ Sure sarti, kapinin DEDEKTOR HIZINA gore sessizce zayiflamasini
       engeller; kare sarti, DONMUS kamerada surenin kendi kendine dolmasini.
       Ikisi de gerekli — bkz. visual_tracking.Cfg.HANDOFF_LOCK_S.
  2) ISTASYONA OTURMA — GPS istasyon hatasi HANDOFF_STATION_ERR_M altinda VE hedefe
     menzil HANDOFF_RANGE_M altinda, ard arda HANDOFF_STATION_TICKS tik boyunca.
     (Hedef GNSS'i bayatsa menzil zaten bilinemez -> bu kosul duser, kutu
     kapisi tek basina yeter.)

  ⛔ 2. KOSUL HEDEFIN GPS'INI OKUR ve bu MESRUDUR: bir FAZ GECISI kapisidir,
    GUDUM YASASI DEGILDIR — gorsel temas HENUZ YOKTUR. Gorsel faz basladiktan
    sonra hedefin GPS'i komuta HIC girmez; gozetmen gorsel fazda hedefe ait
    TEK BIR sayiyi bile okumaz (bkz. `visual_tick` imzasi: yalnizca kutu var mi
    yok mu). Kamera-tek kapiya dusmek icin `Cfg.CAMERA_ONLY_GATE = True`
    yapilir; o zaman 2. kosul YAPISAL olarak devre disi kalir.

  NEDEN 2. KOSUL VAR (olculdu, kardes depo): kamera kapisi tek basina
  YAKLASMA sirasinda, arac daha oturmadan atesliyordu — devir 22.7 m'de,
  14.9 s'de, istasyon hatasi hala 34.6 m. "Otur, SONRA devret" hic
  gerceklesmiyordu.

GORSEL FAZDA GPS KOMUTA GIRMEZ (yarisma kurali; aksi diskalifiye). Yapisal
garanti `control.visual_tracking.VisualTracker.compute` imzasindadir: hedefe ait
tek veri bbox pikselleridir. Kosturucunun gorsel fazda cagirmasi mesru olan
tek GPS islevi `GPSTracker.clean_target()`'dir ve donen deger HICBIR KOMUTA
GIRMEZ (faz geri donerse filtre isinmis olsun diyedir).
"""
import time

from control.visual_tracking import Cfg as VisualCfg, is_stale, aim_box
from perception import detection_state


class Cfg:
    # --- DEVIR KAPISI ---
    CAMERA_ONLY_GATE = False     # True -> devir YALNIZ kamera kapisiyla (asagidaki
                                 #  GPS kosulu YAPISAL olarak calismaz)
    HANDOFF_RANGE_M = 15.0       # m; hedefe GPS menzili (dedektor menzile siddetle
                                 #  bagli: ~14 m'de ham tespit %88-97, 40 m'de %50,
                                 #  70 m'de %33 — olculdu, n=2097 istasyon karesi)
    HANDOFF_STATION_ERR_M = 8.0  # m; istasyon hatasi bunun altindaysa "oturdu"
    HANDOFF_STATION_TICKS = 25   # ard arda tik (~0.5 s) oturmus kalmali
    GPS_STALE_S = 2.0            # s; hedef GNSS paketi bundan eskiyse "bayat"

    # --- GORSEL FAZDAN DONUS ---
    # LOST_FRAMES(20) / dedektor ~10 Hz = 2 s. Sure cinsinden yazildi ki kamera
    # thread'i DONARSA da tetiklensin (donmus kamerada kare sayaci ilerlemez,
    # kare temelli sayac sonsuza kadar beklerdi).
    LOST_S = 2.0


class PhaseSupervisor:
    """GPS <-> GORSEL faz kapisi. Durumsuz degildir (sayaclari tutar) ama
    KOMUT URETMEZ; kosturucu her tik ilgili fazin `*_tick` islevini cagirir.

    Tipik kullanim (kosturucu tarafinda):

        det, seq = goz.read_detection(t)
        if goz.faz == goz.GPS:
            gps.step()
            if goz.gps_tick(t, det, seq, takeoff_done=..., station_err=...,
                           range_h=..., last_raw=...):
                gorsel.reset()                  # devir oldu
        else:
            kutu = gorsel.box(det, own_att, t)
            ...komutu gonder...
            if goz.visual_tick(t, det, seq, box_ok=(kutu is not None)):
                gorsel.reset()                  # hedef kayip, GPS'e donuldu
    """

    GPS = "GPS"
    VISUAL = "VISUAL"

    def __init__(self, cfg=Cfg, visual_cfg=VisualCfg):
        self.cfg = cfg
        self.visual_cfg = visual_cfg
        self.reset()

    def reset(self):
        """Yeni gorev: faz ve TUM sayaclar basa doner."""
        self.phase = self.GPS
        self.handoff_count = 0
        self._lock = 0           # ard arda GECERLI kare (tik degil)
        self._lock_since = None  # kesintisiz kanit zincirinin BASLANGIC damgasi
        self._last_frame_t = None  # son YENI karenin damgasi (donmus kamera tespiti)
        self._last_seq = None    # sayaca islenmis son kare no
        self._station_ticks = 0  # ard arda "istasyona oturmus" tik
        self._last_valid_t = None
        self._last_raw = None
        self._last_packet_t = None
        self._message = ""  # son faz gecisinin insan okur aciklamasi

    # ================================================================
    #  GIRDI OKUMA
    # ================================================================
    def read_detection(self, t=None):
        """detection_state'ten guduume GIREBILECEK tespiti oku -> (det, seq).

        `seq` kamera thread'inin KARE sayacidir; DEDUP icin gerekir. Dongu
        50 Hz, dedektor 8-10 Hz -> ayni kayit 5-6 tik boyunca dondurulur.
        Sayan taraf tik ile kareyi ayirt etmezse "ard arda N kare" sarti
        fiilen "ard arda N tik" olur (N=10 icin 0.2 s), yani kapi TEK
        tespitle acilir. Kardes depoda olculen cirpinmanin kok nedeni tam
        olarak buydu: 190 s'de 6-12 faz degisimi, gorsel faz omru medyan
        3.6-5.2 s.

        Kapi TEK YERDEDIR: `aim_box`. Gorsel faz da AYNISINI kullanir.
        """
        t = time.perf_counter() if t is None else t
        det, seq, _ = detection_state.status()
        if is_stale(det, self.visual_cfg, now=t):
            return None, seq
        return aim_box(det, self.visual_cfg), seq

    # ----------------------------------------------------------------
    def _track_packet(self, last_raw, t):
        """YENI ham GNSS paketi geldiyse zaman damgasini tazele. HER FAZDA
        calisir: gorsel fazda da filtre beslendiginden kesinti izlemesi
        kesintisiz surer (faz geri donunce 'bayat' bayragi gercegi gostersin).
        """
        if last_raw is not None and last_raw != self._last_raw:
            self._last_raw = last_raw
            self._last_packet_t = t

    def gnss_stale(self, t=None):
        """Hedef GNSS paketi GPS_STALE_S'ten eski mi? (yalniz kapi ve gosterge)"""
        if self._last_packet_t is None:
            return False
        t = time.perf_counter() if t is None else t
        return (t - self._last_packet_t) > self.cfg.GPS_STALE_S

    def _process_frame(self, t, det, seq):
        """Kanit zincirini surdur: SURE damgasi + AYRI KARE sayaci.

        Sayac YALNIZ YENI karede ilerler (tik degil, KARE) — dongu 50 Hz,
        dedektor cok daha yavas oldugundan ayni kayit onlarca tik boyunca
        dondurulur ve tik saymak kapiyi tek tespitle acardi.

        ⚠ ZINCIR KIRILMASI (det is None) AYNI KAREDE DE SIFIRLAR. `det`,
          `read_detection`'da `is_stale` suzgecinden gecmistir: ayni `seq`
          uzerinde None'a donmesi "kutu BAYATLADI" demektir, yani kanit
          gercekten bitmistir. Bunu `seq` esitligine takilip atlarsak, donmus
          bir kamerada zincir hic kirilmaz ve sure kapisi kendi kendine dolar.

        ⛔ KARE ILERLEMESI DE SART (yapisal, cagirana guvenmez). Kamera thread'i
          donarsa `seq` durur ama DUVAR SAATI ilerler; kare tabani o ana kadar
          dolmussa saf sure kapisi DONMUS bir goruntuyle acilirdi (olculdu:
          53 Hz'de 0.20 s'de donan kamera kapiyi 1.00 s'de aciyordu). Bu yuzden
          "son YENI kareden beri gecen sure > STALE_S" zinciri kirar. Esik
          bilerek `STALE_S`'tir: gorsel fazin "bu kutu artik guduume giremez"
          dedigi ayni andir — iki katmanda iki ayri esik olmaz.
        """
        if (self._last_frame_t is not None
                and (t - self._last_frame_t) > self.visual_cfg.STALE_S):
            self._lock = 0
            self._lock_since = None
        if det is None:
            self._lock = 0
            self._lock_since = None
            self._last_seq = seq
            return
        self._last_valid_t = t
        if seq == self._last_seq:
            return  # ayni kare, zaten sayildi
        self._last_seq = seq
        self._last_frame_t = t
        if self._lock_since is None:
            self._lock_since = t
        self._lock += 1

    def _lock_s(self, t):
        """Kesintisiz gorsel kanit suresi (s)."""
        return 0.0 if self._lock_since is None else (t - self._lock_since)

    def _is_locked(self, t):
        """Gorsel kilit kuruldu mu? SURE **VE** KARE sarti birlikte.

        Fiili kapi = max(HANDOFF_LOCK_S, HANDOFF_FRAMES / dedektor_hizi).
        Gerekce ve olculmus hiz-kapi tablosu:
        control/visual_tracking.py :: Cfg.HANDOFF_LOCK_S.
        """
        if self._lock_since is None:
            return False
        if self._lock < self.visual_cfg.HANDOFF_FRAMES:
            return False
        return self._lock_s(t) >= self.visual_cfg.HANDOFF_LOCK_S

    def _is_settled(self, t, station_err, range_h):
        """Arac istasyona OTURDU ve hedefe devir menzilinde mi?

        ⛔ HEDEFIN GPS'INI OKUR — yalnizca GPS fazinda, gorsel temas YOKKEN
          cagrilir; bir faz gecisi kapisidir, guduum yasasi degildir.
          `Cfg.CAMERA_ONLY_GATE` ile tamamen devre disi birakilabilir.
        """
        if self.cfg.CAMERA_ONLY_GATE:
            return True  # kapi yalnizca kamera kutusuna baksin
        if self.gnss_stale(t):
            return True  # menzil bilinemez -> kutu kapisi yeter
        if station_err is None or range_h is None:
            self._station_ticks = 0
            return False
        if (station_err <= self.cfg.HANDOFF_STATION_ERR_M
                and range_h <= self.cfg.HANDOFF_RANGE_M):
            self._station_ticks += 1
        else:
            self._station_ticks = 0
        return self._station_ticks >= self.cfg.HANDOFF_STATION_TICKS

    # ================================================================
    #  KAPILAR
    # ================================================================
    def gps_tick(self, t, det, seq, takeoff_done=True, station_err=None, range_h=None,
                 last_raw=None):
        """GPS fazinda bir tik islenir. GORSEL faza gecildiyse True doner.

        det, seq  : `read_detection` ciktisi
        takeoff_done, station_err, range_h, last_raw : GPSTracker'in DURUM alanlari
                    (guduum degil gosterge/kapi verisi; gorsel temas YOK)
        """
        self._track_packet(last_raw, t)
        self._process_frame(t, det, seq)
        # ⚠ `_is_settled` HER tik cagrilir (kisa devre YOK): icindeki oturma
        #   sayaci ancak her tik islenirse "ard arda HANDOFF_STATION_TICKS" anlamina
        #   gelir. Kilit sartinin arkasina saklanirsa sayac kilit acilana
        #   kadar hic islemez ve kapi 0.5 s GECIKIR.
        settled = self._is_settled(t, station_err, range_h)
        if not (takeoff_done and self._is_locked(t) and settled):
            return False

        self.phase = self.VISUAL
        self.handoff_count += 1
        distance = ("%.0f m" % range_h) if range_h else "?"
        self._message = ("GORSEL TEMAS (#%d, menzil %s, kilit %.1f s / %d kare%s) — "
                         "GPS yonelimi BIRAKILDI, komut yalnizca kameradan."
                         % (self.handoff_count, distance, self._lock_s(t), self._lock,
                            ", GNSS BAYAT" if self.gnss_stale(t) else ""))
        return True

    def visual_tick(self, t, det, seq, box_ok, last_raw=None):
        """Gorsel fazda bir tik islenir. GPS fazina DONULDUYSE True doner.

        ⛔ Imzada hedefe ait TEK veri "kutu var mi yok mu"dur. Menzil, konum,
          GNSS buraya PARAMETRE OLARAK BILE girmez -> gorsel fazda kural
          ihlali yapisal olarak imkansizdir. (`last_raw` hedefin konumu degil,
          paket kimligidir; yalnizca "paket geliyor mu" izlemesini besler ve
          hicbir kapiyi bu fazda tetiklemez.)

        box_ok : taze tespit YA DA kopru (olu-hesap) kutusu uretildi mi
        """
        self._track_packet(last_raw, t)
        self._process_frame(t, det, seq)
        if box_ok:
            return False

        lost_s = (t - self._last_valid_t) if self._last_valid_t else 0.0
        if lost_s <= self.cfg.LOST_S:
            return False

        self.phase = self.GPS
        self._lock = 0
        self._lock_since = None
        self._station_ticks = 0
        self._message = ("Hedef %.1f s kayip — GPS istasyon tutmaya GERI DONULDU."
                         % lost_s)
        return True

    # ================================================================
    #  GOSTERGE (guduume GIRMEZ)
    # ================================================================
    def handoff_message(self):
        """Son faz gecisinin insan okur aciklamasi (olay gunlugu icin)."""
        return self._message

    def status(self, t=None):
        """Gozetmenin ic sayaclari — arayuz/konsol icin."""
        t = time.perf_counter() if t is None else t
        return {
            "phase": self.phase,
            "lock": self._lock,
            "lock_need": self.visual_cfg.HANDOFF_FRAMES,
            "lock_s": self._lock_s(t),
            "lock_s_need": self.visual_cfg.HANDOFF_LOCK_S,
            "station_ticks": self._station_ticks,
            "station_ticks_need": self.cfg.HANDOFF_STATION_TICKS,
            "handoff_count": self.handoff_count,
            "gnss_stale": self.gnss_stale(t),
            "camera_only_gate": bool(self.cfg.CAMERA_ONLY_GATE),
        }


# ==========================================================
#  Bu dosya bir GIRIS NOKTASI DEGILDIR.
#  `python -m control.main` sessizce hicbir sey yapmasin diye isaret levhasi:
# ==========================================================
if __name__ == "__main__":
    print("control/main.py bir giris noktasi DEGILDIR — yalnizca faz kapisidir "
          "(PhaseSupervisor).\nGorevi calistirmak icin:  python -m web.server  "
          "->  http://127.0.0.1:8001")

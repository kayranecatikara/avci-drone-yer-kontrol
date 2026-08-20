# -*- coding: utf-8 -*-
"""
control/main.py — GOREV GOZETMENI + giris noktasi.

    python3 -m control.main            oyunda PLAY moduna gecip ENTER'a bas
    python3 -m control.main --hemen    beklemeden basla
    Ctrl+C                             gorevi durdur (motorlar kesilir)

FAZ AKISI
    KALKIS -> GPS YAKLASMA -> (devir kapisi) -> GORSEL TAKIP -> (kayip) -> GPS ...

DEVIR KAPISI (GPS -> GORSEL): iki kosul BIRLIKTE saglanmalidir —
    1) YAKINLIK  : GPS yatay mesafesi HANDOFF_RANGE altinda (ya da hedef GNSS'i
                   bayat; o zaman menzil zaten bilinemez, kutu kapisi yeter),
    2) GORSEL KILIT: ard arda N_LOCK kare guduume girebilecek kutu
                   (control.gorsel_takip.nisan_kutusu — gorsel fazin KULLANDIGI
                   kapinin AYNISI; ayri esik yazmak iki katmani ayristirir ve
                   devirden hemen sonra "kayip" verip faz sekmesine yol acar).

GORSEL FAZDA GPS KOMUTA GIRMEZ: gorsel temas kurulduktan sonra hareket komutu
YALNIZCA kameradan turer (yarisma kurali; aksi diskalifiye). Bu dosyada gorsel
fazda cagrilan tek GPS islevi `_hedef_temizle()`'dir ve o SADECE filtreyi taze
tutar — donen deger hicbir komuta girmez (faz geri donerse filtre isinmis olur).
"""
import math
import sys
import threading
import time

from control.common import KomutGonderici
from control.gorsel_takip import Cfg as GorselCfg, GorselTakip, bayat_mi, nisan_kutusu
from control.gps_approach import GPSCfg, GPSTakip
from perception import camera, detection_state
from sdk import drone_sdk as drone

CM_TO_M = 0.01


class Cfg:
    LOOP_HZ = 50.0
    DT = 1.0 / LOOP_HZ

    # --- DEVIR KAPISI ---
    HANDOFF_RANGE = 4000.0    # cm; GPS yatay mesafesi bunun altindayken gorsele devir
    GPS_STALE_S = 2.0         # s; hedef GNSS paketi bundan eskiyse "GNSS bayat" say

    # --- KONSOL ---
    OZET_S = 1.0              # s; durum satiri araligi


class Gorev:

    def __init__(self):
        self.gonderici = KomutGonderici(drone)
        self.gps = GPSTakip(drone, self.gonderici)
        self.gorsel = GorselTakip()
        self.faz = "GPS"
        self.aktif = False
        self._kilit_sayac = 0     # ard arda gecerli tespit (devir kapisi)
        self._kayip_t = None      # gorsel fazda tespitsiz gecen surenin baslangici
        self._devir_sayisi = 0
        self._son_paket_t = None  # son YENI ham GNSS paketinin zamani
        self._son_ham = None
        self._son_det = None      # konsol ozeti icin

    # ----------------------------------------------------------------
    def basla(self):
        self.gps.sifirla()
        self.gorsel.sifirla()
        self.gonderici.sifirla()
        detection_state.sifirla()
        self.faz = "GPS"
        self._kilit_sayac = 0
        self._kayip_t = None
        self._devir_sayisi = 0
        self.aktif = True
        print("[GOREV] BASLADI — kalkis + bozuk GNSS ile yaklasma.")

    def dur(self):
        self.aktif = False
        try:
            self.gonderici.kes()
        except Exception:
            pass
        print("[GOREV] DURDURULDU — motorlar kesildi.")

    # ----------------------------------------------------------------
    def _paket_izle(self, t):
        """YENI ham GNSS paketi geldiyse zaman damgasini tazele. HER FAZDA calisir:
        gorsel fazda da filtre beslendiginden kesinti izlemesi kesintisiz surer
        (faz geri donunce 'bayat' bayragi gercegi gostersin)."""
        ham = self.gps.son_ham
        if ham is not None and ham != self._son_ham:
            self._son_ham = ham
            self._son_paket_t = t

    def _gnss_bayat(self, t):
        """Hedef GNSS paketi GPS_STALE_S'ten uzun suredir yenilenmedi mi?"""
        if self._son_paket_t is None:
            return False
        return (t - self._son_paket_t) > Cfg.GPS_STALE_S

    def _tespit_oku(self, t):
        """detection_state'ten guduume GIREBILECEK tespiti oku (yoksa None)."""
        det = detection_state.son()
        if bayat_mi(det, GorselCfg, simdi=t):
            return None
        return nisan_kutusu(det, GorselCfg)

    # ================================================================
    #  TEK KONTROL ADIMI (50 Hz)
    # ================================================================
    def adim(self):
        t = time.perf_counter()
        det = self._tespit_oku(t)
        self._son_det = det

        if self.faz == "GPS":
            self.gps.adim()                       # kalkis + bozuk GNSS ile yaklasma
            self._paket_izle(t)
            bayat = self._gnss_bayat(t)
            self._kilit_sayac = (self._kilit_sayac + 1) if det is not None else 0
            yakin = (self.gps.d_h is not None and self.gps.d_h <= Cfg.HANDOFF_RANGE)
            if (self.gps._kalkis_done and self._kilit_sayac >= GorselCfg.N_LOCK
                    and (yakin or bayat)):
                self.faz = "GORSEL"
                self._devir_sayisi += 1
                self._kayip_t = None
                self.gorsel.sifirla()             # taze EMA + yumusak gecis rampasi
                mesafe = ("%.0f m" % (self.gps.d_h * CM_TO_M)) if self.gps.d_h else "?"
                print("[DEVIR] GORSEL TEMAS (#%d, menzil %s%s) -> GPS yonelimi BIRAKILDI, "
                      "komut yalnizca kameradan." % (self._devir_sayisi, mesafe,
                                                     ", GNSS BAYAT" if bayat else ""))
            return

        # ==================== GORSEL FAZ ====================
        # Filtreyi taze tut (KOMUTA GIRMEZ; faz geri donerse isinmis olsun).
        self.gps._hedef_temizle()
        self._paket_izle(t)

        if det is not None:
            self._kayip_t = None
            # KENDI IMU pitch'imiz = ego-motion telafisi (hedef verisi DEGIL).
            rot = drone.get_drone_rotation()
            own_pitch = (math.radians(float(rot[1])) if GPSCfg.ROT_IN_DEGREES
                         else float(rot[1]))
            thr, pitch, roll, yaw = self.gorsel.hesapla(det, own_pitch_rad=own_pitch)
            self.gonderici.gonder(thr, pitch, roll, yaw)
            return

        # --- TESPIT YOK: kisa sure hover, uzun kayipta GPS'e geri don ---
        if self._kayip_t is None:
            self._kayip_t = t
        kayip_s = t - self._kayip_t
        if kayip_s <= float(GorselCfg.LOST_S):
            self.gonderici.loiter()               # hedefi ararken bekle
            return
        print("[DEVIR] Hedef %.1f s kayip -> GPS yaklasmaya GERI DONULDU." % kayip_s)
        self.faz = "GPS"
        self._kilit_sayac = 0
        self._kayip_t = None
        self.gorsel.sifirla()

    # ----------------------------------------------------------------
    def ozet(self):
        """Tek satir konsol durumu (guduume GIRMEZ)."""
        kam = camera.durum()
        cmd = self.gonderici.prev
        if self.faz == "GPS":
            d = ("%.0f m" % (self.gps.d_h * CM_TO_M)) if self.gps.d_h else "?"
            ic = "faz=%-9s menzil=%-8s kilit=%d/%d" % (
                self.gps.faz, d, self._kilit_sayac, GorselCfg.N_LOCK)
        else:
            g = self.gorsel.durum()
            ic = "faz=GORSEL   sapma=%-6s boyut=%-7s conf=%-5s" % (
                g.get("sapma", "-"), g.get("boyut", "-"),
                ("%.2f" % self._son_det["conf"]) if self._son_det else "KAYIP")
        return ("[%s] %s | thr%+.2f pit%+.2f rol%+.2f yaw%+.2f | kamera %.1f FPS (%.0f ms)"
                % (self.faz, ic, cmd["thr"], cmd["pitch"], cmd["roll"], cmd["yaw"],
                   kam["fps"], kam["det_ms"]))


# ==========================================================
#  BAGLANTI YONETICISI
# ==========================================================
def baglanti_yoneticisi():
    onceki = None
    while True:
        c = drone.is_connected()
        if c and onceki is not True:
            print("[BAGLANTI] Oyuna baglanildi.")
        elif (not c) and onceki is True:
            print("[BAGLANTI] Oyun baglantisi koptu — yeniden deneniyor...")
        onceki = c
        if not c:
            try:
                drone.disconnect()
            except Exception:
                pass
            drone.connect()
        time.sleep(2.0)


# ==========================================================
#  ANA PROGRAM
# ==========================================================
def main():
    hemen = "--hemen" in sys.argv
    gorev = Gorev()

    threading.Thread(target=baglanti_yoneticisi, daemon=True,
                     name="baglanti").start()
    camera.baslat(lambda: gorev.aktif and drone.is_connected())

    print("=" * 62)
    print("  AVCI DRONE — GPS TAKIP + GORSEL TAKIP")
    print("  Oyun (Drones of War) acik ve PLAY modunda olmali.")
    print("  Oyun penceresi GORUNUR/ONDE kalsin (kamera ekrani yakalar).")
    print("=" * 62)
    if not hemen:
        try:
            input("Baslatmak icin ENTER (cikis: Ctrl+C) > ")
        except (EOFError, KeyboardInterrupt):
            return

    for _ in range(50):                       # baglanti icin kisa bekleme
        if drone.is_connected():
            break
        time.sleep(0.1)
    if not drone.is_connected():
        print("[UYARI] Oyuna henuz baglanilamadi — baglanti kurulunca gorev basliyor.")

    gorev.basla()
    t_ozet = 0.0
    try:
        while True:
            t0 = time.monotonic()
            if drone.is_connected():
                try:
                    gorev.adim()
                except Exception as e:
                    print("[HATA] kontrol adimi: %r" % e)
            if time.monotonic() - t_ozet >= Cfg.OZET_S:
                t_ozet = time.monotonic()
                print(gorev.ozet())
            kalan = Cfg.DT - (time.monotonic() - t0)
            if kalan > 0:
                time.sleep(kalan)
    except KeyboardInterrupt:
        print("\nKapatiliyor...")
    finally:
        gorev.dur()
        try:
            drone.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    main()

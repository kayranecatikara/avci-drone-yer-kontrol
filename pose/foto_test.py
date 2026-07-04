# -*- coding: utf-8 -*-
"""
================================================================================
 FOTO_TEST — Photo Mode'da SDK ne okuyor?  (KRITIK DENEY)
================================================================================
Hipotez: Photo Mode'a girince oyun SERBEST KAMERA (spectator) pawn'ini devralir.
SDK "o an kontrol edilen pawn"i okuyorsa -> get_drone_location() artik DRONU DEGIL
SERBEST KAMERAYI verir. Oyle ise: sahne DONUK (blur/latency yok) + Talon truth pozu
var + kamera pozu get_drone'dan geliyor -> 6 keypoint'i projekte edip KUSURSUZ
otomatik etiket uretiriz.

Bu script telemetriyi CANLI basar; sen photo mode'a girip kamerayi gezdirince
"DRONE" degerlerinin kamerayla birlikte DEGISIP DEGISMEDIGINI gozlersin.

Calistirma (repo kokunden; oyun PLAY'de; arayuz KAPALI):
    python pose\\foto_test.py

Adimlar (script calisirken):
  1) Once NORMAL ucusta: drone pos degisiyor mu bak (ucarken degismeli).
  2) PHOTO MODE'a gir (zamani durdur). Ekranda:
     - "TARGET" degerleri DONDU mu? (Talon sabit kaldiysa donmali)
     - Telemetri hala GELIYOR mu? (satirlar akmaya devam ediyor mu?)
  3) Photo mode'da SERBEST KAMERAYI gezdir (ileri/geri/yan/yukari + bak).
     - "DRONE" degerleri kamerayla DEGISIYOR mu?
        * DEGISIYORSA  -> get_drone = SERBEST KAMERA. ZAFER: otomatik etiket MUMKUN.
        * DEGISMIYORSA -> get_drone hala dronu okuyor (donmus). Baska yol lazim.
  4) Gozlemini bana yaz.

Script her saniye "DRONE HAREKET" / "TARGET DONUK" gibi ozet bayraklar da basar.
Durdurmak: CTRL-C.
"""
import os
import sys
import time
import math

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _KOK not in sys.path:
    sys.path.insert(0, _KOK)

from sdk import drone_sdk as drone


def _uz(a, b):
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def main():
    if not drone.connect():
        print("[HATA] Oyuna baglanilamadi. Oyun PLAY'de + arayuz KAPALI mi?")
        return 1
    print("[SDK] baglandi. 2 sn telemetri bekleniyor...")
    time.sleep(2.0)
    truth = drone.get_debug_truth()
    print("[SDK] truth available =", truth.get("available"))
    print("=" * 78)
    print("ADIMLAR: (1) normal ucus -> drone pos degisir  (2) PHOTO MODE'a gir")
    print("         (3) serbest kamerayi gezdir -> 'DRONE' degisiyor mu?  (CTRL-C: dur)")
    print("=" * 78)
    print("%-9s %-26s %-26s %-8s" % ("t(s)", "DRONE pos (x,y,z m)", "TARGET pos (x,y,z m)", "mesafe"))

    son_d = None
    son_t = None
    son_ozet = 0.0
    d_hareket_top = 0.0     # son 1 sn drone hareket miktari (m)
    t_hareket_top = 0.0
    t0 = time.perf_counter()

    try:
        while True:
            if not drone.is_connected():
                print("[HATA] baglanti koptu (photo mode telemetriyi kesmis olabilir).")
                break
            dp = drone.get_drone_location()
            dr = drone.get_drone_rotation()
            tp = drone.get_target_location()
            tru = drone.get_debug_truth()
            ttp = tru["target"]["position"] if tru.get("available") else tp

            dpm = tuple(c / 100.0 for c in dp)
            tpm = tuple(c / 100.0 for c in ttp)
            mes = _uz(dp, ttp) / 100.0

            if son_d is not None:
                d_hareket_top += _uz(dp, son_d) / 100.0
                t_hareket_top += _uz(ttp, son_t) / 100.0
            son_d, son_t = dp, ttp

            now = time.perf_counter()
            print("%-9.1f (%7.1f,%7.1f,%7.1f)   (%7.1f,%7.1f,%7.1f)   %6.1fm" %
                  (now - t0, dpm[0], dpm[1], dpm[2], tpm[0], tpm[1], tpm[2], mes),
                  end="\r", flush=True)

            if now - son_ozet >= 1.0:
                son_ozet = now
                dbay = "DRONE HAREKET(%.2fm/s)" % d_hareket_top if d_hareket_top > 0.05 else "drone DURGUN"
                tbay = "target HAREKET(%.2fm/s)" % t_hareket_top if t_hareket_top > 0.05 else "TARGET DONUK"
                print("\n[%5.1fs] %-26s | %-24s | drot=(%.0f,%.0f,%.0f) mes=%.1fm" %
                      (now - t0, dbay, tbay, dr[0], dr[1], dr[2], mes))
                d_hareket_top = 0.0
                t_hareket_top = 0.0

            time.sleep(0.15)
    except KeyboardInterrupt:
        print("\n[FOTO_TEST] durduruldu.")
    finally:
        drone.disconnect()
    print("\nGOZLEM SORULARI:")
    print("  A) Photo mode'a girince TARGET DONDU mu? (Talon sabit kaldi mi)")
    print("  B) Photo mode'da telemetri AKMAYA devam etti mi? (baglanti kopmadi mi)")
    print("  C) Serbest kamerayi gezdirince DRONE pos DEGISTI mi?")
    print("     -> C 'evet' ise: get_drone = kamera. Otomatik etiket MUMKUN, harika.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

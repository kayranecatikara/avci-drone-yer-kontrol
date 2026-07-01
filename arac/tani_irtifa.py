# -*- coding: utf-8 -*-
"""
GECICI TANI SCRIPTI — irtifa (Z) telemetrisini ekrana basar VE CSV'ye kaydeder.
Bu dosya tek seferlik teshis icindir; sorun cozulunce SILEBILIRSIN.

NE YAPAR:
  server.py'nin HTTP telemetri ucundan (/api/telemetry) canli veriyi okur,
  ekrana basar ve ayni klasordeki 'tani_log.csv' dosyasina her satiri yazar.
  Oyuna ikinci TCP baglantisi ACMAZ; server.py + oyun calisirken guvenli.

NASIL CALISTIRILIR:
  1) Oyun (Play modunda) + server.py (python server.py) acik olsun.
  2) AYRI bir terminalde:  python tani_irtifa.py
  3) Gorevi baslat, birak bir sure aksin, sonra Ctrl+C ile durdur.
  4) 'tani_log.csv' dosyasini Excel'de ac ya da bana yolla.

CSV SUTUNLARI (hepsi metre / m-s / -1..1):
  t_sn         : gecen sure (saniye)
  avci_irtifa  : avci drone irtifasi (get_drone_location Z)
  hedef_ham    : hedef HAM GPS irtifasi (bozuk)
  hedef_filtre : filtrenin temizledigi hedef irtifasi (kontrolcunun takip ettigi)
  hedef_gercek : hedefin GERCEK irtifasi (debug truth; yoksa bos)
  filtre_sapma : hedef_filtre - hedef_gercek (filtre ne kadar sapmis)
  dron_hata    : hedef_filtre - avci_irtifa (negatif = avci hedefin USTUNDE)
  throttle     : kontrolcunun gonderdigi dikey gaz (-1 alc / +1 tirman)
  pitch        : kontrolcunun gonderdigi ileri egim komutu (-1..1)
  hiz_ms       : avci drone toplam hizi (m/s)
"""
import csv
import json
import math
import os
import time
import urllib.request

URL = "http://127.0.0.1:8000/api/telemetry"
CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tani_log.csv")

BASLIKLAR = ["t_sn", "avci_irtifa", "hedef_ham", "hedef_filtre", "hedef_gercek",
             "filtre_sapma", "dron_hata", "throttle", "pitch", "hiz_ms",
             "gercek_mesafe", "ham_mesafe"]


def _uzaklik(a, b):
    if not a or not b:
        return None
    return math.sqrt((a.get("x", 0) - b.get("x", 0))**2 +
                     (a.get("y", 0) - b.get("y", 0))**2 +
                     (a.get("z", 0) - b.get("z", 0))**2)


def oku():
    with urllib.request.urlopen(URL, timeout=2.0) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    print("Baglaniliyor:", URL)
    print("CSV kaydi   :", CSV_PATH, " (Ctrl+C ile durdur)")
    print("GERCEK_MESAFE = asil basari olcutu (gercek drone<->gercek hedef).")
    print("HAM = ekrandaki deger (bozuk GPS, ~29 m sismis). Tum sutunlar CSV'de.\n")
    print("-" * 100)

    csv_f = open(CSV_PATH, "w", newline="", encoding="utf-8")
    yazici = csv.writer(csv_f)
    yazici.writerow(BASLIKLAR)
    csv_f.flush()

    t0 = None
    try:
        while True:
            try:
                d = oku()
            except Exception as e:
                print("  (server/oyun yok ya da telemetri akmiyor):", e)
                time.sleep(1.0)
                continue
            if t0 is None:
                t0 = time.time()
            t = time.time() - t0

            drone = d.get("drone", {})
            target = d.get("target", {})
            avci_z   = drone.get("z")             # avci drone irtifasi (m)
            hedef_ham = target.get("z")           # hedef HAM GPS irtifasi (m, bozuk)
            throttle = drone.get("cmd_throttle")  # gonderilen dikey gaz
            pitch    = drone.get("cmd_pitch")     # gonderilen ileri egim
            hiz_ms   = drone.get("speed_ms")      # avci toplam hizi

            jinfo = d.get("j", {}) or {}
            hedef_filtre = (jinfo.get("temiz") or {}).get("z")   # filtrelenmis hedef irtifasi

            dbg = d.get("debug", {}) or {}
            hedef_gercek = None
            gercek_mesafe = None
            if dbg.get("available"):
                hedef_gercek = (dbg.get("target_real") or {}).get("z")
                # GERCEK 3B mesafe: gercek drone <-> gercek hedef (asil basari olcutu)
                gercek_mesafe = _uzaklik(dbg.get("drone_real"), dbg.get("target_real"))
            # HAM 3B mesafe: server'in bozuk-GPS'e gore hesabi (ekranda gorunen, ~29 m sisirmeli)
            ham_mesafe = d.get("distance_m")

            sapma = (hedef_filtre - hedef_gercek) if (hedef_filtre is not None and hedef_gercek is not None) else None
            dron_hata = (hedef_filtre - avci_z) if (hedef_filtre is not None and avci_z is not None) else None

            # --- CSV satiri (bos deger -> "") ---
            def c(x): return round(x, 2) if isinstance(x, (int, float)) else ""
            yazici.writerow([round(t, 1), c(avci_z), c(hedef_ham), c(hedef_filtre), c(hedef_gercek),
                             c(sapma), c(dron_hata), c(throttle), c(pitch), c(hiz_ms),
                             c(gercek_mesafe), c(ham_mesafe)])
            csv_f.flush()

            # --- ekran (GERCEK mesafe = asil basari; HAM = ekrandaki sisirmeli deger) ---
            def f(x, w=8): return f"{x:{w}.1f}" if isinstance(x, (int, float)) else f"{'NA':>{w}}"
            def f3(x, w=8): return f"{x:{w}.3f}" if isinstance(x, (int, float)) else f"{'NA':>{w}}"
            print(f"{t:5.0f} | avci_z={f(avci_z,6)} dron_hata={f(dron_hata,7)} | "
                  f"THR={f3(throttle,6)} | GERCEK_MESAFE={f(gercek_mesafe,6)} m  HAM={f(ham_mesafe,6)} m")
            time.sleep(0.5)
    finally:
        csv_f.close()
        print(f"\nbitti. Kayit: {CSV_PATH}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass

# -*- coding: utf-8 -*-
"""
================================================================================
GELISTIRME/DOGRULAMA ARACI — gorev ucusunda ve degerlendirme kosusunda
kullanilmaz. (Test/olcum turlarini yonetir; teslim paketine girmez.)
================================================================================
KOSU YONETICI — tek komutla uctan uca test/olcum turu
================================================================================
Sorumluluklar (master prompt EK + saha protokolleri):
  a) OYUN YASAM DONGUSU: oyun acik degilse DronesOfWar.exe'yi baslatir, pencereyi
     bulup PLAY'e gecilmesini (telemetri baslamasi) bekler. PLAY otomasyonu
     GUVENILIR degil (menu akisi bilinmiyor) -> tek insan adimi "PLAY'e bas"
     kalir; arac telemetriyi OTOMATIK algilayip devam eder (kullanici "hazir"
     yazmaz bile).
  b) TEK TCP OTURUMU: turdaki tum araclar AYNI baglantiyi paylasir (araclar arasi
     baglan/kop YOK -> oyun dinleyici tikanmasinin baslica suphelisi). Kapanis
     standart: disconnect + kisa bekleme.
  c) KAPANIS: baglanti kapat -> (ucusluysa / --oyunu-acik-birak degilse) oyunu
     KAPAT (surec sonlandir) -> sesli bip + konsol basliginda [KOSU BITTI] +
     raporu terminale yaz.
  d) ZOMBILESME PROTOKOLU: UCUSLU her turdan sonra (arm edildi) oyun KOMPLE
     yeniden baslatilir (sim v0.0.5'te arm sonrasi telemetri bozuluyor: donuk
     attitude + komuttan bagimsiz sayan z; MEVCUT_DURUM'da 3 kez dogrulandi).
     ARM'SIZ olcumler ayni oturumu paylasabilir.

Kullanici yalnizca: (gerekirse) PLAY'e basar ve raporu okur. Oyunu KAPATMA
kullaniciya birakilmaz (isinma derdi).

KULLANIM:
    python arac/kosu_yonetici.py k-sanity          # arm'siz: hakem + K sanity (birlesik)
    python arac/kosu_yonetici.py hakem             # arm'siz: hareket-farki hakemi
    python arac/kosu_yonetici.py filtre            # arm'siz: fusion filtre dogrulama
    python arac/kosu_yonetici.py k-sanity --sure 150
    python arac/kosu_yonetici.py <tur> --oyunu-acik-birak   # kapanista oyunu kapatma
    python arac/kosu_yonetici.py <tur> --oyun-hazir         # oyunu ben baslatma (zaten PLAY'de)
Turler ekitikce (FAZ 1 CMC vb.) TUR_KAYDI'na eklenir; ucusluysa ucuslu=True.
================================================================================
"""
import argparse
import ctypes
import os
import subprocess
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJ_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _PROJ_ROOT)
sys.path.insert(0, _HERE)

GAME_TITLE_HINTS = ["dronesofwar", "drones of war", "drone of war"]
GAME_PROC = "dronesofwar"                     # surec adi ipucu (kucuk harf)
EXE_ADAYLARI = [
    os.path.join(_PROJ_ROOT, "Drones of War Teknofest", "DronesOfWar.exe"),
    os.path.join(os.path.dirname(_PROJ_ROOT), "Drones of War Teknofest", "DronesOfWar.exe"),
]


# ----------------------------------------------------------------------------
#  Oyun sureci: bul / baslat / kapat
# ----------------------------------------------------------------------------
def _oyun_surecleri():
    """Calisan DronesOfWar sureclerinin psutil.Process listesi."""
    try:
        import psutil
    except Exception:
        return []
    bulunan = []
    for p in psutil.process_iter(["name"]):
        try:
            ad = (p.info.get("name") or "").lower()
            if GAME_PROC in ad:
                bulunan.append(p)
        except Exception:
            continue
    return bulunan


def oyun_calisiyor_mu():
    return len(_oyun_surecleri()) > 0


def oyunu_baslat():
    """Oyun calismiyorsa exe'yi baslatir. (baslatildi_mi, hata) doner."""
    if oyun_calisiyor_mu():
        print("[OYUN] Zaten calisiyor.")
        return True, None
    exe = next((e for e in EXE_ADAYLARI if os.path.isfile(e)), None)
    if exe is None:
        return False, ("DronesOfWar.exe bulunamadi. Aranan:\n   " +
                       "\n   ".join(EXE_ADAYLARI))
    print("[OYUN] Baslatiliyor: %s" % exe)
    try:
        subprocess.Popen([exe], cwd=os.path.dirname(exe))
    except Exception as e:
        return False, "Exe baslatilamadi: %s" % e
    # Pencere gorunene kadar bekle (en cok 60 sn)
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < 60.0:
        try:
            from detection.pencere_yakala import pencere_bul
            baslik, _hwnd = pencere_bul(GAME_TITLE_HINTS)
            if baslik is not None:
                print("[OYUN] Pencere goründü (+%.0f sn): %s"
                      % (time.perf_counter() - t0, baslik))
                return True, None
        except Exception:
            pass
        time.sleep(1.0)
    return False, "Oyun penceresi 60 sn'de gorunmedi."


def oyunu_kapat():
    """Tum DronesOfWar sureclerini sonlandir (terminate -> kill). Oyun kapaninca
    isinma icin kisa bekleme."""
    surecler = _oyun_surecleri()
    if not surecler:
        print("[OYUN] Kapatilacak surec yok.")
        return
    print("[OYUN] Kapatiliyor (%d surec)..." % len(surecler))
    for p in surecler:
        try:
            p.terminate()
        except Exception:
            pass
    import psutil
    _gitti, kalan = psutil.wait_procs(surecler, timeout=8)
    for p in kalan:
        try:
            p.kill()                          # inatci surec -> zorla
        except Exception:
            pass
    time.sleep(2.0)
    print("[OYUN] Kapatildi.")


# ----------------------------------------------------------------------------
#  Baglanti + PLAY (telemetri) bekleme
# ----------------------------------------------------------------------------
def baglan_ve_bekle(play_bekle_s=120.0):
    """Tek TCP baglantisi ac; telemetri (PLAY) baslayana kadar bekle.
    drone modulu | None (basarisiz) doner."""
    from sdk import drone_sdk as drone
    if not drone.connect():
        # oyun yeni acildiysa TCP dinleyici birkac sn sonra hazir olur -> birkac dene
        for _ in range(15):
            time.sleep(2.0)
            if drone.connect():
                break
        else:
            print("[BAGLANTI] Oyuna baglanilamadi (TCP dinleyici yok).")
            return None
    print("[BAGLANTI] TCP kuruldu. PLAY'e gec (telemetri bekleniyor; en cok %.0f sn)..."
          % play_bekle_s)
    print("           >>> OYUNDA PLAY'E BAS <<<  (arac otomatik algilar, 'hazir' yazma)")
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < play_bekle_s:
        try:
            if any(abs(v) > 1e-6 for v in drone.get_drone_location()):
                print("[BAGLANTI] Telemetri basladi (+%.0f sn)." % (time.perf_counter() - t0))
                return drone
        except Exception:
            pass
        time.sleep(0.25)
    print("[BAGLANTI] Telemetri gelmedi (PLAY'e gecilmedi?).")
    try:
        drone.disconnect()
    except Exception:
        pass
    return None


def truth_bekle(drone, sure_s=10.0):
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < sure_s:
        try:
            if drone.get_debug_truth().get("available"):
                return True
        except Exception:
            pass
        time.sleep(0.25)
    return False


# ----------------------------------------------------------------------------
#  Kapanis bildirimi: bip + konsol basligi + banner
# ----------------------------------------------------------------------------
def _bip():
    try:
        import winsound
        for f in (880, 1175, 1568):           # yukselen uc nota
            winsound.Beep(f, 160)
    except Exception:
        sys.stdout.write("\a")                # terminal zili (fallback)
        sys.stdout.flush()


def kosu_bitti_bildir(baslik_ozet):
    try:
        ctypes.windll.kernel32.SetConsoleTitleW("[KOSU BITTI] " + baslik_ozet)
    except Exception:
        pass
    print("\n" + "#" * 68)
    print("#  [KOSU BITTI]  %s" % baslik_ozet)
    print("#" * 68)
    _bip()


# ----------------------------------------------------------------------------
#  TUR TANIMLARI: her tur (bagli drone) -> (basari_mi, rapor_metni)
#  ucuslu=True olanlar arm eder -> tur sonrasi oyun KOMPLE restart edilir.
# ----------------------------------------------------------------------------
def _tur_hakem(drone, arg):
    import hareket_hakemi as hakem
    if not truth_bekle(drone):
        return False, "Truth AKMIYOR (sim debug kanali kapali?)."
    r = hakem.kosu(drone, arg.sure if arg.sure else 40.0)
    if r is None:
        return False, "Hakem yetersiz eslesme."
    return True, ("Hakem: n=%d | yatay %+.1f deg (MAD %.1f) | dikey %+.1f deg (MAD %.1f)"
                  " | K olcek k=%.3f (ex %.2f..%.2f)"
                  % (r["n"], r["yatay_med_deg"], r["yatay_mad_deg"],
                     r["dikey_med_deg"], r["dikey_mad_deg"],
                     r["k_kestirim"], r["ex_aralik"][0], r["ex_aralik"][1]))


def _tur_k_sanity(drone, arg):
    import hareket_hakemi as hakem
    import k_sanity_olcum as ks
    if not truth_bekle(drone):
        return False, "Truth AKMIYOR (sim debug kanali kapali?)."
    # (1) hakem (zincir kontrolu) — arm'siz, ayni oturum
    h = hakem.kosu(drone, 30.0)
    hakem_str = "hakem yetersiz"
    if h is not None:
        hakem_str = ("dikey %+.1f deg, K olcek k=%.3f"
                     % (h["dikey_med_deg"], h["k_kestirim"]))
    # (2) K sanity siluet olcumu — AYNI baglanti (arm'siz)
    csv_yolu = os.path.join(_PROJ_ROOT, "veri",
                            time.strftime("k_sanity_%Y%m%d_%H%M%S.csv"))
    csv_yolu = ks.olc(arg.sure if arg.sure else 150.0, 0.0, csv_yolu,
                      yontem="siluet", irtifa_hedefe=False, drone_baglanti=drone)
    if not csv_yolu:
        return False, "K sanity olcumu basarisiz. (Hakem: %s)" % hakem_str
    sonuc = ks.analiz(csv_yolu)
    if not sonuc or sonuc.get("yetersiz"):
        return True, "K sanity YETERSIZ VERI (N<%d). Hakem: %s" % (ks.N_MIN, hakem_str)
    return True, ("K sanity: N=%d sapma %+.1f%% (esik %%5) -> %s | Hakem: %s"
                  % (sonuc["n"], 100 * sonuc["sapma"],
                     "GECTI" if sonuc["gecti"] else "KALDI", hakem_str))


def _tur_filtre(drone, arg):
    import filtre_dogrulama as fd
    if not truth_bekle(drone):
        return False, "Truth AKMIYOR (sim debug kanali kapali?)."
    csv_yolu = os.path.join(_PROJ_ROOT, "veri",
                            time.strftime("filtre_dogrulama_%Y%m%d_%H%M%S.csv"))
    csv_yolu = fd.olc(arg.sure if arg.sure else 60.0, csv_yolu, drone_baglanti=drone)
    if not csv_yolu:
        return False, "Filtre dogrulama olcumu basarisiz."
    r = fd.analiz(csv_yolu)
    if not r:
        return False, "Filtre dogrulama analizi bos."
    return True, ("Filtre: RMSE ham %.1f m -> J %.1f m (kazanc %%%.0f) | gecikme ham %.2f s"
                  " -> J %.2f s" % (r["ham"]["rmse_m"], r["filtre"]["rmse_m"],
                                    r["kazanc_pct"], r["ham"]["tau_s"], r["filtre"]["tau_s"]))


# TUR_KAYDI: ad -> (fonksiyon, ucuslu_mu, aciklama). FAZ 1+ turleri buraya eklenir.
TUR_KAYDI = {
    "hakem":    (_tur_hakem,   False, "hareket-farki hakemi (zincir/K acisal kontrolu)"),
    "k-sanity": (_tur_k_sanity, False, "hakem + K sanity siluet olcumu (birlesik)"),
    "filtre":   (_tur_filtre,  False, "fusion filtre dogrulama (RMSE/gecikme)"),
}


# ----------------------------------------------------------------------------
#  Tur yurutucu (oyun yasam dongusu + kapanis + zombilesme protokolu)
# ----------------------------------------------------------------------------
def tur_yurut(tur_adi, arg):
    fn, ucuslu, aciklama = TUR_KAYDI[tur_adi]
    print("=" * 68)
    print(" KOSU YONETICI — tur: %s  (%s%s)"
          % (tur_adi, aciklama, " [UCUSLU]" if ucuslu else " [arm'siz]"))
    print("=" * 68)

    # (a) Oyun yasam dongusu
    if not arg.oyun_hazir:
        ok, hata = oyunu_baslat()
        if not ok:
            print("[HATA] %s" % hata)
            return 1

    # (b) Tek TCP oturumu + PLAY bekle
    drone = baglan_ve_bekle()
    if drone is None:
        if not arg.oyunu_acik_birak and not arg.oyun_hazir:
            oyunu_kapat()
        return 1

    basari = False
    rapor = "(rapor yok)"
    try:
        basari, rapor = fn(drone, arg)
    except Exception as e:
        import traceback
        traceback.print_exc()
        rapor = "Tur ISTISNA ile dustu: %s" % e
    finally:
        # (c) standart kapanis: disconnect + kisa bekleme
        try:
            drone.disconnect()
        except Exception:
            pass
        time.sleep(1.0)
        print("[BAGLANTI] Kapatildi.")

    # (d) ZOMBILESME PROTOKOLU: ucuslu tur oyunu bozar -> KOMPLE restart.
    #     (Bir sonraki tur/kullanici taze oturum bulsun.)
    if ucuslu and not arg.oyunu_acik_birak:
        print("[PROTOKOL] UCUSLU tur bitti -> zombilesme onlemi: oyun yeniden baslatiliyor.")
        oyunu_kapat()
        ok, hata = oyunu_baslat()
        if not ok:
            print("[PROTOKOL][UYARI] Oyun yeniden baslatilamadi: %s" % hata)
    elif not arg.oyunu_acik_birak and not arg.oyun_hazir:
        # arm'siz tur + oyunu biz actiysak: temiz birak (kapat)
        oyunu_kapat()
    else:
        print("[OYUN] Acik birakildi (--oyunu-acik-birak / --oyun-hazir).")

    kosu_bitti_bildir("%s -> %s" % (tur_adi, "OK" if basari else "BASARISIZ"))
    print("\nRAPOR:\n  %s\n" % rapor)
    return 0 if basari else 1


def main():
    ap = argparse.ArgumentParser(description="Kosu yonetici (tek komutla test/olcum turu)")
    ap.add_argument("tur", choices=sorted(TUR_KAYDI.keys()), help="calistirilacak tur")
    ap.add_argument("--sure", type=float, default=0.0, help="olcum suresi (sn; 0=tur varsayilani)")
    ap.add_argument("--oyunu-acik-birak", action="store_true",
                    help="kapanista oyunu KAPATMA (varsayilan: biz actiysak kapatilir)")
    ap.add_argument("--oyun-hazir", action="store_true",
                    help="oyunu ben baslatma/kapatma (zaten acik ve PLAY'de)")
    arg = ap.parse_args()
    sys.exit(tur_yurut(arg.tur, arg))


if __name__ == "__main__":
    main()

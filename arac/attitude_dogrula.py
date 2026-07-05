# -*- coding: utf-8 -*-
"""
================================================================================
GELISTIRME/DOGRULAMA ARACI — gorev ucusunda ve degerlendirme kosusunda
kullanilmaz. (Attitude-konvansiyon dogrulamasi; truth-tabanli; pakete girmez.)
================================================================================
ATTITUDE KONVANSIYON OTURUMU — kamera_model pitch/roll isaret + Euler sirasi
================================================================================
HIPOTEZ: reprojeksiyon zinciri LEVEL'da dogru (K-sanity gecti) ama YATISTA bozuk
(referans kosuda: hedefe yaklasirken truth yalniz %21 kadraj-ici, %57 "kamera
arkasi"). Suphe: R_govde_to_dunya pitch/roll ISARETI veya Euler KOMPOZISYON SIRASI.

YONTEM (CMC-yaw testinin TUM eksenlere + MUTLAK zincire genellestirilmisi):
  Hover'da hedef gorus alanindayken KONTROLLU attitude adimlari uygulanir
  (saf PITCH ±10-15, saf ROLL ±10-15, sonra kombinasyon). Her karede:
    - drone attitude'u telemetriden OKUNUR (roll,pitch,yaw derece),
    - truth hedef konumu bu attitude ile GORUNTUYE reprojekte edilir (kamera_model),
    - hedefin GERCEK pikseli truth-BAGIMSIZ bulunur (siluet: gokten koyu Talon;
      arac/k_sanity_olcum._siluet_tespit, GENIS ROI),
    - ofset = (u_gercek - u_reproj, v_gercek - v_reproj) EKSEN BAZINDA kaydedilir.
  DOGRU konvansiyon -> ofset attitude'dan BAGIMSIZ kucuk/sabit. YANLIS pitch
  isareti -> dv |pitch| ile buyur (ya da ters yon). eksen_analiz() ofseti
  pitch/roll/yaw'a REGRESE eder; hangi eksenin katsayisi buyukse o eksenin
  isaret/sira suphesi. Bulunan duzeltme kamera_model'de TEK NOKTADAN yapilir;
  R_govde_to_dunya (veya R_mount) tek kaynak; tuketiciler (PnP/CMC/IBVS/geometrik
  kapi) DEGISMEZ.

OTURUM SONU (2-3 dk MINI FSM SEGMENTI — SART): Blokor A kapali (truth artik
GORSEL_TAKIP'te loglaniyor). Duzeltilmis reprojeksiyonla kisa bir gorev kosulur
-> arac/tp_fp_analiz ILK KEZ gercek TP/FP verir. Referans kosunun ESKI CSV'sinden
retroaktif TP/FP CIKMAZ (truth o an yoktu) -> bu segment olmadan Madde 1/4'un
FP savunmasi sayiyla dogrulanamaz.

BASARI KRITERI: her eksende |ofset| attitude sweep boyunca < ESIK (orn. %3 W ~
0.03 normalize) ve pitch/roll regresyon katsayilari ~0 (attitude-bagimsiz). O
zaman kamera_model basindaki ">>> SIM'DE DOGRULA <<<" serhi OLCUM KIMLIGIYLE
(tarih + sweep araligi + artik ofset) kapatilir.

ZOMBILESME PROTOKOLU: her ucuslu tur sonrasi taze oyun oturumu (menu PLAY/FLY/E).

KULLANIM (kullanici "hazir" deyince):
  1) main.py calisir + oyun PLAY modunda + DEBUG TRUTH akiyor.
  2) python arac/attitude_dogrula.py --adimlar          # canli sweep + analiz
     python arac/attitude_dogrula.py --analiz <csv>      # kayittan yeniden analiz
  3) Verdikt + onerilen kamera_model duzeltmesi yazilir; duzeltme uygulanip
     mini-FSM segmenti kosulur.
================================================================================
"""
import argparse
import csv
import math
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJ = os.path.dirname(_HERE)
sys.path.insert(0, _PROJ)
sys.path.insert(0, _HERE)

import numpy as np
from detection import kamera_model as km

# --- kontrollu attitude adim dizisi (manuel-mod komut [-1,1], derece DEGIL;
#     drone fizigi tepki verir, attitude telemetriden OKUNUR) ---
ADIM_DIZISI = [
    ("hover", 0.0, 0.0, 2.0),        # (ad, pitch_cmd, roll_cmd, sure_s)
    ("pitch+", +0.30, 0.0, 2.5), ("hover", 0.0, 0.0, 1.5),
    ("pitch-", -0.30, 0.0, 2.5), ("hover", 0.0, 0.0, 1.5),
    ("roll+", 0.0, +0.30, 2.5), ("hover", 0.0, 0.0, 1.5),
    ("roll-", 0.0, -0.30, 2.5), ("hover", 0.0, 0.0, 1.5),
    ("pitch+roll+", +0.25, +0.25, 2.5), ("hover", 0.0, 0.0, 1.5),
    ("pitch-roll-", -0.25, -0.25, 2.5), ("hover", 0.0, 0.0, 1.5),
]
KAYIT_KOLON = ["t", "adim", "roll", "pitch", "yaw", "u_reproj", "v_reproj",
               "u_gercek", "v_gercek", "du_norm", "dv_norm", "W", "H"]


# ----------------------------------------------------------------------------
#  OLCUM CEKIRDEGI (offline test edilebilir; sim gerekmez)
# ----------------------------------------------------------------------------
def reproj_norm(truth_world, drone_pos, roll, pitch, yaw_deg, W, H):
    """truth dunya -> normalize goruntu (u,v) [0..1] | None (kamera arkasi)."""
    p_kam = km.dunya_to_kamera(truth_world, drone_pos, roll, pitch, yaw_deg)
    uv = km.izdusur(p_kam, km.K_matrisi(W, H))
    if uv is None:
        return None
    return uv[0] / W, uv[1] / H


def _lin_katsayi(x, y):
    """Basit en-kucuk-kareler egimi (y ~ a*x + b) -> a. |a| buyukse y, x'e bagli."""
    x = np.asarray(x, float); y = np.asarray(y, float)
    if len(x) < 3 or float(np.std(x)) < 1e-6:
        return 0.0
    a, _b = np.polyfit(x, y, 1)
    return float(a)


def eksen_analiz(kayitlar):
    """kayitlar: dict listesi (roll,pitch,yaw,du_norm,dv_norm). -> verdikt.
    Her eksen icin ofsetin o eksene REGRESYON egimi; buyukse konvansiyon suphesi.
    DOGRU konvansiyon: tum egimler ~0 + |ofset| kucuk."""
    if not kayitlar:
        return {"n": 0, "sonuc": "veri yok"}
    roll = [k["roll"] for k in kayitlar]
    pitch = [k["pitch"] for k in kayitlar]
    yaw = [k["yaw"] for k in kayitlar]
    du = [k["du_norm"] for k in kayitlar]
    dv = [k["dv_norm"] for k in kayitlar]
    egim = {
        "dv~pitch": _lin_katsayi(pitch, dv), "du~pitch": _lin_katsayi(pitch, du),
        "du~roll": _lin_katsayi(roll, du), "dv~roll": _lin_katsayi(roll, dv),
        "du~yaw": _lin_katsayi(yaw, du), "dv~yaw": _lin_katsayi(yaw, dv),
    }
    ofset_buyuk = float(np.median([math.hypot(a, b) for a, b in zip(du, dv)]))
    # esik: normalize/derece egim; |egim|>0.003 (der basina %0.3 W) belirgin bagimlilik
    suphe = [k for k, v in egim.items() if abs(v) > 0.003]
    tutarli = (not suphe) and ofset_buyuk < 0.03
    return {"n": len(kayitlar), "egim": egim, "ofset_medyan_norm": ofset_buyuk,
            "suphe": suphe, "konvansiyon_tutarli": tutarli,
            "sonuc": ("TUTARLI (attitude-bagimsiz, ofset<%%3)" if tutarli
                      else "SUPHE: " + ", ".join(suphe) if suphe
                      else "ofset buyuk (%.3f) ama attitude-bagimsiz -> zincir sabiti/K")}


def oneri_metni(analiz):
    """Analize gore kamera_model duzeltme onerisi (insan uygular; TEK nokta)."""
    if analiz.get("konvansiyon_tutarli"):
        return ("KONVANSIYON DOGRU -> kamera_model'deki '>>> SIM'DE DOGRULA <<<' serhi\n"
                "  olcum kimligiyle KAPATILABILIR (tarih + sweep + artik ofset<%%3).")
    s = analiz.get("suphe", [])
    sat = ["SUPHE EKSENLERI: %s" % ", ".join(s)]
    if any("pitch" in k for k in s):
        sat.append("  -> R_govde_to_dunya pitch bloklari (Rpitch isareti) VEYA kompozisyon")
        sat.append("     sirasi (Ryaw@Rpitch@Rroll) gozden gecir; pitch isaretini test-flip.")
    if any("roll" in k for k in s):
        sat.append("  -> Rroll isareti / R_mount roll ekseni gozden gecir.")
    if any("yaw" in k for k in s):
        sat.append("  -> yaw zaten CMC-yaw'da GECTI; yaw suphesi cikarsa mutlak-zincir")
        sat.append("     (R_mount) yaw ile etkilesimini kontrol et.")
    sat.append("  Duzeltme kamera_model'de TEK NOKTADAN; tuketiciler degismez; sonra")
    sat.append("  bu araci TEKRAR kos -> tum egimler ~0 olana dek.")
    return "\n".join(sat)


# ----------------------------------------------------------------------------
#  CANLI SWEEP (sim gerekir; kullanici "hazir" deyince)
# ----------------------------------------------------------------------------
def canli_sweep(csv_yol):
    """Manuel-mod attitude sweep + kare/siluet + truth reproj -> kayit + analiz."""
    from sdk import drone_sdk as drone
    try:
        import cv2
    except Exception:
        cv2 = None
    import mss
    from k_sanity_olcum import kare_al, _siluet_tespit, _oyun_one_getir  # arac/ (dev)

    if not drone.is_connected():
        drone.connect()
    if not drone.get_debug_truth().get("available"):
        print("[HATA] DEBUG TRUTH AKMIYOR — bu arac truth-tabanli. Sim'de truth'u ac.")
        return 1
    _oyun_one_getir()
    # Manuel mod + arm + hover (irtifa-tutma kullaniciya/otomatiga birakilir; burada
    # basit sabit throttle ile hover denenir — drift olursa adim sureleri kisadir).
    drone.set_control_surfaces(0.0, 0.0, 0.0, 0.0, True)   # arm + hover
    print("[OK] truth akiyor; attitude sweep basliyor (%d adim)." % len(ADIM_DIZISI))
    sct = mss.mss()
    kayit = []
    t0 = time.perf_counter()
    for ad, pcmd, rcmd, sure in ADIM_DIZISI:
        t_adim = time.perf_counter()
        while time.perf_counter() - t_adim < sure:
            drone.set_control_surfaces(0.55, pcmd, rcmd, 0.0, True)   # hover throttle + adim
            dbg = drone.get_debug_truth()
            if not dbg.get("available"):
                continue
            tpos = np.array(dbg["target"]["position"], float)
            dpos = np.array(drone.get_drone_gps(), float)
            roll, pitch, yaw = drone.get_drone_rotation()
            fr, _kaynak = kare_al(sct, cv2)
            H, W = fr.shape[:2]
            uvn = reproj_norm(tpos, dpos, roll, pitch, yaw, W, H)
            if uvn is None:
                continue
            det, _neden = _siluet_tespit(fr, (uvn[0] * W, uvn[1] * H), cv2) if cv2 else (None, "")
            if not det:
                continue
            ug, vg = det["cx"] / W, det["cy"] / H
            kayit.append({"t": round(time.perf_counter() - t0, 2), "adim": ad,
                          "roll": roll, "pitch": pitch, "yaw": yaw,
                          "u_reproj": uvn[0], "v_reproj": uvn[1], "u_gercek": ug, "v_gercek": vg,
                          "du_norm": ug - uvn[0], "dv_norm": vg - uvn[1], "W": W, "H": H})
            time.sleep(0.05)
    drone.set_control_surfaces(0.0, 0.0, 0.0, 0.0, True)     # hover birak
    if csv_yol and kayit:
        with open(csv_yol, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=KAYIT_KOLON); w.writeheader()
            for k in kayit:
                w.writerow(k)
        print("[KAYIT] %d ornek -> %s" % (len(kayit), csv_yol))
    _rapor(eksen_analiz(kayit))
    return 0


def _rapor(analiz):
    print("=" * 68)
    print(" ATTITUDE KONVANSIYON ANALIZI")
    print("=" * 68)
    print(" ornek: %d ; ofset medyan (norm): %s ; sonuc: %s"
          % (analiz.get("n", 0), round(analiz.get("ofset_medyan_norm", 0), 4)
             if analiz.get("n") else "-", analiz.get("sonuc")))
    if analiz.get("egim"):
        print(" regresyon egimleri (|.|>0.003 = suphe):")
        for k, v in analiz["egim"].items():
            print("    %-10s %+.4f%s" % (k, v, "  <== SUPHE" if abs(v) > 0.003 else ""))
    print("-" * 68)
    print(oneri_metni(analiz))


def _analiz_csv(yol):
    with open(yol, encoding="utf-8", newline="") as f:
        kayit = [{k: (float(v) if k not in ("adim",) else v) for k, v in r.items()}
                 for r in csv.DictReader(f)]
    _rapor(eksen_analiz(kayit))


def main():
    ap = argparse.ArgumentParser(description="Attitude konvansiyon dogrulama oturumu")
    ap.add_argument("--adimlar", action="store_true", help="canli attitude sweep (sim)")
    ap.add_argument("--analiz", metavar="CSV", help="kayittan yeniden analiz")
    ap.add_argument("--csv", default=os.path.join(_PROJ, "veri", "attitude_sweep.csv"))
    arg = ap.parse_args()
    if arg.analiz:
        return _analiz_csv(arg.analiz)
    if arg.adimlar:
        return canli_sweep(arg.csv)
    print("Kullanim: --adimlar (canli sweep) | --analiz <csv>. Plan icin dosya basligi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

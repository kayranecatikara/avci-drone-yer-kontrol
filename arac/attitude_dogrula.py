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
# adim: (ad, pitch_cmd, roll_cmd, yaw_cmd, sure_s). Saf eksenler + kombinasyon +
# TESHIS-1 icin saf yaw. Reprojeksiyon sweep'i ve komut-eksen testi AYNI oturumda.
ADIM_DIZISI = [
    ("hover", 0.0, 0.0, 0.0, 2.0),
    ("pitch+", +0.30, 0.0, 0.0, 2.5), ("hover", 0.0, 0.0, 0.0, 1.5),
    ("pitch-", -0.30, 0.0, 0.0, 2.5), ("hover", 0.0, 0.0, 0.0, 1.5),
    ("roll+", 0.0, +0.30, 0.0, 2.5), ("hover", 0.0, 0.0, 0.0, 1.5),
    ("roll-", 0.0, -0.30, 0.0, 2.5), ("hover", 0.0, 0.0, 0.0, 1.5),
    ("yaw+", 0.0, 0.0, +0.30, 2.5), ("hover", 0.0, 0.0, 0.0, 1.5),
    ("yaw-", 0.0, 0.0, -0.30, 2.5), ("hover", 0.0, 0.0, 0.0, 1.5),
    ("pitch+roll+", +0.25, +0.25, 0.0, 2.5), ("hover", 0.0, 0.0, 0.0, 1.5),
]
KAYIT_KOLON = ["t", "adim", "roll", "pitch", "yaw", "u_reproj", "v_reproj",
               "u_gercek", "v_gercek", "du_norm", "dv_norm", "W", "H",
               "vx", "vy", "pitch_cmd", "roll_cmd", "yaw_cmd"]


def _world_to_body(vx, vy, yaw_rad):
    """dunya yatay vektor -> govde (fwd, right). ana_kontrol.world_to_body ile ayni."""
    c, s = math.cos(yaw_rad), math.sin(yaw_rad)
    return vx * c + vy * s, vx * s - vy * c


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
    kayitlar = [k for k in kayitlar if k.get("du_norm") not in (None, "")]  # siluetli kareler
    if not kayitlar:
        return {"n": 0, "sonuc": "reproj/siluet verisi yok (hedef siluet bulunamadi)"}
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


def komut_eksen_analiz(kayitlar):
    """TESHIS-1: komut -> dunya-tepki eksen/isaret. Saf pitch/roll/yaw adimlarinda
    govde-cercevesi hiz (fwd/right) + heading degisimi olculur; beklenen eksene
    karsi dominant olculen eksen + isaret. Reproj tablosuyla YAN YANA konur (ayni
    konvansiyon hatasini paylasabilirler)."""
    from collections import defaultdict
    grup = defaultdict(list)
    for k in kayitlar:
        ad = k.get("adim", "")
        if ad and ad != "hover":
            grup[ad].append(k)
    bekle = {"pitch+": ("fwd", +1), "pitch-": ("fwd", -1),
             "roll+": ("right", +1), "roll-": ("right", -1),
             "yaw+": ("yawrate", +1), "yaw-": ("yawrate", -1)}
    tablo = []
    for ad, ks in sorted(grup.items()):
        if ad not in bekle:
            continue
        fwd, right = [], []
        for k in ks:
            f, r = _world_to_body(k.get("vx") or 0.0, k.get("vy") or 0.0,
                                  math.radians(k.get("yaw") or 0.0))    # yaw derece->rad
            fwd.append(f); right.append(r)
        mf = sum(fwd) / len(fwd) if fwd else 0.0
        mr = sum(right) / len(right) if right else 0.0
        yawrate = _lin_katsayi([(k.get("t") or 0.0) for k in ks],
                               [(k.get("yaw") or 0.0) for k in ks]) if len(ks) > 2 else 0.0
        olcu = {"fwd": mf, "right": mr, "yawrate": yawrate}
        dominant = max(olcu, key=lambda a: abs(olcu[a]))
        bek_eks, bek_is = bekle[ad]
        isaret_ok = (olcu[bek_eks] * bek_is > 0) if abs(olcu[bek_eks]) > 1e-6 else None
        tablo.append({"adim": ad, "beklenen": ("%s%s" % ("+" if bek_is > 0 else "-", bek_eks)),
                      "fwd": mf, "right": mr, "yawrate": yawrate, "dominant": dominant,
                      "eksen_ok": (dominant == bek_eks), "isaret_ok": isaret_ok})
    return tablo


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
    onceki = {"t": None, "pos": None}
    for ad, pcmd, rcmd, ycmd, sure in ADIM_DIZISI:
        t_adim = time.perf_counter()
        while time.perf_counter() - t_adim < sure:
            drone.set_control_surfaces(0.55, pcmd, rcmd, ycmd, True)   # hover throttle + adim
            dbg = drone.get_debug_truth()
            if not dbg.get("available"):
                continue
            tnow = time.perf_counter()
            tpos = np.array(dbg["target"]["position"], float)
            dpos = np.array(drone.get_drone_gps(), float)
            roll, pitch, yaw = drone.get_drone_rotation()          # derece
            # dunya yatay hiz (konum farki)
            vx = vy = 0.0
            if onceki["pos"] is not None and onceki["t"] is not None:
                dt = tnow - onceki["t"]
                if dt > 1e-3:
                    vx = (dpos[0] - onceki["pos"][0]) / dt
                    vy = (dpos[1] - onceki["pos"][1]) / dt
            onceki = {"t": tnow, "pos": dpos}
            fr, _kaynak = kare_al(sct, cv2)
            H, W = fr.shape[:2]
            uvn = reproj_norm(tpos, dpos, roll, pitch, yaw, W, H)
            det = None
            if uvn is not None and cv2 is not None:
                det, _neden = _siluet_tespit(fr, (uvn[0] * W, uvn[1] * H), cv2)
            k = {"t": round(tnow - t0, 2), "adim": ad, "roll": roll, "pitch": pitch,
                 "yaw": yaw, "W": W, "H": H, "vx": vx, "vy": vy,      # yaw derece
                 "pitch_cmd": pcmd, "roll_cmd": rcmd, "yaw_cmd": ycmd}
            if uvn is not None and det:                # reproj sweep verisi (siluet varsa)
                ug, vg = det["cx"] / W, det["cy"] / H
                k.update({"u_reproj": uvn[0], "v_reproj": uvn[1], "u_gercek": ug, "v_gercek": vg,
                          "du_norm": ug - uvn[0], "dv_norm": vg - uvn[1]})
            kayit.append(k)
            time.sleep(0.05)
    drone.set_control_surfaces(0.0, 0.0, 0.0, 0.0, True)     # hover birak
    if csv_yol and kayit:
        with open(csv_yol, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=KAYIT_KOLON, restval="", extrasaction="ignore")
            w.writeheader()
            for k in kayit:
                w.writerow(k)
        print("[KAYIT] %d ornek -> %s" % (len(kayit), csv_yol))
    _rapor(eksen_analiz(kayit), komut_eksen_analiz(kayit))
    return 0


def _rapor(analiz, komut_tablo=None):
    print("=" * 68)
    print(" ATTITUDE KONVANSIYON ANALIZI (A: telemetri->kamera reprojeksiyon)")
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
    if komut_tablo is not None:
        print("\n" + "=" * 68)
        print(" KOMUT->DUNYA-TEPKI EKSEN TABLOSU (B: TESHIS-1)")
        print("=" * 68)
        print(" %-8s %-9s %10s %10s %10s  %-8s %s" %
              ("adim", "beklenen", "fwd", "right", "yawrate", "dominant", "isaret"))
        for r in komut_tablo:
            iok = "-" if r["isaret_ok"] is None else ("OK" if r["isaret_ok"] else "TERS")
            eok = "" if r["eksen_ok"] else "  <== EKSEN SAPMASI"
            print(" %-8s %-9s %10.1f %10.1f %10.2f  %-8s %s%s"
                  % (r["adim"], r["beklenen"], r["fwd"], r["right"], r["yawrate"],
                     r["dominant"], iok, eok))
        print(" NOT: A ve B AYNI konvansiyon hatasini paylasabilir (telemetri->kamera")
        print("      ve komut->hareket); yan yana oku. Duzeltme kamera_model/komut-cevrim")
        print("      TEK noktadan; sonra iki tablo da temiz olana dek tekrar kos.")


def _analiz_csv(yol):
    kayit = []
    with open(yol, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            k = {}
            for key, v in r.items():
                if key == "adim":
                    k[key] = v
                    continue
                try:
                    k[key] = float(v)
                except (TypeError, ValueError):
                    k[key] = None
            kayit.append(k)
    _rapor(eksen_analiz(kayit), komut_eksen_analiz(kayit))


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

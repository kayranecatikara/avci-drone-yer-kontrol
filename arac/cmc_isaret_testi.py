# -*- coding: utf-8 -*-
"""
================================================================================
GELISTIRME/DOGRULAMA ARACI — gorev ucusunda ve degerlendirme kosusunda
kullanilmaz. (Truth-tabanli; teslim paketine girmez.)
================================================================================
CMC ISARET TESTI (FAZ 1 kabul kriteri) — UCUSLU
================================================================================
Amac: gyro-CMC homografisinin (kamera_model.cmc_homografi) SIM'in attitude
isaret/eksen konvansiyonuyla TUTARLI oldugunu canli dogrulamak. Isaret hatasi
CMC'yi duzeltme yerine BOZUCU yapar (kaymayi 2x'ler); unit test yalniz
kamera_model'in KENDI konvansiyonunu dogrular, sim'in gercek isaretini DEGIL.

YONTEM (YOLO'suz — best.pt kucuk hedefi goremiyor): hedefin goruntudeki gercek
pikseli TRUTH reprojeksiyonundan alinir (truth avci attitude'undan bagimsiz
dunya konumu; guvenilir). Avciya kucuk YAW ve ROLL osilasyonu verilir; ardisik
kareler arasi:
  p1 = truth reproj (frame t1),  p2 = truth reproj (frame t2, attitude degisti)
  CMC tahmini: p2_tahmin = H(att1->att2) · p1
  hata_CMC  = |p2_tahmin - p2|   (warp uygulandi)
  hata_HAM  = |p1 - p2|          (warp yok — track oldugu yerde kalir)
CMC dogru isarette ise hata_CMC << hata_HAM (avci-donusu kaymasi telafi edilir).
Isaret TERS ise hata_CMC > hata_HAM (bozucu). Kabul: medyan(hata_CMC) <
0.5·medyan(hata_HAM) VE eksen-ayrimi (yaw fazi yatay, roll fazi ~konum-bagimli).

UCUSLU: arm + yaw/roll osilasyonu + irtifa P-tutucu. kosu_yonetici bu turu
ucuslu=True ile calistirir -> tur sonrasi oyun KOMPLE restart (zombilesme).
kosu(drone, sure_s) BAGLI drone moduluyle cagrilir (tek TCP oturumu).
================================================================================
"""
import math
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJ_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _PROJ_ROOT)

import numpy as np

from detection import kamera_model as km

YAW_GENLIK = 0.35       # yaw osilasyon komut genligi
ROLL_GENLIK = 0.12      # roll osilasyon komut genligi (~+-8 deg; hedef merkezde kalsin;
                        # buyuk roll drone'u yatirinca hedef FOV'dan cikip roll fazi bosalir)
PERIYOT_S = 3.0         # osilasyon periyodu
KENAR_PAY = 60          # truth reproj bu kadar kenara yakinsa kareyi alma


def _reproj_piksel(drone, W, H):
    """Truth hedefin goruntu pikseli (u,v) + attitude. FOV disi/arka -> None."""
    dpos = np.array(drone.get_drone_location(), float)
    drot = drone.get_drone_rotation()
    tr = drone.get_debug_truth()
    if not tr.get("available"):
        return None
    tpos = np.array(tr["target"]["position"], float)
    pk = km.dunya_to_kamera(tpos, dpos, drot[0], drot[1], drot[2])
    if pk[2] <= 0:
        return None
    uv = km.izdusur(pk, km.K_matrisi(W, H))
    if uv is None or not (KENAR_PAY <= uv[0] < W - KENAR_PAY
                          and KENAR_PAY <= uv[1] < H - KENAR_PAY):
        return None
    return (uv[0], uv[1], (drot[0], drot[1], drot[2]))


def kosu(drone, sure_s=40.0, W=1920, H=1080):
    """BAGLI drone ile CMC isaret testi. Sonuc dict | None."""
    # irtifa referansi = hedef yorunge irtifasi (gecisler FOV'da kalsin)
    ornek = []
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < 1.5:
        tr = drone.get_debug_truth()
        if tr.get("available"):
            ornek.append(float(tr["target"]["position"][2]))
        time.sleep(0.05)
    if not ornek:
        print("[CMC] Truth AKMIYOR.")
        return None
    z_ref = float(np.median(ornek))
    z0 = float(drone.get_drone_location()[2])
    print("[CMC] irtifa referansi %.1f m (drone %.1f m). Arm + irtifaya cikiliyor..."
          % (z_ref / 100.0, z0 / 100.0))

    def _irtifa_thr():
        dz = (float(drone.get_drone_location()[2]) - z_ref) / 100.0
        return max(-0.40, min(0.40, -0.10 * dz)), dz

    # irtifaya cik (arm) — en cok 100 sn
    tc = time.perf_counter()
    while time.perf_counter() - tc < 100.0:
        thr, dz = _irtifa_thr()
        drone.set_control_surfaces(thr, 0.0, 0.0, 0.0, True)
        if abs(dz) < 4.0:
            break
        time.sleep(0.1)
    thr, dz = _irtifa_thr()
    if abs(dz) > 25.0:
        print("[CMC][HATA] Irtifaya OTURULAMADI (sapma %+.1f m) - oturum bozulmus?" % dz)
        return None
    print("[CMC] irtifa tutuldu (%+.1f m). Osilasyon + olcum basliyor." % dz)

    import cv2
    import mss
    import k_sanity_olcum as ks
    sct = mss.mss()

    onceki = None            # (u, v, att)
    yaw_kayit = []           # yaw-baskin fazlarda (hata_ham, hata_cmc, du_ham, du_cmc)
    roll_kayit = []
    t_baslat = time.perf_counter()
    while time.perf_counter() - t_baslat < sure_s:
        t = time.perf_counter() - t_baslat
        # yaw ve roll AYRI fazlarda (eksen ayrimi): ilk yari yaw, ikinci yari roll
        faz_yaw = t < sure_s / 2.0
        thr, _dz = _irtifa_thr()
        if faz_yaw:
            yaw = YAW_GENLIK * math.sin(2 * math.pi * t / PERIYOT_S)
            drone.set_control_surfaces(thr, 0.0, 0.0, yaw, True)
        else:
            roll = ROLL_GENLIK * math.sin(2 * math.pi * t / PERIYOT_S)
            drone.set_control_surfaces(thr, 0.0, roll, 0.0, True)

        p = _reproj_piksel(drone, W, H)
        if p is not None and onceki is not None:
            u1, v1, att1 = onceki
            u2, v2, att2 = p
            Hcmc = km.cmc_homografi(W, H, att1, att2)
            q = Hcmc @ np.array([u1, v1, 1.0])
            up, vp = q[0] / q[2], q[1] / q[2]
            hata_ham = math.hypot(u1 - u2, v1 - v2)         # warp yok
            hata_cmc = math.hypot(up - u2, vp - v2)         # warp uygulandi
            if hata_ham > 1.0:                              # anlamli hareket olan kareler
                kayit = (hata_ham, hata_cmc, u2 - u1, up - u1)
                (yaw_kayit if faz_yaw else roll_kayit).append(kayit)
        onceki = p
        time.sleep(0.03)

    drone.set_control_surfaces(0.0, 0.0, 0.0, 0.0, True)    # hover birak
    if len(yaw_kayit) < 8:
        print("[CMC] Yeterli yaw-faz eslesmesi yok (%d)." % len(yaw_kayit))
        return None
    ya = np.array(yaw_kayit)
    ham_med = float(np.median(ya[:, 0]))
    cmc_med = float(np.median(ya[:, 1]))
    oran = cmc_med / max(ham_med, 1e-9)
    sonuc = {"n_yaw": len(yaw_kayit), "n_roll": len(roll_kayit),
             "yaw_ham_med": ham_med, "yaw_cmc_med": cmc_med, "oran": oran,
             "gecti": oran < 0.5}
    if roll_kayit:
        ra = np.array(roll_kayit)
        sonuc["roll_ham_med"] = float(np.median(ra[:, 0]))
        sonuc["roll_cmc_med"] = float(np.median(ra[:, 1]))
        sonuc["roll_oran"] = sonuc["roll_cmc_med"] / max(sonuc["roll_ham_med"], 1e-9)
    print("[CMC] YAW fazi: n=%d | hata_HAM medyan %.1f px -> hata_CMC medyan %.1f px"
          " (oran %.2f)" % (len(yaw_kayit), ham_med, cmc_med, oran))
    if roll_kayit:
        print("[CMC] ROLL fazi: hata_HAM %.1f -> hata_CMC %.1f (oran %.2f)"
              % (sonuc["roll_ham_med"], sonuc["roll_cmc_med"], sonuc["roll_oran"]))
    print("[CMC] SONUC: %s (CMC dogru isarette kaymayi %s)"
          % ("GECTI" if sonuc["gecti"] else "KALDI",
             "AZALTIYOR" if sonuc["gecti"] else "AZALTMIYOR/BOZUYOR -> isaret/eksen suphesi"))
    return sonuc


if __name__ == "__main__":
    from sdk import drone_sdk as drone
    if not drone.connect():
        print("BAGLANTI YOK")
        sys.exit(1)
    time.sleep(1.5)
    r = kosu(drone, 40.0)
    try:
        drone.set_control_surfaces(0.0, 0.0, 0.0, 0.0, True)
    except Exception:
        pass
    drone.disconnect()
    sys.exit(0 if (r and r.get("gecti")) else 1)

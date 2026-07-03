# -*- coding: utf-8 -*-
"""
================================================================================
GELISTIRME/DOGRULAMA ARACI — gorev ucusunda ve degerlendirme kosusunda
kullanilmaz. (Truth-tabanli; teslim paketine girmez.)
================================================================================
HAREKET-FARKI HAKEMI — YOLO'suz hedef piksel konumu + K acisal dogrulama
================================================================================
Drone SABIT + sahne statik iken ardisik kare farkindaki en buyuk hareketli leke
= ucan Talon. Bu, hedefin goruntudeki konumunu TESPIT MODELINDEN BAGIMSIZ verir
(best.pt kucuk/uzak hedefi goremiyor). Iki kullanim:

  1) ZINCIR/K ACISAL DOGRULAMA (FAZ 0): leke merkezi vs truth-reprojeksiyon
     acisal offset'i. fx yanlissa reproj merkez-disi hedefte ORANTILI kayar
     (du ~ ex*(1-k)*(W/2)); du~ex regresyon egiminden fx olcek kestirimi
     k = 1 + egim/(W/2). k~1 -> HFOV=125 dogru; k~0.46 -> %54 hata.
  2) CMC ISARET TESTI (FAZ 1): hedef sabitken avciya saf yaw/roll step verilir;
     CMC acikken leke bbox uzerinde kalmali, kapaliyken kaymali (o testte bu
     modul lekenin GERCEK konumunu saglar, CMC tahmini ustune bindirilir).

kosu(drone, sure_s) BAGLI bir drone moduluyle cagrilir (tek TCP oturumu).
Goruntu-tabanli CMC (ORB/ECC) DEGIL: yalniz hareket-farki + truth referansi.
================================================================================
"""
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJ_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _PROJ_ROOT)
sys.path.insert(0, _HERE)

import numpy as np

GOK_SINIR = 0.55        # goruntunun ust %55'i: gokyuzu bolgesi (cimen/insan disari)
KENAR_PAY = 40          # reproj bu kadar kenara yakinsa eslestirme yapma


def kosu(drone, sure_s=30.0):
    """BAGLI drone moduluyle hareket-farki hakemi. Sonuc dict | None (yetersiz).
    {n, yatay_med_deg, yatay_mad_deg, dikey_med_deg, dikey_mad_deg,
     k_kestirim, du_ex_egim, ex_aralik, ornek_png}"""
    import cv2
    import mss
    import k_sanity_olcum as ks
    from detection import kamera_model as km

    sct = mss.mss()
    onceki = None
    kayit = []
    ornek_kare = None
    t0 = time.perf_counter()
    print("[HAKEM] %.0f sn hareket-farki (gokyuzu + ekran-ici reproj)..." % sure_s)
    while time.perf_counter() - t0 < sure_s:
        dpos = np.array(drone.get_drone_location(), float)
        drot = drone.get_drone_rotation()
        tpos = np.array(drone.get_debug_truth()["target"]["position"], float)
        fr, _kaynak = ks.kare_al(sct, cv2, genislik=0)
        H, W = fr.shape[:2]
        fx = km.fx_px(W)
        gri = cv2.GaussianBlur(cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY), (5, 5), 0)
        R = float(np.linalg.norm(tpos - dpos)) / 100.0
        pk = km.dunya_to_kamera(tpos, dpos, drot[0], drot[1], drot[2])
        uv = km.izdusur(pk, km.K_matrisi(W, H)) if pk[2] > 0 else None
        ekran_ici = (uv is not None and KENAR_PAY <= uv[0] < W - KENAR_PAY
                     and KENAR_PAY <= uv[1] < H * GOK_SINIR - KENAR_PAY)
        if onceki is not None and ekran_ici:
            fark = cv2.absdiff(gri, onceki)
            fark[int(H * GOK_SINIR):, :] = 0              # yalniz gokyuzu
            fark[:95, :260] = 0                           # OSD sol-ust
            fark[:140, W - 340:] = 0                      # OSD sag-ust
            _, esik = cv2.threshold(fark, 16, 255, cv2.THRESH_BINARY)
            esik = cv2.dilate(esik, np.ones((3, 3), np.uint8), 1)
            konturlar, _ = cv2.findContours(esik, cv2.RETR_EXTERNAL,
                                            cv2.CHAIN_APPROX_SIMPLE)
            adaylar = []
            for c in konturlar:
                if cv2.contourArea(c) < 4:
                    continue
                x, y, bw, bh = cv2.boundingRect(c)
                adaylar.append((x + bw / 2.0, y + bh / 2.0, bw, bh))
            if adaylar:
                bx, by, bw, bh = min(
                    adaylar, key=lambda a: (a[0] - uv[0]) ** 2 + (a[1] - uv[1]) ** 2)
                du, dv = bx - uv[0], by - uv[1]
                ex = (uv[0] - W / 2.0) / (W / 2.0)         # merkez-disilik (K-testi)
                kayit.append((R, du, dv,
                              float(np.degrees(np.arctan(du / fx))),
                              float(np.degrees(np.arctan(dv / fx))), bw, bh, ex))
                if ornek_kare is None or R < ornek_kare[0]:
                    ci = fr.copy()
                    cv2.circle(ci, (int(uv[0]), int(uv[1])), 30, (0, 0, 255), 3)
                    cv2.rectangle(ci, (int(bx - bw / 2), int(by - bh / 2)),
                                  (int(bx + bw / 2), int(by + bh / 2)), (0, 255, 0), 3)
                    ornek_kare = (R, ci)
        onceki = gri
        time.sleep(0.15)

    if len(kayit) < 8:
        print("[HAKEM] Yeterli eslesme yok (%d)." % len(kayit))
        return None
    a = np.array(kayit)
    # K DOGRULAMA (pozitif): du_reproj=(u-cx)=fx*tan(aci). fx yanlissa reproj
    # merkez-disi hedefte merkez-disilikle ORANTILI kayar: du ~ ex*(1-k)*(W/2),
    # k=fx_gercek/fx_varsayim. du'yu ex'e regresyonla fit et; egim ~0 -> fx dogru.
    ex = a[:, 7]
    du = a[:, 1]
    W2 = 1920.0 / 2.0
    if float(np.std(ex)) > 0.05:
        egim, _kesim = np.polyfit(ex, du, 1)
        k_kestirim = 1.0 + egim / W2
    else:
        egim = k_kestirim = float("nan")
    sonuc = {"n": len(a),
             "yatay_med_deg": float(np.median(a[:, 3])),
             "yatay_mad_deg": float(np.median(np.abs(a[:, 3] - np.median(a[:, 3])))),
             "dikey_med_deg": float(np.median(a[:, 4])),
             "dikey_mad_deg": float(np.median(np.abs(a[:, 4] - np.median(a[:, 4])))),
             "k_kestirim": float(k_kestirim), "du_ex_egim": float(egim),
             "ex_aralik": (float(ex.min()), float(ex.max())),
             "ornek_png": None}
    print("[HAKEM] eslesme: %d | mesafe %.0f-%.0f m" % (len(a), a[:, 0].min(), a[:, 0].max()))
    print("[HAKEM] yatay medyan %+.1f deg (MAD %.1f) | dikey medyan %+.1f deg (MAD %.1f)"
          % (sonuc["yatay_med_deg"], sonuc["yatay_mad_deg"],
             sonuc["dikey_med_deg"], sonuc["dikey_mad_deg"]))
    print("[HAKEM] K DOGRULAMA: ex araligi %.2f..%.2f | du~ex egimi %.1f px ->"
          % (ex.min(), ex.max(), egim))
    print("        fx olcek k = %.3f (1.00 = HFOV 125 dogru; %%54 hata k~0.46 verirdi)"
          % k_kestirim)
    if ornek_kare is not None:
        yol = os.path.join(_PROJ_ROOT, "veri", "hakem_ornek.png")
        cv2.imwrite(yol, ornek_kare[1])
        sonuc["ornek_png"] = yol
    return sonuc


if __name__ == "__main__":
    from sdk import drone_sdk as drone
    if not drone.connect():
        print("BAGLANTI YOK")
        sys.exit(1)
    time.sleep(1.5)
    if not drone.get_debug_truth().get("available"):
        print("TRUTH YOK")
        drone.disconnect()
        sys.exit(1)
    r = kosu(drone, 40.0)
    drone.disconnect()
    sys.exit(0 if r else 1)

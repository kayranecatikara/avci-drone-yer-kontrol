# -*- coding: utf-8 -*-
"""
================================================================================
 ONIZLE — kayitli karelere truth pozdan 6 keypoint ciz (GORSEL DOGRULAMA KAPISI)
================================================================================
Faz 1 kaydindan kareleri alir, her karede hedefin TRUTH konumu + rotasyonundan
6 Talon keypoint'ini (talon_keypoints.json) projekte edip uzerine cizer. Amac:
GEOMETRININ dogru oldugunu GOZLE dogrulamak (tilt=0? pivot=AM? eksen isaretleri?).
Noktalar Talon'un burun/kanat/kuyruk uclarina OTURUYORSA geometri dogru -> etiketleme
ve egitime gecebiliriz. Sistematik kayma varsa buradan anlasilir (bkz. asagi).

Kullanim (repo kokunden):
    python pose\\onizle.py                         # en son oturumu bul, 30 kare ciz
    python pose\\onizle.py --oturum C:\\...\\oturum_XX  --sayi 40
    python pose\\onizle.py --hepsi                 # tum kareler (cok olabilir)

Cikti: <oturum>\\onizle\\*.png  (nokta + iskelet + indeks + mesafe yazili)

Kayma teshisi (nokta Talon'a oturmuyorsa):
  * Noktalar araca YAPISIK ama sabit DIKEY kayik  -> tilt yanlis (KAMERA_TILT_DEG).
  * Noktalar araca YAPISIK ama sabit her yone kayik-> pivot != AM (keypoint origin ofseti).
  * Noktalar araci sarmis ama sol/sag TERS          -> Y ekseni isareti / flip.
  * Noktalar cok yayvan/dar (uctan tasip/icde)      -> HFOV yanlis.
  * Noktalar araÇtan bagimsiz her yerde             -> rotasyon senkronu/bozulmasi (o kareyi at).
"""
import os
import sys
import glob
import json
import argparse

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _KOK not in sys.path:
    sys.path.insert(0, _KOK)

import numpy as np
import cv2

from pose import geometri


# nokta indeksleri: 0 burun,1 sol_kanat,2 sag_kanat,3 sol_kuyruk,4 sag_kuyruk,5 kuyruk_arka
ISKELET = [(0, 5), (1, 2), (0, 1), (0, 2), (3, 5), (4, 5), (3, 4)]
# BGR renkler (nokta basina)
RENK = [(0, 0, 255), (0, 255, 0), (0, 200, 255), (255, 128, 0),
        (255, 0, 255), (255, 255, 0)]


def _en_son_oturum(kok=r"C:\talon_pose_data\ham"):
    ler = sorted(glob.glob(os.path.join(kok, "oturum_*")))
    return ler[-1] if ler else None


def _ciz(kare, uv, W, H, d_m, corr):
    img = kare.copy()
    # iskelet
    for a, b in ISKELET:
        if uv[a] is not None and uv[b] is not None:
            pa = (int(round(uv[a][0])), int(round(uv[a][1])))
            pb = (int(round(uv[b][0])), int(round(uv[b][1])))
            cv2.line(img, pa, pb, (255, 255, 255), 1, cv2.LINE_AA)
    # noktalar + indeks
    for i, p in enumerate(uv):
        if p is None:
            continue
        c = (int(round(p[0])), int(round(p[1])))
        cv2.circle(img, c, 4, RENK[i], -1, cv2.LINE_AA)
        cv2.circle(img, c, 4, (0, 0, 0), 1, cv2.LINE_AA)
        cv2.putText(img, str(i), (c[0] + 5, c[1] - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, RENK[i], 1, cv2.LINE_AA)
    # ekran merkezi +
    cv2.drawMarker(img, (W // 2, H // 2), (0, 255, 255), cv2.MARKER_CROSS, 16, 1)
    # bilgi
    txt = "d=%.1fm  corr=%d" % (d_m, corr)
    cv2.putText(img, txt, (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(img, txt, (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                (255, 255, 255), 1, cv2.LINE_AA)
    return img


def calistir(args):
    oturum = args.oturum or _en_son_oturum()
    if not oturum or not os.path.isdir(oturum):
        print("[HATA] Oturum bulunamadi. --oturum ile yol ver ya da once kayit al.")
        return 1
    jsonl_yol = os.path.join(oturum, "telemetri.jsonl")
    if not os.path.isfile(jsonl_yol):
        print("[HATA] telemetri.jsonl yok:", jsonl_yol)
        return 1

    _, kp_cm, _ = geometri.keypointleri_yukle()

    satirlar = []
    with open(jsonl_yol, "r", encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if ln:
                satirlar.append(json.loads(ln))
    if not satirlar:
        print("[HATA] Kayitta hic kare yok (kayit=0 miydi?). Once dolu bir oturum al.")
        return 1

    if args.hepsi or args.sayi >= len(satirlar):
        secili = satirlar
    else:
        idx = np.linspace(0, len(satirlar) - 1, args.sayi).round().astype(int)
        secili = [satirlar[i] for i in idx]

    cikti = os.path.join(oturum, "onizle")
    os.makedirs(cikti, exist_ok=True)
    print("[ONIZLE] oturum: %s" % oturum)
    print("[ONIZLE] %d/%d kare cizilecek -> %s" % (len(secili), len(satirlar), cikti))

    yazilan = 0
    for s in secili:
        kare_yol = os.path.join(oturum, s["kare"])
        kare = cv2.imread(kare_yol)
        if kare is None:
            continue
        W, H = int(s["W"]), int(s["H"])
        cam_pos, R_cam = geometri.kamera_pozu(s["drone_pos"], s["drone_rot_rpy"])
        fx = geometri.fx_from_hfov(W)
        kp_world = geometri.keypoints_dunyada(
            s["truth_target_pos"], s["target_rot_rpy"], kp_cm)
        uv = [geometri.projekte(p, cam_pos, R_cam, fx, W, H) for p in kp_world]
        img = _ciz(kare, uv, W, H, s.get("mesafe_cm", 0) / 100.0,
                   int(s.get("corruption_mask", 0)))
        cv2.imwrite(os.path.join(cikti, "onizle_" + s["kare"]), img)
        yazilan += 1

    print("[ONIZLE] bitti: %d gorsel yazildi." % yazilan)
    print("[ONIZLE] Klasoru ac ve GOZLE bak: noktalar Talon'un uclarina oturuyor mu?")
    try:
        os.startfile(cikti)          # Windows: klasoru otomatik ac
    except Exception:
        pass
    return 0


def main():
    ap = argparse.ArgumentParser(description="Kayitli karelere keypoint ciz (gorsel dogrulama)")
    ap.add_argument("--oturum", default=None, help="oturum klasoru (vars: en son)")
    ap.add_argument("--sayi", type=int, default=30, help="cizilecek kare sayisi (vars: 30)")
    ap.add_argument("--hepsi", action="store_true", help="tum kareleri ciz")
    sys.exit(calistir(ap.parse_args()))


if __name__ == "__main__":
    main()

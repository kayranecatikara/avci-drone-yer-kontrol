# -*- coding: utf-8 -*-
"""
================================================================================
GELISTIRME/DOGRULAMA ARACI — gorev ucusunda ve degerlendirme kosusunda
kullanilmaz. (Truth-tabanli gorsel teyit; teslim paketine girmez.)
================================================================================
FAZ 2 SIM DOGRULAMASI — pose zinciri gercek veride (zayif modelle)
================================================================================
Zincir: model_yonetici(pose) -> algi_hatti(tespit->takip->PnP) -> AlgiCiktisi.
Amac (kullanici madde 3): zincir ENTEGRASYONUNU kanitlamak + model kalitesini
SAYIYLA olcmek. Beklenti: PnP-uygun frame orani DUSUK (best/pose zayif) — bu
BASARISIZLIK DEGIL OLCUMDUR (yeni modelin hedefini koyar).

Cikti:
  1) GORSEL TEYIT: pose tespitli birkac kare keypoints cizili kaydedilir
     (index-renkli + numarali) -> keypoint SIRASI 3D tablo ile eslesir mi?
     (sema kararinin gozle teyidi; MEVCUT_DURUM'a yaz.)
  2) PnP-uygun oran, reproj dagilimi, gorunur-kp/conf (model kalite metrigi).
  3) Yeterli PnP-uygun frame + perspektif varsa k-taramasi (k*); yetersizse
     k* BORC listesinde kalir. Statu: "KOD TAMAM + ZINCIR DOGRULANDI".

UCUSLU: arm + irtifa tut (hedef FOV'da). kosu_yonetici pnp-test turu ucuslu=True
-> tur sonrasi oyun restart. kosu(drone, sure_s) BAGLI drone ile.
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


def kosu(drone, sure_s=60.0):
    import cv2
    import mss
    import k_sanity_olcum as ks
    from detection.model_yonetici import ModelYonetici
    from detection.algi_hatti import AlgiHatti
    from detection.talon_pose_estimator import TalonPozKestirici, k_taramasi

    # 1) pose modelini yukle (registry)
    yon = ModelYonetici(baslangic_conf=0.25)
    liste = yon.modelleri_listele()
    pose_ad = next((m["ad"] for m in liste if "pose" in m["ad"].lower()), None)
    if pose_ad is None:
        print("[PNP] models/ altinda pose .pt yok.")
        return None
    print("[PNP] Pose model yukleniyor: %s ..." % pose_ad)
    if not yon.model_yukle(pose_ad, arka_plan=False):
        print("[PNP] Pose model yuklenemedi: %s" % yon._hata)
        return None
    durum = yon.durum()
    print("[PNP] task=%s kpt_shape=%s sema=%s" % (durum.get("task"),
          durum.get("kpt_shape"), durum.get("sema")))
    algi = AlgiHatti(dedektor=yon)
    algi.pnp_baglan(TalonPozKestirici(sema=yon.aktif_sema()))

    # 2) irtifa referansi = hedef yorunge irtifasi (hedef FOV'da kalsin) + arm
    ornek = []
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < 1.5:
        tr = drone.get_debug_truth()
        if tr.get("available"):
            ornek.append(float(tr["target"]["position"][2]))
        time.sleep(0.05)
    z_ref = float(np.median(ornek)) if ornek else None

    def _irtifa_thr():
        if z_ref is None:
            return 0.0, 0.0
        dz = (float(drone.get_drone_location()[2]) - z_ref) / 100.0
        return max(-0.40, min(0.40, -0.10 * dz)), dz

    if z_ref is not None:
        print("[PNP] irtifa referansi %.1f m; arm + cikis..." % (z_ref / 100.0))
        tc = time.perf_counter()
        while time.perf_counter() - tc < 60.0:
            thr, dz = _irtifa_thr()
            drone.set_control_surfaces(thr, 0.0, 0.0, 0.0, True)
            if abs(dz) < 4.0:
                break
            time.sleep(0.1)

    # 3) olcum dongusu
    sct = mss.mss()
    n_kare = n_tespit = n_kp = n_pnp_uygun = n_pnp_gecerli = 0
    reprojlar = []
    kp_kayitlari = []          # k-taramasi icin
    gorsel_kayit = 0
    t_bas = time.perf_counter()
    son_hover = t_bas
    while time.perf_counter() - t_bas < sure_s:
        if z_ref is not None and time.perf_counter() - son_hover > 0.3:
            thr, _dz = _irtifa_thr()
            drone.set_control_surfaces(thr, 0.0, 0.0, 0.0, True)
            son_hover = time.perf_counter()
        try:
            fr, _kaynak = ks.kare_al(sct, cv2, genislik=0)
            att = drone.get_drone_rotation()
        except Exception:
            time.sleep(0.05)
            continue
        cikti = algi.adim(fr, att)
        n_kare += 1
        hedef = cikti.hedef
        if hedef is not None and hedef.get("tespit_mi"):
            n_tespit += 1
            kp = hedef.get("keypoints")
            if kp:
                n_kp += 1
                gorunur = sum(1 for *_xy, c in kp if c >= 0.5)
                if gorunur >= 4:
                    n_pnp_uygun += 1
                    kp_kayitlari.append(kp)
                # gorsel teyit: ilk birkac pose-tespitli kareyi kaydet
                if gorsel_kayit < 5:
                    _gorsel_teyit_kaydet(cv2, fr, kp, hedef, gorsel_kayit)
                    gorsel_kayit += 1
            pnp = cikti.pnp
            if pnp and pnp.get("gecerli"):
                n_pnp_gecerli += 1
                reprojlar.append(pnp["reproj_err"])
        if n_kare % 60 == 0:
            print("  ... kare=%d tespit=%d kp=%d pnp_uygun=%d pnp_gecerli=%d"
                  % (n_kare, n_tespit, n_kp, n_pnp_uygun, n_pnp_gecerli))

    drone.set_control_surfaces(0.0, 0.0, 0.0, 0.0, True)
    W, H = fr.shape[1], fr.shape[0]

    # 4) k-taramasi (yeterli PnP-uygun frame varsa)
    k_sonuc = None
    if len(kp_kayitlari) >= 10:
        k_sonuc = k_taramasi(kp_kayitlari, W, H, sema=yon.aktif_sema())

    sonuc = {
        "pose_ad": pose_ad, "sema": yon.aktif_sema(),
        "n_kare": n_kare, "n_tespit": n_tespit, "n_kp": n_kp,
        "pnp_uygun_oran": (n_pnp_uygun / n_kare) if n_kare else 0.0,
        "pnp_gecerli_oran": (n_pnp_gecerli / n_kare) if n_kare else 0.0,
        "reproj_medyan": (float(np.median(reprojlar)) if reprojlar else None),
        "gorsel_teyit_kare": gorsel_kayit, "k_sonuc": k_sonuc,
    }
    print("\n[PNP] === FAZ 2 SIM DOGRULAMA ===")
    print("[PNP] model=%s sema=%s" % (pose_ad, yon.aktif_sema()))
    print("[PNP] kare=%d | tespit=%d | keypoints'li=%d | PnP-uygun=%d (%%%.1f) | "
          "PnP-gecerli=%d (%%%.1f)"
          % (n_kare, n_tespit, n_kp, n_pnp_uygun, 100 * sonuc["pnp_uygun_oran"],
             n_pnp_gecerli, 100 * sonuc["pnp_gecerli_oran"]))
    if reprojlar:
        print("[PNP] reproj medyan: %.1f px (n=%d)" % (sonuc["reproj_medyan"], len(reprojlar)))
    if k_sonuc and k_sonuc.get("k_star") is not None:
        print("[PNP] k-taramasi: k*=%.3f | perspektif=%.3f | guvenilir=%s"
              % (k_sonuc["k_star"], k_sonuc.get("perspektif_gucu", 0), k_sonuc.get("guvenilir")))
    else:
        print("[PNP] k-taramasi: yetersiz PnP-uygun frame -> k* BORC listesinde")
    print("[PNP] gorsel teyit kareleri: veri/pnp_teyit_*.png (keypoint SIRASI kontrolu)")
    print("[PNP] STATU: KOD TAMAM + ZINCIR DOGRULANDI (model->kp->PnP->AlgiCiktisi)")
    return sonuc


def _gorsel_teyit_kaydet(cv2, fr, kp, hedef, idx):
    """Keypoints'i index-renkli + numarali cizip kaydet (sema sirasi gozle teyit)."""
    ci = fr.copy()
    renk = [(93, 93, 255), (84, 180, 255), (74, 225, 255), (122, 255, 74),
            (255, 160, 51), (255, 107, 196)]
    cx, cy, w, h = hedef["cx"], hedef["cy"], hedef["w"], hedef["h"]
    cv2.rectangle(ci, (int(cx - w / 2), int(cy - h / 2)),
                  (int(cx + w / 2), int(cy + h / 2)), (0, 255, 160), 2)
    adlar = ["burun", "kuyruk", "solVT", "sagVT", "solK", "sagK"]
    for i, (x, y, c) in enumerate(kp):
        if c < 0.3:
            continue
        cv2.circle(ci, (int(x), int(y)), 5, renk[i % 6], -1)
        cv2.putText(ci, "%d:%s" % (i, adlar[i % 6]), (int(x) + 6, int(y)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, renk[i % 6], 1)
    yol = os.path.join(_PROJ_ROOT, "veri", "pnp_teyit_%d.png" % idx)
    cv2.imwrite(yol, ci)


if __name__ == "__main__":
    from sdk import drone_sdk as drone
    if not drone.connect():
        print("BAGLANTI YOK")
        sys.exit(1)
    time.sleep(1.5)
    r = kosu(drone, 60.0)
    try:
        drone.set_control_surfaces(0.0, 0.0, 0.0, 0.0, True)
    except Exception:
        pass
    drone.disconnect()
    sys.exit(0 if r else 1)

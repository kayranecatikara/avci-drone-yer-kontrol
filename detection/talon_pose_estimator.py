# -*- coding: utf-8 -*-
"""
================================================================================
TALON POSE ESTIMATOR — PnP poz kestirimi (YARISMA PIPELINE FAZ 2)
================================================================================
Girdi: CONFIRMED track'in keypoints'i (pose modeli yukluyse; detect modelinde
bu faz OTOMATIK pasif -> gecerli=False). Cikti: hedefin kamera/dunya cercevesi
konumu + yonelimi (roll phi_T / yaw psi_T), reproj error, kullanilan kp.

3D MODEL (mm; origin = AM tablo referans merkezi; govde cercevesi SAG-EL:
+X kuyruga/aft, +Y yukari, +Z sol kanat). 1718 mm fiziksel olcek (Z ackligi
+-859.0; SDK'da teyitli). Origin AM oldugundan tvec DOGRUDAN hedef merkezinin
kamera-cercevesi konumudur (burun-origin'e gore yarim govde ~550 mm sistematik
ofset yok). SDK govde uzunlugu 1100 mm; modelde burun->kuyruk_ucu 1087.1 mm
(%1.2 sapma) -> olcek reproj error istatistigiyle teyit, elle "duzeltilmez".

>>> KEYPOINT SIRASI SEMA-PARAMETRELI <<< pose modelinin cikardigi keypoint
sirasi metadata'da YOK -> GORSEL TEYIT sart (FAZ 2 sim). Uc sema destekli:
  "berat_json" (MERGE 2026-07-06, ONERILEN): 3B tablo TEK KAYNAKTAN
      pose/talon_keypoints.json (Berat; sim'de dogrulanmis, flip_idx'li) okunur;
      keypoint SIRASI = talon_pose.pt MODEL CIKTI SIRASI (pose/sira_bul.py ile
      87 karede deneysel bulunan pose.poz_cozucu.EGITIM_SIRASI) ve MESH_PIVOT
      ofseti uygulanir -> tvec = kamera->ACTOR ORIGIN (= get_target_location;
      telemetriyle dogrudan kiyaslanir). models/talon_pose.yaml bunu secer.
  "kuyruk_ucu" (gomulu): burun, kuyruk_ucu, sol_vtail, sag_vtail, sol_kanat, sag_kanat
  "motor"      (gomulu, ESKI): burun, motor, sol_vtail, sag_vtail, sol_kanat, sag_kanat
(Gomulu tablolar SILINMEDI: JSON okunamazsa/başka modelde bayrakla [yaml 'sema']
secilebilir yedek olarak durur. Sayilar zaten ayni preview.jpg tablosundandir.)
Yanlis sira sessizce sacma cozum uretir; ilk belirti anormal reproj error.
Model registry per-model yaml'daki 'sema' ile hangi setin kullanilacagini secer.

OpenCV kamera cercevesi (+X sag, +Y asagi, +Z ileri) object cercevesinden
FARKLIDIR; solvePnP object'i oldugu gibi alir, donusum rvec/tvec'tedir
(eksenler elle "duzeltilmez"). Oryantasyon dunya cercevesine kamera_model
montaj zinciriyle (R_mount 25 tilt) tasinir -> guduum hazir dunya-LOS'u tuketir.

cv2 YOKSA gecerli=False (graceful). Saf sinif: sentetik keypoint'le round-trip
unit-test edilir (test/).
================================================================================
"""
import json
import math
import os

import numpy as np

from detection import kamera_model


# --- 3D model noktalari (mm; origin AM). Ortak 4 nokta + sema-bagimli 2. nokta ---
_BURUN      = (-550.3, -13.2, 0.0)
_KUYRUK_UCU = (536.8, -6.5, 0.0)        # YENI sema (govde arka ucu)
_MOTOR      = (536.8, -6.5, 0.0)        # ESKI sema — konum ayni varsayimi (teyit: gorsel)
_SOL_VTAIL  = (531.6, 179.3, 225.6)
_SAG_VTAIL  = (531.6, 179.3, -225.7)
_SOL_KANAT  = (101.7, 44.9, 859.0)
_SAG_KANAT  = (101.7, 44.9, -859.0)

# Sema -> 6x3 object points (keypoint index sirasi). Registry yaml 'sema' secer.
SEMALAR = {
    "kuyruk_ucu": np.array([_BURUN, _KUYRUK_UCU, _SOL_VTAIL, _SAG_VTAIL,
                            _SOL_KANAT, _SAG_KANAT], dtype=np.float64),
    "motor":      np.array([_BURUN, _MOTOR, _SOL_VTAIL, _SAG_VTAIL,
                            _SOL_KANAT, _SAG_KANAT], dtype=np.float64),
}
VARSAYILAN_SEMA = "kuyruk_ucu"
KP_ADLARI = {
    "kuyruk_ucu": ["burun", "kuyruk_ucu", "sol_vtail", "sag_vtail", "sol_kanat", "sag_kanat"],
    "motor":      ["burun", "motor", "sol_vtail", "sag_vtail", "sol_kanat", "sag_kanat"],
}


def sema_berat_yukle():
    """MERGE 2026-07-06: 'berat_json' semasini pose/talon_keypoints.json'dan kur.

    TEK KAYNAK ilkesi: 3B nokta DEGERLERI json'un `kaynak_tablo_mm` alanindan
    (tablo-mm cercevesi = bu dosyanin obje cercevesi: +X kuyruk, +Y yukari,
    +Z sol kanat — sayilar sim'de dogrulanmis), SIRA ve PIVOT ise Berat'in
    calisan cozucusundan (pose.poz_cozucu.EGITIM_SIRASI / MESH_PIVOT_OFFSET_CM)
    import edilir; burada IKINCI bir kopya tutulmaz.

    pred[k] -> json[EGITIM_SIRASI[k]] esleme geregi obje noktalari MODEL CIKTI
    SIRASINA dizilir. MESH_PIVOT_OFFSET (+11.76 cm ileri, UE) tablo cercevesinde
    -X yonune (-117.6 mm) uygulanir -> cozulen tvec kamera->ACTOR ORIGIN olur
    (= get_target_location; telemetriyle dogrudan kiyas).

    Basarisizsa (json/pose paketi yok) None doner; gomulu semalar aynen kalir."""
    try:
        from pose.poz_cozucu import EGITIM_SIRASI, MESH_PIVOT_OFFSET_CM
        kok = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(kok, "pose", "talon_keypoints.json"), "r",
                  encoding="utf-8") as f:
            d = json.load(f)
        ham = d["kaynak_tablo_mm"]                 # tablo-mm (bizim obje cercevemiz)
        adlar = list(d["keypoint_isimleri"])       # json REF sirasi
        model_adlar = [adlar[i] for i in EGITIM_SIRASI]   # model cikti sirasi
        # UE +X(ileri) pivot ofseti -> tablo cercevesinde -X (tablo +X = kuyruk), mm
        pivot_mm = float(MESH_PIVOT_OFFSET_CM[0]) * 10.0
        obj = np.array([[float(ham[a][0]) - pivot_mm, float(ham[a][1]), float(ham[a][2])]
                        for a in model_adlar], dtype=np.float64)
        SEMALAR["berat_json"] = obj
        KP_ADLARI["berat_json"] = model_adlar
        return "berat_json"
    except Exception as e:
        print("[PNP] berat_json semasi yuklenemedi (%s) -> gomulu semalar kullanilir." % e)
        return None


# Modul yuklenirken dene (graceful): pose/ paketi + json varsa sema kayitli olur,
# yoksa sessizce gomulu semalarla devam edilir (pose'suz kurulum bozulmaz).
sema_berat_yukle()


class PnPCfg:
    KP_CONF_ESIK  = 0.5     # bu conf ustundeki keypoint PnP'ye girer
    MIN_KP        = 4       # < 4 nokta -> gecerli=False (P3P belirsizligi)
    REPROJ_ESIK   = 8.0     # px; ortalama reproj error bunu asarsa REDDET (ana kalite kapisi)
    RANSAC_REPROJ = 8.0     # solvePnPRansac ic esik (px)
    ORIENT_TAU    = 0.3     # oryantasyon low-pass zaman sabiti (sn)


class TalonPozKestirici:
    """keypoints -> PnP -> {gecerli, tvec, mesafe, phi_T, psi_T, reproj_err, ...}."""

    def __init__(self, cfg=None, sema=VARSAYILAN_SEMA):
        self.cfg = cfg or PnPCfg()
        self.sema = sema if sema in SEMALAR else VARSAYILAN_SEMA
        self.obj = SEMALAR[self.sema]
        self._phi_f = None       # oryantasyon low-pass durumu (wrap-around'a dikkat)
        self._psi_f = None
        self._son_t = None
        try:
            import cv2  # noqa: F401
            self._cv2_var = True
        except Exception:
            self._cv2_var = False

    def sema_ayarla(self, sema):
        if sema in SEMALAR and sema != self.sema:
            self.sema = sema
            self.obj = SEMALAR[sema]
            self._phi_f = self._psi_f = None

    # ------------------------------------------------------------------
    def kestir(self, keypoints, attitude, W, H, t=None):
        """keypoints: [[x,y,conf], ...] (model sirasinda, sema ile eslesir).
        attitude: (roll,pitch,yaw) deg (avci). -> sonuc dict (gecerli alani sart)."""
        origin = "actor" if self.sema == "berat_json" else "AM"   # berat_json: pivot ofsetli
        bos = {"gecerli": False, "sebep": None, "sema": self.sema,
               "origin": origin, "kullanilan_kp": 0}
        if not self._cv2_var:
            bos["sebep"] = "cv2 yok"
            return bos
        if keypoints is None or W is None or H is None:
            bos["sebep"] = "girdi yok"
            return bos
        import cv2
        kp = np.asarray(keypoints, dtype=np.float64)
        if kp.ndim != 2 or kp.shape[0] != 6:
            bos["sebep"] = "kp sayisi != 6 (kpt_shape uyumsuz)"
            return bos
        # conf esigi ustu >=4 nokta
        confs = kp[:, 2] if kp.shape[1] >= 3 else np.ones(6)
        maske = confs >= self.cfg.KP_CONF_ESIK
        n = int(maske.sum())
        if n < self.cfg.MIN_KP:
            bos["sebep"] = "yeterli kp yok (%d<%d)" % (n, self.cfg.MIN_KP)
            bos["kullanilan_kp"] = n
            return bos
        obj = self.obj[maske].astype(np.float64)
        img = kp[maske, :2].astype(np.float64)
        Km = kamera_model.K_matrisi(W, H)
        dist = kamera_model.dist_katsayilari()
        try:
            ok, rvec, tvec, inliers = cv2.solvePnPRansac(
                obj, img, Km, dist, reprojectionError=self.cfg.RANSAC_REPROJ,
                flags=cv2.SOLVEPNP_ITERATIVE)
        except Exception as e:
            bos["sebep"] = "solvePnP hata: %s" % e
            bos["kullanilan_kp"] = n
            return bos
        if not ok or tvec is None:
            bos["sebep"] = "PnP cozum yok"
            bos["kullanilan_kp"] = n
            return bos
        # refine (ITERATIVE) tum inlier'larla
        if inliers is not None and len(inliers) >= self.cfg.MIN_KP:
            idx = inliers.flatten()
            try:
                rvec, tvec = cv2.solvePnPRefineLM(obj[idx], img[idx], Km, dist, rvec, tvec)
            except Exception:
                pass
        # reproj error (ortalama, kullanilan noktalarda)
        proj, _ = cv2.projectPoints(obj, rvec, tvec, Km, dist)
        proj = proj.reshape(-1, 2)
        reproj_err = float(np.mean(np.linalg.norm(proj - img, axis=1)))
        if reproj_err > self.cfg.REPROJ_ESIK:
            bos["sebep"] = "reproj error yuksek (%.1f>%.1f px)" % (reproj_err, self.cfg.REPROJ_ESIK)
            bos["reproj_err"] = reproj_err
            bos["kullanilan_kp"] = n
            return bos

        # tvec: kamera cercevesi konumu (mm -> cm; SDK cm calisir)
        tvec_cm = (tvec.flatten() / 10.0)
        mesafe_cm = float(np.linalg.norm(tvec_cm))
        # oryantasyon: R (govde->kamera) -> dunya cercevesine (montaj + attitude)
        R_obj2kam, _ = cv2.Rodrigues(rvec)
        phi_T, psi_T = self._dunya_yonelim(R_obj2kam, attitude)
        phi_T, psi_T = self._lowpass(phi_T, psi_T, t)
        # dunya-cercevesi relatif konum (kamera->govde->dunya; R_mount 25 tilt burada)
        rel_dunya = kamera_model.kamera_to_dunya_yon(tvec_cm, *attitude)

        return {"gecerli": True, "sebep": "ok", "sema": self.sema, "origin": origin,
                "tvec": tuple(float(x) for x in tvec_cm), "mesafe": mesafe_cm,
                "phi_T": phi_T, "psi_T": psi_T, "reproj_err": reproj_err,
                "kullanilan_kp": n, "rel_konum_dunya": tuple(float(x) for x in rel_dunya)}

    # ------------------------------------------------------------------
    def _dunya_yonelim(self, R_obj2kam, attitude):
        """R (object->kamera) -> hedef roll phi_T, yaw psi_T (dunya, derece).
        Zincir: object -> kamera -> govde (R_mount) -> dunya (avci attitude)."""
        # object ekseni dunyada: R_dunya_obj = R_dunya_kam @ R_kam_obj
        R_govde2dunya = kamera_model.R_govde_to_dunya(*attitude)
        R_kam2govde = kamera_model.R_mount_kam2gov()
        R_dunya_obj = R_govde2dunya @ R_kam2govde @ R_obj2kam.T   # obj eksenleri dunyada
        # hedef govde +X = burun->aft; ileri yon = -X_obj (burun ileri). Dunyada:
        ileri = -R_dunya_obj[:, 0]
        psi_T = math.degrees(math.atan2(ileri[1], ileri[0]))     # yaw (dunya)
        # roll: +Z_obj (sol kanat) dunyada dikey bilesenin isareti/acisi
        sol_kanat = R_dunya_obj[:, 2]
        yatay = math.hypot(sol_kanat[0], sol_kanat[1])
        phi_T = math.degrees(math.atan2(sol_kanat[2], yatay))     # kanat yatikligi
        return phi_T, psi_T

    def _lowpass(self, phi, psi, t):
        """Aci-uzayinda low-pass (wrap-around: fark [-180,180]'e sar)."""
        if t is None:
            return phi, psi
        if self._phi_f is None or self._son_t is None:
            self._phi_f, self._psi_f, self._son_t = phi, psi, t
            return phi, psi
        dt = t - self._son_t
        self._son_t = t
        if dt <= 0:
            return self._phi_f, self._psi_f
        a = dt / (self.cfg.ORIENT_TAU + dt)
        self._phi_f += a * ((phi - self._phi_f + 180) % 360 - 180)
        self._psi_f += a * ((psi - self._psi_f + 180) % 360 - 180)
        return self._phi_f, self._psi_f


# ============================================================
#  k-TARAMASI: f_x = k·f_nominal icin reproj error egrisi -> k* (FAZ 0 borcu)
#  Ayni keypoint setlerini k in [0.75,1.25] izgarasinda cozup medyan reproj
#  error'un minimumunu bulur. k*~1 -> HFOV=125 hassas teyit. Saf fonksiyon.
#
#  >>> DEJENERASYON UYARISI (kritik) <<< PnP fx belirlemesi hedefin ACISAL
#  BOYUTUNA baglidir. FAR-FIELD'de (model boyutu << mesafe; orn. 1.7 m hedef
#  50 m'de acisal ~2 derece) fx degisimi tvec DERINLIK-OLCEGIYLE telafi edilir
#  -> reproj error k'ya DUYARSIZ -> k* guvenilmez (izgara kenarina kayar).
#  k-taramasi ancak hedef YAKINken (perspektif guclu; terminal faz ~5-20 m)
#  anlamlidir. Cikti 'perspektif_gucu' (medyan bbox-genislik/goruntu-genislik)
#  ile gelir; dusukse (<~0.06) k* RAPOR EDILIR ama GUVENILMEZ isaretlenir.
# ============================================================
def k_taramasi(kayitlar, W, H, sema=VARSAYILAN_SEMA,
               k_min=0.75, k_max=1.25, adim=0.01, perspektif_esik=0.03):
    """kayitlar: [(keypoints,)] veya [keypoints] (her biri [[x,y,conf],...]).
    -> {k_izgara, reproj_medyan, k_star, n, perspektif_gucu, guvenilir}."""
    try:
        import cv2
    except Exception:
        return None
    obj_tam = SEMALAR.get(sema, SEMALAR[VARSAYILAN_SEMA])
    cx, cy = W / 2.0, H / 2.0
    fnom = kamera_model.fx_px(W)
    ks = np.arange(k_min, k_max + 1e-9, adim)
    med = []
    setler = []
    genislikler = []
    for kayit in kayitlar:
        kp = np.asarray(kayit[0] if isinstance(kayit, tuple) else kayit, dtype=np.float64)
        if kp.ndim != 2 or kp.shape[0] != 6:
            continue
        confs = kp[:, 2] if kp.shape[1] >= 3 else np.ones(6)
        maske = confs >= 0.5
        if int(maske.sum()) < 4:
            continue
        setler.append((obj_tam[maske], kp[maske, :2]))
        xy = kp[maske, :2]
        genislikler.append(float(xy[:, 0].max() - xy[:, 0].min()))   # kp yayilim genisligi
    persp = (float(np.median(genislikler)) / W) if genislikler else 0.0
    if len(setler) < 5:
        return {"k_izgara": ks.tolist(), "reproj_medyan": [], "k_star": None,
                "n": len(setler), "perspektif_gucu": persp, "guvenilir": False}
    for k in ks:
        fx = k * fnom
        Kk = np.array([[fx, 0, cx], [0, fx, cy], [0, 0, 1]], float)
        errs = []
        for obj, img in setler:
            try:
                ok, rvec, tvec = cv2.solvePnP(obj, img, Kk, None, flags=cv2.SOLVEPNP_ITERATIVE)
            except Exception:
                ok = False
            if not ok:
                continue
            proj, _ = cv2.projectPoints(obj, rvec, tvec, Kk, None)
            errs.append(float(np.mean(np.linalg.norm(proj.reshape(-1, 2) - img, axis=1))))
        med.append(float(np.median(errs)) if errs else float("nan"))
    med = np.array(med)
    if np.all(np.isnan(med)):
        return {"k_izgara": ks.tolist(), "reproj_medyan": med.tolist(), "k_star": None,
                "n": len(setler), "perspektif_gucu": persp, "guvenilir": False}
    k_star = float(ks[int(np.nanargmin(med))])
    # GUVENILIRLIK: (1) egri BELIRGIN min vermeli (far-field'de fx-tvec dejenere
    # -> egri DUZ -> egri_derinlik kucuk; asil ayrimci bu), (2) hedef yeterince
    # yakin (perspektif), (3) k* izgara kenarinda olmamali.
    egri_derinlik = float(np.nanmax(med) - np.nanmin(med)) / max(np.nanmin(med), 1e-6)
    guvenilir = bool(egri_derinlik > 0.25 and persp >= perspektif_esik
                     and k_min + adim < k_star < k_max - adim)
    return {"k_izgara": ks.tolist(), "reproj_medyan": med.tolist(),
            "k_star": k_star, "n": len(setler), "perspektif_gucu": persp,
            "egri_derinlik": egri_derinlik, "guvenilir": guvenilir}

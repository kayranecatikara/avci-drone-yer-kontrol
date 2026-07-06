# -*- coding: utf-8 -*-
"""
================================================================================
 POZ_COZUCU — 6 keypoint'ten PnP ile 6DoF poz (mesafe + yonelim)  [Faz 6]
================================================================================
Girdi : pose modelinin bir karedeki 6 keypoint'i (u,v,conf) + kare boyutu (W,H).
Cikti : hedefin KAMERADAN mesafesi (cm), kamera-frame rotasyonu, dunya yaw/pitch
        (kamera pozu verilirse), aspect acisi, reprojeksiyon RMS'i.

Neden PnP: model yalnizca 2D nokta ogrenir; mesafe/aciyi klasik geometri cozer
(cv2.solvePnP — standart OpenCV, hazir gudum degildir; kural 8'e uygun).

KRITIK UYUM NOKTALARI (degistirme — egitim etiketleriyle birebir ayni olmali):
  * EGITIM_SIRASI: modelin kpt cikti sirasi, talon_keypoints.json sirasindan
    FARKLIDIR. pose/sira_bul.py ile DENEYSEL bulundu (87 karede oy: %76-86
    diagonal, sol/sag kanat ayrimi 70'e 6 -> flip karisikligi YOK):
        pred[k] -> json[EGITIM_SIRASI[k]]
        [burun, sol_kanat, sag_kanat, kuyruk_arka, sol_kuyruk, sag_kuyruk]
  * MESH_PIVOT_OFFSET (+11.76 cm ileri): etiketler actor-origin'e bu ofsetle
    kuruldu (draw_keypoint.py bulgusu) -> PnP obje noktalarina da eklenir.
    Boylece cozulen t = KAMERA -> ACTOR ORIGIN (= get_target_location) vektoru;
    telemetri mesafesiyle dogrudan kiyaslanabilir.
  * HFOV 125 der (yatay, kullanici teyidi) -> fx = (W/2)/tan(62.5 der).

Kullanim:
    from pose.poz_cozucu import PozCozucu
    pc = PozCozucu()
    poz = pc.coz(kp_uv, kp_conf, W, H)        # kp'ler MODEL CIKTI SIRASINDA, px
    # poz None | dict(mesafe_cm, rms_px, R_ue, t_ue, aspect_deg, n_kp, ...)
    yaw, pitch = pc.dunya_yonelim(poz, drone_rot_rpy)   # kamera pozu gerekirse
"""
import os
import sys

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _KOK not in sys.path:
    sys.path.insert(0, _KOK)

import numpy as np
import cv2

from pose import geometri

# Model cikti indeksi -> talon_keypoints.json indeksi (pose/sira_bul.py, 87 kare)
EGITIM_SIRASI = [0, 1, 2, 5, 3, 4]

# Etiket uretimindeki mesh pivot duzeltmesi (draw_keypoint.MESH_PIVOT_OFFSET ile ayni):
# actor origin gorsel mesh'ten 11.76 cm GERIDE -> keypoint'ler +X'e kaydirilarak yazildi.
MESH_PIVOT_OFFSET_CM = np.array([11.76, 0.0, 0.0])

# UE (sol-elli, X ileri, Y saga, Z yukari)  ->  OpenCV kamera (x saga, y asagi, z ileri)
_C = np.array([[0.0, 1.0, 0.0],
               [0.0, 0.0, -1.0],
               [1.0, 0.0, 0.0]])


def _obje_noktalari_model_sirasinda():
    """talon_keypoints.json -> (6,3) cm, MODEL CIKTI SIRASINDA + pivot ofseti."""
    _, kp_cm, _ = geometri.keypointleri_yukle()
    return kp_cm[EGITIM_SIRASI] + MESH_PIVOT_OFFSET_CM


def K_matrisi(W, H, fx=None):
    """Pinhole K. fx verilmezse HFOV=125'ten (fy=fx; UE kare piksel, distorsiyon yok)."""
    if fx is None:
        fx = geometri.fx_from_hfov(W)
    return np.array([[fx, 0.0, W / 2.0],
                     [0.0, fx, H / 2.0],
                     [0.0, 0.0, 1.0]])


class PozCozucu:
    """Kare kare PnP + yumusatma. Thread-safe DEGIL (tek dedektor thread'i kullanir).

    conf_esik : bu guvenin altindaki keypoint PnP'ye girmez (>=4 nokta sart)
    rms_esik_1920 : 1920 px genislikte kabul RMS'i (px); baska cozunurluk W/1920 olcekli
    ema_alpha : mesafe/yon EMA katsayisi (0=kapali)
    """

    def __init__(self, conf_esik=0.5, rms_esik_1920=8.0, ema_alpha=0.4,
                 sifirla_sn=1.0):
        self.obj_ue = _obje_noktalari_model_sirasinda()        # (6,3) cm
        self.obj_cv = (_C @ self.obj_ue.T).T                   # CV konvansiyonu
        self.conf_esik = float(conf_esik)
        self.rms_esik_1920 = float(rms_esik_1920)
        self.ema_alpha = float(ema_alpha)
        self.sifirla_sn = float(sifirla_sn)
        self._onceki = None            # (rvec, tvec) — sonraki kareye tasi (jitter dusurur)
        self._onceki_t = None          # perf_counter: bayatlarsa sifirla
        self.mesafe_ema_cm = None      # EMA durumlari (telemetride gosterilir)
        self._fwd_ema = None           # hedef burun vektoru EMA'si (kamera-UE frame)

    def sifirla(self):
        self._onceki = None
        self._onceki_t = None
        self.mesafe_ema_cm = None
        self._fwd_ema = None

    # ------------------------------------------------------------------
    def coz(self, kp_uv, kp_conf, W, H, t=None):
        """kp_uv (6,2) px MODEL SIRASINDA, kp_conf (6,). None | poz dict doner.
        t: time.perf_counter (bayatlik takibi; None ise dahili saat)."""
        import time as _t
        now = _t.perf_counter() if t is None else float(t)
        if self._onceki_t is not None and (now - self._onceki_t) > self.sifirla_sn:
            self.sifirla()                       # uzun bosluk -> eski cozumle baslama

        kp_uv = np.asarray(kp_uv, float)
        kp_conf = np.asarray(kp_conf, float)
        m = kp_conf >= self.conf_esik
        n = int(m.sum())
        if n < 4:
            return None
        obj = np.ascontiguousarray(self.obj_cv[m])
        img = np.ascontiguousarray(kp_uv[m])
        K = K_matrisi(W, H)

        try:
            if self._onceki is not None:
                rvec, tvec = self._onceki
                ok, rvec, tvec = cv2.solvePnP(
                    obj, img, K, None, rvec.copy(), tvec.copy(),
                    useExtrinsicGuess=True, flags=cv2.SOLVEPNP_ITERATIVE)
            elif n >= 5:
                ok, rvec, tvec, _ = cv2.solvePnPRansac(
                    obj, img, K, None, flags=cv2.SOLVEPNP_SQPNP,
                    reprojectionError=max(4.0, 6.0 * W / 1920.0))
            else:                                 # tam 4 nokta: RANSAC anlamsiz
                ok, rvec, tvec = cv2.solvePnP(obj, img, K, None,
                                              flags=cv2.SOLVEPNP_SQPNP)
        except cv2.error:
            return None
        if not ok or tvec is None:
            return None

        # Reprojeksiyon RMS'i — oturmayan cozumu reddet (cozunurluk-olcekli esik)
        proj, _ = cv2.projectPoints(obj, rvec, tvec, K, None)
        rms = float(np.sqrt(np.mean(np.sum((proj.reshape(-1, 2) - img) ** 2, axis=1))))
        if rms > self.rms_esik_1920 * W / 1920.0:
            self.sifirla()                        # bozuk cozumu sonraki kareye TASIMA
            return None
        # Hedef kamera ONUNDE olmali (CV: z ileri) — arkada cozum = sacma/ayna
        if float(np.ravel(tvec)[2]) <= 0.0:
            self.sifirla()
            return None

        R_cv, _ = cv2.Rodrigues(rvec)
        R_ue = _C.T @ R_cv @ _C                   # hedef-lokal -> kamera-lokal (UE eksen)
        t_ue = (_C.T @ tvec).ravel()              # cm, kamera-UE frame (x ileri)
        mesafe = float(np.linalg.norm(t_ue))

        # asiri yakin/uzak cozumler fiziksel degil (sim zarfi ~1..120 m)
        if not (100.0 < mesafe < 12000.0):
            self.sifirla()
            return None

        self._onceki = (rvec, tvec)
        self._onceki_t = now

        # --- turetilmis buyuklukler (tilt/kamera pozu GEREKMEZ) ---
        fwd = R_ue @ np.array([1.0, 0.0, 0.0])    # hedef burnu, kamera-UE frame
        los = t_ue / mesafe                       # kamera -> hedef birim vektor
        # aspect: hedef burnu ile hedef->kamera yonu arasi aci.
        # 0 der = burun bize donuk (kafa kafaya), 180 der = kuyruk bize donuk (arkadan takip).
        aspect = float(np.degrees(np.arccos(np.clip(np.dot(fwd, -los), -1.0, 1.0))))

        # --- EMA yumusatma ---
        a = self.ema_alpha
        if a > 0.0:
            self.mesafe_ema_cm = (mesafe if self.mesafe_ema_cm is None
                                  else a * mesafe + (1 - a) * self.mesafe_ema_cm)
            self._fwd_ema = (fwd if self._fwd_ema is None
                             else a * fwd + (1 - a) * self._fwd_ema)
            nrm = np.linalg.norm(self._fwd_ema)
            if nrm > 1e-9:
                self._fwd_ema = self._fwd_ema / nrm
        else:
            self.mesafe_ema_cm = mesafe
            self._fwd_ema = fwd

        return {
            "mesafe_cm": mesafe,
            "mesafe_ema_cm": float(self.mesafe_ema_cm),
            "R_ue": R_ue,                 # hedef-lokal -> kamera-UE
            "t_ue": t_ue,                 # cm, kamera-UE
            "fwd_cam": fwd,               # hedef burnu (kamera-UE, anlik)
            "fwd_cam_ema": None if self._fwd_ema is None else self._fwd_ema.copy(),
            "aspect_deg": aspect,
            "rms_px": rms,
            "n_kp": n,
        }

    # ------------------------------------------------------------------
    def dunya_yonelim(self, poz, drone_rot_rpy, ema=True):
        """Hedefin DUNYA yaw/pitch'i (derece). Kamera pozu gerekir -> tilt'e bagli
        (geometri.KAMERA_TILT_DEG su an 25 der placeholder; kalibre.py netlestirir).
        drone_rot_rpy: SDK (roll, pitch, yaw). (yaw, pitch) doner; poz None ise None."""
        if poz is None:
            return None
        _, R_cam = geometri.kamera_pozu((0.0, 0.0, 0.0), drone_rot_rpy)
        f_cam = poz["fwd_cam_ema"] if (ema and poz.get("fwd_cam_ema") is not None) \
            else poz["fwd_cam"]
        f_w = R_cam @ f_cam                       # hedef burnu dunyada
        yaw = float(np.degrees(np.arctan2(f_w[1], f_w[0])))
        pitch = float(np.degrees(np.arctan2(f_w[2], np.hypot(f_w[0], f_w[1]))))
        return yaw, pitch

    @staticmethod
    def dunya_yonelim_kamera_pozuyla(poz, R_cam, ema=True):
        """dunya_yonelim'in R_cam'i HAZIR olan hali (offline degerlendirme:
        kamera rotasyonu JSON'dan kesin bilinir, tilt belirsizligi YOK)."""
        if poz is None:
            return None
        f_cam = poz["fwd_cam_ema"] if (ema and poz.get("fwd_cam_ema") is not None) \
            else poz["fwd_cam"]
        f_w = np.asarray(R_cam, float) @ f_cam
        yaw = float(np.degrees(np.arctan2(f_w[1], f_w[0])))
        pitch = float(np.degrees(np.arctan2(f_w[2], np.hypot(f_w[0], f_w[1]))))
        return yaw, pitch


# --- hizli kendi-kendine test: sentetik pozdan uretilen 2D -> PnP geri cozumu ---
def _selftest():
    rng = np.random.default_rng(7)
    obj_ue = _obje_noktalari_model_sirasinda()
    W, H = 1920, 1080
    fx = geometri.fx_from_hfov(W)
    hata_m, hata_yaw = [], []
    for _ in range(60):
        # rastgele hedef pozu: 6-30 m onde, +-8 m yanal/dikey, rastgele yonelim
        t_true = np.array([rng.uniform(600, 3000),
                           rng.uniform(-800, 800), rng.uniform(-500, 500)])
        rpy = (rng.uniform(-30, 30), rng.uniform(-20, 20), rng.uniform(0, 360))
        R_true = geometri.ue_rot_matrix(rpy[1], rpy[2], rpy[0])
        uv = []
        for p in obj_ue:
            w = t_true + R_true @ p               # kamera-UE framede nokta
            uv.append((W / 2 + fx * w[1] / w[0], H / 2 - fx * w[2] / w[0]))
        uv = np.array(uv) + rng.normal(0, 1.0, (6, 2))     # 1 px gurultu
        pc = PozCozucu(ema_alpha=0.0)
        poz = pc.coz(uv, np.ones(6), W, H)
        assert poz is not None, "PnP cozemedi"
        hata_m.append(abs(poz["mesafe_cm"] - np.linalg.norm(t_true)) / 100.0)
        # dunya = kamera (R_cam=I) kabul edip yaw kiyasla
        yw, _ = PozCozucu.dunya_yonelim_kamera_pozuyla(poz, np.eye(3), ema=False)
        d = (yw - rpy[2] + 180.0) % 360.0 - 180.0
        hata_yaw.append(abs(d))
    print("SELFTEST (1 px gurultu, 60 rastgele poz):")
    print("  mesafe hatasi  ort=%.2f m  max=%.2f m" % (np.mean(hata_m), np.max(hata_m)))
    print("  yaw hatasi     ort=%.2f der max=%.2f der" % (np.mean(hata_yaw), np.max(hata_yaw)))
    # 1 px gurultu @30 m ~ %3-4 derinlik belirsizligi (kanat 28 px) -> ort ~0.5 m NORMAL
    ok = np.mean(hata_m) < 1.0 and np.mean(hata_yaw) < 3.0
    print("  [%s]" % ("OK" if ok else "HATA — eksen koprusu/sira supheli"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(_selftest())

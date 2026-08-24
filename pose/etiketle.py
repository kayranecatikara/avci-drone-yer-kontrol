# -*- coding: utf-8 -*-
"""
================================================================================
 ETIKETLE (Faz 4) — kayit ucusu oturumundan OTOMATIK YOLO detect etiketi
================================================================================
GELISTIRME ARACI — teslim paketine girmez. Yol haritasi: docs/DATASET_YOL_HARITASI.md

Girdi : pose/kayit_ucusu.py oturum klasoru
        (kare_*.png + telemetri.jsonl + telemetri_akis.jsonl + meta.json)
Cikti : <oturum>/labels/kare_XXXXXX.txt   YOLO detect satiri "0 cx cy w h" (normalize)
        <oturum>/etiket_rapor.json        sayilar + eleme kirilimi + mesafe binleri
        [--kp]        <oturum>/labels_pose/   YOLO pose satiri (bbox + 6*(x y v));
                      kp sirasi = talon_keypoints.json sirasi (flip_idx de oradan)
        [--onizle N]  <oturum>/onizleme_etiket/  kutu+kp cizimli QA kareleri

YONTEM: truth hedef konumu + hedef rotasyonu + kendi konum/rotasyonumuz ->
6 keypoint (talon_keypoints.json) dunyaya tasinir (geometri.keypoints_dunyada),
kameraya projekte edilir (geometri.projekte). Tilt/HFOV geometri modul
globallerinden CAGRI ANINDA okunur -> pose/kalibre.py guncellerse otomatik
gecerli. bbox = kp zarfi + MARJ (kp'ler iskelet uclari; govde silueti disari
tasar -> x/y ayri marj; --onizle cikti gozle rafine edilir).

GECIKME: kare ile telemetri arasindaki dt'yi pose/kalibre.py olcer; --dt ile
verilir (dt>0 = kare, telemetriden dt saniye ESKI durumu gosterir). Durum,
telemetri_akis.jsonl (~50 Hz) uzerinden (t_kare - dt) anina interpolasyonla
bulunur (pozisyon lineer, acilar kisa-yol). Akis yoksa kare satiri aynen
kullanilir ve dt yok sayilir (uyari).

HEDEF ROTASYON GUVENI: target_rot_rpy truth DEGIL (kayit meta notu). Yaw,
truth konum hareket yonuyle capraz kontrol edilir: sapma > --rot-esik ve hedef
yeterince hizliysa rotasyon HEADING-SENTETIK ile degistirilir (yaw=heading,
pitch=tirmanma acisi, roll=0) — bbox zarfi icin yeterli; rapora sayilir.

ELEME (supheli kare etiketlenmez; rapora sebep kirilimiyla yazilir):
  arkada       herhangi bir kp kamera arkasinda
  kadraj_disi  kirpilmis kutu alani / tam kutu alani < --min-gorunur
  cok_kucuk    kirpilmis kutu kisa kenari < --min-px
  bozulma      corruption_mask != 0 (kayit ucusu BOZULMASIZ yapilmali)
  kare_yok     telemetri satiri var, PNG dosyasi yok

KULLANIM:
    python pose/etiketle.py --oturum <dir> [<dir2> ...] [--dt 0.0] [--kp]
        [--marj-x 0.06] [--marj-y 0.20] [--onizle 30]
    python pose/etiketle.py --dogrula-gt C:\\talon_pose_data\\dataset [--sayi 40]
        Lua GT karelerine projeksiyon overlay cizer: goruntudeki GERCEK Talon
        pikselleri BAGIMSIZ referanstir; zincir dogruysa cizim ucagin ustune
        oturur (metrik degil GOZ kapisi — ayni matematikle uretilen sayilarla
        kendi kendini dogrulamak totolojidir, o yuzden sayi iddia edilmez).
================================================================================
"""
import os
import sys
import json
import glob
import random
import argparse

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _KOK not in sys.path:
    sys.path.insert(0, _KOK)

import numpy as np

from pose import geometri

KP_ISIMLER, KP_CM, FLIP_IDX = geometri.keypointleri_yukle()
BIN_SINIR_M = [0, 15, 30, 50, 80, 120, 1e9]
BIN_AD = ["0-15", "15-30", "30-50", "50-80", "80-120", "120+"]


# =============================================================================
#  Saf yardimcilar (birim testli: tests/test_etiketle.py)
# =============================================================================
def wrap180(a):
    """Aciyi (-180, 180] bandina sarar (derece)."""
    return (a + 180.0) % 360.0 - 180.0


def aci_interp(a, b, f):
    """Iki aci arasinda kisa-yol lineer interpolasyon; (-180,180] doner (derece)."""
    return wrap180(a + wrap180(b - a) * f)


class Akis:
    """telemetri_akis.jsonl -> zaman indeksli durum. durum(t): interpolasyonlu
    (dp drone_pos, dr drone_rot_rpy, tp truth_target_pos, tr target_rot_rpy)."""

    def __init__(self, yol):
        t, dp, dr, tp, tr = [], [], [], [], []
        with open(yol, encoding="utf-8") as f:
            for satir in f:
                try:
                    d = json.loads(satir)
                except ValueError:
                    continue                      # yarim satir (CTRL-C aninda)
                t.append(d["t"]); dp.append(d["dp"]); dr.append(d["dr"])
                tp.append(d["tp"]); tr.append(d["tr"])
        self.t = np.asarray(t, float)
        self.dp = np.asarray(dp, float); self.dr = np.asarray(dr, float)
        self.tp = np.asarray(tp, float); self.tr = np.asarray(tr, float)

    def __len__(self):
        return len(self.t)

    def durum(self, t_sorgu):
        """(dp, dr, tp, tr) @ t_sorgu; pozisyon lineer, acilar kisa-yol."""
        i = int(np.searchsorted(self.t, t_sorgu))
        if i <= 0:
            return self.dp[0], self.dr[0], self.tp[0], self.tr[0]
        if i >= len(self.t):
            return self.dp[-1], self.dr[-1], self.tp[-1], self.tr[-1]
        t0, t1 = self.t[i - 1], self.t[i]
        f = 0.0 if t1 <= t0 else (t_sorgu - t0) / (t1 - t0)
        poz = lambda a: a[i - 1] + (a[i] - a[i - 1]) * f
        aci = lambda a: np.array([aci_interp(a[i - 1][k], a[i][k], f) for k in range(3)])
        return poz(self.dp), aci(self.dr), poz(self.tp), aci(self.tr)

    def hedef_dikey_hiz(self, t_sorgu, pencere_s=0.3):
        """truth hedef dusey hiz (cm/s) — sentetik rotasyon pitch'i icin."""
        m = (self.t >= t_sorgu - pencere_s) & (self.t <= t_sorgu + pencere_s)
        if m.sum() < 2:
            return 0.0
        ts, zs = self.t[m], self.tp[m][:, 2]
        dt = ts[-1] - ts[0]
        return float((zs[-1] - zs[0]) / dt) if dt > 1e-6 else 0.0


def rot_sec(trot, heading_deg, hiz_cms, vz_cms=0.0,
            esik_deg=25.0, min_hiz_cms=300.0):
    """Hedef rotasyonu sec: telemetri mi, heading-sentetik mi.
    -> (rot_rpy, kaynak)  kaynak: 'tel' | 'heading' | 'dogrulanamadi'"""
    if heading_deg is None or hiz_cms is None or hiz_cms < min_hiz_cms:
        return tuple(trot), "dogrulanamadi"       # yavas hedef: heading anlamsiz
    if abs(wrap180(float(trot[2]) - heading_deg)) <= esik_deg:
        return tuple(trot), "tel"
    vxy = max(float(hiz_cms), 1e-6)
    pitch = float(np.degrees(np.arctan2(vz_cms, vxy)))
    return (0.0, pitch, float(heading_deg)), "heading"


def kare_etiketi(dpos, drot, tpos, trot, W, H,
                 marj_x=0.06, marj_y=0.20, min_gorunur=0.35, min_px=3.0):
    """TEK karenin etiket cekirdegi. -> (durum, kutu, uvs)
    durum: 'ok' | 'arkada' | 'kadraj_disi' | 'cok_kucuk'
    kutu : (x0, y0, x1, y1) piksel, kadraja KIRPILMIS (durum 'ok' ise)
    uvs  : 6 kp piksel listesi (arkadaki None)"""
    cam_pos, R_cam = geometri.kamera_pozu(dpos, drot)
    fx = geometri.fx_from_hfov(W)
    kp_w = geometri.keypoints_dunyada(tpos, trot, KP_CM)
    uvs = [geometri.projekte(p, cam_pos, R_cam, fx, W, H) for p in kp_w]
    if any(uv is None for uv in uvs):
        return "arkada", None, uvs

    us = [uv[0] for uv in uvs]; vs = [uv[1] for uv in uvs]
    x0, x1 = min(us), max(us)
    y0, y1 = min(vs), max(vs)
    w, h = x1 - x0, y1 - y0
    x0 -= w * marj_x; x1 += w * marj_x
    y0 -= h * marj_y; y1 += h * marj_y
    tam_alan = max((x1 - x0) * (y1 - y0), 1e-9)

    kx0, ky0 = max(x0, 0.0), max(y0, 0.0)
    kx1, ky1 = min(x1, float(W)), min(y1, float(H))
    if kx1 <= kx0 or ky1 <= ky0:
        return "kadraj_disi", None, uvs
    if (kx1 - kx0) * (ky1 - ky0) / tam_alan < min_gorunur:
        return "kadraj_disi", None, uvs
    if min(kx1 - kx0, ky1 - ky0) < min_px:
        return "cok_kucuk", None, uvs
    return "ok", (kx0, ky0, kx1, ky1), uvs


def yolo_satiri(kutu, W, H):
    """Kirpilmis piksel kutusu -> 'cls cx cy w h' YOLO satiri (normalize)."""
    x0, y0, x1, y1 = kutu
    cx, cy = (x0 + x1) / 2.0 / W, (y0 + y1) / 2.0 / H
    w, h = (x1 - x0) / W, (y1 - y0) / H
    return "0 %.6f %.6f %.6f %.6f" % (cx, cy, w, h)


def yolo_pose_satiri(kutu, uvs, W, H):
    """YOLO pose satiri: bbox + 6*(x y v). Kadraj disi kp -> v=0, x=y=0."""
    parca = [yolo_satiri(kutu, W, H)]
    for uv in uvs:
        if uv is not None and 0 <= uv[0] < W and 0 <= uv[1] < H:
            parca.append("%.6f %.6f 2" % (uv[0] / W, uv[1] / H))
        else:
            parca.append("0 0 0")
    return " ".join(parca)


# =============================================================================
#  Oturum etiketleme
# =============================================================================
def etiketle_oturum(oturum, args):
    j_yol = os.path.join(oturum, "telemetri.jsonl")
    if not os.path.exists(j_yol):
        print("[HATA] telemetri.jsonl yok: %s" % oturum)
        return None

    akis = None
    a_yol = os.path.join(oturum, "telemetri_akis.jsonl")
    uyarilar = []
    if os.path.exists(a_yol):
        akis = Akis(a_yol)
        if len(akis) < 2:
            akis = None
    if akis is None and args.dt != 0.0:
        uyarilar.append("telemetri_akis.jsonl yok/kisa -> dt yok sayildi")

    meta_yol = os.path.join(oturum, "meta.json")
    if os.path.exists(meta_yol):
        with open(meta_yol, encoding="utf-8") as f:
            meta = json.load(f)
        for ad, simdiki in (("hfov_deg", geometri.KAMERA_HFOV_DEG),
                            ("kamera_tilt_deg", geometri.KAMERA_TILT_DEG)):
            if ad in meta and abs(float(meta[ad]) - simdiki) > 0.01:
                uyarilar.append("meta.%s=%.2f, geometri=%.2f (guncel kalibre kullanildi)"
                                % (ad, float(meta[ad]), simdiki))

    lbl_dir = os.path.join(oturum, "labels")
    os.makedirs(lbl_dir, exist_ok=True)
    if args.kp:
        lblp_dir = os.path.join(oturum, "labels_pose")
        os.makedirs(lblp_dir, exist_ok=True)

    sayac = {"arkada": 0, "kadraj_disi": 0, "cok_kucuk": 0, "bozulma": 0, "kare_yok": 0}
    rot_sayac = {"tel": 0, "heading": 0, "dogrulanamadi": 0}
    bin_say = [0] * len(BIN_AD)
    kisa_kenarlar = []
    etiketli = []                                  # (png_yol, kutu, uvs, mesafe_m, rot_k)

    with open(j_yol, encoding="utf-8") as f:
        satirlar = [json.loads(s) for s in f if s.strip()]

    for sat in satirlar:
        png = os.path.join(oturum, sat["kare"])
        if not os.path.exists(png):
            sayac["kare_yok"] += 1
            continue
        if int(sat.get("corruption_mask", 0)) != 0:
            sayac["bozulma"] += 1
            continue
        W, H = int(sat["W"]), int(sat["H"])

        if akis is not None:
            dpos, drot, tpos, trot0 = akis.durum(float(sat["t"]) - args.dt)
            vz = akis.hedef_dikey_hiz(float(sat["t"]) - args.dt)
        else:
            dpos = np.asarray(sat.get("truth_drone_pos", sat["drone_pos"]), float)
            drot = np.asarray(sat["drone_rot_rpy"], float)
            tpos = np.asarray(sat["truth_target_pos"], float)
            trot0 = np.asarray(sat["target_rot_rpy"], float)
            vz = 0.0

        trot, rot_k = rot_sec(trot0, sat.get("hedef_heading_deg"),
                              sat.get("truth_target_speed"), vz,
                              esik_deg=args.rot_esik)
        durum, kutu, uvs = kare_etiketi(dpos, drot, tpos, trot, W, H,
                                        marj_x=args.marj_x, marj_y=args.marj_y,
                                        min_gorunur=args.min_gorunur,
                                        min_px=args.min_px)
        if durum != "ok":
            sayac[durum] += 1
            continue

        rot_sayac[rot_k] += 1
        ad = os.path.splitext(sat["kare"])[0]
        with open(os.path.join(lbl_dir, ad + ".txt"), "w", encoding="utf-8") as g:
            g.write(yolo_satiri(kutu, W, H) + "\n")
        if args.kp:
            with open(os.path.join(lblp_dir, ad + ".txt"), "w", encoding="utf-8") as g:
                g.write(yolo_pose_satiri(kutu, uvs, W, H) + "\n")

        mesafe_m = float(sat.get("mesafe_cm", 0.0)) / 100.0
        for b in range(len(BIN_AD)):
            if BIN_SINIR_M[b] <= mesafe_m < BIN_SINIR_M[b + 1]:
                bin_say[b] += 1
                break
        kisa_kenarlar.append(min(kutu[2] - kutu[0], kutu[3] - kutu[1]))
        etiketli.append((png, kutu, uvs, mesafe_m, rot_k))

    n_etiket = len(etiketli)
    rapor = {
        "oturum": os.path.abspath(oturum),
        "n_telemetri": len(satirlar), "n_etiket": n_etiket,
        "elemeler": sayac, "rot_kaynak": rot_sayac,
        "bin_m": dict(zip(BIN_AD, bin_say)),
        "bbox_kisa_kenar_px": ({"min": round(float(np.min(kisa_kenarlar)), 1),
                                "medyan": round(float(np.median(kisa_kenarlar)), 1),
                                "max": round(float(np.max(kisa_kenarlar)), 1)}
                               if kisa_kenarlar else None),
        "ayar": {"dt": args.dt, "marj_x": args.marj_x, "marj_y": args.marj_y,
                 "min_gorunur": args.min_gorunur, "min_px": args.min_px,
                 "rot_esik": args.rot_esik,
                 "tilt_deg": geometri.KAMERA_TILT_DEG,
                 "hfov_deg": geometri.KAMERA_HFOV_DEG},
        "uyarilar": uyarilar,
    }
    with open(os.path.join(oturum, "etiket_rapor.json"), "w", encoding="utf-8") as f:
        json.dump(rapor, f, ensure_ascii=False, indent=2)

    print("[ETIKET] %s" % oturum)
    print("  telemetri satiri: %d | etiketlenen: %d | eleme: %s"
          % (len(satirlar), n_etiket,
             ", ".join("%s=%d" % kv for kv in sayac.items() if kv[1])))
    print("  rot kaynak: tel=%d heading=%d dogrulanamadi=%d"
          % (rot_sayac["tel"], rot_sayac["heading"], rot_sayac["dogrulanamadi"]))
    print("  mesafe binleri (m): %s"
          % "  ".join("%s:%d" % (a, s) for a, s in zip(BIN_AD, bin_say)))
    for u in uyarilar:
        print("  UYARI: %s" % u)

    if args.onizle > 0 and etiketli:
        _onizle_ciz(oturum, etiketli, args.onizle)
    return rapor


def _onizle_ciz(oturum, etiketli, n):
    """Rastgele n etiketli kareye kutu+kp cizip onizleme_etiket/ altina yazar."""
    import cv2
    cikti = os.path.join(oturum, "onizleme_etiket")
    os.makedirs(cikti, exist_ok=True)
    renk = [(0, 0, 255), (0, 255, 0), (0, 200, 255),
            (255, 128, 0), (255, 0, 255), (255, 255, 0)]   # sira_bul/onizle paleti
    ornekler = random.sample(etiketli, min(n, len(etiketli)))
    for png, kutu, uvs, mesafe_m, rot_k in ornekler:
        img = cv2.imread(png)
        if img is None:
            continue
        x0, y0, x1, y1 = [int(round(v)) for v in kutu]
        cv2.rectangle(img, (x0, y0), (x1, y1), (0, 255, 0), 2)
        for k, uv in enumerate(uvs):
            if uv is not None:
                cv2.circle(img, (int(uv[0]), int(uv[1])), 3, renk[k], -1)
        cv2.putText(img, "d=%.1fm rot=%s" % (mesafe_m, rot_k), (x0, max(y0 - 6, 12)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1, cv2.LINE_AA)
        cv2.imwrite(os.path.join(cikti, os.path.basename(png)), img)
    print("  onizleme: %d kare -> %s" % (len(ornekler), cikti))


# =============================================================================
#  Lua GT seti overlay dogrulamasi (goz kapisi)
# =============================================================================
def dogrula_gt(dataset_dir, sayi, marj_x, marj_y):
    """Lua GT karelerinde kp+kutu overlay uretir. Goruntudeki GERCEK Talon
    pikselleri bagimsiz referans: cizim ucagin ustune oturuyorsa keypoint
    modeli + eksen konvansiyonu + projeksiyon zinciri dogrudur."""
    import cv2
    from pose.sira_bul import gt_noktalar
    jler = sorted(glob.glob(os.path.join(dataset_dir, "*.json")))
    if not jler:
        print("[HATA] JSON bulunamadi: %s" % dataset_dir)
        return 1
    if sayi and len(jler) > sayi:
        idx = np.linspace(0, len(jler) - 1, sayi).round().astype(int)
        jler = [jler[i] for i in sorted(set(idx.tolist()))]
    cikti = os.path.join(os.path.dirname(os.path.abspath(dataset_dir)),
                         "etiket_dogrulama")
    os.makedirs(cikti, exist_ok=True)
    renk = [(0, 0, 255), (0, 255, 0), (0, 200, 255),
            (255, 128, 0), (255, 0, 255), (255, 255, 0)]
    n_ok = 0
    for jf in jler:
        png = jf[:-5] + ".png"
        if not os.path.exists(png):
            continue
        img = cv2.imread(png)
        if img is None:
            continue
        H, W = img.shape[:2]
        with open(jf, encoding="utf-8") as f:
            data = json.load(f)
        uvs = gt_noktalar(data, W, H)
        gecerli = [uv for uv in uvs if uv is not None]
        if len(gecerli) >= 2:
            us = [uv[0] for uv in gecerli]; vs = [uv[1] for uv in gecerli]
            w, h = max(us) - min(us), max(vs) - min(vs)
            cv2.rectangle(img,
                          (int(min(us) - w * marj_x), int(min(vs) - h * marj_y)),
                          (int(max(us) + w * marj_x), int(max(vs) + h * marj_y)),
                          (0, 255, 0), 2)
        for k, uv in enumerate(uvs):
            if uv is not None:
                cv2.circle(img, (int(uv[0]), int(uv[1])), 3, renk[k], -1)
        cv2.imwrite(os.path.join(cikti, os.path.basename(png)), img)
        n_ok += 1
    print("[DOGRULA-GT] %d kare cizildi -> %s" % (n_ok, cikti))
    print("  GOZ KONTROLU: cizim ucagin ustune oturuyor mu? Oturmuyorsa once")
    print("  eksen/isaret (arac/attitude_dogrula.py) ve kalibre (pose/kalibre.py).")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Kayit oturumundan otomatik YOLO etiketi")
    ap.add_argument("--oturum", nargs="+", help="kayit_ucusu oturum klasoru(leri)")
    ap.add_argument("--dt", type=float, default=0.0,
                    help="kare-telemetri gecikmesi sn (pose/kalibre.py olcer; >0 = kare eski)")
    ap.add_argument("--marj-x", type=float, default=0.06, help="bbox yatay marj orani")
    ap.add_argument("--marj-y", type=float, default=0.20, help="bbox dusey marj orani")
    ap.add_argument("--min-gorunur", type=float, default=0.35,
                    help="kirpilmis/tam kutu alan orani alt siniri")
    ap.add_argument("--min-px", type=float, default=3.0, help="kutu kisa kenar alt siniri (px)")
    ap.add_argument("--rot-esik", type=float, default=25.0,
                    help="yaw-heading sapma esigi (deg); ustunde heading-sentetik")
    ap.add_argument("--kp", action="store_true", help="YOLO pose etiketi de yaz")
    ap.add_argument("--onizle", type=int, default=0, help="rastgele N QA onizlemesi ciz")
    ap.add_argument("--dogrula-gt", default=None,
                    help="Lua GT dataset klasorunde overlay dogrulamasi uret")
    ap.add_argument("--sayi", type=int, default=40, help="--dogrula-gt kare sayisi")
    args = ap.parse_args(argv)

    if args.dogrula_gt:
        return dogrula_gt(args.dogrula_gt, args.sayi, args.marj_x, args.marj_y)
    if not args.oturum:
        ap.error("--oturum veya --dogrula-gt verilmeli")
    for o in args.oturum:
        etiketle_oturum(o, args)
    return 0


if __name__ == "__main__":
    sys.exit(main())

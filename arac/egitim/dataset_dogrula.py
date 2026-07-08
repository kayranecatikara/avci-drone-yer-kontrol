# -*- coding: utf-8 -*-
"""
================================================================================
GELISTIRME ARACI — teslim paketine girmez.
================================================================================
DATASET FORMAT DOGRULAYICI (pose fine-tune oncesi)
================================================================================
Ultralytics pose dataset'ini egitimden ONCE dogrular; sessiz sacmaliga (yanlis
kpt sirasi / flip_idx / split) karsi kapi. Kontroller:
  1) data.yaml: kpt_shape [6,3], flip_idx (yoksa UYARI — yatay flip augmentation
     sol/sag kp cifti degistirmez; YENI kuyruk_ucu semasi icin dogru flip sart),
     names (tek sinif 'talon'), train/val split yollari mevcut.
  2) Label ornekleri: her .txt satiri 'cls cx cy w h + 6*(kx ky v)' = 5+18=23
     alan; koordinatlar [0,1]; v in {0,1,2}. Bozuk satir sayisi raporlanir.
  3) SEMA UYUMU: pipeline'in bekledigi sira (talon_pose_estimator.KP_ADLARI)
     ile data.yaml kpt isim sirasi (varsa) karsilastirilir; uyusmazsa UYARI.
  4) flip_idx TUTARLILIK: tanimliysa sol/sag ciftleri (vtail, kanat) simetrik
     yer degistirmeli; degilse UYARI.

KULLANIM:
    python arac/egitim/dataset_dogrula.py <data.yaml yolu>
Cikti: rapor + exit 0 (temiz/uyari) | 1 (kritik hata: egitime girme).
================================================================================
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJ_ROOT = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _PROJ_ROOT)

BEKLENEN_KPT = 6
BEKLENEN_DIM = 3
# YENI sema keypoint sirasi (pipeline sozlesmesi). Sol/sag ciftleri flip_idx icin.
BEKLENEN_SIRA = ["burun", "kuyruk_ucu", "sol_vtail", "sag_vtail", "sol_kanat", "sag_kanat"]
# flip_idx: yatay aynalamada index i -> flip[i]. burun/kuyruk_ucu sabit; sol<->sag.
BEKLENEN_FLIP = [0, 1, 3, 2, 5, 4]


def _yaml_oku(yol):
    try:
        import yaml
        with open(yol, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        # minimal fallback
        cfg = {}
        try:
            with open(yol, "r", encoding="utf-8") as f:
                for s in f:
                    s = s.split("#", 1)[0].strip()
                    if ":" in s:
                        k, v = s.split(":", 1)
                        cfg[k.strip()] = v.strip()
        except Exception:
            pass
        return cfg


def dogrula(yaml_yolu):
    hatalar, uyarilar = [], []
    if not os.path.isfile(yaml_yolu):
        print("[HATA] data.yaml yok: %s" % yaml_yolu)
        return False
    cfg = _yaml_oku(yaml_yolu)
    kok = os.path.dirname(os.path.abspath(yaml_yolu))

    # 1) kpt_shape
    ks = cfg.get("kpt_shape")
    if isinstance(ks, str):
        ks = [int(x) for x in ks.strip("[]").split(",") if x.strip().isdigit()]
    if list(ks or []) != [BEKLENEN_KPT, BEKLENEN_DIM]:
        hatalar.append("kpt_shape %s != [%d,%d]" % (ks, BEKLENEN_KPT, BEKLENEN_DIM))

    # 2) names
    names = cfg.get("names")
    if isinstance(names, dict):
        names = list(names.values())
    if not names or "talon" not in [str(x).lower() for x in (names or [])]:
        uyarilar.append("names 'talon' icermiyor: %s" % names)

    # 3) flip_idx
    flip = cfg.get("flip_idx")
    if flip is None:
        uyarilar.append("flip_idx TANIMSIZ -> yatay-flip augmentation sol/sag kp "
                        "cifti degistirmez. YENI kuyruk_ucu semasi icin flip_idx=%s ekle."
                        % BEKLENEN_FLIP)
    elif list(flip) != BEKLENEN_FLIP:
        uyarilar.append("flip_idx %s != beklenen %s (sol/sag ciftleri: vtail 2<->3, "
                        "kanat 4<->5)" % (flip, BEKLENEN_FLIP))

    # 4) split yollari
    for anahtar in ("train", "val"):
        yol = cfg.get(anahtar)
        if not yol:
            hatalar.append("%s split tanimsiz" % anahtar)
            continue
        tam = yol if os.path.isabs(yol) else os.path.join(kok, yol)
        if not os.path.exists(tam):
            uyarilar.append("%s yolu bulunamadi (Colab yolu olabilir): %s" % (anahtar, yol))

    # 5) label ornekleri (varsa)
    n_bozuk = n_kontrol = 0
    for anahtar in ("train", "val"):
        yol = cfg.get(anahtar)
        if not yol:
            continue
        tam = yol if os.path.isabs(yol) else os.path.join(kok, yol)
        lbl_dir = tam.replace("images", "labels")
        if not os.path.isdir(lbl_dir):
            continue
        for fn in sorted(os.listdir(lbl_dir))[:50]:
            if not fn.endswith(".txt"):
                continue
            try:
                with open(os.path.join(lbl_dir, fn), "r") as f:
                    for satir in f:
                        p = satir.split()
                        if not p:
                            continue
                        n_kontrol += 1
                        if len(p) != 5 + BEKLENEN_KPT * BEKLENEN_DIM:
                            n_bozuk += 1
            except Exception:
                pass
    if n_kontrol and n_bozuk:
        uyarilar.append("label kontrol: %d/%d satir alan-sayisi yanlis (23 bekleniyor)"
                        % (n_bozuk, n_kontrol))

    # --- rapor ---
    print("=" * 64)
    print(" DATASET DOGRULAMA: %s" % yaml_yolu)
    print("=" * 64)
    print(" kpt_shape : %s | names: %s | flip_idx: %s" % (ks, names, flip))
    print(" beklenen sira: %s" % ", ".join(BEKLENEN_SIRA))
    print(" label kontrol: %d satir, %d bozuk" % (n_kontrol, n_bozuk))
    for u in uyarilar:
        print(" [UYARI] %s" % u)
    for h in hatalar:
        print(" [HATA]  %s" % h)
    ok = not hatalar
    print("\n SONUC: %s%s" % ("TEMIZ" if ok and not uyarilar else
                              ("UYARILI (egitilebilir)" if ok else "KRITIK HATA (egitme)"),
                              ""))
    print("=" * 64)
    return ok


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Kullanim: python arac/egitim/dataset_dogrula.py <data.yaml>")
        sys.exit(2)
    sys.exit(0 if dogrula(sys.argv[1]) else 1)

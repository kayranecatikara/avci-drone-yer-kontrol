# -*- coding: utf-8 -*-
"""
================================================================================
 NEGATIF TOPLA — HARD NEGATIVE madenciligi (Hat C, yol haritasi FAZ 1)
================================================================================
GELISTIRME ARACI — teslim paketine girmez. Yol haritasi: docs/DATASET_YOL_HARITASI.md

DERT: model HUD metinlerini ("ARMED", "TRIGGER:NOT READY", "ALT 31m", "SPD",
sinyal/batarya okumalari) ucak saniyor. Bunlar kadrajda SABIT yerlerde ve HER
karede varlar -> egitim setinde "bunlar arka plan" ornegi yoksa model uyduruyor.
ILAC: etiketsiz (BOS .txt) kareler. Ultralytics bos etiket dosyasini background
ornegi olarak egitime alir.

ZOR (hard) negatif = modelin SU AN yanlis-pozitif urettigi negatif kare.
Rastgele bos gokyuzu karesi modele bir sey ogretmez; modelin takildigi kare ogretir.

--------------------------------------------------------------------------------
 GUVENLIK KURALI (en kritik kisim)
--------------------------------------------------------------------------------
Bir karede hedef GORUNUYORSA ve biz onu etiketsiz verirsek, modele "bu ucagi
GORME" demis oluruz -> gercek tespiti bozar. Bu, negatif eklemenin tek gercek
riski. O yuzden kare ancak SU KOSULLARDA negatif sayilir:

  (a) 6 keypoint'in TAMAMI kamera ARKASINDA  -> hedef kesin kadrajda degil, VEYA
  (b) hepsi onde ve projekte kutu, kadrajin TAMAMEN disinda + `--kenar-pay`
      piksel emniyet payi (govde iskelet uclarindan tasar diye kutu ayrica
      marj_x/marj_y ile SISIRILIR).

Aradaki her sey (kismen gorunur, kadrajin kiyisinda, kp'lerin bir kismi arkada)
REDDEDILIR. Emin olmadigimiz kareyi negatif yapmayiz. Rapor "riskli" sayaciyla
neyin neden elendigini yazar.

--------------------------------------------------------------------------------
 AKIS
--------------------------------------------------------------------------------
  1. Oturum(lar)i oku (pose/kayit_ucusu.py ciktisi; etiketle.py ile AYNI
     projeksiyon zinciri -> tilt/HFOV pose/kalibre.py'den canli okunur).
  2. Her kare icin truth'tan hedefi projekte et -> GUVENLI / RISKLI.
  3. GUVENLI karelerde modeli DUSUK conf ile kostur. Cikan HER kutu, tanim geregi
     YANLIS POZITIFTIR (o karede hedef yok).
  4. Kareyi "en yuksek FP conf" ile puanla, azalan sirala, ilk --n tanesini yaz.
  5. Rapor: FP conf histogrami + FP merkezlerinin IZGARA ISI HARITASI (HUD
     kosesinde mi kumeleniyor, sayiyla gorunur) + onizleme cizimleri.

CIKTI:
  <cikti>/images/neg_XXXXXX.png     kare kopyasi
  <cikti>/labels/neg_XXXXXX.txt     BOS dosya  (= background ornegi)
  <cikti>/negatif_rapor.json        sayilar, conf dagilimi, isi haritasi
  <cikti>/onizleme/*.jpg            FP kutulari cizili QA kareleri

KULLANIM:
    python veriseti/negatif_topla.py --oturum C:\\talon_pose_data\\ham\\oturum_X \\
        --model models/best.pt --n 1000 --cikti C:\\talon_dataset_v2\\negatif
    (--imgsz verilmezse modelin KENDI egitim imgsz'i okunur)

NOT: --model ile HANGI modelin zayifligini madenledigini sec. Kullanilacak model
hangisiyse onunla madenle (baska modelin FP'si baska yerde olabilir).
================================================================================
"""
import os
import sys
import json
import shutil
import argparse

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _KOK not in sys.path:
    sys.path.insert(0, _KOK)

import numpy as np

from pose import geometri
from pose.etiketle import Akis, KP_CM


# =============================================================================
#  Saf yardimcilar (birim testli: tests/test_negatif_topla.py)
# =============================================================================

def kutu_zarfi(uvs, marj_x, marj_y):
    """kp piksel listesinden SISIRILMIS kutu. -> (x0, y0, x1, y1)
    Sisirme sebebi: kp'ler iskelet uclari; govde silueti disari tasar. Negatif
    kararinda sisirme GUVENLIK yonunde calisir (kutu buyudukce 'tamamen disarida'
    demek zorlasir -> supheli kare reddedilir)."""
    us = [uv[0] for uv in uvs]
    vs = [uv[1] for uv in uvs]
    x0, x1 = min(us), max(us)
    y0, y1 = min(vs), max(vs)
    w, h = x1 - x0, y1 - y0
    return (x0 - w * marj_x, y0 - h * marj_y,
            x1 + w * marj_x, y1 + h * marj_y)


def disarida_pay(uvs, W, H, marj_x=0.10, marj_y=0.30):
    """Sisirilmis kutu kadrajin NE KADAR disinda? -> px (float)

      pay > 0  : kutu kadrajin tamamen disinda, en yakin kenara pay px var
      pay <= 0 : kutu kadrajla KESISIYOR (|pay| = iceri girme miktari)
      +inf     : tum kp'ler kamera arkasinda (hedef kesinlikle gorunmuyor)

    QA'nin omurgasi: bu sayi KUCUK olan kareler sinira en yakin, yani
    "acaba ucak gorunuyor mu?" riskinin YOGUNLASTIGI kareler. Onizleme onlardan
    orneklenir; rastgele ornek kolay kareleri gosterip yanlis guven verir."""
    if all(uv is None for uv in uvs):
        return float("inf")
    if any(uv is None for uv in uvs):
        return float("-inf")                       # kismen arkada = en riskli
    x0, y0, x1, y1 = kutu_zarfi(uvs, marj_x, marj_y)
    return max(-x1, x0 - W, -y1, y0 - H)


def gerekli_pay(uvs, W, H, marj_x, marj_y, kenar_pay, pay_oran):
    """Kadraj disi sayilmak icin gereken ASGARI pay (px).

    Sabit `kenar_pay` tek basina YETMEZ: hedefin ROTASYONU normal (bozulabilen)
    kanaldan geliyor -- truth'ta rotasyon yok. Yanlis rotasyon kp zarfini
    doner/kaydirir; bu hatanin buyuklugu hedefin KENDI boyutuyla sinirlidir
    (govde 1.7 m). O yuzden pay, kutunun kendi boyutuyla OLCEKLENIR:

        gerekli = max(kenar_pay, pay_oran * max(kutu_w, kutu_h))

    pay_oran=0.5 -> "kutu, kendi boyunun yarisi kadar disarida olmali". Uzakta
    kutu kucuk (birkac px) -> kenar_pay baglar; yakinda kutu buyuk -> oran baglar.
    Rotasyon hatasina mesafeden BAGIMSIZ dayanikli olmanin yolu bu."""
    x0, y0, x1, y1 = kutu_zarfi(uvs, marj_x, marj_y)
    return max(kenar_pay, pay_oran * max(x1 - x0, y1 - y0))


def negatif_mi(uvs, W, H, marj_x=0.10, marj_y=0.30, kenar_pay=8.0, pay_oran=0.5):
    """Kare GUVENLE negatif sayilabilir mi? -> (guvenli_mi, sebep)

    uvs: 6 keypoint'in projeksiyonu; kamera arkasindaki kp icin None.
    Kararlar dokumandaki (a)/(b) kurallari; ARADAKI HER SEY reddedilir.
    Karar disarida_pay() uzerinden verilir -> QA'da gosterilen sayi ile
    kararin kendisi AYNI hesaptan gelir (ikisi ayrisamaz)."""
    arkada = sum(1 for uv in uvs if uv is None)
    if arkada == len(uvs):
        return True, "tamami_arkada"
    if arkada > 0:
        # Bir kismi onde bir kismi arkada = hedef kamera duzlemini kesiyor,
        # yani COK yakin. Kadrajda olma ihtimali yuksek -> asla negatif sayma.
        return False, "kismen_arkada"
    if (disarida_pay(uvs, W, H, marj_x, marj_y)
            > gerekli_pay(uvs, W, H, marj_x, marj_y, kenar_pay, pay_oran)):
        return True, "kadraj_disi"
    return False, "kadrajda"


def izgara_say(fp_merkezleri, W, H, nx=6, ny=4):
    """FP merkezlerini nx*ny izgaraya say. -> ny satirli, nx sutunlu int matris.
    HUD kosede kumeleniyorsa o hucre patlar (PROP_MASKE analizinin ayni mantigi)."""
    izgara = [[0] * nx for _ in range(ny)]
    for cx, cy in fp_merkezleri:
        if W <= 0 or H <= 0:
            continue
        i = min(int(max(cy, 0.0) / H * ny), ny - 1)
        j = min(int(max(cx, 0.0) / W * nx), nx - 1)
        izgara[i][j] += 1
    return izgara


def histogram(degerler, kenarlar):
    """Basit histogram. -> her bin icin adet (len(kenarlar)-1 uzunlukta)."""
    say = [0] * (len(kenarlar) - 1)
    for v in degerler:
        for k in range(len(say)):
            if kenarlar[k] <= v < kenarlar[k + 1]:
                say[k] += 1
                break
        else:
            if v >= kenarlar[-1]:
                say[-1] += 1
    return say


# =============================================================================
#  Oturum tarama
# =============================================================================

def _oturum_kareleri(oturum, dt, marj_x, marj_y, kenar_pay, bozulmayi_atla=False,
                     pay_oran=0.5):
    """Bir oturumdaki GUVENLI negatif adaylarini dondur.
    -> (adaylar, sayac)   aday: {"png": yol, "t": t, "W": W, "H": H, "sebep": s}"""
    j_yol = os.path.join(oturum, "telemetri.jsonl")
    if not os.path.exists(j_yol):
        print("[HATA] telemetri.jsonl yok: %s" % oturum)
        return [], {}

    akis = None
    a_yol = os.path.join(oturum, "telemetri_akis.jsonl")
    if os.path.exists(a_yol):
        akis = Akis(a_yol)
        if len(akis) < 2:
            akis = None

    sayac = {"guvenli": 0, "kadrajda": 0, "kismen_arkada": 0,
             "bozulma": 0, "kare_yok": 0}
    adaylar = []

    with open(j_yol, encoding="utf-8") as f:
        satirlar = [json.loads(s) for s in f if s.strip()]

    for sat in satirlar:
        png = os.path.join(oturum, sat["kare"])
        if not os.path.exists(png):
            sayac["kare_yok"] += 1
            continue
        if bozulmayi_atla and int(sat.get("corruption_mask", 0)) != 0:
            # VARSAYILAN KAPALI (etiketle.py'den farkli). Negatif karari
            # truth_target_pos'tan veriliyor; corruption NORMAL kanali kirletir,
            # truth'u DEGIL -> bozuk kareyi atmak veriyi bosuna yakar (canli
            # olcum: yarisma konfigurasyonunda karelerin %100'u 'bozuk' isaretli).
            # Bozulmadan etkilenen tek girdi hedef ROTASYONU; onun payi
            # gerekli_pay()'de kutu boyutuyla olceklenerek sogurulur.
            sayac["bozulma"] += 1
            continue
        W, H = int(sat["W"]), int(sat["H"])

        if akis is not None:
            dpos, drot, tpos, trot = akis.durum(float(sat["t"]) - dt)
        else:
            dpos = np.asarray(sat.get("truth_drone_pos", sat["drone_pos"]), float)
            drot = np.asarray(sat["drone_rot_rpy"], float)
            tpos = np.asarray(sat["truth_target_pos"], float)
            trot = np.asarray(sat["target_rot_rpy"], float)

        cam_pos, R_cam = geometri.kamera_pozu(dpos, drot)
        fx = geometri.fx_from_hfov(W)
        kp_w = geometri.keypoints_dunyada(tpos, trot, KP_CM)
        uvs = [geometri.projekte(p, cam_pos, R_cam, fx, W, H) for p in kp_w]

        guvenli, sebep = negatif_mi(uvs, W, H, marj_x, marj_y, kenar_pay, pay_oran)
        if guvenli:
            sayac["guvenli"] += 1
            pay = disarida_pay(uvs, W, H, marj_x, marj_y)
            kutu = None if sebep == "tamami_arkada" else kutu_zarfi(uvs, marj_x, marj_y)
            d_m = float(np.linalg.norm(np.asarray(tpos) - np.asarray(dpos))) / 100.0
            adaylar.append({"png": png, "t": float(sat["t"]),
                            "W": W, "H": H, "sebep": sebep,
                            "pay": pay, "kutu": kutu, "mesafe_m": d_m})
        else:
            sayac[sebep] = sayac.get(sebep, 0) + 1

    return adaylar, sayac


# =============================================================================
#  Ana akis
# =============================================================================

def qa_ciz(cv2, bgr, aday, kenar_pay):
    """QA karesine KARARIN GEREKCESINI ciz. Insan gozu 'ucak gercekten yok mu?'
    sorusunu bu cizimle yanitlar:
      - sari ok  : hedefin kadraj DISINDA hangi yonde oldugu (+ mesafe)
      - sari kutu: projekte kutu (kadraja kirpilmis gorunur parcasi)
      - kenar payi: sinira kac px kaldigi (kucukse o kare kritik)
    Ok/kutu kadrajin ICINE dusuyorsa guvenlik kurali ZAYIF demektir."""
    H, W = bgr.shape[:2]
    pay = aday["pay"]
    ust = "GUVENLI (%s)  pay=%s px  mesafe=%.0f m" % (
        aday["sebep"], "sonsuz" if pay == float("inf") else "%.0f" % pay,
        aday.get("mesafe_m", 0.0))
    cv2.putText(bgr, ust, (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                (0, 255, 255), 2)
    cv2.putText(bgr, "sari = hedefin projekte yeri (kadraj disi olmali)",
                (12, 54), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

    kutu = aday.get("kutu")
    if kutu is None:                                   # tamami arkada
        cv2.putText(bgr, "hedef KAMERA ARKASINDA", (12, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        return bgr

    x0, y0, x1, y1 = kutu
    cv2.rectangle(bgr, (int(x0), int(y0)), (int(x1), int(y1)), (0, 255, 255), 2)
    hx = int(min(max((x0 + x1) / 2.0, 5), W - 5))      # kadraja kirpilmis hedef yonu
    hy = int(min(max((y0 + y1) / 2.0, 5), H - 5))
    cv2.arrowedLine(bgr, (W // 2, H // 2), (hx, hy), (0, 255, 255), 2, tipLength=0.03)
    cv2.putText(bgr, "kutu: [%.0f %.0f %.0f %.0f]  kadraj: %dx%d"
                % (x0, y0, x1, y1, W, H), (12, 80),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
    return bgr


def _egitim_imgsz(pt_yolu, varsayilan=640):
    """Checkpoint'in kendi egitim imgsz'i (web/server.py ile ayni mantik)."""
    try:
        import torch
        ck = torch.load(pt_yolu, map_location="cpu", weights_only=False)
        v = int((ck.get("train_args") or {}).get("imgsz") or 0)
        del ck
        return v if v > 0 else int(varsayilan)
    except Exception:
        return int(varsayilan)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Hard negative madencisi (Hat C)")
    ap.add_argument("--oturum", nargs="+", required=True,
                    help="pose/kayit_ucusu.py oturum klasoru (birden fazla olabilir)")
    ap.add_argument("--model", default=os.path.join(_KOK, "models", "best.pt"),
                    help="zayifligi madenlenecek .pt (kullanacagin model olmali)")
    ap.add_argument("--imgsz", type=int, default=0,
                    help="0 = modelin KENDI egitim imgsz'i")
    ap.add_argument("--conf", type=float, default=0.05,
                    help="madencilik esigi: DUSUK tut, zayif FP'ler de gorunsun")
    ap.add_argument("--n", type=int, default=1000, help="yazilacak zor negatif adedi")
    ap.add_argument("--cikti", required=True, help="cikti klasoru")
    ap.add_argument("--dt", type=float, default=0.0,
                    help="kare-telemetri gecikmesi (pose/kalibre.py olcer)")
    ap.add_argument("--marj-x", type=float, default=0.10)
    ap.add_argument("--marj-y", type=float, default=0.30)
    ap.add_argument("--kenar-pay", type=float, default=8.0,
                    help="kadraj disi sayilmak icin gereken SABIT emniyet payi (px)")
    ap.add_argument("--pay-oran", type=float, default=0.5,
                    help="ek pay = bu oran x kutu boyutu (hedef rotasyonu normal "
                         "kanaldan gelir; hatasi hedef boyutuyla sinirli)")
    ap.add_argument("--bozulmayi-atla", action="store_true",
                    help="corruption_mask!=0 kareleri ele (VARSAYILAN KAPALI: "
                         "negatif karari truth konumdan verilir, corruption "
                         "truth'u kirletmez)")
    ap.add_argument("--onizle", type=int, default=30,
                    help="FP cizimli QA karesi adedi (0 = kapali)")
    ap.add_argument("--sahi", action="store_true",
                    help="SAHI dilimleme ile madenle (canlida acikken kullan)")
    ap.add_argument("--qa", type=int, default=0,
                    help="SADECE QA: guvenlik kararini denetle. SINIRA EN YAKIN N "
                         "kareyi gerekce cizimiyle yazar, model KOSMAZ, negatif "
                         "URETMEZ. Once bunu kos, gozunle onayla, sonra madenle.")
    args = ap.parse_args(argv)

    # --- 1) GUVENLI negatif havuzu ---
    havuz, toplam_sayac = [], {}
    for otr in args.oturum:
        adaylar, sayac = _oturum_kareleri(otr, args.dt, args.marj_x, args.marj_y,
                                          args.kenar_pay, args.bozulmayi_atla,
                                          args.pay_oran)
        havuz.extend(adaylar)
        for k, v in sayac.items():
            toplam_sayac[k] = toplam_sayac.get(k, 0) + v
        print("[TARA] %s -> %d guvenli aday" % (os.path.basename(otr), len(adaylar)))

    print("[TARA] TOPLAM guvenli negatif havuzu: %d kare" % len(havuz))
    print("[TARA] eleme: %s" % json.dumps(toplam_sayac, ensure_ascii=False))
    if not havuz:
        print("[HATA] guvenli negatif bulunamadi. Hedefin kadraj DISINDA oldugu")
        print("       bir ucus kaydi gerekiyor (arama fazi / hedeften uzaga bakis).")
        return 2

    # --- 1b) QA MODU: kararı denetle, uretme ---
    # Rastgele ornek KOLAY kareleri gosterir ve yanlis guven verir. Burada
    # havuz 'pay'a gore SIRALANIR ve EN KUCUK paylilar (= sinira en yakin,
    # riskin yogunlastigi kareler) secilir. Onlar temizse gerisi zaten temiz.
    if args.qa > 0:
        import cv2
        os.makedirs(args.cikti, exist_ok=True)
        sirali = sorted(havuz, key=lambda a: a["pay"])
        secim = sirali[:args.qa]
        for k, a in enumerate(secim):
            bgr = cv2.imread(a["png"])
            if bgr is None:
                continue
            qa_ciz(cv2, bgr, a, args.kenar_pay)
            cv2.imwrite(os.path.join(args.cikti, "qa_%03d_pay%s.jpg"
                        % (k, "inf" if a["pay"] == float("inf") else
                           "%04.0f" % max(a["pay"], 0))), bgr)
        sonlu = [a["pay"] for a in havuz if a["pay"] != float("inf")]
        print("")
        print("=" * 60)
        print("  QA: %d kare yazildi -> %s" % (len(secim), args.cikti))
        print("  Havuz: %d guvenli (%d tanesi kamera-arkasi = tartismasiz)"
              % (len(havuz), len(havuz) - len(sonlu)))
        if sonlu:
            sonlu.sort()
            print("  Kenar payi (px): min=%.0f  medyan=%.0f  max=%.0f"
                  % (sonlu[0], sonlu[len(sonlu) // 2], sonlu[-1]))
            print("  -> qa_000 EN RISKLI kare. Icinde ucak GORUNUYORSA")
            print("     --kenar-pay / --marj-x / --marj-y buyutulmeli.")
        print("=" * 60)
        return 0

    # --- 2) Modeli kostur: her kutu = yanlis pozitif ---
    imgsz = args.imgsz or _egitim_imgsz(args.model, 640)
    print("[MODEL] %s  imgsz=%d  conf=%.2f  sahi=%s"
          % (os.path.basename(args.model), imgsz, args.conf, args.sahi))
    import cv2
    from detection.gorsel_tespit import HedefDedektor
    ded = HedefDedektor(args.model, conf=args.conf, imgsz=imgsz, sahi=args.sahi)
    if not ded.hazir:
        print("[HATA] model yuklenemedi: %s" % ded.hata)
        return 2

    puanli, fp_merkez, fp_conf = [], [], []
    for i, a in enumerate(havuz):
        bgr = cv2.imread(a["png"])
        if bgr is None:
            continue
        kutular = ded.tespit_hepsi(bgr)
        a["fp"] = [{"cx": k["cx"], "cy": k["cy"], "w": k["w"], "h": k["h"],
                    "conf": k["conf"]} for k in kutular]
        a["puan"] = max([k["conf"] for k in kutular], default=0.0)
        if kutular:
            for k in kutular:
                fp_merkez.append((k["cx"], k["cy"]))
                fp_conf.append(k["conf"])
        puanli.append(a)
        if (i + 1) % 200 == 0:
            print("[MADEN] %d/%d kare tarandi" % (i + 1, len(havuz)))

    zor = [a for a in puanli if a["puan"] > 0.0]
    zor.sort(key=lambda a: -a["puan"])
    secilen = zor[:args.n]
    print("[MADEN] FP ureten kare: %d/%d  (toplam %d yanlis kutu)"
          % (len(zor), len(puanli), len(fp_conf)))
    if len(zor) < args.n:
        print("[UYARI] istenen %d, bulunan %d. Daha fazla kayit gerekiyor "
              "veya --conf dusur." % (args.n, len(zor)))

    # --- 3) Yaz: kare + BOS etiket ---
    img_dir = os.path.join(args.cikti, "images")
    lbl_dir = os.path.join(args.cikti, "labels")
    os.makedirs(img_dir, exist_ok=True)
    os.makedirs(lbl_dir, exist_ok=True)
    for k, a in enumerate(secilen):
        ad = "neg_%06d" % k
        shutil.copy2(a["png"], os.path.join(img_dir, ad + ".png"))
        open(os.path.join(lbl_dir, ad + ".txt"), "w").close()   # BOS = background

    # --- 4) Onizleme (FP kutulari cizili) ---
    if args.onizle > 0 and secilen:
        onz = os.path.join(args.cikti, "onizleme")
        os.makedirs(onz, exist_ok=True)
        adim = max(1, len(secilen) // args.onizle)
        for k in range(0, len(secilen), adim):
            a = secilen[k]
            bgr = cv2.imread(a["png"])
            if bgr is None:
                continue
            for f in a["fp"]:
                x0 = int(f["cx"] - f["w"] / 2); y0 = int(f["cy"] - f["h"] / 2)
                x1 = int(f["cx"] + f["w"] / 2); y1 = int(f["cy"] + f["h"] / 2)
                cv2.rectangle(bgr, (x0, y0), (x1, y1), (0, 0, 255), 2)
                cv2.putText(bgr, "FP %.2f" % f["conf"], (x0, max(y0 - 5, 12)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            cv2.imwrite(os.path.join(onz, "neg_%06d.jpg" % k), bgr)

    # --- 5) Rapor ---
    W = secilen[0]["W"] if secilen else 0
    H = secilen[0]["H"] if secilen else 0
    izgara = izgara_say(fp_merkez, W, H)
    kenarlar = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    rapor = {
        "model": os.path.abspath(args.model), "imgsz": imgsz, "conf": args.conf,
        "sahi": bool(args.sahi),
        "oturumlar": [os.path.abspath(o) for o in args.oturum],
        "eleme": toplam_sayac,
        "guvenli_havuz": len(havuz),
        "fp_ureten_kare": len(zor),
        "yazilan": len(secilen),
        "toplam_fp_kutu": len(fp_conf),
        "fp_conf_hist": dict(zip(["%.1f" % k for k in kenarlar[:-1]],
                                 histogram(fp_conf, kenarlar))),
        "fp_izgara_6x4": izgara,
        "kare_boyut": [W, H],
    }
    with open(os.path.join(args.cikti, "negatif_rapor.json"), "w",
              encoding="utf-8") as f:
        json.dump(rapor, f, indent=2, ensure_ascii=False)

    print("")
    print("=" * 60)
    print("  YAZILAN ZOR NEGATIF : %d  ->  %s" % (len(secilen), args.cikti))
    print("  FP ISI HARITASI (satir=ust->alt, sutun=sol->sag):")
    for satir in izgara:
        print("    " + " ".join("%5d" % c for c in satir))
    print("  (kose hucreleri patliyorsa FP'ler HUD'da demektir)")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())

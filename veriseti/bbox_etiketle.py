# -*- coding: utf-8 -*-
"""
================================================================================
 BBOX ETIKETLEYICI — CANLI (yakalama surerken etiketle)
================================================================================
GELISTIRME ARACI — teslim paketine girmez.

Klasoru SUREKLI izler: web/server.py (AVCI_KAYIT) yeni kare yazdikca liste
kendiliginden buyur. Ucus devam ederken etiketlemeye baslanabilir; bos
beklenmez.

DOSYA DUZENI (yakalayici uretir):
    talon1_0000.png   kare
    talon1_0000.txt   BOS  = "henuz etiketlenmedi"
                      DOLU = "0 cx cy w h" (YOLO, normalize) = etiketli
Dosya BOYUTU tek dogruluk kaynagi -> ayri durum dosyasi yok, senkron kaymaz.

HIZ (5000 kare elle cizilecek — her tiklama sayilir):
  * Kutu KARELER ARASI TASINIR. 2 Hz'de Talon az kayar; yeni karede onceki kutu
    hazir gelir, cogu zaman ufak bir itme yeter. Ortadan baslamak her seferinde
    sifirdan cizmek demekti.
  * Enter/Space = KAYDET + SONRAKI (tek tusla akis).
  * Etiketlenmemis ilk kareye atlama (Tab) — arayuz seni bekleyen ise goturur.
  * Fare tekerlegi zoom, orta tus (veya bosluk-surukle) pan.

TUSLAR
    Enter / Space   kaydet + sonraki          Tab   ilk ETIKETSIZ kareye atla
    Sag / Sol       sonraki / onceki kare     R     kutuyu ortala (sifirla)
    D               etiketi SIL (txt bosalir) F     kutuyu kadraja sigdir
    + / -           zoom                      0     zoom sifirla
    Esc             cikis

KULLANIM
    python veriseti/bbox_etiketle.py --klasor C:\\talon_dataset_v2\\pozitif
    [--ad talon1]  [--hedef 5000]
================================================================================
"""
import os
import sys
import glob
import argparse
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

TARAMA_MS = 1000          # klasoru kac ms'de bir yeniden tara (yeni kare gelir)
TUTAMAC = 7               # kose/kenar tutamac yaricapi (ekran px)
ASGARI_PX = 3             # gecerli kutu asgari kenari (goruntu px)


# =============================================================================
#  Saf yardimcilar (birim testli: tests/test_bbox_etiketle.py)
# =============================================================================

def guvenli_yaz(yol, icerik):
    """Etiketi KESIN yaz: atomik degistirme + fsync + geri okuyup dogrula.

    NEDEN (2026-08-11, kullanici istegi: "enter/space basinca kayit SAGLAM ve
    KESIN olsun"): eski kod duz `open(...,"w")` kullaniyordu. Uc riski vardi:
      1) fsync YOK -> veri isletim sistemi tamponunda kalir; makine cokerse
         ya da elektrik giderse yazi KAYBOLUR.
      2) ATOMIK DEGIL -> yazma ortasinda kesinti olursa dosya yarim kalir.
      3) HATA GORUNMEZ -> disk dolu / dosya kilitli / izin yoksa istisna
         Tkinter geri cagirmasinda kaybolur, arayuz SONRAKI KAREYE GECERDI;
         kullanici kaydettim sanip devam ederdi.
    Simdi: gecici dosyaya yaz -> flush + fsync -> os.replace (atomik, Windows
    dahil) -> geri oku ve DOGRULA. Herhangi biri tutmazsa Exception yukselir.
    """
    gecici = yol + ".tmp"
    with open(gecici, "w", encoding="utf-8", newline="\n") as f:
        f.write(icerik)
        f.flush()
        os.fsync(f.fileno())
    os.replace(gecici, yol)
    with open(yol, encoding="utf-8") as f:
        okunan = f.read()
    if okunan != icerik:
        raise IOError("dogrulama basarisiz: yazilan %d bayt, geri okunan %d"
                      % (len(icerik), len(okunan)))


def yolo_satiri(kutu, W, H):
    """[x1,y1,x2,y2] piksel -> '0 cx cy w h' (normalize, kirpilmis)."""
    x1, y1, x2, y2 = kutu
    x1, x2 = min(x1, x2), max(x1, x2)
    y1, y2 = min(y1, y2), max(y1, y2)
    cx = ((x1 + x2) / 2.0) / W
    cy = ((y1 + y2) / 2.0) / H
    w = (x2 - x1) / float(W)
    h = (y2 - y1) / float(H)
    d = [min(1.0, max(0.0, v)) for v in (cx, cy, w, h)]
    return "0 %.6f %.6f %.6f %.6f" % tuple(d)


def yolo_oku(metin, W, H):
    """'0 cx cy w h' -> [x1,y1,x2,y2] piksel. Bos/bozuksa None."""
    if not metin:
        return None
    parca = metin.strip().split()
    if len(parca) < 5:
        return None
    try:
        cx, cy, w, h = (float(v) for v in parca[1:5])
    except ValueError:
        return None
    return [(cx - w / 2.0) * W, (cy - h / 2.0) * H,
            (cx + w / 2.0) * W, (cy + h / 2.0) * H]


def kutu_kirp(kutu, W, H):
    """Kutuyu goruntu sinirlarina kirp + kose sirasini duzelt."""
    x1, y1, x2, y2 = kutu
    x1, x2 = min(x1, x2), max(x1, x2)
    y1, y2 = min(y1, y2), max(y1, y2)
    return [max(0.0, min(x1, W)), max(0.0, min(y1, H)),
            max(0.0, min(x2, W)), max(0.0, min(y2, H))]


def kutu_gecerli(kutu, W, H, asgari=ASGARI_PX):
    """Kaydedilebilir mi? (kirpma SONRASI en az `asgari` px kenar)"""
    if kutu is None:
        return False
    x1, y1, x2, y2 = kutu_kirp(kutu, W, H)
    return (x2 - x1) >= asgari and (y2 - y1) >= asgari


def kutu_tasi(kutu, dx, dy, W, H):
    """Kutuyu kaydir; kadrajdan TASMASIN diye kaymayi sinirla (boyut korunur)."""
    x1, y1, x2, y2 = kutu
    dx = max(-x1, min(dx, W - x2))
    dy = max(-y1, min(dy, H - y2))
    return [x1 + dx, y1 + dy, x2 + dx, y2 + dy]


def orta_kutu(W, H, oran=0.12):
    """Kadraj ortasinda baslangic kutusu (ilk kare / R tusu)."""
    w, h = W * oran, H * oran
    return [W / 2.0 - w / 2, H / 2.0 - h / 2, W / 2.0 + w / 2, H / 2.0 + h / 2]


def etiketli_mi(txt_yolu):
    """DOLU .txt = etiketli. Dosya boyutu tek dogruluk kaynagi."""
    try:
        return os.path.getsize(txt_yolu) > 0
    except OSError:
        return False


#  Yakalama .png uretir; DAGITIM kopyalari .jpg olabilir (48.9 GB -> 8.8 GB,
#  etiket normalize oldugu icin kutu orijinal PNG'ye birebir oturur). Uzanti
#  listesi TEK yerde dursun ki iki akis da ayni kodu kullansin.
KARE_UZANTILARI = (".png", ".jpg", ".jpeg")


def kare_listesi(klasor, ad):
    """<ad>_*.<kare uzantisi> dosyalarini NUMARA sirasinda dondur."""
    yollar = []
    for uz in KARE_UZANTILARI:
        yollar += glob.glob(os.path.join(klasor, ad + "_*" + uz))
    def anahtar(p):
        t = os.path.splitext(os.path.basename(p))[0][len(ad) + 1:]
        return int(t) if t.isdigit() else 0
    return sorted(yollar, key=anahtar)


class Akis:
    """telemetri_akis.jsonl (~48 Hz) -> zaman indeksli durum, ara-degerlemeli.

    NEDEN: kare, telemetriden ESKI gelir (pencere yakalama gecikmesi). Olculdu:
    dt = 0.10 sn, dedektor referansiyla IoU 0.693 -> 0.824 (banka kareleri
    0.637 -> 0.768). Bu telafi ancak yeterli ORNEKLEME varsa yapilabilir; 2 Hz
    kare telemetrisiyle denendi, ara-degerlemenin kendi hatasi kazanci yedi."""

    def __init__(self, yol):
        import json as _j
        t, dp, dr, tp, tr = [], [], [], [], []
        try:
            with open(yol, encoding="utf-8") as f:
                for s in f:
                    s = s.strip()
                    if not s:
                        continue
                    try:
                        r = _j.loads(s)
                    except ValueError:
                        continue
                    t.append(r["t"]); dp.append(r["dp"]); dr.append(r["dr"])
                    tp.append(r["tp"]); tr.append(r["tr"])
        except OSError:
            pass
        import numpy as _np
        self.t = _np.asarray(t, float)
        self.dp = _np.asarray(dp, float); self.dr = _np.asarray(dr, float)
        self.tp = _np.asarray(tp, float); self.tr = _np.asarray(tr, float)

    def __len__(self):
        return len(self.t)

    def kapsar(self, t):
        return len(self.t) > 1 and self.t[0] <= t <= self.t[-1]

    def durum(self, t_sorgu):
        """(dpos, drot, tpos, trot) @ t_sorgu. Aci sarmasi YOK: hedef/drone
        acilari bu pencerede (21 ms) +-180 sinirini nadiren gecer; gecerse o
        kare zaten supheli isaretlenir."""
        import numpy as _np
        if len(self.t) == 0:
            return None
        i = int(_np.searchsorted(self.t, t_sorgu))
        if i <= 0:
            return self.dp[0], self.dr[0], self.tp[0], self.tr[0]
        if i >= len(self.t):
            return self.dp[-1], self.dr[-1], self.tp[-1], self.tr[-1]
        t0, t1 = self.t[i - 1], self.t[i]
        f = 0.0 if t1 <= t0 else (t_sorgu - t0) / (t1 - t0)
        lin = lambda X: X[i - 1] + (X[i] - X[i - 1]) * f
        return lin(self.dp), lin(self.dr), lin(self.tp), lin(self.tr)


def projeksiyon_kutusu(sat, marj_x=0.07, marj_y=0.10, kenar_tol=5.0, durum=None):
    """telemetri.jsonl satirindan hedefin PROJEKTE kutusu. -> [x1,y1,x2,y2] | None

    NEDEN: truth hedef konumu + ucagin 3B nokta modeli + kalibreli kamera ile
    kutu HESAPLANABILIR. 10 elle cizilmis kareyle olculdu: bu kutu, kullanicinin
    kendi ciziminin %90 IoU'suyla ayni (medyan 0.907). Yani 5000 kutuyu elle
    cizmek gereksiz; insan sadece ONAYLAR.

    None doner: truth yok / hedef kamera arkasinda / kutu kadraja tam sigmiyor
    (kismi gorunurde projeksiyon zarfi guvenilmez -> elle cizilsin)."""
    if not sat or sat.get("truth_target_pos") is None:
        return None
    try:
        import numpy as np
        from pose import geometri
        from veriseti.negatif_topla import KP_CM, kutu_zarfi
    except Exception:
        return None
    W, H = int(sat["W"]), int(sat["H"])
    if durum is not None:                    # gecikme telafili (t - dt) durumu
        dpos, drot, tpos, trot = (np.asarray(v, float) for v in durum)
    else:
        dpos = np.asarray(sat.get("truth_drone_pos") or sat["drone_pos"], float)
        drot = np.asarray(sat["drone_rot_rpy"], float)
        tpos = np.asarray(sat["truth_target_pos"], float)
        trot = np.asarray(sat["target_rot_rpy"], float)
    cam, R = geometri.kamera_pozu(dpos, drot)
    fx = geometri.fx_from_hfov(W)
    uvs = [geometri.projekte(p, cam, R, fx, W, H)
           for p in geometri.keypoints_dunyada(tpos, trot, KP_CM)]
    if any(u is None for u in uvs):
        return None
    x0, y0, x1, y1 = kutu_zarfi(uvs, marj_x, marj_y)
    if (x0 < -kenar_tol or y0 < -kenar_tol
            or x1 > W + kenar_tol or y1 > H + kenar_tol):
        return None                      # kismen disarida -> elle
    return kutu_kirp([x0, y0, x1, y1], W, H)


def hedef_roll(sat):
    """Telemetri satirindan hedefin |banka| acisi (derece). Bilinmiyorsa None.

    NEDEN ONEMLI: 50 kareyle olculdu -- projeksiyon kutusunun dogrulugu hedefin
    banka acisiyla dogrudan bozuluyor:
        |roll| < 20 grad -> dedektorle IoU medyan ~0.85 (kutu oturuyor)
        |roll| >=20 grad -> IoU ~0.67 (kutu kayiyor, gozle de gorunuyor)
    Sebep BOYUT degil KONUM hatasi (marj genisletmek hic ise yaramadi) ve
    isaret de dogru (+1 en iyi). Kalan aday: kare telemetriden ESKI ve manevrada
    bagil geometri en hizli degistigi icin hata orada patliyor (dt=0.15 sn
    telafisi banka karelerinde +0.055 IoU verdi).
    Cozulene kadar: bu kareler ISARETLENIR, insan bakar."""
    try:
        return abs(float(sat["target_rot_rpy"][0]))
    except (KeyError, TypeError, IndexError, ValueError):
        return None


def telemetri_oku(klasor):
    """telemetri.jsonl -> {kare_adi: satir}. Yoksa bos sozluk."""
    import json
    yol = os.path.join(klasor, "telemetri.jsonl")
    d = {}
    try:
        with open(yol, encoding="utf-8") as f:
            for s in f:
                s = s.strip()
                if not s:
                    continue
                try:
                    r = json.loads(s)
                except ValueError:
                    continue
                if "kare" in r:
                    d[r["kare"]] = r
    except OSError:
        pass
    return d


# Tutamac sirasi _tutamaclar() ile AYNI olmak ZORUNDA (fare ve klavye ayni
# indeksi kullanir; ayrisirsa fareyle secilen tutamaci klavye baska yerden iter).
TUT_SOL_UST, TUT_SAG_UST, TUT_SOL_ALT, TUT_SAG_ALT = 0, 1, 2, 3
TUT_UST, TUT_ALT, TUT_SOL, TUT_SAG = 4, 5, 6, 7

# Kullanicinin istedigi tus dizilimi (kendi tarif ettigi gibi):
#   a sol-ust   w ust   d sag-ust
#   q sol               e sag
#   z sol-alt   s alt   x sag-alt
TUS_TUTAMAC = {
    "a": TUT_SOL_UST, "w": TUT_UST,  "d": TUT_SAG_UST,
    "q": TUT_SOL,                    "e": TUT_SAG,
    "z": TUT_SOL_ALT, "s": TUT_ALT,  "x": TUT_SAG_ALT,
}
TUTAMAC_AD = {0: "sol ust", 1: "sag ust", 2: "sol alt", 3: "sag alt",
              4: "ust", 5: "alt", 6: "sol", 7: "sag"}


def tutamac_tasi(kutu, i, dx, dy, W, H, asgari=ASGARI_PX):
    """Tek TUTAMACI dx,dy kadar it -> yeni kutu (kenar yeniden boyutlanir).

    Kenar tutamaclari tek eksende hareket eder (ust/alt yalniz dikey, sol/sag
    yalniz yatay); koseler iki eksende. Kutu TERS DONMEZ: karsi kenari gecmeye
    calisirsa `asgari` px kala durur -- aksi halde kullanici farkinda olmadan
    sifir/negatif alanli kutu uretir ve etiket sessizce bozulur."""
    x1, y1, x2, y2 = [float(v) for v in kutu]
    if i in (TUT_SOL_UST, TUT_SOL_ALT, TUT_SOL):
        x1 = min(max(x1 + dx, 0.0), x2 - asgari)
    if i in (TUT_SAG_UST, TUT_SAG_ALT, TUT_SAG):
        x2 = max(min(x2 + dx, float(W)), x1 + asgari)
    if i in (TUT_SOL_UST, TUT_SAG_UST, TUT_UST):
        y1 = min(max(y1 + dy, 0.0), y2 - asgari)
    if i in (TUT_SOL_ALT, TUT_SAG_ALT, TUT_ALT):
        y2 = max(min(y2 + dy, float(H)), y1 + asgari)
    return [x1, y1, x2, y2]


SILINEN_DIR = "_silinen"


def silme_hedefi(png_yolu, klasor):
    """Silinecek kare/etiket ciftinin TASINACAGI yollar. -> (png_hedef, txt_hedef)

    NEDEN TASIMA, NEDEN SILME DEGIL: yanlislikla basilan bir tus egitim verisini
    yok etmemeli. Cift `_silinen/` altina tasinir; listeden dusier ama diskte
    durur. Ctrl+Z son silmeyi geri alir, o da yetmezse klasorden elle geri
    konur."""
    ad = os.path.basename(png_yolu)
    hedef = os.path.join(klasor, SILINEN_DIR)
    return (os.path.join(hedef, ad),
            os.path.join(hedef, os.path.splitext(ad)[0] + ".txt"))


def kare_no_indeksi(kareler, ad, no):
    """DOSYA NUMARASINDAN liste indeksi. -> indeks | None

    NEDEN GEREKLI: kare silinince liste sirasi ile dosya numarasi AYRISIR
    (5050 kareden 4'u silinince talon1_0534, listenin 531. sirasina duser).
    Kullanici ekranda gordugu DOSYA ADINI soyluyor -> arama numaraya gore
    yapilmali, siraya gore degil."""
    hedef = "%s_%04d" % (ad, no)          # uzantisiz: .png ve .jpg ayni numara
    for i, p in enumerate(kareler):
        if os.path.splitext(os.path.basename(p))[0] == hedef:
            return i
    return None


def sonraki_dikkat(etiketli_bayrak, roll_listesi, baslangic, roll_esik=20.0):
    """`baslangic`tan SONRAKI ilk "goz gerektiren" kare. -> indeks | None

    Goz gerektiren = etiketi BOS  VEYA  hedef bankada (|roll| >= esik; olculdu:
    o bandda projeksiyon kutusu kayiyor).

    NEDEN DEGISTI: Tab eskiden "ilk ETIKETSIZ kare"ye gidiyordu. Toplu otomatik
    etiketlemeden sonra neredeyse hersey doldu, geriye tek bos kare kaldi ve o
    da listenin sonundaydi -> Tab kullaniciyi her seferinde sona firlatiyordu.
    Simdi Tab, sirayla ILERI giderek gercekten bakilmasi gereken kareye atar."""
    n = len(etiketli_bayrak)
    for k in range(1, n + 1):
        i = (baslangic + k) % n
        if not etiketli_bayrak[i]:
            return i
        r = roll_listesi[i] if i < len(roll_listesi) else None
        if r is not None and r >= roll_esik:
            return i
    return None


def gezinme_kabul(simdi, son_gezinme, asgari_aralik=0.08):
    """Tus TEKRARINI kis: iki gezinme arasi en az `asgari_aralik` sn olsun.

    NEDEN: Windows tus tekrari ~30 olay/sn uretir; bir karenin yuklenmesi
    (1.9 MB PNG cozme) ~40 ms surer (~15/sn). Fark Tk olay kuyruguna birikir
    ve tus BIRAKILDIKTAN sonra bile arayuz binlerce kare ileri kosar --
    kullanici oka basili tutunca liste sonuna firladi. Bu kapi, islenemeyecek
    olaylari daha kuyruga girmeden eler."""
    return (simdi - son_gezinme) >= asgari_aralik


def sonraki_etiketsiz(txt_yollari, baslangic):
    """`baslangic`tan itibaren ilk ETIKETSIZ indeks; yoksa bastan ara; yoksa None."""
    n = len(txt_yollari)
    for k in range(n):
        i = (baslangic + k) % n
        if not etiketli_mi(txt_yollari[i]):
            return i
    return None


# =============================================================================
#  Arayuz
# =============================================================================

class BBoxEtiketleyici:
    def __init__(self, kok, klasor, ad, hedef, oto=True, marj_x=0.07,
                 marj_y=0.10, roll_esik=20.0, basla=0, etiket_klasor=None):
        self.kok = kok
        self.klasor = klasor
        # None = .txt PNG'nin YANINDA (yakalama klasoru duzeni).
        # Dolu = .txt ayri klasorde (images/ + labels/ duzeni, talon_hepsi gibi
        # hazir veri setleri boyle). Bkz. _txt().
        self.etiket_klasor = etiket_klasor
        self.ad = ad
        self.hedef = hedef
        self.oto = oto               # truth projeksiyonundan kutu ON-DOLDUR
        self.marj_x, self.marj_y = marj_x, marj_y
        self.tel = telemetri_oku(klasor) if oto else {}
        self.kaynak = ""             # bu karedeki kutu nereden geldi (rozet)
        self.roll = None             # hedefin banka acisi (derece)
        self.supheli = False         # yuksek banka -> projeksiyon guvenilmez
        self.roll_esik = roll_esik   # olculen kirilma noktasi (20 grad)
        self.basla = int(basla)      # 0 = ilk etiketsiz; N = N. kare (1-tabanli)
        self._son_gezinme = 0.0      # tus tekrarini kismak icin
        self.aktif_tutamac = None    # klavyeyle secili tutamac (0-7) veya None
        self._son_silinen = None     # (png_kaynak, txt_kaynak, png_hedef, txt_hedef)

        self.kareler = []            # png yollari
        self.idx = 0
        self.img = None              # PIL Image (tam cozunurluk)
        self.tk_img = None
        self.W = self.H = 1
        self.kutu = None             # [x1,y1,x2,y2] goruntu pikseli
        self.son_kutu = None         # KARELER ARASI TASINAN kutu (hiz anahtari)
        self.zoom = 1.0
        self.ox = self.oy = 0.0      # goruntu -> tuval ofseti
        self.surukle = None          # ("yeni"|"tasi"|"tutamac", veri...)
        self.pan = None
        self.oto_yakin = True        # kare acilinca kutuya yakinlas (Z ile kapat)
        self.dokunuldu = False       # bu karede kutuya EL DEGDI mi (uyari icin)

        self._arayuz()
        self._tara(ilk=True)
        self.kok.after(TARAMA_MS, self._periyodik_tara)

    # ---------------------------------------------------------------- arayuz
    def _arayuz(self):
        self.kok.title("BBOX Etiketleyici — canli")
        self.kok.configure(bg="#14171c")

        ust = tk.Frame(self.kok, bg="#14171c")
        ust.pack(fill=tk.X, padx=8, pady=(8, 4))
        self.lbl_durum = tk.Label(ust, text="", bg="#14171c", fg="#e6e9ef",
                                  font=("Consolas", 12, "bold"), anchor="w")
        self.lbl_durum.pack(side=tk.LEFT)
        self.lbl_yeni = tk.Label(ust, text="", bg="#14171c", fg="#ffb454",
                                 font=("Consolas", 11), anchor="e")
        self.lbl_yeni.pack(side=tk.RIGHT)

        self.ilerleme = ttk.Progressbar(self.kok, maximum=max(self.hedef, 1))
        self.ilerleme.pack(fill=tk.X, padx=8)

        self.tuval = tk.Canvas(self.kok, bg="#0b0d10", highlightthickness=0,
                               cursor="crosshair")
        self.tuval.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        alt = tk.Label(self.kok, bg="#14171c", fg="#8b93a1", anchor="w",
                       font=("Consolas", 10),
                       text=" Enter/Space kaydet+sonraki | Tab ilk etiketsiz | "
                            "Tab: sonraki dikkat karesi | TUTAMAC: a w d / q e / z s x -> ok ile it | "
                            "R ortala | F sigdir | Del etiketi sil | Shift+Del KAREYI sil | "
                            "Ctrl+Z geri al | Y oto-yakin | "
                            "Shift+ok kutuyu tasi | SAG TUS yeni kutu | Esc cikis")
        alt.pack(fill=tk.X, padx=8, pady=(0, 8))

        self.tuval.bind("<Button-1>", self.tik)
        self.tuval.bind("<B1-Motion>", self.suru)
        self.tuval.bind("<ButtonRelease-1>", self.birak)
        self.tuval.bind("<Button-2>", self.pan_basla)
        self.tuval.bind("<B2-Motion>", self.pan_suru)
        # SAG TUS = KOSULSUZ yeni kutu. Sol tus kutunun ICINE denk gelirse
        # tasima yapar; oto-yakinlasmayla kutu ekranin ~%30'unu kapladigi icin
        # tiklamalarin cogu icine dusuyordu ve "yeniden cizmek" zorlasiyordu.
        self.tuval.bind("<Button-3>", self.sag_tik)
        self.tuval.bind("<B3-Motion>", self.suru)
        self.tuval.bind("<ButtonRelease-3>", self.birak)
        self.tuval.bind("<MouseWheel>", self.tekerlek)
        self.tuval.bind("<Configure>", lambda e: self.ciz())

        for tus in ("<Return>", "<space>"):
            self.kok.bind(tus, lambda e: self.kaydet_sonraki())
        self.kok.bind("<Tab>", lambda e: self.etiketsize_atla())
        self.kok.bind("<r>", lambda e: self.ortala())
        self.kok.bind("<f>", lambda e: self.sigdir())
        # D ve Z artik TUTAMAC tuslari -> eski islevleri tasindi
        self.kok.bind("<Delete>", lambda e: self.etiketi_sil())
        # Shift+Delete = KAREYI komple sil (Windows alisikligi; tek basina
        # Delete etiketi siler, kareyi DEGIL -> yanlislikla veri kaybi olmaz).
        self.kok.bind("<Shift-Delete>", lambda e: self.kareyi_sil())
        self.kok.bind("<Control-z>", lambda e: self.silmeyi_geri_al())
        self.kok.bind("<y>", lambda e: self.oto_yakin_degistir())
        # 8 TUTAMAC secimi (kullanicinin dizilimi). Ayni tusa tekrar basmak
        # secimi KALDIRIR -> ok tuslari yeniden KARE gezinir.
        for _t, _i in TUS_TUTAMAC.items():
            self.kok.bind("<%s>" % _t, lambda e, i=_i: self.tutamac_sec(i))
        # Tutamac SECILIYKEN ok tuslari o tutamaci 1 px iter (gezinmez).
        for _tus, _dx, _dy in (("<Up>", 0, -1), ("<Down>", 0, 1),
                               ("<Left>", -1, 0), ("<Right>", 1, 0)):
            self.kok.bind(_tus, lambda e, a=_dx, b=_dy: self.ok_tusu(a, b))
        self.kok.bind("<plus>", lambda e: self.zoomla(1.25))
        self.kok.bind("<minus>", lambda e: self.zoomla(0.8))
        self.kok.bind("<Key-0>", lambda e: self.sigdir_zoom())
        # Ok tuslari KARE gezinir; SHIFT+ok KUTUYU 1 px iter. Dordu de ayni
        # kuralda olsun diye Shift'e alindi (Yukari/Asagi itip Sol/Sag gezinmek
        # elde karisiyordu).
        for tus, dx, dy in (("<Shift-Up>", 0, -1), ("<Shift-Down>", 0, 1),
                            ("<Shift-Left>", -1, 0), ("<Shift-Right>", 1, 0)):
            self.kok.bind(tus, lambda e, a=dx, b=dy: self.itele(a, b))
        self.kok.bind("<Escape>", lambda e: self.kok.destroy())

    # ----------------------------------------------------------- dosya tarama
    def _txt(self, png_yolu):
        """Bu PNG'nin etiket dosyasi. TEK yer — silme/geri-alma dahil butun
        .txt yollari buradan gecer, dolayisiyla iki duzen de tek satirda ayrilir."""
        if self.etiket_klasor:
            gov = os.path.splitext(os.path.basename(png_yolu))[0]
            return os.path.join(self.etiket_klasor, gov + ".txt")
        return os.path.splitext(png_yolu)[0] + ".txt"

    def _tara(self, ilk=False):
        """Klasoru yeniden tara. Yeni kare geldiyse listeye ekle (indeks korunur).

        CANLI AKIS: yakalama surerken bos beklememek icin, KULLANICI BOSTAYSA yeni
        kare kendiliginden acilir. "Bostaysa" = uzerinde durdugu kare ZATEN
        ETIKETLI (isini bitirmis, bekliyor). Etiketsiz bir karedeyse CIZIYOR
        demektir -> ekran ALTINDAN KAYDIRILMAZ."""
        yeni = kare_listesi(self.klasor, self.ad)
        eklendi = len(yeni) - len(self.kareler)
        if self.oto and eklendi > 0:
            self.tel = telemetri_oku(self.klasor)   # yeni karelerin telemetrisi
        onceki_bostu = bool(self.kareler) and etiketli_mi(self._txt(self.kareler[self.idx]))
        self.kareler = yeni
        if ilk and self.kareler:
            if self.basla > 0:                  # --basla N: talon1_000N karesi
                i = kare_no_indeksi(self.kareler, self.ad, self.basla)
                # Numara bulunamazsa (silinmis olabilir) SIRA olarak yorumla.
                self.idx = i if i is not None else min(self.basla - 1,
                                                       len(self.kareler) - 1)
            else:                               # varsayilan: ilk ETIKETSIZ
                i = sonraki_etiketsiz([self._txt(p) for p in self.kareler], 0)
                self.idx = 0 if i is None else i
            self.yukle(self.idx)
            print("[ETIKET] acilis: kare %d/%d  (%s)  basla=%d"
                  % (self.idx + 1, len(self.kareler),
                     os.path.basename(self.kareler[self.idx]), self.basla))
        elif eklendi > 0:
            self.lbl_yeni.config(text="+%d yeni kare" % eklendi)
            self.kok.after(2500, lambda: self.lbl_yeni.config(text=""))
            if not self.kareler:
                pass
            elif not self.img or onceki_bostu:
                i = sonraki_etiketsiz([self._txt(p) for p in self.kareler], self.idx)
                if i is not None:
                    self.yukle(i)               # bosta -> yeni kare ANINDA gelsin
        self.guncelle_durum()

    def _periyodik_tara(self):
        try:
            self._tara()
        finally:
            self.kok.after(TARAMA_MS, self._periyodik_tara)

    def guncelle_durum(self):
        txts = [self._txt(p) for p in self.kareler]
        etiketli = sum(1 for t in txts if etiketli_mi(t))
        self.ilerleme.config(maximum=max(self.hedef, 1), value=etiketli)
        ad = (os.path.basename(self.kareler[self.idx])
              if self.kareler else "(kare bekleniyor...)")
        tut = ("   |   TUTAMAC: %s (ok tuslari iter)"
               % TUTAMAC_AD[self.aktif_tutamac]
               if self.aktif_tutamac is not None else "")
        self.lbl_durum.config(
            text="%s   |   kare %d/%d   |   ETIKETLI %d / hedef %d%s"
                 % (ad, self.idx + 1 if self.kareler else 0,
                    len(self.kareler), etiketli, self.hedef, tut))

    # ------------------------------------------------------------ kare yukle
    def yukle(self, i):
        if not self.kareler:
            return
        self.idx = max(0, min(i, len(self.kareler) - 1))
        yol = self.kareler[self.idx]
        try:
            self.img = Image.open(yol).convert("RGB")
        except Exception:
            self.img = None
            return
        self.W, self.H = self.img.size
        # KUTU KAYNAK ONCELIGI:
        #   1) kayitli .txt        -> bilincli, uyari yok
        #   2) truth projeksiyonu  -> %90 IoU (olculdu); sadece ONAYLA
        #   3) onceki kareden tasinan
        #   4) kadraj ortasi
        var = yolo_oku(self._txt_oku(self._txt(yol)), self.W, self.H)
        proj = (projeksiyon_kutusu(self.tel.get(os.path.basename(yol)),
                                   self.marj_x, self.marj_y) if self.oto else None)
        self.aktif_tutamac = None                # yeni karede secim temiz
        self.roll = hedef_roll(self.tel.get(os.path.basename(yol))) if self.oto else None
        self.supheli = (self.roll is not None and self.roll >= self.roll_esik)
        if var is not None:
            self.kutu, self.dokunuldu, self.kaynak = var, True, "KAYITLI"
        elif proj is not None:
            self.kutu, self.dokunuldu, self.kaynak = proj, False, "OTO"
        elif self.son_kutu is not None:
            self.kutu = kutu_kirp(list(self.son_kutu), self.W, self.H)
            self.dokunuldu, self.kaynak = False, "TASINAN"
        else:
            self.kutu = orta_kutu(self.W, self.H)
            self.dokunuldu, self.kaynak = False, "ORTA"
        if self.oto_yakin:
            self.odakla(ciz=False)
        else:
            self.sigdir_zoom(ciz=False)
        self.ciz()
        self.guncelle_durum()

    @staticmethod
    def _txt_oku(yol):
        try:
            with open(yol, encoding="utf-8") as f:
                return f.readline()
        except OSError:
            return ""

    # ------------------------------------------------------------ koordinat
    def t2g(self, cx, cy):
        """tuval -> goruntu pikseli"""
        return ((cx - self.ox) / self.zoom, (cy - self.oy) / self.zoom)

    def g2t(self, mx, my):
        """goruntu -> tuval"""
        return (mx * self.zoom + self.ox, my * self.zoom + self.oy)

    def sigdir_zoom(self, ciz=True):
        tw = max(self.tuval.winfo_width(), 50)
        th = max(self.tuval.winfo_height(), 50)
        self.zoom = min(tw / float(self.W), th / float(self.H))
        self.ox = (tw - self.W * self.zoom) / 2.0
        self.oy = (th - self.H * self.zoom) / 2.0
        if ciz:
            self.ciz()

    def odakla(self, ciz=True):
        """Kutuya OTOMATIK YAKINLAS: kutunun uzun kenari tuvalin ~%30'unu kaplasin,
        merkezi ortada. 12-24 px'lik uzak hedefi tam kadrajda gozle secmek imkansiz;
        her karede elle zoom yapmak 5000 karede kabul edilemez. Zoom, TAM SIGDIRMA
        ile 20x arasina kirpilir (kucuk kutuda sonsuza gitmesin)."""
        if self.kutu is None or self.img is None:
            return self.sigdir_zoom(ciz=ciz)
        tw = max(self.tuval.winfo_width(), 50)
        th = max(self.tuval.winfo_height(), 50)
        k = kutu_kirp(self.kutu, self.W, self.H)
        uzun = max(k[2] - k[0], k[3] - k[1], 1.0)
        tam = min(tw / float(self.W), th / float(self.H))     # taban: tum kare
        self.zoom = max(tam, min(0.30 * min(tw, th) / uzun, 20.0))
        mx, my = (k[0] + k[2]) / 2.0, (k[1] + k[3]) / 2.0
        self.ox = tw / 2.0 - mx * self.zoom
        self.oy = th / 2.0 - my * self.zoom
        if ciz:
            self.ciz()

    def oto_yakin_degistir(self):
        self.oto_yakin = not self.oto_yakin
        self.lbl_yeni.config(text="oto yakinlasma: %s"
                             % ("ACIK" if self.oto_yakin else "KAPALI"))
        self.kok.after(1500, lambda: self.lbl_yeni.config(text=""))
        if self.oto_yakin:
            self.odakla()

    def zoomla(self, k):
        tw = self.tuval.winfo_width() / 2.0
        th = self.tuval.winfo_height() / 2.0
        mx, my = self.t2g(tw, th)
        self.zoom = max(0.05, min(self.zoom * k, 40.0))
        self.ox = tw - mx * self.zoom
        self.oy = th - my * self.zoom
        self.ciz()

    def tekerlek(self, e):
        k = 1.2 if e.delta > 0 else 1 / 1.2
        mx, my = self.t2g(e.x, e.y)
        self.zoom = max(0.05, min(self.zoom * k, 40.0))
        self.ox = e.x - mx * self.zoom
        self.oy = e.y - my * self.zoom
        self.ciz()

    def pan_basla(self, e):
        self.pan = (e.x, e.y, self.ox, self.oy)

    def pan_suru(self, e):
        if self.pan:
            x0, y0, ox, oy = self.pan
            self.ox = ox + (e.x - x0)
            self.oy = oy + (e.y - y0)
            self.ciz()

    # --------------------------------------------------------------- cizim
    def ciz(self):
        self.tuval.delete("all")
        if self.img is None:
            self.tuval.create_text(
                self.tuval.winfo_width() / 2, self.tuval.winfo_height() / 2,
                text="Kare bekleniyor...\nYakalama basladiginda buraya dusecek.",
                fill="#8b93a1", font=("Consolas", 14), justify="center")
            return
        # ---- SADECE GORUNEN BOLGEYI olcekle ----------------------------------
        # ONCEDEN tum goruntu buyutuluyordu: 20x zoom'da 1920x1080 -> 38400x21600
        # = 830 milyon piksel. Bellek/CPU patliyor, arayuz DONUYOR ve yarim
        # cizilen kare "bozulmus" gorunuyordu. Artik yalnizca tuvale dusen parca
        # kirpilip olcekleniyor -> maliyet zoom'dan BAGIMSIZ, tuval boyutu kadar.
        tw = max(self.tuval.winfo_width(), 1)
        th = max(self.tuval.winfo_height(), 1)
        ix0 = max(0, int((0 - self.ox) / self.zoom))
        iy0 = max(0, int((0 - self.oy) / self.zoom))
        ix1 = min(self.W, int((tw - self.ox) / self.zoom) + 2)
        iy1 = min(self.H, int((th - self.oy) / self.zoom) + 2)
        if ix1 <= ix0 or iy1 <= iy0:
            return                                   # goruntu tuvalin disinda
        dw = max(int((ix1 - ix0) * self.zoom), 1)
        dh = max(int((iy1 - iy0) * self.zoom), 1)
        # Yakinlasirken NEAREST: gercek pikselleri gosterir (100 px'lik hedefin
        # kenarini bulanikliktan degil pikselden secersin). Uzaklasirken BILINEAR.
        yontem = Image.NEAREST if self.zoom >= 1.5 else Image.BILINEAR
        try:
            parca = self.img.crop((ix0, iy0, ix1, iy1)).resize((dw, dh), yontem)
            self.tk_img = ImageTk.PhotoImage(parca)
        except Exception:
            return
        self.tuval.create_image(self.ox + ix0 * self.zoom,
                                self.oy + iy0 * self.zoom,
                                anchor="nw", image=self.tk_img)
        if self.kutu is None:
            return
        # DOKUNULMADI uyarisi: kutu onceki kareden TASINDI ve bu karede el degmedi.
        # Dalginlikla basilan Enter "makul gorunen ama yanlis" etiket uretir; boyle
        # bir etiketi sonradan gozle ayiklamak cok pahali. Kaydi ENGELLEMEZ (akis
        # kesilmesin), sadece renk degistirip uyarir.
        # Supheli (yuksek banka) OTO kutusu KIRMIZI: "onaylamadan once BAK".
        if self.kaynak == "OTO" and self.supheli and not self.dokunuldu:
            renk = "#ff4d6d"
        elif self.dokunuldu:
            renk = "#00ff88"
        else:
            renk = "#22d3ee" if self.kaynak == "OTO" else "#ffb454"
        x1, y1 = self.g2t(self.kutu[0], self.kutu[1])
        x2, y2 = self.g2t(self.kutu[2], self.kutu[3])
        self.tuval.create_rectangle(x1, y1, x2, y2, outline=renk, width=2)
        for j, (sx, sy) in enumerate(self._tutamaclar()):
            if j == self.aktif_tutamac:      # secili tutamac: buyuk + beyaz cerceve
                self.tuval.create_rectangle(sx - 7, sy - 7, sx + 7, sy + 7,
                                            fill="#ffd166", outline="#ffffff", width=2)
            else:
                self.tuval.create_rectangle(sx - 4, sy - 4, sx + 4, sy + 4,
                                            fill=renk, outline="")
        k = kutu_kirp(self.kutu, self.W, self.H)
        etiket = "%dx%d px" % (int(k[2] - k[0]), int(k[3] - k[1]))
        if not self.dokunuldu:
            if self.kaynak == "OTO" and self.supheli:
                etiket += "   OTO ama HEDEF BANKADA (%.0f) - KONTROL ET" % self.roll
            elif self.kaynak == "OTO":
                etiket += "   OTO (truth) - ENTER ile onayla"
            else:
                etiket += "   DOKUNULMADI"
        self.tuval.create_text(x1 + 2, y1 - 12, anchor="w", fill=renk,
                               font=("Consolas", 10), text=etiket)

    def _tutamaclar(self):
        """8 tutamacin TUVAL koordinati (4 kose + 4 kenar ortasi)."""
        x1, y1 = self.g2t(self.kutu[0], self.kutu[1])
        x2, y2 = self.g2t(self.kutu[2], self.kutu[3])
        mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        return [(x1, y1), (x2, y1), (x1, y2), (x2, y2),
                (mx, y1), (mx, y2), (x1, my), (x2, my)]

    # ------------------------------------------------------------- fare
    def tik(self, e):
        if self.img is None:
            return
        self.kok.focus_set()
        if self.kutu is not None:
            for i, (sx, sy) in enumerate(self._tutamaclar()):
                if abs(e.x - sx) <= TUTAMAC and abs(e.y - sy) <= TUTAMAC:
                    self.surukle = ("tutamac", i)
                    return
            x1, y1 = self.g2t(self.kutu[0], self.kutu[1])
            x2, y2 = self.g2t(self.kutu[2], self.kutu[3])
            if x1 <= e.x <= x2 and y1 <= e.y <= y2:
                gx, gy = self.t2g(e.x, e.y)
                self.surukle = ("tasi", gx, gy, list(self.kutu))
                return
        gx, gy = self.t2g(e.x, e.y)
        self.surukle = ("yeni", gx, gy)
        self.kutu = [gx, gy, gx, gy]

    def sag_tik(self, e):
        """Sag tus: nereye basilirsa basilsin SIFIRDAN kutu cizmeye basla."""
        if self.img is None:
            return
        self.kok.focus_set()
        gx, gy = self.t2g(e.x, e.y)
        self.surukle = ("yeni", gx, gy)
        self.kutu = [gx, gy, gx, gy]
        self.dokunuldu = True
        self.ciz()

    def suru(self, e):
        if not self.surukle or self.img is None:
            return
        self.dokunuldu = True
        gx, gy = self.t2g(e.x, e.y)
        tur = self.surukle[0]
        if tur == "yeni":
            self.kutu = [self.surukle[1], self.surukle[2], gx, gy]
        elif tur == "tasi":
            _, bx, by, ilk = self.surukle
            self.kutu = kutu_tasi(list(ilk), gx - bx, gy - by, self.W, self.H)
        else:
            i = self.surukle[1]
            x1, y1, x2, y2 = self.kutu
            if i in (0, 2, 6):
                x1 = gx
            if i in (1, 3, 7):
                x2 = gx
            if i in (0, 1, 4):
                y1 = gy
            if i in (2, 3, 5):
                y2 = gy
            self.kutu = [x1, y1, x2, y2]
        self.ciz()

    def birak(self, e):
        if self.surukle:
            self.kutu = kutu_kirp(self.kutu, self.W, self.H)
            self.surukle = None
            self.ciz()

    # -------------------------------------------------------------- eylemler
    def kaydet_sonraki(self):
        if self.img is None or not self.kareler:
            return
        if not kutu_gecerli(self.kutu, self.W, self.H):
            self.lbl_yeni.config(text="kutu cok kucuk — kaydedilmedi")
            self.kok.after(2000, lambda: self.lbl_yeni.config(text=""))
            return
        k = kutu_kirp(self.kutu, self.W, self.H)
        try:
            guvenli_yaz(self._txt(self.kareler[self.idx]),
                        yolo_satiri(k, self.W, self.H) + "\n")
        except Exception as e:
            # KAYIT TUTMADI -> sonraki kareye GECME, kullaniciya GORUNUR soyle.
            self.lbl_yeni.config(text="!! KAYIT BASARISIZ: %s" % (e,),
                                 fg="#ff5555")
            print("[ETIKET] KAYIT BASARISIZ %s: %r"
                  % (self._txt(self.kareler[self.idx]), e))
            return
        self.son_kutu = list(k)            # sonraki karede hazir gelsin
        self.aktif_tutamac = None          # sonraki kare temiz baslasin
        self.git(self.idx + 1, gezinme=False)

    def etiketi_sil(self):
        if not self.kareler:
            return
        try:
            guvenli_yaz(self._txt(self.kareler[self.idx]), "")   # BOS = negatif
        except Exception as e:
            self.lbl_yeni.config(text="!! SILME BASARISIZ: %s" % (e,),
                                 fg="#ff5555")
            print("[ETIKET] SILME BASARISIZ: %r" % (e,))
            return
        self.guncelle_durum()

    def kareyi_sil(self):
        """Shift+Delete: kare + etiketi `_silinen/` altina TASI, sonrakine gec."""
        if not self.kareler:
            return "break"
        import shutil
        png = self.kareler[self.idx]
        txt = self._txt(png)
        hp, ht = silme_hedefi(png, self.klasor)
        os.makedirs(os.path.dirname(hp), exist_ok=True)
        try:
            shutil.move(png, hp)
            if os.path.exists(txt):
                shutil.move(txt, ht)
        except Exception as e:
            self.lbl_yeni.config(text="silinemedi: %r" % e)
            return "break"
        self._son_silinen = (png, txt, hp, ht)
        self.kareler.pop(self.idx)
        self.lbl_yeni.config(text="SILINDI: %s  (Ctrl+Z geri alir)"
                             % os.path.basename(png))
        self.kok.after(4000, lambda: self.lbl_yeni.config(text=""))
        if not self.kareler:
            self.img = None; self.kutu = None; self.ciz(); self.guncelle_durum()
            return "break"
        self.yukle(min(self.idx, len(self.kareler) - 1))
        return "break"

    def silmeyi_geri_al(self):
        """Ctrl+Z: son silinen kareyi yerine koy ve ona git."""
        if not self._son_silinen:
            self.lbl_yeni.config(text="geri alinacak silme yok")
            self.kok.after(2000, lambda: self.lbl_yeni.config(text=""))
            return "break"
        import shutil
        png, txt, hp, ht = self._son_silinen
        try:
            shutil.move(hp, png)
            if os.path.exists(ht):
                shutil.move(ht, txt)
        except Exception as e:
            self.lbl_yeni.config(text="geri alinamadi: %r" % e)
            return "break"
        self._son_silinen = None
        self._tara()
        try:
            self.yukle(self.kareler.index(png))
        except ValueError:
            pass
        self.lbl_yeni.config(text="GERI ALINDI: %s" % os.path.basename(png))
        self.kok.after(3000, lambda: self.lbl_yeni.config(text=""))
        return "break"

    def git(self, i, gezinme=True):
        if not self.kareler:
            return
        if gezinme:
            import time as _t
            simdi = _t.perf_counter()
            if not gezinme_kabul(simdi, self._son_gezinme):
                return                      # tus tekrari: bu olayi YUT
            self._son_gezinme = simdi
        if i >= len(self.kareler):
            self._tara()                    # sona geldiysek yeni kare gelmis mi
            i = min(i, len(self.kareler) - 1)
        self.yukle(i)

    def etiketsize_atla(self):
        """Tab: SIRAYLA ILERI giderek goz gerektiren ilk kareye atla
        (bos etiket VEYA hedef bankada). Bkz. sonraki_dikkat()."""
        if not self.kareler:
            return "break"
        bayrak = [etiketli_mi(self._txt(p)) for p in self.kareler]
        rolls = [hedef_roll(self.tel.get(os.path.basename(p))) if self.oto else None
                 for p in self.kareler]
        i = sonraki_dikkat(bayrak, rolls, self.idx, self.roll_esik)
        if i is None:
            self.lbl_yeni.config(text="dikkat gerektiren kare YOK")
            self.kok.after(2000, lambda: self.lbl_yeni.config(text=""))
        else:
            self.yukle(i)
        return "break"                      # Tab'in odak gezdirmesini engelle

    def tutamac_sec(self, i):
        """8 tutamactan birini sec/birak. Secili tutamac ok tuslariyla itilir."""
        if self.kutu is None:
            return "break"
        self.aktif_tutamac = None if self.aktif_tutamac == i else i
        self.ciz(); self.guncelle_durum()
        return "break"

    def ok_tusu(self, dx, dy):
        """Tutamac seciliyse ONU it; degilse KARE gezin (eski davranis)."""
        if self.aktif_tutamac is not None and self.kutu is not None:
            self.kutu = tutamac_tasi(self.kutu, self.aktif_tutamac, dx, dy,
                                     self.W, self.H)
            self.dokunuldu = True
            self.ciz()
        else:
            self.git(self.idx + (1 if dx > 0 or dy > 0 else -1))
        return "break"

    def itele(self, dx, dy):
        """Kutuyu piksel piksel it (Yukari/Asagi, Shift+Sol/Sag). Uzak
        hedefte fareyle 1-2 px duzeltmek zor; klavye kesin."""
        if self.kutu is None or self.img is None:
            return
        self.kutu = kutu_tasi(list(self.kutu), dx, dy, self.W, self.H)
        self.dokunuldu = True
        self.ciz()

    def ortala(self):
        if self.img is not None:
            self.kutu = orta_kutu(self.W, self.H)
            self.dokunuldu = True
            self.ciz()

    def sigdir(self):
        if self.kutu is not None:
            self.kutu = kutu_kirp(self.kutu, self.W, self.H)
            self.ciz()


def main(argv=None):
    ap = argparse.ArgumentParser(description="Canli bbox etiketleyici")
    ap.add_argument("--klasor", required=True, help="yakalama klasoru")
    ap.add_argument("--etiket-klasor", default=None,
                    help="etiketler AYRI klasordeyse (images/ + labels/ duzeni). "
                         "Verilmezse .txt PNG'nin yaninda aranir/yazilir.")
    ap.add_argument("--ad", default="talon1", help="dosya on eki (vars: talon1)")
    ap.add_argument("--hedef", type=int, default=5000, help="hedef etiket adedi")
    ap.add_argument("--oto", dest="oto", action="store_true", default=True,
                    help="kutuyu truth projeksiyonundan ON-DOLDUR (VARSAYILAN)")
    ap.add_argument("--elle", dest="oto", action="store_false",
                    help="on-doldurmayi KAPAT (her kutu elle)")
    ap.add_argument("--marj-x", type=float, default=0.07)
    ap.add_argument("--marj-y", type=float, default=0.10)
    ap.add_argument("--basla", type=int, default=0,
                    help="hangi kareden acilsin: DOSYA NUMARASI (534 -> "
                         "talon1_0534). 0 = ilk ETIKETSIZ kareden.")
    ap.add_argument("--roll-esik", type=float, default=20.0,
                    help="hedef |banka| bunun ustundeyse kutu SUPHELI "
                         "isaretlenir (olculen kirilma: 20 derece)")
    args = ap.parse_args(argv)
    os.makedirs(args.klasor, exist_ok=True)
    if args.etiket_klasor:
        os.makedirs(args.etiket_klasor, exist_ok=True)

    kok = tk.Tk()
    kok.geometry("1500x900")
    BBoxEtiketleyici(kok, args.klasor, args.ad, args.hedef,
                     oto=args.oto, marj_x=args.marj_x, marj_y=args.marj_y,
                     roll_esik=args.roll_esik, basla=args.basla,
                     etiket_klasor=args.etiket_klasor)
    kok.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())

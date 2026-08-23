# -*- coding: utf-8 -*-
"""
================================================================================
 TESPIT AKISI — DoW dedektor ciktisini yasanin bekledigi `wait_pose`e cevirir
================================================================================
Gazebo yasasi (bbox_ibvs / supervisor) tespitleri SU SOZLESMEYLE tuketiyor:

    wait_pose(son_seq, timeout) -> {"seq": int, "pose": kayit | None}   ya da None
        kayit: {"conf": float, "cx","cy","w","h": px}   (tam-kare piksel)

    * seq        her YENI karede artan sayac. Cagiran son gordugu seq'i verir;
                 daha yenisi gelene KADAR bloklanir (yeni kare = yeni karar).
    * pose=None  kare geldi ama gecerli kutu YOK (tespit basarisiz).
                 -> yasa bunu "kayip kare" sayar, KAYIP_M'e dogru sayar.
    * None       `timeout` boyunca HIC yeni kare gelmedi (akis durdu).
                 -> yasa bunu da kayip sayar.

BIZDE tespit `web/server.py`'nin dedektor thread'inde uretiliyor ve beyne
`set_gorsel_tespit` ile veriliyor. Bu modul araya girmez; server her tespitte
`TespitAkisi.yaz(...)` cagirir, yasa da `bekle(...)` ile okur. Tek yonlu, kilitli,
kopyalayan bir kuyruk -- yasa ile dedektor birbirini bloklamaz.

--------------------------------------------------------------------------------
 ⛔ KURAL: BURADAN GPS GECMEZ
--------------------------------------------------------------------------------
Yazilan kayitta YALNIZ kamera olcumleri vardir (cx, cy, w, h, conf). Hedef
konumu/hizi, menzil, truth -- HICBIRI gecmez. Gorsel fazin GPS'e erisimi
yapisal olarak imkansiz kalir (bkz. run_bbox_ibvs imzasi: get_plane YOK).
Birim test bunu kilitler: `test_kural_yalniz_kamera_alanlari`.

--------------------------------------------------------------------------------
 ⚠ KARE HIZI FARKI (olculdu, kullanici karari: esikler AYNEN kalacak)
--------------------------------------------------------------------------------
Yasa ~30 Hz tespit akisi varsayarak KARE SAYISI cinsinden esik kullaniyor:

    KILIT_N=10 / pencere 15   Gazebo'da 0.50 s
    KAYIP_M=20                Gazebo'da 0.66 s

Bizim dedektor canli ~8-9 FPS (olculdu: DET ~100 ms, oyun GPU'yu paylasiyor).
Ayni sayilar bizde:

    kilit penceresi   ~1.7 s
    kayip esigi       ~2.2 s

Yani devir GEC olur, kayip GEC algilanir. Sayilara DOKUNULMADI (kullanici
karari); `olcum()` bunu canli raporlar ki etkisi sayiyla gorunsun.
================================================================================
"""
import math
import os
import threading
import time

# ══ KAMERA CERCEVESI CEVIRISI (2026-08-10) ═════════════════════════════════
# ⛔ BULUNAN HATA: yasa (bbox_ibvs) piksel koordinatlarini GAZEBO iris
# kamerasinin modeliyle yorumluyor -- vision/geometry.py: 640x480, CX=320,
# CY=240, FX=FY=166.6. Bizim dedektor ise DoW karesini 1920x1080 TAM PIKSEL
# veriyor. Ceviri yazilmadigi icin kadrajin TAM MERKEZINDEKI hedef icin yasa
#     eps_yaw  = atan((960-320)/166.6) = +75.4 deg
#     eps_elev = atan((540-301)/166.6) = +55.1 deg
# hesapliyordu (dogrusu ~0) -> gorsel faz acilir acilmaz tavandan yaw kirip
# hedefi kadrajdan atardi. Hibrit hic ucurulmadigi icin gizli kalmisti.
#
# ⚙ DOGRU CEVIRI: piksel degil ACI korunur. Once DoW piksellerinden kamera
# cercevesi teget'i cikarilir, sonra yasanin ince-kamera modeliyle YENIDEN
# piksellenir:
#       t_x = (cx_dow - W/2) / fx_dow ,  fx_dow = (W/2)/tan(HFOV_DOW/2)
#       cx_yasa = geo.CX + geo.FX * t_x           (cy icin FY/CY ile ayni)
#       w_yasa  = w_dow * geo.FX / fx_dow         (acisal boyut korunur)
# W/H her kareden okunur -> cozunurluk degisirse kendiliginden uyar.
#
# 📐 HFOV_DOW OLCULDU (2026-08-10, tahmin DEGIL): talon_pozitif oturumunun
# 4992 karesinde Talon'un 6 keypoint'i truth pozundan projekte edilip ELLE
# CIZILMIS kutularla IoU kiyaslandi; HFOV 60..150 tarandi. Tepe kesin:
#     60 deg -> IoU 0.007 | 125 deg -> 0.584 | 150 deg -> 0.030
#     ince tarama (HFOV x tilt): EN IYI 119.0 deg / tilt 26.0 -> IoU 0.624
# Modulde yazan 125/25 ("kullanici teyidi") IoU 0.584 -- olculen 119 biraz
# daha iyi. Fark fx'te %13; kapali cevrimde zararsiz ama olculeni kullaniyoruz.
# AVCI_DOW_HFOV ile degistirilebilir.
# ── 2026-08-14 DUZELTME: 119.0 -> 122.0709 ────────────────────────────────
# Yukaridaki 119.0, ELLE CIZILMIS kutularla IoU taramasindan tahmin edilmisti
# (60..150 tarandi, tepe 119). Ama bu deger artik OLCULEBILIR: veri seti
# calismasinda UE4SS modu her karede motorun KENDI POV'unu JSON'a yaziyor:
#       "camera_fov": 122.0709        (7000+ karede sabit)
# Ayrica ayni JSON'lardaki 3B->2B motor projeksiyonlarindan en kucuk kareler
# ile ic parametreler cozuldu:  fx = fy = 531.36, cx = 960, cy = 540
#       artik (residual) = 0.001 px   -> tahmin degil, motorun kendi degeri.
# Kontrol:  (1920/2) / tan(122.0709/2) = 531.36  ->  cozumle BIREBIR.
#
# 119.0'in bedeli:  fx = 565.48  (%6.4 buyuk) -> yasa hedefi oldugundan
# MERKEZE DAHA YAKIN saniyor:
#       merkezden 200 px -> gercek 20.6 deg, yasa 19.5 deg  (1.1 deg eksik)
#       merkezden 600 px -> gercek 48.5 deg, yasa 46.7 deg  (1.8 deg eksik)
# Yani her karede EKSIK duzeltme -> hedef yavasca kenara kayar -> kadraj disi.
# IoU taramasinin 119'da tepe yapmasi sasirtici degil: o tarama tilt ile
# birlikte optimize ediliyordu, iki hata birbirini kismen telafi etmisti.
# Geri almak icin: AVCI_DOW_HFOV=119 ortam degiskeni (yedek: *.yedek_*).
HFOV_DOW_DEG = float(os.environ.get("AVCI_DOW_HFOV", "122.0709"))


def _yasa_icsellik():
    """Yasanin kamera icsellikleri (CX, CY, FX, FY). Import basarisizsa
    Gazebo SDF varsayilanlari -- sessiz yanlis olmaktansa bilinen deger."""
    try:
        from vision import geometry as geo
        return float(geo.CX), float(geo.CY), float(geo.FX), float(geo.FY)
    except Exception:
        return 320.0, 240.0, 166.6, 166.6


def dow_pikseli_yasaya(cx, cy, w, h, W, H, hfov_deg=None):
    """DoW tam-kare pikseli -> yasanin kamera cercevesi pikseli (aci korunur).

    W/H gecersizse (0/None) ceviri YAPILMAZ, girdi aynen doner -- boyle bir
    karede yanlis olceklemektense yasanin kendi kapilarina birakmak yeglenir.
    """
    if not W or not H or W <= 0 or H <= 0:
        return cx, cy, w, h
    CX, CY, FX, FY = _yasa_icsellik()
    hf = HFOV_DOW_DEG if hfov_deg is None else float(hfov_deg)
    fx_dow = (W / 2.0) / math.tan(math.radians(hf) / 2.0)   # kare piksel: fy=fx
    if fx_dow <= 0:
        return cx, cy, w, h
    # ══ YATAY AYNA (2026-08-17) — GORSEL GUDUMUN KOK NEDENI ══════════════
    # dow_kopru.py:49-53 dunyayi AYNALIYOR:  NED_y = -DoW_y,  yaw_NED = -yaw_DoW.
    # Konum, hiz ve yaw BIRLIKTE aynalanip ned_yaw_to_dow ile geri cevrildigi
    # icin GPS hatti kendi icinde tutarli. Ama KAMERA aynalanmiyordu:
    # eps_yaw = atan((cx-CX)/FX) fiziksel SAG-pozitif bir govde acisi; aynali
    # dunyada hedefin dogru bagil kerterizi -eps'tir. Yasa ise
    #     yaw_cmd = iris_yaw + K_YAW * eps_yaw        (bbox_ibvs.py)
    # yaziyordu -> her karede burun 2*eps TERS tarafa suruluyordu.
    #
    # OLCULDU (iki bagimsiz olcum, gercek ucus kayitlari):
    #   eps -> 0.5 s sonraki yaw degisimi: egim -0.863 / -0.902,
    #          ayni isaret yalniz %10.2 / %8.6  -> burun hedeften KACIYOR
    #   |d_yaw - yaw_cmd| medyan 107.6°  vs  |d_yaw + yaw_cmd| medyan 10.2°
    #          -> aynalama imzasi tartismasiz
    #   Sonuc: |eps| faz boyunca buyuyor (10° -> 45.8°), hedef 1.91 s'de
    #          kadrajdan cikiyor, komut karelerinin %62.7'si hayalet oluyor.
    #
    # ⚠ AYNA PIKSELDE YAPILIR, ACIDA DEGIL: los_seviye()'nin roll telafisi
    #    zaten aynalanmis roll'u kullaniyor; ikisi birlikte aynalanip dogru
    #    seviye azimutunu verir. Yukselis (cy) kanali DEGISMEZ.
    # ⚠ Bu, bu depodaki NED/oyun-dunyasi ayna hatasinin UCUNCU tekrari.
    # ⚠ Yamadan sonra dogrulama betiklerinde beklenen bagintı
    #    "d_yaw + eps" DEGIL "d_yaw - eps" olur.
    return (CX - FX * (cx - W / 2.0) / fx_dow,
            CY + FY * (cy - H / 2.0) / fx_dow,
            w * FX / fx_dow,
            h * FY / fx_dow)


class TespitAkisi:
    """Dedektor -> yasa arasi tek yonlu kare akisi (thread-guvenli)."""

    def __init__(self):
        self._kilit = threading.Condition()
        self._seq = 0
        self._kayit = None          # son kare icin {"conf","cx","cy","w","h"} | None
        self._t = 0.0               # son karenin damgasi (perf_counter)
        # olcum sayaclari (salt gozlem; gudume girmez)
        self.toplam = 0
        self.kutulu = 0
        # kadraj gozlemi (SALT GOZLEM; yasaya giden kayda girmez)
        self.son_ex = self.son_ey = 0.0
        self._ex_top = self._ey_top = 0.0
        self.kenar = 0
        self._ilk_t = None
        self._son_t = None

    # ------------------------------------------------------------------ yazma
    def yaz(self, det, simdi=None):
        """Dedektor her KAREDE bir kez cagirir.

        det: {"cx","cy","w","h","conf", ...} | None
             None = kare islendi ama gecerli kutu yok (tespit basarisiz).
        ⛔ det icindeki BASKA alanlar (track_id, t, W, H...) TASINMAZ --
        yasaya yalnizca kamera olcumu gider.
        """
        simdi = time.perf_counter() if simdi is None else simdi
        kayit = None
        if det is not None:
            try:
                # W/H CEVIRI ICIN okunur, yasaya GECMEZ (D0 sozlesmesi: kayitta
                # yalniz conf/cx/cy/w/h var). Ceviri olmadan yasa DoW pikselini
                # Gazebo icsellikleriyle okuyup hedefi kadrajdan atiyordu.
                cx, cy = float(det["cx"]), float(det["cy"])
                w, h = float(det.get("w", 0.0)), float(det.get("h", 0.0))
                cx, cy, w, h = dow_pikseli_yasaya(
                    cx, cy, w, h, float(det.get("W", 0.0)), float(det.get("H", 0.0)))
                kayit = {"conf": float(det.get("conf", 0.0)),
                         "cx": cx, "cy": cy, "w": w, "h": h}
            except (KeyError, TypeError, ValueError):
                kayit = None          # bozuk kayit = kutusuz kare (sessizce yutma)
        with self._kilit:
            self._seq += 1
            self._kayit = kayit
            self._t = simdi
            self.toplam += 1
            if kayit is not None:
                self.kutulu += 1
                # KADRAJ GOZLEMI (2026-08-10): hibritte eski IBVS yolu devre disi
                # oldugundan ucus logunun vis_ex/vis_ey kolonlari BOS kaliyor ->
                # "hedef gorsel fazda kadrajda kaliyor mu" sorusu olculemez hale
                # gelmisti. Burada yasanin kendi cercevesinde normalize sapma
                # tutulur (SALT GOZLEM; yasaya giden kayit DEGISMEZ).
                CX, CY, FX, FY = _yasa_icsellik()
                self.son_ex = (kayit["cx"] - CX) / FX      # tan(yatay aci)
                self.son_ey = (kayit["cy"] - CY) / FY      # tan(dikey aci)
                self._ex_top += abs(self.son_ex)
                self._ey_top += abs(self.son_ey)
                if abs(self.son_ex) > 0.7 or abs(self.son_ey) > 0.7:
                    self.kenar += 1
            if self._ilk_t is None:
                self._ilk_t = simdi
            self._son_t = simdi
            self._kilit.notify_all()

    # ------------------------------------------------------------------ okuma
    def bekle(self, son_seq, timeout=0.5):
        """Yasanin `wait_pose`u. son_seq'ten YENI bir kare gelene kadar bekler.

        -> {"seq": n, "pose": kayit | None}   yeni kare geldi
        -> None                                timeout doldu, kare gelmedi
        """
        bitis = time.perf_counter() + float(timeout)
        with self._kilit:
            while self._seq <= son_seq:
                kalan = bitis - time.perf_counter()
                if kalan <= 0:
                    return None
                self._kilit.wait(kalan)
            # "t" = karenin AKISA GIRIS damgasi (perf_counter). Yasa bunu
            # iris_yaw'i ayni ana hizalamak icin kullanir; olmazsa piksel
            # acisi GECMISTEKI kareye, yaw ise SIMDIKI ana ait olur ve fark
            # dogrudan sahte LOS hizi uretir (bkz. bbox_ibvs YAW_HIZALA_S).
            return {"seq": self._seq, "pose": self._kayit, "t": self._t}

    # ------------------------------------------------------------------ olcum
    def olcum(self):
        """Salt gozlem: akisin gercek hizi ve tespit orani.

        Yasanin kare-sayisi esikleri bu hiza gore SURE karsiligi kazanir --
        rapor bunu gorunur kilar (30 Hz varsayimi bizde tutmuyor)."""
        with self._kilit:
            n, k = self.toplam, self.kutulu
            t0, t1 = self._ilk_t, self._son_t
        sure = (t1 - t0) if (t0 is not None and t1 is not None) else 0.0
        hz = (n - 1) / sure if (sure > 0 and n > 1) else 0.0
        return {"kare": n, "kutulu": k,
                "tespit_orani": (k / n) if n else 0.0,
                "hz": hz,
                "kilit_penceresi_s": (15.0 / hz) if hz > 0 else None,
                "kayip_esigi_s": (20.0 / hz) if hz > 0 else None,
                # KADRAJ: hedef merkezde mi kenarda mi (gorsel faz teshisi)
                "ex": self.son_ex, "ey": self.son_ey,
                "ex_ort": (self._ex_top / k) if k else 0.0,
                "ey_ort": (self._ey_top / k) if k else 0.0,
                "kenar_orani": (self.kenar / k) if k else 0.0}

    def sifirla(self):
        """Yeni gorev: sayaclar ve seq bastan (bayat kare devrilmesin)."""
        with self._kilit:
            self._seq = 0
            self._kayit = None
            self.toplam = self.kutulu = 0
            self.son_ex = self.son_ey = 0.0
            self._ex_top = self._ey_top = 0.0
            self.kenar = 0
            self._ilk_t = self._son_t = None
            self._kilit.notify_all()

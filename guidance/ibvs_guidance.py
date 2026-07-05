# -*- coding: utf-8 -*-
"""
HAMIDIYE - GORSEL GUDUM (DUZ IBVS: image-based visual servoing)
================================================================================
Gorsel temas sonrasi YONELIM komutu YALNIZCA kameradan uretilir (yarisma kurali:
bu asamada GPS yonelimi KULLANILMAZ). Tek hata sinyali: best.pt bbox MERKEZININ
goruntu merkezinden sapmasi. PnP / derinlik / poz / ROLL YOK (roll=0; sonraki asama).

Goruntu ekseni: sol-ust orijin, x -> SAGA, y -> ASAGI.
  ex = (cx - W/2) / (W/2)   [-1..1]  (+ = hedef SAGDA)
  ey = (cy - H/2) / (H/2)   [-1..1]  (+ = hedef ALTTA)

EKSEN ESLEME (SDK fizigi ile TUTARLI):
  SDK'da  pitch/roll = YATAY ivme (ileri/sag),  throttle = DIKEY hiz (tirman/alc).
  Kullanicinin niyeti "hedefi ortala + yaklas". Fizige gore dogru eslesme:
    yaw      <- ex            : hedefi YATAYDA ortala (burnu/govdeyi dondur)
    throttle <- (ey - EY_REF) : hedefi DIKEY REFERANSTA tut. SDK v2.2: kamera 25
                                derece YUKARI tilt'li -> ayni irtifadaki hedef
                                merkezin ALTINDA gorunur; referans cizgisi
                                (VIS_EY_REF~0.43) o noktadir. Tam merkeze ortalamak
                                drone'u hedefin ALTINA oturturdu (tilt telafisi).
                                DIKEY ASIMETRIK YASA (2026-07-05 v2): goruntu
                                hatasi once ISTENEN DIKEY HIZA cevrilir (VIS_VZ_MAX
                                tavanli). TIRMANISTA thr = vz_des/VZ_MAX feedforward
                                (SDK thr>0 zaten hiz komutu, sim donguyu kapatir);
                                INISTE thr = vz-hatasi P'si UST KLEMP 0.0 ile (fren
                                = yercekimi telafisini geri ac; iniste ASLA tirmanis
                                komutu yok). v1'in simetrik P'si asimetrik plantta
                                limit cevrimiyle NET TIRMANIS yaratti (log kaniti).
    pitch    <- ILERI         : yatay hizali + hedef COK YUKARIDA degilse YAKLAS
                                (koordineli dalis; bbox buyudukce yavasla)
    roll     <- ex (istege)   : ceviklik (kullanici spec'i); VIS_K_ROLL=0 default KAPALI
  (Kullanici spec'inde pitch<-ey yaziyordu; SDK'da pitch=YATAY oldugundan dikey
   ortalama throttle'a takaslandi. SIGN_* + canli tune ile dogrulanir.)

Rate-limit BURADA yapilmaz; AvciKontrol._send() zaten yapar (komut surekliligi).
Parametreler (SIGN_*, K_*, ...) disaridan `p` (Cfg) ile gelir; kendi dikey hiz `vz`
(cm/s, +yukari; SDK drone telemetrisi TEMIZ) cagirandan parametre gelir -> canli
tune bedava, dongusel import yok (bu dosya ana_kontrol'u/SDK'yi import ETMEZ).

Ek: KilitlenmeTakip — sartname KILITLENME olcumu (asagida). IBVS'ten bagimsiz
GOZLEMCIDIR: komut uretmez, sadece "bbox vurus alaninda ve yeterince buyuk mu,
ne kadar suredir?" sayar. AvciKontrol her tik gunceller; UI/olay gunlugu okur.
"""


import math


def clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x


def dinamik_ey_ref(p, pitch_deg, W, H):
    """DINAMIK DIKEY REFERANS (F1): govdeye sabit kamera one yatinca hedefin goruntu
    konumu kayar (23 derece yatista ~0.40 birim!) — sabit VIS_EY_REF yalniz sifir-yatis
    kalibrasyonudur. Referans durustan hesaplanir:
        ey_ref = tan(TILT + pitch_own) / tan(vFOV/2),  tan(vFOV/2) = tan(hFOV/2)*H/W
    (UE FRotator: pitch>0 = burun YUKARI; one yatis = NEGATIF pitch — log-dogrulandi.)
    pitch_deg None / VIS_ATT_COMP<=0 -> statik VIS_EY_REF (eski davranis, canli toggle)."""
    if pitch_deg is None or float(getattr(p, "VIS_ATT_COMP", 1.0)) <= 0.0:
        return float(getattr(p, "VIS_EY_REF", 0.0))
    tilt = float(getattr(p, "VIS_CAM_TILT_DEG", 25.0))
    hfov = float(getattr(p, "VIS_HFOV_DEG", 125.0))
    tan_v = math.tan(math.radians(hfov / 2.0)) * (float(H) / float(W)) if W > 1 else 1.0
    elev = clamp(tilt + float(pitch_deg), -75.0, 75.0)   # tan patlamasin (uc yatislar)
    return clamp(math.tan(math.radians(elev)) / max(tan_v, 1e-6), -1.0, 1.0)


class AvciGorselGuduum:

    def __init__(self):
        self.ex_f = None            # EMA-yumusatilmis yatay hata (kare-basina; asagiya bak)
        self.ey_f = None
        self.w_f = None             # EMA'li normalize bbox GENISLIGI (ileri fren olcusu)
        self._son = None            # (ex_f, ey_f, w_f, ey_ref, poz_cm) — kor-devam snapshot'i
        self._son_det_t = None      # son islenen tespitin zamani (kare-basina EMA kapisi)
        self.son_vz_des = None      # gozlemlenebilirlik: son istenen dikey hiz (cm/s; UI karti + log)
        self.son_vz = None          # son vz geri beslemesi (cm/s)
        self.son_alc = 1.0          # son ileri-kisma faktoru (1 = kisma yok)
        self.son_ey_ref = None      # son dikey referans (dinamik; UI REF cizgisi + log)
        self.son_eyd = None         # referansa gore dikey hata (kontrolorun sifirladigi buyukluk)

    def sifirla(self):
        """Re-acquire / gorev basi: EMA ve kor-devam durumunu temizle."""
        self.ex_f = self.ey_f = None
        self.w_f = None
        self._son = None
        self._son_det_t = None
        self.son_vz_des = None
        self.son_vz = None
        self.son_alc = 1.0
        self.son_ey_ref = None
        self.son_eyd = None

    # ------------------------------------------------------------------
    #  Yeni bbox ile komut uret (gorsel temas VAR).
    #  bbox_merkez=(cx,cy) px, W,H goruntu px, bbox_boyut=(w,h) px, p=Cfg, dt,
    #  vz=kendi dikey hiz (cm/s, +yukari), pitch_deg=kendi durusu (UE derece;
    #  dinamik referans icin), det_t=tespitin kare-ani (kare-basina EMA kapisi),
    #  poz_cm=poz cozucu mesafesi (ileri profil; bayrakla).
    #  return: (throttle, pitch, roll, yaw) hepsi [-1,1].
    # ------------------------------------------------------------------
    def hesapla(self, bbox_merkez, W, H, bbox_boyut, p, dt=0.02, vz=0.0,
                pitch_deg=None, det_t=None, poz_cm=None):
        cx, cy = bbox_merkez
        W = float(W); H = float(H)
        ex = (cx - W / 2.0) / (W / 2.0) if W > 1 else 0.0     # + = sagda
        ey = (cy - H / 2.0) / (H / 2.0) if H > 1 else 0.0     # + = altta
        w, h = bbox_boyut
        w_n = (float(w) / W) if W > 1 else 0.0                # normalize genislik (fren olcusu)

        # KARE-BASINA guncelleme: adim() 50 Hz AYNI tespitle tekrar cagirir; EMA'yi
        # her tikte isletmek tek kotu kareye ~%92 agirlik veriyordu ("tek-kare
        # bastirma" ancak kare-basina EMA ile calisir). Dikey referans + poz da
        # goruntuyle AYNI anda SNAPSHOT'lanir (donmus-ey + canli-ref karisimi kareler
        # arasinda sahte inis/tirmanis uretirdi). det_t=None -> eski her-cagri davranisi.
        if det_t is None or det_t != self._son_det_t:
            self._son_det_t = det_t
            a = float(p.VIS_EMA)                              # EMA yumusatma (kare-basina)
            if self.ex_f is None:
                self.ex_f, self.ey_f, self.w_f = ex, ey, w_n
            else:
                self.ex_f = (1.0 - a) * self.ex_f + a * ex
                self.ey_f = (1.0 - a) * self.ey_f + a * ey
                self.w_f = (1.0 - a) * self.w_f + a * w_n
            ey_ref = dinamik_ey_ref(p, pitch_deg, W, H)
            self._son = (self.ex_f, self.ey_f, self.w_f, ey_ref, poz_cm)
        else:
            _, _, _, ey_ref, poz_cm = self._son               # ayni kare: donmus snapshot, CANLI vz
        return self._komut(self.ex_f, self.ey_f, self.w_f, p, vz, ey_ref, poz_cm)

    # ------------------------------------------------------------------
    #  Kayip (dead-reckon): yeni bbox yok -> son EMA yonuyle KISA sure devam.
    #  Suru asilinca AvciKontrol hover'a gecirir.
    # ------------------------------------------------------------------
    def kor_devam(self, p, vz=0.0):
        if self._son is None:
            return 0.0, 0.0, 0.0, 0.0                          # hic tespit olmadi -> hover
        exf, eyf, wf, ey_ref, poz_cm = self._son               # donmus snapshot (ref+poz dahil)
        return self._komut(exf, eyf, wf, p, vz, ey_ref, poz_cm)  # sonum CANLI vz ile surer

    # ------------------------------------------------------------------
    #  Ortak komut hesabi (angle-mode).
    # ------------------------------------------------------------------
    def _komut(self, exf, eyf, wf, p, vz=0.0, ey_ref=None, poz_cm=None):
        # YATAY ortala: burnu/govdeyi hedefe dondur (yaw hiz komutu)
        yaw = clamp(p.VIS_SIGN_YAW * p.VIS_K_YAW * exf, -1.0, 1.0)
        if ey_ref is None:                                     # dogrudan cagri guvencesi
            ey_ref = float(getattr(p, "VIS_EY_REF", 0.0))
        # DIKEY: ASIMETRIK YASA (2026-07-05 v2).
        # SDK planti asimetrik: thr>0 = HIZ komutu (sim aninda izler; +0.7 = 23 m/s
        # TIRMANIS!), thr=0 = irtifa-tut, thr<0 = IVME alani (yercekimi telafisi kalkar;
        # inis yavas birikir, dalis hiz siniri yok). Canli loglardaki NET tirmanis
        # (+7.8 m/s, isaret ALTTAYKEN; ucus_log_20260705, thr max +0.715 = eski klemp izi)
        # ESKI ham-P kodundan (v1 hic ucmadi). Simetrik hiz-hatasi P'si (v1) de bu
        # plantta limit cevrimine MAHKUM: "fren" diye verilen pozitif thr, hiz-modunda
        # roket tirmanisi demek (olcum: thr>=0.5'te vz ort +17 m/s).
        #   TIRMANIS (vz_des>=0): thr = vz_des/VZ_MAX feedforward (sim donguyu kapatir;
        #                         GPS terminalinin kanitli eslemesi; oyun tavani 3333).
        #   INIS    (vz_des<0) : thr = KV*(vz_des - vz), klemp [THR_DN, 0.0] — fren =
        #                         telafiyi geri ac (thr=0 irtifa-tut); iniste ASLA
        #                         tirmanis komutu yok -> cevrim olur. Denge: thr -> 0'a
        #                         yaslanan testere disi (integrator plant, tau ~ 0.5 s).
        eyd = eyf - float(ey_ref)                              # referans DINAMIK (dinamik_ey_ref)
        vz_des = p.VIS_SIGN_VZ * p.VIS_VZ_MAX * clamp(p.VIS_K_VZ * eyd, -1.0, 1.0)
        if vz_des >= 0.0:
            throttle = clamp(vz_des / float(p.VZ_MAX), 0.0, p.THR_UP)
        else:
            throttle = clamp(p.VIS_KV_Z * (vz_des - vz), p.THR_DN, 0.0)
        # Ceviklik (kullanici spec'i: roll = SIGN*K*ex; "istenirse 0"): default K=0 KAPALI.
        roll = clamp(getattr(p, "VIS_SIGN_ROLL", 1.0) * getattr(p, "VIS_K_ROLL", 0.0) * exf,
                     -1.0, 1.0)
        # ILERI yaklas — KOORDINELI DALIS: yatay hizali VE hedef COK YUKARIDA degilse
        # surer. Alt-taraf kapisi KALDIRILDI (log kaniti: inis tiklerinin %84-92'sinde
        # pitch=0 -> "kanatlar durur", hedefe dalis yerine dik asansor dususu). Hedef
        # alttayken ileri+inis birlikte = dalis vektoru; ust-taraf kapisi kalir (hedef
        # cok yukaridaysa once tirman — altindan gecme).
        alc = 1.0
        if abs(exf) < p.VIS_CENTER_GATE and eyd > -p.VIS_CENTER_GATE:
            if poz_cm is not None and float(getattr(p, "VIS_USE_POSE_DIST", 0.0)) > 0.0:
                # POZ-MESAFELI ILERI PROFIL: gercek metreden dogrusal fren (yalniz
                # ILERIYI etkiler; yaw/throttle poz'dan bagimsiz). Bayrak kapali /
                # poz yokken asagidaki genislik yasasi BIREBIR gecerli (fallback).
                slow = float(getattr(p, "VIS_DIST_SLOW_M", 12.0)) * 100.0
                stop = float(getattr(p, "VIS_DIST_STOP_M", 4.0)) * 100.0
                fwd = p.VIS_K_FWD * clamp((float(poz_cm) - stop) / max(slow - stop, 1.0), 0.0, 1.0)
            else:
                # GENISLIK yasasi: sartname kisitlari EKSEN-BAZLI (Av'a sigma + >=%6)
                # oldugundan fren olcusu bbox GENISLIGI. (Eski alan yasasi area/0.20
                # durusu w~0.5'e tasiyordu = tam Av kenari, sifir gezinme payi.)
                fwd = max(0.0, p.VIS_K_FWD * (1.0 - float(wf) / max(float(getattr(p, "VIS_W_STOP", 0.30)), 1e-6)))
            pitch = clamp(p.VIS_SIGN_PITCH * fwd, -p.VIS_FWD_MAX, p.VIS_FWD_MAX)
            # ALCALMA ONCELIGI (hafif): inis isteginde ileri yatisi kis ki tasima inisi
            # yenmesin. Taban VIS_ALC_MIN (default 0.5): eski 0.15 tabani "kanat
            # durmasi" yaratiyordu. vz_des kapisi: VIS_SIGN_VZ cevrilse de dogru kalir.
            if vz_des < 0.0:
                alc = clamp(1.0 - abs(eyd) / p.VIS_CENTER_GATE,
                            float(getattr(p, "VIS_ALC_MIN", 0.5)), 1.0)
                pitch *= alc
        else:
            pitch = 0.0                                        # once hizala / once tirman
        # Gozlemlenebilirlik (UI GUDUM karti + ucus logu icin; komutu ETKILEMEZ)
        self.son_vz_des = float(vz_des)
        self.son_vz = float(vz)
        self.son_alc = float(alc)
        self.son_ey_ref = float(ey_ref)
        self.son_eyd = float(eyd)
        return float(throttle), float(pitch), float(roll), float(yaw)


# ==========================================================================
#  KILITLENME TAKIBI (sartname olcumu) — GOZLEMCI, komut uretmez.
#
#  Sartname geometrisi (kamera goruntusu %100 x %100):
#    - Hedef Vurus Alani (Av): yatayda her kenardan %25, dikeyde %10 iceride
#      kalan dikdortgen (p.KILIT_ALAN_X / p.KILIT_ALAN_Y).
#    - Kilitlenme Dortgeni (Ah) = tespit bbox'i. GECERLI kilit tiki icin:
#        (a) bbox genisligi >= p.KILIT_ESIK_ORAN*W ve yuksekligi >= ...*H
#            (sartname siniri %5; TAM sinirda calismak hakem incelemesinde
#             "hatali kilitlenme" riski -> tavsiye geregi %6 kullanilir),
#        (b) bbox TAMAMEN Av icinde,
#        (c) tespit TAZE: son bbox p.KILIT_TOLERANS_S'ten eski degil (ayni
#            sartname sabiti tazelik siniri olarak da kullanilir; yeni sabit
#            icat edilmez — 200 ms'den uzun kare boslugu zaten ihlaldir).
#    - KILITLENME = p.KILIT_SURE_S boyunca kesintisiz gecerlilik. Deneme icinde
#      biriken GECERSIZ sure p.KILIT_TOLERANS_S'i ("eksik veya hatali frame
#      toleransi", 5 sn'de ~200 ms) asarsa deneme SIFIRLANIR. Tolerans
#      baslangic/bitiste GECERLI DEGIL: deneme gecerli tikte baslar, basari
#      yalnizca gecerli tikte ilan edilir.
# ==========================================================================
class KilitlenmeTakip:

    def __init__(self):
        self.sifirla()

    def sifirla(self):
        """Yeni gorev: deneme + basari latch'i dahil her sey temiz."""
        self.gecerli = False        # bu tik kilit sartlari sagliyor mu?
        self.neden = "tespit yok"   # gecersizse kisa neden: tespit yok|kayip|kucuk|alan disi
        self.t0 = None              # aktif denemenin baslangici (perf_counter)
        self.sure_s = 0.0           # aktif denemenin yasi (sn) — UI ilerleme cubugu
        self.gap_s = 0.0            # denemede biriken gecersiz sure (sn) — tolerans butcesi
        self.basarili = False       # KILITLENME latch'i (gorev boyunca kalici)
        self.sayi = 0               # tamamlanan kilitlenme sayisi (deneme basina 1)
        self._deneme_sayildi = False  # bu denemede basari bir kez sayilsin

    # ------------------------------------------------------------------
    #  Her kontrol tikinde cagrilir (50 Hz). det: beyin.son_tespit (px,
    #  {cx,cy,w,h,W,H,...}) | None; det_t: o tespitin perf_counter zamani;
    #  now: perf_counter; p: Cfg; dt: tik suresi (Cfg.DT).
    # ------------------------------------------------------------------
    def guncelle(self, det, det_t, now, p, dt):
        ok, neden = False, "tespit yok"
        if det is not None and det_t is not None:
            if (now - det_t) > p.KILIT_TOLERANS_S + 1e-6:   # 1e-6: tik-carpani float payi
                neden = "kayip"                       # kare akisi durdu/bayat
            else:
                W = float(det.get("W", 0) or 0)
                H = float(det.get("H", 0) or 0)
                if W > 1 and H > 1:
                    w = float(det["w"]) / W
                    h = float(det["h"]) / H
                    cx = float(det["cx"]) / W
                    cy = float(det["cy"]) / H
                    if w < p.KILIT_ESIK_ORAN or h < p.KILIT_ESIK_ORAN:
                        neden = "kucuk"               # bbox boyut esiginin altinda
                    elif (cx - w / 2.0) < p.KILIT_ALAN_X or (cx + w / 2.0) > 1.0 - p.KILIT_ALAN_X \
                            or (cy - h / 2.0) < p.KILIT_ALAN_Y or (cy + h / 2.0) > 1.0 - p.KILIT_ALAN_Y:
                        neden = "alan disi"           # bbox vurus alanindan tasiyor
                    else:
                        ok, neden = True, "OK"
        self.gecerli, self.neden = ok, neden

        if ok:
            if self.t0 is None:                       # deneme GECERLI tikte baslar (bas kenar)
                self.t0 = now
                self.gap_s = 0.0
                self._deneme_sayildi = False
            self.sure_s = now - self.t0
            if (not self._deneme_sayildi) and self.sure_s >= p.KILIT_SURE_S:
                self._deneme_sayildi = True           # basari GECERLI tikte ilan (bitis kenari)
                self.basarili = True
                self.sayi += 1
        elif self.t0 is not None:
            self.gap_s += dt                          # eksik/hatali kare butcesinden ye
            self.sure_s = now - self.t0
            # butce asildi -> deneme bastan. 1e-6 payi: dt toplami float hatasiyla
            # TAM sinirda (10 tik x 0.02 = 0.2) sahte tasma yapmasin ("200 ms'ye
            # KADAR tolerans" siniri dahil).
            if self.gap_s > p.KILIT_TOLERANS_S + 1e-6:
                self.t0 = None
                self.sure_s = 0.0
                self.gap_s = 0.0

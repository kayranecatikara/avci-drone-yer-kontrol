# -*- coding: utf-8 -*-
"""
MENZIL KESTIRIMI — YOLO bounding box'tan hedef menzili.

Yasaya takilabilir SAF fonksiyon: menzil_kestir(w, h, ...) -> (R_metre, guven)
I/O yok, global durum yok, yan etki yok. Cagiran taraf gecmis tamponunu tutar.

--------------------------------------------------------------------------
SABITLERIN KAYNAGI  (2026-08-16 gercek ucus verisi)
--------------------------------------------------------------------------
Veri:  kopru/gazebo_kaynak/logs/bbox_ibvs_20260816_*.csv   (93 kosu)
Truth: veri/hedef_iz/hedef_iz_20260816_*.csv               (~30 Hz DoW dunya)
Eslesme: bbox `t` (time.monotonic) ile hedef_iz `t_mutlak` (time.perf_counter)
         ayni eksende; np.interp ile eslendi. Kalinti~Rdot dekorelasyonu ile
         olculen kalan gecikme +0.06 s (ihmal edilebilir: +-0.30 s kayma K'yi
         sadece %2.4 oynatiyor).
Ornek:  1788 tespitli kare, gercek menzil 15.4-41.5 m (medyan 21.7 m),
        gercek aspect 138-166 deg (KUYRUK TAKIBI - bkz. UYARI 1).

MODEL:  R = F * S_ETK / (w^A_W * h^A_H),   A_W + A_H = 1
        Us toplami 1'de KILITLI. Bu kasitli: kutu bir s kati buyurse menzil
        1/s kati kuculmeli (fiziksel olcek degismezligi). Uslari serbest
        birakan regresyon bu veride medAPE'yi 6.2%'den 3.2%'ye dusuruyor AMA
        blok-tutma testinde (uzun-menzilli blokta egit / kisa-menzilde test)
        %15-24 yanliliga cokuyor: serbest us, egitim setinin menzil
        ortalamasina cekilen bir SHRINKAGE kestirimi uretiyor, menzil olcmuyor.
        Us=-1 kilitli model ayni testte %3-4 yanlilikta kaliyor.
        (Ayni tuzak conf'u regresora koymakta da var - bkz. conf parametresi.)

OLCULEN PERFORMANS (bu modulun kendisi, kosu-ici ring-buffer ile, n=1788):
        model                       medAPE  P90    yanlilik  medAE   std(log)
        ESKI R=160/sqrt(wh)          21.0%  39.3%   -21.0%   4.64 m   0.163
        YENI tek-kare                 6.2%  20.2%     0.0%   1.41 m   0.147
        YENI 0.60 s pencere           5.3%  12.6%    +4.1%   1.19 m   0.080
        YENI 0.60 s + vc_ms telafisi  4.1%  11.1%    +1.6%   0.89 m   0.074
        Blok-tutma (farkli menzil rejiminde test): ESKI %23.7/%20.7 ->
        YENI %6.3/%5.0, yanlilik -%23.7/-%20.7 -> +%2.7/+%4.4.

A_W=0.15 / A_H=0.85: w^a*h^(1-a) ailesinde log-sacilimi en aza indiren a.
        std(log R*boyut) egrisi: a=0.5 (sqrt(wh)) 0.163 | a=0.15 0.147 |
        a=0.0 (yalniz h) 0.151. h agirlikli olmasinin sebebi kuyruk takibinde
        kutu YUKSEKLIGININ bakis acisina w'den cok daha az duyarli olmasi
        (w kanat aciklinigi izdusumu, aspect ile %26 oynuyor).
        DIKKAT: bu ucusta |roll| medyani 2.6 deg (maks 15). Yuksek yatista
        kanat h'ye sizar ve h agirligi bozulur; roll zarfi guvene islendi.

S_ETK=0.856 m: K = medyan(R_gercek * w^0.15*h^0.85) = 142.6 px*m olculdu;
        S_ETK = K/F = 142.6/166.6. Fiziksel yorumu hedefin bu aspect bandinda
        agirlikli gorunur uzanimi. Capraz kontrol: ayni veride sqrt(wh) icin
        K=202.6 -> 1.216 m; hedefin geometrik gorunur uzanimi (kanat 1.78 m,
        govde 1.10 m, aspect 138-166 deg) 1.15-1.45 m -> tutarli.
        S_ETK metre cinsinden oldugu icin F degisirse formul kendini tasir.

F=166.6 px: YASA kamera cercevesi (640x480, CX=320, CY=240). Dogrulandi —
        log'daki eps_yaw_deg ile atan((cx-320)/166.6) r=0.992 uyusuyor.

ESKI FORMUL (R=160/sqrt(wh)) ayni veride: medAPE %21.0, P90 %39.3,
        yanlilik -%21.0 (hep YAKIN saniyor), medAE 4.64 m. Yanliligin sebebi
        K'nin 160 secilmesi; olculen dogru degeri 202.6 (yani 160 = 0.79x).

--------------------------------------------------------------------------
UYARI 1 — ASPECT TABANI (modelin bilemedigi belirsizlik)
--------------------------------------------------------------------------
Aspect (hedef burun yonu ile hedef->biz yonu arasindaki aci) yasaya YASAK
(gorsel fazda hedef GPS'i yok), o yuzden modele KONMADI. Sadece olculdu:
  * Bu veride aspect 138-166 deg. log(R*boyut) sacilimi 0.163; bunun aspect
    ile aciklanan payi std 0.040 (varyansin %6). Yani BU BANTTA aspect
    +-%4'luk bir taban belirsizlik biniyor.
  * Bu rakam IYIMSER. Geometrik gorunur uzanim bu bantta 1.15-1.45 m (%26)
    degisiyor; TAM aspect araliginda (0-180 deg) 1.10-1.78 m (%62) degisir.
    Kuyruk takibi icin kalibre edilmis bir model bordadan (beam) gorulen
    hedefte menzili ~%25-30 EKSIK sayar. Head-on/beam gecislerde bu modelin
    tabani +-%4 degil, +-%25'tir. Yeni geometrilerde veri toplanmali.
  * Kalan sacilim (aspect ve olcum gurultusu cikarilinca) std 0.153 —
    detektor kutu tanimindaki kararsizlik. Duzlestirme bunun cogunu yiyor.

UYARI 2 — DUZLESTIRME GECIKMESI (terminal tetigi icin KRITIK)
--------------------------------------------------------------------------
PENCERE_S=0.60 s nedensel medyan, sacilimi std(log) 0.147 -> 0.080'e yariya
indiriyor (P90 %20.2 -> %12.6). Bedeli olculen 0.25 s
grup gecikmesi: kutu 0.25 s once neyse onu gosterir, yaklasirken o zaman
daha kucuktu, dolayisiyla menzil Vc*0.25 m FAZLA cikar.
  * Bu ucusta (Vc~2 m/s) yanlilik +%4.1. Vc=20 m/s'lik bir terminal daliste
    +%30 olur — yani 12 m'de 15.6 m sanir. Tetik gec yanar.
  * `vc_ms` verilirse tam telafi uygulanir: olculen kalinti~Vc egimi
    0.01506 -> 0.00493 (%67 dusuyor), yanlilik +%4.1 -> +%1.6.
  * Gecikme sabit degil, her cagirida gercek ornek zamanlarindan hesaplanir
    (tau = t - medyan(kullanilan ornek zamanlari)); seyrek/bosluklu
    gecmiste kendini dogru olcekler, tek-karede 0 olur.
  * `vc_ms`i KUTUDAN cikarmayin (UYARI 3) — kendi hizinizdan/PN'den verin.
NOT: K'yi 142.6 yerine 137.0 secip bu ucusun nominal gecikmesini SABITE
gommek de mumkundu (yanlilik %0 cikardi) ama o, 2 m/s kuyruk takibini
fizige gomer ve terminalde hatayi ikiye katlardi. K fiziksel birakildi.

UYARI 3 — KUTU BUYUMESINDEN KAPANMA HIZI CIKMAZ (bu rejimde)
--------------------------------------------------------------------------
Vc = R * dlog(boyut)/dt bagintisi olculdu. 0.8 s nedensel pencere en iyisi:
egim 1.03 (yansiz) ama korelasyon r=0.315 ve egim gurultusu 0.239 1/s.
Bu, sigma(Vc) ~ 0.24 * R m/s demek: R=22 m'de +-5.3 m/s. Bu ucusta gercek
Vc medyani 2.07 m/s oldugu icin SNR ~0.4 — kestirim, "sabit 2.07 ver"
demekten DAHA KOTU (medAE 2.78 vs 1.21 m/s; r=0.044).
=> 3-sigma tespit esigi: Vc > 3*0.239*R = 0.72*R  (R=22 m'de 16 m/s).
   Yani bu estimator ancak DIK/hizli terminal daliste anlam kazanir,
   kuyruk takibinde ASLA. Kapanma hizini kutudan degil kendi hizinizdan +
   PN/LOS'tan turetin. Neden bu kadar kotu: Vc/R = 0.095 1/s'lik gercek
   sinyal, kutunun 0.3 s korelasyon sureli ~%15 gurultusunun altinda kaliyor.
   Yardimci fonksiyon kapanma_kestir() guveni de dondurur; bu veride
   karelerin sadece %16'sinda guven>0.5 veriyor — yani dogru sekilde susuyor.
"""

import math

# ---- kamera ----
F_VARSAYILAN = 166.6          # px, YASA cerc. 640x480 (CX=320, CY=240)

# ---- menzil yasasi:  R = F * S_ETK / (w^A_W * h^A_H) ----
A_W = 0.15                    # 2026-08-16 ucusu, sacilim minimumu
A_H = 0.85                    # A_W + A_H = 1 (olcek degismezligi) - DEGISTIRMEYIN
S_ETK = 0.856                 # m; K/F = 142.6/166.6

# ---- duzlestirme ----
PENCERE_S = 0.60              # s, nedensel medyan penceresi. W=0.4/0.6/0.8 icin
                              # std(log) 0.088/0.080/0.079 -> 0.6'dan sonra
                              # kazanc bitiyor, gecikme buyumeye devam ediyor.

# ---- guven modeli: sigma^2 = TABAN^2 + KARE^2/N, sonra carpan cezalari ----
# Sabitler duzlestirilmis+telafili yolun kalintisina fit edildi; std(z)=0.996
# (z = kalinti/ongorulen sigma), ucte-bir dilimlerde de kalibre.
SIGMA_TABAN = 0.045           # duzlestirmenin indiremedigi yapisal taban
SIGMA_KARE = 0.080            # kare-basi bagimsiz bilesen
SIGMA_REF = 0.075             # guven=1.0 kabul edilen hedef 1-sigma
CONF_REF = 0.80               # bu conf'ta ceza yok
CONF_US = 1.5                 # sigma *= (CONF_REF/conf)^CONF_US; olculen std:
                              #   conf>0.80    0.071 | 0.72-0.80 0.081
                              #   0.60-0.72    0.129 | <0.60     0.193
# kalibrasyon zarfi: w/h orani. Olculen std(log): <2.2 0.228 | 2.2-2.6 0.087
# | 2.6-3.0 0.072 | 3.0-3.6 0.118 | >3.6 0.155. Zarf disi = model bu
# geometriyi hic gormedi (aspect ve/veya roll farkli).
ORAN_ALT, ORAN_UST = 2.5, 3.0
CEZA_ALT, CEZA_UST = 1.0, 0.5
ROLL_ZARF_DEG = 15.0               # ucusta gorulen maks |roll|


def _medyan(v):
    s = sorted(v)
    n = len(s)
    if n == 0:
        return None
    return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])


def menzil_kestir(w, h, conf=None, t=None, gecmis=None,
                  roll_deg=0.0, vc_ms=0.0, F=F_VARSAYILAN):
    """
    YOLO kutusundan menzil kestir. SAF fonksiyon (I/O yok, durum yok).

    Parametreler
    ------------
    w, h     : float  Kutu genisligi/yuksekligi, YASA cercevesinde PIKSEL
                      (640x480, F=166.6). Ham YOLO cerc. farkliysa once olcekle.
    conf     : float  YOLO guven skoru (0-1). Menzili KAYDIRMAZ, sadece guveni
                      belirler. Sebep: conf'u regresora koymak blok-tutma
                      testinde medAPE'yi %8.7 -> %14.0 bozdu (conf sahne/isik
                      bagimli, menzil vekili degil). Ama hata BUYUKLUGUNUN iyi
                      gostergesi (std 0.082 vs 0.240).
    t        : float  Bu karenin zaman damgasi (s). gecmis verilecekse gerekli.
    gecmis   : sequence of (t, w, h)  Onceki kareler (bu kare HARIC). Sadece
                      son PENCERE_S saniyesi kullanilir. None ise tek-kare mod.
    roll_deg : float  Kendi roll acimiz (kendi IMU'muz - gorsel fazda serbest).
                      Menzili kaydirmaz; zarf disinda guveni dusurur.
    vc_ms    : float  Bilinen kapanma hizi (m/s, yaklasan icin POZITIF). Verilirse
                      duzlestirme gecikmesi telafi edilir. Kutudan cikarmayin
                      (UYARI 3); kendi hiz/PN kestiriminizden verin.
    F        : float  Odak uzunlugu (px).

    Doner
    -----
    (R_metre, guven)
        R_metre : float  Kestirilen menzil (m). w veya h gecersizse None.
        guven   : float  0-1. Bagil 1-sigma hatayi geri almak icin:
                         sigma_bagil = SIGMA_REF / max(guven, 1e-3)
                         Ornek: guven 1.0 -> +-%7.5 ; guven 0.5 -> +-%15.
                         guven < 0.35 iken menzili kritik kararda (terminal
                         tetigi) tek basina kullanmayin.
    """
    if w is None or h is None:
        return None, 0.0
    try:
        w = float(w); h = float(h)
    except (TypeError, ValueError):
        return None, 0.0
    if not (w > 0.0 and h > 0.0) or not (math.isfinite(w) and math.isfinite(h)):
        return None, 0.0

    # ---- 1) nedensel duzlestirme: olcek ozelligini biriktir ----
    # (zaman, ozellik) ciftleri; zaman grup gecikmesini OLCMEK icin lazim.
    ornekler = [(t if t is not None else 0.0, (w ** A_W) * (h ** A_H))]
    if gecmis and t is not None:
        for kayit in gecmis:
            try:
                tg, wg, hg = kayit[0], float(kayit[1]), float(kayit[2])
            except (TypeError, ValueError, IndexError):
                continue
            if wg <= 0.0 or hg <= 0.0 or tg is None:
                continue
            if 0.0 <= (t - tg) <= PENCERE_S:
                ornekler.append((tg, (wg ** A_W) * (hg ** A_H)))
    n = len(ornekler)
    # medyan: buyuk-kutu patlamalarina (birlesmis/hatali tespit) dayanikli.
    # Ayni veride ortalama ile medyan medAPE'de esit (3.53 vs 3.81) ama
    # medyan P99 kuyrugunu daha az sisiriyor ve h>6.5 px'te gorulen
    # "kutu patlamasi" modunu tek karede yutuyor.
    olcek = _medyan([o[1] for o in ornekler])

    # ---- 2) menzil ----
    R = F * S_ETK / olcek

    # ---- 3) duzlestirme gecikmesi telafisi ----
    # Medyan filtresinin grup gecikmesi = simdiki zaman ile kullanilan
    # orneklerin MEDYAN zamani arasindaki fark. Sabit varsaymiyoruz: kare
    # atlamasi/seyrek gecmiste kendini dogru olcekler, n=1'de sifir olur.
    # Bu ucusta olculen medyan tau = 0.250 s (W/2 = 0.30 bekleniyordu).
    if vc_ms and n > 1 and t is not None:
        tau = t - _medyan([o[0] for o in ornekler])
        if tau > 0.0:
            R = max(R - vc_ms * tau, 0.1)

    # ---- 4) guven ----
    sigma = math.sqrt(SIGMA_TABAN ** 2 + (SIGMA_KARE ** 2) / float(n))
    if conf is not None:
        try:
            c = min(max(float(conf), 0.30), 1.0)
            sigma *= (CONF_REF / c) ** CONF_US if c < CONF_REF else 1.0
        except (TypeError, ValueError):
            pass
    # kalibrasyon zarfi: w/h orani. Zarf disi = aspect/roll bu modelin
    # gordugu geometriden farkli, kestirim dogrulanmadi.
    oran = w / h
    if oran < ORAN_ALT:
        sigma *= 1.0 + CEZA_ALT * (ORAN_ALT - oran) / ORAN_ALT
    elif oran > ORAN_UST:
        sigma *= 1.0 + CEZA_UST * (oran - ORAN_UST) / ORAN_UST
    # roll zarfi: h agirlikli model yuksek yatista bozulur
    ar = abs(roll_deg or 0.0)
    if ar > ROLL_ZARF_DEG:
        sigma *= 1.0 + (ar - ROLL_ZARF_DEG) / 30.0

    guven = SIGMA_REF / sigma
    guven = 0.0 if guven < 0.0 else (1.0 if guven > 1.0 else guven)
    return R, guven


# --------------------------------------------------------------------------
# YARDIMCI — kutu buyumesinden kapanma hizi. UYARI 3'u okumadan kullanmayin:
# bu rejimde (Vc ~ 2 m/s, R ~ 22 m) SNR ~0.4, sabit tahminden kotu. Fonksiyon
# guveni bu yuzden dondurur; guven esigini gecmeden komuta sokmayin.
# --------------------------------------------------------------------------
KAPANMA_PENCERE_S = 0.80      # olculen en iyi pencere (egim 1.03, yansiz)
KAPANMA_EGIM_SIGMA = 0.239    # 1/s, o penceredeki egim gurultusu (olculen)


def kapanma_kestir(t, w, h, gecmis, R_m=None, F=F_VARSAYILAN):
    """
    dlog(kutu)/dt egiminden kapanma hizi. Doner: (Vc_ms, guven).
    Vc pozitif = yaklasiyor. gecmis: (t, w, h) dizisi (bu kare haric).
    guven = SNR/3 tabanli; sigma(Vc) ~ KAPANMA_EGIM_SIGMA * R.
    """
    if gecmis is None or t is None:
        return None, 0.0
    ts, ys = [], []
    for kayit in list(gecmis) + [(t, w, h)]:
        try:
            tg, wg, hg = kayit[0], float(kayit[1]), float(kayit[2])
        except (TypeError, ValueError, IndexError):
            continue
        if wg <= 0.0 or hg <= 0.0 or tg is None:
            continue
        if 0.0 <= (t - tg) <= KAPANMA_PENCERE_S:
            ts.append(tg)
            ys.append(math.log((wg ** A_W) * (hg ** A_H)))
    n = len(ts)
    if n < 4:
        return None, 0.0
    tm = sum(ts) / n
    ym = sum(ys) / n
    sxx = sum((x - tm) ** 2 for x in ts)
    if sxx <= 1e-9:
        return None, 0.0
    egim = sum((ts[i] - tm) * (ys[i] - ym) for i in range(n)) / sxx
    if R_m is None:
        R_m, _ = menzil_kestir(w, h, t=t, gecmis=gecmis, F=F)
        if R_m is None:
            return None, 0.0
    Vc = R_m * egim                       # -dR/dt = R * dlog(boyut)/dt
    sigma_vc = KAPANMA_EGIM_SIGMA * R_m
    guven = abs(Vc) / (3.0 * sigma_vc) if sigma_vc > 0 else 0.0
    return Vc, (1.0 if guven > 1.0 else guven)

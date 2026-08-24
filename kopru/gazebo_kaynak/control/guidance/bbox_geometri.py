# -*- coding: utf-8 -*-
"""
================================================================================
  BBOX GEOMETRI  --  tespit kutusundan yon / menzil / irtifa / burun yonelimi
================================================================================
NE ISE YARAR
--------------------------------------------------------------------------------
Tek canli olcum "kutu" (cx, cy, w, h) + aracin KENDI durusu (roll, pitch, yaw)
iken sorulan dort soruyu SIFIRDAN turetilmis matematikle cevaplar:

    1. YON      hedefin bagil kerterizi (azimut) ve yukselisi nedir?
    2. MENZIL   kutunun boyutundan mesafe nasil cikar, belirsizligi ne?
    3. IRTIFA   dunya cercevesinde Delta-z (hedef bize gore ne kadar yukarida)?
    4. BURUN    yaw komutu nasil kurulur ki KANAL GECIKMESIYLE kararli kalsin?
    5. DAGITIM  istenen 3B ivme roll/pitch/itki kanallarina nasil paylastirilir?

⛔ BU MODUL YASA DEGIL, KUTUPHANEDIR
--------------------------------------------------------------------------------
Butun fonksiyonlar SAFTIR: yan etkisiz, global durum okumaz, env okumaz,
zaman okumaz, log yazmaz. Ayni girdi -> ayni cikti. Boylece:
    * birim testle kilitlenebilir (tests/test_bbox_geometri.py)
    * tezgahta gercek ucus loglarina karsi KOR kiyaslanabilir (sim/bbox_kontrol.py)
    * canli yasaya (bbox_ibvs) ancak env kapili TEK bir blokla baglanir.
Hicbir fonksiyon `bbox_ibvs` davranisini KENDILIGINDEN degistirmez.

⚠ IKI AYRI PIKSEL CERCEVESI VAR -- KARISTIRMA
--------------------------------------------------------------------------------
    (A) DoW ham karesi     1920x1080, HFOV 122.0709 deg, fx_dow = 531.36
    (B) YASA cercevesi     640x480,  CX=320, CY=240, FX=FY=166.58

    kopru/tespit_akisi.py::dow_pikseli_yasaya  A -> B cevirir ve AYNI ANDA
    dunyayi aynalar (yatay isaret donusu). Bu modulun BUTUN fonksiyonlari
    (B) cercevesinde, yani AYNALANMIS pikselle calisir -- bbox_ibvs ne
    goruyorsa o. Ham DoW pikseli vermeyin.

    Olcek:  FX / fx_dow = 166.58 / 531.36 = 0.31350

⚠ AYNA (bu depodaki en pahali hata, UC KEZ tekrarladi)
--------------------------------------------------------------------------------
    kopru/dow_kopru.py:49-53   NED_x=DoW_x, NED_y=-DoW_y, NED_z=-DoW_z,
                               yaw_NED = -yaw_DoW
    Dunya aynalandigi icin KAMERA da aynalanmak zorunda. Ayna PIKSELDE yapilir
    (dow_pikseli_yasaya), ACIDA degil. Bu modul aynanin ZATEN yapilmis oldugunu
    varsayar; burada ikinci kez aynalamayin.

================================================================================
 TURETMELERIN OZETI (ayrintisi her fonksiyonun docstring'inde)
================================================================================
 CERCEVE ZINCIRI   piksel -> kamera isini -> GOVDE(FRD) -> SEVIYE -> DUNYA
     kamera govdeye KAMERA_TILT = +25 deg YUKARI vidali (vision/geometry.py:27,
     CAM_TILT_RAD = -0.4363; Gazebo'da negatif pitch = burun yukari).
     Govde pitch trimi OLCULDU: -14.5 deg (n=7569; bagimsiz -13.3, n=31164)
     -> etkin bakis +25 - 14.5 = +10.5 .. +11.7 deg.

 MENZIL           R * (acisal boyut) = L_etkin  -- PIKSEL boyutu DEGIL.
     122 deg HFOV'da piksel boyutu merkezden uzaklastikca sec^2(alfa) ile
     SISER; sabit "px*m" carpani bu yuzden merkezde ve kenarda ayni degildir.
     Dogru degismez acisal boyuttur (bkz. acisal_boyut).

 KARARLILIK       yaw kanali:  149.7 deg/s per stick (R^2=0.948),
     takip gecikmesi 0.28 s, dongu 32.3 Hz (LOOP_HZ=50 varsayimi YANLIS),
     dedektor gecikmesi 0.20-0.25 s. Toplam faz kaybi kazanci belirler
     (bkz. yaw_kazanc_kararlilik).

================================================================================
 ÖLÇÜM SONUÇLARI  (sim/bbox_kontrol.py --veri --gecikme, 2026-08-17)
================================================================================
KAYNAK: 150 adet `bbox_ibvs_*.csv` (piksel + tutum) ile `veri/hedef_iz/*.csv`
(get_debug_truth konumu) t/t_mutlak ekseninde birlestirildi -> n = 20.944
GERCEK TESPITLI kare (hayalet kareler ve conf<0.35 atildi).
⛔ `karar_*.csv`'nin `u_truth/v_truth` sutunlari KULLANILMADI: onlar
   gps_guidance'in EMA ile filtrelenmis KESTIRIMININ projeksiyonudur, truth
   degil (ve YANLIS icsellikle, HFOV 125 ile, uretilmislerdir).

 1) DEDEKTOR GECIKMESI = 0.20 s   -- IKI BAGIMSIZ kanaldan ayni cevap
      yukselis hatasi (yaw'dan bagimsiz):  0.70 (D=0) -> 0.18 (D=0.20) -> 0.66 (D=0.40)
      yatay hata (tam tutarli)          :  1.94 (D=0) -> 0.91 (D=0.20) -> 1.97 (D=0.40)

 2) YON  (|hata| medyani, derece)
      A1 ham azimut,   yasanin zamanlamasiyla        4.30
      A2 los_seviye,   yasanin zamanlamasiyla        5.20   <-- ★ HAM'DAN KOTU
      A3 ham azimut,   tutum t-D'ye hizali           1.32
      A4 los_seviye,   tutum t-D'ye hizali           0.90
    ⇒ Yatay hatanin %83'u GEOMETRI DEGIL ZAMAN HIZALAMASIDIR. Ve roll
      telafisi BAYAT tutumla uygulandiginda hatayi BUYUTUR (4.30 -> 5.20).

 3) YUKSELIS  (|hata| medyani, derece; ayna dikeyi etkilemez, n=20.944)
      B1 piksel_elev(cy) + pitch  (bbox_ibvs:1410 yolu)     0.90
      B2 los_seviye yukselisi     (roll telafili)           0.51
      yatis 10-20 deg bandinda    1.89 -> 0.56   (kazanc 1.33 deg)
      yatis 20-30 deg bandinda    8.87 -> 3.03   (kazanc 5.84 deg)
      TERMINAL karelerde          0.80 -> 0.43   (n=6598)

 4) MENZIL  (medyan mutlak yuzde hata / yanlilik; kirpiksiz, n=14.724)
      M0  kod MENZIL_PX_M=202.6 / sqrt(wh)     33.8%  /  +33.0%   ⛔
      M0b kodun hardcoded ikizi 160.0          18.1%  /   +5.1%
      M1  232.9 / max(w,h)                     19.8%  /   -7.8%
      M2  arac/menzil_model (w^.15 h^.85)      40.3%  /  +38.0%   ⛔ EN KOTU
      M3  ACISAL, sabit L                      19.0%  /   +0.0%
      M4  ACISAL + GERCEK aspect               13.5%  /   +3.9%   (ALT SINIR)
      M5  ★ K_w / w  (yalniz GENISLIK)         16.7%  /   +0.0%   ← EN IYI
      M6  additif pay k/(sqrt(wh)-c)           21.8%  /   -0.5%   (en TUTARLI)
      OLCULEN SABITLER (n=22.527): R*sqrt(w*h)=148.9 | R*w=241.5 | R*max=242.4
        (hepsinin 1sigma bandi +-%30 -- taban belirsizlik ASPECT'ten geliyor)
      MENZILE GORE: 3-6 m'de 121.7 -> 15-30 m'de 158.6  (1.30 kat kayma)
      ⇒ M5 NEDEN KAZANIYOR: kutu YUKSEKLIGI genisliginden cok daha gurultulu
        (std(log(R*h)) = 0.494 vs std(log(R*w)) = 0.365). sqrt(w*h) o
        gurultuyu iceri aliyor.
      ⇒ USTEL TARAMASI (w^a h^(1-a)): en iyi a = 0.70 (std 0.3165).
        arac/menzil_model.py'nin A_W = 0.15'i std 0.4309 -- %36 DAHA KOTU.
        O sabit baska bir kosunun verisinde secilmis; bu veride cürüyor.
      ⇒ ADDITIF PAY (c = 2.50 px) menzil DILIMLERI arasindaki kaymayi
        1.303x -> 1.082x'e indiriyor (yani "R x boyut menzille kayiyor"
        bilmecesini buyuk olcude COZUYOR) ama nokta hatasini iyilestirmiyor.

 5) COZULEN/COZULMEYEN ALT SORULAR
      KIRPILMA  : kareler yalniz %0.4'u kadraj kenarina degiyor -> ACIKLAMA DEGIL
      OFF-AXIS  : sec^2 sismesi TEORIK olarak var ama VERIDE YOK
                  (menzil bandi sabitken olculen 0.77-1.06, beklenen 1.0-2.6)
                  -> bu yuzden ACISAL model PIKSEL modelinden %18 DAHA KOTU
      ASPECT    : ARTI(cross) modeli L=max(b|cos a|, l|sin a|) olculenle
                  %79-95 oraninda ortusuyor -> menzil hatasinin ANA kaynagi
      ADDITIF PAY: R*boyut'un menzille kaymasinin buyuk kismini aciklar;
                  c = 3.0 px ile dilim yayilimi 1.379x -> 1.102x
                  (⚠ en kucuk kareler c=4.9 der ve ASIRI duzeltir -- medyan kullan)
      YATAY OLCEK: tan(az_truth) = 0.86 * tan(az_olculen). D'den ve donus
                  hizindan BAGIMSIZ, yani gecikme artigi DEGIL. Ama DIKEY
                  eksen s=1.00'da (HFOV 122.07) en iyi -> kare piksel altinda
                  bir ODAK/HFOV hatasi OLAMAZ. ⛔ SEBEBI BULUNAMADI.
                  AVCI_DOW_HFOV'a DOKUNMAYIN: dikeyi ve menzil olcegini bozar.

 6) KAPALI CEVRIM (sim/deney.py, DEGISTIRILMEMIS bbox_ibvs.komut, n=40/kol)
      Tezgah sahayi dogruluyor (medyan 4.28-4.66 m; saha 4.22 m) AMA
      MENZIL_PX_M, DIKEY_ROLL, ACCEL_SPLIT ve K_YAW kollarinin HICBIRI
      iskayi anlamli degistirmiyor. Sebep: gorus orani yalnizca %18-26 --
      kestirim kalitesi seyreltiliyor, bagli kisit baska yerde.
      ⇒ Bu degisikliklerin sahada FAYDASI KANITLANMADI; yalnizca OLCUM
        kalitesinin duzeldigi kanitlandi. Hepsi env kapili ve KAPALI kalmali.
================================================================================
"""

from __future__ import annotations

import math

# ══════════════════════════════════════════════════════════════════════════
#  SABITLER — hepsi OLCULDU ya da motorun kendi degeri; hicbiri tahmin degil
# ══════════════════════════════════════════════════════════════════════════

# ── (B) YASA cercevesi icsellikleri — vision/geometry.py:21-24 ──
# IMG 640x480, HFOV_RAD=2.18166 (125 deg, Gazebo iris SDF'inden miras).
# ⚠ "125 deg" DoW'un gercek FOV'u DEGIL; ama dow_pikseli_yasaya aciyi
#   KORUYARAK cevirdigi icin FX sadelesir -> zararsiz. Bkz. sim/tesis.py:96-104.
CX = 320.0
CY = 240.0
FX = FY = (640.0 / 2.0) / math.tan(2.18166 / 2.0)      # 166.5786...

# ── (A) DoW ham karesi — UE5 motorunun KENDI degeri ──
# veri seti calismasinda UE4SS modu her kareye "camera_fov": 122.0709 yaziyor
# (7000+ karede sabit) ve 3B->2B motor projeksiyonlarindan en kucuk karelerle
# cozulen icsellikler fx=fy=531.36, cx=960, cy=540, artik 0.001 px.
DOW_GEN = 1920.0
DOW_YUK = 1080.0
DOW_HFOV_DEG = 122.0709
FX_DOW = (DOW_GEN / 2.0) / math.tan(math.radians(DOW_HFOV_DEG) / 2.0)   # 531.36
OLCEK_DOW_YASA = FX / FX_DOW                                            # 0.31350

# ── Kamera montaji ──
KAMERA_TILT_DEG = 25.0        # govdeye gore YUKARI (vision/geometry.py:27)
GOVDE_PITCH_TRIM_DEG = -14.5  # OLCULDU n=7569 (bagimsiz dogrulama -13.3, n=31164)

# ── Hedef (Talon) fiziksel boyutlari — collision mesh AABB'sinden ──
# vision/geometry.talon_aabb(); sim/tesis.Olcum ile ayni.
TALON_KANAT_M = 1.78          # kanat acikligi (y ekseni)
TALON_UZUNLUK_M = 1.10        # govde uzunlugu (x ekseni)
TALON_YUKSEKLIK_M = 0.38      # v-tail dahil dikey acikligi (z ekseni)

# ── Kanal olcumleri (arac/zarf_olcum*.py, kumanda cubugu dogrudan surulerek) ──
YAW_STICK_DPS = 149.7         # deg/s per stick (R^2 = 0.948)
YAW_GECIKME_S = 0.28          # komut -> donus takip gecikmesi
YAW_TAVAN_DPS = 120.0         # yazilim tavani
DEDEKTOR_GECIKME_S = 0.20     # gecikme taramasinin tepesi (egim 1.041)
# ── MENZIL KALIBRASYON SABITLERI (OLCULDU, sim/yaw_menzil.py --menzil,
#    n = 59.858 gercek tespitli kare / 393 log, 2026-08-17) ──
# ⛔ Bunlar bbox_ibvs'in VARSAYILANI DEGILDIR (orasi 202.6'da, kampanya
#    kosuyor). Burasi OLCULEN dogrudur; A/B kolu bu sayilari kullanir.
MENZIL_SQRT_PX_M = 153.1      # R * sqrt(w*h) medyani  (yanlilik +0.0%)
MENZIL_KW_PX_M = 240.9        # R * w  medyani         (yanlilik +0.0%)
MENZIL_TERM_PX_M = 196.0      # TERMINAL kapisi (boyut>=25 px kosullu; bkz.
#                               menzil_genislik docstring'i, Berkson secilimi)
MENZIL_PAY_PX = 2.23          # dedektorun sabit kutu payi c (regresyon egimi)
MENZIL_PAY_K = 127.6          # ayni regresyonun kesisimi -> R = K/(boyut - c)
DONGU_HZ = 32.3               # OLCULDU (kodun LOOP_HZ=50 varsayimi YANLIS)
DIKEY_OLU_S = 0.08
DIKEY_TAU_S = 0.64
DIKEY_DC = 1.05
YATAY_DC = 1.06
YATAY_TAU_S = 0.82            # olculen bant 0.72-0.93 ortasi

G = 9.80665


# ══════════════════════════════════════════════════════════════════════════
#  0. KUCUK YARDIMCILAR
# ══════════════════════════════════════════════════════════════════════════

def kirp(x, lo, hi):
    """Saf clamp. (lo > hi verilirse lo kazanir -- sessiz NaN uretmez.)"""
    return lo if x < lo else (hi if x > hi else x)


def sarmala_pi(a):
    """Aciyi (-pi, pi] araligina sarar. Kerteriz farki alan HER yerde sart:
    179 deg ile -179 deg arasindaki fark 358 degil 2 derecedir."""
    return (a + math.pi) % (2.0 * math.pi) - math.pi


# ══════════════════════════════════════════════════════════════════════════
#  1. CERCEVE ZINCIRI  —  piksel -> kamera -> govde -> seviye
# ══════════════════════════════════════════════════════════════════════════

def piksel_isin(cx, cy):
    """Yasa cercevesi pikseli -> KAMERA isini (normalize EDILMEMIS).

    Ince (pinhole) kamera modeli, radyal bozunum YOK:
        x = (cx - CX) / FX      kamera SAG
        y = (cy - CY) / FY      kamera ASAGI
        z = 1                   kamera ILERI

    NEDEN bozunum yok: DoW karesinin icsellikleri motorun kendi 3B->2B
    projeksiyonundan en kucuk karelerle cozuldu ve artik 0.001 PIKSEL cikti
    (veri seti calismasi, 7000+ kare). Yani DoW kamerasi TAM ince kameradir;
    bozunum modeli eklemek olcum gurultusunden kucuk bir duzeltme uydurur.
    -> `radyal bozunum` alternatifi tezgahta olculdu ve KAZANC SIFIR (bkz.
       sim/bbox_kontrol.py, "IBOZ" satiri).

    Donus: (x, y, 1.0)
    """
    return ((cx - CX) / FX, (cy - CY) / FY, 1.0)


def isin_govde(x, y, z=1.0, tilt_deg=KAMERA_TILT_DEG):
    """KAMERA isini -> GOVDE (FRD: ileri, sag, asagi).

    TURETME. Kamera govdeye `tilt` kadar YUKARI vidali (govde y ekseni etrafinda
    burun-yukari donus). Kamera ekseni ile govde ekseninin iliskisi:
        kamera ileri (z_c) = govdede  ( cos t, 0, -sin t )
        kamera asagi (y_c) = govdede  ( sin t, 0,  cos t )
        kamera sag   (x_c) = govdede  ( 0,     1,  0     )
    Isin (x, y, z) = x*x_c + y*y_c + z*z_c oldugundan:
        ileri = z*cos t + y*sin t
        sag   = x
        asagi = y*cos t - z*sin t

    DOGRULAMA: bbox_ibvs.los_seviye:1096-1098 ile BIREBIR ayni satirlar
    (z=1 ozel hali). tests/test_bbox_geometri.py::test_isin_govde_los_seviye_ile_ayni
    """
    t = math.radians(tilt_deg)
    ct, st = math.cos(t), math.sin(t)
    return (z * ct + y * st,        # ileri
            x,                      # sag
            y * ct - z * st)        # asagi


def govde_seviye(bx, by, bz, roll, pitch):
    """GOVDE (FRD) vektoru -> SEVIYE cercevesi (yaw haric duruş cikarilir).

    TURETME. ZYX Euler'de  v_ned = Rz(psi) Ry(theta) Rx(phi) v_govde.
    Yaw'i disarida birakinca kalan SEVIYE cercevesidir:
        v_seviye = Ry(pitch) . Rx(roll) . v_govde
    Rx(phi):  y1 = by*cos p - bz*sin p ,  z1 = by*sin p + bz*cos p
    Ry(th) :  x2 = bx*cos t + z1*sin t ,  z2 = -bx*sin t + z1*cos t

    Donus: (ileri, sag, asagi) SEVIYE cercevesinde.
    DOGRULAMA: roll=pitch=0 -> girdi aynen doner (birim test).
    """
    cr, sr = math.cos(roll), math.sin(roll)
    y1 = by * cr - bz * sr
    z1 = by * sr + bz * cr
    cp, sp = math.cos(pitch), math.sin(pitch)
    x2 = bx * cp + z1 * sp
    z2 = -bx * sp + z1 * cp
    return (x2, y1, z2)


def los_seviye(cx, cy, roll, pitch, tilt_deg=KAMERA_TILT_DEG):
    """★ REFERANS KESTIRIM — piksel + durus -> SEVIYE (azimut, yukselis) rad.

    Zincir: piksel_isin -> isin_govde -> govde_seviye -> kuresel acilar.
        azimut   = atan2(sag, ileri)          BURNA gore, SAG pozitif
        yukselis = atan2(-asagi, hypot(ileri, sag))   YUKARI pozitif

    ⚠ `yukselis` KURESEL (koni) acisidir: hypot(ileri, sag) paydasi yuzunden
      cx merkezden uzaklastikca kucultur. Duzlemsel `piksel_elev` bunu YAPMAZ
      ve iki fonksiyon cx != CX'te AYRISIR (bkz. piksel_elev docstring'i).
      Dogru olan kuresel olandir: dunyadaki gercek yukselis budur.

    Bu, bbox_ibvs.py:1074 `los_seviye` ile ayni matematiktir (orasi tek
    fonksiyonda yazilmis, burada zincir parcalara ayrildi ki her halka ayri
    test edilebilsin).

    DOGRULAMA (bu depo, gercek ucus): truth'a 0.00 deg hatayla uyuyor
    -- ama yasa bunu YALNIZ yatay kanalda kullaniyordu (bbox_ibvs:1133);
    terminal dikey nisani (:1410) roll'u hic cikarmiyor.
    """
    x, y, z = piksel_isin(cx, cy)
    bx, by, bz = isin_govde(x, y, z, tilt_deg)
    fx_, ry_, dn_ = govde_seviye(bx, by, bz, roll, pitch)
    return (math.atan2(ry_, fx_),
            math.atan2(-dn_, math.hypot(fx_, ry_)))


def piksel_elev(cy, tilt_deg=KAMERA_TILT_DEG):
    """GOVDE cercevesinde DUZLEMSEL yukselis (rad) — bbox_ibvs:1017 ikizi.

    TURETME. cx = CX varsayilir (yani isin dikey duzlemde). O zaman
        b = (cy - CY)/FY ,  ileri = cos t + b sin t ,  asagi = b cos t - sin t
        yukselis = atan2(sin t - b cos t, cos t + b sin t)

    ⚠ SINIRI: cx != CX oldugunda bu, gercek kuresel yukselisten BUYUKTUR
      (payda hypot(ileri, sag) yerine yalniz `ileri` kullanilir). Yasa
      terminalde tam da bunu yapiyor. Sapma tezgahta olculdu, bkz.
      sim/bbox_kontrol.py "DUZLEM vs KURESEL" tablosu.

    DOGRULAMA: cy = CY + FY*tan(25 deg) = 317.7 -> yukselis 0 (seviye hedef).
               cy = 301 (CY_NISAN) -> +4.888 deg.
    """
    t = math.radians(tilt_deg)
    b = (cy - CY) / FY
    return math.atan2(math.sin(t) - math.cos(t) * b,
                      math.cos(t) + math.sin(t) * b)


def elev_piksel(elev, tilt_deg=KAMERA_TILT_DEG):
    """piksel_elev'in TAM TERSI: govde yukselisi (rad) -> cy pikseli.

    TURETME. tan(e) = (sin t - cos t b)/(cos t + sin t b)'yi b icin cozersek
        b = tan(t - e)   =>   cy = CY + FY * tan(KAMERA_TILT - e)
    DOGRULAMA (tur-donusu): elev_piksel(piksel_elev(cy)) == cy, |hata| < 1e-9
    px, 301 .. 400 araliginda taranarak (birim test).

    ⚠ tan patlamasina karsi (t - e) +-70 deg ile sinirlanir; oradan otesi
      zaten kadraj disidir.
    """
    t = math.radians(tilt_deg)
    a = kirp(t - elev, -math.radians(70.0), math.radians(70.0))
    return CY + FY * math.tan(a)


def seviye_piksel(az, el, roll, pitch, tilt_deg=KAMERA_TILT_DEG):
    """★ los_seviye'nin TAM TERSI: SEVIYE (az, el) + durus -> piksel (cx, cy).

    TURETME (zinciri geriye kosarak):
      1) seviye birim vektoru  u = (cos el cos az, cos el sin az, -sin el)
      2) seviye -> GOVDE       u_b = Rx(-roll) . Ry(-pitch) . u
      3) govde -> KAMERA isini isin_govde'yi tersine cevirerek:
            z =  bx*cos t - bz*sin t        (kamera ileri)
            y =  bx*sin t + bz*cos t        (kamera asagi)
            x =  by                          (kamera sag)
         (Kontrol: z*ct + y*st = bx ve y*ct - z*st = bz -- birebir kapanir.)
      4) piksel  cx = CX + FX*x/z ,  cy = CY + FY*y/z ;  z <= 0 ise KAMERA
         ARKASI -> None.

    NE ISE YARAR: tezgahin ileri modeli. Gercek 3B geometriden piksel uretip
    yasaya vermek icin gerekir; boylece kapali cevrim benzetimi yasanin
    KENDI okuma zincirini kullanir ve "tesisin kendi hatasi bulgu sanilir"
    tuzagina dusmez (bkz. sim/tesis.py'nin iki sahte bulgusu).

    DOGRULAMA: tur-donusu los_seviye(seviye_piksel(az,el,r,p), r, p) == (az,el),
    |hata| < 1e-12 rad, 4 durus x 25 yon taranarak (birim test).
    """
    ce, se = math.cos(el), math.sin(el)
    u = (ce * math.cos(az), ce * math.sin(az), -se)
    cp, sp = math.cos(pitch), math.sin(pitch)
    x1 = u[0] * cp - u[2] * sp                    # Ry(-pitch)
    z1 = u[0] * sp + u[2] * cp
    cr, sr = math.cos(roll), math.sin(roll)
    by = u[1] * cr + z1 * sr                      # Rx(-roll)
    bz = -u[1] * sr + z1 * cr
    bx = x1
    t = math.radians(tilt_deg)
    ct, st = math.cos(t), math.sin(t)
    z = bx * ct - bz * st
    y = bx * st + bz * ct
    x = by
    if z <= 1e-9:
        return None
    return (CX + FX * x / z, CY + FY * y / z)


def kutu_uret(az, el, roll, pitch, menzil_m, l_yatay_m, l_dikey_m,
              tilt_deg=KAMERA_TILT_DEG):
    """Gercek geometriden TESPIT KUTUSU uretir (tezgahin ileri modeli).

    Kutu boyutu, off-axis sismesi DAHIL hesaplanir -- yani ince kamera
    modelinin gercekten yaptigi sey:
        yari_aci = atan( L / (2R) )
        kenarlar, LOS'un iki yanindaki yari_aci kadar sapmis isinlarin
        PIKSEL yerleridir; aradaki fark sec^2 ile buyur.
    Bu, sabit "L/R * FX" kisayolunun aksine kadraj kenarinda DOGRUdur.

    Donus: (cx, cy, w, h) veya kadraj arkasindaysa None.
    """
    m = seviye_piksel(az, el, roll, pitch, tilt_deg)
    if m is None:
        return None
    d_y = 2.0 * math.atan((l_yatay_m / 2.0) / max(menzil_m, 1e-6))
    d_d = 2.0 * math.atan((l_dikey_m / 2.0) / max(menzil_m, 1e-6))
    p1 = seviye_piksel(az - d_y / 2.0, el, roll, pitch, tilt_deg)
    p2 = seviye_piksel(az + d_y / 2.0, el, roll, pitch, tilt_deg)
    p3 = seviye_piksel(az, el - d_d / 2.0, roll, pitch, tilt_deg)
    p4 = seviye_piksel(az, el + d_d / 2.0, roll, pitch, tilt_deg)
    if None in (p1, p2, p3, p4):
        return None
    return (m[0], m[1], abs(p2[0] - p1[0]), abs(p4[1] - p3[1]))


# ── KAMERA MONTAJ OFSETI (paralaks) ──
# vision/geometry.py:26  CAM_OFFSET_POS = (0.10, 0.0, 0.05) m, base_link'e gore
# (Gazebo cercevesi: x ileri, y sol, z yukari). FRD karsiligi (ileri, sag, asagi):
KAMERA_OFSET_FRD = (0.10, 0.0, -0.05)


def parallaks_duzelt(az, el, menzil_m, ofset_frd=KAMERA_OFSET_FRD):
    """Kamera GOVDE MERKEZINDE degil -> yakin menzilde olculur bir kayma.

    TURETME. Olculen yon KAMERA'dan hedefe olandir; guduum GOVDE merkezinden
    olani ister. Kamera govde cercevesinde `p` noktasindaysa
            T_govde = R_kam * u + p
    Birim LOS ve onun aci turevleri (FRD, el YUKARI pozitif):
            u      = ( cos el cos az,  cos el sin az, -sin el )
            du/daz = ( -cos el sin az, cos el cos az,  0      )   |.| = cos el
            du/del = ( -sin el cos az, -sin el sin az, -cos el)   |.| = 1
    Birinci mertebede p'nin bu iki yondeki bileseni aciyi kaydirir:
            d_az = ( -p_f sin az + p_r cos az ) / ( R cos el )
            d_el = ( -p_f sin el cos az - p_r sin el sin az - p_d cos el ) / R

    ⚠ ILK YAZIMDA d_el = +p_d/R yazmistim: HEM ISARET ters HEM `p_f`
      (ileri ofset) terimi eksikti. Motorun ileri modeline karsi yazilan
      test bunu yakaladi (0.24 derece artik). Duzeltilmis form artik
      1e-4 rad altinda kapaniyor.

    BUYUKLUK (Gazebo ofseti 0.10 ileri / 0.05 YUKARI, seviye hedef):
        R = 20 m -> d_el = +0.14 deg     R =  8 m -> +0.36 deg
        R =  5 m -> +0.57 deg            R =  3 m -> +0.95 deg
    Yani TERMINALDE olculen yukselis hatasiyla (0.38 deg medyan) AYNI
    MERTEBEDE. Uzakta ihmal edilebilir, son metrelerde DEGIL.

    ⛔ ÖLÇÜLMEDİ: bu ofset GAZEBO iris SDF'inden gelir (vision/geometry.py:26).
      DoW'daki kamera montaj noktasi bu depoda HIC olculmedi. Fonksiyon dogru
      matematigi saglar ama DoW icin `ofset_frd` OLCULENE KADAR KULLANMAYIN --
      yanlis ofsetle duzeltmek, hic duzeltmemekten kotudur.
    """
    R = max(menzil_m, 1e-6)
    p_f, p_r, p_d = ofset_frd
    ce, se = math.cos(el), math.sin(el)
    ca, sa = math.cos(az), math.sin(az)
    d_az = (-p_f * sa + p_r * ca) / (R * max(ce, 1e-6))
    d_el = (-p_f * se * ca - p_r * se * sa - p_d * ce) / R
    return az + d_az, el + d_el


def azimut_ham(cx):
    """TELAFISIZ kamera azimutu: atan((cx - CX)/FX).

    Bu, aracin duruşunu YOK SAYAR. Yatista seviye azimutu DEGILDIR:
    olculdu, 30-40 deg yatista 11-14 deg sapma. Kiyas tabani olarak durur.
    """
    return math.atan((cx - CX) / FX)


def dow_yasa_piksel(cx_dow, cy_dow, w_dow, h_dow, W=DOW_GEN, H=DOW_YUK,
                    hfov_deg=DOW_HFOV_DEG):
    """DoW ham pikseli -> YASA cercevesi pikseli (AYNALI).

    kopru/tespit_akisi.py::dow_pikseli_yasaya ile BIREBIR ayni; burada
    bagimsiz test edilebilsin diye kopyalandi (bagimlilik istemiyoruz).
        cx_yasa = CX - FX*(cx_dow - W/2)/fx_dow      <- AYNA (eksi)
        cy_yasa = CY + FY*(cy_dow - H/2)/fx_dow      <- dikey DEGISMEZ
        w,h     = *, FX/fx_dow ile olceklenir        <- acisal boyut korunur
    DOGRULAMA: tests/test_bbox_geometri.py::test_dow_ceviri_tespit_akisi_ile_ayni
    (gercek tespit_akisi modulu import edilip 1000 rastgele piksel kiyaslanir).
    """
    if not W or not H or W <= 0 or H <= 0:
        return cx_dow, cy_dow, w_dow, h_dow
    fx_dow = (W / 2.0) / math.tan(math.radians(hfov_deg) / 2.0)
    if fx_dow <= 0:
        return cx_dow, cy_dow, w_dow, h_dow
    return (CX - FX * (cx_dow - W / 2.0) / fx_dow,
            CY + FY * (cy_dow - H / 2.0) / fx_dow,
            w_dow * FX / fx_dow,
            h_dow * FY / fx_dow)


# ══════════════════════════════════════════════════════════════════════════
#  2. KUTUDAN MENZIL  —  once ACISAL boyut, sonra metre
# ══════════════════════════════════════════════════════════════════════════

def acisal_boyut(cx, cy, w, h):
    """Kutunun GERCEK acisal genisligi ve yuksekligi (rad).

    ⛔ NEDEN "w/FX" YANLIS: 122 deg HFOV'da piksel olcegi merkezden uzaklastikca
    SISER. Isin yonu (x, y, 1) ise rho = sqrt(1+x^2+y^2) = sec(alfa) ve

        RADYAL yonde   piksel/aci kazanci = FX * sec^2(alfa) = FX * rho^2
        TEGET  yonde   piksel/aci kazanci = FX * sec(alfa)   = FX * rho

    (Turetme: u = FX tan(alfa) cos(phi), v = FX tan(alfa) sin(phi).
     d(u,v)/d(alfa) buyuklugu FX sec^2 alfa; d(u,v)/d(phi) buyuklugu
     FX tan alfa, ve teget acisal yer degistirme sin(alfa) dphi oldugundan
     kazanc FX tan alfa / sin alfa = FX sec alfa.)

    Sayisal: alfa=45 deg'de RADYAL kazanc 2.00x, TEGET 1.41x. Yani ayni
    hedef kadrajin kenarinda merkezdekinin IKI KATI piksel kaplar. Sabit bir
    "px*m" carpani bu yuzden kadraj boyunca SABIT DEGILDIR -- MENZIL_PX_M'in
    menzille kaymasinin ana sebeplerinden biri budur.

    ⚙ COZUM (yaklasim degil, TAM): kutunun kenarlarini isin'a cevirip
    ARALARINDAKI ACIYI olc. Boylece butun sec kuvvetleri kendiliginden gider.
        d_yatay = aci( isin(cx-w/2, cy), isin(cx+w/2, cy) )
        d_dikey = aci( isin(cx, cy-h/2), isin(cx, cy+h/2) )

    ⛔⛔ OLCUM BU TURETMEYI DESTEKLEMIYOR -- ve bu, raporun en onemli
    NEGATIF bulgusudur. Menzil bandi SABIT tutulup (6-12 m, kirpiksiz)
    off-axis acisina gore bakildiginda 'R x piksel_boyut' ARTMIYOR, hafifce
    AZALIYOR:
        alfa      0-10   10-20  20-30  30-45  45-65
        olculen   1.000  0.910  0.930  0.862  0.771
        sec^2     1.015  1.068  1.213  1.512  2.516
    Yani sec^2 duzeltmesi uygulanirsa hata BUYUR: acisal olcutun sacilimi
    piksel olcutunden %18 DAHA KOTU (std(log) 0.401 vs 0.340, n=20.756).
    ⇒ Geometrik turetme dogru, ama DEDEKTORUN kutusu ideal siluet degil:
      kadraj kenarinda hedef radyal olarak 2-3 kat gerilir ve YOLO onu
      sistematik olarak KUCUK kutular. Iki etki birbirini goturuyor.
    ⇒ MENZIL ICIN PIKSEL OLCUTUNU KULLANIN. Bu fonksiyon ACI olcmek icin
      dogrudur (ve `menzil_acisal` sentetik testte kusursuzdur), ama gercek
      dedektorle menzil kestiriminde KAZANC SAGLAMAZ.

    Donus: (d_yatay, d_dikey) radyan.
    """
    def _birim(px, py):
        x, y, z = piksel_isin(px, py)
        n = math.sqrt(x * x + y * y + z * z)
        return (x / n, y / n, z / n)

    def _aci(a, b):
        d = kirp(a[0] * b[0] + a[1] * b[1] + a[2] * b[2], -1.0, 1.0)
        return math.acos(d)

    hw, hh = max(w, 0.0) / 2.0, max(h, 0.0) / 2.0
    d_yatay = _aci(_birim(cx - hw, cy), _birim(cx + hw, cy))
    d_dikey = _aci(_birim(cx, cy - hh), _birim(cx, cy + hh))
    return d_yatay, d_dikey


def menzil_px_sabit(w, h, k_px_m):
    """EN BASIT model (yasanin bugunku hali): R = k / sqrt(w*h).

    bbox_ibvs.Cfg.MENZIL_PX_M = 202.6 px*m (2026-08-16 kalibrasyonu, 1788 kare).

    ★ 20.944 KARELIK YENIDEN OLCUM (2026-08-17): DOGRU SABIT 147.9 px*m.
        202.6 -> medyan mutlak hata %37.4, yanlilik +%37.0  (menzil SISIRILIYOR)
        160.0 -> %20.0, +%8.2        147.9 -> %20.0, ~0
      ⚠ YANI bbox_ibvs.py:1938'deki "duzeltilmemis" HARDCODED 160.0 IKIZ,
        yasanin "kalibre" 202.6'sindan DAHA DOGRUDUR. Terminal nisan kapisi
        %27 gevsek degil, tersine yasanin geri kalani %37 sisik calisiyor.
      ⚠ 202.6 ancak 30-60 m'de dogru (orada olculen 222). 6-15 m'de -- yani
        TERMINALDE -- %40-50 sisik. Kalibrasyon o zaman uzak karelerin
        agirligiyla cikmis olmali.

    ⚠ TEK SABIT YETMEZ: 'R x sqrt(w*h)' menzille 1.38 kat kayiyor
      (3-6 m: 114.7 ... 15-30 m: 159.4) ve 1sigma bandi +-%31. Bunun ana
      sebebi ASPECT'tir (bkz. gorunur_genislik_m); ikincil sebep dedektorun
      sabit kutu payidir (bkz. menzil_ofsetli).
    """
    b = math.sqrt(max(w, 0.0) * max(h, 0.0))
    return (k_px_m / b) if b > 1e-6 else float("inf")


def menzil_ofsetli(w, h, k_px_m, ofset_px):
    """★ EN IYI OLCULEN MODEL: R = k / (sqrt(w*h) - c).

    ⛔ COZULEN BILMECE: "MENZIL_PX_M neden menzille kayiyor?" Kodun notu
    (bbox_ibvs:961) vekilin yakinda 2.13 kat sistigini yaziyor ama SEBEBINI
    bilmiyordu. Sebep, DEDEKTORUN KUTUSUNDAKI SABIT PAYDIR.

    TURETME. Dedektor kutusu gercek siluetten sabit `c` piksel BUYUK olsun
    (bulaniklik, kenar yumusatma, egitim etiketlerindeki pay):
            s_olculen = s_gercek + c = FX*L/R + c
    Buradan
            s_olculen * R = FX*L + c*R
    yani "R x boyut" carpani SABIT DEGIL, R'de DOGRUSALDIR. Olculen tam da
    budur (n=13203, D=0.20 s, kirpiksiz):
            menzil  3-6 m -> 120.6 | 6-10 -> 138.1 | 10-15 -> 145.6 | 15-30 -> 158.9
        egim ~ 2.2 px, kesisim ~ 111 px*m -> L_etkin = 111/166.58 = 0.67 m
    Tersi:  R = FX*L / (s - c) = k / (s - c).

    ⚠ c > 0 oldugu icin s -> c'ye yaklastikca R patlar; UZAK hedefte
      (kucuk kutu) model kirilgandir. Kullanirken s > c + 3 px kapisi koyun;
      altinda "menzil bilinmiyor" demek, yanlis menzil vermekten iyidir.
    ⚠ c dedektore ozguduur: model/esik degisirse YENIDEN kalibre edilmeli.
      Mekanizma kapisi: kalibrasyon dogruysa "R x boyut" dilimleri arasindaki
      yayilim 1.32x'ten ~1.05x'e DUSMELI.
    """
    s = math.sqrt(max(w, 0.0) * max(h, 0.0)) - ofset_px
    return (k_px_m / s) if s > 1e-6 else float("inf")


def menzil_genislik(w, k_px_m=MENZIL_KW_PX_M):
    """★ YALNIZ GENISLIK: R = K_w / w.

    NEDEN YUKSEKLIGI ATIYORUZ. Olculen (n=20.944, 2026-08-17):
        std(log(R*w)) = 0.365   <   std(log(R*h)) = 0.494
    Kutu YUKSEKLIGI genisliginden %35 daha gurultulu (Talon'un dikey acikligi
    yalniz 0.38 m; birkac pikselde tasiniyor ve dedektor payi orada baskin).
    sqrt(w*h) o gurultuyu yariya indirmis olarak ICERI ALIR. Genisligi tek
    basina kullanmak gurultuyu DISARIDA birakir.

    ★ YENIDEN OLCULDU (n=59.858 kare / 393 log, 2026-08-17 aksami,
      sim/yaw_menzil.py --menzil):
            model                          medAPE   yanlilik   R<15m medAE
            202.6/sqrt(wh)  (yasa)          33.0%    +32.3%      3.52 m
            160.0/sqrt(wh)  (kod ikizi)     19.0%     +4.5%      2.16 m
            153.1/sqrt(wh)  (olculen)       19.3%     +0.0%      2.11 m
            240.9/w         (bu fonksiyon)  19.9%     +0.0%      2.01 m
      ⚠ ONCEKI TUR "K_w/w %16.7 ile EN IYI" demisti; 3 KAT buyuk veride
        NOKTA HATASINDA fark KALMIYOR (19.9 vs 19.3). Kazanci baska yerde:
        menzil bantlari arasindaki KAYMA (asagi bak).

    ⚠ KOSULLANDIRMA TUZAGI (bu depoda iki kez yanlis hukum verdirdi):
      Ayni sabit, hangi degiskene kosullandirdiginiza gore FARKLI yanlilik
      gosterir.
            R'ye kosullu (3-6 m bandi)      : 202.6 -> +53%,  153.1 -> +16%
            boyut'a kosullu (boyut >= 25 px): 202.6 ->  +3%,  153.1 -> -22%
      Sebep BERKSON SECILIMI: boyut>=25 secmek, kutunun RASGELE BUYUK
      ciktigi kareleri toplar; orada k/boyut zaten dusuk cikar.
      ⇒ TERMINAL KAPISI boyut'a bakarak actigi icin ONUN hukmu boyut
        kosullusudur (olculen en iyi sabit ~196 px*m); kapanma hizi ve
        YANAL_K ise R'ye kosullu calisir (olculen 153.1). BU YUZDEN
        bbox_ibvs'de MENZIL_PX_M ile MENZIL_TERM_PX_M AYRI kalir.
    """
    return (k_px_m / w) if w > 1e-6 else float("inf")


def menzil_acisal(cx, cy, w, h, l_yatay_m, l_dikey_m=None, agirlik=None):
    """★ ACISAL menzil: R = L_etkin / delta_acisal (off-axis sismesi YOK).

    TURETME. LOS'a dik, uzunlugu L olan bir parca R menzilde delta = 2*atan(L/2R)
    aci gorur; kucuk aci icin delta ~ L/R. `acisal_boyut` delta'yi TAM olctugu
    icin
            R = (L/2) / tan(delta/2)
    Kucuk acida R = L/delta. Buradaki tan, hedefin yakin oldugu (delta buyuk)
    son metrelerde onemlidir: delta = 20 deg'de kucuk-aci %1.0 hata verir,
    delta = 40 deg'de %4.2.

    l_yatay_m / l_dikey_m: hedefin o eksendeki fiziksel acikligi. Ikisi de
    verilirse `agirlik` (0..1) ile harmanlanir; agirlik None ise ikisinin
    belirsizligine gore ters-varyans agirligi yerine BASIT geometrik ortalama
    kullanilir (tezgahta ikisi ayri ayri da olculur).
    """
    dy, dd = acisal_boyut(cx, cy, w, h)
    r_y = ((l_yatay_m / 2.0) / math.tan(dy / 2.0)) if dy > 1e-9 else float("inf")
    if l_dikey_m is None or dd <= 1e-9:
        return r_y
    r_d = (l_dikey_m / 2.0) / math.tan(dd / 2.0)
    if agirlik is None:
        if not (math.isfinite(r_y) and math.isfinite(r_d)):
            return r_y if math.isfinite(r_y) else r_d
        return math.sqrt(max(r_y, 1e-9) * max(r_d, 1e-9))
    a = kirp(agirlik, 0.0, 1.0)
    return a * r_y + (1.0 - a) * r_d


def gorunur_genislik_m(aspect_rad, kanat_m=TALON_KANAT_M,
                       uzunluk_m=TALON_UZUNLUK_M, dedektor_k=1.0):
    """Hedefin LOS'a DIK gorunen yatay acikligi (m), aspect acisina gore.

    ASPECT TANIMI (bu depoda kullanilan): hedefin BURNU ile (hedef -> biz)
    vektoru arasindaki aci. aspect = 180 deg -> tam ARKASINDAYIZ (kuyruk
    takibi); 90 deg -> BORDA; 0 deg -> karsidan (burun bize donuk).

    ⛔ TURETME — TOPLAM DEGIL, MAKSIMUM. Talon yatayda bir DIKDORTGEN degil
    bir ARTI isaretidir: kanatlar (aciklik b) govde eksenine DIK, govde
    (uzunluk l) eksen BOYUNCA, ikisi ortak merkezden gecer. Govde ekseni ile
    LOS arasindaki aci phi olsun (|cos phi| = |cos aspect|).
        kanat uclarinin LOS'a dik izdusumu : +- (b/2)|cos phi|
        govde uclarinin LOS'a dik izdusumu : +- (l/2)|sin phi|
    Eksen-hizali kutu bu UC noktalarin en disini sarar, yani TOPLAM degil
    MAKSIMUM alinir:
        L(aspect) = max( b*|cos(aspect)| , l*|sin(aspect)| )
    Sinir degerler:  aspect=180/0  (burun/kuyruk) -> 1.78 m  (kanat aciklığı)
                     aspect=90     (borda)        -> 1.10 m  (govde uzunlugu)
                     aspect=148    (gecis)        -> 1.51 m
    ⚠ ILK YAZIMDA "b|sin|+l|cos|" YAZMISTIM -- HEM toplam HEM sin/cos ters.
      Tezgah bunu yakaladi: modelin dedigi 2.04 m'ye karsi olculen 0.66-1.48 m.
      Duzeltilmis MAKSIMUM modeli olculenle %85-98 orantida (bkz. asagi).

    OLCULDU (bu tezgah, n=7667 gercek tespit, truth menzille):
        aspect bandi   olculen L   max-model   oran
        60-90 deg        0.998       1.02      0.98
        90-120           1.007       1.07      0.94
        120-150          1.073       1.26      0.85
        150-180          1.481       1.66      0.89
      -> `dedektor_k` (0.85-0.95) YOLO kutusunun gercek siluetten daha SIKI
         olmasini temsil eder; kanat uclari ince oldugu icin kutuya tam
         girmiyor. Varsayilan 1.0 = saf geometri.

    ⚠ KALIBRASYON VERISININ TUZAGI: MENZIL_PX_M=202.6 TAMAMEN kuyruk takibi
      verisinden (aspect 138-166 deg) cikarilmisti; orada L ~ 1.5-1.7 m.
      Bordadan gorulen hedefte L 1.10'a DUSER, yani sabit carpan menzili
      orada %35-50 FAZLA sayar. Yon isareti eski notun TERSIDIR.
    """
    s, c = abs(math.sin(aspect_rad)), abs(math.cos(aspect_rad))
    return dedektor_k * max(kanat_m * c, uzunluk_m * s)


def aspect_kutudan(w, h, kanat_m=TALON_KANAT_M, uzunluk_m=TALON_UZUNLUK_M,
                   yukseklik_m=TALON_YUKSEKLIK_M):
    """Kutunun EN-BOY oranindan aspect (rad). ⚠ ZAYIF — yalnizca teshis icin.

    TURETME. Yatay aciklik L(a) = max(b|cos a|, l|sin a|), dikey aciklik
    yaklasik SABIT (kanat kalinligi + v-tail) = k. Oran:
        w/h = L(a)/k   =>   q = k*(w/h) = max(b|cos a|, l|sin a|)
    L(a) [0, pi/2]'de MONOTON DEGILDIR: a=0'da b (1.78), a=58.3 deg'de
    minimum b*cos(58.3) = 0.935, a=90'da l (1.10). Yani ayni q IKI aspect'e
    karsilik gelebilir. Kuyruk takibi baskin oldugu icin (olculen: karelerin
    %77'si aspect 150-180) `q >= b*cos(a_kesisim)` dalinda, yani KANAT
    dalinda cozulur:
        |cos a| = q/b   =>   a = acos(clamp(q/b, 0, 1))
    q < 0.935 (iki dalin da altinda) ise None.

    ⛔ OLCULDU: gercek veride bu kestirim ZAYIF. Kutu yuksekligi sabit degil
      (std(log(R*h)) = 0.473 iken std(log(R*w)) = 0.366) -- hedefin YATISI ve
      dikey aspect'i h'yi buyutuyor. MENZIL MODELINDE KULLANMAYIN.
    """
    if h <= 1e-6 or w <= 1e-6:
        return None
    q = yukseklik_m * (w / h)
    a_kes = math.atan2(kanat_m, uzunluk_m)          # dallarin kesistigi aci
    q_min = kanat_m * math.cos(a_kes)
    if q < q_min or q > kanat_m:
        return None
    return math.acos(kirp(q / kanat_m, 0.0, 1.0))


# ── DoW kadrajinin YASA cercevesindeki siniri (kirpilma kapisi) ──
# DoW 1920x1080 karesi yasa cercevesine dogrusal olceklendiginde:
KADRAJ_U0 = CX - FX * (DOW_GEN / 2.0) / FX_DOW      #  18.9
KADRAJ_U1 = CX + FX * (DOW_GEN / 2.0) / FX_DOW      # 621.1
KADRAJ_V0 = CY - FY * (DOW_YUK / 2.0) / FX_DOW      #  70.7
KADRAJ_V1 = CY + FY * (DOW_YUK / 2.0) / FX_DOW      # 409.3


def kutu_kirpik(cx, cy, w, h, pay_px=2.0):
    """Kutu DoW kadrajinin kenarina DEGIYOR mu (yani gercek boyut kesilmis mi)?

    NEDEN ONEMLI: kenara degen kutuda w/h hedefin GERCEK acisal boyutu
    DEGILDIR, kadrajin kestigi kadaridir. Menzil kalibrasyonunda bu kareler
    menzili SISTEMATIK OLARAK BUYUK gosterir (boyut kucuk -> R = k/boyut
    buyuk) ve yakin menzilde en cok onlar bulunur.
    ⇒ Menzil sabiti kalibre edilirken kirpik kareler ATILMALIDIR; yasa
      calisirken ise atilmaz (kutu yine de yon bilgisi tasir) ama menzile
      GUVENILMEZ (bkz. rapor, "kirpilma" satiri).
    """
    return (cx - w / 2.0 <= KADRAJ_U0 + pay_px or
            cx + w / 2.0 >= KADRAJ_U1 - pay_px or
            cy - h / 2.0 <= KADRAJ_V0 + pay_px or
            cy + h / 2.0 >= KADRAJ_V1 - pay_px)


def menzil_belirsizlik(R, w, h, sigma_px=1.0):
    """Menzil kestiriminin 1-sigma belirsizligi (m), iki kaynaktan.

    TURETME. R = L/delta ve delta = s/FX (s = piksel boyutu) ise
        dR/R = -ds/s        (piksel gurultusu)   ve   dR/R = dL/L  (boyut modeli)
    Bagimsiz varsayilirsa
        sigma_R / R = sqrt( (sigma_px/s)^2 + (sigma_L/L)^2 )

    sigma_px: dedektor kutu kenari gurultusu (px). sigma_L/L: aspect
    bilinmiyorsa L 1.10 .. 2.04 m arasinda gezer -> ortalama 1.45,
    yari-genislik 0.47 -> duzgun dagilimda sigma/L = 0.47/(sqrt(3)*1.45) = 0.187.
    Yani ASPECT BILINMEDIGINDE menzil hatasinin TABANI %19'dur; piksel
    gurultusu 30 px'lik kutuda yalnizca %3.3 katar.
    ⇒ Menzili iyilestirmenin yolu daha iyi piksel DEGIL, aspect bilgisidir.
    """
    s = math.sqrt(max(w, 1e-9) * max(h, 1e-9))
    rel_px = sigma_px / max(s, 1e-9)
    rel_L = 0.187
    return abs(R) * math.sqrt(rel_px * rel_px + rel_L * rel_L)


# ══════════════════════════════════════════════════════════════════════════
#  3. KUTUDAN IRTIFA FARKI (Delta-z)
# ══════════════════════════════════════════════════════════════════════════

def irtifa_farki(cx, cy, roll, pitch, menzil_m, tilt_deg=KAMERA_TILT_DEG):
    """Hedefin bize gore DUNYA cercevesindeki irtifa farki (m, + = hedef YUKARIDA).

    TURETME. Seviye cercevesindeki yukselis `el` ve menzil R ile
        dz = R * sin(el)          (yatay ayrim = R * cos(el))
    `el` los_seviye()'den gelir; yani roll VE pitch tam telafi edilir.

    ★ ROLL TELAFISININ OLCULEN KATKISI (n=20.944, truth menzille):
        yatis bandi   roll YOK   roll VAR   kazanc
        0-10 deg        0.72       0.50     0.23 deg
        10-20 deg       1.89       0.56     1.33 deg
        20-30 deg       8.87       3.03     5.84 deg
        TERMINAL        0.80       0.43     0.37 deg
      Metreye cevirisi (irtifa farkinda, MENZIL truth verilirken):
        C1 duzlem elev |med| 0.19 m  ->  C2 seviye elev |med| 0.10 m
        (p95: 0.89 m -> 0.51 m)
      Menzil de kutudan gelince hata MENZIL HATASININ egemenligine giriyor:
        C3 0.57 m -> C4 0.48 m (p95 4.10 -> 3.89 m)
      ⇒ Dikey kanalda bagli kisit ARTIK ACI DEGIL MENZILDIR.
    """
    _, el = los_seviye(cx, cy, roll, pitch, tilt_deg)
    return menzil_m * math.sin(el)


def irtifa_farki_telafisiz(cy, pitch, menzil_m, tilt_deg=KAMERA_TILT_DEG):
    """bbox_ibvs:1410'un yaptigi: dz = R*sin(piksel_elev(cy) + pitch). ROLL YOK.

    Kiyas tabani. Iki hata kaynagi birden tasir:
      (a) roll hic cikarilmaz,
      (b) piksel_elev DUZLEMSEL, cx != CX'te kuresel yukselisi asar.
    """
    return menzil_m * math.sin(piksel_elev(cy, tilt_deg) + pitch)


# ══════════════════════════════════════════════════════════════════════════
#  3b. TAM DURUM KESTIRIMI  —  kutudan IRTIFA + HIZ + YON + ACI
# ══════════════════════════════════════════════════════════════════════════
# ⛔ BU BOLUM NEDEN VAR: kullanicinin istegi "bbox'tan TAM hesaplama --
#    irtifa, hiz, yon, aci kestirimi" idi. Modulun geri kalani YON (azimut),
#    ACI (yukselis) ve MENZIL'i veriyordu; IRTIFA yalnizca skaler dz olarak,
#    HIZ ise HIC yoktu. Asagidaki dort fonksiyon zinciri o boslugu kapatir:
#
#        piksel + durus + menzil  ->  hedefin BAGIL NED KONUMU  (3B)
#        konumun ZAMAN TUREVI + ARACIN KENDI HIZI  ->  hedefin HIZI
#        hizdan  ->  hedefin ROTASI (kurs) ve YER HIZI
#
# ⚠ D0 (yarisma kurali) TEMIZ: girdiler yalnizca (a) tespit kutusu,
#   (b) aracin KENDI durusu ve KENDI hiz sensoru. Hedefin GPS'i HIC girmez.
#   Zaten girmesi de mumkun degil: fonksiyonlar saf, disari bakmiyor.
#
# ⚠⚠ HATA BUTCESI ONCEDEN SOYLENIR (olcum degil, TURETME -- olculmesi
#    kampanya kolunda yapilacak):
#      * TEGET bilesen (aciden gelir) IYIDIR: 1 derece aci hatasi 10 m'de
#        0.17 m konum hatasi.
#      * RADYAL bilesen (menzilden gelir) KOTUDUR: menzil hatasi %19 (aspect
#        tabani, bkz. menzil_belirsizlik) -> 10 m'de 1.9 m.
#      * VE MENZILDEKI SISTEMATIK YANLILIK TUREVDE AYNEN KALIR: R_kest =
#        (1+b)*R ise dR_kest/dt = (1+b)*dR/dt. MENZIL_PX_M=202.6'nin olculen
#        b=+%33'u, kapanma hizini da %33 buyuk gosterir. Yani menzil sabitini
#        duzeltmek YALNIZ menzili degil, HIZ KESTIRIMINI de duzeltir.
#        ⇒ Bu, recetedeki menzil kolunun IKINCI (ve bagimsiz) mekanizma
#          kapisidir: kest_vh_ms yanliligi menzil sabitiyle ORANTILI kaymali.


def hedef_ofset_ned(cx, cy, roll, pitch, yaw, menzil_m,
                    dpsi=0.0, tilt_deg=KAMERA_TILT_DEG):
    """★ Hedefin BIZE gore NED ofseti (N, E, D) metre. D ASAGI pozitif.

    TURETME. los_seviye SEVIYE cercevesinde (azimut BURNA gore, yukselis
    YUKARI pozitif) verir. Yaw eklenince azimut MUTLAK olur:
            psi = yaw + az
            N = R cos(el) cos(psi)
            E = R cos(el) sin(psi)
            D = -R sin(el)            [NED'de asagi pozitif -> yukari eksi]
    Buradan irtifa farki dogrudan  dz = -D = R sin(el)  (irtifa_farki ile
    BIREBIR ayni; birim test ikisini kilitler).

    ⚠⚠ `dpsi` — YAW BAYATLIGI. `cx, cy` karenin CEKILDIGI an (t-D) gecerlidir
    ve `roll, pitch` da o ana aittir; ama cagiran genellikle SIMDIKI yaw'i
    verir. Aradaki fark dpsi = yaw(t) - yaw(t-D) olculdu: medyan 4.27 deg,
    p90 13.05 deg (n=22058). `dpsi` verilirse yaw'dan CIKARILIR, yani
    kestirim karenin anina hizalanir. Verilmezse (0.0) cagiranin verdigi yaw
    aynen kullanilir -- bbox_ibvs'in bugunku komut yolunun yaptigi sey.
    ⇒ Bu, konum kestiriminin EN BUYUK tek hata kalemidir: 10 m menzilde
      4.27 derece bayatlik 0.74 m TEGET konum hatasi demektir; menzilin
      %19'luk radyal hatasindan (1.9 m) kucuk ama HIZ kestiriminde
      turevlendigi icin baskin hale gelir (asagi bak).

    ⚠ ROLL/PITCH bayatligi burada telafi EDILMEZ: onlar ayni kareden okunuyorsa
      zaten hizalidir. Cagiran onlari SIMDIKI IMU'dan veriyorsa ayni bayatlik
      dikey eksende de olusur; olculmedi. ÖLÇÜLMEDİ.
    """
    az, el = los_seviye(cx, cy, roll, pitch, tilt_deg)
    psi = sarmala_pi(yaw - dpsi + az)
    ce = math.cos(el)
    R = float(menzil_m)
    return (R * ce * math.cos(psi), R * ce * math.sin(psi), -R * math.sin(el))


def egim_pencere(ts, xs):
    """Pencere uzerinde EN KUCUK KARELER egimi (dx/dt). Ornek < 3 ise None.

    ⛔ NEDEN ARDISIK FARK DEGIL: ardisik fark gurultuyu sigma/dt ile buyutur.
    dt = 1/32 s ve 1 px jitter (menzilde ~0.2 m) 6.4 m/s SAHTE hiz uretir.
    Pencere egimi gurultuyu sqrt(N) kadar bastirir ve DUZENSIZ ornekleme
    araligina duyarsizdir (tespit kesintili gelir; bu depoda dt zaten
    duzensiz). Ayni teknik bbox_ibvs'de lambda-nokta ve eps-nokta icin
    ZATEN kullaniliyor -- ucuncu kez ayni kavram, ayni bicim.

    HATA (turetme): N ornek T pencereye duzgun yayilmissa
            Sum (t - t_ort)^2 ~ N T^2 / 12
            sigma_egim = sigma_x * sqrt(12/N) / T
    Sayilar (sigma_x = konum gurultusu):
        R=10 m, menzil hatasi %19 -> sigma_x 1.9 m, T=0.5 s, N=8
            -> sigma_v = 1.9*sqrt(1.5)/0.5 = 4.7 m/s   ⛔ RADYAL EKSENDE COP
        ayni pencerede aci hatasi 1 deg -> sigma_x 0.17 m
            -> sigma_v = 0.42 m/s                       ✔ TEGET EKSENDE IYI
    ⇒ Kutudan cikan hedef hizi TEGET yonde kullanilabilir, RADYAL yonde
      DEGIL. Pencereyi buyutmek radyali duzeltir ama hedefin manevrasini
      siler (olculen hedef donus hizi medyan 6.55 deg/s; 1 s pencerede
      6.5 derece kurs bulanikligi).
    """
    n = len(ts)
    if n < 3 or n != len(xs):
        return None
    tm = sum(ts) / n
    xm = sum(xs) / n
    sxx = sum((t - tm) ** 2 for t in ts)
    if sxx <= 1e-12:
        return None
    return sum((t - tm) * (x - xm) for t, x in zip(ts, xs)) / sxx


def hedef_hiz_ned(ts, ofsetler, v_kendi_ned):
    """★ Hedefin NED hizi (vN, vE, vD) — kutudan + ARACIN KENDI hizindan.

    TURETME (tek satir, ama kritik):
            p_hedef(t) = p_kendi(t) + ofset(t)
        ->  v_hedef    = v_kendi    + d(ofset)/dt
    Yani kutudan cikan sey hedefin hizi DEGIL, BAGIL hizdir; mutlak hiza
    cevirmek icin aracin KENDI hiz sensoru gerekir (D0 temiz: kendi sensor).

    ⛔ SIK YAPILAN HATA: "kutu buyuyor, demek hedef yaklasiyor" -> bu ancak
      BIZ dururken dogrudur. Kapanma hizi (bbox_ibvs'deki `kapanma`) BAGIL
      buyukluktur ve hedefin hizi hakkinda tek basina bir sey SOYLEMEZ.
      Bu fonksiyonun butun isi o iki kavrami ayirmaktir.

    ts        : pencere zaman damgalari (s)
    ofsetler  : ayni sirada (N, E, D) baglil ofsetler (m) -- hedef_ofset_ned
    v_kendi_ned: (vN, vE, vD) aracin KENDI hizi (m/s), pencerenin ORTASINDAKI
                 deger ideal; kalici rejimde son deger yeterli.
    Donus: (vN, vE, vD) veya ornek yetmezse None.

    ⚠ v_kendi SABIT varsayilir. Arac pencere boyunca ivmeleniyorsa (olculen
      tiklerin %84.5'i 12 m/s^2 tavaninda!) 0.3 s'de 3.6 m/s degisir ve
      kestirim o kadar kayar. ⇒ PENCEREYI KISA TUT ve tercihen v_kendi'yi de
      ayni pencerede ORTALA. ÖLÇÜLMEDİ: bu hatanin saha buyuklugu.
    """
    if len(ts) < 3 or len(ts) != len(ofsetler):
        return None
    dn = egim_pencere(ts, [o[0] for o in ofsetler])
    de = egim_pencere(ts, [o[1] for o in ofsetler])
    dd = egim_pencere(ts, [o[2] for o in ofsetler])
    if dn is None or de is None or dd is None:
        return None
    return (v_kendi_ned[0] + dn, v_kendi_ned[1] + de, v_kendi_ned[2] + dd)


def rota_ve_yer_hizi(vn, ve):
    """NED yatay hizdan (rota_rad, yer_hizi_ms). Rota KUZEYDEN saat yonunde.

    rota = atan2(vE, vN);  hiz = hypot(vN, vE).
    ⚠ Yer hizi kucukken rota TANIMSIZLASIR (gurultu 180 derece donduruyor).
      Cagiran hiz esigi koymali; olculen hedef seyir hizi 18 m/s oldugu icin
      3 m/s alti "rota bilinmiyor" saymak guvenlidir.
    """
    return math.atan2(ve, vn), math.hypot(vn, ve)


def aspect_hizdan(ofset_ned, hedef_hiz_ned_):
    """Hedefin ASPECT acisi (rad) — kutudan cikan hiz vektoruyle.

    aspect = (hedef -> BIZ) vektoru ile hedefin BURNU (hiz yonu) arasindaki
    aci; 180 deg = tam kuyrugunda, 90 = borda, 0 = karsidan.
    Bu, `gorunur_genislik_m`in girdisidir -- yani menzil modelinin
    L_etkin'ini KUTUDAN kapatmanin yolu buradan gecer.

    ⛔ ÇEMBERSEL BAGIMLILIK UYARISI: aspect -> L -> menzil -> ofset -> hiz ->
      aspect. Tek adimda cozulmez; ya sabit L ile baslatip BIR kez yinelenir
      ya da aspect ayri bir olcumden (kutu en-boy orani, ki OLCULDU: ZAYIF)
      gelir. Bu fonksiyon zincirin yalnizca bir halkasidir, cozucu DEGILDIR.
      ⇒ ÖLÇÜLMEDİ: yinelemenin yakinsayip yakinsamadigi.
    """
    vn, ve, _ = hedef_hiz_ned_
    if math.hypot(vn, ve) < 1e-6:
        return None
    rota = math.atan2(ve, vn)
    # hedeften BIZE bakan yon = ofsetin TERSI
    los_geri = math.atan2(-ofset_ned[1], -ofset_ned[0])
    return abs(sarmala_pi(los_geri - rota))


def durum_kestir(cx, cy, w, h, roll, pitch, yaw, menzil_m,
                 dpsi=0.0, tilt_deg=KAMERA_TILT_DEG):
    """Tek karelik TAM durum paketi (hizsiz) — irtifa + yon + aci + menzil.

    Donus sozlugu (hepsi SI / radyan):
        az, el      : SEVIYE cercevesinde kerteriz ve yukselis (burna gore)
        psi         : MUTLAK kerteriz (yaw + az, bayatlik cikarilmis)
        menzil_m    : verilen menzil (cagiran hangi modeli sectiyse)
        ofset_ned   : (N, E, D) bagil konum
        dz_m        : + = hedef YUKARIDA  (= -D)
        yatay_m     : yatay ayrim = R cos(el)
        sigma_R_m   : menzil 1-sigma belirsizligi (menzil_belirsizlik)
        kirpik      : kutu kadraj kenarina degiyor mu (menzil GUVENILMEZ)

    ⚠ HIZ BURADA YOK: hiz tek kareden CIKMAZ, pencere ister (hedef_hiz_ned).
      Bunu ayirmak bilerek: tek kare fonksiyonu SAF ve durumsuz kalir.
    """
    az, el = los_seviye(cx, cy, roll, pitch, tilt_deg)
    ofs = hedef_ofset_ned(cx, cy, roll, pitch, yaw, menzil_m, dpsi, tilt_deg)
    return {
        "az": az, "el": el,
        "psi": sarmala_pi(yaw - dpsi + az),
        "menzil_m": float(menzil_m),
        "ofset_ned": ofs,
        "dz_m": -ofs[2],
        "yatay_m": float(menzil_m) * math.cos(el),
        "sigma_R_m": menzil_belirsizlik(float(menzil_m), w, h),
        "kirpik": kutu_kirpik(cx, cy, w, h),
    }


# ══════════════════════════════════════════════════════════════════════════
#  4. BURUN YONELIMI  —  yaw yasasi + KARARLILIK
# ══════════════════════════════════════════════════════════════════════════

def yaw_acik_dongu_faz(k, w_rad_s, gecikme_s=None, tau_s=YAW_GECIKME_S):
    """Kerteriz dongusunun acik-dongu kazanc/fazi (kararlilik icin).

    MODEL — turetme:
      Kerteriz kinematigi bir INTEGRATORDUR: epsilon_dot = -omega_gövde + lambda_dot
      (burun donunce kerteriz hatasi ayni hizda kapanir). Kanal ise
      birinci mertebe gecikme + saf olu zaman:
            omega(s) / omega_cmd(s) = e^{-Td s} / (1 + tau s)
      Td  = dedektor gecikmesi (0.20 s, olculdu) + dongu ornekleme yarisi
            (1/(2*32.3) = 0.0155 s)
      tau = yaw takip gecikmesi (0.28 s, olculdu)
      Oransal yasa omega_cmd = k * epsilon ile acik dongu:
            L(s) = k * e^{-Td s} / ( s (1 + tau s) )

      |L(jw)| = k / (w * sqrt(1 + (tau w)^2))
      arg L   = -90 deg - atan(tau w) - Td*w  (radyan -> derece)

    Donus: (kazanc_buyuklugu, faz_derece)
    """
    if gecikme_s is None:
        gecikme_s = DEDEKTOR_GECIKME_S + 0.5 / DONGU_HZ
    w = max(w_rad_s, 1e-9)
    mag = k / (w * math.sqrt(1.0 + (tau_s * w) ** 2))
    faz = -90.0 - math.degrees(math.atan(tau_s * w)) - math.degrees(gecikme_s * w)
    return mag, faz


def yaw_kazanc_kararlilik(k, gecikme_s=None, tau_s=YAW_GECIKME_S):
    """Verilen kazanc icin (kesim frekansi, faz payi, kazanc payi).

    kesim  : |L| = 1 olan w_c   -> k = w_c*sqrt(1+(tau w_c)^2), tersi aranir
    faz payi: 180 + arg L(jw_c)
    kazanc payi: arg L = -180 olan w_180'de 1/|L(jw_180)|

    OLCULEN KANALLA SONUC (Td=0.2155 s, tau=0.28 s):
        k=1.0 -> w_c 0.93 rad/s, PM 60.1 deg
        k=1.4 -> w_c 1.24 rad/s, PM 49.0 deg
        k=2.0 -> w_c 1.65 rad/s, PM 34.9 deg
        k=2.6 -> w_c 2.02 rad/s, PM 23.6 deg
        k=3.4 -> w_c 2.44 rad/s, PM 11.0 deg
    (Sayilar bu fonksiyonun kendisiyle uretildi; sim/bbox_kontrol.py --kararlilik.)
    """
    if gecikme_s is None:
        gecikme_s = DEDEKTOR_GECIKME_S + 0.5 / DONGU_HZ
    lo, hi = 1e-4, 200.0
    for _ in range(200):                     # |L| w'de MONOTON AZALAN -> ikiye bolme
        mid = math.sqrt(lo * hi)
        if yaw_acik_dongu_faz(k, mid, gecikme_s, tau_s)[0] > 1.0:
            lo = mid
        else:
            hi = mid
    w_c = math.sqrt(lo * hi)
    pm = 180.0 + yaw_acik_dongu_faz(k, w_c, gecikme_s, tau_s)[1]
    lo, hi = 1e-4, 200.0                     # faz -180'i gectigi yer
    for _ in range(200):
        mid = math.sqrt(lo * hi)
        if yaw_acik_dongu_faz(k, mid, gecikme_s, tau_s)[1] > -180.0:
            lo = mid
        else:
            hi = mid
    w_180 = math.sqrt(lo * hi)
    gm = 1.0 / max(yaw_acik_dongu_faz(k, w_180, gecikme_s, tau_s)[0], 1e-12)
    return w_c, pm, gm


def yaw_kazanc_oner(faz_payi_deg=50.0, gecikme_s=None, tau_s=YAW_GECIKME_S):
    """Istenen faz payini veren EN BUYUK (en hizli) kazanc.

    PM kazancta MONOTON AZALAN oldugu icin ikiye bolme yeter.
    OLCULEN KANALDA: PM 60 -> k=1.00 ; PM 50 -> k=1.37 ; PM 45 -> k=1.55 rad/s.
    ⚠ AVCI_DPP_K=1.4 (mevcut varsayilan) tam da PM~49 deg'e denk geliyor --
      bagimsiz turetme mevcut ayarli degeri DOGRULUYOR.
    """
    lo, hi = 1e-3, 50.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if yaw_kazanc_kararlilik(mid, gecikme_s, tau_s)[1] > faz_payi_deg:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def yaw_kalici_hata(k, lambda_nokta_rad_s, ff=0.0):
    """Donen hedefte KALICI kerteriz hatasi (rad).

    TURETME. Kapali dongude epsilon_dot = -k*epsilon + (1-ff)*lambda_dot
    (ff = lambda_dot ileri beslemesinin orani). Denge:
            epsilon_ss = (1 - ff) * lambda_dot / k
    OLCULEN HEDEF DONUS HIZLARI (869 angajman): medyan 6.55, p90 32.0,
    p95 111.9 deg/s. k = 1.4 rad/s = 80.2 deg/s ile ff=0'da:
        medyan  4.7 deg   |  p90  22.9 deg  |  p95  80.1 deg
    p90'da 22.9 derece KALICI hata, kadraj yari-acisi 61 derece olsa bile
    terminal nisan icin kabul edilemez. ff=1.0 ile hata YAPISAL OLARAK 0'a
    iner -- `AVCI_DPP_FF=1.0`'in neden zorunlu oldugunun turetmesi budur.
    """
    return (1.0 - ff) * lambda_nokta_rad_s / max(k, 1e-9)


def yaw_komut(eps_rad, lambda_nokta=0.0, k=1.4, ff=1.0,
              gecikme_telafi_s=0.0, yaw_hizi=0.0, tavan_dps=YAW_TAVAN_DPS):
    """Yaw HIZ komutu (rad/s) — DPP(sigma) + lambda_dot ileri beslemesi.

        omega_cmd = k*(eps + gecikme_telafi*eps_dot_tahmini) + ff*lambda_dot
    Gecikme telafisi: dedektor gecikmesi Td boyunca kerteriz eps_dot ile
    kaymistir; olculen eps_dot ~ (lambda_dot - yaw_hizi). Bunu ileri sarmak
    Smith-tahmincisinin en yalin halidir.

    ⚠ NEDEN PN DEGIL -- UC BAGIMSIZ SEBEP:
      (1) PN a = N*V*lambda_dot ister; lambda_dot TUREVDIR ve 130-250 ms
          gecikmede gurultuyle patlar (olculen sisme 5.9x). sigma (piksel
          acisi) STATIK bir olcumdur, turev icermez, iris_yaw'a ihtiyac
          duymaz -> strapdown govde kuplaji YAPISAL OLARAK olusmaz.
          [Literatur: gövdeye sabit arayicida lambda_dot = eps_dot + omega
           olarak YENIDEN KURULUR ve olcek/gecikme hatasi "parasitic attitude
           loop" uretir -- Hong, Park, Lee, Ryoo, "Study on Parasite Effect
           with Strapdown Seeker in Consideration of Time Delay", JGCD 42(6),
           2019, DOI 10.2514/1.G004040; ayrica Willman, JGCD 11(3), 1988,
           DOI 10.2514/3.20294. Bizim olctugumuz "yaw bayatligi" (hatanin
           %81'i) tam olarak bu mekanizmanin ta kendisidir.]
      (2) DOYMA: a_max = 12 m/s^2 ile N=3'te ancak 10.6 deg/s LOS hizi
          servis edilir; olculen 50-100 deg/s.
      (3) YAKALANABILIRLIK: Guelman'in sonucu (IEEE T-AES AES-7(4), 1971,
          DOI 10.1109/TAES.1971.310406) MANEVRA YAPAN hedef icin
          nu = V_M/V_T > 2 VE N > 2 ister. Bizim hiz oranimiz 21.5/18.0
          = 1.19 -- yani nu > 2 kosulunun cok altinda. Hicbir N secimi bunu
          kurtarmaz; kuyrukta kapanma GEOMETRIK olarak kazanilamaz (olculen
          donus yaricaplari: bizim p5 27.7 m, hedefin 27.1 m).
      ⚠ Depo hafizasindaki "Guelman: gereken N > 1+mu = 1.83" ifadesi
        DOGRULANAMADI; birincil kaynaktaki kosul k = N-1 > 1, yani N > 2.
    """
    eps_ileri = eps_rad + gecikme_telafi_s * (lambda_nokta - yaw_hizi)
    w = k * eps_ileri + ff * lambda_nokta
    tav = math.radians(tavan_dps)
    return kirp(w, -tav, tav)


def donus_hizi_tavani(v_ms, max_accel=12.0):
    """HIZ VEKTORUNUN donebilecegi en yuksek hiz (rad/s) — burnun DEGIL.

    TURETME. Merkezcil: omega = a_yanal / V. a=12 m/s^2, V=18 m/s -> 0.667 rad/s
    = 38.2 deg/s. Olculen %99 donus hizi 37.9 deg/s -- BIREBIR ayni, yani
    baglayan sey aracin fizigi degil bu clamp'tir.

    ⚠ BU, YAW TAVANINDAN (120 deg/s) UC KAT KUCUKTUR. Burun hedefe 120 deg/s
      donebilir ama hiz vektoru 38 deg/s doner: yaw yasasini burun icin
      ayarlayip kesisimi hiz vektorunden beklemek yapisal hatadir.
    """
    return max_accel / max(v_ms, 1e-6)


# ══════════════════════════════════════════════════════════════════════════
#  5. IVME DAGITIMI  —  roll / pitch / itki + KAMERA kisiti
# ══════════════════════════════════════════════════════════════════════════

def ivme_tutum(a_n, a_e, a_d, yaw, g=G):
    """Istenen NED ivmesi -> (roll, pitch, itki_ivmesi, yatma_acisi) rad, m/s^2.

    TURETME (multirotor, itki govde -z boyunca):
        m*a = R*(0,0,-T) + m*g_ned ,  g_ned = (0,0,+g)   [NED: z ASAGI]
        => R*(0,0,-T)/m = u ,  u = (a_n, a_e, a_d - g)
      Yaw-hizali cerceveye donusturursek u_f = a_n cos(psi) + a_e sin(psi),
      u_r = -a_n sin(psi) + a_e cos(psi), u_d = a_d - g. ZYX ile
        Ry(th) Rx(ph) (0,0,-T) = (-T sin th cos ph, T sin ph, -T cos th cos ph)
      Esitleyerek:
        T/m   = |u|
        roll  = asin( u_r / |u| )
        pitch = atan2( u_f , g - a_d )        [ISARET: ileri ivme -> burun ASAGI]

    ⚠ ISARET: FRD'de pozitif pitch burun YUKARI'dir; ileri ivmelenmek icin
      pitch NEGATIF olur. Formul bunu dogrudan verir (atan2(u_f, g-a_d)'nin
      isareti ters alinmaz: u_f>0 -> pitch>0 gibi gorunur, o yuzden asagida
      ACIKCA eksi ile donduruluyor). Test: a_n=+5, yaw=0 -> pitch ~ -27 deg.
    """
    cp, sp = math.cos(yaw), math.sin(yaw)
    u_f = a_n * cp + a_e * sp
    u_r = -a_n * sp + a_e * cp
    u_d = a_d - g
    T = math.sqrt(u_f * u_f + u_r * u_r + u_d * u_d)
    if T < 1e-9:
        return 0.0, 0.0, 0.0, 0.0
    roll = math.asin(kirp(u_r / T, -1.0, 1.0))
    pitch = -math.atan2(u_f, max(g - a_d, 1e-6))
    yatma = math.acos(kirp(max(g - a_d, 0.0) / T, -1.0, 1.0))
    return roll, pitch, T, yatma


def kamera_bakis_acisi(pitch, tilt_deg=KAMERA_TILT_DEG):
    """Kameranin DUNYA cercevesindeki bakis yukselisi (rad).

        bakis = KAMERA_TILT + pitch
    Trim pitch -14.5 deg ile durgun bakis +10.5 deg. Bu, "kamera 25 derece
    yukari bakiyor, o yuzden hedefin altindan gitmek zorundayiz" gerekcesini
    buyuk olcude GECERSIZ kilar (olculdu, n=7569).
    """
    return math.radians(tilt_deg) + pitch


def yatay_ivme_tavani_kamera(a_d, bakis_min_deg=0.0, tilt_deg=KAMERA_TILT_DEG,
                             g=G):
    """Kamerayi ufkun uzerinde tutan EN BUYUK yatay ivme (m/s^2).

    TURETME. Kamera bakisi = tilt + pitch ve pitch = -atan(a_yatay/(g - a_d)).
    Bakis >= bakis_min istersek
        atan(a_yatay/(g - a_d)) <= tilt - bakis_min
        a_yatay <= (g - a_d) * tan(tilt - bakis_min)

    SAYILAR (a_d = 0, tilt = 25 deg):
        bakis_min =  0 deg -> a_yatay <= 4.57 m/s^2
        bakis_min =  5 deg -> a_yatay <= 3.60
        bakis_min = 10 deg -> a_yatay <= 2.63
    ⇒ common.py'nin "~5 m/s^2 ustunde gokyuzu arka plani kaybolur" notu
      BAGIMSIZ olarak bu turetmeden cikiyor. Ama yasanin MAX_ACCEL'i 12 m/s^2
      ve olculen tiklerin %84.5'i o tavanda -> kamera kisiti FIILEN HIC
      UYGULANMIYOR. Bu, split'in gerekcesi degil, split'in EKSIK yarisidir.
    """
    a = math.radians(tilt_deg) - math.radians(bakis_min_deg)
    if a <= 0.0:
        return float("inf")
    return max(g - a_d, 0.0) * math.tan(min(a, math.radians(89.0)))


def ivme_butce(a_n, a_e, a_d, a_yatay_max, a_dikey_max):
    """3B ivme talebini AYRI yatay/dikey tavanlara oturtur (yon korunur).

    ⛔ NEDEN TEK 3B TAVAN YANLIS: |a| <= A ile kirpmak, yatay talep buyukken
    dikeye KIRINTI birakir. Olculdu (14 ucus, 1970 tik): 8-15 m menzilde
    yatay 12.00 m/s^2 alirken dikeye kalan 0.22 m/s^2 -- terminal kapinin
    istedigi tirmanisin ~5'te 1'i.
    ⚙ FIZIK GEREKCESI (common.py:56-69 ile ayni): yatay ivmelenmek burnu eger
    ve KAMERAYI asagi cevirir; dikey ivmelenmek yalnizca itki artirir, kamera
    acisini HIC degistirmez. Iki eksenin kisiti FARKLI cinstendir; tek sayiyla
    ifade edilemez.

    Bu fonksiyon `common.limit_acceleration_split`in IVME (hiz degil) karsiligi:
    orada hiz komutunun DEGISIMI sinirlanir, burada dogrudan ivme vektoru.
    """
    h = math.hypot(a_n, a_e)
    if h > a_yatay_max and h > 0.0:
        s = a_yatay_max / h
        a_n, a_e = a_n * s, a_e * s
    a_d = kirp(a_d, -a_dikey_max, a_dikey_max)
    return a_n, a_e, a_d


def ivme_butce_kamerali(a_n, a_e, a_d, a_dikey_max, bakis_min_deg=0.0,
                        tilt_deg=KAMERA_TILT_DEG, a_yatay_tavan=None, g=G):
    """★ Kamera kisiti ve itki butcesini BIRLIKTE cozen dagitim.

    SIRA ONEMLI ve turetmesi su:
      1) DIKEY ONCE. Dikey ivme kamerayi hic bozmaz, o yuzden onun tavani
         yalnizca itki butcesidir. |a_d| <= a_dikey_max.
      2) YATAY SONRA, kalan kamera butcesiyle:
             a_yatay <= (g - a_d) * tan(tilt - bakis_min)
         Dikkat: dikey talep degistigi anda yatay tavan da degisir --
         tirmanirken (a_d < 0, NED'de yukari) g - a_d BUYUR, yani yatay
         butce ARTAR. Iki eksen bagimsiz DEGILDIR; tek 3B tavan bu bagi
         yanlis yonde kurar (yatayi buyutunce dikeyi kisar), dogrusu tersidir.
      3) Istege bagli sert yatay tavan (a_yatay_tavan) ile kesisim alinir.

    Donus: (a_n, a_e, a_d, tavan_yatay_kullanilan)
    """
    a_d = kirp(a_d, -a_dikey_max, a_dikey_max)
    tav = yatay_ivme_tavani_kamera(a_d, bakis_min_deg, tilt_deg, g)
    if a_yatay_tavan is not None:
        tav = min(tav, a_yatay_tavan)
    h = math.hypot(a_n, a_e)
    if h > tav and h > 0.0:
        s = tav / h
        a_n, a_e = a_n * s, a_e * s
    return a_n, a_e, a_d, tav


# ══════════════════════════════════════════════════════════════════════════
#  6. TUR-DONUSU / TUTARLILIK KONTROLLERI (test ve tezgah kullanir)
# ══════════════════════════════════════════════════════════════════════════

def tutarlilik_raporu():
    """Modulun kendi ic tutarliligini SAYIYLA dondurur (assert etmez).

    Testler bunu kilitler; tezgah da her taramadan once cagirir ki sessiz bir
    regresyon "yasada bug" gibi gorunmesin (sim/tesis.dogrula ile ayni ders).
    """
    r = {}
    r["FX"] = FX
    r["FX_DOW"] = FX_DOW
    r["olcek"] = OLCEK_DOW_YASA
    # 1) tur-donusu: elev_piksel(piksel_elev(cy)) == cy
    hata = 0.0
    for cy in range(150, 460, 7):
        hata = max(hata, abs(elev_piksel(piksel_elev(float(cy))) - cy))
    r["turdonus_px"] = hata
    # 2) roll=pitch=0 ve cx=CX'te los_seviye == piksel_elev
    d = 0.0
    for cy in range(150, 460, 7):
        _, el = los_seviye(CX, float(cy), 0.0, 0.0)
        d = max(d, abs(el - piksel_elev(float(cy))))
    r["seviye_vs_duzlem_merkez_deg"] = math.degrees(d)
    # 3) merkezden uzakta DUZLEM ile KURESEL ayrisir (olculu fark)
    _, el_k = los_seviye(CX + 250.0, 301.0, 0.0, 0.0)
    r["duzlem_kuresel_fark_deg"] = math.degrees(piksel_elev(301.0) - el_k)
    # 4) seviye hedef pikseli
    r["cy_seviye"] = elev_piksel(0.0)
    # 5) off-axis sisme kontrolu: ayni acisal boyut, iki farkli yer
    dy0, _ = acisal_boyut(CX, CY, 30.0, 20.0)
    dy1, _ = acisal_boyut(CX + 250.0, CY, 30.0, 20.0)
    r["offaxis_sisme"] = dy0 / dy1 if dy1 > 0 else float("nan")
    return r


# ══════════════════════════════════════════════════════════════════════════
#  EK: ENTEGRASYON DURUMU  (2026-08-18 -- GUNCELLENDI, artik UYGULANDI)
# ══════════════════════════════════════════════════════════════════════════
# ⛔ ONCEKI SURUM BURADA "HENUZ UYGULANMADI" YAZIYORDU -- O ARTIK YANLIS.
#    Asagisi bbox_ibvs.py'nin GERCEK halini yansitir. Bir sonraki okuyucu
#    icin: kapiyi kodda `grep -n "AVCI_IBVS_" bbox_ibvs.py` ile dogrula,
#    bu yorumun dogru oldugunu VARSAYMA (bu blok bir kez bayatladi bile).
#
# ── UYGULANMIS KAPILAR (hepsi env, hepsi VARSAYILAN KAPALI/BIT-AYNI) ──────
#   Y2  AVCI_IBVS_KOMUT_HIZALA      (0.0)   bbox_ibvs.py:330
#         -> yaw_cmd (:1477), PN tabani (:1556), DPP _los_kert (:1607)
#            UCUNE BIRDEN bagli. "Yarim baglama" hatasi TEKRARLANMADI.
#         ⚠ `hiz_yonu`nun saf-takip dalina BILEREK dokunulmadi: orada
#            SONUM_T=0.30 zaten ayni telafinin kaba hali.
#   M-KAL AVCI_IBVS_MENZIL_PX       (202.6) :772   yasanin menzili
#         AVCI_IBVS_MENZIL_TERM_PX  (160.0) :781   terminal nisan kapisi
#         AVCI_IBVS_MENZIL_KW       (0.0)   :786   K_w/w modeli
#         AVCI_IBVS_MENZIL_OFS      (0.0)   :791   additif pay c
#         -> TEK fonksiyon: menzil_kutudan() / menzil_olcek()
#   T1b AVCI_IBVS_DIKEY_ROLL        (0)     :1020  TUTUS dikey kanali
#   T1c AVCI_IBVS_TERM_ROLL         (0)     TERMINAL dikey kanali  ← YENI
#   KES AVCI_IBVS_KESTIRIM          (0)     tam durum kestirimi    ← YENI
#
# ── SIRA HALA ZORUNLU ─────────────────────────────────────────────────────
#   1. AVCI_IBVS_KOMUT_HIZALA=0.20      (yaw bayatligi -- hatanin %81'i)
#   2. AVCI_IBVS_DIKEY_ROLL=1 + AVCI_IBVS_TERM_ROLL=1
#   3. AVCI_IBVS_MENZIL_* duzeltmesi
#   ⚠ TERSI SIRA OLMAZ: roll telafisi BAYAT tutumla uygulandiginda YATAY
#     hatayi BUYUTUYOR (olculdu: ham 4.45 -> telafili 5.45 deg; hizalama
#     acikken 1.74 -> 1.29 deg). Isaret kapiya BAGLI.
#
# ⛔⛔ BEKLENEN SAHA KAZANCI HALA KANITLANMADI. Kapali cevrim tezgahi
#   (sim/deney.py, degistirilmemis yasa, n=40/kol) HICBIR kolda iyilesme
#   gostermedi. Kanitlanan tek sey OLCUM KALITESIDIR. Sahada A/B ile
#   kanitlanmadan hicbiri varsayilan ACIK yapilmamalidir.

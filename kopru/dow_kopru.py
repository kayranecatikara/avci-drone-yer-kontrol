# -*- coding: utf-8 -*-
"""
================================================================================
kopru/dow_kopru.py — Gazebo/ArduPilot GPS gudumunu DoW SDK'sina baglayan kopru
================================================================================
FAZ 2 DURUMU: DIKEY (TRIM+PI, olculdu) + YAW (P + kacak kirpma, olculdu) +
YATAY (trim ileri-besleme + PI; ADIM 1-4 olcumleri surauyor). YATAY_AKTIF
varsayilani False — olcum scriptleri ve Faz 3 calistiricisi acikca True yapar;
bayrak kapaliyken pitch/roll yalniz PITCH_SABIT/ROLL_SABIT kancalaridir.

MIMARI (kaynak: GUDUM_TASIMA/dow_kopru.py on taslagi):

    DoW telemetri --[get_iris/get_plane]--> gps_guidance.py (DOKUNULMAZ)
                                                 |
                                     send_velocity(conn=kopru, vx,vy,vz,yaw)
                                                 |   (yalniz SETPOINT yazar)
    DoW set_control_surfaces <--[adim() @ LOOP_HZ ic dongu]-- kontrolculer

ON TASLAKTAN FARKLAR (gerekceli):
 1) IC DONGU eklendi (dongu_baslat/adim): taslak yalniz send_velocity aninda
    kosuyordu (gudum 20 Hz). (a) BAYAT_S korumasi OLU KODDU — _t_sp her cagrida
    tazelendigi icin kosul hicbir zaman tutamazdi; (b) MAX_DELTA=0.05 slew'i
    50 Hz'e gore kanitli (ana_kontrol.py:240), 20 Hz'te yari hizda kalirdi;
    (c) SDK_README:59 kontrol dongusu icin 50 Hz oneriyor. Simdi send_velocity
    SADECE setpoint yazar; kontrol LOOP_HZ=50'de ayri kosar -> bayat korumasi
    GERCEK, slew/kazanc semantigi ana_kontrol ile ayni.
 2) get_iris PITCH ISARETI DUZELTILDI (taslak -pitch veriyordu): DoW telemetri
    pitch'i burun-asagi NEGATIF (canli log kaniti: ileri itkide govde -37 deg;
    ana_kontrol ego-pitch telafisi bu isaretle calisiyor, CLAUDE.md 2026-07-09).
    NED pitch de burun-yukari POZITIF -> isaret AYNEN GECER. (Bu alanlar yalniz
    kadraj OLCUMUNE girer, komut yoluna girmez; roll/pitch konvansiyonu simde
    truth ile tam dogrulanmadi — "Blokor B", MEVCUT_DURUM.md.)
 3) Dikey kazanclar ana_kontrol'un UCUSTA KANITLI ic hiz dongusunden birim
    cevrimiyle alindi (guidance/ana_kontrol.py:212-217, cm -> m x100):
       KV_Z    0.00220 thr/(cm/s) -> KP_VZ   0.22 thr/(m/s)
       KI_Z_VEL 0.00150           -> KI_VZ   0.15
       INT_Z_AUTH 0.60            -> I_VZ_MAX 0.60
 4) Yaw kanali ana_kontrol'un kanitli degerleriyle: KP_YAW=1.3 (:225),
    YAW_DEADBAND=3 deg (:245), YAW_MAX=0.60 (:235). Kacak korumasi (uzerinde
    calisilan hatayi +-90 dege kirp) taslaktan aynen.
 5) OLCUM KANCALARI (yalniz kopru/olcum_faz1.py kullanir; varsayilan KAPALI ->
    davranis degismez): Cfg.PITCH_SABIT (sabit pitch enjeksiyonu),
    Cfg.YAW_SABIT (acik-dongu yaw kalibrasyonu), son_tani sozlugu (CSV log).
 6) HIZ_KAYNAK anahtari: dikey geri besleme "sdk" (telemetri velocity vektoru)
    veya "sonlu_fark" (irtifa turevi + EMA; ana_kontrol._own_dikey_hiz deseni,
    :757-771). Iki kestirim HER tik hesaplanir (log ikisini de gorur); hangisi
    KOMUTA girer bu anahtar secer. Karar OLCUMLE verilecek (hizkaynak modu).

CERCEVE SOZLESMESI — TEK yerde tanimli, cikis girisin tam tersi:
    NED_x (Kuzey) =  DoW_x
    NED_y (Dogu)  = -DoW_y
    NED_z (Asagi) = -DoW_z       det(diag(1,-1,-1)) = +1  (sag-el korunur)
    yaw_NED       = -yaw_DoW
DAYANAK (Faz 0 dogrulamasi, REPO satirlari):
    guidance/ana_kontrol.py:516-521  world_to_body: "RH, z-up, yaw CCW, burun=+x"
                                     e_fwd = ex*c + ey*s ; e_right = ex*s - ey*c
    guidance/ana_kontrol.py:113-120  ROT_IN_DEGREES=True; 4 isaret +1 (ucusta)
    guidance/ana_kontrol.py:228-240  PITCH/ROLL_MAX=0.75, YAW_MAX=0.60,
                                     THR_UP=0.70, THR_DN=-1.00, MAX_DELTA=0.05
    sdk/drone_sdk.py:124-137         konum cm, hiz cm/s, rotasyon (roll,pitch,yaw)
    SDK_README.md:78-95              +-1.0 = 60 deg yatis; throttle ASIMETRIK:
                                     +1 tirman (33.3 m/s tavan), 0 hover,
                                     -1 yercekimi telafisi kapali (serbest dusus)

ISARET TUZAGI (dikey): NED vz ASAGI pozitif, DoW throttle YUKARI pozitif.
Kod boyunca "vz_up" adiyla yukari-pozitif ara degisken kullanilir.
"""

from __future__ import annotations

import collections
import math
import os
import threading
import time

# ── Sabitler ────────────────────────────────────────────────────────────────
CM = 100.0                          # DoW cm -> m bolucusu
TIRMANMA_MAX_MS = 120.0 / 3.6       # 33.33 m/s @ throttle +1.0 (SDK_README:81)


def _env_f(ad: str, vars: float) -> float:
    """Env'den float oku (gps_guidance.py'deki desenin aynisi).
    Cfg SINIF TANIMINDA okunur -> import'tan ONCE set edilmeli."""
    try:
        return float(os.environ.get(ad, vars))
    except (TypeError, ValueError):
        return vars


def sarmala_pi(a: float) -> float:
    return (a + math.pi) % (2.0 * math.pi) - math.pi


def kirp(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else (hi if x > hi else x)


def rate_limit(hedef: float, onceki: float, max_delta: float) -> float:
    """ana_kontrol.py:512-513 ile ayni (tik basina max degisim)."""
    return onceki + kirp(hedef - onceki, -max_delta, max_delta)


def dunya_to_govde(ex: float, ey: float, yaw_dow_rad: float):
    """ana_kontrol.py:515-521'in birebir kopyasi. DoW z-up / yaw-CCW icin dogru;
    NED'de e_right'in isareti ters olurdu — o yuzden once DoW'a cevrilip
    burada dondurulur (yatay kanal kullanir)."""
    c, s = math.cos(yaw_dow_rad), math.sin(yaw_dow_rad)
    e_fwd = ex * c + ey * s
    e_right = ex * s - ey * c
    return e_fwd, e_right


def yatay_trim_stick(v_ms: float, noktalar) -> float:
    """Hiz (m/s) -> yatis stick'i trim ILERI-BESLEMESI (THR_TRIM'in yatay emsali).

    Isaretli/simetrik: |v| tabloda parcali-dogrusal interpolasyon; son noktadan
    sonra SON parcanin egimiyle ekstrapolasyon (cikis ayrica PITCH/ROLL_MAX'a
    kirpilir). Tablo: ((hiz_ms, stick), ...) artan hizla sirali."""
    a = abs(v_ms)
    isaret = 1.0 if v_ms >= 0.0 else -1.0
    n = noktalar
    if a <= n[0][0]:
        return isaret * n[0][1]
    for i in range(1, len(n)):
        if a <= n[i][0]:
            v0, s0 = n[i - 1]
            v1, s1 = n[i]
            return isaret * (s0 + (s1 - s0) * (a - v0) / (v1 - v0))
    v0, s0 = n[-2]
    v1, s1 = n[-1]
    return isaret * (s1 + (s1 - s0) * (a - v1) / (v1 - v0))


# ── Cerceve donusumu: TEK yerde, cift yonlu, birim testli ───────────────────

def dow_to_ned_vek(v_dow):
    """DoW dunya (z-YUKARI) -> NED. Konum ve hiz icin ayni (olcek haric)."""
    return (v_dow[0], -v_dow[1], -v_dow[2])


def ned_to_dow_vek(v_ned):
    """Tersi — diag(1,-1,-1) kendi tersidir: ned_to_dow(dow_to_ned(v)) == v."""
    return (v_ned[0], -v_ned[1], -v_ned[2])


def dow_yaw_to_ned(yaw_dow_rad: float) -> float:
    return sarmala_pi(-yaw_dow_rad)


def ned_yaw_to_dow(yaw_ned_rad: float) -> float:
    return sarmala_pi(-yaw_ned_rad)


# ── Ayarlar ────────────────────────────────────────────────────────────────

class Cfg:
    # ── Zarf (SDK sabiti + ana_kontrol'de ucusta dogrulanmis) ──
    PITCH_MAX = 0.75          # 0.75 * 60 = 45 deg
    ROLL_MAX = 0.75
    # (YAW_MAX asagida, yaw bolumunde: 0.85 — 2026-08-06 olcumuyle guncellendi)
    THR_UP = 0.70             # ana_kontrol.py:230
    THR_DN = -1.00            # ana_kontrol.py:231 (eski -0.40 lift-carry'ye yenildi)
    MAX_DELTA = 0.05          # komut/tik @ LOOP_HZ=50 (ana_kontrol.py:240)
    LOOP_HZ = 50.0            # ic dongu; gudum 20 Hz setpoint yazar (SDK_README:59)

    # ── FAZ BAYRAGI ──
    YATAY_AKTIF = False       # Varsayilan KAPALI; olcum scriptleri ve Faz 3
                              # kosucusu acikca True yapar (tek satir geri-donus).

    # ── NED DUSEY ORIJIN KAYDIRMASI (Faz 3.1 guvenligi) ──
    # gps_guidance'in yere-cakilma korumasi (LOOKUP_MIN_ALT=8, :414) NED z'sinin
    # ZEMIN ~ 0 oldugu Gazebo'ya gore tasarlandi. DoW'da zemin DUNYA-Z ~48.4 m'de
    # -> kaydirmasiz koruma calismaz (hedef 5 m AGL'ye inerse istasyon ~2 m
    # AGL'ye kurulur). Adaptor NED z = -(dow_z - NED_ZEMIN_M) verir: yasanin
    # gordugu "irtifa" = AGL, Gazebo konvansiyonunun birebiri. YASA DEGISMEDI —
    # cerceve tanimi ceviri katmaninin isidir. 0 = eski davranis (birim testler).
    NED_ZEMIN_M = 0.0

    # ── DIKEY: vz -> throttle (asimetrik kanal; TRIM + PI + ileri besleme) ──
    # Kazanc kaynagi: ana_kontrol ic hiz dongusu (:212-217), cm->m cevrimi.
    KP_VZ = 0.22              # thr per (m/s) hiz hatasi
    KI_VZ = 0.15              # thr per (m/s * s) — kalan yanliligi kapatir
    I_VZ_MAX = 0.60           # integral yetki tavani (INT_Z_AUTH aynasi)
    FF_VZ = 1.0 / TIRMANMA_MAX_MS   # ileri besleme (tirmanma tarafi lineer varsayimi)
    # HOVER DENGE GAZI — OLCULDU (2026-08-06 dikey kosusu, kopru_olcum_dikey CSV):
    # SDK dokumani "thr 0 = hover" DIYOR ama olcum baska soyluyor:
    #   thr -0.38 -> +1.4 m/s tirmanis; thr -0.617 -> -0.18 m/s (denge ~ -0.60);
    #   hover1/hover2 oturmus thr -0.62..-0.66. TRIM'siz halde integrator -0.60
    #   tavanina KILITLENIYORDU (yetkinin tamamini sabit yanlilik yiyordu).
    # ana_kontrol'un "tirmanma yanliligi" savasinin ayni koku; FF olarak eklenir,
    # integrator yalniz ARTIGI kapatir.
    THR_TRIM = -0.60
    HIZ_KAYNAK = "sonlu_fark" # "sonlu_fark" | "sdk" — komuta giren vz olcumu.
                              # OLCUMLE SECILDI (2026-08-06): SDK velocity z'de
                              # +0.27 m/s SABIT yanlilik var (uc segmentte vz_sdk,
                              # gercek irtifa egiminden hep +0.25..0.30 fazla);
                              # sonlu_fark irtifa egimiyle +-0.03 uyumlu. Ayrica
                              # KP_VZ/KI_VZ zaten sonlu-fark geri beslemeli
                              # ana_kontrol dongusunden alinmisti (ayni duzen).

    # ── ATTITUDE ISARETI: DoW rotation -> NED/FRD ──────────────────────────
    # ⛔ DUZELTME 2026-08-13. Denetimde (docs/kopru_denetim.md B5-roll) OLCULDU
    # ama duzeltilmemisti: "etkisi kucuk, roll yalniz kadraj OLCUMUNE giriyor".
    # ARTIK GECERSIZ — yeni gorsel yasa (bbox_ibvs, dal HEAD) roll'u KOMUTA
    # sokuyor: bbox_ibvs.py:943 iris["roll"] -> los_seviye() -> T1a yatay
    # roll/pitch telafisi, ve T1a VARSAYILAN ACIK (ROLL_TELAFI=True; kaynagin
    # M1 kampanyasinda ucusta dogrulanmis ozelligi). Kurtarma.guncelle() de
    # ayni roll'u okur.
    # KANIT (U kosusu, oturmus faz, n=984): korelasyon(stick, bildirilen roll)
    #   = -0.965; SOLA yatis komutunda (stick<0, n=733) DoW +4.70 deg bildiriyor.
    #   NED/FRD'de sol kanat asagi = NEGATIF => DoW roll = -NED roll.
    #   (Pitch farkli: -0.843 korelasyon + bagimsiz sinama (artik 0.39 deg ↔ ters
    #   hipotez 24.40 deg) pitch'in AYNEN gectigini dogruladi — ona DOKUNULMAZ.)
    # ETKI (olculdu, bbox_ibvs.los_seviye ile): ters isaretle yaw komutunda
    #   14.6 deg'e kadar TERS YONDE hata (yatis 20 deg, hedef kadraj kenarinda).
    #   Yani T1a salinimi azaltmak yerine ARTIRIRDI.
    # GERI DONUS: AVCI_KOPRU_ROLL_ISARET=1 -> eski (duzeltilmemis) davranis.
    ROLL_ISARET = _env_f("AVCI_KOPRU_ROLL_ISARET", -1.0)
    PITCH_ISARET = 1.0        # AYNEN gecer (yukarida kanit) — knob YOK

    # ── YATAY: hiz -> yatis stick'i = TRIM ILERI-BESLEME + PI (Faz 2) ──
    # ESKI YAKLASIM IPTAL (2026-08-06, olcum curuttu): ArduCopter'dan turetilen
    # KP_V=2.0 + aci=atan(a/g) modeli "45 deg ~ 18 m/s" tesisi varsayiyordu;
    # OLCUM 18 deg yatisin 26.2 m/s verdigini gosterdi (derece basina 3-4x
    # hizli tesis, dusuk surukleme) -> ayni kazanc ASMA yapar. Yerine dikeyde
    # ise yarayan yapi (THR_TRIM emsali): sabit calisma noktasi integratore
    # KOVALATILMAZ, ILERI BESLENIR:
    #     stick = yatay_trim_stick(v_sp) + KP_VH*e_v + i
    # (hiz m/s, stick) noktalari — isaretli/simetrik, aralar dogrusal, son
    # noktadan sonra son egimle ekstrapolasyon.
    # OLCULDU (2026-08-06, kopru_olcum_f2trim_pitch, ADIM 2 taramasi):
    #   0.10->8.70  0.15->13.17  0.20->17.56  0.30->26.15  0.45->32.86 m/s
    #   Calisma bandinda (<=17.6) NEREDEYSE TAM DOGRUSAL: v = 87.8 * stick
    #   (dogrusal R2=0.962, kuadratik R2=0.987 — fark yalniz 33.3 m/s zarf
    #   tavaninin dayattigi son-nokta duzlesmesi). Beklenen kaba tablo alt ucta
    #   CURUTULDU (10 m/s ~0.05 degil ~0.115 stick).
    #   ROLL egrisi pitch'le BIREBIR (8.69/17.53/26.13; fark <%0.2, R2=0.9999)
    #   -> TEK tablo iki eksene de gecerli (f2trim_roll kosusu).
    YATAY_TRIM_NOKTA = ((0.0, 0.0), (8.7, 0.10), (13.2, 0.15),
                        (17.6, 0.20), (26.2, 0.30), (32.9, 0.45))
    KP_VH = 0.024             # stick per (m/s). Turetim: dv/dstick=87.8 olcumu ->
                              # bant 2.1 1/s. 0.018 DENENDI ve GERI ALINDI: asma
                              # 20.2->%23.7 BUYUDU — anatomi (f2adim CSV) sucluyu
                              # integrator windup'i gosterdi, P negatif-hata tarafinda
                              # SONUMDU; dusuk P sonumu zayiflatti.
    KI_VH = 0.012             # stick per (m/s*s) — trim egrisi artigi icin (tau_i ~2 s)
    I_VH_MAX = 0.15           # stick; integral yetkisi (doyumda DONUK, dikey emsali)
    E_VH_INT_BAND = 2.5       # m/s; integral YALNIZ |hata| bu bandin icindeyken birikir.
                              # OLCUMLE eklendi (2026-08-06 f2adim anatomisi): sert
                              # basamakta rampa boyunca biriken integral (+0.079 stick
                              # = ~7 m/s'lik trim fazlasi) hedef gecilirken stick'i
                              # trim ustunde tutuyordu -> %20-24 asma + 5 s'lik bosalma
                              # kuyrugu. Buyuk hatada P+FF yeter; i yalniz son kapanisi
                              # yapar. ana_kontrol dikey INT_Z_BAND'inin (:218) emsali.
    # YATAY GERI BESLEME = SDK velocity — OLCUMLE SECILDI (2026-08-06,
    # kopru_olcum_hizkaynak, hakem = katedilen yol/zaman 26.21 m/s):
    #   sapma  : sdk +0.36 m/s | sonlu-fark +2.68 m/s (gurultu dogrultmasi sisirir)
    #   gurultu: sdk std 0.28-0.34 | sonlu-fark 3.1-5.5 m/s (~15x)
    #   gecikme: 0-20 ms (rampa/birakma pencereleri, tepe korelasyon 0.89-0.93)
    # adim() yatay kanali v_dow'u (SDK velocity) kullanir.

    # ── YAW: mutlak aci -> donus hizi ──
    KP_YAW = 1.3              # stick per rad hata (ana_kontrol.py:225, kanitli)
    YAW_MAX = 0.85            # 0.60 -> 0.85 (2026-08-06 Faz 2 EK): olcum 143 deg/s
                              # per stick -> 0.85 ~ 121 deg/s = gps_guidance
                              # YAW_RATE_MAX=120 ile ESLESIR (0.60 yalniz ~86
                              # veriyordu; hizli kerteriz degisiminde gudum komutu
                              # onde birikirdi). ana_kontrol'un 0.60'i kamera
                              # bulanikligi icindi — bu hatta kamera YOK.
                              # Kacak/asma testi: olcum_faz2 yawtavan modu.
    YAW_DEADBAND = math.radians(3.0)   # ana_kontrol.py:245
    # KACAK KORUMASI: gps_guidance cmd_yaw'i kalici durum (:440-445), gercek
    # heading'e demirli degil; arac yetisemezse komut onde birikir (olculmus
    # tuzak: 1.0 tur yerine 7.4 tur). Uzerinde calisilan hata kirpilir.
    YAW_HATA_MAX = math.radians(90.0)

    # ── Bayat setpoint korumasi (gudum 20 Hz -> normal ara 0.05 s) ──
    # GORSEL fazda ayri esik (2026-08-10 olcumu; 0 = kapali, GPS esigi kullanilir).
    # 1.0 s: olculen gorsel komut araligi p99 = 1.23 s, MAX 1.45 s. Kayip
    # tespiti yasanin isi (supervisor 20 kare ~2 s), kopru onu beklemeli.
    # 2.5 s (2026-08-10 denetimi duzeltmesi): 1.0 kendi gerekcesinin ALTINDAYDI.
    # Olculen gorsel komut araligi p99 = 1.23 s, MAX 1.45 s; ayrica bbox_ibvs
    # wait_pose timeout'u 0.5 s dolunca HIC setpoint gondermiyor. Kayip karari
    # yasanin: supervisor KAYIP_M=20 kare @ ~8-9 FPS = ~2.2 s. Kopru onu
    # beklemeli, yoksa 1.0-1.45 s'lik dedektor bosluklarinda 18 m/s seyirde
    # tam fren yapip hedefi saniyede ~18 m aciyordu.
    BAYAT_S_GORSEL = 2.5
    BAYAT_S = 0.30            # bu surede setpoint gelmezse guvenli birakma:
                              # thr=0 (hover, irtifa korunur) + pitch/roll/yaw=0

    # ── Kalkis (ayri hat; ana_kontrol.py:1161-1168 deseni) ──
    KALKIS_THR = 0.60         # ana_kontrol TAKEOFF_THR (:131)
    KALKIS_TOL_M = 1.5

    # ── GNSS DUZELTICI (CT-EKF) — get_plane() zincirine takilir ──
    # Gazebo zincirinde bozuk hedef GPS'i guduume HAM girmez; pozisyon tabanli
    # CT-EKF'ten gecer. DoW koprusunde bu katman EKSIKTI (tasima eksigi, tasarim
    # tercihi degil) -> hedef konumu 1 s gecikmeli + (2,2,1) m offsetli geliyordu.
    # Bu KOPRU isidir (birim/cerceve cevirisiyle ayni katman); gps_guidance'a
    # DOKUNULMAZ, yasa CT-EKF'in ciktisini normal bir get_plane ciktisi gibi gorur.
    # Filtre: fusion/inovasyonlu_j_v2.GNSSDuzeltici (v2.1, repo icinde, uretimde).
    GNSS_DUZELTICI_AKTIF = True    # bayrak: False = ham konum (eski davranis, bit-ayni).
                                   # ACIK (2026-08-06, kullanici onayi + UCTAN UCA olcum):
                                   # yasanin GORDUGU konum hatasi medyani 25.67 -> 10.56 m
                                   # (-%59). Iki katman birbirini YEMIYOR (EMA'nin ekledigi
                                   # ~0.33 s gecikme olculdu; zincir optimumu 1.0-1.25'te
                                   # plato, 1.0 daha iyi p99/gurultu veriyor).
    GNSS_DT = 0.23            # s; filtre PREDICT adimi = OLCULEN taze paket araligi
                              # (2026-08-06: 345 paket/90 s, medyan 234 ms; oyunun
                              # bildirdigi rate_hz=5.0, dropout'lar etkin hizi dusuruyor).
                              # Filtrenin varsayilani 1.0'dir (Gazebo 1 Hz icindi).
    GNSS_TELAFI_SN = 1.0      # s; lead/gecikme telafisi. OYUNUN KENDI bildirdigi
                              # delay_s = 1.00 s (get_debug_truth corruption_params)
                              # + offline tarama ayni noktada tepe yapti (0.5->12.55,
                              # 1.0->10.14, 1.5->14.40 m konum hatasi).
                              # UCTAN UCA DOGRULANDI (2026-08-06): zincir (CT-EKF ->
                              # gps_guidance EMA) taramasi 1.00 -> 10.56 m ve 1.25 ->
                              # 10.55 m ile PLATO; 1.0 secildi (p99 56.1 vs 60.3, hiz
                              # gurultusu 8.8 vs 9.7 daha iyi) + oyunun bildirdigi
                              # delay_s ile birebir. Iki bagimsiz kosuda da saglam.

    # ══ PERIYODIK KESTIRICI (2026-08-19) — hedef konum hatasinin KOKU ═══
    # ⭐ OLCULEN SORUN (yarisma modu, 1055 esli ornek):
    #     HAM bozuk hedef GPS'i : medyan 21.6 m | p90 39.5
    #     mevcut "j" filtresi   : medyan 14.9 m | p90 39.0
    #   Angajman 10-30 m'de geciyor -> 15 m hatayla vurmak IMKANSIZ.
    #   Ucusta olculdu: yarisma modunda 10 dk'da <3 m gecis %0
    #   (teshis modunda %58, ayni sure). Yani ASIL DARBOGAZ BURASI --
    #   gudum ayarlari (K_VZ, sonumleme, aspect...) 0.3-0.8 m mertebesinde.
    #
    # ⭐ BOZULMANIN CINSI: GURULTU DEGIL GECIKME. Bozuk veriye periyodik
    #   model uydurulunca artik yalniz ~5 m -> sinyal kendi icinde duzenli.
    #   Oyunun bildirdigi delay_s = 1.00 s x hedef 18 m/s = ~18 m; olculen
    #   21.6 m ile birebir.
    #
    # ⭐ COZUM VE NEDENSEL OLCUM (her an yalniz gecmise uydurulur):
    #     ileri 0.0 s (OLUMSUZ KONTROL) -> 21.3 m   <-- ham seviyesine doner
    #     ileri 0.6 s                   -> 11.2 m
    #     ileri 1.2 s (URETIM)          ->  5.8 m   p90 10.1
    #     ileri 2.0 s                   -> 14.5 m
    #   Doz-cevap 1.2 s'te tepe yapiyor; olumsuz kontrol kazancin
    #   GECIKME TELAFISINDEN geldigini kanitliyor.
    #
    # ⚠ Uydurma AYRI IS PARCACIGINDA (bkz. isci_baslat): kontrol dongusune
    #   maliyeti maks 0.14 ms (tik butcesinin %0.3). Dongude yapilsaydi
    #   p99 18.7 ms / maks 121.8 ms olurdu.
    # ⚠ Kapi ~90 s'de acilir (bir tur + ortusme); oncesinde HAM konuma duser.
    # 0 = KAPALI (varsayilan) -> bit-ayni eski davranis.
    PERIYODIK_AKTIF = _env_f("AVCI_PERIYODIK", 0.0) >= 0.5
    PERIYODIK_ILERI_S = _env_f("AVCI_PERIYODIK_ILERI", 1.2)

    # ── TESHIS: HEDEFIN GERCEK GPS'i (get_debug_truth) ──
    # YARISMA KONFIGURASYONU DEGIL — teshis kosusu icin. True iken get_plane()
    # bozuk hedef kanalini HIC okumaz; telemetri satirindaki truth alanlarini
    # (index 18-26) kullanir ve CT-EKF BAYPAS edilir (kusursuz veri filtrelenmez).
    # Cerceve/birim cevrimi AYNEN kalir (cm->m, z-yukari -> NED, zemin kaydirmasi).
    # Amac tek bir soruyu ayirmak: kusursuz hedef verisiyle bu yasa kilitlenebiliyor
    # mu? Kilitleniyorsa sorun kestirimde, kilitlenmiyorsa yasada/geometride.
    # Bayrak False -> onceki hal (bozuk kanal + CT-EKF) bit-ayni geri gelir.
    # NOT: truth her telemetri satirinda gelir -> yasa 5 Hz yerine ~50 Hz taze veri
    # gorur. Bu da "kusursuz veri"nin parcasidir; testi POZITIF yonde kayirir,
    # dolayisiyla "kilitlenemiyor" sonucu cikarsa KESINDIR.
    # 2026-08-14: False -> True (kullanici istegi: "dogru gps verisini kullanalim,
    # bozulmus GPS'i ve onun filtrelemesini degil").
    # ACIK iken: bozuk hedef kanali HIC okunmaz, CT-EKF baypas edilir, hedef
    # konumu oyunun truth alanindan ~50 Hz gelir.
    # NEDEN (canli olculdu, 2026-08-14 18:xx, gorev sirasinda /api/telemetry):
    #     ham GNSS hatasi        24.9 m
    #     CT-EKF sonrasi         19.8 m   (kazanc yalniz %20.5)
    #     en kotu                57.5 m
    #     o anki gercek 207.9 m'ye karsi yasanin gordugu 185.9 m -> 22 m sapma
    #   Ustelik oyun kasitli olarak: 1.0 sn GECIKME, 40 m ANI ZIPLAMA,
    #   2 sn VERI DONMASI, +-10 m/s hiz gurultusu, 5 Hz rate limiti uyguluyor.
    #   Bu veriyle hicbir gudum yasasi hassas takip yapamaz -- kullanicinin
    #   "salak gibi takip ediyor, kesiyor, baska yere gidiyor" dedigi davranisin
    #   birebir karsiligi: kesme = 2 sn donma, baska yer = 40 m ziplama.
    # KAPATMAK ICIN: False yaz (yedek: dow_kopru.py.yedek_*).
    HEDEF_TRUTH_AKTIF = False   # YARISMA MODU (2026-08-18 olcumu icin kapatildi)

    # ── OLCUM KANCALARI (yalniz olcum scriptleri; varsayilan KAPALI) ──
    PITCH_SABIT = 0.0         # 0 disi: yatay kapaliyken sabit pitch enjeksiyonu
    ROLL_SABIT = 0.0          # 0 disi: yatay kapaliyken sabit roll (yanal trim taramasi)
    YAW_SABIT = None          # None disi: yaw kontrolcusu yerine sabit stick


# ── Kopru ──────────────────────────────────────────────────────────────────

class DowKopru:
    """gps_guidance'a `conn` olarak verilir; telemetri adaptorlerini de sunar.

    Kullanim (Faz 3 hedef deseni):
        kopru = DowKopru(drone_sdk)
        kopru.kalkis(30.0)
        kopru.dongu_baslat()                      # 50 Hz ic kontrol dongusu
        gg.send_velocity = dow_kopru.send_velocity
        run_gps_guidance(kopru, kopru.get_plane, kopru.get_iris, stop_event)
    """

    def __init__(self, sdk, cfg=Cfg):
        self.sdk = sdk
        self.cfg = cfg
        self._kilit = threading.Lock()
        # kontrolcu durumu
        self._i_fwd = 0.0
        self._i_right = 0.0
        self._i_vz = 0.0
        self._onceki = {"thr": 0.0, "pitch": 0.0, "roll": 0.0, "yaw": 0.0}
        self._t_son = None                 # son adim() zamani (dt icin)
        # setpoint (NED) — send_velocity yazar, adim okur
        self._sp_ned = (0.0, 0.0, 0.0)
        self._sp_yaw_ned = 0.0
        self._t_sp = None                  # None = henuz hic setpoint gelmedi
        # hedef donukluk takibi (get_plane)
        self._son_hedef_ham = None
        # GNSS duzeltici (CT-EKF) durumu — yalniz GNSS_DUZELTICI_AKTIF iken kurulur
        self._gnss = None
        self._gnss_cikti = None            # son duzeltilmis konum (m, DoW dunya)
        self._gnss_uyari = False           # hata bir kez bildirilir (sessiz olmesin)
        # dikey sonlu-fark hiz kestirimi (ana_kontrol._own_dikey_hiz deseni)
        self._fd_z = None
        self._fd_zt = None
        self._fd_vz = 0.0                  # m/s, +yukari, EMA'li
        # ── TANI LOGU (2026-08-10) — koprunun IC durumu diske yazilir ────────
        # NEDEN: 10 Agu carpisma analizinde yasa logu yasanin V_MAX'i hic asmadigini
        # gosterdi ama arac 28 m/s yapti. Koprunun kendi gordugu hiz (SDK velocity),
        # hata, integrator ve stick'ler HICBIR YERE yazilmadigi icin sebep
        # bayat attitude'dan TAHMIN edilmek zorunda kalindi -> uc hipotez de
        # olcumle curudu. Bu log tahmini bitirir. Davranisa DOKUNMAZ (salt yazma,
        # tamponlu; hata olursa sessizce kapanir, kontrol dongusu asla olmez).
        # AVCI_KOPRU_LOG=0 ile kapatilir.
        self._log_acik = os.environ.get("AVCI_KOPRU_LOG", "1") != "0"
        self._log_kuyruk = collections.deque()
        self._log_yazici = None
        self._log_dur = threading.Event()
        self._log_tampon = []
        self._log_dosya = None
        self._log_f = None
        self._log_kolon = None
        self._log_uyari = False
        # bagimsiz hiz (konum farki) — SDK velocity'nin HAKEMI
        self._fd_xy = None                 # (x, y, t)
        self._fd_vh = 0.0
        # tazelik takibi: SDK'nin hangi kanali ne kadar donuk kaliyor
        self._son_yaw = None
        self._son_yaw_t = None
        self._son_v = None
        self._son_v_t = None
        # Supervisor hangi fazda? entegre.adim() her tik gunceller.
        # Yalniz BAYAT_S secimini etkiler; komut/kontrol yolu DEGISMEZ.
        self.gorsel_faz = False
        # ic dongu
        self._dongu = None
        self._dur = threading.Event()
        # tani (olcum scriptleri okur; her adim yeni dict atanir)
        self.son_tani = {}

    # ── Telemetri okuma (DoW ham -> m / m/s / rad, DoW dunya z-up) ──────────
    def _drone_dow(self):
        t = self.sdk.get_telemetry()["drone"]
        p = tuple(x / CM for x in t["position"])       # m
        v = tuple(x / CM for x in t["velocity"])       # m/s
        r = t["rotation"]                              # DERECE (roll, pitch, yaw)
        return p, v, (math.radians(r[0]), math.radians(r[1]), math.radians(r[2]))

    def _vz_sonlu_fark(self, z_m: float, t: float) -> float:
        """Irtifa turevi + EMA (0.7/0.3) — ana_kontrol.py:757-771 deseninin
        m/s kopyasi. Bayat aralikta (>=0.5 s) kestirim resetlenir."""
        if self._fd_z is None or self._fd_zt is None:
            self._fd_z, self._fd_zt = z_m, t
            return self._fd_vz
        dt = t - self._fd_zt
        if 1e-3 < dt < 0.5:
            ham = (z_m - self._fd_z) / dt
            self._fd_vz = 0.7 * self._fd_vz + 0.3 * ham
            self._fd_z, self._fd_zt = z_m, t
        elif dt >= 0.5:
            self._fd_z, self._fd_zt = z_m, t
        return self._fd_vz

    # ── GIRIS ADAPTORLERI — gps_guidance sozlesmesi ─────────────────────────
    def get_iris(self) -> dict:
        """{x,y,z, roll,pitch,yaw, vx,vy,vz} — m/rad, NED (gps_guidance:24).
        NED z, NED_ZEMIN_M kadar kaydirilir (zemin ~ 0; Gazebo konvansiyonu)."""
        p, v, (roll, pitch, yaw) = self._drone_dow()
        pn = dow_to_ned_vek(p)
        vn = dow_to_ned_vek(v)                     # hiza kaydirma UYGULANMAZ (sabit ofset)
        # ATTITUDE ISARETI (Cfg.ROLL_ISARET / PITCH_ISARET, kanit orada):
        #   pitch AYNEN gecer (+1), roll CEVRILIR (-1; DoW roll = -NED roll).
        # roll artik SALT OLCUM DEGIL: bbox_ibvs T1a telafisi ve Kurtarma okur.
        return {"x": pn[0], "y": pn[1],
                "z": -(p[2] - float(self.cfg.NED_ZEMIN_M)),
                "vx": vn[0], "vy": vn[1], "vz": vn[2],
                "roll": float(self.cfg.ROLL_ISARET) * roll,
                "pitch": float(self.cfg.PITCH_ISARET) * pitch,
                "yaw": dow_yaw_to_ned(yaw)}

    def get_plane(self) -> dict:
        """{x,y,z, yaw, frozen} — m/rad, NED (gps_guidance:23).

        frozen: DoW hedef telemetrisi 5 Hz + dropout'lu; deger degismediyse
        donuk sayilir. gps_guidance kendi tazelik kontrolunu de yapar
        (raw != last_raw, :288) — iki mekanizma ayni semantikte."""
        truth_modu = bool(getattr(self.cfg, "HEDEF_TRUTH_AKTIF", False))
        yaw_dow = 0.0
        if truth_modu:
            # TESHIS: bozuk kanal HIC okunmaz; yalniz truth alanlari (index 18-26).
            d = self.sdk.get_debug_truth()
            if not d.get("available"):
                raise RuntimeError("HEDEF_TRUTH_AKTIF ama get_debug_truth YOK "
                                   "(oyunda debug kapali) — teshis kosusu gecersiz")
            ham_cm = d["target"]["position"]
            # yaw: yasa plane['yaw']'i KULLANMIYOR (gps_guidance:297 yalniz x,y,z
            # okur) -> truth'ta rotasyon olmadigi icin 0 verilir.
        else:
            t = self.sdk.get_telemetry()["target"]
            ham_cm = t["position"]
            yaw_dow = math.radians(t["rotation"][2])
        ham = tuple(x / CM for x in ham_cm)
        donuk = (ham == self._son_hedef_ham)
        if not donuk:
            self._son_hedef_ham = ham
        p = ham
        if self.cfg.GNSS_DUZELTICI_AKTIF and not truth_modu:
            # CT-EKF YALNIZ taze pakette guncellenir (ana_kontrol._hedef_temizle
            # deseni): donmus kare filtreye ZAMAN ILERLETMEZ. Donukken son cikti
            # aynen dondurulur -> yasanin tazelik kapisi (raw != last_raw) korunur.
            if not donuk:
                self._gnss_cikti = self._gnss_guncelle(ham_cm)
            if self._gnss_cikti is not None:
                p = self._gnss_cikti
        # ══ PERIYODIK KESTIRICI (bkz. Cfg.PERIYODIK_AKTIF) ══════════════
        # Hedefin KAPALI pistine Fourier modeli uydurup t+ILERI'de
        # degerlendirir -> oyunun ~1 s gecikmesi telafi edilir.
        # Olculen (nedensel): 14.9 m -> 5.8 m (p90 39.0 -> 10.1).
        # ⚠ Kapali ya da hazir degilse ASAGISI HIC CALISMAZ -> bit-ayni.
        # ⚠ Girdi HAM (bozuk) konum; truth kanali KULLANILMAZ.
        if self.cfg.PERIYODIK_AKTIF and not truth_modu:
            pk = self._periyodik_al()
            if pk is not None:
                try:
                    _tm = time.monotonic()
                    if not donuk:
                        pk.ekle(_tm, ham[0], ham[1], ham[2])
                    _pp = pk.kestir(_tm)
                    if _pp is not None:
                        p = (_pp[0], _pp[1], _pp[2])
                        self._periyodik_kullanildi = True
                    else:
                        self._periyodik_kullanildi = False
                    # ── MEKANIZMA KAPISI: kapinin gercekten calistigini
                    #    loglardan dogrulayabilmek icin periyodik tani.
                    #    Sonucu kabul etmeden ONCE buraya bakilir.
                    if _tm - getattr(self, "_pk_son_log", 0.0) > 5.0:
                        self._pk_son_log = _tm
                        try:
                            _d = pk.tani()
                            _sap = math.dist(p, ham) if _pp is not None else 0.0
                            print("[PK] hazir=%s periyot=%s kalite=%s ornek=%d "
                                  "sure=%.0fs sapma=%.1fm"
                                  % (_d["pk_hazir"],
                                     ("%.2f" % _d["pk_periyot_s"]) if _d["pk_periyot_s"] else "-",
                                     ("%.2f" % _d["pk_kalite_m"]) if _d["pk_kalite_m"] else "-",
                                     _d["pk_ornek"], _d["pk_sure_s"], _sap),
                                  flush=True)
                        except Exception:
                            pass
                except Exception:
                    self._periyodik_kullanildi = False
        pn = dow_to_ned_vek(p)
        return {"x": pn[0], "y": pn[1],
                "z": -(p[2] - float(self.cfg.NED_ZEMIN_M)),
                "yaw": dow_yaw_to_ned(yaw_dow),
                "frozen": donuk}

    def _periyodik_al(self):
        """Periyodik kestiriciyi tembel kur; arkaplan iscisini baslat.

        ⚠ Uydurma AYRI IS PARCACIGINDA: kontrol dongusunde yapilsaydi
        p99 18.7 ms / maks 121.8 ms takilma olurdu (olculdu). Boyle
        ekle+kestir maliyeti maks 0.14 ms.
        """
        pk = getattr(self, "_periyodik", None)
        if pk is not None:
            return pk
        try:
            from fusion.periyodik_kestirici import PeriyodikKestirici
        except Exception as e:
            print("[KOPRU] periyodik kestirici YUKLENEMEDI: %r" % (e,))
            self._periyodik = False
            return None
        if pk is False:
            return None
        pk = PeriyodikKestirici(
            ileri_s=float(getattr(self.cfg, "PERIYODIK_ILERI_S", 1.2)))
        pk.isci_baslat(arali_s=0.5)
        self._periyodik = pk
        print("[KOPRU] periyodik kestirici ACIK (ileri %.2f s) — hedef konum "
              "hatasi olculen 14.9 m -> 5.8 m" % pk.ileri_s)
        return pk

    def _gnss_guncelle(self, ham_cm):
        """Bozuk hedef konumunu CT-EKF'ten gecir. Girdi/cikti: cm -> m (DoW dunya).
        Isinmada/hatada None -> cagiran HAM konuma duser (zarif bozulma)."""
        try:
            if self._gnss is None:
                from fusion.inovasyonlu_j_v2 import GNSSDuzeltici
                self._gnss = GNSSDuzeltici(telafi_sn=float(self.cfg.GNSS_TELAFI_SN),
                                           dt=float(self.cfg.GNSS_DT))
            s = self._gnss.guncelle(float(ham_cm[0]), float(ham_cm[1]),
                                    float(ham_cm[2]))
            if s is None:                          # isinma / donmus kare
                return self._gnss_cikti
            return (s[0] / CM, s[1] / CM, s[2] / CM)
        except Exception as e:                     # ASLA sessiz olme; ham'a dus
            if not self._gnss_uyari:
                print("[KOPRU] GNSS duzeltici hatasi, HAM konuma dusuldu:", repr(e))
                self._gnss_uyari = True
            return None

    # ── SETPOINT GIRISI — send_velocity'nin karsiligi (yalniz yazar) ────────
    def set_hiz_ned(self, vx: float, vy: float, vz: float, yaw: float):
        """gudum thread'i cagirir (20 Hz). Kontrol adim()'de kosar (LOOP_HZ)."""
        with self._kilit:
            self._sp_ned = (float(vx), float(vy), float(vz))
            self._sp_yaw_ned = float(yaw)
            self._t_sp = time.monotonic()

    # ── TEK KONTROL TIKI ────────────────────────────────────────────────────
    def adim(self, dt: float = None):
        """Telemetri oku -> kontrolculer -> set_control_surfaces. dt verilmezse
        gercek zamandan olculur (testler deterministik dt gecirir)."""
        cfg = self.cfg
        simdi = time.monotonic()
        if dt is None:
            dt = kirp((simdi - self._t_son) if self._t_son is not None else 1.0 / cfg.LOOP_HZ,
                      1e-3, 0.2)
        self._t_son = simdi

        with self._kilit:
            sp = self._sp_ned
            sp_yaw_ned = self._sp_yaw_ned
            t_sp = self._t_sp

        p_dow, v_dow, (_roll, _pitch, yaw_dow) = self._drone_dow()
        yaw_yas, v_yas, vh_fd = self._tazelik(simdi, yaw_dow, v_dow, p_dow)

        # iki dikey hiz kestirimi de HER tik hesaplanir (log kiyasi icin)
        vz_up_sdk = v_dow[2]                              # DoW z zaten YUKARI
        vz_up_fd = self._vz_sonlu_fark(p_dow[2], simdi)
        vz_up_olc = vz_up_sdk if cfg.HIZ_KAYNAK == "sdk" else vz_up_fd

        # ── BAYATLIK ESIGI FAZA GORE (2026-08-10, canli olculdu) ──────────
        # GPS yasasi 20 Hz SABIT kosar: komut araligi medyan 0.047 s, p99 0.079,
        # MAX 0.125 -> 0.30 s esigini HIC asmaz (olculdu: %0.0 bayat).
        # GORSEL yasa (bbox_ibvs) KARE-GUDUMLU: medyan 0.062 s ama kuyruk uzun,
        # p99 1.23 s, MAX 1.45 s -> araliklarin %8.1'i 0.30 s'yi asiyor. Her
        # asimda o bosluktaki TUM 50 Hz tikleri bayat sayilip stickler
        # SIFIRLANIYOR: olculen bayat tik orani GORSEL fazda %27.8 (GPS'te %0.0).
        # Sonuc: komut 16.2 m/s istenirken gerceklesen 14.4'e dusuyor, hedef
        # 18 m/s giderken saniyede ~3.5 m aciliyor -> 9 saniyede ~30 m kacis.
        # Kayip tespiti ZATEN yasanin isi (supervisor KAYIP_M=20 kare ~2 s),
        # koprunun bayat-guvenligi gorsel fazda gereksiz sikiligi getiriyordu.
        _bayat_s = (cfg.BAYAT_S_GORSEL if (self.gorsel_faz and cfg.BAYAT_S_GORSEL)
                    else cfg.BAYAT_S)
        bayat = (t_sp is None) or (simdi - t_sp > _bayat_s)

        # ── Cerceve: setpoint'i DoW dunyasina getir ──
        v_sp_dow = ned_to_dow_vek(sp)
        yaw_sp_dow = ned_yaw_to_dow(sp_yaw_ned)

        # ── 1) YATAY: stick = trim(v_sp_govde) + PI(v_hata_govde) ──
        #    (Faz 2 yapisi — dikeydeki THR_TRIM+PI'nin yatay emsali; hiz komutu
        #    ve olcum ayni dunya_to_govde ile govde cercevesine indirgenir.)
        e_fwd = e_right = 0.0
        pitch_ham = roll_ham = 0.0
        sp_fwd = sp_right = olc_fwd = olc_right = 0.0
        trim_fwd = trim_right = 0.0
        if cfg.YATAY_AKTIF and not bayat:
            sp_fwd, sp_right = dunya_to_govde(v_sp_dow[0], v_sp_dow[1], yaw_dow)
            olc_fwd, olc_right = dunya_to_govde(v_dow[0], v_dow[1], yaw_dow)
            e_fwd = sp_fwd - olc_fwd
            e_right = sp_right - olc_right
            trim_fwd = yatay_trim_stick(sp_fwd, cfg.YATAY_TRIM_NOKTA)
            trim_right = yatay_trim_stick(sp_right, cfg.YATAY_TRIM_NOKTA)
            pitch_ham = trim_fwd + cfg.KP_VH * e_fwd + self._i_fwd
            roll_ham = trim_right + cfg.KP_VH * e_right + self._i_right
            # anti-windup: eksen doymamisken VE hata banttayken biriktir
            # (buyuk-hata rampasi integrali doldurup asma yapiyordu — olculdu)
            if (-cfg.PITCH_MAX < pitch_ham < cfg.PITCH_MAX
                    and abs(e_fwd) <= cfg.E_VH_INT_BAND):
                self._i_fwd = kirp(self._i_fwd + cfg.KI_VH * e_fwd * dt,
                                   -cfg.I_VH_MAX, cfg.I_VH_MAX)
            if (-cfg.ROLL_MAX < roll_ham < cfg.ROLL_MAX
                    and abs(e_right) <= cfg.E_VH_INT_BAND):
                self._i_right = kirp(self._i_right + cfg.KI_VH * e_right * dt,
                                     -cfg.I_VH_MAX, cfg.I_VH_MAX)
        pitch_cmd = kirp(pitch_ham, -cfg.PITCH_MAX, cfg.PITCH_MAX)
        roll_cmd = kirp(roll_ham, -cfg.ROLL_MAX, cfg.ROLL_MAX)
        if not cfg.YATAY_AKTIF:
            pitch_cmd = kirp(float(cfg.PITCH_SABIT), -cfg.PITCH_MAX, cfg.PITCH_MAX)
            roll_cmd = kirp(float(cfg.ROLL_SABIT), -cfg.ROLL_MAX, cfg.ROLL_MAX)

        # ── 2) DIKEY: vz -> throttle. ISARET: NED asagi(+) -> yukari(+) ──
        vz_up_sp = -sp[2]
        e_vz = vz_up_sp - vz_up_olc
        thr_ham = (cfg.THR_TRIM + cfg.FF_VZ * vz_up_sp
                   + cfg.KP_VZ * e_vz + self._i_vz)
        thr_doydu = not (cfg.THR_DN < thr_ham < cfg.THR_UP)
        if not thr_doydu and not bayat:
            self._i_vz = kirp(self._i_vz + cfg.KI_VZ * e_vz * dt,
                              -cfg.I_VZ_MAX, cfg.I_VZ_MAX)
        thr_cmd = kirp(thr_ham, cfg.THR_DN, cfg.THR_UP)

        # ── 3) YAW: mutlak aci -> donus hizi (sarma + kacak kirpma) ──
        # ⚠ 2026-08-17: HAM hata saklaniyor. Onceden yalniz olu bant
        #   uygulanmis deger loglaniyordu -> tiklerin %57.1'i "tam 0"
        #   gorunuyor ve <3°'lik KALICI yanlilik gizleniyordu.
        yaw_hata_ham = sarmala_pi(yaw_sp_dow - yaw_dow)
        yaw_hata = kirp(yaw_hata_ham, -cfg.YAW_HATA_MAX, cfg.YAW_HATA_MAX)
        if abs(yaw_hata) < cfg.YAW_DEADBAND:
            yaw_hata = 0.0
        yaw_cmd = kirp(cfg.KP_YAW * yaw_hata, -cfg.YAW_MAX, cfg.YAW_MAX)
        if cfg.YAW_SABIT is not None:                  # acik-dongu kalibrasyon kancasi
            yaw_cmd = kirp(float(cfg.YAW_SABIT), -1.0, 1.0)

        # ── Bayat setpoint: guvenli birakma (thr=TRIM ~seviye tut, sticks sifir).
        #    thr=0 DEGIL: olcum thr 0'in +1.4 m/s ustu tirmanis oldugunu gosterdi —
        #    gudum takilirsa arac gokyuzune kacmasin, yaklasik seviyede kalsin. ──
        if bayat:
            pitch_cmd = roll_cmd = 0.0
            thr_cmd = cfg.THR_TRIM
            if cfg.YAW_SABIT is None:
                yaw_cmd = 0.0

        self._uygula(thr_cmd, pitch_cmd, roll_cmd, yaw_cmd)

        self.son_tani = {
            "t": simdi, "dt": dt, "bayat": int(bayat),
            "sp_vx": sp[0], "sp_vy": sp[1], "sp_vz": sp[2],
            "sp_yaw_ned_deg": math.degrees(sp_yaw_ned),
            "x_m": p_dow[0], "y_m": p_dow[1], "alt_m": p_dow[2],
            "yaw_dow_deg": math.degrees(yaw_dow),
            "vx_sdk": v_dow[0], "vy_sdk": v_dow[1],
            "vz_up_sdk": vz_up_sdk, "vz_up_fd": vz_up_fd,
            "vz_up_sp": vz_up_sp, "e_vz": e_vz, "i_vz": self._i_vz,
            "e_fwd": e_fwd, "e_right": e_right,
            "i_fwd": self._i_fwd, "i_right": self._i_right,
            "yaw_hata_deg": math.degrees(yaw_hata),
            "yaw_hata_ham_deg": math.degrees(yaw_hata_ham),
            "thr_ham": thr_ham, "thr_doydu": int(thr_doydu),
            "thr": self._onceki["thr"], "pitch": self._onceki["pitch"],
            "roll": self._onceki["roll"], "yaw": self._onceki["yaw"],
            # ── tani (2026-08-10): govde ayristirmasi + stick zinciri + tazelik ──
            "sp_fwd": sp_fwd, "sp_right": sp_right,
            "olc_fwd": olc_fwd, "olc_right": olc_right,
            "trim_fwd": trim_fwd, "trim_right": trim_right,
            "pitch_ham": pitch_ham, "roll_ham": roll_ham,
            "pitch_cmd": pitch_cmd, "roll_cmd": roll_cmd,
            # HAKEM: koprunun gordugu hiz (SDK) vs konumdan turetilen gercek hiz
            "vh_sdk": math.hypot(v_dow[0], v_dow[1]),
            "vh_fd": vh_fd,
            "vh_sp": math.hypot(v_sp_dow[0], v_sp_dow[1]),
            # tazelik: SDK kanallari kac saniyedir ayni degeri veriyor
            "yaw_yas_s": yaw_yas, "v_yas_s": v_yas,
        }
        self._tani_yaz(self.son_tani)
        return self.son_tani

    # ── TANI LOGU — salt yazma, davranisa dokunmaz ──────────────────────────
    def _tazelik(self, simdi, yaw_dow, v_dow, p_dow):
        """SDK kanallarinin donukluk yasi + konumdan bagimsiz yatay hiz.

        NEDEN: 10 Agu analizinde attitude'un tiklerin %17-51'inde DONUK kaldigi
        (yaw'da 7 s'ye varan bloklar) olculdu. Kopru hem yaw'i (govde ayristirmasi)
        hem SDK hizini (geri besleme) kullanir; bunlar bayatsa kontrolcu KOR olur.
        Yas = ayni degerin kac saniyedir tekrarlandigi.
        """
        if self._son_yaw is None or abs(yaw_dow - self._son_yaw) > 1e-9:
            self._son_yaw, self._son_yaw_t = yaw_dow, simdi
        yaw_yas = simdi - (self._son_yaw_t if self._son_yaw_t is not None else simdi)
        v_now = (v_dow[0], v_dow[1], v_dow[2])
        if self._son_v is None or any(abs(a - b) > 1e-9 for a, b in zip(v_now, self._son_v)):
            self._son_v, self._son_v_t = v_now, simdi
        v_yas = simdi - (self._son_v_t if self._son_v_t is not None else simdi)
        # bagimsiz yatay hiz (konum farki) — SDK velocity'nin hakemi
        if self._fd_xy is not None:
            dtp = simdi - self._fd_xy[2]
            if dtp > 0.05:                 # ~20 Hz altinda ornekle (gurultu dogrultmasi)
                self._fd_vh = math.hypot(p_dow[0] - self._fd_xy[0],
                                         p_dow[1] - self._fd_xy[1]) / dtp
                self._fd_xy = (p_dow[0], p_dow[1], simdi)
        else:
            self._fd_xy = (p_dow[0], p_dow[1], simdi)
        return yaw_yas, v_yas, self._fd_vh

    def _tani_yaz(self, tani):
        """Kontrol yolundan I/O YOK: yalniz kuyruga birak (deque.append atomik).

        OLCULDU (2026-08-10): dosya yazimi kontrol dongusunde 5.9-7.1 ms tepe
        yapiyordu = 50 Hz butcesinin %30-36'si. Acik tutamak da cozmedi (maliyet
        flush'in kendisi). Yazma ayri thread'e alindi -> kontrol tikinda kalan
        is tek append. Bir tani logu ASLA ucusu bozamaz.
        """
        if not self._log_acik:
            return
        self._log_kuyruk.append(tani)
        if self._log_yazici is None:
            self._log_yazici = threading.Thread(target=self._tani_yazici_kos,
                                                name="kopru-tani-log", daemon=True)
            self._log_yazici.start()

    def _tani_yazici_kos(self):
        """Yazici thread: kuyrugu bosaltir. Hata olursa log kapanir, ucus surer."""
        while not self._log_dur.is_set() or self._log_kuyruk:
            if len(self._log_kuyruk) < 250 and not self._log_dur.is_set():
                self._log_dur.wait(0.25)
                continue
            self._tani_bosalt()
        self._tani_bosalt()

    def _tani_bosalt(self):
        if not self._log_acik or not self._log_kuyruk:
            return
        try:
            self._log_tampon = []
            while self._log_kuyruk:
                self._log_tampon.append(self._log_kuyruk.popleft())
            if self._log_f is None:
                # Tutamak BIR KEZ acilir ve acik kalir: her flush'ta open/close
                # Windows'ta 5.9 ms tutuyordu = 50 Hz butcesinin %30'u (olculdu
                # 2026-08-10). Acik tutamakla ayni is ~0.2 ms. Kontrol dongusunu
                # sarsmamak bu logun on sartidir.
                dz = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "gazebo_kaynak", "logs")
                os.makedirs(dz, exist_ok=True)
                self._log_dosya = os.path.join(
                    dz, "kopru_tani_%s.csv" % time.strftime("%Y%m%d_%H%M%S"))
                self._log_kolon = list(self._log_tampon[0].keys())
                self._log_f = open(self._log_dosya, "w", encoding="utf-8",
                                   newline="", buffering=1 << 16)
                self._log_f.write(",".join(self._log_kolon) + "\n")
                print("[KOPRU] tani logu: %s" % self._log_dosya)
            for s in self._log_tampon:
                self._log_f.write(",".join(
                    # ⚠ 2026-08-17: "%.6g" ile t=300320.123 -> 300320 oluyordu
                    #   (843 benzersiz deger / 28749 satir). Bu logla gecikme
                    #   ya da faz analizi YAPILAMIYORDU. t tam duyarlilikta.
                    ((("%.6f" if k == "t" else "%.6g") % s[k])
                     if isinstance(s[k], (int, float)) else str(s.get(k, "")))
                    for k in self._log_kolon) + "\n")
            self._log_f.flush()        # cokme/kill aninda son 5 s kaybolmasin
            self._log_tampon = []
        except Exception as e:
            if not self._log_uyari:
                print("[KOPRU] tani logu yazilamadi, kapatiliyor:", repr(e))
                self._log_uyari = True
            self._log_acik = False
            self._log_tampon = []
            try:
                if self._log_f is not None:
                    self._log_f.close()
            except Exception:
                pass
            self._log_f = None

    def tani_log_kapat(self):
        """Yazici thread'i durdur, kuyrugu bosalt, tutamagi kapat."""
        self._log_dur.set()
        y = self._log_yazici
        if y is not None and y.is_alive():
            y.join(timeout=2.0)
        self._log_yazici = None
        self._tani_bosalt()                    # thread olmese bile kuyruk insin
        try:
            if self._log_f is not None:
                self._log_f.flush()
                self._log_f.close()
        except Exception:
            pass
        finally:
            self._log_f = None

    def _uygula(self, thr, pitch, roll, yaw):
        """ana_kontrol.py:795-801 ile ayni: rate-limit + atomik gonderim."""
        c = self.cfg
        thr = rate_limit(thr, self._onceki["thr"], c.MAX_DELTA)
        pitch = rate_limit(pitch, self._onceki["pitch"], c.MAX_DELTA)
        roll = rate_limit(roll, self._onceki["roll"], c.MAX_DELTA)
        yaw = rate_limit(yaw, self._onceki["yaw"], c.MAX_DELTA)
        self._onceki = {"thr": thr, "pitch": pitch, "roll": roll, "yaw": yaw}
        self.sdk.set_control_surfaces(thr, pitch, roll, yaw, True)

    # ── IC DONGU (LOOP_HZ) ──────────────────────────────────────────────────
    def dongu_baslat(self):
        if self._dongu is not None and self._dongu.is_alive():
            return
        self._dur.clear()
        self._dongu = threading.Thread(target=self._dongu_kos, daemon=True)
        self._dongu.start()

    def dongu_durdur(self):
        self._dur.set()
        if self._dongu is not None:
            self._dongu.join(timeout=1.0)
            self._dongu = None
        self.tani_log_kapat()          # tamponda kalan son tikler diske insin

    def _dongu_kos(self):
        period = 1.0 / self.cfg.LOOP_HZ
        while not self._dur.is_set():
            t0 = time.monotonic()
            try:
                self.adim()
            except Exception as e:                     # thread ASLA sessiz olmesin
                print("[KOPRU] adim hatasi:", repr(e))
                time.sleep(0.1)
            gecen = time.monotonic() - t0
            if gecen < period:
                time.sleep(period - gecen)

    def sifirla(self):
        """Faz gecisi / yeniden baslatmada integrator ve kestirimleri sil."""
        self._i_fwd = self._i_right = self._i_vz = 0.0
        self._fd_z = self._fd_zt = None
        self._fd_vz = 0.0

    # ── KALKIS — ayri hat, gudum oncesi (bloklar) ───────────────────────────
    def kalkis(self, hedef_irtifa_m: float, zaman_asimi_s: float = 40.0,
               zemin_m: float = None) -> bool:
        """ana_kontrol.py:1161-1168 deseni: TAKEOFF_THR ile duz tirman, irtifa
        kapisinda TRIM hover'a gec. Kaynak sistemde bu is drone_functions'in
        POZISYON setpoint'iyle yapiliyordu; DoW'da pozisyon komutu yok ->
        irtifa kapili acik-dongu tirmanis.

        DIKKAT — get_drone_altitude DUNYA-Z verir, AGL DEGIL (2026-08-06 kazasi:
        spawn zemini z=48.4 m'de; eski mutlak esik yerdeyken 'kalkis tamam' dedi,
        arac yerde suruklenip patladi). hedef_irtifa_m ZEMINE GORE yorumlanir:
        zemin_m verilirse o, verilmezse CAGRI ANINDAKI irtifa zemin sayilir
        (arac yerde cagrildigi varsayimi)."""
        c = self.cfg
        self.sdk.set_arm(True)
        if zemin_m is None:
            zemin_m = self.sdk.get_drone_altitude() / CM
        hedef_z = zemin_m + hedef_irtifa_m
        son = time.monotonic() + zaman_asimi_s
        while time.monotonic() < son:
            irtifa = self.sdk.get_drone_altitude() / CM
            if irtifa >= hedef_z - c.KALKIS_TOL_M:
                self._uygula(c.THR_TRIM, 0.0, 0.0, 0.0)   # ~seviye tut (TRIM)
                return True
            self._uygula(c.KALKIS_THR, 0.0, 0.0, 0.0)
            time.sleep(1.0 / c.LOOP_HZ)
        return False

    def hover(self):
        # thr=0 DEGIL: olculen denge gazi THR_TRIM (thr 0 = +1.4 m/s tirmanis).
        self._uygula(self.cfg.THR_TRIM, 0.0, 0.0, 0.0)


# ── gps_guidance icindeki send_velocity(conn, ...) cagrisinin karsiligi ─────

def send_velocity(conn, vx, vy, vz, yaw):
    """common.send_velocity ile AYNI imza; `conn` bir DowKopru ornegidir.

    gps_guidance.py'yi DEGISTIRMEDEN baglamak icin (Faz 3):
        import control.guidance.gps_guidance as gg
        from kopru import dow_kopru
        gg.send_velocity = dow_kopru.send_velocity
    """
    conn.set_hiz_ned(vx, vy, vz, yaw)

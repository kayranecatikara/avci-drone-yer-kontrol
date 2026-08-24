# -*- coding: utf-8 -*-
"""
================================================================================
  BBOX DURUM TEZGAHI  --  T1c (terminal dikey roll) + KES (tam durum kestirimi)
================================================================================
NE YAPAR
--------------------------------------------------------------------------------
  --kapi     MEKANIZMA KAPILARI. `run_bbox_ibvs` DONGUSUNU sahte bir arac/
             kare akisiyla bastan sona kosturur ve uretilen CSV'ye bakar:
               (a) kapilar KAPALIYKEN yeni sutunlar BOS / 0 mi,
               (b) acildiginda beklenen IMZAYI uretiyor mu.
             ⚠ `sim/yaw_menzil.py --bitayni` yalniz `komut()`u sinar; DONGU
               icindeki degisiklikleri (los_el, kutu_son, kestirim blogu)
               ancak bu tezgah gorur.
  --dogru    KESTIRIMIN DOGRULUGU, SENTETIK GERCEKLE. Bilinen bir 3B
             geometriden piksel URETILIR, yasaya verilir, yasanin yazdigi
             `kest_*` sutunlari GERCEKLE kiyaslanir. Menzil modeli
             kasitli olarak TAM tutulur ki olculen sey KESTIRIM ZINCIRI
             olsun, menzil sabiti olmasin.
  --bitayni  DONGU DUZEYINDE bit-aynilik: ayni sahte kosu, YAMA ONCESI
             modulle ve simdikiyle kosulur; ORTAK sutunlar karsilastirilir.
  --veri     GERCEK UCUS LOGLARINDA truth'a karsi KOR KIYAS (irtifa/hiz/rota).
  --hepsi    dordu birden (--veri haric; o ayri istenir, yavastir).

⛔ OYUNA DOKUNMAZ. Port 12345'e BAGLANMAZ, sureç baslatmaz/oldurmez.
   MAVLink `send_velocity` no-op'a baglanir, log dizini gecici klasore
   yonlendirilir, kilit denetim kaydi susturulur -> kampanyanin log
   klasorune TEK BAYT yazilmaz. Kampanya kosarken guvenle calisir.

================================================================================
 ⚠⚠ BU TEZGAHIN NE OLDUGU VE NE OLMADIGI  (tesis dersinin tekrari)
================================================================================
BU TEZGAH BIR PERFORMANS OLCUMU DEGILDIR. Sahte kosuda arac/hedef kinematigi
SENARYODAN gelir; yasanin urettigi komut arac hareketini ETKILEMEZ (acik
cevrim). Yani "T1c iskayi duzeltti mi" sorusu BURADA CEVAPLANAMAZ ve
cevaplanmaya CALISILMAMALIDIR.

Cevapladigi iki soru sudur:
    1. Yama TESISATI dogru mu (kapali=bit-ayni, acik=beklenen imza)?
    2. Kestirim MATEMATIGI, yasanin kendi okuma zinciriyle kosuldugunda
       gercegi geri veriyor mu?
Saha kazanci YALNIZ arac/recete_bbox2.json ile ucusta olculur.

⚠ SENTETIK KOSUDA DEDEKTOR GECIKMESI YOKTUR: piksel, o ANKI tutumdan
  uretilir. Bu yuzden `AVCI_IBVS_KOMUT_HIZALA` sentetik kollarda KAPALI
  tutulur -- acilirsa var olmayan bir bayatligi telafi eder ve kestirimi
  BOZAR. (Gercek veride durum tersidir; bkz. --veri.)
================================================================================
"""

from __future__ import annotations

import argparse
import contextlib
import csv
import io
import math
import os
import shutil
import sys
import tempfile
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "kopru", "gazebo_kaynak"))
sys.path.insert(0, os.path.join(KOK, "sim"))

from control.guidance import bbox_geometri as BG          # noqa: E402


# ══════════════════════════════════════════════════════════════════════════
#  0. YARDIMCILAR
# ══════════════════════════════════════════════════════════════════════════

def med(a):
    if not a:
        return float("nan")
    s = sorted(a)
    n = len(s)
    return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])


def p95(a):
    if not a:
        return float("nan")
    s = sorted(a)
    return s[min(len(s) - 1, int(0.95 * (len(s) - 1)))]


def _f(s, vars=float("nan")):
    if s is None:
        return vars
    s = str(s).strip()
    if s in ("", "None", "nan"):
        return vars
    try:
        return float(s)
    except ValueError:
        return vars


def ozet(ad, e, birim="m", gen=34):
    if not e:
        return "%-*s  ORNEK YOK" % (gen, ad)
    a = [abs(x) for x in e]
    return ("%-*s n=%-6d |hata| med %7.3f  p95 %7.3f  yanlilik %+7.3f %s"
            % (gen, ad, len(e), med(a), p95(a), med(e), birim))


# ══════════════════════════════════════════════════════════════════════════
#  1. SAHTE KOSU  --  run_bbox_ibvs DONGUSUNU bastan sona kostur
# ══════════════════════════════════════════════════════════════════════════
# ⚠ NEDEN DONGUYU KOSTURUYORUZ (komut()'u dogrudan cagirmak yerine):
#   T1c'nin IKINCI yarisi (`los_el` -> los_hiz[1] -> lead_el) DONGUDEDIR;
#   kestirim blogu da oyle. `komut()`u tek basina cagirmak ikisini de
#   ISKALAR ve "yama calisiyor" diye YANLIS hukum verdirir. Bu tezgahin
#   var olma sebebi tam olarak budur.

SENARYO_VARSAYILAN = dict(
    # NED, drone: konum ve SABIT hiz
    d_konum=(0.0, 0.0, -50.0),
    d_hiz=(20.0, 0.0, 0.0),
    # NED, hedef: baslangic BAGIL ofseti ve SABIT hizi
    ofset0=(10.0, 2.0, -1.8),
    h_hiz=(18.5, -0.5, 0.10),
    # tutum: roll SALINIR (T1c'yi gezmek icin), pitch/yaw sabit
    roll_genlik=0.60,          # rad; +-34 deg
    roll_periyot=2.0,          # s
    pitch=-0.25,               # rad; olculen seyir trimi civari
    yaw=0.0,
    # ⚠ YAW SALINIMI VARSAYILAN 0 (yani arac DONMUYOR). Bu bilerek boyle:
    #   T1c ve KES kollarinin yaw ile isi yok. AMA Y2 (KOMUT_HIZALA) kapisi
    #   `hizala = K * yaw_hizi` oldugu icin DONMEYEN aracta HEP 0 kalir --
    #   bu tezgah bir kez tam da bu yuzden "olumsuz kontrol olu" dedi.
    #   Y2'yi sinayan kol bu iki degeri ACIKCA verir.
    yaw_genlik=0.0,            # rad
    yaw_periyot=2.0,           # s
    # kutu: aspect orani (w/h). Boyut, menzil modelini TAM tutacak sekilde
    # secilir -> olculen sey kestirim zinciri olur, menzil sabiti DEGIL.
    aspect=1.40,
    menzil_yanlilik=0.0,       # b; R_kest = (1+b)*R kurmak icin
)


def _senaryo_durum(t, sen):
    """t aninda (bagil ofset NED, drone tutumu, hedef hizi) — GERCEK."""
    o0 = sen["ofset0"]
    dv = sen["d_hiz"]
    hv = sen["h_hiz"]
    ofs = tuple(o0[i] + (hv[i] - dv[i]) * t for i in range(3))
    roll = sen["roll_genlik"] * math.sin(2.0 * math.pi * t / sen["roll_periyot"])
    yaw = sen["yaw"]
    if sen["yaw_genlik"]:
        yaw += sen["yaw_genlik"] * math.sin(
            2.0 * math.pi * t / sen["yaw_periyot"])
    return ofs, (roll, sen["pitch"], yaw), hv


def _kutu_uret(ofs, tutum, sen, menzil_px_m):
    """GERCEK 3B ofsetten yasanin GORECEGI kutuyu uret. Kadraj disi -> None.

    ⚠ BOYUT SECIMI: yasanin varsayilan menzil modeli R = K/sqrt(w*h).
      sqrt(w*h) = K/R secilirse yasanin menzili GERCEK menzil olur ve
      olculen hata SAF kestirim hatasidir. `menzil_yanlilik` ile bilerek
      bozulabilir (bkz. --dogru'nun ikinci kolu).
    """
    roll, pitch, yaw = tutum
    R = math.sqrt(sum(v * v for v in ofs))
    if R < 0.5:
        return None
    psi = math.atan2(ofs[1], ofs[0])
    el = math.atan2(-ofs[2], math.hypot(ofs[0], ofs[1]))
    az = BG.sarmala_pi(psi - yaw)
    m = BG.seviye_piksel(az, el, roll, pitch)
    if m is None:
        return None
    cx, cy = m
    if not (0.0 < cx < 640.0 and 0.0 < cy < 480.0):
        return None
    s = menzil_px_m / (R * (1.0 + sen["menzil_yanlilik"]))
    ar = sen["aspect"]
    w = s * math.sqrt(ar)
    h = s / math.sqrt(ar)
    return cx, cy, w, h, R


class _Durdur:
    def __init__(self, n):
        self.kalan = n

    def is_set(self):
        self.kalan -= 1
        return self.kalan <= 0


class _SessizDenetim:
    """kilit_denetim yerine gecer: KAMPANYA LOG KLASORUNE YAZMASIN."""

    def yaz(self, *a, **k):
        return None


class _SahteZaman:
    """⚠⚠ SANAL SAAT — bu tezgahin en onemli parcasi.

    ILK SURUM GERCEK SAATI KULLANDI VE SAHTE BIR BULGU URETTI: "KESTIRIM
    komutu degistiriyor" dedi. Sebep yamada degildi -- iki kosu FARKLI duvar
    saatlerinde gectigi icin senaryo da farkli anlarda ornekleniyordu, yani
    kiyaslanan sey ayni kare bile degildi. (sim/tesis.py'nin iki sahte
    bulgusuyla AYNI ders: tesisin kendi kusuru bulgu sanildi.)

    Sanal saatle:
      * kare k TAM olarak t = k/LOOP_HZ aninda gecer -> kosular TEKRARLANABILIR,
      * `wait_pose`in gordugu an ile yasanin `now`u AYNI -> zamanlama artigi 0,
      * `sleep` gercekten beklemez -> tezgah saniyeler yerine milisaniyelerde
        kosar (kampanyanin CPU'sunu yemez).
    """

    def __init__(self):
        self.t = 1000.0

    def monotonic(self):
        return self.t

    def perf_counter(self):
        return self.t

    def time(self):
        return 1.7e9 + self.t

    def sleep(self, s):
        self.t += max(float(s), 0.0)

    def strftime(self, *a, **k):
        return time.strftime(*a, **k)


def sahte_kosu(kapilar=None, n_kare=160, sen=None, modul=None, loop_hz=50.0):
    """Donguyu kostur, uretilen CSV satirlarini ve GERCEK durumu dondur.

    Donus: (satirlar, gercek, cikti)
      gercek[i] = {t, ofset, R, dz, h_hiz, tutum, cx}
    ⚠ Satirlar ile gercek `_esle` ile `cx` uzerinden DOGRULANARAK eslesir.
    """
    import control.guidance.bbox_ibvs as bi
    if modul is not None:
        bi = modul
    sen = dict(SENARYO_VARSAYILAN, **(sen or {}))

    class Cfg2(bi.Cfg):
        pass
    Cfg2.LOOP_HZ = loop_hz
    for k, v in (kapilar or {}).items():
        setattr(Cfg2, k, v)

    tmp = tempfile.mkdtemp(prefix="bbox_durum_")
    eski_log, eski_send, eski_den = bi._LOG_DIR, bi.send_velocity, bi.kilit_denetim
    eski_zaman = bi.time
    saat = _SahteZaman()
    bi._LOG_DIR = tmp
    bi.send_velocity = lambda *a, **k: None
    bi.kilit_denetim = _SessizDenetim()
    bi.time = saat

    t0 = saat.t
    gercek = []
    sayac = {"seq": 0}

    def _simdi():
        return saat.t - t0

    def get_iris():
        t = _simdi()
        _, tutum, _ = _senaryo_durum(t, sen)
        return {"roll": tutum[0], "pitch": tutum[1], "yaw": tutum[2],
                "vx": sen["d_hiz"][0], "vy": sen["d_hiz"][1],
                "vz": sen["d_hiz"][2]}

    def wait_pose(son_seq, timeout=0.5):
        t = _simdi()
        ofs, tutum, hv = _senaryo_durum(t, sen)
        k = _kutu_uret(ofs, tutum, sen, Cfg2.MENZIL_PX_M)
        sayac["seq"] += 1
        if k is None:
            gercek.append(None)
            return {"seq": sayac["seq"], "pose": None, "t": t}
        cx, cy, w, h, R = k
        gercek.append({"t": t, "ofset": ofs, "R": R, "dz": -ofs[2],
                       "h_hiz": hv, "tutum": tutum, "cx": cx})
        return {"seq": sayac["seq"], "t": t,
                "pose": {"conf": 0.90, "cx": cx, "cy": cy, "w": w, "h": h}}

    try:
        with contextlib.redirect_stdout(io.StringIO()) as cikti:
            bi.run_bbox_ibvs(conn=None, get_iris=get_iris, wait_pose=wait_pose,
                             stop_event=_Durdur(n_kare), cfg=Cfg2,
                             kayip_kare_esik=10 ** 6, ff_hiz=(18.0, 0.0, 0.0))
        yol = None
        for ad in os.listdir(tmp):
            if ad.startswith("bbox_ibvs_") and ad.endswith(".csv"):
                yol = os.path.join(tmp, ad)
        satir = []
        if yol:
            with open(yol, "r", encoding="utf-8", errors="replace") as f:
                satir = list(csv.DictReader(f))
        return satir, [g for g in gercek if g is not None], cikti.getvalue()
    finally:
        bi._LOG_DIR, bi.send_velocity, bi.kilit_denetim = eski_log, eski_send, eski_den
        bi.time = eski_zaman
        shutil.rmtree(tmp, ignore_errors=True)


def _esle(satir, gercek):
    """CSV satirlarini GERCEK kayitlarla eslestir ve `cx` ile DOGRULA.

    ⚠ Dongu bazi kareleri (kutusuz, kurtarma) atlayabilir; sirayla eslemek
      sessizce KAYABILIR. Bu yuzden her cift `cx` uzerinden sinanir; tutmayan
      cift ATILIR (ve sayisi cagiran tarafindan gorulebilir).
    """
    out, kayma = [], 0
    j = 0
    for r in satir:
        if (r.get("durum") or "") not in ("IBVS", "TERMINAL"):
            continue
        if j >= len(gercek):
            break
        g = gercek[j]
        j += 1
        if abs(_f(r.get("cx")) - g["cx"]) > 0.06:      # CSV 1 ondalige yuvarlar
            kayma += 1
            continue
        out.append((r, g))
    if kayma:
        print("      ⚠ ESLEME KAYMASI: %d kare atildi" % kayma)
    return out


# ══════════════════════════════════════════════════════════════════════════
#  2. MEKANIZMA KAPILARI
# ══════════════════════════════════════════════════════════════════════════

def kapilar():
    print("\n" + "=" * 78)
    print(" MEKANIZMA KAPILARI  (dongu bastan sona kosturularak)")
    print("=" * 78)
    ok = True

    def _sut(satir, ad):
        return [_f(r.get(ad)) for r in satir
                if (r.get("durum") or "") in ("IBVS", "TERMINAL")]

    # ── K1: HEPSI KAPALI -> yeni sutunlar 0 / BOS ────────────────────────
    print("\n  K1  VARSAYILAN (butun kapilar kapali)")
    s0, g0, _ = sahte_kosu()
    n_iyi = len([r for r in s0 if (r.get("durum") or "") in ("IBVS", "TERMINAL")])
    n_term = len([r for r in s0 if (r.get("durum") or "") == "TERMINAL"])
    print("      kare: toplam %d, TERMINAL %d, gercek ornek %d"
          % (n_iyi, n_term, len(g0)))
    v = n_iyi > 50 and n_term > 5
    print("      senaryo TERMINALE giriyor mu (T1c'nin yasadigi dal): %s"
          % ("GECTI" if v else "KALDI -- senaryo gecersiz!"))
    ok = ok and v
    tr = [x for x in _sut(s0, "term_roll_deg") if math.isfinite(x)]
    v = bool(tr) and max(abs(x) for x in tr) == 0.0
    print("      term_roll_deg TAM 0 (n=%d, maks %.6f): %s"
          % (len(tr), max((abs(x) for x in tr), default=float("nan")),
             "GECTI" if v else "KALDI"))
    ok = ok and v
    bos = all((r.get("kest_R_m") or "") == "" for r in s0)
    print("      kest_* sutunlari BOS: %s" % ("GECTI" if bos else "KALDI"))
    ok = ok and bos
    # roll GERCEKTEN saliniyor mu (yoksa K2 anlamsiz olur)
    rl = [abs(x) for x in _sut(s0, "iris_roll_deg") if math.isfinite(x)]
    v = bool(rl) and max(rl) > 15.0
    print("      |iris_roll| maks %.1f deg (>15 gerekli): %s"
          % (max(rl, default=float("nan")), "GECTI" if v else "KALDI"))
    ok = ok and v

    # ── K2: TERM_ROLL acik -> term_roll_deg 0'dan AYRILMALI ──────────────
    print("\n  K2  AVCI_IBVS_TERM_ROLL=1  (T1c)")
    s1, g1, _ = sahte_kosu({"TERM_ROLL": True})
    tr1 = [x for x in _sut(s1, "term_roll_deg") if math.isfinite(x)]
    v = bool(tr1) and max(abs(x) for x in tr1) > 0.5
    print("      term_roll_deg maks %.3f deg (>0.5 gerekli): %s"
          % (max((abs(x) for x in tr1), default=float("nan")),
             "GECTI" if v else "KALDI"))
    ok = ok and v
    # ROLL ILE BUYUMELI: |roll| ile |term_roll| korelasyonu pozitif olmali
    cift = [(abs(_f(r.get("iris_roll_deg"))), abs(_f(r.get("term_roll_deg"))))
            for r in s1 if (r.get("durum") or "") in ("IBVS", "TERMINAL")]
    cift = [c for c in cift if all(math.isfinite(x) for x in c)]
    kucuk = med([b for a, b in cift if a < 10.0])
    buyuk = med([b for a, b in cift if a > 25.0])
    v = math.isfinite(kucuk) and math.isfinite(buyuk) and buyuk > 3.0 * kucuk
    print("      |term_roll| : |roll|<10 deg -> %.3f ;  |roll|>25 deg -> %.3f"
          % (kucuk, buyuk))
    print("      yatisla BUYUYOR mu (>3 kat): %s" % ("GECTI" if v else "KALDI"))
    ok = ok and v
    # roll=0 civarinda TAM 0'a inmeli
    sifir = [b for a, b in cift if a < 0.5]
    v = (not sifir) or max(sifir) < 0.05
    print("      |roll|<0.5 deg iken |term_roll| < 0.05: %s"
          % ("GECTI" if v else "KALDI"))
    ok = ok and v
    # KOMUT GERCEKTEN DEGISTI MI: terminal dikey komut (vz_cmd) sapmali
    def _vz(s):
        return [_f(r.get("vz_cmd")) for r in s
                if (r.get("durum") or "") == "TERMINAL"]
    d = [abs(a - b) for a, b in zip(_vz(s0), _vz(s1))
         if math.isfinite(a) and math.isfinite(b)]
    v = bool(d) and max(d) > 0.05
    print("      TERMINAL vz_cmd degisti mi (maks |fark| %.3f m/s): %s"
          % (max(d, default=float("nan")), "GECTI" if v else "KALDI"))
    ok = ok and v

    # ── K3: KESTIRIM acik -> kest_* dolmali ──────────────────────────────
    print("\n  K3  AVCI_IBVS_KESTIRIM=1  (KES)")
    s2, g2, _ = sahte_kosu({"KESTIRIM": True})
    dolu_R = [r for r in s2 if (r.get("kest_R_m") or "") != ""]
    dolu_v = [r for r in s2 if (r.get("kest_vh_ms") or "") != ""]
    print("      kest_R_m dolu %d kare, kest_vh_ms dolu %d kare"
          % (len(dolu_R), len(dolu_v)))
    v = len(dolu_R) > 50 and len(dolu_v) > 40
    print("      sutunlar DOLDU mu: %s" % ("GECTI" if v else "KALDI"))
    ok = ok and v
    # CAPRAZ KILIT: kest_dz_m ile eps_elev_deg TERS isaretli olmali
    c = [(_f(r.get("kest_dz_m")), _f(r.get("eps_elev_deg"))) for r in dolu_R]
    c = [x for x in c if all(math.isfinite(y) for y in x) and abs(x[0]) > 0.3]
    ters = sum(1 for a, b in c if a * b < 0)
    v = bool(c) and ters >= 0.9 * len(c)
    print("      kest_dz_m ile eps_elev_deg TERS isaret: %d/%d  %s"
          % (ters, len(c), "GECTI" if v else "KALDI"))
    ok = ok and v
    # KESTIRIM GUDUME DOKUNMAMALI: komut sutunlari K1 ile BIREBIR AYNI
    ayni = True
    for a, b in zip(s0, s2):
        for k in ("vx_cmd", "vy_cmd", "vz_cmd", "yaw_cmd_deg", "v_los"):
            if (a.get(k) or "") != (b.get(k) or ""):
                ayni = False
                break
        if not ayni:
            break
    print("      KESTIRIM guduume DOKUNMUYOR (komut sutunlari ayni): %s"
          % ("GECTI" if ayni else "KALDI -- SALT GOZLEM IHLALI!"))
    ok = ok and ayni

    # ── K3b: OLUMSUZ KONTROL GERCEKTEN BAGLIYOR MU ───────────────────────
    # ⛔ BU KONTROL BIR TUZAK YAKALADI: kapinin kosulu `_kh > 0` idi, yani
    #   NEGATIF deger SESSIZCE YUTULUYORDU. Olumsuz kontrol kolu fiilen
    #   TABANLA AYNI kosacak, deney "fark yok" diyecek ve biz mekanizmayi
    #   yanlislikla CURUTULMUS sayacaktik. Kapi artik `!= 0`.
    print("\n  K3b OLUMSUZ KONTROL  (AVCI_IBVS_KOMUT_HIZALA = -0.20)")
    print("      ⚠ Bu kol aracin DONMESINI gerektirir (hizala = K*yaw_hizi);")
    print("        senaryoya yaw salinimi (+-20 deg / 2 s) ACIKCA eklenir.")
    _yw = {"yaw_genlik": 0.35, "yaw_periyot": 2.0}
    sp, _, _ = sahte_kosu({"KOMUT_HIZALA_S": 0.20}, sen=_yw)
    sn, _, _ = sahte_kosu({"KOMUT_HIZALA_S": -0.20}, sen=_yw)
    hp = [_f(r.get("hizala_deg")) for r in sp
          if (r.get("durum") or "") in ("IBVS", "TERMINAL")]
    hn = [_f(r.get("hizala_deg")) for r in sn
          if (r.get("durum") or "") in ("IBVS", "TERMINAL")]
    hp = [x for x in hp if math.isfinite(x) and abs(x) > 1e-6]
    hn = [x for x in hn if math.isfinite(x) and abs(x) > 1e-6]
    v = bool(hp) and bool(hn)
    print("      +0.20 -> hizala_deg medyan %+7.3f (n=%d)" % (med(hp), len(hp)))
    print("      -0.20 -> hizala_deg medyan %+7.3f (n=%d)" % (med(hn), len(hn)))
    print("      NEGATIF deger BAGLIYOR mu (0'a yapisik DEGIL): %s"
          % ("GECTI" if v else "KALDI -- olumsuz kontrol OLU!"))
    ok = ok and v
    if v:
        v2 = med(hp) * med(hn) < 0
        print("      isaretler TERS mi: %s" % ("GECTI" if v2 else "KALDI"))
        ok = ok and v2

    # ── K4: MENZIL kapilari dongude de tutarli mi ────────────────────────
    print("\n  K4  MENZIL KAPILARI  (menzil_m / menzil_term_m / kutu hiz siniri)")
    m0 = [(_f(r.get("menzil_m")), _f(r.get("menzil_term_m"))) for r in s0
          if (r.get("menzil_m") or "") != ""]
    oran = [a / b for a, b in m0 if math.isfinite(a) and math.isfinite(b) and b > 0]
    # ⚠ TOLERANS: CSV menzilleri 2 ondalige YUVARLIYOR; oranin son hanesi
    #   yuvarlamadan gelir. 1e-6 istemek tezgahin kendi kusurunu bulgu sanmaktir.
    v = bool(oran) and abs(med(oran) - 202.6 / 160.0) < 2e-3
    print("      taban IKIZ orani med %.4f (beklenen %.4f): %s"
          % (med(oran), 202.6 / 160.0, "GECTI" if v else "KALDI"))
    ok = ok and v
    s3, _, _ = sahte_kosu({"MENZIL_KW": 240.9})
    o3 = [(_f(r.get("menzil_m")), _f(r.get("menzil_term_m"))) for r in s3
          if (r.get("menzil_m") or "") != ""]
    or3 = [a / b for a, b in o3 if math.isfinite(a) and math.isfinite(b) and b > 0]
    v = bool(or3) and abs(med(or3) - 1.0) < 1e-9
    print("      MENZIL_KW acikken IKIZ KAPANIYOR (oran med %.6f = 1): %s"
          % (med(or3), "GECTI" if v else "KALDI"))
    ok = ok and v

    print("\n  -> MEKANIZMA KAPILARI: %s" % ("HEPSI GECTI" if ok else "KALDI"))
    return ok


# ══════════════════════════════════════════════════════════════════════════
#  3. KESTIRIMIN DOGRULUGU  --  SENTETIK GERCEKLE
# ══════════════════════════════════════════════════════════════════════════

def dogruluk():
    print("\n" + "=" * 78)
    print(" KESTIRIM DOGRULUGU  (sentetik gercek; menzil modeli TAM tutuluyor)")
    print("=" * 78)
    print(" ⚠ Bu kol menzil SABITINI olcmez -- kutu, yasanin menzil modelini")
    print("   birebir dogru yapacak sekilde uretilir. Olculen sey KESTIRIM")
    print("   ZINCIRIDIR: piksel -> aci -> 3B ofset -> turev -> hedef hizi.")
    ok = True

    s, g, _ = sahte_kosu({"KESTIRIM": True})
    par = _esle(s, g)
    e_R, e_dz, e_az, e_v, e_rota = [], [], [], [], []
    for r, t in par:
        if (r.get("kest_R_m") or "") == "":
            continue
        e_R.append(_f(r["kest_R_m"]) - t["R"])
        e_dz.append(_f(r["kest_dz_m"]) - t["dz"])
        psi_t = math.atan2(t["ofset"][1], t["ofset"][0])
        az_t = BG.sarmala_pi(psi_t - t["tutum"][2])
        e_az.append(math.degrees(BG.sarmala_pi(
            math.radians(_f(r["kest_az_deg"])) - az_t)))
        if (r.get("kest_vh_ms") or "") != "":
            hv = t["h_hiz"]
            e_v.append(_f(r["kest_vh_ms"]) - math.hypot(hv[0], hv[1]))
            e_rota.append(math.degrees(BG.sarmala_pi(
                math.radians(_f(r["kest_rota_deg"])) - math.atan2(hv[1], hv[0]))))

    print("\n  n = %d eslesmis kare" % len(e_R))
    print("   " + ozet("menzil R", e_R, "m"))
    print("   " + ozet("irtifa farki dz", e_dz, "m"))
    print("   " + ozet("kerteriz az", e_az, "deg"))
    print("   " + ozet("hedef YER HIZI", e_v, "m/s"))
    print("   " + ozet("hedef ROTASI", e_rota, "deg"))

    # ⚠ Esikler GEVSEK degil: sentetik kosuda gurultu YOK, kalan hata
    #   yalnizca zaman damgasi kaymasindan (< 1 ms) gelmeli.
    for ad, e, esik, br in (("R", e_R, 0.02, "m"), ("dz", e_dz, 0.02, "m"),
                            ("az", e_az, 0.05, "deg"),
                            ("hiz", e_v, 0.30, "m/s"),
                            ("rota", e_rota, 1.50, "deg")):
        v = bool(e) and med([abs(x) for x in e]) < esik
        print("      %-5s medyan |hata| < %.2f %-4s : %s"
              % (ad, esik, br, "GECTI" if v else "KALDI"))
        ok = ok and v

    # ── IKINCI KOL: MENZIL YANLILIGI HIZA AYNEN BINIYOR MU ───────────────
    print("\n  MENZIL YANLILIGI -> HIZ YANLILIGI  (turetmenin saha kilidi)")
    print("   Iddia: R_kest = (1+b)R ise BAGIL hiz da (1+b) katidir; yani")
    print("   MENZIL_PX_M'in +%33 yanliligi kapanma hizini da %33 sisirir.")
    b = 0.33
    # ⚠ ISARET: kutu (1+b) kat KUCUK uretilir -> yasanin R = K/boyut'u
    #   (1+b) kat BUYUK cikar. Ilk yazimda ters cevirmistim ve tezgah
    #   0.752 dedi; hukum vermeden ONCE `R_kest/R_gercek` satirina bakin.
    s2, g2, _ = sahte_kosu({"KESTIRIM": True}, sen={"menzil_yanlilik": b})
    par2 = _esle(s2, g2)
    oran = [_f(r["kest_R_m"]) / t["R"] for r, t in par2
            if (r.get("kest_R_m") or "") != "" and t["R"] > 0]
    v = bool(oran) and abs(med(oran) - (1.0 + b)) < 0.01
    print("      olculen R_kest/R_gercek medyan: %.4f  (beklenen %.4f)  %s"
          % (med(oran), 1.0 + b, "GECTI" if v else "KALDI"))
    ok = ok and v

    # BAGIL hiz VEKTORU (skaler degil): vN = vh*cos(rota), vE = vh*sin(rota)
    def _bagil(kaynak):
        out = []
        for r, t in kaynak:
            if (r.get("kest_vh_ms") or "") == "":
                continue
            vh = _f(r["kest_vh_ms"])
            ro = math.radians(_f(r["kest_rota_deg"]))
            out.append(math.hypot(vh * math.cos(ro) - 20.0,
                                  vh * math.sin(ro) - 0.0))
        return out
    r1, r2 = med(_bagil(par)), med(_bagil(par2))
    print("      |bagil yatay hiz| : taban %.3f  yanlili %.3f m/s" % (r1, r2))
    v = (math.isfinite(r1) and math.isfinite(r2) and abs(r1) > 1e-3
         and abs(r2 / r1 - (1.0 + b)) < 0.05)
    print("      oran %.4f ~ %.4f (%%5 tolerans): %s"
          % (r2 / r1 if abs(r1) > 1e-9 else float("nan"), 1.0 + b,
             "GECTI" if v else "KALDI"))
    ok = ok and v

    print("\n  -> KESTIRIM DOGRULUGU: %s" % ("GECTI" if ok else "KALDI"))
    return ok


# ══════════════════════════════════════════════════════════════════════════
#  4. DONGU DUZEYINDE BIT-AYNILIK
# ══════════════════════════════════════════════════════════════════════════

def bitayni(yedek_yolu=None):
    """Ayni sahte kosuyu YAMA ONCESI modulle ve simdikiyle kostur, kiyasla.

    ⚠ ZAMANA BAGLI SUTUNLAR HARIC TUTULUR (`t`, `dt`, `gecikme_s`, ve
      onlardan tureyenler): iki kosu FARKLI duvar saatlerinde gecer, o
      yuzden birebir esit olamazlar. Kiyas KOMUT sutunlari uzerindedir --
      zaten "davranis degismedi" iddiasinin konusu odur.
    ⚠ Bu yuzden kiyas TOLERANSLIDIR (1e-6): zamanlama jitteri komutu
      mikroskobik oynatir. TAM esitlik iddiasi `sim/yaw_menzil.py --bitayni`
      ile (saf `komut()` cagrisi) ayrica kanitlanir.
    """
    import importlib.util
    print("\n" + "=" * 78)
    print(" DONGU DUZEYINDE BIT-AYNILIK")
    print("=" * 78)
    if yedek_yolu is None:
        kok = os.path.join(KOK, "yedek")
        aday = []
        for d in os.listdir(kok):
            for alt in ("bbox_ibvs.py",
                        os.path.join("kopru__gazebo_kaynak__control__guidance",
                                     "bbox_ibvs.py")):
                p = os.path.join(kok, d, "kod", alt)
                if os.path.exists(p):
                    aday.append(p)
        if not aday:
            print("  YEDEK BULUNAMADI -> SINANAMADI")
            return None
        aday.sort(key=os.path.getmtime)
        yedek_yolu = aday[-1]
    print("  yedek: %s" % yedek_yolu)

    spec = importlib.util.spec_from_file_location("_bbox_ibvs_yedek2", yedek_yolu)
    eski = importlib.util.module_from_spec(spec)
    sys.modules["_bbox_ibvs_yedek2"] = eski
    spec.loader.exec_module(eski)
    import control.guidance.bbox_ibvs as yeni

    ortak = [k for k in (eski._CSV_ALANLAR if hasattr(eski, "_CSV_ALANLAR")
                         else []) if k in yeni._CSV_ALANLAR]
    haric = {"t", "dt", "gecikme_s"}
    ortak = [k for k in ortak if k not in haric]
    # ⚠ IKI SENARYO: roll=0 KOLAY haldir (yeni kod yollarinin cogu zaten
    #   sifirlanir). Asil sinav YATISLI koludur -- kapilar KAPALIYKEN roll
    #   salinsa bile hicbir sey degismemeli.
    ok = True
    for ad, sen in (("roll = 0 (kolay hal)", {"roll_genlik": 0.0}),
                    ("roll +-34 deg (asil sinav)", {})):
        s_e, _, _ = sahte_kosu(sen=sen, modul=eski)
        s_y, _, _ = sahte_kosu(sen=sen, modul=yeni)
        n = min(len(s_e), len(s_y))
        kotu, ornek = 0, None
        for i in range(n):
            for k in ortak:
                a, b = (s_e[i].get(k) or ""), (s_y[i].get(k) or "")
                if a == b:
                    continue
                fa, fb = _f(a), _f(b)
                if math.isfinite(fa) and math.isfinite(fb) and abs(fa - fb) < 1e-6:
                    continue
                kotu += 1
                if ornek is None:
                    ornek = (i, k, a, b)
        print("  %-28s %3d satir x %2d sutun  ->  FARKLI hucre: %d"
              % (ad, n, len(ortak), kotu))
        if ornek:
            print("     ORNEK: satir %d, sutun '%s':  eski=%s  yeni=%s" % ornek)
        ok = ok and (n > 50) and kotu == 0
    print("  -> %s" % ("GECTI" if ok else "KALDI"))
    return ok


# ══════════════════════════════════════════════════════════════════════════
#  5. GERCEK UCUS VERISINDE KOR KIYAS
# ══════════════════════════════════════════════════════════════════════════
# ⚠⚠ BU KOLUN SINIRI ACIKCA SOYLENIR:
#    Ucus CSV'sinde ARACIN KENDI HIZI YOK (yalniz vx_cmd/vy_cmd -- komut,
#    olcum degil). Bu yuzden hedef hizi kiyasinda kendi hizimiz TRUTH
#    izinden (dx,dy,dz turevi) alinir. Yani olculen hata, gercek uctaki
#    hatanin ALT SINIRIDIR: hiz sensorunun kendi gurultusu MODELLENMEDI.
#    ÖLÇÜLMEDİ: get_iris hiz gurultusunun kestirime katkisi.

def _truth_hiz(iz, tq, pencere=0.25):
    """Truth izden (hedef, drone) NED hizlari — merkezi fark, +-pencere."""
    import bbox_kontrol as BK
    ileri = [t + pencere for t in tq]
    geri = [t - pencere for t in tq]
    out = {}
    for ad, anahtar in (("h", ("hx", "hy", "hz")), ("d", ("dx", "dy", "dz"))):
        a = [BK._interp(ileri, iz["t"], iz[k]) for k in anahtar]
        b = [BK._interp(geri, iz["t"], iz[k]) for k in anahtar]
        # DoW -> NED: N=+x, E=-y, D=-z
        out[ad] = [((a[0][i] - b[0][i]) / (2 * pencere),
                    -(a[1][i] - b[1][i]) / (2 * pencere),
                    -(a[2][i] - b[2][i]) / (2 * pencere))
                   for i in range(len(tq))]
    return out


def veri(en_fazla_log=60, conf_min=0.35, pencere_s=0.40,
         gecikme_s=None, menzil_px_m=202.6):
    import bbox_kontrol as BK
    if gecikme_s is None:
        gecikme_s = BG.DEDEKTOR_GECIKME_S
    print("\n" + "=" * 78)
    print(" GERCEK UCUS VERISI: KUTUDAN IRTIFA / HIZ / ROTA  (truth ile KOR kiyas)")
    print("=" * 78)
    print(" ⚠ Kendi hizimiz TRUTH izinden alindi (CSV'de olcum yok) -> olculen")
    print("   hata GERCEGIN ALT SINIRIDIR. Hiz sensoru gurultusu MODELLENMEDI.")
    print(" ⚠ Menzil modeli: K = %.1f px*m / sqrt(w*h)  (yasanin varsayilani)"
          % menzil_px_m)

    izler = BK._izleri_al()
    if not izler:
        print("  TRUTH IZ YOK -> OLCULEMEDI")
        return None
    import glob
    loglar = sorted(glob.glob(os.path.join(BK.LOG_DIR, "bbox_ibvs_*.csv")),
                    key=os.path.getsize, reverse=True)[:en_fazla_log]

    e_dz, e_dz_ham, e_v, e_rota, e_R = [], [], [], [], []
    # ⚠ KENDINI CURUTME KOLU: "roll telafisi dz'yi duzeltiyor" iddiasi ancak
    #   kazanc YATISLA BUYUYORSA dogrudur. Yatis bandina gore ayirmazsak
    #   herhangi bir baska fark (menzil, pitch, secilim) ayni ortalamayi
    #   uretebilir ve YANLIS hukum veririz.
    bant = [(0.0, 5.0), (5.0, 10.0), (10.0, 20.0), (20.0, 30.0), (30.0, 90.0)]
    b_dz = {b: [] for b in bant}
    b_ham = {b: [] for b in bant}
    b_term = {"T": [], "Tham": []}
    _roll_hepsi, _roll_term = [], []
    n_log = 0
    for yol in loglar:
        try:
            y = BK.yasa_yukle(yol, conf_min)
        except Exception:
            y = None
        if not y:
            continue
        iz = None
        for z in izler:
            if y["t0"] < z["t1"] and y["t1"] > z["t0"]:
                iz = z
                break
        if iz is None:
            continue
        try:
            par = BK.birlestir(y, iz, gecikme_s)
        except Exception:
            continue
        if len(par) < 20:
            continue
        # AYNA ERASI KAPISI (yatay isaret) -- BK ile ayni olcut
        e_k = [BG.azimut_ham(r["cx"]) for r in par]
        e_t = [r["eps_truth"] for r in par]
        sxx = sum(a * a for a in e_k)
        if sxx <= 1e-12 or sum(a * b for a, b in zip(e_k, e_t)) / sxx <= 0.0:
            continue
        n_log += 1
        tq = [r["t"] - gecikme_s for r in par]
        hz = _truth_hiz(iz, tq)
        # ── kutudan ofset dizisi (yasanin okuma zinciriyle) ──
        ofs, ts = [], []
        for r in par:
            R = menzil_px_m / max(r["boyut"], 1e-6)
            o = BG.hedef_ofset_ned(r["cx"], r["cy"], r["roll_h"], r["pitch_h"],
                                   r["yaw"], R)
            ofs.append(o)
            ts.append(r["t"])
            _e1 = -o[2] - r["dz_truth"]
            _e0 = (BG.irtifa_farki_telafisiz(r["cy"], r["pitch_h"], R)
                   - r["dz_truth"])
            e_R.append(R - r["R"])
            e_dz.append(_e1)
            e_dz_ham.append(_e0)
            _rd = abs(math.degrees(r["roll_h"]))
            _roll_hepsi.append(_rd)
            if r["durum"] == "TERMINAL":
                _roll_term.append(_rd)
            for bb in bant:
                if bb[0] <= _rd < bb[1]:
                    b_dz[bb].append(_e1)
                    b_ham[bb].append(_e0)
                    break
            if r["durum"] == "TERMINAL":
                b_term["T"].append(_e1)
                b_term["Tham"].append(_e0)
        # ── pencere kaydirarak hiz ──
        i0 = 0
        for i in range(len(par)):
            while ts[i] - ts[i0] > pencere_s:
                i0 += 1
            if i - i0 + 1 < 3:
                continue
            v = BG.hedef_hiz_ned(ts[i0:i + 1], ofs[i0:i + 1], hz["d"][i])
            if v is None:
                continue
            vt = hz["h"][i]
            hiz_t = math.hypot(vt[0], vt[1])
            if hiz_t < 3.0:
                continue                       # rota tanimsiz
            e_v.append(math.hypot(v[0], v[1]) - hiz_t)
            e_rota.append(math.degrees(BG.sarmala_pi(
                math.atan2(v[1], v[0]) - math.atan2(vt[1], vt[0]))))

    print("\n  kullanilan log: %d   kare: %d" % (n_log, len(e_dz)))
    if not e_dz:
        print("  ORNEK YOK -> OLCULEMEDI")
        return None
    print("\n  A) MENZIL ve IRTIFA  (tek kare, pencere gerekmez)")
    print("   " + ozet("menzil R (yasa sabiti)", e_R, "m"))
    print("   " + ozet("dz  ROLL TELAFILI", e_dz, "m"))
    print("   " + ozet("dz  telafisiz (yasanin hali)", e_dz_ham, "m"))
    print("\n  A1) YATIS DAGILIMI  (T1c'nin BEKLENTISINI belirleyen sey)")
    print("      ⛔ 'terminalde yatis 50.7 dereceye cikiyor' iddiasi CURUTULDU:")
    print("         depodaki BUTUN bbox_ibvs loglarinda (6.590 dosya /")
    print("         317.927 satir) MAKS |roll| = 30.5 deg ve 30 dereceyi")
    print("         asan kare SADECE 1 TANE. Yani 20-30 bandinin buyuk")
    print("         kazanci FIILEN ERISILEMEZ; T1c DUSUK oncelikli koldur.")
    print("      %-12s %7s %7s %7s %7s" % ("kume", "n", "med", "p95", "maks"))
    for ad, kume in (("tespitli", _roll_hepsi), ("TERMINAL", _roll_term)):
        if not kume:
            print("      %-12s  ORNEK YOK" % ad)
            continue
        s_ = sorted(kume)
        print("      %-12s %7d %7.1f %7.1f %7.1f deg"
              % (ad, len(s_), med(s_), p95(s_), max(s_)))
    _ust = sum(1 for x in _roll_hepsi if x > 30.0)
    print("      |roll| > 30 deg olan kare: %d  (%%%.3f)"
          % (_ust, 100.0 * _ust / max(len(_roll_hepsi), 1)))

    print("\n  A2) ROLL TELAFISININ KAZANCI, YATIS BANDINA GORE")
    print("      ⚠ KENDINI CURUTME: kazanc yatisla BUYUMUYORSA sebep roll")
    print("        DEGILDIR ve T1c'nin gerekcesi COKER.")
    print("      %-12s %7s %10s %10s %9s" % ("|roll| bandi", "n", "telafisiz",
                                             "telafili", "kazanc"))
    for bb in bant:
        h0 = [abs(x) for x in b_ham[bb]]
        h1 = [abs(x) for x in b_dz[bb]]
        if len(h0) < 30:
            print("      %-12s %7d  (ornek az)" % ("%.0f-%.0f" % bb, len(h0)))
            continue
        print("      %-12s %7d %10.3f %10.3f %+9.3f m"
              % ("%.0f-%.0f" % bb, len(h0), med(h0), med(h1),
                 med(h0) - med(h1)))
    if len(b_term["T"]) > 30:
        h0 = [abs(x) for x in b_term["Tham"]]
        h1 = [abs(x) for x in b_term["T"]]
        print("      %-12s %7d %10.3f %10.3f %+9.3f m"
              % ("TERMINAL", len(h0), med(h0), med(h1), med(h0) - med(h1)))

    print("\n  B) HEDEF HIZI ve ROTASI  (%.2f s pencere)" % pencere_s)
    print("   " + ozet("hedef YER HIZI", e_v, "m/s"))
    print("   " + ozet("hedef ROTASI", e_rota, "deg"))
    print("\n  ⇒ OKUMA: rota hatasi kucukse YON kestirimi kullanilabilir;")
    print("    hiz hatasi buyukse sebep MENZILDIR (radyal bilesen) --")
    print("    yanliligin isareti menzil sabitinin isaretiyle AYNI olmali.")
    return True


# ══════════════════════════════════════════════════════════════════════════
#  6. CLI
# ══════════════════════════════════════════════════════════════════════════

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kapi", action="store_true")
    ap.add_argument("--dogru", action="store_true")
    ap.add_argument("--bitayni", action="store_true")
    ap.add_argument("--veri", action="store_true")
    ap.add_argument("--hepsi", action="store_true")
    ap.add_argument("--yedek", default=None)
    ap.add_argument("--log-sayisi", type=int, default=60)
    ap.add_argument("--conf", type=float, default=0.35)
    ap.add_argument("--pencere", type=float, default=0.40)
    a = ap.parse_args()
    if not any((a.kapi, a.dogru, a.bitayni, a.veri, a.hepsi)):
        a.hepsi = True

    sonuc = {}
    if a.kapi or a.hepsi:
        sonuc["kapi"] = kapilar()
    if a.dogru or a.hepsi:
        sonuc["dogru"] = dogruluk()
    if a.bitayni or a.hepsi:
        sonuc["bitayni"] = bitayni(a.yedek)
    if a.veri:
        sonuc["veri"] = veri(a.log_sayisi, a.conf, a.pencere)

    print("\n" + "=" * 78)
    print(" OZET")
    print("=" * 78)
    for k, v in sonuc.items():
        print("  %-10s : %s" % (k, {True: "GECTI", False: "KALDI",
                                    None: "SINANAMADI"}.get(v, v)))
    return 0 if all(v is not False for v in sonuc.values()) else 1


if __name__ == "__main__":
    sys.exit(main())

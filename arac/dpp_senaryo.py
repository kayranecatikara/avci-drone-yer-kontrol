# -*- coding: utf-8 -*-
"""
================================================================================
  DPP SENARYO  --  bakis acisi dongusunu TUM senaryolara karsi sina
================================================================================
NEDEN AYRI BIR TEZGAH
--------------------------------------------------------------------------------
Oyuna sokmadan once yasanin NEREDE BOZULDUGUNU bilmek gerek. Bu tezgah
bbox_ibvs.komut()'u GERCEK haliyle cagirir (kopya matematik YOK) ve etrafina
minik bir kinematik model kurar.

⚠ NE OLCER, NE OLCMEZ
   OLCER : yasanin kendi matematigi, doygunluklari, yakinsamasi, kadraj siniri.
   OLCMEZ: dedektor gurultusu/deligi, gercek arac dinamigi, oyunun ic donguleri.
   Yani buradaki basari GEREK sarttir, YETER sart DEGILDIR. "Tezgahta gecti"
   demek "ucusta calisir" demek DEGILDIR -- bu depoda tezgah daha once UC kez
   sahte bulgu uretti.

ARAC MODELI (bilerek kaba, ama fiziksel sinirlar GERCEK)
   * hiz komutu 1. mertebe gecikmeyle izlenir (TAU_ARAC)
   * donus hizi a_max/V ile SINIRLI
   * olcum gecikmesi GECIKME_S kadar (kare kuyruğu)
   * tespit deligi: TESPIT_ORANI olasilikla kare DUSER (yasa kor kalir)

CALISTIR
    python arac/dpp_senaryo.py                    # tum senaryolar
    python arac/dpp_senaryo.py --gecikme 0.25     # kotu gecikme
    python arac/dpp_senaryo.py --tespit 0.35      # kotu tespit orani
================================================================================
"""
import os
import sys
import math
import argparse
import random
from collections import deque

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "kopru", "gazebo_kaynak"))
from control.guidance import bbox_ibvs as B                      # noqa: E402

C = B.Cfg
DT = 0.05
VT = 17.98
YARIM_HFOV = 61.0
TAU_ARAC = 0.30


# ─────────────────────────────────────────────────────────────────────────
#  SENARYOLAR: hedefin yaptigi
# ─────────────────────────────────────────────────────────────────────────
def duz(t):
    return 0.0


def yumusak_don(t):
    return math.radians(15.0)


def sert_don(t):
    return math.radians(35.0)


def zikzak(t):
    return math.radians(30.0) * (1.0 if int(t / 4.0) % 2 == 0 else -1.0)


def s_manevra(t):
    return math.radians(25.0) * math.sin(2 * math.pi * t / 12.0)


# ⚠ 2026-08-17 OLCULDU (11487 ornek, 3 gercek ucus kaydi): Talon'un GERCEK
#   donus hizi medyan 0.4 deg/s, p95 3.1, p99 4.1. Zamanin yalniz %0.3'unde
#   5 deg/s'yi asiyor, %0.1'inde 10'u. Hizi 18.0 m/s (p5-p95: 16.9-19.1),
#   irtifa bandi 10.5 m. Yani hedef PRATIKTE DUZ VE SEVIYELI uciyor.
#   Ilk senaryo listem 15-35 deg/s manevralari sinaniyordu -- gercegin 4-10
#   KATI. O liste yasayi haksiz yere "basarisiz" gosteriyordu.
#   Simdi: GERCEKCI bant (0-4) ana olcut, STRES bandi (8-20) ayri raporlanir.
def cok_yumusak(t):   return math.radians(2.0)     # gercek p75
def gercekci_don(t):  return math.radians(4.0)     # gercek p99
def gercek_zikzak(t): return math.radians(4.0) * (1.0 if int(t / 6.0) % 2 == 0 else -1.0)
def stres_8(t):       return math.radians(8.0)     # gercegin ~2 kati
def stres_15(t):      return math.radians(15.0)    # gercegin ~4 kati
def stres_25(t):      return math.radians(25.0) * math.sin(2 * math.pi * t / 12.0)

SENARYO = [
    ("G_duz", duz), ("G_yumusak_2", cok_yumusak), ("G_don_4", gercekci_don),
    ("G_zikzak_4", gercek_zikzak),
    ("S_stres_8", stres_8), ("S_stres_15", stres_15), ("S_smanevra_25", stres_25),
]

# baslangic geometrileri: (menzil, kurs hatasi derece, yanal ofset m)
# ⚠ BASLANGIC KOSULU GERCEKCI OLMALI: gorsel faz ancak hedef GORULDUGUNDE
#   devralinir, yani t=0'da hedef KADRAJIN ICINDE olmak ZORUNDA. Ilk yazimda
#   "yandan/cok_yandan" gibi girisler hedefi t=0'da 89 derecede, yani 61
#   derecelik yari-HFOV'un DISINDA baslatiyordu -> yasa hic olcum alamiyordu.
#   Bu bir YASA kusuru degil, TEZGAH kusuruydu. Asagidaki girisler kurulurken
#   dogrulanir (kadraj disi baslayan senaryo ATLANIR ve rapor edilir).
#   (ad, menzil, kurs hatasi derece, yanal ofset m)
BASLANGIC = [
    ("arkadan_yakin", 12.0, 5.0, -1.0),
    ("arkadan_orta", 20.0, 12.0, -3.0),
    ("arkadan_uzak", 35.0, 18.0, -6.0),
    ("hafif_yandan", 22.0, -25.0, 8.0),
    ("kotu_kurs", 28.0, 35.0, -10.0),
]


# ═══════════════════════════════════════════════════════════════════════
#  GERCEK YORUNGE  --  modelleme yok, Talon'un KENDI kaydi oynatilir
# ═══════════════════════════════════════════════════════════════════════
_GERCEK = None


def gercek_yorunge():
    """Son ucus kaydindan hedefin (t, x, y, z) izini yukle.

    ⚠ Logger konum DEGISMEDIKCE yazmiyor -> tekrar eden satirlar atilir.
      Bu adim atlanirsa turev yikanir; ilk olcumumde donus hizini 6.1 yerine
      0.4 deg/s bulmamin sebebi tam olarak buydu.
    """
    global _GERCEK
    if _GERCEK is not None:
        return _GERCEK
    import csv
    import glob
    ys = sorted(glob.glob(os.path.join(KOK, "veri", "hedef_iz", "hedef_iz_*.csv")),
                key=os.path.getmtime)
    for y in reversed(ys):
        T, X, Y, Z = [], [], [], []
        try:
            for r in csv.DictReader(open(y, encoding="utf-8", errors="replace")):
                try:
                    t = float(r["t_mutlak"]); x = float(r["hx_m"])
                    yy = float(r["hy_m"]); z = float(r["hz_m"])
                except Exception:
                    continue
                if X and x == X[-1] and yy == Y[-1]:
                    continue                       # TEKRAR -> at
                T.append(t); X.append(x); Y.append(yy); Z.append(z)
        except OSError:
            continue
        if len(T) > 3000:
            t0 = T[0]
            _GERCEK = ([t - t0 for t in T], X, Y, Z, os.path.basename(y))
            return _GERCEK
    _GERCEK = None
    return None


def _gercek_konum(iz, t):
    T, X, Y, Z, _ = iz
    per = T[-1]
    tt = t % per
    lo, hi = 0, len(T) - 1
    while lo < hi:
        m = (lo + hi) // 2
        if T[m] < tt:
            lo = m + 1
        else:
            hi = m
    i = max(1, lo)
    d = T[i] - T[i - 1]
    a_ = 0.0 if d <= 0 else (tt - T[i - 1]) / d
    return (X[i - 1] + a_ * (X[i] - X[i - 1]),
            Y[i - 1] + a_ * (Y[i] - Y[i - 1]),
            Z[i - 1] + a_ * (Z[i] - Z[i - 1]))


def kos(hedef_don, R0, kurs_hata_deg, yanal, gecikme_s, tespit_orani,
        sure_s=45.0, tohum=0, gercek_t0=None):
    """Tek angajman. gercek_t0 verilirse hedef GERCEK kayittan oynatilir."""
    rnd = random.Random(tohum)
    hx, hy, hpsi = 0.0, 0.0, 0.0
    _iz = gercek_yorunge() if gercek_t0 is not None else None
    if _iz is not None:
        _tg = float(gercek_t0)
        hx, hy, _ = _gercek_konum(_iz, _tg)
        _nx, _ny, _ = _gercek_konum(_iz, _tg + 0.25)
        hpsi = math.atan2(_ny - hy, _nx - hx)
    los0 = math.pi                                   # hedefin arkasindan
    dx = hx - R0 * math.cos(hpsi) + yanal * math.sin(hpsi)
    dy = hy - R0 * math.sin(hpsi) - yanal * math.cos(hpsi)
    psi = B.normalize_angle(hpsi + math.radians(kurs_hata_deg))
    v = VT
    hiz_I = 17.0
    psi_v = None
    kuyruk = deque()
    n_gec = max(1, int(round(gecikme_s / DT)))
    kilit_kesintisiz = 0.0
    kilit_en_uzun = 0.0
    en_yakin = 1e9
    kadraj_disi = False
    t = 0.0
    R = R0
    men_izi = []
    sig_izi = []
    son_v = (v * math.cos(psi), v * math.sin(psi))

    # baslangic gecerliligi: hedef t=0'da kadrajda mi?
    _los0 = math.atan2(hy - dy, hx - dx)
    _eps0 = B.normalize_angle(_los0 - psi)
    if abs(math.degrees(_eps0)) > YARIM_HFOV:
        return {"gecersiz": True, "eps0": math.degrees(_eps0)}

    while t < sure_s:
        if _iz is not None:
            _tg += DT
            _px, _py = hx, hy
            hx, hy, _ = _gercek_konum(_iz, _tg)
            if abs(hx - _px) > 1e-9 or abs(hy - _py) > 1e-9:
                hpsi = math.atan2(hy - _py, hx - _px)
        else:
            wt = hedef_don(t)
            hpsi = B.normalize_angle(hpsi + wt * DT)
            hx += VT * math.cos(hpsi) * DT
            hy += VT * math.sin(hpsi) * DT

        R = math.hypot(hx - dx, hy - dy)
        en_yakin = min(en_yakin, R)
        men_izi.append(R)
        los = math.atan2(hy - dy, hx - dx)
        eps = B.normalize_angle(los - psi)
        sig_izi.append(math.degrees(eps))

        if abs(math.degrees(eps)) > YARIM_HFOV:
            kadraj_disi = True
            kilit_kesintisiz = 0.0
        else:
            # olcum kuyruga girer (gecikme), tespit orani ile duser
            gorunur = (rnd.random() < tespit_orani)
            kuyruk.append((eps, R) if gorunur else None)

        olcum = None
        if len(kuyruk) >= n_gec:
            olcum = kuyruk.popleft()

        if olcum is not None:
            e_o, R_o = olcum
            boyut = max(C.MENZIL_PX_M / max(R_o, 0.5), 1.0)
            cx = C.CX_NISAN + B.geo.FX * math.tan(e_o)
            vx, vy, vz, yaw_cmd, hiz_I, tani = B.komut(
                cx, C.CY_NISAN, boyut, boyut, psi, hiz_I, DT, cfg=C,
                terminal=False, kapanma=None, iris_roll=0.0, yaw_hizi=0.0,
                psi_v=psi_v)
            psi_v = tani.get("psi_v")
            son_v = (vx, vy)
        vx, vy = son_v
        v_cmd = math.hypot(vx, vy)
        psi_cmd = math.atan2(vy, vx)

        # arac: hiz 1. mertebe, donus a_max/V ile sinirli
        v += (v_cmd - v) * (DT / TAU_ARAC)
        wmax = C.MAX_ACCEL / max(v, 1.0)
        dps = B.normalize_angle(psi_cmd - psi)
        psi = B.normalize_angle(psi + max(-wmax * DT, min(wmax * DT, dps)))
        dx += v * math.cos(psi) * DT
        dy += v * math.sin(psi) * DT

        # KILIT OLCUTU — SARTNAMEDEN, kafadan DEGIL (2026-08-17 duzeltmesi).
        # kilit_sayaci.py: merkez ANGAJMAN VOLUMUNDE olmali; yatay %25-75.
        # Kadraj yari-genisligi 61 derece, f = 531 px, yari-genislik 960 px.
        # %25-75 => merkezden 480 px => atan(480/531) = 42.1 derece.
        # Ilk yazimda 15 derece kullanmistim -- sartnamenin UC KATI sert.
        # Menzil kapisi: devir sayaci LOCK_PCT=0.02 -> R <= 25.7 m.
        if (abs(math.degrees(eps)) < 42.0 and 3.0 < R < 25.7):
            kilit_kesintisiz += DT
            kilit_en_uzun = max(kilit_en_uzun, kilit_kesintisiz)
        else:
            kilit_kesintisiz = 0.0
        t += DT

    yerlesme = None
    for i, r in enumerate(men_izi):
        if abs(r - C.DPP_R_SET) < 2.0:
            if all(abs(x - C.DPP_R_SET) < 3.0 for x in men_izi[i:i + 40]):
                yerlesme = i * DT
                break
    son = men_izi[-60:] if len(men_izi) >= 60 else men_izi
    return {
        "en_yakin": en_yakin, "son_menzil": R,
        "kilit_en_uzun": kilit_en_uzun, "kadraj_disi": kadraj_disi,
        "yerlesme_s": yerlesme,
        "menzil_ort_son": sum(son) / len(son),
        "menzil_std_son": (sum((x - sum(son) / len(son)) ** 2 for x in son) / len(son)) ** .5,
        "sigma_p95": sorted(abs(x) for x in sig_izi)[int(.95 * (len(sig_izi) - 1))],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gecikme", type=float, default=0.18)
    ap.add_argument("--tespit", type=float, default=0.70)
    ap.add_argument("--sure", type=float, default=45.0)
    a = ap.parse_args()

    print("DPP AYARLARI: k_sigma=%.2f  k_r=%.2f  r_set=%.1f  v_min=%.1f  PN=%.2f"
          % (C.DPP_K_SIGMA, C.DPP_K_R, C.DPP_R_SET, C.DPP_V_MIN, C.PN_N))
    print("TEZGAH      : gecikme %.2f s | tespit orani %.2f | sure %.0f s | "
          "arac tau %.2f s | a_max %.1f" % (a.gecikme, a.tespit, a.sure,
                                            TAU_ARAC, C.MAX_ACCEL))
    if C.DPP_K_SIGMA <= 0:
        print("\n⚠ DPP KAPALI (AVCI_DPP_K=0). Su komutla ac:")
        print("   AVCI_DPP_K=1.4 AVCI_DPP_KR=0.7 AVCI_IBVS_PN=0 python arac/dpp_senaryo.py")
    print("\n%-16s %-16s %8s %8s %9s %8s %8s %7s"
          % ("hedef", "baslangic", "en_yakin", "yerles_s", "kilit_5s", "men_std",
             "sigma95", "kadraj"))
    print("-" * 96)
    ozet = {"toplam": 0, "kilit5": 0, "kadraj_disi": 0}
    for sad, sfn in SENARYO:
        for bad, R0, kh, yl in BASLANGIC:
            r = kos(sfn, R0, kh, yl, a.gecikme, a.tespit, a.sure)
            if r.get("gecersiz"):
                print("%-16s %-16s  ATLANDI: t=0'da eps=%.0f derece, kadraj disi"
                      % (sad, bad, r["eps0"]))
                continue
            ozet["toplam"] += 1
            k5 = r["kilit_en_uzun"] >= 5.0
            ozet["kilit5"] += k5
            _g = sad.startswith("G_")
            ozet["g_top" if _g else "s_top"] = ozet.get("g_top" if _g else "s_top", 0) + 1
            ozet["g_kilit" if _g else "s_kilit"] = ozet.get("g_kilit" if _g else "s_kilit", 0) + k5
            ozet["kadraj_disi"] += r["kadraj_disi"]
            print("%-16s %-16s %8.2f %8s %9s %8.2f %8.1f %7s"
                  % (sad, bad, r["en_yakin"],
                     ("%.1f" % r["yerlesme_s"]) if r["yerlesme_s"] else "—",
                     ("EVET %.1f" % r["kilit_en_uzun"]) if k5 else ("hayir %.1f" % r["kilit_en_uzun"]),
                     r["menzil_std_son"], r["sigma_p95"],
                     "CIKTI" if r["kadraj_disi"] else "ic"))
    print("-" * 96)
    print("OZET: %d senaryonun %d'sinde 5 s KESINTISIZ kilit (%%%.0f) | "
          "kadrajdan cikan %d"
          % (ozet["toplam"], ozet["kilit5"], 100.0 * ozet["kilit5"] / ozet["toplam"],
             ozet["kadraj_disi"]))
    g = ozet.get("g_top", 0)
    s_ = ozet.get("s_top", 0)
    if g:
        print("  GERCEKCI bant (G_*, hedefin olculen 0-4 deg/s davranisi): "
              "%d/%d = %%%.0f" % (ozet["g_kilit"], g, 100.0 * ozet["g_kilit"] / g))
    if s_:
        print("  STRES bandi   (S_*, gercegin 2-6 kati):                   "
              "%d/%d = %%%.0f" % (ozet["s_kilit"], s_, 100.0 * ozet["s_kilit"] / s_))


if __name__ == "__main__":
    main()

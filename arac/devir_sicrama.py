# -*- coding: utf-8 -*-
"""
================================================================================
  DEVIR SICRAMASI  --  GPS -> GORSEL faz devrinin ILK 2 SANIYESI
================================================================================
KULLANICI SIKAYETI (2026-08-17)
--------------------------------------------------------------------------------
  "faza gectiginde dikeyi (irtifayi) tutmuyor, yatayda (x ekseninde) de ayni
   sekilde."

Yani sikayet CPA hakkinda DEGIL, DEVIR ANI hakkinda: devirden hemen sonra
arac hedefi dikeyde ve yatayda TUTAMIYOR.

NE OLCULUYOR
--------------------------------------------------------------------------------
veri/hedef_iz/*.csv  ~30 Hz TRUTH kaydi (iki aracin da oyun-ici konumu) ve her
satirda supervisor'in FAZ damgasi var. Devir anini (faz: GPS -> VISUAL) veriden
buluruz, t=0 yapariz ve [-1.5 s, +4 s] penceresini ayrik eksenlerde cikariniz.

EKSEN AYRISTIRMASI  (hepsi HEDEF cercevesinde, hedefin hiz yonune gore)
    dikey   = dz - hz          + = BIZ USTTEYIZ      (irtifa farki, m)
    boyuna  = LOS'un hedef hiz yonundeki bileseni,  + = hedefin ONUNDEYIZ
    yanal   = LOS'un dik bileseni,                  + = hedefin saginda
    menzil  = 3B mesafe
"x ekseni" belirsiz oldugu icin UCU DE ayri ayri verilir (NED-kuzey dahil).

⚠ OLCUM TUZAKLARI (bu dosyada acikca ele alindi)
--------------------------------------------------------------------------------
(1) BAGLANTI: hedef_iz kaydi baglanti kopsa da satir yazar. Donmus paket
    (hedef konumu ARDISIK ayni) "hareketsiz hedef" gibi gorunur ve tum
    hiz/kapanma olcumlerini bozar. Her devir icin pencere ICINDEKI TAZE ORAN
    olculur; TAZE_ESIK altindaki devirler ATILIR ve sayilir.
(2) d_vz sutunu bagimsiz truth DEGIL (+0.240 yanli, MEMORY). Dikey hiz
    KONUMDAN pencereli turevle cikarilir.
(3) Hedefin h_vx/h_vy sutunlari SDK truth paketinde YOK (bos). Hedef hizi da
    konumdan turetilir.
(4) faz='?' satirlari (supervisor durumu okunamamis) devir tespitinde
    "bilinmiyor" sayilir; GPS->?->VISUAL de devir kabul edilir ama '?' suresi
    0.5 s'yi asarsa devir ATILIR (damga guvenilmez).

CALISTIR
    python arac/devir_sicrama.py                 (en yeni buyuk kayit)
    python arac/devir_sicrama.py <csv> [<csv>..]
    python arac/devir_sicrama.py --hepsi         (bugunun tum kayitlari)
================================================================================
"""
import os
import sys
import csv
import glob
import math

import numpy as np

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IZ = os.path.join(KOK, "veri", "hedef_iz")

ONCE = 1.5          # s; devir oncesi pencere
SONRA = 4.0         # s; devir sonrasi pencere
W_HIZ = 0.40        # s; hiz turevi penceresi
TAZE_ESIK = 0.60    # pencere icinde taze hedef ornegi orani alt siniri
BOS_MAX = 0.5       # s; faz='?' bosluk ust siniri


def _oku(yol):
    with open(yol, encoding="utf-8", errors="replace") as f:
        r = list(csv.DictReader(f))
    if not r:
        return None
    n = len(r)

    def col(ad):
        v = np.full(n, np.nan)
        for i, x in enumerate(r):
            s = (x.get(ad) or "").strip()
            if s:
                try:
                    v[i] = float(s)
                except ValueError:
                    pass
        return v

    d = {a: col(a) for a in ("t_s", "hx_m", "hy_m", "hz_m",
                             "dx_m", "dy_m", "dz_m",
                             "d_roll", "d_pitch", "d_yaw",
                             "h_roll", "h_pitch", "h_yaw")}
    d["faz"] = np.array([(x.get("faz") or "?").strip() for x in r])
    # zaman artmayan satirlari at (kayit basinda tekrar var)
    ok = np.concatenate([[True], np.diff(d["t_s"]) > 1e-9])
    ok &= np.isfinite(d["t_s"])
    for k in d:
        d[k] = d[k][ok]
    return d


def _pencereli_hiz(t, x, w=W_HIZ):
    """Pencereli turev. Ham komsu farki ornekleme titremesinden guvenilmez."""
    ta = np.clip(t - w / 2, t[0], t[-1])
    tb = np.clip(t + w / 2, t[0], t[-1])
    return (np.interp(tb, t, x) - np.interp(ta, t, x)) / np.maximum(tb - ta, 1e-6)


def _taze(hx, hy, hz):
    """Hedef paketi TAZE mi (onceki ornekten farkli mi)."""
    dd = np.concatenate([[1.0], np.abs(np.diff(hx)) + np.abs(np.diff(hy))
                         + np.abs(np.diff(hz))])
    return dd > 1e-6


def devirler(d):
    """faz GPS -> VISUAL gecis indeksleri (ara '?' bosluguna toleransli)."""
    faz, t = d["faz"], d["t_s"]
    out = []
    son_bilinen = None      # (idx, faz) en son '?' olmayan
    for i in range(len(faz)):
        f = faz[i]
        if f == "?":
            continue
        if f == "VISUAL" and son_bilinen is not None and son_bilinen[1] == "GPS":
            bos = t[i] - t[son_bilinen[0]]
            out.append((i, bos))
        son_bilinen = (i, f)
    return out


def cikar(d, i):
    """Tek devrin eksen-ayristirmali penceresi. None = olcum gecersiz."""
    t = d["t_s"]
    t0 = t[i]
    m = (t >= t0 - ONCE) & (t <= t0 + SONRA)
    if m.sum() < 40:
        return None
    tt = t[m] - t0
    hx, hy, hz = d["hx_m"][m], d["hy_m"][m], d["hz_m"][m]
    dx, dy, dz = d["dx_m"][m], d["dy_m"][m], d["dz_m"][m]
    if not (np.isfinite(hx).all() and np.isfinite(dx).all()):
        return None
    taze = _taze(hx, hy, hz).mean()
    if taze < TAZE_ESIK:
        return None, taze

    # hizlar (konumdan, pencereli)
    hvx, hvy = _pencereli_hiz(tt, hx), _pencereli_hiz(tt, hy)
    hvz = _pencereli_hiz(tt, hz)
    dvx, dvy = _pencereli_hiz(tt, dx), _pencereli_hiz(tt, dy)
    dvz = _pencereli_hiz(tt, dz)

    # LOS ve eksen ayristirmasi (hedef cercevesi)
    lx, ly, lz = hx - dx, hy - dy, hz - dz        # bize gore hedef
    yer = np.hypot(lx, ly)
    menzil = np.sqrt(lx ** 2 + ly ** 2 + lz ** 2)
    dikey = dz - hz                                # + = BIZ USTTEYIZ
    hs = np.hypot(hvx, hvy)
    ux = np.where(hs > 0.5, hvx / np.maximum(hs, 1e-6), 1.0)
    uy = np.where(hs > 0.5, hvy / np.maximum(hs, 1e-6), 0.0)
    # bizim hedefe gore konumumuz = -LOS
    rx, ry = dx - hx, dy - hy
    boyuna = rx * ux + ry * uy                     # + = hedefin ONUNDE
    yanal = -rx * uy + ry * ux                     # + = hedefin saginda

    # kapanma hizi (menzil turevi, - = yaklasiyoruz -> +'ya cevir)
    kapanma = -_pencereli_hiz(tt, menzil)

    # kerteriz hatasi: hiz vektorumuz ile LOS arasindaki aci (yatay duzlem)
    bh = np.hypot(dvx, dvy)
    kert = np.full(len(tt), np.nan)
    ok = (bh > 0.5) & (yer > 0.3)
    kert[ok] = np.degrees(np.arctan2(
        dvx[ok] * ly[ok] - dvy[ok] * lx[ok],
        dvx[ok] * lx[ok] + dvy[ok] * ly[ok]))

    # gorunen yukselis: hedef bize gore kac derece yukarida (seviye cercevesi)
    yuk = np.degrees(np.arctan2(lz, np.maximum(yer, 1e-6)))

    return dict(t=tt, menzil=menzil, yer=yer, dikey=dikey, boyuna=boyuna,
                yanal=yanal, kapanma=kapanma, kert=kert, yuk=yuk,
                dvz=dvz, hvz=hvz, hiz=np.hypot(dvx, dvy),
                hedef_hiz=hs, taze=taze,
                pitch=d["d_pitch"][m], roll=d["d_roll"][m],
                dz=dz, hz=hz), taze


def _at(g, ta, tb, ad):
    """[ta,tb) penceresinin ortalamasi."""
    m = (g["t"] >= ta) & (g["t"] < tb)
    if m.sum() == 0:
        return np.nan
    return float(np.nanmean(g[ad][m]))


def _anlik(g, ts, ad):
    return float(np.interp(ts, g["t"], g[ad]))


def _med(v):
    v = [x for x in v if np.isfinite(x)]
    return float(np.median(v)) if v else float("nan")


def _p(v, q):
    v = [x for x in v if np.isfinite(x)]
    return float(np.percentile(v, q)) if v else float("nan")


def analiz(yollar):
    G = []
    atilan_taze = atilan_bos = atilan_kisa = 0
    for yol in yollar:
        d = _oku(yol)
        if d is None or len(d["t_s"]) < 100:
            continue
        for i, bos in devirler(d):
            if bos > BOS_MAX:
                atilan_bos += 1
                continue
            r = cikar(d, i)
            if r is None:
                atilan_kisa += 1
                continue
            g, taze = r
            if g is None:
                atilan_taze += 1
                continue
            g["kaynak"] = os.path.basename(yol)
            G.append(g)
    return G, (atilan_taze, atilan_bos, atilan_kisa)


# ── ANALITIK DENGE (gorsel yasanin dikey denge noktasi) ────────────────────
def dikey_denge(R, pitch_deg, cy_nisan=None):
    """Gorsel TUTUS yasasinin dikey denge noktasi: bizim hedefin USTUNDE
    kalacagimiz metre. Turetme:
        vz = K_VZ*V_NOM*eps_elev,  eps_elev = W0 - W_hedef
        W0 = piksel_elev(CY_NISAN) + pitch      (nisanin DUNYA yukselisi)
        denge: W_hedef = W0  =>  atan(-D/R) = W0  =>  D = -R*tan(W0)
    D>0 = BIZ USTTEYIZ.
    """
    sys.path.insert(0, os.path.join(KOK, "kopru", "gazebo_kaynak"))
    from control.guidance.bbox_ibvs import Cfg, piksel_elev
    cy = cy_nisan if cy_nisan is not None else Cfg.CY_NISAN
    W0 = piksel_elev(cy) + math.radians(pitch_deg)
    return -R * math.tan(W0), math.degrees(W0)


def rapor(G, atilan):
    print("=" * 78)
    print("DEVIR SICRAMASI -- GPS -> GORSEL faz devrinin ilk saniyeleri")
    print("=" * 78)
    print("  gecerli devir: %d   (atilan: taze<%.0f%% %d, faz-boslugu %d, kisa %d)"
          % (len(G), TAZE_ESIK * 100, atilan[0], atilan[1], atilan[2]))
    if not G:
        return
    print("  taze paket orani: medyan %.1f%%  (min %.1f%%)"
          % (100 * _med([g["taze"] for g in G]),
             100 * min(g["taze"] for g in G)))

    # ── 1) DEVIR ANINDAKI DURUM ──
    print()
    print("-" * 78)
    print("1) DEVIR ANINDAKI DURUM  (t=0, n=%d)" % len(G))
    print("-" * 78)
    print("  %-26s%9s%9s%9s%9s" % ("olcu", "p10", "medyan", "p90", "ort"))
    for ad, key in (("menzil (3B, m)", "menzil"),
                    ("yer mesafesi (m)", "yer"),
                    ("DIKEY dz-hz (m) +=ust", "dikey"),
                    ("BOYUNA (m) +=onde", "boyuna"),
                    ("YANAL (m) +=sag", "yanal"),
                    ("gorunen yukselis (deg)", "yuk"),
                    ("kapanma (m/s)", "kapanma"),
                    ("bizim hiz (m/s)", "hiz"),
                    ("hedef hizi (m/s)", "hedef_hiz"),
                    ("kerteriz hatasi (deg)", "kert"),
                    ("govde pitch (deg)", "pitch"),
                    ("govde roll (deg)", "roll"),
                    ("dikey hiz vz (m/s)", "dvz")):
        v = [_anlik(g, 0.0, key) for g in G]
        print("  %-26s%9.2f%9.2f%9.2f%9.2f"
              % (ad, _p(v, 10), _med(v), _p(v, 90), np.nanmean(v)))

    # ── 2) ILK 2 SANIYE, 0.25 s dilimlerle ──
    print()
    print("-" * 78)
    print("2) DEVIRDEN SONRA -- 0.25 s dilimler (medyan, n=%d)" % len(G))
    print("-" * 78)
    dilim = [(-1.0, -0.5), (-0.5, 0.0), (0.0, 0.25), (0.25, 0.5), (0.5, 0.75),
             (0.75, 1.0), (1.0, 1.5), (1.5, 2.0), (2.0, 3.0), (3.0, 4.0)]
    kolon = [("menzil", "menzil"), ("DIKEY", "dikey"), ("BOYUNA", "boyuna"),
             ("YANAL", "yanal"), ("yuks°", "yuk"), ("kapan", "kapanma"),
             ("hiz", "hiz"), ("vz", "dvz"), ("kert°", "kert")]
    print("  %-13s" % "pencere (s)" + "".join("%8s" % k[0] for k in kolon))
    for a, b in dilim:
        sat = "  %-13s" % ("[%+.2f,%+.2f)" % (a, b))
        for _, key in kolon:
            sat += "%8.2f" % _med([_at(g, a, b, key) for g in G])
        print(sat)

    # ── 3) DIKEY ve YATAY AYRI: hata buyuyor mu? ──
    print()
    print("-" * 78)
    print("3) DIKEY ve YATAY -- devirden SONRA hata buyuyor mu?")
    print("-" * 78)
    for ad, key in (("DIKEY |dz-hz|", "dikey"), ("YANAL |yanal|", "yanal"),
                    ("BOYUNA |boyuna|", "boyuna"), ("menzil", "menzil")):
        a = _med([abs(_at(g, -0.5, 0.0, key)) for g in G])
        b = _med([abs(_at(g, 0.0, 0.5, key)) for g in G])
        c = _med([abs(_at(g, 0.5, 1.0, key)) for g in G])
        e = _med([abs(_at(g, 1.0, 2.0, key)) for g in G])
        h = _med([abs(_at(g, 2.0, 4.0, key)) for g in G])
        print("  %-16s once %6.2f | +0.5s %6.2f | +1s %6.2f | +2s %6.2f | +4s %6.2f  (%s)"
              % (ad, a, b, c, e, h,
                 "BUYUYOR" if h > a * 1.05 else ("kuculuyor" if h < a * 0.95
                                                 else "sabit")))

    # DIKEY YON: isaret degistiriyor mu (altta -> ustte)?
    print()
    alt_once = np.mean([_at(g, -0.5, 0.0, "dikey") < 0 for g in G])
    alt_2s = np.mean([_at(g, 1.5, 2.0, "dikey") < 0 for g in G])
    print("  dikey ISARET: devir oncesi %%%.0f ALTTA  ->  +2 s'de %%%.0f ALTTA"
          % (100 * alt_once, 100 * alt_2s))
    # tirmanma sicramasi
    vz_once = _med([_at(g, -0.5, 0.0, "dvz") for g in G])
    vz_son = _med([_at(g, 0.0, 0.5, "dvz") for g in G])
    print("  dikey HIZ (dz turevi, + = TIRMANIS): once %+.2f -> devirden sonra %+.2f m/s"
          "   SICRAMA %+.2f m/s" % (vz_once, vz_son, vz_son - vz_once))
    kap_once = _med([_at(g, -0.5, 0.0, "kapanma") for g in G])
    kap_son = _med([_at(g, 0.0, 0.5, "kapanma") for g in G])
    print("  KAPANMA hizi: once %+.2f -> sonra %+.2f m/s   SICRAMA %+.2f"
          % (kap_once, kap_son, kap_son - kap_once))
    h_once = _med([_at(g, -0.5, 0.0, "hiz") for g in G])
    h_son = _med([_at(g, 0.5, 1.0, "hiz") for g in G])
    print("  YATAY HIZ: once %+.2f -> +0.5..1 s %+.2f m/s   SICRAMA %+.2f"
          % (h_once, h_son, h_son - h_once))

    # ── 4) ANALITIK DIKEY DENGE vs OLCUM ──
    print()
    print("-" * 78)
    print("4) GORSEL YASANIN DIKEY DENGE NOKTASI -- analitik vs olculen")
    print("-" * 78)
    R0 = _med([_anlik(g, 0.0, "menzil") for g in G])
    pit = _med([_anlik(g, 0.0, "pitch") for g in G])
    D0, W0 = dikey_denge(R0, pit)
    print("  devir menzili R0 = %.1f m, govde pitch = %.1f deg" % (R0, pit))
    print("  nisan DUNYA yukselisi W0 = piksel_elev(CY_NISAN) + pitch = %+.2f deg" % W0)
    print("  => yasanin istedigi dikey ayrim  D* = -R*tan(W0) = %+.2f m  (+ = BIZ USTTE)"
          % D0)
    olc0 = _med([_anlik(g, 0.0, "dikey") for g in G])
    print("  devir anindaki OLCULEN dikey ayrim         = %+.2f m" % olc0)
    print("  >>> DEVIR ANI DIKEY SETPOINT SICRAMASI     = %+.2f m" % (D0 - olc0))
    for ts in (0.5, 1.0, 2.0, 3.0):
        Rt = _med([_anlik(g, ts, "menzil") for g in G])
        pt = _med([_anlik(g, ts, "pitch") for g in G])
        Dt, _ = dikey_denge(Rt, pt)
        ot = _med([_anlik(g, ts, "dikey") for g in G])
        print("   t=%+.1f s: R=%5.1f m  hedef D*=%+6.2f  olculen=%+6.2f  fark=%+6.2f"
              % (ts, Rt, Dt, ot, ot - Dt))
    print()
    print("  ZAMAN SABITI (analitik): tau = R / (K_VZ*V_NOM) = R/6")
    for R in (20.0, 15.0, 10.0, 8.0):
        print("     R=%4.1f m -> tau = %.2f s" % (R, R / 6.0))

    # ── 5) YATAY DENGE ──
    print()
    print("-" * 78)
    print("5) GORSEL YASANIN YATAY (menzil) DENGE NOKTASI")
    print("-" * 78)
    sys.path.insert(0, os.path.join(KOK, "kopru", "gazebo_kaynak"))
    from control.guidance.bbox_ibvs import Cfg
    Rstar = Cfg.MENZIL_PX_M / Cfg.BOYUT_REF
    Rterm = Cfg.MENZIL_PX_M / Cfg.TERMINAL_BOYUT
    print("  hiz yasasi: v_los = hiz_I + K_FWD*(BOYUT_REF - boyut),  boyut=%.1f/R"
          % Cfg.MENZIL_PX_M)
    print("  denge (hata=0): R* = MENZIL_PX_M/BOYUT_REF = %.1f m" % Rstar)
    print("  terminal mandali: R_term = %.1f m  (BOYUT_REF ile AYNI -> denge = mandal)"
          % Rterm)
    print("  devirde P terimi: K_FWD*(REF - %.1f/R0) = %+.2f m/s  (hiz_I USTUNE)"
          % (Cfg.MENZIL_PX_M,
             Cfg.K_FWD * (Cfg.BOYUT_REF - Cfg.MENZIL_PX_M / max(R0, 1e-6))))
    print("  yanal denge: eps_yaw=0 (cx=CX_NISAN) -> yanal ayrim 0 (nisan hatasi yok)")
    yan0 = _med([abs(_anlik(g, 0.0, "yanal")) for g in G])
    yan2 = _med([abs(_anlik(g, 2.0, "yanal")) for g in G])
    print("  olculen |yanal|: devirde %.2f m -> +2 s'de %.2f m" % (yan0, yan2))
    boy0 = _med([_anlik(g, 0.0, "boyuna") for g in G])
    boy2 = _med([_anlik(g, 2.0, "boyuna") for g in G])
    print("  olculen boyuna : devirde %+.2f m -> +2 s'de %+.2f m  (- = hedefin ARKASINDA)"
          % (boy0, boy2))

    # ── 6) SICRAMANIN SURESI ──
    print()
    print("-" * 78)
    print("6) DEVIR SICRAMASININ SURESI  (faz basina olcum, medyan/p90)")
    print("-" * 78)

    def _ilk(g, key, kos, t0=0.0, t1=4.0):
        m = (g["t"] >= t0) & (g["t"] <= t1)
        tt, vv = g["t"][m], g[key][m]
        for i in range(len(tt)):
            if np.isfinite(vv[i]) and kos(vv[i]):
                return float(tt[i])
        return float("nan")

    olc = [
        ("dikey ISARET degisimi (alt->ust)", [_ilk(g, "dikey", lambda v: v > 0) for g in G]),
        ("kapanma SIFIRI gecisi (yaklas->uzaklas)",
         [_ilk(g, "kapanma", lambda v: v < 0, 0.3) for g in G]),
        ("menzilin EN KUCUK oldugu an",
         [float(g["t"][(g["t"] >= 0) & (g["t"] <= 4)][
             np.nanargmin(g["menzil"][(g["t"] >= 0) & (g["t"] <= 4)])]) for g in G]),
        ("|kerteriz hatasi| > 15 deg olma ani",
         [_ilk(g, "kert", lambda v: abs(v) > 15.0, 0.2) for g in G]),
    ]
    for ad, v in olc:
        ok = [x for x in v if np.isfinite(x)]
        print("  %-42s medyan %5.2f s   p90 %5.2f s   (fazlarin %%%.0f'i)"
              % (ad, _med(ok), _p(ok, 90) if ok else float("nan"),
                 100 * len(ok) / max(len(v), 1)))
    # en dusuk |dikey| ve o andaki t
    en = []
    for g in G:
        m = (g["t"] >= 0) & (g["t"] <= 4)
        a = np.abs(g["dikey"][m])
        en.append((float(np.nanmin(a)), float(g["t"][m][np.nanargmin(a)])))
    print("  %-42s medyan %5.2f m  (t = %5.2f s)"
          % ("ilk 4 s'de en kucuk |dikey|", _med([x[0] for x in en]),
             _med([x[1] for x in en])))
    print("  %-42s medyan %5.2f m"
          % ("ayni fazda +3..+4 s'deki |dikey|",
             _med([abs(_at(g, 3.0, 4.0, "dikey")) for g in G])))


# ══════════════════════════════════════════════════════════════════════════
#  IC SINYALLER -- yasanin KOMUT ETTIGI degerler (kopru/gazebo_kaynak/logs)
# ══════════════════════════════════════════════════════════════════════════
# Her gorsel faz TEK bir bbox_ibvs_*.csv yazar; dosyanin ILK satiri devir
# anidir (t=0). Hemen ONCEKI gps_guidance_*.csv'nin SON satirlari da GPS
# fazinin cikis durumudur. Ikisi birlikte "devir sicramasi"ni komut
# tarafindan gosterir (truth tarafini yukaridaki analiz gosteriyor).
LOGD = os.path.join(KOK, "kopru", "gazebo_kaynak", "logs")


def _ic_oku(p):
    with open(p, encoding="utf-8", errors="replace") as f:
        r = list(csv.DictReader(f))
    return r


def _fl(x, k, vars=None):
    s = (x.get(k) or "").strip()
    try:
        return float(s)
    except (TypeError, ValueError):
        return float("nan")


def ic_analiz(esik="bbox_ibvs_20260817_1100", enaz_kare=10):
    """Gorsel fazlarin ILK 2 SANIYESINI ic sinyallerle olc."""
    yollar = sorted(glob.glob(os.path.join(LOGD, "bbox_ibvs_*.csv")),
                    key=os.path.getmtime)
    yollar = [p for p in yollar if os.path.basename(p) >= esik]
    gps = sorted(glob.glob(os.path.join(LOGD, "gps_guidance_*.csv")),
                 key=os.path.getmtime)
    gps = {os.path.basename(p)[13:28]: p for p in gps}
    gps_ad = sorted(gps)

    F = []
    for p in yollar:
        r = _ic_oku(p)
        r = [x for x in r if x.get("durum") in ("IBVS", "TERMINAL")
             and (x.get("hiz_I") or "").strip()]
        if len(r) < enaz_kare:
            continue
        t0 = _fl(r[0], "t")
        tt = np.array([_fl(x, "t") - t0 for x in r])
        d = {"t": tt, "yol": p, "ad": os.path.basename(p)}
        for k in ("eps_elev_deg", "eps_elev_ham_deg", "eps_yaw_deg", "boyut",
                  "hiz_I", "v_los", "vz_cmd", "vx_cmd", "vy_cmd",
                  "iris_pitch_deg", "iris_roll_deg", "cy", "cy_nisan",
                  "w_talep_deg", "w_tavan_deg", "gecikme_s", "conf"):
            d[k] = np.array([_fl(x, k) for x in r])
        d["menzil"] = 202.6 / np.maximum(d["boyut"], 1e-6)
        d["vh_cmd"] = np.hypot(d["vx_cmd"], d["vy_cmd"])
        # ONCEKI GPS fazi: ayni damgadan kucuk en buyuk gps logu
        stamp = os.path.basename(p)[10:25]
        onc = [a for a in gps_ad if a < stamp]
        d["gps"] = gps[onc[-1]] if onc else None
        F.append(d)
    return F


def _ic_at(d, ta, tb, k):
    m = (d["t"] >= ta) & (d["t"] < tb)
    if m.sum() == 0:
        return float("nan")
    v = d[k][m]
    v = v[np.isfinite(v)]
    return float(np.mean(v)) if len(v) else float("nan")


def ic_rapor(F, hedef_hiz=18.05):
    print()
    print("=" * 78)
    print("IC SINYALLER -- gorsel yasanin KOMUT ETTIGI degerler (n=%d faz)" % len(F))
    print("=" * 78)
    if not F:
        return
    print("  kaynak: kopru/gazebo_kaynak/logs/bbox_ibvs_*.csv")
    print("  MEKANIZMA KAPILARI (ilk kare): cy_nisan medyan %.0f px (301 = "
          "TERM_DIKEY rampasi KAPALI), w_talep dolu = DPP acik"
          % _med([d["cy_nisan"][0] for d in F]))

    print()
    print("  ILK KARE (devir ani):")
    print("  %-28s%9s%9s%9s" % ("olcu", "p10", "medyan", "p90"))
    for ad, k in (("menzil (kutu vekili, m)", "menzil"),
                  ("boyut (px)", "boyut"),
                  ("eps_elev (deg) -=hedef UST", "eps_elev_deg"),
                  ("eps_yaw (deg)", "eps_yaw_deg"),
                  ("hiz_I SICAK BASLANGIC", "hiz_I"),
                  ("v_los KOMUT (m/s)", "v_los"),
                  ("vz_cmd (m/s) -=tirmanis", "vz_cmd"),
                  ("govde pitch (deg)", "iris_pitch_deg"),
                  ("govde roll (deg)", "iris_roll_deg")):
        v = [d[k][0] for d in F]
        print("  %-28s%9.2f%9.2f%9.2f" % (ad, _p(v, 10), _med(v), _p(v, 90)))

    print()
    print("  >>> HIZ BUTCESI: hedefin hizi ~%.1f m/s" % hedef_hiz)
    v0 = [d["v_los"][0] for d in F]
    i0 = [d["hiz_I"][0] for d in F]
    print("      v_los ilk kare medyan %.2f  ->  kapanma payi %+.2f m/s"
          % (_med(v0), _med(v0) - hedef_hiz))
    print("      v_los < hedef hizi olan faz orani: %%%.0f"
          % (100 * np.mean([x < hedef_hiz for x in v0])))
    print("      hiz_I (integral) ilk kare medyan %.2f  (hedef hizina uzaklik %+.2f)"
          % (_med(i0), _med(i0) - hedef_hiz))
    print("      hiz_I < hedef hizi olan faz orani : %%%.0f"
          % (100 * np.mean([x < hedef_hiz for x in i0])))

    print()
    print("  ILK 2 SANIYENIN EVRIMI (medyan, faz basina pencere ortalamasi):")
    dil = [(0.0, 0.25), (0.25, 0.5), (0.5, 0.75), (0.75, 1.0),
           (1.0, 1.5), (1.5, 2.0), (2.0, 3.0), (3.0, 5.0)]
    kol = [("menzil", "menzil"), ("epsEl°", "eps_elev_deg"),
           ("epsYaw°", "eps_yaw_deg"), ("hiz_I", "hiz_I"),
           ("v_los", "v_los"), ("vh_cmd", "vh_cmd"), ("vz_cmd", "vz_cmd"),
           ("pitch°", "iris_pitch_deg"), ("roll°", "iris_roll_deg"),
           ("gecik", "gecikme_s")]
    print("  %-13s" % "pencere (s)" + "".join("%8s" % k[0] for k in kol))
    for a, b in dil:
        s = "  %-13s" % ("[%.2f,%.2f)" % (a, b))
        for _, k in kol:
            s += "%8.2f" % _med([_ic_at(d, a, b, k) for d in F])
        print(s)

    # dikey doygunluk
    print()
    tum = np.concatenate([d["vz_cmd"][d["t"] <= 2.0] for d in F])
    tum = tum[np.isfinite(tum)]
    print("  ilk 2 s'de vz_cmd: medyan %+.2f  |vz|>2.9 (VZ_MAX doygunluk) %%%.1f"
          % (np.median(tum), 100 * np.mean(np.abs(tum) > 2.9)))
    ee = np.concatenate([d["eps_elev_deg"][d["t"] <= 2.0] for d in F])
    ee = ee[np.isfinite(ee)]
    print("  ilk 2 s'de eps_elev: medyan %+.1f deg  (<0 => yasa TIRMAN diyor) "
          "negatif oran %%%.0f" % (np.median(ee), 100 * np.mean(ee < 0)))
    print("  yasanin istedigi ham vz = K_VZ*V_NOM*eps_elev = %.2f m/s (medyan)"
          % (6.0 * math.radians(np.median(ee))))


# ══════════════════════════════════════════════════════════════════════════
#  ESLESTIRME -- KOMUT (bbox_ibvs log) ile GERCEKLESEN (truth iz) yan yana
# ══════════════════════════════════════════════════════════════════════════
# Iki kayit da time.monotonic kullanir: bbox_ibvs 't' ve hedef_iz 't_mutlak'
# AYNI saattir (dogrulandi: 311315 vs 311361 ayni pencerede). Bu sayede
# "yasa ne komut etti / arac ne yapti" farki DOGRUDAN olculebilir.
def esle_analiz(esik="bbox_ibvs_20260817_1100"):
    F = ic_analiz(esik)
    izler = sorted(glob.glob(os.path.join(IZ, "hedef_iz_*.csv")),
                   key=os.path.getmtime)[-8:]
    TR = []
    for y in izler:
        d = _oku(y)
        if d is None or len(d["t_s"]) < 200:
            continue
        # mutlak saat gerek
        with open(y, encoding="utf-8", errors="replace") as f:
            rr = list(csv.DictReader(f))
        tm = np.array([float(x["t_mutlak"]) for x in rr if (x.get("t_mutlak") or "")])
        if len(tm) != len(d["t_s"]):
            # _oku tekrar eden zamanlari attigi icin yeniden hizala
            tm0 = np.array([float(x["t_mutlak"]) for x in rr])
            ts0 = np.array([float(x["t_s"]) for x in rr])
            ok = np.concatenate([[True], np.diff(ts0) > 1e-9])
            tm = tm0[ok]
        d["tm"] = tm
        TR.append(d)
    if not TR:
        return []

    out = []
    for f in F:
        tm0 = f["t"][0] + 0.0
        # bbox 't' zaten mutlak monotonic; ilk kare devir ani
        t_abs = np.array([f["t"][i] for i in range(len(f["t"]))])
        # ic log 't' zaten mutlak degil: ic_analiz t0'i cikardi -> geri ekle
        with open(f["yol"], encoding="utf-8", errors="replace") as fh:
            rr = [x for x in csv.DictReader(fh)
                  if x.get("durum") in ("IBVS", "TERMINAL")
                  and (x.get("hiz_I") or "").strip()]
        if not rr:
            continue
        t_abs = np.array([float(x["t"]) for x in rr])
        for d in TR:
            if d["tm"][0] <= t_abs[0] and t_abs[-1] <= d["tm"][-1]:
                break
        else:
            continue
        # truth'tan hiz turet
        tt = d["tm"]
        dvx = _pencereli_hiz(tt, d["dx_m"])
        dvy = _pencereli_hiz(tt, d["dy_m"])
        dvz = _pencereli_hiz(tt, d["dz_m"])
        hs = np.hypot(_pencereli_hiz(tt, d["hx_m"]), _pencereli_hiz(tt, d["hy_m"]))
        vh = np.hypot(dvx, dvy)
        menzil = np.sqrt((d["hx_m"] - d["dx_m"]) ** 2 + (d["hy_m"] - d["dy_m"]) ** 2
                         + (d["hz_m"] - d["dz_m"]) ** 2)
        out.append(dict(
            t=t_abs - t_abs[0],
            vh_cmd=f["vh_cmd"], vz_cmd=f["vz_cmd"], v_los=f["v_los"],
            vh_ger=np.interp(t_abs, tt, vh),
            vz_ger=-np.interp(t_abs, tt, dvz),      # NED asagi + (truth z YUKARI)
            hedef_hiz=np.interp(t_abs, tt, hs),
            menzil_ger=np.interp(t_abs, tt, menzil),
            menzil_kutu=f["menzil"],
            dikey=np.interp(t_abs, tt, d["dz_m"] - d["hz_m"]),
            eps_elev=f["eps_elev_deg"]))
    return out


def esle_rapor(E):
    print()
    print("=" * 78)
    print("KOMUT vs GERCEKLESEN  (bbox_ibvs log  x  truth iz, ayni monotonic saat)")
    print("=" * 78)
    print("  eslesen gorsel faz: %d" % len(E))
    if not E:
        return
    dil = [(0.0, 0.25), (0.25, 0.5), (0.5, 1.0), (1.0, 1.5), (1.5, 2.0),
           (2.0, 3.0)]
    kol = [("vh_KOM", "vh_cmd"), ("vh_GER", "vh_ger"),
           ("vz_KOM", "vz_cmd"), ("vz_GER", "vz_ger"),
           ("hedefV", "hedef_hiz"),
           ("R_kutu", "menzil_kutu"), ("R_truth", "menzil_ger"),
           ("dikey", "dikey")]
    print("  %-13s" % "pencere (s)" + "".join("%9s" % k[0] for k in kol))
    for a, b in dil:
        s = "  %-13s" % ("[%.2f,%.2f)" % (a, b))
        for _, k in kol:
            s += "%9.2f" % _med([_ic_at(d, a, b, k) for d in E])
        print(s)
    print()
    print("  >>> YATAY HIZ ACIGI (komut - gerceklesen), ilk 2 s medyani: %+.2f m/s"
          % _med([_ic_at(d, 0.0, 2.0, "vh_cmd") - _ic_at(d, 0.0, 2.0, "vh_ger")
                  for d in E]))
    print("  >>> DIKEY HIZ ACIGI (komut - gerceklesen), ilk 2 s medyani: %+.2f m/s"
          % _med([_ic_at(d, 0.0, 2.0, "vz_cmd") - _ic_at(d, 0.0, 2.0, "vz_ger")
                  for d in E]))
    print("  >>> KUTU VEKILI MENZIL YANLILIGI (kutu - truth): %+.2f m (medyan)"
          % _med([_ic_at(d, 0.0, 2.0, "menzil_kutu") - _ic_at(d, 0.0, 2.0, "menzil_ger")
                  for d in E]))
    print("  >>> HIZ PAYI (gerceklesen yatay - hedef hizi):")
    for a, b in dil:
        print("      [%.2f,%.2f) : %+.2f m/s" % (
            a, b, _med([_ic_at(d, a, b, "vh_ger") - _ic_at(d, a, b, "hedef_hiz")
                        for d in E])))


def main():
    argv = sys.argv[1:]
    if argv and argv[0] == "--esle":
        esle_rapor(esle_analiz(*(argv[1:2] or [])))
        return 0
    if argv and argv[0] == "--ic":
        ic_rapor(ic_analiz(*(argv[1:2] or [])))
        return 0
    if argv and argv[0] == "--hepsi":
        yollar = sorted(glob.glob(os.path.join(IZ, "hedef_iz_*.csv")),
                        key=os.path.getmtime)[-20:]
    elif argv:
        yollar = argv
    else:
        a = sorted(glob.glob(os.path.join(IZ, "hedef_iz_*.csv")),
                   key=os.path.getsize)
        yollar = a[-3:] if a else []
    if not yollar:
        print("Kayit yok.")
        return 1
    print("kaynak: " + ", ".join(os.path.basename(y) for y in yollar))
    G, atilan = analiz(yollar)
    rapor(G, atilan)
    return 0


if __name__ == "__main__":
    sys.exit(main())

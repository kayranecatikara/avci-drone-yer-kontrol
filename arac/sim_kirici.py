# -*- coding: utf-8 -*-
"""KIRICI (adversarial bench) — onerilen duzeltmeleri KIRMAYA calisir.

⚠ SADECE OKUR. kopru/, sim/ ve diger arac/sim_*.py DEGISTIRILMEZ; hepsi
aynen import edilir. Tezgah, arac/sim_omur.py'deki KALIBRE "Tezgah B"dir
(DedektorAR: rho .93, h_olum 1.4, tau_f 2.0) — orada saha ile eslesmisti:
    saha  iska 12.73 m | omur 1.28 s | sur %79 | kor 0.41
    Tzg.B iska 13.56 m | omur 2.37 s | sur %82 | kor 0.32

BU DOSYANIN sim_omur.kosu()'dan FARKI (hepsi CANLI KODU taklit icin):
  1) KOR KOPRU SANIYE cinsinden ve bbox_ibvs.run_bbox_ibvs:1140-1159 ile
     AYNI semantikte: son iki GERCEK tespitin piksel hizi, ±900 px/s kirpma,
     1e-3 < dt_kaynak < 0.6 kapisi, yas <= KOR_KOPRU_S.
  2) eps_hizi (kadraj ici kayma hizi) 0.30 s en-kucuk-kareler penceresiyle
     HESAPLANIR ve IB.komut'a GECILIR. ⚠ sim_omur bunu gecmiyor, yani orada
     BURUN_KD OLCULEMEZ (yasa 0 goruyor).
  3) SAPMA metrigi: |hiz yonu − hedefe yon|. Sahanin acik iddiasi bu:
     tespit varken 8.3°, faz genelinde 56.4°, %24'u >90°.
  4) Senaryo kapilari: donus giris/cikis, yanlis-nesne seli, jitter, yakin
     menzil, aspect, ters donus.

KOSU:  python arac/sim_kirici.py <bolum>
       bolum: sinama kopru kopru_manevra kopru_yanlis kopru_kayip yaw
              burunkd kadraj kayip dikey sinir hepsi
"""
import math
import os
import random
import statistics as st
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "kopru", "gazebo_kaynak"))
sys.path.insert(0, os.path.join(KOK, "sim"))
sys.path.insert(0, os.path.join(KOK, "arac"))

import tesis as T                                                  # noqa: E402
from tesis import (Avci, Hedef, Olcum, kadraj, F_YASA, CX,          # noqa: E402
                   TX_MAX, TY_MAX, HataAyari, Algi)
from control.guidance import bbox_ibvs as IB                        # noqa: E402
import sim_omur as OM                                              # noqa: E402
import deney as D                                                  # noqa: E402


SahaCfg = OM.SahaCfg
cfg_ile = OM.cfg_ile


# ══════════════════════════════════════════════════════════════════════════
#  SENARYOLAR — hedefin yorungesindeki faz0, MANEVRAYI zorlamak icin
# ══════════════════════════════════════════════════════════════════════════
# Hedef ovali: duz kenar L = 104.8 m, donus yay = pi*R = 160.2 m, cevre 530 m.
#   s < L                      -> 1. duz kenar
#   L <= s < L+piR             -> 1. donus (20.1 °/s)
#   L+piR <= s < 2L+piR        -> 2. duz kenar
#   s >= 2L+piR                -> 2. donus
_L = max((Olcum.TUR_UZUNLUK - 2 * math.pi * Olcum.DONUS_YARICAP) / 2.0, 1.0)
_CEV = 2 * _L + 2 * math.pi * Olcum.DONUS_YARICAP
_V = Olcum.HEDEF_HIZ


def _faz(s):
    return (s % _CEV) / _CEV


def faz_dagilim(ad, i, n):
    """Senaryonun i. kosusu icin faz0. Angajman ~2-3 s surdugu icin
    'donuse giris' = hedefin 0.5-1.5 s icinde donuse girmesi demek."""
    u = i / float(n)
    if ad == "saha":                      # OLCULEN karisim: %52 duz
        return u
    if ad == "duz":                       # tamami duz kenarda baslar
        return _faz(u * (_L - 3.0 * _V))
    if ad == "giris":                     # 0.2-1.4 s icinde donuse girer
        return _faz(_L - (0.2 + 1.2 * u) * _V)
    if ad == "icinde":                    # donusun ORTASINDA (tam manevra)
        return _faz(_L + (0.25 + 0.5 * u) * math.pi * Olcum.DONUS_YARICAP)
    if ad == "cikis":                     # 0.2-1.4 s icinde donusten cikar
        return _faz(_L + math.pi * Olcum.DONUS_YARICAP - (0.2 + 1.2 * u) * _V)
    raise KeyError(ad)


# ══════════════════════════════════════════════════════════════════════════
#  ANGAJMAN
# ══════════════════════════════════════════════════════════════════════════
def kosu(cfg=SahaCfg, hata=None, devir_m=15.7, sure=20.0, dt=1 / 62.0,
         tohum=0, faz0=0.0, devir_aci=0.0, hedef_yon=+1,
         pencere=0.25, tau=0.10, yasa_ici=True,
         kayip_m=20, dedektor=None, kopru_s=0.0, kopru_kirp=900.0,
         eps_kd=True, kopru_temas=False, kopru_geri=False):
    """Tek gorsel faz. sim_omur.kosu ile ayni iskelet; kopru SANIYE cinsinden.

    kopru_s : KOR_KOPRU_S (s). Kutu yoksa son iki GERCEK tespitin piksel
              hiziyla ileri tasi, en fazla bu kadar SANIYE.
    eps_kd  : eps_hizi hesaplanip IB.komut'a gecilsin mi (BURUN_KD yolu).
    """
    if hata is None:
        hata = HataAyari()
    if dedektor is not None:
        dedektor = dedektor.klon(tohum)
        hata = OM._hata_kopya(hata, tespit_kaybi=False,
                              yanlis_hiz=dedektor.yanlis_hiz(hata.yanlis_hiz))
    algi = Algi(hata, tohum=tohum)
    rnd = random.Random(7919 * tohum + 13)

    hed = Hedef(faz0=faz0, yon=hedef_yon)
    hx, hy, hz, hvx, hvy, _ = hed.durum()
    hdg = math.atan2(hvy, hvx)
    yon = hdg + math.pi + math.radians(devir_aci)
    av = Avci(x=hx + devir_m * math.cos(yon), y=hy + devir_m * math.sin(yon),
              z=hz - 3.0, yaw=hdg, max_accel=cfg.MAX_ACCEL,
              v_max=cfg.V_TOPLAM_MAX, vz_max=cfg.VZ_MAX,
              yaw_rate_max=cfg.YAW_RATE_MAX_DEG)
    av.vx, av.vy = Olcum.HEDEF_HIZ * math.cos(hdg), Olcum.HEDEF_HIZ * math.sin(hdg)
    av.yaw = math.atan2(hy - av.y, hx - av.x)

    psi_v_yasa = None
    hiz_I = Olcum.HEDEF_HIZ
    t = 0.0
    kayip = 0
    terminal = False
    lam_f = 0.0
    gecmis = []
    en_yakin = 1e9
    gor = 0
    top = 0
    son_yasa_t = -1e9
    son_kare_kendi = -1e9

    kop_gecmis = []          # son 2 GERCEK teslim: (t, cx, cy, w, h)
    kop_kare = 0
    kop_hata_px = []         # koprunun GERCEKTEN nerede oldugundan sapmasi
    kop_vpx = []             # koprunun varsaydigi piksel hizi (px/s)
    kop_vpx_ger = []         # hedefin GERCEK piksel hizi (px/s, truth kadraj)
    _k_onc = None            # onceki yasa tikindeki GERCEK kadraj (t,cx,cy)
    eps_gecmis = []          # (t, eps_seviye) — 0.30 s pencere (canli ile ayni)

    t_ilk_kutu = t_son_kutu = None
    n_kutu = 0
    n_tik = 0
    n_doyum = 0
    bosluk = 0
    tik_ilk = tik_son = None
    n_tik_temas = 0
    son_eps = None
    en_yakin_kesik = 1e9
    kilit = False

    # SAPMA: |hiz yonu − hedefe yon|
    sap_hep = []
    sap_kutulu = []
    kutu_bu_tik = False
    # ⚠ SAHANIN OLCTUGU SEY: KOMUT yonu (vx_cmd,vy_cmd) — kutu yokken son
    # komut aynen tekrar GONDERILDIGI icin o da yaslanir. Aracin GERCEK hizi
    # tesiste zaten 0.211 s'lik gecikmeyle suzuluyor, o yuzden ayri tutulur.
    sapc_hep = []
    sapc_kutulu = []
    son_cmd = None           # (vx, vy) — en son GONDERILEN komut
    son_gercek_cmd = None    # (vx, vy, vz, yaw) — son GERCEK kutulu komut
    # DIKEY
    vz_tavan = 0
    n_vz = 0
    ayrim_ey = None          # en yakin anda irtifa farki (hedef - avci)
    yuks_ey = None           # en yakin anda hedefe yukselis acisi (deg)

    while t < sure:
        hed.adim(dt)
        hx, hy, hz, hvx, hvy, _ = hed.durum()
        av._hedef_yon = math.atan2(hvy, hvx)
        k = kadraj(av, hx, hy, hz)
        top += 1
        d_simdi = math.dist((av.x, av.y, av.z), (hx, hy, hz))
        if d_simdi < en_yakin:
            en_yakin = d_simdi
            ayrim_ey = hz - av.z
            _yatay = math.hypot(hx - av.x, hy - av.y)
            yuks_ey = math.degrees(math.atan2(hz - av.z, max(_yatay, 1e-6)))
        if not kilit:
            en_yakin_kesik = min(en_yakin_kesik, d_simdi)
            if t_son_kutu is not None and t > t_son_kutu + 0.5:
                kilit = True

        # SAPMA olcumu — HER sim adiminda (faz genelinde)
        _pt = math.atan2(hy - av.y, hx - av.x)
        if math.hypot(av.vx, av.vy) > 0.5:
            _pv = math.atan2(av.vy, av.vx)
            _s = abs(math.degrees((_pv - _pt + math.pi) % (2 * math.pi) - math.pi))
            sap_hep.append(_s)
            if kutu_bu_tik:
                sap_kutulu.append(_s)
        if son_cmd is not None and math.hypot(*son_cmd) > 0.5:
            _pc = math.atan2(son_cmd[1], son_cmd[0])
            _sc = abs(math.degrees((_pc - _pt + math.pi) % (2 * math.pi) - math.pi))
            sapc_hep.append(_sc)
            if kutu_bu_tik:
                sapc_kutulu.append(_sc)

        k_ver = k
        if dedektor is not None:
            yeni_kare = not (hata.kamera_hz > 0.0 and
                             t - son_kare_kendi < 1.0 / hata.kamera_hz - 1e-9)
            if yeni_kare:
                dedektor.yeni_kare(t - son_kare_kendi if son_kare_kendi > -1e8 else None)
                son_kare_kendi = t
                self_p = 0.0 if k is None else dedektor.olasilik(k[2], k[3], k[0])
                if k is not None and rnd.random() >= self_p:
                    k_ver = None
        algi.kare_ver(t, av, k_ver)

        if hata.yasa_hz > 0.0 and t - son_yasa_t < 1.0 / hata.yasa_hz - 1e-9:
            av.adim(dt, t)
            t += dt
            continue
        dt_yasa = dt if son_yasa_t < 0.0 else max(t - son_yasa_t, dt)
        son_yasa_t = t
        n_tik += 1
        poz = algi.oku(t)
        yaw_olc = algi.yaw_oku(t)
        roll_olc, pitch_olc = algi.tutum_oku(t)
        if poz is not None:
            gor += 1

        # ── KOR KOPRU (bbox_ibvs.py:1140-1159 ile AYNI semantik) ──────────
        kopru = False
        if poz is not None:
            if not kop_gecmis or abs(t - kop_gecmis[-1][0]) > 1e-9:
                kop_gecmis.append((t, poz[0], poz[1], poz[2], poz[3]))
                if len(kop_gecmis) > 6:
                    kop_gecmis.pop(0)
        elif kopru_s > 0.0 and len(kop_gecmis) >= 2:
            _a, _b = kop_gecmis[-2], kop_gecmis[-1]
            _yas = t - _b[0]
            _dtk = _b[0] - _a[0]
            if 1e-3 < _dtk < 0.6 and 0.0 < _yas <= kopru_s:
                _vx = max(-kopru_kirp, min(kopru_kirp, (_b[1] - _a[1]) / _dtk))
                _vy = max(-kopru_kirp, min(kopru_kirp, (_b[2] - _a[2]) / _dtk))
                poz = (_b[1] + _vx * _yas, _b[2] + _vy * _yas, _b[3], _b[4])
                kopru = True
                kop_kare += 1
                # ⚠ NEDEN: koprunun VARSAYDIGI piksel hizi ile hedefin
                # GERCEK piksel hizi. Ikisi ayrisiyorsa kopru kendi yaw
                # duzeltmemizi/jitteri ekstrapole ediyor demektir.
                kop_vpx.append(math.hypot(_vx, _vy))
                if k is not None and _k_onc is not None and t - _k_onc[0] > 1e-6:
                    kop_vpx_ger.append(math.hypot(k[0] - _k_onc[1],
                                                  k[1] - _k_onc[2]) / (t - _k_onc[0]))
                if k is not None:
                    kop_hata_px.append(math.hypot(poz[0] - k[0], poz[1] - k[1]))
                else:
                    kop_hata_px.append(float("nan"))   # hedef kadrajda bile yok

        kutu_bu_tik = (poz is not None and not kopru)

        if poz is None or kopru:
            bosluk += 1
        if poz is None:
            # ⚠ TANI KAPISI (kopru_geri): kopru penceresi bitince, DONACAK
            # komut kopruden kalan ZEHIRLI komut mu, yoksa son GERCEK komut
            # mu? Bu secenek son gercek komutu geri koyar -> "kopru surus
            # sirasinda mi yoksa BIRAKTIGI komutla mi zarar veriyor" ayrisir.
            if kopru_geri and son_gercek_cmd is not None and son_cmd is not None \
                    and son_cmd != son_gercek_cmd[:2]:
                av.setpoint(son_gercek_cmd[0], son_gercek_cmd[1],
                            son_gercek_cmd[2], son_gercek_cmd[3], t)
                son_cmd = son_gercek_cmd[:2]
            kayip += 1
            if kayip >= kayip_m:
                break
        else:
            if not kopru:
                kayip = 0
                n_kutu += 1
                if t_ilk_kutu is not None and bosluk > 0:
                    pass
                bosluk = 0
                if t_ilk_kutu is None:
                    t_ilk_kutu = t
                    tik_ilk = n_tik
                t_son_kutu = t
                tik_son = n_tik
                kilit = False
                tx, ty, onde = OM._aci(av, hx, hy, hz)
                son_eps = abs(math.degrees(math.atan(tx)))
            elif kopru_temas:
                kayip = 0
            else:
                kayip += 1
                if kayip >= kayip_m:
                    break
            cx, cy, w, h = poz
            los = yaw_olc + math.atan((cx - cfg.CX_NISAN) / F_YASA)
            if pencere > 0.0:
                if gecmis:
                    onc = gecmis[-1][1]
                    los_a = onc + ((los - onc + math.pi) % (2 * math.pi) - math.pi)
                else:
                    los_a = los
                gecmis.append((t, los_a))
                while gecmis and t - gecmis[0][0] > pencere:
                    gecmis.pop(0)
                if len(gecmis) >= 3:
                    n_ = len(gecmis)
                    tm = sum(g[0] for g in gecmis) / n_
                    lm = sum(g[1] for g in gecmis) / n_
                    sxx = sum((g[0] - tm) ** 2 for g in gecmis)
                    lam_f = (sum((g[0] - tm) * (g[1] - lm) for g in gecmis) / sxx) if sxx > 1e-12 else 0.0
                    lam_f = max(-6.0, min(6.0, lam_f))
                else:
                    lam_f = 0.0
            n_tik_temas += 1

            # ── eps_hizi: KADRAJ ICI kayma hizi (canli kod: 0.30 s LS) ────
            eps_hizi = 0.0
            if eps_kd:
                if cfg.ROLL_TELAFI:
                    _az_s, _ = IB.los_seviye(cx, cy, roll_olc, pitch_olc, cfg)
                else:
                    _az_s = math.atan((cx - cfg.CX_NISAN) / F_YASA)
                eps_gecmis.append((t, _az_s))
                while eps_gecmis and t - eps_gecmis[0][0] > 0.30:
                    eps_gecmis.pop(0)
                if len(eps_gecmis) >= 3:
                    _kk = len(eps_gecmis)
                    _tm = sum(g[0] for g in eps_gecmis) / _kk
                    _em = sum(g[1] for g in eps_gecmis) / _kk
                    _sxx = sum((g[0] - _tm) ** 2 for g in eps_gecmis)
                    if _sxx > 1e-12:
                        eps_hizi = max(-6.0, min(6.0, sum(
                            (g[0] - _tm) * (g[1] - _em) for g in eps_gecmis) / _sxx))

            boyut = math.sqrt(w * h)
            if not terminal and boyut >= cfg.TERMINAL_BOYUT:
                terminal = True
            vx, vy, vz, yaw_cmd, hiz_I, tani = IB.komut(
                cx, cy, w, h, yaw_olc, hiz_I, dt_yasa, cfg, terminal,
                (lam_f, 0.0),
                pitch_olc, av.vz, None, roll_olc, av.yaw_hizi, psi_v_yasa,
                eps_hizi)
            if yasa_ici:
                psi_v_yasa = tani.get("psi_v")
            n_vz += 1
            _tav = cfg.VZ_MAX_TERM if terminal else cfg.VZ_MAX
            if abs(vz) >= 0.95 * _tav:
                vz_tavan += 1
            av.setpoint(vx, vy, vz, yaw_cmd, t)
            son_cmd = (vx, vy)
            if not kopru:
                son_gercek_cmd = (vx, vy, vz, yaw_cmd)
        if abs(math.degrees(av.yaw_hizi)) >= 0.95 * cfg.YAW_RATE_MAX_DEG:
            n_doyum += 1
        _k_onc = (t, k[0], k[1]) if k is not None else None
        av.adim(dt, t)
        t += dt

    hx, hy, hz, _, _, _ = hed.durum()
    tx, ty, onde = OM._aci(av, hx, hy, hz)
    if not onde:
        olum = "arka"
    elif abs(tx) > TX_MAX:
        olum = "yan"
    elif abs(ty) > TY_MAX:
        olum = "dikey"
    else:
        olum = "ici"

    temas = (t_son_kutu - t_ilk_kutu) if (t_ilk_kutu is not None and
                                          t_son_kutu is not None) else 0.0
    _kh = [x for x in kop_hata_px if x == x]
    return {
        "en_yakin": en_yakin,
        "iska_adil": en_yakin_kesik if kilit else en_yakin,
        "omur": t, "temas": temas,
        "gorus": gor / max(top, 1),
        "n_kutu": n_kutu,
        "sureklilik": (n_kutu / max(1, tik_son - tik_ilk + 1)
                       if (tik_ilk is not None and tik_son > tik_ilk) else float("nan")),
        "kutu_orani_faz": n_kutu / max(1, n_tik),
        "olum": olum, "olum_eps": son_eps,
        "kop_kare": kop_kare,
        "kop_hata": (st.median(_kh) if _kh else float("nan")),
        "kop_kadraj_disi": (sum(1 for x in kop_hata_px if x != x)
                            / max(len(kop_hata_px), 1)) if kop_hata_px else 0.0,
        "kop_vpx": (st.median(kop_vpx) if kop_vpx else float("nan")),
        "kop_vpx_ger": (st.median(kop_vpx_ger) if kop_vpx_ger else float("nan")),
        "sap": (st.median(sap_hep) if sap_hep else float("nan")),
        "sap_k": (st.median(sap_kutulu) if sap_kutulu else float("nan")),
        "sap90": (sum(1 for x in sap_hep if x > 90.0) / len(sap_hep)) if sap_hep else 0.0,
        "sapc": (st.median(sapc_hep) if sapc_hep else float("nan")),
        "sapc_k": (st.median(sapc_kutulu) if sapc_kutulu else float("nan")),
        "sapc90": (sum(1 for x in sapc_hep if x > 90.0) / len(sapc_hep)) if sapc_hep else 0.0,
        "yaw_doyum": n_doyum / max(top, 1),
        "vz_tavan": vz_tavan / max(n_vz, 1),
        "ayrim": ayrim_ey, "yuks": yuks_ey,
    }


def parti(n=120, senaryo="saha", **kw):
    return [kosu(faz0=faz_dagilim(senaryo, i, n), tohum=i, **kw)
            for i in range(n)]


def _med(x):
    y = [v for v in x if v == v]
    return st.median(y) if y else float("nan")


def ozet(r):
    e = [x["en_yakin"] for x in r]
    a = [x["iska_adil"] for x in r]
    return {
        "iska": _med(e), "iyi": min(e), "adil": _med(a),
        "omur": _med([x["omur"] for x in r]),
        "temas": _med([x["temas"] for x in r]),
        "sur": _med([x["sureklilik"] for x in r]),
        "kor": _med([x["kutu_orani_faz"] for x in r]),
        "sap": _med([x["sap"] for x in r]),
        "sap_k": _med([x["sap_k"] for x in r]),
        "sap90": _med([x["sap90"] for x in r]),
        "sapc": _med([x["sapc"] for x in r]),
        "sapc_k": _med([x["sapc_k"] for x in r]),
        "sapc90": sum(x["sapc90"] for x in r) / len(r),
        "eps": _med([x["olum_eps"] for x in r if x["olum_eps"] is not None]),
        "kopk": _med([x["kop_kare"] for x in r]),
        "koph": _med([x["kop_hata"] for x in r]),
        "kopd": _med([x["kop_kadraj_disi"] for x in r]),
        "kopv": _med([x["kop_vpx"] for x in r]),
        "kopvg": _med([x["kop_vpx_ger"] for x in r]),
        "vz": _med([x["vz_tavan"] for x in r]),
        "ayrim": _med([x["ayrim"] for x in r]),
        "yuks": _med([x["yuks"] for x in r]),
        "v3": sum(1 for x in e if x < 3.0),
        "v3a": sum(1 for x in a if x < 3.0),
        "n": len(r),
    }


BAS = ("  %-30s %7s %7s %7s %6s %6s %5s %6s %6s %5s %5s" %
       ("kurulum", "iska", "adil", "eniyi", "omur", "temas", "kor",
        "sapC", "sapC_k", ">90%", "<3m"))


def satir(ad, s):
    return ("  %-30s %6.2fm %6.2fm %6.2fm %5.2fs %5.2fs %5.2f %5.1f° %5.1f° "
            "%4.0f%% %2d/%d" %
            (ad, s["iska"], s["adil"], s["iyi"], s["omur"], s["temas"],
             s["kor"], s["sapc"], s["sapc_k"], 100 * s["sapc90"],
             s["v3a"], s["n"]))


N = 120
DEVIR = 15.7          # m — saha devir menzili p50 (gorev brifingi)


def kos(ad, senaryo="saha", det=None, yaz=True, **kw):
    d = OM.tezgah_b(**(det or {}))
    r = parti(n=kw.pop("n", N), senaryo=senaryo, dedektor=d,
              devir_m=kw.pop("devir_m", DEVIR), sure=20.0, **kw)
    s = ozet(r)
    if yaz:
        print(satir(ad, s), flush=True)
    return s


# ══════════════════════════════════════════════════════════════════════════
#  SINAMA — kopru KAPALI iken sim_omur.kosu ile ayni sayiyi vermeli
# ══════════════════════════════════════════════════════════════════════════
def sinama(n=16):
    kotu = []
    for i in range(n):
        kw = dict(faz0=i / n, tohum=i, devir_m=15.7, sure=8.0, cfg=SahaCfg)
        d = OM.tezgah_b()
        a = OM.kosu(dedektor=d, **kw)
        b = kosu(dedektor=d, kopru_s=0.0, eps_kd=False, **kw)
        if abs(a["en_yakin"] - b["en_yakin"]) > 1e-9 or abs(a["omur"] - b["omur"]) > 1e-9:
            kotu.append((i, a["en_yakin"], b["en_yakin"], a["omur"], b["omur"]))
    print("  GERILEME (kopru kapali == sim_omur.kosu): %s" %
          ("TAMAM (%d/%d)" % (n, n) if not kotu else "KALDI"))
    for x in kotu:
        print("    ! %s" % (x,))
    # eps_kd ACIK ama BURUN_KD=0 iken de AYNI olmali (yasa terimi 0 ile carpar)
    kotu2 = []
    for i in range(n):
        kw = dict(faz0=i / n, tohum=i, devir_m=15.7, sure=8.0, cfg=SahaCfg)
        d = OM.tezgah_b()
        a = kosu(dedektor=d, kopru_s=0.0, eps_kd=False, **kw)
        b = kosu(dedektor=d, kopru_s=0.0, eps_kd=True, **kw)
        if abs(a["en_yakin"] - b["en_yakin"]) > 1e-9:
            kotu2.append(i)
    print("  eps_hizi yolu BURUN_KD=0'da etkisiz: %s" %
          ("TAMAM" if not kotu2 else "KALDI (%d)" % len(kotu2)))
    return kotu + kotu2


# ══════════════════════════════════════════════════════════════════════════
#  BOLUMLER
# ══════════════════════════════════════════════════════════════════════════
def b_kopru():
    print("\n  === 1) KOR KOPRU — TABAN (saha karisimi, devir %.1f m) ===" % DEVIR)
    print(BAS)
    for ks in (0.0, 0.30, 0.60, 1.00):
        kos("kopru %.2f s" % ks, kopru_s=ks)
    print("  -- kopru TEMAS sayilsin (kayip sayacini sifirlar) --")
    for ks in (0.30, 0.60):
        kos("kopru %.2f s + temas" % ks, kopru_s=ks, kopru_temas=True)


def b_kopru_tani():
    print("\n  === 1b) KOPRU TANISI — nereye goturuyor, zarar NEREDEN ===")
    print("  %-24s %6s %6s %6s %8s %8s %7s %6s" %
          ("kurulum", "kopKar", "pxHata", "kadDis", "vpx_kop", "vpx_ger",
           "adil", "omur"))
    for sen in ("saha", "duz", "icinde"):
        for ks in (0.30, 0.60):
            s = kos("", senaryo=sen, kopru_s=ks, yaz=False)
            print("  %-24s %6.1f %6.0f %5.0f%% %7.0f  %7.0f  %6.2fm %5.2fs" %
                  ("%-7s kopru %.2f" % (sen, ks), s["kopk"], s["koph"],
                   100 * s["kopd"], s["kopv"], s["kopvg"], s["adil"],
                   s["omur"]), flush=True)
    print("  -- ZARAR NEREDEN: kopru penceresi bitince DONEN komut --")
    print(BAS)
    for sen in ("duz", "saha"):
        kos("%-7s taban" % sen, senaryo=sen)
        kos("%-7s kopru 0.60" % sen, senaryo=sen, kopru_s=0.60)
        kos("%-7s kopru 0.60 (geri al)" % sen, senaryo=sen, kopru_s=0.60,
            kopru_geri=True)
    print("  -- TOHUM SAGLAMLIGI: ayni sey, 240 kosu --")
    print(BAS)
    kos("duz taban n=240", senaryo="duz", n=240)
    kos("duz kopru 0.60 n=240", senaryo="duz", n=240, kopru_s=0.60)


def b_kopru_manevra():
    print("\n  === 2) KOPRU x MANEVRA — donuse giris/cikis ===")
    for sen in ("duz", "giris", "icinde", "cikis"):
        print("  -- senaryo: %s --" % sen)
        print(BAS)
        for ks in (0.0, 0.30, 0.60):
            kos("%-7s kopru %.2f" % (sen, ks), senaryo=sen, kopru_s=ks)


def b_kopru_yanlis():
    print("\n  === 3) KOPRU x YANLIS NESNE (sahada karelerin %0.8'i >100 px) ===")
    print(BAS)
    for carp, ad in ((1.0, "saha x1"), (3.0, "x3"), (10.0, "x10 (sel)")):
        h = HataAyari(yanlis_hiz=0.085 * carp)
        for ks in (0.0, 0.30, 0.60):
            kos("%-10s kopru %.2f" % (ad, ks), hata=h, kopru_s=ks)
    print("  -- piksel hizi kirpmasi (canli ±900 px/s) --")
    h = HataAyari(yanlis_hiz=0.085 * 3.0)
    for kirp in (900.0, 300.0, 120.0):
        kos("x3 kopru 0.60 kirp %.0f" % kirp, hata=h, kopru_s=0.60,
            kopru_kirp=kirp)


def b_kopru_kayip():
    print("\n  === 4) KOPRU + KAYIP_M (birikimli kor ucus) ===")
    print(BAS)
    for km in (20, 60):
        for ks in (0.0, 0.30, 0.60):
            kos("KAYIP_M %-3d kopru %.2f" % (km, ks), kayip_m=km, kopru_s=ks)
    print("  -- ayni sey, donus icinde (en zor) --")
    for km in (20, 60):
        for ks in (0.0, 0.60):
            kos("icinde K%-3d kopru %.2f" % (km, ks), senaryo="icinde",
                kayip_m=km, kopru_s=ks)


def b_yaw():
    print("\n  === 5) SESSIZ BURUN (K_YAW) ===")
    print("  -- PN ACIK (varsayilan 1.6): K_YAW yalniz BURNU etkiler --")
    print(BAS)
    for ky in (1.0, 0.6, 0.3):
        kos("K_YAW %.1f (PN 1.6)" % ky, cfg=cfg_ile(K_YAW=ky))
    print("  -- PN KAPALI (ab_omur'un plani): K_YAW HIZ YONUNU de kisar --")
    for ky in (1.0, 0.6, 0.3):
        kos("K_YAW %.1f (PN 0)" % ky, cfg=cfg_ile(K_YAW=ky, PN_N=0.0))
    print("  -- hedef HIZLI kayarken (donus icinde), KAYIP_M 60 --")
    for ky in (1.0, 0.3):
        for pn in (1.6, 0.0):
            kos("icinde K_YAW %.1f PN %.1f" % (ky, pn), senaryo="icinde",
                kayip_m=60, cfg=cfg_ile(K_YAW=ky, PN_N=pn))


def b_burunkd():
    print("\n  === 6) BURUN PD (BURUN_KD) ===")
    print(BAS)
    for kd in (0.0, 0.15, 0.30, 0.60):
        kos("BURUN_KD %.2f" % kd, cfg=cfg_ile(BURUN_KD=kd))
    print("  -- piksel jitter 3 ve 5 px (gurultuyle besle) --")
    for j in (3.0, 5.0):
        h = HataAyari(jitter_px=j)
        for kd in (0.0, 0.30, 0.60):
            kos("jitter %.0f px BURUN_KD %.2f" % (j, kd), hata=h,
                cfg=cfg_ile(BURUN_KD=kd))
    print("  -- KD + sessiz burun birlikte (onerilen esleme) --")
    for kd in (0.0, 0.30):
        kos("K_YAW 0.3 + KD %.2f" % kd, cfg=cfg_ile(K_YAW=0.3, BURUN_KD=kd))


def b_kadraj():
    print("\n  === 7) KADRAJ ONCELIGI (KADRAJ_ESIK_DEG) ===")
    print(BAS)
    for ke in (0.0, 30.0, 45.0, 61.0):
        kos("KADRAJ_ESIK %.0f" % ke, cfg=cfg_ile(KADRAJ_ESIK_DEG=ke))
    print("  -- HEDEF KACAR MI: uzak devir (menzil acilirsa faz bosa gecer) --")
    for dm in (22.0, 30.0, 40.0):
        for ke in (0.0, 45.0):
            kos("devir %.0f m esik %.0f" % (dm, ke), devir_m=dm,
                cfg=cfg_ile(KADRAJ_ESIK_DEG=ke))
    print("  -- KENAR CEZASI GUCLU (sahanin 'kenarda kayip 0.609' rejimi) --")
    kn = [(5.0, 0.0), (35.0, 0.0), (45.0, -0.10), (55.0, -0.25), (65.0, -0.40)]
    _yedek = OM.KENAR_EGRI[:]
    try:
        OM.KENAR_EGRI[:] = kn
        for ke in (0.0, 45.0):
            kos("kenar-guclu esik %.0f" % ke, cfg=cfg_ile(KADRAJ_ESIK_DEG=ke))
        for kd in (0.0, 0.30):
            kos("kenar-guclu BURUN_KD %.2f" % kd, cfg=cfg_ile(BURUN_KD=kd))
        for ky in (1.0, 0.3):
            kos("kenar-guclu K_YAW %.1f" % ky, cfg=cfg_ile(K_YAW=ky))
    finally:
        OM.KENAR_EGRI[:] = _yedek


def b_kayip():
    print("\n  === 8) KAYIP_M tek basina ===")
    print(BAS)
    for km in (20, 30, 45, 60, 90):
        kos("KAYIP_M %d" % km, kayip_m=km)


def b_dikey():
    print("\n  === 9) DIKEY KANAL bozuluyor mu ===")
    print("  %-30s %7s %7s %6s %6s" % ("kurulum", "ayrim", "yuks", "vz%", "iska"))
    kur = [("taban", dict()),
           ("kopru 0.60", dict(kopru_s=0.60)),
           ("K_YAW 0.3", dict(cfg=cfg_ile(K_YAW=0.3))),
           ("K_YAW 0.3 PN0", dict(cfg=cfg_ile(K_YAW=0.3, PN_N=0.0))),
           ("BURUN_KD 0.30", dict(cfg=cfg_ile(BURUN_KD=0.30))),
           ("KADRAJ_ESIK 45", dict(cfg=cfg_ile(KADRAJ_ESIK_DEG=45.0))),
           ("KAYIP_M 60", dict(kayip_m=60)),
           ("kopru 0.60 + K60", dict(kopru_s=0.60, kayip_m=60))]
    for ad, kw in kur:
        s = kos(ad, yaz=False, **kw)
        print("  %-30s %+6.2fm %+6.1f° %5.0f%% %5.2fm" %
              (ad, s["ayrim"], s["yuks"], 100 * s["vz"], s["adil"]), flush=True)


def b_sinir():
    print("\n  === 10) SINIR DURUMLAR ===")
    kur = [("taban", dict()),
           ("kopru 0.60", dict(kopru_s=0.60)),
           ("K_YAW 0.3 PN0", dict(cfg=cfg_ile(K_YAW=0.3, PN_N=0.0))),
           ("KADRAJ_ESIK 45", dict(cfg=cfg_ile(KADRAJ_ESIK_DEG=45.0))),
           ("BURUN_KD 0.30", dict(cfg=cfg_ile(BURUN_KD=0.30)))]
    for ad_s, kw_s in (("cok yakin devir 5 m", dict(devir_m=5.0)),
                       ("cok uzak devir 40 m", dict(devir_m=40.0)),
                       ("aspect +40", dict(devir_aci=40.0)),
                       ("aspect -40", dict(devir_aci=-40.0)),
                       ("hedef TERS yon", dict(hedef_yon=-1))):
        print("  -- %s --" % ad_s)
        print(BAS)
        for ad, kw in kur:
            d = dict(kw)
            d.update(kw_s)
            kos("%-16s %s" % (ad_s.split()[0], ad), **d)


def b_ek():
    print("\n  === 11) HEDEFLI KONTROLLER ===")
    # (a) K_YAW YALNIZ BURNU MU ETKILIYOR? — yasa koduna dogrudan sor.
    print("  (a) K_YAW hiz yonunu de kisiyor mu (bbox_ibvs.py:874/886)")
    print("      eps_yaw = +30°, iris_yaw = 0, ilk kare (psi_v=None)")
    for pn in (1.6, 0.0):
        for ky in (1.0, 0.3):
            c = cfg_ile(K_YAW=ky, PN_N=pn)
            cx = IB.geo.CX + IB.geo.FX * math.tan(math.radians(30.0))
            vx, vy, vz, yaw_cmd, _, tani = IB.komut(
                cx, c.CY_NISAN, 12.0, 6.0, 0.0, 18.0, 0.047, c, False,
                (0.0, 0.0), 0.0, 0.0, None, 0.0, 0.0, None, 0.0)
            print("      PN %.1f K_YAW %.1f -> burun %+6.1f°  HIZ YONU %+6.1f°"
                  % (pn, ky, math.degrees(yaw_cmd),
                     math.degrees(math.atan2(vy, vx))), flush=True)
    # (b) KADRAJ_ESIK gercekten kisiyor mu? hiz_I doyunca terim OLU kalir.
    print("  (b) KADRAJ_ESIK: pay = (esik-|eps|)/esik, taban hiz_I")
    for hi in (18.0, 24.0):
        for ke in (0.0, 45.0):
            c = cfg_ile(KADRAJ_ESIK_DEG=ke)
            cx = IB.geo.CX + IB.geo.FX * math.tan(math.radians(40.0))
            _, _, _, _, _, tani = IB.komut(
                cx, c.CY_NISAN, 8.0, 4.0, 0.0, hi, 0.047, c, False,
                (0.0, 0.0), 0.0, 0.0, None, 0.0, 0.0, None, 0.0)
            print("      hiz_I %.0f esik %-4.0f -> v_los %5.2f m/s"
                  % (hi, ke, tani["v_los"]), flush=True)
    # (c) YAKIN MENZIL (5 m) ATFI: zarar K_YAW'in mi PN kapatmanin mi?
    print("  (c) cok yakin devir 5 m — K_YAW / PN atfi")
    print(BAS)
    for pn in (1.6, 0.0):
        for ky in (1.0, 0.3):
            kos("5m K_YAW %.1f PN %.1f" % (ky, pn), devir_m=5.0,
                cfg=cfg_ile(K_YAW=ky, PN_N=pn))
    # (d) BURUN_KD ve KADRAJ_ESIK: n=240 ile gurultuden ayir
    print("  (d) n=240 tekrar (etki gurultunun icinde mi)")
    print(BAS)
    kos("taban n=240", n=240)
    kos("BURUN_KD 0.30 n=240", n=240, cfg=cfg_ile(BURUN_KD=0.30))
    kos("KADRAJ_ESIK 45 n=240", n=240, cfg=cfg_ile(KADRAJ_ESIK_DEG=45.0))
    kos("K_YAW 0.3 n=240", n=240, cfg=cfg_ile(K_YAW=0.3))
    kos("kopru 0.60 n=240", n=240, kopru_s=0.60)
    kos("KAYIP_M 60 n=240", n=240, kayip_m=60)
    kos("K60 + kopru 0.60 n=240", n=240, kayip_m=60, kopru_s=0.60)


def b_kosullu():
    """DURUSTLUK BOLUMU: her kaldirac icin KAZANABILECEGI rejimi ara.
    Kirmaya calisiyoruz; kirilmiyorsa bu ONUN LEHINE kanittir."""
    print("\n  === 12) KOSULLU — kaldiraclarin KAZANDIGI rejim var mi ===")
    print("  (a) COK KISA kopru (1-4 kare) kurtarir mi? [K20 ve K60]")
    print(BAS)
    for km in (20, 60):
        for ks in (0.0, 0.05, 0.10, 0.15, 0.20, 0.30):
            kos("K%-2d kopru %.2f" % (km, ks), n=240, kayip_m=km, kopru_s=ks)
    print("  (b) BURUN_KD kendi tasarim rejiminde (donus icinde, K60)")
    print(BAS)
    for kd in (0.0, 0.15, 0.30):
        kos("icinde K60 BURUN_KD %.2f" % kd, senaryo="icinde", n=240,
            kayip_m=60, cfg=cfg_ile(BURUN_KD=kd))
    print("  (c) KADRAJ_ESIK kendi rejiminde (K60 + kenar cezasi guclu)")
    print(BAS)
    _yedek = OM.KENAR_EGRI[:]
    try:
        OM.KENAR_EGRI[:] = [(5.0, 0.0), (35.0, 0.0), (45.0, -0.10),
                            (55.0, -0.25), (65.0, -0.40)]
        for ke in (0.0, 30.0, 45.0):
            kos("kenar-guclu K60 esik %.0f" % ke, n=240, kayip_m=60,
                cfg=cfg_ile(KADRAJ_ESIK_DEG=ke))
        print("  (d) K_YAW kenar-guclu + K60 (kadraji tutmasi gereken yer)")
        print(BAS)
        for ky in (1.0, 0.6, 0.3):
            kos("kenar-guclu K60 K_YAW %.1f" % ky, n=240, kayip_m=60,
                cfg=cfg_ile(K_YAW=ky))
    finally:
        OM.KENAR_EGRI[:] = _yedek
    print("  (e) KAYIP_M 60'i kirmaya calis: kotu tarafi var mi")
    print(BAS)
    for sen in ("duz", "giris", "icinde", "cikis"):
        kos("%-7s K20" % sen, senaryo=sen, n=240, kayip_m=20)
        kos("%-7s K60" % sen, senaryo=sen, n=240, kayip_m=60)
    for dm in (5.0, 22.0, 40.0):
        kos("devir %.0f m K20" % dm, n=120, devir_m=dm, kayip_m=20)
        kos("devir %.0f m K60" % dm, n=120, devir_m=dm, kayip_m=60)


def main():
    ne = sys.argv[1] if len(sys.argv) > 1 else "hepsi"
    if ne in ("hepsi", "sinama"):
        sinama()
        T.dogrula()
    for ad, fn in (("kopru", b_kopru), ("kopru_tani", b_kopru_tani),
                   ("kopru_manevra", b_kopru_manevra),
                   ("kopru_yanlis", b_kopru_yanlis),
                   ("kopru_kayip", b_kopru_kayip), ("yaw", b_yaw),
                   ("burunkd", b_burunkd), ("kadraj", b_kadraj),
                   ("kayip", b_kayip), ("dikey", b_dikey), ("sinir", b_sinir),
                   ("ek", b_ek), ("kosullu", b_kosullu)):
        if ne in ("hepsi", ad):
            fn()


if __name__ == "__main__":
    main()

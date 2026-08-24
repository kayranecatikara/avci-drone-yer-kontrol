# -*- coding: utf-8 -*-
"""Deney kosumu: yatay yasa varyantlarini AYNI tesiste karsilastirir.

⚠ Yasa kodu degistirilmez; bbox_ibvs.komut() aynen cagrilir. PN varyantinda
yalnizca komutun YATAY bileseni degistirilir, dikey/hiz kanallari yasadan
gelir. Boylece fark tek degiskene indirgenir.

⚠ OLCUM HATASI (2026-08-16): yasa artik GERCEK durumu gormuyor —
tesis.Algi'dan gecen GECIKMELI/GURULTULU/YANLI olcumu goruyor:
    * kutu   : gecmis bir kareden  (yakalama + dedektor cikarimi)
    * iris_yaw: ayri, cok daha KUCUK gecikmeli telemetriden
Ikisinin zaman uyumsuzlugu SAHTE LOS HIZI uretir — oyunda olculen ama eski
tesiste TANIMI GEREGI imkansiz olan ariza kipi. `hata=` ile kapatilabilir:
    kosu(hata=T.HataAyari.eski())     -> eski (kusursuz) tesis
    kosu(hata=T.HataAyari.tek("gecikme"))  -> yalniz o kaynak
"""
import os, sys, math

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "kopru", "gazebo_kaynak"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tesis as T                                   # noqa: F401 (T.HataAyari)
from tesis import Avci, Hedef, Olcum, kadraj, F_YASA, HataAyari, Algi
from control.guidance import bbox_ibvs as IB


def _medyan(x):
    if not x:
        return 0.0
    y = sorted(x)
    n = len(y)
    return y[n // 2] if n % 2 else 0.5 * (y[n // 2 - 1] + y[n // 2])


def kosu(cfg=IB.Cfg, N=0.0, burun_los=False, tau=0.10, pencere=0.0, faz0=0.0, devir_m=13.0,
         yasa_ici=False, kayit=False,
         devir_aci=0.0, sure=25.0, dt=1 / 62.0, gurultu=True, jitter=1.0,
         tohum=0, hedef_yon=+1, hedef_hiz=None, hata=None):
    """Tek angajman. N=0 -> yasanin kendi yatay kanali. N>0 -> PN.

    hata : tesis.HataAyari — olcum hata modeli. None ise GERCEKCI varsayilan
           (eski davranis icin HataAyari.eski()). `gurultu`/`jitter` yalniz
           hata=None iken gecerlidir (geriye uyumluluk).
    """
    if hata is None:
        hata = HataAyari(tespit_kaybi=bool(gurultu), jitter_px=float(jitter))
    algi = Algi(hata, tohum=tohum)
    if hedef_hiz is not None:
        eski = Olcum.HEDEF_HIZ
        Olcum.HEDEF_HIZ = hedef_hiz
    hed = Hedef(faz0=faz0, yon=hedef_yon)
    hx, hy, hz, hvx, hvy, _ = hed.durum()
    hdg = math.atan2(hvy, hvx)
    # devir noktasi: hedefin gerisinde devir_m, gorus hattina devir_aci ile
    yon = hdg + math.pi + math.radians(devir_aci)
    av = Avci(x=hx + devir_m * math.cos(yon), y=hy + devir_m * math.sin(yon),
              z=hz - 3.0, yaw=hdg, max_accel=cfg.MAX_ACCEL, v_max=cfg.V_TOPLAM_MAX,
              vz_max=cfg.VZ_MAX, yaw_rate_max=cfg.YAW_RATE_MAX_DEG)
    av.vx, av.vy = Olcum.HEDEF_HIZ * math.cos(hdg), Olcum.HEDEF_HIZ * math.sin(hdg)
    av.yaw = math.atan2(hy - av.y, hx - av.x)          # burun hedefe (devir ani)

    psi_v = math.atan2(av.vy, av.vx)
    psi_v_yasa = None            # yasa_ici modunda komut()'a geri beslenir
    hiz_I = Olcum.HEDEF_HIZ
    t = 0.0; kayip = 0; terminal = False
    los_o = None; t_o = None; lam_f = 0.0
    gecmis = []          # pencere >0 ise (t, los_acilmis) yigini
    en_yakin = 1e9; gor = 0; top = 0
    iz = []
    son_yasa_t = -1e9    # yasa dongusu (hata.yasa_hz) icin
    # tani: lam_sisme'yi arac/pn_kiyas.py ile AYNI tanimla olcelim
    #   lam = |3-ornek tabanli turev|, p95 alinir, sonra oran.
    tn_t = []; tn_yasa = []; tn_truth = []; tn_yas = []; tn_yawyas = []

    while t < sure:
        hed.adim(dt)
        hx, hy, hz, hvx, hvy, _ = hed.durum()
        av._hedef_yon = math.atan2(hvy, hvx)
        k = kadraj(av, hx, hy, hz)
        top += 1
        en_yakin = min(en_yakin, math.dist((av.x, av.y, av.z), (hx, hy, hz)))

        # ── OLCUM BORU HATTI ──────────────────────────────────────────────
        # ⚠ Yasa artik av.yaw'i ve k'yi DOGRUDAN gormuyor. Kutu GECMISTEN,
        # iris_yaw AYRI (ve daha bayat) bir kanaldan geliyor.
        algi.kare_ver(t, av, k)
        # yasa dongusu 21.3 Hz (OLCULDU); arada setpoint TUTULUR
        if hata.yasa_hz > 0.0 and t - son_yasa_t < 1.0 / hata.yasa_hz - 1e-9:
            av.adim(dt, t)
            t += dt
            continue
        # ⚠ Yasaya verilen dt de YASANIN dt'si olmali (sim adimi degil):
        # lam kestirimi, EMA ve integral hepsi bunu kullaniyor.
        dt_yasa = dt if son_yasa_t < 0.0 else max(t - son_yasa_t, dt)
        son_yasa_t = t
        poz = algi.oku(t)
        yaw_olc = algi.yaw_oku(t)
        roll_olc, pitch_olc = algi.tutum_oku(t)
        if poz is not None:
            gor += 1

        if poz is None:
            kayip += 1
            if kayip >= 20:
                break
        else:
            kayip = 0
            cx, cy, w, h = poz
            # ⚠ LOS'un IKI PARCASI DA OLCUMDUR: yaw bayat telemetriden,
            # eps gecmis bir kareden. Eski tesiste ikisi de anlik GERCEKTI ve
            # bu satir truth'un TANIM GEREGI aynisini veriyordu.
            los = yaw_olc + math.atan((cx - cfg.CX_NISAN) / F_YASA)
            tn_t.append(t)
            tn_yasa.append(math.degrees(los))
            tn_truth.append(math.degrees(math.atan2(hy - av.y, hx - av.x)))
            tn_yas.append(algi.son_yas)
            tn_yawyas.append(algi.yaw_yas)
            # ── LOS HIZI KESTIRIMI ──────────────────────────────────
            # ⚠ Ardisik-fark turevi gurultuyu sigma_px/(F*dt) ile buyutur:
            # 1 px jitter ve dt=1/62 -> 21 °/s sahte LOS hizi. PN bunu N kati
            # yapar. Bu yuzden pencere>0 ise EN KUCUK KARELER EGIMI kullanilir
            # (gurultuyu ~sqrt(orneksayisi) kadar bastirir ve dt'ye duyarsiz).
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
            else:
                lam = 0.0
                if los_o is not None and t_o is not None and t - t_o > 1e-6:
                    lam = ((los - los_o + math.pi) % (2 * math.pi) - math.pi) / (t - t_o)
                    lam = max(-6.0, min(6.0, lam))
                los_o, t_o = los, t
                a = 1.0 if tau <= 0 else min(1.0, dt_yasa / max(tau, dt_yasa))
                lam_f += a * (lam - lam_f)

            boyut = math.sqrt(w * h)
            if not terminal and boyut >= cfg.TERMINAL_BOYUT:
                terminal = True
            # ⚠ iris_yaw/roll/pitch OLCUMDEN (ayni bayat ATTITUDE ornegi).
            # vz ve yaw_hizi hala gercek: SDK hizi OLCULEN kanal olarak TAZE
            # (v_yas_s p90 0.031 s), yaw_hizi ise tesisin kendi turevi.
            vx, vy, vz, yaw_cmd, hiz_I, tani = IB.komut(
                cx, cy, w, h, yaw_olc, hiz_I, dt_yasa, cfg, terminal,
                (lam_f, 0.0),
                pitch_olc, av.vz, None, roll_olc, av.yaw_hizi, psi_v_yasa)
            if yasa_ici:
                psi_v_yasa = tani.get("psi_v")
            if N > 0.0:
                psi_v += N * lam_f * dt_yasa
                v = math.hypot(vx, vy)
                vx, vy = v * math.cos(psi_v), v * math.sin(psi_v)
            else:
                psi_v = math.atan2(vy, vx)
            if burun_los:
                yaw_cmd = los
            av.setpoint(vx, vy, vz, yaw_cmd, t)
        if kayit:
            iz.append([round(t, 3),
                       round(av.x, 2), round(av.y, 2), round(av.z, 2),
                       round(math.degrees(av.yaw), 1), round(math.degrees(av.roll), 1),
                       round(hx, 2), round(hy, 2), round(hz, 2),
                       round(math.degrees(math.atan2(hvy, hvx)), 1),
                       (round(poz[0], 1) if poz else None),
                       (round(poz[1], 1) if poz else None),
                       (round(math.sqrt(poz[2] * poz[3]), 1) if poz else None),
                       round(math.dist((av.x, av.y, av.z), (hx, hy, hz)), 2)])
        av.adim(dt, t)
        t += dt

    if hedef_hiz is not None:
        Olcum.HEDEF_HIZ = eski

    # ── lam_sisme: arac/pn_kiyas.py:82-92 ile BIT-AYNI tanim ──────────────
    # 3-ornek tabanli turev, mutlak deger, p95; sonra yasa/truth orani.
    # Boylece simulator sayisi SAHA sayisiyla dogrudan kiyaslanabilir
    # (saha olcumu: 7 gorsel faz, medyan 5.9x, aralik 3.8-8.2, bir aykiri 52).
    def _hizlar(v):
        o = []
        for i in range(3, len(v)):
            d = tn_t[i] - tn_t[i - 3]
            if d > 1e-3:
                o.append(abs(((v[i] - v[i - 3] + 540) % 360 - 180) / d))
        return o

    def _p95(v):
        return sorted(v)[int(0.95 * (len(v) - 1))] if v else None

    lam_yasa = _p95(_hizlar(tn_yasa)) if len(tn_yasa) >= 8 else None
    lam_truth = _p95(_hizlar(tn_truth)) if len(tn_truth) >= 8 else None
    sisme = (lam_yasa / lam_truth
             if lam_yasa and lam_truth and lam_truth > 1e-6 else None)
    # LOS acisal hatasi: faz BASI ve faz SONU (ilk/son %20)
    hata_d = [((y - g + 540) % 360 - 180) for y, g in zip(tn_yasa, tn_truth)]
    n_ = len(hata_d)
    d_bas = d_son = None
    if n_ >= 10:
        m = max(1, n_ // 5)
        d_bas = sum(hata_d[:m]) / m
        d_son = sum(hata_d[-m:]) / m
    return {"en_yakin": en_yakin, "sure": t, "gorus": gor / max(top, 1),
            "iz": iz,
            "lam_yasa": lam_yasa, "lam_truth": lam_truth, "sisme": sisme,
            "los_hata_bas": d_bas, "los_hata_son": d_son,
            "los_hata_mutlak": (sum(abs(x) for x in hata_d) / n_) if n_ else None,
            "kutu_yas": _medyan(tn_yas), "yaw_yas": _medyan(tn_yawyas),
            "kare": n_}


def parti(n=40, **kw):
    return [kosu(faz0=i / n, tohum=i, **kw) for i in range(n)]


def satir(ad, r, gen=38):
    import statistics as st
    e = [x["en_yakin"] for x in r]
    return ("  %-*s%8.2fm%8.2fm%6d%6d%6d" %
            (gen, ad, st.median(e), min(e),
             sum(1 for x in e if x < 1.0), sum(1 for x in e if x < 2.0),
             sum(1 for x in e if x < 3.0)))


def baslik(gen=38):
    return ("  %-*s%9s%9s%6s%6s%6s" % (gen, "yasa", "medyan", "en iyi", "<1m", "<2m", "<3m")
            + "\n  " + "-" * (gen + 36))

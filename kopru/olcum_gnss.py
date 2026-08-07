# -*- coding: utf-8 -*-
"""
kopru/olcum_gnss.py — GNSS DUZELTICI ON OLCUMU (salt gozlem + OFFLINE A/B).

TAMAMEN PASIF: komut yok, arm yok, ucus yok. Hedef telemetrisi izlenir ve
kestirimler GERCEGE (get_debug_truth) karsi olculur.

Ne yapar:
  1) DoW bozulma parametrelerini CANLI okur (rate_hz, delay_s, aktif efektler)
     -> gnss duzelticinin dt ve telafi_sn ayari VERIDEN cikar.
  2) TABAN CIZGISI (su anki DoW kopru davranisi): ham bozuk konum + gps_guidance'in
     kendi kestiricisi (POS_EMA=0.4 / VEL_EMA=0.3) GERCEGE karsi:
       konum hatasi medyan/p99/maks, hiz siskinligi + gurultu, omega siskinligi.
  3) OFFLINE A/B: AYNI ham akis fusion/inovasyonlu_j_v2.GNSSDuzeltici'ye
     (CT-EKF) beslenir; dt ve telafi_sn taranir; ayni metrikler.
     -> "bu filtre tasinsa ne kazanirdik" sorusu UCMADAN cevaplanir.

Kullanim: python -m kopru.olcum_gnss [--sure 90]
"""
from __future__ import annotations

import argparse
import math
import time

import numpy as np

from sdk import drone_sdk as drone
from kopru.dow_kopru import CM
from kopru.olcum_faz1 import baglan_ve_dogrula

POS_EMA, VEL_EMA = 0.4, 0.3          # gps_guidance.Cfg:198-199 (birebir)


def izle(sure_s):
    """Taze hedef paketlerini + o andaki GERCEK konumu topla."""
    print(f"[GNSS] {sure_s:.0f} sn gozlem (komut YOK)...")
    ilk = drone.get_debug_truth()
    if not ilk.get("available"):
        print("[GNSS] get_debug_truth YOK — dogrulama yapilamaz (oyunda debug kapali).")
        return None, None
    kayit, bozulma = [], []
    son_ham = None
    t0 = time.monotonic()
    while time.monotonic() - t0 < sure_s:
        simdi = time.monotonic()
        ham = drone.get_target_location()
        dbg = drone.get_debug_truth()
        gercek = dbg["target"]["position"]
        p = dbg.get("corruption_params") or {}
        if p:
            bozulma.append((p.get("rate_hz"), p.get("delay_s"),
                            p.get("pos_noise_m"), p.get("dropout_remain_s")))
        if ham != son_ham:                       # TAZE paket
            son_ham = ham
            kayit.append((simdi, ham, gercek))
        time.sleep(0.01)
    return kayit, bozulma


def _hiz_1s(seri):
    """(t, (x,y,z)) serisinden ~1 s tabanli hiz — GERCEK icin (temiz)."""
    out, i0 = [], 0
    for i in range(len(seri)):
        while seri[i][0] - seri[i0][0] > 1.0:
            i0 += 1
        dt = seri[i][0] - seri[i0][0]
        if 0.6 <= dt <= 1.4 and i0 < i:
            out.append((seri[i][0],
                        (seri[i][1][0] - seri[i0][1][0]) / dt,
                        (seri[i][1][1] - seri[i0][1][1]) / dt))
    return out


def _omega(seri_hiz, taban_s=2.0):
    """Hiz serisinden isaretli donus hizi (rad/s), ~taban_s tabanli."""
    out, i0 = [], 0
    for i in range(len(seri_hiz)):
        while seri_hiz[i][0] - seri_hiz[i0][0] > taban_s:
            i0 += 1
        dt = seri_hiz[i][0] - seri_hiz[i0][0]
        if 0.6 * taban_s <= dt <= 1.4 * taban_s and i0 < i:
            h1 = math.atan2(seri_hiz[i][2], seri_hiz[i][1])
            h0 = math.atan2(seri_hiz[i0][2], seri_hiz[i0][1])
            dpsi = (h1 - h0 + math.pi) % (2 * math.pi) - math.pi
            out.append((seri_hiz[i][0], dpsi / dt))
    return out


def _hizala(a, b, tol=0.15):
    """(t,val) iki seriyi zaman esitle -> (val_a, val_b) ciftleri."""
    ciftler, j = [], 0
    for ta, va in a:
        while j + 1 < len(b) and abs(b[j+1][0] - ta) <= abs(b[j][0] - ta):
            j += 1
        if j < len(b) and abs(b[j][0] - ta) <= tol:
            ciftler.append((va, b[j][1]))
    return ciftler


def rapor_kestirim(ad, kest_pos, kest_vel, kest_om, ger_pos, ger_vel, ger_om):
    """kest_*/ger_*: (t, deger) serileri. Konum: (t,(x,y,z)) m."""
    # konum hatasi (zaman esli)
    hata = []
    j = 0
    for t, p in kest_pos:
        while j + 1 < len(ger_pos) and abs(ger_pos[j+1][0] - t) <= abs(ger_pos[j][0] - t):
            j += 1
        if j < len(ger_pos) and abs(ger_pos[j][0] - t) <= 0.15:
            g = ger_pos[j][1]
            hata.append(math.dist(p, g))
    h = np.array(hata) if hata else np.array([np.nan])
    # hiz buyuklugu siskinligi + gurultu
    kv = np.array([math.hypot(v[1], v[2]) for v in kest_vel])
    gv = np.array([math.hypot(v[1], v[2]) for v in ger_vel])
    oran = float(np.median(kv) / max(np.median(gv), 1e-6))
    ciftler = _hizala([(v[0], math.hypot(v[1], v[2])) for v in kest_vel],
                      [(v[0], math.hypot(v[1], v[2])) for v in ger_vel])
    sapma = np.array([a - b for a, b in ciftler]) if ciftler else np.array([np.nan])
    # omega siskinligi (mutlak deger medyani)
    ko = np.array([abs(o[1]) for o in kest_om]) if kest_om else np.array([np.nan])
    go = np.array([abs(o[1]) for o in ger_om]) if ger_om else np.array([np.nan])
    om_oran = float(np.median(ko) / max(np.median(go), 1e-9))
    print(f"  {ad:34s} | konum hata med {np.median(h):5.2f} p99 {np.percentile(h,99):6.2f} "
          f"maks {h.max():6.2f} m | hiz {np.median(kv):5.2f} m/s (siskinlik "
          f"{oran:4.2f}x) sapma-std {np.std(sapma):4.2f} | |omega| med "
          f"{np.median(ko):5.3f} rad/s (siskinlik {om_oran:4.2f}x)")
    return dict(hata_med=float(np.median(h)), hata_p99=float(np.percentile(h, 99)),
                hata_max=float(h.max()), siskinlik=oran,
                sapma_std=float(np.std(sapma)), om_oran=om_oran)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sure", type=float, default=90.0)
    a = ap.parse_args()
    baglan_ve_dogrula()
    kayit, bozulma = izle(a.sure)
    if not kayit or len(kayit) < 50:
        print("[GNSS] Yeterli veri yok.")
        return

    # ── 1) CANLI BOZULMA PARAMETRELERI ──
    araliklar = [kayit[i][0] - kayit[i-1][0] for i in range(1, len(kayit))]
    dt_med = float(np.median(araliklar))
    print(f"\n===== 1) DoW BOZULMA PARAMETRELERI (canli) =====")
    print(f"taze paket: {len(kayit)} adet, aralik medyan {dt_med*1000:.0f} ms "
          f"-> etkin {1/dt_med:.2f} Hz")
    if bozulma:
        rt = [b[0] for b in bozulma if b[0]]
        dl = [b[1] for b in bozulma if b[1] is not None]
        gr = [b[2] for b in bozulma if b[2] is not None]
        if rt:
            print(f"oyunun bildirdigi rate_hz: medyan {np.median(rt):.2f} "
                  f"({min(rt):.2f}..{max(rt):.2f})")
        if dl:
            print(f"oyunun bildirdigi delay_s: medyan {np.median(dl):.2f} s "
                  f"({min(dl):.2f}..{max(dl):.2f})  << telafi_sn ADAYI")
        if gr:
            print(f"konum gurultusu: medyan +-{np.median(gr):.1f} m")
    print(f"aktif efektler: {drone.get_active_corruption()}")

    # ── GERCEK seriler ──
    ger_pos = [(t, tuple(x / CM for x in g)) for t, _h, g in kayit]
    ger_vel = _hiz_1s(ger_pos)
    ger_om = _omega(ger_vel)
    print(f"\nGERCEK hedef: hiz medyan "
          f"{np.median([math.hypot(v[1], v[2]) for v in ger_vel]):.2f} m/s, "
          f"|omega| medyan {np.median([abs(o[1]) for o in ger_om]):.4f} rad/s "
          f"(yaricap {np.median([math.hypot(v[1],v[2]) for v in ger_vel])/max(np.median([abs(o[1]) for o in ger_om]),1e-9):.0f} m)")

    # ── 2) TABAN CIZGISI: ham + gps_guidance kestiricisi ──
    print(f"\n===== 2) TABAN CIZGISI (su anki kopru davranisi) =====")
    ham_pos = [(t, tuple(x / CM for x in h)) for t, h, _g in kayit]
    ham_vel_ard = []          # ardisik taze paket farki (gg'nin gordugu ham turev)
    for i in range(1, len(ham_pos)):
        dt = ham_pos[i][0] - ham_pos[i-1][0]
        if 0.05 <= dt <= 0.6:
            ham_vel_ard.append((ham_pos[i][0],
                                (ham_pos[i][1][0] - ham_pos[i-1][1][0]) / dt,
                                (ham_pos[i][1][1] - ham_pos[i-1][1][1]) / dt))
    rapor_kestirim("HAM (filtresiz)", ham_pos, ham_vel_ard, _omega(ham_vel_ard),
                   ger_pos, ger_vel, ger_om)

    est = None
    vel = np.zeros(3)
    t_son = None
    gg_pos, gg_vel = [], []
    for t, h, _g in kayit:
        p = np.array([x / CM for x in h])
        if est is None:
            est = p
        else:
            n = POS_EMA * p + (1 - POS_EMA) * est
            if t_son is not None and 1e-3 < t - t_son < 2.0:
                vel = VEL_EMA * ((n - est) / (t - t_son)) + (1 - VEL_EMA) * vel
            est = n
        t_son = t
        gg_pos.append((t, tuple(est)))
        gg_vel.append((t, float(vel[0]), float(vel[1])))
    rapor_kestirim("gps_guidance kestiricisi (EMA)", gg_pos, gg_vel, _omega(gg_vel),
                   ger_pos, ger_vel, ger_om)

    # ── 3) OFFLINE A/B: CT-EKF (fusion/inovasyonlu_j_v2) ──
    from fusion.inovasyonlu_j_v2 import GNSSDuzeltici
    print(f"\n===== 3) OFFLINE A/B — CT-EKF (fusion/inovasyonlu_j_v2, ayni ham akis) =====")
    print(f"  (dt = olculen taze aralik {dt_med:.2f} s; telafi_sn taraniyor)")
    en_iyi = None
    for telafi in (0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0):
        f = GNSSDuzeltici(telafi_sn=telafi, dt=dt_med)
        fp, fv, fo = [], [], []
        for t, h, _g in kayit:
            f.guncelle(h[0], h[1], h[2])          # cm (filtrenin birimi)
            d = f.durum_guduum()
            if d is None:
                continue
            # KONUM: telafi_sn kadar ONE tasinmis kestirim (guncelle ciktisi ile ayni)
            px, py, w = d["pos"][0], d["pos"][1], d["w"]
            vx, vy = d["vel"][0], d["vel"][1]
            if abs(w) < 1e-6:
                w = 1e-6
            s_, c_ = math.sin(w * telafi), math.cos(w * telafi)
            lx = px + (vx * s_ - vy * (1 - c_)) / w
            ly = py + (vx * (1 - c_) + vy * s_) / w
            fp.append((t, (lx / CM, ly / CM, d["pos"][2] / CM)))
            fv.append((t, vx / CM, vy / CM))
            fo.append((t, w))
        if len(fp) < 30:
            continue
        r = rapor_kestirim(f"CT-EKF telafi_sn={telafi:.2f}", fp, fv, fo,
                           ger_pos, ger_vel, ger_om)
        if en_iyi is None or r["hata_med"] < en_iyi[1]["hata_med"]:
            en_iyi = (telafi, r)
    if en_iyi:
        print(f"\n>> EN IYI telafi_sn (TEK BASINA) = {en_iyi[0]:.2f} "
              f"(konum hata medyan {en_iyi[1]['hata_med']:.2f} m, "
              f"hiz siskinligi {en_iyi[1]['siskinlik']:.2f}x, "
              f"omega siskinligi {en_iyi[1]['om_oran']:.2f}x)")

    # ── 4) UCTAN UCA ZINCIR: CT-EKF -> get_plane -> gps_guidance EMA ──
    # Yasa CT-EKF'i TEK BASINA gormez: get_plane ciktisina KENDI POS_EMA/VEL_EMA'sini
    # uygular. EMA yeni gecikme BINDIRIR (tau ~ dt*(1-a)/a) -> iki katman birbirini
    # yiyebilir. Yasanin GERCEKTEN gordugu sey burada olculur; telafi_sn zincire
    # gore yeniden taranir (kopru tarafi ayari, yasaya dokunulmaz).
    print(f"\n===== 4) UCTAN UCA ZINCIR (CT-EKF -> gps_guidance EMA) =====")
    print(f"  (EMA'nin ekledigi gecikme ~ dt*(1-a)/a = {dt_med*(1-POS_EMA)/POS_EMA:.2f} s"
          f" -> zincir optimumu 1.0'in USTUNE kayabilir)")
    zincir_en_iyi = None
    for telafi in (0.75, 1.0, 1.25, 1.5, 1.75, 2.0):
        f = GNSSDuzeltici(telafi_sn=telafi, dt=dt_med)
        z_est = None
        z_vel = np.zeros(3)
        z_tson = None
        zp, zv = [], []
        son_cikti = None
        for t, h, _g in kayit:
            f.guncelle(h[0], h[1], h[2])
            d = f.durum_guduum()
            if d is None:
                continue
            px, py, w = d["pos"][0], d["pos"][1], d["w"]
            vx, vy = d["vel"][0], d["vel"][1]
            if abs(w) < 1e-6:
                w = 1e-6
            s_, c_ = math.sin(w * telafi), math.cos(w * telafi)
            # get_plane()'in dondurecegi deger (m) — CT-EKF'in telafili ciktisi
            gp = np.array([(px + (vx * s_ - vy * (1 - c_)) / w) / CM,
                           (py + (vx * (1 - c_) + vy * s_) / w) / CM,
                           (d["pos"][2] + d["vel"][2] * telafi) / CM])
            # gps_guidance:288 tazelik kapisi: deger degismediyse EMA GUNCELLENMEZ
            anahtar = tuple(np.round(gp, 6))
            if son_cikti is not None and anahtar == son_cikti:
                continue
            son_cikti = anahtar
            # gps_guidance:292-306 BIREBIR (EMA konum + sonlu-fark hiz EMA'si)
            if z_est is None:
                z_est = gp
            else:
                n = POS_EMA * gp + (1 - POS_EMA) * z_est
                if z_tson is not None and 1e-3 < t - z_tson < 2.0:
                    z_vel = VEL_EMA * ((n - z_est) / (t - z_tson)) + (1 - VEL_EMA) * z_vel
                z_est = n
            z_tson = t
            zp.append((t, tuple(z_est)))
            zv.append((t, float(z_vel[0]), float(z_vel[1])))
        if len(zp) < 30:
            continue
        r = rapor_kestirim(f"ZINCIR telafi_sn={telafi:.2f}", zp, zv, _omega(zv),
                           ger_pos, ger_vel, ger_om)
        if zincir_en_iyi is None or r["hata_med"] < zincir_en_iyi[1]["hata_med"]:
            zincir_en_iyi = (telafi, r)
    if zincir_en_iyi:
        print(f"\n>> ZINCIR OPTIMUMU telafi_sn = {zincir_en_iyi[0]:.2f} "
              f"(konum hata medyan {zincir_en_iyi[1]['hata_med']:.2f} m, "
              f"hiz siskinligi {zincir_en_iyi[1]['siskinlik']:.2f}x, "
              f"gurultu std {zincir_en_iyi[1]['sapma_std']:.2f}, "
              f"omega {zincir_en_iyi[1]['om_oran']:.2f}x)")
        print(f"   KIYAS — su anki zincir (filtresiz + EMA): konum hata medyan 24.74 m "
              f"(bu kosudaki degeri yukarida '2) TABAN CIZGISI' bolumunde)")
    print("\n[GNSS] Bitti (hic komut gonderilmedi).")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
kopru/kosu_faz31.py — FAZ 3.1 TAM ANGAJMAN: gps_guidance (DEGISMEMIS) + kopru.

Baglama (dosyaya dokunmadan, calisma aninda):
    sys.path -> kopru/gazebo_kaynak (hash'le dogrulanmis BIREBIR kopyalar)
    import control.guidance.gps_guidance as gg
    gg.send_velocity = kopru.dow_kopru.send_velocity
    run_gps_guidance(kopru, kopru.get_plane, kopru.get_iris, stop)

Kullanim:
    python -m kopru.kosu_faz31 --n 3 --sure 75 --zemin 48.4 --etiket A
    python -m kopru.kosu_faz31 --n 3 --sure 75 --zemin 48.4 --etiket B --ic-oran 0.27
    (--ic-oran, AVCI_GPS_IC_ORAN env'ini gg IMPORT'undan ONCE set eder —
     yasanin KENDI anahtari, dosya degismez.)

OLCUMLER (kullanici madde 1-6):
  1. Angajman menzili medyani (oturmus faz = son 40 s) + en yakin
  2. Menzil-zaman egrisi (5 sn'lik tablo + CSV) — monotonluk/salinim/takilma
  3. Komut-takip: komut hiz vektoru vs olculen; ACI + buyukluk farki (medyan/p95),
     manevra anlarinda (komut yonu >15 deg/s donerken) ayri medyan
  4. E_VH_INT_BAND: |e| 2.5 bandinin icinde kalma yuzdesi + integral aktivitesi
  5. SISKINLIK/DOYUM (gg'nin kendi CSV'sinden): |vel_hedef| medyani, 17.55'e
     orani, komutun V_MAX doyum yuzdesi, doyumda kapanma teriminin akibeti
  6. Hava akimi hucreleri: dikey izleme hatasi (|e_vz|>1.5, >=1 s) pencereleri

EMNIYET: AGL<12 -> bolum iptal; teleport -> kosu iptal; NED_ZEMIN_M kaydirmasi
sayesinde gps_guidance'in kendi LOOKUP_MIN_ALT=8 korumasi AGL uzerinden calisir.
"""
from __future__ import annotations

import argparse
import csv
import glob
import math
import os
import sys
import threading
import time

import numpy as np

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_KAYNAK = os.path.join(_REPO, "kopru", "gazebo_kaynak")
_VERI = os.path.join(_REPO, "veri")
BASLINE_HEDEF_HIZ = 17.55          # Faz 3.0 robust olcumu (5 s taban)

KOLONLAR = [
    "ep", "t", "t_wall", "x_m", "y_m", "alt_m", "agl_m", "yaw_dow_deg",
    "sp_vx", "sp_vy", "sp_vz", "vx_ned", "vy_ned", "vz_up_fd",
    "e_fwd", "e_right", "e_vz", "i_fwd", "i_right", "bayat",
    "pitch", "roll", "thr", "yaw",
    "tgt_x_m", "tgt_y_m", "tgt_z_m", "menzil_ham",
    # GERCEK (get_debug_truth) — kilit bandi BUNDAN olculur: ham hedef konumu
    # 1 s gecikmeli + (2,2,1) m offsetli (medyan 19 m hata), kilit kriteri ise
    # GERCEK geometriye aittir (kameranin gordugu). menzil_ham kiyas icin durur.
    "tgt_true_x", "tgt_true_y", "tgt_true_z", "menzil_true",
    "gg_durum", "gg_dh", "gg_menzil", "aci_deg", "mag_fark",
]


def _aci_deg(ax, ay, bx, by):
    na, nb = math.hypot(ax, ay), math.hypot(bx, by)
    if na < 1.5 or nb < 1.5:
        return None
    c = max(-1.0, min(1.0, (ax * bx + ay * by) / (na * nb)))
    return math.degrees(math.acos(c))


def _med_p95(dizi):
    a = np.asarray([x for x in dizi if x is not None], float)
    if len(a) == 0:
        return float("nan"), float("nan")
    return float(np.median(a)), float(np.percentile(a, 95))


def _dwell(s, esik=20.0):
    """gg_dh < esik araliklarinin sureleri + toplam oran (devir bandi kalisi)."""
    araliklar, acik_t, onceki_t = [], None, None
    for r in s:
        d, t = r.get("gg_dh"), r["t"]
        if onceki_t is not None and t - onceki_t > 0.5 and acik_t is not None:
            araliklar.append(onceki_t - acik_t)
            acik_t = None
        if d is not None and d < esik:
            if acik_t is None:
                acik_t = t
        else:
            if acik_t is not None:
                araliklar.append(t - acik_t)
                acik_t = None
        onceki_t = t
    if acik_t is not None:
        araliklar.append(s[-1]["t"] - acik_t)
    araliklar = [x for x in araliklar if x >= 0.2]
    kapsam = s[-1]["t"] - s[0]["t"]
    return araliklar, sum(araliklar) / max(kapsam, 1e-6)


def _r_own(s):
    """Kendi donus yaricapi medyani: |v| / |EMA'li heading orani| (hiz>8)."""
    hdg_prev, t_prev, om_f, sonuc = None, None, 0.0, []
    for r in s:
        spd = math.hypot(r["vx_ned"], r["vy_ned"])
        if spd < 8.0:
            hdg_prev = None
            continue
        h = math.atan2(r["vy_ned"], r["vx_ned"])
        if hdg_prev is not None and 1e-3 < r["t"] - t_prev < 0.2:
            dpsi = (h - hdg_prev + math.pi) % (2 * math.pi) - math.pi
            om_f = 0.95 * om_f + 0.05 * (dpsi / (r["t"] - t_prev))
            if abs(om_f) > 0.03:
                sonuc.append(min(spd / abs(om_f), 600.0))
        hdg_prev, t_prev = h, r["t"]
    return (float(np.median(sonuc)) if sonuc else float("nan")), len(sonuc)


def _salinim(s):
    """Oturmus fazda (t0+20 sonrasi): medyan, genlik (p90-p10), periyot
    (1 s EMA'li menzilin medyani asagi kesmeleri arasi medyan sure)."""
    t0 = s[0]["t"]
    otur = [r for r in s if r["t"] - t0 > 20.0]
    if len(otur) < 20:                     # kisa/iptal bolum: oturmus faz yok
        return float("nan"), float("nan"), float("nan")
    x = np.array([r["menzil_ham"] for r in otur])
    tt = np.array([r["t"] for r in otur])
    f, xs = x[0], []
    for v in x:                                     # 1 s EMA (50 Hz -> a=0.02)
        f += 0.02 * (v - f)
        xs.append(f)
    xs = np.array(xs)
    med = float(np.median(x))
    gecis = [tt[i] for i in range(1, len(xs)) if xs[i-1] >= med > xs[i]]
    periyot = float(np.median(np.diff(gecis))) if len(gecis) > 2 else float("nan")
    return med, float(np.percentile(x, 90) - np.percentile(x, 10)), periyot


def main():
    ap = argparse.ArgumentParser(description="FAZ 3.1 tam angajman")
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--sure", type=float, default=75.0)
    ap.add_argument("--zemin", type=float, default=48.4)
    ap.add_argument("--etiket", default="A")
    # ⛔ YASA DEGERLERI DONDURULDU (kullanici kurali 2026-08-06): gps_guidance.Cfg
    # icindeki hicbir deger degistirilmez (dosya/setattr/env). TEK istisna V_MAX=22
    # (olcumle gerekcelendirildi). Asagidaki iki bayrak OLCUM araclaridir; --ic-oran
    # ve --vmax IZIN OLMADAN kullanilmaz, varsayilan = yasaya DOKUNMA.
    ap.add_argument("--ic-oran", type=float, default=None, dest="ic_oran",
                    help="[IZIN GEREKIR] AVCI_GPS_IC_ORAN env'i")
    ap.add_argument("--vmax", type=float, default=None,
                    help="[TEK ONAYLI ISTISNA: 22] setattr(gg.Cfg,'V_MAX',x), yalniz bu surec")
    ap.add_argument("--range", type=float, default=None, dest="range_set",
                    help="[ONAYLI ISTISNA: 6.9] AVCI_GPS_RANGE env — kilit bandi turetmesi")
    ap.add_argument("--elev", type=float, default=None,
                    help="[TEST] AVCI_GPS_ISTASYON_ELEV env — istasyon LOS yukselisi (deg)")
    ap.add_argument("--ic", type=float, default=None,
                    help="[ONAYLI TESHIS: 0] AVCI_GPS_IC env — ic-daire yan kaymasi (m)")
    ap.add_argument("--kp", type=float, default=None,
                    help="[IZIN GEREKIR] AVCI_GPS_KP env — yatay konum kazanci")
    ap.add_argument("--gnss", choices=["ac", "kapat"], default=None,
                    help="GNSS duzeltici (CT-EKF) — kopru katmani; varsayilan Cfg'den (ACIK)")
    ap.add_argument("--hedef", choices=["bozuk", "truth"], default="bozuk",
                    help="TESHIS: 'truth' = get_plane hedefin GERCEK GPS'inden beslenir "
                         "(bozuk kanal okunmaz, CT-EKF baypas). Yarisma konfigi DEGIL.")
    a = ap.parse_args()

    # gg.Cfg env'i SINIF TANIMINDA okur -> import'tan ONCE set et
    if a.ic_oran is not None:
        os.environ["AVCI_GPS_IC_ORAN"] = str(a.ic_oran)
    if a.range_set is not None:
        os.environ["AVCI_GPS_RANGE"] = str(a.range_set)
    if a.elev is not None:
        os.environ["AVCI_GPS_ISTASYON_ELEV"] = str(a.elev)
    if a.ic is not None:
        os.environ["AVCI_GPS_IC"] = str(a.ic)
    if a.kp is not None:
        os.environ["AVCI_GPS_KP"] = str(a.kp)
    sys.path.insert(0, _KAYNAK)
    import control.guidance.gps_guidance as gg
    if a.vmax is not None:
        setattr(gg.Cfg, "V_MAX", float(a.vmax))     # RANGE_SET ile ayni yontem
    from kopru import dow_kopru
    from kopru.dow_kopru import CM, Cfg, DowKopru
    from kopru.olcum_faz1 import baglan_ve_dogrula
    from sdk import drone_sdk as drone

    gg.send_velocity = dow_kopru.send_velocity      # TEK baglama noktasi
    print(f"[KOSU] gg baglandi: V_MAX={gg.Cfg.V_MAX} RANGE_SET={gg.Cfg.RANGE_SET} "
          f"ELEV={gg.Cfg.ISTASYON_ELEV_DEG} IC_KAYMA={gg.Cfg.IC_KAYMA} "
          f"IC_ORAN={gg.Cfg.IC_ORAN} KP_H={gg.Cfg.KP_H} (etiket {a.etiket})")
    print(f"[KOSU] istasyon: {gg.Cfg.RANGE_SET*math.cos(math.radians(gg.Cfg.ISTASYON_ELEV_DEG)):.2f} m ARKA"
          f" + {gg.Cfg.RANGE_SET*math.sin(math.radians(gg.Cfg.ISTASYON_ELEV_DEG)):.2f} m ALT")
    _K = 1.718 / (2.0 * math.tan(math.radians(125.0) / 2.0))     # 0.4472
    print(f"[KOSU] kilit geometrisi: istasyonda kutu orani "
          f"%{_K / gg.Cfg.RANGE_SET * 100:.2f} (%5 -> R<{_K/0.05:.2f} m, "
          f"%6 -> R<{_K/0.06:.2f} m)")

    baglan_ve_dogrula()
    drone.set_arm(False)
    time.sleep(0.3)
    _ek = {"YATAY_AKTIF": True, "NED_ZEMIN_M": a.zemin}
    if a.gnss is not None:
        _ek["GNSS_DUZELTICI_AKTIF"] = (a.gnss == "ac")
    if a.hedef == "truth":
        _ek["HEDEF_TRUTH_AKTIF"] = True
        _ek["GNSS_DUZELTICI_AKTIF"] = False        # kusursuz veri filtrelenmez
    cfg = type("CfgKosu", (Cfg,), _ek)
    if cfg.HEDEF_TRUTH_AKTIF:
        print("[KOSU] *** TESHIS MODU: hedef GERCEK GPS'ten (bozuk kanal okunmuyor,"
              " CT-EKF baypas) — yarisma konfigurasyonu DEGIL ***")
    else:
        print(f"[KOSU] kopru: GNSS duzeltici "
              f"{'ACIK' if cfg.GNSS_DUZELTICI_AKTIF else 'KAPALI'} "
              f"(dt={cfg.GNSS_DT}, telafi_sn={cfg.GNSS_TELAFI_SN})")
    kopru = DowKopru(drone, cfg=cfg)
    print(f"[KOSU] Kalkis 40 m AGL (zemin {a.zemin})...")
    if not kopru.kalkis(40.0, zemin_m=a.zemin):
        print("[KOSU] Kalkis olmadi — cikiliyor.")
        sys.exit(3)
    kopru.dongu_baslat()                            # 50 Hz ic kontrol dongusu

    os.makedirs(_VERI, exist_ok=True)
    csv_yol = os.path.join(
        _VERI, time.strftime(f"kopru_angajman_{a.etiket}_%Y%m%d_%H%M%S.csv"))
    f = open(csv_yol, "w", newline="", encoding="utf-8")
    w = csv.DictWriter(f, fieldnames=KOLONLAR, extrasaction="ignore")
    w.writeheader()
    satirlar = []
    gg_log_dir = os.path.join(_KAYNAK, "logs")
    ep_gg_csv = {}

    def tgt_ham_m():
        tp = drone.get_target_location()
        return (tp[0] / CM, tp[1] / CM, tp[2] / CM)

    def truth_m():
        """(hedef, drone) GERCEK konumlari (m) — yoksa (None, None)."""
        d = drone.get_debug_truth()
        if not d.get("available"):
            return None, None
        t = d["target"]["position"]
        dr = d["drone"]["position"]
        return ((t[0] / CM, t[1] / CM, t[2] / CM),
                (dr[0] / CM, dr[1] / CM, dr[2] / CM))

    iptal = None
    try:
        for ep in range(1, a.n + 1):
            once_gg = set(glob.glob(os.path.join(gg_log_dir, "gps_guidance_*.csv")))
            stop = threading.Event()
            th = threading.Thread(
                target=gg.run_gps_guidance,
                args=(kopru, kopru.get_plane, kopru.get_iris, stop), daemon=True)
            print(f"\n[KOSU] === ANGAJMAN {ep}/{a.n} ({a.sure:.0f} s) ===")
            th.start()
            t0 = time.monotonic()
            onceki_poz = None
            while time.monotonic() - t0 < a.sure:
                t_tik = time.monotonic()
                tani = kopru.son_tani
                if tani:
                    tg = tgt_ham_m()
                    poz = (tani["x_m"], tani["y_m"], tani["alt_m"])
                    if onceki_poz is not None and math.dist(poz, onceki_poz) > 30.0:
                        iptal = "TELEPORT"
                        break
                    onceki_poz = poz
                    agl = tani["alt_m"] - a.zemin
                    if agl < 12.0:
                        print(f"[KOSU] !! AGL {agl:.1f} m — bolum IPTAL (emniyet)")
                        iptal = f"AGL-ep{ep}"
                        break
                    vx_ned, vy_ned = tani["vx_sdk"], -tani["vy_sdk"]
                    d = {k: tani.get(k) for k in
                         ("t", "sp_vx", "sp_vy", "sp_vz", "e_fwd", "e_right",
                          "e_vz", "i_fwd", "i_right", "bayat", "pitch", "roll",
                          "thr", "yaw", "yaw_dow_deg", "x_m", "y_m", "alt_m",
                          "vz_up_fd")}
                    tg_t, dr_t = truth_m()
                    d.update(ep=ep, t_wall=time.time(), agl_m=agl,
                             vx_ned=vx_ned, vy_ned=vy_ned,
                             tgt_x_m=tg[0], tgt_y_m=tg[1], tgt_z_m=tg[2],
                             menzil_ham=math.dist(poz, tg),
                             tgt_true_x=(tg_t[0] if tg_t else None),
                             tgt_true_y=(tg_t[1] if tg_t else None),
                             tgt_true_z=(tg_t[2] if tg_t else None),
                             menzil_true=(math.dist(dr_t, tg_t)
                                          if (tg_t and dr_t) else None),
                             gg_durum=gg.status.get("durum"),
                             gg_dh=gg.status.get("d_h"),
                             gg_menzil=gg.status.get("menzil"),
                             aci_deg=_aci_deg(tani["sp_vx"], tani["sp_vy"],
                                              vx_ned, vy_ned),
                             mag_fark=(math.hypot(tani["sp_vx"], tani["sp_vy"])
                                       - math.hypot(vx_ned, vy_ned)))
                    satirlar.append(d)
                    w.writerow({k: (round(v, 5) if isinstance(v, float) else v)
                                for k, v in d.items() if k in KOLONLAR})
                gecen = time.monotonic() - t_tik
                if gecen < 0.02:
                    time.sleep(0.02 - gecen)
            stop.set()
            th.join(timeout=2.0)
            yeni = set(glob.glob(os.path.join(gg_log_dir, "gps_guidance_*.csv"))) - once_gg
            if yeni:
                ep_gg_csv[ep] = sorted(yeni)[-1]
            if iptal == "TELEPORT":
                print("[KOSU] !! TELEPORT/respawn — kosu iptal.")
                break
            iptal = None if (iptal or "").startswith("AGL") else iptal
            time.sleep(4.0)                          # bayat -> TRIM hover arasi
    finally:
        f.close()
        for _ in range(30):
            kopru.hover()
            time.sleep(0.02)

    # ═══ ANALIZ ═══
    print(f"\n[KOSU] Ana CSV: {csv_yol}")
    ozet_medyan, ozet_enyakin = [], []
    for ep in range(1, a.n + 1):
        s = [r for r in satirlar if r["ep"] == ep]
        if len(s) < 100:
            continue
        t0 = s[0]["t"]
        _mk = "menzil_true" if any(r.get("menzil_true") is not None for r in s) \
            else "menzil_ham"
        men = [r[_mk] for r in s if r.get(_mk) is not None]
        for r in s:                       # egri/analiz icin tek isim
            r["menzil_ham"] = r.get(_mk) if r.get(_mk) is not None else r["menzil_ham"]
        print(f"\n===== ANGAJMAN {ep} — menzil egrisi (5 s'lik, "
              f"{'GERCEK' if _mk == 'menzil_true' else 'HAM'} 3B m) =====")
        satir = []
        for i, r in enumerate(s):
            if not satir or r["t"] - t0 >= len(satir) * 5.0:
                satir.append(f"{r['t']-t0:3.0f}s:{r['menzil_ham']:5.1f}")
        print("  " + " | ".join(satir))
        son40 = [r for r in s if r["t"] >= s[-1]["t"] - 40.0]
        m_med = float(np.median([r["menzil_ham"] for r in son40]))
        m_min = float(np.min(men))
        m_std = float(np.std([r["menzil_ham"] for r in son40]))
        t30 = next((r["t"] - t0 for r in s if r["menzil_ham"] < 30.0), None)
        ozet_medyan.append(m_med)
        ozet_enyakin.append(m_min)
        print(f"baslangic {men[0]:.0f} m | <30 m'ye "
              f"{('%.0f s' % t30) if t30 is not None else 'ULASAMADI'} | "
              f"EN YAKIN {m_min:.1f} m | oturmus (son 40 s) medyan {m_med:.1f} m, "
              f"std {m_std:.1f} m")
        # 3) komut-takip
        aci_m, aci_p = _med_p95([r["aci_deg"] for r in s])
        mag = [abs(r["mag_fark"]) for r in s if r["aci_deg"] is not None]
        mag_m, mag_p = _med_p95(mag)
        # manevra anlari: komut yonu donus hizi > 15 deg/s
        yon = [math.atan2(r["sp_vy"], r["sp_vx"]) if
               math.hypot(r["sp_vx"], r["sp_vy"]) > 1.5 else None for r in s]
        man_aci = []
        for i in range(1, len(s)):
            if yon[i] is None or yon[i-1] is None:
                continue
            dt = s[i]["t"] - s[i-1]["t"]
            dpsi = abs(math.degrees(
                (yon[i] - yon[i-1] + math.pi) % (2 * math.pi) - math.pi))
            if dt > 1e-3 and dpsi / dt > 15.0 and s[i]["aci_deg"] is not None:
                man_aci.append(s[i]["aci_deg"])
        man_m, _ = _med_p95(man_aci)
        print(f"komut-takip ACISI: medyan {aci_m:.1f} / p95 {aci_p:.1f} deg "
              f"(manevra anlari medyan {man_m:.1f} deg, n={len(man_aci)}); "
              f"buyukluk farki medyan {mag_m:.2f} / p95 {mag_p:.2f} m/s")
        # 4) E_VH_INT_BAND
        aktif = [r for r in s if not r["bayat"]]
        ic_f = np.mean([abs(r["e_fwd"]) <= 2.5 for r in aktif]) * 100
        ic_r = np.mean([abs(r["e_right"]) <= 2.5 for r in aktif]) * 100
        imax = max(max(abs(r["i_fwd"]) for r in aktif),
                   max(abs(r["i_right"]) for r in aktif))
        print(f"E_VH_INT_BAND: |e_fwd| bant-ici %{ic_f:.0f}, |e_right| %{ic_r:.0f}; "
              f"max |i| {imax:.3f} (yetki 0.15)")
        # GERCEK KILIT BANDI (kutu orani) — R = GERCEK menzil (truth). Ham hedef
        # konumu 1 s gecikmeli/offsetli oldugundan kilit bandi ONDAN olculemez.
        _truth_var = any(r.get("menzil_true") is not None for r in s)
        _kaynak_k = "menzil_true" if _truth_var else "menzil_ham"
        if not _truth_var:
            print("UYARI: truth yok -> kilit bandi HAM menzilden (guvenilmez)")
        for esik, etiket_k in ((_K / 0.06, "%6"), (_K / 0.05, "%5")):
            ic = [(r.get(_kaynak_k) is not None and r[_kaynak_k] < esik) for r in s]
            tt = [r["t"] for r in s]
            ar, acik, onc = [], None, None
            for i, t in enumerate(tt):
                if onc is not None and t - onc > 0.5 and acik is not None:
                    ar.append(onc - acik); acik = None
                if ic[i]:
                    if acik is None:
                        acik = t
                elif acik is not None:
                    ar.append(t - acik); acik = None
                onc = t
            if acik is not None:
                ar.append(tt[-1] - acik)
            ar = [x for x in ar if x >= 0.2]
            # 10 s kayan pencerede kumulatif maksimum (prefix + iki isaretci)
            n = len(tt)
            cum = [0.0] * (n + 1)
            for i in range(n - 1):
                dtt = tt[i+1] - tt[i]
                cum[i+1] = cum[i] + (dtt if (ic[i] and dtt < 0.5) else 0.0)
            cum[n] = cum[n-1]
            j, pen = 0, 0.0
            for i in range(n):
                j = max(j, i)
                while j + 1 < n and tt[j+1] - tt[i] <= 10.0:
                    j += 1
                pen = max(pen, cum[j] - cum[i])
            print(f"KILIT BANDI {etiket_k} (R<{esik:.2f} m): {len(ar)} giris, kalis "
                  f"medyan {(np.median(ar) if ar else 0):.1f} s (max "
                  f"{(max(ar) if ar else 0):.1f}), toplam "
                  f"%{sum(ar)/max(tt[-1]-tt[0],1e-6)*100:.1f}, 10s-KUMULATIF "
                  f"{pen:.2f} s" + ("  >>ISTERI SAGLANDI" if pen >= 5.0 else ""))
        # devir bandi + kendi donus yaricapi + salinim (C kiyas metrikleri)
        ar, oran = _dwell(s)
        r_med, r_n = _r_own(s)
        sal_med, sal_gen, sal_per = _salinim(s)
        print(f"DEVIR BANDI (d_h<20): {len(ar)} giris, kalis medyan "
              f"{(np.median(ar) if ar else float('nan')):.1f} s (max "
              f"{(max(ar) if ar else 0):.1f}), toplam %{oran*100:.0f}")
        print(f"KENDI DONUS YARICAPI medyan {r_med:.0f} m (n={r_n}); "
              f"salinim: genlik(p90-p10) {sal_gen:.0f} m, periyot {sal_per:.1f} s")
        # 6) dikey bozucu pencereleri
        boz, acik = 0, 0
        for r in s:
            if abs(r["e_vz"]) > 1.5:
                acik += 1
                if acik == 50:
                    boz += 1
            else:
                acik = 0
        print(f"dikey bozucu (|e_vz|>1.5 m/s, >=1 s): {boz} pencere")
        # 5) siskinlik/doyum (gg CSV)
        yol_gg = ep_gg_csv.get(ep)
        if yol_gg:
            with open(yol_gg, newline="", encoding="utf-8") as fg:
                gs = [r for r in csv.DictReader(fg) if r["tgt_vx"]]
            tv = np.array([[float(r["tgt_vx"]), float(r["tgt_vy"])] for r in gs])
            vc = np.array([[float(r["vx_cmd"]), float(r["vy_cmd"])] for r in gs])
            e_st = np.array([[float(r["st_x"]) - float(r["iris_x"]),
                              float(r["st_y"]) - float(r["iris_y"])] for r in gs])
            tvm = np.linalg.norm(tv, axis=1)
            vcm = np.linalg.norm(vc, axis=1)
            doy = vcm >= 0.985 * gg.Cfg.V_MAX
            en = np.linalg.norm(e_st, axis=1)
            eh = e_st / np.clip(en, 1e-6, None)[:, None]
            kapanma_eff = np.einsum("ij,ij->i", vc - tv, eh)
            istek_p = gg.Cfg.KP_H * en
            print(f"SISKINLIK: |vel_hedef| medyan {np.median(tvm):.2f} m/s -> "
                  f"oran {np.median(tvm)/BASLINE_HEDEF_HIZ:.2f}x (taban 17.55); "
                  f"DOYUM %{np.mean(doy)*100:.0f} (V_MAX={gg.Cfg.V_MAX})")
            if doy.any() and (~doy).any():
                print(f"  kapanma: istek KP_H*|e| medyan {np.median(istek_p):.2f} m/s; "
                      f"EFEKTIF kapanma bileseni medyan "
                      f"doyumda {np.median(kapanma_eff[doy]):+.2f} / "
                      f"doyumsuz {np.median(kapanma_eff[~doy]):+.2f} m/s")
            print(f"  gg CSV: {os.path.basename(yol_gg)}")
    if ozet_medyan:
        print(f"\n===== TOPLU ({a.etiket}, {len(ozet_medyan)} angajman) =====")
        print(f"oturmus menzil medyanlari: "
              + ", ".join(f"{m:.1f}" for m in ozet_medyan)
              + f" -> GENEL MEDYAN {np.median(ozet_medyan):.1f} m")
        print(f"en yakin mesafeler: "
              + ", ".join(f"{m:.1f}" for m in ozet_enyakin)
              + f" -> EN YAKIN {min(ozet_enyakin):.1f} m")
    if iptal:
        print(f"[KOSU] NOT: kosu '{iptal}' ile kesildi.")
    print("[KOSU] Bitti; arac hover'da birakildi.")


if __name__ == "__main__":
    main()

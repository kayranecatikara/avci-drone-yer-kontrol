# -*- coding: utf-8 -*-
"""
kopru/olcum_faz2.py — FAZ 2 yatay kanal olcumleri (isaret/trim/kapali-cevrim/yanal/yaw).

Kullanim (repo kokunden, oyun PLAY'de; --zemin spawn zemininin dunya-z'si, m):
    python -m kopru.olcum_faz2 --mod acik   --zemin 48.4   (ADIM 1+2+4-trim)
    python -m kopru.olcum_faz2 --mod kapali --zemin 48.4   (ADIM 3+4-kapali+EK yaw)

MODLAR:
  isaret : ADIM 1 — acik dongu, 4 heading'de (NED 0/90/180/270) sabit kucuk
           pitch ve roll stick'i; dunya hiz azimutu beklenen yonle karsilastirilir
           (e_right isaret tuzagi + cerceve donusumu her heading'de).
  trim   : ADIM 2 — pitch stick taramasi (0.10/0.15/0.20/0.30/0.45), oturmus
           seyir hizi + oturma suresi; egri uydurmalar (dogrusal / kuadratik)
           + Cfg.YATAY_TRIM_NOKTA icin OLCULMUS tablo basilir.
  yanal  : ADIM 4-trim — roll stick taramasi (0.10/0.20/0.30); yanal egri
           ileri egriyle karsilastirilir (ayni mi ayrisiyor mu).
  adim   : ADIM 3 — kapali cevrim (YATAY_AKTIF=True): 0->10 ve 10->18 m/s
           basamaklari; asma %, oturma, kalici hata (kabul: hata<%5, asma<%20).
  yanaladim : ADIM 4-kapali — saf yanal 0->5 m/s basamagi (yaw sabit).
  yawtavan  : EK — YAW_MAX=0.85 ile +-90 adim tekrari + 0.85 stick acik-dongu orani.

Emniyet: olcum_faz1'in katmanlari aynen (AGL<15 koruma, teleport dedektoru,
zemin referansi, arm kenari). Sticks yalniz kancalar uzerinden (slew korunur).
"""
from __future__ import annotations

import argparse
import math
import sys
import time

import numpy as np

from sdk import drone_sdk as drone
from kopru.dow_kopru import (CM, Cfg, DowKopru, dunya_to_govde, dow_yaw_to_ned,
                             sarmala_pi, yatay_trim_stick)
from kopru.olcum_faz1 import (GUARD_AGL_M, GUARD_VZ_NED, TELEPORT_M, Kayitci,
                              RespawnHatasi, YatayFD, baglan_ve_dogrula, egim,
                              kalkis_yap)
from kopru.olcum_faz1 import KOLONLAR as _K1

KOLONLAR = _K1 + ["sp_vx", "sp_vy", "i_fwd", "i_right", "e_fwd", "e_right",
                  "knob_pitch", "knob_roll", "spd"]


def hazirla_faz2(zemin_arg):
    drone.set_arm(False)                # arm kenari
    time.sleep(0.3)
    kopru = DowKopru(drone, cfg=type("CfgOlcum2", (Cfg,), {}))
    alt = drone.get_drone_altitude() / CM
    if zemin_arg is not None:
        zemin = float(zemin_arg)
        print(f"[OLCUM] Zemin (verilen): {zemin:.1f} m — su anki dunya-z {alt:.1f} "
              f"(AGL {alt - zemin:.1f})")
    else:
        zemin = alt
        print(f"[OLCUM] Zemin (VARSAYIM: arac yerde): {zemin:.1f} m — "
              f"havadaysa --zemin ver!")
    return kopru, zemin


def tik(kopru, kayit, fd, zemin, ad, sp_ned=(0.0, 0.0, 0.0), yaw_sp=0.0,
        onceki_poz=None):
    """TEK kontrol tiki + log + koruma. Donus: (tani, poz)."""
    agl = None
    kopru.set_hiz_ned(sp_ned[0], sp_ned[1], sp_ned[2], yaw_sp)
    tani = dict(kopru.adim())
    agl = tani["alt_m"] - zemin
    poz = (tani["x_m"], tani["y_m"], tani["alt_m"])
    if onceki_poz is not None and math.dist(poz, onceki_poz) > TELEPORT_M:
        print(f"[OLCUM]   !! RESPAWN/ISINLANMA ({ad}) — olcum gecersiz.")
        raise RespawnHatasi(ad)
    vxf, vyf = fd.guncelle(tani["x_m"], tani["y_m"], tani["t"])
    tani.update(seg=ad, t_wall=time.time(), sp_vz=sp_ned[2], agl_m=agl,
                guard=0, vx_fd=vxf, vy_fd=vyf,
                knob_pitch=float(kopru.cfg.PITCH_SABIT),
                knob_roll=float(kopru.cfg.ROLL_SABIT),
                spd=math.hypot(tani["vx_sdk"], tani["vy_sdk"]))
    kayit.yaz(tani)
    return tani, poz


def kos(kopru, kayit, fd, zemin, ad, sure_s, sp_ned=(0.0, 0.0, 0.0), yaw_sp=0.0,
        bitis=None):
    """sure_s boyunca 50 Hz kos; bitis(t0, tani) True donerse erken cik.
    AGL korumasi: dusukse dikey setpoint zorla tirmanisa cevrilir."""
    period = 1.0 / kopru.cfg.LOOP_HZ
    onceki_poz = None
    t0 = time.monotonic()
    guard_ilan = False
    while time.monotonic() - t0 < sure_s:
        t_tik = time.monotonic()
        agl = kopru.sdk.get_drone_altitude() / CM - zemin
        sp = sp_ned
        if agl < GUARD_AGL_M:
            sp = (sp_ned[0], sp_ned[1], GUARD_VZ_NED)
            if not guard_ilan:
                print(f"[OLCUM]   !! AGL {agl:.1f} < {GUARD_AGL_M:.0f} -> "
                      f"koruma tirmanisi ({ad})")
                guard_ilan = True
        tani, onceki_poz = tik(kopru, kayit, fd, zemin, ad, sp, yaw_sp, onceki_poz)
        if bitis is not None and bitis(t0, tani):
            break
        gecen = time.monotonic() - t_tik
        if gecen < period:
            time.sleep(period - gecen)


def don(kopru, kayit, fd, zemin, hedef_yaw_ned, ad="don", tavan_s=8.0):
    """Buruns hedef NED yaw'a donene kadar bekle (|hata|<5 deg, 0.4 s)."""
    sayac = [0]

    def bitis(t0, tani):
        if abs(tani["yaw_hata_deg"]) < 5.0:
            sayac[0] += 1
        else:
            sayac[0] = 0
        return sayac[0] >= 20                      # 0.4 s icerde
    kos(kopru, kayit, fd, zemin, ad, tavan_s, (0.0, 0.0, 0.0), hedef_yaw_ned,
        bitis)


def fren(kopru, kayit, fd, zemin, yaw_sp, esik=2.5, tavan_s=14.0, ad="fren"):
    """Hizi dusur: govde-cercevesi hiza KARSI sabit stick (acik dongu)."""
    period = 1.0 / kopru.cfg.LOOP_HZ
    onceki_poz = None
    t0 = time.monotonic()
    while time.monotonic() - t0 < tavan_s:
        t_tik = time.monotonic()
        t = kopru.sdk.get_telemetry()["drone"]
        vx, vy = t["velocity"][0] / CM, t["velocity"][1] / CM
        yaw_dow = math.radians(t["rotation"][2])
        v_fwd, v_right = dunya_to_govde(vx, vy, yaw_dow)
        spd = math.hypot(vx, vy)
        if spd < esik:
            break
        kopru.cfg.PITCH_SABIT = -0.35 if v_fwd > 1.0 else (0.35 if v_fwd < -1.0 else 0.0)
        kopru.cfg.ROLL_SABIT = -0.35 if v_right > 1.0 else (0.35 if v_right < -1.0 else 0.0)
        tani, onceki_poz = tik(kopru, kayit, fd, zemin, ad,
                               (0.0, 0.0, 0.0), yaw_sp, onceki_poz)
        gecen = time.monotonic() - t_tik
        if gecen < period:
            time.sleep(period - gecen)
    kopru.cfg.PITCH_SABIT = 0.0
    kopru.cfg.ROLL_SABIT = 0.0


def _seg(kayit, ad):
    return [r for r in kayit.satirlar if r["seg"] == ad]


def _son_sn(rows, sn):
    if not rows:
        return []
    t1 = rows[-1]["t"]
    return [r for r in rows if r["t"] >= t1 - sn]


def _az_ned_deg(vx_ned, vy_ned):
    return math.degrees(math.atan2(vy_ned, vx_ned))


# ── ADIM 1: isaret/eksen (acik dongu) ───────────────────────────────────────

def mod_isaret(kopru, zemin):
    kalkis_yap(kopru, zemin, 60.0)
    kayit = Kayitci("f2isaret", KOLONLAR)
    fd = YatayFD()
    sonuc = []
    try:
        for h_deg in (0.0, 90.0, 180.0, 270.0):
            h = sarmala_pi(math.radians(h_deg))
            don(kopru, kayit, fd, zemin, h, ad=f"don_{int(h_deg)}")
            for eksen, beklenen_off in (("pitch", 0.0), ("roll", 90.0)):
                ad = f"{eksen}_{int(h_deg)}"
                if eksen == "pitch":
                    kopru.cfg.PITCH_SABIT = 0.12
                else:
                    kopru.cfg.ROLL_SABIT = 0.12
                kos(kopru, kayit, fd, zemin, ad, 4.0, (0.0, 0.0, 0.0), h)
                kopru.cfg.PITCH_SABIT = 0.0
                kopru.cfg.ROLL_SABIT = 0.0
                s = _son_sn(_seg(kayit, ad), 1.5)
                # DoW hiz -> NED: y ve isaretler dow_to_ned ile (vx, -vy)
                vx = float(np.mean([r["vx_sdk"] for r in s]))
                vy = float(np.mean([r["vy_sdk"] for r in s]))
                az = _az_ned_deg(vx, -vy)
                spd = math.hypot(vx, vy)
                beklenen = sarmala_pi(math.radians(h_deg + beklenen_off))
                hata = math.degrees(sarmala_pi(math.radians(az) - beklenen))
                sonuc.append((h_deg, eksen, az, math.degrees(beklenen), hata, spd))
                fren(kopru, kayit, fd, zemin, h, ad=f"fren_{ad}")
    finally:
        kopru.cfg.PITCH_SABIT = 0.0
        kopru.cfg.ROLL_SABIT = 0.0
        kayit.kapat()

    print("\n===== ADIM 1: ISARET/EKSEN RAPORU (acik dongu, stick 0.12) =====")
    print("heading | eksen | olculen az (NED) | beklenen | HATA | hiz")
    kotu = 0
    for h_deg, eksen, az, bek, hata, spd in sonuc:
        isaret = "OK" if abs(hata) < 25.0 else "!! TERS/SAPKIN"
        if abs(hata) >= 25.0:
            kotu += 1
        print(f"  {h_deg:5.0f} | {eksen:5s} | {az:+8.1f} deg | {bek:+8.1f} | "
              f"{hata:+6.1f} deg | {spd:4.1f} m/s  {isaret}")
    print(f"SONUC: {len(sonuc) - kotu}/{len(sonuc)} yon dogru "
          f"(esik +-25 deg; ruzgar yok, sapma buyukse cerceve hatasi demektir)")
    print(f"CSV: {kayit.yol}")
    return kotu == 0


# ── ADIM 2: trim egrisi ─────────────────────────────────────────────────────

def _oturt(kopru, kayit, fd, zemin, ad, yaw_sp, tavan_s=25.0):
    """Sabit knob'la oturmus hiza gel: hiz egimi < 0.15 m/s^2 (son 2 s) ve t>6 s."""
    pencere = []

    def bitis(t0, tani):
        pencere.append((tani["t"], tani["spd"]))
        while pencere and pencere[-1][0] - pencere[0][0] > 2.0:
            pencere.pop(0)
        if time.monotonic() - t0 < 6.0 or len(pencere) < 50:
            return False
        m = egim([p[0] for p in pencere], [p[1] for p in pencere])
        return abs(m) < 0.15
    kos(kopru, kayit, fd, zemin, ad, tavan_s, (0.0, 0.0, 0.0), yaw_sp, bitis)


def _oturma_suresi(rows, hedef_spd):
    """%95 bandina ILK giris zamani (s, segment basindan)."""
    for r in rows:
        if r["spd"] >= 0.95 * hedef_spd:
            return r["t"] - rows[0]["t"]
    return None


def mod_trim(kopru, zemin, stickler=(0.10, 0.15, 0.20, 0.30, 0.45), eksen="pitch"):
    kalkis_yap(kopru, zemin, 60.0)
    kayit = Kayitci(f"f2trim_{eksen}", KOLONLAR)
    fd = YatayFD()
    h_deg = 0.0
    noktalar = []
    try:
        for stick in stickler:
            h = sarmala_pi(math.radians(h_deg))
            don(kopru, kayit, fd, zemin, h, ad=f"don_{stick:.2f}")
            ad = f"trim_{stick:.2f}"
            if eksen == "pitch":
                kopru.cfg.PITCH_SABIT = stick
            else:
                kopru.cfg.ROLL_SABIT = stick
            _oturt(kopru, kayit, fd, zemin, ad, h)
            kopru.cfg.PITCH_SABIT = 0.0
            kopru.cfg.ROLL_SABIT = 0.0
            s = _seg(kayit, ad)
            v_otur = float(np.mean([r["spd"] for r in _son_sn(s, 2.0)]))
            t_otur = _oturma_suresi(s, v_otur)
            noktalar.append((stick, v_otur, t_otur, s[-1]["t"] - s[0]["t"]))
            print(f"[OLCUM]   stick {stick:.2f} -> {v_otur:5.2f} m/s "
                  f"(%95'e {t_otur if t_otur else -1:.1f} s, segment "
                  f"{s[-1]['t'] - s[0]['t']:.1f} s)")
            fren(kopru, kayit, fd, zemin, h, ad=f"fren_{stick:.2f}")
            h_deg = (h_deg + 180.0) % 360.0        # mekik: harita disina tasma
    finally:
        kopru.cfg.PITCH_SABIT = 0.0
        kopru.cfg.ROLL_SABIT = 0.0
        kayit.kapat()

    print(f"\n===== ADIM 2: TRIM EGRISI ({eksen}) =====")
    print("stick | oturmus hiz | %95 suresi")
    for stick, v, t_o, t_seg in noktalar:
        print(f" {stick:.2f} | {v:6.2f} m/s | {t_o if t_o else -1:5.1f} s")
    v = np.array([n[1] for n in noktalar])
    st = np.array([n[0] for n in noktalar])
    # uydurmalar: stick = a*v (dogrusal) | a*v + b*v^2 (kuadratik surukleme)
    a_lin = float(np.sum(st * v) / np.sum(v * v))
    A = np.vstack([v, v * v]).T
    (a_q, b_q), _, _, _ = np.linalg.lstsq(A, st, rcond=None)
    for adx, tahmin in (("dogrusal a*v", a_lin * v),
                        ("kuadratik a*v+b*v^2", A @ np.array([a_q, b_q]))):
        ss_res = float(np.sum((st - tahmin) ** 2))
        ss_tot = float(np.sum((st - np.mean(st)) ** 2))
        print(f"uydurma {adx}: R^2 = {1 - ss_res / ss_tot:.4f}")
    print(f"  dogrusal : stick = {a_lin:.5f} * v")
    print(f"  kuadratik: stick = {a_q:.5f}*v + {b_q:.6f}*v^2")
    print("OLCULMUS TABLO (Cfg.YATAY_TRIM_NOKTA icin, (hiz, stick)):")
    tablo = "((0.0, 0.0), " + ", ".join(
        f"({n[1]:.1f}, {n[0]:.2f})" for n in noktalar) + ")"
    print("  " + tablo)
    print(f"CSV: {kayit.yol}")
    return noktalar


# ── ADIM 3: kapali cevrim basamaklari ───────────────────────────────────────

def _basamak_rapor(ad, s, v0, v1):
    yon = np.array([math.cos(math.radians(s[0]["sp_yaw_ned_deg"])),
                    math.sin(math.radians(s[0]["sp_yaw_ned_deg"]))])
    # hiz bileseni komut yonunde (NED): (vx, -vy) . yon
    vy_yon = [float(np.dot((r["vx_sdk"], -r["vy_sdk"]), yon)) for r in s]
    adim_b = v1 - v0
    tepe = max(vy_yon) if adim_b > 0 else min(vy_yon)
    asma = max(0.0, (tepe - v1) / adim_b * 100.0) if adim_b > 0 else \
        max(0.0, (v1 - tepe) / (-adim_b) * 100.0)
    bant = 0.05 * abs(adim_b)
    otur = None
    for i, r in enumerate(s):
        if all(abs(v - v1) <= bant for v in vy_yon[i:i + 25]):
            otur = r["t"] - s[0]["t"]
            break
    kalici = float(np.mean(vy_yon[-100:])) - v1
    print(f"{ad}: {v0:.0f}->{v1:.0f} m/s | asma {asma:.1f}% | oturma "
          f"{('%.2f s' % otur) if otur is not None else 'OLMADI'} | kalici hata "
          f"{kalici:+.2f} m/s ({abs(kalici) / max(abs(v1), 1e-6) * 100:.1f}%) | "
          f"KABUL: {'GECTI' if (abs(kalici) <= 0.05 * abs(v1) and asma <= 20.0) else 'KALDI'}")
    return asma, otur, kalici


def mod_adim(kopru, zemin):
    kalkis_yap(kopru, zemin, 60.0)
    kayit = Kayitci("f2adim", KOLONLAR)
    fd = YatayFD()
    kopru.cfg.YATAY_AKTIF = True
    try:
        h = kopru.get_iris()["yaw"]
        yon = (math.cos(h), math.sin(h))
        print(f"[OLCUM] adim: heading NED {math.degrees(h):.0f} deg; "
              f"0->10 (12s), 10->18 (12s), 18->0 (10s)")
        for ad, v in (("adim_0_10", 10.0), ("adim_10_18", 18.0), ("adim_18_0", 0.0)):
            kos(kopru, kayit, fd, zemin, ad, 12.0 if v else 10.0,
                (v * yon[0], v * yon[1], 0.0), h)
    finally:
        kopru.cfg.YATAY_AKTIF = False
        kayit.kapat()

    print("\n===== ADIM 3: KAPALI CEVRIM BASAMAK RAPORU =====")
    _basamak_rapor("adim_0_10", _seg(kayit, "adim_0_10"), 0.0, 10.0)
    _basamak_rapor("adim_10_18", _seg(kayit, "adim_10_18"), 10.0, 18.0)
    s = _seg(kayit, "adim_18_0")
    print(f"adim_18_0 (fren): son hiz {_son_sn(s, 1.0)[-1]['spd']:.2f} m/s "
          f"({s[-1]['t'] - s[0]['t']:.1f} s'de)")
    son = _seg(kayit, "adim_10_18")
    print(f"i_fwd son: {son[-1]['i_fwd']:+.3f} (yetki {kopru.cfg.I_VH_MAX})")
    print(f"CSV: {kayit.yol}")


def mod_yanaladim(kopru, zemin):
    kalkis_yap(kopru, zemin, 60.0)
    kayit = Kayitci("f2yanaladim", KOLONLAR)
    fd = YatayFD()
    kopru.cfg.YATAY_AKTIF = True
    try:
        h = kopru.get_iris()["yaw"]
        sag = sarmala_pi(h + math.pi / 2.0)        # NED'de sag = heading+90
        yon = (math.cos(sag), math.sin(sag))
        print(f"[OLCUM] yanaladim: burun {math.degrees(h):.0f} deg sabit, "
              f"saga 0->5 m/s (10 s), 5->0 (8 s)")
        kos(kopru, kayit, fd, zemin, "yanal_0_5",
            10.0, (5.0 * yon[0], 5.0 * yon[1], 0.0), h)
        kos(kopru, kayit, fd, zemin, "yanal_5_0", 8.0, (0.0, 0.0, 0.0), h)
    finally:
        kopru.cfg.YATAY_AKTIF = False
        kayit.kapat()

    print("\n===== ADIM 4: YANAL KAPALI CEVRIM =====")
    s = _seg(kayit, "yanal_0_5")
    # yanal hiz bileseni (sag yonunde) + burun sapmasi
    yon = (math.cos(sag), math.sin(sag))
    vy_yan = [float(np.dot((r["vx_sdk"], -r["vy_sdk"]), yon)) for r in s]
    kalici = float(np.mean(vy_yan[-100:])) - 5.0
    print(f"yanal_0_5: son hiz (sag bileseni) {np.mean(vy_yan[-100:]):.2f} m/s, "
          f"kalici hata {kalici:+.2f} m/s, "
          f"burun sapmasi max {max(abs(r['yaw_hata_deg']) for r in s):.1f} deg, "
          f"i_right son {s[-1]['i_right']:+.3f}")
    print(f"CSV: {kayit.yol}")


# ── EK: yaw tavani 0.85 ─────────────────────────────────────────────────────

def mod_yawtavan(kopru, zemin):
    kalkis_yap(kopru, zemin, 40.0)
    kayit = Kayitci("f2yawtavan", KOLONLAR)
    fd = YatayFD()
    print(f"[OLCUM] yawtavan: YAW_MAX={kopru.cfg.YAW_MAX} — acik 0.85 stick 3s + "
          f"kapali +-90 adim")
    try:
        kopru.cfg.YAW_SABIT = 0.85
        kos(kopru, kayit, fd, zemin, "acik_0.85", 3.0, (0.0, 0.0, 0.0),
            kopru.get_iris()["yaw"])
        kopru.cfg.YAW_SABIT = None
        kos(kopru, kayit, fd, zemin, "dur", 2.0, (0.0, 0.0, 0.0),
            kopru.get_iris()["yaw"])
        for yonn, ad in ((+90.0, "adim_p90"), (-90.0, "adim_n90")):
            y0 = kopru.get_iris()["yaw"]
            hedef = sarmala_pi(y0 + math.radians(yonn))
            kos(kopru, kayit, fd, zemin, ad, 8.0, (0.0, 0.0, 0.0), hedef)
    finally:
        kopru.cfg.YAW_SABIT = None
        kayit.kapat()

    print("\n===== EK: YAW_MAX=0.85 RAPORU =====")
    s = _son_sn(_seg(kayit, "acik_0.85"), 2.0)
    hiz = egim([r["t"] for r in s],
               list(np.degrees(np.unwrap(np.radians([r["yaw_dow_deg"] for r in s])))))
    print(f"acik dongu 0.85 stick: {hiz:+.1f} deg/s "
          f"(hedef ~121; 143 deg/s-per-stick dogrusalligi)")
    for ad, yonn in (("adim_p90", +90.0), ("adim_n90", -90.0)):
        s = _seg(kayit, ad)
        otur = None
        for r in s:
            if abs(r["yaw_hata_deg"]) < 5.0:
                otur = r["t"] - s[0]["t"]
                break
        top = 0.0
        onceki = None
        for r in s:
            y = math.radians(r["yaw_dow_deg"])
            if onceki is not None:
                top += sarmala_pi(y - onceki)
            onceki = y
        kuyruk = _son_sn(s, 1.5)
        print(f"{ad}: oturma {('%.2f s' % otur) if otur else 'OLMADI'}, toplam donus "
              f"{math.degrees(top):+.1f} deg (~{yonn:+.0f} olmali, kacak yok ise), "
              f"kalan hata {float(np.mean([r['yaw_hata_deg'] for r in kuyruk])):+.1f} deg")
    print(f"CSV: {kayit.yol}")


# ── main ────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="FAZ 2 yatay kanal olcumleri")
    ap.add_argument("--mod", choices=["isaret", "trim", "yanal", "adim",
                                      "yanaladim", "yawtavan", "acik", "kapali"],
                    default="acik")
    ap.add_argument("--zemin", type=float, default=None,
                    help="spawn zemini dunya-z (m); verilmezse mevcut irtifa zemin sayilir")
    a = ap.parse_args()

    baglan_ve_dogrula()
    kopru, zemin = hazirla_faz2(a.zemin)
    try:
        if a.mod in ("isaret", "acik"):
            mod_isaret(kopru, zemin)
        if a.mod in ("trim", "acik"):
            mod_trim(kopru, zemin)
        if a.mod in ("yanal", "acik"):
            mod_trim(kopru, zemin, stickler=(0.10, 0.20, 0.30), eksen="roll")
        if a.mod in ("adim", "kapali"):
            mod_adim(kopru, zemin)
        if a.mod in ("yanaladim", "kapali"):
            mod_yanaladim(kopru, zemin)
        if a.mod in ("yawtavan", "kapali"):
            mod_yawtavan(kopru, zemin)
    except RespawnHatasi as e:
        print(f"\n[OLCUM] IPTAL: respawn/isinlanma ({e}). Kalan modlar KOSULMADI.")
    except KeyboardInterrupt:
        print("\n[OLCUM] Kesildi — TRIM hover'a geciliyor.")
    finally:
        kopru.cfg.PITCH_SABIT = 0.0
        kopru.cfg.ROLL_SABIT = 0.0
        kopru.cfg.YAW_SABIT = None
        kopru.cfg.YATAY_AKTIF = False
        for _ in range(30):
            kopru.hover()
            time.sleep(0.02)
        print("[OLCUM] Bitti; arac hover'da birakildi.")


if __name__ == "__main__":
    main()
